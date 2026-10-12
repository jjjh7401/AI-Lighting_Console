"""카드 t592 — 새 위치 프리셋을 콘솔에 실제로 만든다(REQ-LDBEAT-015(i-3)(i-7)(i-8)).

값 = 곡 격자 ``preset_targets["2.n"]``(무대 목표 좌표)를 조준 경로
(``server/spatial/pointing.py``)로 환산한 장비별 Pan/Tilt. 이름 =
``preset_labels["2.n"]``(t589 와 같은 키·모양). 반영 묶음에 붙는 줄은
t474 run3 실기 선례와 같은 꼴: 조준 줄 → ``Store Preset 2.n`` →
``Label Preset 2.n '이름'`` → ``ClearAll``.

핵심 잠금: ``Store Preset`` 은 풀 판독에서 slot 이 **비었다고 읽힌** 번호에만
나간다(덮어쓰기 0). 풀을 못 읽었거나 slot 이 있으면 만들기 줄 0. 콘솔 접촉 0건.
"""

from __future__ import annotations

import math

import pytest

from server.design.beat_grid import (
    CELL_HOLD,
    EMPTY_PRESET_HOLD,
    POOL_UNREAD_HOLD,
    check_evidence_approval,
)
from server.design.beat_grid_position_presets import (
    POSITION_COORDS_UNREAD,
    POSITION_GROUP_UNCONFIRMED,
    POSITION_LABEL_INVALID,
    POSITION_LABEL_MISSING,
    POSITION_MEMBERS_UNREAD,
    POSITION_TARGET_MISSING,
    POSITION_UNAIMABLE,
    PointingFrames,
    plan_position_preset_creation,
    position_preset_target,
    record_position_preset_target,
)
from server.web.session import SongTimelineStore

from .test_apply_time_approval_t577 import _cue_of, _new_session, _state_tree, _timeline

# -- 픽스처 -------------------------------------------------------------------

_MEMBERS = {"BACK": [101, 102]}
_FRAMES = PointingFrames(
    positions={101: (-1.0, 0.0, 5.0), 102: (1.0, 0.0, 5.0)},
    rotz={},
    rotation_skipped=(),
)


def _grid(cues: list[dict], *, confirmed: bool = True, **extra: object) -> dict:
    grid: dict = {
        "tracks": [
            {
                "group_name": "BACK",
                "group_no": 7,
                "group_no_confirmed": confirmed,
                "cues": cues,
            }
        ]
    }
    grid.update(extra)
    return grid


def _held(value: str, *, bar: int = 1, field: str = "position_preset_no", reason=None) -> dict:
    return {
        "group_name": "BACK",
        "bar": bar,
        "field": field,
        "field_label": field,
        "value": value,
        "hold_reason": reason or EMPTY_PRESET_HOLD,
    }


_RECIPE = {
    "preset_targets": {"2.71": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "preset_labels": {"2.71": "LA Center"},
}


def _plan(grid, held, *, members=_MEMBERS, frames=_FRAMES):
    return plan_position_preset_creation(grid, held, members=members, frames=frames)


# -- 저장 자리 -----------------------------------------------------------------


class TestRecordTarget:
    def test_records_a_copy_keyed_by_pool_slot(self) -> None:
        grid = _grid([])
        updated = record_position_preset_target(grid, "2.71", (0.5, -1, 2))
        assert "preset_targets" not in grid, "원본을 바꿨다"
        assert updated["preset_targets"] == {"2.71": {"x": 0.5, "y": -1.0, "z": 2.0}}
        assert position_preset_target(updated, "2.71") == (0.5, -1.0, 2.0)

    @pytest.mark.parametrize("value", ["4.21", "2", "abc", "2.x"])
    def test_refuses_non_position_pool_numbers(self, value) -> None:
        with pytest.raises(ValueError):
            record_position_preset_target(_grid([]), value, (0, 0, 0))

    @pytest.mark.parametrize("bad", [math.nan, math.inf, "1"])
    def test_refuses_non_finite_coordinates(self, bad) -> None:
        with pytest.raises(ValueError):
            record_position_preset_target(_grid([]), "2.71", (0, bad, 0))

    def test_missing_or_malformed_target_reads_as_none(self) -> None:
        assert position_preset_target(_grid([]), "2.71") is None
        assert position_preset_target({"preset_targets": {"2.71": {"x": 1}}}, "2.71") is None


# -- 계획(순수) ----------------------------------------------------------------


class TestPlanCreatesTheRecipe:
    def test_creation_lines_follow_the_t474_live_shape(self) -> None:
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **_RECIPE), [_held("2.71")])
        assert plan.held == []
        assert [e["value"] for e in plan.released] == ["2.71"]
        assert list(plan.creations) == ["2.71"]
        lines = plan.creations["2.71"]
        assert lines[0].startswith("Fixture 101 ; Attribute 'Pan' At ")
        assert lines[1].startswith("Fixture 102 ; Attribute 'Pan' At ")
        assert lines[2:] == (
            "Store Preset 2.71",
            "Label Preset 2.71 'LA Center'",
            "ClearAll",
        )

    def test_aim_values_come_from_the_pointing_model(self) -> None:
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **_RECIPE), [_held("2.71")])
        # 101 은 (-1,0,5) — 목표 (0,0,0) 은 +X 쪽 아래: pan = atan2(-1, 0) = -90.
        assert "Attribute 'Pan' At -90" in plan.creations["2.71"][0]
        assert "Attribute 'Tilt' At 11.3" in plan.creations["2.71"][0]


