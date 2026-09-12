"""t363 — 곡 큐에 페이드가 없고 드롭 앞에 어둠이 없다.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` §6(구간별 의도 · 밝기 칸) ·
§8(어둠과 대비 — 자동화가 가장 놓치는 축) · §9(큐 밀도와 타이밍 — 페이드 수치) ·
§12 항목 7(고칠 것: 「어두운 큐의 개념이 없다」).

**고치기 전에 실측한 것**(2026-09-12, main ``980a1db``):
``grep -rn "CueFade" server/looks/songcue.py`` → **0건**. 곡→큐 경로가 낸 모든 큐가 하드
스냅이었고, 드롭 앞에서 밝기를 빼는 규칙은 어디에도 없었다. 6구간 EDM 입력
(Intro·Build·Drop·Breakdown·Drop·Outro)의 실측 값 라인은 20 → **72** → 90 → 25 → 95 → 18
이다 — 드롭 직전이 72 로 이미 밝고, 정본 §8 의 「플래시 앞에 무슨 일이 있었는지가 만든다」가
성립할 자리가 없다.

## 안전 조항 — 이 카드가 지키는 것과 **못 지키는 것**

정본 §8 의 안전 한계는 둘이다. (가) 어떤 룩에서도 비상구·통로·안전 표지가 읽혀야 한다,
(나) 오퍼레이터는 전 회장을 즉시 밝히는 큐 또는 수동 오버라이드를 갖는다.

**먼저 저장소에 이미 있는 것을 쟀다**(2026-09-12, 이 워크트리):

* ``server/safety/`` 는 **콘솔 쓰기 관문**이다 — 블랙리스트·승인·백업·라이브락
  (``server/safety/gate.py`` 독스트링). 무대 밝기와는 무관하고, 이 조항을 덮지 않는다.
* ``grep -rniE "비상|emergency|house.?up|exit sign" server --include='*.py'`` 의 히트는
  전부 블랙아웃 **큐 플래그**(``server/design/song_cue_composer.py`` ·
  ``server/design/lint.py`` L8 블랙아웃 예산)이고, **전 회장을 올리는 경로는 0건**이다.
* ``grep -rn "eye_height|눈높이|house_depth" server`` → 0건. 객석 형상이 없다는 실측은
  ``server/looks/movement.py:20-23`` 이 이미 기록했다.

그러므로 이 카드가 만드는 보장은 **하나**이고 기계로 잰다:

* **지킨다** — 감광 규칙이 내보내는 ``Dimmer`` 는 :data:`DARKNESS_FLOOR` 아래로 안 간다.
  §8 이 허용한 세 형태 중 **짧은 블랙아웃을 일부러 안 만든다**는 뜻이기도 하다. 그리고
  이 규칙은 값을 **내리기만** 한다 — 라이브러리가 스스로 어둡게 저작한 룩을 올리지 않는다.
* **못 지킨다** — 비상구 표지에 실제로 닿는 빛의 양. 광도 모형이 없으므로 lux 주장은
  만들 수 없고, 만들면 그것이 안전 근거로 인용된다.
* **안 만들었다** — 전 회장 즉시 점등 큐. 이 저장소에 그 경로가 없고(위 실측), 역할
  어휘에 하우스·블라인더가 없으며(카드 t356), 없는 리그 개념을 지어내는 것은 이 카드의
  범위가 아니다. **없다는 사실을 여기 적는 것이 오늘 할 수 있는 전부다.**
"""

from __future__ import annotations

import pytest

