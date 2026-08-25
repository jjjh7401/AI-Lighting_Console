"""t57 — 기존 한 장짜리 자리에 주입이 통하는지. 측정 후 삭제.

감사 D4 는 「비-status 3자리가 이 트리거로 원리적으로 갈릴 수 있는 유일한 후보」라는
plan M5 의 전제를 물려받았다. 그 전제를 검산한다.

기존 자리의 모양:  assert recv_frame(ws)["type"] == "<응답 타입>"
여기에 기대 밖 프레임을 밀어넣으면 무슨 일이 나는가를 네 칸으로 잰다.
단정 대신 결과를 기록해 표로 찍는다 — 프로브가 빨개지면 표를 못 보므로.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .conftest import drain_until, recv_frame
from .test_runner_self_correction import ScriptedProvider
from .test_web_app import _deps


def _case(tmp_path, *, inject: bool, mutated: bool) -> str:
    """자리 하나를 재현: (선택적 주입) -> 요청 -> 한 장 읽기 -> == "error" 단정."""
    deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        assert recv_frame(ws, timeout=3.0)["type"] == "status"
        if inject:
            notify = tuple(deps.status_listeners)[0]
            notify()
        ws.send_text("{ not json")
        if mutated:
            frame = drain_until(ws, "error")
        else:
            frame = recv_frame(ws, timeout=3.0)
        return "PASS" if frame["type"] == "error" else "FAIL(got " + frame["type"] + ")"


def test_injection_into_an_existing_single_read_site(tmp_path):
    rows = []
    for inject in (False, True):
        for mutated in (False, True):
            outcome = _case(tmp_path, inject=inject, mutated=mutated)
            rows.append((inject, mutated, outcome))
    for inject, mutated, outcome in rows:
        print("INJECT inject=" + str(inject) + " mutated=" + str(mutated) + " -> " + outcome)
