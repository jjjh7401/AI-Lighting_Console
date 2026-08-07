from __future__ import annotations

import ast
import re
from copy import deepcopy
from pathlib import Path

import pytest

from server.prechk.inventory import COMPLETE, FIXTURE_ROOT, FixtureRecord, Inventory
from server.vwx.address import ADDRESS_BASIS_DIRECT, PATCHED, ResolvedRecord
from server.vwx.diff import compare
from server.vwx.patchplan import (  # noqa: I001
    ASSUMPTION_71_GO,
    ASSUMPTION_71_INCONCLUSIVE,
    ASSUMPTION_71_NEGATIVE,
    _existing_fids_from_console,
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
        "attempted": True,
        "child_count": 2,
        "enumerated_count": 1,
        "unseen_count": 1,
        "unreadable_fid_count": 0,
        "unusable_row_count": 0,
        "unparsable_row_count": 0,
        "over_enumerated": False,
        "root_unreadable": False,
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
    read = plan.fid_safety["conflict_precheck"]["read"]
    # 슬롯 2개는 **봤고**(enumerated 2), 그중 2개의 FID 값을 못 얻었다. 못 본 슬롯은 0이다 —
    # [round13 S05 · round14 T01] 같은 슬롯을 두 축으로 세면 "선언 2대 중 4대" 가 나온다.
    assert read["enumerated_count"] == 2
    assert read["unseen_count"] == 0
    assert read["unreadable_fid_count"] == 2
    assert read["complete"] is False


def test_a_duplicate_slot_index_is_not_counted_as_a_read_slot():
    """[round12 R01] 중복 `i`가 섞이면 행 수는 총계와 맞아도 못 읽은 슬롯이 남는다."""

    class _Duplicated(_CountingFidPort):
        def query_state(self, path: str) -> dict:
            payload = super().query_state(path)
            payload["children"] = [{"i": 1, "name": "a"}, {"i": 1, "name": "a-again"}]
            return payload

    plan = _plan_with(_Duplicated(enumerated=2, child_count=2))
    assert plan.ok is False
    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read["enumerated_count"] == 1  # 행은 2개지만 **서로 다른 슬롯은 1개**
    assert read["complete"] is False


def test_more_rows_than_the_declared_total_is_also_unread():
    """`childCount`보다 행이 **많아도** 총계와 어긋난 것이므로 완전하다고 말할 수 없다."""

    class _Overflowing(_CountingFidPort):
        def query_state(self, path: str) -> dict:
            payload = super().query_state(path)
            payload["node"] = {"childCount": 1}
            payload["children"] = [{"i": 1}, {"i": 2}, {"i": 3}]
            return payload

    plan = _plan_with(_Overflowing(enumerated=3, child_count=1))
    assert plan.ok is False
    assert plan.fid_safety["conflict_precheck"]["read"]["complete"] is False


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


# --------------------------------------------------------------------------
# round14 회귀 — 차단 사유 **문구**에 대조군을 붙인다
#
# round13 S05는 계수 축을 분리했으나 **그 숫자를 소비하는 문장**은 검증하지 않았다.
# 그래서 "선언 2대 중 4대를 읽지 못했다"(산술 불가)와 "선언 None대 중 0대만 열거했고
# 0대는 FID 값을 얻지 못했다"(전부 0 = 아무 문제 없음으로 읽힌다)가 통과했다.
# 이 문장은 **되돌릴 수 없는 FID 배정을 막는 화면**에 나간다 — 조작자가 그것을 무해하다고
# 읽으면 사전검사를 무시하고 이미 쓰이는 FID를 덮는다.
# --------------------------------------------------------------------------


class _ShapedFidPort:
    """루트 스냅샷 형태를 자유롭게 만드는 포트."""

    def __init__(self, *, child_count, rows, fids=None, root_ok=True):
        self.child_count = child_count
        self.rows = rows
        self.fids = fids or {}
        self.root_ok = root_ok

    def query_state(self, path: str) -> dict:
        if not self.root_ok:
            return {"ok": False, "path": path, "error": "unreadable"}
        node = {} if self.child_count is None else {"childCount": self.child_count}
        return {"ok": True, "path": path, "node": node, "children": [{"i": i} for i in self.rows]}

    def query_property(self, path: str, property_name: str) -> dict:
        value = self.fids.get(int(path.rsplit("/", 1)[1]))
        if value is None:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        return {"ok": True, "path": path, "property": property_name, "value": value}


FID_READ_SHAPES = (
    ("절단", dict(child_count=2, rows=[1], fids={1: 100}), "열거하지 못했다"),
    ("중복 슬롯", dict(child_count=2, rows=[1, 1], fids={1: 100}), "중복인 행"),
    ("초과 열거", dict(child_count=2, rows=[1, 2, 3], fids={}), "자기모순"),
    ("총계 부재", dict(child_count=None, rows=[1], fids={1: 100}), "총계(childCount)를 읽지 못해"),
    ("루트 실패", dict(child_count=2, rows=[], root_ok=False), "루트 상태를 읽지 못했다"),
    ("FID 미판독", dict(child_count=2, rows=[1, 2], fids={}), "FID 값을 얻지 못했다"),
)


@pytest.mark.parametrize(
    "label,kwargs,expected_phrase", FID_READ_SHAPES, ids=[row[0] for row in FID_READ_SHAPES]
)
def test_every_incomplete_shape_reports_an_observed_fact(label, kwargs, expected_phrase):
    """어떤 불완전 형태든 **관측된 사실**을 말한다 — 전부 0인 문장을 내지 않는다."""
    read = _existing_fids_from_console(_ShapedFidPort(**kwargs))
    assert read.complete is False
    reason = read.reason()
    assert expected_phrase in reason, reason
    assert reason != "부분 관측이다"


@pytest.mark.parametrize(
    "label,kwargs,_p", FID_READ_SHAPES, ids=[row[0] for row in FID_READ_SHAPES]
)
def test_no_shape_reports_more_unseen_than_declared(label, kwargs, _p):
    """`unseen <= child_count`가 **모든 형태에서** 성립한다 — 한 형태만 고정하지 않는다."""
    read = _existing_fids_from_console(_ShapedFidPort(**kwargs))
    if read.child_count is not None and read.unseen is not None:
        assert read.unseen <= read.child_count, read.to_dict()


def test_a_complete_read_says_so_and_the_reason_is_not_consulted():
    read = _existing_fids_from_console(
        _ShapedFidPort(child_count=2, rows=[1, 2], fids={1: 100, 2: 101})
    )
    assert read.complete is True
    assert read.fids == (100, 101)


def test_the_root_failure_message_carries_a_nonzero_signal():
    """[round14 T02] 전부 0인 문장은 조작자에게 '아무 문제 없음'으로 읽힌다."""
    read = _existing_fids_from_console(_ShapedFidPort(child_count=2, rows=[], root_ok=False))
    reason = read.reason()
    assert "0" not in reason
    assert "None" not in reason


def test_the_message_reaches_the_user_facing_rejection():
    """문구가 실제 거부 사유에 실린다 — 함수만 고쳐 놓고 쓰지 않으면 의미가 없다."""
    plan = _plan_with(_ShapedFidPort(child_count=2, rows=[], root_ok=False))
    assert plan.ok is False
    assert "루트 상태를 읽지 못했다" in plan.rejection.reason


# --------------------------------------------------------------------------
# --- round15 ExistingFidRead 축별 경계 게이트 ---
#
# `ExistingFidRead.complete`는 되돌릴 수 없는 FID 배정을 막는 **유일한 술어**다.
# 그 부정 조건은 여덟 축이지만, round15 적대 감사가 뮤테이션 48건을 돌린 결과
# **경계 1에 대조군이 있는 축은 `unseen > 0` 하나뿐**이었다:
#   · `unreadable_fids > 0` → `> 1` 이 5,234건 전부 통과 — 기존 테스트가 두 슬롯을
#     모두 실패시켜 `== 2`만 봤다. 실물 콘솔에서 가장 흔한 부분 실패는 **한 슬롯**이다.
#   · `unusable_rows > 0` → `> 1` 도 전부 통과 — 기존 중복 슬롯 테스트는 `unseen`도
#     동시에 1이 되어 **다른 축이 대신 막아준다**. 이 축 단독 검증은 한 번도 없었다.
#   · `to_dict()`의 `over_enumerated`·`root_unreadable`을 리터럴 `False`로 바꿔도 무검출.
#   · `max(child_count - len(read_slots), 0)`의 `max`를 제거해도 무검출(불변식이 단측).
#   · 포트 부재 분기에 `attempted=True`를 붙여도(= fail-open 복원) 무검출.
# 아래 표는 **여덟 축을 각각 단독으로 1** 발화시키고, 나머지 일곱 축이 전부 0임을
# 같은 단정에서 고정한다. "다른 축이 대신 막지 않는다"가 없으면 경계를 집지 못한다.
# --------------------------------------------------------------------------


class _R15RawPort:
    """루트 스냅샷의 `node`·`children`을 **가공 없이** 돌려주는 포트.

    `_ShapedFidPort`는 행을 항상 `{"i": …}` 매핑으로 만들어 `i` 결손 행과 비매핑 행을
    표현할 수 없다. `unusable_rows`·`unparsable_rows` 축을 **단독으로** 발화시키려면
    그 두 형태가 필요하다(중복 슬롯을 쓰면 `unseen`이 함께 오르므로 단독이 아니다).
    """

    def __init__(self, *, node, children, fids=None, root_ok=True):
        self.node = node
        self.children = children
        self.fids = fids or {}
        self.root_ok = root_ok

    def query_state(self, path: str) -> dict:
        if not self.root_ok:
            return {"ok": False, "path": path, "error": "unreadable"}
        return {"ok": True, "path": path, "node": self.node, "children": self.children}

    def query_property(self, path: str, property_name: str) -> dict:
        value = self.fids.get(int(path.rsplit("/", 1)[1]))
        if value is None:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        return {"ok": True, "path": path, "property": property_name, "value": value}


def _r15_axes(read) -> dict:
    """`complete`의 부정 조건이 읽는 **일곱 축 전부**를 한 사전으로 관측한다."""
    return {
        "attempted": read.attempted,
        "root_unreadable": read.root_unreadable,
        "over_enumerated": read.over_enumerated,
        "unseen": read.unseen,
        "unreadable_fids": read.unreadable_fids,
        "unusable_rows": read.unusable_rows,
        "unparsable_rows": read.unparsable_rows,
    }


def _r15_clean_axes(**overrides) -> dict:
    """ "아무 문제 없는 읽기"의 축 벡터에서 **한 축만** 바꾼다."""
    axes = {
        "attempted": True,
        "root_unreadable": False,
        "over_enumerated": False,
        "unseen": 0,
        "unreadable_fids": 0,
        "unusable_rows": 0,
        "unparsable_rows": 0,
    }
    axes.update(overrides)
    return axes


# (축 이름, 그 축만 발화시키는 포트 구성, 기대 축 벡터, reason() 문구 조각)
R15_SOLE_AXIS_ROWS = (
    (
        "attempted=False",
        None,
        # 포트가 없으면 조회 자체를 하지 않았다 — 다른 축은 전부 기본값 0이라
        # `attempted`가 유일한 차단 신호다.
        _r15_clean_axes(attempted=False),
        "콘솔 FID 조회를 수행하지 않았다",
    ),
    (
        "root_unreadable",
        dict(node={"childCount": 2}, children=[], root_ok=False),
        _r15_clean_axes(root_unreadable=True, unseen=0),
        "루트 상태를 읽지 못했다",
    ),
    (
        "over_enumerated",
        dict(node={"childCount": 1}, children=[{"i": 1}, {"i": 2}], fids={1: 100, 2: 101}),
        _r15_clean_axes(over_enumerated=True),
        "열거된 슬롯 2개가 선언 총계 1개보다 많다",
    ),
    (
        "unseen is None",
        dict(node={}, children=[{"i": 1}], fids={1: 100}),
        _r15_clean_axes(unseen=None),
        "총계(childCount)를 읽지 못해",
    ),
    (
        "unseen == 1",
        dict(node={"childCount": 2}, children=[{"i": 1}], fids={1: 100}),
        _r15_clean_axes(unseen=1),
        "선언 2개 중 1개를 열거하지 못했다",
    ),
    (
        "unreadable_fids == 1",
        dict(node={"childCount": 2}, children=[{"i": 1}, {"i": 2}], fids={1: 100}),
        _r15_clean_axes(unreadable_fids=1),
        "열거된 슬롯 1개의 FID 값을 얻지 못했다",
    ),
    (
        "unusable_rows == 1",
        dict(
            node={"childCount": 2},
            children=[{"i": 1}, {"i": 2}, {"name": "슬롯 번호 없음"}],
            fids={1: 100, 2: 101},
        ),
        _r15_clean_axes(unusable_rows=1),
        "슬롯 번호가 없거나 중복인 행 1개를 쓰지 못했다",
    ),
    (
        "unparsable_rows == 1",
        dict(node={"childCount": 2}, children=[{"i": 1}, {"i": 2}, None], fids={1: 100, 2: 101}),
        _r15_clean_axes(unparsable_rows=1),
        "슬롯으로 해석되지 않는 행 1개가 섞여 있다",
    ),
)


@pytest.mark.parametrize(
    "axis,port_kwargs,expected_axes,expected_phrase",
    R15_SOLE_AXIS_ROWS,
    ids=[row[0] for row in R15_SOLE_AXIS_ROWS],
)
def test_each_incomplete_axis_alone_blocks_the_fid_assignment(
    axis, port_kwargs, expected_axes, expected_phrase
):
    """여덟 축을 **각각 단독으로 1**만 발화시켜도 배정이 멈춘다.

    기대 축 벡터를 통째로 단정하므로 "다른 축이 대신 막아준 것"이 아님이 같은
    단정에서 고정된다 — 그 고정이 없으면 경계(`> 0` vs `> 1`)를 집지 못한다.

    [round15 N1] `patchplan.py` `complete`의 `self.unreadable_fids > 0`을 `> 1`로 바꾸면
      'unreadable_fids == 1' 행이 실패한다(기존 테스트는 두 슬롯 모두 실패시켜 `== 2`만 본다).
    [round15 N2] 같은 곳 `self.unusable_rows > 0` → `> 1` 이면 'unusable_rows == 1' 행이 실패한다
      (기존 중복 슬롯 테스트는 `unseen`도 1이 되어 다른 축이 대신 막아준다).
    [round15 N3] 같은 곳 `self.unparsable_rows > 0` → `> 1` 이면
      'unparsable_rows == 1' 행이 실패한다.
    [round15 N4] 같은 곳 `self.attempted and`를 지우면 'attempted=False' 행이 실패한다.
    [round15 N5] `max(child_count - len(read_slots), 0)`에서 `max`를 지우면
      'over_enumerated' 행의 `unseen`이 -1이 되어 축 벡터 단정이 실패한다.
    [round15 N6] `_existing_fids_from_console`의 포트 None 분기를
      `ExistingFidRead(attempted=True)`로 되돌리면 'attempted=False' 행이 실패한다.
    """
    port = None if port_kwargs is None else _R15RawPort(**port_kwargs)
    read = _existing_fids_from_console(port)

    assert _r15_axes(read) == expected_axes
    assert read.complete is False
    assert expected_phrase in read.reason(), read.reason()

    plan = _plan_with(port)
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]
    assert expected_phrase in plan.rejection.reason, plan.rejection.reason
    # [round15 N11] `reason()`의 끝 마침표를 되살리면 호출부의 `. `와 겹쳐 이중 마침표가 된다.
    assert ".." not in plan.rejection.reason

    payload_read = plan.fid_safety["conflict_precheck"]["read"]
    assert payload_read["complete"] is False
    # payload boolean 2축 — 이 두 필드는 `complete`와 **별도로** 조작자 화면에 나간다.
    assert payload_read["attempted"] is expected_axes["attempted"]
    assert payload_read["over_enumerated"] is expected_axes["over_enumerated"]
    assert payload_read["root_unreadable"] is expected_axes["root_unreadable"]
    assert payload_read["unreadable_fid_count"] == expected_axes["unreadable_fids"]
    assert payload_read["unusable_row_count"] == expected_axes["unusable_rows"]
    assert payload_read["unparsable_row_count"] == expected_axes["unparsable_rows"]


