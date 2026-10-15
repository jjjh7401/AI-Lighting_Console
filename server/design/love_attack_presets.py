"""SPEC-LDRHYTHM-001 stage 2 — LOVE ATTACK 연출 프리셋 계획 (순수 함수).

격자 칸이 쓰는 값(디머 %·색·방향)을 모아 「새로 만들 프리셋」 목록을 만든다.

- 같은 값은 한 프리셋으로 묶고 칸 수를 센다(de-dup).
- 번호는 콘솔 풀을 **읽은** 결과에서 빈 번호만 고른다 — 있는 번호는 덮지 않는다.
- 값·이름·대상 그룹이 확정되지 않은 것은 「미정」으로 남긴다(지어내지 않는다).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 콘솔 풀 판독 결과와 디머 속성은 인자로 받는다.
승인 카드에 실을 저장 줄은 `save_commands`가 만들고, 칸의 번호 참조는 승인 **뒤에만**
`apply_plan_references`가 적는다 — 카드가 거절되면 격자는 바이트까지 그대로다.

저장 범위(이 단계): 기본 디머 프리셋만. 색은 RGB 가 정해지면 기존 「＋ 새 프리셋」 색
경로(t594)로, 위치는 목표 좌표가 정해지면 기존 위치 경로(t592)로 만든다 — 그 두
경로는 이 카드에 싣지 않는다(계획표에는 후보 번호와 사유로 남는다).
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from server.design.app_movement import brightness_value_commands
from server.design.beat_grid import (
    apply_pending_approval,
    check_evidence_approval,
    pending_preset_approvals,
    preset_pool_no,
)
from server.design.beat_grid_edit import apply_beat_grid_edit
from server.design.beat_grid_presets import (
    first_free_base_color_number,
    first_free_base_dimmer_number,
    first_free_base_position_number,
)

__all__ = [
    "LoveAttackPlan",
    "PlanCell",
    "PlanPreset",
    "apply_plan_references",
    "load_love_attack_annotations",
    "plan_love_attack_presets",
    "save_commands",
]

#: 계획 주석(칸의 색·방향 대응) — 격자 데이터와 같은 디렉터리.
_ANNOTATIONS_PATH = Path(__file__).resolve().parent / "beat_grid_data" / "love_attack_presets.yaml"

#: 디머 프리셋 콘솔 이름 접두 — 값으로 이름을 짓는다(같은 값 = 같은 이름).
_DIMMER_NAME_PREFIX = "DIM"

#: 풀 판독 결과 — ``(풀 번호, {슬롯: 이름 또는 None})``. 못 읽었으면 ``None``.
PoolRead = tuple[int, Mapping[int, object]] | None


@dataclass(frozen=True)
class PlanCell:
    """계획이 쓰는 칸 하나(그룹 이름 + 마디)."""

    group_name: str
    bar: int


@dataclass(frozen=True)
class PlanPreset:
    """계획표의 프리셋 한 줄.

    ``slot``은 이 계획이 고른 **후보** 번호다(콘솔 풀에서 빈 것). ``ready``가 참이면
    이 카드가 저장 줄을 만들고, 거짓이면 ``hold``가 「미정」 사유다."""

    kind: str  # "dimmer" | "color" | "position"
    value: str  # 사람이 읽는 값: "40%" · "RGB 미정" · "바닥 쪽"
    name: str  # 콘솔 이름(영문·숫자·공백·_.-)
    slot: str | None  # 후보 "pool.slot"; 풀을 못 읽으면 None
    cells: tuple[PlanCell, ...]
    groups: tuple[str, ...]  # 쓰는 그룹 이름(첫 등장 순)
    ready: bool
    hold: str | None  # ready 가 아니면 사유, ready 이면 None
    value_percent: int | None = None
    group_no: int | None = None  # 디머만 — 저장 선택에 쓰는 그룹 번호(확인된 것)
    attributes: tuple[str, ...] = ()  # 디머만 — 그 그룹의 디머 속성 이름


@dataclass(frozen=True)
class LoveAttackPlan:
    presets: tuple[PlanPreset, ...]
    #: 「미정」 목록 — 사람이 정해야 할 것(사유 문장). 계획표 밖 항목 포함.
    unresolved: tuple[str, ...]
    #: 격자에 이미 있는 고정 번호와 그 칸 수 — 계획은 이것을 건드리지 않는다.
    kept: tuple[tuple[str, int], ...]


def load_love_attack_annotations(path: Path | None = None) -> dict[str, object]:
    """계획 주석 YAML을 읽는다. 읽기 실패는 숨기지 않고 그대로 올린다."""
    target = path if path is not None else _ANNOTATIONS_PATH
    with target.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return dict(document) if isinstance(document, Mapping) else {}


def _grid_cues(grid: Mapping[str, object]) -> list[tuple[str, object, bool, Mapping[str, object]]]:
    """(그룹 이름, 그룹 번호, 번호 확인 여부, 칸)을 트랙 순서대로 돌려준다."""
    rows: list[tuple[str, object, bool, Mapping[str, object]]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        group = str(track.get("group_name"))
        group_no = track.get("group_no")
        confirmed = bool(track.get("group_no_confirmed"))
        for cue in track.get("cues") or []:
            if isinstance(cue, Mapping):
                rows.append((group, group_no, confirmed, cue))
    return rows


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)


def _reserve_next(
    pool: PoolRead,
    first_free,
    *,
    policy: Mapping[str, object],
    grid: Mapping[str, object],
    reserved: Sequence[str],
) -> str | None:
    """콘솔이 쥔 빈 번호 중 다음 것을 고른다. 이 계획이 이미 고른 번호는 점유처럼 가린다
    — 같은 풀에서 두 번째 후보가 첫 번째와 겹치지 않게."""
    if pool is None:
        return None
    pool_no, children = pool
    taken = {
        int(number.partition(".")[2]): None
        for number in reserved
        if preset_pool_no(number) == pool_no
    }
    number, _reason = first_free(
        policy=policy, grid=grid, console_children=(pool_no, {**children, **taken})
    )
    return number


def _annotated_cells(
    raw: object,
    by_cell: Mapping[tuple[str, int], object],
    unresolved: list[str],
) -> tuple[PlanCell, ...]:
    """주석의 칸 목록 → 격자에 실제로 있는 칸만.

    없는 칸은 조용히 버리지 않고 「미정」 목록으로 알린다."""
    cells: list[PlanCell] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, Mapping):
            continue
        group = str(item.get("group_name"))
        bar = int(item.get("bar"))  # type: ignore[arg-type]
        if (group, bar) in by_cell:
            cells.append(PlanCell(group, bar))
        else:
            unresolved.append(f"주석 칸 {group} {bar}마디가 격자에 없음 — 주석을 고쳐야 함")
    return tuple(cells)


def _grid_cue(grid: Mapping[str, object], cell: PlanCell) -> Mapping[str, object] | None:
    for group, _no, _confirmed, cue in _grid_cues(grid):
        if group == cell.group_name and cue.get("bar") == cell.bar:
            return cue
    return None


def _prior_approval_source(grid: Mapping[str, object], cell: PlanCell) -> str | None:
    """칸에 이미 완전한 승인이 있었다면 그 출처. 승인 기록을 덮지 않고 덧붙이려고 본다."""
    cue = _grid_cue(grid, cell)
    if cue is None or check_evidence_approval(cue) is not None:
        return None
    evidence = cue.get("evidence")
    approval = evidence.get("approval") if isinstance(evidence, Mapping) else None
    source = approval.get("source") if isinstance(approval, Mapping) else None
    return str(source) if source else None


def plan_love_attack_presets(
    grid: Mapping[str, object],
    *,
    annotations: Mapping[str, object],
    policy: Mapping[str, object],
    dimmer_pool: PoolRead,
    color_pool: PoolRead,
    position_pool: PoolRead,
    dimmer_attributes: Mapping[str, Sequence[str]],
) -> LoveAttackPlan:
    """격자 칸에서 새로 만들 프리셋 계획을 만든다(콘솔 무접촉, 순수 함수).

    - 디머: 칸의 ``brightness.value_percent``를 값으로 묶는다(같은 값 = 한 프리셋).
    - 색·방향: ``annotations``(``love_attack_presets.yaml``)가 칸에 붙인 색·방향만 쓴다.
    - 번호: 풀 판독(``dimmer_pool``·``color_pool``·``position_pool``)에서 빈 것만 고른다.
    - 이미 있는 번호는 ``kept``로 세기만 하고 건드리지 않는다.
    """
    rows = _grid_cues(grid)
    by_cell: dict[tuple[str, int], tuple[object, bool]] = {}
    for group, group_no, confirmed, cue in rows:
        if isinstance(cue.get("bar"), int):
            by_cell[(group, int(cue["bar"]))] = (group_no, confirmed)  # type: ignore[index]

    unresolved: list[str] = []
    presets: list[PlanPreset] = []
    reserved: list[str] = []

    # -- 디머: 칸의 value_percent 를 값으로 묶는다(첫 등장 순) -------------------
    uses: dict[int, list[tuple[str, object, bool, int]]] = {}
    for group, group_no, confirmed, cue in rows:
        brightness = cue.get("brightness")
        if not isinstance(brightness, Mapping) or brightness.get("mode") != "value":
            continue
        percent = brightness.get("value_percent")
        if percent is None:
            continue
        if isinstance(percent, bool) or not isinstance(percent, int):
            unresolved.append(f"{group} {cue.get('bar')}마디: 밝기 값 {percent!r}은 정수 %가 아님")
            continue
        uses.setdefault(percent, []).append((group, group_no, confirmed, int(cue["bar"])))  # type: ignore[arg-type]

    for percent, uses_of_value in uses.items():
        cells = tuple(PlanCell(group, bar) for group, _no, _c, bar in uses_of_value)
        groups = _unique(group for group, _no, _c, _bar in uses_of_value)
        slot = _reserve_next(
            dimmer_pool, first_free_base_dimmer_number, policy=policy, grid=grid, reserved=reserved
        )
        if slot is not None:
            reserved.append(slot)
        holds: list[str] = []
        if dimmer_pool is None:
            holds.append("디머 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        group_no_value: int | None = None
        attributes: tuple[str, ...] = ()
        if len(groups) > 1:
            holds.append(
                f"그룹 {len(groups)}개({', '.join(groups)})가 같은 값을 씀 — 디머 프리셋 저장은 "
                "그룹 하나를 고른다. 그룹마다 따로 저장할지, 여러 그룹을 고른 저장을 쓸지 정해야 함"
            )
        else:
            group = groups[0]
            _g, raw_no, confirmed, _b = uses_of_value[0]
            if (
                confirmed
                and isinstance(raw_no, int)
                and not isinstance(raw_no, bool)
                and raw_no > 0
            ):
                group_no_value = raw_no
            else:
                holds.append(f"그룹 '{group}' 번호가 확인되지 않음")
            attributes = tuple(dimmer_attributes.get(group) or ())
            if not attributes:
                holds.append(f"그룹 '{group}'의 디머 속성을 콘솔에서 읽지 못함")
        ready = not holds and slot is not None
        presets.append(
            PlanPreset(
                kind="dimmer",
                value=f"{percent}%",
                name=f"{_DIMMER_NAME_PREFIX}-{percent}",
                slot=slot,
                cells=cells,
                groups=groups,
                ready=ready,
                hold=None if ready else "; ".join(holds),
                value_percent=percent,
                group_no=group_no_value,
                attributes=attributes if ready else (),
            )
        )

    # -- 색: 주석이 칸에 붙인 색 이름. RGB 가 없으면 「미정」 -----------------------
    for entry in annotations.get("colors") or []:
        if not isinstance(entry, Mapping):
            continue
        cells = _annotated_cells(entry.get("cells"), by_cell, unresolved)
        groups = _unique(cell.group_name for cell in cells)
        slot = _reserve_next(
            color_pool, first_free_base_color_number, policy=policy, grid=grid, reserved=reserved
        )
        if slot is not None:
            reserved.append(slot)
        holds = []
        if color_pool is None:
            holds.append("색 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        rgb = entry.get("rgb")
        if rgb is None:
            holds.append(f"RGB 미정 — {str(entry.get('note') or '').strip()}")
            value = "RGB 미정"
        else:
            holds.append("색 저장은 기존 「＋ 새 프리셋」 색 경로(t594)로 만든다 — 이 카드 범위 밖")
            value = "RGB " + " ".join(str(channel) for channel in rgb)
        presets.append(
            PlanPreset(
                kind="color",
                value=value,
                name=str(entry.get("console_name") or ""),
                slot=slot,
                cells=cells,
                groups=groups,
                ready=False,
                hold="; ".join(holds),
            )
        )

    # -- 위치: 방향 이름만. 목표 좌표가 없어 전부 「미정」 ---------------------------
    for entry in annotations.get("directions") or []:
        if not isinstance(entry, Mapping):
            continue
        cells = _annotated_cells(entry.get("cells"), by_cell, unresolved)
        groups = _unique(cell.group_name for cell in cells)
        slot = _reserve_next(
            position_pool,
            first_free_base_position_number,
            policy=policy,
            grid=grid,
            reserved=reserved,
        )
        if slot is not None:
            reserved.append(slot)
        holds = []
        if position_pool is None:
            holds.append("위치 풀을 콘솔에서 읽지 못해 빈 번호를 알 수 없음")
        holds.append("목표 좌표 미정 — 프로젝트에 방향→좌표 표가 없어 위치 프리셋을 만들 수 없음")
        if len(groups) > 1:
            holds.append("위치 프리셋은 그룹마다 따로 저장해야 함")
        presets.append(
            PlanPreset(
                kind="position",
                value=str(entry.get("name") or ""),
                name=str(entry.get("console_name") or ""),
                slot=slot,
                cells=cells,
                groups=groups,
                ready=False,
                hold="; ".join(holds),
            )
        )

    # -- 「미정」 목록: 계획표 밖 항목 -------------------------------------------
    for preset in presets:
        if not preset.ready:
            unresolved.append(
                f"{preset.name} {preset.value}(칸 {len(preset.cells)}개, 후보 "
                f"{preset.slot or '없음'}): {preset.hold}"
            )
    for entry in annotations.get("relative_position_cells") or []:
        if not isinstance(entry, Mapping):
            continue
        group = str(entry.get("group_name"))
        bar = entry.get("bar")
        if (group, bar) in by_cell:
            label = entry.get("label")
            unresolved.append(
                f"{group} {bar}마디 「{label}」 — 상대 이동·새 자리라 위치 프리셋이 아님(미정)"
            )
    for memo in grid.get("scene_memos") or []:
        if isinstance(memo, Mapping):
            unresolved.append(
                f"SCENE 메모 {memo.get('bar')}마디(칸이 아니라 계획 밖): {memo.get('text')}"
            )
    if policy.get("confirmed") is not True:
        unresolved.append(
            "프리셋 번호대 미확정(preset_pools.yaml confirmed: false) — 효과 밴드 밖의 빈 번호를 "
            "골랐으나 실기 대조 전이다"
        )

    # -- 칸에 이미 있는 고정 번호(건드리지 않음) -----------------------------------
    kept_counts: dict[str, int] = {}
    for _group, _no, _confirmed, cue in rows:
        numbers: list[str] = []
        brightness = cue.get("brightness")
        if (
            isinstance(brightness, Mapping)
            and brightness.get("mode") in ("dimmer_preset", "dimmer_effect")
            and brightness.get("preset_no") is not None
        ):
            numbers.append(str(brightness["preset_no"]))
        for field in ("position_preset_no", "color_preset_no", "effect_preset_no"):
            if cue.get(field) is not None:
                numbers.append(str(cue[field]))
        for number in numbers:
            kept_counts[number] = kept_counts.get(number, 0) + 1

    return LoveAttackPlan(
        presets=tuple(presets),
        unresolved=tuple(unresolved),
        kept=tuple(sorted(kept_counts.items())),
    )


def save_commands(plan: LoveAttackPlan) -> tuple[str, ...]:
    """승인 카드에 실을 저장 줄. **준비된 기본 디머 프리셋만** 싣는다.

    묶음 꼴은 색 레시피(t594)와 같다 — ClearAll → 선택+값 → Store Preset → Label Preset
    → ClearAll. 선택+값 줄은 emitter 가 디머 값을 내는 그 줄(``brightness_value_commands``)
    이라 같은 문법을 쓴다. 묶음 사이의 ClearAll 은 하나로 합친다."""
    lines: list[str] = []
    for preset in plan.presets:
        if not preset.ready or preset.kind != "dimmer":
            continue
        assert preset.group_no is not None and preset.value_percent is not None
        assert preset.slot is not None
        if not lines:
            lines.append("ClearAll")
        lines.extend(
            brightness_value_commands(
                group_no=preset.group_no,
                value_percent=preset.value_percent,
                dimmer_attributes=preset.attributes,
            )
        )
        lines.append(f"Store Preset {preset.slot}")
        lines.append(f"Label Preset {preset.slot} '{preset.name}'")
        lines.append("ClearAll")
    return tuple(lines)


def apply_plan_references(
    grid: Mapping[str, object],
    plan: LoveAttackPlan,
    *,
    by: str,
    date: str,
    source: str,
    planned_from: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """**승인 뒤에만** 부른다. 준비된 디머 프리셋을 그 칸의 밝기로 참조시키고, 참조가 바뀐
    칸·필드를 승인으로 적는다. 칸에 이미 있던 승인은 출처를 덧붙여 남긴다(기록 유실 방지).

    이 함수는 ``grid`` 를 건드리지 않고 새 사본을 돌려준다. 승인 전에는 호출하지 않는다 —
    카드가 거절되면 격자는 바이트까지 그대로다.

    ``planned_from`` — 계획을 세운 때의 격자. 승인 창이 떠 있는 사이 감독이 고친 칸을 지우지
    않으려고, 승인 뒤 **지금** 격자(``grid``)를 넘기고 계획 시점 격자를 여기 넘긴다. 그 사이
    밝기가 바뀐(또는 사라진) 칸은 건너뛴다 — 감독의 새 편집이 계획보다 우선이다."""
    updated: dict[str, object] = copy.deepcopy(dict(grid))
    touched: list[tuple[PlanCell, str | None]] = []
    for preset in plan.presets:
        if not preset.ready or preset.kind != "dimmer" or preset.slot is None:
            continue
        for cell in preset.cells:
            cue = _grid_cue(grid, cell)
            if planned_from is not None:
                planned_cue = _grid_cue(planned_from, cell)
                if (
                    cue is None
                    or planned_cue is None
                    or cue.get("brightness") != planned_cue.get("brightness")
                ):
                    continue
            prior = _prior_approval_source(grid, cell)
            evidence = cue.get("evidence") if cue is not None else None
            grade = evidence.get("grade") if isinstance(evidence, Mapping) else None
            # 옛 승인은 옛 번호의 것이라 이 편집에서 비운다(grade 는 보존). 안 비우면 승인 기록이
            # 새 번호 1.x 를 덮어 "승인됨"으로 거짓 통과한다. 공유 편집 경로도 이제 디머 기본
            # 프리셋 번호 변경을 승인 대기로 세지만, 여기서는 명시적으로 비운 뒤 아래에서 이
            # 카드의 승인을 적는다.
            updated, _report = apply_beat_grid_edit(
                updated,
                bar=cell.bar,
                target=cell.group_name,
                changes={
                    "brightness": {
                        "mode": "dimmer_preset",
                        "value_percent": None,
                        "preset_no": preset.slot,
                    },
                    "evidence": {"grade": grade, "approval": None},
                },
            )
            touched.append((cell, prior))
    pending = pending_preset_approvals(updated)
    for cell, prior in touched:
        entries = [
            entry
            for entry in pending
            if entry["group_name"] == cell.group_name and entry["bar"] == cell.bar
        ]
        if not entries:
            continue
        cell_source = source if prior is None else f"{prior} | {source}"
        updated = apply_pending_approval(updated, entries, by=by, date=date, source=cell_source)
    return updated
