"""Music profile — the song's musical identity, and the unified mood
dictionary that turns a section's mood-word into (D level, color tendency,
position candidates) (SPEC-COPILOT-SONGSTD-001 M1, REQ R1, docs/proposals/
song-lighting-design-standard.md §2b, §3, §4b, §7).

:class:`MusicProfile` carries the attributes the standard's §2b binding table
names (tempo, meter, genre, key/mode, concept, palette) as one immutable
value. :func:`resolve_section` is the unified mood dictionary the standard's
§2b M4 clause describes: where ``server.spatial.position_moods`` gives a mood
sentence one position suggestion, this gives every section three axes at
once — extending ``server.spatial.position_moods``' own eight looks with the
D level and color tendency the standard's worked examples name for each one
('"웅장한 피날레" → D5 + 쿨 볼드 + Ring In', '"잔잔한 발라드" → D2 + 블루/
웜화이트 + Vocal DSC').

``server.spatial.position_moods`` keeps running unmodified for its existing
callers (spec.md R1's R clause: "기존 position_moods 키워드 무겹침 계약
유지") — this module READS its table (``POSITION_MOOD_TABLE``) rather than
duplicating the keyword lists, so the two can never drift apart and the
existing non-overlap contract is inherited by construction, not re-declared.

Per the standard's own attribute-to-rule binding (§2b table), genre and
concept do not ground a D level — only a section's own mood-word does (an
explicit D1-D5 assignment is a later milestone). :func:`resolve_section`
therefore resolves each of the three axes independently against its own
priority chain (director intent > section mood-word > concept > genre >
global default — M2 + DI1) rather than picking one tier to answer all three;
D level's chain simply has no concept/genre rung because the standard gives
it none. A section whose mood-word is given but matches nothing in the table
(or ties between two entries) is never guessed at (spec.md R1's R clause:
"무드어 불일치 구간은 추측 없이 카드 질의") — it comes back as
:class:`UnresolvedMood` instead, unless a director override already covers
every axis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.spatial.position_moods import POSITION_MOOD_TABLE

__all__ = [
    "BPM_SOURCE_DEFAULT",
    "BPM_SOURCE_MEASURED",
    "BPM_SOURCE_SHEET",
    "CONCEPT_SEED_TABLE",
    "DEFAULT_BPM",
    "GENRE_DEFAULT_TABLE",
    "GLOBAL_DEFAULT_COLOR_TENDENCY",
    "GLOBAL_DEFAULT_D_LEVEL",
    "SOURCE_CONCEPT",
    "SOURCE_DIRECTOR_INTENT",
    "SOURCE_GENRE",
    "SOURCE_GLOBAL_DEFAULT",
    "SOURCE_SECTION_MOOD",
    "UNIFIED_MOOD_TABLE",
    "BpmResolution",
    "ConceptSeed",
    "DirectorOverride",
    "GenreDefault",
    "MoodEntry",
    "MusicProfile",
    "ProfileError",
    "SectionMoodResolution",
    "UnresolvedMood",
    "parse_sheet_bpm",
    "resolve_bpm",
    "resolve_section",
]


class ProfileError(ValueError):
    """A music-profile input is malformed."""


#: BPM defaults to this when a song doesn't declare one (spec.md R1's R
#: clause: "BPM 미지정 시 120 기본값 + 결과에 명시"). ``MusicProfile`` always
#: discloses whether a value fell back to this default via
#: :attr:`MusicProfile.bpm_is_default` — the "결과에 명시" half of the rule.
DEFAULT_BPM = 120.0

#: The neutral D level used only when NEITHER a director override NOR a
#: section mood-word supplies one (no concept/genre rung exists for this
#: axis — see the module docstring). The mid-point of D1-D5, chosen for the
#: same reason ``DEFAULT_BPM`` is a plain round number: an explicit,
#: disclosed placeholder, not a claim about the song.
GLOBAL_DEFAULT_D_LEVEL = 3

#: The neutral color tendency used only when no tier (director, section
#: mood-word, concept, genre) supplies one.
GLOBAL_DEFAULT_COLOR_TENDENCY = "중립 화이트"

#: Priority-chain source tags (M2 + DI1: "감독 답변 > 구간 무드 > 컨셉 > 장르
#: > 전역 기본값"), recorded per axis on :class:`SectionMoodResolution` so a
#: caller can audit which tier actually decided each value.
SOURCE_DIRECTOR_INTENT = "director_intent"
SOURCE_SECTION_MOOD = "section_mood"
SOURCE_CONCEPT = "concept"
SOURCE_GENRE = "genre"
SOURCE_GLOBAL_DEFAULT = "global_default"

#: D level + color tendency per ``position_moods`` label. Grounded in the
#: standard's own worked examples (§2b M4) plus the §3 D-budget table's
#: per-level CCT/saturation/position-width columns and the §4b C4 color
#: semantics ("벌스 쿨→코러스 웜(록)", "감성=블루/퍼플", "피크=레드 또는 곡
#: 액센트색 볼드") — never invented beyond what those sections state:
#:
#: * Vocal DSC (조용/발라드) — §2b M4 예시 그대로: D2 + 블루/웜화이트.
#: * Center (오프닝/등장/드라마틱) — 진입 순간의 중간 텐션. §3 D3 행의
#:   CCT "중립~쿨"을 그대로 옮김.
#: * Ring In (웅장/장엄/클라이맥스) — §2b M4 예시 그대로: D5 + 쿨 볼드.
#: * Cross (후렴/파티/edm) — §4b C4 "코러스는 웜(록)"의 코러스 기본값.
#: * Fan Out (화려/개방/스케일) — §3 D4 행의 채도 "높음"을 "비비드"로.
#: * Audience (호응/떼창) — §4c P4 "Audience는 D5 전용" + §4b C4 "피크=레드".
#: * Wall (배경/커튼/합창) — §3 D3 행의 CCT "중립~쿨"을 유사색 배경으로.
#: * Home (정리/리셋/대기) — §3 D1 행의 CCT "웜 3000~4000K" 그대로.
_D_LEVEL_AND_COLOR_BY_LABEL: dict[str, tuple[int, str]] = {
    "Vocal DSC": (2, "블루/웜화이트"),
    "Center": (3, "중립~쿨 화이트"),
    "Ring In": (5, "쿨 볼드"),
    "Cross": (4, "웜 볼드"),
    "Fan Out": (4, "비비드"),
    "Audience": (5, "레드 액센트"),
    "Wall": (3, "쿨 유사색"),
    "Home": (1, "웜 3000K"),
}


@dataclass(frozen=True)
class MoodEntry:
    """One ``position_moods`` look extended with the standard's other two
    axes (§2b M4) — one row of the unified mood dictionary."""

    label: str
    keywords: tuple[str, ...]
    d_level: int
    color_tendency: str
    position_candidates: tuple[str, ...]
    reason: str


def _build_unified_mood_table() -> tuple[MoodEntry, ...]:
    labels = {entry.label for entry in POSITION_MOOD_TABLE}
    missing = labels - _D_LEVEL_AND_COLOR_BY_LABEL.keys()
    if missing:
        raise ProfileError(
            f"position_moods label(s) {sorted(missing)} have no D-level/color "
            "mapping in _D_LEVEL_AND_COLOR_BY_LABEL"
        )
    return tuple(
        MoodEntry(
            label=entry.label,
            keywords=entry.keywords,
            d_level=_D_LEVEL_AND_COLOR_BY_LABEL[entry.label][0],
            color_tendency=_D_LEVEL_AND_COLOR_BY_LABEL[entry.label][1],
            position_candidates=(entry.label, *entry.alternatives),
            reason=entry.reason,
        )
        for entry in POSITION_MOOD_TABLE
    )


#: The unified mood dictionary (§2b M4) — one row per ``position_moods``
#: look, D level + color tendency joined on. Keyword non-overlap is
#: inherited from ``POSITION_MOOD_TABLE`` by construction (see module
#: docstring) and re-verified below for drift-safety.
UNIFIED_MOOD_TABLE: tuple[MoodEntry, ...] = _build_unified_mood_table()


@dataclass(frozen=True)
class ConceptSeed:
    """One concept-vocabulary seed (§2b: "컨셉 어휘 → 시드"). Grounded ONLY
    in the three worked examples the standard names — no invented concepts."""

    concept: str
    color_tendency: str
    position_bias: tuple[str, ...]
    reason: str


#: §2b: '"우주"=블루/퍼플+Ring In, "네온"=마젠타/시안+Cross, "빈티지"=웜
#: CTO+Wall 등 (확장 가능한 시드 표)'. These three are the only seeds the
#: standard names; the table is intentionally left "확장 가능" (extensible)
#: rather than padded with ungrounded entries.
CONCEPT_SEED_TABLE: tuple[ConceptSeed, ...] = (
    ConceptSeed(
        concept="우주",
        color_tendency="블루/퍼플",
        position_bias=("Ring In",),
        reason='표준 §2b: "우주"=블루/퍼플+Ring In.',
    ),
    ConceptSeed(
        concept="네온",
        color_tendency="마젠타/시안",
        position_bias=("Cross",),
        reason='표준 §2b: "네온"=마젠타/시안+Cross.',
    ),
    ConceptSeed(
        concept="빈티지",
        color_tendency="웜 CTO",
        position_bias=("Wall",),
        reason='표준 §2b: "빈티지"=웜 CTO+Wall.',
    ),
)


@dataclass(frozen=True)
class GenreDefault:
    """One genre's palette default (§7 장르 프로파일 table, palette column
    only — texture/feature columns are R2/energy.py territory, not this
    module's)."""

    genre: str
    color_tendency: str
    reason: str


