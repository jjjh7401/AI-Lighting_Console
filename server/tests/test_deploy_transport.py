"""Deploy transport tests (M7 — wire builder + ConsoleLink + gate deploy surface).

The deployment send is console-bound traffic: it MUST ride the gate
(REQ-MVP-029) and be audited 1:1 like every other send. The wire form is a
new responder verb (``deploy <id> <enc-name> <enc-source>`` — PROTOCOL.md §2,
percent-encoded so the payload survives MA3 plugin-argument quoting), an
onPC-unverified protocol extension recorded as ASSUMPTION-6.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable

import pytest

from server.bridge.osc import FEEDBACK_ADDRESS, FeedbackMessage
from server.bridge.protocol import ProtocolError, build_deploy_request, encode_payload
from server.deploy.pack import import_slug
from server.safety.audit import AuditLog
from server.safety.console import ConsoleLink, LinkTimeouts
from server.safety.gate import SafetyGate
from server.safety.monitor import HealthMonitor

from .test_safety_gate import FakeConsole

_FAST = LinkTimeouts(
    exec_confirm_seconds=0.05,
    ping_seconds=0.05,
    state_query_seconds=0.05,
    deploy_confirm_seconds=0.05,
)

_DEPLOY_WIRE = re.compile(r'^Plugin "CopilotResponder" "deploy (\S+) (\S+) (\S+)"$')


class TestBuildDeployRequest:
    def test_wire_shape_and_percent_encoding(self):
        wire = build_deploy_request("d-1", "My Cleaner", 'Cmd("Delete 1")\n')
        match = _DEPLOY_WIRE.match(wire)
        assert match, wire
        rid, enc_name, enc_source = match.groups()
        assert rid == "d-1"
        assert urllib.parse.unquote(enc_name) == "My Cleaner"
        assert urllib.parse.unquote(enc_source) == 'Cmd("Delete 1")\n'

    def test_encoded_payload_is_quote_and_space_free(self):
        wire = build_deploy_request("d-2", 'na"me', 'x = "샤막"\n')
        inner = wire[len('Plugin "CopilotResponder" "') : -1]
        # The MA3 plugin argument tolerates no embedded double quote; the
        # encoded tokens must therefore be pure [A-Za-z0-9-._~%] + separators.
        assert '"' not in inner
        assert re.fullmatch(r"deploy [A-Za-z0-9._-]+ \S+ \S+", inner), inner

    def test_invalid_request_id_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_deploy_request("bad id", "Cleaner", "return 1")

    def test_empty_name_or_source_is_rejected(self):
        with pytest.raises(ProtocolError):
            build_deploy_request("d-3", "", "return 1")
        with pytest.raises(ProtocolError):
            build_deploy_request("d-3", "Cleaner", "")


def _deploy_echo_send(link: ConsoleLink, *, ok: bool = True, silent: bool = False):
    sent: list[str] = []

    def send(wire: str) -> None:
        sent.append(wire)
        if silent:
            return
        match = _DEPLOY_WIRE.match(wire)
        assert match, f"unexpected wire line: {wire!r}"
        rid, enc_name, _ = match.groups()
        payload = {
            "v": 1,
            "kind": "deploy",
            "id": rid,
            "ok": ok,
            "name": urllib.parse.unquote(enc_name),
        }
        if not ok:
            payload["error"] = "plugin pool unavailable"
        link.deliver(FeedbackMessage(address=FEEDBACK_ADDRESS, args=(encode_payload(payload),)))

    return send, sent


class TestConsoleLinkDeploy:
    def test_confirmed_deploy(self):
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _deploy_echo_send(link)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "ok"
        assert len(sent) == 1

    def test_console_error_is_reported(self):
        link = ConsoleLink(timeouts=_FAST)
        send, _ = _deploy_echo_send(link, ok=False)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "failed"
        assert "plugin pool unavailable" in outcome.detail

    def test_timeout_is_unconfirmed_never_resent(self):
        # REQ-MVP-032 discipline: send loss and reply loss are
        # indistinguishable; the link reports unconfirmed and sends ONCE.
        link = ConsoleLink(timeouts=_FAST)
        send, sent = _deploy_echo_send(link, silent=True)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "unconfirmed"
        assert len(sent) == 1


class DeployableFakeConsole(FakeConsole):
    """FakeConsole + the M7 deploy surface (+ M7.5 per-send records)."""

    def __init__(self, state_tree: dict | None = None):
        super().__init__(state_tree)
        self.deployed: list[tuple[str, str]] = []
        self.deploy_status = "ok"
        self.deploy_detail = "deployed"
        self.deploy_sends: tuple = ()

    def deploy_plugin(self, name: str, lua_source: str):
        from server.safety.console import ExecOutcome

        self.deployed.append((name, lua_source))
        return ExecOutcome(
            status=self.deploy_status, detail=self.deploy_detail, sends=self.deploy_sends
        )


def _gate(tmp_path, **kwargs):
    console = kwargs.pop("console", None) or DeployableFakeConsole()
    audit = AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, **kwargs)
    return gate, console, audit


def _events(audit, event_type):
    return [e for e in audit.iter_events() if e["event"] == event_type]


class TestGateDeploySurface:
    def test_deploy_send_is_audited_one_to_one(self, tmp_path):
        gate, console, audit = _gate(tmp_path)
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is True
        assert console.deployed == [("Cleaner", "return 1")]
        (event,) = [e for e in _events(audit, "executed") if e["kind"] == "deploy"]
        assert event["command"] == "Cleaner"
        assert event["ok"] is True

    def test_live_lock_blocks_the_deploy(self, tmp_path):
        # REQ-MVP-016: under the live lock NOTHING reaches the console.
        gate, console, audit = _gate(tmp_path)
        gate.lock.activate()
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert result.detail.startswith("blocked:")
        assert console.deployed == []
        assert _events(audit, "blocked") != []

    def test_console_offline_blocks_the_deploy(self, tmp_path):
        gate, console, _ = _gate(tmp_path, monitor=HealthMonitor())
        gate.monitor.note_ping_timeout()  # no prior activity -> console_offline
        assert gate.monitor.executions_blocked
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert result.detail.startswith("blocked:")
        assert console.deployed == []

    def test_unconfirmed_deploy_carries_the_marker(self, tmp_path):
        # Same honest-marker contract the chat surface pins (REQ-MVP-032).
        console = DeployableFakeConsole()
        console.deploy_status = "unconfirmed"
        console.deploy_detail = "no confirmation"
        gate, _, audit = _gate(tmp_path, console=console)
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert "execution unconfirmed" in result.detail
        (event,) = [e for e in _events(audit, "executed") if e["kind"] == "deploy"]
        assert event["ok"] is False

    def test_console_failure_detail_is_returned(self, tmp_path):
        console = DeployableFakeConsole()
        console.deploy_status = "failed"
        console.deploy_detail = "no plugin pool"
        gate, _, _ = _gate(tmp_path, console=console)
        result = gate.deploy_plugin_source("Cleaner", "return 1")
        assert result.ok is False
        assert "no plugin pool" in result.detail


# ------------------------------------------------- MA3-shaped plugin-pool double

_RESPONDER = "CopilotResponder"
_PATCH = "PatchPlugin"

_WIRE = re.compile(
    r'^Plugin "(?P<plugin>[^"]+)" "(?P<verb>ping|state|exec) (?P<rid>\S+)(?: (?P<rest>.*))?"$'
)
_IMPORT_CMD = re.compile(r"^Import Plugin (?P<slot>\d+) '(?P<stem>[^']+)'(?P<flags>(?: /\S+)*)$")
_DELETE_CMD = re.compile(r"^Delete Plugin (?P<slot>\d+)$")
_CANCELED = "User Canceled Command"


class PoolConsole:
    """Plugin-pool double that reproduces the 2.4.2 confirm-dialog refusals.

    Measured live in ``docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md``
    §1 and modelled here so the deploy path is tested against the console's real
    behaviour instead of an always-yes fake:

    ① a plugin may NOT delete the pool slot it is itself running in — MA3 raises
       a confirm dialog the OSC/exec path cannot answer, so the command comes
       back ``User Canceled Command``;
    ② importing a Name that already exists anywhere in the pool asks the same
       unanswerable question — unless ``/nc`` is passed;
    ③ a ``/nc`` duplicate import lands under a CONSOLE-chosen suffixed Name.

    Commands are recorded with their invoking plugin, so a test can assert who
    ran what. ``refuse`` / ``silent`` inject a per-command failure or a dropped
    reply (timeout).
    """

    def __init__(
        self,
        link: ConsoleLink,
        *,
        stems: dict[str, str],
        pool: dict[int, str] | None = None,
        alias_suffix: str = "#2",
    ) -> None:
        self._link = link
        self._stems = dict(stems)  # import stem -> the pool Name inside the XML
        self.pool: dict[int, str] = dict(pool or {})
        self.alias_suffix = alias_suffix
        self.calls: list[tuple[str, str]] = []  # (invoking plugin, exec command)
        self.state_reads: list[str] = []
        self.self_delete_attempts: list[tuple[str, int]] = []
        self.refuse: Callable[[str, str], str | None] = lambda invoker, command: None
        self.silent: Callable[[str, str], bool] = lambda invoker, command: False

    @property
    def commands(self) -> list[str]:
        return [command for _invoker, command in self.calls]

    def invokers_of(self, command: str) -> list[str]:
        return [invoker for invoker, sent in self.calls if sent == command]

    def send(self, wire: str) -> None:
        match = _WIRE.match(wire)
        assert match, f"unexpected wire line: {wire!r}"
        invoker, verb, rid, rest = match.group("plugin", "verb", "rid", "rest")
        if verb == "ping":
            self._reply(FEEDBACK_ADDRESS, {"v": 1, "kind": "pong", "id": rid, "ok": True})
            return
        if verb == "state":
            self.state_reads.append(rest or "")
            self._reply(
                "/copilot/state",
                {
                    "v": 1,
                    "kind": "state",
                    "id": rid,
                    "ok": True,
                    "path": rest,
                    "children": [
                        {"i": slot, "name": name} for slot, name in sorted(self.pool.items())
                    ],
                },
            )
            return
        command = rest or ""
        self.calls.append((invoker, command))
        if self.silent(invoker, command):
            return  # dropped reply -> the link reports unconfirmed
        error = self.refuse(invoker, command) or self._apply(invoker, command)
        payload = {"v": 1, "kind": "result", "id": rid, "ok": error is None}
        payload["error" if error else "result"] = error or "OK"
        self._reply(FEEDBACK_ADDRESS, payload)

    def _apply(self, invoker: str, command: str) -> str | None:
        """Run one command against the modelled pool; None means ok."""
        if invoker != _RESPONDER and invoker not in self.pool.values():
            # Addressing an object that is not in the pool (a deleted alias).
            return f"no such plugin: {invoker}"
        delete = _DELETE_CMD.match(command)
        if delete:
            slot = int(delete.group("slot"))
            if self.pool.get(slot) == invoker:
                self.self_delete_attempts.append((invoker, slot))
                return _CANCELED  # ① self-delete confirm dialog
            if slot not in self.pool:
                return f"no plugin in slot {slot}"
            del self.pool[slot]
            return None
        imported = _IMPORT_CMD.match(command)
        if imported:
            slot = int(imported.group("slot"))
            name = self._stems.get(imported.group("stem"))
            if name is None:
                return f"no such plugin file: {imported.group('stem')}"
            if slot in self.pool:
                return f"slot {slot} is occupied by {self.pool[slot]}"
            if name in self.pool.values():
                if " /nc" not in imported.group("flags"):
                    return _CANCELED  # ② duplicate-Name confirm dialog
                name = f"{name}{self.alias_suffix}"  # ③ console picks the Name
            self.pool[slot] = name
            return None
        return None

    def _reply(self, address: str, payload: dict) -> None:
        self._link.deliver(FeedbackMessage(address=address, args=(encode_payload(payload),)))


def _pool_link(tmp_path, *, pool=None, names=(_RESPONDER, _PATCH), alias_suffix="#2"):
    link = ConsoleLink(
        timeouts=LinkTimeouts(exec_confirm_seconds=2.0, state_query_seconds=2.0),
        import_dir=tmp_path / "plugins",
    )
    console = PoolConsole(
        link,
        stems={import_slug(name): name for name in names},
        pool=pool,
        alias_suffix=alias_suffix,
    )
    link.bind_send(console.send)
    return link, console


# ---------------------------------------------------------------- M7.5 per-send granularity


class TestFileImportPerSendRecords:
    """M7.5 (AC-DEPLOY-027 Layer ②) — every console round-trip inside a
    file+Import deploy is returned as its own ``DeploySend`` record, so the
    gate can audit each wire send 1:1 instead of one blanket ``deploy`` event."""

    def _import_link(self, tmp_path):
        from .test_responder_import_gate import RecordingConsole

        link = ConsoleLink(
            timeouts=LinkTimeouts(exec_confirm_seconds=2.0, state_query_seconds=2.0),
            import_dir=tmp_path / "plugins",
        )
        console = RecordingConsole(link)
        link.bind_send(console.send)
        return link, console

    def test_fresh_deploy_returns_one_record_per_round_trip(self, tmp_path):
        link, _console = self._import_link(tmp_path)
        outcome = link.deploy_plugin("CopilotResponder", "return 1")
        assert outcome.status == "ok"
        assert [(s.kind, s.command, s.ok) for s in outcome.sends] == [
            ("state_query", "DataPool/Plugins", True),
            ("command", "Import Plugin 1 'CopilotResponder'", True),
            ("state_query", "DataPool/Plugins", True),
        ]

    def test_redeploy_records_the_delete_round_trip_too(self, tmp_path):
        # A NON-responder plugin keeps the direct-delete path (the responder's
        # own redeploy goes through the alias swap — see TestResponderAliasRedeploy).
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER, 2: _PATCH})
        outcome = link.deploy_plugin(_PATCH, "return 2")
        assert outcome.status == "ok"
        assert ("command", "Delete Plugin 2") in [(s.kind, s.command) for s in outcome.sends]
        assert len(outcome.sends) == 4  # pool read + Delete + Import + confirm read
        assert console.pool == {1: _RESPONDER, 2: _PATCH}

    def test_timeout_path_still_records_the_sends_that_hit_the_wire(self, tmp_path):
        # No replies at all: the pool read times out and the Import exec times
        # out — but both SENT a datagram, so both MUST be recorded (a lost
        # reply is not a lost send; AC-DEPLOY-027 reconciles the wire).
        link = ConsoleLink(timeouts=_FAST, import_dir=tmp_path / "plugins")
        sent: list[str] = []
        link.bind_send(sent.append)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "unconfirmed"
        assert len(sent) == 2  # state query + Import Plugin exec
        assert [(s.kind, s.ok) for s in outcome.sends] == [
            ("state_query", False),
            ("command", False),
        ]

    def test_osc_verb_fallback_has_no_sub_sends(self):
        # The remote deploy verb is ONE wire send, already represented 1:1 by
        # the gate's parent kind="deploy" audit entry — no sub-records.
        link = ConsoleLink(timeouts=_FAST)  # no import_dir -> OSC deploy verb
        send, _ = _deploy_echo_send(link)
        link.bind_send(send)
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "ok"
        assert outcome.sends == ()


class TestFileImportSlotHonesty:
    """The free-slot arithmetic depends on ``i`` being a REAL pool slot.

    The responder omits ``i`` when it could not establish a child's slot
    (PROTOCOL.md §4.2). Guessing anyway would mean ``Import Plugin <slot>``
    into an occupied slot — the pool read exists precisely to prevent that.
    """

    def _link_with_pool(self, tmp_path, children: list[dict]):
        link = ConsoleLink(timeouts=_FAST, import_dir=tmp_path / "plugins")
        sent: list[str] = []

        def send(wire: str) -> None:
            sent.append(wire)
            match = re.match(r'^Plugin "CopilotResponder" "(state|exec) (\S+)(?: (.*))?"$', wire)
            assert match, wire
            kind, rid, rest = match.groups()
            if kind == "state":
                payload = {
                    "v": 1,
                    "kind": "state",
                    "id": rid,
                    "ok": True,
                    "path": rest,
                    "children": children,
                }
                address = "/copilot/state"
            else:
                payload = {"v": 1, "kind": "result", "id": rid, "ok": True, "result": "OK"}
                address = FEEDBACK_ADDRESS
            link.deliver(FeedbackMessage(address=address, args=(encode_payload(payload),)))

        link.bind_send(send)
        return link, sent

    def test_unnumbered_pool_entry_stops_the_import(self, tmp_path):
        link, sent = self._link_with_pool(
            tmp_path, [{"i": 1, "name": "Other"}, {"name": "SlotUnknown"}]
        )
        outcome = link.deploy_plugin("Cleaner", "return 1")
        assert outcome.status == "failed"
        assert "free plugin slot" in outcome.detail
        assert "1 plugin(s)" in outcome.detail
        # Nothing was imported or deleted: only the pool read hit the wire.
        assert len(sent) == 1
        assert [s.kind for s in outcome.sends] == ["state_query"]

    def test_fully_numbered_gapped_pool_picks_a_genuinely_free_slot(self, tmp_path):
        # Gapped pool (1, 5, 7): slot 2 is free and must be chosen. Under the
        # old positional `i` the same pool reported 1, 2, 3 — so slot 4 looked
        # free while the real slot 2 sat unused and slot 5 stayed hidden.
        link, _sent = self._link_with_pool(
            tmp_path,
            [{"i": 1, "name": "A"}, {"i": 5, "name": "B"}, {"i": 7, "name": "C"}],
        )
        outcome = link.deploy_plugin("Cleaner", "return 1")
        imports = [s.command for s in outcome.sends if s.kind == "command"]
        assert imports == ["Import Plugin 2 'Cleaner'"]


class TestGatePerSendDeployAudit:
    """M7.5 — the gate fans deploy sub-sends out into individual ``executed``
    audit entries correlated to the parent deploy (``deploy_of``)."""

    def test_sub_sends_get_their_own_audit_entries_with_correlation(self, tmp_path):
        from server.safety.console import DeploySend

        console = DeployableFakeConsole()
        console.deploy_sends = (
            DeploySend(kind="state_query", command="DataPool/Plugins", ok=True, outcome="ok"),
            DeploySend(kind="command", command="Import Plugin 1 'Cleaner'", ok=True, outcome="ok"),
        )
        gate, _, audit = _gate(tmp_path, console=console)
        assert gate.deploy_plugin_source("Cleaner", "return 1").ok is True

        executed = _events(audit, "executed")
        subs = [e for e in executed if e.get("deploy_of") == "Cleaner"]
        assert [(e["kind"], e["command"], e["ok"]) for e in subs] == [
            ("state_query", "DataPool/Plugins", True),
            ("command", "Import Plugin 1 'Cleaner'", True),
        ]
        # The parent deploy entry survives (approval/summary record) and counts
        # its sub-sends; sub-entries precede it in the durable log.
        (parent,) = [e for e in executed if e["kind"] == "deploy"]
        assert parent["command"] == "Cleaner"
        assert parent["deploy_sends"] == 2
        assert executed.index(parent) > max(executed.index(e) for e in subs)

    def test_deploy_without_sub_sends_stays_single_entry(self, tmp_path):
        # OSC-verb fallback / fakes: no sends -> exactly the old single entry.
        gate, _, audit = _gate(tmp_path)
        assert gate.deploy_plugin_source("Cleaner", "return 1").ok is True
        executed = _events(audit, "executed")
        assert len(executed) == 1
        assert executed[0]["kind"] == "deploy"
        assert executed[0]["deploy_sends"] == 0


# ------------------------------------------- responder redeploy: the self-delete trap

_ALIAS = f"{_RESPONDER}#2"
_ALIAS_IMPORT = f"Import Plugin 2 '{_RESPONDER}' /nc"
_DROP_OLD = "Delete Plugin 1"
_REIMPORT = f"Import Plugin 1 '{_RESPONDER}'"
_DROP_ALIAS = "Delete Plugin 2"


class TestResponderAliasRedeploy:
    """Redeploying the RESPONDER cannot go through the direct-delete path.

    ``ConsoleLink`` wraps every command as ``Plugin "CopilotResponder" "exec
    <id> <cmd>"``, so ``Delete Plugin <own slot>`` runs inside the object it
    deletes; MA3 2.4.2 answers that with a confirm dialog the OSC path cannot
    reach and reports ``User Canceled Command``
    (docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md §1.2).
    The alias swap (§1.3) is the measured way out.
    """

    def test_the_direct_path_would_have_been_refused_by_the_console(self, tmp_path):
        # Baseline that makes the rest of this class meaningful: the double
        # really does refuse a self-delete, so a test asserting the alias path
        # is not asserting against an always-yes fake.
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        assert link.execute(_DROP_OLD).status == "failed"
        assert console.self_delete_attempts == [(_RESPONDER, 1)]
        assert console.pool == {1: _RESPONDER}

    def test_redeploy_takes_the_alias_path_and_never_attempts_a_self_delete(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "ok", outcome.detail
        assert console.commands == [_ALIAS_IMPORT, _DROP_OLD, _REIMPORT, _DROP_ALIAS]
        # Double check ①: the console never saw a self-delete attempt at all.
        assert console.self_delete_attempts == []
        # Double check ②: every delete was issued from a DIFFERENT plugin than
        # the one it targets — the old slot from the alias, the alias from the
        # freshly imported primary.
        assert console.invokers_of(_DROP_OLD) == [_ALIAS]
        assert console.invokers_of(_DROP_ALIAS) == [_RESPONDER]
        assert console.invokers_of(_ALIAS_IMPORT) == [_RESPONDER]
        assert console.invokers_of(_REIMPORT) == [_ALIAS]

    def test_the_alias_name_is_read_from_the_pool_not_a_hardcoded_suffix(self, tmp_path):
        # MA3 picks the duplicate's Name; the code must learn it from the pool
        # re-read. A console that suffixes differently must still work.
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER}, alias_suffix="~dup")
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "ok", outcome.detail
        assert console.invokers_of(_DROP_OLD) == [f"{_RESPONDER}~dup"]
        assert f"{_RESPONDER}~dup" in outcome.detail
        assert "#2" not in outcome.detail

    def test_nc_is_only_on_the_alias_import(self, tmp_path):
        # `/nc` suppresses the duplicate-Name confirmation, which is needed
        # EXACTLY once: while the old object still holds the Name. The
        # re-import under the real Name must stay confirmable.
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        assert link.deploy_plugin(_RESPONDER, "return 2").status == "ok"
        assert [c for c in console.commands if "/nc" in c] == [_ALIAS_IMPORT]
        assert "/nc" not in _REIMPORT
        assert _REIMPORT in console.commands

    def test_the_alias_is_gone_and_one_copy_remains(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "ok"
        assert console.pool == {1: _RESPONDER}  # no `#2` leftover, original slot
        # ok is only reported after the confirming pool read proves that.
        assert console.state_reads == ["DataPool/Plugins"] * 3

    def test_retry_after_a_failed_swap_works_around_the_leftover_alias(self, tmp_path):
        # A previous swap that failed midway leaves its alias behind on purpose
        # (TestAliasFailurePreservesTheWorkingCopy). The next attempt must still
        # run: it picks the next free slot and uses whatever Name the console
        # gives THAT copy, leaving the stale one alone for the human who owns it.
        stale = f"{_RESPONDER}#2"
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER, 2: stale}, alias_suffix="#3")
        outcome = link.deploy_plugin(_RESPONDER, "return 3")
        assert outcome.status == "ok", outcome.detail
        assert console.commands == [
            f"Import Plugin 3 '{_RESPONDER}' /nc",
            _DROP_OLD,
            _REIMPORT,
            "Delete Plugin 3",
        ]
        assert console.invokers_of(_DROP_OLD) == [f"{_RESPONDER}#3"]
        assert console.pool == {1: _RESPONDER, 2: stale}

    def test_every_alias_round_trip_is_recorded_as_a_deploy_send(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert [(s.kind, s.command, s.ok) for s in outcome.sends] == [
            ("state_query", "DataPool/Plugins", True),
            ("command", _ALIAS_IMPORT, True),
            ("state_query", "DataPool/Plugins", True),
            ("command", _DROP_OLD, True),
            ("command", _REIMPORT, True),
            ("command", _DROP_ALIAS, True),
            ("state_query", "DataPool/Plugins", True),
        ]
        # 1:1 with the wire: seven records, seven datagrams.
        assert len(outcome.sends) == len(console.commands) + len(console.state_reads)
        # The record keeps the BARE command line (the wire subject the audit
        # reconciler keys on) and names the executing alias in the detail.
        alias_sends = [s for s in outcome.sends if s.detail.startswith("via ")]
        assert [s.command for s in alias_sends] == [_DROP_OLD, _REIMPORT]
        assert all(_ALIAS in s.detail for s in alias_sends)

    def test_gate_audits_each_alias_round_trip_individually(self, tmp_path):
        # AC-DEPLOY-027 Layer ②: the gate fans the sub-sends out, so a wire
        # capture spanning an alias swap still reconciles 1:1.
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        audit = AuditLog(tmp_path / "audit")
        gate = SafetyGate(console=link, audit=audit)
        assert gate.deploy_plugin_source(_RESPONDER, "return 2").ok is True
        subs = [e for e in _events(audit, "executed") if e.get("deploy_of") == _RESPONDER]
        assert [e["command"] for e in subs] == [
            "DataPool/Plugins",
            _ALIAS_IMPORT,
            "DataPool/Plugins",
            _DROP_OLD,
            _REIMPORT,
            _DROP_ALIAS,
            "DataPool/Plugins",
        ]
        assert len(subs) == len(console.commands) + len(console.state_reads)
        (parent,) = [e for e in _events(audit, "executed") if e["kind"] == "deploy"]
        assert parent["deploy_sends"] == len(subs)


class TestAliasFailurePreservesTheWorkingCopy:
    """A mid-sequence failure must LEAVE the alias in place — it is a working
    copy of the new source — and say where it is, because a human finishes the
    swap by hand from there."""

    def test_reimport_failure_keeps_the_alias_and_names_it(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        console.refuse = lambda invoker, command: "no free plugin" if command == _REIMPORT else None
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "failed"
        # The old version is gone and the new source survives as the alias.
        assert console.pool == {2: _ALIAS}
        assert _ALIAS in outcome.detail
        assert "slot 2" in outcome.detail
        assert "DELETED" in outcome.detail
        # The alias was NOT dropped in an attempt to tidy up.
        assert _DROP_ALIAS not in console.commands

    def test_old_delete_failure_reports_both_copies(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        console.refuse = lambda invoker, command: "locked" if command == _DROP_OLD else None
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "failed"
        assert console.pool == {1: _RESPONDER, 2: _ALIAS}
        assert _ALIAS in outcome.detail
        assert "slot 2" in outcome.detail
        assert "slot 1" in outcome.detail
        assert _DROP_ALIAS not in console.commands

    def test_alias_import_failure_leaves_the_old_version_untouched(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        console.refuse = lambda invoker, command: (
            "no free slot" if command == _ALIAS_IMPORT else None
        )
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "failed"
        assert console.pool == {1: _RESPONDER}
        assert "UNCHANGED" in outcome.detail
        assert console.commands == [_ALIAS_IMPORT]

    def test_alias_cleanup_failure_still_reports_the_leftover(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        console.refuse = lambda invoker, command: "busy" if command == _DROP_ALIAS else None
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        # The new version IS in place, but the pool holds the Lua twice —
        # that is not "ok" until the alias is gone.
        assert outcome.status == "failed"
        assert console.pool == {1: _RESPONDER, 2: _ALIAS}
        assert _ALIAS in outcome.detail
        assert "slot 2" in outcome.detail

    def test_alias_step_timeout_is_unconfirmed_and_not_retried(self, tmp_path):
        # REQ-MVP-032: a lost reply is unconfirmed, never re-sent.
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER})
        link._timeouts = _FAST  # noqa: SLF001 — shrink the wait for the test
        console.silent = lambda invoker, command: command == _DROP_OLD
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "unconfirmed"
        assert console.commands == [_ALIAS_IMPORT, _DROP_OLD]  # no retry, no cleanup
        assert _ALIAS in outcome.detail

    def test_unnumbered_entry_in_the_alias_re_read_refuses_and_names_the_alias(self, tmp_path):
        # The slot-honesty rule (PROTOCOL.md §4.2) applies to the SECOND pool
        # read too: with an unplaceable plugin listed, the remaining slot
        # arithmetic would be a guess.
        link, sent = _scripted_pool_link(
            tmp_path,
            [
                [{"i": 1, "name": _RESPONDER}],
                [{"i": 1, "name": _RESPONDER}, {"name": "SlotUnknown"}],
            ],
        )
        outcome = link.deploy_plugin(_RESPONDER, "return 2")
        assert outcome.status == "failed"
        assert "free plugin slot" in outcome.detail
        assert "1 plugin(s)" in outcome.detail
        assert "slot 2" in outcome.detail  # where the working copy now lives
        # Pool read, alias import, pool re-read — and then it stopped.
        assert len(sent) == 3


def _scripted_pool_link(tmp_path, pools):
    """Link whose successive pool reads return scripted children (the last
    entry repeats) and whose execs always report ok."""
    link = ConsoleLink(timeouts=_FAST, import_dir=tmp_path / "plugins")
    sent: list[str] = []
    reads = list(pools)

    def send(wire: str) -> None:
        sent.append(wire)
        match = _WIRE.match(wire)
        assert match, wire
        verb, rid, rest = match.group("verb", "rid", "rest")
        if verb == "state":
            children = reads.pop(0) if len(reads) > 1 else reads[0]
            link.deliver(
                FeedbackMessage(
                    address="/copilot/state",
                    args=(
                        encode_payload(
                            {
                                "v": 1,
                                "kind": "state",
                                "id": rid,
                                "ok": True,
                                "path": rest,
                                "children": children,
                            }
                        ),
                    ),
                )
            )
            return
        link.deliver(
            FeedbackMessage(
                address=FEEDBACK_ADDRESS,
                args=(
                    encode_payload(
                        {"v": 1, "kind": "result", "id": rid, "ok": True, "result": "OK"}
                    ),
                ),
            )
        )

    link.bind_send(send)
    return link, sent


class TestNonResponderRedeployKeepsTheDirectPath:
    """A foreign plugin is not the executing object, so its delete needs no
    alias — and must not grow extra round-trips."""

    def test_patch_plugin_redeploy_uses_delete_then_import(self, tmp_path):
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER, 2: _PATCH})
        outcome = link.deploy_plugin(_PATCH, "return 2")
        assert outcome.status == "ok", outcome.detail
        assert console.commands == ["Delete Plugin 2", f"Import Plugin 2 '{_PATCH}'"]
        assert console.invokers_of("Delete Plugin 2") == [_RESPONDER]
        assert [c for c in console.commands if "/nc" in c] == []
        assert len(outcome.sends) == 4  # pool read + Delete + Import + confirm read
        assert console.pool == {1: _RESPONDER, 2: _PATCH}

    def test_a_refused_delete_falls_back_to_the_alias_swap(self, tmp_path):
        # The old code discarded the Delete result and imported anyway. A
        # refusal now routes through the alias, which never needs that delete
        # to be issued from the responder.
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER, 2: _PATCH})
        console.refuse = lambda invoker, command: (
            _CANCELED if invoker == _RESPONDER and command == "Delete Plugin 2" else None
        )
        outcome = link.deploy_plugin(_PATCH, "return 2")
        assert outcome.status == "ok", outcome.detail
        assert console.commands == [
            "Delete Plugin 2",  # refused
            f"Import Plugin 3 '{_PATCH}' /nc",
            "Delete Plugin 2",  # retried from the alias — a different object
            f"Import Plugin 2 '{_PATCH}'",
            "Delete Plugin 3",
        ]
        assert console.invokers_of("Delete Plugin 2") == [_RESPONDER, f"{_PATCH}#2"]
        assert console.pool == {1: _RESPONDER, 2: _PATCH}
        assert "was refused" in outcome.detail

    def test_an_unconfirmed_delete_stops_instead_of_importing(self, tmp_path):
        # REQ-MVP-032: whether the delete landed is unknown, so importing now
        # would gamble on the pool's shape (and count as a retry of the effect).
        link, console = _pool_link(tmp_path, pool={1: _RESPONDER, 2: _PATCH})
        link._timeouts = _FAST  # noqa: SLF001
        console.silent = lambda invoker, command: command == "Delete Plugin 2"
        outcome = link.deploy_plugin(_PATCH, "return 2")
        assert outcome.status == "unconfirmed"
        assert console.commands == ["Delete Plugin 2"]
        assert [s.kind for s in outcome.sends] == ["state_query", "command"]
