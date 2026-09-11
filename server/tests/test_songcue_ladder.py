"""t355 — 사라지는 후렴을 되살린다: 구간 세 필드 + 아껴두기 사다리.

정본은 `docs/proposals/song-structure-lighting-standard.md` (origin/main `d9e9fbe`)
§3(라벨·회차·변형) · §7(곡 안 반복은 미덕) · §7.1(아껴두기 사다리) · §12 항목 3(고칠 것).

**고치기 전에 실측한 것**(2026-09-11, main `d9e9fbe`): 5구간 EDM 입력이 큐 3장이 됐다.
후렴이 드롭과 값 라인이 같아 `VALUE_LINE_COLLISION` 으로 **버려졌기** 때문이다. 정본 §7 은
곡 안의 반복을 규범으로 못박는다 — 되돌아와야 하는 룩을 지우는 것이 결함이었다.

**이 파일이 재지 않는 것**도 적는다. 정본 §7.1 표의 마지막 두 칸(무빙 포지션 전환 ·
블라인더/백색 플래시)과 앙코르의 스트로브는 오늘의 어휘로 발화되지 않는다 — `Pan`/`Tilt`
는 `MovementSpec` 안에서만 합법이고 v1 번들은 movement 를 안 내며(카드 t357), 블라인더·
스트로브는 역할 어휘에 이름이 없다(카드 t356). 그래서 사다리의 실제 칸은 밝기 히트와
빔(줌·아이리스) 좁힘 셋이고, 그 뒤는 밝기의 남은 머리 공간이다.
"""

from __future__ import annotations

from server.looks.busking import VALUE_LINE_COLLISION
from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    LADDER_DIMMER_HIT,
    LADDER_ZOOM_PINCH,
    VARIANT_PRIME,
    SongCueLookSelection,
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

_MEASURED_FIVE_SECTIONS = (
    ("Intro", "0:00"),
    ("Build", "0:30"),
    ("Chorus", "1:00"),
    ("Drop", "1:30"),
    ("Chorus", "2:00"),
)


class TestTheThreeFields:
    """정본 §3 — 구간 하나는 라벨 + 회차 + 변형 표시로 적는다."""

    def test_instance_counts_per_label_and_the_prime_marks_a_variant(self):
        sections = parse_sections(
            (
                ("Chorus", "0:00"),
                ("Verse", "0:30"),
                ("Chorus", "1:00"),
                ("Chorus" + VARIANT_PRIME, "1:30"),
            )
        )

        assert [section.label for section in sections] == [
            "Chorus",
            "Verse",
            "Chorus",
            "Chorus",
        ]
        assert [section.instance for section in sections] == [1, 1, 2, 3]
        assert [section.variant for section in sections] == ["", "", "", VARIANT_PRIME]
        # 이름은 입력 그대로 남는다 — 변형 표시를 뗀 것은 라벨뿐이다.
        assert sections[3].name == "Chorus" + VARIANT_PRIME

    def test_cue_names_read_that_counter_instead_of_keeping_a_second_one(self):
        """변형 후렴이 「3회차」로 이름 붙는다 — 이름과 세기가 같은 카운터를 읽는 증거.

        이름이 **원래 이름**으로 따로 셌다면 프라임이 붙은 구간은 그 이름의 첫 등장이라
        번호가 안 붙거나 1이 됐을 것이다. 3이 나오는 것은 이름이 라벨 기준 회차
        (`_numbered_by_label`)를 읽는다는 뜻이고, 카운터가 한 벌이라는 뜻이다.
        """
        sections = parse_sections(
            (("Chorus", "0:00"), ("Chorus", "0:30"), ("Chorus" + VARIANT_PRIME, "1:00"))
        )
        bundle = _bundle_of(
            (sections[0], _look("a", dimmer=60)),
            (sections[1], _look("b", dimmer=70)),
            (sections[2], _look("c", dimmer=80)),
        )

        assert [section.cue_name for section in bundle.sections] == [
            "Chorus 1",
            "Chorus 2",
            "Chorus 3",
        ]


