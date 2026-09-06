"""SPEC-COPILOT-BULKGATE-001 — 곡→콘솔 대량 반영이 승인을 거친다.

2026-09-07 브라우저 실측: 곡 파일 하나를 올리면 명령 수십 건이 나가고 그 안에
`Store Sequence <N> Cue …` 와 `Store Timecode <slot>` 이 있는데, 화면에는
「주의」 배지만 있고 승인 컨트롤이 없었다. 감사 로그에 `approved` 는 0건.

이 파일은 그 경로를 **진짜 게이트**로 몰아 잰다 — 게이트 더블이 아니다.
같은 세션을 승인 채널만 바꿔 두 번 돌리고, 거절 회차에서 콘솔이 0건을 받는지,
수락 회차에서 카드가 한 장인지를 본다.

한계. 여기서 재는 것은 서버 층이다. DOM 은 안 잰다 — 화면에 카드가 실제로
그려지는지는 브라우저 회차가 답한다(AC-BULKGATE-012).
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.tests.test_songcue_tool import _DEFAULT_SECTIONS, _library, _tree
from server.tests.test_songcue_tool import _SongCueStatePort as _StatePort

_TOOL = "prepare_songcue"


class _Console:
    """콘솔이 실제로 받은 명령만 센다 — 「0건 나갔다」의 계측기."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str):
        from server.safety.console import ExecOutcome

        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict:
        raise RuntimeError(f"no such path: {path}")


class _Approval:
    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.requests: list[object] = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return self.answer


def _run(tmp_path, *, approve: bool):
    console = _Console()
    approval = _Approval(approve)
    audit = AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    state = _StatePort(_tree())
    registry = build_toolset(
        execution_port=gate.execution_port,
        state_port=state,
        bundle_gate=gate,
        look_library=_library(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="songcue-bulkgate",
            name=_TOOL,
            arguments={
                "song_title": "테스트 곡",
                "genre": "록",
                "timecode_number": 7,
                "sections": list(_DEFAULT_SECTIONS),
            },
        )
    )
    return execution, json.loads(execution.result.content), console, approval, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


class TestApprovalIsAsked:
    def test_exactly_one_card_for_the_whole_song(self, tmp_path):
        _, _, _, approval, _ = _run(tmp_path, approve=True)
        # 명령마다 묻지 않는다 — 28장이 뜨면 감독은 읽지 않고 누른다.
        assert len(approval.requests) == 1

    def test_the_card_carries_every_command_of_the_bundle(self, tmp_path):
        _, payload, console, approval, _ = _run(tmp_path, approve=True)
        assert approval.requests[0].commands == tuple(console.executed)
        assert payload["executed"] is True

    def test_the_reason_names_sequence_cue_count_timecode_and_no_restore(self, tmp_path):
        # REQ-BULKGATE-007 — 「위험한 명령입니다」로는 이 요구가 안 채워진다.
        _, payload, _, approval, _ = _run(tmp_path, approve=True)
        reason = approval.requests[0].items[0].risk_reasons[0]
        assert f"Sequence {payload['sequence']}" in reason
        assert "큐" in reason
        assert "Timecode 7" in reason
        assert "복원 경로가 없습니다" in reason

    def test_the_showfile_writes_reach_the_console_on_acceptance(self, tmp_path):
        _, _, console, _, _ = _run(tmp_path, approve=True)
        assert any(c.startswith("Store Sequence ") for c in console.executed)
        assert any(c.startswith("Store Timecode ") for c in console.executed)


class TestRefusalSendsNothing:
    def test_zero_commands_reach_the_console(self, tmp_path):
        _, _, console, approval, _ = _run(tmp_path, approve=False)
        assert len(approval.requests) == 1
        assert console.executed == []

    def test_the_wording_says_zero_and_claims_no_partial_apply(self, tmp_path):
        _, payload, _, _, _ = _run(tmp_path, approve=False)
        assert payload["executed"] is False
        assert payload["console_commands_sent"] == 0
        assert "0건" in payload["summary_ko"]

    def test_the_audit_separates_the_two_rounds(self, tmp_path):
        # AC-BULKGATE-003 — 「executed N, approved 0」이 재현되지 않는다.
        _, _, _, _, ok_audit = _run(tmp_path / "ok", approve=True)
        _, _, _, _, no_audit = _run(tmp_path / "no", approve=False)

        approved = _events(ok_audit, "approved")
        assert len(approved) == 1
        assert approved[0]["kind"] == "songcue"
        assert _events(ok_audit, "executed")

        rejected = _events(no_audit, "rejected")
        assert len(rejected) == 1
        assert rejected[0]["kind"] == "songcue"
        assert _events(no_audit, "executed") == []


class TestTheModelCannotTurnItOff:
    """REQ-BULKGATE-004 — 모델이 끌 수 있는 안전장치는 안전장치가 아니다."""

    def test_a_risk_key_in_the_tool_arguments_is_ignored(self, tmp_path):
        console = _Console()
        approval = _Approval(False)
        gate = SafetyGate(
            console=console,
            audit=AuditLog(tmp_path / "audit"),
            approval_port=approval,
        )
        registry = build_toolset(
            execution_port=gate.execution_port,
            state_port=_StatePort(_tree()),
            bundle_gate=gate,
            look_library=_library(),
        )
        execution = registry.dispatch(
            ToolCall(
                id="songcue-bypass",
                name=_TOOL,
                arguments={
                    "song_title": "테스트 곡",
                    "genre": "록",
                    "timecode_number": 7,
                    "sections": list(_DEFAULT_SECTIONS),
                    # 모델이 선언을 끄려 시도하는 모양.
                    "risk": None,
                },
            )
        )
        payload = json.loads(execution.result.content)
        # 선언이 살아 있어 승인이 요구되고, 거절이므로 발사 0건이다.
        assert len(approval.requests) == 1
        assert console.executed == []
        assert payload["executed"] is False

    def test_run_commands_never_reads_risk_from_the_tool_arguments(self):
        # 정적 확인 — `arguments` 에서 `risk` 를 꺼내는 줄이 없어야 한다.
        # 있으면 모델이 그 키로 선언을 조작할 표면이 생긴다.
        import ast
        from pathlib import Path

        source = Path("server/orchestrator/tools.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        run_commands = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "run_commands"
        )
        subscripts = {
            node.slice.value
            for node in ast.walk(run_commands)
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
        }
        get_keys = {
            node.args[0].value
            for node in ast.walk(run_commands)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        assert "risk" not in subscripts | get_keys
