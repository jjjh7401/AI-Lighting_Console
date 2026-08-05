"""Safety ruleset SSOT tests (M4 — REQ-MVP-013/026 closed sets).

The blacklist and the invoking-verb set are CLOSED sets defined verbatim in a
single version-controlled config file (``server/safety/blacklist.yaml``). Set
changes are allowed ONLY via a file revision (version bump) — these tests pin
the shipped content exactly so any change creates review friction on purpose
(safety asymmetry: silent set widening/narrowing must be impossible).

The friction is working as designed, not being worked around: the pins below
were updated for the v1 -> v2 revision (SPEC-COPILOT-WRITEGATE-001) BECAUSE
that revision is deliberate and ratified — the file's REVISION HISTORY header
carries its justification, and this update is the second half of the same
ratification. A pin edit with no corresponding entry in that header is the
thing these tests exist to stop.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.safety.ruleset import (
    DEFAULT_RULESET_PATH,
    RulesetError,
    SafetyRuleset,
    load_ruleset,
)

# The shipped closed set: the 6 initial entries from REQ-MVP-013 (verbatim)
# plus the one v2 addition (SPEC-COPILOT-WRITEGATE-001 — fixture patch writes
# are showfile mutations and need a human; see blacklist.yaml REVISION HISTORY).
EXPECTED_BLACKLIST = {
    "Delete",
    "Remove",
    "Off Everything",
    "Store /overwrite",
    "Shutdown",
    "Format",
    "Set Fixture",
}
EXPECTED_INVOKING_VERBS = (
    "Go", "Go+", "Go-", "Goto", "On", "Off", "Toggle", "Temp", "Flash", "Call"
)  # fmt: skip
EXPECTED_BARE_FORMS = ("Macro <n>", "Plugin <n>")

# One revision-log marker, e.g. `v1 -> v2`. Used both to FIND a bump's entry
# and to find where the NEXT one starts, so an entry cannot silently absorb
# its neighbour's justification.
_REVISION_MARKER = re.compile(r"v\d+ -> v\d+")


def _revision_history_block(text: str) -> str:
    """The contiguous comment block the ``REVISION HISTORY`` header introduces.

    Ends at the first non-comment line (``version:`` on the shipped file). A
    whole-file substring check cannot tell the log from prose living anywhere
    else in the file; this can.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "REVISION HISTORY" not in line:
            continue
        block = [line]
        for follow in lines[i + 1 :]:
            if not follow.lstrip().startswith("#"):
                break
            block.append(follow)
        return "\n".join(block)
    return ""


def _revision_entry(block: str, marker: str) -> str:
    """One revision's OWN text: its marker plus its continuation lines.

    Terminated by the next ``v<n> -> v<n+1>`` marker, so a contentless entry
    cannot pass by borrowing the justification of the entry above it.
    """
    start = block.find(marker)
    if start < 0:
        return ""
    rest = block[start + len(marker) :]
    following = _REVISION_MARKER.search(rest)
    return marker + (rest[: following.start()] if following else rest)


def _assert_every_revision_is_justified(path: Path) -> None:
    """Assert every version bump ``path`` ships carries a justified entry.

    Two layers, because either one alone is defeatable:

    ① the ``v<N-1> -> v<N>`` marker occurs INSIDE the REVISION HISTORY block,
      not merely somewhere in the file;
    ② that marker's OWN entry names the ratifying ``SPEC-COPILOT-`` id.

    Takes a path rather than reading the SSOT directly so the SAME checker can
    be driven over synthetic multi-revision files — that is what makes the loop
    below more than single-iteration decoration (``TestRevisionJustification``).
    """
    ruleset = load_ruleset(path)
    text = path.read_text(encoding="utf-8")
    block = _revision_history_block(text)
    assert block, (
        f"{path.name} ships version {ruleset.version} with no REVISION HISTORY "
        "comment block — a closed-set file that cannot say why a set changed "
        "provides no friction at all (REQ-MVP-013)"
    )
    for bump in range(2, ruleset.version + 1):
        marker = f"v{bump - 1} -> v{bump}"
        assert marker in block, (
            f"{path.name} ships version {ruleset.version} but its REVISION "
            f"HISTORY block documents no '{marker}' revision — a closed-set "
            "change must carry its justification IN THE LOG, not merely "
            "somewhere in the file (REQ-MVP-013)"
        )
        entry = _revision_entry(block, marker)
        assert "SPEC-COPILOT-" in entry, (
            f"the '{marker}' entry of {path.name}'s REVISION HISTORY names no "
            "ratifying SPEC-COPILOT- id, so the bump records THAT it happened "
            f"but not who ratified it — entry was: {entry.strip()!r}"
        )


