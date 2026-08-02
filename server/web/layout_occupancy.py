"""Backward-compatible re-export (T-J).

The occupancy-fetch logic previously defined here now lives in
``server.orchestrator.layout_occupancy`` — see that module's docstring for
why (the executor-layout TOOL registered in ``server.orchestrator.tools``
needs the same check, and importing it back from ``server.web`` would invert
the established ``web -> orchestrator`` dependency direction). This module
keeps the original import path working for any existing or future web-layer
caller.
"""

from __future__ import annotations

from server.orchestrator.layout_occupancy import check_occupancy, fetch_executor_states

__all__ = ["check_occupancy", "fetch_executor_states"]
