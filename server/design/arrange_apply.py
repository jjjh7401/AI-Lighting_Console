"""배치 초안을 격자에 반영하는 적용 함수 — SPEC-LDARRANGE-001 두 번째 묶음.

기존 격자 편집(``apply_beat_grid_edit_range``)은 이미 있는 칸만 고친다. 자동 배치 초안은 칸이
없는 마디에도 칸을 만들어야 하므로 별도 함수로 둔다. 전부 맞거나 전부 안 바뀐다. 원본 격자는
건드리지 않고 새 사전을 돌려준다.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from server.design.arrange_generator import ArrangementDraft
from server.design.beat_grid import normalize_beat_grid_cue, validate_beat_grid_tracks

__all__ = ["ArrangementApplyError", "apply_arrangement_draft"]


class ArrangementApplyError(ValueError):
    """초안을 격자에 반영하지 못했다. 사유는 한국어 문장 하나다."""


def _union_bar_range(
    grid_range: Mapping[str, Any] | None, draft_range: Mapping[str, Any]
) -> dict[str, int]:
    """격자 데이터 범위와 초안 범위를 합친다. 격자 범위를 줄이지는 않는다.

    「채운 범위」와 「N마디~ 아직 배치 안 함」은 ``bar_range`` 로 그린다. 칸을 넣고도 이 값을
    옛 기본값(0~25)에 두면 칸이 있는 마디가 빗금으로 보인다.
    """
    if not grid_range:
        return {"start": int(draft_range["start"]), "end": int(draft_range["end"])}
    return {
        "start": min(int(grid_range["start"]), int(draft_range["start"])),
        "end": max(int(grid_range["end"]), int(draft_range["end"])),
    }


_PRESET_KEYS = (
    "position_preset_no",
    "color_preset_no",
    "effect_preset_no",
    "effect_kind",
    "app_movement",
)


def _has_structured_value(cue: Mapping[str, Any]) -> bool:
    """칸에 구조화 값(밝기·프리셋·진입·움직임) 가운데 하나라도 있는가."""
    brightness = cue.get("brightness") or {}
    entry = cue.get("entry") or {}
    if brightness.get("mode") is not None:
        return True
    if any(cue.get(key) is not None for key in _PRESET_KEYS):
        return True
    return any(value is not None for value in entry.values())


def director_blank_cells(default_grid: Mapping[str, Any]) -> frozenset[tuple[str, int]]:
    """감독 원본(곡 기본 격자)에서 구조화 값 없이 비워 둔 칸 — (트랙 이름, 마디) 집합이다.

    이 칸은 감독이 비워 둔 것이라 자동 배치가 채우지 않는다. 송신하지 않고 숫자로만 보인다.
    """
    blanks: set[tuple[str, int]] = set()
    for track in default_grid.get("tracks") or []:
        name = str(track["group_name"])
        for cue in track.get("cues") or []:
            if not _has_structured_value(cue):
                blanks.add((name, int(cue["bar"])))
    return frozenset(blanks)


def _is_placeholder(cue: Mapping[str, Any], track_name: str, director_blanks: frozenset) -> bool:
    """구조화 값이 하나도 없고 감독 원본의 빈 칸도 아닌 칸 — 이전 적용이 남긴 빈 칸이다.

    사람이 넣은 값이 있는 칸은 건드리지 않는다. 감독이 비워 둔 칸도 건드리지 않는다.
    나머지 빈 칸은 초안 값으로 채운다.
    """
    if (track_name, int(cue["bar"])) in director_blanks:
        return False
    return not _has_structured_value(cue)


# @MX:NOTE: [AUTO] 초안 한 단위를 격자에 한꺼번에 반영한다. 원본 격자는 바꾸지 않는다.
def apply_arrangement_draft(
    grid: Mapping[str, Any],
    draft: ArrangementDraft,
    *,
    director_blanks: frozenset = frozenset(),
) -> tuple[dict[str, Any], list[str]]:
    """초안 한 단위를 격자에 반영하고, 새 격자와 한국어 보고를 돌려준다.

    - 이름이 같은 트랙이 있으면 그 트랙의 칸을 고치고, 없으면 트랙을 새로 만든다.
    - 칸이 없는 마디에는 칸을 새로 만든다. 있는 칸은 라벨만 초안 값으로 바꾸고, 밝기·프리셋
      같은 구조화 필드는 그대로 둔다(사람이 넣은 값을 지우지 않는다).
    - 구조화 값이 하나도 없는 빈 칸은 초안 값으로 채운다(이전 적용이 남긴 칸). 단 감독 원본의
      빈 칸(``director_blanks``)은 그대로 둔다.
    - 격자 데이터 범위(``bar_range``)도 초안 범위까지 넓힌다. 줄이지는 않는다.
    - 결과가 트랙 검증(같은 장비를 겹쳐 잡는 트랙)을 통과하지 못하면 ``ArrangementApplyError``다.
      어떤 경우에도 원본 격자는 바뀌지 않는다.
    """
    tracks = [copy.deepcopy(dict(track)) for track in grid.get("tracks") or []]
    by_name = {str(track["group_name"]): track for track in tracks}
    created_tracks = created_cells = changed_cells = 0
    for draft_track in draft["tracks"]:
        name = str(draft_track["group_name"])
        track = by_name.get(name)
        if track is None:
            track = {
                "group_no": draft_track["group_no"],
                "group_no_confirmed": draft_track["group_no_confirmed"],
                "group_name": name,
                "layer_role": draft_track["layer_role"],
                "cues": [],
            }
            tracks.append(track)
            by_name[name] = track
            created_tracks += 1
        cues_by_bar = {cue["bar"]: cue for cue in track["cues"]}
        for draft_cue in draft_track["cues"]:
            bar = draft_cue["bar"]
            label = draft_cue["label"]
            existing = cues_by_bar.get(bar)
            if existing is None or _is_placeholder(existing, name, director_blanks):
                cues_by_bar[bar] = normalize_beat_grid_cue(dict(draft_cue))
                created_cells += 1
                continue
            if existing["label"] != label:
                changed_cells += 1
            updated_cue = {**existing, "label": label}
            # 계획 위치는 계획 값이라 기존 칸에도 얹는다. 위치 번호·구조값은 건드리지 않는다.
            if "planned_position" in draft_cue:
                updated_cue["planned_position"] = draft_cue["planned_position"]
            cues_by_bar[bar] = updated_cue
        track["cues"] = [cues_by_bar[bar] for bar in sorted(cues_by_bar)]

    reason = validate_beat_grid_tracks(tracks)
    if reason is not None:
        raise ArrangementApplyError(reason)
    updated = dict(grid)
    updated["tracks"] = tracks
    if draft.get("bar_range"):
        updated["bar_range"] = _union_bar_range(grid.get("bar_range"), draft["bar_range"])
    report = f"자동 배치 칸 {created_cells}개를 새로 만들고 {changed_cells}개의 라벨을 바꿨습니다"
    if created_tracks:
        report += f", 트랙 {created_tracks}개를 새로 만들었습니다"
    return updated, [report]
