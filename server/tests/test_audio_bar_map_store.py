"""M4 — 마디 지도 저장 인터페이스, 순수 모듈 (SPEC-LDBARMAP-001, 카드 t539).

``server/audio/bar_map_store.py`` 만 다룬다 — 콘솔·세션·라이브러리는 전혀
닿지 않는다(세션 배선은 ``test_session_bar_map_store.py``). 네 층:

1. 왕복 동등성(``build_bar_map_payload`` → ``attach_bar_map`` → ``read_bar_map``,
   AC-LDBARMAP-010 조건 1).
2. ``validate_bar_map`` 거절 — 각 규칙을 개별로 깨는 음성 대조군(검사기가
   공허하지 않다는 증거, "검사 자신이 공허할 수 있다" 교훈 적용).
3. 일반화 — LOVE ATTACK 전용 상수를 가정하지 않는 비-4/4 픽스처
   (AC-LDBARMAP-010 조건 5).
4. ``derive_bars``(M2)와의 일관성 — 같은 비트 격자·오프셋이면 다운비트 시각이
   같다.
5. 문서 검사(AC-LDBARMAP-010 조건 6) — spec.md §5 가 REQ-LDBEAT-006 저장소
   실체와 SPEC-LDARRANGE-001 을 인용하는지.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.audio.bar_map import BarEvent, derive_bars
from server.audio.bar_map_store import (
    BAR_MAP_SCHEMA_VERSION,
    BarMapStoreError,
    attach_bar_map,
    build_bar_map_payload,
    read_bar_map,
    validate_bar_map,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).parent / "fixtures"
LOVE_ATTACK_BEAT_GRID_PATH = FIXTURES_DIR / "love_attack_beat_grid.json"

#: 감독이 귀로 확정한 LOVE ATTACK 첫 박 오프셋(progress.md §E.2, plan.md M2).
CONFIRMED_FIRST_BEAT_OFFSET = 1
LOVE_ATTACK_BPM = 112.35


# ---------------------------------------------------------------------------
# 헬퍼 — 두 비-4/4 합성 픽스처 + LOVE ATTACK 픽스처 로더
# ---------------------------------------------------------------------------


def _simple_4_4_beats(n_bars: int = 3) -> list[int]:
    """오프셋 0, 못갖춘마디 없음, 4/4, 500ms 간격."""
    return list(range(0, n_bars * 4 * 500, 500))


def _three_four_no_pickup_partial_last() -> list[int]:
    """3/4, 못갖춘마디 없음, 마지막 마디 2박만(부분 마디)."""
    # 2마디(6박) + 마지막 마디 2박 = 8박.
    return [i * 400 for i in range(8)]


def _six_eight_with_pickup() -> tuple[list[int], int]:
    """6/8, 못갖춘마디 2박(오프셋 2), 그 뒤 온전한 마디 2개."""
    beats = [i * 250 for i in range(14)]  # 2(pickup) + 6 + 6
    return beats, 2


def _love_attack_beats() -> list[int]:
    import json

    data = json.loads(LOVE_ATTACK_BEAT_GRID_PATH.read_text(encoding="utf-8"))
    return [int(t) for t in data["beat_times_ms"]]


# ---------------------------------------------------------------------------
# 1. 왕복 동등성 (AC-LDBARMAP-010 조건 1)
# ---------------------------------------------------------------------------


def test_round_trip_equality_build_attach_read() -> None:
    beats = _simple_4_4_beats(4)
    payload = build_bar_map_payload(beats, 0, bpm=112.35, time_signature=(4, 4))
    timeline = {"song_title": "Test"}
    stored = attach_bar_map(timeline, payload)
    assert "bar_map" not in timeline  # 원본 불변
    read_back = read_bar_map(stored)
    assert read_back == payload
    assert read_back["schema_version"] == BAR_MAP_SCHEMA_VERSION


def test_round_trip_equality_with_events() -> None:
    beats = _simple_4_4_beats(6)
    events = [
        BarEvent("kick_entry", 2, 2, grade="measured"),
        BarEvent("build", 3, 5, grade="measured"),
    ]
    payload = build_bar_map_payload(beats, 0, bpm=120.0, time_signature=(4, 4), events=events)
    stored = attach_bar_map({}, payload)
    read_back = read_bar_map(stored)
    assert read_back == payload
    assert read_back["events"] == [
        {"kind": "kick_entry", "start_bar": 2, "end_bar": 2, "start_beat": 1, "grade": "measured"},
        {"kind": "build", "start_bar": 3, "end_bar": 5, "start_beat": 1, "grade": "measured"},
    ]


def test_round_trip_tolerates_bpm_relative_floating_point_noise() -> None:
    beats = _simple_4_4_beats(4)
    payload = build_bar_map_payload(beats, 0, bpm=112.34999999999999, time_signature=(4, 4))
    stored = attach_bar_map({}, payload)
    read_back = read_bar_map(stored)
    assert abs(read_back["bpm"] - payload["bpm"]) <= abs(payload["bpm"]) * 1e-9


def test_attach_bar_map_does_not_mutate_the_original_payload_object() -> None:
    beats = _simple_4_4_beats(2)
    payload = build_bar_map_payload(beats, 0, bpm=100.0)
    stored = attach_bar_map({}, payload)
    stored["bar_map"]["bars"][0]["bar"] = 999
    assert payload["bars"][0]["bar"] == 1  # read_bar_map/attach_bar_map 둘 다 깊은 사본


def test_read_bar_map_returns_a_deep_copy_each_time() -> None:
    beats = _simple_4_4_beats(2)
    payload = build_bar_map_payload(beats, 0, bpm=100.0)
    stored = attach_bar_map({}, payload)
    first = read_bar_map(stored)
    first["bars"][0]["bar"] = 999
    second = read_bar_map(stored)
    assert second["bars"][0]["bar"] == 1


# ---------------------------------------------------------------------------
# 2. validate_bar_map 거절 — 유효한 기준 페이로드를 한 필드씩 깬다.
# ---------------------------------------------------------------------------


def _valid_payload() -> dict:
    beats = _simple_4_4_beats(3)
    events = [BarEvent("break", 2, 2, grade="measured")]
    return build_bar_map_payload(beats, 0, bpm=112.35, time_signature=(4, 4), events=events)


def test_valid_payload_passes() -> None:
    assert validate_bar_map(_valid_payload()) is None


def test_read_bar_map_is_fail_open_on_absence() -> None:
    assert read_bar_map({}) is None
    assert read_bar_map({"bar_map": None}) is None


def test_read_bar_map_is_fail_open_on_corruption() -> None:
    payload = _valid_payload()
    payload["bars"] = []  # 손상
    assert read_bar_map({"bar_map": payload}) is None


def test_read_bar_map_rejects_non_mapping_timeline() -> None:
    assert read_bar_map(["not", "a", "mapping"]) is None


@pytest.mark.parametrize(
    "mutate,description",
    [
        (lambda p: p.pop("schema_version"), "missing schema_version"),
        (lambda p: p.update(schema_version=2), "wrong schema_version"),
        (lambda p: p.update(schema_version=True), "bool schema_version"),
        (lambda p: p.update(extra_field="x"), "unknown top-level field"),
        (lambda p: p.update(bpm="fast"), "non-numeric bpm"),
        (lambda p: p.update(bpm=True), "bool bpm"),
        (lambda p: p.update(bpm=0.0), "zero bpm"),
        (lambda p: p.update(bpm=-10.0), "negative bpm"),
        (lambda p: p.update(bpm=float("nan")), "nan bpm"),
        (lambda p: p.update(bpm=float("inf")), "infinite bpm"),
        (lambda p: p.update(time_signature=[4]), "short time_signature"),
        (lambda p: p.update(time_signature=[0, 4]), "zero numerator"),
        (lambda p: p.update(time_signature=[17, 4]), "numerator over 16"),
        (lambda p: p.update(time_signature=[4, 3]), "denominator not in allowed set"),
        (lambda p: p.update(first_beat_offset=-1), "negative first_beat_offset"),
        (lambda p: p.update(first_beat_offset=4), "first_beat_offset equal to numerator"),
        (lambda p: p.update(first_beat_offset=True), "bool first_beat_offset"),
        (lambda p: p.update(bars=[]), "empty bars"),
        (lambda p: p.update(bars="not-a-list"), "bars not a list"),
    ],
)
def test_validator_rejects_each_top_level_mutation(mutate, description) -> None:
    payload = _valid_payload()
    mutate(payload)
    reason = validate_bar_map(payload)
    assert reason is not None, f"expected rejection for: {description}"
    assert isinstance(reason, str) and reason


def test_validator_rejects_negative_bar_number() -> None:
    payload = _valid_payload()
    payload["bars"][0]["bar"] = -1
    assert validate_bar_map(payload) is not None


def test_validator_rejects_non_contiguous_bar_numbers() -> None:
    payload = _valid_payload()
    payload["bars"][1]["bar"] = 5
    assert validate_bar_map(payload) is not None


def test_validator_rejects_first_bar_number_not_zero_or_one() -> None:
    payload = _valid_payload()
    payload["bars"][0]["bar"] = 2
    for bar in payload["bars"][1:]:
        bar["bar"] += 1
    assert validate_bar_map(payload) is not None


def test_validator_rejects_wrong_beat_count_for_a_non_last_bar() -> None:
    payload = _valid_payload()
    payload["bars"][0]["beats_ms"] = payload["bars"][0]["beats_ms"][:3]  # 3 아니라 4 가 필요
    assert validate_bar_map(payload) is not None


def test_validator_accepts_a_short_final_bar() -> None:
    payload = _valid_payload()
    last = payload["bars"][-1]
    last["beats_ms"] = last["beats_ms"][:2]
    assert validate_bar_map(payload) is None


def test_validator_rejects_start_ms_not_matching_first_beat() -> None:
    payload = _valid_payload()
    payload["bars"][0]["start_ms"] = payload["bars"][0]["beats_ms"][0] + 1
    assert validate_bar_map(payload) is not None


def test_validator_rejects_non_increasing_beats_within_a_bar() -> None:
    payload = _valid_payload()
    beats = payload["bars"][0]["beats_ms"]
    beats[1] = beats[0]  # 같은 값 — 엄격히 증가해야 한다
    assert validate_bar_map(payload) is not None


def test_validator_rejects_non_increasing_beats_across_bars() -> None:
    payload = _valid_payload()
    payload["bars"][1]["beats_ms"][0] = payload["bars"][0]["beats_ms"][-1]
    payload["bars"][1]["start_ms"] = payload["bars"][1]["beats_ms"][0]
    assert validate_bar_map(payload) is not None


def test_validator_rejects_negative_ms_values() -> None:
    payload = _valid_payload()
    payload["bars"][0]["beats_ms"][0] = -500
    payload["bars"][0]["start_ms"] = -500
    assert validate_bar_map(payload) is not None


def test_validator_rejects_bool_ms_value() -> None:
    payload = _valid_payload()
    payload["bars"][0]["start_ms"] = True
    payload["bars"][0]["beats_ms"][0] = True
    assert validate_bar_map(payload) is not None


def test_validator_rejects_unknown_bar_field() -> None:
    payload = _valid_payload()
    payload["bars"][0]["extra"] = 1
    assert validate_bar_map(payload) is not None


def test_validator_rejects_missing_bar_field() -> None:
    payload = _valid_payload()
    del payload["bars"][0]["start_ms"]
    assert validate_bar_map(payload) is not None


# -- events --------------------------------------------------------------


def test_validator_rejects_start_beat_zero() -> None:
    payload = _valid_payload()
    payload["events"][0]["start_beat"] = 0
    assert validate_bar_map(payload) is not None


def test_validator_rejects_start_beat_above_numerator() -> None:
    payload = _valid_payload()
    payload["events"][0]["start_beat"] = 5  # 분자 4 초과
    assert validate_bar_map(payload) is not None


def test_validator_rejects_bool_start_beat() -> None:
    payload = _valid_payload()
    payload["events"][0]["start_beat"] = True
    assert validate_bar_map(payload) is not None


def test_validator_rejects_unknown_event_kind() -> None:
    payload = _valid_payload()
    payload["events"][0]["kind"] = "fade"
    assert validate_bar_map(payload) is not None


def test_validator_rejects_unknown_event_grade() -> None:
    payload = _valid_payload()
    payload["events"][0]["grade"] = "guessed"
    assert validate_bar_map(payload) is not None


def test_validator_rejects_start_bar_greater_than_end_bar() -> None:
    payload = _valid_payload()
    payload["events"][0]["start_bar"] = 3
    payload["events"][0]["end_bar"] = 1
    assert validate_bar_map(payload) is not None


def test_validator_rejects_event_bar_outside_stored_range() -> None:
    payload = _valid_payload()
    payload["events"][0]["start_bar"] = 999
    payload["events"][0]["end_bar"] = 999
    assert validate_bar_map(payload) is not None


def test_validator_rejects_unknown_event_field() -> None:
    payload = _valid_payload()
    payload["events"][0]["extra"] = 1
    assert validate_bar_map(payload) is not None


def test_validator_rejects_missing_event_field() -> None:
    payload = _valid_payload()
    del payload["events"][0]["grade"]
    assert validate_bar_map(payload) is not None


def test_validator_rejects_events_not_a_list() -> None:
    payload = _valid_payload()
    payload["events"] = "not-a-list"
    assert validate_bar_map(payload) is not None


def test_build_bar_map_payload_raises_store_error_for_bad_offset() -> None:
    with pytest.raises(BarMapStoreError):
        build_bar_map_payload([0, 500, 1000, 1500], 4, bpm=100.0, time_signature=(4, 4))


def test_build_bar_map_payload_raises_store_error_for_non_int_offset() -> None:
    with pytest.raises(BarMapStoreError):
        build_bar_map_payload([0, 500, 1000, 1500], 1.5, bpm=100.0, time_signature=(4, 4))


def test_attach_bar_map_raises_store_error_for_invalid_payload() -> None:
    payload = _valid_payload()
    payload["bars"][0]["bar"] = -1
    with pytest.raises(BarMapStoreError):
        attach_bar_map({}, payload)


# ---------------------------------------------------------------------------
# 3. 일반화 — LOVE ATTACK 전용 상수를 가정하지 않는 비-4/4 픽스처
#    (AC-LDBARMAP-010 조건 5)
# ---------------------------------------------------------------------------


def test_three_four_no_pickup_partial_last_bar_round_trips() -> None:
    beats = _three_four_no_pickup_partial_last()
    payload = build_bar_map_payload(beats, 0, bpm=90.0, time_signature=(3, 4))
    assert payload["bars"][0]["bar"] == 1  # 못갖춘마디 없음
    assert len(payload["bars"][-1]["beats_ms"]) == 2  # 부분 마디
    stored = attach_bar_map({}, payload)
    assert read_bar_map(stored) == payload
    # 기대 오프셋 범위는 박자표 분자(3)로 나눈 나머지 — 0~2(acceptance.md 조건 5).
    assert 0 <= payload["first_beat_offset"] <= 2


def test_six_eight_with_pickup_round_trips() -> None:
    beats, offset = _six_eight_with_pickup()
    payload = build_bar_map_payload(beats, offset, bpm=140.0, time_signature=(6, 8))
    assert payload["bars"][0]["bar"] == 0  # 못갖춘마디 있음
    assert len(payload["bars"][0]["beats_ms"]) == offset
    stored = attach_bar_map({}, payload)
    assert read_bar_map(stored) == payload


def test_two_bar_song_round_trips() -> None:
    beats = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]  # 정확히 2마디, 4/4
    payload = build_bar_map_payload(beats, 0, bpm=120.0, time_signature=(4, 4))
    assert [bar["bar"] for bar in payload["bars"]] == [1, 2]
    stored = attach_bar_map({}, payload)
    assert read_bar_map(stored) == payload


# ---------------------------------------------------------------------------
# 4. derive_bars(M2)와의 일관성 — LOVE ATTACK 326개 비트 고정 픽스처.
# ---------------------------------------------------------------------------


def test_build_bar_map_payload_matches_derive_bars_on_love_attack_fixture() -> None:
    beats = _love_attack_beats()
    derived = derive_bars(beats, CONFIRMED_FIRST_BEAT_OFFSET)
    payload = build_bar_map_payload(
        beats, CONFIRMED_FIRST_BEAT_OFFSET, bpm=LOVE_ATTACK_BPM, time_signature=(4, 4)
    )
    bars_ge1 = [bar for bar in payload["bars"] if bar["bar"] >= 1]
    assert tuple(bar["start_ms"] for bar in bars_ge1) == derived.downbeats_ms
    bar0 = next((bar for bar in payload["bars"] if bar["bar"] == 0), None)
    if derived.pickup_beats_ms:
        assert bar0 is not None
        assert tuple(bar0["beats_ms"]) == derived.pickup_beats_ms
    else:
        assert bar0 is None


# ---------------------------------------------------------------------------
# 5. 문서 검사 (AC-LDBARMAP-010 조건 6) — spec.md §5 가 REQ-LDBEAT-006 저장소
#    실체와 SPEC-LDARRANGE-001 을 인용하는지, §5 범위로 한정해서 센다.
# ---------------------------------------------------------------------------


def test_spec_section_5_cites_the_storage_substrate_and_future_consumer() -> None:
    spec_path = PROJECT_ROOT / ".moai/specs/SPEC-LDBARMAP-001/spec.md"
    lines = spec_path.read_text(encoding="utf-8").splitlines()

    start = next(i for i, line in enumerate(lines) if line.startswith("## 5."))
    end = next(
        i for i, line in enumerate(lines) if i > start and line.startswith("1. **마디 지도와")
    )
    section_5 = "\n".join(lines[start:end])

    assert section_5.count("SPEC-LDBEAT-001") >= 1
    assert section_5.count("SongTimelineStore") >= 1
    assert section_5.count("TimelineDraftHistory") >= 1
    assert section_5.count("SongTimelineLibrary") >= 1
    assert section_5.count("SPEC-LDARRANGE-001") >= 1