class TestTheChorusReturns:
    """대조군 ①(정본 §7) — 같은 룩이 회차만 달리 세 번 나가면 큐가 세 장이다."""

    def test_three_occurrences_of_one_look_store_three_distinct_cues(self):
        first, second, third = parse_sections(
            (("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20"))
        )
        look = _look("chorus", dimmer=90, zoom=18)
        bundle = _bundle_of((first, look), (second, look), (third, look))

        assert len(bundle.stored_sections) == 3
        assert bundle.skipped == ()
        lines = _value_lines(bundle)
        assert len(set(lines)) == 3, "세 회차의 값 라인이 서로 달라야 한다"

    def test_the_first_occurrence_is_the_base_look_and_its_colour_comes_back(self):
        """§7 — 코러스 1의 색은 이후 코러스에서 **되돌아와야** 한다.

        그래서 사다리는 색을 건드리지 않는다: 1회차의 값 라인은 기준 룩 그대로이고,
        2·3회차는 같은 룩의 같은 색에 요소를 하나씩 더한 것이다.
        """
        first, second, third = parse_sections(
            (("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20"))
        )
        look = _look("chorus", dimmer=90, zoom=18)
        bundle = _bundle_of((first, look), (second, look), (third, look))

        stored = bundle.stored_sections
        assert stored[0].commands[2] == _values_line_of(look)
        assert stored[0].ladder == ()
        # 룩의 정체는 그대로 — 다른 룩으로 갈아탄 것이 아니다.
        assert [section.selection.look.look_id for section in stored] == ["chorus"] * 3
        for line in _value_lines(bundle):
            assert "Attribute 'ColorRGB_R' At 72" in line
            assert "Attribute 'ColorRGB_G' At 100" in line
            assert "Attribute 'ColorRGB_B' At 0" in line

    def test_each_occurrence_adds_exactly_one_element_in_the_documented_order(self):
        """§7.1 — 「같은 룩 + 새 요소 하나」. 2회차는 밝기 히트, 3회차는 거기에 줌 좁힘."""
        first, second, third = parse_sections(
            (("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20"))
        )
        look = _look("chorus", dimmer=90, zoom=18)
        bundle = _bundle_of((first, look), (second, look), (third, look))

        assert [section.ladder for section in bundle.stored_sections] == [
            (),
            (LADDER_DIMMER_HIT,),
            (LADDER_DIMMER_HIT, LADDER_ZOOM_PINCH),
        ]
        lines = _value_lines(bundle)
        assert "Attribute 'Dimmer' At 90" in lines[0]
        assert "Attribute 'Dimmer' At 95" in lines[1]
        assert "Attribute 'Zoom' At 18" in lines[1], "2회차는 빔을 아직 안 쓴다 (머리 공간)"
        assert "Attribute 'Zoom' At 13" in lines[2]

    def test_the_headroom_is_real_the_first_occurrence_is_not_at_the_ceiling(self):
        """§7.1 머리 공간 — 1회차에 다 쓰지 않는다: 기준 룩을 손대지 않는 것이 그 성질이다."""
        only = parse_sections((("Chorus", "0:00"),))[0]
        look = _look("chorus", dimmer=90, zoom=18)
        bundle = _bundle_of((only, look))

        assert bundle.stored_sections[0].commands[2] == _values_line_of(look)
        assert bundle.stored_sections[0].ladder == ()


class TestCrossSongReuseIsNotWhatThisFixes:
    """대조군 ②(정본 §7 후반) — 곡 **사이**의 재사용은 이 카드가 고치는 것이 아니다.

    §7 의 비대칭이 그것이다: 곡 안의 반복은 미덕이고 곡 사이의 반복은 결함이다. 사다리는
    한 번들(= 한 곡) 안에서만 오른다 — 그러므로 다음 곡의 첫 후렴은 앞 곡의 첫 후렴과
    **값이 같다**. 그 재사용을 없애는 것은 룩 **선택**의 문제이고 정본 §12 항목 2(카드
    t357 계열)의 몫이다. 여기서는 그 경계를 실측으로 못박아 둔다.
    """

    def test_a_second_song_starts_from_the_base_look_again(self):
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40")))
        look = _look("chorus", dimmer=90, zoom=18)
        first_song = _bundle_of(*((section, look) for section in sections), title="Song A")
        second_song = _bundle_of(*((section, look) for section in sections), title="Song B")

        assert _value_lines(first_song) == _value_lines(second_song)
        assert _value_lines(second_song)[0] == _values_line_of(look)


