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
from collections.abc import Sequence
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
    "Q2B_COLOR_USAGE",
    "Q3_CLIMAX",
    "Q4_SPATIAL_STORY",
    "Q5_TEXTURE",
    "SOURCE_AUTO_DRAFT",
    "SOURCE_DEFAULT_ACCEPTED",
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


#: The six closed questions (표준 §2d table + SPEC-COPILOT-COLORMODE-001
#: Q2B), in the fixed order DI2 asks them ("한 번에 하나씩").
Q1_CONCEPT = "Q1_CONCEPT"
Q2_PALETTE = "Q2_PALETTE"
#: SPEC-COPILOT-COLORMODE-001 D1 — "이 색을 곡 전체에 걸쳐 어떻게 쓸지"
#: 확인하는 새 스텝. Q2(팔레트) 바로 다음, Q3(클라이맥스) 이전에 온다.
Q2B_COLOR_USAGE = "Q2B_COLOR_USAGE"
Q3_CLIMAX = "Q3_CLIMAX"
Q4_SPATIAL_STORY = "Q4_SPATIAL_STORY"
Q5_TEXTURE = "Q5_TEXTURE"

STEP_ORDER: tuple[str, ...] = (
    Q1_CONCEPT,
    Q2_PALETTE,
    Q2B_COLOR_USAGE,
    Q3_CLIMAX,
    Q4_SPATIAL_STORY,
    Q5_TEXTURE,
)

#: Audit-trail source tags (DI6) — where an :class:`AnswerRecord`'s value
#: actually came from.
SOURCE_OPTION = "option"
SOURCE_FREE_TEXT = "free_text"
SOURCE_PRE_SPECIFIED = "pre_specified"
SOURCE_AUTO_DRAFT = "auto_draft"
#: SPEC-COPILOT-COLORMODE-001 D3 — Q2B's blank-answer path. Unlike
#: SOURCE_AUTO_DRAFT (confirmed=False, "모르겠다"), a blank Q2B answer means
#: the director SAW the card and explicitly accepted its first option — so
#: it is recorded confirmed=True and never re-queried.
SOURCE_DEFAULT_ACCEPTED = "default_accepted"

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
    #: SPEC-COPILOT-COLORMODE-001 D3 — when True, a blank/unanswered
    #: submission for this card is recorded confirmed=True with
    #: SOURCE_DEFAULT_ACCEPTED instead of the default confirmed=False/
    #: SOURCE_AUTO_DRAFT path. Defaults to False so every existing card
    #: (Q1/Q2/Q3/Q4/Q5) is byte-identical.
    default_confirms: bool = False

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
    count = rig.inventory.fixture_count
    if count <= 0:
        # 실측 2026-08-16: the design-interview rig is built with patch=[]
        # (RG5 — no console patch query on this path), so the inventory count
        # is structurally 0 while the stage clearly has fixtures. Showing
        # "장비 0대" reads as a broken rig — say what we actually used.
        #
        # 카드 t312 (실측 2026-09-07): the previous wording claimed the
        # suggestion was built "무대 좌표를 기준으로". It was not.
        # `RigProfile.geometry` has zero consumers (`grep -rn "\.geometry"
        # server/ ui/src` → test-only hits), and `_q4_candidates` derives its
        # candidates from the music profile alone — a straight-line stage and
        # an arc get the same answer. A note that names a basis the code never
        # reads is an unobserved claim on the director's screen, so it names
        # the basis actually used instead.
        #
        # 카드 t314: Q4 는 배치가 또렷하게 읽힐 때만 :func:`_q4_rig_note` 로
        # 기하를 언급한다. 그 외 단계(Q1·Q3·Q5)와 판독 불가 리그는 이 문면
        # 그대로다 — 안 읽은 근거를 대지 않는다.
        return "장비 목록 없이 곡 구조만 보고 만든 제안이에요"
    return f"현재 장비 {count}대를 기준으로 만든 제안이에요"


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
# Q2B — 색 운용 방식 (SPEC-COPILOT-COLORMODE-001 D1)
# ---------------------------------------------------------------------------

#: spec.md §2 D1 — 2026-09-13 감독 지시 인용, 카드마다 그대로 보여준다.
_COLOR_USAGE_WHY = (
    '2026-09-13 감독 지시: "물론 곡과 조명감독의 스타일에 따라서 다르겠지. '
    '그리고 조명감독의 확인을 받는게 좋을 것 같아." 기본값은 감독이 이미 '
    "밝힌 선호(메인 컬러 중심 변조 + 임팩트에서 터뜨림)입니다."
)


