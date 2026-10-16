"""리듬 특징(rhythm.py)과 마디 지도의 선택 키 rhythm 검증(bar_map_store) — SPEC-LDRHYTHM-001 v1."""

from __future__ import annotations

from collections import namedtuple

import numpy
import pytest

from server.audio import bar_map_store
from server.audio.bar_map_store import (
    BarMapStoreError,
    attach_rhythm,
    build_bar_map_payload,
    validate_bar_map,
)
from server.audio.rhythm import (
    SECTION_KINDS,
    big_hit_indices,
    build_rhythm,
    classify_section_kinds,
    snap_sections,
    song_relative,
)

Grade = namedtuple("Grade", "start_ms end_ms d_level")


def _bars_at(starts: list[int]) -> list[dict]:
    return [
        {"bar": number, "start_ms": start, "beats_ms": [start]}
        for number, start in enumerate(starts)
    ]


def test_song_relative_is_centred_and_ordered_by_percentile() -> None:
    z, pct = song_relative([1.0, 10.0, 100.0, 1000.0])
    assert abs(sum(z)) < 1e-9
    assert pct == sorted(pct)
    assert pct[0] == 0.0
    assert pct[-1] == 1.0


def test_song_relative_flat_song_has_zero_z_without_dividing_by_zero() -> None:
    z, pct = song_relative([5.0, 5.0, 5.0])
    assert z == [0.0, 0.0, 0.0]
    assert len(pct) == 3


def test_big_hit_needs_a_local_maximum_above_the_song_threshold() -> None:
    lone_peak = [0.0] * 20
    lone_peak[10] = 9.0
    assert big_hit_indices(lone_peak) == [10]

    taller_neighbour = [0.0] * 20
    taller_neighbour[10] = 9.0
    taller_neighbour[11] = 9.5
    picked = big_hit_indices(taller_neighbour)
    assert 10 not in picked
    assert 11 in picked

    gentle_slope = [1.0 + 0.01 * index for index in range(20)]
    assert big_hit_indices(gentle_slope) == []


def test_snap_sections_moves_boundaries_to_bars_and_takes_the_max_overlap_grade() -> None:
    bars = _bars_at([0, 2000, 4000, 6000, 8000, 10000, 12000, 14000])
    grades = [Grade(0, 5000, 1), Grade(5000, 9000, 3), Grade(9000, 20000, 5)]
    spans = snap_sections(bars, [0, 4100, 8300], grades)
    assert [(span["start_bar"], span["end_bar"], span["bars"]) for span in spans] == [
        (0, 1, 2),
        (2, 3, 2),
        (4, 7, 4),
    ]
    assert [span["d_level"] for span in spans] == [1, 3, 5]
    assert (spans[1]["start_ms"], spans[1]["end_ms"]) == (4000, 8000)
    assert spans[2]["end_ms"] == 16000


def test_snap_sections_breaks_an_overlap_tie_with_the_grade_holding_the_span_start() -> None:
    bars = _bars_at([0, 2000, 4000, 6000])
    grades = [Grade(0, 6000, 1), Grade(6000, 12000, 5)]
    spans = snap_sections(bars, [0, 4000], grades)
    assert spans[1]["start_ms"] == 4000
    assert spans[1]["d_level"] == 1


