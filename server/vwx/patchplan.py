from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol

from server.vwx.address import ADDRESS_BASIS_ABS_BACK_CALCULATED
from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_OVERLAP_IN_PLAN,
    COMPARISON_NOT_PERFORMED,
    FID_ALREADY_IN_USE,
    FID_CONFLICT_PRECHECK_DESCOPE,
    FID_RANGE_CONFIRMATION_REQUIRED,
    FID_RANGE_EXHAUSTED,
    FID_RANGE_REQUIRED,
    FOOTPRINT_UNKNOWN,
    INVALID_FID_RANGE,
    INVALID_REPORT_PAYLOAD,
    UNKNOWN_CANDIDATE_ID,
    autopatch_label,
    skipped_check_label,
    target_exclusion_label,
    validate_autopatch,
)

IRREVERSIBLE_WARNING = (
    "이 앱에는 실행 취소·백업 복원 경로가 없고, 잘못 생성된 픽스처는 콘솔에서 사람이 지워야 한다."
)
SOURCE_PATH_MISSING_IN_CONSOLE = "diffs.missing_in_console"
FID_FIXTURE_ROOT = "Patch/Stages/1/Fixtures"
FID_PROPERTY_NAME = "FID"

ASSUMPTION_71_GO = "go"
ASSUMPTION_71_NEGATIVE = "negative"
ASSUMPTION_71_INCONCLUSIVE = "inconclusive"
ASSUMPTION_71_VALUES = frozenset(
    {
        ASSUMPTION_71_GO,
        ASSUMPTION_71_NEGATIVE,
        ASSUMPTION_71_INCONCLUSIVE,
    }
)

DEFERRED_TO_M2 = "deferred_to_m2"
DEFERRED_TO_M3 = "deferred_to_m3"
DEFERRED_TO_M4 = "deferred_to_m4"

TARGET_TABLE_COLUMNS = (
    "type",
    "mode",
    "fid",
    "universe",
    "address",
    "footprint",
    "address_basis",
)
UNRESOLVED_TARGET_FIELDS = MappingProxyType(
    {
        "mode": DEFERRED_TO_M3,
        "fid": DEFERRED_TO_M2,
        "footprint": DEFERRED_TO_M3,
    }
)


class FidPropertyPort(Protocol):
    def query_state(self, path: str) -> Mapping[str, object]: ...

    def query_property(self, path: str, property_name: str) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class FIDRange:
    start: int
    end: int


@dataclass(frozen=True)
class PatchCandidate:
    id: str
    unit_number: str | None
    instrument_type: str
    universe: int
    address: int
    detail: str
    address_basis: str | None
    source_index: int
    assigned_fid: int | None = None
    fid_range_visually_confirmed_empty: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "unit_number": self.unit_number,
            "type": self.instrument_type,
            "universe": self.universe,
            "address": self.address,
            "detail": self.detail,
            "address_basis": self.address_basis,
            "source_path": SOURCE_PATH_MISSING_IN_CONSOLE,
            "source_index": self.source_index,
        }

    def with_fid(
        self, fid: int, *, fid_range_visually_confirmed_empty: bool | None = None
    ) -> PatchCandidate:
        return replace(
            self,
            assigned_fid=fid,
            fid_range_visually_confirmed_empty=fid_range_visually_confirmed_empty,
        )

    def target_row(self) -> dict[str, object]:
        unresolved_reason = dict(UNRESOLVED_TARGET_FIELDS)
        if self.assigned_fid is not None:
            unresolved_reason.pop("fid")
        row: dict[str, object] = {
            "id": self.id,
            "type": self.instrument_type,
            "mode": None,
            "fid": self.assigned_fid,
            "universe": self.universe,
            "address": self.address,
            "footprint": None,
            "address_basis": self.address_basis,
            "unresolved_reason": unresolved_reason,
        }
        if self.fid_range_visually_confirmed_empty is not None:
            row["fid_range_visually_confirmed_empty"] = self.fid_range_visually_confirmed_empty
        return row


