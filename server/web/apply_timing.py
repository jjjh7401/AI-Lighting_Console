"""「⇪ 콘솔에 반영」 단계별 시간 계측 (SPEC-LDRHYTHM-001, 카드 apply-latency-2).

반영 한 번마다 서버 로그(표준 오류)에 단계당 한 줄을 남긴다. 한 줄에는 그 단계의 경과 시간과, 그
사이에 게이트를 거친 콘솔 읽기 수·합계 시간·가장 오래 걸린 읽기가 들어간다. 승인 카드를 보낸
순간에는 카드 항목 수와 만든 시간·보낸 시간을 덧붙인다. 계측만 하고 동작은 바꾸지 않는다.
"""

from __future__ import annotations

import functools
import logging
import sys
import time
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar, cast

from server.observability.console_tally import ACTIVE_TALLY, ConsoleTally

_Method = TypeVar("_Method", bound=Callable[..., Any])

_LOG = logging.getLogger("server.web.apply_timing")
if not _LOG.handlers:
    # uvicorn 의 기본 설정은 루트 로거에 핸들러를 달지 않아 INFO 가 버려진다. 그래서 이 로거만
    # 표준 오류로 직접 내고 루트로는 넘기지 않는다 — 다른 로그와 섞이지 않게.
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _LOG.addHandler(_handler)
    _LOG.setLevel(logging.INFO)
    _LOG.propagate = False

_CURRENT: ContextVar[ApplyClock | None] = ContextVar("current_apply_clock", default=None)


class ApplyClock:
    """반영 한 번의 단계 시계. ``start()`` 로 켜고 ``finish()`` 로 끈다."""

    def __init__(self) -> None:
        self._started = time.perf_counter()
        self._mark = self._started
        self._tally = ConsoleTally()
        self._tally_token = None
        self._clock_token = None

    def start(self) -> None:
        self._tally_token = ACTIVE_TALLY.set(self._tally)
        self._clock_token = _CURRENT.set(self)

    def stage(self, name: str) -> None:
        """직전 표시 뒤의 한 단계를 적는다."""
        self._emit(f"stage={name}")

    def card(self, *, items: int, build_ms: float, send_ms: float) -> None:
        """승인 카드를 보낸 순간 — 항목 수와 만든 시간·보낸 시간을 덧붙인다."""
        self._emit(f"stage=card items={items} build_ms={build_ms:.1f} send_ms={send_ms:.1f}")

    def finish(self) -> None:
        self._emit("stage=tail")
        total_ms = (time.perf_counter() - self._started) * 1000
        _LOG.info("apply.timing stage=total ms=%.1f", total_ms)
        if self._tally_token is not None:
            ACTIVE_TALLY.reset(self._tally_token)
        if self._clock_token is not None:
            _CURRENT.reset(self._clock_token)

    def _emit(self, label: str) -> None:
        now = time.perf_counter()
        tally = self._tally
        _LOG.info(
            "apply.timing %s ms=%.1f console_reads=%d console_ms=%.1f "
            "console_max_ms=%.1f slowest=%s",
            label,
            (now - self._mark) * 1000,
            tally.calls,
            tally.seconds * 1000,
            tally.slowest_seconds * 1000,
            tally.slowest_path or "-",
        )
        self._tally = ConsoleTally()
        ACTIVE_TALLY.set(self._tally)
        self._mark = now


def current_clock() -> ApplyClock | None:
    """지금 반영 중인 시계 — 승인 카드를 보내는 자리가 쓴다. 반영 밖이면 ``None``."""
    return _CURRENT.get()


def apply_stage(name: str) -> None:
    """지금 반영의 단계 한 줄을 남긴다. 반영 밖에서 불리면 아무 일도 하지 않는다."""
    clock = _CURRENT.get()
    if clock is not None:
        clock.stage(name)


def timed_apply(method: _Method) -> _Method:
    """반영 메서드를 시계로 감싼다. 안의 ``apply_stage`` 호출이 단계 줄이 된다."""

    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        clock = ApplyClock()
        clock.start()
        try:
            return method(self, *args, **kwargs)
        finally:
            clock.finish()

    return cast(_Method, wrapper)
