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

from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_segments import generate_segment_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_planned import annotated_cell_colors
from server.design.beat_grid_position_presets import PointingFrames
from server.design.cell_direction import assign_color_names
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

#: 주석 색이 칸에만 있고 계획 색이 없는 칸 — 적용이 시드 칸을 초안 칸으로 바꾸므로 없다.
_ANNOTATION_ONLY: set[tuple[str, int]] = set()


def _applied_grid() -> dict:
    """세션의 자동 배치 적용과 같은 호출로 만든 LOVE ATTACK 격자(계획 색이 칸에 실려 있다)."""
    timeline = json.loads(SHAPE_TIMELINE.read_text(encoding="utf-8"))
    base = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    planned = annotated_cell_colors(load_preset_annotations(LOVE_ATTACK_TITLE))
    draft = generate_segment_draft(timeline["bar_map"], base["tracks"], planned_colors=planned)
    assert draft["note"] is None, draft["note"]
    grid, _report = apply_arrangement_draft(base, draft)
    return grid


def _planned_cells(grid: dict) -> set[tuple[str, int]]:
    """계획 색 칸 전부 — 역할로 빼지 않는다(컬러 채널 유무는 저장 단계가 장비를 읽어 가른다)."""
    return {
        (track["group_name"], cue["bar"])
        for track in grid["tracks"]
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
        # 적용이 시드 칸을 초안 칸으로 바꾸므로 계획 색 없이 번호만 받는 칸은 없다.
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

    def test_a_planned_color_outside_the_table_takes_the_nearest_name(self) -> None:
        # 리드 지시: 이름이 없다고 색 프리셋을 막지 않는다. 표 밖의 색은 가장 가까운 이름을 받는다.
        grid = _applied_grid()
        track = next(t for t in grid["tracks"] if t["group_name"] == "MOVER-U")
        cue = next(c for c in track["cues"] if c["bar"] == 14)
        cue["planned_color"] = [1, 2, 3]  # 주석에도 표준 팔레트에도 없는 색
        plan = _plan(grid)
        expected = assign_color_names([(1, 2, 3)])[(1, 2, 3)]
        mine = [p for p in _color_presets(plan) if ("MOVER-U", 14) in _cells_of(p)]
        assert [p.name for p in mine] == [f"{expected} MOVER-U"]
        assert mine[0].deferred or mine[0].ready or mine[0].reused
        assert not any("계획 색 RGB 1 2 3" in line for line in plan.unresolved), plan.unresolved
        assert all(p.name for p in _color_presets(plan) if p.split_side is None)

    def test_key_and_effect_lines_are_color_candidates_like_any_other_line(self) -> None:
        # 인수 C-06(2026-10-17): FOH 0 · BLIND 18·46·67 · STROBE 63 이 번호 없이 남았다. 역할로
        # 「컬러 채널 없음」을 단정해 후보에서 뺐기 때문이다 — 장비 능력은 채널 판독이 정한다.
        grid = _applied_grid()
        effect_cells = {
            (track["group_name"], cue["bar"])
            for track in grid["tracks"]
            if track.get("layer_role") in {"key", "effect"}
            for cue in track["cues"]
            if isinstance(cue.get("planned_color"), list)
        }
        assert effect_cells == {
            ("FOH", 0),
            ("BLIND", 18),
            ("BLIND", 46),
            ("BLIND", 67),
            ("STROBE", 63),
        }
        updated = _approve(grid, _with_stores(grid, _plan(grid)))
        assert effect_cells <= _numbered_cells(updated)

    def test_a_group_without_color_channels_is_held_with_a_reason_not_numbered(self) -> None:
        # 컬러 채널이 없는 장비(여기선 BLIND 를 디머만 있는 장비로 둔다)는 번호 없이 사유가 남는다.
        grid = _applied_grid()
        plan = _plan(grid)
        members, channels = _fake_reads(grid)
        for fid in members["BLIND"]:
            channels[fid] = ["Dimmer"]
        stored = attach_color_store(plan, grid, members=members, channel_names=channels)
        blind = [p for p in _color_presets(stored) if "BLIND" in p.groups]
        assert blind and all(not p.ready and p.hold for p in blind)
        updated = _approve(grid, stored)
        numbered = _numbered_cells(updated)
        assert not {cell for cell in numbered if cell[0] == "BLIND"}
        assert ("FOH", 0) in numbered

    def test_a_console_number_with_the_same_rgb_and_group_is_reused_without_a_store_line(
        self,
    ) -> None:
        grid = _applied_grid()
        # 라벤더 번호의 기록 — 저장할 때 담은 그룹(WASH-ALL)까지 적혀 있다.
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100, "group": "WASH-ALL"}}
        plan = _with_stores(grid, _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER))
        lavender = next(p for p in _color_presets(plan) if p.slot == "4.33")
        assert lavender.reused is True
        assert lavender.ready is True
        assert lavender.store is None
        # 워시 줄은 구간마다 한 칸이다. 4마디 킥이 벌스라 도입·벌스·빌드가 같은 라벤더(벌스 색)
        # 한 칸이고, 라벤더 칸은 그 칸의 첫 마디(0)다.
        assert ("WASH-ALL", 0) in _cells_of(lavender)
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
        wash_lavender = next(p for p in _color_presets(plan) if ("WASH-ALL", 0) in _cells_of(p))
        assert wash_lavender.slot != "4.33"
        assert wash_lavender.reused is False

    def test_a_number_stored_for_one_group_is_not_reused_by_another(self) -> None:
        # 1차 전체 실행 — 4.106 은 「Group 10 ; Attribute 'ColorRGB_…'」(WASH-ALL)만 담아
        # 저장됐는데(감사 기록 10-16 15:38), 새 분석으로 격자가 비자 그 번호를 쓰는 칸이 없어
        # MOVER-U·MOVER-D 도 같은 RGB 라며 그 번호를 재사용했다. 재사용은 저장한 그룹만이다.
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100, "group": "WASH-ALL"}}
        plan = _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER)
        users = {group for p in _color_presets(plan) if p.slot == "4.33" for group in p.groups}
        assert users == {"WASH-ALL"}
        others = [
            p
            for p in _color_presets(plan)
            if p.rgb is not None and tuple(p.rgb) == (55, 35, 100) and p.groups != ("WASH-ALL",)
        ]
        assert others, "다른 그룹의 라벤더 후보가 있어야 한다(픽스처)"
        assert all(p.slot != "4.33" and not p.reused for p in others)

    def test_an_old_number_without_its_group_is_not_reused_when_no_cell_uses_it(self) -> None:
        # 그룹 기록이 없는 옛 번호(4.106 처럼)는 누가 담겼는지 모른다 — 그 번호를 쓰는 칸이 전부
        # 이 그룹일 때만 재사용한다. 쓰는 칸이 하나도 없으면 재사용하지 않는다(새 번호로 저장).
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100}}
        plan = _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER)
        assert not [p for p in _color_presets(plan) if p.slot == "4.33"]

    def test_an_old_number_is_still_reused_by_the_group_whose_cells_use_it(self) -> None:
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100}}
        wash = next(t for t in grid["tracks"] if t["group_name"] == "WASH-ALL")
        held = next(c for c in wash["cues"] if c["bar"] != 0)
        held["color_preset_no"] = "4.33"  # WASH-ALL 칸만 이 번호를 쓰고 있다
        plan = _plan(grid, color_pool=_COLOR_POOL_WITH_LAVENDER)
        users = {group for p in _color_presets(plan) if p.slot == "4.33" for group in p.groups}
        assert users == {"WASH-ALL"}

    def test_a_new_color_store_records_the_group_it_holds(self) -> None:
        grid = _applied_grid()
        plan = _with_stores(grid, _plan(grid))
        updated = _approve(grid, plan)
        stored = [p for p in _color_presets(plan) if p.store is not None and len(p.groups) == 1]
        assert stored
        for preset in stored:
            assert updated["preset_colors"][preset.slot]["group"] == preset.groups[0]


