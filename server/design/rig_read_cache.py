"""서버 수명 리그 판독 캐시 — 「⇪ 콘솔에 반영」이 같은 장비 사실을 매번 다시 읽지 않게 한다.

실기 측정(LOVE ATTACK)에서 반영 한 번의 98% 는 리그 단계였다: 응답기 상태 읽기 588건이
``Patch/FixtureTypes/.../DMXModes/.../DMXChannels`` 를 채널 단위로 걸었고, 디머 그룹 단계가
85건을 더 읽었다. 기종·모드·채널 배치는 쇼 동안 바뀌지 않는다.

리드 결정(2026-10-19 재측정 뒤): 장비·기종 판독은 **시간으로 끊지 않는다**. 서버가 살아 있는 동안
유지하고, 버리는 때는 (1) 앱의 패치 쓰기 epoch 가 바뀔 때, (2) 「장비 다시 읽기」 때, (3) 재연결이나
명시적 새로고침(:meth:`RigReadCache.invalidate`)뿐이다. 콘솔에서 사람이 패치를 고치면 앱은 그것을
모르므로 「장비 다시 읽기」로 바로잡는다. 그룹 소속만 무대 칸을 그릴 때도 갱신되므로 짧게 둔다.

안전 규율:

* **전수로 읽힌 결과만** 저장한다. 부분·실패·미판독은 저장하지 않아 다음 반영이 다시 묻는다.
* 키에 이름을 넣는다. 같은 슬롯이라도 기종·모드 이름이 달라지면 적중하지 않는다.
* 읽기 전용이다. 이 모듈은 콘솔에 아무것도 쓰지 않는다.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from typing import Any

#: 장비·기종 판독 — 서버 수명 동안 유지한다. 버리기는 invalidate 로만 한다(시간으로 끊지 않는다).
KEEP_UNTIL_INVALIDATED = math.inf
#: 그룹 소속 — 무대 칸을 다시 그릴 때 갱신되므로 짧게 둔다.
LIVE_TTL_SECONDS = 120.0

KIND_TYPE_MODES = "type_modes"
KIND_MODE_CAPS = "mode_caps"
KIND_FIXTURE = "fixture"
KIND_SINGLE = "single"
KIND_MEMBERS = "members"

_TTL_BY_KIND = {
    KIND_TYPE_MODES: KEEP_UNTIL_INVALIDATED,
    KIND_MODE_CAPS: KEEP_UNTIL_INVALIDATED,
    KIND_FIXTURE: KEEP_UNTIL_INVALIDATED,
    KIND_SINGLE: KEEP_UNTIL_INVALIDATED,
    KIND_MEMBERS: LIVE_TTL_SECONDS,
}


class RigReadCache:
    """종류별 TTL 을 가진 작은 읽기 전용 캐시. 스레드 안전."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, Hashable], tuple[float, Any]] = {}
        self._reading = 0
        self.hits = 0
        self.misses = 0
        #: 비운 횟수 — 시험과 로그가 무효화가 실제로 일어났는지 본다.
        self.invalidations = 0
        #: 마지막으로 맞춰 본 게이트의 패치 epoch. 게이트 값과 다르면 장비 판독을 버린다.
        self.synced_patch_epoch: int | None = None

    def get(self, kind: str, key: Hashable) -> Any | None:
        with self._lock:
            entry = self._entries.get((kind, key))
            if entry is not None and self._clock() < entry[0]:
                self.hits += 1
                return entry[1]
            if entry is not None:
                del self._entries[(kind, key)]
            self.misses += 1
            return None

    def put(self, kind: str, key: Hashable, value: Any) -> None:
        expires = self._clock() + _TTL_BY_KIND[kind]
        with self._lock:
            self._entries[(kind, key)] = (expires, value)

    def invalidate(self, kind: str | None = None) -> None:
        """전부(또는 한 종류) 비운다 — 패치 쓰기·「장비 다시 읽기」·재연결에서 부른다."""
        with self._lock:
            if kind is None:
                self._entries.clear()
            else:
                for entry_key in [k for k in self._entries if k[0] == kind]:
                    del self._entries[entry_key]
            self.invalidations += 1

    @contextmanager
    def reading(self) -> Iterator[None]:
        """장비 판독이 도는 동안 표시한다 — 감시 폴링이 이 동안 콘솔을 양보하게 한다."""
        with self._lock:
            self._reading += 1
        try:
            yield
        finally:
            with self._lock:
                self._reading -= 1

    def is_reading(self) -> bool:
        with self._lock:
            return self._reading > 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


def follow_patch_epoch(cache: RigReadCache, epoch: int) -> None:
    """게이트의 패치 epoch 가 바뀌었으면 장비 판독을 버린다. 세션과 예열이 같은 규칙을 쓴다."""
    if cache.synced_patch_epoch != epoch:
        cache.invalidate()
        cache.synced_patch_epoch = epoch


#: 장비 판독이 도는 동안 감시 틱을 기다리게 하는 상한(초). 판독이 길어도 감시가 영영 멈추지 않는다.
CUE_MONITOR_DEFER_CAP_SECONDS = 5.0


def wait_while_reading(
    cache: RigReadCache, *, cap_seconds: float, poll_seconds: float = 0.05
) -> float:
    """장비 판독이 도는 동안 기다린다. ``cap_seconds`` 를 넘지 않고, 기다린 초를 돌려준다."""
    started = time.monotonic()
    while cache.is_reading() and time.monotonic() - started < cap_seconds:
        time.sleep(poll_seconds)
    return time.monotonic() - started
