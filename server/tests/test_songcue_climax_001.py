"""SPEC-LDCLIMAX-001 — 코러스 색 스냅 액센트 + 절정 지속시간 상한.

정본 `docs/proposals/song-structure-lighting-standard.md` §6("절정의 지속 시간에
상한이 있다")·§6.1(일곱 액센트 수단 — 색 스냅)·§7(코러스 1의 색은 되돌아와야
한다). 감독 결정(2026-09-20): color_snap 은 기존 찍는 액센트 사다리
(`_MARKING_ACCENTS` — zoom_pinch/blinder_or_flash/iris_pinch[/strobe_hit])와 같은
자격의 정규 칸이다 — 대체도 병행도 아닌 같은 회전의 맨 끝 후보(`plan.md §NC`).

이 파일이 재는 것 둘:

1. **색 스냅** (AC-LDCLIMAX-001~005) — `_marking_accents` 가 `color_snap` 을
   무조건 후보에 포함하되(REQ-001), §7 색 집합 밖(REQ-002)·직전 저장 큐와 같은
   색(REQ-004)이면 무영향으로 걸러진다. 확정되면 페이드가 0으로 강제되고
   (REQ-003), 큐당 액센트 하나 규율(REQ-005)은 그대로 지켜진다.
2. **절정 지속시간 상한** (AC-LDCLIMAX-006~009) — `blinder_or_flash`/`strobe_hit`
   를 실은 큐마다 상한 박수 뒤로 복귀 큐를 끼운다(REQ-006/007), 자연 전환이
   이미 상한을 지키면 끼우지 않는다(REQ-008), BPM 미선언이면 아무 것도 안
   한다(REQ-009).

`disable_color_snap`(REQ-LDCLIMAX-012, AC-LDCLIMAX-010)은 첫 실기 콘솔 검증
세션까지의 임시 안전판이다 — 기본값 거짓(색 스냅은 REQ-001 대로 항상 활성).
"""

from __future__ import annotations

import pytest

import server.looks.songcue as songcue_module
from server.design.cue_fade import store_with_fade
from server.looks.resolver import resolve_roles
from server.looks.schema import AttributeValue, Look
from server.looks.section_fade import SectionFade
from server.looks.songcue import (
    CLIMAX_RETURN_DIMMER_EXHAUSTED,
    DARKNESS_FLOOR,
    LADDER_BLINDER_OR_FLASH,
    LADDER_COLOR_SNAP,
    LADDER_STROBE_HIT,
    SongCueAccentFixture,
    SongCueBundle,
    SongCueLookSelection,
    SongCueSection,
    SongCueSectionBundle,
    build_songcue_bundle,
    parse_sections,
)
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_resolver import LXSEQ_RIG

#: 실기 리그(`test_songcue_accent_fixture.py` 와 같은 자료) — BLIND 그룹 3번이 있다.
#: 절정 지속시간 상한(M3) 시험만 이 리그를 쓴다 — 블라인더 그룹이 실제로 있어야
#: `_climax_cue` 픽스처가 공허하지 않다.
_LXSEQ_GROUPS: tuple[tuple[int, str], ...] = tuple(
    (index + 1, name) for index, (name, _count) in enumerate(LXSEQ_RIG)
)
_BLIND_GROUP_NUMBER = 3


def _look(
    look_id: str,
    *,
    dimmer: float,
    color: tuple[int, int, int] = (72, 100, 0),
    roles: tuple[str, ...] = ("백라이트",),
) -> Look:
    """줌·아이리스가 **없는** 룩 — 색 스냅이 유일한 후보가 되게 한다."""
    r, g, b = color
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="edm",
        dynamics=5,
        roles=roles,
        attributes=(
            AttributeValue("Dimmer", dimmer),
            AttributeValue("ColorRGB_R", r),
            AttributeValue("ColorRGB_G", g),
            AttributeValue("ColorRGB_B", b),
        ),
    )


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }


def _bundle_of(*pairs, allow_strobe: bool = False, disable_color_snap: bool = False, bpm=None):
    """색 스냅 시험용 조립 — ``FULL_RIG``(블라인더 그룹 없음)를 쓴다. 줌·아이리스도
    ``_look`` 이 안 싣는다 — 그래서 이 조합에서 살아남는 찍는 액센트 후보는
    color_snap **하나뿐**이고, 대조군이 공허해지지 않는다."""
    return build_songcue_bundle(
        "Song",
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in pairs
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
        allow_strobe=allow_strobe,
        disable_color_snap=disable_color_snap,
        bpm=bpm,
    )


