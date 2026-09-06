"""카드 t305 — 긴 구간이 마디 경계에서 여러 큐로 갈린다.

기준선은 운영자의 정본 산출물이다: `LXSEQ_SAMPLE_01_Sugar_r3.timeline.html`
(Maroon 5 — Sugar, 3:56 · 120 BPM · 4/4 · 118마디 · 1마디 2.000s · 큐 18장).
그 파일에서 센 구간별 큐 수를 여기 표로 못박아 두고, 이 규칙이 그 표의
"마디 수만으로 도출되는 부분"을 재현하는지 잰다.

정본이 하는 것 중 이 규칙이 **하지 않는** 두 가지도 같이 못박는다 —
BRIDGE 의 4·4 분할(마디 수가 아니라 연출 판단)과 OUTRO 의 암전 큐(분할이
아니라 다른 종류의 큐). 재현하지 않기로 한 것을 기록해 두지 않으면 다음
사람이 "왜 18이 아니라 16인가"를 다시 조사하게 된다.
"""

from __future__ import annotations

import pytest

from server.design.cue_density import (
    BAR_UNIT_BARS,
    CueSplit,
    bar_milliseconds,
    beats_per_bar,
    plan_cue_density,
    rotate_palette,
)

#: 정본의 구간 표: (이름, 시작 초, 마디 수, 정본이 실제로 세운 큐 수).
SUGAR_SECTIONS: tuple[tuple[str, float, int, int], ...] = (
    ("INTRO", 0.0, 4, 1),
    ("VERSE1", 8.0, 16, 2),
    ("PRE1", 40.0, 8, 1),
    ("CHORUS1", 56.0, 16, 2),
    ("VERSE2", 88.0, 8, 1),
    ("PRE2", 104.0, 8, 1),
    ("CHORUS2", 120.0, 16, 2),
    ("BRIDGE", 152.0, 8, 2),
    ("CHORUS3", 168.0, 32, 4),
    ("OUTRO", 232.0, 2, 2),
)

SUGAR_BPM = 120.0
SUGAR_METER = "4/4"
SUGAR_END_MS = 236_000  # 03:56.0

#: 정본이 마디 수만으로 설명되지 **않는** 두 구간과 그 이유.
NOT_DERIVED_FROM_BARS = {
    "BRIDGE": "8마디를 4·4 로 쪼갠 것은 낙차 연출(35→75)이지 마디 연산이 아니다",
    "OUTRO": "둘째 큐는 분할이 아니라 곡 끝의 암전 큐다",
}


def _starts_ms() -> list[int]:
    return [round(start * 1000) for _name, start, _bars, _cues in SUGAR_SECTIONS]


def _cue_counts(plan) -> dict[int, int]:
    counts: dict[int, int] = {}
    for split in plan.splits:
        counts[split.source_index] = counts.get(split.source_index, 0) + 1
    return counts


# --------------------------------------------------------------------------
# 마디 연산 — 하드코딩이 아니라 선언된 BPM 에서 나온다
# --------------------------------------------------------------------------


def test_bar_milliseconds_matches_the_sample_header():
    """정본 헤더의 `1마디 2.000s` 를 그대로 재현한다."""
    assert bar_milliseconds(SUGAR_BPM, SUGAR_METER) == pytest.approx(2000.0)


@pytest.mark.parametrize(
    ("bpm", "meter", "expected"),
    [
        (120.0, "4/4", 2000.0),
        (140.0, "4/4", 60_000.0 * 4 / 140.0),
        (90.0, "3/4", 60_000.0 * 3 / 90.0),
        (120.0, "6/8", 60_000.0 * 6 / 120.0),
    ],
)
def test_bar_milliseconds_is_arithmetic_on_the_declared_tempo(bpm, meter, expected):
    assert bar_milliseconds(bpm, meter) == pytest.approx(expected)


@pytest.mark.parametrize("meter", ["", "공통", "4-4", "0/4", None])
def test_unreadable_meter_yields_no_bar_length(meter):
    assert beats_per_bar(meter) is None
    assert bar_milliseconds(120.0, meter) is None


# --------------------------------------------------------------------------
# 분할 규칙 — 정본 표에 대고 잰다
# --------------------------------------------------------------------------


def test_split_reproduces_the_sample_cue_counts_where_bars_explain_them():
    plan = plan_cue_density(
        _starts_ms(),
        bpm=SUGAR_BPM,
        meter=SUGAR_METER,
        song_end_ms=SUGAR_END_MS,
    )
    counts = _cue_counts(plan)
    for index, (name, _start, _bars, sample_cues) in enumerate(SUGAR_SECTIONS):
        if name in NOT_DERIVED_FROM_BARS:
            # 기록만 남긴다: 이 규칙은 정본보다 적게 낸다, 의도적으로.
            assert counts[index] == 1, NOT_DERIVED_FROM_BARS[name]
            continue
        assert counts[index] == sample_cues, f"{name}: {sample_cues} 큐를 기대"


