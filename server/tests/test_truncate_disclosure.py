"""Truncation disclosure — SPEC-COPILOT-TRUNCATE-001 (M1/M2).

The defect this file pins is not a wrong number. It is a SILENCE: on the
measured calibration rig the stage patch answered ``childCount 19`` while
handing over 18 children with ``truncated: true``, and the reply carried that
flag right next to a row analysis reporting ``low_confidence: False`` — a
confident left/right ordering asserted for a rig that does not exist (SPATIAL
``progress.md:485``). The flag was true, correct, present and ignored.

So the prescription is not a louder flag. Two properties, and each one has to
go RED when its branch is deleted:

  * **a partial read returns a DIFFERENT reply** (REQ-TRUNCATE-001/002). The
    fixture list moves to ``partial_fixtures`` and the ``fixtures`` key is
    GONE. A boolean beside the data can be skipped because the payload still
    reads; an absent key cannot, because there is nothing left to skip. The
    branch predicate is the EXISTING ``coverage.complete`` — console
    truncation OR this tool's own round-trip cap OR the two counts simply
    disagreeing — so no new judgment was introduced anywhere.
  * **the row structure is WITHHELD, not flagged** (REQ-TRUNCATE-003). This is
    the half that carries the load. ``analyze_spatial_records`` takes records
    and nothing else (``server/spatial/rows.py:202-204`` — verified: one
    parameter, no coverage argument), so its output is structurally incapable
    of knowing it describes part of a rig, and teaching it would mean editing
    the pure geometry layer that REQ-TRUNCATE-012 seals. A model that ignores
    a boolean can still quote an ordering; it cannot quote a key that was
    never computed.

And one write-path hole the same measurement exposed: every geometric group
``classify_arrangement_topology`` proposes has carried ``topology_partial``
since the GROUPGEN-024 amendment, and ``create_arrangement_groups`` read it
ZERO times. It is wired here — refusing unless the caller ENUMERATES the fids
the read never saw. Not a boolean: a boolean is filled in reflexively without
reading what is absent, which is the very shape this SPEC rejects, so an
acknowledgement in that shape would rebuild the defect inside the fix.

Nothing here touches a console. The material mirrors the live onPC 2.4.2
measurements: property reads answer with STRINGS, and the calibration
container answers ``childCount: 19`` while delivering 18 children.
"""

from __future__ import annotations

import json

import pytest

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    SPATIAL_FIXTURE_PROPERTIES,
    SPATIAL_PROPERTY_QUERY_CAP,
    TOOL_NAMES,
    build_toolset,
)
from server.safety.approval import ApprovalRequest

SPATIAL = "get_spatial_context"
CLASSIFY = "classify_arrangement_topology"
CREATE = "create_arrangement_groups"

FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]
GROUPS_PATH = DEFAULT_RIG_CONTEXT_PATHS["groups"]

#: The rig size at which this tool stops asking on its own: the property
#: budget divided by the properties one fixture costs. Derived, never a
#: literal — a test that hardcoded 30 would keep passing if the cap moved.
CAP_FIXTURES = SPATIAL_PROPERTY_QUERY_CAP // len(SPATIAL_FIXTURE_PROPERTIES)

#: Every key a COMPLETE reply has, in the order it has them. The pin for
#: "the non-breaking half is actually non-breaking" (AC-TRUNCATE-004).
COMPLETE_REPLY_KEYS = [
    "source",
    "path",
    "fixtures",
    "unreadable",
    "truncated",
    "roundtrip_capped",
    "coverage",
    "analysis",
]


def _fixture(slot, fid, name, x="0.0", y="0.0", z="0.0"):
    """One fixture as the console reports it: strings, or ``None`` if unreadable."""
    return {"slot": slot, "fid": fid, "name": name, "posx": x, "posy": y, "posz": z}


def _bar(count, *, spacing=1.0):
    """A row of ``count`` fixtures at distinct x — a rig with a real ordering."""
    return [
        _fixture(i + 1, str(i + 1), f"PAR {i + 1}", x=f"{i * spacing:.1f}") for i in range(count)
    ]


