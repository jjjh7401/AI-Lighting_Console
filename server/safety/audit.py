"""Durable audit log — JSONL, daily rotation, 90-day retention (REQ-MVP-018).

Format decisions (plan.md §A-4, user-decided 2026-07-15): append-only JSONL
files, one file per UTC day (``audit-YYYYMMDD.jsonl``), retained for 90 days.
Storage path decision (M4): ``server/audit_logs/`` (gitignored runtime data).

The four gate event types are executed / approved / rejected / blocked
(AC-MVP-006 completeness). :meth:`record` accepts ANY event dict, which makes
this class a drop-in :class:`server.orchestrator.fallback.AuditSink` — the M3
fallback detector's decisions land in the same durable log.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Runtime audit data lives under server/ per plan.md §A-4 (gitignored).
DEFAULT_AUDIT_DIR = Path(__file__).resolve().parents[1] / "audit_logs"

DEFAULT_RETENTION_DAYS = 90

_FILE_PREFIX = "audit-"
_FILE_SUFFIX = ".jsonl"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AuditLog:
    """Append-only JSONL audit log with daily rotation and retention purge."""

    def __init__(
        self,
        directory: Path | str = DEFAULT_AUDIT_DIR,
        *,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._directory = Path(directory)
        self._retention_days = retention_days
        self._clock = clock
        self._directory.mkdir(parents=True, exist_ok=True)

    # @MX:ANCHOR: [AUTO] single durable audit write point — gate events (executed/
    #   approved/rejected/blocked) AND fallback-detector decisions all land here
    # @MX:REASON: AC-MVP-006/019② reconcile console sends against THIS log 1:1;
    #   a second write path would break completeness accounting (fan_in >= 3)
    def record(self, event: dict) -> None:
        """Append one audit event (AuditSink-compatible); adds a UTC timestamp."""
        now = self._clock()
        enriched = {"ts": now.isoformat(), **event}
        path = self._directory / f"{_FILE_PREFIX}{now:%Y%m%d}{_FILE_SUFFIX}"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")
        self._purge(now)

    def _purge(self, now: datetime) -> None:
        cutoff = (now - timedelta(days=self._retention_days)).date()
        for path in self._directory.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}"):
            stamp = path.name[len(_FILE_PREFIX) : -len(_FILE_SUFFIX)]
            try:
                file_date = datetime.strptime(stamp, "%Y%m%d").date()
            except ValueError:
                continue  # foreign file — never delete what we did not write
            if file_date < cutoff:
                path.unlink()

    def iter_events(self) -> Iterator[dict]:
        """Yield all retained events in file/line order (test/reconciliation aid)."""
        for path in sorted(self._directory.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    # -- the four gate event types (AC-MVP-006) ------------------------------

    def log_executed(
        self, command: str, *, kind: str = "command", ok: bool = True, detail: str = "", **extra
    ) -> None:
        """One console send (every OSC send maps 1:1 to an executed event)."""
        self.record(
            {"event": "executed", "command": command, "kind": kind, "ok": ok, "detail": detail}
            | extra
        )

    def log_approved(self, commands: Sequence[str], **extra) -> None:
        """One human approval decision for a bundle."""
        self.record({"event": "approved", "commands": list(commands)} | extra)

    def log_rejected(self, commands: Sequence[str], **extra) -> None:
        """One human rejection decision for a bundle (all-or-nothing)."""
        self.record({"event": "rejected", "commands": list(commands)} | extra)

    def log_blocked(self, command: str, *, reason: str, **extra) -> None:
        """One blocked command (grammar / risk / lock / health / backup)."""
        self.record({"event": "blocked", "command": command, "reason": reason} | extra)
