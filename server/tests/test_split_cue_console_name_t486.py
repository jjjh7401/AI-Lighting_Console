"""카드 t486 ① — 쪼갠 큐의 콘솔 이름이 ``Intro 12`` 로 저장된다.

재현(t480 판정서 §6 2번): 마디 분할이 붙인 회차 접미사 ``(1/2)`` 를 콘솔 라벨
정리(``_safe_song_cue_name``)가 허용 문자 밖이라며 괄호·빗금만 지워, 숫자 둘이 붙은
``Intro 12`` 가 된다. 콘솔에서 읽으면 「열두 번째 Intro」다.

고침: 허용 문자 표(``_SAFE_SONG_CUE_NAME``)는 넓히지 않는다 — 괄호·빗금이 콘솔
명령의 따옴표 안에서 안전한지는 이 카드가 재지 않았다. 대신 접미사만 허용 문자
안의 모양 ``1 of 2`` 로 옮긴다. 표시용 이름(CUE SHEET·판정기가 읽는 ``(1/2)``)은
그대로 둔다.
"""

from __future__ import annotations

from server.design.profile import MusicProfile
from server.design.song_cue_render import _safe_song_cue_name
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import _split_sections_for_density


class TestSplitSuffixSurvivesTheConsoleName:
    def test_split_suffix_becomes_k_of_n(self):
        assert _safe_song_cue_name("Intro (1/2)", 1) == "Intro 1 of 2"
        assert _safe_song_cue_name("Chorus 3 (2/2)", 7) == "Chorus 3 2 of 2"

    def test_digits_of_the_suffix_are_not_glued_together(self):
        """결함의 모양 그 자체 — 회차 숫자 둘이 한 숫자로 붙으면 안 된다."""
        assert "12" not in _safe_song_cue_name("Intro (1/2)", 1)

    def test_unsplit_names_are_byte_identical(self):
        for name in ("Intro", "Verse 1", "Chorus 2", "Finale"):
            assert _safe_song_cue_name(name, 1) == name

    def test_the_safe_alphabet_was_not_widened(self):
        """대조군 — 접미사 모양이 아닌 괄호·빗금·따옴표·세미콜론은 여전히 지워진다."""
        assert _safe_song_cue_name("A'B;C/D(E)", 1) == "ABCDE"
        assert _safe_song_cue_name("Intro (a/b)", 1) == "Intro ab"

    def test_empty_or_digit_only_falls_back_to_section_number(self):
        assert _safe_song_cue_name("(1/2)", 4) == "1 of 2"
        assert _safe_song_cue_name("()", 4) == "Section 4"


class TestSplitPathEndToEnd:
    """실제 마디 분할 경로를 태워 콘솔 이름까지 간다."""

    def test_split_cues_carry_distinct_readable_console_names(self):
        profile = MusicProfile(bpm=120.0, genre=None)
        sections = [
            PositionSheetSection(name="Intro", start_ms=0, mood="", role="intro"),
            PositionSheetSection(name="Chorus 3", start_ms=10_000, mood="", role="chorus"),
            PositionSheetSection(name="Finale", start_ms=74_000, mood="", role="finale"),
        ]
        expanded, origins, _notes = _split_sections_for_density(
            sections, profile=profile, color_usage="split_swap"
        )
        split = [
            _safe_song_cue_name(section.name, index + 1)
            for index, (section, origin) in enumerate(zip(expanded, origins, strict=True))
            if origin == 1
        ]
        total = len(split)
        assert total > 1, "전제가 깨졌다 — 구간이 안 쪼개졌다"
        assert split == [f"Chorus 3 {k} of {total}" for k in range(1, total + 1)]
