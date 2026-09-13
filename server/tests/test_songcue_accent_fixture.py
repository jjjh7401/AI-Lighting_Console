"""t378 — 사다리의 마지막 두 칸: 블라인더(chorus 3)와 스트로브(앙코르·피날레).

정본 `docs/proposals/song-structure-lighting-standard.md` §7.1 표:

| chorus 3 (마지막) | 여기까지 그대로 + 블라인더 또는 백색 플래시(1~2박) |
| 앙코르·피날레 | 스트로브를 처음 푼다 |

**고치기 전 이유가 만료됐다**(`songcue.py` 의 :data:`LADDER_BLINDER_OR_FLASH`
독스트링) — 카드 t356 이 역할 어휘에 블라인더·스트로브 이름을 열었다. 이 파일은
그 두 칸이 실제로 콘솔 그룹까지 켜지는 것을 잰다.

**이 사다리가 "정확히 chorus 3"을 보장하지 않는다는 것도 함께 잰다** — 값 라인
충돌-회피 구조가 먼저이기 때문이다(:data:`server.looks.songcue._MARKING_ACCENTS`
독스트링). 블라인더는 깊이 3(3회차 이상, 회차 수는 곡마다 갈린다)부터 회전에
들어가고, 스트로브는 ``allow_strobe=True`` 를 준 자리에서만 그보다 더 깊은
회전 칸에서 나온다 — 반복 횟수만으로는 안 뜬다.
"""

from __future__ import annotations

from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    LADDER_BLINDER_OR_FLASH,
    LADDER_STROBE_HIT,
    SongCueLookSelection,
    build_songcue_bundle,
    parse_sections,
)
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_resolver import LXSEQ_RIG

#: 실기 리그(`.moai/specs/SPEC-COPILOT-LXSEQ-001/research.md:28`) 그대로 — 12그룹.
#: BLIND 은 3번째(그룹 번호 3), STROBE 는 4번째(그룹 번호 4).
_LXSEQ_GROUPS: tuple[tuple[int, str], ...] = tuple(
    (index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG)
)
_BLIND_GROUP_NUMBER = 3
_STROBE_GROUP_NUMBER = 4


def _look(
    look_id: str, *, dynamics: int = 5, dimmer: float = 60, roles: tuple[str, ...] = ("백라이트",)
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


def _bundle_of(*pairs, allow_strobe: bool = False, title: str = "Song"):
    return build_songcue_bundle(
        title,
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*_LXSEQ_GROUPS),
        allow_strobe=allow_strobe,
    )


class TestBlinderReachesTheConsole:
    """양성 대조군 — 반복되는 후렴이 결국 블라인더 그룹에 값을 낸다."""

    def test_the_repeated_chorus_lights_the_blind_group(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60)
        bundle = _bundle_of(*((section, look) for section in sections))

        stored = bundle.stored_sections
        assert bundle.skipped == ()
        with_blinder = [s for s in stored if LADDER_BLINDER_OR_FLASH in s.ladder]
        assert with_blinder, "6회 반복이면 블라인더 칸에 닿는다"
        fixture = with_blinder[0].accent_fixture
        assert fixture is not None
        assert fixture.rung == LADDER_BLINDER_OR_FLASH
        assert fixture.groups == (_BLIND_GROUP_NUMBER,)
        assert f"Group {_BLIND_GROUP_NUMBER}" in with_blinder[0].commands
        assert bundle.accent_fixture_sections and with_blinder[0] in bundle.accent_fixture_sections

    def test_the_blinder_value_never_exceeds_the_row_range(self):
        """안전 방향 — §6 chorus·drop 행(80~100%) 밖의 값은 절대 안 나간다.

        연구 문서 19의 `audience_blind_or_strobe` 안전 노트(낮은 값·수동 확인·
        안전 문구 필요)를 이 계층이 지키는 방법은 "자동으로 전 리그 최대치를
        관객에 쏘지 않는다"이다 — 값은 §6 행의 범위 안에서만 오른다.
        """
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60)
        bundle = _bundle_of(*((section, look) for section in sections))

        for section in bundle.stored_sections:
            if section.accent_fixture is None:
                continue
            assert 80 <= section.accent_fixture.dimmer <= 100


