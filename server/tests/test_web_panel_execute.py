"""Panel execution through the safety gate (SHOWUI M3).

The panel's firing half: `/ws` routing for the five panel message types, the
membership guard, the one-at-a-time execute serialization with its stop
exemption, and — the reason this milestone is the dangerous one — the proof
that EVERY route by which a panel press can reach the console passes through
``gate.screen()`` and nothing else (REQ-SHOWUI-006/007, AC-SHOWUI-005/006).

Every test drives a REAL :class:`server.safety.gate.SafetyGate` over a fake
console port, so clearance issue/consumption and the 1:1 send↔audit contract
are the production ones rather than a stand-in. ``gate.screen`` is wrapped by a
spy in the tests that must prove a NON-call: "no bundle was built" is only
believable if the gate can testify it was never asked.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor
from server.safety.session_context import new_session_key
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import PROTOCOL_VERSION
from server.web.panel import (
    PANEL_BUSY_MESSAGE,
    PANEL_UNKNOWN_TARGET_MESSAGE,
    PIN_SEED_UNAVAILABLE_MESSAGE,
    PanelRuntime,
    PanelStore,
    PinStore,
    playback_command,
)

from .test_runner_self_correction import ScriptedProvider, _final, _run_turn
from .test_safety_gate import FakeConsole

PANEL_MODULE = Path(__file__).resolve().parents[1] / "web" / "panel.py"


# -- fixtures -------------------------------------------------------------------


class FakeStatePort:
    """Fake StateQueryPort — the same shape ``gate.state_port`` presents."""

    def __init__(self, tree: dict):
        self.tree = tree
        self.queries: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queries.append(path)
        if path not in self.tree:
            raise LookupError(f"unknown object path: {path}")
        return self.tree[path]


def _snapshot(path: str, entries: list[tuple[int, str]]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": number, "name": name} for number, name in entries],
    }


# Deliberately NON-CONTIGUOUS, and with the live-probed executor shape
# (progress.md ASSUMPTION-7: page 1's children came back 1, 5, 11, 91, 92, …).
RIG_TREE = {
    "DataPool/Sequences": _snapshot(
        "DataPool/Sequences", [(2, "House"), (7, "Warm Wash"), (41, "Summer Rock")]
    ),
    "DataPool/Pages": _snapshot("DataPool/Pages", [(1, "Page 1")]),
    "DataPool/Pages/1": _snapshot(
        "DataPool/Pages/1", [(5, "Cyan Look"), (11, "Chase"), (191, "Summer Rock")]
    ),
    # SPEC-COPILOT-DASHUI-001 M2 — macros joined the fireable closed set
    # (REQ-DASHUI-012). Macro 3 is benign; Macro 9 mirrors acceptance.md
    # scenario 3's blacklisted-body macro number for cross-test convention.
    "DataPool/Macros": _snapshot("DataPool/Macros", [(3, "Blackout FX"), (9, "Danger Macro")]),
}


class _NoProvider:
    """The chat half is not under test here; a call would be a defect."""

    name = "none"
    model_id = "none"
    supports_prompt_caching = False

    def complete(self, *, system_prefix, conversation, tools=()):  # pragma: no cover
        raise AssertionError("the panel path must not reach the LLM provider")


class ApprovingPort:
    """Approval port that answers yes — the gate holds every invoking command
    whose reference it cannot expand, which includes ``Go+/Off Executor N``."""

    def __init__(self, approve: bool = True) -> None:
        self.approve = approve
        self.requests: list[object] = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return self.approve


class Harness:
    """One composed app: real gate + fake console + seeded panel store."""

    def __init__(self, *, gate, console, audit, store, deps, client, screened):
        self.gate = gate
        self.console = console
        self.audit = audit
        self.store = store
        self.deps = deps
        self.client = client
        self.screened = screened

    @property
    def sent(self) -> list[str]:
        return list(self.console.executed)

    def audit_sends(self, command: str) -> int:
        """How many 1:1 send↔audit ``executed`` records name ``command``."""
        return sum(
            1
            for event in self.audit.iter_events()
            if event.get("event") == "executed"
            and event.get("command") == command
            and event.get("kind") == "command"
        )


class OverlapDetectingConsole(FakeConsole):
    """Records whether two sends were ever in flight at the same time.

    The stop lane's serialization is a STRUCTURAL guarantee (every screen()
    resets this session's clearance Counter, so overlapping stops can strand
    each other), and a structural guarantee needs a structural test: a fast
    fake console would let an unserialized lane pass by luck. This one holds
    each send open long enough that an overlap, if the lane permitted one,
    cannot be missed.
    """

    def __init__(self, hold_seconds: float = 0.05) -> None:
        super().__init__()
        self._hold = hold_seconds
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0

    def execute(self, command: str):
        with self._lock:
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)
        try:
            time.sleep(self._hold)
            return super().execute(command)
        finally:
            with self._lock:
                self._in_flight -= 1


class CoordinatedConsole(FakeConsole):
    """Parks one named send until released, so a second path can interleave."""

    def __init__(self, *, pause_on: str) -> None:
        super().__init__()
        self.pause_on = pause_on
        self.reached = threading.Event()
        self.resume = threading.Event()

    def execute(self, command: str):
        if command == self.pause_on:
            self.reached.set()
            self.resume.wait(10.0)
        return super().execute(command)


def make_harness(
    tmp_path,
    *,
    approval_port=None,
    provider=None,
    refresh: bool = True,
    pins: list[dict] | None = None,
    console=None,
) -> Harness:
    console = console or FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    gate = SafetyGate(
        console=console,
        audit=audit,
        approval_port=approval_port or ApprovingPort(),
        monitor=HealthMonitor(),
    )
    screened: list[list[str]] = []
    inner = gate.screen

    def spy(commands):
        screened.append(list(commands))
        return inner(commands)

    gate.screen = spy  # type: ignore[method-assign]

    pin_store = PinStore(tmp_path / "panel_pins.json")
    for pin in pins or []:
        pin_store.add(pin)
    store = PanelStore(state_port=FakeStatePort(RIG_TREE), pins=pin_store)
    if refresh:
        store.refresh_catalog()
    deps = WebDeps(
        gate=gate,
        provider=provider or _NoProvider(),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=ApprovalChannel(timeout_seconds=10.0),
        panel=store,
    )
    return Harness(
        gate=gate,
        console=console,
        audit=audit,
        store=store,
        deps=deps,
        client=TestClient(create_app(deps)),
        screened=screened,
    )


@pytest.fixture()
def harness(tmp_path):
    return make_harness(tmp_path)


def _send(ws, **fields) -> None:
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


def _recv(ws, timeout: float = 10.0) -> dict:
    """One frame, or a failure — never a hang.

    ``TestClient``'s websocket receive has no timeout, so a missing frame would
    block the whole suite forever. This suite is concurrency-heavy by nature
    (two lanes, a parked approval, a chat turn in flight), which is exactly the
    shape where "it hangs" is the most likely failure — so it must be the most
    visible one.
    """
    box: dict[str, object] = {}

    def pump() -> None:
        try:
            box["event"] = ws.receive_json()
        except Exception as error:  # closed socket, decode failure, …
            box["error"] = error

    worker = threading.Thread(target=pump, daemon=True)
    worker.start()
    worker.join(timeout)
    if "event" not in box:
        raise AssertionError(f"no websocket frame within {timeout}s ({box.get('error')})")
    return box["event"]  # type: ignore[return-value]


def _drain(ws, event_type: str, *, limit: int = 40) -> dict:
    seen: list[str] = []
    for _ in range(limit):
        event = _recv(ws)
        seen.append(event["type"])
        if event["type"] == event_type:
            return event
    raise AssertionError(f"no {event_type!r} within {limit} frames: {seen}")


# -- the command bundle ----------------------------------------------------------


class TestPlaybackCommand:
    """The ONLY place a panel command string is built (REQ-SHOWUI-006/025/026)."""

    def test_executor_targets_use_the_console_playback_verbs(self):
        assert playback_command("Go+", "executor", 191) == "Go+ Executor 191"
        assert playback_command("Off", "executor", 191) == "Off Executor 191"

    def test_sequence_targets_address_the_sequence_pool(self):
        assert playback_command("Go+", "sequence", 41) == "Go+ Sequence 41"

    def test_an_unaddressable_class_cannot_produce_a_command(self):
        # REQ-SHOWUI-003: a fixture `no` is a patch slot, never a fire address.
        with pytest.raises(ValueError):
            playback_command("Go+", "fixture", 3)

    def test_a_non_positive_target_cannot_produce_a_command(self):
        for bad in (0, -1, True, "5", None):
            with pytest.raises(ValueError):
                playback_command("Go+", "executor", bad)

    def test_only_the_two_console_verbs_are_constructible(self):
        for bad in ("Delete", "Off Everything", "Go", ""):
            with pytest.raises(ValueError):
                playback_command(bad, "executor", 5)


class TestMacroPlaybackCommand:
    """SPEC-COPILOT-DASHUI-001 M1 — the rulebook-verified macro run form.

    The macro extension lives INSIDE ``playback_command`` (the sole command
    construction site, @MX:ANCHOR) — the closed verb set and the
    single-positive-integer property are preserved (REQ-DASHUI-010/012).
    """

    def test_a_macro_press_is_the_bare_rulebook_form(self):
        # rulebook 00_grammar.md:60 — ``Macro 3``. The run form has NO playback
        # verb word in front of it; ``Go+ Macro 3`` is not a verified command.
        assert playback_command("Go+", "macro", 3) == "Macro 3"

    def test_a_macro_has_no_stop_form(self):
        # One-shot by decision (plan.md §F D1 / M5): no rulebook-verified stop
        # form exists, so ``Off`` on a macro is UNCONSTRUCTIBLE, not guessed.
        with pytest.raises(ValueError):
            playback_command("Off", "macro", 3)

    def test_a_macro_target_is_still_a_single_object_number(self):
        for bad in (0, -1, True, "3", "3 Thru 9", None):
            with pytest.raises(ValueError):
                playback_command("Go+", "macro", bad)

    def test_no_third_verb_reaches_the_macro_form(self):
        for bad in ("Delete", "Go", "Macro", ""):
            with pytest.raises(ValueError):
                playback_command(bad, "macro", 3)


class TestWideTargetsAreUnconstructible:
    """REQ-SHOWUI-026 — no wide target may ever leave the panel."""

    def test_the_panel_module_contains_no_wide_target_literal(self):
        source = PANEL_MODULE.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        # Quoted string literals only — the prose in docstrings explains WHY
        # these are banned and must stay readable.
        literals = re.findall(r"""["']([^"'\n]*)["']""", code)
        for literal in literals:
            assert "Thru" not in literal, f"wide-target literal in panel.py: {literal!r}"
            assert "Everything" not in literal, f"wide-target literal: {literal!r}"

    def test_a_wide_target_cannot_be_smuggled_through_the_builder(self):
        for bad in ("5 Thru 9", "*", "Everything"):
            with pytest.raises(ValueError):
                playback_command("Off", "executor", bad)


# -- membership (REQ-SHOWUI-022, AC-SHOWUI-005 rejection half) --------------------


class TestMembershipGuard:
    def test_an_unknown_target_never_reaches_the_gate(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=9999)
            event = _drain(ws, "error")
        assert event["message"] == PANEL_UNKNOWN_TARGET_MESSAGE
        assert harness.screened == [], "gate.screen() must NOT be called for an unknown target"
        assert harness.sent == []

    def test_the_object_class_is_part_of_membership(self, harness):
        # Sequence 41 exists; Executor 41 does not. A bare number cannot tell
        # them apart — the (class, number) pair must.
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=41)
            _drain(ws, "error")
        assert harness.screened == []

    def test_a_malformed_target_is_refused_at_parse_time(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            for bad in (0, -3, "191", 1.5, None, True):
                _send(ws, type="panel_execute", target_kind="executor", target=bad)
                event = _drain(ws, "error")
                assert event["kind"] == "protocol"
        assert harness.screened == []
        assert harness.sent == []

    def test_a_pinned_target_is_a_member_even_without_a_catalog(self, tmp_path):
        pin = {
            "kind": "sequence",
            "target_kind": "executor",
            "target": 201,
            "name": "Pinned Look",
            "appearance": None,
        }
        harness = make_harness(tmp_path, refresh=False, pins=[pin])
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=201)
            _drain(ws, "panel_item_state")
        assert harness.screened == [["Go+ Executor 201"]]
        assert harness.sent == ["Go+ Executor 201"]

    def test_membership_is_rechecked_below_the_transport(self, harness):
        # Defence in depth: the runtime refuses even when called DIRECTLY, so a
        # future caller cannot skip the check by not going through /ws. This is
        # the branch that keeps "no bundle, no screen" a property of the firing
        # method rather than of one dispatch site.
        events: list[dict] = []
        runtime = PanelRuntime(
            gate=harness.gate,
            store=harness.store,
            send_event=events.append,
            session_key=new_session_key(),
        )
        assert runtime.contains("executor", 191) is True
        assert runtime.contains("executor", 9999) is False

        outcome = runtime.fire("Go+", "executor", 9999)
        assert outcome.status == "unknown_target"
        assert outcome.screened is False
        assert outcome.command == "", "no bundle may be built for an unknown target"
        assert [e["type"] for e in events] == ["error"]
        assert harness.screened == []
        assert harness.sent == []


# -- gate routing (AC-SHOWUI-005) -------------------------------------------------


class TestGateRouting:
    def test_one_press_is_one_screened_bundle_one_send_one_audit_record(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            state = _drain(ws, "panel_item_state")
        assert harness.screened == [["Go+ Executor 191"]]
        assert harness.sent == ["Go+ Executor 191"]
        assert harness.audit_sends("Go+ Executor 191") == 1
        assert state["running"] is True
        assert state["id"] == "executor:191"

    def test_stop_builds_the_off_bundle(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_stop", target_kind="executor", target=191)
            state = _drain(ws, "panel_item_state")
        assert harness.screened == [["Off Executor 191"]]
        assert harness.sent == ["Off Executor 191"]
        assert state["running"] is False

    def test_a_sequence_tile_addresses_the_sequence_pool(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="sequence", target=41)
            _drain(ws, "panel_item_state")
        assert harness.sent == ["Go+ Sequence 41"]

    def test_without_a_clearance_nothing_is_sent(self, tmp_path):
        # A rejected approval clears nothing — the execution port then refuses.
        harness = make_harness(tmp_path, approval_port=ApprovingPort(approve=False))
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            error = _drain(ws, "error")
        assert harness.screened == [["Go+ Executor 191"]]
        assert harness.sent == [], "no clearance -> zero console sends"
        assert error["kind"] == "panel"
        assert any("가" <= ch <= "힣" for ch in error["message"])

    def test_a_console_failure_is_never_rendered_as_running(self, tmp_path):
        console = FakeConsole()
        console.fail_on["Go+ Executor 191"] = "no such executor"
        harness = make_harness(tmp_path, console=console)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            error = _drain(ws, "error")
            state = _drain(ws, "panel_item_state")
        assert error["kind"] == "panel"
        assert state["running"] is False, "a failed send must not light the tile"

    def test_an_unconfirmed_send_is_reported_as_unconfirmed(self, tmp_path):
        # REQ-MVP-032 inherited: unconfirmed is NOT a failure claim and NOT a
        # success claim, and nothing is auto-resent. The tile keeps the state
        # the panel actually knows rather than guessing either way.
        console = FakeConsole()
        console.unconfirmed_on.add("Go+ Executor 191")
        harness = make_harness(tmp_path, console=console)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            error = _drain(ws, "error")
            state = _drain(ws, "panel_item_state")
        assert "미확인" in error["message"]
        assert state["running"] is False
        assert harness.sent == ["Go+ Executor 191"], "sent once, and only once"

    def test_every_console_send_was_screened_first(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            _drain(ws, "panel_item_state")
            _send(ws, type="panel_stop", target_kind="executor", target=191)
            _drain(ws, "panel_item_state")
        screened_commands = [c for bundle in harness.screened for c in bundle]
        assert harness.sent == screened_commands


# -- macro gate routing (SPEC-COPILOT-DASHUI-001 M2, AC-DASHUI-006) ---------------


class TestMacroGateRouting:
    """A macro press builds the rulebook-verified bare form and goes through
    the SAME single screening path as every other panel command — no second
    entry, no bypass (REQ-DASHUI-012/020)."""

    def test_a_benign_macro_press_is_screened_and_sent(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="macro", target=3)
            state = _drain(ws, "panel_item_state")
        assert harness.screened == [["Macro 3"]]
        assert harness.sent == ["Macro 3"]
        assert harness.audit_sends("Macro 3") == 1
        assert state["id"] == "macro:3"

    def test_a_macro_press_never_latches_the_running_state(self, harness):
        # A macro is ONE-SHOT (no Off form exists — plan.md §F D1): were a
        # successful press to enter the running set, the tile would stay
        # lit-as-running forever, with no affordance that could ever clear it
        # (the live defect this test reproduces: tiles 1/13/150 stuck amber
        # after their first press, 2026-07-24).
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="macro", target=3)
            state = _drain(ws, "panel_item_state")
        assert state["running"] is False, "one-shot macros must not latch running"

    def test_a_macro_target_not_in_the_catalog_is_refused_before_the_gate(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="macro", target=999)
            event = _drain(ws, "error")
        assert event["message"] == PANEL_UNKNOWN_TARGET_MESSAGE
        assert harness.screened == []
        assert harness.sent == []

    def test_a_macro_stop_frame_never_reaches_the_console(self, harness):
        # playback_command has no macro stop form (one-shot, plan.md §F D1);
        # the parser still accepts a well-formed panel_stop frame (the closed
        # target_kind set is shared), so the refusal comes from
        # PanelRuntime.fire raising on the unconstructible command — the
        # panel task boundary catches it and reports an error, never a
        # silent reach to the console (REQ-SHOWUI-020's spirit: no bundle, no
        # gate call, no send for a command that cannot exist).
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_stop", target_kind="macro", target=3)
            error = _drain(ws, "error")
        assert error["kind"] == "panel"
        assert harness.screened == []
        assert harness.sent == []


# -- single screening path (AC-SHOWUI-006) ----------------------------------------


class TestSingleScreeningPath:
    def test_the_panel_module_never_imports_the_osc_send_surface(self):
        source = PANEL_MODULE.read_text(encoding="utf-8")
        for forbidden in ("server.bridge", "pythonosc"):
            assert forbidden not in source, f"panel.py must not reference {forbidden}"

    def test_the_panel_runtime_holds_no_execution_surface_of_its_own(self, harness):
        from server.web import panel as panel_module

        # The ONLY execution the panel can perform is the gate's own port.
        assert not hasattr(panel_module, "send_command")
        assert not hasattr(panel_module, "osc")

    def test_every_send_consumed_a_gate_clearance(self, harness):
        # Positive control that the boundary is not vacuous: bypassing screen()
        # and calling the port directly sends nothing.
        result = harness.gate.execution_port.execute("Go+ Executor 191")
        assert result.ok is False
        assert harness.sent == []


# -- approval (AC-SHOWUI-007) ------------------------------------------------------


class TestApprovalRoundTrip:
    def test_a_held_panel_bundle_surfaces_on_the_existing_approval_card(self, tmp_path):
        channel = ApprovalChannel(timeout_seconds=10.0)
        harness = make_harness(tmp_path, approval_port=channel)
        harness.deps.approval_channel = channel
        client = TestClient(create_app(harness.deps))
        with client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            request = _drain(ws, "approval_request")
            (item,) = request["items"]
            assert item["command"] == "Go+ Executor 191"
            assert item["risk_reasons"]
            _send(
                ws,
                type="approval_decision",
                request_id=request["request_id"],
                approved=True,
            )
            _drain(ws, "panel_item_state")
        assert harness.sent == ["Go+ Executor 191"]

    def test_a_rejected_panel_bundle_blocks_the_whole_bundle(self, tmp_path):
        channel = ApprovalChannel(timeout_seconds=10.0)
        harness = make_harness(tmp_path, approval_port=channel)
        harness.deps.approval_channel = channel
        client = TestClient(create_app(harness.deps))
        with client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            request = _drain(ws, "approval_request")
            _send(
                ws,
                type="approval_decision",
                request_id=request["request_id"],
                approved=False,
            )
            _drain(ws, "error")
        assert harness.sent == []

    def test_a_disconnect_denies_the_pending_panel_approval(self, tmp_path):
        # acceptance.md §D edge case 8 — fail-safe deny survives the panel path.
        channel = ApprovalChannel(timeout_seconds=10.0)
        harness = make_harness(tmp_path, approval_port=channel)
        harness.deps.approval_channel = channel
        client = TestClient(create_app(harness.deps))
        with client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            _drain(ws, "approval_request")
        assert harness.sent == []
        assert channel.pending_ids == ()


# -- live lock (AC-SHOWUI-008) ------------------------------------------------------


class TestLiveLock:
    def test_the_lock_demotes_a_panel_press_to_a_proposal_with_zero_sends(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="lock", active=True)
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            proposal = _drain(ws, "proposal")
        assert proposal["commands"] == ["Go+ Executor 191"]
        assert harness.sent == []

    def test_the_lock_also_demotes_a_panel_stop(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="lock", active=True)
            _drain(ws, "status")
            _send(ws, type="panel_stop", target_kind="executor", target=191)
            _drain(ws, "proposal")
        assert harness.sent == []


# -- blocked state (AC-SHOWUI-015 pytest half, REQ-SHOWUI-010) ----------------------


class TestBlockedStateIsSurfaced:
    def test_a_console_offline_press_gets_an_explicit_refusal(self, harness):
        harness.gate.monitor.note_ping_timeout()
        harness.gate.monitor.note_ping_timeout()
        harness.gate.monitor.note_ping_timeout()
        harness.gate.monitor.note_ping_timeout()
        assert harness.gate.monitor.executions_blocked is True
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            error = _drain(ws, "error")
        assert error["kind"] == "panel"
        assert error["message"], "a blocked press must never be silently swallowed"
        assert harness.sent == []

    def test_a_blocked_press_still_reports_the_tile_state(self, harness):
        harness.gate.monitor.note_ping_timeout()
        harness.gate.monitor.note_ping_timeout()
        harness.gate.monitor.note_ping_timeout()
        harness.gate.monitor.note_ping_timeout()
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            state = _drain(ws, "panel_item_state")
        # The tile must be released, and released to the TRUTH: nothing ran.
        assert state["running"] is False


# -- serialization (AC-SHOWUI-009) ---------------------------------------------------


class _GatedApproval:
    """Approval port that parks the FIRST request until released."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.requests: list[object] = []
        self._first = True

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        if self._first:
            self._first = False
            self.entered.set()
            self.release.wait(10.0)
        return True


