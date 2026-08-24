"""세션이 진행 한 줄을 **실제로 내보낸다** — 러너와 웹소켓 사이의 이음매.

느슨한 이음매의 계약: ``server/orchestrator/runner.py``\\ 는 선택적
``ProgressSink`` 하나만 알고 웹소켓·프로토콜·이벤트 모양은 모른다. 그것을
``send_event``\\ 로 잇는 일은 ``ChatSession._emit_progress``\\ 가 한다. 여기서
재는 것은 그 이음매가 **정말 연결돼 있는지**\\ 다 — 러너 단위 테스트가 통과해도
세션이 싱크를 주입하지 않으면 화면에는 여전히 아무것도 도착하지 않는다.

실측 근거: 종전에는 턴이 전부 끝난 뒤 ``chat_response`` 하나뿐이었고, 그 사이
모델 호출 최대 24회 + 도구당 수백 콘솔 왕복(``get_spatial_context`` 1회 =
240~420왕복 = 16~28초) 동안 프레임이 0개였다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.web.app import create_app
from server.web.messages import PROTOCOL_VERSION

from .conftest import recv_frame
from .test_runner_self_correction import ScriptedProvider, _final, _run_turn
from .test_web_app import _deps, _send
from .test_web_session import _session


def _progress(sent: list[dict]) -> list[dict]:
    return [event for event in sent if event["type"] == "progress"]


@pytest.fixture
def turn(tmp_path):
    """하나의 도구 라운드 + 마지막 글로 끝나는 세션 하나."""
    provider = ScriptedProvider([_run_turn(["Store Group 3"], "c1"), _final()])
    session, console, _audit, sent, _channel = _session(tmp_path, provider)
    return session, console, sent


class TestTheTurnStreamsBeforeItEnds:
    def test_progress_events_precede_the_final_chat_response(self, turn):
        session, _console, sent = turn
        session.run_instruction("3번 그룹 저장해줘")
        types = [event["type"] for event in sent]
        assert "progress" in types, "진행 이벤트가 0건이면 화면은 종전처럼 정지한다"
        assert types.index("progress") < types.index("chat_response")

    def test_every_frame_carries_the_shared_payload_shape(self, turn):
        session, _console, sent = turn
        session.run_instruction("3번 그룹 저장해줘")
        events = _progress(sent)
        assert events
        for event in events:
            assert event["v"] == PROTOCOL_VERSION
            assert event["type"] == "progress"
            assert event["phase"] in ("model_call", "tool_start", "tool_done")
            assert isinstance(event["detail"], str) and event["detail"].strip()
            assert isinstance(event["seq"], int)

    def test_seq_is_monotonic_within_the_turn_and_restarts_on_the_next(self, tmp_path):
        provider = ScriptedProvider(
            [
                _run_turn(["Store Group 3"], "c1"),
                _final(),
                _run_turn(["Store Group 4"], "c2"),
                _final(),
            ]
        )
        session, _console, _audit, sent, _channel = _session(tmp_path, provider)
        session.run_instruction("3번 그룹 저장해줘")
        first = [event["seq"] for event in _progress(sent)]
        assert first == list(range(1, len(first) + 1))
        boundary = len(sent)
        session.run_instruction("4번 그룹도 저장해줘")
        second = [event["seq"] for event in _progress(sent[boundary:])]
        assert second == list(range(1, len(second) + 1))

    def test_the_tool_phases_name_the_work_in_korean(self, turn):
        session, _console, sent = turn
        session.run_instruction("3번 그룹 저장해줘")
        started = [e["detail"] for e in _progress(sent) if e["phase"] == "tool_start"]
        done = [e["detail"] for e in _progress(sent) if e["phase"] == "tool_done"]
        assert started == ["콘솔에 명령 전송…"]
        assert done == ["콘솔에 명령 전송 완료"]
        # 영어 도구 이름은 조명 감독의 어휘가 아니다 — 어디에도 새지 않는다.
        assert all("run_commands" not in e["detail"] for e in _progress(sent))

    def test_progress_adds_no_console_round_trip(self, turn):
        """진행 표시는 **이미 일어나는 일에 이름을 붙이는 것**\\ 이다.

        게이트 감사는 콘솔 왕복 1:1 기록이므로, 진행 이벤트가 왕복을 하나라도
        더 만들면 감사 기록도 함께 늘어난다. 늘지 않아야 한다.
        """
        session, console, _sent = turn
        session.run_instruction("3번 그룹 저장해줘")
        assert console.executed == ["Store Group 3"]


class TestTheFinalReportIsUnchanged:
    """진행 스트리밍은 **덧붙이는** 것이다 — 기존 종결 프레임을 건드리지 않는다."""

    def test_exactly_one_chat_response_still_ends_the_turn(self, turn):
        session, _console, sent = turn
        event = session.run_instruction("3번 그룹 저장해줘")
        assert [e["type"] for e in sent].count("chat_response") == 1
        assert sent[-1] == event
        assert event["status"] == "ok"
        assert event["text"] == "완료했습니다"


class TestTheFramesReachTheWire:
    """app.py 배선 — 진행 프레임이 **워커 스레드에서 소켓까지** 실제로 간다.

    턴은 ``asyncio.to_thread``\\ 에서 돌고(app.py의 chat 분기), ``send_event``\\ 는
    ``asyncio.run_coroutine_threadsafe``\\ 로 이벤트 루프에 되돌린다. 세션 단위
    테스트는 그 경계를 지나지 않으므로 여기서 한 번 실물 소켓으로 확인한다 —
    이 축은 app.py를 **한 줄도 고치지 않고** 기존 싱크를 그대로 재사용한다는
    주장의 근거이기도 하다.
    """

    def test_a_chat_turn_streams_progress_frames_then_the_response(self, tmp_path):
        provider = ScriptedProvider([_run_turn(["Store Group 3"], "c1"), _final()])
        deps, console, _gate = _deps(tmp_path, provider)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            assert recv_frame(ws)["type"] == "status"
            _send(ws, type="chat", text="3번 그룹 저장해줘")
            frames: list[dict] = []
            for _ in range(40):
                frames.append(recv_frame(ws))
                if frames[-1]["type"] == "chat_response":
                    break
        streamed = [f for f in frames if f["type"] == "progress"]
        assert streamed, f"소켓에 진행 프레임이 0건이다: {[f['type'] for f in frames]}"
        assert [f["seq"] for f in streamed] == list(range(1, len(streamed) + 1))
        assert {f["phase"] for f in streamed} == {"model_call", "tool_start", "tool_done"}
        assert frames[-1]["type"] == "chat_response"
        # 진행 스트리밍이 실행 경로를 바꾸지 않았다.
        assert console.executed == ["Store Group 3"]