def test_split_count_is_the_bar_quotient_not_a_hardcoded_number():
    """32마디 후렴이 8마디 단위로 넷이 되고, 오프셋은 BPM 연산이다."""
    bar_ms = bar_milliseconds(SUGAR_BPM, SUGAR_METER)
    unit_ms = bar_ms * BAR_UNIT_BARS
    start = 168_000
    plan = plan_cue_density(
        [start, 232_000], bpm=SUGAR_BPM, meter=SUGAR_METER, song_end_ms=SUGAR_END_MS
    )
    chorus3 = [split for split in plan.splits if split.source_index == 0]
    assert [split.start_ms for split in chorus3] == [
        start + round(unit * unit_ms) for unit in range(4)
    ]
    assert [split.unit_index for split in chorus3] == [0, 1, 2, 3]
    # 정본의 Q130~Q160 시각(02:48 / 03:04 / 03:20 / 03:36).
    assert [split.start_ms for split in chorus3] == [168_000, 184_000, 200_000, 216_000]


def test_a_faster_tempo_moves_the_offsets():
    """같은 구간이라도 BPM 이 다르면 오프셋이 달라진다 — 상수가 아니다."""
    slow = plan_cue_density([0, 64_000], bpm=120.0, meter="4/4")
    fast = plan_cue_density([0, 64_000], bpm=180.0, meter="4/4")
    slow_starts = [split.start_ms for split in slow.splits if split.source_index == 0]
    fast_starts = [split.start_ms for split in fast.splits if split.source_index == 0]
    assert slow_starts == [0, 16_000, 32_000, 48_000]
    assert fast_starts != slow_starts
    assert fast_starts[1] == round(8 * 4 * 60_000 / 180.0)
    # 빠른 템포에서는 같은 64초에 마디가 더 들어가므로 큐도 더 나온다.
    assert len(fast_starts) > len(slow_starts)


def test_remainder_is_absorbed_by_the_last_cue():
    """20마디(40초 @120BPM)는 8+12 로 둘이지, 8+8+4 로 셋이 아니다."""
    plan = plan_cue_density([0, 40_000], bpm=120.0, meter="4/4")
    first = [split for split in plan.splits if split.source_index == 0]
    assert len(first) == 2
    assert [split.start_ms for split in first] == [0, 16_000]


def test_a_section_shorter_than_one_unit_stays_whole():
    """4마디(8초)는 한 단위에 못 미치므로 큐 하나."""
    plan = plan_cue_density([0, 8_000], bpm=120.0, meter="4/4")
    assert [split.start_ms for split in plan.splits if split.source_index == 0] == [0]


def test_the_last_section_is_not_split_without_a_song_end():
    """끝나는 시각을 안 주면 길이를 모른다 — 안 잰 것으로 큐를 놓지 않는다."""
    starts = [0, 8_000]
    without_end = plan_cue_density(starts, bpm=120.0, meter="4/4")
    assert _cue_counts(without_end)[1] == 1
    with_end = plan_cue_density(starts, bpm=120.0, meter="4/4", song_end_ms=104_000)
    assert _cue_counts(with_end)[1] == 6


# --------------------------------------------------------------------------
# 없으면 안 쏜다 — BPM 미선언은 오늘 동작 그대로
# --------------------------------------------------------------------------


def test_no_bpm_means_one_cue_per_section_byte_identical():
    starts = _starts_ms()
    plan = plan_cue_density(starts, bpm=None, meter=SUGAR_METER, song_end_ms=SUGAR_END_MS)
    assert plan.splits == tuple(
        CueSplit(source_index=index, unit_index=0, start_ms=start)
        for index, start in enumerate(starts)
    )
    assert plan.cue_count == len(starts)
    assert plan.notes and "BPM" in plan.notes[0]


def test_unreadable_meter_means_one_cue_per_section():
    starts = _starts_ms()
    plan = plan_cue_density(starts, bpm=SUGAR_BPM, meter="자유박", song_end_ms=SUGAR_END_MS)
    assert plan.cue_count == len(starts)
    assert plan.notes and "박자표" in plan.notes[0]


def test_empty_input_is_empty_output():
    assert plan_cue_density([], bpm=120.0, meter="4/4").splits == ()


# --------------------------------------------------------------------------
# 쪼갠 큐는 서로 달라야 한다
# --------------------------------------------------------------------------


def test_split_cues_rotate_the_palette():
    """이어지는 큐는 색이 돌아간다 — 정본 Q060 "강도 유지, 색만 교체"."""
    colors = ("amber", "magenta", "cyan")
    assert rotate_palette(colors, 0) == colors
    assert rotate_palette(colors, 1) == ("magenta", "cyan", "amber")
    assert rotate_palette(colors, 2) == ("cyan", "amber", "magenta")
    assert rotate_palette(colors, 3) == colors  # 한 바퀴


def test_a_single_colour_section_is_not_split_and_says_why():
    """차이를 못 만들면 같은 큐 둘 대신 큐 하나 — 그리고 사유를 밖에 낸다."""
    plan = plan_cue_density(
        [0, 64_000],
        bpm=120.0,
        meter="4/4",
        palette_sizes=[1, 1],
    )
    assert _cue_counts(plan)[0] == 1
    assert any("색이 하나뿐" in note for note in plan.notes)


def test_a_two_colour_section_is_split():
    plan = plan_cue_density(
        [0, 64_000],
        bpm=120.0,
        meter="4/4",
        palette_sizes=[2, 2],
    )
    assert _cue_counts(plan)[0] == 4
    assert not any("색이 하나뿐" in note for note in plan.notes)


def test_source_origins_maps_every_cue_back_to_its_section():
    plan = plan_cue_density(
        [0, 64_000, 96_000],
        bpm=120.0,
        meter="4/4",
        palette_sizes=[2, 2, 2],
    )
    assert plan.source_origins == (0, 0, 0, 0, 1, 1, 2)
    assert len(plan.source_origins) == plan.cue_count