@dataclass(frozen=True)
class PatchTargetExclusion:
    candidate_id: str
    code: str
    reason: str
    proposed_fid: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "code": validate_autopatch("target_exclusion_reason", self.code),
            "label": target_exclusion_label(self.code),
            "reason": self.reason,
            "proposed_fid": self.proposed_fid,
        }


@dataclass(frozen=True)
class AddressPlanEntry:
    """계획된 한 항목의 점유 구간. `address`는 **언제나 도면 주소 그대로**다."""

    candidate_id: str
    universe: int
    address: int
    footprint: int
    end_address: int

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "universe": self.universe,
            "address": self.address,
            "footprint": self.footprint,
            "end_address": self.end_address,
        }


@dataclass(frozen=True)
class AddressPlan:
    entries: tuple[AddressPlanEntry, ...] = ()
    exclusions: tuple[PatchTargetExclusion, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "exclusions": [exclusion.to_dict() for exclusion in self.exclusions],
        }


def plan_addresses(
    targets: Sequence[PatchCandidate],
    *,
    footprints: Mapping[str, int | None],
    occupied: Mapping[int, Sequence[tuple[int, int]]],
) -> AddressPlan:
    """도면 주소를 그대로 쓰면서 겹치는 항목을 **제외**한다 (REQ-AUTOPATCH-019).

    `footprints`는 **1단계 도면이 준 점유폭**이다 — 콘솔에서 읽은 `DMXChannels` 개수를
    넣으면 안 된다(M0 함정 7: 그것은 점유폭이 아니다). 폭을 모르는 항목은 추측하지 않고
    `footprint_unknown`으로 제외한다.

    `occupied`는 유니버스별 기존 점유 구간 `(시작, 끝)` 목록이다.

    **재배치는 하지 않는다** — 빈 주소를 찾아 옮겨 붙이는 경로가 이 함수에 없다.
    그것은 사람이 결정할 일이다(design.md §7 안티패턴 7).
    """
    entries: list[AddressPlanEntry] = []
    exclusions: list[PatchTargetExclusion] = []
    planned_spans: dict[int, list[tuple[int, int]]] = {}

    for target in targets:
        footprint = footprints.get(target.id)
        if not isinstance(footprint, int) or isinstance(footprint, bool) or footprint <= 0:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FOOTPRINT_UNKNOWN,
                    reason=(
                        "점유폭이 확정되지 않아 간격을 계산할 수 없다 — "
                        "콘솔의 DMXChannels 개수는 점유폭이 아니므로 대체하지 않는다."
                    ),
                )
            )
            continue

        span = (target.address, target.address + footprint - 1)

        console_spans = tuple(occupied.get(target.universe, ()))
        if any(_spans_overlap(span, existing) for existing in console_spans):
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=ADDRESS_ALREADY_OCCUPIED,
                    reason=(
                        f"유니버스 {target.universe} 주소 {span[0]}~{span[1]} 구간이 "
                        "콘솔에서 이미 점유되어 있다 — 빈 주소로 옮겨 붙이지 않고 제외한다."
                    ),
                )
            )
            continue

        same_universe = planned_spans.setdefault(target.universe, [])
        if any(_spans_overlap(span, existing) for existing in same_universe):
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=ADDRESS_OVERLAP_IN_PLAN,
                    reason=(
                        f"유니버스 {target.universe} 주소 {span[0]}~{span[1]} 구간이 "
                        "같은 계획의 다른 항목과 겹친다 — 도면 주소를 바꾸지 않고 제외한다."
                    ),
                )
            )
            continue

        same_universe.append(span)
        entries.append(
            AddressPlanEntry(
                candidate_id=target.id,
                universe=target.universe,
                address=target.address,
                footprint=footprint,
                end_address=span[1],
            )
        )

    return AddressPlan(entries=tuple(entries), exclusions=tuple(exclusions))


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


