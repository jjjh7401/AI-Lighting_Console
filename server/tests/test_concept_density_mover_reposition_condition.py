"""카드 t439 §④b M5 판단 2 — REQ-064 "다음 후렴을 위해 포지션을 바꿔야
하면"의 **조건 계산**만 시험한다(``server.concept.density._next_chorus_
position``/``_movers_need_repositioning``).

**이 시험이 고정하는 것은 조건 계산 로직뿐이다 — Verse/Bridge 조립기
배선은 하지 않았다.** ``density.py`` 안의 Verse 1회차·Bridge 주석이
설명하듯, 이 조건을 실제로 무버 소등 여부에 연결해 보니
``TOO_COOL_RAW`` 픽스처에서 AC-LDDESIGN-010 이 고정한 밝기 회귀 시험
(``test_concept_density.py``
``test_verse_first_occurrence_clears_prior_mover_and_wash_state``, 45%
기대)이 100%로 깨졌다 — 다음 후렴이 지금과 같은 포지션이면 무버가
이전 후렴의 최대 밝기를 그대로 들고 절로 들어오기 때문이다. REQ-064는
"포지션을 안 바꾼다"만 말하지 "밝기도 그대로 둔다"는 말하지 않는데, 이
둘을 하나의 이분법(소등/비소등)으로 묶으면 후자가 원치 않게 딸려 온다.
밝기를 절 수준으로는 낮추되 포지션만 유지하는 제3의 동작이 필요할 수
있지만, 그 값은 spec.md 에 없어 지어내지 않는다 — 감독 확인이 필요한
자리로 리드에게 보고한다(카드 지시가 gates.py 13게이트 행렬에 요구한
"바뀌면 재고정하지 말고 보고"와 같은 원칙을 이 회귀에도 적용했다).
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