#: 세 번째 회차부터 찍는 액센트가 강제된다(§7.1 "2회차는 밝기만",
#: ``_ensure_marking_accent`` 독스트링) — 그래서 색 스냅 회전 시험은 코러스
#: **셋**(다리 구간 둘로 갈라)을 쓴다: 코러스1(기준 색 확립) → 다리1(다른 색) →
#: 코러스2(밝기만, 색 스냅 아직 아님) → 다리2(다른 색) → 코러스3(강제 액센트
#: 자리 — 여기서 color_snap 이 회전에 든다).
def _three_choruses_with_bridges(
    *, third_chorus_color: tuple[int, int, int] = (200, 0, 0), **bundle_kwargs
):
    chorus_look = _look("chorus", dimmer=60, color=(200, 0, 0))
    bridge_look = _look("bridge", dimmer=50, color=(0, 0, 200))
    third_look = (
        chorus_look
        if third_chorus_color == (200, 0, 0)
        else _look("chorus-third", dimmer=60, color=third_chorus_color)
    )
    sections = parse_sections(
        (
            ("Chorus", "0:00"),
            ("Bridge", "0:40"),
            ("Chorus", "1:20"),
            ("Bridge", "2:00"),
            ("Chorus", "2:40"),
        )
    )
    chorus_sections = [s for s in sections if s.label == "Chorus"]
    bridge_sections = [s for s in sections if s.label == "Bridge"]
    bundle = _bundle_of(
        (chorus_sections[0], chorus_look),
        (bridge_sections[0], bridge_look),
        (chorus_sections[1], chorus_look),
        (bridge_sections[1], bridge_look),
        (chorus_sections[2], third_look),
        **bundle_kwargs,
    )
    return bundle


class TestColorSnapIsAlwaysACandidate:
    """AC-LDCLIMAX-001 — color_snap 은 무조건 후보이고, 색 변화 없는 골든 픽스처는
    바이트 동일. 색이 실제로 바뀌는 곡에서는 새 결과(color_snap 선택)가 나온다."""

    def test_a_color_invariant_repeat_never_shows_color_snap(self):
        """(a) — 회차 간 색이 항상 같은 픽스처는 color_snap 이 매 회차 무영향으로
        걸러진다(REQ-004) — 스위치가 꺼져서가 아니라 이 필터 때문이다."""
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60)
        bundle = _bundle_of(*((section, look) for section in sections))

        assert bundle.skipped == ()
        assert all(LADDER_COLOR_SNAP not in s.ladder for s in bundle.stored_sections)

    def test_a_returning_color_after_an_interstitial_section_can_win_the_rotation(self):
        """(b) — 코러스 3회차 직전에 다른 색의 다리 구간이 끼면, 코러스 1의 색으로
        돌아올 때 직전 저장 큐(다리)와 색이 달라 color_snap 이 유효 후보가 된다.
        이 SPEC 이전에는 나오지 않던 결과 — REQ-001 이 요구하는 의도된 동작이다.
        """
        bundle = _three_choruses_with_bridges()

        assert bundle.skipped == ()
        chorus_three = next(
            s
            for s in bundle.stored_sections
            if s.section.label == "Chorus" and s.section.instance == 3
        )
        assert LADDER_COLOR_SNAP in chorus_three.ladder


class TestColorSnapStaysWithinTheReturningPalette:
    """AC-LDCLIMAX-002 — §7 색 집합 안에서만 색을 낸다."""

    def test_a_color_outside_chorus_ones_palette_is_filtered_out(self):
        """코러스 1의 색과 다른 색을 강제로 준 3회차는 color_snap 이 후보에서
        빠진다(REQ-002) — 줌·아이리스·블라인더도 이 리그·이 룩에서 전부
        무영향이므로 유효 후보가 하나도 안 남아 유보 기록이 남는다."""
        bundle = _three_choruses_with_bridges(third_chorus_color=(0, 200, 200))

        chorus_three = next(
            s.section
            for s in bundle.sections
            if s.section.label == "Chorus" and s.section.instance == 3
        )
        withheld = [w for w in bundle.withheld_accents if w.section == chorus_three]
        assert withheld, "§7 집합 밖 색은 무영향 칸으로 판정돼 유효 후보가 남지 않는다"


class TestColorSnapForcesFadeToZero:
    """AC-LDCLIMAX-003 — 색 스냅 확정 시 페이드가 0으로 강제된다."""

    def test_the_cue_that_carries_color_snap_has_fade_exactly_zero(self):
        bundle = _three_choruses_with_bridges()

        chorus_three = next(
            s
            for s in bundle.stored_sections
            if s.section.label == "Chorus" and s.section.instance == 3
        )
        assert LADDER_COLOR_SNAP in chorus_three.ladder
        assert chorus_three.fade is not None
        assert chorus_three.fade.seconds == 0.0
        # 색은 색 스냅이 없었을 때와 동일(§7 이 요구하는 코러스 1의 색) — 색
        # 스냅은 색과 페이드만 바꾼다.
        assert "Attribute 'ColorRGB_R' At 200" in chorus_three.commands[2]


class TestColorSnapIsFilteredWhenColorDoesNotChange:
    """AC-LDCLIMAX-004 — 색이 안 바뀌면 색 스냅은 무영향 칸으로 제외된다."""

    def test_no_color_change_from_the_previous_stored_cue_excludes_color_snap(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(4)))
        look = _look("chorus", dimmer=70)
        bundle = _bundle_of(*((section, look) for section in sections))

        assert bundle.skipped == ()
        assert all(LADDER_COLOR_SNAP not in s.ladder for s in bundle.stored_sections)