def _synthetic_track(bars_count: int = 6, bpm: float = 120.0, sample_rate: int = 22050):
    rng = numpy.random.default_rng(0)
    beat_s = 60.0 / bpm
    total_s = bars_count * 4 * beat_s + 1.0
    signal = numpy.zeros(int(total_s * sample_rate), dtype=numpy.float32)
    tail = numpy.arange(int(0.2 * sample_rate)) / sample_rate
    for bar in range(bars_count):
        for beat in range(4):
            onset = int(round((bar * 4 + beat) * beat_s * sample_rate))
            if beat in (0, 2):
                # 큰 히트는 곡 평균에서 2σ 이상 떨어져야 잡힌다. 악센트는 그만큼 커야 한다.
                amplitude = 4.0 if (bar == 3 and beat == 0) else 0.7
                click = numpy.exp(-tail / 0.02) * rng.standard_normal(tail.size)
                thump = numpy.exp(-tail / 0.06) * numpy.sin(2 * numpy.pi * 60.0 * tail)
                hit = amplitude * (0.5 * click + thump)
                signal[onset : onset + hit.size] += hit.astype(numpy.float32)
            if beat in (1, 3):
                burst = numpy.exp(-tail / 0.03) * rng.standard_normal(tail.size)
                signal[onset : onset + burst.size] += (0.5 * burst).astype(numpy.float32)
    bars = [
        {
            "bar": bar + 1,
            "start_ms": int(round(bar * 4 * beat_s * 1000)),
            "beats_ms": [int(round((bar * 4 + beat) * beat_s * 1000)) for beat in range(4)],
        }
        for bar in range(bars_count)
    ]
    return signal, sample_rate, bars, int(total_s * 1000)


def test_build_rhythm_separates_kick_beats_from_snare_beats_and_finds_the_accent() -> None:
    mono, sample_rate, bars, total_ms = _synthetic_track()
    rhythm = build_rhythm(mono, sample_rate, bars, [0], [Grade(0, total_ms, 3)])
    beats = rhythm["beats"]
    assert len(beats) == 24

    def mean_of(name: str, beat_numbers: set[int]) -> float:
        values = [item[name] for item in beats if item["beat"] in beat_numbers]
        return sum(values) / len(values)

    assert mean_of("kick", {1, 3}) - mean_of("kick", {2, 4}) > 0.25
    # 킥의 광대역 클릭이 스네어 대역으로 새어 대비가 작다(실측 약 0.22). 방향과 뚜렷한 간격만 본다.
    assert mean_of("snare", {2, 4}) - mean_of("snare", {1, 3}) > 0.15
    accent = [hit for hit in rhythm["hits"] if (hit["bar"], hit["beat"]) == (4, 1)]
    assert accent
    assert accent[0]["kind"] == "big"


def _rhythm_for_two_bars(payload: dict) -> dict:
    beats = []
    for bar in payload["bars"]:
        for index, time_ms in enumerate(bar["beats_ms"], start=1):
            beats.append(
                {
                    "bar": bar["bar"],
                    "beat": index,
                    "t_ms": time_ms,
                    "kick": 0.5,
                    "snare": 0.5,
                    "onset": 0.5,
                    "kick_hit": False,
                    "snare_hit": False,
                }
            )
    return {
        "beats": beats,
        "hits": [],
        "sections": [
            {"start_bar": 1, "end_bar": 2, "bars": 2, "start_ms": 0, "end_ms": 4000, "d_level": 3}
        ],
    }


def _two_bar_payload() -> dict:
    beat_times = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
    return build_bar_map_payload(beat_times, 0, bpm=120.0, time_signature=(4, 4), events=())


def test_rhythm_is_an_optional_key_and_a_consistent_block_validates() -> None:
    payload = _two_bar_payload()
    assert validate_bar_map(payload) is None
    merged = attach_rhythm(payload, _rhythm_for_two_bars(payload))
    assert "rhythm" in merged
    assert validate_bar_map(merged) is None


def test_unknown_top_level_key_is_still_rejected() -> None:
    payload = _two_bar_payload()
    payload["junk"] = 1
    problem = validate_bar_map(payload)
    assert problem is not None
    assert "알 수 없는 필드" in problem


def test_rhythm_beat_time_must_match_the_bar_map_beat() -> None:
    payload = _two_bar_payload()
    rhythm = _rhythm_for_two_bars(payload)
    rhythm["beats"][0]["t_ms"] = 1
    with pytest.raises(BarMapStoreError, match="t_ms"):
        attach_rhythm(payload, rhythm)