from server.design.cue_fade import CUE_FADE_KEYWORD, CueFadeError, store_with_fade
from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue, Look
from server.looks.section_fade import (
    FADE_CUT,
    FADE_SLOW,
    FADE_SMOOTH,
    LINE_OUTRO,
    fade_for_label,
)
from server.looks.section_intent import SectionIntent
from server.looks.section_vocab import ROW_BUILD, ROW_CHORUS
from server.looks.songcue import (
    DARKNESS_ALREADY_DARK,
    DARKNESS_FLOOR,
    DARKNESS_NO_PRECEDING_CUE,
    DARKNESS_SAME_SIX_ROW,
    DARKNESS_SIX_ROW_ABSENT,
    SongCueLookSelection,
    build_songcue_bundle,
    darkness_target,
    map_sections_to_looks,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_ladder import _sequences

#: 정본 §12 항목 7 의 실측 입력 — EDM 6구간. 드롭이 둘이고 앞 구간이 각각 다르다
#: (빌드업 뒤 드롭 · 브레이크다운 뒤 드롭), 그래서 감광의 두 갈래가 한 입력에 다 걸린다.
_SIX_SECTIONS = (
    ("Intro", "0:00"),
    ("Build", "0:30"),
    ("Drop", "1:00"),
    ("Breakdown", "1:30"),
    ("Drop", "2:00"),
    ("Outro", "2:30"),
)


def _library_bundle(raw_sections=_SIX_SECTIONS, genre: str = "edm", title: str = "Song"):
    library = load_library_from_dir()
    selections = map_sections_to_looks(parse_sections(raw_sections), library, genre)
    return build_songcue_bundle(
        title,
        selections,
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )


def _dimmer_of(section) -> float:
    """이 큐가 **실제로 콘솔에 낸** 값 라인의 ``Dimmer``.

    선택의 룩이 아니라 명령을 읽는 것이 요점이다 — 감광도 사다리도 값 라인에서만 보인다.
    """
    for command in section.commands:
        if command.startswith("Attribute 'Dimmer' At "):
            return float(command.split("Attribute 'Dimmer' At ")[1].split(" ;")[0])
    raise AssertionError(f"cue {section.cue_number} has no Dimmer line: {section.commands}")


def _store_line(section) -> str:
    return next(command for command in section.commands if command.startswith("Store Sequence "))


def _look(look_id: str, *, dynamics: int, dimmer: float) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", 72),
            AttributeValue("ColorRGB_G", 100),
            AttributeValue("ColorRGB_B", 0),
        ),
    )


def _hand_bundle(*pairs, title: str = "Song"):
    return build_songcue_bundle(
        title,
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )


class TestFadeIsRoutedByTheSectionIntent:
    """정본 §9 — 페이드 값은 둘뿐이고(2~4초 · 0.2초), 갈래는 §6 이 말로 가른다."""

    def test_the_drop_snaps_and_the_outro_fades_slowly(self):
        """카드가 요구한 관계 — **아웃트로의 페이드가 드롭보다 길다.**

        숫자가 아니라 관계를 단언한다: 0.2 와 4 라는 값은 §9 문면에서 왔고, 둘의 대소는
        §6 이 드롭을 「짧게」, 아웃트로를 「느린 페이드 1회」라고 적은 데서 온다.
        """
        bundle = _library_bundle()
        by_label = {section.section.label: section for section in bundle.stored_sections}

        drop = by_label["Drop"].fade
        outro = by_label["Outro"].fade

        assert (drop.line, drop.seconds) == (ROW_CHORUS, FADE_CUT)
        assert (outro.line, outro.seconds) == (LINE_OUTRO, FADE_SLOW)
        assert outro.seconds > drop.seconds
        # 값이 명령 문면까지 닿는다 — 계획만 세우고 안 내보내는 갈래를 막는다.
        assert _store_line(by_label["Drop"]).endswith(f"{CUE_FADE_KEYWORD} 0.2")
        assert _store_line(by_label["Outro"]).endswith(f"{CUE_FADE_KEYWORD} 4")

    def test_every_six_row_label_gets_the_value_its_row_names(self):
        assert fade_for_label("Intro").seconds == FADE_SMOOTH
        assert fade_for_label("Verse").seconds == FADE_SMOOTH
        assert fade_for_label("Build-Up").seconds == FADE_SMOOTH
        assert fade_for_label("Post-Chorus").seconds == FADE_SMOOTH
        assert fade_for_label("Breakdown").seconds == FADE_SMOOTH
        assert fade_for_label("Chorus").seconds == FADE_CUT
        assert fade_for_label("드랍").seconds == FADE_CUT
        assert fade_for_label("코다").seconds == FADE_SLOW

    def test_an_ambiguous_or_unknown_label_gets_no_fade_and_no_suffix(self):
        """줄이 둘 걸리거나 아예 없으면 **지어내지 않는다** — 그 큐는 고치기 전 그대로다."""
        assert fade_for_label("Build to Chorus") is None
        assert fade_for_label("Nonsense") is None

        section = parse_sections((("Nonsense", "0:00"),))[0]
        bundle = _hand_bundle((section, _look("a", dynamics=5, dimmer=90)))
        stored = bundle.stored_sections[0]

        assert stored.fade is None
        assert _store_line(stored) == "Store Sequence 1 Cue 1 'Nonsense'"
        assert CUE_FADE_KEYWORD not in _store_line(stored)


