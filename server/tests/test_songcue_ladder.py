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

import server.looks.songcue as songcue_module
from server.looks.busking import VALUE_LINE_COLLISION
from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    LADDER_DIMMER_HIT,
    LADDER_DIMMER_YIELD,
    LADDER_IRIS_PINCH,
    LADDER_RUNGS,
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


class TestTheBundleBuilderHoldsNoCrossSongState:
    """대조군 ②(정본 §7 후반) — 곡 **사이**의 재사용은 이 계층에서 안 고친다.

    **카드 t358 이 이 클래스를 고쳐 썼다.** 원래 이름은
    ``TestCrossSongReuseIsNotWhatThisFixes`` 였고, 「다음 곡의 첫 후렴은 앞 곡과 값이
    같다」를 **현재 동작**으로 적어 두었다 — 즉 t358 이 없애려던 결함을 이 파일이 기준선
    으로 들고 있었다. 지우지 않고 뜻을 바꾼 이유는, 같은 단정이 t358 이후에는 **경계**를
    재기 때문이다.

    경계는 이렇다: ``build_songcue_bundle`` 은 여전히 곡 사이의 기억을 **하나도** 갖지
    않는다. 같은 룩을 손으로 들려 주면 두 곡의 값 라인은 바이트 동일하다. 곡 B 가 다른
    룩으로 열리는 것은 한 계층 앞(``map_sections_to_looks`` 의 ``used_look_ids``)에서
    일어나고, 그 기억의 주인은 세션이다(``server/looks/song_history.py``). 이 분리가
    깨지면 곡 사이 회피가 곡 안으로 새어 후렴 2회차가 1회차를 피하게 되므로, 여기서
    「번들은 기억이 없다」를 계속 재는 것이 §7 의 비대칭을 지키는 일이다.

    곡 사이 축 자체의 실측은 ``server/tests/test_songcue_cross_song.py`` 에 있다.
    """

    def test_one_look_handed_to_two_bundles_still_yields_the_same_lines(self):
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40")))
        look = _look("chorus", dimmer=90, zoom=18)
        first_song = _bundle_of(*((section, look) for section in sections), title="Song A")
        second_song = _bundle_of(*((section, look) for section in sections), title="Song B")

        assert _value_lines(first_song) == _value_lines(second_song)
        assert _value_lines(second_song)[0] == _values_line_of(look)

    def test_the_selection_layer_is_where_the_second_song_turns_away(self):
        """같은 구간 모양에 기억만 더하면 룩이 바뀐다 — 번들이 아니라 **선택**이 바꾼다.

        위 단정이 「곡 사이 재사용이 아직 안 고쳐졌다」로 다시 읽히지 않게 하는 대조군이다.
        """
        library = load_library_from_dir()
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40")))

        song_a = map_sections_to_looks(sections, library, "edm")
        song_b = map_sections_to_looks(
            sections,
            library,
            "edm",
            used_look_ids=[selection.look.look_id for selection in song_a],
        )

        assert song_a[0].look.look_id != song_b[0].look.look_id


class TestTheMeasuredRegression:
    """정본 §12 항목 3 의 실측 — 5구간이 큐 3장이 됐다. 이제 5장이다."""

    def test_five_sections_yield_five_cues_on_the_real_edm_library(self):
        library = load_library_from_dir()
        sections = parse_sections(_MEASURED_FIVE_SECTIONS)
        selections = map_sections_to_looks(sections, library, "edm")

        # 비공허성 — 충돌의 원인이 여전히 실재한다: 후렴 두 회차가 **같은 룩**이다.
        #
        # **2026-09-12 (카드 t360) 에 이 줄을 뒤집었다.** t355 가 적을 때는 셋이 전부
        # 같은 룩이었고(`chosen[2] == chosen[3] == chosen[4]`), 그 줄 자신이 사유를
        # 「룩 선택은 이 카드의 범위가 아니다 — 정본 §12 항목 2」라고 적어 두었다.
        # t360 이 그 항목을 닫았으므로 드롭은 이제 후렴과 **다른** 룩이다. 사라진 것은
        # 결함이지 이 검사의 대상이 아니다 — 사다리가 재는 것은 「같은 라벨의 반복이
        # 되돌아와도 큐가 사라지지 않는다」이고, 그 축은 후렴 1·2회차가 그대로 든다.
        chosen = [selection.look.look_id for selection in selections]
        assert chosen[2] == chosen[4], "같은 라벨의 회차는 되돌아온다 (정본 §7)"
        assert chosen[3] != chosen[2], "다른 라벨은 앞 큐와 대비된다 (정본 §12 항목 2)"

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


