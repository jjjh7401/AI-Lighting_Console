"""Built-in look library census (M2 — AC-LOOKLIB-002 / AC-LOOKLIB-003 / AC-LOOKLIB-004).

This is an EXHAUSTIVE census, not a sample: every assert below walks the whole
shipped library. A sample-based test would let a single bad look through, and a
bad look here is not a test-fixture problem — it is a bad command sent to a real
console.

The three requirements under test:

* REQ-LOOKLIB-002 — four genres, 6-10 looks each, the dynamics scale covered
  from its lowest band to its highest.
* REQ-LOOKLIB-003 — the attribute vocabulary is limited to the three bands, and
  the v1 library carries no movement at all (band 6, v0.3.1 F3).
* REQ-LOOKLIB-004 — no per-show value anywhere.

Failure modes are separate tests on purpose (design.md §6.2). Nothing here
touches a console: the library is static repo data and the loader is pure.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from server.looks.loader import DEFAULT_LIBRARY_DIR, LookSchemaError, load_library_from_dir
from server.looks.roles import ROLE_NAMES
from server.looks.schema import (
    CONFIRMED_ATTRIBUTES,
    DYNAMICS_MAX,
    DYNAMICS_MIN,
    IN_SCOPE_POOL_FAMILIES,
    MOVEMENT_ONLY_ATTRIBUTES,
    PROBE_GATED_ATTRIBUTES,
    Look,
    look_to_dict,
    payload_for_family,
    pool_family,
)

# The four genres of 사용자 확정 ② (spec.md §A). The slugs are English because
# the genre is a machine axis paired with the English ``look_id``; Korean is
# first-class where REQ-LOOKLIB-001 puts it — display_name, aliases and mood
# keywords. ``EDM`` would otherwise force a mixed-script enum.
EXPECTED_GENRES = ("worship", "rock", "ballad", "edm")

MIN_LOOKS_PER_GENRE = 6
MAX_LOOKS_PER_GENRE = 10

# The dynamics bands REQ-LOOKLIB-002 requires each genre to reach.
LOW_BAND = frozenset({1, 2})
HIGH_BAND = frozenset({4, 5})

# Band 1 + band 3 — the only names that may carry a static value. Band 2
# (Pan/Tilt) is legal ONLY inside a movement spec, and the v1 library has no
# movement, so its occurrence count here is zero.
STATIC_VOCABULARY = frozenset(CONFIRMED_ATTRIBUTES + PROBE_GATED_ATTRIBUTES)

COLOR_CHANNELS = ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")

# Substring scan, matching the shipped verification grep verbatim. These are API
# tokens, not topic words, so a plain case-insensitive substring is the right
# shape — a word boundary would miss ``ColorRGB_Pan``-style compounds. Focus /
# Frost / Prism1 / Shutter were REJECTED by the M0 probe and are out of scope
# under every branch (spec.md §D); Pan / Tilt are movement-only.
FORBIDDEN_ATTRIBUTE_TOKENS = ("Pan", "Tilt", "Focus", "Frost", "Prism", "Shutter")

# A per-show value can only reach the assets through a string field (the schema
# is closed) or through a comment. Both are scanned. The pattern is keyword +
# number because that is what an actual rig binding looks like; the bare words
# may legitimately appear in prose explaining why they are absent.
PER_SHOW_PATTERN = re.compile(
    r"(?:group|preset|fixture|fid|executor|exec|page|sequence|cue|universe|dmx|채널|그룹|프리셋|익스큐터)"
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


def _by_genre(library) -> dict[str, list[Look]]:
    grouped: dict[str, list[Look]] = {}
    for look in library.looks:
        grouped.setdefault(look.genre, []).append(look)
    return grouped


class TestLibraryLoads:
    """AC-LOOKLIB-002 — the shipped assets are loadable at all."""

    def test_the_shipped_library_loads_without_error(self, library):
        # load_library_from_dir raises LookSchemaError on any violation, so a
        # clean return already means every look passed the M1 loader.
        assert library.looks, "the shipped library is empty"

    def test_every_look_is_individually_reachable_by_id(self, library):
        for look in library.looks:
            assert library.by_id(look.look_id) is look

    def test_look_ids_are_unique_across_the_whole_library(self, library):
        ids = [look.look_id for look in library.looks]
        assert len(ids) == len(set(ids)), "duplicate look id across asset files"

    def test_assets_are_yaml_files_under_the_library_directory(self, asset_paths):
        assert asset_paths, f"no *.yaml assets in {DEFAULT_LIBRARY_DIR}"


class TestGenreCoverage:
    """AC-LOOKLIB-002 — four genres, 6-10 looks each."""

    def test_exactly_the_four_confirmed_genres_are_present(self, library):
        assert set(_by_genre(library)) == set(EXPECTED_GENRES)

    def test_every_genre_carries_between_six_and_ten_looks(self, library):
        for genre, looks in sorted(_by_genre(library).items()):
            assert MIN_LOOKS_PER_GENRE <= len(looks) <= MAX_LOOKS_PER_GENRE, (
                f"{genre} has {len(looks)} looks, "
                f"expected {MIN_LOOKS_PER_GENRE}-{MAX_LOOKS_PER_GENRE}"
            )


class TestDynamicsScale:
    """AC-LOOKLIB-002 — the integer scale and the per-genre coverage rule."""

    def test_every_dynamics_level_is_an_integer_within_range(self, library):
        for look in library.looks:
            assert isinstance(look.dynamics, int) and not isinstance(look.dynamics, bool)
            assert DYNAMICS_MIN <= look.dynamics <= DYNAMICS_MAX, (
                f"{look.look_id} dynamics {look.dynamics} out of range"
            )

    def test_every_genre_reaches_the_low_band(self, library):
        # "Reaches its lowest band" is mechanised as >=1 look at level 1 or 2
        # (acceptance.md AC-LOOKLIB-002). Asserted separately from the high band
        # so a failure names which end of the arc is missing.
        for genre, looks in sorted(_by_genre(library).items()):
            levels = {look.dynamics for look in looks}
            assert levels & LOW_BAND, (
                f"{genre} has no look at dynamics 1 or 2 (levels: {sorted(levels)})"
            )

    def test_every_genre_reaches_the_high_band(self, library):
        for genre, looks in sorted(_by_genre(library).items()):
            levels = {look.dynamics for look in looks}
            assert levels & HIGH_BAND, (
                f"{genre} has no look at dynamics 4 or 5 (levels: {sorted(levels)})"
            )


class TestAttributeVocabulary:
    """AC-LOOKLIB-003 bands 1, 2, 3 — the census over every attribute name."""

    def test_every_static_attribute_is_in_the_confirmed_or_probed_bands(self, library):
        for look in library.looks:
            for value in look.attributes:
                assert value.name in STATIC_VOCABULARY, (
                    f"{look.look_id} uses {value.name!r}, outside {sorted(STATIC_VOCABULARY)}"
                )

    def test_no_movement_only_attribute_appears_as_a_static_value(self, library):
        # Band 2: Pan/Tilt are legal only inside a movement spec. Since the v1
        # library has no movement (see TestMovementAbsence), their total count
        # is zero — but this assert survives the day movement is switched on.
        for look in library.looks:
            for value in look.attributes:
                assert value.name not in MOVEMENT_ONLY_ATTRIBUTES, (
                    f"{look.look_id} carries {value.name!r} as a static position value"
                )

    def test_no_probe_rejected_beam_string_appears_in_any_asset(self, asset_text):
        # Raw-text scan, not a parsed scan: the loader would reject these names
        # in an attribute payload, but it never sees a comment or a display
        # name. Focus/Frost/Prism1/Shutter were rejected by the console at M0.
        for name, text in asset_text:
            for token in FORBIDDEN_ATTRIBUTE_TOKENS:
                assert token.lower() not in text.lower(), (
                    f"{name} mentions {token!r}; band-2 and probe-rejected "
                    "vocabulary must not appear in the v1 assets at all"
                )

    def test_every_attribute_attributes_to_exactly_one_in_scope_pool_family(self, library):
        # AC-LOOKLIB-003 band 4 — an allowed name with no pool to store it in
        # would only surface at M4, when the bundle builder has nowhere to put it.
        for look in library.looks:
            for value in look.attributes:
                family = pool_family(value.name)
                assert family in IN_SCOPE_POOL_FAMILIES, (
                    f"{look.look_id}: {value.name!r} attributes to {family!r}, "
                    f"not one of {list(IN_SCOPE_POOL_FAMILIES)}"
                )

    def test_every_payload_splits_by_family_without_loss(self, library):
        # AC-LOOKLIB-003 band 5 — the mechanical evidence that the ASSUMPTION-14
        # FALLBACK branch (per-family isolated capture) can be built from this
        # same data without re-authoring the library.
        for look in library.looks:
            union: list = []
            for family in IN_SCOPE_POOL_FAMILIES:
                union.extend(payload_for_family(look, family))
            assert sorted(union, key=lambda a: a.name) == sorted(
                look.attributes, key=lambda a: a.name
            ), f"{look.look_id} payload does not partition cleanly by family"


class TestColourIsFullySpecified:
    """M0 secondary observation — a partially named colour renders white.

    Storing a preset after setting only one ColorRGB channel captures the whole
    colour family, so a look that names only R arrives on the console as white.
    Naming one channel is therefore not "specifying less colour", it is
    specifying a different colour than the author intended.
    """

    def test_a_look_naming_any_colour_channel_names_all_three(self, library):
        for look in library.looks:
            named = {value.name for value in look.attributes if value.name in COLOR_CHANNELS}
            assert named in (set(), set(COLOR_CHANNELS)), (
                f"{look.look_id} names {sorted(named)} but not all of "
                f"{list(COLOR_CHANNELS)} — it would render white on the console"
            )

    def test_every_look_specifies_a_colour(self, library):
        # Not required by the schema, but a look with no colour is a look whose
        # colour is whatever the programmer left active — the same silent
        # inheritance the rule above guards against.
        for look in library.looks:
            named = {value.name for value in look.attributes if value.name in COLOR_CHANNELS}
            assert named == set(COLOR_CHANNELS), f"{look.look_id} specifies no colour"

    def test_every_look_specifies_an_intensity(self, library):
        names = {"Dimmer"}
        for look in library.looks:
            assert names & {value.name for value in look.attributes}, (
                f"{look.look_id} specifies no Dimmer"
            )


class TestMovementAbsence:
    """AC-LOOKLIB-003 band 6 — TWO separate asserts, deliberately not merged."""

    def test_no_shipped_look_carries_a_movement_spec(self, library):
        offenders = [look.look_id for look in library.looks if look.movement]
        assert offenders == [], (
            f"{offenders} declare movement; the v1 bundle never emits that field, "
            "so the declared axis would be dropped while the run reports success "
            "(design.md AP-18)"
        )

    def test_the_schema_still_round_trips_a_movement_bearing_look(self):
        # The other half of the pair. Without this, "the library has no
        # movement" and "the field was deleted" are indistinguishable — and the
        # field is a successor-SPEC contract (P1-1 / P1-2).
        from server.looks.loader import load_library
        from server.looks.schema import SCHEMA_VERSION

        with_movement = {
            "look_id": "probe-movement-roundtrip",
            "display_name": "왕복 확인용",
            "genre": "worship",
            "dynamics": 3,
            "roles": ["백라이트"],
            "attributes": {"Dimmer": 60, "ColorRGB_R": 100, "ColorRGB_G": 70, "ColorRGB_B": 20},
            "movement": [
                {"attribute": "Pan", "phase_from": 0, "phase_to": 360, "speed": 60},
            ],
        }
        loaded = load_library({"schema_version": SCHEMA_VERSION, "looks": [with_movement]})
        look = loaded.looks[0]
        assert len(look.movement) == 1
        assert look.movement[0].attribute == "Pan"

        # dump -> parse -> identical object.
        reloaded = load_library({"schema_version": SCHEMA_VERSION, "looks": [look_to_dict(look)]})
        assert reloaded.looks[0] == look


class TestNoPerShowValues:
    """AC-LOOKLIB-004 — structural absence plus a census over the assets."""

    def test_the_schema_carries_no_rig_binding_field(self):
        # Structural half: there is no field to put a per-show value in.
        fields = {field.name for field in dataclasses.fields(Look)}
        forbidden = {
            "group",
            "group_number",
            "preset",
            "preset_slot",
            "slot",
            "fid",
            "fixture",
            "fixture_id",
            "executor",
            "executor_number",
            "page",
            "universe",
            "dmx_address",
        }
        assert not (fields & forbidden), (
            f"schema exposes rig binding field(s): {fields & forbidden}"
        )

    def test_no_look_string_field_carries_a_per_show_binding(self, library):
        # The closed schema means a per-show value can only ride in on a string.
        for look in library.looks:
            for label, text in (
                ("look_id", look.look_id),
                ("display_name", look.display_name),
                ("genre", look.genre),
                *((f"alias {a!r}", a) for a in look.aliases),
                *((f"mood {m!r}", m) for m in look.mood_keywords),
            ):
                match = PER_SHOW_PATTERN.search(text)
                assert match is None, (
                    f"{look.look_id} {label} contains a per-show binding: {match.group(0)!r}"
                )

    def test_no_asset_file_mentions_a_per_show_binding(self, asset_text):
        # Comments are scanned too: an example binding in a comment is the
        # invitation for the next author to write a real one.
        for name, text in asset_text:
            for line_number, line in enumerate(text.splitlines(), start=1):
                match = PER_SHOW_PATTERN.search(line)
                assert match is None, (
                    f"{name}:{line_number} contains a per-show binding: {match.group(0)!r}"
                )

    def test_roles_are_the_only_way_a_look_names_a_stage_position(self, library):
        for look in library.looks:
            assert look.roles, f"{look.look_id} names no role"
            for role in look.roles:
                assert role in ROLE_NAMES, (
                    f"{look.look_id} uses role {role!r} outside the closed set"
                )


class TestKoreanIsFirstClass:
    """REQ-LOOKLIB-001 — Korean aliases and mood keywords, not an afterthought."""

    def test_every_display_name_is_korean(self, library):
        for look in library.looks:
            assert HANGUL.search(look.display_name), (
                f"{look.look_id} display_name {look.display_name!r} has no Hangul"
            )

    def test_every_look_carries_at_least_one_korean_mood_keyword(self, library):
        for look in library.looks:
            korean = [word for word in look.mood_keywords if HANGUL.search(word)]
            assert korean, f"{look.look_id} has no Korean mood keyword"

    def test_every_look_carries_at_least_one_alias(self, library):
        for look in library.looks:
            assert look.aliases, f"{look.look_id} has no alias"


class TestCensusIsExhaustive:
    """Guards on the census itself — a census that walks nothing passes silently."""

    def test_the_library_is_large_enough_to_make_the_census_meaningful(self, library):
        # 4 genres x 6 looks minimum. If a future edit drops the library to a
        # handful of looks, every per-look loop above would still "pass".
        assert len(library.looks) >= len(EXPECTED_GENRES) * MIN_LOOKS_PER_GENRE

    def test_the_census_sees_every_asset_file(self, library, asset_paths):
        # Ties the parsed view to the on-disk view: a file the loader silently
        # skipped would never be censused.
        assert len(asset_paths) == len(EXPECTED_GENRES)
        assert len(library.looks) >= len(asset_paths)

    def test_a_missing_library_directory_is_an_explicit_error(self, tmp_path):
        with pytest.raises(LookSchemaError):
            load_library_from_dir(tmp_path / "does-not-exist")
