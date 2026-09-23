"""컬러 검사기 시험 — SPEC-LDDESIGN-001 M3 (REQ-LDDESIGN-027~031 narrow,
034, 카드 t436).

REQ-031 은 이 배차(t436)에서 **좁은 해석**으로 읽는다 — 신규 컬러 검사
코드는 `_arc_palette`/`_per_chorus_palette` 를 import 하거나 호출하지
않는다(REQ-031 narrow reading). `server/web/session.py` 자체를 고쳐 실제
출력 색을 바꾸는 일(REQ-004)은 이 SPEC의 M6 스코프다 — 여기서는 건드리지
않는다.

t409 흰색 경계(카드 t409) — 색 정체성 비교는 `color_names.py` 의
`_HUE_MODIFIER_STRIP` 을 쓰지 않는다. 그 정규식은 "warm"/"cold" 수식어를
벗겨 Warm White 와 Cool White 를 같은 색으로 뭉갠다 — 이 검사기는 대소문자·
공백만 정규화하고 Warm White 와 Cool White 를 항상 다른 색으로 다룬다.
"""

from __future__ import annotations

from pathlib import Path

from server.concept.color_lint import (
    Constraints,
    check_adjacent_bridge,
    check_chorus_identity,
    check_reserved_color_release,
    check_skin_tone_clash,
    check_underpainting,
)
from server.concept.color_strip import ConceptCue


def _cue(
    section: str,
    occurrence: int,
    *,
    colors=(),
    desaturated: bool = False,
    lit_group_ids: frozenset[str] = frozenset(),
    layer: str = "section",
) -> ConceptCue:
    return ConceptCue(
        section=section,
        occurrence=occurrence,
        layer=layer,
        colors=colors,
        max_brightness=80.0,
        lit_groups=len(lit_group_ids) or 4,
        total_groups=8,
        desaturated=desaturated,
        lit_group_ids=lit_group_ids,
    )


# --- REQ-027 — 유보색은 해제 이전에 나타나면 위반 --------------------------


class TestReservedColorRelease:
    def test_reserved_color_before_release_is_a_violation(self):
        cues = [
            _cue("Verse", 1, colors=("Blue",)),
            _cue("Chorus", 1, colors=("Red",)),  # 유보색 Red 조기 등장
            _cue("Final Chorus", 1, colors=("Red", "White")),  # 해제
        ]
        result = check_reserved_color_release(
            cues, reserved=("Red",), release_section="Final Chorus"
        )
        assert result.status == "fail"
        assert len(result.violations) == 1
        assert result.violations[0].section == "Chorus"

    def test_reserved_color_only_at_and_after_release_passes(self):
        cues = [
            _cue("Verse", 1, colors=("Blue",)),
            _cue("Chorus", 1, colors=("Blue",)),
            _cue("Final Chorus", 1, colors=("Red", "White")),
        ]
        result = check_reserved_color_release(
            cues, reserved=("Red",), release_section="Final Chorus"
        )
        assert result.status == "pass"
        assert result.violations == ()

    def test_no_reserved_colors_is_vacuously_pass(self):
        cues = [_cue("Verse", 1, colors=("Blue",))]
        result = check_reserved_color_release(cues, reserved=(), release_section="Final Chorus")
        assert result.status == "pass"

    def test_phrase_and_one_shot_cues_are_ignored(self):
        cues = [
            _cue("Verse", 1, colors=("Red",), layer="phrase"),
            _cue("Chorus", 1, colors=("Red",), layer="one_shot"),
            _cue("Final Chorus", 1, colors=("Red",)),
        ]
        result = check_reserved_color_release(
            cues, reserved=("Red",), release_section="Final Chorus"
        )
        assert result.status == "pass"


# --- REQ-029 — 인접 구간 브리지: 공통색 최소 1개, 암전 전환은 예외 ---------


class TestAdjacentBridge:
    def test_adjacent_sections_sharing_a_color_pass(self):
        cues = [
            _cue("Intro", 1, colors=("Blue", "White")),
            _cue("Verse", 1, colors=("Blue",)),
        ]
        result = check_adjacent_bridge(cues)
        assert result.status == "pass"

    def test_adjacent_sections_with_no_shared_color_is_a_violation(self):
        cues = [
            _cue("Intro", 1, colors=("Blue",)),
            _cue("Verse", 1, colors=("Red",)),
        ]
        result = check_adjacent_bridge(cues)
        assert result.status == "fail"
        assert len(result.violations) == 1

    def test_disjoint_lit_groups_exempts_the_pair(self):
        cues = [
            _cue("Intro", 1, colors=("Blue",), lit_group_ids=frozenset({"A", "B"})),
            _cue("Verse", 1, colors=("Red",), lit_group_ids=frozenset({"C", "D"})),
        ]
        result = check_adjacent_bridge(cues)
        assert result.status == "pass"
        assert result.violations == ()

    def test_white_boundary_warm_white_and_cool_white_do_not_count_as_shared(self):
        cues = [
            _cue("Intro", 1, colors=("Warm White",)),
            _cue("Verse", 1, colors=("Cool White",)),
        ]
        result = check_adjacent_bridge(cues)
        assert result.status == "fail"


# --- REQ-030 — 후렴(Chorus) 전체 동일 주색, Final Chorus 클라이맥스 예외 --


