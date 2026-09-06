"""카드 t306 — 업로드 경로도 마디 경계에서 쪼갠다.

t305 는 감독 인터뷰 경로(``_song_design_interview`` → ``_build_unified_song_plan``)
만 쪼갰다. 이 파일은 **업로드 경로**(오디오 업로드 → ``analyse_song_audio`` →
확인 카드 → ``prepare_songcue``)가 같은 규칙을 타는지 잰다.

콘솔 접촉 0건 — 가짜 실행 포트와 가짜 상태 포트 위에서만 돈다.

세 가지를 못박는다:

1. 측정 BPM 이 있으면 마디 파생 오프셋에서 큐가 늘어난다.
2. BPM 이 없으면 **콘솔에 가는 명령이 바이트 동일**하다 — 기본값 120 은 안 쓴다.
3. 쪼갠 큐 하나가 못 묶여도 건너뜀 고지의 개수가 참을 유지한다(카드 t277).
"""

from __future__ import annotations

import json

import pytest

from server.design.cue_density import BAR_UNIT_BARS, bar_milliseconds
from server.design.profile import BpmResolution
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.web.question import (
    ConfirmedSongAnalysis,
    ConfirmedSongSection,
    SongSectionProposal,
    section_label,
)

from .test_looks_tool import _RecordingPort
from .test_songcue_confirmed_default import _AnalysisPort
from .test_songcue_tool import _library, _look, _SongCueStatePort, _tree

_TOOL = "prepare_songcue"
_SHA = "306" + "0" * 61

#: 2026-09-06 실기에서 DSP 가 이 곡에서 잰 값(카드 t302). 지어낸 숫자가 아니다.
_MEASURED_BPM = 129.199
_UNIT_MS = bar_milliseconds(_MEASURED_BPM, "4/4") * BAR_UNIT_BARS

#: 구간 셋: 2단위 · 1단위 · 2단위(마지막 구간은 ``end_ms`` 로 길이를 안다).
#: 단위 수를 변주 수(다이내믹스당 룩 2개) 이하로 잡았다 — 넘기면 회전이 한 바퀴
#: 돌아 앞 큐와 같은 큐가 나오고, 그 갈래는 아래 건너뜀 시험이 따로 잰다.
_LONG_SECTIONS = (
    (0, 32_000, 1),
    (32_000, 47_000, 3),
    (47_000, 79_000, 5),
)

#: 첫 구간만 3단위 — 변주 2가지로는 셋째 큐를 다르게 만들 수 없다.
_OVERLONG_SECTIONS = (
    (0, 45_000, 1),
    (45_000, 60_000, 3),
    (60_000, 79_000, 5),
)


def _section(index: int, start_ms: int, end_ms: int, d_level: int) -> ConfirmedSongSection:
    proposal = SongSectionProposal(start_ms=start_ms, end_ms=end_ms, d_level=d_level)
    return ConfirmedSongSection(
        index=index,
        label=section_label(proposal),
        start_ms=start_ms,
        end_ms=end_ms,
        d_level=d_level,
        selected=True,
    )


def _record(*, bpm: float | None, source: str = "measured", sections=_LONG_SECTIONS):
    return ConfirmedSongAnalysis(
        source_sha256=_SHA,
        source_file_name="synth_128bpm.wav",
        confirmed_at="2026-09-06T12:00:00+00:00",
        bpm=BpmResolution(bpm=bpm, source=source, reason="채택 우선순위."),
        sections=tuple(_section(i, *spec) for i, spec in enumerate(sections)),
    )


def _multi_look_library():
    """다이내믹스마다 룩을 **둘씩** — 이어지는 큐가 돌려 쓸 변주가 있어야 쪼개진다.

    ``Dimmer`` 값이 룩마다 달라서, 어느 룩이 어느 큐에 실렸는지 명령 문면의
    ``Attribute 'Dimmer' At <값>`` 줄로 읽힌다.
    """
    looks = []
    for level in range(1, 6):
        looks.append(_look(f"d{level}a", dynamics=level, value=level * 10))
        looks.append(_look(f"d{level}b", dynamics=level, value=level * 10 + 5))
    return _library(*looks)


