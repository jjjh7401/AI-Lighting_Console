"""곡 큐 계획 조립과 콘솔 값 줄 — 대화 길·업로드 길이 함께 쓰는 순수 계산.

카드 t480(SPEC-LDDESIGN-001 REQ-003, AC-017) — 원래 ``server/web/session.py`` 에
있던 계획 조립(``_build_unified_song_plan``)과 명령 값 줄 헬퍼를 이 모듈로 옮겼다.
업로드 길(``server/orchestrator/tools.py``)은 ``server.web`` 을 import 할 수 없어
(층 경계) 세션 안에 있으면 같은 조립기를 쓸 수 없었기 때문이다. 코드는 한 글자도
바꾸지 않고 자리만 옮겼다 — 세션의 콘솔 명령은 바이트 동일
(``.moai/reports/t480/m1_session_dump.*``).

이 모듈은 콘솔을 읽지 않는다. 콘솔에서 찾아야 하는 슬롯(포지션·페이저·흰색 프리셋)은
호출자가 찾아서 넘긴다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace

from server.design import color_names as _COLOR_NAMES
from server.design.cue_density import plan_cue_density, rotate_palette
from server.design.interview import (
    Q1_CONCEPT,
    Q2_PALETTE,
    Q2B_COLOR_USAGE,
    Q3_CLIMAX,
    Q4_SPATIAL_STORY,
    Q5_TEXTURE,
)
from server.design.profile import (
    SOURCE_GLOBAL_DEFAULT,
    DirectorOverride,
    MusicProfile,
    SectionMoodResolution,
    UnresolvedMood,
    resolve_section,
)
from server.design.section_palette import _section_palette_choice
from server.design.song_plan import (
    COLOR_USAGE_AXIS,
    D_AXIS,
    FX_AXIS,
    PALETTE_AXIS,
    POSITION_AXIS,
    TEXTURE_AXIS,
    AccentDecision,
    ApprovalState,
    DirectorDecision,
    DisabledNote,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    UnresolvedNote,
)
from server.looks.songcue import (
    SongCueBundle as TimingSongCueBundle,
)
from server.looks.songcue import (
    SongCueLookSelection,
    SongCueSection,
    SongCueSectionBundle,
    SongCueTimingAxes,
    SongCueTimingPlan,
    build_songcue_timing,
)
from server.spatial.mib import PositionCuePlan, position_cue_bundle, premove_follow_command
from server.spatial.pointing import SpatialPointingError
from server.spatial.position_cuesheet import PositionSheetSection

_SONG_CLIMAX_SECTION = re.compile(
    r"후렴|드롭|클라이맥스|피크|chorus|drop|climax|peak", re.IGNORECASE
)


_SAFE_SONG_CUE_NAME = re.compile(r"[A-Za-z0-9 _-]+")
# 카드 t486 — 마디 분할 접미사 ``(1/2)``(``_disambiguate_split_names``)를 허용 문자 안의
# ``1 of 2`` 로 옮긴다. 옮기지 않으면 괄호·빗금만 지워져 ``Intro 12`` 가 된다.
_SPLIT_SUFFIX = re.compile(r"\((\d+)/(\d+)\)")


_DI_RECORD_AXES = {
    Q1_CONCEPT: PALETTE_AXIS,
    Q2_PALETTE: PALETTE_AXIS,
    Q2B_COLOR_USAGE: COLOR_USAGE_AXIS,
    Q3_CLIMAX: D_AXIS,
    Q4_SPATIAL_STORY: POSITION_AXIS,
    Q5_TEXTURE: TEXTURE_AXIS,
}


def _safe_song_cue_name(label: str, cue_number: float) -> str:
    label = _SPLIT_SUFFIX.sub(r"\1 of \2", label)
    kept = "".join(_SAFE_SONG_CUE_NAME.findall(label)).strip()
    if not kept or kept.isdigit():
        return f"Section {cue_number:g}"
    return kept


def _director_decisions(records: Sequence[object]) -> tuple[DirectorDecision, ...]:
    decisions: list[DirectorDecision] = []
    for record in records:
        step = getattr(record, "step", "")
        axis = _DI_RECORD_AXES.get(step)
        if axis is None:
            continue
        decisions.append(DirectorDecision.from_audit_record(record, axis=axis))
    return tuple(decisions)


def _projection(records: Sequence[object], step: str):
    for record in records:
        if getattr(record, "step", None) == step:
            return getattr(record, "director_decision", None)
    return None


def _record_value(records: Sequence[object], step: str, fallback: object = None) -> object:
    for record in records:
        if getattr(record, "step", None) == step:
            return getattr(record, "value", fallback)
    return fallback


def _record_source(records: Sequence[object], step: str, fallback: str = "standard") -> str:
    for record in records:
        if getattr(record, "step", None) == step:
            source = getattr(record, "source", fallback)
            return source if isinstance(source, str) and source else fallback
    return fallback


def _climax_section_index(sections: Sequence[PositionSheetSection]) -> int:
    # 카드 t403 — 확정 구간(role 이 명시된 경로, t393)의 표시 이름은
    # "Chorus 1" 처럼 역할 어휘를 그대로 담는다(`_confirmed_section_names`).
    # 아래 텍스트 검색을 그대로 두면 그 이름 안의 "Chorus" 글자를 절정
    # 신호로 오독해 곡의 **첫** 코러스에서 멈춘다(실측: 141초 곡에서 3초
    # 지점). role 이 있으면 텍스트 검색을 건너뛰고 role + D 레벨로
    # 판정한다 — 코러스 후보 중 D 레벨이 가장 높은(동률이면 나중) 구간을
    # 고른다("마지막 drop" 이 정본 §6 의 최댓값이기 때문이다).
    if any(section.role is not None for section in sections):
        d_levels = [section.d_level if section.d_level is not None else 0 for section in sections]
        chorus_candidates = [
            index for index, section in enumerate(sections, start=1) if section.role == "chorus"
        ]
        if chorus_candidates:
            return max(chorus_candidates, key=lambda index: (d_levels[index - 1], index))
        finale_candidates = [
            index for index, section in enumerate(sections, start=1) if section.role == "finale"
        ]
        if finale_candidates:
            return finale_candidates[-1]
        return len(sections)
    for index, section in enumerate(sections, start=1):
        if _SONG_CLIMAX_SECTION.search(f"{section.name} {section.mood}"):
            return index
    return len(sections)


def _distributed_position(
    positions: tuple[str, ...], section_index: int, section_count: int
) -> str | None:
    if not positions:
        return None
    if section_count <= 1 or len(positions) == 1:
        return positions[0]
    slot = round((section_index - 1) * (len(positions) - 1) / (section_count - 1))
    return positions[slot]


def _section_director_override(
    *,
    section_index: int,
    section_count: int,
    records: Sequence[object],
    climax_index: int,
) -> DirectorOverride | None:
    d_level: int | None = None
    color: str | None = None
    positions: tuple[str, ...] | None = None

    q4 = _projection(records, Q4_SPATIAL_STORY)
    spatial_story = getattr(q4, "spatial_story", None)
    if spatial_story is not None:
        position = _distributed_position(
            tuple(getattr(spatial_story, "positions", ()) or ()),
            section_index,
            section_count,
        )
        if position is not None:
            positions = (position,)

    q3 = _projection(records, Q3_CLIMAX)
    climax = getattr(q3, "climax", None)
    if section_index == climax_index and climax is not None:
        projected_d = getattr(climax, "d_level", None)
        if isinstance(projected_d, int):
            d_level = projected_d
        projected_color = getattr(climax, "accent_color", None)
        if isinstance(projected_color, str) and projected_color.strip():
            color = projected_color
        peak_positions = tuple(getattr(climax, "peak_positions", ()) or ())
        if peak_positions:
            positions = peak_positions

    if d_level is None and color is None and positions is None:
        return None
    return DirectorOverride(d_level=d_level, color_tendency=color, position_candidates=positions)


def _texture_decision(records: Sequence[object]) -> TextureDecision:
    texture = _record_value(records, Q5_TEXTURE, "중간")
    return TextureDecision(label=str(texture), source=_record_source(records, Q5_TEXTURE))


def _fx_decision(records: Sequence[object]) -> FxDecision:
    q5 = _projection(records, Q5_TEXTURE)
    texture = getattr(q5, "texture", None)
    density = getattr(texture, "fx_density", "medium")
    if density == "high":
        return FxDecision(
            allowed=("dimmer chase", "pan sweep"),
            source="director_texture",
            density=2,
        )
    if density == "medium":
        return FxDecision(allowed=("dimmer chase",), source="director_texture", density=1)
    return FxDecision(allowed=(), source="director_texture", density=0)


def _occurrence_accent_label(
    role: str, occurrence: int, total: int, *, is_final_occurrence: bool
) -> str | None:
    """정본 §7.1 사다리를 회차 수가 얼마든 일반화한다 (카드 t403).

    코러스가 25회 반복돼도 매 회차를 찍으면 "짧고 드물어야" 하는 액센트가
    흔해져 정본 §6.1 을 어긴다 — 감독이 원한 것은 "부분마다 변조"(팔레트,
    t402)이지 "부분마다 폭발"이 아니다. 그래서 몇 회든 딱 **가운데**
    회차(무빙 포지션 전환)와 **마지막** 회차(블라인더/백색 플래시)만
    찍는다. 피날레는 항상 곡에 한 번뿐이라(싱글턴, t391) 항상 마지막이다.
    """
    if role == "finale":
        return "white flash" if is_final_occurrence else None
    if role != "chorus" or total <= 1:
        return None
    if is_final_occurrence:
        return "white flash"
    midpoint = max(2, round(total / 2))
    return "moving position hit" if occurrence == midpoint else None


def _accent_decision(
    records: Sequence[object],
    *,
    section_index: int,
    climax_index: int,
    role: str = "other",
    occurrence: int = 1,
    total_for_role: int = 0,
    is_final_occurrence: bool = False,
) -> AccentDecision:
    if section_index == climax_index:
        q3 = _projection(records, Q3_CLIMAX)
        climax = getattr(q3, "climax", None)
        color = getattr(climax, "accent_color", None)
        if isinstance(color, str) and color.strip():
            return AccentDecision(accents=(f"climax accent {color}",), source="director_climax")
        return AccentDecision(accents=("climax accent",), source="director_climax")
    # 카드 t403 — 절정 하나뿐이던 액센트를 회차 사다리로 넓힌다. 절정이
    # 아닌 구간은 §7.1 사다리의 가운데·마지막 회차에서만 액센트가 난다.
    label = _occurrence_accent_label(
        role, occurrence, total_for_role, is_final_occurrence=is_final_occurrence
    )
    if label is not None:
        return AccentDecision(accents=(label,), source="section_arc")
    return AccentDecision()


# ── Section look-arc (연출 아크, handoff 결함 3/4) ─────────────────────────
# Role classification drives per-section Texture / FX / Palette / D-level so
# the five-section pop arc (도입→벌스→후렴→브리지→피날레) never collapses to
# one global look. Direct natural-language section intent outranks the Q4
# whole-song spatial story (결함 4 priority: 구간 자연어 > 감독 구간 선택 >
# Q4 > 장르 > fallback).
_SECTION_ROLE_INTRO = re.compile(r"도입|인트로|오프닝|intro", re.IGNORECASE)


_SECTION_ROLE_BRIDGE = re.compile(r"브리지|간주|인터루드|bridge", re.IGNORECASE)


_SECTION_ROLE_VERSE = re.compile(r"벌스|verse", re.IGNORECASE)


_SECTION_ROLE_FINALE = re.compile(r"마지막|피날레|엔딩|아웃트로|outro|finale|ending", re.IGNORECASE)


_ARC_D_LEVEL: dict[str, int] = {"intro": 2, "verse": 3, "chorus": 5, "bridge": 2, "finale": 5}


_ARC_TEXTURE: dict[str, str] = {
    "intro": "긴 페이드 · 정적",
    "verse": "점진 빌드",
    "chorus": "샤프 히트",
    "bridge": "스파스 · 고립",
    "finale": "서스테인 히트",
}


_ARC_FX: dict[str, tuple[tuple[str, ...], int]] = {
    "intro": ((), 0),
    "verse": (("slow pan",), 1),
    "chorus": (("dimmer chase", "pan sweep"), 2),
    "bridge": (("slow tilt",), 1),
    "finale": (("dimmer chase", "accent sweep"), 2),
}


#: 카드 t405 — 회차마다 효과를 바꾼다. 고치기 전 실측(main@611ce34, Club
#: Diver.mp3 를 앱 경로로 끝까지 태운 타임라인 39구간): 서로 다른 효과가 넷뿐이고
#: 그중 26구간이 바이트 동일한 ``dimmer chase`` 였다. 원인은 둘이다 — ``_ARC_FX``
#: 가 역할당 효과를 한 벌만 갖고, 감독 질감이 medium 이면 아래 ``[:1]`` 이 **항상
#: 0번**을 집는다. 이 곡은 39구간 중 25개가 chorus 라 그 한 줄이 곡을 덮는다.
#:
#: 처방은 색이 카드 t402 에서 한 것과 같은 축이다: 회차(occurrence)로 사다리를
#: 돈다. **회차 1은 위 ``_ARC_FX`` 의 값과 바이트 동일**이라 기존 룩은 안 바뀐다.
#: 효과 이름은 지어내지 않는다 — 전부 이 저장소가 이미 싣고 있는 FX 라이브러리
#: 항목의 말이다(``server/fx/library/{movement,dimmer,color}.yaml``):
#: horizontal chase→``chase-horizontal``, bounce chase→``chase-bounce-run``,
#: v-shape swing→``sweep-vshape-swing``(셋 다 카드 t372 가 넣고 이 곡에서 한
#: 번도 안 뽑히던 것), soft wave→``wave-soft-rise``, cross diagonal→
#: ``diagonal-club-cross``, orbit→``circle-relative-orbit``, breathing→
#: ``pulse-breath``.
#:
#: 🔴 여기 쓰는 말은 ``song_cue_composer._contains_any`` 가 ``_BLACKOUT_TOKENS``
#: (blackout/암전/…)와 ``_AUDIENCE_TOKENS``(audience/blinder/객석/…)로 되읽는다 —
#: 새 이름을 더할 때 그 토큰이 문자열 안에 들어가면 구간이 통째로 블랙아웃이나
#: 객석 조명으로 오판된다. 아래 이름은 어느 토큰도 포함하지 않는다.
_ARC_FX_LADDER: dict[str, tuple[tuple[str, ...], ...]] = {
    "intro": ((),),
    "verse": (("slow pan",), ("slow tilt",), ("soft wave",)),
    "chorus": (
        ("dimmer chase", "pan sweep"),
        ("horizontal chase", "pan sweep"),
        ("bounce chase", "v-shape swing"),
        ("cross diagonal", "dimmer chase"),
    ),
    "bridge": (("slow tilt",), ("orbit",), ("breathing",)),
    "finale": (("dimmer chase", "accent sweep"),),
}


def _arc_fx_allowed(role: str, occurrence: int) -> tuple[str, ...] | None:
    """이 회차가 쓸 효과 묶음. 사다리가 없는 역할이면 ``None`` (카드 t405).

    회차는 1부터 센다 — 1회차는 항상 사다리 0번, 즉 ``_ARC_FX`` 와 같은 값이다.
    """
    rungs = _ARC_FX_LADDER.get(role)
    if not rungs:
        return None
    return rungs[(max(occurrence, 1) - 1) % len(rungs)]


# Direct positional intent inside one section's own wording. Ordered: an
# audience mention wins over a generic "퍼지/넓혀" in the same sentence.
_DIRECT_POSITION_INTENTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"보컬|vocal|솔로|한\s*명|시선.*모", re.IGNORECASE), ("Vocal DSC",)),
    (re.compile(r"객석|관객|audience|블라인더", re.IGNORECASE), ("Audience",)),
    (re.compile(r"넓혀|넓어지|넓게|확장|폭.*넓|퍼지", re.IGNORECASE), ("Fan Out",)),
    (re.compile(r"비워|비운|비어|고립|미니멀", re.IGNORECASE), ("Wall",)),
)


def _section_role(section: PositionSheetSection, *, section_index: int, section_count: int) -> str:
    # 카드 t393 — 오디오 확정 구간은 이름/무드가 비어(중립 ASCII·빈 문자열) 아래
    # 자연어 판독이 항상 "other" 로 떨어진다. 명시 role 이 실려 있으면(구간
    # 확정 경로가 t393 처방으로 채운 값) 그 값을 최우선으로 쓴다 — d_level 이
    # 명시 필드로 전역 기본값 우회를 푼 것과 같은 처방(position_cuesheet.py 참조).
    if section.role is not None:
        return section.role
    text = f"{section.name} {section.mood}"
    is_chorus = _SONG_CLIMAX_SECTION.search(text) is not None
    if section_index == section_count and (
        is_chorus or _SECTION_ROLE_FINALE.search(text) is not None
    ):
        return "finale"
    if _SECTION_ROLE_INTRO.search(text):
        return "intro"
    if _SECTION_ROLE_BRIDGE.search(text):
        return "bridge"
    if is_chorus:
        return "chorus"
    if _SECTION_ROLE_VERSE.search(text):
        return "verse"
    return "other"


def _direct_position_intent(text: str) -> tuple[str, ...] | None:
    for pattern, positions in _DIRECT_POSITION_INTENTS:
        if pattern.search(text):
            return positions
    return None


def _section_texture_decision(
    *,
    section: PositionSheetSection,
    section_index: int,
    climax_index: int,
    section_count: int,
    records: Sequence[object],
) -> TextureDecision:
    base = _texture_decision(records)
    role = _section_role(section, section_index=section_index, section_count=section_count)
    label = _ARC_TEXTURE.get(role)
    if label is None:
        return base
    return TextureDecision(
        label=label, source="section_arc", notes=(f"감독 전환 방식 기준: {base.label}",)
    )


def _section_fx_decision(
    *,
    section: PositionSheetSection,
    section_index: int,
    climax_index: int,
    section_count: int,
    records: Sequence[object],
    occurrence: int = 1,
) -> FxDecision:
    base = _fx_decision(records)
    role = _section_role(section, section_index=section_index, section_count=section_count)
    arc = _ARC_FX.get(role)
    if arc is None:
        return base
    _, density = arc
    # 카드 t405 — 묶음은 회차 사다리에서, 축 개수(density)는 ``_ARC_FX`` 에서.
    # 사다리 칸은 전부 같은 길이라 density 는 회차와 무관하게 그대로다.
    allowed = _arc_fx_allowed(role, occurrence) or arc[0]
    if base.density <= 0:
        # Director asked for a calm texture — the arc never re-enables FX.
        return FxDecision(allowed=(), source="section_arc", disabled=allowed, density=0)
    if base.density == 1 and density > 1:
        # 감독 질감이 medium 이면 축이 하나로 깎인다. 예전에는 여기서 **항상**
        # 0번을 집어 회차 사다리가 통째로 지워졌다(실측: 26구간이 같은 효과).
        # 회차가 고른 묶음의 첫 축을 그대로 남겨 사다리를 살린다.
        allowed, density = allowed[:1], 1
    return FxDecision(allowed=allowed, source="section_arc", density=density)


def _unresolved_prompt(section: PositionSheetSection, reason: str) -> str:
    return (
        f"{section.name} 구간({section.start_ms / 1000:g}s)의 무드/포지션을 "
        f"해석하지 못했습니다({reason}). 이 구간의 무드를 다시 지정해 주세요."
    )


# 페이저 자동 제안(T12) — 곡 설계 섹션 큐의 역할 텍스트에서 고신뢰 쌍만
# 제안한다(코디네이터 매핑 표, 보수적). ``cue.cue_name``은 ``song_plan.
# CuePayload.cue_name == section.label == section.name``(디자인 인터뷰가
# 부여한 섹션 원문 이름) — session.py의 ``_section_role`` 역할 판별기가
# 쓰는 것과 같은 어휘를 재사용한다. '최고 에너지(드롭/후렴 피크 상당)'와
# '후렴'을 가르기 위해 기존 ``_SONG_CLIMAX_SECTION``(후렴|드롭|클라이맥스|
# 피크를 하나로 뭉뚱그림)을 두 갈래로 세분화했다 — 드롭/클라이맥스/피크
# 어휘가 있으면 최고 에너지, 없이 '후렴'만 있으면 일반 후렴이다.
# ``cue.d_level``(1-5)은 이 판별에 쓰지 않는다 — ``_ARC_D_LEVEL``에서
# chorus=finale=5로 같은 값을 공유해 최고 에너지/후렴/피날레를 구별할
# 신호가 못 된다(추측 금지 — 확인 결과는 worker_done에 보고). 매칭되지
# 않는 나머지 전부(인트로 포함)는 None — 정적 유지가 안전 기본값이다.
_PHASER_PEAK_SECTION = re.compile(r"드롭|클라이맥스|피크|drop|climax|peak", re.IGNORECASE)


_PHASER_CHORUS_SECTION = re.compile(r"후렴|chorus", re.IGNORECASE)


def _phaser_label_for_cue(cue) -> str | None:
    """섹션 큐 → 카탈로그 페이저 라벨 제안, 없으면 None(정적 유지 = 안전).

    MIB pre-move(``kind != 'section'``)는 어두운 순간의 순수 이동 큐라
    제외한다 — 페이저는 보이는 연출이므로 암전 이동에 실을 이유가 없다.
    블랙아웃 큐(``dimmer.blackout`` 또는 key_pct 없음/0)도 제외한다 —
    페이저 recall이 프로그래머 Dimmer 값을 되살려 의도한 암전을 깰 수
    있다(``_back_layer_value_lines``와 같은 안전 규율, key_pct<=0 가드).
    """
    if cue.kind != "section":
        return None
    if cue.dimmer.blackout or not cue.dimmer.key_pct or cue.dimmer.key_pct <= 0:
        return None
    name = cue.cue_name or ""
    if _PHASER_PEAK_SECTION.search(name):
        return "Drop Slam"
    if _PHASER_CHORUS_SECTION.search(name):
        return "Wave CM"
    if _SECTION_ROLE_BRIDGE.search(name):
        return "Breathe Cool"
    if _SECTION_ROLE_FINALE.search(name):
        return "Finale Slam"
    if _SECTION_ROLE_VERSE.search(name):
        return "Breathe Warm"
    return None


def _phaser_cue_value_lines(
    cue, fids: Sequence[int], phaser_slots: Mapping[str, tuple[int, int]]
) -> tuple[str, ...]:
    """제안된 페이저의 recall 한 줄(T11 §2 문법) — 슬롯 미해석이면 빈 튜플.

    ``position_cue_bundle``의 ``extra_value_lines``에 얹힌다: 플랜 자신의
    포지션/디머 라인 **뒤**에 온다(``_reviewed_song_commands`` 호출부),
    그래서 콤보/디머 페이저의 디머 스텝이 큐의 정적 key_pct를 프로그래머
    last-wins 규칙으로 정확히 덮어쓴다(계약 #5 순서 규율). recall이 멀티스텝
    페이저를 통째로 싣는 것은 **2026-08-19 실기 육안 확인**됐다(Drop Slam
    발사 → 조명이 페이저로 재생, 13번 프로브 §확인 기록). [잔여 ASSUMPTION —
    T11 프로브 §4] 이 recall을 담아 **저장한 큐**가 프리셋 참조를 보존하는지
    (참조 vs 평탄화)는 여전히 프로토콜로 판독 불가 — 곡 큐 재생의 육안
    확인이 남은 마지막 조각이다.
    """
    label = _phaser_label_for_cue(cue)
    if label is None:
        return ()
    resolved = phaser_slots.get(label)
    if resolved is None:
        return ()
    pool_no, slot = resolved
    return (_preset_recall_command(pool_no, fids, slot),)


#: 카드 t453 — 흰색 큐가 부르는 콘솔 컬러 프리셋 라벨(감독 결정 2026-09-27:
#: RGBW 숫자를 앱이 박지 않고 콘솔 프리셋을 이름으로 참조). 라벨은 판독값이다
#: (`.moai/reports/t469/run3_phaser_pools.txt`, 컬러 풀 4 슬롯 7·8). 슬롯 번호는
#: 적지 않는다 — 쇼파일마다 다르므로 ``_white_preset_slots``가 풀에서 찾는다.
_WHITE_PRESET_LABELS: dict[str, str] = {
    "Warm White": "웜 화이트 (=P2)",
    "Cool White": "뉴트럴 화이트 (=P3)",
}


_WHITE_NAME_BY_RGB: dict[tuple[int, int, int], str] = {
    rgb: name for name, rgb in _COLOR_NAMES.COLOR_PALETTE_SEQUENCE if name in _WHITE_PRESET_LABELS
}


def _white_palette_name(cue) -> str | None:
    """구간 큐의 주색이 표준 팔레트 흰색 둘 중 하나면 그 이름, 아니면 None."""
    if cue.kind != "section" or not cue.color.palette:
        return None
    rgb = _COLOR_NAMES.resolve_color_name(cue.color.palette[0])
    return None if rgb is None else _WHITE_NAME_BY_RGB.get(rgb)


def _song_color_value_lines(
    cue,
    fids: Sequence[int],
    w_fids: frozenset[int] = frozenset(),
    white_presets: Mapping[str, tuple[int, int] | str] | None = None,
) -> tuple[tuple[str, ...], str | None]:
    """SPEC-LDDESIGN-001 M2 — 큐의 팔레트 주색을 콘솔 값 라인으로 낸다.

    ``(값 라인들, 실패 사유 또는 None)``. **고치기 전 실측**: 감독 확정
    경로는 색을 한 줄도 보내지 않았다(`reports/lddesign-m2-cue-path/`)
    — 설계층은 팔레트를 들고 있는데 명령 생성기가 떨어뜨렸다.

    주색만 낸다. 보조색·유보색·언더페인팅은 M3(컬러 규칙)의 몫이고,
    이 자리에서 지어내면 그 규칙이 도착했을 때 두 출처가 생긴다.

    MIB 사전이동 큐(``kind == "mib_premove"``)는 건너뛴다 — 어둠 속 이동
    큐라 색 값이 공연에 보이지 않고, 사전에 색까지 얹을지는 아직 안 잰
    별도 판단이다.

    카드 t430 — ``w_fids``(W 채널 확인 기구, 기본 빈 집합)에 든 fid는
    ``fids``에서 빼고 별도 줄로 낸다: 오늘과 같은 R/G/B 줄에
    ``Attribute 'ColorRGB_W' At 0``을 이어붙인다. 값은 0 고정이다 — 이
    카드는 무대 색을 바꾸지 않는다(어느 흰색을 W로 낼지는 리드 결정
    대기, `.moai/reports/t430/verdict.md` §3). W 없이 부르면(``w_fids``
    빈 집합) 오늘과 바이트 동일하다. W 라인 없는 기구 목록이 비면 그
    줄은 아예 안 낸다.

    카드 t453 — ``white_presets``(흰색 이름 → ``(풀, 슬롯)`` 또는 못 찾은
    사유)를 주면, 흰색 큐의 W 기구에 ``At Preset`` 한 줄을 W 줄 **뒤에**
    붙인다. 콘솔은 뒤에 온 값을 쓰므로 프리셋의 RGBW 가 적용되고, 프리셋에
    값이 없는 기구는 앞 줄의 RGB 흰색을 그대로 받는다. 다음 큐의 W 기구 줄이
    늘 ``W At 0``을 적으므로 프리셋이 켠 W 는 다음 색으로 새지 않는다. 사유가
    오면 프리셋 줄 없이 오늘 줄만 내고 그 사유를 돌려준다(지어내지 않는다).
    ``None``(판독 안 함)이면 t430 동작 그대로다.
    """
    if cue.kind != "section":
        return (), None
    palette = cue.color.palette
    if not palette:
        return (), None
    name = palette[0]
    rgb = _COLOR_NAMES.resolve_color_name(name)
    if rgb is None:
        return (), f"Q{cue.cue_number:g} {cue.cue_name!r}의 색 {name!r}은 표준 팔레트 10색에 없음"
    if not w_fids:
        return (_color_apply_command(fids, rgb),), None
    rgb_only_fids = [fid for fid in fids if fid not in w_fids]
    w_only_fids = [fid for fid in fids if fid in w_fids]
    lines: list[str] = []
    if rgb_only_fids:
        lines.append(_color_apply_command(rgb_only_fids, rgb))
    if w_only_fids:
        lines.append(_color_apply_command(w_only_fids, rgb) + " ; Attribute 'ColorRGB_W' At 0")
    white = _white_palette_name(cue)
    if white is None or white_presets is None or not w_only_fids:
        return tuple(lines), None
    resolved = white_presets.get(white)
    if not isinstance(resolved, tuple):
        reason = resolved or f"{white} 프리셋 판독 결과 없음"
        return tuple(lines), f"Q{cue.cue_number:g} {cue.cue_name!r} 흰색 프리셋 미사용: {reason}"
    pool_no, slot = resolved
    lines.append(_preset_recall_command(pool_no, w_only_fids, slot))
    return tuple(lines), None


def _back_layer_value_lines(cue, layer_mapping: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """결함 6 후속 (priority 6): Front/Back 분리 연출 — the director-confirmed
    'back' role group adds ONE group-addressed dimmer line to every LIT
    section cue, at 80% of the key level (the same key→back ratio the
    composer's layered-rig path uses). The group NUMBER is console-addressable
    without membership knowledge (RG5 — fids are never claimed); blackouts and
    MIB pre-moves stay untouched. The line comes AFTER the all-fixture key
    dimmer, so the console's last-wins programmer order lowers only the back
    group."""
    back_no = next(
        (
            entry["group_no"]
            for entry in layer_mapping
            if entry.get("role") == "back" and isinstance(entry.get("group_no"), int)
        ),
        None,
    )
    if back_no is None or cue.kind != "section":
        return ()
    key_pct = cue.dimmer.key_pct
    if key_pct is None or key_pct <= 0:
        return ()
    back_pct = cue.dimmer.back_pct if cue.dimmer.back_pct is not None else key_pct * 0.8
    return (f"Group {back_no} ; Attribute 'Dimmer' At {back_pct:g}",)


def _accent_fixture_value_lines(cue, previous_fixture) -> tuple[str, ...]:
    """블라인더를 켜는 줄, 또는 앞 큐가 켠 블라인더를 끄는 줄 (카드 t462).

    콘솔은 값을 다음 큐로 이어 가므로(트래킹) 켠 블라인더는 누가 끄기 전까지
    켜진 채 남는다. 그래서 블라인더 큐 **다음** 큐(복귀 큐든 다음 구간이든)가
    같은 그룹을 0 으로 내린다. 줄은 전체 기구 밝기 줄 **뒤**에 와서 이긴다.
    """
    fixture = cue.accent_fixture
    if fixture is not None:
        return (f"Group {fixture.group_no} ; Attribute 'Dimmer' At {fixture.dimmer_pct:g}",)
    if previous_fixture is not None:
        return (f"Group {previous_fixture.group_no} ; Attribute 'Dimmer' At 0",)
    return ()


#: The placeholder title `_build_unified_song_plan` stamps on a fresh design —
#: auto-snapshots fall back to the sequence name instead of versioning it.
_DESIGN_INTERVIEW_TITLE = "Design Interview"


def _plan_edit_fx(decision: FxDecision, override: bool | None) -> FxDecision:
    """Apply a director's PLAN-stage FX on/off: off empties the allowed set
    (audited as disabled); on/None keeps the standard arc decision."""
    if override is False and decision.allowed:
        return FxDecision(allowed=(), source="director_edit", disabled=decision.allowed, density=0)
    return decision


def _section_arc_geometry(
    sections: Sequence[PositionSheetSection],
    section_origin: Sequence[int] | None,
) -> tuple[list[int], list[int], list[int], int, int]:
    """쪼갠 큐 목록을 **원래 구간** 기준의 아크 좌표로 되돌린다 (카드 t305).

    한 구간이 여러 큐로 갈려도 연출 아크(role · D 계단 · texture · FX)는
    구간 단위로 그대로여야 한다 — 정본의 Q020·Q030 은 둘 다 VERSE1 이고,
    구간이 둘로 갈렸다고 절정 위치가 옮겨 가지는 않는다.

    돌려주는 것은 큐마다 하나씩: 아크 위치(1-based), 그 구간을 여는 큐의
    번호(1-based, 재질의·미해소 보고가 쓰는 키), 구간 안에서 몇 번째
    큐인지(0 = 여는 큐), 그리고 원래 구간 수와 절정 구간 번호.

    ``section_origin`` 이 없거나 길이가 안 맞으면(계획 편집이 구간을
    넣거나 뺀 뒤) 항등으로 되돌아간다 — 쪼개기 전과 바이트 동일.
    """
    count = len(sections)
    origins = (
        list(section_origin)
        if section_origin is not None and len(section_origin) == count
        else list(range(count))
    )
    arc_positions: list[int] = []
    head_indexes: list[int] = []
    units: list[int] = []
    head_by_origin: dict[int, int] = dict()
    position_by_origin: dict[int, int] = dict()
    for offset, origin in enumerate(origins):
        if origin not in head_by_origin:
            head_by_origin[origin] = offset + 1
            position_by_origin[origin] = len(position_by_origin) + 1
        arc_positions.append(position_by_origin[origin])
        head_indexes.append(head_by_origin[origin])
        units.append(offset + 1 - head_by_origin[origin])
    originals = [sections[head_by_origin[origin] - 1] for origin in position_by_origin]
    return (
        arc_positions,
        head_indexes,
        units,
        len(position_by_origin),
        _climax_section_index(originals),
    )


#: 카드 t445 — 후렴 분할 큐의 주색을 고정하지 **않는** 곡별 선택(Q2B).
#: ``per_chorus`` 는 회차마다 색을 바꾸는 선택이라 기존 회전을 그대로 두고,
#: ``split_swap`` 은 한 후렴 안에서 주·보조색을 맞바꾸는 t305 동작 그 자체다.
_SPLIT_PRIMARY_UNPINNED_USAGES = frozenset({"per_chorus", "split_swap"})


def _pins_split_primary(role: str, color_usage: str) -> bool:
    """카드 t445 — 이 역할의 마디 분할 큐가 주색을 고정하는가.

    감독 결정 2026-09-23 「기본은 후렴 주색 고정, 곡마다 선택」(REQ-LDDESIGN-030).
    후렴(chorus/finale)만 해당하고, verse 등 다른 역할의 분할 회전은 그대로다.
    """
    return role in ("chorus", "finale") and color_usage not in _SPLIT_PRIMARY_UNPINNED_USAGES


def _build_unified_song_plan(
    *,
    sections: Sequence[PositionSheetSection],
    profile: MusicProfile,
    rig: object,
    records: Sequence[object],
    timing: TimingPlan,
    sequence_no: int,
    requery_overrides: Mapping[int, DirectorOverride] | None = None,
    palette_mode: str = "palette",
    concept_colors: tuple[str, ...] = (),
    fade_overrides: Mapping[int, float] | None = None,
    fx_overrides: Mapping[int, bool] | None = None,
    section_origin: Sequence[int] | None = None,
    position_disabled_reason: str = "",
    blinder_group_no: int | None = None,
) -> UnifiedSongLightingPlan:
    arc_positions, head_indexes, units, section_count, climax_index = _section_arc_geometry(
        sections, section_origin
    )
    # 카드 t402·t403 — 역할이 같은 구간이 반복될 때(코러스 25회 등) 몇 번째
    # 회차인지 미리 센다. 원본(origin) 단위로 세야 한다 — 마디 분할로 갈린
    # 큐는 부모와 같은 회차를 공유해야, 부모가 이미 정한 팔레트 회전·액센트
    # 사다리가 자식 큐에서 흔들리지 않는다. `head_indexes[i] == i+1` 인
    # 자리(``units[i] == 0``)만 새 원본의 시작이다.
    origin_roles: dict[int, str] = {}
    for offset, section in enumerate(sections, start=1):
        if units[offset - 1] == 0:
            arc_index = arc_positions[offset - 1]
            origin_roles[head_indexes[offset - 1]] = _section_role(
                section, section_index=arc_index, section_count=section_count
            )
    role_totals: dict[str, int] = {}
    for role_name in origin_roles.values():
        role_totals[role_name] = role_totals.get(role_name, 0) + 1
    role_running: dict[str, int] = {}
    occurrence_by_head: dict[int, int] = {}
    for head in sorted(origin_roles):
        role_name = origin_roles[head]
        role_running[role_name] = role_running.get(role_name, 0) + 1
        occurrence_by_head[head] = role_running[role_name]
    # SPEC-COPILOT-COLORMODE-001 — Q2B_COLOR_USAGE decision, read once for
    # the whole plan (default "modulate" when unanswered, matching modulate
    # being the interview's recommended/first option).
    color_usage = _record_value(records, Q2B_COLOR_USAGE, "modulate")
    decisions: list[SectionDecision] = []
    unresolved: list[UnresolvedNote] = []
    roles: list[str] = []
    for index, section in enumerate(sections, start=1):
        arc_index = arc_positions[index - 1]
        head_index = head_indexes[index - 1]
        unit_index = units[index - 1]
        role = _section_role(section, section_index=arc_index, section_count=section_count)
        roles.append(role)
        # 카드 t402·t403 — 이 원본(head_index)이 자기 역할 안에서 몇 번째
        # 회차인지(사전 계산한 표에서 조회), 그 역할의 총 회차 수, 그리고
        # 그것이 **마지막** 회차인지.
        occurrence = occurrence_by_head.get(head_index, 1)
        total_for_role = role_totals.get(role, 0)
        is_final_occurrence = occurrence == total_for_role
        override = _section_director_override(
            section_index=arc_index,
            section_count=section_count,
            records=records,
            climax_index=climax_index,
        )
        # Priority (결함 4): 구간 재질의 답변 > 구간 직접 자연어 의도 > Q3/Q4.
        merged = (requery_overrides or {}).get(head_index)
        if merged is not None:
            override = merged
        else:
            direct_positions = _direct_position_intent(f"{section.name} {section.mood}")
            if direct_positions is not None:
                override = (
                    replace(override, position_candidates=direct_positions)
                    if override is not None
                    else DirectorOverride(position_candidates=direct_positions)
                )
        resolved = resolve_section(section.mood, profile, director_intent=override)
        if isinstance(resolved, UnresolvedMood):
            # 한 구간을 여러 큐로 쪼갰어도 감독에게는 카드가 **한 번** 떠야
            # 한다 — 같은 구간의 같은 무드를 큐 수만큼 되묻는 것은 잡음이다.
            if unit_index == 0:
                unresolved.append(
                    UnresolvedNote(
                        axis=POSITION_AXIS,
                        section_index=head_index,
                        reason=resolved.reason,
                        prompt=_unresolved_prompt(section, resolved.reason),
                    )
                )
            fallback = resolve_section(None, profile, director_intent=override)
            if not isinstance(fallback, SectionMoodResolution):
                fallback = SectionMoodResolution(
                    d_level=3,
                    color_tendency="white",
                    position_candidates=("Home",),
                    d_source="fallback",
                    color_source="fallback",
                    position_source="fallback",
                )
            resolved = fallback
        position = resolved.position_candidates[0] if resolved.position_candidates else "Home"
        # D-level: arc replaces only undecided defaults — a mood-word or
        # director tier keeps its value.
        d_level, d_source = resolved.d_level, resolved.d_source
        # 카드 t383 — 확정 분석이 잰 D 레벨(``section.d_level``)은 아직 아무도
        # 결정하지 않은 구간에서만 기본값을 채운다. 무드 단어나 감독 답변
        # (Q3 절정 포함, ``resolve_section`` 이 이미 SOURCE_DIRECTOR_INTENT 로
        # 최우선 처리했다)이 이미 정했으면 그 값을 덮지 않는다 — 여기서
        # 고치는 것은 「비어서 전역 기본값(D3)으로 떨어진」 구간뿐이다.
        if section.d_level is not None and d_source in (SOURCE_GLOBAL_DEFAULT, "fallback"):
            d_level, d_source = section.d_level, "confirmed_song_analysis"
        arc_d = _ARC_D_LEVEL.get(role)
        if arc_d is not None and d_source in (SOURCE_GLOBAL_DEFAULT, "fallback"):
            d_level, d_source = arc_d, "section_arc"
        # Palette: section's own color words > palette-conflict choice > Q2
        # palette blended with the role arc.
        palette_colors, palette_source, palette_weight = _section_palette_choice(
            section,
            role=role,
            profile=profile,
            color_tendency=resolved.color_tendency,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            occurrence=occurrence,
            color_usage=color_usage,
        )
        # 카드 t305 — 구간 안에서 이어지는 큐는 앞 큐와 **달라야** 한다.
        # 정본이 하는 것과 같은 축: 강도는 유지하고 색만 돌린다(Q060 "강도
        # 유지, 색만 교체" · Q140 "색상만 순환"). 색이 하나뿐인 구간은
        # 애초에 쪼개지지 않으므로(`plan_cue_density`) 여기서 같은 큐가
        # 나오는 일은 없다.
        # 카드 t398 — 회전은 이미 고른 색을 순서만 바꾼다(원소 추가 없음), 그래서
        # `palette_source` 는 **덮어쓰지 않는다**. 예전에는 여기서
        # "cue_density_rotation" 으로 갈아끼웠는데, 그러면 L5 가 아크 악센트인지
        # 감독 문구인지 구분할 근거(원래 출처)를 잃는다 — 이 리터럴은 코드베이스
        # 전체에서 이 한 줄이 유일한 생산자였다(다른 소비자 없음, grep 확인).
        # 카드 t445 — 기본(modulate)·single 의 후렴은 주색을 고정하고 보조색만
        # 돌린다. 한 후렴 안에서 주·보조색을 맞바꾸는 것은 감독이 곡마다 고르는
        # ``split_swap``(와 ``per_chorus``)일 때뿐이다.
        if unit_index > 0:
            if _pins_split_primary(role, color_usage) and palette_colors:
                rotated = (palette_colors[0], *rotate_palette(palette_colors[1:], unit_index))
            else:
                rotated = rotate_palette(palette_colors, unit_index)
            if rotated != palette_colors:
                palette_colors = rotated
        decisions.append(
            SectionDecision(
                section=TimestampedSection(
                    index=index,
                    label=section.name,
                    start_ms=section.start_ms,
                    source="song_design_interview",
                ),
                d=DLevelDecision(level=d_level, source=d_source),
                palette=PaletteDecision(
                    colors=palette_colors, source=palette_source, weight=palette_weight
                ),
                position=PositionDecision(
                    preset=position,
                    source=resolved.position_source,
                    candidates=resolved.position_candidates,
                ),
                texture=_section_texture_decision(
                    section=section,
                    section_index=arc_index,
                    climax_index=climax_index,
                    section_count=section_count,
                    records=records,
                ),
                fx=_plan_edit_fx(
                    _section_fx_decision(
                        section=section,
                        section_index=arc_index,
                        climax_index=climax_index,
                        section_count=section_count,
                        records=records,
                        occurrence=occurrence,
                    ),
                    (fx_overrides or {}).get(index),
                ),
                accent=_accent_decision(
                    records,
                    section_index=arc_index,
                    climax_index=climax_index,
                    role=role,
                    occurrence=occurrence,
                    total_for_role=total_for_role,
                    is_final_occurrence=is_final_occurrence,
                ),
                cue_number=index,
                fade_override=(fade_overrides or {}).get(index),
                role=role,
            )
        )
    # Invariant (결함 3): the finale never lands below the first chorus.
    chorus_levels = [
        decision.d.level
        for decision, role in zip(decisions, roles, strict=True)
        if role == "chorus"
    ]
    if chorus_levels:
        floor = max(chorus_levels)
        for slot, (decision, role) in enumerate(zip(decisions, roles, strict=True)):
            if role == "finale" and decision.d.level < floor:
                decisions[slot] = replace(
                    decision, d=DLevelDecision(level=floor, source="section_arc_invariant")
                )
    disabled = tuple(DisabledNote(axis=FX_AXIS, reason=note) for note in getattr(rig, "notes", ()))
    # 카드 t311 — 좌표가 없으면 포지션 축은 **전곡** 비활성이다(구간별이 아니라).
    # 이 노트 하나가 작곡기·리뷰·타임라인 셋 모두의 판별기가 된다 — 축을 끈
    # 사실과 그 사유가 한 곳에만 적힌다.
    if position_disabled_reason:
        disabled = (*disabled, DisabledNote(axis=POSITION_AXIS, reason=position_disabled_reason))
    return UnifiedSongLightingPlan(
        song_title=_DESIGN_INTERVIEW_TITLE,
        sequence_name=f"Sequence {sequence_no}",
        sections=tuple(decisions),
        timing=timing,
        music_profile=profile,
        rig_profile=rig,
        approval=ApprovalState.pending(reviewer="director"),
        director_decisions=_director_decisions(records),
        unresolved=tuple(unresolved),
        disabled=disabled,
        blinder_group_no=blinder_group_no,
    )


def _preset_recall_command(pool_no: int, fids: Sequence[int], preset_no: int) -> str:
    """``Fixture <fids> ; At Preset <pool>.<n>`` — 풀 일반형 recall 명령 빌더.

    ``pointing.preset_recall_command``의 문면·규칙(양수 preset_no, 빈 fids
    거부)을 임의 풀 번호에 적용한다 — ``_preset_store_commands``와 같은 세션
    계층 일반화(REQ-COLORPRESET-007, pool_no=2 출력은 문자 단위로 동일)이고,
    실측 문법 출처는 T11 프로브 §2(Color/Dimmer/All 1 3풀 전부 수락)다.
    """
    if not isinstance(pool_no, int) or isinstance(pool_no, bool) or pool_no <= 0:
        # 대칭 검증 — _preset_store_commands와 같은 이유(SEC-CMD-003).
        raise SpatialPointingError(f"pool number {pool_no!r} must be a positive integer")
    if preset_no <= 0:
        raise SpatialPointingError(f"preset number {preset_no!r} must be positive")
    if not fids:
        raise SpatialPointingError("no fixtures to recall the preset on")
    selection = " + ".join(str(fid) for fid in fids)
    return f"Fixture {selection} ; At Preset {pool_no}.{preset_no}"


def _color_apply_command(fids: Sequence[int], rgb: tuple[int, int, int]) -> str:
    """한 색을 컬러 가능 장비 전체에 싣는 **한 줄** 체인 (spec §B REQ-003).

    ``aimed_commands``의 한 줄 규율과 같은 이유(텍스트 중복 제거 방어)로
    선택과 세 어트리뷰트를 ``;``로 묶는다 — 문법은 룰북 라이브 검증분만
    (``Attribute 'ColorRGB_R' At <0-100>``, G/B 동일).
    """
    selection = " + ".join(str(fid) for fid in fids)
    r, g, b = rgb
    return (
        f"Fixture {selection} ; Attribute 'ColorRGB_R' At {r} ; "
        f"Attribute 'ColorRGB_G' At {g} ; Attribute 'ColorRGB_B' At {b}"
    )


def reviewed_song_commands(
    bundle,
    *,
    sequence_no: int,
    fids: Sequence[int],
    timing: TimingPlan,
    position_slots: Mapping[str, int],
    phaser_slots: Mapping[str, tuple[int, int]],
    white_presets: Mapping[str, tuple[int, int] | str] | None,
    layer_mapping: Sequence[Mapping[str, object]] = (),
    w_fids: frozenset[int] = frozenset(),
) -> tuple[tuple[str, ...], dict[str, str]]:
    """조립기 번들 → 콘솔 명령 ``(commands, color_failures)`` — 카드 t480.

    원래 ``ChatSession._reviewed_song_commands`` 의 반복문이다. 콘솔에서 찾아야
    하는 슬롯(포지션 라벨 → 프리셋 번호, 페이저 라벨 → 슬롯, 흰색 프리셋)은
    호출자가 미리 찾아 넘긴다 — 이 함수는 콘솔을 읽지 않는다. 대화 길과 업로드
    길이 같은 명령 모양을 내는 자리가 이 함수 하나다.
    """
    color_failures: dict[str, str] = {}
    commands: list[str] = ["ChangeDestination Root"]
    # 카드 t462 — 앞 저장 큐가 켠 블라인더(다음 큐가 끈다).
    previous_fixture = None
    for cue in bundle.cues:
        preset_no = None
        if cue.position.stored is not None:
            preset_no = position_slots[cue.position.stored]
        dimmer = cue.dimmer.key_pct
        color_lines, color_failure = _song_color_value_lines(cue, fids, w_fids, white_presets)
        if color_failure is not None:
            color_failures[f"{cue.cue_number:g}"] = color_failure
        if preset_no is None and dimmer is None:
            continue
        accent_lines = _accent_fixture_value_lines(cue, previous_fixture)
        previous_fixture = cue.accent_fixture
        plan = PositionCuePlan(
            cue_no=cue.cue_number,
            name=_safe_song_cue_name(cue.cue_name, cue.cue_number),
            preset_no=preset_no,
            dimmer=dimmer,
            fade_seconds=cue.fade_seconds,
            premove=cue.kind == "mib_premove",
        )
        commands.extend(
            position_cue_bundle(
                sequence_no,
                plan,
                fids,
                extra_value_lines=(
                    *color_lines,
                    *_back_layer_value_lines(cue, layer_mapping),
                    *_phaser_cue_value_lines(cue, fids, phaser_slots),
                    *accent_lines,
                ),
            )
        )
        if plan.premove:
            commands.append(premove_follow_command(sequence_no, plan))
    commands.extend(reviewed_song_timing_commands(bundle, sequence_no, timing))
    return tuple(commands), color_failures


def reviewed_song_timing_commands(
    bundle,
    sequence_no: int,
    timing: TimingPlan,
) -> tuple[str, ...]:
    """조립기 번들의 타이밍 명령(타임코드·큐 타임) — 카드 t480, 원래 세션 메서드."""
    plan = reviewed_song_timing(bundle, sequence_no, timing)
    return () if plan is None else plan.commands


def reviewed_song_timing(
    bundle,
    sequence_no: int,
    timing: TimingPlan,
    *,
    axes: SongCueTimingAxes | None = None,
) -> SongCueTimingPlan | None:
    """조립기 번들의 타이밍 계획 전체 — 명령·타임코드/자동진행 갈래·건너뛴 축.

    카드 t480 — 업로드 길은 명령만이 아니라 갈래별 목록과 건너뛴 축까지 회신에
    싣는다. ``axes`` 는 업로드 길이 타임코드 슬롯 점검에서 잰 값이고, 대화 길은
    넘기지 않는다(``None`` 이면 옮기기 전과 같은 호출). 수동 Go 이거나 타임코드
    번호가 없으면 ``None``.
    """
    if timing.mode == "manual_go":
        return None
    sections: list[SongCueSectionBundle] = []
    # 카드 t462 — 절정 복귀 큐도 시각을 갖고 타이밍에 실린다(``timed_cues``).
    for cue in bundle.timed_cues:
        if cue.timing.start_ms is None:
            continue
        section = SongCueSection(
            name=cue.cue_name,
            start_ms=cue.timing.start_ms,
            index=cue.section_index - 1,
            dynamics=(cue.d_level,),
            requires_explicit_dynamics=False,
        )
        selection = SongCueLookSelection(section=section, requested_dynamics=(cue.d_level,))
        sections.append(
            SongCueSectionBundle(
                section=section,
                # 정수 큐는 전과 같은 글자(`Set Cue 4`), 복귀 큐만 소수(`Set Cue 4.5`).
                cue_number=(
                    int(cue.cue_number) if float(cue.cue_number).is_integer() else cue.cue_number
                ),
                cue_name=_safe_song_cue_name(cue.cue_name, cue.cue_number),
                selection=selection,
                commands=("reviewed",),
            )
        )
    timing_bundle = TimingSongCueBundle(
        song_title=bundle.song_title,
        sequence_number=sequence_no,
        sequence_name=bundle.sequence_name or f"Sequence {sequence_no}",
        commands=("reviewed",),
        sections=tuple(sections),
    )
    if timing.mode == "trig_time":
        return build_songcue_timing(
            timing_bundle,
            timecode_number=1,
            axes=SongCueTimingAxes(timecode_go=False, auto_advance_go=True),
        )
    if timing.timecode_number is None:
        return None
    if axes is None:
        return build_songcue_timing(timing_bundle, timecode_number=timing.timecode_number)
    return build_songcue_timing(timing_bundle, timecode_number=timing.timecode_number, axes=axes)


#: 카드 t396 — bridge 로 볼 수 있는 **절대** 상한. 정본 6절 표가 breakdown·bridge 를
#: 20~35% 대역에 두므로 D1·D2 만 해당한다. 이웃 대비(상대) 조건만 쓰면 두 방향으로
#: 틀렸다(실측 2026-09-15, 감독 음원 8곡): 밝은 D4 가 이웃보다 낮다는 이유로 bridge 가
#: 되고(5건), 낮은 구간이 둘 연속이면 서로가 서로의 이웃이 되어 조건이 깨져 verse 로
#: 남았다(4건). 절대 대역으로 바꾸면 두 방향이 함께 닫힌다 — t371·t375 가 같은 계열의
#: 실수를 상대 문턱에 절대 대역을 섞어 고친 그 처방이다.
_BRIDGE_MAX_D_LEVEL = 2


def _infer_confirmed_role(index: int, d_levels: Sequence[int]) -> str:
    """오디오 확정 구간 하나의 아크 역할을 D 레벨만으로 추정한다 (카드 t393).

    이름·무드가 비어 있어 ``_section_role`` 의 자연어 판독이 닿지 않는 구간을
    위한 대체 판정기다. ``_ARC_D_LEVEL``(intro 2 · verse 3 · chorus 5 ·
    bridge 2 · finale 5)의 역표를 그대로 따른다: 첫 구간은 intro, 마지막
    구간은 finale, 최고 D 레벨 구간은(동률 허용) chorus, :data:`_BRIDGE_MAX_D_LEVEL`
    이하의 낮은 대역은 bridge, 나머지는 verse. 순전히 서수·측정값 기반이라 무드
    단어를 지어내지 않는다.

    bridge 판정은 **절대 대역**이다(카드 t396). 이웃 대비만 보던 앞선 규칙은 밝은
    구간을 bridge 로 오인하고 연속 저강도 구간을 놓쳤다 — 근거는
    :data:`_BRIDGE_MAX_D_LEVEL` 주석의 실측이다.
    """
    count = len(d_levels)
    if count == 0:
        return "other"
    if index == 0:
        return "intro"
    if index == count - 1:
        return "finale"
    level = d_levels[index]
    if level >= max(d_levels):
        return "chorus"
    if level <= _BRIDGE_MAX_D_LEVEL:
        return "bridge"
    return "verse"


#: 카드 t391 — 역할 → 표시 이름 앞머리. 콘솔 큐 목록이 이미 쓰는 어휘
#: (Intro / Verse N / Chorus N / Bridge N / Finale, 감독 실측)와 맞춘다.
#: `_infer_confirmed_role` 이 내는 역할 5종만 다루면 되므로 "other" 는
#: 방어적으로만 존재한다 — 확정 구간 경로에서는 나오지 않는다.
_CONFIRMED_ROLE_DISPLAY_NAME: dict[str, str] = {
    "intro": "Intro",
    "verse": "Verse",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "finale": "Finale",
    "other": "Section",
}


#: 이 역할은 곡에 한 번뿐이라 뒤에 회차 번호를 붙이지 않는다 — "Intro 1" 은
#: 감독 화면의 콘솔 큐 이름(Intro / Verse 1 / Verse 2 / ...)과 다른 어휘가
#: 된다.
_CONFIRMED_ROLE_SINGLETON = frozenset({"intro", "finale"})


def _confirmed_section_names(roles: Sequence[str]) -> list[str]:
    """오디오 확정 구간의 표시 이름 — 역할 + 회차 번호 (카드 t391).

    고침 전: 이름이 전부 중립 ASCII ``S<n>`` 이라 곡 하나에 같은 라벨이
    중복됐다(실측: 17개 라벨 중 8번째·9번째가 둘 다 ``S8`` — 마디 분할이
    한 구간을 두 큐로 쪼개면서 부모 이름을 그대로 물려받았기 때문). 콘솔의
    큐 목록은 같은 화면에서 ``Intro / Verse 1 / Verse 2 / Chorus 1 ...``
    처럼 역할+회차로 감독이 하나를 짚을 수 있게 이름 붙인다 — 이 함수는
    확정 구간에도 같은 어휘를 쓴다.

    ``dynamics``(D 레벨)는 이 이름과 **무관한 경로**로 전달된다
    (``_confirmed_section_input`` 의 ``dynamics`` 키, ``_map_section_to_look``
    이 명시 dynamics 를 이름보다 먼저 본다) — 그래서 이름을 "Chorus 1" 로
    바꿔도 D 레벨 판정을 우회하지 않는다(plan.md §C D5 가 지키려던 것과
    같은 불변식).

    지시문이 직접 구간을 적은 경로(``section_names``)는 이 함수를 타지
    않는다 — 그 경로는 이미 감독이 준 이름이 정본이다.
    """
    occurrence: dict[str, int] = {}
    names: list[str] = []
    for role in roles:
        prefix = _CONFIRMED_ROLE_DISPLAY_NAME.get(role, role.title() or "Section")
        if role in _CONFIRMED_ROLE_SINGLETON:
            names.append(prefix)
            continue
        occurrence[role] = occurrence.get(role, 0) + 1
        names.append(f"{prefix} {occurrence[role]}")
    return names


def _disambiguate_split_names(names: Sequence[str], source_origins: Sequence[int]) -> list[str]:
    """마디 분할로 한 구간이 여러 큐로 갈리면 라벨을 서로 다르게 만든다
    (카드 t391). ``plan_cue_density`` 는 시작 시각만 갈라 주고 이름은 부모
    구간 것을 그대로 물려주므로(``replace(sections[split.source_index], ...)``
    이 ``name`` 은 안 바꾼다), 같은 이름이 연달아 여러 번 나올 수 있다 —
    이 함수가 그 자리에만 회차 접미사(" (2/2)" 형태)를 붙인다. 쪼개지지
    않은 구간(부모당 큐 하나)의 이름은 바이트 그대로 둔다.
    """
    counts: dict[int, int] = {}
    for origin in source_origins:
        counts[origin] = counts.get(origin, 0) + 1
    seen: dict[int, int] = {}
    disambiguated: list[str] = []
    for name, origin in zip(names, source_origins, strict=True):
        total = counts[origin]
        if total <= 1:
            disambiguated.append(name)
            continue
        seen[origin] = seen.get(origin, 0) + 1
        disambiguated.append(f"{name} ({seen[origin]}/{total})")
    return disambiguated


#: 카드 t462 — 블라인더 그룹으로 인정하는 콘솔 그룹 이름(정확 일치만, RG5).
#: `server/design/rig.py` 의 `_LAYER_GROUP_ALIASES` 는 BLIND 를 STROBE·HAZE 와 같은
#: ``effect`` 역할로 묶으므로(2026-09-15 감독 답), 역할만으로는 블라인더를 가를 수
#: 없어 이름을 한 번 더 본다.
_BLINDER_GROUP_NAMES = frozenset({"blind", "blinder"})


def _blinder_group_no(layer_mapping: Sequence[Mapping[str, object]]) -> int | None:
    """콘솔이 보고한 그룹 중 이름이 BLIND/BLINDER 와 정확히 같은 그룹 번호 (카드 t462)."""
    for entry in layer_mapping or ():
        name = str(entry.get("group_name") or "").strip().casefold()
        number = entry.get("group_no")
        if name in _BLINDER_GROUP_NAMES and isinstance(number, int) and number > 0:
            return number
    return None


def _section_palette_sizes(
    sections: Sequence[PositionSheetSection],
    *,
    profile: MusicProfile,
    palette_mode: str,
    concept_colors: tuple[str, ...],
    color_usage: str = "modulate",
) -> list[int]:
    """구간별 팔레트 색 수 — 쪼갠 큐가 서로 달라질 수 있는지의 판정 재료.

    감독 재질의 답변(``requery_overrides``)은 아직 없는 시점이라 여기서는
    보지 않는다. 오버라이드는 색을 **더하는** 쪽이므로 이 값은 실제보다
    작거나 같다 — 즉 이 판정은 덜 쪼개는 쪽으로만 틀린다. 같은 큐 둘을
    내는 것보다 안 쪼개는 쪽이 낫다는 카드의 방향과 같다.

    ``color_usage`` — SPEC-COPILOT-COLORMODE-001. 실제 산출(`_section_palette_choice`)
    과 어긋나지 않도록 여기도 같은 값을 전달한다(research.md §6).
    """
    count = len(sections)
    sizes: list[int] = []
    for index, section in enumerate(sections, start=1):
        role = _section_role(section, section_index=index, section_count=count)
        resolved = resolve_section(section.mood, profile, director_intent=None)
        tendency = getattr(resolved, "color_tendency", "white")
        colors, _source, _weight = _section_palette_choice(
            section,
            role=role,
            profile=profile,
            color_tendency=tendency,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            color_usage=color_usage,
        )
        # 카드 t445 — 주색을 고정하는 후렴은 보조색만 돌므로, 쪼갤 수 있는지도
        # 보조색 개수로 센다. 2색 팔레트면 돌릴 것이 없어 쪼개지 않는다.
        pinned = _pins_split_primary(role, color_usage) and len(colors) > 1
        sizes.append(len(colors) - 1 if pinned else len(colors))
    return sizes


def _split_sections_for_density(
    sections: Sequence[PositionSheetSection],
    *,
    profile: MusicProfile,
    palette_mode: str = "palette",
    concept_colors: tuple[str, ...] = (),
    color_usage: str = "modulate",
    song_end_ms: int | None = None,
) -> tuple[list[PositionSheetSection], list[int], tuple[str, ...]]:
    """구간 목록을 마디 경계에서 쪼갠 큐 목록으로 넓힌다 (카드 t305).

    돌려주는 것은 (넓힌 구간 목록, 큐마다의 원래 구간 번호, 공개할 사유).
    BPM 이 선언되지 않았으면 입력이 그대로 나온다 — 오늘과 동일.

    카드 t480 — ``song_end_ms`` 를 주면 **마지막 구간도** 쪼갠다. 대화 길은 곡 끝을
    모르므로 넘기지 않는다(``None`` — 옮기기 전과 같다). 업로드 길의 확정 분석 기록은
    구간마다 ``end_ms`` 를 들고 있어, 옛 업로드 길(t306)이 하던 대로 넘긴다.

    카드 t391 — 한 구간이 여러 큐로 갈리면(``plan.splits`` 에서 같은
    ``source_index`` 가 둘 이상) 부모 이름을 그대로 물려받아 라벨이
    중복됐다(실측: 17개 라벨 중 8번째·9번째가 둘 다 ``S8``). 이름이
    바뀌는 구간은 쪼개진 자리에 한해서만이고, 쪼개지지 않은 구간의
    이름은 바이트 그대로 둔다(``_disambiguate_split_names``).
    """
    plan = plan_cue_density(
        [section.start_ms for section in sections],
        bpm=profile.bpm,
        meter=profile.meter,
        palette_sizes=_section_palette_sizes(
            sections,
            profile=profile,
            palette_mode=palette_mode,
            concept_colors=concept_colors,
            color_usage=color_usage,
        ),
        song_end_ms=song_end_ms,
    )
    source_origins = list(plan.source_origins)
    names = _disambiguate_split_names(
        [sections[split.source_index].name for split in plan.splits], source_origins
    )
    expanded = [
        replace(sections[split.source_index], start_ms=split.start_ms, name=name)
        for split, name in zip(plan.splits, names, strict=True)
    ]
    return expanded, source_origins, plan.notes
