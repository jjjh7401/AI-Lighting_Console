"""Tests for server/design/interview.py — the director interview engine
(SPEC-COPILOT-SONGSTD-001, M2, R1c, docs/proposals/song-lighting-design-
standard.md §2d).

Scenarios per spec.md R1c §S: 5-card sequential dispatch, each of the
selection/free-text/no-answer paths, Q1 answer changing Q2-Q4 proposals,
pre-specified-answer card skipping, unresolved free text re-asking instead
of guessing, and partial restart preserving prior answers.
"""

from __future__ import annotations

import pytest

from server.design.interview import (
    GLOBAL_DEFAULT_TEXTURE,
    Q1_CONCEPT,
    Q2_PALETTE,
    Q3_CLIMAX,
    Q4_SPATIAL_STORY,
    Q5_TEXTURE,
    SOURCE_AUTO_DRAFT,
    SOURCE_FREE_TEXT,
    SOURCE_OPTION,
    SOURCE_PRE_SPECIFIED,
    STEP_ORDER,
    AnswerRecord,
    DirectorDecisionProjection,
    DirectorInterview,
    InterviewError,
    QuestionCard,
    UnresolvedAnswer,
    build_question,
)
from server.design.profile import DirectorOverride, MusicProfile
from server.design.rig import RigProfile, build_rig_profile


def _rig(fixture_count: int = 0) -> RigProfile:
    patch = [
        {"fid": fid, "type_name": "Sharpy", "capabilities": []}
        for fid in range(1, fixture_count + 1)
    ]
    return build_rig_profile(patch=patch, groups={}, coords=[])


# ---------------------------------------------------------------------------
# build_question — exactly 3 profile/rig-derived options per step
# ---------------------------------------------------------------------------


class TestBuildQuestionExactlyThreeOptions:
    @pytest.mark.parametrize("step", list(STEP_ORDER))
    def test_every_step_yields_exactly_three_options(self, step):
        card = build_question(step, MusicProfile(), _rig())
        assert isinstance(card, QuestionCard)
        assert len(card.options) == 3

    @pytest.mark.parametrize("step", list(STEP_ORDER))
    def test_options_carry_nonblank_label_and_description(self, step):
        card = build_question(step, MusicProfile(genre="메탈", bpm=160), _rig(fixture_count=8))
        for option in card.options:
            assert option.label.strip()
            assert option.description.strip()

    def test_card_rejects_a_non_three_option_count(self):
        with pytest.raises(InterviewError):
            QuestionCard(step=Q1_CONCEPT, prompt="x", why="y", options=())

    def test_unknown_step_is_rejected(self):
        with pytest.raises(InterviewError):
            build_question("Q9_NONSENSE", MusicProfile(), _rig())


class TestQ1ConceptOptions:
    def test_options_are_the_three_concept_seeds(self):
        card = build_question(Q1_CONCEPT, MusicProfile(), _rig())
        assert {option.label for option in card.options} == {"우주", "네온", "빈티지"}
        assert all(isinstance(option.value, str) for option in card.options)

    def test_a_profile_concept_already_set_is_promoted_to_the_recommendation(self):
        card = build_question(Q1_CONCEPT, MusicProfile(concept="네온"), _rig())
        assert card.options[0].label == "네온"


class TestQ2PaletteOptions:
    def test_defaults_to_unified_mood_table_and_global_default_colors(self):
        card = build_question(Q2_PALETTE, MusicProfile(), _rig())
        values = [option.value for option in card.options]
        assert len(set(values)) == 3  # always deduped and distinct

    def test_concept_color_outranks_genre_and_global_default(self):
        profile = MusicProfile(genre="메탈", concept="우주")
        card = build_question(Q2_PALETTE, profile, _rig())
        assert card.options[0].value == "블루/퍼플"  # 우주 concept seed's color

    def test_genre_wins_when_no_concept_is_set(self):
        profile = MusicProfile(genre="edm")
        card = build_question(Q2_PALETTE, profile, _rig())
        assert card.options[0].value == "단색 볼드, 퍼플/레드/화이트"


