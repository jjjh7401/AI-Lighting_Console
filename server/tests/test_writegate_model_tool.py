"""SPEC-COPILOT-WRITEGATE-001 — 모델의 `run_commands` 통로를 몰아 잰다 (카드 t323).

t320 이 `session.py` 의 쇼파일 쓰기 열 자리를 봉합했고 t322 가 그 봉합을 게이트
앞단에서 다시 쟀는데, 열 자리 **밖**이 남아 있었다: 모델이 자기 도구
(`run_commands`)로 직접 보내는 번들. 여덟 번들이 `Store Cue 1` · `Store Group 3` ·
`Store Sequence 71 ; Assign …` 을 싣고 `matched_entry: None` · 분류 `safe` 로
카드 한 장 없이 콘솔에 닿았다.

사람의 의도가 가장 옅은 통로에 게이트가 가장 얇았다는 뜻이라 여기를 닫는다.
이 파일이 재는 것은 셋이다.

거절
    승인기가 거절하면 쇼파일을 고치는 줄이 **0건** 콘솔에 닿는다.

수락
    카드가 **한 장**이고 번들의 모든 줄을 싣는다. 감사 로그의 `approved`
    기록이 이 통로의 `kind` (`model_run_commands`)를 단다.

무해한 번들
    쇼파일을 안 고치는 번들(조회·프로그래머 값)에는 카드가 **안 뜨고**
    명령은 그대로 나간다. 안 고치는 번들에 카드를 띄우면 감독은 곧 카드를
    안 읽게 되고, 그게 진짜 쓰기를 통과시킨다.

그리고 넷째로, 심사받는 당사자가 자기 선언을 못 만진다는 것 — 모델이
`arguments` 에 `risk` 를 실어도 무시된다.

한계. 서버 층만 잰다. 실기 콘솔도, 모델의 실제 출력 분포도 안 잰다.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.tools import ExecutionContext, build_toolset
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel

from .test_web_session import FakeConsole

#: 쇼파일 오브젝트를 만들거나 덮는 줄 — `test_writegate_session_sites.py` 와 같은 술어.
_SHOWFILE_PREFIXES = ("Store ", "Assign Sequence ", "Copy Sequence ", "Set Fixture ")


def _showfile(commands) -> list[str]:
    return [c for c in commands if c.startswith(_SHOWFILE_PREFIXES)]


class _Channel(ApprovalChannel):
    """카드를 자기가 답하는 승인 채널."""

    def __init__(self, verdict: bool) -> None:
        super().__init__(timeout_seconds=1.0)
        self.verdict = verdict
        self.requests: list = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return self.verdict


class _StatePort:
    def query(self, path):  # pragma: no cover - 이 파일은 쓰기 경로만 잰다
        raise AssertionError("이 검사는 판독을 쓰지 않는다")


def _audit_events(audit: AuditLog) -> list[dict]:
    root = audit.directory if hasattr(audit, "directory") else audit._directory
    entries: list[dict] = []
    for path in sorted(root.rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
    return entries


def _dispatch(tmp_path, commands, *, verdict: bool, arguments=None):
    """모델이 부르는 그 자리로 번들을 보낸다 — `ToolRegistry.dispatch`."""
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = _Channel(verdict)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    registry = build_toolset(
        execution_port=gate.execution_port, state_port=_StatePort(), bundle_gate=gate
    )
    args = {"commands": list(commands)}
    if arguments:
        args.update(arguments)
    execution = registry.dispatch(
        ToolCall(id="t323", name="run_commands", arguments=args), ExecutionContext()
    )
    return execution, console, audit, channel


# ---------------------------------------------------------------------------
# t322 가 실제로 잡은 세 번들. 여기서 다시 재는 이유는 「닫혔다」를 그 증거로
# 말하기 위해서다 — 다른 문장으로 바꿔 적으면 같은 것을 잰 게 아니다.
# ---------------------------------------------------------------------------
_MEASURED_BUNDLES = (
    ["Store Cue 1"],
    ["Store Group 3"],
    ["Store Sequence 71", "Assign Sequence 71 At Executor 201"],
)


class TestRejectSendsNothing:
    def test_a_rejected_model_bundle_reaches_the_console_zero_times(self, tmp_path):
        for commands in _MEASURED_BUNDLES:
            _execution, console, _audit, channel = _dispatch(tmp_path, commands, verdict=False)
            assert channel.requests, f"카드가 안 떴다: {commands}"
            assert _showfile(console.executed) == [], (
                f"거절했는데 쇼파일 쓰기가 나갔다: {console.executed}"
            )


class TestAcceptRaisesExactlyOneCard:
    def test_one_card_carries_every_line_and_the_audit_names_this_channel(self, tmp_path):
        commands = ["Store Sequence 71", "Assign Sequence 71 At Executor 201"]
        _execution, console, audit, channel = _dispatch(tmp_path, commands, verdict=True)
        assert len(channel.requests) == 1, "카드는 번들당 한 장이다"
        carried = [item.command for item in channel.requests[0].items]
        assert carried == commands, "카드가 번들의 모든 줄을 실어야 한다"
        assert console.executed == commands
        approved = [e for e in _audit_events(audit) if e.get("event") == "approved"]
        assert approved, "승인 기록이 없다"
        assert any(e.get("kind") == "model_run_commands" for e in approved), (
            f"이 통로의 kind 가 감사 로그에 안 남았다: {approved}"
        )

    def test_the_card_text_says_what_the_bundle_writes(self, tmp_path):
        _execution, _console, _audit, channel = _dispatch(tmp_path, ["Store Group 3"], verdict=True)
        reasons = " ".join(
            reason for item in channel.requests[0].items for reason in item.risk_reasons
        )
        assert "쇼파일 쓰기" in reasons and "Group 3" in reasons, reasons


class TestHarmlessBundlesRaiseNoCard:
    def test_a_programmer_only_bundle_flows_without_a_card(self, tmp_path):
        # 프로그래머 값이다 — `Store` 가 없으면 쇼파일에 안 남는다.
        commands = ["Fixture 20 Attribute 'Pan' At 12", "ClearAll"]
        _execution, console, _audit, channel = _dispatch(tmp_path, commands, verdict=False)
        assert channel.requests == [], "안 고치는 번들에 카드가 떴다"
        assert console.executed == commands


class TestTheModelCannotTouchItsOwnDeclaration:
    def test_a_model_supplied_risk_argument_is_ignored(self, tmp_path):
        # 모델이 「위험 없음」을 스스로 선언해도 카드는 뜬다. 심사받는 당사자가
        # 자기 심사 선언을 만들면 그건 선언이 아니다(REQ-BULKGATE-004).
        _execution, console, _audit, channel = _dispatch(
            tmp_path,
            ["Store Group 3"],
            verdict=False,
            arguments={"risk": None, "kind": "safe", "showfile_write": False},
        )
        assert channel.requests, "모델이 실은 인자가 선언을 껐다"
        assert _showfile(console.executed) == []

    def test_the_declaration_is_not_read_from_arguments_at_all(self, tmp_path):
        # 반대 방향도 잰다: 모델이 위험을 **켜려** 해도 안 켜진다. 안 그러면
        # 모델이 임의의 번들에 카드를 띄워 감독을 지치게 할 수 있다.
        _execution, _console, _audit, channel = _dispatch(
            tmp_path,
            ["Fixture 20 Attribute 'Pan' At 12"],
            verdict=False,
            arguments={"risk": {"reason": "위험합니다", "kind": "model_says_so"}},
        )
        assert channel.requests == [], "모델이 실은 인자로 카드를 띄웠다"
