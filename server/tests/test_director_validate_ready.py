"""ready 판정 시험 — `LD-STATE-001`·`LD-STATE-002`·`LD-FX-001` (SPEC-LDCOMPILE-001 C3).

이 파일이 지키는 것은 둘이고 방향이 반대다.

1. **거부**: 누락 baseline·FX 생애 결함·terminal 불일치는 blocking 이다.
2. **통과**: 조용한 엔딩·동일 후렴 강도·반복 motif 는 **통과해야 한다.** `LD-STATE-002` 가
   이 셋을 유효하다고 명시했으므로, 이것이 빨간 것은 검증기가 정확한 것이 아니라 **예술
   정책을 주입한 것**이다 (`acceptance.md` AC-LDPLUGIN-010 음성 대조).

두 방향을 한 파일에 두는 이유: 거부만 있는 시험은 「넓게 잡을수록 좋아 보이는」 계기가 된다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_EXAMPLES = Path(__file__).resolve().parents[2] / ".moai/specs/SPEC-LDPLUGIN-001/examples"

GROUPS = ("group-front", "group-back")


def _load(name: str) -> dict[str, Any]:
    return json.loads((_EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def plan() -> dict[str, Any]:
    return _load("plan.json")


@pytest.fixture
def context() -> dict[str, Any]:
    return _load("context.json")


def _blocking(diagnostics: list[Any]) -> list[Any]:
    return [d for d in diagnostics if d.blocking]


def _rules(diagnostics: list[Any]) -> set[str]:
    return {d.rule_id for d in diagnostics}


# --------------------------------------------------------------------------- #
# 계획 조립 도구 — 최소 계획을 손으로 짠다. 규범 예제는 16 cue 60 action 이라
# 경계 하나를 흔들어 보기에는 너무 크다.
# --------------------------------------------------------------------------- #

_PROV = {
    "origin": "synthetic",
    "actor_ref": "test-fixture",
    "source_refs": ["src-fixture"],
    "evidence_refs": ["ev-music"],
    "rationale": "시험 고정물이며 실제 청취·콘솔 검증을 주장하지 않는다.",
}

_AID = [0]


def _next_aid() -> str:
    _AID[0] += 1
    return f"action-{_AID[0]:04d}"


def _timing(*axes: str, delay: int = 0, fade: int = 0) -> dict[str, Any]:
    return {axis: {"delay_ms": delay, "fade_ms": fade, "curve": "linear"} for axis in axes}


def intensity(group_id: str, pct: float, *, delay: int = 0, fade: int = 0) -> dict[str, Any]:
    return {
        "op": "intensity_set",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "value_pct": pct,
        "timing": _timing("intensity", delay=delay, fade=fade),
    }


def color(
    group_id: str, ref: str = "color-amber", *, delay: int = 0, fade: int = 0
) -> dict[str, Any]:
    return {
        "op": "color_set",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "preset_ref": ref,
        "timing": _timing("color", delay=delay, fade=fade),
    }


def position(
    group_id: str, ref: str = "pos-center", *, delay: int = 0, fade: int = 0
) -> dict[str, Any]:
    return {
        "op": "position_set",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "preset_ref": ref,
        "move_mode": "dark_move",
        "timing": _timing("pan", "tilt", delay=delay, fade=fade),
    }


def beam(group_id: str, ref: str = "beam-wash", *, delay: int = 0, fade: int = 0) -> dict[str, Any]:
    return {
        "op": "beam_set",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "preset_ref": ref,
        "timing": _timing("beam", delay=delay, fade=fade),
    }


def fx_start(
    group_id: str,
    instance_id: str,
    *,
    preset_ref: str = "fx-pulse",
    cycle_beats: float = 4,
    phase_beats: float = 0,
    delay: int = 0,
    fade: int = 0,
) -> dict[str, Any]:
    return {
        "op": "fx_start",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "instance_id": instance_id,
        "preset_ref": preset_ref,
        "cycle_beats": cycle_beats,
        "phase_beats": phase_beats,
        "timing": _timing("fx", delay=delay, fade=fade),
    }


def fx_stop(group_id: str, instance_id: str, *, delay: int = 0, fade: int = 0) -> dict[str, Any]:
    return {
        "op": "fx_stop",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "instance_id": instance_id,
        "timing": _timing("fx", delay=delay, fade=fade),
    }


def group_release(group_id: str, *, delay: int = 0, fade: int = 0) -> dict[str, Any]:
    return {
        "op": "group_release",
        "action_id": _next_aid(),
        "group_id": group_id,
        "provenance": _PROV,
        "timing": _timing("intensity", "color", "pan", "tilt", "beam", delay=delay, fade=fade),
    }


def baseline(
    group_id: str, *, pct: float = 0, delay: int = 0, fade: int = 0
) -> list[dict[str, Any]]:
    """4축 완전 baseline. `LD-STATE-001` 이 첫 cue 에 요구하는 것."""
    return [
        intensity(group_id, pct, delay=delay, fade=fade),
        color(group_id, delay=delay, fade=fade),
        position(group_id, delay=delay, fade=fade),
        beam(group_id, delay=delay, fade=fade),
    ]


def cue(
    cue_id: str, at_ms: int, actions: list[dict[str, Any]], section_id: str = "intro"
) -> dict[str, Any]:
    return {
        "cue_id": cue_id,
        "section_id": section_id,
        "at_ms": at_ms,
        "label": cue_id,
        "actions": actions,
        "provenance": _PROV,
    }


def terminal(
    group_id: str,
    *,
    intensity_pct: float = 0,
    color_ref: str = "color-amber",
    position_ref: str = "pos-center",
    beam_ref: str = "beam-wash",
    active_fx: list[str] | None = None,
    ownership: str = "held",
) -> dict[str, Any]:
    return {
        "group_id": group_id,
        "state": {
            "intensity_pct": intensity_pct,
            "color_ref": color_ref,
            "position_ref": position_ref,
            "beam_ref": beam_ref,
            "active_fx": active_fx if active_fx is not None else [],
            "ownership": ownership,
        },
    }


def make_plan(
    cues: list[dict[str, Any]],
    terminal_state: list[dict[str, Any]],
    *,
    controlled: tuple[str, ...] = GROUPS,
) -> dict[str, Any]:
    return {
        "message_type": "lighting_plan",
        "controlled_group_ids": list(controlled),
        "cues": cues,
        "terminal_state": terminal_state,
    }


def minimal_plan(**terminal_overrides: Any) -> dict[str, Any]:
    """모든 검사를 통과해야 하는 최소 계획 — 나머지 시험의 양성 대조 원본."""
    actions = baseline(GROUPS[0]) + baseline(GROUPS[1])
    return make_plan(
        [cue("cue-baseline", 0, actions)],
        [terminal(g, **terminal_overrides) for g in GROUPS],
    )


# --------------------------------------------------------------------------- #
# 양성 대조 — 계기가 아무것도 막지 않는 상태부터 확인한다
# --------------------------------------------------------------------------- #


class TestPositiveControl:
    def test_minimal_complete_plan_passes(self):
        from server.director.validate.simulate import check_ready

        assert _blocking(check_ready(minimal_plan())) == []

    def test_contract_example_passes(self, plan):
        """규범 예제(16 cue · 60 action · FX 4쌍)가 ready 판정을 통과한다."""
        from server.director.validate.simulate import check_ready

        assert _blocking(check_ready(plan)) == []

    def test_every_action_receives_a_diagnostic_free_pass(self):
        """통과해도 진단은 나온다 — 조용한 수용은 이 층에서 합법이 아니다."""
        from server.director.validate.simulate import check_ready

        assert check_ready(minimal_plan()) != []


# --------------------------------------------------------------------------- #
# 음성 대조 (필수) — 예술 정책 주입 탐지. 이 셋이 빨간 것은 계기의 결함이다.
# --------------------------------------------------------------------------- #


class TestArtisticPolicyIsNotInjected:
    def test_quiet_ending_passes(self):
        """조용한 엔딩 — outro intensity 가 낮다. `role=outro` 를 이유로 올리면 FAIL."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0], pct=80) + baseline(GROUPS[1], pct=80)),
                cue(
                    "cue-outro",
                    60000,
                    [intensity(GROUPS[0], 3), intensity(GROUPS[1], 2)],
                    section_id="outro",
                ),
            ],
            [terminal(GROUPS[0], intensity_pct=3), terminal(GROUPS[1], intensity_pct=2)],
        )
        assert _blocking(check_ready(plan)) == []

    def test_identical_chorus_intensity_passes(self):
        """두 후렴의 강도가 동일하다. 변주를 강제하면 FAIL."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-chorus-1", 30000, [intensity(g, 75) for g in GROUPS], section_id="chorus"),
                cue("cue-verse-2", 50000, [intensity(g, 40) for g in GROUPS], section_id="verse"),
                cue("cue-chorus-2", 70000, [intensity(g, 75) for g in GROUPS], section_id="chorus"),
            ],
            [terminal(g, intensity_pct=75) for g in GROUPS],
        )
        assert _blocking(check_ready(plan)) == []

    def test_repeated_motif_passes(self):
        """같은 preset 을 반복해서 쓴다. 반복 자체를 결함으로 보면 FAIL."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-hit-1", 20000, [color(g, "color-blue") for g in GROUPS]),
                cue("cue-hit-2", 40000, [color(g, "color-blue") for g in GROUPS]),
                cue("cue-hit-3", 60000, [color(g, "color-blue") for g in GROUPS]),
            ],
            [terminal(g, color_ref="color-blue") for g in GROUPS],
        )
        assert _blocking(check_ready(plan)) == []


