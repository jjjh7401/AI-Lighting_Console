"""M4 — the instantiation bundle builder (AC-LOOKLIB-007 / 016 / 018).

The rig shapes here are assembled by the PRODUCER's own helpers
(``rig_object`` / ``rig_section`` / ``drill_into`` from
``server.orchestrator.tools``), never by hand. A hand-written dict keeps passing
after the console shape changes, which makes it a fixture rather than a boundary
test — M3 established this and M4 inherits it.

Console contact: zero. Everything below is in-memory.
"""

from __future__ import annotations

import re

import pytest

from server.looks.instantiate import (
    CAPTURE_PER_FAMILY,
    CAPTURE_SHARED,
    CONFLICT,
    NO_FREE_SLOT,
    POOL_UNADDRESSABLE,
    POOL_UNRESOLVED,
    LookInstantiationError,
    build_instantiation,
    instantiate_look,
    resolve_pools,
)
from server.looks.loader import load_library_from_dir
from server.looks.resolver import resolve_roles
from server.looks.roles import AMBIGUOUS, NO_MATCH
from server.looks.schema import IN_SCOPE_POOL_FAMILIES, AttributeValue, Look
from server.orchestrator.tools import (
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    RIG_DRILLDOWN_QUERY_CAP,
    drill_into,
    rig_object,
    rig_section,
)

# -- rig assembly -------------------------------------------------------------
#
# Responder wire shape: a child carries "i" ONLY when the responder positively
# established that slot (tools.py:196-205). Omitting "i" here is how a rig says
# "this exists and I could not number it", which is a state the look layer must
# never paper over.


class _FakeStatePort:
    """Answers the drill queries ``drill_into`` makes, and nothing else."""

    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise RuntimeError(f"no such path: {path}")
        return self._tree[path]


def _section(children: list[dict], *, truncated: bool = False) -> dict:
    objects = [rig_object(c) for c in children]
    payload = {"truncated": truncated, "node": {"childCount": len(children)}}
    return rig_section(objects, payload)


def _groups(*entries: tuple[int | None, str]) -> dict:
    children = [({"name": name} if no is None else {"i": no, "name": name}) for no, name in entries]
    return _section(children)


DEFAULT_POOL_NAMES = (
    (1, "Dimmer"),
    (2, "Position"),
    (3, "Gobo"),
    (4, "Color"),
    (5, "Beam"),
    (6, "Focus"),
)


def _pools(
    pools: tuple[tuple[int | None, str], ...] = DEFAULT_POOL_NAMES,
    *,
    contents: dict[int, list[dict]] | None = None,
    budget: int = RIG_DRILLDOWN_QUERY_CAP,
) -> dict:
    """Build a preset_pools section and drill it exactly as get_rig_context does."""
    contents = contents or {}
    entry = _section([({"name": n} if no is None else {"i": no, "name": n}) for no, n in pools])
    tree = {
        f"DataPool/PresetPools/{no}": {"children": contents.get(no, [])}
        for no, _ in pools
        if no is not None
    }
    port = _FakeStatePort(tree)
    drill_into(port, entry["objects"], "DataPool/PresetPools", entry, budget)
    return entry


def _preset(no: int | None, name: str) -> dict:
    return {"name": name} if no is None else {"i": no, "name": name}


# -- looks --------------------------------------------------------------------


def _look(
    *,
    look_id: str = "test-look",
    display_name: str = "테스트 룩",
    roles: tuple[str, ...] = ("백라이트",),
    attributes: tuple[tuple[str, float], ...] = (
        ("Dimmer", 80),
        ("ColorRGB_R", 100),
        ("ColorRGB_G", 25),
        ("ColorRGB_B", 0),
    ),
) -> Look:
    return Look(
        look_id=look_id,
        display_name=display_name,
        genre="rock",
        dynamics=4,
        roles=roles,
        attributes=tuple(AttributeValue(name=n, value=v) for n, v in attributes),
    )


FOUR_FAMILY_ATTRIBUTES = (
    ("Dimmer", 40),
    ("ColorRGB_R", 100),
    ("ColorRGB_G", 82),
    ("ColorRGB_B", 60),
    ("Iris", 32),
    ("Zoom", 12),
)


def _plan(look: Look, groups: dict, pools: dict, **kwargs):
    return instantiate_look(look, groups_section=groups, preset_pools_section=pools, **kwargs)


def _stores(commands) -> list[str]:
    return [c for c in commands if c.startswith("Store ")]


def _cycles(commands) -> list[list[str]]:
    """Split a bundle into its ClearAll-delimited capture cycles."""
    cycles: list[list[str]] = []
    current: list[str] | None = None
    for command in commands:
        if command == "ClearAll":
            if current is not None:
                cycles.append(current)
            current = []
            continue
        if current is not None:
            current.append(command)
    return [c for c in cycles if c]


# =============================================================================
# Pool resolution — the M0 follow-up (renamed / unnumbered / undrilled pools)
# =============================================================================


