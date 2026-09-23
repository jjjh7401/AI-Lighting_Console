"""카드 t439 — SPEC-LDDESIGN-001 M6 §④b. 컨셉 v2 파이프라인이
``prepare_songcue``(사다리 경로) 진입점을 통해 실제로 배선됐는가.

``test_songcue_bpm_production_wiring.py`` 와 같은 원칙 — ``build_concept_
report_from_songcue_sections`` 를 직접 부르는 게 아니라 **공개 진입점을
통해서만** 잰다(직접 부르면 배선 결함을 재현하지 못한다). 콘솔 접촉 0건
— 가짜 실행 포트와 가짜 상태 포트 위에서만 돈다.

ADDITIVE 원칙 확인이 이 파일의 핵심이다: ``concept_report`` 가
``available: False`` 든(파이프라인 예외 — 카드 t452 전에는 6연속 Chorus
픽스처가 g9 사각지대로 이를 냈다) ``available: True`` 든,
어느 쪽도 콘솔 명령 생성 자체(``is_error``·저장된 큐 수)에 영향을 주지
않는다.
"""

from __future__ import annotations

import json

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset

from .test_looks_resolver import LXSEQ_RIG
from .test_looks_tool import _RecordingPort
from .test_songcue_bpm_production_wiring import _chorus_library, _record
from .test_songcue_confirmed_default import _AnalysisPort
from .test_songcue_tool import _SongCueStatePort, _tree

_LXSEQ_GROUPS: tuple[tuple[int, str], ...] = tuple(
    (index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG)
)
_SIX_CHORUSES = tuple({"name": "Chorus", "start": f"{minute}:00"} for minute in range(6))


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
            id="t439-songcue-wiring",
            name="prepare_songcue",
            arguments={
                "song_title": "Concept Report Wiring",
                "genre": "록",
                "timecode_number": 7,
                "sections": list(_SIX_CHORUSES),
            },
        )
    )
    return port, json.loads(execution.result.content), execution


class TestConceptReportKeyIsAlwaysPresent:
    """REQ-073/074 §④b — ``prepare_songcue`` 의 반환 payload 는 항상
    ``concept_report`` 키를 갖는다(성공/무명령 두 반환 갈래 모두
    ``songconfirm_fields`` 를 펼치므로)."""

    def test_bpm_declared_payload_has_concept_report(self) -> None:
        port, payload, execution = _run(bpm=120.0)
        assert not execution.result.is_error, execution.result.content
        assert "concept_report" in payload
        assert "available" in payload["concept_report"]

    def test_bpm_undeclared_payload_still_has_concept_report_unavailable(self) -> None:
        port, payload, execution = _run(bpm=None)
        assert not execution.result.is_error, execution.result.content
        assert payload["concept_report"] == {
            "available": False,
            "reason": "BPM이 선언되지 않았다 — 컨셉 파이프라인의 마디 계산 전제가 없다",
        }


class TestConceptReportIsAdditiveNotBreaking:
    """컨셉 파이프라인이 예외를 던져도 콘솔 명령 경로는 그대로 간다는
    것을 진입점 레벨에서 확인한다. (이 카드가 처음 쓴 실패 유발원 —
    6연속 Chorus 가 Outro 없이 끝나 g9 이 ``VocabError`` — 은 카드 t452 가
    고쳤으므로, 실패는 ``build_song`` 을 바꿔치기해 일으킨다.)"""

    def test_concept_report_unavailable_does_not_block_console_commands(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(raw_song):
            raise RuntimeError("t452 주입 실패")

        monkeypatch.setattr("server.concept.session_bridge.build_song", _boom)
        port, payload, execution = _run(bpm=120.0)
        assert not execution.result.is_error, execution.result.content
        assert payload["concept_report"]["available"] is False
        assert "t452 주입 실패" in payload["concept_report"]["reason"]
        stored = [line for line in port.executed if line.startswith("Store Sequence ")]
        assert len(stored) > 0, "concept_report 실패가 콘솔 명령 생성을 막으면 안 된다"

    def test_baseline_console_command_count_unchanged_regardless_of_concept_report(
        self,
    ) -> None:
        # `test_songcue_bpm_production_wiring.py` 가 이미 고정한 기준값(6
        # 구간 → 6큐, BPM 없을 때)과 같은 수를 다시 재서, concept_report
        # 배선이 그 기존 회귀 시험이 지키던 값을 조용히 바꾸지 않았다는
        # 것을 이 파일 자신도 확인한다.
        port, payload, execution = _run(bpm=None)
        assert not execution.result.is_error, execution.result.content
        assert len(payload["report"]["generated_cues"]) == 6
