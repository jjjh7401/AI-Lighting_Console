"""dark move·재진입 거부 (SPEC-LDCOMPILE-001 C5, REQ-LDPLUGIN-012).

계약 §8 의 두 조항을 구현한다. 둘의 성격이 다르다.

`LD-MIB-001` — **증명 부담이 계획 쪽에 있다.** *"dark_move는 movement 시작부터 pan/tilt의
늦은 완료+settle_ms까지 intensity=0 및 intensity FX 없음이 증명되어야 한다."* 「어둡지 않다는
증거가 없다」가 통과 사유가 되면 무대에서 빔이 지나간다. 그래서 기본값이 blocking 이고,
통과에는 적극적인 증거가 필요하다.

```
        at_ms   +delay        pan/tilt 중 늦은 완료     +settle_ms
          |-------|=============================|----------|
                  [           어두워야 하는 창             )
```

창 안에서 intensity 가 0 임이 증명되려면 둘이 다 성립해야 한다.

1. 창에 **들어가는 순간의 정착값이 0** 이어야 한다. 정착값은 창 시작까지 완료된 마지막
   intensity 쓰기의 값이며, 그런 쓰기가 아예 없으면 미증명이다(부재는 증명이 아니다 —
   group 의 `safe_state` 를 상속하지 않는 `LD-STATE-001` 과 같은 이유).
2. 창 안에서 **진행 중이거나 새로 시작하는 intensity 쓰기가 없어야** 한다. 목표값이 0 인
   fade 도 진행 중이면 미증명이다: 0 으로 **가는** 중인 것은 0 **인** 것이 아니다.

`LD-REENTRY-001` — **광고를 검증한다.** `random_access` 는 계획의 필드가 아니라 context 의
capability 신고다. 계약은 *"중간 fade의 현재 값·remaining duration, beat 위치가 재현되지
않으면 random_access=false/unsupported다"* 라고 적었고, 그 재현은 실기 관측이므로 이 저장소의
관측은 0건이다. C4 가 이 축을 판정 없이 남겨 두었고 여기서 닫는다.

[HARD] **reveal 시각을 미뤄 맞추지 않는다.** 진단은 대체안을 내지 않으며(`after` 부재),
계약이 적은 두 갈래만 요청으로 담는다 — 원점을 확장한 새 audio/context, 또는 사람이 사전
준비한 verified baseline. 이 버전 스키마에 음수 clock·pre-roll 필드가 없기 때문이다.

[HARD] 콘솔 무접촉 · OSC 무접촉 — dict 만 다룬다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.director.validate.conflict import group_fixtures
from server.director.validate.diagnostics import (
    STATUS_UNRESOLVED,
    STATUS_UNSUPPORTED,
    Diagnostic,
    absent,
)
from server.director.validate.simulate import ActionRef, action_refs, fx_instances

STAGE = "safety"

ROOT_POINTER = ""

#: 어둠을 깨는 축. `affects_axes` 에 이것이 있는 FX 가 창 안에 살아 있으면 미증명이다.
INTENSITY_AXIS = "intensity"

#: **관측된** random_access 조합. 지금은 비어 있다.
#:
#: [HARD] 이 상수를 채우는 것이 곧 승격이며 근거는 실기 관측이어야 한다 — 임의 cue index 에서
#: 중간 fade 의 현재 값·잔여 duration·beat 위치가 재현되는지 실제로 보아야 한다
#: (`acceptance.md` AC-LDPLUGIN-012 콘솔 PASS 조건). context 의 자기 신고로 채우지 않는다.
RANDOM_ACCESS_OBSERVED: tuple[str, ...] = ()

_CONTRACT_ROUTES = (
    "이 버전 스키마에는 음수 clock·pre-roll 필드가 없으므로, 계약 LD-MIB-001 이 적은 두 갈래 "
    "중 하나가 필요합니다 — (가) 원점을 확장한 새 audio/context, 또는 (나) 사람이 사전 준비한 "
    "verified baseline. reveal 시각을 미뤄 맞추는 것은 두 갈래에 없습니다."
)


@dataclass(frozen=True, slots=True)
class DarkWindow:
    """한 dark move 가 어두워야 하는 구간 `[start_ms, end_ms)`."""

    group_id: str
    pointer: str
    start_ms: int
    end_ms: int
    settle_ms: int


@dataclass(frozen=True, slots=True)
class _Write:
    """intensity 쓰기 하나 — 구간과 목표값."""

    start_ms: int
    end_ms: int
    value: float | int | None
    pointer: str


def _refuse(
    pointer: str, reason: str, *, status: str = STATUS_UNSUPPORTED, rule: str = "LD-MIB-001"
) -> Diagnostic:
    """거부 진단 하나. `after` 는 **항상 부재**다 — reveal 이동을 제안하지 않는다."""
    return Diagnostic(
        rule_id=rule,
        pointer=pointer,
        status=status,
        blocking=True,
        reason=reason,
        stage=STAGE,
        before=absent(),
        after=absent(),
    )


def _presets_by_id(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(p.get("preset_id")): p for p in context.get("presets") or [] if isinstance(p, dict)}


def _is_dark_move(ref: ActionRef) -> bool:
    return ref.op == "position_set" and str(ref.action.get("move_mode", "")) == "dark_move"


def _axis_span(ref: ActionRef, axis: str) -> tuple[int, int] | None:
    timing = ref.action.get("timing")
    entry = timing.get(axis) if isinstance(timing, dict) else None
    if not isinstance(entry, dict):
        return None
    start = ref.at_ms + int(entry.get("delay_ms", 0))
    return start, start + int(entry.get("fade_ms", 0))


def dark_windows(plan: dict[str, Any], context: dict[str, Any]) -> list[DarkWindow]:
    """해소 가능한 dark move 창 전부. `settle_ms` 를 못 찾은 것은 **빼고** 낸다.

    빼는 이유: `settle_ms` 를 0 으로 가정하면 창이 짧아져 어둠 요구가 느슨해진다. 그 경우는
    `check_dark_move` 가 별도 blocking 으로 답한다 — 여기서 짧은 창을 내면 판정 불능이
    통과로 바뀐다.
    """
    presets = _presets_by_id(context)
    windows: list[DarkWindow] = []

    for ref in action_refs(plan):
        if not _is_dark_move(ref):
            continue
        spans = [span for span in (_axis_span(ref, "pan"), _axis_span(ref, "tilt")) if span]
        if not spans:
            continue
        preset = presets.get(str(ref.action.get("preset_ref", "")))
        if preset is None:
            continue
        settle = int(preset.get("settle_ms", 0) or 0)

        windows.append(
            DarkWindow(
                group_id=ref.group_id,
                pointer=ref.pointer,
                # movement 는 delay 가 끝나고 시작한다 — delay 구간은 아직 안 움직인다.
                start_ms=min(start for start, _ in spans),
                # 끝은 pan·tilt 중 **늦은** 완료 + settle. 빠른 쪽으로 재면 창이 짧아진다.
                end_ms=max(end for _, end in spans) + settle,
                settle_ms=settle,
            )
        )
    return windows


def shadow_groups(context: dict[str, Any], group_id: str) -> dict[str, tuple[str, ...]]:
    """`group_id` 와 fixture 를 **공유하는** 모든 group → 겹치는 fixture 목록.

    자기 자신도 들어간다(자기와의 교집합은 비지 않는다). 어둠은 **fixture 의 성질**이므로
    dark move 를 요청한 group 만 보면 같은 조명을 공유하는 다른 group 이 그것을 밝혀도
    통과한다 — 계약 `LD-CONFLICT-001` 이 fixture 전개를 요구하는 것과 같은 이유가 여기에도
    걸린다. 전개 규칙은 `conflict.group_fixtures` 하나를 쓴다.
    """
    fixtures = group_fixtures(context)
    own = set(fixtures.get(group_id, ()))
    if not own:
        return {}
    shared: dict[str, tuple[str, ...]] = {}
    for other, members in fixtures.items():
        overlap = own & set(members)
        if overlap:
            shared[other] = tuple(sorted(overlap))
    return shared


def _intensity_writes(plan: dict[str, Any], group_id: str) -> list[_Write]:
    writes: list[_Write] = []
    for ref in action_refs(plan):
        if ref.op != "intensity_set" or ref.group_id != group_id:
            continue
        span = _axis_span(ref, INTENSITY_AXIS)
        if span is None:
            continue
        start, end = span
        writes.append(_Write(start, end, ref.action.get("value_pct"), ref.pointer))
    return writes


def _settled_value_at(writes: list[_Write], t_ms: int) -> _Write | None:
    """`t_ms` 까지 **완료된** 마지막 쓰기. 없으면 `None` — 미증명이다."""
    settled = [w for w in writes if w.end_ms <= t_ms]
    if not settled:
        return None
    return max(settled, key=lambda w: (w.end_ms, w.start_ms))


def _in_flight(writes: list[_Write], window: DarkWindow) -> list[_Write]:
    """창 안에서 진행 중이거나 새로 시작하는 쓰기.

    술어는 `start < W.end and end > W.start` 다. 창 시작 시각에 정확히 **완료되는** fade 는
    걸리지 않고(그 값은 정착값 검사가 본다), 창 시작 시각에 **새로 놓이는** 순간 변경은
    정착값 검사가 잡는다 — 두 경우가 같은 `end == W.start` 를 갖지만 뜻이 다르므로 한
    술어로 뭉치지 않았다.
    """
    return [w for w in writes if w.start_ms < window.end_ms and w.end_ms > window.start_ms]


def _intensity_fx_spans(
    plan: dict[str, Any], context: dict[str, Any], group_id: str
) -> tuple[list[tuple[str, int, int, str]], list[Diagnostic]]:
    """intensity 축을 쓰는 FX 의 `(instance, start, end, pointer)` 와 판정 불능 진단."""
    presets = _presets_by_id(context)
    spans: list[tuple[str, int, int, str]] = []
    diagnostics: list[Diagnostic] = []

    for instance, entry in sorted(fx_instances(plan).items()):
        if not entry.starts or not entry.stops:
            continue
        start, stop = entry.starts[0], entry.stops[0]
        if start.group_id != group_id:
            continue
        preset_ref = str(start.action.get("preset_ref", ""))
        preset = presets.get(preset_ref)
        if preset is None:
            diagnostics.append(
                _refuse(
                    start.pointer,
                    f"FX preset {preset_ref} 를 context 에서 찾을 수 없어 affects_axes 를 알 수 "
                    "없습니다. 「intensity 축을 안 쓴다」로 두면 dark move 의 어둠 검사를 "
                    "조용히 통과하므로, 판정 불능으로 답합니다.",
                    status=STATUS_UNRESOLVED,
                )
            )
            continue
        if INTENSITY_AXIS not in [str(a) for a in preset.get("affects_axes") or []]:
            continue
        span = _axis_span(stop, "fx")
        spans.append((instance, start.at_ms, span[1] if span else stop.at_ms, start.pointer))

    return spans, diagnostics


def check_dark_move(plan: dict[str, Any], context: dict[str, Any] | None) -> list[Diagnostic]:
    """`LD-MIB-001` — dark move 의 어둠이 증명되는가."""
    if context is None:
        return [
            _refuse(
                ROOT_POINTER,
                "ContextSnapshot 없이 dark move 를 판정할 수 없습니다 — preset 의 settle_ms 와 "
                "FX 의 affects_axes 가 모두 context 에 있습니다. 판정 불능을 통과로 바꾸지 "
                "않습니다.",
                status=STATUS_UNRESOLVED,
            )
        ]

    presets = _presets_by_id(context)
    diagnostics: list[Diagnostic] = []

    # settle_ms 를 해소할 수 없는 dark move 는 창을 만들 수 없다 — 0 으로 가정하지 않는다.
    for ref in action_refs(plan):
        if not _is_dark_move(ref):
            continue
        preset_ref = str(ref.action.get("preset_ref", ""))
        if presets.get(preset_ref) is None:
            diagnostics.append(
                _refuse(
                    ref.pointer,
                    f"position preset {preset_ref} 을 context 에서 찾을 수 없어 settle_ms 를 알 "
                    "수 없습니다. 0 으로 가정하면 어두워야 하는 창이 짧아져 요구가 느슨해지므로, "
                    "판정 불능으로 답합니다.",
                    status=STATUS_UNRESOLVED,
                )
            )

    for window in dark_windows(plan, context):
        shared = shadow_groups(context, window.group_id)
        if not shared:
            diagnostics.append(
                _refuse(
                    window.pointer,
                    f"group {window.group_id} 이 context 의 groups 에 없거나 fixture 가 비어 "
                    "있어 어느 조명이 어두워야 하는지 알 수 없습니다. 판정 불능으로 답합니다.",
                    status=STATUS_UNRESOLVED,
                )
            )
            continue

        # 어둠은 fixture 의 성질이다 — 공유하는 모든 group 을 본다. 요청한 group 만 보면
        # 같은 조명을 공유하는 다른 group 이 그것을 밝혀도 통과한다.
        for lit_group, overlap in sorted(shared.items()):
            where = (
                ""
                if lit_group == window.group_id
                else f" (group {lit_group} 이 fixture {', '.join(overlap)} 를 공유합니다)"
            )
            writes = _intensity_writes(plan, lit_group)

            settled = _settled_value_at(writes, window.start_ms)
            if settled is None:
                diagnostics.append(
                    _refuse(
                        window.pointer,
                        f"group {lit_group} 의 intensity 가 dark move 창 시작 "
                        f"{window.start_ms}ms 까지 한 번도 선언되지 않았습니다{where}. 0 으로 "
                        f"가정하지 않습니다 — 부재는 증명이 아닙니다. {_CONTRACT_ROUTES}",
                    )
                )
            elif settled.value != 0:
                diagnostics.append(
                    _refuse(
                        window.pointer,
                        f"group {lit_group} 의 intensity 가 dark move 창 시작 "
                        f"{window.start_ms}ms 에 {settled.value} 입니다 (0 이어야 합니다){where}. "
                        f"창은 [{window.start_ms}, {window.end_ms}) 이며 pan/tilt 중 늦은 완료에 "
                        f"settle_ms {window.settle_ms} 를 더한 구간입니다. {_CONTRACT_ROUTES}",
                    )
                )

            for write in _in_flight(writes, window):
                diagnostics.append(
                    _refuse(
                        window.pointer,
                        f"dark move 창 [{window.start_ms}, {window.end_ms}) 안에서 group "
                        f"{lit_group} 의 intensity 쓰기가 진행되거나 시작됩니다{where} "
                        f"({write.pointer}, [{write.start_ms}, {write.end_ms}) → {write.value}). "
                        "목표값이 0 이어도 진행 중인 fade 는 0 임이 증명되지 않습니다 — 0 으로 "
                        f"가는 중인 것은 0 인 것이 아닙니다. {_CONTRACT_ROUTES}",
                    )
                )

            spans, problems = _intensity_fx_spans(plan, context, lit_group)
            diagnostics.extend(problems)
            for instance, fx_start_ms, fx_end_ms, pointer in spans:
                if fx_start_ms < window.end_ms and fx_end_ms > window.start_ms:
                    diagnostics.append(
                        _refuse(
                            window.pointer,
                            f"intensity 축을 쓰는 FX {instance}(group {lit_group}) 가 dark move "
                            f"창 [{window.start_ms}, {window.end_ms}) 안에 살아 있습니다{where} "
                            f"([{fx_start_ms}, {fx_end_ms}), {pointer}). 계약은 창 동안 "
                            f"intensity FX 가 없음을 요구합니다. {_CONTRACT_ROUTES}",
                        )
                    )

    return diagnostics


def check_random_access(plan: dict[str, Any], context: dict[str, Any] | None) -> list[Diagnostic]:
    """`LD-REENTRY-001` — `random_access` 광고에 근거가 있는가.

    계획을 읽지 않는다: 이 조항의 판정 대상은 계획이 아니라 context 의 capability 신고다.
    그래도 `plan` 을 받는 이유는 5단의 다른 검사와 호출 형태를 맞추기 위한 것이며, 안 쓰는
    입력임을 여기에 적어 둔다.
    """
    if context is None:
        return [
            _refuse(
                ROOT_POINTER,
                "ContextSnapshot 없이 random_access 광고를 판정할 수 없습니다. 판정 불능을 "
                "통과로 바꾸지 않습니다.",
                status=STATUS_UNRESOLVED,
                rule="LD-REENTRY-001",
            )
        ]

    diagnostics: list[Diagnostic] = []
    for entry in context.get("capabilities") or []:
        if not isinstance(entry, dict) or not entry.get("random_access"):
            continue
        group_id = str(entry.get("group_id"))
        if group_id in RANDOM_ACCESS_OBSERVED:
            continue
        diagnostics.append(
            _refuse(
                ROOT_POINTER,
                f"group {group_id} 의 capability 가 random_access=true 로 광고하지만 그 근거가 "
                "관측되지 않았습니다(관측 0건). 계약 LD-REENTRY-001 은 임의 cue index 에서 중간 "
                "fade 의 현재 값·잔여 duration·beat 위치가 재현되지 않으면 random_access 를 "
                "false/unsupported 로 규정합니다 — 재현 여부는 실기 관측이며 context 의 자기 "
                "신고로 대신할 수 없습니다. 계획의 결함이 아닙니다.",
                rule="LD-REENTRY-001",
            )
        )
    return diagnostics
