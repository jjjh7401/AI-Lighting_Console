"""자동 배치 계획 위치 → 위치 프리셋 후보 (카드 WT-plan-positions).

콘솔 접촉 0건. 격자는 LOVE ATTACK 마디 지도 픽스처를 세션과 같은 호출(``generate_segment_draft`` →
``apply_arrangement_draft``)로 돌린 자동 배치 적용 격자다. 그룹 소속 · 장비 좌표는 합성 값이다.

검증하는 것: 무빙 칸은 기본 위치 사다리(4종) 안의 계획 위치를 얻고, 구간이 바뀔 때 한 칸씩만
움직인다. 계획 위치는 그룹마다 위치 후보 한 줄이 되고, 그 줄은 기본 위치 10종 조준표에서 같은
이름의 조준값으로 저장된다. 승인 카드 뒤에는 계획 위치가 실린 무빙 칸 전부가 위치 번호를 가진다.
"""

from __future__ import annotations

import copy
import json
from itertools import pairwise
from pathlib import Path

from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_policy import MOVER_POSITION_LADDER
from server.design.arrange_segments import generate_segment_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_planned import annotated_cell_colors
from server.design.beat_grid_position_presets import POSITION_UNAIMABLE, PointingFrames
from server.design.preset_plan import build_preset_plan, load_preset_annotations
from server.design.preset_plan_store import attach_floor_position_store
from server.spatial.pointing import (
    aimed_commands,
    basic_position_presets,
    position_preset_store_commands,
)

from .test_planned_color_presets import (
    _COLOR_POOL,
    _applied_grid,
    _card_session,
    _fake_reads,
)
from .test_preset_plan import _POSITION_CHILDREN
from .test_preset_plan_store_all import _FRAMES, _MEMBERS

SHAPE_TIMELINE = Path(__file__).resolve().parent / "fixtures" / "love_attack_shape_timeline.json"
_POSITION_POOL = (2, _POSITION_CHILDREN)
_MOVER_GROUPS = ("MOVER-U", "MOVER-D")
#: 구간이 바뀔 때마다 옮긴 위치 순서(같은 이름이 이어지면 하나로 본다). 규칙서의 해석이다.
#: 무빙은 어둠 속 사전이동(MIB)이 가능한 곳에서만 옮긴다 — 후렴·드롭을 비우거나 앞 위치의 켜는
#: 칸이 남지 않으면 그 구간에서는 앞 위치에 머문다. 그래서 켜진 채 옮기는 칸이 없다.
_PINNED_LOOKS = {
    "MOVER-U": ["Home", "Center", "Ring In"],
    "MOVER-D": ["Home", "Center", "Ring In"],
}


def _draft(base: dict) -> dict:
    """세션과 같은 호출로 만든 자동 배치 초안(계획 색 포함)."""
    timeline = json.loads(SHAPE_TIMELINE.read_text(encoding="utf-8"))
    planned = annotated_cell_colors(load_preset_annotations(LOVE_ATTACK_TITLE))
    return generate_segment_draft(timeline["bar_map"], base["tracks"], planned_colors=planned)


def _cue(grid: dict, group: str, bar: int) -> dict:
    track = next(t for t in grid["tracks"] if t["group_name"] == group)
    return next(c for c in track["cues"] if c["bar"] == bar)


def _planned_looks(grid: dict, group: str) -> list[tuple[int, str]]:
    """그룹의 계획 위치 칸을 마디 순서대로 — (마디, 기본 위치 이름)."""
    track = next(t for t in grid["tracks"] if t["group_name"] == group)
    return [
        (cue["bar"], cue["planned_position"])
        for cue in track["cues"]
        if isinstance(cue.get("planned_position"), str)
    ]


def _collapse(looks: list[tuple[int, str]]) -> list[str]:
    """같은 이름이 연속되면 하나로 — 칸마다 되풀이되는 값은 빼고 바뀌는 순서만 본다."""
    names: list[str] = []
    for _bar, name in looks:
        if not names or names[-1] != name:
            names.append(name)
    return names


def _planned_mover_cells(grid: dict) -> set[tuple[str, int]]:
    return {
        (track["group_name"], cue["bar"])
        for track in grid["tracks"]
        if track.get("layer_role") == "mover"
        for cue in track["cues"]
        if isinstance(cue.get("planned_position"), str)
    }


def _numbered_mover_cells(grid: dict) -> set[tuple[str, int]]:
    return {
        (track["group_name"], cue["bar"])
        for track in grid["tracks"]
        if track.get("layer_role") == "mover"
        for cue in track["cues"]
        if cue.get("position_preset_no") is not None
    }


def _position_plan(grid: dict, *, position_pool=_POSITION_POOL):
    return build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=_COLOR_POOL,
        position_pool=position_pool,
        dimmer_attributes={},
    )


