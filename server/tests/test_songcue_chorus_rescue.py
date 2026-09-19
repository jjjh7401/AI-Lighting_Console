"""t368 — 코러스 3회차 이상이 사다리 소진으로 통째로 사라진다.

**고치기 전에 실측한 것**(2026-09-12, main `7197b2e` — t366·t367 이후, 재확인:
`befac6b`). `reports/onsite-round-20260912/sweep.py` 로 4개 장르 × 5개 구성을 실제
룩 라이브러리에 태운 전수 훑기에서, 후렴이 세 번 이상 반복되면서 그 후렴이 받는 룩이
밝기 천장(``Dimmer`` 100)에 있는 경우 세 자리가 전부 같은 결함을 보였다:

* edm 「Intro Verse Chorus Verse Chorus Bridge Chorus Chorus Outro」
  → 코러스 3·4회차(7·8번 큐) 둘 다 사라짐
* edm 「Intro Verse Chorus Verse Chorus Verse Chorus Outro」
  → 코러스 3회차(7번 큐) 사라짐
* worship 「Intro Verse Chorus Verse Chorus Bridge Chorus Chorus Outro」
  → 코러스 4회차(8번 큐) 사라짐

원인은 t366 이 고친 것과 **같은 매커니즘**이 드롭이 아닌 자리에서 다시 실측된 것이다
— ``edm-drop-crimson`` 은 ``Dimmer`` 가 이미 천장이고 빔 축이 ``Zoom`` 하나뿐이라
사다리가 오를 수 있는 값이 「기준값 · 줌 좁힌 값」 둘뿐이고, 1·2회차가 그 둘을 다
쓰면 3회차부터는 사다리를 아무리 올려도 이미 쓴 값으로만 돌아온다(``_climb_rungs``
의 액센트는 갈아탈 뿐 누적하지 않으므로). ``worship-glory-climax`` 는 ``Zoom`` ·
``Iris`` 둘 다 있어 값이 셋(기준값·줌·아이리스)이라 4회차에서야 같은 일이 난다.

t366 의 회수(``_rescue_value_line_collisions``)를 **드롭이거나 3회차 이상**인
반복 라벨까지 열어서 고쳤다 — 1·2회차가 그래도 충돌하는 것은 이 룩에 액센트 축이
아예 없다는 뜻이라 성질이 다르고(``test_songcue_ladder.py`` 의
``TestTheLastResortSkipStillFires`` 가 그 갈래를 그대로 지킨다), 3회차부터는
「액센트를 다 썼다」는 뜻이라 드롭과 같은 회수가 맞는다.
"""

from __future__ import annotations

from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    LADDER_DIMMER_YIELD,
    SongCueLookSelection,
    _dimmer_from_values_line,
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

#: 카드 t368 실측 — 후렴 4회, EDM. 다이내믹스는 라벨 어휘가 스스로 정한다(카드
#: t362 이후 ``dynamics`` 필드는 안 읽는다 — ``sweep.py`` 와 동일한 모양).
_EDM_NINE_SECTIONS_FOUR_CHORUS = (
    ("Intro", "0:00"),
    ("Verse", "0:16"),
    ("Chorus", "0:32"),
    ("Verse", "0:48"),
    ("Chorus", "1:04"),
    ("Bridge", "1:20"),
    ("Chorus", "1:36"),
    ("Chorus", "1:52"),
    ("Outro", "2:08"),
)

#: 카드 t368 실측 — 후렴 3회, EDM.
_EDM_EIGHT_SECTIONS_THREE_CHORUS = (
    ("Intro", "0:00"),
    ("Verse", "0:16"),
    ("Chorus", "0:32"),
    ("Verse", "0:48"),
    ("Chorus", "1:04"),
    ("Verse", "1:20"),
    ("Chorus", "1:36"),
    ("Outro", "1:52"),
)

#: 카드 t368 실측 — 후렴 4회, worship(줌·아이리스 둘 다 있는 룩).
_WORSHIP_NINE_SECTIONS_FOUR_CHORUS = _EDM_NINE_SECTIONS_FOUR_CHORUS


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _chorus_sections(bundle):
    return [s for s in bundle.stored_sections if s.section.label == "Chorus"]


