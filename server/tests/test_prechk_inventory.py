"""PRECHK chokepoint + fixture inventory tests (M1 — AC-PRECHK-013).

The pre-check needs fixture PROPERTIES (addresses live only in properties, not
in the enumeration payload), and property reads must ride the SAME single
chokepoint as state reads (REQ-MVP-029, REQ-PRECHK-019). The approved
conditional PRESERVE exception is four pure additions; this module fixes the
boundary those additions must not cross:

  * ``server/prechk/`` never imports the OSC send surface (REQ-PRECHK-019)
  * the operator-utility exemption list does not grow (REQ-PRECHK-020)
  * ``query_state``'s existing contract is untouched (AC-PRECHK-013 ③)

Property reads use ``prop`` requests, which the responder answers on the STATE
address -- the same reply channel as ``state``
(``console/lua/copilot_responder.lua:915``).
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from server.bridge.osc import STATE_ADDRESS, FeedbackMessage
from server.bridge.protocol import ProtocolError, encode_payload
from server.measurement.mock_provider import OfflineConsole
from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
from server.prechk.query import read_properties
from server.safety.audit import AuditLog
from server.safety.console import ConsoleLink, ExecOutcome, LinkTimeouts, StateQueryError
from server.safety.gate import SafetyGate, _GateStatePort

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRECHK_DIR = PROJECT_ROOT / "server" / "prechk"

_FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc")

_FAST = LinkTimeouts(exec_confirm_seconds=0.05, ping_seconds=0.05, state_query_seconds=0.05)

_PROP_REQUEST = re.compile(r'^Plugin "CopilotResponder" "prop (\S+) (.+) (\S+)"$')


def _prop_send(link: ConsoleLink, *, values: dict[str, str], silent: bool = False):
    """Stub console answering ``prop`` requests from a path+property map."""

    sent: list[str] = []

    def send(wire: str) -> None:
        sent.append(wire)
        if silent:
            return
        match = _PROP_REQUEST.match(wire)
        assert match, f"unexpected wire line: {wire!r}"
        rid, path, prop = match.groups()
        key = f"{path} {prop}"
        payload: dict = {"v": 1, "kind": "prop", "id": rid, "path": path, "property": prop}
        if key in values:
            payload["ok"] = True
            payload["value"] = values[key]
        else:
            payload["ok"] = False
            payload["error"] = f"property not readable: {prop}"
        link.deliver(FeedbackMessage(address=STATE_ADDRESS, args=(encode_payload(payload),)))

    return send, sent


class FakeConsole:
    """ConsolePort double with both query surfaces and failure injection."""

    def __init__(self, properties: dict[str, str] | None = None):
        self.properties = properties or {}
        self.property_calls: list[tuple[str, str]] = []
        self.state_calls: list[str] = []
        self.raise_on: set[str] = set()

    def execute(self, command: str) -> ExecOutcome:
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        return {"ok": True, "path": path, "children": []}

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        key = f"{path} {property_name}"
        if key in self.raise_on:
            raise StateQueryError(f"property not readable: {property_name}")
        return {"ok": True, "path": path, "property": property_name, "value": self.properties[key]}


def _make_gate(tmp_path, console=None):
    console = console or FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    return SafetyGate(console=console, audit=audit), console, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


def _scan_prechk_imports() -> tuple[int, int, list[str]]:
    """Return (visited files, collected import nodes, boundary violations)."""
    visited = 0
    nodes = 0
    violations: list[str] = []
    for source in sorted(PRECHK_DIR.rglob("*.py")):
        visited += 1
        tree = ast.parse(source.read_text(encoding="utf-8"))
        rel = source.relative_to(PROJECT_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                nodes += 1
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                nodes += 1
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if module.startswith(_FORBIDDEN_MODULE_PREFIXES):
                    violations.append(f"{rel} imports {module}")
    return visited, nodes, violations


class TestChokepointBoundary:
    """AC-PRECHK-013 ①②③ — the boundary the approved additions must not cross."""

    def test_prechk_package_reaches_no_bridge_and_the_scan_is_non_vacuous(self):
        visited, nodes, violations = _scan_prechk_imports()
        # Non-vacuity FIRST: an empty package or a scanner that collects
        # nothing makes "zero violations" true for free (AC-PRECHK-013 ①).
        assert visited >= 1, f"scan visited no files under {PRECHK_DIR}"
        assert nodes >= 1, "scan collected no import nodes — the 0-count is vacuous"
        assert violations == [], (
            f"REQ-PRECHK-019 violation — server/prechk reaches the send surface: {violations}"
        )

    def test_operator_utility_exemptions_did_not_grow(self):
        """AC-PRECHK-013 ② — REQ-PRECHK-020 forbids adding a util exemption."""
        source = (PROJECT_ROOT / "server" / "tests" / "test_architecture.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        literals: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_NAMED_TOOL_EXEMPTIONS" for t in node.targets
            ):
                literals = [
                    element.value
                    for element in ast.walk(node.value)
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                ]
        assert literals, "could not locate the exemption literal — scan is vacuous"
        assert set(literals) == {
            "server/tools/osc_smoke.py",
            "server/tools/responder_roundtrip.py",
        }
        assert not [rel for rel in literals if "prechk" in rel]

    def test_query_state_contract_is_unchanged(self):
        """AC-PRECHK-013 ③ — the addition is pure; it changed no signature."""
        assert list(inspect.signature(ConsoleLink.query_state).parameters) == ["self", "path"]
        assert list(inspect.signature(_GateStatePort.query_state).parameters) == ["self", "path"]
        assert list(inspect.signature(StateQueryPort.query_state).parameters) == ["self", "path"]

    def test_approval_record_exists_in_progress(self):
        """AC-PRECHK-013 ④ — the approval record is the entry precondition."""
        progress = (
            PROJECT_ROOT / ".moai" / "specs" / "SPEC-COPILOT-PRECHK-001" / "progress.md"
        ).read_text(encoding="utf-8")
        section = progress.split("## §F.")[-1]
        assert "server/safety/**" in section
        assert "승인" in section
        for approved in (
            "server/safety/console.py",
            "server/orchestrator/ports.py",
            "server/safety/gate.py",
            "server/measurement/mock_provider.py",
        ):
            assert approved in section, f"approved touchpoint missing from §F: {approved}"


class TestConsoleLinkPropertyQuery:
    """The chokepoint's own property read — homologous to query_state."""

    def test_returns_the_decoded_payload(self):
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _prop_send(link, values={"Patch/Stages/1/Fixtures/1 Patch": "1.001"})
        link.bind_send(send)
        payload = link.query_property("Patch/Stages/1/Fixtures/1", "Patch")
        assert payload["ok"] is True
        assert payload["value"] == "1.001"
        assert len(sent) == 1
        assert _PROP_REQUEST.match(sent[0]).groups()[1:] == (
            "Patch/Stages/1/Fixtures/1",
            "Patch",
        )

    def test_not_readable_raises(self):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _prop_send(link, values={})
        link.bind_send(send)
        with pytest.raises(StateQueryError, match="not readable"):
            link.query_property("Patch/Stages/1/Fixtures/1", "ChannelCount")

    def test_timeout_raises(self):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _prop_send(link, values={}, silent=True)
        link.bind_send(send)
        with pytest.raises(StateQueryError):
            link.query_property("Patch/Stages/1/Fixtures/1", "Patch")

    def test_property_name_with_a_space_is_rejected_before_any_send(self):
        """REQ-PRECHK-001 relies on this: the whitelist must stay single-token."""
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _prop_send(link, values={})
        link.bind_send(send)
        with pytest.raises(ProtocolError, match="single token"):
            link.query_property("Patch/Stages/1/Fixtures/1", "Fixture Id")
        assert sent == []


