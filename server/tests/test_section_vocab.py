"""t362 — 브레이크다운 구간이 큐를 **하나도** 못 내던 자리.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` §2(구간 어휘 두 축) ·
§2.3(drop 은 정의상 측정 가능한 최대점) · §6 표(breakdown · bridge = 20~35%, 무빙 정지) ·
§12 항목 4(고칠 것: 어휘 추가).

**고치기 전에 실측한 것**(2026-09-12, main ``0c0237b``):

* ``matching.DYNAMICS_TERMS`` 에 ``breakdown`` 도 ``브레이크다운`` 도 없다(grep 0건).
* 6구간 EDM 입력에서 **Breakdown 과 Outro 두 장이 안 나갔다**
  (``reason=explicit_dynamics_required``). 엉뚱한 룩이 아니라 큐가 없었다.
* 그리고 **하이픈이 어휘를 뚫었다** — ``Pre-Chorus`` 와 ``Post-Chorus`` 가 둘 다
  ``(4, 5)`` 로, 즉 **후렴 대역**으로 읽혔다. ``-`` 가 ``matching._WORD`` 가 아니라
  ``chorus`` 의 앞 경계가 통과한다. 이쪽은 무음 결함이 아니라 **틀린 룩**이다.

이 파일이 지키는 것은 셋이다 — 어휘가 §2 를 덮는가, 최장 일치가 사는가, 그리고
**두 축이 아직 갈리지 않았다**는 측정이 공허하지 않은가.
"""

from __future__ import annotations

import pytest

from server.looks.loader import load_library_from_dir
from server.looks.matching import DYNAMICS_TERMS, resolve_dynamics
from server.looks.movement import MOVEMENT_STILL, band_for_dynamics
from server.looks.section_intent import brightness_fits, intent_for_label
from server.looks.section_vocab import (
    EDM_AXIS,
    GENRE_AXES,
    POP_AXIS,
    SECTION_TERMS,
    SIX_ROW_ONLY,
    SectionLabel,
    axis_disagreements,
    matched_section_terms,
    resolve_section_dynamics,
)
from server.looks.songcue import (
    EXPLICIT_DYNAMICS_REQUIRED,
    map_sections_to_looks,
    parse_sections,
)


class TestTheBreakdownSectionNowProducesACue:
    """카드가 고치라고 지목한 자리 — 큐가 **없던** 것이 생긴다."""

    def test_the_six_section_edm_song_now_stores_a_cue_for_every_section(self):
        """실측 입력 그대로. 고치기 전 Breakdown · Outro 가 ``look=None`` 이었다."""
        library = load_library_from_dir()
        sections = parse_sections(
            (
                ("Intro", "0:00"),
                ("Build-Up", "0:16"),
                ("Drop", "0:32"),
                ("Breakdown", "0:48"),
                ("Drop 2", "1:04"),
                ("Outro", "1:20"),
            )
        )

        selections = map_sections_to_looks(sections, library, "edm")

        assert [s.reason for s in selections] == [None] * 6
        assert all(s.look is not None for s in selections)
        breakdown = selections[3]
        assert breakdown.section.name == "Breakdown"
        assert breakdown.requested_dynamics == (1,)

    def test_the_breakdown_cue_is_dim_and_still_as_the_six_row_says(self):
        """§6 「breakdown · bridge」 행의 두 칸을 **둘 다** 잰다 — 20~35% 와 무빙 정지.

        밝기는 :func:`brightness_fits` 로, 정지는 ``movement.band_for_dynamics`` 로
        잰다. 둘은 서로 다른 계층이고, 한쪽만 재면 나머지가 조용히 어긋난다.
        """
        library = load_library_from_dir()
        intent = intent_for_label("Breakdown")
        assert intent is not None
        assert intent.row == "breakdown · bridge"
        assert intent.brightness == (20, 35)

        sections = parse_sections((("Breakdown", "0:00"),))
        for genre in sorted(GENRE_AXES):
            selection = map_sections_to_looks(sections, library, genre)[0]

            assert selection.look is not None, genre
            assert brightness_fits(intent, selection.look) is True, genre
            assert band_for_dynamics(selection.look.dynamics) == MOVEMENT_STILL, genre

    def test_every_genre_holds_at_least_one_candidate_in_the_breakdown_band(self):
        """비공허성 — (1,) 로 좁힌 것이 어느 장르도 **굶기지 않는다**.

        좁은 대역이 좋은 룩을 조용히 버리는 것은 ``matching`` 머리가 이름으로 거절하는
        실패 방향이다. 여기서 좁힌 근거는 §6 의 「무빙·이펙트 정지」이고, 그 좁힘이
        후보를 0으로 만들지 않는다는 것은 **재야** 아는 사실이다.
        """
        library = load_library_from_dir()
        for genre in sorted(GENRE_AXES):
            candidates = [
                look for look in library.looks if look.genre == genre and look.dynamics == 1
            ]
            assert len(candidates) >= 1, genre


