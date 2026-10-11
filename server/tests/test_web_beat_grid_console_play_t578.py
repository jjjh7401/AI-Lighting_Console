"""「콘솔 같이」 재생·정지가 **WebSocket 층을 실제로 지나서** 세션에 닿는지
(카드 t578, REQ-LDBEAT-024(a)).

``test_web_beat_grid_send_t563.py``와 같은 이유: 세션 메서드를 직접 부르는 시험은
``server/web/app.py`` 디스패치 분기 누락을 잡지 못한다. 그래서 이 파일은
``client.websocket_connect``를 반드시 지난다. 콘솔 접촉 0건 — ``FakeConsole``만 쓴다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.timeline_library import SongTimelineLibrary

from .conftest import drain_until as _drain_until
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole
from .test_web_beat_grid_send_t563 import _approve_until, _send, _state_tree, _timeline

_TIMECODE = 20
_TIMECODE_NAME = "LDBEAT Timecode 20"


def _deps(tmp_path, *, owned: bool) -> tuple[WebDeps, FakeConsole]:
    """``test_web_beat_grid_send_t563._deps``와 같은 조립이되, 가짜 콘솔을 밖에서
    들고 있어 실제로 나간 줄을 읽는다. ``owned``이면 t572 소유 기록과 그 이름의
    타임코드를 콘솔에 심는다."""
    state_tree = _state_tree()
    if owned:
        state_tree["DataPool/Timecodes"] = {
            "children": [{"i": _TIMECODE, "name": _TIMECODE_NAME}],
            "node": {"childCount": 1},
        }
    console = FakeConsole(state_tree=state_tree)
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
    if owned:
        deps.song_timeline_store.set_beat_grid_allocation(
            ("LOVE ATTACK", 210),
            {"timecode_number": _TIMECODE, "timecode_name": _TIMECODE_NAME, "tracks": {}},
        )
    return deps, console


class TestConsolePlayOverTheWire:
    def test_play_without_an_apply_record_is_refused(self, tmp_path):
        deps, console = _deps(tmp_path, owned=False)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_console_play")
            status = _drain_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "console_play"
        assert status["ok"] is False
        assert console.executed == []

    def test_play_reaches_the_console_with_top_then_go(self, tmp_path):
        deps, console = _deps(tmp_path, owned=True)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_console_play")
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "console_play"
        assert status["ok"] is True
        executed = [c for c in console.executed if "Timecode" in c]
        assert executed == [f"Top Timecode {_TIMECODE}", f"Go Timecode {_TIMECODE}"]


class TestConsoleStopOverTheWire:
    def test_stop_reaches_the_console_with_off(self, tmp_path):
        deps, console = _deps(tmp_path, owned=True)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_console_stop")
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "console_stop"
        assert status["ok"] is True
        assert [c for c in console.executed if "Timecode" in c] == [f"Off Timecode {_TIMECODE}"]
