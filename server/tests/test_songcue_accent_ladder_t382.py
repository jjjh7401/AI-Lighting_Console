"""t382 — 반복 회차는 양보로 자리를 얻어도 찍는 액센트를 잃지 않는다.

**고치기 전에 실측한 것**(카드 t382 보고, 후렴 일곱 회차·단일 축(``Dimmer`` 뿐)
룩·시작값 95): 값 라인 충돌-회피 사다리(``_distinct_values_line``)가 먼저이므로,
헤드룸이 한 걸음뿐인 룩에서는 대부분의 회차가 사다리를 오르지 못하고
양보(``LADDER_DIMMER_YIELD``, :func:`server.looks.songcue._yield_bundle`)나 양보로
비워진 기준값 자리를 그대로 물려받아 액센트 없이 밝기만 오르내렸다 — 7회차 중
1~5회차가 전부 ``(dimmer_yield,)``, 6회차만 ``(dimmer_hit, zoom_pinch)``, 7회차는
빈 튜플이었다.

이 파일은 :func:`server.looks.songcue._ensure_marking_accent` /
:func:`server.looks.songcue._finalize_marking_accents` 가 반복 회차(instance >= 2)
마다 정확히 하나의 찍는 액센트를 붙이는 것을, 그 값이 양보·재배열을 거쳐 최종
확정된 뒤에도 실측한다. 밝기(``Dimmer``) 자체의 단조 상승·재배열 성질(t366·t368·
t369)은 여기서 다시 재지 않는다 — 그 자리는 `test_songcue_ladder.py` ·
`test_songcue_chorus_rescue.py` 다.
"""

from __future__ import annotations

import server.looks.songcue as songcue_module
from server.looks.resolver import resolve_roles
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    LADDER_BLINDER_OR_FLASH,
    LADDER_DIMMER_YIELD,
    SongCueLookSelection,
    SongCueSection,
    _dimmer_from_values_line,
    _marking_accents,
    build_songcue_bundle,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_resolver import LXSEQ_RIG

#: 실기 리그 그대로(`test_songcue_accent_fixture.py` 와 같은 자료) — 블라인더 그룹이
#: 실제로 있는 리그라야 AC-2 가 공허하지 않다.
_LXSEQ_GROUPS: tuple[tuple[int, str], ...] = tuple(
    (index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG)
)

#: 카드 t382 재현 자리 그대로 — 단일 축(``Dimmer``) 룩, 후렴 7회, 시작값 95(헤드룸
#: 한 걸음). 줌·아이리스가 없으므로 그 두 액센트는 이 룩 자신의 값을 안 바꾼다
#: (블라인더·스트로브와 같은 무영향 — :data:`server.looks.songcue.LADDER_ZOOM_PINCH`
#: 독스트링). 그래서 이 룩에서는 어느 액센트가 실려도 값 라인이 갈리지 않고, 사다리가
#: 오를 수 있는 값은 「기준값 · 밝기 히트 한 걸음」 둘뿐이다 — 실측 카드의 결함을
#: 정확히 그대로 재현한다.
_MARKING = _marking_accents(allow_strobe=False)