class TestGateDelegation:
    """Property reads are audited exactly like state reads."""

    def test_state_port_exposes_query_property(self, tmp_path):
        gate, _, _ = _make_gate(tmp_path)
        assert hasattr(gate.state_port, "query_property")
        assert list(inspect.signature(gate.state_port.query_property).parameters) == [
            "path",
            "property_name",
        ]
        # The gate port matches the declared port contract name-for-name, so a
        # consumer typed against the protocol cannot drift from the gate.
        assert list(inspect.signature(PropertyQueryPort.query_property).parameters) == [
            "self",
            "path",
            "property_name",
        ]

    def test_successful_read_is_audited(self, tmp_path):
        console = FakeConsole({"Patch/Stages/1/Fixtures/1 Patch": "1.001"})
        gate, _, audit = _make_gate(tmp_path, console)
        payload = gate.state_port.query_property("Patch/Stages/1/Fixtures/1", "Patch")
        assert payload["value"] == "1.001"
        events = [e for e in _events(audit, "executed") if e.get("kind") == "property_query"]
        assert len(events) == 1
        assert events[0]["ok"] is True
        assert "Patch" in events[0]["command"]

    def test_failed_read_is_audited_and_reraises(self, tmp_path):
        console = FakeConsole()
        console.raise_on.add("Patch/Stages/1/Fixtures/1 ChannelCount")
        gate, _, audit = _make_gate(tmp_path, console)
        with pytest.raises(StateQueryError):
            gate.state_port.query_property("Patch/Stages/1/Fixtures/1", "ChannelCount")
        events = [e for e in _events(audit, "executed") if e.get("kind") == "property_query"]
        assert len(events) == 1
        assert events[0]["ok"] is False

    def test_offline_double_answers_property_reads(self):
        payload = OfflineConsole().query_property("Patch/Stages/1/Fixtures/1", "Patch")
        assert payload["ok"] is True
        assert payload["property"] == "Patch"
        assert isinstance(payload["value"], str) and payload["value"]