class TestColorSnapRespectsOneAccentPerCue:
    """AC-LDCLIMAX-005 — 색 스냅도 큐당 액센트 하나 규율을 지킨다."""

    def test_the_color_snap_cue_carries_no_other_marking_accent(self):
        bundle = _three_choruses_with_bridges()

        chorus_three = next(
            s
            for s in bundle.stored_sections
            if s.section.label == "Chorus" and s.section.instance == 3
        )
        assert LADDER_COLOR_SNAP in chorus_three.ladder
        other_marking = {
            rung for rung in chorus_three.ladder if rung not in ("dimmer_hit", LADDER_COLOR_SNAP)
        }
        assert other_marking == set()


class TestDisableColorSnapIsAnOptOutSafetyValve:
    """AC-LDCLIMAX-010 — disable_color_snap=True 는 임시 안전판으로 후보를
    완전히 제거한다."""

    def test_explicit_disable_removes_the_candidate_entirely(self):
        with_color_snap = _three_choruses_with_bridges()
        without_color_snap = _three_choruses_with_bridges(disable_color_snap=True)

        assert any(LADDER_COLOR_SNAP in s.ladder for s in with_color_snap.stored_sections), (
            "기본값(끄지 않음)에서는 color_snap 이 후보로 나타나야 대조군이 공허하지 않다"
        )
        assert all(LADDER_COLOR_SNAP not in s.ladder for s in without_color_snap.stored_sections)
        # 다른 후보(이 픽스처에는 실질적으로 없지만)의 효과 판정은 이 스위치의
        # 영향을 받지 않는다 — 코러스 3회차 전까지의 큐는 두 번들에서 동일하다.
        assert (
            with_color_snap.stored_sections[0].commands
            == without_color_snap.stored_sections[0].commands
        )


# ---------------------------------------------------------------------------
# 절정 지속시간 상한 (REQ-LDCLIMAX-006~011) — 완성된 SongCueBundle 을 받는
# 후처리 패스이므로, 사다리 회전과 무관하게 번들을 직접 지어 잰다.
# ---------------------------------------------------------------------------


def _resolution():
    return resolve_roles(_groups(*_LXSEQ_GROUPS))


def _climax_cue(
    *,
    cue_number: int,
    start_ms: int,
    base_dimmer: float = 60.0,
    stored_dimmer: float = 90.0,
    rung: str = LADDER_BLINDER_OR_FLASH,
    instance: int = 3,
) -> SongCueSectionBundle:
    """블라인더/스트로브를 실은 저장 큐 하나 — 절정 지속시간 상한 패스가 훑을
    입력을 손으로 짓는다(``_apply_climax_duration_cap`` 은 완성된 번들만 본다).

    ``base_dimmer`` 는 ``selection.look`` 자신의(사다리를 오르기 전) 값이고,
    ``stored_dimmer`` 는 이 큐가 실제로 저장한(사다리를 오른 뒤) 값이다 — 둘을
    갈라야 "복귀 큐는 오르기 전 기준 값을 쓴다"(REQ-LDCLIMAX-007)는 시험이
    공허해지지 않는다.
    """
    section = SongCueSection(
        name="Chorus",
        start_ms=start_ms,
        index=cue_number - 1,
        dynamics=None,
        requires_explicit_dynamics=False,
        label="Chorus",
        instance=instance,
        variant="",
    )
    look = _look(f"chorus-{cue_number}", dimmer=base_dimmer)
    selection = SongCueLookSelection(section=section, requested_dynamics=(5,), look=look)
    stored_values = (
        f"Attribute 'Dimmer' At {int(stored_dimmer)} ; Attribute 'ColorRGB_R' At 72 ; "
        "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0"
    )
    group = _BLIND_GROUP_NUMBER if rung == LADDER_BLINDER_OR_FLASH else _BLIND_GROUP_NUMBER + 1
    accent_fixture = SongCueAccentFixture(
        section=section, cue_number=cue_number, rung=rung, groups=(group,), dimmer=90.0
    )
    commands = (
        "ClearAll",
        "Group 11",
        stored_values,
        f"Group {group}",
        "Attribute 'Dimmer' At 90",
        f"Store Sequence 1 Cue {cue_number} 'Chorus {cue_number}'",
        "ClearAll",
    )
    return SongCueSectionBundle(
        section=section,
        cue_number=cue_number,
        cue_name=f"Chorus {cue_number}",
        selection=selection,
        commands=commands,
        ladder=(rung,),
        accent_fixture=accent_fixture,
    )


