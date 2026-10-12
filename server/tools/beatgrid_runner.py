"""Fixed-approval payload runner for the grandMA3 onPC console (card t608).

Three modes behind one entry point. The default is send.

* ``--dry-run``: check the input's sha256 against ``--expect-sha256`` and print the
  lines. No console stack is built, nothing is sent, nothing is logged.
* send (default): check the sha256, then send the file through the app's safety gate.
  ``SafetyGate.screen`` receives the whole file as one bundle with a declared risk, so
  the gate asks its approval port once for all of it. ``PinnedPayloadApproval`` says
  yes only when the requested commands are exactly the pinned lines. After clearance,
  each line goes through ``gate.execution_port`` in file order, and that is the app's
  console client underneath. One JSON record per line goes to ``--log``. The run stops
  at the first line whose outcome is not ``ok``.
* ``--probe``: read only. The gate's audited heartbeat pings the responder, and the
  gate's state port reads the slots the approval depends on. The probe never calls
  ``screen`` or ``execution_port``. ``ReadOnlyPort`` exposes no write method, and any
  write attempt raises ``ProbeWriteRefused`` and exits 5.

Both console modes come from ``build_console_stack``, so the app's audit, lock, health
and backup rules apply. Send mode keeps the app's boot-time session backup, which saves
the showfile on the console. Probe mode skips it.

Exit codes: 0 success; 1 run failure (a line was not ok, the gate raised, or a probe
verdict was not definite); 2 argparse usage error; 3 tree guard (``assert_same_tree``);
4 refusal before any command is sent (malformed expected hash, unreadable or malformed
input, sha256 mismatch, existing log file, gate refusal, failed session backup);
5 read-only guard violation.

``--listen-port`` comes from the shared helper, which forbids a default, so it is
required in every mode, including ``--dry-run`` where it is not used.

UNVERIFIED: the timecode pool path ``DataPool/Timecodes`` is not live-calibrated (see
``server/orchestrator/tools.py``). Its probe reads carry ``path_status="unverified"``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from server.design.console_slots import paged_pool_children
from server.safety.approval import ApprovalPort, ApprovalRequest
from server.safety.bootstrap import ConsoleStack, build_console_stack
from server.safety.console import ConsoleSilentError, LinkTimeouts, StateQueryError
from server.safety.gate import BatchRisk, SafetyGate, ScreenDecision
from server.safety.monitor import HealthMonitor
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

EXIT_OK = 0
EXIT_RUN_FAILED = 1
EXIT_REFUSED = 4
EXIT_READ_ONLY_VIOLATED = 5

APPROVAL_KIND = "t608_fixed_payload"
SEQUENCE_POOL = "DataPool/Sequences"
# UNVERIFIED on the live console; see the module docstring.
TIMECODE_POOL = "DataPool/Timecodes"
PRESET_POOLS = "DataPool/PresetPools"
PROBE_SEQUENCES: tuple[int, ...] = (700, 701, 702, 703)
PROBE_TIMECODES: tuple[int, ...] = (70,)
PROBE_PRESETS: tuple[tuple[int, int], ...] = (
    (2, 351),
    (4, 351),
    (4, 352),
    (22, 97),
    (22, 98),
    (22, 0),
)
READ_METHODS = frozenset(
    {"ping", "query_state", "query_property", "enumerate_fields", "query_properties"}
)
DEFINITE_VERDICTS = frozenset({"occupied", "empty"})
EXCERPT_LIMIT = 200
_SHA256_HEX = re.compile(r"[0-9a-fA-F]{64}")


class InputRefused(Exception):
    """The expected hash, the input file, or the log target is not acceptable."""


class ProbeWriteRefused(RuntimeError):
    """A write-capable console method was requested while the probe is read-only."""


@dataclass(frozen=True)
class Payload:
    """A verified input: its path, its sha256, and its command lines in order."""

    path: str
    sha256: str
    lines: tuple[str, ...]


def load_payload(path: Path, expected_sha256: str) -> Payload:
    """Hash the raw bytes first; split into lines only after the hash matches."""
    if not _SHA256_HEX.fullmatch(expected_sha256):
        raise InputRefused(
            f"--expect-sha256 must be 64 hex characters, got {len(expected_sha256)} characters"
        )
    expected = expected_sha256.lower()
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise InputRefused(f"cannot read input {path}: {error}") from error
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise InputRefused(f"sha256 mismatch: file={digest} expected={expected}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InputRefused(f"input is not UTF-8: {error}") from error
    if "\r" in text:
        raise InputRefused("input contains carriage returns; expected LF line endings")
    lines = text.split("\n")
    if lines[-1] == "":
        # The final newline ends the last line; it is not a line of its own.
        lines.pop()
    if not lines:
        raise InputRefused("input has no command lines")
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            raise InputRefused(f"line {number} is blank; blank lines are refused")
    return Payload(path=str(path), sha256=digest, lines=tuple(lines))


def print_dry_run(payload: Payload, out: TextIO) -> int:
    """Print the verified lines with their numbers. Touches no console and no log."""
    print(f"lines={len(payload.lines)} sha256={payload.sha256}", file=out)
    for number, line in enumerate(payload.lines, start=1):
        print(f"{number}\t{line}", file=out)
    return EXIT_OK


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds")


def _write_record(sink: TextIO, record: Mapping[str, object]) -> None:
    sink.write(json.dumps(record, ensure_ascii=False) + "\n")
    sink.flush()


class PinnedPayloadApproval:
    """Approval port that says yes only to the exact pinned payload.

    The gate asks once per bundle. The answer is yes only when the requested commands
    equal the pinned lines as a multiset, so nothing outside the approved file can ride
    along, and nothing approved can be dropped.
    """

    def __init__(self, lines: Sequence[str]) -> None:
        self._pinned = Counter(lines)
        self.requests: list[tuple[str, ...]] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.requests.append(request.commands)
        return Counter(request.commands) == self._pinned


def _screen_summary(decision: ScreenDecision) -> dict[str, object]:
    by_status = Counter(item.status for item in decision.commands)
    return {
        "cleared": decision.cleared,
        "status": decision.status,
        "notice": decision.notice,
        "commands": len(decision.commands),
        "by_status": dict(sorted(by_status.items())),
    }


def run_send(
    payload: Payload,
    gate: SafetyGate,
    sink: TextIO,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> int:
    """Screen the whole payload through the gate, then send it line by line.

    Nothing reaches the console unless the gate clears the bundle. Once cleared, each
    line goes through ``gate.execution_port`` in file order, and the run stops at the
    first line whose outcome is not ``ok``. An exception from the gate or the link is
    recorded, and it also closes the run, so the log always ends with an ``end`` record.
    """
    _write_record(
        sink,
        {
            "event": "start",
            "input": payload.path,
            "sha256": payload.sha256,
            "lines": len(payload.lines),
            "started_at": _iso(clock()),
        },
    )
    risk = BatchRisk(
        reason=f"t608 fixed approval: sha256 {payload.sha256}, {len(payload.lines)} lines",
        kind=APPROVAL_KIND,
    )
    try:
        decision = gate.screen(payload.lines, risk=risk)
    except Exception as error:  # the run must still close its log
        _write_record(
            sink,
            {
                "event": "end",
                "sent": 0,
                "stopped_at": None,
                "status": "gate_error",
                "detail": f"{type(error).__name__}: {error}",
                "ended_at": _iso(clock()),
            },
        )
        return EXIT_RUN_FAILED
    _write_record(sink, {"event": "screen", "at": _iso(clock()), **_screen_summary(decision)})
    if not decision.cleared:
        _write_record(
            sink,
            {
                "event": "end",
                "sent": 0,
                "stopped_at": None,
                "status": "refused_by_gate",
                "ended_at": _iso(clock()),
            },
        )
        return EXIT_REFUSED

    sent = 0
    stopped_at: int | None = None
    for index, line in enumerate(payload.lines, start=1):
        sent_at = clock()
        try:
            result = gate.execution_port.execute(line)
            status, detail = result.outcome, result.detail
        except Exception as error:  # the run must still close its log
            status, detail = "error", f"{type(error).__name__}: {error}"
        responded_at = clock()
        _write_record(
            sink,
            {
                "index": index,
                "line": line,
                "sent_at": _iso(sent_at),
                "responded_at": _iso(responded_at),
                "status": status,
                "detail": detail,
            },
        )
        sent += 1
        if status != "ok":
            stopped_at = index
            break
    _write_record(
        sink,
        {
            "event": "end",
            "sent": sent,
            "stopped_at": stopped_at,
            "status": "ok" if stopped_at is None else "stopped",
            "ended_at": _iso(clock()),
        },
    )
    return EXIT_OK if stopped_at is None else EXIT_RUN_FAILED


class ReadOnlyPort:
    """Read face of the safety gate for the probe: the audited heartbeat and the state port.

    ``execute`` and ``deploy_plugin`` exist only to refuse. Each attempt is recorded in
    ``calls`` before ``ProbeWriteRefused`` is raised, so a violation stays visible.
    """

    def __init__(self, gate: SafetyGate) -> None:
        self._gate = gate
        self._reads = gate.state_port
        self.calls: list[str] = []

    @property
    def responder_version(self) -> str | None:
        return self._gate.monitor.responder_version

    def ping(self) -> str:
        """Audited heartbeat. Returns the resulting health state."""
        self.calls.append("ping")
        return self._gate.heartbeat()

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append("query_state")
        return self._reads.query_state(path, offset=offset)

    def query_property(self, path: str, property_name: str) -> dict:
        self.calls.append("query_property")
        return self._reads.query_property(path, property_name)

    def enumerate_fields(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append("enumerate_fields")
        return self._reads.enumerate_fields(path, offset=offset)

    def query_properties(
        self, path: str, property_names: Sequence[str], *, offset: int | None = None
    ) -> dict:
        self.calls.append("query_properties")
        return self._reads.query_properties(path, property_names, offset=offset)

    def execute(self, command: str) -> object:
        self.calls.append("execute")
        raise ProbeWriteRefused("probe refuses execute: only read methods are allowed")

    def deploy_plugin(self, name: str, lua_source: str) -> object:
        self.calls.append("deploy_plugin")
        raise ProbeWriteRefused("probe refuses deploy_plugin: only read methods are allowed")


def _excerpt(text: str) -> str:
    return text[:EXCERPT_LIMIT]


def _node_exists(payload: object) -> bool:
    """A query_state payload that names a real console object carries a dict node."""
    return isinstance(payload, dict) and isinstance(payload.get("node"), dict)


def _classify_container(port: ReadOnlyPort, path: str) -> tuple[str, str]:
    """Verdict for a container path: resolved, path_unverified, or unreadable.

    A "not found" reply on a container means the path itself did not resolve. It is
    not evidence that the container is empty.
    """
    try:
        payload = port.query_state(path)
    except ConsoleSilentError as error:
        return "unreadable", _excerpt(str(error))
    except StateQueryError as error:
        text = str(error)
        if "not found" in text.lower():
            return "path_unverified", _excerpt(text)
        return "unreadable", _excerpt(text)
    return "resolved", _excerpt(json.dumps(payload, ensure_ascii=False))


def _classify_slot(port: ReadOnlyPort, path: str, container_verdict: str) -> tuple[str, str]:
    """Verdict for one pool slot, using the same rules as the app's slot read.

    An error containing "not found" under a resolved container is the console stating
    that the slot is empty. A timeout or any other error is unreadable. An ok reply
    without a node is a hole, which is empty.
    """
    if container_verdict != "resolved":
        return container_verdict, ""
    try:
        payload = port.query_state(path)
    except ConsoleSilentError as error:
        return "unreadable", _excerpt(str(error))
    except StateQueryError as error:
        text = str(error)
        if "not found" in text.lower():
            return "empty", _excerpt(text)
        return "unreadable", _excerpt(text)
    verdict = "occupied" if _node_exists(payload) else "empty"
    return verdict, _excerpt(json.dumps(payload, ensure_ascii=False))


def _paging_query(port: ReadOnlyPort) -> Callable[[str, Mapping[str, object]], object | None]:
    """Adapt the read port to the query shape ``paged_pool_children`` expects.

    Any failure becomes ``None``, which the paged reader reports as an unreadable pool.
    """

    def query(probe_id: str, arguments: Mapping[str, object]) -> object | None:
        path = str(arguments["path"])
        offset = arguments.get("offset", 0)
        try:
            return port.query_state(path, offset=offset if isinstance(offset, int) else 0)
        except StateQueryError:
            return None

    return query


def _read_preset_pool(
    port: ReadOnlyPort, pool: int, preset_root_verdict: str
) -> tuple[str, dict[int, str | None] | None, str]:
    """Read one preset pool completely. Returns (verdict, slot map or None, excerpt)."""
    path = f"{PRESET_POOLS}/{pool}"
    if preset_root_verdict != "resolved":
        return preset_root_verdict, None, ""
    verdict, excerpt = _classify_container(port, path)
    if verdict != "resolved":
        return verdict, None, excerpt
    children = paged_pool_children(_paging_query(port), path, probe_id=f"t608-probe-pool-{pool}")
    if children is None:
        return "unreadable", None, "paged pool read incomplete or unreadable"
    return "resolved", children, excerpt


def _emit(sinks: Sequence[TextIO], record: Mapping[str, object]) -> None:
    line = json.dumps(record, ensure_ascii=False)
    for sink in sinks:
        sink.write(line + "\n")
        sink.flush()


def run_probe(stack: ConsoleStack, sinks: Sequence[TextIO]) -> int:
    """Read-only check of the responder and of the slots the approval depends on."""
    guard = ReadOnlyPort(stack.gate)
    slot_verdicts: list[str] = []
    try:
        ping_state = guard.ping()
        ping_online = ping_state == HealthMonitor.ONLINE
        version = guard.responder_version
        _emit(
            sinks,
            {
                "check": "ping",
                "target": "ping",
                "verdict": "online" if ping_online else "not_online",
                "state": ping_state,
                "responder_version": version,
            },
        )

        roots: dict[str, str] = {}
        for root in (SEQUENCE_POOL, TIMECODE_POOL, PRESET_POOLS):
            verdict, excerpt = _classify_container(guard, root)
            roots[root] = verdict
            _emit(
                sinks, {"check": "root", "target": root, "verdict": verdict, "raw_excerpt": excerpt}
            )

        for number in PROBE_SEQUENCES:
            path = f"{SEQUENCE_POOL}/{number}"
            verdict, excerpt = _classify_slot(guard, path, roots[SEQUENCE_POOL])
            slot_verdicts.append(verdict)
            _emit(
                sinks,
                {
                    "check": "sequence",
                    "target": str(number),
                    "path": path,
                    "verdict": verdict,
                    "raw_excerpt": excerpt,
                },
            )

        for number in PROBE_TIMECODES:
            path = f"{TIMECODE_POOL}/{number}"
            verdict, excerpt = _classify_slot(guard, path, roots[TIMECODE_POOL])
            slot_verdicts.append(verdict)
            _emit(
                sinks,
                {
                    "check": "timecode",
                    "target": str(number),
                    "path": path,
                    "path_status": "unverified",
                    "verdict": verdict,
                    "raw_excerpt": excerpt,
                },
            )

        pools: dict[int, tuple[str, dict[int, str | None] | None, str]] = {}
        for pool, slot in PROBE_PRESETS:
            if pool not in pools:
                pools[pool] = _read_preset_pool(guard, pool, roots[PRESET_POOLS])
            pool_verdict, children, pool_excerpt = pools[pool]
            if pool_verdict != "resolved" or children is None:
                verdict, excerpt = pool_verdict, pool_excerpt
            else:
                verdict = "occupied" if slot in children else "empty"
                excerpt = pool_excerpt
            slot_verdicts.append(verdict)
            _emit(
                sinks,
                {
                    "check": "preset",
                    "target": f"{pool}.{slot}",
                    "path": f"{PRESET_POOLS}/{pool}",
                    "slot": slot,
                    "verdict": verdict,
                    "raw_excerpt": excerpt,
                },
            )
    except ProbeWriteRefused as error:
        _emit(sinks, {"event": "refused", "detail": str(error)})
        return EXIT_READ_ONLY_VIOLATED

    not_read = sorted(set(guard.calls) - READ_METHODS)
    if not_read:
        _emit(sinks, {"event": "refused", "detail": f"non-read calls recorded: {not_read}"})
        return EXIT_READ_ONLY_VIOLATED

    all_definite = ping_online and all(verdict in DEFINITE_VERDICTS for verdict in slot_verdicts)
    _emit(
        sinks,
        {
            "event": "summary",
            "ping": ping_state,
            "responder_version": version,
            "all_definite": all_definite,
        },
    )
    return EXIT_OK if all_definite else EXIT_RUN_FAILED


@contextmanager
def open_console_stack(
    host: str,
    port: int,
    listen_port: int,
    *,
    wait: float,
    approval_port: ApprovalPort | None,
    session_backup: bool,
) -> Iterator[ConsoleStack]:
    """Compose the app's console stack and stop its bridge when the run ends.

    This is the only place that opens sockets. Tests never call it.
    """
    stack = build_console_stack(
        send_host=host,
        send_port=port,
        receive_port=listen_port,
        approval_port=approval_port,
        timeouts=LinkTimeouts(
            exec_confirm_seconds=wait,
            ping_seconds=wait,
            state_query_seconds=wait,
        ),
        attempt_session_backup=session_backup,
    )
    try:
        yield stack
    finally:
        stack.stop()


def _open_new_log(path: str) -> TextIO:
    """Open a log that must not exist yet, so an earlier record is never overwritten."""
    try:
        return open(path, "x", encoding="utf-8")
    except FileExistsError as error:
        raise InputRefused(f"log file already exists: {path}") from error


def _run_probe_command(args: argparse.Namespace) -> int:
    sinks: list[TextIO] = [sys.stdout]
    log_sink: TextIO | None = None
    if args.log:
        try:
            log_sink = _open_new_log(args.log)
        except InputRefused as error:
            print(f"refused: {error}", file=sys.stderr)
            return EXIT_REFUSED
        sinks.append(log_sink)
    try:
        with open_console_stack(
            args.host,
            args.port,
            args.listen_port,
            wait=args.wait,
            approval_port=None,
            session_backup=False,
        ) as stack:
            return run_probe(stack, sinks)
    except OSError as error:
        _emit(sinks, {"event": "error", "detail": f"{type(error).__name__}: {error}"})
        return EXIT_RUN_FAILED
    finally:
        if log_sink is not None:
            log_sink.close()


def _run_send_command(args: argparse.Namespace, payload: Payload) -> int:
    try:
        log_sink = _open_new_log(args.log)
    except InputRefused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    with log_sink:
        try:
            with open_console_stack(
                args.host,
                args.port,
                args.listen_port,
                wait=args.wait,
                approval_port=PinnedPayloadApproval(payload.lines),
                session_backup=True,
            ) as stack:
                if not stack.session_backup_ok:
                    _write_record(
                        log_sink,
                        {
                            "event": "end",
                            "sent": 0,
                            "stopped_at": None,
                            "status": "refused_session_backup",
                            "detail": stack.session_backup_detail,
                        },
                    )
                    return EXIT_REFUSED
                return run_send(payload, stack.gate, log_sink)
        except OSError as error:
            _write_record(
                log_sink, {"event": "error", "detail": f"{type(error).__name__}: {error}"}
            )
            return EXIT_RUN_FAILED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", help="payload file to send (send and --dry-run)")
    parser.add_argument(
        "--expect-sha256",
        help="the approved sha256 of --input, as 64 hex characters (send and --dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="check the sha256 and print the lines; send nothing, log nothing",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="read only: audited ping and state reads; never writes to the console",
    )
    parser.add_argument(
        "--log",
        help="new JSONL log file (required for send; optional for --probe; never overwritten)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="onPC host (default: %(default)s)")
    parser.add_argument(
        "--port", type=int, default=8000, help="onPC OSC UDP input port (default: %(default)s)"
    )
    add_listen_port_argument(parser)
    parser.add_argument(
        "--wait", type=float, default=5.0, help="reply timeout in seconds (default: %(default)s)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.dry_run and args.probe:
        parser.error("--dry-run and --probe are mutually exclusive")
    if args.probe:
        return _run_probe_command(args)
    if not args.input or not args.expect_sha256:
        parser.error("--input and --expect-sha256 are required for send and --dry-run")
    try:
        payload = load_payload(Path(args.input), args.expect_sha256)
    except InputRefused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    if args.dry_run:
        return print_dry_run(payload, sys.stdout)
    if not args.log:
        parser.error("--log is required for send")
    return _run_send_command(args, payload)


if __name__ == "__main__":
    raise SystemExit(main())
