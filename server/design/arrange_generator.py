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
- 켜는 칸마다 계획 색(콘솔 퍼센트 RGB)을 붙인다. 쉬는 칸에는 붙이지 않는다. 우선순위는 곡별 주석
  색(칸 하나) > 역광 역할(BACK) > 구간 색이다. 구간 색은 구간 종류(드롭·브릿지·마지막 후렴·후렴·
  벌스)에서 나온다. 계획 색은 콘솔 값이 아니라 화면 표시용이라 콘솔에 보내지 않는다.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple, NotRequired, TypedDict

from server.audio.bar_map_store import validate_bar_map
from server.design.arrange_policy import ArrangementPolicy
from server.design.beat_grid import (
    BeatGridCue,
    BeatGridTrack,
    find_overlapping_group_tracks,
    normalize_beat_grid_cue,
)
from server.design.cell_direction import (
    BASIC_WORDS,
    assign_color_names,
    build_direction,
    direction_label,
)
from server.design.rig import RIG_LAYER_ROLES

__all__ = [
    "ArrangementDraft",
    "ArrangementWindow",
    "generate_arrangement_draft",
]

# 칸 이름은 방향 값에서 만든다(``cell_direction.direction_label``). 아래 상수는 그 말 표
# (``BASIC_WORDS``)의 이름표일 뿐 말을 따로 들지 않는다 — 규칙 제안
# (``beat_grid_suggestion_rules``)이 이 이름으로 칸을 알아본다.
#: 칸이 쉰다는 명시적 표식(AC-LDARRANGE-002).
REST_LABEL = BASIC_WORDS["rest"]
#: 무빙이 제자리에 서 있는 칸(움직이지 않음).
HOLD_LABEL = BASIC_WORDS["hold"]
#: 얼굴 빛·워시처럼 구간 내내 켜 두는 칸.
STATIC_LABEL = BASIC_WORDS["static"]
PULSE_LABEL = BASIC_WORDS["pulse"]
CHASE_LABEL = BASIC_WORDS["chase"]
MOTION_LABEL = BASIC_WORDS["motion"]
BLIND_LABEL = BASIC_WORDS["blind"]
STROBE_LABEL = BASIC_WORDS["strobe"]

#: 마디 지도가 없을 때 화면에 보일 안내(AC-LDARRANGE-015).
UNCONFIRMED_NOTE = "마디 지도 미확정"
#: 출처 표식. 손 배치(``beat_grid_data``)와 구분한다.
SOURCE = "arrangement_generator"

#: 구간 종류. 마디 지도에는 벌스·후렴 이름이 없어서 이벤트와 마디 에너지로 어림한다.
_SECTION_DROP = "drop"
_SECTION_BRIDGE = "bridge"
_SECTION_LAST_CHORUS = "last_chorus"
_SECTION_CHORUS = "chorus"
_SECTION_VERSE = "verse"

_PULSE = "pulse"
_CHASE = "chase"
_MOTION = "motion"

#: 정적 역할. 리듬을 타지 않고 구간 내내 켜 둔다.
_STATIC_ROLES = frozenset({"key", "audience", "wash"})

#: 무빙 칸의 움직임 모양과 축. 「팬 웨이브」 규칙값이고 곡 전용 값이 아니다.
_MOTION_SHAPE = "wave"
_MOTION_AXES = ("Pan",)
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
    #: 콘솔 그룹 대조 결과(카드 WT-all-fixtures) — 새로 붙인 줄·빠진 장비와 이유·판독 공백.
    #: 세션이 초안을 만든 뒤 싣는다. 생성기는 이 키를 만들지 않는다.
    console_coverage: NotRequired[dict[str, Any]]


class _CellPlan(NamedTuple):
    """칸 하나의 규칙 결정. 라벨과 구조화 값을 한 곳에서 함께 만든다.

    라벨에서 값을 역산하지 않는다.
    """

    label: str
    brightness_percent: int
    movement_shape: str | None
    #: 어느 규칙 칸인지. 칸의 ``source_ref`` 로 남아 감독이 출처를 본다.
    kind: str
    #: 계획 색(콘솔 퍼센트 RGB). 쉬는 칸은 None 이다.
    color_rgb: tuple[int, int, int] | None = None
    #: 계획 위치(기본 위치 이름, 예: ``Center``). 무빙의 켜는 칸에만 있다. 쉬는 칸은 None 이다.
    position: str | None = None


