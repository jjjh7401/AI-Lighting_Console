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

## 큐별 판정은 반영에게 물어본다 (t304)

t303 은 큐별 판정을 위해 이름 사다리를 **다시 구현했다**. 그래서 대답할 수 있는
질문이 「이 큐에 주소가 있는가」로 좁았고, 주소는 있는데 반영이 다른 사유로
건너뛰는 큐(팔레트 범례에 없는 컬러, 일부만 잡힌 주소)를 「반영 가능」으로
세었다 — 쇼 전에 돌리는 점검이 **낙관 방향으로 틀리는** 모양이다.

이제 판정을 지어내지 않고 반영의 큐별 계획 함수
(:func:`~server.design.cue_sheet_apply.plan_cue_console_apply`)를 그대로 부른다.
두 판정이 같다는 것이 주장이 아니라 **같은 코드**이므로, 「점검은 통과했는데
반영은 건너뛴다」가 구조적으로 생기지 않는다. 건너뜀 사유도 번역하지 않고
반영이 쓴 문장을 그대로 싣는다.

시퀀스 번호는 **판정에 쓰이지 않는다**. 번호는 반영이 ``Store Sequence N Cue M``
을 지을 때에만 필요하고, 그래서 이 점검은 번호가 없어도 큐별 판정을 낸다 —
없는 번호를 지어내지 않는다.

## 콘솔 왕복

주소록 읽기(``DataPool/Groups``) 한 번은 t303 그대로다. 여기에 t304 가
**슬롯 점유**를 더한다: 시퀀스 번호가 선언돼 있으면 그 슬롯을, 타임코드 번호가
선언돼 있으면 그 슬롯을 각각 한 번씩 더 읽는다. 번호가 없으면 읽지 않고
「번호가 없어 재지 않았다」고 적는다 — 슬롯을 짐작하지 않는다.

이 모듈은 아무것도 실행하지 않는다. 콘솔 쓰기 명령을 **한 줄도 만들지 않는다** —
반환하는 것은 판정 하나뿐이다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.design.cue_sheet_apply import (
    CueSkip,
    _section_group_names,
    _sections,
    layer_mapping_from_console_groups,
    palette_index,
    plan_cue_console_apply,
    timeline_group_names,
)
from server.looks.songcue_report import ROLE_UNADDRESSED

__all__ = [
    "ROLE_UNADDRESSED",
    "SLOT_LABELS",
    "UNMEASURED_NOTES",
    "CuePreflight",
    "RigPreflight",
    "console_group_names",
    "plan_rig_preflight",
    "render_rig_preflight",
]

#: 슬롯 판정 세 갈래를 감독의 말로. ``unreadable`` 을 「비었다」로 접지 않는다 —
#: 재지 못한 것과 재서 비어 있는 것은 감독이 해야 할 행동이 다르다.
SLOT_LABELS: dict[str, str] = {
    "empty": "비어 있습니다",
    "occupied": "이미 내용이 있습니다 — 반영은 그 위에 겹쳐 씁니다",
    "unreadable": "읽지 못했습니다 (재지 못한 것을 「비었다」로 적지 않습니다)",
}

#: 이 점검이 **재지 않은 것**. 감독이 「점검했으니 다 봤겠지」라고 읽지 않도록
#: 보고서 끝에 그대로 실린다. 각 항목마다 왜 안 쟀는지가 붙는다.
UNMEASURED_NOTES: tuple[str, ...] = (
    "그룹 **멤버십**(어느 픽스처가 들어 있는가)은 이 통로로 읽히지 않습니다 — "
    "이름이 맞아도 그 그룹의 내용까지 맞는지는 이 점검이 답하지 못합니다.",
    "슬롯이 「비어 있다」는 것은 그 번호에 객체가 없다는 뜻일 뿐입니다 — 다른 곡이 "
    "그 자리를 쓰기로 돼 있는지까지는 이 점검이 답하지 못합니다.",
    "이 점검은 곡 전체를 지금 반영하면 무엇이 나가는지를 잽니다 — 감독이 초안에서 "
    "일부 큐만 고쳤다면 실제 반영은 그 큐들만 보냅니다(더 적게 나갑니다).",
)


@dataclass(frozen=True)
class CuePreflight:
    """큐 하나의 판정 — **반영이 낸 것 그대로**.

    ``would_apply`` 도 ``skips`` 도 :func:`plan_cue_console_apply` 가 돌려준
    값이다. 이 클래스는 그것을 감싸기만 하고 다시 판정하지 않는다.
    """

    cue_number: int
    label: str
    group_names: tuple[str, ...]
    would_apply: bool
    #: 반영이 이 큐를 내보낼 때의 한 줄(「조도 90% · 컬러 P2 …」). 안 나가면 빈 문자열.
    summary: str = ""
    #: 반영이 적은 건너뜀 기록 그대로. **나가는 큐에도 붙는다**(부분 성공).
    skips: tuple[CueSkip, ...] = ()

    @property
    def reason(self) -> str:
        """첫 건너뜀 사유 코드. 나가고 아무 유보도 없으면 빈 문자열."""
        return self.skips[0].reason if self.skips else ""


