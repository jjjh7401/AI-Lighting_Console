"""후렴 회차 확장 판정 시험 — SPEC-LDDESIGN-001 M4 (REQ-LDDESIGN-042~049,
카드 t437).

:class:`~server.concept.escalation.ChorusSnapshot` 을 손으로 조립해
각 축·게이트를 정확한 값으로 시험한다 — density.py 를 거치지 않고도
escalation.py 단독으로 검증 가능함을 보장한다(모듈 경계 분리).
정수·실기 곡 데이터를 통한 통합 시험은 ``test_concept_density.py`` 의
``TestChorusPhraseCap`` 을 참고.
"""

from __future__ import annotations

from server.concept.density import (
    GROUP_ROSTER,
    SectionOccurrence,
    compile_density,
)
from server.concept.escalation import (
    AXES,
    ChorusSnapshot,
    build_chorus_snapshots,
    check_pairs,
    g2_identity,
    g3_new_axis_within_five,
    g4_final_new_axis_and_headroom,
    g49_stagnation_is_normal,
    new_axes,
)
from server.concept.resolver import resolve_sequence


def _snap(
    *,
    section: str = "Chorus",
    occurrence: int = 1,
    round_number: int,
    color: str | None = "노랑",
    groups_on: int = 5,
    area: float = 0.5,
    brightness: int = 75,
    motion: int = 1,
    position: str = "back",
    phrase_density: int = 1,
) -> ChorusSnapshot:
    return ChorusSnapshot(
        section=section,
        occurrence=occurrence,
        round_number=round_number,
        color=color,
        groups_on=groups_on,
        area=area,
        brightness=brightness,
        motion=motion,
        position=position,
        phrase_density=phrase_density,
    )


class TestNewAxes:
    """REQ-043 — 여섯 축(기구군 수·면적·밝기·모션·방향·밀도) 각각을
    독립적으로 판정한다."""

    def test_no_change_yields_empty_axes(self) -> None:
        prev = _snap(round_number=1)
        curr = _snap(round_number=2)
        assert new_axes(prev, curr) == frozenset()

    def test_groups_axis(self) -> None:
        prev = _snap(round_number=1, groups_on=5)
        curr = _snap(round_number=2, groups_on=6)
        assert new_axes(prev, curr) == frozenset({"groups"})

    def test_area_axis(self) -> None:
        prev = _snap(round_number=1, area=0.4)
        curr = _snap(round_number=2, area=0.5)
        assert new_axes(prev, curr) == frozenset({"area"})

    def test_brightness_axis(self) -> None:
        prev = _snap(round_number=1, brightness=75)
        curr = _snap(round_number=2, brightness=80)
        assert new_axes(prev, curr) == frozenset({"brightness"})

    def test_motion_axis(self) -> None:
        prev = _snap(round_number=1, motion=1)
        curr = _snap(round_number=2, motion=2)
        assert new_axes(prev, curr) == frozenset({"motion"})

    def test_direction_axis_fires_on_any_change_not_only_increase(self) -> None:
        prev = _snap(round_number=1, position="back")
        curr = _snap(round_number=2, position="side")
        assert new_axes(prev, curr) == frozenset({"direction"})

    def test_density_axis(self) -> None:
        prev = _snap(round_number=1, phrase_density=1)
        curr = _snap(round_number=2, phrase_density=2)
        assert new_axes(prev, curr) == frozenset({"density"})

    def test_decrease_is_not_a_new_axis(self) -> None:
        prev = _snap(round_number=1, brightness=90, groups_on=8)
        curr = _snap(round_number=2, brightness=80, groups_on=6)
        assert new_axes(prev, curr) == frozenset()

    def test_all_six_axes_cover_the_req_043_set(self) -> None:
        assert frozenset(AXES) == frozenset(
            {"groups", "area", "brightness", "motion", "direction", "density"}
        )