def _plain_cue(*, cue_number: int, start_ms: int, dimmer: float = 60.0) -> SongCueSectionBundle:
    """절정 칸이 없는 평범한 저장 큐 — "다음 큐" 자리를 채운다."""
    section = SongCueSection(
        name="Verse",
        start_ms=start_ms,
        index=cue_number - 1,
        dynamics=None,
        requires_explicit_dynamics=False,
        label="Verse",
        instance=1,
        variant="",
    )
    look = _look(f"verse-{cue_number}", dimmer=dimmer)
    selection = SongCueLookSelection(section=section, requested_dynamics=(5,), look=look)
    values = (
        f"Attribute 'Dimmer' At {int(dimmer)} ; Attribute 'ColorRGB_R' At 72 ; "
        "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0"
    )
    commands = (
        "ClearAll",
        "Group 11",
        values,
        f"Store Sequence 1 Cue {cue_number} 'Verse {cue_number}'",
        "ClearAll",
    )
    return SongCueSectionBundle(
        section=section,
        cue_number=cue_number,
        cue_name=f"Verse {cue_number}",
        selection=selection,
        commands=commands,
    )


def _bundle(sections: tuple[SongCueSectionBundle, ...]) -> SongCueBundle:
    return SongCueBundle(
        song_title="Climax Song",
        sequence_number=1,
        sequence_name="Climax Song",
        commands=(),
        sections=sections,
    )


class TestClimaxReturnIsInsertedForALongClimax:
    """AC-LDCLIMAX-006/009 — BPM 120, blinder_or_flash 확정 큐 뒤 다음 큐가
    2박(1.0초)보다 한참 뒤(8초)에 오면 복귀 큐가 끼워지고, 삽입은 명시적으로
    보고되며, 기존 큐 값은 불변이다."""

    def test_a_return_cue_lands_at_the_two_beat_cap(self):
        climax = _climax_cue(cue_number=1, start_ms=0, rung=LADDER_BLINDER_OR_FLASH)
        # SPEC-LDRETURN-001 — ``following`` 의 밝기는 climax 의 사다리-오르기-전
        # 기준 값(60, ``_climax_cue`` 의 ``base_dimmer`` 기본값)과 달라야 한다.
        # 둘이 우연히 같으면(둘 다 기본값 60) 복귀 큐 자신의 값 라인이 이
        # ``following`` 큐와 글자 그대로 충돌해 넛지가 개입한다 — 이 시험의
        # 의도(§ AC-LDRETURN-005, "충돌 없는 다음 큐")와 어긋나는 우연한 충돌을
        # 피하려고 명시적으로 다른 값을 준다(``_plain_cue`` 의 기본값 자체는
        # 다른 시험이 의존하므로 바꾸지 않는다).
        following = _plain_cue(cue_number=2, start_ms=8000, dimmer=45.0)
        bundle = _bundle((climax, following))

        result = songcue_module._apply_climax_duration_cap(bundle, bpm=120.0)

        assert len(result.climax_returns) == 1
        record = result.climax_returns[0]
        assert record.rung == LADDER_BLINDER_OR_FLASH
        assert record.cap_beats == 2.0
        assert record.source_cue_number == 1
        assert record.inserted_cue_number == 2
        assert record.inserted_start_ms == 1000

        stored = result.stored_sections
        assert [s.cue_number for s in stored] == [1, 2, 3]
        return_cue = stored[1]
        assert return_cue.section.start_ms == 1000
        assert "Attribute 'Dimmer' At 60" in return_cue.commands[2]  # 사다리를 오르기 전 기준값
        assert not any(f"Group {_BLIND_GROUP_NUMBER}" in c for c in return_cue.commands)

        # REQ-LDCLIMAX-011 — 절정 큐 자신의 값·사다리는 전혀 안 바뀐다. (전체
        # 번들을 재훑는 ``_flatten_commands`` 가 첫 저장 큐에 ``Label Sequence``
        # 줄을 새로 스플라이스하므로, 원본 ``climax.commands`` 와의 비교는 그
        # 한 줄을 뺀 나머지로 한다 — 그 줄 자체는 이 시험의 관심사가 아니다.)
        assert stored[0].ladder == climax.ladder
        assert stored[0].accent_fixture == climax.accent_fixture
        assert tuple(c for c in stored[0].commands if not c.startswith("Label Sequence ")) == (
            climax.commands
        )
        assert stored[0].commands[2] == climax.commands[2]
        # 다음 큐는 번호만 밀린다 — Dimmer 값은 동일.
        assert stored[2].cue_number == 3
        assert "Attribute 'Dimmer' At 45" in stored[2].commands[2]

    def test_a_return_cue_reuses_the_pre_climb_baseline_look_not_the_climax_commands(self):
        """복귀 큐의 값은 절정 큐가 사다리를 오르기 전의 기준 값(즉, ``look``
        자신의 값)과 동일하다 — 절정 큐 자신이 낸 명령(블라인더 그룹 선택 줄 등)
        과는 다르다(design.md §2.1 6번)."""
        climax = _climax_cue(
            cue_number=1, start_ms=0, rung=LADDER_STROBE_HIT, base_dimmer=70.0, stored_dimmer=95.0
        )
        following = _plain_cue(cue_number=2, start_ms=9000)
        bundle = _bundle((climax, following))

        result = songcue_module._apply_climax_duration_cap(bundle, bpm=120.0)

        return_cue = result.stored_sections[1]
        expected_values = (
            f"Attribute 'Dimmer' At {int(climax.selection.look.attributes[0].value)} ; "
            "Attribute 'ColorRGB_R' At 72 ; Attribute 'ColorRGB_G' At 100 ; "
            "Attribute 'ColorRGB_B' At 0"
        )
        assert return_cue.commands[2] == expected_values
        assert return_cue.commands[2] != climax.commands[2], (
            "절정 큐 자신의 명령(블라인더 그룹 선택 줄이 낀 값)과 복귀 큐가 같으면 안 된다"
        )
        # 그룹 선택 줄(commands[1])은 절정 큐와 같다 — 룩 자신이 켠 그룹은 안 바뀐다.
        assert return_cue.commands[1] == climax.commands[1]


