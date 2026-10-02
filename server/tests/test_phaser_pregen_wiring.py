"""SPEC-LDRENDER-001 M6(REQ-LDRENDER-011, 카드 t501) —
``ChatSession._pregenerate_missing_phasers`` 배선 단위 시험. 콘솔 접촉 0건
— 가짜 레지스트리만. 세 갈래:

  - 요청됨 + 풀 미점유 -> 번들이 기존 ``run_commands`` 게이트(``risk=``)를
    거쳐 디스패치되고, 성공하면 ``resolved`` 에 새 ``(pool, slot)`` 이 병합.
  - ``cue.fx.permitted`` 가 비면(예산 0) 시도조차 하지 않는다 — 콘솔 쓰기 0건.
  - 충돌(``VALUE_LINE_COLLISION``/``PRESET_OCCUPIED``)은 FXLIB 기존 사유
    그대로 ``failed`` 에 남고, ``resolved`` 는 건드리지 않는다(덮어쓰기 없음).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.song_cue_composer import CueFxData
from server.llm.types import ToolCall, ToolResult
from server.orchestrator.tools import CommandOutcome, ToolExecution
from server.safety.gate import BatchRisk
from server.web.session import ChatSession


@dataclass(frozen=True)
class _Dimmer:
    key_pct: float | None = 60.0
    blackout: bool = False


@dataclass(frozen=True)
class _Cue:
    kind: str
    cue_name: str
    dimmer: _Dimmer
    fx: CueFxData


@dataclass(frozen=True)
class _Bundle:
    cues: tuple


def _cue(cue_name: str, *, permitted: tuple[str, ...]) -> _Cue:
    fx = CueFxData(requested=permitted, permitted=permitted, disabled=(), density=0, axis_budget=0)
    return _Cue(kind="section", cue_name=cue_name, dimmer=_Dimmer(), fx=fx)


class _PregenStub:
    """``_pregenerate_missing_phasers`` 가 실제로 쓰는 네 자리만 채운 대역."""

    def __init__(self, *, pool_no=4, children=None, dispatch_ok=True, dispatch_detail="OK"):
        self._rig_paths: dict[str, str] = {}
        self._pool_no = pool_no
        self._children = {} if children is None else children
        self._dispatch_ok = dispatch_ok
        self._dispatch_detail = dispatch_detail
        self.dispatched: list[ToolCall] = []
        self.risks: list[BatchRisk] = []

    def _resolve_named_pool_no(self, name, *, probe_id):
        return self._pool_no

    def _paged_pool_children(self, path, *, probe_id):
        return self._children

    def _dispatch_declared(self, call: ToolCall, *, risk):
        self.dispatched.append(call)
        self.risks.append(risk)
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=self._dispatch_detail,
                is_error=not self._dispatch_ok,
            ),
            command_outcomes=(CommandOutcome(command="Store Preset 4.1", status="proposal"),),
        )


_PREGEN = ChatSession._pregenerate_missing_phasers


class TestSkipsWhenNoBudget:
    def test_a_label_with_empty_fx_permitted_is_never_attempted(self):
        stub = _PregenStub()
        bundle = _Bundle(cues=(_cue("후렴", permitted=()),))
        resolved, failed = _PREGEN(
            stub, bundle, {}, {"Wave CM": "'Wave CM' 페이저 프리셋을 콘솔에서 찾지 못했습니다"}
        )
        assert resolved == {}
        assert "Wave CM" in failed  # unchanged — not even attempted
        assert stub.dispatched == []  # 콘솔 쓰기 0건


class TestSkipsWhenAlreadyResolved:
    def test_an_already_resolved_label_is_not_retried(self):
        stub = _PregenStub()
        bundle = _Bundle(cues=(_cue("후렴", permitted=("dimmer chase",)),))
        resolved, failed = _PREGEN(stub, bundle, {"Wave CM": (4, 7)}, {})
        assert resolved == {"Wave CM": (4, 7)}
        assert stub.dispatched == []


class TestSuccessfulPregeneration:
    def test_a_missing_label_is_generated_and_dispatched_through_the_gate(self):
        stub = _PregenStub(pool_no=4, children={41: "Breathe Warm"})
        bundle = _Bundle(cues=(_cue("후렴", permitted=("dimmer chase",)),))
        failed = {"Wave CM": "'Wave CM' 페이저 프리셋을 콘솔에서 찾지 못했습니다"}
        resolved, failed = _PREGEN(stub, bundle, {}, failed)
        assert "Wave CM" not in failed
        assert resolved["Wave CM"][0] == 4
        assert resolved["Wave CM"][1] == 1  # 41 점유 — 번호만 보고 1부터
        # went through the EXISTING gate — a BatchRisk declaration rode the call
        assert len(stub.dispatched) == 1
        assert stub.dispatched[0].name == "run_commands"
        assert stub.risks[0] is not None
        assert stub.risks[0].kind == "song_design_fx_pregen"

    def test_a_rejected_gate_dispatch_lands_in_failed_not_resolved(self):
        stub = _PregenStub(dispatch_ok=False, dispatch_detail="blocked: blacklist")
        bundle = _Bundle(cues=(_cue("후렴", permitted=("dimmer chase",)),))
        failed = {"Wave CM": "'Wave CM' 페이저 프리셋을 콘솔에서 찾지 못했습니다"}
        resolved, failed = _PREGEN(stub, bundle, {}, failed)
        assert "Wave CM" not in resolved
        assert "Wave CM" in failed
        assert "거부" in failed["Wave CM"]


class TestCollisionRefusals:
    def test_a_label_outside_the_catalog_refuses_without_touching_the_pool(self):
        stub = _PregenStub()
        bundle = _Bundle(cues=(_cue("장면1", permitted=("dimmer chase",)),))
        # "장면1" never maps to a catalog label (`_phaser_label_for_cue` ->
        # None), so `wanted` is empty and pregen never fires at all.
        resolved, failed = _PREGEN(stub, bundle, {}, {})
        assert resolved == {} and failed == {}
        assert stub.dispatched == []

    def test_drop_slam_now_builds_and_dispatches_through_the_gate(self):
        # M6 측정: "Drop Slam"(combo: Red@100 -> Red@0)은 두 스텝 모두
        # `ColorRGB_R At 100`을 내어 `build_fx_preset_bundle`의 `_guard_
        # collision`에 거부됐다. M6b(카드 t501, 2026-10-02 리드 결정)가
        # `run_commands` 중복 제거 범위를 `Step <n>` 경계에서 리셋하도록
        # 좁히고 `_guard_collision`을 그에 맞춰 완화한 뒤로는, 스텝 경계를
        # 건넌 반복은 충돌이 아니다 — Drop Slam도 이제 다른 4개 필요 라벨과
        # 같이 그냥 빌드되어 기존 게이트를 통과해 디스패치된다.
        stub = _PregenStub(pool_no=9, children={})
        bundle = _Bundle(cues=(_cue("드롭", permitted=("dimmer chase",)),))
        failed = {"Drop Slam": "'Drop Slam' 페이저 프리셋을 콘솔에서 찾지 못했습니다"}
        resolved, failed = _PREGEN(stub, bundle, {}, failed)
        assert "Drop Slam" not in failed
        assert resolved["Drop Slam"][0] == 9
        assert len(stub.dispatched) == 1
        assert stub.dispatched[0].name == "run_commands"

    def test_a_genuine_same_step_collision_is_still_reported_not_overwritten(self, monkeypatch):
        # The relaxation is scoped to a repeat that crosses a Step boundary —
        # a TRUE same-step collision (no FXLIB catalog label reproduces this
        # today) must still be refused and must still never touch the pool.
        import server.web.session as session_module
        from server.fx.instantiate import VALUE_LINE_COLLISION, FxInstantiationError

        def _always_collides(label, *, presets_section, preset_pool, requested_slot=None):
            raise FxInstantiationError(
                VALUE_LINE_COLLISION, f"fx {label!r} would emit a line twice"
            )

        monkeypatch.setattr(session_module, "pregenerate_phaser_bundle", _always_collides)
        stub = _PregenStub(pool_no=9, children={})
        bundle = _Bundle(cues=(_cue("드롭", permitted=("dimmer chase",)),))
        failed = {"Drop Slam": "'Drop Slam' 페이저 프리셋을 콘솔에서 찾지 못했습니다"}
        resolved, failed = _PREGEN(stub, bundle, {}, failed)
        assert "Drop Slam" not in resolved
        assert "Drop Slam" in failed
        assert stub.dispatched == []  # refused before any console write