class TestCheckPairsIdentity:
    """REQ-042 — 정체성(주색 동일 **또는** Final Chorus)."""

    def test_same_color_non_final_is_identity_maintained(self) -> None:
        snapshots = [_snap(round_number=1, color="노랑"), _snap(round_number=2, color="노랑")]
        pairs = check_pairs(snapshots)
        assert pairs[0].identity_maintained is True

    def test_different_color_non_final_violates_identity(self) -> None:
        snapshots = [_snap(round_number=1, color="노랑"), _snap(round_number=2, color="파랑")]
        pairs = check_pairs(snapshots)
        assert pairs[0].identity_maintained is False

    def test_final_chorus_always_counts_as_identity_maintained(self) -> None:
        pairs = check_pairs(
            [
                _snap(round_number=1, color="노랑"),
                _snap(section="Final Chorus", occurrence=1, round_number=2, color="흰색"),
            ]
        )
        # 클라이맥스 색 전환(흰색)이 있어도 Final Chorus 는 REQ-042 예외로
        # 항상 유지 판정이다.
        assert pairs[0].identity_maintained is True

    def test_label_carries_section_and_round(self) -> None:
        pairs = check_pairs([_snap(round_number=1), _snap(round_number=2)])
        assert pairs[0].label == "Chorus 1→Chorus 2"


class TestG2Identity:
    def test_n_a_when_no_pairs(self) -> None:
        assert g2_identity([]).passed is None

    def test_pass_when_all_maintained(self) -> None:
        pairs = check_pairs([_snap(round_number=i, color="노랑") for i in range(1, 4)])
        result = g2_identity(pairs)
        assert result.passed is True
        assert result.detail == "2/2 쌍 정체성 유지"

    def test_fail_when_any_violated(self) -> None:
        snapshots = [_snap(round_number=1, color="노랑"), _snap(round_number=2, color="파랑")]
        result = g2_identity(check_pairs(snapshots))
        assert result.passed is False


class TestG3NewAxisWithinFive:
    def test_n_a_when_no_pairs(self) -> None:
        assert g3_new_axis_within_five([]).passed is None

    def test_fails_when_a_pair_within_five_has_no_new_axis(self) -> None:
        snapshots = [
            _snap(round_number=1, brightness=75, groups_on=5),
            _snap(round_number=2, brightness=80, groups_on=6),  # 새 축 있음
            _snap(round_number=3, brightness=80, groups_on=6),  # 새 축 없음(위반)
        ]
        result = g3_new_axis_within_five(check_pairs(snapshots))
        assert result.passed is False
        assert "1개" in result.detail

    def test_passes_when_every_pair_within_five_has_a_new_axis(self) -> None:
        snapshots = [_snap(round_number=i, brightness=70 + i * 5) for i in range(1, 6)]
        result = g3_new_axis_within_five(check_pairs(snapshots))
        assert result.passed is True

    def test_stagnant_pair_at_round_six_does_not_count(self) -> None:
        # round_number 6→7 쌍은 5회차 이내가 아니므로 G3 이 보지 않는다
        # (REQ-049 몫 — g49 가 대신 진다).
        snapshots = [_snap(round_number=i, brightness=70 + i * 5) for i in range(1, 6)] + [
            _snap(round_number=6, brightness=95),
            _snap(round_number=7, brightness=95),
        ]
        result = g3_new_axis_within_five(check_pairs(snapshots))
        assert result.passed is True


class TestG4FinalNewAxisAndHeadroom:
    def test_n_a_when_no_final_chorus(self) -> None:
        pairs = check_pairs([_snap(round_number=1), _snap(round_number=2)])
        result = g4_final_new_axis_and_headroom(pairs, before_final_remaining_motion=2)
        assert result.passed is None

    def test_passes_with_new_axis_and_remaining_motion(self) -> None:
        snapshots = [
            _snap(round_number=1, brightness=70),
            _snap(section="Final Chorus", occurrence=1, round_number=2, brightness=100),
        ]
        result = g4_final_new_axis_and_headroom(
            check_pairs(snapshots), before_final_remaining_motion=1
        )
        assert result.passed is True

    def test_fails_without_new_axis_even_with_remaining_motion(self) -> None:
        snapshots = [
            _snap(round_number=1, brightness=70, groups_on=5, area=0.5, motion=1, position="back"),
            _snap(
                section="Final Chorus",
                occurrence=1,
                round_number=2,
                brightness=70,
                groups_on=5,
                area=0.5,
                motion=1,
                position="back",
                phrase_density=1,
            ),
        ]
        result = g4_final_new_axis_and_headroom(
            check_pairs(snapshots), before_final_remaining_motion=3
        )
        assert result.passed is False

    def test_fails_with_new_axis_but_no_remaining_motion(self) -> None:
        snapshots = [
            _snap(round_number=1, brightness=70),
            _snap(section="Final Chorus", occurrence=1, round_number=2, brightness=100),
        ]
        result = g4_final_new_axis_and_headroom(
            check_pairs(snapshots), before_final_remaining_motion=0
        )
        assert result.passed is False

    def test_fails_when_remaining_motion_is_none(self) -> None:
        snapshots = [
            _snap(round_number=1, brightness=70),
            _snap(section="Final Chorus", occurrence=1, round_number=2, brightness=100),
        ]
        result = g4_final_new_axis_and_headroom(
            check_pairs(snapshots), before_final_remaining_motion=None
        )
        assert result.passed is False


