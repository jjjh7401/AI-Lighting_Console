"""capability 거부 (SPEC-LDCOMPILE-001 C4, REQ-LDPLUGIN-008·013 거부부).

계약 §8 `LD-CAP-001`: *"group별 op/preset/timing 축/cycle/dark_move/random_access가
compiler+rig 실제 capability와 맞아야 한다. parser가 받아도 emitter가 보존하지 못하면
unsupported+blocking. 요청 field 제거, fallback preset, percent clamp는 금지."*

**이 모듈은 아무것도 열지 않는다.** 4단은 C1 때부터 전부 blocking 이었고, C4 가 하는 일은
그 blocking 의 *사유를 축·op별로 정확하게 만드는 것*이다 (`plan.md` §2.1). 승격은 C6 의
emitter 프로브가 관측한 뒤에만 일어난다 — `AXIS_TIMING_OBSERVED` 가 그 자리이며 지금은
비어 있다.

가장 중요한 설계 하나: **context 의 `capabilities` 자기 신고를 근거로 쓰지 않는다.** 규범
예제의 context 는 7개 op·6개 축·dark_move·random_access 를 전부 `true` 로 광고하지만,
`LD-CAP-001` 은 광고의 근거를 *"실제 compiler+rig+target 출력"* 으로 못박았고 이 저장소의
축별 emitter 실측은 0건이다(`spec.md` §6.1). 그래서 신고는 **좁히는 데만** 쓴다 — 신고가
「지원 안 함」이라고 말하면 그 사유를 정확하게 붙이고, 「지원함」이라고 말해도 관측이 없으면
여전히 unsupported 다. 신고를 넓히는 근거로 쓰면 그 순간 관측 없는 승격이 된다.

5대 금지(clamp·quantize·대체 preset·필드 제거·임의 command)를 한 문장으로 집행한다:
**이 모듈의 어떤 진단도 `after` 에 값을 싣지 않는다.** 값을 실으면 그것이 곧 「이렇게 바꾸면
된다」는 제안이고, 네 금지가 모두 그 형태로 새어 나온다.

[HARD] 콘솔 무접촉 · OSC 무접촉 — dict 만 다룬다.
"""

from __future__ import annotations

from typing import Any

from server.director.validate.diagnostics import (
    STATUS_SAFETY_BLOCKED,
    STATUS_UNSUPPORTED,
    Diagnostic,
    absent,
)
from server.director.validate.simulate import ActionRef, action_refs

STAGE = "capability_fidelity"

ROOT_POINTER = ""

#: 계약 스키마의 op enum 7개. 시험이 스키마에서 읽어 이 표와 대조한다 — 표가 새면 그 op 은
#: 시험되지 않은 채 통과하므로, 기대값의 출처를 손이 아니라 스키마로 둔다.
OPS: tuple[str, ...] = (
    "intensity_set",
    "color_set",
    "position_set",
    "beam_set",
    "fx_start",
    "fx_stop",
    "group_release",
)

#: op 이 timing 을 요구하는 축. 계약 §7 *"모든 axis timing을 명시하며 기본값 상속은 없다"*.
_OP_TIMING_AXES: dict[str, tuple[str, ...]] = {
    "intensity_set": ("intensity",),
    "color_set": ("color",),
    "position_set": ("pan", "tilt"),
    "beam_set": ("beam",),
    "fx_start": ("fx",),
    "fx_stop": ("fx",),
    "group_release": ("intensity", "color", "pan", "tilt", "beam"),
}

#: `preset_ref` 를 드는 op.
_PRESET_OPS = frozenset({"color_set", "position_set", "beam_set", "fx_start"})