#: 카드 t366 실측 — 8구간 EDM 입력, 마디 없이 라벨만 배치했다(정본 §2.2 어휘 그대로).
#: 다이내믹스는 배차서가 적은 값(2/2/4/3/4/2/5/1)을 §6 표가 그대로 배정한다.
_MEASURED_EIGHT_SECTIONS = (
    ("Intro", "0:00"),
    ("Verse", "0:20"),
    ("Chorus", "0:50"),
    ("Verse", "1:20"),
    ("Chorus", "1:50"),
    ("Breakdown", "2:20"),
    ("Drop", "2:40"),
    ("Outro", "3:10"),
)


class TestTheDropDoesNotYield:
    """t366 — 드롭이 값 충돌로 버려지지 않는다: 물러서는 쪽은 상대다.

    **고치기 전에 실측한 것**(2026-09-12, main `13595be`, 실기 콘솔 대상 드라이런).
    위 8구간을 실제 EDM 라이브러리에 태우면 코러스 두 회차와 드롭이 전부 같은 룩
    (``edm-drop-crimson``, ``Dimmer`` 100·``Zoom`` 10, ``Iris`` 축 없음)을 받는다.
    사다리는 코러스 2회차까지는 오르지만(빔 축 하나로 겨우), 드롭이 오를 차례엔
    쓸 수 있는 값이 이미 둘 다(기준값·줌 좁힌 값) 앞 코러스들이 차지한 뒤라 사다리가
    비공허하게 소진되고 드롭이 통째로 버려졌다 — 저장된 큐가 ``[1,2,3,4,5,6,8]``
    (드롭인 7번이 없다).
    """

    def test_eight_sections_yield_eight_cues_on_the_real_edm_library(self):
        library = load_library_from_dir()
        sections = parse_sections(_MEASURED_EIGHT_SECTIONS)
        selections = map_sections_to_looks(sections, library, "edm")

        # 비공허성 — 충돌의 원인이 여전히 실재한다: 코러스 두 회차와 드롭이 실제로
        # 같은 룩을 받는다. 이 값이 바뀌면(라이브러리·배정 로직이 갈리면) 이 검사는
        # 드롭 회수 경로가 아니라 다른 경로를 재는 것이므로, 여기서 먼저 빨개진다.
        chosen = [selection.look.look_id for selection in selections]
        assert chosen[2] == chosen[4] == chosen[6] == "edm-drop-crimson", (
            "코러스 두 회차와 드롭이 같은 룩을 받아야 이 회수 경로가 실제로 켜진다"
        )

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == (), "드롭이 값 충돌로 버려지면 안 된다"
        assert len(bundle.stored_sections) == 8
        assert [section.cue_number for section in bundle.stored_sections] == list(range(1, 9))
        assert len(set(_value_lines(bundle))) == 8, "여덟 큐의 값 라인은 서로 달라야 한다"

        drop = bundle.stored_sections[6]
        assert drop.section.label == "Drop"
        # 드롭은 사다리를 안 오른다 — 정본 §6 「마지막 드롭은 전 리그 최대」 그대로,
        # 기준 룩의 값을 손대지 않고 낸다.
        assert drop.ladder == ()
        assert drop.commands[2] == (
            "Attribute 'Dimmer' At 100 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 15 ; "
            "Attribute 'Zoom' At 10"
        )

        # 물러선 쪽은 코러스 1회차다 — 룩 정체성은 그대로(정본 §7), 밝기만 한 칸 내려
        # 자리를 비켰다.
        yielded = bundle.stored_sections[2]
        assert yielded.section.label == "Chorus"
        assert yielded.section.instance == 1
        assert LADDER_DIMMER_YIELD in yielded.ladder
        assert "Attribute 'Dimmer' At 95" in yielded.commands[2]

        # 코러스 2회차는 이 회수와 무관하게 그대로 선다 — 회수는 충돌한 그 한 큐만
        # 건드린다.
        second_chorus = bundle.stored_sections[4]
        assert second_chorus.section.label == "Chorus"
        assert second_chorus.section.instance == 2
        assert LADDER_DIMMER_YIELD not in second_chorus.ladder

    def test_a_yield_still_respects_the_darkness_floor(self, monkeypatch):
        """물러설 자리가 이미 다 찼고 바닥까지 닿으면 회수가 실패하고 드롭이 원래대로
        버려진다 — :data:`DARKNESS_FLOOR` 는 이 회수에도 그대로 산다.

        바닥을 실제 20 에서 재려면 15칸을 미리 채워야 해서, 검사 안에서만
        :data:`songcue_module.DARKNESS_FLOOR` 를 95 로 낮춘다 — 물러서는 방향·폭
        (:data:`_HIT_STEP`)은 그대로이고, 「내려갈 수 있는 가장 낮은 자리」라는 바닥의
        뜻만 검사 스케일로 줄인 것이다. 코러스가 천장(100)에서 딱 한 칸(95) 내려가면
        바닥이고, 그 한 칸을 벌스가 이미 차지해 두면 회수가 더 내려갈 데가 없다.
        """
        monkeypatch.setattr(songcue_module, "DARKNESS_FLOOR", 95)
        chorus, verse, drop = parse_sections(
            (("Chorus", "0:00"), ("Verse", "0:20"), ("Drop", "0:40"))
        )
        ceiling = _look("ceiling2", dimmer=100)  # 천장, 빔 축 없음 — 드롭이 못 오른다.
        floor_slot = _look("verse_filler", dimmer=95)  # 바닥 자리를 미리 차지한다.
        bundle = _bundle_of((chorus, ceiling), (verse, floor_slot), (drop, ceiling))

        assert len(bundle.stored_sections) == 2
        assert [section.section.label for section in bundle.stored_sections] == [
            "Chorus",
            "Verse",
        ]
        assert [item.reason for item in bundle.skipped] == [VALUE_LINE_COLLISION]
        assert bundle.skipped[0].section.label == "Drop"
        # 코러스는 물러서려다 실패했으므로 원래 값 그대로 선다 — 회수 흔적이 없다.
        assert bundle.stored_sections[0].ladder == ()
        assert bundle.stored_sections[0].commands[2] == _values_line_of(ceiling)


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
    """충돌이 없는 입력의 콘솔 명령에 **사다리가 손대지 않는다**.

    카드 t363 이 이 기대값의 Store 두 줄에 ``CueFade`` 를 더했다(정본 §9). 이 검사가 재는
    성질은 그대로다 — 값 라인과 그룹 줄이 기준 룩 그대로이고 사다리 칸이 하나도 안 붙는
    것. 페이드는 사다리 축이 아니라 구간 라벨이 정하는 별개 축이다.
    """

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
            "Store Sequence 1 Cue 1 'Chorus' CueFade 0.2",
            "Label Sequence 1 'Song'",
            "ClearAll",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 45 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0",
            "Store Sequence 1 Cue 2 'Verse' CueFade 2",
            "ClearAll",
        )
        assert all(section.ladder == () for section in bundle.stored_sections)


