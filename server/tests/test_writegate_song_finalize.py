"""SPEC-COPILOT-WRITEGATE-001 — 감독의 곡 흐름이 승인을 거친다 (카드 t317).

BULKGATE 는 `prepare_songcue`(모델 도구) 한 자리를 봉인했다. 그런데 2026-09-07
브라우저 회차에서 감독이 실제로 지난 길은 그 자리가 **아니었다**: 디자인 요청은
모델을 부르기 전에 `_song_design_interview_run` 이 가로채고, 명령은
`session.py::_song_finalize` 의 `run_commands` 디스패치
(`ToolCall(id="song-design-reviewed-bundle")`)로 나간다.

이 파일이 못으로 박는 것 셋:

1. **경로** — 이 흐름의 유일한 `run_commands` 디스패치는 `_song_finalize` 다.
   (실측 재현: `.moai/state/verify/t317/repro_path_before.json`)
2. **거절** — 감독이 승인 카드를 거절하면 콘솔이 받는 명령은 **0건**이다.
3. **수락** — 승인 카드는 **한 장**이고 번들의 **모든** 명령을 담으며,
   감사 로그에 `kind="song_design"` 으로 `approved` 가 남는다.

한계. 여기서 재는 것은 서버 층이다. DOM 은 안 잰다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.tests.test_safety_gate import FakeConsole
from server.web.approval_bridge import ApprovalChannel
from server.web.question import UNANSWERED
from server.web.session import ChatSession

REQUEST = (
    "디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9: "
    "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
)
#: Q1~Q5 인터뷰 다섯 장 + 전곡 리뷰 번들 승인 한 장.
ANSWERS = ("우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)", "승인")

_EMPTY = {"ok": True, "node": {"childCount": 0}, "children": []}


class _Console(FakeConsole):
    """빈 풀 슬롯을 실기와 같이 'path segment not found' 로 답한다."""

    def query_state(self, path: str) -> dict:
        if path in ("DataPool/Groups", "DataPool/PresetPools/2"):
            return _EMPTY
        raise RuntimeError(f"path segment not found: {path}")


class _Questions:
    def __init__(self, answers):
        self.answers = list(answers)
        self.asked = []

    def ask(self, request, **_kw):
        self.asked.append(request)
        return self.answers.pop(0) if self.answers else UNANSWERED

    def bind(self, *_a, **_kw):
        return None


class _Approval:
    """게이트 승인 통로 — 「카드가 떴는가」의 계측기."""

    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.requests = []

    def request_approval(self, request):
        self.requests.append(request)
        return self.answer

    def bind(self, *_a, **_kw):
        return None


class _Recording:
    """레지스트리를 감싸 디스패치 자리만 기록한다 — 위임은 그대로."""

    def __init__(self, inner, log):
        self._inner = inner
        self._log = log

    def definitions(self):
        return self._inner.definitions()

    def dispatch(self, call, context=None, *, risk=None):
        if call.name == "run_commands":
            self._log.append(call.id)
        if risk is not None:
            return self._inner.dispatch(call, context, risk=risk)
        if context is None:
            return self._inner.dispatch(call)
        return self._inner.dispatch(call, context)


class _Spatial:
    """좌표 판독만 대역 — 합성 패치를 Lua 로 돌리지 않기 위해서다."""

    def __init__(self, inner, log):
        self._recording = _Recording(inner, log)

    def definitions(self):
        return self._recording.definitions()

    def dispatch(self, call, context=None, *, risk=None):
        if call.name == "get_spatial_context":
            from server.llm.types import ToolResult
            from server.orchestrator.tools import ToolExecution

            return ToolExecution(
                ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "fixtures": [
                                {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
                                {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
                            ],
                            "coverage": {"complete": True},
                        }
                    ),
                )
            )
        return self._recording.dispatch(call, context, risk=risk)


class _Provider:
    def complete(self, *_a, **_kw):  # pragma: no cover - 이 경로는 모델을 안 부른다
        raise AssertionError("디자인 인터뷰는 모델을 부르지 않는다")


def _drive(tmp_path: Path, *, approve: bool):
    console = _Console()
    audit = AuditLog(tmp_path / "audit")
    approval = _Approval(approve)
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    session = ChatSession(
        gate=gate,
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=lambda event: None,
        approval_channel=ApprovalChannel(timeout_seconds=1.0),
    )
    sites: list[str] = []
    session._registry = _Spatial(session._registry, sites)
    questions = _Questions(ANSWERS)
    session._question_channel = questions
    session.run_instruction(REQUEST)
    return console, approval, sites, questions, audit


@pytest.fixture
def accepted(tmp_path):
    return _drive(tmp_path, approve=True)


class TestTheDirectorsFlowLeavesThroughSongFinalize:
    """경로 못 — 이 흐름의 디스패치 자리를 이름으로 고정한다."""

    def test_the_only_dispatch_is_the_song_finalize_bundle(self, accepted):
        _console, _approval, sites, _questions, _audit = accepted
        assert sites == ["song-design-reviewed-bundle"], (
            "감독의 곡 흐름은 prepare_songcue 가 아니라 _song_finalize 로 나간다"
        )

    def test_the_bundle_carries_the_showfile_writes(self, accepted):
        console, _approval, _sites, _questions, _audit = accepted
        assert any(line.startswith("Store Sequence 210 Cue ") for line in console.executed)
        assert any(line.startswith("Store Timecode 9") for line in console.executed)


class TestTheGateAsksBeforeTheWriteLeaves:
    """이 반이 변경 전에 빨갛다 — 오늘은 승인 요청이 0건이다."""

    def test_exactly_one_approval_card_is_raised(self, accepted):
        _console, approval, _sites, _questions, _audit = accepted
        assert len(approval.requests) == 1, "번들 하나에 카드 한 장"

    def test_the_card_carries_every_command_in_the_bundle(self, accepted):
        # 카드는 **번들 전체**를 담는다. 콘솔이 받는 줄 수가 더 적은 것은
        # run_commands 의 명령별 중복 제거 때문이고(같은 프리셋 회수 한 줄),
        # 카드가 무엇을 빼놓기 때문이 아니다 — 그 방향을 여기서 못 박는다.
        console, approval, _sites, _questions, _audit = accepted
        carried = [item.command for item in approval.requests[0].items]
        assert len(carried) >= len(console.executed) > 1
        for line in console.executed:
            assert line in carried
        assert [line for line in carried if line.startswith("Store ")] == [
            line for line in console.executed if line.startswith("Store ")
        ]

    def test_the_reason_names_what_is_written_and_that_there_is_no_restore(self, accepted):
        _console, approval, _sites, _questions, _audit = accepted
        reason = " ".join(r for item in approval.requests[0].items for r in item.risk_reasons)
        assert "Sequence 210" in reason
        assert "Timecode 9" in reason
        assert "복원 경로가 없습니다" in reason


class TestRejectionSendsNothing:
    def test_no_command_of_the_bundle_reaches_the_console(self, tmp_path):
        # 나가는 유일한 줄은 프로그래머를 비우는 `ClearAll` 이다 — 그 줄은
        # 쇼파일 오브젝트를 안 건드리며, 전수 조사에서도 비-쓰기로 분류돼 있다
        # (`_song_finalize` 그 함수 안 1번째 자리). 「부분 반영 없음」의 계측기는
        # 저장 줄이 하나도 안 나갔다는 것.
        console, approval, sites, _questions, _audit = _drive(tmp_path, approve=False)
        assert len(approval.requests) == 1
        assert sites == ["song-design-reviewed-bundle", "song-design-cleanup"]
        assert console.executed == ["ClearAll"], "저장 줄은 한 건도 나가지 않는다"
        assert not [line for line in console.executed if line.startswith("Store ")]


class TestTheAuditNamesTheChannel:
    def test_the_approved_entry_carries_the_song_design_kind(self, accepted):
        _console, _approval, _sites, _questions, audit = accepted
        entries = [json.loads(line) for line in _audit_lines(audit)]
        approved = [e for e in entries if e.get("event") == "approved"]
        assert approved, "수락 회차에 approved 기록이 있어야 한다"
        assert all(e.get("kind") == "song_design" for e in approved), approved


class TestTheCardReachesTheBrowser:
    """한 층 위 — 앱이 실제로 쓰는 배선(`app.py`: gate 의 approval_port 가
    세션 UI 에 bind 된 그 `ApprovalChannel`)에서 카드 프레임이 나가는지.

    DOM 은 여전히 안 잰다. 재는 것은 「브라우저로 나가는 이벤트가 생겼는가」다.
    """

    def test_an_approval_request_frame_is_emitted_and_no_answer_denies(self, tmp_path):
        console = _Console()
        audit = AuditLog(tmp_path / "audit")
        channel = ApprovalChannel(timeout_seconds=0.2)
        gate = SafetyGate(console=console, audit=audit, approval_port=channel)
        sent: list[dict] = []
        session = ChatSession(
            gate=gate,
            provider=_Provider(),
            system_prefix="PREFIX",
            audit=audit,
            send_event=sent.append,
            approval_channel=channel,
        )
        session._registry = _Spatial(session._registry, [])
        session._question_channel = _Questions(ANSWERS)
        session.run_instruction(REQUEST)

        cards = [event for event in sent if event.get("type") == "approval_request"]
        assert cards, "게이트 승인 카드가 브라우저로 나가야 한다"
        commands = [item["command"] for item in cards[-1]["items"]]
        assert any(line.startswith("Store Sequence 210 Cue ") for line in commands)
        assert any(line.startswith("Store Timecode 9") for line in commands)
        # 아무도 답하지 않으면 거절 — 저장 줄은 한 건도 안 나간다.
        assert not [line for line in console.executed if line.startswith("Store ")]


def _audit_lines(audit: AuditLog) -> list[str]:
    root = Path(audit.directory if hasattr(audit, "directory") else audit._directory)
    lines: list[str] = []
    for path in sorted(root.rglob("*.jsonl")):
        lines.extend(p for p in path.read_text(encoding="utf-8").splitlines() if p.strip())
    return lines