def _single_axis_look(dimmer: float = 95.0) -> Look:
    return Look(
        look_id="chorus-single-axis",
        display_name="chorus-single-axis",
        genre="edm",
        dynamics=5,
        roles=("백라이트",),
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _chorus_times(count: int) -> tuple[tuple[str, str], ...]:
    times = []
    for index in range(count):
        total_seconds = index * 20
        minute, second = divmod(total_seconds, 60)
        times.append((f"{minute}:{second:02d}",))
    return tuple(("Chorus", time) for (time,) in times)


def _build(count: int, *, dimmer: float = 95.0):
    sections = parse_sections(_chorus_times(count))
    look = _single_axis_look(dimmer=dimmer)
    selections = tuple(
        SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
        for section in sections
    )
    return build_songcue_bundle(
        "Chorus Rise Ladder",
        selections,
        sequences_section=_sequences(1),
        groups_section=_groups(*FULL_RIG),
    )


class TestEveryRepeatOccurrenceCarriesOneAccent:
    """AC-1 — 헤드룸 한 걸음뿐인 룩의 7회차 전부: 저장 개수·밝기 단조·액센트 하나씩."""

    def test_all_seven_survive_with_non_decreasing_brightness_and_one_accent_each(self):
        bundle = _build(7, dimmer=95.0)

        assert bundle.skipped == (), "일곱 회차 전부 저장돼야 한다(t368)"
        assert len(bundle.stored_sections) == 7

        dimmers = [_dimmer_from_values_line(s.commands[2]) for s in bundle.stored_sections]
        assert all(value is not None for value in dimmers)
        assert dimmers == sorted(dimmers), f"밝기가 회차 순으로 뒤집히면 안 된다(t369): {dimmers}"

        by_instance = {s.section.instance: s for s in bundle.stored_sections}
        assert set(by_instance) == set(range(1, 8))

        for instance in range(2, 8):
            ladder = by_instance[instance].ladder
            marking_in_ladder = [rung for rung in ladder if rung in _MARKING]
            assert len(marking_in_ladder) == 1, (
                f"{instance}회차는 찍는 액센트를 정확히 하나 실어야 한다: ladder={ladder}"
            )

    def test_instances_two_three_four_cycle_through_different_accents(self):
        """액센트가 갈아탄다는 성질 — 연속 회차 셋이 같은 것으로 굳지 않는다."""
        bundle = _build(7, dimmer=95.0)
        by_instance = {s.section.instance: s for s in bundle.stored_sections}

        accents = []
        for instance in (2, 3, 4):
            ladder = by_instance[instance].ladder
            marking_in_ladder = [rung for rung in ladder if rung in _MARKING]
            assert len(marking_in_ladder) == 1
            accents.append(marking_in_ladder[0])

        assert len(set(accents)) == 3, (
            f"2·3·4회차의 액센트가 서로 달라야 회전이 실제로 도는 것이 보인다: {accents}"
        )


class TestForcedAccentReachesTheConsoleWhenItPicksTheBlinder:
    """AC-2 — 강제로 얹힌 액센트가 블라인더를 고르면, 리그에 그 그룹이 있는 한 실제로
    콘솔 그룹 명령까지 나간다.

    이 이음매를 직접 잰다: 3회차(``instance=3``, 회전 자리 ``(3-2)%3=1`` →
    ``blinder_or_flash``) 선택 하나를 :func:`server.looks.songcue._section_bundle`
    에 **비어 있는** ``emitted`` 로 직접 넣는다 — 이렇게 하면 ``_distinct_values_line``
    이 기준값을 곧바로 돌려준다(``rungs=()``, 아무도 그 값 라인을 아직 안 썼으므로),
    정확히 카드 t382 가 고치는 모양이다("반복이 깊어져도 값 겹침이 없으면 사다리를
    안 오른다" — 실제 곡에서는 회수가 자리를 비워 준 뒤에 이 모양이 생긴다,
    `_ensure_marking_accent` 독스트링). 전체 파이프라인(회수+재배열)을 다 태우면
    이 정확한 조합(3회차·블라인더·재배열 생존)을 결정론적으로 재현하기 어려워
    (재배열이 어느 회차가 어느 값을 받을지 다시 섞는다), 실제 결함 지점을 직접
    잰다.
    """

    def test_a_direct_success_landing_on_the_base_line_still_lights_the_blinder(self):
        resolution = resolve_roles(_groups(*_LXSEQ_GROUPS))
        look = Look(
            look_id="chorus-single-axis",
            display_name="chorus-single-axis",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(
                AttributeValue("Dimmer", 60.0),
                AttributeValue("ColorRGB_R", 72),
                AttributeValue("ColorRGB_G", 100),
                AttributeValue("ColorRGB_B", 0),
            ),
        )
        section = SongCueSection(
            name="Chorus",
            start_ms=0,
            index=0,
            dynamics=(4, 5),
            requires_explicit_dynamics=False,
            label="Chorus",
            instance=3,
            variant="",
        )
        selection = SongCueLookSelection(section=section, requested_dynamics=(5,), look=look)

        bundle = songcue_module._section_bundle(
            selection=selection,
            cue_number=1,
            cue_name="Chorus",
            sequence_number=1,
            resolution=resolution,
            emitted={},
        )

        assert bundle.skipped == ()
        assert bundle.ladder == (LADDER_BLINDER_OR_FLASH,), (
            "값이 곧바로 기준값으로 확정돼도(빈 사다리) 3회차는 액센트를 하나 받는다"
        )
        fixture = bundle.accent_fixture
        assert fixture is not None, "리그에 블라인더 그룹이 있으므로 무대 명령까지 나가야 한다"
        assert fixture.rung == LADDER_BLINDER_OR_FLASH
        assert any(f"Group {group}" in bundle.commands for group in fixture.groups)
        # 값 라인 자체(Dimmer 등)는 블라인더가 안 바꾼다 — 기준값 그대로.
        assert bundle.commands[2] == (
            "Attribute 'Dimmer' At 60 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0"
        )


class TestHeadroomCaseIsUntouched:
    """AC-3 — 헤드룸이 넉넉해 애초에 양보가 필요 없는 곡은 이 카드 이전과 바이트
    동일하다. 값은 카드 조사 중 실측한 것을 그대로 굳힌 것이다(회귀 대조군).
    """

    def test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after(self):
        bundle = _build(7, dimmer=20.0)

        assert bundle.skipped == ()
        by_instance = {s.section.instance: s for s in bundle.stored_sections}

        expected_dimmers = {1: 20.0, 2: 25.0, 3: 30.0, 4: 35.0, 5: 40.0, 6: 45.0, 7: 50.0}
        expected_ladders = {
            1: (),
            2: ("dimmer_hit",),
            3: ("dimmer_hit", "dimmer_hit", "blinder_or_flash"),
            4: ("dimmer_hit", "dimmer_hit", "dimmer_hit", "iris_pinch"),
            5: ("dimmer_hit", "dimmer_hit", "dimmer_hit", "dimmer_hit", "zoom_pinch"),
            6: (
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "blinder_or_flash",
            ),
            7: (
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "dimmer_hit",
                "iris_pinch",
            ),
        }
        for instance, expected_dimmer in expected_dimmers.items():
            section = by_instance[instance]
            assert _dimmer_from_values_line(section.commands[2]) == expected_dimmer
            assert section.ladder == expected_ladders[instance], (
                f"{instance}회차 사다리가 이 카드 이전과 달라지면 안 된다: {section.ladder}"
            )


class TestExistingGuardsStillHold:
    """AC-4 — 기존 대조군(3회차 짧은 반복·충돌 없는 입력)이 이 카드로 안 흔들린다."""

    def test_three_occurrence_control_from_the_library_still_climbs_normally(self):
        """`test_songcue_ladder.py` ``TestOneMarkingAccentPerCue`` 와 같은 룩·회차 —
        여기서는 3회차의 값·개수만 재확인한다(전체 단정은 그 파일이 든다)."""
        from server.looks.loader import load_library_from_dir
        from server.looks.songcue import map_sections_to_looks

        library = load_library_from_dir()
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20")))
        bundle = build_songcue_bundle(
            "Song",
            map_sections_to_looks(sections, library, "edm"),
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )
        assert bundle.skipped == ()
        assert len(bundle.stored_sections) == 3
        assert len({s.commands[2] for s in bundle.stored_sections}) == 3

    def test_no_collision_input_stays_byte_identical(self):
        """구간 하나뿐 — 사다리도 액센트 강제도 만질 것이 없다."""
        bundle = _build(1, dimmer=60.0)
        assert bundle.skipped == ()
        assert len(bundle.stored_sections) == 1
        assert bundle.stored_sections[0].ladder == ()


class TestDropStillNeverYields:
    """AC-5 — 드롭은 여전히 절대 양보하지 않는다(t366)."""

    def test_the_only_drop_in_the_song_never_carries_a_yield(self):
        sections = parse_sections((("Verse", "0:00"), ("Drop", "0:20")))
        look = _single_axis_look(dimmer=100.0)
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section in sections
        )
        bundle = build_songcue_bundle(
            "Drop Song",
            selections,
            sequences_section=_sequences(1),
            groups_section=_groups(*FULL_RIG),
        )
        drop_sections = [s for s in bundle.stored_sections if s.section.label == "Drop"]
        assert drop_sections, "드롭이 저장돼야 이 대조군이 공허하지 않다"
        for section in drop_sections:
            assert LADDER_DIMMER_YIELD not in section.ladder
