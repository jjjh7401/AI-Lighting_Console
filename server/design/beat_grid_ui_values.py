"""박자 배치 화면이 읽는 값 — 트랙 부가 정보·구간 에너지·구간 색·강조 마디 (순수 함수).

콘솔에 닿지 않고 I/O 도 하지 않는다. 곡·리그 고유값을 하나도 담지 않는다 — 구간 종류별
색 표(:data:`SECTION_KIND_COLORS`)만 곡과 무관한 고정 상수이고, 나머지는 전부 입력(타임라인의
``sections``·``bar_map``, 콘솔에서 읽은 그룹 소속·기종)에서 계산한다. 계산할 수 없는 값은 키를
빼서 「모른다」를 그대로 둔다(지어내지 않는다).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

__all__ = [
    "SECTION_KIND_COLORS",
    "accent_bars_from_bar_map",
    "attach_beat_grid_ui_values",
    "format_fid_ranges",
    "section_kind",
    "track_sub_info",
]

#: 구간 종류 -> 색. 곡·리그와 무관한 하나의 표(모든 곡이 같은 색을 쓴다).
SECTION_KIND_COLORS: dict[str, str] = {
    "intro": "#64748b",
    "verse": "#3b82f6",
    "pre-chorus": "#a855f7",
    "chorus": "#ec4899",
    "bridge": "#f59e0b",
    "drop": "#f97316",
    "build": "#eab308",
    "break": "#14b8a6",
    "outro": "#94a3b8",
}

#: (종류, 이름에 들어 있으면 그 종류인 낱말들) — 앞에서부터 처음 맞는 종류를 쓴다.
#: ``pre-chorus`` 가 ``chorus`` 보다 먼저여야 「프리 후렴」이 후렴으로 잡히지 않는다.
_KIND_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pre-chorus", ("프리", "pre-chorus", "prechorus", "pre chorus", "pre-")),
    ("outro", ("아웃트로", "outro", "엔딩", "ending")),
    ("intro", ("인트로", "intro")),
    ("chorus", ("후렴", "코러스", "chorus", "hook", "훅")),
    ("verse", ("벌스", "verse")),
    ("bridge", ("브리지", "bridge")),
    ("drop", ("드롭", "drop")),
    ("build", ("빌드", "build")),
    ("break", ("브레이크", "break", "간주", "interlude", "인터루드")),
)


def section_kind(label: object) -> str | None:
    """구간 이름 -> 종류(없으면 ``None`` — 모르는 이름에 색을 지어내지 않는다)."""
    if not isinstance(label, str):
        return None
    lowered = label.strip().lower()
    for kind, words in _KIND_KEYWORDS:
        if any(word in lowered for word in words):
            return kind
    return None


def format_fid_ranges(fids: Iterable[int]) -> str:
    """fid 목록 -> ``201~212`` / ``201~204,210`` (정렬·중복 제거, 이어진 번호는 범위로)."""
    ordered = sorted({fid for fid in fids if isinstance(fid, int) and not isinstance(fid, bool)})
    parts: list[str] = []
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1] == ordered[end] + 1:
            end += 1
        if end == index:
            parts.append(str(ordered[index]))
        elif end == index + 1:
            parts.append(f"{ordered[index]},{ordered[end]}")
        else:
            parts.append(f"{ordered[index]}~{ordered[end]}")
        index = end + 1
    return ",".join(parts)


def track_sub_info(
    *,
    group_no: int | None,
    member_fids: Sequence[int] | None,
    complete: bool,
    fixture_types: Mapping[int, str] | None,
) -> dict[str, object] | None:
    """트랙 이름 밑 둘째 줄 — ``{group_no?, fid_ranges?, fixture_count?, fixture_types?, text}``.

    소속이 **전수로** 읽힌 그룹만 fid 범위·대수·기종을 싣는다(부분 소속은 틀린 대수를 말하게
    된다). 기종은 소속 장비 전부가 읽힌 이름일 때만 싣고, 섞인 그룹은 많은 순으로 이어 붙인다.
    아무것도 모르면 ``None``."""
    info: dict[str, object] = {}
    parts: list[str] = []
    if isinstance(group_no, int) and not isinstance(group_no, bool):
        info["group_no"] = group_no
        parts.append(f"G{group_no}")
    fids = list(member_fids or ())
    if complete and fids:
        ranges = format_fid_ranges(fids)
        info["fid_ranges"] = ranges
        info["fixture_count"] = len(set(fids))
        parts += [ranges, f"{len(set(fids))}대"]
        types = fixture_types or {}
        names = [types.get(fid) for fid in set(fids)]
        if names and all(isinstance(name, str) and name for name in names):
            counts: dict[str, int] = {}
            for name in names:
                counts[str(name)] = counts.get(str(name), 0) + 1
            ordered = [n for n, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
            info["fixture_types"] = ordered
            parts.append(" + ".join(ordered))
    if not info:
        return None
    info["text"] = " · ".join(parts)
    return info


def accent_bars_from_bar_map(bar_map: Mapping[str, object] | None) -> list[dict[str, object]]:
    """마디 지도의 드롭 이벤트 -> 강조(★) 마디 ``[{bar, kind, grade}]``(시작 마디, 중복 없음)."""
    events = bar_map.get("events") if isinstance(bar_map, Mapping) else None
    out: list[dict[str, object]] = []
    seen: set[int] = set()
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, Mapping) or event.get("kind") != "drop":
            continue
        bar = event.get("start_bar")
        if isinstance(bar, bool) or not isinstance(bar, int) or bar in seen:
            continue
        seen.add(bar)
        out.append({"bar": bar, "kind": "drop", "grade": event.get("grade", "measured")})
    return sorted(out, key=lambda item: int(item["bar"]))  # type: ignore[call-overload]


def _section_energies(
    sections: Sequence[Mapping[str, object]], bar_map: Mapping[str, object] | None
) -> dict[int, float]:
    """구간 위치 -> 에너지(0~1). 마디 시작 시각이 구간 ``[start_ms, 다음 start_ms)`` 에 드는
    마디들의 저장된 ``energy`` 평균. 에너지가 하나도 없으면 그 구간은 빠진다."""
    bars = bar_map.get("bars") if isinstance(bar_map, Mapping) else None
    if not isinstance(bars, list):
        return {}
    timed = [
        (bar["start_ms"], bar["energy"])
        for bar in bars
        if isinstance(bar, Mapping)
        and isinstance(bar.get("start_ms"), int)
        and isinstance(bar.get("energy"), int | float)
    ]
    if not timed:
        return {}
    starts = [section.get("start_ms") for section in sections]
    result: dict[int, float] = {}
    for position, start in enumerate(starts):
        if isinstance(start, bool) or not isinstance(start, int):
            continue
        end = next(
            (
                later
                for later in starts[position + 1 :]
                if isinstance(later, int) and not isinstance(later, bool)
            ),
            None,
        )
        inside = [e for t, e in timed if t >= start and (end is None or t < end)]
        if inside:
            result[position] = round(sum(inside) / len(inside), 3)
    return result


def attach_beat_grid_ui_values(
    timeline: Mapping[str, object],
    *,
    track_sub_infos: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """타임라인 사본에 화면용 값을 싣는다(원본 불변, 있는 값은 덮지 않는다).

    - ``sections[i].kind``·``color`` — 이름에서 종류를 알아볼 때만.
    - ``sections[i].energy`` — 마디 지도에 마디별 ``energy`` 가 있을 때만.
    - ``accent_bars`` — 마디 지도에 드롭 이벤트가 있을 때만.
    - ``beat_grid.tracks[i].sub_info`` — ``track_sub_infos``(그룹 이름 대문자 -> 정보)에 있을 때만.
    """
    merged = dict(timeline)
    bar_map = merged.get("bar_map")
    raw_sections = merged.get("sections")
    if isinstance(raw_sections, list):
        energies = _section_energies(
            [s if isinstance(s, Mapping) else {} for s in raw_sections],
            bar_map if isinstance(bar_map, Mapping) else None,
        )
        sections: list[object] = []
        for position, section in enumerate(raw_sections):
            if not isinstance(section, Mapping):
                sections.append(section)
                continue
            section = dict(section)
            kind = section_kind(section.get("label"))
            if kind is not None:
                section.setdefault("kind", kind)
                section.setdefault("color", SECTION_KIND_COLORS[kind])
            if position in energies:
                section.setdefault("energy", energies[position])
            sections.append(section)
        merged["sections"] = sections
    accents = accent_bars_from_bar_map(bar_map if isinstance(bar_map, Mapping) else None)
    if accents:
        merged["accent_bars"] = accents
    grid = merged.get("beat_grid")
    if track_sub_infos and isinstance(grid, Mapping) and isinstance(grid.get("tracks"), list):
        tracks: list[object] = []
        for track in grid["tracks"]:
            if isinstance(track, Mapping):
                info = track_sub_infos.get(str(track.get("group_name", "")).upper())
                if info is not None:
                    track = {**track, "sub_info": dict(info)}
            tracks.append(track)
        merged["beat_grid"] = {**grid, "tracks": tracks}
    return merged