class TestTheMeasuredRegression:
    """정본 §12 항목 3 의 실측 — 5구간이 큐 3장이 됐다. 이제 5장이다."""

    def test_five_sections_yield_five_cues_on_the_real_edm_library(self):
        library = load_library_from_dir()
        sections = parse_sections(_MEASURED_FIVE_SECTIONS)
        selections = map_sections_to_looks(sections, library, "edm")

        # 충돌의 원인이 여전히 실재한다는 비공허성: 후렴과 드롭이 **같은 룩**을 고른다
        # (룩 선택은 이 카드의 범위가 아니다 — 정본 §12 항목 2).
        chosen = [selection.look.look_id for selection in selections]
        assert chosen[2] == chosen[3] == chosen[4]

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert len(bundle.sections) == 5
        assert len(bundle.stored_sections) == 5
        assert bundle.skipped == ()
        assert len(set(_value_lines(bundle))) == 5


class TestTheLastResortSkipStillFires:
    """사다리가 오를 칸이 없으면 그때만 건너뛴다 — 그리고 그 갈래는 공허하지 않다."""

    def test_a_look_at_the_ceiling_with_no_beam_axis_still_collides(self):
        first, second = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40")))
        ceiling = _look("ceiling", dimmer=100)
        bundle = _bundle_of((first, ceiling), (second, ceiling))

        assert len(bundle.stored_sections) == 1
        assert [item.reason for item in bundle.skipped] == [VALUE_LINE_COLLISION]
        assert bundle.skipped[0].collides_with_section_index == first.index
        assert bundle.skipped[0].collides_with_cue_number == 1
        assert "ladder exhausted" in bundle.skipped[0].detail

    def test_the_same_shape_below_the_ceiling_stores_both_cues(self):
        """대조군 — 천장이 아니라면 같은 모양이 큐 두 장을 낸다. 위 단정이 「항상 건너뜀」을
        재는 것이 아니라는 증거."""
        first, second = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40")))
        movable = _look("movable", dimmer=90)
        bundle = _bundle_of((first, movable), (second, movable))

        assert len(bundle.stored_sections) == 2
        assert bundle.skipped == ()

    def test_two_cues_of_one_section_are_still_folded_instead_of_escalated(self):
        """한 구간을 마디로 쪼갠 큐끼리 겹치면 사다리가 아니라 예전처럼 접힌다.

        정본 §7 의 상승은 구간의 **반복 회차** 사이에서 일어난다. 같은 구간 안에서 밝기를
        올리면 구간 하나가 도중에 세어져, 밀도 경로의 축(강도는 유지하고 그림만 교체)을
        어긴다.
        """
        section = parse_sections((("Chorus", "0:00"),))[0]
        look = _look("chorus", dimmer=90, zoom=18)
        bundle = _bundle_of((section, look), (section, look))

        assert len(bundle.stored_sections) == 1
        assert [item.reason for item in bundle.skipped] == [VALUE_LINE_COLLISION]


class TestNoCollisionIsByteIdentical:
    """충돌이 없는 입력의 콘솔 명령은 고치기 전과 바이트 동일하다."""

    def test_the_command_bundle_of_a_collision_free_song_is_unchanged(self):
        first, second = parse_sections((("Chorus", "0:00"), ("Verse", "0:40")))
        bundle = _bundle_of(
            (first, _look("chorus", dimmer=90, zoom=18)),
            (second, _look("verse", dimmer=45)),
        )

        assert bundle.commands == (
            "ChangeDestination Root",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 90 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0 ; "
            "Attribute 'Zoom' At 18",
            "Store Sequence 1 Cue 1 'Chorus'",
            "Label Sequence 1 'Song'",
            "ClearAll",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 45 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0",
            "Store Sequence 1 Cue 2 'Verse'",
            "ClearAll",
        )
        assert all(section.ladder == () for section in bundle.stored_sections)


def _look(
    look_id: str,
    *,
    dynamics: int = 5,
    dimmer: float = 90,
    zoom: float | None = None,
    iris: float | None = None,
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    attributes = [
        AttributeValue("Dimmer", dimmer),
        AttributeValue("ColorRGB_R", 72),
        AttributeValue("ColorRGB_G", 100),
        AttributeValue("ColorRGB_B", 0),
    ]
    if zoom is not None:
        attributes.append(AttributeValue("Zoom", zoom))
    if iris is not None:
        attributes.append(AttributeValue("Iris", iris))
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=roles,
        attributes=tuple(attributes),
    )


def _values_line_of(look: Look) -> str:
    return " ; ".join(
        f"Attribute '{value.name}' At {int(value.value)}" for value in look.attributes
    )


def _value_lines(bundle) -> list[str]:
    return [section.commands[2] for section in bundle.stored_sections]


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _bundle_of(*pairs, title: str = "Song"):
    return build_songcue_bundle(
        title,
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
