"""Color Strip 산출 + 팔레트 해석 시험 — SPEC-LDDESIGN-001 M3
(REQ-LDDESIGN-026, 032, 033, 035, 카드 t436).

세 갈래를 잰다:

1. Color Strip(REQ-026)이 구간 큐만 대상으로 하고 프레이즈·원샷 큐를
   제외하는지(REQ-033, AC-LDDESIGN-031).
2. 워크시트 ``concept`` 필드가 요약·재작성 없이 원문 그대로 노출되는지
   (REQ-032, AC-LDDESIGN-046) — 비-ASCII·꼬리 공백 포함.
3. 팔레트 4칸이 비어 있을 때 인터뷰 Q2 답변으로 자동 초안이 채워지고
   (REQ-035, AC-LDDESIGN-047), 워크시트가 이미 채워져 있으면 초안을
   덮어쓰지 않는지.
"""

from __future__ import annotations

import pytest

from server.concept.color_strip import (
    ColorStripEntry,
    ConceptCue,
    PaletteDraft,
    compute_color_strip,
    draft_palette_from_interview,
    is_palette_blank,
    render_concept_bullet,
    resolve_palette,
)
from server.concept.worksheet import Palette


def _section_cue(section: str, occurrence: int, *, colors=("Blue",), area=(4, 8)) -> ConceptCue:
    lit, total = area
    return ConceptCue(
        section=section,
        occurrence=occurrence,
        layer="section",
        colors=colors,
        max_brightness=80.0,
        lit_groups=lit,
        total_groups=total,
        intent="구간 전환 의도 한 문장",
    )


def _phrase_cue(section: str, occurrence: int) -> ConceptCue:
    return ConceptCue(
        section=section,
        occurrence=occurrence,
        layer="phrase",
        colors=("Blue",),
        max_brightness=60.0,
        lit_groups=2,
        total_groups=8,
    )


def _one_shot_cue(section: str, occurrence: int) -> ConceptCue:
    return ConceptCue(
        section=section,
        occurrence=occurrence,
        layer="one_shot",
        colors=("White",),
        max_brightness=100.0,
        lit_groups=1,
        total_groups=8,
    )


class TestColorStripSectionCuesOnly:
    """REQ-026/033, AC-LDDESIGN-031 — 프레이즈·원샷 큐 제외, 구간 큐만."""

    def test_only_section_layer_cues_appear(self):
        cues = [
            _section_cue("Intro", 1),
            _phrase_cue("Intro", 1),
            _one_shot_cue("Intro", 1),
            _section_cue("Verse", 1),
        ]
        strip = compute_color_strip(cues)
        assert len(strip) == 2
        assert {entry.section for entry in strip} == {"Intro", "Verse"}

    def test_entry_carries_primary_secondary_brightness_area_intent(self):
        cue = _section_cue("Chorus", 1, colors=("Blue", "White"), area=(6, 8))
        strip = compute_color_strip([cue])
        assert strip == (
            ColorStripEntry(
                section="Chorus",
                occurrence=1,
                primary_color="Blue",
                secondary_color="White",
                max_brightness=80.0,
                area=0.75,
                intent="구간 전환 의도 한 문장",
            ),
        )

    def test_single_color_cue_has_no_secondary(self):
        strip = compute_color_strip([_section_cue("Outro", 1, colors=("Red",))])
        assert strip[0].secondary_color is None

    def test_empty_input_yields_empty_strip(self):
        assert compute_color_strip([]) == ()

    def test_only_phrase_and_one_shot_cues_yield_empty_strip(self):
        cues = [_phrase_cue("Verse", 1), _one_shot_cue("Verse", 1)]
        assert compute_color_strip(cues) == ()


class TestConceptBulletPassthrough:
    """REQ-032, AC-LDDESIGN-046 — 인과 불릿은 요약·재작성 없이 원문과
    바이트 동일하다(비-ASCII·꼬리 공백 포함)."""

    def test_plain_text_passes_through_unchanged(self):
        text = "이 곡은 에너제틱 → 그래서 레드 → 뜨거운 분위기 → 후렴 White hit"
        assert render_concept_bullet(text) == text

    def test_non_ascii_and_trailing_whitespace_survive_byte_identical(self):
        text = "레인은 비 오는 무대 → 그래서 블루 → 서늘한 분위기 → 브릿지 암전   \n"
        result = render_concept_bullet(text)
        assert result == text
        assert result.encode("utf-8") == text.encode("utf-8")


class TestPaletteBlankDetection:
    """`is_palette_blank` — 팔레트 4칸 중 필수 3칸이 비었는지 판정한다."""

    def test_none_is_blank(self):
        assert is_palette_blank(None) is True

    def test_fully_filled_palette_is_not_blank(self):
        palette = Palette(primary="Blue", secondary="White", climax="Red", reserved=("Red",))
        assert is_palette_blank(palette) is False

    def test_whitespace_only_fields_count_as_blank(self):
        palette = Palette(primary="  ", secondary="", climax="  ", reserved=())
        assert is_palette_blank(palette) is True


class TestDraftPaletteFromInterview:
    """REQ-035 — Q2 인터뷰 답변(색 경향 문자열)으로 팔레트 초안을 만든다."""

    def test_two_color_answer_splits_into_primary_and_secondary(self):
        palette = draft_palette_from_interview("블루와 화이트")
        assert palette.primary == "블루"
        assert palette.secondary == "화이트"
        assert palette.climax == "화이트"
        assert palette.reserved == ("화이트",)

    def test_single_color_answer_reuses_it_as_secondary_and_climax(self):
        palette = draft_palette_from_interview("레드")
        assert palette.primary == "레드"
        assert palette.secondary == "레드"
        assert palette.climax == "레드"

    def test_blank_answer_raises(self):
        with pytest.raises(ValueError):
            draft_palette_from_interview("   ")


class TestResolvePalette:
    """REQ-035, AC-LDDESIGN-047 — 비어 있을 때만 인터뷰 답변으로 채운다."""

    def test_blank_palette_with_interview_answer_yields_auto_draft(self):
        result = resolve_palette(None, interview_q2_answer="블루와 화이트")
        assert isinstance(result, PaletteDraft)
        assert result.auto_draft is True
        assert result.palette.primary == "블루"

    def test_filled_worksheet_palette_is_not_overwritten(self):
        worksheet_palette = Palette(
            primary="Green", secondary="Amber", climax="Red", reserved=("Red",)
        )
        result = resolve_palette(worksheet_palette, interview_q2_answer="블루와 화이트")
        assert result.auto_draft is False
        assert result.palette is worksheet_palette

    def test_blank_palette_without_interview_answer_raises(self):
        with pytest.raises(ValueError):
            resolve_palette(None, interview_q2_answer=None)