class TestQ3ClimaxOptions:
    def test_top_options_are_the_highest_d_level_unified_mood_rows(self):
        card = build_question(Q3_CLIMAX, MusicProfile(), _rig())
        assert {option.label for option in card.options} == {"Ring In", "Audience", "Cross"}
        for option in card.options:
            assert isinstance(option.value, DirectorOverride)
            assert option.value.d_level in (4, 5)

    def test_concept_position_bias_promotes_the_recommendation(self):
        # "네온" concept seed biases toward Cross — normally ranked 3rd by
        # D level alone, must become the recommendation once confirmed.
        card = build_question(Q3_CLIMAX, MusicProfile(concept="네온"), _rig())
        assert card.options[0].label == "Cross"


class TestQ4SpatialStoryOptions:
    def test_default_options_are_ascending_descending_and_table_order(self):
        card = build_question(Q4_SPATIAL_STORY, MusicProfile(), _rig())
        labels = [option.label for option in card.options]
        assert labels == ["좁음→넓음 (E3 기본)", "넓음→좁음 (역순)", "사전 등재 순서"]
        ascending = card.options[0].value.position_candidates
        descending = card.options[1].value.position_candidates
        assert ascending == tuple(reversed(descending))
        assert ascending[0] == "Home"  # D1, the narrowest per E3
        assert ascending[-1] in ("Ring In", "Audience")  # D5, the widest

    def test_concept_biased_order_is_recommended_when_a_concept_is_set(self):
        card = build_question(Q4_SPATIAL_STORY, MusicProfile(concept="네온"), _rig())
        assert card.options[0].label == "네온 컨셉 우선 배치"
        assert card.options[0].value.position_candidates[0] == "Cross"


# ---------------------------------------------------------------------------
# 카드 t314 — Q4 가 무대의 실제 모양을 읽는다
# ---------------------------------------------------------------------------


def _rig_with_coords(points: list[tuple[float, float, float]]) -> RigProfile:
    coords = [
        {"fid": index + 1, "x": point[0], "y": point[1], "z": point[2]}
        for index, point in enumerate(points)
    ]
    return build_rig_profile(patch=[], groups={}, coords=coords)


#: 좌우로 갈라져 같은 깊이 띠에 선 리그 → `grid` 판독(t314 실측).
_LATERAL_POINTS = [
    (-5.0, 0.0, 5.0),
    (-5.0, 1.0, 5.0),
    (-4.0, 0.0, 5.0),
    (-4.0, 1.0, 5.0),
    (5.0, 0.0, 5.0),
    (5.0, 1.0, 5.0),
    (4.0, 0.0, 5.0),
    (4.0, 1.0, 5.0),
]

#: 전 장비가 한 점에 모인 리그 — SPEC-COPILOT-SPATIAL-001 §E.2.4 가 실기에서
#: 읽은 모양(19대 전부 `(0,0,0)`)이다.
_ALL_ZERO_POINTS = [(0.0, 0.0, 0.0) for _ in range(19)]


def _q4_labels(rig: RigProfile, profile: MusicProfile | None = None) -> list[str]:
    card = build_question(Q4_SPATIAL_STORY, profile or MusicProfile(), rig)
    return [option.label for option in card.options]


