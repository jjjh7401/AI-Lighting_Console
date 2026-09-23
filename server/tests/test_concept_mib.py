"""MIB(사전 이동) 시퀀스 판정 시험 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-062~067,
카드 t438).

제약 3 검증(단일 지점 상수): 이 파일의 마지막 클래스가 ``mib.py`` 소스에
``1.5``/``0.5`` 리터럴이 없는지 grep 한다 — mutation 확인은 progress.md
에 기록한다(일시적으로 리터럴을 넣어 이 시험이 실패하는 것을 보인 뒤
되돌림).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.concept.cue_model import CueState, MibVerdict
from server.concept.mib import (
    LIVE_MOVE_ANNOTATION,
    MOVER_HOLD_SECTIONS,
    compute_mib_sequence,
    live_move_note,
    mark_cue_spec,
    movers_off_ops,
    resolve_position,
)
from server.concept.resolver import MOVE_SECONDS, SETTLE_SECONDS

MOVERS = ("MOVER-U", "MOVER-D")


def _state(dim=None, pos="home"):
    return CueState(dim=dim or {}, color=None, pos=pos, motion=0)


class TestComputeMibSequence:
    """REQ-LDDESIGN-062/067 — resolver.mib_verdict 를 재사용한 시퀀스 판정."""

    def test_no_position_change_is_none(self):
        states = [_state(pos="home"), _state(pos="home")]
        verdicts = compute_mib_sequence(states, [0.0, 5.0], movers=MOVERS)
        assert verdicts[1] is None

    def test_dark_when_movers_stay_off(self):
        states = [
            _state(dim={"MOVER-U": 0}, pos="home"),
            _state(dim={"MOVER-U": 0}, pos="back"),
        ]
        verdicts = compute_mib_sequence(states, [0.0, 3.0], movers=MOVERS)
        assert verdicts[1].status == "dark"

    def test_off_since_advances_when_movers_turn_off_then_back_on(self):
        states = [
            _state(dim={"MOVER-U": 50}, pos="home"),
            _state(dim={"MOVER-U": 0}, pos="home"),
            _state(dim={"MOVER-U": 50}, pos="back"),
        ]
        gap = MOVE_SECONDS + SETTLE_SECONDS + 1.0
        verdicts = compute_mib_sequence(states, [0.0, 10.0, 10.0 + gap], movers=MOVERS)
        assert verdicts[2].status == "mark"
        assert verdicts[2].mark_insert_at is not None

    def test_live_when_movers_stay_on(self):
        states = [
            _state(dim={"MOVER-U": 50}, pos="home"),
            _state(dim={"MOVER-U": 50}, pos="back"),
        ]
        verdicts = compute_mib_sequence(states, [0.0, 1.0], movers=MOVERS)
        assert verdicts[1].status == "live"


class TestMarkCueSpec:
    """REQ-LDDESIGN-063 — mark 판정마다 Mark 큐(포지션만, 밝기 0 유지)."""

    def test_builds_position_only_ops(self):
        verdict = MibVerdict(status="mark", window_seconds=2.5, mark_insert_at=42.0)
        spec = mark_cue_spec(verdict, pos="back")
        assert spec["ts"] == 42.0
        assert spec["ops"] == [{"op": "retain", "pos": "back"}]

    def test_rejects_non_mark_verdict(self):
        verdict = MibVerdict(status="dark", window_seconds=2.5, mark_insert_at=None)
        with pytest.raises(ValueError):
            mark_cue_spec(verdict, pos="back")


class TestMoversOffOps:
    """REQ-LDDESIGN-064 — 절·브릿지에서 무버를 소등한 뒤 어두운 창에서
    포지션을 옮긴다."""

    def test_verse_turns_off_movers(self):
        ops = movers_off_ops("Verse", MOVERS)
        assert ops == [{"op": "remove", "roles": list(MOVERS)}]

    def test_bridge_turns_off_movers(self):
        assert movers_off_ops("Bridge", MOVERS) is not None

    def test_chorus_returns_none(self):
        assert movers_off_ops("Chorus", MOVERS) is None

    def test_hold_sections_are_exactly_verse_and_bridge(self):
        assert frozenset({"Verse", "Bridge"}) == MOVER_HOLD_SECTIONS


class TestResolvePosition:
    """REQ-LDDESIGN-065 — 어두운 창이 없으면(연속 후렴·연속 브릿지) 포지션을
    유지해 변화 자체가 없어야 한다 — 두 번째 판정 함수를 만들지 않고
    resolver.mib_verdict 를 재사용해 판정한다(REQ-067 과 같은 원칙)."""

    def test_holds_position_when_movers_on(self):
        prev = _state(dim={"MOVER-U": 50}, pos="home")
        pos, verdict = resolve_position("back", prev, ts=1.0, dark_since=0.0, movers=MOVERS)
        assert pos == "home"
        assert verdict is None

    def test_allows_position_when_dark(self):
        prev = _state(dim={"MOVER-U": 0}, pos="home")
        pos, verdict = resolve_position("back", prev, ts=5.0, dark_since=0.0, movers=MOVERS)
        assert pos == "back"
        assert verdict.status == "dark"

    def test_long_dark_window_still_resolves_dark_not_mark(self):
        """resolve_position 은 포지션만 바꿔 보는 프로브다 — dim 은 바꾸지
        않는다. 따라서 무버가 꺼진 채라면 창이 아무리 길어도 판정은
        늘 dark 다(무버가 같은 큐에서 함께 켜지는 mark 케이스는 이
        함수의 프로브 범위 밖이다 — mib.py resolve_position 독스트링)."""
        prev = _state(dim={"MOVER-U": 0}, pos="home")
        gap = MOVE_SECONDS + SETTLE_SECONDS + 1.0
        pos, verdict = resolve_position("back", prev, ts=gap, dark_since=0.0, movers=MOVERS)
        assert pos == "back"
        assert verdict.status == "dark"


class TestLiveMoveNote:
    """REQ-LDDESIGN-066 — live 판정 설명에 live_move 표시 + 대안 제안."""

    def test_contains_live_move_marker(self):
        assert LIVE_MOVE_ANNOTATION in live_move_note()

    def test_contains_alternative_suggestion(self):
        note = live_move_note()
        assert "느린 포지션 페이드" in note or "구조 재배치" in note

    def test_custom_alternative_overridable(self):
        note = live_move_note(alternative="테스트 대안")
        assert "테스트 대안" in note


class TestNoLiteralConstantRedefinition:
    """제약 3 — mib.py 는 MOVE_SECONDS/SETTLE_SECONDS 를 resolver.py 에서만
    가져온다(단일 지점) — 1.5/0.5 리터럴을 다시 적지 않는다."""

    def test_no_1_5_or_0_5_literal_in_source(self):
        src = Path("server/concept/mib.py").read_text(encoding="utf-8")
        assert "1.5" not in src
        assert "0.5" not in src