def test_the_sole_axis_table_control_a_clean_read_fires_no_axis_and_assigns():
    """비공허성 대조군 — 같은 포트 계열이라도 축이 하나도 발화하지 않으면 배정이 진행된다.

    이 대조군이 없으면 위 표는 "무엇을 해도 막는다"를 확인하는 공허한 테스트가 된다.
    """
    port = _R15RawPort(node={"childCount": 0}, children=[])
    read = _existing_fids_from_console(port)

    assert _r15_axes(read) == _r15_clean_axes()
    assert read.complete is True

    plan = _plan_with(port)
    assert plan.ok is True
    assert [target.assigned_fid for target in plan.targets] == [101]


def test_a_missing_fid_property_port_fails_closed_in_the_go_branch():
    """포트 부재 fail-open 회귀 — 조회하지 않았으면 배정하지 않는다.

    `fid_property_port`는 시그니처상 기본값이 `None`이다. 이전 판은 그 분기에서
    `complete=True`인 기본 인스턴스를 돌려줘 GO 분기 가드를 **통과**시켰고, 조회 없이
    FID를 배정했다. 이 앱에는 실행 취소가 없다.

    [round15 N6] `_existing_fids_from_console`의 포트 None 분기를
    `ExistingFidRead(attempted=True)`로 바꾸면 이 테스트가 실패한다.
    [round15 N4] `complete`에서 `self.attempted and`를 지우면 이 테스트가 실패한다.
    """
    report = _one_candidate_report()
    candidate = build_patch_plan(report).candidates[0].id
    plan = build_patch_plan(
        report,
        selected=[candidate],
        fid_range={"start": 101, "end": 110},
        assumption_71=ASSUMPTION_71_GO,
        fid_property_port=None,
    )

    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]
    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read["attempted"] is False
    assert read["complete"] is False
    assert plan.fid_safety["conflict_precheck"]["existing_fids"] == []

    # 비공허성 대조군 — **같은 호출에 유효한 포트만 주면** 배정이 진행된다.
    # 막힌 원인이 포트 부재였음을 이 한 쌍이 증명한다.
    with_port = build_patch_plan(
        _one_candidate_report(),
        selected=[candidate],
        fid_range={"start": 101, "end": 110},
        assumption_71=ASSUMPTION_71_GO,
        fid_property_port=_R15RawPort(node={"childCount": 0}, children=[]),
    )
    assert with_port.ok is True
    assert with_port.fid_safety["conflict_precheck"]["read"]["attempted"] is True
    assert [target.assigned_fid for target in with_port.targets] == [101]


