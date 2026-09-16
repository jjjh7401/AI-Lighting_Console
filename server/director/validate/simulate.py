"""축별 상태 simulation 과 ready 판정 (SPEC-LDCOMPILE-001 C3, REQ-LDPLUGIN-010).

계약 §8 의 세 조항을 구현한다.

- `LD-STATE-001` — **누락은 hold 다.** 쓰지 않은 축은 앞서 선언된 값을 유지하며, 선언된 적이
  없으면 `None` 으로 남는다. group 의 `safe_state` 를 상속하지 않는다: 상속하면 baseline
  누락이 진단 없이 사라지고, 그것이 *"이전 show/programmer state 를 상속하지 않는다"* 가
  막는 실패다.
- `LD-STATE-002` — simulation 결과와 `terminal_state` 가 **정확히 일치**해야 한다. 축 하나만
  달라도 blocking (감독 판정 2026-09-16: 계약 문면대로).
- `LD-FX-001` — `instance_id` 는 **plan 전체에서** 한 start 와 한 stop 에 1:1.

[HARD] **예술 정책을 주입하지 않는다.** `section_id` 를 보지 않으며, 강도의 높낮이·반복
자체를 결함으로 보지 않는다. 조용한 엔딩·동일 후렴 강도·반복 motif 는 통과해야 한다
(`LD-STATE-002` 가 유효하다고 명시). 이 모듈이 무엇을 보지 않는지가 무엇을 보는지만큼
중요하다.

[HARD] 콘솔 무접촉 · OSC 무접촉 — dict 만 다룬다.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from server.director.validate.diagnostics import (
    STATUS_ACCEPTED,
    STATUS_CONFLICT,
    STATUS_UNRESOLVED,
    Diagnostic,
    absent,
    present,
)

STAGE = "tracking_fx"

#: 전체 plan 을 가리키는 pointer (계약 §6.3).
ROOT_POINTER = ""

#: 상태 슬롯 넷. 첫 cue 가 controlled group 전부에 대해 이 넷을 채워야 한다.
#: pan·tilt 는 `position_set` 하나가 함께 움직이므로 상태 슬롯은 `position_ref` 하나다
#: (축이 둘로 갈리는 것은 예약 구간을 다루는 `conflict.py` 의 관심사다).
BASELINE_OPS: tuple[str, ...] = ("intensity_set", "color_set", "position_set", "beam_set")

#: op → 상태 슬롯 이름.
_OP_SLOT = {
    "intensity_set": "intensity_pct",
    "color_set": "color_ref",
    "position_set": "position_ref",
    "beam_set": "beam_ref",
}

OWNERSHIP_HELD = "held"
OWNERSHIP_RELEASED = "released"


@dataclass(frozen=True, slots=True)
class GroupState:
    """한 group 의 축별 상태. `None` 은 **한 번도 선언되지 않았다**는 뜻이다.

    `None` 을 `safe_state` 로 채우지 않는 것이 이 자료형의 요점이다 — 모르는 값을 채우면
    baseline 누락이 조용히 사라진다.
    """

    intensity_pct: float | int | None = None
    color_ref: str | None = None
    position_ref: str | None = None
    beam_ref: str | None = None
    active_fx: tuple[str, ...] = ()
    ownership: str = OWNERSHIP_HELD

    def as_terminal(self) -> dict[str, Any]:
        """`terminal_state[].state` 와 같은 형태로 낸다 — 대조를 한 자리에서 한다."""
        return {
            "intensity_pct": self.intensity_pct,
            "color_ref": self.color_ref,
            "position_ref": self.position_ref,
            "beam_ref": self.beam_ref,
            "active_fx": list(self.active_fx),
            "ownership": self.ownership,
        }


@dataclass(frozen=True, slots=True)
class ActionRef:
    """action 하나의 위치와 시각. 진단의 pointer 가 여기서 나온다."""

    cue_index: int
    action_index: int
    at_ms: int
    action: dict[str, Any]

    @property
    def pointer(self) -> str:
        return f"/cues/{self.cue_index}/actions/{self.action_index}"

    @property
    def op(self) -> str:
        return str(self.action.get("op", ""))

    @property
    def group_id(self) -> str:
        return str(self.action.get("group_id", ""))


def _cue_order(plan: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    """cue 를 **시각 순**으로 낸다 (동시각은 배열 순).

    배열 순을 그대로 쓰지 않는 이유: simulation 은 시간의 함수이며, 배열이 정렬되어 있다는
    보장은 이 층의 입력에 없다. 시각 순서가 곧 상태 전이 순서다.
    """
    cues = plan.get("cues") or []
    indexed = [(i, c) for i, c in enumerate(cues) if isinstance(c, dict)]
    return sorted(indexed, key=lambda pair: (int(pair[1].get("at_ms", 0)), pair[0]))


def action_refs(plan: dict[str, Any]) -> list[ActionRef]:
    """모든 action 을 시각 순으로 낸다."""
    refs: list[ActionRef] = []
    for cue_index, cue in _cue_order(plan):
        at_ms = int(cue.get("at_ms", 0))
        for action_index, action in enumerate(cue.get("actions") or []):
            if isinstance(action, dict):
                refs.append(ActionRef(cue_index, action_index, at_ms, action))
    return refs


def controlled_groups(plan: dict[str, Any]) -> list[str]:
    return [str(g) for g in plan.get("controlled_group_ids") or []]


def simulate(plan: dict[str, Any]) -> dict[str, GroupState]:
    """계획을 시각 순으로 적용해 group 별 최종 상태를 낸다.

    쓰지 않은 축은 그대로 유지된다(hold). 이것이 `LD-STATE-001` 의 *"누락 action/axis 는
    hold"* 이며, 초기값이 `None` 이라는 사실이 *"상속하지 않는다"* 를 집행한다.
    """
    states: dict[str, GroupState] = {group: GroupState() for group in controlled_groups(plan)}

    for ref in action_refs(plan):
        group = ref.group_id
        if not group:
            continue
        state = states.get(group, GroupState())
        op = ref.op

        if op in _OP_SLOT:
            value = (
                ref.action.get("value_pct")
                if op == "intensity_set"
                else ref.action.get("preset_ref")
            )
            # 쓰면 다시 소유한다 — release 뒤 재진입은 ownership 을 held 로 되돌린다.
            # 부분 재진입은 `_check_release_reentry` 가 별도로 막으므로, 여기서 「완전한
            # baseline 인지」를 다시 판정하지 않는다.
            state = replace(state, ownership=OWNERSHIP_HELD, **{_OP_SLOT[op]: value})
        elif op == "fx_start":
            instance = str(ref.action.get("instance_id", ""))
            if instance not in state.active_fx:
                state = replace(state, active_fx=(*state.active_fx, instance))
        elif op == "fx_stop":
            instance = str(ref.action.get("instance_id", ""))
            state = replace(state, active_fx=tuple(i for i in state.active_fx if i != instance))
        elif op == "group_release":
            state = replace(state, ownership=OWNERSHIP_RELEASED)

        states[group] = state

    return states


# --------------------------------------------------------------------------- #
# `LD-STATE-001` — 첫 cue 의 완전한 baseline
# --------------------------------------------------------------------------- #


def _baseline_ops_in_cue(cue: dict[str, Any], group: str) -> set[str]:
    return {
        str(a.get("op"))
        for a in cue.get("actions") or []
        if isinstance(a, dict) and a.get("group_id") == group and a.get("op") in BASELINE_OPS
    }


def _check_first_cue_baseline(plan: dict[str, Any]) -> list[Diagnostic]:
    order = _cue_order(plan)
    groups = controlled_groups(plan)

    if not order:
        return [
            Diagnostic(
                rule_id="LD-STATE-001",
                pointer=ROOT_POINTER,
                status=STATUS_UNRESOLVED,
                blocking=True,
                reason=(
                    "cue 가 없습니다. 계약 LD-STATE-001 은 schema-valid 빈 cue/terminal "
                    "배열을 draft 에서만 허용하므로 ready 판정 대상이 아닙니다."
                ),
                stage=STAGE,
            )
        ]

    first_index, first_cue = order[0]
    diagnostics: list[Diagnostic] = []

    for group in groups:
        missing = sorted(set(BASELINE_OPS) - _baseline_ops_in_cue(first_cue, group))
        if missing:
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-STATE-001",
                    pointer=f"/cues/{first_index}",
                    status=STATUS_UNRESOLVED,
                    blocking=True,
                    reason=(
                        f"첫 cue 가 controlled group {group} 의 baseline 을 완전히 지정하지 "
                        f"않았습니다 — 누락: {', '.join(missing)}. 계약 LD-STATE-001 은 첫 "
                        "cue 가 intensity/color/position/beam 전부를 지정하도록 규정하며, "
                        "누락된 축은 이전 show·programmer 값으로 상속되지 않습니다. "
                        "뒤 cue 로 미루면 그 사이 구간이 미지 상태로 남습니다."
                    ),
                    stage=STAGE,
                    before=absent(),
                    after=absent(),
                )
            )

    started_in_first = [
        a
        for a in first_cue.get("actions") or []
        if isinstance(a, dict) and a.get("op") == "fx_start"
    ]
    if started_in_first:
        instances = ", ".join(str(a.get("instance_id")) for a in started_in_first)
        diagnostics.append(
            Diagnostic(
                rule_id="LD-STATE-001",
                pointer=f"/cues/{first_index}",
                status=STATUS_CONFLICT,
                blocking=True,
                reason=(
                    f"첫 cue 가 FX 를 시작합니다 ({instances}). 계약 LD-STATE-001 은 첫 cue 에서 "
                    "active FX 없음이 확인되어야 한다고 규정합니다 — baseline cue 는 clean "
                    "상태를 선언하는 자리이므로 그 안에서 FX 를 켜면 무엇이 기준값인지 "
                    "판정할 수 없습니다. FX 는 다음 cue 에서 시작하십시오."
                ),
                stage=STAGE,
            )
        )

    return diagnostics


def _check_release_reentry(plan: dict[str, Any]) -> list[Diagnostic]:
    """release 이후 부분 재진입을 막는다 (`AC-LDPLUGIN-010` 6번).

    release 는 제어를 놓는 것이므로 그 뒤의 상태는 이 계획이 아는 값이 아니다. 다시 쓰려면
    완전한 baseline 을 새로 선언해야 한다 — 부분 선언은 놓기 전 값을 상속하는 것과 같다.
    """
    released: set[str] = set()
    diagnostics: list[Diagnostic] = []

    for cue_index, cue in _cue_order(plan):
        actions = [a for a in cue.get("actions") or [] if isinstance(a, dict)]
        touched = {
            str(a.get("group_id"))
            for a in actions
            if a.get("op") != "group_release" and a.get("group_id")
        }
        for group in sorted(touched & released):
            missing = sorted(set(BASELINE_OPS) - _baseline_ops_in_cue(cue, group))
            if missing:
                diagnostics.append(
                    Diagnostic(
                        rule_id="LD-STATE-001",
                        pointer=f"/cues/{cue_index}",
                        status=STATUS_UNRESOLVED,
                        blocking=True,
                        reason=(
                            f"group {group} 은 앞서 release 되었는데 이 cue 가 완전한 baseline "
                            f"없이 다시 씁니다 — 누락: {', '.join(missing)}. release 이후의 "
                            "상태는 이 계획이 아는 값이 아니므로 부분 재진입은 놓기 전 값을 "
                            "상속하는 것과 같습니다 (계약 LD-STATE-001)."
                        ),
                        stage=STAGE,
                    )
                )
            else:
                released.discard(group)

        for action in actions:
            if action.get("op") == "group_release":
                released.add(str(action.get("group_id")))

    return diagnostics


# --------------------------------------------------------------------------- #
# `LD-FX-001` — instance 생애
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class _Instance:
    starts: list[ActionRef] = field(default_factory=list)
    stops: list[ActionRef] = field(default_factory=list)


def fx_instances(plan: dict[str, Any]) -> dict[str, _Instance]:
    """`instance_id` → start/stop 목록. plan 전체가 범위다 (group 별이 아니다)."""
    instances: dict[str, _Instance] = {}
    for ref in action_refs(plan):
        if ref.op not in ("fx_start", "fx_stop"):
            continue
        instance = str(ref.action.get("instance_id", ""))
        entry = instances.setdefault(instance, _Instance())
        (entry.starts if ref.op == "fx_start" else entry.stops).append(ref)
    return instances


def _fx_diagnostic(instance: str, pointer: str, reason: str) -> Diagnostic:
    return Diagnostic(
        rule_id="LD-FX-001",
        pointer=pointer,
        status=STATUS_CONFLICT,
        blocking=True,
        reason=reason,
        stage=STAGE,
        after=present(instance),
    )


def _check_fx_lifecycle(plan: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for instance, entry in sorted(fx_instances(plan).items()):
        if len(entry.starts) > 1:
            diagnostics.append(
                _fx_diagnostic(
                    instance,
                    entry.starts[1].pointer,
                    f"instance_id {instance} 가 {len(entry.starts)} 번 start 됩니다. 계약 "
                    "LD-FX-001 은 instance_id 를 plan 전체에서 한 start 에 1:1 로 묶습니다 — "
                    "group 별 유일이 아니라 계획 전체에서 유일합니다.",
                )
            )
        if len(entry.stops) > 1:
            diagnostics.append(
                _fx_diagnostic(
                    instance,
                    entry.stops[1].pointer,
                    f"instance_id {instance} 가 {len(entry.stops)} 번 stop 됩니다. 계약 "
                    "LD-FX-001 은 한 stop 만 허용합니다.",
                )
            )
        if not entry.starts:
            diagnostics.append(
                _fx_diagnostic(
                    instance,
                    entry.stops[0].pointer,
                    f"instance_id {instance} 가 start 없이 stop 됩니다. 무엇을 멈추는지 "
                    "계획 안에서 해소되지 않습니다 (계약 LD-FX-001).",
                )
            )
            continue
        if not entry.stops:
            diagnostics.append(
                _fx_diagnostic(
                    instance,
                    entry.starts[0].pointer,
                    f"instance_id {instance} 에 stop 이 없습니다. 계약 LD-FX-001 은 "
                    "active_fx 의 terminal 값을 항상 빈 배열로 규정하므로, stop 없는 FX 는 "
                    "그 조건을 만족할 수 없습니다.",
                )
            )
            continue

        start, stop = entry.starts[0], entry.stops[0]
        if (stop.at_ms, stop.cue_index, stop.action_index) < (
            start.at_ms,
            start.cue_index,
            start.action_index,
        ):
            diagnostics.append(
                _fx_diagnostic(
                    instance,
                    stop.pointer,
                    f"instance_id {instance} 의 stop({stop.at_ms}ms) 이 "
                    f"start({start.at_ms}ms) 보다 앞섭니다 (계약 LD-FX-001).",
                )
            )
        if start.group_id != stop.group_id:
            diagnostics.append(
                _fx_diagnostic(
                    instance,
                    stop.pointer,
                    f"instance_id {instance} 의 start group({start.group_id}) 과 "
                    f"stop group({stop.group_id}) 이 다릅니다. group mismatch 는 blocking "
                    "입니다 (계약 LD-FX-001).",
                )
            )

    return diagnostics


# --------------------------------------------------------------------------- #
# `LD-STATE-002` — terminal 정확 일치
# --------------------------------------------------------------------------- #

_TERMINAL_SLOTS: tuple[str, ...] = (
    "intensity_pct",
    "color_ref",
    "position_ref",
    "beam_ref",
    "ownership",
)


def _check_terminal(plan: dict[str, Any], states: dict[str, GroupState]) -> list[Diagnostic]:
    groups = controlled_groups(plan)
    entries = [e for e in plan.get("terminal_state") or [] if isinstance(e, dict)]
    diagnostics: list[Diagnostic] = []

    by_group: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, entry in enumerate(entries):
        by_group.setdefault(str(entry.get("group_id")), []).append((index, entry))

    for group in groups:
        found = by_group.get(group, [])
        if not found:
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-STATE-002",
                    pointer="/terminal_state",
                    status=STATUS_UNRESOLVED,
                    blocking=True,
                    reason=(
                        f"controlled group {group} 의 terminal_state 항목이 없습니다. 계약 "
                        "LD-STATE-002 는 모든 group 의 terminal 을 요구합니다."
                    ),
                    stage=STAGE,
                )
            )
            continue
        if len(found) > 1:
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-STATE-002",
                    pointer=f"/terminal_state/{found[1][0]}",
                    status=STATUS_CONFLICT,
                    blocking=True,
                    reason=(
                        f"group {group} 의 terminal_state 항목이 {len(found)} 개입니다. "
                        "모든 controlled group 에 정확히 하나여야 합니다 "
                        "(계약 LD-STATE-002)."
                    ),
                    stage=STAGE,
                )
            )

        index, entry = found[0]
        declared = entry.get("state") if isinstance(entry.get("state"), dict) else {}
        simulated = states.get(group, GroupState()).as_terminal()

        declared_fx = declared.get("active_fx")
        if declared_fx:
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-FX-001",
                    pointer=f"/terminal_state/{index}/state/active_fx",
                    status=STATUS_CONFLICT,
                    blocking=True,
                    reason=(
                        f"group {group} 의 terminal active_fx 가 비어 있지 않습니다 "
                        f"({declared_fx}). 계약 LD-FX-001 은 terminal 값을 **항상 빈 배열** 로 "
                        "규정합니다."
                    ),
                    stage=STAGE,
                    after=absent(),
                )
            )
        if simulated["active_fx"]:
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-FX-001",
                    pointer=f"/terminal_state/{index}/state/active_fx",
                    status=STATUS_CONFLICT,
                    blocking=True,
                    reason=(
                        f"group {group} 의 simulation 이 끝나도 FX "
                        f"{simulated['active_fx']} 가 살아 있습니다. terminal active_fx 는 "
                        "항상 빈 배열이어야 하므로 stop 이 빠졌습니다 (계약 LD-FX-001)."
                    ),
                    stage=STAGE,
                )
            )

        for slot in _TERMINAL_SLOTS:
            want, got = simulated[slot], declared.get(slot)
            if want == got:
                continue
            diagnostics.append(
                Diagnostic(
                    rule_id="LD-STATE-002",
                    pointer=f"/terminal_state/{index}/state/{slot}",
                    status=STATUS_CONFLICT,
                    blocking=True,
                    reason=(
                        f"group {group} 의 {slot} 이 축별 simulation 결과와 다릅니다 — "
                        f"simulation {want!r}, 선언 {got!r}. 계약 LD-STATE-002 는 "
                        "**정확히 일치** 를 요구합니다."
                        + (
                            " simulation 값이 None 인 것은 그 축이 계획 안에서 한 번도 "
                            "선언되지 않았다는 뜻입니다 — 이전 상태를 상속하지 않습니다."
                            if want is None
                            else ""
                        )
                    ),
                    stage=STAGE,
                    before=present(want) if isinstance(want, (int, float, str)) else absent(),
                    after=present(got) if isinstance(got, (int, float, str)) else absent(),
                )
            )

    for group, found in sorted(by_group.items()):
        if group in groups:
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="LD-STATE-002",
                pointer=f"/terminal_state/{found[0][0]}",
                status=STATUS_UNRESOLVED,
                blocking=True,
                reason=(
                    f"terminal_state 가 controlled 되지 않은 group {group} 을 선언합니다. "
                    "제어하지 않는 group 의 최종 상태는 이 계획이 약속할 수 있는 것이 "
                    "아닙니다 (계약 LD-STATE-002)."
                ),
                stage=STAGE,
            )
        )

    return diagnostics


# --------------------------------------------------------------------------- #
# 진입점
# --------------------------------------------------------------------------- #


def check_ready(plan: dict[str, Any]) -> list[Diagnostic]:
    """3단의 ready 판정 — `LD-STATE-001`·`LD-STATE-002`·`LD-FX-001`.

    `context` 를 받지 않는다: 이 판정에 필요한 것은 전부 계획 안에 있고(controlled group·
    cue·terminal), group membership 은 충돌 검출의 관심사다. 안 쓰는 입력을 받으면 그것을
    본다고 오해된다.
    """
    states = simulate(plan)
    diagnostics = [
        *_check_first_cue_baseline(plan),
        *_check_release_reentry(plan),
        *_check_fx_lifecycle(plan),
        *_check_terminal(plan, states),
    ]
    if diagnostics:
        return diagnostics

    # 조용한 수용은 이 층에서 합법이 아니다 — 통과도 사유가 붙는다 (계약 §6.3).
    return [
        Diagnostic(
            rule_id="LD-STATE-002",
            pointer=ROOT_POINTER,
            status=STATUS_ACCEPTED,
            blocking=False,
            reason=(
                f"controlled group {len(controlled_groups(plan))} 개의 축별 simulation 이 "
                "선언된 terminal_state 와 정확히 일치하고, FX instance 는 전부 짝이 맞으며 "
                "terminal active_fx 는 빈 배열입니다. 강도의 높낮이·반복·구간 역할은 "
                "판정하지 않습니다 — 예술 판단은 이 층의 것이 아닙니다."
            ),
            stage=STAGE,
        )
    ]
