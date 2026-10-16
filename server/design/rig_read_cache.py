"""세션 단위 리그 판독 캐시 — 「⇪ 콘솔에 반영」이 같은 정적 사실을 매번 다시 읽지 않게 한다.

실기 측정(LOVE ATTACK)에서 반영 한 번의 98% 는 리그 단계였다: 응답기 상태 읽기 588건이
``Patch/FixtureTypes/.../DMXModes/.../DMXChannels`` 를 채널 단위로 걸었고, 디머 그룹 단계가
85건을 더 읽었다. 기종·모드·채널 배치는 쇼 세션 동안 바뀌지 않는다. 그래서 두 층으로 나눈다.

* **정적 층**(기종 모드 목록, (기종, 모드) 능력) — 수명이 길다(``STATIC_TTL_SECONDS``).
* **동적 층**(장비별 FID·Mode·좌표 묶음 판독, 그룹 소속) — 수명이 짧다(``LIVE_TTL_SECONDS``).
  운영자가 콘솔에서 패치·그룹을 고칠 수 있기 때문이다.

안전 규율:

* **전수로 읽힌 결과만** 저장한다. 부분·실패·미판독은 저장하지 않아 다음 반영이 다시 묻는다
  (부분 결과가 전수처럼 굳는 것을 막는다).
* 키에 이름을 넣는다. 같은 슬롯이라도 기종·모드 이름이 달라지면 적중하지 않는다.
* 재연결·명시적 새로고침은 :meth:`RigReadCache.invalidate` 로 전부 비운다.
* 읽기 전용이다. 이 모듈은 콘솔에 아무것도 쓰지 않는다.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Hashable
from typing import Any

#: 기종·모드·채널 배치 — 쇼 세션 동안 정적이다.
STATIC_TTL_SECONDS = 1800.0
#: 장비 패치 판독·그룹 소속 — 운영자가 콘솔에서 고칠 수 있어 짧게 둔다.
LIVE_TTL_SECONDS = 120.0

KIND_TYPE_MODES = "type_modes"
KIND_MODE_CAPS = "mode_caps"
KIND_FIXTURE = "fixture"
KIND_SINGLE = "single"
KIND_MEMBERS = "members"

_TTL_BY_KIND = {
    KIND_TYPE_MODES: STATIC_TTL_SECONDS,
    KIND_MODE_CAPS: STATIC_TTL_SECONDS,
    KIND_FIXTURE: LIVE_TTL_SECONDS,
    KIND_SINGLE: LIVE_TTL_SECONDS,
    KIND_MEMBERS: LIVE_TTL_SECONDS,
}


class RigReadCache:
    """종류별 TTL 을 가진 작은 읽기 전용 캐시. 스레드 안전."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, Hashable], tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0
        #: 비운 횟수 — 시험과 로그가 무효화가 실제로 일어났는지 본다.
        self.invalidations = 0

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
        """전부(또는 한 종류) 비운다 — 재연결·명시적 새로고침에서 부른다."""
        with self._lock:
            if kind is None:
                self._entries.clear()
            else:
                for entry_key in [k for k in self._entries if k[0] == kind]:
                    del self._entries[entry_key]
            self.invalidations += 1

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
