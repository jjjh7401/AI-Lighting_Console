"""t335 — 무엇이 이 행의 모드를 풀었는지가 보고에 실린다.

t333 이 24행을 풀었을 때 감독이 볼 수 있었던 것은 `already_patched` 62 → 86 이라는
**결과**뿐이었다. 무엇이 풀었는지(`width_unique` / `label_token` / `override` /
`console_mode`)는 어디에도 실리지 않았다 — `mode_resolutions` 는 매퍼 밖으로 나가지
않는다. 그래서 실기 관측은 결과를 증언했고 메커니즘은 단위 시험의 단언이 유일한
증거였다(`.moai/reports/t333/verdict.md` §4-2).

**행마다 싣는다, 키마다 싣지 않는다.** `mode_resolutions` 는 `(타입, 폭, 라벨)`
키마다 하나인데 t333 의 해석은 **행 단위**다. 같은 키의 행들이 서로 다른 자리에
앉아 일부만 임자가 있을 수 있고, 그 표에는 먼저 도달한 해석 하나만 남는다. 그 표를
그대로 실으면 일부만 풀린 키가 「풀렸다」로 보인다 — 관측성을 붙이려다 조용한 오답을
새로 만드는 길이다. 아래 `test_a_key_whose_rows_split_reports_per_row` 가 그 갈림을
고정한다.

모드가 확정되기 **전에** 걸러진 행(`type_unresolved` · `mode_unresolved`)에는 보고할
해석이 없다. 그 행의 `resolved_by` 는 `None` 이고, 그것은 「못 풀었다」의 정직한
표기다 — 빈 문자열이나 `"unknown"` 으로 채우면 「풀렸는데 이름을 잃었다」와 구별되지
않는다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq.mapper import build_import_plan
from server.lxseq.parser import parse_patch_csv
from server.prechk.inventory import COMPLETE, FixtureRecord, Inventory
from server.prechk.mode_read import ModeChoice, TypeModeRead
from server.vwx.addressfit import Occupant
from server.vwx.patchplan import ExistingFidRead

FIXTURE_PATH = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")
CSV_TYPE = "Robe Spiider"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _records():
    records = parse_patch_csv(FIXTURE_PATH.read_text(encoding="utf-8")).records
    subset = [r for r in records if r.fixture_type == CSV_TYPE]
    assert subset, f"{CSV_TYPE} 행이 정본 fixture 에서 사라졌다 — 시험이 공허해진다"
    # 아래 「키가 갈리는」 시험은 이 타입에 행이 둘 이상이어야 성립한다.
    assert len(subset) >= 2, "이 타입의 행이 하나면 행별/키별 구별을 만들 수 없다"
    return subset


def _complete_fid_read() -> ExistingFidRead:
    return ExistingFidRead(
        fids=(),
        child_count=0,
        enumerated_count=0,
        unseen=0,
        unreadable_fids=0,
        unusable_rows=0,
        unparsable_rows=0,
        attempted=True,
    )


def _inventory(fixtures: tuple[FixtureRecord, ...]) -> Inventory:
    return Inventory(
        path="Root",
        child_count=len(fixtures),
        enumerated_count=len(fixtures),
        recovered_count=0,
        observed_count=len(fixtures),
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=fixtures,
    )


def _seat(record, mode_text: str, *, fixture_type: str = CSV_TYPE, slot: int = 1):
    return FixtureRecord(
        slot=slot,
        name=f"SP {record.fid}",
        patch_raw=f"{record.universe}.{record.address:03d}",
        fixture_type=fixture_type,
        mode=mode_text,
    )


def _occupant(record, *, fixture_type: str = CSV_TYPE) -> Occupant:
    return Occupant(
        universe=record.universe,
        address=record.address,
        name=f"SP {record.fid}",
        fixture_type=fixture_type,
    )


def _one_mode(channels: int) -> dict[str, TypeModeRead]:
    return {
        CSV_TYPE: TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(ModeChoice(name="Only", width=channels, slot=1),),
        )
    }


def _two_same_width_modes(channels: int) -> dict[str, TypeModeRead]:
    return {
        CSV_TYPE: TypeModeRead(
            attempted=True,
            type_found=True,
            modes=(
                ModeChoice(name="A", width=channels, slot=1),
                ModeChoice(name="B", width=channels, slot=2),
            ),
        )
    }


def _present(name: str | None) -> dict:
    status = "present" if name is not None else "absent"
    return {"status": status, "resolved": name, "candidates": []}


def _plan(records, **overrides):
    kwargs = {
        "records": records,
        "type_resolutions": {CSV_TYPE: _present(CSV_TYPE)},
        "mode_reads": _one_mode(records[0].channels),
        "inventory": _inventory(()),
        "occupants": (),
        "existing_fids": _complete_fid_read(),
    }
    kwargs.update(overrides)
    return build_import_plan(**kwargs)


def _by_fid(rows):
    return {row.fid: row for row in rows}


# ---------------------------------------------------------------------------
# 런에 실린다
# ---------------------------------------------------------------------------


def test_a_run_carries_what_resolved_its_mode():
    records = _records()
    plan = _plan(records)
    assert plan.runs, "이 시험은 런이 있어야 성립한다"
    assert all(run.resolved_by == "width_unique" for run in plan.runs)


def test_a_run_resolved_by_override_says_so():
    records = _records()
    channels = records[0].channels
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        mode_overrides={CSV_TYPE: "B"},
    )
    assert plan.runs
    assert all(run.resolved_by == "override" for run in plan.runs)
    assert all(run.console_mode == "B" for run in plan.runs)


# ---------------------------------------------------------------------------
# 건너뛴 행에 실린다 — 이게 t333 이 못 보여 준 자리다
# ---------------------------------------------------------------------------


def test_an_already_patched_row_says_what_resolved_it():
    """t333 의 62/24 분할이 보이는 자리."""
    records = _records()
    channels = records[0].channels
    seats = tuple(_seat(r, "2 B", slot=i + 1) for i, r in enumerate(records))
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(seats),
        occupants=tuple(_occupant(r) for r in records),
    )
    assert all(row.kind == "already_patched" for row in plan.skipped)
    assert all(row.resolved_by == "console_mode" for row in plan.skipped)


def test_a_row_skipped_before_the_mode_was_decided_reports_none():
    """모드를 못 풀었으면 보고할 해석이 없다 — `None` 이 정직한 표기다.

    빈 문자열이나 `"unknown"` 으로 채우면 「풀렸는데 이름을 잃었다」와 구별되지
    않는다. 두 상태는 감독이 취할 다음 행동이 다르다.
    """
    records = _records()
    channels = records[0].channels
    plan = _plan(records, mode_reads=_two_same_width_modes(channels))
    assert all(row.kind == "mode_unresolved" for row in plan.skipped)
    assert all(row.resolved_by is None for row in plan.skipped)


def test_a_type_unresolved_row_reports_none():
    records = _records()
    plan = _plan(
        records,
        type_resolutions={CSV_TYPE: _present(None)},
    )
    assert all(row.kind == "type_unresolved" for row in plan.skipped)
    assert all(row.resolved_by is None for row in plan.skipped)


# ---------------------------------------------------------------------------
# 🔴 핵심 — 키가 아니라 행이다
# ---------------------------------------------------------------------------


def test_a_key_whose_rows_split_reports_per_row():
    """같은 (타입, 폭, 라벨) 키의 행이 갈리면 행마다 다르게 보고해야 한다.

    이 쇼의 이 타입은 행 전부가 같은 키를 쓴다. 임자를 **첫 행에만** 두면
    그 행은 `console_mode` 로 풀리고 나머지는 못 풀린다. `mode_resolutions`
    표에는 먼저 도달한 해석 하나만 남으므로, 그 표를 보고에 그대로 실었다면
    나머지 행까지 「풀렸다」로 보였을 것이다.
    """
    records = _records()
    channels = records[0].channels
    first, rest = records[0], records[1:]
    assert rest, "갈림을 만들 나머지 행이 없다"

    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory((_seat(first, "2 B"),)),
        occupants=(_occupant(first),),
    )

    rows = _by_fid(plan.skipped)
    assert rows[first.fid].kind == "already_patched"
    assert rows[first.fid].resolved_by == "console_mode"

    for record in rest:
        assert rows[record.fid].kind == "mode_unresolved", record.fid
        assert rows[record.fid].resolved_by is None, record.fid

    # 비공허성 — 두 갈래가 실제로 둘 다 나왔는가.
    kinds = {row.kind for row in plan.skipped}
    assert kinds == {"already_patched", "mode_unresolved"}
    reported = {row.resolved_by for row in plan.skipped}
    assert reported == {"console_mode", None}


def test_the_key_table_alone_would_have_been_misleading():
    """위 시험의 전제를 명시한다 — 키 표는 갈림을 표현할 수 없다.

    이 단언이 깨지는 날은 키 표가 행별 정보를 갖게 된 날이고, 그때는 위
    시험의 이유(「표를 그대로 실으면 오답」)를 다시 검토해야 한다.
    """
    records = _records()
    channels = records[0].channels
    first = records[0]
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory((_seat(first, "2 B"),)),
        occupants=(_occupant(first),),
    )
    keys = [key for key in plan.mode_resolutions if key[0] == CSV_TYPE]
    # 행은 여럿인데 키는 하나다 — 표 하나로는 갈림을 담을 자리가 없다.
    assert len(keys) == 1
    assert len(plan.skipped) > 1


# ---------------------------------------------------------------------------
# 집계 — 먼저 읽는 것은 이쪽이다
# ---------------------------------------------------------------------------


def test_the_plan_aggregates_resolved_by():
    records = _records()
    channels = records[0].channels
    first, rest = records[0], records[1:]
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory((_seat(first, "2 B"),)),
        occupants=(_occupant(first),),
    )
    assert plan.resolved_by_counts == {"console_mode": 1, None: len(rest)}


def test_the_aggregate_counts_runs_and_skipped_together():
    """행은 런으로도 건너뛴 행으로도 끝난다 — 집계가 한쪽만 세면 합이 안 맞는다."""
    records = _records()
    plan = _plan(records)
    assert plan.runs
    assert plan.skipped == ()
    total = sum(plan.resolved_by_counts.values())
    assert total == len(records)
    assert plan.resolved_by_counts == {"width_unique": len(records)}


def test_the_aggregate_total_always_equals_the_row_count():
    """어떤 갈래 조합에서도 합은 행 수다 — 세지 못한 행이 생기면 여기서 깨진다."""
    records = _records()
    channels = records[0].channels
    first = records[0]
    for kwargs in (
        {},
        {"mode_reads": _two_same_width_modes(channels)},
        {
            "mode_reads": _two_same_width_modes(channels),
            "inventory": _inventory((_seat(first, "2 B"),)),
            "occupants": (_occupant(first),),
        },
        {
            "mode_reads": _two_same_width_modes(channels),
            "mode_overrides": {CSV_TYPE: "A"},
        },
        {"type_resolutions": {CSV_TYPE: _present(None)}},
    ):
        plan = _plan(records, **kwargs)
        assert sum(plan.resolved_by_counts.values()) == len(records), kwargs


@pytest.mark.parametrize("mode_text", ["9 Z", "B", None])
def test_an_unresolvable_seat_leaves_the_row_uncounted_as_resolved(mode_text):
    records = _records()
    channels = records[0].channels
    seats = tuple(_seat(r, mode_text, slot=i + 1) for i, r in enumerate(records))
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(seats),
        occupants=tuple(_occupant(r) for r in records),
    )
    assert plan.resolved_by_counts == {None: len(records)}


# ---------------------------------------------------------------------------
# 🔴 회귀 — t333 이 심은 캐시 누출
# ---------------------------------------------------------------------------


def test_a_seat_resolution_never_leaks_to_a_row_with_no_seat():
    """t333 회귀. 한 행의 자리 판독이 같은 키의 다른 행을 확정해서는 안 된다.

    t333 은 자리 판독 결과를 `mode_resolutions` 키 표에 써 넣었다. 그러면 같은 키의
    **다음 행**이 그 값을 물려받아, 자기 자리에는 임자가 없는데도 그 모드로 확정되고
    그대로 쓰기 계획이 된다. 이 앱에 실행 취소는 없으므로 되돌릴 수 없는 쓰기다.

    t333 회차에 드러나지 않은 이유는 그 쇼의 24행이 전부 임자를 가져, 물려받은 값과
    실측값이 우연히 같았기 때문이다. 임자가 **일부에만** 있는 이 배치가 그 우연을
    제거한다.

    단언의 핵심은 「나머지 행이 런이 되지 않는다」다 — 해석이 새면 그 행들은 건너뛴
    행이 아니라 **런**으로 나타나고, 그것이 쓰기로 이어지는 경로다.
    """
    records = _records()
    channels = records[0].channels
    first, rest = records[0], records[1:]
    assert rest

    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory((_seat(first, "2 B"),)),
        occupants=(_occupant(first),),
    )

    assert plan.runs == (), "임자 없는 행이 런이 되었다 — 해석이 키를 통해 새고 있다"
    assert plan.write_count_planned == 0
    leaked = [row.fid for row in plan.skipped if row.fid != first.fid and row.resolved_by]
    assert leaked == [], f"임자 없는 행이 해석을 물려받았다: {leaked}"


def test_the_key_table_stays_at_the_library_read_verdict():
    """키 표는 라이브러리 판독의 결과로 남는다 — 자리 판독으로 덮지 않는다.

    덮는 순간 위 시험의 누출이 생긴다. 표가 `unresolved` 인 것은 거짓이 아니다:
    라이브러리는 실제로 못 좁혔고, 좁힌 것은 행마다의 자리 판독이다.
    """
    records = _records()
    channels = records[0].channels
    seats = tuple(_seat(r, "2 B", slot=i + 1) for i, r in enumerate(records))
    plan = _plan(
        records,
        mode_reads=_two_same_width_modes(channels),
        inventory=_inventory(seats),
        occupants=tuple(_occupant(r) for r in records),
    )
    keys = [r for key, r in plan.mode_resolutions.items() if key[0] == CSV_TYPE]
    assert keys
    assert all(r.resolution == "unresolved" for r in keys)
    # 그런데 행은 전부 풀렸다 — 표와 행이 다른 것을 말하는 것이 설계다.
    assert all(row.resolved_by == "console_mode" for row in plan.skipped)


def test_every_run_reports_a_resolution_from_the_vocabulary():
    """런에 해석이 실렸는지, 그리고 그 값이 어휘 안인지.

    ⚠️ 이 시험은 **한 런에 해석이 섞이지 않는다**를 증명하지 않는다. 섞임을 만들려면
    같은 타입에서 CSV 라벨이 다른 두 키가 같은 콘솔 모드·같은 폭에 닿아야 하는데,
    정본 fixture 에는 타입마다 라벨이 하나뿐이라 이 자리에서 그 배치를 만들 수 없다.
    섞임을 막는 것은 `boundary_key` 에 `resolved_by` 를 넣은 것이고, 그것은 코드
    주석으로만 지켜진다 — 미검증으로 남는다.

    여기서 고정하는 것은 더 좁다: 런이 해석을 **잃지 않는다**(None 이 아니다).
    필드를 배선하지 않은 채 런을 만들면 여기서 걸린다.
    """
    records = _records()
    plan = _plan(records)
    assert plan.runs
    vocabulary = {"width_unique", "label_token", "override", "console_mode"}
    for run in plan.runs:
        assert run.resolved_by in vocabulary, run.index
