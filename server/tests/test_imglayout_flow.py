"""M5 — the full IMGLAYOUT flow through a real ``ChatSession`` (integration).

Wires M1's upload channel, M2's image-attachment types, and M3's
``analyse_layout_image`` tool together through M4's session plumbing
(``server/web/session.py`` build_toolset wiring) and drives ONE turn:

    layout_image_upload -> analyse_layout_image (structure JSON, annotations
    text/interpreted, unresolved) -> ask_user (the unresolved value, via the
    question channel) -> arrange_fixtures (the resulting plan)

Uses the same scripted-provider pattern as ``test_web_session.py``
(``ScriptedProvider`` from ``test_runner_self_correction``) and the same
console double as ``test_spatial_arrange.py`` (``ArrangeConsole`` — the only
fake in this codebase that plays state/property/execution together, which
``arrange_fixtures``'s real backup-before-write path needs). No real network
calls: every ``LLMProvider.complete()`` — including the ONE vision call
``analyse_layout_image`` makes internally, since M4 wires the session's
single active provider as both the orchestrator model and the vision model
(server/llm/factory.py builds exactly one active adapter) — is answered by
the same pre-scripted list, in the order the real code actually calls it.
"""

from __future__ import annotations

import base64
import json

from server.llm.types import ModelTurn, ToolCall, Usage
from server.safety.audit import AuditLog
from server.safety.console import ExecOutcome
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock
from server.web.approval_bridge import ApprovalChannel
from server.web.question import QuestionRequest
from server.web.session import ChatSession

from .test_runner_self_correction import ScriptedProvider
from .test_spatial_arrange import ArrangeConsole, ScriptedApprovalPort

_PREFIX = "PREFIX"
_PNG_MIME = "image/png"


class _GateArrangeConsole(ArrangeConsole):
    """``ArrangeConsole`` speaks ``orchestrator.ports.ExecutionResult`` — the
    shape ``test_spatial_arrange.py`` wires straight into ``build_toolset``'s
    ``execution_port``, bypassing ``SafetyGate`` entirely. This test instead
    goes through the REAL gate (as production ``ChatSession`` wiring does),
    whose console contract is ``server.safety.console.ExecOutcome``
    (``.status``/``.detail``) — so only the return-type translation is
    overridden; the write/lie/float32 mutation stays ``ArrangeConsole``'s.
    """

    def execute(self, command: str) -> ExecOutcome:
        result = super().execute(command)
        return ExecOutcome(status="ok" if result.ok else "failed", detail=result.detail)


def _tool_turn(name: str, arguments: dict, call_id: str) -> ModelTurn:
    return ModelTurn(
        text="",
        tool_calls=(ToolCall(id=call_id, name=name, arguments=arguments),),
        stop_reason="tool_use",
        usage=Usage(),
        provider="scripted",
    )


def _final(text: str) -> ModelTurn:
    return ModelTurn(
        text=text, tool_calls=(), stop_reason="end", usage=Usage(), provider="scripted"
    )


class _FakeQuestionChannel:
    """The ``QuestionChannel`` shape the ``ask_user`` tool needs — bind() is
    a no-op (nothing here renders a live UI), ask() answers synchronously
    from a fixed script, mirroring the nested class ``test_web_session.py``
    uses for the SAME port."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.asked: list[QuestionRequest] = []

    def bind(self, notify, *, session_key=None) -> None:  # noqa: ANN001 — test double
        del notify, session_key

    def ask(self, request: QuestionRequest, **_kwargs) -> str:
        self.asked.append(request)
        return self.answers.pop(0) if self.answers else ""


class TestImgLayoutFlow:
    def test_upload_analyse_question_arrange_end_to_end(self, tmp_path):
        # fids 101/102/103 (slot != fid on purpose, per rig_object's warning),
        # all at the origin.
        console = _GateArrangeConsole(
            [(slot, slot + 100, f"PAR {slot}", 0.0, 0.0, 0.0) for slot in range(1, 4)]
        )
        audit = AuditLog(tmp_path / "audit")
        gate = SafetyGate(
            console=console,
            audit=audit,
            approval_port=ScriptedApprovalPort(True),
            lock=LiveLock(),
        )
        question_channel = _FakeQuestionChannel(["1.5"])
        vision_payload = {
            "pattern": "rings",
            "layers": [{"count": 3, "note": "inner ring"}],
            "symmetry": "radial",
            "confidence": "high",
            "annotations": [
                {"text": "간격 2m", "interpreted": {"spacing": 2.0}, "applies_to": "inner ring"}
            ],
            "unresolved": ["장비 높이(z)"],
        }
        provider = ScriptedProvider(
            [
                _tool_turn(
                    "analyse_layout_image",
                    {"description": "원형 배치 스케치, 안쪽 링 3대"},
                    "analyse-1",
                ),
                _final(json.dumps(vision_payload, ensure_ascii=False)),
                _tool_turn(
                    "ask_user",
                    {
                        "prompt": "장비 높이(z)를 몇 미터로 할까요?",
                        "options": [{"label": "1.5m"}],
                        "why": "이미지 주석에 높이가 없습니다.",
                    },
                    "ask-1",
                ),
                _tool_turn(
                    "arrange_fixtures",
                    {"preset": "elevation", "fids": [101, 102, 103], "height": 1.5},
                    "arrange-1",
                ),
                _final("안쪽 링 3대의 높이를 1.5m로 배치했습니다"),
            ]
        )
        sent: list[dict] = []
        session = ChatSession(
            gate=gate,
            provider=provider,
            system_prefix=_PREFIX,
            audit=audit,
            send_event=sent.append,
            approval_channel=ApprovalChannel(timeout_seconds=1.0),
            question_channel=question_channel,
        )

        content_base64 = base64.b64encode(b"pretend-png-bytes").decode()
        session.upload_layout_image("stage-sketch.png", _PNG_MIME, content_base64)

        event = session.run_instruction("첨부한 이미지를 분석해서 배치를 제안해줘")

        # -- the vision call actually received the uploaded image bytes --------
        vision_call_conversation = provider.calls[1]
        (vision_message,) = vision_call_conversation[-1:]
        (image,) = vision_message.images
        assert image.mime_type == _PNG_MIME
        assert image.content_base64 == content_base64

        # -- the unresolved value was asked through the question channel -------
        assert len(question_channel.asked) == 1
        assert "높이" in question_channel.asked[0].prompt

        # -- the resulting plan actually reached the console (write path) ------
        assert console.written_fids == {101, 102, 103}
        for fid in (101, 102, 103):
            assert console.coordinates(fid)[2] == 1.5

        # -- chat surface reports success, not a gate-truth demotion -----------
        assert event["type"] == "chat_response"
        assert event["status"] == "ok"
        assert event["text"] == "안쪽 링 3대의 높이를 1.5m로 배치했습니다"
        assert all(command["status"] == "executed_ok" for command in event["commands"])
