"""박자 배치 화면이 읽는 값 — 트랙 부가 정보·구간 에너지·구간 색·강조 마디 (순수 함수).

콘솔에 닿지 않고 I/O 도 하지 않는다. 곡·리그 고유값을 하나도 담지 않는다 — 구간 종류별
색 표(:data:`SECTION_KIND_COLORS`)만 곡과 무관한 고정 상수이고, 나머지는 전부 입력(타임라인의
``sections``·``bar_map``, 콘솔에서 읽은 그룹 소속·기종)에서 계산한다. 계산할 수 없는 값은 키를
빼서 「모른다」를 그대로 둔다(지어내지 않는다).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from server.design.beat_grid import preset_pool_no
from server.design.beat_grid_cell_split import attach_cell_split_to_cues
from server.design.beat_grid_color_presets import attach_color_rgb_to_cues
from server.design.beat_grid_planned import attach_planned_marks

__all__ = [
    "SECTION_KIND_COLORS",
    "accent_bars_from_bar_map",
    "attach_beat_grid_ui_values",
    "attach_console_preset_names",
    "format_fid_ranges",
    "section_kind",
    "track_sub_info",
]

#: 구간 종류 -> 색. 곡·리그와 무관한 하나의 표(모든 곡이 같은 색을 쓴다).
SECTION_KIND_COLORS: dict[str, str] = {
    "intro": "#5b6b8a",
    "bridge": "#5b6b8a",
    "verse": "#6d5ba8",
    "pre-chorus": "#8a6bc4",
    "chorus": "#c4508a",
    "final-chorus": "#e0607a",
    "drop": "#d9774f",
    "break": "#444",
    "outro": "#333",
}

#: (종류, 이름에 들어 있으면 그 종류인 낱말들) — 앞에서부터 처음 맞는 종류를 쓴다.
#: ``final-chorus`` 가 ``pre-chorus``·``chorus`` 보다 먼저여야 「마지막 코러스」가 일반 후렴으로
#: 잡히지 않고, ``pre-chorus`` 가 ``chorus`` 보다 먼저여야 「프리 후렴」이 후렴으로 잡히지 않는다.
_KIND_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "final-chorus",
        (
            "마지막 후렴",
            "마지막 코러스",
            "마지막후렴",
            "마지막코러스",
            "last chorus",
            "final chorus",
        ),
    ),
    ("pre-chorus", ("프리", "pre-chorus", "prechorus", "pre chorus", "pre-")),
    ("outro", ("아웃트로", "outro", "엔딩", "ending", "끝")),
    ("intro", ("인트로", "intro")),
    ("chorus", ("후렴", "코러스", "chorus", "hook", "훅")),
    ("verse", ("벌스", "verse")),
    ("bridge", ("브리지", "bridge")),
    ("drop", ("드롭", "drop")),
    (
        "break",
        ("킥멈춤", "킥 멈춤", "덜어냄", "간주", "브레이크", "break", "interlude", "인터루드"),
    ),
)

_STANDALONE_END = re.compile(r"\bend\b")


def section_kind(label: object) -> str | None:
    """구간 이름 -> 종류(없으면 ``None`` — 모르는 이름에 색을 지어내지 않는다)."""
    if not isinstance(label, str):
        return None
    lowered = label.strip().lower()
    for kind, words in _KIND_KEYWORDS:
        if any(word in lowered for word in words):
            return kind
    if _STANDALONE_END.search(lowered):
        return "outro"
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


_NAME_FIELDS = (
    ("position_preset_no", "position_preset_name"),
    ("color_preset_no", "color_preset_name"),
)


def _console_preset_name(
    pool_slots: Mapping[int, Mapping[int, str | None] | None], preset_no: object
) -> str | None:
    """``"pool.slot"`` 번호의 콘솔 이름. 풀을 못 읽었거나(``None``) 슬롯이 없거나 이름이
    비었으면 ``None`` — 지어내지 않는다."""
    pool_no = preset_pool_no(preset_no)
    if pool_no is None or not isinstance(preset_no, str):
        return None
    slot_text = preset_no.partition(".")[2]
    if not slot_text.isdigit():
        return None
    slots = pool_slots.get(pool_no)
    name = slots.get(int(slot_text)) if isinstance(slots, Mapping) else None
    return name.strip() if isinstance(name, str) and name.strip() else None


def attach_console_preset_names(
    grid: Mapping[str, object],
    pool_slots: Mapping[int, Mapping[int, str | None] | None],
) -> dict[str, object]:
    """격자 사본의 칸마다 위치·색 프리셋의 **콘솔 이름**을 단다(읽기 전용, 원본 불변).
    이미 칸에 있는 이름은 덮지 않고, 이름을 모르면 키를 뺀다."""
    tracks = grid.get("tracks")
    if not isinstance(tracks, list):
        return dict(grid)
    new_tracks: list[object] = []
    for track in tracks:
        cues = track.get("cues") if isinstance(track, Mapping) else None
        if not isinstance(cues, list):
            new_tracks.append(track)
            continue
        new_cues: list[object] = []
        for cue in cues:
            if isinstance(cue, Mapping):
                extra = {
                    name_key: name
                    for no_key, name_key in _NAME_FIELDS
                    if name_key not in cue
                    and (name := _console_preset_name(pool_slots, cue.get(no_key))) is not None
                }
                cue = {**cue, **extra} if extra else cue
            new_cues.append(cue)
        new_tracks.append({**track, "cues": new_cues})
    return {**grid, "tracks": new_tracks}


def attach_beat_grid_ui_values(
    timeline: Mapping[str, object],
    *,
    track_sub_infos: Mapping[str, Mapping[str, object]] | None = None,
    pool_slots: Mapping[int, Mapping[int, str | None] | None] | None = None,
    track_sequence_numbers: Mapping[str, int] | None = None,
) -> dict[str, object]:
    """타임라인 사본에 화면용 값을 싣는다(원본 불변, 있는 값은 덮지 않는다).

    - ``sections[i].kind``·``color`` — 이름에서 종류를 알아볼 때만.
    - ``sections[i].energy`` — 마디 지도에 마디별 ``energy`` 가 있을 때만.
    - ``accent_bars`` — 마디 지도에 드롭 이벤트가 있을 때만.
    - ``beat_grid.tracks[i].cues[j].color_rgb`` — ``preset_colors`` 에 그 색 번호가 기록됐을 때만.
    - ``beat_grid.tracks[i].cues[j].split.{left,right}.color_rgb`` — 칸에 ``split``(왼쪽·오른쪽 따로
      색)이 있을 때만, 쪽마다 색 이름을 푼 RGB(못 풀면 ``None``). ``split`` 이 없으면 키도 없다.
      모양이 틀린 ``split`` 은 조용히 버리지 않고 ``ValueError``(그룹·마디를 말한다)로 올린다.
    - ``beat_grid.tracks[i].cues[j].color_rgb`` + ``color_planned`` — 곡별 계획 주석의 계획 색이고
      칸에 콘솔 색 번호가 없을 때만(``beat_grid_planned.attach_planned_marks``).
    - ``beat_grid.tracks[i].cues[j].planned_dimmer_name`` / ``planned_position_name`` —
      곡별 계획 주석의 계획 이름이고 칸에 콘솔 번호가 없을 때만.
    - ``beat_grid.tracks[i].cues[j].position_preset_name`` / ``color_preset_name`` — 세션이 이미
      완전 판독해 기억한 콘솔 풀(``pool_slots``)에 그 번호의 이름이 있을 때만.
    - ``beat_grid.tracks[i].sub_info`` — ``track_sub_infos``(그룹 이름 대문자 -> 정보)에 있을 때만.
    - ``beat_grid.tracks[i].sequence_number`` — ``track_sequence_numbers``(그룹 이름 대문자 -> 콘솔
      시퀀스 번호, 반영 때 실제로 배정·기록된 값)에 있을 때만. 없으면 키를 뺀다.
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
            # 구간이 종류를 직접 싣고 있으면(새 분석 작업본 — 이름이 D 레벨뿐이다) 그 종류를 쓴다.
            explicit = section.get("kind")
            kind = (
                explicit if explicit in SECTION_KIND_COLORS else section_kind(section.get("label"))
            )
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
    if isinstance(grid, Mapping):
        grid = attach_color_rgb_to_cues(grid)
        grid = attach_cell_split_to_cues(grid)
        # 계획 표시(화면 전용) — beat_grid_planned 참고.
        grid = attach_planned_marks(grid, merged.get("song_title"))
        if pool_slots:
            grid = attach_console_preset_names(grid, pool_slots)
        merged["beat_grid"] = grid
    if (
        (track_sub_infos or track_sequence_numbers)
        and isinstance(grid, Mapping)
        and isinstance(grid.get("tracks"), list)
    ):
        tracks: list[object] = []
        for track in grid["tracks"]:
            if isinstance(track, Mapping):
                group = str(track.get("group_name", "")).upper()
                info = (track_sub_infos or {}).get(group)
                if info is not None:
                    track = {**track, "sub_info": dict(info)}
                number = (track_sequence_numbers or {}).get(group)
                if isinstance(number, int) and not isinstance(number, bool):
                    track = {**track, "sequence_number": number}
            tracks.append(track)
        merged["beat_grid"] = {**grid, "tracks": tracks}
    return merged