class TestG49StagnationIsNormal:
    """REQ-049 — 6회차 이상에서 상태 유지는 결함이 아니라 정상이다."""

    def test_always_passes_even_with_flat_pairs_at_round_six_plus(self) -> None:
        snapshots = [_snap(round_number=6, brightness=95), _snap(round_number=7, brightness=95)]
        result = g49_stagnation_is_normal(check_pairs(snapshots))
        assert result.passed is True
        assert "1건" in result.detail

    def test_passes_and_reports_zero_when_nothing_stagnant(self) -> None:
        snapshots = [_snap(round_number=1, brightness=70), _snap(round_number=2, brightness=90)]
        result = g49_stagnation_is_normal(check_pairs(snapshots))
        assert result.passed is True
        assert "0건" in result.detail

    def test_never_flags_pairs_before_round_six(self) -> None:
        # 5회차 이내 정체 쌍이 있어도 이 게이트(REQ-049)는 그것을 보지
        # 않는다 — 그 몫은 G3 다. 날조 대조군: round_number<6 인 정체
        # 쌍만 있는 시나리오에서 detail 의 건수가 0 이어야 한다(부주의한
        # 구현이면 round_number 조건을 빠뜨리고 세었을 것이다).
        snapshots = [_snap(round_number=1, brightness=70), _snap(round_number=2, brightness=70)]
        result = g49_stagnation_is_normal(check_pairs(snapshots))
        assert result.passed is True
        assert "0건" in result.detail


class TestBuildChorusSnapshotsIntegration:
    """density.py 의 출력을 resolver 로 해석한 뒤 escalation 으로 요약하는
    전체 경로 — 모듈 경계가 실제로 맞물리는지 확인한다."""

    def test_rain_pairs_all_pass_g2_g3_g4(self) -> None:
        raw = [
            ("Intro", "0:00", "0:20"),
            ("Verse", "0:20", "0:33"),
            ("Verse", "0:33", "0:49"),
            ("Chorus", "0:49", "1:06"),
            ("Chorus", "1:06", "1:19"),
            ("Verse", "1:19", "1:46"),
            ("Chorus", "1:46", "2:03"),
            ("Chorus", "2:03", "2:18"),
            ("Chorus", "2:18", "2:46"),
            ("Verse", "2:46", "2:59"),
            ("Chorus", "2:59", "3:29"),
            ("Outro", "3:29", "3:42"),
        ]

        def mmss(text: str) -> float:
            m, s = text.split(":")
            return float(int(m) * 60 + int(s))

        chorus_positions = [i for i, (n, _, _) in enumerate(raw) if n == "Chorus"]
        last_chorus = chorus_positions[-1]
        occurrence_by_name: dict[str, int] = {}
        sections = []
        for i, (name, start, end) in enumerate(raw):
            label = "Final Chorus" if (name == "Chorus" and i == last_chorus) else name
            occurrence_by_name[label] = occurrence_by_name.get(label, 0) + 1
            sections.append(
                SectionOccurrence(
                    section=label,
                    occurrence=occurrence_by_name[label],
                    start=mmss(start),
                    end=mmss(end),
                )
            )

        result = compile_density(sections, 76.0)
        states = resolve_sequence(result.sequence)
        snapshots = build_chorus_snapshots(result.sequence, states, total_groups=len(GROUP_ROSTER))
        pairs = check_pairs(snapshots)

        assert g2_identity(pairs).passed is True
        assert g3_new_axis_within_five(pairs).passed is True

        final_index = next(
            i
            for i, row in enumerate(result.sequence)
            if row["section"] == "Final Chorus" and row["kind"] == "section"
        )
        before_final_motion = 3 - states[final_index - 1].motion
        assert (
            g4_final_new_axis_and_headroom(
                pairs, before_final_remaining_motion=before_final_motion
            ).passed
            is True
        )