# --------------------------------------------------------------------------- #
# `LD-STATE-001` — 누락은 hold, 첫 cue 는 완전한 baseline
# --------------------------------------------------------------------------- #


class TestBaselineCompleteness:
    @pytest.mark.parametrize("dropped", ["intensity_set", "color_set", "position_set", "beam_set"])
    def test_missing_axis_in_first_cue_is_blocking(self, dropped):
        from server.director.validate.simulate import check_ready

        actions = [a for a in baseline(GROUPS[0]) + baseline(GROUPS[1]) if a["op"] != dropped]
        plan = make_plan([cue("cue-baseline", 0, actions)], [terminal(g) for g in GROUPS])
        diagnostics = _blocking(check_ready(plan))
        assert diagnostics, f"{dropped} 누락이 막히지 않았다"
        assert "LD-STATE-001" in _rules(diagnostics)

    def test_missing_group_in_first_cue_is_blocking(self):
        """controlled group 하나가 첫 cue 에 없으면 blocking — 「전부」가 조건이다."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [cue("cue-baseline", 0, baseline(GROUPS[0]))],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-STATE-001" in _rules(_blocking(check_ready(plan)))

    def test_baseline_split_across_two_cues_is_blocking(self):
        """첫 cue 가 조건이다 — 두 번째 cue 로 미루면 그 사이가 미지 상태다."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0])),
                cue("cue-late", 1000, baseline(GROUPS[1])),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-STATE-001" in _rules(_blocking(check_ready(plan)))

    def test_empty_cues_is_blocking(self):
        """schema-valid 빈 배열은 draft 만 허용한다 — ready 판정 대상이 아니다."""
        from server.director.validate.simulate import check_ready

        assert _blocking(check_ready(make_plan([], [terminal(g) for g in GROUPS])))

    def test_active_fx_in_first_cue_is_blocking(self):
        """첫 cue 에서 FX 를 켜면 「active FX 없음」 사전조건이 깨진다."""
        from server.director.validate.simulate import check_ready

        actions = baseline(GROUPS[0]) + baseline(GROUPS[1])
        actions.insert(0, fx_start(GROUPS[0], "pulse-early"))
        plan = make_plan(
            [
                cue("cue-baseline", 0, actions),
                cue("cue-stop", 10000, [fx_stop(GROUPS[0], "pulse-early")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-STATE-001" in _rules(_blocking(check_ready(plan)))


class TestMissingAxisIsHoldNotInherited:
    def test_unwritten_axis_holds_the_declared_baseline(self):
        """baseline 뒤 intensity 만 바꾸면 나머지 셋은 baseline 값을 유지한다."""
        from server.director.validate.simulate import simulate

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0], pct=10) + baseline(GROUPS[1], pct=10)),
                cue("cue-up", 5000, [intensity(GROUPS[0], 90)]),
            ],
            [terminal(GROUPS[0], intensity_pct=90), terminal(GROUPS[1], intensity_pct=10)],
        )
        states = simulate(plan)
        assert states[GROUPS[0]].intensity_pct == 90
        assert states[GROUPS[0]].color_ref == "color-amber"
        assert states[GROUPS[1]].intensity_pct == 10

    def test_never_declared_axis_is_none_not_a_safe_state_guess(self):
        """선언되지 않은 축은 `None` 이다 — group 의 `safe_state` 를 상속하지 않는다.

        상속하면 baseline 누락이 진단 없이 사라진다. 이것이 `LD-STATE-001` 의
        *"이전 show/programmer state 를 상속하지 않는다"* 가 막는 실패다.
        """
        from server.director.validate.simulate import simulate

        plan = make_plan(
            [cue("cue-partial", 0, [intensity(GROUPS[0], 50)])],
            [terminal(GROUPS[0])],
            controlled=(GROUPS[0],),
        )
        state = simulate(plan)[GROUPS[0]]
        assert state.intensity_pct == 50
        assert state.color_ref is None
        assert state.position_ref is None
        assert state.beam_ref is None


