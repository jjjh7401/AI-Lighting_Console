"""Song-structure position cue sheet — mood per section → preset-referenced cues.

SPEC-COPILOT-CUETIME-001 T3: the combination the kickoff names —
``prepare_songcue``'s section/time vocabulary (reused via
:func:`server.looks.songcue.normalise_start_ms`) × the mood→position mapping
(:mod:`server.spatial.position_moods`) × the T2 MIB rule
(:mod:`server.spatial.mib`). The output is a DRAFT cue sheet for one
sequence:

* every position cue stores a PRESET RECALL state (``At Preset 2.<n>``) —
  regenerating the presets at a new venue re-focuses the whole song
  (32_spatial_design.md:167-170);
* a section whose mood names a blackout stores dimmer 0 only, and the next
  reveal onto a new position automatically gains a dark pre-move cue
  (:func:`server.spatial.mib.apply_mib` — measured in M2);
* a section whose mood matches nothing is SKIPPED with a note, consuming its
  cue number (the songcue numbering convention) — the draft never invents a
  position for a mood it cannot name.

The energy-curve principle (narrow→wide, person→space) lives in the mood
table itself: ballad moods land on the tight Vocal DSC focus, chorus/drop on
Cross, finale on the wide Ring In cone.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.spatial.mib import (
    PositionCuePlan,
    apply_mib,
    position_cue_bundle,
    premove_follow_command,
)
from server.spatial.pointing import SpatialPointingError
from server.spatial.position_moods import match_position_mood

__all__ = [
    "PositionSheetSection",
    "PositionSheetResolution",
    "PositionCueSheet",
    "build_position_cue_sheet",
    "required_sheet_labels",
]

#: Blackout vocabulary — an explicit dark section, not a position. Checked
#: BEFORE the mood table so "암전" never scores as a position mood.
_BLACKOUT = re.compile(r"암전|블랙\s*아웃|blackout", re.IGNORECASE)

#: The reveal intensity of every lit cue in the draft. The sheet is a
#: POSITION draft: color/effect intensity design stays with the look
#: pipeline, so lit simply means full.
_LIT_DIMMER = 100.0

_SAFE_NAME = re.compile(r"[A-Za-z0-9 _-]+")


@dataclass(frozen=True)
class PositionSheetSection:
    """One song section of the request: name, start time, mood words.

    ``d_level`` — 카드 t383. 확정 분석(``ConfirmedSongSection``)에서 구간을
    기본값으로 채울 때만 채워진다(``None`` 이 기본): DSP 가 실측한 밝기 단계를
    실어, 무드가 빈 문자열이라 ``resolve_section`` 이 전역 기본값(D3)으로
    떨어지는 대신 실측값이 쓰이게 한다. 지시문에서 직접 구간을 적은 경로는
    이 필드를 채우지 않는다 — 그 경로는 무드 단어로 이미 D 레벨이 정해진다.

    ``role`` — 카드 t393. 오디오 확정 구간은 이름이 중립 ASCII(``S<n>``,
    plan.md §C D5)이고 무드가 비어 있어(DSP 는 밝기만 재고 느낌은 재지 않음),
    ``session.py`` 의 ``_section_role`` 이 이름·무드만 읽으면 항상 ``other`` 로
    떨어진다 — 그 결과 ``_ARC_PALETTE``/``_ARC_FX``/``_ARC_TEXTURE`` 세 표가
    동시에 우회되어 17개 구간이 팔레트 1종·이펙트 1종·텍스처 1종으로
    뭉개졌다(실측). ``d_level`` 과 같은 처방: 명시 필드를 두고, 있으면 그
    값을 최우선으로 쓴다(``_section_role`` 참조). 지시문이 직접 적은 구간은
    이 필드를 채우지 않는다 — 그 경로는 이름/무드 단어로 이미 역할이 갈린다
    (운영자 ``section_names`` 가 여전히 유일한 정본이라는 원칙,
    tools.py:630 의 dynamics 분리와 같은 이유).
    """

    name: str
    start_ms: int
    mood: str
    d_level: int | None = None
    role: str | None = None


@dataclass(frozen=True)
class PositionSheetResolution:
    """How one section resolved — the draft's per-section audit line."""

    section: PositionSheetSection
    cue_no: int
    look_label: str | None = None  # BASIC_POSITION_SEQUENCE name, None = no position
    preset_no: int | None = None
    blackout: bool = False
    skipped_reason: str | None = None
    varied_from: str | None = None  # canonical mood look when an alternative was used


