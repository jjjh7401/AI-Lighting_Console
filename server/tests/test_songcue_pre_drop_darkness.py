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

from server.design.cue_fade import CueFadeError, store_with_fade
from server.looks.schema import AttributeValue, Look
from server.looks.section_fade import (
    FADE_CUT,
    FADE_SLOW,
    FADE_SMOOTH,
    fade_for_label,
)
from server.looks.section_intent import SectionIntent
from server.looks.songcue import (
    DARKNESS_FLOOR,
    darkness_target,
)

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


class TestFadeIsRoutedByTheSectionIntent:
    """정본 §9 — 페이드 값은 둘뿐이고(2~4초 · 0.2초), 갈래는 §6 이 말로 가른다."""

    def test_every_six_row_label_gets_the_value_its_row_names(self):
        assert fade_for_label("Intro").seconds == FADE_SMOOTH
        assert fade_for_label("Verse").seconds == FADE_SMOOTH
        assert fade_for_label("Build-Up").seconds == FADE_SMOOTH
        assert fade_for_label("Post-Chorus").seconds == FADE_SMOOTH
        assert fade_for_label("Breakdown").seconds == FADE_SMOOTH
        assert fade_for_label("Chorus").seconds == FADE_CUT
        assert fade_for_label("드랍").seconds == FADE_CUT
        assert fade_for_label("코다").seconds == FADE_SLOW


class TestTheFadeGrammarIsTheMeasuredOne:
    """실측된 형태 하나만 나간다 — ``Property 'Fade'`` 는 금지다."""

    def test_the_builder_is_the_one_the_repository_already_measured(self):
        base = "Store Sequence 1 Cue 1 'Drop'"

        assert store_with_fade(base, 0.2) == f"{base} CueFade 0.2"
        assert store_with_fade(base, 2.0) == f"{base} CueFade 2"
        # None 은 항등 — 페이드 없는 입력의 명령이 바이트 동일한 이유가 이것이다.
        assert store_with_fade(base, None) == base

    def test_a_negative_fade_is_refused_rather_than_emitted(self):
        with pytest.raises(CueFadeError):
            store_with_fade("Store Sequence 1 Cue 1 'X'", -1)


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
