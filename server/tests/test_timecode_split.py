"""줄 수에 고정 상한을 두지 않는다 — 한 타임코드의 잰 트랙 수를 넘으면 다음 타임코드에 나눠 담는다.

감독 지시(2026-10-18, 카드 WT-track-model PR2): 「무대마다 장비 종류가 수십 가지, 수량이 수백 대」.
8 → 16 으로 올려도 고정 상한이면 같은 결함이다. 기준은 **줄(콘솔 그룹) 수**이고 장비 대수가
아니다. 나눌 타임코드 번호는 비어 있는 것만 쓰고, 쓰지 않을 번호(감독 쇼의 TC3·4)는 데이터
파일(`beat_grid_data/measured_console.yaml` 의 ``reserved_timecodes``)에서 온다.
"""

from __future__ import annotations

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_emit import MEASURED_MAX_TIMECODE_TRACKS, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import read_m1_probe_results_from_path
from server.design.timecode_split import (
    RESERVED_TIMECODES,
    pick_extra_timecode_numbers,
    split_rows_by_timecode,
)
from server.tests.test_beat_grid_emit_t549 import _TIMING, default_progress_md_path


def _rows(count: int) -> list[dict]:
    base = list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])
    return [dict(base[i % 2], group_name=f"ROW-{i + 1}") for i in range(count)]


def test_reserved_timecodes_come_from_the_data_file() -> None:
    assert frozenset({3, 4}) == RESERVED_TIMECODES


def test_rows_are_split_in_grid_order_by_the_measured_track_count() -> None:
    names = [f"R{i}" for i in range(1, 31)]
    chunks = split_rows_by_timecode(names, per_timecode=16)
    assert chunks == [names[:16], names[16:]]
    assert split_rows_by_timecode(names[:16], per_timecode=16) == [names[:16]]
    assert split_rows_by_timecode([], per_timecode=16) == []


def test_extra_numbers_skip_used_and_reserved_and_reuse_recorded_first() -> None:
    # 5 가 첫 타임코드, 6·7 은 남이 쓰는 중, 3·4 는 쓰지 않을 번호.
    assert pick_extra_timecode_numbers(5, needed=2, used={1, 2, 3, 4, 5, 6, 7}) == ([8, 9], None)
    # 기록된(앱이 만든) 추가 타임코드는 그대로 다시 쓴다.
    assert pick_extra_timecode_numbers(5, needed=2, used={5, 6, 20}, recorded=[20]) == (
        [20, 7],
        None,
    )
    # 첫 타임코드보다 작은 빈 번호(예: 1)는 고르지 않는다 — 곡의 타임코드가 번호순으로 이어진다.
    assert pick_extra_timecode_numbers(2, needed=1, used={2})[0] == [5]


def test_thirty_rows_emit_two_timecodes_and_every_row_is_assigned() -> None:
    rows = _rows(30)
    names = [r["group_name"] for r in rows]
    chunks = split_rows_by_timecode(names, per_timecode=MEASURED_MAX_TIMECODE_TRACKS)
    numbers = [5, *pick_extra_timecode_numbers(5, needed=len(chunks) - 1, used={1, 2, 3, 4, 5})[0]]
    timecode_numbers = {name: numbers[k] for k, chunk in enumerate(chunks) for name in chunk}
    result = emit_beat_grid_write_bundle(
        rows,
        timing=_TIMING,
        sequence_numbers={name: 300 + i for i, name in enumerate(names)},
        timecode_numbers=timecode_numbers,
        dimmer_attributes={name: ("Dimmer",) for name in names},
        probe_results=read_m1_probe_results_from_path(default_progress_md_path()),
    )
    assert "Store Timecode 5" in result.timecode_setup_commands
    assert "Store Timecode 6" in result.timecode_setup_commands
    assigned = [t for t in result.tracks if t.assign_timecode_commands]
    assert len(assigned) == 30
    assert not any(t.blocked_reason for t in result.tracks)
    assert assigned[15].assign_timecode_commands == ("Assign Sequence 315 At Timecode 5.1.16",)
    assert assigned[16].assign_timecode_commands == ("Assign Sequence 316 At Timecode 6.1.1",)
    assert assigned[29].assign_timecode_commands == ("Assign Sequence 329 At Timecode 6.1.14",)


def test_the_split_counts_rows_not_fixtures() -> None:
    # 장비 수백 대라도 줄(그룹)이 3개면 타임코드 하나 — 장비 대수는 나누는 기준이 아니다.
    assert len(split_rows_by_timecode(["WASH", "SPOT", "BEAM"], per_timecode=16)) == 1
    # 장비가 한 대씩이라도 줄이 17개면 둘로 나뉜다.
    assert len(split_rows_by_timecode([f"G{i}" for i in range(17)], per_timecode=16)) == 2