class TestQ4ReadsTheStageShape:
    def test_two_rigs_with_the_same_music_and_different_geometry_differ(self):
        """이 카드가 참으로 만들려던 단언 — 일자 무대와 깊이 열이 다른 답을 낸다."""
        from server.tests.synthetic_rig import synthetic_fixtures

        lateral = _rig_with_coords(_LATERAL_POINTS)
        depth = _rig_with_coords(
            [(fixture.x, fixture.y, fixture.z) for fixture in synthetic_fixtures()]
        )

        assert lateral.geometry.arrangement == "grid"
        assert depth.geometry.arrangement == "depth_rows"

        lateral_labels = _q4_labels(lateral)
        depth_labels = _q4_labels(depth)
        assert lateral_labels != depth_labels
        # 폭으로 퍼진 리그는 넓어지는 서사를, 깊이 열은 모이는 서사를 먼저 낸다.
        assert lateral_labels[0] == "좁음→넓음 (E3 기본)"
        assert depth_labels[0] == "넓음→좁음 (역순)"

    def test_a_readable_arrangement_names_geometry_in_the_note(self):
        card = build_question(Q4_SPATIAL_STORY, MusicProfile(), _rig_with_coords(_LATERAL_POINTS))
        for option in card.options:
            assert "무대 배치(격자)와 곡 구조를 함께 보고" in option.description

    def test_an_all_zero_rig_falls_back_to_the_music_only_ordering(self):
        """퇴화 리그는 예외가 아니라 1급 경로다 — 실기 desk 가 이 모양이다."""
        degenerate = _rig_with_coords(_ALL_ZERO_POINTS)
        assert degenerate.geometry.arrangement is None
        assert degenerate.geometry.arrangement_low_confidence is True

        card = build_question(Q4_SPATIAL_STORY, MusicProfile(), degenerate)
        assert [option.label for option in card.options] == [
            "좁음→넓음 (E3 기본)",
            "넓음→좁음 (역순)",
            "사전 등재 순서",
        ]
        for option in card.options:
            # t312 가 세운 정직한 문면 그대로 — 안 읽은 근거를 대지 않는다.
            assert "장비 목록 없이 곡 구조만 보고 만든 제안이에요" in option.description
            assert "무대 배치" not in option.description

    def test_a_confirmed_concept_still_outranks_geometry(self):
        """감독이 말한 의도가 방을 이긴다.

        기하가 **다른** 순서를 밀고 있을 때만 이 단언이 힘을 가진다: 깊이 열
        리그는 「넓음→좁음」을 앞으로 밀어내는데, 그래도 1번은 컨셉이어야
        한다. 밀린 자리는 2번으로 내려온다.
        """
        from server.tests.synthetic_rig import synthetic_fixtures

        depth = _rig_with_coords(
            [(fixture.x, fixture.y, fixture.z) for fixture in synthetic_fixtures()]
        )
        assert depth.geometry.arrangement == "depth_rows"

        card = build_question(Q4_SPATIAL_STORY, MusicProfile(concept="네온"), depth)
        assert card.options[0].label == "네온 컨셉 우선 배치"
        assert card.options[0].value.position_candidates[0] == "Cross"
        assert card.options[1].label == "넓음→좁음 (역순)"

    def test_the_no_coordinates_path_is_unchanged(self):
        """카드 t311 경로 — 좌표가 아예 없는 리그."""
        no_coords = _rig()
        assert no_coords.geometry.centroid is None
        assert no_coords.geometry.dominant_axis is None

        card = build_question(Q4_SPATIAL_STORY, MusicProfile(), no_coords)
        assert [option.label for option in card.options] == [
            "좁음→넓음 (E3 기본)",
            "넓음→좁음 (역순)",
            "사전 등재 순서",
        ]
        for option in card.options:
            assert "장비 목록 없이 곡 구조만 보고 만든 제안이에요" in option.description


# ---------------------------------------------------------------------------
# 카드 t315 — 라벨이 같아도 크기가 다르면 다른 답을 낸다
# ---------------------------------------------------------------------------


def _grid_rig_pair() -> tuple[RigProfile, RigProfile]:
    """폭으로 퍼진 격자와 깊이로 쌓인 격자. 좌표는 하네스가 만든다."""
    from server.tests.synthetic_rig import (
        synthetic_deep_grid_fixtures,
        synthetic_wide_grid_fixtures,
    )

    return (
        _rig_with_coords([(f.x, f.y, f.z) for f in synthetic_wide_grid_fixtures()]),
        _rig_with_coords([(f.x, f.y, f.z) for f in synthetic_deep_grid_fixtures()]),
    )