class TestBlinderIsANoOpOnTheLookItself:
    """§6.1 [HARD] — 찍는 액센트는 하나. 블라인더는 이 룩의 밝기·색을 안 바꾼다."""

    def test_the_base_look_dimmer_climbs_from_hits_alone(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60)
        bundle = _bundle_of(*((section, look) for section in sections))

        third = bundle.stored_sections[2]
        assert LADDER_BLINDER_OR_FLASH in third.ladder
        # 밝기 히트 2개 + 블라인더(무변화) = 60 + 10 = 70. 블라인더가 이 룩의
        # 값을 바꿨다면 이 숫자가 달라졌을 것이다.
        assert "Attribute 'Dimmer' At 70" in third.commands[2]


class TestStrobeNeedsExplicitPermission:
    """정본 §7.1 — 스트로브는 "클라이맥스 브레이크다운이나 세트 피날레까지 보류".

    이 파일(한 곡)은 몇 번째 곡인지 모른다 — 그래서 반복 횟수만으로는 스트로브가
    안 뜬다. 세션 층이 ``allow_strobe=True`` 로 그 위치를 밝힌 자리에서만 뜬다.
    """

    def test_strobe_never_appears_without_the_flag_even_after_many_repeats(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(8)))
        look = _look("chorus", dimmer=60)
        bundle = _bundle_of(*((section, look) for section in sections))

        assert bundle.skipped == ()
        assert all(LADDER_STROBE_HIT not in s.ladder for s in bundle.stored_sections)
        assert bundle.accent_fixture_sections
        assert all(
            s.accent_fixture.rung != LADDER_STROBE_HIT for s in bundle.accent_fixture_sections
        )

    def test_strobe_unlocks_and_reaches_the_console_when_permitted(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60)
        bundle = _bundle_of(*((section, look) for section in sections), allow_strobe=True)

        assert bundle.skipped == ()
        with_strobe = [s for s in bundle.stored_sections if LADDER_STROBE_HIT in s.ladder]
        assert with_strobe, "허가하면 충분한 반복에서 스트로브가 뜬다"
        fixture = with_strobe[0].accent_fixture
        assert fixture is not None
        assert fixture.rung == LADDER_STROBE_HIT
        assert fixture.groups == (_STROBE_GROUP_NUMBER,)
        assert f"Group {_STROBE_GROUP_NUMBER}" in with_strobe[0].commands

    def test_the_default_is_byte_identical_to_calling_without_the_argument(self):
        """``allow_strobe`` 생략 = ``False`` — 기존 호출은 바이트 동일해야 한다."""
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(4)))
        look = _look("chorus", dimmer=60)
        explicit = _bundle_of(*((section, look) for section in sections), allow_strobe=False)
        implicit = _bundle_of(*((section, look) for section in sections))

        assert explicit.commands == implicit.commands


class TestAccentGroupAbsentMeansNoConsoleCommand:
    """음성 대조군 — 리그에 블라인더·스트로브 그룹이 없으면 칸은 회전해도 무대는 안 켜진다.

    실측(카드 t377 다이어그노시스): 이 저장소가 처음 만난 EDM 실기 리그
    (``server.tests.busking_fixtures.FULL_RIG``)에는 블라인더·스트로브 그룹이
    없다 — 종류 역할 넷(워시·블라인더·스트로브·헤이즈)은 출하 룩 어디에도
    선언되지 않는다(``busking_fixtures`` 머리말).
    """

    def test_no_blind_group_in_the_rig_means_no_accent_command(self):
        from server.tests.busking_fixtures import FULL_RIG

        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60)
        bundle = build_songcue_bundle(
            "Song",
            tuple(
                SongCueLookSelection(
                    section=section, requested_dynamics=(look.dynamics,), look=look
                )
                for section in sections
            ),
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )

        assert bundle.skipped == ()
        assert any(LADDER_BLINDER_OR_FLASH in s.ladder for s in bundle.stored_sections)
        assert bundle.accent_fixture_sections == (), "칸은 회전했지만 리그에 그룹이 없다"
