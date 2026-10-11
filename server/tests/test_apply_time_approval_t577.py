"""카드 t577 — 승인 시점을 편집에서 「⇪ 콘솔에 반영」으로 이동
(REQ-LDBEAT-015(h-1)~(h-6), AC-LDBEAT-016(v-1)~(v-5)).

리드 결정(원문, `design/ldbeat-runbook-mockup-20261008.md:37`): 「모든 길은
같은 서버 검사를 거쳐 초안만 바꿈. 콘솔은 「고친 것 콘솔에 반영」 승인
1회(새 프리셋 N개 + 다시 저장할 큐 M개 표시)에서만.」

이 파일은 (v-1)~(v-5) 다섯 시나리오를 가짜 콘솔(``FakeConsole``) + 각본
승인(``ScriptedApproval``)으로 승인=송신 경로 전체를 재현한다 — t563/t572가
쓰는 것과 같은 모양의 세션 레벨 하네스다(이 파일 밖 임포트를 늘리지 않으려
``ScriptedApproval``/타임라인 헬퍼를 짧게 복제한다, t563과 같은 선택).

콘솔 접촉: 0건. ``FakeConsole`` 만 쓰고 실기 포트로는 한 바이트도 나가지
않는다.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid import (
    apply_pending_approval,
    check_evidence_approval,
    pending_preset_approvals,
)
from server.design.beat_grid_edit import apply_beat_grid_edit
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("이 경로는 모델을 부르지 않는다")


class ScriptedApproval:
    """``test_safety_gate.ScriptedApproval``과 같은 모양(t563과 같은 이유로
    이 파일 안에 복제한다 — 결정적이고 짧다)."""

    def __init__(self, decisions=(True,)):
        self.decisions = list(decisions)
        self.requests = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if not self.decisions:
            return False
        return self.decisions.pop(0)


_SEQUENCES_SECTION = {"children": []}
_TIMECODE_POOL_CHILDREN_EMPTY = {"children": [], "node": {"childCount": 0, "enumeration": "ok"}}


def _bar_map(bpm: float = 112.35, beats_per_bar: int = 4) -> dict:
    return {
        "bpm": bpm,
        "time_signature": [beats_per_bar, 4],
        "bars": [
            {"bar": n, "start_ms": 1000 + (n - 1) * 2000, "beats_ms": [1000 + (n - 1) * 2000]}
            for n in range(1, 30)
        ],
    }


def _state_tree() -> dict:
    return {
        "DataPool/Sequences": _SEQUENCES_SECTION,
        "DataPool/Timecodes": _TIMECODE_POOL_CHILDREN_EMPTY,
    }


def _timeline(**overrides: object) -> dict:
    """BACK bar 1 에 승인 없는(``evidence`` 없음) ``effect_preset_no``
    하나(= (v-1)이 남긴 승인 대기 칸·필드)만 가진 최소 격자."""
    base: dict[str, object] = {
        "song_title": "LOVE ATTACK",
        "sequence_number": 210,
        "bar_map": _bar_map(),
        "timecode_number": 20,
        "beat_grid": {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [
                        {
                            "bar": 1,
                            "effect_preset_no": "4.21",
                            "effect_kind": "position",
                            "evidence": None,
                        }
                    ],
                }
            ],
            "probe_results": {1: "통과", 2: "통과", 4: "통과", 5: "통과", 7: "통과", 9: "통과"},
        },
    }
    base.update(overrides)
    return base


def _new_session(
    tmp_path,
    *,
    store: SongTimelineStore,
    decisions=(True, True, True, True, True),
    state_tree: dict | None = None,
    sent: list[dict] | None = None,
):
    console = FakeConsole(state_tree=state_tree if state_tree is not None else _state_tree())
    audit = AuditLog(tmp_path / "audit")
    approval = ScriptedApproval(decisions=decisions)
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    channel = ApprovalChannel(timeout_seconds=1.0)
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=(sent.append if sent is not None else (lambda event: None)),
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console, approval, audit


@pytest.fixture
def harness(tmp_path):
    store = SongTimelineStore()
    store.latest = _timeline()
    sent: list[dict] = []
    session, console, approval, audit = _new_session(tmp_path, store=store, sent=sent)
    return {
        "tmp_path": tmp_path,
        "store": store,
        "session": session,
        "console": console,
        "approval": approval,
        "audit": audit,
        "sent": sent,
    }


def _cue_of(grid, group_name: str, bar: int) -> dict:
    track = next(t for t in grid["tracks"] if t["group_name"] == group_name)
    return next(c for c in track["cues"] if c["bar"] == bar)


# -- (v-1) 완전한 evidence.approval 없이 새 번호 추가 → 거절되지 않고 ---------
#    승인 대기로 초안에 남는다 (REQ-LDBEAT-015(h-1)) -------------------------


class TestPendingAcceptanceAtEditTime:
    def test_new_number_without_evidence_is_accepted_and_observed_pending(self) -> None:
        from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid

        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        updated, report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="BACK",
            changes={"effect_preset_no": "2.65", "effect_kind": "position"},
        )
        cue = _cue_of(updated, "BACK", 3)
        assert cue["effect_preset_no"] == "2.65"
        # 즉시 거절(BeatGridEditError)되지 않았다는 것 자체가 핵심 — 위
        # 호출이 예외 없이 (updated, report) 를 돌려준 것으로 이미 증명됐다.
        assert check_evidence_approval(cue) is not None, "승인 완전성 없이 통과했다"
        assert any("승인 대기" in line for line in report)
        pending = pending_preset_approvals(updated)
        assert {"BACK", 3} <= {pending[0]["group_name"], pending[0]["bar"]} or any(
            entry["group_name"] == "BACK" and entry["bar"] == 3 for entry in pending
        )


# -- (v-2) 저장된 승인을 새 번호의 근거로 재사용하지 않는다 -------------------
#    (REQ-LDBEAT-015(h-5), 카드 t555/t566 결정 계승) --------------------------


class TestStoredApprovalIsNotReused:
    def test_cell_with_a_stored_approval_stays_pending_for_a_fresh_new_number(self) -> None:
        from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid

        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        pre = _cue_of(grid, "MOVER-U", 3)
        assert pre["evidence"]["approval"] is not None  # t555 밝기 100% 승인

        updated, report = apply_beat_grid_edit(
            grid,
            bar=3,
            target="MOVER-U",
            changes={"effect_preset_no": "2.65", "effect_kind": "position"},
        )
        cue = _cue_of(updated, "MOVER-U", 3)
        assert cue["effect_preset_no"] == "2.65"
        assert check_evidence_approval(cue) is not None, "저장된 승인이 새 번호를 통과시켰다"
        assert any("승인 대기" in line for line in report)


# -- (v-3) 「⇪ 콘솔에 반영」 승인 카드가 승인 대기를 "새로 만드는 프리셋 N개"로
#    열거하고, 승인되면 그 칸·필드에 한해 정확히 evidence.approval을 기록한다
#    (REQ-LDBEAT-015(h-2)(h-3)) ------------------------------------------------


class TestApprovalCardEnumeratesPendingAndRecordsEvidence:
    def test_risk_reason_lists_the_pending_preset_number(self, harness) -> None:
        session = harness["session"]
        event = session.beat_grid_apply()
        assert event["ok"] is True
        assert len(harness["approval"].requests) == 1
        risk_reasons = harness["approval"].requests[0].items[0].risk_reasons
        joined = " ".join(risk_reasons)
        assert "새로 만드는 프리셋 1개" in joined
        assert "BACK" in joined
        assert "1마디" in joined
        assert "4.21" in joined

    def test_approval_writes_evidence_only_on_the_enumerated_cell(self, harness) -> None:
        session = harness["session"]
        store = harness["store"]
        session.beat_grid_apply()
        updated_grid = store.latest["beat_grid"]
        cue = _cue_of(updated_grid, "BACK", 1)
        approval = cue["evidence"]["approval"]
        assert approval["by"] == "supervisor"
        assert approval["date"]
        assert approval["source"]
        assert check_evidence_approval(cue) is None, "승인 뒤에도 여전히 승인 대기로 보인다"

    def test_declined_card_writes_no_evidence_and_sends_nothing(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, approval, _audit = _new_session(tmp_path, store=store, decisions=(False,))
        event = session.beat_grid_apply()
        assert event["ok"] is False
        assert console.executed == []
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert cue["evidence"] is None
        assert check_evidence_approval(cue) is not None


# -- (v-4) 카드가 구성된 뒤 추가된 새 번호는 이번 반영에서 0 송신이고, -------
#    여전히 승인 대기로 남는다 (REQ-LDBEAT-015(h-4)) --------------------------


class TestNumbersAddedAfterCardConstructionStayPending:
    def test_apply_pending_approval_only_touches_the_enumerated_set(self) -> None:
        # 카드 구성 시점의 grid(=card_time_grid)에는 BACK 1마디만 승인 대기다
        # — 그 뒤 다른 편집으로 SIDE-ALL 5마디가 추가로 승인 대기가 됐다고
        # 가정한다(반영 시점의 grid=later_grid). `apply_pending_approval`은
        # `pending`(카드가 실제로 열거한 집합)에 **없는** SIDE-ALL 5마디를
        # 건드리지 않아야 한다 — 그 칸은 다음 반영까지 승인 대기로 남는다.
        card_time_grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "cues": [
                        {
                            "bar": 1,
                            "effect_preset_no": "4.21",
                            "effect_kind": "position",
                            "evidence": None,
                        }
                    ],
                }
            ]
        }
        pending = pending_preset_approvals(card_time_grid)
        assert len(pending) == 1
        assert pending[0]["group_name"] == "BACK" and pending[0]["bar"] == 1

        later_grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "cues": [
                        {
                            "bar": 1,
                            "effect_preset_no": "4.21",
                            "effect_kind": "position",
                            "evidence": None,
                        }
                    ],
                },
                {
                    "group_name": "SIDE-ALL",
                    "cues": [
                        {
                            "bar": 5,
                            "color_preset_no": "4.99",
                            "evidence": None,
                        }
                    ],
                },
            ]
        }
        approved = apply_pending_approval(
            later_grid,
            pending,
            by="supervisor",
            date="2026-10-11T00:00:00+00:00",
            source="beat_grid_apply:deadbeef",
        )
        back_cue = _cue_of(approved, "BACK", 1)
        side_cue = _cue_of(approved, "SIDE-ALL", 5)
        assert back_cue["evidence"]["approval"]["by"] == "supervisor"
        # 카드가 열거하지 않은 SIDE-ALL 5마디는 바이트까지 그대로다 — 여전히
        # 승인 대기(evidence None, check_evidence_approval 이 non-None).
        assert side_cue["evidence"] is None
        assert check_evidence_approval(side_cue) is not None


# -- (v-5) 승인=송신 비교(REQ-LDBEAT-011)는 이 변경 전후로 동일하게 성립한다
#    (REQ-LDBEAT-015(h-6)) ------------------------------------------------------


class TestApprovalVsSentUnaffected:
    def test_approval_vs_sent_still_matches_with_a_pending_cell_present(self, harness) -> None:
        session = harness["session"]
        status = session.beat_grid_apply()
        assert status["ok"] is True
        assert status["approval_vs_sent"]["match"] is True
