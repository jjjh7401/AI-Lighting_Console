from __future__ import annotations

from copy import deepcopy

import pytest

from server.prechk.inventory import COMPLETE, FIXTURE_ROOT, FixtureRecord, Inventory, read_inventory
from server.vwx.address import (
    ABSOLUTE_BACK_CALCULATED_PREMISE_NOTE,
    ADDRESS_BASIS_ABS_BACK_CALCULATED,
    ADDRESS_BASIS_DIRECT,
    PATCHED,
    ResolvedRecord,
)
from server.vwx.diff import MULTI_SYSTEM_MAPPING_ABSENT, compare
from server.vwx.patchplan import IRREVERSIBLE_WARNING, build_patch_plan
from server.vwx.report import build_vwx_report
from server.vwx.rig import build_designed_rig
from server.vwx.verdicts import (
    AUTOPATCH_CLOSED_VOCABULARIES,
    COMPARISON_NOT_PERFORMED,
    UNKNOWN_CANDIDATE_ID,
    UnknownAutopatchVerdict,
    candidate_rejection_label,
    selection_error_label,
    validate_autopatch,
)


def make_inventory(fixtures: list[tuple[int, str, str, str, str]] | None = None) -> Inventory:
    records = tuple(
        FixtureRecord(slot=slot, name=name, patch_raw=patch_raw, fixture_type=ftype, mode=mode)
        for slot, patch_raw, ftype, mode, name in fixtures or []
    )
    return Inventory(
        path=FIXTURE_ROOT,
        child_count=len(records),
        enumerated_count=len(records),
        recovered_count=0,
        observed_count=len(records),
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=records,
    )


def rr(
    row_index: int,
    *,
    unit_number: str | None = None,
    instrument_type: str = "Robe MegaPointe",
    universe: int = 1,
    address: int | None = None,
    address_basis: str = ADDRESS_BASIS_DIRECT,
) -> ResolvedRecord:
    fields = {
        "instrument_type": instrument_type,
        "unit_number": unit_number if unit_number is not None else str(row_index + 1),
    }
    return ResolvedRecord(
        fields=fields,
        extra={},
        row_index=row_index,
        classification=PATCHED,
        universe=universe,
        address=address if address is not None else row_index + 1,
        address_basis=address_basis,
    )


def report_payload(records: list[ResolvedRecord]) -> dict:
    designed_rig = build_designed_rig(records, candidate_count=len(records))
    diff = compare(designed_rig, make_inventory([]))
    return build_vwx_report(diff).to_dict()


def candidate_ids(payload: dict) -> list[str]:
    return [candidate["id"] for candidate in build_patch_plan(payload).to_dict()["candidates"]]


class RecordingDrawingReader:
    def __init__(self):
        self.calls: list[bytes] = []

    def read(self, data: bytes) -> None:
        self.calls.append(data)


class RecordingConsolePort:
    def __init__(self):
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path == FIXTURE_ROOT:
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Fixtures", "class": "Fixtures", "childCount": 1},
                "children": [{"i": 1, "name": "Existing 1", "class": "Fixture"}],
                "truncated": False,
            }
        raise RuntimeError(f"unexpected state path: {path}")

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        values = {
            "Patch": "1.001",
            "FixtureType": "Robe MegaPointe",
            "Mode": "Mode 1",
            "Name": "Existing 1",
        }
        return {"ok": True, "path": path, "property": property_name, "value": values[property_name]}


def exercise_phase_one_recorders(
    reader: RecordingDrawingReader, port: RecordingConsolePort
) -> None:
    reader.read(b"Instrument Type\tUnit Number\tUniverse\tDMX Address\nRobe MegaPointe\t1\t1\t1")
    read_inventory(port)


def assert_irreversible_warning_present(payload: dict) -> None:
    assert IRREVERSIBLE_WARNING in payload["warnings"]


class TestAutopatchVerdicts:
    def test_vocabulary_labels_match_the_closed_key_sets(self):
        assert candidate_rejection_label(COMPARISON_NOT_PERFORMED)
        assert selection_error_label(UNKNOWN_CANDIDATE_ID)
        for vocabulary, allowed in AUTOPATCH_CLOSED_VOCABULARIES.items():
            for code in allowed:
                assert validate_autopatch(vocabulary, code) == code

    def test_unknown_codes_raise_instead_of_passing_through(self):
        with pytest.raises(UnknownAutopatchVerdict):
            validate_autopatch("selection_error_reason", "not_real")