#: §7 table, palette column verbatim per row.
GENRE_DEFAULT_TABLE: tuple[GenreDefault, ...] = (
    GenreDefault(
        genre="메탈",
        color_tendency="스래시=레드/웜, 블랙=콜드블루/화이트, 파워=비비드",
        reason="표준 §7: 메탈 팔레트.",
    ),
    GenreDefault(
        genre="록",
        color_tendency="레드+화이트 시그니처, 웜/쿨 대비",
        reason="표준 §7: 록 팔레트.",
    ),
    GenreDefault(
        genre="edm",
        color_tendency="단색 볼드, 퍼플/레드/화이트",
        reason="표준 §7: EDM 팔레트.",
    ),
    GenreDefault(
        genre="발라드",
        color_tendency="블루/퍼플 백 + 소프트 화이트 프런트",
        reason="표준 §7: 발라드 팔레트.",
    ),
    GenreDefault(
        genre="팝",
        color_tendency="유사색 3~4 + 액센트 1",
        reason="표준 §7: 팝 팔레트.",
    ),
)


def _validate_position_names() -> None:
    canonical = set(BASIC_POSITION_SEQUENCE)
    for entry in UNIFIED_MOOD_TABLE:
        bad = [name for name in entry.position_candidates if name not in canonical]
        if bad:
            raise ProfileError(f"{entry.label!r} names non-canonical position(s) {bad}")
    for seed in CONCEPT_SEED_TABLE:
        bad = [name for name in seed.position_bias if name not in canonical]
        if bad:
            raise ProfileError(
                f"concept seed {seed.concept!r} names non-canonical position(s) {bad}"
            )


