"""Human approval channel (gate stage ③ — REQ-MVP-013/014/021 seed).

Approval arrives through a port interface: Milestone M5 wires the real
WebSocket approval UI (blocking on the human decision); tests use in-memory
scripted ports. The DEFAULT port denies everything — without an approval
channel nothing risky can run (fail-safe; REQ-MVP-014: no exception via ANY
route). Each request carries the command text plus its risk reasons and
warnings, which is the data the M5 UI renders (AC-MVP-021).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ApprovalItem:
    """One held command with the reasons/warnings the approver must see."""

    command: str
    risk_reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApprovalRequest:
    """One all-or-nothing bundle approval request (REQ-MVP-015)."""

    items: tuple[ApprovalItem, ...]

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(item.command for item in self.items)


class ApprovalPort(Protocol):
    """Blocking human approval channel (M5 wires the WebSocket UI)."""

    def request_approval(self, request: ApprovalRequest) -> bool:
        """Return True only when the human approved the WHOLE bundle."""
        ...


class DenyAllApprovalPort:
    """Fail-safe default: no approval channel -> nothing risky executes."""

    def request_approval(self, request: ApprovalRequest) -> bool:
        return False
