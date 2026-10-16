"""배치 초안 생성기 — SPEC-LDARRANGE-001 첫 묶음(데이터 모양·생성 함수, 순수 계산).

마디 지도(``timeline["bar_map"]``)와 트랙 구성(콘솔 그룹 트랙 목록)을 받아 「트랙 × 마디」
초안을 만든다. 파일을 쓰지 않고, 콘솔에 닿지 않고, 아무것도 저장하지 않는다. 같은 입력이면
같은 결과다.

출력 트랙과 칸은 박자 격자의 모양(``BeatGridTrack``·``BeatGridCue``)을 그대로 따른다. 모든
마디의 모든 칸을 채운다. 쉬는 칸은 명시적 쉼(「—」)이고, 정지·유지 칸은 값이다. 칸의 라벨과
구조화 값(밝기·진입·움직임)은 같은 규칙 결정(``_cell_plan``)에서 함께 나온다.

- 구간은 마디 4개씩 고정으로 나눈다. 구간마다 주인공 층 하나와 보조 층 하나가 움직이고,
  드롭 구간에서만 셋이 움직인다(규칙 3). 주인공은 펄스 → 체이스 → 움직임 순으로 바뀐다(규칙 4).
- 움직임 층은 두 무빙 중 하나만 움직이고 다른 쪽은 정지한다. 움직임 구간마다 교대한다
  (배치 규칙서 §5 벌스 무빙 기본안). 그래서 리듬을 타는 트랙은 구간당 둘(드롭은 셋)을 넘지 않는다.
- 강조(BLIND·STROBE)는 임팩트 마디에만 둔다. 임팩트는 킥 진입 마디(BLIND)와 드롭 시작
  마디(STROBE)다(spec.md §5 항목 1). 느린 곡이면 스트로브를 두지 않는다(REQ-LDARRANGE-007).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple, TypedDict

from server.audio.bar_map_store import validate_bar_map
from server.design.arrange_policy import ArrangementPolicy
from server.design.beat_grid import (
    BeatGridCue,
    BeatGridTrack,
    find_overlapping_group_tracks,
    normalize_beat_grid_cue,
)
from server.design.rig import RIG_LAYER_ROLES

__all__ = [
    "ArrangementDraft",
    "ArrangementWindow",
    "generate_arrangement_draft",
]

#: 칸이 쉰다는 명시적 표식(AC-LDARRANGE-002).
REST_LABEL = "—"
#: 무빙이 제자리에 서 있는 칸(움직이지 않음).
HOLD_LABEL = "정지"
#: 얼굴 빛·워시처럼 구간 내내 켜 두는 칸.
STATIC_LABEL = "유지"
PULSE_LABEL = "펄스 1·2·4박"
CHASE_LABEL = "체이스 2·4박"
MOTION_LABEL = "팬 웨이브 2마디"
BLIND_LABEL = "블라인드 2박"
STROBE_LABEL = "스트로브 1마디"

#: 마디 지도가 없을 때 화면에 보일 안내(AC-LDARRANGE-015).
UNCONFIRMED_NOTE = "마디 지도 미확정"
#: 출처 표식. 손 배치(``beat_grid_data``)와 구분한다.
SOURCE = "arrangement_generator"

_PULSE = "pulse"
_CHASE = "chase"
_MOTION = "motion"

#: 정적 역할. 리듬을 타지 않고 구간 내내 켜 둔다.
_STATIC_ROLES = frozenset({"key", "audience", "wash"})

#: 무빙 칸의 움직임 모양과 축. 「팬 웨이브」 규칙값이고 곡 전용 값이 아니다.
_MOTION_SHAPE = "wave"
_MOTION_AXES = ("pan",)
# 밝기·트리거·움직임 주기 같은 숫자는 ``ArrangementPolicy`` 에 든다(REQ-LDARRANGE-004).
# 펄스·체이스의 패턴은 효과 프리셋의 몫이라 여기서는 밝기만 정한다.
# 효과·위치·색 번호는 콘솔에서 와야 하므로 지어내지 않는다.


class ArrangementWindow(TypedDict):
    """4마디 구간 하나의 배치 결정. 주인공과 움직이는 층을 담는다."""

    start_bar: int
    end_bar: int
    #: 주인공 층("pulse" | "chase" | "motion"). 리듬 트랙이 없으면 None.
    lead: str | None
    #: 이 구간에서 움직이는 리듬 층(주인공과 보조, 드롭이면 셋).
    active: list[str]
    #: 드롭 마디와 겹치는 구간인가.
    drop: bool


class ArrangementDraft(TypedDict):
    """배치 초안. ``tracks`` 는 박자 격자와 같은 모양이고, ``windows`` 는 구간별 결정이다."""

    tracks: list[BeatGridTrack]
    windows: list[ArrangementWindow]
    bar_range: dict[str, int]
    source: str
    #: 정상이면 None, 마디 지도가 없거나 쓸 수 없으면 안내 문장.
    note: str | None


class _CellPlan(NamedTuple):
    """칸 하나의 규칙 결정. 라벨과 구조화 값을 한 곳에서 함께 만든다.

    라벨에서 값을 역산하지 않는다.
    """

    label: str
    brightness_percent: int
    movement_shape: str | None
    #: 어느 규칙 칸인지. 칸의 ``source_ref`` 로 남아 감독이 출처를 본다.
    kind: str


# @MX:NOTE: [AUTO] 마디 지도와 트랙 구성만 받는 순수 함수다. 파일이나 콘솔에 닿지 않는다.
def generate_arrangement_draft(
    bar_map: Mapping[str, Any] | None,
    layout: Sequence[Mapping[str, Any]],
    policy: ArrangementPolicy | None = None,
) -> ArrangementDraft:
    """마디 지도와 트랙 구성을 「트랙 × 마디」 초안으로 바꾼다.

    - 마디 지도가 없거나 저장 모양 검증을 통과하지 못하면 빈 초안과 안내 문장을 돌려준다.
      예외를 던지지 않는다(AC-LDARRANGE-015).
    - ``layout`` 의 항목은 ``group_no``·``group_no_confirmed``·``group_name``·``layer_role``
      을 가진다. 같은 장비를 두 트랙이 잡는 겹침이나 모르는 역할 이름이 있으면 ``ValueError``
      다(AC-LDARRANGE-014).
    """
    settings = ArrangementPolicy() if policy is None else policy
    if bar_map is None:
        return _unconfirmed(UNCONFIRMED_NOTE)
    problem = validate_bar_map(bar_map)
    if problem is not None:
        return _unconfirmed(f"{UNCONFIRMED_NOTE}: {problem}")
    _check_layout(layout)

    bar_numbers = sorted(int(entry["bar"]) for entry in bar_map["bars"])
    events = list(bar_map["events"])
    kick_bars = {int(event["start_bar"]) for event in events if event["kind"] == "kick_entry"}
    drop_ranges = [
        (int(event["start_bar"]), int(event["end_bar"]))
        for event in events
        if event["kind"] == "drop"
    ]
    drop_starts = {start for start, _end in drop_ranges}

    voices = _voices(layout)
    movers = [str(track["group_name"]) for track in layout if track.get("layer_role") == "mover"]
    plans: dict[str, dict[int, _CellPlan]] = {str(track["group_name"]): {} for track in layout}
    windows: list[ArrangementWindow] = []
    motion_turn = 0
    for window_id in sorted({bar // settings.window_bars for bar in bar_numbers}):
        bars_here = [bar for bar in bar_numbers if bar // settings.window_bars == window_id]
        start, end = bars_here[0], bars_here[-1]
        is_drop = any(
            start <= drop_end and drop_start <= end for drop_start, drop_end in drop_ranges
        )
        cap = settings.drop_layer_cap if is_drop else settings.base_layer_cap
        lead_index = window_id % len(voices) if voices else 0
        active = [
            voices[(lead_index + offset) % len(voices)] for offset in range(min(cap, len(voices)))
        ]
        moving: str | None = None
        if _MOTION in active:
            moving = movers[motion_turn % len(movers)]
            motion_turn += 1
        windows.append(
            ArrangementWindow(
                start_bar=start,
                end_bar=end,
                lead=voices[lead_index] if voices else None,
                active=active,
                drop=is_drop,
            )
        )
        for track in layout:
            name = str(track["group_name"])
            for bar in bars_here:
                plans[name][bar] = _cell_plan(
                    track,
                    active=active,
                    moving=moving,
                    is_kick=bar in kick_bars,
                    is_drop_start=bar in drop_starts,
                    settings=settings,
                )

    tracks = [
        BeatGridTrack(
            group_no=track.get("group_no"),
            group_no_confirmed=bool(track.get("group_no_confirmed", False)),
            group_name=str(track["group_name"]),
            layer_role=track.get("layer_role"),
            cues=[
                _draft_cue(bar, plans[str(track["group_name"])][bar], settings)
                for bar in bar_numbers
            ],
        )
        for track in layout
    ]
    return ArrangementDraft(
        tracks=tracks,
        windows=windows,
        bar_range={"start": bar_numbers[0], "end": bar_numbers[-1]},
        source=SOURCE,
        note=None,
    )


def _unconfirmed(note: str) -> ArrangementDraft:
    return ArrangementDraft(tracks=[], windows=[], bar_range={}, source=SOURCE, note=note)


def _check_layout(layout: Sequence[Mapping[str, Any]]) -> None:
    for track in layout:
        role = track.get("layer_role")
        if role is not None and role not in RIG_LAYER_ROLES:
            raise ValueError(f"모르는 층 역할입니다: {role}")
    overlap = find_overlapping_group_tracks([str(track["group_name"]) for track in layout])
    if overlap is not None:
        raise ValueError(f"같은 장비를 겹쳐 잡는 트랙입니다: {overlap[0]}, {overlap[1]}")


def _voices(layout: Sequence[Mapping[str, Any]]) -> list[str]:
    """이 구성에 있는 리듬 층을 주인공 교대 순서(펄스 → 체이스 → 움직임)로 돌려준다."""
    roles = {track.get("layer_role") for track in layout}
    ordered = [(_PULSE, "back"), (_CHASE, "side"), (_MOTION, "mover")]
    return [voice for voice, role in ordered if role in roles]


def _rest_plan(settings: ArrangementPolicy, kind: str = "rest") -> _CellPlan:
    return _CellPlan(REST_LABEL, settings.rest_percent, None, kind)


def _cell_plan(
    track: Mapping[str, Any],
    *,
    active: Sequence[str],
    moving: str | None,
    is_kick: bool,
    is_drop_start: bool,
    settings: ArrangementPolicy,
) -> _CellPlan:
    role = track.get("layer_role")
    name = str(track["group_name"])
    lit = settings.lit_percent
    if role == "back":
        if _PULSE in active:
            return _CellPlan(PULSE_LABEL, lit, None, "pulse")
        return _rest_plan(settings)
    if role == "side":
        if _CHASE in active:
            return _CellPlan(CHASE_LABEL, lit, None, "chase")
        return _rest_plan(settings)
    if role == "mover":
        if moving == name:
            return _CellPlan(MOTION_LABEL, lit, _MOTION_SHAPE, "motion")
        return _CellPlan(HOLD_LABEL, lit, None, "hold")
    if role == "effect":
        if "STROBE" in name.upper():
            if is_drop_start and not settings.slow_song:
                return _CellPlan(STROBE_LABEL, lit, None, "strobe")
            return _rest_plan(settings)
        if is_kick:
            return _CellPlan(BLIND_LABEL, lit, None, "blind")
        return _rest_plan(settings)
    if role in _STATIC_ROLES:
        return _CellPlan(STATIC_LABEL, lit, None, "static")
    return _rest_plan(settings)


def _draft_cue(bar: int, plan: _CellPlan, settings: ArrangementPolicy) -> BeatGridCue:
    """규칙 결정 하나를 격자 칸으로 옮긴다. 값은 이 결정에서만 온다."""
    raw: dict[str, object] = {
        "bar": bar,
        "label": plan.label,
        "brightness": {"mode": "value", "value_percent": plan.brightness_percent},
        "entry": {"trigger_beat": settings.downbeat_trigger},
        "source_ref": f"{SOURCE}:{plan.kind}",
    }
    if plan.movement_shape is not None:
        raw["app_movement"] = {
            "shape": plan.movement_shape,
            "axes": _MOTION_AXES,
            "period_unit": "bar",
            "period_value": settings.motion_period_bars,
        }
    return normalize_beat_grid_cue(raw)
