"""Tests for server.lxseq.mapper — SPEC-COPILOT-LXSEQ-001 M2.

AC-LXSEQ-005: type resolution flows only through the resolve_fixture_type contract.
AC-LXSEQ-006: console mode is filled only on a measured-width unique match.
AC-LXSEQ-007: occupied rows are skipped and listed, never overwritten.
AC-LXSEQ-008: a non-exhaustive console read yields zero runs.
AC-LXSEQ-009: run grouping + FID map.
AC-LXSEQ-010: server/lxseq carries no console-write surface.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from server.lxseq.mapper import ModeResolution, build_import_plan
from server.lxseq.parser import parse_patch_csv
from server.prechk.inventory import COMPLETE, INCOMPLETE, Inventory
from server.prechk.mode_read import ModeChoice, TypeModeRead
from server.vwx.addressfit import Occupant
from server.vwx.patchplan import ExistingFidRead

FIXTURE_PATH = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")


def _records():
    return parse_patch_csv(FIXTURE_PATH.read_text(encoding="utf-8")).records


def _csv_types(records) -> list[str]:
    seen: list[str] = []
    for record in records:
        if record.fixture_type not in seen:
            seen.append(record.fixture_type)
    return seen


def _present(resolved: str) -> dict:
    return {"status": "present", "resolved": resolved, "candidates": []}


def _all_present(records) -> dict[str, dict]:
    return {name: _present(name) for name in _csv_types(records)}


class _CountingResolutions(dict):
    """조회를 기록하는 해석표.

    매퍼가 스스로 보고하는 `plan.types_requested` 는 records 에서 파생된 값이라
    (`mapper.py` `types_requested = _distinct_types(records)`), 매퍼가 실제로 몇 번
    조회했는지를 말해 주지 않는다 — 행마다 불러도 그 값은 8종 그대로다. 그래서
    조회 자체를 여기서 센다.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookups: list[str] = []

    def get(self, key, default=None):
        self.lookups.append(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.lookups.append(key)
        return super().__getitem__(key)


def _unique_modes(records) -> dict[str, TypeModeRead]:
    """타입마다 폭이 유일한 모드 하나 — 모드 확정이 항상 성공하는 바탕."""
    widths: dict[str, int] = {}
    for record in records:
        widths.setdefault(record.fixture_type, record.channels)
    return {
        name: TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name=f"{name} std", width=width, slot=1),),
        )
        for name, width in widths.items()
    }


def _empty_inventory() -> Inventory:
    return Inventory(
        path="Root",
        child_count=0,
        enumerated_count=0,
        recovered_count=0,
        observed_count=0,
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
    )


def _complete_fid_read(fids: tuple[int, ...] = ()) -> ExistingFidRead:
    return ExistingFidRead(
        fids=fids,
        child_count=len(fids),
        enumerated_count=len(fids),
        unseen=0,
        unreadable_fids=0,
        unusable_rows=0,
        unparsable_rows=0,
        attempted=True,
    )


def _plan(records=None, **overrides):
    records = _records() if records is None else records
    kwargs = {
        "records": records,
        "type_resolutions": _all_present(records),
        "mode_reads": _unique_modes(records),
        "inventory": _empty_inventory(),
        "occupants": (),
        "existing_fids": _complete_fid_read(),
    }
    kwargs.update(overrides)
    return build_import_plan(**kwargs)


# ---------------------------------------------------------------------------
# AC-LXSEQ-005 — type_resolution
# ---------------------------------------------------------------------------


def test_type_resolution_present_uses_console_name_not_csv_label():
    records = _records()
    csv_label = "Robe Spiider"
    assert any(r.fixture_type == csv_label for r in records)

    resolutions = _all_present(records)
    resolutions[csv_label] = _present("Robin Spiider")
    modes = _unique_modes(records)
    modes["Robin Spiider"] = modes[csv_label]

    plan = _plan(records, type_resolutions=resolutions, mode_reads=modes)
    spiider_runs = [r for r in plan.runs if r.console_type == "Robin Spiider"]
    assert spiider_runs
    assert sum(r.count for r in spiider_runs) == 8
    assert all(r.console_type != csv_label for r in plan.runs)


def test_type_resolution_ambiguous_skips_that_type_with_candidates():
    records = _records()
    csv_label = "Robe Spiider"
    resolutions = _all_present(records)
    resolutions[csv_label] = {
        "status": "ambiguous",
        "resolved": None,
        "candidates": ["Robin Spiider", "Robin Spiider WB"],
    }

    plan = _plan(records, type_resolutions=resolutions)
    skipped = [s for s in plan.skipped if s.kind == "type_unresolved"]
    assert len(skipped) == 8
    assert all("Robin Spiider" in s.detail for s in skipped)
    assert all(r.console_type != csv_label for r in plan.runs)


def test_type_resolution_absent_advises_adding_the_type():
    records = _records()
    csv_label = "Robe Spiider"
    resolutions = _all_present(records)
    resolutions[csv_label] = {"status": "absent", "resolved": None, "candidates": []}

    plan = _plan(records, type_resolutions=resolutions)
    skipped = [s for s in plan.skipped if s.kind == "type_unresolved"]
    assert len(skipped) == 8
    assert any("타입 추가" in s.detail for s in skipped)