def _build_q2b(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    del profile, rig  # 색 운용 후보는 곡/리그와 무관하게 항상 같은 3옵션.
    options = (
        QuestionOption(
            label="메인 컬러 중심 변조 + 임팩트에서 터뜨림 (기본)",
            description=(
                "Q2에서 고른 색을 기본으로 곡 전체에서 조금씩 바꾸다가, "
                "가장 중요한 순간에 크게 터뜨려요."
            ),
            value="modulate",
        ),
        QuestionOption(
            label="이 색 계열로만 간다",
            description="Q2에서 고른 색 계열을 곡 전체에서 그대로 유지해요.",
            value="single",
        ),
        QuestionOption(
            label="후렴마다 다른 포인트 색",
            description="후렴(하이라이트)마다 서로 다른 포인트 색을 써요.",
            value="per_chorus",
        ),
    )
    return QuestionCard(
        step=Q2B_COLOR_USAGE,
        prompt="이 색을 곡 전체에서 어떻게 쓸까요?",
        why=_COLOR_USAGE_WHY,
        options=options,
        default_confirms=True,
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


#: 카드 t314 — 배치 판독(`RigGeometry.arrangement`) → Q4 에서 **먼저 놓을**
#: 포지션 진행. 무대 모양이 후보 자체를 만들지는 않는다(후보는 여전히 곡
#: 프로파일이 만든다). 정하는 것은 **순서**뿐이다.
#:
#: 카드 t315 가 `RigGeometry.spans` 를 실어 **크기 축이 열렸다.** 그전까지
#: 이 표는 배치 라벨 하나로만 답했고, 그 한계를 여기 적어 두었다: 「깊이/폭
#: 비」를 못 낸다고. 이제 낸다 — :func:`_q4_preferred_progression` 이 라벨의
#: 기본값을 실제로 잰 비와 대조한다. `dominant_axis` 는 여전히 안 쓴다:
#: 전 장비가 한 점에 모인 리그에서도 동률 타이브레이크로 `"x"` 를 답하므로,
#: 판독 불가와 좌우 배치를 못 가른다. 크기가 필요한 자리는 `spans` 가 답한다.
#:
#: 매핑 근거(연출 판단):
#: * `lateral_split` · `bilateral_pairs` · `grid` — 장비가 무대 폭에 걸쳐
#:   퍼져 있다. 「좁음→넓음」은 **무대 폭이 열리는** 서사인데, 폭으로 퍼진
#:   리그만 실제로 열 수 있다. 기존 기본값을 그대로 둔다.
#: * `depth_rows` · `concentric` — 앞뒤 열이나 동심 링으로 묶인 리그다. 폭을
#:   넓히는 단계가 같은 좌우 그림을 깊이만 바꿔 반복해 「밝기 변화」로 읽힌다.
#:   이 리그가 또렷하게 읽는 서사는 **모아 들어가는** 쪽이다.
#: * `vertical_levels` — 트림 높이로 읽히는 리그인데 포지션 어휘에 높이 축이
#:   없다. 어느 램프도 더 참이 아니라, 방향을 번갈아 쓰는 사전 등재 순서를
#:   앞에 둔다.
_GEOMETRY_PREFERRED_PROGRESSION: dict[str, str] = {
    "lateral_split": "ascending",
    "bilateral_pairs": "ascending",
    "grid": "ascending",
    "depth_rows": "descending",
    "concentric": "descending",
    "vertical_levels": "table",
}

_GEOMETRY_ARRANGEMENT_LABELS: dict[str, str] = {
    "lateral_split": "좌우 분할",
    "bilateral_pairs": "좌우 대칭 쌍",
    "grid": "격자",
    "depth_rows": "깊이 열",
    "concentric": "동심 배치",
    "vertical_levels": "높이 단",
}


def _readable_arrangement(rig: RigProfile) -> str | None:
    """Q4 순서를 바꿀 만큼 또렷하게 읽힌 배치, 없으면 ``None``.

    카드 t314 — **퇴화 리그를 예외가 아니라 1급 경로로 다룬다.** 실기에서
    읽은 값이 그렇다: SPEC-COPILOT-SPATIAL-001 §E.2.4 는 장비 19대가 전부
    `(0,0,0)` 으로 답했다고 적는다. 좌표는 읽히는데 뜻이 없다. 그런 리그는
    `classify` 가 `arrangement=None, low_confidence=True` 로 답하므로(t314
    실측) 이 술어 하나가 세 경우를 함께 막는다 — 전 장비 원점, 좌표 자체가
    없는 리그(`coords=[]`), 그리고 어느 축으로도 확신이 안 서는 리그.
    """
    geometry = rig.geometry
    if geometry.arrangement is None or geometry.arrangement_low_confidence:
        return None
    if geometry.arrangement not in _GEOMETRY_PREFERRED_PROGRESSION:
        return None
    return geometry.arrangement


# @MX:NOTE: [AUTO] 깊이가 폭의 이 배를 넘으면 「폭이 열리는」 서사를 못 싣는다.
#   1.5 는 잰 값이 아니라 정한 값이다 — 「깊이가 더 크다」(>1.0)로 잡으면
#   비 1.01 짜리 정사각 리그까지 뒤집혀, 무대에서 아무도 다르게 보지 못할
#   차이로 제안 순서가 흔들린다. 「반쯤 더 깊다」를 경계로 두어 애매한
#   구간은 라벨의 기본값에 남긴다.
_DEPTH_DOMINANCE_RATIO = 1.5


def _q4_preferred_progression(rig: RigProfile) -> str | None:
    """Q4 에서 **먼저 놓을** 진행. 배치가 안 읽히면 ``None``.

    카드 t315 — 라벨만으로 답하던 자리에 **실제로 잰 크기**를 끼운다. 위
    `_GEOMETRY_PREFERRED_PROGRESSION` 의 매핑 근거가 `ascending` 을 고르는
    이유는 하나뿐이다: 「좁음→넓음」은 **무대 폭이 열리는** 서사이고, 폭으로
    퍼진 리그만 그것을 실제로 열 수 있다. 그런데 배치 라벨은 **구조**를
    답할 뿐 크기를 답하지 않는다 — `grid` 는 깊이·좌우 양쪽이 또렷하게
    묶였다는 뜻이어서, 폭 10m·깊이 1m 인 리그와 폭 1m·깊이 10m 인 리그가
    **같은 라벨**을 받는다(t315 실측: 둘 다 `grid`, low_confidence 아님).
    뒤쪽 리그에 「폭이 열린다」를 제안하면 무대에서 일어나지 않는 일을 적는
    셈이다. 그래서 깊이가 폭을 :data:`_DEPTH_DOMINANCE_RATIO` 배 넘게
    앞서면 모아 들어가는 쪽(`descending`)으로 내린다.

    **한 방향으로만 뒤집는다.** 반대쪽(`descending` 라벨인데 폭이 넓은 리그)
    은 건드리지 않는다. `depth_rows` · `concentric` 이 모아 들어가는 서사를
    받은 근거는 span 크기가 아니라 **구조**였다 — 앞뒤 열로 묶인 리그는 폭이
    아무리 넓어도 폭을 넓히는 단계가 같은 좌우 그림을 반복해 「밝기 변화」로
    읽힌다. 그 근거는 비가 커져도 그대로라서, 뒤집을 이유가 없다. 있지도
    않은 대칭을 만들지 않는다.

    비를 못 내는 리그(좌표 없음, 전 장비 원점, 폭이 잡음 수준)는
    `depth_width_ratio` 가 `None` 을 답하고, 그때는 라벨의 기본값이 그대로
    남는다. `_readable_arrangement` 가 앞에서 한 번 더 막으므로 — 낮은 확신
    판독은 애초에 여기까지 오지 않는다 — 같은 좌표에서 뽑은 비로 흐릿한
    판독을 덮어쓰는 일은 없다.
    """
    arrangement = _readable_arrangement(rig)
    if arrangement is None:
        return None
    preferred = _GEOMETRY_PREFERRED_PROGRESSION[arrangement]
    if preferred != "ascending":
        return preferred
    ratio = rig.geometry.depth_width_ratio
    if ratio is not None and ratio > _DEPTH_DOMINANCE_RATIO:
        return "descending"
    return preferred


def _q4_rig_note(rig: RigProfile) -> str:
    """Q4 근거 문면. 기하가 **실제로** 순서를 정했을 때만 그렇게 적는다.

    카드 t312 가 「무대 좌표를 기준으로」를 걷어낸 이유가 그대로 남는다:
    읽지 않은 근거를 대면 감독 화면 위의 미검증 주장이 된다. 배치가 안 읽히면
    t312 가 세운 정직한 문면(:func:`_rig_note`)으로 되돌아간다.
    """
    arrangement = _readable_arrangement(rig)
    if arrangement is None:
        return _rig_note(rig)
    label = _GEOMETRY_ARRANGEMENT_LABELS[arrangement]
    return f"무대 배치({label})와 곡 구조를 함께 보고 만든 제안이에요"


def _q4_candidates(
    profile: MusicProfile, rig: RigProfile
) -> list[tuple[str, str, tuple[str, ...]]]:
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
    # 기하와 무관한 후보들. 키(`ascending`/`descending`/`table`)는
    # `_GEOMETRY_PREFERRED_PROGRESSION` 의 값과 같은 어휘다.
    generic: list[tuple[str, tuple[str, str, tuple[str, ...]]]] = [
        (
            "ascending",
            (
                "좁음→넓음 (E3 기본)",
                "처음엔 한곳에 집중하고 뒤로 갈수록 무대를 넓게 보여 줘요.",
                ascending,
            ),
        ),
        (
            "descending",
            (
                "넓음→좁음 (역순)",
                "처음에는 무대를 넓게 쓰고 마지막에는 한곳에 시선을 모아요.",
                descending,
            ),
        ),
        (
            "table",
            ("사전 등재 순서", "장면마다 다른 방향을 골고루 보여 줘요.", table_order),
        ),
    ]
    preferred = _q4_preferred_progression(rig)
    if preferred is not None:
        # 감독이 확정한 컨셉이 기하보다 앞선다 — 사람이 말한 의도가 방을
        # 이긴다. 그래서 컨셉 후보는 건드리지 않고, 그 **뒤**만 재정렬한다.
        generic.sort(key=lambda pair: pair[0] != preferred)
    candidates.extend(entry for _, entry in generic)
    return candidates


def _build_q4(profile: MusicProfile, rig: RigProfile) -> QuestionCard:
    seen: set[tuple[str, ...]] = set()
    options: list[QuestionOption] = []
    note = _q4_rig_note(rig)
    for label, desc, sequence in _q4_candidates(profile, rig):
        if sequence in seen:
            continue
        seen.add(sequence)
        options.append(
            QuestionOption(
                label=label,
                description=f"{desc} ({note})",
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
    Q2B_COLOR_USAGE: _build_q2b,
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


#: spec.md §2 D1 — Q2B 자유 입력 키워드 그룹 (단색/하나/only/single →
#: "single"; 변조/기본/modulate/main → "modulate"; 후렴마다/포인트/
#: per chorus/accent → "per_chorus"). 순서가 판정 순서다 — 어느 그룹에도
#: 안 걸리면 재질의(DI3 무추측 원칙).
_COLOR_USAGE_SINGLE_TOKENS = ("단색", "하나", "only", "single")
_COLOR_USAGE_MODULATE_TOKENS = ("변조", "기본", "modulate", "main")
_COLOR_USAGE_PER_CHORUS_TOKENS = ("후렴마다", "포인트", "per chorus", "per_chorus", "accent")


def _parse_free_text(step: str, raw: str, profile: MusicProfile) -> object | _ParseFailure:
    """Parse one step's free text into the same value shape its options
    carry (DI3). Q1/Q5 are open vocabulary and always resolve; Q2 checks
    against :data:`_KNOWN_COLOR_TOKENS`; Q2B checks the color-usage keyword
    groups; Q3/Q4 delegate to
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
    if step == Q2B_COLOR_USAGE:
        folded = raw.casefold()
        if any(token in folded for token in _COLOR_USAGE_SINGLE_TOKENS):
            return "single"
        if any(token in folded for token in _COLOR_USAGE_MODULATE_TOKENS):
            return "modulate"
        if any(token in folded for token in _COLOR_USAGE_PER_CHORUS_TOKENS):
            return "per_chorus"
        return _ParseFailure(reason="no_known_color_usage_token")
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
        skipped_steps: Sequence[str] = (),
    ) -> None:
        self._base_profile = profile
        self.rig = rig
        self.answers: dict[str, AnswerRecord] = {}
        # 카드 t311 — 답을 쓸 데가 없는 카드는 **묻지 않는다**. 좌표가 없는
        # 리그에서 Q4(공간 스토리)가 그렇다: 프리셋을 앉힐 장비가 없어 어떤
        # 답을 받아도 큐에 닿지 못한다. 기본값으로 조용히 답하는 것(DI4의
        # auto-draft)은 금지다 — 감독이 고르지 않은 것을 고른 것처럼 남긴다.
        # 건너뛴 단계는 `answers` 에 들어가지 않으므로 `audit_trail` 에도,
        # 재질의 요구에도 나타나지 않는다.
        unknown_skips = set(skipped_steps) - set(STEP_ORDER)
        if unknown_skips:
            raise InterviewError(f"unknown interview step(s) {sorted(unknown_skips)!r}")
        self.skipped_steps = frozenset(skipped_steps)
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
            if step not in self.answers and step not in self.skipped_steps:
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
            if card.default_confirms:
                confirmed, source = True, SOURCE_DEFAULT_ACCEPTED
            else:
                confirmed, source = False, SOURCE_AUTO_DRAFT
            record = AnswerRecord(
                step=step,
                proposals=card.options,
                choice=card.options[0],
                free_text=None,
                value=value,
                confirmed=confirmed,
                source=source,
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
