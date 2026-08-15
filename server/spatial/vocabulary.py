"""Deterministic Korean vocabulary for explicit 3D fixture arrangements.

This module recognizes only an operator's explicit geometry request. It never
infers fixture targets: callers must still resolve a complete, console-read FID
list before making a write request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

LayoutPreset = Literal["grid", "row", "circle"]


# Operator-facing aliases. Values are the deterministic action or the required
# disambiguation; no term silently selects fixtures or invents a geometry.
LAYOUT_VOCABULARY: dict[str, tuple[str, ...]] = {
    "alternate_order": ("번갈아", "홀짝", "1/2"),
    "paired_types": ("짝지어", "다른 장비끼리", "페어"),
    "left_to_right": ("좌-->우", "좌→우", "왼쪽부터 오른쪽", "좌우"),
    "front_to_back": ("앞-->뒤", "앞→뒤", "앞에서 뒤", "전후"),
    "semicircle": ("반원", "세미서클"),
    "rectangle": ("사각형", "직사각형"),
    "triangle": ("삼각형",),
    "diamond": ("마름모", "다이아몬드"),
    "floor_height": ("바닥 위", "바닥으로부터"),
    "stage_height": ("무대 위", "무대 바닥 위"),
    "height_step": ("높이 간격", "간격으로 높이", "층간격"),
}


@dataclass(frozen=True)
class LayoutVocabularyMatch:
    """A recognized layout intent and its explicit geometry parameters."""

    preset: LayoutPreset
    rows: int | None = None
    columns: int | None = None
    spacing: float | None = None
    radius: float | None = None


RingKind = Literal["mmx", "beam", "remainder"]


@dataclass(frozen=True)
class RingSpec:
    """One ring of a multi-ring circle request, in innermost-first order."""

    kind: RingKind
    count: int | None = None
    alternate: bool = False


_MULTI_RING_CIRCLE = re.compile(
    r"(?:여러\s*겹|여러\s*개|겹겹).*원|원.*(?:여러\s*겹|여러\s*개)|\d+\s*번째\s*원",
    re.IGNORECASE,
)
_RING_MARKER = re.compile(r"안쪽|바깥|마지막|\d+\s*번째|원", re.IGNORECASE)
_BEAM_NAME = re.compile(r"rlb\s*350|350", re.IGNORECASE)


def parse_ring_layout(text: str) -> tuple[RingSpec, ...] | None:
    """Parse a multi-ring circle request into ordered ring specs.

    Returns ``None`` when the request is not a multi-ring circle. Each clause
    (split on Korean sentence/comma punctuation) that names a ring contributes
    one :class:`RingSpec`; the intro clause ("여러 겹의 원형으로 배치할거야")
    carries no type/count/remainder and is skipped. Fixture TARGETS are never
    invented here — the caller resolves real FIDs from a console read.
    """
    if _MULTI_RING_CIRCLE.search(text) is None:
        return None
    rings: list[RingSpec] = []
    for clause in re.split(r"[,.\n]", text):
        c = clause.strip()
        if not c or _RING_MARKER.search(c) is None:
            continue
        remainder = re.search(r"남은|나머지", c) is not None
        alternate = re.search(r"번갈아|홀짝|교대", c) is not None
        count_match = re.search(r"(\d+)\s*대", c)
        count = int(count_match.group(1)) if count_match else None
        kind: RingKind | None = None
        if "mmx" in c.casefold():
            kind = "mmx"
        elif _BEAM_NAME.search(c):
            kind = "beam"
        if remainder:
            kind = "remainder"
        if kind is None and count is None:
            continue  # a ring-ish clause with no concrete spec (e.g. the intro)
        rings.append(RingSpec(kind=kind or "remainder", count=count, alternate=alternate))
    return tuple(rings) or None


_ALL_FIXTURES = re.compile(
    r"(?:모든|전체|전부).*(?:장비|픽스처|fixture)"
    r"|(?:장비|픽스처|fixture).*(?:모든|전체|전부)",
    re.IGNORECASE,
)
_ALL_MARKER = re.compile(r"(?:모든|전체|전부)", re.IGNORECASE)
_ACTION = re.compile(r"(?:배치|배열|정렬|놓아|놓아줘|놓고|이동)", re.IGNORECASE)


def recognized_layout_terms(text: str) -> tuple[str, ...]:
    """Return vocabulary categories present in a request, in catalog order."""
    lowered = text.casefold()
    return tuple(
        category
        for category, aliases in LAYOUT_VOCABULARY.items()
        if any(alias.casefold() in lowered for alias in aliases)
    )


# What each vocabulary category still NEEDS to become an executable arrangement.
# Surfaced to the model as reasoning guidance — not a canned reply — so it
# reasons about the whole request and asks only for what is genuinely missing.
_TERM_REQUIREMENTS: dict[str, str] = {
    "alternate_order": "번갈아/홀짝은 기준 순서(좌→우 또는 앞→뒤, 또는 FID 오름차순)가 필요",
    "paired_types": "짝지어는 짝지을 두 장비 타입 또는 두 그룹이 필요",
    "left_to_right": "좌→우는 각 슬롯을 차지하는 순서",
    "front_to_back": "앞→뒤는 각 슬롯을 차지하는 순서",
    "semicircle": "반원은 반지름과 시작 각도가 필요",
    "rectangle": "사각형은 행×열이 필요",
    "triangle": "삼각형은 변당 대수 또는 꼭짓점 방향이 필요",
    "diamond": "마름모는 대각 길이 또는 변당 대수가 필요",
    "floor_height": "바닥 위 높이는 절대 z 값(미터)이 필요",
    "stage_height": "무대 위 높이는 절대 z 값(미터)이 필요",
    "height_step": "층간 높이는 기준 높이와 대상 순서가 필요",
}


def layout_terms_guidance(text: str) -> str:
    """Reasoning guidance for the layout vocabulary present in ``text``.

    Returns an empty string when no term is recognized. The model receives this
    so it can REASON about the full request and, if a parameter is truly
    missing, ask one question at a time via ask_user — replacing the reflexive
    canned clarifier that fired on a keyword alone.
    """
    needs = [
        _TERM_REQUIREMENTS[category]
        for category in recognized_layout_terms(text)
        if category in _TERM_REQUIREMENTS
    ]
    if not needs:
        return ""
    return (
        "Session context — the request uses layout vocabulary that needs "
        "parameters: " + "; ".join(needs) + ". Reason about the WHOLE request, "
        "reuse anything already given, and if a value is genuinely missing ask "
        "for it with ask_user (one question at a time, options as buttons) "
        "instead of a canned line."
    )


_GRID = re.compile(r"(?:바둑판|그리드|grid|매트릭스)", re.IGNORECASE)
_ROW = re.compile(r"(?:일렬|한[\s-]*줄|라인|row|줄\s*세워)", re.IGNORECASE)
_CIRCLE = re.compile(r"(?:원형|원[\s-]*형|원으로|링|circle|ring|동그랗게|둥글게)", re.IGNORECASE)
_GRID_SIZE = re.compile(r"(?P<rows>\d+)\s*행\s*(?:[×xX*]\s*)?(?P<columns>\d+)\s*열")
_SPACING = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?:m|미터)\s*(?:간격|spacing)",
    re.IGNORECASE,
)
_RADIUS = re.compile(
    r"(?:반지름|radius)\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?:m|미터)?",
    re.IGNORECASE,
)


def _metres(match: re.Match[str] | None) -> float | None:
    if match is None:
        return None
    return float(match.group("value").replace(",", "."))


def match_explicit_layout(text: str) -> LayoutVocabularyMatch | None:
    """Match a fully addressed Korean layout request without model inference.

    The request must name all fixtures and an arrangement verb. A grid also
    needs an explicit rows×columns shape; row and circle use the tool's
    documented safe defaults when spacing/radius is omitted.
    """
    if _ALL_FIXTURES.search(text) is None and _ALL_MARKER.search(text) is None:
        return None
    if _ACTION.search(text) is None:
        return None

    spacing = _metres(_SPACING.search(text))
    if _GRID.search(text):
        dimensions = _GRID_SIZE.search(text)
        if dimensions is None:
            return None
        return LayoutVocabularyMatch(
            preset="grid",
            rows=int(dimensions.group("rows")),
            columns=int(dimensions.group("columns")),
            spacing=spacing,
        )
    if _ROW.search(text):
        return LayoutVocabularyMatch(preset="row", spacing=spacing)
    if _CIRCLE.search(text):
        return LayoutVocabularyMatch(preset="circle", radius=_metres(_RADIUS.search(text)))
    return None