def test_type_resolution_library_unreadable_skips_every_row():
    records = _records()
    resolutions = {
        name: {"status": "library_unreadable", "resolved": None, "candidates": []}
        for name in _csv_types(records)
    }

    plan = _plan(records, type_resolutions=resolutions)
    assert plan.runs == ()
    assert len(plan.skipped) == 86
    assert all(s.kind == "type_unresolved" for s in plan.skipped)
    assert all("단정하지 않는다" in s.detail for s in plan.skipped)


def test_type_resolution_is_requested_once_per_distinct_type():
    records = _records()
    distinct = _csv_types(records)
    # 비공허성 두 줄 — 행이 타입보다 훨씬 많아야 「타입마다 한 번」이 「행마다 한 번」과
    # 구별된다. 둘이 같은 수라면 아래 단언은 아무것도 가르지 못한다.
    assert len(distinct) == 8
    assert len(records) == 86

    resolutions = _CountingResolutions(_all_present(records))
    plan = _plan(records, type_resolutions=resolutions)

    # 매퍼의 자기 보고(파생값)가 아니라 **실제 조회 횟수**를 잰다. 행마다 부르면 86이 된다.
    assert len(resolutions.lookups) == 8
    assert sorted(resolutions.lookups) == sorted(distinct)
    # 자기 보고도 같은 값이어야 한다 — 다만 이것만으로는 위 단언을 대신하지 못한다.
    assert sorted(plan.types_requested) == sorted(distinct)


# ---------------------------------------------------------------------------
# AC-LXSEQ-006 — mode_resolution
# ---------------------------------------------------------------------------


def _resolution(plan, csv_type: str):
    """`plan.mode_resolutions` 를 CSV 타입 이름으로 조회한다.

    키는 (타입, 채널수, CSV 모드라벨) 이다 — 한 타입이 두 폭으로 오면 해석도 갈리기
    때문이다(PR #72 D3). 아래 테스트들은 폭이 하나인 입력만 쓰므로, 해석이 정말로
    하나뿐인지 확인한 뒤 그것을 돌려준다. 둘 이상이면 그 사실 자체가 보고돼야 한다.
    """
    found = [value for key, value in plan.mode_resolutions.items() if key[0] == csv_type]
    assert len(found) == 1, f"{csv_type}: 해석이 {len(found)}개 — 폭이 하나인 입력이 아니다"
    return found[0]


def _single_type_records(records, csv_label: str):
    return tuple(r for r in records if r.fixture_type == csv_label)


def test_mode_resolution_unique_width_match_is_adopted():
    records = _single_type_records(_records(), "Robe Spiider")
    channels = records[0].channels
    modes = {
        "Robe Spiider": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="Mode 1", width=channels, slot=1),
                ModeChoice(name="Mode 2", width=channels - 5, slot=2),
            ),
        )
    }
    plan = _plan(records, mode_reads=modes)
    assert plan.runs
    assert all(r.console_mode == "Mode 1" for r in plan.runs)
    assert _resolution(plan, "Robe Spiider").resolution == "resolved"
    assert _resolution(plan, "Robe Spiider").resolved_by == "width_unique"


def test_mode_resolution_tied_width_broken_by_label_token():
    records = _single_type_records(_records(), "Robe Spiider")
    channels = records[0].channels
    records = tuple(type(r)(**{**r.__dict__, "mode_label": "Extended 25ch"}) for r in records)
    modes = {
        "Robe Spiider": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="Basic", width=channels, slot=1),
                ModeChoice(name="Extended", width=channels, slot=2),
            ),
        )
    }
    plan = _plan(records, mode_reads=modes)
    assert all(r.console_mode == "Extended" for r in plan.runs)
    assert _resolution(plan, "Robe Spiider").resolved_by == "label_token"


def test_mode_resolution_unresolvable_skips_that_type_without_a_card():
    records = _single_type_records(_records(), "Robe Spiider")
    channels = records[0].channels
    modes = {
        "Robe Spiider": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="A", width=channels, slot=1),
                ModeChoice(name="B", width=channels, slot=2),
            ),
        )
    }
    plan = _plan(records, mode_reads=modes)
    assert plan.runs == ()
    assert len(plan.skipped) == 8  # 비공허성 — 그 타입 행 수와 같다
    assert all(s.kind == "mode_unresolved" for s in plan.skipped)
    assert all("mode_overrides" in s.detail for s in plan.skipped)
    assert _resolution(plan, "Robe Spiider").resolution == "unresolved"
    assert len(_resolution(plan, "Robe Spiider").measured_modes) == 2


def test_mode_resolution_unresolvable_leaves_other_types_untouched():
    records = _records()
    channels = _single_type_records(records, "Robe Spiider")[0].channels
    modes = _unique_modes(records)
    baseline_runs = len(_plan(records).runs)

    modes["Robe Spiider"] = TypeModeRead(
        attempted=True,
        type_found=True,
        modes=(
            ModeChoice(name="A", width=channels, slot=1),
            ModeChoice(name="B", width=channels, slot=2),
        ),
    )
    plan = _plan(records, mode_reads=modes)
    unresolved = [s for s in plan.skipped if s.kind == "mode_unresolved"]
    assert len(unresolved) == 8
    assert sum(r.count for r in plan.runs) == 86 - 8
    assert baseline_runs > len(plan.runs)  # 비공허성 — 바탕에서 실제로 줄었다


