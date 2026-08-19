"""Property reads through the chokepoint port (REQ-PRECHK-019).

Fixture addresses are NOT in the enumeration payload -- an object-tree snapshot
carries ``name``, ``class`` and ``i`` only, so the address lives exclusively in
the ``Patch`` property. That makes a property read the one unavoidable extra
capability of the pre-check, and it rides the same gate as every state read.

Read failures are CAPTURED, not raised. A single unreadable property must not
discard the readable ones: the inventory classifies read failures and reports
them (REQ-PRECHK-003), and a sweep that aborted on the first failure would turn
one bad property into a missing fixture.

BULK-FIRST (2026-08-19 latency measurement, ``server/audit_logs/probe-*.jsonl``).
One-property-per-round-trip was the second largest source of console traffic in
the measured day: 457,666 round trips at a p90 of 67.3 ms, of which one
``get_spatial_context`` call alone spent 240..420 round trips = 16..28 s of
wall clock. The responder has answered whole name lists since 1.6.0
(``console/lua/PROTOCOL.md`` §4.8) and the port, gate and audit wiring for it
already exist, so the sweep now asks once per object instead of once per name.
The single-read loop stays as the fallback -- see :func:`read_properties`.
"""

from __future__ import annotations

import contextlib
import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.orchestrator.ports import PropertyQueryPort

#: Names per bulk ``props`` request. Mirrors ``MAX_PROPS_NAMES``
#: (``server/bridge/protocol.py``), restated rather than imported because the
#: prechk package must not reach into ``server.bridge`` (AC-PRECHK-013 ①); a
#: test pins the two together so they cannot drift.
BULK_READ_CHUNK = 16

#: Ports whose bulk read proved unusable, held weakly so a port dying takes its
#: entry with it. The live console still runs responder 1.6.0, whose ``props``
#: is a paged variant with a different wire format, so the bulk attempt CAN
#: fail permanently -- and retrying it on every sweep would make the read
#: slower than the single-read loop it replaced. One failure that the single
#: reads then survive is enough to stop asking (see :func:`read_properties`).
_BULK_UNUSABLE: weakref.WeakSet = weakref.WeakSet()


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


def bulk_capable(port: object) -> bool:
    """Does this port still offer a bulk read we have not already given up on?

    Public because the round-trip BUDGET has to agree with the read path: a
    bulk-capable port spends ONE round trip per object regardless of how many
    property names are asked for, so a caller that budgets per-name would cap
    itself four to seven times too early (measured 2026-08-19 on an 80-fixture
    rig: the per-name budget stopped the spatial read at 60 fixtures and the
    console refused the whole request as incomplete).
    """
    if not callable(getattr(port, "query_properties", None)):
        return False
    try:
        return port not in _BULK_UNUSABLE
    except TypeError:  # unhashable port -- never remembered, so never disabled
        return True


def _single_read(port: PropertyQueryPort, path: str, name: str) -> PropertyRead:
    """One ``prop`` round trip -> one :class:`PropertyRead`, failures captured."""
    try:
        payload = port.query_property(path, name)
    except Exception as error:  # the port raises on failure AND on timeout
        return PropertyRead(name=name, ok=False, error=str(error))
    if not isinstance(payload, Mapping) or not payload.get("ok"):
        detail = f"property query failed: {path} {name}"
        if isinstance(payload, Mapping):
            detail = str(payload.get("error") or detail)
        return PropertyRead(name=name, ok=False, error=detail)
    value = payload.get("value")
    return PropertyRead(name=name, ok=True, value=value if isinstance(value, str) else str(value))