@dataclass(frozen=True)
class PatchPlanRejection:
    code: str
    reason: str
    quoted_report_reason: str | None = None
    vocabulary: str = "candidate_rejection_reason"

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": validate_autopatch(self.vocabulary, self.code),
            "label": autopatch_label(self.vocabulary, self.code),
            "reason": self.reason,
        }
        if self.quoted_report_reason is not None:
            payload["quoted_report_reason"] = self.quoted_report_reason
        return payload


@dataclass(frozen=True)
class PatchPlan:
    ok: bool
    status: str
    dry_run: bool
    candidates: tuple[PatchCandidate, ...]
    selected: tuple[str, ...] = ()
    targets: tuple[PatchCandidate, ...] = ()
    rejection: PatchPlanRejection | None = None
    errors: tuple[dict[str, str], ...] = ()
    address_basis_notes: tuple[str, ...] = ()
    target_exclusions: tuple[PatchTargetExclusion, ...] = ()
    skipped_checks: tuple[Mapping[str, object], ...] = ()
    fid_safety: Mapping[str, object] | None = None
    fid_range_visually_confirmed_empty: bool | None = None

    @property
    def execution_requested(self) -> bool:
        return not self.dry_run

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ok": self.ok,
            "status": self.status,
            "dry_run": self.dry_run,
            "execution_requested": self.execution_requested,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected": list(self.selected),
            "targets": [target.target_row() for target in self.targets],
            "target_table": {
                "columns": list(TARGET_TABLE_COLUMNS),
                "rows": [target.target_row() for target in self.targets],
            },
            "warnings": [IRREVERSIBLE_WARNING],
            "address_basis_notes": list(self.address_basis_notes),
            "target_exclusions": [exclusion.to_dict() for exclusion in self.target_exclusions],
            "skipped_checks": [dict(check) for check in self.skipped_checks],
            "lua_source": None,
            "lua_source_unresolved_reason": DEFERRED_TO_M4,
        }
        if self.fid_safety is not None:
            payload["fid_safety"] = dict(self.fid_safety)
        if self.fid_range_visually_confirmed_empty is not None:
            payload["fid_range_visually_confirmed_empty"] = self.fid_range_visually_confirmed_empty
        if self.rejection is not None:
            payload["rejection"] = self.rejection.to_dict()
        if self.errors:
            payload["errors"] = [dict(error) for error in self.errors]
        return payload


def build_patch_plan(
    report: Mapping[str, object],
    *,
    selected: Sequence[str] | None = None,
    dry_run: bool = True,
    fid_range: Mapping[str, object] | None = None,
    assumption_71: str | None = None,
    fid_range_visually_confirmed_empty: bool | None = None,
    fid_property_port: FidPropertyPort | None = None,
) -> PatchPlan:
    rejection = _rejection_for_report(report)
    if rejection is not None:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=(),
            rejection=rejection,
        )

    candidates = _candidates_from_report(report)
    selected_ids = tuple(selected or ())
    candidates_by_id = {candidate.id: candidate for candidate in candidates}
    unknown = tuple(
        candidate_id for candidate_id in selected_ids if candidate_id not in candidates_by_id
    )
    if unknown:
        return PatchPlan(
            ok=False,
            status="selection_error",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            errors=tuple(
                {
                    "code": validate_autopatch("selection_error_reason", UNKNOWN_CANDIDATE_ID),
                    "candidate_id": candidate_id,
                }
                for candidate_id in unknown
            ),
        )

    target_ids = frozenset(selected_ids)
    targets = tuple(candidate for candidate in candidates if candidate.id in target_ids)
    if not _fid_assignment_requested(fid_range, assumption_71, fid_range_visually_confirmed_empty):
        return PatchPlan(
            ok=True,
            status="planned",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            address_basis_notes=_address_basis_notes(report, targets),
        )

    assumption_71_value = _assumption_71_or_default(assumption_71)
    parsed_fid_range = _parse_fid_range(fid_range)
    if fid_range is None:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=FID_RANGE_REQUIRED,
                reason=(
                    "패치할 빈 FID 범위를 fid_range {'start': int, 'end': int} 형식으로 "
                    "입력해야 한다."
                ),
                vocabulary="fid_assignment_rejection_reason",
            ),
        )
    if parsed_fid_range is None:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=INVALID_FID_RANGE,
                reason=(
                    "fid_range는 정수 start와 end를 포함해야 하며 end는 start보다 작을 수 없다."
                ),
                vocabulary="fid_assignment_rejection_reason",
            ),
        )

    confirmation_required = assumption_71_value != ASSUMPTION_71_GO
    confirmation_recorded = (
        bool(fid_range_visually_confirmed_empty) if confirmation_required else None
    )
    fid_safety = _fid_safety_payload(
        assumption_71_value,
        confirmation_required=confirmation_required,
        confirmation_recorded=confirmation_recorded,
        existing_fids=(),
        precheck_performed=assumption_71_value == ASSUMPTION_71_GO,
    )
    if confirmation_required and confirmation_recorded is not True:
        return PatchPlan(
            ok=False,
            status="rejected",
            dry_run=dry_run,
            candidates=candidates,
            selected=selected_ids,
            targets=targets,
            rejection=PatchPlanRejection(
                code=FID_RANGE_CONFIRMATION_REQUIRED,
                reason=(
                    "ASSUMPTION-71 부정 또는 INCONCLUSIVE 분기에서는 FID 범위를 콘솔에서 "
                    "눈으로 확인했다는 별도 확인(fid_range_visually_confirmed_empty=true)이 "
                    "필요하다."
                ),
                vocabulary="fid_assignment_rejection_reason",
            ),
            fid_safety=fid_safety,
            fid_range_visually_confirmed_empty=False,
        )

    existing_fids = (
        _existing_fids_from_console(fid_property_port)
        if assumption_71_value == ASSUMPTION_71_GO
        else ()
    )
    planned_targets, target_exclusions = _assign_fids(
        targets,
        parsed_fid_range,
        existing_fids=frozenset(existing_fids),
        fid_range_visually_confirmed_empty=confirmation_recorded,
    )
    skipped_checks = _fid_skipped_checks(assumption_71_value)
    return PatchPlan(
        ok=True,
        status="planned",
        dry_run=dry_run,
        candidates=candidates,
        selected=selected_ids,
        targets=planned_targets,
        address_basis_notes=_address_basis_notes(report, planned_targets),
        target_exclusions=target_exclusions,
        skipped_checks=skipped_checks,
        fid_safety=_fid_safety_payload(
            assumption_71_value,
            confirmation_required=confirmation_required,
            confirmation_recorded=confirmation_recorded,
            existing_fids=existing_fids,
            precheck_performed=assumption_71_value == ASSUMPTION_71_GO,
        ),
        fid_range_visually_confirmed_empty=confirmation_recorded,
    )


def _fid_assignment_requested(
    fid_range: Mapping[str, object] | None,
    assumption_71: str | None,
    fid_range_visually_confirmed_empty: bool | None,
) -> bool:
    return (
        fid_range is not None
        or assumption_71 is not None
        or fid_range_visually_confirmed_empty is not None
    )


def _assumption_71_or_default(value: str | None) -> str:
    if value is None:
        return ASSUMPTION_71_GO
    if value not in ASSUMPTION_71_VALUES:
        raise ValueError(
            f"assumption_71 must be one of {sorted(ASSUMPTION_71_VALUES)}, got {value!r}"
        )
    return value


def _parse_fid_range(value: Mapping[str, object] | None) -> FIDRange | None:
    if value is None:
        return None
    start = _optional_int(value.get("start"))
    end = _optional_int(value.get("end"))
    if start is None or end is None or end < start:
        return None
    return FIDRange(start=start, end=end)


