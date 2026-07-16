"""Safety ruleset SSOT tests (M4 — REQ-MVP-013/026 closed sets).

The blacklist and the invoking-verb set are CLOSED sets defined verbatim in a
single version-controlled config file (``server/safety/blacklist.yaml``). Set
changes are allowed ONLY via a file revision (version bump) — these tests pin
the initial v1 content exactly so any change creates review friction on purpose
(safety asymmetry: silent set widening/narrowing must be impossible).
"""

from __future__ import annotations

import pytest

from server.safety.ruleset import (
    DEFAULT_RULESET_PATH,
    RulesetError,
    SafetyRuleset,
    load_ruleset,
)

# The exact initial closed sets from REQ-MVP-013 and REQ-MVP-026 (verbatim).
EXPECTED_BLACKLIST = {
    "Delete",
    "Remove",
    "Off Everything",
    "Store /overwrite",
    "Shutdown",
    "Format",
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

    def test_blacklist_is_exactly_the_six_initial_entries(self):
        # REQ-MVP-013: exactly 6 entries, verbatim — no open-ended list.
        ruleset = load_ruleset()
        assert set(ruleset.blacklist) == EXPECTED_BLACKLIST
        assert len(ruleset.blacklist) == 6

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
