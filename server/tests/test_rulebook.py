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


class TestMacroAuthoringRecipe:
    """M6b-1r2 — the r1 5.86% FAIL root cause was a rulebook teaching gap:
    macros were taught only as runnable, so the model filled the authoring
    gap with grandMA2 `/Cmd='...'` assignment syntax (invalid on MA3 v2.x,
    16/19 rejections). The prefix must teach the compliant MA3 form."""

    def test_prefix_teaches_the_ma3_set_property_macro_recipe(self):
        prefix = assemble_prefix()
        # Canonical v2.4 form (keyword_set/keyword_equal), single-quoted per
        # this deployment's transport rule (double quotes are forbidden).
        assert "Set Macro" in prefix
        assert "Property 'Command'" in prefix

    def test_prefix_carries_the_ma2_assignment_anti_example(self):
        prefix = assemble_prefix()
        assert "MA2" in prefix
        assert "/Cmd=" in prefix  # named explicitly as INVALID on MA3

    def test_prefix_warns_against_dotted_quoted_name_composition(self):
        # r1 numerator minority pattern (3/19): `Preset 4.'Blue'` mid-token
        # quote — a pool id and a quoted name must never be dot-composed.
        prefix = assemble_prefix()
        assert "4.'Blue'" in prefix  # shown as the anti-example

    def test_recipe_examples_pass_the_structural_validator(self):
        # The recipe must only teach lines our own gate accepts.
        from server.safety.grammar import validate

        for line in (
            "Store Macro 21",
            "Store Macro 21.1",
            "Set Macro 21.1 Property 'Command' 'ClearAll'",
        ):
            assert validate(line).ok, line

    def test_prefix_warns_against_nested_quotes_inside_a_macro_lines_command_text(self):
        # M6c-8 backlog item 3 (00_grammar.md:81) — the macro-authoring recipe
        # never addressed what happens when <command text> itself needs a
        # single-quoted object name. Naively composing `Label Group 7
        # 'Vocals'` into a macro line produces a nested-quote command with no
        # escape mechanism (`Set Macro 21.3 Property 'Command' 'Label Group 7
        # 'Vocals'''), which either breaks the outer property-value string
        # early or is malformed. The prefix must warn against this and steer
        # toward numeric/dotted pool-id references inside macro lines.
        prefix = assemble_prefix()
        assert "nested" in prefix.lower() and "quote" in prefix.lower()
        # The anti-example shows the exact broken composition so the model
        # recognizes the shape it must avoid.
        assert "'Label Group 7 'Vocals''" in prefix
        # Positive guidance: numeric/dotted pool-id reference preferred
        # inside a macro line's command text specifically.
        assert "Group 3" in prefix and "Preset 4.1" in prefix


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
