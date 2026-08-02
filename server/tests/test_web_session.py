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
from server.llm.types import UserMessage
from server.orchestrator.last_created import LastCreated
from server.orchestrator.tools import CommandOutcome
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.measure import RoundTripRecorder
from server.web.session import ChatSession, outcome_view, summarize_outcomes

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
        assert len(followup_conversation) == 2
        preamble = followup_conversation[0]
        assert isinstance(preamble, UserMessage)
        # AC ②: identity present — Seq 71 / Exec 201, NOT an arbitrary target.
        assert "71" in preamble.text
        assert "201" in preamble.text
        # AC ③: regeneration is preferred over a blind edit.
        assert "regenerat" in preamble.text.lower()
        # the real instruction follows the injected note
        assert followup_conversation[1].text == "더 느리게"

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


class TestStatusSnapshot:
    def test_snapshot_reflects_gate_truth(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        snapshot = session.status_snapshot()
        assert snapshot["type"] == "status"
        assert snapshot["health"] == "online"
        assert snapshot["live_lock"] is False
        assert snapshot["executions_blocked"] is False