#: **관측된** 축별 timing 통로.
#:
#: `spec.md` §6.1 실측(2026-09-14, `cde2744`): `PanFade`·`TiltFade`·`ColorFade`·`BeamFade`
#: 각 0건, `IndividualFade`·`AttributeFade`·`IndividualTime` 각 0건, `.py` 의 `delay_ms` 0건.
#: 유일한 `CueFade` 87건은 큐 단위 스칼라 하나라 축을 구분하지 못한다.
#:
#: [HARD] 이 상수를 채우는 것이 곧 승격이며, 근거는 **실기 관측**이어야 한다
#: (`acceptance.md` AC-LDPLUGIN-013 *"콘솔 PASS 조건(승격의 유일한 근거)"*). 코드 판독이나
#: context 의 자기 신고로 채우지 않는다.
#:
#: C6 round 5(2026-09-16) 실기 관측: `Set Cue <n> Sequence <seq> Property 'Preset2Fade'/
#: 'Preset2Delay' <값>` — 다른 카드 t215(`.moai/reports/t215/verdict.md` §3 F1)가 확정한
#: 문법을 다시 추측하지 않고 재사용해, 되읽기로 값이 실제로 바뀌는 것까지 확인했다
#: (`progress.md` §E.2 Evidence — P1 ④). `intensity`·`color`·`beam`·`fx` 는 여전히
#: 관측 0건이라 이 튜플에 없다.
#:
#: [HARD] **`pan`·`tilt` 는 조건부 관측이다 — 무조건이 아니다.** `Preset2Fade`/
#: `Preset2Delay` 는 Position **한 preset type 전체**에 걸리는 값 하나뿐이라 pan·tilt 를
#: 다른 시간으로 나눠 담을 통로가 없다(pan ≠ tilt 독립성은 여전히 미확립,
#: `progress.md` §E.3 Gap). 그래서 이 튜플에 있다는 사실만으로 축별 timing 이 통과하지
#: 않는다 — `_axis_timing_is_reproducible` 이 **pan·tilt 값이 같을 때만** 관측된 것으로
#: 본다. 이 제약을 지우고 이 튜플 멤버십만으로 판단하면, pan·tilt 에 다른 값을 요구한
#: 요청까지 통과시키는 관측 없는 승격이 된다.
AXIS_TIMING_OBSERVED: tuple[str, ...] = ("pan", "tilt")

_UNMEASURED_REASON = (
    "축별 delay/fade 를 보존하는 emitter 가 실측되지 않았습니다(관측 0건). LD-CAP-001 은 "
    "capability 광고의 근거를 실제 compiler+rig+target 출력으로 규정하므로, 관측 전에는 "
    "context 가 지원한다고 신고해도 unsupported 로 답합니다. 최소 timing 해상도 또한 "
    "실측되지 않아 요청 값을 정확히 재현할 수 있는지 증명할 수 없습니다 — 자동으로 "
    "quantize·clamp·대체하지 않습니다. 계획의 결함이 아닙니다."
)

_POSITION_MISMATCH_REASON = (
    "pan·tilt 에 다른 timing 값을 요청했습니다. 실기로 관측된 유일한 Position timing "
    "통로(Preset2Fade/Preset2Delay, 2026-09-16 관측)는 Position preset type 전체에 걸리는 "
    "값 하나뿐이라 pan·tilt 를 다른 시간으로 나눌 수 없습니다. 하나의 값으로 합치거나 "
    "clamp 하지 않습니다 — 다른 값을 그대로 재현할 수 있는 통로가 실측되기 전까지는 "
    "unsupported 로 답합니다."
)


def _position_pan_tilt_mismatch(op: str, axes: list[str], timing: dict[str, Any]) -> bool:
    """`position_set` 이 pan·tilt 를 정확히 둘 다 선언했고 값이 다른가.

    둘 다 선언했을 때만 판단한다 — 하나만 선언한 경우(예: pan 만)는 이 함수가 아니라
    `AXIS_TIMING_OBSERVED` 멤버십만으로 이미 걸린다(둘 다 있어야 재현 가능하므로).
    """
    return (
        op == "position_set" and axes == ["pan", "tilt"] and timing.get("pan") != timing.get("tilt")
    )


def _axis_timing_is_reproducible(op: str, axes: list[str], timing: dict[str, Any]) -> bool:
    """요청한 축별 timing 을 관측된 통로로 충실히 재현할 수 있는가.

    `pan`·`tilt` 를 조금이라도 든 요청은 **전부** 이 조건을 거친다 — `position_set` 이고
    pan·tilt 둘 다 선언했고 값이 같을 때만 참이다. `pan` 하나만 선언한 요청을 일반
    멤버십 검사로 흘리면(`{"pan"} <= {"pan","tilt"}` 는 참이다) tilt 없이도 통과해
    버린다 — Position 은 한 preset type 뿐이라 pan 하나만 따로 재현할 통로가 없다.
    """
    if "pan" in axes or "tilt" in axes:
        return (
            op == "position_set"
            and axes == ["pan", "tilt"]
            and set(axes) <= set(AXIS_TIMING_OBSERVED)
            and timing.get("pan") == timing.get("tilt")
        )
    return set(axes) <= set(AXIS_TIMING_OBSERVED)


def _refuse(pointer: str, reason: str, *, status: str = STATUS_UNSUPPORTED) -> Diagnostic:
    """거부 진단 하나. `after` 는 **항상 부재**다 — 대체안을 제안하지 않는다."""
    return Diagnostic(
        rule_id="LD-CAP-001",
        pointer=pointer,
        status=status,
        blocking=True,
        reason=reason,
        stage=STAGE,
        before=absent(),
        after=absent(),
    )


def _capabilities_by_group(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("group_id")): entry
        for entry in context.get("capabilities") or []
        if isinstance(entry, dict)
    }


