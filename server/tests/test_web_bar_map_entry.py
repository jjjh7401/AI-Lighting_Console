"""M3 — 마디 지도 분석 프레임을 WebSocket 층을 실제로 지나서 판정한다 (SPEC-LDBARMAP-002, t647).

AC-LDBARENTRY-001(첨부 오디오 없음) · 009(처리 중이면 busy) · 010(분석 중에도 수신 루프가 산다)
· 015 의 와이어 쪽 세 경우(분석에 도달하지 못한 요청은 ``chat_response`` 0개). 합성 단계
(``synthesize_bar_map``)는 ``test_audio_bar_map_entry.py``, 세션 메서드는
``test_session_bar_map_entry.py``, 파서는 ``test_messages_bar_map_entry.py`` 가 잰다.

이 파일의 존재 이유는 층이다. 세션 메서드를 직접 부르는 시험은 ``server/web/app.py`` 의 디스패치
분기를 지우고도 통과한다. 그래서 아래 시험은 ``client.websocket_connect`` 를 지나고, 진입 메서드
(``ChatSession.analyse_bar_map``)는 실제 합성을 돌리지 않는 대역으로 바꿔 끼운다 — 여기서 재는
것은 분석이 아니라 프레임이 분기에 닿는가, 수신 루프가 막히지 않는가, 예외가 새도 응답이 나가는가다.

대역의 대기에는 모두 명시적 시간 상한이 있다(``HOLD_SECONDS``) — ``pyproject.toml`` 의
``faulthandler_timeout = 60`` 이 멈춘 시험을 프로세스째 끊기 때문이다.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import _BUSY_MESSAGE, WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import PROTOCOL_VERSION, chat_response_event
from server.web.session import (
    _BAR_MAP_ENTRY_FAILED_TEXT,
    _BAR_MAP_ENTRY_REJECTED_SUMMARY,
    ChatSession,
)

from .conftest import drain_until as _receive_until
from .conftest import recv_frame
from .fixtures.audio import synthesize_track
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

SMALL_WAV_B64 = base64.b64encode(synthesize_track(duration_ms=3000)).decode("ascii")

#: 대역이 풀림을 기다리는 명시적 상한(초). 시험이 풀어 주지 못한 채 깨져도 작업 스레드는 이
#: 시간 뒤에 끝난다.
HOLD_SECONDS = 20.0

#: AC-LDBARENTRY-010 의 시간 상한(초) — 분석 중 ``status_request`` 의 답이 이 안에 와야 한다.
STATUS_BOUND_SECONDS = 5.0

#: 대역이 보내는 ``chat_response`` 의 요약 — 래퍼가 대신 보낸 것과 가르는 표지다.
STUB_SUMMARY = "대역 응답"

#: 대역이 내는 예외 문구. 객체 주소 모양을 일부러 담는다 — 어떤 조각도 프레임에 새면 안 된다.
RAW_EXCEPTION_TEXT = "대역 폭발: <object object at 0x7f00dead> 0xBAD"

#: 래퍼가 예외를 남기는 로거 — 원문은 프레임이 아니라 여기에 간다.
APP_LOGGER = "server.web.app"


# ---------------------------------------------------------------------------
# 시험 틀 — test_web_song_audio.py 와 같은 모양(TestClient + create_app + recv_frame).
# ---------------------------------------------------------------------------


def _deps(tmp_path: Path) -> WebDeps:
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    return WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
    )


def _send(ws, **fields: object) -> None:
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


def _collect_until(ws, *event_types: str, limit: int = 30, timeout: float = 10.0) -> list[dict]:
    """``event_types`` 중 하나가 나올 때까지 받은 프레임 전부(그 프레임 포함) — 시간 상한 위에서.

    ``drain_until`` 은 앞서 온 프레임을 버린다. 여기서는 「그 사이에 무엇이 왔는가」를 세야 한다."""
    frames: list[dict] = []
    for _ in range(limit):
        frame = recv_frame(ws, timeout=timeout)
        frames.append(frame)
        if frame["type"] in event_types:
            return frames
    raise AssertionError(f"no {event_types!r} frame within {limit} frames: {_types(frames)}")


def _settle(ws) -> list[dict]:
    """``status_request`` 를 보내 ``status`` 답이 올 때까지의 프레임 전부.

    수신 루프가 먼저 처리한 프레임의 답은 이 답보다 앞서 온다 — 「0개」를 단언하기 전에 흘려
    보내는 장치다. 안 오는 프레임을 시간 제한으로 기다리면 읽는 스레드가 남아 다음 수신을
    어지럽힌다."""
    _send(ws, type="status_request")
    return _collect_until(ws, "status")


def _types(frames: list[dict]) -> list[str]:
    return [frame["type"] for frame in frames]


def _chat_responses(frames: list[dict]) -> list[dict]:
    return [frame for frame in frames if frame["type"] == "chat_response"]


class _EntryStub:
    """``ChatSession.analyse_bar_map`` 의 대역 — 합성·저장 없이 불린 오프셋만 ``calls`` 에 기록한다.

    ``mode`` 가 거동을 고른다.

    * ``refuse``: 불리면 안 된다. 기록한 뒤 ``AssertionError`` 를 낸다.
    * ``reply``: 곧바로 ``chat_response`` 하나를 보낸다.
    * ``hold``: 첫 호출은 ``release`` 가 설 때까지(``HOLD_SECONDS`` 상한) 멈췄다가 ``chat_response``
      하나를 보내고 끝난다. 그 뒤 호출은 곧바로 보낸다.
    * ``raise``: 첫 호출은 응답을 보내기 전에 예외를 낸다. 그 뒤 호출은 곧바로 보낸다.
    * ``reply_then_raise``: 첫 호출은 ``chat_response`` 를 보낸 **뒤** 예외를 낸다.
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.calls: list[int] = []
        self.entered = threading.Event()  # 첫 호출이 대역 안에 들어왔다
        self.release = threading.Event()  # 시험이 풀어 준다

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        stub = self

        def analyse_bar_map(session: ChatSession, first_beat_offset: int) -> None:
            stub.run(session, first_beat_offset)

        monkeypatch.setattr(ChatSession, "analyse_bar_map", analyse_bar_map)

    def run(self, session: ChatSession, first_beat_offset: int) -> None:
        self.calls.append(first_beat_offset)
        first_call = len(self.calls) == 1
        if self.mode == "refuse":
            raise AssertionError("진입 메서드가 불려서는 안 된다")
        if self.mode == "hold" and first_call:
            self.entered.set()
            self.release.wait(timeout=HOLD_SECONDS)
        if self.mode == "raise" and first_call:
            raise RuntimeError(RAW_EXCEPTION_TEXT)
        session._send(
            chat_response_event(status="ok", summary=STUB_SUMMARY, text="대역", commands=[])
        )
        if self.mode == "reply_then_raise" and first_call:
            raise RuntimeError(RAW_EXCEPTION_TEXT)