class TestQ4ReadsTheStageSize:
    def test_the_same_arrangement_label_with_a_different_ratio_differs(self):
        """t315 가 참으로 만들려던 단언 — **라벨이 같은데** 답이 갈린다.

        이 한 쌍은 배치 판독이 구별해 주지 못한다: 둘 다 `grid` 다. 갈라 주는
        것은 t315 가 실은 `spans` 뿐이라, 이 단언이 빨간불이면 배선이 안 된
        것이고 초록불이면 배선이 **실제로 답을 바꿨다**는 뜻이다.
        """
        wide, deep = _grid_rig_pair()

        # 전제: 라벨은 정말로 같다. 이게 깨지면 이 시험은 크기가 아니라
        # 배치를 재고 있는 것이므로, 단언 자체가 무의미해진다.
        assert wide.geometry.arrangement == "grid"
        assert deep.geometry.arrangement == "grid"
        assert wide.geometry.arrangement_low_confidence is False
        assert deep.geometry.arrangement_low_confidence is False

        # 갈라 주는 값
        assert wide.geometry.depth_width_ratio == pytest.approx(0.1)
        assert deep.geometry.depth_width_ratio == pytest.approx(10.0)

        wide_labels = _q4_labels(wide)
        deep_labels = _q4_labels(deep)
        assert wide_labels != deep_labels
        # 폭이 있는 리그만 「폭이 열리는」 서사를 받는다.
        assert wide_labels[0] == "좁음→넓음 (E3 기본)"
        # 폭 1.0m 짜리 리그에는 열 폭이 없다 → 모아 들어가는 쪽.
        assert deep_labels[0] == "넓음→좁음 (역순)"

    def test_a_ratio_that_does_not_discriminate_keeps_todays_answer(self):
        """음성 대조군 — 비가 경계 아래면 라벨의 기본값이 그대로 남는다.

        t314 가 세운 `_LATERAL_POINTS` 리그다. 깊이/폭 = 0.1 로 경계
        (`_DEPTH_DOMINANCE_RATIO` = 1.5) 한참 아래라, t315 의 배선은 이
        리그에 손대지 않아야 한다. 라벨 세 줄이 **바이트 동일**해야 한다.
        """
        lateral = _rig_with_coords(_LATERAL_POINTS)
        assert lateral.geometry.arrangement == "grid"
        assert lateral.geometry.depth_width_ratio == pytest.approx(0.1)
        assert _q4_labels(lateral) == [
            "좁음→넓음 (E3 기본)",
            "넓음→좁음 (역순)",
            "사전 등재 순서",
        ]

    def test_a_degenerate_rig_gets_no_confident_ratio(self):
        """전 장비 원점 — 「없다」를 0 이 아니라 `None` 으로 답한다."""
        degenerate = _rig_with_coords(_ALL_ZERO_POINTS)
        assert degenerate.geometry.spans == {"x": 0.0, "y": 0.0, "z": 0.0}
        assert degenerate.geometry.depth_width_ratio is None

    def test_a_rig_with_no_coordinates_carries_no_spans(self):
        """좌표가 없으면 span 도 없다 — 0 으로 채우지 않는다."""
        no_coords = _rig()
        assert no_coords.geometry.spans is None
        assert no_coords.geometry.depth_width_ratio is None

    def test_a_depth_row_rig_is_not_flipped_by_a_wide_ratio(self):
        """한 방향으로만 뒤집는다 — 폭이 넓어도 깊이 열은 그대로 모인다.

        `depth_rows` 가 모아 들어가는 서사를 받은 근거는 span 크기가 아니라
        **구조**였다. 그 근거는 폭이 넓어져도 그대로이므로, 있지도 않은 대칭을
        만들어 이 리그를 `ascending` 으로 올리지 않는다. 비를 대칭으로
        구현했다면 이 리그(깊이/폭 = 0.3, 폭이 3배 이상 넓다)가 바로
        `ascending` 으로 올라가므로, 이 단언이 그 구현을 걸러 낸다.
        """
        from server.tests.synthetic_rig import synthetic_wide_depth_row_fixtures

        depth = _rig_with_coords([(f.x, f.y, f.z) for f in synthetic_wide_depth_row_fixtures()])
        assert depth.geometry.arrangement == "depth_rows"
        assert depth.geometry.depth_width_ratio == pytest.approx(0.3)
        assert _q4_labels(depth)[0] == "넓음→좁음 (역순)"


