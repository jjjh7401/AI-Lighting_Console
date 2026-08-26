"""카드 t110 — 앱 경로의 프리셋·그룹 쓰기가 항상 거절되던 자리.

`import_lxseq_presets` · `create_arrangement_groups` 는 게이트가 위험으로 분류하지
않는 명령(`Store Preset` · `Store Group`)을 쓰므로 **자기 승인 통로**를 따로 묻는다
(`tools.py` 의 `group_approval_port`). 통로가 없으면 `DenyAllApprovalPort` 로 떨어져
fail-closed 로 거절한다 — 2026-08-25 사고 뒤에 그렇게 만들어졌고, 그 기본값은 옳다.

문제는 **앱이 그 통로를 한 번도 안 실었다**는 것이다. `ChatSession` 은 이미 살아 있는
`ApprovalChannel`(게이트와 같은 객체, 세션 UI 에 bind 됨)을 들고 있으면서
`build_toolset(...)` 호출에 안 넘겼다. 그래서 앱에서는 프리셋 적용이 **항상 declined**
였다 — 하네스에서만 돌았다.

이 파일이 재는 것은 **경계**다: 세션이 무엇을 넘기는가(배선), 그리고 안 넘겼을 때
무슨 일이 일어나는가(fail-closed 가 여전히 사는가). 두 축을 따로 잡는다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.web.approval_bridge import ApprovalChannel

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import _session

RIG = Path("src/Lighting_Designer/02_RIG팩")
DIM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"
PRESET_TOOL = "import_lxseq_presets"


class _RecordingPort:
    """발화를 **기록만** 한다 — 예외로 죽이면 「발화했다」와 「발화하려다
    막혔다」가 구분되지 않는다(`test_lxseq_preset_safety.py` 와 같은 이유)."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str) -> dict:
        if path.endswith("PresetPools"):
            return dict(children=[dict(i=1, name="Dimmer")], node=dict(childCount=1))
        return dict(children=[], node=dict(childCount=0), truncated=False)

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


class _AlwaysApprove:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _apply_through(registry) -> dict:
    execution = registry.dispatch(
        ToolCall(
            id="t110",
            name=PRESET_TOOL,
            arguments=dict(
                file_content_base64=base64.b64encode(DIM.read_bytes()).decode("ascii"),
                action="apply",
            ),
        )
    )
    return json.loads(execution.result.content)


# -- 1. 배선 — 세션이 자기 승인 채널을 툴셋에 싣는다 -------------------------------


class TestSessionWiresItsApprovalChannel:
    def _captured(self, tmp_path, monkeypatch) -> dict:
        import server.web.session as session_module

        original = session_module.build_toolset
        seen: dict = dict()

        def _capture(**kwargs):
            seen.update(kwargs)
            return original(**kwargs)

        monkeypatch.setattr(session_module, "build_toolset", _capture)
        session, _console, _audit, _sent, channel = _session(tmp_path, ScriptedProvider([]))
        seen["__channel__"] = channel
        seen["__session__"] = session
        return seen

    def test_group_approval_port_is_passed_at_all(self, tmp_path, monkeypatch):
        """안 실으면 `tools.py` 가 `DenyAllApprovalPort` 로 떨어져 항상 declined 다."""
        seen = self._captured(tmp_path, monkeypatch)
        assert "group_approval_port" in seen, (
            "build_toolset 호출에 group_approval_port 가 없다 — 앱 경로는 항상 거절된다"
        )
        assert seen["group_approval_port"] is not None

    def test_it_is_the_session_own_live_channel(self, tmp_path, monkeypatch):
        """새 통로를 만들면 안 된다 — UI 에 bind 된 그 채널이어야 사람이 답한다."""
        seen = self._captured(tmp_path, monkeypatch)
        assert seen["group_approval_port"] is seen["__channel__"]

    def test_the_channel_really_is_an_approval_port(self, tmp_path, monkeypatch):
        """비공허성 — 「무언가 실렸다」가 아니라 물을 수 있는 물건인가."""
        seen = self._captured(tmp_path, monkeypatch)
        assert callable(getattr(seen["group_approval_port"], "request_approval", None))
        assert isinstance(seen["__channel__"], ApprovalChannel)


# -- 2. fail-closed — 통로가 없으면 여전히 거절한다 (약화 금지) --------------------


class TestFailClosedSurvives:
    """이 축을 안 쏘면 배선하면서 fail-closed 를 깨뜨렸는지 모른다."""

    def test_no_port_still_declines_and_fires_nothing(self):
        port = _RecordingPort()
        registry = build_toolset(execution_port=port, state_port=port, property_port=port)
        payload = _apply_through(registry)

        assert payload.get("approval") == "declined", payload.get("approval")
        assert port.executed == [], "통로가 없는데 발화했다: " + repr(port.executed)

    def test_a_wired_port_is_actually_asked_and_then_fires(self):
        """대조군 — 통로가 있으면 묻고, 승인하면 나간다.

        이게 없으면 위 검사가 「무조건 안 나간다」(툴 고장)와 구분되지 않는다.
        """
        port = _RecordingPort()
        approval = _AlwaysApprove()
        registry = build_toolset(
            execution_port=port,
            state_port=port,
            property_port=port,
            group_approval_port=approval,
        )
        payload = _apply_through(registry)

        assert approval.asked, "승인 통로를 한 번도 안 물었다"
        assert payload.get("approval") == "granted", payload.get("approval")
        assert any(c.startswith("Store Preset ") for c in port.executed), port.executed
