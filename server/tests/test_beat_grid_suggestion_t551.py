"""SPEC-LDBEAT-001 M3 — 박자 격자 편집 경로 ③(AI 제안) 보류 메커니즘
(카드 t551 후속). 제안 생성~「적용」 사이에 격자·콘솔 어느 쪽도 바뀌지
않는다(결정④) — 이 모듈 자신은 `apply_beat_grid_edit`를 부르지 않는다.

제안 소스는 교체 가능(pluggable)하다. 이 카드는 실제 AI 백엔드를 갖지
않는다 — `NullSuggestionSource`가 그 상태를 정직하게 말하는 기본값이고,
이 시험의 "가짜 소스"는 결정적 테스트 더블일 뿐 AI 를 흉내 내지 않는다."""

from __future__ import annotations

from server.design.beat_grid_suggestion import (
    BeatGridSuggestion,
    NullSuggestionSource,
    PendingSuggestionStore,
)


def _fake_source(grid, bar, target):
    """결정적 테스트 더블 — AI 가 아니다. 입력을 그대로 반영해 테스트가
    재현 가능하게 만든다."""
    return (
        {"brightness": {"mode": "value", "value_percent": 55, "preset_no": None}},
        f"{target} {bar}마디를 55%로 제안(결정적 테스트 더블, AI 아님)",
    )


class TestNullSuggestionSourceIsHonestAboutAbsence:
    def test_null_source_never_fabricates_a_suggestion(self) -> None:
        store = PendingSuggestionStore()
        result = store.create({}, 11, "MOVER-U", source=NullSuggestionSource())
        assert result is None
        assert len(store) == 0


class TestPendingLifecycle:
    def test_create_with_a_source_yields_a_suggestion_and_keeps_it_pending(self) -> None:
        store = PendingSuggestionStore()
        grid = {"tracks": []}
        before = dict(grid)
        suggestion = store.create(grid, 11, "MOVER-U", source=_fake_source)
        assert isinstance(suggestion, BeatGridSuggestion)
        assert suggestion.bar == 11
        assert suggestion.target == "MOVER-U"
        assert suggestion.changes == {
            "brightness": {"mode": "value", "value_percent": 55, "preset_no": None}
        }
        assert len(store) == 1
        # 보류 생성은 grid를 전혀 건드리지 않는다(결정④ — 상태 diff 0).
        assert grid == before

    def test_peek_does_not_consume(self) -> None:
        store = PendingSuggestionStore()
        suggestion = store.create({}, 7, "BACK", source=_fake_source)
        assert store.peek(suggestion.suggestion_id) == suggestion
        assert len(store) == 1  # peek 뒤에도 그대로 남아 있다

    def test_consume_removes_and_returns_once(self) -> None:
        store = PendingSuggestionStore()
        suggestion = store.create({}, 7, "BACK", source=_fake_source)
        consumed = store.consume(suggestion.suggestion_id)
        assert consumed == suggestion
        assert len(store) == 0
        # 두 번째 소비는 이미 없다 — 지어내지 않고 None.
        assert store.consume(suggestion.suggestion_id) is None

    def test_unknown_id_consume_and_peek_return_none(self) -> None:
        store = PendingSuggestionStore()
        assert store.peek("no-such-id") is None
        assert store.consume("no-such-id") is None

    def test_two_suggestions_get_distinct_ids(self) -> None:
        store = PendingSuggestionStore()
        first = store.create({}, 7, "BACK", source=_fake_source)
        second = store.create({}, 11, "MOVER-U", source=_fake_source)
        assert first.suggestion_id != second.suggestion_id
        assert len(store) == 2
