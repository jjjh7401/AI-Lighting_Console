"""Spatial read tool tests (M1 — SPEC-COPILOT-SPATIAL-001).

``get_spatial_context`` is the READ half of the spatial axis: it asks the
console where every patched fixture physically stands, so that "left to right"
can mean something different on a 30-fixture bar than on a 3x10 grid.

Four properties are pinned here, and each one is a guard that has to go RED
when it is deleted:

  * **no coordinate is ever invented** (REQ-SPATIAL-004 / AC-SPATIAL-004). A
    fixture whose ``posx`` did not answer is reported ABSENT with the console's
    own reason. It never arrives with a zero, because a fabricated zero is
    indistinguishable from the all-(0,0,0) rig that was actually measured
    (progress.md §E.2.4) — the fabrication would be invisible in exactly the
    reply that matters.
  * **two incompleteness signals stay separate** (REQ-SPATIAL-006 /
    AC-SPATIAL-006). ``truncated`` is the console shortening its own list;
    ``roundtrip_capped`` is this tool running out of query budget. Only the
    second is fixable by asking differently, so collapsing them would destroy
    the caller's only way to tell "ask again" from "the console cut it".
  * **fixture ids come from the console** (REQ-SPATIAL-007). The container slot
    and the FID are different numbers, and the material below makes them
    disagree on purpose — a fixture at slot 1 whose fid is 101.
  * **the path reads and never writes.** No command is composed, the execution
    port is untouched, and the parameter schema accepts nothing a caller could
    point at a fixture.

The material mirrors the live onPC 2.4.2 measurements in ``progress.md §E.2``:
property reads answer with STRINGS (``"19"``, ``"0.0"``, ``"-3.5"``), an
unknown property answers ``ok:false`` with ``"property not readable: <name>"``
(the ``prop`` channel is discriminating — §E.2.1), and the calibration
container answers ``childCount: 19`` while delivering 18 children (§E.2.3).
Nothing here touches a real console.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    SPATIAL_FIXTURE_PROPERTIES,
    SPATIAL_PROPERTY_QUERY_CAP,
    SPATIAL_SOURCE_PATCH3D,
    TOOL_NAMES,
    build_toolset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_SOURCE = PROJECT_ROOT / "server" / "orchestrator" / "tools.py"

TOOL = "get_spatial_context"
FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]

#: Fixtures that fit under the round-trip cap, and the first one that does not.
CAP_FIXTURES = SPATIAL_PROPERTY_QUERY_CAP // len(SPATIAL_FIXTURE_PROPERTIES)


def _fixture(slot, fid, name, x="0.0", y="0.0", z="0.0"):
    """One fixture as the console reports it: strings, or ``None`` for unreadable."""
    return {"slot": slot, "fid": fid, "name": name, "posx": x, "posy": y, "posz": z}


def _bar(count, *, first_slot=1, first_fid=1, spacing=1.0):
    """A single row of ``count`` fixtures at distinct x, flat depth and height."""
    return [
        _fixture(
            first_slot + i,
            str(first_fid + i),
            f"PAR {first_fid + i}",
            x=f"{i * spacing:.1f}",
        )
        for i in range(count)
    ]


class SpatialRig:
    """State + property double for the stage patch container.

    ``declared`` overrides ``node.childCount`` so a container can honestly say
    it holds more fixtures than it handed over — the live truncation shape.
    ``flag`` is the responder's own ``truncated`` boolean; ``with_child_count``
    drops ``childCount`` entirely, which ``rig_section`` already treats as an
    unknown total.
    """

    def __init__(self, fixtures, *, declared=None, flag=False, with_child_count=True):
        self.fixtures = {entry["slot"]: entry for entry in fixtures}
        self.declared = len(fixtures) if declared is None else declared
        self.flag = flag
        self.with_child_count = with_child_count
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
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
                {"i": entry["slot"], "name": entry["name"], "class": "Fixture"}
                for entry in self.fixtures.values()
            ],
            "truncated": self.flag,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        slot = int(path.rsplit("/", 1)[1])
        # The live console's property lookup is case-INSENSITIVE (§E.2.1), so
        # the double must not make the tool's spelling load-bearing.
        value = self.fixtures[slot].get(property_name.lower())
        if value is None:
            return {
                "ok": False,
                "path": path,
                "property": property_name,
                "error": f"property not readable: {property_name}",
            }
        return {"ok": True, "path": path, "property": property_name, "value": value}


class RecordingExecutionPort:
    def __init__(self):
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


def _registry(rig, execution_port=None):
    return build_toolset(
        execution_port=execution_port or RecordingExecutionPort(),
        state_port=rig,
    )


def _read(rig) -> dict:
    execution = _registry(rig).dispatch(ToolCall(id="call-1", name=TOOL, arguments={}))
    assert execution.result.is_error is False
    return json.loads(execution.result.content)


def _fids(reply) -> list[int]:
    """Fids out of a COMPLETE reply.

    Deliberately shape-strict (SPEC-COPILOT-TRUNCATE-001): a partial reply has
    no ``fixtures`` key at all, so a helper that quietly accepted either shape
    would erase from these tests the exact distinction the divergence exists to
    create.
    """
    return [fixture["fid"] for fixture in reply["fixtures"]]


def _partial_fids(reply) -> list[int]:
    """Fids out of a PARTIAL reply — the other shape, named so that no test can
    take one for the other."""
    return [fixture["fid"] for fixture in reply["partial_fixtures"]]


class TestRegistration:
    def test_the_tool_is_in_all_three_places(self):
        # Dispatch, not a dict lookup: a handler registered without a
        # TOOL_NAMES entry still resolves in the map, and TOOL_NAMES is what
        # the provider advertises to the model.
        rig = SpatialRig(_bar(3))
        registry = _registry(rig)
        assert TOOL in TOOL_NAMES
        assert TOOL in {definition.name for definition in registry.definitions()}
        execution = registry.dispatch(ToolCall(id="probe", name=TOOL, arguments={}))
        assert "unknown tool" not in execution.result.content
        assert execution.result.name == TOOL

    def test_the_parameter_schema_accepts_no_arguments(self):
        # The handler reads the rig itself. A caller cannot aim it at a stage,
        # a slot or a fixture, which is the only way it cannot be aimed at the
        # wrong one (the discipline precheck_patch's schema already follows).
        registry = _registry(SpatialRig(_bar(3)))
        definition = next(d for d in registry.definitions() if d.name == TOOL)
        assert definition.description.strip()
        assert definition.parameters == {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }


class TestReadPathOnly:
    def test_the_handler_never_reaches_the_execution_port(self):
        port = RecordingExecutionPort()
        rig = SpatialRig(_bar(4))
        registry = _registry(rig, execution_port=port)
        registry.dispatch(ToolCall(id="call-1", name=TOOL, arguments={}))
        assert port.executed == []
        assert rig.state_calls == [FIXTURES_PATH]
        assert rig.property_calls  # non-vacuity: it DID read something

    def test_the_handler_body_names_neither_the_execution_port_nor_a_command(self):
        # Static half of the same claim: the fake above only proves this one
        # rig took no write branch.
        handler = _handler_ast(TOOL)
        names = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}
        attrs = {node.attr for node in ast.walk(handler) if isinstance(node, ast.Attribute)}
        assert names, "이름을 하나도 모으지 못하면 0건 판정이 공허하다"
        assert "execution_port" not in names | attrs
        assert "run_commands" not in names
        assert "bundle_gate" not in names

    def test_the_reply_names_its_source(self):
        # AC-SPATIAL-002 — a reply that cannot say which source answered is the
        # shape the field exists to prevent.
        assert _read(SpatialRig(_bar(3)))["source"] == SPATIAL_SOURCE_PATCH3D


class TestCoordinateInventionIsImpossible:
    """AC-SPATIAL-004 (mutation-required) — absence is an ITEM, never a zero.

    Every rig in this class is PARTIAL by arithmetic: a fixture whose
    coordinate does not parse never reaches the record list, so ``judged``
    falls short of the container's ``childCount`` and ``coverage.complete`` is
    False. That is the SAME predicate ``truncated`` trips, so these replies
    carry ``partial_fixtures`` and no ``fixtures`` key (AC-TRUNCATE-001). The
    invariant below is unchanged — it is simply asserted on the shape a short
    read actually returns.
    """

    def test_an_unreadable_axis_makes_the_fixture_absent_with_the_consoles_reason(self):
        rig = SpatialRig(
            [
                _fixture(1, "11", "PAR 1", x="-4.5", y="0.0", z="3.0"),
                _fixture(2, "12", "PAR 2", x=None, y="0.0", z="3.0"),
                _fixture(3, "13", "PAR 3", x="4.5", y="0.0", z="3.0"),
            ]
        )
        reply = _read(rig)

        assert _partial_fids(reply) == [11, 13]
        assert reply["unreadable"] == [
            {"fid": 12, "name": "PAR 2", "reason": "property not readable: posx"}
        ]
        # The load-bearing half: PAR 2 is not in the map AT ALL. Fill its x
        # with a default and it reappears here with a coordinate nobody read.
        assert all(fixture["fid"] != 12 for fixture in reply["partial_fixtures"])
        assert 0.0 not in [fixture["x"] for fixture in reply["partial_fixtures"]]

    def test_a_fixture_that_fails_on_the_second_axis_is_absent_whole(self):
        # posx answered, posy did not. A record with two real axes and one
        # invented one is the subtlest form of the same defect: it looks like
        # data. Nothing partial is emitted.
        rig = SpatialRig(
            [
                _fixture(1, "11", "PAR 1", x="-4.5", y="1.0", z="3.0"),
                _fixture(2, "12", "PAR 2", x="0.0", y=None, z="3.0"),
            ]
        )
        reply = _read(rig)

        assert _partial_fids(reply) == [11]
        assert reply["unreadable"] == [
            {"fid": 12, "name": "PAR 2", "reason": "property not readable: posy"}
        ]
        assert all("y" in fixture for fixture in reply["partial_fixtures"])

    def test_an_unparseable_coordinate_is_an_absence_not_a_zero(self):
        # The console answered ok with something that is not a number. That
        # produced no usable coordinate, so it is the same event as a failed
        # read — and emphatically not a reason to substitute one.
        rig = SpatialRig(
            [
                _fixture(1, "11", "PAR 1", x="-4.5"),
                _fixture(2, "12", "PAR 2", x="n/a"),
            ]
        )
        reply = _read(rig)

        assert _partial_fids(reply) == [11]
        assert reply["unreadable"] == [
            {"fid": 12, "name": "PAR 2", "reason": "posx is not a number: 'n/a'"}
        ]

    def test_a_non_finite_coordinate_is_refused(self):
        # float("nan") parses, then sorts unpredictably — a silent arbitrary
        # order is exactly what AC-SPATIAL-010 forbids downstream.
        rig = SpatialRig([_fixture(1, "11", "PAR 1", x="nan")])
        reply = _read(rig)

        assert reply["partial_fixtures"] == []
        assert reply["unreadable"] == [
            {"fid": 11, "name": "PAR 1", "reason": "posx is not finite: 'nan'"}
        ]

    def test_a_fixture_whose_fid_did_not_answer_comes_back_without_a_number(self):
        # AC-SPATIAL-007 — no identifier was established, so the entry carries
        # a name and a reason and NO number for anybody to address.
        rig = SpatialRig(
            [
                _fixture(1, None, "PAR 1", x="-4.5"),
                _fixture(2, "12", "PAR 2", x="4.5"),
            ]
        )
        reply = _read(rig)

        assert _partial_fids(reply) == [12]
        assert reply["unreadable"] == [{"name": "PAR 1", "reason": "property not readable: fid"}]
        assert "fid" not in reply["unreadable"][0]

    def test_a_child_with_no_container_slot_is_reported_absent_never_dropped(self):
        # The responder declined to establish this child's slot, so there is no
        # path to read a coordinate off. A fixture missing from BOTH lists is a
        # fixture nobody mentioned.
        rig = SpatialRig(_bar(2))
        rig.fixtures[1]["slot"] = 1
        original = rig.query_state

        def unslotted(path: str) -> dict:
            payload = original(path)
            payload["children"][0] = {"name": "PAR 1", "class": "Fixture"}
            return payload

        rig.query_state = unslotted  # type: ignore[method-assign]
        reply = _read(rig)

        assert _partial_fids(reply) == [2]
        assert reply["unreadable"] == [
            {"name": "PAR 1", "reason": "container slot not established by the responder"}
        ]

    def test_every_readable_fixture_carries_exactly_what_the_console_said(self):
        rig = SpatialRig(
            [
                _fixture(1, "11", "PAR 1", x="-4.5", y="0.0", z="3.0"),
                _fixture(2, "12", "PAR 2", x="0.0", y="0.0", z="3.0"),
                _fixture(3, "13", "PAR 3", x="4.5", y="2.5", z="3.25"),
            ]
        )
        reply = _read(rig)

        assert reply["fixtures"] == [
            {"fid": 11, "name": "PAR 1", "x": -4.5, "y": 0.0, "z": 3.0},
            {"fid": 12, "name": "PAR 2", "x": 0.0, "y": 0.0, "z": 3.0},
            {"fid": 13, "name": "PAR 3", "x": 4.5, "y": 2.5, "z": 3.25},
        ]
        assert reply["unreadable"] == []


class TestTruncationSignal:
    """AC-SPATIAL-006 (mutation-required) — the container's own item drop.

    A truncated read returns the PARTIAL shape (AC-TRUNCATE-001): the records
    are under ``partial_fixtures`` and there is no ``fixtures`` key to read.
    """

    def test_the_live_calibration_container_is_reported_truncated(self):
        # The exact measured shape (progress.md §E.2.3): childCount 19, 18
        # children delivered, truncated:true. The 19th fixture read back fine
        # when asked directly, so it is UNSEEN, not unreadable — and a reply
        # that stayed quiet would describe an 18-fixture rig that does not
        # exist. Material bigger than what arrives is what makes this test
        # discriminate at all (design.md §7's mutation trap).
        rig = SpatialRig(_bar(18), declared=19, flag=True)
        reply = _read(rig)

        assert reply["truncated"] is True
        assert len(reply["partial_fixtures"]) == 18
        # The 18 that DID arrive are complete, and the missing one is not
        # slandered as a read failure.
        assert reply["unreadable"] == []
        # Separate signals: nothing here hit the query budget.
        assert reply["roundtrip_capped"] is False

    def test_the_responders_own_flag_raises_it_when_no_child_count_arrives(self):
        # ``node.childCount`` may be absent (rig_section already treats that as
        # an unknown total), so the arithmetic cannot fire and only the flag
        # can. Delete the flag read and this goes red.
        rig = SpatialRig(_bar(18), flag=True, with_child_count=False)
        reply = _read(rig)

        assert reply["truncated"] is True
        assert len(reply["partial_fixtures"]) == 18

    def test_the_arithmetic_raises_it_when_the_flag_is_missing(self):
        # A responder that ever drops the flag still cannot make the loss
        # silent. Delete the childCount comparison and this goes red.
        rig = SpatialRig(_bar(18), declared=19, flag=False)
        reply = _read(rig)

        assert reply["truncated"] is True
        assert len(reply["partial_fixtures"]) == 18

    def test_a_complete_container_is_not_reported_truncated(self):
        # Non-vacuity for the three above: a hardcoded True would pass them all.
        reply = _read(SpatialRig(_bar(18), declared=18, flag=False))
        assert reply["truncated"] is False
        assert reply["roundtrip_capped"] is False


class TestRoundTripCap:
    """REQ-SPATIAL-006 — stopping is fine; stopping quietly is the defect.

    A capped read is incomplete for a different reason and returns the SAME
    partial shape (AC-TRUNCATE-005); a rig that stops exactly AT the cap is
    complete and keeps ``fixtures``.
    """

    def test_a_rig_past_the_cap_stops_and_says_so(self):
        rig = SpatialRig(_bar(CAP_FIXTURES + 1))
        reply = _read(rig)

        assert reply["roundtrip_capped"] is True
        assert len(reply["partial_fixtures"]) == CAP_FIXTURES
        # Spent the whole budget and not one round trip more.
        assert len(rig.property_calls) == SPATIAL_PROPERTY_QUERY_CAP
        # A different signal from the console shortening its own list.
        assert reply["truncated"] is False

    def test_the_fixtures_the_cap_skipped_are_unseen_not_unreadable(self):
        # acceptance.md §D: "누락분을 '판독 실패'가 아니라 '미판독'으로 구분".
        # Filing them as read failures would blame the console for a budget
        # this code owns.
        rig = SpatialRig(_bar(CAP_FIXTURES + 3))
        reply = _read(rig)

        assert reply["unreadable"] == []
        assert reply["roundtrip_capped"] is True
        assert max(_partial_fids(reply)) == CAP_FIXTURES

    def test_a_rig_exactly_at_the_cap_is_complete(self):
        # Non-vacuity + the off-by-one: the last fixture that fits must be read.
        rig = SpatialRig(_bar(CAP_FIXTURES))
        reply = _read(rig)

        assert reply["roundtrip_capped"] is False
        assert len(reply["fixtures"]) == CAP_FIXTURES
        assert len(rig.property_calls) == SPATIAL_PROPERTY_QUERY_CAP


class TestFixtureIdsComeFromTheConsole:
    """REQ-SPATIAL-007 — the slot is not the FID, and neither is the position."""

    def test_fids_are_read_not_counted(self):
        # Slots 1,2,3 carry fids 101,55,7 — no coincidence can make an
        # enumeration index or a list position produce this answer.
        rig = SpatialRig(
            [
                _fixture(1, "101", "PAR A", x="-2.0"),
                _fixture(2, "55", "PAR B", x="0.0"),
                _fixture(3, "7", "PAR C", x="2.0"),
            ]
        )
        reply = _read(rig)

        assert _fids(reply) == [101, 55, 7]
        assert _fids(reply) != [1, 2, 3]  # the slots
        assert _fids(reply) != [0, 1, 2]  # the positions

    def test_properties_are_read_off_the_slot_path_not_the_fid_path(self):
        # The addressing runs the other way: the SLOT is what the object tree
        # is keyed by, and non-contiguous slots are a real showfile shape.
        rig = SpatialRig(
            [
                _fixture(1, "101", "PAR A", x="-2.0"),
                _fixture(4, "55", "PAR B", x="0.0"),
                _fixture(5, "7", "PAR C", x="2.0"),
            ]
        )
        _read(rig)

        paths = [path for path, _ in rig.property_calls]
        assert set(paths) == {f"{FIXTURES_PATH}/{slot}" for slot in (1, 4, 5)}
        assert f"{FIXTURES_PATH}/101" not in paths
        assert list(dict.fromkeys(paths)) == [f"{FIXTURES_PATH}/{s}" for s in (1, 4, 5)]

    def test_the_two_rig_tools_return_different_numbers_for_the_same_rig(self):
        # REQ-SPATIAL-008 additivity, stated as behaviour rather than as a diff:
        # get_rig_context still presents the container SLOT as "no" and this
        # tool presents the console's FID. Collapsing either into the other
        # would be the slot-is-the-FID trap the repo already paid for.
        rig = SpatialRig(
            [
                _fixture(1, "101", "PAR A", x="-2.0"),
                _fixture(2, "55", "PAR B", x="2.0"),
            ]
        )
        registry = _registry(rig)
        spatial = json.loads(
            registry.dispatch(ToolCall(id="s", name=TOOL, arguments={})).result.content
        )
        rig_context = json.loads(
            registry.dispatch(ToolCall(id="r", name="get_rig_context", arguments={})).result.content
        )

        assert [obj["no"] for obj in rig_context["fixtures"]["objects"]] == [1, 2]
        assert _fids(spatial) == [101, 55]


class TestTheDegenerateRigIsARealReading:
    """acceptance.md §D — (0,0,0) everywhere is a rig nobody positioned, not a
    rig nobody could read."""

    def test_the_all_zero_nineteen_fixture_rig_reads_successfully(self):
        # Today's real console (progress.md §E.2.4): 19 fixtures, fid 1..19,
        # every one at (0.0, 0.0, 0.0).
        rig = SpatialRig(
            [_fixture(slot, str(slot), f"MMX {slot}") for slot in range(1, 20)],
        )
        execution = _registry(rig).dispatch(ToolCall(id="call-1", name=TOOL, arguments={}))
        reply = json.loads(execution.result.content)

        assert execution.result.is_error is False
        assert len(reply["fixtures"]) == 19
        assert reply["unreadable"] == []
        assert reply["truncated"] is False
        assert reply["roundtrip_capped"] is False
        assert all(
            (fixture["x"], fixture["y"], fixture["z"]) == (0.0, 0.0, 0.0)
            for fixture in reply["fixtures"]
        )

    def test_the_channel_proved_itself_per_object_on_the_same_round_trips(self):
        # Why the zeros are believed: the SAME reads that returned 19 identical
        # coordinate triples returned 19 DISTINCT fids and 19 distinct names.
        # A channel handing back a constant would not have done that.
        rig = SpatialRig(
            [_fixture(slot, str(slot), f"MMX {slot}") for slot in range(1, 20)],
        )
        reply = _read(rig)

        assert sorted(_fids(reply)) == list(range(1, 20))
        assert len({fixture["name"] for fixture in reply["fixtures"]}) == 19

    def test_it_is_flagged_low_confidence_rather_than_declared_a_row(self):
        # The honest demotion (REQ-SPATIAL-005 / AC-SPATIAL-011): a caller is
        # told the layout was not established instead of being handed a
        # left-to-right order the patch cannot support.
        rig = SpatialRig(
            [_fixture(slot, str(slot), f"MMX {slot}") for slot in range(1, 20)],
        )
        reply = _read(rig)

        assert reply["analysis"]["low_confidence"] is True
        assert reply["analysis"]["confidence_reason"] == "no_spatial_spread"
        assert reply["analysis"]["fixture_count"] == 19

    def test_a_positioned_bar_is_not_flagged(self):
        # Non-vacuity for the three above.
        reply = _read(SpatialRig(_bar(8, spacing=1.5)))

        assert reply["analysis"]["low_confidence"] is False
        assert reply["analysis"]["confidence_reason"] is None
        assert reply["analysis"]["row_count"] == 1
        assert reply["analysis"]["rows"][0]["fids"] == list(range(1, 9))


class TestAnalysisFoldIn:
    def test_row_structure_distinguishes_one_bar_from_three_rows(self):
        # The point of the whole axis (REQ-SPATIAL-011): the same instruction
        # must be able to produce a different chain on a different rig.
        bar = _read(SpatialRig(_bar(9, spacing=1.0)))
        grid = _read(
            SpatialRig(
                [
                    _fixture(
                        row * 3 + col + 1,
                        str(row * 3 + col + 1),
                        f"PAR {row * 3 + col + 1}",
                        x=f"{col * 1.0:.1f}",
                        y=f"{row * 5.0:.1f}",
                    )
                    for row in range(3)
                    for col in range(3)
                ]
            )
        )

        assert bar["analysis"]["row_count"] == 1
        assert grid["analysis"]["row_count"] == 3
        assert [row["fids"] for row in grid["analysis"]["rows"]] == [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]

    def test_a_duplicate_fid_costs_the_analysis_never_the_map(self):
        # Two records claiming one console identifier is a read defect the pure
        # layer refuses. The coordinate map plus the absence report is the
        # mandatory deliverable, so it survives.
        rig = SpatialRig(
            [
                _fixture(1, "11", "PAR 1", x="-2.0"),
                _fixture(2, "11", "PAR 2", x="2.0"),
            ]
        )
        reply = _read(rig)

        assert _fids(reply) == [11, 11]
        assert reply["analysis"] is None
        assert "11" in reply["analysis_error"]

    def test_an_empty_container_is_an_answer_carrying_its_own_demotion(self):
        # REQ-SPATIAL-005: the console answered, there is simply nothing
        # positioned. That is a signal, not a failed call.
        execution = _registry(SpatialRig([])).dispatch(
            ToolCall(id="call-1", name=TOOL, arguments={})
        )
        reply = json.loads(execution.result.content)

        assert execution.result.is_error is False
        assert reply["fixtures"] == []
        assert reply["analysis"]["low_confidence"] is True
        assert reply["analysis"]["confidence_reason"] == "no_fixtures"


class TestUnavailableCapability:
    def test_a_container_that_never_answers_is_a_failed_call(self):
        class Silent:
            def query_state(self, path: str) -> dict:
                raise TimeoutError("no reply within 3.0s")

            def query_property(self, path: str, property_name: str) -> dict:
                raise AssertionError("must not be reached when the container is silent")

        execution = _registry(Silent()).dispatch(ToolCall(id="call-1", name=TOOL, arguments={}))

        assert execution.result.is_error is True
        assert "no reply within 3.0s" in execution.result.content

    def test_an_unwired_property_port_says_so_instead_of_answering_zero_fixtures(self):
        # Coordinates live ONLY in properties. A narrow state-only double must
        # get "unavailable", never a clean-looking empty rig.
        class StateOnly:
            def query_state(self, path: str) -> dict:
                return {
                    "ok": True,
                    "path": path,
                    "node": {"childCount": 0},
                    "children": [],
                    "truncated": False,
                }

        execution = build_toolset(
            execution_port=RecordingExecutionPort(), state_port=StateOnly()
        ).dispatch(ToolCall(id="call-1", name=TOOL, arguments={}))

        assert execution.result.is_error is True
        assert "property_port" in execution.result.content

    def test_a_rig_paths_override_without_fixtures_fails_by_name(self):
        execution = build_toolset(
            execution_port=RecordingExecutionPort(),
            state_port=SpatialRig(_bar(2)),
            rig_paths={"groups": "DataPool/Groups"},
        ).dispatch(ToolCall(id="call-1", name=TOOL, arguments={}))

        assert execution.result.is_error is True
        assert "'fixtures'" in execution.result.content


def _handler_ast(name: str) -> ast.FunctionDef:
    """The shipped handler's own AST node, found by name in tools.py."""
    tree = ast.parse(TOOLS_SOURCE.read_text(encoding="utf-8"))
    matches = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1, f"expected exactly one {name} definition, found {len(matches)}"
    return matches[0]
