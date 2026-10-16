"""마디 지도 저장 인터페이스 — 순수 함수 (SPEC-LDBARMAP-001 M4, 카드 t539).

콘솔에 닿지 않는다. librosa 를 쓰지 않는다. I/O 를 하지 않는다 — 입력도
출력도 순수 파이썬 사전뿐이다(``server/design/beat_grid.py``·
``cue_sheet_edit.py``와 같은 모양).

M4 가 확정한 저장 위치(옵션 A, ``timeline["bar_map"]`` 임베드, spec.md §5
열린 결정 0)는 이 모듈이 다루지 않는다 — 이 모듈은 그 키에 들어갈 **값**의
모양을 만들고(``build_bar_map_payload``) 검증하고(``validate_bar_map``)
타임라인 사전에 얹고 꺼내는(``attach_bar_map``/``read_bar_map``) 네 함수만
가진다. 실제 ``timeline["bar_map"]`` 읽기·쓰기 배선은 ``server/web/session.py``
의 ``store_timeline_bar_map``/``timeline_bar_map``이 맡는다.

일반화 규칙(감독 원칙 2026-10-10, 카드 t539 — spec.md §5 열린 결정 0):
LOVE ATTACK 고유값(82마디·112.35 BPM·4/4 전용)을 가정하지 않는다. 임의의
곡 길이, 임의의 박자표(분자 1~16, 분모 ∈ {1,2,4,8,16}), 못갖춘마디 유무,
마지막 못다 채운 마디를 받아들인다 — 그래서 아래 ``validate_bar_map``의
모든 규칙은 "이 곡"이 아니라 "박자표 분자"를 기준으로 쓴다.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "BAR_MAP_KEY",
    "BAR_MAP_SCHEMA_VERSION",
    "BarMapStoreError",
    "attach_bar_map",
    "build_bar_map_payload",
    "read_bar_map",
    "validate_bar_map",
]

#: ``timeline`` 사전에 마디 지도를 심는 키(REQ-LDBARMAP-010, M4 확정 — 옵션 A).
BAR_MAP_KEY = "bar_map"

#: 저장 스키마 버전(spec.md §5 열린 결정 0, 카드 t539). 마디 지도 구조가
#: 바뀌면 이 값을 올린다 — 지금은 1뿐이다.
BAR_MAP_SCHEMA_VERSION = 1

#: REQ-LDBARMAP-008 — events[].kind 어휘 4개 고정. 새 종류를 더하지 않는다.
_EVENT_KINDS = frozenset({"kick_entry", "build", "drop", "break"})

#: REQ-LDBARMAP-009 — 신뢰도 갈래(지도 보고서 [잰 값]/[추정]).
_EVENT_GRADES = frozenset({"measured", "estimated"})

#: 박자표 분모로 허용하는 값(spec.md §5 열린 결정 0 일반화 규칙).
_ALLOWED_DENOMINATORS = frozenset({1, 2, 4, 8, 16})

#: 저장 사전의 최상위 키 — 이 다섯과 다른 키가 있으면 거절한다(타이포 방지).
_TOP_LEVEL_KEYS = frozenset(
    {"schema_version", "bpm", "time_signature", "first_beat_offset", "bars", "events"}
)
_BAR_KEYS = frozenset({"bar", "start_ms", "beats_ms"})
#: 마디 항목의 선택 키 — 곡 안에서 정규화한 에너지(0~1). 없는 지도(옛 저장분)도 유효하다.
_BAR_OPTIONAL_KEYS = frozenset({"energy"})
_EVENT_KEYS = frozenset({"kind", "start_bar", "end_bar", "start_beat", "grade"})
#: 마디 지도의 선택 최상위 키 — 리듬 특징(rhythm.py). 없는 지도(옛 저장분)도 유효하다.
_TOP_LEVEL_OPTIONAL_KEYS = frozenset({"rhythm"})
_RHYTHM_KEYS = frozenset({"beats", "hits", "sections"})
_RHYTHM_BEAT_KEYS = frozenset(
    {"bar", "beat", "t_ms", "kick", "snare", "onset", "kick_hit", "snare_hit"}
)
_RHYTHM_HIT_KEYS = frozenset({"bar", "beat", "t_ms", "strength", "kind"})
_RHYTHM_SECTION_KEYS = frozenset({"start_bar", "end_bar", "bars", "start_ms", "end_ms", "d_level"})


class BarMapStoreError(ValueError):
    """마디 지도를 만들거나 저장하지 못했다 — 사유는 메시지 하나(단일 원인)."""


def _is_plain_int(value: object) -> bool:
    """``bool`` 은 ``int`` 의 서브클래스라 ``isinstance(x, int)`` 만으로는
    ``True``/``False`` 가 걸러지지 않는다 — 이 저장소의 다른 검증기들과 같은
    관행(``server/audio/bar_map.py`` ``derive_bars``)으로 명시적으로 뺀다."""
    return isinstance(value, int) and not isinstance(value, bool)


def _event_to_dict(event: Any) -> dict:
    """``BarEvent`` 인스턴스 또는 이미 사전 모양인 사건 하나를
    ``{kind, start_bar, end_bar, start_beat, grade}`` 로 통일한다.

    ``start_beat`` 는 ``BarEvent`` 에 그 필드가 없으므로 기본 1(spec.md §5
    열린 결정 0 — "기본 1, 지도 보고서의 당겨 들어오는 히트 같은 경우에만
    1이 아니다")이다."""
    if isinstance(event, Mapping):
        kind = event.get("kind")
        start_bar = event.get("start_bar")
        end_bar = event.get("end_bar")
        start_beat = event.get("start_beat", 1)
        grade = event.get("grade", "measured")
    else:
        kind = getattr(event, "kind", None)
        start_bar = getattr(event, "start_bar", None)
        end_bar = getattr(event, "end_bar", None)
        start_beat = getattr(event, "start_beat", 1)
        grade = getattr(event, "grade", "measured")
    return {
        "kind": kind,
        "start_bar": start_bar,
        "end_bar": end_bar,
        "start_beat": 1 if start_beat is None else start_beat,
        "grade": grade,
    }


def build_bar_map_payload(
    beat_times_ms: Sequence[int],
    first_beat_offset: int,
    *,
    bpm: float,
    time_signature: tuple[int, int] = (4, 4),
    events: Sequence[Any] = (),
    bar_energy: Mapping[int, float] | None = None,
) -> dict:
    """자동 비트 격자 + 사람이 지정한 첫 박 오프셋 → 저장용 마디 지도 사전.

    ``beat_times_ms`` 를 마디로 묶는 규칙은 박자표에 **일반적**이다(LOVE
    ATTACK 4/4 전용이 아니다, spec.md §5 열린 결정 0 일반화 규칙) —
    ``first_beat_offset`` 이전의 박들은 못갖춘마디(``bar: 0``, 못갖춘마디가
    없으면 생략)이고, 그 뒤로는 박자표 분자 개씩 연속해서 마디 1, 2, …로
    번호를 매긴다. 마지막 묶음은 분자보다 적을 수 있다(못다 채운 마디).

    돌려주기 전에 ``validate_bar_map`` 으로 스스로 검증한다 — 잘못된 입력이
    조용히 저장되지 않는다."""
    numerator, denominator = time_signature
    if not _is_plain_int(first_beat_offset):
        raise BarMapStoreError(f"첫 박 오프셋은 정수여야 합니다: {first_beat_offset!r}")
    if not _is_plain_int(numerator) or numerator <= 0:
        raise BarMapStoreError(f"박자표 분자는 양의 정수여야 합니다: {numerator!r}")
    if not (0 <= first_beat_offset < numerator):
        raise BarMapStoreError(
            f"첫 박 오프셋은 0~{numerator - 1} 범위여야 합니다: {first_beat_offset}"
        )
    beats = [int(t) for t in beat_times_ms]

    pickup = beats[:first_beat_offset]
    remaining = beats[first_beat_offset:]

    bars: list[dict] = []
    if pickup:
        bars.append({"bar": 0, "start_ms": pickup[0], "beats_ms": list(pickup)})
    bar_no = 1
    for i in range(0, len(remaining), numerator):
        chunk = remaining[i : i + numerator]
        if not chunk:
            continue
        bars.append({"bar": bar_no, "start_ms": chunk[0], "beats_ms": list(chunk)})
        bar_no += 1
    if bar_energy:
        for bar in bars:
            value = bar_energy.get(bar["bar"])
            if value is not None:
                bar["energy"] = float(value)

    events_payload = [_event_to_dict(event) for event in events]

    payload = {
        "schema_version": BAR_MAP_SCHEMA_VERSION,
        "bpm": float(bpm),
        "time_signature": [int(numerator), int(denominator)],
        "first_beat_offset": int(first_beat_offset),
        "bars": bars,
        "events": events_payload,
    }

    reason = validate_bar_map(payload)
    if reason is not None:
        raise BarMapStoreError(reason)
    return payload


# @MX:ANCHOR: [AUTO] validate_bar_map — build_bar_map_payload/attach_bar_map/
# read_bar_map/ChatSession.store_timeline_bar_map 네 곳이 부른다(fan_in 4).
# @MX:REASON: 저장 스키마의 유일한 검증 관문 — 이 함수 하나가 거부하면
# timeline["bar_map"] 에 잘못된 모양이 들어가는 길이 전부 막힌다
# (REQ-LDBARMAP-010, acceptance.md AC-LDBARMAP-010 조건 4).
def validate_bar_map(payload: object) -> str | None:
    """저장 스키마 검증 — 문제가 없으면 ``None``, 있으면 한국어 이유 하나.

    규칙은 spec.md §5 열린 결정 0의 확정 모양 + 일반화 규칙을 그대로 따른다
    (LOVE ATTACK 전용 상수를 쓰지 않는다 — 분자·분모는 매번 ``payload``
    자신에서 읽는다). 타이포로 들어온 알 수 없는 필드는 전부 거절한다 —
    조용히 무시하면 저장된 값과 쓴 값이 다르게 읽히는 결함을 놓친다."""
    if not isinstance(payload, Mapping):
        return "마디 지도는 사전이어야 합니다."

    extra = set(payload.keys()) - _TOP_LEVEL_KEYS - _TOP_LEVEL_OPTIONAL_KEYS
    if extra:
        return f"마디 지도에 알 수 없는 필드가 있습니다: {sorted(extra)}"
    missing = _TOP_LEVEL_KEYS - set(payload.keys())
    if missing:
        return f"마디 지도에 필요한 필드가 없습니다: {sorted(missing)}"

    schema_version = payload["schema_version"]
    if not _is_plain_int(schema_version) or schema_version != BAR_MAP_SCHEMA_VERSION:
        return f"schema_version 은 {BAR_MAP_SCHEMA_VERSION} 이어야 합니다: {schema_version!r}"

    bpm = payload["bpm"]
    if isinstance(bpm, bool) or not isinstance(bpm, int | float):
        return f"bpm 은 숫자여야 합니다: {bpm!r}"
    bpm_value = float(bpm)
    if bpm_value != bpm_value or bpm_value in (float("inf"), float("-inf")):
        return f"bpm 은 유한한 값이어야 합니다: {bpm!r}"
    if bpm_value <= 0:
        return f"bpm 은 0보다 커야 합니다: {bpm!r}"

    time_signature = payload["time_signature"]
    if (
        not isinstance(time_signature, Sequence)
        or isinstance(time_signature, str | bytes)
        or len(time_signature) != 2
    ):
        return f"time_signature 는 [분자, 분모] 2개짜리여야 합니다: {time_signature!r}"
    numerator, denominator = time_signature
    if not _is_plain_int(numerator) or not (1 <= numerator <= 16):
        return f"time_signature 분자는 1~16 사이 정수여야 합니다: {numerator!r}"
    if not _is_plain_int(denominator) or denominator not in _ALLOWED_DENOMINATORS:
        return (
            "time_signature 분모는 "
            f"{sorted(_ALLOWED_DENOMINATORS)} 중 하나여야 합니다: {denominator!r}"
        )

    first_beat_offset = payload["first_beat_offset"]
    if not _is_plain_int(first_beat_offset) or not (0 <= first_beat_offset < numerator):
        return (
            f"first_beat_offset 은 0~{numerator - 1} 범위의 정수여야 합니다: {first_beat_offset!r}"
        )

    bars = payload["bars"]
    reason = _validate_bars(bars, numerator=numerator)
    if reason is not None:
        return reason

    events = payload["events"]
    bar_numbers = {bar["bar"] for bar in bars}
    reason = _validate_events(events, numerator=numerator, bar_numbers=bar_numbers)
    if reason is not None:
        return reason
    if "rhythm" in payload:
        return _validate_rhythm(payload["rhythm"], bars)
    return None


def attach_rhythm(payload: Mapping[str, object], rhythm: Mapping[str, object]) -> dict:
    """마디 지도 사전에 ``rhythm`` 블록을 붙이고 저장 스키마로 다시 검증한다(선택 키)."""
    merged = {**payload, "rhythm": dict(rhythm)}
    problem = validate_bar_map(merged)
    if problem is not None:
        raise BarMapStoreError(problem)
    return merged


def _is_unit_number(value: object) -> bool:
    """0~1 사이의 실수(또는 정수)다. bool 과 NaN·무한대는 아니다."""
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and 0.0 <= float(value) <= 1.0
    )


