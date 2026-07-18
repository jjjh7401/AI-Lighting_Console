"""Persistent-miss fallback detector (REQ-MVP-040 part ii, AD2-m1 — AC-MVP-031).

Detection rule (config-defined operational parameters, defaults N=20 / M=2):
over the rolling window of the last N JUDGED turns (retry turns are excluded
upstream, per the acceptance round-trip measurement rules), when the window
median exceeds the threshold for M consecutive window evaluations, the detector
emits a fallback decision.

The decision is emitted through an injectable audit sink — the durable audit
log is Milestone M4 scope. The provider switch itself is a CONFIG change
(REQ-MVP-039, ``fallback.target_provider``): when a target is configured, the
detector invokes an injectable ``on_fallback`` callback exactly once at the
moment the decision fires (AC-MVP-027 part 3) — the callback is where the
actual hand-off happens (see ``server.orchestrator.runner.SwitchableProvider``).
When no target is configured, the detector decides and audit-logs only, same
as before; the recorded event honestly distinguishes the two (or three, see
``observe_turn``) states so the audit trail never silently claims a switch
that did not happen.
"""

from __future__ import annotations

import statistics
import threading
from collections import deque
from collections.abc import Callable
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
        on_fallback: Callable[[str], None] | None = None,
    ) -> None:
        self._settings = settings
        self._audit_sink = audit_sink
        self._active_provider = active_provider
        self._on_fallback = on_fallback
        self._durations: deque[float] = deque(maxlen=settings.window_turns)
        self._consecutive = 0
        self.triggered = False
        # @MX:ANCHOR: [AUTO] serializes the whole check-then-set decision —
        #   production wiring shares ONE FallbackDetector across every
        #   ChatSession (server.web.measure.RoundTripRecorder), and
        #   ChatSession.run_instruction runs on a worker thread via
        #   asyncio.to_thread (server/web/session.py), so observe_turn() can
        #   genuinely be entered concurrently from two OS threads.
        # @MX:REASON: [AUTO] without the lock, two concurrent callers could
        #   both pass the `if self.triggered` early-return before either sets
        #   it, then both satisfy the consecutive-windows threshold and both
        #   invoke on_fallback — violating the class's documented "exactly
        #   once" invariant (module docstring, AC-MVP-027 part 3). Guarding
        #   the full method body (not just the trigger assignment) closes the
        #   race atomically: the second concurrent caller either observes
        #   `triggered is True` already and returns immediately, or the two
        #   calls are strictly ordered and only the winner's window state
        #   mutation is visible to the loser.
        self._lock = threading.Lock()

    def observe_turn(self, duration_seconds: float) -> bool:
        """Feed one judged turn's round-trip duration; True once fallback is due."""
        with self._lock:
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
                target = self._settings.target_provider
                # Three honest states (AC-MVP-027 part 3) — never a silent no-op:
                #   (a) switched     — a target is configured AND a callback is
                #       wired; the hand-off actually happened, exactly once.
                #   (b) decided-only — no target_provider is configured at all
                #       (today's shipped default, pending the M6b-3 human check-in).
                #   (c) decided-only (mismatch) — a target IS configured but no
                #       on_fallback was wired at construction time; this is a
                #       wiring gap, distinguished in the recorded action text.
                if target is not None and self._on_fallback is not None:
                    self._on_fallback(target)
                    switched = True
                    action = (
                        f"switched active provider to {target!r} via the configured "
                        "on_fallback callback (REQ-MVP-039 fallback.target_provider)"
                    )
                elif target is not None:
                    switched = False
                    action = (
                        f"fallback.target_provider={target!r} is configured but no "
                        "on_fallback callback was wired at construction — decision "
                        "recorded only, no switch was performed"
                    )
                else:
                    switched = False
                    action = (
                        "no fallback.target_provider configured — decision recorded "
                        "only; a human must select and configure "
                        "config/provider.toml [fallback].target_provider (pending "
                        "the M6b-3 check-in) before an automatic switch can occur"
                    )
                self._audit_sink.record(
                    {
                        "event": "provider_fallback_triggered",
                        "provider": self._active_provider,
                        "window_turns": self._settings.window_turns,
                        "consecutive_windows": self._settings.consecutive_windows,
                        "threshold_seconds": self._settings.threshold_seconds,
                        "window_median_seconds": window_median,
                        "target_provider": target,
                        "switched": switched,
                        "action": action,
                    }
                )
            return self.triggered
