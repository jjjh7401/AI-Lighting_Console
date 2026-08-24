"""SPEC-COPILOT-LXSEQ-003 — 승인 없이는 콘솔에 닿지 않는다 (REQ-LXSEQ3-015).

🔴 **이 파일은 사고 뒤에 쓰였다.** 2026-08-25, `--approve` 없이 `--action apply` 로
하네스를 돌렸는데 명령이 **실제로 나갔다** — `Store Preset 1.1` · `Label Preset 1.1`
이 콘솔에서 `executed_ok` 를 받았고 승인 통로는 **한 번도 안 물어졌다**.

원인은 둘이다.

1. 툴 `import_lxseq_presets` 가 `run_commands` 를 바로 부르고 **어떤 승인 통로도
   안 묻는다.** 형제 `create_arrangement_groups` 는 묻는다.
2. 하네스의 `--approve` 는 승인 통로의 **대답**만 정할 뿐 디스패치를 안 막는다.
   툴이 안 물으니 대답이 쓰이지도 않았다.

그리고 그 앞에 절차 결함이 있었다 — **「승인 없이 실행해서 안 닿는 것을 확인하라」**
는 단계가 배차서에 있었다. 안전장치가 있으면 이미 믿던 것을 확인할 뿐이고, **없으면
그 확인이 곧 사고**다. 확인과 사고가 같은 행위인 절차였다.

그래서 그 확인은 **여기서** 한다. 실기가 아니라 검사가 할 일이다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset

RIG = Path("src/Lighting_Designer/02_RIG팩")
DIM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"
TOOL = "import_lxseq_presets"


class _RecordingPort:
    """발화를 **기록만** 한다. 실패로 죽이지 않는 이유는, 죽이면 「발화했다」와
    「발화하려다 예외로 막혔다」가 구분되지 않기 때문이다."""

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


class _Approval:
    def __init__(self, *, approve: bool) -> None:
        self.approve = approve
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return self.approve


def _dispatch(*, approve: bool, action: str = "apply"):
    port = _RecordingPort()
    approval = _Approval(approve=approve)
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=approval,
    )
    execution = registry.dispatch(
        ToolCall(
            id="safety",
            name=TOOL,
            arguments=dict(
                file_content_base64=base64.b64encode(DIM.read_bytes()).decode("ascii"),
                action=action,
            ),
        )
    )
    return json.loads(execution.result.content), port, approval


class TestApplyRequiresApproval:
    def test_a_denied_approval_fires_nothing(self):
        """🔴 **사고가 난 자리다.** 승인이 거절되면 콘솔에 한 줄도 가면 안 된다."""
        _payload, port, approval = _dispatch(approve=False)
        assert approval.asked, "승인 통로를 **한 번도 안 물었다** — 게이트가 없다"
        assert port.executed == [], "승인이 거절됐는데 발화했다: " + repr(port.executed)

    def test_an_approved_apply_does_fire(self):
        """대조군 — 승인하면 나간다. 이게 없으면 위 검사가 「무조건 안 나간다」와
        구분되지 않는다(예: 툴이 그냥 고장 난 경우)."""
        _payload, port, approval = _dispatch(approve=True)
        assert approval.asked
        assert any(c.startswith("Store Preset ") for c in port.executed), port.executed

    def test_preview_never_asks_and_never_fires(self):
        """preview 는 승인을 물을 일조차 없다 — 쓰지 않기 때문이다."""
        _payload, port, approval = _dispatch(approve=True, action="preview")
        assert port.executed == []
        assert approval.asked == []

    def test_the_refusal_is_named_in_the_payload(self):
        """조용히 0건이 되면 사용자는 승인 때문인지 계획이 없어서인지 모른다."""
        payload, _port, _approval = _dispatch(approve=False)
        assert payload.get("approval") == "declined", payload.get("approval")


class TestHarnessRefusesWithoutApprove:
    def test_apply_without_approve_does_not_dispatch(self, monkeypatch):
        """하네스의 `--approve` 가 **디스패치 자체**를 막아야 한다.

        사고 당시 그 플래그는 승인 통로의 대답만 정했고, 툴이 안 물으니 아무 효과도
        없었다. 플래그가 막는 것은 대답이 아니라 **행위**여야 한다.
        """
        from server.tools import lxseq_presets_e2e as harness

        def _boom(*_a, **_k):
            raise AssertionError("--approve 없이 콘솔 스택을 세웠다")

        monkeypatch.setattr(harness, "build_console_stack", _boom)
        with pytest.raises(SystemExit) as exit_info:
            harness.main(
                [
                    "--preset-csv",
                    str(DIM),
                    "--listen-port",
                    "9005",
                    "--action",
                    "apply",
                ]
            )
        assert exit_info.value.code != 0


class TestPoolListingNormalisation:
    """응답기의 `i` 를 `no` 로 정규화하지 않으면 **fail-closed 로 막힌다**.

    실기에서 실제로 났다: 툴이 `children` 을 그대로 `objects` 로 넘겨 매퍼가
    슬롯 번호를 못 읽고 `pool_unreadable` 로 거절했다. **막힌 것이 옳다** —
    번호를 못 읽었는데 배정했으면 점유 슬롯을 덮어썼을 것이고, 프리셋 값은
    되읽을 수 없어 복구도 못 한다.

    정규화기(`rig_object`)는 이미 있었다. 두 번째로 구현한 것이 defect 였다.
    """

    @staticmethod
    def _dispatch_with(children):
        approval = _Approval(approve=True)

        class _Pool(_RecordingPort):
            def query_state(self, path: str) -> dict:
                if path.endswith("PresetPools"):
                    return dict(children=[dict(i=1, name="Dimmer")], node=dict(childCount=1))
                if path.endswith("PresetPools/1"):
                    return dict(children=children, node=dict(childCount=len(children)))
                return dict(children=[], node=dict(childCount=0), truncated=False)

        pool = _Pool()
        registry = build_toolset(
            execution_port=pool,
            state_port=pool,
            property_port=pool,
            group_approval_port=approval,
        )
        execution = registry.dispatch(
            ToolCall(
                id="norm",
                name=TOOL,
                arguments=dict(
                    file_content_base64=base64.b64encode(DIM.read_bytes()).decode("ascii"),
                    action="preview",
                ),
            )
        )
        return json.loads(execution.result.content)

    def test_a_responder_slot_key_is_understood(self):
        """`i` 로 온 점유 슬롯을 읽고 **그 슬롯을 피한다**."""
        payload = self._dispatch_with([dict(i=1, name="풀")])
        assert payload["refusal"] is None, payload["refusal_detail"]
        slots = [p["slot"] for p in payload["planned"]]
        assert 1 not in slots, slots
        assert slots[0] == 2

    def test_an_entry_without_a_slot_still_refuses(self):
        """대조군 — 정규화가 **부재를 보존**하는지. 번호 없는 항목이 오면
        여전히 fail-closed 여야 한다. 정규화가 없는 번호를 지어내면 이 검사가
        빨개진다."""
        payload = self._dispatch_with([dict(name="번호를 확정 못 한 항목")])
        assert payload["refusal"] == "pool_unreadable", payload["refusal"]
        assert payload["planned"] == []
