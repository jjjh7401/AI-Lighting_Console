"""Built-in fx library census (M2 — AC-FXLIB-002 / AC-FXLIB-003 / AC-FXLIB-004).

An EXHAUSTIVE census over the shipped assets, mirroring `test_looks_library.py`:
every assert walks the whole library. A sample would let one bad entry through,
and a bad entry here is not a fixture problem — it is a bad command sent to a
real console.

TWO LAYERS, DELIBERATELY. Half of these tests read the YAML directly
(`raw_entries` / `asset_text`) and half read it through the M1 loader
(`library`). The loader has its own suite (`test_fx_schema.py`); if this census
ran only through it, an asset regression and a loader regression would be
indistinguishable, and a loader that stopped enforcing a rule would also stop
this census from noticing that an asset had broken it. The raw layer survives
that.

WHY THE CENSUS CARRIES UNUSUAL WEIGHT HERE. M0 measured that an effect is not
machine-readable (progress.md §E.2): a stored cue holding a phaser is
indistinguishable from an empty one, phase/speed read back as "property not
readable", and live fixture values are not readable either. A malformed entry
therefore produces `ok:true` on every line and silence on stage. The loader and
this census are the whole net under the assets.

Nothing here touches a console: static repo data plus pure functions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from server.fx.loader import DEFAULT_LIBRARY_DIR, FxSchemaError, load_library_from_dir
from server.fx.schema import (
    GATED_CURVE_AXES,
    KNOWN_ATTRIBUTES,
    MIN_STEPS,
    PATTERN_KINDS,
)

# spec.md §A — 4 unconditional kinds, plus the 2 that entered on the
# ASSUMPTION-37 GO M0 recorded. The gate is mechanised through PATTERN_KINDS
# rather than through a document read: `test_fx_schema.py` pins that tuple to
# the GO branch, so if the judgement were ever reversed there, the coverage
# tests below would demand the two gated kinds be ABSENT from the library.
UNCONDITIONAL_PATTERNS = ("sweep", "wave", "circle", "diagonal")
GATED_PATTERNS = ("pulse", "chase")

# 31_choreography_patterns.md:236-241 — the mood table's two numeric speed
# bands, reseeded under a BPM reading (ASSUMPTION-38 GO). Under BPM both bands
# read as musical tempo, which is what makes them usable as seeds at all.
SLOW_BAND = (10.0, 20.0)  # warm / ballad / intimate
FAST_BAND = (90.0, 180.0)  # energetic / club / party

# The one speed that does NOT come from the mood table. M0 fired it on a live
# console and watched the result, so this entry is a regression baseline: the
# bundle M4 renders from it has to match the measured shape (AC-FXLIB-008).
M0_ANCHOR_ID = "pulse-beat"
M0_ANCHOR_SPEED = 60.0
M0_ANCHOR_STEPS = ({"Dimmer": 100}, {"Dimmer": 0})
M0_ANCHOR_PHASE = (0.0, 360.0)

# Raw-text scan tokens. Case-insensitive substrings of the COMMAND form, not of
# the topic word: the assets are allowed to discuss why a verb is absent, and
# keying on the bare word would blunt the scan into uselessness the first time
# somebody wrote a comment. Comments are scanned too — an example line in a
# comment is the invitation for the next author to write a real one.
FORBIDDEN_COMMAND_FORMS = (
    "at absolute",  # static position value — spec.md §D
    "at accel",  # probe-pending curve, effect unobserved at M0 (SKIP)
    "at decel",
    "at relative",  # unmeasured as a step value — ASSUMPTION-40, v1 never emits it
    "attribute '",  # the assets carry values, never command lines
)

# REQ-FXLIB-022 / AC-FXLIB-023 owns its own token so a failure names that AC
# rather than the general vocabulary one. This form is accepted by the console
# with `ok:true` and does nothing (M0 — it caused the probe's three failures).
FORBIDDEN_STEP_FORM = "at step"

# server/web/preview.py:131 rates these dangerous to audience and camera; the
# family is out of scope (spec.md §D). Word-boundary, matching that classifier.
DANGER_TOKEN = re.compile(r"\b(strobe|shutter|hz)\b", re.IGNORECASE)

# Keyword + number, because that is what an actual rig binding looks like; the
# bare words may legitimately appear in prose explaining why they are absent.
# Shape borrowed from `test_looks_library.py` (REQ-LOOKLIB-004 mirror).
PER_SHOW_PATTERN = re.compile(
    r"(?:group|preset|fixture|fid|executor|exec|page|sequence|cue|universe|dmx"
    r"|채널|그룹|프리셋|익스큐터|시퀀스|큐)"
    r"\s*[.#]?\s*\d",
    re.IGNORECASE,
)

HANGUL = re.compile(r"[가-힣]")


@pytest.fixture(scope="module")
def library():
    """The real shipped library, loaded exactly the way production loads it."""
    return load_library_from_dir()


@pytest.fixture(scope="module")
def asset_paths() -> tuple[Path, ...]:
    return tuple(sorted(DEFAULT_LIBRARY_DIR.glob("*.yaml")))


@pytest.fixture(scope="module")
def asset_text(asset_paths) -> tuple[tuple[str, str], ...]:
    return tuple((path.name, path.read_text(encoding="utf-8")) for path in asset_paths)


@pytest.fixture(scope="module")
def raw_entries(asset_paths) -> tuple[tuple[str, dict], ...]:
    """Every entry as it sits on disk, parsed but NOT validated.

    The loader is not in this path on purpose — see the module docstring.
    """
    entries: list[tuple[str, dict]] = []
    for path in asset_paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for entry in data["fx"]:
            entries.append((f"{path.name}:{entry.get('fx_id')}", entry))
    return tuple(entries)


class TestLibraryLoads:
    """AC-FXLIB-002 — the shipped assets are loadable at all."""

    def test_the_shipped_library_loads_without_error(self, library):
        # load_library_from_dir raises on any violation, so a clean return
        # already means every entry passed the M1 loader.
        assert library.fx, "the shipped library is empty"

    def test_every_fx_is_individually_reachable_by_id(self, library):
        for fx in library.fx:
            assert library.by_id(fx.fx_id) is fx

    def test_fx_ids_are_unique_across_the_whole_library(self, library):
        ids = [fx.fx_id for fx in library.fx]
        assert len(ids) == len(set(ids)), "duplicate fx id across asset files"

    def test_assets_are_yaml_files_under_the_library_directory(self, asset_paths):
        assert asset_paths, f"no *.yaml assets in {DEFAULT_LIBRARY_DIR}"


class TestPatternCoverage:
    """AC-FXLIB-002 — the closed vocabulary, covered and not exceeded."""

    def test_every_unconditional_pattern_has_at_least_one_entry(self, library):
        kinds = {fx.pattern for fx in library.fx}
        missing = [kind for kind in UNCONDITIONAL_PATTERNS if kind not in kinds]
        assert missing == [], f"no entry for unconditional pattern(s): {missing}"

    def test_the_gated_patterns_have_entries_while_the_schema_still_carries_them(self, library):
        # The conditional half of AC-FXLIB-002: `pulse`/`chase` exist because M0
        # recorded ASSUMPTION-37 GO. PATTERN_KINDS is where that judgement lives
        # in code, so this reads the gate rather than restating its outcome.
        kinds = {fx.pattern for fx in library.fx}
        for pattern in GATED_PATTERNS:
            if pattern in PATTERN_KINDS:
                assert pattern in kinds, f"{pattern} is open but has no library entry"
            else:
                assert pattern not in kinds, f"{pattern} is gated shut but has a library entry"

    def test_no_entry_uses_a_pattern_kind_outside_the_closed_set(self, raw_entries):
        # Raw layer: this holds even if the loader stopped checking.
        for where, entry in raw_entries:
            assert entry["pattern"] in PATTERN_KINDS, (
                f"{where} uses pattern {entry['pattern']!r}, outside {list(PATTERN_KINDS)}"
            )

    def test_the_library_covers_the_closed_set_exactly(self, library):
        assert {fx.pattern for fx in library.fx} == set(PATTERN_KINDS)


class TestStepAxisInEveryAsset:
    """AC-FXLIB-002 — every entry satisfies the phaser creation condition.

    Asserted at the raw layer as well as the loaded one. These are the two
    checks M0 turned into the only automatic detectors of a silent failure: an
    entry that breaks either one reaches the stage as `ok:true` and no motion.
    """

    def test_every_asset_entry_declares_at_least_two_steps(self, raw_entries):
        for where, entry in raw_entries:
            steps = entry.get("steps")
            assert isinstance(steps, list) and len(steps) >= MIN_STEPS, (
                f"{where} declares {steps if steps is None else len(steps)} step(s); "
                f"a phaser needs at least {MIN_STEPS}"
            )

    def test_every_asset_entry_declares_one_attribute_set_across_its_steps(self, raw_entries):
        for where, entry in raw_entries:
            sets = [frozenset(step) for step in entry["steps"]]
            assert len(set(sets)) == 1, (
                f"{where} changes attribute set mid-run: {[sorted(s) for s in sets]}"
            )

    def test_no_asset_entry_repeats_a_value_for_one_attribute(self, raw_entries):
        # A repeated value emits an identical command line; the instruction-scoped
        # dedupe drops the second one and the phaser silently loses a step.
        for where, entry in raw_entries:
            steps = entry["steps"]
            for attribute in steps[0]:
                values = [step[attribute] for step in steps]
                assert len(values) == len(set(values)), (
                    f"{where} repeats a value for {attribute!r}: {values}"
                )

    def test_every_step_value_is_an_absolute_number(self, raw_entries):
        # `At Relative <n>` as a step value is unmeasured (ASSUMPTION-40), so a
        # non-numeric step value is a form v1 has no way to emit.
        for where, entry in raw_entries:
            for index, step in enumerate(entry["steps"]):
                for attribute, value in step.items():
                    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
                        f"{where} steps[{index}] {attribute} is {value!r}, not an absolute number"
                    )

    def test_every_loaded_fx_exposes_the_same_step_count_as_its_asset(self, library, raw_entries):
        by_id = {entry["fx_id"]: entry for _, entry in raw_entries}
        for fx in library.fx:
            assert len(fx.steps) == len(by_id[fx.fx_id]["steps"])


class TestVocabularyBands:
    """AC-FXLIB-003 — only band 1 and band 2 attributes, and no command forms."""

    def test_every_attribute_named_by_an_asset_is_in_the_closed_vocabulary(self, raw_entries):
        for where, entry in raw_entries:
            for step in entry["steps"]:
                for attribute in step:
                    assert attribute in KNOWN_ATTRIBUTES, (
                        f"{where} uses attribute {attribute!r}, outside "
                        f"{sorted(KNOWN_ATTRIBUTES)}"
                    )

    def test_no_asset_carries_a_forbidden_command_form(self, asset_text):
        # Raw text, comments included. The parsed scan cannot see a comment, and
        # a comment is where a forbidden form gets rehearsed before it is used.
        for name, text in asset_text:
            lowered = text.lower()
            for token in FORBIDDEN_COMMAND_FORMS:
                assert token not in lowered, (
                    f"{name} contains {token!r}; the assets carry values only, and that "
                    "form is outside the REQ-FXLIB-003 vocabulary"
                )

    def test_no_asset_mentions_the_out_of_scope_danger_family(self, asset_text):
        for name, text in asset_text:
            match = DANGER_TOKEN.search(text)
            assert match is None, (
                f"{name} mentions {match.group(0)!r}; that family is out of scope "
                "(spec.md §D) and the preview classifier rates it dangerous"
            )

    def test_no_loaded_fx_carries_a_relative_amplitude(self, library):
        # The parsed half of the `At Relative` exclusion: the schema keeps the
        # axis (a successor may measure it) and v1 leaves it empty.
        offenders = [fx.fx_id for fx in library.fx if fx.relative is not None]
        assert offenders == [], f"{offenders} declare a relative amplitude; v1 never emits it"


class TestGatedCurveAxesCarryNoValue:
    """AC-FXLIB-003 ② — accel/decel got `ok:true` and no observed effect at M0."""

    def test_no_asset_entry_declares_a_gated_curve_key(self, raw_entries):
        # Raw layer on purpose: the loader refuses these values, but that
        # refusal is M1's test. This one names the ASSET as the offender.
        for where, entry in raw_entries:
            declared = [axis for axis in GATED_CURVE_AXES if entry.get(axis) is not None]
            assert declared == [], (
                f"{where} declares {declared}; those curves are probe-pending "
                "(M0 recorded ok:true with no observed effect), so v1 defines the "
                "field and never carries a value in it"
            )

    def test_no_loaded_fx_carries_a_gated_curve_value(self, library):
        for fx in library.fx:
            for axis in GATED_CURVE_AXES:
                assert getattr(fx, axis) is None, f"{fx.fx_id} carries {axis}"


class TestForbiddenStepFormIsAbsent:
    """AC-FXLIB-023 (library half — the bundle half is M4's).

    The console accepts this form with `ok:true` and does nothing, and the
    effect is not machine-readable, so no runtime signal would ever expose it.
    A total scan is the only defence, which is why it is its own AC.
    """

    def test_no_asset_contains_the_forbidden_step_form(self, asset_text):
        for name, text in asset_text:
            assert FORBIDDEN_STEP_FORM not in text.lower(), (
                f"{name} contains {FORBIDDEN_STEP_FORM!r}; a step transition is a "
                "standalone line and never an attribute verb (REQ-FXLIB-022)"
            )


class TestNoPerShowValues:
    """AC-FXLIB-004 — rig binding happens at instantiation time, never here."""

    def test_no_asset_entry_declares_a_rig_binding_key(self, raw_entries):
        # Independent of the loader's unknown-key rejection: this names the
        # asset even if the schema were opened up.
        forbidden = {
            "group",
            "group_number",
            "sequence",
            "sequence_number",
            "cue",
            "cue_number",
            "fid",
            "fixture",
            "fixture_id",
            "slot",
            "executor",
            "executor_number",
            "page",
            "universe",
            "dmx_address",
        }
        for where, entry in raw_entries:
            smuggled = sorted(set(entry) & forbidden)
            assert smuggled == [], f"{where} declares rig binding key(s): {smuggled}"

    def test_no_fx_string_field_carries_a_per_show_binding(self, library):
        # The closed schema means a per-show value can only ride in on a string.
        for fx in library.fx:
            for label, text in (
                ("fx_id", fx.fx_id),
                ("display_name", fx.display_name),
                ("pattern", fx.pattern),
                *((f"alias {a!r}", a) for a in fx.aliases),
                *((f"mood {m!r}", m) for m in fx.mood_keywords),
            ):
                match = PER_SHOW_PATTERN.search(text)
                assert match is None, (
                    f"{fx.fx_id} {label} contains a per-show binding: {match.group(0)!r}"
                )

    def test_no_asset_file_mentions_a_per_show_binding(self, asset_text):
        for name, text in asset_text:
            for line_number, line in enumerate(text.splitlines(), start=1):
                match = PER_SHOW_PATTERN.search(line)
                assert match is None, (
                    f"{name}:{line_number} contains a per-show binding: {match.group(0)!r}"
                )


class TestKoreanIsFirstClass:
    """AC-FXLIB-002 / REQ-FXLIB-002 — Korean field vocabulary, not an afterthought."""

    def test_every_display_name_is_korean(self, library):
        for fx in library.fx:
            assert HANGUL.search(fx.display_name), (
                f"{fx.fx_id} display_name {fx.display_name!r} has no Hangul"
            )

    def test_every_fx_carries_at_least_one_korean_mood_keyword(self, library):
        for fx in library.fx:
            korean = [word for word in fx.mood_keywords if HANGUL.search(word)]
            assert korean, f"{fx.fx_id} has no Korean mood keyword"

    def test_every_fx_carries_at_least_one_korean_alias(self, library):
        # The matcher (M3) reads aliases before mood keywords; a library with
        # English-only aliases would answer a Korean instruction with a fallback.
        for fx in library.fx:
            korean = [word for word in fx.aliases if HANGUL.search(word)]
            assert korean, f"{fx.fx_id} has no Korean alias"


class TestSpeedSeeds:
    """REQ-FXLIB-002 — the mood table reseeded under a BPM reading."""

    def test_every_fx_declares_a_speed(self, library):
        # An entry with no speed inherits whatever rate was last set, which is
        # the same silent inheritance an unset colour channel would cause.
        for fx in library.fx:
            assert fx.speed is not None, f"{fx.fx_id} declares no speed"

    def test_every_speed_is_a_mood_table_seed_or_the_measured_anchor(self, library):
        for fx in library.fx:
            if fx.fx_id == M0_ANCHOR_ID:
                # The single exemption, and it is an exemption UPWARD in
                # evidence: this value was measured on a console rather than
                # read off a table (progress.md §E.2).
                assert fx.speed == M0_ANCHOR_SPEED
                continue
            in_slow = SLOW_BAND[0] <= fx.speed <= SLOW_BAND[1]
            in_fast = FAST_BAND[0] <= fx.speed <= FAST_BAND[1]
            assert in_slow or in_fast, (
                f"{fx.fx_id} speed {fx.speed} is in neither mood-table band "
                f"{SLOW_BAND} nor {FAST_BAND}"
            )

    def test_the_library_offers_both_bands(self, library):
        speeds = [fx.speed for fx in library.fx]
        assert any(SLOW_BAND[0] <= s <= SLOW_BAND[1] for s in speeds), "no slow-band entry"
        assert any(FAST_BAND[0] <= s <= FAST_BAND[1] for s in speeds), "no fast-band entry"


class TestM0AnchorIsPinned:
    """The one entry transcribed from a live measurement (progress.md §E.2).

    M4 has to render a bundle from this entry that matches the measured shape
    string for string (AC-FXLIB-008), so its values are a regression baseline
    rather than a taste decision.
    """

    def test_the_anchor_entry_exists(self, library):
        assert library.by_id(M0_ANCHOR_ID).pattern == "pulse"

    def test_the_anchor_steps_match_the_measured_shape(self, library):
        fx = library.by_id(M0_ANCHOR_ID)
        rendered = tuple({v.attribute: v.value for v in step.values} for step in fx.steps)
        assert rendered == M0_ANCHOR_STEPS

    def test_the_anchor_phase_and_speed_match_the_measured_shape(self, library):
        fx = library.by_id(M0_ANCHOR_ID)
        assert (fx.phase_from, fx.phase_to) == M0_ANCHOR_PHASE
        assert fx.speed == M0_ANCHOR_SPEED


class TestCensusIsExhaustive:
    """Guards on the census itself — a census that walks nothing passes silently."""

    def test_the_library_is_large_enough_to_make_the_census_meaningful(self, library):
        assert len(library.fx) >= len(PATTERN_KINDS)

    def test_the_census_sees_every_entry_on_disk(self, library, raw_entries):
        # Ties the parsed view to the on-disk view: an entry the loader silently
        # skipped would never be censused.
        assert len(library.fx) == len(raw_entries)

    def test_the_raw_layer_reads_more_than_one_asset_file(self, asset_paths):
        # The raw scans loop over files; one file would still "pass" them all.
        assert len(asset_paths) > 1

    def test_a_missing_library_directory_is_an_explicit_error(self, tmp_path):
        with pytest.raises(FxSchemaError):
            load_library_from_dir(tmp_path / "does-not-exist")


# -- F1: the closed key sets are pinned by MEMBERSHIP, not only by rejection ---
#
# Found by the independent sync-audit (24 mutations, this was the only survivor):
# adding `group_number` to the loader's library-level key set AND shipping it in
# an asset passed all 482 tests. Two nets were open at once —
#   * the schema test proves an unknown key is rejected by feeding it "rig",
#     which stays unknown no matter what the set gains; it never pinned WHICH
#     keys are allowed.
#   * PER_SHOW_PATTERN requires a digit right after the keyword, so it catches
#     the console form `Group 11` but not the YAML form `group_number: 11`.
# Both are closed below. The loader does not read such a key today, so this was
# a hole in the net rather than a shipped defect — which is exactly the kind
# that survives until someone widens the set for an unrelated reason.


def test_the_library_level_key_set_is_exactly_these_two():
    from server.fx.loader import _LIBRARY_KEYS

    assert set(_LIBRARY_KEYS) == {"schema_version", "fx"}


PER_SHOW_KEY_NAME = re.compile(
    r"(?:group|preset|fixture|fid|executor|exec|page|sequence|cue|universe|dmx|rig|slot)",
    re.IGNORECASE,
)


def _yaml_keys(node, path=""):
    """Every mapping key in the document, with its path, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}" if path else str(key)
            yield here, str(key)
            yield from _yaml_keys(value, here)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _yaml_keys(value, f"{path}[{index}]")


def test_no_asset_declares_a_key_NAMED_after_a_per_show_binding(asset_text):
    # The value-side scan above catches `group: 11`. This catches `group_number: 11`,
    # where the binding hides in the KEY and the value is a bare integer.
    for name, text in asset_text:
        document = yaml.safe_load(text)
        for path, key in _yaml_keys(document):
            match = PER_SHOW_KEY_NAME.search(key)
            assert match is None, (
                f"{name}: key {path!r} is named after a per-show binding: {match.group(0)!r}"
            )