def _assign_fids(
    targets: tuple[PatchCandidate, ...],
    fid_range: FIDRange,
    *,
    existing_fids: frozenset[int],
    fid_range_visually_confirmed_empty: bool | None,
) -> tuple[tuple[PatchCandidate, ...], tuple[PatchTargetExclusion, ...]]:
    planned: list[PatchCandidate] = []
    exclusions: list[PatchTargetExclusion] = []
    next_fid = fid_range.start
    for target in targets:
        if next_fid > fid_range.end:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FID_RANGE_EXHAUSTED,
                    reason=(
                        f"사용자가 입력한 FID 범위 {fid_range.start}-{fid_range.end}를 "
                        "초과해 이 장비에는 FID를 배정하지 않았다."
                    ),
                )
            )
            continue
        proposed_fid = next_fid
        next_fid += 1
        if proposed_fid in existing_fids:
            exclusions.append(
                PatchTargetExclusion(
                    candidate_id=target.id,
                    code=FID_ALREADY_IN_USE,
                    reason=f"FID {proposed_fid}는 콘솔 기존 픽스처가 이미 사용 중이다.",
                    proposed_fid=proposed_fid,
                )
            )
            continue
        planned.append(
            target.with_fid(
                proposed_fid,
                fid_range_visually_confirmed_empty=fid_range_visually_confirmed_empty,
            )
        )
    return tuple(planned), tuple(exclusions)


def _existing_fids_from_console(fid_property_port: FidPropertyPort | None) -> tuple[int, ...]:
    if fid_property_port is None:
        return ()
    state = fid_property_port.query_state(FID_FIXTURE_ROOT)
    existing_fids: list[int] = []
    for child in _mapping_rows(state.get("children")):
        child_index = _optional_int(child.get("i"))
        if child_index is None:
            continue
        response = fid_property_port.query_property(
            f"{FID_FIXTURE_ROOT}/{child_index}", FID_PROPERTY_NAME
        )
        if response.get("ok") is not True:
            continue
        fid = _fid_int(response.get("value"))
        if fid is not None:
            existing_fids.append(fid)
    return tuple(existing_fids)


def _fid_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _fid_skipped_checks(assumption_71: str) -> tuple[Mapping[str, object], ...]:
    if assumption_71 == ASSUMPTION_71_GO:
        return ()
    return (
        {
            "kind": validate_autopatch("skipped_check_kind", FID_CONFLICT_PRECHECK_DESCOPE),
            "label": skipped_check_label(FID_CONFLICT_PRECHECK_DESCOPE),
            "reason": (
                "ASSUMPTION-71이 부정 또는 INCONCLUSIVE라 기존 FID 충돌 사전검사를 수행하지 "
                "않고, 사용자가 입력한 FID 범위와 별도 육안 확인에 의존한다."
            ),
            "assumption_71": assumption_71,
        },
    )


def _fid_safety_payload(
    assumption_71: str,
    *,
    confirmation_required: bool,
    confirmation_recorded: bool | None,
    existing_fids: Sequence[int],
    precheck_performed: bool,
) -> Mapping[str, object]:
    return {
        "assumption_71": assumption_71,
        "active_safety": (
            "fid_conflict_precheck"
            if assumption_71 == ASSUMPTION_71_GO
            else "visual_empty_range_confirmation"
        ),
        "conflict_precheck": {
            "performed": precheck_performed,
            "property": FID_PROPERTY_NAME if precheck_performed else None,
            "source_path": FID_FIXTURE_ROOT if precheck_performed else None,
            "existing_fids": list(existing_fids),
        },
        "visual_confirmation": {
            "required": confirmation_required,
            "confirmed": confirmation_recorded,
            "field": "fid_range_visually_confirmed_empty",
        },
    }


