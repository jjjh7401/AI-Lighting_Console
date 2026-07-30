"""Property reads through the chokepoint port (REQ-PRECHK-019).

Fixture addresses are NOT in the enumeration payload -- an object-tree snapshot
carries ``name``, ``class`` and ``i`` only, so the address lives exclusively in
the ``Patch`` property. That makes a property read the one unavoidable extra
capability of the pre-check, and it rides the same gate as every state read.

Read failures are CAPTURED, not raised. A single unreadable property must not
discard the readable ones: the inventory classifies read failures and reports
them (REQ-PRECHK-003), and a sweep that aborted on the first failure would turn
one bad property into a missing fixture.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.orchestrator.ports import PropertyQueryPort


@dataclass(frozen=True, slots=True)
class PropertyRead:
    """One property read attempt: the raw value, or why it is unavailable.

    ``value`` is the responder's string form and is deliberately UNVALIDATED
    here -- shape checking belongs to the inventory, which knows which shapes
    each property may take. ``ok`` means "the console answered with a value",
    not "the value is usable".
    """

    name: str
    ok: bool
    value: str | None = None
    error: str | None = None


def read_properties(
    port: PropertyQueryPort, path: str, names: Sequence[str]
) -> dict[str, PropertyRead]:
    """Read ``names`` off ``path``, one port call per distinct name.

    Order is preserved and duplicates collapse to a single call. Raises
    ``ValueError`` on an empty name list: an empty result would make every
    downstream "no read failures" assertion true for free.
    """
    wanted = list(dict.fromkeys(names))
    if not wanted:
        raise ValueError("read_properties requires at least one property name")
    reads: dict[str, PropertyRead] = {}
    for name in wanted:
        try:
            payload = port.query_property(path, name)
        except Exception as error:  # the port raises on failure AND on timeout
            reads[name] = PropertyRead(name=name, ok=False, error=str(error))
            continue
        if not payload.get("ok"):
            detail = str(payload.get("error") or f"property query failed: {path} {name}")
            reads[name] = PropertyRead(name=name, ok=False, error=detail)
            continue
        value = payload.get("value")
        reads[name] = PropertyRead(
            name=name, ok=True, value=value if isinstance(value, str) else str(value)
        )
    return reads