def test_the_negative_branch_payload_never_claims_a_read_it_did_not_make():
    """비-GO 분기 payload 정직성 — 수행하지 않은 읽기를 '완전 · 기존 FID 0개'로 싣지 않는다.

    이전 판은 이 분기에서 기본 `ExistingFidRead()`를 payload에 실었고, 기본값이
    `complete=True`·`fids=()`였다. 그러면 조작자 화면에서 **'읽었고 깨끗했다'와
    구별되지 않는다**. 다만 이 분기에서 **배정 자체는 진행된다** — 사용자 육안 확인
    (`fid_range_visually_confirmed_empty`)이 대체 안전장치이기 때문이다. 그 사실도
    같은 테스트에서 고정해, payload 정직성을 고치다 배정을 막아버리는 회귀를 잡는다.

    [round15 N4] `complete`에서 `self.attempted and`를 지우면 `read["complete"]`가
    True가 되어 이 테스트가 실패한다.
    """
    report = _one_candidate_report()
    candidate = build_patch_plan(report).candidates[0].id
    plan = build_patch_plan(
        report,
        selected=[candidate],
        fid_range={"start": 101, "end": 110},
        assumption_71=ASSUMPTION_71_NEGATIVE,
        fid_range_visually_confirmed_empty=True,
        fid_property_port=ExplodingFidRigPort(),
    )

    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read["attempted"] is False
    assert read["complete"] is False
    assert plan.fid_safety["conflict_precheck"]["performed"] is False

    # …그러나 배정은 진행된다. 육안 확인이 이 분기의 활성 안전장치다.
    assert plan.ok is True
    assert plan.fid_safety["active_safety"] == "visual_empty_range_confirmation"
    assert plan.fid_safety["visual_confirmation"]["confirmed"] is True
    assert [target.assigned_fid for target in plan.targets] == [101]


def test_the_root_failure_payload_carries_its_boolean_as_the_only_signal():
    """루트 실패 payload에서 `root_unreadable`은 **무해 판독을 막는 유일한 필드**다.

    수치 축이 전부 0/None이라, 그 boolean 하나가 리터럴 `False`로 새어 나가면
    조작자는 같은 payload를 '아무 문제 없음'으로 읽는다.

    [round15 N7] `to_dict()`의 `"root_unreadable": self.root_unreadable`을 리터럴
    `False`로 바꾸면 이 테스트가 실패한다.
    """
    plan = _plan_with(_R15RawPort(node={"childCount": 2}, children=[], root_ok=False))
    read = plan.fid_safety["conflict_precheck"]["read"]

    assert read["root_unreadable"] is True
    # 다른 축은 전부 무해한 값이다 — 그래서 위 boolean이 유일한 신호다.
    assert read["child_count"] is None
    assert read["enumerated_count"] == 0
    assert read["unseen_count"] == 0
    assert read["unreadable_fid_count"] == 0
    assert read["unusable_row_count"] == 0
    assert read["unparsable_row_count"] == 0
    assert read["over_enumerated"] is False


def test_the_over_enumerated_payload_carries_its_boolean_as_the_only_signal():
    """초과 열거 payload에서 `over_enumerated`가 유일한 수치 외 신호다.

    `unseen`은 `max(…, 0)` 때문에 0이고 미판독·미해석 행도 0이라, 이 boolean이
    리터럴 `False`로 새면 자기모순 스냅샷이 무해하게 읽힌다.

    [round15 N8] `to_dict()`의 `"over_enumerated": self.over_enumerated`를 리터럴
    `False`로 바꾸면 이 테스트가 실패한다.
    """
    plan = _plan_with(
        _R15RawPort(node={"childCount": 1}, children=[{"i": 1}, {"i": 2}], fids={1: 100, 2: 101})
    )
    read = plan.fid_safety["conflict_precheck"]["read"]

    assert read["over_enumerated"] is True
    assert read["child_count"] == 1
    assert read["enumerated_count"] == 2
    assert read["unseen_count"] == 0
    assert read["unreadable_fid_count"] == 0
    assert read["unusable_row_count"] == 0
    assert read["unparsable_row_count"] == 0
    assert read["root_unreadable"] is False


