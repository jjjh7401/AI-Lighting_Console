"""Safety ruleset loader — the closed-set SSOT config (REQ-MVP-013/026).

Loads and validates ``server/safety/blacklist.yaml``: the blacklist (6 initial
entries) and the invoking-verb set (10 verbs + 2 bare object forms). Both are
CLOSED sets — any change requires a file revision with a version bump. The
loader enforces a closed schema (unknown keys rejected) so the SSOT file cannot
silently grow side channels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_RULESET_PATH = Path(__file__).resolve().parent / "blacklist.yaml"

_TOP_LEVEL_KEYS = frozenset({"version", "blacklist", "invoking_verbs"})
_INVOKING_KEYS = frozenset({"verbs", "bare_object_forms"})
_BARE_FORM = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]* <n>$")


class RulesetError(ValueError):
    """Raised when the safety ruleset file is missing, malformed, or unsafe."""


@dataclass(frozen=True)
class SafetyRuleset:
    """The validated closed sets from one revision of the SSOT file."""

    version: int
    blacklist: tuple[str, ...]
    invoking_verbs: tuple[str, ...]
    bare_object_forms: tuple[str, ...]


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RulesetError(f"{field} must be a non-empty list")
    entries: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RulesetError(f"{field} entries must be non-empty strings, got {item!r}")
        entries.append(item)
    lowered = [e.lower() for e in entries]
    if len(set(lowered)) != len(lowered):
        raise RulesetError(f"{field} contains duplicate entries")
    return tuple(entries)


# @MX:ANCHOR: [AUTO] closed-set SSOT load point — grammar/classify/expand and every
#   FN-corpus test consume the blacklist + invoking_verbs exclusively through here
# @MX:REASON: REQ-MVP-013/026 require ONE version-controlled closed-set source;
#   a second load path would let the sets silently diverge (fan_in >= 3)
def load_ruleset(path: Path | str = DEFAULT_RULESET_PATH) -> SafetyRuleset:
    """Load and validate the closed-set safety ruleset file."""
    path = Path(path)
    if not path.is_file():
        raise RulesetError(f"safety ruleset file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RulesetError(f"safety ruleset is not valid YAML: {error}") from error
    if not isinstance(data, dict):
        raise RulesetError("safety ruleset must be a mapping")

    unknown = set(data) - _TOP_LEVEL_KEYS
    if unknown:
        raise RulesetError(f"unknown top-level keys in safety ruleset: {sorted(unknown)}")

    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise RulesetError(f"version must be a positive integer, got {version!r}")

    blacklist = _string_tuple(data.get("blacklist"), field="blacklist")

    invoking = data.get("invoking_verbs")
    if not isinstance(invoking, dict):
        raise RulesetError("invoking_verbs must be a mapping with verbs + bare_object_forms")
    unknown_invoking = set(invoking) - _INVOKING_KEYS
    if unknown_invoking:
        raise RulesetError(f"unknown keys in invoking_verbs: {sorted(unknown_invoking)}")
    verbs = _string_tuple(invoking.get("verbs"), field="invoking_verbs.verbs")
    bare_forms = _string_tuple(
        invoking.get("bare_object_forms"), field="invoking_verbs.bare_object_forms"
    )
    for form in bare_forms:
        if not _BARE_FORM.match(form):
            raise RulesetError(f"bare object form must look like 'Macro <n>', got {form!r}")

    return SafetyRuleset(
        version=version,
        blacklist=blacklist,
        invoking_verbs=verbs,
        bare_object_forms=bare_forms,
    )