class TestShippedRuleset:
    def test_shipped_file_exists_and_loads(self):
        ruleset = load_ruleset()
        assert isinstance(ruleset, SafetyRuleset)

    def test_version_field_is_required_and_positive(self):
        ruleset = load_ruleset()
        assert isinstance(ruleset.version, int)
        assert ruleset.version >= 1

    def test_blacklist_is_exactly_the_shipped_closed_set(self):
        # REQ-MVP-013 (6 initial) + the ratified v2 addition — no open-ended list.
        ruleset = load_ruleset()
        assert set(ruleset.blacklist) == EXPECTED_BLACKLIST
        assert len(ruleset.blacklist) == 7

    def test_every_shipped_revision_is_documented_in_the_file(self):
        """A version bump with no recorded reason is a silent widening.

        Pinning entry text alone is not enough: it forces an edit here, but it
        cannot force the edit to be JUSTIFIED. So `version: N` must not ship
        without a `v<N-1> -> v<N>` line saying what changed and which SPEC
        ratified it. Deliberately NOT an entry-count rule — a future revision
        may add two entries at once, and a count formula would manufacture
        false friction.

        The check is TWO layers because the single whole-file
        `"v1 -> v2" in text` form it replaces was defeatable: swapping the
        entire 12-line justification for a contentless `# REVISION HISTORY` +
        `#   v1 -> v2` left this module green. The enforced property now
        matches the documented one — the marker must sit INSIDE the REVISION
        HISTORY block, and that marker's own entry must name the ratifying
        SPEC. Both probes live in `TestRevisionJustification`.

        On the version pin: it STAYS (deliberate friction — a bump has to come
        here and be argued). It does make the checker's loop single-iteration
        at the shipped pin, so rather than soften the docstring to match, the
        "every shipped revision" generality is made REAL by driving the same
        checker over a synthetic v4 file in `TestRevisionJustification`.
        """
        assert load_ruleset().version == 2
        _assert_every_revision_is_justified(DEFAULT_RULESET_PATH)

    def test_invoking_verbs_are_exactly_the_ten_initial_verbs(self):
        # REQ-MVP-026: 10 verbs, verbatim, order preserved from the file.
        ruleset = load_ruleset()
        assert ruleset.invoking_verbs == EXPECTED_INVOKING_VERBS

    def test_bare_object_forms_are_exactly_the_two_initial_forms(self):
        ruleset = load_ruleset()
        assert ruleset.bare_object_forms == EXPECTED_BARE_FORMS

    def test_default_path_is_the_ssot_yaml_under_server_safety(self):
        assert DEFAULT_RULESET_PATH.name == "blacklist.yaml"
        assert DEFAULT_RULESET_PATH.parent.name == "safety"


class TestRevisionJustification:
    """The revision-log checker, driven over files the shipped pin cannot reach.

    `test_every_shipped_revision_is_documented_in_the_file` keeps its
    `version == 2` pin, so its loop runs once. These supply what that call
    cannot: the multi-bump generality, and the negative controls proving each
    layer of the check actually bites. Every file below is written under
    `tmp_path` — the SSOT `blacklist.yaml` is never touched.
    """

    # The closed sets themselves are irrelevant here; only the header is under
    # test, so this is the smallest body `load_ruleset` accepts.
    _SETS = (
        "blacklist: ['Delete']\n"
        "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n"
    )

    def _write(self, tmp_path, header: str, *, version: int = 2) -> Path:
        path = tmp_path / "blacklist.yaml"
        path.write_text(f"{header}version: {version}\n{self._SETS}", encoding="utf-8")
        return path

    def test_a_justified_revision_passes(self, tmp_path):
        # Positive control: the shipped shape, minimised. Without this the
        # probes below could be passing on an unconditionally-failing checker.
        path = self._write(
            tmp_path,
            "# REVISION HISTORY:\n"
            '#   v1 -> v2  SPEC-COPILOT-WRITEGATE-001 adds "Set Fixture" because a\n'
            "#     patch row is showfile state.\n",
        )
        _assert_every_revision_is_justified(path)

    def test_a_contentless_marker_inside_the_block_is_rejected(self, tmp_path):
        """PROBE E1 — the exact defeat the whole-file substring form allowed.

        Replacing the justification with a bare marker used to leave this
        module at 17 passed: `"REVISION HISTORY" in text` and `"v1 -> v2" in
        text` were both still true. Layer ② is what stops it.
        """
        path = self._write(tmp_path, "# REVISION HISTORY\n#   v1 -> v2\n")
        with pytest.raises(AssertionError, match="ratifying SPEC-COPILOT- id"):
            _assert_every_revision_is_justified(path)

    def test_a_justification_living_outside_the_log_is_rejected(self, tmp_path):
        # Layer ①: both substrings are present in the file, but the marker is
        # not in the LOG — it is loose prose down beside the sets. The
        # whole-file form could not tell the two apart.
        path = tmp_path / "blacklist.yaml"
        path.write_text(
            "# REVISION HISTORY (nothing recorded):\n"
            "version: 2\n"
            "# v1 -> v2  SPEC-COPILOT-SMUGGLED-001 — justification in the wrong place\n"
            f"{self._SETS}",
            encoding="utf-8",
        )
        with pytest.raises(AssertionError, match="documents no 'v1 -> v2' revision"):
            _assert_every_revision_is_justified(path)

    def test_a_missing_revision_history_header_is_rejected(self, tmp_path):
        # Negative control E0: the header itself is load-bearing.
        path = self._write(
            tmp_path, '#   v1 -> v2  SPEC-COPILOT-WRITEGATE-001 adds "Set Fixture".\n'
        )
        with pytest.raises(AssertionError, match="no REVISION HISTORY"):
            _assert_every_revision_is_justified(path)

    def test_a_multi_revision_file_is_checked_bump_by_bump(self, tmp_path):
        """The generality the shipped `version == 2` pin makes unreachable.

        Three bumps, each justified, all checked in one call — this is the loop
        running more than once for real rather than only in a docstring.
        """
        path = self._write(
            tmp_path,
            "# REVISION HISTORY:\n"
            '#   v1 -> v2  SPEC-COPILOT-WRITEGATE-001 adds "Set Fixture".\n'
            "#   v2 -> v3  SPEC-COPILOT-EXAMPLE-002 adds a second entry.\n"
            "#   v3 -> v4  SPEC-COPILOT-EXAMPLE-003 narrows one entry.\n",
            version=4,
        )
        _assert_every_revision_is_justified(path)

    def test_one_unjustified_bump_among_justified_ones_is_rejected(self, tmp_path):
        # An entry must not pass by borrowing its neighbour's justification:
        # the `v3 -> v4` entry terminates at nothing, so it is empty, while the
        # two above it are fine. Without the marker-to-marker slice the trailing
        # bump would inherit `SPEC-COPILOT-EXAMPLE-002` and pass.
        path = self._write(
            tmp_path,
            "# REVISION HISTORY:\n"
            '#   v1 -> v2  SPEC-COPILOT-WRITEGATE-001 adds "Set Fixture".\n'
            "#   v2 -> v3  SPEC-COPILOT-EXAMPLE-002 adds a second entry.\n"
            "#   v3 -> v4\n",
            version=4,
        )
        with pytest.raises(AssertionError, match="the 'v3 -> v4' entry"):
            _assert_every_revision_is_justified(path)