@pytest.mark.parametrize(
    "label,kwargs,_p", FID_READ_SHAPES, ids=[row[0] for row in FID_READ_SHAPES]
)
def test_every_shape_reports_a_coherent_unseen_count(label, kwargs, _p):
    """`unseen` 불변식을 **양측으로**, 그리고 **모든 형태에 실질 단정으로** 건다.

    형제 테스트 `test_no_shape_reports_more_unseen_than_declared`는 `unseen <= child_count`
    만 보고(단측), 게다가 `if child_count is not None and unseen is not None:` 가드 때문에
    6형태 중 2형태('총계 부재'·'루트 실패')에서 **아무것도 단정하지 않는다**. 여기서는
    분기를 전부 소진해 어떤 형태도 무단정으로 빠져나가지 못하게 한다.

    [round15 N5] `_existing_fids_from_console`의 `max(child_count - len(read_slots), 0)`
    에서 `max`를 제거하면 '초과 열거' 형태의 `unseen`이 -1이 되어 이 테스트가 실패한다.
    """
    read = _existing_fids_from_console(_ShapedFidPort(**kwargs))

    if read.root_unreadable:
        # 루트 실패: 수치는 아무것도 모른다 — 전용 문장이 그 사실을 말해야 한다.
        assert read.child_count is None
        assert read.unseen == 0
        assert "루트 상태를 읽지 못했다" in read.reason()
        assert read.complete is False
        return
    if read.child_count is None:
        # 총계 부재: 무엇을 못 봤는지 셀 수 없다 — `unseen`은 0이 아니라 `None`이어야 한다.
        assert read.unseen is None
        assert "총계(childCount)를 읽지 못해" in read.reason()
        assert read.complete is False
        return
    assert read.unseen is not None
    assert 0 <= read.unseen <= read.child_count, read.to_dict()


def test_a_non_mapping_child_row_is_counted_rather_than_silently_dropped():
    """비매핑 행이 섞인 스냅샷을 프로덕션 경로가 **부분 관측으로 등급**한다.

    이전 판은 `_mapping_rows`가 그 행을 조용히 버려 다섯 축 어디에도 걸리지 않는
    여섯 번째 실패 형태를 만들었고 `complete=True`를 냈다 — 같은 스냅샷에서 형제 리더
    `server/prechk/inventory.py`의 `read_inventory`는 `AttributeError`로 죽는다.
    두 리더가 같은 스냅샷을 정반대로 등급하는 상태였다.

    [round15 N3] `complete`의 `self.unparsable_rows > 0`을 `> 1`로 바꾸면 이 테스트가 실패한다.
    """
    port = _R15RawPort(
        node={"childCount": 2}, children=[{"i": 1}, {"i": 2}, None], fids={1: 100, 2: 101}
    )
    read = _existing_fids_from_console(port)

    assert read.unparsable_rows == 1
    assert read.complete is False
    # 다른 축은 이 스냅샷을 막지 못한다 — `unparsable_rows`가 유일한 차단 신호다.
    assert read.unseen == 0
    assert read.unusable_rows == 0
    assert read.unreadable_fids == 0
    assert read.over_enumerated is False

    plan = _plan_with(port)
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]
    assert plan.fid_safety["conflict_precheck"]["read"]["unparsable_row_count"] == 1
    assert "슬롯으로 해석되지 않는 행 1개가 섞여 있다" in plan.rejection.reason


# --- round16 표 전단사·문장 전문 고정 (TableBijection) ---
#
# round16 A1: `R15_SOLE_AXIS_ROWS`에는 전단사 게이트가 **없었다**. 적대 감사 실측 —
# 표에서 행 하나(`unreadable_fids == 1`)를 지우면 전체 스위트가 실패 0으로 조용히
# 축소되고, 그 위에서 `complete`의 `self.unreadable_fids > 0`을 `> 1`로 되돌리면
# **부분 관측 위에 FID 101이 실제로 배정**된다(round15 치명 #1의 재개방). 같은 방식으로
# `unusable_rows` 행이 round15 치명 #2를 재개방한다.
#
# 그래서 표를 **프로덕션에서 파생한 집합과 전단사**로 묶는다. 기준 집합은 리터럴 목록이
# 아니라 `ExistingFidRead.complete`의 소스를 파싱해 얻은 **차단 조항 전부**다.
#   · 표에서 행을 빼면 → 어떤 조항도 그 행을 대신 발화시키지 못해 전사성이 깨진다.
#   · 프로덕션에 조항을 더하면 → 덮지 못한 조항이 생겨 전사성이 깨진다.
#   · 프로덕션에서 조항을 빼거나 경계를 옮기면(`> 0` → `> 1`) → 해당 행이 조항을
#     하나도 발화시키지 못해 단독성 단정이 깨진다.


def _round16_complete_clauses() -> tuple[tuple[str, bool], ...]:
    """`ExistingFidRead.complete`의 **차단 조항을 프로덕션 소스에서 파생**한다.

    각 원소는 `(조항 소스, 차단으로 세는 진리값)`이다. 선행 연언 `self.attempted`는
    **거짓일 때** 차단이고, `not (...)` 안의 선택지들은 **참일 때** 차단이다.
    리터럴 목록을 두지 않는 것이 요점 — 기준이 프로덕션과 함께 움직여야 한다.
    """
    import inspect
    import textwrap

    from server.vwx.patchplan import ExistingFidRead

    tree = ast.parse(textwrap.dedent(inspect.getsource(ExistingFidRead.complete.fget)))
    returns = [node for node in ast.walk(tree) if isinstance(node, ast.Return)]
    assert len(returns) == 1, ast.dump(tree)
    top = returns[0].value
    assert isinstance(top, ast.BoolOp) and isinstance(top.op, ast.And), ast.dump(top)
    assert len(top.values) == 2, ast.dump(top)
    head, tail = top.values
    assert isinstance(tail, ast.UnaryOp) and isinstance(tail.op, ast.Not), ast.dump(tail)
    inner = tail.operand
    assert isinstance(inner, ast.BoolOp) and isinstance(inner.op, ast.Or), ast.dump(inner)
    clauses = [(ast.unparse(head), False)]
    clauses.extend((ast.unparse(value), True) for value in inner.values)
    return tuple(clauses)


def _round16_blocking_clauses(axes: dict) -> frozenset[str]:
    """축 벡터 하나를 **프로덕션 조항에 그대로 먹여** 어느 조항이 차단하는지 본다."""
    from server.vwx.patchplan import ExistingFidRead

    read = ExistingFidRead(**axes)
    fired: set[str] = set()
    for source, blocking in _round16_complete_clauses():
        try:
            value = bool(eval(source, {"self": read}))  # noqa: S307
        except TypeError:
            # `self.unseen is None`이 먼저 참이면 프로덕션은 `self.unseen > 0`을
            # **평가하지 않는다**(or 단축 평가). 여기서도 발화하지 않은 것으로 센다.
            continue
        if value is blocking:
            fired.add(source)
    return frozenset(fired)