# @MX:ANCHOR: [AUTO] the bulk reply is TRUSTED ONLY when it is fully well formed.
# @MX:REASON: The live console runs responder 1.6.0, whose ``props`` is a paged
#   variant with a different wire format. A half-understood reply is the one
#   outcome worse than a slow read: it would classify names the console never
#   answered for, and "0 read failures" would become true for free. Anything
#   this function cannot map name-for-name comes back as ``None`` so the caller
#   re-reads it singly.
def _bulk_chunk(
    port: object, path: str, chunk: Sequence[str]
) -> dict[str, PropertyRead | None] | None:
    """One ``props`` round trip for up to :data:`BULK_READ_CHUNK` names.

    Returns ``None`` when the reply is unusable as a whole (exception, timeout,
    top-level failure, or a shape this code cannot read) -- the caller then
    falls back to the single-read loop for every name in ``chunk``. Otherwise
    returns one entry per requested name, where a ``None`` entry means "this
    one name needs a single re-read" (the responder shortened its value, or
    dropped it to fit the payload budget).
    """
    try:
        payload = port.query_properties(path, tuple(chunk))  # type: ignore[attr-defined]
    except Exception:  # unsupported verb, wire mismatch, or timeout -- all fall back
        return None
    if not isinstance(payload, Mapping) or not payload.get("ok"):
        return None
    items = payload.get("reads")
    if not isinstance(items, (list, tuple)):
        return None
    by_name: dict[str, Mapping] = {}
    for item in items:
        if not isinstance(item, Mapping):
            return None
        name = item.get("n")
        # Duplicate request names collapse to their first occurrence on the
        # responder side too (PROTOCOL.md §4.8), so a repeat here is a reply
        # shape we do not recognise -- keep the first and let the mismatch
        # surface through the name sweep below.
        if isinstance(name, str) and name not in by_name:
            by_name[name] = item
    # Trailing entries dropped to fit ``CONFIG.max_payload`` are LEGITIMATE and
    # signalled top-level; missing names WITHOUT that signal are a format the
    # caller must not trust.
    truncated_list = bool(payload.get("truncated"))
    out: dict[str, PropertyRead | None] = {}
    for name in chunk:
        item = by_name.get(name)
        if item is None:
            if not truncated_list:
                return None
            out[name] = None
            continue
        if not item.get("ok"):
            detail = str(item.get("e") or f"property query failed: {path} {name}")
            out[name] = PropertyRead(name=name, ok=False, error=detail)
            continue
        # An item-level ``truncated`` means the responder SHORTENED the value
        # past ``CONFIG.max_prop_value`` (§4.8). The single-read ``prop`` verb
        # does not shorten (§4.6), so re-reading is the only way to keep the
        # value the caller would have got before bulking.
        value = item.get("v")
        if item.get("truncated") or value is None:
            out[name] = None
            continue
        out[name] = PropertyRead(
            name=name, ok=True, value=value if isinstance(value, str) else str(value)
        )
    return out


def read_properties(
    port: PropertyQueryPort, path: str, names: Sequence[str]
) -> dict[str, PropertyRead]:
    """Read ``names`` off ``path`` in ONE port call when the port can bulk-read.

    A port carrying ``query_properties``
    (:class:`~server.orchestrator.ports.BulkPropertyQueryPort`) is asked once
    per :data:`BULK_READ_CHUNK` names; anything else -- and anything the bulk
    reply cannot answer for -- falls back to the historical one-call-per-name
    loop. The fallback is SILENT by contract: a console that cannot bulk-read
    must still produce the same reads, so no bulk failure is ever propagated.

    Observable semantics are unchanged either way: order is preserved,
    duplicates collapse to a single read, an individual read failure is
    captured rather than raised, and an empty name list raises ``ValueError``
    because an empty result would make every downstream "no read failures"
    assertion true for free.
    """
    wanted = list(dict.fromkeys(names))
    if not wanted:
        raise ValueError("read_properties requires at least one property name")

    reads: dict[str, PropertyRead] = {}
    pending: list[str] = []
    unanswered: list[str] = []  # names the BULK CALL itself could not cover
    if bulk_capable(port):
        for start in range(0, len(wanted), BULK_READ_CHUNK):
            chunk = wanted[start : start + BULK_READ_CHUNK]
            answered = _bulk_chunk(port, path, chunk)
            if answered is None:
                unanswered.extend(chunk)
                pending.extend(chunk)
                continue
            for name in chunk:
                read = answered[name]
                if read is None:
                    pending.append(name)
                else:
                    reads[name] = read
    else:
        pending = list(wanted)

    for name in pending:
        reads[name] = _single_read(port, path, name)

    # @MX:ANCHOR: [AUTO] the one-shot switch, and why it needs the single reads.
    # @MX:REASON: "Bulk failed" alone does not mean the port cannot bulk-read --
    #   an unresolvable path fails every verb. Only a bulk failure that the
    #   SINGLE reads then survived says the capability is missing, and that is
    #   the case where retrying bulk costs a wasted round trip on every sweep
    #   for the rest of the session.
    if unanswered and any(reads[name].ok for name in unanswered):
        # A port that cannot be weak-referenced is simply never remembered.
        with contextlib.suppress(TypeError):
            _BULK_UNUSABLE.add(port)

    return {name: reads[name] for name in wanted}
