from __future__ import annotations

import ast
import re
from copy import deepcopy
from pathlib import Path

import pytest

from server.prechk.inventory import COMPLETE, FIXTURE_ROOT, FixtureRecord, Inventory
from server.vwx.address import ADDRESS_BASIS_DIRECT, PATCHED, ResolvedRecord
from server.vwx.diff import compare
from server.vwx.patchplan import (
    ASSUMPTION_71_GO,
    ASSUMPTION_71_INCONCLUSIVE,
    ASSUMPTION_71_NEGATIVE,
    build_patch_plan,
)
from server.vwx.report import build_vwx_report
from server.vwx.rig import build_designed_rig
from server.vwx.verdicts import (
    FID_ALREADY_IN_USE,
    FID_CONFLICT_PRECHECK_DESCOPE,
    FID_RANGE_CONFIRMATION_REQUIRED,
    FID_RANGE_EXHAUSTED,
    FID_RANGE_REQUIRED,
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


class FidRigPort:
    def __init__(self, existing_fids: tuple[int, ...] = ()):
        self.existing_fids = existing_fids
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path != FIXTURE_ROOT:
            raise RuntimeError(f"unexpected state path: {path}")
        children = [
            {"i": index, "name": f"Existing {fid}", "class": "Fixture"}
            for index, fid in enumerate(self.existing_fids, start=1)
        ]
        return {
            "ok": True,
            "path": path,
            "node": {"name": "Fixtures", "class": "Fixtures", "childCount": len(children)},
            "children": children,
            "truncated": False,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        if property_name != "FID":
            raise RuntimeError(f"unexpected property name: {property_name}")
        index = int(path.rsplit("/", 1)[1]) - 1
        return {
            "ok": True,
            "path": path,
            "property": property_name,
            "value": str(self.existing_fids[index]),
        }


class ExplodingFidRigPort:
    state_calls: list[str] = []
    property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        raise AssertionError(f"negative branch must not query state: {path}")

    def query_property(self, path: str, property_name: str) -> dict:
        raise AssertionError(f"negative branch must not query property: {path} {property_name}")


def assigned_rows(payload: dict) -> list[dict]:
    return payload["target_table"]["rows"]


def assigned_fids(payload: dict) -> list[int]:
    return [row["fid"] for row in assigned_rows(payload)]


def assert_no_fid_assignments(payload: dict) -> None:
    assert all(row.get("fid") is None for row in assigned_rows(payload))


def all_payload_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            strings.extend(all_payload_strings(key))
            strings.extend(all_payload_strings(item))
        return strings
    if isinstance(value, list | tuple):
        strings = []
        for item in value:
            strings.extend(all_payload_strings(item))
        return strings
    return []


def assert_no_fixture_selection_commands(payload: dict) -> None:
    offenders = [
        text for text in all_payload_strings(payload) if re.search(r"\bFixture \d+\b", text)
    ]
    assert offenders == []


def slot_reference_locations(source: str) -> list[tuple[int, int, str]]:
    locations: list[tuple[int, int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr == "slot":
            locations.append((node.lineno, node.col_offset, ".slot"))
        if isinstance(node, ast.Constant) and node.value == "slot":
            locations.append((node.lineno, node.col_offset, "'slot'"))
    return locations


class TestFidRangeAssignment:
    def test_fids_stay_inside_user_range_and_excess_targets_are_reported(self):
        payload = report_payload([rr(0), rr(1), rr(2)])
        ids = candidate_ids(payload)

        first = build_patch_plan(
            payload,
            selected=ids,
            fid_range={"start": 100, "end": 101},
            fid_property_port=FidRigPort(),
        ).to_dict()
        second = build_patch_plan(
            deepcopy(payload),
            selected=ids,
            fid_range={"start": 100, "end": 101},
            fid_property_port=FidRigPort(),
        ).to_dict()

        assert first["ok"] is True
        assert assigned_fids(first) == [100, 101]
        assert assigned_fids(second) == [100, 101]
        assert all(100 <= fid <= 101 for fid in assigned_fids(first))
        assert [
            {
                "candidate_id": row["candidate_id"],
                "code": row["code"],
                "proposed_fid": row["proposed_fid"],
            }
            for row in first["target_exclusions"]
        ] == [{"candidate_id": ids[2], "code": FID_RANGE_EXHAUSTED, "proposed_fid": None}]

    def test_missing_fid_range_rejects_m2_and_does_not_guess_from_slots(self):
        payload = report_payload([rr(0)])
        selected = candidate_ids(payload)

        result = build_patch_plan(
            payload,
            selected=selected,
            assumption_71=ASSUMPTION_71_GO,
        ).to_dict()

        assert result["ok"] is False
        assert result["status"] == "rejected"
        assert result["rejection"]["code"] == FID_RANGE_REQUIRED
        assert "fid_range" in result["rejection"]["reason"]
        assert "start" in result["rejection"]["reason"]
        assert "end" in result["rejection"]["reason"]
        assert_no_fid_assignments(result)

        record = FixtureRecord(
            slot=41,
            name="Control",
            patch_raw="1.001",
            fixture_type="Robe MegaPointe",
            mode="Mode 1",
        )
        guessed = deepcopy(result)
        guessed["target_table"]["rows"] = [{"id": selected[0], "fid": record.slot + 1}]
        with pytest.raises(AssertionError):
            assert_no_fid_assignments(guessed)


class TestSlotDerivedValuesAreExcluded:
    def test_fid_assignment_source_does_not_read_fixture_record_slot(self):
        source = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")

        assert slot_reference_locations(source) == []
        assert slot_reference_locations("def bad(record):\n    return record.slot\n")
        assert slot_reference_locations("def bad(row):\n    return row['slot']\n")

    def test_unresolved_fid_note_is_not_assignment_basis_and_no_fixture_selection_is_generated(
        self,
    ):
        payload = report_payload([rr(0)])
        payload["diffs"]["missing_in_console"][0]["fid_note"] = "999 (미확정)"
        payload["designed_rig"]["fixtures"][0]["fid_note"] = "999 (미확정)"
        selected = candidate_ids(payload)

        result = build_patch_plan(
            payload,
            selected=selected,
            fid_range={"start": 100, "end": 100},
            fid_property_port=FidRigPort(),
        ).to_dict()

        assert assigned_fids(result) == [100]
        assert 999 not in assigned_fids(result)
        assert_no_fixture_selection_commands(result)

        bad_payload = {**result, "lua_source": "Fixture 999 At 1.001"}
        with pytest.raises(AssertionError):
            assert_no_fixture_selection_commands(bad_payload)


class TestFidConflictPrecheckBranches:
    def test_go_branch_reads_fid_property_and_excludes_existing_fid_collisions(self):
        payload = report_payload([rr(0), rr(1)])
        ids = candidate_ids(payload)
        rig = FidRigPort(existing_fids=(100,))

        result = build_patch_plan(
            payload,
            selected=ids,
            fid_range={"start": 100, "end": 101},
            assumption_71=ASSUMPTION_71_GO,
            fid_property_port=rig,
        ).to_dict()

        assert result["ok"] is True
        assert rig.state_calls == [FIXTURE_ROOT]
        assert rig.property_calls == [(f"{FIXTURE_ROOT}/1", "FID")]
        assert assigned_fids(result) == [101]
        assert [
            {
                "candidate_id": row["candidate_id"],
                "code": row["code"],
                "proposed_fid": row["proposed_fid"],
            }
            for row in result["target_exclusions"]
        ] == [{"candidate_id": ids[0], "code": FID_ALREADY_IN_USE, "proposed_fid": 100}]
        assert result["fid_safety"]["assumption_71"] == ASSUMPTION_71_GO
        assert result["fid_safety"]["conflict_precheck"]["performed"] is True
        assert result["fid_safety"]["conflict_precheck"]["property"] == "FID"
        assert result["fid_safety"]["conflict_precheck"]["existing_fids"] == [100]

    def test_negative_branch_skips_precheck_structurally_and_lists_all_assignments(self):
        payload = report_payload([rr(0), rr(1)])
        ids = candidate_ids(payload)

        result = build_patch_plan(
            payload,
            selected=ids,
            fid_range={"start": 100, "end": 101},
            assumption_71=ASSUMPTION_71_NEGATIVE,
            fid_range_visually_confirmed_empty=True,
            fid_property_port=ExplodingFidRigPort(),
        ).to_dict()

        assert result["ok"] is True
        assert [{"id": row["id"], "fid": row["fid"]} for row in result["target_table"]["rows"]] == [
            {"id": ids[0], "fid": 100},
            {"id": ids[1], "fid": 101},
        ]
        assert len(result["skipped_checks"]) == 1
        skipped = result["skipped_checks"][0]
        assert skipped["kind"] == FID_CONFLICT_PRECHECK_DESCOPE
        assert skipped["assumption_71"] == ASSUMPTION_71_NEGATIVE
        assert "기존 FID 충돌 사전검사" in skipped["reason"]
        assert result["fid_safety"]["conflict_precheck"]["performed"] is False
        assert result["fid_safety"]["visual_confirmation"]["required"] is True
        assert result["fid_safety"]["visual_confirmation"]["confirmed"] is True


class TestVisualEmptyConfirmation:
    @pytest.mark.parametrize("assumption_71", [ASSUMPTION_71_NEGATIVE, ASSUMPTION_71_INCONCLUSIVE])
    def test_negative_or_inconclusive_execution_requires_separate_visual_empty_confirmation(
        self, assumption_71: str
    ):
        payload = report_payload([rr(0)])
        selected = candidate_ids(payload)

        missing = build_patch_plan(
            payload,
            selected=selected,
            fid_range={"start": 200, "end": 200},
            assumption_71=assumption_71,
            fid_property_port=ExplodingFidRigPort(),
        ).to_dict()
        false = build_patch_plan(
            payload,
            selected=selected,
            dry_run=False,
            fid_range={"start": 200, "end": 200},
            assumption_71=assumption_71,
            fid_range_visually_confirmed_empty=False,
            fid_property_port=ExplodingFidRigPort(),
        ).to_dict()

        for result in (missing, false):
            assert result["ok"] is False
            assert result["status"] == "rejected"
            assert result["rejection"]["code"] == FID_RANGE_CONFIRMATION_REQUIRED
            assert "FID 범위" in result["rejection"]["reason"]
            assert "눈으로 확인" in result["rejection"]["reason"]
            assert "별도 확인" in result["rejection"]["reason"]

    def test_visual_confirmation_is_independent_and_audited_when_present(self):
        payload = report_payload([rr(0)])
        selected = candidate_ids(payload)

        go = build_patch_plan(
            payload,
            selected=selected,
            dry_run=False,
            fid_range={"start": 200, "end": 200},
            assumption_71=ASSUMPTION_71_GO,
            fid_property_port=FidRigPort(),
        ).to_dict()
        negative_without_confirmation = build_patch_plan(
            payload,
            selected=selected,
            fid_range={"start": 200, "end": 200},
            assumption_71=ASSUMPTION_71_NEGATIVE,
            fid_property_port=ExplodingFidRigPort(),
        ).to_dict()
        negative_with_confirmation = build_patch_plan(
            payload,
            selected=selected,
            dry_run=False,
            fid_range={"start": 200, "end": 200},
            assumption_71=ASSUMPTION_71_NEGATIVE,
            fid_range_visually_confirmed_empty=True,
            fid_property_port=ExplodingFidRigPort(),
        ).to_dict()

        assert go["ok"] is True
        assert negative_without_confirmation["ok"] is False
        assert negative_with_confirmation["ok"] is True
        assert negative_with_confirmation["fid_range_visually_confirmed_empty"] is True
        assert assigned_rows(negative_with_confirmation) == [
            {
                **assigned_rows(negative_with_confirmation)[0],
                "fid_range_visually_confirmed_empty": True,
            }
        ]


# --------------------------------------------------------------------------
# round11 회귀 — 절단된 FID 열거를 완전한 것으로 취급하지 않는다
#
# 실물 콘솔은 이 루트(`Patch/Stages/1/Fixtures`)가 **19대에서 이미 절단**된다
# (`progress.md` §E.2 M0 1차). `server/prechk/inventory.py` 모듈 독스트링 1·2번이
# "절단은 기본 경로다 · childCount가 진짜 총계다 · len(children)를 총계로 읽은 조사가
# 이 저장소에서 실제로 틀렸다"를 명시하는데, 이전 판의 `_existing_fids_from_console`이
# 정확히 그 오류를 재현해 **이미 쓰이는 FID를 배정**했다(round11 N01).
# --------------------------------------------------------------------------


class _CountingFidPort:
    """콘솔에 FID 100·101이 있고, 열거는 원하는 만큼만 돌려준다."""

    def __init__(self, *, enumerated: int, child_count: int = 2, fid_readable: bool = True):
        self.enumerated = enumerated
        self.child_count = child_count
        self.fid_readable = fid_readable

    def query_state(self, path: str) -> dict:
        children = [{"i": i, "name": f"f{i}"} for i in range(1, self.enumerated + 1)]
        return {
            "ok": True,
            "path": path,
            "node": {"childCount": self.child_count},
            "children": children,
            "truncated": self.enumerated < self.child_count,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        if not self.fid_readable:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        slot = int(path.rsplit("/", 1)[1])
        return {"ok": True, "path": path, "property": property_name, "value": 99 + slot}


def _one_candidate_report() -> dict:
    fixture = {
        "unit_number": "1",
        "instrument_type": "Robin LEDBeam 350",
        "gdtf_fixture": None,
        "mode": "Mode 1",
        "footprint": 16,
        "system": None,
        "universe": 1,
        "address": 1,
        "classification": "patched",
        "address_basis": "universe_address_direct",
    }
    return {
        "designed_rig": {"fixture_count": 1, "fixtures": [fixture]},
        "diffs": {
            "performed": True,
            "missing_in_console": [
                {
                    "unit_number": "1",
                    "instrument_type": "Robin LEDBeam 350",
                    "universe": 1,
                    "address": 1,
                    "detail": "",
                }
            ],
            "address_collision": [],
            "quantity_mismatch": [],
        },
        "skipped_checks": [],
    }


def _plan_with(port):
    report = _one_candidate_report()
    candidate = build_patch_plan(report).candidates[0].id
    return build_patch_plan(
        report,
        selected=[candidate],
        fid_range={"start": 101, "end": 110},
        fid_property_port=port,
    )


def test_a_truncated_fid_enumeration_refuses_to_assign():
    """부분 관측으로 '빈 FID'를 단정하면 이미 쓰이는 번호를 배정하게 된다."""
    plan = _plan_with(_CountingFidPort(enumerated=1, child_count=2))
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]
    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read == {
        "child_count": 2,
        "enumerated_count": 1,
        "unread_count": 1,
        "complete": False,
    }


def test_the_truncation_control_a_complete_enumeration_still_assigns():
    """비공허성 — 같은 범위·같은 콘솔이라도 열거가 완전하면 배정이 진행된다."""
    plan = _plan_with(_CountingFidPort(enumerated=2, child_count=2))
    assert plan.ok is True
    assert plan.fid_safety["conflict_precheck"]["read"]["complete"] is True
    assert plan.fid_safety["conflict_precheck"]["existing_fids"] == [100, 101]


def test_an_unreadable_fid_property_also_blocks_assignment():
    """열거는 완전해도 FID 값을 못 읽으면 빈 FID를 단정할 수 없다."""
    plan = _plan_with(_CountingFidPort(enumerated=2, child_count=2, fid_readable=False))
    assert plan.ok is False
    assert plan.fid_safety["conflict_precheck"]["read"]["unread_count"] == 2


def test_an_unknown_child_count_is_treated_as_unread_rather_than_complete():
    """`childCount`를 못 읽으면 총계를 모르므로 완전하다고 말할 수 없다."""

    class _NoCount(_CountingFidPort):
        def query_state(self, path: str) -> dict:
            payload = super().query_state(path)
            payload["node"] = {}
            return payload

    plan = _plan_with(_NoCount(enumerated=2, child_count=2))
    assert plan.ok is False
    assert plan.fid_safety["conflict_precheck"]["read"]["child_count"] is None
