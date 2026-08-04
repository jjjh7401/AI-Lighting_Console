"""TDD suite for server/spatial/naming.py (SPEC-COPILOT-GROUPGEN-001, M2).

Covers REQ-GROUPGEN-015~019 and the mutation-required AC-GROUPGEN-037
(no-arbitrary-naming) contract. Defines a minimal local stub for the
TopologyResult shape (design.md §2.2) so this suite does not import
server/spatial/topology.py, which a sibling worker is writing concurrently.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import pytest

from server.spatial import naming

# ---------------------------------------------------------------------------
# Local stub of the M1 cross-contract shape (design.md §2.2). NOT an import of
# topology.py — this suite must not depend on the sibling worker's module.
# ---------------------------------------------------------------------------

TopologyKind = Literal[
    "depth_rows",
    "lateral_split",
    "concentric",
    "vertical_levels",
    "grid",
    "bilateral_pairs",
    None,
]


@dataclass(frozen=True)
class _TopologyResultStub:
    kind: TopologyKind
    fids_by_bucket: tuple[tuple[int, ...], ...]
    low_confidence: bool
    reason: str | None = None
    grid_axes: Mapping[Literal["depth", "lateral"], tuple[tuple[int, ...], ...]] | None = None


# ---------------------------------------------------------------------------
# §4.1 depth axis
# ---------------------------------------------------------------------------


def test_depth_2way_split_is_downstage_upstage():
    assert naming.name_depth_bucket(0, 2) == "GEO Downstage"
    assert naming.name_depth_bucket(1, 2) == "GEO Upstage"


def test_depth_3way_split_adds_center():
    assert naming.name_depth_bucket(0, 3) == "GEO Downstage"
    assert naming.name_depth_bucket(1, 3) == "GEO Center"
    assert naming.name_depth_bucket(2, 3) == "GEO Upstage"


def test_electric_fallback_orders_downstage_to_upstage():
    # index 0 is defined as the downstage-most bucket per the §2.2 bucket-order
    # contract (fids_by_bucket[0] == downstage-most). Electric numbering must
    # follow the same DS->US direction (REQ-GROUPGEN-017).
    names = [naming.name_depth_bucket(i, 5) for i in range(5)]
    assert names == [
        "GEO Electric 1",
        "GEO Electric 2",
        "GEO Electric 3",
        "GEO Electric 4",
        "GEO Electric 5",
    ]


# ---------------------------------------------------------------------------
# §4.1 / §4.2 lateral axis
# ---------------------------------------------------------------------------


def test_lateral_2way_split_is_stage_right_stage_left():
    assert naming.name_lateral_bucket(0, 2) == "GEO Stage Right"
    assert naming.name_lateral_bucket(1, 2) == "GEO Stage Left"


def test_lateral_3way_split_adds_centerline():
    assert naming.name_lateral_bucket(0, 3) == "GEO Stage Right"
    assert naming.name_lateral_bucket(1, 3) == "GEO Centerline"
    assert naming.name_lateral_bucket(2, 3) == "GEO Stage Left"


def test_lateral_names_carry_stage_reference_frame():
    # REQ-GROUPGEN-016: no bare Left/Right without a stated frame of reference.
    for total in (2, 3):
        for index in range(total):
            name = naming.name_lateral_bucket(index, total)
            if "Right" in name or "Left" in name:
                assert "Stage" in name, f"{name!r} lacks a stage reference frame"


def test_lateral_4plus_numbers_approved_tokens_outward_from_centre():
    """4+ lateral fallback reuses `Stage Right`/`Stage Left` + an ordinal.

    It must NOT name rigging hardware — spec.md §D lists Boom/FOH/Ladder/Torm
    as out-of-scope structure names, and carves out `Electric N` on the DEPTH
    axis only. Numbering runs outward from the centreline (1 = nearest centre),
    the documented direction required by REQ-GROUPGEN-017.
    """
    assert [naming.name_lateral_bucket(i, 4) for i in range(4)] == [
        "GEO Stage Right 2",
        "GEO Stage Right 1",
        "GEO Stage Left 1",
        "GEO Stage Left 2",
    ]
    # odd total keeps the single middle bucket as Centerline, never "Center"
    assert [naming.name_lateral_bucket(i, 5) for i in range(5)] == [
        "GEO Stage Right 2",
        "GEO Stage Right 1",
        "GEO Centerline",
        "GEO Stage Left 1",
        "GEO Stage Left 2",
    ]


def test_no_produced_name_ever_claims_rigging_hardware():
    """spec.md §D — coordinates cannot know a boom/FOH/ladder/torm exists.

    MUTATION: restore a `SR Boom N`-shaped lateral fallback and this test goes
    RED. Naming a hardware structure the patch does not contain persists a
    false asset in the showfile, which is the exact failure §D forbids.
    """
    produced: list[str] = []
    for total in range(2, 13):
        for index in range(total):
            produced.append(naming.name_lateral_bucket(index, total))
            produced.append(naming.name_depth_bucket(index, total))
            produced.append(naming.name_concentric_bucket(index, total))
            produced.append(naming.name_vertical_bucket(index, total))
    assert produced, "non-vacuity: the sweep must actually produce names"
    for name in produced:
        for token in _RIGGING_HARDWARE_TOKENS:
            assert token not in name, (
                f"{name!r} claims rigging hardware {token!r} — spec.md §D "
                "forbids inferring hardware structure from coordinates"
            )


def test_lateral_bucket_rejects_out_of_range_index():
    with pytest.raises(ValueError):
        naming.name_lateral_bucket(4, 4)


# ---------------------------------------------------------------------------
# §4.3 — depth Center vs lateral Centerline must never collide
# ---------------------------------------------------------------------------


def test_depth_center_and_lateral_centerline_are_distinct_strings():
    depth_center = naming.name_depth_bucket(1, 3)
    lateral_center = naming.name_lateral_bucket(1, 3)
    assert depth_center == "GEO Center"
    assert lateral_center == "GEO Centerline"
    assert depth_center != lateral_center


def test_grid_contention_produces_six_distinct_names_no_collision():
    # design.md §2.4 worked example: 3x3 grid contention -> 6 names, not 9.
    depth_names = [naming.name_depth_bucket(i, 3) for i in range(3)]
    lateral_names = [naming.name_lateral_bucket(i, 3) for i in range(3)]
    combined = depth_names + lateral_names
    assert len(combined) == 6
    assert len(set(combined)) == 6, "grid axis names must not collide"


# ---------------------------------------------------------------------------
# §4.1 concentric axis
# ---------------------------------------------------------------------------


def test_concentric_2way_split_is_inner_outer():
    assert naming.name_concentric_bucket(0, 2) == "GEO Inner"
    assert naming.name_concentric_bucket(1, 2) == "GEO Outer"


def test_concentric_3way_split_adds_mid():
    assert naming.name_concentric_bucket(0, 3) == "GEO Inner"
    assert naming.name_concentric_bucket(1, 3) == "GEO Mid"
    assert naming.name_concentric_bucket(2, 3) == "GEO Outer"


def test_concentric_fallback_orders_inner_to_outer():
    names = [naming.name_concentric_bucket(i, 4) for i in range(4)]
    assert names == ["GEO Ring 1", "GEO Ring 2", "GEO Ring 3", "GEO Ring 4"]


# ---------------------------------------------------------------------------
# §4.1 vertical axis
# ---------------------------------------------------------------------------


def test_vertical_2way_split_is_low_high_and_claims_no_lighting_system():
    """v0.3.0: ``Low Side``/``High Side`` was replaced by ``Low``/``High``.

    Two independent reasons, both live-verified:
      1. ``server/looks/roles.py``'s 사이드 role matches the hint ``Side`` on a
         word boundary, so ``GEO Low Side`` resolved to that role — the role
         resolver would mis-aim on an auto-generated geometry group.
      2. On stage "low side"/"high side" name sidelight POSITIONS, i.e. a
         lighting system. REQ-GROUPGEN-019 forbids borrowing system vocabulary;
         coordinates only know "lower" and "higher".

    MUTATION: restore the ``Side``-suffixed pair and
    ``test_no_geo_name_matches_any_looks_role_hint`` goes RED.
    """
    assert naming.name_vertical_bucket(0, 2) == "GEO Low"
    assert naming.name_vertical_bucket(1, 2) == "GEO High"


def test_vertical_fallback_orders_up_to_down():
    # design.md §4.1 table: numbered fallback reads "위→아래" (up -> down),
    # i.e. the highest bucket (last index, per the low->high bucket-order
    # contract) is Level 1.
    names = [naming.name_vertical_bucket(i, 4) for i in range(4)]
    assert names == ["GEO Level 4", "GEO Level 3", "GEO Level 2", "GEO Level 1"]


# ---------------------------------------------------------------------------
# §4.4 — 9-cell composite vocabulary defined but statically unreachable in v1
# ---------------------------------------------------------------------------


def test_grid_9cell_vocab_is_defined_as_closed_set():
    assert naming.GRID_9CELL_VOCAB == (
        "DSR",
        "DSC",
        "DSL",
        "CSR",
        "CS",
        "CSL",
        "USR",
        "USC",
        "USL",
    )


def test_name_grid_9cell_exists_and_is_addressable():
    # Defined (not deleted) per design.md §4.4 — callable directly, but no
    # production caller in this module reaches it (see next test).
    assert naming.name_grid_9cell(0, 0) == "GEO DSR"
    assert naming.name_grid_9cell(2, 2) == "GEO USL"


def test_name_grid_9cell_is_unreachable_from_any_other_public_function():
    # Static reachability check: no OTHER public function's source references
    # name_grid_9cell — it is dead-but-defined, never invoked by a production
    # code path (design.md §4.4 / §2.4).
    module_source_by_function = {
        fn_name: inspect.getsource(fn)
        for fn_name, fn in vars(naming).items()
        if inspect.isfunction(fn)
        and fn.__module__ == naming.__name__
        and fn_name != "name_grid_9cell"
    }
    for fn_name, source in module_source_by_function.items():
        assert "name_grid_9cell(" not in source, (
            f"{fn_name} calls name_grid_9cell — must remain unreachable in v1 (D-Q2)"
        )


# ---------------------------------------------------------------------------
# §D-Q3 — GEO prefix on every generated name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "produced",
    [
        naming.name_depth_bucket(0, 2),
        naming.name_depth_bucket(1, 3),
        naming.name_depth_bucket(0, 5),
        naming.name_lateral_bucket(0, 2),
        naming.name_lateral_bucket(1, 3),
        naming.name_lateral_bucket(0, 4),
        naming.name_lateral_bucket(3, 5),
        naming.name_concentric_bucket(0, 2),
        naming.name_concentric_bucket(1, 3),
        naming.name_concentric_bucket(0, 4),
        naming.name_vertical_bucket(0, 2),
        naming.name_vertical_bucket(0, 4),
        naming.name_grid_9cell(0, 0),
    ],
)
def test_every_generated_name_carries_geo_prefix(produced):
    assert produced.startswith("GEO ")


# ---------------------------------------------------------------------------
# §D-Q10 — bilateral_pairs must never be consumed by naming.py
# ---------------------------------------------------------------------------


def test_naming_module_never_references_bilateral_pairs():
    import pathlib

    source = pathlib.Path(naming.__file__).read_text(encoding="utf-8")
    assert "bilateral_pairs" not in source


# ---------------------------------------------------------------------------
# REQ-GROUPGEN-019 — no functional/role vocabulary borrowed into constants
# ---------------------------------------------------------------------------


def test_naming_module_has_no_functional_role_vocabulary():
    """REQ-GROUPGEN-019 — functional/system vocabulary must never reach a NAME.

    v0.3.0: this used to grep the module SOURCE, which contradicted its own
    comment ("prose mentioning them … is out of scope") and made it impossible
    to document WHY a term is banned — recording the ``Low Side`` -> ``Low``
    correction tripped it. Source-grepping is also weaker than it looks: an
    f-string could assemble a forbidden token without the literal appearing.

    So the guard now checks what actually matters — every value a public naming
    function can RETURN, plus the closed-vocabulary constants themselves.
    """
    forbidden = re.compile(
        r"front light|backlight|sidelight|\bkey\b|\bfill\b|\bwash\b|\bspecial\b",
        re.IGNORECASE,
    )

    produced: list[str] = []
    for total in range(2, 13):
        for index in range(total):
            produced.append(naming.name_depth_bucket(index, total))
            produced.append(naming.name_lateral_bucket(index, total))
            produced.append(naming.name_concentric_bucket(index, total))
            produced.append(naming.name_vertical_bucket(index, total))
    produced.extend(naming.GRID_9CELL_VOCAB)
    produced.extend(
        naming._DEPTH_2
        + naming._DEPTH_3
        + naming._LATERAL_2
        + naming._LATERAL_3
        + naming._CONCENTRIC_2
        + naming._CONCENTRIC_3
        + naming._VERTICAL_2
    )

    assert produced, "non-vacuity: the sweep must actually produce names"
    for value in produced:
        match = forbidden.search(value)
        assert match is None, (
            f"forbidden functional vocabulary {match.group(0)!r} reaches the "
            f"produced name {value!r} (REQ-GROUPGEN-019)"
        )


def test_naming_module_has_no_bare_front_back_literals():
    import pathlib

    source = pathlib.Path(naming.__file__).read_text(encoding="utf-8")
    assert '"Front"' not in source
    assert '"Back"' not in source


# ---------------------------------------------------------------------------
# AC-GROUPGEN-037 — no-arbitrary-naming, mutation-required
# ---------------------------------------------------------------------------

_CLOSED_SET = frozenset(
    naming._DEPTH_2
    + naming._DEPTH_3
    + naming._LATERAL_2
    + naming._LATERAL_3
    + naming._CONCENTRIC_2
    + naming._CONCENTRIC_3
    + naming._VERTICAL_2
    + naming.GRID_9CELL_VOCAB
)

_FALLBACK_RE = re.compile(r"^(Electric|Ring|Level|Stage Right|Stage Left) \d+$")

# spec.md §D "Out of Scope — 리깅 하드웨어 위치 판정": these are hardware
# STRUCTURE names absent from the patch. `Electric N` is the SINGLE carved-out
# borrowing and only on the depth axis. A produced name must never claim one.
_RIGGING_HARDWARE_TOKENS = ("Boom", "FOH", "Ladder", "Torm")


def _assert_is_closed_set_or_fallback(produced: str) -> None:
    assert produced.startswith(naming.GEO_PREFIX), f"{produced!r} missing GEO prefix"
    body = produced[len(naming.GEO_PREFIX) :]
    assert body in _CLOSED_SET or _FALLBACK_RE.match(body), (
        f"{produced!r} is neither a closed-vocabulary element nor a documented numbered fallback"
    )


def test_no_group_name_is_ever_constructed_from_arbitrary_input():
    """AC-GROUPGEN-037 — full contract, parts (a) and (b).

    (a) Exhaustive cross-check: every public naming function's output is
        either a closed-set element or a documented numbered fallback.
    (b) Adversarial input: feeding attacker-controlled fixture-name-shaped
        strings into the naming surface (index/total only — naming.py's
        public API takes no free-form string input) never lets a fragment of
        that input reach the produced name, because the API has no channel
        for it to enter through.
    """
    adversarial_inputs = ["Copilot MMX 3", "'; Label Group 1 'x", "", "조명 1호기 ☃"]

    # (a) exhaustive closed-set-or-fallback check across the full public surface.
    for total in (2, 3, 4, 5, 12):
        for index in range(total):
            _assert_is_closed_set_or_fallback(naming.name_depth_bucket(index, total))
            _assert_is_closed_set_or_fallback(naming.name_concentric_bucket(index, total))
            _assert_is_closed_set_or_fallback(naming.name_vertical_bucket(index, total))
        for index in range(total):
            _assert_is_closed_set_or_fallback(naming.name_lateral_bucket(index, total))
    for depth_idx in range(3):
        for lateral_idx in range(3):
            _assert_is_closed_set_or_fallback(naming.name_grid_9cell(depth_idx, lateral_idx))

    # (b) naming.py's public functions accept only (index, total) — there is
    # no parameter through which an adversarial fixture-name-shaped string
    # could be threaded into a returned name.
    # Confirm no public function even accepts a free-form str parameter that
    # could carry such a fragment into a produced name.
    for fn_name, fn in vars(naming).items():
        if not (inspect.isfunction(fn) and fn.__module__ == naming.__name__):
            continue
        if fn_name.startswith("_"):
            continue
        sig = inspect.signature(fn)
        for param in sig.parameters.values():
            if param.annotation is str:
                pytest.fail(
                    f"{fn_name} accepts a free-form str parameter {param.name!r} — "
                    "AC-037 requires no channel for fixture-derived input to reach "
                    "a produced name"
                )

    for adversarial in adversarial_inputs:
        for produced in (
            naming.name_depth_bucket(0, 2),
            naming.name_lateral_bucket(0, 3),
            naming.name_concentric_bucket(0, 4),
            naming.name_vertical_bucket(0, 4),
            naming.name_grid_9cell(0, 0),
        ):
            assert adversarial == "" or adversarial not in produced


def test_mutation_fstring_interpolation_of_closed_lookup_breaks_the_contract():
    """AC-GROUPGEN-037 part (c) — mutation proof.

    Simulates the forbidden mutation (`f"GEO {bucket_label}"` where
    bucket_label is input-derived) as an isolated local function and proves
    that the same closed-set-or-fallback assertion used above correctly goes
    RED against it. This demonstrates the real production assertion is not
    vacuously true — a naming function built by interpolating an
    attacker-controlled label WOULD be caught.
    """

    def mutated_name_depth_bucket(bucket_label: str) -> str:
        # The forbidden pattern named in AC-037: f-string interpolation of an
        # input-derived label instead of a closed-set lookup.
        return f"GEO {bucket_label}"

    adversarial_label = "Copilot MMX 3"
    produced = mutated_name_depth_bucket(adversarial_label)

    with pytest.raises(AssertionError):
        _assert_is_closed_set_or_fallback(produced)

    # And the adversarial-input-not-in-output guarantee is also violated by
    # the mutation, proving part (b)'s guard is load-bearing too.
    assert adversarial_label in produced


# ---------------------------------------------------------------------------
# §4.5 — stage-left sign convention documented at a single point
# ---------------------------------------------------------------------------


def test_stage_left_sign_convention_is_documented():
    assert naming.STAGE_LEFT_IS_POSITIVE_X is True