class TestOneMarkingAccentPerCue:
    """t361 — 한 큐에 **찍는 액센트는 하나**, 밝기만 누적한다(정본 §6.1, 감독 결정 2026-09-12).

    **고치기 전에 실측한 것**(2026-09-12, main ``051e98b``): 후렴 4회차 한 큐가
    ``Zoom At 13`` 과 ``Iris At 55`` 를 함께 실었다 — 둘 다 실제로 값을 바꿨고, §6.1
    [HARD]「한 큐에 하나만」 위반이다. 원인은 칸 목록의 앞자락을 그대로 잘라 쓴 것
    (``_LADDER_CLIMB[:n]``)이고, 그래서 깊이가 3에 닿으면 빔 계열 둘이 같이 나갔다.

    갈래는 감독이 정했다 — **누적하는 축은 밝기 하나**, 나머지는 큐당 하나이고 뒤 회차는
    앞 회차의 액센트 위에 얹는 것이 아니라 **갈아탄다**.
    """

    #: 찍는 액센트를 **검사 쪽에서 따로 적는다**. 구현의 ``_MARKING_ACCENTS`` 를 읽어
    #: 세면 그 목록이 비는 순간 단정이 공허해진다(0개도 「하나 이하」다). 아래
    #: :meth:`test_every_ladder_rung_is_classified` 가 새 칸이 조용히 새는 것을 막는다.
    _MARKING = (LADDER_ZOOM_PINCH, LADDER_IRIS_PINCH)

    def test_every_ladder_rung_is_classified(self):
        """새 칸이 생기면 여기가 먼저 빨개진다 — 분류 안 된 칸은 세어지지 않는다."""
        assert set(LADDER_RUNGS) == {LADDER_DIMMER_HIT, *self._MARKING}

    def test_the_third_chorus_carries_brightness_plus_exactly_one_marking_accent(self):
        """양성 대조군 — 실측 라이브러리의 후렴 3회차. 명령 줄과 **개수**를 함께 잰다."""
        library = load_library_from_dir()
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20")))
        bundle = build_songcue_bundle(
            "Song",
            map_sections_to_looks(sections, library, "edm"),
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        third = bundle.stored_sections[2]
        assert self._marking_count(third.ladder) == 1, "찍는 액센트는 큐당 하나"
        assert LADDER_DIMMER_HIT in third.ladder, "밝기는 누적 축이므로 함께 실린다"
        # 실제로 나가는 명령 줄 — 밝기 히트(90→95)와 빔 히트(18→13) 하나.
        assert (
            third.commands[2] == "Attribute 'Dimmer' At 95 ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0 ; "
            "Attribute 'Zoom' At 13"
        )
        # t355 의 보증 — 세 회차의 값 라인은 여전히 서로 다르다.
        assert len(set(_value_lines(bundle))) == 3
        assert bundle.skipped == ()

    def test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking(self):
        """고친 그 자리 — 줌 위에 아이리스를 **얹지 않고** 갈아탄다.

        룩이 줌과 아이리스를 **둘 다** 실어야 이 단정이 공허하지 않다(없는 축의 칸은
        아무것도 안 바꾸므로, 축이 하나뿐인 룩에서는 쌓아도 한 줄만 나간다).
        """
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(5)))
        look = _look("chorus", dimmer=80, zoom=18, iris=60)
        bundle = _bundle_of(*((section, look) for section in sections))

        assert [section.ladder for section in bundle.stored_sections] == [
            (),
            (LADDER_DIMMER_HIT,),
            (LADDER_DIMMER_HIT, LADDER_ZOOM_PINCH),
            (LADDER_DIMMER_HIT, LADDER_DIMMER_HIT, LADDER_IRIS_PINCH),
            (LADDER_DIMMER_HIT, LADDER_DIMMER_HIT, LADDER_DIMMER_HIT, LADDER_ZOOM_PINCH),
        ]
        lines = _value_lines(bundle)
        # 4회차: 줌은 기준값으로 **돌아가고** 아이리스가 좁혀진다. 밝기는 계속 오른다.
        assert "Attribute 'Zoom' At 18" in lines[3]
        assert "Attribute 'Iris' At 55" in lines[3]
        assert "Attribute 'Dimmer' At 90" in lines[3]
        # 5회차: 다시 줌으로 갈아타고 아이리스가 기준값으로 돌아온다.
        assert "Attribute 'Zoom' At 13" in lines[4]
        assert "Attribute 'Iris' At 60" in lines[4]
        assert "Attribute 'Dimmer' At 95" in lines[4]
        # 고치기 전 실측 그 자리 — 한 줄에 빔 계열 둘이 함께 나가던 것이 사라졌다.
        for line in lines:
            assert not ("Attribute 'Zoom' At 13" in line and "Attribute 'Iris' At 55" in line)
        for section in bundle.stored_sections:
            assert self._marking_count(section.ladder) <= 1
        assert len(set(lines)) == 5
        assert bundle.skipped == ()

    def test_brightness_carries_the_cue_when_accent_swapping_cannot(self):
        """액센트 갈아타기만으로는 값을 못 가르는 입력 — 큐가 사라지지 않고 밝기가 든다.

        빔 축이 아예 없는 룩이라 줌·아이리스 칸은 **아무것도 안 바꾼다**. 액센트에만
        기대면 2회차 이후가 전부 앞 큐와 같아져 버려졌을 것이다.
        """
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(4)))
        look = _look("washonly", dimmer=70)
        bundle = _bundle_of(*((section, look) for section in sections))

        assert len(bundle.stored_sections) == 4
        assert bundle.skipped == ()
        lines = _value_lines(bundle)
        assert len(set(lines)) == 4
        for expected in ("At 70", "At 75", "At 80", "At 85"):
            assert any(f"Attribute 'Dimmer' {expected}" in line for line in lines)
        # 빔 축이 없으므로 어떤 줄에도 줌·아이리스가 나가지 않는다 — 공허하지 않다는 증거.
        for line in lines:
            assert "Zoom" not in line and "Iris" not in line

    def test_the_accent_carries_it_when_brightness_is_at_the_ceiling(self):
        """거울상 대조군 — 밝기가 천장이면 액센트가 값을 가른다. 그래도 큐당 하나다."""
        first, second = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40")))
        look = _look("ceiling", dimmer=100, zoom=18, iris=60)
        bundle = _bundle_of((first, look), (second, look))

        assert len(bundle.stored_sections) == 2
        assert bundle.skipped == ()
        second_line = _value_lines(bundle)[1]
        assert "Attribute 'Dimmer' At 100" in second_line, "밝기는 더 못 오른다"
        assert "Attribute 'Zoom' At 13" in second_line
        assert "Attribute 'Iris' At 60" in second_line, "아이리스는 아직 안 쓴다 (머리 공간)"
        assert self._marking_count(bundle.stored_sections[1].ladder) == 1

    @classmethod
    def _marking_count(cls, rungs) -> int:
        return sum(1 for rung in rungs if rung in cls._MARKING)


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