class TestStoreLinesAndCard:
    def test_each_new_planned_preset_gets_one_store_bundle_and_nothing_is_held_on_the_fake_console(
        self,
    ) -> None:
        grid = _applied_grid()
        plan = _with_stores(grid, _plan(grid))
        new = [p for p in _color_presets(plan) if p.deferred or p.ready]
        held = [p for p in _color_presets(plan) if not p.ready and not p.deferred]
        # 칸이 있는 후보는 전부 저장된다. 남는 것은 주석 색이 칸 없는 마디(워시 14마디 LAVENDER,
        # 22마디 PITCH)에 놓인 주석뿐이다 — 워시 줄은 구간마다 한 칸이고(리드 결정 2026-10-16),
        # 도입·벌스·빌드는 같은 벌스 색이라 0마디 한 칸이다.
        assert [(p.name, p.cells) for p in held] == [("LAVENDER", ()), ("PITCH", ())]
        stores = [line for line in save_commands(plan) if line.startswith("Store Preset 4.")]
        assert len(stores) == len([p for p in new if not p.reused])

    def test_the_card_table_marks_reused_presets(self) -> None:
        grid = _applied_grid()
        grid["preset_colors"] = {"4.33": {"r": 55, "g": 35, "b": 100, "group": "WASH-ALL"}}
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
        # 주석 색 3 + 계획 색 13 + 키·효과 줄(FOH·BLIND·STROBE)의 계획 색 3.
        # 주석 PITCH(워시 22마디)는 구간 중간이라 칸이 없어 저장하지 않는다(워시는 구간마다 한 칸).
        assert len([line for line in card if line.startswith("Store Preset 4.")]) == 19
        numbered = _numbered_cells(store.latest["beat_grid"])
        assert _planned_cells(grid) <= numbered
        assert numbered - _planned_cells(grid) == _ANNOTATION_ONLY
