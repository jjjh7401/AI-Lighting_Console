"""Chat session tests (M5 — REQ-MVP-020/022/044 + M4 UI-half surfaces).

The session drives one Korean instruction through the REAL M4 gate + M3
orchestrator (scripted provider, in-memory fake console) and reports gate
TRUTH in Korean: blocked / held / unconfirmed / partial states are never
rendered as success (Section D chat-surface honesty).

AC-MVP-030 (1)(2)(3) lands here for BOTH provider adapter paths: real SDK
exceptions are raised inside the real adapters, and the tests assert (1) no raw
SDK text in ANY chat-surface event, (2) a Korean user message, (3) the raw
detail present in the diagnostic (audit) log.
"""

from __future__ import annotations

import json
import threading

import anthropic
import httpx
from google.genai import errors as genai_errors

from server.llm.anthropic_adapter import AnthropicAdapter
from server.llm.config import AnthropicSettings, GeminiSettings
from server.llm.gemini_adapter import GeminiAdapter
from server.llm.types import ModelTurn, ToolCall, ToolResult, UserMessage
from server.orchestrator.last_created import LastCreated
from server.orchestrator.tools import CommandOutcome, ToolExecution
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.measure import RoundTripRecorder
from server.web.question import UNANSWERED, QuestionRequest
from server.web.session import (
    HISTORY_MAX_MESSAGES,
    ChatSession,
    outcome_view,
    summarize_outcomes,
)

from .test_runner_self_correction import ScriptedProvider, _final, _run_turn
from .test_safety_gate import FakeConsole

_PREFIX = "PREFIX"


def _session(
    tmp_path,
    provider,
    *,
    console=None,
    channel=None,
    recorder=None,
    preshow_receive_port=None,
    preshow_osc_slot=None,
    **gate_kwargs,
):
    console = console or FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = channel or ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel, **gate_kwargs)
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=provider,
        system_prefix=_PREFIX,
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        recorder=recorder,
        preshow_receive_port=preshow_receive_port,
        preshow_osc_slot=preshow_osc_slot,
    )
    return session, console, audit, sent, channel


def _surface_text(sent: list[dict]) -> str:
    """Everything the chat surface would ever render, as one string."""
    return json.dumps(sent, ensure_ascii=False)


class TestOutcomeViews:
    def test_korean_labels_for_every_status(self):
        cases = {
            "executed_ok": "실행 완료",
            "failed": "실행 실패",
            "not_executed": "미실행",
            "skipped_already_executed": "중복 실행 방지",
            "blocked": "차단됨",
            "rejected": "거부됨",
            "proposal": "제안",
            "held": "승인 대기",
        }
        for status, expected in cases.items():
            view = outcome_view(CommandOutcome(command="List", status=status, detail="d"))
            assert expected in view["label"], (status, view)

    def test_unconfirmed_execution_is_reported_as_unconfirmed_not_failed(self):
        # REQ-MVP-032 UI half: the gate marks the detail; the surface must say
        # 실행 미확인 — never 실패, never success.
        outcome = CommandOutcome(
            command="Store Cue 1",
            status="failed",
            detail="execution unconfirmed — the command may or may not have run",
        )
        view = outcome_view(outcome)
        assert view["status"] == "unconfirmed"
        assert "실행 미확인" in view["label"]

    def test_partial_execution_summary(self):
        views = [
            outcome_view(CommandOutcome(command="A", status="executed_ok")),
            outcome_view(CommandOutcome(command="B", status="failed", detail="err")),
            outcome_view(CommandOutcome(command="C", status="not_executed")),
        ]
        summary = summarize_outcomes("ok", views)
        assert "부분 실행" in summary or "일부" in summary


class TestHappyPath:
    def test_korean_instruction_executes_and_reports_in_korean(self, tmp_path):
        provider = ScriptedProvider(
            [_run_turn(["Store Group 3"], "c1"), _final("보컬 그룹을 만들었습니다")]
        )
        recorder = RoundTripRecorder()
        session, console, _audit, sent, _ = _session(tmp_path, provider, recorder=recorder)
        event = session.run_instruction("보컬 그룹 만들어줘")
        assert event["type"] == "chat_response"
        assert event["status"] == "ok"
        assert event["text"] == "보컬 그룹을 만들었습니다"
        assert console.executed == ["Store Group 3"]
        preview_events = [e for e in sent if e["type"] == "execution_preview"]
        assert len(preview_events) == 1
        assert preview_events[0]["commands"][0]["command"] == "Store Group 3"
        (command,) = event["commands"]
        assert command["status"] == "executed_ok"
        assert "실행 완료" in command["label"]
        assert sent[-1] == event
        # Measurement: one judged record with a console-result end event.
        (record,) = recorder.records
        assert record.judged is True
        assert record.console_results == 1

    def test_failure_is_reported_in_korean_after_retries_exhausted(self, tmp_path):
        from .test_runner_self_correction import AlwaysFailingCommandProvider

        provider = AlwaysFailingCommandProvider("Store Cue 9")
        console = FakeConsole()
        console.fail_on["Store Cue 9"] = "console says no"
        session, _console, _audit, sent, _ = _session(tmp_path, provider, console=console)
        event = session.run_instruction("큐 9 저장해줘")
        assert event["status"] == "retries_exhausted"
        assert "실패" in event["summary"]
        assert any(c["status"] == "failed" for c in event["commands"])