def _validate_keyword_uniqueness() -> None:
    seen: dict[str, str] = {}
    for entry in UNIFIED_MOOD_TABLE:
        for keyword in entry.keywords:
            owner = seen.get(keyword)
            if owner is not None and owner != entry.label:
                raise ProfileError(
                    f"keyword {keyword!r} appears in both {owner!r} and {entry.label!r}"
                )
            seen[keyword] = entry.label


_validate_position_names()
_validate_keyword_uniqueness()


@dataclass(frozen=True)
class MusicProfile:
    """The song's musical identity (spec.md R1, standard §2b's binding
    table): ``bpm``, ``meter``, ``genre``, ``key_mode``, ``concept``,
    ``palette``. Every rule the standard defines takes its parameters from
    one of these attributes — nothing downstream should hardcode a tempo or
    a palette the profile already carries.

    Immutable by design: a profile describes one song for the duration of
    one design session and has no field that should ever need to mutate
    in place.
    """

    bpm: float | None = None
    meter: str = "4/4"
    genre: str | None = None
    key_mode: str | None = None
    concept: str | None = None
    palette: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.bpm is not None:
            if isinstance(self.bpm, bool) or not isinstance(self.bpm, int | float):
                raise ProfileError(f"bpm must be a number, got {self.bpm!r}")
            if self.bpm <= 0:
                raise ProfileError(f"bpm must be positive, got {self.bpm!r}")

    @property
    def effective_bpm(self) -> float:
        """The BPM every timing rule actually converts against — the
        declared value, or :data:`DEFAULT_BPM` when none was given."""
        return self.bpm if self.bpm is not None else DEFAULT_BPM

    @property
    def bpm_is_default(self) -> bool:
        """True when :attr:`effective_bpm` fell back to :data:`DEFAULT_BPM`
        — the "결과에 명시" half of the BPM default rule (spec.md R1's R
        clause): callers that report timing values must disclose when they
        rest on an assumed tempo."""
        return self.bpm is None


