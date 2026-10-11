"""카드 t598 — 판독~송신 시간차: 승인 창이 떠 있는 사이 콘솔에서 번호가 채워지면 덮어쓴다.

반영(``beat_grid_apply``)은 「⇪ 콘솔에 반영」을 누른 순간 위치 풀을 읽어 빈 slot 에만
``Store Preset 2.n``(t592)을 싣는다. 그런데 그 줄은 감독이 승인한 **뒤** 나간다 —
승인 창이 떠 있는 사이 누가 콘솔에서 그 번호에 프리셋을 저장하면, ``Store Preset``은
경고 없이 덮어쓴다(REQ-LDBEAT-015(i-7)).

리드 결정(2026-10-12): 송신 직전(승인 뒤·실행 전) 만들 번호의 풀을 다시 읽어, 하나라도
이제 채워졌거나 다시 못 읽으면 **묶음 전체 0줄** + 사유. 줄 단위로 빼면 승인≠송신이
되므로 lock-first(승인 중 잠금 → 묶음 전체 중단) 선례를 따른다. 콘솔 쓰기 0건(가짜 콘솔).
"""

from __future__ import annotations

from server.design.beat_grid import check_evidence_approval
from server.safety.audit import AuditLog
from server.safety.gate import BatchRisk, SafetyGate
from server.web.session import SongTimelineStore

from .test_apply_time_approval_t577 import _cue_of, _new_session, _state_tree, _timeline
from .test_position_preset_create_t592 import _FRAMES, _MEMBERS, _RECIPE, _pool
from .test_safety_gate import FakeConsole, ScriptedApproval

_POOL2 = "DataPool/PresetPools/2"
_POSITION_CUE = {"bar": 1, "position_preset_no": "2.71", "evidence": None}


def _apply(tmp_path, during_approval):
    """2.71 이 빈 위치 풀(1·2 만)에서 반영을 누르고, 승인 창 안에서
    ``during_approval(console)``이 콘솔 상태를 바꾼다."""
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = [dict(_POSITION_CUE)]
    timeline["beat_grid"].update(_RECIPE)
    tree = _state_tree()
    tree[_POOL2] = _pool(_POOL2, [1, 2])
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    session._beat_grid_group_members = lambda names: {
        n: _MEMBERS[n] for n in names if n in _MEMBERS
    }
    session._beat_grid_pointing_frames = lambda: _FRAMES
    original = approval.request_approval

    def request_approval(request):
        during_approval(console)
        return original(request)

    approval.request_approval = request_approval
    status = session.beat_grid_apply()
    return status, store, approval, console


def _fill_71(console) -> None:
    console.state_tree[_POOL2] = _pool(_POOL2, [1, 2, 71])


def _drop_pool(console) -> None:
    del console.state_tree[_POOL2]


class TestSlotFilledDuringApproval:
    def test_nothing_is_sent_and_the_reason_names_the_number(self, tmp_path) -> None:
        status, store, approval, console = _apply(tmp_path, _fill_71)
        # 승인 카드는 떴다(만들기 줄 포함) — 그 뒤 송신 직전 재판독이 막았다.
        sent_on_card = [item.command for r in approval.requests for item in r.items]
        assert "Store Preset 2.71" in sent_on_card
        assert status["ok"] is False
        assert console.executed == [], "묶음 일부라도 나갔다"
        assert "2.71" in status["reason"]
        assert "채워" in status["reason"]
        assert "다시 반영" in status["reason"]
        # 승인 기록도 없다 — 아무것도 안 나갔으므로.
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is not None


class TestPoolUnreadableOnReread:
    def test_unreadable_reread_also_aborts(self, tmp_path) -> None:
        status, store, _approval, console = _apply(tmp_path, _drop_pool)
        assert status["ok"] is False
        assert console.executed == []
        assert "다시 읽지 못" in status["reason"]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is not None


class TestStillEmptyProceeds:
    def test_unchanged_pool_sends_and_reread_happened(self, tmp_path) -> None:
        reads: list[str] = []

        def watch(console) -> None:
            query = console.query_state

            def counted(path, *args, **kwargs):
                reads.append(path)
                return query(path, *args, **kwargs)

            console.query_state = counted

        status, _store, _approval, console = _apply(tmp_path, watch)
        assert status["ok"] is True
        assert "Store Preset 2.71" in console.executed
        # 승인 창 뒤 송신 직전에 위치 풀을 다시 읽었다.
        assert _POOL2 in reads


class TestGateRecheckHook:
    def _gate(self, tmp_path, approval):
        console = FakeConsole()
        gate = SafetyGate(
            console=console, audit=AuditLog(tmp_path / "audit"), approval_port=approval
        )
        return gate, console

    def test_none_recheck_is_byte_identical(self, tmp_path) -> None:
        commands = ["Fixture 5 At 50", "Store Preset 2.71"]
        gate_a, _ = self._gate(tmp_path / "a", ScriptedApproval([True]))
        gate_b, _ = self._gate(tmp_path / "b", ScriptedApproval([True]))
        plain = gate_a.screen(commands, risk=BatchRisk(reason="r", kind="k"))
        explicit = gate_b.screen(commands, risk=BatchRisk(reason="r", kind="k", recheck=None))
        assert plain == explicit
        assert BatchRisk(reason="r", kind="k") == BatchRisk(reason="r", kind="k", recheck=None)

    def test_recheck_reason_blocks_the_whole_bundle(self, tmp_path) -> None:
        gate, console = self._gate(tmp_path, ScriptedApproval([True]))
        decision = gate.screen(
            ["Fixture 5 At 50", "Store Preset 2.71"],
            risk=BatchRisk(reason="r", kind="k", recheck=lambda: "채워짐"),
        )
        assert decision.cleared is False
        assert decision.status == "blocked_precondition"
        assert decision.notice == "채워짐"
        assert gate.execution_port.execute("Store Preset 2.71").ok is False
        assert console.executed == []

    def test_recheck_runs_only_after_approval(self, tmp_path) -> None:
        calls: list[int] = []
        gate, _ = self._gate(tmp_path, ScriptedApproval([False]))
        gate.screen(
            ["Store Preset 2.71"],
            risk=BatchRisk(reason="r", kind="k", recheck=lambda: calls.append(1)),
        )
        assert calls == [], "거절된 묶음에서 재판독이 돌았다"