class TestTheNegativeArm:
    """고친 것을 **되돌리면** 원래 결함이 돌아오는가. 안 쏜 가드는 잰 가드가 아니다."""

    def test_removing_the_new_vocabulary_returns_the_section_to_no_cue(self, monkeypatch):
        """날조 대조군 — 어휘에서 breakdown 계열만 빼면 그 구간이 다시 사라진다.

        빼는 것은 **이 카드가 더한 말**뿐이다. 나머지 구간이 그대로 큐를 내는 것까지
        함께 단언해야 「표를 통째로 비웠더니 다 죽었다」가 아니라 「이 말이 그 큐를
        살린다」가 된다.
        """
        library = load_library_from_dir()
        stripped = {
            term: band
            for term, band in SECTION_TERMS.items()
            if term not in {"breakdown", "브레이크다운"}
        }
        monkeypatch.setattr("server.looks.section_vocab.SECTION_TERMS", stripped)

        sections = parse_sections((("Intro", "0:00"), ("Breakdown", "0:16"), ("Drop", "0:32")))
        selections = map_sections_to_looks(sections, library, "edm")

        assert selections[1].reason == EXPLICIT_DYNAMICS_REQUIRED
        assert selections[1].look is None
        # 양옆은 살아 있다 — 죽은 것은 뺀 말 하나다.
        assert selections[0].look is not None
        assert selections[2].look is not None

    @pytest.mark.parametrize("name", ["Zzyzx", "Wobblegroove", "Solo", "Fadeout"])
    def test_a_name_the_standard_gives_no_band_never_guesses_one(self, name):
        """추측 금지 — 어휘 밖 이름도, 정본이 세기를 안 준 이름도 같은 사유로 끝난다.

        네 이름이 두 갈래를 함께 쏜다: ``Zzyzx``·``Wobblegroove`` 는 어휘에 **없고**,
        ``Solo``·``Fadeout`` 은 어휘에 **있는데 대역이 비었다**(§6 solo 행은 밝기 대신
        역할을 말하고, fadeout 은 §2 가 겹쳐 붙는 라벨이라고 명시한다).
        """
        library = load_library_from_dir()
        selection = map_sections_to_looks(parse_sections(((name, "0:00"),)), library, "rock")[0]

        assert selection.reason == EXPLICIT_DYNAMICS_REQUIRED
        assert selection.look is None
        assert selection.requested_dynamics == ()