@pytest.mark.parametrize(
    ("override", "expected_mode"),
    [({"Robe Spiider": "B"}, "B"), ({"Robe Spiider": "b"}, "B")],
)
def test_mode_resolution_override_adopted_when_in_measured_list(override, expected_mode):
    records = _single_type_records(_records(), "Robe Spiider")
    channels = records[0].channels
    modes = {
        "Robe Spiider": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="A", width=channels, slot=1),
                ModeChoice(name="B", width=channels, slot=2),
            ),
        )
    }
    plan = _plan(records, mode_reads=modes, mode_overrides=override)
    assert plan.runs
    assert all(r.console_mode == expected_mode for r in plan.runs)
    assert _resolution(plan, "Robe Spiider").resolved_by == "override"


def test_mode_resolution_override_rejected_when_not_measured():
    records = _single_type_records(_records(), "Robe Spiider")
    channels = records[0].channels
    modes = {
        "Robe Spiider": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="A", width=channels, slot=1),
                ModeChoice(name="B", width=channels, slot=2),
            ),
        )
    }
    plan = _plan(records, mode_reads=modes, mode_overrides={"Robe Spiider": "C"})
    assert plan.runs == ()
    assert all(s.kind == "mode_unresolved" for s in plan.skipped)
    assert any("실측 목록에 없음" in s.detail for s in plan.skipped)


def test_mode_resolution_tree_unread_falls_back_to_caller_width():
    records = _single_type_records(_records(), "Robe Spiider")
    modes = {"Robe Spiider": TypeModeRead(attempted=True, type_found=False)}
    plan = _plan(records, mode_reads=modes)
    assert plan.runs
    assert all(r.footprint_source == "caller_unverified" for r in plan.runs)
    assert all(r.channels_per_fixture == records[0].channels for r in plan.runs)
    assert _resolution(plan, "Robe Spiider").resolution == "tree_unread"


def test_mode_resolution_tree_unread_passes_override_unverified():
    records = _single_type_records(_records(), "Robe Spiider")
    modes = {"Robe Spiider": TypeModeRead(attempted=True, type_found=False)}
    plan = _plan(records, mode_reads=modes, mode_overrides={"Robe Spiider": "Anything"})
    assert all(r.console_mode == "Anything" for r in plan.runs)


def test_mode_resolution_csv_mode_string_never_leaks_into_runs():
    records = _records()
    csv_modes = {r.mode_label for r in records}
    assert csv_modes  # 비공허성
    plan = _plan(records)
    run_modes = {r.console_mode for r in plan.runs}
    assert not (run_modes & csv_modes)


# ---------------------------------------------------------------------------
# AC-LXSEQ-007 — occupied
# ---------------------------------------------------------------------------


def _skipped_by_fid(plan, fid: int):
    return [s for s in plan.skipped if s.fid == fid]


def test_occupied_address_row_is_skipped_with_occupant():
    records = _records()
    target = next(r for r in records if r.universe == 2 and r.address == 1)
    occupants = (Occupant(universe=2, address=1, name="기존", fixture_type="X"),)
    plan = _plan(records, occupants=occupants)

    skipped = _skipped_by_fid(plan, target.fid)
    assert [s.kind for s in skipped] == ["address_occupied"]
    assert skipped[0].occupant["address"] == "2.1"
    assert all(target.fid not in r.fids for r in plan.runs)


def test_occupied_same_type_same_start_is_already_patched():
    records = _records()
    target = next(r for r in records if r.universe == 4 and r.address == 26)
    occupants = (
        Occupant(
            universe=4,
            address=26,
            name="기존",
            fixture_type=target.fixture_type,
        ),
    )
    plan = _plan(records, occupants=occupants)

    skipped = _skipped_by_fid(plan, target.fid)
    assert [s.kind for s in skipped] == ["already_patched"]
    assert all(target.fid not in r.fids for r in plan.runs)


def test_occupied_fid_row_is_skipped():
    records = _records()
    target = records[10]
    plan = _plan(records, existing_fids=_complete_fid_read((target.fid,)))

    skipped = _skipped_by_fid(plan, target.fid)
    assert [s.kind for s in skipped] == ["fid_occupied"]
    assert skipped[0].occupied_fid == target.fid


def test_occupied_start_inside_span_collides_but_earlier_start_is_blind_spot():
    records = _records()
    inside = next(r for r in records if r.universe == 2 and r.address == 1)

    # 구간 안에서 시작 → 확정 충돌
    plan_inside = _plan(records, occupants=(Occupant(universe=2, address=inside.address + 5),))
    assert [s.kind for s in _skipped_by_fid(plan_inside, inside.fid)] == ["address_occupied"]

    # 구간 앞에서 시작 → 잡지 않는다, 대신 blind_spot 문구가 계획에 실린다
    later = next(r for r in records if r.universe == 2 and r.address > inside.address + 5)
    plan_before = _plan(records, occupants=(Occupant(universe=2, address=later.address - 5),))
    kinds = [s.kind for s in _skipped_by_fid(plan_before, later.fid)]
    assert "address_occupied" not in kinds
    assert plan_before.blind_spot