def _validate_rhythm(rhythm: object, bars: list) -> str | None:
    """``rhythm`` 블록 검증. 박은 마디 지도의 ``beats_ms`` 와 한 개씩 시각까지 맞아야 하고,
    히트와 구간은 그 박과 마디에 묶여야 한다. 점수는 0~1, 문턱 판정은 bool 이다."""
    if not isinstance(rhythm, Mapping):
        return "rhythm 은 사전이어야 합니다."
    if set(rhythm.keys()) != _RHYTHM_KEYS:
        return f"rhythm 필드가 맞지 않습니다: {sorted(rhythm.keys())}"
    beats = rhythm["beats"]
    hits = rhythm["hits"]
    sections = rhythm["sections"]
    if not isinstance(beats, list) or not isinstance(hits, list) or not isinstance(sections, list):
        return "rhythm.beats·hits·sections 는 목록이어야 합니다."

    beat_times = {bar["bar"]: list(bar["beats_ms"]) for bar in bars}
    bar_starts = {bar["bar"]: bar["start_ms"] for bar in bars}
    expected = sum(len(times) for times in beat_times.values())
    if len(beats) != expected:
        return f"rhythm.beats 는 마디 지도의 박 수({expected})와 같아야 합니다: {len(beats)}"

    seen: dict[tuple[int, int], int] = {}
    previous_ms = -1
    for item in beats:
        if not isinstance(item, Mapping) or set(item.keys()) != _RHYTHM_BEAT_KEYS:
            return "rhythm.beats 항목 필드가 맞지 않습니다."
        bar_no, beat_no, t_ms = item["bar"], item["beat"], item["t_ms"]
        if not _is_plain_int(bar_no) or bar_no not in beat_times:
            return f"rhythm.beats 의 마디 번호가 마디 지도에 없습니다: {bar_no!r}"
        if not _is_plain_int(beat_no) or not (1 <= beat_no <= len(beat_times[bar_no])):
            return f"rhythm.beats 의 박 번호가 마디 {bar_no} 범위를 벗어났습니다: {beat_no!r}"
        if not _is_plain_int(t_ms) or t_ms != beat_times[bar_no][beat_no - 1]:
            return f"rhythm.beats 의 t_ms 가 박 시각과 다릅니다(마디 {bar_no} 박 {beat_no})"
        if t_ms <= previous_ms:
            return "rhythm.beats 는 시간 순서여야 합니다."
        previous_ms = t_ms
        for name in ("kick", "snare", "onset"):
            if not _is_unit_number(item[name]):
                return f"rhythm.beats.{name} 은 0~1 사이 숫자여야 합니다: {item[name]!r}"
        for name in ("kick_hit", "snare_hit"):
            if not isinstance(item[name], bool):
                return f"rhythm.beats.{name} 은 bool 이어야 합니다: {item[name]!r}"
        seen[(bar_no, beat_no)] = t_ms

    for item in hits:
        if not isinstance(item, Mapping) or set(item.keys()) != _RHYTHM_HIT_KEYS:
            return "rhythm.hits 항목 필드가 맞지 않습니다."
        bar_no, beat_no = item["bar"], item["beat"]
        if (
            not (_is_plain_int(bar_no) and _is_plain_int(beat_no))
            or seen.get((bar_no, beat_no)) != item["t_ms"]
        ):
            return f"rhythm.hits 가 박에 묶이지 않습니다: 마디 {bar_no!r} 박 {beat_no!r}"
        if item["kind"] != "big":
            return f'rhythm.hits.kind 는 "big" 이어야 합니다: {item["kind"]!r}'
        if not _is_unit_number(item["strength"]):
            return f"rhythm.hits.strength 는 0~1 사이 숫자여야 합니다: {item['strength']!r}"

    previous_end = -1
    for item in sections:
        if not isinstance(item, Mapping) or set(item.keys()) != _RHYTHM_SECTION_KEYS:
            return "rhythm.sections 항목 필드가 맞지 않습니다."
        start_bar, end_bar = item["start_bar"], item["end_bar"]
        if not (_is_plain_int(start_bar) and _is_plain_int(end_bar)):
            return f"rhythm.sections 의 마디 번호는 정수여야 합니다: {start_bar!r}~{end_bar!r}"
        if start_bar not in beat_times or end_bar not in beat_times or start_bar > end_bar:
            return f"rhythm.sections 의 마디 범위가 맞지 않습니다: {start_bar}~{end_bar}"
        if start_bar <= previous_end:
            return "rhythm.sections 는 겹치지 않아야 합니다."
        if not _is_plain_int(item["bars"]) or item["bars"] != end_bar - start_bar + 1:
            return (
                f"rhythm.sections.bars 는 끝 마디 - 시작 마디 + 1 이어야 합니다: {item['bars']!r}"
            )
        if not _is_plain_int(item["start_ms"]) or item["start_ms"] != bar_starts[start_bar]:
            return f"rhythm.sections.start_ms 가 마디 {start_bar} 시작과 다릅니다"
        if not _is_plain_int(item["end_ms"]) or item["end_ms"] < item["start_ms"]:
            return f"rhythm.sections.end_ms 가 시작보다 앞입니다: {item['end_ms']!r}"
        if not _is_plain_int(item["d_level"]) or not (1 <= item["d_level"] <= 5):
            return f"rhythm.sections.d_level 은 1~5 정수여야 합니다: {item['d_level']!r}"
        previous_end = end_bar
    return None


