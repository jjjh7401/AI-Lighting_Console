"""카드 t446 — REQ-064 무버 소등 조건을 Verse 조립기에 배선한 결과를 시험한다.

감독 결정(2026-09-27): 다음 후렴이 새 포지션을 요구하지 않아 무버를 끄지
않는 절에서는 무버를 **그 절 밝기로 낮춘다** — 포지션은 그대로 둔다.
"낮춘다"이므로 절에 들어오기 전 무버가 더 어두웠으면(꺼져 있었으면) 그
값을 올리지 않는다(``min(직전 밝기, 절 밝기)``).

Bridge 는 배선하지 않는다 — REQ-046 이 KEY·BACK 외 그룹을 무조건 끄라고
정하고, 감독 결정도 절만 다룬다.
"""

from __future__ import annotations

from server.concept.density import MOVER_GROUPS, SectionOccurrence, compile_density
from server.concept.resolver import resolve_sequence

BPM = 120.0  # 1마디 = 2초
VERSE_TOP = 45
VERSE_REPEAT_TOP = int(round(VERSE_TOP * 0.85))


def _s(name: str, occurrence: int, start: float, end: float) -> SectionOccurrence:
    return SectionOccurrence(section=name, occurrence=occurrence, start=start, end=end)


def _states_by_section(sections: list[SectionOccurrence]):
    result = compile_density(sections, BPM)
    states = resolve_sequence(result.sequence)
    out: dict[tuple[str, int], tuple[object, object]] = {}
    prev_track = None
    for row, state in zip(result.sequence, states, strict=True):
        if row["kind"] == "section":
            out[(row["section"], row["occurrence"])] = (prev_track, state)
        if row.get("tracking") != "cue_only":
            prev_track = state
    return out


def _mover_dims(state) -> set[int]:
    return {state.dim.get(m, 0) for m in MOVER_GROUPS}


# 후렴 3회차(k=3)가 무버를 켜고 포지션 "front" 를 정한다(density._chorus_position).
_THREE_CHORUSES = [
    _s("Chorus", 1, 0.0, 8.0),
    _s("Chorus", 2, 8.0, 16.0),
    _s("Chorus", 3, 16.0, 24.0),
]


class TestVerseKeepsMoversAtVerseBrightness:
    def test_same_next_position_lowers_movers_to_verse_level_and_holds_position(self) -> None:
        # 다음 후렴(k=4, 직전이 절)은 "front" — 지금 위치와 같아 옮길 이유가 없다.
        sections = [*_THREE_CHORUSES, _s("Verse", 1, 24.0, 40.0), _s("Chorus", 4, 40.0, 48.0)]
        pre, verse = _states_by_section(sections)[("Verse", 1)]
        assert _mover_dims(pre) == {84}  # 전제: 절 직전 무버가 켜져 있다
        assert _mover_dims(verse) == {VERSE_TOP}
        assert verse.pos == pre.pos == "front"
        assert max(verse.dim.values()) == VERSE_TOP

    def test_repeat_verse_uses_its_own_reduced_level(self) -> None:
        sections = [
            *_THREE_CHORUSES,
            _s("Verse", 1, 24.0, 40.0),
            _s("Chorus", 4, 40.0, 48.0),
            _s("Verse", 2, 48.0, 64.0),
            _s("Chorus", 5, 64.0, 72.0),
        ]
        pre, verse2 = _states_by_section(sections)[("Verse", 2)]
        assert max(_mover_dims(pre)) > VERSE_REPEAT_TOP  # 전제
        assert _mover_dims(verse2) == {VERSE_REPEAT_TOP}
        assert max(verse2.dim.values()) == VERSE_REPEAT_TOP


class TestVerseTurnsMoversOffWhenRepositioning:
    def test_next_chorus_needs_new_position_turns_movers_off(self) -> None:
        # Final Chorus(직전이 절)는 "audience" — 지금 "front" 와 달라 옮겨야 한다.
        sections = [*_THREE_CHORUSES, _s("Verse", 1, 24.0, 40.0), _s("Final Chorus", 1, 40.0, 48.0)]
        pre, verse = _states_by_section(sections)[("Verse", 1)]
        assert _mover_dims(pre) == {84}  # 전제
        assert _mover_dims(verse) == {0}

    def test_repeat_verse_turns_movers_off_even_if_verse_1_kept_them(self) -> None:
        # Verse 2 는 Verse 1 을 restore 하므로, Verse 1 이 무버를 켜 둔 채면
        # 그 값이 새어 들어온다 — 옮겨야 하는 회차에서는 다시 꺼야 한다.
        sections = [
            *_THREE_CHORUSES,
            _s("Verse", 1, 24.0, 40.0),
            _s("Chorus", 4, 40.0, 48.0),
            _s("Verse", 2, 48.0, 64.0),
            _s("Final Chorus", 1, 64.0, 72.0),
        ]
        by = _states_by_section(sections)
        assert _mover_dims(by[("Verse", 1)][1]) == {VERSE_TOP}  # 전제
        assert _mover_dims(by[("Verse", 2)][1]) == {0}


class TestVerseNeverRaisesMovers:
    def test_movers_off_before_verse_stay_off(self) -> None:
        sections = [
            _s("Intro", 1, 0.0, 8.0),
            _s("Verse", 1, 8.0, 24.0),
            _s("Chorus", 1, 24.0, 32.0),
        ]
        pre, verse = _states_by_section(sections)[("Verse", 1)]
        assert _mover_dims(pre) == {0}
        assert _mover_dims(verse) == {0}