class TestTheChorusRescueGeneralizesBeyondDrop:
    """t368 — 3회차 이상의 후렴도 사다리 소진으로 버려지지 않는다."""

    def test_edm_four_chorus_repeats_all_survive_on_the_real_library(self):
        library = load_library_from_dir()
        sections = parse_sections(_EDM_NINE_SECTIONS_FOUR_CHORUS)
        selections = map_sections_to_looks(sections, library, "edm")

        # 비공허성 — 결함이 실린 룩이 여전히 실제로 배정된다. 이 값이 바뀌면(라이브러리·
        # 배정 로직이 갈리면) 이 검사는 t368 이 고친 회수 경로가 아니라 다른 경로를 재는
        # 것이므로, 여기서 먼저 빨개진다.
        chorus_looks = [
            selection.look.look_id
            for selection in selections
            if selection.section.label == "Chorus"
        ]
        assert chorus_looks == ["edm-drop-crimson"] * 4, (
            "네 회차 전부 같은 천장 룩을 받아야 이 결함이 실제로 켜진다"
        )

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == (), "코러스 3·4회차가 사다리 소진으로 버려지면 안 된다"
        assert len(bundle.stored_sections) == 9
        assert len({s.commands[2] for s in bundle.stored_sections}) == 9, (
            "아홉 큐의 값 라인은 서로 달라야 한다"
        )

        chorus = _chorus_sections(bundle)
        assert [c.section.instance for c in chorus] == [1, 2, 3, 4]
        # 룩 정체는 그대로 — 갈아탄 것이 아니라 같은 룩이 네 번 돌아온다(정본 §7).
        assert [c.selection.look.look_id for c in chorus] == ["edm-drop-crimson"] * 4

    def test_edm_three_chorus_repeats_all_survive_on_the_real_library(self):
        library = load_library_from_dir()
        sections = parse_sections(_EDM_EIGHT_SECTIONS_THREE_CHORUS)
        selections = map_sections_to_looks(sections, library, "edm")

        chorus_looks = [
            selection.look.look_id
            for selection in selections
            if selection.section.label == "Chorus"
        ]
        assert chorus_looks == ["edm-drop-crimson"] * 3

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == ()
        assert len(bundle.stored_sections) == 8
        assert len({s.commands[2] for s in bundle.stored_sections}) == 8

        chorus = _chorus_sections(bundle)
        assert [c.section.instance for c in chorus] == [1, 2, 3]
        # 세 번째 회차가 회수(밝기 물러섬)로 되살아난 자리 — LADDER_DIMMER_YIELD 는
        # **상대**(1회차)에 붙지, 되살아난 3회차 자신에는 안 붙는다(정본 §6 「전 리그
        # 최대」와 같은 방향 — 최신 회차가 기준값을 그대로 받는다).
        assert LADDER_DIMMER_YIELD not in chorus[2].ladder
        assert LADDER_DIMMER_YIELD in chorus[0].ladder, "1회차가 물러서서 3회차에 자리를 냈다"

    def test_worship_four_chorus_repeats_all_survive_on_the_real_library(self):
        library = load_library_from_dir()
        sections = parse_sections(_WORSHIP_NINE_SECTIONS_FOUR_CHORUS)
        selections = map_sections_to_looks(sections, library, "worship")

        chorus_looks = [
            selection.look.look_id
            for selection in selections
            if selection.section.label == "Chorus"
        ]
        assert chorus_looks == ["worship-glory-climax"] * 4

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == ()
        assert len(bundle.stored_sections) == 9
        assert len({s.commands[2] for s in bundle.stored_sections}) == 9

        chorus = _chorus_sections(bundle)
        assert [c.section.instance for c in chorus] == [1, 2, 3, 4]
        # worship 룩은 줌·아이리스 둘 다 있어 사다리만으로 「기준값·줌·아이리스」
        # 셋을 낸다 — 그래서 EDM(빔 축 하나)과 달리 3회차까지는 회수가 필요 없고,
        # 회수가 실제로 켜지는 것은 값이 넷째로 필요해지는 4회차뿐이다. 물러서는
        # 쪽은 **상대**(1회차)다 — 정본 §6 「전 리그 최대」와 같은 방향으로, 되살아난
        # 4회차 자신은 기준값을 그대로 받는다(값 라인은 사다리 흔적이 없다).
        #
        # 카드 t378 이 회전에 블라인더를 더하면서 3회차가 깊이 3(둘째 자리, 블라인더)
        # 대신 깊이 4(셋째 자리, 아이리스)까지 오른다 — 블라인더는 이 룩의 값을 안
        # 바꾸므로 깊이 3 은 2회차와 값이 겹쳐(``_MARKING_ACCENTS`` 독스트링) 건너뛴다.
        assert LADDER_DIMMER_YIELD in chorus[0].ladder, "1회차가 물러서서 4회차에 자리를 냈다"
        assert chorus[1].ladder == ("dimmer_hit", "zoom_pinch")
        assert chorus[2].ladder == (
            "dimmer_hit",
            "dimmer_hit",
            "dimmer_hit",
            "iris_pinch",
        )
        # 카드 t382 이후 — 4회차는 값 라인은 여전히 기준값 그대로지만(사다리 흔적
        # 없음), 반복 회차(instance >= 2)로서 찍는 액센트를 하나 받는다
        # (``_ensure_marking_accent``). 값을 안 바꾸는 블라인더가 실린 이유는 줌·
        # 아이리스 좁힘이 각각 2·3회차의 값 라인과 겹쳐 회전이 밀렸기 때문이다
        # (``_ensure_marking_accent`` 의 겹치지 않는 자리 찾기).
        assert chorus[3].ladder == ("blinder_or_flash",), (
            "4회차는 값은 기준값 그대로지만 반복 회차이므로 찍는 액센트를 하나 받는다"
        )


