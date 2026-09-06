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

콘솔 값으로 옮길 수 있는 칸은 오늘 **조도뿐**이다. 무드·컬러 이름·무브먼트·
이펙트·전환·페이드·노트는 이 저장소에 실측된 명령 형태가 없어서, 지어내지
않고 **건너뛴 것으로 보고**한다. 사유 문자열은 새로 만들지 않고 t277 이 이미
쓰던 두 개를 그대로 쓴다:

* :data:`UNMAPPED_LOOK` — 이 큐의 변경이 콘솔 값으로 옮겨지지 않는다.
* :data:`ROLE_UNADDRESSED` — 옮길 값은 있는데 그 그룹의 콘솔 번호를 모른다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from server.design.cue_sheet_edit import section_intensity_percent
from server.looks.songcue import UNMAPPED_LOOK
from server.looks.songcue_report import ROLE_UNADDRESSED

__all__ = [
    "ROLE_UNADDRESSED",
    "UNMAPPED_LOOK",
    "ConsoleApplyError",
    "ConsoleApplyPlan",
    "CueSkip",
    "changed_cue_numbers",
    "plan_console_apply",
]

_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"

#: 콘솔 값으로 옮길 수 있는 칸. 이 표 밖의 변경은 `UNMAPPED_LOOK` 로 보고된다.
CONSOLE_APPLIABLE_FIELDS: tuple[str, ...] = ("intensity", "d_level")


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
class ConsoleApplyPlan:
    sequence_number: int
    commands: tuple[str, ...] = ()
    applied: tuple[int, ...] = ()
    skipped: tuple[CueSkip, ...] = ()
    #: 큐별 조도 목표값 — 미리보기 문구가 「무엇이 나가는지」를 적을 때 쓴다.
    targets: Mapping[int, int] = field(default_factory=dict)

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
    names = section.get("fixture_groups")
    names = [str(name).strip() for name in names] if isinstance(names, list) else []
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

    before = _by_cue(baseline)
    sections = _by_cue(current)
    commands: list[str] = []
    applied: list[int] = []
    skipped: list[CueSkip] = []
    targets: dict[int, int] = {}
    for cue in changed:
        section = sections[cue]
        label = str(section.get("label") or f"Cue {cue}")
        if not _intensity_changed(before.get(cue), section):
            skipped.append(
                CueSkip(
                    cue_number=cue,
                    label=label,
                    reason=UNMAPPED_LOOK,
                    detail=(
                        "이 큐의 수정은 콘솔 값으로 옮길 수 있는 칸이 아닙니다 "
                        "(조도만 콘솔로 나갑니다). 초안과 저장본에는 남아 있습니다."
                    ),
                )
            )
            continue
        numbers, unresolved = _group_numbers(section, layer_mapping)
        if not numbers:
            skipped.append(
                CueSkip(
                    cue_number=cue,
                    label=label,
                    reason=ROLE_UNADDRESSED,
                    detail=("콘솔 그룹 번호를 모르는 대상입니다: " + ", ".join(unresolved)),
                )
            )
            continue
        percent = section_intensity_percent(section)
        targets[cue] = percent
        selection = "Group " + " + ".join(str(number) for number in numbers)
        commands.extend(
            (
                _CLEAR,
                f"{selection} ; Attribute 'Dimmer' At {percent:g}",
                f"Store Sequence {sequence_number} Cue {cue} /Merge",
                _CLEAR,
            )
        )
        applied.append(cue)
        if unresolved:
            # 일부만 주소가 잡힌 큐도 **나간 것과 안 나간 것을 같이** 말한다.
            skipped.append(
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
    return ConsoleApplyPlan(
        sequence_number=sequence_number,
        commands=((_DESTINATION, *commands) if commands else ()),
        applied=tuple(applied),
        skipped=tuple(skipped),
        targets=targets,
    )
