"""자동 배치 규칙으로 만드는 AI 제안 소스 — 선택한 마디·줄 한 칸(SPEC-LDBEAT-001 M3 후속).

근거는 자동 배치 생성기(``generate_arrangement_draft``)와 마디 지도다. 생성기가 그 마디·줄에
고르는 칸 종류를, 편집 경로가 받는 구조화 필드 ``effect_kind`` 로 옮기는 제안만 만든다.
제안은 기존 보류 흐름(``PendingSuggestionStore``)에 담기고, 「적용」은 기존 편집 경로
(``apply_beat_grid_edit``)가 맡는다. 이 모듈은 격자와 콘솔에 쓰지 않는다.

라벨 문자열(예: "스트로브 1마디")은 편집 경로가 받는 필드가 아니라서 제안으로 바꾸지 않는다.
대신 제안 이유(rationale)에 생성기가 고른 라벨을 그대로 적는다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from server.design.arrange_generator import (
    BLIND_LABEL,
    CHASE_LABEL,
    HOLD_LABEL,
    MOTION_LABEL,
    PULSE_LABEL,
    REST_LABEL,
    STATIC_LABEL,
    STROBE_LABEL,
    generate_arrangement_draft,
)

__all__ = ["ArrangementRuleSuggestionSource"]

#: 생성기 칸 라벨 → 구조화 효과 종류(``effect_kind``). 값은 콘솔 풀 이름과 맞춘다
#: (``beat_grid_presets._POOL_NAME_TO_EFFECT_KIND``): 움직임 → 위치, 밝기 계열 → 디머.
#: 체이스는 여러 속성이 섞이는 「All 1」(혼합) 풀로 본다 — 이 한 줄은 해석이라 확인이 필요하다.
#: ``None`` 은 효과 없는 칸(꺼짐·정지·유지)이라 효과 종류를 지운다는 뜻이다.
_EFFECT_KIND_FOR_LABEL: dict[str, str | None] = {
    MOTION_LABEL: "position",
    PULSE_LABEL: "dimmer",
    BLIND_LABEL: "dimmer",
    STROBE_LABEL: "dimmer",
    CHASE_LABEL: "mixed",
    REST_LABEL: None,
    HOLD_LABEL: None,
    STATIC_LABEL: None,
}

_EFFECT_KIND_NAMES: dict[str, str] = {
    "position": "위치",
    "color": "색",
    "dimmer": "디머",
    "mixed": "혼합",
}


class ArrangementRuleSuggestionSource:
    """``SuggestionSource`` 구현 — 자동 배치 규칙으로 한 칸을 제안한다.

    ``bar_map_of`` 는 지금 열린 곡의 마디 지도를 돌려준다(없으면 ``None``). 다음 경우엔
    제안이 없다(``None``): 마디 지도가 없음, 트랙 구성이 없음, 생성기가 거절함, 줄 이름이
    트랙과 맞지 않음, 그 마디에 규칙 칸이 없음, 규칙과 현재 칸이 이미 같음.
    """

    def __init__(self, bar_map_of: Callable[[], Mapping[str, object] | None]) -> None:
        self._bar_map_of = bar_map_of

    def __call__(
        self, grid: Mapping[str, object], bar: int, target: str
    ) -> tuple[dict[str, object], str] | None:
        bar_map = self._bar_map_of()
        tracks = list(grid.get("tracks") or [])
        if bar_map is None or not tracks:
            return None
        try:
            draft = generate_arrangement_draft(bar_map, tracks)
        except ValueError:
            # 겹치는 장비·모르는 역할 같은 트랙 구성 오류 — 규칙을 적용할 수 없으니 제안도 없다.
            return None
        if draft["note"] is not None:
            return None
        name = target.casefold()
        draft_track = next(
            (track for track in draft["tracks"] if str(track["group_name"]).casefold() == name),
            None,
        )
        if draft_track is None:
            return None
        draft_cue = next((cue for cue in draft_track["cues"] if cue["bar"] == bar), None)
        if draft_cue is None or draft_cue["label"] not in _EFFECT_KIND_FOR_LABEL:
            return None
        label = str(draft_cue["label"])
        wanted = _EFFECT_KIND_FOR_LABEL[label]
        if wanted == _current_effect_kind(tracks, name, bar):
            return None
        return {"effect_kind": wanted}, _rationale(bar_map, bar, target, label, wanted)


def _current_effect_kind(tracks: list[Mapping[str, object]], name: str, bar: int) -> object:
    """격자에 적힌 그 줄·그 마디의 효과 종류. 칸이 없으면 ``None``."""
    for track in tracks:
        if str(track.get("group_name", "")).casefold() != name:
            continue
        for cue in track.get("cues") or []:
            if isinstance(cue, Mapping) and cue.get("bar") == bar:
                return cue.get("effect_kind")
    return None


def _rationale(
    bar_map: Mapping[str, object], bar: int, target: str, label: str, wanted: str | None
) -> str:
    context = _context(bar_map.get("events") or [], bar)
    if wanted is None:
        action = "효과 종류를 지웁니다."
    else:
        name = _EFFECT_KIND_NAMES[wanted]
        action = f"효과 종류를 {name}({wanted}){_ro(name)} 맞춥니다."
    return f"{bar}마디 {target}: {context}입니다. 자동 배치 규칙 라벨은 '{label}'입니다. {action}"


def _ro(word: str) -> str:
    """한글 낱말 끝소리에 맞춘 방향 조사 — 받침이 있으면 「으로」, 없으면 「로」."""
    return "으로" if (ord(word[-1]) - 0xAC00) % 28 else "로"


def _context(events: object, bar: int) -> str:
    """마디가 곡 안에서 어떤 자리인지 한 구절로. 드롭 > 킥 진입 > 킥 멈춤 > 빌드업 순으로 고른다."""
    items = (
        [event for event in events if isinstance(event, Mapping)]
        if isinstance(events, list)
        else []
    )
    for event in items:
        start, end = int(event["start_bar"]), int(event["end_bar"])
        if event.get("kind") == "drop" and start <= bar <= end:
            return (
                f"드롭 시작 마디(드롭 {start}~{end})"
                if bar == start
                else f"드롭 구간 안(드롭 {start}~{end})"
            )
    for event in items:
        if event.get("kind") == "kick_entry" and int(event["start_bar"]) == bar:
            return "킥 진입 마디"
    for event in items:
        if event.get("kind") == "break" and int(event["start_bar"]) == bar:
            return "킥 멈춤 마디"
    for event in items:
        start, end = int(event["start_bar"]), int(event["end_bar"])
        if event.get("kind") == "build" and start <= bar <= end:
            return f"빌드업 구간({start}~{end})"
    return "보통 구간"
