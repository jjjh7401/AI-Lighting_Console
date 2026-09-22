"""카드 t428 — 곡 BPM 이 큐 번들 조립까지 실제로 배선되는가.

``build_songcue_bundle`` 은 ``bpm`` 키워드 인자를 받아 절정 지속시간 상한
(REQ-LDCLIMAX-006~009, ``server/looks/songcue.py`` 의 ``_apply_climax_duration_cap``)
을 계산한다. 그런데 이 함수의 유일한 실서비스 호출자인 ``prepare_songcue``
(``server/orchestrator/tools.py``)는 이 인자를 **주지 않았다** — 이미 같은 함수
안에서 마디 분할에 쓰던 ``density_bpm`` (``_confirmed_density_bpm(confirmed)``)이
53줄 위에 있는데도 ``build_songcue_bundle`` 호출에는 실리지 않았다. 그 결과
상한 메커니즘은 ``test_songcue_climax_001.py`` 가 함수를 직접 부르는 시험에서만
돌았을 뿐, 실기로 나가는 어느 곡에서도 한 번도 발화한 적이 없다.

이 파일은 그 배선을 **``prepare_songcue`` 진입점을 통해서만** 잰다 —
``build_songcue_bundle`` 을 직접 부르면 이 결함을 재현하지 못한다(고치기 전에도
통과했을 시험이기 때문이다). 콘솔 접촉 0건 — 가짜 실행 포트와 가짜 상태
포트 위에서만 돈다.
"""

from __future__ import annotations

import json

from server.design.profile import BpmResolution
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.web.question import ConfirmedSongAnalysis

from .test_looks_resolver import LXSEQ_RIG
from .test_looks_tool import _RecordingPort
from .test_songcue_confirmed_default import _AnalysisPort
from .test_songcue_tool import _library, _look, _SongCueStatePort, _tree

_TOOL = "prepare_songcue"
_SHA = "428" + "0" * 61

#: 실기 리그(``test_songcue_climax_001.py`` 와 같은 자료) — BLIND 그룹이 있어야
#: 사다리가 blinder_or_flash 칸에 닿을 수 있다(``_FULL_GROUPS`` 에는 없다).
_LXSEQ_GROUPS: tuple[tuple[int, str], ...] = tuple(
    (index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG)
)

#: 코러스 여섯 회차, 1분 간격 — ``test_songcue_climax_001.py``
#: ``TestClimaxDurationCapIsWiredThroughBuildSongcueBundle`` 이 쓰는 것과 같은
#: 픽스처다. 같은 룩이 반복되면 사다리 회전이 여섯 번째 회차까지 블라인더 칸에
#: 닿는다(그 파일의 주석 실측).
_SIX_CHORUSES = tuple({"name": "Chorus", "start": f"{minute}:00"} for minute in range(6))


def _record(*, bpm: float | None) -> ConfirmedSongAnalysis:
    return ConfirmedSongAnalysis(
        source_sha256=_SHA,
        source_file_name="wiring_t428.wav",
        confirmed_at="2026-09-22T00:00:00+00:00",
        bpm=BpmResolution(bpm=bpm, source="measured", reason="카드 t428 배선 시험."),
        sections=(),
    )


def _chorus_library():
    """다이내믹스 4·5 대역(코러스)에 룩 하나만 — 마디 분할이 끼어들지 않게 한다.

    변주(``dynamics_matches``)가 하나뿐이면 ``split_selections_for_density`` 가
    쪼개지 않으므로(``cue_density.py`` "쓸 수 있는 룩이 하나뿐이면 쪼개지 않는다"),
    이 시험이 재는 성질(절정 지속시간 상한)이 마디 분할과 뒤섞이지 않는다.
    """
    return _library(_look("chorus", dynamics=5, value=60))


def _run(*, bpm: float | None):
    port = _RecordingPort()
    record = None if bpm is None else _record(bpm=bpm)
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree(groups=_LXSEQ_GROUPS)),
        look_library=_chorus_library(),
        song_analysis=_AnalysisPort(record),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t428",
            name=_TOOL,
            arguments={
                "song_title": "BPM Wiring",
                "genre": "록",
                "timecode_number": 7,
                "sections": list(_SIX_CHORUSES),
            },
        )
    )
    return port, json.loads(execution.result.content), execution


class TestConfirmedBpmReachesTheClimaxDurationCap:
    """REQ-LDCLIMAX-006~009 — 확정 기록의 BPM 이 ``prepare_songcue`` 를 거쳐
    절정 지속시간 상한까지 실제로 닿는다(공개 진입점을 통한 배선 확인)."""

    def test_a_confirmed_bpm_inserts_a_climax_return_cue_the_baseline_does_not(self):
        """BPM 이 없으면(``song_analysis`` 무기록) 큐 6건 그대로다 — 상한이 아무
        것도 안 한다(REQ-LDCLIMAX-009). BPM 이 확정돼 있으면 같은 픽스처가 사다리
        blinder_or_flash 칸에 닿아(주석의 실측) 복귀 큐가 최소 한 장 더 끼워진다.
        큐 수가 갈리지 않으면 이 시험은 배선이 아니라 아무것도 재지 않는다.
        """
        baseline_port, baseline_payload, baseline_execution = _run(bpm=None)
        wired_port, wired_payload, wired_execution = _run(bpm=120.0)

        assert not baseline_execution.result.is_error, baseline_execution.result.content
        assert not wired_execution.result.is_error, wired_execution.result.content

        baseline_cues = len(baseline_payload["report"]["generated_cues"])
        wired_cues = len(wired_payload["report"]["generated_cues"])

        assert baseline_cues == 6, "구간 6건이 큐 6건이어야 상한 분할이 안 섞인 기준선이다"
        assert wired_cues > baseline_cues, (
            "BPM 이 확정돼 있으면 절정 지속시간 상한이 복귀 큐를 끼워 baseline 보다 "
            "큐가 많아져야 한다 — 같으면 'bpm' 이 build_songcue_bundle 에 실려가지 "
            "않은 것이다"
        )

        baseline_stores = [c for c in baseline_port.executed if c.startswith("Store Sequence ")]
        wired_stores = [c for c in wired_port.executed if c.startswith("Store Sequence ")]
        assert len(wired_stores) > len(baseline_stores)
