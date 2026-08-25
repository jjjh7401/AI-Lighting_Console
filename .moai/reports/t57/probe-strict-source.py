"""t57 무계측 · 무감싸개 프로브 — 측정 후 삭제.

감사 D10: 이전 CLEAN 프로브는 초과를 삼켜 None 으로 바꾸는 _try 감싸개로
판독했고, 그 형태는 AC-RECVOBS-014 가 출하 검사에서 금지한다.
여기서는 recv_frame 을 맨몸으로 부른다 — 초과하면 AssertionError 로 터진다.
즉 출하 검사가 실제로 쓸 수 있는 판독 방식으로 같은 값을 잰다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .conftest import recv_frame
from .test_runner_self_correction import ScriptedProvider
from .test_web_app import _deps


def test_strict_trigger_ordering_no_swallowing(tmp_path):
    deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
    orders = []
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        assert recv_frame(ws, timeout=3.0)["type"] == "status"
        listeners = tuple(deps.status_listeners)
        assert len(listeners) == 1, listeners
        notify = listeners[0]
        for _ in range(20):
            notify()
            ws.send_text("{ not json")
            a = recv_frame(ws, timeout=3.0)
            b = recv_frame(ws, timeout=3.0)
            orders.append((a["type"], b["type"]))
    print("STRICT pairs=" + str(sorted(set(orders))))
    print("STRICT status_first=" + str(sum(1 for a, _ in orders if a == "status")) + "/20")


def test_strict_negative_control_no_swallowing(tmp_path):
    deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
    kinds = []
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        assert recv_frame(ws, timeout=3.0)["type"] == "status"
        for _ in range(20):
            ws.send_text("{ not json")
            kinds.append(recv_frame(ws, timeout=3.0)["type"])
    print("STRICT-NEG first_frames=" + str(sorted(set(kinds))))
    print("STRICT-NEG status_count=" + str(sum(1 for k in kinds if k == "status")) + "/20")
