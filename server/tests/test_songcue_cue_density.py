"""카드 t306 — 업로드 경로도 마디 경계에서 쪼갠다.

t305 는 감독 인터뷰 경로(``_song_design_interview`` → ``_build_unified_song_plan``)
만 쪼갰다. 이 파일은 **업로드 경로**(오디오 업로드 → ``analyse_song_audio`` →
확인 카드 → ``prepare_songcue``)가 같은 규칙을 타는지 잰다.

콘솔 접촉 0건 — 가짜 실행 포트와 가짜 상태 포트 위에서만 돈다.

세 가지를 못박는다:

1. 측정 BPM 이 있으면 마디 파생 오프셋에서 큐가 늘어난다.
2. BPM 이 없으면 쪼개지 않는다 — 기본값 120 은 안 쓴다.
3. 확정 기록은 곡 끝을 알므로 마지막 구간도 쪼갤 수 있다.

카드 t480 — 업로드 길이 대화 길 조립기로 합쳐졌다(감독 결정 2026-09-28). 쪼개는
규칙도 대화 길과 **같은 함수**(``_split_sections_for_density`` — 팔레트 색 수 기준)다.
그래서 예전 룩 후보 수 기준 시험(룩이 하나면 안 쪼갬, 못 묶이는 룩이 접힘)은 뺐고,
세 성질은 조립기 규칙으로 다시 잰다. 기본 색 운용(modulate)은 후렴·피날레의 주색을
고정해 두 색이면 쪼개지 않는다(t445) — 그래서 마지막 구간 분할은 주색을 고정하지
않는 ``split_swap`` 으로 잰다.
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
#: 단위 수를 변주 수(다이내믹스당 룩 2개) 이하로 잡았다 — 넘겨도 t307 의 상한이
#: 변주 수까지 잘라내므로 큐 수는 같아진다.
_LONG_SECTIONS = (
    (0, 32_000, 1),
    (32_000, 47_000, 3),
    (47_000, 79_000, 5),
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


def _run_with_usage(record, color_usage: str):
    """인터뷰 기록(Q2 팔레트 + Q2B 색 운용)이 있는 세션으로 돌린다."""
    from .test_chorus_color_two_paths_t441 import _records, _RecordsPort

    port = _RecordingPort()
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree()),
        look_library=_multi_look_library(),
        song_analysis=_AnalysisPort(record),
        interview_records=_RecordsPort(_records(color_usage)),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t306-usage",
            name=_TOOL,
            arguments={"song_title": "Density", "genre": "록", "timecode_number": 7},
        )
    )
    return port, json.loads(execution.result.content), execution


def _d_levels(payload) -> list[int]:
    return [cue["d_level"] for cue in payload["report"]["generated_cues"]]


def _colour_lines(port) -> list[str]:
    return [command for command in port.executed if "ColorRGB_R" in command]


class TestMeasuredBpmSplitsTheUploadPath:
    def test_cues_outnumber_sections_at_bar_derived_offsets(self):
        """구간 3건이 큐 4건이 되고, 오프셋은 8마디 간격이다.

        2단위 · 1단위 · 2단위 중 첫 구간(D1)이 둘로 갈린다. 마지막 구간(D5, 피날레)은
        기본 색 운용(modulate)이 주색을 고정해 두 색 팔레트로는 쪼갤 색이 없어 한
        큐로 남는다(t445 — 대화 길과 같은 규칙).
        """
        port, payload, _execution = _run(record=_record(bpm=_MEASURED_BPM))

        assert payload["cue_density"]["section_count"] == 3
        assert payload["cue_density"]["cue_count"] == 4
        assert payload["cue_density"]["bpm"] == pytest.approx(_MEASURED_BPM)
        assert payload["cue_density"]["bpm_source"] == "measured"
        assert len(_store_lines(port)) == 4

        unit_s = _UNIT_MS / 1000
        assert _trig_times(payload) == pytest.approx([0.0, unit_s, 32.0, 47.0], abs=0.001)

    def test_the_continuation_cue_holds_the_d_level_and_rotates_the_colour(self):
        """정본의 축 — 강도는 유지하고 그림만 바꾼다(Q060 "강도 유지, 색만 교체")."""
        port, payload, _execution = _run(record=_record(bpm=_MEASURED_BPM))
        # 첫 구간(D1)이 두 큐로 갈렸다 — 둘 다 D1 이고 색 줄이 다르다.
        assert _d_levels(payload)[:2] == [1, 1]
        colours = _colour_lines(port)
        assert colours[0] != colours[1]

    def test_the_last_section_splits_because_the_record_knows_where_it_ends(self):
        """확정 기록은 구간마다 ``end_ms`` 를 들고 있다 — 인터뷰 경로엔 없는 재료.

        주색을 고정하지 않는 색 운용(``split_swap``)이면 마지막 구간(47_000~79_000,
        2단위)도 큐 둘을 낸다 — 곡 끝(79_000)을 알기 때문이다.
        """
        _port, payload, _execution = _run_with_usage(_record(bpm=_MEASURED_BPM), "split_swap")
        assert payload["cue_density"]["song_end_ms"] == 79_000
        assert payload["cue_density"]["cue_count"] == 5
        assert _trig_times(payload)[-2:] == pytest.approx([47.0, 47.0 + _UNIT_MS / 1000], abs=0.001)


class TestNoMeasuredBpmDoesNotSplit:
    """BPM 이 없으면 쪼개지 않는다. 기본값 120 은 마디 계산에 안 쓴다."""

    @pytest.mark.parametrize("source", ["default", "sheet"])
    def test_one_cue_per_section_without_a_bpm(self, source: str):
        split_port, _split_payload, _split_exec = _run(record=_record(bpm=_MEASURED_BPM))
        flat_port, flat_payload, _flat_exec = _run(record=_record(bpm=None, source=source))

        assert flat_payload["cue_density"]["cue_count"] == 3
        assert len(_store_lines(flat_port)) == 3
        assert any("BPM 미선언" in note for note in flat_payload["cue_density"]["notes"])
        # 쪼개진 회차와 달라야 이 시험이 무언가를 재고 있다는 뜻이다.
        assert len(_store_lines(split_port)) == 4

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
        assert payload["cue_density"]["cue_count"] == 4
        assert payload["cue_density"]["bpm_source"] == "sheet"


# 카드 t480 — ``TestSkipAccountingSurvivesTheSplit`` 두 시험은 뺐다. 룩 후보가 리그에
# 안 묶여 쪼갠 큐가 접히거나 저장되지 않는 갈래를 쟀는데, 업로드 길이 조립기로 합쳐지며
# 큐가 패치된 기구 번호에 저장되므로(감독 결정 D1) 그 갈래를 만드는 입력이 없다.