def test_the_r15_sole_axis_table_is_a_bijection_with_the_production_blocking_clauses():
    """`R15_SOLE_AXIS_ROWS` ↔ `ExistingFidRead.complete`의 차단 조항 **전단사**.

    [round16 P1/P2/P3] 표에서 `unparsable_rows == 1` · `unreadable_fids == 1` ·
      `unusable_rows == 1` 중 어느 행을 지워도 전사성 단정이 실패한다(이전에는 전체
      스위트가 실패 0으로 조용히 축소됐다).
    [round16 C1] 위 삭제에 더해 `patchplan.py` `complete`의 `self.unreadable_fids > 0`을
      `> 1`로 바꿔도 실패한다 — 조항 `self.unreadable_fids > 1`을 덮는 행이 없다.
    [round16 C2] `self.unusable_rows > 0` → `> 1`도 같은 이유로 실패한다.
    [round16] `complete`에 조항을 **추가**해도 실패한다 — 덮지 않은 조항이 남는다.
    """
    from dataclasses import fields

    from server.vwx.patchplan import ExistingFidRead

    clauses = _round16_complete_clauses()
    sources = {source for source, _ in clauses}
    assert len(sources) == len(clauses), clauses

    # 대조의 대조 — 깨끗한 축 벡터는 어느 조항도 발화시키지 않는다.
    assert _round16_blocking_clauses(_r15_clean_axes()) == frozenset()
    assert ExistingFidRead(**_r15_clean_axes()).complete is True

    field_names = {field.name for field in fields(ExistingFidRead)}
    fired_by_axis: dict[str, str] = {}
    for axis, _port_kwargs, expected_axes, _phrase in R15_SOLE_AXIS_ROWS:
        assert set(expected_axes) <= field_names, (axis, sorted(expected_axes))
        fired = _round16_blocking_clauses(expected_axes)
        # 단독성 — 그 행은 **정확히 한 조항**을 발화시킨다. 경계가 밀리면 0개가 된다.
        assert len(fired) == 1, (axis, sorted(fired))
        fired_by_axis[axis] = next(iter(fired))

    # 단사 — 두 행이 같은 조항을 겹쳐 덮지 않는다.
    assert len(set(fired_by_axis.values())) == len(fired_by_axis), fired_by_axis
    # 전사 — 프로덕션 조항이 하나도 남김없이 덮인다.
    assert set(fired_by_axis.values()) == sources, sorted(sources - set(fired_by_axis.values()))
    assert len(R15_SOLE_AXIS_ROWS) == len(sources)
    assert len({row[0] for row in R15_SOLE_AXIS_ROWS}) == len(R15_SOLE_AXIS_ROWS)


# --- round16 형제 필드·형제 사이트 (SiblingFields) ---
#
# 처방을 한 사이트에만 붙이고 형제 사이트는 두는 것이 여섯 라운드 연속 FAIL의 기제다.
# 이 절은 (a) `ExistingFidRead`가 payload로 나가는 **모든** 자리, (b) 부분 관측 고지의
# **여덟 축 전부**, (c) bool 가드를 가진 **모든** 정수 판독기를 프로덕션에서 파생해 고정한다.


def _r16_patchplan_source() -> str:
    return Path("server/vwx/patchplan.py").read_text(encoding="utf-8")


def _r16_in_source_order(nodes):
    return sorted(nodes, key=lambda node: (node.lineno, node.col_offset))


# ==========================================================================
# S16-02 — `attempted` 정직성은 payload **사이트 전부**의 규약이다
#
# round15 N01/N02는 `ExistingFidRead()` 기본값을 "미수행"으로 뒤집었지만, 그 정직성을
# 지키는 대조군은 비-GO **배정 진행** 사이트에만 붙었다. 형제 사이트 —
# `FID_RANGE_CONFIRMATION_REQUIRED` 거부 payload — 에는 아무 대조군이 없어서
# `ExistingFidRead()`를 `ExistingFidRead(attempted=True, child_count=0)`로 바꾸면
# 조작자 화면이 "콘솔을 읽었고 픽스처 0대이며 읽기는 완전했다"고 말하는데도 전부 통과했다.
# 포트는 만지면 터지는 대역인데도 그렇다 — round15가 닫은 fail-open과 같은 오류 양식이다.
# ==========================================================================

#: 손으로 쓴 사이트 표 — (사이트 이름, `existing_read=` 인자 원문). 소스 순서.
_R16_FID_SAFETY_SITES = (
    ("confirmation_required_rejection", "ExistingFidRead()"),
    ("precheck_incomplete_rejection", "existing_read"),
    ("planned", "existing_read"),
)


def _r16_production_fid_safety_sites():
    """`patchplan.py`의 `_fid_safety_payload(...)` 호출에서 `existing_read=` 인자를 전수."""
    import ast

    source = _r16_patchplan_source()
    tree = ast.parse(source)
    calls = _r16_in_source_order(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_fid_safety_payload"
    )
    return tuple(
        ast.get_source_segment(source, keyword.value)
        for call in calls
        for keyword in call.keywords
        if keyword.arg == "existing_read"
    )


def test_the_fid_safety_site_table_is_a_bijection_onto_production():
    """[round16 S16-02] payload 사이트 표가 프로덕션 호출과 1:1이다.

    사이트를 더하면 행 없이는 통과하지 못하고, 표에서 행을 지우면 실패한다.
    `existing_read=ExistingFidRead()`를 다른 식으로 바꿔도 실패한다.
    """
    assert tuple(expr for _, expr in _R16_FID_SAFETY_SITES) == (_r16_production_fid_safety_sites())


def test_the_default_existing_fid_read_means_not_attempted():
    """[round16 S16-02] 아래 정직성 표가 딛는 프로덕션 사실 — 기본 인스턴스는 **미수행**이다.

    [round15 N01] 기본값을 `attempted=True`로 되돌리면 이 단정이 먼저 실패한다.
    """
    from server.vwx.patchplan import ExistingFidRead

    default = ExistingFidRead()
    assert default.attempted is False
    assert default.complete is False
    assert default.fids == ()
    assert "수행하지 않았다" in default.reason()


def _r16_plan(*, assumption_71, confirmed, port):
    """`build_patch_plan`을 후보 1건으로 돌린다 — 포트·판정·육안확인만 바꾼다."""
    report = _one_candidate_report()
    candidate = build_patch_plan(report).candidates[0].id
    return build_patch_plan(
        report,
        selected=[candidate],
        fid_range={"start": 101, "end": 110},
        assumption_71=assumption_71,
        fid_range_visually_confirmed_empty=confirmed,
        fid_property_port=port,
    )


def _r16_clean_port():
    return _R15RawPort(node={"childCount": 0}, children=[])


def _r16_truncated_port():
    return _R15RawPort(node={"childCount": 2}, children=[{"i": 1}], fids={1: 100})


# (행 이름, 사이트, 판정, 육안확인, 포트 팩토리, 기대 attempted, 기대 complete,
#  기대 performed, plan.ok)
_R16_PAYLOAD_HONESTY_ROWS = (
    (
        "confirmation_required_rejection/negative_unconfirmed",
        "confirmation_required_rejection",
        ASSUMPTION_71_NEGATIVE,
        None,
        ExplodingFidRigPort,
        False,
        False,
        False,
        False,
    ),
    (
        "confirmation_required_rejection/inconclusive_unconfirmed",
        "confirmation_required_rejection",
        ASSUMPTION_71_INCONCLUSIVE,
        False,
        ExplodingFidRigPort,
        False,
        False,
        False,
        False,
    ),
    (
        "planned/negative_confirmed",
        "planned",
        ASSUMPTION_71_NEGATIVE,
        True,
        ExplodingFidRigPort,
        False,
        False,
        False,
        True,
    ),
    (
        "precheck_incomplete_rejection/no_port",
        "precheck_incomplete_rejection",
        ASSUMPTION_71_GO,
        None,
        lambda: None,
        False,
        False,
        False,
        False,
    ),
    (
        "precheck_incomplete_rejection/truncated_port",
        "precheck_incomplete_rejection",
        ASSUMPTION_71_GO,
        None,
        _r16_truncated_port,
        True,
        False,
        False,
        False,
    ),
    (
        "planned/clean_read",
        "planned",
        ASSUMPTION_71_GO,
        None,
        _r16_clean_port,
        True,
        True,
        True,
        True,
    ),
)