class TestOverwriteIsImpossible:
    """핵심 잠금 — slot 이 비었다고 **읽힌** 번호에만 Store 가 나간다."""

    def test_unreadable_pool_never_creates(self) -> None:
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **_RECIPE), [_held("2.71", reason=POOL_UNREAD_HOLD)])
        assert plan.creations == {}
        assert [e["hold_reason"] for e in plan.held] == [POOL_UNREAD_HOLD]

    def test_only_held_empty_numbers_are_candidates(self) -> None:
        # slot 이 있는 번호는 split 단계에서 held 로 오지 않는다 — held 가
        # 비면 만들기 0줄(recipe 가 있어도).
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **_RECIPE), [])
        assert plan.creations == {}

    def test_cell_hold_entry_alone_never_creates(self) -> None:
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **_RECIPE), [_held("2.71", reason=CELL_HOLD)])
        assert plan.creations == {}


class TestEveryMissingPieceHoldsWithItsReason:
    @pytest.mark.parametrize(
        ("grid_extra", "confirmed", "members", "frames", "reason"),
        [
            (
                {"preset_labels": {"2.71": "LA Center"}},
                True,
                _MEMBERS,
                _FRAMES,
                POSITION_TARGET_MISSING,
            ),
            (
                {"preset_targets": _RECIPE["preset_targets"]},
                True,
                _MEMBERS,
                _FRAMES,
                POSITION_LABEL_MISSING,
            ),
            (
                {**_RECIPE, "preset_labels": {"2.71": "라 센터"}},
                True,
                _MEMBERS,
                _FRAMES,
                POSITION_LABEL_INVALID,
            ),
            (_RECIPE, False, _MEMBERS, _FRAMES, POSITION_GROUP_UNCONFIRMED),
            (_RECIPE, True, {}, _FRAMES, POSITION_MEMBERS_UNREAD),
            (_RECIPE, True, _MEMBERS, None, POSITION_COORDS_UNREAD),
            (_RECIPE, True, {"BACK": [101, 103]}, _FRAMES, POSITION_COORDS_UNREAD),
        ],
    )
    def test_missing_piece(self, grid_extra, confirmed, members, frames, reason) -> None:
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        grid = _grid([cue], confirmed=confirmed, **grid_extra)
        plan = _plan(grid, [_held("2.71")], members=members, frames=frames)
        assert plan.creations == {}
        assert plan.released == []
        assert [e["hold_reason"] for e in plan.held] == [reason]

    def test_rotation_skipped_member_holds(self) -> None:
        frames = PointingFrames(positions=_FRAMES.positions, rotz={}, rotation_skipped=(102,))
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **_RECIPE), [_held("2.71")], frames=frames)
        assert plan.creations == {}
        assert plan.held[0]["hold_reason"].startswith(POSITION_UNAIMABLE)

    def test_unreachable_target_holds_instead_of_dropping_a_fixture(self) -> None:
        recipe = {**_RECIPE, "preset_targets": {"2.71": {"x": 0.0, "y": 0.0, "z": 9.0}}}
        cue = {"bar": 1, "position_preset_no": "2.71", "evidence": None}
        plan = _plan(_grid([cue], **recipe), [_held("2.71")])
        assert plan.creations == {}
        assert plan.held[0]["hold_reason"].startswith(POSITION_UNAIMABLE)


