"""격자 「모양」 비교 — 자동 배치 결과를 손으로 설계한 기본 격자와 숫자로 견준다.

SPEC-LDRHYTHM-001 검증 도구. 격자 두 개를 받아 줄(트랙)마다 여섯 지표를 재고,
「기본 격자와 비슷함 / 다름 / 판정 불가」를 판정한다. 읽기 전용이다. 파일을 쓰지 않고
(출력은 표준 출력이나 --out 한 곳), 콘솔과 통신하지 않는다. 같은 입력이면 같은 출력이다.

지표 (줄마다 재고, 전체로 합쳐 판정한다)
  ① count      칸 수 — 줄마다 기본과의 차이를 본다
  ② length     칸 길이 분포 — 1·2·4·8마디·16마디 이상, 그리고 3·5·7 같은 값은 「기타」
  ③ alignment  칸 시작 마디가 구간 경계와 맞는 비율 (곡에 프레이즈 경계가 없어 구간 경계만 쓴다)
  ④ pattern    박 패턴 종류 분포 — 칸 라벨의 키워드로 나눈다. 못 나눈 칸은 「기타」
  ⑤ accent     강조 층(효과 줄)의 칸이 큰 히트(후렴 진입·드롭) 근처에만 있는 비율
  ⑥ color      색이 정해진 칸의 비율 (칸 필드의 색 번호, 또는 색 주석이 칸 안에 드는 경우)

비교 범위는 기본 격자의 마디 범위다(LOVE ATTACK 기본 격자는 0~25마디만 가진다). 범위 밖의
후보 칸은 판정하지 않고 개수만 적는다.

판정 기준 ``Thresholds`` 의 값은 **제안값**이다. 정답지 한 곡(LOVE ATTACK 기본 격자)으로만
교정했고, 다른 곡에 쓰기 전에 그 곡의 기본 격자로 다시 교정해야 한다(시험 test_grid_shape.py).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.audio.bar_map_store import read_bar_map
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import generate_arrangement_draft
from server.design.beat_grid import default_beat_grid
from server.design.preset_plan import load_preset_annotations

__all__ = [
    "DEFAULT_THRESHOLDS",
    "Cell",
    "Check",
    "Context",
    "ShapeCheckError",
    "ShapeReport",
    "Thresholds",
    "TrackRow",
    "accent_hits",
    "alignment_share",
    "build_auto_candidate",
    "build_context",
    "cells_for_track",
    "compare_grids",
    "grid_cells",
    "length_bin",
    "main",
    "pattern_category",
    "render_markdown",
    "total_variation",
]

#: 칸이 쉰다는 표식(arrange_generator 의 REST_LABEL 과 같다).
REST_LABEL = "—"
#: 강조 층의 역할 이름. 기본 격자에서 BLIND·STROBE 줄이 이 역할이다.
ACCENT_ROLE = "effect"
#: 칸 길이 구간. 16 은 「16마디 이상」이다.
LENGTH_BINS: tuple[str, ...] = ("1", "2", "4", "8", "16+", "기타")
OTHER = "기타"
REST = "쉼"

#: 박 패턴 키워드. 앞에 있는 것이 이긴다 — 「1·2·4박」을 「2·4박」과 「4박」보다 먼저 본다.
_BEAT_TOKENS: tuple[tuple[str, str], ...] = (
    ("킥", "킥"),
    ("1·2·4박", "1·2·4박"),
    ("2·4박", "2·4박"),
    ("앞박", "앞박"),
    ("3·4박", "3·4박"),
    ("4박", "4박"),
    ("2박", "2박"),
    ("1박", "1박"),
)
#: 박이 없는 상태 라벨. 박 키워드가 없을 때만 본다.
_STATE_WORDS: tuple[str, ...] = ("정지", "유지")

GAP_PHRASE = "③ 프레이즈 경계는 타임라인에 없어 구간 경계만으로 쟀습니다."
GAP_PALETTE = "⑥ 색은 칸 필드와 곡의 색 주석(preset_annotations)을 합쳐 쟀습니다."
GAP_ACCENT = (
    "⑤ 강조는 「큰 히트에만 있는가」(정밀도)만 쟀습니다. "
    "큰 히트마다 강조가 있는가(재현율)는 재지 않았습니다."
)

_DISPLAY = {
    "count": "① 칸 수",
    "length": "② 칸 길이",
    "alignment": "③ 경계 정렬",
    "pattern": "④ 박 패턴",
    "accent": "⑤ 강조 위치",
    "color": "⑥ 색 지정",
}
_PASS_TEXT = {True: "통과", False: "실패", None: "판정 불가"}


class ShapeCheckError(ValueError):
    """비교를 돌릴 수 없다(마디 지도 없음, 초안 비어 있음 등). 사유는 한국어 한 문장이다."""


@dataclass(frozen=True)
class Thresholds:
    """판정 기준(제안값). 기본 격자 한 곡으로 교정했다."""

    #: ① 줄별 칸 수 허용 비율. 허용 폭은 max(1, floor(기본 칸 수 × 이 값)).
    count_share: float = 0.25
    #: ② 전체 칸 길이 분포 거리(0~1, 전체 변위의 절반) 상한.
    length_tv: float = 0.25
    #: ③ 전체 경계 정렬률은 기본보다 이만큼까지만 낮아질 수 있다.
    alignment_drop: float = 0.15
    #: ④ 전체 박 패턴 분포 거리 상한.
    pattern_tv: float = 0.25
    #: ⑤ 강조 위치 중 큰 히트 근처에 든 비율 하한(줄별).
    accent_share: float = 0.9
    #: ⑤ 예고·여운으로 허용하는 마디 수.
    accent_tolerance: int = 1
    #: ⑥ 색 지정 비율 차이의 허용 폭 — 최소값.
    color_abs: float = 0.05
    #: ⑥ 색 지정 비율 차이의 허용 폭 — 기본 비율의 배수.
    color_rel: float = 0.5


DEFAULT_THRESHOLDS = Thresholds()


@dataclass(frozen=True)
class Cell:
    """칸 하나. 시작 마디부터 다음 칸 시작(또는 비교 범위 끝)까지다."""

    track: str
    start: int
    length: int
    label: str
    colored: bool = False


@dataclass(frozen=True)
class Context:
    """곡의 구간·히트·색 정보. 타임라인과 색 주석에서 만든다."""

    #: 구간 시작 마디 전부(② 경계 정렬의 기준).
    section_starts: frozenset[int]
    #: 후렴 시작 마디. 마지막 후렴은 이 가운데 가장 뒤다.
    chorus_bars: frozenset[int]
    #: 드롭 마디 전부(마디 지도 drop 사건의 범위).
    drop_bars: frozenset[int]
    #: 색 주석이 정한 (줄 이름, 마디) 쌍.
    color_cells: frozenset[tuple[str, int]]

    @property
    def hit_bars(self) -> frozenset[int]:
        return self.chorus_bars | self.drop_bars


@dataclass(frozen=True)
class Check:
    """지표 하나의 판정 한 줄. ``passed`` 가 None 이면 재 볼 데이터가 없다."""

    key: str
    scope: str
    track: str
    rule: str
    base: str
    candidate: str
    passed: bool | None
    detail: str = ""


@dataclass(frozen=True)
class TrackRow:
    """표의 줄 한 칸. 값은 이미 사람이 읽을 문자열이다."""

    name: str
    role: str
    base_count: int
    cand_count: int
    base_length: str
    cand_length: str
    base_alignment: str
    cand_alignment: str
    base_pattern: str
    cand_pattern: str
    base_accent: str
    cand_accent: str
    base_color: str
    cand_color: str


@dataclass(frozen=True)
class ShapeReport:
    verdict: str
    checks: tuple[Check, ...]
    rows: tuple[TrackRow, ...]
    window: tuple[int, int]
    out_of_window: int
    gaps: tuple[str, ...]

    @property
    def failing(self) -> tuple[str, ...]:
        """실패한 지표 키(중복 없이, 나온 순서대로)."""
        return tuple(dict.fromkeys(check.key for check in self.checks if check.passed is False))


def pattern_category(label: str | None) -> str:
    """칸 라벨을 박 패턴 종류 하나로 나눈다. 우선순위는 ``_BEAT_TOKENS`` 순서다."""
    text = (label or "").strip()
    if not text:
        return OTHER
    if text == REST_LABEL:
        return REST
    for token, category in _BEAT_TOKENS:
        if token in text:
            return category
    for word in _STATE_WORDS:
        if word in text:
            return word
    return OTHER


def length_bin(length: int) -> str:
    """칸 길이(마디)를 구간 하나로 나눈다. 3·5·6·7 같은 값은 「기타」다."""
    if length in (1, 2, 4, 8):
        return str(length)
    if length >= 16:
        return "16+"
    return OTHER


def total_variation(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    """두 분포의 거리(전체 변위의 절반). 같으면 0, 겹치는 항목이 없으면 1."""
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(key, 0.0) - q.get(key, 0.0)) for key in keys)


def shares_of(counts: Mapping[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total == 0:
        return {}
    return {key: value / total for key, value in counts.items()}


def cells_for_track(
    cues: Sequence[Mapping[str, Any]],
    window: tuple[int, int],
    *,
    track_name: str,
    color_cells: frozenset[tuple[str, int]],
) -> list[Cell]:
    """한 줄의 칸 목록. 칸은 다음 칸 시작에서 끝나고, 비교 범위 끝(포함)에서 잘린다."""
    start, end = window
    end_exclusive = end + 1
    ordered = sorted(cues, key=lambda cue: int(cue["bar"]))
    bars = [int(cue["bar"]) for cue in ordered]
    annotation_bars = [bar for name, bar in color_cells if name == track_name]
    cells: list[Cell] = []
    for index, cue in enumerate(ordered):
        bar = bars[index]
        if not start <= bar <= end:
            continue
        next_bar = bars[index + 1] if index + 1 < len(bars) else end_exclusive
        span_end = min(next_bar, end_exclusive)
        colored = (
            cue.get("color_preset_no") is not None
            or bool(cue.get("split"))
            or any(bar <= annotated < span_end for annotated in annotation_bars)
        )
        cells.append(
            Cell(
                track=track_name,
                start=bar,
                length=span_end - bar,
                label=str(cue.get("label") or ""),
                colored=colored,
            )
        )
    return cells


def grid_cells(
    grid: Mapping[str, Any],
    window: tuple[int, int],
    color_cells: frozenset[tuple[str, int]],
) -> dict[str, list[Cell]]:
    """격자의 줄 이름마다 칸 목록을 만든다(줄 순서는 격자의 순서다)."""
    return {
        str(track["group_name"]): cells_for_track(
            track.get("cues") or [],
            window,
            track_name=str(track["group_name"]),
            color_cells=color_cells,
        )
        for track in grid.get("tracks") or []
    }


def alignment_share(cells: Sequence[Cell], boundary_bars: frozenset[int]) -> float | None:
    """칸 시작 마디 가운데 경계 마디에 드는 비율. 칸이 없으면 None."""
    if not cells:
        return None
    return sum(1 for cell in cells if cell.start in boundary_bars) / len(cells)


def accent_hits(
    cells: Sequence[Cell],
    hit_bars: frozenset[int],
    *,
    tolerance: int,
) -> tuple[int, int]:
    """강조 위치(쉼이 아닌 칸) 수와, 그 가운데 큰 히트 ±tolerance 마디 안에 든 수."""
    positions = [cell for cell in cells if cell.label.strip() not in ("", REST_LABEL)]
    near = sum(
        1 for cell in positions if any(abs(cell.start - hit) <= tolerance for hit in hit_bars)
    )
    return len(positions), near


def build_context(timeline: Mapping[str, Any], annotations: Mapping[str, Any]) -> Context:
    """타임라인(구간·마디 지도)과 색 주석으로 비교 맥락을 만든다."""
    sections = [
        section
        for section in timeline.get("sections") or []
        if isinstance(section, Mapping) and section.get("bar_start") is not None
    ]
    section_starts = frozenset(int(section["bar_start"]) for section in sections)
    chorus = frozenset(
        int(section["bar_start"])
        for section in sections
        if str(section.get("label") or "").startswith("후렴")
    )
    drop: set[int] = set()
    bar_map = timeline.get("bar_map")
    if isinstance(bar_map, Mapping):
        for event in bar_map.get("events") or []:
            if event.get("kind") == "drop":
                drop.update(range(int(event["start_bar"]), int(event["end_bar"]) + 1))
    colors = {
        (str(cell["group_name"]), int(cell["bar"]))
        for entry in annotations.get("colors") or []
        for cell in entry.get("cells") or []
    }
    return Context(
        section_starts=section_starts,
        chorus_bars=chorus,
        drop_bars=frozenset(drop),
        color_cells=frozenset(colors),
    )


def _layout_item(track: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "group_no": track.get("group_no"),
        "group_no_confirmed": bool(track.get("group_no_confirmed", False)),
        "group_name": str(track["group_name"]),
        "layer_role": track.get("layer_role"),
    }


# @MX:NOTE: [AUTO] 운영 경로(beat_grid_draft_propose → beat_grid_draft_apply)와
# 같은 순서로 오프라인에서 만든다. 감독 원본 칸 없이 빈 골격에 적용하므로
# 결과는 자동 배치만 보여 준다.
def build_auto_candidate(timeline: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    """마디 지도와 기본 격자의 줄 구성으로 자동 배치 격자를 오프라인으로 만든다."""
    bar_map = read_bar_map(timeline)
    if bar_map is None:
        raise ShapeCheckError("마디 지도가 없거나 유효하지 않아 자동 배치를 만들 수 없습니다.")
    base_tracks = list(base.get("tracks") or [])
    if not base_tracks:
        raise ShapeCheckError("기본 격자에 줄이 없습니다.")
    draft = generate_arrangement_draft(bar_map, [_layout_item(track) for track in base_tracks])
    if draft["note"] is not None or not draft["tracks"]:
        raise ShapeCheckError(str(draft["note"] or "자동 배치 초안이 비어 있습니다."))
    skeleton = {
        "song_title": str(base.get("song_title") or ""),
        "bar_range": dict(base.get("bar_range") or {}),
        "tracks": [{**_layout_item(track), "cues": []} for track in base_tracks],
        "scene_memos": [],
        "source": "skeleton",
    }
    candidate, _report = apply_arrangement_draft(skeleton, draft)
    return candidate


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def _hits_text(hits: int, total: int) -> str:
    return "—" if total == 0 else f"{hits}/{total}"


def _accent_text(cells: Sequence[Cell], hit_bars: frozenset[int], tolerance: int) -> str:
    """큰 히트 근처 수/위치 수. ``accent_hits`` 의 반환 순서를 여기서만 푼다."""
    positions, near = accent_hits(cells, hit_bars, tolerance=tolerance)
    return _hits_text(near, positions)


def _color_share(cells: Sequence[Cell]) -> float | None:
    if not cells:
        return None
    return sum(1 for cell in cells if cell.colored) / len(cells)


def _display_key(key: str) -> str:
    if key in ("1", "2", "4", "8"):
        return f"{key}마디"
    if key == "16+":
        return "16마디+"
    return key


def _top_text(shares: Mapping[str, float], *, limit: int) -> str:
    ranked = sorted(
        ((key, value) for key, value in shares.items() if value > 0),
        key=lambda item: (-item[1], item[0]),
    )[:limit]
    return " · ".join(f"{_display_key(key)} {value:.0%}" for key, value in ranked) or "—"


def compare_grids(
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    context: Context,
    *,
    window: tuple[int, int] | None = None,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> ShapeReport:
    """기본 격자와 후보 격자를 여섯 지표로 견주고 판정한다."""
    if window is None:
        bar_range = base.get("bar_range") or {}
        window = (int(bar_range["start"]), int(bar_range["end"]))
    base_cells = grid_cells(base, window, context.color_cells)
    cand_cells = grid_cells(candidate, window, context.color_cells)
    names = list(base_cells)
    roles = {
        str(track["group_name"]): str(track.get("layer_role") or "")
        for track in base.get("tracks") or []
    }

    gaps: list[str] = [GAP_PHRASE, GAP_PALETTE, GAP_ACCENT]
    extra = [name for name in cand_cells if name not in base_cells]
    if extra:
        gaps.append("후보에만 있는 줄은 비교하지 않았습니다: " + ", ".join(extra))
    absent = [name for name in names if name not in cand_cells]
    if absent:
        gaps.append("후보에 없는 줄은 칸 0개로 셌습니다: " + ", ".join(absent))
    out_of_window = sum(
        1
        for track in candidate.get("tracks") or []
        for cue in track.get("cues") or []
        if not window[0] <= int(cue["bar"]) <= window[1]
    )
    if out_of_window:
        gaps.append(
            f"비교 범위({window[0]}~{window[1]}마디) 밖의 후보 칸 {out_of_window}개는 "
            "판정하지 않았습니다."
        )
    for name in names:
        cand_cells.setdefault(name, [])

    all_base = [cell for name in names for cell in base_cells[name]]
    all_cand = [cell for name in names for cell in cand_cells[name]]
    checks: list[Check] = []

    # ① 칸 수 — 줄마다
    for name in names:
        base_n, cand_n = len(base_cells[name]), len(cand_cells[name])
        tolerance = max(1, math.floor(thresholds.count_share * base_n))
        checks.append(
            Check(
                key="count",
                scope="줄별",
                track=name,
                rule=f"허용 ±{tolerance}칸",
                base=str(base_n),
                candidate=str(cand_n),
                passed=abs(cand_n - base_n) <= tolerance,
            )
        )

    # ② 칸 길이 분포 — 전체
    base_length = shares_of(Counter(length_bin(cell.length) for cell in all_base))
    cand_length = shares_of(Counter(length_bin(cell.length) for cell in all_cand))
    length_tv = total_variation(base_length, cand_length) if all_base and all_cand else None
    if not all_base:
        length_passed: bool | None = None
    elif not all_cand:
        length_passed = False
    else:
        length_passed = length_tv <= thresholds.length_tv
    checks.append(
        Check(
            key="length",
            scope="전체",
            track="",
            rule=f"분포 거리 ≤ {thresholds.length_tv:g}",
            base=_top_text(base_length, limit=6),
            candidate=_top_text(cand_length, limit=6),
            passed=length_passed,
            detail="" if length_tv is None else f"거리 {length_tv:.3f}",
        )
    )

    # ③ 경계 정렬 — 전체
    base_align = alignment_share(all_base, context.section_starts)
    cand_align = alignment_share(all_cand, context.section_starts)
    if base_align is None:
        align_passed: bool | None = None
    elif cand_align is None:
        align_passed = False
    else:
        align_passed = cand_align >= base_align - thresholds.alignment_drop
    checks.append(
        Check(
            key="alignment",
            scope="전체",
            track="",
            rule=f"후보 ≥ 기본 − {thresholds.alignment_drop:g}",
            base=_pct(base_align),
            candidate=_pct(cand_align),
            passed=align_passed,
        )
    )

    # ④ 박 패턴 분포 — 전체
    base_pattern = shares_of(Counter(pattern_category(cell.label) for cell in all_base))
    cand_pattern = shares_of(Counter(pattern_category(cell.label) for cell in all_cand))
    pattern_tv = total_variation(base_pattern, cand_pattern) if all_base and all_cand else None
    if not all_base:
        pattern_passed: bool | None = None
    elif not all_cand:
        pattern_passed = False
    else:
        pattern_passed = pattern_tv <= thresholds.pattern_tv
    checks.append(
        Check(
            key="pattern",
            scope="전체",
            track="",
            rule=f"분포 거리 ≤ {thresholds.pattern_tv:g}",
            base=_top_text(base_pattern, limit=3),
            candidate=_top_text(cand_pattern, limit=3),
            passed=pattern_passed,
            detail="" if pattern_tv is None else f"거리 {pattern_tv:.3f}",
        )
    )

    # ⑤ 강조 위치 — 강조 층(효과 줄)마다
    for name in names:
        if roles.get(name) != ACCENT_ROLE:
            continue
        base_n, base_hits = accent_hits(
            base_cells[name], context.hit_bars, tolerance=thresholds.accent_tolerance
        )
        cand_n, cand_hits = accent_hits(
            cand_cells[name], context.hit_bars, tolerance=thresholds.accent_tolerance
        )
        checks.append(
            Check(
                key="accent",
                scope="줄별",
                track=name,
                rule=(
                    f"위치의 {thresholds.accent_share:.0%} 이상이 "
                    f"큰 히트 ±{thresholds.accent_tolerance}마디 안"
                ),
                base=_hits_text(base_hits, base_n),
                candidate=_hits_text(cand_hits, cand_n),
                passed=cand_n == 0 or cand_hits / cand_n >= thresholds.accent_share,
            )
        )

    # ⑥ 색 지정 비율 — 전체
    base_color = _color_share(all_base)
    cand_color = _color_share(all_cand)
    if base_color is None:
        color_passed: bool | None = None
    elif cand_color is None:
        color_passed = False
    else:
        tolerance_color = max(thresholds.color_abs, thresholds.color_rel * base_color)
        color_passed = abs(cand_color - base_color) <= tolerance_color
    checks.append(
        Check(
            key="color",
            scope="전체",
            track="",
            rule=f"|후보 − 기본| ≤ max({thresholds.color_abs:g}, {thresholds.color_rel:g} × 기본)",
            base=_pct(base_color),
            candidate=_pct(cand_color),
            passed=color_passed,
        )
    )

    if any(check.passed is False for check in checks):
        verdict = "다름"
    elif any(check.passed is None for check in checks):
        verdict = "판정 불가"
    else:
        verdict = "비슷함"

    rows: list[TrackRow] = []
    for name in names:
        base_row, cand_row = base_cells[name], cand_cells[name]
        is_accent = roles.get(name) == ACCENT_ROLE
        rows.append(
            TrackRow(
                name=name,
                role=roles.get(name, ""),
                base_count=len(base_row),
                cand_count=len(cand_row),
                base_length=_top_text(
                    shares_of(Counter(length_bin(cell.length) for cell in base_row)), limit=3
                ),
                cand_length=_top_text(
                    shares_of(Counter(length_bin(cell.length) for cell in cand_row)), limit=3
                ),
                base_alignment=_pct(alignment_share(base_row, context.section_starts)),
                cand_alignment=_pct(alignment_share(cand_row, context.section_starts)),
                base_pattern=_top_text(
                    shares_of(Counter(pattern_category(cell.label) for cell in base_row)), limit=2
                ),
                cand_pattern=_top_text(
                    shares_of(Counter(pattern_category(cell.label) for cell in cand_row)), limit=2
                ),
                base_accent=(
                    _accent_text(base_row, context.hit_bars, thresholds.accent_tolerance)
                    if is_accent
                    else "—"
                ),
                cand_accent=(
                    _accent_text(cand_row, context.hit_bars, thresholds.accent_tolerance)
                    if is_accent
                    else "—"
                ),
                base_color=_pct(_color_share(base_row)),
                cand_color=_pct(_color_share(cand_row)),
            )
        )

    return ShapeReport(
        verdict=verdict,
        checks=tuple(checks),
        rows=tuple(rows),
        window=window,
        out_of_window=out_of_window,
        gaps=tuple(gaps),
    )


def render_markdown(report: ShapeReport, *, inputs: Mapping[str, str]) -> str:
    """사람이 읽는 마크다운 표. 판정, 기준과 측정값, 줄별 표, 빠진 데이터 순서다."""
    lines: list[str] = ["# 격자 모양 비교", ""]
    for key, value in inputs.items():
        lines.append(f"- **{key}**: {value}")
    lines += ["", "## 판정", "", f"**{report.verdict}**"]
    if report.failing:
        lines += ["", "실패한 지표: " + ", ".join(_DISPLAY[key] for key in report.failing)]
    lines += [
        "",
        "## 기준과 측정값",
        "",
        "| 지표 | 범위 | 기준 | 기본 | 후보 | 결과 | 비고 |",
        "|---|---|---|---|---|---|---|",
    ]
    for check in report.checks:
        lines.append(
            f"| {_DISPLAY[check.key]} | {check.track or '전체'} | {check.rule} | "
            f"{check.base} | {check.candidate} | {_PASS_TEXT[check.passed]} | {check.detail} |"
        )
    lines += [
        "",
        "## 줄별 비교",
        "",
        "| 줄 | 역할 | ① 칸 수 (기본→후보) | ② 칸 길이 (상위) | ③ 경계 정렬 (기본→후보) "
        "| ④ 박 패턴 (상위) | ⑤ 강조 위치 (큰 히트 안) | ⑥ 색 지정 (기본→후보) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report.rows:
        lines.append(
            f"| {row.name} | {row.role} | {row.base_count}→{row.cand_count} | "
            f"기본 {row.base_length} / 후보 {row.cand_length} | "
            f"{row.base_alignment}→{row.cand_alignment} | "
            f"기본 {row.base_pattern} / 후보 {row.cand_pattern} | "
            f"{row.base_accent}→{row.cand_accent} | {row.base_color}→{row.cand_color} |"
        )
    lines += [
        "",
        "## 비교 범위와 빠진 데이터",
        "",
        f"- 비교 범위: {report.window[0]}~{report.window[1]}마디 (기본 격자의 마디 범위)",
    ]
    lines += [f"- {gap}" for gap in report.gaps]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m server.design.grid_shape",
        description="자동 배치 격자와 기본 격자의 모양을 줄마다 숫자로 견준다.",
    )
    parser.add_argument(
        "--timeline",
        type=Path,
        required=True,
        help="구간(sections)과 마디 지도(bar_map)가 든 타임라인 JSON",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=None,
        help="비교할 후보 격자 JSON. 없으면 타임라인 마디 지도로 자동 배치를 오프라인으로 만든다.",
    )
    parser.add_argument(
        "--song", default=None, help="기본 격자 곡 이름(기본: 타임라인의 song_title)"
    )
    parser.add_argument("--out", type=Path, default=None, help="표를 쓸 파일(없으면 표준 출력)")
    parser.add_argument(
        "--fail-on-different", action="store_true", help="판정이 「비슷함」이 아니면 종료 코드 1"
    )
    args = parser.parse_args(argv)

    try:
        timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
        title = args.song or str(timeline.get("song_title") or "")
        base = default_beat_grid(title)
        if not base.get("tracks"):
            raise ShapeCheckError(f"「{title}」의 기본 격자가 등록돼 있지 않습니다.")
        if args.candidate is not None:
            candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
            source = f"파일 {args.candidate.name}"
        else:
            candidate = build_auto_candidate(timeline, base)
            source = "자동 배치 (마디 지도 → 초안 → 빈 골격에 적용, 오프라인)"
    except (OSError, ValueError) as error:
        print(f"격자 비교를 돌릴 수 없습니다: {error}", file=sys.stderr)
        return 2

    context = build_context(timeline, load_preset_annotations(title))
    report = compare_grids(base, candidate, context)
    bar_range = base["bar_range"]
    text = render_markdown(
        report,
        inputs={
            "기본 격자": f"{title} ({bar_range['start']}~{bar_range['end']}마디)",
            "후보": source,
            "타임라인": args.timeline.name,
        },
    )
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.fail_on_different and report.verdict != "비슷함":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
