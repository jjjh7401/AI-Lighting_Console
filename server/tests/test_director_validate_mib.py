"""dark move·재진입 거부 시험 — `LD-MIB-001`·`LD-REENTRY-001` (SPEC-LDCOMPILE-001 C5).

계약 §8 의 두 조항이며 성격이 다르다.

- `LD-MIB-001` — **증명 부담이 계획 쪽에 있다.** dark move 는 *"movement 시작부터 pan/tilt 의
  늦은 완료 + `settle_ms` 까지 intensity=0 및 intensity FX 없음이 증명되어야"* 한다. 「어둡지
  않다는 증거가 없다」가 아니라 「어둡다는 증거가 있어야」 통과다 — 부재가 통과가 되면
  무대에서 빔이 지나간다.
- `LD-REENTRY-001` — **광고를 검증한다.** `random_access` 는 계획의 필드가 아니라 context 의
  capability 신고다. 재현이 관측되지 않았으면 `true` 로 서 있을 수 없다. C4 가 이 축을 남겨
  두었고(진단 0건) 여기서 닫는다.

두 조항 모두 C4 와 같은 금지를 진다: **reveal 시각을 미뤄 맞추지 않는다.** 그래서 진단은
대체안을 내지 않고, 계약이 적은 두 갈래(원점을 확장한 새 audio/context · 사람이 사전 준비한
verified baseline)를 요청으로만 담는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.tests.test_director_validate_ready import (
    GROUPS,
    baseline,
    cue,
    fx_start,
    fx_stop,
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


def _rules(diagnostics: list[Any]) -> set[str]:
    return {d.rule_id for d in diagnostics}


def _reasons(diagnostics: list[Any]) -> str:
    return " ".join(d.reason for d in diagnostics)


GROUP = GROUPS[0]


def dark_context(*, settle_ms: int = 800, random_access: bool = False) -> dict[str, Any]:
    """`pos-wide` 의 `settle_ms` 와 `random_access` 신고만 흔드는 최소 context."""
    ctx = _load("examples/context.json")
    for preset in ctx["presets"]:
        if preset["preset_id"] == "pos-wide":
            preset["settle_ms"] = settle_ms
    for entry in ctx["capabilities"]:
        entry["random_access"] = random_access
    return ctx


def dark_plan(
    *,
    move_at_ms: int = 10000,
    delay: int = 0,
    fade: int = 2000,
    intensity_actions: list[dict[str, Any]] | None = None,
    fx: list[dict[str, Any]] | None = None,
    move_mode: str = "dark_move",
) -> dict[str, Any]:
    """baseline(intensity 0) 뒤에 dark move 하나. 추가 action 을 끼워 창을 흔든다."""
    move = position(GROUP, "pos-wide", delay=delay, fade=fade)
    move["move_mode"] = move_mode
    cues = [
        cue("cue-baseline", 0, baseline(GROUP, pct=0)),
        cue("cue-move", move_at_ms, [move]),
    ]
    for extra in intensity_actions or []:
        cues.append(cue(f"cue-extra-{len(cues)}", extra.pop("_at_ms"), [extra]))
    for extra in fx or []:
        cues.append(cue(f"cue-fx-{len(cues)}", extra.pop("_at_ms"), [extra]))
    return make_plan(cues, [terminal(GROUP, position_ref="pos-wide")], controlled=(GROUP,))


def at(action: dict[str, Any], at_ms: int) -> dict[str, Any]:
    action["_at_ms"] = at_ms
    return action


# --------------------------------------------------------------------------- #
# 양성 대조 먼저 — 증명이 서는 계획은 통과한다
# --------------------------------------------------------------------------- #


class TestPositiveControl:
    def test_provably_dark_move_passes(self):
        """baseline 이 intensity 0 이고 창 안에 아무 변경이 없으면 통과한다."""
        from server.director.validate.mib import check_dark_move

        assert _blocking(check_dark_move(dark_plan(), dark_context())) == []

    def test_live_move_is_not_subject_to_the_dark_window(self):
        """`move_mode=live` 는 이 조항의 대상이 아니다 — 넓게 잡으면 정상 계획이 막힌다."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(
            move_mode="live",
            intensity_actions=[at(intensity(GROUP, 80), 10500)],
        )
        assert _blocking(check_dark_move(plan, dark_context())) == []

    def test_intensity_restored_after_the_window_passes(self):
        """창이 끝난 뒤 올리는 것은 허용 — reveal 은 창 밖이다.

        창은 `[10000, 10000+2000+800) = [10000, 12800)`. 12800ms 에 올린다.
        """
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 12800)])
        assert _blocking(check_dark_move(plan, dark_context())) == []


