"""계획 표시 — 콘솔에 아직 없는 계획 값을 격자 칸에 얹는다(화면 전용, 콘솔 무접촉).

계획 값은 곡별 계획 주석(``preset_annotations``)과 계획표(``preset_plan``)가 정한다. 칸에 콘솔
색 프리셋 번호가 없으면 계획 색을 ``color_rgb``(0~100%)로 싣고 ``color_planned: true`` 를 붙인다.
디머·위치 프리셋 번호가 없으면 계획 이름만 싣는다
(``planned_dimmer_name`` · ``planned_position_name``, 예: DIM-70 · FLOOR).
화면은 이 키들을 점선 테두리·흐린 글자로 그려서 콘솔 값과 구분한다.

원본 격자는 바뀌지 않는다 — 화면에 보낼 사본에만 붙는다. 「반영 이후 바뀐 칸」 비교
(``beat_grid_send.beat_grid_cell_snapshot``)도 이 키들을 뺀다.
"""

from __future__ import annotations

from collections.abc import Mapping

from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import LoveAttackPlan, build_preset_plan, load_preset_annotations

__all__ = ["attach_planned_marks"]

_CellKey = tuple[str, int]


def _valid_rgb(rgb: object) -> bool:
    """세 채널이 모두 0~100 사이의 수(콘솔 퍼센트)인가. 아니면 색을 싣지 않는다."""
    if not isinstance(rgb, (tuple, list)) or len(rgb) != 3:
        return False
    return all(
        not isinstance(channel, bool) and isinstance(channel, (int, float)) and 0 <= channel <= 100
        for channel in rgb
    )


def _planned_names(
    plan: LoveAttackPlan,
) -> tuple[dict[_CellKey, set[tuple[float, ...]]], dict[_CellKey, str], dict[_CellKey, str]]:
    """계획표에서 칸마다 계획 색(RGB 목록), 계획 디머 이름, 계획 위치 이름을 모은다."""
    colors: dict[_CellKey, set[tuple[float, ...]]] = {}
    dimmers: dict[_CellKey, str] = {}
    positions: dict[_CellKey, str] = {}
    for preset in plan.presets:
        for cell in preset.cells:
            key = (cell.group_name, cell.bar)
            if preset.kind == "color" and preset.rgb is not None:
                colors.setdefault(key, set()).add(tuple(preset.rgb))
            elif preset.kind == "dimmer":
                dimmers.setdefault(key, preset.name)
            elif preset.kind == "position":
                positions.setdefault(key, preset.name)
    return colors, dimmers, positions


def _marks_for_cue(
    cue: Mapping[str, object],
    key: _CellKey,
    colors: Mapping[_CellKey, set[tuple[float, ...]]],
    dimmers: Mapping[_CellKey, str],
    positions: Mapping[_CellKey, str],
) -> dict[str, object]:
    """한 칸에 얹을 계획 표시. 콘솔 번호가 이미 있는 자리에는 계획 표시를 붙이지 않는다."""
    marks: dict[str, object] = {}
    rgbs = colors.get(key, set())
    # 계획 색이 둘 이상이면 어느 색인지 지어내지 않는다(칠하지 않음).
    if len(rgbs) == 1 and cue.get("color_preset_no") is None and cue.get("color_rgb") is None:
        (rgb,) = rgbs
        if _valid_rgb(rgb):
            marks["color_rgb"] = list(rgb)
            marks["color_planned"] = True
    brightness = cue.get("brightness")
    if key in dimmers and isinstance(brightness, Mapping) and brightness.get("preset_no") is None:
        marks["planned_dimmer_name"] = dimmers[key]
    if key in positions and cue.get("position_preset_no") is None:
        marks["planned_position_name"] = positions[key]
    return marks


def attach_planned_marks(grid: Mapping[str, object], song_title: object) -> dict[str, object]:
    """격자 사본의 칸에 계획 표시를 얹는다(원본 불변).

    ``song_title`` 은 계획 주석 파일을 고르는 열쇠다. 계획 주석이 없는 곡이면 키를 하나도 더하지
    않고 격자를 복사해 돌려준다."""
    tracks = grid.get("tracks")
    annotations = load_preset_annotations(song_title)
    if not annotations or not isinstance(tracks, list):
        return dict(grid)
    plan = build_preset_plan(
        grid,
        annotations=annotations,
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=None,
        position_pool=None,
        dimmer_attributes={},
    )
    colors, dimmers, positions = _planned_names(plan)
    new_tracks: list[object] = []
    for track in tracks:
        if not isinstance(track, Mapping) or not isinstance(track.get("cues"), list):
            new_tracks.append(track)
            continue
        group = str(track.get("group_name"))
        new_cues: list[object] = []
        for cue in track["cues"]:
            bar = cue.get("bar") if isinstance(cue, Mapping) else None
            if isinstance(cue, Mapping) and isinstance(bar, int) and not isinstance(bar, bool):
                marks = _marks_for_cue(cue, (group, bar), colors, dimmers, positions)
                new_cues.append({**cue, **marks} if marks else cue)
            else:
                new_cues.append(cue)
        new_tracks.append({**track, "cues": new_cues})
    return {**grid, "tracks": new_tracks}