def test_the_payload_honesty_table_covers_every_site_and_both_attempted_values():
    """[round16 S16-02] 전수 게이트 — 사이트마다 도달 가능한 `attempted` 값이 전부 표에 있다.

    `ExistingFidRead()` **리터럴**을 싣는 사이트는 구조상 `attempted=False`만 낼 수 있고
    (`ExistingFidRead().attempted is False` — 위 테스트가 그 사실을 따로 고정한다),
    `existing_read` 변수를 싣는 사이트는 두 값 모두 낸다. 그래서 이 기대는 표가 아니라
    **프로덕션 인자 원문**에서 파생된다. 어느 행을 지워도 이 단정이 실패한다.
    """
    covered: dict[str, set] = {}
    for _, site, *_rest in _R16_PAYLOAD_HONESTY_ROWS:
        covered.setdefault(site, set())
    for row in _R16_PAYLOAD_HONESTY_ROWS:
        covered[row[1]].add(row[5])

    expected = {
        site: ({False} if expr == "ExistingFidRead()" else {False, True})
        for site, expr in _R16_FID_SAFETY_SITES
    }
    assert covered == expected


@pytest.mark.parametrize(
    "name,site,assumption_71,confirmed,port_factory,attempted,complete,performed,plan_ok",
    _R16_PAYLOAD_HONESTY_ROWS,
    ids=[row[0] for row in _R16_PAYLOAD_HONESTY_ROWS],
)
def test_every_fid_safety_payload_site_reports_the_read_it_actually_made(
    name, site, assumption_71, confirmed, port_factory, attempted, complete, performed, plan_ok
):
    """[round16 S16-02] 어느 사이트든 payload는 **실제로 한 읽기만** 주장한다.

    `attempted=False` 행은 포트로 `ExplodingFidRigPort`(만지면 `AssertionError`) 또는
    `None`을 쓴다 — "정말 안 읽었다"가 구조적으로 보장된다.

    [round16 S16-02] `patchplan.py`의 `existing_read=ExistingFidRead()`(확인요구 거부
    사이트)를 `ExistingFidRead(attempted=True, child_count=0)`로 바꾸면
    'confirmation_required_rejection/*' 두 행이 실패한다 — round15는 통과했다.
    [round15 N4] `complete`에서 `self.attempted and`를 지우면 세 행이 실패한다.
    """
    plan = _r16_plan(assumption_71=assumption_71, confirmed=confirmed, port=port_factory())

    assert plan.ok is plan_ok
    precheck = plan.fid_safety["conflict_precheck"]
    read = precheck["read"]

    assert read["attempted"] is attempted
    assert read["complete"] is complete
    assert precheck["performed"] is performed
    # 읽지 않았으면 "기존 FID 0개"라는 **관측 주장**도 하지 않는다. 읽었으면 실제로 읽은
    # 것만 싣는다 — 기대값은 같은 포트 구성을 프로덕션 리더에 다시 태워 얻는다.
    if attempted:
        assert precheck["existing_fids"] == list(_existing_fids_from_console(port_factory()).fids)
    else:
        assert precheck["existing_fids"] == []
    if not attempted:
        # 미수행 사이트는 조회 대상 경로·프로퍼티조차 주장하지 않는다.
        assert precheck["property"] is None
        assert precheck["source_path"] is None
        assert read["child_count"] is None
        assert read["enumerated_count"] == 0

    # 같은 사실이 payload 사전(조작자 화면으로 나가는 축)에도 그대로 실린다.
    payload_read = plan.to_dict()["fid_safety"]["conflict_precheck"]["read"]
    assert payload_read["attempted"] is attempted
    assert payload_read["complete"] is complete


def test_the_confirmation_required_rejection_never_touches_the_console():
    """[round16 S16-02] 확인요구 거부 사이트는 콘솔을 **한 번도** 건드리지 않는다.

    payload의 `attempted=False`가 사실인지를 포트 대역으로 구조적으로 확인한다 —
    `ExplodingFidRigPort`는 `query_state`·`query_property` 어느 쪽이든 불리면 즉시
    `AssertionError`를 던진다. 이 테스트가 통과한다는 것이 곧 "안 읽었다"의 증거다.
    """
    plan = _r16_plan(
        assumption_71=ASSUMPTION_71_NEGATIVE, confirmed=None, port=ExplodingFidRigPort()
    )
    assert plan.rejection.code == FID_RANGE_CONFIRMATION_REQUIRED
    assert plan.fid_safety["conflict_precheck"]["read"]["attempted"] is False
    assert [target.assigned_fid for target in plan.targets] == [None]


# ==========================================================================
# S16-03 · M69 — 부분 관측 고지(`_fid_precheck_incomplete_check`)는 전수 단정된다
#
# GO 분기가 부분 관측으로 배정을 거부할 때 조작자에게 "무엇을 못 봤는지" 알리는 **유일한
# 구조화 항목**인데 세 뮤테이션이 전부 SURVIVED였다:
#   ① `**read.to_dict()`를 통째 삭제 → 여덟 축 계수 전부 소실
#   ② 같은 자리에 `complete: True · attempted: True` → 거부 사유와 자기모순
#   ③ `reason`을 "확인할 것은 없다." 안심 문구로 교체
# ==========================================================================

#: 고지에 실려야 하는 읽기 축 전부. 아래 전단사 단정이 프로덕션 `to_dict()`와 맞춘다.
_R16_PRECHECK_READ_KEYS = (
    "attempted",
    "child_count",
    "enumerated_count",
    "unseen_count",
    "unreadable_fid_count",
    "unusable_row_count",
    "unparsable_row_count",
    "over_enumerated",
    "root_unreadable",
    "complete",
)

#: 고지가 **스스로** 내는 세 필드.
_R16_PRECHECK_OWN_KEYS = ("kind", "label", "reason")

#: 부분 관측 거부 고지가 절대 쓰면 안 되는 안심 문구. round16 뮤테이션 ③이 심은 문구를
#: 포함한다 — 거부 payload가 "확인할 것은 없다"고 말하면 조작자는 사유를 무시한다.
_R16_REASSURING_PHRASES = (
    "확인할 것은 없다",
    "문제 없다",
    "문제없다",
    "이상 없다",
    "이상없다",
    "안전하다",
    "정상이다",
    "전부 읽었다",
)


def test_the_precheck_read_key_table_is_a_bijection_onto_the_production_payload():
    """[round16 S16-03] 축 목록이 `ExistingFidRead.to_dict()`와 1:1이다.

    `to_dict()`에서 축을 지우거나 더하면 실패하고, 이 표에서 행을 지워도 실패한다 —
    그래서 아래 전수 단정이 "열 축 중 여섯 축만" 상태로 조용히 축소될 수 없다.
    """
    from server.vwx.patchplan import ExistingFidRead

    assert tuple(ExistingFidRead().to_dict()) == _R16_PRECHECK_READ_KEYS


