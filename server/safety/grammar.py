"""Grammar validator — gate stage ① (REQ-MVP-011/012).

Validation depth (plan.md §A-6, finalized here): STRUCTURAL parsing — one
command line is tokenized with quote balancing, and the leading token must be
verb-shaped. This is deliberately NOT a full MA3 grammar: stage ① exists to
(a) reject unparseable lines deterministically and (b) hand a verb/args token
stream to the stage-② risk classifier. Grammar QUALITY (error rate < 5%) is
measured at M6 against the console itself; gate SAFETY does not depend on full
parsing. Over-blocking is acceptable (safety asymmetry) — a rejected line's
reason feeds the self-correction loop (REQ-MVP-012).

Pure module: no I/O, fully deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_VERB_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]*$")
_QUOTES = ("'", '"')


@dataclass(frozen=True)
class Token:
    """One command-line token; quoted tokens carry their unquoted text."""

    text: str
    quoted: bool = False


@dataclass(frozen=True)
class ParsedCommand:
    """A structurally valid command line: leading verb + argument tokens."""

    raw: str
    verb: str
    args: tuple[Token, ...]


@dataclass(frozen=True)
class GrammarResult:
    """Validation outcome: parsed tokens on success, a block reason otherwise."""

    ok: bool
    parsed: ParsedCommand | None = None
    reason: str = ""


class _TokenizeError(ValueError):
    pass


def _tokenize(line: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    length = len(line)
    while i < length:
        ch = line[i]
        if ch.isspace():
            i += 1
            continue
        if ch in _QUOTES:
            closing = line.find(ch, i + 1)
            if closing == -1:
                raise _TokenizeError(f"unbalanced quote starting at column {i + 1}")
            if closing + 1 < length and not line[closing + 1].isspace():
                raise _TokenizeError(f"misplaced quote at column {closing + 1}")
            tokens.append(Token(text=line[i + 1 : closing], quoted=True))
            i = closing + 1
        else:
            start = i
            while i < length and not line[i].isspace():
                if line[i] in _QUOTES:
                    raise _TokenizeError(f"misplaced quote inside token at column {i + 1}")
                i += 1
            tokens.append(Token(text=line[start:i], quoted=False))
    return tokens


def validate(line: str) -> GrammarResult:
    """Validate ONE command line structurally; never raises."""
    if not line or not line.strip():
        return GrammarResult(ok=False, reason="empty command line")
    if "\n" in line or "\r" in line:
        return GrammarResult(ok=False, reason="command must be a single line")
    for ch in line:
        if ord(ch) < 32:
            return GrammarResult(ok=False, reason="command contains a control character")
    try:
        tokens = _tokenize(line)
    except _TokenizeError as error:
        return GrammarResult(ok=False, reason=str(error))
    if not tokens:
        return GrammarResult(ok=False, reason="empty command line")
    head = tokens[0]
    if head.quoted or not _VERB_SHAPE.match(head.text):
        return GrammarResult(
            ok=False,
            reason=f"command must begin with a keyword verb, got {head.text!r}",
        )
    return GrammarResult(
        ok=True,
        parsed=ParsedCommand(raw=line, verb=head.text, args=tuple(tokens[1:])),
    )
