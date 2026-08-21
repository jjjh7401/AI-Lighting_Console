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

from server.lxseq.mapper import build_import_plan
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
    assert len(distinct) == 8  # 비공허성 — 8종이 실제로 있다
    plan = _plan(records)
    assert sorted(plan.types_requested) == sorted(distinct)
    assert len(plan.types_requested) == 8


# ---------------------------------------------------------------------------
# AC-LXSEQ-006 — mode_resolution
# ---------------------------------------------------------------------------


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
    assert plan.mode_resolutions["Robe Spiider"].resolution == "resolved"
    assert plan.mode_resolutions["Robe Spiider"].resolved_by == "width_unique"


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
    assert plan.mode_resolutions["Robe Spiider"].resolved_by == "label_token"


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
    assert plan.mode_resolutions["Robe Spiider"].resolution == "unresolved"
    assert len(plan.mode_resolutions["Robe Spiider"].measured_modes) == 2


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
    assert plan.mode_resolutions["Robe Spiider"].resolved_by == "override"


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
    assert plan.mode_resolutions["Robe Spiider"].resolution == "tree_unread"


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
    plan = _plan()
    required = {"console_type", "address", "count", "fids", "name_prefix"}
    for run in plan.runs:
        assert required <= set(run.as_tool_arguments())


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