@pytest.fixture
def entry_stub(monkeypatch: pytest.MonkeyPatch):
    """대역을 만들어 꽂는다. 시험이 어떻게 끝나도 멈춰 있는 작업 스레드를 풀어 준다."""
    made: list[_EntryStub] = []

    def make(mode: str) -> _EntryStub:
        stub = _EntryStub(mode)
        stub.install(monkeypatch)
        made.append(stub)
        return stub

    yield make
    for stub in made:
        stub.release.set()


@contextmanager
def _connected(tmp_path: Path, *, attach_audio: bool, stub: _EntryStub | None = None) -> Iterator:
    """WS 하나. ``attach_audio`` 면 곡 오디오를 와이어로 올려 ``notice`` 까지 받는다.

    ``stub`` 을 주면 본문이 어떻게 끝나든 소켓을 닫기 **전에** 풀어 준다 — 수신 루프가 대역을
    기다리며 막혀 있으면(AC-LDBARENTRY-010 이 깨진 경우) 닫기가 그 상한까지 기다리기 때문이다."""
    with (
        TestClient(create_app(_deps(tmp_path))) as client,
        client.websocket_connect("/ws") as ws,
    ):
        try:
            recv_frame(ws)  # 최초 status
            if attach_audio:
                _send(
                    ws,
                    type="song_audio_upload",
                    file_name="track.wav",
                    mime_type="audio/wav",
                    content_base64=SMALL_WAV_B64,
                )
                _receive_until(ws, "notice")
            yield ws
        finally:
            if stub is not None:
                stub.release.set()


def _hold_one_and_send_a_second(ws, stub: _EntryStub) -> list[dict]:
    """첫 요청을 대역 안에 붙잡아 두고 두 번째 요청을 보낸다. 풀리기 전에 받은 프레임을 돌려준다."""
    _send(ws, type="bar_map_analyse", first_beat_offset=0)
    assert stub.entered.wait(timeout=5.0), "첫 요청이 진입 메서드에 들어가지 못했다"
    _send(ws, type="bar_map_analyse", first_beat_offset=1)
    frames = _collect_until(ws, "busy")
    return frames + _settle(ws)


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-001 — 첨부 오디오 없음.
# ---------------------------------------------------------------------------