@dataclass(frozen=True)
class PositionCueSheet:
    """The rendered draft: MIB-applied plans and one store bundle per cue."""

    sequence_no: int
    resolutions: tuple[PositionSheetResolution, ...]
    plans: tuple[PositionCuePlan, ...]
    bundles: tuple[tuple[str, ...], ...]


def _cue_name(section: PositionSheetSection, cue_no: int) -> str:
    """An MA3-safe cue name — ASCII subset, no dots (the console strips them).

    A Korean name with a trailing digit ("브레이크1") would otherwise degrade
    to the bare digit (measured live: cues named '1', '2') — a digits-only
    remainder is as meaningless as an empty one, so both fall back.
    """
    kept = "".join(_SAFE_NAME.findall(section.name)).strip()
    if not kept or kept.isdigit():
        return f"Section {cue_no}"
    return kept


def _pick_varied(candidates: Sequence[str], usage: dict[str, tuple[int, int]]) -> str:
    """The mood's look, rotated over its ALTERNATIVES when the sheet repeats.

    A recurring chorus mood should not park the rig on the identical preset
    every time (measured: the metal sheet stored Cross twice and Fan Out
    twice). Deterministic choice among the entry's same-vibe candidates:
    fewest uses so far, then least-recently used, then table order — the
    first occurrence keeps the canonical look and every repeat drifts to a
    fresh alternative before any look comes back.
    """

    def key(pair: tuple[int, str]) -> tuple[int, int, int]:
        order, label = pair
        count, last_index = usage.get(label, (0, -1))
        return (count, last_index, order)

    return min(enumerate(candidates), key=key)[1]


@dataclass(frozen=True)
class _SectionLook:
    """One section's look decision, before any preset number exists."""

    blackout: bool = False
    skipped_reason: str | None = None
    label: str | None = None
    canonical: str | None = None


def _section_looks(sections: Sequence[PositionSheetSection]) -> list[_SectionLook]:
    """Blackout / skip / look label per section — the sheet's ONE selection rule.

    Shared by :func:`required_sheet_labels` and
    :func:`build_position_cue_sheet` so the labels a caller resolves on the
    console are exactly the labels the builder then recalls (t449).
    """
    looks: list[_SectionLook] = []
    usage: dict[str, tuple[int, int]] = {}  # label -> (use count, last section index)
    for index, section in enumerate(sections):
        if _BLACKOUT.search(section.mood) is not None:
            looks.append(_SectionLook(blackout=True))
            continue
        suggestion = match_position_mood(section.mood)
        if suggestion is None:
            looks.append(_SectionLook(skipped_reason="무드 어휘가 포지션 표와 일치하지 않음"))
            continue
        candidates = (suggestion.entry.label, *suggestion.entry.alternatives)
        label = _pick_varied(candidates, usage)
        usage[label] = (usage.get(label, (0, -1))[0] + 1, index)
        looks.append(_SectionLook(label=label, canonical=suggestion.entry.label))
    return looks


def required_sheet_labels(sections: Sequence[PositionSheetSection]) -> tuple[str, ...]:
    """The Position preset labels the sheet for ``sections`` recalls — first-use order.

    카드 t449 — 호출자는 이 라벨들을 콘솔에서 **라벨로** 찾아 실제 슬롯을
    :func:`build_position_cue_sheet` 의 ``preset_numbers`` 로 넘긴다
    (``ChatSession._resolve_position_preset_labels``, t232 와 같은 규율).
    """
    return tuple(dict.fromkeys(look.label for look in _section_looks(sections) if look.label))


