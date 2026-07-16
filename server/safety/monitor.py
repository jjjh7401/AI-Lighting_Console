"""Console health monitor (REQ-MVP-030/031) — failure-mode state machine.

States (design.md §E):

- ``online`` — heartbeat/queries healthy; normal execution path.
- ``console_offline`` — heartbeat or query timeout with no console traffic at
  all: the UI shows the state and NEW executions are blocked (REQ-MVP-030).
- ``responder_degraded`` — native console traffic was seen within the activity
  window but the responder does not answer: state queries / result retrieval
  are reported degraded and side-effectful commands are NOT started while
  result confirmation is impossible (REQ-MVP-031).

Recovery is via a successful heartbeat only — passive traffic alone never
clears a degraded/offline state (the responder must actually answer).
"""

from __future__ import annotations

import time
from collections.abc import Callable

DEFAULT_ACTIVITY_WINDOW_SECONDS = 15.0


class HealthMonitor:
    """Tracks console liveness from heartbeat results and inbound traffic."""

    ONLINE = "online"
    CONSOLE_OFFLINE = "console_offline"
    RESPONDER_DEGRADED = "responder_degraded"

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

    @property
    def state(self) -> str:
        """UI-visible health state (REQ-MVP-030: shown to the user)."""
        return self._state

    @property
    def executions_blocked(self) -> bool:
        """True when new side-effectful executions must not start."""
        return self._state != self.ONLINE

    def note_activity(self) -> None:
        """Record ANY inbound console traffic (native feedback included)."""
        self._last_activity_at = self._clock()

    def note_ping_success(self) -> None:
        """A responder heartbeat answered — the full path is healthy."""
        self._last_activity_at = self._clock()
        self._state = self.ONLINE

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
