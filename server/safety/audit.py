"""Durable audit log — JSONL, daily rotation, 90-day retention (REQ-MVP-018).

Format decisions (plan.md §A-4, user-decided 2026-07-15): append-only JSONL
files, one file per UTC day (``audit-YYYYMMDD.jsonl``), retained for 90 days.
Storage path decision (M4): ``server/audit_logs/`` (gitignored runtime data).

The four gate event types are executed / approved / rejected / blocked
(AC-MVP-006 completeness). :meth:`record` accepts ANY event dict, which makes
this class a drop-in :class:`server.orchestrator.fallback.AuditSink` — the M3
fallback detector's decisions land in the same durable log.

**Probe traffic split (growth fix, 2026-08-15 handoff item 2).** The gate's
read-only probes (``state_query`` / ``property_query`` / ``heartbeat``) run
~10/second from the background pollers and measured 99.9 % of the log volume
(819 MB across 5 days, ~200 MB/day). They now land in a SECOND file family
``probe-YYYYMMDD.jsonl`` with (a) short retention (default 2 days) and (b) a
per-day byte cap — once a day's probe file hits the cap, one
``probe_log_capped`` marker is appended and further probe events that day are
dropped. Command/gate/deploy writes are untouched: the 1:1 "every console
send" durability invariant covers them at full 90-day retention, and a deploy
sub-send (an event carrying ``deploy_of``) NEVER routes to the probe family
even when its kind is a query. Both iterators read both families, so
reconciliation (:meth:`iter_events`) still sees every retained event.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Runtime audit data lives under server/ per plan.md §A-4 (gitignored).
DEFAULT_AUDIT_DIR = Path(__file__).resolve().parents[1] / "audit_logs"

DEFAULT_RETENTION_DAYS = 90
DEFAULT_PROBE_RETENTION_DAYS = 2
# ~200 MB/day of probe JSONL was measured on 2026-08-15; 64 MiB keeps roughly
# a third of a day's densest traffic while bounding total growth to
# cap × retention (128 MiB) worst case.
DEFAULT_PROBE_DAILY_MAX_BYTES = 64 << 20

_FILE_PREFIX = "audit-"
_PROBE_PREFIX = "probe-"
_FILE_SUFFIX = ".jsonl"

#: Read-only probe kinds — high-volume, low-value; routed to the probe family.
PROBE_KINDS = frozenset({"state_query", "property_query", "heartbeat"})


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AuditLog:
    """Append-only JSONL audit log with daily rotation and retention purge."""

    def __init__(
        self,
        directory: Path | str = DEFAULT_AUDIT_DIR,
        *,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        probe_retention_days: int = DEFAULT_PROBE_RETENTION_DAYS,
        probe_daily_max_bytes: int = DEFAULT_PROBE_DAILY_MAX_BYTES,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._directory = Path(directory)
        self._retention_days = retention_days
        self._probe_retention_days = probe_retention_days
        self._probe_daily_max_bytes = probe_daily_max_bytes
        self._clock = clock
        # The day whose probe file already carries its probe_log_capped marker
        # (restart may re-mark once — harmless; a dropped marker would not be).
        self._probe_capped_day: str | None = None
        self._directory.mkdir(parents=True, exist_ok=True)
        self._compact_legacy(self._clock())

    @staticmethod
    def _is_probe(event: dict) -> bool:
        """Read-only probe traffic — NEVER a deploy sub-send (``deploy_of``),
        whose 1:1 wire-send accounting needs full retention."""
        return (
            event.get("event") == "executed"
            and event.get("kind") in PROBE_KINDS
            and "deploy_of" not in event
        )

    # @MX:ANCHOR: [AUTO] single durable audit write point — gate events (executed/
    #   approved/rejected/blocked) AND fallback-detector decisions all land here
    # @MX:REASON: AC-MVP-006/019② reconcile console sends against THIS log 1:1;
    #   a second write path would break completeness accounting (fan_in >= 3)
    def record(self, event: dict) -> None:
        """Append one audit event (AuditSink-compatible); adds a UTC timestamp.

        Probe events (:data:`PROBE_KINDS`) route to the capped, short-retention
        ``probe-`` family; everything else is durable ``audit-`` (90 days).
        """
        now = self._clock()
        enriched = {"ts": now.isoformat(), **event}
        day = f"{now:%Y%m%d}"
        if self._is_probe(event):
            path = self._directory / f"{_PROBE_PREFIX}{day}{_FILE_SUFFIX}"
            if not self._probe_write_allowed(path, day):
                return
        else:
            path = self._directory / f"{_FILE_PREFIX}{day}{_FILE_SUFFIX}"
        # default=str: a value that cannot be JSON-serialized is degraded to
        # its str() form rather than losing the whole event — a demoted value
        # is recoverable; a dropped audit line is not (see the class @MX:ANCHOR).
        line = json.dumps(enriched, ensure_ascii=False, default=str) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        self._purge(now)

    def _probe_write_allowed(self, path: Path, day: str) -> bool:
        """Enforce the per-day probe byte cap: at the crossing, append ONE
        ``probe_log_capped`` marker, then drop the day's remaining probes."""
        try:
            size = path.stat().st_size
        except OSError:
            return True  # no file yet — first write of the day
        if size < self._probe_daily_max_bytes:
            return True
        if self._probe_capped_day != day:
            self._probe_capped_day = day
            marker = {
                "ts": self._clock().isoformat(),
                "event": "probe_log_capped",
                "cap_bytes": self._probe_daily_max_bytes,
            }
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(marker, ensure_ascii=False) + "\n")
        return False

    def _purge(self, now: datetime) -> None:
        for prefix, retention in (
            (_FILE_PREFIX, self._retention_days),
            (_PROBE_PREFIX, self._probe_retention_days),
        ):
            cutoff = (now - timedelta(days=retention)).date()
            for path in self._directory.glob(f"{prefix}*{_FILE_SUFFIX}"):
                stamp = path.name[len(prefix) : -len(_FILE_SUFFIX)]
                try:
                    file_date = datetime.strptime(stamp, "%Y%m%d").date()
                except ValueError:
                    continue  # foreign file — never delete what we did not write
                if file_date < cutoff:
                    path.unlink()

    def _compact_legacy(self, now: datetime) -> None:
        """One-time (idempotent) startup split of PRE-SPLIT mixed files.

        Before 2026-08-15 every probe event landed in ``audit-*.jsonl`` —
        819 MB across 5 days, 99.9 % probes. Streaming each audit file once:
        probe lines move to that day's ``probe-`` file (where retention/cap
        then apply), everything else is rewritten in place atomically
        (same-dir temp + ``os.replace``). After the first pass the audit
        family is small, so later startups re-scan only kilobytes.
        """
        probe_cutoff = (now - timedelta(days=self._probe_retention_days)).date()
        for path in sorted(self._directory.glob(f"{_FILE_PREFIX}*{_FILE_SUFFIX}")):
            stamp = path.name[len(_FILE_PREFIX) : -len(_FILE_SUFFIX)]
            try:
                file_date = datetime.strptime(stamp, "%Y%m%d").date()
            except ValueError:
                continue  # foreign file — never rewrite what we did not write
            probe_path = self._directory / f"{_PROBE_PREFIX}{stamp}{_FILE_SUFFIX}"
            keep_probes = file_date >= probe_cutoff
            moved = 0
            tmp = path.with_name(path.name + ".compact.tmp")
            with (
                path.open("r", encoding="utf-8") as source,
                tmp.open("w", encoding="utf-8") as kept,
                probe_path.open("a", encoding="utf-8") as probes,
            ):
                for line in source:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        kept.write(line)  # never drop an unparseable audit line
                        continue
                    if self._is_probe(event):
                        moved += 1
                        if keep_probes:
                            probes.write(line)
                    else:
                        kept.write(line)
            if moved:
                os.replace(tmp, path)
            else:
                tmp.unlink(missing_ok=True)
            if probe_path.exists() and probe_path.stat().st_size == 0:
                probe_path.unlink()

    def _sorted_files(self, *, include_probes: bool = True) -> list[Path]:
        """Both families in one deterministic order: by day, ``audit-`` before
        ``probe-`` within a day (cross-family intra-day interleaving is not
        preserved — no consumer asserts it)."""
        prefixes = [_FILE_PREFIX] + ([_PROBE_PREFIX] if include_probes else [])
        files: list[tuple[str, int, Path]] = []
        for rank, prefix in enumerate(prefixes):
            for path in self._directory.glob(f"{prefix}*{_FILE_SUFFIX}"):
                stamp = path.name[len(prefix) : -len(_FILE_SUFFIX)]
                files.append((stamp, rank, path))
        return [path for _stamp, _rank, path in sorted(files)]

    def iter_events(self) -> Iterator[dict]:
        """Yield all retained events in file/line order (test/reconciliation aid)."""
        for path in self._sorted_files():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    def iter_events_reversed(
        self, *, chunk_bytes: int = 1 << 22, include_probes: bool = True
    ) -> Iterator[dict]:
        """Yield all retained events NEWEST-FIRST, reading backwards in bounded
        chunks (default 4 MiB).

        Exists because :meth:`iter_events` materialises every retained day as
        one decoded string — measured 2026-08-15 at 709 MB of JSONL (a
        background poller writes ~10 probe events/second), which turned every
        cue-monitor snapshot into a whole-log parse: hundreds of MB of
        transient objects per UI refresh, GC pressure that starved the event
        loop, and multi-second static responses. A consumer that wants "the
        most recent N matching events" stops this iterator after N hits and
        never touches more than a chunk or two.

        ``include_probes=False`` skips the ``probe-`` family entirely — the
        cue-monitor history reader filters those kinds out anyway, so it never
        has to wade through them.
        """
        for path in reversed(self._sorted_files(include_probes=include_probes)):
            with path.open("rb") as handle:
                handle.seek(0, 2)
                position = handle.tell()
                carry = b""
                while position > 0:
                    step = min(chunk_bytes, position)
                    position -= step
                    handle.seek(position)
                    buffer = handle.read(step) + carry
                    lines = buffer.split(b"\n")
                    # The first split piece may be a PARTIAL line whose head
                    # lives in the previous (not yet read) chunk — carry it.
                    carry = lines[0] if position > 0 else b""
                    complete = lines[1:] if position > 0 else lines
                    for line in reversed(complete):
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