@pytest.mark.parametrize(
    "axis,port_kwargs,expected_axes,expected_phrase",
    R15_SOLE_AXIS_ROWS,
    ids=[f"incomplete-check/{row[0]}" for row in R15_SOLE_AXIS_ROWS],
)
def test_the_incomplete_check_carries_every_read_axis_with_the_observed_value(
    axis, port_kwargs, expected_axes, expected_phrase
):
    """[round16 S16-03 · M69] 고지가 **여덟 축 계수 전부**를 관측값 그대로 싣는다.

    [round16 M69①] `patchplan.py` `_fid_precheck_incomplete_check`에서 `**read.to_dict()`를
      지우면 키 집합 단정이 실패한다.
    [round16 M69②] 같은 자리에 `"complete": True, "attempted": True`를 심으면 값 단정과
      아래 자기모순 금지 단정이 실패한다.
    [round16 M69③] `reason`을 "확인할 것은 없다."로 바꾸면 문구 단정이 실패한다.
    """
    from server.vwx.verdicts import FID_CONFLICT_PRECHECK_INCOMPLETE

    port = None if port_kwargs is None else _R15RawPort(**port_kwargs)
    read = _existing_fids_from_console(port)
    plan = _plan_with(port)

    assert plan.ok is False
    (check,) = plan.skipped_checks

    # ① 존재 — 고지 자신의 세 필드 + 읽기 축 전부. 그 밖의 키는 없다.
    assert set(check) == set(_R16_PRECHECK_OWN_KEYS) | set(_R16_PRECHECK_READ_KEYS)

    # ② 값 — 축마다 **관측된 값 그대로**. 계수를 상수로 갈아끼우면 여기서 걸린다.
    observed = read.to_dict()
    for key in _R16_PRECHECK_READ_KEYS:
        assert check[key] == observed[key], key

    # ③ 자기모순 금지 — 거부 payload 안의 `complete`는 반드시 거짓이다.
    assert check["complete"] is False
    assert check["kind"] == FID_CONFLICT_PRECHECK_INCOMPLETE
    assert check["label"]

    # ④ 사유 문구 — 왜 막았는지를 말하고, 안심시키지 않는다.
    assert "부분 관측" in check["reason"]
    assert "빈 FID를 단정할 수 없다" in check["reason"]
    for phrase in _R16_REASSURING_PHRASES:
        assert phrase not in check["reason"], phrase

    # ⑤ 같은 고지가 조작자 화면 payload에도 그대로 나간다.
    (payload_check,) = plan.to_dict()["skipped_checks"]
    assert payload_check == dict(check)


def test_the_incomplete_check_axes_are_not_all_default_in_at_least_one_row():
    """[round16 S16-03] 비공허성 — 위 전수 단정이 "전부 0"만 보는 표가 아니다.

    어느 행에서는 계수 축이 실제로 0이 아닌 값을 싣는다. 그 사실이 없으면 `**read.to_dict()`
    삭제 대신 `**{k: 0 for k in ...}` 같은 뮤테이션이 값 단정을 빠져나간다.
    """
    port = _R15RawPort(
        node={"childCount": 4},
        children=[{"i": 1}, {"i": 2}, {"i": 2}, None],
        fids={1: 100},
    )
    (check,) = _plan_with(port).skipped_checks

    assert check["unseen_count"] == 2
    assert check["unreadable_fid_count"] == 1
    assert check["unusable_row_count"] == 1
    assert check["unparsable_row_count"] == 1
    assert check["enumerated_count"] == 2
    assert check["child_count"] == 4
    assert check["attempted"] is True
    assert check["complete"] is False


# ---- 안심 문구 금지 목록의 대조군 ------------------------------------------------
#
# 금지 목록은 **그 자체로는 게이트가 아니다** — 목록에서 항목을 지우면 그 항목의 검사도
# 함께 사라져 아무것도 실패하지 않는다(round15가 같은 결함으로 지적받았다). 그래서
# 목록과 **독립인 침해 표본 표**를 두고, 표본을 **프로덕션 사본에 심어** 프로덕션 함수의
# 반환값을 검사한다. `test_autopatch_verify.py`의 `_PLUGIN_OUTCOME_PROBES` 선례와 같다.

PATCHPLAN_PATH = Path("server/vwx/patchplan.py")
PATCHPLAN_SOURCE = PATCHPLAN_PATH.read_text(encoding="utf-8")

#: 사본에서 갈아끼울 **사유 문구 한 덩어리**. 앵커가 사라지면 아래 대조군이 즉시 실패한다.
INCOMPLETE_REASON_ANCHOR = (
    '            "기존 FID 열거가 부분 관측이라 빈 FID를 단정할 수 없다 — "\n'
    '            "절단은 이 콘솔의 기본 경로이고 childCount가 진짜 총계다."'
)

_PATCHPLAN_UNDER_TEST = "server.vwx._patchplan_under_test"


def _load_patchplan(source: str) -> dict:
    """`patchplan.py` 소스를 **진짜 모듈로** 적재한다 — `test_autopatch_execute._load` 관례.

    `dataclass`가 `sys.modules` 조회를 하므로 네임스페이스 dict만으로는 적재되지 않는다.
    """
    import sys
    from types import ModuleType

    module = ModuleType(_PATCHPLAN_UNDER_TEST)
    module.__file__ = str(PATCHPLAN_PATH)
    saved = sys.modules.get(_PATCHPLAN_UNDER_TEST)
    sys.modules[_PATCHPLAN_UNDER_TEST] = module
    try:
        exec(compile(source, str(PATCHPLAN_PATH), "exec"), module.__dict__)
    finally:
        if saved is None:
            del sys.modules[_PATCHPLAN_UNDER_TEST]
        else:
            sys.modules[_PATCHPLAN_UNDER_TEST] = saved
    return module.__dict__


def test_the_patchplan_copy_loader_reproduces_the_untouched_reason():
    """사본 적재가 진짜임을 먼저 고정한다 — 원문 사본은 원본과 같은 사유를 낸다."""
    namespace = _load_patchplan(PATCHPLAN_SOURCE)
    check = namespace["_fid_precheck_incomplete_check"](namespace["ExistingFidRead"]())
    (original,) = _plan_with(None).skipped_checks
    assert check["reason"] == original["reason"]
    assert PATCHPLAN_SOURCE.count(INCOMPLETE_REASON_ANCHOR) == 1, "사유 앵커가 유일하지 않다"


#: 침해 표본 — (금지 문구, 그 문구에만 걸리는 사유 문장). 금지 목록에서 **파생하지 않는다**.
_R16_REASSURING_PROBES = (
    ("확인할 것은 없다", "확인할 것은 없다."),
    ("문제 없다", "읽기에 문제 없다."),
    ("문제없다", "읽기에 문제없다."),
    ("이상 없다", "열거에 이상 없다."),
    ("이상없다", "열거에 이상없다."),
    ("안전하다", "이 배정은 안전하다."),
    ("정상이다", "스냅샷이 정상이다."),
    ("전부 읽었다", "기존 픽스처를 전부 읽었다."),
)


def test_the_reassuring_probe_table_is_a_bijection_onto_the_ban_list():
    """[round16 S16-03] 표와 금지 목록이 1:1 — 목록에서 문구를 지우거나 더하면 실패한다."""
    assert tuple(phrase for phrase, _ in _R16_REASSURING_PROBES) == _R16_REASSURING_PHRASES


@pytest.mark.parametrize(
    "phrase,sentence",
    _R16_REASSURING_PROBES,
    ids=[phrase for phrase, _ in _R16_REASSURING_PROBES],
)
def test_each_reassuring_probe_is_caught_by_exactly_one_banned_phrase(phrase, sentence):
    """[round16 S16-03] 표본이 **겨냥한 문구에만** 걸린다 — 인과가 다른 문구에 가려지지 않는다.

    `_R16_REASSURING_PHRASES`에서 `phrase`를 지우면 짝이 되는 아래 대조군이 빈 목록을 받아
    실패한다. 이 단정은 그 인과를 고정한다.
    """
    assert [p for p in _R16_REASSURING_PHRASES if p in sentence] == [phrase]


@pytest.mark.parametrize(
    "phrase,sentence",
    _R16_REASSURING_PROBES,
    ids=[phrase for phrase, _ in _R16_REASSURING_PROBES],
)
def test_the_reassuring_ban_catches_each_probe_planted_in_the_production_reason(phrase, sentence):
    """[round16 S16-03] 비공허성(전수) — 표본마다 **프로덕션 사본**에 심어 금지가 잡는지 본다.

    금지 목록에서 이 표본이 겨냥한 문구를 지우면 `offenders`가 비어 이 단정이 실패한다 —
    목록만 있고 대조군이 없던 상태에서는 문구를 지워도 아무것도 실패하지 않았다.
    """
    planted = PATCHPLAN_SOURCE.replace(INCOMPLETE_REASON_ANCHOR, f'            "{sentence}"', 1)
    assert planted != PATCHPLAN_SOURCE
    namespace = _load_patchplan(planted)
    check = namespace["_fid_precheck_incomplete_check"](namespace["ExistingFidRead"]())

    offenders = [p for p in _R16_REASSURING_PHRASES if p in check["reason"]]
    assert offenders == [phrase]