# ---------------------------------------------------------------------------
# BPM 정본 우선순위 (SPEC-COPILOT-MUSICSYNC-001 M2 · REQ-MUSICSYNC-016/017)
# ---------------------------------------------------------------------------
#
# **측정(사람이 확인 카드에서 확정한 값) > 시트 ``HEAD.BPM`` > 기본값 120.**
# ``FX-Rate`` 는 **대조 전용**이며 판정에는 쓰지 않는다(plan.md §C 결정 3).
#
# 시트 우선을 기각한 이유: 시트가 스스로 「청취 미검증」을 자백하는 경우
# (``TC_METHOD: DERIVED``)에도 음원에서 온 값을 밀어낸다.
#
# ``FX-Rate`` 역산을 3번째 판정원으로 삼는 것을 기각한 이유:
# ``FX-Rate = SongBPM ÷ 사이클당 박수`` 인데 **사이클당 박수가 사람의 의도**라
# 역산이 일의적이지 않다 — 하나의 ``FX-Rate`` 가 여러 BPM 과 양립한다.

BPM_SOURCE_MEASURED = "measured"
BPM_SOURCE_SHEET = "sheet"
BPM_SOURCE_DEFAULT = "default"

#: 두 템포가 「어긋났다」고 부를 최소 차이(BPM). 부동소수 잔차와 반올림을 불일치로
#: 외치면 보고가 늑대 소년이 되고, 그러면 진짜 불일치도 안 읽힌다.
_BPM_MISMATCH_TOLERANCE = 0.5

#: 시트 ``HEAD.BPM`` 은 주석을 달고 온다(실측: ``120 (고정)``). 첫 숫자 하나만
#: 읽고 나머지는 사람이 읽을 주석으로 둔다. 부호를 **함께** 읽는 것이 중요하다 —
#: 부호를 빼고 읽으면 ``-40`` 이 ``40`` 이라는 멀쩡한 템포로 둔갑한다.
_SHEET_BPM_PATTERN = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


@dataclass(frozen=True)
class BpmResolution:
    """어느 템포를 채택했고, 무엇이 어긋났는지.

    ``bpm`` 이 ``None`` 인 것은 「0」이 아니라 **「아무도 안 줬다」**\\ 이다 —
    그대로 :class:`MusicProfile` 에 실으면 ``bpm_is_default`` 가 ``True`` 로 남아
    「기본값이다」가 하류 전부에 전달된다. 숫자를 채워 넣으면 그 고지가 사라진다.
    """

    bpm: float | None
    source: str
    reason: str
    mismatches: tuple[str, ...] = ()
    fx_rate_back_calculated: float | None = None