class TestPoolIndex:
    def test_the_four_in_scope_families_resolve_from_the_default_pool_names(self):
        index = resolve_pools(_pools())
        for family in IN_SCOPE_POOL_FAMILIES:
            binding = index.bindings[family]
            assert binding.reason is None
            assert binding.number is not None

    def test_pool_numbers_come_from_the_section_and_not_from_a_literal(self):
        # M0 measured 1/4/5/6 on ONE showfile. A build that hardcodes those
        # numbers passes against that rig and aims at the wrong pools on any
        # other, so the fixture deliberately does NOT use them (AP-16).
        shuffled = ((31, "Dimmer"), (32, "Color"), (33, "Beam"), (34, "Focus"))
        index = resolve_pools(_pools(shuffled))
        assert [index.bindings[f].number for f in IN_SCOPE_POOL_FAMILIES] == [31, 32, 33, 34]

    def test_a_renamed_pool_is_reported_unresolved_and_never_guessed(self):
        renamed = ((1, "Dimmer"), (4, "팔레트"), (5, "Beam"), (6, "Focus"))
        index = resolve_pools(_pools(renamed))
        assert index.bindings["Color"].reason == POOL_UNRESOLVED
        assert index.bindings["Color"].number is None
        # The neighbouring pools are untouched: one rename is not a rig failure.
        assert index.bindings["Dimmer"].reason is None

    def test_a_missing_pool_is_unresolved_too(self):
        index = resolve_pools(_pools(((1, "Dimmer"), (4, "Color"))))
        assert index.bindings["Beam"].reason == POOL_UNRESOLVED
        assert index.bindings["Focus"].reason == POOL_UNRESOLVED

    def test_a_pool_the_responder_could_not_number_is_unaddressable_not_unresolved(self):
        # Same split M3 made for groups: "there is no Color pool" and "there is
        # one and it has no address" are different facts with different fixes.
        index = resolve_pools(_pools(((1, "Dimmer"), (None, "Color"), (5, "Beam"), (6, "Focus"))))
        assert index.bindings["Color"].reason == POOL_UNADDRESSABLE
        assert index.bindings["Color"].number is None
        assert index.bindings["Color"].name == "Color"

    def test_pool_name_matching_is_case_insensitive(self):
        index = resolve_pools(_pools(((1, "DIMMER"), (4, "color"), (5, "Beam"), (6, "Focus"))))
        assert index.bindings["Dimmer"].number == 1
        assert index.bindings["Color"].number == 4

    def test_a_pool_name_that_merely_contains_a_family_word_does_not_resolve(self):
        # "Color Fx Backup" is not the Color pool. Substring matching here would
        # aim stores at whatever pool happened to be named nearby.
        index = resolve_pools(
            _pools(
                (
                    (1, "Dimmer"),
                    (4, "Color Fx Backup"),
                )
            )
        )
        assert index.bindings["Color"].reason == POOL_UNRESOLVED

    @pytest.mark.parametrize("reason", [REASON_UNRESOLVED, REASON_UNREACHABLE])
    def test_an_unavailable_section_propagates_its_own_reason_verbatim(self, reason):
        index = resolve_pools({"reason": reason})
        assert index.unavailable_reason == reason
        for family in IN_SCOPE_POOL_FAMILIES:
            assert index.bindings[family].reason == reason

    def test_a_drilled_empty_pool_is_observed_empty_not_unknown(self):
        index = resolve_pools(_pools())
        assert index.bindings["Color"].occupied == ()

    def test_an_undrilled_pool_reports_unobserved_occupancy_rather_than_empty(self):
        # Budget 2 opens the first two pools only; the rest are never queried,
        # and an unopened pool says nothing about its contents.
        index = resolve_pools(_pools(budget=2))
        assert index.bindings["Dimmer"].occupied == ()
        assert index.bindings["Color"].occupied is None

    def test_a_pool_whose_drill_failed_reports_unobserved_occupancy(self):
        entry = _section([{"i": 1, "name": "Dimmer"}, {"i": 4, "name": "Color"}])
        port = _FakeStatePort({"DataPool/PresetPools/1": {"children": []}})
        drill_into(port, entry["objects"], "DataPool/PresetPools", entry, 8)
        index = resolve_pools(entry)
        assert index.bindings["Dimmer"].occupied == ()
        assert index.bindings["Color"].occupied is None

    def test_a_preset_without_a_slot_number_makes_the_whole_pool_unobservable(self):
        # One un-numbered preset means SOME slot is taken and we cannot say
        # which, so no slot in that pool can be claimed free.
        index = resolve_pools(_pools(contents={4: [_preset(1, "A"), _preset(None, "B")]}))
        assert index.bindings["Color"].occupied is None

    def test_a_malformed_pool_entry_is_ignored_rather_than_crashing(self):
        # The section is console-shaped data; a non-mapping entry must not take
        # the whole resolve down with it (M3's TestMalformedEntry, pool side).
        section = _pools(((1, "Dimmer"),))
        section["objects"].append("not-a-mapping")
        index = resolve_pools(section)
        assert index.bindings["Dimmer"].number == 1
        assert index.bindings["Color"].reason == POOL_UNRESOLVED

    def test_a_malformed_preset_entry_makes_the_pool_unobservable(self):
        # Not "ignore the bad entry and carry on": something IS in that pool and
        # its slot is unreadable, so no slot in it can be claimed free.
        section = _pools(((1, "Dimmer"),), contents={1: [_preset(1, "A")]})
        section["objects"][0]["contents"].append("not-a-mapping")
        index = resolve_pools(section)
        assert index.bindings["Dimmer"].occupied is None

    def test_occupied_slots_are_read_from_the_pool_contents(self):
        index = resolve_pools(_pools(contents={4: [_preset(1, "A"), _preset(7, "B")]}))
        assert index.bindings["Color"].occupied == (1, 7)
        assert index.bindings["Color"].labels == ("A", "B")


