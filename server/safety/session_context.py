"""Per-instruction-turn session identity (M6c-1 — cross-session isolation seam).

Concurrent ``ChatSession`` connections share ONE ``SafetyGate`` and ONE
``ApprovalChannel`` instance by design (``server/web/app.py`` composes
``WebDeps`` once, before any WebSocket connects — REQ-MVP-014/016 do not
require a distinct object graph per connection). Without a way to say "this
particular ``screen()``/``request_approval()`` call belongs to session X",
those two shared instances have nowhere to scope per-caller state (clearance
tokens, pending approvals), and one session's activity can leak into
another's — a disconnecting session denying an unrelated session's pending
approval, or a screening call invalidating another session's clearances.

This module is that seam: a ``contextvars.ContextVar`` set once at the top of
``ChatSession.run_instruction`` (a plain synchronous call — no thread/task
boundary is crossed between the set and the nested ``gate.screen()`` /
``approval_port.request_approval()`` calls it makes on the SAME thread), read
by :class:`server.safety.gate.SafetyGate` and
:class:`server.web.approval_bridge.ApprovalChannel` to key their internal
per-session state. Callers outside any bound session context (direct unit
tests exercising the gate/channel standalone) all see the same
``DEFAULT_SESSION_KEY``, preserving single-session semantics exactly as
before this change.
"""

from __future__ import annotations

import itertools
from contextvars import ContextVar, Token
from typing import NewType

SessionKey = NewType("SessionKey", object)

# The implicit key every un-scoped caller shares (no ChatSession in play) —
# keeps direct gate/channel unit tests behaving exactly as before this change.
DEFAULT_SESSION_KEY: SessionKey = SessionKey("_default_session_")

_counter = itertools.count(1)
_current: ContextVar[SessionKey] = ContextVar("current_session_key", default=DEFAULT_SESSION_KEY)


def new_session_key() -> SessionKey:
    """A fresh, process-unique identity token for one ``ChatSession``."""
    return SessionKey(next(_counter))


def bind_session_key(key: SessionKey) -> Token:
    """Make ``key`` the current session for this context; returns the reset Token."""
    return _current.set(key)


def reset_session_key(token: Token) -> None:
    _current.reset(token)


def current_session_key() -> SessionKey:
    """The active session key (``DEFAULT_SESSION_KEY`` outside any bound turn)."""
    return _current.get()