def parse_sheet_bpm(raw: object) -> float | None:
    """시트 ``HEAD.BPM`` 문자열에서 템포를 읽는다 — 없으면 ``None``.

    ``None`` 을 돌려주는 것이 ``0.0`` 을 돌려주는 것보다 언제나 낫다. ``0`` 은
    유효한 템포처럼 생겨서 하류로 흘러가고, 흘러간 자리에서 나눗셈이 터지거나
    (더 나쁘게) 조용히 첫 박으로 접힌다.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        value = float(raw)
        return value if value > 0 else None
    if not isinstance(raw, str):
        return None
    match = _SHEET_BPM_PATTERN.search(raw)
    if match is None:
        return None
    value = float(match.group(0))
    return value if value > 0 else None


def resolve_bpm(
    *,
    measured_bpm: float | None = None,
    sheet_bpm: object = None,
    fx_rate: float | None = None,
    beats_per_cycle: float | None = None,
) -> BpmResolution:
    """세 후보를 우선순위대로 갈라 하나를 채택하고, 어긋남은 **전부** 보고한다.

    어긋남 보고는 채택 여부와 **무관하다**(REQ-MUSICSYNC-017): 이긴 값이 있어도
    진 값이 얼마나 달랐는지는 사람이 알아야 한다. 조용한 채택이 바로 이 SPEC 이
    막으려는 실패다.
    """
    sheet_value = parse_sheet_bpm(sheet_bpm)
    reason = "채택 우선순위: 측정 > 시트 HEAD.BPM > 기본값 120."

    mismatches: list[str] = []
    if (
        measured_bpm is not None
        and sheet_value is not None
        and abs(measured_bpm - sheet_value) > _BPM_MISMATCH_TOLERANCE
    ):
        mismatches.append(
            f"측정 BPM {measured_bpm:g} 과 시트 HEAD.BPM {sheet_value:g} 이 어긋납니다."
        )

    back_calculated: float | None = None
    if fx_rate is not None and beats_per_cycle:
        # 대조 전용이다. 이 값은 어느 분기에서도 ``source`` 가 되지 않는다.
        back_calculated = float(fx_rate) * float(beats_per_cycle)
        others = [v for v in (measured_bpm, sheet_value) if v is not None]
        if any(abs(back_calculated - other) > _BPM_MISMATCH_TOLERANCE for other in others) or (
            not others
        ):
            mismatches.append(
                f"FX-Rate 역산값 {back_calculated:g} 은 대조 항목입니다 — "
                "사이클당 박수가 사람의 의도라 역산이 일의적이지 않아 채택 후보에 오르지 않습니다."
            )

    if measured_bpm is not None:
        return BpmResolution(
            bpm=float(measured_bpm),
            source=BPM_SOURCE_MEASURED,
            reason=reason,
            mismatches=tuple(mismatches),
            fx_rate_back_calculated=back_calculated,
        )
    if sheet_value is not None:
        return BpmResolution(
            bpm=sheet_value,
            source=BPM_SOURCE_SHEET,
            reason=reason,
            mismatches=tuple(mismatches),
            fx_rate_back_calculated=back_calculated,
        )
    return BpmResolution(
        bpm=None,
        source=BPM_SOURCE_DEFAULT,
        reason=reason,
        mismatches=tuple(mismatches),
        fx_rate_back_calculated=back_calculated,
    )


@dataclass(frozen=True)
class DirectorOverride:
    """A director-confirmed value for one or more axes (standard §2d DI1:
    "감독 답변이 해당 축을 최우선 오버라이드"). Every field is optional and
    independent — a caller supplies only the axes the director has actually
    confirmed; unset axes fall through to the section-mood/concept/genre/
    global-default chain below it.

    This is M1's hook for the M2 연출 인터뷰 (``interview.py``, R1c), not
    that interview itself — M1 ships the override *point*, not the 5-card
    Socratic flow that will eventually populate it.
    """

    d_level: int | None = None
    color_tendency: str | None = None
    position_candidates: tuple[str, ...] | None = None

    def is_complete(self) -> bool:
        """True when every axis is already decided — the resolver can skip
        section-mood matching entirely in that case."""
        return (
            self.d_level is not None
            and self.color_tendency is not None
            and self.position_candidates is not None
        )


@dataclass(frozen=True)
class SectionMoodResolution:
    """One section's resolved (D level, color tendency, position
    candidates) triple (spec.md R1's A clause), plus the priority-chain
    source that decided each axis (a ``SOURCE_*`` tag) so a caller can
    audit — and eventually surface to the director — why a value is what
    it is."""

    d_level: int
    color_tendency: str
    position_candidates: tuple[str, ...]
    d_source: str
    color_source: str
    position_source: str
    matched_keywords: tuple[str, ...] = ()

    def as_tuple(self) -> tuple[int, str, tuple[str, ...]]:
        """The bare (D level, color tendency, position candidates) triple
        spec.md R1's A clause names, with the source audit trail dropped."""
        return (self.d_level, self.color_tendency, self.position_candidates)


@dataclass(frozen=True)
class UnresolvedMood:
    """A section's mood-word could not be resolved without guessing
    (spec.md R1's R clause: "무드어 불일치 구간은 추측 없이 카드 질의") — the
    caller should surface a question card for this section rather than
    silently substituting a default."""

    mood_text: str
    reason: str
    tied_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class _MoodMatch:
    entry: MoodEntry
    matched_keywords: tuple[str, ...]


@dataclass(frozen=True)
class _AmbiguousMoodMatch:
    tied_labels: tuple[str, ...]


def _match_unified_mood(text: str) -> _MoodMatch | _AmbiguousMoodMatch | None:
    """Score ``text`` against :data:`UNIFIED_MOOD_TABLE`, same decision rule
    as ``position_moods.match_position_mood`` (most matched keywords wins)
    but with one difference: a tie at the top score is reported as
    ambiguous instead of resolved by table order, per the no-guess rule."""
    folded = text.casefold()
    scored = [
        (entry, matched)
        for entry in UNIFIED_MOOD_TABLE
        if (matched := tuple(keyword for keyword in entry.keywords if keyword in folded))
    ]
    if not scored:
        return None
    best_score = max(len(matched) for _, matched in scored)
    top = [(entry, matched) for entry, matched in scored if len(matched) == best_score]
    if len(top) > 1:
        return _AmbiguousMoodMatch(tied_labels=tuple(entry.label for entry, _ in top))
    entry, matched = top[0]
    return _MoodMatch(entry=entry, matched_keywords=matched)


def _find_concept_seed(concept: str) -> ConceptSeed | None:
    folded = concept.strip().casefold()
    for seed in CONCEPT_SEED_TABLE:
        if seed.concept.casefold() == folded:
            return seed
    return None


def _find_genre_default(genre: str) -> GenreDefault | None:
    folded = genre.strip().casefold()
    for default in GENRE_DEFAULT_TABLE:
        if default.genre.casefold() == folded:
            return default
    return None


def resolve_section(
    mood_text: str | None,
    profile: MusicProfile,
    *,
    director_intent: DirectorOverride | None = None,
) -> SectionMoodResolution | UnresolvedMood:
    """The unified mood dictionary (§2b M4): resolve one section's
    (D level, color tendency, position candidates) from ``mood_text`` and
    ``profile``, per the priority chain M2 + DI1 define — 감독 답변 > 구간
    무드 > 컨셉 > 장르 > 전역 기본값.

    Each axis resolves independently against its own chain (see module
    docstring for why D level's chain has no concept/genre rung). When
    ``mood_text`` is given but matches nothing in :data:`UNIFIED_MOOD_TABLE`
    — or ties between two entries — this returns :class:`UnresolvedMood`
    instead of falling through to concept/genre/global-default, UNLESS
    ``director_intent`` already covers every axis (:meth:`DirectorOverride.
    is_complete`), in which case the mood-word never needed consulting.
    A blank/absent ``mood_text`` is not a mismatch — it simply means the
    section-mood rung has nothing to contribute, and the chain proceeds to
    concept/genre/global-default for the un-overridden axes.
    """
    stripped = mood_text.strip() if mood_text else ""
    fully_overridden = director_intent is not None and director_intent.is_complete()

    matched_entry: MoodEntry | None = None
    matched_keywords: tuple[str, ...] = ()
    if stripped:
        match = _match_unified_mood(stripped)
        if match is None:
            if not fully_overridden:
                return UnresolvedMood(mood_text=stripped, reason="no_keyword_match")
        elif isinstance(match, _AmbiguousMoodMatch):
            if not fully_overridden:
                return UnresolvedMood(
                    mood_text=stripped,
                    reason="ambiguous_keyword_match",
                    tied_labels=match.tied_labels,
                )
        else:
            matched_entry = match.entry
            matched_keywords = match.matched_keywords

    concept_seed = _find_concept_seed(profile.concept) if profile.concept else None
    genre_default = _find_genre_default(profile.genre) if profile.genre else None

    if director_intent is not None and director_intent.d_level is not None:
        d_level, d_source = director_intent.d_level, SOURCE_DIRECTOR_INTENT
    elif matched_entry is not None:
        d_level, d_source = matched_entry.d_level, SOURCE_SECTION_MOOD
    else:
        d_level, d_source = GLOBAL_DEFAULT_D_LEVEL, SOURCE_GLOBAL_DEFAULT

    if director_intent is not None and director_intent.color_tendency is not None:
        color_tendency, color_source = director_intent.color_tendency, SOURCE_DIRECTOR_INTENT
    elif matched_entry is not None:
        color_tendency, color_source = matched_entry.color_tendency, SOURCE_SECTION_MOOD
    elif concept_seed is not None:
        color_tendency, color_source = concept_seed.color_tendency, SOURCE_CONCEPT
    elif genre_default is not None:
        color_tendency, color_source = genre_default.color_tendency, SOURCE_GENRE
    else:
        color_tendency, color_source = GLOBAL_DEFAULT_COLOR_TENDENCY, SOURCE_GLOBAL_DEFAULT

    if director_intent is not None and director_intent.position_candidates is not None:
        position_candidates, position_source = (
            director_intent.position_candidates,
            SOURCE_DIRECTOR_INTENT,
        )
    elif matched_entry is not None:
        position_candidates, position_source = (
            matched_entry.position_candidates,
            SOURCE_SECTION_MOOD,
        )
    elif concept_seed is not None:
        position_candidates, position_source = concept_seed.position_bias, SOURCE_CONCEPT
    else:
        position_candidates, position_source = (), SOURCE_GLOBAL_DEFAULT

    return SectionMoodResolution(
        d_level=d_level,
        color_tendency=color_tendency,
        position_candidates=position_candidates,
        d_source=d_source,
        color_source=color_source,
        position_source=position_source,
        matched_keywords=matched_keywords,
    )
