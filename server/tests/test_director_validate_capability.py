"""capability 거부 시험 — `LD-CAP-001` (SPEC-LDCOMPILE-001 C4, REQ-LDPLUGIN-008·013 거부부).

이 마일스톤은 **아무것도 열지 않는다.** 4단은 C1 때부터 전부 blocking 이었고 C4 가 하는 일은
그 blocking 의 *사유를 축·op별로 정확하게 만드는 것*이다 (`plan.md` §2.1). 승격은 C6 의
emitter 프로브가 관측한 뒤에만 일어난다 — `acceptance.md` AC-LDPLUGIN-013 이 *"콘솔 PASS
조건(승격의 유일한 근거)"* 이라고 못박았다.

그래서 이 파일의 시험은 두 종류다.

1. **사유가 정확한가** — 원인이 다르면 진단도 달라야 한다. 「전부 같은 문구」는 사람이
   무엇을 고쳐야 할지 알려주지 않는다.
2. **대체안을 내지 않는가** — 5대 금지(clamp·quantize·대체 preset·필드 제거·임의 command)를
   한 문장으로 검사 가능하게 만들면 *"어떤 진단도 `after` 에 값을 싣지 않는다"* 다. 값을
   실으면 그것이 곧 「이렇게 바꾸면 된다」는 제안이고, 계약이 금지한 것이다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.tests.test_director_validate_ready import (
    GROUPS,
    beam,
    color,
    cue,
    fx_start,
    fx_stop,
    group_release,
    intensity,
    make_plan,
    position,
    terminal,
)

_SPEC = Path(__file__).resolve().parents[2] / ".moai/specs/SPEC-LDPLUGIN-001"


def _load(relative: str) -> dict[str, Any]:
    return json.loads((_SPEC / relative).read_text(encoding="utf-8"))


@pytest.fixture
def plan() -> dict[str, Any]:
    return _load("examples/plan.json")


@pytest.fixture
def context() -> dict[str, Any]:
    return _load("examples/context.json")


def _blocking(diagnostics: list[Any]) -> list[Any]:
    return [d for d in diagnostics if d.blocking]


def _reasons(diagnostics: list[Any]) -> str:
    return " ".join(d.reason for d in diagnostics)


def one_action_plan(action: dict[str, Any], *, group: str = GROUPS[0]) -> dict[str, Any]:
    """action 하나만 든 계획. 4단은 action 단위로 판정하므로 이것이 최소 단위다."""
    return make_plan([cue("cue-a", 0, [action])], [terminal(group)], controlled=(group,))


# --------------------------------------------------------------------------- #
# op 표가 새지 않는가 — 표가 새면 그 op 은 시험되지 않는다
# --------------------------------------------------------------------------- #


class TestOpTableCoversTheSchema:
    def test_op_table_equals_the_schema_enum(self):
        """`AC-LDPLUGIN-008` 6번 — op 표가 7건 전부를 덮는지 **스키마에서 읽어** 대조한다.

        표를 손으로 적어 두면 스키마에 op 이 늘 때 조용히 새고, 새 op 은 시험되지 않은 채
        통과한다. 그래서 기대값의 출처를 스키마로 둔다.
        """
        from server.director.validate.capability import OPS

        schema = _load("schemas/exchange.schema.json")
        enums = [
            value
            for definition in schema["$defs"].values()
            if isinstance(definition, dict)
            for value in [definition.get("properties", {}).get("op", {}).get("const")]
            if value
        ]
        assert set(OPS) == set(enums)
        assert len(OPS) == 7

    def test_every_op_receives_a_blocking_diagnostic(self):
        """7개 op 각각이 판정을 받는다 — 침묵으로 통과하는 op 이 없다.

        `position_set` 은 **pan≠tilt** 로 만든다(`position()` 기본값은 pan==tilt 라 C6
        round 5 이후 관측된 통로로 재현되어 조용히 통과한다 — 이 시험의 취지와 맞지 않다).
        pan≠tilt 는 `Preset2Fade`/`Preset2Delay` 하나로 나눠 담을 수 없어 여전히 막힌다.
        """
        from server.director.validate.capability import OPS, check_capability

        mismatched_position = position(GROUPS[0])
        mismatched_position["timing"]["tilt"] = dict(
            mismatched_position["timing"]["tilt"], fade_ms=500
        )
        actions = {
            "intensity_set": intensity(GROUPS[0], 50),
            "color_set": color(GROUPS[0]),
            "position_set": mismatched_position,
            "beam_set": beam(GROUPS[0]),
            "fx_start": fx_start(GROUPS[0], "pulse-a"),
            "fx_stop": fx_stop(GROUPS[0], "pulse-a"),
            "group_release": group_release(GROUPS[0]),
        }
        assert set(actions) == set(OPS), "시험이 op 표를 다 덮지 않는다"

        ctx = _load("examples/context.json")
        for op, action in actions.items():
            found = _blocking(check_capability(one_action_plan(action), ctx))
            assert found, f"{op} 이 판정 없이 통과했다"


# --------------------------------------------------------------------------- #
# 5대 금지 — 대체안을 내지 않는다
# --------------------------------------------------------------------------- #


class TestNoSubstituteIsEverProposed:
    def _every_shape(self) -> list[dict[str, Any]]:
        return [
            intensity(GROUPS[0], 50),
            intensity(GROUPS[0], 150),  # 상한 초과
            intensity(GROUPS[0], -10),  # 음수
            color(GROUPS[0], "color-nonexistent"),  # 부재 preset
            color(GROUPS[0], "color-amber", fade=3000),
            position(GROUPS[0], "pos-center", delay=500, fade=2000),
            beam(GROUPS[0], "beam-narrow", fade=100),
            fx_start(GROUPS[0], "pulse-a", cycle_beats=0.0625),
            fx_stop(GROUPS[0], "pulse-a", fade=500),
            group_release(GROUPS[0], fade=1000),
        ]

    def test_no_diagnostic_carries_a_replacement_value(self, context):
        """5대 금지를 한 문장으로 — **어떤 진단도 `after` 에 값을 싣지 않는다.**

        값을 실으면 그것이 곧 「이렇게 바꾸면 된다」는 제안이며, clamp·quantize·대체
        preset·필드 제거가 모두 그 형태로 새어 나온다. 그래서 축을 하나로 모았다.
        """
        from server.director.validate.capability import check_capability

        for action in self._every_shape():
            for diagnostic in check_capability(one_action_plan(action), context):
                wire = diagnostic.to_internal()
                assert wire["after"] == {"present": False}, (
                    f"{action['op']} 진단이 대체 값을 제안한다: {wire['after']}"
                )

    def test_over_limit_intensity_is_diagnosed_not_clamped(self, context):
        """`value_pct=150` 은 100 으로 잘리지 않는다 — clamp 는 금지다."""
        from server.director.validate.capability import check_capability

        found = _blocking(check_capability(one_action_plan(intensity(GROUPS[0], 150)), context))
        assert found
        text = _reasons(found)
        assert "150" in text, "무엇이 상한을 넘었는지 말해야 사람이 고칠 수 있다"
        assert "100" in text, "상한 값을 말해야 한다"

    def test_absent_preset_is_not_replaced_with_a_similar_one(self, context):
        """부재 preset 을 비슷한 것으로 바꾸지 않는다 — 다른 preset 이름을 내지 않는다."""
        from server.director.validate.capability import check_capability

        found = check_capability(one_action_plan(color(GROUPS[0], "color-nonexistent")), context)
        text = _reasons(found)
        assert "color-nonexistent" in text
        assert "color-amber" not in text, "대체 후보를 제안하면 fallback preset 금지 위반이다"
        assert "color-blue" not in text

    def test_unsupported_composition_refuses_the_whole_action(self, context):
        """필드 제거 금지 — `beam_set` 은 구성 전체가 판정 단위다.

        진단의 pointer 가 action leaf 이며 그 아래 개별 필드를 가리키지 않는다. 필드를
        가리키면 「그 필드만 버리면 된다」로 읽힌다.
        """
        from server.director.validate.capability import check_capability

        found = _blocking(
            check_capability(one_action_plan(beam(GROUPS[0], "beam-narrow", fade=100)), context)
        )
        assert found
        for diagnostic in found:
            assert diagnostic.pointer == "/cues/0/actions/0", (
                f"필드 단위 pointer 는 부분 폐기로 읽힌다: {diagnostic.pointer}"
            )


# --------------------------------------------------------------------------- #
# 사유가 원인별로 갈리는가
# --------------------------------------------------------------------------- #


class TestReasonsDistinguishCauses:
    def _narrow(self, context: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        """`group-front` 의 capability 선언만 좁힌다."""
        ctx = json.loads(json.dumps(context))
        for entry in ctx["capabilities"]:
            if entry["group_id"] == GROUPS[0]:
                entry.update(overrides)
        return ctx

    def test_unsupported_op_names_the_op(self, context):
        from server.director.validate.capability import check_capability

        ctx = self._narrow(context, operations=["intensity_set"])
        found = _blocking(check_capability(one_action_plan(color(GROUPS[0])), ctx))
        assert "color_set" in _reasons(found)

    def test_supported_op_does_not_get_the_unsupported_op_reason(self, context):
        """구멍도 잰다 — 선언된 op 에는 「op 미지원」 사유가 붙지 않는다."""
        from server.director.validate.capability import check_capability

        ctx = self._narrow(context, operations=["intensity_set"])
        found = check_capability(one_action_plan(intensity(GROUPS[0], 50)), ctx)
        assert "선언에 없습니다" not in _reasons(found)

    def test_unsupported_axis_names_the_axis(self, context):
        from server.director.validate.capability import check_capability

        ctx = self._narrow(context, timing_axes=["intensity", "color", "beam", "fx"])
        found = _blocking(check_capability(one_action_plan(position(GROUPS[0])), ctx))
        text = _reasons(found)
        assert "pan" in text and "tilt" in text

    def test_group_without_capability_entry_is_named(self, context):
        from server.director.validate.capability import check_capability

        ctx = json.loads(json.dumps(context))
        ctx["capabilities"] = [e for e in ctx["capabilities"] if e["group_id"] != GROUPS[0]]
        found = _blocking(check_capability(one_action_plan(intensity(GROUPS[0], 50)), ctx))
        assert GROUPS[0] in _reasons(found)

    def test_fx_cycle_unsupported_is_named(self, context):
        from server.director.validate.capability import check_capability

        ctx = self._narrow(context, fx_cycle_beats=False)
        found = _blocking(check_capability(one_action_plan(fx_start(GROUPS[0], "pulse-a")), ctx))
        assert "cycle" in _reasons(found)

    def test_dark_move_unsupported_is_named(self, context):
        from server.director.validate.capability import check_capability

        ctx = self._narrow(context, dark_move=False)
        found = _blocking(check_capability(one_action_plan(position(GROUPS[0])), ctx))
        assert "dark_move" in _reasons(found)

    def test_dark_move_reason_is_absent_when_supported(self, context):
        """구멍도 잰다 — `dark_move=true` 면 그 사유가 붙지 않는다."""
        from server.director.validate.capability import check_capability

        found = check_capability(one_action_plan(position(GROUPS[0])), context)
        assert "dark_move" not in _reasons(found)

    def test_preset_not_shared_with_the_group_is_named(self, context):
        """preset 이 존재하지만 이 group 을 덮지 않는 경우 — 부재와 다른 사유다."""
        from server.director.validate.capability import check_capability

        ctx = json.loads(json.dumps(context))
        for preset in ctx["presets"]:
            if preset["preset_id"] == "color-amber":
                preset["group_ids"] = [GROUPS[1]]
        found = _blocking(check_capability(one_action_plan(color(GROUPS[0])), ctx))
        text = _reasons(found)
        assert "color-amber" in text
        assert GROUPS[0] in text

    def test_forbidden_preset_is_safety_blocked_not_unsupported(self, context):
        """금지 preset 은 capability 문제가 아니라 safety 문제다 — status 가 갈린다."""
        from server.director.validate.capability import check_capability
        from server.director.validate.diagnostics import STATUS_SAFETY_BLOCKED

        ctx = json.loads(json.dumps(context))
        ctx["safety"]["forbidden_preset_refs"] = ["color-amber"]
        found = _blocking(check_capability(one_action_plan(color(GROUPS[0])), ctx))
        assert STATUS_SAFETY_BLOCKED in {d.status for d in found}

    def test_unknown_op_is_refused(self):
        """임의 command·query·channel address 는 스키마 enum 밖의 op 으로 도착한다.

        스키마가 `additionalProperties: false` + 7개 const 로 1차 방어하지만, 이 층도
        모르는 op 을 조용히 지나치지 않는다 — 방어가 한 층뿐이면 그 층을 우회하는 경로가
        곧 구멍이다.
        """
        from server.director.validate.capability import check_capability

        rogue = {
            "op": "lua_command",
            "action_id": "action-rogue",
            "group_id": GROUPS[0],
            "provenance": {},
            "command": "Off Group 1",
        }
        ctx = _load("examples/context.json")
        found = _blocking(check_capability(one_action_plan(rogue), ctx))
        assert found
        assert "lua_command" in _reasons(found)

    def test_schema_also_refuses_the_rogue_op(self, plan):
        """1차 방어도 실제로 거부하는지 쏜다 — 「스키마가 막는다」를 가정하지 않는다.

        **거짓 사유로 통과하지 않게** 규범 예제에 rogue op 하나만 주입한다. 손으로 짠 최소
        계획을 넣으면 상위 필드 부재 때문에 `UNSUPPORTED_SCHEMA_VERSION` 이 먼저 나서,
        rogue op 을 막지 않는 스키마에서도 이 시험이 통과한다 — 거절 사유가 둘 다 「거절」이라
        성공/실패 이분법으로는 안 잡힌다. 그래서 **코드를 단언**하고 양성 대조를 함께 둔다.
        """
        from server.director.models import ExchangeError, parse_exchange

        # 양성 대조 — 손대지 않은 예제는 통과한다. 계기가 무조건 거절하는 것이 아니다.
        parse_exchange(json.dumps(plan), environment="synthetic")

        rogue = dict(plan)
        rogue["cues"] = json.loads(json.dumps(plan["cues"]))
        rogue["cues"][0]["actions"][0] = {
            "op": "lua_command",
            "action_id": "action-rogue",
            "group_id": GROUPS[0],
            "provenance": plan["cues"][0]["actions"][0]["provenance"],
            "command": "Off Group 1",
        }
        with pytest.raises(ExchangeError) as raised:
            parse_exchange(json.dumps(rogue), environment="synthetic")
        assert raised.value.code == "SCHEMA_INVALID", (
            f"거절 사유가 rogue op 때문이 아니다: {raised.value.code}"
        )


# --------------------------------------------------------------------------- #
# 상시 사유 — emitter 실측 0건. 이것이 승격을 막는 자리다.
# --------------------------------------------------------------------------- #


class TestUnmeasuredEmitterIsTheStandingReason:
    def test_pan_and_tilt_are_the_only_observed_axes(self):
        """`AXIS_TIMING_OBSERVED` 가 `pan`·`tilt` 만 담는다 — C6 round 5(2026-09-16)의
        실기 관측(`Set Cue <n> Sequence <seq> Property 'Preset2Fade'/'Preset2Delay'
        <값>`, 다른 카드 t215 의 문법 재사용, `progress.md` §E.2 Evidence — P1 ④)이
        승격의 근거다. `intensity`·`color`·`beam`·`fx` 는 여전히 관측 0건이다.
        """
        from server.director.validate.capability import AXIS_TIMING_OBSERVED

        assert AXIS_TIMING_OBSERVED == ("pan", "tilt")

    def test_every_action_in_the_contract_example_is_blocked_except_the_reproducible_pair(
        self, plan, context
    ):
        """규범 예제는 capability 를 전부 지원한다고 광고하지만 그래도 막힌다 —

        **단, action-003·action-007 은 예외다.** 둘 다 `position_set` 이며 pan==tilt
        (둘 다 delay=0/fade=0)이라 `Preset2Fade`/`Preset2Delay` 로 충실히 재현된다(C6
        round 5, 위 참조). 그 뒤의 모든 `position_set`(action-017 이하)은 pan≠tilt 라
        (예: pan.delay_ms=0 vs tilt.delay_ms=200) 여전히 막힌다 — Position 이 preset
        type 하나뿐이라 다른 값을 나눠 담을 수 없기 때문이다.

        `LD-CAP-001` 이 광고의 근거를 *"실제 compiler+rig+target 출력"* 으로 못박았으므로,
        context 의 자기 신고를 근거로 쓰지 않는다 — 이 예외 둘도 신고가 아니라 실기
        관측이 근거다.
        """
        from server.director.validate.capability import check_capability

        found = check_capability(plan, context)
        pointers = {d.pointer for d in found if d.blocking}
        reproducible = {"/cues/0/actions/2", "/cues/0/actions/6"}
        expected = {
            f"/cues/{i}/actions/{j}"
            for i, c in enumerate(plan["cues"])
            for j in range(len(c["actions"]))
        } - reproducible
        assert expected <= pointers, "action 중 판정을 못 받은 것이 있다"
        assert reproducible.isdisjoint(pointers), (
            "관측되고 재현 가능한 action(pan==tilt==0)까지 여전히 막혔다 — 승격이 반영되지 않았다"
        )

    def test_reason_separates_missing_implementation_from_a_bad_plan(self, context):
        """사람이 「내 계획이 틀렸나」와 「아직 안 만들어졌나」를 구분할 수 있어야 한다."""
        from server.director.validate.capability import check_capability

        found = _blocking(
            check_capability(one_action_plan(intensity(GROUPS[0], 50, fade=2000)), context)
        )
        text = _reasons(found)
        assert "계획의 결함이 아닙니다" in text

    def test_resolution_is_unknown_so_exact_reproduction_is_unproven(self, context):
        """quantize 금지의 근거 — 최소 해상도가 실측 0건이라 정확 재현을 증명할 수 없다."""
        from server.director.validate.capability import check_capability

        found = _blocking(
            check_capability(one_action_plan(intensity(GROUPS[0], 50, fade=2000)), context)
        )
        assert "해상도" in _reasons(found)


# --------------------------------------------------------------------------- #
# 제한적 승격 — pan==tilt 일 때만 Position timing 이 관측된 것으로 본다
# --------------------------------------------------------------------------- #


class TestPositionTimingPromotionIsRestrictedToUniformValues:
    def test_uniform_pan_and_tilt_timing_is_no_longer_flagged_unobserved(self, context):
        """pan·tilt 가 같은 값이면 축별 timing 진단이 사라진다 — `Preset2Fade`/
        `Preset2Delay` 하나로 충실히 재현되기 때문이다(C6 round 5 실기 관측)."""
        from server.director.validate.capability import check_capability

        uniform = position(GROUPS[0], "pos-center", delay=500, fade=2000)
        found = _blocking(check_capability(one_action_plan(uniform), context))
        assert not found, f"pan==tilt 인데도 여전히 막혔다: {_reasons(found)}"

    def test_mismatched_pan_and_tilt_is_still_refused_with_a_distinct_reason(self, context):
        """pan≠tilt 는 여전히 막히지만, 「관측 0건」이 아니라 「값이 갈리면 못 나눈다」가
        사유여야 한다 — pan·tilt 자체는 이제 관측됐으므로 옛 사유는 더 이상 정확하지
        않다(사유가 원인별로 갈려야 한다는 이 파일의 원칙, `TestReasonsDistinguishCauses`
        와 같은 취지)."""
        from server.director.validate.capability import check_capability

        mismatched = position(GROUPS[0], "pos-center", delay=0, fade=2000)
        mismatched["timing"]["tilt"] = dict(mismatched["timing"]["tilt"], fade_ms=1200)
        found = _blocking(check_capability(one_action_plan(mismatched), context))
        text = _reasons(found)
        assert found, "pan≠tilt 인데 통과했다"
        assert "관측 0건" not in text, "pan·tilt 는 이제 관측됐다 — 옛 사유가 그대로 남았다"
        assert "Preset2Fade" in text or "Preset2Delay" in text

    def test_a_single_axis_alone_is_still_unobserved(self, context):
        """pan 만 선언하고 tilt 를 아예 안 든 요청은 여전히 미관측이다 — Position 은
        preset type 하나뿐이라 pan 하나만 따로 재현할 통로가 없다."""
        from server.director.validate.capability import check_capability

        partial = position(GROUPS[0], "pos-center", delay=0, fade=2000)
        del partial["timing"]["tilt"]
        found = _blocking(check_capability(one_action_plan(partial), context))
        assert found, "pan 하나만 선언했는데도 통과했다"
        assert "pan" in _reasons(found)


# --------------------------------------------------------------------------- #
# 판정 불능은 통과가 아니다 · 배선
# --------------------------------------------------------------------------- #


class TestUndecidableIsBlocking:
    def test_missing_context_is_blocking(self):
        from server.director.validate.capability import check_capability

        assert _blocking(check_capability(one_action_plan(intensity(GROUPS[0], 50)), None))

    def test_missing_context_still_yields_one_diagnostic_per_action(self):
        """context 가 없어도 **action 별로** 낸다.

        4단은 계약 §6.3 의 *"각 요청 action에는 적어도 하나의 diagnostic"* 을 채우는 자리다
        (`pipeline.py` 독스트링). 첫 판에서 root 진단 하나로 갈음했더니 C1 의 coverage 가드
        5건이 깨졌다 — 판정 불능이라는 사실이 coverage 면제가 되지 않는다.
        """
        from server.director.validate.capability import check_capability

        plan = make_plan(
            [
                cue("cue-a", 0, [intensity(GROUPS[0], 10), color(GROUPS[0])]),
                cue("cue-b", 1000, [beam(GROUPS[0])]),
            ],
            [terminal(GROUPS[0])],
            controlled=(GROUPS[0],),
        )
        pointers = {d.pointer for d in check_capability(plan, None)}
        assert pointers == {
            "/cues/0/actions/0",
            "/cues/0/actions/1",
            "/cues/1/actions/0",
        }

    def test_plan_without_actions_still_receives_a_verdict(self, context):
        from server.director.validate.capability import check_capability

        empty = make_plan([], [terminal(GROUPS[0])], controlled=(GROUPS[0],))
        assert _blocking(check_capability(empty, context))


class TestWiredIntoThePipeline:
    def test_stage_four_uses_capability_module(self, plan, context):
        """4단이 `check_capability` 를 부른다 — 자리표시자 문구가 남아 있지 않다."""
        from server.director.validate.pipeline import run_stages

        report = run_stages(plan, context)
        stage_four = [d for d in report.diagnostics if d["stage"] == "capability_fidelity"]
        assert stage_four
        assert all(d["blocking"] for d in stage_four), "C4 는 아무것도 열지 않는다"

    def test_stage_four_reasons_differ_by_cause(self, context):
        """배선이 실물인지 — 원인을 바꾸면 4단 진단 문면이 바뀐다."""
        from server.director.validate.pipeline import run_stages

        narrow = json.loads(json.dumps(context))
        for entry in narrow["capabilities"]:
            entry["operations"] = ["intensity_set"]

        plan = one_action_plan(color(GROUPS[0]))
        wide_reasons = {
            d["reason"]
            for d in run_stages(plan, context).diagnostics
            if d["rule_id"] == "LD-CAP-001"
        }
        narrow_reasons = {
            d["reason"]
            for d in run_stages(plan, narrow).diagnostics
            if d["rule_id"] == "LD-CAP-001"
        }
        assert wide_reasons != narrow_reasons

    def test_c1_invariant_holds_all_capability_diagnostics_block(self, plan, context):
        """C1 의 가드를 이 파일에서도 다시 쏜다 — 승격이 조용히 일어나지 않게."""
        from server.director.validate.diagnostics import STATUS_UNSUPPORTED
        from server.director.validate.pipeline import run_stages

        stage_four = [
            d for d in run_stages(plan, context).diagnostics if d["stage"] == "capability_fidelity"
        ]
        assert all(d["blocking"] for d in stage_four)
        assert all(d["status"] == STATUS_UNSUPPORTED for d in stage_four)


class TestNoConsoleAndNoArtisticImport:
    def test_module_does_not_import_osc_or_producers(self):
        import server.director.validate.capability as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "server.bridge" not in source
        assert "server.looks" not in source
        assert "server.web" not in source
