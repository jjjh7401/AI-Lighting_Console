"""서랍 열기가 같은 연결의 느린 읽기(무대 판독)에 막히지 않는다(카드 t677 후속).

실측: 새 페이지가 열리면 UI 가 `beat_grid_stage_request` 를 보내고, 무대 판독은 장비 수만큼
콘솔을 왕복해 40초를 넘긴다. 예전엔 수신 루프가 그 판독을 인라인으로 await 해서 다음
메시지(`beat_grid_drawer_request`)가 처리되지 않았다 — `busy` 응답조차 없이 영원히 「불러오는 중」.
"""

from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from server.web.app import create_app
from server.web.session import ChatSession

from .conftest import drain_until as _drain_until
from .test_web_beat_grid_console_play_t578 import _deps
from .test_web_beat_grid_send_t563 import _send


def test_drawer_answers_while_a_stage_read_is_still_running(tmp_path, monkeypatch):
    release = threading.Event()
    started = threading.Event()

    def slow_stage(self):
        started.set()
        release.wait(timeout=20)
        return {}

    monkeypatch.setattr(ChatSession, "beat_grid_stage", slow_stage)
    deps, _console = _deps(tmp_path, owned=False)
    try:
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_stage_request")
            assert started.wait(timeout=5)
            _send(ws, type="beat_grid_drawer_request")
            event = _drain_until(ws, "beat_grid_drawer")
            assert [s["pool_name"] for s in event["sections"]] == ["Dimmer", "Position", "Color"]
            release.set()
    finally:
        release.set()


def test_drawer_answers_while_a_write_task_is_busy(tmp_path, monkeypatch):
    release = threading.Event()
    started = threading.Event()

    def slow_apply(self):
        started.set()
        release.wait(timeout=20)

    monkeypatch.setattr(ChatSession, "beat_grid_console_stop", slow_apply)
    deps, _console = _deps(tmp_path, owned=False)
    try:
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_console_stop")
            assert started.wait(timeout=5)
            _send(ws, type="beat_grid_drawer_request")
            event = _drain_until(ws, "beat_grid_drawer")
            assert event["type"] == "beat_grid_drawer"
            # 쓰기 쪽은 여전히 가드된다 — 두 번째 쓰기는 busy.
            _send(ws, type="beat_grid_console_stop")
            assert _drain_until(ws, "busy")["type"] == "busy"
            release.set()
    finally:
        release.set()
