"""Deploy self-correction accounting tests (M7 — GWT scenario 5, REQ-MVP-010).

A compile-failing deployment feeds the self-correction loop exactly like a
failing command bundle: the structured error goes back to the model, and each
corrected ``deploy_plugin`` attempt after a failure counts one retry toward
the SAME hard cap of 3 (no unbounded deploy churn). A human review REJECTION
is not a technical failure and never consumes a retry (mirror of the M4
approval-rejection rule).
"""

from __future__ import annotations

from server.deploy.compile import LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.llm.types import ModelTurn, ToolCall, Usage
from server.orchestrator.runner import Orchestrator
from server.orchestrator.tools import build_toolset
from server.safety.audit import AuditLog
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import load_ruleset

from .test_deploy_pipeline import FakeDeployPort, ScriptedReview
from .test_tools import FakeStatePort, ScriptedPort

BROKEN_SOURCE = "function broken( end"
SAFE_SOURCE = 'return function() Cmd("Store Group 3") end'


def _deploy_turn(call_id: str, source: str = BROKEN_SOURCE) -> ModelTurn:
    return ModelTurn(
        text="",
        tool_calls=(
            ToolCall(
                id=call_id,
                name="deploy_plugin",
                arguments={"name": "Cleaner", "lua_source": source},
            ),
        ),
        stop_reason="tool_use",
        usage=Usage(),
        provider="scripted",
    )


def _final(text: str = "완료") -> ModelTurn:
    return ModelTurn(
        text=text, tool_calls=(), stop_reason="end", usage=Usage(), provider="scripted"
    )


class AlwaysBrokenDeployProvider:
    """Answers every turn with the same compile-failing deployment."""

    name = "scripted"
    model_id = "scripted-model"
    supports_prompt_caching = False

    def __init__(self):
        self.calls = 0

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls += 1
        return _deploy_turn(f"call-{self.calls}")


def _orchestrator(tmp_path, provider, *, review_decisions=(True,)):
    pipeline = DeployPipeline(
        compile_checker=LuaCompileChecker(),
        ruleset=load_ruleset(),
        deploy_port=FakeDeployPort(),
        registry=PluginFlagRegistry(),
        audit=AuditLog(tmp_path / "audit"),
        review_port=ScriptedReview(list(review_decisions)),
    )
    registry = build_toolset(
        execution_port=ScriptedPort(),
        state_port=FakeStatePort({}),
        deploy_pipeline=pipeline,
    )
    return Orchestrator(provider=provider, registry=registry, system_prefix="PREFIX")


class TestDeployRetryCap:
    def test_compile_failures_hit_the_same_three_retry_cap(self, tmp_path):
        provider = AlwaysBrokenDeployProvider()
        orchestrator = _orchestrator(tmp_path, provider)
        result = orchestrator.handle_instruction("정리 플러그인 배포해줘")
        assert result.status == "retries_exhausted"
        assert result.retries_used == 3
        # Initial attempt + exactly 3 corrections = 4 model calls, no 5th.
        assert result.model_calls == 4
        assert all(o.status == "blocked" for o in result.command_outcomes)

    def test_corrected_deploy_succeeds_within_the_cap(self, tmp_path):
        from .test_runner_self_correction import ScriptedProvider

        provider = ScriptedProvider(
            [_deploy_turn("c1"), _deploy_turn("c2", SAFE_SOURCE), _final("배포했습니다")]
        )
        orchestrator = _orchestrator(tmp_path, provider, review_decisions=(True, True))
        result = orchestrator.handle_instruction("배포해줘")
        assert result.status == "ok"
        assert result.retries_used == 1
        statuses = [o.status for o in result.command_outcomes]
        assert statuses == ["blocked", "executed_ok"]


class TestReviewRejectionIsNotARetry:
    def test_rejection_does_not_consume_the_retry_budget(self, tmp_path):
        from .test_runner_self_correction import ScriptedProvider

        provider = ScriptedProvider(
            [_deploy_turn("c1", SAFE_SOURCE), _final("리뷰가 거부되었습니다")]
        )
        orchestrator = _orchestrator(tmp_path, provider, review_decisions=(False,))
        result = orchestrator.handle_instruction("배포해줘")
        assert result.status == "ok"  # honest rejection report, not a failure loop
        assert result.retries_used == 0
        (outcome,) = result.command_outcomes
        assert outcome.status == "rejected"
