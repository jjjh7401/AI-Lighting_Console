"""콘솔 읽기 집계 — 반영 한 번 안에서 게이트를 거친 콘솔 읽기 수와 기다린 시간을 센다.

계측만 하고 동작은 바꾸지 않는다. 집계가 켜져 있지 않으면(기본) 읽기 한 번마다 contextvar 를
들여다볼 뿐이다. 켜는 쪽은 반영 계측(``server.web.apply_timing``). 이 패키지는 safety 바깥에 둔다 —
safety 는 쓰기 게이트 chokepoint 로 파일 집합이 고정되어 있어 새 파일을 넣지 않는다.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, TypeVar, cast

_Method = TypeVar("_Method", bound=Callable[..., Any])


@dataclass
class ConsoleTally:
    """한 구간 동안의 콘솔 읽기 집계."""

    calls: int = 0
    seconds: float = 0.0
    slowest_seconds: float = 0.0
    slowest_path: str = ""

    def record(self, path: str, seconds: float) -> None:
        self.calls += 1
        self.seconds += seconds
        if seconds > self.slowest_seconds:
            self.slowest_seconds = seconds
            self.slowest_path = path


#: 지금 켜진 집계. ``None`` 이면 아무것도 세지 않는다.
ACTIVE_TALLY: ContextVar[ConsoleTally | None] = ContextVar("active_console_tally", default=None)


def counted_read(method: _Method) -> _Method:
    """게이트의 콘솔 읽기 메서드(``(self, path, ...)`` 모양)를 켜진 집계에 올린다."""

    @functools.wraps(method)
    def wrapper(self: Any, path: str, *args: Any, **kwargs: Any) -> Any:
        tally = ACTIVE_TALLY.get()
        if tally is None:
            return method(self, path, *args, **kwargs)
        started = time.perf_counter()
        try:
            return method(self, path, *args, **kwargs)
        finally:
            tally.record(str(path), time.perf_counter() - started)

    return cast(_Method, wrapper)
