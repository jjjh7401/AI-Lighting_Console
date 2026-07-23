"""Risk classification — gate stage ② (REQ-MVP-013/026/036b). Pure module.

Classification is command-SYNTAX based: keywords are matched against unquoted
tokens only, so a blacklist keyword inside a quoted object name never matches
(acceptance edge case). Matching is abbreviation-aware in the FP-safe
direction — MA3 accepts abbreviated keywords (``Del`` for ``Delete``), so an
unquoted token matches a keyword when it equals it case-insensitively OR is a
>=3-character prefix of it (options abbreviate from 1 character). Over-matching
is resolved by human approval; under-matching would be a safety false negative.

EXCEPTION (M6c-2 Finding 1, REQ-MVP-013): a macro line's command TEXT is itself
persisted as a quoted PROPERTY VALUE (M6b-1r2 rulebook recipe — ``Set Macro
<pool>.<line> Property 'Command'/'Cmd' '<command text>'``). The general
"quoted tokens never match keywords" rule above protects quoted OBJECT NAMES
from false-positive keyword matching; it must NOT also shield an executable
command line merely because MA3's macro-authoring syntax happens to carry it
inside a quoted property value. :func:`classify_command` therefore recurses
the SAME classification into that quoted value when the narrow
``Property 'Command'/'Cmd' '<value>'`` shape is detected — see
:func:`_quoted_property_command_value`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.safety.grammar import ParsedCommand, Token, validate
from server.safety.ruleset import SafetyRuleset

# Object types whose references the expand-or-hold path can resolve to bodies.
# Invoking commands targeting anything else are UNVERIFIABLE -> held (FP-safe).
# @MX:NOTE: [AUTO] SPEC-COPILOT-EXECREF-001 M1 (v0.2.0) added "Executor" as a
#   deliberate, intentional revision of this closed set -- weighted the same
#   as a blacklist.yaml revision (a false-negative review backs the change,
#   see design.md §4). Recognition alone (this milestone, S1) is a no-op wrt
#   the gate's observable decision: "Executor" has no entry in console.py's
#   DEFAULT_BODY_PATHS (S2, body-path interpretation, was DESCOPED after a
#   2026-07-23 live probe returned decisively negative -- design.md §5), so
#   `Go+ Executor N` still holds; only the hold-reason string changes. A
#   follow-up SPEC (recommended: SPEC-COPILOT-EXECBODY-001, not yet created)
#   would need a responder-side (console/lua/copilot_responder.lua) extension
#   before S2 body interpretation could land.
RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor")

_NUMERIC_REF = re.compile(r"^\d+(\.\d+)*$")


@dataclass(frozen=True)
class RiskFinding:
    """Stage-② verdict for one parsed command (pre-expansion)."""

    command: str
    category: str  # "safe" | "blacklisted" | "invoking"
    risky: bool
    reasons: tuple[str, ...]
    unspecified_target: bool = False
    reference: str | None = None
    matched_entry: str | None = None


def _keyword_match(text: str, keyword: str) -> bool:
    """Case-insensitive exact or >=3-char-prefix match (abbreviation-aware)."""
    t, k = text.lower(), keyword.lower()
    return t == k or (len(t) >= 3 and k.startswith(t))


def _option_match(text: str, option: str) -> bool:
    """Match ``/xxx`` option tokens; options abbreviate from one character."""
    if not text.startswith("/") or not option.startswith("/"):
        return False
    body, target = text[1:].lower(), option[1:].lower()
    return len(body) >= 1 and target.startswith(body)


def _entry_part_matches(token: Token, part: str) -> bool:
    if token.quoted:
        return False  # quoted object names NEVER match keywords
    if part.startswith("/"):
        return token.text.startswith("/") and _option_match(token.text, part)
    return _keyword_match(token.text, part)


def _match_blacklist(parsed: ParsedCommand, ruleset: SafetyRuleset) -> str | None:
    for entry in ruleset.blacklist:
        parts = entry.split()
        if not _keyword_match(parsed.verb, parts[0]):
            continue
        if all(any(_entry_part_matches(a, part) for a in parsed.args) for part in parts[1:]):
            return entry
    return None


def _unspecified_target(parsed: ParsedCommand, entry: str) -> tuple[bool, str]:
    """Detect a destructive command lacking an explicit target (REQ-MVP-036b)."""
    entry_parts = entry.split()[1:]
    if any(part.lower() == "everything" for part in entry_parts):
        return True, "inherently broad scope (Everything)"
    remaining = [a for a in parsed.args if not any(_entry_part_matches(a, p) for p in entry_parts)]
    if not remaining:
        return True, "no explicit target specified"
    texts = [a.text for a in remaining if not a.quoted]
    if any(t == "*" for t in texts):
        return True, "broad target pattern (*)"
    if any(_keyword_match(t, "All") or _keyword_match(t, "Everything") for t in texts):
        return True, "broad target (All/Everything)"
    args = parsed.args
    for i, a in enumerate(args):
        if a.quoted or not _keyword_match(a.text, "Thru"):
            continue
        prev_numeric = i > 0 and not args[i - 1].quoted and _NUMERIC_REF.match(args[i - 1].text)
        next_numeric = (
            i + 1 < len(args) and not args[i + 1].quoted and _NUMERIC_REF.match(args[i + 1].text)
        )
        if not (prev_numeric and next_numeric):
            return True, "open-ended Thru range"
    return False, ""


def _bare_form_reference(parsed: ParsedCommand, ruleset: SafetyRuleset) -> str | None:
    for form in ruleset.bare_object_forms:
        type_word = form.split()[0]
        if _keyword_match(parsed.verb, type_word) and parsed.args:
            return f"{type_word} {parsed.args[0].text}"
    return None


def _extract_reference(parsed: ParsedCommand, reference_types: tuple[str, ...]) -> str | None:
    args = parsed.args
    for i, a in enumerate(args):
        if a.quoted:
            continue
        for type_word in reference_types:
            if _keyword_match(a.text, type_word) and i + 1 < len(args):
                return f"{type_word} {args[i + 1].text}"
    return None


# The property name a macro-authoring assignment stores command text under
# (M6b-1r2 rulebook recipe: `Command` on MA3 v2.4.2; `Cmd` on older material).
_COMMAND_PROPERTY_NAMES = ("command", "cmd")


# @MX:NOTE: [AUTO] narrow shape-specific detector for the M6c-2 Finding 1
#   quoted-property-content bypass — matches ONLY `Property 'Command'/'Cmd'
#   '<value>'`, so ordinary quoted object names/labels are never affected
def _quoted_property_command_value(parsed: ParsedCommand) -> Token | None:
    """Locate a ``Property 'Command'/'Cmd' '<value>'`` assignment's value token.

    Returns the quoted value token when the exact shape is present, else None.
    Deliberately narrow (verb-agnostic, but requires the literal ``Property``
    keyword immediately followed by a quoted ``Command``/``Cmd`` name token)
    so it cannot misfire on unrelated quoted content (e.g. object labels).
    """
    args = parsed.args
    for i, token in enumerate(args):
        if token.quoted or not _keyword_match(token.text, "Property"):
            continue
        if i + 2 >= len(args):
            continue
        name_token, value_token = args[i + 1], args[i + 2]
        if not name_token.quoted or not value_token.quoted:
            continue
        if name_token.text.strip().lower() in _COMMAND_PROPERTY_NAMES:
            return value_token
    return None


# @MX:ANCHOR: [AUTO] stage-② risk verdict — the gate pipeline, the expand-or-hold
#   recursion, and every FN-corpus test route classification through this function
# @MX:REASON: REQ-MVP-013/014 FN=0 rests on ONE matching semantics; a second
#   classifier would fork the closed-set interpretation (fan_in >= 3)
def classify_command(
    parsed: ParsedCommand,
    ruleset: SafetyRuleset,
    *,
    reference_types: tuple[str, ...] = RECOGNIZED_REFERENCE_TYPES,
) -> RiskFinding:
    """Classify one parsed command against the closed-set ruleset."""
    entry = _match_blacklist(parsed, ruleset)
    if entry is not None:
        unspecified, why = _unspecified_target(parsed, entry)
        reasons = [f"blacklisted command (matches closed-set entry {entry!r})"]
        if unspecified:
            reasons.append(f"unspecified target: {why}")
        return RiskFinding(
            command=parsed.raw,
            category="blacklisted",
            risky=True,
            reasons=tuple(reasons),
            unspecified_target=unspecified,
            matched_entry=entry,
        )

    # M6c-2 Finding 1 (REQ-MVP-013): a quoted `Property 'Command'/'Cmd'
    # '<value>'` assignment can smuggle a destructive command line past the
    # outer-syntax-only check above. Recurse the SAME classification into the
    # quoted value so a destructive/invoking command persisted this way is
    # treated exactly as if it had been sent bare (the outer assignment's own
    # verb never needs to be blacklist/invoking-verb shaped for this to fire).
    property_value = _quoted_property_command_value(parsed)
    if property_value is not None:
        nested_grammar = validate(property_value.text)
        if nested_grammar.ok:
            nested = classify_command(
                nested_grammar.parsed, ruleset, reference_types=reference_types
            )
            if nested.category != "safe":
                reasons = (
                    "quoted property value is itself an executable command "
                    f"({property_value.text!r})",
                    *nested.reasons,
                )
                return RiskFinding(
                    command=parsed.raw,
                    category=nested.category,
                    risky=nested.risky,
                    reasons=reasons,
                    unspecified_target=nested.unspecified_target,
                    reference=nested.reference,
                    matched_entry=nested.matched_entry,
                )

    bare_reference = _bare_form_reference(parsed, ruleset)
    if bare_reference is not None:
        return RiskFinding(
            command=parsed.raw,
            category="invoking",
            risky=False,
            reasons=("reference-invoking command (bare object call)",),
            reference=bare_reference,
        )
    if any(_keyword_match(parsed.verb, verb) for verb in ruleset.invoking_verbs):
        return RiskFinding(
            command=parsed.raw,
            category="invoking",
            risky=False,
            reasons=("reference-invoking command",),
            reference=_extract_reference(parsed, reference_types),
        )
    return RiskFinding(command=parsed.raw, category="safe", risky=False, reasons=())
