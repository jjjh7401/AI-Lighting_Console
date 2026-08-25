"""t57 임시 프로브 — 측정 후 삭제한다. 커밋하지 않는다.

재는 것: send_event 의 크로스 스레드 경로가 애초에 작동하는가, 그리고
같은 호출을 어느 스레드에서 하느냐가 도착을 가르는가.

계측기 두 개:
- asyncio.run_coroutine_threadsafe 를 감싸 호출 스레드와 Future 를 잡는다.
- _safe_send 를 suppress 없는 판으로 갈아끼워 삼켜지던 예외를 드러낸다.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading

import pytest
from fastapi.testclient import TestClient

import server.web.app as app_mod
from server.web.app import create_app

from .conftest import recv_frame
from .test_runner_self_correction import ScriptedProvider, _final, _run_turn
from .test_web_app import _deps, _send


class Rec:
    def __init__(self) -> None:
        self.scheduled: list[int] = []
        self.futures: list = []
        self.entered: list[int] = []
        self.errors: list[str] = []
        self.caller_errors: list[str] = []


@pytest.fixture
def rec(monkeypatch):
    r = Rec()
    real = asyncio.run_coroutine_threadsafe

    def spy(coro, loop):
        fut = real(coro, loop)
        r.scheduled.append(threading.get_ident())
        r.futures.append(fut)
        return fut

    async def loud_send(websocket, event):
        r.entered.append(threading.get_ident())
        try:
            await websocket.send_json(event)
        except Exception as error:
            r.errors.append(repr(error))
            raise

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", spy)
    monkeypatch.setattr(app_mod, "_safe_send", loud_send)
    return r


def _loop_from(notify):
    for cell in notify.__closure__ or ():
        obj = cell.cell_contents
        if callable(obj) and getattr(obj, "__name__", "") == "send_event":
            for inner in obj.__closure__ or ():
                candidate = inner.cell_contents
                if isinstance(candidate, asyncio.AbstractEventLoop):
                    return candidate
    raise AssertionError("send_event 클로저에서 루프를 못 찾았다")


def _loop_thread_ident(loop, timeout=3.0):
    """루프 안에서 스레드 id 를 직접 기록시킨다.

    이 호출 자체가 측정이다 — 시간 안에 안 돌아오면 루프가 콜백을 안 돌리고
    있다는 뜻이고, 그것만으로 (b) 스레드 축의 절반이 답해진다.
    """
    box: dict[str, int] = {}
    done = threading.Event()

    def mark():
        box["ident"] = threading.get_ident()
        done.set()

    loop.call_soon_threadsafe(mark)
    fired = done.wait(timeout)
    return box.get("ident"), fired


@contextlib.contextmanager
def _live(tmp_path, provider=None):
    deps, _console, _gate = _deps(tmp_path, provider or ScriptedProvider([]))
    with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
        first = recv_frame(ws, timeout=3.0)
        assert first["type"] == "status", first
        listeners = tuple(deps.status_listeners)
        assert len(listeners) == 1, listeners
        notify = listeners[0]
        loop = _loop_from(notify)
        ident, fired = _loop_thread_ident(loop)
        print(
            "PROBE loop_callback_fired="
            + str(fired)
            + " loop_thread="
            + str(ident)
            + " loop_is_running="
            + str(loop.is_running())
            + " main_thread="
            + str(threading.main_thread().ident)
        )
        yield ws, notify, loop, ident


def _try_recv(ws, timeout=2.0):
    try:
        return recv_frame(ws, timeout=timeout)
    except AssertionError:
        return None


def _report(name, rec, loop_ident, arrived):
    states = []
    for fut in rec.futures:
        if not fut.done():
            states.append("pending")
            continue
        exc = fut.exception()
        states.append("ok" if exc is None else "exc=" + repr(exc))
    print(
        "PROBE-"
        + name
        + " loop_thread="
        + str(loop_ident)
        + " main_thread="
        + str(threading.main_thread().ident)
    )
    print("PROBE-" + name + " scheduled_from=" + str(rec.scheduled))
    print("PROBE-" + name + " entered_in=" + str(rec.entered))
    print(
        "PROBE-"
        + name
        + " send_errors="
        + str(rec.errors)
        + " caller_errors="
        + str(rec.caller_errors)
    )
    print("PROBE-" + name + " future_states=" + str(states))
    print("PROBE-" + name + " ARRIVED=" + str(arrived["type"] if arrived else None))


class TestControlCrossThread:
    def test_chat_turn_progress_reaches_the_socket(self, tmp_path, rec):
        provider = ScriptedProvider([_run_turn(["Store Group 3"], "c1"), _final()])
        with _live(tmp_path, provider) as (ws, _notify, _loop, loop_ident):
            _send(ws, type="chat", text="3번 그룹 저장해줘")
            frames = []
            for _ in range(40):
                frame = _try_recv(ws, 5.0)
                if frame is None:
                    break
                frames.append(frame)
                if frame["type"] == "chat_response":
                    break
        kinds = [f["type"] for f in frames]
        _report("CONTROL", rec, loop_ident, frames[-1] if frames else None)
        print("PROBE-CONTROL kinds=" + str(kinds))
        cross = [t for t in rec.scheduled if t != loop_ident]
        print(
            "PROBE-CONTROL cross_thread_schedules="
            + str(len(cross))
            + " of "
            + str(len(rec.scheduled))
        )


class TestArms:
    def test_arm_main_thread(self, tmp_path, rec):
        with _live(tmp_path) as (ws, notify, _loop, loop_ident):
            try:
                notify()
            except Exception as error:
                rec.caller_errors.append(repr(error))
            arrived = _try_recv(ws)
        _report("ARM-main", rec, loop_ident, arrived)

    def test_arm_worker_thread(self, tmp_path, rec):
        with _live(tmp_path) as (ws, notify, _loop, loop_ident):

            def run():
                try:
                    notify()
                except Exception as error:
                    rec.caller_errors.append(repr(error))

            worker = threading.Thread(target=run)
            worker.start()
            worker.join(5.0)
            arrived = _try_recv(ws)
        _report("ARM-worker", rec, loop_ident, arrived)

    def test_arm_loop_thread(self, tmp_path, rec):
        with _live(tmp_path) as (ws, notify, loop, loop_ident):
            print("PROBE-ARM-loop loop_obj_running=" + str(loop.is_running()))
            loop.call_soon_threadsafe(notify)
            arrived = _try_recv(ws)
        _report("ARM-loop", rec, loop_ident, arrived)


class TestControls:
    def test_negative_no_call_no_frame(self, tmp_path, rec):
        """음성 대조군 — 아무도 안 부르면 프레임이 없어야 한다."""
        with _live(tmp_path) as (ws, _notify, _loop, loop_ident):
            arrived = _try_recv(ws)
        _report("NEG", rec, loop_ident, arrived)

    def test_fabricated_control_instrument_can_report_none(self, tmp_path, rec):
        """날조 대조군 — 계측기가 None 을 낼 수 있는지."""
        with _live(tmp_path) as (ws, notify, _loop, loop_ident):
            arrived_before = _try_recv(ws, 0.3)
            notify()
            arrived_after = _try_recv(ws, 2.0)
        print(
            "PROBE-FAB before="
            + str(arrived_before["type"] if arrived_before else None)
            + " after="
            + str(arrived_after["type"] if arrived_after else None)
        )
        _report("FAB", rec, loop_ident, arrived_after)


class TestOrphanPump:
    """가설 — 시간 상한을 넘긴 recv_frame 의 daemon 펌프가 살아남아
    **다음 프레임을 가로챈다.** 참이면 §8.2 의 0/20 은 앱이 아니라 계측기다."""

    def test_a_timed_out_read_steals_the_next_frame(self, tmp_path, rec):
        with _live(tmp_path) as (ws, notify, _loop, loop_ident):
            first = _try_recv(ws, 0.3)  # 반드시 시간 초과 -> 고아 펌프 1개
            notify()  # 이제 프레임을 하나 민다
            second = _try_recv(ws, 2.0)  # 새 펌프가 받나, 고아가 훔치나
            notify()
            third = _try_recv(ws, 2.0)
        print(
            "PROBE-ORPHAN first="
            + str(first)
            + " second="
            + str(second["type"] if second else None)
            + " third="
            + str(third["type"] if third else None)
        )
        _report("ORPHAN", rec, loop_ident, second)

    def test_repeat_loop_reproduces_the_zero(self, tmp_path, rec):
        """§8.2 의 모양 그대로 — notify + recv 를 20회."""
        arrivals = 0
        with _live(tmp_path) as (ws, notify, _loop, loop_ident):
            for _ in range(20):
                notify()
                if _try_recv(ws, 1.0) is not None:
                    arrivals += 1
        print(
            "PROBE-REPEAT arrivals="
            + str(arrivals)
            + "/20"
            + " scheduled="
            + str(len(rec.scheduled))
            + " entered="
            + str(len(rec.entered))
            + " errors="
            + str(rec.errors)
        )


class TestOrdering:
    """트리거가 **먼저** 도착하는가 — 20회 반복해 결정성을 잰다.

    시나리오: notify() 로 기대 밖 status 를 밀고, 곧바로 프로토콜 오류를
    보내 서버가 error 한 장으로 답하게 한다. recv_frame 이 status 를 돌려주면
    뒤따르는 단정이 깨지고, drain_until(ws, "error") 는 조용히 버린다 —
    두 헬퍼가 갈리는 바로 그 모양이다.
    """

    def test_pushed_status_precedes_the_reply(self, tmp_path, rec):
        orders = []
        with _live(tmp_path) as (ws, notify, _loop, loop_ident):
            for _ in range(20):
                notify()
                ws.send_text("{ not json")
                a = _try_recv(ws, 3.0)
                b = _try_recv(ws, 3.0)
                orders.append((a["type"] if a else None, b["type"] if b else None))
        first_status = sum(1 for a, _ in orders if a == "status")
        print("PROBE-ORDER pairs=" + str(sorted(set(orders))))
        print("PROBE-ORDER status_first=" + str(first_status) + "/20")