@dataclass(frozen=True)
class RigPreflight:
    """점검 결과 전부. 「닿았는가」와 「맞았는가」가 **다른 칸**이다."""

    console_reachable: bool
    #: 못 닿았을 때의 사유(그대로 감독에게 나간다). 닿았으면 빈 문자열.
    unreachable_detail: str = ""
    song_title: str = ""
    sequence_number: int | None = None
    #: 시퀀스 슬롯 판정 — ``empty``/``occupied``/``unreadable``, 빈 문자열이면 재지 않음.
    sequence_slot: str = ""
    timecode_number: int | None = None
    timecode_slot: str = ""
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

    @property
    def partial_cues(self) -> tuple[CuePreflight, ...]:
        """나가긴 하는데 **일부를 못 싣는** 큐들. t303 이 못 보던 자리다."""
        return tuple(cue for cue in self.cues if cue.would_apply and cue.skips)


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
    sequence_slot: str = "",
    timecode_slot: str = "",
) -> RigPreflight:
    """타임라인이 필요로 하는 이름과 콘솔이 답한 이름을 대조한다.

    ``console_error`` 가 있으면 **대조를 시작하지 않는다** — 닿지 못한 상태에서
    「일치 0」을 적으면 리그 이름 불일치와 구별되지 않기 때문이다.

    대조 규칙도 큐별 판정도 반영과 **같은 함수**를 쓴다
    (:func:`~server.design.cue_sheet_apply.layer_mapping_from_console_groups`
    와 :func:`~server.design.cue_sheet_apply.plan_cue_console_apply`).
    점검이 통과했는데 반영이 건너뛰는 일이 없으려면 두 판정이 같은 술어여야
    한다 — 여기에 두 번째 판정 규칙을 만들지 않는다.

    ``sequence_slot`` / ``timecode_slot`` 은 호출자가 콘솔에서 읽어 온 슬롯
    판정이다(``empty``/``occupied``/``unreadable``). 이 순수 함수는 콘솔을 보지
    않으므로, 안 넘어오면 「재지 않음」으로 남는다 — 짐작하지 않는다.
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

    timecode_number = timeline.get("timecode_number")
    if not isinstance(timecode_number, int) or isinstance(timecode_number, bool):
        timecode_number = None

    resolved = layer_mapping_from_console_groups(console_payload, names)
    index = {str(entry["group_name"]).strip().casefold() for entry in resolved}
    unresolved = tuple(name for name in names if name.strip().casefold() not in index)
    return RigPreflight(
        console_reachable=True,
        song_title=song_title,
        sequence_number=sequence_number,
        sequence_slot=sequence_slot if sequence_number is not None else "",
        timecode_number=timecode_number,
        timecode_slot=timecode_slot if timecode_number is not None else "",
        console_names=console_group_names(console_payload),
        timeline_names=names,
        resolved=tuple(resolved),
        unresolved=unresolved,
        cues=_cue_verdicts(timeline, resolved),
    )


def _cue_verdicts(
    timeline: Mapping[str, object], layer_mapping: Sequence[Mapping[str, object]]
) -> tuple[CuePreflight, ...]:
    """큐마다 「반영하면 이 큐가 나가는가」 — 판정은 **반영이 낸다**.

    호출은 ``previous=None`` 이다: 「곡 전체를 지금 반영하면 무엇이 닿는가」가
    쇼 전에 묻는 질문이고, 반영에서 ``previous`` 가 없다는 것은 곧 「이 큐는
    통째로 새로 나간다」다. 감독이 초안에서 일부만 고쳤다면 실제 반영은 그
    큐들만 보내므로 이 점검은 **더 많이** 세는 쪽이고, 낙관 방향으로 틀리지
    않는다.
    """
    verdicts: list[CuePreflight] = []
    colors = palette_index(timeline)
    for section in _sections(timeline):
        cue = section.get("cue_number")
        if not isinstance(cue, int):
            continue
        decision = plan_cue_console_apply(section, None, layer_mapping, colors)
        verdicts.append(
            CuePreflight(
                cue_number=decision.cue_number,
                label=decision.label,
                group_names=tuple(_section_group_names(section)),
                would_apply=decision.would_apply,
                summary=decision.summary,
                skips=decision.skips,
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
    partial = report.partial_cues
    lines.append(
        f"· 큐 {len(report.cues)}개 중 반영 가능 {len(report.appliable_cues)}건"
        + (f"(그중 일부만 나가는 큐 {len(partial)}건)" if partial else "")
        + f", 건너뜀 {len(skipped)}건."
    )
    # 사유는 반영이 쓴 문장 그대로다 — 여기서 다시 쓰지 않는다(t304).
    for cue in skipped:
        for skip in cue.skips:
            lines.append(f"  · 큐 {cue.cue_number}({cue.label}) [{skip.reason}] — {skip.detail}")
    for cue in partial:
        lines.append(f"  · 큐 {cue.cue_number}({cue.label}) 나가는 것: {cue.summary}")
        for skip in cue.skips:
            lines.append(f"    · 못 나가는 것 [{skip.reason}] — {skip.detail}")

    lines.append(_slot_line("시퀀스", report.sequence_number, report.sequence_slot))
    lines.append(_slot_line("타임코드", report.timecode_number, report.timecode_slot))

    if report.console_names:
        lines.append(f"· 콘솔이 보고한 그룹 이름: {', '.join(report.console_names)}")
    for note in UNMEASURED_NOTES:
        lines.append(f"· (재지 않음) {note}")
    lines.append("이 점검은 읽기 전용입니다 — 콘솔에는 아무것도 쓰지 않았습니다.")
    return "\n".join(lines)


def _slot_line(kind: str, number: int | None, state: str) -> str:
    """슬롯 한 칸의 보고. 번호가 없으면 **재지 않았다고 적는다** — 짐작하지 않는다."""
    if number is None:
        return f"· {kind} 슬롯: 이 타임라인에 {kind} 번호가 없어 재지 않았습니다."
    if not state:
        return f"· {kind} {number}번 슬롯: 재지 않았습니다."
    return f"· {kind} {number}번 슬롯: {SLOT_LABELS.get(state, state)}."