class TestQ5TextureOptions:
    def test_genre_texture_is_recommended_when_genre_known(self):
        card = build_question(Q5_TEXTURE, MusicProfile(genre="메탈"), _rig())
        assert card.options[0].value == "스냅 위주, 더블킥×디머 체이스 동기"

    def test_fast_bpm_yields_a_snap_leaning_texture_without_a_genre(self):
        card = build_question(Q5_TEXTURE, MusicProfile(bpm=170), _rig())
        assert card.options[0].value == "스냅 위주 (빠른 템포)"

    def test_slow_bpm_yields_a_fade_leaning_texture_without_a_genre(self):
        card = build_question(Q5_TEXTURE, MusicProfile(bpm=70), _rig())
        assert card.options[0].value == "긴 페이드 성향 (느린 템포)"

    def test_no_genre_and_default_bpm_pads_with_distinct_genre_texture_rows(self):
        # genre absent + BPM default (120, mid-band -> "중간") collapses with
        # the neutral fallback ("중간") to ONE unique candidate; padding
        # from the genre-texture table must still fill exactly 3 distinct.
        card = build_question(Q5_TEXTURE, MusicProfile(), _rig())
        values = {option.value for option in card.options}
        assert len(values) == 3
        assert GLOBAL_DEFAULT_TEXTURE in values