class TestTheFadeGrammarIsTheMeasuredOne:
    """실측된 형태 하나만 나간다 — ``Property 'Fade'`` 는 금지다."""

    def test_the_bundle_never_emits_the_forbidden_property_form(self):
        bundle = _library_bundle()

        assert bundle.commands
        assert all("Property 'Fade'" not in command for command in bundle.commands)

    def test_the_builder_is_the_one_the_repository_already_measured(self):
        base = "Store Sequence 1 Cue 1 'Drop'"

        assert store_with_fade(base, 0.2) == f"{base} CueFade 0.2"
        assert store_with_fade(base, 2.0) == f"{base} CueFade 2"
        # None 은 항등 — 페이드 없는 입력의 명령이 바이트 동일한 이유가 이것이다.
        assert store_with_fade(base, None) == base

    def test_a_negative_fade_is_refused_rather_than_emitted(self):
        with pytest.raises(CueFadeError):
            store_with_fade("Store Sequence 1 Cue 1 'X'", -1)


class TestBrightnessGoesDownBeforeItGoesUp:
    """정본 §8 [HARD] — 드롭 직전에 밝기를 빼는 큐를 넣는다."""

    def test_the_cue_before_the_drop_now_takes_brightness_out(self):
        """양성 대조 — 실측 6구간 입력에서 빌드업 큐의 두 숫자가 갈린다.

        고치기 전 값 라인(2026-09-12, ``980a1db``)::

            Attribute 'Dimmer' At 72 ; Attribute 'ColorRGB_R' At 100 ; \
Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 85 ; Attribute 'Zoom' At 35
            Attribute 'Dimmer' At 90 ; Attribute 'ColorRGB_R' At 72 ; \
Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0 ; Attribute 'Zoom' At 18

        고친 뒤 같은 자리::

            Attribute 'Dimmer' At 40 ; Attribute 'ColorRGB_R' At 100 ; \
Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 85 ; Attribute 'Zoom' At 35
            Attribute 'Dimmer' At 90 ; Attribute 'ColorRGB_R' At 72 ; \
Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0 ; Attribute 'Zoom' At 18

        색도 줌도 그대로다 — 뺀 것은 밝기 하나다.
        """
        bundle = _library_bundle()
        build, drop = bundle.sections[1], bundle.sections[2]

        assert build.section.label == "Build"
        assert drop.section.label == "Drop"

        darkness = build.darkness
        assert darkness is not None
        assert (darkness.before, darkness.after, darkness.row) == (72, 40, ROW_BUILD)
        assert darkness.drop_cue_number == drop.cue_number

        # 관계 셋을 단언한다 — 「큐가 있다」가 아니라 숫자가 어느 쪽으로 움직였는가.
        assert _dimmer_of(build) == darkness.after
        assert _dimmer_of(build) < darkness.before  # 자기 룩보다 어둡다 = 밝기를 뺐다
        assert _dimmer_of(build) < _dimmer_of(drop)  # 그리고 드롭보다 어둡다 = 밸리다
        # 페이드도 같은 큐에서 읽힌다 — 빌드 2초, 드롭 0.2초.
        assert (build.fade.seconds, drop.fade.seconds) == (FADE_SMOOTH, FADE_CUT)
        assert _store_line(build).endswith("CueFade 2")
        assert _store_line(drop).endswith("CueFade 0.2")

    def test_the_colour_and_beam_axes_are_untouched(self):
        """뺀 것은 밝기 하나 — 색 스냅도 줌 변화도 감광의 일이 아니다(정본 §6.1)."""
        bundle = _library_bundle()
        build = bundle.sections[1]
        library_look = build.selection.look
        emitted = next(c for c in build.commands if c.startswith("Attribute 'Dimmer'"))

        for value in library_look.attributes:
            if value.name == "Dimmer":
                continue
            assert f"Attribute '{value.name}' At {value.value:g}" in emitted


