"""SPEC-LDRHYTHM-001 stage 2 — LOVE ATTACK 연출 프리셋 계획·저장 승인 카드.

콘솔 접촉 0건. 콘솔 풀 판독은 가짜 상태 트리(2026-10-15 읽기 결과를 옮긴 픽스처)로,
디머 속성 이름은 테스트 픽스처로 주입한다. 승인 카드는 실제 게이트 경로를 탄다 —
거절이면 `FakeConsole.executed`가 비어 있고 격자가 바이트까지 그대로여야 하고,
승인(가짜)이면 칸의 번호 참조와 승인 기록이 그때 처음 적혀야 한다.
"""

from __future__ import annotations

import copy
import threading

from server.design.beat_grid import (
    LOVE_ATTACK_TITLE,
    check_evidence_approval,
    default_beat_grid,
)
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    load_preset_annotations,
    save_commands,
)
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_new_preset_dialog_t589 import (
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline_for_apply,
)
from .test_safety_gate import FakeConsole

# -- 2026-10-15 콘솔 읽기 결과(읽기 전용)를 옮긴 픽스처 ------------------------------
# dimmer 풀 1: 1~7 사용 · color 풀 4: 1~10, 32 · position 풀 2: 1~6, 21~30 사용.
# 이름은 판독 결과가 아니라 픽스처다 — 번호의 빈 자리만 계획이 쓴다.
_DIMMER_CHILDREN = {
    1: "풀",
    2: "쇼 하이 OLD",
    3: "미드",
    4: "로우",
    5: "잔광",
    6: "아웃",
    7: "쇼 하이",
}
_COLOR_CHILDREN = {**{slot: f"COLOR {slot}" for slot in range(1, 11)}, 32: "COLOR 32"}
_POSITION_CHILDREN = {
    **{slot: f"POS {slot}" for slot in range(1, 7)},
    **{slot: f"POS {slot}" for slot in range(21, 31)},
}
#: 디머 속성 이름 — 테스트 픽스처(실기 판독 대신). 격자의 모든 트랙이 같은 이름을 쓴다고 가정.
_ATTRIBUTES = {
    group: ("Dimmer",) for group in ("WASH-ALL", "BACK", "SIDE-ALL", "MOVER-U", "MOVER-D", "BLIND")
}
_EFFECT_BANDS = (
    ("1.", 21, 26),
    ("1.", 31, 33),
    ("2.", 61, 68),
    ("4.", 41, 99),
)

_EXPECTED_SAVE = (
    "ClearAll",
    "Group 10 ; Attribute 'Dimmer' At 40",
    "Store Preset 1.8",
    "Label Preset 1.8 'DIM-40'",
    "ClearAll",
    "Group 10 ; Attribute 'Dimmer' At 25",
    "Store Preset 1.9",
    "Label Preset 1.9 'DIM-25'",
    "ClearAll",
    "Group 4 ; Attribute 'Dimmer' At 60",
    "Store Preset 1.10",
    "Label Preset 1.10 'DIM-60'",
    "ClearAll",
    "Group 4 + 7 + 11 + 12 + 14 ; Attribute 'Dimmer' At 100",
    "Store Preset 1.11",
    "Label Preset 1.11 'DIM-100'",
    "ClearAll",
)


def _love_attack_grid() -> dict:
    return copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))


def _plan(
    grid=None,
    *,
    dimmer=(1, _DIMMER_CHILDREN),
    color=(4, _COLOR_CHILDREN),
    position=(2, _POSITION_CHILDREN),
    attributes=None,
):
    return build_preset_plan(
        grid if grid is not None else _love_attack_grid(),
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=dimmer,
        color_pool=color,
        position_pool=position,
        dimmer_attributes=_ATTRIBUTES if attributes is None else attributes,
    )


def _preset(plan, name: str):
    matches = [preset for preset in plan.presets if preset.name == name]
    assert len(matches) == 1, f"{name!r} 이 한 번만 있어야 한다: {[p.name for p in plan.presets]}"
    return matches[0]


