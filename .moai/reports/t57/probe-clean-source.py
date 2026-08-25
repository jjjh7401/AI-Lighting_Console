"""t57 무계측 프로브 — monkeypatch 를 하나도 안 쓴다. 측정 후 삭제.

§9 의 20/20 은 _safe_send 의 suppress 를 벗기고 run_coroutine_threadsafe 를
감싼 상태에서 잰 값이다. 실제 검사는 그 계측기를 달 수 없다.
그래서 계측기 없이 같은 값이 나오는지 여기서 확인한다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .conftest import recv_frame
from .test_runner_self_correction import ScriptedProvider
from .test_web_app import _deps


def _try(ws, timeout=3.0):
    try:
        return recv_frame(ws, timeout=timeout)
    except AssertionError:
        return None


def test_clean_trigger_arrival_and_ordering(tmp_path):
    deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
    orders = []
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        first = recv_frame(ws, timeout=3.0)
        assert first["type"] == "status", first
        listeners = tuple(deps.status_listeners)
        assert len(listeners) == 1, listeners
        notify = listeners[0]
        for _ in range(20):
            notify()
            ws.send_text("{ not json")
            a = _try(ws)
            b = _try(ws)
            orders.append((a["type"] if a else None, b["type"] if b else None))
    print("CLEAN pairs=" + str(sorted(set(orders))))
    print("CLEAN status_first=" + str(sum(1 for a, _ in orders if a == "status")) + "/20")


def test_clean_negative_control_no_trigger(tmp_path):
    """음성 대조군 — 트리거를 안 부르면 첫 프레임은 status 가 아니어야 한다."""
    deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
    kinds = []
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        assert recv_frame(ws, timeout=3.0)["type"] == "status"
        for _ in range(20):
            ws.send_text("{ not json")
            a = _try(ws)
            kinds.append(a["type"] if a else None)
    print("CLEAN-NEG first_frames=" + str(sorted(set(kinds))))
    print("CLEAN-NEG status_count=" + str(sum(1 for k in kinds if k == "status")) + "/20")