def _presets_by_id(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("preset_id")): entry
        for entry in context.get("presets") or []
        if isinstance(entry, dict)
    }


def _requested_axes(ref: ActionRef) -> list[str]:
    """action 이 실제로 timing 을 든 축. 표에 있는 축 중 payload 에 들어온 것만 본다."""
    timing = ref.action.get("timing")
    declared = timing if isinstance(timing, dict) else {}
    return [axis for axis in _OP_TIMING_AXES.get(ref.op, ()) if axis in declared]


def _check_op_and_group(ref: ActionRef, capability: dict[str, Any] | None) -> list[Diagnostic]:
    if ref.op not in OPS:
        return [
            _refuse(
                ref.pointer,
                f"op {ref.op!r} 은 계약이 정의한 7개 op 이 아닙니다. 임의 MA/Lua/OSC command "
                "string·임의 query·임의 channel address 는 이 통로로 들어올 수 없으며, "
                "모르는 op 을 조용히 지나치지 않습니다.",
            )
        ]
    if capability is None:
        return [
            _refuse(
                ref.pointer,
                f"group {ref.group_id} 의 capability 선언이 context 에 없습니다. 무엇을 "
                "지원하는지 모르는 상태를 지원으로 바꾸지 않습니다.",
            )
        ]

    operations = [str(o) for o in capability.get("operations") or []]
    if ref.op not in operations:
        return [
            _refuse(
                ref.pointer,
                f"op {ref.op} 이 group {ref.group_id} 의 capability 선언에 없습니다 "
                f"(선언된 op: {', '.join(operations) or '없음'}).",
            )
        ]
    return []


def _check_axes(ref: ActionRef, capability: dict[str, Any]) -> list[Diagnostic]:
    declared = [str(a) for a in capability.get("timing_axes") or []]
    missing = [axis for axis in _requested_axes(ref) if axis not in declared]
    if not missing:
        return []
    return [
        _refuse(
            ref.pointer,
            f"{ref.op} 이 요구하는 timing 축 {', '.join(missing)} 이 group {ref.group_id} 의 "
            f"capability 선언에 없습니다 (선언된 축: {', '.join(declared) or '없음'}). "
            "지원하지 않는 축의 요청을 버리고 나머지만 적용하지 않습니다 — 구성 전체가 "
            "판정 단위입니다.",
        )
    ]


def _check_preset(
    ref: ActionRef, presets: dict[str, dict[str, Any]], safety: dict[str, Any]
) -> list[Diagnostic]:
    if ref.op not in _PRESET_OPS:
        return []
    preset_ref = str(ref.action.get("preset_ref", ""))

    if preset_ref in {str(p) for p in safety.get("forbidden_preset_refs") or []}:
        return [
            _refuse(
                ref.pointer,
                f"preset {preset_ref} 은 safety 정책의 forbidden_preset_refs 에 있습니다. "
                "이것은 capability 부족이 아니라 정책 거부이므로 사람이 할 일이 다릅니다.",
                status=STATUS_SAFETY_BLOCKED,
            )
        ]

    preset = presets.get(preset_ref)
    if preset is None:
        return [
            _refuse(
                ref.pointer,
                f"preset {preset_ref} 을 context 에서 찾을 수 없습니다. 비슷한 preset 으로 "
                "바꾸지 않습니다 — fallback preset 은 금지이며, 무엇이 실제로 나갈지 "
                "사람이 모르는 상태가 되기 때문입니다.",
            )
        ]

    group_ids = [str(g) for g in preset.get("group_ids") or []]
    if ref.group_id not in group_ids:
        return [
            _refuse(
                ref.pointer,
                f"preset {preset_ref} 은 group {ref.group_id} 을 덮지 않습니다 "
                f"(덮는 group: {', '.join(group_ids) or '없음'}). 존재하지만 이 group 에 "
                "쓸 수 없는 경우이며, 호환되는 다른 preset 으로 대체하지 않습니다.",
            )
        ]
    return []


def _check_intensity_policy(ref: ActionRef, safety: dict[str, Any]) -> list[Diagnostic]:
    if ref.op != "intensity_set":
        return []
    value = ref.action.get("value_pct")
    if not isinstance(value, (int, float)):
        return []

    limit = safety.get("max_intensity_pct")
    if isinstance(limit, (int, float)) and value > limit:
        return [
            _refuse(
                ref.pointer,
                f"value_pct {value} 가 safety 정책 상한 {limit} 를 넘습니다. 상한으로 "
                "clamp 하지 않습니다 — percent clamp 는 금지이며, 조용히 깎으면 사람이 "
                "의도한 값과 나간 값이 달라진 것을 알 수 없습니다.",
                status=STATUS_SAFETY_BLOCKED,
            )
        ]
    if value < 0:
        return [
            _refuse(
                ref.pointer,
                f"value_pct {value} 가 음수입니다. 0 으로 올리지 않습니다 — 이것도 clamp "
                "이며 같은 이유로 금지입니다.",
                status=STATUS_SAFETY_BLOCKED,
            )
        ]
    return []


