"""Rulebook fixed-prefix tests (M3 — AC-MVP-014 part 1, AC-MVP-028 parts 1-2).

The MA3 grammar rulebook is the fixed system-prompt prefix (REQ-MVP-007). It is
assembled deterministically from static assets and MUST be byte-stable across
assemblies (REQ-MVP-008 — no timestamps, session IDs, or any per-turn variable
values; one changed byte invalidates the whole provider cache prefix).

The Korean field-lighting term dictionary axis (REQ-MVP-042) is part of that
fixed prefix and inherits the same stability contract.
"""

from __future__ import annotations

import re

from server.rulebook.assembly import (
    RULEBOOK_VERSION,
    assemble_prefix,
    korean_term_entries,
    rulebook_asset_files,
)

# Variable-value patterns that must never appear in the fixed prefix
# (REQ-MVP-008: cache-prefix stability — no per-turn values).
_ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class TestPrefixStability:
    """AC-MVP-014 part 1 — byte identity of the fixed prefix over N>=5 assemblies."""

    def test_assembly_is_byte_identical_across_five_builds(self):
        builds = [assemble_prefix() for _ in range(5)]
        first = builds[0]
        assert first, "assembled prefix must be non-empty"
        assert all(build == first for build in builds), "prefix must be byte-identical"

    def test_assembly_is_byte_identical_when_reread_from_disk(self):
        # A second, independent assembly (fresh file reads) must match exactly.
        assert assemble_prefix() == assemble_prefix(version=RULEBOOK_VERSION)

    def test_prefix_contains_no_variable_value_patterns(self):
        prefix = assemble_prefix()
        assert not _ISO_TIMESTAMP.search(prefix), "prefix must not contain timestamps"
        assert not _ISO_DATE.search(prefix), "prefix must not contain calendar dates"
        assert not _UUID.search(prefix), "prefix must not contain UUIDs/session ids"
        assert "session" not in prefix.lower(), "prefix must not reference session ids"

    def test_prefix_targets_ma3_242_grammar(self):
        # The rulebook is versioned per MA3 release (plan.md section A-2 pin).
        assert RULEBOOK_VERSION == "2.4.2"
        assert "grandMA3" in assemble_prefix()

    def test_assets_are_markdown_files_in_stable_order(self):
        files = rulebook_asset_files()
        assert len(files) >= 3, "grammar + object model + korean terms expected"
        names = [path.name for path in files]
        assert names == sorted(names), "assembly order must be the sorted filename order"


class TestKoreanDictionaryAxis:
    """AC-MVP-028 parts 1-2 — dictionary axis present, >=10 entries, prefix-stable."""

    def test_dictionary_section_exists_in_prefix(self):
        assert "한국어 조명 용어 사전" in assemble_prefix()

    def test_at_least_ten_term_mappings(self):
        entries = korean_term_entries()
        assert len(entries) >= 10

    def test_includes_shamak_and_wash(self):
        terms = [entry.korean for entry in korean_term_entries()]
        assert any("샤막" in term for term in terms)
        assert any("워시" in term for term in terms)

    def test_every_entry_maps_to_ma3_vocabulary(self):
        for entry in korean_term_entries():
            assert entry.korean.strip(), "korean term must be non-empty"
            assert entry.ma3_vocabulary.strip(), f"{entry.korean}: MA3 vocabulary required"

    def test_dictionary_axis_is_inside_the_fixed_prefix(self):
        prefix = assemble_prefix()
        for entry in korean_term_entries():
            assert entry.korean in prefix, f"{entry.korean} must live in the fixed prefix"