class TestApprovalFlow:
    def test_approval_request_reaches_the_surface_and_approve_executes(self, tmp_path):
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 5"], "c1"), _final("시퀀스 5를 삭제했습니다")]
        )
        recorder = RoundTripRecorder()
        channel = ApprovalChannel(timeout_seconds=5.0, recorder=recorder)
        session, console, audit, sent, channel = _session(
            tmp_path, provider, channel=channel, recorder=recorder
        )

        def approve_when_asked():
            for event in sent:
                if event["type"] == "approval_request":
                    channel.resolve(event["request_id"], approved=True)
                    return True
            return False

        resolver = threading.Timer(0.05, approve_when_asked)
        # Poll until the request appears (the session blocks the calling thread).
        stop = threading.Event()

        def poller():
            while not stop.is_set():
                if approve_when_asked():
                    return
                stop.wait(0.01)

        poll_thread = threading.Thread(target=poller)
        poll_thread.start()
        try:
            event = session.run_instruction("시퀀스 5 지워줘")
        finally:
            stop.set()
            poll_thread.join(timeout=2.0)
            resolver.cancel()

        request_events = [e for e in sent if e["type"] == "approval_request"]
        preview_events = [e for e in sent if e["type"] == "execution_preview"]
        assert len(preview_events) == 1
        assert sent.index(preview_events[0]) < sent.index(request_events[0])
        assert preview_events[0]["risk_level"] == "danger"
        assert len(request_events) == 1
        (item,) = request_events[0]["items"]
        assert item["command"] == "Delete Sequence 5"
        assert item["risk_reasons"]  # risk reason shown (REQ-MVP-021)
        assert request_events[0]["actions"] == ["approve", "reject"]
        assert console.executed == ["Delete Sequence 5"]
        assert event["status"] == "ok"
        # Approval wait was measured and subtracted (nonnegative measured time).
        (record,) = recorder.records
        assert record.approval_wait_seconds > 0

    def test_rejection_voids_the_bundle_and_reports_in_korean(self, tmp_path):
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 6"], "c1"), _final("추가 확인이 필요합니다")]
        )
        channel = ApprovalChannel(timeout_seconds=1.0)
        session, console, audit, sent, channel = _session(tmp_path, provider, channel=channel)

        stop = threading.Event()

        def reject_when_asked():
            while not stop.is_set():
                for event in sent:
                    if event["type"] == "approval_request":
                        channel.resolve(event["request_id"], approved=False)
                        return
                stop.wait(0.01)

        thread = threading.Thread(target=reject_when_asked)
        thread.start()
        try:
            event = session.run_instruction("시퀀스 6 지워줘")
        finally:
            stop.set()
            thread.join(timeout=2.0)

        assert console.executed == []
        assert any(c["status"] == "rejected" for c in event["commands"])
        assert "거부" in event["summary"]

    def test_lock_first_wins_over_an_in_flight_approval(self, tmp_path):
        # REQ-MVP-035 through the async bridge: lock activation while the
        # approval is pending -> approval True still may not execute.
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 7"], "c1"), _final("잠금 상태입니다")]
        )
        channel = ApprovalChannel(timeout_seconds=5.0)
        session, console, audit, sent, channel = _session(tmp_path, provider, channel=channel)

        stop = threading.Event()

        def lock_then_approve():
            while not stop.is_set():
                for event in sent:
                    if event["type"] == "approval_request":
                        session.set_lock(True)
                        channel.resolve(event["request_id"], approved=True)
                        return
                stop.wait(0.01)

        thread = threading.Thread(target=lock_then_approve)
        thread.start()
        try:
            session.run_instruction("시퀀스 7 지워줘")
        finally:
            stop.set()
            thread.join(timeout=2.0)

        assert console.executed == []  # lock-first survived the async bridge
        proposals = [e for e in sent if e["type"] == "proposal"]
        assert proposals, "lock outcome must surface a proposal card"


class TestLockAndProposal:
    def test_lock_active_yields_proposal_cards_and_no_sends(self, tmp_path):
        provider = ScriptedProvider([_run_turn(["Store Cue 1"], "c1"), _final("잠금 중입니다")])
        session, console, _audit, sent, _ = _session(tmp_path, provider)
        session.set_lock(True)
        event = session.run_instruction("큐 1 저장해줘")
        assert console.executed == []
        proposals = [e for e in sent if e["type"] == "proposal"]
        assert proposals and proposals[0]["commands"] == ["Store Cue 1"]
        assert all(c["status"] == "proposal" for c in event["commands"])

    def test_set_lock_emits_status_events(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        on = session.set_lock(True)
        off = session.set_lock(False)
        assert on["live_lock"] is True
        assert off["live_lock"] is False
        statuses = [e for e in sent if e["type"] == "status"]
        assert [s["live_lock"] for s in statuses] == [True, False]


class TestFailureModeSurfaces:
    def test_console_offline_blocks_and_reports_in_korean(self, tmp_path):
        provider = ScriptedProvider([_run_turn(["Store Cue 1"], "c1"), _final("확인해 주세요")])
        session, console, _audit, sent, _ = _session(tmp_path, provider)
        session._gate.monitor.note_ping_timeout()  # no prior activity -> offline
        event = session.run_instruction("큐 1 저장해줘")
        assert console.executed == []
        assert "콘솔 오프라인" in event["summary"]
        statuses = [e for e in sent if e["type"] == "status"]
        assert statuses and statuses[-1]["health"] == "console_offline"
        assert statuses[-1]["executions_blocked"] is True

    def test_responder_degraded_blocks_and_reports_in_korean(self, tmp_path):
        provider = ScriptedProvider([_run_turn(["Store Cue 1"], "c1"), _final("확인해 주세요")])
        session, console, _audit, sent, _ = _session(tmp_path, provider)
        session._gate.monitor.note_activity()
        session._gate.monitor.note_ping_timeout()  # recent activity -> degraded
        event = session.run_instruction("큐 1 저장해줘")
        assert console.executed == []
        assert "응답기" in event["summary"] or "저하" in event["summary"]

    def test_unconfirmed_execution_reports_and_never_claims_success(self, tmp_path):
        provider = ScriptedProvider(
            [_run_turn(["Store Cue 2"], "c1"), _final("결과를 확인해 주세요")]
        )
        console = FakeConsole()
        console.unconfirmed_on.add("Store Cue 2")
        session, _console, _audit, sent, _ = _session(tmp_path, provider, console=console)
        event = session.run_instruction("큐 2 저장해줘")
        (command,) = [c for c in event["commands"] if c["command"] == "Store Cue 2"]
        assert command["status"] == "unconfirmed"
        assert "실행 미확인" in event["summary"]
        assert "완료" not in event["summary"]

    def test_backup_failure_notifies_and_blocks(self, tmp_path):
        provider = ScriptedProvider(
            [_run_turn(["Delete Sequence 5"], "c1"), _final("차단되었습니다")]
        )
        channel = ApprovalChannel(timeout_seconds=5.0)
        session, console, audit, sent, channel = _session(tmp_path, provider, channel=channel)

        class FailingBackup:
            def before_risky_execution(self):
                from server.safety.backup import BackupError

                raise BackupError("disk full")

            def session_start(self):
                pass

        session._gate._backup = FailingBackup()

        stop = threading.Event()

        def approve():
            while not stop.is_set():
                for event in sent:
                    if event["type"] == "approval_request":
                        channel.resolve(event["request_id"], approved=True)
                        return
                stop.wait(0.01)

        thread = threading.Thread(target=approve)
        thread.start()
        try:
            event = session.run_instruction("시퀀스 5 지워줘")
        finally:
            stop.set()
            thread.join(timeout=2.0)

        assert console.executed == []
        notices = [e for e in sent if e["type"] == "notice"]
        assert notices and "백업" in notices[0]["message"]
        assert "차단" in event["summary"]


_RAW_MARKERS = ("boom detail", "Error code", "429", "RateLimitError", "rate_limit_error")


def _anthropic_error(cls, status: int):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, request=request)
    return cls("boom detail", response=response, body=None)


