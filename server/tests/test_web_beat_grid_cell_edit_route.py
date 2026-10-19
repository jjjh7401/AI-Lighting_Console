"""칸 옮기기 메시지가 WebSocket 층을 실제로 지나서 세션에 닿고, 백그라운드 작업으로 도는지
(SPEC-LDRHYTHM-001 TC5).

``test_web_draft_propose_not_blocking.py`` 와 같은 이유로 ``client.websocket_connect`` 를 지난다 —
세션 메서드를 직접 부르는 시험은 ``server/web/app.py`` 의 디스패치 분기 누락을 잡지 못한다.

세션 메서드 ``beat_grid_cell_edit`` 은 이 묶음에 없다(다음 묶음이 만든다). 그래서 ``ChatSession``
클래스에 기록기를 끼워서 시험한다(``raising=False`` — 아직 없는 이름이다). 칸 편집은 승인 왕복을
기다리며 콘솔에 쓰므로 수신 루프에서 인라인으로 await 하면 교착한다 — 이 파일은 그 길이 아니라
다른 콘솔 쓰기 버튼들과 같은 백그라운드 작업 길임을 본다. 콘솔 접촉 0건: ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from server.web.app import create_app
from server.web.session import ChatSession

from .conftest import drain_until as _drain_until
from .test_web_beat_grid_console_play_t578 import _deps
from .test_web_beat_grid_send_t563 import _send

_OPS = [{"op": "move", "group_name": "BACK", "bar": 3, "to_bar": 5}]
#: 이 버전이 지원하지 않는 일. 옮기기와 키가 똑같아서, 파서가 막을 이유는 op 하나뿐이다.
_CREATE_OPS = [{"op": "create", "group_name": "BACK", "bar": 3, "to_bar": 5}]


def test_the_frame_reaches_the_session_once_with_the_parsed_ops(tmp_path, monkeypatch):
    called = threading.Event()
    calls: list[object] = []
    stops: list[bool] = []

    def record(self, ops):
        calls.append(ops)
        called.set()

    monkeypatch.setattr(ChatSession, "beat_grid_cell_edit", record, raising=False)
    # 디스패치 분기 사슬의 마지막 ``else`` 는 콘솔 끄기다 — 칸 편집이 거기로 새면 Off 가 나간다.
    monkeypatch.setattr(ChatSession, "beat_grid_console_stop", lambda self: stops.append(True))
    deps, console = _deps(tmp_path, owned=False)
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        _send(ws, type="beat_grid_cell_edit", ops=_OPS)
        assert called.wait(timeout=5)
    assert calls == [_OPS]
    assert stops == []
    assert console.executed == []


def test_the_connection_keeps_receiving_while_the_edit_is_still_running(tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    calls: list[object] = []

    def blocking(self, ops):
        calls.append(ops)
        started.set()
        release.wait(timeout=8)
        finished.set()

    monkeypatch.setattr(ChatSession, "beat_grid_cell_edit", blocking, raising=False)
    deps, _console = _deps(tmp_path, owned=False)
    try:
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            # 접속 때 서버가 먼저 보내는 상태 프레임을 치운다 — 아래 상태 요청의 답과 섞이지 않게.
            _drain_until(ws, "status")
            _send(ws, type="beat_grid_cell_edit", ops=_OPS)
            assert started.wait(timeout=5)
            _send(ws, type="status_request")
            _drain_until(ws, "status")
            # 상태 답이 온 때 기록기는 아직 막혀 있다 — 수신 루프가 편집이 끝나길 기다리지 않았다.
            assert not finished.is_set()
            # 같은 연결의 두 번째 칸 편집은 다른 쓰기 버튼들처럼 busy 로 막힌다.
            _send(ws, type="beat_grid_cell_edit", ops=_OPS)
            assert _drain_until(ws, "busy")["type"] == "busy"
            release.set()
    finally:
        release.set()
    assert len(calls) == 1


def test_a_refused_frame_never_reaches_the_session(tmp_path, monkeypatch):
    called = threading.Event()
    calls: list[object] = []

    def record(self, ops):
        calls.append(ops)
        called.set()

    monkeypatch.setattr(ChatSession, "beat_grid_cell_edit", record, raising=False)
    deps, console = _deps(tmp_path, owned=False)
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        # 대조군 — 유효한 프레임은 닿는다. 이게 없으면 타입이 목록에 없는 때도 이 시험이 통과한다.
        _send(ws, type="beat_grid_cell_edit", ops=_OPS)
        assert called.wait(timeout=5)
        # 이 버전이 지원하지 않는 만들기는 파서에서 막혀 세션까지 가지 않는다.
        _send(ws, type="beat_grid_cell_edit", ops=_CREATE_OPS)
        assert _drain_until(ws, "error")["kind"] == "protocol"
    assert calls == [_OPS]
    assert console.executed == []