# =============================================================================
# Bundle discipline — string-level invariants (design.md §6.3)
# =============================================================================


class TestBundleDiscipline:
    @pytest.fixture
    def bundle(self):
        look = _look(roles=("백라이트", "프론트"), attributes=FOUR_FAMILY_ATTRIBUTES)
        return _plan(look, _groups((11, "Back"), (12, "Front")), _pools()).commands

    def test_the_destination_is_the_first_command(self, bundle):
        assert bundle[0] == "ChangeDestination Root"

    def test_the_destination_is_issued_exactly_once(self, bundle):
        assert bundle.count("ChangeDestination Root") == 1

    def test_every_capture_cycle_opens_with_clearall(self, bundle):
        # Everything after the destination line lives inside a ClearAll-opened
        # cycle: leftover programmer values TRACK into the next capture
        # (31_choreography_patterns.md:40-41).
        assert bundle[1] == "ClearAll"
        body = bundle[1:]
        for index, command in enumerate(body):
            if command.startswith("Group "):
                assert body[index - 1] == "ClearAll"

    def test_the_bundle_ends_with_clearall(self, bundle):
        assert bundle[-1] == "ClearAll"

    def test_every_store_is_immediately_followed_by_its_own_label(self, bundle):
        for index, command in enumerate(bundle):
            if not command.startswith("Store Preset "):
                continue
            target = command.removeprefix("Store Preset ")
            assert bundle[index + 1].startswith(f"Label Preset {target} '")

    def test_no_store_runs_outside_a_clearall_delimited_cycle(self, bundle):
        # A Store that is not enclosed by ClearAll on both sides captures
        # whatever the previous cycle left behind.
        for cycle in _cycles(bundle[1:]):
            assert any(c.startswith("Store ") for c in cycle) == any(
                c.startswith("Group ") for c in cycle
            )
        assert bundle[-1] == "ClearAll"

    def test_overwrite_is_absent_case_insensitively(self, bundle):
        # AP-13: the runtime matches case-insensitively (ruleset.py:47,
        # classify.py:64, preview.py:100), so a case-fixed assert would pass
        # silently on a lowercase emission.
        assert not re.search(r"/overwrite", "\n".join(bundle), re.IGNORECASE)

    def test_the_overwrite_assert_would_actually_catch_a_lowercase_emission(self):
        # Control for the assert above: prove the matcher is the one that
        # catches the mutation, not the absence of any /Overwrite anywhere.
        assert re.search(r"/overwrite", "Store Preset 4.1 /Overwrite", re.IGNORECASE)
        assert re.search(r"/overwrite", "Store Preset 4.1 /overwrite", re.IGNORECASE)

    def test_no_group_appears_that_the_resolver_did_not_supply(self, bundle):
        emitted = {int(n) for c in bundle for n in re.findall(r"\b(\d+)\b", _group_operand(c))}
        assert emitted == {11, 12}

    def test_the_bundle_never_synthesises_a_fixture_range(self, bundle):
        joined = "\n".join(bundle).lower()
        assert "fixture" not in joined
        assert "thru" not in joined

    def test_each_command_is_one_line(self, bundle):
        for command in bundle:
            assert "\n" not in command
            assert command == command.strip()
            assert command

    def test_values_are_chained_with_the_validated_semicolon_form(self, bundle):
        values = [c for c in bundle if c.startswith("Attribute ")]
        assert len(values) == 1
        assert values[0].count(" ; ") == len(FOUR_FAMILY_ATTRIBUTES) - 1

    def test_integral_values_are_not_emitted_as_floats(self, bundle):
        assert "At 40 " in bundle[3] or bundle[3].endswith("At 40")
        assert ".0" not in bundle[3]

    def test_a_label_that_would_break_the_quoting_is_rejected_not_escaped(self):
        look = _look(display_name="won't fit")
        with pytest.raises(LookInstantiationError):
            _plan(look, _groups((11, "Back")), _pools())


def _group_operand(command: str) -> str:
    return command.removeprefix("Group ") if command.startswith("Group ") else ""


# =============================================================================
# The two capture shapes (M0 ASSUMPTION-14 GO + its live FALLBACK)
# =============================================================================