class TestRulesetValidation:
    def _write(self, tmp_path, text: str):
        path = tmp_path / "blacklist.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(RulesetError, match="not found"):
            load_ruleset(tmp_path / "nope.yaml")

    def test_missing_version_raises(self, tmp_path):
        path = self._write(
            tmp_path,
            "blacklist: ['Delete']\ninvoking_verbs:\n  verbs: ['Go']\n"
            "  bare_object_forms: ['Macro <n>']\n",
        )
        with pytest.raises(RulesetError, match="version"):
            load_ruleset(path)

    def test_non_integer_version_raises(self, tmp_path):
        path = self._write(
            tmp_path,
            "version: '1'\nblacklist: ['Delete']\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n",
        )
        with pytest.raises(RulesetError, match="version"):
            load_ruleset(path)

    def test_empty_blacklist_raises(self, tmp_path):
        path = self._write(
            tmp_path,
            "version: 1\nblacklist: []\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n",
        )
        with pytest.raises(RulesetError, match="blacklist"):
            load_ruleset(path)

    def test_duplicate_blacklist_entries_raise(self, tmp_path):
        path = self._write(
            tmp_path,
            "version: 1\nblacklist: ['Delete', 'Delete']\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n",
        )
        with pytest.raises(RulesetError, match="duplicate"):
            load_ruleset(path)

    def test_missing_invoking_verbs_table_raises(self, tmp_path):
        path = self._write(tmp_path, "version: 1\nblacklist: ['Delete']\n")
        with pytest.raises(RulesetError, match="invoking_verbs"):
            load_ruleset(path)

    def test_unknown_top_level_key_raises(self, tmp_path):
        # Closed schema: the SSOT file carries the closed sets and nothing else.
        path = self._write(
            tmp_path,
            "version: 1\nblacklist: ['Delete']\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n"
            "extras: ['x']\n",
        )
        with pytest.raises(RulesetError, match="unknown"):
            load_ruleset(path)

    def test_bare_form_must_match_type_placeholder_pattern(self, tmp_path):
        path = self._write(
            tmp_path,
            "version: 1\nblacklist: ['Delete']\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro']\n",
        )
        with pytest.raises(RulesetError, match="bare"):
            load_ruleset(path)

    def test_non_string_entry_raises(self, tmp_path):
        path = self._write(
            tmp_path,
            "version: 1\nblacklist: ['Delete', 5]\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n",
        )
        with pytest.raises(RulesetError, match="string"):
            load_ruleset(path)

    def test_valid_minimal_file_loads(self, tmp_path):
        path = self._write(
            tmp_path,
            "version: 2\nblacklist: ['Delete']\n"
            "invoking_verbs:\n  verbs: ['Go']\n  bare_object_forms: ['Macro <n>']\n",
        )
        ruleset = load_ruleset(path)
        assert ruleset.version == 2
        assert ruleset.blacklist == ("Delete",)
        assert ruleset.invoking_verbs == ("Go",)
