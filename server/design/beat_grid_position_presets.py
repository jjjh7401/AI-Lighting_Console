"""카드 t592 — 박자 격자의 새 위치 프리셋을 콘솔에 만드는 레시피
(SPEC-LDBEAT-001 REQ-LDBEAT-015(i-3)(i-7)(i-8), plan M12).

값의 출처는 곡 격자 ``preset_targets["2.n"]``(무대 목표 좌표 x·y·z, 미터)다.
반영 시점에 그 좌표를 조준 경로(``server/spatial/pointing.py`` — 실측
Pan/Tilt 모델)로 장비별 Pan/Tilt 로 환산하고, t474 run3 실기 선례와 같은
꼴로 만든다: 조준 줄 → ``Store Preset 2.n`` → ``Label Preset 2.n '이름'`` →
``ClearAll``. 콘솔 이름은 t589 와 같은 ``preset_labels["2.n"]`` 자리에서
읽는다(같은 키·모양 — 리드 결정 2026-10-11).

이 모듈은 콘솔에 아무것도 쓰지 않는다 — 순수 함수뿐이다. 만들 후보는
``split_empty_preset_holds``가 「풀은 읽혔고 slot 이 없다」(``EMPTY_PRESET_HOLD``)
로 보류한 위치 번호뿐이다 — 풀을 못 읽었거나 slot 이 있는 번호는 애초에
후보가 아니므로 ``Store Preset``이 기존 슬롯을 덮어쓰는 길이 없다(i-7).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from server.design.beat_grid import CELL_HOLD, EMPTY_PRESET_HOLD, preset_pool_no
from server.design.beat_grid_edit import BeatGridEditError, _assert_ascii_preset_label
from server.design.beat_grid_presets import app_preset_label
from server.spatial.pointing import (
    POSITION_PRESET_POOL,
    SpatialPointingError,
    aim_pan_tilt,
    aimed_commands,
    position_preset_store_commands,
)

__all__ = [
    "POSITION_COORDS_UNREAD",
    "POSITION_GROUP_UNCONFIRMED",
    "POSITION_LABEL_INVALID",
    "POSITION_LABEL_MISSING",
    "POSITION_MEMBERS_UNREAD",
    "POSITION_TARGET_MISSING",
    "POSITION_UNAIMABLE",
    "PointingFrames",
    "PositionPresetPlan",
    "PresetCreationPlan",
    "plan_cells",
    "plan_position_preset_creation",
    "position_preset_outcomes",
    "position_preset_target",
    "record_position_preset_target",
    "referencing_tracks",
]

#: 보류 사유 — 승인 카드와 시험이 같은 값을 읽는다(t590 문구와 나란히).
POSITION_TARGET_MISSING = "위치 프리셋 목표 좌표가 없음"
POSITION_LABEL_MISSING = "위치 프리셋 콘솔 이름(영문)이 없음"
POSITION_LABEL_INVALID = "위치 프리셋 콘솔 이름이 영문·숫자 규칙에 맞지 않음"
POSITION_GROUP_UNCONFIRMED = "트랙 그룹 번호 미확인 — 선택을 만들 수 없음"
POSITION_MEMBERS_UNREAD = "트랙 그룹 소속을 다 읽지 못함"
POSITION_COORDS_UNREAD = "장비 좌표를 다 읽지 못함"
POSITION_UNAIMABLE = "목표를 조준할 수 없는 장비가 있음"

_POSITION_FIELD = "position_preset_no"


@dataclass(frozen=True)
class PointingFrames:
    """콘솔 패치에서 읽은 장비 좌표·회전(``_read_pointing_frames`` 결과).

    ``rotation_skipped`` 는 Rotx/Roty 가 0 이 아니라고 확인된 장비다 —
    조준 모델이 그 축을 보정하지 못하므로 조준하면 틀린다."""

    positions: Mapping[int, tuple[float, float, float]]
    rotz: Mapping[int, float]
    rotation_skipped: Sequence[int] = ()


@dataclass
class PositionPresetPlan:
    """``released``: 만들기 줄이 붙어 승인 기록 대상으로 돌아가는 항목(사본,
    ``hold_reason`` 없음). ``creations``: 번호 → 만들기 줄. ``held``: 여전히
    보류하는 항목(사유를 단 사본)."""

    released: list[dict[str, object]] = field(default_factory=list)
    creations: dict[str, tuple[str, ...]] = field(default_factory=dict)
    held: list[dict[str, object]] = field(default_factory=list)
    #: 카드 t593 — 만든 번호 → 그 번호를 가리킨 필드(``position_preset_no`` /
    #: ``effect_preset_no``). 승인 카드가 종류별로 문구를 가를 때 읽는다.
    creation_fields: dict[str, str] = field(default_factory=dict)


#: 카드 t593 — 위치(t592)·효과(t593)가 같은 칸 판정을 함께 쓴다.
PresetCreationPlan = PositionPresetPlan


def _position_slot(preset_no: object) -> int | None:
    """``"2.71"`` → ``71``. 위치 풀(2)의 ``pool.slot`` 꼴이 아니면 ``None``."""
    if preset_pool_no(preset_no) != POSITION_PRESET_POOL:
        return None
    return int(str(preset_no).partition(".")[2])


def position_preset_target(
    grid: Mapping[str, object], preset_no: str
) -> tuple[float, float, float] | None:
    """곡 격자 ``preset_targets[preset_no]`` 의 목표 좌표. 없거나 세 값이
    유한한 수가 아니면 ``None``(지어내지 않는다)."""
    targets = grid.get("preset_targets")
    if not isinstance(targets, Mapping):
        return None
    raw = targets.get(preset_no)
    if not isinstance(raw, Mapping):
        return None
    values: list[float] = []
    for axis in ("x", "y", "z"):
        value = raw.get(axis)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if not math.isfinite(value):
            return None
        values.append(float(value))
    return (values[0], values[1], values[2])


def record_position_preset_target(
    grid: Mapping[str, object], preset_no: str, target: Sequence[object]
) -> dict[str, object]:
    """새 위치 프리셋의 목표 좌표를 곡 격자에 남기는 단일 저장 자리.
    ``grid``의 사본을 돌려준다(원본은 그대로). 위치 풀 번호가 아니거나
    좌표가 유한한 수 셋이 아니면 거절한다."""
    if _position_slot(preset_no) is None:
        raise ValueError(f"'{preset_no}'은(는) 위치 프리셋(풀 2) 번호가 아닙니다.")
    if len(target) != 3:
        raise ValueError("목표 좌표는 x·y·z 세 값이어야 합니다.")
    coords: list[float] = []
    for value in target:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"목표 좌표 {value!r}는 수가 아닙니다.")
        if not math.isfinite(value):
            raise ValueError(f"목표 좌표 {value!r}는 유한한 수가 아닙니다.")
        coords.append(float(value))
    updated = dict(grid)
    existing = grid.get("preset_targets")
    targets = dict(existing) if isinstance(existing, Mapping) else {}
    targets[preset_no] = {"x": coords[0], "y": coords[1], "z": coords[2]}
    updated["preset_targets"] = targets
    return updated


def referencing_tracks(grid: Mapping[str, object], preset_no: str) -> list[Mapping[str, object]]:
    """``preset_no``를 위치 번호로 가리키는 칸이 하나라도 있는 트랙 **전부** —
    이번 승인 대기 칸만이 아니다. 이미 승인된 칸의 트랙 장비도 같은 프리셋을
    부르므로, 빠지면 그 큐에서 안 움직인다(리드 지적, #634)."""
    result: list[Mapping[str, object]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        if any(
            isinstance(cue, Mapping) and cue.get(_POSITION_FIELD) == preset_no
            for cue in track.get("cues") or []
        ):
            result.append(track)
    return result


def position_grid_blocker(grid: Mapping[str, object], preset_no: str) -> str | None:
    """콘솔을 읽지 않고 격자만으로 알 수 있는 만들기 걸림돌 — ``_plan_one``과 같은
    순서·같은 사유(목표 좌표 → 영문 이름 → 그 번호를 가리키는 트랙의 그룹 확인).
    ``None``이면 남은 조건은 반영 때 읽는 그룹 소속·장비 좌표뿐이다. 격자의
    「빈 프리셋」 표식(카드 t595)이 반영 전에 「반영 때 만듦」을 가를 때 쓴다."""
    if position_preset_target(grid, preset_no) is None:
        return POSITION_TARGET_MISSING
    label = app_preset_label(grid, preset_no)
    if label is None:
        return POSITION_LABEL_MISSING
    try:
        _assert_ascii_preset_label(label)
    except BeatGridEditError:
        return POSITION_LABEL_INVALID
    if any(not track.get("group_no_confirmed") for track in referencing_tracks(grid, preset_no)):
        return POSITION_GROUP_UNCONFIRMED
    return None


def _plan_one(
    grid: Mapping[str, object],
    preset_no: str,
    tracks: Sequence[Mapping[str, object]],
    *,
    members: Mapping[str, Sequence[int]],
    frames: PointingFrames | None,
) -> tuple[tuple[str, ...] | None, str | None]:
    """번호 하나의 만들기 줄 — 또는 (None, 보류 사유). 빠진 것이 하나라도 있으면
    보류한다(일부 장비만 조준한 프리셋을 만들지 않는다)."""
    blocker = position_grid_blocker(grid, preset_no)
    if blocker is not None:
        return None, blocker
    target = position_preset_target(grid, preset_no)
    label = app_preset_label(grid, preset_no)
    assert target is not None and label is not None  # 걸림돌이 없으면 둘 다 있다
    fids: list[int] = []
    for track in tracks:
        if not track.get("group_no_confirmed"):
            return None, POSITION_GROUP_UNCONFIRMED
        track_fids = members.get(str(track.get("group_name")))
        if not track_fids:
            return None, POSITION_MEMBERS_UNREAD
        fids.extend(fid for fid in track_fids if fid not in fids)
    if frames is None or any(fid not in frames.positions for fid in fids):
        return None, POSITION_COORDS_UNREAD
    skipped = set(frames.rotation_skipped)
    aims: list[tuple[int, float, float]] = []
    unaimable: list[int] = []
    for fid in fids:
        if fid in skipped:
            unaimable.append(fid)
            continue
        try:
            pan, tilt = aim_pan_tilt(frames.positions[fid], target, rotz=frames.rotz.get(fid, 0.0))
        except SpatialPointingError:
            unaimable.append(fid)
            continue
        aims.append((fid, pan, tilt))
    if unaimable:
        return None, f"{POSITION_UNAIMABLE}(FID {', '.join(map(str, unaimable))})"
    slot = _position_slot(preset_no)
    assert slot is not None  # 호출자가 위치 풀 번호만 넘긴다
    commands = (
        *aimed_commands(aims),
        *position_preset_store_commands(slot, label),
        "ClearAll",
    )
    return commands, None


Outcome = tuple[tuple[str, ...] | None, str | None]


def position_preset_outcomes(
    grid: Mapping[str, object],
    numbers: Sequence[str],
    *,
    members: Mapping[str, Sequence[int]],
    frames: PointingFrames | None,
) -> dict[str, Outcome]:
    """번호마다 한 번 — 만들기 줄 또는 (None, 보류 사유). 그 번호를 가리키는
    칸의 트랙 전부(이미 승인된 칸 포함)의 소속을 한 프리셋에 담는다."""
    return {
        number: _plan_one(
            grid, number, referencing_tracks(grid, number), members=members, frames=frames
        )
        for number in numbers
    }


# @MX:ANCHOR: [AUTO] 박자 격자 반영이 콘솔에 새 프리셋(위치·효과)을 만드는 칸 판정의 유일한 자리.
# @MX:REASON: ``Store Preset``은 기존 슬롯을 경고 없이 덮어쓴다 — 후보를
#   ``EMPTY_PRESET_HOLD``(풀이 읽혔고 slot 이 없음)로 보류된 번호로만 좁히는
#   이 함수의 입구가 덮어쓰기 0 의 근거다(REQ-LDBEAT-015(i-7)). 위치(t592)·효과(t593)가
#   함께 쓰고, 색(t594)도 같은 입구를 재사용해야 한다.
def plan_cells(
    held: Sequence[Mapping[str, object]],
    outcomes: Mapping[tuple[str, str], Outcome],
) -> PositionPresetPlan:
    """보류 항목을 칸 단위로 판정한다(t590 과 같다). ``outcomes``는 (필드, 번호) →
    만들기 줄 또는 보류 사유이고, 후보는 「풀은 읽혔고 slot 이 없다」로 보류된 항목 중
    ``outcomes``에 있는 것뿐이다.

    칸의 보류 항목이 전부 「만들 수 있는 후보」 또는 「같은 칸이라 함께 보류」(slot 이
    있는 번호)일 때만 그 칸 전체가 승인 기록 대상으로 돌아간다. 풀을 못 읽은 항목·
    만들 수 없는 빈 번호가 하나라도 있으면 칸 전체가 보류로 남고, 그 칸의 번호는
    만들지 않는다."""
    plan = PositionPresetPlan()
    if not held:
        return plan
    cells: dict[tuple[object, object], list[Mapping[str, object]]] = {}
    for entry in held:
        cells.setdefault((entry.get("group_name"), entry.get("bar")), []).append(entry)

    def _key(entry: Mapping[str, object]) -> tuple[str, str]:
        return (str(entry.get("field")), str(entry.get("value")))

    def _candidate(entry: Mapping[str, object]) -> bool:
        return entry.get("hold_reason") == EMPTY_PRESET_HOLD and _key(entry) in outcomes

    for entries in cells.values():
        blockers = [e for e in entries if e.get("hold_reason") != CELL_HOLD and not _candidate(e)]
        failed = {
            _key(e): outcomes[_key(e)][1]
            for e in entries
            if _candidate(e) and outcomes[_key(e)][1] is not None
        }
        has_candidate = any(map(_candidate, entries))
        if has_candidate and not blockers and not failed:
            for entry in entries:
                released = {k: v for k, v in entry.items() if k != "hold_reason"}
                plan.released.append(released)
                if _candidate(entry):
                    field_name, number = _key(entry)
                    commands = outcomes[_key(entry)][0]
                    assert commands is not None
                    plan.creations.setdefault(number, commands)
                    plan.creation_fields.setdefault(number, field_name)
            continue
        for entry in entries:
            reason = entry.get("hold_reason")
            if _candidate(entry):
                reason = failed.get(_key(entry)) or CELL_HOLD
            plan.held.append({**entry, "hold_reason": reason})
    return plan


def plan_position_preset_creation(
    grid: Mapping[str, object],
    held: Sequence[Mapping[str, object]],
    *,
    members: Mapping[str, Sequence[int]],
    frames: PointingFrames | None,
) -> PositionPresetPlan:
    """``split_empty_preset_holds``가 보류한 항목 중 새 위치 프리셋으로 만들 수
    있는 칸을 가려낸다 — 위치 번호만 후보로 본 ``plan_cells``(다른 종류의 빈 번호는
    걸림돌이다). 같은 번호를 가리키는 칸의 트랙 전부(이미 승인된 칸 포함)의 소속을
    한 프리셋에 담는다 — 그중 하나라도 빠지면 그 번호를 가리키는 칸 전부가 보류다."""
    numbers = sorted(
        {
            str(e.get("value"))
            for e in held
            if e.get("field") == _POSITION_FIELD
            and e.get("hold_reason") == EMPTY_PRESET_HOLD
            and _position_slot(e.get("value")) is not None
        }
    )
    outcomes = position_preset_outcomes(grid, numbers, members=members, frames=frames)
    return plan_cells(
        held, {(_POSITION_FIELD, number): outcome for number, outcome in outcomes.items()}
    )