class TestTheFabricatedControls:
    """규칙을 빼면 빨개지는가 — 쏘지 않은 그물은 실측된 그물이 아니다."""

    def test_removing_the_rule_turns_the_valley_assertion_red(self, monkeypatch):
        """음성 대조 — 앞 큐가 드롭보다 **밝은** 입력에서 규칙을 거둬 본다.

        고른 입력이 요점이다: 벌스 95 · 드롭 90 은 §8 이 「이미 밝고 바쁜 무대에는 플래시가
        등록될 여지가 없다」고 적은 바로 그 형상이다. 규칙이 있으면 벌스가 §6 verse 행 바닥
        25 로 내려가 밸리가 생기고, 거둬 내면 95 > 90 이라 밸리가 아예 반대로 선다.
        """
        sections = parse_sections((("Verse", "0:00"), ("Drop", "0:30")))
        pairs = (
            (sections[0], _look("bright-verse", dynamics=3, dimmer=95)),
            (sections[1], _look("drop", dynamics=5, dimmer=90)),
        )

        with_rule = _hand_bundle(*pairs)
        verse, drop = with_rule.sections[0], with_rule.sections[1]
        assert _dimmer_of(verse) == 25
        assert _dimmer_of(verse) < _dimmer_of(drop)

        # 규칙만 거둔다 — 나머지 경로(사다리·움직임·충돌 그물)는 그대로 돈다.
        monkeypatch.setattr(
            "server.looks.songcue._pre_drop_positions", lambda ordered: (dict(), ())
        )
        without_rule = _hand_bundle(*pairs)
        control_verse, control_drop = without_rule.sections[0], without_rule.sections[1]

        assert control_verse.darkness is None
        assert _dimmer_of(control_verse) == 95
        # 같은 단언이 여기서 거짓이다 — 그래서 이 단언은 규칙을 재고 있다.
        assert not _dimmer_of(control_verse) < _dimmer_of(control_drop)

    def test_a_drop_as_the_first_section_neither_crashes_nor_invents_a_cue(self):
        """드롭이 곡의 첫 구간이면 — 앞 큐가 없다. 만들지 않고 **이름과 함께 보고한다.**"""
        bundle = _library_bundle((("Drop", "0:00"), ("Breakdown", "0:30"), ("Outro", "1:00")))

        assert [section.cue_number for section in bundle.sections] == [1, 2, 3]
        assert bundle.darkened_sections == ()
        withheld = bundle.withheld_darkness
        assert [(w.cue_number, w.drop_cue_number, w.reason) for w in withheld] == [
            (None, 1, DARKNESS_NO_PRECEDING_CUE)
        ]

    def test_the_three_other_withheld_branches_are_named_rather_than_silent(self):
        """안 한 것은 **네 가지 다른 사실**이고, 하나로 뭉뚱그리지 않는다."""
        already_dark = _library_bundle().withheld_darkness
        assert [w.reason for w in already_dark] == [DARKNESS_ALREADY_DARK]
        assert already_dark[0].cue_number == 4  # Breakdown, 이미 §6 바닥 20

        no_row = _library_bundle((("Outro", "0:00"), ("Drop", "0:30")))
        assert [w.reason for w in no_row.withheld_darkness] == [DARKNESS_SIX_ROW_ABSENT]

        # 후렴 뒤 드롭 — 후렴 자신도 §6 chorus · drop 행이라 **두 사실**이 함께 난다:
        # 첫 큐인 후렴에는 앞 큐가 없고(1번), 그 후렴은 드롭과 같은 행이라 뺄 어둠이 없다(2번).
        same_row = _library_bundle((("Chorus", "0:00"), ("Drop", "0:30")))
        assert [
            (w.cue_number, w.drop_cue_number, w.reason) for w in same_row.withheld_darkness
        ] == [
            (None, 1, DARKNESS_NO_PRECEDING_CUE),
            (1, 2, DARKNESS_SAME_SIX_ROW),
        ]


class TestTheSafetyFloor:
    """정본 §8 안전 한계 — 우리가 내리는 값에 바닥이 있다."""

    def test_the_floor_clamps_a_row_that_would_go_below_it(self):
        """날조 대조군 — 정본에 없는 행을 만들어 바닥을 **쏜다.**

        오늘 §6 표의 가장 낮은 값이 20 이라 실제 여섯 행은 이 걸쇠를 안 건드린다. 안 걸리는
        것과 없는 것은 다르므로, 바닥 0 짜리 행을 지어내 걸쇠가 실제로 무는지 확인한다.
        """
        fabricated = SectionIntent(row="fabricated", brightness=(0, 50))

        assert fabricated.brightness[0] == 0  # 걸쇠가 없었다면 목표가 0(= 블랙아웃)이다
        assert darkness_target(fabricated) == DARKNESS_FLOOR

    def test_every_real_six_row_target_sits_at_or_above_the_floor(self):
        from server.looks.section_intent import SECTION_INTENTS

        for row, brightness, _terms in SECTION_INTENTS:
            intent = SectionIntent(row=row, brightness=brightness)
            assert darkness_target(intent) >= DARKNESS_FLOOR

    def test_the_rule_only_lowers_and_never_emits_a_blackout(self):
        """내리기만 한다 — 어둡게 저작된 룩을 올리지 않고, 0 을 내보내지 않는다."""
        for raw, genre in (
            (_SIX_SECTIONS, "edm"),
            ((("Verse", "0:00"), ("Chorus", "0:30"), ("Verse", "1:00")), "rock"),
            ((("Intro", "0:00"), ("Chorus", "0:30")), "worship"),
            ((("Intro", "0:00"), ("Chorus", "0:30")), "ballad"),
        ):
            bundle = _library_bundle(raw, genre=genre)
            for section in bundle.darkened_sections:
                assert section.darkness.after < section.darkness.before
                assert section.darkness.after >= DARKNESS_FLOOR
            for section in bundle.stored_sections:
                assert _dimmer_of(section) > 0
