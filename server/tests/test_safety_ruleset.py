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
        cannot force the edit to be JUSTIFIED. This asserts the file documents
        its own current version, so `version: N` cannot ship without a
        `v<N-1> -> v<N>` line saying what changed and which SPEC ratified it.
        Deliberately NOT an entry-count rule — a future revision may add two
        entries at once, and a count formula would manufacture false friction.
        """
        ruleset = load_ruleset()
        assert ruleset.version == 2
        text = DEFAULT_RULESET_PATH.read_text(encoding="utf-8")
        assert "REVISION HISTORY" in text
        for bump in range(2, ruleset.version + 1):
            assert f"v{bump - 1} -> v{bump}" in text, (
                f"blacklist.yaml ships version {ruleset.version} but documents no "
                f"'v{bump - 1} -> v{bump}' revision — a closed-set change must "
                f"carry its justification in the file (REQ-MVP-013)"
            )

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