class TestSerialization:
    def test_a_second_execute_while_one_is_in_flight_is_refused_busy(self, tmp_path):
        approval = _GatedApproval()
        harness = make_harness(tmp_path, approval_port=approval)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            assert approval.entered.wait(5.0), "the first execute must reach the gate"
            for _ in range(3):
                _send(ws, type="panel_execute", target_kind="executor", target=5)
            busies = [_drain(ws, "panel_busy") for _ in range(3)]
            approval.release.set()
            _drain(ws, "panel_item_state")
        assert all(b["message"] == PANEL_BUSY_MESSAGE for b in busies)
        assert all(b["id"] == "executor:5" for b in busies), "busy must name the refused tile"
        assert harness.sent == ["Go+ Executor 191"], "exactly one of N executes ran"
        assert harness.screened == [["Go+ Executor 191"]], "a busy refusal builds no bundle"

    def test_a_stop_is_exempt_from_the_busy_guard(self, tmp_path):
        approval = _GatedApproval()
        harness = make_harness(tmp_path, approval_port=approval)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            assert approval.entered.wait(5.0)
            _send(ws, type="panel_stop", target_kind="executor", target=5)
            # The stop is handled while the execute is parked inside screen():
            # no panel_busy, and its own screen() call happens concurrently.
            state = _drain(ws, "panel_item_state")
            assert state["id"] == "executor:5"
            assert state["running"] is False
            assert ["Off Executor 5"] in harness.screened
            approval.release.set()
            _drain(ws, "panel_item_state")
        assert "Off Executor 5" in harness.sent

    def test_the_chat_turn_lock_is_not_shared_with_the_panel(self, tmp_path):
        # REQ-SHOWUI-013: a chat turn in flight must not busy-out the panel.
        provider = ScriptedProvider([_run_turn(["Store Group 3"], "c1"), _final("완료")])
        harness = make_harness(tmp_path, provider=provider)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="chat", text="보컬 그룹 만들어줘")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            events = []
            for _ in range(20):
                events.append(_recv(ws))
                types = [e["type"] for e in events]
                if "chat_response" in types and "panel_item_state" in types:
                    break
        types = [e["type"] for e in events]
        assert "panel_item_state" in types, "the panel ran while a chat turn was in flight"
        assert "busy" not in types, "the panel must not consume the chat turn lock"
        assert "Go+ Executor 191" in harness.sent

    def test_a_panel_screen_does_not_invalidate_a_chat_bundles_clearance(self, tmp_path):
        # REQ-SHOWUI-013, the half a busy-event assert cannot see. The gate keys
        # clearances PER SESSION and every screen() resets that session's
        # Counter, so if the panel shared the chat's session key, a tile press
        # landing between two commands of a chat bundle would strand the rest of
        # that bundle. The panel therefore carries its OWN key.
        console = CoordinatedConsole(pause_on="Store Group 3")
        provider = ScriptedProvider(
            [_run_turn(["Store Group 3", "Store Group 4"], "c1"), _final("완료")]
        )
        harness = make_harness(tmp_path, provider=provider, console=console)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="chat", text="그룹 두 개 만들어줘")
            assert console.reached.wait(5.0), "the chat bundle must be mid-execution"
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            _drain(ws, "panel_item_state")  # the panel screened AND executed
            console.resume.set()
            response = _drain(ws, "chat_response")
        statuses = {c["command"]: c["status"] for c in response["commands"]}
        assert statuses == {"Store Group 3": "executed_ok", "Store Group 4": "executed_ok"}, (
            "a panel press stranded the chat bundle's clearance — the two paths "
            "are sharing one session key"
        )

    def test_a_panel_execution_does_not_busy_out_a_chat_turn(self, tmp_path):
        approval = _GatedApproval()
        provider = ScriptedProvider([_run_turn(["Store Group 3"], "c1"), _final("완료")])
        harness = make_harness(tmp_path, approval_port=approval, provider=provider)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_execute", target_kind="executor", target=191)
            assert approval.entered.wait(5.0)
            _send(ws, type="chat", text="보컬 그룹 만들어줘")
            approval.release.set()
            events = []
            for _ in range(20):
                events.append(_recv(ws))
                if events[-1]["type"] == "chat_response":
                    break
        assert "busy" not in [e["type"] for e in events]


