"""t377 — 프론트 필은 룩 선택과 무관하게 항상 채운다.

정본 `docs/proposals/song-structure-lighting-standard.md` §6.2 [HARD]:
"프론트 필은 밝은 워시가 아니라 **부드러운 보정광으로 항상 유지**한다 — 없으면
연주자가 안 보이고 영상이 어둡게 나온다."

**고치기 전에 실측한 것**(감독 실기 관측, 2026-09-12, Sequence 14 'DinoDino'):
verse 큐(``edm-intro-bed`` 등, 역할 ``배경``·``탑``·``무버``)가 KEY·FOH·BACK 을
전혀 안 건드렸다 — 무빙헤드만 돌고 연주자 자리는 어두웠다
(`reports/onsite-round-20260912/realsong-cue-diagnosis.txt`).
"""

from __future__ import annotations

from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    DARKNESS_FLOOR,
    FRONT_FILL_COLOR,
    FRONT_FILL_DIMMER,
    SongCueLookSelection,
    build_songcue_bundle,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups

#: FULL_RIG 그룹 12 는 "FOH Wash" — 위치가 종류를 이기는 규칙으로 프론트 역할에
#: 묶인다(`server/looks/roles.py` 모듈 독스트링). 프론트 필이 실제로 여기로
#: 나간다.
_FRONT_GROUP_NUMBER = 12

#: 프론트를 아예 안 가진 리그 — FULL_RIG 에서 "FOH Wash" 하나만 뺐다.
_RIG_WITHOUT_FRONT: tuple[tuple[int, str], ...] = tuple(
    (number, name) for number, name in FULL_RIG if name != "FOH Wash"
)


def _look(
    look_id: str,
    *,
    dynamics: int = 3,
    dimmer: float = 80,
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=dynamics,
        roles=roles,
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


def _bundle_of(*pairs, groups: tuple[tuple[int, str], ...] = FULL_RIG, title: str = "Song"):
    return build_songcue_bundle(
        title,
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*groups),
    )


class TestFrontFillFillsWhatTheLookOmits:
    """양성 대조군 — 프론트가 없는 룩도 프론트 그룹에 값이 나간다."""

    def test_a_front_less_look_still_lights_the_front_group(self):
        section = parse_sections((("Verse", "0:00"),))[0]
        look = _look("intro-bed", dimmer=45, roles=("배경", "탑", "무버"))
        bundle = _bundle_of((section, look))

        stored = bundle.stored_sections[0]
        assert stored.front_fill is not None
        assert stored.front_fill.groups == (_FRONT_GROUP_NUMBER,)
        assert stored.front_fill.dimmer == FRONT_FILL_DIMMER
        assert f"Group {_FRONT_GROUP_NUMBER}" in stored.commands
        front_index = stored.commands.index(f"Group {_FRONT_GROUP_NUMBER}")
        assert stored.commands[front_index + 1] == (
            f"Attribute 'Dimmer' At {FRONT_FILL_DIMMER} ; "
            f"Attribute 'ColorRGB_R' At {int(FRONT_FILL_COLOR[0].value)} ; "
            f"Attribute 'ColorRGB_G' At {int(FRONT_FILL_COLOR[1].value)} ; "
            f"Attribute 'ColorRGB_B' At {int(FRONT_FILL_COLOR[2].value)}"
        )
        assert bundle.front_filled_sections == (stored,)

    def test_the_floor_is_soft_not_a_bright_wash(self):
        """§6.2 — "밝은 워시가 아니라". 뜬 값은 §6 표 intro 행의 아래끝(20)이다."""
        section = parse_sections((("Chorus", "0:00"),))[0]
        # dynamics=5 룩이라도 프론트가 없으면 프론트 필은 그 밝기를 안 따라간다 —
        # 채우는 값은 항상 20 부터 시작한다(감독 결정과 무관하게 룩과 독립).
        look = _look("drop-no-front", dimmer=100, roles=("백라이트",))
        bundle = _bundle_of((section, look))

        stored = bundle.stored_sections[0]
        assert stored.front_fill.dimmer == DARKNESS_FLOOR == 20