def _cue_of(grid, group_name: str, bar: int) -> dict:
    track = next(t for t in grid["tracks"] if t["group_name"] == group_name)
    return next(c for c in track["cues"] if c["bar"] == bar)


def _in_effect_band(number: str) -> bool:
    pool, _, slot = number.partition(".")
    return any(
        pool + "." == prefix and low <= int(slot) <= high for prefix, low, high in _EFFECT_BANDS
    )


# == 계획: 묶기 · 번호 · 미정 ======================================================


class TestDeDuplication:
    def test_identical_values_become_one_preset_with_every_cell_counted(self) -> None:
        plan = _plan()
        names = [preset.name for preset in plan.presets if preset.kind == "dimmer"]
        assert names == ["DIM-40", "DIM-25", "DIM-60", "DIM-100"]
        assert len(_preset(plan, "DIM-100").cells) == 19
        # 디머 값으로 세던 칸 22개 = 프리셋 칸 합 (WASH 2 + BACK 60 한 칸 + 100% 19칸).
        value_cells = sum(len(preset.cells) for preset in plan.presets if preset.kind == "dimmer")
        assert value_cells == 22

    def test_same_value_across_groups_is_one_entry_listing_every_group(self) -> None:
        plan = _plan()
        assert _preset(plan, "DIM-100").groups == (
            "BACK",
            "SIDE-ALL",
            "MOVER-U",
            "MOVER-D",
            "BLIND",
        )


class TestReadyAndHeldPresets:
    def test_single_group_dimmers_are_ready_and_carry_the_group_number(self) -> None:
        plan = _plan()
        for name, group_no in (("DIM-40", 10), ("DIM-25", 10), ("DIM-60", 4)):
            preset = _preset(plan, name)
            assert preset.ready is True
            assert preset.hold is None
            assert preset.group_no == group_no

    def test_multi_group_dimmer_is_ready_as_one_selection(self) -> None:
        preset = _preset(_plan(), "DIM-100")
        assert preset.ready is True
        assert preset.hold is None
        assert preset.group_nos == (4, 7, 11, 12, 14)

    def test_lavender_is_a_palette_rgb_and_stays_out_of_this_card(self) -> None:
        preset = _preset(_plan(), "LAVENDER")
        assert preset.kind == "color"
        assert preset.value == "RGB 55 35 100"
        assert preset.ready is False
        assert preset.deferred is True
        assert "이 카드 범위 밖" in (preset.hold or "")

    def test_floor_is_an_approximate_target_and_stays_out_of_this_card(self) -> None:
        preset = _preset(_plan(), "FLOOR")
        assert preset.kind == "position"
        assert "무대 중앙 깊이 바닥" in preset.value
        assert preset.ready is False
        assert preset.deferred is True
        assert len(preset.cells) == 2


class TestEmptySlots:
    def test_chosen_slots_are_empty_console_numbers_only(self) -> None:
        plan = _plan()
        dimmer_slots = [p.slot for p in plan.presets if p.kind == "dimmer"]
        assert dimmer_slots == ["1.8", "1.9", "1.10", "1.11"]
        assert _preset(plan, "LAVENDER").slot == "4.33"
        assert _preset(plan, "FLOOR").slot == "2.31"

    def test_no_chosen_slot_is_occupied_or_in_an_effect_band(self) -> None:
        plan = _plan()
        occupied = {f"1.{slot}" for slot in _DIMMER_CHILDREN}
        occupied |= {f"4.{slot}" for slot in _COLOR_CHILDREN}
        occupied |= {f"2.{slot}" for slot in _POSITION_CHILDREN}
        for preset in plan.presets:
            assert preset.slot not in occupied, f"{preset.name} 이 점유된 번호 {preset.slot}"
            assert not _in_effect_band(preset.slot), f"{preset.name} 이 효과 번호대 {preset.slot}"

    def test_slots_follow_the_console_read_not_a_constant(self) -> None:
        more_dimmers = {**_DIMMER_CHILDREN, 8: "X8", 9: "X9", 10: "X10"}
        plan = _plan(dimmer=(1, more_dimmers))
        assert _preset(plan, "DIM-40").slot == "1.11"
        assert _preset(plan, "DIM-100").slot == "1.14"

    def test_unread_dimmer_pool_leaves_every_dimmer_unassigned_and_held(self) -> None:
        plan = _plan(dimmer=None)
        for preset in plan.presets:
            if preset.kind != "dimmer":
                continue
            assert preset.slot is None
            assert preset.ready is False
            assert "디머 풀을 콘솔에서 읽지 못해" in (preset.hold or "")
        assert save_commands(plan) == ()


