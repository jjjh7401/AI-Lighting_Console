"""Response-check macro tests (AC-PRECHK-010 · AC-PRECHK-011 — M4).

Both branches of `AC-PRECHK-010` execute here, so **no `skip` marker is needed**:
the `ASSUMPTION-26` negative state is a `MacroPolicy` value, not a live console
condition, and injecting it costs one constructor call. A `skip` would be the
weaker artifact -- it would leave the DESCOPE path unexercised while claiming
coverage.

The canonical GO literal is NOT copied into this file. `AC-PRECHK-010` ① makes
the `GO: ASSUMPTION-26 literal=…` prefix line in `progress.md` the canon, so
:func:`measured_authoring_literal` parses it and the comparison runs against
what M0 actually spoke. A transcribed copy would keep passing after the record
changed, which is exactly the failure the AC forbids.

Console contact is zero: every input is an in-memory `state DataPool/Groups`
payload of the shape the responder returns.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from server.prechk.macro import (
    ASSUMPTION_MACRO_AUTHORING,
    AUTHORING_DESCOPED,
    GROUP_POOL_EMPTY,
    GROUP_POOL_PATH,
    GROUPS_UNADDRESSABLE,
    OFF,
    ON,
    PARTIAL_GROUP_COVERAGE,
    TARGET_KIND_GROUP,
    VISUAL_CONFIRMATION_REQUIRED,
    GroupPool,
    GroupTarget,
    MacroPolicy,
    build_response_check_macro,
    groups_from_snapshot,
    reason_label,
)

SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent
MACRO_MODULE = SERVER_DIR / "prechk" / "macro.py"
M0_PROGRESS = PROJECT_ROOT / ".moai" / "specs" / "SPEC-COPILOT-PRECHK-001" / "progress.md"

PROBE_SLOT = 91

# ---------------------------------------------------------------------------
# the canonical M0 record (AC-PRECHK-010 ① · AC-PRECHK-016 recording format)
# ---------------------------------------------------------------------------

# Prefix-line judgement, anchored at line start: prose that merely mentions the
# literal must NOT satisfy it (AC-PRECHK-016 recording format).
_GO_LINE = re.compile(
    r"^GO:[ \t]+ASSUMPTION-26[ \t]+literal=(?P<literal>.*?)[ \t]+effect=", re.MULTILINE
)


class MeasuredLiteralMissing(AssertionError):
    """No canon to compare against — the GO branch must fail, not pass."""


def measured_authoring_literal(progress_text: str) -> str:
    """The `literal=` value of the `GO: ASSUMPTION-26` prefix line.

    Raises :class:`MeasuredLiteralMissing` when the line is absent or its
    `literal=` value is empty. `AC-PRECHK-010` ① requires that state to FAIL the
    GO branch rather than let it through: without the record there is nothing to
    compare generated commands against.
    """
    match = _GO_LINE.search(progress_text)
    if match is None:
        raise MeasuredLiteralMissing(
            "no 'GO: ASSUMPTION-26 literal=… effect=…' prefix line in the M0 record"
        )
    literal = match.group("literal").strip()
    if not literal:
        raise MeasuredLiteralMissing("'GO: ASSUMPTION-26' prefix line carries an empty literal=")
    return literal


def measured_segments(literal: str) -> tuple[str, ...]:
    """The `;`-separated commands M0 spoke, in the order it spoke them."""
    segments = tuple(part.strip() for part in literal.split(";"))
    assert all(segments), f"empty segment in measured literal: {literal!r}"
    return segments


# A dotted id and a bare id are DIFFERENT steps -- `Store Macro 91` creates the
# macro object and `Store Macro 91.1` creates a line inside it. Collapsing both
# to one placeholder would let a two-step implementation (the rulebook recipe at
# server/rulebook/assets/v2.4.2/00_grammar.md:80-84, which omits the line-object
# step) match the three-step measured sequence.
_DOTTED_ID = re.compile(r"\b\d+\.\d+\b")
_BARE_ID = re.compile(r"\b\d+\b")
_PROPERTY_VALUE = re.compile(r"(Property '[A-Za-z]+' )'[^']*'")


def authoring_shape(command: str) -> str:
    """The command with ids and the stored payload replaced by placeholders."""
    shaped = _PROPERTY_VALUE.sub(r"\1'<cmd>'", command)
    shaped = _DOTTED_ID.sub("<n>.<line>", shaped)
    return _BARE_ID.sub("<n>", shaped)


def payload_shape(payload: str) -> str:
    return _BARE_ID.sub("<n>", payload)


def stored_payload(command: str) -> str | None:
    """The text a `Set … Property 'Command' '<text>'` command stores."""
    match = re.search(r"Property '[A-Za-z]+' '([^']*)'", command)
    return None if match is None else match.group(1)


def assert_commands_match_record(progress_text: str, commands) -> set[str]:
    """Compare generated command shapes against the M0 record's literal.

    The record is read FIRST and unconditionally: if it is missing or empty this
    raises before any comparison happens, so a GO branch with no canon fails
    instead of passing (`AC-PRECHK-010` ①).
    """
    measured = {
        authoring_shape(segment)
        for segment in measured_segments(measured_authoring_literal(progress_text))
    }
    assert commands, "non-vacuity: an empty command list matches any shape set"
    generated = {authoring_shape(command) for command in commands}
    assert generated == measured
    return measured


# ---------------------------------------------------------------------------
# in-memory fixtures (design.md §6.1)
# ---------------------------------------------------------------------------


def groups_snapshot(
    entries: tuple[tuple[int, str], ...],
    *,
    child_count: int | None = None,
    truncated: bool = False,
) -> dict:
    """A `state DataPool/Groups` payload of the shape the responder returns."""
    children = [{"i": number, "name": name, "class": "Group"} for number, name in entries]
    return {
        "ok": True,
        "path": GROUP_POOL_PATH,
        "node": {
            "name": "Groups",
            "class": "Groups",
            "childCount": len(children) if child_count is None else child_count,
        },
        "children": children,
        "truncated": truncated,
    }


# `groups_present` — two or more NUMBERED groups (design.md §6.1).
GROUPS_PRESENT = ((11, "Back"), (12, "Front"))

# `groups_empty` — zero groups (design.md §6.1).
GROUPS_EMPTY: tuple[tuple[int, str], ...] = ()

# The live rig, for reference only. The structural tests below vary the count on
# purpose so nothing is pinned to these four values.
LIVE_RIG_GROUPS = ((1, "Copilot Grp"), (11, "Back"), (12, "Front"), (13, "All"))

# `slot_not_fid` — slot 1, FID 101 (design.md §6.1). The rig this SPEC measured
# has slot == FID for every fixture, so only a fixture where they DIVERGE can
# show that a generated command references neither (console/lua/PROTOCOL.md:322-324).
SLOT_NOT_FID = {"slot": 1, "fid": 101, "name": "RMMXSm1 1", "patch": "1.001"}


def go_policy(slot: int = PROBE_SLOT) -> MacroPolicy:
    return MacroPolicy.available(macro_slot=slot)


def descoped_policy(reason: str = "매크로 저작 문법이 실측되지 않았다") -> MacroPolicy:
    return MacroPolicy.descoped(reason)


def built(
    entries: tuple[tuple[int, str], ...] = GROUPS_PRESENT,
    *,
    policy: MacroPolicy | None = None,
    truncated: bool = False,
    child_count: int | None = None,
):
    pool = groups_from_snapshot(
        groups_snapshot(entries, truncated=truncated, child_count=child_count)
    )
    return build_response_check_macro(pool, policy or go_policy())


# ---------------------------------------------------------------------------
# scanners — each one is proven to catch a planted violation
# ---------------------------------------------------------------------------

_FIXTURE_SELECTION = re.compile(r"\bFixture\s+\d")

# Object references inside a stored line, by pool type. Restricted to real
# object keywords so that the intensity value in `Group 11 At 0` is not mistaken
# for a reference -- `0` is a level, not an object.
_OBJECT_REFERENCE = re.compile(
    r"\b(Fixture|Group|Sequence|Macro|Preset|Executor|Page|Timecode)\s+(\d+(?:\.\d+)*)"
)

# `no_response` has no 'respond' in it and `responded` has no 'respons' in it,
# so the shared prefix is the only token that catches both families.
_RESPONSE_ASSERTION_TOKENS = ("respon", "fixture_ok", "verified", "is_lit", "_lit", "lit_")


def fixture_selection_hits(commands) -> tuple[str, ...]:
    return tuple(command for command in commands if _FIXTURE_SELECTION.search(command))


def response_assertion_keys(payload: dict) -> tuple[str, ...]:
    def forbidden(key: str) -> bool:
        low = key.lower()
        return any(token in low for token in _RESPONSE_ASSERTION_TOKENS)

    hits = [key for key in payload if forbidden(key)]
    for value in payload.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    hits.extend(key for key in item if forbidden(key))
    return tuple(hits)


def imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return tuple(names)


# ---------------------------------------------------------------------------


class TestTheMeasuredLiteralIsTheCanon:
    """AC-PRECHK-010 ① — the record is the canon, and a missing record fails."""

    def test_the_m0_record_carries_exactly_one_go_line_for_assumption_26(self):
        text = M0_PROGRESS.read_text(encoding="utf-8")
        assert len(_GO_LINE.findall(text)) == 1, (
            "AC-PRECHK-016 allows one prefix line per ASSUMPTION; two records "
            "would make 'the canon' ambiguous"
        )

    def test_the_measured_literal_is_a_three_step_authoring_sequence(self):
        literal = measured_authoring_literal(M0_PROGRESS.read_text(encoding="utf-8"))
        segments = measured_segments(literal)
        assert len(segments) == 3, (
            f"M0 measured a three-step sequence; the record has {len(segments)}: {segments}"
        )
        shapes = [authoring_shape(segment) for segment in segments]
        assert shapes == [
            "Store Macro <n>",
            "Store Macro <n>.<line>",
            "Set Macro <n>.<line> Property 'Command' '<cmd>'",
        ]

    def test_a_missing_go_line_fails_instead_of_passing(self):
        # The AC is explicit: with no canon the GO branch must NOT be let through.
        text = "DESCOPE: ASSUMPTION-26 문법이 없다\nGO: ASSUMPTION-25 literal=x effect=y\n"
        with pytest.raises(MeasuredLiteralMissing, match="no 'GO: ASSUMPTION-26"):
            measured_authoring_literal(text)

    def test_an_empty_literal_value_fails_instead_of_passing(self):
        with pytest.raises(MeasuredLiteralMissing, match="empty literal="):
            measured_authoring_literal("GO: ASSUMPTION-26 literal= effect=아무것도 없음\n")

    def test_prose_mentioning_the_literal_does_not_satisfy_the_prefix_line(self):
        prose = (
            "M0는 GO: ASSUMPTION-26 literal=Store Macro 91 effect=확인 처럼 적지 않고\n"
            "산문에 녹여 적었다.\n"
        )
        with pytest.raises(MeasuredLiteralMissing):
            measured_authoring_literal(prose)

    def test_the_real_record_actually_parses(self):
        # Non-vacuity for the three tests above: they assert on FAILURE paths,
        # so a parser that rejected everything would pass all of them.
        literal = measured_authoring_literal(M0_PROGRESS.read_text(encoding="utf-8"))
        assert literal
        assert "Store Macro" in literal
        assert "Property 'Command'" in literal


class TestGoBranchUsesOnlyMeasuredShapes:
    """AC-PRECHK-010 ① — no rulebook-only variant is ever spoken."""

    def test_generated_command_shapes_equal_the_measured_shapes(self):
        measured = assert_commands_match_record(
            M0_PROGRESS.read_text(encoding="utf-8"), built().commands
        )
        assert len(measured) == 3

    def test_the_comparison_fails_when_the_record_lost_its_go_line(self):
        # The same commands that pass above must NOT pass without the canon --
        # the gate is the record, not the shape of the generated list.
        commands = built().commands
        for crippled in (
            "DESCOPE: ASSUMPTION-26 문법 미실측\n",
            "GO: ASSUMPTION-26 literal= effect=아무것도 없음\n",
            "이 문서는 GO: ASSUMPTION-26 을 산문에 녹여 적었다\n",
            "",
        ):
            with pytest.raises(MeasuredLiteralMissing):
                assert_commands_match_record(crippled, commands)

    def test_the_line_object_step_is_emitted(self):
        # The rulebook recipe omits it; without it the third step fails with
        # `Illegal object` on a live console (progress.md M0 record).
        result = built()
        assert f"Store Macro {PROBE_SLOT}.1" in result.commands

    def test_the_object_step_comes_first_and_only_once(self):
        result = built(LIVE_RIG_GROUPS)
        assert result.commands[0] == f"Store Macro {PROBE_SLOT}"
        assert result.commands.count(f"Store Macro {PROBE_SLOT}") == 1

    def test_every_line_is_created_immediately_before_it_is_set(self):
        result = built(LIVE_RIG_GROUPS)
        for index, command in enumerate(result.commands):
            if command.startswith(f"Set Macro {PROBE_SLOT}."):
                target = command.split(" Property ")[0].removeprefix("Set ")
                assert result.commands[index - 1] == f"Store {target}", (
                    "the measured order per line is create-then-set; reordering "
                    "reintroduces the `Illegal object` failure"
                )

    def test_the_on_payload_shape_is_the_measured_one(self):
        literal = measured_authoring_literal(M0_PROGRESS.read_text(encoding="utf-8"))
        measured_payloads = [
            stored_payload(segment)
            for segment in measured_segments(literal)
            if stored_payload(segment) is not None
        ]
        assert measured_payloads, "the measured literal must store at least one line"
        measured = {payload_shape(payload) for payload in measured_payloads}
        result = built()
        on_shapes = {payload_shape(line.payload) for line in result.lines if line.phase == ON}
        assert on_shapes, "non-vacuity: no ON line would make the comparison free"
        assert on_shapes <= measured

    def test_no_command_carries_a_double_quote_or_newline(self):
        # server/bridge/protocol.py:105-111 rejects both before the wire.
        result = built(LIVE_RIG_GROUPS)
        assert result.commands
        for command in result.commands:
            assert '"' not in command
            assert "\n" not in command and "\r" not in command


class TestPairAccounting:
    """AC-PRECHK-010 ④ — one on/off pair per group, never a constant."""

    def test_one_pair_per_group(self):
        result = built(GROUPS_PRESENT)
        assert result.pair_count == len(result.targets) == 2

    @pytest.mark.parametrize("count", [1, 2, 3, 4, 7])
    def test_pair_count_follows_the_group_count(self, count):
        entries = tuple((10 + index, f"G{index}") for index in range(count))
        result = built(entries)
        assert result.pair_count == count
        assert len(result.lines) == count * 2

    def test_command_count_follows_the_group_count(self):
        # 1 object step + 2 commands per line + 2 lines per group.
        for count in (1, 3, 5):
            entries = tuple((10 + index, f"G{index}") for index in range(count))
            assert len(built(entries).commands) == 1 + 4 * count

    def test_each_pair_is_exactly_one_on_and_one_off(self):
        result = built(LIVE_RIG_GROUPS)
        assert result.pairs
        for on_line, off_line in result.pairs:
            assert on_line.phase == ON
            assert off_line.phase == OFF
            assert on_line.group_no == off_line.group_no

    def test_every_target_group_appears_in_exactly_one_pair(self):
        result = built(LIVE_RIG_GROUPS)
        paired = [on_line.group_no for on_line, _ in result.pairs]
        assert sorted(paired) == sorted(target.no for target in result.targets)
        assert len(paired) == len(set(paired))

    def test_line_numbers_are_contiguous_from_one(self):
        result = built(LIVE_RIG_GROUPS)
        assert [line.number for line in result.lines] == list(range(1, len(result.lines) + 1))


class TestDescopeBranch:
    """AC-PRECHK-010 ② — a negative ASSUMPTION-26 speaks zero commands."""

    def test_zero_commands_when_authoring_is_descoped(self):
        result = built(GROUPS_PRESENT, policy=descoped_policy())
        assert result.created is False
        assert result.commands == ()
        assert result.lines == ()
        assert result.pair_count == 0

    def test_the_go_branch_command_list_is_not_empty(self):
        # Non-vacuity for the "zero commands" scan above: if the builder never
        # produced commands, every 0-count assertion would pass silently.
        assert len(built(GROUPS_PRESENT).commands) >= 5

    def test_the_descope_is_reported_as_a_skipped_check(self):
        result = built(GROUPS_PRESENT, policy=descoped_policy("문법 미실측"))
        assert result.reason_code == AUTHORING_DESCOPED
        assert result.skipped_checks() == (
            {
                "kind": "macro_descope",
                "reason": result.reason,
                "assumption": ASSUMPTION_MACRO_AUTHORING,
            },
        )
        assert "문법 미실측" in result.reason

    def test_a_descoped_policy_without_a_reason_is_rejected(self):
        with pytest.raises(ValueError, match="descope"):
            MacroPolicy(authoring_available=False)

    def test_an_available_policy_carrying_a_descope_reason_is_rejected(self):
        with pytest.raises(ValueError, match="descope"):
            MacroPolicy(authoring_available=True, macro_slot=91, descope_reason="모순")

    def test_the_go_branch_emits_no_skipped_check(self):
        assert built(GROUPS_PRESENT).skipped_checks() == ()

    def test_no_targets_are_claimed_when_nothing_was_created(self):
        result = built(GROUPS_PRESENT, policy=descoped_policy())
        assert result.targets == ()
        assert result.to_dict()["targets"] == []


class TestTheMacroAxisIsIndependentOfPatchJudgement:
    """AC-PRECHK-010 ③ — the macro axis cannot kill the patch check."""

    def test_the_macro_module_imports_no_judgement_axis(self):
        modules = imported_modules(MACRO_MODULE)
        assert len(modules) >= 1, "non-vacuity: an empty scan makes every 0-count true"
        forbidden = [
            module
            for module in modules
            if module.startswith(("server.prechk.patch", "server.prechk.inventory"))
        ]
        assert forbidden == [], (
            "coupling the macro axis to the patch axis is what would let a "
            "descoped macro take the patch judgement down with it"
        )

    def test_the_macro_module_reaches_no_send_surface(self):
        # REQ-PRECHK-019 / REQ-PRECHK-018 restated at file scope.
        modules = imported_modules(MACRO_MODULE)
        assert modules
        assert [m for m in modules if m.startswith(("server.bridge", "pythonosc"))] == []

    def test_the_builder_needs_no_patch_input_at_all(self):
        # Structural independence: the descope path returns a complete answer
        # from the pool and the policy alone.
        result = built(GROUPS_PRESENT, policy=descoped_policy())
        assert result.reason
        assert result.target_kind == TARGET_KIND_GROUP


class TestFixtureSelectionIsForbidden:
    """AC-PRECHK-011 ① — group targets only, never `Fixture <n>`."""

    def test_no_generated_command_selects_a_fixture(self):
        result = built(LIVE_RIG_GROUPS)
        assert result.commands, "non-vacuity: an empty list has zero of everything"
        assert fixture_selection_hits(result.commands) == ()

    def test_the_scanner_catches_a_planted_fixture_command(self):
        planted = (
            *built(GROUPS_PRESENT).commands,
            f"Set Macro {PROBE_SLOT}.9 Property 'Command' 'Fixture 3 At Full'",
        )
        assert len(fixture_selection_hits(planted)) == 1

    def test_at_least_one_command_targets_a_group(self):
        result = built(GROUPS_PRESENT)
        group_targeting = [line.payload for line in result.lines if "Group " in line.payload]
        assert len(group_targeting) == len(result.lines) >= 2

    def test_stored_payloads_reference_only_group_objects(self):
        # `slot_not_fid`: slot 1 and FID 101 must appear as an object reference
        # in NO payload. A build that selected fixtures by slot would emit
        # `Fixture 1`, one that trusted FID would emit `Fixture 101` -- and the
        # measured rig (slot == FID) cannot tell those two bugs apart.
        result = built(((11, "Back"), (12, "Front")))
        references: set[tuple[str, str]] = set()
        for line in result.lines:
            references.update(_OBJECT_REFERENCE.findall(line.payload))
        assert references == {("Group", "11"), ("Group", "12")}
        assert ("Fixture", str(SLOT_NOT_FID["slot"])) not in references
        assert ("Fixture", str(SLOT_NOT_FID["fid"])) not in references

    def test_the_target_kind_is_group(self):
        assert built(GROUPS_PRESENT).to_dict()["target_kind"] == TARGET_KIND_GROUP

    def test_an_empty_group_pool_answers_with_a_reason_and_invents_nothing(self):
        result = built(GROUPS_EMPTY)
        assert result.created is False
        assert result.commands == ()
        assert result.targets == ()
        assert result.reason_code == GROUP_POOL_EMPTY
        assert result.reason == reason_label(GROUP_POOL_EMPTY)
        assert result.skipped_checks() == (
            {"kind": "macro_no_groups", "reason": result.reason, "assumption": ""},
        )

    def test_groups_without_a_number_are_not_a_missing_pool(self):
        # Different user action: the pool exists, the groups are unaddressable.
        pool = groups_from_snapshot(
            {
                "ok": True,
                "path": GROUP_POOL_PATH,
                "node": {"name": "Groups", "class": "Groups", "childCount": 2},
                "children": [{"name": "Back", "class": "Group"}, {"name": "Front"}],
                "truncated": False,
            }
        )
        result = build_response_check_macro(pool, go_policy())
        assert result.created is False
        assert result.reason_code == GROUPS_UNADDRESSABLE
        assert "Back" in result.reason and "Front" in result.reason
        assert result.skipped_checks()[0]["kind"] == "macro_no_groups"

    def test_a_group_pool_is_never_synthesised_for_the_caller(self):
        # No fallback target: an empty pool with an available policy still
        # produces zero commands.
        result = build_response_check_macro(GroupPool(), go_policy())
        assert result.commands == ()


class TestNoResponseEvidence:
    """AC-PRECHK-011 ② ③ — the payload never claims a fixture answered."""

    SCHEMA_KEYS = {
        "created",
        "target_kind",
        "targets",
        "commands",
        "requires_human_visual_confirmation",
        "reason",
    }

    def test_the_payload_carries_every_schema_key(self):
        # Non-vacuity for the forbidden-field scan: an empty payload has zero
        # forbidden fields for free.
        payload = built(GROUPS_PRESENT).to_dict()
        assert set(payload) == self.SCHEMA_KEYS
        assert all(payload[key] is not None for key in self.SCHEMA_KEYS)

    def test_the_descope_payload_carries_every_schema_key_too(self):
        payload = built(GROUPS_PRESENT, policy=descoped_policy()).to_dict()
        assert set(payload) == self.SCHEMA_KEYS

    def test_the_payload_has_no_response_asserting_field(self):
        for policy in (go_policy(), descoped_policy()):
            payload = build_response_check_macro(
                groups_from_snapshot(groups_snapshot(GROUPS_PRESENT)), policy
            ).to_dict()
            assert payload
            assert response_assertion_keys(payload) == ()

    def test_the_forbidden_field_scanner_catches_planted_fields(self):
        payload = built(GROUPS_PRESENT).to_dict()
        for planted in ("responded", "fixture_ok", "no_response", "fixtures_verified"):
            assert response_assertion_keys({**payload, planted: True}) == (planted,)

    def test_the_scanner_reaches_into_the_target_rows(self):
        payload = built(GROUPS_PRESENT).to_dict()
        poisoned = {**payload, "targets": [{"no": 11, "name": "Back", "responded": True}]}
        assert response_assertion_keys(poisoned) == ("responded",)

    def test_visual_confirmation_is_required_in_every_branch(self):
        for policy in (go_policy(), descoped_policy()):
            for entries in (GROUPS_PRESENT, GROUPS_EMPTY):
                payload = build_response_check_macro(
                    groups_from_snapshot(groups_snapshot(entries)), policy
                ).to_dict()
                assert payload["requires_human_visual_confirmation"] is True

    def test_the_reason_tells_the_user_to_look_at_the_rig(self):
        reason = built(GROUPS_PRESENT).reason
        assert reason == reason_label(VISUAL_CONFIRMATION_REQUIRED)
        assert "눈으로" in reason
        assert "접수" in reason, "the reason must say an ok is acceptance, not a response"

    def test_a_truncated_group_pool_says_so_in_the_reason(self):
        result = built(GROUPS_PRESENT, child_count=9)
        assert result.created is True
        assert reason_label(PARTIAL_GROUP_COVERAGE) in result.reason
        assert reason_label(VISUAL_CONFIRMATION_REQUIRED) in result.reason

    def test_an_untruncated_pool_carries_no_coverage_caveat(self):
        assert reason_label(PARTIAL_GROUP_COVERAGE) not in built(GROUPS_PRESENT).reason


class TestStoredLineLiterals:
    """The payload forms, and why the off line is not `Off Group <n>`."""

    def test_the_on_line_is_the_measured_form(self):
        result = built(((11, "Back"),))
        on_line = next(line for line in result.lines if line.phase == ON)
        assert on_line.payload == "On Group 11"

    def test_the_off_line_is_the_value_form_not_the_off_verb(self):
        result = built(((11, "Back"),))
        off_line = next(line for line in result.lines if line.phase == OFF)
        assert off_line.payload == "Group 11 At 0"
        assert not off_line.payload.startswith("Off ")

    def test_the_gate_holds_the_off_verb_form_but_clears_the_value_form(self):
        # This is the whole reason the off line is `Group <n> At 0`
        # (.moai/state/verify/prechk-m0/MacroAuthoringProbe.md:138). The quoted
        # property value is reclassified recursively
        # (server/safety/classify.py:201-222), and `Off` is an invoking verb
        # (server/safety/blacklist.yaml:29) whose target `Group` is NOT a
        # recognized reference type (server/safety/classify.py:44) -> held.
        from server.safety.classify import classify_command
        from server.safety.grammar import validate as validate_grammar
        from server.safety.ruleset import load_ruleset

        ruleset = load_ruleset()

        def category(command: str) -> str:
            parsed = validate_grammar(command)
            assert parsed.ok, f"test line must parse: {command!r}"
            return classify_command(parsed.parsed, ruleset).category

        assert category(f"Set Macro {PROBE_SLOT}.2 Property 'Command' 'Off Group 11'") == "invoking"
        assert category(f"Set Macro {PROBE_SLOT}.2 Property 'Command' 'Group 11 At 0'") == "safe"

    def test_the_measured_on_form_is_also_gate_held(self):
        # Finding of this milestone, recorded so it cannot be lost: `On` sits in
        # the SAME invoking-verb list as `Off` (server/safety/blacklist.yaml:28),
        # so the authoring line that stores the M0-measured `On Group <n>` is
        # held for human approval on the production path. A hold is a DEFINED
        # outcome (AC-PRECHK-014 ④), not a failure -- but it is not "clears the
        # gate", and this test fails loudly if that ever changes.
        from server.safety.classify import classify_command
        from server.safety.grammar import validate as validate_grammar
        from server.safety.ruleset import load_ruleset

        parsed = validate_grammar(f"Set Macro {PROBE_SLOT}.1 Property 'Command' 'On Group 11'")
        assert parsed.ok
        finding = classify_command(parsed.parsed, load_ruleset())
        assert finding.category == "invoking"
        assert finding.risky is False

    def test_no_payload_contains_a_nested_quote(self):
        # server/rulebook/assets/v2.4.2/00_grammar.md:97-101 -- MA3 quoting has
        # no escape, so a group NAME may never enter the payload.
        result = built(LIVE_RIG_GROUPS)
        for line in result.lines:
            assert "'" not in line.payload
        for target in result.targets:
            assert target.name not in "".join(result.commands)


class TestGroupsFromSnapshot:
    def test_numbered_children_become_targets_in_order(self):
        pool = groups_from_snapshot(groups_snapshot(LIVE_RIG_GROUPS))
        assert [(target.no, target.name) for target in pool.targets] == list(LIVE_RIG_GROUPS)
        assert pool.unaddressable == ()
        assert pool.truncated is False

    def test_a_child_without_a_number_is_recorded_not_dropped(self):
        payload = groups_snapshot(((11, "Back"),))
        payload["children"].append({"name": "Nameless", "class": "Group"})
        payload["node"]["childCount"] = 2
        pool = groups_from_snapshot(payload)
        assert [target.no for target in pool.targets] == [11]
        assert pool.unaddressable == ("Nameless",)

    @pytest.mark.parametrize("bad", [0, -1, "11", 11.0, True, None])
    def test_a_non_slot_index_is_unaddressable(self, bad):
        payload = groups_snapshot(())
        payload["children"] = [{"i": bad, "name": "Odd", "class": "Group"}]
        payload["node"]["childCount"] = 1
        assert groups_from_snapshot(payload).targets == ()

    def test_truncation_comes_from_the_count_comparison_not_only_the_flag(self):
        # The M2 lesson applied to the group pool: `childCount` is the true
        # total and the flag can be absent or wrong (spec.md §A constraint 2).
        payload = groups_snapshot(GROUPS_PRESENT, child_count=9, truncated=False)
        assert groups_from_snapshot(payload).truncated is True

    def test_the_flag_alone_still_marks_truncation(self):
        payload = groups_snapshot(GROUPS_PRESENT, truncated=True)
        assert groups_from_snapshot(payload).truncated is True

    def test_a_complete_pool_is_not_truncated(self):
        assert groups_from_snapshot(groups_snapshot(GROUPS_PRESENT)).truncated is False

    def test_a_failed_snapshot_raises(self):
        with pytest.raises(ValueError, match="not ok"):
            groups_from_snapshot({"ok": False, "path": GROUP_POOL_PATH, "error": "boom"})

    def test_an_empty_pool_is_normal_not_an_error(self):
        pool = groups_from_snapshot(groups_snapshot(()))
        assert pool.targets == ()
        assert pool.unaddressable == ()


class TestInputValidation:
    def test_a_duplicate_group_number_is_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            GroupPool(targets=(GroupTarget(no=11, name="Back"), GroupTarget(no=11, name="Again")))

    @pytest.mark.parametrize("bad", [0, -3])
    def test_a_non_positive_group_number_is_rejected(self, bad):
        with pytest.raises(ValueError, match="positive"):
            GroupTarget(no=bad, name="Bad")

    def test_an_available_policy_needs_a_real_macro_slot(self):
        with pytest.raises(ValueError, match="macro slot"):
            MacroPolicy(authoring_available=True)

    def test_the_macro_slot_is_the_callers_choice(self):
        # Nothing here picks a slot: overwriting the responder's own `Copilot Go`
        # at slot 1 is a real hazard, and only a live pool read rules it out.
        result = built(GROUPS_PRESENT, policy=go_policy(slot=77))
        assert result.commands[0] == "Store Macro 77"
        assert result.macro_slot == 77