def _run(*, record, library=None):
    port = _RecordingPort()
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree()),
        look_library=library if library is not None else _multi_look_library(),
        song_analysis=_AnalysisPort(record),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t306",
            name=_TOOL,
            arguments={"song_title": "Density", "genre": "록", "timecode_number": 7},
        )
    )
    return port, json.loads(execution.result.content), execution


def _store_lines(port) -> list[str]:
    return [command for command in port.executed if command.startswith("Store Sequence ")]


def _trig_times(payload) -> list[float]:
    """자동 진행 명령이 실은 큐별 시작 초 — 오프셋의 관측 지점."""
    times = []
    for command in payload["timing"]["auto_advance_commands"]:
        if "'TrigTime'" in command:
            times.append(float(command.rsplit(" ", 1)[1]))
    return times


class TestMeasuredBpmSplitsTheUploadPath:
    def test_cues_outnumber_sections_at_bar_derived_offsets(self):
        """구간 3건이 큐 5건이 되고, 오프셋은 8마디 간격이다."""
        port, payload, _execution = _run(record=_record(bpm=_MEASURED_BPM))

        assert payload["cue_density"]["section_count"] == 3
        assert payload["cue_density"]["cue_count"] == 5
        assert payload["cue_density"]["bpm"] == pytest.approx(_MEASURED_BPM)
        assert payload["cue_density"]["bpm_source"] == "measured"
        assert len(_store_lines(port)) == 5

        # 2단위 · 1단위 · 2단위. 오프셋은 구간 시작 + k × 8마디.
        unit_s = _UNIT_MS / 1000
        expected = [
            0.0,
            unit_s,
            32.0,
            47.0,
            47.0 + unit_s,
        ]
        assert _trig_times(payload) == pytest.approx(expected, abs=0.001)

    def test_the_continuation_cue_holds_the_d_level_and_rotates_the_look(self):
        """정본의 축 — 강도는 유지하고 그림만 바꾼다(Q060 "강도 유지, 색만 교체")."""
        port, _payload, _execution = _run(record=_record(bpm=_MEASURED_BPM))
        dimmers = [
            float(command.rsplit(" ", 1)[1])
            for command in port.executed
            if command.startswith("Attribute 'Dimmer' At ")
        ]
        # 첫 구간은 D1 → 10 / 15. 같은 다이내믹스라 D 레벨은 유지되고 룩만 돈다.
        assert dimmers[:2] == [10, 15]
        # 세 번째 구간은 D5 → 50 / 55.
        assert dimmers[-2:] == [50, 55]

    def test_the_last_section_splits_because_the_record_knows_where_it_ends(self):
        """확정 기록은 구간마다 ``end_ms`` 를 들고 있다 — 인터뷰 경로엔 없는 재료."""
        _port, payload, _execution = _run(record=_record(bpm=_MEASURED_BPM))
        assert payload["cue_density"]["song_end_ms"] == 79_000
        # 마지막 구간(47_000~79_000, 2단위)이 큐 둘을 냈다.
        assert _trig_times(payload)[-2:] == pytest.approx([47.0, 47.0 + _UNIT_MS / 1000], abs=0.001)

    def test_a_single_look_dynamics_is_not_split_and_says_why(self):
        """돌려 놓을 룩이 하나뿐이면 쪼개지 않는다 — 같은 큐 둘은 큐 하나보다 나쁘다."""
        single = _library(*(_look(f"d{n}", dynamics=n, value=n * 10) for n in range(1, 6)))
        _port, payload, _execution = _run(record=_record(bpm=_MEASURED_BPM), library=single)
        assert payload["cue_density"]["cue_count"] == 3
        notes = payload["cue_density"]["notes"]
        assert any("쓸 수 있는 룩이 하나뿐" in note for note in notes)


