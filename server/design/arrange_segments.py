"""구간 단위 배치 초안 생성기 — SPEC-LDRHYTHM-001(음악 분석 이벤트로 나눈 희소 칸, 순수 계산).

``generate_arrangement_draft`` 는 모든 줄의 모든 마디에 칸을 하나씩 내서 어느 줄이나 칸 길이가
한 마디로 똑같다. 이 생성기는 마디 지도의 이벤트(킥 진입·빌드업·브레이크·드롭)로 곡을 구간으로
나누고, 줄마다 계획이 바뀌는 마디에만 칸을 낸다. 칸 하나의 길이는 그 줄의 계획이 이어지는 마디
수다. 입력과 출력 모양은 기존 생성기와 같고(``ArrangementDraft``), 기존 생성기는 건드리지 않는다.
이 모듈은 파일을 쓰지 않고 콘솔에 닿지 않는다. 같은 입력이면 같은 결과다.

- 구간은 첫 마디, 모든 이벤트의 시작 마디, 드롭이 끝난 다음 마디에서 시작한다(마디 지도에 있는
  마디만). 구간은 시작 마디부터 다음 구간 시작의 앞 마디까지이고, 마지막 구간은 마지막 마디까지다.
- 구간 종류는 시작 마디에서 정한다. 위에서부터 먼저 맞는 것을 쓴다: 첫 마디에 이벤트가 없으면
  도입(intro), 드롭이 시작하면 드롭(drop), 드롭이 끝난 다음 마디면 마지막 후렴(last_chorus),
  킥 진입이면 후렴(chorus), 빌드업이면 빌드(build), 브레이크 끝 마디 뒤 2마디 안에 드롭이
  시작하면 브릿지(bridge), 그 밖은 벌스(verse)다. 마디 에너지로는 구간 종류를 정하지 않는다.
- 구간 색은 ``policy.palette`` 에서 온다. 드롭·후렴·브릿지는 각자의 색이고, 도입·벌스·빌드는
  벌스 색이다(빌드에는 팔레트 항목이 없어 벌스 색을 빌려 쓴다). 마지막 후렴은 앞선 마지막 후렴
  구간의 수만큼 색 목록을 돈다. 역광(BACK) 칸은 어느 구간에서나 역광 색이고, 곡별 주석 색
  (``planned_colors``)은 둘보다 앞선다.
- 칸 안의 규칙(라벨·밝기·움직임)은 기존 생성기의 ``_cell_plan`` 을 그대로 쓴다. 주인공 교대는
  구간 시작부터 세어 ``policy.window_bars`` 마디마다 다시 정하고, 차례는 곡 전체에서 이어진다.
- 강조는 임팩트 마디에만 둔다. 후렴·마지막 후렴 구간의 첫 마디에 BLIND, 드롭 구간의 첫 마디에
  STROBE(느린 곡이면 두지 않는다)다. 임팩트 직전에 비우는 예고는 아직 두지 않는다.
- 줄마다 마디별 계획을 보고, 계획이 같은 연속 마디를 한 칸으로 묶어 첫 마디에만 칸을 낸다. 쉬는
  구간(「—」)도 첫 마디에 칸이 있고, 모든 줄에 첫 마디 칸이 있다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from server.audio.bar_map_store import validate_bar_map
from server.design.arrange_generator import (
    _MOTION,
    _SECTION_BRIDGE,
    _SECTION_CHORUS,
    _SECTION_DROP,
    _SECTION_LAST_CHORUS,
    _SECTION_VERSE,
    UNCONFIRMED_NOTE,
    ArrangementDraft,
    ArrangementWindow,
    _cell_plan,
    _CellPlan,
    _check_layout,
    _draft_cue,
    _section_color,
    _voices,
)
from server.design.arrange_policy import ArrangementPolicy
from server.design.beat_grid import BeatGridCue, BeatGridTrack

__all__ = ["SegmentSection", "generate_segment_draft", "split_sections"]

#: 출처 표식. 모든 마디에 칸을 내는 ``arrangement_generator`` 와 구분한다.
SOURCE = "arrangement_segments"

#: 마디 지도 이벤트 종류(``bar_map_store`` 와 같은 어휘).
_KICK_ENTRY = "kick_entry"
_BUILD = "build"
_BREAK = "break"
_DROP = "drop"

#: 기존 생성기에 없는 구간 종류. 팔레트에 항목이 없어 둘 다 벌스 색을 쓴다.
_SECTION_INTRO = "intro"
_SECTION_BUILD = "build"

#: 구간의 첫 마디에 블라인드(BLIND)를 두는 구간 종류. 드롭은 스트로브(STROBE)가 맡는다.
_BLIND_SECTIONS = frozenset({_SECTION_CHORUS, _SECTION_LAST_CHORUS})

# @MX:DEBT: 브릿지 판정의 「브레이크 뒤 2마디 안」이 곡별 정책이 아니라 모듈 상수다
# @MX:CEILING: 이 값 하나. 곡마다 다르게 둘 수 없다(REQ-LDARRANGE-004 는 규칙 값을 곡별로 둔다)
# @MX:UPGRADE: 감독이 곡별로 고치려 하면 ``ArrangementPolicy`` 의 필드로 옮긴다
_BRIDGE_LOOKAHEAD_BARS = 2


class SegmentSection(NamedTuple):
    """구간 하나. 두 마디 번호는 양끝을 포함한다."""

    start_bar: int
    end_bar: int
    #: 도입·벌스·빌드·후렴·브릿지·드롭·마지막 후렴 중 하나.
    kind: str


class _Event(NamedTuple):
    kind: str
    start_bar: int
    end_bar: int


class _Window(NamedTuple):
    """구간 안의 창 하나의 결정. 창은 구간 시작부터 ``window_bars`` 마디씩이다."""

    section: SegmentSection
    color: tuple[int, int, int]
    start_bar: int
    end_bar: int
    lead: str | None
    active: list[str]
    moving: str | None


# @MX:NOTE: [AUTO] 마디 지도와 트랙 구성만 받는 순수 함수다. 파일이나 콘솔에 닿지 않는다.
def generate_segment_draft(
    bar_map: Mapping[str, Any] | None,
    layout: Sequence[Mapping[str, Any]],
    policy: ArrangementPolicy | None = None,
    *,
    planned_colors: Mapping[tuple[str, int], tuple[int, int, int]] | None = None,
) -> ArrangementDraft:
    """마디 지도의 이벤트로 곡을 구간으로 나눠 「트랙 × 칸」 희소 초안을 만든다.

    - 마디 지도가 없거나 저장 모양 검증을 통과하지 못하면 빈 초안과 안내 문장을 돌려준다.
      예외를 던지지 않는다. 트랙 구성의 겹침이나 모르는 층 역할은 기존 생성기처럼
      ``ValueError`` 다.
    - 돌려주는 모양은 ``generate_arrangement_draft`` 와 같다. ``windows`` 는 구간 안의 창별
      결정이고, ``tracks`` 의 칸은 줄마다 계획이 바뀌는 마디에만 있다. 칸이 없는 마디는 앞
      칸의 상태가 이어진다.
    - ``planned_colors`` 는 기존 생성기와 같다. 켜는 칸에서는 구간 색·역광 색보다 우선하고,
      쉬는 칸에는 닿지 않는다. 이 함수는 파일을 읽지 않는다.
    """
    settings = ArrangementPolicy() if policy is None else policy
    if bar_map is None:
        return _unconfirmed(UNCONFIRMED_NOTE)
    problem = validate_bar_map(bar_map)
    if problem is not None:
        return _unconfirmed(f"{UNCONFIRMED_NOTE}: {problem}")
    _check_layout(layout)

    bar_numbers = sorted(int(entry["bar"]) for entry in bar_map["bars"])
    overrides = planned_colors or {}
    windows = _plan_windows(split_sections(bar_map), layout, settings)

    plans: dict[str, dict[int, _CellPlan]] = {str(track["group_name"]): {} for track in layout}
    for window in windows:
        section = window.section
        for track in layout:
            name = str(track["group_name"])
            for bar in range(window.start_bar, window.end_bar + 1):
                at_start = bar == section.start_bar
                plans[name][bar] = _cell_plan(
                    track,
                    active=window.active,
                    moving=window.moving,
                    is_kick=at_start and section.kind in _BLIND_SECTIONS,
                    is_drop_start=at_start and section.kind == _SECTION_DROP,
                    settings=settings,
                    section_color=window.color,
                    override=overrides.get((name, bar)),
                )

    tracks = [
        BeatGridTrack(
            group_no=track.get("group_no"),
            group_no_confirmed=bool(track.get("group_no_confirmed", False)),
            group_name=str(track["group_name"]),
            layer_role=track.get("layer_role"),
            cues=[
                _segment_cue(bar, plan, settings)
                for bar, plan in _runs(plans[str(track["group_name"])], bar_numbers)
            ],
        )
        for track in layout
    ]
    return ArrangementDraft(
        tracks=tracks,
        windows=[
            ArrangementWindow(
                start_bar=window.start_bar,
                end_bar=window.end_bar,
                lead=window.lead,
                active=window.active,
                drop=window.section.kind == _SECTION_DROP,
            )
            for window in windows
        ],
        bar_range={"start": bar_numbers[0], "end": bar_numbers[-1]},
        source=SOURCE,
        note=None,
    )


def split_sections(bar_map: Mapping[str, Any]) -> list[SegmentSection]:
    """저장 모양 검증을 통과한 마디 지도를 구간 목록으로 나눈다(시작 마디 순서).

    구간은 첫 마디, 모든 이벤트의 시작 마디, 드롭 끝 마디의 다음 마디에서 시작한다. 마디 지도에 없는
    마디(마지막 마디에서 끝나는 드롭의 다음 마디)는 시작이 아니다.
    """
    bar_numbers = sorted(int(entry["bar"]) for entry in bar_map["bars"])
    events = [
        _Event(str(event["kind"]), int(event["start_bar"]), int(event["end_bar"]))
        for event in bar_map["events"]
    ]
    starts = {bar_numbers[0]}
    starts.update(event.start_bar for event in events)
    starts.update(event.end_bar + 1 for event in events if event.kind == _DROP)
    ordered = sorted(starts & set(bar_numbers))
    ends = [start - 1 for start in ordered[1:]] + [bar_numbers[-1]]
    return [
        SegmentSection(start, end, _section_kind(start, bar_numbers[0], events))
        for start, end in zip(ordered, ends, strict=True)
    ]


def _section_kind(start: int, first_bar: int, events: Sequence[_Event]) -> str:
    """구간 하나의 종류를 시작 마디로 정한다. 위에서부터 먼저 맞는 것을 쓴다."""
    here = [event for event in events if event.start_bar == start]
    kinds = {event.kind for event in here}
    if start == first_bar and not here:
        return _SECTION_INTRO
    if _DROP in kinds:
        return _SECTION_DROP
    if any(event.kind == _DROP and event.end_bar + 1 == start for event in events):
        return _SECTION_LAST_CHORUS
    if _KICK_ENTRY in kinds:
        return _SECTION_CHORUS
    if _BUILD in kinds:
        return _SECTION_BUILD
    if any(_drop_follows(event, events) for event in here if event.kind == _BREAK):
        return _SECTION_BRIDGE
    return _SECTION_VERSE


def _drop_follows(break_event: _Event, events: Sequence[_Event]) -> bool:
    """브레이크 끝 마디 뒤 ``_BRIDGE_LOOKAHEAD_BARS`` 마디 안에서 드롭이 시작하는가."""
    return any(
        event.kind == _DROP and 0 < event.start_bar - break_event.end_bar <= _BRIDGE_LOOKAHEAD_BARS
        for event in events
    )


def _plan_windows(
    sections: Sequence[SegmentSection],
    layout: Sequence[Mapping[str, Any]],
    settings: ArrangementPolicy,
) -> list[_Window]:
    """구간을 구간 시작부터 ``window_bars`` 마디씩 창으로 쪼개 창마다 주인공·움직이는 층을 정한다.

    주인공 차례(``window_turn``)와 움직이는 무빙의 차례(``motion_turn``)는 구간이 바뀌어도
    처음으로 돌아가지 않고 곡 전체에서 이어진다. 움직이는 층의 수는 드롭 구간이면 드롭 상한,
    아니면 보통 상한이다.
    """
    voices = _voices(layout)
    movers = [str(track["group_name"]) for track in layout if track.get("layer_role") == "mover"]
    windows: list[_Window] = []
    window_turn = motion_turn = last_chorus_turn = 0
    for section in sections:
        # 마지막 후렴 돌림의 차례 = 이 구간보다 앞선 마지막 후렴 구간의 수.
        color = _section_color(section.kind, last_chorus_turn, settings)
        if section.kind == _SECTION_LAST_CHORUS:
            last_chorus_turn += 1
        cap = settings.drop_layer_cap if section.kind == _SECTION_DROP else settings.base_layer_cap
        for start in range(section.start_bar, section.end_bar + 1, settings.window_bars):
            lead_index = window_turn % len(voices) if voices else 0
            active = [
                voices[(lead_index + offset) % len(voices)]
                for offset in range(min(cap, len(voices)))
            ]
            moving: str | None = None
            if _MOTION in active:
                moving = movers[motion_turn % len(movers)]
                motion_turn += 1
            windows.append(
                _Window(
                    section=section,
                    color=color,
                    start_bar=start,
                    end_bar=min(start + settings.window_bars - 1, section.end_bar),
                    lead=voices[lead_index] if voices else None,
                    active=active,
                    moving=moving,
                )
            )
            window_turn += 1
    return windows


def _runs(
    plans: Mapping[int, _CellPlan], bar_numbers: Sequence[int]
) -> list[tuple[int, _CellPlan]]:
    """마디별 계획에서 앞 마디와 달라지는 마디만 골라 (첫 마디, 계획) 목록으로 돌려준다.

    계획이 같은 연속 마디는 한 칸이다. 쉬는 계획도 다른 계획과 똑같이 센다.
    """
    rows: list[tuple[int, _CellPlan]] = []
    for bar in bar_numbers:
        if not rows or rows[-1][1] != plans[bar]:
            rows.append((bar, plans[bar]))
    return rows


def _segment_cue(bar: int, plan: _CellPlan, settings: ArrangementPolicy) -> BeatGridCue:
    """칸 하나를 기존 생성기의 ``_draft_cue`` 로 만들고, 출처 표식만 이 생성기의 것으로 바꾼다."""
    cue = _draft_cue(bar, plan, settings)
    cue["source_ref"] = f"{SOURCE}:{plan.kind}"
    return cue


def _unconfirmed(note: str) -> ArrangementDraft:
    return ArrangementDraft(tracks=[], windows=[], bar_range={}, source=SOURCE, note=note)