class TestCaptureShapes:
    LOOK = _look(roles=("백라이트",), attributes=FOUR_FAMILY_ATTRIBUTES)

    def test_the_shared_shape_captures_once_and_stores_per_pool(self):
        plan = _plan(self.LOOK, _groups((11, "Back")), _pools(), shape=CAPTURE_SHARED)
        cycles = _cycles(plan.commands[1:])
        assert len(cycles) == 1
        assert len([c for c in cycles[0] if c.startswith("Group ")]) == 1
        assert len(_stores(plan.commands)) == 4

    def test_the_per_family_shape_isolates_one_capture_per_store(self):
        plan = _plan(self.LOOK, _groups((11, "Back")), _pools(), shape=CAPTURE_PER_FAMILY)
        cycles = _cycles(plan.commands[1:])
        assert len(cycles) == 4
        for cycle in cycles:
            assert len(_stores(cycle)) == 1

    def test_the_per_family_shape_satisfies_clearall_after_every_store_literally(self):
        # This is the shape that does not depend on the capture semantics at
        # all: the programmer holds one family's values at store time.
        plan = _plan(self.LOOK, _groups((11, "Back")), _pools(), shape=CAPTURE_PER_FAMILY)
        commands = plan.commands
        for index, command in enumerate(commands):
            if command.startswith("Store "):
                assert commands[index + 2] == "ClearAll"

    def test_a_per_family_cycle_carries_only_that_family_values(self):
        plan = _plan(self.LOOK, _groups((11, "Back")), _pools(), shape=CAPTURE_PER_FAMILY)
        for cycle in _cycles(plan.commands[1:]):
            values = next(c for c in cycle if c.startswith("Attribute "))
            store = next(c for c in cycle if c.startswith("Store "))
            if store.startswith("Store Preset 1."):
                assert "Dimmer" in values and "ColorRGB" not in values
            if store.startswith("Store Preset 4."):
                assert "ColorRGB" in values and "Dimmer" not in values

    def test_both_shapes_are_generable_from_the_same_look_data(self):
        # REQ-LOOKLIB-001's family-splittability rule exists so the FALLBACK
        # branch costs commands, never a library rewrite.
        groups, pools = _groups((11, "Back")), _pools()
        shared = _plan(self.LOOK, groups, pools, shape=CAPTURE_SHARED)
        split = _plan(self.LOOK, groups, pools, shape=CAPTURE_PER_FAMILY)
        assert shared.created == split.created
        assert shared.skipped == split.skipped
        assert len(split.commands) > len(shared.commands)

    def test_the_shape_is_recorded_on_the_report(self):
        plan = _plan(self.LOOK, _groups((11, "Back")), _pools(), shape=CAPTURE_PER_FAMILY)
        assert plan.capture_shape == CAPTURE_PER_FAMILY

    def test_an_unknown_shape_is_rejected(self):
        with pytest.raises(LookInstantiationError):
            _plan(self.LOOK, _groups((11, "Back")), _pools(), shape="whatever")


# =============================================================================
# Slot search
# =============================================================================


class TestSlotSearch:
    def test_the_lowest_free_slot_is_chosen(self):
        plan = _plan(
            _look(attributes=(("Dimmer", 50),)),
            _groups((11, "Back")),
            _pools(contents={1: [_preset(1, "A"), _preset(2, "B")]}),
        )
        assert plan.created[0].slot == 3

    def test_a_gap_below_the_occupied_slots_is_used(self):
        plan = _plan(
            _look(attributes=(("Dimmer", 50),)),
            _groups((11, "Back")),
            _pools(contents={1: [_preset(2, "A"), _preset(3, "B")]}),
        )
        assert plan.created[0].slot == 1

    def test_the_stored_pool_number_comes_from_the_rig_not_from_a_literal(self):
        # AC-018 (a) + AP-16, at the BUNDLE layer rather than the index layer.
        # M0 measured Dimmer/Color/Beam/Focus at 1/4/5/6 on one showfile, and a
        # build that reaches for those literals passes every test written
        # against that rig while aiming at the wrong pools on any other. The
        # numbers here are deliberately nothing like the measured ones.
        pools = _pools(((31, "Dimmer"), (32, "Color"), (33, "Beam"), (34, "Focus")))
        plan = _plan(_look(attributes=FOUR_FAMILY_ATTRIBUTES), _groups((11, "Back")), pools)
        assert [c.pool for c in plan.created] == [31, 32, 33, 34]
        assert "Store Preset 31.1" in plan.commands
        assert "Store Preset 34.1" in plan.commands
        assert not any(c.startswith("Store Preset 4.") for c in plan.commands)

    def test_an_occupied_slot_is_never_a_store_target(self):
        pools = _pools(contents={1: [_preset(1, "A"), _preset(2, "B"), _preset(3, "C")]})
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        assert "Store Preset 1.1" not in plan.commands
        assert "Store Preset 1.2" not in plan.commands
        assert "Store Preset 1.3" not in plan.commands

    def test_unobserved_occupancy_is_skipped_rather_than_assumed_free(self):
        # Slot 1 LOOKS free here only because nothing was read. Claiming it
        # would be the preset-pool version of inventing a group.
        pools = _pools(budget=0)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        assert plan.created == ()
        assert [s.reason for s in plan.skipped] == [NO_FREE_SLOT]
        assert _stores(plan.commands) == []

    def test_the_slot_search_issues_no_console_queries_of_its_own(self):
        # The search consumes the drilldown get_rig_context already paid for
        # (tools.py:88 cap); it does not open a second query budget.
        entry = _section([{"i": 1, "name": "Dimmer"}])
        port = _FakeStatePort({"DataPool/PresetPools/1": {"children": []}})
        drill_into(port, entry["objects"], "DataPool/PresetPools", entry, 8)
        before = len(port.queried)
        resolve_pools(entry)
        _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), entry)
        assert len(port.queried) == before