# --------------------------------------------------------------------------- #
# `LD-MIB-001` — 창의 경계
# --------------------------------------------------------------------------- #


class TestDarkWindowBoundary:
    def test_intensity_up_inside_the_window_is_blocking(self):
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 11000)])
        found = _blocking(check_dark_move(plan, dark_context()))
        assert "LD-MIB-001" in _rules(found)

    def test_one_ms_before_the_window_ends_is_blocking(self):
        """경계 바깥을 쏜다 — 12799ms 는 아직 창 안이다."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 12799)])
        assert "LD-MIB-001" in _rules(_blocking(check_dark_move(plan, dark_context())))

    def test_settle_ms_extends_the_window(self):
        """`settle_ms` 가 창을 늘린다 — 같은 계획이 settle 0 이면 통과한다.

        이것이 `settle_ms` 가 이 층에서 하는 유일한 일이며, C4 가 예약 구간에 넣지 않은
        이유이기도 하다: reveal 전 정착시간은 충돌이 아니라 **어둠의 길이**다.
        """
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 12500)])
        assert "LD-MIB-001" in _rules(_blocking(check_dark_move(plan, dark_context(settle_ms=800))))
        assert _blocking(check_dark_move(plan, dark_context(settle_ms=0))) == []

    def test_delay_shifts_the_window_start(self):
        """movement 는 `at_ms + delay` 에 시작한다 — delay 구간은 아직 어둡지 않아도 된다."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(delay=3000, intensity_actions=[at(intensity(GROUP, 0), 11000)])
        assert _blocking(check_dark_move(plan, dark_context())) == []

    def test_a_fade_crossing_into_the_window_is_blocking(self):
        """창 앞에서 시작해 창 안으로 이어지는 fade 는 「0 임이 증명되지 않는다」."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 0, fade=4000), 8000)])
        assert "LD-MIB-001" in _rules(_blocking(check_dark_move(plan, dark_context())))

    def test_nonzero_baseline_is_blocking(self):
        """증명 부담이 계획 쪽에 있다 — baseline 이 0 이 아니면 창 전체가 미증명이다."""
        from server.director.validate.mib import check_dark_move

        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUP, pct=60)),
                cue("cue-move", 10000, [dict(position(GROUP, "pos-wide", fade=2000))]),
            ],
            [terminal(GROUP, intensity_pct=60, position_ref="pos-wide")],
            controlled=(GROUP,),
        )
        plan["cues"][1]["actions"][0]["move_mode"] = "dark_move"
        assert "LD-MIB-001" in _rules(_blocking(check_dark_move(plan, dark_context())))

    def test_never_declared_intensity_is_blocking(self):
        """선언되지 않은 intensity 를 0 으로 가정하지 않는다 — 부재는 증명이 아니다."""
        from server.director.validate.mib import check_dark_move

        move = position(GROUP, "pos-wide", fade=2000)
        move["move_mode"] = "dark_move"
        plan = make_plan([cue("cue-move", 0, [move])], [terminal(GROUP)], controlled=(GROUP,))
        assert "LD-MIB-001" in _rules(_blocking(check_dark_move(plan, dark_context())))

    def test_later_axis_completion_defines_the_window_end(self):
        """pan·tilt 중 **늦은** 완료가 창의 끝이다 — 빠른 쪽으로 재면 창이 짧아진다."""
        from server.director.validate.mib import check_dark_move

        move = position(GROUP, "pos-wide")
        move["move_mode"] = "dark_move"
        move["timing"] = {
            "pan": {"delay_ms": 0, "fade_ms": 500, "curve": "linear"},
            "tilt": {"delay_ms": 0, "fade_ms": 4000, "curve": "linear"},
        }
        plan = make_plan(
            [
                cue("cue-baseline", 0, baseline(GROUP, pct=0)),
                cue("cue-move", 10000, [move]),
                cue("cue-up", 13000, [intensity(GROUP, 80)]),
            ],
            [terminal(GROUP, intensity_pct=80, position_ref="pos-wide")],
            controlled=(GROUP,),
        )
        # tilt 로 재면 창은 [10000, 14800) 이라 13000 은 안에 있다.
        # pan 으로 재면 [10000, 11300) 이라 통과해 버린다.
        assert "LD-MIB-001" in _rules(_blocking(check_dark_move(plan, dark_context())))


class TestIntensityFxInTheWindow:
    def test_intensity_fx_active_in_the_window_is_blocking(self):
        """`fx-pulse` 는 intensity 축을 쓴다 — 창 안에서 살아 있으면 blocking."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(
            fx=[at(fx_start(GROUP, "pulse-a"), 9000), at(fx_stop(GROUP, "pulse-a"), 13000)]
        )
        found = _blocking(check_dark_move(plan, dark_context()))
        assert "LD-MIB-001" in _rules(found)
        assert "pulse-a" in _reasons(found)

    def test_non_intensity_fx_does_not_block(self):
        """구멍도 잰다 — pan·tilt 만 쓰는 FX 는 어둠을 깨지 않는다."""
        from server.director.validate.mib import check_dark_move

        ctx = dark_context()
        for preset in ctx["presets"]:
            if preset["preset_id"] == "fx-pulse":
                preset["affects_axes"] = ["pan", "tilt"]
        plan = dark_plan(
            fx=[at(fx_start(GROUP, "pulse-a"), 9000), at(fx_stop(GROUP, "pulse-a"), 13000)]
        )
        assert _blocking(check_dark_move(plan, ctx)) == []

    def test_fx_stopped_before_the_window_does_not_block(self):
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(
            fx=[at(fx_start(GROUP, "pulse-a"), 5000), at(fx_stop(GROUP, "pulse-a"), 9000)]
        )
        assert _blocking(check_dark_move(plan, dark_context())) == []


