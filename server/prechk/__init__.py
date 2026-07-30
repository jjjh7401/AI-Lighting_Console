"""Rig pre-check: fixture inventory, patch consistency, response macros.

This package is a PURE consumer of the orchestrator ports. It never imports
``server.bridge``: property and snapshot reads arrive through the gate-owned
ports (REQ-PRECHK-019), and commands are executed by the existing single
execution path (REQ-PRECHK-018). ``server/tests/test_architecture.py`` and
``server/tests/test_prechk_inventory.py`` both enforce that boundary.
"""

from __future__ import annotations

from server.prechk.query import PropertyRead, read_properties

__all__ = ["PropertyRead", "read_properties"]