# =============================================================================
# Conflict — the skip unit is one preset store, never one look (AP-15)
# =============================================================================


class TestConflict:
    def test_a_pool_already_holding_this_looks_label_is_skipped(self):
        pools = _pools(contents={1: [_preset(1, "테스트 룩")]})
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        assert plan.created == ()
        assert [s.reason for s in plan.skipped] == [CONFLICT]
        assert _stores(plan.commands) == []

    def test_the_label_conflict_check_is_case_insensitive(self):
        pools = _pools(contents={1: [_preset(1, "STAGE WASH")]})
        look = _look(display_name="Stage Wash", attributes=(("Dimmer", 50),))
        plan = _plan(look, _groups((11, "Back")), pools)
        assert [s.reason for s in plan.skipped] == [CONFLICT]

    def test_a_partial_conflict_creates_one_and_skips_one(self):
        # AC-018 (c): Color slot free, Dimmer already carries this look.
        # A look-unit implementation cannot express this — it reports either
        # "1 skipped, 0 created" or "0 skipped", and both lie.
        pools = _pools(contents={1: [_preset(1, "테스트 룩")], 4: []})
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        plan = _plan(look, _groups((11, "Back")), pools)
        assert len(plan.created) == 1
        assert plan.created[0].family == "Color"
        assert len(plan.skipped) == 1
        assert plan.skipped[0].family == "Dimmer"
        assert plan.skipped[0].reason == CONFLICT

    def test_the_skip_count_is_preset_stores_not_looks(self):
        pools = _pools(contents={1: [_preset(1, "테스트 룩")], 4: [_preset(1, "테스트 룩")]})
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        plan = _plan(look, _groups((11, "Back")), pools)
        assert plan.skipped_count == 2

    def test_a_skipped_store_keeps_its_pool_and_slot(self):
        pools = _pools(contents={1: [_preset(1, "테스트 룩")]})
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        skipped = plan.skipped[0]
        assert skipped.pool == 1
        assert skipped.slot == 2  # the slot it WOULD have taken

    def test_an_unrelated_label_in_the_pool_is_not_a_conflict(self):
        pools = _pools(contents={1: [_preset(1, "다른 룩")]})
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        assert len(plan.created) == 1
        assert plan.skipped == ()


# =============================================================================
# Pool-resolution failures reach the report as skips
# =============================================================================


class TestPoolFailureSkips:
    def test_a_renamed_pool_skips_that_store_and_nothing_else(self):
        pools = _pools(((1, "Dimmer"), (4, "팔레트")))
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        plan = _plan(look, _groups((11, "Back")), pools)
        assert [c.family for c in plan.created] == ["Dimmer"]
        assert [(s.family, s.reason) for s in plan.skipped] == [("Color", POOL_UNRESOLVED)]

    def test_an_unnumbered_pool_skips_with_its_own_reason(self):
        pools = _pools(((1, "Dimmer"), (None, "Color")))
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        plan = _plan(look, _groups((11, "Back")), pools)
        assert [(s.family, s.reason) for s in plan.skipped] == [("Color", POOL_UNADDRESSABLE)]

    def test_the_two_pool_failures_are_not_merged(self):
        pools = _pools(((1, "Dimmer"), (None, "Color"), (5, "빔풀"), (6, "Focus")))
        look = _look(attributes=FOUR_FAMILY_ATTRIBUTES)
        plan = _plan(look, _groups((11, "Back")), pools)
        reasons = {s.family: s.reason for s in plan.skipped}
        assert reasons == {"Color": POOL_UNADDRESSABLE, "Beam": POOL_UNRESOLVED}

    @pytest.mark.parametrize("reason", [REASON_UNRESOLVED, REASON_UNREACHABLE])
    def test_an_unavailable_pool_section_skips_every_store_with_that_reason(self, reason):
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        plan = _plan(look, _groups((11, "Back")), {"reason": reason})
        assert plan.created == ()
        assert {s.reason for s in plan.skipped} == {reason}
        assert plan.commands == ()

    def test_a_family_the_look_has_no_values_in_is_neither_created_nor_skipped(self):
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        assert [c.family for c in plan.created] == ["Dimmer"]
        assert plan.skipped == ()


# =============================================================================
# Unmapped roles — three reasons, tested one at a time (design.md §6.2)
# =============================================================================


