"""자동 배치 계획 색 → 색 프리셋 후보 (카드 WT-plan-planned-colors).

콘솔 접촉 0건. 격자는 LOVE ATTACK 마디 지도 픽스처를 세션과 같은 호출(``generate_segment_draft`` →
``apply_arrangement_draft``)로 돌린 자동 배치 적용 격자다. 색 풀 판독·그룹 소속·컬러 채널은 가짜다.

검증하는 것: 계획 색이 실린 칸은 전부 승인 뒤 색 번호를 가진다. 같은 그룹·같은 RGB 는 한
프리셋이다. 콘솔에 같은 RGB·같은 그룹의 번호가 있으면 저장 줄 없이 그 번호를 쓴다. 이름이 없는
색은 지어내지 않는다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from server.design.arrange_apply import apply_arrangement_draft, director_blank_cells
from server.design.arrange_segments import generate_segment_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_planned import annotated_cell_colors
from server.design.beat_grid_position_presets import PointingFrames
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    load_preset_annotations,
    plan_table_markdown,
    save_commands,
)
from server.design.preset_plan_store import attach_color_store
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import (
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline_for_apply,
)
from .test_preset_plan import _COLOR_CHILDREN, _DIMMER_CHILDREN, _POSITION_CHILDREN

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SHAPE_TIMELINE = FIXTURES / "love_attack_shape_timeline.json"

#: 색 풀 — 1~10 과 32 가 이미 쓰이고 있다(테스트 픽스처). 나머지 번호는 빈 것으로 본다.
_COLOR_POOL = (4, {**{slot: f"COLOR {slot}" for slot in range(1, 11)}, 32: "COLOR 32"})
#: 같은 픽스처에 라벤더 번호 4.33 이 이미 있다(콘솔에 있는 같은 RGB 재사용 시험용).
_COLOR_POOL_WITH_LAVENDER = (
    4,
    {**_COLOR_POOL[1], 33: "LAVENDER"},
)
_RGB_CHANNELS = ["Main Module#2_ColorRGB_R", "Main Module#2_ColorRGB_G", "Main Module#2_ColorRGB_B"]
_DATE = "2026-10-16T00:00:00+00:00"

#: 주석 색이 칸에만 있고 자동 배치 계획 색이 없는 칸(주석 색 경로가 이미 번호를 붙인다).
_ANNOTATION_ONLY = {
    ("WASH-ALL", 7),
    ("WASH-ALL", 14),
    ("WASH-ALL", 18),
    ("WASH-ALL", 22),
    ("BACK", 0),
}


def _applied_grid() -> dict:
    """세션의 자동 배치 적용과 같은 호출로 만든 LOVE ATTACK 격자(계획 색이 칸에 실려 있다)."""
    timeline = json.loads(SHAPE_TIMELINE.read_text(encoding="utf-8"))
    base = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    planned = annotated_cell_colors(load_preset_annotations(LOVE_ATTACK_TITLE))
    draft = generate_segment_draft(timeline["bar_map"], base["tracks"], planned_colors=planned)
    assert draft["note"] is None, draft["note"]
    blanks = director_blank_cells(default_beat_grid(LOVE_ATTACK_TITLE))
    grid, _report = apply_arrangement_draft(base, draft, director_blanks=blanks)
    return grid


#: 색 후보에서 빼는 역할 — 키(FOH)·효과(BLIND·STROBE)는 컬러 채널이 없는 장비다(리드 결정).
_NO_COLOR_ROLES = {"key", "effect"}


def _planned_cells(grid: dict) -> set[tuple[str, int]]:
    """색 후보 범위의 계획 색 칸 — 키·효과 역할 줄은 세지 않는다."""
    return {
        (track["group_name"], cue["bar"])
        for track in grid["tracks"]
        if track.get("layer_role") not in _NO_COLOR_ROLES
        for cue in track["cues"]
        if isinstance(cue.get("planned_color"), list)
    }


def _no_color_cells(grid: dict) -> set[tuple[str, int]]:
    """키·효과 역할 줄의 계획 색 칸 — 색 후보에 아예 들어가지 않아야 한다."""
    return {
        (track["group_name"], cue["bar"])
        for track in grid["tracks"]
        if track.get("layer_role") in _NO_COLOR_ROLES
        for cue in track["cues"]
        if isinstance(cue.get("planned_color"), list)
    }


def _numbered_cells(grid: dict) -> set[tuple[str, int]]:
    return {
        (track["group_name"], cue["bar"])
        for track in grid["tracks"]
        for cue in track["cues"]
        if cue.get("color_preset_no") is not None
    }


def _fake_reads(grid: dict) -> tuple[dict, dict]:
    """합성 그룹 소속·컬러 채널(실기 리그가 아니다). 그룹마다 두 장비, 모두 RGB 채널이 있다."""
    members = {}
    channels = {}
    for index, track in enumerate(grid["tracks"]):
        fids = [100 * (index + 1) + 1, 100 * (index + 1) + 2]
        members[track["group_name"]] = fids
        for fid in fids:
            channels[fid] = list(_RGB_CHANNELS)
    return members, channels


def _plan(grid: dict, *, color_pool=_COLOR_POOL):
    return build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=color_pool,
        position_pool=None,
        dimmer_attributes={},
    )


def _with_stores(grid: dict, plan, *, color_pool=_COLOR_POOL):
    members, channels = _fake_reads(grid)
    return attach_color_store(plan, grid, members=members, channel_names=channels)


def _approve(grid: dict, plan) -> dict:
    return apply_plan_references(
        grid,
        plan,
        by="supervisor",
        date=_DATE,
        source="preset_plan:test",
        planned_from=grid,
    )


def _color_presets(plan) -> list:
    return [preset for preset in plan.presets if preset.kind == "color"]


def _cells_of(preset) -> set[tuple[str, int]]:
    return {(cell.group_name, cell.bar) for cell in preset.cells}


class TestPlannedColorCandidates:
    def test_every_planned_color_cell_gets_a_color_number_after_approval(self) -> None:
        grid = _applied_grid()
        plan = _with_stores(grid, _plan(grid))
        updated = _approve(grid, plan)
        numbered = _numbered_cells(updated)
        planned = _planned_cells(grid)
        assert planned, "픽스처에 계획 색 칸이 있어야 한다"
        assert planned - numbered == set(), "계획 색이 실린 칸은 전부 번호를 받아야 한다"
        # 번호가 붙은 칸 중 계획 색이 없는 칸은 주석 색 경로가 이미 붙인 칸뿐이다.
        assert numbered - planned == _ANNOTATION_ONLY

    def test_the_plan_has_one_color_preset_per_group_and_rgb(self) -> None:
        grid = _applied_grid()
        plan = _plan(grid)
        keys = [(preset.groups, preset.rgb) for preset in _color_presets(plan) if preset.groups]
        assert len(keys) == len(set(keys)), keys

    def test_names_follow_the_annotation_then_the_palette_and_carry_the_group_elsewhere(
        self,
    ) -> None:
        grid = _applied_grid()
        names = {preset.name for preset in _color_presets(_plan(grid))}
        # 주석 색은 주석의 콘솔 이름을 그대로 쓴다(WASH-ALL 라벤더 = LAVENDER).
        assert "LAVENDER" in names
        assert "PINK" in names and "SKY" in names
        # 다른 그룹의 같은 색은 「이름 그룹」, 주석에 없는 드롭·브릿지 색은 표준 팔레트 이름이다.
        assert "LAVENDER SIDE-ALL" in names
        assert "AMBER MOVER-D" in names
        assert "COOL WHITE WASH-ALL" in names

    def test_a_planned_color_with_no_name_is_held_and_not_guessed(self) -> None:
        grid = _applied_grid()
        track = next(t for t in grid["tracks"] if t["group_name"] == "MOVER-U")
        cue = next(c for c in track["cues"] if c["bar"] == 14)
        cue["planned_color"] = [1, 2, 3]  # 주석에도 표준 팔레트에도 없는 색
        plan = _plan(grid)
        live = [p for p in _color_presets(plan) if p.ready or p.deferred or p.reused]
        assert ("MOVER-U", 14) not in set().union(*(_cells_of(p) for p in live))
        assert any("계획 색 RGB 1 2 3" in line for line in plan.unresolved), plan.unresolved

    def test_key_and_effect_lines_are_not_counted_as_color_candidates_at_all(self) -> None:
        grid = _applied_grid()
        no_color_groups = {
            track["group_name"]
            for track in grid["tracks"]
            if track.get("layer_role") in _NO_COLOR_ROLES
        }
        assert _no_color_cells(grid), "픽스처에 키·효과 줄의 계획 색 칸이 있어야 한다"
        plan = _with_stores(grid, _plan(grid))
        updated = _approve(grid, plan)
        assert not (_no_color_cells(grid) & _numbered_cells(updated))
        assert not any(
            group in no_color_groups for preset in _color_presets(plan) for group in preset.groups
        )
        covered = set().union(*(_cells_of(p) for p in _color_presets(plan)))
        assert not (_no_color_cells(grid) & covered)


class TestConsoleNumberReuse:
    def test_a_console_number_with_the_same_rgb_and_group_is_reused_without_a_store_line(
        self,
    ) -> None:
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100}}  # 라벤더 번호의 기록
        plan = _with_stores(grid, _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER))
        lavender = next(p for p in _color_presets(plan) if p.slot == "4.33")
        assert lavender.reused is True
        assert lavender.ready is True
        assert lavender.store is None
        assert ("WASH-ALL", 7) in _cells_of(lavender)
        lines = save_commands(plan)
        assert not any("Store Preset 4.33" in line for line in lines)
        updated = _approve(grid, plan)
        for group, bar in _cells_of(lavender):
            cue = next(
                c
                for c in next(t for t in updated["tracks"] if t["group_name"] == group)["cues"]
                if c["bar"] == bar
            )
            assert cue["color_preset_no"] == "4.33"

    def test_a_number_used_by_another_group_is_not_reused(self) -> None:
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100}}
        back0 = next(
            c
            for t in grid["tracks"]
            if t["group_name"] == "BACK"
            for c in t["cues"]
            if c["bar"] == 0
        )
        back0["color_preset_no"] = "4.33"  # 다른 그룹(BACK)이 이 번호를 쓰고 있다
        plan = _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER)
        wash_lavender = next(p for p in _color_presets(plan) if ("WASH-ALL", 7) in _cells_of(p))
        assert wash_lavender.slot != "4.33"
        assert wash_lavender.reused is False


class TestStoreLinesAndCard:
    def test_each_new_planned_preset_gets_one_store_bundle_and_nothing_is_held_on_the_fake_console(
        self,
    ) -> None:
        grid = _applied_grid()
        plan = _with_stores(grid, _plan(grid))
        new = [p for p in _color_presets(plan) if p.deferred or p.ready]
        held = [p for p in _color_presets(plan) if not p.ready and not p.deferred]
        assert held == []
        stores = [line for line in save_commands(plan) if line.startswith("Store Preset 4.")]
        assert len(stores) == len([p for p in new if not p.reused])

    def test_the_card_table_marks_reused_presets(self) -> None:
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100}}
        plan = _with_stores(grid, _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER))
        table = plan_table_markdown(plan)
        assert "재사용(이 카드)" in table
        assert "저장(이 카드)" in table


def _card_session(tmp_path, monkeypatch, grid: dict, *, decisions):
    """세션 승인 카드 경로 — 자동 배치 적용 격자를 격자로 두고, 콘솔 판독은 합성 값으로 채운다."""
    store = SongTimelineStore()
    store.latest = _timeline_for_apply(beat_grid=grid)
    state_tree = {
        **_state_tree(),
        "DataPool/PresetPools": _pool_list_payload({"Dimmer": 1, "Position": 2, "Color": 4}),
        "DataPool/PresetPools/1": _pool_children_payload(_DIMMER_CHILDREN),
        "DataPool/PresetPools/2": _pool_children_payload(_POSITION_CHILDREN),
        "DataPool/PresetPools/4": _pool_children_payload(_COLOR_CHILDREN),
    }
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, decisions=decisions, state_tree=state_tree
    )
    members, channels = _fake_reads(grid)
    monkeypatch.setattr(
        session,
        "_beat_grid_preset_dimmer_attributes",
        lambda names: {name: ("Dimmer",) for name in names},
    )
    monkeypatch.setattr(
        session,
        "_beat_grid_group_members",
        lambda names: {group: list(members[group]) for group in names if group in members},
    )
    monkeypatch.setattr(
        session,
        "_beat_grid_color_channel_names",
        lambda fids: {fid: list(channels[fid]) for fid in fids if fid in channels},
    )
    monkeypatch.setattr(
        session,
        "_beat_grid_pointing_frames",
        lambda: PointingFrames(positions={}, rotz={}, rotation_skipped=()),
    )
    return session, console, approval, store


class TestTheApprovalCard:
    def test_the_card_stores_each_new_color_and_approval_numbers_every_planned_cell(
        self, tmp_path, monkeypatch
    ) -> None:
        grid = _applied_grid()
        session, _console, approval, store = _card_session(
            tmp_path, monkeypatch, grid, decisions=(True,)
        )

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert len(approval.requests) == 1  # 카드는 한 장이다
        card = list(approval.requests[0].commands)
        # 주석 색 4 + 계획 색 13. 키·효과 줄(FOH·BLIND·STROBE)의 프리셋 3개는 세지 않는다.
        assert len([line for line in card if line.startswith("Store Preset 4.")]) == 17
        numbered = _numbered_cells(store.latest["beat_grid"])
        assert _planned_cells(grid) <= numbered
        assert numbered - _planned_cells(grid) == _ANNOTATION_ONLY
