"""Round-trip measurement (M5 — M6 prep + AD4-m1 rider).

Operationalizes the acceptance.md "왕복 시간 측정 방법" §1-4 for the live
server:

- §1 start  = the instruction's WebSocket receipt (:meth:`turn_started`)
- §2 end    = the LAST console result received (:meth:`note_console_result`)
- §3 minus  = accumulated human-approval wait
  (:meth:`approval_wait_started` / :meth:`approval_wait_ended`)
- §4 split  = retry turns are recorded but never judged

Judged turns (zero retries, at least one console result, no error) feed the
M3 fallback detector with the approval-subtracted value — the session builds
the orchestrator WITHOUT its own detector wiring so this is the single feed
point (no double counting).

Thread-safety: hooks are called from the WebSocket event loop (turn start) and
from the orchestrator worker thread (console results, approval waits); a lock
guards all mutations.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


class TurnObserver(Protocol):
    """The judged-turn feed shape (matches FallbackDetector.observe_turn)."""

    def observe_turn(self, duration_seconds: float) -> bool: ...


@dataclass(frozen=True)
class TurnRecord:
    """One measured instruction turn (M6 reads these for the corpus report)."""

    started_at: float
    ended_at: float
    approval_wait_seconds: float
    console_results: int
    retries_used: int
    error: bool

    @property
    def measured_seconds(self) -> float:
        """Round-trip per acceptance §1-3: (end - start) - approval wait."""
        return (self.ended_at - self.started_at) - self.approval_wait_seconds

    @property
    def judged(self) -> bool:
        """Acceptance §4: single-turn (zero-retry) executions only, no errors."""
        return not self.error and self.retries_used == 0 and self.console_results > 0


class RoundTripRecorder:
    """Per-server turn measurement; one instruction turn active at a time."""

    def __init__(
        self,
        *,
        detector: TurnObserver | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._detector = detector
        self._clock = clock
        self._lock = threading.Lock()
        self._records: list[TurnRecord] = []
        self._reset_turn()

    def _reset_turn(self) -> None:
        self._active = False
        self._started_at = 0.0
        self._last_result_at: float | None = None
        self._console_results = 0
        self._wait_total = 0.0
        self._wait_started_at: float | None = None

    @property
    def records(self) -> tuple[TurnRecord, ...]:
        with self._lock:
            return tuple(self._records)

    def attach_detector(self, detector: TurnObserver) -> None:
        """Late-bind the judged-turn feed (the detector needs the audit sink,
        which is composed after the recorder in the production wiring)."""
        self._detector = detector

    # -- turn lifecycle hooks --------------------------------------------------

    def turn_started(self) -> None:
        """§1 start event: the instruction arrived over the WebSocket."""
        with self._lock:
            self._reset_turn()
            self._active = True
            self._started_at = self._clock()

    def note_console_result(self) -> None:
        """§2 end-event candidate: one console execution result was received."""
        with self._lock:
            if not self._active:
                return
            self._last_result_at = self._clock()
            self._console_results += 1

    def approval_wait_started(self) -> None:
        """§3: the approval request became visible — the human wait begins."""
        with self._lock:
            if not self._active or self._wait_started_at is not None:
                return
            self._wait_started_at = self._clock()

    def approval_wait_ended(self) -> None:
        """§3: the human decision arrived — accumulate the wait."""
        with self._lock:
            if not self._active or self._wait_started_at is None:
                return
            self._wait_total += self._clock() - self._wait_started_at
            self._wait_started_at = None

    def turn_finished(self, *, retries_used: int, error: bool = False) -> TurnRecord | None:
        """Close the turn; judged turns feed the fallback detector (AD4-m1)."""
        with self._lock:
            if not self._active:
                return None
            if self._wait_started_at is not None:
                # An approval wait left open (e.g. denied by disconnect) still
                # counts as human wait up to now.
                self._wait_total += self._clock() - self._wait_started_at
                self._wait_started_at = None
            ended_at = self._last_result_at if self._last_result_at is not None else self._clock()
            record = TurnRecord(
                started_at=self._started_at,
                ended_at=ended_at,
                approval_wait_seconds=self._wait_total,
                console_results=self._console_results,
                retries_used=retries_used,
                error=error,
            )
            self._records.append(record)
            self._reset_turn()
        if record.judged and self._detector is not None:
            self._detector.observe_turn(record.measured_seconds)
        return record