class TestTheHyphenHoleIsClosed:
    """``-`` 가 단어 문자가 아니라서 뚫린 구멍 — 최장 일치가 막는다."""

    @pytest.mark.parametrize(
        ("label", "band", "row"),
        [
            ("Pre-Chorus", (3,), "pre-chorus · build"),
            ("Post-Chorus", (3, 4), "post-chorus"),
            ("Chorus", (4, 5), "chorus · drop"),
            ("Pre-Verse", (3,), "pre-chorus · build"),
            ("Verse", (2, 3), "verse"),
            ("Build-Up", (3,), "pre-chorus · build"),
        ],
    )
    def test_the_longer_label_wins_over_the_word_it_contains(self, label, band, row):
        assert resolve_section_dynamics(label) == band
        intent = intent_for_label(label)
        assert intent is not None and intent.row == row

    def test_the_old_union_predicate_still_reads_the_hyphen_labels_wrong(self):
        """비공허성 — 고치기 전 술어를 그대로 불러 **결함이 실재했음**을 보인다.

        ``matching.resolve_dynamics`` 는 운영자 질의용으로 그대로 살아 있고, 그 자리에서는
        합집합이 옳다. 여기서 부르는 것은 「구간 라벨에 쓰면 틀린다」를 재기 위해서다.
        """
        assert resolve_dynamics("Pre-Chorus") == (4, 5)
        assert resolve_dynamics("Post-Chorus") == (4, 5)

    def test_a_name_that_truly_carries_two_rows_stays_unconstrained(self):
        """부분 문자열이 **아닌** 두 말은 둘 다 살아남는다 — 기존 규율이 그대로다."""
        assert matched_section_terms("Build to Chorus") == {"build", "chorus"}
        assert intent_for_label("Build to Chorus") is None


class TestTheHangulBoundaryAndParticlesStillHold:
    """``matching`` 이 이름으로 거절하는 두 함정 — 한글 경계와 닫힌 조사 목록."""

    @pytest.mark.parametrize(
        "label", ["솔로이스트", "밤하늘", "블록", "백색", "간주곡", "전환기", "브릿지들"]
    )
    def test_a_term_is_not_found_inside_a_longer_hangul_word(self, label):
        """``솔로`` 가 ``솔로이스트`` 안에서 걸리면 솔로이스트 구간이 솔로가 된다.

        ``솔로이스트`` 는 조사 ``이`` 까지 시도해도 뒤에 ``스`` 가 남아 경계가 막는다 —
        이 카드가 ``솔로``·``간주``·``전환``·``브릿지`` 를 어휘에 넣으면서 새로 생긴
        함정이고, 기존 술어가 그대로 막는다는 것은 **재야** 아는 사실이다.
        """
        assert matched_section_terms(label) == frozenset()

    @pytest.mark.parametrize(
        ("label", "band"),
        [
            ("브레이크다운으로", (1,)),
            ("브릿지에서", (1,)),
            ("포스트코러스까지", (3, 4)),
            ("아웃트로는", (1, 2)),
            ("간주가", (3,)),
        ],
    )
    def test_a_closed_particle_may_follow_a_new_korean_term(self, label, band):
        """한국어는 교착어다 — ``브레이크다운으로`` 도 브레이크다운이다."""
        assert resolve_section_dynamics(label) == band