class TestUndecidedItems:
    def test_relative_moves_and_scene_memos_are_listed_as_undecided(self) -> None:
        plan = _plan()
        text = "\n".join(plan.unresolved)
        assert "5마디 1박 위치 한 칸 올림" in text
        assert "11마디 1박 새 자리" in text
        assert "SCENE 메모 18마디" in text
        assert "confirmed: false" in "\n".join(plan.supervisor_fixes)

    def test_kept_numbers_are_counted_and_not_planned(self) -> None:
        plan = _plan()
        kept = dict(plan.kept)
        assert kept["2.1"] == 2 and kept["1.1"] == 1 and kept["1.6"] == 1
        planned = {p.slot for p in plan.presets}
        assert planned.isdisjoint(kept)


# == 저장 줄 · 승인 뒤 참조 ======================================================


class TestSaveCommands:
    def test_only_ready_dimmers_are_saved_with_exact_text(self) -> None:
        assert save_commands(_plan()) == _EXPECTED_SAVE

    def test_no_color_or_position_text_reaches_the_card(self) -> None:
        joined = "\n".join(save_commands(_plan()))
        assert "ColorRGB" not in joined
        assert "LAVENDER" not in joined and "FLOOR" not in joined
        assert "Label Preset 1.11 'DIM-100'" in joined

    def test_planning_never_mutates_the_grid(self) -> None:
        grid = _love_attack_grid()
        before = copy.deepcopy(grid)
        _plan(grid)
        assert grid == before


class TestReferenceUpdate:
    def test_reference_update_sets_dimmer_numbers_and_records_approval(self) -> None:
        grid = _love_attack_grid()
        plan = _plan(grid)
        approved = apply_plan_references(
            grid, plan, by="supervisor", date="2026-10-15T00:00:00+00:00", source="fake-approval"
        )
        wash = _cue_of(approved, "WASH-ALL", 7)
        assert wash["brightness"] == {
            "mode": "dimmer_preset",
            "value_percent": None,
            "preset_no": "1.8",
        }
        assert check_evidence_approval(wash) is None
        assert wash["evidence"]["approval"]["by"] == "supervisor"
        back = _cue_of(approved, "BACK", 7)
        assert back["brightness"]["preset_no"] == "1.10"
        assert _cue_of(approved, "BACK", 18)["brightness"]["preset_no"] == "1.11"
        assert back["effect_preset_no"] == "21.1"
        # 칸에 있던 기존 승인(t543 proposal #6)의 출처는 지우지 않고 덧붙인다.
        assert "proposal-table.md#6" in back["evidence"]["approval"]["source"]
        assert "fake-approval" in back["evidence"]["approval"]["source"]

    def test_reference_update_leaves_the_original_grid_and_unplanned_cells_alone(self) -> None:
        grid = _love_attack_grid()
        before = copy.deepcopy(grid)
        approved = apply_plan_references(
            grid, _plan(grid), by="supervisor", date="2026-10-15T00:00:00+00:00", source="x"
        )
        assert grid == before
        # 100% 칸은 이제 다중 그룹 DIM-100(1.11)을 가리키고, 승인된 위치 2.1 칸은 그대로다.
        assert _cue_of(approved, "MOVER-U", 18)["brightness"]["preset_no"] == "1.11"
        assert _cue_of(approved, "MOVER-U", 18)["position_preset_no"] == "2.1"