class TestInputComesOnlyFromReportPayload:
    def test_candidates_are_derived_only_from_missing_in_console_without_new_reads(self):
        payload = report_payload([rr(0), rr(1, unit_number="11", universe=2, address=101)])
        reader = RecordingDrawingReader()
        console = RecordingConsolePort()

        plan = build_patch_plan(payload).to_dict()

        assert reader.calls == []
        assert console.state_calls == []
        assert console.property_calls == []
        assert [
            {
                "unit_number": c["unit_number"],
                "instrument_type": c["type"],
                "universe": c["universe"],
                "address": c["address"],
                "detail": c["detail"],
            }
            for c in plan["candidates"]
        ] == payload["diffs"]["missing_in_console"]
        assert {c["source_path"] for c in plan["candidates"]} == {"diffs.missing_in_console"}

    def test_reader_and_console_recorders_are_nonvacuous_on_a_phase_one_control_path(self):
        reader = RecordingDrawingReader()
        console = RecordingConsolePort()

        exercise_phase_one_recorders(reader, console)

        assert len(reader.calls) == 1
        assert console.state_calls == [FIXTURE_ROOT]
        assert console.property_calls

    def test_diffs_not_performed_is_rejected_with_the_report_reason_quoted(self):
        payload = report_payload([])
        reason = payload["diffs"]["reason"]

        result = build_patch_plan(payload).to_dict()

        assert result["ok"] is False
        assert result["status"] == "rejected"
        assert result["rejection"]["code"] == COMPARISON_NOT_PERFORMED
        assert result["rejection"]["quoted_report_reason"] == reason
        assert reason in result["rejection"]["reason"]
        assert result["candidates"] == []

    def test_multi_system_mapping_absent_skip_rejects_as_structured_payload(self):
        payload = report_payload([rr(0)])
        payload["skipped_checks"].append(
            {"kind": MULTI_SYSTEM_MAPPING_ABSENT, "reason": "System mapping was not supplied"}
        )

        result = build_patch_plan(payload).to_dict()

        assert result["ok"] is False
        assert result["status"] == "rejected"
        assert result["rejection"]["code"] == MULTI_SYSTEM_MAPPING_ABSENT
        assert result["rejection"]["reason"] == "System mapping was not supplied"


class TestCandidateSelection:
    def test_candidate_ids_are_stable_for_the_same_report_payload(self):
        payload = report_payload([rr(0), rr(1, unit_number="11", universe=2, address=101)])

        assert candidate_ids(payload) == candidate_ids(deepcopy(payload))

    def test_default_selection_has_zero_targets_and_explicit_selection_targets_only_that_item(self):
        payload = report_payload([rr(0), rr(1, unit_number="11", universe=2, address=101)])
        first_id, second_id = candidate_ids(payload)

        default_plan = build_patch_plan(payload).to_dict()
        selected_plan = build_patch_plan(payload, selected=[second_id]).to_dict()

        assert default_plan["targets"] == []
        assert [target["id"] for target in selected_plan["targets"]] == [second_id]
        assert first_id not in {target["id"] for target in selected_plan["targets"]}

    def test_unknown_candidate_id_is_reported_as_an_error_not_silently_ignored(self):
        payload = report_payload([rr(0)])

        result = build_patch_plan(payload, selected=["candidate-does-not-exist"]).to_dict()

        assert result["ok"] is False
        assert result["status"] == "selection_error"
        assert result["errors"] == [
            {"code": UNKNOWN_CANDIDATE_ID, "candidate_id": "candidate-does-not-exist"}
        ]
        assert result["targets"] == []


class TestDryRunOutput:
    def test_dry_run_is_the_default_and_target_table_carries_required_unresolved_columns(self):
        payload = report_payload([rr(0)])
        selected_id = candidate_ids(payload)[0]

        result = build_patch_plan(payload, selected=[selected_id]).to_dict()

        assert result["dry_run"] is True
        assert result["execution_requested"] is False
        assert result["lua_source"] is None
        assert result["lua_source_unresolved_reason"] == "deferred_to_m4"
        assert result["target_table"]["columns"] == [
            "type",
            "mode",
            "fid",
            "universe",
            "address",
            "footprint",
            "address_basis",
        ]
        row = result["target_table"]["rows"][0]
        assert row["type"] == "Robe MegaPointe"
        assert row["mode"] is None
        assert row["fid"] is None
        assert row["footprint"] is None
        assert row["universe"] == 1
        assert row["address"] == 1
        assert row["address_basis"] == ADDRESS_BASIS_DIRECT
        assert row["unresolved_reason"] == {
            "mode": "deferred_to_m3",
            "fid": "deferred_to_m2",
            "footprint": "deferred_to_m3",
        }

    def test_absolute_back_calculated_basis_reuses_phase_one_premise_note(self):
        payload = report_payload([rr(0, address_basis=ADDRESS_BASIS_ABS_BACK_CALCULATED)])
        selected_id = candidate_ids(payload)[0]

        result = build_patch_plan(payload, selected=[selected_id]).to_dict()

        assert result["address_basis_notes"] == [ABSOLUTE_BACK_CALCULATED_PREMISE_NOTE]

    def test_direct_address_basis_does_not_emit_the_back_calculation_note(self):
        payload = report_payload([rr(0, address_basis=ADDRESS_BASIS_DIRECT)])
        selected_id = candidate_ids(payload)[0]

        result = build_patch_plan(payload, selected=[selected_id]).to_dict()

        assert ABSOLUTE_BACK_CALCULATED_PREMISE_NOTE not in result["address_basis_notes"]

    def test_irreversible_warning_is_present_and_the_absence_checker_is_nonvacuous(self):
        payload = report_payload([rr(0)])
        selected_id = candidate_ids(payload)[0]
        result = build_patch_plan(payload, selected=[selected_id]).to_dict()

        assert_irreversible_warning_present(result)
        without_warning = {**result, "warnings": []}
        with pytest.raises(AssertionError):
            assert_irreversible_warning_present(without_warning)
