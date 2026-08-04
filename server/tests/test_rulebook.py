"""Rulebook fixed-prefix tests (M3 — AC-MVP-014 part 1, AC-MVP-028 parts 1-2).

The MA3 grammar rulebook is the fixed system-prompt prefix (REQ-MVP-007). It is
assembled deterministically from static assets and MUST be byte-stable across
assemblies (REQ-MVP-008 — no timestamps, session IDs, or any per-turn variable
values; one changed byte invalidates the whole provider cache prefix).

The Korean field-lighting term dictionary axis (REQ-MVP-042) is part of that
fixed prefix and inherits the same stability contract, and so does the spatial
design axis (SPEC-COPILOT-SPATIAL-001 REQ-SPATIAL-016/017) — one asset added,
five assets untouchable.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from server.rulebook.assembly import (
    RULEBOOK_VERSION,
    assemble_prefix,
    korean_term_entries,
    rulebook_asset_files,
    rulebook_dir,
)

# Variable-value patterns that must never appear in the fixed prefix
# (REQ-MVP-008: cache-prefix stability — no per-turn values).
_ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

_REPO_ROOT = Path(__file__).resolve().parents[2]

# SPEC-COPILOT-SPATIAL-001 run-phase kickoff (progress.md §E.2.0 row 2). The
# five assets that existed then are PRESERVE for the whole SPEC: byte-diff 0.
_RUN_PHASE_BASE = "4d298b87225d4d0292b3c641360d90d231b5a177"
_ASSETS_PREFIX = "server/rulebook/assets/v2.4.2"
_PRESERVED_ASSETS = (
    "00_grammar.md",
    "10_object_model.md",
    "20_korean_terms.md",
    "30_plugin_patterns.md",
    "31_choreography_patterns.md",
)
_SPATIAL_ASSET = "32_spatial_design.md"

# A per-show binding is a rig object addressed by number. REQ-SPATIAL-017 keeps
# them out of the NEW asset: an example id in a freshly added file reads to the
# model as a universal fact about every show. The pattern is the one the
# look/fx/scene asset gates already use (`test_looks_library.py:74`).
_PER_SHOW_PATTERN = re.compile(
    r"(?:group|preset|fixture|fid|executor|exec|page|sequence|cue|universe|dmx|채널|그룹|프리셋|익스큐터)"
    r"\s*[.#]?\s*\d",
    re.IGNORECASE,
)


def _git(*arguments: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *arguments],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _preserved_paths() -> tuple[str, ...]:
    return tuple(f"{_ASSETS_PREFIX}/{name}" for name in _PRESERVED_ASSETS)


def _asset_text(name: str) -> str:
    return (rulebook_dir() / name).read_text(encoding="utf-8")


def _fenced_blocks(text: str) -> list[str]:
    """The fenced code blocks of one markdown asset, fences excluded."""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("\n".join(current))
                current = None
            continue
        if current is not None:
            current.append(line)
    assert current is None, "unbalanced code fence"
    return blocks


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


class TestFixtureNumbersAreNotAddressableIds:
    """A rig-context fixture number is a stage-patch SLOT; `Fixture <n>` on MA3
    addresses FID <n>. The two are equal only by coincidence.

    The tool description already refuses to promise FID-ness (pinned by
    test_tools.py::TestRigContextDescription), but the rulebook told the model
    to "select the patched fixtures by their real id range" in the same bullet
    that told it to read those fixtures from `get_rig_context` — closing a
    read->address loop the tool description explicitly forbids. Of the two
    surfaces the rulebook is the one the model is reading while it designs a
    look, so it wins; the failure is silent and wrong-target, because MA3
    accepts `Fixture 1 Thru 9` happily and stores the look against whichever
    fixtures own those FIDs.

    Repairing DEFAULT_RIG_CONTEXT_PATHS is what armed this: while the fixtures
    path was a dead placeholder the section never resolved, so the instruction
    could not be acted on. The prompt surface must not re-arm it.
    """

    def test_prefix_never_calls_a_rig_context_number_a_real_id(self):
        # The exact phrase that closed the read->address loop.
        assert "real id range" not in assemble_prefix()

    def test_prefix_states_a_fixture_number_is_a_slot_and_not_its_fid(self):
        prefix = assemble_prefix()
        # Both halves must be present: what the number IS, and what it is NOT.
        assert "NOT its fixture id" in prefix
        assert "slot" in prefix.lower()

    def test_prefix_teaches_how_to_confirm_a_real_fid_before_addressing_by_number(self):
        # The tool description tells the model to "confirm the FID with
        # query_state"; a rulebook that forbids the shortcut without naming
        # the confirmation step leaves the model with no way forward.
        assert "query_state" in assemble_prefix()

    def test_korean_dictionary_scopes_rig_context_ids_away_from_fixtures(self):
        # The blanket claim was true for groups/preset pools and false for
        # fixtures, making it a second, quieter source of the same defect.
        prefix = assemble_prefix()
        assert "the concrete object ids come from `get_rig_context`" not in prefix

    def test_korean_moving_head_row_does_not_authorize_bare_fixture_ranges(self):
        # The showfile-dependent 무빙 row resolves through `get_rig_context`,
        # so authorizing a `Fixture` range there inherits the slot/FID defect.
        assert "selected via `Group` or `Fixture` ranges" not in assemble_prefix()


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


class TestSpatialDesignAsset:
    """AC-SPATIAL-016 / AC-SPATIAL-017 — the rulebook grows by exactly one file.

    SPEC-COPILOT-SPATIAL-001 REQ-SPATIAL-016 allows one new asset and no other
    change. The prefix is a provider cache key (REQ-MVP-008), so touching an
    existing asset is not a documentation edit — it invalidates the cached
    prefix for every turn of every conversation.
    """

    def test_the_spatial_asset_sorts_immediately_after_the_choreography_one(self):
        names = [path.name for path in rulebook_asset_files()]
        assert names[names.index("31_choreography_patterns.md") + 1] == _SPATIAL_ASSET
        assert names[-1] == _SPATIAL_ASSET, "the spatial axis reads last, after the grammar"

    def test_the_asset_set_is_the_five_preserved_files_plus_the_new_one(self):
        names = tuple(path.name for path in rulebook_asset_files())
        assert names == (*_PRESERVED_ASSETS, _SPATIAL_ASSET)

    def test_the_preserved_assets_all_exist_at_the_run_phase_base(self):
        # Non-vacuity for the gate below: `git diff` reports nothing for a path
        # the base never had, so an empty diff is only evidence once the base is
        # known to carry all five.
        listed = _git("ls-tree", "--name-only", _RUN_PHASE_BASE, "--", *_preserved_paths())
        assert sorted(listed.split()) == sorted(_preserved_paths())

    def test_every_preserved_asset_is_byte_unchanged_from_the_run_phase_base(self):
        # Working tree against the base commit — not `base..HEAD` — so an
        # uncommitted edit is caught too. The five must not change at all.
        assert _git("diff", "--stat", _RUN_PHASE_BASE, "--", *_preserved_paths()) == ""

    def test_the_new_asset_is_appended_and_perturbs_no_earlier_byte(self):
        # The five preserved files still assemble, in order, as the HEAD of the
        # prefix. File 32 is appended, never interleaved.
        head = "\n\n".join(_asset_text(name).strip() for name in _PRESERVED_ASSETS)
        assert assemble_prefix().startswith(head + "\n\n")

    def test_the_prefix_carries_the_new_asset_verbatim_and_stays_byte_stable(self):
        builds = [assemble_prefix() for _ in range(5)]
        assert _asset_text(_SPATIAL_ASSET).strip() in builds[0]
        assert all(build == builds[0] for build in builds)

    def test_the_spatial_asset_names_no_per_show_binding(self):
        for number, line in enumerate(_asset_text(_SPATIAL_ASSET).splitlines(), 1):
            match = _PER_SHOW_PATTERN.search(line)
            assert match is None, f"{_SPATIAL_ASSET}:{number} binds {match.group(0)!r}"

    def test_the_per_show_scan_would_catch_a_binding(self):
        # Non-vacuity: the scan above must be able to fail.
        assert _PER_SHOW_PATTERN.search("Fixture 11 + Fixture 12") is not None

    def test_the_recipe_teaches_the_two_step_phaser(self):
        text = _asset_text(_SPATIAL_ASSET)
        for line in (
            "Attribute 'Dimmer' At 0",
            "Step 2",
            "Attribute 'Dimmer' At 100",
            "Attribute 'Dimmer' At Phase 0 Thru 360",
            "Attribute 'Dimmer' At Speed 30",
        ):
            assert line in text, line

    def test_no_recipe_spreads_a_phase_across_a_single_static_value(self):
        # M0 measured this exact shape: one value, then `At Phase 0 Thru 360`.
        # Every line answered ok and the stage stayed lit and MOTIONLESS
        # (progress.md §E.2.7), so the one-step form must never be shown.
        blocks = [
            block for block in _fenced_blocks(_asset_text(_SPATIAL_ASSET)) if "At Phase" in block
        ]
        assert blocks, "non-vacuity: the asset must actually teach a phaser"
        for block in blocks:
            lines = block.splitlines()
            fan = next(index for index, line in enumerate(lines) if "At Phase" in line)
            assert any(line.strip().startswith("Step ") for line in lines[:fan]), block

    def test_no_fenced_command_carries_a_coordinate_or_a_double_quote(self):
        # REQ-SPATIAL-014 on the teaching surface. A coordinate is a DECIMAL
        # number, and a recipe that showed one is a recipe the model would copy.
        # A double quote cannot be sent at all (`server/bridge/protocol.py:105`),
        # which is why every MA3 name in the recipe is single-quoted.
        decimal = re.compile(r"\d\.|\.\d")
        blocks = _fenced_blocks(_asset_text(_SPATIAL_ASSET))
        assert blocks, "non-vacuity: the asset must actually show commands"
        assert decimal.search("Attribute 'Posx' At -4.25"), "non-vacuity: the scan can fail"
        for block in blocks:
            for line in block.splitlines():
                assert decimal.search(line) is None, line
                assert '"' not in line, line
