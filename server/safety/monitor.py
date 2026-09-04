"""Console health monitor (REQ-MVP-030/031) — failure-mode state machine.

States (design.md §E):

- ``online`` — heartbeat/queries healthy; normal execution path.
- ``console_offline`` — heartbeat or query timeout with no console traffic at
  all: the UI shows the state and NEW executions are blocked (REQ-MVP-030).
- ``responder_degraded`` — native console traffic was seen within the activity
  window but the responder does not answer: state queries / result retrieval
  are reported degraded and side-effectful commands are NOT started while
  result confirmation is impossible (REQ-MVP-031).
- ``responder_version_mismatch`` — the responder ANSWERS, but with a version
  lower than expected: the deployed plugin is stale and a re-import fixes it
  (REQ-READBACK2-003).
- ``responder_version_unrecognized`` — the responder answers with a version
  that cannot be parsed or is HIGHER than expected: what is running is unknown,
  so the operator investigates rather than re-imports (REQ-READBACK2-004).

Recovery is via a successful heartbeat only — passive traffic alone never
clears a degraded/offline state (the responder must actually answer).

두 버전 상태는 **성공한 하트비트에서만** 나온다. 그래서 침묵 분류(오프라인 /
저하)보다 엄격히 하류이고, `note_ping_timeout` 이 무조건 상태를 다시 쓰므로
버전 사유가 오프라인 판정을 가리는 것이 구조적으로 불가능하다
(REQ-READBACK2-005).
"""

from __future__ import annotations

import time
from collections.abc import Callable

from server.safety.responder_version import (
    VERSION_LOW,
    VERSION_UNRECOGNIZED,
    classify_version,
)

DEFAULT_ACTIVITY_WINDOW_SECONDS = 15.0


class HealthMonitor:
    """Tracks console liveness from heartbeat results and inbound traffic."""

    ONLINE = "online"
    CONSOLE_OFFLINE = "console_offline"
    RESPONDER_DEGRADED = "responder_degraded"
    RESPONDER_VERSION_MISMATCH = "responder_version_mismatch"
    RESPONDER_VERSION_UNRECOGNIZED = "responder_version_unrecognized"

    #: 버전 판정 → health state. `ok` 와 `unreported` 는 여기 없다 — 둘 다
    #: `online` 이며, 그 이유는 `responder_version` 모듈 docstring 이 소유한다.
    _VERSION_STATES = {
        VERSION_LOW: RESPONDER_VERSION_MISMATCH,
        VERSION_UNRECOGNIZED: RESPONDER_VERSION_UNRECOGNIZED,
    }

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        activity_window_seconds: float = DEFAULT_ACTIVITY_WINDOW_SECONDS,
    ) -> None:
        self._clock = clock
        self._activity_window_seconds = activity_window_seconds
        self._last_activity_at: float | None = None
        self._state = self.ONLINE
        self._responder_version: str | None = None

    @property
    def state(self) -> str:
        """UI-visible health state (REQ-MVP-030: shown to the user)."""
        return self._state

    @property
    def responder_version(self) -> str | None:
        """마지막 하트비트가 보고한 응답기 버전 (없으면 None).

        차단 사유 문면에 실린다 — 「버전이 어긋났다」만으로는 운영자가 무엇을
        재임포트해야 하는지 알 수 없다.
        """
        return self._responder_version

    @property
    def executions_blocked(self) -> bool:
        """True when new side-effectful executions must not start."""
        return self._state != self.ONLINE

    def note_activity(self) -> None:
        """Record ANY inbound console traffic (native feedback included)."""
        self._last_activity_at = self._clock()

    def note_ping_success(self, *, version: str | None = None) -> None:
        """A responder heartbeat answered — classify the reported version.

        `version` 이 생략되면(기존 호출자 · 버전을 재지 않는 가짜 포트) 판정은
        `unreported` 이고 상태는 `online` 이다 — 재지 않은 것을 차단 사유로
        쓰지 않는다.
        """
        self._last_activity_at = self._clock()
        self._responder_version = version
        self._state = self._VERSION_STATES.get(classify_version(version), self.ONLINE)

    def note_ping_timeout(self) -> None:
        """Heartbeat timed out — classify offline vs degraded (design.md §E)."""
        self._state = self._classify_silence()

    def note_query_timeout(self) -> None:
        """A state query timed out — same semantics as a heartbeat timeout."""
        self._state = self._classify_silence()

    def _classify_silence(self) -> str:
        if self._last_activity_at is None:
            return self.CONSOLE_OFFLINE
        if self._clock() - self._last_activity_at <= self._activity_window_seconds:
            return self.RESPONDER_DEGRADED
        return self.CONSOLE_OFFLINE