class TestNaturalTransitionAlreadyRespectsTheCap:
    """AC-LDCLIMAX-007 — 자연 전환이 상한을 지키면 복귀 큐를 생략한다."""

    def test_a_next_cue_inside_the_cap_window_gets_no_insertion(self):
        """BPM 120, strobe_hit(4박 상한 = 2.0초)이고, 다음 저장 큐가 1.5초
        뒤(상한 이전)에 온다 — 새 복귀 큐가 삽입되지 않는다(no-op)."""
        climax = _climax_cue(cue_number=1, start_ms=0, rung=LADDER_STROBE_HIT)
        following = _plain_cue(cue_number=2, start_ms=1500)
        bundle = _bundle((climax, following))

        result = songcue_module._apply_climax_duration_cap(bundle, bpm=120.0)

        assert result.climax_returns == ()
        assert [s.cue_number for s in result.stored_sections] == [1, 2]
        assert result.sections == bundle.sections
        assert result.commands == bundle.commands

    def test_no_next_cue_at_all_is_treated_the_same_as_arriving_within_the_cap(self):
        """다음 큐가 없어도(마지막 절정 큐가 곡의 마지막 저장 큐가 아닌 한) 삽입은
        "다음 큐가 없거나 상한 이후"일 때만 일어난다 — 여기서는 뒤에 바로 이어지는
        평범한 큐가 상한 안에 있으므로 생략된다는 것을 한 번 더 확인한다."""
        climax = _climax_cue(cue_number=1, start_ms=0, rung=LADDER_BLINDER_OR_FLASH)
        following = _plain_cue(cue_number=2, start_ms=999)
        bundle = _bundle((climax, following))

        result = songcue_module._apply_climax_duration_cap(bundle, bpm=120.0)

        assert result.climax_returns == ()


class TestUndeclaredBpmIsANoOp:
    """AC-LDCLIMAX-008 — BPM 미선언이면 상한이 아예 적용되지 않는다."""

    def test_bpm_none_returns_the_input_untouched(self):
        climax = _climax_cue(cue_number=1, start_ms=0, rung=LADDER_BLINDER_OR_FLASH)
        following = _plain_cue(cue_number=2, start_ms=60_000)
        bundle = _bundle((climax, following))

        result = songcue_module._apply_climax_duration_cap(bundle, bpm=None)

        assert result is bundle
        assert result.climax_returns == ()


