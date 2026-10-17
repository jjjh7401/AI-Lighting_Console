"""SPEC-LDRHYTHM-001 stage 2 — 연출 프리셋 계획의 색·위치 저장 줄 (순수 함수, 콘솔 무접촉).

`build_preset_plan` 은 색과 위치를 「후보」(``PlanPreset.deferred``)로만 낸다 — 그룹 소속 · 컬러
채널 · 장비 좌표는 콘솔을 읽어야 알 수 있기 때문이다. 이 모듈은 호출자가 읽어 온 값을 받아 후보마다
저장 줄(``PlanPreset.store``)을 만들어 계획에 붙인다. 줄을 못 만든 후보는 사유와 함께 「미정」으로
내려간다(``resolve_preset``). 콘솔에는 아무것도 쓰지 않는다 — 읽은 결과는 인자로 받는다.

- 색: 기존 「＋ 새 프리셋」 색 경로(t594)와 **같은 함수**(``color_preset_outcomes``)가 줄을 만든다.
  그 함수는 격자가 이미 그 번호를 가리키고 RGB·이름이 적힌 모양을 읽으므로, 승인 뒤 적을 모양을
  격자 **사본**에 미리 적어 넘긴다. 진짜 격자는 건드리지 않는다.
- 위치: 기존 위치 경로(t592)의 조각 — 보류 사유 · ``aim_pan_tilt`` · ``aimed_commands`` ·
  ``position_preset_store_commands`` — 으로 줄을 만든다. 목표는 장비마다 「x 유지 · y=cy · z=0」인
  바닥점이다(cy 는 읽은 장비 전체의 y 평균 — ``lxseq.position_derive`` 무대 기준틀과 같은 정의).
  좌표 표가 아니라 근사값이라 줄을 붙일 때마다 「감독이 고칠 값」을 한 줄 남긴다. 이 목표 모델은
  계획이 위치 후보로 내는 방향 전부에 쓴다 — 다른 모양의 방향을 더하려면 방향별 목표 필드가
  먼저 필요하다.
- 칸을 이미 번호가 가리키면 덮어쓰지 않는다 — 계획을 다시 돌려도 같은 칸에 프리셋이 겹으로
  생기지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from server.design.beat_grid import preset_pool_no
from server.design.beat_grid_color_presets import (
    color_preset_outcomes,
    group_has_no_color,
    record_color_preset_rgb,
)
from server.design.beat_grid_edit import (
    BeatGridEditError,
    _assert_ascii_preset_label,
    apply_beat_grid_edit,
)
from server.design.beat_grid_position_presets import (
    POSITION_COORDS_UNREAD,
    POSITION_GROUP_UNCONFIRMED,
    POSITION_LABEL_INVALID,
    POSITION_LABEL_MISSING,
    POSITION_MEMBERS_UNREAD,
    POSITION_UNAIMABLE,
    PointingFrames,
)
from server.design.beat_grid_presets import record_app_preset_label
from server.design.preset_plan import (
    LoveAttackPlan,
    PlanCell,
    PlanPreset,
    _grid_cue,
    resolve_preset,
)
from server.spatial.pointing import (
    POSITION_PRESET_POOL,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    basic_position_presets,
    position_preset_store_commands,
)

__all__ = [
    "attach_color_store",
    "attach_floor_position_store",
    "store_candidates",
]

#: 후보 종류 → (칸에서 그 프리셋을 가리키는 필드, 화면 이름).
_REFERENCE = {
    "color": ("color_preset_no", "색 프리셋"),
    "position": ("position_preset_no", "위치 프리셋"),
}

#: 위치 프리셋은 그룹마다 따로 저장한다 — 계획이 줄마다 그룹 하나를 담아 낸다.
#: 한 줄에 그룹이 여럿이면 만들지 않는다.
_PER_GROUP_HOLD = "위치 프리셋은 그룹마다 따로 저장해야 함"


def store_candidates(plan: LoveAttackPlan, kind: str | None = None) -> tuple[PlanPreset, ...]:
    """저장 줄을 기다리는 후보 — 값이 정해진 색·위치(``deferred``). ``kind`` 로 하나만 고른다.

    칸 하나의 왼쪽·오른쪽 색 후보는 이름을 감독이 정하므로 뺀다(기존 색 경로로 간다)."""
    return tuple(
        preset
        for preset in plan.presets
        if preset.kind in _REFERENCE
        and (kind is None or preset.kind == kind)
        and preset.deferred
        and preset.split_side is None
        and not preset.ready
    )


def _occupied_cells(grid: Mapping[str, object], preset: PlanPreset) -> list[PlanCell]:
    """후보의 칸 중 이미 그 종류 번호를 가진 칸. 있던 번호를 덮어쓰지 않는다."""
    field, _label = _REFERENCE[preset.kind]
    return [
        cell
        for cell in preset.cells
        if (cue := _grid_cue(grid, cell)) is not None and cue.get(field) is not None
    ]


def _occupied_hold(grid: Mapping[str, object], preset: PlanPreset) -> str | None:
    """후보의 칸 중 이미 그 종류 번호를 가진 칸이 있으면 사유. 있던 번호를 덮어쓰지 않는다."""
    taken = _occupied_cells(grid, preset)
    if not taken:
        return None
    _field, label = _REFERENCE[preset.kind]
    where = ", ".join(f"{cell.group_name} {cell.bar}마디" for cell in taken)
    return f"{label} 번호가 이미 있는 칸이라 덮어쓰지 않음: {where}"


def _after_edits(
    grid: Mapping[str, object], preset: PlanPreset, changes: Mapping[str, object]
) -> Mapping[str, object]:
    """``changes`` 를 후보의 칸마다 적은 격자 사본. 승인 뒤 `apply_plan_references` 가 같은 편집 길
    (``apply_beat_grid_edit``)을 타므로, 여기서 거절되는 편집은 카드가 뜨기 전에 사유가 된다
    (``ValueError``). 진짜 격자는 그대로다."""
    edited = grid
    for cell in preset.cells:
        edited, _report = apply_beat_grid_edit(
            edited, bar=cell.bar, target=cell.group_name, changes=changes
        )
    return edited


def _color_store(
    grid: Mapping[str, object],
    preset: PlanPreset,
    *,
    members: Mapping[str, Sequence[int]],
    channel_names: Mapping[int, Sequence[str | None] | None],
) -> tuple[tuple[str, ...] | None, str | None]:
    number = preset.slot or ""
    try:
        virtual = record_color_preset_rgb(grid, number, preset.rgb or ())
        virtual = record_app_preset_label(virtual, number, preset.name)
        virtual = _after_edits(virtual, preset, {"color_preset_no": number})
    except ValueError as error:  # BeatGridEditError 도 ValueError 다
        return None, str(error)
    return color_preset_outcomes(virtual, [number], members=members, channel_names=channel_names)[
        number
    ]


def attach_color_store(
    plan: LoveAttackPlan,
    grid: Mapping[str, object],
    *,
    members: Mapping[str, Sequence[int]],
    channel_names: Mapping[int, Sequence[str | None] | None],
) -> LoveAttackPlan:
    """색 후보마다 저장 줄을 붙인 새 계획. 줄은 기존 색 경로(t594)의 ``color_preset_outcomes`` 가
    만든다 — 같은 선행 조건(RGB · 영문 이름 · 그룹 번호 확인 · 한 그룹 · 컬러 채널)이 그대로 걸린다.

    ``grid`` 는 계획을 세운 격자다. 후보 번호를 가리키는 **사본**을 만들어 넘기므로 ``grid`` 는
    바뀌지 않는다. 줄을 못 만든 후보는 ``ready`` 가 아니고 사유가 ``hold`` 다(「미정」)."""
    for preset in store_candidates(plan, "color"):
        # 이미 번호가 있는 칸(감독이 고친 칸 등)만 빼고 나머지 칸은 저장한다. 한 칸 때문에 후보
        # 전체를 보류하면, 이 후보에 합쳐진 계획 색 칸이 전부 번호 없이 남는다.
        taken = _occupied_cells(grid, preset)
        cells = tuple(cell for cell in preset.cells if cell not in taken)
        if not cells:
            plan = resolve_preset(plan, preset, store=None, hold=_occupied_hold(grid, preset))
            continue
        # 컬러 채널이 하나도 없는 그룹(예: 디머만 있는 블라인더)의 칸은 이 색을 낼 수 없다 — 그 칸만
        # 빼고 나머지 칸은 저장한다. 주석 색은 여러 그룹 칸을 한 후보로 묶어서, 빼지 않으면 그 그룹
        # 하나가 후보 전체를 막는다(full3 C-06: 핑크 24칸 중 BLIND 3칸 때문에 21칸이 번호 없음).
        colorless = tuple(
            group
            for group in preset.groups
            if group_has_no_color(members.get(group) or (), channel_names)
        )
        kept = tuple(cell for cell in cells if cell.group_name not in colorless)
        if colorless and kept:
            dropped = len(cells) - len(kept)
            note = (
                f"{preset.name} — {'·'.join(colorless)} 칸 {dropped}개는 컬러 채널이 없는 장비라 "
                "색 프리셋을 쓰지 않는다(나머지 칸만 저장)"
            )
            groups = tuple(group for group in preset.groups if group not in colorless)
            narrowed = replace(preset, cells=kept, groups=groups)
            store, hold = _color_store(grid, narrowed, members=members, channel_names=channel_names)
            plan = resolve_preset(
                plan, preset, store=store, hold=hold, cells=kept, groups=groups, fixes=(note,)
            )
            continue
        narrowed = replace(preset, cells=cells)
        store, hold = _color_store(grid, narrowed, members=members, channel_names=channel_names)
        plan = resolve_preset(plan, preset, store=store, hold=hold, cells=cells)
    return plan


def _aim_store(
    number: str,
    name: str,
    *,
    aim: str,
    fids: Sequence[int],
    frames: PointingFrames,
) -> tuple[tuple[str, ...] | None, str | None]:
    """계획 위치(기본 위치 이름 ``aim``)의 저장 줄. 장비 좌표 전체로 세운 기본 위치 10종
    (``basic_position_presets``)에서 그 이름의 조준값만 쓴다 — 콘솔 포지션 메뉴와 같은 기준이다.
    그룹 장비 전부가 그 룩을 조준해야 하고, 한 대라도 빠지면 프리셋을 만들지 않는다."""
    try:
        looks = {
            label: (aims, skipped)
            for label, aims, skipped in basic_position_presets(sorted(frames.positions.items()))
        }
    except SpatialPointingError:
        return None, "기본 위치 조준 표를 세우지 못함(장비 좌표를 다시 읽는다)"
    if aim not in looks:
        return None, f"기본 위치 「{aim}」이 조준 표에 없음"
    look_aims, look_skipped = looks[aim]
    aimed = {fid: (pan, tilt) for fid, pan, tilt in look_aims}
    # 몸체 기울임으로 조준에서 뺀 장비는 좌표 표에 남아 있어도 조준하지 않는다(바닥점 경로와 같다).
    tilted = set(frames.rotation_skipped)
    unaimable = [fid for fid in fids if fid in look_skipped or fid in tilted or fid not in aimed]
    if unaimable:
        return None, f"{POSITION_UNAIMABLE}(FID {', '.join(map(str, unaimable))})"
    slot = int(number.partition(".")[2])
    bundle = (
        *aimed_commands([(fid, *aimed[fid]) for fid in fids]),
        *position_preset_store_commands(slot, name),
        "ClearAll",
    )
    return bundle, None


def _position_store(
    grid: Mapping[str, object],
    preset: PlanPreset,
    *,
    members: Mapping[str, Sequence[int]],
    frames: PointingFrames | None,
) -> tuple[tuple[str, ...] | None, str | None]:
    if len(preset.groups) != 1:
        return None, _PER_GROUP_HOLD
    (group,) = preset.groups
    number = preset.slot or ""
    if preset_pool_no(number) != POSITION_PRESET_POOL:
        return None, f"위치 풀(Preset {POSITION_PRESET_POOL}) 번호가 아님: {number or '없음'}"
    if not preset.name:
        return None, POSITION_LABEL_MISSING
    try:
        _assert_ascii_preset_label(preset.name)
    except BeatGridEditError:
        return None, POSITION_LABEL_INVALID
    # t592 와 같은 선행 조건 — 트랙의 그룹 번호가 확인된 그룹만 만든다.
    if not any(
        isinstance(track, Mapping)
        and str(track.get("group_name")) == group
        and track.get("group_no_confirmed")
        for track in grid.get("tracks") or []
    ):
        return None, POSITION_GROUP_UNCONFIRMED
    try:
        _after_edits(grid, preset, {"position_preset_no": number})
    except ValueError as error:
        return None, str(error)
    fids = list(members.get(group) or ())
    if not fids:
        return None, POSITION_MEMBERS_UNREAD
    # 몸체 기울임(Rotx/Roty ≠ 0)으로 조준에서 빠진 장비는 실기 판독
    # (``_beat_grid_pointing_frames``)이 좌표 표에서도 뺀다. 그대로 두면 아래 검사가 「좌표를
    # 못 읽음」이라 말해 원인이 틀리다 — 좌표는 읽혔고 조준만 못 한다. 보류는 그대로이고 사유
    # 문장만 바로잡는다. 좌표 표에 든 채 제외 표시만 된 장비는 아래 조준 단계의 기존 사유가 맡는다.
    if frames is not None:
        tilted = [
            fid for fid in fids if fid in frames.rotation_skipped and fid not in frames.positions
        ]
        if tilted:
            return None, (
                f"{POSITION_UNAIMABLE}(FID {', '.join(map(str, tilted))}) — "
                "몸체 기울임(Rotx/Roty가 0이 아님)이라 조준에서 제외됨"
            )
    if frames is None or any(fid not in frames.positions for fid in fids):
        return None, POSITION_COORDS_UNREAD
    if preset.aim is not None:
        return _aim_store(number, preset.name, aim=preset.aim, fids=fids, frames=frames)
    # 무대 기준틀 cy — 읽은 장비 전체의 y 평균(lxseq.position_derive._stage_frame 과 같은 정의).
    # 몸체 기울임으로 읽기에서 빠진 장비는 평균에도 못 든다.
    cy = sum(position[1] for position in frames.positions.values()) / len(frames.positions)
    skipped = set(frames.rotation_skipped)
    aims: list[tuple[int, float, float]] = []
    unaimable: list[int] = []
    for fid in fids:
        position = frames.positions[fid]
        if fid in skipped:
            unaimable.append(fid)
            continue
        try:
            pan, tilt = aim_pan_tilt(
                position, (position[0], cy, 0.0), rotz=frames.rotz.get(fid, 0.0)
            )
        except SpatialPointingError:
            unaimable.append(fid)
            continue
        aims.append((fid, pan, tilt))
    if unaimable:
        return None, f"{POSITION_UNAIMABLE}(FID {', '.join(map(str, unaimable))})"
    slot = int(number.partition(".")[2])
    bundle = (
        *aimed_commands(aims),
        *position_preset_store_commands(slot, preset.name),
        "ClearAll",
    )
    return bundle, None


def _floor_note(preset: PlanPreset) -> str:
    return (
        f"{preset.name} 위치는 바닥점 대략값이다(장비 x 유지 · y=cy · z=0, cy 는 읽은 장비 전체의 "
        "y 평균) — 감독이 고칠 값: 실기 바닥 위치를 확인한다."
    )


def attach_floor_position_store(
    plan: LoveAttackPlan,
    grid: Mapping[str, object],
    *,
    members: Mapping[str, Sequence[int]],
    frames: PointingFrames | None,
) -> LoveAttackPlan:
    """위치 후보(그룹마다 한 줄)마다 저장 줄을 붙인 새 계획. 장비마다 「x 유지 · y=cy · z=0」
    바닥점을 조준하는 줄 → ``Store Preset`` → ``Label Preset`` → ``ClearAll`` 이다(기존 위치
    경로 t592 와 같은 꼴). 계획 위치(``aim`` 이 있는 후보)는 바닥점 대신 기본 위치 10종의
    조준값을 쓴다.

    줄을 붙인 바닥점 후보마다 「감독이 고칠 값」을 한 줄 남긴다 — 바닥점은 좌표 표가
    아닌 근사값이다. 계획 위치는 빌드 때 이미 그 줄을 실었으므로 여기서 또 싣지 않는다.
    그룹 소속 · 장비 좌표를 못 읽었거나 조준할 수 없는 장비가 있으면 줄을 만들지 않고 사유를
    ``hold`` 로 남긴다(일부 장비만 조준한 프리셋을 만들지 않는다)."""
    for preset in store_candidates(plan, "position"):
        hold = _occupied_hold(grid, preset)
        store = None
        if hold is None:
            store, hold = _position_store(grid, preset, members=members, frames=frames)
        fixes = (_floor_note(preset),) if store is not None and preset.aim is None else ()
        plan = resolve_preset(plan, preset, store=store, hold=hold, fixes=fixes)
    return plan