class TestCellScope:
    def test_cell_with_another_empty_kind_stays_held_and_creates_nothing(self) -> None:
        cue = {
            "bar": 1,
            "position_preset_no": "2.71",
            "color_preset_no": "4.99",
            "evidence": None,
        }
        held = [_held("2.71"), _held("4.99", field="color_preset_no")]
        plan = _plan(_grid([cue], **_RECIPE), held)
        assert plan.creations == {}
        assert plan.released == []
        reasons = {e["value"]: e["hold_reason"] for e in plan.held}
        assert reasons == {"2.71": CELL_HOLD, "4.99": EMPTY_PRESET_HOLD}

    def test_existing_number_in_a_released_cell_is_released_too(self) -> None:
        cue = {
            "bar": 1,
            "position_preset_no": "2.71",
            "color_preset_no": "4.21",
            "evidence": None,
        }
        held = [_held("2.71"), _held("4.21", field="color_preset_no", reason=CELL_HOLD)]
        plan = _plan(_grid([cue], **_RECIPE), held)
        assert plan.held == []
        assert {e["value"] for e in plan.released} == {"2.71", "4.21"}
        assert all("hold_reason" not in e for e in plan.released)

    def test_shared_number_is_created_once_for_all_its_groups(self) -> None:
        grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 1, "position_preset_no": "2.71"}],
                },
                {
                    "group_name": "SIDE",
                    "group_no": 8,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 2, "position_preset_no": "2.71"}],
                },
            ],
            **_RECIPE,
        }
        held = [_held("2.71"), {**_held("2.71", bar=2), "group_name": "SIDE"}]
        frames = PointingFrames(
            positions={**_FRAMES.positions, 201: (0.0, 3.0, 5.0)}, rotz={}, rotation_skipped=()
        )
        plan = _plan(grid, held, members={"BACK": [101, 102], "SIDE": [201]}, frames=frames)
        assert list(plan.creations) == ["2.71"]
        fixtures = [line.split(" ;")[0] for line in plan.creations["2.71"][:3]]
        assert fixtures == ["Fixture 101", "Fixture 102", "Fixture 201"]
        assert len(plan.released) == 2

    def test_shared_number_holds_everywhere_if_one_group_is_unconfirmed(self) -> None:
        grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 1, "position_preset_no": "2.71"}],
                },
                {
                    "group_name": "SIDE",
                    "group_no": None,
                    "group_no_confirmed": False,
                    "cues": [{"bar": 2, "position_preset_no": "2.71"}],
                },
            ],
            **_RECIPE,
        }
        held = [_held("2.71"), {**_held("2.71", bar=2), "group_name": "SIDE"}]
        plan = _plan(grid, held, members={"BACK": [101, 102], "SIDE": [201]})
        assert plan.creations == {}
        assert {e["hold_reason"] for e in plan.held} == {POSITION_GROUP_UNCONFIRMED}

    @staticmethod
    def _grid_with_approved_side(side_confirmed: bool) -> dict:
        approved = {"by": "supervisor", "date": "2026-10-11", "source": "x"}
        return {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 1, "position_preset_no": "2.71"}],
                },
                {
                    "group_name": "SIDE",
                    "group_no": 8 if side_confirmed else None,
                    "group_no_confirmed": side_confirmed,
                    "cues": [
                        {
                            "bar": 2,
                            "position_preset_no": "2.71",
                            "evidence": {"grade": None, "approval": approved},
                        }
                    ],
                },
            ],
            **_RECIPE,
        }

    def test_already_approved_cells_of_the_same_number_are_included(self) -> None:
        # 리드 지적(#634) — 이번 승인 대기 칸(BACK)만 모으면 이미 승인된 SIDE 칸의
        # 장비가 프리셋에 빠져 그 큐에서 안 움직인다.
        frames = PointingFrames(
            positions={**_FRAMES.positions, 201: (0.0, 3.0, 5.0)}, rotz={}, rotation_skipped=()
        )
        plan = _plan(
            self._grid_with_approved_side(True),
            [_held("2.71")],
            members={"BACK": [101, 102], "SIDE": [201]},
            frames=frames,
        )
        fixtures = [line.split(" ;")[0] for line in plan.creations["2.71"][:3]]
        assert fixtures == ["Fixture 101", "Fixture 102", "Fixture 201"]

    def test_unconfirmed_track_of_an_approved_cell_holds_the_number(self) -> None:
        plan = _plan(
            self._grid_with_approved_side(False),
            [_held("2.71")],
            members={"BACK": [101, 102], "SIDE": [201]},
        )
        assert plan.creations == {}
        assert [e["hold_reason"] for e in plan.held] == [POSITION_GROUP_UNCONFIRMED]

    def test_non_position_empty_number_is_untouched(self) -> None:
        cue = {"bar": 1, "effect_preset_no": "4.99", "effect_kind": "color", "evidence": None}
        held = [_held("4.99", field="effect_preset_no")]
        plan = _plan(_grid([cue], **_RECIPE), held)
        assert plan.creations == {}
        assert plan.held == held