def test_rhythm_hit_kind_is_fixed_to_big() -> None:
    payload = _two_bar_payload()
    rhythm = _rhythm_for_two_bars(payload)
    rhythm["hits"] = [{"bar": 1, "beat": 1, "t_ms": 0, "strength": 0.5, "kind": "small"}]
    with pytest.raises(BarMapStoreError, match="big"):
        attach_rhythm(payload, rhythm)


def test_rhythm_scores_must_be_unit_numbers() -> None:
    payload = _two_bar_payload()
    rhythm = _rhythm_for_two_bars(payload)
    rhythm["beats"][3]["kick"] = 1.5
    with pytest.raises(BarMapStoreError, match="kick"):
        attach_rhythm(payload, rhythm)


def test_rhythm_section_bar_count_must_match_its_span() -> None:
    payload = _two_bar_payload()
    rhythm = _rhythm_for_two_bars(payload)
    rhythm["sections"][0]["bars"] = 3
    with pytest.raises(BarMapStoreError, match="bars"):
        attach_rhythm(payload, rhythm)


def test_rhythm_block_rejects_unknown_fields() -> None:
    payload = _two_bar_payload()
    rhythm = _rhythm_for_two_bars(payload)
    rhythm["phrases"] = []
    with pytest.raises(BarMapStoreError, match="rhythm"):
        attach_rhythm(payload, rhythm)


# --- 구간 종류(kind) — 이 곡 안의 에너지 순위·이벤트·구간 순서만 근거로 쓴다 ---


def _sections_of(spans: list[tuple[int, int]]) -> list[dict]:
    return [{"start_bar": a, "end_bar": b, "bars": b - a + 1} for a, b in spans]


def _flat_energy(per_section: list[float | None], spans: list[tuple[int, int]]) -> dict:
    return {
        bar: value
        for (a, b), value in zip(spans, per_section, strict=True)
        if value is not None
        for bar in range(a, b + 1)
    }


def test_section_kinds_apply_the_rules_in_order_on_a_ten_section_layout() -> None:
    spans = [(1 + 4 * index, 4 + 4 * index) for index in range(10)]
    events = [
        {"kind": "build", "start_bar": 10, "end_bar": 12},
        {"kind": "break", "start_bar": 21, "end_bar": 21},
        {"kind": "drop", "start_bar": 26, "end_bar": 27},
        {"kind": "kick_entry", "start_bar": 5, "end_bar": 5},
    ]
    # 둘째 구간(S1)의 에너지를 가장 높게 둔다 — 후렴이 이미 있으면 에너지 순위는 쓰이지 않아야 한다.
    energy = _flat_energy([0.1, 0.99, 0.5, 0.6, 0.3, 0.2, 0.9, 0.8, 0.4, 0.1], spans)
    kinds = classify_section_kinds(_sections_of(spans), events, energy)
    assert kinds == [
        "intro",  # R3
        "verse",  # R8 (R7 은 후렴이 있어 쓰이지 않는다)
        "pre",  # R2: build 시작 마디 10 이 9~12 안에 있다
        "chorus",  # R5: 앞이 pre
        "verse",
        "bridge",  # R6: break 시작 = 구간 시작 21, 다음이 drop
        "drop",  # R1: drop 시작 마디 26 이 25~28 안에 있다
        "chorus",  # R5: 앞이 drop
        "verse",
        "outro",  # R4
    ]


def test_a_break_started_section_right_before_a_drop_is_a_bridge() -> None:
    spans = [(1, 4), (5, 8), (9, 12), (13, 16)]
    events = [
        {"kind": "break", "start_bar": 5, "end_bar": 5},
        {"kind": "drop", "start_bar": 9, "end_bar": 12},
    ]
    kinds = classify_section_kinds(_sections_of(spans), events, {})
    assert kinds == ["intro", "bridge", "drop", "outro"]

    # break 가 구간 시작이 아니거나 다음이 drop 이 아니면 다리가 아니다.
    off_start = [{"kind": "break", "start_bar": 6, "end_bar": 6}, events[1]]
    assert classify_section_kinds(_sections_of(spans), off_start, {})[1] == "verse"
    no_drop = [{"kind": "break", "start_bar": 5, "end_bar": 5}]
    assert classify_section_kinds(_sections_of(spans), no_drop, {})[1] == "verse"