# --------------------------------------------------------------------------- #
# `LD-FX-001` — instance 생애
# --------------------------------------------------------------------------- #


class TestFxLifecycle:
    def test_start_without_stop_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-fx", 10000, [fx_start(GROUPS[0], "pulse-a")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))

    def test_stop_without_start_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-fx", 10000, [fx_stop(GROUPS[0], "ghost")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))

    def test_stop_before_start_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-stop", 10000, [fx_stop(GROUPS[0], "pulse-a")]),
                cue("cue-start", 20000, [fx_start(GROUPS[0], "pulse-a")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))

    def test_duplicate_start_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-a", 10000, [fx_start(GROUPS[0], "pulse-a")]),
                cue("cue-b", 20000, [fx_start(GROUPS[0], "pulse-a")]),
                cue("cue-c", 30000, [fx_stop(GROUPS[0], "pulse-a")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))

    def test_duplicate_stop_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-a", 10000, [fx_start(GROUPS[0], "pulse-a")]),
                cue("cue-b", 20000, [fx_stop(GROUPS[0], "pulse-a")]),
                cue("cue-c", 30000, [fx_stop(GROUPS[0], "pulse-a")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))

    def test_group_mismatch_between_start_and_stop_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-a", 10000, [fx_start(GROUPS[0], "pulse-a")]),
                cue("cue-b", 20000, [fx_stop(GROUPS[1], "pulse-a")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))

    def test_matched_pair_passes(self):
        """양성 대조 — 짝이 맞는 한 쌍은 통과한다."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-a", 10000, [fx_start(GROUPS[0], "pulse-a")]),
                cue("cue-b", 20000, [fx_stop(GROUPS[0], "pulse-a")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert _blocking(check_ready(plan)) == []

    def test_same_instance_id_in_two_groups_is_blocking(self):
        """`instance_id` 는 **plan 전체에서** 유일하다 — group 별 유일이 아니다."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-a", 10000, [fx_start(GROUPS[0], "pulse"), fx_start(GROUPS[1], "pulse")]),
                cue("cue-b", 20000, [fx_stop(GROUPS[0], "pulse"), fx_stop(GROUPS[1], "pulse")]),
            ],
            [terminal(g) for g in GROUPS],
        )
        assert "LD-FX-001" in _rules(_blocking(check_ready(plan)))