class TestClimaxDurationCapIsWiredThroughBuildSongcueBundle:
    """REQ-LDCLIMAX-006~009 — ``build_songcue_bundle(bpm=...)`` 가 실제로 이
    후처리 패스를 부른다(단위 시험이 아니라 공개 진입점을 통한 배선 확인).

    F1(sync-auditor, SPEC-LDCLIMAX-001) 후속 — 이 클래스가 원래 배선 확인에 쓰던
    바로 이 픽스처(6회 반복 동일 룩 코러스)가 F1 결함의 재현 사례임이 드러났다.
    블라인더/스트로브는 룩 자신의 값을 안 바꾸므로(``_rung_applied``) 복귀 큐가
    재방출하는 "사다리를 오르기 전 기준 값"은 반드시 그 룩이 (경쟁 없이) 처음
    저장됐을 때의 값과 글자 그대로 같다 — 같은 룩이 반복되는 픽스처에서는 그
    값을 이미 쥔 큐가 항상 존재한다(1회차). F1 수정으로 ``build_songcue_bundle``
    이 절정 지속시간 상한 패스 뒤에도 ``_guard_bundle_collision`` 을 다시 돌리므로,
    이 조합은 F1~F4 사이에는 ``SongCueBundleError`` 로 거절됐었다.

    SPEC-LDRETURN-001(F4 후속)이 이 결함을 닫는다 — 복귀 큐 자신의 ``Dimmer`` 를
    넛지해 비충돌 값을 찾으므로, 이 조합은 이제 예외 없이 성공하고
    ``climax_returns`` 에 실제로 삽입된다. 이것이 **공개 진입점을 통한 삽입
    성공을 재는 이 저장소 최초의 시험**이다(AC-LDRETURN-001, F4 가 지목한
    커버리지 공백을 직접 닫는다) — ``_apply_climax_duration_cap`` 을 직접 부르지
    않는다.
    """

    def test_bpm_argument_reaches_the_duration_cap_pass(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(6)))
        look = _look("chorus", dimmer=60.0)
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section in sections
        )
        bundle_without_bpm = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*_LXSEQ_GROUPS),
        )

        assert bundle_without_bpm.climax_returns == ()
        with_blinder = [
            s for s in bundle_without_bpm.stored_sections if LADDER_BLINDER_OR_FLASH in s.ladder
        ]
        assert with_blinder, (
            "6회 반복이면 블라인더 칸에 닿는다(test_songcue_accent_fixture.py 와 같은 픽스처) "
            "— bpm 과 무관하게 사다리 회전만으로 정해지므로 bpm=None 픽스처로도 확인된다"
        )

        # AC-LDRETURN-001 — bpm 을 넘기면 상한 패스가 돌아 복귀 큐 삽입을 시도한다.
        # 그 복귀 큐의 기준 값이 1회차의 저장 값과 충돌하지만(F1 재현 조합),
        # SPEC-LDRETURN-001 의 넛지가 비충돌 값을 찾아 예외 없이 성공한다 —
        # ``_apply_climax_duration_cap`` 을 직접 부르지 않는 공개 진입점 그대로다.
        bundle_with_bpm = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*_LXSEQ_GROUPS),
            bpm=120.0,
        )

        assert bundle_with_bpm.climax_returns != (), (
            "AC-LDRETURN-001 — 적어도 1건의 복귀 큐가 실제로 삽입돼야 한다"
        )
        assert bundle_with_bpm.withheld_climax_returns == ()


class TestClimaxReturnCueCollisionIsGuarded:
    """F1(sync-auditor, SPEC-LDCLIMAX-001) — ``build_songcue_bundle`` 은
    ``_apply_climax_duration_cap`` 이 끼운 복귀 큐도 ``_guard_bundle_collision``
    으로 다시 거른다(REQ-LDCLIMAX-007 이 요구하는 "기준 값 재방출"과
    ``run_commands`` 의 dedupe 가 부딪히는 지점).

    재현(auditor): 같은 룩이 반복되는 코러스 3장(bpm 지정) — 3회차가 사다리를
    올라 ``blinder_or_flash`` 에 닿고, 그 복귀 큐가 재방출하는 기준 값은 1회차의
    저장 값과 글자 그대로 같다. F1~F4 사이에는 ``_guard_bundle_collision`` 이
    이 충돌을 정확히 잡아 ``SongCueBundleError`` 로 거절했다 — 배선 자체는
    맞지만 공개 진입점을 통한 성공 삽입 경로가 없었다(F4).

    SPEC-LDRETURN-001 이 F4 를 닫는다 — 복귀 큐 자신의 ``Dimmer`` 를 넛지해
    비충돌 값을 찾는다(REQ-001~002). 넛지할 축이 있으면 성공하고(AC-007,
    아래 첫 시험), 넛지할 데가 없으면(``Dimmer`` 가 이미 :data:`DARKNESS_FLOOR`)
    예외 대신 유보한다(AC-004, 아래 둘째 시험).
    """

    def test_a_repeated_look_climax_return_succeeds_via_nudge(self):
        """AC-LDRETURN-007 — F1→F4 폐쇄 확인. 오늘(이 SPEC 이전) 쓰던 결함
        재현 픽스처(3회 반복, ``Dimmer`` 축 존재, ``bpm=120``)가 이제 예외 없이
        성공하고, 3회차의 복귀 큐가 넛지된 ``Dimmer`` 값으로 삽입된다."""
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(3)))
        look = _look("chorus", dimmer=60.0)
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section in sections
        )

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*_LXSEQ_GROUPS),
            bpm=120.0,
        )

        assert bundle.withheld_climax_returns == ()
        assert len(bundle.climax_returns) == 1
        record = bundle.climax_returns[0]
        assert record.source_cue_number == 3
        return_cue = next(
            s for s in bundle.stored_sections if s.cue_number == record.inserted_cue_number
        )
        # 넛지가 실제로 적용됐다 — 재방출 값은 더는 1회차 기준 값(60)과 같지 않다
        # (REQ-001). 그러나 이 번들 다른 어디에도 이미 나가 있지 않다(REQ-002,
        # 삽입 성공 그 자체가 증거 — 성공했다는 사실이 곧 비충돌 확인이다).
        assert "Attribute 'Dimmer' At 60" not in return_cue.commands[2]
        # AC-LDRETURN-002 — 색은 그대로다(넛지는 Dimmer 축에만 적용된다).
        assert "Attribute 'ColorRGB_R' At 72" in return_cue.commands[2]
        assert "Attribute 'ColorRGB_G' At 100" in return_cue.commands[2]
        assert "Attribute 'ColorRGB_B' At 0" in return_cue.commands[2]
        # AC-LDRETURN-003 — 넛지된 값도 DARKNESS_FLOOR 이상이다.
        nudged_dimmer = float(return_cue.commands[2].split("At ")[1].split(" ;")[0])
        assert nudged_dimmer >= DARKNESS_FLOOR

    def test_a_repeated_look_climax_return_is_withheld_without_dimmer_axis(self):
        """AC-LDRETURN-004 — 넛지가 물러날 데가 없으면(REQ-003) 예외 대신
        유보한다.

        위 시험과 같은 3회 반복 구조를 재구성하되, ``Dimmer`` 를 처음부터
        :data:`DARKNESS_FLOOR` 에 둔다. ``_stepped`` 는 속성이 아예 없을 때와
        이미 한계에 닿았을 때를 같은 방식으로 처리한다 — 입력을 그대로
        돌려준다 — 이므로 이 픽스처는 "``Dimmer`` 축 부재"와 넛지 관점에서
        바이트 동일한 조건을 재현한다. ``Dimmer`` 축을 아예 제거하면
        이 리그·이 픽스처에서는 ``dimmer_hit`` 이 값을 전혀 못 바꿔 3회차
        자체가 사다리를 못 올라(``_climb_rungs`` 의 "hits" 접두사가 유일한
        차별화 수단이다) ``blinder_or_flash`` 에 닿지 못한다 — 이 시험의
        Given 절("blinder_or_flash 사다리 칸에 도달")을 만족시키는 동시에
        REQ-003 의 유보 경로를 실제로 트는 유일한 재구성이 이것이다.
        """
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(3)))
        look = _look("chorus", dimmer=float(DARKNESS_FLOOR))
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section in sections
        )

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*_LXSEQ_GROUPS),
            bpm=120.0,
        )

        assert bundle.climax_returns == ()
        assert len(bundle.withheld_climax_returns) == 1
        withheld = bundle.withheld_climax_returns[0]
        assert withheld.source_cue_number == 3
        assert withheld.rung == LADDER_BLINDER_OR_FLASH
        assert withheld.cap_beats == 2.0
        assert withheld.reason == CLIMAX_RETURN_DIMMER_EXHAUSTED
        assert withheld.detail != ""

    def test_the_guard_still_passes_when_bpm_is_undeclared(self):
        """대조군 — bpm 을 안 주면 상한 패스가 아예 안 돌아 복귀 큐도 안 생기고,
        같은 픽스처가 예전처럼 조용히 성공한다(REQ-LDCLIMAX-009)."""
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(3)))
        look = _look("chorus", dimmer=60.0)
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section in sections
        )

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*_LXSEQ_GROUPS),
        )

        assert bundle.climax_returns == ()
        assert any(LADDER_BLINDER_OR_FLASH in s.ladder for s in bundle.stored_sections)


