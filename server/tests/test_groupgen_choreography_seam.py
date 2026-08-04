"""Choreography-integration regression seam (plan.md §B M4).

These tests pin that the groups `server/groupgen/write.py` produces are
directly usable by the EXISTING, already-validated choreography path — the
rulebook (`31_choreography_patterns.md`) and the role vocabulary
(`server/looks/roles.py`) are consumed READ-ONLY here; nothing in either is
modified, and no new rulebook content is authored (`.plan-contract.md` §2
D-Q7: "룰북 v1 신설 없음"). AC-033 already pins rulebook byte-diff 0
elsewhere — this file does not repeat that assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

from server.groupgen.write import build_group_write_plan
from server.looks.roles import match_role_by_name
from server.spatial import naming

RULEBOOK_PATH = Path("server/rulebook/assets/v2.4.2/31_choreography_patterns.md")

MEASURED_GROUPS_SECTION = {
    "ok": True,
    "truncated": False,
    "objects": [{"no": n} for n in (1, 11, 12, 13, 15)],
}
UNTRUNCATED_FIXTURES_SECTION = {"ok": True, "truncated": False, "childCount": 19}


def _sample_plan():
    """One representative axis-separated grid plan (design.md §D-Q2)."""
    buckets = {
        "depth0": (1, 2),
        "depth1": (3, 4),
        "lateral0": (5, 6),
        "lateral1": (7, 8),
    }
    names = {
        "depth0": naming.name_depth_bucket(0, 2),
        "depth1": naming.name_depth_bucket(1, 2),
        "lateral0": naming.name_lateral_bucket(0, 2),
        "lateral1": naming.name_lateral_bucket(1, 2),
    }
    return build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )


# -- 1. produced recall commands are the SAME bare form the rulebook --------
#       already validates ("Group 11" — no `Select`/`SelFix` prefix) --------


def test_human_check_commands_are_bare_group_recall_form() -> None:
    """`Group <n>` bare form — the same shape `31_choreography_patterns.md`
    validates at :29 (`Group recall selects its members: Group 11`) and
    requires at :31 (bare `Fixture ...` / `Group ...`, NOT `Select Fixture
    ...` / `SelFix ...`, both of which returned "Illegal object" on 2.4.2).
    """
    plan = _sample_plan()
    assert plan.human_check_commands  # non-empty — there is something to check
    for command in plan.human_check_commands:
        assert re.fullmatch(r"Group \d+", command), (
            f"{command!r} is not the bare 'Group <n>' recall form the rulebook validates"
        )


def test_rulebook_documents_the_exact_bare_recall_form_being_reused() -> None:
    """Confirms the citation above still matches the rulebook text on disk —
    a READ, never a write; if the rulebook's wording ever moves, this test
    (not `31_choreography_patterns.md`) is what should be revisited.
    """
    text = RULEBOOK_PATH.read_text(encoding="utf-8")
    assert "Group recall selects its members: `Group 11`" in text
    assert "Do NOT prefix with `Select Fixture ...` or use `SelFix ...`" in text


def test_store_and_label_commands_never_use_select_or_selfix_prefix() -> None:
    """The write chain itself (`Store Group N`, `Label Group N '...'`,
    `Fixture ...` selection) stays inside the same validated bare-command
    grammar the recall check above pins — no `Select`/`SelFix` prefix
    anywhere in the emitted chain.
    """
    plan = _sample_plan()
    for step in plan.steps:
        for command in step.commands:
            assert not command.startswith("Select ")
            assert not command.startswith("SelFix ")


# -- 2. GEO-prefixed auto-generated names never collide with the role -------
#       vocabulary (naming.py already checked this; re-confirm from the -----
#       choreography-consumption side — a collision would misfire the role --
#       resolver, not just misname a group) -------------------------------


def test_geo_prefixed_names_never_match_a_position_role() -> None:
    """If a `GEO ...` name matched a role hint, `match_role_by_name` (the
    function the choreography/role-resolution path actually calls) would
    misclassify an auto-generated geometric group as a functional position
    role. Sweeps every closed-vocabulary name shape `naming.py` can produce.
    """
    candidate_names: list[str] = []
    for total in (2, 3, 4, 5):
        candidate_names.extend(naming.name_depth_bucket(index, total) for index in range(total))
        candidate_names.extend(naming.name_lateral_bucket(index, total) for index in range(total))
        candidate_names.extend(
            naming.name_concentric_bucket(index, total) for index in range(total)
        )
        candidate_names.extend(naming.name_vertical_bucket(index, total) for index in range(total))

    assert candidate_names  # the sweep actually produced names to check
    for name in candidate_names:
        match = match_role_by_name(name)
        assert match.role is None, (
            f"auto-generated name {name!r} matched role {match.role!r} — a "
            "GEO-prefixed geometric group must never resolve as a functional "
            "position role"
        )


# -- 3. write.py never fabricates MAtricks — 3-layer division of labor ------
#       (group=who / selection order=which order / MAtricks=how to reshape) -
#       stays code-enforced, per D-Q10 + contract §C.0 axis E --------------

_MATRICKS_TOKENS = ("XWings", "XShuffle", "PhaseFromX")


def test_write_module_never_emits_matricks_tokens() -> None:
    """`server/groupgen/write.py` composes only `ClearAll` / `Fixture ...` /
    `Store Group` / `Label Group` — MAtricks reshaping is runtime territory
    (`Attribute ... At X + XWings ...`), explicitly out of scope for group
    generation (`.plan-contract.md` §2 D-Q10: "MAtricks ... 축 E는 명시적
    제외 범위"). A grep-0 static check, since MAtricks tokens are a fixed,
    named vocabulary distinct from the group/topology naming vocabulary.
    """
    source = Path("server/groupgen/write.py").read_text(encoding="utf-8")
    for token in _MATRICKS_TOKENS:
        assert token not in source


def test_write_plan_commands_never_contain_matricks_tokens() -> None:
    """Same check against an actual assembled plan's command text, not just
    the source — the static grep above proves the module never hardcodes a
    MAtricks token; this proves none leaks in via a runtime-composed string.
    """
    plan = _sample_plan()
    for step in plan.steps:
        for command in step.commands:
            for token in _MATRICKS_TOKENS:
                assert token not in command


# -- 4. bilateral_pairs stays a reported PROPERTY, never a group ------------
#       (D-Q10: "신호만 보고 · 그룹 생성 안 함") — re-confirmed from the -----
#       choreography-consumption side: write.py has no notion of pairing ----


def test_write_module_has_no_bilateral_pairing_concept() -> None:
    """`build_group_write_plan` takes only `buckets: Mapping[str, Sequence[
    int]]` — an unordered named-fid-list mapping with no pairing/symmetry
    field. There is no code path from a `bilateral_pairs` topology result
    into a Stored group: the write module is structurally blind to pairing,
    it only ever sees flat fid buckets a caller already decided to name and
    write (`classify_arrangement_topology`'s naming layer is what excludes
    `bilateral_pairs` from `suggested_groups` in the first place — a read-side
    decision this write-side module cannot see around even if it wanted to).
    """
    source = Path("server/groupgen/write.py").read_text(encoding="utf-8")
    assert "bilateral" not in source.lower()