class _RaisingAnthropicClient:
    def __init__(self, exc: Exception):
        class _Messages:
            @staticmethod
            def create(**kwargs):
                raise exc

        self.messages = _Messages()


class _RaisingGeminiModels:
    def __init__(self, exc: Exception):
        self._exc = exc

    def generate_content(self, **kwargs):
        raise self._exc


class _RaisingGeminiClient:
    def __init__(self, exc: Exception):
        self.models = _RaisingGeminiModels(exc)


class TestProviderErrorSurface:
    """AC-MVP-030 (1)(2)(3) — both real adapter paths, >=3 SDK errors each."""

    def _run_error_case(self, tmp_path, provider, expected_kind):
        session, _console, audit, sent, _ = _session(tmp_path, provider)
        event = session.run_instruction("보컬 그룹 만들어줘")
        # (1) NO raw SDK text anywhere on the chat surface.
        surface = _surface_text(sent)
        for marker in _RAW_MARKERS:
            assert marker not in surface, f"raw SDK text {marker!r} leaked to the chat surface"
        # (2) a Korean user error message is shown.
        assert event["type"] == "error"
        assert event["kind"] == expected_kind
        assert any("가" <= ch <= "힣" for ch in event["message"])
        # (3) the raw detail IS in the diagnostic (audit) log.
        errors = [e for e in audit.iter_events() if e["event"] == "provider_error"]
        assert len(errors) == 1
        assert errors[0]["kind"] == expected_kind
        assert "boom detail" in errors[0]["raw_detail"] or "429" in errors[0]["raw_detail"]

    def test_anthropic_rate_limit(self, tmp_path):
        adapter = AnthropicAdapter(
            AnthropicSettings(model="claude-opus-4-8"),
            client=_RaisingAnthropicClient(_anthropic_error(anthropic.RateLimitError, 429)),
        )
        self._run_error_case(tmp_path, adapter, "rate_limit")

    def test_anthropic_auth_failure(self, tmp_path):
        adapter = AnthropicAdapter(
            AnthropicSettings(model="claude-opus-4-8"),
            client=_RaisingAnthropicClient(_anthropic_error(anthropic.AuthenticationError, 401)),
        )
        self._run_error_case(tmp_path, adapter, "auth")

    def test_anthropic_server_error(self, tmp_path):
        adapter = AnthropicAdapter(
            AnthropicSettings(model="claude-opus-4-8"),
            client=_RaisingAnthropicClient(_anthropic_error(anthropic.InternalServerError, 500)),
        )
        self._run_error_case(tmp_path, adapter, "server")

    def test_gemini_rate_limit(self, tmp_path):
        adapter = GeminiAdapter(
            GeminiSettings(model="gemini-2.5-pro", context_caching=False),
            client=_RaisingGeminiClient(
                genai_errors.APIError(429, {"error": {"message": "boom detail"}})
            ),
        )
        self._run_error_case(tmp_path, adapter, "rate_limit")

    def test_gemini_auth_failure(self, tmp_path):
        adapter = GeminiAdapter(
            GeminiSettings(model="gemini-2.5-pro", context_caching=False),
            client=_RaisingGeminiClient(
                genai_errors.APIError(401, {"error": {"message": "boom detail"}})
            ),
        )
        self._run_error_case(tmp_path, adapter, "auth")

    def test_gemini_server_error(self, tmp_path):
        adapter = GeminiAdapter(
            GeminiSettings(model="gemini-2.5-pro", context_caching=False),
            client=_RaisingGeminiClient(
                genai_errors.APIError(503, {"error": {"message": "boom detail"}})
            ),
        )
        self._run_error_case(tmp_path, adapter, "server")

    def test_unexpected_exception_is_sanitized_too(self, tmp_path):
        class BoomProvider:
            name = "scripted"
            model_id = "m"
            supports_prompt_caching = False

            def complete(self, **kwargs):
                raise ValueError("super secret traceback detail")

        session, _console, audit, sent, _ = _session(tmp_path, BoomProvider())
        event = session.run_instruction("안녕")
        assert event["type"] == "error"
        assert "super secret" not in _surface_text(sent)
        errors = [e for e in audit.iter_events() if e["event"] == "provider_error"]
        assert "super secret" in errors[0]["raw_detail"]

    def test_gemini_missing_key_surfaces_korean_auth_not_unexpected(self, tmp_path, monkeypatch):
        # AC-DEPLOY-022 ② e2e: a Gemini adapter constructed with no client and no
        # env key surfaces the Korean AUTH message (not 'unexpected'); the raw
        # "No API key ..." detail goes to the audit log ONLY, never the surface.
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        adapter = GeminiAdapter(
            GeminiSettings(model="gemini-2.5-pro", context_caching=False),
            # no client injected → _ensure_client() builds a real genai.Client()
            # which raises ValueError("No API key ...") without a key in env.
        )
        session, _console, audit, sent, _ = _session(tmp_path, adapter)
        event = session.run_instruction("보컬 그룹 만들어줘")
        # (1) NO raw SDK/key text anywhere on the chat surface.
        surface = _surface_text(sent)
        assert "No API key" not in surface
        assert "ai.google.dev" not in surface
        # (2) a Korean AUTH user message is shown — NOT the 'unexpected' bucket.
        assert event["type"] == "error"
        assert event["kind"] == "auth"
        assert any("가" <= ch <= "힣" for ch in event["message"])
        # (3) the raw detail IS in the diagnostic (audit) log.
        errors = [e for e in audit.iter_events() if e["event"] == "provider_error"]
        assert len(errors) == 1
        assert errors[0]["kind"] == "auth"
        assert "No API key" in errors[0]["raw_detail"]

    def test_error_turn_is_never_judged(self, tmp_path):
        recorder = RoundTripRecorder()
        adapter = AnthropicAdapter(
            AnthropicSettings(model="claude-opus-4-8"),
            client=_RaisingAnthropicClient(_anthropic_error(anthropic.RateLimitError, 429)),
        )
        session, _console, _audit, _sent, _ = _session(tmp_path, adapter, recorder=recorder)
        session.run_instruction("보컬 그룹 만들어줘")
        (record,) = recorder.records
        assert record.judged is False


