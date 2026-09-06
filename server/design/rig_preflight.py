"""쇼 전에 한 번 돌리는 **읽기 전용** 리그 점검 (t303).

## 이 파일이 있는 이유

반영(`server/design/cue_sheet_apply.py`)은 콘솔이 **스스로 보고한 그룹 이름**과
타임라인이 적어 둔 이름이 완전 일치할 때만 명령을 만든다(t294). 그룹 멤버십은
이 통로로 읽히지 않으므로 짐작이 금지돼 있고, 그래서 이름이 안 맞으면 그 큐는
``ROLE_UNADDRESSED`` 로 조용히 건너뛴다.

t302 실측: 가짜 리그의 원래 이름으로는 **모든 큐**가 그 사유로 건너뛰어져
콘솔로 0건이 나갔다. 감독 입장에서 이 실패는 최악의 모양이다 — 곡 한 곡을
통째로 반영하라고 시켰는데 아무 일도 일어나지 않는다. 그것을 **쇼 중이 아니라
쇼 전에** 알자는 것이 이 모듈이다.

## 두 상태를 절대 섞지 않는다

「콘솔에 닿지 못했다」와 「닿았는데 이름이 하나도 안 맞았다」는 감독이 해야 할
행동이 정반대다(데스크를 켜라 vs 그룹 이름을 고쳐라). 그런데 둘 다 「일치 0」으로
보이기 쉽다. 그래서 :class:`RigPreflight` 는 ``console_reachable`` 를 별도의
칸으로 들고, 닿지 못한 경우에는 일치 수를 **아예 주장하지 않는다** —
재지 못한 것을 0 으로 적지 않는다.

## 콘솔 왕복은 한 번뿐

읽는 것은 주소록이 이미 읽는 ``DataPool/Groups`` 하나다. 시퀀스 슬롯 점유·
타임코드 슬롯 여부는 **재지 않는다** — 그 답에는 또 다른 왕복이 필요하고,
이 모듈은 그 값을 추측하는 대신 「재지 않았다」고 적는다
(:data:`UNMEASURED_NOTES`).

이 모듈은 아무것도 실행하지 않는다. 콘솔 쓰기 명령을 **한 줄도 만들지 않는다** —
반환하는 것은 판정 하나뿐이다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from server.design.cue_sheet_apply import (
    _section_group_names,
    _sections,
    layer_mapping_from_console_groups,
    timeline_group_names,
)
from server.looks.songcue_report import ROLE_UNADDRESSED

__all__ = [
    "ROLE_UNADDRESSED",
    "UNMEASURED_NOTES",
    "CuePreflight",
    "RigPreflight",
    "console_group_names",
    "plan_rig_preflight",
    "render_rig_preflight",
]

#: 이 점검이 **재지 않은 것**. 감독이 「점검했으니 다 봤겠지」라고 읽지 않도록
#: 보고서 끝에 그대로 실린다. 각 항목마다 왜 안 쟀는지가 붙는다.
UNMEASURED_NOTES: tuple[str, ...] = (
    "그룹 **멤버십**(어느 픽스처가 들어 있는가)은 이 통로로 읽히지 않습니다 — "
    "이름이 맞아도 그 그룹의 내용까지 맞는지는 이 점검이 답하지 못합니다.",
    "시퀀스 슬롯 점유·타임코드 슬롯 여부는 재지 않았습니다 — 콘솔 왕복이 "
    "한 번 더 필요하고, 이 점검은 읽기 한 번으로 끝내기로 했습니다.",
)


@dataclass(frozen=True)
class CuePreflight:
    """큐 하나의 판정. ``reason`` 은 못 나가는 큐에만 붙는다."""

    cue_number: int
    label: str
    group_names: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def would_apply(self) -> bool:
        return not self.unresolved

    @property
    def reason(self) -> str:
        return "" if self.would_apply else ROLE_UNADDRESSED


@dataclass(frozen=True)
class RigPreflight:
    """점검 결과 전부. 「닿았는가」와 「맞았는가」가 **다른 칸**이다."""

    console_reachable: bool
    #: 못 닿았을 때의 사유(그대로 감독에게 나간다). 닿았으면 빈 문자열.
    unreachable_detail: str = ""
    song_title: str = ""
    sequence_number: int | None = None
    #: 콘솔이 보고한 그룹 이름 전부(못 닿았으면 빈 튜플 — 0 이라고 주장하지 않는다).
    console_names: tuple[str, ...] = ()
    #: 타임라인이 주소를 필요로 하는 이름들(등장 순서).
    timeline_names: tuple[str, ...] = ()
    #: ``{"group_name": …, "group_no": …}`` — 반영이 쓰는 주소록과 같은 모양.
    resolved: tuple[Mapping[str, object], ...] = ()
    unresolved: tuple[str, ...] = ()
    cues: tuple[CuePreflight, ...] = ()

    @property
    def appliable_cues(self) -> tuple[CuePreflight, ...]:
        return tuple(cue for cue in self.cues if cue.would_apply)

    @property
    def skipped_cues(self) -> tuple[CuePreflight, ...]:
        return tuple(cue for cue in self.cues if not cue.would_apply)


def console_group_names(payload: object) -> tuple[str, ...]:
    """콘솔이 답한 ``DataPool/Groups`` 에서 **이름만** 뽑는다 (등장 순서).

    번호가 없는 항목도 이름은 센다 — 감독이 「콘솔에는 이런 이름들이 있다」를
    읽을 수 있어야 무엇을 고쳐야 할지 안다.
    """
    if not isinstance(payload, Mapping):
        return ()
    children = payload.get("children")
    if not isinstance(children, list):
        return ()
    names: list[str] = []
    for child in children:
        if not isinstance(child, Mapping):
            continue
        name = str(child.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return tuple(names)


def plan_rig_preflight(
    timeline: Mapping[str, object] | None,
    *,
    console_payload: object = None,
    console_error: str | None = None,
) -> RigPreflight:
    """타임라인이 필요로 하는 이름과 콘솔이 답한 이름을 대조한다.

    ``console_error`` 가 있으면 **대조를 시작하지 않는다** — 닿지 못한 상태에서
    「일치 0」을 적으면 리그 이름 불일치와 구별되지 않기 때문이다.

    대조 규칙은 반영과 **같은 함수**를 쓴다
    (:func:`~server.design.cue_sheet_apply.layer_mapping_from_console_groups`).
    점검이 통과했는데 반영이 건너뛰는 일이 없으려면 두 판정이 같은 술어여야
    한다 — 여기에 두 번째 대조 규칙을 만들지 않는다.
    """
    timeline = timeline if isinstance(timeline, Mapping) else {}
    song_title = str(timeline.get("song_title") or "").strip()
    # 0 은 「번호가 없다」는 뜻이다(시드 타임라인이 그렇게 실려 온다) — 「Sequence 0」
    # 이라고 적으면 감독이 0번 슬롯을 쓴다고 읽는다. 실측: 브라우저 1회차 보고가
    # 「(Sequence 0)」을 달고 나왔다.
    sequence_number = timeline.get("sequence_number")
    if not isinstance(sequence_number, int) or sequence_number < 1:
        sequence_number = None
    names = timeline_group_names(timeline)

    if console_error is not None:
        return RigPreflight(
            console_reachable=False,
            unreachable_detail=console_error,
            song_title=song_title,
            sequence_number=sequence_number,
            timeline_names=names,
        )

    resolved = layer_mapping_from_console_groups(console_payload, names)
    index = {str(entry["group_name"]).strip().casefold() for entry in resolved}
    unresolved = tuple(name for name in names if name.strip().casefold() not in index)
    return RigPreflight(
        console_reachable=True,
        song_title=song_title,
        sequence_number=sequence_number,
        console_names=console_group_names(console_payload),
        timeline_names=names,
        resolved=tuple(resolved),
        unresolved=unresolved,
        cues=_cue_verdicts(timeline, index),
    )


def _cue_verdicts(timeline: Mapping[str, object], index: set[str]) -> tuple[CuePreflight, ...]:
    """큐마다 「이 큐의 그룹 이름이 전부 풀리는가」.

    이름 사다리는 반영과 같다(``fixture_groups`` → ``intensity[].group`` →
    리터럴 ``ALL``). ``ALL`` 은 **주소록에 적힌 것 전부**로 풀리므로, 주소록이
    비면 그 큐도 못 나간다 — 반영의 ``_group_numbers`` 와 같은 판정이다.
    """
    verdicts: list[CuePreflight] = []
    for section in _sections(timeline):
        cue = section.get("cue_number")
        if not isinstance(cue, int):
            continue
        group_names = tuple(_section_group_names(section))
        unresolved: list[str] = []
        for name in group_names:
            if name.casefold() == "all":
                if not index:
                    unresolved.append(name)
                continue
            if name.strip().casefold() not in index:
                unresolved.append(name)
        verdicts.append(
            CuePreflight(
                cue_number=cue,
                label=str(section.get("label") or f"Cue {cue}"),
                group_names=group_names,
                unresolved=tuple(unresolved),
            )
        )
    return tuple(verdicts)


def render_rig_preflight(report: RigPreflight) -> str:
    """감독이 읽는 한 덩어리 보고. **명령 문자열은 한 줄도 담기지 않는다.**"""
    if not report.console_reachable:
        # 「일치 0」이라고 절대 쓰지 않는다 — 재지 못한 것과 재서 0인 것은
        # 감독이 해야 할 행동이 정반대다(데스크를 켜라 vs 이름을 고쳐라).
        return (
            "리그 사전 점검을 하지 못했습니다 — **콘솔에 닿지 못했습니다** "
            f"(DataPool/Groups 읽기 실패: {report.unreachable_detail}).\n"
            "이것은 「이름이 하나도 안 맞았다」가 아닙니다: 콘솔이 답을 주지 "
            "않아 대조를 시작조차 하지 못했습니다 — 일치 수는 재지 않았습니다.\n"
            "데스크와 응답기(플러그인)가 켜져 있는지 확인한 뒤 다시 요청해 "
            "주세요. 콘솔에는 아무것도 쓰지 않았습니다."
        )

    title = report.song_title or "이름 없는 곡"
    head = f"리그 사전 점검 — 「{title}」"
    if report.sequence_number is not None:
        head += f" (Sequence {report.sequence_number})"
    lines = [head + f". 콘솔 그룹 이름 {len(report.console_names)}개를 읽었습니다."]

    if report.resolved:
        found = ", ".join(
            f"{entry['group_name']}=Group {entry['group_no']}" for entry in report.resolved
        )
        lines.append(f"· 주소를 잡은 대상 {len(report.resolved)}: {found}")
    if report.unresolved:
        lines.append(
            f"· 콘솔에 같은 이름의 그룹이 없어 주소를 못 잡은 대상 "
            f"{len(report.unresolved)}: {', '.join(report.unresolved)} "
            "(이름을 지어내지 않습니다 — 콘솔의 그룹 이름을 타임라인과 같게 "
            "고치거나, 타임라인의 이름을 콘솔에 맞춰 주세요.)"
        )
    if not report.timeline_names:
        lines.append("· 이 타임라인은 그룹 이름을 지목하지 않습니다(ALL 만 씁니다).")

    skipped = report.skipped_cues
    lines.append(
        f"· 큐 {len(report.cues)}개 중 반영 가능 {len(report.appliable_cues)}건, "
        f"건너뜀 {len(skipped)}건."
    )
    for cue in skipped:
        lines.append(
            f"  · 큐 {cue.cue_number}({cue.label}) [{cue.reason}] — "
            f"주소 없음: {', '.join(cue.unresolved)}"
        )
    if report.console_names:
        lines.append(f"· 콘솔이 보고한 그룹 이름: {', '.join(report.console_names)}")
    for note in UNMEASURED_NOTES:
        lines.append(f"· (재지 않음) {note}")
    lines.append("이 점검은 읽기 1회뿐입니다 — 콘솔에는 아무것도 쓰지 않았습니다.")
    return "\n".join(lines)
