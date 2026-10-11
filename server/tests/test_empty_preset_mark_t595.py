"""카드 t595 — 박자 격자 칸·편집 칸의 「빈 프리셋」 표식(REQ-LDBEAT-015(i-1)
「그 칸에 표시」).

서버가 이미 읽은 풀(반영 때 승인 대기 번호의 풀 판독 · 프리셋 서랍 판독)로만
가른 ``beat_grid["empty_preset_cells"]``를 격자 이벤트에 실어 보낸다 — UI 는 이
목록만 읽는다. 아직 읽지 않은 풀의 번호는 판정하지 않는다. 이미 승인된 칸의 빈
번호도 표식 대상이다 — 카드 t600 이후 반영이 승인된 칸도 같은 규칙으로 보류·생성하므로
``state``는 held·create 둘이다(옛 ``approved``「그대로 나감」은 없어졌다).

하네스: t577/t590 가짜 콘솔(반영), t551 가짜 콘솔(서랍·편집). 콘솔 쓰기 0건.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid import (
    EMPTY_PRESET_HOLD,
    POOL_UNREAD_HOLD,
    POSITION_CREATE_ON_APPLY,
    classify_empty_preset,
    empty_preset_cells,
)
from server.design.beat_grid_effect_presets import EFFECT_RECIPE_MISSING
from server.design.beat_grid_position_presets import POSITION_TARGET_MISSING
from server.web.session import SongTimelineStore

from . import test_session_beat_grid_edit_t551 as t551
from .test_apply_time_approval_t577 import _new_session, _state_tree, _timeline

_APPROVED = {
    "grade": None,
    "approval": {"by": "supervisor", "date": "2026-10-11", "source": "t595"},
}


def _grid(*cues: dict) -> dict:
    return {"tracks": [{"group_name": "BACK", "cues": list(cues)}]}


def _marks_by_bar(cells: list[dict]) -> dict[int, dict]:
    return {cell["bar"]: cell for cell in cells}


def _grids(sent: list[dict]) -> list[dict]:
    return [e["timeline"]["beat_grid"] for e in sent if e.get("type") == "song_timeline"]


class TestClassifier:
    """보류(t590)와 표식(t595)이 쓰는 한 판정."""

    POOLS = {4: {21: "P21"}, 2: None}

    @pytest.mark.parametrize(
        ("value", "unknown_unread", "expected"),
        [
            ("4.21", False, None),
            ("4.99", False, EMPTY_PRESET_HOLD),
            ("2.5", False, POOL_UNREAD_HOLD),
            ("9.1", False, None),  # 안 읽은 풀 — 표식은 판정하지 않는다
            ("9.1", True, POOL_UNREAD_HOLD),  # 반영은 방금 읽었으니 「못 읽음」
            ("abc", False, EMPTY_PRESET_HOLD),
        ],
    )
    def test_cases(self, value, unknown_unread, expected) -> None:
        got = classify_empty_preset(value, self.POOLS, unknown_pool_unread=unknown_unread)
        assert got == expected


class TestEmptyPresetCells:
    def test_pending_and_approved_cells_are_split_by_state(self) -> None:
        grid = _grid(
            {"bar": 1, "effect_preset_no": "4.99", "evidence": None},
            {"bar": 2, "color_preset_no": "4.98", "evidence": dict(_APPROVED)},
            {"bar": 3, "effect_preset_no": "4.21", "evidence": None},
        )
        marks = _marks_by_bar(empty_preset_cells(grid, {4: {21: "P21"}}))
        assert set(marks) == {1, 2}
        assert marks[1]["state"] == "held"
        assert marks[2]["state"] == "held"  # 카드 t600 — 승인된 칸도 송신 보류
        assert marks[1]["fields"] == [
            {
                "field": "effect_preset_no",
                "field_label": "효과 프리셋",
                "value": "4.99",
                "kind": "empty",
                # 카드 t593 — 빈 효과 번호도 반영 때 만들 수 있게 되어, 못 만드는 사유를 붙인다.
                "reason": f"{EMPTY_PRESET_HOLD}({EFFECT_RECIPE_MISSING})",
            }
        ]

    def test_unread_pool_and_brightness_preset(self) -> None:
        grid = _grid({"bar": 5, "brightness": {"mode": "dimmer_preset", "preset_no": "1.7"}})
        (cell,) = empty_preset_cells(grid, {1: None})
        assert cell["fields"][0]["field"] == "brightness.preset_no"
        assert cell["fields"][0]["kind"] == "pool_unread"
        assert cell["fields"][0]["reason"] == POOL_UNREAD_HOLD

    def test_pool_never_read_gives_no_mark(self) -> None:
        grid = _grid({"bar": 1, "effect_preset_no": "4.99", "evidence": None})
        assert empty_preset_cells(grid, {}) == []


def _pool(path: str, slots: list[int]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": slot, "name": f"P{slot}"} for slot in slots],
    }


def _apply(tmp_path, cues: list[dict], *, pool4: list[int] | None):
    tree = _state_tree()
    if pool4 is None:
        tree.pop("DataPool/PresetPools/4", None)
    else:
        tree["DataPool/PresetPools/4"] = _pool("DataPool/PresetPools/4", pool4)
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = cues
    store = SongTimelineStore()
    store.latest = timeline
    sent: list[dict] = []
    session, console, _approval, _audit = _new_session(
        tmp_path, store=store, state_tree=tree, sent=sent
    )
    status = session.beat_grid_apply()
    return status, sent


class TestApplySendsMarks:
    """반영의 풀 판독(t590)이 끝나면 승인 카드보다 먼저 격자에 표식이 실린다."""

    CUES = [
        {"bar": 1, "effect_preset_no": "4.99", "effect_kind": "position", "evidence": None},
        {"bar": 2, "color_preset_no": "4.98", "evidence": dict(_APPROVED)},
        {"bar": 3, "effect_preset_no": "4.21", "effect_kind": "position", "evidence": None},
    ]

    def test_marks_reach_the_ui_before_the_approval_card(self, tmp_path) -> None:
        status, sent = _apply(tmp_path, [dict(c) for c in self.CUES], pool4=[21])
        assert status["ok"] is True
        types = [e.get("type") for e in sent]
        assert types.index("song_timeline") < types.index("execution_preview")
        marks = _marks_by_bar(_grids(sent)[0]["empty_preset_cells"])
        assert set(marks) == {1, 2}, "있는 번호(4.21)에 표식이 붙었거나 빈 번호가 빠졌다"
        assert marks[1]["state"] == "held"
        assert marks[2]["state"] == "held"  # 카드 t600 — 승인된 칸도 송신 보류

    def test_every_later_grid_event_keeps_the_marks(self, tmp_path) -> None:
        _status, sent = _apply(tmp_path, [dict(c) for c in self.CUES], pool4=[21])
        grids = _grids(sent)
        assert len(grids) >= 2
        assert all(set(_marks_by_bar(g["empty_preset_cells"])) == {1, 2} for g in grids)

    def test_unreadable_pool_marks_pool_unread(self, tmp_path) -> None:
        cue = {"bar": 1, "effect_preset_no": "4.99", "effect_kind": "position", "evidence": None}
        _status, sent = _apply(tmp_path, [cue], pool4=None)
        (cell,) = _grids(sent)[0]["empty_preset_cells"]
        assert cell["fields"][0]["kind"] == "pool_unread"


def _drawer_session(tmp_path, cues: list[dict]):
    state_tree = {
        "DataPool/PresetPools": t551._pool_list_payload({"Dimmer": 1, "Position": 2, "Color": 4}),
        "DataPool/PresetPools/1": t551._pool_children_payload({1: "LA Full"}),
        "DataPool/PresetPools/2": t551._pool_children_payload({41: "Center"}),
        "DataPool/PresetPools/4": t551._pool_children_payload({21: "LA Pink"}),
    }
    store = SongTimelineStore()
    store.latest = t551._timeline(
        beat_grid={"tracks": [{"group_name": "BACK", "group_no": 7, "cues": cues}]}
    )
    sent: list[dict] = []
    session, console = t551._new_session(tmp_path, store=store, sent=sent, state_tree=state_tree)
    return session, console, store, sent


class TestDrawerReadSendsMarks:
    def test_drawer_read_marks_empty_numbers_without_writing(self, tmp_path) -> None:
        session, console, _store, sent = _drawer_session(
            tmp_path,
            [
                {"bar": 1, "position_preset_no": "2.99", "evidence": dict(_APPROVED)},
                {"bar": 2, "color_preset_no": "4.21", "evidence": None},
            ],
        )
        session.beat_grid_preset_drawer()
        assert console.executed == []
        (cell,) = _grids(sent)[-1]["empty_preset_cells"]
        assert (cell["bar"], cell["state"], cell["fields"][0]["value"]) == (1, "held", "2.99")

    def test_same_read_twice_does_not_resend_the_grid(self, tmp_path) -> None:
        session, _console, _store, sent = _drawer_session(
            tmp_path, [{"bar": 1, "position_preset_no": "2.99", "evidence": None}]
        )
        session.beat_grid_preset_drawer()
        first = len(_grids(sent))
        session.beat_grid_preset_drawer()
        assert first == 1
        assert len(_grids(sent)) == first, "표식이 그대로인데 격자를 다시 보냈다"

    def test_no_empty_number_sends_no_grid(self, tmp_path) -> None:
        session, _console, _store, sent = _drawer_session(
            tmp_path, [{"bar": 1, "position_preset_no": "2.41", "evidence": None}]
        )
        session.beat_grid_preset_drawer()
        assert _grids(sent) == []


class TestNewPresetDialogMarksItsNumber:
    """t589 「＋ 새 프리셋 만들기」도 풀을 읽어 빈 번호를 고른다 — 그 판독으로
    배정 직후 그 칸에 표식이 붙는다(반영에서 보류될 칸)."""

    def test_assigned_empty_number_is_marked_held(self, tmp_path) -> None:
        from . import test_new_preset_dialog_t589 as t589

        store = SongTimelineStore()
        store.latest = t589._timeline()
        state_tree = t589._state_tree(
            **{
                "DataPool/PresetPools": t589._pool_list_payload({"Position": 2}),
                "DataPool/PresetPools/2": t589._pool_children_payload({}),
            }
        )
        sent: list[dict] = []
        session, console, _approval, _audit = t589._new_session(
            tmp_path, store=store, state_tree=state_tree, sent=sent
        )
        session.beat_grid_new_preset(1, "BACK", "effect", "LA Wave", "따뜻한 흰색")
        assert console.executed == []
        (cell,) = _grids(sent)[-1]["empty_preset_cells"]
        assert (cell["bar"], cell["state"], cell["fields"][0]["value"]) == (1, "held", "2.61")


class TestEditRecomputesMarks:
    def test_editing_to_an_existing_slot_clears_the_mark(self, tmp_path) -> None:
        session, _console, store, sent = _drawer_session(
            tmp_path, [{"bar": 1, "color_preset_no": "4.99", "evidence": None}]
        )
        session.beat_grid_preset_drawer()
        assert _grids(sent)[-1]["empty_preset_cells"]
        session.beat_grid_edit(1, "BACK", {"color_preset_no": "4.21"})
        cue = store.latest["beat_grid"]["tracks"][0]["cues"][0]
        assert cue["color_preset_no"] == "4.21", sent[-3:]
        assert _grids(sent)[-1]["empty_preset_cells"] == []


# -- t592(#634) 합친 뒤: 빈 위치 번호는 반영 때 만들어질 수 있다 ----------------

_RECIPE = {
    "preset_targets": {"2.71": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "preset_labels": {"2.71": "LA Center"},
}


def _position_grid(cue: dict, **extra: object) -> dict:
    grid: dict = {
        "tracks": [{"group_name": "BACK", "group_no": 7, "group_no_confirmed": True, "cues": [cue]}]
    }
    grid.update(extra)
    return grid


class TestPositionCreateOnApply:
    def test_pending_empty_position_with_recipe_is_create(self) -> None:
        grid = _position_grid({"bar": 1, "position_preset_no": "2.71", "evidence": None}, **_RECIPE)
        (cell,) = empty_preset_cells(grid, {2: {1: "P1"}})
        assert cell["state"] == "create"
        assert cell["fields"][0]["kind"] == "create_on_apply"
        assert cell["fields"][0]["reason"] == POSITION_CREATE_ON_APPLY

    def test_missing_target_stays_held_with_t592_reason(self) -> None:
        grid = _position_grid({"bar": 1, "position_preset_no": "2.71", "evidence": None})
        (cell,) = empty_preset_cells(grid, {2: {1: "P1"}})
        assert cell["state"] == "held"
        assert cell["fields"][0]["kind"] == "empty"
        assert POSITION_TARGET_MISSING in cell["fields"][0]["reason"]

    def test_approved_only_reference_is_created(self) -> None:
        """카드 t600 — 승인된 칸만 가리켜도 t592 후보다(반영이 같은 규칙으로 만든다)."""
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": dict(_APPROVED)}
        (cell,) = empty_preset_cells(_position_grid(cue, **_RECIPE), {2: {1: "P1"}})
        assert cell["state"] == "create"
        assert cell["fields"][0]["kind"] == "create_on_apply"


class TestCreatedEstimateYieldsToARead:
    """리드 조건 ① — 송신 성공에서 나온 「있음」은 추정이다. 다음 실제 판독이 이긴다."""

    def test_estimate_clears_the_mark_then_a_real_read_restores_it(self, tmp_path) -> None:
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": dict(_APPROVED)}
        session, _console, store, sent = _drawer_session(tmp_path, [cue])
        session.beat_grid_preset_drawer()  # 실제 판독: 풀 2 = {41}
        assert _grids(sent)[-1]["empty_preset_cells"]
        session._beat_grid_note_created_presets(["2.71"])  # 추정: 만들었다
        grid = store.latest["beat_grid"]
        assert empty_preset_cells(grid, session._beat_grid_pool_slots) == []
        session.beat_grid_preset_drawer()  # 다시 실제 판독: 콘솔엔 여전히 {41}
        (cell,) = _grids(sent)[-1]["empty_preset_cells"]
        assert cell["fields"][0]["value"] == "2.71", "추정이 판독을 이겼다"

    def test_never_read_pool_gets_no_estimate(self, tmp_path) -> None:
        session, _console, _store, _sent = _drawer_session(tmp_path, [])
        session._beat_grid_note_created_presets(["9.5"])
        assert 9 not in session._beat_grid_pool_slots


class TestApplyThatCreatesClearsTheMark:
    """t592 실제 만들기 흐름 — 승인=송신 성공 뒤 격자에서 표식이 사라진다."""

    def test_created_number_loses_its_mark_after_apply(self, tmp_path) -> None:
        from .test_position_preset_create_t592 import _FRAMES, _MEMBERS

        timeline = _timeline()
        timeline["beat_grid"]["tracks"][0]["cues"] = [
            {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        ]
        timeline["beat_grid"].update(_RECIPE)
        tree = _state_tree()
        tree["DataPool/PresetPools/2"] = _pool("DataPool/PresetPools/2", [1, 2])
        store = SongTimelineStore()
        store.latest = timeline
        sent: list[dict] = []
        session, _console, approval, _audit = _new_session(
            tmp_path, store=store, state_tree=tree, sent=sent
        )
        session._beat_grid_group_members = lambda names: {
            n: _MEMBERS[n] for n in names if n in _MEMBERS
        }
        session._beat_grid_pointing_frames = lambda: _FRAMES
        status = session.beat_grid_apply()
        assert status["ok"] is True
        assert "Store Preset 2.71" in [i.command for r in approval.requests for i in r.items]
        grids = _grids(sent)
        (before,) = grids[0]["empty_preset_cells"]
        assert before["state"] == "create"
        assert grids[-1]["empty_preset_cells"] == [], "만든 번호에 빈 프리셋 표식이 남았다"
