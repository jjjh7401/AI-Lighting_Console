"""구간 단위 배치 초안 생성기 — SPEC-LDRHYTHM-001(음악 분석 이벤트로 나눈 희소 칸, 순수 계산).

``generate_arrangement_draft`` 는 모든 줄의 모든 마디에 칸을 하나씩 내서 어느 줄이나 칸 길이가
한 마디로 똑같다. 이 생성기는 마디 지도의 이벤트(킥 진입·빌드업·브레이크·드롭)로 곡을 구간으로
나누고, 줄마다 값이 바뀌는 마디에만 칸을 낸다. 칸 하나의 길이는 그 줄의 값이 이어지는 마디
수다. 입력과 출력 모양은 기존 생성기와 같고(``ArrangementDraft``), 기존 생성기는 건드리지 않는다.
이 모듈은 파일을 쓰지 않고 콘솔에 닿지 않는다. 같은 입력이면 같은 결과다.

- 구간은 첫 마디, 모든 이벤트의 시작 마디, 드롭이 끝난 다음 마디에서 시작한다(마디 지도에 있는
  마디만). 구간은 시작 마디부터 다음 구간 시작의 앞 마디까지이고, 마지막 구간은 마지막 마디까지다.
  리듬 블록(``rhythm``)은 구간 경계를 바꾸지 않는다. 구간마다 시작 마디를 품은 리듬 구간의
  등급(``d_level``)을 메타데이터로만 달고, 초안에는 싣지 않는다.
- 구간 종류는 시작 마디에서 정한다. 위에서부터 먼저 맞는 것을 쓴다: 첫 마디에 이벤트가 없으면
  도입(intro), 드롭이 시작하면 드롭(drop), 드롭이 끝난 다음 마디면 마지막 후렴(last_chorus),
  킥 진입이면 후렴(chorus) — 단 도입 뒤 곧바로 오는 곡의 첫 사건인 킥(같은 마디에 빌드 없음)은
  비트가 들어오는 벌스(verse)다 —, 빌드업이면 빌드(build), 브레이크 끝 마디 뒤 2마디 안에 드롭이
  시작하면 브릿지(bridge), 그 밖은 벌스(verse)다. 마디 에너지로는 구간 종류를 정하지 않는다.
- 구간 색은 ``policy.palette`` 에서 온다. 드롭·후렴·브릿지는 각자의 색이고, 도입·벌스·빌드는
  벌스 색이다(빌드에는 팔레트 항목이 없어 벌스 색을 빌려 쓴다). 마지막 후렴은 앞선 마지막 후렴
  구간의 수만큼 색 목록을 돈다. 역광(BACK) 칸은 어느 구간에서나 역광 색이고, 곡별 주석 색
  (``planned_colors``)은 둘보다 앞선다.
- 칸 안의 규칙(밝기·움직임)은 기존 생성기의 ``_cell_plan`` 을 그대로 쓴다. 라벨만 기본 격자
  (``love_attack.yaml``)와 배치 규칙서의 말로 바꾼다(BACK 펄스는 「킥 1·2·4박」이다). 같은 종류
  구간은 같은 처리다: 켜는 리듬 층은 구간 종류가 정하고(``_LEAD_OF_KIND``) 구간 안에서 돌리지
  않는다. 창(``policy.window_bars`` 마디, 구간 시작부터 세고 짧은 끝 창은 앞 창에 붙임)마다
  바뀌는 것은 움직이는 무빙뿐이고 그 차례는 구간마다 처음부터 센다. BACK·SIDE·무빙의 켜는 칸은
  값이 같아도 창 시작마다 새 칸이다.
- 무빙이 위치를 바꾸기 전에는 어둠 속 사전이동(MIB)이 가능한 길이만큼 쉼 칸을 둔다(마디 시각으로
  잼). 후렴·드롭 안이나 앞 위치가 남지 않아 쉼을 둘 수 없으면 그 구간에서는 위치를 바꾸지 않는다.
- 강조는 임팩트 마디에만 둔다. 후렴·마지막 후렴 구간의 첫 마디에 BLIND, 드롭 구간의 첫 마디에
  STROBE(느린 곡이면 두지 않는다)다. 마디 지도에 리듬 블록이 있으면 BLIND 마디는 그 구간 안 첫 큰
  히트(``kind == "big"``)의 마디이고, 구간 안에 큰 히트가 없으면 구간의 첫 마디 그대로다.
- 예고는 강조가 아니다. 강조 구간(후렴·마지막 후렴·드롭)이 시작하기 바로 앞 마디, 곧 큰 히트
  직전 마디에 블라인드 줄이 한 마디를 비운다(「3·4박 전부 비움(예고)」, 밝기는 쉼과 같다).
- 칸은 값이 같은 연속 마디의 묶음이고 첫 마디에만 낸다. 값은 라벨·밝기·움직임이고 구간 종류와
  구간 경계는 값이 아니다. 쉬는 연속 마디(「—」)도 구간을 몇 번 넘든 한 칸이다. 모든 줄에 첫
  마디 칸이 있다.
- 색은 칸의 속성이라 칸 첫 마디의 색을 쓴다. 색이 바뀐다고 칸을 나누는 줄은 워시 줄(역할 wash)
  뿐이다. 다른 줄의 칸은 구간 색이 바뀌는 마디를 넘어 이어진다. 곡별 주석 색이 놓인 마디는 칸을
  나눈다. 그 마디의 칸이 그 색을 보여야 해서다(앞뒤 마디의 색과 다를 때만).
- 줄마다 트래킹을 싣는다: 첫 칸 Block, 끝 칸 Release, 구간 첫 칸 Track(콘솔 기본값), 그 밖의 칸
  Cue Only(``_with_tracking``).
- 워시 줄은 구간마다 한 칸이다. 구간 첫 마디의 값이 구간 끝까지 가고, 색이 바뀌는 구간 경계에서만
  나뉜다. 구간 중간 마디의 주석 색은 워시 칸을 쪼개지 않는다(리드 결정 2026-10-16).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from server.audio.bar_map_store import validate_bar_map
from server.design.arrange_generator import (
    _CHASE,
    _MOTION,
    _MOTION_AXES,
    _PULSE,
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
    _rest_plan,
    _section_color,
    _voices,
)
from server.design.arrange_policy import MOVER_POSITION_LADDER, ArrangementPolicy
from server.design.beat_grid import BeatGridCue, BeatGridTrack
from server.design.beat_grid_measured import visible_axes
from server.design.beat_grid_mib import MIB_MIN_DARK_SECONDS
from server.design.cell_direction import SEGMENT_WORDS, assign_color_names

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
#: 곡 끝 브레이크 구간. 도입처럼 다룬다(움직임이 주인공, 두 무빙 바닥 쪽, 벌스 색).
_SECTION_OUTRO = "outro"

#: 구간의 첫 마디에 블라인드(BLIND)를 두는 구간 종류. 드롭은 스트로브(STROBE)가 맡는다.
_BLIND_SECTIONS = frozenset({_SECTION_CHORUS, _SECTION_LAST_CHORUS})
#: 무빙을 사전이동 쉼으로 비우지 않는 구간 종류 — 곡의 큰 순간이라 빛이 가장 꽉 차야 한다.
_HIT_KINDS = frozenset({_SECTION_CHORUS, _SECTION_LAST_CHORUS, _SECTION_DROP})

#: 구간 종류 → (위 무빙 U, 아래 무빙 D) 목표 위치(사다리 이름). 배치 규칙서 무빙 위치 행: 인트로는
#: 둘 다 바닥 쪽에 정지, 벌스는 위 무빙을 세우고 아래 무빙은 바닥 쪽에 정지(규칙 6), 빌드·브릿지는
#: 무대 중앙, 코러스·마지막 코러스·드롭은 두 무빙이 다른 자리에서 함께 연다(규칙 5).
_MOVER_TARGET_OF_KIND: dict[str, tuple[str, str]] = {
    _SECTION_INTRO: ("Home", "Home"),
    _SECTION_OUTRO: ("Home", "Home"),
    _SECTION_VERSE: ("Center", "Home"),
    _SECTION_BUILD: ("Center", "Center"),
    _SECTION_BRIDGE: ("Center", "Center"),
    _SECTION_CHORUS: ("Audience", "Ring In"),
    _SECTION_LAST_CHORUS: ("Audience", "Ring In"),
    _SECTION_DROP: ("Audience", "Ring In"),
}
#: 구간 종류 → 주인공 리듬 층(``_voices`` 순서: 펄스 → 체이스 → 움직임). 켜는 층은 주인공부터
#: 상한 수만큼이고 구간 안에서 창마다 돌리지 않는다 — 기본 격자도 구간 종류마다 켜는 층 조합이
#: 고정이다(후렴·벌스·도입은 움직임+펄스, 빌드·브릿지는 체이스+움직임). 마지막 후렴은 후렴과 같다.
_LEAD_OF_KIND: dict[str, str] = {
    _SECTION_INTRO: _MOTION,
    _SECTION_OUTRO: _MOTION,
    _SECTION_VERSE: _MOTION,
    _SECTION_BUILD: _CHASE,
    _SECTION_CHORUS: _MOTION,
    _SECTION_LAST_CHORUS: _MOTION,
    _SECTION_BRIDGE: _CHASE,
    _SECTION_DROP: _PULSE,
}
#: 무빙 켜는 칸의 규칙 종류 — 이 칸에만 계획 위치를 싣는다.
_MOVER_LIT_KINDS = frozenset({"motion", "hold"})


def _mover_positions(
    sections: Sequence[SegmentSection], layout: Sequence[Mapping[str, Any]]
) -> dict[tuple[str, int], str]:
    """무빙 줄마다 구간(시작 마디)의 계획 위치 이름을 돌려준다. 키는 (줄 이름, 구간 시작 마디).

    구간의 목표를 따르되, 구간이 바뀔 때마다 사다리에서 한 칸씩만 옮긴다 — 상대 이동(「한 칸 올림」
    「새 자리」)을 앞 칸 위치에서 한 단계 옮긴 절대 위치로 바꾼 것이다. 위치는 구간 경계에서만
    바뀐다(규칙 2). 위 무빙은 이름이 ``-U`` 로 끝나는 줄, 나머지 무빙은 아래 무빙(D) 목표를 받는다.
    """
    found: dict[tuple[str, int], str] = {}
    for track in layout:
        if track.get("layer_role") != "mover":
            continue
        name = str(track["group_name"])
        upper = name.upper().endswith("-U")
        current: int | None = None
        for section in sections:
            target = _MOVER_TARGET_OF_KIND.get(section.kind)
            if target is None:
                continue
            goal = MOVER_POSITION_LADDER.index(target[0] if upper else target[1])
            current = goal if current is None else current + max(-1, min(1, goal - current))
            found[(name, section.start_bar)] = MOVER_POSITION_LADDER[current]
    return found


# 칸 라벨은 방향 값에서 만든다(``cell_direction.direction_label``, 말 표는 ``SEGMENT_WORDS``).
# 기존 생성기의 이름(「펄스」「체이스」「스트로브」「블라인드」「유지」)이 아니라 기본 격자
# (``beat_grid_data/love_attack.yaml``)와 배치 규칙서
# (``reports/effect-arrangement-rules-20261007.md``)에 적힌 말이다. 아래 상수는 그 표의 이름표다.
PULSE_LABEL = SEGMENT_WORDS["pulse"]
CHASE_LABEL = SEGMENT_WORDS["chase"]
MOTION_LABEL = SEGMENT_WORDS["motion"]
FOH_LABEL = SEGMENT_WORDS["static:key"]
WASH_LABEL = SEGMENT_WORDS["static:wash"]
BLIND_LABEL = SEGMENT_WORDS["blind"]
STROBE_LABEL = SEGMENT_WORDS["strobe"]
PRE_HIT_LABEL = SEGMENT_WORDS["pre_hit"]

#: 큰 히트 직전에 블라인드 줄을 비우는 예고 칸의 규칙 종류.
_KIND_PRE_HIT = "pre_hit"
#: 색이 바뀌는 마디에서 칸을 나누는 줄의 역할. 워시는 색이 곧 그 줄의 내용이다. 다른 줄의 칸은
#: 색이 바뀌어도 이어진다(기본 격자도 색 주석이 워시 줄과 BACK 0마디뿐이다).
_COLOR_LINE_ROLES = frozenset({"wash"})
#: 켜는 칸을 창(프레이즈) 시작마다 새로 세우는 리듬 층의 역할. 기본 격자도 같은 「킥 1·2·4박」을
#: 4마디마다 다시 찍는다. 쉬는 칸은 나누지 않는다.
_PHRASE_ROLES = frozenset({"back", "side", "mover"})

# @MX:DEBT: 브릿지 판정의 「브레이크 뒤 2마디 안」이 곡별 정책이 아니라 모듈 상수다
# @MX:CEILING: 이 값 하나. 곡마다 다르게 둘 수 없다(REQ-LDARRANGE-004 는 규칙 값을 곡별로 둔다)
# @MX:UPGRADE: 감독이 곡별로 고치려 하면 ``ArrangementPolicy`` 의 필드로 옮긴다
_BRIDGE_LOOKAHEAD_BARS = 2


class SegmentSection(NamedTuple):
    """구간 하나. 두 마디 번호는 양끝을 포함한다."""

    start_bar: int
    end_bar: int
    #: 도입·벌스·빌드·후렴·브릿지·드롭·마지막 후렴·아웃트로 중 하나.
    kind: str
    #: 이 구간 시작 마디를 품은 리듬 구간(``bar_map["rhythm"]["sections"]``)의 등급(1~5).
    #: 리듬 블록이 없거나 품은 리듬 구간이 없으면 ``None``. 메타데이터라 초안에는 실리지 않는다.
    d_level: int | None = None


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
      결정이고, ``tracks`` 의 칸은 줄마다 값이 바뀌는 마디에만 있다. 칸이 없는 마디는 앞
      칸의 상태가 이어진다. 쉬는 연속 마디는 쉼(「—」) 한 칸이다.
    - ``planned_colors`` 는 기존 생성기와 같다. 켜는 칸에서는 구간 색·역광 색보다 우선하고,
      쉬는 칸에는 닿지 않는다. 이 함수는 파일을 읽지 않는다.
    - 블라인드 줄에는 강조 구간 바로 앞 마디에 예고 칸(밝기는 쉼과 같고 색은 없다)이 선다.
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
    sections = split_sections(bar_map)
    windows = _plan_windows(sections, layout, settings)
    big_hit_bars = _big_hit_bars(bar_map)
    mover_at = _mover_positions(sections, layout)

    plans: dict[str, dict[int, _CellPlan]] = {str(track["group_name"]): {} for track in layout}
    for window in windows:
        section = window.section
        for track in layout:
            name = str(track["group_name"])
            for bar in range(window.start_bar, window.end_bar + 1):
                at_start = bar == section.start_bar
                plan = _cell_plan(
                    track,
                    active=window.active,
                    moving=window.moving,
                    is_kick=section.kind in _BLIND_SECTIONS
                    and bar == _emphasis_bar(section, big_hit_bars),
                    is_drop_start=at_start and section.kind == _SECTION_DROP,
                    settings=settings,
                    section_color=window.color,
                    override=overrides.get((name, bar)),
                )
                if track.get("layer_role") == "mover" and plan.kind in _MOVER_LIT_KINDS:
                    plan = plan._replace(position=mover_at.get((name, section.start_bar)))
                plans[name][bar] = plan

    bar_ms = {int(entry["bar"]): int(entry["start_ms"]) for entry in bar_map["bars"]}
    hit_bars = frozenset(
        bar
        for section in sections
        if section.kind in _HIT_KINDS
        for bar in range(section.start_bar, section.end_bar + 1)
    )
    for track in layout:
        if track.get("layer_role") == "mover":
            _darken_before_moves(
                plans[str(track["group_name"])],
                bar_numbers,
                bar_ms,
                settings,
                keep_lit=hit_bars,
                section_starts=frozenset(section.start_bar for section in sections),
                phrase_starts=frozenset(window.start_bar for window in windows),
            )

    # 예고 칸은 강조가 아니라서 강조 규칙(``_cell_plan`` 의 ``is_kick``)을 거치지 않고 따로 놓는다.
    notice = _CellPlan(PRE_HIT_LABEL, settings.rest_percent, None, _KIND_PRE_HIT)
    pre_hit_bars = _pre_hit_bars(sections)
    for track in layout:
        if _is_blind_line(track):
            for bar in pre_hit_bars:
                plans[str(track["group_name"])][bar] = notice

    # 워시 줄은 구간마다 한 칸이다(리드 결정 2026-10-16). 구간 첫 마디의 값(색 포함)이 구간 끝까지
    # 가고, 칸은 색이 바뀌는 구간 경계에서만 나뉜다. 구간 중간의 주석 색은 워시 칸을 쪼개지 않는다.
    section_starts = frozenset(section.start_bar for section in sections)
    phrase_starts = frozenset(window.start_bar for window in windows)
    for track in layout:
        if track.get("layer_role") not in _COLOR_LINE_ROLES:
            continue
        name = str(track["group_name"])
        for section in sections:
            head = plans[name].get(section.start_bar)
            if head is None:
                continue
            for bar in range(section.start_bar, section.end_bar + 1):
                if bar in plans[name]:
                    plans[name][bar] = head

    # 색 이름은 이 초안 전체의 색으로 한 번에 정한다 — 같은 색은 어느 칸에서나 같은 이름이다.
    color_names = assign_color_names(
        plan.color_rgb for by_bar in plans.values() for plan in by_bar.values() if plan.color_rgb
    )
    tail_bar = _tail_bar(bar_map)
    tracks = []
    for track in layout:
        name = str(track["group_name"])
        annotated = frozenset(bar for track_name, bar in overrides if track_name == name)
        if track.get("layer_role") in _COLOR_LINE_ROLES:
            annotated = annotated & section_starts
        runs = _runs(
            plans[name],
            bar_numbers,
            splits_on_color=track.get("layer_role") in _COLOR_LINE_ROLES,
            annotated=annotated,
            phrase_starts=phrase_starts
            if track.get("layer_role") in _PHRASE_ROLES
            else frozenset(),
        )
        # 칸이 하나뿐인 줄(곡 내내 켜는 FOH 등)은 마지막 구간 첫 마디에 같은 값의 끝 칸을 하나 더
        # 둔다 — 그 칸이 다른 줄처럼 Release 를 받는다(인수 D-11, full3: FOH 만 Release 없음).
        # 하나뿐인 첫 칸에 Release 를 얹으면 곡 시작에서 값을 놓게 되므로 그렇게 하지 않는다.
        runs = list(runs)
        if (
            len(runs) == 1
            and (runs[0][1].brightness_percent or 0) > 0
            and sections
            and sections[-1].start_bar > runs[0][0]
        ):
            runs.append((sections[-1].start_bar, runs[0][1]))
        if tail_bar is not None:
            runs = _ending_dark(runs, tail_bar, _rest_plan(settings))
        tracks.append(
            BeatGridTrack(
                group_no=track.get("group_no"),
                group_no_confirmed=bool(track.get("group_no_confirmed", False)),
                group_name=name,
                layer_role=track.get("layer_role"),
                cues=_with_tracking(
                    [
                        _segment_cue(
                            bar,
                            plan,
                            settings,
                            role=track.get("layer_role"),
                            color_names=color_names,
                            axes=_motion_axes(track),
                        )
                        for bar, plan in runs
                    ],
                    section_starts,
                ),
            )
        )
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

    마디 지도에 ``rhythm`` 블록이 있어도 구간 경계는 바뀌지 않는다(사건 경계만 쓴다). 블록이 있든
    없든 경계 집합이 같다. 구간의 ``d_level`` 은 그 시작 마디를 품은 리듬 구간의 등급이며
    메타데이터일 뿐이다. 블록이 없으면 ``d_level`` 은 ``None`` 이다.
    """
    bar_numbers = sorted(int(entry["bar"]) for entry in bar_map["bars"])
    events = [
        _Event(str(event["kind"]), int(event["start_bar"]), int(event["end_bar"]))
        for event in bar_map["events"]
    ]
    rhythm_sections = _rhythm_sections(bar_map)
    starts = {bar_numbers[0]}
    starts.update(event.start_bar for event in events)
    starts.update(event.end_bar + 1 for event in events if event.kind == _DROP)
    ordered = sorted(starts & set(bar_numbers))
    ends = [start - 1 for start in ordered[1:]] + [bar_numbers[-1]]
    sections = [
        SegmentSection(
            start,
            end,
            _section_kind(start, bar_numbers[0], events),
            _d_level_at(start, rhythm_sections),
        )
        for start, end in zip(ordered, ends, strict=True)
    ]
    # 곡 끝까지 가는 마지막 구간이 브레이크로 시작하고 뒤에 사건이 없으면 아웃트로다(벌스가 아니다).
    last = sections[-1]
    if (
        len(sections) > 1
        and last.kind == _SECTION_VERSE
        and any(event.kind == _BREAK and event.start_bar == last.start_bar for event in events)
        and all(event.start_bar <= last.start_bar for event in events)
    ):
        sections[-1] = last._replace(kind=_SECTION_OUTRO)
    return sections


