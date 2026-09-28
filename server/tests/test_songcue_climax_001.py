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

from server.looks.resolver import resolve_roles
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    LADDER_BLINDER_OR_FLASH,
    SongCueAccentFixture,
    SongCueBundle,
    SongCueLookSelection,
    SongCueSection,
    SongCueSectionBundle,
)
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