class TestNoRevealShiftIsProposed:
    def test_diagnostic_does_not_propose_moving_the_reveal(self):
        """*"visible reveal 시각을 미뤄 맞추지 않는다"* — 대체안을 내지 않는다."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 11000)])
        found = check_dark_move(plan, dark_context())
        for diagnostic in found:
            assert diagnostic.to_internal()["after"] == {"present": False}

    def test_diagnostic_names_the_two_contract_routes(self):
        """계약이 적은 두 갈래를 요청으로 담는다 — 이 버전에 음수 필드가 없기 때문이다."""
        from server.director.validate.mib import check_dark_move

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 11000)])
        text = _reasons(_blocking(check_dark_move(plan, dark_context())))
        assert "audio" in text or "원점" in text
        assert "baseline" in text

    def test_no_negative_ms_is_ever_emitted(self):
        """compiler 준비 동작에 음수 ms 를 쓰지 않는다 — 창 계산에도 음수가 없다."""
        from server.director.validate.mib import dark_windows

        windows = dark_windows(dark_plan(delay=0, fade=2000), dark_context())
        assert windows
        for window in windows:
            assert window.start_ms >= 0
            assert window.end_ms >= window.start_ms


# --------------------------------------------------------------------------- #
# `LD-REENTRY-001` — 광고를 검증한다 (C4 가 남긴 구멍)
# --------------------------------------------------------------------------- #


class TestRandomAccessAdvertisement:
    def test_advertised_true_is_blocking_without_observation(self):
        """재현이 관측되지 않았으면 `random_access=true` 로 서 있을 수 없다."""
        from server.director.validate.mib import check_random_access

        found = _blocking(check_random_access(dark_plan(), dark_context(random_access=True)))
        assert "LD-REENTRY-001" in _rules(found)
        assert GROUP in _reasons(found)

    def test_advertised_false_is_not_a_defect(self):
        """구멍도 잰다 — 정직하게 `false` 라고 적은 것은 결함이 아니다."""
        from server.director.validate.mib import check_random_access

        assert _blocking(check_random_access(dark_plan(), dark_context(random_access=False))) == []

    def test_contract_example_advertises_true_and_is_refused(self, plan, context):
        """규범 예제는 `random_access=true` 로 광고한다 — 그래서 막힌다."""
        from server.director.validate.mib import check_random_access

        assert all(e["random_access"] for e in context["capabilities"])
        assert _blocking(check_random_access(plan, context))

    def test_nothing_is_observed_yet(self):
        """`RANDOM_ACCESS_OBSERVED` 가 비어 있다 — 채우는 것이 승격이고 근거는 실기다."""
        from server.director.validate.mib import RANDOM_ACCESS_OBSERVED

        assert RANDOM_ACCESS_OBSERVED == ()

    def test_reason_separates_advertisement_from_a_bad_plan(self):
        """계획의 결함이 아니라 광고의 근거 부족임을 말한다."""
        from server.director.validate.mib import check_random_access

        text = _reasons(
            _blocking(check_random_access(dark_plan(), dark_context(random_access=True)))
        )
        assert "계획의 결함이 아닙니다" in text


# --------------------------------------------------------------------------- #
# 판정 불능은 통과가 아니다
# --------------------------------------------------------------------------- #


class TestUndecidableIsBlocking:
    def test_missing_context_is_blocking(self):
        from server.director.validate.mib import check_dark_move, check_random_access

        assert _blocking(check_dark_move(dark_plan(), None))
        assert _blocking(check_random_access(dark_plan(), None))

    def test_absent_position_preset_is_blocking_not_settle_zero(self):
        """preset 을 못 찾으면 `settle_ms` 를 0 으로 가정하지 않는다 — 창이 짧아진다."""
        from server.director.validate.mib import check_dark_move

        ctx = dark_context()
        ctx["presets"] = [p for p in ctx["presets"] if p["preset_id"] != "pos-wide"]
        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 12500)])
        assert _blocking(check_dark_move(plan, ctx))

    def test_absent_fx_preset_is_blocking_not_axisless(self):
        """FX preset 부재를 「축 없음」으로 두지 않는다 — 어둠이 조용히 통과한다."""
        from server.director.validate.mib import check_dark_move

        ctx = dark_context()
        ctx["presets"] = [p for p in ctx["presets"] if p["preset_id"] != "fx-pulse"]
        plan = dark_plan(
            fx=[at(fx_start(GROUP, "pulse-a"), 9000), at(fx_stop(GROUP, "pulse-a"), 13000)]
        )
        assert _blocking(check_dark_move(plan, ctx))


# --------------------------------------------------------------------------- #
# 배선
# --------------------------------------------------------------------------- #


class TestWiredIntoThePipeline:
    def test_stage_five_reports_dark_move_failures(self):
        """5단이 `check_dark_move` 를 실제로 부른다."""
        from server.director.validate.pipeline import run_stages

        plan = dark_plan(intensity_actions=[at(intensity(GROUP, 80), 11000)])
        report = run_stages(plan, dark_context())
        rules = {d["rule_id"] for d in report.diagnostics if d["blocking"]}
        assert "LD-MIB-001" in rules

    def test_stage_five_reports_random_access_advertisement(self):
        from server.director.validate.pipeline import run_stages

        report = run_stages(dark_plan(), dark_context(random_access=True))
        rules = {d["rule_id"] for d in report.diagnostics if d["blocking"]}
        assert "LD-REENTRY-001" in rules

    def test_stage_five_actually_judges_not_just_announces(self, plan, context):
        """5단이 판정을 낸다 — 「도달했습니다」 수용 하나로 끝나지 않는다.

        첫 판은 *"'safety 단계에 도달했습니다' 가 없어야 한다"* 로 썼는데, 그 문장은
        **일부러 남긴** SafetyGate 소유 진술이며 바로 아래 시험이 그 존재를 요구한다 —
        내 시험 둘이 서로 모순이었다. 자리표시자 판별은 문구의 부재가 아니라 **판정의
        존재**로 해야 한다.
        """
        from server.director.validate.pipeline import run_stages

        rules = {
            d["rule_id"] for d in run_stages(plan, context).diagnostics if d["stage"] == "safety"
        }
        assert rules - {"LD-SAFE-001"}, "5단이 LD-SAFE-001 수용 하나만 낸다 — 판정이 없다"
        assert "LD-REENTRY-001" in rules

    def test_safety_gate_ownership_is_still_stated(self, plan, context):
        """5단이 실행 층의 SafetyGate 를 우회하지 않는다는 문장은 남아야 한다."""
        from server.director.validate.pipeline import run_stages

        report = run_stages(plan, context)
        reasons = " ".join(d["reason"] for d in report.diagnostics)
        assert "SafetyGate" in reasons


class TestNoConsoleAndNoArtisticImport:
    def test_module_does_not_import_osc_or_producers(self):
        import server.director.validate.mib as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "server.bridge" not in source
        assert "server.looks" not in source
        assert "server.web" not in source