def test_occupied_rows_excluded_from_run_counts():
    records = _records()
    target = next(r for r in records if r.universe == 2 and r.address == 1)
    occupants = (Occupant(universe=2, address=1),)
    plan = _plan(records, occupants=occupants)

    skipped_fids = {s.fid for s in plan.skipped}
    assert skipped_fids  # 비공허성
    assert sum(r.count for r in plan.runs) == 86 - len(skipped_fids)
    run_fids = {fid for r in plan.runs for fid in r.fids}
    assert not (run_fids & skipped_fids)
    assert target.fid in skipped_fids


# ---------------------------------------------------------------------------
# AC-LXSEQ-008 — read_incomplete
# ---------------------------------------------------------------------------


def _truncated_inventory() -> Inventory:
    return Inventory(
        path="Root",
        child_count=10,
        enumerated_count=4,
        recovered_count=0,
        observed_count=4,
        missing_count=6,
        completeness=INCOMPLETE,
        recovery_boundary=4,
        index_domain_unknown=True,
    )


def test_read_incomplete_inventory_yields_zero_runs():
    plan = _plan(inventory=_truncated_inventory())
    assert plan.runs == ()
    assert len(plan.skipped) == 86
    assert all(s.kind == "console_read_incomplete" for s in plan.skipped)


def test_read_incomplete_fid_read_yields_zero_runs():
    partial = ExistingFidRead(attempted=True, unreadable_fids=3)
    plan = _plan(existing_fids=partial)
    assert plan.runs == ()
    assert all(s.kind == "console_read_incomplete" for s in plan.skipped)


def test_read_incomplete_unattempted_fid_read_yields_zero_runs():
    plan = _plan(existing_fids=ExistingFidRead())
    assert plan.runs == ()
    assert all(s.kind == "console_read_incomplete" for s in plan.skipped)


def test_read_incomplete_gate_reacts_to_input_non_vacuously():
    incomplete = _plan(inventory=_truncated_inventory())
    complete = _plan()
    assert incomplete.runs == ()
    assert complete.runs  # 같은 입력에서 읽기가 전수면 런이 생긴다


def test_read_incomplete_records_reason_in_plan():
    plan = _plan(inventory=_truncated_inventory())
    assert plan.console_read["complete_enough_to_judge_absence"] is False
    assert plan.console_read["reason"]


# -- 결함 D1 (M4 실기에서 드러남): 절단 ≠ 미판독 ---------------------------
#
# 실물 콘솔의 열거는 19대에서 절단된다. 86대를 패치한 뒤 재실행하면 열거는 짧지만
# **선언된 자식을 전부 관측**한다(`child_count == observed_count`, `missing_count 0`).
# 저장소 정본 `server/vwx/apply.py::console_read_caveat` 독스트링이 그 상태를
# «주의는 남기되 막지 않는다»로 정해 두었고 형제 호출부 둘이 그 규약을 지킨다.
# 이 게이트가 `completeness` 라벨만 보고 막으면, 리그가 절단선을 넘는 순간 이 툴은
# 어떤 계획도 세우지 못한다. 오프라인 가짜 콘솔은 절단되지 않아 이 분기를 가렸다.


def _index_domain_only_inventory() -> Inventory:
    """열거는 절단됐으나 선언된 자식을 **전부** 관측한 판독 — 막지 않아야 한다."""
    return Inventory(
        path="Root",
        child_count=86,
        enumerated_count=19,
        recovered_count=67,
        observed_count=86,
        missing_count=0,
        completeness=INCOMPLETE,
        recovery_boundary=19,
        index_domain_unknown=True,
    )


def test_a_truncated_but_fully_observed_read_still_plans():
    plan = _plan(inventory=_index_domain_only_inventory())

    assert plan.console_read["complete_enough_to_judge_absence"] is True
    assert len(plan.runs) == 12
    assert plan.write_count_planned == 86


def test_a_genuinely_short_read_still_blocks():
    # 비공허성 — 규약을 넓힌 것이 아니다. 못 읽은 것이 남아 있으면 여전히 막는다.
    plan = _plan(inventory=_truncated_inventory())

    assert plan.console_read["complete_enough_to_judge_absence"] is False
    assert plan.runs == ()


def test_the_gate_uses_the_repository_criterion_not_the_completeness_label():
    # 두 인벤토리는 `completeness`가 **똑같이** INCOMPLETE다. 라벨로는 가를 수 없고,
    # caveat 종류로만 갈린다 — 이 테스트가 그 잣대를 고정한다.
    blocked = _truncated_inventory()
    allowed = _index_domain_only_inventory()
    assert blocked.completeness == allowed.completeness == INCOMPLETE

    assert _plan(inventory=blocked).runs == ()
    assert _plan(inventory=allowed).runs


# ---------------------------------------------------------------------------
# AC-LXSEQ-009 — runs
# ---------------------------------------------------------------------------


def test_runs_group_mode_yields_twelve_runs_over_86_fixtures():
    plan = _plan()
    assert len(plan.runs) == 12
    assert sum(r.count for r in plan.runs) == 86
    assert all(r.name_prefix == r.group for r in plan.runs)


