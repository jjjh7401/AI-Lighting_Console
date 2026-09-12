"""t360 — 한 곡 안에서 룩을 이름 알파벳 순으로 고르지 않는다.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` §6(구간별 조명 의도) ·
§6.1(액센트는 한 번에 하나) · §6.3(색은 적게) · §7(곡 안 반복은 미덕) ·
§12 항목 2(고칠 것: 「룩을 이름 알파벳 순으로 고른다」).

**고치기 전에 실측한 것**(2026-09-12, main ``7d78876``). 5구간 EDM 입력
(Intro·Build·Chorus·Drop·Chorus)의 뒤 세 구간이 전부 ``edm-drop-acid`` 하나였다 —
후렴도 드롭도 다음 후렴도 같은 그림이다. 원인은 ``busking.looks_for_genre`` 의
``(dynamics, look_id)`` 전순서와 그 선두를 집는 선택 계층이고, 그래서 같은 세기 안에서는
**룩 id 의 사전순**이 무대를 정했다.

**이 파일이 재는 두 축과, 그 둘이 부딪히지 않는 이유.**

- 라벨이 §6 행을 가리키면 그 행의 밝기 구간이 후보를 가른다(§6).
- 라벨이 **바뀌면** 앞 큐와 가장 대비되는 룩을 고른다(§12 항목 2 · §8).
- 라벨이 **되풀이되면** 1회차의 룩이 되돌아온다(§7 [HARD]). 회차 사이의 변화는 룩
  교체가 아니라 사다리가 만든다(§7.1, 카드 t355).

세 번째 줄이 없으면 두 번째 줄이 t355 를 방향만 바꿔 되돌린다 — 후렴 2회차가 1회차를
피해 다른 룩으로 갈아타고, 「돌아와야 하는 것이 사라진다」.

**이 파일이 재기만 하고 안 고쳤던 것은 카드 t361 이 닫았다.** §6.1 [HARD]「한 큐에 하나만」
은 이제 지켜진다 — 감독이 갈래를 정했고(2026-09-12: 밝기만 누적), 사다리가 액센트를 쌓지
않고 갈아탄다. 아래 :class:`TestTheOneAccentRuleNowHolds` 가 그 자리를 계속 지킨다.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from server.looks import songcue
from server.looks.loader import load_library_from_dir
from server.looks.matching import DYNAMICS_TERMS
from server.looks.schema import AttributeValue, Look, LookLibrary
from server.looks.section_intent import (
    SECTION_INTENTS,
    brightness_fits,
    contrast,
    intent_for_label,
    sorted_candidates,
)
from server.looks.songcue import (
    LADDER_DIMMER_HIT,
    LADDER_ZOOM_PINCH,
    build_songcue_bundle,
    escalate_attributes,
    map_sections_to_looks,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_ladder import _sequences

#: 정본 §12 항목 2 가 실측 근거로 인용한 그 입력.
_MEASURED_FIVE_SECTIONS = (
    ("Intro", "0:00"),
    ("Build", "0:30"),
    ("Chorus", "1:00"),
    ("Drop", "1:30"),
    ("Chorus", "2:00"),
)


def _chosen(sections, genre: str = "edm", **kwargs) -> list[str]:
    library = load_library_from_dir()
    selections = map_sections_to_looks(parse_sections(sections), library, genre, **kwargs)
    return [
        selection.look.look_id if selection.look else selection.reason for selection in selections
    ]


class TestTheLabelSteersSelection:
    """정본 §6 — 구간 이름이 세기뿐 아니라 **의도**를 정한다."""

    def test_a_labelled_section_prefers_a_look_inside_its_six_row(self):
        """rock 의 vocal 대역 실측 — §6 verse 행(25~50%)이 사전순 선두를 뒤로 보낸다.

        고치기 전 rock 의 첫 Verse 는 ``rock-verse-amber-grit`` 였다. 그 룩만이 아니라
        **사전순이** 골랐다: ``amber-grit`` < ``verse-side``. 밝기는 52% 로 §6 verse 행
        바깥이고, 같은 세기의 ``rock-verse-side`` 는 48% 로 안이다.
        """
        library = load_library_from_dir()
        amber = library.by_id("rock-verse-amber-grit")
        side = library.by_id("rock-verse-side")
        verse = intent_for_label("Verse")

        assert verse is not None
        assert verse.row == "verse"
        assert verse.brightness == (25, 50)
        # 비공허성 — 두 룩이 실제로 §6 구간의 양쪽에 있다.
        assert brightness_fits(verse, amber) is False
        assert brightness_fits(verse, side) is True

        assert _chosen((("Verse", "0:00"),), genre="rock") == ["rock-verse-side"]

    def test_a_label_with_no_six_row_leaves_the_existing_order_alone(self):
        """§6 행이 없는 라벨은 **행을 지어내지 않는다** — 기존 전순서가 그대로 답이다.

        ``Bridge`` 는 오늘의 어휘(``matching.DYNAMICS_TERMS``)에 없어서 세기조차 해석되지
        않는다(정본 §12 항목 4: 어휘 추가는 별도 처방). 세기를 손으로 줘도 §6 행은 여전히
        없고, 그러면 이 축은 아무 말도 하지 않는다.
        """
        assert intent_for_label("Bridge") is None

        library = load_library_from_dir()
        sections = parse_sections((("Bridge", "0:00"),))
        selections = map_sections_to_looks(sections, library, "rock", {0: 2})

        head = min(
            (look for look in library.looks if look.genre == "rock" and look.dynamics == 2),
            key=lambda look: (look.dynamics, look.look_id),
        )
        assert selections[0].look.look_id == head.look_id == "rock-verse-amber-grit"

    def test_two_rows_named_at_once_is_no_constraint_rather_than_half_of_one(self):
        """행이 둘 걸리는 이름은 ``None`` — ``resolve_genre`` 가 장르 둘을 접는 규율."""
        assert intent_for_label("Build to Chorus") is None
        assert intent_for_label("Build") is not None
        assert intent_for_label("Chorus") is not None

    def test_every_row_term_comes_from_the_shared_section_vocabulary(self):
        """§6 행의 말은 한 벌뿐이다 — 여기서 새 말을 만들면 어휘가 갈라진다."""
        for _row, _brightness, terms in SECTION_INTENTS:
            assert terms
            for term in terms:
                assert term in DYNAMICS_TERMS, term

    def test_the_six_row_divergence_from_the_old_order_is_exactly_one(self):
        """전수 실측 — §6 의도가 사전순 선두를 바꾸는 자리는 라이브러리 전체에서 **한 곳**.

        「라벨을 걸어도 거의 아무것도 안 바뀐다」와 「다 바뀐다」는 둘 다 주장이다. 네
        장르 × §6 행 넷을 전수로 돌려 실제 개수를 센다. 룩이 늘면 이 수가 움직이고,
        움직이면 그때 다시 읽어야 한다.
        """
        library = load_library_from_dir()
        genres = sorted({look.genre for look in library.looks})
        diverged = []
        for genre in genres:
            for row, _brightness, terms in SECTION_INTENTS:
                intent = intent_for_label(terms[0])
                band = DYNAMICS_TERMS[terms[0]]
                matches = tuple(
                    look for look in library.looks if look.genre == genre and look.dynamics in band
                )
                if not matches:
                    continue
                before = sorted_candidates(matches, previous=None, intent=None)[0]
                after = sorted_candidates(matches, previous=None, intent=intent)[0]
                if before.look_id != after.look_id:
                    diverged.append((genre, row, before.look_id, after.look_id))

        assert diverged == [("rock", "verse", "rock-verse-amber-grit", "rock-verse-side")]


class TestTheContrastDefinition:
    """대비는 자료가 실제로 드는 세 축의 합이다 — 색 · 밝기 · 역할."""

    def test_the_three_axes_sum_to_the_reported_contrast(self):
        """실제 라이브러리 값으로 셈을 전개한다. 분수라 자릿수 반올림이 없다."""
        library = load_library_from_dir()
        acid = library.by_id("edm-drop-acid")  # D90 rgb(72,100,0) 역할 4
        crimson = library.by_id("edm-drop-crimson")  # D100 rgb(100,0,15) 역할 6
        beams = library.by_id("edm-drop-beams")  # D100 rgb(70,88,100) 역할 3

        # 색 (|72-100| + |100-0| + |0-15|) / 300 = 143/300
        # 밝기 |90-100| / 100 = 30/300
        # 역할 1 - 4/6 = 100/300
        assert contrast(acid, crimson) == Fraction(143 + 30 + 100, 300) == Fraction(91, 100)
        # 색 (2 + 12 + 100)/300 · 밝기 30/300 · 역할 1 - 3/4 = 75/300
        assert contrast(acid, beams) == Fraction(114 + 30 + 75, 300) == Fraction(73, 100)
        # 대칭이고, 자기 자신과는 0 이다.
        assert contrast(crimson, acid) == contrast(acid, crimson)
        assert contrast(acid, acid) == Fraction(0)

    def test_an_axis_the_data_does_not_carry_contributes_nothing(self):
        """못 잰 축은 0 — 없는 값을 기본값으로 지어내지 않는다."""
        colourless = Look(
            look_id="colourless",
            display_name="colourless",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(AttributeValue("Dimmer", 100),),
        )
        other = Look(
            look_id="other",
            display_name="other",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(AttributeValue("Dimmer", 40),),
        )
        # 밝기 축만 값을 낸다: |100-40| / 100. 색도 역할도 0.
        assert contrast(colourless, other) == Fraction(60, 100)


class TestTheSecondCueTurnsAway:
    """양성 팔 ① — 같은 세기의 두 구간이 서로 다른 룩을 받고, 뒤가 더 대비되는 쪽이다."""

    def test_the_drop_takes_the_more_contrasting_of_the_two_remaining_looks(self):
        library = load_library_from_dir()
        acid = library.by_id("edm-drop-acid")
        crimson = library.by_id("edm-drop-crimson")
        beams = library.by_id("edm-drop-beams")

        chosen = _chosen((("Chorus", "0:00"), ("Drop", "0:40")))

        # 두 구간은 같은 세기 대역(4,5)이다 — 대비가 갈랐지 세기가 가른 것이 아니다.
        assert DYNAMICS_TERMS["chorus"] == DYNAMICS_TERMS["drop"] == (4, 5)
        assert chosen == ["edm-drop-acid", "edm-drop-crimson"]
        # 뒤 큐가 **더 대비되는** 쪽이라는 것을 값으로 단정한다.
        assert contrast(acid, crimson) == Fraction(91, 100)
        assert contrast(acid, beams) == Fraction(73, 100)
        assert contrast(acid, crimson) > contrast(acid, beams)

    def test_the_measured_five_sections_are_five_different_stage_pictures(self):
        """정본 §12 항목 2 의 실측 입력 — 뒤 세 구간이 전부 같은 룩이던 자리."""
        chosen = _chosen(_MEASURED_FIVE_SECTIONS)

        assert chosen == [
            "edm-ambient-hold",
            "edm-build-magenta",
            "edm-drop-acid",
            "edm-drop-crimson",
            "edm-drop-acid",  # 후렴 2회차는 §7 대로 되돌아온다
        ]
        assert chosen[3] != chosen[2], "드롭은 앞 후렴과 다른 방이다"


class TestTheRepeatStillReturns:
    """양성 팔 ② — 대비가 §7 을 못 이긴다. 같은 라벨의 회차는 되돌아온다."""

    def test_a_repeated_label_comes_back_even_when_another_look_contrasts_more(self):
        library = load_library_from_dir()
        acid = library.by_id("edm-drop-acid")
        crimson = library.by_id("edm-drop-crimson")

        chosen = _chosen((("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20")))

        assert chosen == ["edm-drop-acid"] * 3
        # 비공허성 — 대비 축만 봤다면 갈아탈 이유가 실재했다.
        assert contrast(acid, crimson) > contrast(acid, acid) == Fraction(0)

    def test_the_returning_look_still_climbs_the_ladder_so_no_cue_is_lost(self):
        """§7.1 — 되돌아온 룩은 회차마다 사다리로 달라지고, 큐는 하나도 안 사라진다."""
        library = load_library_from_dir()
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20")))
        bundle = build_songcue_bundle(
            "Song",
            map_sections_to_looks(sections, library, "edm"),
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert len(bundle.stored_sections) == 3
        assert bundle.skipped == ()
        assert [section.ladder for section in bundle.stored_sections] == [
            (),
            (LADDER_DIMMER_HIT,),
            (LADDER_DIMMER_HIT, LADDER_ZOOM_PINCH),
        ]


class TestTheFabricatedControls:
    """날조 대조군 — 옛 규칙을 되돌리면 실측 결함이 그대로 돌아온다."""

    def test_restoring_the_alphabetical_pick_brings_the_measured_defect_back(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """t360 이전의 정렬을 끼워 넣으면 위 단정들이 **빨개진다**.

        되돌리는 것은 ``(dynamics, look_id)`` 하나 — 정본 §12 항목 2 가 인용한 그
        정렬이다. 이 대조군이 없으면 위 단정이 공허할 수 있다: 룩이 원래부터 달랐을
        수도 있으니까.
        """

        def _alphabetical(candidates, **_kwargs):
            return tuple(sorted(candidates, key=lambda look: (look.dynamics, look.look_id)))

        monkeypatch.setattr(songcue, "sorted_candidates", _alphabetical)

        chosen = _chosen(_MEASURED_FIVE_SECTIONS)

        # 2026-09-12 main `7d78876` 에서 실제로 나온 값 그대로.
        assert chosen[2] == chosen[3] == chosen[4] == "edm-drop-acid"
        # 즉 위 클래스의 성질이 여기서는 거짓이다.
        assert chosen[3] == chosen[2]

    def test_a_band_holding_one_look_degrades_without_pretending_to_have_contrasted(self):
        """후보가 하나뿐이면 고를 것이 없다 — 대비는 **아무것도 못 한다**.

        「대비로 골랐다」를 이 갈래에서 말하지 않기 위해 잰다. 정렬은 항등이고, 어떤
        앞 큐를 줘도 답이 같다.
        """
        only = Look(
            look_id="only-one",
            display_name="only-one",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(
                AttributeValue("Dimmer", 90),
                AttributeValue("ColorRGB_R", 72),
                AttributeValue("ColorRGB_G", 100),
                AttributeValue("ColorRGB_B", 0),
            ),
        )
        library = LookLibrary(schema_version=1, looks=(only,))
        chorus = intent_for_label("Chorus")

        for previous in (None, only):
            assert sorted_candidates((only,), previous=previous, intent=chorus) == (only,)
            assert sorted_candidates((only,), previous=previous, intent=None) == (only,)

        selections = map_sections_to_looks(
            parse_sections((("Chorus", "0:00"), ("Drop", "0:40"))), library, "edm"
        )
        assert [selection.look.look_id for selection in selections] == ["only-one"] * 2
        # 후보가 하나라는 사실이 보고에 그대로 남는다 — 고른 척이 아니라 고를 것이 없었다.
        assert [len(selection.dynamics_matches) for selection in selections] == [1, 1]

        # 대조군의 대조군 — 후보가 둘이면 **같은 호출이** 실제로 순서를 바꾼다. 이것이
        # 없으면 위 항등이 「정렬이 원래 아무것도 안 한다」와 구별되지 않는다.
        rival = Look(
            look_id="aaa-rival",  # 사전순으로는 앞, 대비로는 뒤
            display_name="aaa-rival",
            genre="edm",
            dynamics=5,
            roles=("백라이트",),
            attributes=(
                AttributeValue("Dimmer", 90),
                AttributeValue("ColorRGB_R", 72),
                AttributeValue("ColorRGB_G", 100),
                AttributeValue("ColorRGB_B", 10),
            ),
        )
        pair = (rival, only)
        assert sorted_candidates(pair, previous=None, intent=None)[0].look_id == "aaa-rival"
        assert sorted_candidates(pair, previous=rival, intent=None)[0].look_id == "only-one"


class TestTheOneAccentRuleNowHolds:
    """정본 §6.1 [HARD] — 이 파일이 재기만 했던 그 자리를 카드 t361 이 닫았다.

    §6.1 은 코러스의 순간을 찍는 수단 일곱(밝기 히트 · 무빙 버스트 · 색 스냅 · 백색
    플래시 · 드롭 직전 블랙아웃 · 짧은 스트로브 · 빔·포지션 히트) 중 **한 큐에 하나만**
    쓰라고 못박는데, §7.1 의 사다리 표는 누적을 문면으로 지시한다(「여기까지 그대로 +
    하나 더」). 두 절이 부딪혔고 **감독이 갈래를 정했다**(2026-09-12): 누적하는 축은
    **밝기 하나**이고, 찍는 액센트는 큐당 하나이며 뒤 회차는 갈아탄다.

    그래서 아래가 재는 숫자는 **그대로인데 뜻이 바뀌었다**. 3회차의 ``Dimmer`` 90→95 와
    ``Zoom`` 18→13 은 고치기 전과 같은 값이지만, 밝기가 예외로 확정됐으므로 이제
    **찍는 액센트는 하나**이고 §6.1 을 지킨다. 쌓임이 실제로 일어나던 자리는 4회차이고
    (``Zoom`` 과 ``Iris`` 가 함께 나갔다), 그쪽 실측과 수정은
    ``test_songcue_ladder.py`` 의 ``TestOneMarkingAccentPerCue`` 가 든다.
    """

    #: 찍는 액센트 — 밝기는 여기 없다(감독 결정: 누적 축은 예외).
    _MARKING = (LADDER_ZOOM_PINCH,)

    def test_the_third_occurrence_carries_brightness_and_one_marking_accent(self):
        library = load_library_from_dir()
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20")))
        bundle = build_songcue_bundle(
            "Song",
            map_sections_to_looks(sections, library, "edm"),
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        third = bundle.stored_sections[2]
        base = tuple(third.selection.look.attributes)
        # 두 칸 모두 **실제로 값을 바꾼다** — 없는 축에 대한 공허한 칸이 아니다.
        changed = tuple(rung for rung in third.ladder if escalate_attributes(base, (rung,)) != base)
        assert changed == (LADDER_DIMMER_HIT, LADDER_ZOOM_PINCH)
        # 그중 **찍는** 액센트는 하나다 — 밝기는 누적 축이라 세지 않는다.
        assert sum(1 for rung in changed if rung in self._MARKING) == 1
        assert "Attribute 'Dimmer' At 95" in third.commands[2]
        assert "Attribute 'Zoom' At 13" in third.commands[2]

        # 대조군 — 2회차는 하나뿐이다. 위 단정이 「늘 둘」을 재는 것이 아니라는 증거.
        second = bundle.stored_sections[1]
        base_second = tuple(second.selection.look.attributes)
        assert tuple(
            rung
            for rung in second.ladder
            if escalate_attributes(base_second, (rung,)) != base_second
        ) == (LADDER_DIMMER_HIT,)
