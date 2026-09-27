"""고친 초안을 콘솔로 보낼 **명령 계획**을 세운다 (t291).

이 모듈도 `cue_sheet_edit` 과 같이 **아무것도 실행하지 않는다.** 여기서 나오는
것은 명령 문자열 목록과 「보내지 못한 큐 + 사유」 목록뿐이고, 실제 발사는
호출자가 기존 `run_commands` 경로로 넘겨서 한다 — 미리보기 카드·승인·LiveLock·
감사 로그가 전부 그 한 경로에 이미 붙어 있으므로, 두 번째 실행 표면을 만들지
않는 것이 이 모듈의 존재 이유다.

## 범위: 바뀐 큐만 (전체 재구축 아님)

계획은 **초안에서 실제로 달라진 큐**만 담고, 그 큐도 `Store … /Merge` 로
기존 큐에 겹쳐 쓴다. 전체 재구축을 고르지 않은 이유 셋:

* 감독이 건드리지 않은 큐를 다시 쓰면, 콘솔에서 손으로 고쳐 둔 값이 조용히
  덮인다. 앱에는 복구 경로가 없다.
* 전체 재구축은 룩 라이브러리·역할 해석·타임코드 슬롯까지 다시 세워야 하고,
  그것은 `prepare_songcue` 가 이미 하는 일이다. 이 경로는 그 자리를 대신하지
  않는다 — 새 곡을 세우는 것은 여전히 `prepare_songcue` 다.
* `/Merge` 는 한 큐 안에서도 **이 명령이 실은 값만** 바꾼다. 그래서 조도만
  고친 초안이 그 큐의 컬러·포지션을 지우지 않는다.

건드리지 않은 큐는 **콘솔에서도 그대로 남는다** — 이 계획이 그 큐를 언급조차
하지 않기 때문이다.

## 시퀀스 슬롯이 그 사이 바뀌었다면

계획은 타임라인이 말하는 시퀀스 번호에 그대로 쓴다. 그 슬롯이 다른 곡으로
바뀌었는지는 이 순수 함수가 알 수 없으므로 **판단하지 않는다**: 계획은
`sequence_number` 를 결과에 실어 올리고, 호출자가 미리보기 카드에 그 번호를
그대로 띄운다. 감독이 「Sequence 210 Cue 20」을 읽고 승인하는 것이 이 위험에
대한 이 저장소의 방어다(승인 카드는 이미 모든 콘솔 쓰기에 붙어 있다).

## 정직한 부분 성공

콘솔 값으로 옮기는 칸은 **조도·컬러·페이드** 셋이다(t293). 셋 다 명령 형태를
지어내지 않고 이 저장소에 **이미 있는 생산자**에서 가져왔다:

* 조도 — ``Attribute 'Dimmer' At <%>``. 줄 형태는 `server/looks/instantiate.py`
  의 ``_values_line`` (:288), 속성 이름은 `server/looks/library/*.yaml`.
* 컬러 — ``Attribute 'ColorRGB_R' At <%> ; …``. 같은 줄 형태에 같은 출처의
  속성 이름. 색값은 감독의 타임라인이 들고 다니는 ``palette_legend``
  (`server/design/sugar_timeline.py:55-63`)에서 읽고, 이름→색 판독은 화면과
  같은 규칙이다(`ui/src/components/CueSheetTimeline.tsx` `paletteColorFor`).
* 페이드 — ``Store … Cue N CueFade <초> /Merge``.
  `docs/handoff/2026-08-15-timeline-workflow-handoff.md:19` 이 이 형태만 쓰라고
  적었고(``Property 'Fade'`` 는 금지), ``/Merge`` 와 함께 쓴 실행 기록은
  `.moai/specs/SPEC-COPILOT-INTENT-001/progress.md:66` 에 있다.

카드 t469 가 실기 실측 뒤 두 칸을 더했다(`.moai/reports/t469/verdict.md`):

* 트래킹 — Release 는 ``Set Cue N Sequence S Property 'Release' 1|0`` (되읽힘),
  Block 은 ``Block``/``Unblock Sequence S Cue N``, Cue Only 는 저장 옵션
  ``/CueOnly`` (둘 다 트래킹 시트로 확인). Cue Only 는 되돌리는 명령이 없다.
* 포지션 — 초안에 **번호**(``2.<n>``)가 있을 때만 ``<그룹> ; At Preset 2.<n>`` 을
  값 줄에 붙인다. 그 프리셋에 선택 기구 값이 없으면 콘솔은 OK 를 돌려주고
  아무것도 싣지 않는다 — 요약의 번호를 화면에서 확인해야 한다.

카드 t477 — 페이저는 초안에 **번호**(``phaser_preset_no``, ``<풀>.<n>``)가 있을 때만 같은
모양(``<그룹> ; At Preset <풀>.<n>``)으로 싣는다. 이름만 있는 포지션·페이저의 번호는 세션이
반영 직전 콘솔 풀을 읽어 채운다(``ChatSession._resolve_draft_preset_names``) — 이 모듈은
여전히 콘솔을 읽지 않는다.

무드·무브먼트·이펙트·전환·노트·MIB 모드와 번호 없는 페이저는 출처를 못 대서 **넓히지 않았다**.
칸마다 왜 못 보내는지는 :data:`UNSOURCED_FIELD_REASONS` 에 적혀 있고, 그
문장이 건너뜀 사유로 그대로 나간다. 사유 **코드**는 새로 만들지 않고 t277 이
이미 쓰던 두 개를 그대로 쓴다:

* :data:`UNMAPPED_LOOK` — 이 큐의 변경이 콘솔 값으로 옮겨지지 않는다.
* :data:`ROLE_UNADDRESSED` — 옮길 값은 있는데 그 그룹의 콘솔 번호를 모른다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from server.design.color_names import resolve_color_name
from server.design.cue_fade import store_with_fade
from server.design.cue_sheet_edit import section_intensity_percent
from server.design.rig import _LAYER_GROUP_ALIASES
from server.looks.songcue import UNMAPPED_LOOK
from server.looks.songcue_report import ROLE_UNADDRESSED

__all__ = [
    "CONSOLE_APPLIABLE_FIELDS",
    "ROLE_UNADDRESSED",
    "UNMAPPED_LOOK",
    "UNSOURCED_FIELD_REASONS",
    "ConsoleApplyError",
    "ConsoleApplyPlan",
    "CuePlan",
    "CueSkip",
    "changed_cue_numbers",
    "layer_mapping_from_console_groups",
    "palette_index",
    "plan_console_apply",
    "plan_cue_console_apply",
    "timeline_group_names",
]

_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")

#: 콘솔 값으로 옮길 수 있는 칸. 이 표 밖의 변경은 `UNMAPPED_LOOK` 로 보고된다.
#:
#: 각 칸의 명령 형태는 **이 저장소에 이미 있는 생산자**에서 가져왔다(t293).
#: 출처를 못 대는 칸은 넓히지 않았다 — 아래 :data:`UNSOURCED_FIELD_REASONS` 가
#: 그 목록과 사유다.
#: 카드 t409 — ``palette_secondary`` 가 여기 합류했다. 감독 판정("메인 색
#: 깔고 포인트는 보조로")에 따라 ``layer_mapping`` 의 ``back`` 역할 그룹이
#: 있으면 그 그룹에 얹는다(:func:`plan_cue_console_apply` 안의 보조 컬러
#: 절 — 별도 함수로 뽑혀 있지 않다). 대상이 없으면 여전히
#: :data:`ROLE_UNADDRESSED` 로 정직하게 건너뛴다 — 조용히 메인 색만 내고
#: 보조를 실은 척하지 않는다.
CONSOLE_APPLIABLE_FIELDS: tuple[str, ...] = (
    "intensity",
    "d_level",
    "palette_primary",
    "palette_secondary",
    "fade_seconds",
    # 카드 t469 — 실측 뒤 합류(`.moai/reports/t469/verdict.md`).
    "tracking",
    "position_preset_no",
    # 카드 t477 — 세션이 반영 직전 콘솔 풀에서 이름으로 찾아 채운 번호.
    "phaser_preset_no",
)

#: 콘솔로 못 보내는 칸과 **그 이유**. 「지원 안 함」이라고만 적으면 감독은 이게
#: 버그인지 경계인지 알 수 없다. 사유는 칸마다 다르고, 여기 적힌 그대로 나간다.
UNSOURCED_FIELD_REASONS: dict[str, str] = {
    "mood": (
        "무드는 콘솔 값이 아니라 룩을 고르는 말입니다 — 값으로 옮기려면 룩 "
        "라이브러리를 다시 태워야 하고, 그것은 `prepare_songcue` 의 일입니다"
    ),
    "movement": (
        "무브먼트(Pan/Tilt) 명령 형태가 이 저장소에 없습니다 — 룩 라이브러리는 "
        "움직임을 담지 않기로 한 설계입니다(`server/looks/library/worship.yaml`)"
    ),
    "effect": (
        "이펙트는 페이저 스텝 축을 요구하고, 그 효과는 이 콘솔에서 기계로 "
        "되읽히지 않습니다(SPEC-COPILOT-FXLIB-001 M0 실측) — 지어내지 않습니다"
    ),
    "trans": (
        "전환(SNAP/XFADE/FADE)을 페이드 초로 환산하는 근거가 이 저장소에 "
        "없습니다 — 페이드는 초 값이 적힌 큐만 나갑니다"
    ),
    "note": "노트는 콘솔에 값이 없는 칸입니다 — 초안과 저장본에만 남습니다",
    # 카드 t466 이 파서에 넣은 네 칸 중 트래킹·포지션은 카드 t469 가 실측 뒤 콘솔로
    # 보낸다(아래 `_tracking_plan`·`_position_recall`). 남은 두 칸의 사유:
    "mib_mode": (
        "MIB 모드는 콘솔 값이 아닙니다 — 이 저장소의 MIB 는 곡 큐 조립기가 어둠 속 "
        "사전이동 큐를 직접 넣는 방식이라(카드 t468), 콘솔 MIB 속성을 켜면 옮기는 "
        "쪽이 둘이 됩니다. 곡을 다시 조립할 때 반영됩니다"
    ),
    "phaser": (
        "페이저 프리셋을 큐에 싣는 형태(`At Preset <풀>.<번호>` 뒤 `/Merge`)는 실측됐지만"
        "(카드 t469), 이 페이저 이름의 콘솔 풀 번호가 없습니다 — 반영 전에 콘솔 풀에서 "
        "이름으로 찾고(카드 t477), 못 찾으면 번호를 지어내지 않습니다"
    ),
}

#: 카드 t469 — 초안 ``tracking`` 칸이 받는 값(`cue_sheet_edit.TRACKING_VALUES` 와 같다).
_TRACK = "Track"
_BLOCK = "Block"
_CUE_ONLY = "Cue Only"
_RELEASE = "Release"
_TRACKING_VALUES = (_TRACK, _BLOCK, _CUE_ONLY, _RELEASE)
#: 포지션 프리셋 번호 — 풀 2 만(`cue_sheet_edit` 이 이미 막는 규칙을 반영 쪽에서도 지킨다).
_POSITION_PRESET_NO = re.compile(r"2\.[1-9]\d*")
#: 카드 t477 — 페이저 프리셋 번호 ``<풀>.<슬롯>``. 풀은 이름으로 찾으므로 고정하지 않는다
#: (t469 실측은 21.4 = All 1 풀의 DIM-BREATHE).
_PHASER_PRESET_NO = re.compile(r"[1-9]\d*\.[1-9]\d*")


class ConsoleApplyError(ValueError):
    """계획 자체를 세울 수 없다. 메시지는 감독에게 그대로 보여도 되는 사유다."""


@dataclass(frozen=True)
class CueSkip:
    """보내지 않은 큐 하나와 그 사유. 사유는 한 가지 원인만 지목한다(t112)."""

    cue_number: int
    label: str
    reason: str
    detail: str


@dataclass(frozen=True)
class CuePlan:
    """큐 **하나**에 대한 반영 판정 — 「무엇이 나가는가」와 「무엇이 안 나가는가」.

    시퀀스 번호를 담지 않는 것이 이 타입의 요점이다(t304). 큐가 나가는지 안
    나가는지는 시퀀스 번호와 무관하고, 번호는 :func:`plan_console_apply` 가
    ``Store Sequence N Cue M`` 을 지을 때에만 쓴다. 그래서 사전 점검은 번호를
    지어내지 않고도 **반영과 같은 판정**을 받아 볼 수 있다.
    """

    cue_number: int
    label: str
    #: 프로그래머 줄. 빈 문자열이면 이 큐는 콘솔로 한 줄도 나가지 않는다.
    value_line: str = ""
    fade_seconds: float | None = None
    percent: int | None = None
    #: 「조도 90% · 컬러 P2 …」 — 감독이 읽는 한 줄.
    summary: str = ""
    #: 이 큐에서 **못 보낸 것**과 사유. 나가는 큐에도 붙을 수 있다(부분 성공).
    skips: tuple[CueSkip, ...] = ()
    #: 카드 t469 — ``Store … /Merge`` 뒤에 붙는 저장 옵션(Cue Only 는 ``/CueOnly``).
    store_options: tuple[str, ...] = ()
    #: 카드 t469 — 저장 뒤 거는 트래킹 동작. 시퀀스 번호가 필요한 명령이라 여기서는
    #: 이름만 들고(``release_on``·``release_off``·``block``·``unblock``), 문면은 번호를
    #: 아는 :func:`plan_console_apply` 가 짓는다(t304 — 큐 판정은 번호를 모른다).
    tracking_ops: tuple[str, ...] = ()

    @property
    def would_apply(self) -> bool:
        return bool(self.value_line)


@dataclass(frozen=True)
class ConsoleApplyPlan:
    sequence_number: int
    commands: tuple[str, ...] = ()
    applied: tuple[int, ...] = ()
    skipped: tuple[CueSkip, ...] = ()
    #: 큐별 조도 목표값 — 미리보기 문구가 「무엇이 나가는지」를 적을 때 쓴다.
    targets: Mapping[int, int] = field(default_factory=dict)
    #: 큐별 한 줄 요약 — 조도 말고 무엇이 같이 나갔는지 감독이 읽는 자리(t293).
    summaries: Mapping[int, str] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.commands


def _sections(timeline: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw = timeline.get("sections")
    if not isinstance(raw, list):
        return []
    return [section for section in raw if isinstance(section, Mapping)]


def _by_cue(timeline: Mapping[str, object]) -> dict[int, Mapping[str, object]]:
    return {
        int(section["cue_number"]): section
        for section in _sections(timeline)
        if isinstance(section.get("cue_number"), int)
    }


def changed_cue_numbers(
    baseline: Mapping[str, object], current: Mapping[str, object]
) -> tuple[int, ...]:
    """초안이 기준본에서 실제로 달라진 큐 번호들, 큐시트 순서 그대로.

    되돌리기로 원래 값으로 돌아온 큐는 여기 나오지 않는다 — 비교는 이력의
    걸음 수가 아니라 **값**을 보기 때문이다. 기준본에 없던 큐는 「달라진 큐」로
    센다(새로 생긴 큐).
    """
    before = _by_cue(baseline)
    changed: list[int] = []
    for section in _sections(current):
        cue = section.get("cue_number")
        if not isinstance(cue, int):
            continue
        previous = before.get(cue)
        if previous is None or dict(previous) != dict(section):
            changed.append(cue)
    return tuple(changed)


def _section_group_names(section: Mapping[str, object]) -> list[str]:
    """구간이 지목한 Fixture Group 이름들 — 사다리 ①②③ 그대로.

    ① ``fixture_groups`` → ② ``intensity[].group`` → ③ 리터럴 ``ALL``.
    """
    names = section.get("fixture_groups")
    names = [str(name).strip() for name in names] if isinstance(names, list) else []
    names = [name for name in names if name]
    if not names:
        entries = section.get("intensity")
        if isinstance(entries, list):
            names = [
                str(entry["group"]).strip()
                for entry in entries
                if isinstance(entry, Mapping) and entry.get("group")
            ]
    if not names:
        names = ["ALL"]
    return names


def timeline_group_names(timeline: Mapping[str, object]) -> tuple[str, ...]:
    """타임라인이 실제로 지목하는 그룹 이름들 (등장 순서, 중복 제거).

    리터럴 ``ALL`` 은 주소가 필요한 이름이 아니라 「주소록에 적힌 것 전부」를
    뜻하는 지시어라 빠진다. 여기서 나오는 것은 **감독의 타임라인이 적어 둔
    이름**뿐이다 — 이 함수는 콘솔을 보지 않는다.
    """
    seen: dict[str, str] = {}
    for section in _sections(timeline):
        for name in _section_group_names(section):
            if name.casefold() == "all":
                continue
            seen.setdefault(name.casefold(), name)
    return tuple(seen.values())


def layer_mapping_from_console_groups(
    payload: object, names: Sequence[str]
) -> list[dict[str, object]]:
    """콘솔이 스스로 보고한 그룹 이름과 타임라인의 이름을 **정확히** 맞춘다.

    두 출처만 쓴다: 콘솔이 답한 ``DataPool/Groups`` 의 이름·번호와, 감독의
    타임라인이 적어 둔 이름. 대조는 앞뒤 공백을 떼고 대소문자를 접은
    **완전 일치**뿐이다 — 하이픈과 공백을 같게 보거나 부분 문자열로 맞추는
    것은 짐작이고, 잘못된 그룹에 쏘는 사고가 이 저장소에서 가장 비싸다.

    그룹 **멤버십**은 이 통로로 읽을 수 없으므로 어느 픽스처가 들어 있는지는
    주장하지 않는다. 기록하는 것은 「이 이름이 콘솔 몇 번 그룹인가」뿐이다.
    맞는 이름이 없으면 그 이름은 주소록에 안 들어가고, 그 큐는 나중에
    ``ROLE_UNADDRESSED`` 로 건너뛴다 — 없는 것이 틀린 것보다 낫다.

    카드 t409 후속 — 그룹 이름이 `server/design/rig.py` 의
    ``_LAYER_GROUP_ALIASES``(RG5 — 정확 일치만, 부분 문자열 추측 없음)에
    걸리면 ``role`` 도 같이 적는다. `server/web/session.py` 의
    `_layer_mapping_from_group_children` 가 이미 같은 표로 역할을 매기고
    있었는데, 이 함수(사전 점검·시드 곡 반영이 쓰는 주소록 생성기)만 표를
    쓰지 않아 콘솔이 실제로 보고한 "BACK" 그룹이 있어도 ``role: "back"``
    이 안 붙었다 — 보조 컬러의 back 역할 조회(``plan_cue_console_apply``)가
    이 경로에서는 항상 실패하는 원인이었다(감독 재정 — 리그가 진짜로
    back 레이어가 없는 게 아니라, 이 주소록 생성기가 role 을 안 적었을
    뿐이다).
    """
    if not isinstance(payload, Mapping):
        return []
    children = payload.get("children")
    if not isinstance(children, list):
        return []
    wanted = {name.strip().casefold(): name for name in names if str(name).strip()}
    mapping: list[dict[str, object]] = []
    claimed: set[str] = set()
    for child in children:
        if not isinstance(child, Mapping):
            continue
        console_name = str(child.get("name") or "").strip()
        number = child.get("i") if isinstance(child.get("i"), int) else child.get("no")
        if not console_name or not isinstance(number, int):
            continue
        key = console_name.casefold()
        if key not in wanted or key in claimed:
            continue
        claimed.add(key)
        # 타임라인이 쓴 철자로 적는다 — `_group_numbers` 는 이 이름으로 찾는다.
        entry: dict[str, object] = {"group_name": wanted[key], "group_no": number}
        for role, aliases in _LAYER_GROUP_ALIASES.items():
            if key in aliases:
                entry["role"] = role
                break
        mapping.append(entry)
    return mapping


def _group_numbers(
    section: Mapping[str, object], layer_mapping: Sequence[Mapping[str, object]]
) -> tuple[list[int], list[str]]:
    """구간의 Fixture Group 이름을 콘솔 그룹 번호로 옮긴다.

    주소록은 감독이 기록한 ``layer_mapping`` 하나뿐이다 — 이름을 짐작해서
    번호를 만들지 않는다(잘못된 슬롯에 쏘는 것이 이 저장소의 가장 비싼 사고다).
    돌려주는 둘째 값은 **주소를 못 찾은 이름들**이다.

    이름의 출처는 사다리다(실측 2026-09-06: 이 앱이 만드는 타임라인 두 계열이
    서로 다른 칸을 채운다 — 정본 시드는 ``fixture_groups`` 를 들고 오고, 설계
    인터뷰가 만든 판은 그 칸 없이 전체 조도만 들고 온다):

    ① ``fixture_groups`` → ② ``intensity[].group`` → ③ 리터럴 ``ALL``.

    ``ALL`` 은 **감독이 기록한 그룹 전부**로 풀린다. 리그 전체가 아니라 그
    주소록에 적힌 것들이다 — 적히지 않은 그룹의 번호를 이 함수는 모른다.
    """
    names = _section_group_names(section)
    index: dict[str, int] = {}
    for entry in layer_mapping:
        number = entry.get("group_no")
        if not isinstance(number, int):
            continue
        for key in (entry.get("group_name"), entry.get("role")):
            if isinstance(key, str) and key.strip():
                index.setdefault(key.strip().casefold(), number)
    numbers: list[int] = []
    unresolved: list[str] = []
    for name in names:
        if name.casefold() == "all":
            if not index:
                unresolved.append(name)
                continue
            for number in index.values():
                if number not in numbers:
                    numbers.append(number)
            continue
        number = index.get(name.casefold())
        if number is None:
            unresolved.append(name)
        elif number not in numbers:
            numbers.append(number)
    return numbers, unresolved


def _intensity_changed(
    previous: Mapping[str, object] | None, section: Mapping[str, object]
) -> bool:
    if previous is None:
        return True
    if section_intensity_percent(previous) != section_intensity_percent(section):
        return True
    return previous.get("intensity") != section.get("intensity")


def palette_index(timeline: Mapping[str, object]) -> dict[str, str]:
    """팔레트 범례 → ``{id 또는 이름(소문자): #RRGGBB}``.

    출처는 감독의 타임라인이 들고 다니는 ``palette_legend`` 하나뿐이다
    (`server/design/sugar_timeline.py:55-63` 이 만들고 `:482` 가 실어 보낸다).
    화면이 색을 찾는 규칙과 같은 규칙이다 —
    `ui/src/components/CueSheetTimeline.tsx` 의 `paletteColorFor`.
    """
    legend = timeline.get("palette_legend")
    index: dict[str, str] = {}
    if not isinstance(legend, list):
        return index
    for entry in legend:
        if not isinstance(entry, Mapping):
            continue
        color = str(entry.get("color") or "").strip()
        if not _HEX_COLOR.fullmatch(color):
            continue
        for key in (entry.get("id"), entry.get("name")):
            if isinstance(key, str) and key.strip():
                index.setdefault(key.strip().casefold(), color)
    return index


def _palette_rgb(index: Mapping[str, str], value: object) -> tuple[int, int, int] | None:
    """``"P4 핫핑크"`` → ``(r, g, b)`` 백분율. 어디에도 없으면 ``None``.

    앞 토큰(``P4``)이 범례 id 다 — 화면과 같은 판독이다. 백분율 축인 이유는
    룩 라이브러리가 그 축으로 적혀 있기 때문이다(`server/looks/library/*.yaml`
    의 ``ColorRGB_R`` 등은 전부 0..100).

    카드 t408 — 범례(``index``)는 실제 곡 분석 경로에는 아예 안 실린다
    (룩 라이브러리가 팔레트에 이름을 안 달아서 지어낼 수 없다는 이유,
    `server/web/session.py` 의 `_song_cue_sheet_view_fields` 주석). 그래서
    범례 조회가 실패하면 곧바로 포기하지 않고
    :func:`server.design.color_names.resolve_color_name` 로 한 번 더
    시도한다 — 아크가 내는 "warm white"·"cold blue" 같은 순정 색 이름과
    감독의 한국어 원색 표기를 표준 무대 팔레트 10색(spec.md §A.2)에서
    찾는다. 그 표에도 없는 이름("gold"·"warm special" 등)은 여전히
    ``None`` — 두 출처 모두 실패해야 진짜로 못 찾은 것이다.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    token = value.strip().split()[0].casefold()
    color = index.get(token) or index.get(value.strip().casefold())
    if color is not None:
        raw = color.lstrip("#")
        channels = tuple(int(raw[offset : offset + 2], 16) for offset in (0, 2, 4))
        return tuple(round(channel * 100 / 255) for channel in channels)  # type: ignore[return-value]
    return resolve_color_name(value.strip())


def _color_line(rgb: tuple[int, int, int]) -> str:
    """``Attribute 'ColorRGB_R' At 100 ; …`` — 독립 세팅은 한 줄에 ``;`` 로 잇는다.

    줄 형태의 출처는 `server/looks/instantiate.py:288` (`_values_line`), 속성
    이름의 출처는 `server/looks/library/*.yaml` 이다. 라이브 실행 예:
    ``Group 4 + 5 + 6 + 7 ; Attribute 'Dimmer' At 72 ; ColorRGB…``.
    """
    return " ; ".join(
        f"Attribute 'ColorRGB_{axis}' At {value:g}"
        for axis, value in zip(("R", "G", "B"), rgb, strict=True)
    )


def _fade_seconds(section: Mapping[str, object]) -> float | None:
    value = section.get("fade_seconds")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _group_dimmer_overrides(
    section: Mapping[str, object],
    layer_mapping: Sequence[Mapping[str, object]],
    numbers: Sequence[int],
    unresolved: Sequence[str],
    percent: int,
) -> tuple[list[str], list[str], str | None]:
    """카드 t461 — 최댓값보다 낮은 그룹의 Dimmer 덮어쓰기 줄.

    ``(줄들, 요약 조각들, 못 나눈 사유)``. 그룹 이름 → 콘솔 번호는
    :func:`_group_numbers` 와 같은 주소록(``layer_mapping`` 의 group_name·role,
    정확 일치)으로만 푼다. 번호를 모르거나 이 큐가 지목하지 않은 그룹이면 줄을
    하나도 내지 않고(한 값 그대로) 사유를 낸다 — 지어내지 않는다. 이미 이 큐의
    대상에서 빠진 그룹(``unresolved``)은 기존 사유가 말하므로 새 사유를 달지 않는다.
    """
    entries = section.get("intensity")
    if not isinstance(entries, list):
        return [], [], None
    lower: list[tuple[str, int]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or not entry.get("group"):
            continue
        level = entry.get("level")
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            continue
        if int(level) != percent:
            lower.append((str(entry["group"]).strip(), int(level)))
    if not lower:
        return [], [], None
    index: dict[str, int] = {}
    for mapping in layer_mapping:
        number = mapping.get("group_no")
        if not isinstance(number, int):
            continue
        for key in (mapping.get("group_name"), mapping.get("role")):
            if isinstance(key, str) and key.strip():
                index.setdefault(key.strip().casefold(), number)
    already_out = {name.casefold() for name in unresolved}
    lines: list[str] = []
    parts: list[str] = []
    missing: list[str] = []
    for name, level in lower:
        number = index.get(name.casefold())
        if number is None or number not in numbers:
            if name.casefold() not in already_out:
                missing.append(name)
            continue
        lines.append(f"Group {number} ; Attribute 'Dimmer' At {level:g}")
        parts.append(f"{name} {level}%")
    if missing:
        return (
            [],
            [],
            "그룹별 조도를 나눠 보내지 못했습니다 — 콘솔 그룹 번호를 모르는 그룹: "
            + ", ".join(missing)
            + f". 큐 전체 {percent}% 한 값으로 보냈습니다.",
        )
    return lines, parts, None


def _tracking_value(section: Mapping[str, object] | None) -> object:
    """초안 트래킹 값. 칸이 없거나 비면 ``Track``(콘솔 기본값)으로 본다."""
    value = None if section is None else section.get("tracking")
    return _TRACK if value in (None, "") else value


def _tracking_plan(
    previous: Mapping[str, object] | None, section: Mapping[str, object]
) -> tuple[tuple[str, ...], tuple[str, ...], str | None, str | None]:
    """카드 t469 — 트래킹 전환을 ``(저장 옵션, 저장 뒤 동작, 요약, 건너뜀 사유)`` 로.

    실측(`.moai/reports/t469/verdict.md`): Release 는 큐 속성이라 켜고 끄기가 되읽힌다.
    Block 은 키워드 명령이고 ``Unblock`` 으로 푼다. Cue Only 는 **저장 옵션**이라
    저장 순간 다음 큐에 값을 박는다 — 되돌리는 명령이 없으므로 Cue Only → Track 은
    보내지 않고 사유를 단다.
    """
    before = _tracking_value(previous)
    after = _tracking_value(section)
    if previous is not None and before == after:
        return (), (), None, None
    if after not in _TRACKING_VALUES:
        if previous is None:
            return (), (), None, None
        return (
            (),
            (),
            None,
            (
                f"트래킹 값 {after!r} 은(는) Track, Block, Cue Only, Release 중 하나가 아닙니다 "
                "— 짐작해서 보내지 않습니다"
            ),
        )
    ops: list[str] = []
    # 앞 표시를 먼저 푼다(Block→Release 면 Unblock 뒤 Release).
    if before == _BLOCK and after != _BLOCK:
        ops.append("unblock")
    if before == _RELEASE and after != _RELEASE:
        ops.append("release_off")
    if after == _RELEASE:
        ops.append("release_on")
    elif after == _BLOCK:
        ops.append("block")
    options = ("/CueOnly",) if after == _CUE_ONLY else ()
    if before == _CUE_ONLY and after != _CUE_ONLY:
        return (
            options,
            tuple(ops),
            None,
            (
                "Cue Only 는 저장 순간 다음 큐에 값을 박는 저장 옵션이라 되돌리는 콘솔 명령이 "
                "없습니다 — 다음 큐의 값은 콘솔에서 직접 확인해 주세요"
            ),
        )
    if not ops and not options:
        return (), (), None, None
    return options, tuple(ops), f"트래킹 {after}", None


def _position_recall(
    previous: Mapping[str, object] | None, section: Mapping[str, object]
) -> tuple[str | None, str | None]:
    """카드 t469 — 포지션 프리셋을 ``(프리셋 번호, 건너뜀 사유)`` 로.

    ``<선택> ; At Preset 2.<n>`` 뒤 ``/Merge`` 가 큐에 프리셋을 싣는 것을 실측했다(2.2·2.5).
    단 **그 프리셋에 선택 기구 값이 없으면 콘솔은 OK 를 돌려주고 아무것도 싣지 않는다**
    (2.1·2.3·2.4·2.6 실측) — 이 경로는 그 차이를 알 수 없으므로 요약에 번호를 적어
    감독이 화면에서 확인하게 한다.
    """
    keys = ("position", "position_preset_no")
    if previous is not None and all(previous.get(k) == section.get(k) for k in keys):
        return None, None
    number = section.get("position_preset_no")
    if number in (None, ""):
        # 곡 전체 반영(`previous is None`)의 ``position`` 은 조립기가 붙인 움직임
        # 이름(``STATIC``·``TILT-UP @slow`` …)이지 감독이 고른 프리셋이 아니다 — 기존
        # UNSOURCED 칸처럼, 감독이 초안에서 **고친** 경우에만 사유를 단다.
        if previous is None or section.get("position") in (None, ""):
            return None, None
        return None, (
            f"포지션 {section.get('position')!r} 은(는) 프리셋 번호 없이 이름만 있습니다 — "
            "반영 전 콘솔 풀 판독에서 번호를 얻지 못했습니다(번호를 지어내지 않음)"
        )
    if not isinstance(number, str) or not _POSITION_PRESET_NO.fullmatch(number):
        if previous is None:
            return None, None
        return None, f"포지션 프리셋 번호 {number!r} 는 풀 2(`2.<n>`) 번호가 아닙니다"
    return number, None


def _phaser_recall(
    previous: Mapping[str, object] | None, section: Mapping[str, object]
) -> tuple[str | None, str | None]:
    """카드 t477 — 페이저 프리셋을 ``(프리셋 번호, 건너뜀 사유)`` 로.

    싣는 형태는 t469 가 실측했다: ``At Preset 21.4`` 뒤 ``/Merge`` → 큐에 ``21.4 DIM-B…`` +
    ``Step 2``. 번호는 세션이 반영 직전 콘솔 풀에서 이름으로 찾아 ``phaser_preset_no`` 에
    채운다(``ChatSession._resolve_draft_preset_names``). 번호가 없으면 ``phaser`` 는 기존
    :data:`UNSOURCED_FIELD_REASONS` 사유로 건너뛴다 — 여기서는 번호 모양만 판정한다.
    곡 전체 반영(``previous is None``)의 페이저 이름은 감독이 고친 것이 아니라 건드리지 않는다.
    """
    if previous is None:
        return None, None
    keys = ("phaser", "phaser_preset_no")
    if all(previous.get(k) == section.get(k) for k in keys):
        return None, None
    number = section.get("phaser_preset_no")
    if number in (None, ""):
        return None, None
    if not isinstance(number, str) or not _PHASER_PRESET_NO.fullmatch(number):
        return None, f"페이저 프리셋 번호 {number!r} 는 `<풀>.<번호>` 모양이 아닙니다"
    return number, None


def plan_cue_console_apply(
    section: Mapping[str, object],
    previous: Mapping[str, object] | None,
    layer_mapping: Sequence[Mapping[str, object]],
    colors: Mapping[str, str],
) -> CuePlan:
    """큐 하나가 **콘솔에 무엇을 내보내는가**. 시퀀스 번호는 쓰지 않는다.

    :func:`plan_console_apply` 의 큐별 본문이 그대로 여기로 나왔다(t304).
    사전 점검(`server/design/rig_preflight.py`)이 같은 함수를 부르기 때문에
    「점검은 나간다고 했는데 반영은 건너뛴다」가 구조적으로 생기지 않는다 —
    두 판정이 같다는 것은 주장이 아니라 **같은 코드**다.

    ``previous`` 가 ``None`` 이면 「이 큐는 통째로 새로 나간다」는 뜻이고, 그것이
    사전 점검이 묻는 질문이다(곡 전체를 지금 반영하면 무엇이 닿는가).
    """
    cue = int(section["cue_number"])
    label = str(section.get("label") or f"Cue {cue}")

    # 어느 축이 달라졌나. 축마다 명령 형태의 출처가 다르므로 따로 센다.
    intensity_changed = _intensity_changed(previous, section)
    color_changed = previous is None or (
        previous.get("palette_primary") != section.get("palette_primary")
        or previous.get("palette_secondary") != section.get("palette_secondary")
    )
    fade_changed = previous is None or _fade_seconds(previous) != _fade_seconds(section)
    # 카드 t469 — 트래킹·포지션, t477 — 페이저 번호. 못 보내는 경우의 사유는 칸마다 따로 든다.
    store_options, tracking_ops, tracking_part, tracking_reason = _tracking_plan(previous, section)
    position_no, position_reason = _position_recall(previous, section)
    phaser_no, phaser_reason = _phaser_recall(previous, section)
    field_reasons = [
        reason for reason in (tracking_reason, position_reason, phaser_reason) if reason
    ]
    unsourced = [
        name
        for name in UNSOURCED_FIELD_REASONS
        if previous is not None
        and previous.get(name) != section.get(name)
        # 번호가 있거나 번호 모양이 틀렸으면 페이저는 위 판정이 말한다(사유 중복 방지).
        and not (name == "phaser" and (phaser_no or phaser_reason))
    ]

    if not (
        intensity_changed
        or color_changed
        or fade_changed
        or store_options
        or tracking_ops
        or position_no
        or phaser_no
    ):
        reasons = "; ".join([UNSOURCED_FIELD_REASONS[name] for name in unsourced] + field_reasons)
        return CuePlan(
            cue_number=cue,
            label=label,
            skips=(
                CueSkip(
                    cue_number=cue,
                    label=label,
                    reason=UNMAPPED_LOOK,
                    detail=(
                        (reasons or "콘솔 값으로 옮길 수 있는 칸이 이 큐에는 없습니다")
                        + ". 초안과 저장본에는 남아 있습니다."
                    ),
                ),
            ),
        )

    numbers, unresolved = _group_numbers(section, layer_mapping)
    if not numbers:
        return CuePlan(
            cue_number=cue,
            label=label,
            skips=(
                CueSkip(
                    cue_number=cue,
                    label=label,
                    reason=ROLE_UNADDRESSED,
                    detail=("콘솔 그룹 번호를 모르는 대상입니다: " + ", ".join(unresolved)),
                ),
            ),
        )

    # 프로그래머 줄. 조도는 **항상** 싣는다 — 컬러·페이드만 바뀐 큐에도
    # 실을 값이 있어야 `/Merge` 가 빈 프로그래머를 저장하지 않는다. 싣는
    # 값은 초안이 말하는 현재 조도라 지어낸 값이 아니고, 값이 그대로면
    # 그 큐의 조도도 그대로다.
    percent = section_intensity_percent(section)
    selection = "Group " + " + ".join(str(number) for number in numbers)
    value_line = f"{selection} ; Attribute 'Dimmer' At {percent:g}"
    parts = [f"조도 {percent}%"]
    skips: list[CueSkip] = []

    rgb = _palette_rgb(colors, section.get("palette_primary")) if color_changed else None
    if color_changed and rgb is None:
        skips.append(
            CueSkip(
                cue_number=cue,
                label=label,
                reason=UNMAPPED_LOOK,
                detail=(
                    "컬러는 못 보냈습니다 — 팔레트 범례에 없는 이름입니다: "
                    f"{section.get('palette_primary')!r} (색을 지어내지 않습니다)."
                ),
            )
        )
    elif rgb is not None:
        value_line += " ; " + _color_line(rgb)
        parts.append(f"컬러 {section.get('palette_primary')}")

    # 카드 t409 — 감독 판정 "메인 색 깔고 포인트는 보조로". 메인은 위에서
    # 이미 나갔고, 이 칸은 `layer_mapping` 의 `back` 역할 그룹에 보조
    # 컬러를 얹는다. 대상 그룹이 없거나 색을 못 찾으면 조용히 메인만
    # 내지 않는다 — 큰 소리로 건너뛴다(정본 [HARD]).
    #
    # 감독 재정(카드 t409 후속) — `color_changed` 와 같은 축으로 판정한다
    # (previous 없음 = 처음부터 다시 반영하는 경우도 포함). 예전에는
    # `previous is not None` 으로 좁혀 첫 전체 반영(감독이 새 곡을 처음
    # 콘솔에 올리는 그 순간)에서 보조 컬러가 아예 안 나갔다 — "후렴
    # 블루 + 백라이트에 warm white" 의 백라이트 절반이 사라지는 결함이었다.
    # `_group_numbers` 가 못 찾은 이름을 조용히 버리지 않고 `ROLE_UNADDRESSED`
    # 로 건너뛰는 것과 같은 원칙 — 대상이 없으면 큰 소리로 알리되, 첫
    # 반영이라는 이유로 시도조차 안 하지는 않는다.
    secondary = section.get("palette_secondary")
    if color_changed and isinstance(secondary, str) and secondary.strip():
        back_no = next(
            (
                entry.get("group_no")
                for entry in layer_mapping
                if entry.get("role") == "back" and isinstance(entry.get("group_no"), int)
            ),
            None,
        )
        if back_no is None:
            skips.append(
                CueSkip(
                    cue_number=cue,
                    label=label,
                    reason=ROLE_UNADDRESSED,
                    detail=(
                        "보조 컬러를 못 보냈습니다 — back 역할 그룹 번호를 모릅니다: "
                        f"{secondary!r}."
                    ),
                )
            )
        else:
            secondary_rgb = _palette_rgb(colors, secondary)
            if secondary_rgb is None:
                skips.append(
                    CueSkip(
                        cue_number=cue,
                        label=label,
                        reason=UNMAPPED_LOOK,
                        detail=(
                            "보조 컬러는 못 보냈습니다 — 팔레트 범례에 없는 이름입니다: "
                            f"{secondary!r} (색을 지어내지 않습니다)."
                        ),
                    )
                )
            else:
                value_line += f" ; Group {back_no} ; " + _color_line(secondary_rgb)
                parts.append(f"보조컬러 {secondary}")

    # 카드 t461(리드 판정) — 그룹별 조도가 서로 다르면 위 한 값(최댓값) 뒤에
    # 낮은 그룹만 자기 Dimmer 줄로 덮는다(last-wins — back 레이어 줄과 같은 방식).
    # 값이 모두 같으면 아무것도 붙지 않아 명령이 바이트 그대로다.
    overrides, override_parts, split_failure = _group_dimmer_overrides(
        section, layer_mapping, numbers, unresolved, percent
    )
    if overrides:
        value_line += " ; " + " ; ".join(overrides)
        parts.extend(override_parts)
    elif split_failure:
        skips.append(
            CueSkip(cue_number=cue, label=label, reason=ROLE_UNADDRESSED, detail=split_failure)
        )

    fade = _fade_seconds(section) if fade_changed else None
    if fade is not None:
        parts.append(f"페이드 {fade:g}초")

    # 카드 t469 — 포지션 프리셋은 이 큐의 그룹 선택에 다시 걸어 싣는다(앞에서 보조
    # 컬러가 선택을 back 그룹으로 옮겼을 수 있으므로 선택부터 다시 적는다).
    if position_no is not None:
        value_line += f" ; {selection} ; At Preset {position_no}"
        parts.append(f"포지션 {position_no}")
    # 카드 t477 — 페이저도 같은 모양(t469 실측 `At Preset 21.4`). 포지션 뒤에 선택을 다시 적는다.
    if phaser_no is not None:
        value_line += f" ; {selection} ; At Preset {phaser_no}"
        parts.append(f"페이저 {phaser_no}")
    if tracking_part is not None:
        parts.append(tracking_part)
    for detail in field_reasons:
        skips.append(CueSkip(cue_number=cue, label=label, reason=UNMAPPED_LOOK, detail=detail))

    if unsourced:
        skips.append(
            CueSkip(
                cue_number=cue,
                label=label,
                reason=UNMAPPED_LOOK,
                detail=(
                    "같은 큐에서 콘솔로 못 보낸 칸이 있습니다 — "
                    + "; ".join(UNSOURCED_FIELD_REASONS[name] for name in unsourced)
                    + ". 초안과 저장본에는 남아 있습니다."
                ),
            )
        )
    if unresolved:
        # 일부만 주소가 잡힌 큐도 **나간 것과 안 나간 것을 같이** 말한다.
        skips.append(
            CueSkip(
                cue_number=cue,
                label=label,
                reason=ROLE_UNADDRESSED,
                detail=(
                    "일부 대상만 반영했습니다 — 콘솔 그룹 번호를 모르는 대상: "
                    + ", ".join(unresolved)
                ),
            )
        )
    return CuePlan(
        cue_number=cue,
        label=label,
        value_line=value_line,
        fade_seconds=fade,
        percent=percent,
        summary=" · ".join(parts),
        skips=tuple(skips),
        store_options=store_options,
        tracking_ops=tracking_ops,
    )


def _tracking_command(op: str, sequence_number: int, cue: int) -> str:
    """카드 t469 — 트래킹 동작 이름을 실측된 문면으로(`.moai/reports/t469/verdict.md`)."""
    if op == "release_on":
        return f"Set Cue {cue} Sequence {sequence_number} Property 'Release' 1"
    if op == "release_off":
        return f"Set Cue {cue} Sequence {sequence_number} Property 'Release' 0"
    if op == "block":
        return f"Block Sequence {sequence_number} Cue {cue}"
    if op == "unblock":
        return f"Unblock Sequence {sequence_number} Cue {cue}"
    raise ValueError(f"unknown tracking op {op!r}")


def plan_console_apply(
    baseline: Mapping[str, object], current: Mapping[str, object]
) -> ConsoleApplyPlan:
    """바뀐 큐들을 콘솔 명령 계획으로 옮긴다. 실행은 하지 않는다.

    계획 자체가 불가능한 두 자리에서만 :class:`ConsoleApplyError` 를 던진다 —
    바뀐 큐가 하나도 없을 때, 그리고 쓸 시퀀스 번호가 없을 때. 그 밖의 실패는
    큐 단위 :class:`CueSkip` 이라 **한 큐가 막혀도 나머지는 나간다**.
    """
    changed = changed_cue_numbers(baseline, current)
    if not changed:
        raise ConsoleApplyError(
            "초안에서 달라진 큐가 없습니다. 먼저 큐시트를 수정한 뒤 반영해 주세요."
        )
    sequence_number = current.get("sequence_number")
    if not isinstance(sequence_number, int) or sequence_number < 1:
        raise ConsoleApplyError(
            "이 타임라인에는 콘솔 시퀀스 번호가 없습니다 "
            f"(현재 값: {sequence_number!r}). 곡을 먼저 콘솔에 올린 뒤 "
            "초안 수정을 반영해 주세요."
        )
    layer_mapping = current.get("layer_mapping")
    layer_mapping = layer_mapping if isinstance(layer_mapping, list) else []
    layer_mapping = [entry for entry in layer_mapping if isinstance(entry, Mapping)]

    colors = palette_index(current)
    before = _by_cue(baseline)
    sections = _by_cue(current)
    commands: list[str] = []
    applied: list[int] = []
    skipped: list[CueSkip] = []
    targets: dict[int, int] = {}
    summaries: dict[int, str] = {}
    for cue in changed:
        # 큐별 판정은 사전 점검과 **같은 함수**다(t304) — 여기서 다시 세우지 않는다.
        decision = plan_cue_console_apply(sections[cue], before.get(cue), layer_mapping, colors)
        skipped.extend(decision.skips)
        if not decision.would_apply:
            continue
        # `CueFade` 는 이 저장소가 실측한 유일한 페이드 형태다. 조립 문면은 카드 t363
        # 에서 `server/design/cue_fade.py` 로 **들어 올렸다** — 곡→큐 경로가 같은 문법을
        # 쓰게 되면서 소비자가 둘이 됐고, 베끼면 두 벌이 조용히 갈라지기 때문이다.
        # 근거 문면(`Property 'Fade'` 금지 · `/Merge` 순서 실행 로그)은 그 파일에 있다.
        store = store_with_fade(
            f"Store Sequence {sequence_number} Cue {cue}", decision.fade_seconds
        )
        options = "".join(f" {option}" for option in decision.store_options)
        commands.extend((_CLEAR, decision.value_line, f"{store} /Merge{options}", _CLEAR))
        # 카드 t469 — 트래킹 표시는 큐가 저장된 **뒤에** 건다(실측 순서).
        commands.extend(_tracking_command(op, sequence_number, cue) for op in decision.tracking_ops)
        applied.append(cue)
        if decision.percent is not None:
            targets[cue] = decision.percent
        summaries[cue] = decision.summary
    return ConsoleApplyPlan(
        sequence_number=sequence_number,
        commands=((_DESTINATION, *commands) if commands else ()),
        applied=tuple(applied),
        skipped=tuple(skipped),
        targets=targets,
        summaries=summaries,
    )
