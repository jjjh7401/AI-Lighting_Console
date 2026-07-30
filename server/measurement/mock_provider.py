"""Deterministic offline doubles for the measurement runner (M6a).

Everything here is scripted and in-memory: the mock LLM provider replays the
corpus scenarios' ``mock`` blocks, the offline console acknowledges commands
without any transport, and the offline deploy pipeline approves mock plugin
deployments. No network, no credentials, no OSC — the single-chokepoint
import boundary (AC-MVP-019 ①) is untouched (nothing here imports the bridge).
"""

from __future__ import annotations

from collections.abc import Sequence

from server.deploy.pipeline import DeployOutcome
from server.llm.types import (
    ConversationItem,
    ModelTurn,
    ToolCall,
    ToolDefinition,
    ToolResultsMessage,
    Usage,
    UserMessage,
)
from server.measurement.corpus import MockScript, Scenario
from server.safety.console import ExecOutcome

_FINAL_TEXT = {
    "commands": "요청한 작업을 실행했습니다.",
    "query": "조회 결과를 정리해 드렸습니다.",
    "plugin": "플러그인을 배포했습니다.",
}


class MockScenarioProvider:
    """Scripted LLMProvider: replays each scenario's mock action, then answers.

    ``first_attempt_overrides`` maps an instruction to the command bundle the
    mock model generates on its FIRST attempt (error-injection hook for the
    numerator-accounting tests); after error feedback it self-corrects to the
    scenario's baseline ``mock.commands``.
    """

    name = "mock"
    model_id = "mock-offline"
    supports_prompt_caching = False

    def __init__(
        self,
        scenarios: Sequence[Scenario],
        *,
        first_attempt_overrides: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._scripts: dict[str, MockScript] = {s.instruction: s.mock for s in scenarios}
        self._overrides = dict(first_attempt_overrides or {})

    def complete(
        self,
        *,
        system_prefix: str,
        conversation: Sequence[ConversationItem],
        tools: Sequence[ToolDefinition] = (),
    ) -> ModelTurn:
        instruction = next(item.text for item in conversation if isinstance(item, UserMessage))
        script = self._scripts.get(instruction)
        if script is None:
            raise KeyError(f"mock provider has no script for instruction: {instruction!r}")
        rounds = sum(1 for item in conversation if isinstance(item, ToolResultsMessage))
        call_id = f"mock-{rounds + 1}"
        if script.kind == "commands":
            attempts: list[tuple[str, ...]] = []
            override = self._overrides.get(instruction)
            if override is not None:
                attempts.append(tuple(override))
            attempts.append(script.commands)
            if rounds < len(attempts):
                return self._tool_turn(
                    ToolCall(
                        id=call_id,
                        name="run_commands",
                        arguments={"commands": list(attempts[rounds])},
                    )
                )
        elif script.kind == "query" and rounds == 0:
            return self._tool_turn(
                ToolCall(id=call_id, name="query_state", arguments={"path": script.query_path})
            )
        elif script.kind == "plugin" and rounds == 0:
            return self._tool_turn(
                ToolCall(
                    id=call_id,
                    name="deploy_plugin",
                    arguments={"name": script.plugin_name, "lua_source": script.plugin_source},
                )
            )
        return ModelTurn(
            text=_FINAL_TEXT[script.kind],
            tool_calls=(),
            stop_reason="end",
            usage=Usage(),
            provider=self.name,
        )

    def _tool_turn(self, call: ToolCall) -> ModelTurn:
        return ModelTurn(
            text="",
            tool_calls=(call,),
            stop_reason="tool_use",
            usage=Usage(),
            provider=self.name,
        )


class OfflineConsole:
    """In-memory ConsolePort: every command is acknowledged, never sent."""

    def execute(self, command: str) -> ExecOutcome:
        return ExecOutcome(status="ok", detail=f"offline mock execution: {command}")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict:
        return {
            "path": path,
            "children": [{"name": f"{path.rsplit('/', 1)[-1]} {n}"} for n in (1, 2, 3)],
        }

    def query_property(self, path: str, property_name: str) -> dict:
        return {
            "ok": True,
            "path": path,
            "property": property_name,
            "value": f"offline {property_name}",
        }

    def deploy_plugin(self, name: str, lua_source: str) -> ExecOutcome:
        return ExecOutcome(status="ok", detail=f"offline mock deploy: {name}")


class OfflineDeployPipeline:
    """DeployPipelinePort double: approves every mock deployment offline."""

    def deploy(self, name: str, lua_source: str) -> DeployOutcome:
        return DeployOutcome(status="deployed", detail=f"offline mock deployment: {name}")
