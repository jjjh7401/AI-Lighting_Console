"""Last-created-look session tracking (REQ-DEPLOY-030 / AC-DEPLOY-021, #4).

A pure, snapshot-only parser that reads the just-created sequence and its
executor out of one turn's executed command strings, so the chat session can
inject that target identity into the NEXT turn's conversation. Without it, a
bare follow-up modification ("더 느리게" / make it slower) gives the model no
anchor and it guesses an arbitrary target (Seq 1 / Exec 1) instead of the look
it just built (Seq 71 / Exec 201).

The parser recognizes exactly two creation shapes (grandMA3 v2.4.2 grammar):

- ``Store Sequence <n>``            — creates/records a sequence
- ``Assign Sequence <n> At Executor <m>`` — binds a sequence to an executor
  (this is also the form Lua-plugin-built sequences emit, e.g.
  ``Assign Sequence 16 At Executor 193``).

It is snapshot-only: :func:`parse_last_created` returns the SINGLE most-recent
look, never an accumulating history.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Keywords are case-insensitive in MA3; the parser anchors at the verb so a
# sequence named inside a modifier (e.g. "Store Cue 1 Sequence 71") is NOT read
# as a "Store Sequence" creation.
_STORE_SEQUENCE = re.compile(r"^\s*Store\s+Sequence\s+(\d+)\b", re.IGNORECASE)
_ASSIGN_SEQ_EXEC = re.compile(
    r"^\s*Assign\s+Sequence\s+(\d+)\s+At\s+Executor\s+(\d+)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class LastCreated:
    """The most-recently-created look's target identity (both fields optional)."""

    sequence: int | None = None
    executor: int | None = None


# @MX:NOTE: [AUTO] snapshot-only parser (REQ-DEPLOY-030) — returns the single
#   most-recent look, never a history; the session keeps only this one value
def parse_last_created(commands: Iterable[str]) -> LastCreated | None:
    """Extract the last-created sequence + executor from executed commands.

    Returns ``None`` when no sequence-creation command is present. A new
    ``Store Sequence`` supersedes the prior look and clears the prior executor
    (an executor belongs to the sequence its ``Assign`` named, so it must not
    leak onto a newer sequence).
    """
    sequence: int | None = None
    executor: int | None = None
    for command in commands:
        assign = _ASSIGN_SEQ_EXEC.match(command)
        if assign is not None:
            sequence = int(assign.group(1))
            executor = int(assign.group(2))
            continue
        store = _STORE_SEQUENCE.match(command)
        if store is not None:
            seq = int(store.group(1))
            if seq != sequence:
                executor = None  # a newer sequence has no executor yet
            sequence = seq
    if sequence is None:
        return None
    return LastCreated(sequence=sequence, executor=executor)