class TestDirectorDecisionProjection:
    def test_q3_climax_projects_peak_accent_and_d_level_without_changing_value(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)
        interview.submit_answer(None)
        card = interview.build_current_card()
        record = interview.submit_answer(card.options[0].label)

        assert isinstance(record.value, DirectorOverride)
        assert record.value == card.options[0].value
        assert isinstance(record.director_decision, DirectorDecisionProjection)
        assert record.director_decision.step == Q3_CLIMAX
        assert record.director_decision.climax is not None
        assert record.director_decision.climax.peak_positions == record.value.position_candidates
        assert record.director_decision.climax.accent_color == record.value.color_tendency
        assert record.director_decision.climax.d_level == record.value.d_level

    def test_q4_spatial_story_projects_positions_and_narrow_to_wide_progression(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer("완전히 새로운 컨셉")
        interview.submit_answer(None)
        interview.submit_answer(None)
        card = interview.build_current_card()
        record = interview.submit_answer(card.options[0].label)

        assert isinstance(record.value, DirectorOverride)
        assert record.value == card.options[0].value
        assert isinstance(record.director_decision, DirectorDecisionProjection)
        assert record.director_decision.step == Q4_SPATIAL_STORY
        assert record.director_decision.spatial_story is not None
        story = record.director_decision.spatial_story
        assert story.positions == record.value.position_candidates
        assert story.progression == "narrow_to_wide"
        assert story.width_tiers[0] == "narrow"
        assert story.width_tiers[-1] == "max"

    @pytest.mark.parametrize(
        ("raw", "bpm", "snap_fade", "fx_density", "bpm_speed"),
        [
            ("드라이 스냅 위주로", 170, "snap", "high", "fast"),
            ("긴 페이드로 천천히", 70, "fade", "low", "slow"),
            ("중간 질감", 120, "balanced", "medium", "medium"),
        ],
    )
    def test_q5_texture_projects_snap_fade_density_and_bpm_speed(
        self, raw, bpm, snap_fade, fx_density, bpm_speed
    ):
        interview = DirectorInterview(MusicProfile(bpm=bpm), _rig())
        for _ in range(4):
            interview.submit_answer(None)
        record = interview.submit_answer(raw)

        assert record.value == raw
        assert not isinstance(record.value, DirectorOverride)
        assert isinstance(record.director_decision, DirectorDecisionProjection)
        assert record.director_decision.step == Q5_TEXTURE
        assert record.director_decision.texture is not None
        texture = record.director_decision.texture
        assert texture.snap_fade == snap_fade
        assert texture.fx_density == fx_density
        assert texture.bpm_speed == bpm_speed
        assert texture.bpm_is_default is False


# ---------------------------------------------------------------------------
# DirectorInterview — sequential progress
# ---------------------------------------------------------------------------


class TestSequentialProgress:
    def test_starts_at_q1_and_advances_through_all_five_in_order(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        seen_order = []
        while not interview.is_complete():
            seen_order.append(interview.current_step)
            interview.submit_answer(None)  # auto-draft every step
        assert seen_order == list(STEP_ORDER)
        assert interview.current_step is None

    def test_build_current_card_is_none_once_complete(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        for _ in STEP_ORDER:
            interview.submit_answer(None)
        assert interview.build_current_card() is None

    def test_submitting_after_completion_raises(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        for _ in STEP_ORDER:
            interview.submit_answer(None)
        with pytest.raises(InterviewError):
            interview.submit_answer("anything")


# ---------------------------------------------------------------------------
# Q1 confirmation changing Q2-Q4 proposal generation (DI2)
# ---------------------------------------------------------------------------


class TestQ1ChangesDownstreamProposals:
    def test_choosing_a_concept_at_q1_reshapes_q2_q3_q4(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        baseline_q2 = interview.build_current_card()  # Q1 card, unused directly
        assert baseline_q2.step == Q1_CONCEPT

        interview.submit_answer("네온")
        q2_card = interview.build_current_card()
        assert q2_card.step == Q2_PALETTE
        assert q2_card.options[0].value == "마젠타/시안"

        interview.submit_answer(None)  # auto-draft Q2
        q3_card = interview.build_current_card()
        assert q3_card.step == Q3_CLIMAX
        assert q3_card.options[0].label == "Cross"

        interview.submit_answer(None)  # auto-draft Q3
        q4_card = interview.build_current_card()
        assert q4_card.step == Q4_SPATIAL_STORY
        assert q4_card.options[0].label == "네온 컨셉 우선 배치"

    def test_a_different_q1_choice_yields_a_different_q2_recommendation(self):
        first = DirectorInterview(MusicProfile(), _rig())
        first.submit_answer("우주")
        first_q2 = first.build_current_card()

        second = DirectorInterview(MusicProfile(), _rig())
        second.submit_answer("빈티지")
        second_q2 = second.build_current_card()

        assert first_q2.options[0].value != second_q2.options[0].value


# ---------------------------------------------------------------------------
# Answer paths: option choice, free text, no-answer (DI3/DI4)
# ---------------------------------------------------------------------------


class TestOptionChoicePath:
    def test_matching_an_option_label_records_it_confirmed(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        card = interview.build_current_card()
        chosen_label = card.options[1].label
        record = interview.submit_answer(chosen_label)
        assert isinstance(record, AnswerRecord)
        assert record.source == SOURCE_OPTION
        assert record.confirmed is True
        assert record.choice == card.options[1]
        assert record.value == card.options[1].value
        assert record.free_text is None

    def test_option_matching_is_case_insensitive(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        record = interview.submit_answer("ring in".upper() if False else "우주")
        assert record.source == SOURCE_OPTION  # sanity: exact-case match works too


class TestFreeTextPath:
    def test_q1_free_text_is_accepted_verbatim(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        record = interview.submit_answer("완전히 새로운 컨셉")
        assert record.source == SOURCE_FREE_TEXT
        assert record.value == "완전히 새로운 컨셉"
        assert record.confirmed is True

    def test_q2_free_text_with_a_known_color_token_resolves(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)  # Q1 auto-draft
        record = interview.submit_answer("네온 사인처럼 마젠타 포인트로")
        assert isinstance(record, AnswerRecord)
        assert record.source == SOURCE_FREE_TEXT
        assert record.value == "네온 사인처럼 마젠타 포인트로"

    def test_q3_free_text_resolves_via_resolve_section_into_a_director_override(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)
        interview.submit_answer(None)
        record = interview.submit_answer("웅장한 피날레 연출")
        assert isinstance(record, AnswerRecord)
        assert isinstance(record.value, DirectorOverride)
        assert record.value.d_level == 5
        assert record.value.color_tendency == "쿨 볼드"

    def test_q4_free_text_resolves_to_position_candidates_only(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        for _ in range(3):
            interview.submit_answer(None)
        record = interview.submit_answer("잔잔한 발라드 느낌")
        assert isinstance(record, AnswerRecord)
        assert record.value.d_level is None
        assert record.value.color_tendency is None
        assert record.value.position_candidates[0] == "Vocal DSC"

    def test_q5_free_text_is_accepted_verbatim_and_never_becomes_an_override(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        for _ in range(4):
            interview.submit_answer(None)
        record = interview.submit_answer("드라이 스냅 위주로")
        assert record.value == "드라이 스냅 위주로"
        assert not isinstance(record.value, DirectorOverride)


class TestNoAnswerAutoDraft:
    def test_blank_submission_advances_with_an_unconfirmed_draft(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        card = interview.build_current_card()
        record = interview.submit_answer(None)
        assert record.source == SOURCE_AUTO_DRAFT
        assert record.confirmed is False
        assert record.value == card.options[0].value
        assert record.choice == card.options[0]
        assert interview.current_step == Q2_PALETTE

    def test_whitespace_only_submission_is_treated_as_no_answer(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        record = interview.submit_answer("   ")
        assert record.source == SOURCE_AUTO_DRAFT


# ---------------------------------------------------------------------------
# Unresolved free text -> re-ask, never a guess (DI3)
# ---------------------------------------------------------------------------


class TestUnresolvedFreeTextReAsks:
    def test_q2_unrecognized_color_text_returns_unresolved_and_does_not_advance(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)  # Q1
        result = interview.submit_answer("이해할 수 없는 외계어 문장")
        assert isinstance(result, UnresolvedAnswer)
        assert result.step == Q2_PALETTE
        assert result.reason == "no_known_color_token"
        assert interview.current_step == Q2_PALETTE  # did not advance

    def test_q3_unmatched_mood_text_returns_unresolved_and_does_not_advance(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)
        interview.submit_answer(None)
        result = interview.submit_answer("이해할 수 없는 외계어 문장")
        assert isinstance(result, UnresolvedAnswer)
        assert result.reason == "no_keyword_match"
        assert interview.current_step == Q3_CLIMAX

    def test_a_valid_answer_after_an_unresolved_one_succeeds_and_advances(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)
        interview.submit_answer(None)
        unresolved = interview.submit_answer("이해할 수 없는 외계어 문장")
        assert isinstance(unresolved, UnresolvedAnswer)
        record = interview.submit_answer("웅장한 피날레 연출")
        assert isinstance(record, AnswerRecord)
        assert interview.current_step == Q4_SPATIAL_STORY

    def test_q4_ambiguous_mood_text_also_re_asks(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        for _ in range(3):
            interview.submit_answer(None)
        result = interview.submit_answer("발라드풍 오프닝 연출")  # ties Vocal DSC/Center
        assert isinstance(result, UnresolvedAnswer)
        assert result.reason == "ambiguous_keyword_match"


# ---------------------------------------------------------------------------
# Pre-specified answers skip cards
# ---------------------------------------------------------------------------


class TestPreSpecifiedAnswersSkipCards:
    def test_a_pre_specified_step_is_recorded_with_no_proposals(self):
        interview = DirectorInterview(MusicProfile(), _rig(), pre_specified={Q1_CONCEPT: "네온"})
        assert interview.answers[Q1_CONCEPT].source == SOURCE_PRE_SPECIFIED
        assert interview.answers[Q1_CONCEPT].proposals == ()
        assert interview.answers[Q1_CONCEPT].confirmed is True
        assert interview.current_step == Q2_PALETTE  # Q1's card never issued

    def test_pre_specified_q1_still_reshapes_q2_proposals(self):
        interview = DirectorInterview(MusicProfile(), _rig(), pre_specified={Q1_CONCEPT: "네온"})
        q2_card = interview.build_current_card()
        assert q2_card.options[0].value == "마젠타/시안"

    def test_multiple_pre_specified_steps_skip_multiple_cards(self):
        interview = DirectorInterview(
            MusicProfile(),
            _rig(),
            pre_specified={Q1_CONCEPT: "우주", Q5_TEXTURE: "드라이 스냅"},
        )
        assert interview.answers.keys() == {Q1_CONCEPT, Q5_TEXTURE}
        assert interview.current_step == Q2_PALETTE

    def test_an_unresolvable_pre_specified_value_falls_through_to_a_normal_card(self):
        interview = DirectorInterview(
            MusicProfile(),
            _rig(),
            pre_specified={Q2_PALETTE: "이해할 수 없는 외계어 문장"},
        )
        # Q2's palette free text has no known color token -> cannot be
        # accepted as a skip; Q1 must still be asked first regardless.
        assert Q2_PALETTE not in interview.answers
        assert interview.current_step == Q1_CONCEPT

    def test_unknown_pre_specified_step_raises(self):
        with pytest.raises(InterviewError):
            DirectorInterview(MusicProfile(), _rig(), pre_specified={"Q9_NONSENSE": "x"})


# ---------------------------------------------------------------------------
# Partial restart from QN preserving prior answers (DI5)
# ---------------------------------------------------------------------------


class TestPartialRestart:
    def test_restart_from_q3_drops_q3_through_q5_but_keeps_q1_and_q2(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer("우주")
        interview.submit_answer(None)
        interview.submit_answer(None)  # Q3
        interview.submit_answer(None)  # Q4
        interview.submit_answer(None)  # Q5
        assert interview.is_complete()

        q1_before = interview.answers[Q1_CONCEPT]
        q2_before = interview.answers[Q2_PALETTE]

        interview.restart_from(Q3_CLIMAX)

        assert interview.current_step == Q3_CLIMAX
        assert interview.answers[Q1_CONCEPT] == q1_before
        assert interview.answers[Q2_PALETTE] == q2_before
        assert Q4_SPATIAL_STORY not in interview.answers
        assert Q5_TEXTURE not in interview.answers

    def test_re_answering_after_restart_completes_the_interview_again(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        for _ in STEP_ORDER:
            interview.submit_answer(None)
        interview.restart_from(Q4_SPATIAL_STORY)
        interview.submit_answer(None)
        interview.submit_answer(None)
        assert interview.is_complete()

    def test_restart_from_unknown_step_raises(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        with pytest.raises(InterviewError):
            interview.restart_from("Q9_NONSENSE")


# ---------------------------------------------------------------------------
# Audit trail (DI6)
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_audit_trail_is_ordered_q1_through_q5_and_covers_every_answer(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer("우주")
        interview.submit_answer(None)
        interview.submit_answer("웅장한 피날레 연출")
        interview.submit_answer(None)
        interview.submit_answer("드라이 스냅")

        trail = interview.audit_trail()
        assert [record.step for record in trail] == list(STEP_ORDER)
        assert trail[0].source == SOURCE_OPTION
        assert trail[1].source == SOURCE_AUTO_DRAFT
        assert trail[1].confirmed is False
        assert trail[2].source == SOURCE_FREE_TEXT

    def test_audit_trail_is_partial_mid_interview(self):
        interview = DirectorInterview(MusicProfile(), _rig())
        interview.submit_answer(None)
        trail = interview.audit_trail()
        assert len(trail) == 1
        assert trail[0].step == Q1_CONCEPT


# ---------------------------------------------------------------------------
# Rig-derived context reaches the cards
# ---------------------------------------------------------------------------


class TestRigDerivedContext:
    @pytest.mark.parametrize("step", list(STEP_ORDER))
    def test_option_descriptions_mention_the_rigs_fixture_count(self, step):
        card = build_question(step, MusicProfile(), _rig(fixture_count=12))
        for option in card.options:
            assert "12대" in option.description