def _chorus_dimmers(bundle) -> list[float | None]:
    return [_dimmer_from_values_line(section.commands[2]) for section in _chorus_sections(bundle)]


class TestRepetitionOrderSurvivesADoubleRescueCascade:
    """t369 — 회수가 두 겹으로 겹치면(카드 t368 이후 실측) 뒤 회차가 앞 회차보다

    어두워질 수 있었다. 정본 §7.1 ``_ladder_start`` 독스트링의 「낮은 칸으로는
    내려가지 않는다: 뒤 회차가 앞 회차보다 약해지면 상승이 아니다」를 후렴 반복에도
    실측으로 못박는다.

    **고치기 전에 실측한 것**(2026-09-13, main `a48aaf0` — t366·t367·t368 이후).
    ``reports/onsite-round-20260912/mono.py`` 로 edm 9구간(후렴 4회)을 태우면
    코러스 밝기 순서가 ``[(1, 95), (2, 100), (3, 90), (4, 100)]`` 로 나와 2회차→3회차
    구간에서 역전했다. 1회차가 물러서서 3회차에게 기준값을 내준 뒤, 4회차가 다시
    그 기준값을 원해 3회차를 물렸는데, 그 두 번째 회수가 1회차가 이미 95를 쥔 줄
    모르고 기준값에서 처음부터 다시 내려가 90에 닿았기 때문이다.
    """

    def test_edm_four_chorus_dimmer_never_decreases_across_repetitions(self):
        """카드의 재현 자리 그대로 — edm 9구간, 후렴 4회."""
        library = load_library_from_dir()
        sections = parse_sections(_EDM_NINE_SECTIONS_FOUR_CHORUS)
        selections = map_sections_to_looks(sections, library, "edm")
        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == ()
        assert len({s.commands[2] for s in bundle.stored_sections}) == 9, (
            "아홉 큐의 값 라인은 여전히 서로 달라야 한다 — 회차를 재배정할 뿐 값 집합은 안 바뀐다"
        )

        dimmers = _chorus_dimmers(bundle)
        assert all(value is not None for value in dimmers)
        assert dimmers == sorted(dimmers), f"뒤 회차가 앞 회차보다 어두우면 안 된다: {dimmers}"

    def test_worship_four_chorus_dimmer_never_decreases_across_repetitions(self):
        """대조군 — worship 은 빔 축이 둘이라 이 카드 이전에도 단조증가였다."""
        library = load_library_from_dir()
        sections = parse_sections(_WORSHIP_NINE_SECTIONS_FOUR_CHORUS)
        selections = map_sections_to_looks(sections, library, "worship")
        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == ()
        dimmers = _chorus_dimmers(bundle)
        assert all(value is not None for value in dimmers)
        assert dimmers == sorted(dimmers), f"뒤 회차가 앞 회차보다 어두우면 안 된다: {dimmers}"

    def test_edm_three_chorus_dimmer_never_decreases_across_repetitions(self):
        """대조군 — edm 후렴 3회는 회수가 한 겹뿐이라 이 카드 이전에도 단조증가였다."""
        library = load_library_from_dir()
        sections = parse_sections(_EDM_EIGHT_SECTIONS_THREE_CHORUS)
        selections = map_sections_to_looks(sections, library, "edm")
        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == ()
        dimmers = _chorus_dimmers(bundle)
        assert all(value is not None for value in dimmers)
        assert dimmers == sorted(dimmers), f"뒤 회차가 앞 회차보다 어두우면 안 된다: {dimmers}"