def test_runs_type_mode_merges_adjacent_groups_into_nine_runs():
    plan = _plan(name_prefix_mode="type")
    assert len(plan.runs) == 9
    assert sum(r.count for r in plan.runs) == 86


def test_runs_key_and_mover_d_shapes():
    plan = _plan()
    key = next(r for r in plan.runs if r.group == "KEY")
    assert key.address == "1.1"
    assert key.count == 6
    assert list(key.fids) == list(range(101, 107))
    assert key.channels_per_fixture == 12

    mover_d = next(r for r in plan.runs if r.group == "MOVER-D")
    assert mover_d.address == "3.1"
    assert mover_d.count == 8
    assert list(mover_d.fids) == list(range(521, 529))


def test_runs_fid_map_covers_every_csv_fid():
    records = _records()
    plan = _plan(records)
    assert set(plan.fid_map) == {r.fid for r in records}
    assert len(plan.fid_map) == 86
    for entry in plan.fid_map.values():
        assert 0 <= entry["run_index"] < len(plan.runs)


def test_runs_split_when_a_row_in_the_middle_is_skipped():
    records = _records()
    mover_u = [r for r in records if r.group == "MOVER-U"]
    assert len(mover_u) == 8  # 비공허성
    middle = mover_u[3]

    baseline = _plan(records)
    baseline_mover_u = [r for r in baseline.runs if r.group == "MOVER-U"]
    assert len(baseline_mover_u) == 1

    plan = _plan(records, existing_fids=_complete_fid_read((middle.fid,)))
    split = [r for r in plan.runs if r.group == "MOVER-U"]
    assert len(split) == 2
    assert sum(r.count for r in split) == 7


def test_runs_carry_only_patch_fixtures_argument_keys():
    """키 집합을 **정확히** 대조한다 — 부분집합 비교는 누락을 못 본다.

    t15 MED-3: 이 단언이 `required <= set(...)` 이던 동안 `channels_per_fixture`
    누락이 그대로 통과했다. 빠진 인자 하나에 tree_unread 런이 0대를 만들고 파일
    전체가 그 런에서 멈췄는데, 테스트는 내내 초록이었다.
    """
    plan = _plan()
    expected = {
        "console_type",
        "address",
        "count",
        "fids",
        "name_prefix",
        "channels_per_fixture",
    }
    for run in plan.runs:
        keys = set(run.as_tool_arguments())
        assert keys - {"console_mode"} == expected
        assert ("console_mode" in keys) is (run.console_mode is not None)


# ---------------------------------------------------------------------------
# AC-LXSEQ-010 — no_write_surface
# ---------------------------------------------------------------------------

_FORBIDDEN_IMPORTS = (
    "server.bridge",
    "pythonosc",
    "server.vwx.luagen",
    "server.vwx.stagedpatch",
    "server.deploy",
)
_FORBIDDEN_NAMES = (
    "execution_port",
    "deploy_pipeline",
    "run_commands",
    "deploy_plugin",
    "AddFixtures",
    "ChangeDestination",
)


def test_no_write_surface_in_lxseq_module():
    sources = sorted(Path("server/lxseq").glob("*.py"))
    assert len(sources) >= 2  # 비공허성

    import_violations: list[str] = []
    name_violations: list[str] = []
    string_violations: list[str] = []

    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in _FORBIDDEN_IMPORTS):
                        import_violations.append(f"{source}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(module.startswith(p) for p in _FORBIDDEN_IMPORTS):
                    import_violations.append(f"{source}: {module}")
                # `from server.vwx import luagen` 형태 — module은 `server.vwx`라
                # 위 검사를 통과한다. 실제로 끌어오는 이름까지 합쳐 봐야 한다.
                for alias in node.names:
                    qualified = f"{module}.{alias.name}" if module else alias.name
                    if any(qualified.startswith(p) for p in _FORBIDDEN_IMPORTS):
                        import_violations.append(f"{source}: {qualified}")
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
                name_violations.append(f"{source}: {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_NAMES:
                name_violations.append(f"{source}: {node.attr}")
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and "Plugin '" in node.value
            ):
                string_violations.append(f"{source}: Plugin '")

    assert import_violations == []
    assert name_violations == []
    assert string_violations == []


# ---------------------------------------------------------------------------
# PR #72 리뷰 결함 — 매퍼 폭 산정 (D3 · D4)
#
# 두 결함 모두 「매퍼가 세운 계획값」과 「콘솔이 실제로 놓을 자리」가 어긋나는 축에
# 있다. 기준 리그 86대는 타입마다 폭이 하나여서 이 갈래를 지나가지 않는다 —
# 그래서 아래 입력은 픽스처가 아니라 손으로 짠 최소 CSV 다.
# ---------------------------------------------------------------------------


def _csv(rows) -> str:
    """(타입, 모드라벨, 채널수, 유니버스, 시작주소) 행들을 9열 CSV 로 만든다.

    `AddrRange` 는 파서가 숫자까지 대조하므로(`addr_range_mismatch`) 여기서 계산해
    맞춰 준다 — 손으로 적으면 검증 대상이 아니라 파서 거부를 시험하게 된다.
    """
    header = "FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position"
    lines = [header]
    for fid, (ftype, mode_label, channels, universe, address) in enumerate(rows, start=1):
        end = address + channels - 1
        lines.append(
            f"{fid},KEY,{ftype},{mode_label},{channels},{universe},{address},"
            f"{universe}.{address:03d}–{end:03d},무대"
        )
    return "\n".join(lines) + "\n"


def _mixed_width_records():
    """한 타입(`Aura`)이 12ch 과 25ch 두 폭으로 섞여 오는 3행."""
    return parse_patch_csv(
        _csv(
            (
                ("Aura", "Basic 12ch", 12, 1, 1),
                ("Aura", "Extended 25ch", 25, 1, 13),
                ("Aura", "Basic 12ch", 12, 1, 38),
            )
        )
    ).records


def _two_width_modes() -> dict[str, TypeModeRead]:
    return {
        "Aura": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="Basic 12ch", width=12, slot=1),
                ModeChoice(name="Extended 25ch", width=25, slot=2),
            ),
        )
    }