class TestReadProperties:
    """server/prechk/query.py — port-only reads that capture failures."""

    def test_reads_every_requested_name_through_the_port(self, tmp_path):
        console = FakeConsole(
            {
                "Patch/Stages/1/Fixtures/1 Patch": "1.001",
                "Patch/Stages/1/Fixtures/1 Name": "RMMXSm1 1",
            }
        )
        gate, _, _ = _make_gate(tmp_path, console)
        reads = read_properties(gate.state_port, "Patch/Stages/1/Fixtures/1", ("Patch", "Name"))
        assert set(reads) == {"Patch", "Name"}
        assert reads["Patch"].ok is True
        assert reads["Patch"].value == "1.001"
        assert reads["Name"].value == "RMMXSm1 1"
        assert console.property_calls == [
            ("Patch/Stages/1/Fixtures/1", "Patch"),
            ("Patch/Stages/1/Fixtures/1", "Name"),
        ]

    def test_a_failed_read_is_captured_not_raised(self, tmp_path):
        console = FakeConsole({"Patch/Stages/1/Fixtures/1 Patch": "1.001"})
        console.raise_on.add("Patch/Stages/1/Fixtures/1 Mode")
        gate, _, _ = _make_gate(tmp_path, console)
        reads = read_properties(gate.state_port, "Patch/Stages/1/Fixtures/1", ("Patch", "Mode"))
        # One unreadable property must not lose the readable ones -- the
        # inventory classifies read failures instead of aborting the sweep.
        assert reads["Patch"].ok is True
        assert reads["Mode"].ok is False
        assert reads["Mode"].value is None
        assert "not readable" in reads["Mode"].error

    def test_ok_false_payload_without_an_exception_is_a_failed_read(self, tmp_path):
        class QuietPort:
            def query_property(self, path: str, property_name: str) -> dict:
                return {"ok": False, "path": path, "property": property_name, "error": "nope"}

        reads = read_properties(QuietPort(), "Patch/Stages/1/Fixtures/1", ("Patch",))
        assert reads["Patch"].ok is False
        assert reads["Patch"].error == "nope"

    def test_duplicate_names_are_read_once(self, tmp_path):
        console = FakeConsole({"Patch/Stages/1/Fixtures/1 Patch": "1.001"})
        gate, _, _ = _make_gate(tmp_path, console)
        reads = read_properties(gate.state_port, "Patch/Stages/1/Fixtures/1", ("Patch", "Patch"))
        assert set(reads) == {"Patch"}
        assert console.property_calls == [("Patch/Stages/1/Fixtures/1", "Patch")]

    def test_empty_name_list_is_rejected(self, tmp_path):
        gate, _, _ = _make_gate(tmp_path)
        # A silent empty result would let every "0 read failures" assertion
        # pass vacuously.
        with pytest.raises(ValueError):
            read_properties(gate.state_port, "Patch/Stages/1/Fixtures/1", ())