class TestChorusIdentity:
    def test_same_primary_color_across_choruses_passes(self):
        cues = [
            _cue("Chorus", 1, colors=("Blue", "White")),
            _cue("Chorus", 2, colors=("Blue", "Red")),
            _cue("Chorus", 3, colors=("Blue",)),
        ]
        result = check_chorus_identity(cues)
        assert result.status == "pass"

    def test_differing_primary_colors_is_a_violation(self):
        cues = [
            _cue("Chorus", 1, colors=("Blue",)),
            _cue("Chorus", 2, colors=("Magenta",)),
        ]
        result = check_chorus_identity(cues)
        assert result.status == "fail"

    def test_final_chorus_is_excluded_from_the_identity_set(self):
        cues = [
            _cue("Chorus", 1, colors=("Blue",)),
            _cue("Chorus", 2, colors=("Blue",)),
            _cue("Final Chorus", 1, colors=("White",)),  # 클라이맥스 전환 — 예외
        ]
        result = check_chorus_identity(cues)
        assert result.status == "pass"

    def test_no_chorus_cues_is_not_evaluated(self):
        cues = [_cue("Verse", 1, colors=("Blue",))]
        result = check_chorus_identity(cues)
        assert result.status == "not_evaluated"

    def test_white_boundary_warm_and_cool_white_are_distinct_primaries(self):
        cues = [
            _cue("Chorus", 1, colors=("Warm White",)),
            _cue("Chorus", 2, colors=("Cool White",)),
        ]
        result = check_chorus_identity(cues)
        assert result.status == "fail"

    def test_ac016_six_chorus_occurrences_share_one_identity(self):
        """AC-LDDESIGN-016 — 오늘 `_arc_palette(("blue","white"), "chorus", k)`
        k=1..6 실측은 (blue,warm white)(blue,magenta) 를 교대 반복했다. M3
        컨셉 계층은 이 회전을 정체성 판정 경로에서 부르지 않으므로, 같은
        후렴 역할이 6회 반복돼도 주색은 항등이다."""
        cues = [_cue("Chorus", k, colors=("blue", "white")) for k in range(1, 7)]
        result = check_chorus_identity(cues)
        assert result.status == "pass"
        primaries = {c.colors[0].strip().casefold() for c in cues if c.section == "Chorus"}
        assert primaries == {"blue"}


# --- REQ-028 — 후렴 3회 이상이면 클라이맥스색 언더페인팅 최소 1회 ---------


class TestUnderpainting:
    def test_three_or_more_choruses_without_underpainting_fails(self):
        cues = [
            _cue("Verse", 1, colors=("Blue",)),
            _cue("Chorus", 1, colors=("Blue",)),
            _cue("Chorus", 2, colors=("Blue",)),
            _cue("Final Chorus", 1, colors=("Red",)),  # 클라이맥스 색 정식 등장
        ]
        result = check_underpainting(cues, climax_color="Red")
        assert result.status == "fail"

    def test_desaturated_climax_color_before_full_appearance_passes(self):
        cues = [
            _cue("Verse", 1, colors=("Red",), desaturated=True),  # 언더페인팅
            _cue("Chorus", 1, colors=("Blue",)),
            _cue("Chorus", 2, colors=("Blue",)),
            _cue("Final Chorus", 1, colors=("Red",)),
        ]
        result = check_underpainting(cues, climax_color="Red")
        assert result.status == "pass"

    def test_fewer_than_three_choruses_is_not_evaluated(self):
        cues = [
            _cue("Chorus", 1, colors=("Blue",)),
            _cue("Final Chorus", 1, colors=("Red",)),
        ]
        result = check_underpainting(cues, climax_color="Red")
        assert result.status == "not_evaluated"


# --- REQ-034 — 빈 제약은 관련 린트를 평가하지 않는다 ------------------------


class TestSkinToneConstraintGate:
    def test_absent_skin_tone_constraint_skips_the_lint(self):
        cues = [_cue("Chorus", 1, colors=("Green",))]
        result = check_skin_tone_clash(cues, constraints=Constraints())
        assert result.status == "not_evaluated"

    def test_present_skin_tone_constraint_evaluates_and_flags_clash(self):
        cues = [_cue("Chorus", 1, colors=("Green",))]
        result = check_skin_tone_clash(cues, constraints=Constraints(skin_tone="warm"))
        assert result.status == "fail"
        assert len(result.violations) == 1

    def test_present_skin_tone_constraint_with_no_clash_passes(self):
        cues = [_cue("Chorus", 1, colors=("Blue",))]
        result = check_skin_tone_clash(cues, constraints=Constraints(skin_tone="warm"))
        assert result.status == "pass"


# --- REQ-031 narrow reading — 신규 코드는 회전 로직을 참조하지 않는다 -----


class TestNoArcPaletteReference:
    """REQ-031 narrow reading(t436 배차 결정 1) — `server/concept/` 신규
    컬러 코드가 `_arc_palette`/`_per_chorus_palette` 를 import·호출하지
    않는다는 것을 소스 텍스트로 직접 확인한다(회귀 방지)."""

    def test_color_strip_and_color_lint_source_do_not_reference_arc_palette(self):
        concept_dir = Path(__file__).resolve().parent.parent / "concept"
        for name in ("color_strip.py", "color_lint.py"):
            text = (concept_dir / name).read_text(encoding="utf-8")
            assert "_arc_palette" not in text
            assert "_per_chorus_palette" not in text
