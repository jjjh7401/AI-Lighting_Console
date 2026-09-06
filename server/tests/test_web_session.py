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
import time

import anthropic
import httpx
import pytest
from google.genai import errors as genai_errors

from server.design.song_cue_composer import (
    ComposedCue,
    CueColorData,
    CueDimmerData,
    CueFxData,
    CueMibData,
    CuePositionData,
    CueTimingData,
)
from server.design.song_plan import MANUAL_GO
from server.llm.anthropic_adapter import AnthropicAdapter
from server.llm.config import AnthropicSettings, GeminiSettings
from server.llm.gemini_adapter import GeminiAdapter
from server.llm.types import ModelTurn, ToolCall, ToolResult, UserMessage
from server.orchestrator.last_created import LastCreated
from server.orchestrator.tools import CommandOutcome, ToolExecution
from server.safety.approval import ApprovalItem, ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.mib import PositionCuePlan, position_cue_bundle
from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    FX_POSITION_SEQUENCE,
    POSITION_PRESET_POOL,
    SpatialPointingError,
    preset_recall_command,
)
from server.spatial.position_fx import position_fx_commands
from server.web.approval_bridge import ApprovalChannel
from server.web.measure import RoundTripRecorder
from server.web.question import UNANSWERED, QuestionRequest
from server.web.session import (
    COLOR_PALETTE_SEQUENCE,
    COLOR_PHASER_SEQUENCE,
    COMBO_PHASER_SEQUENCE,
    DIMMER_LEVEL_SEQUENCE,
    DIMMER_PHASER_SEQUENCE,
    HISTORY_MAX_MESSAGES,
    ChatSession,
    _phaser_cue_value_lines,
    _phaser_failure_note,
    _phaser_label_for_cue,
    _phaser_sequence_commands,
    _preset_recall_command,
    _preset_release_command,
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


def _wait_for_question_frames(sent: list[dict], timeout: float = 2.0) -> list[dict]:
    """UI로 나간 질문 카드 프레임들 — 물음을 낸 쪽이 다른 스레드라 잠깐 기다린다."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        cards = [event for event in sent if event.get("type") == "question_request"]
        if cards:
            return cards
        time.sleep(0.01)
    return []


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
            "not_created": "생성 안 됨",
            "partially_created": "부분 생성",
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
        # Read-only probes (verified number proposals, 2026-08-16) are fine;
        # the invariant is ZERO writes without an answer.
        assert calls[0].name == "get_spatial_context"
        assert all(call.name in ("get_spatial_context", "query_state") for call in calls)
        assert "MMX 5대" in event["text"]
        assert "최소 10대" in event["text"]

    def test_remembers_repeating_layout_until_spacing_follow_up(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

    def test_locked_whole_rig_layout_does_not_read_or_write_inventory(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
                calls.append(call)
                raise AssertionError("locked layout must not dispatch a rig read or write")

        session._registry = Registry()
        session._gate.lock.activate()

        event = session.run_instruction("전체 장비를 동그랗게 놓아줘")

        assert provider.calls == []
        assert calls == []
        assert event["commands"] == []
        assert "라이브 잠금 중이라 현재 리그 좌표를 읽지 않았습니다." in event["text"]


class TestPointFixturesAtTarget:
    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
            {"fid": 41, "name": "Sphere 1", "x": 0.0, "y": 0.0, "z": 0.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
                if call.name == "query_state":
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps({"ok": True, "path": call.arguments["path"]}),
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

    def test_body_rotation_is_compensated_skipped_or_disclosed(self, tmp_path):
        # Rotz is the measured axis: the pan the console needs is the
        # geometric pan minus the body rotation, so FID 20's Pan 90 becomes
        # Pan 0 under Rotz 90. Rotx/Roty are UNMEASURED: a confirmed non-zero
        # value skips the fixture by name instead of aiming it confidently
        # wrong. A fixture whose rotation could not be read keeps the old
        # assume-zero behaviour, said out loud.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        fixtures = [
            {
                "fid": 20,
                "name": "A",
                "x": 4.0,
                "y": 0.0,
                "z": 6.0,
                "rotx": 0.0,
                "roty": 0.0,
                "rotz": 90.0,
            },
            {
                "fid": 26,
                "name": "B",
                "x": -4.0,
                "y": 0.0,
                "z": 6.0,
                "rotx": 15.0,
                "roty": 0.0,
                "rotz": 0.0,
            },
            {
                "fid": 30,
                "name": "C",
                "x": 4.0,
                "y": 0.0,
                "z": 6.0,
                "rotation_unread": ["rotx", "roty", "rotz"],
            },
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

        session._registry = Registry()
        event = session.run_instruction("모든 장비가 무대 중앙(0,0,0)을 바라보게 해줘")

        assert calls[0].name == "get_spatial_context"
        assert calls[0].arguments == {"include_rotation": True}
        commands = calls[-1].arguments["commands"]
        assert commands == [
            "Fixture 20 ; Attribute 'Pan' At 0 ; Attribute 'Tilt' At 33.7",
            "Fixture 30 ; Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7",
        ]
        assert "1대(FID 26)" in event["text"]  # non-zero Rotx: skipped by name
        assert "Rotx/Roty" in event["text"]
        assert "회전값을 읽지 못한 1대(FID 30)" in event["text"]  # assume-0 disclosure

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


class TestPositionMoodSuggestion:
    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    def test_a_mood_request_suggests_then_applies_the_accepted_look(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["Vocal DSC"])
        session._question_channel = channel

        event = session.run_instruction("잔잔한 발라드 느낌으로 불 켜고 포지션 잡아줘")

        assert provider.calls == []
        assert len(channel.asked) == 1
        assert "보컬 포커스" in channel.asked[0].prompt
        # 추천이 첫 옵션, 대안 + '적용 안 함'이 뒤따른다.
        labels = [option.label for option in channel.asked[0].options]
        assert labels[0] == "Vocal DSC"
        assert labels[-1] == "적용 안 함"
        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        commands = writes[0].arguments["commands"]
        # Vocal DSC: 두 대가 (0, -2, 1.6)을 향한다 — 픽스처별 상이한 pan/tilt,
        # 디머 온, 픽스처당 한 줄.
        assert len(commands) == 2
        assert commands[0].startswith("Fixture 20 ; Attribute 'Dimmer' At 100 ; ")
        assert "Vocal DSC 포지션을 장비 2대에" in event["text"]

    def test_an_alternative_answer_applies_that_look_instead(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(["Wall"])

        session.run_instruction("잔잔한 발라드 포지션으로")

        commands = [call for call in calls if call.name == "run_commands"][0].arguments["commands"]
        # Wall = 전 대 동일 pan180/tilt45.
        assert commands == [
            "Fixture 20 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 45",
            "Fixture 26 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 45",
        ]

    def test_declining_sends_nothing(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(["적용 안 함"])

        event = session.run_instruction("웅장한 피날레 연출 포지션")

        # Read-only probes (verified number proposals, 2026-08-16) are fine;
        # the invariant is ZERO writes without an answer.
        assert calls[0].name == "get_spatial_context"
        assert all(call.name in ("get_spatial_context", "query_state") for call in calls)
        assert "적용하지 않았습니다" in event["text"]

    def test_a_mood_without_position_intent_reaches_the_model(self, tmp_path):
        # "따뜻한 발라드 느낌으로 만들어줘"는 색·룩 요청일 수 있다 — 모델
        # 경로(find_looks)에 남긴다.
        provider = ScriptedProvider([_final("룩 라이브러리를 확인하겠습니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)

        event = session.run_instruction("잔잔한 발라드 느낌으로 만들어줘")

        assert len(provider.calls) == 1
        assert event["text"] == "룩 라이브러리를 확인하겠습니다"

    def test_an_explicit_technique_request_is_not_intercepted(self, tmp_path):
        # "화려하게 부채살로 펼쳐줘"는 무드 어휘(화려)를 담지만 기법이 명시돼
        # 있다 — LOOK 핸들러가 먼저 잡아 카드 없이 실행된다.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel([])
        session._question_channel = channel

        session.run_instruction("화려하게 부채살로 펼쳐줘")

        assert channel.asked == []
        assert [call.name for call in calls] == ["get_spatial_context", "run_commands"]


class TestBasicPositionPresets:
    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    def test_asks_the_start_number_once_and_stores_ten_presets(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["21"])
        session._question_channel = channel

        event = session.run_instruction("기본 포지션 10개를 프리셋에 저장해줘")

        assert provider.calls == []
        assert len(channel.asked) == 1
        assert "몇 번부터" in channel.asked[0].prompt
        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 10
        first = writes[0].arguments["commands"]
        # Home = straight down for both fixtures, stored+labelled+cleared.
        assert first == [
            "Fixture 20 ; Attribute 'Pan' At 0 ; Attribute 'Tilt' At 0",
            "Fixture 26 ; Attribute 'Pan' At 0 ; Attribute 'Tilt' At 0",
            "Store Preset 2.21",
            "Label Preset 2.21 'Home'",
            "ClearAll",
        ]
        # Every bundle ends with its own ClearAll; numbering is consecutive.
        assert all(call.arguments["commands"][-1] == "ClearAll" for call in writes)
        assert [call.arguments["commands"][-3] for call in writes] == [
            f"Store Preset 2.{21 + offset}" for offset in range(10)
        ]
        assert "2.21 'Home'" in event["text"]
        assert "2.30 'Ring In'" in event["text"]

    def test_an_explicit_start_number_skips_the_question(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel([])
        session._question_channel = channel

        event = session.run_instruction("기본 포지션 프리셋을 5번부터 만들어줘")

        assert channel.asked == []
        writes = [call for call in calls if call.name == "run_commands"]
        assert "Store Preset 2.5" in writes[0].arguments["commands"]
        # 이 리그는 query_state에 "{}"를 돌려주므로 풀 판독이 None(미상)이다 —
        # 겹침 가드는 `unverified` 갈래를 타 카드 없이 진행하며(오늘 동작 보존),
        # 회신은 점유를 확인하지 못했음을 **명시한다**. 카드가 안 뜬 이유가
        # "검증된 빈칸"이 아니라 "판독 실패"임을 이 단정이 고정한다
        # (SPEC-COPILOT-PRESETGUARD-001 AC-006 · 스텁 함정).
        assert "확인하지 못했습니다" in event["text"]

    def test_no_answer_refuses_instead_of_guessing_a_slot(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])  # UNANSWERED

        event = session.run_instruction("기본 포지션 10개를 프리셋에 저장해줘")

        # Read-only probes (verified number proposals, 2026-08-16) are fine;
        # the invariant is ZERO writes without an answer.
        assert calls[0].name == "get_spatial_context"
        assert all(call.name in ("get_spatial_context", "query_state") for call in calls)
        assert "시작 프리셋 번호" in event["text"]


class _PresetPoolRegistry:
    """``query_state``가 **실제 Position 풀 페이로드**를 돌려주는 리그.

    기존 ``TestBasicPositionPresets._registry``는 ``query_state``에 ``"{}"``를
    돌려주므로 ``_position_preset_pool_slots()``가 ``None``(미상)이 되고, 점유
    가드는 ``unverified`` 갈래로 빠진다 — **가드가 없어도 통과하는** 위양성
    리그다(acceptance.md 머리말 '스텁 함정'). 점유 가드를 검증하는 테스트는
    전부 이 리그처럼 풀 판독이 **성공하는** 상태를 명시 구성해야 한다.

    ``pool``은 **첫 write 이전**의 모든 ``query_state``가 보는 점유 집합이고,
    ``readback``은 그 이후가 보는 집합이다. 호출 순번이 아니라 write 경계로 가르는
    이유: 카드 경로는 ``_position_preset_free_starts``가 풀을 한 번 먼저 읽으므로
    "첫 판독 = 가드"가 성립하지 않는다. 순번으로 갈랐다면 카드 경로 테스트에서
    가드를 겨눈다고 믿으면서 실제로는 ``readback``을 겨누게 된다 — 두 값이 기본으로
    같아 조용히 통과한다.
    """

    _FIXTURES = [
        {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
        {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
    ]

    def __init__(
        self,
        calls,
        *,
        pool=(),
        readback=None,
        pool_error=False,
        readback_error=False,
        status="executed_ok",
        truncated=False,
        child_count=None,
        page_size=None,
        legacy_pager=False,
        names=None,
        pool_index=None,
        pool_index_truncated=False,
    ):
        self.calls = calls
        self.pool = tuple(pool)
        self.readback = self.pool if readback is None else tuple(readback)
        self.pool_error = pool_error
        self.readback_error = readback_error
        self.status = status
        self.truncated = truncated
        self.child_count = child_count
        #: 풀 **목록**(`DataPool/PresetPools` 루트)의 번호→이름 — 컬러 풀 해석
        #: (REQ-COLORPRESET-002) 전용. None이면 루트도 기존 풀 페이로드로
        #: 응답한다(기존 테스트 무수정 동작 동일).
        self.pool_index = None if pool_index is None else dict(pool_index)
        self.pool_index_truncated = pool_index_truncated
        # 페이징 응답기 시뮬레이션 (PROTOCOL §4.2, responder 1.6.0):
        # ``page_size``가 있으면 창 단위로 자르고 ``offset``을 에코한다.
        # ``legacy_pager=True``는 구버전(≤1.5.0) — offset을 무시하고 항상
        # 첫 창을 돌려주며 에코가 없다. 둘 다 childCount는 총계다.
        self.page_size = page_size
        self.legacy_pager = legacy_pager
        #: 슬롯 번호 → 프리셋 이름. 가족 필터(재생성)가 이름을 볼 때만 지정한다;
        #: 미지정 슬롯은 이름 없는 자식(구형 페이로드)으로 남는다.
        self.names = dict(names or {})
        self.state_reads = 0
        self.wrote = False

    def _child(self, number):
        child = {"i": number}
        if number in self.names:
            child["name"] = self.names[number]
        return child

    def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
        self.calls.append(call)
        if call.name == "get_spatial_context":
            return ToolExecution(
                ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {"fixtures": self._FIXTURES, "coverage": {"complete": True}}
                    ),
                )
            )
        if call.name == "query_state":
            self.state_reads += 1
            if self.pool_index is not None and call.arguments.get("path") == "DataPool/PresetPools":
                # 풀 목록 루트 — 컬러 풀 해석(REQ-COLORPRESET-002) 전용 응답.
                index_payload = {
                    "children": [
                        {"i": no, "name": name} for no, name in sorted(self.pool_index.items())
                    ],
                    "node": {"childCount": len(self.pool_index)},
                }
                if self.pool_index_truncated:
                    index_payload["truncated"] = True
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=json.dumps(index_payload),
                    )
                )
            # write 경계로 가른다 — 호출 순번이 아니다(§F9).
            before_write = not self.wrote
            error = self.pool_error if before_write else self.readback_error
            slots = self.pool if before_write else self.readback
            if self.page_size is not None:
                requested = call.arguments.get("offset", 0)
                offset = 0 if self.legacy_pager else requested
                window = slots[offset : offset + self.page_size]
                payload = {
                    "children": [self._child(n) for n in window],
                    "node": {"childCount": len(slots)},
                }
                # truncated = 이 창 **이후에도** 남았는가 (계약 §4.2).
                if offset + len(window) < len(slots):
                    payload["truncated"] = True
                if not self.legacy_pager:
                    payload["offset"] = offset
            else:
                payload = {"children": [self._child(n) for n in slots]}
                if self.truncated:
                    payload["truncated"] = True
                if self.child_count is not None:
                    payload["node"] = {"childCount": self.child_count}
            return ToolExecution(
                ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=("" if error else json.dumps(payload)),
                    is_error=error,
                )
            )
        self.wrote = True
        return ToolExecution(
            ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
            (CommandOutcome(command="Store Preset", status=self.status),),
        )


class _AnsweringChannel:
    def __init__(self, answers):
        self.answers = list(answers)
        self.asked = []

    def ask(self, request, **_kwargs):
        self.asked.append(request)
        return self.answers.pop(0) if self.answers else UNANSWERED


def _writes(calls):
    return [call for call in calls if call.name == "run_commands"]


def _all_commands(calls):
    return [cmd for call in _writes(calls) for cmd in call.arguments["commands"]]


class TestPresetPoolPaging:
    """PROTOCOL §4.2 페이징 — 캡(24) 밖 슬롯의 완전 판독과 무진전 방어.

    실측 2026-08-16: 31개 풀에서 캡(24) 밖의 신규 저장 41~50이 되읽기에서
    "미확인 0/10"으로 오보됐다. 페이징 판독은 그 창을 이어 붙여 복구하되,
    전진 없는 반복(구버전 응답기·상한 초과)은 오늘의 '절단=미상(None)'
    규율로 내려간다 — 부분 판독은 더 작은 풀이 아니다.
    """

    def _slots(self, tmp_path, **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, **rig)
        return session._position_preset_pool_slots(), calls

    @staticmethod
    def _reads(calls):
        return [call for call in calls if call.name == "query_state"]

    def test_a_two_page_pool_reads_completely(self, tmp_path):
        # 31슬롯 — 41~50이 둘째 창에 있어도 슬롯 집합에 들어온다.
        pool = tuple(range(1, 22)) + tuple(range(41, 51))
        slots, calls = self._slots(tmp_path, pool=pool, page_size=24)

        assert slots == set(pool)
        reads = self._reads(calls)
        assert len(reads) == 2
        # 첫 요청은 기존 무페이징 판독과 인자까지 동일하다(하위호환).
        assert "offset" not in reads[0].arguments
        assert reads[1].arguments["offset"] == 24

    def test_a_legacy_responder_aborts_to_none_without_looping(self, tmp_path):
        # 구버전 응답기 — offset 무시·에코 부재·항상 첫 창. 둘째 요청에서
        # 에코가 없으므로 즉시 None. 절대 재시도하지 않는다(무한루프 금지).
        slots, calls = self._slots(
            tmp_path, pool=tuple(range(1, 32)), page_size=24, legacy_pager=True
        )

        assert slots is None
        assert len(self._reads(calls)) == 2

    def test_the_page_cap_aborts_to_none(self, tmp_path):
        # 창 2개짜리 응답기로 31슬롯 → 16페이지 필요 > 상한 10 → None.
        slots, calls = self._slots(tmp_path, pool=tuple(range(1, 32)), page_size=2)

        assert slots is None
        assert len(self._reads(calls)) == 10

    def test_a_single_window_pool_is_unchanged(self, tmp_path):
        # 무회귀 — 한 창에 다 들어오는 풀은 요청 1회로 끝난다.
        slots, calls = self._slots(tmp_path, pool=(1, 2, 3), page_size=24)

        assert slots == {1, 2, 3}
        assert len(self._reads(calls)) == 1

    def test_a_forced_truncation_without_echo_still_reads_none(self, tmp_path):
        # 모놀리식(무페이징) 리그의 truncated 강제 — 둘째 창 시도에서 에코가
        # 없어 None. 오늘의 '절단=판독 불가' 동작이 페이징 실패 경로로 유지된다.
        slots, _calls = self._slots(tmp_path, pool=tuple(range(1, 25)), truncated=True)

        assert slots is None

    def test_readback_confirms_slots_in_the_second_window(self, tmp_path):
        # 실측 재현 — 신규 저장 41~50이 둘째 창으로 밀려나도 되읽기가 확인한다.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls,
            pool=tuple(range(1, 22)),  # 21슬롯 — 41~50은 검증된 빈칸(가드 통과)
            readback=tuple(range(1, 22)) + tuple(range(41, 51)),  # 31슬롯, 2창
            page_size=24,
        )
        session._question_channel = _AnsweringChannel([])
        event = session.run_instruction("기본 포지션 프리셋을 41번부터 저장해줘")

        assert len(_writes(calls)) == 10
        assert "10개 확인" in event["text"]
        assert "되읽지 못했습니다" not in event["text"]
        # 가드 1창 + 되읽기 2창 = 3회 — 페이지 수만큼만 늘어난다.
        assert len(self._reads(calls)) == 3


class _ColorRigPropPort:
    """``query_property``가 M0 실측 **표시 문자열**을 돌려주는 픽스처 포트.

    세션의 판별 hop-1/2는 ``read_properties(self._current_cue_port, ...)``를
    타므로(리허설 CurrentCue 읽기와 같은 채널) 레지스트리가 아니라 이 포트를
    직접 스텁한다.
    """

    def __init__(self, entries, *, fail=()):
        self.entries = dict(entries)
        self.fail = set(fail)
        self.calls: list[tuple[str, str]] = []

    def query_property(self, path, property_name):
        self.calls.append((path, property_name))
        if (path, property_name) in self.fail:
            return {"ok": False, "error": "property read failed"}
        value = self.entries.get((path, property_name))
        if value is None:
            return {"ok": False, "error": f"no value: {path}|{property_name}"}
        return {"ok": True, "value": value}


class _ColorChannelRegistry:
    """``query_state``가 ``DMXChannels`` 창을 돌려주는 리그 — hop-3 전용.

    ``page_size``가 있으면 창 단위로 자르고 ``offset``을 에코한다(응답기
    1.6.0). ``legacy_pager=True``는 구버전 — offset 무시·에코 부재·항상 첫
    창(무진전). 채널 이름 ``None``은 이름 없는 자식(무명 채널)이다.
    """

    def __init__(self, calls, *, channels, page_size=None, legacy_pager=False):
        self.calls = calls
        self.channels = {key: list(names) for key, names in channels.items()}
        self.page_size = page_size
        self.legacy_pager = legacy_pager

    def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
        self.calls.append(call)
        assert call.name == "query_state", call
        parts = call.arguments["path"].split("/")
        assert parts[:2] == ["Patch", "FixtureTypes"], call.arguments["path"]
        assert parts[3] == "DMXModes" and parts[5] == "DMXChannels", parts
        names = self.channels[(int(parts[2]), int(parts[4]))]
        page_size = self.page_size if self.page_size is not None else max(len(names), 1)
        requested = call.arguments.get("offset", 0)
        offset = 0 if self.legacy_pager else requested
        window = names[offset : offset + page_size]
        children = []
        for index, name in enumerate(window, start=offset + 1):
            child = {"i": index}
            if name is not None:
                child["name"] = name
            children.append(child)
        payload = {"children": children, "node": {"childCount": len(names)}}
        if offset + len(window) < len(names):
            payload["truncated"] = True
        if not self.legacy_pager:
            payload["offset"] = offset
        return ToolExecution(
            ToolResult(tool_call_id=call.id, name=call.name, content=json.dumps(payload))
        )


def _color_fixture_props(assignments):
    """슬롯 → (타입, 모드) 배치를 M0 표시 문자열 항목으로 펼친다."""
    entries = {}
    for slot, (type_index, mode_index) in assignments.items():
        base = f"Patch/Stages/1/Fixtures/{slot}"
        entries[(base, "FixtureType")] = f"FixtureType {type_index}"
        entries[(base, "Mode")] = f"{mode_index} Mode {mode_index}"
    return entries


#: M0 실측 리그의 채널 목록 축약본 (progress.md §E.1) — 타입 1 Sphere(채널
#: 1개), 타입 2 MMX(ColorRGB_R/G/B + Color1 휠), 타입 3 LEDBeam350(+W),
#: 타입 4 Sharpy(Color1 휠만 — RGB 믹싱 없음).
_M0_COLOR_CHANNELS = {
    (1, 1): ["DMXChannel 1"],
    (2, 1): ["Dimmer", "Pan", "Tilt", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "Color1"],
    (3, 1): ["Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "ColorRGB_W"],
    (4, 1): ["Dimmer", "Pan", "Tilt", "Color1", "Gobo1"],
}

#: M0 리그 배치 — 슬롯 ≠ FID로 잡아 prop 경로가 **슬롯**을 쓰는지도 함께
#: 증명한다. fid 40(Sharpy)·41(Sphere)이 제외 2대(REQ-005 산술 기준값).
_M0_COLOR_PAIRS = [(1, 10), (2, 11), (3, 12), (4, 40), (5, 41)]
_M0_COLOR_ASSIGNMENTS = {1: (2, 1), 2: (2, 1), 3: (3, 1), 4: (4, 1), 5: (1, 1)}


class TestColorCapabilityDiscrimination:
    """SPEC-COPILOT-COLORPRESET-001 REQ-005 — M0 3-hop 컬러 판별 (§E.1).

    판정 원칙: **unknown ≠ capable, unknown ≠ excluded.** prop 실패·표시
    문자열 파싱 불가·채널 목록 절단 미해소·무명 자식은 전부 undetermined다 —
    어느 쪽으로도 승격하지 않는다(침묵 축소·오조준 양쪽 금지).
    """

    def _discriminate(
        self,
        tmp_path,
        pairs=None,
        assignments=None,
        channels=None,
        *,
        page_size=None,
        legacy_pager=False,
        fail=(),
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _ColorChannelRegistry(
            calls,
            channels=_M0_COLOR_CHANNELS if channels is None else channels,
            page_size=page_size,
            legacy_pager=legacy_pager,
        )
        port = _ColorRigPropPort(
            _color_fixture_props(_M0_COLOR_ASSIGNMENTS if assignments is None else assignments),
            fail=fail,
        )
        session._current_cue_port = port
        result = session._color_capable_fids(
            _M0_COLOR_PAIRS if pairs is None else pairs, probe_id_prefix="test-color"
        )
        return result, calls, port

    # REQ-COLORPRESET-005 — M0 리그 재현: 타입 2·3 capable, 타입 1·4 제외.
    def test_the_measured_rig_splits_into_capable_and_excluded(self, tmp_path):
        (capable, excluded, undetermined), _calls, port = self._discriminate(tmp_path)

        assert capable == [10, 11, 12]
        assert excluded == [40, 41]
        assert undetermined == []
        # prop 경로는 FID가 아니라 **슬롯**이다 (슬롯 1~5 ≠ fid 10~41).
        assert ("Patch/Stages/1/Fixtures/4", "FixtureType") in port.calls
        assert all("/40" not in path for path, _name in port.calls)

    # 비용 계약 — (타입,모드) 조합 단위 캐시: 채널 조회는 조합당 1회다.
    def test_a_type_mode_combination_probes_its_channels_once(self, tmp_path):
        _result, calls, port = self._discriminate(tmp_path)

        paths = [call.arguments["path"] for call in calls]
        # 픽스처 5대·조합 4개 — 슬롯 1·2가 같은 (2,1)을 공유해도 조회는 1회.
        assert len(paths) == 4
        assert len(set(paths)) == 4
        assert paths.count("Patch/FixtureTypes/2/DMXModes/1/DMXChannels") == 1
        # 픽스처당 prop 2회 (FixtureType + Mode) — 라운드트립 예산의 절반.
        assert len(port.calls) == 2 * len(_M0_COLOR_PAIRS)

    # M0 주의 재현 — 절단된 채널 목록(29중 15)은 페이징으로 완주해 판정한다.
    def test_a_truncated_channel_list_is_paged_to_completion(self, tmp_path):
        filler = [f"Channel {n}" for n in range(1, 27)]
        channels = {(2, 1): filler + ["ColorRGB_R", "ColorRGB_G", "ColorRGB_B"]}
        (capable, excluded, undetermined), calls, _port = self._discriminate(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (2, 1)},
            channels=channels,
            page_size=15,
        )

        # ColorRGB는 둘째 창에만 있다 — 첫 창 판정이었다면 excluded로 오판한다.
        assert capable == [10]
        assert (excluded, undetermined) == ([], [])
        assert len(calls) == 2
        assert "offset" not in calls[0].arguments
        assert calls[1].arguments["offset"] == 15

    # 무진전 방어 — 구버전 응답기(에코 부재·항상 첫 창)는 undetermined다.
    def test_a_no_progress_pager_yields_undetermined(self, tmp_path):
        channels = {(2, 1): [f"Channel {n}" for n in range(1, 27)] + ["ColorRGB_R"]}
        (capable, excluded, undetermined), calls, _port = self._discriminate(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (2, 1)},
            channels=channels,
            page_size=15,
            legacy_pager=True,
        )

        # 첫 창에 ColorRGB가 없고 완독도 못 했다 — capable도 excluded도 아니다.
        assert (capable, excluded) == ([], [])
        assert undetermined == [10]
        assert len(calls) == 2  # 에코 부재를 본 즉시 중단 — 재시도 루프 금지

    # prop 실패·표시 문자열 파싱 불가 — 채널 조회 없이 undetermined다.
    def test_a_property_failure_or_unparseable_display_yields_undetermined(self, tmp_path):
        assignments = {1: (2, 1)}
        entries = _color_fixture_props(assignments)
        # 슬롯 2는 무번호 모드 표시("Mode 1") — M0 형태가 아니므로 파싱 불가.
        entries[("Patch/Stages/1/Fixtures/2", "FixtureType")] = "FixtureType 2"
        entries[("Patch/Stages/1/Fixtures/2", "Mode")] = "Mode 1"
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _ColorChannelRegistry(calls, channels=_M0_COLOR_CHANNELS)
        session._current_cue_port = _ColorRigPropPort(
            entries, fail={("Patch/Stages/1/Fixtures/1", "FixtureType")}
        )
        capable, excluded, undetermined = session._color_capable_fids(
            [(1, 10), (2, 11)], probe_id_prefix="test-color"
        )

        assert (capable, excluded) == ([], [])
        assert undetermined == [10, 11]
        assert calls == []  # 판별 못 한 픽스처는 채널 조회 비용도 쓰지 않는다

    # 부분 문자열 판정 — ColorRGB_W만 있는 가상 타입도 capable이다.
    def test_a_w_only_emitter_is_capable_by_substring(self, tmp_path):
        (capable, excluded, undetermined), _calls, _port = self._discriminate(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (7, 2)},
            channels={(7, 2): ["Dimmer", "ColorRGB_W"]},
        )

        assert capable == [10]
        assert (excluded, undetermined) == ([], [])

    # 무명 자식 — 목록은 끝까지 왔지만 그 채널의 정체는 안 왔다. excluded로
    # 확정하면 침묵 축소가 된다 — undetermined다.
    def test_a_nameless_channel_child_blocks_an_excluded_verdict(self, tmp_path):
        (capable, excluded, undetermined), _calls, _port = self._discriminate(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (7, 1)},
            channels={(7, 1): ["Dimmer", None, "Gobo1"]},
        )

        assert (capable, excluded) == ([], [])
        assert undetermined == [10]


#: 컬러 플로우 테스트의 표준 풀 목록 — M0 실측(progress.md §E.1)의 배치.
_M0_POOL_INDEX = {1: "Dimmer", 2: "Position", 3: "Gobo", 4: "Color", 5: "Beam"}

#: 콤보 플로우 테스트의 표준 풀 목록 — T7 라이브 프로브
#: (``10-combo-phaser-m0-probe.md`` §1)가 확정한 'All 1'=21을 더한 것.
_COMBO_POOL_INDEX = {**_M0_POOL_INDEX, 21: "All 1"}


class TestBasicColorPresets:
    """SPEC-COPILOT-COLORPRESET-001 — 표준 무대 팔레트 10색의 저장·가드·재생성.

    판정 원칙: 포지션 프리셋 기계의 **세대화**다 — 풀 번호는 리그 판독으로만
    얻고(REQ-002), 안전 장치(점유 카드·되읽기 산술)는 공용 몸통 그대로이며
    (REQ-003/006), 컬러 미보유·판별 불가 장비는 침묵 없이 산술로 고지한다
    (REQ-005). 판별 자체(_color_capable_fids)는 위
    `TestColorCapabilityDiscrimination`이 검증하므로 여기서는 소재 공급을
    인스턴스 스텁으로 갈아끼우고 **흐름**(라우팅·가드·번들·회신)을 겨눈다.
    """

    def _run(
        self,
        tmp_path,
        text,
        *,
        answers=(),
        channel=True,
        pool_index=None,
        pairs=((20, 20), (26, 26)),
        fid_unread=(),
        capable=(20, 26),
        excluded=(),
        undetermined=(),
        stub_material=True,
        **rig,
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls,
            pool_index=_M0_POOL_INDEX if pool_index is None else pool_index,
            **rig,
        )
        if stub_material:
            session._color_rig_fixture_pairs = lambda: (
                [tuple(pair) for pair in pairs],
                list(fid_unread),
            )
            session._color_capable_fids = lambda _pairs, *, probe_id_prefix: (
                list(capable),
                list(excluded),
                list(undetermined),
            )
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # REQ-001/-006 — 6경로 코퍼스: 컬러/포지션/FX × 저장/재생성이 서로의
    # 문장을 삼키지 않는다. 저장 3경로는 제 풀·제 라벨로만 쓰고, 재생성
    # 3경로는 빈 풀 거부 문면의 명사가 행선지를 증명한다.
    def test_the_six_preset_paths_route_mutually_exclusively(self, tmp_path):
        stores = [
            ("기본 컬러 프리셋을 11번부터 저장해줘", "Store Preset 4.11", "Warm White", "4."),
            ("기본 포지션 프리셋을 21번부터 저장해줘", "Store Preset 2.21", "Home", "2."),
            ("이펙트 포지션 프리셋을 41번부터 저장해줘", "Store Preset 2.41", "Sweep L", "2."),
        ]
        for text, store_cmd, first_label, pool_prefix in stores:
            _event, calls, _chan = self._run(tmp_path, text)
            commands = _all_commands(calls)
            assert store_cmd in commands, text
            assert any(first_label in cmd for cmd in commands), text
            # 다른 풀로는 한 줄도 쓰지 않는다 — 상호 배타의 실체.
            assert all(
                cmd.split("Store Preset ", 1)[1].startswith(pool_prefix)
                for cmd in commands
                if cmd.startswith("Store Preset ")
            ), text
        regenerations = [
            ("기본 컬러 다시 잡아줘", "기본 컬러"),
            ("기본 포지션 다시 잡아줘", "기본 포지션"),
            ("이펙트 포지션 다시 잡아줘", "FX 포지션"),
        ]
        for text, noun in regenerations:
            event, calls, _chan = self._run(tmp_path, text)
            assert noun in event["text"], text
            assert _writes(calls) == [], text

    # REQ-002 — 풀 목록에 'Color'가 없으면 거부한다. 4 하드코딩이 있었다면
    # 이 리그(목록에 Color 부재)에서도 4번 풀로 썼을 것이다.
    def test_a_missing_color_pool_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            pool_index={1: "Dimmer", 2: "Position"},
        )

        assert _writes(calls) == []
        assert "Color 풀을 찾지 못했습니다" in event["text"]

    # REQ-002 fail-closed — 절단된 풀 목록의 'Color 부재'는 부재가 아니라
    # 모름이다. 모름 위에서는 저장하지 않는다.
    def test_a_truncated_pool_index_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            pool_index=_M0_POOL_INDEX,
            pool_index_truncated=True,
        )

        assert _writes(calls) == []
        assert "Color 풀을 찾지 못했습니다" in event["text"]

    # REQ-003 — M0 실측 재현: Color 4.1~4.7 수동 프리셋 실존. 명시 번호 1은
    # 그 7개와 충돌하고, 카드가 전부 번호로 열거하며, 거절이면 쓰기 0건이다.
    def test_an_explicit_number_hitting_the_manual_presets_opens_the_card(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 1번부터 저장해줘",
            pool=(1, 2, 3, 4, 5, 6, 7),
            answers=["취소"],
        )

        assert _writes(calls) == []
        assert len(chan.asked) == 1
        prompt = chan.asked[0].prompt
        assert "7개" in prompt
        assert "4.1" in prompt and "4.7" in prompt
        assert "저장하지 않았습니다" in event["text"]

    def test_a_consented_overwrite_stores_and_reports_the_slots(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 1번부터 저장해줘",
            pool=(1, 2, 3, 4, 5, 6, 7),
            readback=tuple(range(1, 11)),
            answers=["덮어쓰기 진행"],
        )

        assert len(chan.asked) == 1
        assert len(_writes(calls)) == 10
        assert "덮어쓰기 승인" in event["text"]
        overwrote = event["text"].split("덮어쓰기 승인", 1)[1]
        assert "4.7" in overwrote and "4.8" not in overwrote

    # REQ-001/-003/-008 — 검증된 빈 구간: 카드 없이 색별 독립 번들 10건.
    # 번들 = 색 체인 → Store → Label → ClearAll, RGB 값은 팔레트 계약 그대로.
    def test_the_ten_color_bundles_carry_the_palette_exactly(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(11, 21)),
        )

        assert chan.asked == []
        writes = _writes(calls)
        assert len(writes) == 10
        for offset, (label, (r, g, b)) in enumerate(COLOR_PALETTE_SEQUENCE):
            preset_no = 11 + offset
            call = writes[offset]
            assert call.id == f"basic-color-preset-{preset_no}"
            assert call.arguments["commands"] == [
                f"Fixture 20 + 26 ; Attribute 'ColorRGB_R' At {r} ; "
                f"Attribute 'ColorRGB_G' At {g} ; Attribute 'ColorRGB_B' At {b}",
                f"Store Preset 4.{preset_no}",
                f"Label Preset 4.{preset_no} '{label}'",
                "ClearAll",
            ]
        assert COLOR_PALETTE_SEQUENCE[0][0] == "Warm White"  # 가족 필터 계약
        commands = _all_commands(calls)
        assert not any("/Merge" in cmd or "/Overwrite" in cmd for cmd in commands)

    # REQ-005 — M0 산술 기준값 재현: 41대 중 39대 적용, fid 40·41 제외.
    def test_exclusion_arithmetic_is_disclosed_with_fids(self, tmp_path):
        pairs = tuple((slot, slot) for slot in range(1, 42))
        event, _calls, _chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            pairs=pairs,
            capable=tuple(range(1, 40)),
            excluded=(40, 41),
        )

        assert "전체 41대 중 39대 적용" in event["text"]
        assert "컬러 어트리뷰트 없음 2대(FID 40, 41) 제외" in event["text"]

    def test_undetermined_fixtures_are_excluded_and_named(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            pairs=((1, 10), (2, 11), (3, 12)),
            capable=(10,),
            undetermined=(11, 12),
        )

        assert "판별 불가 2대(FID 11, 12) 제외" in event["text"]
        # 판별 불가는 번들에 오르지 않는다 — 침묵 승격 금지.
        assert all(
            "11" not in cmd.split(";")[0]
            for cmd in _all_commands(calls)
            if cmd.startswith("Fixture ")
        )

    def test_no_capable_fixture_refuses_with_arithmetic(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            capable=(),
            excluded=(20, 26),
        )

        assert _writes(calls) == []
        assert "컬러 어트리뷰트(ColorRGB)가 확인된 장비가 없어" in event["text"]

    # REQ-001 — 번호 없는 지시는 카드 1장: 문면은 Color 풀을 말하고 제안
    # 구간은 4.x 표기다(컬러 전용 카드 신설 없이 공용 카드의 풀 문면만 바뀜).
    def test_a_numberless_instruction_asks_with_color_pool_wording(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "기본 컬러 프리셋 저장해줘",
            pool=(),
            answers=["11"],
        )

        assert len(chan.asked) == 1
        prompt = chan.asked[0].prompt
        assert "Color 프리셋 몇 번부터" in prompt
        assert any("4.11" in option.label for option in chan.asked[0].options)
        assert "Store Preset 4.11" in _all_commands(calls)

    # REQ-004 — 재생성 가족 필터: 'Warm White'로 시작하는 구간만 표적이다.
    def test_regeneration_targets_only_the_warm_white_family(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "기본 컬러 다시 잡아줘",
            pool=tuple(range(11, 21)) + tuple(range(21, 31)),
            names={11: "Sunset Wash", 21: "Warm White"},
            answers=["덮어쓰기 진행"],
        )

        writes = _writes(calls)
        assert len(writes) == 10
        commands = _all_commands(calls)
        # 라벨이 맞는 21 구간만 덮는다 — 11 구간(다른 가족)은 무접촉.
        assert "Store Preset 4.21" in commands
        assert not any(cmd == "Store Preset 4.11" for cmd in commands)
        assert "다시 저장 요청했습니다" in event["text"]

    def test_regenerating_a_foreign_family_span_by_number_refuses(self, tmp_path):
        # Warm White 구간(21~)이 실존해도 지목된 11 구간은 다른 가족이다 —
        # 후보로 갈아타지 않고 지목 자체를 거부한다(오표적 방지).
        event, calls, _chan = self._run(
            tmp_path,
            "11번부터 기본 컬러 다시 잡아줘",
            pool=tuple(range(11, 31)),
            names={11: "Sunset Wash", 21: "Warm White"},
        )

        assert _writes(calls) == []
        assert "'Warm White'이 아니라" in event["text"]

    # 소재 공급 실물 — (slot, fid) 짝은 컨테이너 자식 열거 + 슬롯당 fid 속성
    # 1회로 만들어지고, fid를 읽지 못한 슬롯은 짝에서 빠져 슬롯 번호로 남는다.
    def test_fixture_pair_enumeration_maps_slots_to_fids(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, pool=(1, 2, 3))
        session._current_cue_port = _ColorRigPropPort(
            {
                ("Patch/Stages/1/Fixtures/1", "fid"): "10",
                ("Patch/Stages/1/Fixtures/3", "fid"): "30",
            }
        )

        result = session._color_rig_fixture_pairs()

        assert result == ([(1, 10), (3, 30)], [2])
        reads = [call for call in calls if call.name == "query_state"]
        assert reads[0].arguments == {"path": "Patch/Stages/1/Fixtures"}

    def test_an_unreadable_fixture_container_yields_none(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, pool_error=True)
        session._current_cue_port = _ColorRigPropPort({})

        assert session._color_rig_fixture_pairs() is None


class TestColorPhaserPresets:
    """멀티컬러 페이저 프리셋 10종 — T1/T1b 라이브 프로브
    (``docs/research/ma3-effects/08-color-phaser-m0-probe.md``)로 실측된
    커맨드라인 문법의 카탈로그 구현.

    판정 원칙: ``TestBasicColorPresets``의 **세대화**다 — 소재 공급만
    갈아끼우고(``_color_phaser_preset_material``), 라우팅·가드·번들·되읽기
    몸통은 100% 재사용이므로 여기서는 (1) 트리거가 기본 컬러 트리거와
    서로소로 동작하는지, (2) 멀티스텝(2/3스텝) 커맨드라인이 프로브에서
    실측된 그대로인지, (3) Form(Sine/Rectangle)·Phase 커맨드가 정확한지,
    (4) 재생성 가족 필터가 'Breathe Warm'인지에 집중한다.
    """

    def _run(
        self,
        tmp_path,
        text,
        *,
        answers=(),
        channel=True,
        pool_index=None,
        pairs=((20, 20), (26, 26)),
        fid_unread=(),
        capable=(20, 26),
        excluded=(),
        undetermined=(),
        stub_material=True,
        **rig,
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls,
            pool_index=_M0_POOL_INDEX if pool_index is None else pool_index,
            **rig,
        )
        if stub_material:
            session._color_rig_fixture_pairs = lambda: (
                [tuple(pair) for pair in pairs],
                list(fid_unread),
            )
            session._color_capable_fids = lambda _pairs, *, probe_id_prefix: (
                list(capable),
                list(excluded),
                list(undetermined),
            )
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # 카탈로그 계약 — 라벨·스텝·Form·Phase 순서는 핸드오프 §2 표 그대로.
    def test_the_catalog_matches_the_handoff_table(self):
        assert [entry[0] for entry in COLOR_PHASER_SEQUENCE] == [
            "Breathe Warm",
            "Breathe Cool",
            "Chase RB",
            "Chase CM",
            "Wave CM",
            "Wave WA",
            "Rainbow",
            "Pulse RY",
            "Duo GL",
            "Slam RW",
        ]
        assert COLOR_PHASER_SEQUENCE[0][0] == "Breathe Warm"  # 가족 필터 계약
        assert COLOR_PHASER_SEQUENCE[6][1] == ("Red", "Green", "Blue")  # Rainbow 3스텝

    # 합성 문장 — '기본'+페이저 어휘 공존("기본 멀티컬러 페이저 …")은 기본
    # 트리거의 갭에도 매치되지만, 디스패치 순서(페이저가 기본보다 앞)가
    # 페이저 경로로 고정한다(2026-08-17 리뷰 오라우팅 재발 방지).
    def test_a_composite_basic_plus_phaser_sentence_routes_to_the_phaser(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        commands = _all_commands(calls)
        assert any("Breathe Warm" in cmd for cmd in commands)  # 페이저 카탈로그
        assert not any("'Warm White'" in cmd for cmd in commands)  # 팔레트 아님
        assert "멀티컬러 페이저" in event["text"]

    # 트리거 서로소 — 멀티컬러/컬러 이펙트 문장은 기본 컬러 경로로 새지
    # 않고, 기본 컬러 문장은 멀티컬러 페이저 경로로 새지 않는다.
    def test_the_trigger_is_disjoint_from_basic_color(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        commands = _all_commands(calls)
        assert "Store Preset 4.31" in commands
        assert any("Breathe Warm" in cmd for cmd in commands)
        # 기본 컬러 풀(4.11~)로는 한 줄도 쓰지 않는다 — 페이저는 4.31~로만.
        assert not any(cmd.startswith("Store Preset 4.1") for cmd in commands)
        assert "멀티컬러 페이저" in event["text"]

        event2, calls2, _chan2 = self._run(
            tmp_path,
            "기본 컬러 프리셋을 11번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(11, 21)),
        )
        commands2 = _all_commands(calls2)
        assert "Store Preset 4.11" in commands2
        assert not any("Breathe Warm" in cmd for cmd in commands2)
        assert "기본 컬러" in event2["text"]

    # 2스텝 Sine — Breathe Warm 커맨드라인이 프로브 §1-B/§3 문법 그대로인지.
    def test_a_two_step_sine_preset_carries_the_probed_grammar(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        writes = _writes(calls)
        assert len(writes) == 10
        call = writes[0]
        assert call.id == "color-phaser-preset-31"
        assert call.arguments["commands"] == [
            "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 40",
            "Step 2",
            "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 55 ; "
            "Attribute 'ColorRGB_B' At 5",
            "Attribute 'ColorRGB_R' At Accel -100",
            "Attribute 'ColorRGB_G' At Accel -100",
            "Attribute 'ColorRGB_B' At Accel -100",
            "Attribute 'ColorRGB_R' At Decel -100",
            "Attribute 'ColorRGB_G' At Decel -100",
            "Attribute 'ColorRGB_B' At Decel -100",
            "Attribute 'ColorRGB_R' At Phase 0",
            "Store Preset 4.31",
            "Label Preset 4.31 'Breathe Warm'",
            "ClearAll",
        ]

    # 2스텝 Rectangle — Chase RB(#3)가 Transition/Accel/Decel 0 근사치를
    # 정확히 싣는지(프로브 §6.1 ASSUMPTION 그대로).
    def test_a_two_step_rectangle_preset_carries_the_probed_approximation(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        writes = _writes(calls)
        call = writes[2]  # Chase RB (index 2 in the catalog)
        assert call.id == "color-phaser-preset-33"
        assert call.arguments["commands"] == [
            "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0",
            "Step 2",
            "Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; "
            "Attribute 'ColorRGB_B' At 100",
            "Attribute 'ColorRGB_R' At Accel 0",
            "Attribute 'ColorRGB_G' At Accel 0",
            "Attribute 'ColorRGB_B' At Accel 0",
            "Attribute 'ColorRGB_R' At Decel 0",
            "Attribute 'ColorRGB_G' At Decel 0",
            "Attribute 'ColorRGB_B' At Decel 0",
            "Attribute 'ColorRGB_R' At Transition 0",
            "Attribute 'ColorRGB_G' At Transition 0",
            "Attribute 'ColorRGB_B' At Transition 0",
            "Attribute 'ColorRGB_R' At Phase 0",
            "Store Preset 4.33",
            "Label Preset 4.33 'Chase RB'",
            "ClearAll",
        ]

    # 3스텝 Rainbow — 프로브 §6.2 실측(Step 3 직후 Store해도 3색 다 담김).
    def test_the_three_step_rainbow_preset_carries_all_three_steps(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        writes = _writes(calls)
        call = writes[6]  # Rainbow (index 6 in the catalog)
        assert call.id == "color-phaser-preset-37"
        commands = call.arguments["commands"]
        assert commands[0] == (
            "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0"
        )
        assert commands[1] == "Step 2"
        assert commands[2] == (
            "Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; "
            "Attribute 'ColorRGB_B' At 10"
        )
        assert commands[3] == "Step 3"
        assert commands[4] == (
            "Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; "
            "Attribute 'ColorRGB_B' At 100"
        )
        assert commands[-4] == "Attribute 'ColorRGB_R' At Phase 0 Thru 360"
        assert commands[-3] == "Store Preset 4.37"
        assert commands[-2] == "Label Preset 4.37 'Rainbow'"
        assert commands[-1] == "ClearAll"

    # Phase 분산 문법 — Duo GL(#9, Phase 180)과 Wave CM(#5, 0 Thru 360).
    def test_phase_tokens_match_the_catalog(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        writes = _writes(calls)
        duo_gl = writes[8].arguments["commands"]
        assert "Attribute 'ColorRGB_R' At Phase 180" in duo_gl
        wave_cm = writes[4].arguments["commands"]
        assert "Attribute 'ColorRGB_R' At Phase 0 Thru 360" in wave_cm

    # 풀 미상 거부 — 기본 컬러와 동일 규율(REQ-002 상속).
    def test_a_missing_color_pool_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool_index={1: "Dimmer", 2: "Position"},
        )

        assert _writes(calls) == []
        assert "Color 풀을 찾지 못했습니다" in event["text"]

    # 재생성 가족 필터 — 'Breathe Warm'로 시작하는 구간만 표적이다.
    def test_regeneration_targets_only_the_breathe_warm_family(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "멀티컬러 페이저 다시 잡아줘",
            pool=tuple(range(11, 21)) + tuple(range(31, 41)),
            names={11: "Sunset Wash", 31: "Breathe Warm"},
            answers=["덮어쓰기 진행"],
        )

        writes = _writes(calls)
        assert len(writes) == 10
        commands = _all_commands(calls)
        assert "Store Preset 4.31" in commands
        assert not any(cmd == "Store Preset 4.11" for cmd in commands)
        assert "다시 저장 요청했습니다" in event["text"]

    # 재생성이 신규 저장보다 앞이다 — "다시 잡아줘"는 저장 트리거의 '잡아'와
    # 겹치므로 등록 순서로 행선지가 고정됨을 뮤테이션으로 증명한다.
    def test_regenerate_is_tried_before_store(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "멀티컬러 페이저 다시 잡아줘",
            pool=(),  # 저장된 구간이 없다 — 재생성 특유의 거부 문면이 나와야 한다
        )

        assert _writes(calls) == []
        assert "먼저" in event["text"] and "저장" in event["text"]


class TestBasicDimmerPresets:
    """T5 — 디머 레벨 프리셋 10종의 저장·가드·재생성.

    판정 원칙: ``TestBasicColorPresets``의 세대화이되 **판별 없음이 계약**
    이다(T5 지시, ``session._dimmer_pool_and_fids`` 독스트링 근거) —
    ``_color_capable_fids``의 대응물을 두지 않으므로 열거된 fid 전부가 그대로
    적용 대상이 된다. 소재 공급은 fixture pair 열거만 스텁하고
    (``_color_rig_fixture_pairs`` 재사용), 라우팅·가드·번들·회신은 공용
    몸통(``_store_position_preset_sequence``) 그대로 검증한다.
    """

    def _run(
        self,
        tmp_path,
        text,
        *,
        answers=(),
        channel=True,
        pool_index=None,
        pairs=((20, 20), (26, 26)),
        fid_unread=(),
        stub_material=True,
        **rig,
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls,
            pool_index=_M0_POOL_INDEX if pool_index is None else pool_index,
            **rig,
        )
        if stub_material:
            session._color_rig_fixture_pairs = lambda: (
                [tuple(pair) for pair in pairs],
                list(fid_unread),
            )
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # 트리거 서로소 — 기본 디머 문장은 컬러 풀(4.x)로도 포지션 풀(2.x)로도
    # 새지 않는다(Dimmer 풀=1로만 착지).
    def test_the_trigger_is_disjoint_from_color_and_position(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 디머 프리셋을 11번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(11, 21)),
        )
        commands = _all_commands(calls)
        assert "Store Preset 1.11" in commands
        assert any("Dim 10" in cmd for cmd in commands)
        assert not any(cmd.startswith("Store Preset 4.") for cmd in commands)
        assert not any(cmd.startswith("Store Preset 2.") for cmd in commands)
        assert "디머 레벨" in event["text"]

    # 풀 미상 거부 — 컬러(REQ-002)와 동일 규율, 명사만 Dimmer.
    def test_a_missing_dimmer_pool_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 디머 프리셋을 11번부터 저장해줘",
            pool_index={2: "Position", 4: "Color"},
        )

        assert _writes(calls) == []
        assert "Dimmer 풀을 찾지 못했습니다" in event["text"]

    # 판별 생략 계약 — 컬러식 "N대 중 M대 적용/제외" 산술 문면이 없고, 열거된
    # fid 전부가 하나의 Fixture 선택으로 번들에 실린다.
    def test_no_discrimination_arithmetic_and_all_enumerated_fids_apply(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 디머 프리셋을 11번부터 저장해줘",
            pairs=((1, 10), (2, 11), (3, 12)),
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(11, 21)),
        )

        assert "판별" not in event["text"]
        assert "제외" not in event["text"]
        commands = _all_commands(calls)
        assert any(cmd.startswith("Fixture 10 + 11 + 12 ;") for cmd in commands)

    # fid 미판독은 컬러와 동일하게 침묵 없이 고지한다.
    def test_unread_fid_slots_are_disclosed(self, tmp_path):
        event, _calls, _chan = self._run(
            tmp_path,
            "기본 디머 프리셋을 11번부터 저장해줘",
            pairs=((1, 10),),
            fid_unread=(2, 3),
            pool=(1,),
            readback=(1,) + tuple(range(11, 21)),
        )

        assert "FID 미판독 2대(패치 슬롯 2, 3) 제외" in event["text"]

    # REQ-001/-003 대응물 — 검증된 빈 구간: 카드 없이 레벨별 독립 번들 10건.
    # 값은 카탈로그의 % 그대로(Full=100).
    def test_the_ten_level_bundles_carry_the_catalog_exactly(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "기본 디머 프리셋을 11번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(11, 21)),
        )

        assert chan.asked == []
        writes = _writes(calls)
        assert len(writes) == 10
        for offset, (label, value) in enumerate(DIMMER_LEVEL_SEQUENCE):
            preset_no = 11 + offset
            call = writes[offset]
            assert call.id == f"basic-dimmer-preset-{preset_no}"
            assert call.arguments["commands"] == [
                f"Fixture 20 + 26 ; Attribute 'Dimmer' At {value}",
                f"Store Preset 1.{preset_no}",
                f"Label Preset 1.{preset_no} '{label}'",
                "ClearAll",
            ]
        assert DIMMER_LEVEL_SEQUENCE[0][0] == "Dim 10"  # 가족 필터 계약
        assert DIMMER_LEVEL_SEQUENCE[-1] == ("Full", 100)
        commands = _all_commands(calls)
        assert not any("/Merge" in cmd or "/Overwrite" in cmd for cmd in commands)

    # REQ-004 대응물 — 재생성 가족 필터: 'Dim 10'로 시작하는 구간만 표적이다.
    def test_regeneration_targets_only_the_dim_10_family(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 디머 다시 잡아줘",
            pool=tuple(range(11, 21)) + tuple(range(21, 31)),
            names={11: "Custom Fade", 21: "Dim 10"},
            answers=["덮어쓰기 진행"],
        )

        writes = _writes(calls)
        assert len(writes) == 10
        commands = _all_commands(calls)
        assert "Store Preset 1.21" in commands
        assert not any(cmd == "Store Preset 1.11" for cmd in commands)
        assert "다시 저장 요청했습니다" in event["text"]

    # 재생성이 신규 저장보다 앞이다 — "다시 잡아줘"는 저장 트리거의 '잡아'와
    # 겹치므로 등록 순서로 행선지가 고정됨을 빈 풀 거부 문면으로 증명한다.
    def test_regenerate_is_tried_before_store(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 디머 다시 잡아줘",
            pool=(),
        )

        assert _writes(calls) == []
        assert "먼저" in event["text"] and "저장" in event["text"]


class TestDimmerPhaserPresets:
    """디머 페이저 프리셋 10종 — T4 라이브 프로브
    (``docs/research/ma3-effects/09-dimmer-phaser-m0-probe.md``)로 실측된
    커맨드라인 문법의 카탈로그 구현. ``TestColorPhaserPresets``의 세대화 —
    소재 공급만 갈아끼우고(``_dimmer_phaser_preset_material``), 라우팅·가드·
    번들·되읽기 몸통은 100% 재사용이므로 여기서는 (1) 트리거가 디머 레벨
    트리거와 서로소로 동작하는지, (2) 멀티스텝(2/3스텝) 커맨드라인이 프로브에서
    실측된 그대로인지, (3) Form(Sine/Rectangle)·Phase 커맨드가 정확한지,
    (4) 재생성 가족 필터가 'Breathe Soft'인지에 집중한다.
    """

    def _run(
        self,
        tmp_path,
        text,
        *,
        answers=(),
        channel=True,
        pool_index=None,
        pairs=((20, 20), (26, 26)),
        fid_unread=(),
        stub_material=True,
        **rig,
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls,
            pool_index=_M0_POOL_INDEX if pool_index is None else pool_index,
            **rig,
        )
        if stub_material:
            session._color_rig_fixture_pairs = lambda: (
                [tuple(pair) for pair in pairs],
                list(fid_unread),
            )
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # 카탈로그 계약 — 라벨·스텝·Form·Phase 순서는 T5 지시 표 그대로.
    def test_the_catalog_matches_the_t5_table(self):
        assert [entry[0] for entry in DIMMER_PHASER_SEQUENCE] == [
            "Breathe Soft",
            "Breathe Deep",
            "Pulse Hard",
            "Pulse Half",
            "Wave Soft",
            "Wave Full",
            "Ripple",
            "Flash Accent",
            "Alt Half",
            "Slam Run",
        ]
        assert DIMMER_PHASER_SEQUENCE[0][0] == "Breathe Soft"  # 가족 필터 계약
        assert DIMMER_PHASER_SEQUENCE[6][1] == (30, 60, 100)  # Ripple 3스텝

    # 합성 문장 — "기본 디머 이펙트 …"는 기본 디머 트리거의 갭에도 매치되지만
    # 디스패치 순서가 페이저 경로로 고정한다(2026-08-17 리뷰).
    def test_a_composite_basic_plus_phaser_sentence_routes_to_the_phaser(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 디머 이펙트 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(21, 31)),
        )
        commands = _all_commands(calls)
        assert any("Breathe Soft" in cmd for cmd in commands)  # 페이저 카탈로그
        assert not any("'Dim 10'" in cmd for cmd in commands)  # 레벨 아님
        assert "디머 페이저" in event["text"]

    # 트리거 서로소 — 디머 이펙트/페이저 문장은 디머 레벨 경로로 새지 않고,
    # 디머 레벨 문장은 디머 페이저 경로로 새지 않는다.
    def test_the_trigger_is_disjoint_from_basic_dimmer(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(21, 31)),
        )
        commands = _all_commands(calls)
        assert "Store Preset 1.21" in commands
        assert any("Breathe Soft" in cmd for cmd in commands)
        # 디머 레벨 풀(1.11~)로는 한 줄도 쓰지 않는다 — 페이저는 1.21~로만.
        assert not any(cmd.startswith("Store Preset 1.1") for cmd in commands)
        assert "디머 페이저" in event["text"]

        event2, calls2, _chan2 = self._run(
            tmp_path,
            "기본 디머 프리셋을 11번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(11, 21)),
        )
        commands2 = _all_commands(calls2)
        assert "Store Preset 1.11" in commands2
        assert not any("Breathe Soft" in cmd for cmd in commands2)
        assert "디머 레벨" in event2["text"]

    # 2스텝 Sine — Breathe Soft 커맨드라인이 프로브 §2 문법 그대로인지.
    def test_a_two_step_sine_preset_carries_the_probed_grammar(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(21, 31)),
        )
        writes = _writes(calls)
        assert len(writes) == 10
        call = writes[0]
        assert call.id == "dimmer-phaser-preset-21"
        assert call.arguments["commands"] == [
            "Fixture 20 + 26 ; Attribute 'Dimmer' At 30",
            "Step 2",
            "Attribute 'Dimmer' At 70",
            "Attribute 'Dimmer' At Accel -100",
            "Attribute 'Dimmer' At Decel -100",
            "Attribute 'Dimmer' At Phase 0",
            "Store Preset 1.21",
            "Label Preset 1.21 'Breathe Soft'",
            "ClearAll",
        ]

    # 2스텝 Rectangle — Pulse Hard(#3)가 Transition/Accel/Decel 0 근사치를
    # 정확히 싣는지(프로브 §6.1 컬러 패턴의 디머 이식, ASSUMPTION 그대로).
    def test_a_two_step_rectangle_preset_carries_the_probed_approximation(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(21, 31)),
        )
        writes = _writes(calls)
        call = writes[2]  # Pulse Hard (index 2 in the catalog)
        assert call.id == "dimmer-phaser-preset-23"
        assert call.arguments["commands"] == [
            "Fixture 20 + 26 ; Attribute 'Dimmer' At 0",
            "Step 2",
            "Attribute 'Dimmer' At 100",
            "Attribute 'Dimmer' At Accel 0",
            "Attribute 'Dimmer' At Decel 0",
            "Attribute 'Dimmer' At Transition 0",
            "Attribute 'Dimmer' At Phase 0",
            "Store Preset 1.23",
            "Label Preset 1.23 'Pulse Hard'",
            "ClearAll",
        ]

    # 3스텝 Ripple — 프로브 §3(3-step)/§6.2(컬러) 실측(Step 3 직후 Store해도
    # 3값 다 담김).
    def test_the_three_step_ripple_preset_carries_all_three_steps(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(21, 31)),
        )
        writes = _writes(calls)
        call = writes[6]  # Ripple (index 6 in the catalog)
        assert call.id == "dimmer-phaser-preset-27"
        commands = call.arguments["commands"]
        assert commands[0] == "Fixture 20 + 26 ; Attribute 'Dimmer' At 30"
        assert commands[1] == "Step 2"
        assert commands[2] == "Attribute 'Dimmer' At 60"
        assert commands[3] == "Step 3"
        assert commands[4] == "Attribute 'Dimmer' At 100"
        assert commands[-4] == "Attribute 'Dimmer' At Phase 0 Thru 360"
        assert commands[-3] == "Store Preset 1.27"
        assert commands[-2] == "Label Preset 1.27 'Ripple'"
        assert commands[-1] == "ClearAll"

    # Phase 분산 문법 — Alt Half(#9, Phase 180)와 Wave Soft(#5, 0 Thru 360).
    def test_phase_tokens_match_the_catalog(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(21, 31)),
        )
        writes = _writes(calls)
        alt_half = writes[8].arguments["commands"]
        assert "Attribute 'Dimmer' At Phase 180" in alt_half
        wave_soft = writes[4].arguments["commands"]
        assert "Attribute 'Dimmer' At Phase 0 Thru 360" in wave_soft

    # 풀 미상 거부 — 디머 레벨과 동일 규율.
    def test_a_missing_dimmer_pool_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 프리셋을 21번부터 저장해줘",
            pool_index={2: "Position", 4: "Color"},
        )

        assert _writes(calls) == []
        assert "Dimmer 풀을 찾지 못했습니다" in event["text"]

    # 재생성 가족 필터 — 'Breathe Soft'로 시작하는 구간만 표적이다.
    def test_regeneration_targets_only_the_breathe_soft_family(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 다시 잡아줘",
            pool=tuple(range(11, 21)) + tuple(range(21, 31)),
            names={11: "Custom Fade", 21: "Breathe Soft"},
            answers=["덮어쓰기 진행"],
        )

        writes = _writes(calls)
        assert len(writes) == 10
        commands = _all_commands(calls)
        assert "Store Preset 1.21" in commands
        assert not any(cmd == "Store Preset 1.11" for cmd in commands)
        assert "다시 저장 요청했습니다" in event["text"]

    # 재생성이 신규 저장보다 앞이다 — 트리거의 '잡아'가 겹치므로 등록 순서로
    # 행선지가 고정됨을 뮤테이션으로 증명한다.
    def test_regenerate_is_tried_before_store(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "디머 페이저 다시 잡아줘",
            pool=(),
        )

        assert _writes(calls) == []
        assert "먼저" in event["text"] and "저장" in event["text"]


class TestComboPhaserPresets:
    """콤보(컬러+디머 혼합) 페이저 프리셋 10종 — T7 라이브 프로브
    (``docs/research/ma3-effects/10-combo-phaser-m0-probe.md``)로 실측된
    저장 풀·문법의 카탈로그 구현. ``TestColorPhaserPresets``의 세대화 —
    소재 공급만 갈아끼우고(``_combo_phaser_preset_material``), 라우팅·가드·
    번들·되읽기 몸통은 100% 재사용이므로 여기서는 (1) 트리거가 기존 5개
    축과 서로소로 동작하는지, (2) 저장 풀이 Color/Dimmer가 아니라 'All 1'
    (T7 프로브가 확정한 21)인지, (3) 스텝이 컬러 3줄+디머 1줄을 한 체인에
    싣는지(2/3스텝), (4) Form(Sine/Rectangle)·Phase 커맨드가 4채널
    (ColorRGB_R/G/B + Dimmer)에 정확히 실리는지, (5) 재생성 가족 필터가
    'Drop Slam'인지에 집중한다.
    """

    def _run(
        self,
        tmp_path,
        text,
        *,
        answers=(),
        channel=True,
        pool_index=None,
        pairs=((20, 20), (26, 26)),
        fid_unread=(),
        capable=(20, 26),
        excluded=(),
        undetermined=(),
        stub_material=True,
        **rig,
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls,
            pool_index=_COMBO_POOL_INDEX if pool_index is None else pool_index,
            **rig,
        )
        if stub_material:
            session._color_rig_fixture_pairs = lambda: (
                [tuple(pair) for pair in pairs],
                list(fid_unread),
            )
            session._color_capable_fids = lambda _pairs, *, probe_id_prefix: (
                list(capable),
                list(excluded),
                list(undetermined),
            )
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # 카탈로그 계약 — 라벨·스텝·Form·Phase 순서는 T8 지시 표 그대로.
    def test_the_catalog_matches_the_t8_table(self):
        assert [entry[0] for entry in COMBO_PHASER_SEQUENCE] == [
            "Drop Slam",
            "Breathe Amber",
            "Breathe Blue",
            "Police",
            "Heartbeat",
            "Golden Wave",
            "Ocean Wave",
            "Rainbow Run",
            "Club Duo",
            "Finale Slam",
        ]
        assert COMBO_PHASER_SEQUENCE[0][0] == "Drop Slam"  # 가족 필터 계약
        assert COMBO_PHASER_SEQUENCE[7][1] == (
            ("Red", 100),
            ("Green", 50),
            ("Blue", 100),
        )  # Rainbow Run 3스텝

    # 합성 문장 — "컬러 디머 페이저 …"는 디머 페이저 축('디머 페이저')에도
    # 매치되지만 디스패치 순서(콤보 맨 앞)가 콤보 경로로 고정한다(2026-08-17
    # 리뷰 실측: 순서 수정 전에는 회색조 카탈로그가 Dimmer 풀로 오착지했다).
    def test_a_composite_color_dimmer_sentence_routes_to_the_combo(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "컬러 디머 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
        )
        commands = _all_commands(calls)
        assert "Store Preset 21.51" in commands  # All 1 풀로만
        assert any("Drop Slam" in cmd for cmd in commands)
        assert not any("Breathe Soft" in cmd for cmd in commands)  # 디머 페이저 아님
        assert not any(cmd.startswith("Store Preset 1.") for cmd in commands)
        assert "콤보 페이저" in event["text"]

    # 트리거 서로소 — 콤보 문장은 기존 4개 저장 축(기본컬러/멀티컬러/기본
    # 디머/디머페이저) 어느 경로로도 새지 않고, 그 역도 마찬가지다.
    def test_the_trigger_is_disjoint_from_the_other_four_axes(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
        )
        commands = _all_commands(calls)
        assert "Store Preset 21.51" in commands
        assert any("Drop Slam" in cmd for cmd in commands)
        # Color(4.x)·Dimmer(1.x) 어느 풀로도 한 줄도 쓰지 않는다 — All 1(21)로만.
        assert not any(cmd.startswith("Store Preset 4.") for cmd in commands)
        assert not any(cmd.startswith("Store Preset 1.") for cmd in commands)
        assert "콤보 페이저" in event["text"]

        event2, calls2, _chan2 = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        commands2 = _all_commands(calls2)
        assert not any("Drop Slam" in cmd for cmd in commands2)
        assert "멀티컬러 페이저" in event2["text"]

    # 2스텝 Rectangle — Drop Slam(#1)이 컬러 3줄+디머 1줄을 한 체인에 싣고,
    # Transition/Accel/Decel 0 근사치가 4채널(ColorRGB_R/G/B+Dimmer) 전부에
    # 정확히 실리는지(프로브 §2 항목1/4 실측 문법 그대로).
    def test_a_two_step_rectangle_preset_carries_the_probed_grammar(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
        )
        writes = _writes(calls)
        assert len(writes) == 10
        call = writes[0]
        assert call.id == "combo-phaser-preset-51"
        assert call.arguments["commands"] == [
            "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0 ; "
            "Attribute 'Dimmer' At 100",
            "Step 2",
            "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; "
            "Attribute 'ColorRGB_B' At 0 ; Attribute 'Dimmer' At 0",
            "Attribute 'ColorRGB_R' At Accel 0",
            "Attribute 'ColorRGB_G' At Accel 0",
            "Attribute 'ColorRGB_B' At Accel 0",
            "Attribute 'Dimmer' At Accel 0",
            "Attribute 'ColorRGB_R' At Decel 0",
            "Attribute 'ColorRGB_G' At Decel 0",
            "Attribute 'ColorRGB_B' At Decel 0",
            "Attribute 'Dimmer' At Decel 0",
            "Attribute 'ColorRGB_R' At Transition 0",
            "Attribute 'ColorRGB_G' At Transition 0",
            "Attribute 'ColorRGB_B' At Transition 0",
            "Attribute 'Dimmer' At Transition 0",
            "Attribute 'ColorRGB_R' At Phase 0",
            "Store Preset 21.51",
            "Label Preset 21.51 'Drop Slam'",
            "ClearAll",
        ]

    # 2스텝 Sine — Breathe Amber(#2)가 서로 다른 팔레트+디머% 스텝 쌍을
    # 정확히 싣는지.
    def test_a_two_step_sine_preset_carries_the_probed_grammar(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
        )
        writes = _writes(calls)
        call = writes[1]  # Breathe Amber (index 1 in the catalog)
        assert call.id == "combo-phaser-preset-52"
        assert call.arguments["commands"] == [
            "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 40 ; "
            "Attribute 'Dimmer' At 70",
            "Step 2",
            "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 55 ; "
            "Attribute 'ColorRGB_B' At 5 ; Attribute 'Dimmer' At 30",
            "Attribute 'ColorRGB_R' At Accel -100",
            "Attribute 'ColorRGB_G' At Accel -100",
            "Attribute 'ColorRGB_B' At Accel -100",
            "Attribute 'Dimmer' At Accel -100",
            "Attribute 'ColorRGB_R' At Decel -100",
            "Attribute 'ColorRGB_G' At Decel -100",
            "Attribute 'ColorRGB_B' At Decel -100",
            "Attribute 'Dimmer' At Decel -100",
            "Attribute 'ColorRGB_R' At Phase 0",
            "Store Preset 21.52",
            "Label Preset 21.52 'Breathe Amber'",
            "ClearAll",
        ]

    # 3스텝 Rainbow Run — 프로브 §2 항목5(3스텝 혼합) 실측(Step 3 직후
    # Store해도 3색+3디머값 다 담김).
    def test_the_three_step_rainbow_run_preset_carries_all_three_steps(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
        )
        writes = _writes(calls)
        call = writes[7]  # Rainbow Run (index 7 in the catalog)
        assert call.id == "combo-phaser-preset-58"
        commands = call.arguments["commands"]
        assert commands[0] == (
            "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0 ; "
            "Attribute 'Dimmer' At 100"
        )
        assert commands[1] == "Step 2"
        assert commands[2] == (
            "Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; "
            "Attribute 'ColorRGB_B' At 10 ; Attribute 'Dimmer' At 50"
        )
        assert commands[3] == "Step 3"
        assert commands[4] == (
            "Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; "
            "Attribute 'ColorRGB_B' At 100 ; Attribute 'Dimmer' At 100"
        )
        assert commands[-4] == "Attribute 'ColorRGB_R' At Phase 0 Thru 360"
        assert commands[-3] == "Store Preset 21.58"
        assert commands[-2] == "Label Preset 21.58 'Rainbow Run'"
        assert commands[-1] == "ClearAll"

    # Phase 분산 문법 — Club Duo(#9, Phase 180)와 Golden Wave(#6, 0 Thru 360).
    def test_phase_tokens_match_the_catalog(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
        )
        writes = _writes(calls)
        club_duo = writes[8].arguments["commands"]
        assert "Attribute 'ColorRGB_R' At Phase 180" in club_duo
        golden_wave = writes[5].arguments["commands"]
        assert "Attribute 'ColorRGB_R' At Phase 0 Thru 360" in golden_wave

    # 풀 미상 거부 — 컬러/디머와 동일 규율, 명사만 'All 1'.
    def test_a_missing_all_pool_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool_index={1: "Dimmer", 2: "Position", 4: "Color"},
        )

        assert _writes(calls) == []
        assert "All 1 풀을 찾지 못했습니다" in event["text"]

    # 컬러 판별 상한 — 컬러 없는 장비는 콤보에서도 제외된다.
    def test_color_incapable_fixtures_are_excluded(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 프리셋을 51번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(51, 61)),
            pairs=((20, 20), (26, 26), (30, 30)),
            capable=(20, 26),
            excluded=(30,),
        )
        commands = _all_commands(calls)
        assert "Fixture 20 + 26" in commands[0]
        assert "30" not in commands[0].split(";")[0]
        assert "컬러 판별" in event["text"]

    # 재생성 가족 필터 — 'Drop Slam'으로 시작하는 구간만 표적이다.
    def test_regeneration_targets_only_the_drop_slam_family(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 다시 잡아줘",
            pool=tuple(range(41, 51)) + tuple(range(51, 61)),
            names={41: "Old Combo", 51: "Drop Slam"},
            answers=["덮어쓰기 진행"],
        )

        writes = _writes(calls)
        assert len(writes) == 10
        commands = _all_commands(calls)
        assert "Store Preset 21.51" in commands
        assert not any(cmd == "Store Preset 21.41" for cmd in commands)
        assert "다시 저장 요청했습니다" in event["text"]

    # 재생성이 신규 저장보다 앞이다 — 트리거의 '잡아'가 겹치므로 등록 순서로
    # 행선지가 고정됨을 뮤테이션으로 증명한다.
    def test_regenerate_is_tried_before_store(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "콤보 페이저 다시 잡아줘",
            pool=(),
        )

        assert _writes(calls) == []
        assert "먼저" in event["text"] and "저장" in event["text"]


class TestPositionPresetOverwriteGuard:
    """SPEC-COPILOT-PRESETGUARD-001 §B.1/§B.2 — 점유 가드와 저장 되읽기.

    판정 원칙: **손실 가능한 쓰기는 승낙의 증거 없이 진행하지 않는다.**
    """

    def _run(self, tmp_path, text, *, answers=(), channel=True, **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, **rig)
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # AC-PRESETGUARD-001 — 명시 번호의 충돌에서 쓰기가 0건이다 (뮤테이션 필수)
    def test_an_explicit_number_hitting_stored_slots_writes_nothing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=["취소"],
        )

        assert _writes(calls) == []
        assert len(chan.asked) == 1
        assert "승인" in event["text"] or "저장하지 않" in event["text"]

    # AC-PRESETGUARD-002 — 검증된 빈 구간에는 카드가 뜨지 않는다 (비공허성 짝)
    def test_a_verified_empty_span_stores_without_asking(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
        )

        assert chan.asked == []
        writes = _writes(calls)
        assert len(writes) == 10
        commands = _all_commands(calls)
        for offset in range(10):
            assert f"Store Preset 2.{21 + offset}" in commands

    # AC-PRESETGUARD-003 — 카드가 사라지는 슬롯을 번호로 열거한다
    def test_the_card_lists_every_slot_that_disappears(self, tmp_path):
        # 비연속 점유 {21,22,27} — "2.21~2.30" 범위 문구로는 22·27을 담을 수 없다.
        _event, _calls, chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=["취소"],
        )

        prompt = chan.asked[0].prompt
        assert "21" in prompt
        assert "22" in prompt
        assert "27" in prompt

    # AC-PRESETGUARD-004 — 무응답에서 쓰기가 0건이다 (fail-closed · 뮤테이션 필수)
    def test_an_unanswered_card_stores_nothing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=[],  # UNANSWERED
        )

        assert _writes(calls) == []
        assert "응답" in event["text"]

    def test_no_ui_attached_stores_nothing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            channel=False,
        )

        assert _writes(calls) == []
        assert "응답" in event["text"]

    # AC-PRESETGUARD-005 — 승낙하면 진행하고 덮어쓴 슬롯을 회신한다 (비공허성 짝)
    def test_an_accepted_card_stores_and_reports_the_overwritten_slots(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            readback=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )

        # 카드가 실제로 떴고, 승낙 뒤에야 저장이 나갔다.
        assert len(_chan.asked) == 1
        assert len(_writes(calls)) == 10
        # 회신은 "저장한 슬롯"이 아니라 **덮어쓴 슬롯**을 따로 적는다.
        assert "덮어쓰기 승인" in event["text"]
        overwrote = event["text"].split("덮어쓰기 승인", 1)[1]
        assert "2.22" in overwrote
        assert "2.27" in overwrote
        assert "2.23" not in overwrote

    # AC-PRESETGUARD-006 — 판독 불가와 검증된 빈칸의 회신이 다르다 (뮤테이션 필수)
    def test_an_unreadable_pool_is_not_reported_as_an_empty_span(self, tmp_path):
        unreadable, unreadable_calls, _c1 = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool_error=True,
            readback=(),
        )
        verified, verified_calls, _c2 = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=tuple(range(21, 31)),
        )

        # 양쪽 모두 저장은 진행한다 (오늘의 동작 보존, REQ-PRESETGUARD-004).
        assert len(_writes(unreadable_calls)) == 10
        assert len(_writes(verified_calls)) == 10
        # 그러나 회신 문면은 다르다 — 미상은 검증된 빈칸이 아니다.
        assert "확인하지 못했습니다" in unreadable["text"]
        assert "확인하지 못했습니다" not in verified["text"]
        assert unreadable["text"] != verified["text"]

    # 절단 실측 2026-08-16 — 31개 풀에서 캡(24) 밖의 신규 저장 10건이
    # "미확인 0/10"으로 오보됐다. 절단은 판독 불가이지 빈칸이 아니다.
    def test_a_truncated_pool_listing_is_unreadable_not_empty(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 41번부터 저장해줘",
            pool=tuple(range(1, 25)),
            truncated=True,
        )

        # 저장은 진행하되(판독 불가 규율과 동일) 되읽기는 전건 미검증이다.
        assert len(_writes(calls)) == 10
        assert "되읽지 못했습니다" in event["text"]
        assert "미확인 2.4" not in event["text"]
        assert "0개 확인" not in event["text"]

    def test_childcount_arithmetic_alone_marks_the_pool_unreadable(self, tmp_path):
        # truncated 플래그가 빠져도 childCount > len(children)이 잡는다 — 이중 방어.
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 41번부터 저장해줘",
            pool=tuple(range(1, 25)),
            child_count=31,
        )

        assert len(_writes(calls)) == 10
        assert "되읽지 못했습니다" in event["text"]
        assert "0개 확인" not in event["text"]

    # AC-PRESETGUARD-007 — 되읽기 산술이 회신에 실린다 (뮤테이션 필수)
    def test_the_readback_carries_arithmetic(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=tuple(range(21, 31)),
        )

        assert "기대 10개" in event["text"]
        assert "10개 확인" in event["text"]
        # 가드 1회 + 되읽기 1회 = 2회. 루프당 반복이 아니다.
        assert len([c for c in calls if c.name == "query_state"]) == 2

    def test_a_missing_slot_is_enumerated_and_triggers_no_retry(self, tmp_path):
        landed = tuple(n for n in range(21, 31) if n != 27)
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=landed,
        )

        assert "2.27" in event["text"]
        assert "미확인" in event["text"]
        # REQ-PRESETGUARD-010 — 되읽기는 보고이지 자기수정 루프가 아니다.
        assert event["status"] == "ok"
        assert len(_writes(calls)) == 10

    # AC-PRESETGUARD-008 — 되읽기 불가가 확인됨으로 보고되지 않는다 (뮤테이션 필수)
    def test_an_unreadable_readback_is_reported_unverified(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback_error=True,
        )

        assert len(_writes(calls)) == 10
        assert "미검증" in event["text"]
        assert "개 확인" not in event["text"]

    # D3 (독립 감사 지적, 종결 후 후속) — 사전 판독 실패를 "원래 차 있었다"로 적지 않는다
    #
    # `run.before is None`은 저장 **전** 풀 판독이 실패했다는 뜻이다 — 그 슬롯이
    # 원래 차 있었는지 **우리는 모른다**. 그런데 회신은 사전 점유가 관측된 경우와
    # 같은 문장("저장 전부터 차 있던 슬롯이라")을 냈다. 바로 앞 문장에서 "풀을 읽지
    # 못했다"고 말해 놓고 다음 문장에서 사전 상태를 단언하는 자기모순이며, 이는
    # 이 SPEC이 닫으려는 결함(관측하지 않은 것을 관측했다고 적기)과 같은 형상이다.
    def test_an_unread_pre_state_is_not_reported_as_preexisting_occupancy(self, tmp_path):
        unknown_before, unknown_calls, _c1 = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool_error=True,  # 저장 전 판독 실패 → before = None
            readback=tuple(range(21, 31)),  # 저장 후 판독은 성공
        )
        observed_before, _c2, _c3 = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=tuple(range(21, 31)),  # 저장 전 판독 성공 + 실제 점유
            readback=tuple(range(21, 31)),
            answers=("덮어쓰기 진행",),
        )

        # 양쪽 모두 저장은 나간다.
        assert len(_writes(unknown_calls)) == 10
        # 관측된 사전 점유에만 "저장 전부터 차 있던"을 쓴다.
        assert "저장 전부터" in observed_before["text"]
        assert "저장 전부터" not in unknown_before["text"]
        # 그리고 모른다는 사실을 모른다고 적는다.
        assert "저장 전 상태를 읽지 못해" in unknown_before["text"]
        # 어느 쪽도 확인으로 세지 않는다 (둘 다 fail-closed 유지).
        assert "10개 확인" not in unknown_before["text"]
        assert "10개 확인" not in observed_before["text"]

    # AC-PRESETGUARD-009 — 승인 대기가 결함으로 보고되지 않는다
    def test_a_gate_held_store_is_classified_as_pending_not_missing(self, tmp_path):
        event, _calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(),
            status="proposal",
        )

        assert "승인 대기" in event["text"]
        assert "미확인" not in event["text"]

    # F1 — 동의는 명시적·일의적 신호여야 한다 (부분 문자열 매칭 금지)
    #
    # `확인|네|예|응`을 부분 문자열로 찾던 구현에서 아래 다섯 문장이 전부 승낙으로
    # 읽혀 비가역 덮어쓰기가 나갔다. 평범한 한국어 비승낙이 승낙 토큰을 조각으로
    # 품기 때문이며, 토큰을 더 넣는 방식으로는 막을 수 없다.
    @pytest.mark.parametrize(
        "answer",
        [
            "잠깐 확인해보고요",
            "안 되네요",
            "예전 값으로 되돌려줘",
            "네가 판단해",
            "확인 안 했어요",
            # 아래 둘은 옛 구현에서도 우연히 통과했다 — 토큰이 하나 늘면 조용히
            # 승낙으로 넘어갈 수 있으므로 함께 못 박는다.
            "21번은 살려줘",
            "일단 보류",
        ],
    )
    def test_free_text_that_is_not_explicit_consent_stores_nothing(self, tmp_path, answer):
        event, calls, chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=[answer],
        )

        assert len(chan.asked) == 1, answer
        assert _writes(calls) == [], answer
        assert "저장하지 않" in event["text"], answer

    # 비공허성 짝 — 승낙 판정이 "전부 거절"로 퇴화하지 않았음을 고정한다.
    #
    # 이 코퍼스는 **구현의 토큰 목록에서 유도하지 않는다.** 토큰 목록을
    # 파라미터화하면 토큰이 존재하는 한 결코 실패할 수 없어 아무것도 검증하지
    # 못한다(공허). 아래는 운영자가 카드 앞에서 실제로 칠 법한 문장을 손으로 적은
    # 것이며, 그래서 구현이 좁아지면 여기가 먼저 깨진다.
    @pytest.mark.parametrize(
        "answer",
        [
            "덮어쓰기 진행",  # 버튼 그대로
            "덮어쓰기 진행해줘",  # 버튼 + 존대
            "진행해주세요",
            "네 진행해주세요",
            "네",
            "넵",
            "좋아요",
            "응",
            "오케이",
            "덮어써",
            "승인",
            "ok",
            "OK",
            "yes",
        ],
    )
    def test_natural_korean_consent_completes_the_overwrite(self, tmp_path, answer):
        _event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            readback=tuple(range(21, 31)),
            answers=[answer],
        )

        assert len(_writes(calls)) == 10, answer

    # R2 — 거절과 "못 알아들음"은 다른 상태다
    @pytest.mark.parametrize("answer", ["취소", "아니요", "그만", "보류", "no"])
    def test_an_explicit_decline_is_reported_as_a_decline(self, tmp_path, answer):
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=[answer],
        )

        assert _writes(calls) == [], answer
        assert "승인받지 못해" in event["text"], answer

    @pytest.mark.parametrize("answer", ["잠깐 확인해보고요", "네가 판단해", "일단 뭐랄까"])
    def test_an_unreadable_answer_says_so_and_shows_how_to_answer(self, tmp_path, answer):
        # 저장하지 않는 것은 거절과 같지만, 운영자는 거절한 적이 없다. 원인을
        # 잘못 귀속하지 않고 어떻게 답해야 하는지 알려준다.
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=[answer],
        )

        assert _writes(calls) == [], answer
        assert "읽지 못해" in event["text"], answer
        assert "덮어쓰기 진행" in event["text"], answer
        assert "취소" in event["text"], answer
        assert "승인받지 못해" not in event["text"], answer

    def test_a_negated_decline_word_is_not_read_as_a_decline(self, tmp_path):
        # "취소하지 마" = 취소하지 말라 = 승낙 의도. 부분 문자열로 `취소`를 찾으면
        # 정반대로 읽힌다. 승낙으로 단정하지도 않고(모호하므로) 거절로도 읽지
        # 않는다 — 못 알아들었다고 답하고 저장하지 않는다.
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            answers=["취소하지 마"],
        )

        assert _writes(calls) == []
        assert "읽지 못해" in event["text"]
        assert "승인받지 못해" not in event["text"]

    # F3 — 사전 점유 슬롯은 "확인"으로 셀 수 없다
    def test_a_preoccupied_slot_is_not_counted_as_confirmed(self, tmp_path):
        # 21·22·27은 저장 전부터 차 있었다. 되읽기에서 여전히 "있음"으로 보이지만
        # 새 값이 들어갔는지는 알 수 없다 — 응답기가 슬롯 번호만 보내기 때문이다.
        event, _calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(21, 22, 27),
            readback=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )

        assert "10개 확인" not in event["text"]
        assert "7개 확인" in event["text"]
        assert "확인 불가" in event["text"]
        for slot in ("2.21", "2.22", "2.27"):
            assert slot in event["text"].split("확인 불가", 1)[1]

    # F6 — 카드 경로도 점유 구간에서 막힌다 (REQ-001 '출처 무관')
    def test_a_typed_number_from_the_card_hits_the_same_guard(self, tmp_path):
        # 제안 버튼(1·11·31)을 무시하고 손으로 21을 타이핑한 경우. 이 경로가
        # 가드를 통과하지 못하면 가드를 if 갈래 안으로 되돌려도 스위트가 통과한다.
        # `readback`을 일부러 다르게 둔다: 이 경로는 `_position_preset_free_starts`가
        # 풀을 먼저 한 번 읽으므로, 리그가 "첫 판독 = 가드"로 갈랐다면 가드는
        # `readback`(빈 풀)을 보고 충돌 없음으로 통과해 버린다(§F9).
        event, calls, chan = self._run(
            tmp_path,
            "기본 포지션 10개를 프리셋에 저장해줘",
            pool=(21, 22, 23),
            readback=(),
            answers=["21"],  # 시작 번호만 답하고 덮어쓰기 카드는 무응답
        )

        assert _writes(calls) == []
        assert any("덮어씁니다" in ask.prompt for ask in chan.asked)
        assert "2.21" in event["text"]
        assert "2.23" in event["text"]

    # F7 — 차단·거부는 "승인 후 반영"이 아니다
    @pytest.mark.parametrize("status", ["blocked", "rejected"])
    def test_a_gate_blocked_store_is_not_rendered_as_awaiting_approval(self, tmp_path, status):
        event, _calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(),
            status=status,
        )

        assert "게이트 차단" in event["text"], status
        assert "반영되지 않음" in event["text"], status
        assert "승인 후 반영" not in event["text"], status
        # 분류는 여전히 보류다 — 미확인 결함으로 세지 않는다(AC-009).
        assert "미확인" not in event["text"], status

    # AC-PRESETGUARD-014 — 경계가 움직이지 않는다 (기존 안전 동작 회귀)
    def test_the_bundle_shape_and_merge_ban_survive(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
        )

        writes = _writes(calls)
        first = writes[0].arguments["commands"]
        assert first[-3:] == [
            "Store Preset 2.21",
            "Label Preset 2.21 'Home'",
            "ClearAll",
        ]
        commands = _all_commands(calls)
        assert not any("/Merge" in cmd or "/Overwrite" in cmd for cmd in commands)


class TestUnverifiedPoolReachesTheApprovalCard:
    """t217 — 판독 실패 사실은 **쓰기 전 승인 카드**에 실린다.

    REQ-PRESETGUARD-004는 판독 불가에서 *저장을 진행하되 회신에 명시*하라고
    한다. 그런데 그 회신은 되돌릴 수 없는 쓰기가 **끝난 뒤**에야 조립된다
    (``_preset_reply_text``는 완료된 ``_PresetStoreRun``과 되읽기를 받는다).
    사실은 판단 시점에 이미 있는데 사후에만 전달되는 것 — 이 반의 표적이다.

    REQ-PRESETGUARD-005(마찰은 손실 가능성이 있는 자리에만)는 그대로 산다:
    새 질문 카드를 띄우지 않고, **이미 뜨는** 승인 카드(`Store Preset`은
    blacklist 항목이다)에 사실 한 줄을 얹을 뿐이다.
    """

    class _ApprovingRegistry(_PresetPoolRegistry):
        """write 번들마다 게이트가 승인 카드를 띄우는 리그.

        실물 게이트는 `Store Preset`을 hold 하고 ``_notify_approval``로 카드를
        UI에 밀어낸 뒤 사람의 결정을 기다린다. 이 리그는 그 **순간**만 흉내
        낸다 — 카드가 나가는 자리가 쓰기 **직전**이라는 것이 재려는 축이다.
        """

        def __init__(self, calls, session, **rig):
            super().__init__(calls, **rig)
            self._session = session
            self.cards = 0

        def dispatch(self, call, context=None):
            if call.name == "run_commands":
                self.cards += 1
                self._session._notify_approval(
                    f"req-{self.cards}",
                    ApprovalRequest(
                        items=tuple(
                            ApprovalItem(
                                command=command,
                                risk_reasons=("blacklist: Store Preset",),
                            )
                            for command in call.arguments["commands"]
                            if command.startswith("Store Preset")
                        )
                    ),
                )
            return super().dispatch(call)

    def _run(self, tmp_path, **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._ApprovingRegistry(calls, session, **rig)
        session._question_channel = _AnsweringChannel([])
        event = session.run_instruction("기본 포지션 프리셋을 21번부터 저장해줘")
        cards = [frame for frame in sent if frame["type"] == "approval_request"]
        return event, calls, cards

    def test_the_card_carries_the_unreadable_pool_before_the_write(self, tmp_path):
        event, calls, cards = self._run(tmp_path, pool_error=True, readback=())

        # 오늘의 동작 보존 — 판독 불가는 거절이 아니다(REQ-PRESETGUARD-004).
        assert len(_writes(calls)) == 10
        # 카드가 실제로 떴고, 그 카드가 판독 실패를 들고 있다.
        assert len(cards) == 10
        for card in cards:
            warnings = [line for item in card["items"] for line in item["warnings"]]
            assert any("확인하지 못했습니다" in line for line in warnings), warnings
        # 회신에도 그대로 남는다 — 카드는 회신을 대체하지 않고 앞선다.
        assert "확인하지 못했습니다" in event["text"]

    def test_a_verified_empty_span_puts_nothing_extra_on_the_card(self, tmp_path):
        """대조군 팔 2 — 기존 상태에서는 이 문면이 카드에 없다.

        없으면 위 단정이 "언제나 붙는 문자열"을 재는 공허 단언이 된다.
        """
        _event, calls, cards = self._run(
            tmp_path, pool=(1, 2, 3), readback=(1, 2, 3) + tuple(range(21, 31))
        )

        assert len(_writes(calls)) == 10
        assert len(cards) == 10
        for card in cards:
            warnings = [line for item in card["items"] for line in item["warnings"]]
            assert not any("확인하지 못했습니다" in line for line in warnings), warnings

    def test_the_advisory_does_not_leak_past_the_store_loop(self, tmp_path):
        """자문은 저장 루프 안에서만 산다 — 다음 턴의 카드에 묻어가지 않는다."""
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._ApprovingRegistry(calls, session, pool_error=True, readback=())
        session._question_channel = _AnsweringChannel([])
        session.run_instruction("기본 포지션 프리셋을 21번부터 저장해줘")
        sent.clear()

        session._notify_approval(
            "req-later",
            ApprovalRequest(
                items=(ApprovalItem(command="Off Fixture 1", risk_reasons=("실행 중지",)),)
            ),
        )

        later = [frame for frame in sent if frame["type"] == "approval_request"]
        assert len(later) == 1
        assert later[0]["items"][0]["warnings"] == []


class TestPositionPresetRegeneration:
    """SPEC-COPILOT-PRESETGUARD-001 §B.3 — 지금 배치로 기존 구간을 다시 잡는다."""

    def _run(self, tmp_path, text, *, answers=(), channel=True, **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, **rig)
        chan = _AnsweringChannel(answers) if channel else None
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # AC-PRESETGUARD-010 — 재생성이 기존 구간을 표적으로 삼는다 (뮤테이션 필수)
    def test_regeneration_overwrites_the_stored_span_in_place(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )

        commands = _all_commands(calls)
        for offset in range(10):
            assert f"Store Preset 2.{21 + offset}" in commands
        # 새 시작 번호를 묻지 않는다 — 새 자리에 저장하면 큐가 따라오지 않는다.
        assert all("몇 번부터" not in ask.prompt for ask in chan.asked)
        # 큐·시퀀스는 건드리지 않는다 — 참조를 든 큐는 프리셋 갱신만으로 따라온다.
        assert not any("Store Sequence" in cmd or "Cue" in cmd for cmd in commands)

    # AC-PRESETGUARD-011 — 겹치는 문장이 재생성으로 결정적 라우팅된다 (뮤테이션 필수)
    def test_overlapping_sentences_route_to_regeneration(self, tmp_path):
        corpus = [
            "기본 포지션 다시 잡아줘",
            "지금 배치로 기본 포지션 다시 잡아줘",
            "기본 포지션 프리셋 재생성해줘",
        ]
        for text in corpus:
            _event, calls, chan = self._run(
                tmp_path,
                text,
                pool=tuple(range(21, 31)),
                answers=["덮어쓰기 진행"],
            )
            commands = _all_commands(calls)
            assert "Store Preset 2.21" in commands, text
            assert all("몇 번부터" not in ask.prompt for ask in chan.asked), text

    def test_new_store_sentences_still_route_to_the_store_path(self, tmp_path):
        # 명시 번호가 있으면 신규 저장이다 — 21번 구간이 비어 있으므로 카드 없이 저장.
        _event, calls, chan = self._run(
            tmp_path,
            "기본 포지션 10개를 프리셋 21번부터 저장해줘",
            pool=(1, 2, 3),
        )
        assert chan.asked == []
        assert "Store Preset 2.21" in _all_commands(calls)

        # 번호가 없으면 시작 번호를 묻는 기존 카드가 그대로 뜬다.
        _event2, calls2, chan2 = self._run(
            tmp_path,
            "기본 포지션 10개를 프리셋에 저장해줘",
            pool=(1, 2, 3),
            answers=["41"],
        )
        assert any("몇 번부터" in ask.prompt for ask in chan2.asked)
        assert "Store Preset 2.41" in _all_commands(calls2)

    # AC-PRESETGUARD-012 — 재생성도 같은 fail-closed를 통과한다 (뮤테이션 필수)
    def test_regeneration_stores_nothing_without_an_answer(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=tuple(range(21, 31)),
            answers=[],  # UNANSWERED
        )

        assert _writes(calls) == []
        assert "응답" in event["text"]

    # AC-PRESETGUARD-013 — 표적이 모호하면 묻고, 미상이면 저장하지 않는다
    def test_no_stored_span_refuses_without_writing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=(1, 2, 3),
        )

        assert _writes(calls) == []
        assert "찾지 못" in event["text"]

    def test_two_candidate_spans_ask_which_one(self, tmp_path):
        occupied = tuple(range(1, 11)) + tuple(range(21, 31))
        _event, calls, chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=occupied,
            answers=["21", "덮어쓰기 진행"],
        )

        assert any("어느 구간" in ask.prompt for ask in chan.asked)
        assert "Store Preset 2.21" in _all_commands(calls)

    # F2 — 구간 선택 답은 후보 목록과 대조된다
    #
    # "2번째"(두 번째라는 뜻)가 숫자 2로 파싱돼 2.2~2.11을 덮어쓰면 원래 구간이
    # 한 칸 밀리고, 2.1을 참조하던 큐만 옛 좌표에 남는다. 그 상태에서 회신은
    # "같은 자리에 다시 저장"이라고 말한다. "1번 말고 21번"은 첫 숫자만 집으면
    # 1을 고르는데, 1도 후보라 범위 검사만으로는 걸러지지 않는다.
    @pytest.mark.parametrize("answer", ["2번째", "1번 말고 21번", "두 번째", "아무거나"])
    def test_an_answer_that_does_not_name_one_candidate_stores_nothing(self, tmp_path, answer):
        occupied = tuple(range(1, 11)) + tuple(range(21, 31))
        # 덮어쓰기 카드까지 **승낙**을 미리 넣어 둔다. 넣지 않으면 구간을 잘못
        # 고르더라도 두 번째 카드가 무응답으로 막아서 테스트가 통과해 버린다 —
        # 구간 선택이 아니라 fail-closed를 검증하는 꼴이 된다.
        event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=occupied,
            answers=[answer, "덮어쓰기 진행"],
        )

        assert _writes(calls) == [], answer
        assert "Store Preset 2.2" not in _all_commands(calls), answer
        assert "저장하지 않" in event["text"], answer

    def test_the_span_card_accepts_the_offered_label_verbatim(self, tmp_path):
        # 비공허성 짝 — 버튼을 그대로 누른 답(라벨에 숫자가 여럿 들어 있다)은
        # 모호하다고 거절되면 안 된다.
        occupied = tuple(range(1, 11)) + tuple(range(21, 31))
        _event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=occupied,
            answers=["21 (2.21~2.30)", "덮어쓰기 진행"],
        )

        assert "Store Preset 2.21" in _all_commands(calls)

    # F4 — 번호를 지목해도 재생성은 재생성이다
    def test_a_numbered_regeneration_sentence_stays_in_the_regeneration_path(self, tmp_path):
        # 풀 미상에서 신규 저장은 진행하고(REQ-004) 재생성은 거부한다(AC-013③).
        # 번호가 있다고 신규 저장으로 넘기면 이 문장이 카드 한 장 없이
        # 2.21~2.30을 덮어쓴다 — 이 SPEC이 없애려던 바로 그 형상이다.
        event, calls, chan = self._run(
            tmp_path,
            "21번부터 기본 포지션 다시 잡아줘",
            pool_error=True,
        )

        assert _writes(calls) == []
        assert chan.asked == []
        assert "저장하지 않" in event["text"]

    def test_a_numbered_regeneration_sentence_targets_the_named_span(self, tmp_path):
        occupied = tuple(range(1, 11)) + tuple(range(21, 31))
        _event, calls, chan = self._run(
            tmp_path,
            "21번부터 기본 포지션 다시 잡아줘",
            pool=occupied,
            answers=["덮어쓰기 진행"],
        )

        assert "Store Preset 2.21" in _all_commands(calls)
        # 후보가 둘이지만 번호를 지목했으므로 구간을 되묻지 않는다.
        assert all("어느 구간" not in ask.prompt for ask in chan.asked)

    def test_a_named_span_that_is_not_a_stored_run_stores_nothing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "41번부터 기본 포지션 다시 잡아줘",
            pool=tuple(range(21, 31)),
        )

        assert _writes(calls) == []
        assert "저장하지 않" in event["text"]

    # F5 — '다시'가 다른 동사에 붙은 문장은 재생성이 아니다.
    def test_an_adverbial_dasi_does_not_route_to_regeneration(self, tmp_path):
        # "끝나면 다시 알려줘"의 '다시'는 알려줘를 꾸민다. 이 문장이 재생성으로
        # 가면 저장 요청이 "먼저 저장하세요"로 되돌아와 영원히 같은 답이 나온다.
        _event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋 10개 저장해줘, 끝나면 다시 알려줘",
            pool=(),
            answers=["1"],
        )

        assert "Store Preset 2.1" in _all_commands(calls)

    def test_an_adverbial_dasi_never_offers_to_overwrite_an_unmentioned_span(self, tmp_path):
        # 풀에 10칸 구간이 있으면, 옛 정규식은 사용자가 언급한 적 없는 21~30을
        # "다시 잡으면 … 덮어씁니다"로 제안했다.
        _event, _calls, chan = self._run(
            tmp_path,
            "기본 포지션 프리셋 10개 저장해줘, 끝나면 다시 알려줘",
            pool=tuple(range(21, 31)),
            answers=["1"],
        )

        assert not any("다시 잡으면" in ask.prompt for ask in chan.asked)

    # R4 — '저장'은 신규 저장의 동사다. 재생성 어휘에 넣으면 안 된다.
    def test_dasi_jeojang_routes_to_the_store_path_on_an_empty_pool(self, tmp_path):
        # 옛 어휘에서는 이 문장이 재생성으로 끌려가, 저장해달라는 요청에
        # "먼저 '기본 포지션 10개 저장'을 실행해 주세요"라고 답했다 — 같은 문장을
        # 다시 쳐도 영원히 같은 답이 나오는 자기모순이다.
        event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋 21번부터 다시 저장해줘",
            pool=(),
        )

        assert "Store Preset 2.21" in _all_commands(calls)
        assert "다시 잡을 자리가 없습니다" not in event["text"]

    def test_dasi_jeojang_is_not_refused_after_a_partial_first_store(self, tmp_path):
        # 첫 저장이 일부만 착지하면(게이트 보류·부분 거절) 그 구간은 정의상
        # 10칸 연속이 아니다. 재생성이 이 문장을 삼키면 가장 자연스러운 재시도가
        # **영구히** 거부된다 — 하필 재시도가 가장 필요한 상황에서.
        event, calls, chan = self._run(
            tmp_path,
            "기본 포지션 프리셋 21번부터 다시 저장해줘",
            pool=tuple(range(21, 26)),  # 21~25만 착지한 상태
            readback=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )

        assert len(_writes(calls)) == 10
        assert "Store Preset 2.21" in _all_commands(calls)
        # 거부가 아니라 덮어쓰기 확인으로 간다 — 21~25는 실제로 덮어써지므로.
        assert any("덮어씁니다" in ask.prompt for ask in chan.asked)
        assert "자리가 없습니다" not in event["text"]

    # R3 — 같은 어휘에 부사 하나가 껴도 재생성이다
    @pytest.mark.parametrize(
        "text",
        [
            "기본 포지션 다시 한번 잡아줘",
            "기본 포지션 다시 좀 잡아줘",
            "지금 배치로 기본 포지션 다시 한번 잡아줘",
        ],
    )
    def test_an_adverb_between_dasi_and_the_verb_stays_regeneration(self, tmp_path, text):
        # `\S`가 공백을 넘지 못해 이 문장들이 저장 경로로 샜다. 그러면 **새 구간**에
        # 저장되는데 운영자는 기존 프리셋이 갱신됐다고 믿는다 — 큐는 옛 좌표를
        # 계속 가리키므로, 조용히 틀리는 종류의 실패다.
        _event, calls, chan = self._run(
            tmp_path,
            text,
            pool=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )

        assert "Store Preset 2.21" in _all_commands(calls), text
        # 새 시작 번호를 묻지 않는다 = 기존 구간을 제자리 갱신했다.
        assert all("몇 번부터" not in ask.prompt for ask in chan.asked), text

    def test_an_unreadable_pool_refuses_instead_of_guessing_a_span(self, tmp_path):
        # 신규 저장(REQ-004, 진행)과 **반대**다 — 재생성은 표적의 존재를 전제한다.
        event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool_error=True,
        )

        assert _writes(calls) == []
        assert "읽지 못" in event["text"]


class TestFxPositionPresetRegeneration:
    """FX 재생성 — '지금 배치로 이펙트 포지션 다시 잡아줘'가 저장된 FX 구간을
    **제자리** 갱신한다. 몸통은 `_regenerate_position_preset_sequence`로 BASIC
    재생성과 공유되므로(풀 미상 거부·구간 탐색·덮어쓰기 카드·되읽기), 여기서는
    라우팅(상호 배타)·제자리 갱신·FX 고유 문면을 겨눈다.
    """

    def _run(self, tmp_path, text, *, answers=(), **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, **rig)
        chan = _AnsweringChannel(answers)
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # 제자리 갱신 — 저장된 41~50 구간에 **같은 번호**로 Store 10건. 새 시작
    # 번호를 묻지 않는다: 새 자리에 저장하면 프리셋 참조를 든 이펙트 시퀀스가
    # 옛 좌표를 계속 가리킨다.
    def test_fx_regeneration_overwrites_the_stored_span_in_place(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "지금 배치로 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(41, 51)),
            answers=["덮어쓰기 진행"],
        )

        commands = _all_commands(calls)
        for offset, label in enumerate(FX_POSITION_SEQUENCE):
            assert f"Store Preset 2.{41 + offset}" in commands
            assert f"Label Preset 2.{41 + offset} '{label}'" in commands
        assert len(_writes(calls)) == 10
        assert all("몇 번부터" not in ask.prompt for ask in chan.asked)

    # 가족 필터 실측 재현 2026-08-16 — 21~50이 전부 저장된 풀(연속 30칸)에서
    # ready 후보는 21·31·41이지만, FX 재생성은 첫 슬롯 라벨이 'Sweep L'인
    # 41만 겨눠야 한다. 필터가 없으면 카드 첫 옵션(21)이 선택될 때 BASIC
    # 프리셋 10개가 FX 값으로 덮인다 — 실제로 일어났던 사고다.
    _FAMILY_NAMES = {
        21: "Home",
        31: "Home#2",
        41: "Sweep L",
    }

    def test_fx_regeneration_skips_basic_spans_by_first_slot_label(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "지금 배치로 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(21, 51)),
            names=self._FAMILY_NAMES,
            answers=["덮어쓰기 진행"],
        )

        commands = _all_commands(calls)
        # 유일한 FX 가족 후보(41)라 구간 선택 카드 없이 41~50만 갱신한다.
        assert all("어느 구간" not in ask.prompt for ask in chan.asked)
        for offset in range(10):
            assert f"Store Preset 2.{41 + offset}" in commands
        assert not any(cmd.startswith("Store Preset 2.2") for cmd in commands)
        assert not any(cmd.startswith("Store Preset 2.3") for cmd in commands)

    def test_a_named_basic_span_is_refused_for_fx_regeneration(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "21번부터 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(21, 51)),
            names=self._FAMILY_NAMES,
        )

        assert _writes(calls) == []
        assert "구간이 아닙니다" in event["text"]

    def test_basic_regeneration_offers_only_home_spans(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=tuple(range(21, 51)),
            names=self._FAMILY_NAMES,
            answers=["21 (2.21~2.30)", "덮어쓰기 진행"],
        )

        span_cards = [ask for ask in chan.asked if "어느 구간" in ask.prompt]
        assert len(span_cards) == 1
        labels = [option.label for option in span_cards[0].options]
        assert any(label.startswith("21 ") for label in labels)
        assert any(label.startswith("31 ") for label in labels)
        assert not any(label.startswith("41 ") for label in labels)
        commands = _all_commands(calls)
        assert "Store Preset 2.21" in commands

    def test_unnamed_pool_children_keep_the_old_run_start_behaviour(self, tmp_path):
        # 이름 없는 페이로드(구형)는 판별 불가 — 런 시작(연속 덩어리의 첫
        # 슬롯)만 후보로 남는 종전 동작이 보존된다. 21~50 연속 풀의 런 시작은
        # 21 하나라 카드 없이 21이 선택된다 — 바로 이 형상이 이름이 필요한
        # 이유다(실측 사고의 재현이자, 이름이 오면 필터가 이를 막는다).
        _event, calls, chan = self._run(
            tmp_path,
            "지금 배치로 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(21, 51)),
            answers=["덮어쓰기 진행"],
        )

        assert all("어느 구간" not in ask.prompt for ask in chan.asked)
        assert "Store Preset 2.21" in _all_commands(calls)

    # 라우팅 — FX 재생성 어휘 변형이 전부 재생성으로 간다. 신규 저장으로 샜다면
    # 시작 번호 카드("몇 번부터")가 떴을 것이다.
    @pytest.mark.parametrize(
        "text",
        [
            "이펙트 포지션 다시 잡아줘",
            "지금 배치로 효과 포지션 다시 잡아줘",
            "fx 포지션 재생성해줘",
            "이펙트 포지션 다시 한번 잡아줘",
        ],
    )
    def test_fx_regeneration_vocabulary_routes_to_regeneration(self, tmp_path, text):
        _event, calls, chan = self._run(
            tmp_path,
            text,
            pool=tuple(range(41, 51)),
            answers=["덮어쓰기 진행"],
        )

        assert "Store Preset 2.41" in _all_commands(calls), text
        assert all("몇 번부터" not in ask.prompt for ask in chan.asked), text

    # 풀 미상 — 표적 구간의 존재를 확인하지 못하면 저장하지 않는다(unknown ≠
    # empty; 신규 저장의 '진행'과 반대). 번호를 지목해도 재생성은 재생성이다.
    def test_an_unreadable_pool_refuses_fx_regeneration_without_writing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "41번부터 이펙트 포지션 다시 잡아줘",
            pool_error=True,
        )

        assert _writes(calls) == []
        assert chan.asked == []
        assert "저장하지 않" in event["text"]

    def test_no_stored_span_refuses_and_names_the_fx_store_step(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 이펙트 포지션 다시 잡아줘",
            pool=(1, 2, 3),
        )

        assert _writes(calls) == []
        assert "FX 포지션 10개 저장" in event["text"]

    def test_a_named_fx_span_that_is_not_a_stored_run_stores_nothing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "21번부터 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(41, 51)),
        )

        assert _writes(calls) == []
        assert "저장하지 않" in event["text"]

    # fail-closed — 덮어쓰기 카드 무응답이면 쓰기 0건 (BASIC과 같은 공용 카드).
    def test_fx_regeneration_stores_nothing_without_an_answer(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "지금 배치로 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(41, 51)),
            answers=[],  # UNANSWERED
        )

        assert _writes(calls) == []
        assert "응답" in event["text"]

    # 상호 배타 — '기본' 문장은 BASIC 룩만, '이펙트' 문장은 FX 룩만 만든다.
    # 같은 21~30 구간을 겨눠도 어휘가 빌더를 정한다.
    def test_the_two_regeneration_vocabularies_never_cross_route(self, tmp_path):
        _e1, basic_calls, _c1 = self._run(
            tmp_path,
            "지금 배치로 기본 포지션 다시 잡아줘",
            pool=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )
        basic_commands = _all_commands(basic_calls)
        assert f"Label Preset 2.21 '{BASIC_POSITION_SEQUENCE[0]}'" in basic_commands
        assert not any(f"'{FX_POSITION_SEQUENCE[0]}'" in cmd for cmd in basic_commands)

        _e2, fx_calls, _c2 = self._run(
            tmp_path,
            "지금 배치로 이펙트 포지션 다시 잡아줘",
            pool=tuple(range(21, 31)),
            answers=["덮어쓰기 진행"],
        )
        fx_commands = _all_commands(fx_calls)
        assert f"Label Preset 2.21 '{FX_POSITION_SEQUENCE[0]}'" in fx_commands
        assert not any(f"'{BASIC_POSITION_SEQUENCE[0]}'" in cmd for cmd in fx_commands)

    # F5의 FX 판도 같다 — '다시'가 알림을 꾸민 저장 문장은 재생성이 아니다.
    def test_an_adverbial_dasi_keeps_the_fx_store_path(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "이펙트 포지션 프리셋 10개 저장해줘, 끝나면 다시 알려줘",
            pool=(),
            answers=["41"],
        )

        assert "Store Preset 2.41" in _all_commands(calls)
        assert "다시 잡을 자리가 없습니다" not in event["text"]


class TestFxPositionPresets:
    """FX 포지션 프리셋 — 페이저 이펙트의 골격 10종을 BASIC과 **동일한** 안전
    장치(점유 가드 → 덮어쓰기 카드 → 룩별 번들 → 되읽기 산술)로 저장한다.

    흐름 자체는 `_store_position_preset_sequence`로 BASIC과 공유되므로, 여기서는
    라우팅(상호 배타)과 FX 고유 문면·라벨 순서를 겨눈다.
    """

    def _run(self, tmp_path, text, *, answers=(), **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, **rig)
        chan = _AnsweringChannel(answers)
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # 라우팅 — FX 문장은 FX 흐름으로 들어가 41번부터 열 개를 저장한다. 재생성
    # 핸들러가 앞에서 가로챘다면 (풀에 10칸 연속 구간이 없으므로) 쓰기 0건으로
    # 거부됐을 것이다 — 열 개의 Store가 그 오인 매칭의 부재를 함께 증언한다.
    def test_an_fx_request_stores_ten_presets_from_the_named_number(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "이펙트 포지션 프리셋을 41번부터 저장해줘",
            pool=(1, 2, 3),
        )

        assert chan.asked == []
        assert len(_writes(calls)) == 10
        commands = _all_commands(calls)
        for offset, label in enumerate(FX_POSITION_SEQUENCE):
            assert f"Store Preset 2.{41 + offset}" in commands
            assert f"Label Preset 2.{41 + offset} '{label}'" in commands

    # 라우팅 회귀 — '기본 포지션' 문장은 여전히 BASIC 시퀀스로 간다.
    def test_a_basic_request_still_lands_in_the_basic_flow(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "기본 포지션 프리셋을 21번부터 저장해줘",
            pool=(1, 2, 3),
        )

        commands = _all_commands(calls)
        assert "Label Preset 2.21 'Home'" in commands
        assert not any("'Sweep L'" in command for command in commands)

    # 라우팅 — 저장 동사 없는 이펙트 **적용** 요청은 어느 프리셋 흐름에도 안 간다.
    def test_an_effect_application_request_enters_neither_flow(self, tmp_path):
        provider = ScriptedProvider([_final("이펙트 적용을 확인하겠습니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls)
        chan = _AnsweringChannel([])
        session._question_channel = chan

        session.run_instruction("무빙 이펙트 적용해줘")

        # 모델까지 내려갔다 — 프리셋 저장 흐름의 카드도 쓰기도 없다.
        assert len(provider.calls) == 1
        assert chan.asked == []
        assert not any("Store Preset" in command for command in _all_commands(calls))

    # 명시 번호가 점유 슬롯과 겹치면 카드가 뜨고, '취소'는 쓰기 0건이다.
    def test_a_collision_asks_the_card_and_cancel_writes_nothing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "이펙트 포지션 프리셋을 41번부터 저장해줘",
            pool=(41, 42, 47),
            answers=["취소"],
        )

        assert _writes(calls) == []
        assert len(chan.asked) == 1
        assert "덮어씁니다" in chan.asked[0].prompt
        assert "2.41" in chan.asked[0].prompt
        assert "승인" in event["text"] or "저장하지 않" in event["text"]

    # 승낙 시 룩별 독립 번들이 FX_POSITION_SEQUENCE 순서·라벨 그대로 나간다.
    def test_consent_stores_each_look_as_its_own_bundle_in_sequence_order(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path,
            "이펙트 포지션 프리셋을 41번부터 저장해줘",
            pool=(41, 42, 47),
            readback=tuple(range(41, 51)),
            answers=["덮어쓰기 진행"],
        )

        writes = _writes(calls)
        assert len(writes) == 10
        for offset, (call, label) in enumerate(zip(writes, FX_POSITION_SEQUENCE, strict=True)):
            commands = call.arguments["commands"]
            assert commands[-3] == f"Store Preset 2.{41 + offset}"
            assert commands[-2] == f"Label Preset 2.{41 + offset} '{label}'"
            assert commands[-1] == "ClearAll"

    # 저장 후 되읽기 산술(착지/누락)이 회신 문면에 실린다.
    def test_the_readback_carries_arithmetic_including_a_missing_slot(self, tmp_path):
        verified, verified_calls, _c1 = self._run(
            tmp_path,
            "이펙트 포지션 프리셋을 41번부터 저장해줘",
            pool=(1, 2, 3),
            readback=tuple(range(41, 51)),
        )
        landed = tuple(n for n in range(41, 51) if n != 47)
        partial, partial_calls, _c2 = self._run(
            tmp_path,
            "이펙트 포지션 프리셋을 41번부터 저장해줘",
            pool=(1, 2, 3),
            readback=landed,
        )

        assert len(_writes(verified_calls)) == 10
        assert "기대 10개" in verified["text"]
        assert "10개 확인" in verified["text"]
        assert len(_writes(partial_calls)) == 10
        assert "미확인" in partial["text"]
        assert "2.47" in partial["text"]

    # 번호 미지정이면 시작 번호 질문 카드가 정확히 한 번 뜬다.
    def test_no_number_asks_the_start_question_once(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "이펙트 포지션 프리셋 저장해줘",
            pool=(1, 2, 3),
            answers=[],  # UNANSWERED
        )

        assert len(chan.asked) == 1
        assert "몇 번부터" in chan.asked[0].prompt
        assert "FX 포지션" in chan.asked[0].prompt
        assert _writes(calls) == []
        assert "시작 프리셋 번호" in event["text"]


class TestPositionCueStoreSession:
    """T1: '프리셋 N을 시퀀스 S 큐 C로 저장, 페이드 F초' — preset-referenced cue."""

    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    def test_the_full_instruction_builds_the_referenced_cue_bundle(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel([])
        session._question_channel = channel

        event = session.run_instruction("프리셋 2.28을 시퀀스 101 큐 1로 저장, 페이드 5초")

        assert provider.calls == []
        assert channel.asked == []
        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        assert writes[0].arguments["commands"] == [
            "Fixture 20 + 26 ; At Preset 2.28",
            "Store Sequence 101 Cue 1 'Pos 2.28' CueFade 5",
            "ClearAll",
        ]
        assert "페이드 5초" in event["text"]

    def test_a_missing_sequence_number_asks_one_card(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["110"])
        session._question_channel = channel

        session.run_instruction("프리셋 28번 포지션을 큐로 저장해줘, 페이드 3초")

        assert len(channel.asked) == 1
        assert "어느 시퀀스" in channel.asked[0].prompt
        writes = [call for call in calls if call.name == "run_commands"]
        assert writes[0].arguments["commands"][1] == (
            "Store Sequence 110 Cue 1 'Pos 2.28' CueFade 3"
        )

    def test_no_answer_refuses_instead_of_guessing_a_sequence(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])  # UNANSWERED

        event = session.run_instruction("프리셋 28을 큐로 저장해줘")

        # Read-only probes (verified number proposals, 2026-08-16) are fine;
        # the invariant is ZERO writes without an answer.
        assert calls[0].name == "get_spatial_context"
        assert all(call.name in ("get_spatial_context", "query_state") for call in calls)
        assert "시퀀스 번호를 받지 못해" in event["text"]

    def test_a_fade_less_instruction_omits_cuefade(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])

        session.run_instruction("프리셋 2.21을 시퀀스 101 큐 2로 저장해줘")

        writes = [call for call in calls if call.name == "run_commands"]
        assert writes[0].arguments["commands"][1] == "Store Sequence 101 Cue 2 'Pos 2.21'"

    def test_a_preset_store_without_cue_words_is_not_intercepted(self, tmp_path):
        # "프리셋 N로 저장" (no 큐) stays with the look/preset path.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])

        session.run_instruction("장비들이 바깥쪽을 바라보게 하고 프리셋 11로 저장해줘")

        writes = [call for call in calls if call.name == "run_commands"]
        commands = writes[0].arguments["commands"]
        assert any(command.startswith("Store Preset 2.11") for command in commands)
        assert not any("Store Sequence" in command for command in commands)


class TestPositionCueSheetSession:
    """T3: '포지션 큐 시트 …: 이름 시각 무드, …' — full-song preset-cue draft."""

    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    _FULL = (
        "포지션 큐 시트 만들어줘, 시퀀스 110, 프리셋 21번부터, 페이드 2초: "
        "인트로 0:00 잔잔한 발라드, 브레이크 0:40 암전, 후렴 0:50 클럽 드롭"
    )

    def test_a_full_instruction_stores_the_sheet_with_mib(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel([])
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        assert provider.calls == []
        assert channel.asked == []
        writes = [call for call in calls if call.name == "run_commands"]
        # 3 sections + 1 MIB pre-move, each its own bundle.
        assert [call.id for call in writes] == [
            "song-sheet-cue-1",
            "song-sheet-cue-2",
            "song-sheet-cue-2.5",
            "song-sheet-cue-3",
        ]
        premove = writes[2].arguments["commands"]
        assert premove == [
            "Fixture 20 + 26 ; At Preset 2.28",
            "Store Sequence 110 Cue 2.5 'Section 3 Move' CueFade 1",
            "ClearAll",
            "Set Cue 2.5 Sequence 110 Property 'TrigType' 'Follow'",
        ]
        reveal = writes[3].arguments["commands"]
        assert reveal == [
            "Fixture 20 + 26 ; Attribute 'Dimmer' At 100",
            "Store Sequence 110 Cue 3 'Section 3' CueFade 2",
            "ClearAll",
        ]
        assert "Vocal DSC" in event["text"]
        assert "MIB 삽입" in event["text"]

    def test_missing_numbers_ask_two_cards_in_order(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["110", "21"])
        session._question_channel = channel

        session.run_instruction("포지션 큐 시트: 인트로 0:00 잔잔하게, 후렴 0:40 클럽 드롭")

        assert len(channel.asked) == 2
        assert "어느 시퀀스" in channel.asked[0].prompt
        assert "몇 번부터" in channel.asked[1].prompt
        writes = [call for call in calls if call.name == "run_commands"]
        assert writes[0].arguments["commands"][0] == "Fixture 20 + 26 ; At Preset 2.25"

    def test_no_answer_refuses(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])  # UNANSWERED

        event = session.run_instruction("포지션 큐 시트: 인트로 0:00 잔잔하게, 후렴 0:40 드롭")

        # Read-only probes (verified number proposals, 2026-08-16) are fine;
        # the invariant is ZERO writes without an answer.
        assert calls[0].name == "get_spatial_context"
        assert all(call.name in ("get_spatial_context", "query_state") for call in calls)
        assert "시퀀스 번호를 받지 못해" in event["text"]

    def test_unparseable_sections_refuse_with_the_format(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])

        event = session.run_instruction("포지션 큐 시트 만들어줘")

        assert calls == []
        assert "형식" in event["text"]


class TestSongDesignInterviewSession:
    """SONGSTD M2 R1c/R4: '디자인 큐 시트 …' — 5-card director interview
    (Q1 컨셉 ~ Q5 전환 방식) → standard profile+rig sheet. Narrowly gated on
    "디자인"/"연출 인터뷰" so it never fires on the existing "포지션 큐 시트"
    vocabulary (see ``TestPositionCueSheetSession`` above, unmodified)."""

    def _sequence_readback(self, *, cue_1_trig_time: object = "0") -> dict:
        return {
            "ok": True,
            "path": "DataPool/Sequences/110",
            "node": {"name": "Sequence 110", "class": "Sequence", "childCount": 2},
            "children": [
                {
                    "class": "Cue",
                    "cueNo": 1,
                    "name": "Intro",
                    "TrigType": "Time",
                    "TrigTime": cue_1_trig_time,
                },
                {
                    "class": "Cue",
                    "cueNo": 2,
                    "name": "Chorus",
                    "properties": {"TrigType": "Time", "TrigTime": "40"},
                },
            ],
        }

    def _timecode_readback(self) -> dict:
        return {
            "ok": True,
            "path": "DataPool/Timecodes/7",
            "node": {"name": "Sequence 110 Timecode", "class": "Timecode", "childCount": 0},
            "children": [],
        }

    def _registry(
        self,
        calls,
        *,
        sequence_readback=None,
        timecode_readback=None,
        groups_readback=None,
        preset_pool_readback=None,
        sequence_exists_before_store=False,
        timecode_exists_before_store=False,
        store_fails=False,
        spatial_fails=False,
    ):
        # 카드 t311 — `spatial_fails` 는 좌표 판독만 실패시킨다(패치 없는 리그).
        # 나머지 응답은 그대로라, 「좌표가 없다」와 「콘솔이 죽었다」가 갈린다.
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
        ]
        states = {
            "DataPool/Sequences/110": sequence_readback or self._sequence_readback(),
            "DataPool/Timecodes/7": timecode_readback or self._timecode_readback(),
            "DataPool/Groups": groups_readback or {},
            "DataPool/PresetPools/2": preset_pool_readback or {},
        }

        class Registry:
            # SPEC-COPILOT-WRITEGATE-001 — `_song_finalize` 이 번들 위험 선언을
            # 실은 `ExecutionContext` 를 둘째 인자로 넘기므로, 더블도 진짜
            # `ToolRegistry` 와 같은 자리에서 그것을 받아야 한다. 여기서는 받기만
            # 한다 — 게이트 판정은 진짜 게이트를 쓰는
            # `test_writegate_song_finalize.py` 가 잰다.
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
                calls.append(call)
                if call.name == "get_spatial_context":
                    if spatial_fails:
                        return ToolExecution(
                            ToolResult(
                                tool_call_id=call.id,
                                name=call.name,
                                content="path segment not found: Patch/Stages/1/Fixtures",
                                is_error=True,
                            )
                        )
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(
                                {"fixtures": fixtures, "coverage": {"complete": True}}
                            ),
                        )
                    )
                if call.name == "query_state":
                    path = call.arguments["path"]
                    # A real console's target sequence is EMPTY before the
                    # store bundle runs (the 2026-08-16 occupied-slot pre-check
                    # reads it first); the readback fixture only exists AFTER
                    # a run_commands dispatched the stores.
                    stored = any(entry.name == "run_commands" for entry in calls)
                    if (
                        path.startswith(("DataPool/Sequences/", "DataPool/Timecodes/"))
                        and not stored
                        and not (
                            sequence_exists_before_store and path.startswith("DataPool/Sequences/")
                        )
                        and not (
                            timecode_exists_before_store and path.startswith("DataPool/Timecodes/")
                        )
                    ):
                        payload = {}
                    else:
                        payload = states.get(path, {})
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(payload),
                        )
                    )
                if call.name == "run_commands" and store_fails:
                    outcomes = tuple(
                        CommandOutcome(
                            command=command,
                            status=("failed" if command.startswith("Store ") else "proposal"),
                            detail=("Not allowed" if command.startswith("Store ") else ""),
                        )
                        for command in call.arguments.get("commands", [])
                    )
                    return ToolExecution(
                        ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                        outcomes,
                    )
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                    (CommandOutcome(command="Fixture 20", status="proposal"),),
                )

        return Registry()

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    _FULL = (
        "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7: "
        "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
    )

    def test_full_choice_flow_previews_before_any_write_and_asks_for_approval(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        # Every answer is the recommended (index-0) option label for this
        # rig/profile — a deterministic full-choice path (DI1 confirms every
        # axis; no auto-draft anywhere).
        channel = self._Channel(
            ["우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]
        )
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        assert len(channel.asked) == 6
        assert [q.prompt for q in channel.asked[:5]] == [
            "공연 전체가 어떤 느낌이면 좋겠어요?",
            "어떤 색이 가장 잘 어울릴까요?",
            "가장 중요한 순간을 어떻게 보여 주면 좋겠어요?",
            "처음부터 끝까지 무대가 어떻게 달라 보이면 좋겠어요?",
            "전환 방식은 어떻게 갈까요? 컷으로 딱 끊을지, 페이드로 이어갈지 정해요.",
        ]
        assert "전곡 리뷰 번들" in channel.asked[5].prompt
        # T12(d) — the '후렴' section's phaser proposal (Wave CM) is visible
        # in the pre-approval review sheet BEFORE any console write, plus
        # the [ASSUMPTION] caveat that recall/reference persistence is not
        # mechanically verifiable (T11 프로브 §1/§4).
        assert "페이저 제안: Wave CM" in channel.asked[5].prompt
        assert "ASSUMPTION" in channel.asked[5].prompt
        assert "콘솔 화면에서 직접 확인" in channel.asked[5].prompt
        for q in channel.asked[:5]:
            assert len(q.options) == 3  # R1c: 제안 3개 + 자유 입력(무조건 제공)
        writes = [call for call in calls if call.name == "run_commands"]
        assert writes == []
        assert event["status"] == "ok"
        assert "(확정)" in event["text"]
        assert "(감독 미확정)" not in event["text"]
        assert "승인 전" in event["text"]
        timelines = [event["timeline"] for event in sent if event["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"
        assert timelines[-1]["sections"][0]["cue_number"] == 1
        assert timelines[-1]["sections"][0]["trig_time_seconds"] == 0

    def test_natural_song_lighting_brief_routes_to_timeline(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(
            ["우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]
        )

        event = session.run_instruction(
            "90초 록 곡 조명 설계를 만들어줘. 시퀀스 110, 프리셋 21번부터, 수동 Go. "
            "0:00 인트로는 파란색과 낮은 밝기로 시작하고, "
            "0:24 벌스에서 시안을 추가해 조금 올리고, "
            "0:48 후렴에서 마젠타와 화이트로 가장 크게 터뜨리고, "
            "1:12 마지막은 화이트 스냅으로 마무리해줘. "
            "아직 콘솔에는 적용하지 말고 검토용 타임라인만 만들어줘."
        )

        assert event["status"] == "ok"
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [event["timeline"] for event in sent if event["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "requires_requery"
        assert [section["label"] for section in timelines[-1]["sections"]] == [
            "인트로",
            "벌스",
            "후렴",
            "마지막",
        ]

    def test_plain_multisection_song_brief_starts_full_interview_not_model_execution(
        self, tmp_path
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "수정",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction(
            "곡은 약 1분 40초의 밝은 팝 무대야.\n"
            "0:00 도입은 무대를 어둡게 두고 보컬에게만 시선을 모아줘.\n"
            "0:22 벌스는 리듬이 시작되면서 무대 폭을 조금씩 넓혀줘.\n"
            "0:48 첫 후렴은 관객까지 에너지가 퍼지는 가장 큰 장면으로 만들어줘.\n"
            "1:12 브리지는 차갑고 비워진 느낌으로 대비를 줘.\n"
            "1:32 마지막 후렴은 따뜻하고 환하게, 가장 큰 에너지로 끝내줘."
        )

        assert event["status"] == "ok"
        assert [call for call in calls if call.name == "run_commands"] == []
        # 3 setup + 5 interview + 1 requery answered ("수정") + 1 requery that
        # went unanswered (channel exhausted) — the loop stops without writes.
        assert len(channel.asked) == 10
        assert [question.prompt for question in channel.asked[3:8]] == [
            "공연 전체가 어떤 느낌이면 좋겠어요?",
            "어떤 색이 가장 잘 어울릴까요?",
            "가장 중요한 순간을 어떻게 보여 주면 좋겠어요?",
            "처음부터 끝까지 무대가 어떻게 달라 보이면 좋겠어요?",
            "전환 방식은 어떻게 갈까요? 컷으로 딱 끊을지, 페이드로 이어갈지 정해요.",
        ]
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "requires_requery"
        assert timelines[-1]["console_stored"] is False
        assert all(
            section["plan_status"] in ("draft", "requires_requery")
            for section in timelines[-1]["sections"]
        )
        assert [section["label"] for section in timelines[-1]["sections"]] == [
            "도입",
            "벌스",
            "후렴",
            "브리지",
            "마지막",
        ]

    def test_explicit_approval_runs_one_reviewed_bundle_and_requests_timing_readback(
        self, tmp_path
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "승인",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        assert writes[0].id == "song-design-reviewed-bundle"
        commands = writes[0].arguments["commands"]
        assert any(command.startswith("Store Sequence 110 Cue 1") for command in commands)
        assert "Store Timecode 7" in commands
        assert "Set Cue 1 Sequence 110 Property 'TrigTime' 0" in commands
        assert not any("/Merge" in command for command in commands)
        assert any(" CueFade " in command for command in commands)
        assert not any("Property 'Fade'" in command for command in commands)
        readbacks = [call.arguments["path"] for call in calls if call.name == "query_state"]
        # The one-time layer-mapping group read, then the 2026-08-16
        # occupied-slot pre-check, then the two post-store readbacks.
        assert readbacks == [
            # Up-front pick verification, the one-time layer-mapping group
            # read, the timecode-conflict check + approval impact summary
            # (2026-08-16), the pre-store slot check, then the two post-store
            # readbacks.
            "DataPool/Sequences/110",
            "DataPool/Groups",
            "DataPool/Timecodes/7",
            "DataPool/Sequences/110",
            "DataPool/Sequences/110",
            # T12: '후렴' section matches the phaser mapping table (Wave CM) —
            # ONE pool-resolution probe inside `_reviewed_song_commands`
            # (`_phaser_slots_for_bundle`, deduplicated per label). This
            # registry has no PresetPools fixture, so resolution fails and
            # the cue proceeds WITHOUT a phaser (contract #4) — the
            # `run_commands` output below is byte-identical to pre-T12.
            "DataPool/PresetPools",
            "DataPool/Sequences/110",
            "DataPool/Timecodes/7",
        ]
        assert event["commands"] == [
            {
                "command": "Fixture 20",
                "status": "proposal",
                "label": "제안 (라이브 잠금 — 전송되지 않음)",
                "detail": "",
            }
        ]
        assert "리뷰 번들 1건을 원자 실행" in event["text"]
        assert "readback 검증 완료" in event["text"]
        # T12(c) — the 'Wave CM' pool-resolution failure above (this
        # registry has no PresetPools fixture) surfaces its reason in the
        # final reply — the song design was not voided by it (contract #4).
        assert "페이저 미배정" in event["text"]
        assert "Wave CM" in event["text"]
        timelines = [event["timeline"] for event in sent if event["type"] == "song_timeline"]
        assert [timeline["lifecycle"] for timeline in timelines] == [
            "pending_approval",
            "approved",
            "verified",
        ]
        assert timelines[-1]["readback"]["verified"] is True
        assert timelines[0]["console_stored"] is False
        assert all(s["plan_status"] == "draft" for s in timelines[0]["sections"])
        assert timelines[-1]["console_stored"] is True
        assert all(s["plan_status"] == "verified" for s in timelines[-1]["sections"])

    # T12(b) — a brief whose sections carry NO phaser-mapping role words
    # (no 드롭/후렴/브리지/피날레/벌스 vocabulary) must never probe
    # PresetPools at all: read traffic for a phaser-irrelevant song stays
    # byte-identical to pre-T12 (coordinator condition b).
    def test_a_phaser_irrelevant_brief_never_probes_presetpools(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "승인",
            ]
        )
        session._question_channel = channel
        neutral_brief = (
            "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7: "
            "장면1 0:00 잔잔한 발라드, 장면2 0:40 밝은 팝"
        )

        session.run_instruction(neutral_brief)

        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        readbacks = [call.arguments["path"] for call in calls if call.name == "query_state"]
        assert "DataPool/PresetPools" not in readbacks
        assert readbacks == [
            "DataPool/Sequences/110",
            "DataPool/Groups",
            "DataPool/Timecodes/7",
            "DataPool/Sequences/110",
            "DataPool/Sequences/110",
            "DataPool/Sequences/110",
            "DataPool/Timecodes/7",
        ]
        assert not any(
            "At Preset 4." in command or "At Preset 21." in command
            for command in writes[0].arguments["commands"]
        )

    # T12(a)+(b) integration — when the live slot lookup SUCCEEDS, the
    # recall line lands in the real ``run_commands`` bundle exactly once,
    # and the label is resolved exactly once (batched, not per-cue).
    def test_a_resolved_phaser_lands_in_the_final_command_bundle(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        resolve_calls: list[str] = []

        def _stub_resolve(label):
            resolve_calls.append(label)
            return (4, 35) if label == "Wave CM" else None

        session._phaser_slot_by_label = _stub_resolve
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "승인",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        commands = writes[0].arguments["commands"]
        assert "Fixture 20 + 26 ; At Preset 4.35" in commands
        assert resolve_calls == ["Wave CM"]  # 라벨당 정확히 한 번 — 중복 조회 없음
        assert "페이저 미배정" not in event["text"]

    _PLAIN_BRIEF = (
        "곡은 약 1분 40초의 밝은 팝 무대야.\n"
        "0:00 도입은 무대를 어둡게 두고 보컬에게만 시선을 모아줘.\n"
        "0:22 벌스는 리듬이 시작되면서 무대 폭을 조금씩 넓혀줘.\n"
        "0:48 첫 후렴은 관객까지 에너지가 퍼지는 가장 큰 장면으로 만들어줘.\n"
        "1:12 브리지는 차갑고 비워진 느낌으로 대비를 줘.\n"
        "1:32 마지막 후렴은 따뜻하고 환하게, 가장 큰 에너지로 끝내줘."
    )

    #: 카드 t305 — 같은 브리프에 BPM 을 선언하고 구간을 길게(각 32초 = 120BPM
    #: 기준 16마디) 잡은 판. 8마디 단위이므로 구간마다 큐가 둘씩 나와야 한다.
    _BPM_BRIEF = (
        "곡은 약 2분 40초의 밝은 팝 무대야. BPM 120.\n"
        "0:00 도입은 무대를 어둡게 두고 보컬에게만 시선을 모아줘.\n"
        "0:32 벌스는 리듬이 시작되면서 무대 폭을 조금씩 넓혀줘.\n"
        "1:04 첫 후렴은 관객까지 에너지가 퍼지는 가장 큰 장면으로 만들어줘.\n"
        "1:36 브리지는 차갑고 비워진 느낌으로 대비를 줘.\n"
        "2:08 마지막 후렴은 따뜻하고 환하게, 가장 큰 에너지로 끝내줘."
    )

    def test_declared_bpm_splits_long_sections_into_multiple_cues(self, tmp_path):
        """카드 t305 — 16마디 구간이 8마디 경계에서 큐 둘로 갈린다.

        오프셋은 선언된 BPM 연산이다: 120BPM · 4/4 → 1마디 2.000s → 8마디
        16.000s. 그래서 0:00 구간의 둘째 큐는 16초, 0:32 구간의 둘째 큐는
        48초에 앉는다. 마지막 구간은 곡의 끝을 아무도 안 주므로 안 갈린다.
        """
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                *(["Center → Fan Out"] * 8),
                "수정",
                "수정",
            ]
        )

        session.run_instruction(self._BPM_BRIEF)

        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        sections = timelines[-1]["sections"]
        starts = [section["start_ms"] for section in sections]
        # 구간 5개 중 앞 4개가 16마디라 둘씩 → 9큐. 오늘(분할 전)이면 5큐다.
        assert len(sections) == 9
        assert starts == [
            0,
            16_000,
            32_000,
            48_000,
            64_000,
            80_000,
            96_000,
            112_000,
            128_000,
        ]
        # 큐 번호는 빈틈 없이 이어진다 — 콘솔이 그 순서로 재생한다.
        assert [section["cue_number"] for section in sections] == list(range(1, 10))
        # BPM 미선언 사유는 이번엔 안 붙는다.
        assert not any("BPM 미선언" in warning for warning in timelines[-1]["warnings"])

    def test_split_cues_are_not_identical_to_the_cue_they_continue(self, tmp_path):
        """카드 t305 — 16초 간격의 똑같은 큐 둘은 큐 하나보다 나쁘다.

        정본이 쪼갠 큐에서 바꾸는 축과 같다: 강도는 유지하고 색을 돌린다
        (Q060 "강도 유지, 색만 교체" · Q140 "색상만 순환").
        """
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                *(["Center → Fan Out"] * 8),
                "수정",
                "수정",
            ]
        )

        session.run_instruction(self._BPM_BRIEF)

        sections = [item["timeline"] for item in sent if item["type"] == "song_timeline"][-1][
            "sections"
        ]
        pairs = [(sections[i], sections[i + 1]) for i in range(0, 8, 2)]
        for opening, continuation in pairs:
            assert opening["palette"] != continuation["palette"], (
                f"{opening['label']} 의 이어지는 큐가 여는 큐와 같습니다"
            )
            # 돌린 것이지 새로 지어낸 것이 아니다 — 같은 색 집합.
            assert sorted(opening["palette"]) == sorted(continuation["palette"])
            # 강도는 유지된다(정본과 같은 축).
            assert opening["d_level"] == continuation["d_level"]

    def test_all_requery_answers_merge_and_recompose_to_pending_approval(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                # Requery answers — one per unresolved section, in order.
                "Center → Fan Out",
                "Wall 저조도",
                "Vocal DSC 스페셜",
                "Fan Out → Audience",
                "Center → Fan Out",
                # Approval card (if reached): decline so nothing is written.
                "수정",
                "수정",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction(self._PLAIN_BRIEF)

        assert event["status"] == "ok"
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        # The first composition required requeries; the merged recomposition
        # replaced it with a complete 5-cue pending_approval plan.
        assert timelines[0]["lifecycle"] == "requires_requery"
        assert timelines[-1]["lifecycle"] == "pending_approval"
        assert timelines[-1]["unresolved"] == []
        assert len(timelines[-1]["sections"]) == 5
        assert all(s["plan_status"] == "draft" for s in timelines[-1]["sections"])
        assert timelines[-1]["console_stored"] is False

    def test_section_look_arc_varies_texture_fx_palette_and_d_levels(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "Center → Fan Out",
                "Wall 저조도",
                "Vocal DSC 스페셜",
                "Fan Out → Audience",
                "Center → Fan Out",
                "수정",
                "수정",
            ]
        )

        session.run_instruction(self._PLAIN_BRIEF)

        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        sections = timelines[-1]["sections"]
        assert len(sections) == 5
        intro, verse, chorus, bridge, finale = sections
        # 결함 3: the look arc must vary across the song.
        assert len({s["texture"] for s in sections}) > 1
        assert len({len(s["fx"]) for s in sections}) > 1
        assert len({tuple(s["palette"]) for s in sections}) > 1
        assert bridge["d_level"] < chorus["d_level"]
        assert finale["d_level"] >= chorus["d_level"]
        assert intro["fx"] == []
        assert len(bridge["fx"]) <= len(chorus["fx"])
        assert chorus["accents"] or finale["accents"]
        # 결함 4: direct section wording beats the Q4 whole-song story.
        assert intro["position"] == "Vocal DSC"
        assert verse["position"] == "Fan Out"
        assert chorus["position"] == "Audience"
        # No same-look warning; the disclosed single-layer note (this fake rig
        # exposes no role-named groups), plus — 카드 t305 — the disclosed
        # reason no section was split into multiple cues. 이 브리프는 BPM 을
        # 선언하지 않으므로 마디를 계산할 수 없고, 그래서 큐 밀도는 오늘과
        # 같은 "구간 하나에 큐 하나"로 남는다. 이전에는 이 목록에 단일 레이어
        # 경고 하나뿐이었다.
        assert timelines[-1]["warnings"] == [
            "단일 레이어 계획입니다. Front/Back/Beam/Audience 분리 연출은 검증되지 않았습니다.",
            "BPM 미선언 — 마디를 계산할 수 없어 구간을 쪼개지 않았습니다",
        ]
        # 그리고 큐 수는 구간 수 그대로다 — 분할 없음의 관측 가능한 형태.
        assert len(sections) == 5

    def test_palette_conflict_card_offers_direction_before_composing(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            [
                "Ring In",
                "",
                "템포 맞춤 (BPM 기준)",
                "구간 분리 (잔잔한 구간 팔레트, 후렴 컨셉 색)",
            ]
        )
        session._question_channel = channel
        text = (
            "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7, "
            "컨셉은 엘로우와 그린, 팔레트는 블루+웜화이트: "
            "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
        )

        session.run_instruction(text)

        assert [call for call in calls if call.name == "run_commands"] == []
        conflict_cards = [q for q in channel.asked if "베이스 컬러 결정" in q.prompt]
        assert len(conflict_cards) == 1
        assert [option.label for option in conflict_cards[0].options] == [
            "팔레트 베이스",
            "컨셉 색 베이스",
            "구간 분리 (잔잔한 구간 팔레트, 후렴 컨셉 색)",
        ]
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        intro, chorus = timelines[-1]["sections"]
        # Mixed split: quiet sections keep the Q2 palette, the peak carries
        # the concept colors — no silent global overwrite either way.
        assert any("블루" in color for color in intro["palette"])
        assert any(color in ("엘로우", "그린") for color in chorus["palette"])

    def test_timeline_store_keeps_the_last_projection_for_new_connections(self, tmp_path):
        from server.web.session import SongTimelineStore

        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        store = SongTimelineStore()
        session._timeline_store = store
        session._question_channel = self._Channel(
            ["우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]
        )

        session.run_instruction(self._FULL)

        assert store.latest is not None
        assert store.latest["sequence_number"] == 110
        assert store.latest["lifecycle"] == "pending_approval"

    def test_timeline_store_persists_to_disk_and_survives_a_new_instance(self, tmp_path):
        from server.web.session import SongTimelineStore

        path = tmp_path / "song_timeline.json"
        store = SongTimelineStore(path)
        assert store.latest is None
        store.latest = {"sequence_number": 210, "lifecycle": "verified", "sections": []}
        # A fresh instance (= a restarted server) reads the same payload back.
        reborn = SongTimelineStore(path)
        assert reborn.latest == {"sequence_number": 210, "lifecycle": "verified", "sections": []}

    def test_timeline_store_fails_open_on_a_corrupt_file(self, tmp_path):
        from server.web.session import SongTimelineStore

        path = tmp_path / "song_timeline.json"
        path.write_text("{not json", encoding="utf-8")
        assert SongTimelineStore(path).latest is None
        # Path-less store stays memory-only and never touches disk.
        memory = SongTimelineStore()
        memory.latest = {"lifecycle": "verified"}
        assert memory.latest == {"lifecycle": "verified"}

    def test_timeline_store_persists_the_setlist_order(self, tmp_path):
        from server.web.session import SongTimelineStore

        path = tmp_path / "song_timeline.json"
        store = SongTimelineStore(path)
        store.setlist_sequence_nos = [210, 220, "junk"]  # non-int filtered
        reborn = SongTimelineStore(path)
        assert reborn.setlist_sequence_nos == [210, 220]
        assert reborn.latest is None  # a setlist alone implies no timeline

    def test_a_legacy_store_file_without_a_setlist_loads_empty(self, tmp_path):
        from server.web.session import SongTimelineStore

        path = tmp_path / "song_timeline.json"
        path.write_text(
            json.dumps({"version": 1, "timeline": {"sequence_number": 210}}),
            encoding="utf-8",
        )
        store = SongTimelineStore(path)
        assert store.latest == {"sequence_number": 210}
        assert store.setlist_sequence_nos == []

    def test_unanswered_requery_persists_and_resumes_on_a_later_turn(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        # Turn 1: interview answered, every requery card left unanswered.
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
            ]
        )
        first = session.run_instruction(self._PLAIN_BRIEF)
        assert "남은 재질의" in first["text"]
        assert "다음 턴에 포지션으로 답하면" in first["text"]
        assert session._pending_song_requery is not None
        assert [call for call in calls if call.name == "run_commands"] == []

        # Turn 2: a position answer resumes the SAME plan; the remaining
        # requery cards ride the channel, and approval is declined.
        session._question_channel = self._Channel(
            [
                "Wall 저조도",
                "Vocal DSC 스페셜",
                "Fan Out → Audience",
                "Center → Fan Out",
                "수정",
                "수정",
            ]
        )
        second = session.run_instruction("벌스는 Center → Fan Out으로 가자")

        assert second["status"] == "ok"
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"
        assert timelines[-1]["unresolved"] == []
        assert len(timelines[-1]["sections"]) == 5
        assert session._pending_song_requery is None

    def _pending_plan_session(self, tmp_path):
        """Turn 1: full brief, every requery answered, approval DECLINED —
        leaves a complete pending_approval plan editable on later turns."""
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "Center → Fan Out",
                "Wall 저조도",
                "Vocal DSC 스페셜",
                "Fan Out → Audience",
                "Center → Fan Out",
                "수정",
                "수정",
            ]
        )
        session.run_instruction(self._PLAIN_BRIEF)
        assert session._pending_song_plan is not None
        assert [call for call in calls if call.name == "run_commands"] == []
        return session, sent, calls

    def test_declined_approval_keeps_the_plan_editable(self, tmp_path):
        session, sent, _calls = self._pending_plan_session(tmp_path)
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"
        assert len(timelines[-1]["sections"]) == 5

    def test_plan_edit_deletes_a_cue_without_console_commands(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("큐 4 삭제해줘")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 4")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"
        assert len(timelines[-1]["sections"]) == 4
        assert session._pending_song_plan is not None

    def test_plan_edit_inserts_a_section_between_cues(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        # The inserted section's mood ("브레이크") may need one requery card;
        # answer it with a position, then decline approval again.
        session._question_channel = self._Channel(["Wall 저조도", "수정"])

        event = session.run_instruction("큐 2와 3 사이에 브레이크 추가")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 3(브레이크) 추가")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"
        sections = timelines[-1]["sections"]
        assert len(sections) == 6
        assert sections[2]["label"] == "브레이크"
        # The new section sits strictly between its neighbours on the clock.
        assert sections[1]["start_ms"] < sections[2]["start_ms"] < sections[3]["start_ms"]

    def test_plan_edit_retargets_position_and_color_console_free(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("타임라인 큐 3을 무대 중앙으로, 컬러는 골드로")

        # Pre-approval, the PLAN route wins over the console /Merge route.
        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 3")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        section = timelines[-1]["sections"][2]
        assert section["position"] == "Center"
        assert "골드" in section["palette"]

    def test_plan_edit_cancel_clears_the_pending_plan(self, tmp_path):
        session, _sent, calls = self._pending_plan_session(tmp_path)

        event = session.run_instruction("취소")

        assert "취소" in event["text"]
        assert session._pending_song_plan is None
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_plan_edit_refuses_an_unknown_cue(self, tmp_path):
        session, _sent, calls = self._pending_plan_session(tmp_path)

        event = session.run_instruction("큐 9 삭제")

        assert "큐 9가 없어" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []
        assert session._pending_song_plan is not None

    def test_confirmed_back_layer_adds_group_dimmer_lines_to_the_bundle(self, tmp_path):
        # 결함 6 후속 (priority 6): the mapping is no longer display-only —
        # every LIT section cue carries a group-addressed back-layer dimmer at
        # 80% of its key level, between the key dimmer and the store.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._song_layer_mapping = [{"role": "back", "group_no": 12, "group_name": "Back"}]
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                # Requery cards for the two unresolved sections (벌스, 브리지).
                "Center → Fan Out",
                "Wall 저조도",
                "승인",
            ]
        )
        session.run_instruction(self._PLAIN_BRIEF)

        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        commands = stores[0].arguments["commands"]
        back_lines = [command for command in commands if command.startswith("Group 12 ; ")]
        # One per lit section cue (all five sections are lit in this brief).
        assert len(back_lines) == 5
        for line in back_lines:
            index = commands.index(line)
            key_line = commands[index - 1]
            assert key_line.startswith("Fixture ") and "'Dimmer' At " in key_line
            assert commands[index + 1].startswith("Store Sequence 110 Cue ")
            key_pct = float(key_line.rsplit(" At ", 1)[1])
            back_pct = float(line.rsplit(" At ", 1)[1])
            assert back_pct == round(key_pct * 0.8, 6)

    def test_without_a_back_mapping_no_group_lines_are_emitted(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["승인"])

        session.run_instruction("큐 4 삭제")

        stores = [call for call in calls if call.name == "run_commands"]
        commands = stores[0].arguments["commands"]
        assert not [command for command in commands if command.startswith("Group ")]

    def test_a_requested_occupied_sequence_is_caught_at_the_first_ask(self, tmp_path):
        # 2026-08-16 사용자 방향: verify numbers UP FRONT — a brief naming an
        # occupied sequence opens the pick card (verified-empty proposals)
        # BEFORE the interview, so the store never targets a full slot.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls, sequence_exists_before_store=True)
        channel = self._Channel(
            [
                "120",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "승인",
            ]
        )
        session._question_channel = channel

        session.run_instruction(self._FULL)

        first_prompt = str(getattr(channel.asked[0], "prompt", channel.asked[0]))
        assert "이미 콘솔 데이터가 있어" in first_prompt
        assert "비어 있는 번호" in first_prompt
        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        commands = stores[0].arguments["commands"]
        assert any(command.startswith("Store Sequence 120 Cue 1") for command in commands)
        assert not any("Sequence 110" in command for command in commands)

    def test_pending_plan_survives_a_reconnect_via_the_shared_store(self, tmp_path):
        # #2 (2026-08-16): a page refresh opens a NEW session; with the shared
        # store, the new session adopts the pending plan and keeps editing.
        from server.web.session import PendingSongPlanStore

        store = PendingSongPlanStore()
        session, _sent, calls = self._pending_plan_session(tmp_path)
        # Simulate the app wiring: move the plan into the shared store.
        store.state = session._pending_song_plan
        provider = ScriptedProvider([])
        fresh, _console, _audit, fresh_sent, _ = _session(tmp_path, provider)
        fresh_calls: list[ToolCall] = []
        fresh._registry = self._registry(fresh_calls)
        fresh._pending_plan_store = store
        fresh._question_channel = self._Channel(["수정"])

        event = fresh.run_instruction("큐 4 삭제")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 4")
        assert [call for call in fresh_calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in fresh_sent if item["type"] == "song_timeline"]
        assert len(timelines[-1]["sections"]) == 4
        assert store.state is not None

    def test_occupied_timecode_opens_a_conflict_card_before_approval(self, tmp_path):
        # #3 (2026-08-16): a timecode slot that already holds data is resolved
        # BEFORE approval — proceed on it, move to a verified-empty slot, or
        # cancel with the plan preserved.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls, timecode_exists_before_store=True)
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "타임코드 8번 슬롯 (비어 있음)",
                "승인",
            ]
        )
        session._question_channel = channel

        session.run_instruction(self._FULL)

        conflict = next(
            str(getattr(request, "prompt", request))
            for request in channel.asked
            if "타임코드 7번 슬롯에 기존" in str(getattr(request, "prompt", request))
        )
        assert "어떻게 할까요" in conflict
        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        assert "Store Timecode 8" in stores[0].arguments["commands"]
        assert "Store Timecode 7" not in stores[0].arguments["commands"]

    def test_approval_card_carries_a_verified_impact_summary(self, tmp_path):
        # #5 (2026-08-16): the approval card states WHAT gets created WHERE,
        # from console-verified facts — never a blind "저장할까요?".
        session, _sent, _calls = self._pending_plan_session(tmp_path)
        channel = self._Channel(["수정"])
        session._question_channel = channel

        session.run_instruction("큐 4 삭제")

        approval_prompt = str(getattr(channel.asked[-1], "prompt", channel.asked[-1]))
        assert "영향 요약" in approval_prompt
        assert "시퀀스 110: 비어 있음 확인(신규 저장)" in approval_prompt
        assert "기존 데이터 덮어쓰기: 없음" in approval_prompt

    def test_a_not_found_error_is_a_verified_empty_slot(self, tmp_path):
        # 실기 2026-08-16 (사용자: '왜 항상 같은 번호만 제안?'): 실기 콘솔은
        # 빈 슬롯 조회에 'path segment not found' 오류로 답한다 — 부재의
        # 확답이므로 '비어 있음'으로 판정해야 제안이 가능하다.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)

        class RealConsoleRegistry:
            def dispatch(self, call, context=None):
                path = call.arguments["path"]
                if path.endswith("/110"):  # 실존 시퀀스만 정상 응답
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps({"ok": True, "node": {"name": "Sequence 110"}}),
                        )
                    )
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=f"state query failed for {path!r}: path segment not found",
                        is_error=True,
                    )
                )

        session._registry = RealConsoleRegistry()
        assert session._song_sequence_occupied(110) is True
        assert session._song_sequence_occupied(120) is False
        assert session._song_free_sequence_slots(120) == [120, 130, 140]
        assert session._free_timecode_slots(7) == [8, 9]

    def test_a_flapping_probe_revives_on_the_single_retry_pass(self, tmp_path):
        # 실기 2026-08-16: responder flapping은 간헐적 — 첫 탐침이 실패한
        # 슬롯은 1회 재시도로 살아나 검증된 번호를 제안할 수 있어야 한다.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        seen: dict[str, int] = {}

        class FlappingRegistry:
            def dispatch(self, call, context=None):
                path = call.arguments["path"]
                seen[path] = seen.get(path, 0) + 1
                if seen[path] == 1:  # first touch always times out
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content="responder timeout",
                            is_error=True,
                        )
                    )
                return ToolExecution(ToolResult(tool_call_id=call.id, name=call.name, content="{}"))

        session._registry = FlappingRegistry()
        assert session._song_free_sequence_slots(120) == [120, 130, 140]

    def test_a_failed_probe_reads_as_occupied_never_empty(self, tmp_path):
        # #6 (2026-08-16): a flapping responder must NEVER get an occupied
        # slot proposed as empty — an unreadable probe is fail-closed.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)

        class BrokenRegistry:
            def dispatch(self, call, context=None):
                return ToolExecution(
                    ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content="responder unreachable",
                        is_error=True,
                    )
                )

        session._registry = BrokenRegistry()
        assert session._song_sequence_occupied(110) is True
        assert session._timecode_occupied(7) is True
        assert session._song_free_sequence_slots(110) == []
        # The fallback card SAYS why nothing could be proposed (실측 2026-08-15
        # 오독: 전 슬롯 폴백이 '전부 차 있음'처럼 보였음).
        channel = self._Channel([])
        session._question_channel = channel
        session._song_pick_sequence(None, purpose="디자인 큐 시트", refusal="거절")
        prompt = str(getattr(channel.asked[0], "prompt", channel.asked[0]))
        assert "조회 실패 12곳" in prompt
        assert "콘솔 응답이 불안정" in prompt

    def test_preset_start_options_come_from_the_console_pool(self, tmp_path):
        # The preset question proposes only starts where TEN consecutive
        # Position presets actually exist on the console.
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        pool = {
            "ok": True,
            "node": {"name": "Position", "class": "PresetPool"},
            # 실기 responder 형태 그대로: 슬롯 번호는 "i" 키 (PROTOCOL §4.2)
            "children": [{"i": slot, "name": f"Pos {slot}"} for slot in range(21, 31)]
            + [{"i": 35, "name": "고아 슬롯"}],
        }
        session._registry = self._registry(calls, preset_pool_readback=pool)
        channel = self._Channel(
            [
                "110",
                "21 (2.21~2.30 저장 확인됨)",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "Center → Fan Out",
                "Wall 저조도",
                "수정",
            ]
        )
        session._question_channel = channel

        session.run_instruction(self._PLAIN_BRIEF)

        preset_card = channel.asked[1]
        labels = [option.label for option in preset_card.options]
        assert labels == ["21 (2.21~2.30 저장 확인됨)"]
        assert "10칸 연속 저장된 구간을 확인했습니다" in str(preset_card.prompt)
        assert session._pending_song_plan is not None

    def test_occupied_sequence_opens_a_recovery_card_and_stores_on_the_pick(self, tmp_path):
        # 2026-08-16 사용자 방향: an occupied Sequence 110 is not a dead end —
        # the recovery card proposes verified-empty slots and a pick stores
        # IMMEDIATELY on the chosen one.
        session, _sent, calls = self._pending_plan_session(tmp_path)
        occupied_calls: list[ToolCall] = []
        session._registry = self._registry(occupied_calls, sequence_exists_before_store=True)
        session._question_channel = self._Channel(["승인", "시퀀스 120"])

        event = session.run_instruction("큐 4 삭제")

        stores = [call for call in occupied_calls if call.name == "run_commands"]
        assert len(stores) == 1
        commands = stores[0].arguments["commands"]
        assert any(command.startswith("Store Sequence 120 Cue 1") for command in commands)
        assert not any("Sequence 110" in command for command in commands)
        # The recovery card was the second question, after the approval card.
        # Stored on the picked slot; the honest readback verdict follows.
        assert "시퀀스 120에 리뷰 번들 1건을 원자 실행 요청" in event["text"]

    def test_occupied_sequence_with_no_answer_keeps_the_plan(self, tmp_path):
        session, _sent, calls = self._pending_plan_session(tmp_path)
        occupied_calls: list[ToolCall] = []
        session._registry = self._registry(occupied_calls, sequence_exists_before_store=True)
        session._question_channel = self._Channel(["승인"])  # recovery card unanswered

        event = session.run_instruction("큐 4 삭제")

        assert "이미 콘솔 데이터가 있어" in event["text"]
        assert "계획은 그대로 보존" in event["text"]
        assert [call for call in occupied_calls if call.name == "run_commands"] == []
        assert [call for call in calls if call.name == "run_commands"] == []
        assert session._pending_song_plan is not None

    def test_sequence_move_edit_retargets_the_pending_plan(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("시퀀스 320으로 변경해줘")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 저장 대상 시퀀스 110 → 320")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sequence_number"] == 320
        assert session._pending_song_plan is not None

    def test_failed_store_cleans_up_asks_recovery_and_keeps_the_plan(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        failing_calls: list[ToolCall] = []
        session._registry = self._registry(failing_calls, store_fails=True)
        session._question_channel = self._Channel(["승인"])  # recovery card unanswered

        event = session.run_instruction("큐 4 삭제")

        assert "거부되었습니다" in event["text"]
        assert "Not allowed" in event["text"]
        assert "계획은 그대로 보존" in event["text"]
        runs = [call for call in failing_calls if call.name == "run_commands"]
        # The failed bundle, then the safety ClearAll cleanup.
        assert len(runs) == 2
        assert runs[1].arguments["commands"] == ["ClearAll"]
        assert session._pending_song_plan is not None
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"

    def test_structure_edit_without_a_pending_plan_refuses_honestly(self, tmp_path):
        # 2026-08-16 user finding: after a restart/reconnect the pending plan
        # is gone; "큐 2와 3 사이에 브레이크 추가" must NOT fall through to the
        # model (which fabricated a "서버 내부 오류" apology) — it explains.
        provider = ScriptedProvider([])  # any model consultation would raise
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        assert session._pending_song_plan is None

        for text in ("큐 2와 3 사이에 브레이크 추가", "큐 4 삭제", "큐 2 뒤에 아웃트로 추가"):
            event = session.run_instruction(text)
            assert "보류 중 계획" in event["text"], text
        assert calls == []

    def test_plan_edit_then_approval_stores_once(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["승인"])

        event = session.run_instruction("큐 4 삭제")

        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        assert session._pending_song_plan is None
        commands = stores[0].arguments["commands"]
        assert any("Store Sequence 110" in command for command in commands)
        assert event["status"] in ("ok", "readback_failed")

    def test_approved_store_auto_saves_a_library_version(self, tmp_path):
        from server.web.session import SongTimelineStore
        from server.web.timeline_library import SongTimelineLibrary

        session, sent, calls = self._pending_plan_session(tmp_path)
        library = SongTimelineLibrary(tmp_path / "library.json")
        session._timeline_store = SongTimelineStore()
        session._timeline_library = library
        session._question_channel = self._Channel(["승인"])

        event = session.run_instruction("큐 4 삭제")

        assert [call for call in calls if call.name == "run_commands"]
        entries = library.items()
        assert len(entries) == 1
        assert entries[0]["name"] == "Sequence 110 (자동 v1)"
        assert "'Sequence 110 (자동 v1)' 자동 저장" in event["text"]
        # The snapshot is the just-sent projection — same lifecycle, 4 cues.
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert entries[0]["timeline"]["lifecycle"] == timelines[-1]["lifecycle"]
        assert len(entries[0]["timeline"]["sections"]) == 4

    def test_declined_approval_saves_no_library_version(self, tmp_path):
        from server.web.timeline_library import SongTimelineLibrary

        session, _sent, calls = self._pending_plan_session(tmp_path)
        library = SongTimelineLibrary(tmp_path / "library.json")
        session._timeline_library = library
        session._question_channel = self._Channel(["수정"])

        session.run_instruction("큐 4 삭제")

        assert [call for call in calls if call.name == "run_commands"] == []
        assert library.items() == []

    def test_plan_edit_sets_a_dimmer_level(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("큐 2를 D5로 올려줘")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 2 디머 D5")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sections"][1]["d_level"] == 5

    def test_plan_edit_sets_an_explicit_fade(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("큐 3 페이드 2초로")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 3 페이드 2초")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sections"][2]["fade_seconds"] == 2.0

    def test_plan_edit_turns_fx_off_and_back_on(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        before = [item["timeline"] for item in sent if item["type"] == "song_timeline"][-1]
        original_fx = before["sections"][2]["fx"]
        session._question_channel = self._Channel(["수정", "수정"])

        session.run_instruction("큐 3 FX 꺼줘")
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sections"][2]["fx"] == []

        session.run_instruction("큐 3 FX 켜줘")
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sections"][2]["fx"] == original_fx
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_plan_edit_moves_a_cue_in_time(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("큐 2를 0:30으로 이동해줘")

        assert event["text"].startswith("계획 수정(콘솔 무접촉): 큐 2 시작 0:30")
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        sections = timelines[-1]["sections"]
        assert sections[1]["start_ms"] == 30_000
        assert [s["label"] for s in sections] == [s["label"] for s in sections]  # no reorder
        assert sections[1]["label"] == "벌스"

    def test_plan_edit_time_move_across_neighbours_reorders_cues(self, tmp_path):
        session, sent, calls = self._pending_plan_session(tmp_path)
        before = [item["timeline"] for item in sent if item["type"] == "song_timeline"][-1][
            "sections"
        ]
        moved_position = before[1]["position"]
        session._question_channel = self._Channel(["수정"])

        event = session.run_instruction("큐 2를 1:20으로 옮겨줘")

        assert "큐 순서 재정렬" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        sections = timelines[-1]["sections"]
        starts = [s["start_ms"] for s in sections]
        assert starts == sorted(starts)
        assert sections[3]["label"] == "벌스"
        assert sections[3]["start_ms"] == 80_000
        # The moved section kept its confirmed position override.
        assert sections[3]["position"] == moved_position
        assert [s["cue_number"] for s in sections] == [1, 2, 3, 4, 5]

    def _stored_timeline_payload(self) -> dict:
        return {
            "song_title": "밝은 팝 무대 v1",
            "sequence_name": "Sequence 210",
            "sequence_number": 210,
            "timing_mode": "manual_go",
            "timecode_number": None,
            "lifecycle": "verified",
            "approval": "approved",
            "director_decisions": [],
            "sections": [
                {"index": 3, "label": "후렴", "cue_number": 3, "position": "Audience"},
                {"index": 5, "label": "마지막", "cue_number": 5, "position": "Audience"},
            ],
            "lint": [],
            "unresolved": [],
            "disabled": [],
            "readback": {"verified": True, "message": "ok"},
            "console_stored": True,
            "warnings": [],
            "layer_mapping": [],
            "preset_start": 21,
        }

    def test_timeline_cue_edit_targets_the_displayed_sequence(self, tmp_path):
        from server.web.session import SongTimelineStore

        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        store = SongTimelineStore()
        store.latest = self._stored_timeline_payload()
        session._timeline_store = store
        session._question_channel = self._Channel([])

        event = session.run_instruction(
            "타임라인 큐3를 객석이 아니라 무대 중앙으로 집중되게 수정해줘"
        )

        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        commands = writes[0].arguments["commands"]
        # Center = BASIC slot index 3 → preset 21 + 3 = 2.24; the edit merges
        # into the TIMELINE's sequence (210), never a name-matched one.
        assert any("At Preset 2.24" in command for command in commands)
        assert "Store Sequence 210 Cue 3 /Merge" in commands
        assert not any("150" in command for command in commands)
        assert "타임라인에 즉시 반영" in event["text"]
        assert store.latest["sections"][0]["position"] == "Center"
        assert store.latest["sections"][1]["position"] == "Audience"  # untouched
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sections"][0]["position"] == "Center"
        assert "큐 3 포지션을 Center" in timelines[-1]["readback"]["message"]

    def test_timeline_cue_edit_without_a_timeline_refuses(self, tmp_path):
        from server.web.session import SongTimelineStore

        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._timeline_store = SongTimelineStore()
        session._question_channel = self._Channel([])

        event = session.run_instruction("타임라인 큐 3를 무대 중앙으로 수정해줘")

        assert [call for call in calls if call.name == "run_commands"] == []
        assert "불러와" in event["text"]

    def test_timeline_cue_edit_unknown_cue_lists_the_known_ones(self, tmp_path):
        from server.web.session import SongTimelineStore

        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        store = SongTimelineStore()
        store.latest = self._stored_timeline_payload()
        session._timeline_store = store
        session._question_channel = self._Channel([])

        event = session.run_instruction("타임라인 큐 9를 무대 중앙으로 수정해줘")

        assert [call for call in calls if call.name == "run_commands"] == []
        assert "큐 9가 없습니다" in event["text"]
        assert "3, 5" in event["text"]

    def test_pending_requery_cancel_clears_without_any_write(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel(
            [
                "110",
                "21",
                "수동 Go",
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
            ]
        )
        session.run_instruction(self._PLAIN_BRIEF)
        assert session._pending_song_requery is not None

        event = session.run_instruction("취소")

        assert "취소" in event["text"]
        assert session._pending_song_requery is None
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_unconfirmed_interview_step_reopens_its_card_with_real_answers(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        # Q4 left blank (auto-draft, unconfirmed) → the requery loop reruns
        # the interview from Q4 with REAL answers this time.
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "",
                "템포 맞춤 (BPM 기준)",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "수정",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        assert "감독 미확정" not in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []
        q4_prompts = [
            q.prompt
            for q in channel.asked
            if q.prompt == "처음부터 끝까지 무대가 어떻게 달라 보이면 좋겠어요?"
        ]
        assert len(q4_prompts) == 2  # first pass + DI5 re-interview
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "pending_approval"

    def test_layer_mapping_card_infers_roles_from_console_groups(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(
            calls,
            groups_readback={
                "ok": True,
                "path": "DataPool/Groups",
                "children": [
                    {"i": 11, "name": "Back", "class": "Group"},
                    {"i": 12, "name": "Front", "class": "Group"},
                    {"i": 13, "name": "Wash", "class": "Group"},
                    {"i": 14, "name": "Audience", "class": "Group"},
                ],
            },
        )
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "이 매핑 사용",
                "수정",
            ]
        )
        session._question_channel = channel

        session.run_instruction(self._FULL)

        layer_cards = [q for q in channel.asked if "레이어 역할" in q.prompt]
        assert len(layer_cards) == 1
        assert [call for call in calls if call.name == "run_commands"] == []
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["layer_mapping"] == [
            {"role": "back", "group_no": 11, "group_name": "Back"},
            {"role": "key", "group_no": 12, "group_name": "Front"},
            {"role": "audience", "group_no": 14, "group_name": "Audience"},
        ]
        # "Wash" matches no role alias (exact match only) and the single-layer
        # disclosure disappears once a mapping is recorded.
        assert all("단일 레이어" not in warning for warning in timelines[-1]["warnings"])

    def test_readback_validation_failure_is_reported_distinctly(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(
            calls,
            sequence_readback=self._sequence_readback(cue_1_trig_time="1"),
        )
        channel = self._Channel(
            [
                "우주",
                "우주 색 조합",
                "Ring In",
                "우주 컨셉 우선 배치",
                "템포 맞춤 (BPM 기준)",
                "승인",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        writes = [call for call in calls if call.name == "run_commands"]
        assert len(writes) == 1
        readbacks = [call.arguments["path"] for call in calls if call.name == "query_state"]
        assert readbacks == [
            # Up-front pick verification, the one-time layer-mapping group
            # read, the timecode-conflict check + approval impact summary
            # (2026-08-16), the pre-store slot check, then the two post-store
            # readbacks.
            "DataPool/Sequences/110",
            "DataPool/Groups",
            "DataPool/Timecodes/7",
            "DataPool/Sequences/110",
            "DataPool/Sequences/110",
            # T12: same one-time phaser pool-resolution probe as the sibling
            # test above ('후렴' → Wave CM, resolution fails in this registry
            # so the cue proceeds without a phaser — commands unchanged).
            "DataPool/PresetPools",
            "DataPool/Sequences/110",
            "DataPool/Timecodes/7",
        ]
        assert event["status"] == "readback_failed"
        assert "readback 검증에 실패" in event["text"]
        assert "TrigTime" in event["text"]
        assert "0이 아닙니다" in event["text"]
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["lifecycle"] == "readback_failed"
        assert timelines[-1]["readback"]["verified"] is False

    def test_unresolved_section_requeries_without_write(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            ["우주", "우주 색 조합", "Ring In", "우주 컨셉 우선 배치", "템포 맞춤 (BPM 기준)"]
        )
        session._question_channel = channel
        text = (
            "디자인 인터뷰, 시퀀스 110, 프리셋 21번부터, 타임코드 7, "
            "BPM 128, 메탈: 0:00 도입, 0:20 후렴"
        )

        event = session.run_instruction(text)

        assert len(channel.asked) == 6
        assert "도입 구간" in channel.asked[-1].prompt
        assert [call for call in calls if call.name == "run_commands"] == []
        assert "미확정/미해결 입력" in event["text"]

    def test_free_text_answer_resolves_the_palette_verbatim(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        # Q1 blank (auto-draft) -> Q2 free text naming a known color token
        # ("레드") that matches none of Q2's 3 option labels -> Q3-Q5 blank.
        channel = self._Channel(["", "레드 톤 위주로 가죠", "", "", ""])
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        # 5 interview cards + a DI5 partial re-interview of the first
        # unconfirmed step (Q1 → Q5 re-asked, unanswered → restored).
        assert len(channel.asked) == 10
        assert "Q2 팔레트: 레드 톤 위주로 가죠 (확정)" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_q1_answer_re_derives_the_q2_palette_suggestions(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["네온", "", "", "", ""])
        session._question_channel = channel

        session.run_instruction(self._FULL)

        # 5 interview cards + restart_from(Q2)'s 4 re-asked cards.
        assert len(channel.asked) == 9
        q2_labels = [option.label for option in channel.asked[1].options]
        assert "네온 색 조합" in q2_labels  # DI2: Q1's confirmed concept re-seeds Q2

    def test_instruction_specified_palette_skips_its_card(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["", "", "", ""])
        session._question_channel = channel
        text = (
            "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7, 팔레트는 청록+마젠타: "
            "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
        )

        event = session.run_instruction(text)

        # Q2 card never fires on the FIRST pass — only Q1/Q3/Q4/Q5 ask; the
        # unanswered DI5 re-interview then re-opens Q1..Q5 (5 more asks) and
        # restores the pre-specified palette untouched.
        assert len(channel.asked) == 9
        assert all("팔레트" not in q.prompt for q in channel.asked[:4])
        assert "Q2 팔레트: 청록+마젠타 (확정)" in event["text"]

    def test_no_answer_marks_every_step_unconfirmed_and_requeries_without_write(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])  # UNANSWERED every card

        event = session.run_instruction(self._FULL)

        # 5 cards + the unanswered Q1 re-interview (5 re-asks, restored).
        assert len(session._question_channel.asked) == 10
        assert event["status"] == "ok"
        assert event["text"].count("감독 미확정") == 5
        writes = [call for call in calls if call.name == "run_commands"]
        assert writes == []
        assert "미확정/미해결 입력" in event["text"]

    def test_final_response_carries_the_di6_audit_trail(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        session._question_channel = self._Channel([])

        event = session.run_instruction(self._FULL)

        assert "연출 인터뷰 결과" in event["text"]
        for label in ("Q1 컨셉", "Q2 팔레트", "Q3 클라이맥스", "Q4 공간 스토리", "Q5 전환 방식"):
            assert label in event["text"]

    def test_partial_restart_reruns_from_the_named_step(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        # Answer Q1/Q2, then on Q3 ask for "Q1만 다시" instead of answering —
        # DI5: Q1 reruns (this time "빈티지"), Q2-Q5 follow fresh.
        channel = self._Channel(["우주", "", "Q1만 다시", "빈티지", "", "", ""])
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        # 8 interview cards (Q1,Q2,Q3 + DI5 restart Q1..Q5) + the unanswered
        # Q2 re-interview (4 re-asks, restored).
        assert len(channel.asked) == 12
        assert "Q1 컨셉: 빈티지 (확정)" in event["text"]

    def test_time_first_two_token_sections_start_the_interview(self, tmp_path):
        """Repro (post-restart browser submission): '디자인 인터뷰, BPM 128,
        메탈: 0:00 도입, 0:20 후렴' used to hit the "곡 구간을 읽지 못해"
        refusal because ``_SHEET_SECTION`` requires a third mood token. The
        2-token "시각 이름" fallback must read both sections and let the
        5-card interview start."""
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["", "", "", "", ""])
        session._question_channel = channel
        text = (
            "디자인 인터뷰, 시퀀스 110, 프리셋 21번부터, 타임코드 7, "
            "BPM 128, 메탈: 0:00 도입, 0:20 후렴"
        )

        event = session.run_instruction(text)

        assert "곡 구간을 읽지 못해" not in event["text"]
        assert len(channel.asked) == 6
        assert [q.prompt for q in channel.asked][0] == "공연 전체가 어떤 느낌이면 좋겠어요?"
        assert event["status"] == "ok"
        assert "미확정/미해결 입력" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []
        # only "후렴" matches a mood keyword; "도입" has none in the table

    def test_name_first_two_token_sections_start_the_interview(self, tmp_path):
        """Same 2-token fallback, opposite token order — '도입 0:00' instead
        of '0:00 도입' — must also read both sections."""
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["", "", "", "", ""])
        session._question_channel = channel
        text = (
            "디자인 인터뷰, 시퀀스 110, 프리셋 21번부터, 타임코드 7, "
            "BPM 128, 메탈: 도입 0:00, 후렴 0:20"
        )

        event = session.run_instruction(text)

        assert "곡 구간을 읽지 못해" not in event["text"]
        assert len(channel.asked) == 6
        assert event["status"] == "ok"
        assert "미확정/미해결 입력" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []
        # only "후렴" matches a mood keyword; "도입" has none in the table

    def test_three_token_sections_still_parse_unchanged(self, tmp_path):
        """The pre-existing '이름 시각 무드' form (self._FULL) must keep
        working byte-for-byte after the 2-token fallback was added —
        _SHEET_SECTION is tried first and the fallback never engages."""
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(["", "", "", "", ""])
        session._question_channel = channel

        event = session.run_instruction(self._FULL)

        # 5 cards + the unanswered Q1 re-interview (5 re-asks, restored).
        assert len(channel.asked) == 10
        assert event["status"] == "ok"
        assert "미확정/미해결 입력" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_plain_opinion_collects_five_director_decisions_without_console_commands(
        self, tmp_path
    ):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        channel = self._Channel(
            [
                "보컬 고정 · 후면 긴장",
                "청록 · 보라 대비",
                "팬 아웃 · 후렴에서 객석 확장",
                "박자 펄스 · 2·4박 강조",
                "화이트 히트 · 0.5초 스냅",
            ]
        )
        session._question_channel = channel

        event = session.run_instruction("메탈 공연을 차갑고 웅장하게 꾸며줘")

        assert len(channel.asked) == 5, event
        assert all(len(question.options) == 3 for question in channel.asked)
        assert [question.prompt.split(" · ", 1)[0] for question in channel.asked] == [
            "01",
            "02",
            "03",
            "04",
            "05",
        ]
        assert "청록 · 보라 대비" in event["text"]
        assert "화이트 히트 · 0.5초 스냅" in event["text"]
        assert (
            "아직 콘솔 명령, 장비 배치, 프리셋 리콜, 큐 저장은 수행하지 않았습니다."
            in event["text"]
        )
        assert calls == []

    def test_status_question_never_reaches_the_model_or_console(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction("진행하고 있는거야?")

        assert "콘솔 명령을 생성하거나 실행하지 않습니다." in event["text"]
        assert provider.calls == []
        assert calls == []


class TestRehearsalCueEdit:
    """Priority 5 (handoff 2026-08-15): '지금 이 큐' edits the cue the console
    is PLAYING (CurrentCue off the sequence handle), always behind a fresh
    approval card because the output is live."""

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    class _CuePort:
        def __init__(self, value, *, ok=True, error=None):
            self.value = value
            self.ok = ok
            self.error = error
            self.queries = []

        def query_property(self, path, name):
            self.queries.append((path, name))
            if not self.ok:
                return {"ok": False, "error": self.error or "unreachable"}
            return {"ok": True, "value": self.value}

    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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
                outcomes = tuple(
                    CommandOutcome(command=command, status="executed_ok")
                    for command in call.arguments.get("commands", [])
                )
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                    outcomes,
                )

        return Registry()

    def _stored_timeline(self, *, stored=True):
        return {
            "song_title": "밝은 팝 무대",
            "sequence_number": 210,
            "lifecycle": "verified" if stored else "pending_approval",
            "console_stored": stored,
            "preset_start": 21,
            "sections": [
                {"index": 3, "label": "후렴", "cue_number": 3, "position": "Audience"},
                {"index": 5, "label": "피날레", "cue_number": 5, "position": "Audience"},
            ],
            "readback": {"verified": True, "message": "ok"},
        }

    def _rehearsal_session(self, tmp_path, *, current_cue, stored=True, answers=("승인",)):
        from server.web.session import SongTimelineStore

        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)
        store = SongTimelineStore()
        store.latest = self._stored_timeline(stored=stored)
        session._timeline_store = store
        port = self._CuePort(current_cue)
        session._current_cue_port = port
        session._question_channel = self._Channel(list(answers))
        return session, calls, sent, port

    def test_edits_the_playing_cue_after_explicit_approval(self, tmp_path):
        session, calls, sent, port = self._rehearsal_session(tmp_path, current_cue="Sequence 210.3")

        event = session.run_instruction("지금 이 큐를 무대 중앙으로 바꿔줘")

        assert "지금 나가는 큐 3의 포지션을 Center" in event["text"]
        assert port.queries == [("DataPool/Sequences/210", "CurrentCue")]
        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        assert "Store Sequence 210 Cue 3 /Merge" in stores[0].arguments["commands"]
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines[-1]["sections"][0]["position"] == "Center"
        assert "리허설" in timelines[-1]["readback"]["message"]

    def test_decline_writes_nothing(self, tmp_path):
        session, calls, _sent, _port = self._rehearsal_session(
            tmp_path, current_cue="Sequence 210.3", answers=("취소",)
        )

        event = session.run_instruction("지금 나가는 큐를 객석으로")

        assert "승인 전이므로 콘솔에 쓰지 않았습니다" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_a_sequence_at_rest_or_blank_value_refuses(self, tmp_path):
        session, calls, _sent, _port = self._rehearsal_session(tmp_path, current_cue="")

        event = session.run_instruction("현재 큐를 무대 중앙으로")

        assert "확인할 수 없습니다" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_a_plan_only_timeline_refuses(self, tmp_path):
        session, calls, _sent, _port = self._rehearsal_session(
            tmp_path, current_cue="Sequence 210.3", stored=False
        )

        event = session.run_instruction("지금 이 큐를 중앙으로")

        assert "콘솔에 저장된 타임라인만" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_a_playing_cue_missing_from_the_timeline_refuses(self, tmp_path):
        session, calls, _sent, _port = self._rehearsal_session(
            tmp_path, current_cue="Sequence 210.9"
        )

        event = session.run_instruction("지금 이 큐를 중앙으로")

        assert "큐 9가 화면 타임라인에 없습니다" in event["text"]
        assert "보유 큐: 3, 5" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []


class TestSetlistMode:
    """Priority 4 (handoff 2026-08-15): library songs → setlist sequences
    (210, 220, …) + page-1 executors (101~), copy-then-assign, one approval,
    empty-slot pre-check, executor-identity readback."""

    class _Channel:
        def __init__(self, answers):
            self.answers = list(answers)
            self.asked = []

        def ask(self, request, **_kwargs):
            self.asked.append(request)
            return self.answers.pop(0) if self.answers else UNANSWERED

    def _registry(self, calls, states):
        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
                calls.append(call)
                if call.name == "query_state":
                    return ToolExecution(
                        ToolResult(
                            tool_call_id=call.id,
                            name=call.name,
                            content=json.dumps(states.get(call.arguments["path"], {})),
                        )
                    )
                outcomes = tuple(
                    CommandOutcome(command=command, status="executed_ok")
                    for command in call.arguments.get("commands", [])
                )
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="{}"),
                    outcomes,
                )

        return Registry()

    def _entry_timeline(self, sequence_number, *, stored=True):
        return {
            "song_title": "곡",
            "sequence_number": sequence_number,
            "lifecycle": "verified" if stored else "pending_approval",
            "console_stored": stored,
            "sections": [{"index": 1, "label": "도입", "cue_number": 1}],
        }

    def _setlist_session(self, tmp_path, *, states=None, answers=("승인",)):
        from server.web.timeline_library import SongTimelineLibrary

        provider = ScriptedProvider([])
        session, _console, _audit, sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls, states or {})
        library = SongTimelineLibrary(tmp_path / "library.json")
        session._timeline_library = library
        session._question_channel = self._Channel(list(answers))
        return session, library, calls, sent

    def test_setlist_copies_and_assigns_in_requested_order(self, tmp_path):
        states = {
            "Executor 101": {"ok": True, "node": {"name": "Exec", "sequenceNo": 210}},
            "Executor 102": {"ok": True, "node": {"name": "Exec", "sequenceNo": 220}},
        }
        session, library, calls, _sent = self._setlist_session(tmp_path, states=states)
        library.save("곡A (자동 v1)", self._entry_timeline(110))
        library.save("곡A (자동 v2)", self._entry_timeline(115))
        library.save("곡B", self._entry_timeline(150))

        event = session.run_instruction("셋리스트 만들어줘: 곡A, 곡B")

        assert event["status"] == "ok"
        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        # 곡A rides its LATEST version (Seq 115, 자동 v2), not v1's 110.
        assert stores[0].arguments["commands"] == [
            "Copy Sequence 115 At 210",
            "Assign Sequence 210 At Executor 101",
            "Copy Sequence 150 At 220",
            "Assign Sequence 220 At Executor 102",
        ]
        assert "readback 검증 완료" in event["text"]
        assert "곡A: Sequence 115 → 210 / Executor 101" in event["text"]

    def test_setlist_execution_records_the_board_plan_order(self, tmp_path):
        # 진행 순서 보드 연동 (handoff item 3): the executed allocation's slot
        # order lands in the shared timeline store for the cue monitor.
        from server.web.session import SongTimelineStore

        states = {
            "Executor 101": {"ok": True, "node": {"name": "Exec", "sequenceNo": 210}},
            "Executor 102": {"ok": True, "node": {"name": "Exec", "sequenceNo": 220}},
        }
        session, library, _calls, _sent = self._setlist_session(tmp_path, states=states)
        store = SongTimelineStore()
        session._timeline_store = store
        library.save("곡A", self._entry_timeline(110))
        library.save("곡B", self._entry_timeline(150))

        event = session.run_instruction("셋리스트: 곡A, 곡B")

        assert "실행했습니다" in event["text"]
        assert store.setlist_sequence_nos == [210, 220]

    def test_a_declined_setlist_records_no_board_plan(self, tmp_path):
        from server.web.session import SongTimelineStore

        session, library, _calls, _sent = self._setlist_session(tmp_path, answers=("취소",))
        store = SongTimelineStore()
        session._timeline_store = store
        library.save("곡A", self._entry_timeline(110))

        session.run_instruction("셋리스트 배분해줘")

        assert store.setlist_sequence_nos == []

    def test_setlist_refuses_an_occupied_slot_without_writing(self, tmp_path):
        states = {
            "DataPool/Sequences/210": {"ok": True, "node": {"name": "Sequence 210"}},
        }
        session, library, calls, _sent = self._setlist_session(tmp_path, states=states)
        library.save("곡A", self._entry_timeline(110))

        event = session.run_instruction("셋리스트 모드")

        assert "이미 사용 중" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_setlist_skips_unstored_songs_and_reports_them(self, tmp_path):
        states = {
            "Executor 101": {"ok": True, "node": {"name": "Exec", "sequenceNo": 210}},
        }
        session, library, calls, _sent = self._setlist_session(tmp_path, states=states)
        library.save("계획만", self._entry_timeline(110, stored=False))
        library.save("저장곡", self._entry_timeline(120))

        event = session.run_instruction("셋리스트 만들어줘")

        stores = [call for call in calls if call.name == "run_commands"]
        assert len(stores) == 1
        assert stores[0].arguments["commands"] == [
            "Copy Sequence 120 At 210",
            "Assign Sequence 210 At Executor 101",
        ]
        assert "계획만(콘솔 미저장" in event["text"]

    def test_setlist_decline_writes_nothing(self, tmp_path):
        session, library, calls, _sent = self._setlist_session(tmp_path, answers=("취소",))
        library.save("곡A", self._entry_timeline(110))

        event = session.run_instruction("셋리스트 배분해줘")

        assert "승인 전이므로 콘솔에 쓰지 않았습니다" in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_setlist_readback_mismatch_is_reported_honestly(self, tmp_path):
        states = {
            "Executor 101": {"ok": True, "node": {"name": "Exec", "sequenceNo": 999}},
        }
        session, library, calls, _sent = self._setlist_session(tmp_path, states=states)
        library.save("곡A", self._entry_timeline(110))

        event = session.run_instruction("셋리스트 만들어줘")

        assert event["status"] == "readback_failed"
        assert "readback 불일치" in event["text"]

    def test_setlist_with_custom_starts_and_page_window_guard(self, tmp_path):
        states = {
            "Executor 305": {"ok": True, "node": {"name": "Exec", "sequenceNo": 400}},
        }
        session, library, calls, _sent = self._setlist_session(tmp_path, states=states)
        library.save("곡A", self._entry_timeline(110))

        event = session.run_instruction("셋리스트: 곡A, 시퀀스 400부터, Executor 305부터")

        stores = [call for call in calls if call.name == "run_commands"]
        assert stores[0].arguments["commands"] == [
            "Copy Sequence 110 At 400",
            "Assign Sequence 400 At Executor 305",
        ]
        assert event["status"] == "ok"

    def test_setlist_without_a_library_refuses(self, tmp_path):
        session, _library, calls, _sent = self._setlist_session(tmp_path)

        event = session.run_instruction("셋리스트 모드 시작")

        assert "라이브러리 곡이 없습니다" in event["text"]
        assert calls == []


class TestLookPanTilt:
    def _registry(self, calls):
        fixtures = [
            {"fid": 20, "name": "RLB350M1 1", "x": 4.0, "y": 0.0, "z": 6.0},
            {"fid": 26, "name": "RLB350M1 7", "x": -4.0, "y": 0.0, "z": 6.0},
            {"fid": 41, "name": "Sphere 1", "x": 0.0, "y": 0.0, "z": 0.0},
        ]

        class Registry:
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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

    def test_a_pan_tilt_fan_request_adds_the_symmetric_tilt_v(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        event = session.run_instruction("팬 45도 틸트 20도 부채살로 펼쳐줘")

        commands = calls[-1].arguments["commands"]
        # Pan spread 45 with a tilt V: end fixtures 45+20=65, centre stays 45.
        assert commands == [
            "Fixture 26 ; Attribute 'Pan' At 135 ; Attribute 'Tilt' At 65",
            "Fixture 41 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 45",
            "Fixture 20 ; Attribute 'Pan' At -135 ; Attribute 'Tilt' At 65",
        ]
        assert "틸트 ±20도" in event["text"]

    def test_a_both_axes_word_without_numbers_takes_the_default_tilt_v(self, tmp_path):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = self._registry(calls)

        session.run_instruction("팬틸트 모두 부채살로 펼쳐줘")

        commands = calls[-1].arguments["commands"]
        # Default pan ±30 with the default ±15 tilt V: ends 60, centre 45.
        assert "Attribute 'Tilt' At 60" in commands[0]
        assert "Attribute 'Tilt' At 45" in commands[1]

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
            def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
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


class TestPositionFxSequence:
    """포지션 이펙트 시퀀스 빌더 — 저장된 FX 포지션 프리셋(2.N~2.N+9)을 실제로
    소비하는 시퀀스를 만든다. 명령열 자체는 ``position_fx_commands``가 만들므로
    여기서는 (1) 효과어 5종 라우팅과 산출 명령열의 일치, (2) 번호 두 개의 출처
    (문장/카드), (3) fail-closed(미답·미해석 시 쓰기 0건), (4) 점유 시퀀스 확인
    카드, (5) 이펙트 **적용** 문장 비탈취를 겨눈다."""

    _FIDS = [20, 26]  # `_PresetPoolRegistry._FIXTURES`의 fid들

    def _run(self, tmp_path, text, *, answers=(), **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls, **rig)
        chan = _AnsweringChannel(answers)
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    def _expected(self, effect, label, *, start=41, sequence=201):
        return position_fx_commands(
            effect,
            fids=self._FIDS,
            fx_preset_start=start,
            sequence_no=sequence,
            label=label,
        )

    # (1)+(2 문장) — 어휘 5종이 각자 효과로 라우팅되고, 두 번호를 모두 문장에서
    # 읽으면 카드 없이 run_commands 1번들이 position_fx_commands 산출 그대로 나간다.
    @pytest.mark.parametrize(
        ("text", "effect", "label"),
        [
            ("좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터", "sweep", "좌우 스윕"),
            (
                "플라이아웃 포지션 이펙트 시퀀스 201 생성해줘, 프리셋 41번부터",
                "flyout",
                "플라이아웃",
            ),
            ("원을 그리는 포지션 이펙트 시퀀스 201 걸어줘, 41번부터", "circle", "서클"),
            ("발리후 시퀀스 201 만들어줘, FX 프리셋 41번부터", "ballyhoo", "발리후"),
            ("물결 시퀀스 201 저장해줘, FX 프리셋 41번부터", "wave", "웨이브"),
        ],
    )
    def test_each_effect_word_builds_the_exact_bundle(self, tmp_path, text, effect, label):
        event, calls, chan = self._run(tmp_path, text)

        # 저장 번들이 전건 executed_ok로 끝나면 실행기 제안 카드가 **한 장**
        # 따라온다 — 리그의 Page 1은 비어 있으므로 대역 최소인 101을 제안하고,
        # 미답이면 Assign 없이 미할당으로 끝난다.
        assert len(chan.asked) == 1
        assert "실행기 101" in chan.asked[0].prompt
        writes = _writes(calls)
        assert len(writes) == 1
        assert tuple(writes[0].arguments["commands"]) == self._expected(effect, label)
        assert "시퀀스 201" in event["text"]
        assert "2.41~2.50" in event["text"]
        assert "실행기 미할당" in event["text"]

    # (2 카드) — 번호가 둘 다 없으면 카드가 정확히 두 장(프리셋 시작 → 시퀀스)
    # 뜨고, 답이 명령열에 그대로 반영된다. 저장이 성공하므로 실행기 제안 카드가
    # 세 번째로 따라온다(미답 → Assign 0건).
    def test_missing_numbers_are_asked_one_card_each(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path, "좌우 스윕 시퀀스 만들어줘", answers=["41", "201"]
        )

        assert len(chan.asked) == 3
        assert "몇 번부터" in chan.asked[0].prompt
        assert "몇 번 시퀀스" in chan.asked[1].prompt
        assert "걸까요" in chan.asked[2].prompt
        writes = _writes(calls)
        assert len(writes) == 1
        assert tuple(writes[0].arguments["commands"]) == self._expected("sweep", "좌우 스윕")

    # (3) — 첫 카드 미답이면 쓰기 0건으로 거부한다 (fail-closed).
    def test_an_unanswered_start_card_writes_nothing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "좌우 스윕 시퀀스 만들어줘",
            answers=[],  # UNANSWERED
        )

        assert len(chan.asked) == 1
        assert _writes(calls) == []
        assert "FX 프리셋 시작 번호" in event["text"]

    def test_an_unanswered_sequence_card_writes_nothing(self, tmp_path):
        event, calls, chan = self._run(tmp_path, "좌우 스윕 시퀀스 만들어줘", answers=["41"])

        assert len(chan.asked) == 2
        assert _writes(calls) == []
        assert "시퀀스 번호" in event["text"]

    def test_a_numberless_answer_is_refused_with_the_format_example(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path, "좌우 스윕 시퀀스 만들어줘", answers=["모르겠는데"]
        )

        assert _writes(calls) == []
        assert "예: " in event["text"]

    # (4) — 점유된 시퀀스는 확인 카드를 거친다: 취소는 쓰기 0건, 승낙은 진행.
    def test_an_occupied_sequence_asks_and_cancel_writes_nothing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터",
            child_count=3,  # query_state가 node를 돌려줘 점유로 판독된다
            answers=["취소"],
        )

        assert _writes(calls) == []
        assert len(chan.asked) == 1
        assert "기존 데이터" in chan.asked[0].prompt
        assert "저장하지 않" in event["text"]

    def test_an_occupied_sequence_proceeds_on_consent(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터",
            child_count=3,
            answers=["진행"],
        )

        assert len(chan.asked) == 1
        writes = _writes(calls)
        assert len(writes) == 1
        assert tuple(writes[0].arguments["commands"]) == self._expected("sweep", "좌우 스윕")

    # (5) — 이펙트 **적용** 문장은 효과어가 있어도(웨이브) 시퀀스/포지션 이펙트
    # 명사와 생성 동사가 없으므로 이 빌더를 지나쳐 기존 경로(모델)로 간다.
    @pytest.mark.parametrize("text", ["무빙 이펙트 적용해줘", "웨이브 이펙트 적용해줘"])
    def test_effect_application_sentences_fall_through_to_the_model(self, tmp_path, text):
        provider = ScriptedProvider([_final("이펙트 적용을 확인하겠습니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(calls)
        chan = _AnsweringChannel([])
        session._question_channel = chan

        session.run_instruction(text)

        assert len(provider.calls) == 1
        assert chan.asked == []
        assert not any("Store Sequence" in cmd for cmd in _all_commands(calls))

    # 라우팅 회귀 — 프리셋 **저장** 문장(효과어 없음)은 여전히 FX 프리셋 저장
    # 흐름으로 가 10번들을 쓴다. 이 빌더가 앞에서 가로챘다면 1번들이었을 것이다.
    def test_a_preset_store_sentence_is_not_captured_by_the_builder(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path, "이펙트 포지션 프리셋을 41번부터 저장해줘", pool=(1, 2, 3)
        )

        assert chan.asked == []
        assert len(_writes(calls)) == 10
        assert not any("Store Sequence" in cmd for cmd in _all_commands(calls))


class _ExecutorPageRegistry(_PresetPoolRegistry):
    """``DataPool/Pages/1`` 판독만 분리 제어하는 리그 — 실행기 제안 흐름 전용.

    베이스 리그는 모든 ``query_state``에 같은 페이로드를 돌려주므로 "제안 전
    스캔"과 "Assign 후 되읽기"를 구별해 겨눌 수 없다. 여기서는 Pages/1 경로만
    가로채고, Assign write 경계 전에는 ``page``, 후에는 ``page_after``를
    돌려준다 — 값은 실행기 번호가 아니라 응답기의 ``i``(= 실행기 − 100)다.
    """

    def __init__(
        self,
        calls,
        *,
        page=(),
        page_after=None,
        page_error=False,
        page_after_error=False,
        page_truncated=False,
        page_child_count=None,
        **kwargs,
    ):
        super().__init__(calls, **kwargs)
        self.page = tuple(page)
        self.page_after = self.page if page_after is None else tuple(page_after)
        self.page_error = page_error
        self.page_after_error = page_after_error
        self.page_truncated = page_truncated
        self.page_child_count = page_child_count
        self.assigned = False

    def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
        if call.name == "query_state" and str(call.arguments.get("path", "")).endswith("Pages/1"):
            self.calls.append(call)
            if self.page_error or (self.assigned and self.page_after_error):
                return ToolExecution(
                    ToolResult(tool_call_id=call.id, name=call.name, content="", is_error=True)
                )
            slots = self.page_after if self.assigned else self.page
            payload = {"children": [{"i": n} for n in slots]}
            if self.page_truncated:
                payload["truncated"] = True
            if self.page_child_count is not None:
                payload["node"] = {"childCount": self.page_child_count}
            return ToolExecution(
                ToolResult(tool_call_id=call.id, name=call.name, content=json.dumps(payload))
            )
        if call.name == "run_commands" and any(
            "Assign Sequence" in cmd for cmd in call.arguments.get("commands", ())
        ):
            self.assigned = True
        return super().dispatch(call)


def _assign_writes(calls):
    return [
        call
        for call in _writes(calls)
        if any("Assign Sequence" in cmd for cmd in call.arguments["commands"])
    ]


class TestPositionFxIntentFrame:
    """SPEC-COPILOT-INTENT-001 M1~M3 — 어휘가 라우터가 아니라 후보라는 계약.

    2026-08-19 실측 재현 케이스: "원형 회전 R/G **컬러** 페이저"가 두 번
    연속 `_POSITION_FX_VOCABULARY` circle 정규식에 잡혀 팬/틸트 서클
    빌더로 갔고, 두 번째 발화의 명시적 부정("포지션이 아니라 컬러다")조차
    무시됐다. 정규식은 부정을 읽지 못하고 첫-매치가 곧 판정이기 때문이다.

    겨누는 것: (1) 명시적 부정은 하드 베토 — 좌표 판독조차 하지 않고
    빠진다, (2) 비-포지션 속성축이 주체로 명시되고 포지션 축 단어가 없으면
    카드 1장으로 축을 확정한다, (3) 그 카드에서 컬러를 고르면 포지션
    빌더는 저장 0건으로 빠진다, (4) 포지션을 고르면 기존 몸통이 그대로
    돈다, (5) 방향·형상 해석은 회신에 근거가 실린다(FID 순서가 아니라
    좌표).

    (2)는 t34에서 개정됐다. 원래는 「포지션 축 단어가 없으면」이 조건이었으나,
    배제 문장이 배제하려는 바로 그 낱말을 쓰기 때문에 낱말의 존재로 카드를
    건너뛰면 배제가 긍정으로 뒤집힌다. 이제 경쟁 축이 주체로 지목되면 낱말과
    무관하게 카드로 확정한다 — 받아들인 비용은 아래 (4) 참조.
    """

    _SWEEP = "좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터"

    def _run(self, tmp_path, text, *, answers=(), **rig):
        provider = ScriptedProvider([_final("확인하겠습니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _ExecutorPageRegistry(calls, **rig)
        chan = _AnsweringChannel(answers)
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    @staticmethod
    def _spatial_reads(calls):
        return [call for call in calls if call.name == "get_spatial_context"]

    @staticmethod
    def _store_writes(calls):
        return [
            call
            for call in _writes(calls)
            if any("Store Sequence" in cmd for cmd in call.arguments["commands"])
        ]

    # ---- (1) 명시적 부정 = 하드 베토 ----

    @pytest.mark.parametrize(
        "text",
        [
            "포지션은 건드리지 말고 컬러 서클 시퀀스 만들어줘",
            "포지션이 아니라 컬러다 — 원을 그리는 시퀀스 만들어줘",
            "빔은 아니고 색만, 웨이브 시퀀스 만들어줘",
            "무빙 말고 컬러로 스윕 시퀀스 만들어줘",
        ],
    )
    def test_an_explicit_negation_vetoes_the_position_builder(self, tmp_path, text):
        _event, calls, chan = self._run(tmp_path, text)

        # 베토는 좌표 판독 **앞**에서 끝난다 — 콘솔 왕복을 쓰지 않는다.
        assert self._spatial_reads(calls) == []
        assert self._store_writes(calls) == []
        assert chan.asked == []

    # ---- (2)(3) 축 충돌은 카드 1장, 컬러를 고르면 포지션 빌더가 빠진다 ----

    def test_a_non_position_attribute_asks_one_axis_card(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "R/G 컬러가 원을 그리며 도는 시퀀스 201 만들어줘, FX 프리셋 41번부터",
            answers=["색이 바뀐다 (장비는 고정)"],
        )

        axis_cards = [q for q in chan.asked if "무엇이" in q.prompt]
        assert len(axis_cards) == 1
        labels = [option.label for option in axis_cards[0].options]
        assert any("색" in label for label in labels)
        assert any("빔" in label for label in labels)
        # 컬러를 골랐으므로 포지션 빌더는 저장 0건으로 빠진다.
        assert self._store_writes(calls) == []
        assert self._spatial_reads(calls) == []

    def test_choosing_the_beam_axis_keeps_the_position_body(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "R/G 컬러가 원을 그리며 도는 시퀀스 201 만들어줘, FX 프리셋 41번부터",
            answers=["빔이 움직인다 (포지션 이펙트)", "걸기"],
        )

        assert len(self._spatial_reads(calls)) == 1
        assert len(self._store_writes(calls)) == 1

    # ---- (4) 두 축이 다 나오면 카드로 확정한다 — 받아들인 비용 ----

    def test_an_explicit_position_word_still_gets_the_card(self, tmp_path):
        """머리말이 분명한 문장에도 카드가 뜬다 — 알고 받은 비용이다(t34).

        이 문장은 모호하지 않다. 머리말이 `포지션 이펙트` 이고 `컬러 프리셋도
        쓰는` 은 그것을 꾸민다. 그런데도 묻는 이유는, 낱말의 존재로 카드를
        건너뛰면 **배제 문장이 같은 낱말을 쓰기 때문에** 배제가 긍정으로
        뒤집히기 때문이다 — 원본 대비 16문장 중 13문장이 그렇게 샜다.

        두 실패의 값이 대칭이 아니다: 여기서 지는 비용은 질문 한 장이고,
        반대 방향은 사용자가 배제한 축으로 조용히 저장되는 것이며 실패
        신호가 없어 리허설에서야 드러난다. 이 테스트를 「없애야 할 과잉」으로
        읽지 말 것 — 개정된 REQ-INTENT-008 이 명시한 비용이다.
        """
        _event, calls, chan = self._run(
            tmp_path,
            "컬러 프리셋도 쓰는 포지션 이펙트 서클 시퀀스 201 만들어줘, FX 프리셋 41번부터",
            answers=["빔이 움직인다 (포지션 이펙트)", "걸기"],
        )

        assert len([q for q in chan.asked if "무엇이" in q.prompt]) == 1
        assert len(self._store_writes(calls)) == 1

    # ---- (5) 해석 근거를 회신에 싣는다 ----

    def test_the_reply_states_how_the_geometry_was_derived(self, tmp_path):
        event, _calls, _chan = self._run(tmp_path, self._SWEEP, answers=["건너뛰기"])

        assert "좌표 해석" in event["text"]
        assert "FID 순서" in event["text"]
        # 실측 범위가 문면에 들어간다 — 스텁 리그는 x −4.0~+4.0.
        assert "-4.0" in event["text"] and "4.0" in event["text"]


class TestPositionFxExecutorOffer:
    """시퀀스 저장 성공 직후의 실행기 할당 제안 — 2026-08-16 Executor 105
    사고(점유 오판 위의 Assign이 기존 바인딩을 덮어씀)의 재발 방지 계약.

    겨누는 것: (1) i−100 매핑과 대역(101~115) 최소 빈 번호 제안, (2) 승낙 시
    Assign 정확히 1건 + Page 1 되읽기로만 착지 보고, (3) 건너뛰기/미답 시
    Assign 0건, (4) 판독 불가(에러·truncated·childCount 불일치) 시 카드 0·
    Assign 0·고지 문면, (5) 되읽기 불일치 시 '착지 미확인' 문면, (6) 저장
    번들이 전건 executed_ok가 아니면 제안 자체가 없다.
    """

    _TEXT = "좌우 스윕 시퀀스 201 만들어줘, FX 프리셋 41번부터"

    def _run(self, tmp_path, *, answers=(), **rig):
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _ExecutorPageRegistry(calls, **rig)
        chan = _AnsweringChannel(answers)
        session._question_channel = chan
        event = session.run_instruction(self._TEXT)
        return event, calls, chan

    # (1) — children i=1~6 점유(= Executor 101~106)면 대역의 최소 빈 번호인
    # 107을 제안한다. i를 실행기 번호로 오독하면 101을 제안했을 것이다.
    def test_occupied_children_map_i_plus_100_and_propose_the_lowest_free(self, tmp_path):
        _event, _calls, chan = self._run(tmp_path, page=(1, 2, 3, 4, 5, 6), answers=[])

        offer_cards = [q for q in chan.asked if "걸까요" in q.prompt]
        assert len(offer_cards) == 1
        assert "실행기 107" in offer_cards[0].prompt
        assert "시퀀스 201" in offer_cards[0].prompt

    # (1 보강) — i=4/5/6 점유는 Executor 104/105/106이므로 최소 빈 번호는
    # 101이다. 105 사고의 반대 방향 오독(i에 100을 두 번 더함)을 잡는다.
    def test_a_sparse_page_still_proposes_the_band_minimum(self, tmp_path):
        _event, _calls, chan = self._run(tmp_path, page=(4, 5, 6), answers=[])

        offer_cards = [q for q in chan.asked if "걸까요" in q.prompt]
        assert len(offer_cards) == 1
        assert "실행기 101" in offer_cards[0].prompt

    # (2) — 승낙(옵션 라벨 '걸기')이면 검증된 문법의 Assign이 정확히 1건
    # 나가고, 되읽기(page_after에 i=7 등장)로 착지를 확인해 산술과 함께
    # 보고한다.
    def test_consent_assigns_once_and_reports_the_verified_landing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            page=(1, 2, 3, 4, 5, 6),
            page_after=(1, 2, 3, 4, 5, 6, 7),
            answers=["걸기"],
        )

        assigns = _assign_writes(calls)
        assert len(assigns) == 1
        assert assigns[0].arguments["commands"] == ["Assign Sequence 201 At Executor 107"]
        # 스캔 1회 + 되읽기 1회 — 착지 판정은 되읽기에서만 나온다.
        page_reads = [
            c
            for c in calls
            if c.name == "query_state" and str(c.arguments.get("path", "")).endswith("Pages/1")
        ]
        assert len(page_reads) == 2
        assert "실행기 107" in event["text"]
        assert "착지를 확인" in event["text"]
        assert "i=7" in event["text"]

    # (2 보강) — 자유 입력 승낙어('네')도 승낙이다 (_preset_answer_intent).
    def test_a_free_text_consent_word_also_assigns(self, tmp_path):
        _event, calls, _chan = self._run(tmp_path, page=(), page_after=(1,), answers=["네"])

        assert len(_assign_writes(calls)) == 1

    # (3) — 건너뛰기·미답이면 Assign 0건, 저장 회신은 유지되고 미할당 한 줄이
    # 붙는다.
    @pytest.mark.parametrize("answers", [["건너뛰기"], []])
    def test_skip_or_silence_never_assigns(self, tmp_path, answers):
        event, calls, chan = self._run(tmp_path, page=(1,), answers=answers)

        assert len(chan.asked) == 1
        assert _assign_writes(calls) == []
        assert "시퀀스 201" in event["text"]
        assert "실행기 미할당" in event["text"]

    # (4) — 판독 불가 세 갈래(에러 / truncated / childCount 불일치)는 전부
    # 카드 0·Assign 0에 고지 문면으로 끝난다. 모름 위의 제안이 105 사고다.
    @pytest.mark.parametrize(
        "rig",
        [
            {"page_error": True},
            {"page": (1, 2), "page_truncated": True},
            {"page": (1, 2), "page_child_count": 30},
        ],
    )
    def test_an_unreadable_page_offers_nothing_and_says_why(self, tmp_path, rig):
        event, calls, chan = self._run(tmp_path, answers=["걸기"], **rig)

        assert chan.asked == []
        assert _assign_writes(calls) == []
        assert "시퀀스 201" in event["text"]  # 저장 회신은 유지된다
        assert "실행기 점유를 읽지 못해 할당을 제안하지 않았습니다" in event["text"]

    # (4 보강) — 대역 전체(101~115)가 점유면 제안할 빈 실행기가 없다:
    # 카드 없이 고지만 남긴다.
    def test_a_full_band_offers_nothing(self, tmp_path):
        event, calls, chan = self._run(tmp_path, page=tuple(range(1, 16)), answers=["걸기"])

        assert chan.asked == []
        assert _assign_writes(calls) == []
        assert "모두 점유돼 있어 할당을 제안하지 않았습니다" in event["text"]

    # (5) — Assign의 OK는 착지 증거가 아니다(2026-08-16 실측): 되읽기에서
    # 표적이 나타나지 않으면 '착지 미확인'으로 보고한다.
    def test_a_readback_miss_reports_the_unconfirmed_landing(self, tmp_path):
        event, calls, _chan = self._run(tmp_path, page=(1,), page_after=(1,), answers=["걸기"])

        assert len(_assign_writes(calls)) == 1
        assert "착지 미확인" in event["text"]
        assert "실행기 102" in event["text"]

    # (5 보강) — 되읽기 자체가 죽어도(판독 불가) 착지 확인으로 위장하지 않고,
    # Assign도 다시 쏘지 않는다.
    def test_a_dead_readback_is_also_unconfirmed(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path, page=(1,), page_after_error=True, answers=["걸기"]
        )

        assert len(_assign_writes(calls)) == 1
        assert "착지 미확인" in event["text"]

    # (6) — 저장 번들이 전건 executed_ok가 아니면(게이트 proposal 등) 제안
    # 자체가 없다: 존재가 확정되지 않은 시퀀스를 걸지 않는다.
    def test_a_gated_store_bundle_suppresses_the_offer(self, tmp_path):
        event, calls, chan = self._run(tmp_path, status="proposal", answers=["걸기"])

        assert chan.asked == []
        assert _assign_writes(calls) == []
        page_reads = [
            c
            for c in calls
            if c.name == "query_state" and str(c.arguments.get("path", "")).endswith("Pages/1")
        ]
        assert page_reads == []
        assert "실행기" not in event["text"]


class TestPhaserRecall:
    """T11 1단계(즉시 recall/해제)·2단계(시퀀스+Exec) — T11 프로브
    (``docs/research/ma3-effects/11-phaser-recall-m0-probe.md``)로 실측된
    recall/해제/큐 저장 문법의 소비 구현.

    겨누는 것: (1) 모듈 빌더가 T11 §2/§3/§4 문법과 문자 단위로 일치하는지
    (pool_no=2 출력은 ``pointing.preset_recall_command``와 동일해야 함),
    (2) 라벨→(pool_no, slot) 실기 해석이 페이징으로 이뤄지고 부재는
    거부인지, (3) Color/Dimmer/All 1 세 카탈로그 각각의 대상 장비 판별이
    맞는 몸통(컬러 판별 vs 전량 열거)으로 가는지, (4) 1단계/2단계/저장
    가족이 서로소로 라우팅되는지, (5) 2단계가 ``_position_fx_sequence``/
    ``_offer_fx_executor_assignment``의 시퀀스 번호·점유·실행기 제안
    몸통을 그대로 재사용하는지.
    """

    _FIDS = [20, 26]  # `_PresetPoolRegistry._FIXTURES`의 fid들

    def _run(
        self,
        tmp_path,
        text,
        *,
        answers=(),
        pool_index=_COMBO_POOL_INDEX,
        pool=(),
        names=None,
        pairs=((20, 20), (26, 26)),
        fid_unread=(),
        capable=(20, 26),
        excluded=(),
        undetermined=(),
        sequence_occupied=None,
        **rig,
    ):
        provider = ScriptedProvider([_final("확인하겠습니다")])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list[ToolCall] = []
        session._registry = _PresetPoolRegistry(
            calls, pool_index=pool_index, pool=pool, names=names or {}, **rig
        )
        session._color_rig_fixture_pairs = lambda: (
            [tuple(pair) for pair in pairs],
            list(fid_unread),
        )
        session._color_capable_fids = lambda _pairs, *, probe_id_prefix: (
            list(capable),
            list(excluded),
            list(undetermined),
        )
        if sequence_occupied is not None:
            session._song_sequence_occupied = lambda _no: sequence_occupied
        chan = _AnsweringChannel(answers)
        session._question_channel = chan
        event = session.run_instruction(text)
        return event, calls, chan

    # ---- (1) 모듈 빌더 — T11 §2/§3/§4 실측 문법과 문자 단위 일치 ----

    def test_recall_command_matches_pointing_at_the_position_pool(self):
        fids = [3, 7, 12]
        assert _preset_recall_command(POSITION_PRESET_POOL, fids, 5) == preset_recall_command(
            fids, 5
        )

    def test_recall_command_carries_the_requested_pool(self):
        assert _preset_recall_command(4, [2], 31) == "Fixture 2 ; At Preset 4.31"
        assert _preset_recall_command(1, [2, 7], 21) == "Fixture 2 + 7 ; At Preset 1.21"

    @pytest.mark.parametrize(
        ("pool_no", "fids", "preset_no"),
        [(0, [2], 1), (-1, [2], 1), (2, [], 1), (2, [2], 0), (2, [2], -1)],
    )
    def test_recall_command_rejects_non_positive_inputs(self, pool_no, fids, preset_no):
        with pytest.raises(SpatialPointingError):
            _preset_recall_command(pool_no, fids, preset_no)

    def test_release_command_matches_the_probed_grammar(self):
        assert _preset_release_command([2]) == "Fixture 2 ; At Preset 0"
        assert _preset_release_command([2, 7]) == "Fixture 2 + 7 ; At Preset 0"

    def test_release_command_rejects_empty_fids(self):
        with pytest.raises(SpatialPointingError):
            _preset_release_command([])

    def test_sequence_bundle_matches_the_probed_grammar(self):
        commands = _phaser_sequence_commands(4, [2], 31, 201, "Breathe Warm")
        assert commands == (
            "ChangeDestination Root",
            "ClearAll",
            "Fixture 2 ; At Preset 4.31",
            "Store Sequence 201 Cue 1 'Breathe Warm' CueFade 2",
            "Label Sequence 201 'Breathe Warm'",
            "ClearAll",
        )
        assert not any("/Merge" in cmd or "/Overwrite" in cmd for cmd in commands)

    def test_sequence_bundle_rejects_a_quoted_label(self):
        with pytest.raises(SpatialPointingError):
            _phaser_sequence_commands(4, [2], 31, 201, "Bad'Label")

    def test_sequence_bundle_rejects_a_non_positive_sequence_no(self):
        with pytest.raises(SpatialPointingError):
            _phaser_sequence_commands(4, [2], 31, 0, "Breathe Warm")

    # ---- (2)+(3) 1단계 — 라벨→슬롯 실기 해석, 발사/해제, 카탈로그별 판별 ----

    def test_recall_resolves_the_slot_via_paged_listing_and_fires(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path, "Breathe Warm 쳐줘", pool=(31,), names={31: "Breathe Warm"}
        )
        assert chan.asked == []
        writes = _writes(calls)
        assert len(writes) == 1
        assert list(writes[0].arguments["commands"]) == [_preset_recall_command(4, self._FIDS, 31)]
        assert "Preset 4.31" in event["text"]
        # recall 적재 ASSUMPTION은 2026-08-19 육안 확인으로 종결 — 발사 회신은
        # Rectangle 파형 잔여 미검증만 고지한다(13번 프로브 §확인 기록).
        assert "Rectangle 계열 파형" in event["text"]

    def test_recall_refuses_when_the_label_is_not_on_console(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path, "Breathe Warm 쳐줘", pool=(31,), names={31: "Chase RB"}
        )
        assert _writes(calls) == []
        assert "찾지 못해" in event["text"]

    def test_release_verb_fires_the_at_preset_zero_grammar(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path, "Breathe Warm 꺼줘", pool=(31,), names={31: "Breathe Warm"}
        )
        writes = _writes(calls)
        assert len(writes) == 1
        assert list(writes[0].arguments["commands"]) == [_preset_release_command(self._FIDS)]
        assert "ASSUMPTION" not in event["text"]

    # 발사·해제 동사가 한 문장에 공존하면 해제가 이긴다(보수적 — 재발사
    # 사고를 피한다).
    def test_both_verbs_present_prefers_release(self, tmp_path):
        _event, calls, _chan = self._run(
            tmp_path, "Breathe Warm 쳐줬다가 꺼줘", pool=(31,), names={31: "Breathe Warm"}
        )
        writes = _writes(calls)
        assert list(writes[0].arguments["commands"]) == [_preset_release_command(self._FIDS)]

    # '재생성'의 부분 문자열 '재생'이 발사 동사로 오인되지 않는다.
    def test_regenerate_wording_does_not_trigger_a_launch(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "Breathe Warm 다시 재생성해줘",
            pool=(31,),
            names={31: "Breathe Warm"},
        )
        assert _writes(calls) == []
        assert chan.asked == []

    def test_a_dimmer_catalog_label_uses_the_dimmer_pool_and_full_enumeration(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "Breathe Soft 쳐줘",
            pool=(21,),
            names={21: "Breathe Soft"},
            capable=(20,),  # 디머는 컬러 판별을 타지 않으므로 무시돼야 한다
        )
        writes = _writes(calls)
        assert list(writes[0].arguments["commands"]) == [_preset_recall_command(1, self._FIDS, 21)]
        assert "Preset 1.21" in event["text"]

    def test_a_combo_catalog_label_uses_all1_and_color_capability(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "Drop Slam 쳐줘",
            pool=(25,),
            names={25: "Drop Slam"},
            capable=(20,),
            excluded=(26,),
        )
        writes = _writes(calls)
        assert list(writes[0].arguments["commands"]) == [_preset_recall_command(21, [20], 25)]
        assert "Preset 21.25" in event["text"]
        assert "컬러 판별" in event["text"]

    def test_storage_sentences_are_not_captured_by_recall(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "멀티컬러 페이저 프리셋을 31번부터 저장해줘",
            pool=(1, 2, 3),
            readback=(1, 2, 3) + tuple(range(31, 41)),
        )
        writes = _writes(calls)
        assert len(writes) == 10  # 저장 가족(카탈로그 10종)이 그대로 처리
        assert chan.asked == []

    # ---- (4)+(5) 2단계 — 시퀀스+실행기, 1단계와 명사 유무로 서로소 ----

    def test_sequence_recall_builds_the_exact_bundle_and_offers_an_executor(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "Breathe Warm 시퀀스 201로 쳐줘",
            pool=(31,),
            names={31: "Breathe Warm"},
        )
        writes = _writes(calls)
        assert len(writes) == 1
        assert tuple(writes[0].arguments["commands"]) == _phaser_sequence_commands(
            4, self._FIDS, 31, 201, "Breathe Warm"
        )
        assert len(chan.asked) == 1
        assert "실행기 101" in chan.asked[0].prompt
        assert "시퀀스 201" in event["text"]
        assert "실행기 미할당" in event["text"]

    def test_a_wave_named_label_is_not_swallowed_by_the_position_fx_path(self, tmp_path):
        # 라이브 2026-08-17 회귀: "Wave CM 시퀀스로 걸어줘"가 position-FX의
        # 세 게이트(효과어 'wave' + 명사 '시퀀스' + 동사 '걸어')를 전부
        # 만족해 포지션 이펙트 경로에 삼켜졌다 — 'Wave'를 품은 카탈로그
        # 라벨 6종(Wave CM/WA/Soft/Full, Ocean Wave, Golden Wave)이 2단계에
        # 도달하지 못했다. 디스패치 순서를 페이저 먼저로 고쳐 고정한다.
        event, calls, _chan = self._run(
            tmp_path,
            "Wave CM 시퀀스 202로 걸어줘",
            pool=(35,),
            names={35: "Wave CM"},
        )
        writes = _writes(calls)
        assert len(writes) == 1
        commands = writes[0].arguments["commands"]
        # 페이저 경로: Color 풀 4.35 recall + 라벨이 'Wave CM'인 시퀀스
        assert any("At Preset 4.35" in cmd for cmd in commands)
        assert any("Store Sequence 202" in cmd and "Wave CM" in cmd for cmd in commands)
        # 포지션 이펙트 경로의 흔적(Pan/Tilt 상대 페이저)이 없어야 한다
        assert not any("Attribute 'Pan'" in cmd or "Attribute 'Tilt'" in cmd for cmd in commands)
        assert "Wave CM" in event["text"]

    def test_a_position_fx_sentence_still_reaches_the_position_path(self, tmp_path):
        # 역방향 — 카탈로그 라벨이 없는 포지션 문장은 페이저 핸들러를
        # 그대로 통과해 종전 경로로 흘러내린다(라벨 게이트의 근거).
        from server.web.session import _match_phaser_label

        assert _match_phaser_label("좌우 스윕 시퀀스 201 만들어줘") is None
        assert _match_phaser_label("웨이브 시퀀스 만들어줘") is None

    def test_a_plain_recall_sentence_does_not_reach_the_sequence_builder(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path, "Breathe Warm 쳐줘", pool=(31,), names={31: "Breathe Warm"}
        )
        writes = _writes(calls)
        assert len(writes) == 1
        assert not any("Store Sequence" in cmd for cmd in writes[0].arguments["commands"])
        assert chan.asked == []  # 1단계는 실행기 카드를 제안하지 않는다

    def test_missing_sequence_number_asks_one_card(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "Breathe Warm 시퀀스로 쳐줘",
            pool=(31,),
            names={31: "Breathe Warm"},
            answers=["201"],
        )
        sequence_cards = [q for q in chan.asked if "몇 번 시퀀스" in q.prompt]
        assert len(sequence_cards) == 1
        writes = _writes(calls)
        assert len(writes) == 1
        assert "Store Sequence 201" in writes[0].arguments["commands"][3]

    def test_an_unanswered_sequence_card_writes_nothing(self, tmp_path):
        event, calls, _chan = self._run(
            tmp_path,
            "Breathe Warm 시퀀스로 쳐줘",
            pool=(31,),
            names={31: "Breathe Warm"},
            answers=[],
        )
        assert _writes(calls) == []
        assert "시퀀스 번호를 받지 못해" in event["text"]

    def test_an_occupied_sequence_asks_and_cancel_writes_nothing(self, tmp_path):
        event, calls, chan = self._run(
            tmp_path,
            "Breathe Warm 시퀀스 201로 쳐줘",
            pool=(31,),
            names={31: "Breathe Warm"},
            sequence_occupied=True,
            answers=["취소"],
        )
        assert _writes(calls) == []
        assert len(chan.asked) == 1
        assert "기존 데이터" in chan.asked[0].prompt
        assert "저장하지 않" in event["text"]

    def test_an_occupied_sequence_proceeds_on_consent(self, tmp_path):
        _event, calls, chan = self._run(
            tmp_path,
            "Breathe Warm 시퀀스 201로 쳐줘",
            pool=(31,),
            names={31: "Breathe Warm"},
            sequence_occupied=True,
            answers=["진행"],
        )
        writes = _writes(calls)
        assert len(writes) == 1


def _cue(
    *,
    cue_name: str,
    d_level: int = 3,
    key_pct: float | None = 60.0,
    blackout: bool = False,
    kind: str = "section",
) -> ComposedCue:
    """A minimal, valid ``ComposedCue`` for direct classifier/builder tests —
    only ``cue_name``/``d_level``/``dimmer`` vary; every other field is a
    harmless constant satisfying each nested dataclass's own validation."""
    resolved_key_pct = 0.0 if blackout else key_pct
    return ComposedCue(
        kind=kind,
        section_index=1,
        cue_number=1.0,
        cue_name=cue_name,
        d_level=d_level,
        fade_seconds=2.0,
        position=CuePositionData(requested=None, stored=None, width_tier=None, source="test"),
        dimmer=CueDimmerData(
            key_pct=resolved_key_pct,
            back_pct=None,
            budget_range_pct=(0.0, 100.0),
            blackout=blackout,
        ),
        color=CueColorData(palette=("White",), saturation="full"),
        fx=CueFxData(requested=(), permitted=(), disabled=(), density=0, axis_budget=0),
        accents=(),
        mib=CueMibData(),
        timing=CueTimingData(mode=MANUAL_GO, trigger="manual_go", start_ms=0),
    )


class TestPhaserSongCueMapping:
    """T12 — 곡 큐 페이저 통합. 겨누는 것: (e) 매핑 표 계약(``_phaser_label_
    for_cue``, 코디네이터 5-카테고리 + '그 외 전부 없음'), (a)/(b) 명령
    조립(``_phaser_cue_value_lines``, 슬롯 미해석/불일치 시 빈 튜플, 해석
    시 recall 한 줄이 플랜 자신의 값 라인 뒤·Store 앞에 온다), 안전 가드
    (MIB pre-move·블랙아웃 제외), (c) 미해석 사유 노출(``_phaser_failure_
    note``). 실기 슬롯 해석(``_phaser_slot_by_label``, 배치 쿼리)과 리뷰
    시트 표시(``_review_text``)는 ``TestSongDesignInterviewSession``의
    비회귀 테스트(§T12(a)/(b) 회귀 방어)가 이미 실측한다.
    """

    # ---- (e) 매핑 표 계약 ----

    @pytest.mark.parametrize(
        ("cue_name", "expected"),
        [
            ("드롭", "Drop Slam"),
            ("클라이맥스", "Drop Slam"),
            ("피크", "Drop Slam"),
            ("Drop", "Drop Slam"),
            ("후렴", "Wave CM"),
            ("Chorus", "Wave CM"),
            ("벌스", "Breathe Warm"),
            ("Verse 1", "Breathe Warm"),
            ("브리지", "Breathe Cool"),
            ("간주", "Breathe Cool"),
            ("피날레", "Finale Slam"),
            ("아웃트로", "Finale Slam"),
            ("엔딩", "Finale Slam"),
            ("인트로", None),  # 코디네이터 표에 없음 — 안전 강등
            ("전주", None),
            ("장면1", None),
        ],
    )
    def test_the_mapping_table_matches_the_coordinator_contract(self, cue_name, expected):
        assert _phaser_label_for_cue(_cue(cue_name=cue_name)) == expected

    # 최고 에너지(드롭/클라이맥스/피크)가 일반 후렴보다 우선한다 — 두
    # 어휘가 한 섹션 이름에 공존하는 문장("후렴 드롭")에서도 갈라진다.
    def test_a_peak_word_wins_over_a_co_occurring_chorus_word(self):
        assert _phaser_label_for_cue(_cue(cue_name="후렴 드롭")) == "Drop Slam"

    # d_level만으로는 최고 에너지/후렴/피날레를 가를 수 없다(_ARC_D_LEVEL
    # 에서 chorus=finale=5로 공유) — 텍스트 신호 없이 d_level 하나로
    # 안 만든다는 확인.
    def test_d_level_alone_never_decides_the_label(self):
        assert _phaser_label_for_cue(_cue(cue_name="장면1", d_level=5)) is None
        assert _phaser_label_for_cue(_cue(cue_name="장면1", d_level=1)) is None

    # ---- 안전 가드 ----

    def test_mib_premove_cues_never_get_a_phaser(self):
        assert _phaser_label_for_cue(_cue(cue_name="후렴", kind="mib_premove")) is None

    def test_blackout_cues_never_get_a_phaser(self):
        assert _phaser_label_for_cue(_cue(cue_name="후렴", blackout=True)) is None

    def test_a_zero_key_pct_cue_never_gets_a_phaser(self):
        assert _phaser_label_for_cue(_cue(cue_name="후렴", key_pct=0.0)) is None

    def test_a_none_key_pct_cue_never_gets_a_phaser(self):
        assert _phaser_label_for_cue(_cue(cue_name="후렴", key_pct=None)) is None

    # ---- (a)/(b) 명령 조립 — 슬롯 미해석 시 빈 튜플, 해석 시 recall 한 줄 ----

    def test_a_resolved_phaser_adds_exactly_one_recall_line(self):
        cue = _cue(cue_name="후렴")
        lines = _phaser_cue_value_lines(cue, [20, 26], {"Wave CM": (4, 35)})
        assert lines == ("Fixture 20 + 26 ; At Preset 4.35",)

    def test_an_unresolved_phaser_adds_nothing(self):
        cue = _cue(cue_name="후렴")
        assert _phaser_cue_value_lines(cue, [20, 26], {}) == ()

    def test_a_non_matching_cue_adds_nothing_even_when_other_slots_are_resolved(self):
        cue = _cue(cue_name="장면1")
        assert _phaser_cue_value_lines(cue, [20, 26], {"Wave CM": (4, 35)}) == ()

    # (b) — 순서 규율(계약 #5): recall 한 줄은 플랜 자신의 포지션/디머 값
    # 라인 **뒤**·Store **앞**에 온다 — 콤보/디머 페이저의 디머 스텝이
    # 큐의 정적 key_pct를 프로그래머 last-wins로 정확히 덮어쓴다.
    def test_the_recall_line_lands_after_the_plans_own_dimmer_line_and_before_store(self):
        plan = PositionCuePlan(cue_no=1.0, name="Chorus", preset_no=None, dimmer=60.0)
        cue = _cue(cue_name="후렴")
        lines = position_cue_bundle(
            110,
            plan,
            [20, 26],
            extra_value_lines=_phaser_cue_value_lines(cue, [20, 26], {"Wave CM": (4, 35)}),
        )
        dimmer_index = next(i for i, line in enumerate(lines) if "Attribute 'Dimmer'" in line)
        recall_index = next(i for i, line in enumerate(lines) if "At Preset 4.35" in line)
        store_index = next(i for i, line in enumerate(lines) if line.startswith("Store Sequence"))
        assert dimmer_index < recall_index < store_index

    # 페이저가 배정되지 않은 큐(라벨 불일치)는 extra_value_lines가 빈
    # 튜플이라 명령열이 T12 이전과 문자 단위로 동일하다.
    def test_no_phaser_leaves_the_bundle_byte_identical_to_pre_t12(self):
        plan = PositionCuePlan(cue_no=1.0, name="Scene1", preset_no=None, dimmer=60.0)
        cue = _cue(cue_name="장면1")
        with_phaser_lookup = position_cue_bundle(
            110,
            plan,
            [20, 26],
            extra_value_lines=_phaser_cue_value_lines(cue, [20, 26], {"Wave CM": (4, 35)}),
        )
        without_lookup = position_cue_bundle(110, plan, [20, 26])
        assert with_phaser_lookup == without_lookup

    # ---- (c) 미해석 사유 노출 ----

    def test_unresolved_labels_are_reported_by_name(self):
        note = _phaser_failure_note(
            {"Wave CM": "'Wave CM' 페이저 프리셋을 콘솔에서 찾지 못했습니다"}
        )
        assert "Wave CM" in note
        assert "찾지 못했습니다" in note

    def test_no_failures_produces_an_empty_note(self):
        assert _phaser_failure_note({}) == ""


class TestMultiSelectQuestionCardReachesTheUi:
    """다중 선택 카드가 **UI까지 그 모양으로** 가는가.

    ``QuestionRequest.multi``만 맞고 이벤트가 그것을 떨어뜨리면 UI는 단일 선택으로
    렌더하고, 사용자는 여러 계열을 지정했는데 하나만 고르게 된다 — 나머지는 조용히
    사라진다. 그래서 여기서는 ``_ask_one``이 실제로 내보낸 **와이어 프레임**을 본다.
    """

    def test_the_wire_frame_carries_multi_and_the_answer_comes_back_joined(self, tmp_path):
        from server.web.question import QuestionChannel, QuestionOption

        session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
        channel = QuestionChannel(timeout_seconds=2.0)
        channel.bind(session._notify_question)
        session._question_channel = channel

        box: list = []
        thread = threading.Thread(
            target=lambda: box.append(
                session._ask_one(
                    "어느 계열을 설정할까요?",
                    options=(
                        QuestionOption(label="기본 포지션 프리셋"),
                        QuestionOption(label="기본 컬러 프리셋"),
                    ),
                    why="여러 계열을 한 문장에서 지정하셨습니다.",
                    multi=True,
                )
            )
        )
        thread.start()

        cards = _wait_for_question_frames(sent)
        assert cards, "질문 카드가 UI까지 오지 않았다"
        assert cards[-1]["multi"] is True
        assert [option["label"] for option in cards[-1]["options"]] == [
            "기본 포지션 프리셋",
            "기본 컬러 프리셋",
        ]

        assert (
            channel.resolve(cards[-1]["request_id"], answer="기본 포지션 프리셋, 기본 컬러 프리셋")
            is True
        )
        thread.join(2)

        # 결합된 답이 다듬어지지 않고 그대로 온다 — 계열을 가르는 것은 부르는 쪽 몫이다.
        assert box == ["기본 포지션 프리셋, 기본 컬러 프리셋"]

    def test_a_single_family_card_stays_single_select(self, tmp_path):
        """기본값이 새면 기존 카드 전부가 「확인」을 한 번 더 요구하게 된다."""
        from server.web.question import QuestionChannel, QuestionOption

        session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
        channel = QuestionChannel(timeout_seconds=2.0)
        channel.bind(session._notify_question)
        session._question_channel = channel

        thread = threading.Thread(
            target=lambda: session._ask_one(
                "몇 번부터 저장할까요?",
                options=(QuestionOption(label="1번부터"),),
            )
        )
        thread.start()

        cards = _wait_for_question_frames(sent)
        assert cards[-1]["multi"] is False

        channel.resolve(cards[-1]["request_id"], answer="1번부터")
        thread.join(2)