def _rhythm_sections(bar_map: Mapping[str, Any]) -> list[tuple[int, int, int]]:
    """리듬 구간의 (시작 마디, 끝 마디, 등급) 목록. 리듬 블록이 없으면 빈 목록."""
    rhythm = bar_map.get("rhythm")
    if not rhythm:
        return []
    return [
        (int(item["start_bar"]), int(item["end_bar"]), int(item["d_level"]))
        for item in rhythm["sections"]
    ]


def _d_level_at(bar: int, rhythm_sections: Sequence[tuple[int, int, int]]) -> int | None:
    """그 마디를 품은 리듬 구간의 등급. 품은 구간이 없으면 ``None``."""
    for start, end, level in rhythm_sections:
        if start <= bar <= end:
            return level
    return None


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
        # 도입 뒤 곧바로 들어오는 킥(곡의 첫 사건, 같은 마디에 빌드 없음)은 비트가 들어오는
        # 벌스다. 후렴은 빌드·브레이크 같은 앞 사건을 거친 뒤 들어오는 킥이다.
        if (
            start > first_bar
            and _BUILD not in kinds
            and start == min(event.start_bar for event in events)
        ):
            return _SECTION_VERSE
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

    같은 종류 구간은 같은 처리를 받는다. 주인공은 구간 종류가 정하고(``_LEAD_OF_KIND``) 구간 안
    에서 돌리지 않는다. 창마다 바뀌는 것은 움직이는 무빙뿐이고, 그 차례는 구간마다 처음부터 센다.
    그래서 후렴 1·2·3 은 같은 창 순서에서 같은 층이 켜지고 같은 무빙이 움직인다. 켜는 층의 수는
    드롭 구간이면 드롭 상한, 아니면 보통 상한이다. 창 길이에 못 미치는 끝 창은 앞 창에 붙인다.
    """
    voices = _voices(layout)
    movers = [str(track["group_name"]) for track in layout if track.get("layer_role") == "mover"]
    windows: list[_Window] = []
    last_chorus_turn = 0
    for section in sections:
        # 마지막 후렴 돌림의 차례 = 이 구간보다 앞선 마지막 후렴 구간의 수.
        color = _section_color(section.kind, last_chorus_turn, settings)
        if section.kind == _SECTION_LAST_CHORUS:
            last_chorus_turn += 1
        cap = settings.drop_layer_cap if section.kind == _SECTION_DROP else settings.base_layer_cap
        lead = _LEAD_OF_KIND.get(section.kind)
        lead_index = voices.index(lead) if lead in voices else 0
        active = [
            voices[(lead_index + offset) % len(voices)] for offset in range(min(cap, len(voices)))
        ]
        motion_turn = 0
        # 창 길이에 못 미치는 끝 창은 따로 세우지 않고 앞 창에 붙인다
        # (구간 끝 2마디짜리 칸을 막는다).
        starts = list(range(section.start_bar, section.end_bar + 1, settings.window_bars))
        if len(starts) > 1 and section.end_bar - starts[-1] + 1 < settings.window_bars:
            starts.pop()
        for start, after in zip(starts, [*starts[1:], section.end_bar + 1], strict=True):
            moving: str | None = None
            if _MOTION in active:
                moving = movers[motion_turn % len(movers)]
                motion_turn += 1
            windows.append(
                _Window(
                    section=section,
                    color=color,
                    start_bar=start,
                    end_bar=after - 1,
                    lead=voices[lead_index] if voices else None,
                    active=list(active),
                    moving=moving,
                )
            )
    return windows


def _big_hit_bars(bar_map: Mapping[str, Any]) -> list[int]:
    """리듬 블록의 큰 히트(``kind == "big"``)가 있는 마디, 작은 마디 순. 블록이 없으면 빈 목록."""
    rhythm = bar_map.get("rhythm")
    if not rhythm:
        return []
    return sorted(int(hit["bar"]) for hit in rhythm["hits"] if hit["kind"] == "big")


def _emphasis_bar(section: SegmentSection, big_hit_bars: Sequence[int]) -> int:
    """블라인드 강조 마디. 구간 안 첫 큰 히트의 마디, 구간 안에 큰 히트가 없으면 구간 시작이다."""
    return next(
        (bar for bar in big_hit_bars if section.start_bar <= bar <= section.end_bar),
        section.start_bar,
    )


# @MX:NOTE: [AUTO] 반영 단계 MIB(``beat_grid_mib.plan_mib_premoves``)와 같은 기준이다 — 사전이동은
# 쉼 칸 다음 마디에 서고, 그때부터 위치가 바뀌는 칸까지 ``MIB_MIN_DARK_SECONDS`` 이상 어두워야 한다.
def _darken_before_moves(
    by_bar: dict[int, _CellPlan],
    bar_numbers: Sequence[int],
    bar_ms: Mapping[int, int],
    settings: ArrangementPolicy,
    *,
    keep_lit: frozenset[int],
    section_starts: frozenset[int],
    phrase_starts: frozenset[int],
) -> None:
    """무빙 줄에서 위치가 바뀌는 칸 앞을 쉼으로 비워 어둠 속 사전이동(MIB)이 가능하게 한다.

    쉼은 사전이동 뒤 어두운 시간이 이동+정착 시간 이상이 되는 가장 짧은 길이다(마디 길이는 곡의
    마디 시각에서 잰다). 앞 위치의 켜는 칸이 한 마디도 남지 않거나 쉼이 ``keep_lit`` 마디(후렴·
    드롭)에 걸리면 비우지 않고, 위치도 바꾸지 않는다 — 다음 위치가 나올 때까지 앞 위치에 머문다.
    그래서 무빙이 켜진 채 위치를 옮기는 칸이 없다.
    """
    # 사전이동 쉼은 보통 쉼과 같은 칸이다(칸 값 모양은 그대로).
    # 반영 단계가 쉼 뒤 위치 변화로 알아본다.
    dark = _rest_plan(settings)
    need_ms = MIB_MIN_DARK_SECONDS * 1000
    index_of = {bar: index for index, bar in enumerate(bar_numbers)}
    position: str | None = None
    position_start = bar_numbers[0]
    for bar in bar_numbers:
        here = by_bar[bar].position
        if here is None:
            continue
        if position is not None and here != position:
            # 쉼 첫 마디 s: 사전이동 마디(s 다음 마디)부터 이 마디까지가
            # need_ms 이상인 가장 뒤 마디.
            start = next(
                (
                    candidate
                    for candidate in reversed(bar_numbers[: index_of[bar] - 1])
                    if bar_ms[bar] - bar_ms[bar_numbers[index_of[candidate] + 1]] >= need_ms
                ),
                None,
            )
            # 쉼 앞에 창 길이보다 짧은 켜는 자투리가 남으면 쉼을 그 창 시작으로 당긴다.
            snap = max(
                (p for p in phrase_starts if start is not None and position_start < p <= start),
                default=None,
            )
            if snap is not None and start is not None and start - snap < settings.window_bars:
                start = snap
            span = [] if start is None else bar_numbers[index_of[start] : index_of[bar]]
            head = _dark_head(bar, bar_numbers, bar_ms, need_ms, section_starts)
            if span and span[0] > position_start and keep_lit.isdisjoint(span):
                for dark_bar in span:
                    by_bar[dark_bar] = dark
            elif head and keep_lit.isdisjoint(head) and _before(bar, bar_numbers) in keep_lit:
                # 후렴·드롭이 꽉 찬 채 끝나서 앞에 쉼을 둘 수 없으면, 새 구간 첫머리를 어둡게 해
                # 그 안에서 옮긴다.
                for dark_bar in head:
                    by_bar[dark_bar] = dark
            else:
                # 어둠을 만들 수 없으면 이 구간에서는 옮기지 않고 앞 위치에 머문다. 다음 구간은 다시
                # 제 목표 위치로 가려 한다.
                for later in bar_numbers[index_of[bar] :]:
                    if later != bar and later in section_starts:
                        break
                    if by_bar[later].position == here:
                        by_bar[later] = by_bar[later]._replace(position=position)
                here = position
        if here != position:
            position, position_start = here, bar


def _before(bar: int, bar_numbers: Sequence[int]) -> int | None:
    """``bar`` 바로 앞 마디. 첫 마디면 None."""
    index = bar_numbers.index(bar)
    return bar_numbers[index - 1] if index > 0 else None


def _dark_head(
    bar: int,
    bar_numbers: Sequence[int],
    bar_ms: Mapping[int, int],
    need_ms: float,
    section_starts: frozenset[int],
) -> list[int]:
    """``bar`` 에서 시작하는 구간 첫머리의 사전이동 쉼 마디들. 같은 구간에 켜는 마디가 남아야 한다.

    쉼 뒤 첫 켜는 마디 e 는 사전이동 마디(``bar`` 다음 마디)부터 ``need_ms`` 이상 지난 가장 이른
    마디다. e 가 없거나 다음 구간에 들어가면 빈 목록이다.
    """
    index = bar_numbers.index(bar)
    if index + 1 >= len(bar_numbers):
        return []
    premove_ms = bar_ms[bar_numbers[index + 1]]
    for later in bar_numbers[index + 1 :]:
        if later in section_starts:
            return []
        if bar_ms[later] - premove_ms >= need_ms:
            return list(bar_numbers[index : bar_numbers.index(later)])
    return []


def _is_blind_line(track: Mapping[str, Any]) -> bool:
    """강조 층 가운데 블라인드 줄인가. 스트로브 줄을 이름으로 가르는 ``_cell_plan`` 과 같다."""
    return track.get("layer_role") == "effect" and "STROBE" not in str(track["group_name"]).upper()


def _pre_hit_bars(sections: Sequence[SegmentSection]) -> list[int]:
    """강조 구간(후렴·마지막 후렴·드롭)이 바로 이어 시작하는 구간의 끝 마디 — 큰 히트 직전에
    비우는 예고 칸이 서는 마디.

    구간은 서로 이어져 있어서 다음 구간의 시작 마디가 앞 구간 끝 마디 바로 다음이다. 앞 구간이
    무엇이든(빌드·브리지·드롭) 강조 직전 마디다 — 곡 후반의 브리지→드롭, 드롭→마지막 후렴도
    같은 규칙이다(인수 D-07, 2026-10-17). 앞 구간이 한 마디짜리 강조 구간이면 그 마디는 강조라
    예고를 두지 않는다.
    """
    return [
        before.end_bar
        for before, after in zip(sections, sections[1:], strict=False)
        if after.kind in _HIT_KINDS
        and not (before.kind in _HIT_KINDS and before.start_bar == before.end_bar)
    ]


# @MX:NOTE: [AUTO] 칸을 나누는 값은 라벨·밝기·움직임이다. 구간 종류·구간 경계·계획 색은 값이 아니다.
def _runs(
    plans: Mapping[int, _CellPlan],
    bar_numbers: Sequence[int],
    *,
    splits_on_color: bool,
    annotated: frozenset[int],
    phrase_starts: frozenset[int] = frozenset(),
) -> list[tuple[int, _CellPlan]]:
    """마디별 계획을 값이 같은 연속 마디로 묶어 (첫 마디, 그 마디의 계획) 목록으로 돌려준다.

    값은 라벨·밝기·움직임·규칙 종류, 곧 계획 색을 뺀 계획이다. 쉬는 계획도 다른 계획과 똑같이
    세므로 쉬는 연속 마디는 구간 경계를 몇 번 넘어도 쉼 한 칸이다. 예고 칸은 쉼과 밝기가 같지만
    라벨이 달라서 쉼 칸에 묻히지 않는다.

    색은 칸의 속성이라 칸 첫 마디의 색이다. 색이 바뀌는 마디에서 칸을 나누는 경우는 둘이다.
    ``splits_on_color`` 인 줄(워시 줄)과, 그 마디나 앞 마디가 곡별 주석 색(``annotated``)을 가진
    경우다. 주석 색은 그 마디의 칸이 보여 줘야 해서 줄을 가리지 않는다. 앞뒤와 색이 같으면 나누지
    않는다(역광 줄에 역광 색을 주석으로 한 번 더 적어도 칸은 늘지 않는다).

    ``phrase_starts`` 의 마디에서는 켜는 칸이 값이 같아도 새로 선다(쉬는 칸은 이어진다).
    """
    rows: list[tuple[int, _CellPlan]] = []
    for index, bar in enumerate(bar_numbers):
        plan = plans[bar]
        if index > 0 and not (bar in phrase_starts and plan.brightness_percent > 0):
            before_bar = bar_numbers[index - 1]
            before = plans[before_bar]
            same_values = plan._replace(color_rgb=None) == before._replace(color_rgb=None)
            color_matters = splits_on_color or bar in annotated or before_bar in annotated
            if same_values and (plan.color_rgb == before.color_rgb or not color_matters):
                continue
        rows.append((bar, plan))
    return rows


def _tail_bar(bar_map: Mapping[str, Any]) -> int | None:
    """곡 마지막 마디가 박이 모자란 꼬리 마디(마지막 다운비트 뒤 남은 소리)면 그 번호, 아니면
    ``None``. 박자표가 없거나 읽히지 않으면 꼬리를 모르므로 ``None`` 이다."""
    signature = bar_map.get("time_signature")
    bars = bar_map.get("bars") or []
    if not isinstance(signature, Sequence) or not signature or not bars:
        return None
    last = max(bars, key=lambda entry: int(entry["bar"]))
    beats = last.get("beats_ms")
    if not isinstance(beats, Sequence) or not isinstance(signature[0], int):
        return None
    return int(last["bar"]) if len(beats) < signature[0] else None


def _ending_dark(
    runs: list[tuple[int, _CellPlan]], last_bar: int, dark: _CellPlan
) -> list[tuple[int, _CellPlan]]:
    """켜진 채 끝나는 줄에 곡 꼬리 마디의 꺼진 끝 칸을 둔다(4차 전체 실행 D-11).

    끝 칸은 Release 를 받지만 Release 는 앞에서 이어 온 값을 놓을 뿐 그 칸이 쥔 값은 남긴다 —
    끝 칸이 켜진 값이면 곡 끝 Off 까지 켜져 있다(full4: MOVER-D 82마디 DIM-100 이 3 초).
    마지막 칸이 그 마디에서 시작하면 그 칸을 꺼진 칸으로 바꾸고, 바로 앞 칸이 이미 꺼진 칸이면
    그 칸이 끝 칸이 된다. 이미 꺼진 채 끝나는 줄과 칸이 그 마디 하나뿐인 줄은 그대로다.
    꼬리가 없는(마지막 마디가 꽉 찬) 곡은 부르지 않는다 — 곡 끝 Off 가 그 마디 끝에서 끈다."""
    if not runs or runs[-1][1].brightness_percent <= 0:
        return runs
    out = list(runs)
    if out[-1][0] == last_bar:
        if len(out) == 1:
            return out
        out.pop()
        if out[-1][1].brightness_percent <= 0:
            return out
    out.append((last_bar, dark))
    return out


#: 줄(시퀀스)의 첫 칸·끝 칸·프레이즈 칸의 트래킹 값(``beat_grid_emit._entry_plan`` 이 읽는 값과
#: 같다). 구간 첫 칸은 콘솔 기본값 Track 이라 값을 두지 않는다(``None``).
_TRACKING_FIRST = "Block"
_TRACKING_LAST = "Release"
_TRACKING_PHRASE = "Cue Only"


def _with_tracking(cues: list[BeatGridCue], section_starts: frozenset[int]) -> list[BeatGridCue]:
    """줄의 칸마다 트래킹 값을 싣는다(인수 D-11, 리드 지시 2026-10-17).

    - 첫 칸은 Block — 앞 곡·이전 상태가 새어 들어오지 않게 막는다.
    - 끝 칸은 Release — 이 줄이 끝나면 쥔 값을 놓는다(새어 나감 0).
    - 구간 첫 칸은 Track(콘솔 기본값, 값 없음) — 구간 안에서 값이 이어진다.
    - 그 밖(프레이즈 칸·구간 안 쉼)은 Cue Only — 그 칸의 값이 다음 칸으로 번지지 않는다.

    칸이 하나뿐인 줄은 Block 하나다(생성기는 켜진 채 끝나는 줄에 꺼진 끝 칸을 둬서 Release 를
    준다 — ``_ending_dark``).
    앞에서부터 처음 맞는 규칙을 쓴다."""
    last = len(cues) - 1
    for position, cue in enumerate(cues):
        if position == 0:
            tracking: str | None = _TRACKING_FIRST
        elif position == last:
            tracking = _TRACKING_LAST
        elif int(cue["bar"]) in section_starts:
            tracking = None
        else:
            tracking = _TRACKING_PHRASE
        if tracking is not None:
            entry = {**(cue.get("entry") or {}), "tracking": tracking}
            cue["entry"] = entry  # type: ignore[typeddict-item]
    return cues


def _motion_axes(track: Mapping[str, Any]) -> tuple[str, ...]:
    """이 줄의 웨이브 축 — 확인된 그룹 번호로 실측 기록(``measured_movements.yaml``)을 읽어 보이는
    축을 고른다. 기본 팬 웨이브가 「기울인 기준에서만 보임」으로 닫힌 그룹은 기준과 무관하게 보이는
    축(예: MOVER-D 의 틸트 웨이브, probe-moverd D1·D3)으로 낸다. 번호가 확인 안 됐으면
    기본 축이다."""
    group_no = track.get("group_no") if track.get("group_no_confirmed") else None
    return visible_axes(group_no if isinstance(group_no, int) else None, "wave", _MOTION_AXES)


def _segment_cue(
    bar: int,
    plan: _CellPlan,
    settings: ArrangementPolicy,
    *,
    role: object,
    color_names: Mapping[tuple[int, int, int], str],
    axes: Sequence[str] = _MOTION_AXES,
) -> BeatGridCue:
    """칸 하나를 기존 생성기의 ``_draft_cue`` 로 만든다 — 라벨은 구간 단위 말 표로, 출처 표식은 이
    생성기의 것으로 한다. 계획 위치는 ``_draft_cue`` 가 방향 값에서 파생한다."""
    cue = _draft_cue(
        bar, plan, settings, role=role, words=SEGMENT_WORDS, color_names=color_names, axes=axes
    )
    cue["source_ref"] = f"{SOURCE}:{plan.kind}"
    return cue


def _unconfirmed(note: str) -> ArrangementDraft:
    return ArrangementDraft(tracks=[], windows=[], bar_range={}, source=SOURCE, note=note)
