"""칸마다 방향 값 하나 — 운영 경로 전체 시험 (SPEC-LDRHYTHM-001 D4·D8·D9·D10·D11, 리드 지시).

운영 경로와 같은 호출(``generate_segment_draft`` → ``apply_arrangement_draft``)로 LOVE ATTACK
격자를 만들고 그 격자로 프리셋 계획을 세워 승인까지 간다. 칸의 라벨·색 이름·위치·움직임은 칸 하나의
방향 값(``direction``)에서 나오고, 계획의 프리셋 이름과 승인 뒤의 움직임도 그 값을 따른다. 콘솔
접촉 0건 — 풀 판독·그룹 소속·컬러 채널·장비 좌표는 전부 시험 픽스처다.
"""

from __future__ import annotations

from server.design.arrange_policy import MOVER_POSITION_LADDER
from server.design.beat_grid import LOVE_ATTACK_TITLE
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.cell_direction import label_value_mismatches
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    load_preset_annotations,
)
from server.design.preset_plan_store import attach_color_store, attach_floor_position_store

from .test_planned_color_presets import _COLOR_POOL, _applied_grid, _fake_reads
from .test_preset_plan import _POSITION_CHILDREN
from .test_preset_plan_store_all import _FRAMES, _MEMBERS

_EFFECT_POOL = (21, {slot: f"EFX {slot}" for slot in range(1, 8)})
_POSITION_POOL = (2, _POSITION_CHILDREN)
_NO_COLOR_ROLES = {"key", "effect"}
_KINDS = {"pulse", "chase", "motion", "hold", "blind", "strobe", "static", "rest", "pre_hit"}


def _cells(grid: dict):
    for track in grid["tracks"]:
        for cue in track["cues"]:
            yield track, cue


def _lit(cue: dict) -> bool:
    value = (cue.get("brightness") or {}).get("value_percent")
    return isinstance(value, int) and value > 0


def _plan_and_approval() -> tuple[dict, object, dict]:
    """(적용된 격자, 저장 줄까지 붙인 계획, 승인 뒤 격자) — 승인 전 격자는 건드리지 않는다."""
    grid = _applied_grid()
    plan = build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=_COLOR_POOL,
        position_pool=_POSITION_POOL,
        dimmer_attributes={},
        effect_pool=_EFFECT_POOL,
        bpm=128.0,
        beats_per_bar=4,
    )
    members, channels = _fake_reads(grid)
    movers = {group: _MEMBERS[group] for group in ("MOVER-U", "MOVER-D")}
    members = {**members, **movers}
    rgb = next(iter(channels.values()))
    channels = {**channels, **{fid: list(rgb) for fids in movers.values() for fid in fids}}
    plan = attach_color_store(plan, grid, members=members, channel_names=channels)
    plan = attach_floor_position_store(plan, grid, members=members, frames=_FRAMES)
    approved = apply_plan_references(
        grid,
        plan,
        by="supervisor",
        date="2026-10-16T00:00:00+00:00",
        source="preset_plan:test",
        planned_from=grid,
    )
    return grid, plan, approved


def test_every_lit_cell_has_a_complete_direction() -> None:
    grid = _applied_grid()
    lit = [(track, cue) for track, cue in _cells(grid) if _lit(cue)]
    assert lit, "픽스처에 켜진 칸이 있어야 한다"
    incomplete: list[tuple[str, int, str]] = []
    for track, cue in lit:
        direction = cue.get("direction")
        role = track.get("layer_role")
        name = (str(track["group_name"]), cue["bar"])
        if not isinstance(direction, dict):
            incomplete.append((*name, "direction 없음"))
            continue
        problems = []
        if direction.get("brightness_percent") != cue["brightness"]["value_percent"]:
            problems.append("brightness_percent")
        if direction.get("effect_kind") not in _KINDS:
            problems.append("effect_kind")
        if not isinstance((direction.get("entry") or {}).get("trigger_beat"), int):
            problems.append("entry.trigger_beat")
        color = direction.get("color") or {}
        if not (isinstance(color.get("rgb"), list) and len(color["rgb"]) == 3):
            problems.append("color.rgb")
        if not (isinstance(color.get("name"), str) and color["name"].strip()):
            problems.append("color.name")
        if role == "mover" and (direction.get("position") or {}).get("name") not in (
            MOVER_POSITION_LADDER
        ):
            problems.append("position.name")
        if (direction.get("effect_kind") == "motion") != (direction.get("movement") is not None):
            problems.append("movement")
        if direction.get("effect_kind") == "motion":
            movement = direction["movement"]
            if not (
                movement.get("shape") and movement.get("axes") and movement.get("period_value")
            ):
                problems.append("movement 내용")
        if problems:
            incomplete.append((*name, ",".join(problems)))
    assert incomplete == []


