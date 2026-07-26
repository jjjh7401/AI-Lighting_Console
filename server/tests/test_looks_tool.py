"""M7 wiring — ``instantiate_look``, the tool that makes the look layer reachable.

M3 built the resolver, M4 built the bundle builder and wired ``run_look_bundle``
to the gate, M5 registered ``find_looks``. Every one of those passed its own
tests, and the chain was still unreachable from a model turn: nothing in
``TOOL_NAMES`` opened ``build_instantiation`` / ``resolve_roles``, and
``run_look_bundle`` had no production caller. A model that consulted the library
correctly could do nothing with the answer but hand-write a bundle.

The M4 tests could not see that, because they called ``run_look_bundle``
themselves. These tests enter where a model enters — ``registry.dispatch`` — so
a tool that is not registered fails them all.

Two properties this file exists to hold, beyond "it works":

* The instantiation path reaches the console through ``run_commands`` and
  nothing else (REQ-LOOKLIB-010/019). Asserted three ways: the gate sees the
  whole bundle as ONE screening, a gate that does not clear yields zero sends,
  and a structural scan of the handler shows it never names the execution port.
* Every number on the wire came from the rig. The tests vary the rig and assert
  the commands follow it, so a hardcoded pool or group number fails rather than
  passing on a fixture that happens to agree with it (AP-16).

Console contact: zero. Everything below is in-memory.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.looks.instantiate import (
    CAPTURE_PER_FAMILY,
    CAPTURE_SHARED,
    CONFLICT,
    NO_FREE_SLOT,
    POOL_UNADDRESSABLE,
    POOL_UNRESOLVED,
)
from server.looks.resolver import UNADDRESSABLE
from server.looks.roles import AMBIGUOUS, NO_MATCH
from server.looks.schema import AttributeValue, Look, LookLibrary
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    TOOL_NAMES,
    build_toolset,
)

TOOL = "instantiate_look"
GROUPS_PATH = "DataPool/Groups"
POOLS_PATH = "DataPool/PresetPools"


# -- fakes --------------------------------------------------------------------


class _RecordingPort:
    """Fake CommandExecutionPort — records every command that reached it."""

    def __init__(self, failures: frozenset[str] = frozenset()) -> None:
        self.failures = set(failures)
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        if command in self.failures:
            return ExecutionResult(ok=False, detail=f"syntax error near '{command}'")
        return ExecutionResult(ok=True, detail="OK")


class _RigStatePort:
    """Answers the two look sections and the preset-pool drill queries."""

    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


@dataclass(frozen=True)
class _CommandDecision:
    command: str
    status: str
    reasons: tuple[str, ...] = ()


@dataclass
class _RecordingGate:
    """Fake BundleGate — records each screened bundle, clears or refuses."""

    cleared: bool = True
    status: str = "ok"
    notice: str = ""
    screened: list[list[str]] = field(default_factory=list)

    def screen(self, commands):
        self.screened.append(list(commands))
        return _ScreenDecision(
            cleared=self.cleared,
            status=self.status,
            commands=tuple(
                _CommandDecision(
                    command=c,
                    status="ok" if self.cleared else "blocked",
                    reasons=() if self.cleared else ("live lock",),
                )
                for c in commands
            ),
            notice=self.notice,
        )


@dataclass(frozen=True)
class _ScreenDecision:
    cleared: bool
    status: str
    commands: tuple[_CommandDecision, ...]
    notice: str = ""


# -- rig assembly -------------------------------------------------------------
#
# RAW responder payloads, not pre-shaped sections: the tool must build the
# section shape with the producer's own helpers, so a fixture that hands it a
# finished section would test nothing about that half.


def _child(no: int | None, name: str) -> dict:
    # No "i" is how the responder says "this exists and I could not number it".
    return {"name": name} if no is None else {"i": no, "name": name}


def _payload(path: str, children: list[dict], *, truncated: bool = False) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": list(children),
        "node": {"childCount": len(children)},
        "truncated": truncated,
    }


DEFAULT_POOLS = (
    (1, "Dimmer"),
    (2, "Position"),
    (3, "Gobo"),
    (4, "Color"),
    (5, "Beam"),
    (6, "Focus"),
)
DEFAULT_GROUPS = ((11, "Back"),)


def _tree(
    *,
    groups: tuple[tuple[int | None, str], ...] = DEFAULT_GROUPS,
    pools: tuple[tuple[int | None, str], ...] = DEFAULT_POOLS,
    contents: dict[int, list[dict]] | None = None,
    undrillable: tuple[int, ...] = (),
    drop: tuple[str, ...] = (),
) -> dict[str, dict]:
    contents = contents or {}
    tree = {
        GROUPS_PATH: _payload(GROUPS_PATH, [_child(n, name) for n, name in groups]),
        POOLS_PATH: _payload(POOLS_PATH, [_child(n, name) for n, name in pools]),
    }
    for no, _name in pools:
        if no is None or no in undrillable:
            continue  # a pool the drill cannot open — occupancy stays unknown
        path = f"{POOLS_PATH}/{no}"
        tree[path] = _payload(path, contents.get(no, []))
    for path in drop:
        tree.pop(path, None)
    return tree


def _preset(no: int | None, name: str) -> dict:
    return _child(no, name)


# -- looks --------------------------------------------------------------------


DIMMER_AND_COLOR = (
    ("Dimmer", 80),
    ("ColorRGB_R", 100),
    ("ColorRGB_G", 25),
    ("ColorRGB_B", 0),
)


def _look(
    *,
    look_id: str = "test-look",
    display_name: str = "테스트 룩",
    roles: tuple[str, ...] = ("백라이트",),
    attributes: tuple[tuple[str, float], ...] = DIMMER_AND_COLOR,
) -> Look:
    return Look(
        look_id=look_id,
        display_name=display_name,
        genre="rock",
        dynamics=4,
        roles=roles,
        attributes=tuple(AttributeValue(name=n, value=v) for n, v in attributes),
    )


def _library(*looks: Look) -> LookLibrary:
    return LookLibrary(schema_version=1, looks=looks or (_look(),))


# -- dispatch -----------------------------------------------------------------


def _registry(*, library=None, tree=None, port=None, state=None, gate=None):
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=state or _RigStatePort(tree if tree is not None else _tree()),
        bundle_gate=gate,
        look_library=library if library is not None else _library(),
    )


def _dispatch(registry, arguments: dict | None = None):
    call = ToolCall(
        id="c1",
        name=TOOL,
        arguments={"look_id": "test-look"} if arguments is None else arguments,
    )
    execution = registry.dispatch(call)
    return execution, json.loads(execution.result.content)


def _definition(registry):
    return next(d for d in registry.definitions() if d.name == TOOL)


# =============================================================================
# registration
# =============================================================================


class TestToolRegistration:
    def test_the_tool_is_in_the_closed_tool_set(self):
        assert TOOL in TOOL_NAMES
        names = [d.name for d in _registry().definitions()]
        assert TOOL in names

    def test_the_look_is_named_by_the_id_find_looks_returns(self):
        # The handle is the id, because it is the only stable machine key in a
        # find_looks match — display names are Korean, editable in the assets
        # and may repeat.
        definition = _definition(_registry())
        assert definition.parameters["required"] == ["look_id"]
        assert "look_id" in definition.parameters["properties"]

    def test_the_description_points_back_at_find_looks_for_the_id(self):
        assert "find_looks" in _definition(_registry()).description

    def test_the_description_says_what_it_does_not_create(self):
        # v1 stores presets. The M7 live turn ended in a sequence + executor
        # assignment; a model that thinks this tool did that stops too early.
        description = _definition(_registry()).description.lower()
        assert "preset" in description
        assert "executor" in description

    def test_the_capture_shape_is_optional_and_enumerated(self):
        # The M0 FALLBACK branch stays reachable — an unreachable fallback is
        # the same defect this milestone is fixing, one layer down.
        shape = _definition(_registry()).parameters["properties"]["capture_shape"]
        assert set(shape["enum"]) == {CAPTURE_SHARED, CAPTURE_PER_FAMILY}
        assert "capture_shape" not in _definition(_registry()).parameters["required"]


# =============================================================================
# the bound path
# =============================================================================


class TestABoundLookReachesTheConsole:
    def test_a_look_that_binds_a_role_stores_its_presets(self):
        port = _RecordingPort()
        execution, payload = _dispatch(_registry(port=port))
        assert payload["executed"] is True
        assert execution.result.is_error is False
        assert port.executed[0] == "ChangeDestination Root"
        assert "Store Preset 1.1" in port.executed
        assert "Label Preset 1.1 '테스트 룩'" in port.executed
        assert port.executed[-1] == "ClearAll"

    def test_the_group_number_is_read_from_the_rig_not_assumed(self):
        # Same look, two rigs. A hardcoded selection passes one and fails the
        # other; only a number that came from the rig passes both.
        for number in (11, 7):
            port = _RecordingPort()
            _dispatch(_registry(port=port, tree=_tree(groups=((number, "Back"),))))
            assert f"Group {number}" in port.executed

    def test_the_pool_number_is_read_from_the_rig_not_assumed(self):
        port = _RecordingPort()
        pools = ((3, "Dimmer"), (9, "Color"))
        _dispatch(_registry(port=port, tree=_tree(pools=pools)))
        assert "Store Preset 3.1" in port.executed
        assert "Store Preset 9.1" in port.executed

    def test_the_report_rides_along_with_the_execution(self):
        _execution, payload = _dispatch(_registry())
        created = payload["report"]["created"]
        assert {(c["family"], c["pool"], c["slot"]) for c in created} == {
            ("Dimmer", 1, 1),
            ("Color", 4, 1),
        }
        assert payload["report"]["look_id"] == "test-look"

    def test_each_command_comes_back_with_its_own_status(self):
        # The same per-command shape run_commands returns, so the chat surface
        # renders a look bundle exactly as it renders any other bundle.
        _execution, payload = _dispatch(_registry())
        assert payload["all_ok"] is True
        assert {row["status"] for row in payload["commands"]} == {"executed_ok"}

    def test_the_per_command_outcomes_reach_the_runner(self):
        # The runner-facing half: without these the chat surface has no rows to
        # render and the turn reports a look bundle as if nothing ran.
        execution, payload = _dispatch(_registry())
        assert [o.command for o in execution.command_outcomes] == [
            row["command"] for row in payload["commands"]
        ]

    def test_a_failing_command_stops_the_bundle_and_is_reported(self):
        port = _RecordingPort(failures=frozenset({"Store Preset 1.1"}))
        execution, payload = _dispatch(_registry(port=port))
        assert execution.result.is_error is True
        assert payload["executed"] is False
        statuses = [row["status"] for row in payload["commands"]]
        assert "failed" in statuses
        assert "not_executed" in statuses


# =============================================================================
# nothing bound
# =============================================================================


class TestAnUnboundLookEmitsNothing:
    def test_a_look_whose_every_role_is_unmapped_sends_nothing(self):
        port = _RecordingPort()
        library = _library(_look(roles=("배경",)))  # the rig has no cyc group
        _execution, payload = _dispatch(_registry(port=port, library=library))
        assert port.executed == []
        assert payload["executed"] is False
        assert payload["report"]["commands"] == []

    def test_the_empty_bundle_is_an_answer_not_a_tool_failure(self):
        # A retry cannot bind a role this rig does not have; an is_error result
        # would feed the self-correction loop a problem it cannot solve.
        library = _library(_look(roles=("배경",)))
        execution, _payload = _dispatch(_registry(library=library))
        assert execution.result.is_error is False

    def test_the_report_names_the_role_it_could_not_bind(self):
        library = _library(_look(roles=("배경",)))
        _execution, payload = _dispatch(_registry(library=library))
        assert [u["role"] for u in payload["report"]["unmapped"]] == ["배경"]

    def test_nothing_is_substituted_for_the_unmapped_role(self):
        # The rig HAS a group; it is just not the one the role asked for.
        port = _RecordingPort()
        library = _library(_look(roles=("배경",)))
        _dispatch(_registry(port=port, library=library, tree=_tree(groups=((11, "Back"),))))
        assert port.executed == []


class TestTheThreeUnmappedReasonsStayApart:
    """REQ-LOOKLIB-013 (b) — no_match / ambiguous / unaddressable, unmerged.

    One dispatch produces all three at once, next to a role that DID bind, so
    the assertion also covers "a partial run is not reported as a whole one".
    """

    LIBRARY = _library(_look(roles=("백라이트", "사이드", "스페셜", "탑")))
    # "FrontBack Truss" is claimed by two roles -> ambiguous. "Side" carries no
    # number -> unaddressable. Nothing names a special -> no_match. "Top" binds.
    TREE = _tree(groups=((11, "FrontBack Truss"), (None, "Side"), (12, "Top")))

    def _report(self):
        _execution, payload = _dispatch(_registry(library=self.LIBRARY, tree=self.TREE))
        return payload["report"]

    def test_all_three_reasons_survive_as_separate_entries(self):
        reasons = {u["role"]: u["reason"] for u in self._report()["unmapped"]}
        assert reasons == {
            "백라이트": AMBIGUOUS,
            "사이드": UNADDRESSABLE,
            "스페셜": NO_MATCH,
        }

    def test_the_ambiguous_entry_names_the_group_that_caused_it(self):
        entry = next(u for u in self._report()["unmapped"] if u["reason"] == AMBIGUOUS)
        assert entry["groups"] == ["FrontBack Truss"]

    def test_the_unaddressable_entry_names_the_unnumbered_group(self):
        entry = next(u for u in self._report()["unmapped"] if u["reason"] == UNADDRESSABLE)
        assert entry["groups"] == ["Side"]

    def test_the_no_match_entry_implicates_no_group(self):
        entry = next(u for u in self._report()["unmapped"] if u["reason"] == NO_MATCH)
        assert entry["groups"] == []

    def test_the_bound_role_still_runs_and_the_run_is_not_called_complete(self):
        port = _RecordingPort()
        _execution, payload = _dispatch(_registry(port=port, library=self.LIBRARY, tree=self.TREE))
        assert "Group 12" in port.executed  # the one role that bound
        assert payload["executed"] is True
        assert payload["report"]["complete"] is False


# =============================================================================
# skips
# =============================================================================


class TestSkipsKeepTheirReasonAndTheirSlot:
    def test_a_name_conflict_is_skipped_with_its_pool_and_slot(self):
        tree = _tree(contents={1: [_preset(1, "테스트 룩")]})
        port = _RecordingPort()
        _execution, payload = _dispatch(_registry(port=port, tree=tree))
        skipped = payload["report"]["skipped"]
        assert [(s["family"], s["reason"], s["pool"], s["slot"]) for s in skipped] == [
            ("Dimmer", CONFLICT, 1, 2)
        ]
        assert not any(c.startswith("Store Preset 1.") for c in port.executed)

    def test_a_conflict_never_overwrites_and_never_reslots(self):
        tree = _tree(contents={1: [_preset(1, "테스트 룩")]})
        port = _RecordingPort()
        _dispatch(_registry(port=port, tree=tree))
        joined = " ".join(port.executed).casefold()
        assert "/overwrite" not in joined
        assert "Store Preset 1.2" not in port.executed

    def test_the_skip_unit_is_one_store_not_one_look(self):
        # Dimmer conflicts, Color does not: 1 created + 1 skipped, not 0 of one
        # and not a whole look thrown away.
        tree = _tree(contents={1: [_preset(1, "테스트 룩")]})
        _execution, payload = _dispatch(_registry(tree=tree))
        assert payload["report"]["skipped_count"] == 1
        assert [c["family"] for c in payload["report"]["created"]] == ["Color"]

    def test_an_unopened_pool_is_no_free_slot_not_an_empty_one(self):
        tree = _tree(undrillable=(1,))
        port = _RecordingPort()
        _execution, payload = _dispatch(_registry(port=port, tree=tree))
        skipped = {s["reason"]: s for s in payload["report"]["skipped"]}
        assert NO_FREE_SLOT in skipped
        assert skipped[NO_FREE_SLOT]["pool"] == 1
        assert skipped[NO_FREE_SLOT]["slot"] is None
        assert not any(c.startswith("Store Preset 1.") for c in port.executed)

    def test_a_family_with_no_pool_in_this_rig_is_pool_unresolved(self):
        tree = _tree(pools=((1, "Dimmer"),))  # no Color pool at all
        _execution, payload = _dispatch(_registry(tree=tree))
        skipped = {s["family"]: s for s in payload["report"]["skipped"]}
        assert skipped["Color"]["reason"] == POOL_UNRESOLVED
        assert skipped["Color"]["pool"] is None

    def test_a_pool_the_rig_could_not_number_is_pool_unaddressable(self):
        tree = _tree(pools=((1, "Dimmer"), (None, "Color")))
        _execution, payload = _dispatch(_registry(tree=tree))
        skipped = {s["family"]: s for s in payload["report"]["skipped"]}
        assert skipped["Color"]["reason"] == POOL_UNADDRESSABLE

    def test_the_two_pool_reasons_are_not_merged(self):
        # "there is no Color pool" and "there is one without an address" have
        # different repairs; one reason for both would erase that.
        _e1, missing = _dispatch(_registry(tree=_tree(pools=((1, "Dimmer"),))))
        _e2, unnumbered = _dispatch(_registry(tree=_tree(pools=((1, "Dimmer"), (None, "Color")))))
        reason_of = lambda p: next(  # noqa: E731
            s["reason"] for s in p["report"]["skipped"] if s["family"] == "Color"
        )
        assert reason_of(missing) != reason_of(unnumbered)


# =============================================================================
# the look id
# =============================================================================


class TestTheLookId:
    def test_an_unknown_id_is_a_structured_error(self):
        execution, payload = _dispatch(_registry(), {"look_id": "no-such-look"})
        assert execution.result.is_error is True
        assert "no-such-look" in payload["error"]

    def test_an_unknown_id_says_where_a_valid_one_comes_from(self):
        _execution, payload = _dispatch(_registry(), {"look_id": "no-such-look"})
        assert "find_looks" in payload["error"]

    def test_an_unknown_id_touches_neither_the_console_nor_the_rig(self):
        port, state = _RecordingPort(), _RigStatePort(_tree())
        _dispatch(_registry(port=port, state=state), {"look_id": "no-such-look"})
        assert port.executed == []
        assert state.queried == []

    @pytest.mark.parametrize("bad", [None, 5, "", "   ", ["test-look"], {"id": "test-look"}])
    def test_a_malformed_id_is_an_error_before_anything_is_read(self, bad):
        port, state = _RecordingPort(), _RigStatePort(_tree())
        execution, _payload = _dispatch(
            _registry(port=port, state=state), {} if bad is None else {"look_id": bad}
        )
        assert execution.result.is_error is True
        assert port.executed == []
        assert state.queried == []


# =============================================================================
# capture shape
# =============================================================================


class TestCaptureShape:
    def test_the_default_is_the_shared_capture(self):
        _execution, payload = _dispatch(_registry())
        assert payload["report"]["capture_shape"] == CAPTURE_SHARED

    def test_the_shared_capture_makes_one_cycle_for_two_families(self):
        port = _RecordingPort()
        _dispatch(_registry(port=port))
        assert port.executed.count("ClearAll") == 2  # opening + closing
        assert port.executed.count("Group 11") == 1
        assert len([c for c in port.executed if c.startswith("Store Preset")]) == 2

    def test_the_per_family_fallback_is_reachable_and_keeps_its_cycles(self):
        port = _RecordingPort()
        _execution, payload = _dispatch(
            _registry(port=port), {"look_id": "test-look", "capture_shape": CAPTURE_PER_FAMILY}
        )
        assert payload["report"]["capture_shape"] == CAPTURE_PER_FAMILY
        assert port.executed.count("ClearAll") == 3  # one per family + closing
        assert port.executed.count("Group 11") == 2  # re-selected per cycle
        assert len([c for c in port.executed if c.startswith("Store Preset")]) == 2

    def test_an_unknown_shape_is_refused_rather_than_silently_corrected(self):
        port = _RecordingPort()
        execution, payload = _dispatch(
            _registry(port=port), {"look_id": "test-look", "capture_shape": "whatever"}
        )
        assert execution.result.is_error is True
        assert "capture_shape" in payload["error"]
        assert port.executed == []


# =============================================================================
# the rig sections
# =============================================================================


class TestTheRigIsReadNotRetyped:
    def test_the_tool_reads_the_two_sections_it_needs_itself(self):
        state = _RigStatePort(_tree())
        _dispatch(_registry(state=state))
        assert GROUPS_PATH in state.queried
        assert POOLS_PATH in state.queried

    def test_a_missing_section_is_an_error_not_an_empty_rig(self):
        # The failure the model must never turn into "this rig has no
        # backlight": the section never arrived, so nothing about the rig's
        # groups was observed at all.
        port = _RecordingPort()
        execution, payload = _dispatch(_registry(port=port, tree=_tree(drop=(GROUPS_PATH,))))
        assert execution.result.is_error is True
        assert payload["rig_unavailable"]["groups"]["reason"] == REASON_UNRESOLVED
        assert port.executed == []

    def test_no_section_answering_reads_as_an_unreachable_console(self):
        _execution, payload = _dispatch(_registry(tree=_tree(drop=(GROUPS_PATH, POOLS_PATH))))
        assert payload["rig_unavailable"]["groups"]["reason"] == REASON_UNREACHABLE

    def test_an_unavailable_rig_reports_no_unmapped_verdict(self):
        # A verdict about roles requires a rig; there was none to judge.
        _execution, payload = _dispatch(_registry(tree=_tree(drop=(GROUPS_PATH,))))
        assert "report" not in payload

    def test_the_same_rig_with_both_sections_does_execute(self):
        # Control: the zero above is caused by the missing section, not by a
        # look that was never going to send anything.
        port = _RecordingPort()
        _dispatch(_registry(port=port))
        assert port.executed

    def test_the_configured_section_paths_are_used_not_hardcoded_ones(self):
        # A rig whose sections live elsewhere still binds — the tool asks
        # rig_paths, exactly as get_rig_context does.
        paths = {"groups": "Show/Grp", "preset_pools": "Show/Pools"}
        tree = {
            "Show/Grp": _payload("Show/Grp", [_child(11, "Back")]),
            "Show/Pools": _payload("Show/Pools", [_child(1, "Dimmer"), _child(4, "Color")]),
            "Show/Pools/1": _payload("Show/Pools/1", []),
            "Show/Pools/4": _payload("Show/Pools/4", []),
        }
        state = _RigStatePort(tree)
        port = _RecordingPort()
        registry = build_toolset(
            execution_port=port,
            state_port=state,
            rig_paths=paths,
            look_library=_library(),
        )
        _execution, payload = _dispatch(registry)
        assert payload["executed"] is True
        assert state.queried[:2] == ["Show/Grp", "Show/Pools"]

    def test_a_rig_configured_without_one_of_the_two_sections_is_refused(self):
        # Half a rig binds half a look silently; say so instead.
        port = _RecordingPort()
        registry = build_toolset(
            execution_port=port,
            state_port=_RigStatePort(_tree()),
            rig_paths={"groups": GROUPS_PATH},
            look_library=_library(),
        )
        execution, payload = _dispatch(registry)
        assert execution.result.is_error is True
        assert "preset_pools" in payload["error"]
        assert port.executed == []

    def test_the_pool_drill_runs_even_where_rig_context_has_it_switched_off(self):
        # Occupancy is not optional on this path: without opening the pool no
        # slot can be claimed free, so every store would be skipped as
        # unobserved — safe, and useless. get_rig_context's own drilldown
        # configuration is left untouched.
        state = _RigStatePort(_tree())
        registry = build_toolset(
            execution_port=_RecordingPort(),
            state_port=state,
            rig_drilldown=(),
            look_library=_library(),
        )
        _execution, payload = _dispatch(registry)
        assert f"{POOLS_PATH}/1" in state.queried
        assert payload["report"]["created"], payload["report"]["skipped"]


# =============================================================================
# the single execution path
# =============================================================================


class TestInstantiationReachesTheConsoleOnlyThroughRunCommands:
    """REQ-LOOKLIB-010 / 019 — one screening path, one execution surface."""

    def test_the_whole_bundle_is_screened_as_one_bundle(self):
        gate = _RecordingGate()
        port = _RecordingPort()
        _dispatch(_registry(port=port, gate=gate))
        assert len(gate.screened) == 1
        assert gate.screened[0] == port.executed

    def test_a_gate_that_does_not_clear_yields_zero_console_sends(self):
        gate = _RecordingGate(cleared=False, status="locked")
        port = _RecordingPort()
        execution, payload = _dispatch(_registry(port=port, gate=gate))
        assert gate.screened, "non-vacuity: the gate must have been consulted"
        assert port.executed == []
        assert payload["executed"] is False
        assert execution.result.is_error is True

    def test_a_refused_bundle_still_comes_back_with_its_report(self):
        gate = _RecordingGate(cleared=False, status="locked")
        _execution, payload = _dispatch(_registry(gate=gate))
        assert payload["report"]["look_id"] == "test-look"
        assert payload["gate_status"] == "locked"

    def test_an_empty_bundle_is_never_screened_at_all(self):
        gate = _RecordingGate()
        library = _library(_look(roles=("배경",)))
        _dispatch(_registry(gate=gate, library=library))
        assert gate.screened == []


class TestTheHandlerNamesNoExecutionSurface:
    """The structural half of the claim above (the M4/M5 AST-scan discipline).

    A behavioural test proves the gate saw THIS bundle; it cannot prove a
    future edit will not add a second route. This one reads the handler's own
    body: it may name ``run_commands`` and must never name the execution port.
    """

    @staticmethod
    def _handler(name: str) -> ast.FunctionDef:
        import server.orchestrator.tools as tools

        tree = ast.parse(Path(tools.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        raise AssertionError(f"no handler named {name!r} in tools.py")

    @classmethod
    def _identifiers(cls, name: str) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(cls._handler(name)):
            if isinstance(node, ast.Attribute):
                found.add(node.attr)
            elif isinstance(node, ast.Name):
                found.add(node.id)
        return found

    def test_the_handler_calls_the_run_commands_tool(self):
        assert "run_commands" in self._identifiers(TOOL)

    def test_the_handler_never_names_the_execution_port(self):
        identifiers = self._identifiers(TOOL)
        assert "execution_port" not in identifiers
        assert "execute" not in identifiers

    def test_the_scan_is_not_vacuous(self):
        # The same scan over the handler that DOES execute must see both.
        identifiers = self._identifiers("run_commands")
        assert "execution_port" in identifiers
        assert "execute" in identifiers

    def test_the_handler_body_is_substantial(self):
        # A scan over an empty or wrongly-located function passes for the wrong
        # reason; the handler has a real body.
        assert len(self._identifiers(TOOL)) > 15