class TestTheTwoAxesAreDeclaredAndCompared:
    """정본 §2 [HARD] — 라벨 집합을 **두 벌** 들고, 갈리는지 기계로 확인한다."""

    def test_the_pop_axis_holds_every_label_the_standard_table_lists(self):
        """§2.1 표의 21행 그대로. 절 제목은 「20개」인데 표는 21행이다 — 표를 따른다."""
        assert set(POP_AXIS) == {
            "intro",
            "verse",
            "chorus",
            "bridge",
            "instrumental",
            "solo",
            "transition",
            "pre-chorus",
            "pre-verse",
            "interlude",
            "head",
            "main theme",
            "secondary theme",
            "exposition",
            "development",
            "recapitulation",
            "outro",
            "coda",
            "fadeout",
            "silence",
            "end",
        }

    def test_the_edm_axis_holds_the_seven_labels_the_standard_lists(self):
        assert set(EDM_AXIS) == {
            "intro",
            "build-up",
            "drop",
            "breakdown",
            "outro",
            "silence",
            "end",
        }

    def test_the_two_axes_agree_on_every_label_they_share(self):
        """오늘의 측정 — 교집합 넷, 불일치 0.

        이 빈 답이 「판정 함수 하나로 둬도 된다」의 근거다. 비지 않는 날 합친 표는
        한쪽을 깨뜨리고, 그때 장르를 배선해야 한다(``section_vocab`` 독스트링).
        """
        assert sorted(set(POP_AXIS) & set(EDM_AXIS)) == ["end", "intro", "outro", "silence"]
        assert axis_disagreements() == ()

    def test_the_agreement_check_can_actually_fail(self, monkeypatch):
        """날조 대조군 — 한 축을 어긋나게 만들면 검사가 그 라벨을 **답해야** 한다.

        두 축이 겹치는 라벨을 한 번만 적었다면 이 검사는 구조적으로 빈 답만 낼 수 있다.
        배정을 일부러 두 번 적는 이유가 이것이고, 그 이유가 실제로 작동하는지는
        **쏴야** 안다.
        """
        forged = dict(EDM_AXIS)
        forged["intro"] = SectionLabel(
            terms=("intro",), dynamics=(4, 5), row="chorus · drop", source="날조"
        )
        monkeypatch.setattr("server.looks.section_vocab.EDM_AXIS", forged)

        assert axis_disagreements() == ("intro",)

    def test_no_shipped_term_distinguishes_the_two_axes_today(self):
        """축을 고르는 스위치는 오늘 **두 갈래가 같다** — 그래서 장르를 안 배선했다.

        각 축이 단독으로 아는 라벨(pop 의 bridge, edm 의 drop)은 서로의 어휘에 없으므로
        합쳐도 충돌하지 않는다. 충돌은 **같은 말이 다른 뜻**일 때만 생기고, 그것이
        :func:`axis_disagreements` 가 재는 것이다.
        """
        pop_only = set(POP_AXIS) - set(EDM_AXIS)
        edm_only = set(EDM_AXIS) - set(POP_AXIS)

        assert "bridge" in pop_only
        assert {"drop", "breakdown", "build-up"} <= edm_only
        assert axis_disagreements() == ()

    def test_every_shipped_genre_maps_to_one_of_the_two_axes(self):
        library = load_library_from_dir()
        assert set(GENRE_AXES) == {look.genre for look in library.looks}
        assert set(GENRE_AXES.values()) == {"pop", "edm"}


class TestTheVocabularyStaysOneTable:
    """어휘를 복제하지 않았다 — 들여와 합치고, 갈라지면 시끄럽게 깨진다."""

    def test_the_merged_table_contains_every_operator_query_term_unchanged(self):
        for term, band in DYNAMICS_TERMS.items():
            assert SECTION_TERMS[term] == band, term

    def test_a_term_carrying_two_different_bands_breaks_at_import(self, monkeypatch):
        """날조 대조군 — 합치기 검사가 실제로 던지는지 쏜다."""
        from server.looks import section_vocab

        forged = dict(POP_AXIS)
        forged["chorus"] = SectionLabel(terms=("chorus",), dynamics=(1,), row=None, source="날조")
        monkeypatch.setattr(section_vocab, "POP_AXIS", forged)

        with pytest.raises(RuntimeError, match="two different dynamics bands"):
            section_vocab._merged_terms()

    def test_every_label_records_where_its_assignment_came_from(self):
        """배정에는 출처 문면이 붙는다 — 안 붙은 배정은 지어낸 배정과 구별되지 않는다."""
        for bucket in (POP_AXIS, EDM_AXIS, SIX_ROW_ONLY):
            for name, label in bucket.items():
                assert label.source.strip(), name
                assert label.terms, name

    def test_a_band_is_only_present_where_the_standard_gives_one(self):
        """빈 대역은 **정본이 안 준 것**이다 — 목록을 못으로 박아 조용한 확장을 막는다."""
        unbanded = {
            name
            for bucket in (POP_AXIS, EDM_AXIS, SIX_ROW_ONLY)
            for name, label in bucket.items()
            if not label.dynamics
        }
        assert unbanded == {
            "instrumental",
            "solo",
            "secondary theme",
            "exposition",
            "development",
            "recapitulation",
            "fadeout",
            "silence",
            "end",
        }