def test_chorus_falls_back_to_the_top_third_by_energy_when_events_give_none() -> None:
    spans = [(1 + 4 * index, 4 + 4 * index) for index in range(6)]
    # 본문 4개(S1~S4)의 에너지: 0.9, 0.2, 0.7, 0.1 → 올림(4/3) = 2개가 후렴.
    energy = _flat_energy([0.5, 0.9, 0.2, 0.7, 0.1, 0.5], spans)
    kinds = classify_section_kinds(_sections_of(spans), [], energy)
    assert kinds == ["intro", "chorus", "verse", "chorus", "verse", "outro"]


def test_energy_ties_pick_the_earlier_section_first() -> None:
    spans = [(1 + 4 * index, 4 + 4 * index) for index in range(5)]
    energy = _flat_energy([0.0, 0.5, 0.5, 0.5, 0.0], spans)
    kinds = classify_section_kinds(_sections_of(spans), [], energy)
    # 본문 3개 → 올림(3/3) = 1개. 동률이면 앞 구간이다.
    assert kinds == ["intro", "chorus", "verse", "verse", "outro"]


def test_no_energy_means_no_chorus_and_every_body_section_is_a_verse() -> None:
    spans = [(1 + 4 * index, 4 + 4 * index) for index in range(5)]
    kinds = classify_section_kinds(_sections_of(spans), [], {})
    assert kinds == ["intro", "verse", "verse", "verse", "outro"]


def test_section_kinds_edge_cases() -> None:
    assert classify_section_kinds([], [], {}) == []
    # 구간이 하나면 첫 구간이므로 intro 이고 outro 는 없다.
    assert classify_section_kinds(_sections_of([(1, 4)]), [], {}) == ["intro"]


def test_build_rhythm_sets_a_valid_kind_on_every_section_and_the_payload_validates() -> None:
    mono, sample_rate, bars, total_ms = _synthetic_track()
    for bar in bars:
        bar["energy"] = 0.2 + 0.1 * bar["bar"]
    events = [{"kind": "drop", "start_bar": 3, "end_bar": 4}]
    rhythm = build_rhythm(
        mono, sample_rate, bars, [0, 4000, 8000], [Grade(0, total_ms, 3)], events=events
    )
    kinds = [section["kind"] for section in rhythm["sections"]]
    assert kinds == ["intro", "drop", "outro"]
    assert set(kinds) <= set(SECTION_KINDS)

    beat_times = [time_ms for bar in bars for time_ms in bar["beats_ms"]]
    payload = build_bar_map_payload(beat_times, 0, bpm=120.0, time_signature=(4, 4), events=())
    merged = attach_rhythm(payload, rhythm)
    assert validate_bar_map(merged) is None


def test_validator_accepts_a_valid_kind_rejects_an_unknown_one_and_allows_none() -> None:
    payload = _two_bar_payload()
    rhythm = _rhythm_for_two_bars(payload)
    assert validate_bar_map(attach_rhythm(payload, rhythm)) is None  # kind 없음

    rhythm["sections"][0]["kind"] = "chorus"
    assert validate_bar_map(attach_rhythm(payload, rhythm)) is None

    rhythm["sections"][0]["kind"] = "refrain"
    with pytest.raises(BarMapStoreError, match="kind"):
        attach_rhythm(payload, rhythm)


def test_section_kind_vocabularies_match_between_builder_and_validator() -> None:
    expected = ("intro", "verse", "pre", "chorus", "bridge", "drop", "outro")
    assert expected == SECTION_KINDS
    assert frozenset(expected) == bar_map_store._SECTION_KINDS
