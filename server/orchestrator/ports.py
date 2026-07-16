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

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExecutionResult:
    """The confirmed outcome of one command execution attempt."""

    ok: bool
    detail: str = ""


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