class TestRepeatedClimaxReturnsDoNotCollideWithEachOther:
    """AC-LDRETURN-008 — 반복 삽입이 서로 충돌하지 않는다.

    절정 칸이 2개 이상이고 둘 다 같은 룩(같은 ``look_id``)을 반복해 두 복귀
    큐가 같은 기준 값을 재방출하려 하면, 두 번째 삽입의 충돌 판정이 첫 번째
    삽입이 만든 값도 포함해서 다시 읽는다(plan.md §B3) — 두 넛지 값은
    서로 달라야 한다.

    전용 픽스처(plan.md M5a) — M5(``TestClimaxDurationCapIsWiredThroughBuildSongcueBundle``,
    AC-001 만 겨냥)의 6회 반복·``Dimmer`` 60 픽스처를 재사용하지 않는다. 반복
    수(7회)와 기준 밝기(65)를 모두 바꿔 독립적으로 구성한다 — M5 는 절정 칸
    개수를 단언·보장하지 않으므로 이 시험의 목적(반복 삽입 간 비충돌)에
    우연히 기댈 수 없다.
    """

    def test_the_second_nudged_return_differs_from_the_first(self):
        sections = parse_sections(tuple(("Chorus", f"{minute}:00") for minute in range(7)))
        look = _look("chorus", dimmer=65.0)
        selections = tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section in sections
        )

        bundle = build_songcue_bundle(
            "Song",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*_LXSEQ_GROUPS),
            bpm=120.0,
        )

        assert bundle.withheld_climax_returns == ()
        assert len(bundle.climax_returns) >= 2, (
            "이 픽스처는 절정 칸이 2개 이상이어야 AC-LDRETURN-008 을 잰다"
        )
        first_record, second_record = bundle.climax_returns[0], bundle.climax_returns[1]
        first_cue = next(
            s for s in bundle.stored_sections if s.cue_number == first_record.inserted_cue_number
        )
        second_cue = next(
            s for s in bundle.stored_sections if s.cue_number == second_record.inserted_cue_number
        )
        assert first_cue.commands[2] != second_cue.commands[2], (
            "AC-LDRETURN-008 — 첫 번째 넛지 값과 두 번째 넛지 값은 서로 달라야 한다 "
            "(§B3 — 두 번째 충돌 판정이 첫 번째 삽입이 만든 값도 다시 읽는다)"
        )