class TestNoMeasuredBpmIsByteIdentical:
    """BPM 이 없으면 오늘과 **바이트 동일**하다. 기본값 120 은 마디 계산에 안 쓴다."""

    @pytest.mark.parametrize("source", ["default", "sheet"])
    def test_commands_match_the_unsplit_baseline(self, source: str):
        split_port, split_payload, _split_exec = _run(record=_record(bpm=_MEASURED_BPM))
        flat_port, flat_payload, _flat_exec = _run(record=_record(bpm=None, source=source))

        assert flat_payload["cue_density"]["cue_count"] == 3
        assert len(_store_lines(flat_port)) == 3
        assert any("BPM 미선언" in note for note in flat_payload["cue_density"]["notes"])
        # 쪼개진 회차와 달라야 이 시험이 무언가를 재고 있다는 뜻이다.
        assert len(_store_lines(split_port)) == 5

        # 구간 하나에 큐 하나 — 저장 줄의 큐 번호가 1..3 이고 그게 전부다.
        assert [line.split(" Cue ")[1].split(" ")[0] for line in _store_lines(flat_port)] == [
            "1",
            "2",
            "3",
        ]
        assert _trig_times(flat_payload) == pytest.approx([0.0, 32.0, 47.0])

    def test_a_sheet_bpm_still_splits_when_it_carries_a_value(self):
        """``source`` 로 거르지 않는다 — 사람이 카드에서 확정한 템포면 쓴다."""
        _port, payload, _execution = _run(record=_record(bpm=_MEASURED_BPM, source="sheet"))
        assert payload["cue_density"]["cue_count"] == 5
        assert payload["cue_density"]["bpm_source"] == "sheet"


class TestSkipAccountingSurvivesTheSplit:
    """카드 t277 — 사라진 큐는 어느 표에도 안 나타난다. 큐가 늘어도 그건 안 변한다."""

    def test_the_notice_counts_cues_not_sections_when_a_split_cue_cannot_bind(self):
        """단위 수가 변주 수를 넘으면 셋째 큐가 첫 큐와 같아져 접힌다 — 고지가 그걸 센다.

        이 갈래는 t305 가 시험으로 못박은 판단(``test_a_two_colour_section_is_split``:
        4단위 · 2색 → 큐 4건)의 뒷면이다. 상한을 씌우면 사라지지만 그것은 이
        카드의 범위 밖이라 **고치지 않고**, 대신 조용히 사라지지 않는다는 것을
        여기서 못박는다.
        """
        port, payload, execution = _run(
            record=_record(bpm=_MEASURED_BPM, sections=_OVERLONG_SECTIONS)
        )

        density = payload["cue_density"]
        assert density["cue_count"] == 5  # D1 3큐 + D3 1큐 + D5 1큐
        stored = len(_store_lines(port))
        assert stored == 4, "접힌 큐가 없으면 이 시험은 아무것도 안 잰다"

        notice = execution.operator_notice
        assert notice.startswith(f"구간 {density['cue_count']}건 중 큐 {stored}건만 저장했습니다")
        # 보고의 큐 수와 실제 저장 줄 수가 갈리면 고지가 거짓말을 한 것이다.
        assert len(payload["report"]["generated_cues"]) == stored
        assert payload["report"]["summary"]["section_count"] == density["cue_count"]

    def test_a_role_that_the_rig_cannot_bind_is_reported_the_same_way_split_or_not(self):
        """묶이는 룩이 하나도 없는 다이내믹스는 쪼갠 큐에서도 같은 사유로 남는다."""
        library = _library(
            _look("d1", dynamics=1, value=10, roles=("존재하지않는역할",)),
            *(_look(f"d{n}", dynamics=n, value=n * 10) for n in range(2, 6)),
        )
        port, payload, execution = _run(record=_record(bpm=_MEASURED_BPM), library=library)

        # D1 은 룩이 하나뿐이라 쪼개지지 않고, 그 하나가 못 묶여 큐가 안 선다.
        assert payload["cue_density"]["cue_count"] == 3
        assert len(_store_lines(port)) == 2
        assert execution.operator_notice.startswith("구간 3건 중 큐 2건만 저장했습니다")
