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
    AliasRejection,
    GroupCandidate,
    resolve_roles,
)
from server.looks.roles import (
    POSITION_ROLE_NAMES,
    ROLE_NAMES,
    ROLES,
    TYPE_ROLE_NAMES,
    match_role_by_name,
)
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

    def test_the_other_four_position_roles_are_reported_unmapped(self):
        # t356: 종류 역할 다섯이 어휘에 들어왔고 이 쇼파일에는 그런 그룹이 없다 —
        # 그래서 미매핑 집합이 넓어졌다. **여기서 재는 것은 위치 축**이므로 위치
        # 역할로 좁힌다. 집합 전체를 재던 원래 단언은 아래 검사가 이어받는다.
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        unmapped = {u.role for u in resolution.unmapped}
        assert unmapped & POSITION_ROLE_NAMES == {SIDE, TOP, BACKDROP, SPECIAL}
        assert {u.reason for u in resolution.unmapped} == {NO_MATCH}

    def test_every_type_role_is_unmapped_because_this_rig_has_no_such_group(self):
        # t356 의 비공허성: 종류 역할은 **조용히 빠지지 않는다**. 이 쇼파일에
        # 워시·무버·블라인더·스트로브·헤이즈 그룹이 없다는 사실은 no_match 로
        # 보고되어야 하고, 보고되지 않으면 미매핑 보고가 축 하나만 덮는 것이다.
        resolution = resolve_roles(_groups(*M0_SHOWFILE))
        assert {u.role for u in resolution.unmapped} & TYPE_ROLE_NAMES == TYPE_ROLE_NAMES

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
        assert {u.role for u in resolution.unmapped} == TYPE_ROLE_NAMES
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
        # `Top Wash` 는 위치(탑)와 종류(워시) 둘 다에 걸리는 이름이다 — 위치가
        # 이기므로 탑에 묶이고, 워시는 이 리그에서 미매핑으로 남는다.
        assert {u.role for u in resolution.unmapped} == TYPE_ROLE_NAMES
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


# ---------------------------------------------------------------------------
# t356 — 열린 역할 어휘를 실기 리그에 대고 잰다.
# ---------------------------------------------------------------------------

#: `.moai/specs/SPEC-COPILOT-LXSEQ-001/research.md:28` 이 기록한 실기 리그.
#: 12그룹 86대. 이름은 그 문서의 `Group` 열 그대로이고, 수량도 그대로다.
#: **이 숫자가 표준 §12 항목 6 이 다투는 분모다** — 그래서 그룹 수가 아니라
#: 기구 수로 센다. 그룹 수로 세면 HAZE 2대와 BACK 12대가 같은 무게가 된다.
LXSEQ_RIG: tuple[tuple[str, int], ...] = (
    ("KEY", 6),
    ("FOH", 8),
    ("BLIND", 6),
    ("STROBE", 4),
    ("HAZE", 2),
    ("MOVER-U", 8),
    ("MOVER-D", 8),
    ("BACK", 12),
    ("SIDE-L", 6),
    ("SIDE-R", 6),
    ("WASH-U", 10),
    ("WASH-D", 10),
)
LXSEQ_TOTAL_FIXTURES = 86

#: t356 이전에는 이 일곱 그룹이 전부 no_match 였다 — 48대, 리그의 56%.
#: 표준 §7.1 사다리의 마지막 두 칸이 불가능했던 이유가 이 중 BLIND·STROBE 다.
LXSEQ_PREVIOUSLY_UNREACHABLE = (
    "BLIND",
    "STROBE",
    "HAZE",
    "MOVER-U",
    "MOVER-D",
    "WASH-U",
    "WASH-D",
)


def _lxseq_section() -> dict:
    return _groups(*(_child(index + 1, name) for index, (name, _) in enumerate(LXSEQ_RIG)))


def _covered_fixtures(resolution) -> int:
    bound = {candidate.name for group in resolution.mapped.values() for candidate in group}
    return sum(count for name, count in LXSEQ_RIG if name in bound)


class TestLxseqRigCoverage:
    """양성 대조군 — 실기 12그룹이 실제로 해석되는가, 그리고 몇 대인가."""

    def test_the_fixture_inventory_matches_the_recorded_rig(self):
        # 비공허성: 분모가 틀리면 아래 커버리지 숫자는 아무것도 안 잰다.
        assert sum(count for _, count in LXSEQ_RIG) == LXSEQ_TOTAL_FIXTURES
        assert len(LXSEQ_RIG) == 12

    def test_every_real_group_resolves_to_a_role(self):
        resolution = resolve_roles(_lxseq_section())
        assert resolution.unmatched_groups == ()
        assert resolution.ambiguous_groups == ()

    def test_coverage_is_the_whole_rig_by_fixture_count(self):
        resolution = resolve_roles(_lxseq_section())
        assert _covered_fixtures(resolution) == LXSEQ_TOTAL_FIXTURES

    def test_the_seven_groups_that_were_unreachable_now_resolve(self):
        resolution = resolve_roles(_lxseq_section())
        bound = {candidate.name for group in resolution.mapped.values() for candidate in group}
        assert set(LXSEQ_PREVIOUSLY_UNREACHABLE) <= bound

    def test_the_ladder_rungs_the_standard_needs_are_callable(self):
        # 표준 §7.1: chorus 3 = 블라인더, 앙코르 = 스트로브. 이 둘이 역할로
        # 안 잡히면 사다리의 마지막 두 칸은 문서로만 존재한다.
        resolution = resolve_roles(_lxseq_section())
        assert [c.name for c in resolution.groups_for("블라인더")] == ["BLIND"]
        assert [c.name for c in resolution.groups_for("스트로브")] == ["STROBE"]

    def test_the_only_unmapped_roles_are_positions_this_rig_lacks(self):
        # 이 리그에는 탑도 배경(호리)도 없다. 그것은 보고되어야 하는 사실이고
        # 결함이 아니다 — 어휘를 넓혔다고 없는 그룹이 생기지는 않는다.
        resolution = resolve_roles(_lxseq_section())
        assert {u.role for u in resolution.unmapped} == {TOP, BACKDROP}
        assert {u.reason for u in resolution.unmapped} == {NO_MATCH}


class TestPositionBeatsTypeOnCollision:
    """음성 대조군 그 1 — 두 축이 같은 이름을 주장할 때. 쏴서 확인한다."""

    def test_a_name_claimed_by_a_position_and_a_type_goes_to_the_position(self):
        resolution = resolve_roles(_groups(_child(1, "Back Wash")))
        assert [c.name for c in resolution.groups_for(BACKLIGHT)] == ["Back Wash"]
        assert resolution.groups_for("워시") == ()
        assert resolution.ambiguous_groups == ()

    def test_the_losing_type_role_is_reported_not_discarded(self):
        match = match_role_by_name("Back Wash")
        assert match.role == BACKLIGHT
        assert match.deferred == ("워시",)

    def test_two_positions_claiming_one_name_stay_ambiguous(self):
        # 위치 우선은 **축 사이**의 규칙이다. 위치 축이 스스로 못 정하는 것을
        # 종류 답으로 메우면 그것은 추측이다.
        resolution = resolve_roles(_groups(_child(5, "FrontBack Wash")))
        assert resolution.ambiguous_groups[0].roles == (BACKLIGHT, FRONT)
        assert resolution.groups_for("워시") == ()

    def test_two_types_claiming_one_name_stay_ambiguous(self):
        match = match_role_by_name("Wash Mover")
        assert match.reason == AMBIGUOUS
        assert match.candidates == ("워시", "무버")


class TestUnmatchedGroupIsReportedNotSwallowed:
    """음성 대조군 그 2 — 아무 역할도 안 부른 이름. 조용히 사라지면 안 된다."""

    def test_a_fabricated_group_name_lands_in_unmatched_groups(self):
        resolution = resolve_roles(_groups(_child(1, "Zorblax Array"), _child(2, "Back")))
        assert resolution.unmatched_groups == ("Zorblax Array",)
        assert [c.name for c in resolution.groups_for(BACKLIGHT)] == ["Back"]

    def test_every_listed_group_is_accounted_for_somewhere(self):
        section = _groups(
            _child(1, "Zorblax Array"),
            _child(2, "Back"),
            _child(3, "FrontBack Truss"),
            _unnumbered("Side L"),
        )
        resolution = resolve_roles(section)
        reported = set(resolution.unmatched_groups) | set(resolution.unaddressable_groups)
        reported |= {entry.name for entry in resolution.ambiguous_groups}
        reported |= {c.name for group in resolution.mapped.values() for c in group}
        assert reported == {"Zorblax Array", "Back", "FrontBack Truss", "Side L"}


class TestPerShowAliases:
    """리그마다 다른 그룹명 — 힌트 목록이 유일한 수단이 아니어야 한다."""

    def test_an_alias_binds_a_name_no_hint_would_match(self):
        resolution = resolve_roles(
            _groups(_child(1, "Zorblax Array")), aliases={"Zorblax Array": "블라인더"}
        )
        assert [c.name for c in resolution.groups_for("블라인더")] == ["Zorblax Array"]
        assert resolution.unmatched_groups == ()

    def test_the_alias_key_ignores_case_and_padding(self):
        resolution = resolve_roles(_groups(_child(1, "WASH-U")), aliases={"  wash-u  ": "스페셜"})
        assert [c.name for c in resolution.groups_for(SPECIAL)] == ["WASH-U"]

    def test_an_alias_overrides_the_hint_match(self):
        # 운영자가 쇼에 대해 아는 것이 저장소의 힌트보다 낫다 — 그렇지 않으면
        # 별칭 표는 힌트가 침묵할 때만 쓰이는 반쪽 수단이 된다.
        resolution = resolve_roles(_groups(_child(1, "Back")), aliases={"back": "배경"})
        assert [c.name for c in resolution.groups_for(BACKDROP)] == ["Back"]
        assert resolution.groups_for(BACKLIGHT) == ()

    def test_an_english_role_alias_is_accepted_as_the_value(self):
        resolution = resolve_roles(_groups(_child(1, "Zorblax")), aliases={"zorblax": "hazer"})
        assert [c.name for c in resolution.groups_for("헤이즈")] == ["Zorblax"]

    def test_an_unknown_role_name_is_rejected_and_reported(self):
        resolution = resolve_roles(_groups(_child(1, "Back")), aliases={"back": "무대감독"})
        assert resolution.alias_rejections == (AliasRejection(group="Back", requested="무대감독"),)

    def test_a_rejected_alias_does_not_fall_back_to_the_hint_match(self):
        # 오타를 힌트로 되돌리면 운영자가 지정하지 않은 조명이 켜진다.
        resolution = resolve_roles(_groups(_child(1, "Back")), aliases={"back": "무대감독"})
        assert resolution.groups_for(BACKLIGHT) == ()
        assert resolution.unmatched_groups == ("Back",)

    def test_an_alias_for_a_group_the_rig_never_listed_is_reported(self):
        resolution = resolve_roles(_groups(_child(1, "Back")), aliases={"nosuchgroup": "워시"})
        assert resolution.unused_aliases == ("nosuchgroup",)

    def test_an_aliased_group_without_a_number_stays_unaddressable(self):
        # 별칭은 이름을 푸는 수단이지 주소를 만드는 수단이 아니다.
        resolution = resolve_roles(_groups(_unnumbered("Zorblax")), aliases={"zorblax": "워시"})
        assert resolution.reason_for("워시") == UNADDRESSABLE

    def test_no_aliases_leaves_both_alias_reports_empty(self):
        resolution = resolve_roles(_lxseq_section())
        assert resolution.alias_rejections == ()
        assert resolution.unused_aliases == ()
