"""Live occupancy fetch for the executor layout planner (T-F/T-J, task item 4).

Thin impure wrapper: performs the actual ``"Executor <n>"`` state queries
(``server/looks/layout.py`` cannot do this itself — it is a look-layer module
and ``server/tests/test_looks_boundary.py`` forbids any look module from
naming ``server.orchestrator.ports`` at all), then hands the plain-dict
results to :func:`server.looks.layout.mark_occupancy_conflicts`, the pure
function that actually decides what counts as a conflict.

Colocated in ``server.orchestrator`` rather than ``server.web`` (where it
first lived): ``server/web`` already imports ``server.orchestrator.tools``
extensively (``dash.py``, ``session.py``, ``panel.py``, ``cue_monitor.py``),
so the T-J executor-layout TOOL — which lives in ``server.orchestrator.tools``
and needs this exact occupancy check — importing it back from
``server.web.layout_occupancy`` would invert that established dependency
direction (``orchestrator -> web -> orchestrator``). Moving the impure logic
here keeps the edge one-way; ``server/web/layout_occupancy.py`` now re-exports
these two names unchanged for any existing or future web-layer caller.

Same read shape as ``server/web/dash.py::_confirm_executor_no`` and
``server/web/cue_monitor.py::build_executor_cue_progress`` (query
``"Executor <n>"``, read ``node.sequenceNo``) — this module is the layout
planner's twin of those two, not a new console-query pattern.

Chokepoint discipline (unchanged): this module holds no execution surface of
its own and never imports the OSC send surface — it only queries state and
never sends a command.
"""

from __future__ import annotations

from collections.abc import Iterable

from server.looks.layout import LayoutPlan, mark_occupancy_conflicts
from server.orchestrator.ports import StateQueryPort


def _executor_ref(console_no: int) -> str:
    return f"Executor {console_no}"


def fetch_executor_states(
    state_port: StateQueryPort, executor_nos: Iterable[int]
) -> dict[int, dict]:
    """One ``"Executor <n>"`` state-query payload per requested number.

    A failed query is DROPPED rather than substituted with a guess — the
    caller (``check_occupancy``) then sees that number missing from the
    result, and ``mark_occupancy_conflicts`` treats a missing entry as
    ``UNCONFIRMED`` (a conflict), never as confirmed-empty.
    """
    states: dict[int, dict] = {}
    for console_no in executor_nos:
        try:
            states[console_no] = state_port.query_state(_executor_ref(console_no))
        except Exception:
            continue
    return states


def check_occupancy(state_port: StateQueryPort, plan: LayoutPlan) -> LayoutPlan:
    """Query every target executor in ``plan`` and mark conflicts (task item 4)."""
    executor_nos = {item.executor_no for item in plan.items}
    states = fetch_executor_states(state_port, executor_nos)
    return mark_occupancy_conflicts(plan, states)


__all__ = ["check_occupancy", "fetch_executor_states"]