# -- All Off, bounded enumeration (REQ-SHOWUI-025/026) ------------------------------


class TestAllOffBoundedEnumeration:
    def test_n_running_executors_yield_exactly_n_off_commands(self, harness):
        running = [5, 11, 191]
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            for target in running:
                _send(ws, type="panel_execute", target_kind="executor", target=target)
                _drain(ws, "panel_item_state")
            harness.console.executed.clear()
            # The All Off gesture: one stop per tracked running executor.
            for target in running:
                _send(ws, type="panel_stop", target_kind="executor", target=target)
            for _ in running:
                _drain(ws, "panel_item_state")
        assert harness.sent == [f"Off Executor {n}" for n in running]
        assert len(harness.sent) == len(set(harness.sent)), "no duplicates"

    def test_serialized_stops_do_not_cancel_each_other_out(self, harness):
        # The clearance Counter is session-keyed and screen() RESETS it, so two
        # stops screened concurrently would leave the first one uncleared and
        # silently un-stopped. Serializing the stop lane is what makes an All
        # Off of N tiles actually stop N tiles.
        targets = [5, 11, 191]
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            for target in targets:
                _send(ws, type="panel_stop", target_kind="executor", target=target)
            for _ in targets:
                _drain(ws, "panel_item_state")
        assert sorted(harness.sent) == sorted(f"Off Executor {n}" for n in targets)

    def test_stops_never_overlap_on_the_wire(self, tmp_path):
        # The lane is what makes N stops actually stop N tiles. Without it the
        # sends interleave, and an interleaved pair can strand each other's
        # clearance — an All Off that silently leaves a light on.
        console = OverlapDetectingConsole()
        harness = make_harness(tmp_path, console=console)
        targets = [5, 11, 191]
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            for target in targets:
                _send(ws, type="panel_stop", target_kind="executor", target=target)
            for _ in targets:
                _drain(ws, "panel_item_state")
        assert console.max_in_flight == 1, (
            "two panel stops were in flight at once — the stop lane is not serializing"
        )
        assert sorted(harness.sent) == sorted(f"Off Executor {n}" for n in targets)

    def test_zero_tracked_running_items_is_a_no_op(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_catalog_request")
            _drain(ws, "panel_catalog")
        # acceptance.md §D edge case 6 — nothing running, nothing sent, no error.
        assert harness.sent == []
        assert harness.screened == []


# -- catalog / pin / unpin routing ----------------------------------------------------


class TestCatalogAndPinRouting:
    def test_a_catalog_request_answers_with_the_tile_list(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_catalog_request")
            event = _drain(ws, "panel_catalog")
        ids = [item["id"] for item in event["items"]]
        assert "executor:191" in ids
        assert "sequence:41" in ids
        assert "sequence:3" not in ids, "keyed on the real no, never a list position"
        assert [s["name"] for s in event["sections"]] == ["sequences", "pages", "macros"]

    def test_a_pin_without_a_seed_is_an_explicit_error(self, harness):
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_pin")
            event = _drain(ws, "error")
        assert event["message"] == PIN_SEED_UNAVAILABLE_MESSAGE

    def test_a_pin_with_a_seed_appends_a_tile_and_persists_it(self, tmp_path):
        # End to end through the REAL seed: a chat turn creates a look, then the
        # panel_pin frame reads that session's own cross-turn memory. The panel
        # holds no second source of truth for "what did the chat just create".
        provider = ScriptedProvider(
            [
                _run_turn(
                    ["Store Sequence 71", "Assign Sequence 71 At Executor 201"], "c1"
                ),
                _final("연출을 만들었습니다"),
            ]
        )
        harness = make_harness(tmp_path, provider=provider)
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="chat", text="연출 만들어줘")
            _drain(ws, "chat_response")
            _send(ws, type="panel_pin")
            event = _drain(ws, "panel_catalog")
        assert event["items"][0]["id"] == "executor:201", "pins lead the grid"
        assert event["items"][0]["name"] == "Sequence 71"
        assert PinStore(tmp_path / "panel_pins.json").contains("executor", 201)

    def test_unpin_removes_the_tile_and_persists_the_removal(self, tmp_path):
        pin = {
            "kind": "sequence",
            "target_kind": "executor",
            "target": 201,
            "name": "Pinned Look",
            "appearance": None,
        }
        harness = make_harness(tmp_path, pins=[pin])
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_unpin", target_kind="executor", target=201)
            event = _drain(ws, "panel_catalog")
        assert all(item["id"] != "executor:201" for item in event["items"])
        assert PinStore(tmp_path / "panel_pins.json").contains("executor", 201) is False

    def test_a_panel_failure_is_reported_and_does_not_kill_the_socket(self, tmp_path):
        # A panel task runs on a worker thread; an unhandled exception there
        # would otherwise vanish into a task nobody awaits, leaving the operator
        # pressing a refresh that silently does nothing.
        class ExplodingStore(PanelStore):
            def refresh_catalog(self):
                raise RuntimeError("state port on fire")

        harness = make_harness(tmp_path)
        harness.deps.panel = ExplodingStore(
            state_port=FakeStatePort(RIG_TREE), pins=PinStore(tmp_path / "panel_pins.json")
        )
        client = TestClient(create_app(harness.deps))
        with client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_catalog_request")
            error = _drain(ws, "error")
            # The socket is still usable afterwards.
            _send(ws, type="status_request")
            assert _drain(ws, "status")["type"] == "status"
        assert error["kind"] == "panel"

    def test_unpinning_something_that_was_never_pinned_is_an_explicit_error(self, harness):
        # A catalog tile is a member for FIRING but is not a pin, so unpinning
        # it is meaningless. Answering with a catalog event would tell the UI
        # "done" about work that never happened.
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_unpin", target_kind="executor", target=191)
            event = _drain(ws, "error")
        assert event["message"] == PANEL_UNKNOWN_TARGET_MESSAGE
        assert event["kind"] == "panel"

    def test_panel_messages_no_longer_fall_through_to_the_status_snapshot(self, harness):
        # The M1 carry-forward: every panel type used to land on the
        # `else: # status_request` fallback and answer with a status frame.
        with harness.client as client, client.websocket_connect("/ws") as ws:
            _drain(ws, "status")
            _send(ws, type="panel_catalog_request")
            first = _recv(ws)
        assert first["type"] == "panel_catalog"