def test_ac001_no_attached_audio_is_a_named_error_and_the_connection_survives(
    tmp_path: Path, entry_stub
) -> None:
    """종류(``kind``)를 단언하는 것이 이 시험의 전부다 — 종류를 안 재면 허용 목록에 타입이 없는
    상태의 ``kind == "protocol"`` 오류와 구별되지 않는다(``test_web_song_audio.py`` 가 같은
    함정을 적었다)."""
    stub = entry_stub("refuse")
    with _connected(tmp_path, attach_audio=False) as ws:
        _send(ws, type="bar_map_analyse", first_beat_offset=1)
        event = recv_frame(ws)
        assert event["type"] == "error"
        assert event["kind"] == "song_audio_missing"
        assert "첨부" in event["message"]
        assert stub.calls == []
        # 연결이 살아 있다 — 그리고 그 사이에 다른 프레임이 끼지 않았다.
        assert _types(_settle(ws)) == ["status"]


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-009 — 처리 중이면 busy.
# ---------------------------------------------------------------------------


def test_ac009_a_second_request_while_busy_gets_busy_and_a_later_one_is_accepted(
    tmp_path: Path, entry_stub
) -> None:
    stub = entry_stub("hold")
    with _connected(tmp_path, attach_audio=True, stub=stub) as ws:
        before_release = _hold_one_and_send_a_second(ws, stub)
        [busy] = [frame for frame in before_release if frame["type"] == "busy"]
        assert busy["message"] == _BUSY_MESSAGE  # (1)
        assert _chat_responses(before_release) == []
        assert stub.calls == [0]  # (2) 두 번째 프레임(오프셋 1)은 대역에 닿지 않았다

        # (3) 푼다 — 대역은 chat_response 하나를 보내고 끝난다.
        stub.release.set()
        first = _collect_until(ws, "chat_response")
        assert first[-1]["summary"] == STUB_SUMMARY
        # 첫 작업이 끝나기 전에 보내면 또 busy 가 올 수 있다 — status 답을 받은 뒤에 보낸다.
        assert _types(_settle(ws))[-1] == "status"
        _send(ws, type="bar_map_analyse", first_beat_offset=2)
        third = _collect_until(ws, "chat_response", "busy")
        assert _types(third) == ["chat_response"]
        assert stub.calls == [0, 2]


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-010 — 분석 중에도 수신 루프가 산다.
# ---------------------------------------------------------------------------


def test_ac010_status_request_is_answered_while_the_analysis_is_in_flight(
    tmp_path: Path, entry_stub
) -> None:
    """디스패치 분기를 ``await asyncio.to_thread(...)`` 로 바꾸면 이 시험은 시간 상한에서 실패한다
    (수신 루프가 대역을 기다리며 막혀 ``status`` 답이 오지 않는다) — 비공허 조건이다."""
    stub = entry_stub("hold")
    with _connected(tmp_path, attach_audio=True, stub=stub) as ws:
        _send(ws, type="bar_map_analyse", first_beat_offset=0)
        assert stub.entered.wait(timeout=5.0), "첫 요청이 진입 메서드에 들어가지 못했다"
        started = time.monotonic()
        _send(ws, type="status_request")
        frames = _collect_until(ws, "status", timeout=STATUS_BOUND_SECONDS)
        elapsed = time.monotonic() - started
        assert not stub.release.is_set()  # 대역이 풀리기 전에 도착했다
        assert elapsed < STATUS_BOUND_SECONDS
        assert _chat_responses(frames) == []


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-015 (와이어 쪽) — 분석에 도달하지 못한 요청은 chat_response 를 0개 보낸다.
# ---------------------------------------------------------------------------


def test_ac015_a_no_attached_audio_answers_an_error_and_no_chat_response(
    tmp_path: Path, entry_stub
) -> None:
    stub = entry_stub("refuse")
    with _connected(tmp_path, attach_audio=False) as ws:
        _send(ws, type="bar_map_analyse", first_beat_offset=0)
        frames = _collect_until(ws, "error") + _settle(ws)
        assert (frames[0]["type"], frames[0]["kind"]) == ("error", "song_audio_missing")
        assert _chat_responses(frames) == []
        assert stub.calls == []


def test_ac015_b_busy_answers_busy_and_no_chat_response_before_the_release(
    tmp_path: Path, entry_stub
) -> None:
    """0개는 대역을 풀기 **전까지** 받은 프레임만 센다 — 풀리면 대역이 응답 하나를 보낸다."""
    stub = entry_stub("hold")
    with _connected(tmp_path, attach_audio=True, stub=stub) as ws:
        frames = _hold_one_and_send_a_second(ws, stub)
        assert "busy" in _types(frames)
        assert _chat_responses(frames) == []
        assert stub.calls == [0]  # 첫 요청 몫의 1