def _rejection_for_report(report: Mapping[str, object]) -> PatchPlanRejection | None:
    for entry in _mapping_rows(report.get("skipped_checks")):
        if entry.get("kind") == MULTI_SYSTEM_MAPPING_ABSENT:
            reason = _string_or_default(
                entry.get("reason"), "System→콘솔 유니버스 매핑이 없어 콘솔 대조를 수행하지 않았다."
            )
            return PatchPlanRejection(code=MULTI_SYSTEM_MAPPING_ABSENT, reason=reason)

    diffs = report.get("diffs")
    if not isinstance(diffs, Mapping):
        return PatchPlanRejection(
            code=INVALID_REPORT_PAYLOAD,
            reason="리포트 payload에 diffs 객체가 없어 패치 후보를 만들 수 없다.",
        )
    if diffs.get("performed") is False:
        report_reason = _string_or_default(
            diffs.get("reason"), "1단계 리포트가 콘솔 대조 미수행 사유를 제공하지 않았다."
        )
        return PatchPlanRejection(
            code=COMPARISON_NOT_PERFORMED,
            reason=f"1단계 대조가 수행되지 않아 패치 후보를 만들 수 없다: {report_reason}",
            quoted_report_reason=report_reason,
        )
    return None


def _candidates_from_report(report: Mapping[str, object]) -> tuple[PatchCandidate, ...]:
    diffs = report.get("diffs")
    if not isinstance(diffs, Mapping):
        return ()
    fixture_basis = _address_basis_by_fixture(report)
    candidates: list[PatchCandidate] = []
    for index, row in enumerate(_mapping_rows(diffs.get("missing_in_console"))):
        unit_number = _optional_string(row.get("unit_number"))
        instrument_type = _required_string(row.get("instrument_type"))
        universe = _required_int(row.get("universe"))
        address = _required_int(row.get("address"))
        detail = _required_string(row.get("detail"))
        address_basis = fixture_basis.get((unit_number, instrument_type, universe, address))
        candidates.append(
            PatchCandidate(
                id=_candidate_id(index, unit_number, instrument_type, universe, address, detail),
                unit_number=unit_number,
                instrument_type=instrument_type,
                universe=universe,
                address=address,
                detail=detail,
                address_basis=address_basis,
                source_index=index,
            )
        )
    return tuple(candidates)


def _address_basis_by_fixture(
    report: Mapping[str, object],
) -> dict[tuple[str | None, str, int, int], str | None]:
    designed = report.get("designed_rig")
    if not isinstance(designed, Mapping):
        return {}
    indexed: dict[tuple[str | None, str, int, int], str | None] = {}
    for fixture in _mapping_rows(designed.get("fixtures")):
        unit_number = _optional_string(fixture.get("unit_number"))
        instrument_type = _optional_string(fixture.get("instrument_type"))
        universe = _optional_int(fixture.get("universe"))
        address = _optional_int(fixture.get("address"))
        if instrument_type is None or universe is None or address is None:
            continue
        indexed[(unit_number, instrument_type, universe, address)] = _optional_string(
            fixture.get("address_basis")
        )
    return indexed


def _address_basis_notes(
    report: Mapping[str, object], targets: tuple[PatchCandidate, ...]
) -> tuple[str, ...]:
    if not any(target.address_basis == ADDRESS_BASIS_ABS_BACK_CALCULATED for target in targets):
        return ()
    designed = report.get("designed_rig")
    if not isinstance(designed, Mapping):
        return ()
    note = _optional_string(designed.get("address_basis_note"))
    return (note,) if note else ()


def _candidate_id(
    index: int,
    unit_number: str | None,
    instrument_type: str,
    universe: int,
    address: int,
    detail: str,
) -> str:
    identity = {
        "address": address,
        "detail": detail,
        "instrument_type": instrument_type,
        "source_index": index,
        "unit_number": unit_number,
        "universe": universe,
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "vwx-missing-" + sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _mapping_rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _required_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _required_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _string_or_default(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default
