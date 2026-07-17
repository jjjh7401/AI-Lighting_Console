"""Destructive-content scan — best-effort ``Cmd()`` analysis (M7, REQ-MVP-027).

Extracts the string-literal argument of every ``Cmd(...)`` call (including the
Lua call-sugar forms ``Cmd"..."`` / ``Cmd'...'`` / ``Cmd[[...]]``) from a
submitted Lua source and classifies each extracted command line through the
SAME closed-set semantics the gate uses — :func:`server.safety.grammar.validate`
+ :func:`server.safety.classify.classify_command` (one matching semantics;
abbreviation-aware, quoted-object-name safe).

RESIDUAL RISK (normative, REQ-MVP-027): this static scan is a BEST-EFFORT
reviewer-assist signal. Dynamically assembled Lua strings (concatenation,
``string.format``, variables) evade literal extraction — such calls are
surfaced as ``dynamic_calls`` so the reviewer sees that unverifiable command
construction exists, but the HUMAN REVIEW GATE remains the authoritative
control. Scan false positives (e.g. commented-out code is still scanned) are
acceptable; they only err in the safe direction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import SafetyRuleset

BEST_EFFORT_CAVEAT = (
    "static Cmd() scan is a best-effort reviewer-assist signal — dynamically "
    "assembled Lua strings can evade it; the human review gate remains the "
    "authoritative control (REQ-MVP-027)"
)

# A global-style Cmd call head: `Cmd(`, `Cmd"`, `Cmd'`, `Cmd[[` / `Cmd[=[`.
# The lookbehind rejects identifier tails (`MyCmd(`), while `M.Cmd(` /
# `obj:Cmd(` still match — over-matching is FP-safe.
_CMD_HEAD = re.compile(r"(?<![A-Za-z0-9_])Cmd\s*(\(|\"|'|\[=*\[)")

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v"}

# Lua's own whitespace set (space, tab, newline, CR, vertical tab, form feed).
# M6c-2 Finding 2: the gap/tail checks below previously allowed only space/tab,
# so a `Cmd(\n"Delete ..."\n)` (or a `..`-concatenation split across a line
# break) evaded classification entirely. Both checks must accept the SAME
# whitespace Lua itself accepts between/after the `Cmd(` argument.
_LUA_WHITESPACE = " \t\n\r\v\f"


@dataclass(frozen=True)
class ScanFinding:
    """One classified Cmd() literal the reviewer must see."""

    line: int
    command: str
    kind: str  # "blacklisted" | "invoking" | "unparseable"
    matched_entry: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DynamicCall:
    """One Cmd() call whose argument is not a plain string literal."""

    line: int
    snippet: str


@dataclass(frozen=True)
class ScanReport:
    """The deploy-time scan verdict shown to the reviewer (REQ-MVP-027)."""

    destructive: bool
    findings: tuple[ScanFinding, ...] = ()
    dynamic_calls: tuple[DynamicCall, ...] = ()
    caveat: str = field(default=BEST_EFFORT_CAVEAT)


def _line_of(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def _line_snippet(source: str, index: int, *, limit: int = 80) -> str:
    start = source.rfind("\n", 0, index) + 1
    end = source.find("\n", index)
    if end == -1:
        end = len(source)
    return source[start:end].strip()[:limit]


def _parse_short_string(source: str, i: int, quote: str) -> tuple[str | None, int]:
    """Parse a Lua short string starting at the opening quote; (text, next_i)."""
    j = i + 1
    parts: list[str] = []
    while j < len(source):
        ch = source[j]
        if ch == "\\":
            j += 1
            if j >= len(source):
                return None, j
            parts.append(_ESCAPES.get(source[j], source[j]))
            j += 1
        elif ch == quote:
            return "".join(parts), j + 1
        elif ch == "\n":
            return None, j  # unterminated short string (Lua would reject it)
        else:
            parts.append(ch)
            j += 1
    return None, j


def _parse_long_string(source: str, i: int) -> tuple[str | None, int]:
    """Parse a Lua long string ``[=*[...]=*]`` starting at the first ``[``."""
    match = re.match(r"\[(=*)\[", source[i:])
    if match is None:
        return None, i
    closer = f"]{match.group(1)}]"
    start = i + match.end()
    end = source.find(closer, start)
    if end == -1:
        return None, len(source)
    text = source[start:end]
    if text.startswith("\n"):  # Lua drops a leading newline in long strings
        text = text[1:]
    return text, end + len(closer)


def _classify_literal(command: str, line: int, ruleset: SafetyRuleset) -> ScanFinding | None:
    grammar = validate(command)
    if not grammar.ok:
        return ScanFinding(
            line=line,
            command=command,
            kind="unparseable",
            matched_entry=None,
            reasons=(f"unparseable Cmd() argument: {grammar.reason}",),
        )
    verdict = classify_command(grammar.parsed, ruleset)
    if verdict.category == "blacklisted":
        return ScanFinding(
            line=line,
            command=command,
            kind="blacklisted",
            matched_entry=verdict.matched_entry,
            reasons=verdict.reasons,
        )
    if verdict.category == "invoking":
        return ScanFinding(
            line=line,
            command=command,
            kind="invoking",
            matched_entry=None,
            reasons=(
                "indirect invocation cannot be verified at deploy time "
                "(the invocation-time expand-or-hold gate covers execution)",
            )
            + verdict.reasons,
        )
    return None


# @MX:NOTE: [AUTO] deploy-time scan reuses the gate's ONE matching semantics
#   (grammar.validate + classify_command) — REQ-MVP-013/027 closed-set fidelity
def scan_lua_source(source: str, ruleset: SafetyRuleset) -> ScanReport:
    """Scan one Lua source for blacklisted ``Cmd()`` literals (REQ-MVP-027)."""
    findings: list[ScanFinding] = []
    dynamic: list[DynamicCall] = []
    for head in _CMD_HEAD.finditer(source):
        line = _line_of(source, head.start())
        opener = head.group(1)
        literal: str | None
        after: int
        if opener == "(":
            i = head.end()
            while i < len(source) and source[i] in _LUA_WHITESPACE:
                i += 1
            ch = source[i : i + 1]
            if ch in ('"', "'"):
                literal, after = _parse_short_string(source, i, ch)
            elif ch == "[" and re.match(r"\[=*\[", source[i:]):
                literal, after = _parse_long_string(source, i)
            else:
                dynamic.append(DynamicCall(line=line, snippet=_line_snippet(source, head.start())))
                continue
        elif opener in ('"', "'"):
            literal, after = _parse_short_string(source, head.end() - 1, opener)
        else:  # long-bracket call sugar
            literal, after = _parse_long_string(source, head.end() - len(opener))
        if literal is None:
            dynamic.append(DynamicCall(line=line, snippet=_line_snippet(source, head.start())))
            continue
        # A concatenated tail (`.. expr`) means the FULL command is dynamic;
        # the literal prefix is still classified (best-effort hardening).
        tail = source[after:].lstrip(_LUA_WHITESPACE)
        if tail.startswith(".."):
            dynamic.append(DynamicCall(line=line, snippet=_line_snippet(source, head.start())))
            literal = literal.strip()
            if not literal:
                continue
        finding = _classify_literal(literal, line, ruleset)
        if finding is not None:
            findings.append(finding)
    destructive = any(f.kind == "blacklisted" for f in findings)
    return ScanReport(
        destructive=destructive,
        findings=tuple(findings),
        dynamic_calls=tuple(dynamic),
    )