class TestUnmappedRoles:
    def test_no_match_is_reported_on_its_own(self):
        plan = _plan(_look(roles=("배경",)), _groups((11, "Back")), _pools())
        assert [(u.role, u.reason) for u in plan.unmapped] == [("배경", NO_MATCH)]

    def test_ambiguous_is_reported_on_its_own(self):
        plan = _plan(_look(roles=("백라이트",)), _groups((11, "FrontBack Truss")), _pools())
        assert [(u.role, u.reason) for u in plan.unmapped] == [("백라이트", AMBIGUOUS)]

    def test_unaddressable_is_reported_on_its_own_and_never_folded_into_no_match(self):
        # The rig said "there IS a backlight and I could not number it".
        # Reporting no_match would erase that, and the two are fixed differently.
        plan = _plan(_look(roles=("백라이트",)), _groups((None, "Back")), _pools())
        assert [(u.role, u.reason) for u in plan.unmapped] == [("백라이트", "unaddressable")]

    def test_a_role_whose_only_candidate_is_unaddressable_emits_zero_commands(self):
        plan = _plan(_look(roles=("백라이트",)), _groups((None, "Back")), _pools())
        assert plan.commands == ()
        assert plan.created == ()

    def test_an_unaddressable_role_is_never_substituted_by_another_group(self):
        # A numbered Front sits right there. Using it would be AP-2.
        plan = _plan(_look(roles=("백라이트",)), _groups((None, "Back"), (12, "Front")), _pools())
        assert plan.commands == ()

    def test_the_three_reasons_survive_together_without_merging(self):
        look = _look(roles=("백라이트", "프론트", "배경"))
        groups = _groups((None, "Back"), (12, "FrontBack Truss"))
        plan = _plan(look, groups, _pools())
        assert {u.role: u.reason for u in plan.unmapped} == {
            "백라이트": "unaddressable",
            "프론트": AMBIGUOUS,
            "배경": NO_MATCH,
        }

    def test_only_the_looks_own_roles_are_reported(self):
        # The resolver judges all six; the report carries the ones this look
        # actually asked for, so an operator is not handed four irrelevant rows.
        plan = _plan(_look(roles=("백라이트",)), _groups((11, "Back")), _pools())
        assert plan.unmapped == ()

    def test_a_partially_mapped_look_uses_the_groups_it_did_get(self):
        plan = _plan(_look(roles=("백라이트", "배경")), _groups((11, "Back")), _pools())
        assert "Group 11" in plan.commands
        assert [u.role for u in plan.unmapped] == ["배경"]
        assert len(plan.created) >= 1

    def test_every_role_unmapped_means_an_empty_bundle_not_a_smaller_one(self):
        plan = _plan(_look(roles=("백라이트",)), _groups((99, "Nothing Here")), _pools())
        assert plan.commands == ()
        assert plan.created == ()
        assert plan.skipped == ()

    @pytest.mark.parametrize("reason", [REASON_UNRESOLVED, REASON_UNREACHABLE])
    def test_an_unavailable_groups_section_carries_its_reason_per_role(self, reason):
        plan = _plan(_look(roles=("백라이트",)), {"reason": reason}, _pools())
        assert [(u.role, u.reason) for u in plan.unmapped] == [("백라이트", reason)]
        assert plan.commands == ()

    def test_two_groups_for_one_role_are_both_selected(self):
        plan = _plan(_look(roles=("백라이트",)), _groups((11, "Back"), (14, "Rear")), _pools())
        assert "Group 11 + 14" in plan.commands

    def test_multiple_roles_contribute_their_groups_in_ascending_number_order(self):
        # Ordering is derived from the rig's own numbers, NOT from the order the
        # role vocabulary happens to list. The fixture discriminates: 백라이트
        # comes first in the vocabulary and its group is the higher number, so a
        # role-ordered implementation emits "Group 20 + 12" here.
        plan = _plan(
            _look(roles=("백라이트", "프론트")), _groups((20, "Back"), (12, "Front")), _pools()
        )
        assert "Group 12 + 20" in plan.commands

    def test_reordering_the_roles_does_not_change_the_selection_line(self):
        groups, pools = _groups((20, "Back"), (12, "Front")), _pools()
        forwards = _plan(_look(roles=("백라이트", "프론트")), groups, pools)
        backwards = _plan(_look(roles=("프론트", "백라이트")), groups, pools)
        assert forwards.commands == backwards.commands


# =============================================================================
# Drilldown cap
# =============================================================================


class TestDrilldownCap:
    def test_an_uncapped_section_reports_capped_false(self):
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        assert plan.drilldown_capped is False

    def test_the_cap_signal_is_carried_onto_the_report(self):
        # M0 G4: preset_pools alone can eat 14 of the 16-query budget shared
        # with pages, so exhaustion is a live possibility, not a non-event.
        pools = _pools(budget=2)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        assert plan.drilldown_capped is True

    def test_pools_drilled_before_the_cap_still_create(self):
        pools = _pools(budget=1)
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        plan = _plan(look, _groups((11, "Back")), pools)
        assert [c.family for c in plan.created] == ["Dimmer"]
        assert [(s.family, s.reason) for s in plan.skipped] == [("Color", NO_FREE_SLOT)]

    def test_a_capped_skip_says_the_occupancy_was_never_observed(self):
        pools = _pools(budget=0)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), pools)
        assert "observ" in plan.skipped[0].detail.lower()


# =============================================================================
# Report shape (a)-(d) — REQ-LOOKLIB-013 / AC-LOOKLIB-018
# =============================================================================