class TestReorderSwapKeepsColorSnapFadeForced:
    """F2(sync-auditor, SPEC-LDCLIMAX-001) — ``_reorder_yields_by_repetition``
    이 (값 라인, 사다리) 묶음을 다른 회차 것으로 바꿔치기해도(그 함수 독스트링:
    ``commands[3:]``·``fade`` 는 건드리지 않는다), color_snap 을 새로 받은 자리는
    ``_finalize_marking_accents`` 를 거치면 페이드가 다시 0으로 강제된다
    (REQ-LDCLIMAX-003).

    재현(auditor): 회차 순서로 밝기가 역순인 두 저장 큐 — 낮은 회차가
    color_snap(페이드 0)을, 높은 회차가 blinder_or_flash(페이드 0.4)를 실었다.
    재배열은 밝기 오름차순으로 (값, 사다리) 묶음을 다시 나누므로 color_snap 은
    낮은 밝기 쪽(원래 blinder_or_flash 였던 큐)으로 옮겨 붙는데, 그 큐 자신의
    ``Store``/``fade`` 는 원래 것(0.4)이 그대로 남는다.
    """

    @staticmethod
    def _cue(*, instance, cue_number, dimmer, ladder, fade_line, fade_seconds):
        section = SongCueSection(
            name="Chorus",
            start_ms=(instance - 1) * 40_000,
            index=instance - 1,
            dynamics=None,
            requires_explicit_dynamics=False,
            label="Chorus",
            instance=instance,
            variant="",
        )
        look = _look("chorus", dimmer=60.0)
        values = (
            f"Attribute 'Dimmer' At {dimmer} ; Attribute 'ColorRGB_R' At 72 ; "
            "Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 0"
        )
        store = store_with_fade(
            f"Store Sequence 1 Cue {cue_number} 'Chorus {cue_number}'", fade_seconds
        )
        commands = ("ClearAll", "Group 11", values, store, "ClearAll")
        selection = SongCueLookSelection(section=section, requested_dynamics=(5,), look=look)
        fade = SectionFade(line=fade_line, seconds=fade_seconds, source="test fixture")
        return SongCueSectionBundle(
            section=section,
            cue_number=cue_number,
            cue_name=f"Chorus {cue_number}",
            selection=selection,
            commands=commands,
            ladder=ladder,
            fade=fade,
        )

    def test_the_swapped_in_color_snap_rung_gets_its_fade_re_forced_to_zero(self):
        # 낮은 회차(2회차)가 color_snap(밝기 90, 페이드 0), 높은 회차(3회차)가
        # blinder_or_flash(밝기 70, 페이드 0.4) — 회차 순으로 밝기가 내려가므로
        # (90 -> 70) 재배열의 방아쇠(단조증가 아님)가 걸린다.
        higher_instance_lower_dimmer = self._cue(
            instance=2,
            cue_number=1,
            dimmer=90,
            ladder=(LADDER_COLOR_SNAP,),
            fade_line=LADDER_COLOR_SNAP,
            fade_seconds=0.0,
        )
        lower_instance_higher_dimmer = self._cue(
            instance=3,
            cue_number=2,
            dimmer=70,
            ladder=(LADDER_BLINDER_OR_FLASH,),
            fade_line=LADDER_BLINDER_OR_FLASH,
            fade_seconds=0.4,
        )
        bundles = [higher_instance_lower_dimmer, lower_instance_higher_dimmer]

        songcue_module._reorder_yields_by_repetition(bundles)

        # 재현 확인 — 재배열 직후에는 color_snap 이 옮겨 붙은 자리가 여전히 옛
        # 페이드(0.4)를 들고 있다(``_reorder_yields_by_repetition`` 은
        # ``commands[3:]``/``fade`` 를 건드리지 않는다, 그 함수 독스트링).
        swapped = next(b for b in bundles if LADDER_COLOR_SNAP in b.ladder)
        assert swapped.fade is not None
        assert swapped.fade.seconds == pytest.approx(0.4)
        assert "CueFade 0.4" in swapped.commands[-2]

        resolution = _resolution()
        emitted: dict[str, tuple[int, int, str]] = {}
        songcue_module._finalize_marking_accents(
            bundles, emitted, resolution, allow_strobe=False, disable_color_snap=False
        )

        fixed = next(b for b in bundles if LADDER_COLOR_SNAP in b.ladder)
        assert fixed.fade is not None
        assert fixed.fade.seconds == 0.0
        store_line = next(c for c in fixed.commands if c.startswith("Store "))
        assert "CueFade 0.4" not in store_line
        assert store_line.endswith("CueFade 0")
