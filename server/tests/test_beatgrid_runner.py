"""Tests for the t608 fixed-approval runner. Every console here is an in-process fake.

The safety gate is the real ``SafetyGate``, wrapped around ``FakeConsole``, so the
gate's clearance, approval and audit rules run as they do in the app. No test builds a
console stack or opens a socket. The stack is reached only through
``open_console_stack``, and each mode test replaces that function.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import socket
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from server.safety.approval import ApprovalItem, ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.console import ConsoleSilentError, ExecOutcome, StateQueryError
from server.safety.gate import SafetyGate
from server.tools import beatgrid_runner as runner

SAMPLE_LINES = ("ClearAll", "Group 4", "Store Preset 2.351")
RESPONDER_VERSION = "1.6.6"  # EXPECTED_RESPONDER_VERSION in server/safety/responder_version.py
MODULE_PATH = Path(runner.__file__)
CONSOLE_READ_METHODS = frozenset(
    {"ping", "query_state", "query_property", "enumerate_fields", "query_properties"}
)


class FakeConsole:
    """In-process stand-in for the console port the gate wraps. Never touches a socket."""

    responder_version = RESPONDER_VERSION

    def __init__(self, *, pings: bool = True, failing: frozenset[str] = frozenset()) -> None:
        self.calls: list[str] = []
        self.executed: list[str] = []
        self.pings = pings
        self.failing = failing
        self.objects: dict[str, dict] = {}
        self.silent: set[str] = set()
        self.pools: dict[str, list[tuple[int, str]]] = {}

    def ping(self) -> bool:
        self.calls.append("ping")
        return self.pings

    def execute(self, command: str) -> ExecOutcome:
        self.calls.append("execute")
        self.executed.append(command)
        if command in self.failing:
            return ExecOutcome(status="failed", detail="console said no")
        return ExecOutcome(status="ok", detail="done")

    def deploy_plugin(self, name: str, lua_source: str) -> ExecOutcome:
        self.calls.append("deploy_plugin")
        return ExecOutcome(status="failed", detail="must never be reached")

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append("query_state")
        if path in self.silent:
            raise ConsoleSilentError(f"no state reply for {path!r}")
        if path in self.pools:
            return self._pool_window(path, offset)
        if path in self.objects:
            return self.objects[path]
        raise StateQueryError(f"path segment not found: {path}")

    def query_property(self, path: str, property_name: str) -> dict:
        self.calls.append("query_property")
        raise StateQueryError(f"path segment not found: {path}")

    def enumerate_fields(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append("enumerate_fields")
        raise StateQueryError(f"path segment not found: {path}")

    def query_properties(
        self, path: str, property_names: Sequence[str], *, offset: int | None = None
    ) -> dict:
        self.calls.append("query_properties")
        raise StateQueryError(f"path segment not found: {path}")

    def _pool_window(self, path: str, offset: int) -> dict:
        # The responder caps children per reply at 24 and echoes the offset of a later window.
        children = self.pools[path]
        window = children[offset : offset + 24]
        payload: dict = {
            "ok": True,
            "node": {"childCount": len(children)},
            "children": [{"i": number, "name": name} for number, name in window],
            "truncated": offset + len(window) < len(children),
        }
        if offset:
            payload["offset"] = offset
        return payload


def healthy_console() -> FakeConsole:
    """A responder where every probe read is definite and the expected verdicts are known."""
    console = FakeConsole()
    console.objects["DataPool/Sequences"] = {"ok": True, "node": {"childCount": 2}}
    console.objects["DataPool/Timecodes"] = {"ok": True, "node": {"childCount": 1}}
    console.objects["DataPool/PresetPools"] = {"ok": True, "node": {"childCount": 3}}
    console.objects["DataPool/Sequences/700"] = {"ok": True, "node": {"name": "LDBEAT FOH"}}
    console.objects["DataPool/Sequences/702"] = {"ok": True, "node": {"name": "other show"}}
    console.objects["DataPool/Timecodes/70"] = {"ok": True, "node": {"name": "LDBEAT TC 70"}}
    # Pool 2 holds 31 presets, and slot 351 sits past the first window, so paging is exercised.
    console.pools["DataPool/PresetPools/2"] = [(n, f"P{n}") for n in range(1, 31)] + [
        (351, "SCR POS")
    ]
    console.pools["DataPool/PresetPools/4"] = [(352, "SCR COLOR")]
    console.pools["DataPool/PresetPools/22"] = [(97, "FX A"), (98, "FX B")]
    return console


EXPECTED_HEALTHY = {
    "sequence:700": "occupied",
    "sequence:701": "empty",
    "sequence:702": "occupied",
    "sequence:703": "empty",
    "timecode:70": "occupied",
    "preset:2.351": "occupied",
    "preset:4.351": "empty",
    "preset:4.352": "occupied",
    "preset:22.97": "occupied",
    "preset:22.98": "occupied",
    "preset:22.0": "empty",
}


def write_payload(directory: Path, lines: tuple[str, ...] = SAMPLE_LINES) -> tuple[Path, str]:
    path = directory / "payload.txt"
    data = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def fake_clock():
    base = datetime(2026, 10, 12, 12, 0, 0, tzinfo=UTC)
    ticks = iter(range(10_000))
    return lambda: base + timedelta(milliseconds=next(ticks))


def parse_records(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def probe_verdicts(stdout: str) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    for record in parse_records(stdout):
        check = record.get("check")
        if check == "sequence":
            verdicts[f"sequence:{record['target']}"] = record["verdict"]
        elif check == "timecode":
            verdicts[f"timecode:{record['target']}"] = record["verdict"]
        elif check == "preset":
            verdicts[f"preset:{record['target']}"] = record["verdict"]
    return verdicts


def make_gate(tmp_path: Path, console: FakeConsole, approval=None) -> SafetyGate:
    return SafetyGate(
        console=console,
        audit=AuditLog(tmp_path / "audit"),
        approval_port=approval,
    )


def use_stack(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    console: FakeConsole,
    seen: list[dict] | None = None,
    *,
    session_backup_ok: bool = True,
) -> None:
    """Replace the stack factory with one that wraps the fake console in a real gate."""

    @contextmanager
    def fake_open(host, port, listen_port, *, wait, approval_port, session_backup) -> Iterator:
        if seen is not None:
            seen.append({"approval_port": approval_port, "session_backup": session_backup})
        gate = make_gate(tmp_path, console, approval_port)
        yield SimpleNamespace(
            gate=gate,
            session_backup_ok=session_backup_ok,
            session_backup_detail="fake session backup",
        )

    monkeypatch.setattr(runner, "open_console_stack", fake_open)


def forbid_console(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("no console stack may be built in this path")

    monkeypatch.setattr(runner, "open_console_stack", refuse)


# -- input handling -----------------------------------------------------------------------


def test_sha_mismatch_refuses_before_any_console_contact(tmp_path, monkeypatch, capsys):
    path, _ = write_payload(tmp_path)
    log = tmp_path / "run.jsonl"
    forbid_console(monkeypatch)

    code = runner.main(
        [
            "--input",
            str(path),
            "--expect-sha256",
            "0" * 64,
            "--log",
            str(log),
            "--listen-port",
            "9000",
        ]
    )

    assert code == runner.EXIT_REFUSED
    assert "sha256 mismatch" in capsys.readouterr().err
    assert not log.exists()


def test_malformed_expected_hash_is_refused(tmp_path, monkeypatch, capsys):
    path, _ = write_payload(tmp_path)
    forbid_console(monkeypatch)

    code = runner.main(
        ["--input", str(path), "--expect-sha256", "abc", "--dry-run", "--listen-port", "9000"]
    )

    assert code == runner.EXIT_REFUSED
    assert "64 hex characters" in capsys.readouterr().err


def test_expected_hash_comparison_is_case_insensitive(tmp_path):
    path, digest = write_payload(tmp_path)

    payload = runner.load_payload(path, digest.upper())

    assert payload.sha256 == digest
    assert payload.lines == SAMPLE_LINES


@pytest.mark.parametrize(
    "content",
    [b"ClearAll\n\nGroup 4\n", b"ClearAll\r\nGroup 4\n", b"   \nGroup 4\n"],
)
def test_blank_and_carriage_return_lines_are_refused(tmp_path, content):
    path = tmp_path / "payload.txt"
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()

    with pytest.raises(runner.InputRefused):
        runner.load_payload(path, digest)


def test_trailing_newline_does_not_create_a_blank_line(tmp_path):
    path = tmp_path / "payload.txt"
    path.write_bytes(b"A\nB\n")
    payload = runner.load_payload(path, hashlib.sha256(b"A\nB\n").hexdigest())
    assert payload.lines == ("A", "B")

    bare = tmp_path / "bare.txt"
    bare.write_bytes(b"A\nB")
    payload = runner.load_payload(bare, hashlib.sha256(b"A\nB").hexdigest())
    assert payload.lines == ("A", "B")


# -- dry-run ------------------------------------------------------------------------------


def test_dry_run_prints_lines_and_never_builds_a_stack(tmp_path, monkeypatch, capsys):
    path, digest = write_payload(tmp_path)
    forbid_console(monkeypatch)

    code = runner.main(
        ["--input", str(path), "--expect-sha256", digest, "--dry-run", "--listen-port", "9000"]
    )

    out = capsys.readouterr().out.splitlines()
    assert code == runner.EXIT_OK
    assert out[0] == f"lines={len(SAMPLE_LINES)} sha256={digest}"
    assert out[1:] == [f"{n}\t{line}" for n, line in enumerate(SAMPLE_LINES, start=1)]


# -- approval binding ---------------------------------------------------------------------


def test_pinned_approval_says_yes_only_to_exactly_the_pinned_lines():
    approval = runner.PinnedPayloadApproval(("ClearAll", "Group 4", "Group 4"))

    def request(*commands: str) -> ApprovalRequest:
        return ApprovalRequest(
            items=tuple(ApprovalItem(command=c, risk_reasons=()) for c in commands)
        )

    assert approval.request_approval(request("ClearAll", "Group 4", "Group 4")) is True
    assert approval.request_approval(request("Group 4", "ClearAll", "Group 4")) is True
    assert approval.request_approval(request("ClearAll", "Group 4")) is False
    assert approval.request_approval(request("ClearAll", "Group 4", "Group 4", "Group 9")) is False


# -- send ---------------------------------------------------------------------------------


def test_send_clears_the_pinned_payload_as_one_request_and_sends_in_order(tmp_path):
    path, digest = write_payload(tmp_path)
    payload = runner.load_payload(path, digest)
    console = FakeConsole()
    approval = runner.PinnedPayloadApproval(payload.lines)
    gate = make_gate(tmp_path, console, approval)
    sink = io.StringIO()

    code = runner.run_send(payload, gate, sink, clock=fake_clock())

    records = parse_records(sink.getvalue())
    assert code == runner.EXIT_OK
    assert approval.requests == [payload.lines]  # one approval request covers the whole file
    screen = next(r for r in records if r["event"] == "screen")
    assert screen["cleared"] is True
    assert console.executed == list(payload.lines)  # file order, nothing extra
    line_records = [r for r in records if "index" in r]
    assert [r["index"] for r in line_records] == [1, 2, 3]
    assert all(r["status"] == "ok" for r in line_records)
    assert all(r["sent_at"] <= r["responded_at"] for r in line_records)
    assert records[-1]["event"] == "end"
    assert records[-1]["status"] == "ok"
    assert records[-1]["stopped_at"] is None


def test_send_refuses_when_the_approval_does_not_match_the_file(tmp_path):
    path, digest = write_payload(tmp_path)
    payload = runner.load_payload(path, digest)
    console = FakeConsole()
    approval = runner.PinnedPayloadApproval(payload.lines + ("Group 9",))
    gate = make_gate(tmp_path, console, approval)
    sink = io.StringIO()

    code = runner.run_send(payload, gate, sink, clock=fake_clock())

    records = parse_records(sink.getvalue())
    assert code == runner.EXIT_REFUSED
    assert console.executed == []
    assert records[-1]["status"] == "refused_by_gate"


def test_send_stops_at_the_first_line_the_console_does_not_confirm(tmp_path):
    path, digest = write_payload(tmp_path)
    payload = runner.load_payload(path, digest)
    console = FakeConsole(failing=frozenset({"Group 4"}))
    gate = make_gate(tmp_path, console, runner.PinnedPayloadApproval(payload.lines))
    sink = io.StringIO()

    code = runner.run_send(payload, gate, sink, clock=fake_clock())

    records = parse_records(sink.getvalue())
    assert code == runner.EXIT_RUN_FAILED
    assert console.executed == ["ClearAll", "Group 4"]
    assert records[-2]["index"] == 2
    assert records[-2]["status"] == "failed"
    assert records[-1]["stopped_at"] == 2
    assert records[-1]["status"] == "stopped"


def test_send_records_a_gate_exception_and_closes_the_log(tmp_path, monkeypatch):
    path, digest = write_payload(tmp_path)
    payload = runner.load_payload(path, digest)
    console = FakeConsole()
    gate = make_gate(tmp_path, console, runner.PinnedPayloadApproval(payload.lines))

    def boom(*args, **kwargs):
        raise RuntimeError("gate fell over")

    monkeypatch.setattr(gate, "screen", boom)
    sink = io.StringIO()

    code = runner.run_send(payload, gate, sink, clock=fake_clock())

    records = parse_records(sink.getvalue())
    assert code == runner.EXIT_RUN_FAILED
    assert console.executed == []
    assert records[-1]["status"] == "gate_error"
    assert "gate fell over" in records[-1]["detail"]


def test_send_through_main_writes_a_full_log_and_keeps_the_session_backup(tmp_path, monkeypatch):
    path, digest = write_payload(tmp_path)
    log = tmp_path / "run.jsonl"
    console = healthy_console()
    seen: list[dict] = []
    use_stack(monkeypatch, tmp_path, console, seen)

    code = runner.main(
        [
            "--input",
            str(path),
            "--expect-sha256",
            digest,
            "--log",
            str(log),
            "--listen-port",
            "9000",
        ]
    )

    records = parse_records(log.read_text(encoding="utf-8"))
    assert code == runner.EXIT_OK
    assert console.executed == list(SAMPLE_LINES)
    assert records[0]["event"] == "start"
    assert records[-1]["status"] == "ok"
    assert seen[0]["session_backup"] is True
    assert isinstance(seen[0]["approval_port"], runner.PinnedPayloadApproval)


def test_send_refuses_when_the_session_backup_failed(tmp_path, monkeypatch):
    path, digest = write_payload(tmp_path)
    log = tmp_path / "run.jsonl"
    console = FakeConsole()
    use_stack(monkeypatch, tmp_path, console, session_backup_ok=False)

    code = runner.main(
        [
            "--input",
            str(path),
            "--expect-sha256",
            digest,
            "--log",
            str(log),
            "--listen-port",
            "9000",
        ]
    )

    assert code == runner.EXIT_REFUSED
    assert console.executed == []
    assert parse_records(log.read_text(encoding="utf-8"))[-1]["status"] == "refused_session_backup"


def test_send_refuses_an_existing_log_before_building_a_stack(tmp_path, monkeypatch, capsys):
    path, digest = write_payload(tmp_path)
    log = tmp_path / "run.jsonl"
    log.write_text("earlier record\n", encoding="utf-8")
    forbid_console(monkeypatch)

    code = runner.main(
        [
            "--input",
            str(path),
            "--expect-sha256",
            digest,
            "--log",
            str(log),
            "--listen-port",
            "9000",
        ]
    )

    assert code == runner.EXIT_REFUSED
    assert "already exists" in capsys.readouterr().err
    assert log.read_text(encoding="utf-8") == "earlier record\n"


# -- probe --------------------------------------------------------------------------------


def test_probe_reads_only_and_reports_definite_verdicts(tmp_path, monkeypatch, capsys):
    console = healthy_console()
    seen: list[dict] = []
    use_stack(monkeypatch, tmp_path, console, seen)
    log = tmp_path / "probe.jsonl"

    code = runner.main(["--probe", "--listen-port", "9000", "--log", str(log)])

    assert code == runner.EXIT_OK
    assert seen[0]["session_backup"] is False  # the probe never asks for the boot-time SaveShow
    assert seen[0]["approval_port"] is None  # and it never reaches the approval channel
    assert set(console.calls) <= CONSOLE_READ_METHODS
    assert "execute" not in console.calls
    assert "deploy_plugin" not in console.calls
    assert probe_verdicts(capsys.readouterr().out) == EXPECTED_HEALTHY
    summary = parse_records(log.read_text(encoding="utf-8"))[-1]
    assert summary == {
        "event": "summary",
        "ping": "online",
        "responder_version": RESPONDER_VERSION,
        "all_definite": True,
    }


def test_probe_marks_the_timecode_path_unverified(tmp_path, monkeypatch, capsys):
    use_stack(monkeypatch, tmp_path, healthy_console())

    runner.main(["--probe", "--listen-port", "9000"])

    timecode = [r for r in parse_records(capsys.readouterr().out) if r.get("check") == "timecode"]
    assert timecode
    assert timecode[0]["path_status"] == "unverified"


def test_probe_root_not_found_is_path_unverified_never_empty(tmp_path, monkeypatch, capsys):
    console = healthy_console()
    del console.objects["DataPool/Timecodes"]  # the container itself does not resolve
    use_stack(monkeypatch, tmp_path, console)

    code = runner.main(["--probe", "--listen-port", "9000"])

    verdicts = probe_verdicts(capsys.readouterr().out)
    assert code == runner.EXIT_RUN_FAILED
    assert verdicts["timecode:70"] == "path_unverified"
    assert verdicts["timecode:70"] != "empty"


def test_probe_timeout_is_unreadable_not_empty(tmp_path, monkeypatch, capsys):
    console = healthy_console()
    console.silent.add("DataPool/Sequences/701")
    use_stack(monkeypatch, tmp_path, console)

    code = runner.main(["--probe", "--listen-port", "9000"])

    assert code == runner.EXIT_RUN_FAILED
    assert probe_verdicts(capsys.readouterr().out)["sequence:701"] == "unreadable"


def test_probe_ping_failure_exits_one(tmp_path, monkeypatch, capsys):
    console = healthy_console()
    console.pings = False
    use_stack(monkeypatch, tmp_path, console)

    code = runner.main(["--probe", "--listen-port", "9000"])

    records = parse_records(capsys.readouterr().out)
    assert code == runner.EXIT_RUN_FAILED
    assert records[0]["check"] == "ping"
    assert records[0]["verdict"] == "not_online"
    assert records[-1]["all_definite"] is False


def test_read_only_port_refuses_every_write_method(tmp_path):
    console = FakeConsole()
    guard = runner.ReadOnlyPort(make_gate(tmp_path, console))

    with pytest.raises(runner.ProbeWriteRefused):
        guard.execute("ClearAll")
    with pytest.raises(runner.ProbeWriteRefused):
        guard.deploy_plugin("x", "return 1")

    assert guard.calls == ["execute", "deploy_plugin"]
    assert console.calls == []


# -- argument surface and import safety ---------------------------------------------------


def test_listen_port_is_required_in_every_mode(tmp_path, capsys):
    path, digest = write_payload(tmp_path)

    with pytest.raises(SystemExit) as dry:
        runner.main(["--input", str(path), "--expect-sha256", digest, "--dry-run"])
    with pytest.raises(SystemExit) as probe:
        runner.main(["--probe"])

    assert dry.value.code == 2
    assert probe.value.code == 2
    assert "--listen-port" in capsys.readouterr().err


def test_dry_run_and_probe_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as excinfo:
        runner.main(["--dry-run", "--probe", "--listen-port", "9000"])

    assert excinfo.value.code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_importing_the_module_opens_no_socket(monkeypatch):
    def no_sockets(*args, **kwargs):
        raise AssertionError("importing the runner must not open a socket")

    monkeypatch.setattr(socket, "socket", no_sockets)
    spec = importlib.util.spec_from_file_location("beatgrid_runner_import_probe", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclass processing resolves string annotations through sys.modules, so the
    # module must be registered while its body runs.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)

    assert module.READ_METHODS == runner.READ_METHODS