class TestReportShape:
    @pytest.fixture
    def plan(self):
        pools = _pools(
            ((1, "Dimmer"), (4, "Color"), (5, "Beam"), (6, "팔레트")),
            contents={4: [_preset(1, "네 패밀리 룩")]},
        )
        look = _look(
            display_name="네 패밀리 룩",
            roles=("백라이트", "배경"),
            attributes=FOUR_FAMILY_ATTRIBUTES,
        )
        return _plan(look, _groups((11, "Back")), pools)

    def test_a_created_presets_carry_pool_slot_and_label(self, plan):
        for created in plan.created:
            assert created.pool > 0
            assert created.slot > 0
            assert created.label == "네 패밀리 룩"
            assert created.family in IN_SCOPE_POOL_FAMILIES

    def test_b_unmapped_roles_carry_a_reason(self, plan):
        assert [(u.role, u.reason) for u in plan.unmapped] == [("배경", NO_MATCH)]

    def test_c_skipped_stores_carry_pool_slot_and_reason(self, plan):
        by_family = {s.family: s for s in plan.skipped}
        assert by_family["Color"].reason == CONFLICT
        assert by_family["Color"].pool == 4
        assert by_family["Focus"].reason == POOL_UNRESOLVED
        assert by_family["Focus"].pool is None

    def test_d_drilldown_capped_is_present_even_when_false(self, plan):
        assert plan.to_dict()["drilldown_capped"] is False

    def test_the_report_dict_carries_all_four_elements(self, plan):
        report = plan.to_dict()
        assert set(report) >= {"created", "unmapped", "skipped", "drilldown_capped"}
        assert report["skipped_count"] == len(plan.skipped)
        assert report["created"][0]["family"] in IN_SCOPE_POOL_FAMILIES
        assert report["unmapped"][0]["reason"] == NO_MATCH
        assert report["skipped"][0]["reason"] in {CONFLICT, POOL_UNRESOLVED}

    def test_a_partial_run_is_never_reported_as_a_whole_success(self, plan):
        assert plan.created
        assert plan.skipped
        assert plan.complete is False

    def test_a_clean_run_reports_complete(self):
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        assert plan.complete is True


# =============================================================================
# The shipped library, and the M0 showfile
# =============================================================================


FULL_RIG = (
    (11, "Back"),
    (12, "Front"),
    (13, "Side L"),
    (14, "Top"),
    (15, "Cyc"),
    (16, "Special"),
)


class TestShippedLibrary:
    LIBRARY = load_library_from_dir()

    def test_every_shipped_look_builds_a_disciplined_bundle(self):
        for look in self.LIBRARY.looks:
            plan = _plan(look, _groups(*FULL_RIG), _pools())
            assert plan.commands[0] == "ChangeDestination Root"
            assert plan.commands.count("ChangeDestination Root") == 1
            assert plan.commands[-1] == "ClearAll"
            assert not re.search(r"/overwrite", "\n".join(plan.commands), re.IGNORECASE)
            assert plan.created
            assert plan.skipped == ()
            assert plan.unmapped == ()

    def test_no_shipped_look_emits_movement(self):
        # v1 does not fire the movement axis, and the library carries none
        # (AC-LOOKLIB-003 band 6) — so no Phase/Speed reaches a bundle.
        for look in self.LIBRARY.looks:
            joined = "\n".join(_plan(look, _groups(*FULL_RIG), _pools()).commands).lower()
            assert "phase" not in joined
            assert "speed" not in joined

    def test_the_m0_showfile_maps_two_roles_and_reports_the_other_four(self):
        # progress.md §E.2 measurement 3, carried into the bundle layer: the
        # only real rig this project has maps 백라이트 and 프론트 and nothing
        # else. The look still instantiates, on the two groups it did get.
        m0 = _groups((1, "Copilot Grp"), (11, "Back"), (12, "Front"), (13, "All"))
        plan = _plan(self.LIBRARY.by_id("rock-chorus-white-slam"), m0, _pools())
        assert {u.role for u in plan.unmapped} == {"사이드", "탑", "배경", "스페셜"}
        assert {u.reason for u in plan.unmapped} == {NO_MATCH}
        assert "Group 11 + 12" in plan.commands
        assert plan.created
        assert plan.complete is False

    def test_the_worked_example_bundle_is_exact(self):
        look = self.LIBRARY.by_id("ballad-single-key")
        plan = _plan(look, _groups(*FULL_RIG), _pools())
        assert list(plan.commands) == [
            "ChangeDestination Root",
            "ClearAll",
            "Group 16",
            (
                "Attribute 'Dimmer' At 40 ; Attribute 'ColorRGB_R' At 100 ; "
                "Attribute 'ColorRGB_G' At 82 ; Attribute 'ColorRGB_B' At 60 ; "
                "Attribute 'Iris' At 32 ; Attribute 'Zoom' At 12"
            ),
            "Store Preset 1.1",
            "Label Preset 1.1 '단독 키'",
            "Store Preset 4.1",
            "Label Preset 4.1 '단독 키'",
            "Store Preset 5.1",
            "Label Preset 5.1 '단독 키'",
            "Store Preset 6.1",
            "Label Preset 6.1 '단독 키'",
            "ClearAll",
        ]


# =============================================================================
# build_instantiation composes with the already-resolved inputs
# =============================================================================


