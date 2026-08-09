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
    """부분 관측으로 '빈 FID'를 단정하면 이미 쓰이는 번호를 배정하게 된다.

    **[round19 재조준]** 포트를 `_CountingFidPort`에서 `_ShapedFidPort`로 바꿨다.
    round19가 붙인 절단 복구 스윕은 숨은 슬롯을 프로브해 **회수**하므로,
    `_CountingFidPort`(어떤 슬롯이든 `ok=True`로 답한다)에서는 절단이 회수되고
    배정이 정당하게 진행된다 — 그 경로는 아래
    `test_r19_a_truncated_enumeration_is_recovered_by_the_sweep`가 잡는다.
    이 테스트가 지키는 명제는 **회수하지 못한 절단은 여전히 배정을 거부한다**이고,
    그것을 재려면 숨은 슬롯이 값을 내놓지 않는 포트가 필요하다. 명제를 약화한 것이
    아니라 스윕이 도달할 수 없는 자리로 옮긴 것이다.
    """
    plan = _plan_with(_ShapedFidPort(child_count=2, rows=[1], fids={1: 100}))
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]
    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read == {
        "attempted": True,
        "child_count": 2,
        "enumerated_count": 1,
        "recovered_count": 0,
        "recovery_boundary": 2,
        "unseen_count": 1,
        "unreadable_fid_count": 0,
        "unusable_row_count": 0,
        "unparsable_row_count": 0,
        "probe_failure_count": 0,
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
    # [round17 S17-04] 조작자가 보는 것은 `reason()` **조각**과 `notes()` 완결 문장의 합이다.
    # 꼬리 판정(`자기모순`)을 조각에서 빼 독립 문장으로 옮겼으므로 — 조각 안에 두면 조립된
    # 사유 한 문장에 ` — `가 둘이 된다(S17-04) — 사실 존재 확인도 그 합 위에서 한다.
    reason = " ".join((read.reason(), *read.notes()))
    assert expected_phrase in reason, reason
    assert read.reason() != "부분 관측이다"


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
    # --- round19 절단 복구 스윕 (TruncationSweep) — 스윕의 detail 축 3개.
    # 고지가 "스윕을 돌렸는가 · 어디까지 · 몇 개를 회수했는가 · 프로브가 몇 건
    # 결말을 못 냈는가"를 싣지 않으면, 조작자는 판독이 열거만으로 이뤄졌는지
    # 스윕까지 갔는지 구별할 수 없다.
    "recovered_count",
    "recovery_boundary",
    "unseen_count",
    "unreadable_fid_count",
    "unusable_row_count",
    "unparsable_row_count",
    "probe_failure_count",
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
# M54 — bool 가드는 `patchplan.py` 정수 판독기 **전부**의 규약이다
#
# `_optional_int`의 `and not isinstance(value, bool)`를 지우면 `True`가 `1`로 해석돼
# 슬롯·주소·`childCount`가 오염되는데 SURVIVED였다. 형제 `_fid_int`는 전체 스위트에서
# 잡혔지만 그 인과를 명시한 테스트는 없었다. 여기서 `patchplan.py`의 **네 판독기**를 표로 연다.
#
# **[round17 #7 정정] 이 절의 선언을 사실대로 좁혔다.** round16은 이 표를 "정수 판독기
# **전부**의 규약"이라 선언했는데 아래 파서는 `patchplan.py` 한 모듈만 읽는다. 실제 가드는
# 여섯 곳이고, `typemap._optional_int`와 `luagen._lua_int`의 가드를 지워도 스위트
# 5,690건이 전건 통과했다 — `luagen._lua_int`는 **전달물 `fid`를 만드는** 자리다.
# `server/vwx` 전 모듈을 덮는 표는 이 파일 끝 round17 절(`_R17_BOOL_GUARD_SITES`)에 있다.
# ==========================================================================

#: (함수 이름, bool 입력, 기대 반환) — `plan_addresses`는 반환이 아니라 갈래로 확인한다.
#: **`patchplan.py`에 한정된 표다**(round17 #7). 전 모듈 표는 `_R17_BOOL_GUARD_SITES`.
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
    """[round16 M54] bool 가드 표가 `patchplan.py` 함수 목록과 1:1이다.

    `patchplan.py`의 어느 판독기에서든 `isinstance(value, bool)` 가드를 지우면 이 단정이
    실패한다 — 형제 판독기를 빠뜨린 채 한쪽만 지키는 상태가 구조적으로 불가능해진다.
    표에서 행을 지워도 실패한다. **[round17 #7] 다른 모듈은 이 표의 범위 밖이다.**
    """
    assert tuple(name for name, _, _ in _R16_BOOL_GUARD_ROWS) == (
        _r16_production_bool_guard_functions()
    )


def test_every_int_reader_refuses_a_bool():
    """[round16 M54] `True`는 `1`이 아니다 — `patchplan.py`의 네 판독기가 그렇게 판정한다.

    `_optional_int`·`_required_int`·`_fid_int`의 `and not isinstance(value, bool)`를 지우거나
    `plan_addresses`의 `or isinstance(footprint, bool)`를 지우면 해당 단정이 실패한다.

    **[round17 #7] 형제 모듈은 여기 없다** — `typemap._optional_int`·`luagen._lua_int`는
    이 파일 끝 round17 절이 덮는다.
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


# --- round17 스코프 확장·문장 전문 동등 (ScopeAndTables) ---
#
#   [round17 #7] `_R16_BOOL_GUARD_ROWS`가 "정수 판독기 **전부**의 규약"이라 선언하면서
#     파서는 `patchplan.py` 한 모듈만 읽었다. 실제 가드는 **여섯 곳**이고 두 곳
#     (`typemap._optional_int` · `luagen._lua_int`)은 무게이트였다 — 지워도 5,690건이
#     전건 통과했다. `luagen._lua_int`가 만드는 것은 **사람이 콘솔에서 실행할 Lua의 `fid`**다.
#     여기서 스캔을 `server/vwx` **전 모듈**로 넓히고, 각 가드마다 프로덕션 호출로 짚는다.
#
#   [round17 #6] `_fid_precheck_incomplete_check` 사유가 어휘목록(금지 문구 8개)과
#     부분문자열 조각 2개로만 지켜졌다. 사유 **뒤에** 안심 문장을 붙이면 셋 다 통과한다.
#     같은 커밋이 caveat 사유에는 **문장 전문 리터럴 고정**을 줬다 — 형제에게 다른 등급을
#     준 전형이다. 여기서 같은 등급으로 맞춘다.


def _r17_vwx_bool_guard_sites() -> tuple[tuple[str, str], ...]:
    """`server/vwx` **전 모듈**에서 `isinstance(..., bool)` 가드를 가진 함수를 (모듈, 함수)로 전수.

    round16 판(`_r16_production_bool_guard_functions`)은 `patchplan.py`만 읽었다.
    스캔 대상은 디렉터리에서 파생하므로 모듈이 하나 생기면 범위가 자동으로 따라간다.
    """
    import ast

    sites: list[tuple[str, str]] = []
    for path in sorted(Path("server/vwx").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in _r16_in_source_order(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            for node in ast.walk(fn):
                if (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "isinstance"
                    and len(node.args) > 1
                    and getattr(node.args[1], "id", None) == "bool"
                ):
                    sites.append((path.name, fn.name))
                    break
    return tuple(sites)


#: bool 가드 **전 모듈 전수 표**. (모듈, 함수). 소스 순서 · 모듈 이름 순.
#: round16 표는 위 네 행(`patchplan.py`)뿐이었고, 아래 두 행이 **무게이트**였다.
_R17_BOOL_GUARD_SITES = (
    ("luagen.py", "_lua_int"),
    ("patchplan.py", "plan_addresses"),
    ("patchplan.py", "_fid_int"),
    ("patchplan.py", "_optional_int"),
    ("patchplan.py", "_required_int"),
    ("typemap.py", "_optional_int"),
)


def test_the_bool_guard_table_covers_every_vwx_module_not_just_patchplan():
    """[round17 #7] bool 가드 표가 `server/vwx` **전 모듈**과 1:1이다.

    [round17 #7] `typemap.py:654`의 `isinstance(value, bool)`를 지우면 실패한다.
    [round17 #7] `luagen.py:129`의 `isinstance(value, bool)`를 지우면 실패한다.
    [round17 #7] 어느 모듈에서든 가드를 더해도 행 없이는 통과하지 못한다.
    [round17 #7] 표에서 행을 지워도 실패한다.
    round16 표(`_R16_BOOL_GUARD_ROWS`)는 `patchplan.py` 네 행뿐이라 두 뮤테이션 모두
    SURVIVED였다 — 그 표는 이제 스스로를 `patchplan.py`로 선언한다.
    """
    assert _r17_vwx_bool_guard_sites() == _R17_BOOL_GUARD_SITES
    # 표가 round16 범위를 **진짜로** 넘는다 — 두 모듈이 새로 들어왔다.
    assert {module for module, _ in _R17_BOOL_GUARD_SITES} == {
        "luagen.py",
        "patchplan.py",
        "typemap.py",
    }
    patchplan_rows = tuple(fn for module, fn in _R17_BOOL_GUARD_SITES if module == "patchplan.py")
    assert patchplan_rows == tuple(name for name, _, _ in _R16_BOOL_GUARD_ROWS)


def test_the_typemap_int_reader_refuses_a_bool_on_the_production_path():
    """[round17 #7] `typemap._optional_int`의 bool 가드 — `childCount: True`는 "1대"가 아니다.

    [round17 #7] `typemap.py:654`의 `and not isinstance(value, bool)`를 지우면 실패한다.
    가드를 지우면 FixtureType 라이브러리의 `i: True`가 **인덱스 1**로 읽혀,
    조회한 적 없는 라이브러리 항목을 가리키는 경로(`Patch/FixtureTypes/1/DMXModes`)가 선다.
    반환값이 아니라 **라이브러리 판독 결과**로 확인한다 — 프로덕션 산출 경로다.
    """
    from server.vwx.typemap import FIXTURE_TYPE_LIBRARY_ROOT, read_fixture_type_library

    class _BoolIndexPort:
        def query_state(self, path: str) -> dict:
            if path == FIXTURE_TYPE_LIBRARY_ROOT:
                return {
                    "ok": True,
                    "path": path,
                    "node": {"childCount": True},
                    "children": [{"i": True, "name": "LEDBeam"}, {"i": 3, "name": "Robin"}],
                    "truncated": False,
                }
            return {"ok": False, "path": path, "error": "not readable"}

        def query_property(self, path: str, property_name: str) -> dict:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}

    library = read_fixture_type_library(_BoolIndexPort())

    # `i: True`인 행은 인덱스를 얻지 못해 **빠진다** — 인덱스 1로 승격되지 않는다.
    assert [entry.index for entry in library.types] == [3]
    assert [entry.name for entry in library.types] == ["Robin"]


def test_the_luagen_int_reader_refuses_a_bool_on_the_deliverable_path():
    """[round17 #7] `luagen._lua_int`의 bool 가드 — `True`인 FID는 Lua에 `1`로 나가지 않는다.

    [round17 #7] `luagen.py:129`의 `isinstance(value, bool)`를 지우면 실패한다.
    이 가드가 만드는 것은 **사람이 콘솔에서 실행할 플러그인의 `fid` 인자**다. `True`가 `1`로
    조용히 통과하면 조작자가 지정하지 않은 FID 1로 픽스처가 생성되고, 이 앱에는 되돌리기가 없다.
    """
    from server.vwx.luagen import LuaGenerationError, LuaPatchEntry, render_addfixtures_plugin

    entry = LuaPatchEntry(
        console_type="Robin LEDBeam 350",
        console_mode="Mode 1",
        fid=True,
        name="LEDBeam 101",
        universe=1,
        address=1,
    )
    with pytest.raises(LuaGenerationError) as raised:
        render_addfixtures_plugin([entry])
    assert "정수 필드에 정수가 아닌 값이 왔다" in str(raised.value)

    # 비공허성 — 같은 호출에 진짜 정수를 주면 플러그인이 만들어지고 `fid = "101"`이 박힌다.
    ok = render_addfixtures_plugin([LuaPatchEntry(**{**entry.__dict__, "fid": 101})])
    assert 'fid = "101"' in ok


# ---- [round17 #6] 부분 관측 고지 사유는 **문장 전문**으로 고정된다 ---------------------

#: 프로덕션 사유 **전문**. caveat 사유가 이미 받는 등급을 형제 사유에도 준다.
#: 이 문자열은 되돌릴 수 없는 배정 앞의 **유일한 고지**다 — 리터럴 고정이 곧 그 변경을
#: 사람 눈에 띄게 하는 장치다(round16 A1 ②가 caveat에 세운 것과 같은 논거).
_R17_INCOMPLETE_REASON = (
    "기존 FID 열거가 부분 관측이라 빈 FID를 단정할 수 없다 — "
    "절단은 이 콘솔의 기본 경로이고 childCount가 진짜 총계다."
)


def test_the_incomplete_check_reason_is_fixed_verbatim():
    """[round17 #6] 사유가 **문장 전문 동등**이다 — 앞뒤로 무엇을 붙여도 실패한다.

    [round17 #6] 사유 뒤에 `"그 밖에 우려할 것은 없으므로 그대로 진행해도 좋다."`를
      **덧붙이면** 여기서 실패한다. round16까지 그 조작은 안심 문구 금지 8개를 전부 피하고
      필수 조각 두 개(`부분 관측`·`빈 FID를 단정할 수 없다`)를 남기고 앵커 부분문자열도
      온전해서 **5,690건을 전건 통과했다**.
    [round17 #6] 사유를 다른 문장으로 갈아도 실패한다 — 어휘목록 방식과 달리 우회로가 없다.

    같은 등급이 형제 caveat 사유에 이미 걸려 있다(round16 A1 ②). 두 사유는 같은 커밋이
    만들었는데 한쪽만 전문 고정을 받았다 — 그 비대칭이 round17 #6의 기제다.
    """
    from server.vwx.patchplan import ExistingFidRead

    (check,) = _plan_with(None).skipped_checks
    assert check["reason"] == _R17_INCOMPLETE_REASON

    # 같은 문장이 **함수 단위**에서도 그대로다 — 계획 조립이 뒤에 무엇을 덧대지 않는다.
    from server.vwx.patchplan import _fid_precheck_incomplete_check

    assert _fid_precheck_incomplete_check(ExistingFidRead())["reason"] == _R17_INCOMPLETE_REASON

    # 그리고 조작자 화면 payload에도 같은 전문이 나간다.
    (payload_check,) = _plan_with(None).to_dict()["skipped_checks"]
    assert payload_check["reason"] == _R17_INCOMPLETE_REASON


def test_the_verbatim_reason_gate_is_not_vacuous():
    """대조의 대조 — 사유 뒤에 한 절을 덧붙인 **프로덕션 사본**에서 위 단정이 실제로 깨진다.

    어휘목록 검사는 이 사본을 통과한다는 것까지 함께 보인다 — 그것이 round17 #6이 실증한
    바로 그 상태이고, 전문 동등만이 그것을 잡는다.
    """
    appended = "그 밖에 우려할 것은 없으므로 그대로 진행해도 좋다."
    planted = PATCHPLAN_SOURCE.replace(
        INCOMPLETE_REASON_ANCHOR,
        INCOMPLETE_REASON_ANCHOR + f'\n            "{appended}"',
        1,
    )
    assert planted != PATCHPLAN_SOURCE
    namespace = _load_patchplan(planted)
    reason = namespace["_fid_precheck_incomplete_check"](namespace["ExistingFidRead"]())["reason"]

    # ① 전문 동등은 깨진다 — 이것이 round17이 새로 세운 등급이다.
    assert reason != _R17_INCOMPLETE_REASON
    # ② 그런데 round16의 세 검사는 **전부 통과한다** — 어휘목록 방식이 반증되는 자리다.
    assert "부분 관측" in reason
    assert "빈 FID를 단정할 수 없다" in reason
    assert [phrase for phrase in _R16_REASSURING_PHRASES if phrase in reason] == []
    assert INCOMPLETE_REASON_ANCHOR in planted


# ==========================================================================
# --- round17 S17-04 FID 사전검사 사유의 문장 형태 (SiblingOccupants) ---
#
# `build_patch_plan`의 사전검사 거부 사유는 **조각 + 독립 문장들**로 조립된다.
# round16까지 조각(`ExistingFidRead.reason()`)이 자체에 ` — `를 품고 있었고, 호출부가 그
# 조각을 대시 있는 문장 **안에** 끼워 넣어 한 문장에 대시가 둘이 됐다(S17-04, 48조합 중 24건).
# 꼬리는 `notes()`가 독립 문장으로 돌려주고, `assemble_sentences`가 결과 형태를 강제한다.
#
# 아래 두 축을 함께 건다 — 한 축만 걸면 다른 축이 곧 같은 결함을 다시 만든다(HARD 규율 1):
#   축 1 — 꼬리 문장이 **조작자에게 실제로 도달한다**(옮기면서 잃어버리지 않았다).
#   축 2 — 조립된 사유가 **여덟 축 전부**에서 형태 불변식을 지킨다.
# ==========================================================================


def _r17_read_for(axis: str):
    """`R15_SOLE_AXIS_ROWS`의 포트 구성을 축 이름으로 되찾아 그 축만 발화시킨다."""
    (row,) = [candidate for candidate in R15_SOLE_AXIS_ROWS if candidate[0] == axis]
    port_kwargs = row[1]
    return _existing_fids_from_console(None if port_kwargs is None else _R15RawPort(**port_kwargs))


def _r17_production_read_notes() -> tuple[str, ...]:
    """`patchplan.py`의 `ExistingFidRead.notes()`가 돌려줄 수 있는 **문장 리터럴 전수**를 뽑는다.

    테스트가 문장을 자기 리터럴로 들고 비교하면 프로덕션에서 문장을 지워도 아무도 실패하지
    않는다(자기 비교). 그래서 프로덕션 소스에서 뽑아 표와 맞춘다.
    """
    import ast

    tree = ast.parse(PATCHPLAN_SOURCE)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "notes"
    )
    return tuple(
        element.value
        for node in ast.walk(function)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple)
        for element in node.value.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    )


#: (축 이름, 그 축에서 조작자에게 나가야 하는 **독립 문장**)
#: 축 이름은 `R15_SOLE_AXIS_ROWS`의 것을 그대로 쓴다 — 포트 구성을 두 벌 들고 있지 않는다.
_R17_FID_READ_NOTE_ROWS = (
    ("attempted=False", "기존 FID를 하나도 확인하지 못했다."),
    ("root_unreadable", "기존 FID를 하나도 확인하지 못했다."),
    ("over_enumerated", "열거가 선언 총계를 넘었으므로 이 스냅샷은 자기모순이다."),
)


def test_the_fid_read_note_table_is_a_bijection_onto_the_noted_axes():
    """[round17 S17-04] 꼬리 문장 표가 **실제로 꼬리를 내는 축 전수**와 1:1이다.

    ① 표에서 행을 지우면 축 집합이 어긋나 실패한다.
    ② 프로덕션이 새 축에 꼬리를 붙이면 행 없이는 통과하지 못한다.
    ③ 프로덕션에서 꼬리 문장을 지우면(`notes()`가 `()`를 돌려주면) 그 축이 사라져 실패한다.
    """
    noted_axes = {axis for axis, *_ in R15_SOLE_AXIS_ROWS if _r17_read_for(axis).notes()}
    assert noted_axes == {axis for axis, _ in _R17_FID_READ_NOTE_ROWS}


def test_the_fid_read_note_table_is_a_bijection_onto_the_production_sentences():
    """[round17 S17-04] 표의 문장이 프로덕션 `notes()`의 **리터럴 전수**와 1:1이다.

    [round17 #S17-04] `notes()`의 어느 갈래든 `return ()`으로 바꾸면 실패한다 —
    옮기면서 문장을 잃어버리는 것이 이 처방의 가장 그럴듯한 회귀다.
    """
    assert {note for _, note in _R17_FID_READ_NOTE_ROWS} == set(_r17_production_read_notes())


@pytest.mark.parametrize(
    "axis,expected_note",
    _R17_FID_READ_NOTE_ROWS,
    ids=[row[0] for row in _R17_FID_READ_NOTE_ROWS],
)
def test_each_note_axis_reaches_the_operator_as_an_independent_sentence(axis, expected_note):
    """[round17 S17-04] 꼬리 문장이 **조립된 거부 사유에 실제로 실린다** — 독립 문장으로.

    조각에서 빼내기만 하고 조립부에 잇지 않으면 조작자는 판정 근거를 잃는다. 그것은
    형태를 고치면서 내용을 버리는 것이고, 이 SPEC이 반복한 "한 축만 고쳤다"의 변형이다.

    [round17 #S17-04] `ExistingFidRead.notes()`를 `()`로 무력화하면 실패한다.
    [round17 #S17-04] `build_patch_plan`의 조립부에서 `*existing_read.notes()`를 빼면 실패한다.
    """
    read = _r17_read_for(axis)
    assert read.notes() == (expected_note,)
    assert " — " not in expected_note, "꼬리는 독립 문장이다 — 대시를 다시 품으면 무의미하다"

    plan = _plan_with(None if axis == "attempted=False" else _R15RawPort(**_r17_port_kwargs(axis)))
    assert plan.ok is False
    assert expected_note in plan.rejection.reason, plan.rejection.reason


def _r17_port_kwargs(axis: str):
    (row,) = [candidate for candidate in R15_SOLE_AXIS_ROWS if candidate[0] == axis]
    return row[1]


@pytest.mark.parametrize(
    "axis,port_kwargs,_axes,_phrase",
    R15_SOLE_AXIS_ROWS,
    ids=[row[0] for row in R15_SOLE_AXIS_ROWS],
)
def test_the_assembled_precheck_reason_keeps_its_sentence_shape(axis, port_kwargs, _axes, _phrase):
    """[round17 S17-04] 조립된 사유가 **여덟 축 전부**에서 형태 불변식을 지킨다.

    판정은 프로덕션 `sentence_shape_violation`이 한다 — 테스트가 규칙 사본을 들고 있으면
    프로덕션 규칙을 느슨하게 바꿔도 아무도 실패하지 않는다.

    [round17 #S17-04] `ExistingFidRead.reason()`의 over_enumerated 절에 `" — 스냅샷이
      자기모순이다"` 꼬리를 되살리면 'over_enumerated' 행이 **한 문장 대시 둘**로 실패한다.
    [round15 N11] `reason()` 끝에 마침표를 되살리면 조립부의 `. `와 겹쳐 `..`로 실패한다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    port = None if port_kwargs is None else _R15RawPort(**port_kwargs)
    plan = _plan_with(port)
    assert plan.ok is False
    reason = plan.rejection.reason
    assert sentence_shape_violation(reason) is None, (axis, reason)


def test_the_precheck_reason_shape_gate_is_not_vacuous():
    """비공허성 — 대시 둘을 심은 문자열에서 같은 판정자가 실제로 잡는다.

    심는 대상은 round17 S17-04가 실제로 낸 문자열 그대로다(감사 실증 문구).
    """
    from server.vwx.patchplan import sentence_shape_violation

    planted = (
        "기존 FID 사전검사가 불완전하다 — 열거된 슬롯 2개가 선언 총계 1개보다 많다 — "
        "스냅샷이 자기모순이다. 부분 관측으로 빈 FID를 단정하면 이미 쓰이는 번호를 배정하게 된다."
    )
    assert sentence_shape_violation(planted) is not None
    assert sentence_shape_violation(_plan_with(None).rejection.reason) is None


# ==========================================================================
# --- round18 FID 수치축 바닥 게이트 · 전 축 레지스트리 (FidFloorGate) ---
#
# 실증(아래 종단 테스트가 그대로 재현한다): `fid_range={'start': -10, 'end': -8}`이
# `_parse_fid_range`의 `end < start` 검사를 그대로 통과해 `ok=True` · 배정 `[-10,-9,-8]` ·
# 제외 0건 · `delivered=true`가 되고, 전달물에 `fid = "-10"`인 `AddFixtures` 호출이 실렸다.
# 게다가 **같은 payload가 `fid_safety.conflict_precheck.performed=true`로 "검사했고
# 깨끗하다"고 보고했다** — 음수 FID는 콘솔에서 읽은 `existing_fids`와 절대 충돌하지 않아
# 충돌검사가 구조적으로 무력한데도 그렇다. 결함의 절반은 값이고 절반은 그 거짓 보고다.
#
# round17이 좌표 양축(`universe`·`address`)에 세운 `_MINIMUM_ADDRESS_INDEX` 게이트의
# **형제 축**이며, 그 근거(PRESERVE `server/prechk/patch.py:121-123` "The console's own
# numbering starts at one")가 FID에도 그대로 성립한다.
#
# **상한은 두지 않는다** — 좌표 축과 같은 판정이고, 그 판정 자체를
# `test_r18_no_fid_ceiling_is_fabricated`가 고정한다(다음 라운드가 근거 없이 넣지 못하게).
# ==========================================================================

_R18_MIN_FID_LITERAL = 1  #: 프로덕션 상수를 참조하지 않는 **독립 리터럴**.
_R18_HUGE_FID = 10**18  #: 상한 날조 감지용 — 어떤 근거 있는 천장보다도 크다.


def _r18_parse(start, end):
    from server.vwx.patchplan import _parse_fid_range

    return _parse_fid_range({"start": start, "end": end})


#: (라벨, start, end, 기대 결함 갈래) — `None`이면 **유효**하다.
#: 갈래는 셋뿐이다: `form`(정수가 아니다) · `floor`(콘솔 최소 FID 미만) · `order`(end<start).
#: 갈래를 값이 아니라 **사유 문장**으로 가르는 이유: 축을 하나 지워도 "거부됨"이라는
#: 결과는 그대로라 통과/거부만 재는 대조군은 축 삭제를 잡지 못한다.
_R18_FID_RANGE_ROWS: tuple[tuple[str, object, object, str | None], ...] = (
    ("minus_ten", -10, -8, "floor"),
    ("minus_one", -1, -1, "floor"),
    ("zero_both", 0, 0, "floor"),
    ("zero_start_positive_end", 0, 2, "floor"),
    ("start_ok_end_below", 5, -1, "floor"),
    ("floor_exact", 1, 1, None),
    ("floor_plus_one", 1, 2, None),
    ("two_three", 2, 3, None),
    ("live_range", 501, 503, None),
    ("huge", _R18_HUGE_FID, _R18_HUGE_FID + 2, "no ceiling"),
    ("inverted", 5, 1, "order"),
    ("bool_true", True, True, "form"),
    ("bool_false", False, False, "form"),
    ("string_start", "1", 3, "form"),
    ("none_end", 1, None, "form"),
)

#: 표에서 파생하지 않은 **독립** 커버리지 요구 — 바닥 앞뒤·순서·형식·상한.
#: `True == 1` · `False == 0`이라 값만으로 된 집합은 bool 행을 정수 행에 삼켜버린다.
#: 그러면 bool 행을 지워도 이 대조군이 통과한다 — 그래서 **형 이름을 함께** 넣는다.
_R18_REQUIRED_RANGE_PROBES = frozenset(
    {
        ("int", _R18_MIN_FID_LITERAL - 11, "int", _R18_MIN_FID_LITERAL - 9),
        ("int", _R18_MIN_FID_LITERAL - 2, "int", _R18_MIN_FID_LITERAL - 2),
        ("int", _R18_MIN_FID_LITERAL - 1, "int", _R18_MIN_FID_LITERAL - 1),
        ("int", _R18_MIN_FID_LITERAL - 1, "int", _R18_MIN_FID_LITERAL + 1),
        ("int", _R18_MIN_FID_LITERAL + 4, "int", _R18_MIN_FID_LITERAL - 2),
        ("int", _R18_MIN_FID_LITERAL, "int", _R18_MIN_FID_LITERAL),
        ("int", _R18_MIN_FID_LITERAL, "int", _R18_MIN_FID_LITERAL + 1),
        ("int", _R18_MIN_FID_LITERAL + 1, "int", _R18_MIN_FID_LITERAL + 2),
        ("int", 501, "int", 503),
        ("int", _R18_HUGE_FID, "int", _R18_HUGE_FID + 2),
        ("int", 5, "int", 1),
        ("bool", True, "bool", True),
        ("bool", False, "bool", False),
        ("str", "1", "int", 3),
        ("int", 1, "NoneType", None),
    }
)


def test_r18_fid_range_boundary_table_covers_exactly_the_required_probes():
    """[round18 표 전수] 행을 하나라도 지우거나 중복시키면 실패한다.

    통과·거부 두 결론과 세 결함 갈래가 **모두** 표에 있어야 한다 — 한쪽만 남기면
    게이트가 공허해진다(round18 minor `_R17_CONTAINMENT_FAMILY` 자기충족 표의 교훈).
    """
    probes = tuple((row[1], row[2]) for row in _R18_FID_RANGE_ROWS)
    assert len(probes) == 15, "행수 리터럴 — 행 삭제/추가 감지"
    # `True == 1` · `False == 0`이라 set 비교가 bool 행을 삼킨다 — 형까지 함께 센다.
    typed = {(type(start).__name__, start, type(end).__name__, end) for start, end in probes}
    assert len(typed) == len(probes), "같은 (형, 값) 쌍이 두 번 들어갔다"
    required = _R18_REQUIRED_RANGE_PROBES
    assert typed == required
    labels = [row[0] for row in _R18_FID_RANGE_ROWS]
    assert len(labels) == len(set(labels))
    assert {row[3] for row in _R18_FID_RANGE_ROWS} == {None, "floor", "order", "form", "no ceiling"}


@pytest.mark.parametrize(
    ("label", "start", "end", "defect_kind"),
    _R18_FID_RANGE_ROWS,
    ids=[row[0] for row in _R18_FID_RANGE_ROWS],
)
def test_r18_parse_fid_range_classifies_every_boundary_row(label, start, end, defect_kind):
    """[round18 R18-A 경계 전수] 각 행이 **거부되는지 통과하는지 + 그때 어느 사유인지**.

    죽이는 뮤테이션:
      · 바닥 게이트 삭제 → `minus_ten`·`zero_both`·`zero_start_positive_end`가 통과해 실패.
      · 바닥 `<`를 `<=`로 → `floor_exact`(1,1) 행이 거부되어 실패.
      · 기준값 `_MINIMUM_FID` 1→2 → 같은 `floor_exact` 행이 실패.
      · **start 축만** 검사(`start < _MINIMUM_FID`만) → `start_ok_end_below`(5,-1)가
        `floor`가 아니라 `order` 사유로 거부되어 실패.
      · **end 축만** 검사(`end < _MINIMUM_FID`만) → `zero_start_positive_end`(0,2)가
        통과해 실패.
      · 바닥 검사를 순서 검사 **뒤로** 옮김 → `start_ok_end_below`가 `order`로 바뀌어 실패.
      · `end < start`를 `<=`로 → 표에 (1,1)·(501,503) 같은 유효 행이 있어 실패.
      · 근거 없는 상한 날조 → `huge` 행이 거부되어 실패.
    """
    parse = _r18_parse(start, end)
    if defect_kind in (None, "no ceiling"):
        assert parse.parsed is not None, f"{label}: 통과해야 하는 입력이 거부됐다"
        assert (parse.parsed.start, parse.parsed.end) == (start, end), "값을 고쳐 통과시켰다"
        assert parse.defect == ""
        return

    assert parse.parsed is None, f"{label}: 거부돼야 하는 입력이 통과했다"
    assert parse.defect, "거부는 사유 없이 나갈 수 없다"
    if defect_kind == "floor":
        assert "콘솔 최소 FID" in parse.defect
        assert f"start={start}" in parse.defect and f"end={end}" in parse.defect
    elif defect_kind == "order":
        assert "end는 start보다 작을 수 없다" in parse.defect
        assert "콘솔 최소 FID" not in parse.defect, "순서 결함을 바닥 사유로 보고했다"
    else:
        assert "정수 start와 end를 포함해야 한다" in parse.defect


def test_r18_fid_range_parse_is_exactly_one_of_value_or_defect():
    """[round18 불변식] `parsed`가 있음 ⇔ `defect`가 비어 있음. 표 전 행에서 확인한다.

    이 단정이 없으면 "값도 있고 사유도 있는" 상태나 "둘 다 없는" 상태가 조용히 생겨
    호출부가 사유 없는 거부를 내보낼 수 있다(빈 문자열 `reason`).
    """
    from server.vwx.patchplan import _parse_fid_range

    seen = set()
    for _label, start, end, _kind in _R18_FID_RANGE_ROWS:
        parse = _r18_parse(start, end)
        assert (parse.parsed is None) == bool(parse.defect)
        seen.add(parse.parsed is None)
    assert seen == {True, False}, "표에 통과·거부가 모두 있어야 이 단정이 비공허하다"
    # `fid_range=None`(미제공)은 값도 사유도 없는 **유일한** 예외 — 상위가 별도 코드로 거부한다.
    absent = _parse_fid_range(None)
    assert absent.parsed is None and absent.defect == ""


def test_r18_minimum_fid_matches_the_preserve_path():
    """[round18 R18-A] `_MINIMUM_FID`를 1에서 옮기면 실패한다.

    근거는 좌표 축과 **같은 원전**이다: PRESERVE 경로 `server/prechk/patch.py:121-123`의
    `normalize_address` 독스트링 — "Both halves must be at least ``_MINIMUM_INDEX``.
    The console's own numbering starts at one, so ``0.0`` · ``1.0`` · ``0.1`` name no
    addressable channel". 콘솔 번호 체계가 1에서 시작한다는 그 사실은 좌표에만 걸리는
    성질이 아니다. 세 값이 어긋나면 여기서 잡힌다 — 비공개 이름을 계층 넘어 import하지
    않으면서 단일 진실을 유지하는 방법이다(round17 선례).
    """
    from server.prechk.patch import _MINIMUM_INDEX
    from server.vwx.patchplan import _MINIMUM_ADDRESS_INDEX, _MINIMUM_FID

    assert _MINIMUM_FID == _R18_MIN_FID_LITERAL
    assert _MINIMUM_FID == _MINIMUM_INDEX
    assert _MINIMUM_FID == _MINIMUM_ADDRESS_INDEX


def test_r18_no_fid_ceiling_is_fabricated():
    """[round18 R18-A 부작용 방지] 바닥을 넣으면서 **근거 없는 상한**을 함께 넣으면 실패한다.

    **근거를 여기 남긴다 — 근거 없이 남으면 다음 사람이 "왜 상한이 없지"라며 넣는다.**

    조사 결과 이 저장소에 FID 상한의 근거는 **없다**:
      · 룰북 `server/rulebook/assets/v2.4.2/30_plugin_patterns.md:35·46`은 `fid`를
        "(string)"으로만 규정하고 예제는 `for fid = 2, 10`이다 — 최대값 언급이 없다.
      · `console/lua/PROTOCOL.md`에도 FID 최대값 규정이 없다.
      · 애초에 이 SPEC은 **콘솔의 기존 FID를 읽는 것 자체**가 최대 난제였고
        (`research.md` §3 · `spec.md` §B.2), 수용 상한은 실측된 적이 없다.
    미실측 위에 천장을 지어내면 PRESERVE 경로가 좌표에서 내린 판정과 정확히 같은 이유로
    틀린다 — "inventing a ceiling would reject addresses the console accepts"
    (`server/prechk/patch.py:128-133`).

    그러므로 **거대값은 그대로 통과한다.** 상한을 넣으면 이 테스트가 실패한다.
    """
    from server.vwx.patchplan import FIDRange, _assign_fids

    parse = _r18_parse(_R18_HUGE_FID, _R18_HUGE_FID + 2)
    assert parse.parsed == FIDRange(start=_R18_HUGE_FID, end=_R18_HUGE_FID + 2)

    planned, exclusions = _assign_fids(
        (_r18_candidate("a"),),
        FIDRange(start=_R18_HUGE_FID, end=_R18_HUGE_FID),
        existing_fids=frozenset(),
        fid_range_visually_confirmed_empty=None,
    )
    assert exclusions == ()
    assert [target.assigned_fid for target in planned] == [_R18_HUGE_FID]

    # 근거: 닫힌 어휘에 "FID 상한" 을 뜻하는 코드가 **아예 없다**(형제 표면 전수 확인).
    from server.vwx.verdicts import AUTOPATCH_CLOSED_VOCABULARIES

    every_code = {code for codes in AUTOPATCH_CLOSED_VOCABULARIES.values() for code in codes}
    assert every_code
    assert not [
        code
        for code in every_code
        if "fid" in code and ("above" in code or "maximum" in code or "ceiling" in code)
    ]


def _r18_candidate(candidate_id: str, *, universe: int = 1, address: int = 1):
    from server.vwx.patchplan import PatchCandidate

    return PatchCandidate(
        id=candidate_id,
        unit_number=None,
        instrument_type="Robe MegaPointe",
        universe=universe,
        address=address,
        detail="",
        address_basis=ADDRESS_BASIS_DIRECT,
        source_index=0,
    )


#: (라벨, FIDRange 인자, 기대 배제 코드 또는 None) — `_assign_fids`의 **두 번째 진입점**.
#: `FIDRange`는 공개 dataclass라 `_parse_fid_range`를 거치지 않고 조립할 수 있다.
#: round17의 교훈: 게이트를 한 함수 경계에만 두면 형제 진입점이 그대로 새어 나간다.
_R18_ASSIGN_DIRECT_ROWS = (
    ("negative_range", (-10, -8), "FID_BELOW_MINIMUM"),
    ("zero_range", (0, 0), "FID_BELOW_MINIMUM"),
    ("straddling_zero", (0, 1), "FID_BELOW_MINIMUM"),
    ("floor_exact", (1, 1), None),
    ("live_range", (501, 503), None),
)


def test_r18_assign_direct_row_table_is_complete():
    """[round18 표 전수] 행 삭제 감지 — 배제·통과 두 결론이 모두 남아 있어야 한다."""
    labels = [row[0] for row in _R18_ASSIGN_DIRECT_ROWS]
    assert len(labels) == len(set(labels)) == 5
    assert {row[2] for row in _R18_ASSIGN_DIRECT_ROWS} == {None, "FID_BELOW_MINIMUM"}
    assert {row[1] for row in _R18_ASSIGN_DIRECT_ROWS} == {
        (-10, -8),
        (0, 0),
        (0, 1),
        (1, 1),
        (501, 503),
    }


@pytest.mark.parametrize(
    ("label", "bounds", "expected_code"),
    _R18_ASSIGN_DIRECT_ROWS,
    ids=[row[0] for row in _R18_ASSIGN_DIRECT_ROWS],
)
def test_r18_assign_fids_excludes_individual_values_below_the_minimum(label, bounds, expected_code):
    """[round18 R18-A 개별값 축] `_assign_fids`의 개별값 검사를 지우면 실패한다.

    `FIDRange`를 직접 조립한 호출자는 `_parse_fid_range`의 바닥 게이트를 지나지 않는다.
    그 값이 `with_fid`를 타면 `PatchCandidate.assigned_fid`가 되고, `apply.py`가 그것을
    `LuaPatchEntry.fid`로 넘겨 `fid = "-10"`인 전달물이 만들어진다.

    죽이는 뮤테이션:
      · `_assign_fids`의 `proposed_fid < _MINIMUM_FID` 갈래 삭제 → 세 배제 행이 통과해 실패.
      · `<`를 `<=`로 → `floor_exact` 행이 배제되어 실패.
      · 개별값 대신 `fid_range.start`만 검사 → `straddling_zero`(0,1)에서 두 번째 값 1이
        배제되어 실패한다(배제는 첫 값만이어야 한다).
      · 배제 대신 값을 1로 끌어올려 통과 → `assigned_fid` 단정에서 실패(자동 보정 0건).
    """
    from server.vwx import verdicts
    from server.vwx.patchplan import FIDRange, _assign_fids

    start, end = bounds
    count = end - start + 1
    targets = tuple(_r18_candidate(f"c{i}", address=1 + i * 16) for i in range(count))
    planned, exclusions = _assign_fids(
        targets,
        FIDRange(start=start, end=end),
        existing_fids=frozenset(),
        fid_range_visually_confirmed_empty=None,
    )
    below = [value for value in range(start, end + 1) if value < _R18_MIN_FID_LITERAL]
    kept = [value for value in range(start, end + 1) if value >= _R18_MIN_FID_LITERAL]

    if expected_code is None:
        assert exclusions == (), label
    else:
        code = getattr(verdicts, expected_code)
        assert [x.code for x in exclusions] == [code] * len(below), label
        assert [x.proposed_fid for x in exclusions] == below
        for exclusion in exclusions:
            assert "콘솔 최소 FID" in exclusion.reason
            assert exclusion.to_dict()["label"], "닫힌 어휘에 라벨이 등재되어야 한다"
    # 자동 보정 0건 — 살아남은 항목의 FID는 **범위 값 그대로**여야 한다.
    assert [target.assigned_fid for target in planned] == kept


def test_r18_below_minimum_fid_is_not_reported_as_already_in_use():
    """[round18 R18-A] 성립하지 않는 번호를 "이미 사용 중"으로 보고하면 실패한다.

    바닥 검사를 기존 FID 대조 **뒤로** 옮겨도 음수는 `existing_fids`와 만나지 않아
    결과가 같아 보인다 — 그래서 0을 기존 FID에 넣은 이 행으로 순서를 고정한다.
    조작자는 배제 사유를 보고 무엇을 고칠지 정한다: 잘못된 사유는 잘못된 수정을 부른다.
    """
    from server.vwx.patchplan import FIDRange, _assign_fids
    from server.vwx.verdicts import FID_ALREADY_IN_USE, FID_BELOW_MINIMUM

    _planned, exclusions = _assign_fids(
        (_r18_candidate("a"),),
        FIDRange(start=0, end=0),
        existing_fids=frozenset({0}),
        fid_range_visually_confirmed_empty=None,
    )
    assert [x.code for x in exclusions] == [FID_BELOW_MINIMUM]
    assert FID_ALREADY_IN_USE not in {x.code for x in exclusions}


# --------------------------------------------------------------------------
# payload 정직성 — 거부된 호출은 "검사했다"를 주장하지 않는다
# --------------------------------------------------------------------------

#: (라벨, fid_range, 거부되는가) — 거부 행에서 `fid_safety`가 payload에 **없어야** 한다.
_R18_PAYLOAD_HONESTY_ROWS = (
    ("below_minimum", {"start": -10, "end": -8}, True),
    ("zero", {"start": 0, "end": 2}, True),
    ("inverted", {"start": 5, "end": 1}, True),
    ("valid", {"start": 501, "end": 503}, False),
)


def test_r18_payload_honesty_row_table_is_complete():
    """[round18 표 전수] 행 삭제 감지 — 거부·통과 두 결론이 모두 있어야 한다."""
    labels = [row[0] for row in _R18_PAYLOAD_HONESTY_ROWS]
    assert len(labels) == len(set(labels)) == 4
    assert {row[2] for row in _R18_PAYLOAD_HONESTY_ROWS} == {True, False}
    assert sum(1 for row in _R18_PAYLOAD_HONESTY_ROWS if row[2]) == 3


@pytest.mark.parametrize(
    ("label", "fid_range", "rejected"),
    _R18_PAYLOAD_HONESTY_ROWS,
    ids=[row[0] for row in _R18_PAYLOAD_HONESTY_ROWS],
)
def test_r18_a_rejected_fid_range_never_claims_a_conflict_precheck(label, fid_range, rejected):
    """[round18 R18-A 나머지 절반] 거부된 호출의 payload가 "검사했고 깨끗하다"고
    주장하면 실패한다.

    round18 실측: `{'start': -10, 'end': -8}`이 `ok=True`로 통과하면서
    `fid_safety.conflict_precheck.performed=true` · `existing_fids: []`를 함께 실었다.
    음수 대역은 콘솔 FID와 **절대** 충돌하지 않으므로 그 "깨끗함"은 검사의 결과가 아니라
    검사가 무의미했다는 뜻인데, payload는 둘을 구별해 주지 않았다.

    거부 갈래를 `_fid_safety_payload` **뒤로** 옮기면 이 테스트가 실패한다 —
    거부된 호출에는 실릴 `fid_safety`가 애초에 없어야 한다.
    """
    payload_report = report_payload([rr(0), rr(1), rr(2)])
    ids = candidate_ids(payload_report)
    plan = build_patch_plan(
        payload_report,
        selected=ids,
        fid_range=fid_range,
        assumption_71=ASSUMPTION_71_GO,
        fid_property_port=FidRigPort(()),
        assignment_requested=True,
    )
    payload = plan.to_dict()
    if rejected:
        assert plan.ok is False and plan.status == "rejected", label
        assert "fid_safety" not in payload, "거부된 호출이 사전검사 payload를 실었다"
        assert payload["rejection"]["code"] == "invalid_fid_range"
        assert payload["rejection"]["reason"], "사유 없는 거부"
        assert [target["fid"] for target in payload["targets"]] == [None, None, None]
    else:
        assert plan.ok is True, label
        assert payload["fid_safety"]["conflict_precheck"]["performed"] is True
        assert [target["fid"] for target in payload["targets"]] == [501, 502, 503]


# --------------------------------------------------------------------------
# 도달성 감지기 — 게이트를 지우면 `fid = "-10"`이 전달물 Lua에 다시 나온다
# --------------------------------------------------------------------------


def _r18_deliverable(fid_range, *, direct_range=None):
    """리포트 → 계획 → 주소 계획 → **전달물 Lua**까지 프로덕션 함수만 밟는다.

    `direct_range`가 주어지면 `build_patch_plan`을 우회해 `_assign_fids`를 직접 부른다 —
    `FIDRange`를 조립하는 형제 진입점이 전달물에 닿는 경로를 같은 파이프라인으로 잰다.
    """
    from server.vwx.apply import build_patch_handoff
    from server.vwx.patchplan import FIDRange, _assign_fids, plan_addresses
    from server.vwx.typemap import LibraryMode, LibraryType, TypeRequest, TypeResolution
    from server.vwx.verdicts import TYPE_RESOLVED

    # 주소는 폭 4가 겹치지 않게 벌려 둔다 — 겹치면 `plan_addresses`가 뒤 항목을
    # `address_overlap_in_plan`으로 빼서 전달물이 한 줄로 줄고, 비공허성 단정이
    # "FID 게이트 때문에" 비었는지 "주소가 겹쳐서" 비었는지 구별할 수 없게 된다.
    payload_report = report_payload([rr(0, address=1), rr(1, address=17), rr(2, address=33)])
    ids = candidate_ids(payload_report)
    plan = build_patch_plan(
        payload_report,
        selected=ids,
        fid_range=fid_range,
        assumption_71=ASSUMPTION_71_GO,
        fid_property_port=FidRigPort(()),
        assignment_requested=True,
    )
    targets = plan.targets
    if direct_range is not None:
        targets, _exclusions = _assign_fids(
            plan.targets,
            FIDRange(*direct_range),
            existing_fids=frozenset(),
            fid_range_visually_confirmed_empty=None,
        )
    address_plan = plan_addresses(
        targets, footprints={target.id: 4 for target in targets}, occupied={}
    )
    resolutions = tuple(
        TypeResolution(
            request=TypeRequest(candidate_id=target.id, instrument_type=target.instrument_type),
            status=TYPE_RESOLVED,
            reason="",
            console_type=LibraryType(index=1, name="Robe MegaPointe"),
            console_mode=LibraryMode(index=1, name="Mode 1"),
        )
        for target in targets
    )
    handoff = build_patch_handoff(
        targets,
        address_plan=address_plan,
        resolutions=resolutions,
        names={target.id: f"MP_{index}" for index, target in enumerate(targets, start=1)},
        dry_run=False,
    )
    return plan, handoff


#: (라벨, 상위 호출 fid_range, `_assign_fids` 직결 범위, 전달물에 나오면 안 되는 토큰)
_R18_REACHABILITY_CASES = (
    ("plan_entry_negative", {"start": -10, "end": -8}, None, 'fid = "-10"'),
    ("plan_entry_zero", {"start": 0, "end": 2}, None, 'fid = "0"'),
    ("assign_entry_negative", {"start": 501, "end": 503}, (-10, -8), 'fid = "-10"'),
)


def test_r18_reachability_case_table_is_complete():
    """[round18 표 전수] 도달성 사례 행을 지우면 실패한다.

    두 **서로 다른 진입점**(상위 `build_patch_plan` · `_assign_fids` 직결)이 모두 있어야
    한다 — 한쪽만 남기면 형제 진입점이 다시 무방비가 된다.
    """
    labels = [case[0] for case in _R18_REACHABILITY_CASES]
    assert len(labels) == len(set(labels)) == 3
    assert {case[2] is None for case in _R18_REACHABILITY_CASES} == {True, False}
    assert {case[3] for case in _R18_REACHABILITY_CASES} == {'fid = "-10"', 'fid = "0"'}


@pytest.mark.parametrize(
    ("label", "fid_range", "direct_range", "forbidden_token"),
    _R18_REACHABILITY_CASES,
    ids=[case[0] for case in _R18_REACHABILITY_CASES],
)
def test_r18_below_minimum_fid_never_reaches_the_lua_deliverable(
    label, fid_range, direct_range, forbidden_token
):
    """[round18 R18-A 도달성 감지기] 사람이 콘솔에 임포트하는 **산출물**이 검사
    대상이다 — 중간 자료구조가 아니라.

    **실측(정확히 재현한 것만 적는다)**: `_parse_fid_range`의 바닥 게이트와
    `_assign_fids`의 개별값 게이트를 **둘 다** 지우면 이 파이프라인이 다시
    `AddFixtures({ … fid = "-10" … })` · `fid = "0"`을 렌더한다(세 행 전부 재현 확인).
    한 층만 지우면 남은 층이 잡으므로 Lua는 비고, 그때는 아래 `plan.ok`·`entries`
    단정이 실패한다 — 즉 **어느 한 층만 지워도 이 테스트는 실패한다.**
    두 층을 둔 이유가 그것이다: `_parse_fid_range`는 사용자 입력을 거부하고,
    `_assign_fids`는 `FIDRange`를 직접 조립하는 형제 진입점을 막는다.
    """
    plan, handoff = _r18_deliverable(fid_range, direct_range=direct_range)

    lua = handoff.lua_source or ""
    assert forbidden_token not in lua, label
    assert "AddFixtures(" not in lua, "배정된 항목이 없으므로 전달물에 호출이 없어야 한다"
    assert handoff.entries == ()
    if direct_range is None:
        assert plan.ok is False and plan.status == "rejected"


def test_r18_reachability_detector_is_not_vacuous_on_a_valid_range():
    """[round18 R18-A 비공허성] 같은 파이프라인에 정상 범위(501~503)를 넣으면
    Lua에 `fid = "501"`이 **실제로 나온다** — 위 테스트가 "언제나 비어 있다"를 확인하는
    공허한 검사가 아님을 같은 경로로 증명한다."""
    plan, handoff = _r18_deliverable({"start": 501, "end": 503})

    assert plan.ok is True
    lua = handoff.lua_source or ""
    assert 'fid = "501"' in lua
    assert 'fid = "502"' in lua and 'fid = "503"' in lua
    assert [entry.fid for entry in handoff.entries] == [501, 502, 503]


# --------------------------------------------------------------------------
# 전달물에 닿는 **정수 축 전수 레지스트리**
#
# 바닥만 또 막고 끝내면 다음 라운드가 형제 축에서 같은 것을 찾는다. 그래서 축을 손으로
# 세지 않고 **전달물 자료형의 int 필드를 AST로 뽑아** 표와 1:1로 맞춘다 — 새 정수 축을
# 추가하면 등재 없이는 통과하지 못한다.
# --------------------------------------------------------------------------

_R18_DELIVERABLE_INT_SOURCES = (
    ("luagen.py", "LuaPatchEntry"),
    ("apply.py", "HandoffEntry"),
)


def _r18_deliverable_int_fields() -> tuple[tuple[str, str], ...]:
    """전달물 자료형의 `int` 필드 전수 — (자료형, 필드).

    **읽는 것은 두 파일뿐이다**: `luagen.py`의 `LuaPatchEntry`와 `apply.py`의
    `HandoffEntry`. 그 둘이 사람 손에 가는 값의 **유일한** 통로이기 때문이다 —
    Lua 본문에 닿는 길은 `LuaPatchEntry`의 6필드뿐이고(`apply.py` 모듈 독스트링),
    payload에 실리는 항목은 `HandoffEntry.to_dict()`다. `server/vwx`의 나머지
    모듈이 다루는 정수는 이 둘을 거치지 않으면 조작자에게 도달하지 않는다.
    """
    found: list[tuple[str, str]] = []
    for module_name, class_name in _R18_DELIVERABLE_INT_SOURCES:
        tree = ast.parse(Path("server/vwx", module_name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    annotation = ast.unparse(item.annotation)
                    if annotation == "int" or annotation.startswith("int "):
                        found.append((class_name, item.target.id))
    return tuple(sorted(found))


#: (자료형, 필드, 바닥 게이트 자리, 상한) — 상한은 전 축이 **무상한**이고 그것이 판정이다.
#: 각 행은 아래에서 **실제 프로덕션 호출로** 바닥 거부·상한 통과를 함께 확인받는다.
_R18_INT_AXIS_REGISTRY: tuple[tuple[str, str, str, None], ...] = (
    ("HandoffEntry", "address", "plan_addresses · _MINIMUM_ADDRESS_INDEX", None),
    ("HandoffEntry", "fid", "_parse_fid_range · _assign_fids · _MINIMUM_FID", None),
    ("HandoffEntry", "footprint", "plan_addresses · footprint <= 0", None),
    ("HandoffEntry", "universe", "plan_addresses · _MINIMUM_ADDRESS_INDEX", None),
    ("LuaPatchEntry", "address", "plan_addresses · _MINIMUM_ADDRESS_INDEX", None),
    ("LuaPatchEntry", "fid", "_parse_fid_range · _assign_fids · _MINIMUM_FID", None),
    ("LuaPatchEntry", "universe", "plan_addresses · _MINIMUM_ADDRESS_INDEX", None),
)


def test_r18_int_axis_registry_is_a_bijection_onto_the_deliverable_types():
    """[round18 형제 축 전수] 전달물 자료형에 `int` 필드를 더하거나 지우면 실패한다.

    round15~18이 여덟 라운드 연속 같은 기제로 실패했다 — 어떤 규율을 적용하고 형제
    표면에는 적용하지 않는다. 이 표는 "어느 정수가 사람 손에 가는가"를 **AST로** 세어
    손 열거의 누락 가능성을 없앤다.

    표에서 행을 지우면 실패하고, 프로덕션에 새 정수 축을 추가해도 실패한다 —
    그때 **의식적으로** 바닥·상한을 결정하고 등재해야 한다.
    """
    declared = tuple(sorted((cls, field) for cls, field, _gate, _ceiling in _R18_INT_AXIS_REGISTRY))
    assert declared == _r18_deliverable_int_fields()
    assert len(declared) == 7, "행수 리터럴 — 행 삭제/추가 감지"
    assert len(set(declared)) == len(declared)
    # 전 축의 상한 칸이 `None`(무상한)이다 — 하나라도 천장을 넣으면 근거를 함께 적어야 한다.
    assert {row[3] for row in _R18_INT_AXIS_REGISTRY} == {None}
    # 바닥 게이트 자리는 세 종류뿐이고, 셋 다 실재하는 프로덕션 이름을 가리킨다.
    gates = {row[2] for row in _R18_INT_AXIS_REGISTRY}
    assert len(gates) == 3
    source = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")
    for token in ("_MINIMUM_ADDRESS_INDEX", "_MINIMUM_FID", "footprint <= 0"):
        assert token in source, token


#: (축 이름, 바닥 미만 입력으로 배제되는가를 재는 호출, 거대값이 통과하는가를 재는 호출)
#: 레지스트리의 **행동 대조군** — 구조 단정만 두면 게이트를 지워도 표가 통과한다.
_R18_AXIS_BEHAVIOUR_ROWS = ("universe", "address", "footprint", "fid")


def test_r18_axis_behaviour_row_table_covers_every_registered_axis():
    """[round18 표 전수] 행동 대조군이 레지스트리의 **모든 축 이름**을 덮는다."""
    registered = {field for _cls, field, _gate, _ceiling in _R18_INT_AXIS_REGISTRY}
    assert set(_R18_AXIS_BEHAVIOUR_ROWS) == registered
    assert len(_R18_AXIS_BEHAVIOUR_ROWS) == len(set(_R18_AXIS_BEHAVIOUR_ROWS)) == 4


@pytest.mark.parametrize("axis", _R18_AXIS_BEHAVIOUR_ROWS)
def test_r18_every_deliverable_int_axis_has_a_floor_and_no_ceiling(axis):
    """[round18 형제 축 전수 · 행동] 네 축 각각에서 **바닥 미만은 배제되고 거대값은 통과**한다.

    어느 축의 바닥 게이트를 지워도 그 행이 실패한다. 어느 축에 근거 없는 천장을 넣어도
    그 행이 실패한다 — 여덟 라운드 연속 실패한 "형제 표면 누락"을 한 표에서 닫는다.
    """
    from server.vwx.patchplan import FIDRange, _assign_fids, plan_addresses

    if axis == "fid":
        _planned, low = _assign_fids(
            (_r18_candidate("a"),),
            FIDRange(start=0, end=0),
            existing_fids=frozenset(),
            fid_range_visually_confirmed_empty=None,
        )
        high_planned, high = _assign_fids(
            (_r18_candidate("a"),),
            FIDRange(start=_R18_HUGE_FID, end=_R18_HUGE_FID),
            existing_fids=frozenset(),
            fid_range_visually_confirmed_empty=None,
        )
        assert [x.code for x in low] == ["fid_below_minimum"]
        assert high == () and high_planned[0].assigned_fid == _R18_HUGE_FID
        return

    if axis == "footprint":
        low_plan = plan_addresses((_r18_candidate("a"),), footprints={"a": 0}, occupied={})
        high_plan = plan_addresses((_r18_candidate("a"),), footprints={"a": 10**6}, occupied={})
        assert [x.code for x in low_plan.exclusions] == ["footprint_unknown"]
        assert high_plan.exclusions == () and high_plan.entries[0].footprint == 10**6
        return

    below = {"universe": _r18_candidate("a", universe=0), "address": _r18_candidate("a", address=0)}
    above = {
        "universe": _r18_candidate("a", universe=_R18_HUGE_FID),
        "address": _r18_candidate("a", address=_R18_HUGE_FID),
    }
    low_plan = plan_addresses((below[axis],), footprints={"a": 4}, occupied={})
    high_plan = plan_addresses((above[axis],), footprints={"a": 4}, occupied={})
    assert [x.code for x in low_plan.exclusions] == ["address_below_minimum"]
    assert high_plan.exclusions == ()
    assert getattr(high_plan.entries[0], axis) == _R18_HUGE_FID


# --------------------------------------------------------------------------
# 축 독립성 — **표에 기대지 않는** 단독 대조군 3개
#
# 교차 실측(행삭제 × 프로덕션 뮤테이션)에서 두 사각지대가 나왔다: `_R18_FID_RANGE_ROWS`의
# `start_ok_end_below` 행을 지우면 **start 축만 검사**하는 뮤턴트가, `straddling_zero`
# 행을 지우면 **범위 시작값만 검사**하는 뮤턴트가 행동 대조군에서 SURVIVED였다.
# 표의 행삭제는 표 자신의 전단사가 잡지만, 그건 구조 게이트다. 아래 셋은 같은 축을
# **표 밖에서** 한 번 더 잰다 — 표 한 행에 걸린 유일 방어를 없앤다.
# --------------------------------------------------------------------------


def test_r18_the_end_axis_of_the_floor_gate_is_checked_independently():
    """[round18 R18-A] 바닥 검사를 `start < _MINIMUM_FID`로 좁히면 실패한다.

    `start=5`는 바닥 위이고 `end=-1`만 아래다. 순서 검사(`end < start`)가 이 입력을
    흡수해 **거부 자체는 유지되므로**, 통과/거부만 재는 단정으로는 이 축 축소를 잡을 수
    없다 — 어느 **사유**가 나오는지까지 재야 잡힌다.
    """
    parse = _r18_parse(5, -1)
    assert parse.parsed is None
    assert "콘솔 최소 FID" in parse.defect, "end 축이 검사되지 않아 순서 사유로 떨어졌다"
    assert "end=-1" in parse.defect


def test_r18_the_start_axis_of_the_floor_gate_is_checked_independently():
    """[round18 R18-A] 바닥 검사를 `end < _MINIMUM_FID`로 좁히면 실패한다.

    `start=0`은 바닥 아래이고 `end=2`는 위다. 순서도 정상이라 축소하면 **그대로 통과**해
    `fid = "0"`이 전달물에 실린다.
    """
    parse = _r18_parse(0, 2)
    assert parse.parsed is None, "start 축이 검사되지 않아 바닥 미만 범위가 통과했다"
    assert "콘솔 최소 FID" in parse.defect
    assert "start=0" in parse.defect


def test_r18_the_individual_value_check_is_per_value_not_per_range():
    """[round18 R18-A] `_assign_fids`의 개별값 검사를 `fid_range.start` 검사로 바꾸면 실패한다.

    범위 `(0, 1)`은 바닥을 **걸친다**: 첫 값 0은 배제되고 둘째 값 1은 배정돼야 한다.
    범위 시작값만 보면 두 대상 모두 배제되고, 범위 전체를 보면 1까지 잃는다 —
    어느 쪽이든 여기서 잡힌다. 반대로 검사를 지우면 0이 배정돼 역시 잡힌다.
    """
    from server.vwx.patchplan import FIDRange, _assign_fids
    from server.vwx.verdicts import FID_BELOW_MINIMUM

    planned, exclusions = _assign_fids(
        (_r18_candidate("a"), _r18_candidate("b", address=17)),
        FIDRange(start=0, end=1),
        existing_fids=frozenset(),
        fid_range_visually_confirmed_empty=None,
    )
    assert [(x.candidate_id, x.code, x.proposed_fid) for x in exclusions] == [
        ("a", FID_BELOW_MINIMUM, 0)
    ]
    assert [(t.id, t.assigned_fid) for t in planned] == [("b", 1)]


# --------------------------------------------------------------------------
# --- round19 절단 복구 스윕 · 미판독 고지 복원 · 라벨 축 (TruncationSweep) ---
#
# 실물 콘솔은 `Patch/Stages/1/Fixtures`를 **19대에서 절단**한다(1900바이트 예산,
# 페이징 없음). round18까지 `_existing_fids_from_console`은 단일 `query_state`만 했고
# 형제 리더 PRESERVE `server/prechk/inventory.py:391-417`의 `1..childCount` 유계
# 스윕이 없었다. 그래서 39대 쇼파일에서 열거는 영원히 총계에 못 미치고
# `unseen>=15`가 상시 성립 → GO 분기가 **한 대도** 배정하지 못한다(M8 대상 0건).
# 아래 대조군은 ① 스윕이 그 절단을 회수한다 ② 회수하지 못한 절단은 여전히 거부한다
# ③ 스윕이 완전성을 **승격시키지 않는다** ④ 스윕 전제·경계·인덱스 도메인을 재는 것이다.
# --------------------------------------------------------------------------


class _R19SweepPort:
    """선언 총계는 진짜, 열거는 앞부분만 — 실물 절단을 재현하는 포트.

    `present`에 있는 슬롯만 FID를 내놓는다. 그 밖의 슬롯은 `hidden_mode`에 따라
    부재(`ok=false`) · 무응답(예외) · 포인터 문자열(`ok=true`인데 값이 쓰레기,
    형제 리더 독스트링 3번의 실측 형태) 중 하나로 답한다.
    """

    def __init__(self, *, total, rows, present=None, hidden_mode="absent"):
        self.total = total
        self.rows = list(rows)
        self.present = dict(present or {})
        self.hidden_mode = hidden_mode
        self.state_calls: list[str] = []
        self.property_calls: list[int] = []

    @property
    def probe_slots(self) -> list[int]:
        """스윕이 찔러 본 슬롯 — 열거된 슬롯의 정규 판독과 구별한다."""
        return [slot for slot in self.property_calls if slot not in self.rows]

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        return {
            "ok": True,
            "path": path,
            "node": {"name": "Fixtures", "class": "Fixtures", "childCount": self.total},
            "children": [{"i": slot, "name": f"f{slot}"} for slot in self.rows],
            "truncated": len(self.rows) < self.total,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        slot = int(path.rsplit("/", 1)[1])
        self.property_calls.append(slot)
        if slot in self.present:
            return {
                "ok": True,
                "path": path,
                "property": property_name,
                "value": str(self.present[slot]),
            }
        if self.hidden_mode == "raise":
            raise TimeoutError(f"no answer for {path}")
        if self.hidden_mode == "pointer":
            # `safe_property`가 `tostring(handle[name])`로 떨어질 때 실측된 형태.
            return {
                "ok": True,
                "path": path,
                "property": property_name,
                "value": "function: 0x105b0f048",
            }
        return {"ok": False, "path": path, "property": property_name, "error": "no such object"}


def _r19_plan(port, *, fid_range, count=1, assumption_71=ASSUMPTION_71_GO, confirmed=None):
    """리포트 → 계획까지 **프로덕션 함수만** 밟는다."""
    payload_report = report_payload([rr(index, address=1 + 16 * index) for index in range(count)])
    ids = candidate_ids(payload_report)
    return build_patch_plan(
        payload_report,
        selected=ids,
        fid_range=fid_range,
        assumption_71=assumption_71,
        fid_range_visually_confirmed_empty=confirmed,
        fid_property_port=port,
        assignment_requested=True,
    )


def test_r19_a_truncated_enumeration_is_recovered_by_the_sweep():
    """[round19 ①] 절단된 열거를 스윕이 회수해 `complete=True`에 도달한다 — 그리고
    **숨어 있던 FID를 배정하지 않는다**.

    선언 3대 중 1대만 열거되고 숨은 슬롯 2·3의 FID가 102·103이다. 대상 4개에 범위
    101-110을 주면, **스윕이 회수한 102·103까지 이미 쓰이는 번호로 배제**되고 네 번째
    대상이 104를 받는다.

    스윕을 지우면 `unseen=2`로 배정 전체가 거부돼 `ok is True` 단정이 실패한다.
    스윕이 슬롯만 관측으로 올리고 FID 수집을 빠뜨리면(`read_slots.add`만 남기고
    `existing_fids.append`를 지우면) `complete=True`인데 102·103이 빈 번호로 보여
    **이미 쓰이는 번호가 배정**되고 배제 목록 단정이 실패한다.
    """
    from server.vwx.verdicts import FID_ALREADY_IN_USE as ALREADY

    port = _R19SweepPort(total=3, rows=[1], present={1: 101, 2: 102, 3: 103})
    plan = _r19_plan(port, fid_range={"start": 101, "end": 110}, count=4)

    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read["child_count"] == 3
    assert read["enumerated_count"] == 1, "열거 계수에 스윕 결과가 섞였다"
    assert read["recovered_count"] == 2
    assert read["recovery_boundary"] == 3
    assert read["unseen_count"] == 0
    assert read["complete"] is True
    assert plan.ok is True
    assert plan.fid_safety["conflict_precheck"]["existing_fids"] == [101, 102, 103]
    assert [(x.code, x.proposed_fid) for x in plan.target_exclusions] == [
        (ALREADY, 101),
        (ALREADY, 102),
        (ALREADY, 103),
    ]
    assert [target.assigned_fid for target in plan.targets] == [104]


def test_r19_an_unrecoverable_truncation_still_refuses():
    """[round19 ①] 대조의 대조 — 스윕이 회수하지 못하면 배정은 여전히 거부된다.

    같은 절단인데 숨은 슬롯이 값을 내놓지 않는다. 스윕이 회수 실패를 삼키고
    `complete`를 올리면(예: 프로브 결과와 무관하게 `read_slots.add(slot)`) 여기서 걸린다.
    """
    port = _R19SweepPort(total=3, rows=[1], present={1: 101})
    plan = _r19_plan(port, fid_range={"start": 101, "end": 110})

    read = plan.fid_safety["conflict_precheck"]["read"]
    assert port.probe_slots == [2, 3], "스윕이 돌지 않았다"
    assert read["recovered_count"] == 0
    assert read["unseen_count"] == 2
    assert read["complete"] is False
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [target.assigned_fid for target in plan.targets] == [None]


def test_r19_the_sweep_does_not_run_on_an_empty_enumeration():
    """[round19 ① 전제] 열거에 확립된 슬롯이 **하나도** 없으면 스윕하지 않는다.

    PRESERVE 원전(`server/prechk/inventory.py:393-400`)이 명시한 사고 그대로다:
    `copilot_responder.lua:434-447`은 `any_slot_known`이 거짓일 때만
    `children[wanted_slot]`을 돌려주므로, 빈 열거에서 슬롯 경로를 찌르면 responder가
    **열거 위치**로 답한다 — 그것을 기존 FID로 적재하면 엉뚱한 픽스처의 번호를
    "이미 쓰인다"고 믿거나, 더 나쁘게 빈 번호로 믿는다.

    `slots_established` 전제(`and read_slots`)를 지우면 프로브 2회가 나가고 숨은 슬롯이
    답을 주므로 `complete=True`로 배정까지 열린다 — 두 단정이 함께 실패한다.
    """
    port = _R19SweepPort(total=2, rows=[], present={1: 101, 2: 102})
    plan = _r19_plan(port, fid_range={"start": 501, "end": 510})

    assert port.probe_slots == [], "빈 열거에서 스윕이 돌았다 — 위치를 슬롯으로 오인한다"
    read = plan.fid_safety["conflict_precheck"]["read"]
    assert read["recovery_boundary"] is None
    assert read["recovered_count"] == 0
    assert read["unseen_count"] == 2
    assert plan.ok is False


def test_r19_the_sweep_probes_exactly_the_declared_range():
    """[round19 ① 경계] 스윕은 `1..childCount`를 유계로 훑는다 — 양방향 ±1 대조군.

    `range(1, recovery_boundary + 1)`에서 `+ 1`을 지우면 마지막 슬롯(4)을 프로브하지
    않아 프로브 목록이 `[2, 3]`이 되고, `+ 2`로 늘리면 선언 총계 **밖**인 5를 찔러
    `[2, 3, 4, 5]`가 된다. 상한을 `childCount`가 아닌 상수로 바꾸면 역시 어긋난다.
    """
    port = _R19SweepPort(total=4, rows=[1], present={1: 101})
    _r19_plan(port, fid_range={"start": 501, "end": 510})

    assert port.probe_slots == [2, 3, 4]
    assert port.state_calls == [FIXTURE_ROOT], "스윕이 루트를 다시 열거했다"


def test_r19_the_sweep_never_promotes_the_completeness_verdict_by_itself():
    """[round19 ①] 완전성은 **자기 근거로만** 판정된다 — 스윕은 detail을 올릴 뿐이다.

    스윕이 실제로 한 대를 회수했지만 한 대가 남았다. `complete`가 `recovered_count`나
    `recovery_boundary`를 읽으면(예: `or self.recovered_count > 0`을 완화 조건으로
    넣으면) 여기서 걸린다. 이 승격이 곧 R18-A의 거짓 보고 — "검사했고 깨끗하다" —와
    같은 형태다.
    """
    from server.vwx.patchplan import ExistingFidRead

    port = _R19SweepPort(total=3, rows=[1], present={1: 101, 2: 102})
    plan = _r19_plan(port, fid_range={"start": 501, "end": 510})
    read = plan.fid_safety["conflict_precheck"]["read"]

    assert read["recovered_count"] == 1, "스윕이 아무 것도 회수하지 못해 비공허하지 않다"
    assert read["unseen_count"] == 1
    assert read["complete"] is False
    assert plan.ok is False

    # 구조 단정 — 회수 계수가 완전성 판정에 **들어갈 자리가 없다**.
    swept_but_short = ExistingFidRead(
        attempted=True, child_count=2, enumerated_count=1, recovered_count=1, unseen=1
    )
    assert swept_but_short.complete is False


def test_r19_a_probe_that_gets_no_answer_keeps_the_structured_refusal():
    """[round19 ①] 프로브 무응답은 **거짓 승격도, 예외 폭발도** 만들지 않는다.

    투기적 프로브의 `try/except`를 지우면 `TimeoutError`가 `build_patch_plan` 밖으로
    나가고, `ToolRegistry.dispatch`에 가드가 없어 **구조화된 거부 자체가 사라진다**
    (round18 R18-D가 명명한 기제). 그러면 이 테스트는 예외로 실패한다.
    프로브 실패를 관측으로 세면 `unseen`이 0이 되어 배정이 열린다 — 그것도 실패한다.
    """
    port = _R19SweepPort(total=3, rows=[1], present={1: 101}, hidden_mode="raise")
    plan = _r19_plan(port, fid_range={"start": 501, "end": 510})
    read = plan.fid_safety["conflict_precheck"]["read"]

    assert read["probe_failure_count"] == 2
    assert read["recovered_count"] == 0
    assert read["unseen_count"] == 2
    assert read["complete"] is False
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"


def test_r19_a_pointer_string_from_a_probe_is_never_adopted_as_a_fid():
    """[round19 ①] `ok=true`라도 값이 FID로 해석되지 않으면 채택하지 않는다.

    형제 리더 독스트링 3번의 실측: `safe_property`가 `tostring(handle[name])`로 떨어져
    `'function: 0x105b0f048'`이 `ok=true`와 함께 온다. 스윕 프로브에서 `_fid_int`를
    빼고 값을 그대로 담으면 `existing_fids`에 문자열이 들어가 `complete=True`가 되고,
    그 뒤 `proposed_fid in existing_fids` 대조는 **정수와 문자열을 비교해 영원히 거짓**
    이라 이미 쓰이는 번호가 배정된다.
    """
    port = _R19SweepPort(total=3, rows=[1], present={1: 101}, hidden_mode="pointer")
    read = _existing_fids_from_console(port)

    assert all(isinstance(fid, int) for fid in read.fids)
    assert read.fids == (101,)
    assert read.probe_failures == 2
    assert read.recovered_count == 0
    assert read.unseen == 2
    assert read.complete is False


def test_r19_the_sweep_stays_out_when_an_enumerated_slot_is_outside_its_domain():
    """[round19 ① 인덱스 도메인] 열거 슬롯이 `1..childCount` **밖**이면 스윕하지 않는다.

    선언 3대인데 열거된 슬롯이 57번이다 — 이 풀의 인덱스 도메인은 스윕 도메인이
    아니다(희소 풀). 그런 스냅샷에서 범위 안을 훑으면 관측 수가 총계에 닿아
    `unseen=0`이 되는데, 정작 범위 **밖** 픽스처의 FID는 못 읽은 채로 남는다.

    게이트(`all(1 <= slot <= child_count ...)`)를 지우면 프로브 1·2·3이 모두 답해
    관측 4개 > 선언 3개가 되어 `over_enumerated`가 참이 되고, 그때 `reason()`은
    **"열거된 슬롯 1개가 선언 총계 3개보다 많다"**는 산술적으로 거짓인 문장을 낸다.
    아래 두 단정이 각각 그 두 결과를 잡는다.
    """
    port = _R19SweepPort(total=3, rows=[57], present={57: 157, 1: 101, 2: 102, 3: 103})
    read = _existing_fids_from_console(port)

    assert port.probe_slots == []
    assert read.recovery_boundary is None
    assert read.over_enumerated is False
    assert read.unseen == 2
    assert read.complete is False


_R19_ARITHMETIC_ROWS = (
    ("절단·회수됨", dict(total=3, rows=[1], present={1: 101, 2: 102, 3: 103})),
    ("절단·회수 실패", dict(total=3, rows=[1], present={1: 101})),
    ("절단·부분 회수", dict(total=3, rows=[1], present={1: 101, 2: 102})),
    ("빈 열거", dict(total=2, rows=[], present={1: 101, 2: 102})),
    ("도메인 밖 슬롯", dict(total=3, rows=[57], present={57: 157, 1: 101})),
    ("초과 열거", dict(total=1, rows=[1, 2], present={1: 101, 2: 102})),
    ("프로브 무응답", dict(total=3, rows=[1], present={1: 101}, hidden_mode="raise")),
)


def test_r19_the_arithmetic_row_table_is_complete():
    """행 삭제 감지 — 일곱 형태가 다 있어야 하고, 라벨은 서로 달라야 한다."""
    labels = [row[0] for row in _R19_ARITHMETIC_ROWS]
    assert len(labels) == len(set(labels)) == 7
    # 스윕이 도는 형태와 돌지 않는 형태가 **둘 다** 있어야 표가 한쪽만 보지 않는다.
    swept = [row for row in _R19_ARITHMETIC_ROWS if row[1]["rows"] and row[1]["total"] > 1]
    assert 0 < len(swept) < len(_R19_ARITHMETIC_ROWS)


@pytest.mark.parametrize(
    "label,kwargs", _R19_ARITHMETIC_ROWS, ids=[row[0] for row in _R19_ARITHMETIC_ROWS]
)
def test_r19_the_census_sentence_is_arithmetically_true_in_every_shape(label, kwargs):
    """[round19 ①] 스윕이 붙은 뒤에도 조작자에게 나가는 **계수 문장이 참**이다.

    두 불변식을 건다.
    ① `over_enumerated`를 말하면 그 문장이 인용하는 두 수(`enumerated_count`,
       `child_count`)가 실제로 그 관계여야 한다 — 인덱스 도메인 게이트를 지우면
       회수분이 총계를 넘겨 놓고 문장은 열거 수를 인용해 **거짓**이 된다.
    ② 관측 = 열거 + 회수이고, 못 본 슬롯 수는 총계 - 관측이다. 어느 슬롯도 두 축으로
       세지 않는다(round14 T01/T03).
    """
    read = _existing_fids_from_console(_R19SweepPort(**kwargs))

    if read.over_enumerated:
        assert read.enumerated_count > (read.child_count or 0), read.reason()
    observed = read.enumerated_count + read.recovered_count
    if read.child_count is not None:
        assert read.unseen == max(read.child_count - observed, 0)
        assert read.unseen <= read.child_count
    assert read.recovered_count <= (read.recovery_boundary or 0)


def test_r19_the_real_scale_truncation_reaches_a_verdict_at_all():
    """[round19 ① 실물 규모] 39대 선언 · 19대 열거 — M8을 막던 그 형태다.

    교정 쇼파일은 슬롯과 FID가 일치하므로(`console/lua/PROTOCOL.md:305-324`) 슬롯 s의
    FID를 s로 둔다. 스윕 없이는 `unseen=20`으로 **한 대도** 배정되지 않았다(M8 대상
    0건). 스윕 뒤에는 프로브 20회로 총계가 닫히고 배정이 진행되며, 기존 FID 1..39는
    전부 회피된다.
    """
    port = _R19SweepPort(
        total=39, rows=list(range(1, 20)), present={slot: slot for slot in range(1, 40)}
    )
    plan = _r19_plan(port, fid_range={"start": 40, "end": 50}, count=3)
    read = plan.fid_safety["conflict_precheck"]["read"]

    assert port.probe_slots == list(range(20, 40)), "실물 절단 구간을 훑지 않았다"
    assert (read["enumerated_count"], read["recovered_count"]) == (19, 20)
    assert read["recovery_boundary"] == 39
    assert read["unseen_count"] == 0
    assert read["complete"] is True
    assert plan.ok is True
    assert plan.fid_safety["conflict_precheck"]["existing_fids"] == list(range(1, 40))
    assert [target.assigned_fid for target in plan.targets] == [40, 41, 42]


# --------------------------------------------------------------------------
# [round19 HARD 규율 4] 형제 표면 전수 — `server/vwx/` 전 모듈의 **열거 판독 자리**
#
# "절단은 기본 경로다"는 이 콘솔 전체의 성질이므로, 열거를 읽는 자리는 모두 절단
# 처방을 **결정한 자리**여야 한다. 스윕을 붙였는지 여부와 그 근거를 등기부로 고정한다 —
# 게이트가 요구하는 것은 "스윕이 있다"가 아니라 **"그 자리가 보이고 판단이 적혀 있다"**다.
# --------------------------------------------------------------------------

#: (모듈, 함수, 스윕 여부, 판단 근거)
_R19_ENUMERATION_READERS = (
    (
        "patchplan.py",
        "_existing_fids_from_console",
        True,
        "전수 관측이 아니면 아무 것도 배정하지 못하는 구조라 절단이 곧 영구 정지였다 — "
        "실물 39대에서 GO 분기가 한 대도 배정하지 못했다(M8 대상 0건).",
    ),
    (
        "typemap.py",
        "read_fixture_type_library",
        False,
        "[round21 R20-A] 이 자리 자체는 스윕하지 않는다 — 라이브러리 루트는 콘솔의 전체 "
        "타입이라 무조건 훑으면 타입당 `_read_type`이 딸려와 200종에서 수천 왕복이 된다. "
        "대신 두 가지를 한다: ① 절단 판정을 `truncated` 플래그 단독에서 **계수 대조**"
        "(`node.childCount` vs 반환 행 수)로 바꿔 형제 리더 독스트링 2번의 규율에 맞췄고, "
        "② 회수는 **요청된 이름만** 찾는 `recover_requested_types`가 맡는다. 열거 안의 "
        "타입은 정상 확정되고, 없는 타입은 미관측 계수와 함께 부재를 단정하지 않는다.",
    ),
    (
        "typemap.py",
        "recover_requested_types",
        True,
        "[round21 R20-A ⓑ] 표적 회수 스윕. 전제·경계·비승격을 PRESERVE "
        "`server/prechk/inventory.py`에서 그대로 가져왔다(열거된 항목이 하나라도 있어야 "
        "하고, `1..childCount` 유계이며, 완전성 판정은 스윕으로 올라가지 않는다). "
        "전수가 아니라 표적인 이유는 비용이다: 표적 `U + M·(1+c·m)` vs 전수 "
        "`U·(2+c·m)` — 200종·모드20에서 197~217회 대 3,872~7,392회다.",
    ),
    (
        "typemap.py",
        "_read_type",
        False,
        "[round21 R20-A ⓐ] 모드 열거도 **계수 대조**를 받는다(`DMXModes`의 "
        "`node.childCount` vs 반환 행 수 → `modes_incomplete`). 스윕은 하지 않는다 — "
        "모드 회수는 타입 회수와 달리 요청 대상이 이름 하나로 좁혀지지 않아 표적화가 "
        "성립하지 않고, 미관측 모드는 `mode_unseen_count`와 고지로 보인다.",
    ),
    (
        "typemap.py",
        "_read_channel_count",
        False,
        "열거가 아니다: `childCount`를 **채널 수라는 값**으로 읽고 자식 목록을 쓰지 "
        "않는다. 절단은 항목 목록만 자르고 `childCount`는 진짜 총계이므로(형제 리더 "
        "독스트링 2번) 이 판독에는 절단 처방이 필요하지 않다.",
    ),
)


def _r19_scan_enumeration_readers() -> set[tuple[str, str]]:
    """`server/vwx/` 전 모듈에서 `*.query_state(...)`를 호출하는 함수를 AST로 전수한다."""
    found: set[tuple[str, str]] = set()
    for path in sorted(Path("server/vwx").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "query_state"
                ):
                    found.add((path.name, node.name))
    return found


def test_r19_the_enumeration_reader_registry_is_a_bijection_onto_server_vwx():
    """[round19 HARD 4] 열거 판독 자리가 전부 등기돼 있고, 유령 행이 없다.

    새 모듈이나 새 함수가 `query_state`로 열거를 읽으면 이 게이트가 먼저 막는다 —
    아홉 라운드 연속 FAIL의 기제는 나쁜 판정이 아니라 **표 밖에 있던 형제 자리**였다.
    """
    scanned = _r19_scan_enumeration_readers()
    registered = {(row[0], row[1]) for row in _R19_ENUMERATION_READERS}
    assert scanned == registered, (
        "열거 판독 자리가 등기부와 다르다 — 미등록:"
        f" {sorted(scanned - registered)} / 유령: {sorted(registered - scanned)}"
    )


@pytest.mark.parametrize("index", range(len(_R19_ENUMERATION_READERS)))
def test_r19_deleting_any_enumeration_reader_row_breaks_the_registry(index: int):
    """행 삭제 프로브 — 어느 행을 지워도 프로덕션 전수와 어긋난다. 근거 문장도 요구한다."""
    shrunk = _R19_ENUMERATION_READERS[:index] + _R19_ENUMERATION_READERS[index + 1 :]
    assert {(row[0], row[1]) for row in shrunk} != _r19_scan_enumeration_readers()
    module, function, sweeps, rationale = _R19_ENUMERATION_READERS[index]
    assert isinstance(sweeps, bool)
    assert len(rationale) > 40, f"{module}:{function}의 판단 근거가 비어 있다"


def test_r19_the_enumeration_registry_records_both_decisions():
    """비공허성 — 등기부에 스윕한 자리와 스윕하지 않은 자리가 **둘 다** 있다.

    전부 `True`거나 전부 `False`인 표는 "판단했다"를 증명하지 못한다.
    """
    decisions = {row[2] for row in _R19_ENUMERATION_READERS}
    assert decisions == {True, False}


# --------------------------------------------------------------------------
# [round19 minor#9] 입력 거부도 **콘솔이 무엇을 못 보여줬는지**를 싣는다
#
# round18이 `fid_range` 검증을 사전검사 앞으로 옮긴 것은 옳다(거부 payload가
# "검사했고 깨끗하다"고 주장하던 R18-A 치명). 그런데 그 이동이 `skipped_checks`
# 고지까지 지워, 바닥 위반 **동시에** 판독 불완전인 호출에서 조작자는 범위만 고치고
# 다시 거부당한다. 고지(부정 진술)는 복원하고 주장(`fid_safety`)은 복원하지 않는다.
# --------------------------------------------------------------------------


def _r19_notice_ports():
    """행마다 새 포트를 만든다 — 포트는 호출 기록을 들고 있어 공유하면 안 된다."""
    return {
        # 숨은 슬롯이 값을 내놓지 않아 스윕으로도 회수되지 않는 절단.
        "truncated": lambda: _R19SweepPort(total=3, rows=[1], present={1: 101}),
        "clean": lambda: _R19SweepPort(total=0, rows=[]),
        "exploding": ExplodingFidRigPort,
    }


#: (행 이름, 판정, 육안확인, fid_range, 포트, 기대 거부 코드, 기대 고지 kind들, fid_safety 여부)
_R19_NOTICE_ROWS = (
    ("범위 미제공", ASSUMPTION_71_GO, None, None, "truncated", FID_RANGE_REQUIRED, True, False),
    (
        "바닥 위반 범위",
        ASSUMPTION_71_GO,
        None,
        {"start": -10, "end": -8},
        "truncated",
        "invalid_fid_range",
        True,
        False,
    ),
    (
        "육안확인 미제공",
        ASSUMPTION_71_NEGATIVE,
        None,
        {"start": 501, "end": 510},
        "exploding",
        FID_RANGE_CONFIRMATION_REQUIRED,
        False,
        True,
    ),
    (
        "판독 불완전",
        ASSUMPTION_71_GO,
        None,
        {"start": 501, "end": 510},
        "truncated",
        "fid_precheck_read_incomplete",
        True,
        True,
    ),
    ("통과", ASSUMPTION_71_GO, None, {"start": 501, "end": 510}, "clean", None, None, True),
)


def test_r19_the_notice_row_table_covers_every_assignment_path_return():
    """행 삭제 감지 · `patchplan.py` 전수 — 이 스캐너가 읽는 것은 `server/vwx/patchplan.py`
    **한 모듈뿐**이고, 그 안에서 FID 배정 갈래의 `return PatchPlan(...)` **다섯 자리**를 센다.

    셈 단위는 **"`_fid_assignment_requested` 조기 반환문(`if not …: return`) 이후에
    있는 `return PatchPlan(...)` 문장"**이다. 그 `if` 블록 자체의 반환은 배정을 요청하지
    않은 열람 호출이라 사전검사 빚이 없으므로 단위에서 뺀다. round18까지 다섯 중 둘만
    고지를 실었고 round19가 다섯 전부로 늘렸다. 프로덕션에 여섯 번째 반환이 생기면
    이 개수 단정이 먼저 실패한다.

    같은 셈을 명령줄로도 재현할 수 있다(진행 보고에 남긴 명령):
        python - <<'PY' … ast.walk로 `_plan_from_report`의 If/Return을 센다 … PY
    """
    source = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    (build,) = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_plan_from_report"
    ]
    (gate,) = [
        node
        for node in ast.walk(build)
        if isinstance(node, ast.If)
        and any(
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "_fid_assignment_requested"
            for inner in ast.walk(node.test)
        )
    ]
    returns = [
        node
        for node in ast.walk(build)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "PatchPlan"
        and node.lineno > gate.end_lineno
    ]
    assert len(returns) == 5, "배정 갈래의 반환 수가 바뀌었다 — 고지 표를 다시 맞춰라"
    carriers = [
        node
        for node in returns
        if any(keyword.arg == "skipped_checks" for keyword in node.value.keywords)
    ]
    assert len(carriers) == 5, "고지를 싣지 않는 반환이 남았다"

    labels = [row[0] for row in _R19_NOTICE_ROWS]
    assert len(labels) == len(set(labels)) == 5
    assert {row[6] for row in _R19_NOTICE_ROWS} == {True, False, None}


@pytest.mark.parametrize(
    "label,assumption,confirmed,fid_range,port_key,code,notice,carries_safety",
    _R19_NOTICE_ROWS,
    ids=[row[0] for row in _R19_NOTICE_ROWS],
)
def test_r19_every_assignment_path_return_says_what_the_console_did_not_show(
    label, assumption, confirmed, fid_range, port_key, code, notice, carries_safety
):
    """[round19 minor#9] 어느 분기에서든 사전검사 고지가 payload에 있다.

    `_fid_precheck_notices` 호출을 어느 반환에서 지워도(=round18 상태로 되돌려도)
    해당 행의 `kind` 단정이 실패한다. 반대로 거부 갈래에 `fid_safety`를 되싣으면
    마지막 단정이 실패한다 — 고지는 복원하고 **주장은 복원하지 않는다**.
    """
    from server.vwx.verdicts import FID_CONFLICT_PRECHECK_INCOMPLETE

    port = _r19_notice_ports()[port_key]()
    plan = _r19_plan(port, fid_range=fid_range, assumption_71=assumption, confirmed=confirmed)
    payload = plan.to_dict()

    if code is None:
        assert plan.ok is True, label
    else:
        assert plan.ok is False and payload["rejection"]["code"] == code, label

    kinds = [check["kind"] for check in payload["skipped_checks"]]
    if notice is True:
        assert kinds == [FID_CONFLICT_PRECHECK_INCOMPLETE], label
    elif notice is False:
        assert kinds == [FID_CONFLICT_PRECHECK_DESCOPE], label
    else:
        assert kinds == [], label

    assert ("fid_safety" in payload) is carries_safety, label


def test_r19_the_restored_notice_states_only_what_was_observed():
    """[round19 minor#9] 복원한 고지는 **부정 진술**뿐이다 — "검사했다"가 없다.

    바닥 위반 범위 + 회수 불가 절단이라는, 감사가 지적한 그 조합이다. 고지는
    무엇을 못 봤는지를 계수로 싣고, payload 어디에도 `performed`(검사 수행 주장)은
    없다. 거부 갈래에 `_fid_safety_payload`를 되싣으면 두 번째 단정이 실패한다.
    """
    port = _R19SweepPort(total=3, rows=[1], present={1: 101})
    plan = _r19_plan(port, fid_range={"start": -10, "end": -8})
    payload = plan.to_dict()

    (check,) = payload["skipped_checks"]
    assert check["complete"] is False
    assert (check["child_count"], check["enumerated_count"], check["unseen_count"]) == (3, 1, 2)
    assert check["recovery_boundary"] == 3, "고지가 스윕 사실을 싣지 않았다"
    assert "fid_safety" not in payload
    assert "performed" not in str(payload), "거부 payload가 검사 수행을 주장한다"
    for phrase in _R16_REASSURING_PHRASES:
        assert phrase not in check["reason"], phrase


def test_r19_the_notice_does_not_appear_when_no_assignment_was_requested():
    """경계 — 배정을 요청하지 않은 열람 호출에는 사전검사 고지가 없다.

    사전검사는 배정이 요청됐을 때 **비로소 갚아야 하는 빚**이다. 고지를 요청 여부와
    무관하게 달면 조작자는 아무 것도 고르지 않았는데 "사전검사가 불완전하다"는 말을
    듣는다. `_fid_precheck_notices`를 함수 머리로 끌어올리는 변형을 이 단정이 막는다.
    """
    payload_report = report_payload([rr(0)])
    plan = build_patch_plan(
        payload_report,
        selected=candidate_ids(payload_report),
        fid_property_port=_R19SweepPort(total=3, rows=[1], present={1: 101}),
    )
    assert plan.ok is True
    assert plan.to_dict()["skipped_checks"] == []


# --------------------------------------------------------------------------
# [round19 minor#8] 별도 코드를 만든 근거 = **라벨이 고칠 축을 가리킨다**
#
# `verdicts.py`의 `FID_BELOW_MINIMUM` 주석은 `address_below_minimum`을 재사용하지 않는
# 이유를 **오직 라벨 내용**으로 설명한다. 그런데 감사가 심은 M24 — FID 라벨을 정확히
# 주소축 문구로 교체 — 는 1,480건 전부를 통과했다(진짜 공백). 문자열 리터럴 비교가
# 아니라 **축 특정 가능성**을 잰다: 각 라벨은 자기 축을 명명하고 형제 축은 명명하지
# 않는다. 전 어휘 라벨 유일성 게이트가 같은 성질의 형제 자리를 함께 닫는다.
#
# 형태는 `DeadEndVocab`과 합의한 것이다(축 어휘 공유, 전 어휘 fix_axis 전단사 표는
# 그쪽 단독 소유 — 여기서는 쌍 범위로만 붙인다).
# --------------------------------------------------------------------------

#: 축 → 그 축을 조작자에게 명명하는 토큰들. 리터럴 라벨이 아니라 **축 이름**이다.
_R19_AXIS_PAIR_TOKENS = {
    "design_fid": ("FID",),
    "design_address": ("주소", "유니버스"),
    "design_type_name": ("FixtureType",),
    "design_mode": ("DMXMode",),
}

#: (등재 코드, 조작자가 고쳐야 할 축). 아래 접미 전수 게이트가 이 표의 완전성을 강제한다.
_R19_AXIS_PAIR_ROWS = (
    ("address_below_minimum", "design_address"),
    ("fid_below_minimum", "design_fid"),
    ("fixture_type_not_in_library", "design_type_name"),
    ("dmx_mode_not_in_library", "design_mode"),
)


def _r19_identified_axis(text: str) -> str | None:
    """이 문장이 **어느 축을 고치라고** 말하는가. 모호하면 `None`."""
    named = {
        axis
        for axis, tokens in _R19_AXIS_PAIR_TOKENS.items()
        if any(token in text for token in tokens)
    }
    return next(iter(named)) if len(named) == 1 else None


def test_r19_the_axis_pair_table_covers_every_registered_member_of_both_families():
    """[round19 minor#8 · 형제 전수] 축만 다른 **같은 형태의 코드**를 접미로 전수한다.

    `*_below_minimum`(바닥 위반)과 `*_not_in_library`(라이브러리 부재)는 각각 형태가
    같고 축만 다른 코드 가족이다. 가족에 코드가 하나 추가되면 이 게이트가 먼저 실패해
    새 코드도 축 대조군을 갖게 된다.
    """
    from server.vwx.verdicts import TARGET_EXCLUSION_REASON

    registered = {row[0] for row in _R19_AXIS_PAIR_ROWS}
    families = {
        code
        for code in TARGET_EXCLUSION_REASON
        if code.endswith("_below_minimum") or code.endswith("_not_in_library")
    }
    assert families == registered
    assert len(_R19_AXIS_PAIR_ROWS) == len(registered) == 4
    assert {row[1] for row in _R19_AXIS_PAIR_ROWS} == set(_R19_AXIS_PAIR_TOKENS)


@pytest.mark.parametrize(
    "code,axis", _R19_AXIS_PAIR_ROWS, ids=[row[0] for row in _R19_AXIS_PAIR_ROWS]
)
def test_r19_each_registered_label_names_its_own_axis_and_not_a_siblings(code, axis):
    """[round19 minor#8] 라벨 하나만 읽어도 **고칠 축**이 특정된다.

    이 단정이 M24를 죽인다: FID 라벨을 주소축 문구로 바꾸면 `design_address`가
    식별돼 기대 축과 어긋난다. 리터럴 비교가 아니라 축 토큰의 **유일 출현**을 재므로,
    같은 축을 다르게 표현한 라벨은 통과하고 형제 축으로 넘어간 라벨만 걸린다.
    """
    from server.vwx.verdicts import target_exclusion_label

    assert _r19_identified_axis(target_exclusion_label(code)) == axis


def test_r19_the_axis_predicate_actually_discriminates_when_labels_are_swapped():
    """[round19 minor#8] 위 단정이 공허하지 않다 — 라벨을 교차 교체하면 축 신호가 뒤집힌다.

    감사가 심은 M24를 **여기서 실제로 심어** 판별식이 그것을 잡는다는 것을 보인다.
    두 방향 모두 확인한다(FID←주소, 주소←FID). 판별식이 라벨이 아닌 다른 근거를
    보고 있었다면 교체 후에도 기대 축이 나와 이 테스트가 실패한다 — 그때는
    `FID_BELOW_MINIMUM`의 존재 근거를 라벨이 아닌 것으로 다시 적어야 한다.
    """
    from server.vwx import verdicts

    fid_label = verdicts._TARGET_EXCLUSION_LABELS[verdicts.FID_BELOW_MINIMUM]
    address_label = verdicts._TARGET_EXCLUSION_LABELS[verdicts.ADDRESS_BELOW_MINIMUM]

    assert _r19_identified_axis(address_label) != "design_fid"
    assert _r19_identified_axis(fid_label) != "design_address"


def test_r19_a_swapped_label_reaches_the_operator_payload_and_loses_the_axis():
    """[round19 minor#8 · 프로덕션 경로] 배제행의 `label`은 등재 표에서 온다.

    `_assign_fids`로 실제 배제행을 만들고, 그 payload의 라벨이 축을 특정하는 것을
    확인한다. 그 다음 등재 표를 주소축 문구로 monkeypatch하면 **같은 payload**가
    축을 잃는다 — 라벨이 조작자에게 축을 알리는 유일한 구조화 근거임을 실증한다.
    """
    from server.vwx import verdicts
    from server.vwx.patchplan import FIDRange, _assign_fids

    def exclusion_label() -> str:
        _, exclusions = _assign_fids(
            (_r18_candidate("a"),),
            FIDRange(start=0, end=1),
            existing_fids=frozenset(),
            fid_range_visually_confirmed_empty=None,
        )
        (row,) = exclusions
        assert row.code == verdicts.FID_BELOW_MINIMUM
        return row.to_dict()["label"]

    assert _r19_identified_axis(exclusion_label()) == "design_fid"

    original = dict(verdicts._TARGET_EXCLUSION_LABELS)
    try:
        verdicts._TARGET_EXCLUSION_LABELS[verdicts.FID_BELOW_MINIMUM] = original[
            verdicts.ADDRESS_BELOW_MINIMUM
        ]
        assert _r19_identified_axis(exclusion_label()) != "design_fid"
    finally:
        verdicts._TARGET_EXCLUSION_LABELS.clear()
        verdicts._TARGET_EXCLUSION_LABELS.update(original)

    assert _r19_identified_axis(exclusion_label()) == "design_fid", "복원 실패"


def test_r19_every_registered_label_is_unique_within_its_vocabulary():
    """[round19 minor#8 · 형제 전수] 라벨이 유일 구분 근거라면 **유일해야** 한다.

    등재 어휘 여덟 개 전부에 건다. 어느 코드의 라벨을 형제 코드의 라벨로 통째 교체하는
    변형(M24가 한 일)은 그 순간 같은 어휘 안에 라벨이 둘 겹치므로 여기서 걸린다.
    새 코드를 기존 라벨 재사용으로 추가하는 것도 막힌다.
    """
    from server.vwx.verdicts import _AUTOPATCH_VOCABULARY_LABELS

    assert len(_AUTOPATCH_VOCABULARY_LABELS) == 8
    for vocabulary, labels in _AUTOPATCH_VOCABULARY_LABELS.items():
        assert len(set(labels.values())) == len(labels), f"{vocabulary}에 중복 라벨이 있다"
        for code, label in labels.items():
            assert label.strip(), f"{vocabulary}/{code}의 라벨이 비어 있다"
