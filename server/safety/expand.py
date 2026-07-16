"""Expand-or-hold — indirect-invocation bypass closure (REQ-MVP-026).

A reference-invoking command's target body is fetched (production: the M2
state path behind :class:`BodyFetcher`) and every body line is classified;
nested invocations recurse. The command is HELD for human approval when the
body contains a blacklisted command (risky), OR when it cannot be verified:
body unavailable, unrecognizable reference, unparseable body line, recursion
depth beyond 3, or a reference cycle. Pure logic — the only I/O lives behind
the injectable fetcher, keeping the FN corpus fully deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.registry import PluginFlagRegistry
from server.safety.ruleset import SafetyRuleset

# REQ-MVP-026: body expansion recursion is capped at 3 levels.
MAX_EXPANSION_DEPTH = 3


class BodyUnavailable(Exception):
    """Raised by a fetcher when a reference body cannot be retrieved."""


class BodyFetcher(Protocol):
    """Returns the command lines making up one referenced object's body."""

    def fetch_body(self, reference: str) -> Sequence[str]:
        """Fetch body lines for e.g. ``"Macro 5"``; raises BodyUnavailable."""
        ...


@dataclass(frozen=True)
class ExpansionResult:
    """Expand-or-hold verdict for one reference."""

    hold: bool
    risky: bool = False
    reasons: tuple[str, ...] = ()


def _hold(reason: str, *, risky: bool = False) -> ExpansionResult:
    return ExpansionResult(hold=True, risky=risky, reasons=(reason,))


def evaluate_reference(
    reference: str | None,
    *,
    ruleset: SafetyRuleset,
    fetcher: BodyFetcher,
    plugin_registry: PluginFlagRegistry | None = None,
    max_depth: int = MAX_EXPANSION_DEPTH,
) -> ExpansionResult:
    """Expand one invoking-command reference, or hold it (REQ-MVP-026)."""
    return _evaluate(
        reference,
        ruleset=ruleset,
        fetcher=fetcher,
        registry=plugin_registry,
        max_depth=max_depth,
        depth=1,
        visited=frozenset(),
    )


def _evaluate(
    reference: str | None,
    *,
    ruleset: SafetyRuleset,
    fetcher: BodyFetcher,
    registry: PluginFlagRegistry | None,
    max_depth: int,
    depth: int,
    visited: frozenset[str],
) -> ExpansionResult:
    if reference is None:
        return _hold("unverifiable reference: no recognizable target object")
    key = reference.lower()
    if key in visited:
        return _hold(f"reference cycle detected at {reference!r}")
    if depth > max_depth:
        return _hold(f"expansion depth {depth} exceeds the limit of {max_depth}")
    if registry is not None and key.startswith("plugin "):
        flag = registry.lookup(reference)
        if flag is not None:
            if flag.destructive:
                return _hold(
                    f"destructive-flagged plugin {reference!r} — human approval "
                    "required on every invocation",
                    risky=True,
                )
            return ExpansionResult(
                hold=False, reasons=(f"registered non-destructive plugin {reference!r}",)
            )
    try:
        body = fetcher.fetch_body(reference)
    except BodyUnavailable as error:
        return _hold(f"unverifiable reference {reference!r}: {error}")
    visited = visited | {key}
    for line in body:
        grammar = validate(line)
        if not grammar.ok:
            return _hold(f"unverifiable body line in {reference!r}: {grammar.reason}")
        finding = classify_command(grammar.parsed, ruleset)
        if finding.category == "blacklisted":
            return _hold(f"body of {reference!r} contains blacklisted command {line!r}", risky=True)
        if finding.category == "invoking":
            nested = _evaluate(
                finding.reference,
                ruleset=ruleset,
                fetcher=fetcher,
                registry=registry,
                max_depth=max_depth,
                depth=depth + 1,
                visited=visited,
            )
            if nested.hold:
                return nested
    return ExpansionResult(hold=False)