def _validate_bars(bars: object, *, numerator: int) -> str | None:
    if not isinstance(bars, list) or not bars:
        return "bars 는 비어 있지 않은 목록이어야 합니다."

    previous_ms = -1
    expected_bar = None
    for index, bar in enumerate(bars):
        if not isinstance(bar, Mapping):
            return f"bars[{index}] 는 사전이어야 합니다."
        extra = set(bar.keys()) - _BAR_KEYS - _BAR_OPTIONAL_KEYS
        if extra:
            return f"bars[{index}] 에 알 수 없는 필드가 있습니다: {sorted(extra)}"
        missing = _BAR_KEYS - set(bar.keys())
        if missing:
            return f"bars[{index}] 에 필요한 필드가 없습니다: {sorted(missing)}"

        energy = bar.get("energy")
        if "energy" in bar and (
            isinstance(energy, bool)
            or not isinstance(energy, int | float)
            or not (0.0 <= float(energy) <= 1.0)
        ):
            return f"bars[{index}].energy 는 0~1 사이 숫자여야 합니다: {energy!r}"

        bar_no = bar["bar"]
        if not _is_plain_int(bar_no) or bar_no < 0:
            return f"bars[{index}].bar 는 0 이상의 정수여야 합니다: {bar_no!r}"
        if expected_bar is None:
            if bar_no not in (0, 1):
                return f"첫 마디 번호는 0 또는 1이어야 합니다: {bar_no}"
            expected_bar = bar_no
        elif bar_no != expected_bar:
            return f"마디 번호가 연속하지 않습니다 — {expected_bar} 다음에 {bar_no}."
        expected_bar += 1

        beats_ms = bar["beats_ms"]
        if not isinstance(beats_ms, list) or not beats_ms:
            return f"bars[{index}].beats_ms 는 비어 있지 않은 목록이어야 합니다."

        is_last = index == len(bars) - 1
        if bar_no == 0 or is_last:
            beat_count_ok = 1 <= len(beats_ms) <= numerator
        else:
            beat_count_ok = len(beats_ms) == numerator
        if not beat_count_ok:
            return (
                f"bars[{index}](마디 {bar_no})의 박 개수가 박자표 분자({numerator})와 "
                f"맞지 않습니다: {len(beats_ms)}개."
            )

        start_ms = bar["start_ms"]
        if not _is_plain_int(start_ms) or start_ms < 0:
            return f"bars[{index}].start_ms 는 0 이상의 정수여야 합니다: {start_ms!r}"
        if start_ms != beats_ms[0]:
            return f"bars[{index}].start_ms 는 beats_ms 의 첫 값과 같아야 합니다."

        for beat_index, ms in enumerate(beats_ms):
            if not _is_plain_int(ms) or ms < 0:
                return f"bars[{index}].beats_ms[{beat_index}] 는 0 이상의 정수여야 합니다: {ms!r}"
            if ms <= previous_ms:
                return (
                    f"bars[{index}].beats_ms[{beat_index}] 는 바로 앞 박 시각보다 "
                    "커야 합니다(엄격히 증가)."
                )
            previous_ms = ms

    return None


