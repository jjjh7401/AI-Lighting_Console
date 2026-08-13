"""무드→포지션 매핑 — 결정론·무겹침·정식 이름 계약."""

import pytest

from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.spatial.position_moods import (
    POSITION_MOOD_TABLE,
    match_position_mood,
)


class TestTableContract:
    def test_every_label_and_alternative_is_a_canonical_look_name(self):
        names = set(BASIC_POSITION_SEQUENCE)
        for entry in POSITION_MOOD_TABLE:
            assert entry.label in names
            assert all(alt in names for alt in entry.alternatives)

    def test_keywords_never_overlap_between_entries(self):
        # 겹침은 동점을 만들고 동점은 표 순서라는 임의성으로 풀린다 — 금지.
        seen: dict[str, str] = {}
        for entry in POSITION_MOOD_TABLE:
            for keyword in entry.keywords:
                assert keyword not in seen, (
                    f"{keyword!r} appears in both {seen.get(keyword)} and {entry.label}"
                )
                seen[keyword] = entry.label

    def test_every_entry_carries_a_reason_and_alternatives(self):
        for entry in POSITION_MOOD_TABLE:
            assert entry.reason
            assert entry.alternatives


class TestMatching:
    @pytest.mark.parametrize(
        "text,label",
        [
            ("잔잔한 발라드 느낌으로 포지션 잡아줘", "Vocal DSC"),
            ("후렴에서 터지는 느낌으로", "Cross"),
            ("웅장한 피날레 연출", "Ring In"),
            ("관객 호응 유도하는 방향으로", "Audience"),
            ("화려하게 펼쳐지는 느낌", "Fan Out"),
            ("오프닝 등장 스포트라이트", "Center"),
            ("배경 커튼처럼", "Wall"),
            ("전환 대기용으로 리셋", "Home"),
        ],
    )
    def test_representative_sentences_map_to_their_look(self, text, label):
        suggestion = match_position_mood(text)
        assert suggestion is not None
        assert suggestion.entry.label == label

    def test_a_sentence_without_mood_words_returns_none(self):
        assert match_position_mood("장비 3번의 주소를 알려줘") is None

    def test_more_matches_win_over_fewer(self):
        # 발라드(Vocal) 1개 vs 후렴+터지(Cross) 2개 -> Cross.
        suggestion = match_position_mood("발라드지만 후렴은 터지게 포지션")
        assert suggestion is not None
        assert suggestion.entry.label == "Cross"
        assert suggestion.score == 2

    def test_matched_keywords_are_reported(self):
        suggestion = match_position_mood("웅장하고 장엄한 클라이맥스")
        assert suggestion is not None
        assert set(suggestion.matched) == {"웅장", "장엄", "클라이맥스"}

    def test_matching_is_case_insensitive_for_latin_keywords(self):
        suggestion = match_position_mood("EDM 드롭 포지션")
        assert suggestion is not None
        assert suggestion.entry.label == "Cross"
