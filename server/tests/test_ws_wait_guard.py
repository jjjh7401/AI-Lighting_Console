"""`recv_frame` 이 실제로 상한을 거는지 잰다 (t52).

이 파일이 없으면 승격은 **아무것도 안 지킨다**. 옮긴 것과 지키는 것은 다른
작업이고, 상한을 지우면 실패가 아니라 **정지**로 나타나므로 평범한 테스트로는
안 잡힌다 — 그래서 「안 끝나는 것」을 바깥에서 재는 형태가 필요하다.
"""

from __future__ import annotations

import threading
import time

import pytest

from .conftest import drain_until, recv_frame


class _NeverAnswers:
    """`receive_json` 이 영영 돌아오지 않는 소켓 — 사건의 모양 그대로."""

    def __init__(self) -> None:
        self.entered = threading.Event()

    def receive_json(self):
        self.entered.set()
        while True:  # 상한은 recv_frame 쪽에 있어야 한다
            time.sleep(0.05)


class _AnswersWrongForever:
    """계속 답하되 **원하는 종류는 영영 안 주는** 소켓."""

    def receive_json(self):
        return dict(type="status")


def test_recv_frame_fails_instead_of_hanging_when_no_frame_arrives():
    ws = _NeverAnswers()
    started = time.monotonic()
    with pytest.raises(AssertionError) as caught:
        recv_frame(ws, timeout=0.3)
    elapsed = time.monotonic() - started

    assert ws.entered.is_set(), "수신을 시도하지도 않았다면 이 테스트는 공허하다"
    assert "no websocket frame within 0.3s" in str(caught.value)
    assert elapsed < 5.0, "상한이 안 걸렸다: " + str(round(elapsed, 1)) + "s"


def test_drain_until_stops_on_the_frame_count_when_frames_keep_arriving():
    """프레임은 오는데 원하는 종류가 안 오는 경우 — 회수 상한이 끊는다."""
    with pytest.raises(AssertionError) as caught:
        drain_until(_AnswersWrongForever(), "chat_response", limit=3)
    assert "within 3 frames" in str(caught.value)
    assert "status" in str(caught.value), "무엇을 봤는지 보고해야 진단이 된다"