def _check_declared_flags(ref: ActionRef, capability: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if ref.op == "fx_start" and not capability.get("fx_cycle_beats"):
        diagnostics.append(
            _refuse(
                ref.pointer,
                f"group {ref.group_id} 의 capability 가 fx_cycle_beats 를 지원하지 않는다고 "
                f"신고했는데 이 action 은 cycle_beats={ref.action.get('cycle_beats')} 를 "
                "요구합니다. cycle 을 반올림하거나 버리지 않습니다.",
            )
        )

    if (
        ref.op == "position_set"
        and str(ref.action.get("move_mode", "")) == "dark_move"
        and not capability.get("dark_move")
    ):
        diagnostics.append(
            _refuse(
                ref.pointer,
                f"group {ref.group_id} 의 capability 가 dark_move 를 지원하지 않는다고 "
                "신고했는데 이 action 은 dark_move 를 요구합니다. 일반 이동으로 바꾸지 "
                "않습니다 — 그것은 무대에서 빔이 지나가는 것을 뜻하므로 조용히 대체할 수 "
                "있는 차이가 아닙니다.",
            )
        )

    return diagnostics


def check_capability(plan: dict[str, Any], context: dict[str, Any] | None) -> list[Diagnostic]:
    """4단의 capability 판정 — `LD-CAP-001`. **모든 진단이 blocking 이다.**

    action 이 판정 단위다 (계약 §6.3 의 *"각 요청 action에는 적어도 하나의 diagnostic"*).
    사유는 원인별로 갈리며, 원인이 여러 개면 여러 개가 붙는다 — 하나만 남기면 사람이 한
    번에 하나씩만 고치게 된다.
    """
    refs = action_refs(plan)

    if context is None:
        # [HARD] context 가 없어도 **action 별로** 낸다. 이 단계가 계약 §6.3 의 *"각 요청
        # action에는 적어도 하나의 diagnostic이 있어야"* 를 채우는 자리이므로, root 하나로
        # 갈음하면 action 들이 진단 0개가 되어 그 조항을 위반한다 — C1 의 coverage 가드가
        # 잡은 회귀다.
        reason = (
            "ContextSnapshot 없이 capability 를 판정할 수 없습니다 — group별 op·축·preset·"
            "정책이 모두 context 에 있습니다. 판정 불능을 통과로 바꾸지 않습니다."
        )
        if not refs:
            return [_refuse(ROOT_POINTER, reason)]
        return [_refuse(ref.pointer, reason) for ref in refs]

    capabilities = _capabilities_by_group(context)
    presets = _presets_by_id(context)
    safety = context.get("safety") if isinstance(context.get("safety"), dict) else {}

    if not refs:
        return [
            _refuse(
                ROOT_POINTER,
                "요청된 action 이 없습니다. 계약 LD-STATE-001 은 빈 cue/terminal 배열을 "
                "draft 에서만 허용하므로 ready 판정 대상이 아닙니다.",
            )
        ]

    diagnostics: list[Diagnostic] = []
    for ref in refs:
        capability = capabilities.get(ref.group_id)
        blockers = _check_op_and_group(ref, capability)
        if blockers:
            # op 이나 group 자체가 해소되지 않으면 축·preset 판정은 의미가 없다.
            diagnostics.extend(blockers)
            continue

        assert capability is not None  # _check_op_and_group 가 None 을 걸렀다
        diagnostics.extend(_check_axes(ref, capability))
        diagnostics.extend(_check_preset(ref, presets, safety))
        diagnostics.extend(_check_intensity_policy(ref, safety))
        diagnostics.extend(_check_declared_flags(ref, capability))

        # 상시 사유 — 재현 가능하지 않으면 여전히 unsupported 다. 이 줄이 곧 「관측 없는
        # 승격이 일어나지 않는다」는 집행이며, `_axis_timing_is_reproducible` 이
        # `AXIS_TIMING_OBSERVED`(C6) 와 pan==tilt 제약을 함께 집행한다.
        requested = _requested_axes(ref)
        timing = ref.action.get("timing")
        timing = timing if isinstance(timing, dict) else {}
        if requested and not _axis_timing_is_reproducible(ref.op, requested, timing):
            reason = (
                _POSITION_MISMATCH_REASON
                if _position_pan_tilt_mismatch(ref.op, requested, timing)
                else _UNMEASURED_REASON
            )
            diagnostics.append(
                _refuse(
                    ref.pointer,
                    f"{ref.op} 의 축 {', '.join(requested)} — {reason}",
                )
            )

    return diagnostics