# --------------------------------------------------------------------------- #
# `LD-STATE-002` — terminal 정확 일치
# --------------------------------------------------------------------------- #


class TestTerminalState:
    def test_active_fx_non_empty_in_terminal_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1]))],
            [terminal(GROUPS[0], active_fx=["pulse-a"]), terminal(GROUPS[1])],
        )
        assert _blocking(check_ready(plan))

    @pytest.mark.parametrize(
        "field,value",
        [
            ("intensity_pct", 99),
            ("color_ref", "color-blue"),
            ("position_ref", "pos-wide"),
            ("beam_ref", "beam-narrow"),
        ],
    )
    def test_terminal_mismatch_is_blocking(self, field, value):
        """축 하나라도 다르면 blocking — 감독 판정: 계약 문면대로 「정확히 일치」."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1]))],
            [terminal(GROUPS[0], **{field: value}), terminal(GROUPS[1])],
        )
        assert "LD-STATE-002" in _rules(_blocking(check_ready(plan)))

    def test_missing_terminal_entry_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1]))],
            [terminal(GROUPS[0])],
        )
        assert "LD-STATE-002" in _rules(_blocking(check_ready(plan)))

    def test_duplicate_terminal_entry_is_blocking(self):
        """모든 controlled group 에 **정확히 하나**."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1]))],
            [terminal(GROUPS[0]), terminal(GROUPS[0]), terminal(GROUPS[1])],
        )
        assert "LD-STATE-002" in _rules(_blocking(check_ready(plan)))

    def test_terminal_entry_for_uncontrolled_group_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1]))],
            [terminal(GROUPS[0]), terminal(GROUPS[1]), terminal("group-stranger")],
        )
        assert "LD-STATE-002" in _rules(_blocking(check_ready(plan)))