class TestControlMeasurementForTheCeilingDiagnosis:
    """진단 재도전 — 「어떻게 우리는 이 천장+축개수 가설이 원인이지 증상이 아니라고
    아는가?」

    진짜 가설은 「천장 + 빔 축 하나」가 아니라 **「천장에서 사다리가 낼 수 있는 값의
    개수(=1 + 빔 축 개수)를 반복 횟수가 넘어서면, 넘어선 만큼만 회수가 필요하다」**
    이다. 그래서 이 대조군은 축 개수를 늘리면 손실이 **사라진다**가 아니라 **한 칸
    미뤄진다**는 것을 재야 한다 — 실측 라이브러리에서도 정확히 그랬다(빔 축 하나인
    ``edm-drop-crimson`` 은 3회차부터, 축 둘인 ``worship-glory-climax`` 는 4회차부터
    회수가 켜졌다). 실제 라이브러리를 고치지 않고(카드의 경계 — 라이브러리 편집은
    권고로만 남긴다), 같은 모양의 **합성 룩**으로 이 가설을 직접 쏜다.
    """

    def test_axis_count_sets_exactly_where_the_ladder_alone_stops_covering(self):
        """빔 축이 N 개면 사다리 혼자(회수 없이) 값을 정확히 N+1 개 낸다.

        반복이 N+1 개 이하면 사다리만으로 충분(회수 0회) — 넘어서야 회수가 켜진다.
        """
        one_axis_look = _look("ceiling-one-axis", dimmer=100, zoom=10)
        two_axis_look = _look("ceiling-two-axis", dimmer=100, zoom=10, iris=100)

        # 빔 축 하나 + 반복 둘(=N+1) — 회수 없이 사다리만으로 산다.
        two_reps = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(2)))
        bundle = _bundle_of(*((s, one_axis_look) for s in two_reps))
        assert bundle.skipped == ()
        assert all(LADDER_DIMMER_YIELD not in c.ladder for c in _chorus_sections(bundle)), (
            "빔 축 하나면 반복 둘까지는 사다리 혼자 값을 낸다(기준값 + 줌 하나) — 회수가 필요 없다"
        )

        # 빔 축 하나 + 반복 셋(=N+2) — 이제 사다리가 못 내는 셋째 값이 필요하다.
        three_reps = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(3)))
        bundle = _bundle_of(*((s, one_axis_look) for s in three_reps))
        assert bundle.skipped == (), "회수가 있으면 셋째도 되살아난다(t368)"
        chorus = _chorus_sections(bundle)
        assert LADDER_DIMMER_YIELD in chorus[0].ladder, (
            "회수 없이는 셋째가 진짜로 사라졌을 자리 — 1회차가 물러서야 산다"
        )

        # 빔 축 둘 + 반복 셋(=N+1) — 아이리스 축 하나를 더 주면 그 셋째까지는 사다리
        # 혼자로 다시 충분해진다. 「축을 늘리면 사라진다」가 아니라 「경계가 밀린다」는
        # 것이 이 대조군의 요점이다.
        bundle = _bundle_of(*((s, two_axis_look) for s in three_reps))
        assert bundle.skipped == ()
        assert all(LADDER_DIMMER_YIELD not in c.ladder for c in _chorus_sections(bundle)), (
            "빔 축을 하나 더 주면 반복 셋까지는 사다리 혼자로 충분해진다 — 진단이 "
            "「사라짐 자체를 없앤다」가 아니라 「경계를 한 칸 민다」였다는 증거"
        )

        # 빔 축 둘 + 반복 넷(=N+2) — worship 실측과 같은 자리, 회수가 다시 켜진다.
        four_reps = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(4)))
        bundle = _bundle_of(*((s, two_axis_look) for s in four_reps))
        assert bundle.skipped == ()
        chorus = _chorus_sections(bundle)
        assert LADDER_DIMMER_YIELD in chorus[0].ladder, (
            "축 둘이어도 반복이 그보다 하나 더 많으면(넷) 다시 회수가 켜진다 — worship "
            "9구간 실측과 같은 경계"
        )

    def test_lowering_dimmer_off_the_ceiling_also_removes_the_loss(self):
        """가설의 다른 절반: 축이 하나뿐이어도 천장이 아니면(오를 머리 공간이 있으면)
        사다리 혼자로 네 회차가 다 산다 — 회수가 아예 필요 없다."""
        below_ceiling_look = _look("below-ceiling", dimmer=70, zoom=10)
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(4)))

        bundle = _bundle_of(*((s, below_ceiling_look) for s in sections))

        assert bundle.skipped == ()
        chorus = _chorus_sections(bundle)
        assert all(LADDER_DIMMER_YIELD not in c.ladder for c in chorus), (
            "천장이 아니면 밝기 히트만으로 네 회차가 갈리므로 회수를 안 쓴다"
        )
        assert len({c.commands[2] for c in chorus}) == 4


def _look(
    look_id: str,
    *,
    dynamics: int = 4,
    dimmer: float = 90,
    zoom: float | None = None,
    iris: float | None = None,
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    attributes = [AttributeValue("Dimmer", dimmer)]
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
