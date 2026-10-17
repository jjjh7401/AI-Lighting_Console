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

__all__ = ["ArrangementApplyError", "apply_arrangement_draft", "is_director_edited"]


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


#: 감독이 손으로 고친 칸을 「⇪ 콘솔에 반영」 승인이 남기는 출처 머리말이다.
_DIRECTOR_APPROVAL_PREFIX = "beat_grid_apply:"


_PRESET_KEYS = ("position_preset_no", "color_preset_no", "effect_preset_no")


def _has_preset_number(cue: Mapping[str, Any]) -> bool:
    brightness = cue.get("brightness") or {}
    return brightness.get("preset_no") is not None or any(
        cue.get(key) is not None for key in _PRESET_KEYS
    )


def is_director_edited(cue: Mapping[str, Any]) -> bool:
    """감독이 직접 고친 칸인가.

    - 콘솔 반영까지 승인한 손 편집은 ``evidence.approval.source`` 에 ``beat_grid_apply:`` 를
      남긴다(여러 출처는 `` | `` 로 이어진다).
    - 아직 승인 전인 손 편집은 프리셋 번호가 있는데 승인 기록이 없다(편집이 낡은 승인을 지운다).
      초안 칸은 번호를 싣지 않고, 프리셋 계획이 붙인 번호는 ``preset_plan:`` 승인이 함께 남는다.

    프리셋 계획(``preset_plan:``)·시드 근거 표시만 있는 칸은 손 편집이 아니다.
    """
    approval = (cue.get("evidence") or {}).get("approval") or {}
    source = str(approval.get("source") or "")
    if not source:
        return _has_preset_number(cue)
    return any(part.strip().startswith(_DIRECTOR_APPROVAL_PREFIX) for part in source.split("|"))


def _draft_bounds(draft: ArrangementDraft, draft_cues: list[Mapping[str, Any]]) -> tuple[int, int]:
    """교체할 마디 범위 — 초안 범위, 없으면 초안 칸의 첫·마지막 마디다."""
    bar_range = draft.get("bar_range") or {}
    if "start" in bar_range and "end" in bar_range:
        return int(bar_range["start"]), int(bar_range["end"])
    bars = [int(cue["bar"]) for cue in draft_cues]
    return min(bars), max(bars)


# @MX:NOTE: [AUTO] 초안 범위의 줄을 초안 칸으로 교체한다. 감독이 고친 칸만 남는다.
def apply_arrangement_draft(
    grid: Mapping[str, Any],
    draft: ArrangementDraft,
) -> tuple[dict[str, Any], list[str]]:
    """초안 한 단위를 격자에 반영하고, 새 격자와 한국어 보고를 돌려준다.

    - 이름이 같은 트랙이 있으면 그 트랙을, 없으면 트랙을 새로 만든다.
    - 초안 범위 안에서 그 줄의 칸을 초안 칸으로 **교체**한다. 손 설계 시드 칸·이전 초안 칸은
      지운다 — 남겨 두면 그 사이에 새 칸이 끼어 칸이 조각난다. 감독이 고쳐 승인한 칸
      (``is_director_edited``)만 그대로 두고, 그 마디의 초안 칸은 넣지 않는다.
    - 범위 밖의 칸은 건드리지 않는다. 같은 초안을 두 번 적용해도 결과가 같다.
    - 격자 데이터 범위(``bar_range``)도 초안 범위까지 넓힌다. 줄이지는 않는다.
    - 결과가 트랙 검증(같은 장비를 겹쳐 잡는 트랙)을 통과하지 못하면 ``ArrangementApplyError``다.
      어떤 경우에도 원본 격자는 바뀌지 않는다.
    """
    tracks = [copy.deepcopy(dict(track)) for track in grid.get("tracks") or []]
    by_name = {str(track["group_name"]): track for track in tracks}
    created_tracks = placed_cells = removed_cells = kept_cells = 0
    for draft_track in draft["tracks"]:
        name = str(draft_track["group_name"])
        draft_cues = list(draft_track["cues"])
        if not draft_cues:
            continue
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
        first, last = _draft_bounds(draft, draft_cues)
        cues_by_bar: dict[int, Any] = {}
        for cue in track["cues"]:
            bar = int(cue["bar"])
            if first <= bar <= last and not is_director_edited(cue):
                removed_cells += 1
                continue
            if first <= bar <= last:
                kept_cells += 1
            cues_by_bar[bar] = cue
        for draft_cue in draft_cues:
            bar = int(draft_cue["bar"])
            if bar in cues_by_bar:
                # 감독 칸은 그대로 두되, 계획 위치는 계획 값이라 얹는다(번호·구조값은 그대로).
                if first <= bar <= last and "planned_position" in draft_cue:
                    cues_by_bar[bar] = {
                        **cues_by_bar[bar],
                        "planned_position": draft_cue["planned_position"],
                    }
                    # 방향 값을 가진 감독 칸은 방향 값의 위치도 같이 간다(둘이 어긋나지 않게).
                    direction = cues_by_bar[bar].get("direction")
                    new_position = (draft_cue.get("direction") or {}).get("position")
                    if isinstance(direction, dict) and new_position is not None:
                        cues_by_bar[bar]["direction"] = {**direction, "position": new_position}
                continue
            cues_by_bar[bar] = normalize_beat_grid_cue(dict(draft_cue))
            placed_cells += 1
        track["cues"] = [cues_by_bar[bar] for bar in sorted(cues_by_bar)]

    reason = validate_beat_grid_tracks(tracks)
    if reason is not None:
        raise ArrangementApplyError(reason)
    updated = dict(grid)
    updated["tracks"] = tracks
    if draft.get("bar_range"):
        updated["bar_range"] = _union_bar_range(grid.get("bar_range"), draft["bar_range"])
    # 콘솔 그룹 대조 결과는 적용 뒤에도 격자에 남는다 — 빠진 장비 안내가 초안 카드와 함께
    # 사라지면 조용히 빠진 것과 같다(카드 WT-all-fixtures). 다음 초안 적용이 덮어쓴다.
    if "console_coverage" in draft:
        updated["console_coverage"] = copy.deepcopy(draft["console_coverage"])
    report = (
        f"자동 배치 칸 {placed_cells}개를 새로 만들고 기존 칸 {removed_cells}개를 지웠습니다"
        f"(감독이 고친 칸 {kept_cells}개는 그대로)"
    )
    if created_tracks:
        report += f", 트랙 {created_tracks}개를 새로 만들었습니다"
    return updated, [report]