# == 승인 카드: 거절 · 가짜 승인 (세션 경로) ====================================


def _love_attack_session(tmp_path, *, decisions, monkeypatch):
    grid = _love_attack_grid()
    store = SongTimelineStore()
    store.latest = _timeline_for_apply(beat_grid=grid)
    state_tree = {
        **_state_tree(),
        "DataPool/PresetPools": _pool_list_payload(
            {"Dimmer": 1, "Position": 2, "Color": 4, "All 1": 21}
        ),
        "DataPool/PresetPools/1": _pool_children_payload(_DIMMER_CHILDREN),
        "DataPool/PresetPools/2": _pool_children_payload(_POSITION_CHILDREN),
        "DataPool/PresetPools/4": _pool_children_payload(_COLOR_CHILDREN),
    }
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, decisions=decisions, state_tree=state_tree
    )
    monkeypatch.setattr(
        session,
        "_beat_grid_preset_dimmer_attributes",
        lambda names: dict(_ATTRIBUTES),
    )
    return session, console, approval, store


class TestApprovalCardRejected:
    def test_rejected_card_contains_the_save_text_sends_nothing_and_keeps_cells(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, approval, store = _love_attack_session(
            tmp_path, decisions=(False,), monkeypatch=monkeypatch
        )
        before = copy.deepcopy(store.latest["beat_grid"])

        event = session.beat_grid_preset_plan()

        # 카드는 올라갔고, 저장 줄이 그 카드 안에 있다.
        assert len(approval.requests) == 1
        card_commands = list(approval.requests[0].commands)
        for text in ("Store Preset 1.8", "Label Preset 1.8 'DIM-40'", "Store Preset 1.10"):
            assert any(text in command for command in card_commands), text
        # (a) 콘솔 송신 0건.
        assert console.executed == []
        # (b) 칸은 바이트까지 그대로다.
        assert store.latest["beat_grid"] == before
        assert event["ok"] is False

    def test_approved_fake_card_writes_references_only_after_approval(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, approval, store = _love_attack_session(
            tmp_path, decisions=(True,), monkeypatch=monkeypatch
        )
        before = copy.deepcopy(store.latest["beat_grid"])

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        # 가짜 콘솔(테스트 전용)에만 저장 줄이 나갔다.
        assert console.executed == list(_EXPECTED_SAVE)
        grid = store.latest["beat_grid"]
        assert grid != before
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"
        assert _cue_of(grid, "WASH-ALL", 14)["brightness"]["preset_no"] == "1.9"
        assert _cue_of(grid, "BACK", 7)["brightness"]["preset_no"] == "1.10"
        # 100% 칸(다중 그룹 DIM-100)은 1.11 을 가리킨다.
        assert _cue_of(grid, "BACK", 18)["brightness"]["preset_no"] == "1.11"


# == 승인 카드: 실제 비동기 승인 통로 (ApprovalChannel + 다른 스레드가 답함) ========


def _real_channel_session(tmp_path, monkeypatch, *, on_card=None, approve=True):
    """게이트의 승인 포트가 ``ApprovalChannel`` 인 세션 — 운영 배선과 같다. 카드(승인 요청
    이벤트)가 뜨면 **다른 스레드**가 (선택적으로 ``on_card`` 를 먼저 돌린 뒤) 답한다."""
    grid = _love_attack_grid()
    store = SongTimelineStore()
    store.latest = _timeline_for_apply(beat_grid=grid)
    state_tree = {
        **_state_tree(),
        "DataPool/PresetPools": _pool_list_payload(
            {"Dimmer": 1, "Position": 2, "Color": 4, "All 1": 21}
        ),
        "DataPool/PresetPools/1": _pool_children_payload(_DIMMER_CHILDREN),
        "DataPool/PresetPools/2": _pool_children_payload(_POSITION_CHILDREN),
        "DataPool/PresetPools/4": _pool_children_payload(_COLOR_CHILDREN),
    }
    console = FakeConsole(state_tree=state_tree)
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=5.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    holder: dict = {}

    def send(event):
        if event.get("type") != "approval_request":
            return

        def answer():
            if on_card is not None:
                on_card(store)
            channel.resolve(event["request_id"], approved=approve)

        threading.Thread(target=answer).start()

    session = ChatSession(
        gate=gate,
        provider=_RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=send,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    holder["session"] = session
    monkeypatch.setattr(
        session,
        "_beat_grid_preset_dimmer_attributes",
        lambda names: dict(_ATTRIBUTES),
    )
    return session, console, store


class _RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - 모델을 부르지 않는다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


class TestApprovalCardRealAsyncChannel:
    def test_cells_are_repointed_when_a_other_thread_approves_the_card(
        self, tmp_path, monkeypatch
    ) -> None:
        session, console, store = _real_channel_session(tmp_path, monkeypatch)

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert console.executed == list(_EXPECTED_SAVE)
        grid = store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"
        assert _cue_of(grid, "WASH-ALL", 14)["brightness"]["preset_no"] == "1.9"
        assert _cue_of(grid, "BACK", 7)["brightness"]["preset_no"] == "1.10"
        assert check_evidence_approval(_cue_of(grid, "WASH-ALL", 7)) is None

    def test_an_edit_made_while_the_card_is_open_survives_the_approval(
        self, tmp_path, monkeypatch
    ) -> None:
        def edit_while_waiting(store) -> None:
            # 카드가 떠 있는 사이 감독이 다른 칸(미정 칸)의 밝기를 고쳤다.
            latest = copy.deepcopy(store.latest)
            cue = _cue_of(latest["beat_grid"], "BACK", 18)
            cue["brightness"] = {"mode": "value", "value_percent": 77, "preset_no": None}
            store.latest = latest

        session, _console, store = _real_channel_session(
            tmp_path, monkeypatch, on_card=edit_while_waiting
        )

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        grid = store.latest["beat_grid"]
        assert _cue_of(grid, "BACK", 18)["brightness"]["value_percent"] == 77
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"

    def test_a_planned_cell_edited_while_the_card_is_open_is_not_repointed(
        self, tmp_path, monkeypatch
    ) -> None:
        def edit_planned_cell(store) -> None:
            latest = copy.deepcopy(store.latest)
            cue = _cue_of(latest["beat_grid"], "WASH-ALL", 7)
            cue["brightness"] = {"mode": "value", "value_percent": 5, "preset_no": None}
            store.latest = latest

        session, _console, store = _real_channel_session(
            tmp_path, monkeypatch, on_card=edit_planned_cell
        )

        session.beat_grid_preset_plan()

        grid = store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["value_percent"] == 5
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] is None
        assert _cue_of(grid, "WASH-ALL", 14)["brightness"]["preset_no"] == "1.9"


# == 콘솔을 못 읽을 때: 계획표는 그래도 보인다 (감독 브라우저 확인 1015) ==========


class TestPlanTableWithoutConsole:
    def test_unread_pools_still_send_the_plan_table_but_raise_no_card(
        self, tmp_path, monkeypatch
    ) -> None:
        grid = _love_attack_grid()
        store = SongTimelineStore()
        store.latest = _timeline_for_apply(beat_grid=grid)
        sent: list[dict] = []
        session, console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(True,), state_tree={}, sent=sent
        )
        monkeypatch.setattr(session, "_beat_grid_preset_dimmer_attributes", lambda names: {})
        before = copy.deepcopy(store.latest["beat_grid"])

        event = session.beat_grid_preset_plan()

        tables = [e for e in sent if e.get("summary") == "연출 프리셋 계획"]
        assert len(tables) == 1
        text = tables[0]["text"]
        assert "| 만들 프리셋 |" in text
        assert "DIM-40" in text
        assert "콘솔 읽은 뒤 정함" in text
        assert "감독이 고칠 값" in text
        # 저장할 것이 없으니 카드·콘솔 송신·격자 변경은 0.
        assert approval.requests == []
        assert console.executed == []
        assert store.latest["beat_grid"] == before
        assert event["ok"] is False