class TestFrontFillRespectsAnAlreadyLitFront:
    """음성 대조군 — 룩이 스스로 프론트를 실었으면 이 층은 아무것도 안 더한다."""

    def test_a_look_that_already_declares_front_is_left_alone(self):
        section = parse_sections((("Chorus", "0:00"),))[0]
        look = _look("drop-crimson", dimmer=100, roles=("백라이트", "프론트"))
        bundle = _bundle_of((section, look))

        stored = bundle.stored_sections[0]
        assert stored.front_fill is None
        # 프론트 그룹은 기준 룩의 Group 줄에 이미 묶여 있다 — 별도 줄이 없다.
        assert stored.commands.count(f"Group {_FRONT_GROUP_NUMBER}") == 0
        assert "Group 11 + 12" in stored.commands or "Group 12 + 11" in stored.commands


class TestFrontFillNeedsAFrontGroup:
    """음성 대조군 — 리그에 프론트로 묶일 그룹이 아예 없으면 채울 대상이 없다."""

    def test_no_front_mapped_group_means_no_fill(self):
        section = parse_sections((("Verse", "0:00"),))[0]
        look = _look("intro-bed", dimmer=45, roles=("배경",))
        bundle = _bundle_of((section, look), groups=_RIG_WITHOUT_FRONT)

        stored = bundle.stored_sections[0]
        assert stored.front_fill is None
        assert not any(c.startswith("Group 12") for c in stored.commands)


class TestFrontFillStaysUniqueAcrossTheWholeSong:
    """카드 t377 의 기계적 제약 — `run_commands` 는 곡 전체를 한 번에 낸다.

    프론트 필이 매 큐 **똑같은** 문자열을 내면 콘솔 쪽 전곡 단위 중복 제거가
    두 번째부터 조용히 버린다(``server.fx.instantiate._PROGRAMMER_STATE_COMMANDS``
    의 면제 대상은 ``Clear``·``ClearAll``·``Group``/``Fixture`` 뿐, 값 라인은
    아니다). 그래서 겹치면 밝기를 한 걸음씩 올려 유일해야 한다.
    """

    def test_two_front_less_cues_climb_instead_of_repeating(self):
        first, second = parse_sections((("Verse", "0:00"), ("Verse", "0:40")))
        look_a = _look("bed-a", dimmer=45, roles=("배경",))
        look_b = _look("bed-b", dimmer=50, roles=("배경",))
        bundle = _bundle_of((first, look_a), (second, look_b))

        stored = bundle.stored_sections
        assert len(stored) == 2
        assert stored[0].front_fill.dimmer == 20
        assert stored[1].front_fill.dimmer == 21, "20 은 이미 첫 큐가 썼다"
        # 전곡 명령에 같은 프론트 필 값 라인이 두 번 나오지 않는다.
        front_value_lines = [
            command for command in bundle.commands if "ColorRGB_R' At 100" in command
        ]
        assert len(set(front_value_lines)) == len(front_value_lines) == 2


class TestFrontFillNeverOutshinesPreDropDarkness:
    """카드 t363 과의 상호작용 — 프론트 필은 §8 이 요구한 어둠보다 밝지 않다.

    프론트 필의 바닥(:data:`FRONT_FILL_DIMMER`)이 감광의 안전 바닥
    (``DARKNESS_FLOOR``)과 **같은 상수**이므로, 드롭 앞에서 감광된 큐의 밝기는
    프론트 필이 더해져도 그 §6 행의 바닥 아래로도 위로도 벗어나지 않는다.
    """

    def test_front_fill_matches_the_darkened_floor_not_above_it(self):
        # Breakdown 행의 바닥은 20(§6). 드롭 앞이라 감광이 걸린다.
        breakdown, drop = parse_sections((("Breakdown", "0:00"), ("Drop", "0:30")))
        breakdown_look = _look("breakdown", dimmer=42, roles=("배경",))
        drop_look = _look("drop", dimmer=100, roles=("백라이트",))
        bundle = _bundle_of((breakdown, breakdown_look), (drop, drop_look))

        darkened = bundle.stored_sections[0]
        assert darkened.darkness is not None
        assert darkened.darkness.after == DARKNESS_FLOOR
        # 프론트 필은 이 큐에서도 같은 바닥에서 시작한다 — 감광이 만든 어둠보다
        # 밝게 튀지 않는다.
        assert darkened.front_fill is not None
        assert darkened.front_fill.dimmer == DARKNESS_FLOOR
