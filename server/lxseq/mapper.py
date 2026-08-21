"""LX-SEQ 패치 레코드 → 패치 런 계획 (SPEC-COPILOT-LXSEQ-001 M2).

콘솔 접촉은 **읽기 결과를 주입받는 것**뿐이다. 이 모듈은 포트를 직접 열지
않고, 쓰기 수단은 이름조차 다루지 않는다(REQ-LXSEQ-009 — AST 스캔으로 확인).

REQ-LXSEQ-004: 타입은 `resolve_fixture_type` 계약으로만 확정한다.
REQ-LXSEQ-005: 모드는 실측 폭이 유일할 때만 채운다 — CSV `Mode` 문자열은 못 믿는다.
REQ-LXSEQ-006: 런을 만들기 전에 행 단위로 점유를 판정한다.
REQ-LXSEQ-007: 읽기가 전수가 아니면 런 0 — 빈 자리라고 말할 수 없으면 쓰지 않는다.
REQ-LXSEQ-008: 남은 행을 최대 연속 구간으로 묶어 순서 있는 계획을 낸다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from server.lxseq.parser import LxseqPatchRecord
from server.prechk.inventory import COMPLETE, Inventory
from server.prechk.mode_read import TypeModeRead
from server.vwx.addressfit import Occupant, evaluate
from server.vwx.patchplan import ExistingFidRead

# `resolve_fixture_type` 계약의 status 어휘. `present`만 런에 들어간다.
_STATUS_PRESENT = "present"

_TYPE_SKIP_DETAIL = {
    "ambiguous": "콘솔 라이브러리에 후보가 여럿이다 — 후보: {candidates}",
    "absent": "콘솔 라이브러리에 없다 — 콘솔에서 타입 추가 후 재실행하라.",
    "library_unreadable": (
        "라이브러리를 읽지 못했다 — 없다고 단정하지 않는다. 콘솔 연결을 확인하라."
    ),
}


@dataclass(frozen=True)
class ModeResolution:
    console_type: str
    channels: int
    resolution: str  # resolved | unresolved | tree_unread
    console_mode: str | None = None
    resolved_by: str | None = None  # width_unique | label_token | override
    measured_modes: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class SkippedRow:
    fid: int
    address: str
    kind: str
    detail: str
    occupant: dict[str, Any] | None = None
    occupied_fid: int | None = None


@dataclass(frozen=True)
class PatchRun:
    index: int
    group: str
    console_type: str
    address: str
    count: int
    channels_per_fixture: int
    fids: tuple[int, ...]
    name_prefix: str
    footprint_source: str
    console_mode: str | None = None

    def as_tool_arguments(self) -> dict[str, Any]:
        """`patch_fixtures` 호출 인자 그대로 — 스키마 밖 키를 만들지 않는다."""
        args: dict[str, Any] = {
            "console_type": self.console_type,
            "address": self.address,
            "count": self.count,
            "fids": list(self.fids),
            "name_prefix": self.name_prefix,
        }
        if self.console_mode is not None:
            args["console_mode"] = self.console_mode
        return args


@dataclass(frozen=True)
class ImportPlan:
    runs: tuple[PatchRun, ...]
    fid_map: dict[int, dict[str, Any]]
    skipped: tuple[SkippedRow, ...]
    write_count_planned: int
    types_requested: tuple[str, ...]
    mode_resolutions: dict[str, ModeResolution]
    console_read: dict[str, Any]
    blind_spot: str = ""
    name_prefix_mode: str = "group"


def _address_text(record: LxseqPatchRecord) -> str:
    return f"{record.universe}.{record.address}"


def _distinct_types(records: tuple[LxseqPatchRecord, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for record in records:
        if record.fixture_type not in seen:
            seen.append(record.fixture_type)
    return tuple(seen)


def _judge_console_read(
    inventory: Inventory | None, existing_fids: ExistingFidRead
) -> tuple[bool, str]:
    """전수 판독인가. 아니면 왜 아닌가."""
    if inventory is None:
        return False, "인벤토리를 읽지 않았다"
    if inventory.completeness != COMPLETE:
        return False, (
            f"인벤토리 판독이 전수가 아니다(completeness={inventory.completeness}, "
            f"미관측 {inventory.missing_count}건)"
        )
    if not existing_fids.attempted:
        return False, "기존 FID를 조회하지 않았다"
    if existing_fids.root_unreadable:
        return False, "FID 루트를 읽지 못했다"
    unresolved = (
        (existing_fids.unseen or 0)
        + existing_fids.unreadable_fids
        + existing_fids.unusable_rows
        + existing_fids.unparsable_rows
    )
    if unresolved > 0:
        return False, f"FID 판독 미해결 {unresolved}건"
    return True, ""


def _resolve_mode(
    console_type: str,
    csv_type: str,
    channels: int,
    mode_read: TypeModeRead | None,
    override: str | None,
) -> ModeResolution:
    """모드 이름은 콘솔이 안다 — CSV `Mode` 문자열에서 추측하지 않는다."""
    measured = tuple(
        {"name": choice.name, "channels": choice.width}
        for choice in (mode_read.modes if mode_read else ())
    )

    # 모드 트리를 못 읽었으면 폭은 호출자 값을 쓰되 미검증임을 표시한다.
    if mode_read is None or not mode_read.attempted or not mode_read.type_found:
        return ModeResolution(
            console_type=console_type,
            channels=channels,
            resolution="tree_unread",
            console_mode=override,
            resolved_by="override" if override else None,
            measured_modes=measured,
        )

    names = [choice.name for choice in mode_read.modes]
    if override is not None:
        matched = next((n for n in names if n.lower() == override.lower()), None)
        if matched is not None:
            return ModeResolution(
                console_type=console_type,
                channels=channels,
                resolution="resolved",
                console_mode=matched,
                resolved_by="override",
                measured_modes=measured,
            )
        return ModeResolution(
            console_type=console_type,
            channels=channels,
            resolution="unresolved",
            measured_modes=measured,
        )

    same_width = [c for c in mode_read.modes if c.width == channels]
    if len(same_width) == 1:
        return ModeResolution(
            console_type=console_type,
            channels=channels,
            resolution="resolved",
            console_mode=same_width[0].name,
            resolved_by="width_unique",
            measured_modes=measured,
        )

    # 폭이 같은 모드가 여럿이면 CSV `Mode` 라벨의 토큰이 딱 하나에만 걸릴 때만 채택.
    if len(same_width) > 1:
        matched = _match_by_label_token(csv_type, same_width)
        if matched is not None:
            return ModeResolution(
                console_type=console_type,
                channels=channels,
                resolution="resolved",
                console_mode=matched,
                resolved_by="label_token",
                measured_modes=measured,
            )

    return ModeResolution(
        console_type=console_type,
        channels=channels,
        resolution="unresolved",
        measured_modes=measured,
    )


def _match_by_label_token(mode_label: str, candidates: list) -> str | None:
    tokens = [t for t in re.split(r"[^0-9A-Za-z가-힣]+", mode_label) if t]
    hits = [
        choice.name
        for choice in candidates
        if any(token.lower() in choice.name.lower() for token in tokens)
    ]
    return hits[0] if len(hits) == 1 else None


def _occupancy_skip(
    record: LxseqPatchRecord,
    console_type: str,
    channels: int,
    occupants: tuple[Occupant, ...],
    existing_fid_set: frozenset[int],
) -> SkippedRow | None:
    """자리·FID 점유를 행 단위로 판정한다. 덮어쓰는 경로는 존재하지 않는다."""
    address = _address_text(record)

    if record.fid in existing_fid_set:
        return SkippedRow(
            fid=record.fid,
            address=address,
            kind="fid_occupied",
            detail=f"FID {record.fid}는 콘솔에 이미 있다",
            occupied_fid=record.fid,
        )

    # 구간 **안에서 시작하는** 장비만 확정 충돌이다(addressfit 규약 그대로).
    fit = evaluate(address, count=1, width=channels, occupants=occupants)
    if fit.collisions:
        first = fit.collisions[0]
        same_type = (first.fixture_type or "") == console_type
        same_start = first.universe == record.universe and first.address == record.address
        kind = "already_patched" if (same_type and same_start) else "address_occupied"
        detail = (
            "같은 타입이 같은 자리에 이미 있다 — 이미 패치됨"
            if kind == "already_patched"
            else "그 자리를 다른 장비가 쓰고 있다"
        )
        return SkippedRow(
            fid=record.fid,
            address=address,
            kind=kind,
            detail=detail,
            occupant={
                "address": f"{first.universe}.{first.address}",
                "name": first.name,
                "fixture_type": first.fixture_type,
            },
        )
    return None


def build_import_plan(
    *,
    records: tuple[LxseqPatchRecord, ...],
    type_resolutions: dict[str, dict[str, Any]],
    mode_reads: dict[str, TypeModeRead],
    inventory: Inventory | None,
    occupants: tuple[Occupant, ...] = (),
    existing_fids: ExistingFidRead | None = None,
    mode_overrides: dict[str, str] | None = None,
    name_prefix_mode: str = "group",
) -> ImportPlan:
    """레코드를 패치 런 계획으로 바꾼다."""
    records = tuple(records)
    existing_fids = existing_fids or ExistingFidRead()
    mode_overrides = mode_overrides or {}
    types_requested = _distinct_types(records)

    read_complete, reason = _judge_console_read(inventory, existing_fids)
    console_read = {
        "complete_enough_to_judge_absence": read_complete,
        "reason": reason,
    }

    # 읽기가 전수가 아니면 계획을 세우지 않는다 — 빈 자리라고 말할 수 없다.
    if not read_complete:
        return ImportPlan(
            runs=(),
            fid_map={},
            skipped=tuple(
                SkippedRow(
                    fid=record.fid,
                    address=_address_text(record),
                    kind="console_read_incomplete",
                    detail=reason,
                )
                for record in records
            ),
            write_count_planned=0,
            types_requested=types_requested,
            mode_resolutions={},
            console_read=console_read,
            name_prefix_mode=name_prefix_mode,
        )

    skipped: list[SkippedRow] = []
    mode_resolutions: dict[str, ModeResolution] = {}
    existing_fid_set = frozenset(existing_fids.fids)

    # 타입 해석은 **서로 다른 타입마다 한 번씩** — 행 수만큼 부르지 않는다.
    console_types: dict[str, str | None] = {}
    for csv_type in types_requested:
        resolution = type_resolutions.get(csv_type) or {
            "status": "library_unreadable",
            "candidates": [],
        }
        status = resolution.get("status")
        if status == _STATUS_PRESENT:
            console_types[csv_type] = resolution.get("resolved") or csv_type
        else:
            console_types[csv_type] = None

    placeable: list[tuple[LxseqPatchRecord, str, ModeResolution]] = []
    for record in records:
        csv_type = record.fixture_type
        console_type = console_types.get(csv_type)
        if console_type is None:
            resolution = type_resolutions.get(csv_type) or {
                "status": "library_unreadable",
                "candidates": [],
            }
            status = str(resolution.get("status", "library_unreadable"))
            template = _TYPE_SKIP_DETAIL.get(status, _TYPE_SKIP_DETAIL["library_unreadable"])
            candidates = ", ".join(resolution.get("candidates") or [])
            skipped.append(
                SkippedRow(
                    fid=record.fid,
                    address=_address_text(record),
                    kind="type_unresolved",
                    detail=template.format(candidates=candidates),
                )
            )
            continue

        if csv_type not in mode_resolutions:
            mode_resolutions[csv_type] = _resolve_mode(
                console_type=console_type,
                csv_type=record.mode_label,
                channels=record.channels,
                mode_read=mode_reads.get(csv_type) or mode_reads.get(console_type),
                override=mode_overrides.get(csv_type) or mode_overrides.get(console_type),
            )
        mode = mode_resolutions[csv_type]

        if mode.resolution == "unresolved":
            measured = ", ".join(f"{m['name']}({m['channels']})" for m in mode.measured_modes)
            hint = (
                "실측 목록에 없음. "
                if mode_overrides.get(csv_type) or mode_overrides.get(console_type)
                else ""
            )
            skipped.append(
                SkippedRow(
                    fid=record.fid,
                    address=_address_text(record),
                    kind="mode_unresolved",
                    detail=(
                        f"{hint}모드를 확정하지 못했다 — 실측 모드: [{measured}]. "
                        f'mode_overrides: {{"{csv_type}": "<콘솔 모드 이름>"}} 로 재호출하라.'
                    ),
                )
            )
            continue

        occupied = _occupancy_skip(
            record, console_type, record.channels, occupants, existing_fid_set
        )
        if occupied is not None:
            skipped.append(occupied)
            continue

        placeable.append((record, console_type, mode))

    runs = _group_into_runs(placeable, name_prefix_mode=name_prefix_mode)
    fid_map = {
        fid: {
            "address": run.address
            if index == 0
            else f"{run.address.split('.')[0]}."
            f"{int(run.address.split('.')[1]) + index * run.channels_per_fixture}",
            "console_type": run.console_type,
            "run_index": run.index,
        }
        for run in runs
        for index, fid in enumerate(run.fids)
    }
    for row in skipped:
        fid_map.setdefault(
            row.fid, {"address": row.address, "console_type": None, "run_index": None}
        )

    return ImportPlan(
        runs=runs,
        fid_map=fid_map,
        skipped=tuple(skipped),
        write_count_planned=sum(run.count for run in runs),
        types_requested=types_requested,
        mode_resolutions=mode_resolutions,
        console_read=console_read,
        blind_spot=evaluate("1.1", count=1, width=1, occupants=()).blind_spot,
        name_prefix_mode=name_prefix_mode,
    )


def _group_into_runs(
    placeable: list[tuple[LxseqPatchRecord, str, ModeResolution]],
    *,
    name_prefix_mode: str,
) -> tuple[PatchRun, ...]:
    """최대 연속 구간으로 묶는다 — 건너뛴 행이 끼면 런이 갈라진다."""
    runs: list[PatchRun] = []
    current: list[tuple[LxseqPatchRecord, str, ModeResolution]] = []

    def boundary_key(item) -> tuple:
        record, console_type, mode = item
        key = (console_type, mode.resolution, mode.console_mode, record.universe)
        if name_prefix_mode == "group":
            key = (*key, record.group)
        return key

    def flush() -> None:
        if not current:
            return
        head_record, console_type, mode = current[0]
        width = mode.channels if mode.resolution != "tree_unread" else head_record.channels
        runs.append(
            PatchRun(
                index=len(runs),
                group=head_record.group,
                console_type=console_type,
                console_mode=mode.console_mode,
                address=_address_text(head_record),
                count=len(current),
                channels_per_fixture=width,
                fids=tuple(r.fid for r, _, _ in current),
                name_prefix=head_record.group if name_prefix_mode == "group" else console_type,
                footprint_source=(
                    "caller_unverified" if mode.resolution == "tree_unread" else "console_measured"
                ),
            )
        )
        current.clear()

    for item in placeable:
        if not current:
            current.append(item)
            continue
        prev_record, _, _ = current[-1]
        record, _, _ = item
        contiguous = record.address == prev_record.address + prev_record.channels
        if boundary_key(item) == boundary_key(current[-1]) and contiguous:
            current.append(item)
        else:
            flush()
            current.append(item)
    flush()

    return tuple(runs)
