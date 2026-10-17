"""자동 배치 초안 요청이 같은 연결의 수신 루프를 막지 않는다(카드 WT-all-fixtures 실측 ① 1차 실패).

실측(2026-10-18, 브랜치 서버 47020): 초안 요청이 콘솔 그룹 18개 전부의 소속 장비와 장비 능력을
읽느라 58~100초 걸렸다. 수신 루프가 그 요청을 인라인으로 await 해서, 그동안 상태 요청에 답하지
못했다. 화면은 31초 뒤 연결을 새로 열었고, 초안 답은 이미 닫힌 옛 연결로 가서 화면에 끝내 오지
않았다(af-p1-ws.log: 16:36:40 propose → 16:37:12 WS open). 다른 느린 분기(반영·미리보기·분석)와
같은 백그라운드 작업으로 돌린다.
"""

from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from server.web.app import create_app
from server.web.session import ChatSession

from .conftest import drain_until as _drain_until
from .test_web_beat_grid_console_play_t578 import _deps
from .test_web_beat_grid_send_t563 import _send


def test_status_is_answered_while_a_draft_proposal_is_still_running(tmp_path, monkeypatch):
    release = threading.Event()
    started = threading.Event()

    def slow_propose(self):
        started.set()
        release.wait(timeout=20)
        return {}

    monkeypatch.setattr(ChatSession, "beat_grid_draft_propose", slow_propose)
    deps, _console = _deps(tmp_path, owned=False)
    try:
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_draft_propose")
            assert started.wait(timeout=5)
            _send(ws, type="status_request")
            assert _drain_until(ws, "status")["type"] == "status"
            # 두 번째 초안 요청은 여전히 가드된다 — busy.
            _send(ws, type="beat_grid_draft_propose")
            assert _drain_until(ws, "busy")["type"] == "busy"
            release.set()
    finally:
        release.set()
