"""Director interview — the five-question Socratic layer that turns an
automatic proposal into a director-confirmed decision (SPEC-COPILOT-
SONGSTD-001 M2, REQ R1c, docs/proposals/song-lighting-design-standard.md
§2d).

M1's :mod:`server.design.profile` already ships the hook this module fills:
:class:`~server.design.profile.DirectorOverride` and
:func:`~server.design.profile.resolve_section`'s ``director_intent`` priority
rung are documented there as "M1's hook for the M2 연출 인터뷰 (interview.py,
R1c), not that interview itself." This module IS that interview.

Five closed questions (표준 §2d table), asked **one at a time** (DI2), each
carrying exactly three profile/rig-derived proposals (a recommendation +
two alternatives) plus free text on equal footing (DI3):

* **Q1 CONCEPT** — 전체 컨셉/분위기. Proposals are
  :data:`~server.design.profile.CONCEPT_SEED_TABLE`'s three seeds.
* **Q2 PALETTE** — 컬러 팔레트(베이스+액센트). Proposals rank the confirmed
  Q1 concept's color tendency ahead of the genre default ahead of the
  unified mood table's colors ahead of the global default (DI1's priority
  order, mirrored for suggestion-ranking rather than resolution).
* **Q3 CLIMAX** — 클라이맥스(피크 구간·터뜨릴 방식). Proposals are the
  highest-D-level rows of :data:`~server.design.profile.UNIFIED_MOOD_TABLE`,
  with the confirmed concept's position bias (if any) promoted to the
  recommendation.
* **Q4 SPATIAL STORY** — 공간 스토리(포지션 진행 서사). Proposals are whole
  position-sequence permutations: the concept-biased order (when a concept
  is confirmed), the §3 E3 canonical "좁음→넓음" ascending-D order, its
  reverse, and the unified mood table's own declaration order — the first
  three of that priority list, deduped.
* **Q5 TEXTURE** — 질감(스냅/페이드 성향·이펙트 밀도). Proposals come from
  §7's per-genre 질감 column (mirrored locally as :data:`_GENRE_TEXTURE_TABLE`
  — profile.py's own ``GENRE_DEFAULT_TABLE`` deliberately does not carry this
  column; see its docstring) and a BPM-tempo-band note. Per the M2
    feasibility read (docs/reports/2026-08-14-songstd-m2-feasibility.md
    Finding B), texture stays out of
    :class:`~server.design.profile.DirectorOverride`; it lands as the raw
    audit value plus a typed, non-console decision projection.

**DI1 — 감독 답변이 최우선.** Q3/Q4 answers resolve into a
:class:`~server.design.profile.DirectorOverride` (Q3: d_level + color +
positions; Q4: position_candidates only) that a caller feeds to
:func:`~server.design.profile.resolve_section` for whichever section(s) the
answer applies to — this module does not itself know which sections exist
(that mapping is session-layer wiring, out of this pure engine's scope; see
the feasibility report's Finding B). Q1/Q2 answers instead fold directly into
the :class:`~server.design.profile.MusicProfile` fed to later questions
(``concept`` / ``palette``), which is exactly how **DI2** ("Q1의 답이 Q2~Q4의
제안을 재유도") is satisfied — no bespoke re-derivation function, just
re-invoking the same candidate builders against an updated profile.

**DI3 — 자유 입력은 1급.** Every step accepts free text on the same footing
as picking one of the three options: the resolved *value* has the identical
shape either way (see :class:`AnswerRecord`). Where a step's free text has a
known vocabulary to check against (Q2's color tokens; Q3/Q4 via
:func:`~server.design.profile.resolve_section`'s own unified-mood matcher)
and the parser cannot ground the text in it, this module returns
:class:`UnresolvedAnswer` instead of guessing — the caller must re-present
the same step's card. Q1/Q2's open-vocabulary steps have nothing to reject
free text against and always resolve it verbatim.

**DI4 — 무응답 = 미확정 초안.** An empty/``None`` submission still advances
the interview (unlike an unresolved free-text answer, which does not) but
records ``confirmed=False`` against the recommended option's value — the
audit trail can always tell an actual director decision from an
undisclosed auto-draft.

**DI5 — 재인터뷰 가능.** :meth:`DirectorInterview.restart_from` drops the
given step and everything after it, preserving every earlier answer intact.

**DI6 — 답변은 감사 가능.** :meth:`DirectorInterview.audit_trail` returns
every step's :class:`AnswerRecord` (proposals shown, what was chosen, free
text if any, confirmed or drafted, and any typed director-decision projection)
in Q1→Q5 order.

Pure module — no console handle, no port, no transport import (matching
``profile.py``/``rig.py``/``energy.py``'s stated purity constraint). Reads
:class:`~server.design.profile.MusicProfile`,
:class:`~server.design.profile.DirectorOverride`,
:func:`~server.design.profile.resolve_section`, and
:class:`~server.design.rig.RigProfile`; never mutates them and never edits
their source modules. Wiring this into an actual question-card channel (the
``_ask_one`` blocking-ask idiom already used elsewhere in ``session.py``) is
session-layer work, deliberately out of this module's scope.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from typing import Literal

from server.design.profile import (
    CONCEPT_SEED_TABLE,
    GENRE_DEFAULT_TABLE,
    GLOBAL_DEFAULT_COLOR_TENDENCY,
    UNIFIED_MOOD_TABLE,
    ConceptSeed,
    DirectorOverride,
    GenreDefault,
    MoodEntry,
    MusicProfile,
    SectionMoodResolution,
    UnresolvedMood,
    resolve_section,
)
from server.design.rig import RigProfile

__all__ = [
    "GLOBAL_DEFAULT_TEXTURE",
    "Q1_CONCEPT",
    "Q2_PALETTE",
    "Q3_CLIMAX",
    "Q4_SPATIAL_STORY",
    "Q5_TEXTURE",
    "SOURCE_AUTO_DRAFT",
    "SOURCE_FREE_TEXT",
    "SOURCE_OPTION",
    "SOURCE_PRE_SPECIFIED",
    "STEP_ORDER",
    "AnswerRecord",
    "ClimaxDirection",
    "DirectorDecisionProjection",
    "DirectorInterview",
    "InterviewError",
    "QuestionCard",
    "QuestionOption",
    "SpatialStoryDirection",
    "TextureDirection",
    "UnresolvedAnswer",
    "build_question",
]


class InterviewError(ValueError):
    """An interview input is malformed — an unknown step, a card that
    failed to carry exactly 3 options, or a submission after the interview
    is already complete."""


#: The five closed questions (표준 §2d table), in the fixed order DI2 asks
#: them ("한 번에 하나씩").
Q1_CONCEPT = "Q1_CONCEPT"
Q2_PALETTE = "Q2_PALETTE"
Q3_CLIMAX = "Q3_CLIMAX"
Q4_SPATIAL_STORY = "Q4_SPATIAL_STORY"
Q5_TEXTURE = "Q5_TEXTURE"

STEP_ORDER: tuple[str, ...] = (Q1_CONCEPT, Q2_PALETTE, Q3_CLIMAX, Q4_SPATIAL_STORY, Q5_TEXTURE)

#: Audit-trail source tags (DI6) — where an :class:`AnswerRecord`'s value
#: actually came from.
SOURCE_OPTION = "option"
SOURCE_FREE_TEXT = "free_text"
SOURCE_PRE_SPECIFIED = "pre_specified"
SOURCE_AUTO_DRAFT = "auto_draft"

#: The neutral texture used only when neither a genre nor a BPM tempo band
#: supplies one — mirrors ``profile.py``'s ``GLOBAL_DEFAULT_COLOR_TENDENCY``
#: in spirit (an explicit, disclosed placeholder, never a guess).
GLOBAL_DEFAULT_TEXTURE = "중간"

#: BPM bands for Q5's tempo-derived texture note (표준 §2d Q5: "장르 질감+
#: BPM"). Explicit, disclosed thresholds — the same discipline
#: ``profile.DEFAULT_BPM`` uses for its own fallback.
FAST_TEMPO_BPM_THRESHOLD = 140.0
SLOW_TEMPO_BPM_THRESHOLD = 90.0

PositionWidthTier = Literal["narrow", "medium", "wide", "max"]
SpatialProgression = Literal["narrow_to_wide", "wide_to_narrow", "mixed"]
SnapFadeDirection = Literal["snap", "fade", "balanced"]
FxDensityDirection = Literal["low", "medium", "high"]
BpmSpeedDirection = Literal["slow", "medium", "fast"]


@dataclass(frozen=True)
class _TextureSeed:
    """One genre's texture note (표준 §7 질감 column). ``GENRE_DEFAULT_TABLE``
    in profile.py deliberately does not carry this column (its own
    docstring: "texture/feature columns are R2/energy.py territory, not this
    module's") — this module's Q5 needs it, so it is mirrored here, grounded
    verbatim in the same §7 table's 질감 column, keyed on the identical
    genre names ``GENRE_DEFAULT_TABLE`` uses."""

    genre: str
    texture: str
    reason: str


#: §7 table, 질감 column verbatim per row — same five genres as
#: ``GENRE_DEFAULT_TABLE``.
_GENRE_TEXTURE_TABLE: tuple[_TextureSeed, ...] = (
    _TextureSeed(
        genre="메탈", texture="스냅 위주, 더블킥×디머 체이스 동기", reason="표준 §7: 메탈 질감."
    ),
    _TextureSeed(genre="록", texture="히트 정밀 타이밍", reason="표준 §7: 록 질감."),
    _TextureSeed(genre="edm", texture="하드 스냅, 기하학", reason="표준 §7: EDM 질감."),
    _TextureSeed(genre="발라드", texture="긴 페이드(5s+)", reason="표준 §7: 발라드 질감."),
    _TextureSeed(genre="팝", texture="중간", reason="표준 §7: 팝 질감."),
)


@dataclass(frozen=True)
class ClimaxDirection:
    peak_positions: tuple[str, ...]
    accent_color: str | None
    d_level: int | None


@dataclass(frozen=True)
class SpatialStoryDirection:
    positions: tuple[str, ...]
    width_tiers: tuple[PositionWidthTier, ...]
    progression: SpatialProgression


@dataclass(frozen=True)
class TextureDirection:
    snap_fade: SnapFadeDirection
    fx_density: FxDensityDirection
    bpm_speed: BpmSpeedDirection
    bpm_is_default: bool


@dataclass(frozen=True)
class DirectorDecisionProjection:
    step: str
    climax: ClimaxDirection | None = None
    spatial_story: SpatialStoryDirection | None = None
    texture: TextureDirection | None = None


@dataclass(frozen=True)
class QuestionOption:
    """One of a card's exactly-3 proposals (index 0 is the recommendation).
    ``value`` is the normalized answer this option resolves to if chosen —
    a plain ``str`` for Q1/Q2/Q5, a
    :class:`~server.design.profile.DirectorOverride` for Q3/Q4 — the same
    shape free text resolves to for that step (DI3's equal-footing
    guarantee)."""

    label: str
    description: str
    value: object


@dataclass(frozen=True)
class QuestionCard:
    """One interview step's question card. Mechanically enforces "exactly
    3 proposals" (표준 §2d: "제안 3개") rather than merely documenting it."""

    step: str
    prompt: str
    why: str
    options: tuple[QuestionOption, ...]

    def __post_init__(self) -> None:
        if len(self.options) != 3:
            raise InterviewError(
                f"a question card must carry exactly 3 options, got {len(self.options)}"
            )


@dataclass(frozen=True)
class AnswerRecord:
    """One step's audit entry (DI6) — what was proposed, what was actually
    chosen (an option, free text, both absent on an auto-draft), and
    whether the director confirmed it at all (DI4)."""

    step: str
    proposals: tuple[QuestionOption, ...]
    choice: QuestionOption | None
    free_text: str | None
    value: object
    confirmed: bool
    source: str
    director_decision: DirectorDecisionProjection | None = None


@dataclass(frozen=True)
class UnresolvedAnswer:
    """A submitted free-text answer this step's parser could not interpret
    (DI3: "해석 불가면 되묻는다") — the caller must re-present the SAME
    step's card rather than guess. Returning this NEVER advances interview
    progress (contrast :data:`SOURCE_AUTO_DRAFT`, which always does)."""

    step: str
    free_text: str
    reason: str


@dataclass(frozen=True)
class _ParseFailure:
    """Internal free-text parse failure, wrapped into :class:`UnresolvedAnswer`
    once the calling step is known."""

    reason: str


def _rig_note(rig: RigProfile) -> str:
    return f"현재 장비 {rig.inventory.fixture_count}대를 기준으로 만든 제안이에요"


def _find_concept_seed(concept: str | None) -> ConceptSeed | None:
    if not concept:
        return None
    folded = concept.strip().casefold()
    for seed in CONCEPT_SEED_TABLE:
        if seed.concept.casefold() == folded:
            return seed
    return None


def _find_genre_default(genre: str | None) -> GenreDefault | None:
    if not genre:
        return None
    folded = genre.strip().casefold()
    for entry in GENRE_DEFAULT_TABLE:
        if entry.genre.casefold() == folded:
            return entry
    return None


def _find_genre_texture(genre: str | None) -> _TextureSeed | None:
    if not genre:
        return None
    folded = genre.strip().casefold()
    for entry in _GENRE_TEXTURE_TABLE:
        if entry.genre.casefold() == folded:
            return entry
    return None


def _tempo_band_texture(profile: MusicProfile) -> tuple[str, str]:
    bpm = profile.effective_bpm
    if bpm >= FAST_TEMPO_BPM_THRESHOLD:
        band, texture = "빠른 템포", "스냅 위주 (빠른 템포)"
    elif bpm < SLOW_TEMPO_BPM_THRESHOLD:
        band, texture = "느린 템포", "긴 페이드 성향 (느린 템포)"
    else:
        band, texture = "중간 템포", GLOBAL_DEFAULT_TEXTURE
    disclosed = " — BPM 미지정, 120 기본값" if profile.bpm_is_default else ""
    return texture, f"BPM {bpm:g} ({band}){disclosed}"


def _bpm_speed_direction(profile: MusicProfile) -> BpmSpeedDirection:
    bpm = profile.effective_bpm
    if bpm >= FAST_TEMPO_BPM_THRESHOLD:
        return "fast"
    if bpm < SLOW_TEMPO_BPM_THRESHOLD:
        return "slow"
    return "medium"


def _position_width_tier(d_level: int) -> PositionWidthTier:
    if d_level <= 2:
        return "narrow"
    if d_level == 3:
        return "medium"
    if d_level == 4:
        return "wide"
    return "max"


_POSITION_WIDTH_BY_LABEL: dict[str, PositionWidthTier] = {
    entry.label: _position_width_tier(entry.d_level) for entry in UNIFIED_MOOD_TABLE
}

_POSITION_WIDTH_ORDER: dict[PositionWidthTier, int] = {
    "narrow": 0,
    "medium": 1,
    "wide": 2,
    "max": 3,
}


def _spatial_progression(width_tiers: tuple[PositionWidthTier, ...]) -> SpatialProgression:
    ordinal = [_POSITION_WIDTH_ORDER[tier] for tier in width_tiers]
    if all(left <= right for left, right in zip(ordinal, ordinal[1:], strict=False)):
        return "narrow_to_wide"
    if all(left >= right for left, right in zip(ordinal, ordinal[1:], strict=False)):
        return "wide_to_narrow"
    return "mixed"


_SNAP_TEXTURE_TOKENS = (
    "스냅",
    "하드",
    "히트",
    "정밀",
    "더블킥",
    "체이스",
    "펄스",
    "기하학",
    "snap",
    "hit",
    "pulse",
    "chase",
)

_FADE_TEXTURE_TOKENS = ("페이드", "부드", "느린", "fade", "soft", "slow")


def _snap_fade_direction(texture: str) -> SnapFadeDirection:
    folded = texture.casefold()
    if any(token in folded for token in _SNAP_TEXTURE_TOKENS):
        return "snap"
    if any(token in folded for token in _FADE_TEXTURE_TOKENS):
        return "fade"
    return "balanced"


def _fx_density_direction(snap_fade: SnapFadeDirection) -> FxDensityDirection:
    if snap_fade == "snap":
        return "high"
    if snap_fade == "fade":
        return "low"
    return "medium"


def _project_director_decision(
    step: str, value: object, profile: MusicProfile
) -> DirectorDecisionProjection | None:
    if step == Q3_CLIMAX and isinstance(value, DirectorOverride):
        return DirectorDecisionProjection(
            step=step,
            climax=ClimaxDirection(
                peak_positions=value.position_candidates or (),
                accent_color=value.color_tendency,
                d_level=value.d_level,
            ),
        )
    if step == Q4_SPATIAL_STORY and isinstance(value, DirectorOverride):
        positions = value.position_candidates or ()
        width_tiers = tuple(_POSITION_WIDTH_BY_LABEL[position] for position in positions)
        return DirectorDecisionProjection(
            step=step,
            spatial_story=SpatialStoryDirection(
                positions=positions,
                width_tiers=width_tiers,
                progression=_spatial_progression(width_tiers),
            ),
        )
    if step == Q5_TEXTURE and isinstance(value, str):
        snap_fade = _snap_fade_direction(value)
        return DirectorDecisionProjection(
            step=step,
            texture=TextureDirection(
                snap_fade=snap_fade,
                fx_density=_fx_density_direction(snap_fade),
                bpm_speed=_bpm_speed_direction(profile),
                bpm_is_default=profile.bpm_is_default,
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Q1 — 전체 컨셉/분위기
# ---------------------------------------------------------------------------


def _build_q1(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    seeds = list(CONCEPT_SEED_TABLE)
    current = _find_concept_seed(profile.concept)
    if current is not None:
        seeds.sort(key=lambda seed: seed is not current)
    options = tuple(
        QuestionOption(
            label=seed.concept,
            description=(
                f"{seed.color_tendency} 색으로 무대의 기본 분위기를 만들어요. ({_rig_note(rig)})"
            ),
            value=seed.concept,
        )
        for seed in seeds[:3]
    )
    return QuestionCard(
        step=Q1_CONCEPT,
        prompt="공연 전체가 어떤 느낌이면 좋겠어요?",
        why="정답은 없어요. 마음에 드는 단어나 문장으로 편하게 말해 주세요.",
        options=options,
    )


# ---------------------------------------------------------------------------
# Q2 — 컬러 팔레트 (베이스+액센트)
# ---------------------------------------------------------------------------


def _q2_color_candidates(profile: MusicProfile) -> list[tuple[str, str, str]]:
    """Ranked ``(label, description, color_tendency)`` candidates."""
    candidates: list[tuple[str, str, str]] = []
    seed = _find_concept_seed(profile.concept)
    if seed is not None:
        candidates.append(
            (
                f"{seed.concept} 색 조합",
                f"{seed.color_tendency} 색으로 {seed.concept} 느낌을 살려요.",
                seed.color_tendency,
            )
        )
    genre = _find_genre_default(profile.genre)
    if genre is not None:
        candidates.append(
            (
                f"{genre.genre} 느낌 색 조합",
                f"{genre.color_tendency} 색을 중심으로 장르의 분위기를 살려요.",
                genre.color_tendency,
            )
        )
    for entry in UNIFIED_MOOD_TABLE:
        candidates.append(
            (
                f"{entry.label} 색 조합",
                f"{entry.color_tendency} 색으로 {entry.label} 느낌을 만들어요.",
                entry.color_tendency,
            )
        )
    candidates.append(
        (
            "기본 색 조합",
            "특별히 원하는 색이 없을 때 편안하게 시작하는 조합이에요.",
            GLOBAL_DEFAULT_COLOR_TENDENCY,
        )
    )
    return candidates


def _build_q2(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    seen: set[str] = set()
    options: list[QuestionOption] = []
    for label, _desc, color in _q2_color_candidates(profile):
        if color in seen:
            continue
        seen.add(color)
        options.append(
            QuestionOption(
                label=label,
                description=f"{color} 색을 중심으로 써요. ({_rig_note(rig)})",
                value=color,
            )
        )
        if len(options) == 3:
            break
    return QuestionCard(
        step=Q2_PALETTE,
        prompt="어떤 색이 가장 잘 어울릴까요?",
        why="좋아하는 색을 말하면 그 색을 중심으로 다른 빛을 맞춰 드려요.",
        options=tuple(options),
    )


# ---------------------------------------------------------------------------
# Q3 — 클라이맥스 (피크 구간·터뜨릴 방식)
# ---------------------------------------------------------------------------


def _q3_ranked_entries(profile: MusicProfile) -> list[MoodEntry]:
    """Highest D level first (table order breaks ties), with the confirmed
    concept's position bias (if any) promoted to the front — grounding V4's
    "피크 유일성"/D5 worked examples while letting Q1 reshape the
    recommendation (DI2)."""
    indexed = list(enumerate(UNIFIED_MOOD_TABLE))
    ranked = [entry for _, entry in sorted(indexed, key=lambda pair: (-pair[1].d_level, pair[0]))]
    seed = _find_concept_seed(profile.concept)
    if seed is not None:
        biased = [entry for entry in ranked if entry.label in seed.position_bias]
        rest = [entry for entry in ranked if entry.label not in seed.position_bias]
        ranked = biased + rest
    return ranked


def _build_q3(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    top = _q3_ranked_entries(profile)[:3]
    options = tuple(
        QuestionOption(
            label=entry.label,
            description=(
                f"{entry.color_tendency} 색으로 가장 중요한 순간을 "
                f"크고 또렷하게 보여 줘요. ({_rig_note(rig)})"
            ),
            value=DirectorOverride(
                d_level=entry.d_level,
                color_tendency=entry.color_tendency,
                position_candidates=entry.position_candidates,
            ),
        )
        for entry in top
    )
    return QuestionCard(
        step=Q3_CLIMAX,
        prompt="가장 중요한 순간을 어떻게 보여 주면 좋겠어요?",
        why="노래에서 가장 기억에 남을 한순간을 정하면 빛의 힘을 그곳에 모을 수 있어요.",
        options=options,
    )


# ---------------------------------------------------------------------------
# Q4 — 공간 스토리 (포지션 진행 서사)
# ---------------------------------------------------------------------------


def _ascending_positions() -> tuple[str, ...]:
    indexed = list(enumerate(UNIFIED_MOOD_TABLE))
    ranked = sorted(indexed, key=lambda pair: (pair[1].d_level, pair[0]))
    return tuple(entry.label for _, entry in ranked)


def _q4_candidates(profile: MusicProfile) -> list[tuple[str, str, tuple[str, ...]]]:
    ascending = _ascending_positions()
    descending = tuple(reversed(ascending))
    table_order = tuple(entry.label for entry in UNIFIED_MOOD_TABLE)
    candidates: list[tuple[str, str, tuple[str, ...]]] = []
    seed = _find_concept_seed(profile.concept)
    if seed is not None:
        biased_first = tuple(seed.position_bias) + tuple(
            label for label in ascending if label not in seed.position_bias
        )
        candidates.append(
            (
                f"{seed.concept} 컨셉 우선 배치",
                f"{seed.concept} 느낌을 먼저 보여 주고 차차 무대를 넓게 보여 줘요.",
                biased_first,
            )
        )
    candidates.append(
        (
            "좁음→넓음 (E3 기본)",
            "처음엔 한곳에 집중하고 뒤로 갈수록 무대를 넓게 보여 줘요.",
            ascending,
        )
    )
    candidates.append(
        (
            "넓음→좁음 (역순)",
            "처음에는 무대를 넓게 쓰고 마지막에는 한곳에 시선을 모아요.",
            descending,
        )
    )
    candidates.append(("사전 등재 순서", "장면마다 다른 방향을 골고루 보여 줘요.", table_order))
    return candidates


def _build_q4(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    seen: set[tuple[str, ...]] = set()
    options: list[QuestionOption] = []
    for label, desc, sequence in _q4_candidates(profile):
        if sequence in seen:
            continue
        seen.add(sequence)
        options.append(
            QuestionOption(
                label=label,
                description=f"{desc} ({_rig_note(rig)})",
                value=DirectorOverride(position_candidates=sequence),
            )
        )
        if len(options) == 3:
            break
    return QuestionCard(
        step=Q4_SPATIAL_STORY,
        prompt="처음부터 끝까지 무대가 어떻게 달라 보이면 좋겠어요?",
        why="한곳에 집중했다가 무대를 넓게 보여 주는 식으로 흐름을 만들어요.",
        options=tuple(options),
    )


# ---------------------------------------------------------------------------
# Q5 — 질감 (스냅/페이드 성향·이펙트 밀도)
# ---------------------------------------------------------------------------


def _build_q5(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    candidates: list[tuple[str, str, str]] = []
    genre_texture = _find_genre_texture(profile.genre)
    if genre_texture is not None:
        candidates.append(
            (f"{genre_texture.genre} 스타일 전환", genre_texture.reason, genre_texture.texture)
        )
    tempo_texture, tempo_reason = _tempo_band_texture(profile)
    candidates.append(("템포 맞춤 (BPM 기준)", tempo_reason, tempo_texture))
    candidates.append(
        ("표준 전환", "장르·BPM 어느 쪽도 특이하지 않을 때의 기본값.", GLOBAL_DEFAULT_TEXTURE)
    )

    seen: set[str] = set()
    options: list[QuestionOption] = []
    for label, _desc, texture in candidates:
        if texture in seen:
            continue
        seen.add(texture)
        options.append(
            QuestionOption(
                label=label,
                description=f"{texture} 느낌으로 빛의 변화를 정해요. ({_rig_note(rig)})",
                value=texture,
            )
        )

    if len(options) < 3:
        for entry in _GENRE_TEXTURE_TABLE:
            if entry.texture in seen:
                continue
            seen.add(entry.texture)
            options.append(
                QuestionOption(
                    label=f"{entry.genre} 스타일 전환(참고)",
                    description=f"{entry.texture} 느낌으로 빛의 변화를 정해요. ({_rig_note(rig)})",
                    value=entry.texture,
                )
            )
            if len(options) == 3:
                break

    return QuestionCard(
        step=Q5_TEXTURE,
        prompt="전환 방식은 어떻게 갈까요? 컷으로 딱 끊을지, 페이드로 이어갈지 정해요.",
        why="전환 방식을 고르면 노래의 느낌에 맞춰 빛이 바뀌는 속도를 정할 수 있어요.",
        options=tuple(options[:3]),
    )


_STEP_BUILDERS = {
    Q1_CONCEPT: _build_q1,
    Q2_PALETTE: _build_q2,
    Q3_CLIMAX: _build_q3,
    Q4_SPATIAL_STORY: _build_q4,
    Q5_TEXTURE: _build_q5,
}


def build_question(step: str, profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    """Build one step's card — always exactly 3 profile/rig-derived
    proposals (index 0 recommended), fresh every call so a changed
    ``profile`` (e.g. Q1's confirmed concept folded in) changes the result
    (DI2)."""
    builder = _STEP_BUILDERS.get(step)
    if builder is None:
        raise InterviewError(f"unknown interview step {step!r}")
    return builder(profile, rig)


# ---------------------------------------------------------------------------
# Free-text parsing (DI3)
# ---------------------------------------------------------------------------


def _known_color_tokens() -> frozenset[str]:
    """Q2's closed color vocabulary — every atomic token already present in
    the codebase's own color-tendency strings (concept seeds, genre
    defaults, the unified mood table, the global default). Not a new color
    list: purely a re-tokenization of what ``profile.py`` already declares,
    so Q2's free-text parser recognizes exactly the vocabulary the rest of
    the standard already uses, never an invented one."""
    raw_strings = [seed.color_tendency for seed in CONCEPT_SEED_TABLE]
    raw_strings += [entry.color_tendency for entry in GENRE_DEFAULT_TABLE]
    raw_strings += [entry.color_tendency for entry in UNIFIED_MOOD_TABLE]
    raw_strings.append(GLOBAL_DEFAULT_COLOR_TENDENCY)
    tokens: set[str] = set()
    for text in raw_strings:
        for chunk in re.split(r"[/,、=+\s]+", text):
            stripped = chunk.strip()
            if stripped:
                tokens.add(stripped.casefold())
    return frozenset(tokens)


_KNOWN_COLOR_TOKENS = _known_color_tokens()


def _palette_value_tokens(value: object) -> tuple[str, ...]:
    """The Q2 answer split into its color tokens — 실측 2026-08-16: the raw
    answer '블루와 화이트' rode into ``MusicProfile.palette`` as ONE string,
    so lint L5 saw a one-color palette and flagged every cue. Splits on the
    usual separators AND strips the Korean joining particles (와/과/랑/이랑/
    하고) when what remains is a known color token; unknown chunks survive
    verbatim (a color our vocabulary lacks is kept, never dropped)."""
    chunks = re.split(r"[/,、=+·\s]+", str(value))
    tokens: list[str] = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if not cleaned:
            continue
        for particle in ("이랑", "하고", "랑", "와", "과"):
            if (
                len(cleaned) > len(particle)
                and cleaned.endswith(particle)
                and cleaned[: -len(particle)].casefold() in _KNOWN_COLOR_TOKENS
            ):
                cleaned = cleaned[: -len(particle)]
                break
        if cleaned and cleaned not in tokens:
            tokens.append(cleaned)
    return tuple(tokens) or (str(value),)


def _parse_free_text(step: str, raw: str, profile: MusicProfile) -> object | _ParseFailure:
    """Parse one step's free text into the same value shape its options
    carry (DI3). Q1/Q5 are open vocabulary and always resolve; Q2 checks
    against :data:`_KNOWN_COLOR_TOKENS`; Q3/Q4 delegate to
    :func:`~server.design.profile.resolve_section`'s own unified-mood
    matcher and surface its :class:`~server.design.profile.UnresolvedMood`
    as a parse failure rather than guessing."""
    if step in (Q1_CONCEPT, Q5_TEXTURE):
        return raw
    if step == Q2_PALETTE:
        folded = raw.casefold()
        if any(token in folded for token in _KNOWN_COLOR_TOKENS):
            return raw
        return _ParseFailure(reason="no_known_color_token")
    if step in (Q3_CLIMAX, Q4_SPATIAL_STORY):
        result: SectionMoodResolution | UnresolvedMood = resolve_section(raw, profile)
        if isinstance(result, UnresolvedMood):
            return _ParseFailure(reason=result.reason)
        if step == Q3_CLIMAX:
            return DirectorOverride(
                d_level=result.d_level,
                color_tendency=result.color_tendency,
                position_candidates=result.position_candidates,
            )
        return DirectorOverride(position_candidates=result.position_candidates)
    raise InterviewError(f"unknown interview step {step!r}")


# ---------------------------------------------------------------------------
# The sequential engine
# ---------------------------------------------------------------------------


class DirectorInterview:
    """Sequential 5-card director interview (R1c) — a pure state machine,
    no console I/O. One step at a time (DI2); Q1's confirmed concept (and
    Q2's confirmed palette) fold into the profile fed to later steps'
    proposal generation via :attr:`working_profile`; every answered step is
    recorded for :meth:`audit_trail` (DI6); DI3/DI4/DI5 are the
    :meth:`submit_answer`/:meth:`restart_from` contracts documented below.
    """

    def __init__(
        self,
        profile: MusicProfile,
        rig: RigProfile,
        *,
        pre_specified: dict[str, str] | None = None,
    ) -> None:
        self._base_profile = profile
        self.rig = rig
        self.answers: dict[str, AnswerRecord] = {}
        pre_specified = pre_specified or {}
        unknown = set(pre_specified) - set(STEP_ORDER)
        if unknown:
            raise InterviewError(f"unknown interview step(s) {sorted(unknown)!r}")
        # Applied in Q1->Q5 order regardless of dict insertion order, so an
        # earlier pre-specified step's effect on `working_profile` is
        # already folded in before a later one is parsed (DI2).
        for step in STEP_ORDER:
            if step in pre_specified:
                self._try_pre_specify(step, pre_specified[step])

    def _try_pre_specify(self, step: str, raw: str) -> None:
        stripped = raw.strip() if raw else ""
        if not stripped:
            return
        profile = self.working_profile
        parsed = _parse_free_text(step, stripped, profile)
        if isinstance(parsed, _ParseFailure):
            # Cannot skip the card on an answer we could not interpret —
            # DI3's no-guess rule; the step falls through to a normal card.
            return
        self.answers[step] = AnswerRecord(
            step=step,
            proposals=(),
            choice=None,
            free_text=stripped,
            value=parsed,
            confirmed=True,
            source=SOURCE_PRE_SPECIFIED,
            director_decision=_project_director_decision(step, parsed, profile),
        )

    @property
    def working_profile(self) -> MusicProfile:
        """The profile later steps' proposals are built from — the base
        profile with Q1's confirmed concept and Q2's confirmed palette
        folded in whenever those steps are already answered (DI2)."""
        profile = self._base_profile
        if Q1_CONCEPT in self.answers:
            profile = dataclasses.replace(profile, concept=self.answers[Q1_CONCEPT].value)
        if Q2_PALETTE in self.answers:
            profile = dataclasses.replace(
                profile, palette=_palette_value_tokens(self.answers[Q2_PALETTE].value)
            )
        return profile

    @property
    def current_step(self) -> str | None:
        """The next step needing a card, or ``None`` once all 5 are
        answered (whether by option, free text, pre-specification, or
        auto-draft)."""
        for step in STEP_ORDER:
            if step not in self.answers:
                return step
        return None

    def is_complete(self) -> bool:
        return self.current_step is None

    def build_current_card(self) -> QuestionCard | None:
        """The current step's card, or ``None`` when the interview is
        already complete. Always freshly generated against
        :attr:`working_profile`."""
        step = self.current_step
        if step is None:
            return None
        return build_question(step, self.working_profile, self.rig)

    def submit_answer(self, raw: str | None) -> AnswerRecord | UnresolvedAnswer:
        """Submit an answer for :attr:`current_step`.

        ``raw`` is matched against the current card's option labels first
        (case-insensitive, exact); anything else is treated as free text
        and parsed per-step (DI3). A blank/``None`` submission is an
        unanswered card — it still advances, recording the recommended
        option's value with ``confirmed=False`` (DI4). An unresolvable free
        text returns :class:`UnresolvedAnswer` and does NOT advance — the
        caller must re-present the same card (DI3's no-guess re-ask).
        """
        step = self.current_step
        if step is None:
            raise InterviewError("interview is already complete — no step to answer")
        profile = self.working_profile
        card = build_question(step, profile, self.rig)
        stripped = raw.strip() if raw else ""

        if not stripped:
            value = card.options[0].value
            record = AnswerRecord(
                step=step,
                proposals=card.options,
                choice=card.options[0],
                free_text=None,
                value=value,
                confirmed=False,
                source=SOURCE_AUTO_DRAFT,
                director_decision=_project_director_decision(step, value, profile),
            )
            self.answers[step] = record
            return record

        for option in card.options:
            if option.label.strip().casefold() == stripped.casefold():
                record = AnswerRecord(
                    step=step,
                    proposals=card.options,
                    choice=option,
                    free_text=None,
                    value=option.value,
                    confirmed=True,
                    source=SOURCE_OPTION,
                    director_decision=_project_director_decision(step, option.value, profile),
                )
                self.answers[step] = record
                return record

        parsed = _parse_free_text(step, stripped, profile)
        if isinstance(parsed, _ParseFailure):
            return UnresolvedAnswer(step=step, free_text=stripped, reason=parsed.reason)

        record = AnswerRecord(
            step=step,
            proposals=card.options,
            choice=None,
            free_text=stripped,
            value=parsed,
            confirmed=True,
            source=SOURCE_FREE_TEXT,
            director_decision=_project_director_decision(step, parsed, profile),
        )
        self.answers[step] = record
        return record

    def restart_from(self, step: str) -> None:
        """DI5 partial restart: drop ``step`` and every step after it,
        preserving every earlier answer untouched. :attr:`current_step`
        becomes ``step`` again."""
        if step not in STEP_ORDER:
            raise InterviewError(f"unknown interview step {step!r}")
        for later in STEP_ORDER[STEP_ORDER.index(step) :]:
            self.answers.pop(later, None)

    def audit_trail(self) -> tuple[AnswerRecord, ...]:
        """DI6 — every answered step's :class:`AnswerRecord`, in Q1→Q5
        order."""
        return tuple(self.answers[step] for step in STEP_ORDER if step in self.answers)
