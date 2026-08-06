from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from server.vwx.address import ADDRESS_BASIS_ABS_BACK_CALCULATED
from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT
from server.vwx.verdicts import (
    COMPARISON_NOT_PERFORMED,
    INVALID_REPORT_PAYLOAD,
    UNKNOWN_CANDIDATE_ID,
    candidate_rejection_label,
    validate_autopatch,
)

IRREVERSIBLE_WARNING = (
    "이 앱에는 실행 취소·백업 복원 경로가 없고, 잘못 생성된 픽스처는 콘솔에서 "
    "사람이 지워야 한다."
)
SOURCE_PATH_MISSING_IN_CONSOLE = "diffs.missing_in_console"

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

    def target_row(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.instrument_type,
            "mode": None,
            "fid": None,
            "universe": self.universe,
            "address": self.address,
            "footprint": None,
            "address_basis": self.address_basis,
            "unresolved_reason": dict(UNRESOLVED_TARGET_FIELDS),
        }


@dataclass(frozen=True)
class PatchPlanRejection:
    code: str
    reason: str
    quoted_report_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": validate_autopatch("candidate_rejection_reason", self.code),
            "label": candidate_rejection_label(self.code),
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
            "lua_source": None,
            "lua_source_unresolved_reason": DEFERRED_TO_M4,
        }
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
    return PatchPlan(
        ok=True,
        status="planned",
        dry_run=dry_run,
        candidates=candidates,
        selected=selected_ids,
        targets=targets,
        address_basis_notes=_address_basis_notes(report, targets),
    )


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
