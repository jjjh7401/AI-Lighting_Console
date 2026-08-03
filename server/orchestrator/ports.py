"""Execution/state ports — the orchestrator's ONLY route toward the console.

Chokepoint forward design (REQ-MVP-029): the safety gate (Milestone M4) will be
the SOLE production implementation of :class:`CommandExecutionPort`, wired to
the OSC bridge behind gate checks. The orchestrator and its tools depend only
on these narrow protocols and MUST NOT import ``server.bridge`` — the
AC-MVP-019 import-boundary architecture test (M4/M6) pins that contract, and a
test in ``test_tools.py`` already scans this package for bridge imports.

State queries follow the same discipline: they ride the M2 protocol layer
(``Plugin "CopilotResponder" "state <id> <path>"`` over ``/copilot/cmd``, reply
on ``/copilot/state``) through the gate-owned port implementation, never raw
bridge calls from tool code.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExecutionResult:
    """The confirmed outcome of one command execution attempt."""

    ok: bool
    detail: str = ""


class GateCommandDecision(Protocol):
    """Per-command screening verdict (shape of the M4 gate's decision rows)."""

    command: str
    status: str
    reasons: tuple[str, ...]


class GateScreenDecision(Protocol):
    """Bundle screening outcome (shape of the M4 gate's ScreenDecision)."""

    cleared: bool
    status: str
    commands: tuple[GateCommandDecision, ...]
    notice: str


# @MX:NOTE: [AUTO] bundle-level gate hook (REQ-MVP-011/015) — run_commands screens
#   the WHOLE bundle here before any per-command port execution starts
class BundleGate(Protocol):
    """Bundle-level safety screening — implemented by the M4 safety gate."""

    def screen(self, commands: Sequence[str]) -> GateScreenDecision:
        """Screen one command bundle; a non-cleared decision means zero sends."""
        ...


# @MX:NOTE: [AUTO] chokepoint port (REQ-MVP-029 forward design) — the M4 safety gate
#   is the only planned production implementation; M3 tests use in-memory fakes
class CommandExecutionPort(Protocol):
    """Executes ONE gate-approved MA3 command line and reports its outcome."""

    def execute(self, command: str) -> ExecutionResult:
        """Execute one command line; blocks until the result is confirmed."""
        ...


class StateQueryPort(Protocol):
    """Returns the decoded object-tree snapshot payload for one path (REQ-MVP-003)."""

    def query_state(self, path: str) -> dict:
        """Query one object-tree path; raises on failure/timeout."""
        ...


class PropertyQueryPort(Protocol):
    """Returns the decoded property payload for one object path (REQ-PRECHK-019).

    Separate from :class:`StateQueryPort` because a snapshot and a property read
    are different requests: enumeration carries ``name``/``class``/``i`` only,
    so fixture addresses are reachable ONLY through a property read. The gate
    implements both on one object; keeping the protocols apart lets a consumer
    declare exactly the capability it needs.
    """

    def query_property(self, path: str, property_name: str) -> dict:
        """Read one property of one object; raises on failure/timeout."""
        ...


class FieldEnumerationPort(Protocol):
    """Returns field names/types for one object path (REQ-INTROSPECT-017/024).

    Same narrow-port precedent as :class:`PropertyQueryPort`: enumeration and
    reads are different capabilities, so a consumer declares only the ability it
    needs while staying behind the gate-owned console path.
    """

    def enumerate_fields(self, path: str) -> dict:
        """Enumerate readable field names/types for one object; raises on failure/timeout."""
        ...


class BulkPropertyQueryPort(Protocol):
    """Returns named property reads for one object path (REQ-INTROSPECT-018/024).

    Split from :class:`FieldEnumerationPort` for the same reason
    :class:`PropertyQueryPort` is split from :class:`StateQueryPort`: listing
    names and reading values are distinct console abilities, and consumers may
    need one without the other.
    """

    def query_properties(self, path: str, property_names: Sequence[str]) -> dict:
        """Read named properties of one object; raises on failure/timeout."""
        ...