def test_mixed_width_rows_of_one_type_keep_their_csv_addresses():
    """D3 — 모드 확정이 타입당 1회면 뒤 행들이 런 머리 폭으로 밀린다."""
    records = _mixed_width_records()
    plan = _plan(records, mode_reads=_two_width_modes())

    assert plan.skipped == ()  # 조용히 틀리는 결함이라 건너뜀은 0 이어야 한다
    csv_addresses = {r.fid: f"{r.universe}.{r.address}" for r in records}
    planned = {fid: entry["address"] for fid, entry in plan.fid_map.items()}
    assert planned == csv_addresses


def test_mixed_width_rows_of_one_type_do_not_merge_into_one_run():
    """D3 — 폭이 다른 행이 한 런으로 뭉치면 런 폭이 뒤 행에도 적용된다."""
    records = _mixed_width_records()
    plan = _plan(records, mode_reads=_two_width_modes())

    assert len(plan.runs) >= 2
    for run in plan.runs:
        widths = {records[fid - 1].channels for fid in run.fids}
        assert widths == {run.channels_per_fixture}


def _override_records():
    """CSV 는 39ch 라고 하는데 콘솔 실측 모드는 25ch 하나뿐 — override 의 정상 상황."""
    return parse_patch_csv(
        _csv(
            (
                ("MegaPointe", "Mode 1 39ch", 39, 1, 1),
                ("MegaPointe", "Mode 1 39ch", 39, 1, 40),
            )
        )
    ).records


def _narrow_mode() -> dict[str, TypeModeRead]:
    return {
        "MegaPointe": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name="Mode 2 25ch", width=25, slot=1),),
        )
    }


def test_override_adopts_the_measured_width_not_the_csv_width():
    """D4 — override 분기가 이름만 찾고 폭을 버리면 계획이 자기모순이 된다."""
    records = _override_records()
    plan = _plan(
        records,
        mode_reads=_narrow_mode(),
        mode_overrides={"MegaPointe": "Mode 2 25ch"},
    )

    assert plan.runs
    assert all(r.console_mode == "Mode 2 25ch" for r in plan.runs)
    # 25채널 모드라고 말하면서 39채널 폭으로 자리를 잡으면 안 된다.
    assert all(r.channels_per_fixture == 25 for r in plan.runs)


def test_override_keeps_the_csv_address_instead_of_packing_at_the_measured_stride():
    """D4 — 폭이 좁아지면 CSV 자리를 지키려고 런이 갈려야 한다.

    한 런으로 묶으면 콘솔이 보폭 25 로 늘어놓아 둘째 대가 CSV 의 `1.40` 이 아니라
    `1.26` 에 간다. 패치 CSV 를 수입하는 목적은 조명감독이 정한 주소를 옮기는 것이니
    당겨 놓고 「당겼다」고 보고하는 대신 당기지 않는다.
    """
    records = _override_records()
    plan = _plan(
        records,
        mode_reads=_narrow_mode(),
        mode_overrides={"MegaPointe": "Mode 2 25ch"},
    )

    assert plan.fid_map[2]["address"] == "1.40"
    csv_addresses = {r.fid: f"{r.universe}.{r.address}" for r in records}
    assert {fid: e["address"] for fid, e in plan.fid_map.items()} == csv_addresses
    assert len(plan.runs) == 2  # 자리를 지키려면 갈리는 수밖에 없다


def test_override_occupancy_is_checked_at_the_address_actually_used():
    """D4 ③ — 점유 검사가 CSV 폭으로 돌면 실제로 쓰이는 자리는 한 번도 안 본다.

    자리를 상수로 박지 않는다. 먼저 빈 콘솔에 계획을 세워 **매퍼가 스스로 고른**
    자리를 읽고, 바로 그 자리에 점유를 놓아 다시 계획한다 — 어떤 수정안을 택하든
    「계획이 쓰겠다고 한 자리는 점유 검사를 거쳤다」는 불변식만 검사한다.
    """
    kwargs = {
        "mode_reads": _narrow_mode(),
        "mode_overrides": {"MegaPointe": "Mode 2 25ch"},
    }
    records = _override_records()
    clean = _plan(records, **kwargs)
    target = clean.fid_map[2]["address"]
    assert clean.fid_map[2]["run_index"] is not None  # 비공허성 — 빈 콘솔에선 실제로 계획된다

    universe, address = (int(part) for part in target.split("."))
    occupants = (Occupant(universe=universe, address=address, name="기존", fixture_type="X"),)
    blocked = _plan(_override_records(), occupants=occupants, **kwargs)

    planned = {
        entry["address"] for entry in blocked.fid_map.values() if entry["run_index"] is not None
    }
    assert target not in planned