def build_position_cue_sheet(
    sections: Sequence[PositionSheetSection],
    *,
    sequence_no: int,
    preset_numbers: Mapping[str, int],
    fids: Sequence[int],
    fade_seconds: float = 3.0,
    move_seconds: float = 1.0,
    lit_dimmer_fade: Sequence[tuple[float, float]] | None = None,
) -> PositionCueSheet:
    """The draft sheet for ``sections`` — resolutions, MIB plans, bundles.

    ``preset_numbers`` maps each label :func:`required_sheet_labels` returns
    for ``sections`` to its RESOLVED Position preset slot — the caller looks
    them up on the console BY LABEL (카드 t449; ``ChatSession.
    _resolve_position_preset_labels``). The old ``preset_start + index``
    arithmetic never checked that the slot actually held that label, so a
    pool whose 10-slot run was taken by other presets silently recalled the
    wrong look. A label with no resolved number is refused, never guessed.

    ``lit_dimmer_fade`` is R4's optional per-section (dimmer %, fade
    seconds) pair, aligned one-to-one with ``sections`` (SPEC-COPILOT-
    SONGSTD-001 M2). The design layer derives each pair from the section's
    own D level and hands the finished numbers DOWN
    (:func:`server.design.position_sheet.build_standard_position_cue_sheet`)
    — this analysis layer stays stdlib + intra-spatial (AC-SPATIAL-013).
    Omitted, behaviour is byte-identical to the pre-R4 contract: every lit
    cue stores the flat ``_LIT_DIMMER`` and the caller's own
    ``fade_seconds``. Blackout cues, the skip rule, MIB pre-moves, the
    alternative-rotation, and the pre-move ``Follow`` trigger never read
    these pairs.
    """
    if not sections:
        raise SpatialPointingError("no song sections to build a sheet from")
    if lit_dimmer_fade is not None and len(lit_dimmer_fade) != len(sections):
        raise SpatialPointingError(
            f"lit_dimmer_fade carries {len(lit_dimmer_fade)} pairs "
            f"for {len(sections)} sections — one pair per section"
        )
    for prev, cur in zip(sections, sections[1:], strict=False):
        if not cur.start_ms > prev.start_ms:
            raise SpatialPointingError(
                f"section start times must strictly increase: "
                f"{prev.name!r} {prev.start_ms}ms then {cur.name!r} {cur.start_ms}ms"
            )
    looks = _section_looks(sections)
    needed = tuple(dict.fromkeys(look.label for look in looks if look.label))
    missing = [label for label in needed if label not in preset_numbers]
    if missing:
        raise SpatialPointingError(
            f"no resolved preset number for {missing!r} — expected one of {needed!r}"
        )
    for label in needed:
        if preset_numbers[label] <= 0:
            raise SpatialPointingError(
                f"preset number {preset_numbers[label]!r} for {label!r} must be positive"
            )

    resolutions: list[PositionSheetResolution] = []
    plans: list[PositionCuePlan] = []
    for index, (section, look) in enumerate(zip(sections, looks, strict=True)):
        cue_no = index + 1  # skipped sections consume numbers (songcue convention)
        if look.blackout:
            resolutions.append(
                PositionSheetResolution(section=section, cue_no=cue_no, blackout=True)
            )
            plans.append(
                PositionCuePlan(
                    cue_no=cue_no,
                    name=_cue_name(section, cue_no),
                    dimmer=0.0,
                    fade_seconds=fade_seconds,
                )
            )
            continue
        if look.label is None:
            resolutions.append(
                PositionSheetResolution(
                    section=section,
                    cue_no=cue_no,
                    skipped_reason=look.skipped_reason,
                )
            )
            continue
        label = look.label
        preset_no = preset_numbers[label]
        resolutions.append(
            PositionSheetResolution(
                section=section,
                cue_no=cue_no,
                look_label=label,
                preset_no=preset_no,
                varied_from=(look.canonical if label != look.canonical else None),
            )
        )
        if lit_dimmer_fade is None:
            cue_dimmer, cue_fade = _LIT_DIMMER, fade_seconds
        else:
            cue_dimmer, cue_fade = lit_dimmer_fade[index]
        plans.append(
            PositionCuePlan(
                cue_no=cue_no,
                name=_cue_name(section, cue_no),
                preset_no=preset_no,
                dimmer=cue_dimmer,
                fade_seconds=cue_fade,
            )
        )

    if not plans:
        raise SpatialPointingError("no section resolved to a cue — nothing to store")
    mib_plans = apply_mib(plans, move_seconds=move_seconds)
    bundles = tuple(
        position_cue_bundle(sequence_no, plan, fids)
        + ((premove_follow_command(sequence_no, plan),) if plan.premove else ())
        for plan in mib_plans
    )
    return PositionCueSheet(
        sequence_no=sequence_no,
        resolutions=tuple(resolutions),
        plans=mib_plans,
        bundles=bundles,
    )