class SpatialRig:
    """State + property double for the stage patch container.

    Duplicated from ``test_spatial_context.py`` rather than imported, the same
    way ``test_groupgen_tools.py`` duplicates it: material another test file
    can edit is material this file does not control.
    """

    def __init__(self, fixtures, *, declared=None, flag=False, with_child_count=True):
        self.fixtures = {entry["slot"]: entry for entry in fixtures}
        self.declared = len(fixtures) if declared is None else declared
        self.flag = flag
        self.with_child_count = with_child_count
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        if path != FIXTURES_PATH:
            raise LookupError(f"unknown object path: {path}")
        node: dict[str, object] = {"name": "Fixtures", "class": "Fixtures"}
        if self.with_child_count:
            node["childCount"] = self.declared
        return {
            "ok": True,
            "path": path,
            "node": node,
            "children": [
                {"i": entry["slot"], "name": entry["name"]} for entry in self.fixtures.values()
            ],
            "truncated": self.flag,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        slot = int(path.rsplit("/", 1)[1])
        value = self.fixtures[slot].get(property_name.lower())
        if value is None:
            return {"ok": False, "error": f"property not readable: {property_name}"}
        return {"ok": True, "value": value}


class RecordingExecutionPort:
    def __init__(self):
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class ScriptedApprovalPort:
    def __init__(self, *, approve: bool):
        self.approve = approve
        self.requests: list[ApprovalRequest] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.requests.append(request)
        return self.approve


def _dispatch(rig, tool=SPATIAL, arguments=None, execution_port=None):
    registry = build_toolset(
        execution_port=execution_port or RecordingExecutionPort(), state_port=rig
    )
    return registry.dispatch(ToolCall(id="call-1", name=tool, arguments=arguments or {}))


def _read(rig) -> dict:
    return json.loads(_dispatch(rig).result.content)


# -- the measured material ----------------------------------------------------
#
# childCount 19 / 18 children / truncated:true. The rig is bigger than what
# arrives, which is what stops a mutation from passing vacuously: on material
# that never crosses the boundary, deleting the branch changes nothing.


def _measured_rig() -> SpatialRig:
    return SpatialRig(_bar(18), declared=19, flag=True)


def _complete_rig(count=18) -> SpatialRig:
    return SpatialRig(_bar(count), declared=count, flag=False)


class TestPartialReplyHasNoFixturesKey:
    """AC-TRUNCATE-001 — the list moves and the old key is gone."""

    def test_the_measured_rig_moves_the_list_and_drops_the_fixtures_key(self):
        # Catches: the shape divergence deleted (single return restored), or
        # the branch predicate pinned to a constant "complete".
        reply = _read(_measured_rig())

        assert "fixtures" not in reply
        assert len(reply["partial_fixtures"]) == 18
        # The 18 that arrived are whole — this is not a degraded read.
        assert reply["unreadable"] == []

    def test_the_child_count_arithmetic_alone_diverges_the_shape(self):
        # A responder that drops its own flag still cannot make the loss
        # silent. Catches: the branch narrowed to payload["truncated"] only.
        reply = _read(SpatialRig(_bar(18), declared=19, flag=False))

        assert "fixtures" not in reply
        assert len(reply["partial_fixtures"]) == 18

    def test_the_round_trip_cap_alone_diverges_the_shape(self):
        # The rig the CONSOLE answered in full, that THIS tool stopped reading
        # at its own budget: truncated false, roundtrip_capped true.
        # Catches: the branch narrowed to `truncated` only, which is the
        # mutation that re-opens the same silence on every rig past
        # SPATIAL_PROPERTY_QUERY_CAP / 4 fixtures.
        reply = _read(SpatialRig(_bar(CAP_FIXTURES + 1)))

        assert reply["truncated"] is False
        assert reply["roundtrip_capped"] is True
        assert "fixtures" not in reply
        assert len(reply["partial_fixtures"]) == CAP_FIXTURES

    def test_a_complete_rig_keeps_fixtures_and_grows_no_partial_key(self):
        # Non-vacuity for all three above: an implementation that always
        # returned the partial shape would pass them and fail here.
        reply = _read(_complete_rig())

        assert "fixtures" in reply
        assert len(reply["fixtures"]) == 18
        assert "partial_fixtures" not in reply
        assert "missing" not in reply


class TestAnalysisIsWithheldNotFlagged:
    """AC-TRUNCATE-002 — the half of the design that carries the load."""

    def test_a_partial_read_computes_no_row_structure_at_all(self):
        # Catches: the analysis still computed on a partial read (today's
        # behaviour), and equally the "additive compromise" — keeping
        # `analysis` and merely adding `analysis_withheld` beside it, which
        # would leave every existing consumer quietly working.
        reply = _read(_measured_rig())

        assert "analysis" not in reply
        assert reply["analysis_withheld"]["reason"]
        assert reply["analysis_withheld"]["withheld"] == "analysis"

    def test_no_ordering_result_survives_anywhere_in_the_partial_reply(self):
        # The whole JSON, not just the top level: an ordering tucked under
        # another key would still be quotable, and quotable is the failure.
        raw = _dispatch(_measured_rig()).result.content

        assert "row_order" not in raw
        assert "row_count" not in raw

    def test_withholding_is_not_an_error_report(self):
        # Catches: withholding implemented through the existing analysis-error
        # path. A partial read is an answer; nothing failed.
        reply = _read(_measured_rig())

        assert "analysis_error" not in reply

    def test_a_complete_read_still_carries_a_real_row_order(self):
        # Non-vacuity: withholding applied unconditionally would pass every
        # assertion above and fail here. A real value, not just the key.
        reply = _read(_complete_rig(8))

        assert "analysis_withheld" not in reply
        assert reply["analysis"]["row_order"]
        assert reply["analysis"]["row_count"] == 1
        assert reply["analysis"]["low_confidence"] is False


class TestTheShortfallIsArithmetic:
    """AC-TRUNCATE-003 — "19 of 18, 1 unseen", never "incomplete"."""

    def test_the_measured_rig_reports_nineteen_eighteen_one(self):
        # Catches: `missing` dropped, or `unseen_count` derived from the
        # children that arrived instead of the console's own count.
        assert _read(_measured_rig())["missing"] == {
            "expected": 19,
            "received": 18,
            "unseen_count": 1,
        }

    def test_the_cap_path_reports_its_own_different_numbers(self):
        # Non-vacuity for the pin above: a hardcoded 19/18/1 passes there and
        # fails here. Catches: `expected` filled from the arrivals, which is
        # the misreading `prechk/inventory.py` records as a real one.
        reply = _read(SpatialRig(_bar(CAP_FIXTURES + 3)))

        assert reply["missing"] == {
            "expected": CAP_FIXTURES + 3,
            "received": CAP_FIXTURES,
            "unseen_count": 3,
        }

    def test_an_unknown_total_is_reported_unknown_never_zero(self):
        # The responder raised its flag but sent no childCount, so the
        # shortfall is genuinely unknown. Catches: an implementation that
        # substitutes the arrival count for the total and then reports
        # "0 unseen" on a read it has just called incomplete.
        reply = _read(SpatialRig(_bar(18), flag=True, with_child_count=False))

        assert reply["truncated"] is True
        assert reply["missing"] == {"expected": None, "received": 18, "unseen_count": None}


class TestCompletePathIsUnchanged:
    """AC-TRUNCATE-004 — the non-breaking half, stated as a whole-shape pin."""

    def test_the_complete_reply_key_set_and_order_are_exactly_todays(self):
        # Catches: any key added to, removed from or reordered on the complete
        # path while the partial path was being built. The list is explicit on
        # purpose — a set comparison would not catch a reordering, and the
        # reply is serialised in insertion order.
        assert list(_read(_complete_rig())) == COMPLETE_REPLY_KEYS

    def test_the_complete_shape_survives_a_rig_that_stops_exactly_at_the_cap(self):
        # The boundary from the other side: spending the ENTIRE budget is not
        # being capped. Catches an off-by-one in the cap branch that would
        # divert a complete read into the partial shape.
        rig = SpatialRig(_bar(CAP_FIXTURES))
        reply = _read(rig)

        assert reply["roundtrip_capped"] is False
        assert list(reply) == COMPLETE_REPLY_KEYS
        assert len(rig.property_calls) == SPATIAL_PROPERTY_QUERY_CAP


class TestBothSignalsStaySeparate:
    """AC-TRUNCATE-005 — the BRANCH is unified; the two signals are not."""

    def test_console_truncation_and_budget_exhaustion_are_told_apart(self):
        # Only `roundtrip_capped` can be fixed by asking differently, so a
        # reader that cannot tell them apart cannot act. Catches: the two
        # fields merged into one `incomplete` boolean now that a single
        # predicate drives the shape.
        shortened = _read(_measured_rig())
        capped = _read(SpatialRig(_bar(CAP_FIXTURES + 1)))

        assert (shortened["truncated"], shortened["roundtrip_capped"]) == (True, False)
        assert (capped["truncated"], capped["roundtrip_capped"]) == (False, True)
        # Same shape from both, which is the point of unifying the branch.
        assert "fixtures" not in shortened
        assert "fixtures" not in capped

    def test_a_complete_read_reports_both_signals_false(self):
        # Non-vacuity: constants would pass one of the two cases above.
        reply = _read(_complete_rig())

        assert reply["truncated"] is False
        assert reply["roundtrip_capped"] is False


class TestPartialIsNotAFailure:
    """AC-TRUNCATE-006 — truncation is the DEFAULT path on the measured rig."""

    def test_a_partial_read_is_not_an_error_result(self):
        # Catches: is_error raised for a partial reply, which would feed the
        # self-correction loop a retry that can only read the same rig again.
        execution = _dispatch(_measured_rig())

        assert execution.result.is_error is False
        assert "partial_fixtures" in json.loads(execution.result.content)

    def test_a_container_that_never_answered_is_still_an_error(self):
        # Non-vacuity: the AC above does not erase every error. A container
        # that said nothing is a failed call, unchanged.
        class Silent:
            def query_state(self, path: str) -> dict:
                raise TimeoutError("no reply within 3.0s")

            def query_property(self, path: str, property_name: str) -> dict:
                raise AssertionError("must not be reached")

        execution = _dispatch(Silent())

        assert execution.result.is_error is True


class TestTheAbsentKeyStopsAShapeBlindConsumer:
    """Scenario 3 — the difference between a flag and an absence, executed."""

    def test_code_written_for_the_complete_shape_raises_instead_of_passing(self):
        # This is the enforcement mechanism itself, asserted rather than
        # described: a consumer that reads reply["fixtures"] cannot silently
        # treat 18 of 19 fixtures as the rig, because there is nothing there
        # to read. With a boolean flag this same consumer would have carried
        # on and been wrong quietly.
        partial = _read(_measured_rig())
        complete = _read(_complete_rig())

        def written_for_the_complete_shape(reply):
            return [fixture["fid"] for fixture in reply["fixtures"]]

        assert len(written_for_the_complete_shape(complete)) == 18
        with pytest.raises(KeyError):
            written_for_the_complete_shape(partial)


class TestTheInProcessConsumerWasMigrated:
    """AC-TRUNCATE-007 — the GROUPGEN partial-topology contract is unchanged."""

    def test_classify_still_judges_a_partial_read_and_marks_it_partial(self):
        # Catches: the one in-process consumer left reading reply["fixtures"]
        # (an immediate KeyError), and equally a migration that lost the
        # coverage annotation on the way.
        payload = json.loads(_dispatch(_measured_rig(), tool=CLASSIFY).result.content)

        assert payload["coverage"] == {"judged": 18, "of": 19, "complete": False}
        assert payload["topology_partial"] is True
        assert payload["topology_partial_reason"]
        assert payload["topology"]["partial"] is True
        assert payload["suggested_groups"]
        for group in payload["suggested_groups"]:
            assert group["topology_partial"] is True

    def test_classify_never_leaks_the_read_reply_shape_into_its_payload(self):
        # The migration is internal. Catches a consumer that "handled" the new
        # shape by forwarding the read reply into its own output.
        payload = json.loads(_dispatch(_measured_rig(), tool=CLASSIFY).result.content)

        assert "partial_fixtures" not in payload
        assert "fixtures" not in payload

    def test_a_complete_read_still_classifies_as_not_partial(self):
        # Non-vacuity for both above.
        payload = json.loads(_dispatch(_complete_rig(8), tool=CLASSIFY).result.content)

        assert payload["topology_partial"] is False
        assert payload["topology_partial_reason"] == ""


# -- the write half: a flag that did nothing, wired up ------------------------
#
# `create_arrangement_groups` re-reads the fixture container itself (it needs
# the group pool anyway), so the shortfall the acknowledgement is checked
# against comes from that fresh listing: childCount 5, four children, one
# fixture the write path never saw.


def _write_console(*, declared=5, listed=4, occupied_names=None):
    """Group pool + fixture container for the write path.

    ``declared`` vs ``listed`` is the shortfall the enumeration must match.
    """
    names = occupied_names or {}
    states: dict[str, dict] = {
        GROUPS_PATH: {
            "ok": True,
            "truncated": False,
            "node": {"childCount": 0},
            "children": [],
        },
        FIXTURES_PATH: {
            "ok": True,
            "truncated": True,
            "node": {"childCount": declared},
            "children": [{"i": slot, "name": f"Spot {slot}"} for slot in range(1, listed + 1)],
        },
    }
    properties: dict[tuple[str, str], dict] = {}
    for slot, name in names.items():
        states[f"{GROUPS_PATH}/{slot}"] = {"ok": True}
        properties[(f"{GROUPS_PATH}/{slot}", "Name")] = {"ok": True, "value": name}

    class WriteConsole:
        def query_state(self, path: str) -> dict:
            if path not in states:
                raise LookupError(f"unknown object path: {path}")
            return states[path]

        def query_property(self, path: str, property_name: str) -> dict:
            key = (path, property_name)
            if key not in properties:
                return {"ok": False, "error": f"property not readable: {property_name}"}
            return properties[key]

    return WriteConsole()


def _create(console, arguments, *, approve=True):
    port = RecordingExecutionPort()
    registry = build_toolset(
        execution_port=port,
        state_port=console,
        group_approval_port=ScriptedApprovalPort(approve=approve),
    )
    execution = registry.dispatch(ToolCall(id="call-1", name=CREATE, arguments=arguments))
    return execution, port


#: A group carrying the flag `classify_arrangement_topology` has stamped on
#: every geometric group since the GROUPGEN-024 amendment.
#:
#: fid 1 is deliberately NOT in it. `True == 1` in Python, so a group written
#: over fid 1 would make the disjointness check refuse `[True]` all by itself
#: — and the boolean test below would then pass even with the
#: `not isinstance(fid, bool)` exclusion deleted, binding itself to an
#: accident of the rig instead of to the line it exists to defend.
_PARTIAL_GROUP = {"name": "GEO Stage Left", "fids": [2, 3], "topology_partial": True}


class TestPartialGroupsCannotBeWrittenUnacknowledged:
    """AC-TRUNCATE-008 — the dead flag, wired to a refusal."""

    def test_a_partial_group_without_the_enumeration_is_refused_and_sends_nothing(self):
        # Catches: the refusal branch removed. On the pre-revision code this
        # assertion is ALREADY red — the handler never read `topology_partial`
        # at all, so the write simply proceeded. It pins a measured hole, not
        # a hypothetical one.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP]},
        )

        assert execution.result.is_error is True
        assert port.executed == []

    def test_the_refusal_names_the_group_that_came_from_a_partial_read(self):
        # A refusal that will not say WHICH group is one the caller can only
        # answer by guessing.
        execution, _port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP]},
        )

        assert "GEO Stage Left" in execution.result.content
        assert "acknowledged_unread_fids" in execution.result.content

    def test_a_correct_enumeration_lets_the_write_through(self):
        # The other side, and the one that proves this gate demands READING
        # rather than forbidding: 5 declared, 4 listed, so fid 5 is the one
        # the write path never saw. Catches: a refusal that cannot be
        # satisfied, which would be a functional outage dressed as safety.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": [5]},
        )

        assert execution.result.is_error is False
        assert json.loads(execution.result.content)["status"] == "created"
        assert port.executed

    def test_a_bare_boolean_is_not_an_acknowledgement(self):
        # The reflexively-filled value this argument shape exists to refuse.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": True},
        )

        assert execution.result.is_error is True
        assert port.executed == []

    def test_a_boolean_inside_the_list_is_not_a_fixture_id(self):
        # `True` IS an `int` in Python, so a plain isinstance(fid, int) check
        # would accept [True] as an enumeration of one fixture. Catches:
        # removal of the `not isinstance(fid, bool)` exclusion — the single
        # line that stops a boolean wearing a list.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": [True]},
        )

        assert execution.result.is_error is True
        assert port.executed == []

    def test_an_enumeration_that_names_a_fixture_being_written_is_refused(self):
        # fid 2 is in the group being stored, so it is one the read DID see.
        # Catches: removal of the disjointness check, which is the check that
        # forces the caller to look at the list it actually received.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": [2]},
        )

        assert execution.result.is_error is True
        assert port.executed == []

    def test_an_enumeration_of_the_wrong_size_is_refused(self):
        # The container reports one unseen fixture; naming three is not
        # reading, it is guessing. Catches: removal of the shortfall check.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": [5, 6, 7]},
        )

        assert execution.result.is_error is True
        assert port.executed == []

    def test_a_repeated_fid_does_not_pad_the_enumeration_to_size(self):
        # Two declared unseen, one real fid repeated: the size check alone
        # would pass. Catches: removal of the duplicate check.
        execution, port = _create(
            _write_console(declared=6, listed=4, occupied_names={1: "GEO Stage Left"}),
            {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": [5, 5]},
        )

        assert execution.result.is_error is True
        assert port.executed == []

    def test_an_unknown_total_still_requires_the_enumeration(self):
        # No childCount, so the shortfall cannot be checked — the other three
        # conditions still apply. Catches: a shortcut that skips the whole
        # gate whenever the size cannot be verified.
        console = _write_console(occupied_names={1: "GEO Stage Left"})
        console.query_state(FIXTURES_PATH).pop("node")

        refused, port = _create(console, {"groups": [_PARTIAL_GROUP]})
        accepted, _ = _create(
            console, {"groups": [_PARTIAL_GROUP], "acknowledged_unread_fids": [5]}
        )

        assert refused.result.is_error is True
        assert port.executed == []
        assert accepted.result.is_error is False

    def test_a_group_that_is_not_partial_writes_without_any_acknowledgement(self):
        # Non-vacuity, and the boundary of the whole gate: this is not a
        # blanket refusal of group writes. Catches: a check that fires on
        # every call regardless of provenance.
        execution, port = _create(
            _write_console(occupied_names={1: "GEO Stage Left"}),
            {"groups": [{"name": "GEO Stage Left", "fids": [1, 2], "topology_partial": False}]},
        )

        assert execution.result.is_error is False
        assert port.executed

    def test_a_species_group_carries_no_flag_and_is_unaffected(self):
        # Species groups are built from caller-supplied fixture-type records
        # and never carry `topology_partial` at all. Catches: a truthiness
        # test that mistook a missing key for a partial group.
        execution, port = _create(
            _write_console(occupied_names={1: "Robin MMX Spot"}),
            {"groups": [{"name": "Robin MMX Spot", "fids": [1, 2], "axis": "species"}]},
        )

        assert execution.result.is_error is False
        assert port.executed


class TestBoundariesDidNotMove:
    """AC-TRUNCATE-009 — a shape change, not a tool-surface change."""

    def test_the_closed_tool_set_is_still_twenty_two(self):
        # The mechanical refusal of the "add a confirmation tool" design.
        assert len(TOOL_NAMES) == 22

    def test_get_spatial_context_still_takes_no_arguments(self):
        # A required argument would make the FIRST call impossible: you would
        # need the reply to construct the call that produces it.
        registry = build_toolset(
            execution_port=RecordingExecutionPort(), state_port=_complete_rig(3)
        )
        definition = next(d for d in registry.definitions() if d.name == SPATIAL)

        assert definition.parameters == {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def test_the_new_write_argument_is_declared_and_optional(self):
        # `additionalProperties: False` means an undeclared argument is not
        # passable at all; `required` must still be groups alone, or every
        # ordinary group write breaks.
        registry = build_toolset(
            execution_port=RecordingExecutionPort(), state_port=_complete_rig(3)
        )
        definition = next(d for d in registry.definitions() if d.name == CREATE)

        assert definition.parameters["properties"]["acknowledged_unread_fids"]["items"] == {
            "type": "integer"
        }
        assert definition.parameters["required"] == ["groups"]