# ==========================================================================
# S16-08 (informational) — 한 행이 두 축을 올리는 것은 **의도된 것**이다
# ==========================================================================


def test_a_single_unparsable_row_deliberately_raises_two_axes_at_once():
    """[round16 S16-08] `unseen`과 `unparsable_rows`가 같은 행에서 함께 오르는 것은 버그가 아니다.

    `children=[{'i': 1}, None]` · `childCount=2`에서 비매핑 행 하나가
    `unparsable_rows=1`(해석 불가 행이 있었다)과 `unseen=1`(선언 2개 중 1개만 슬롯으로
    확인됐다)을 **동시에** 올린다. 두 축은 서로 다른 명제이고, 둘 다 참이다:
    "해석 못 한 행이 있다"와 "선언된 슬롯 하나를 끝내 확인하지 못했다".
    산술적 불가능(`unseen > child_count`)이 아니며 — round13 S05 · round14 T01/T03이 막은
    것은 그 쪽이다 — 방향도 **더 막는 쪽**이라 안전하다.

    **고치지 마라.** 이 중복 계수를 "한 행은 한 축"으로 바꾸면 `unseen`이 0이 되고, 그러면
    `childCount`와 열거 수의 대조라는 **가장 강한 축**이 이 스냅샷에서 침묵한다.
    이 테스트는 다음 라운드가 그것을 버그로 오인해 축을 약화시키는 것을 막는다.
    """
    read = _existing_fids_from_console(
        _R15RawPort(node={"childCount": 2}, children=[{"i": 1}, None], fids={1: 100})
    )

    assert read.unparsable_rows == 1
    assert read.unseen == 1
    assert read.enumerated_count == 1
    assert read.child_count == 2
    # 산술적으로 가능한 상태다 — 못 본 슬롯 수가 선언 총계를 넘지 않는다.
    assert 0 <= read.unseen <= read.child_count
    assert read.complete is False
    # 두 축이 각자 자기 문장을 낸다 — 조작자는 두 사실을 따로 읽는다.
    assert "선언 2개 중 1개를 열거하지 못했다" in read.reason()
    assert "슬롯으로 해석되지 않는 행 1개가 섞여 있다" in read.reason()


# ==========================================================================
# M54 — bool 가드는 정수 판독기 **전부**의 규약이다
#
# `_optional_int`의 `and not isinstance(value, bool)`를 지우면 `True`가 `1`로 해석돼
# 슬롯·주소·`childCount`가 오염되는데 SURVIVED였다. 형제 `_fid_int`는 전체 스위트에서
# 잡혔지만 그 인과를 명시한 테스트는 없었다. 여기서 **네 판독기 전부**를 표로 연다.
# ==========================================================================

#: (함수 이름, bool 입력, 기대 반환) — `plan_addresses`는 반환이 아니라 갈래로 확인한다.
_R16_BOOL_GUARD_ROWS = (
    ("plan_addresses", True, None),
    ("_fid_int", True, None),
    ("_optional_int", True, None),
    ("_required_int", True, 0),
)


def _r16_production_bool_guard_functions():
    """`patchplan.py`에서 `isinstance(..., bool)` 가드를 가진 함수를 소스 순서로 전수."""
    import ast

    tree = ast.parse(_r16_patchplan_source())
    names = []
    for fn in _r16_in_source_order(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ):
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "isinstance"
                and getattr(node.args[1], "id", None) == "bool"
            ):
                names.append(fn.name)
                break
    return tuple(names)


def test_the_bool_guard_table_is_a_bijection_onto_production():
    """[round16 M54] bool 가드 표가 프로덕션 함수 목록과 1:1이다.

    어느 판독기에서든 `isinstance(value, bool)` 가드를 지우면 이 단정이 실패한다 —
    형제 판독기를 빠뜨린 채 한쪽만 지키는 상태가 구조적으로 불가능해진다.
    표에서 행을 지워도 실패한다.
    """
    assert tuple(name for name, _, _ in _R16_BOOL_GUARD_ROWS) == (
        _r16_production_bool_guard_functions()
    )


def test_every_int_reader_refuses_a_bool():
    """[round16 M54] `True`는 `1`이 아니다 — 네 판독기가 전부 그렇게 판정한다.

    `_optional_int`·`_required_int`·`_fid_int`의 `and not isinstance(value, bool)`를 지우거나
    `plan_addresses`의 `or isinstance(footprint, bool)`를 지우면 해당 단정이 실패한다.
    """
    from server.vwx.patchplan import _fid_int, _optional_int, _required_int

    assert _optional_int(True) is None
    assert _optional_int(False) is None
    assert _optional_int(1) == 1
    assert _required_int(True) == 0
    assert _required_int(False) == 0
    assert _required_int(1) == 1
    assert _fid_int(True) is None
    assert _fid_int(False) is None
    assert _fid_int(1) == 1

    # `plan_addresses`는 반환값이 아니라 **갈래**로 답한다 — 폭이 `True`면 폭을 모르는 것이다.
    from server.vwx.patchplan import plan_addresses
    from server.vwx.verdicts import FOOTPRINT_UNKNOWN

    report = _one_candidate_report()
    target = build_patch_plan(report, selected=[]).candidates[0]
    bool_width = plan_addresses([target], footprints={target.id: True}, occupied={})
    assert bool_width.entries == ()
    assert [exclusion.code for exclusion in bool_width.exclusions] == [FOOTPRINT_UNKNOWN]
    # 비공허성 — 같은 호출에 진짜 정수 폭을 주면 계획이 선다.
    int_width = plan_addresses([target], footprints={target.id: 1}, occupied={})
    assert [entry.candidate_id for entry in int_width.entries] == [target.id]


def test_a_boolean_child_count_is_not_read_as_one_declared_fixture():
    """[round16 M54 · 프로덕션 경로] `childCount: True`가 "선언 1대"로 읽히면 배정이 열린다.

    `_optional_int`의 bool 가드를 지우면 `child_count=1`·`enumerated_count=1`이 되어
    `unseen=0`·`complete=True`가 되고, **조회한 적 없는 픽스처 위에 FID가 배정된다**.
    가드가 있으면 총계를 모르는 것이므로 `unseen=None`으로 막힌다.
    """
    port = _R15RawPort(node={"childCount": True}, children=[{"i": 1}], fids={1: 100})
    read = _existing_fids_from_console(port)

    assert read.child_count is None
    assert read.unseen is None
    assert read.complete is False

    plan = _plan_with(port)
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]
    assert "총계(childCount)를 읽지 못해" in plan.rejection.reason


def test_a_boolean_fid_value_is_counted_as_unreadable_not_as_fid_one():
    """[round16 M54 형제 축] `_fid_int`의 bool 가드 — FID 값 `True`는 FID 1이 아니다.

    가드를 지우면 `existing_fids=(True,)`가 되어 부분 관측이 **완전한 읽기로** 등급되고,
    FID 1을 "이미 쓰이는 번호"로 오판한다. 가드가 있으면 그 슬롯은 미판독으로 세어
    배정 자체가 막힌다 — 모르면 하지 않는다.
    """
    port = _R15RawPort(node={"childCount": 1}, children=[{"i": 1}], fids={1: True})
    read = _existing_fids_from_console(port)

    assert read.fids == ()
    assert read.unreadable_fids == 1
    assert read.complete is False

    plan = _plan_with(port)
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert "열거된 슬롯 1개의 FID 값을 얻지 못했다" in plan.rejection.reason
