"""Deployed-plugin flag registry — invocation-gate half of AC-MVP-018.

Milestone M7 (deploy gate: pcall compile + destructive ``Cmd()`` scan + human
review) populates this registry at deployment time; M4 consumes it at
INVOCATION time: a destructive-flagged plugin call is held for human approval
on every invocation (REQ-MVP-028), a registered non-destructive plugin passes
(audited), and an UNREGISTERED plugin falls back to expand-or-hold.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PluginFlag:
    """Deploy-time verdict for one plugin reference."""

    reference: str
    destructive: bool


class PluginFlagRegistry:
    """In-memory plugin flag store (M7 wires deploy-time population)."""

    def __init__(self) -> None:
        self._flags: dict[str, PluginFlag] = {}

    def register(self, reference: str, *, destructive: bool) -> None:
        """Record the deploy-time scan verdict for one plugin reference."""
        self._flags[reference.lower()] = PluginFlag(reference=reference, destructive=destructive)

    def lookup(self, reference: str) -> PluginFlag | None:
        """Return the flag for a reference, or None when unregistered."""
        return self._flags.get(reference.lower())