class TestReleaseAndReentry:
    def test_reuse_after_release_without_full_baseline_is_blocking(self):
        """첫 release 이후 부분 재진입은 blocking (`AC-LDPLUGIN-010` 6번)."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-release", 10000, [group_release(GROUPS[0])]),
                cue("cue-partial", 20000, [intensity(GROUPS[0], 50)]),
            ],
            [terminal(GROUPS[0], intensity_pct=50), terminal(GROUPS[1])],
        )
        assert "LD-STATE-001" in _rules(_blocking(check_ready(plan)))

    def test_reuse_after_release_with_full_baseline_passes(self):
        """양성 대조 — 완전한 baseline 을 다시 선언하면 통과한다."""
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-release", 10000, [group_release(GROUPS[0])]),
                cue("cue-reenter", 20000, baseline(GROUPS[0], pct=50)),
            ],
            [terminal(GROUPS[0], intensity_pct=50), terminal(GROUPS[1])],
        )
        assert _blocking(check_ready(plan)) == []

    def test_released_group_reports_released_ownership(self):
        from server.director.validate.simulate import check_ready, simulate

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-release", 10000, [group_release(GROUPS[0])]),
            ],
            [terminal(GROUPS[0], ownership="released"), terminal(GROUPS[1])],
        )
        assert simulate(plan)[GROUPS[0]].ownership == "released"
        assert _blocking(check_ready(plan)) == []

    def test_ownership_mismatch_is_blocking(self):
        from server.director.validate.simulate import check_ready

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUPS[0]) + baseline(GROUPS[1])),
                cue("cue-release", 10000, [group_release(GROUPS[0])]),
            ],
            [terminal(GROUPS[0], ownership="held"), terminal(GROUPS[1])],
        )
        assert "LD-STATE-002" in _rules(_blocking(check_ready(plan)))


# --------------------------------------------------------------------------- #
# 계기가 공허하지 않다는 확인 — 검사 밖 필드를 흔들면 통과해야 한다
# --------------------------------------------------------------------------- #


class TestScopeIsNotOverbroad:
    def test_label_change_does_not_block(self):
        """음성 대조 — 이 검사가 보지 않는 필드를 바꿔도 blocking 이 생기지 않는다."""
        from server.director.validate.simulate import check_ready

        plan = minimal_plan()
        plan["cues"][0]["label"] = "완전히 다른 라벨"
        plan["title"] = "무관한 제목"
        assert _blocking(check_ready(plan)) == []

    def test_section_role_does_not_change_the_verdict(self):
        """`section_id` 를 바꿔도 판정이 같다 — 구간 이름으로 예술 판정을 하지 않는다."""
        from server.director.validate.simulate import check_ready

        for section in ("intro", "chorus", "outro", "bridge"):
            plan = minimal_plan()
            plan["cues"][0]["section_id"] = section
            assert _blocking(check_ready(plan)) == [], section


# --------------------------------------------------------------------------- #
# 배선 — 부품이 초록이어도 경로가 안 이어지면 판정에 도달하지 않는다
# --------------------------------------------------------------------------- #


class TestWiredIntoThePipeline:
    def test_stage_three_reports_ready_failures(self, plan, context):
        """3단이 `simulate` 를 실제로 부른다 — baseline 을 깨면 진단에 나타난다."""
        from server.director.validate.pipeline import run_stages

        broken = json.loads(json.dumps(plan))
        broken["cues"][0]["actions"] = [
            a for a in broken["cues"][0]["actions"] if a["op"] != "beam_set"
        ]
        report = run_stages(broken, context)
        rules = {d["rule_id"] for d in report.diagnostics if d["blocking"]}
        assert "LD-STATE-001" in rules

    def test_stage_three_is_not_a_placeholder(self, plan, context):
        """자리표시자 문구가 남아 있지 않다."""
        from server.director.validate.pipeline import run_stages

        report = run_stages(plan, context)
        reasons = " ".join(d["reason"] for d in report.diagnostics)
        assert "C3 의 simulation 이 이 자리에서 수행합니다" not in reasons

    def test_rounding_conflicts_has_a_non_test_caller(self):
        """C2 가 남긴 빚 — `rounding_conflicts` 가 경로에 이어졌다.

        부품으로만 초록인 검사는 판정에 도달하지 않는다. 시험 아닌 호출자를 센다.
        """
        import subprocess

        out = subprocess.run(
            ["grep", "-rn", "rounding_conflicts(", "server", "--include=*.py"],
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        callers = [
            line for line in out if "/tests/" not in line and "def rounding_conflicts(" not in line
        ]
        assert callers, "비테스트 호출자가 0건이다 — 검사가 경로에 이어지지 않았다"
        # 여는 괄호를 요구하는 이유: 이 단언의 첫 판은 `rounding_conflicts` 만 찾아서
        # `timing.py:14` 의 **독스트링 언급**을 호출자로 셌고, 구현 전에 통과했다.
        # 도달 가능성은 정당화가 아니다 — 호출을 세야 한다.