class TestLastCreatedSessionTracking:
    """AC-DEPLOY-021 (#4) — the session captures the just-created sequence/
    executor and injects it into the NEXT turn so a bare follow-up modification
    targets the real look (Seq 71 / Exec 201), not an arbitrary Seq 1 / Exec 1,
    and steers toward regeneration over a blind edit."""

    def test_creating_a_look_captures_last_created_state(self, tmp_path):
        # AC ①: after creating a look on Seq 71 / Exec 201, the last-created
        # state is present in the session.
        provider = ScriptedProvider(
            [
                _run_turn(["Store Sequence 71", "Assign Sequence 71 At Executor 201"], "c1"),
                _final("보컬 룩을 만들었습니다"),
            ]
        )
        session, console, _audit, _sent, _ = _session(tmp_path, provider)
        assert session._last_created is None  # nothing created yet
        session.run_instruction("보컬 룩 만들어줘")
        assert console.executed == ["Store Sequence 71", "Assign Sequence 71 At Executor 201"]
        assert session._last_created == LastCreated(sequence=71, executor=201)
        # No preamble was injected on the very first (create) turn.
        create_conversation = provider.calls[0]
        assert len(create_conversation) == 1
        assert create_conversation[0].text == "보컬 룩 만들어줘"

    def test_followup_turn_injects_the_last_created_target_and_regeneration_steer(self, tmp_path):
        # AC ②/③: a bare follow-up ("더 느리게") resolves to Seq 71 / Exec 201
        # via the injected session-context preamble, and the preamble carries
        # the regenerate-don't-blind-edit steer.
        provider = ScriptedProvider(
            [
                _run_turn(["Store Sequence 71", "Assign Sequence 71 At Executor 201"], "c1"),
                _final("보컬 룩을 만들었습니다"),
                _final("더 느리게 재생성했습니다"),
            ]
        )
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.run_instruction("보컬 룩 만들어줘")
        session.run_instruction("더 느리게")
        followup_conversation = provider.calls[2]
        # The follow-up now also carries the prior turn's transcript (rolling
        # memory): [user create, assistant reply, session-context, instruction].
        assert len(followup_conversation) == 4
        assert isinstance(followup_conversation[0], UserMessage)
        assert followup_conversation[0].text == "보컬 룩 만들어줘"
        assert isinstance(followup_conversation[1], ModelTurn)
        assert followup_conversation[1].text == "보컬 룩을 만들었습니다"
        preamble = followup_conversation[-2]
        assert isinstance(preamble, UserMessage)
        # AC ②: identity present — Seq 71 / Exec 201, NOT an arbitrary target.
        assert "71" in preamble.text
        assert "201" in preamble.text
        # AC ③: regeneration is preferred over a blind edit.
        assert "regenerat" in preamble.text.lower()
        # the real instruction follows the injected note
        assert followup_conversation[-1].text == "더 느리게"

    def test_last_created_snapshot_is_not_an_accumulating_history(self, tmp_path):
        # A second creation replaces (not appends to) the snapshot — the single
        # most-recent look only.
        provider = ScriptedProvider(
            [
                _run_turn(["Store Sequence 71", "Assign Sequence 71 At Executor 201"], "c1"),
                _final("첫 룩"),
                _run_turn(["Store Sequence 72", "Assign Sequence 72 At Executor 202"], "c2"),
                _final("둘째 룩"),
            ]
        )
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.run_instruction("첫 룩 만들어줘")
        assert session._last_created == LastCreated(sequence=71, executor=201)
        session.run_instruction("둘째 룩 만들어줘")
        assert session._last_created == LastCreated(sequence=72, executor=202)

    def test_non_creating_turn_preserves_the_prior_snapshot(self, tmp_path):
        # A follow-up turn that creates nothing keeps pointing at the last look.
        provider = ScriptedProvider(
            [
                _run_turn(["Store Sequence 71", "Assign Sequence 71 At Executor 201"], "c1"),
                _final("룩 생성"),
                _final("확인만 했습니다"),
            ]
        )
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.run_instruction("룩 만들어줘")
        session.run_instruction("지금 상태 어때?")
        assert session._last_created == LastCreated(sequence=71, executor=201)

    def test_prior_turns_are_replayed_to_the_model_as_context(self, tmp_path):
        # A non-layout follow-up must see earlier turns: the model receives the
        # rolling transcript, not just the bare current instruction.
        provider = ScriptedProvider([_final("첫 답"), _final("둘째 답")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.run_instruction("사파리 리그 상태 알려줘")
        session.run_instruction("그럼 아까 그건 어때?")
        second_conversation = provider.calls[1]
        assert [type(item) for item in second_conversation] == [
            UserMessage,
            ModelTurn,
            UserMessage,
        ]
        assert second_conversation[0].text == "사파리 리그 상태 알려줘"
        assert second_conversation[1].text == "첫 답"
        assert second_conversation[2].text == "그럼 아까 그건 어때?"

    def test_history_window_is_bounded_to_recent_exchanges(self, tmp_path):
        provider = ScriptedProvider([_final(f"답 {n}") for n in range(11)])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        for n in range(11):  # turns 0..10 -> provider.calls[0..10]
            session.run_instruction(f"지시 {n}")
        # The final turn's replayed history never exceeds the bound (2 messages
        # per exchange), and it holds the MOST RECENT exchanges, not the oldest.
        last_conversation = provider.calls[10]
        assert len(last_conversation) == HISTORY_MAX_MESSAGES + 1  # + current instruction
        # Before turn 10, exchanges 0..9 were recorded; trimmed to the last 8.
        assert last_conversation[0].text == f"지시 {10 - HISTORY_MAX_MESSAGES // 2}"
        assert last_conversation[-1].text == "지시 10"

    def test_restored_transcript_seeds_a_fresh_session_and_reaches_the_model(self, tmp_path):
        # Refresh survival: the client reinjects its persisted transcript, and
        # the NEXT model turn sees those messages as prior context.
        provider = ScriptedProvider([_final("이어서 진행합니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.restore_history(
            [
                {"role": "user", "text": "링 배치해줘"},
                {"role": "assistant", "text": "3개 링을 배치했습니다"},
            ]
        )
        session.run_instruction("아까 그거 반지름만 5m로 바꿔줘")

        conversation = provider.calls[0]
        assert isinstance(conversation[0], UserMessage)
        assert conversation[0].text == "링 배치해줘"
        assert isinstance(conversation[1], ModelTurn)
        assert conversation[1].text == "3개 링을 배치했습니다"
        assert conversation[-1].text == "아까 그거 반지름만 5m로 바꿔줘"

    def test_restore_never_overwrites_live_session_memory(self, tmp_path):
        provider = ScriptedProvider([_final("첫 답"), _final("둘째 답")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.run_instruction("실제 첫 지시")  # live turn recorded
        session.restore_history([{"role": "user", "text": "낡은 복원 기록"}])
        session.run_instruction("둘째 지시")

        second_conversation = provider.calls[1]
        # The live exchange survives; the late restore frame was ignored.
        assert second_conversation[0].text == "실제 첫 지시"
        assert all(
            item.text != "낡은 복원 기록" for item in second_conversation if hasattr(item, "text")
        )

    def test_restore_caps_to_the_rolling_window(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session.restore_history(
            [{"role": "user", "text": f"지시 {n}"} for n in range(HISTORY_MAX_MESSAGES + 10)]
        )
        assert len(session._history) == HISTORY_MAX_MESSAGES
        assert session._history[-1].text == f"지시 {HISTORY_MAX_MESSAGES + 9}"


class TestAllFixturesElevation:
    def test_uses_complete_spatial_read_and_preserves_xy(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                if call.name == "get_spatial_context":
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(
                                {
                                    "fixtures": [{"fid": 20}, {"fid": 21}],
                                    "coverage": {"complete": True},
                                }
                            ),
                            is_error=False,
                        )
                    )
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content="{}",
                        is_error=False,
                    ),
                    (CommandOutcome(command="Set Fixture 20 PosZ 5.0", status="proposal"),),
                )

        session._registry = Registry()
        event = session.run_instruction(
            "3D 레이아웃의 모든 장비를 바닥으로부터 5미터 높이로 올려줘"
        )

        assert event["text"].startswith("전체 배치 장비 2대")
        assert event["commands"][0]["status"] == "proposal"

        assert provider.calls == []
        assert [call.name for call in calls] == ["get_spatial_context", "arrange_fixtures"]
        assert calls[1].arguments == {
            "preset": "elevation",
            "fids": [20, 21],
            "height": 5.0,
        }

    def test_routes_stage_floor_height_vocabulary_without_model_tool_call(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps(
                                {
                                    "fixtures": [{"fid": 20}, {"fid": 21}],
                                    "coverage": {"complete": True},
                                }
                            )
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    )
                )

        session._registry = Registry()
        session.run_instruction("전체 조명을 무대 위 5m로 배치해줘")

        assert provider.calls == []
        assert calls[-1].arguments == {
            "preset": "elevation",
            "fids": [20, 21],
            "height": 5.0,
        }

    def test_vocabulary_request_reaches_the_model_with_reasoning_guidance(self, tmp_path):
        # No canned keyword reply: a "짝지어/번갈아" request now REASONS via the
        # model, and the model receives guidance about the missing parameters
        # rather than a reflexive one-liner short-circuiting the turn.
        provider = ScriptedProvider([_final("링 구성을 확인하겠습니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)

        event = session.run_instruction("MMX와 350M을 짝지어 좌→우로 배치해줘")

        assert len(provider.calls) == 1  # went to the model, not a canned handler
        context_note = provider.calls[0][0].text
        assert "짝지어" in context_note or "번갈아" in context_note
        assert "ask_user" in context_note
        assert event["text"] == "링 구성을 확인하겠습니다"

    def test_reuses_complete_spatial_fixture_ids_for_repeated_elevation(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                content = json.dumps(
                    {"fixtures": [{"fid": 20}, {"fid": 21}], "coverage": {"complete": True}}
                )
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=content if call.name == "get_spatial_context" else "{}",
                        is_error=False,
                    )
                )

        session._registry = Registry()
        request = "3D 레이아웃의 모든 장비를 바닥으로부터 5미터 높이로 올려줘"
        session.run_instruction(request)
        session.run_instruction(request)

        assert [call.name for call in calls] == [
            "get_spatial_context",
            "arrange_fixtures",
            "arrange_fixtures",
        ]
        assert calls[-1].arguments["fids"] == [20, 21]

    def test_routes_repeating_mmx_mmx_350_columns_without_model_tool_call(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [
                    *[{"fid": fid, "name": f"MMX {fid}"} for fid in range(1, 21)],
                    *[{"fid": fid, "name": f"350M {fid}"} for fid in range(21, 31)],
                ]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    )
                )

        session._registry = Registry()
        session.run_instruction(
            "1열: MMX 10대, 2열: MMX 10대, 3열: 350 10대 다음과 같이 반복해서 "
            "모든 장비를 배치해줘. 열간 간격은 1.5미터, 장비간의 간격은 1미터로 배치해줘"
        )

        assert provider.calls == []
        assert [call.name for call in calls] == ["get_spatial_context", "arrange_fixtures"]
        assert calls[-1].arguments == {
            "preset": "grid",
            "fids": list(range(1, 31)),
            "rows": 3,
            "columns": 10,
            "row_spacing": 1.5,
            "column_spacing": 1.0,
            "orientation": "xy",
        }

    def test_places_all_complete_columns_across_types_not_just_the_first(self, tmp_path):
        # Regression: 19 MMX + 20 beam must place 3 full columns (MMX,350,350 =
        # 30 fixtures), never one MMX column while abandoning all 20 beams.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [
                    *[{"fid": fid, "name": f"MMX {fid}"} for fid in range(1, 20)],  # 19
                    *[{"fid": fid, "name": f"RLB350M {fid}"} for fid in range(20, 40)],  # 20
                ]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    )
                )

        session._registry = Registry()
        event = session.run_instruction(
            "1열 MMX 10대, 2열 MMX 10대, 3열 350 10대 반복 배치해줘. "
            "열간 간격은 1.5미터, 장비간의 간격은 1미터"
        )

        assert calls[-1].arguments["rows"] == 3
        assert calls[-1].arguments["fids"] == [*range(1, 11), *range(20, 30), *range(30, 40)]
        assert "MMX 9대" in event["text"]  # honest remainder, not silently dropped

    def test_missing_spacing_is_collected_one_card_at_a_time(self, tmp_path):
        # Instead of a prose wall, each missing gap becomes its OWN card, asked
        # one at a time; after both answers the placement runs.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [
                    *[{"fid": fid, "name": f"MMX {fid}"} for fid in range(1, 21)],
                    *[{"fid": fid, "name": f"RLB350M {fid}"} for fid in range(21, 31)],
                ]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    )
                )

        class FakeQuestionChannel:
            def __init__(self, answers):
                self.answers = list(answers)
                self.asked: list[QuestionRequest] = []

            def ask(self, request, **_kwargs):
                self.asked.append(request)
                return self.answers.pop(0) if self.answers else UNANSWERED

        channel = FakeQuestionChannel(["1.5m", "1m"])
        session._registry = Registry()
        session._question_channel = channel
        session.run_instruction(
            "1열 MMX 10대, 2열 MMX 10대, 3열 350 10대 반복 배치해줘"  # no spacing given
        )

        # Two separate cards, one per gap, each offering clickable presets.
        assert len(channel.asked) == 2
        assert "열간" in channel.asked[0].prompt
        assert [opt.label for opt in channel.asked[0].options] == ["1m", "1.5m", "2m"]
        assert "좌우" in channel.asked[1].prompt
        # Collected answers drive the real placement.
        assert calls[-1].name == "arrange_fixtures"
        assert calls[-1].arguments["row_spacing"] == 1.5
        assert calls[-1].arguments["column_spacing"] == 1.0

    def test_missing_spacing_falls_back_to_prose_without_a_question_channel(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        session._question_channel = None
        event = session.run_instruction("1열 MMX 10대, 2열 MMX 10대, 3열 350 10대 반복 배치해줘")
        assert "미터 단위로 알려주세요" in event["text"]

    def test_bare_grid_request_reasons_via_model_not_a_canned_reply(self, tmp_path):
        # The canned "행×열과 간격이 필요합니다" reflex is gone: a bare grid
        # request now reaches the model to reason and ask holistically.
        provider = ScriptedProvider([_final("몇 행 몇 열로 놓을지 함께 정해요")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        event = session.run_instruction("장비를 바둑판으로 배치해줘")
        assert len(provider.calls) == 1
        assert event["text"] == "몇 행 몇 열로 놓을지 함께 정해요"

    def test_session_note_carries_established_spacing(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        assert session._session_context_note() is None
        session._last_layout_spacing = (1.5, 1.0)
        note = session._session_context_note()
        assert note is not None
        assert "column gap 1.5 m" in note
        assert "fixture gap 1 m" in note

    def test_places_complete_columns_and_reports_leftovers(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [
                    *[{"fid": fid, "name": f"Robin MMX Spot {fid}"} for fid in range(1, 26)],
                    *[{"fid": fid, "name": f"Robin LEDBeam 350 {fid}"} for fid in range(26, 36)],
                ]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    )
                )

        session._registry = Registry()
        event = session.run_instruction(
            "1열 MMX 10대, 2열 MMX 10대, 3열 350 10대 반복 배치해줘. "
            "열간 간격은 1.5미터, 장비간의 간격은 1미터"
        )

        assert provider.calls == []
        # 25 MMX + 10 beam -> MMX,MMX,350 = 3 full columns (20 MMX + 10 beam); 5 MMX left over.
        assert calls[-1].arguments["fids"] == [*range(1, 21), *range(26, 36)]
        assert calls[-1].arguments["rows"] == 3
        assert "MMX 25대" in event["text"]
        assert "350 계열 10대" in event["text"]
        assert "MMX 5대" in event["text"]

    def test_reports_actual_counts_when_no_column_can_form(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [{"fid": fid, "name": f"MMX {fid}"} for fid in range(1, 6)]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=json.dumps({"fixtures": fixtures, "coverage": {"complete": True}}),
                    )
                )

        session._registry = Registry()
        event = session.run_instruction(
            "1열 MMX 10대, 2열 MMX 10대, 3열 350 10대 반복 배치해줘. "
            "열간 간격은 1.5미터, 장비간의 간격은 1미터"
        )

        assert provider.calls == []
        assert [call.name for call in calls] == ["get_spatial_context"]
        assert "MMX 5대" in event["text"]
        assert "최소 10대" in event["text"]

    def test_remembers_repeating_layout_until_spacing_follow_up(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [
                    *[{"fid": fid, "name": f"MMX {fid}"} for fid in range(1, 21)],
                    *[{"fid": fid, "name": f"350M {fid}"} for fid in range(21, 31)],
                ]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    )
                )

        session._registry = Registry()
        first = session.run_instruction(
            "1열: MMX 10대, 2열: MMX 10대, 3열: 350 10대 반복해서 모든 장비를 배치해줘"
        )
        question = session.run_instruction("내가 뭘 알려주면 돼?")
        session.run_instruction("장비간의 좌우간격은 1미터, 열간 간격은 1.5미터")

        assert "기억했습니다" in first["text"]
        assert "반복 배치를 계속 준비 중" in question["text"]
        assert provider.calls == []
        assert calls[-1].arguments["row_spacing"] == 1.5
        assert calls[-1].arguments["column_spacing"] == 1.0

    def test_routes_typed_two_row_layout_without_model_tool_call(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                if call.name == "get_spatial_context":
                    fixtures = [
                        *[{"fid": fid, "name": f"350M {fid}"} for fid in range(1, 11)],
                        *[{"fid": fid, "name": f"MMX {fid}"} for fid in range(11, 21)],
                    ]
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(
                                {"fixtures": fixtures, "coverage": {"complete": True}}
                            ),
                        )
                    )
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                    (CommandOutcome(command="Set Fixture 1 PosX '0.0'", status="proposal"),),
                )

        session._registry = Registry()
        event = session.run_instruction(
            "제일 뒤쪽부터 MMX 10대, 그 앞줄에 350M 10대를 1.5미터 간격으로 배치해줘"
        )

        assert provider.calls == []
        assert event["commands"][0]["status"] == "proposal"
        assert calls[1].arguments == {
            "preset": "grid",
            "fids": list(range(1, 21)),
            "rows": 2,
            "columns": 10,
            "spacing": 1.5,
            "orientation": "xy",
        }

    def test_routes_whole_rig_vocabulary_grid_without_model_tool_call(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [{"fid": fid} for fid in range(1, 5)]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    ),
                    (CommandOutcome(command="Set Fixture 1 PosX '0.0'", status="proposal"),),
                )

        session._registry = Registry()
        event = session.run_instruction("모든 장비를 2행×2열 그리드로 1.5m 간격 배치해줘")

        assert provider.calls == []
        assert event["commands"][0]["status"] == "proposal"
        assert [call.name for call in calls] == ["get_spatial_context", "arrange_fixtures"]
        assert calls[-1].arguments == {
            "preset": "grid",
            "fids": [1, 2, 3, 4],
            "rows": 2,
            "columns": 2,
            "spacing": 1.5,
        }


