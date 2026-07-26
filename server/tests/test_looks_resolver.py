"""Role → rig group resolution (M3 — AC-LOOKLIB-005 / AC-LOOKLIB-006).

Every fixture here is an in-memory rig built with the PRODUCER's own helpers
(``rig_object`` / ``rig_section`` from ``server.orchestrator.tools``). Building
the input by hand would let this suite keep passing after the console shape
changed underneath it — the boundary is only real when both sides are read
together.

Nothing here touches a console.

Failure modes are separate tests on purpose (design.md §6.2). The seven this
milestone owns: no candidate / ambiguous / truncated / path_not_resolved /
console_unreachable / a group the responder could not number / an empty groups
section. Merging any two of them would hide the one that matters.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from server.looks.resolver import (
    AMBIGUOUS,
    NO_MATCH,
    UNADDRESSABLE,
    GroupCandidate,
    resolve_roles,
)
from server.looks.roles import ROLE_NAMES, ROLES
from server.orchestrator.tools import (
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    rig_object,
    rig_section,
)

BACKLIGHT = "백라이트"
FRONT = "프론트"
SIDE = "사이드"
TOP = "탑"
BACKDROP = "배경"
SPECIAL = "스페셜"


def _child(no: int, name: str) -> dict:
    """A responder child WITH an established pool slot (PROTOCOL.md §4.2)."""
    return {"i": no, "name": name}


def _unnumbered(name: str) -> dict:
    """A responder child whose slot could NOT be established — no ``i`` key.

    Not a malformed payload: the responder refuses to substitute the listing
    position, so the absence is the signal (``tools.py:185-211``).
    """
    return {"name": name}


def _groups(*children: dict, truncated: bool = False, child_count: int | None = None) -> dict:
    objects = [rig_object(dict(child)) for child in children]
    payload = {
        "node": {"childCount": len(children) if child_count is None else child_count},
        "truncated": truncated,
    }
    return rig_section(objects, payload)


def _failed(reason: str) -> dict:
    """A groups section the console did not deliver — the tools.py shape."""
    return {
        "reason": reason,
        "path": "DataPool/Groups",
        "error": f"{reason}: boom",
    }


# The live showfile of the M0 probe, verbatim (progress.md §E.2 measurement 3).
M0_SHOWFILE = (
    _child(1, "Copilot Grp"),
    _child(11, "Back"),
    _child(12, "Front"),
    _child(13, "All"),
)


class TestM0LiveShowfile:
    """The only real-rig data point this project has. Pinned whole.

    Measured 2026-07-26 against a live grandMA3 onPC: 2/6 roles matched, zero
    ambiguous names, zero false positives. A change that moves any number here
    is a change in behaviour against the one rig we actually observed.
    """

    def test_backlight_binds_to_the_group_named_back(self):
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert resolution.groups_for(BACKLIGHT) == (GroupCandidate(number=11, name="Back"),)

    def test_front_binds_to_the_group_named_front(self):
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert resolution.groups_for(FRONT) == (GroupCandidate(number=12, name="Front"),)

    def test_the_other_four_roles_are_reported_unmapped(self):
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert {u.role for u in resolution.unmapped} == {SIDE, TOP, BACKDROP, SPECIAL}
        assert {u.reason for u in resolution.unmapped} == {NO_MATCH}

    def test_zero_ambiguous_names(self):
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert resolution.ambiguous_groups == ()

    def test_copilot_grp_and_all_match_nothing(self):
        # Recorded by M0 as hint-expansion candidates, NOT as a defect.
        #
        # Correction carried from M1: `All` matching nothing does NOT prove
        # token-boundary discipline — no hint is a substring of "all", so even
        # a naive substring matcher returns no match here. The observation is
        # real; the explanation attached to it in §E.2 was wrong. The names
        # that actually carry boundary discipline are in
        # TestConsumesTheM1MatchingContract below.
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert resolution.unmatched_groups == ("Copilot Grp", "All")

    def test_a_two_of_six_rig_is_a_successful_resolve(self):
        # §A.3 honest shrinkage: unmapped is correct output, not failure.
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert resolution.unavailable_reason is None
        assert resolution.truncated is False


class TestNamingConventions:
    def test_korean_convention_maps_all_six_roles(self):
        resolution = resolve_roles(
            _groups(
                _child(1, "백라이트 바"),
                _child(2, "프론트 열"),
                _child(3, "측면 SL"),
                _child(4, "상부 다운"),
                _child(5, "배경 호리"),
                _child(6, "키라이트"),
            )
        )
        assert resolution.unmapped == ()
        assert [c.number for c in resolution.groups_for(BACKLIGHT)] == [1]
        assert [c.number for c in resolution.groups_for(FRONT)] == [2]
        assert [c.number for c in resolution.groups_for(SIDE)] == [3]
        assert [c.number for c in resolution.groups_for(TOP)] == [4]
        assert [c.number for c in resolution.groups_for(BACKDROP)] == [5]
        assert [c.number for c in resolution.groups_for(SPECIAL)] == [6]

    def test_english_convention_maps_all_six_roles(self):
        resolution = resolve_roles(
            _groups(
                _child(11, "Back Truss"),
                _child(12, "Front Bar"),
                _child(13, "Side L"),
                _child(14, "Top Wash"),
                _child(15, "Cyc"),
                _child(16, "Special 1"),
            )
        )
        assert resolution.unmapped == ()
        assert [c.name for c in resolution.groups_for(TOP)] == ["Top Wash"]

    def test_one_role_may_hold_several_groups_in_rig_order(self):
        resolution = resolve_roles(
            _groups(
                _child(21, "Side SR"),
                _child(7, "Side SL"),
            )
        )
        assert resolution.groups_for(SIDE) == (
            GroupCandidate(number=21, name="Side SR"),
            GroupCandidate(number=7, name="Side SL"),
        )

    def test_the_real_pool_number_is_carried_not_the_listing_position(self):
        # Live-demo finding #3: the model must never map "the Nth item" onto
        # "object N" (tools.py:180-184).
        resolution = resolve_roles(_groups(_child(97, "Back")))
        assert resolution.groups_for(BACKLIGHT)[0].number == 97


class TestConsumesTheM1MatchingContract:
    """The resolver must not re-derive matching with a looser rule."""

    def test_baeksaek_does_not_reach_the_backlight_role(self):
        # `백색` (a colour word) contains the `백` hint. Python's \b would not
        # have stopped it; M1's explicit word class does.
        resolution = resolve_roles(_groups(_child(1, "백색")))
        assert resolution.groups_for(BACKLIGHT) == ()
        assert resolution.unmatched_groups == ("백색",)

    def test_backdrop_reaches_only_the_backdrop_role(self):
        resolution = resolve_roles(_groups(_child(1, "Backdrop")))
        assert [c.name for c in resolution.groups_for(BACKDROP)] == ["Backdrop"]
        assert resolution.groups_for(BACKLIGHT) == ()

    def test_underscore_separated_abbreviation_still_binds(self):
        resolution = resolve_roles(_groups(_child(1, "BL_Truss")))
        assert [c.number for c in resolution.groups_for(BACKLIGHT)] == [1]


class TestNoCandidate:
    def test_a_rig_with_no_convention_maps_nothing(self):
        resolution = resolve_roles(
            _groups(
                _child(1, "Copilot Grp"),
                _child(2, "Slash Bar"),
                _child(3, "Keys"),
            )
        )
        assert {u.role for u in resolution.unmapped} == set(ROLE_NAMES)
        assert {u.reason for u in resolution.unmapped} == {NO_MATCH}
        assert resolution.mapped == {}

    def test_no_match_carries_no_group_names(self):
        resolution = resolve_roles(_groups(_child(1, "Keys")))
        assert all(u.groups == () for u in resolution.unmapped)


class TestAmbiguous:
    def test_a_name_claimed_by_two_roles_is_never_assigned(self):
        resolution = resolve_roles(_groups(_child(5, "FrontBack Truss")))
        assert resolution.groups_for(BACKLIGHT) == ()
        assert resolution.groups_for(FRONT) == ()

    def test_both_claimed_roles_report_reason_ambiguous(self):
        resolution = resolve_roles(_groups(_child(5, "FrontBack Truss")))
        assert resolution.reason_for(BACKLIGHT) == AMBIGUOUS
        assert resolution.reason_for(FRONT) == AMBIGUOUS

    def test_the_ambiguous_name_and_its_claimants_are_reported(self):
        resolution = resolve_roles(_groups(_child(5, "FrontBack Truss")))
        assert len(resolution.ambiguous_groups) == 1
        entry = resolution.ambiguous_groups[0]
        assert entry.name == "FrontBack Truss"
        assert entry.roles == (BACKLIGHT, FRONT)

    def test_the_unmapped_entry_names_the_group_that_caused_it(self):
        resolution = resolve_roles(_groups(_child(5, "FrontBack Truss")))
        assert resolution.unmapped_for(FRONT).groups == ("FrontBack Truss",)

    def test_an_ambiguous_name_does_not_shadow_a_clean_match(self):
        resolution = resolve_roles(
            _groups(
                _child(5, "FrontBack Truss"),
                _child(12, "Front"),
            )
        )
        assert resolution.groups_for(FRONT) == (GroupCandidate(number=12, name="Front"),)
        assert resolution.reason_for(BACKLIGHT) == AMBIGUOUS

    def test_roles_untouched_by_the_ambiguity_still_report_no_match(self):
        resolution = resolve_roles(_groups(_child(5, "FrontBack Truss")))
        assert resolution.reason_for(TOP) == NO_MATCH


class TestUnaddressableGroup:
    """A group the responder listed but could not number."""

    def test_an_unnumbered_group_does_not_crash_the_resolve(self):
        resolution = resolve_roles(_groups(_unnumbered("Back")))
        assert resolution.mapped == {}

    def test_an_unnumbered_group_never_becomes_a_candidate(self):
        resolution = resolve_roles(_groups(_unnumbered("Back")))
        assert resolution.groups_for(BACKLIGHT) == ()

    def test_the_role_is_unmapped_with_its_own_reason(self):
        resolution = resolve_roles(_groups(_unnumbered("Back")))
        assert resolution.reason_for(BACKLIGHT) == UNADDRESSABLE
        assert resolution.unmapped_for(BACKLIGHT).groups == ("Back",)

    def test_unaddressable_is_distinct_from_no_match(self):
        # Merging them would read as "this rig has no backlight", when what the
        # rig actually said is "there IS one and I could not number it".
        assert UNADDRESSABLE != NO_MATCH

    def test_every_unnumbered_group_is_reported_whatever_it_matched(self):
        resolution = resolve_roles(
            _groups(
                _unnumbered("Back"),
                _unnumbered("Keys"),
                _child(12, "Front"),
            )
        )
        assert resolution.unaddressable_groups == ("Back", "Keys")

    def test_an_addressable_sibling_still_binds_the_role(self):
        resolution = resolve_roles(
            _groups(
                _unnumbered("Back Truss"),
                _child(11, "Back Bar"),
            )
        )
        assert resolution.groups_for(BACKLIGHT) == (GroupCandidate(number=11, name="Back Bar"),)
        assert resolution.reason_for(BACKLIGHT) is None
        assert resolution.unaddressable_groups == ("Back Truss",)

    def test_an_unnumbered_exact_match_outranks_an_ambiguous_claim(self):
        # Both reasons apply to 백라이트 here. The one reported is the one an
        # operator can act on: a group that named this role and only needs a
        # slot beats a name that could not decide which role it meant.
        resolution = resolve_roles(
            _groups(
                _child(5, "FrontBack Truss"),
                _unnumbered("Back Bar"),
            )
        )
        assert resolution.reason_for(BACKLIGHT) == UNADDRESSABLE
        assert resolution.unmapped_for(BACKLIGHT).groups == ("Back Bar",)
        # The ambiguity is still reported — it is just not what blocks this role.
        assert resolution.reason_for(FRONT) == AMBIGUOUS
        assert resolution.ambiguous_groups[0].roles == (BACKLIGHT, FRONT)


class TestMalformedEntry:
    """A listing entry that is not an object at all."""

    def test_a_non_mapping_entry_is_skipped_not_fatal(self):
        section = _groups(_child(11, "Back"))
        section["objects"].insert(0, "Front")  # type: ignore[union-attr]
        resolution = resolve_roles(section)
        assert resolution.groups_for(BACKLIGHT) == (GroupCandidate(number=11, name="Back"),)

    def test_a_non_mapping_entry_never_becomes_a_group(self):
        section = _groups(_child(11, "Back"))
        section["objects"].insert(0, "Front")  # type: ignore[union-attr]
        resolution = resolve_roles(section)
        assert resolution.reason_for(FRONT) == NO_MATCH
        assert resolution.unmatched_groups == ()


class TestTruncated:
    def test_the_truncation_signal_is_propagated(self):
        resolution = resolve_roles(_groups(_child(11, "Back"), truncated=True, child_count=40))
        assert resolution.truncated is True

    def test_an_untruncated_section_reports_false(self):
        resolution = resolve_roles(_groups(_child(11, "Back")))
        assert resolution.truncated is False

    def test_truncation_does_not_suppress_what_did_arrive(self):
        resolution = resolve_roles(_groups(_child(11, "Back"), truncated=True, child_count=40))
        assert resolution.groups_for(BACKLIGHT) == (GroupCandidate(number=11, name="Back"),)
        assert resolution.reason_for(FRONT) == NO_MATCH


class TestPathNotResolved:
    """A sibling section answered — this path is wrong for this showfile."""

    def test_the_reason_is_propagated_verbatim(self):
        resolution = resolve_roles(_failed(REASON_UNRESOLVED))
        assert resolution.unavailable_reason == REASON_UNRESOLVED

    def test_every_role_is_unmapped_with_that_reason(self):
        resolution = resolve_roles(_failed(REASON_UNRESOLVED))
        assert {u.role for u in resolution.unmapped} == set(ROLE_NAMES)
        assert {u.reason for u in resolution.unmapped} == {REASON_UNRESOLVED}

    def test_no_candidate_is_produced(self):
        resolution = resolve_roles(_failed(REASON_UNRESOLVED))
        assert resolution.mapped == {}
        assert resolution.unmatched_groups == ()


class TestConsoleUnreachable:
    """Nothing answered — no path can be blamed."""

    def test_the_reason_is_propagated_verbatim(self):
        resolution = resolve_roles(_failed(REASON_UNREACHABLE))
        assert resolution.unavailable_reason == REASON_UNREACHABLE

    def test_every_role_is_unmapped_with_that_reason(self):
        resolution = resolve_roles(_failed(REASON_UNREACHABLE))
        assert {u.reason for u in resolution.unmapped} == {REASON_UNREACHABLE}


class TestTheTwoUnavailableReasonsStaySplit:
    """A configuration defect and an operating condition are not the same fact.

    REQ-SHOWUI-002 already consumes this split; a resolver that normalised both
    to one soft "unavailable" would re-create the failure mode that let two dead
    rig paths ship for a whole stage (tools.py:92-105).
    """

    def test_the_two_resolutions_do_not_report_the_same_reason(self):
        unresolved = resolve_roles(_failed(REASON_UNRESOLVED))
        unreachable = resolve_roles(_failed(REASON_UNREACHABLE))
        assert unresolved.unavailable_reason != unreachable.unavailable_reason

    def test_neither_is_flattened_into_a_matching_reason(self):
        for reason in (REASON_UNRESOLVED, REASON_UNREACHABLE):
            resolution = resolve_roles(_failed(reason))
            assert resolution.reason_for(BACKLIGHT) not in (NO_MATCH, AMBIGUOUS, UNADDRESSABLE)

    def test_an_unknown_reason_string_is_not_swallowed(self):
        resolution = resolve_roles(_failed("drilldown_capped"))
        assert resolution.unavailable_reason == "drilldown_capped"


class TestEmptyGroupsSection:
    """The console answered and the pool is genuinely empty."""

    def test_all_roles_are_unmapped_with_no_match(self):
        resolution = resolve_roles(_groups())
        assert {u.reason for u in resolution.unmapped} == {NO_MATCH}

    def test_an_empty_pool_is_not_an_unavailable_rig(self):
        resolution = resolve_roles(_groups())
        assert resolution.unavailable_reason is None

    def test_nothing_is_reported_as_unmatched_or_ambiguous(self):
        resolution = resolve_roles(_groups())
        assert resolution.unmatched_groups == ()
        assert resolution.ambiguous_groups == ()
        assert resolution.unaddressable_groups == ()


class TestNeverInventsAGroup:
    """AC-LOOKLIB-006 — only groups the rig listed may come back."""

    @pytest.mark.parametrize(
        "section",
        [
            _groups(*M0_SHOWFILE),
            _groups(_child(11, "Back Truss"), _child(12, "Front Bar")),
            _groups(_child(5, "FrontBack Truss"), _child(12, "Front")),
            _groups(_unnumbered("Back"), _child(13, "Side L")),
            _groups(truncated=True, child_count=9),
            _failed(REASON_UNRESOLVED),
            _failed(REASON_UNREACHABLE),
        ],
    )
    def test_every_candidate_came_from_the_input_rig(self, section):
        listed = {
            (obj.get("no"), obj.get("name")) for obj in section.get("objects", []) if "no" in obj
        }
        resolution = resolve_roles(section)
        for candidates in resolution.mapped.values():
            for candidate in candidates:
                assert (candidate.number, candidate.name) in listed

    @pytest.mark.parametrize(
        "section",
        [
            _groups(*M0_SHOWFILE),
            _groups(_unnumbered("Back"), _child(13, "Side L")),
            _failed(REASON_UNREACHABLE),
        ],
    )
    def test_every_reported_name_came_from_the_input_rig(self, section):
        listed = {obj.get("name") for obj in section.get("objects", [])}
        resolution = resolve_roles(section)
        reported = set(resolution.unmatched_groups) | set(resolution.unaddressable_groups)
        reported |= {entry.name for entry in resolution.ambiguous_groups}
        reported |= {name for entry in resolution.unmapped for name in entry.groups}
        assert reported <= listed


class TestRoleAccounting:
    @pytest.mark.parametrize(
        "section",
        [
            _groups(*M0_SHOWFILE),
            _groups(),
            _groups(_child(5, "FrontBack Truss")),
            _groups(_unnumbered("Back")),
            _failed(REASON_UNRESOLVED),
        ],
    )
    def test_every_role_is_either_mapped_or_explicitly_unmapped(self, section):
        resolution = resolve_roles(section)
        mapped = set(resolution.mapped)
        unmapped = {entry.role for entry in resolution.unmapped}
        assert mapped | unmapped == set(ROLE_NAMES)
        assert mapped & unmapped == set()

    def test_unmapped_entries_follow_the_vocabulary_order(self):
        resolution = resolve_roles(_groups())
        assert [entry.role for entry in resolution.unmapped] == [role.name for role in ROLES]

    def test_a_mapped_role_reports_no_reason(self):
        resolution = resolve_roles(_groups(_child(11, "Back")))
        assert resolution.reason_for(BACKLIGHT) is None
        assert resolution.unmapped_for(BACKLIGHT) is None


# -- static discipline ---------------------------------------------------------
#
# These scan the resolver's own SOURCE. They key on the forbidden API surface
# (a command string, a section key) rather than on topic vocabulary, so that
# prose explaining WHY the resolver avoids fixtures cannot blunt them — the M2
# census caught a forbidden token inside its own comment for exactly this
# reason. Docstrings are excluded from the scan for the same reason.

_FORBIDDEN_IN_CODE_STRINGS = (
    "fixture",  # the slot≠FID section must never be read (tools.py:33-36)
    "thru",  # `Fixture x Thru y` range synthesis
    "attribute",  # any attribute emission, incl. pan/tilt (REQ-LOOKLIB-009)
    "pan",
    "tilt",
    "group ",  # `Group <n>` — the resolver returns numbers, not commands
)


def _code_string_constants(path: Path) -> list[str]:
    """Every string literal in the module EXCEPT docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


class TestNoConsoleCommandSynthesis:
    """AC-LOOKLIB-006 static half + REQ-LOOKLIB-009's synthesis ban."""

    def test_the_scan_actually_sees_this_module(self):
        # Non-vacuity: a scan that finds nothing because it parsed nothing
        # passes for the wrong reason. Every section key the resolver reads is
        # a code string, so their presence proves the scan reaches the code —
        # not merely the module header.
        from server.looks import resolver

        constants = set(_code_string_constants(Path(resolver.__file__)))
        assert UNADDRESSABLE in constants
        assert {"reason", "objects", "truncated", "no", "name"} <= constants

    def test_the_resolver_emits_no_console_command_text(self):
        from server.looks import resolver

        offenders = [
            value
            for value in _code_string_constants(Path(resolver.__file__))
            for token in _FORBIDDEN_IN_CODE_STRINGS
            if token in value.lower()
        ]
        assert offenders == []