# -- 세션 배선(가짜 콘솔) --------------------------------------------------------


def _pool(path: str, slots: list[int]) -> dict:
    return {"children": [{"i": slot, "name": f"P{slot}"} for slot in slots], "path": path}


def _apply(tmp_path, cue: dict, *, pool2: list[int] | None, grid_extra=_RECIPE, frames=_FRAMES):
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = [cue]
    timeline["beat_grid"].update(grid_extra)
    tree = _state_tree()
    if pool2 is not None:
        tree["DataPool/PresetPools/2"] = _pool("DataPool/PresetPools/2", pool2)
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    session._beat_grid_group_members = lambda names: {
        n: _MEMBERS[n] for n in names if n in _MEMBERS
    }
    session._beat_grid_pointing_frames = lambda: frames
    status = session.beat_grid_apply()
    return status, store, approval


def _sent(approval) -> list[str]:
    return [item.command for request in approval.requests for item in request.items]


_POSITION_CUE = {"bar": 1, "position_preset_no": "2.71", "evidence": None}


class TestApplyCreatesThePreset:
    def test_creation_lines_ride_the_batch_and_cell_is_approved(self, tmp_path) -> None:
        status, store, approval = _apply(tmp_path, dict(_POSITION_CUE), pool2=[1, 2])
        assert status["ok"] is True
        sent = _sent(approval)
        store_at = sent.index("Store Preset 2.71")
        assert sent[store_at + 1] == "Label Preset 2.71 'LA Center'"
        assert sent[store_at + 2] == "ClearAll"
        assert sent[store_at - 2].startswith("Fixture 101 ;")
        risk = " ".join(approval.requests[0].items[0].risk_reasons)
        assert "새로 만드는 위치 프리셋 1개" in risk
        assert "2.71 'LA Center'" in risk
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is None
        assert status["approval_vs_sent"]["match"] is True

    def test_occupied_slot_is_never_stored(self, tmp_path) -> None:
        # 2.71 이 이미 있다 → split 이 held 로 보내지 않음 → Store 0줄.
        status, _store, approval = _apply(tmp_path, dict(_POSITION_CUE), pool2=[71])
        assert status["ok"] is True
        assert not [c for c in _sent(approval) if c.startswith("Store Preset")]

    def test_unreadable_pool_is_never_stored(self, tmp_path) -> None:
        status, store, approval = _apply(tmp_path, dict(_POSITION_CUE), pool2=None)
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "2.71" in c]
        assert POOL_UNREAD_HOLD in status["reason"]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is not None

    def test_missing_recipe_holds_with_reason(self, tmp_path) -> None:
        status, store, approval = _apply(tmp_path, dict(_POSITION_CUE), pool2=[1], grid_extra={})
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "2.71" in c]
        assert POSITION_TARGET_MISSING in status["reason"]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is not None

    def test_refused_approval_creates_nothing_and_records_nothing(self, tmp_path) -> None:
        timeline = _timeline()
        timeline["beat_grid"]["tracks"][0]["cues"] = [dict(_POSITION_CUE)]
        timeline["beat_grid"].update(_RECIPE)
        tree = _state_tree()
        tree["DataPool/PresetPools/2"] = _pool("DataPool/PresetPools/2", [1])
        store = SongTimelineStore()
        store.latest = timeline
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=tree, decisions=(False,)
        )
        session._beat_grid_group_members = lambda names: {"BACK": [101, 102]}
        session._beat_grid_pointing_frames = lambda: _FRAMES
        status = session.beat_grid_apply()
        assert status["ok"] is False
        assert not [c for c in console.executed if "Preset" in c]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert check_evidence_approval(cue) is not None
