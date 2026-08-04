"""Spatial choreography tests — M3 (AC-SPATIAL-014 / AC-SPATIAL-015).

SPEC-COPILOT-SPATIAL-001 REQ-SPATIAL-014 and REQ-SPATIAL-015.

Two axes, and they fail for different reasons on purpose:

* **the qualifier matcher** — `왼쪽에서 오른쪽` must land on exactly one of four
  closed names, an unknown qualifier must MISS visibly, and a query naming two
  must return nothing at all. The last one is the load-bearing case: the stage
  effect of a selection order has no machine channel (spec.md §C.1), so a
  confident wrong pick executes silently and looks correct in every log;
* **the utterance** — the emitted chain must equal `spatial_sorted_fids`
  element for element, and the whole bundle must carry NO coordinate. That scan
  is AC-SPATIAL-014, and it is the machine half of this SPEC's premise: M0
  reversed a live wave by reversing the chain alone, with the coordinates and
  every phaser line held identical (progress.md §E.2.7).

The 1x8 golden is not a convenient shape — it is the rig M0 physically built on
the console for that observation (fids 11..18 at x = -3.5 .. 3.5). The chains
asserted here are the two chains a human watched sweep left and right.

Nothing here touches a console. The two transport-side checks
(`server.safety.grammar.validate`, `server.bridge.protocol.build_exec_request`)
are pure validators run over the produced strings: they prove the bundle is
SENDABLE without sending it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from server.bridge.protocol import build_exec_request
from server.safety.grammar import validate
from server.spatial import (
    SPATIAL_QUALIFIER_AMBIGUOUS,
    SPATIAL_QUALIFIER_EMPTY,
    SPATIAL_QUALIFIER_NO_MATCH,
    SPATIAL_QUALIFIER_REASONS,
    SPATIAL_SORTS,
    SPATIAL_WAVE_ATTRIBUTE,
    SPATIAL_WAVE_DEFAULT_SPEED,
    SPATIAL_WAVE_HIGH,
    SPATIAL_WAVE_LOW,
    SPATIAL_WAVE_PHASE_SPAN,
    SpatialAnalysisError,
    analyze_spatial_records,
    build_spatial_selection_chain,
    build_spatial_wave_commands,
    match_spatial_qualifier,
    resolve_spatial_sort,
    spatial_sorted_fids,
)

SPATIAL_DIR = Path(__file__).resolve().parents[1] / "spatial"
RULEBOOK_ASSET = Path(__file__).resolve().parents[1] / "rulebook" / "assets" / "v2.4.2"

# A concrete rig object addressed by number — forbidden in a static asset
# (REQ-SPATIAL-017), which is why the recipe's chain line is a placeholder.
_PER_SHOW_ID = re.compile(r"(?:fixture|fid|group)\s*[.#]?\s*\d", re.IGNORECASE)


def _rec(fid: int, x: float, y: float, z: float) -> dict:
    return {"fid": fid, "name": f"MMX {fid}", "x": x, "y": y, "z": z}


def _live_bar_1x8() -> list[dict]:
    """The rig M0 built on the console for the P8 observation (progress.md §E.2.7).

    fids 11..18, one row, x from -3.5 to 3.5 at 1.0 spacing. Every x is a half
    metre, which is also what makes it usable for the coordinate scan: no
    rendering of any of these values collides with a fid or a phaser literal.
    """
    return [_rec(11 + i, -3.5 + i, 0.0, 3.0) for i in range(8)]


def _fractional_grid_3x10() -> list[dict]:
    """3 rows of 10 where NO coordinate on ANY axis is a whole number.

    The 1x8 golden leaves y and z integral, so a leak of `0` or `3` would be
    indistinguishable from a phaser literal or a fid. Here every coordinate on
    all three axes renders with a fraction, which makes the scan sharp on all
    three rather than on x alone.
    """
    return [
        _rec(
            row * 10 + column + 21,
            -4.25 + 1.5 * column,
            -3.75 + 3.25 * row,
            4.75,
        )
        for row in range(3)
        for column in range(10)
    ]


@pytest.fixture(scope="module")
def bar():
    return analyze_spatial_records(_live_bar_1x8())


@pytest.fixture(scope="module")
def grid():
    return analyze_spatial_records(_fractional_grid_3x10())


# --------------------------------------------------------------------------
# AC-SPATIAL-015 — the qualifier lands on the closed vocabulary, or on nothing
# --------------------------------------------------------------------------


class TestQualifierHits:
    """The mappings REQ-SPATIAL-015 names, plus the phrasings around them."""

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            # The four examples the SPEC itself writes out.
            ("왼쪽에서 오른쪽", "left_to_right"),
            ("오른쪽에서 왼쪽", "right_to_left"),
            ("가운데부터 바깥으로", "center_out"),
            ("대각선", "diagonal"),
            # Same instruction, ordinary sentence shapes around it.
            ("왼쪽에서 오른쪽으로 웨이브 걸어줘", "left_to_right"),
            ("오른쪽에서 왼쪽으로 흘러가게", "right_to_left"),
            ("센터에서 양옆으로 퍼지는 느낌", "center_out"),
            ("대각선으로 훑어줘", "diagonal"),
            # Shorter synonyms inside the closed endpoint list.
            ("좌에서 우로", "left_to_right"),
            ("우측에서 좌측으로", "right_to_left"),
            ("중앙부터 바깥쪽으로", "center_out"),
            ("사선으로", "diagonal"),
        ],
    )
    def test_a_qualifier_resolves_to_its_sort(self, query, expected):
        assert resolve_spatial_sort(query) == expected

    @pytest.mark.parametrize(
        "query",
        [
            "왼쪽에서 오른쪽",  # bare, no trailing particle
            "왼쪽에서 오른쪽으로",  # 으로
            "왼쪽에서 오른쪽까지",  # 까지
            "왼쪽에서부터 오른쪽",  # compound origin marker
            "왼쪽부터 오른쪽",  # 부터 as the origin marker
            "왼쪽에서도 시작하는 웨이브",  # origin marker + a second particle
        ],
    )
    def test_korean_particles_do_not_hide_the_qualifier(self, query):
        # 조사 handling is the whole reason a closed particle list exists
        # (`server/looks/matching.py:139`): the operator writes 왼쪽에서, never 왼쪽.
        assert resolve_spatial_sort(query) == "left_to_right"

    def test_a_decomposed_hangul_query_resolves_the_same(self):
        # macOS hands over NFD often enough to matter, and NFD 왼쪽 is a
        # different string from NFC 왼쪽 to every regex in the matcher.
        import unicodedata

        composed = "왼쪽에서 오른쪽으로"
        decomposed = unicodedata.normalize("NFD", composed)
        assert decomposed != composed
        assert resolve_spatial_sort(decomposed) == "left_to_right"

    def test_the_origin_particle_is_what_picks_the_starting_end(self):
        # `오른쪽` appears FIRST here, carrying an object particle. Reading the
        # first endpoint word as the origin would answer right_to_left.
        assert resolve_spatial_sort("오른쪽 무버를 왼쪽에서 오른쪽으로") == "left_to_right"

    def test_every_sort_in_the_closed_vocabulary_is_reachable(self):
        # Non-vacuity: the miss tests below would all pass against a matcher
        # that answers None to everything.
        reached = {
            resolve_spatial_sort(query)
            for query in ("왼쪽에서 오른쪽", "오른쪽에서 왼쪽", "가운데부터 바깥으로", "대각선")
        }
        assert reached == set(SPATIAL_SORTS)

    def test_a_resolved_sort_is_always_a_member_of_the_closed_vocabulary(self):
        for query in ("좌에서 우로", "우에서 좌로", "안쪽에서 가장자리로", "사선"):
            sort = resolve_spatial_sort(query)
            assert sort is None or sort in SPATIAL_SORTS


class TestQualifierMisses:
    """A miss is an answer. It is never the nearest neighbour."""

    @pytest.mark.parametrize("query", ["", "   ", "\n\t "])
    def test_an_empty_query_reports_empty_and_not_no_match(self, query):
        result = match_spatial_qualifier(query)
        assert result.sort is None
        assert result.reason == SPATIAL_QUALIFIER_EMPTY
        assert result.candidates == ()

    @pytest.mark.parametrize(
        "query",
        [
            "따뜻한 발라드 느낌으로",  # a mood, not a direction
            "앞에서 뒤로",  # a real axis the vocabulary has no sort for
            "왼쪽 오른쪽",  # two ends named, neither marked as the origin
            "좌우로 흔들어",  # "left and right" names no direction at all
            "밝게 해줘",
        ],
    )
    def test_an_unknown_qualifier_falls_back_instead_of_guessing(self, query):
        result = match_spatial_qualifier(query)
        assert result.sort is None
        assert result.reason == SPATIAL_QUALIFIER_NO_MATCH
        assert result.candidates == ()

    def test_outside_in_resolves_to_nothing_rather_than_to_its_mirror(self):
        # `center_out` is in the vocabulary; its reverse is not. Mapping
        # 바깥에서 가운데로 onto center_out would be the invented mapping
        # REQ-SPATIAL-015 forbids — and it would run the wave backwards.
        assert match_spatial_qualifier("바깥에서 가운데로").reason == SPATIAL_QUALIFIER_NO_MATCH

    def test_a_pair_the_vocabulary_cannot_express_resolves_to_nothing(self):
        # centre -> left is a real instruction and not one of the four sorts.
        # Falling back on the origin alone would answer center_out.
        assert match_spatial_qualifier("가운데에서 왼쪽으로").reason == SPATIAL_QUALIFIER_NO_MATCH

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("왼쪽에서 오른쪽으로 갔다가 오른쪽에서 왼쪽으로", ("left_to_right", "right_to_left")),
            ("대각선으로 왼쪽에서 오른쪽으로", ("left_to_right", "diagonal")),
        ],
    )
    def test_two_sorts_named_returns_none_and_reports_both(self, query, expected):
        result = match_spatial_qualifier(query)
        assert result.sort is None
        assert result.reason == SPATIAL_QUALIFIER_AMBIGUOUS
        assert result.candidates == expected

    def test_the_ambiguous_candidates_come_back_in_the_canonical_order(self):
        # A reported ambiguity must read the same way every time, so the order
        # is SPATIAL_SORTS' order and not set-iteration order.
        result = match_spatial_qualifier("대각선으로 왼쪽에서 오른쪽으로")
        assert list(result.candidates) == [
            sort for sort in SPATIAL_SORTS if sort in set(result.candidates)
        ]


class TestQualifierContract:
    """Properties that hold for every query, hit or miss."""

    _QUERIES = (
        "",
        "왼쪽에서 오른쪽으로",
        "대각선",
        "밝게 해줘",
        "왼쪽에서 오른쪽으로 갔다가 오른쪽에서 왼쪽으로",
        "바깥에서 가운데로",
    )

    def test_a_reason_is_present_exactly_when_no_sort_was_chosen(self):
        for query in self._QUERIES:
            result = match_spatial_qualifier(query)
            assert (result.sort is None) == (result.reason is not None), query

    def test_every_reason_belongs_to_the_closed_reason_set(self):
        for query in self._QUERIES:
            reason = match_spatial_qualifier(query).reason
            assert reason is None or reason in SPATIAL_QUALIFIER_REASONS, query

    def test_matching_is_deterministic(self):
        for query in self._QUERIES:
            first = match_spatial_qualifier(query)
            assert [match_spatial_qualifier(query) for _ in range(5)] == [first] * 5

    def test_resolve_is_the_matchs_sort_field_and_nothing_else(self):
        for query in self._QUERIES:
            assert resolve_spatial_sort(query) == match_spatial_qualifier(query).sort


# --------------------------------------------------------------------------
# AC-SPATIAL-014 — the utterance carries the order, and only the order
# --------------------------------------------------------------------------

_LIVE_LEFT_TO_RIGHT_CHAIN = (
    "Fixture 11 + Fixture 12 + Fixture 13 + Fixture 14 + "
    "Fixture 15 + Fixture 16 + Fixture 17 + Fixture 18"
)


class TestSelectionOrderUtterance:
    """design.md §4 — the bundle, line for line."""

    def test_the_bundle_is_the_shape_design_specifies(self, bar):
        assert build_spatial_wave_commands(bar, "left_to_right") == (
            "ChangeDestination Root",
            "ClearAll",
            _LIVE_LEFT_TO_RIGHT_CHAIN,
            "Attribute 'Dimmer' At 0",
            "Step 2",
            "Attribute 'Dimmer' At 100",
            "Attribute 'Dimmer' At Phase 0 Thru 360",
            "Attribute 'Dimmer' At Speed 30",
            "ClearAll",
        )

    def test_the_chain_is_the_two_chains_a_human_watched_on_stage(self, bar):
        # progress.md §E.2.7: order A swept left->right, order B (nothing else
        # changed) swept right->left. These are those two lines.
        assert build_spatial_wave_commands(bar, "left_to_right")[2] == _LIVE_LEFT_TO_RIGHT_CHAIN
        assert build_spatial_wave_commands(bar, "right_to_left")[2] == (
            "Fixture 18 + Fixture 17 + Fixture 16 + Fixture 15 + "
            "Fixture 14 + Fixture 13 + Fixture 12 + Fixture 11"
        )

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_the_chain_matches_the_sorted_fids_element_for_element(self, bar, grid, sort):
        for analysis in (bar, grid):
            chain = build_spatial_wave_commands(analysis, sort)[2]
            emitted = tuple(int(token.split()[1]) for token in chain.split(" + "))
            assert emitted == spatial_sorted_fids(analysis, sort)

    def test_reversing_the_sort_reverses_the_chain(self, bar):
        # The live observation, in machine form: order A and order B differ by
        # nothing but direction (progress.md §E.2.7).
        forward = build_spatial_wave_commands(bar, "left_to_right")[2].split(" + ")
        backward = build_spatial_wave_commands(bar, "right_to_left")[2].split(" + ")
        assert backward == list(reversed(forward))

    def test_on_a_multi_row_rig_the_reversal_is_row_scoped(self, grid):
        # The row-scoped sorts order WITHIN each row and keep the rows in the
        # analysis's own front-to-back order (design.md §3.2). A three-row rig
        # therefore reverses row by row, not end to end — three simultaneous
        # sweeps, not one long one. Asserting a global reversal here would be
        # asserting a bar's behaviour on a grid, which is the exact conflation
        # REQ-SPATIAL-011 exists to prevent.
        forward = build_spatial_wave_commands(grid, "left_to_right")[2].split(" + ")
        backward = build_spatial_wave_commands(grid, "right_to_left")[2].split(" + ")
        assert backward != list(reversed(forward))

        offset = 0
        for row in grid.rows:
            segment = slice(offset, offset + len(row.fixtures))
            assert backward[segment] == list(reversed(forward[segment])), row.index
            offset += len(row.fixtures)
        assert offset == len(forward), "every fixture must belong to exactly one row segment"

    def test_the_same_instruction_differs_between_a_bar_and_a_grid(self, bar, grid):
        # Scenario 1, on the utterance surface: one sort name, two rigs, two
        # different chains. If these ever match, the SPEC has no purpose.
        assert bar.row_count == 1
        assert grid.row_count == 3
        assert (
            build_spatial_wave_commands(bar, "diagonal")[2]
            != build_spatial_wave_commands(grid, "diagonal")[2]
        )

    def test_the_bundle_opens_at_root_and_clears_at_both_ends(self, bar):
        commands = build_spatial_wave_commands(bar, "center_out")
        assert commands[0] == "ChangeDestination Root"
        assert commands[1] == "ClearAll"
        assert commands[-1] == "ClearAll"

    def test_building_is_deterministic(self, grid):
        first = build_spatial_wave_commands(grid, "diagonal")
        assert [build_spatial_wave_commands(grid, "diagonal") for _ in range(3)] == [first] * 3

    def test_the_selection_chain_helper_preserves_the_order_handed_to_it(self):
        # The chain is the direction, so the builder must not re-sort or dedupe.
        assert build_spatial_selection_chain((18, 11, 14)) == (
            "Fixture 18 + Fixture 11 + Fixture 14"
        )


class TestTwoStepPhaser:
    """The measured difference between motion and a lit, motionless stage."""

    def test_the_phaser_is_built_from_two_steps_around_a_step_line(self, bar):
        commands = build_spatial_wave_commands(bar, "left_to_right")
        low = f"Attribute '{SPATIAL_WAVE_ATTRIBUTE}' At {SPATIAL_WAVE_LOW}"
        high = f"Attribute '{SPATIAL_WAVE_ATTRIBUTE}' At {SPATIAL_WAVE_HIGH}"
        assert commands.index(low) < commands.index("Step 2") < commands.index(high)

    def test_the_phase_fan_comes_after_both_step_values(self, bar):
        # M0 emitted one static value and then the phase fan: every line
        # answered ok and the stage stood still (progress.md §E.2.7). The fan
        # must have two steps behind it before it is spread.
        commands = build_spatial_wave_commands(bar, "left_to_right")
        fan = f"Attribute '{SPATIAL_WAVE_ATTRIBUTE}' At Phase {SPATIAL_WAVE_PHASE_SPAN}"
        high = f"Attribute '{SPATIAL_WAVE_ATTRIBUTE}' At {SPATIAL_WAVE_HIGH}"
        assert commands.index(high) < commands.index(fan)

    def test_the_two_step_values_are_distinct(self):
        # Two steps holding the SAME value is one static value wearing a hat.
        assert SPATIAL_WAVE_LOW != SPATIAL_WAVE_HIGH

    def test_the_speed_line_carries_the_requested_rate(self, bar):
        assert build_spatial_wave_commands(bar, "left_to_right", speed=90)[-2] == (
            f"Attribute '{SPATIAL_WAVE_ATTRIBUTE}' At Speed 90"
        )
        assert build_spatial_wave_commands(bar, "left_to_right")[-2] == (
            f"Attribute '{SPATIAL_WAVE_ATTRIBUTE}' At Speed {SPATIAL_WAVE_DEFAULT_SPEED}"
        )


def _coordinate_renderings(value: float) -> set[str]:
    """Every plausible way a leaked coordinate could be written into a command.

    ``abs`` is included because a coordinate that lost its sign on the way out
    is still a coordinate — and losing the sign is a measured failure mode of
    this console's own write path (progress.md §E.2.6a).
    """
    renderings = set()
    for candidate in (value, abs(value)):
        renderings.update(
            {
                repr(candidate),
                str(candidate),
                f"{candidate:g}",
                f"{candidate:.1f}",
                f"{candidate:.2f}",
            }
        )
    return renderings


def _coordinate_leaks(commands, analysis) -> list[str]:
    text = "\n".join(commands)
    return [
        f"{rendering!r} (fixture {fixture.fid} {axis})"
        for fixture in analysis.fixtures
        for axis, value in (("x", fixture.x), ("y", fixture.y), ("z", fixture.z))
        for rendering in _coordinate_renderings(value)
        if rendering in text
    ]


class TestNoCoordinateReachesACommand:
    """AC-SPATIAL-014 — the static half of this SPEC's premise.

    Direction is carried by ORDER alone. A coordinate in a programming command
    is meaningless to MA3 and invisible in every log, because the stage effect
    has no machine channel (spec.md §C.1).
    """

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_no_coordinate_of_any_fixture_appears_in_any_command(self, grid, sort):
        # The grid golden has no whole-number coordinate on any axis, so every
        # rendering scanned for is unambiguous.
        assert _coordinate_leaks(build_spatial_wave_commands(grid, sort), grid) == []

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_no_coordinate_of_the_live_rig_appears_in_any_command(self, bar, sort):
        commands = build_spatial_wave_commands(bar, sort)
        for fixture in bar.fixtures:
            for rendering in ("-3.5", "3.5", "-0.5", "0.5", f"{fixture.x:g}"):
                if "." in rendering:
                    assert rendering not in "\n".join(commands)

    def test_the_leak_scan_would_catch_a_leak(self, grid):
        # Non-vacuity: the two assertions above are only evidence if the scan
        # can fail. Feed it a line that DOES carry a coordinate.
        leaked = (*build_spatial_wave_commands(grid, "left_to_right"), "Attribute 'Pan' At -4.25")
        assert _coordinate_leaks(leaked, grid) != []

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_no_command_contains_a_decimal_point_at_all(self, bar, grid, sort):
        # A coordinate is a float; every number this bundle legitimately writes
        # is an integer. The absence of `.` is therefore a whole class of leak
        # ruled out at once, including renderings the scan above does not guess.
        for analysis in (bar, grid):
            for command in build_spatial_wave_commands(analysis, sort):
                assert "." not in command, command

    def test_the_bundle_names_no_axis_property(self, grid):
        # posx/posy/posz belong to the WRITE path. A choreography bundle that
        # mentions one is writing coordinates, not ordering fixtures.
        text = "\n".join(build_spatial_wave_commands(grid, "diagonal")).lower()
        for axis_property in ("posx", "posy", "posz", "rotx", "roty", "rotz"):
            assert axis_property not in text


class TestTheBundleIsSendable:
    """Proving the strings are shippable without shipping them."""

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_every_line_passes_the_gates_structural_validator(self, bar, sort):
        for command in build_spatial_wave_commands(bar, sort):
            assert validate(command).ok, command

    @pytest.mark.parametrize("sort", SPATIAL_SORTS)
    def test_every_line_survives_the_transports_double_quote_rejection(self, grid, sort):
        # `server/bridge/protocol.py:105` rejects `"` outright, which is why the
        # attribute name is single-quoted. Running the real validator beats
        # asserting the absence of a character we happened to think of.
        for command in build_spatial_wave_commands(grid, sort):
            assert build_exec_request("m3", command)

    def test_the_transport_check_would_catch_a_double_quote(self):
        # Non-vacuity for the test above.
        from server.bridge.protocol import ProtocolError

        with pytest.raises(ProtocolError):
            build_exec_request("m3", 'Attribute "Dimmer" At 100')


class TestUtteranceRefusals:
    """What the builder refuses, rather than papers over."""

    def test_a_sort_outside_the_closed_vocabulary_raises(self, bar):
        with pytest.raises(SpatialAnalysisError, match="not a spatial sort"):
            build_spatial_wave_commands(bar, "back_to_front")

    def test_an_analysis_with_no_fixtures_raises_instead_of_emitting_a_bare_keyword(self):
        empty = analyze_spatial_records([])
        with pytest.raises(SpatialAnalysisError, match="at least one fixture"):
            build_spatial_wave_commands(empty, "left_to_right")

    def test_an_empty_chain_raises(self):
        with pytest.raises(SpatialAnalysisError, match="at least one fixture"):
            build_spatial_selection_chain(())

    @pytest.mark.parametrize("speed", [0, -30, 1.5, "30", True, None])
    def test_a_speed_that_is_not_a_positive_integer_raises(self, bar, speed):
        # `True` is in the list deliberately: it is an int to Python and would
        # otherwise be emitted as `At Speed True`.
        with pytest.raises(SpatialAnalysisError, match="positive integer"):
            build_spatial_wave_commands(bar, "left_to_right", speed=speed)

    def test_a_low_confidence_analysis_still_compiles(self):
        # The all-(0,0,0) rig is a SUCCESSFUL read of an unpositioned show
        # (progress.md §E.2.4). The layer neither hides the flag nor refuses to
        # compute; deciding whether to use the chain is the caller's job.
        unpositioned = analyze_spatial_records([_rec(fid, 0.0, 0.0, 0.0) for fid in range(1, 20)])
        assert unpositioned.low_confidence is True
        assert len(build_spatial_wave_commands(unpositioned, "left_to_right")) == 9


class TestTheRulebookTeachesWhatTheBuilderEmits:
    """The recipe the model reads and the bundle the server sends are one thing.

    Two surfaces describing the same MA3 grammar drift silently: the rulebook is
    prose the tests never execute, and the builder is code the model never
    reads. AC-SPATIAL-016 requires the asset's syntax to be live-confirmed, and
    the only live-confirmed source for it is what this builder emits.
    """

    def _recipe(self) -> list[str]:
        text = (RULEBOOK_ASSET / "32_spatial_design.md").read_text(encoding="utf-8")
        blocks = [
            block.strip().splitlines()
            for block in text.split("```")[1::2]
            if "ChangeDestination Root" in block
        ]
        assert len(blocks) == 1, "the asset must teach exactly one sort-select-phaser recipe"
        return blocks[0]

    def test_the_recipe_matches_the_emitted_bundle_line_for_line(self, bar):
        recipe = self._recipe()
        emitted = list(build_spatial_wave_commands(bar, "left_to_right"))

        # The chain is the one line the asset cannot show concretely: a fid in a
        # static asset would be a per-show binding (REQ-SPATIAL-017).
        assert recipe[2].startswith("Fixture <"), recipe[2]
        assert _PER_SHOW_ID.search(recipe[2]) is None, recipe[2]
        recipe[2] = emitted[2]
        assert recipe == emitted


class TestChoreographyLayerBoundary:
    """REQ-SPATIAL-013 — the new module is inside the pure package."""

    _IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE)

    def _imports(self) -> list[str]:
        source = SPATIAL_DIR / "choreography.py"
        assert source.exists(), "positive control: the module must exist to be scanned"
        return self._IMPORT_LINE.findall(source.read_text(encoding="utf-8"))

    def test_it_imports_no_transport_and_no_gate_surface(self):
        forbidden = ("server.bridge", "server.safety", "server.orchestrator", "pythonosc")
        assert [module for module in self._imports() if module.startswith(forbidden)] == []

    def test_it_imports_nothing_outside_the_standard_library_and_its_own_package(self):
        assert [
            module
            for module in self._imports()
            if module.split(".")[0] not in sys.stdlib_module_names
            and not module.startswith("server.spatial")
        ] == []