def test_labels_and_values_agree_on_the_applied_grid() -> None:
    assert label_value_mismatches(_applied_grid()) == []


def test_color_names_are_one_to_one_with_rgb_across_the_grid() -> None:
    by_name: dict[str, set[tuple[int, ...]]] = {}
    for _track, cue in _cells(_applied_grid()):
        color = (cue.get("direction") or {}).get("color")
        if color:
            by_name.setdefault(color["name"], set()).add(tuple(color["rgb"]))
    assert by_name
    assert [name for name, rgbs in by_name.items() if len(rgbs) != 1] == []


def test_plan_has_no_unnamed_color_or_position_row() -> None:
    _grid, plan, _approved = _plan_and_approval()
    unnamed = [
        (preset.kind, preset.value)
        for preset in plan.presets
        if preset.kind in ("color", "position") and preset.split_side is None and not preset.name
    ]
    assert unnamed == []


def test_plan_stores_color_presets_so_naming_never_empties_it() -> None:
    _grid, plan, _approved = _plan_and_approval()
    stored = [preset for preset in plan.presets if preset.kind == "color" and preset.ready]
    assert stored, "이름 때문에 저장할 색 프리셋이 0개가 되면 안 된다"


def test_plan_row_names_follow_the_cells_color_names() -> None:
    grid, plan, _approved = _plan_and_approval()
    direction_names = {
        tuple(cue["direction"]["color"]["rgb"]): cue["direction"]["color"]["name"]
        for _track, cue in _cells(grid)
        if (cue.get("direction") or {}).get("color")
    }
    for preset in plan.presets:
        if preset.kind == "color" and preset.rgb is not None and preset.rgb in direction_names:
            assert preset.name.startswith(direction_names[preset.rgb]), (
                preset.name,
                direction_names[preset.rgb],
            )


def test_wave_cells_keep_their_movement_after_the_effect_number_is_assigned() -> None:
    grid, _plan, approved = _plan_and_approval()
    waves = {
        (track["group_name"], cue["bar"]): cue
        for track, cue in _cells(grid)
        if (cue.get("app_movement") or {}).get("shape") == "wave"
    }
    assert waves
    after = {(track["group_name"], cue["bar"]): cue for track, cue in _cells(approved)}
    lost = []
    for key, before in waves.items():
        cue = after[key]
        if not cue.get("effect_preset_no"):
            lost.append((key, "효과 번호 없음"))
        elif cue.get("app_movement") != before["app_movement"]:
            lost.append((key, "app_movement"))
        elif (cue.get("direction") or {}).get("movement") != before["direction"]["movement"]:
            lost.append((key, "direction.movement"))
    assert lost == []


def test_labels_and_values_still_agree_after_the_plan_is_approved() -> None:
    _grid, _plan, approved = _plan_and_approval()
    assert label_value_mismatches(approved) == []


def test_planning_again_after_approval_does_not_propose_the_numbered_wave_cells_again() -> None:
    # 효과 번호를 받은 칸이 움직임(app_movement)을 그대로 가지므로, 다시 계획을 세워도 같은 칸에
    # 효과 프리셋이 또 생기면 안 된다.
    _grid, _plan, approved = _plan_and_approval()
    again = build_preset_plan(
        approved,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=_COLOR_POOL,
        position_pool=_POSITION_POOL,
        dimmer_attributes={},
        effect_pool=_EFFECT_POOL,
        bpm=128.0,
        beats_per_bar=4,
    )
    numbered = {
        (track["group_name"], cue["bar"])
        for track, cue in _cells(approved)
        if cue.get("effect_preset_no")
    }
    claimed = {
        (cell.group_name, cell.bar)
        for preset in again.presets
        if preset.kind == "effect"
        for cell in preset.cells
    }
    assert numbered, "승인 뒤 효과 번호를 받은 칸이 있어야 한다"
    assert numbered & claimed == set()
