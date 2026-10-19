"""「콘솔 같이」 연속 마디 이동 — 콘솔 명령이 도는 동안 들어온 이동을 버리지 않는다.

실기 증상(리드, 2026-10-19): 재생 중 방향키를 여러 번 오가면 콘솔 커서가 앱 위치와 어긋나고
키를 눌러도 바로 반영되지 않는다. 서버는 콘솔 명령 한 개가 도는 동안 들어온 같은 종류의
메시지를 「처리 중」으로 거절한다(busy). 거절된 이동은 콘솔에 가지 않고 사라진다.

이 시험은 WebSocket 층을 실제로 지난다. 콘솔은 커서 쓰기마다 0.4초 걸리는 가짜다.
"""

from __future__ import annotations

import json
import re
import time

import pytest
from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import PROTOCOL_VERSION
from server.web.timeline_library import SongTimelineLibrary

from .conftest import recv_frame
from .test_beat_grid_reapply_t572 import _owned_state_tree, _seed_record, _timeline
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole


class _SlowCursorConsole(FakeConsole):
    """커서 쓰기 한 번에 0.4초 — 콘솔이 확인을 늦게 주는 상황을 흉내 낸다."""

    def execute(self, command):
        if "'Cursor'" in command:
            time.sleep(0.4)
        return super().execute(command)


def _deps(tmp_path) -> tuple[WebDeps, _SlowCursorConsole]:
    console = _SlowCursorConsole(state_tree=_owned_state_tree())
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=5.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    deps = WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    deps.song_timeline_store.latest = _timeline()
    _seed_record(deps.song_timeline_store)
    return deps, console


def _send(ws, **fields) -> None:
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


def _replies(ws, count: int, limit: int = 40) -> list[dict]:
    """답이 ``count`` 개 올 때까지 읽는다. 답은 상태 이벤트나 「처리 중」 거절이다.

    승인 카드는 그 자리에서 수락한다 — 이 시험의 관심사는 이동이 버려지는지지 승인 UX가 아니다.
    """
    out: list[dict] = []
    for _ in range(limit):
        event = recv_frame(ws)
        if event["type"] == "approval_request":
            _send(ws, type="approval_decision", request_id=event["request_id"], approved=True)
        elif event["type"] in ("beat_grid_send_status", "busy"):
            out.append(event)
            if len(out) == count:
                return out
    raise AssertionError(f"{count} replies not received within {limit} frames: {out}")


def _cursor_values(executed: list[str]) -> list[float]:
    values: list[float] = []
    for command in executed:
        match = re.search(r"'Cursor' ([0-9.]+)$", command)
        if match:
            values.append(float(match.group(1)))
    return values


def test_a_seek_sent_while_another_is_running_is_not_dropped(tmp_path) -> None:
    deps, console = _deps(tmp_path)
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        _send(ws, type="beat_grid_console_seek", seconds=10.0, playing=True)
        _replies(ws, 1)  # 첫 이동 — 세션 승인을 받는다
        _send(ws, type="beat_grid_console_seek", seconds=20.0, playing=True)
        _send(ws, type="beat_grid_console_seek", seconds=30.0, playing=True)  # 20초가 도는 동안
        replies = _replies(ws, 2)
    assert [r["type"] for r in replies] == ["beat_grid_send_status", "beat_grid_send_status"], (
        f"뒤의 이동이 「처리 중」으로 거절돼 콘솔에 가지 않았다: {replies}"
    )
    assert all(r["ok"] is True for r in replies), replies
    assert _cursor_values(console.executed)[-1] == pytest.approx(30.0, abs=0.5)


def test_while_one_seek_runs_only_the_newest_waiting_seek_reaches_the_console(tmp_path) -> None:
    deps, console = _deps(tmp_path)
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        _send(ws, type="beat_grid_console_seek", seconds=10.0, playing=True)
        _replies(ws, 1)  # 첫 이동 — 세션 승인을 받는다
        _send(ws, type="beat_grid_console_seek", seconds=20.0, playing=True)  # 콘솔에 쓰는 중
        _send(ws, type="beat_grid_console_seek", seconds=30.0, playing=True)  # 기다리다 밀린다
        _send(ws, type="beat_grid_console_seek", seconds=40.0, playing=True)  # 가장 새 것
        replies = _replies(ws, 3)
    assert all(r["type"] == "beat_grid_send_status" and r["ok"] is True for r in replies), replies
    values = _cursor_values(console.executed)
    assert values[-1] == pytest.approx(40.0, abs=0.5)
    assert not any(abs(v - 30.0) < 0.5 for v in values), f"밀린 30초가 콘솔에 써졌다: {values}"
