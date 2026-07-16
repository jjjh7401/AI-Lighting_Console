"""Persistent-miss fallback detector (REQ-MVP-040 part ii, AD2-m1 — AC-MVP-031).

Detection rule (config-defined operational parameters, defaults N=20 / M=2):
over the rolling window of the last N JUDGED turns (retry turns are excluded
upstream, per the acceptance round-trip measurement rules), when the window
median exceeds the threshold for M consecutive window evaluations, the detector
emits a fallback decision.

The decision is emitted through an injectable audit sink — the durable audit
log is Milestone M4 scope. The actual provider switch remains a CONFIG change
(REQ-MVP-039); this detector only decides and records.
"""

from __future__ import annotations

import statistics
from collections import deque
from typing import Protocol

from server.llm.config import FallbackSettings


class AuditSink(Protocol):
    """Receives fallback decision events (M4 wires the durable audit log)."""

    def record(self, event: dict) -> None:
        """Persist/forward one audit event."""
        ...


class FallbackDetector:
    """Rolling-window median detector over judged-turn round-trip durations."""

    def __init__(
        self,
        settings: FallbackSettings,
        *,
        audit_sink: AuditSink,
        active_provider: str,
    ) -> None:
        self._settings = settings
        self._audit_sink = audit_sink
        self._active_provider = active_provider
        self._durations: deque[float] = deque(maxlen=settings.window_turns)
        self._consecutive = 0
        self.triggered = False

    def observe_turn(self, duration_seconds: float) -> bool:
        """Feed one judged turn's round-trip duration; True once fallback is due."""
        if self.triggered:
            return True  # latched — the decision is emitted exactly once
        self._durations.append(duration_seconds)
        if len(self._durations) < self._settings.window_turns:
            return False  # no evaluation until the window is full
        window_median = statistics.median(self._durations)
        if window_median > self._settings.threshold_seconds:
            self._consecutive += 1
        else:
            self._consecutive = 0
        if self._consecutive >= self._settings.consecutive_windows:
            self.triggered = True
            self._audit_sink.record(
                {
                    "event": "provider_fallback_triggered",
                    "provider": self._active_provider,
                    "window_turns": self._settings.window_turns,
                    "consecutive_windows": self._settings.consecutive_windows,
                    "threshold_seconds": self._settings.threshold_seconds,
                    "window_median_seconds": window_median,
                    "action": (
                        "switch to another eligible provider via config change "
                        "(REQ-MVP-039); this event is the audit record of the decision"
                    ),
                }
            )
        return self.triggered