class TestPointFixturesAtTarget:
    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
            {"fid": 41, "name": "Sphere 1", "x": 0.0, "y": 0.0, "z": 0.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                if call.name == "get_spatial_context":
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(
                                {"fixtures": fixtures, "coverage": {"complete": True}}
                            ),
                        )
                    )
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                    (CommandOutcome(command="Fixture 20", status="proposal"),),
                )

        return Registry()

    def test_routes_centre_pointing_without_model_and_skips_the_on_target_fixture(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction(
            "모든 장비를 선택해서 불을 켜고 무대 바닥 중앙(0,0,0) 위치로 "
            "조명장비의 헤드가 바라볼 수 있도록 해줘"
        )

        assert provider.calls == []
        assert [call.name for call in calls] == ["get_spatial_context", "run_commands"]
        commands = calls[-1].arguments["commands"]
        # ONE chained line per fixture (text-dedupe defence); the measured aim
        # for FID 20 at (4,0,6) -> origin: Pan 90 / Tilt 33.7, mirrored fixture
        # gets the mirrored pan; the sphere ON the target is skipped, and
        # 불을 켜고 turns the dimmer on.
        assert commands == [
            "Fixture 20 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7",
            "Fixture 26 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At -90 ; Attribute 'Tilt' At 33.7",
        ]
        assert "2대" in event["text"]
        assert "1대(FID 41)" in event["text"]

    def test_an_explicit_coordinate_triple_overrides_the_centre_words(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction("전체 헤드가 (2, -3, 0.5) 지점을 바라보게 해줘")

        assert calls[-1].name == "run_commands"
        assert "(2, -3, 0.5)" in event["text"]
        commands = calls[-1].arguments["commands"]
        # No dimmer word -> no dimmer line.
        assert not any("Dimmer" in command for command in commands)

    def test_an_aiming_verb_without_a_target_goes_to_the_model(self, tmp_path):
        provider = ScriptedProvider([_final("어느 지점을 바라보게 할까요?")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)

        event = session.run_instruction("무빙헤드가 저쪽을 바라보게 해줘")

        assert len(provider.calls) == 1
        assert event["text"] == "어느 지점을 바라보게 할까요?"


class TestLookPanTilt:
    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
            {"fid": 41, "name": "Sphere 1", "x": 0.0, "y": 0.0, "z": 0.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                if call.name == "get_spatial_context":
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(
                                {"fixtures": fixtures, "coverage": {"complete": True}}
                            ),
                        )
                    )
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                    (CommandOutcome(command="Fixture 20", status="proposal"),),
                )

        return Registry()

    def test_a_fan_request_spreads_pan_over_the_x_ordered_chain(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction("전체 장비를 불 켜고 45도 부채살로 펼쳐줘")

        assert provider.calls == []
        assert [call.name for call in calls] == ["get_spatial_context", "run_commands"]
        # x-ordered chain 26(-4) -> 41(0) -> 20(4); base pan 180, offsets
        # -45/0/+45, tilt 45, dimmer on.
        assert calls[-1].arguments["commands"] == [
            "Fixture 26 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At 135 ; Attribute 'Tilt' At 45",
            "Fixture 41 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At 180 ; Attribute 'Tilt' At 45",
            "Fixture 20 ; Attribute 'Dimmer' At 100 ; "
            "Attribute 'Pan' At -135 ; Attribute 'Tilt' At 45",
        ]
        assert "부채살" in event["text"]

    def test_a_ring_out_request_skips_the_centroid_fixture_and_can_store_a_preset(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction("장비들이 바깥쪽을 바라보게 하고 프리셋 11로 저장해줘")

        commands = calls[-1].arguments["commands"]
        # Centroid is (0,0): the sphere ON it has no outward radial and is
        # skipped; 20/26 aim 4 m outward (target z=0 -> tilt 33.7) with
        # mirrored pans; the explicit preset number appends the store+label.
        assert commands == [
            "Fixture 20 ; Attribute 'Pan' At -90 ; Attribute 'Tilt' At 33.7",
            "Fixture 26 ; Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7",
            "Store Preset 2.11",
            "Label Preset 2.11 'RING OUT'",
        ]
        assert "1대(FID 41)" in event["text"]
        assert "2.11" in event["text"]

    def test_a_ring_in_request_converges_on_the_centroid(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        session.run_instruction("모든 장비가 안쪽을 바라보게 해줘")

        commands = calls[-1].arguments["commands"]
        assert "Fixture 20 ; Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7" in commands
        assert "Fixture 26 ; Attribute 'Pan' At -90 ; Attribute 'Tilt' At 33.7" in commands

    def test_a_centre_pointing_request_still_reaches_the_focus_handler(self, tmp_path):
        # "중앙을 바라보게" carries an aiming verb but no fan/ring word — it
        # must fall through to the FOCUS handler, not be eaten by LOOK.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction("모든 장비가 무대 중앙을 바라보게 해줘")

        assert "지점을 향하도록" in event["text"]


class TestMultiRingCircle:
    def test_asks_radii_and_order_then_places_three_rings(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall) -> ToolExecution:
                calls.append(call)
                fixtures = [
                    *[{"fid": f, "name": f"MMX {f}", "x": f, "y": 0.0} for f in range(1, 20)],
                    *[{"fid": f, "name": f"RLB350 {f}", "x": f, "y": 1.0} for f in range(20, 40)],
                    {"fid": 40, "name": "Sharpy 250W Beam", "x": 40.0, "y": 2.0},
                ]
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=(
                            json.dumps({"fixtures": fixtures, "coverage": {"complete": True}})
                            if call.name == "get_spatial_context"
                            else "{}"
                        ),
                    ),
                    (CommandOutcome(command="Set Fixture 1 Posx '2.0'", status="proposal"),),
                )

        class FakeQuestionChannel:
            def __init__(self, answers):
                self.answers = list(answers)
                self.asked: list[QuestionRequest] = []

            def ask(self, request, **_kwargs):
                self.asked.append(request)
                return self.answers.pop(0) if self.answers else UNANSWERED

        channel = FakeQuestionChannel(["4·6·8m", "FID 오름차순"])
        session._registry = Registry()
        session._question_channel = channel
        session.run_instruction(
            "장비를 여러 겹의 원형으로 배치할거야. 가장 안쪽에 mmx 8대 , 2번째원은 "
            "RLB350 12대, 3번째 원은 남은 장비들을 번갈아 배치해줘."
        )

        assert provider.calls == []  # reasoned + executed directly, no model wall
        # Two cards, one at a time: radii first, then the remainder-ring order.
        assert len(channel.asked) == 2
        assert "지름" in channel.asked[0].prompt
        assert [o.label for o in channel.asked[0].options] == ["4·6·8m", "6·8·10m"]
        assert "번갈아" in channel.asked[1].prompt
        # Three circle writes, innermost first, with the parsed radii.
        writes = [c for c in calls if c.name == "arrange_fixtures"]
        assert len(writes) == 3
        assert [w.arguments["preset"] for w in writes] == ["circle", "circle", "circle"]
        assert writes[0].arguments["fids"] == list(range(1, 9))  # MMX 1~8
        assert writes[0].arguments["radius"] == 2.0
        assert writes[1].arguments["fids"] == list(range(20, 32))  # RLB350 20~31
        assert writes[1].arguments["radius"] == 3.0
        assert writes[2].arguments["radius"] == 4.0
        assert writes[2].arguments["fids"] == [
            9,
            32,
            10,
            33,
            11,
            34,
            12,
            35,
            13,
            36,
            14,
            37,
            15,
            38,
            16,
            39,
            17,
            18,
            19,
            40,
        ]


class TestStatusSnapshot:
    def test_snapshot_reflects_gate_truth(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        snapshot = session.status_snapshot()
        assert snapshot["type"] == "status"
        assert snapshot["health"] == "online"
        assert snapshot["live_lock"] is False
        assert snapshot["executions_blocked"] is False
