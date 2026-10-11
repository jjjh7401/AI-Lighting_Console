"""SPEC-LDBEAT-001 M4 — 상단 바 콘솔 버튼 셋이 **WebSocket 층을 실제로
지나서** 서버 연산에 닿는지 (카드 t563, REQ-LDBEAT-011~013/017).

``test_web_song_audio.py`` 모듈 독스트링과 같은 이유: ``parse_client_message``
가 새 타입을 통과시키는데 ``server/web/app.py`` 에 디스패치 분기가 없으면
메시지가 조용히 버려진다 — 세션 메서드를 직접 부르는 시험(예:
``test_beat_grid_send_t563.py``)은 이 층을 지나지 않아 그 회귀를 판정할 수
없다. 그래서 이 파일은 ``client.websocket_connect`` 를 반드시 지난다.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓰고 실기 포트로는 한 바이트도 나가지
않는다.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import PROTOCOL_VERSION
from server.web.timeline_library import SongTimelineLibrary

from .conftest import drain_until as _drain_until
from .conftest import recv_frame
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

_APPROVED_EVIDENCE = {"approval": {"by": "supervisor", "date": "2026-10-11", "source": "t563"}}


def _bar_map() -> dict:
    return {
        "bpm": 112.35,
        "time_signature": [4, 4],
        "bars": [
            {"bar": n, "start_ms": 1000 + (n - 1) * 2000, "beats_ms": [1000 + (n - 1) * 2000]}
            for n in range(1, 10)
        ],
    }


def _timeline() -> dict:
    return {
        "song_title": "LOVE ATTACK",
        "sequence_number": 210,
        "bar_map": _bar_map(),
        "timecode_number": 20,
        "beat_grid": {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [
                        {
                            "bar": 1,
                            "position_preset_no": "1.1",
                            "evidence": _APPROVED_EVIDENCE,
                        }
                    ],
                }
            ],
            "probe_results": {},
        },
    }


#: 카드 t600 — 이 시험들의 칸이 가리키는 프리셋 번호가 콘솔 풀에 **있는** 상태.
_EXISTING_PRESET_POOLS = {
    f"DataPool/PresetPools/{pool}": {
        "children": [{"i": i, "name": f"P{pool}.{i}"} for i in range(1, 6)]
    }
    for pool in (1, 2, 3, 4)
}


def _state_tree() -> dict:
    return {
        # 카드 t600 — 반영은 승인된 칸의 프리셋 번호도 콘솔 풀을 읽어 가른다(빈
        # 번호·못 읽은 풀은 송신 보류). 이 시험들이 쓰는 번호는 콘솔에 있는 프리셋이다.
        **_EXISTING_PRESET_POOLS,
        "DataPool/Sequences": {"children": []},
        "DataPool/Timecodes": {"children": [], "node": {"childCount": 0, "enumeration": "ok"}},
    }


def _deps(tmp_path) -> WebDeps:
    console = FakeConsole(state_tree=_state_tree())
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
    return deps


def _send(ws, **fields) -> None:
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


def _approve_until(ws, event_type: str, *, limit: int = 15) -> dict:
    """``event_type``까지 프레임을 읽되, 그 사이의 ``approval_request``는
    전부 수락한다(이 시험의 관심사는 디스패치 배선이지 승인 UX가
    아니다) — ``drain_until``과 같은 시간/회수 상한 이유."""
    for _ in range(limit):
        event = recv_frame(ws)
        if event["type"] == event_type:
            return event
        if event["type"] == "approval_request":
            _send(ws, type="approval_decision", request_id=event["request_id"], approved=True)
    raise AssertionError(f"no {event_type!r} within {limit} frames")


class TestBeatGridApplyOverTheWire:
    def test_apply_reaches_the_session_and_writes_to_the_console(self, tmp_path):
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "apply"
        assert status["ok"] is True
        assert status["approval_vs_sent"]["match"] is True


class TestBeatGridPreviewOverTheWire:
    def test_preview_before_apply_is_refused_with_no_console_send(self, tmp_path):
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_preview", bar=1)
            status = _drain_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "preview"
        assert status["ok"] is False

    def test_preview_after_apply_emits_goto_over_the_wire(self, tmp_path):
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            _approve_until(ws, "beat_grid_send_status")
            _send(ws, type="beat_grid_preview", bar=1)
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "preview"
        assert status["ok"] is True


class TestBeatGridPreviewOffOverTheWire:
    def test_preview_off_emits_off_sequence_over_the_wire(self, tmp_path):
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            _approve_until(ws, "beat_grid_send_status")
            _send(ws, type="beat_grid_preview_off")
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "preview_off"
        assert status["ok"] is True


class TestBeatGridPreviewMalformedFrame:
    def test_a_non_integer_bar_is_a_protocol_error(self, tmp_path):
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_preview", bar="one")
            event = _drain_until(ws, "error")
        assert event["kind"] == "protocol"