# @MX:NOTE: [AUTO] 마디 지도와 트랙 구성만 받는 순수 함수다. 파일이나 콘솔에 닿지 않는다.
def generate_arrangement_draft(
    bar_map: Mapping[str, Any] | None,
    layout: Sequence[Mapping[str, Any]],
    policy: ArrangementPolicy | None = None,
    *,
    planned_colors: Mapping[tuple[str, int], tuple[int, int, int]] | None = None,
) -> ArrangementDraft:
    """마디 지도와 트랙 구성을 「트랙 × 마디」 초안으로 바꾼다.

    - 마디 지도가 없거나 저장 모양 검증을 통과하지 못하면 빈 초안과 안내 문장을 돌려준다.
      예외를 던지지 않는다(AC-LDARRANGE-015).
    - ``layout`` 의 항목은 ``group_no``·``group_no_confirmed``·``group_name``·``layer_role``
      을 가진다. 같은 장비를 두 트랙이 잡는 겹침이나 모르는 역할 이름이 있으면 ``ValueError``
      다(AC-LDARRANGE-014).
    - ``planned_colors`` 는 호출한 쪽이 건네는 「(트랙 이름, 마디) → 주석 색」이다. 켜는 칸에서는
      구간 색·역광 색보다 우선한다. 이 함수는 파일을 읽지 않는다.
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
    break_ranges = [
        (int(event["start_bar"]), int(event["end_bar"]))
        for event in events
        if event["kind"] == "break"
    ]
    energy = {
        int(entry["bar"]): float(entry["energy"]) for entry in bar_map["bars"] if "energy" in entry
    }
    overrides = planned_colors or {}
    relative_energy = _relative_energies(bar_numbers, energy, settings.window_bars)

    voices = _voices(layout)
    movers = [str(track["group_name"]) for track in layout if track.get("layer_role") == "mover"]
    plans: dict[str, dict[int, _CellPlan]] = {str(track["group_name"]): {} for track in layout}
    windows: list[ArrangementWindow] = []
    motion_turn = 0
    last_drop_end = max((end for _start, end in drop_ranges), default=None)
    last_chorus_turn = 0
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
        section = _section_kind(
            start,
            end,
            drop_ranges=drop_ranges,
            break_ranges=break_ranges,
            last_drop_end=last_drop_end,
            has_kick=any(bar in kick_bars for bar in bars_here),
            relative_energy=relative_energy.get(window_id),
            settings=settings,
        )
        # 마지막 후렴 돌림의 차례 = 이 구간보다 앞선 마지막 후렴 구간의 수. 브릿지는 세지 않는다.
        section_color = _section_color(section, last_chorus_turn, settings)
        if section == _SECTION_LAST_CHORUS:
            last_chorus_turn += 1
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
                    section_color=section_color,
                    override=overrides.get((name, bar)),
                )

    # 색 이름은 이 초안 전체의 색으로 한 번에 정한다 — 같은 색은 어느 칸에서나 같은 이름이다.
    color_names = assign_color_names(
        plan.color_rgb for by_bar in plans.values() for plan in by_bar.values() if plan.color_rgb
    )
    tracks = [
        BeatGridTrack(
            group_no=track.get("group_no"),
            group_no_confirmed=bool(track.get("group_no_confirmed", False)),
            group_name=str(track["group_name"]),
            layer_role=track.get("layer_role"),
            cues=[
                _draft_cue(
                    bar,
                    plans[str(track["group_name"])][bar],
                    settings,
                    role=track.get("layer_role"),
                    color_names=color_names,
                )
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
    """이 구성에 있는 리듬 층을 주인공 교대 순서(펄스 → 체이스 → 움직임)로 돌려준다.

    역할을 정하지 못한 줄(``layer_role`` 이 None)은 체이스 층이다 — 콘솔 그룹 이름이 리그마다
    달라서 이름으로 역할을 못 정해도 장비가 곡 내내 꺼져 있으면 안 된다(카드 WT-side-allocation).
    """
    roles = {track.get("layer_role") for track in layout}
    if None in roles:
        roles.add("side")
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
    section_color: tuple[int, int, int],
    override: tuple[int, int, int] | None = None,
) -> _CellPlan:
    role = track.get("layer_role")
    name = str(track["group_name"])
    lit = settings.lit_percent
    # 켜는 칸의 계획 색 — 주석 색 > 역광 역할 > 앞빛 역할 > 구간 색. 쉬는 칸에는 색이 없다.
    fixed = {"back": settings.palette.backlight, "key": settings.palette.key}.get(role)
    color = override or fixed or section_color
    if role == "back":
        if _PULSE in active:
            return _CellPlan(PULSE_LABEL, lit, None, "pulse", color)
        return _rest_plan(settings)
    # 역할을 정하지 못한 줄도 체이스 층으로 리듬에 들어간다(``_voices`` 와 같은 판단).
    if role == "side" or role is None:
        if _CHASE in active:
            return _CellPlan(CHASE_LABEL, lit, None, "chase", color)
        return _rest_plan(settings)
    if role == "mover":
        if moving == name:
            return _CellPlan(MOTION_LABEL, lit, _MOTION_SHAPE, "motion", color)
        return _CellPlan(HOLD_LABEL, lit, None, "hold", color)
    if role == "effect":
        if "STROBE" in name.upper():
            if is_drop_start and not settings.slow_song:
                return _CellPlan(STROBE_LABEL, lit, None, "strobe", color)
            return _rest_plan(settings)
        if is_kick:
            return _CellPlan(BLIND_LABEL, lit, None, "blind", color)
        return _rest_plan(settings)
    if role in _STATIC_ROLES:
        return _CellPlan(STATIC_LABEL, lit, None, "static", color)
    return _rest_plan(settings)


# @MX:NOTE: [AUTO] 후렴은 절대 에너지가 아니라 곡 안 상대 위치로 가른다. LOVE ATTACK 은 4마디 구간
# 평균이 전부 0.710~1.000 이라 절대 기준(0.6)이면 벌스가 하나도 없었다.
def _relative_energies(
    bar_numbers: Sequence[int], energy: Mapping[int, float], window_bars: int
) -> dict[int, float]:
    """구간(``bar // window_bars``)마다 곡 안 상대 에너지 위치(0~1)를 돌려준다.

    구간 평균은 에너지가 있는 마디만으로 잰다(없는 마디는 0 으로 세지 않고 뺀다). 평균이 가장 낮은
    구간이 0, 가장 높은 구간이 1이다. 에너지가 있는 구간이 없거나 구간 평균이 모두 같으면(평평한
    곡) 위치를 정할 수 없어 빈 사전이다. 에너지가 한 마디도 없는 구간도 사전에 없다. 호출한 쪽은
    ``get`` 으로 읽고, 없으면(None) 에너지로는 후렴이 되지 않는다.
    """
    by_window: dict[int, list[float]] = {}
    for bar in bar_numbers:
        if bar in energy:
            by_window.setdefault(bar // window_bars, []).append(energy[bar])
    means = {window_id: sum(values) / len(values) for window_id, values in by_window.items()}
    if not means:
        return {}
    low, high = min(means.values()), max(means.values())
    # 같은 값이 깔린 곡도 3마디·4마디 구간의 부동소수 평균은 미세하게 달라진다(0.1 →
    # 0.10000000000000002). 정확한 같음(==)으로는 평평함을 가를 수 없어 오차 범위 안이면 평평하다.
    if math.isclose(high, low):
        return {}
    return {window_id: (mean - low) / (high - low) for window_id, mean in means.items()}


def _section_kind(
    start: int,
    end: int,
    *,
    drop_ranges: Sequence[tuple[int, int]],
    break_ranges: Sequence[tuple[int, int]],
    last_drop_end: int | None,
    has_kick: bool,
    relative_energy: float | None,
    settings: ArrangementPolicy,
) -> str:
    """4마디 구간 하나의 종류를 돌려준다.

    위에서부터 먼저 맞는 것을 쓴다: 드롭과 겹침 → 브릿지(``break`` 와 겹침) → 마지막 드롭 뒤 →
    킥 진입이 있거나 곡 안 상대 에너지(``relative_energy``, 가장 조용한 구간 0 ~ 가장 큰 구간 1)가
    기준(``chorus_energy_cut``)보다 크면 후렴 → 나머지는 벌스. 마디 지도에는 구간 이름이 없어서
    이것은 어림이다. 상대 에너지가 None(에너지 없음·평평한 곡)이면 에너지로는 후렴이 되지 않는다.
    """
    if any(start <= drop_end and drop_start <= end for drop_start, drop_end in drop_ranges):
        return _SECTION_DROP
    if any(start <= break_end and break_start <= end for break_start, break_end in break_ranges):
        return _SECTION_BRIDGE
    if _after(start, last_drop_end):
        return _SECTION_LAST_CHORUS
    if has_kick or (relative_energy is not None and relative_energy > settings.chorus_energy_cut):
        return _SECTION_CHORUS
    return _SECTION_VERSE


def _after(start: int, last_drop_end: int | None) -> bool:
    """구간이 마지막 드롭이 끝난 뒤에서 시작하는가. 드롭이 없으면 거짓이다."""
    return last_drop_end is not None and start > last_drop_end


def _section_color(section: str, turn: int, settings: ArrangementPolicy) -> tuple[int, int, int]:
    """구간 종류의 색. 마지막 후렴은 목록을 돌며 쓴다(``turn`` 은 그 구간이 몇 번째인가)."""
    palette = settings.palette
    if section == _SECTION_DROP:
        return palette.drop
    if section == _SECTION_BRIDGE:
        return palette.bridge
    if section == _SECTION_LAST_CHORUS:
        return palette.last_chorus[turn % len(palette.last_chorus)]
    if section == _SECTION_CHORUS:
        return palette.chorus
    return palette.verse


def _draft_cue(
    bar: int,
    plan: _CellPlan,
    settings: ArrangementPolicy,
    *,
    role: object = None,
    words: Mapping[str, str] = BASIC_WORDS,
    color_names: Mapping[tuple[int, int, int], str] | None = None,
    axes: Sequence[str] = _MOTION_AXES,
) -> BeatGridCue:
    """규칙 결정 하나를 격자 칸으로 옮긴다. 값은 이 결정에서만 온다.

    결정에서 방향 값(``direction``)을 한 번 만들고, 라벨과 옛 필드(밝기·진입·움직임·계획 색·계획
    위치)는 전부 그 방향 값에서 파생한다 — 같은 자리에서 같은 결정으로 나오므로 서로 어긋날 수 없다.
    ``words`` 는 라벨 말 표(기존 생성기 말이 기본, 구간 단위 생성기는 구간 말을 넘긴다),
    ``color_names`` 는 초안 전체에서 정한 RGB → 이름이다(없으면 이 칸의 색만으로 정한다).
    """
    movement = (
        None
        if plan.movement_shape is None
        else {
            "shape": plan.movement_shape,
            "axes": list(axes),
            "period_unit": "bar",
            "period_value": settings.motion_period_bars,
            "phase_spread": None,
        }
    )
    rgb = plan.color_rgb
    names = color_names if color_names is not None else assign_color_names([rgb] if rgb else [])
    direction = build_direction(
        brightness_percent=plan.brightness_percent,
        kind=plan.kind,
        rgb=rgb,
        color_name=names.get(rgb) if rgb else None,
        position=plan.position,
        movement=movement,
        trigger_beat=settings.downbeat_trigger,
    )
    raw: dict[str, object] = {
        "bar": bar,
        "label": direction_label(direction, role, words=words) or plan.label,
        "brightness": {"mode": "value", "value_percent": direction["brightness_percent"]},
        "entry": {"trigger_beat": direction["entry"]["trigger_beat"]},
        "source_ref": f"{SOURCE}:{plan.kind}",
        "direction": direction,
    }
    if direction["movement"] is not None:
        raw["app_movement"] = dict(direction["movement"])
    if direction["color"] is not None:
        raw["planned_color"] = list(direction["color"]["rgb"] or ())
    if direction["position"] is not None:
        # 계획 위치는 콘솔 값이 아니라 계획 값이다 — 위치 번호는 승인 뒤 계획 경로가 붙인다.
        raw["planned_position"] = direction["position"]["name"]
    return normalize_beat_grid_cue(raw)