def _store_plan(grid: dict, frames: PointingFrames | None = _FRAMES):
    plan = _position_plan(grid)
    return attach_floor_position_store(plan, grid, members=_MEMBERS, frames=frames)


def _position_presets(plan) -> list:
    return [preset for preset in plan.presets if preset.kind == "position"]


def _look_presets(plan) -> list:
    """계획 위치 후보 — 기본 위치 이름(``aim``)이 붙은 위치 후보."""
    return [preset for preset in _position_presets(plan) if preset.aim is not None]


def _live_presets(plan) -> list:
    return [preset for preset in _position_presets(plan) if preset.deferred or preset.ready]


def _cells_of(preset) -> set[tuple[str, int]]:
    return {(cell.group_name, cell.bar) for cell in preset.cells}


class TestGeneratorPlansAMoverLook:
    def test_the_section_targets_give_the_pinned_look_sequence(self) -> None:
        grid = _applied_grid()
        for group in _MOVER_GROUPS:
            looks = _planned_looks(grid, group)
            assert looks[0] == (0, "Home"), (group, looks[:1])
            assert all(name in MOVER_POSITION_LADDER for _bar, name in looks), group
            assert _collapse(looks) == _PINNED_LOOKS[group], group

    def test_neighbouring_looks_are_one_ladder_step_apart(self) -> None:
        grid = _applied_grid()
        for group in _MOVER_GROUPS:
            steps = [
                MOVER_POSITION_LADDER.index(name) for name in _collapse(_planned_looks(grid, group))
            ]
            assert all(abs(after - before) == 1 for before, after in pairwise(steps)), group


class TestApplyKeepsStructuredValues:
    def test_an_existing_numbered_cell_keeps_its_number_and_gains_the_planned_look(self) -> None:
        base = copy.deepcopy(_applied_grid())
        cue = _cue(base, "MOVER-U", 4)
        del cue["planned_position"]
        cue["position_preset_no"] = "2.31"

        grid, _report = apply_arrangement_draft(base, _draft(base))

        cue = _cue(grid, "MOVER-U", 4)
        assert cue["position_preset_no"] == "2.31"
        # 4마디(벌스 첫머리)는 앞에 어둠을 둘 자리가 없어 도입 위치(Home)에 머문다.
        assert cue["planned_position"] == "Home"


class TestPlanPositionCandidates:
    def test_each_look_is_one_candidate_per_group_and_covers_exactly_its_cells(self) -> None:
        grid = _applied_grid()
        plan = _position_plan(grid)
        looks = _look_presets(plan)
        keys = [(preset.groups, preset.aim) for preset in looks]
        assert len(keys) == len(set(keys)), keys
        for preset in looks:
            assert len(preset.groups) == 1
            for group, bar in _cells_of(preset):
                assert group == preset.groups[0]
                assert _cue(grid, group, bar)["planned_position"] == preset.aim

    def test_every_unnumbered_planned_cell_is_covered_unless_an_annotated_point_claims_it(
        self,
    ) -> None:
        grid = _applied_grid()
        plan = _position_plan(grid)
        covered = set().union(*(_cells_of(preset) for preset in _look_presets(plan)))
        claimed = set().union(
            *(
                _cells_of(preset)
                for preset in _live_presets(plan)
                if preset.aim is None  # 주석 바닥 점 후보가 먼저 잡은 칸
            )
        )
        assert claimed, "픽스처에는 주석 바닥 점이 잡은 무빙 칸이 있어야 한다"
        expected = _planned_mover_cells(grid) - _numbered_mover_cells(grid) - claimed
        assert covered == expected, (sorted(covered - expected), sorted(expected - covered))

    def test_a_cell_belongs_to_at_most_one_live_candidate_and_numbers_are_distinct(self) -> None:
        plan = _position_plan(_applied_grid())
        seen: set[tuple[str, int]] = set()
        for preset in _live_presets(plan):
            assert not (_cells_of(preset) & seen), preset.name
            seen |= _cells_of(preset)
        slots = [preset.slot for preset in _live_presets(plan)]
        assert len(slots) == len(set(slots)), slots

    def test_a_look_outside_the_ladder_is_held_and_listed_once(self) -> None:
        grid = _applied_grid()
        _cue(grid, "MOVER-U", 14)["planned_position"] = "Wall"  # 사다리 밖의 기본 위치

        plan = _position_plan(grid)

        wall = [preset for preset in _position_presets(plan) if preset.value.startswith("Wall")]
        assert wall
        assert not any(preset.deferred or preset.ready for preset in wall)
        assert sum("Wall" in line for line in plan.unresolved) == 1, plan.unresolved

    def test_an_unreadable_position_pool_holds_every_look(self) -> None:
        plan = _position_plan(_applied_grid(), position_pool=None)
        looks = _look_presets(plan)
        assert looks, "계획 위치 후보가 있어야 한다"
        assert not any(preset.deferred or preset.ready for preset in looks)
        assert all("위치 풀을 콘솔에서 읽지 못해" in preset.hold for preset in looks)

    def test_each_live_look_has_one_supervisor_fix_line_naming_it(self) -> None:
        plan = _position_plan(_applied_grid())
        deferred = [preset for preset in _look_presets(plan) if preset.deferred]
        assert deferred
        for preset in deferred:
            lines = [fix for fix in plan.supervisor_fixes if fix.startswith(preset.name)]
            assert len(lines) == 1, (preset.name, plan.supervisor_fixes)
            assert "감독이 고칠 값" in lines[0]


