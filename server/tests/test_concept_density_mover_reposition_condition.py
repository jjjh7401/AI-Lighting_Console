"""카드 t439 §④b M5 판단 2 — REQ-064 "다음 후렴을 위해 포지션을 바꿔야
하면"의 **조건 계산**만 시험한다(``server.concept.density._next_chorus_
position``/``_movers_need_repositioning``).

배선은 카드 t446 이 했다 — 감독 결정(2026-09-27)으로 무버를 끄지 않는 절은
무버를 절 밝기로 낮춘다. 배선 결과 시험은
``test_concept_density_verse_mover_wiring.py`` 에 있다.
"""

from __future__ import annotations

from server.concept.density import (
    SectionOccurrence,
    _movers_need_repositioning,
    _next_chorus_position,
)


def _section(name: str, occurrence: int, start: float, end: float) -> SectionOccurrence:
    return SectionOccurrence(section=name, occurrence=occurrence, start=start, end=end)


class TestNextChorusPosition:
    def test_no_chorus_after_from_index_returns_none(self) -> None:
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Verse", 1, 6.0, 17.0),
            _section("Outro", 1, 17.0, 25.0),
        ]
        assert _next_chorus_position(sections, 1, {0: 1}) is None

    def test_finds_first_chorus_family_section_after_from_index(self) -> None:
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Verse", 1, 6.0, 17.0),
            _section("Chorus", 2, 17.0, 28.0),
        ]
        # k=2 → REQ-043 "side" (density._chorus_position 문면 그대로).
        assert _next_chorus_position(sections, 1, {0: 1, 2: 2}) == "side"

    def test_chorus_immediately_after_another_chorus_can_return_none(self) -> None:
        # k>=4 이면서 직전이 후렴이면 _chorus_position 자체가 None(포지션
        # 유지) — `_next_chorus_position` 도 그 None 을 그대로 전달한다.
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Chorus", 2, 6.0, 12.0),
            _section("Chorus", 3, 12.0, 18.0),
            _section("Chorus", 4, 18.0, 24.0),
        ]
        k_by_index = {0: 1, 1: 2, 2: 3, 3: 4}
        assert _next_chorus_position(sections, 2, k_by_index) is None


class TestMoversNeedRepositioning:
    """REQ-064 — 배차서가 지정한 시나리오("다음 후렴의 포지션이 지금과
    같으면 무버를 강제로 끄지 않는다")를 정확히 재현한다."""

    def test_verse_before_chorus_with_same_position_does_not_need_repositioning(self) -> None:
        # 배차서 지정 시나리오 그대로 — TOO_COOL_RAW 가 실측으로 낸
        # 것과 같은 모양(현재 포지션 "front", 다음 후렴도 k!=2 라 "front").
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Verse", 1, 6.0, 17.0),
            _section("Chorus", 2, 17.0, 28.0),  # k=5 는 아래서 직접 지정
        ]
        k_by_index = {0: 1, 2: 5}
        current_pos = "front"  # k=1 후렴이 REQ-043 문면대로 정한 값.
        assert _movers_need_repositioning(sections, 1, k_by_index, current_pos) is False

    def test_verse_before_chorus_with_different_position_needs_repositioning(self) -> None:
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Verse", 1, 6.0, 17.0),
            _section("Chorus", 2, 17.0, 28.0),
        ]
        k_by_index = {0: 1, 2: 2}  # k=2 → "side", current_pos 와 다르다.
        assert _movers_need_repositioning(sections, 1, k_by_index, "front") is True

    def test_bridge_with_no_chorus_afterward_does_not_need_repositioning(self) -> None:
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Bridge", 1, 6.0, 12.0),
            _section("Outro", 1, 12.0, 20.0),
        ]
        assert _movers_need_repositioning(sections, 1, {0: 1}, "front") is False

    def test_next_chorus_position_none_does_not_need_repositioning(self) -> None:
        # 다음 후렴 자체가 새 포지션을 요구하지 않으면(None) 옮길 이유가
        # 없다 — current_pos 값과 무관하게 False.
        sections = [
            _section("Verse", 1, 0.0, 10.0),
            _section("Chorus", 1, 10.0, 16.0),
            _section("Chorus", 2, 16.0, 22.0),
            _section("Chorus", 3, 22.0, 28.0),
            _section("Chorus", 4, 28.0, 34.0),
        ]
        k_by_index = {1: 1, 2: 2, 3: 3, 4: 4}
        assert _movers_need_repositioning(sections, 3, k_by_index, "anything") is False


class TestPredictionMatchesAssembler:
    """카드 t446 — 예측(:func:`_next_chorus_position`)이 조립기가 실제로
    쓰는 포지션과 같아야 한다. 전에는 k=1 의 "back" 과 Final Chorus 의
    "audience" 를 "front" 로 잘못 봤다."""

    def test_first_chorus_is_back(self) -> None:
        sections = [_section("Verse", 1, 0.0, 10.0), _section("Chorus", 1, 10.0, 16.0)]
        assert _next_chorus_position(sections, 0, {1: 1}) == "back"

    def test_final_chorus_after_verse_is_audience(self) -> None:
        sections = [
            _section("Chorus", 1, 0.0, 6.0),
            _section("Verse", 1, 6.0, 16.0),
            _section("Final Chorus", 1, 16.0, 24.0),
        ]
        assert _next_chorus_position(sections, 1, {0: 1, 2: 2}) == "audience"