def test_tree_unread_mixed_widths_still_keep_their_csv_addresses():
    """D3 — 모드 이름이 없을 때는 폭만이 런의 유일한 구분자다.

    모드 트리를 못 읽으면 `resolution` 도 `console_mode` 도 행마다 같다. 런 경계가
    폭을 보지 않으면 12ch 과 25ch 이 한 런으로 뭉치고, 런 폭은 머리 행 값이 되어
    뒤 행이 CSV 가 지정한 자리에서 밀린다 — 이름이 갈라 주던 다른 갈래와 달리
    여기서는 폭을 빼면 그대로 통과해 버린다.
    """
    records = _mixed_width_records()
    plan = _plan(records, mode_reads={"Aura": TypeModeRead(attempted=True, type_found=False)})

    assert all(r.footprint_source == "caller_unverified" for r in plan.runs)  # 비공허성
    csv_addresses = {r.fid: f"{r.universe}.{r.address}" for r in records}
    assert {fid: e["address"] for fid, e in plan.fid_map.items()} == csv_addresses
    assert len(plan.runs) >= 2


def _wide_mode(width: int) -> dict[str, TypeModeRead]:
    return {
        "MegaPointe": TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name=f"Mode 0 {width}ch", width=width, slot=1),),
        )
    }


def test_plan_overlap_created_by_a_wider_measured_mode_is_rejected():
    """D4 ③ 나머지 절반 — 계획이 자기 자신과 겹치는 것은 점유 검사가 못 본다.

    CSV 폭 39 로는 `1.1` 과 `1.40` 이 안 겹치지만, 확정된 모드가 50채널이면 발자국이
    `1..50` 과 `40..89` 로 넓어져 `40..50` 이 겹친다. 콘솔 기존 점유는 비어 있으므로
    점유 검사는 아무 말도 하지 않는다 — 이 축을 따로 보지 않으면 조용히 통과한다.
    """
    plan = _plan(
        _override_records(),
        mode_reads=_wide_mode(50),
        mode_overrides={"MegaPointe": "Mode 0 50ch"},
    )

    assert plan.runs == ()
    assert [s.kind for s in plan.skipped] == ["address_overlap_in_plan"] * 2
    assert all("겹친다" in s.detail for s in plan.skipped)


def test_a_wider_measured_mode_that_still_fits_is_planned_normally():
    """비공허성 — 넓어졌다는 이유만으로 거부하면 위 검사는 아무 뜻이 없다.

    같은 50채널이라도 CSV 자리가 충분히 떨어져 있으면(`1.1` · `1.60`) 겹치지 않는다.
    이 경우까지 거부되면 위 테스트는 「폭이 넓으면 거부」를 검사하는 것이 된다.
    """
    records = parse_patch_csv(
        _csv(
            (
                ("MegaPointe", "Mode 1 39ch", 39, 1, 1),
                ("MegaPointe", "Mode 1 39ch", 39, 1, 60),
            )
        )
    ).records
    plan = _plan(
        records,
        mode_reads=_wide_mode(50),
        mode_overrides={"MegaPointe": "Mode 0 50ch"},
    )

    assert plan.skipped == ()
    assert len(plan.runs) == 2
    assert {fid: e["address"] for fid, e in plan.fid_map.items()} == {1: "1.1", 2: "1.60"}


def test_occupancy_uses_the_measured_width_not_the_csv_width():
    """D4 ③ 전반부 — 점유 검사의 발자국은 콘솔이 실제로 밟을 폭이어야 한다.

    CSV 는 39채널이라 하고 확정된 모드는 25채널이다. 이 대는 `1.1` 에서 `1..25` 만
    쓰므로 `1.30` 의 기존 장비와 다투지 않는다. CSV 폭으로 검사하면 발자국이 `1..39`
    가 되어 다투지 않는 자리를 다툰다고 보고, 멀쩡한 행을 건너뛴다.

    **의도된 선택임을 밝혀 둔다.** 이렇게 하면 콘솔의 겹침 판정이 물리 장비의 실제
    폭(39)보다 느슨해진다 — 콘솔은 안 겹친다는데 실제 리그에서는 겹칠 수 있다.
    override 를 쓰는 순간 감수하는 것이며, 이 커밋의 범위 밖이다(§E.2 잔여위험).
    검사 기준을 콘솔 모델에 맞춘 것이지, 물리 폭을 잊은 것이 아니다.
    """
    records = parse_patch_csv(_csv((("MegaPointe", "Mode 1 39ch", 39, 1, 1),))).records
    occupants = (Occupant(universe=1, address=30, name="기존", fixture_type="X"),)
    plan = _plan(
        records,
        mode_reads=_narrow_mode(),
        mode_overrides={"MegaPointe": "Mode 2 25ch"},
        occupants=occupants,
    )

    assert plan.skipped == ()
    assert [(r.address, r.channels_per_fixture) for r in plan.runs] == [("1.1", 25)]