def test_ac015_c_a_frame_without_an_offset_answers_a_protocol_error_and_no_chat_response(
    tmp_path: Path, entry_stub
) -> None:
    # 오디오가 붙어 있어야 한다 — 파서가 0 으로 채워 통과시키면 대역이 불려 이 시험이 실패한다.
    stub = entry_stub("refuse")
    with _connected(tmp_path, attach_audio=True) as ws:
        _send(ws, type="bar_map_analyse")
        frames = _collect_until(ws, "error") + _settle(ws)
        assert (frames[0]["type"], frames[0]["kind"]) == ("error", "protocol")
        assert _chat_responses(frames) == []
        assert stub.calls == []


# ---------------------------------------------------------------------------
# 디스패치가 오프셋을 그대로 넘긴다 — 범위 판정은 세션의 몫이다(AC-LDBARENTRY-003).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset", [-1, 0, 1, 2, 3, 4])
def test_the_frames_offset_reaches_the_session_method_unchanged(
    tmp_path: Path, entry_stub, offset: int
) -> None:
    stub = entry_stub("reply")
    with _connected(tmp_path, attach_audio=True) as ws:
        _send(ws, type="bar_map_analyse", first_beat_offset=offset)
        frames = _collect_until(ws, "chat_response", "error")
    assert _types(frames)[-1] == "chat_response"
    assert stub.calls == [offset]


# ---------------------------------------------------------------------------
# 래퍼 — 세션 메서드에서 예외가 새도 응답은 정확히 하나, 원문은 로그에만.
# ---------------------------------------------------------------------------


def _request_until_accepted(ws, offset: int, *, attempts: int = 20) -> list[dict]:
    """분석 요청을 보내 받아들여질 때까지 — busy 면 잠깐 기다렸다 다시 보낸다.

    앞 작업이 예외 처리를 마치고 끝나는 짧은 창을 건너기 위한 것이다. 계속 busy 면 앞 작업이
    끝나지 않은 것이라 실패한다. 받아들여졌다는 것은 앞 작업의 모든 전송이 끝났다는 뜻이다."""
    for _ in range(attempts):
        _send(ws, type="bar_map_analyse", first_beat_offset=offset)
        frames = _collect_until(ws, "chat_response", "busy")
        if frames[-1]["type"] != "busy":
            return frames
        time.sleep(0.05)
    raise AssertionError(f"{attempts}번 보내도 계속 busy 다 — 앞 작업이 끝나지 않았다")


def _warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == APP_LOGGER and record.levelno == logging.WARNING
    ]


def test_an_exception_before_any_reply_is_answered_with_one_general_chat_response(
    tmp_path: Path, entry_stub, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=APP_LOGGER)
    stub = entry_stub("raise")
    with _connected(tmp_path, attach_audio=True) as ws:
        _send(ws, type="bar_map_analyse", first_beat_offset=0)
        frames = _collect_until(ws, "chat_response")
        frames += _settle(ws)
        frames += _request_until_accepted(ws, 1)  # 예외가 작업 상태를 망가뜨리지 않았다

    responses = _chat_responses(frames)
    assert len(responses) == 2, _types(frames)
    # 첫 응답은 래퍼가 대신 보낸 것 — 세션 자신의 분석 실패 응답과 같은 모양이다.
    assert responses[0] == chat_response_event(
        status="ok",
        summary=_BAR_MAP_ENTRY_REJECTED_SUMMARY,
        text=_BAR_MAP_ENTRY_FAILED_TEXT,
        commands=[],
    )
    assert responses[1]["summary"] == STUB_SUMMARY  # 두 번째 요청은 정상으로 돌았다
    assert stub.calls == [0, 1]
    # 예외 문구의 어떤 조각도 프레임에 없다.
    serialized = json.dumps(frames, ensure_ascii=False)
    for fragment in ("대역 폭발", "0x", "object at", "RuntimeError"):
        assert fragment not in serialized, fragment
    # 원문은 로그에 있다 — WARNING, 트레이스백 포함.
    [record] = _warnings(caplog)
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError
    assert RAW_EXCEPTION_TEXT in caplog.text


def test_an_exception_after_the_session_already_replied_adds_no_second_chat_response(
    tmp_path: Path, entry_stub, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=APP_LOGGER)
    stub = entry_stub("reply_then_raise")
    with _connected(tmp_path, attach_audio=True) as ws:
        _send(ws, type="bar_map_analyse", first_beat_offset=0)
        frames = _collect_until(ws, "chat_response")
        frames += _request_until_accepted(ws, 1)  # 받아들여진 뒤에는 첫 작업의 전송이 모두 끝났다

    responses = _chat_responses(frames)
    assert len(responses) == 2, _types(frames)
    assert [response["summary"] for response in responses] == [STUB_SUMMARY, STUB_SUMMARY]
    assert all(response["text"] != _BAR_MAP_ENTRY_FAILED_TEXT for response in responses)
    assert stub.calls == [0, 1]
    [record] = _warnings(caplog)  # 응답은 막지 않지만 예외는 로그에 남는다
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError
