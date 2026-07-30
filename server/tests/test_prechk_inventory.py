"""PRECHK chokepoint + fixture inventory tests (AC-PRECHK-013 · 001 · 002 · 003 · 004).

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
import json
import re
from pathlib import Path

import pytest

from server.bridge.osc import STATE_ADDRESS, FeedbackMessage
from server.bridge.protocol import ProtocolError, encode_payload
from server.measurement.mock_provider import OfflineConsole
from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
from server.prechk.inventory import (
    COMPLETE,
    FID_UNRESOLVED_MARK,
    FIXTURE_ROOT,
    FUNCTION_REFERENCE_PREFIX,
    INCOMPLETE,
    PROPERTY_UNREADABLE,
    PROPERTY_WHITELIST,
    RETIRED_PATHS,
    SHAPE_INVALID,
    InventoryPolicy,
    InventoryReadError,
    fid_note,
    read_inventory,
    shape_error,
    slot_path,
)
from server.prechk.patch import evaluate_patch
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
        # §F grew a §F.1 revision, so the LAST chunk is the revision alone.
        # The record lives in §F and its subsections -- take all of them.
        parts = progress.split("## §F.")
        assert len(parts) >= 2, "progress.md에 §F 절이 없다"
        section = "## §F.".join(parts[1:])
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


# ---------------------------------------------------------------------------
# In-memory rigs (design §6.1). A consistent rig alone cannot show that
# detection works -- every verdict converges on "nothing wrong", which is
# indistinguishable from a scanner that never fires. So the defects are planted
# here, and the live session only has to show the absence of false positives.
# ---------------------------------------------------------------------------

#: A property the console refuses to answer.
UNREADABLE = "<<unreadable-property>>"

#: Measured verbatim: ``prop <fixture> Index`` answered ok=true with this.
MEASURED_FUNCTION_REF = "function: 0x105b0f048"

#: Footprint widths for the range-overlap branch. The value 29 is the measured
#: ``DMXChannels`` child count of mode 1; it is INJECTED, never derived.
RANGE_OVERLAP_WIDTHS = {1: 29, 2: 29, 3: 29, 4: 29}
FOOTPRINT_SOURCE = "Patch/FixtureTypes/1/DMXModes/1/DMXChannels childCount"

_FIXTURE_SELECTION = re.compile(r"\bFixture \d+\b")

# Property names measured unreadable, or readable but banned as judgement
# inputs. None of them may appear as a string constant anywhere in the package.
_FORBIDDEN_PROPERTY_NAMES = frozenset(
    {
        "Address",
        "DMXAddress",
        "DmxAddress",
        "BreakAddress",
        "Break",
        "Universe",
        "DMXUniverse",
        "FID",
        "FixtureID",
        "FixtureId",
        "No",
        "Index",
        "CID",
        "IDType",
        "ChannelCount",
        "Channels",
        "Footprint",
        "Fixture Id",
        "Fixture ID",
    }
)


def fixture_props(
    patch: str,
    *,
    name: str,
    fixture_type: str = "FixtureType 1",
    mode: str = "1 Mode 1",
    fid: str | None = None,
) -> dict[str, str]:
    """One fixture's property table as the responder would answer it.

    ``fid`` is stored so a test can prove the inventory never ASKS for it --
    the pool can answer, the reader must not request.
    """
    props = {"Patch": patch, "Name": name, "FixtureType": fixture_type, "Mode": mode}
    if fid is not None:
        props["FID"] = fid
    return props


class FixturePool:
    """In-memory ``Patch/Stages/1/Fixtures`` — a state + property port double.

    Answers what the responder answers: ``node.childCount`` is the TRUE total,
    ``children`` may be short, a single-node read is never truncated, and one
    property may fail while its siblings succeed.
    """

    def __init__(
        self,
        slots: dict[int, dict[str, str]],
        *,
        child_count: int | None = None,
        enumerated: tuple[int, ...] | None = None,
        truncated: bool | None = None,
        snapshot_names: dict[int, str | None] | None = None,
    ):
        self.slots = {slot: dict(props) for slot, props in slots.items()}
        self.enumerated = tuple(enumerated) if enumerated is not None else tuple(sorted(self.slots))
        self.child_count = child_count if child_count is not None else len(self.enumerated)
        self.truncated = (
            truncated if truncated is not None else self.child_count > len(self.enumerated)
        )
        self.snapshot_names = dict(snapshot_names or {})
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def snapshot_name(self, slot: int) -> str | None:
        if slot in self.snapshot_names:
            return self.snapshot_names[slot]
        value = self.slots.get(slot, {}).get("Name")
        if isinstance(value, str) and value != UNREADABLE and shape_error(value) is None:
            return value
        return f"슬롯-{slot}"

    def _slot_of(self, path: str) -> int | None:
        prefix = f"{FIXTURE_ROOT}/"
        if not path.startswith(prefix):
            return None
        tail = path[len(prefix) :]
        return int(tail) if tail.isdigit() else None

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path == FIXTURE_ROOT:
            return {
                "ok": True,
                "path": path,
                "node": {
                    "name": "Fixtures",
                    "class": "Fixtures",
                    "childCount": self.child_count,
                },
                "children": [
                    {"i": slot, "name": self.snapshot_name(slot), "class": "Fixture"}
                    for slot in self.enumerated
                ],
                "truncated": self.truncated,
            }
        slot = self._slot_of(path)
        if slot is not None and slot in self.slots:
            return {
                "ok": True,
                "path": path,
                "node": {
                    "name": self.snapshot_name(slot),
                    "class": "Fixture",
                    "childCount": 0,
                },
                "children": [],
                "truncated": False,
            }
        return {"ok": False, "path": path, "error": "path segment not found"}

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        slot = self._slot_of(path)
        props = self.slots.get(slot) if slot is not None else None
        if props is None or property_name not in props or props[property_name] == UNREADABLE:
            return {
                "ok": False,
                "path": path,
                "property": property_name,
                "error": f"property not readable: {property_name}",
            }
        return {"ok": True, "path": path, "property": property_name, "value": props[property_name]}


def clean_rig_18() -> FixturePool:
    """18 consistent fixtures: no duplicate address, no truncation.

    DELIBERATELY SYNTHETIC and frozen at 18. The calibration show file has since
    grown to 19 fixtures and this pool does NOT follow it: binding an in-memory
    rig to a field show file destroys determinism -- a patch edit on site would
    turn into a test failure -- and the live 19-slot table is evidence recorded
    in ``progress.md`` §E.2, not an input here.
    """
    slots = {1: fixture_props("1.001", name="RMMXSm1 1")}
    for offset, slot in enumerate(range(2, 11)):
        slots[slot] = fixture_props(f"1.{101 + offset * 42:03d}", name=f"Copilot MMX {slot}")
    for offset, slot in enumerate(range(11, 19)):
        slots[slot] = fixture_props(f"2.{1 + offset * 50:03d}", name=f"MMX {slot}")
    return FixturePool(slots)


def slot_not_fid() -> FixturePool:
    """Slot 1 carries fixture id 101, slot 2 carries an unreadable one.

    Both sit at ``1.001``, so the duplicate must be reported by SLOT and must
    still be found while a fixture id is unavailable. The live rig has
    slot == FID for every fixture, which makes this distinction unverifiable
    there (``console/lua/PROTOCOL.md:322-324``).
    """
    return FixturePool(
        {
            1: fixture_props("1.001", name="스팟 좌", fid="101"),
            2: fixture_props("1.001", name="스팟 우", fid=UNREADABLE),
        }
    )


def duplicate_address_pair() -> FixturePool:
    """Slots 1 and 2 share ``1.010``; slot 3 is unique (non-vacuity)."""
    return FixturePool(
        {
            1: fixture_props("1.010", name="워시 1"),
            2: fixture_props("1.010", name="워시 2"),
            3: fixture_props("1.200", name="워시 3"),
        }
    )


def duplicate_address_triple() -> FixturePool:
    """Three fixtures on ``1.010`` — one collision, not three pairs."""
    return FixturePool(
        {
            1: fixture_props("1.010", name="워시 1"),
            2: fixture_props("1.010", name="워시 2"),
            3: fixture_props("1.010", name="워시 3"),
            4: fixture_props("1.200", name="워시 4"),
        }
    )


def same_address_other_universe() -> FixturePool:
    """``1.001`` and ``2.001`` — the same number, different universes."""
    return FixturePool(
        {
            1: fixture_props("1.001", name="유니버스 1"),
            2: fixture_props("2.001", name="유니버스 2"),
        }
    )


def truncated_parent(*, hidden: tuple[int, ...] = ()) -> FixturePool:
    """``childCount = 40`` with 18 enumerated children and ``truncated = true``.

    ``hidden`` slots EXIST -- a single-node read finds them -- but are absent
    from the enumeration. That is how per-slot recovery raises detail without
    ever proving completeness.
    """
    slots = {slot: fixture_props(f"1.{slot:03d}", name=f"트러스 {slot}") for slot in range(1, 19)}
    for slot in hidden:
        slots[slot] = fixture_props(f"2.{slot:03d}", name=f"복구 {slot}")
    return FixturePool(slots, child_count=40, enumerated=tuple(range(1, 19)), truncated=True)


def truncated_flag_false() -> FixturePool:
    """``childCount`` exceeds ``len(children)`` while ``truncated`` is FALSE.

    Both responder truncation paths do set the flag, so this pool is the flag
    lost or tampered with. The count comparison must still say incomplete.
    """
    slots = {slot: fixture_props(f"1.{slot:03d}", name=f"트러스 {slot}") for slot in range(1, 19)}
    return FixturePool(slots, child_count=40, enumerated=tuple(range(1, 19)), truncated=False)


def function_ref_property() -> FixturePool:
    """Slot 1's ``Patch`` is the measured Lua function reference.

    Slot 2 is clean (non-vacuity) and slot 3's ``FixtureType`` is unreadable --
    a fixture that must be excluded from the consistency judgement rather than
    counted either way (REQ-PRECHK-009).
    """
    return FixturePool(
        {
            1: fixture_props(MEASURED_FUNCTION_REF, name="함수참조 1"),
            2: fixture_props("1.002", name="정상 2"),
            3: fixture_props("1.100", name="타입불명 3", fixture_type=UNREADABLE),
        }
    )


def none_string_property() -> FixturePool:
    """Slot 1's ``Patch`` is the string ``'None'`` — absence spelled out."""
    return FixturePool(
        {
            1: fixture_props("None", name="부재값 1"),
            2: fixture_props("1.002", name="정상 2"),
        }
    )


def bad_patch_value(raw: str) -> FixturePool:
    """Slot 1's ``Patch`` will not parse; slot 2 is clean (non-vacuity)."""
    return FixturePool(
        {
            1: fixture_props(raw, name="주소불명 1"),
            2: fixture_props("1.002", name="정상 2"),
        }
    )


def range_overlap_go() -> FixturePool:
    """Slots 1 and 2 at addresses 1 and 15; slots 3 and 4 at 101 and 143.

    At the measured width of 29 the first pair overlaps and the second pair does
    not -- 143 minus 101 is the measured 42-channel spacing of the live rig.
    """
    return FixturePool(
        {
            1: fixture_props("1.001", name="겹침 A"),
            2: fixture_props("1.015", name="겹침 B"),
            3: fixture_props("1.101", name="간격 C"),
            4: fixture_props("1.143", name="간격 D"),
        }
    )


def range_descope() -> FixturePool:
    """The same rig as :func:`range_overlap_go`.

    The descope lives in the POLICY, not in the data: ``ASSUMPTION-27`` is
    NEGATIVE, so the shipped configuration cannot reach a footprint at all and
    records the check as not performed.
    """
    return range_overlap_go()


def _retired_path_hits(lines) -> list[str]:
    return [line for line in lines for dead in RETIRED_PATHS if dead in line]


def _fixture_selection_hits(lines) -> list[str]:
    return [line for line in lines if _FIXTURE_SELECTION.search(line)]


def _string_constants(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


class TestFixtureEnumerationAndWhitelist:
    """AC-PRECHK-001 — the enumeration path and the property whitelist."""

    def test_enumeration_uses_the_live_path_and_never_a_retired_one(self):
        inventory = read_inventory(clean_rig_18())
        queries = inventory.generated_queries()
        # Non-vacuity FIRST: an empty query list makes every "0 hits" scan below
        # pass for free.
        assert len(queries) >= 1, "생성 조회 목록이 비면 0건 스캔이 공허하다"
        assert inventory.path == "Patch/Stages/1/Fixtures"
        assert inventory.state_paths[0] == FIXTURE_ROOT
        assert _retired_path_hits(queries) == []
        planted = (*queries, f"state {RETIRED_PATHS[0]}", f"state {RETIRED_PATHS[1]}")
        assert len(_retired_path_hits(planted)) == 2, "스캐너가 심어둔 죽은 경로를 놓쳤다"

    def test_every_queried_path_stays_under_the_fixture_root(self):
        inventory = read_inventory(clean_rig_18())
        assert inventory.queried_paths
        assert all(
            path == FIXTURE_ROOT or path.startswith(f"{FIXTURE_ROOT}/")
            for path in inventory.queried_paths
        )

    def test_requested_property_names_are_the_whitelist(self):
        inventory = read_inventory(clean_rig_18())
        assert inventory.queried_properties, "프로퍼티 조회 목록이 비면 부분집합 검사가 공허하다"
        assert set(inventory.queried_properties) <= set(PROPERTY_WHITELIST)
        assert set(inventory.queried_properties) == set(PROPERTY_WHITELIST)

    def test_no_code_path_names_a_property_outside_the_whitelist(self):
        collected: list[str] = []
        visited = 0
        for source in sorted(PRECHK_DIR.rglob("*.py")):
            visited += 1
            collected.extend(_string_constants(source))
        assert visited >= 1, f"AST 스캔이 {PRECHK_DIR} 아래 파일을 방문하지 않았다"
        assert len(collected) >= 1, "AST 스캔이 문자열 상수를 하나도 모으지 않았다"
        assert set(collected) & _FORBIDDEN_PROPERTY_NAMES == set()
        assert set([*collected, "Address"]) & _FORBIDDEN_PROPERTY_NAMES == {"Address"}

    def test_whitelist_is_the_measured_four_and_carries_no_space(self):
        # Non-vacuity: an empty whitelist would satisfy "no space-bearing name"
        # automatically.
        assert len(PROPERTY_WHITELIST) >= 1
        assert "Patch" in PROPERTY_WHITELIST
        assert set(PROPERTY_WHITELIST) == {"Patch", "FixtureType", "Mode", "Name"}
        assert [name for name in PROPERTY_WHITELIST if " " in name] == []
        assert [name for name in (*PROPERTY_WHITELIST, "Fixture Id") if " " in name] == [
            "Fixture Id"
        ]


class TestValueShapeValidation:
    """AC-PRECHK-002 — ``ok=true`` is not a licence to adopt the value."""

    def test_a_function_reference_is_a_read_failure_not_a_value(self):
        inventory = read_inventory(function_ref_property())
        failures = [failure for failure in inventory.read_failures if failure.slot == 1]
        assert [failure.property for failure in failures] == ["Patch"]
        assert failures[0].kind == SHAPE_INVALID
        assert failures[0].raw_value == MEASURED_FUNCTION_REF
        record = {record.slot: record for record in inventory.fixtures}[1]
        assert record.patch_raw is None, "형태 불만족 값이 픽스처 값으로 채택됐다"

    def test_the_none_string_is_a_read_failure(self):
        inventory = read_inventory(none_string_property())
        failures = [failure for failure in inventory.read_failures if failure.slot == 1]
        assert [(failure.property, failure.kind) for failure in failures] == [
            ("Patch", SHAPE_INVALID)
        ]
        assert failures[0].raw_value == "None"
        assert {record.slot: record for record in inventory.fixtures}[1].patch_raw is None

    def test_a_read_failure_carries_its_reason_and_the_raw_text(self):
        inventory = read_inventory(function_ref_property())
        assert inventory.read_failures
        for failure in inventory.read_failures:
            assert failure.detail, "판독 실패가 사유 없이 실렸다"
        detail = next(f.detail for f in inventory.read_failures if f.slot == 1)
        assert MEASURED_FUNCTION_REF in detail

    def test_a_valid_address_is_not_a_read_failure(self):
        inventory = read_inventory(clean_rig_18())
        assert inventory.fixtures, "픽스처가 0개면 '판독 실패 0건'이 공허하다"
        assert inventory.read_failures == ()
        assert {"1.001", "2.351"} <= {record.patch_raw for record in inventory.fixtures}

    def test_the_discriminator_is_the_prefix_not_one_pointer(self):
        other = f"{FUNCTION_REFERENCE_PREFIX}deadbeef"
        assert other != MEASURED_FUNCTION_REF
        assert shape_error(other) is not None
        pool = FixturePool(
            {
                1: fixture_props(other, name="다른 포인터"),
                2: fixture_props("1.002", name="정상"),
            }
        )
        inventory = read_inventory(pool)
        assert [failure.kind for failure in inventory.read_failures] == [SHAPE_INVALID]

    def test_shape_error_accepts_display_strings_and_rejects_the_three_forms(self):
        for good in ("1.001", "MMX 19", "FixtureType 1", "1 Mode 1", "Robin MMX Spot"):
            assert shape_error(good) is None, good
        for bad in (None, "", "   ", "None", MEASURED_FUNCTION_REF):
            assert shape_error(bad) is not None, bad

    def test_an_unreadable_property_is_a_different_class_from_a_bad_shape(self):
        inventory = read_inventory(function_ref_property())
        kinds = {
            (failure.slot, failure.property): failure.kind for failure in inventory.read_failures
        }
        assert kinds[(3, "FixtureType")] == PROPERTY_UNREADABLE
        assert kinds[(1, "Patch")] == SHAPE_INVALID
        assert PROPERTY_UNREADABLE != SHAPE_INVALID

    def test_every_lua_pointer_type_is_rejected_not_only_function(self):
        # `safe_property` falls back to `tostring` on every non-nil value and
        # Lua's `tostring` renders EVERY non-primitive as `<type>: 0x<addr>`, so
        # the fault is "a pointer came back", not "a function came back". Gating
        # on the function prefix alone adopted the other three as values.
        for pointer in (
            "table: 0x105b0f048",
            "userdata: 0x105b0f048",
            "thread: 0x105b0f048",
            MEASURED_FUNCTION_REF,
        ):
            assert shape_error(pointer) is not None, pointer
        # Non-vacuity: the widened gate must not swallow legitimate values that
        # merely resemble one. Fixture names and type strings are free text.
        for good in ("table", "0x105b0f048", "userdata 1", "table: value", "Robin MMX Spot"):
            assert shape_error(good) is None, good

    def test_a_pointer_in_the_type_slot_is_a_read_failure_not_a_type_name(self):
        # Adopting it printed a pointer string where a fixture type belongs and
        # let the fixture through the range-overlap check as a normal entry.
        pool = FixturePool(
            {
                1: fixture_props("1.001", name="MMX 1", fixture_type="userdata: 0x105b0f048"),
                2: fixture_props("1.002", name="MMX 2"),
            }
        )
        inventory = read_inventory(pool)
        record = {record.slot: record for record in inventory.fixtures}[1]
        assert record.fixture_type is None, "a pointer was adopted as the fixture type"
        failure = record.failure_for("FixtureType")
        assert failure is not None
        assert failure.kind == SHAPE_INVALID


class TestCompleteness:
    """AC-PRECHK-003 — completeness comes from the counts, not the flag."""

    def test_a_short_enumeration_is_incomplete_and_names_the_deficit(self):
        inventory = read_inventory(truncated_parent())
        assert inventory.child_count == 40
        assert inventory.enumerated_count == 18
        assert inventory.observed_count == 18
        assert inventory.missing_count == 22
        assert inventory.completeness == INCOMPLETE

    def test_the_verdict_survives_a_falsified_truncated_flag(self):
        pool = truncated_flag_false()
        assert pool.truncated is False
        inventory = read_inventory(pool)
        assert inventory.completeness == INCOMPLETE
        assert inventory.missing_count == 22

    def test_equal_counts_are_complete(self):
        inventory = read_inventory(clean_rig_18())
        assert inventory.child_count == 18
        assert inventory.observed_count == 18
        assert inventory.missing_count == 0
        assert inventory.completeness == COMPLETE
        assert inventory.recovery_boundary is None
        assert inventory.index_domain_unknown is False
        assert len(inventory.fixtures) == 18

    def test_recovery_raises_detail_but_never_promotes_to_complete(self):
        inventory = read_inventory(truncated_parent(hidden=(19, 20)))
        assert inventory.recovered_slots == (19, 20)
        assert inventory.recovered_count == 2
        assert inventory.observed_count == 20
        assert inventory.missing_count == 20
        assert inventory.completeness == INCOMPLETE
        assert inventory.recovery_boundary == 40
        assert inventory.index_domain_unknown is True
        assert {record.slot for record in inventory.fixtures if record.recovered} == {19, 20}
        assert {record.slot for record in inventory.fixtures} == set(range(1, 21))

    def test_the_recovery_arithmetic_closes(self):
        pools = (
            clean_rig_18(),
            truncated_parent(),
            truncated_parent(hidden=(19, 20)),
            truncated_flag_false(),
        )
        for pool in pools:
            inventory = read_inventory(pool)
            assert inventory.observed_count + inventory.missing_count == inventory.child_count
            assert inventory.recovered_count <= inventory.observed_count
            assert inventory.still_unobserved_count == inventory.missing_count

    def test_recovery_can_be_disabled_without_changing_the_verdict(self):
        inventory = read_inventory(
            truncated_parent(hidden=(19, 20)), InventoryPolicy(recover_truncated=False)
        )
        assert inventory.recovered_count == 0
        assert inventory.recovery_boundary is None
        assert inventory.index_domain_unknown is True
        assert inventory.completeness == INCOMPLETE
        assert inventory.missing_count == 22

    def test_the_inventory_block_carries_exactly_the_schema_keys(self):
        payload = read_inventory(truncated_parent()).to_dict()
        assert set(payload) == {
            "path",
            "child_count",
            "observed_count",
            "recovered_count",
            "missing_count",
            "completeness",
            "recovery_boundary",
            "index_domain_unknown",
        }

    def test_an_unreadable_root_is_refused_not_reported_as_an_empty_rig(self):
        class DeadRoot:
            def query_state(self, path: str) -> dict:
                return {"ok": False, "path": path, "error": "path segment not found"}

            def query_property(self, path: str, property_name: str) -> dict:
                raise AssertionError("must not be reached")

        with pytest.raises(InventoryReadError):
            read_inventory(DeadRoot())

    def test_a_snapshot_without_a_child_count_is_refused(self):
        class NoCount:
            def query_state(self, path: str) -> dict:
                return {"ok": True, "path": path, "node": {"name": "Fixtures"}, "children": []}

            def query_property(self, path: str, property_name: str) -> dict:
                raise AssertionError("must not be reached")

        with pytest.raises(InventoryReadError):
            read_inventory(NoCount())

    def test_a_child_without_an_index_is_a_read_failure_not_a_position(self):
        pool = FixturePool({1: fixture_props("1.001", name="정상")})

        class NoIndex(FixturePool):
            def query_state(self, path: str) -> dict:
                payload = super().query_state(path)
                if path == FIXTURE_ROOT:
                    payload["children"] = [{"name": "이름만", "class": "Fixture"}]
                return payload

        broken = NoIndex(pool.slots, child_count=1)
        inventory = read_inventory(broken)
        assert [failure.property for failure in inventory.read_failures] == ["i"]
        assert inventory.read_failures[0].kind == SHAPE_INVALID

    def test_a_child_without_an_index_is_not_reported_as_a_short_root(self):
        # The responder omits `i` whenever the slot is unestablished, and it
        # returned EVERY child it declared. Folding that into "the root
        # enumeration was short" puts a cause in front of the user that did not
        # happen — the fourth instance of read-failure-as-absence in this SPEC.
        pool = FixturePool({1: fixture_props("1.001", name="정상")})

        class NoIndex(FixturePool):
            def query_state(self, path: str) -> dict:
                payload = super().query_state(path)
                if path == FIXTURE_ROOT:
                    payload["children"] = [{"name": "이름만", "class": "Fixture"}]
                return payload

        inventory = read_inventory(NoIndex(pool.slots, child_count=1))
        assert inventory.child_count == 1
        assert len(inventory.read_failures) == 1, "the slot-index failure vanished"
        # The root returned all 1 of its 1 declared children: nothing was short.
        assert inventory.index_domain_unknown is False
        assert inventory.recovery_boundary is None
        # Still incomplete — the population was declared but never confirmed.
        assert inventory.completeness == INCOMPLETE
        assert inventory.observed_count == 0
        assert inventory.missing_count == 1

    def test_recovery_is_skipped_when_no_child_established_a_slot(self):
        # A numeric path segment degrades to a LIST POSITION when not one child
        # of the node has an established slot, and that is exactly the state a
        # slot-less enumeration reports. Sweeping then adopts positions as slots
        # — the promotion read_inventory forbids outright.
        pool = FixturePool(
            {slot: fixture_props(f"1.{slot:03d}", name=f"MMX {slot}") for slot in (1, 2, 3)}
        )

        class SlotlessAndShort(FixturePool):
            def query_state(self, path: str) -> dict:
                payload = super().query_state(path)
                if path == FIXTURE_ROOT:
                    payload["children"] = [{"name": "MMX 1", "class": "Fixture"}]
                    payload["truncated"] = True
                return payload

        broken = SlotlessAndShort(pool.slots, child_count=3, enumerated=(1,))
        inventory = read_inventory(broken)
        # The root WAS short (3 declared, 1 returned), so the old predicate ran
        # the sweep and every probe answered ok — by list position.
        assert inventory.recovered_count == 0, (
            f"the sweep adopted positions as slots: {inventory.recovered_slots}"
        )
        assert inventory.recovery_boundary is None
        assert [path for path in broken.state_calls if path != FIXTURE_ROOT] == [], (
            "a per-slot probe was issued with no established slot to anchor it"
        )
        assert inventory.completeness == INCOMPLETE
        assert inventory.missing_count == 3

    def test_recovery_still_runs_when_a_slot_is_established(self):
        # Non-vacuity: the guard must not have disabled recovery outright.
        inventory = read_inventory(truncated_parent(hidden=(19, 20)))
        assert inventory.recovered_slots == (19, 20)

    def test_a_snapshot_that_overcounts_its_own_children_is_refused(self):
        # The clamp `max(child_count - observed_count, 0)` absorbed this and
        # AC-PRECHK-003's identity then closed FALSELY: the report printed
        # `관측 3개 / 보고된 자식 수 2개` and called itself COMPLETE in the same
        # sentence. Nothing verified the identity at runtime — the docstring
        # merely asserted it. A census that contradicts itself is not a rig fact.
        pool = FixturePool(
            {slot: fixture_props(f"1.{slot:03d}", name=f"MMX {slot}") for slot in (1, 2, 3)},
            child_count=2,
            enumerated=(1, 2, 3),
            truncated=False,
        )
        with pytest.raises(InventoryReadError):
            read_inventory(pool)

    def test_the_arithmetic_identity_holds_by_construction(self):
        # Non-vacuity for the refusal above: the well-formed pools still close,
        # and now without a clamp absorbing anything.
        for pool in (clean_rig_18(), truncated_parent(), truncated_parent(hidden=(19, 20))):
            inventory = read_inventory(pool)
            assert inventory.observed_count + inventory.still_unobserved_count == (
                inventory.child_count
            )

    def test_a_probe_that_never_answered_is_recorded_not_silently_dropped(self):
        # `ok=false` means the path segment is absent — information, since the
        # pool may be sparse. A RAISING port is a timeout: the console did not
        # answer, which says nothing about whether the slot exists. Folding the
        # second into the first erased every probe failure from the report, so a
        # dead link and a sparse pool read identically.
        class DeadProbe(FixturePool):
            def query_state(self, path: str) -> dict:
                if path != FIXTURE_ROOT:
                    raise RuntimeError("no reply within 3.0s")
                return super().query_state(path)

        pool = DeadProbe(
            {slot: fixture_props(f"1.{slot:03d}", name=f"MMX {slot}") for slot in (1, 2)},
            child_count=4,
            enumerated=(1, 2),
        )
        inventory = read_inventory(pool)
        probe_failures = [
            failure
            for failure in inventory.read_failures
            if failure.kind == PROPERTY_UNREADABLE and failure.slot in (3, 4)
        ]
        assert len(probe_failures) == 2, (
            "a probe that never answered left no trace in the report: "
            f"{[f.property for f in inventory.read_failures]}"
        )
        # The judgement numbers are unchanged — this raises diagnosis only.
        assert inventory.missing_count == 2
        assert inventory.completeness == INCOMPLETE

    def test_a_sparse_pool_stays_silent_and_is_not_a_read_failure(self):
        # The other side of the same seam: `ok=false` must NOT become a failure,
        # or every sparse rig would report phantom console faults.
        inventory = read_inventory(truncated_parent())
        assert inventory.missing_count == 22
        assert [f for f in inventory.read_failures if f.slot and f.slot > 18] == []


class TestFidIsNotAJudgementInput:
    """AC-PRECHK-004 — the three fixture-id bans."""

    def test_the_judgement_keys_on_the_slot_not_the_fixture_id(self):
        pool = slot_not_fid()
        inventory = read_inventory(pool)
        assert "FID" not in inventory.queried_properties
        assert ("Patch/Stages/1/Fixtures/1", "FID") not in pool.property_calls
        evaluation = evaluate_patch(inventory)
        assert len(evaluation.address_duplicates) == 1
        members = evaluation.address_duplicates[0].members
        assert [member.slot for member in members] == [1, 2]
        assert [member.name for member in members] == ["스팟 좌", "스팟 우"]
        dumped = json.dumps(evaluation.to_dict(), ensure_ascii=False)
        assert "101" not in dumped, "FID 값이 결과에 새어 나왔다"

    def test_no_generated_request_selects_a_fixture_by_number(self):
        inventory = read_inventory(clean_rig_18())
        queries = inventory.generated_queries()
        assert len(queries) >= 1, "생성 목록이 비면 'Fixture <n> 0건'이 공허하다"
        assert _fixture_selection_hits(queries) == []
        assert _fixture_selection_hits([*queries, "Fixture 7 At 100"]) == ["Fixture 7 At 100"]

    def test_a_slot_reference_is_a_path_never_a_selection(self):
        assert slot_path(7) == "Patch/Stages/1/Fixtures/7"
        assert _fixture_selection_hits([slot_path(7)]) == []

    def test_duplicates_are_found_while_the_fixture_id_is_unreadable(self):
        pool = slot_not_fid()
        assert pool.slots[2]["FID"] == UNREADABLE
        evaluation = evaluate_patch(read_inventory(pool))
        assert len(evaluation.address_duplicates) == 1
        assert [member.slot for member in evaluation.address_duplicates[0].members] == [1, 2]

    def test_every_fixture_row_marks_the_fixture_id_unresolved(self):
        evaluation = evaluate_patch(read_inventory(clean_rig_18()))
        rows = [row.to_dict() for row in evaluation.rows]
        assert rows
        assert all(FID_UNRESOLVED_MARK in row["fid_note"] for row in rows)
        assert fid_note() == FID_UNRESOLVED_MARK
        assert FID_UNRESOLVED_MARK in fid_note("101")
        assert "101" in fid_note("101")