class TestStoreAimsFromTheBasicLooks:
    def test_a_look_is_stored_with_its_own_group_aims_from_the_rig_look_table(self) -> None:
        grid = _applied_grid()
        plan = _store_plan(grid)
        rig_looks = {
            label: aims
            for label, aims, _skipped in basic_position_presets(sorted(_FRAMES.positions.items()))
        }
        ready = [preset for preset in _look_presets(plan) if preset.ready]
        assert ready, "저장 줄이 붙은 계획 위치 후보가 있어야 한다"
        for preset in ready:
            (group,) = preset.groups
            aims = [aim for aim in rig_looks[preset.aim] if aim[0] in _MEMBERS[group]]
            assert len(aims) == len(_MEMBERS[group]), (preset.name, aims)
            slot = int(preset.slot.partition(".")[2])
            assert tuple(preset.store) == (
                *aimed_commands(aims),
                *position_preset_store_commands(slot, preset.name),
                "ClearAll",
            ), preset.name

    def test_a_planned_look_does_not_repeat_the_floor_point_note(self) -> None:
        plan = _store_plan(_applied_grid())
        preset = next(preset for preset in _look_presets(plan) if preset.ready)
        lines = [fix for fix in plan.supervisor_fixes if fix.startswith(preset.name)]
        assert len(lines) == 1, lines
        assert "바닥점" not in lines[0]

    def test_a_tilted_mover_fixture_holds_the_whole_group_look(self) -> None:
        positions = {fid: pos for fid, pos in _FRAMES.positions.items() if fid != 202}
        frames = PointingFrames(positions=positions, rotz={}, rotation_skipped=(202,))

        plan = _store_plan(_applied_grid(), frames)

        group_looks = [preset for preset in _look_presets(plan) if preset.groups == ("MOVER-U",)]
        assert group_looks
        assert not any(preset.ready for preset in group_looks)
        assert all(POSITION_UNAIMABLE in preset.hold for preset in group_looks)
        assert all("202" in preset.hold for preset in group_looks)

    def test_a_fixture_flagged_as_tilted_is_held_even_while_its_position_stays(self) -> None:
        # 좌표 표에는 남아 있으나 몸체 기울임으로 표시된 장비 — 바닥점 경로처럼 조준하지 않는다.
        frames = PointingFrames(positions=dict(_FRAMES.positions), rotz={}, rotation_skipped=(202,))

        plan = _store_plan(_applied_grid(), frames)

        group_looks = [preset for preset in _look_presets(plan) if preset.groups == ("MOVER-U",)]
        assert group_looks
        assert not any(preset.ready for preset in group_looks)
        assert all(POSITION_UNAIMABLE in preset.hold for preset in group_looks)
        assert all("202" in preset.hold for preset in group_looks)


def _session_frames(grid: dict) -> PointingFrames:
    """카드 시험용 합성 좌표 — 장비를 가로로 흩어 놓는다(실기 리그가 아니다)."""
    fids = [fid for members in _fake_reads(grid)[0].values() for fid in members]
    positions = {
        fid: (round(-6.0 + 12.0 * index / (len(fids) - 1) + 0.37, 2), 2.0 + index % 5, 6.0)
        for index, fid in enumerate(fids)
    }
    return PointingFrames(positions=positions, rotz={}, rotation_skipped=())


class TestTheApprovalCardWritesPlannedLooks:
    def test_the_card_stores_each_planned_look_and_approval_numbers_every_planned_mover_cell(
        self, tmp_path, monkeypatch
    ) -> None:
        grid = _applied_grid()
        session, _console, approval, store = _card_session(
            tmp_path, monkeypatch, grid, decisions=(True,)
        )
        monkeypatch.setattr(session, "_beat_grid_pointing_frames", lambda: _session_frames(grid))

        event = session.beat_grid_preset_plan()

        assert event["ok"] is True
        assert len(approval.requests) == 1  # 카드는 한 장이다
        card = list(approval.requests[0].commands)
        assert any(line.startswith("Store Preset 2.") for line in card)
        planned = _planned_mover_cells(grid)
        assert planned - _numbered_mover_cells(grid), "번호 없는 계획 위치 칸이 있어야 한다"
        numbered = _numbered_mover_cells(store.latest["beat_grid"])
        assert planned <= numbered, sorted(planned - numbered)