class TestSessionWiring:
    """REQ-LOOKLIB-010/019 — a look reaches the console the one existing way."""

    @staticmethod
    def _session(tmp_path):
        from .test_runner_self_correction import ScriptedProvider
        from .test_web_session import _session

        return _session(tmp_path, ScriptedProvider([]))

    def test_a_look_bundle_flows_through_the_gate_and_reaches_the_console(self, tmp_path):
        session, console, _audit, sent, _channel = self._session(tmp_path)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        result = session.run_look_bundle(plan)
        assert result["executed"] is True
        assert console.executed[0] == "ChangeDestination Root"
        assert any(c.startswith("Store Preset ") for c in console.executed)
        # The preview the gate path wraps fired for the look bundle too.
        assert any(event.get("type") == "execution_preview" for event in sent)

    def test_the_trailing_clearall_reaches_the_console(self, tmp_path):
        # WAS a finding, now fixed at its source: run_commands deduplicated
        # identical strings within one bundle, which is right for a `Store` —
        # re-running it duplicates a console object — and wrong for a
        # `ClearAll`, whose second occurrence exists to run at a different
        # MOMENT rather than to repeat an effect. Programmer-state commands are
        # exempt from that dedupe (tools._is_programmer_state), so the wire now
        # carries the whole discipline REQ-LOOKLIB-011 puts in the bundle text.
        session, console, _audit, _sent, _channel = self._session(tmp_path)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        session.run_look_bundle(plan)
        assert plan.commands[-1] == "ClearAll"
        assert console.executed == list(plan.commands)

    def test_the_next_bundle_still_starts_clean(self, tmp_path):
        # Belt as well as braces: the previous bundle closed with its own
        # ClearAll, and this one opens with a leading one that also runs —
        # neither is suppressed by the other.
        session, console, _audit, _sent, _channel = self._session(tmp_path)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        session.run_look_bundle(plan)
        console.executed.clear()
        session.run_look_bundle(plan)
        assert console.executed[1] == "ClearAll"

    def test_the_per_family_shape_runs_with_its_cycles_intact(self, tmp_path):
        # The FALLBACK branch is executable again (M0 ASSUMPTION-14). It was
        # refused while the dedupe flattened it: cycles 2..N lost BOTH their
        # ClearAll and their Group re-selection, so each stored the previous
        # cycle's programmer — the cross-family over-capture this shape exists
        # to rule out. Every line now reaches the console in order.
        session, console, _audit, _sent, _channel = self._session(tmp_path)
        look = _look(attributes=FOUR_FAMILY_ATTRIBUTES)
        plan = _plan(look, _groups((11, "Back")), _pools(), shape=CAPTURE_PER_FAMILY)
        result = session.run_look_bundle(plan)
        assert result["executed"] is True
        assert "refused" not in result
        assert console.executed == list(plan.commands)

    def test_every_per_family_store_keeps_its_own_capture_cycle(self, tmp_path):
        # What the round-trip above is FOR: four stores means four isolated
        # captures, each preceded by its own clear and re-selection, plus the
        # closing clear. A flattened bundle would show one of each.
        session, console, _audit, _sent, _channel = self._session(tmp_path)
        look = _look(attributes=FOUR_FAMILY_ATTRIBUTES)
        plan = _plan(look, _groups((11, "Back")), _pools(), shape=CAPTURE_PER_FAMILY)
        session.run_look_bundle(plan)
        assert len(_stores(console.executed)) == 4
        assert console.executed.count("ClearAll") == 5
        assert console.executed.count("Group 11") == 4

    def test_the_look_bundle_is_screened_as_one_bundle_not_command_by_command(self, tmp_path):
        session, _console, _audit, sent, _channel = self._session(tmp_path)
        plan = _plan(_look(attributes=(("Dimmer", 50),)), _groups((11, "Back")), _pools())
        session.run_look_bundle(plan)
        previews = [e for e in sent if e.get("type") == "execution_preview"]
        assert len(previews) == 1

    def test_an_empty_bundle_sends_nothing(self, tmp_path):
        session, console, _audit, _sent, _channel = self._session(tmp_path)
        plan = _plan(_look(roles=("배경",)), _groups((11, "Back")), _pools())
        result = session.run_look_bundle(plan)
        assert plan.commands == ()
        assert result["executed"] is False
        assert console.executed == []

    def test_the_report_rides_along_with_the_execution_result(self, tmp_path):
        session, _console, _audit, _sent, _channel = self._session(tmp_path)
        pools = _pools(contents={1: [_preset(1, "테스트 룩")]})
        look = _look(attributes=(("Dimmer", 50), ("ColorRGB_R", 100)))
        result = session.run_look_bundle(_plan(look, _groups((11, "Back")), pools))
        assert result["report"]["skipped_count"] == 1
        assert result["report"]["complete"] is False


class TestComposition:
    def test_the_builder_accepts_an_already_resolved_role_and_pool_input(self):
        look = _look(attributes=(("Dimmer", 50),))
        resolution = resolve_roles(_groups((11, "Back")))
        pools = resolve_pools(_pools())
        plan = build_instantiation(look, resolution=resolution, pools=pools)
        assert plan.created[0].pool == 1

    def test_the_convenience_entry_point_agrees_with_the_composed_one(self):
        look = _look(attributes=(("Dimmer", 50),))
        groups, pools = _groups((11, "Back")), _pools()
        composed = build_instantiation(
            look, resolution=resolve_roles(groups), pools=resolve_pools(pools)
        )
        assert composed.commands == _plan(look, groups, pools).commands