def _unmeasured_mode():
    """모드 이름은 답했는데 폭 속성은 못 답한 콘솔.

    지어낸 상태가 아니다. read_type_mode_widths 가 속성 읽기 예외, ok False,
    정수 아님, 1 미만, 네 갈래로 width=None 을 낸다.
    """
    return dict(
        MegaPointe=TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name="Mode 2 25ch", width=None, slot=1),),
        )
    )


def _ceiling_wide_mode():
    """CSV 8ch 인데 콘솔 실측은 32ch. override 의 정상 상황이고 폭이 넓어진다."""
    return dict(
        MegaPointe=TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name="Wide 32ch", width=32, slot=1),),
        )
    )


def _near_ceiling_records():
    """1.500 에서 시작하는 8채널 한 행. CSV 폭으로는 507 까지라 파서를 통과한다."""
    return parse_patch_csv(_csv((("MegaPointe", "Basic 8ch", 8, 1, 500),))).records


def test_a_widened_row_that_overruns_the_universe_is_not_planned():
    """t15 HIGH-1. 실측 폭이 512 를 넘기면 계획에서 빠져야 한다.

    실측: 계획서는 1.500 이라 하고 콘솔은 2.1 에 만들었다. 자리를 옮긴 사실이
    아무 데도 남지 않아, 쓰기 경로가 그대로 다음 유니버스에 심고 created 를 냈다.
    """
    plan = _plan(
        _near_ceiling_records(),
        mode_reads=_ceiling_wide_mode(),
        mode_overrides=dict(MegaPointe="Wide 32ch"),
    )

    assert plan.runs == ()
    assert [s.kind for s in plan.skipped] == ["address_unfittable"]
    assert plan.write_count_planned == 0


def test_an_occupant_inside_the_widened_span_is_seen():
    """t15 HIGH-1 거짓 음성. 진짜 발자국 1.500~1.531 안의 장비를 놓치면 안 된다."""
    squatter = Occupant(universe=1, address=505, name="이미 여기 있음", fixture_type="X")

    plan = _plan(
        _near_ceiling_records(),
        mode_reads=_ceiling_wide_mode(),
        mode_overrides=dict(MegaPointe="Wide 32ch"),
        occupants=(squatter,),
    )

    assert plan.runs == ()
    assert plan.skipped[0].occupant is not None
    assert plan.skipped[0].occupant["address"] == "1.505"


def test_an_occupant_in_another_universe_is_not_blamed():
    """t15 HIGH-1 거짓 양성. 감긴 자리로 검사하면 남의 선반 장비를 범인으로 지목한다."""
    elsewhere = Occupant(universe=2, address=1, name="다른 선반", fixture_type="X")

    plan = _plan(
        _near_ceiling_records(),
        mode_reads=_ceiling_wide_mode(),
        mode_overrides=dict(MegaPointe="Wide 32ch"),
        occupants=(elsewhere,),
    )

    assert plan.skipped[0].kind == "address_unfittable"
    assert plan.skipped[0].occupant is None


def test_a_row_that_fits_is_still_planned():
    """대조군. 넓어져도 천장 안이면 그대로 간다. 새 천장을 만든 게 아니다."""
    records = parse_patch_csv(_csv((("MegaPointe", "Basic 8ch", 8, 1, 1),))).records

    plan = _plan(
        records, mode_reads=_ceiling_wide_mode(), mode_overrides=dict(MegaPointe="Wide 32ch")
    )

    assert [(r.address, r.channels_per_fixture) for r in plan.runs] == [("1.1", 32)]


def test_an_override_onto_an_unmeasured_width_is_not_called_resolved():
    """t15 HIGH-2. 폭을 못 잰 모드를 override 로 집으면 TypeError 로 죽었다.

    resolution="resolved" 인데 channels=None 이라는 상태가 만들어졌다. 폭을 재지
    못했으면 확정이 아니다. override 없는 갈래와 같은 답을 내야 한다.
    """
    plan = _plan(
        _override_records(),
        mode_reads=_unmeasured_mode(),
        mode_overrides=dict(MegaPointe="Mode 2 25ch"),
    )

    assert plan.runs == ()
    assert [s.kind for s in plan.skipped] == ["mode_unresolved", "mode_unresolved"]


def test_the_branch_without_an_override_already_bows_out():
    """대조군. 이쪽은 c.width == channels 가 None 과 안 맞아 우연히 보호됐다."""
    plan = _plan(_override_records(), mode_reads=_unmeasured_mode())

    assert plan.runs == ()
    assert [s.kind for s in plan.skipped] == ["mode_unresolved", "mode_unresolved"]


def test_a_resolution_can_never_claim_a_width_it_does_not_have():
    """t15 사이트 #4. 크래시만 막으면 조용한 거짓 출처로 바뀐다.

    실측: PatchRun(channels_per_fixture=None, footprint_source='console_measured')
    가 예외 없이 나갔다. 폭을 못 쟀는데 콘솔 실측이라고 적어 내보낸 것이다.
    폭 없는 확정을 만들 수 없게 막는다.
    """
    with pytest.raises(ValueError):
        ModeResolution(
            console_type="MegaPointe",
            channels=None,
            resolution="resolved",
            console_mode="Mode 2 25ch",
            resolved_by="override",
        )