def _validate_events(events: object, *, numerator: int, bar_numbers: set[int]) -> str | None:
    if not isinstance(events, list):
        return "events 는 목록이어야 합니다."

    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            return f"events[{index}] 는 사전이어야 합니다."
        extra = set(event.keys()) - _EVENT_KEYS
        if extra:
            return f"events[{index}] 에 알 수 없는 필드가 있습니다: {sorted(extra)}"
        missing = _EVENT_KEYS - set(event.keys())
        if missing:
            return f"events[{index}] 에 필요한 필드가 없습니다: {sorted(missing)}"

        kind = event["kind"]
        if kind not in _EVENT_KINDS:
            return f"events[{index}].kind 는 {sorted(_EVENT_KINDS)} 중 하나여야 합니다: {kind!r}"

        start_bar = event["start_bar"]
        end_bar = event["end_bar"]
        if not _is_plain_int(start_bar):
            return f"events[{index}].start_bar 는 정수여야 합니다: {start_bar!r}"
        if not _is_plain_int(end_bar):
            return f"events[{index}].end_bar 는 정수여야 합니다: {end_bar!r}"
        if start_bar > end_bar:
            return f"events[{index}] 는 start_bar <= end_bar 여야 합니다: {start_bar} > {end_bar}."
        if start_bar not in bar_numbers or end_bar not in bar_numbers:
            return f"events[{index}] 의 마디 범위가 저장된 마디 밖입니다: {start_bar}~{end_bar}."

        start_beat = event["start_beat"]
        if not _is_plain_int(start_beat) or not (1 <= start_beat <= numerator):
            return (
                f"events[{index}].start_beat 는 1~{numerator} 범위의 정수여야 합니다: "
                f"{start_beat!r}"
            )

        grade = event["grade"]
        if grade not in _EVENT_GRADES:
            return f"events[{index}].grade 는 {sorted(_EVENT_GRADES)} 중 하나여야 합니다: {grade!r}"

    return None


def attach_bar_map(timeline: Mapping[str, object], payload: Mapping[str, object]) -> dict:
    """``timeline`` 사전의 사본에 마디 지도를 싣는다 — 원본은 건드리지 않는다
    (``server/design/beat_grid.py`` ``attach_beat_grid_default`` 와 같은
    사본-후-머지 관행). 잘못된 ``payload`` 는 쓰기 전에 거절한다."""
    reason = validate_bar_map(payload)
    if reason is not None:
        raise BarMapStoreError(reason)
    merged = dict(timeline)
    merged[BAR_MAP_KEY] = copy.deepcopy(payload)
    return merged


def read_bar_map(timeline: Mapping[str, object]) -> dict | None:
    """``timeline`` 에서 마디 지도를 꺼낸다 — 없거나 유효하지 않으면 ``None``
    (``SongTimelineStore`` 와 같은 fail-open 읽기, 예외를 내보내지 않는다)."""
    if not isinstance(timeline, Mapping):
        return None
    payload = timeline.get(BAR_MAP_KEY)
    if payload is None:
        return None
    if validate_bar_map(payload) is not None:
        return None
    return copy.deepcopy(payload)
