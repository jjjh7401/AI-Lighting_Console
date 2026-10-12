"""카드 t590 — 값이 없는 새 프리셋 번호를 가리키는 칸은 「⇪ 콘솔에 반영」에서
송신 보류(REQ-LDBEAT-015(i-1)(i-2), AC-LDBEAT-016(w-1)~(w-5)).

"새 프리셋 번호" = 반영 시점에 그 번호의 풀(``pool.slot`` 의 pool)을 콘솔에서
완전 판독한 결과 slot 이 없는 번호. 풀을 못 읽으면 같은 보류로 다룬다. 보류는
칸 단위(``evidence.approval`` 이 칸 단위)이고, 보류한 칸에는 승인을 적지 않는다.

하네스는 t577 과 같은 가짜 콘솔(``FakeConsole``) + 각본 승인. 콘솔 접촉 0건.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid import check_evidence_approval, split_empty_preset_holds
from server.web.session import SongTimelineStore

from .test_apply_time_approval_t577 import _cue_of, _new_session, _state_tree, _timeline

_HOLD_LABEL = "빈 프리셋 — 아직 콘솔에 만들 길 없음"


def _pool(path: str, slots: list[int]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": slot, "name": f"P{slot}"} for slot in slots],
    }


def _tree_with_pools(**pools: list[int]) -> dict:
    tree = _state_tree()
    for pool_no, slots in pools.items():
        path = f"DataPool/PresetPools/{pool_no.lstrip('p')}"
        tree[path] = _pool(path, slots)
    return tree


def _timeline_with_cue(cue: dict) -> dict:
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = [cue]
    return timeline


def _apply(tmp_path, timeline: dict, tree: dict):
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    status = session.beat_grid_apply()
    return status, store, console, approval


def _risk_text(approval) -> str:
    return " ".join(approval.requests[0].items[0].risk_reasons)


def _sent_commands(approval) -> list[str]:
    return [item.command for request in approval.requests for item in request.items]


_EMPTY_EFFECT_CUE = {
    "bar": 1,
    "effect_preset_no": "4.99",
    "effect_kind": "position",
    "evidence": None,
}


class TestHoldWhenSlotIsAbsent:
    """(w-1) 풀은 읽혔고 slot 이 없다 → 칸 보류 + 표시 + 승인 기록 없음."""

    def test_card_lists_the_empty_preset_and_not_as_a_new_preset(self, tmp_path) -> None:
        status, _store, _console, approval = _apply(
            tmp_path, _timeline_with_cue(dict(_EMPTY_EFFECT_CUE)), _tree_with_pools(p4=[21])
        )
        assert status["ok"] is False
        assert approval.requests == []
        risk = status["reason"]
        assert _HOLD_LABEL in risk
        assert "4.99" in risk
        assert "새로 만드는 프리셋" not in risk, "보류 칸이 승인 기록 대상 목록에 올랐다"

    def test_no_command_references_the_held_number(self, tmp_path) -> None:
        _status, _store, _console, approval = _apply(
            tmp_path, _timeline_with_cue(dict(_EMPTY_EFFECT_CUE)), _tree_with_pools(p4=[21])
        )
        assert not [c for c in _sent_commands(approval) if "4.99" in c]

    def test_held_cell_gets_no_approval_and_stays_pending(self, tmp_path) -> None:
        _status, store, _console, _approval = _apply(
            tmp_path, _timeline_with_cue(dict(_EMPTY_EFFECT_CUE)), _tree_with_pools(p4=[21])
        )
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert not (cue.get("evidence") or {}).get("approval")
        assert check_evidence_approval(cue) is not None


class TestHoldWhenPoolIsUnreadable:
    """(w-2) 풀을 못 읽으면 비었는지 모른다 → 같은 보류, 다른 문구."""

    def test_unreadable_pool_holds_with_its_own_reason(self, tmp_path) -> None:
        tree = _state_tree()
        tree.pop("DataPool/PresetPools/4", None)
        status, store, _console, approval = _apply(
            tmp_path, _timeline_with_cue(dict(_EMPTY_EFFECT_CUE)), tree
        )
        assert status["ok"] is False
        assert approval.requests == []
        risk = status["reason"]
        assert "풀을 못 읽어 빈 프리셋인지 확인 못 함" in risk
        assert "새로 만드는 프리셋" not in risk
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is not None


class TestExistingSlotPassesThrough:
    """(w-3) 대조군 — slot 이 있는 번호는 t577 그대로 승인 기록 대상."""

    def test_existing_slot_is_listed_and_approved(self, tmp_path) -> None:
        cue = {"bar": 1, "effect_preset_no": "4.21", "effect_kind": "position", "evidence": None}
        status, store, _console, approval = _apply(
            tmp_path, _timeline_with_cue(cue), _tree_with_pools(p4=[21])
        )
        assert status["ok"] is True
        risk = _risk_text(approval)
        assert "새로 만드는 프리셋 1개" in risk
        assert _HOLD_LABEL not in risk
        approved = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(approved) is None


class TestHoldIsCellScoped:
    """(w-4) 한 칸에 있는 번호 하나 + 빈 번호 하나 → 칸 전체 보류."""

    def test_mixed_cell_is_held_whole(self, tmp_path) -> None:
        cue = {
            "bar": 1,
            "position_preset_no": "2.5",
            "color_preset_no": "4.99",
            "evidence": None,
        }
        status, store, _console, approval = _apply(
            tmp_path, _timeline_with_cue(cue), _tree_with_pools(p2=[5], p4=[21])
        )
        assert status["ok"] is False
        assert approval.requests == []
        risk = status["reason"]
        assert _HOLD_LABEL in risk
        assert "새로 만드는 프리셋" not in risk, "보류 칸의 다른 번호가 승인 대상으로 남았다"
        held = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(held) is not None
        assert not [c for c in _sent_commands(approval) if "2.5" in c or "4.99" in c]


class TestApprovalVsSentExcludesHeldCells:
    """(w-5) 보류 칸은 송신으로 세지 않는다 — 승인=송신 대조가 맞는다."""

    def test_held_cell_is_not_counted_as_sent(self, tmp_path) -> None:
        status, _store, console, _approval = _apply(
            tmp_path, _timeline_with_cue(dict(_EMPTY_EFFECT_CUE)), _tree_with_pools(p4=[21])
        )
        # 보류 칸은 송신으로 세지 않는다 — 보낼 줄이 없어 반영은 거절되고 콘솔 쓰기는 0건이다.
        assert status["ok"] is False
        assert status["approval_vs_sent"] is None
        assert console.executed == []


class TestSplitEmptyPresetHolds:
    """순수 분류기 — 콘솔 없이."""

    @staticmethod
    def _entry(group: str, bar: int, field: str, value: str) -> dict:
        return {
            "group_name": group,
            "bar": bar,
            "field": field,
            "field_label": field,
            "value": value,
        }

    def test_partitions_by_slot_presence_and_unread(self) -> None:
        pending = [
            self._entry("BACK", 1, "color_preset_no", "4.21"),
            self._entry("BACK", 2, "color_preset_no", "4.99"),
            self._entry("SIDE", 3, "position_preset_no", "2.7"),
        ]
        approvable, held = split_empty_preset_holds(pending, {4: {21: "Red"}, 2: None})
        assert [e["value"] for e in approvable] == ["4.21"]
        assert [(e["value"], e["hold_reason"]) for e in held] == [
            ("4.99", _HOLD_LABEL),
            ("2.7", "풀을 못 읽어 빈 프리셋인지 확인 못 함"),
        ]

    def test_one_held_number_holds_the_whole_cell(self) -> None:
        pending = [
            self._entry("BACK", 1, "position_preset_no", "2.5"),
            self._entry("BACK", 1, "color_preset_no", "4.99"),
        ]
        approvable, held = split_empty_preset_holds(pending, {2: {5: None}, 4: {}})
        assert approvable == []
        assert {e["value"] for e in held} == {"2.5", "4.99"}

    @pytest.mark.parametrize("value", ["abc", "4", "4.x", ""])
    def test_unparseable_number_is_held_not_guessed(self, value) -> None:
        pending = [self._entry("BACK", 1, "color_preset_no", value)]
        approvable, held = split_empty_preset_holds(pending, {})
        assert approvable == []
        assert len(held) == 1
