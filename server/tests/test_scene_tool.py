"""M6 wiring — ``find_scene`` / ``compile_scene``, the two tools that make the
scene layer reachable from a model turn.

M1 built the schema, M2 the library, M3 the matcher, M4 the bundle builder and
guards, M5 the claim-separating report. Every one passed its own tests and the
chain was still unreachable: nothing in ``TOOL_NAMES`` opened ``match_scene`` or
the compiler, so a model asked for "파란 백라이트가 천천히 웨이브하는 씬" could
only hand-write the bundle with ``run_commands`` — the one path where the
combination order M0 measured is enforced by nothing.

These tests enter where a model enters — ``registry.dispatch`` — so a tool that
is not registered fails them all.

Four properties this file holds beyond "it works":

* The compile path reaches the console through ``run_commands`` and nothing else
  (REQ-SCENE-018/019). Asserted three ways: the gate sees the whole bundle as
  ONE screening, a gate that does not clear yields zero sends, and a structural
  scan of both handlers shows neither ever names the execution port.
* The target group came from the rig. An unlisted group is refused before a
  single command is sent, because ``Group 7`` on a rig without group 7 selects
  nothing and the ``Store`` that follows writes an EMPTY cue — silently, since a
  stored cue's content is not machine-readable (spec.md §C.1).
* A fixture slot is not a group. ``Fixture <slot>`` never appears in a bundle and
  a slot number that is not a listed group is refused.
* The report's four claims survive the tool boundary — the payload carries them
  as separate keys, and the effect notice is there on the SUCCESS path too.

Console contact: zero. Everything below is in-memory.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from server.fx.schema import Fx, FxLibrary, FxStep, StepValue
from server.llm.types import ToolCall
from server.looks.schema import AttributeValue, Look, LookLibrary
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    TOOL_NAMES,
    build_toolset,
)
from server.scene.compile import CUE_OCCUPIED, SCENE_UNIFORM_ATTRIBUTES
from server.scene.report import (
    EFFECT_EVIDENCE_NOTICE,
    TRACKING_UNOBSERVABLE_NOTICE,
    UNCLAIMED_ENUMERATION_NOTE,
)
from server.scene.schema import Scene, SceneLibrary

FIND = "find_scene"
COMPILE = "compile_scene"
GROUPS_PATH = "DataPool/Groups"
SEQUENCES_PATH = "DataPool/Sequences"


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
    """Answers the two scene sections (groups, sequences) and nothing else."""

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


@dataclass(frozen=True)
class _ScreenDecision:
    cleared: bool
    status: str
    commands: tuple[_CommandDecision, ...]
    notice: str = ""


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
                    status="ok" if self.cleared else "proposal",
                    reasons=() if self.cleared else ("live lock",),
                )
                for c in commands
            ),
            notice=self.notice,
        )


# -- rig assembly -------------------------------------------------------------
#
# RAW responder payloads, not pre-shaped sections: the tool must build the
# section shape with the producer's own helpers.


def _child(no: int | None, name: str) -> dict:
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


DEFAULT_GROUPS = ((11, "Back"), (12, "Front"))
DEFAULT_SEQUENCES = ((1, "Opening"), (2, "Ballad"))


def _tree(
    *,
    groups: tuple[tuple[int | None, str], ...] = DEFAULT_GROUPS,
    sequences: tuple[tuple[int | None, str], ...] = DEFAULT_SEQUENCES,
    groups_truncated: bool = False,
    drop: tuple[str, ...] = (),
) -> dict[str, dict]:
    tree = {
        GROUPS_PATH: _payload(
            GROUPS_PATH,
            [_child(n, name) for n, name in groups],
            truncated=groups_truncated,
        ),
        SEQUENCES_PATH: _payload(SEQUENCES_PATH, [_child(n, name) for n, name in sequences]),
    }
    for path in drop:
        tree.pop(path, None)
    return tree


# -- upstream entries ---------------------------------------------------------


def _look(look_id: str = "look-blue") -> Look:
    return Look(
        look_id=look_id,
        display_name="파란 워시",
        genre="worship",
        dynamics=2,
        roles=("백라이트",),
        attributes=(
            AttributeValue(name="Dimmer", value=80),
            AttributeValue(name="ColorRGB_R", value=10),
            AttributeValue(name="ColorRGB_G", value=20),
            AttributeValue(name="ColorRGB_B", value=90),
        ),
    )


def _fx(fx_id: str = "pulse-beat") -> Fx:
    return Fx(
        fx_id=fx_id,
        display_name="펄스",
        pattern="pulse",
        steps=(
            FxStep(values=(StepValue(attribute="Dimmer", value=100.0),)),
            FxStep(values=(StepValue(attribute="Dimmer", value=0.0),)),
        ),
        phase_from=0.0,
        phase_to=360.0,
        speed=60.0,
    )


def _scene(
    scene_id: str = "blue-wave",
    *,
    look_id: str | None = "look-blue",
    fx_id: str | None = "pulse-beat",
    label: str = "SCN BLUE",
) -> Scene:
    return Scene(
        scene_id=scene_id,
        display_name="파란 펄스",
        label=label,
        look_id=look_id,
        fx_id=fx_id,
        aliases=("파란 펄스",),
        mood_keywords=("차분한",),
    )


def _libraries(*scenes: Scene):
    return (
        SceneLibrary(schema_version=1, scenes=scenes or (_scene(),)),
        LookLibrary(schema_version=1, looks=(_look(),)),
        FxLibrary(schema_version=1, fx=(_fx(),)),
    )


# -- dispatch -----------------------------------------------------------------


def _registry(*, scenes=None, tree=None, port=None, state=None, gate=None):
    scene_lib, look_lib, fx_lib = _libraries(*(scenes or ()))
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=state or _RigStatePort(tree if tree is not None else _tree()),
        bundle_gate=gate,
        look_library=look_lib,
        fx_library=fx_lib,
        scene_library=scene_lib,
    )


def _dispatch(registry, tool: str, arguments: dict, context=None):
    call = ToolCall(id="c1", name=tool, arguments=arguments)
    execution = registry.dispatch(call, context)
    return execution, json.loads(execution.result.content)


def _compile(registry, arguments: dict | None = None, context=None):
    return _dispatch(
        registry,
        COMPILE,
        {"scene_id": "blue-wave", "group": 11} if arguments is None else arguments,
        context,
    )


def _lines(payload) -> list[str]:
    """The command STRINGS out of a run_commands payload.

    The payload carries per-command dicts (status + detail); the report carries
    counts, not the bundle. Everything below asserts on the lines that actually
    reached the path, which is the surface the gate and the dedupe see.
    """
    return [entry["command"] for entry in payload["commands"]]


def _definition(registry, tool: str):
    return next(d for d in registry.definitions() if d.name == tool)


# =============================================================================
# registration
# =============================================================================


class TestToolRegistration:
    def test_both_tools_are_in_the_closed_tool_set(self):
        assert FIND in TOOL_NAMES
        assert COMPILE in TOOL_NAMES

    def test_both_tools_are_offered_to_the_model(self):
        names = [d.name for d in _registry().definitions()]
        assert FIND in names
        assert COMPILE in names

    def test_compile_scene_requires_only_the_id_and_the_group(self):
        # Everything else is measured here or named by the operator; requiring a
        # sequence number would invite the model to invent one.
        definition = _definition(_registry(), COMPILE)
        assert definition.parameters["required"] == ["scene_id", "group"]
        assert definition.parameters["additionalProperties"] is False

    def test_the_description_routes_the_model_away_from_the_two_tool_chain(self):
        # design.md §2.1 — the chain does not work and fails silently, so the
        # tool description is the only place that can head it off.
        text = _definition(_registry(), COMPILE).description
        assert "instantiate_look" in text
        assert "instantiate_fx" in text

    def test_the_description_states_the_effect_limit(self):
        text = _definition(_registry(), COMPILE).description
        assert "human" in text.lower()

    def test_the_description_names_the_unclaimed_axis_as_may(self):
        # AC-SCENE-024's wording limit reaches the model surface too.
        text = _definition(_registry(), COMPILE).description
        assert "unclaimed_attributes" in text
        assert "MAY" in text or "may" in text


# =============================================================================
# find_scene — lookup only
# =============================================================================


class TestFindScene:
    def test_a_match_returns_the_two_axes_separately(self):
        _execution, payload = _dispatch(_registry(), FIND, {"query": "파란 펄스"})
        assert "look" in payload
        assert "fx" in payload

    def test_a_lookup_sends_nothing_to_the_console(self):
        port = _RecordingPort()
        registry = _registry(port=port)
        _dispatch(registry, FIND, {"query": "파란 펄스"})
        assert port.executed == []

    def test_a_miss_is_an_answer_not_a_tool_error(self):
        execution, payload = _dispatch(_registry(), FIND, {"query": "존재하지 않는 무언가"})
        assert execution.result.is_error is False
        assert payload["fallback"] is True

    def test_a_non_string_query_is_a_tool_error(self):
        execution, payload = _dispatch(_registry(), FIND, {"query": 7})
        assert execution.result.is_error is True
        assert "query" in payload["error"]


# =============================================================================
# compile_scene — the group must come from the rig (AC-SCENE-018)
# =============================================================================


class TestGroupMustBeAddressable:
    def test_a_listed_group_is_accepted(self):
        execution, payload = _compile(_registry())
        assert execution.result.is_error is False
        assert payload["succeeded"] is True

    def test_an_unlisted_group_is_refused_before_anything_is_sent(self):
        port = _RecordingPort()
        execution, payload = _compile(_registry(port=port), {"scene_id": "blue-wave", "group": 7})
        assert execution.result.is_error is True
        assert "not addressable" in payload["error"]
        assert payload["groups"] == [11, 12]
        assert port.executed == []

    def test_a_truncated_group_listing_does_not_license_an_unlisted_number(self):
        # Absence from a cut list is not evidence of absence — but it is not
        # evidence of presence either, and addressing it would assume the latter.
        registry = _registry(tree=_tree(groups_truncated=True))
        execution, payload = _compile(registry, {"scene_id": "blue-wave", "group": 7})
        assert execution.result.is_error is True
        assert payload["groups_truncated"] is True

    def test_a_fixture_slot_number_is_not_a_group(self):
        # A fixture slot is not a group and not an FID (spec.md §A). Passing one
        # reaches the same refusal as any unlisted number — and no command that
        # names a fixture is ever emitted.
        port = _RecordingPort()
        execution, _payload = _compile(
            _registry(port=port), {"scene_id": "blue-wave", "group": 101}
        )
        assert execution.result.is_error is True
        assert port.executed == []

    def test_no_bundle_ever_targets_a_fixture(self):
        _execution, payload = _compile(_registry())
        assert not [c for c in _lines(payload) if "Fixture" in c]

    @pytest.mark.parametrize("group", [0, -1, "11", 11.0, True, None])
    def test_a_non_positive_integer_group_is_refused(self, group):
        execution, payload = _compile(_registry(), {"scene_id": "blue-wave", "group": group})
        assert execution.result.is_error is True
        assert "group" in payload["error"]

    def test_an_unknown_scene_id_is_a_correctable_error(self):
        execution, payload = _compile(_registry(), {"scene_id": "nope", "group": 11})
        assert execution.result.is_error is True
        assert "unknown scene_id" in payload["error"]

    def test_a_missing_rig_section_is_reported_not_assumed(self):
        registry = _registry(tree=_tree(drop=(GROUPS_PATH,)))
        execution, payload = _compile(registry)
        assert execution.result.is_error is True
        assert "did not arrive" in payload["error"]


# =============================================================================
# the single execution path (REQ-SCENE-019)
# =============================================================================


class TestSingleExecutionPath:
    def test_the_gate_screens_the_whole_bundle_once(self):
        gate = _RecordingGate()
        registry = _registry(gate=gate)
        _execution, payload = _compile(registry)
        assert len(gate.screened) == 1
        assert gate.screened[0] == _lines(payload)

    def test_a_gate_that_does_not_clear_sends_nothing(self):
        port = _RecordingPort()
        gate = _RecordingGate(cleared=False, status="locked", notice="live lock")
        registry = _registry(port=port, gate=gate)
        execution, payload = _compile(registry)
        assert port.executed == []
        assert payload["gate_status"] == "locked"
        # A LiveLock demotion is an ANSWER, not a failure (REQ-SCENE-020).
        assert execution.result.is_error is False
        assert payload["succeeded"] is False

    def test_the_store_line_is_visible_in_the_proposal(self):
        # The operator must be able to see what would have fired.
        gate = _RecordingGate(cleared=False, status="locked")
        _execution, payload = _compile(_registry(gate=gate))
        assert [c for c in gate.screened[0] if c.startswith("Store ")]

    def test_the_bundle_reaches_the_port_in_order_when_the_gate_clears(self):
        port = _RecordingPort()
        _execution, payload = _compile(_registry(port=port))
        assert port.executed == _lines(payload)


class TestNoSecondExecutionSurface:
    """A structural scan: the handlers must not name the execution port."""

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

    def test_the_compile_handler_calls_the_run_commands_tool(self):
        assert "run_commands" in self._identifiers(COMPILE)

    @pytest.mark.parametrize("handler", [FIND, COMPILE])
    def test_no_scene_handler_names_the_execution_port(self, handler):
        identifiers = self._identifiers(handler)
        assert "execution_port" not in identifiers
        assert "execute" not in identifiers

    def test_the_lookup_handler_reaches_no_execution_path_at_all(self):
        assert "run_commands" not in self._identifiers(FIND)

    def test_the_scan_is_not_vacuous(self):
        identifiers = self._identifiers("run_commands")
        assert "execution_port" in identifiers
        assert "execute" in identifiers

    def test_the_handler_body_is_substantial(self):
        assert len(self._identifiers(COMPILE)) > 15


# =============================================================================
# the scene layer's own rules survive the tool boundary
# =============================================================================


class TestSceneRulesHoldThroughTheTool:
    def test_the_store_line_carries_no_flag(self):
        _execution, payload = _compile(_registry())
        stores = [c for c in _lines(payload) if c.startswith("Store ")]
        assert len(stores) == 1
        blob = "\n".join(_lines(payload)).lower()
        assert "/merge" not in blob
        assert "/overwrite" not in blob
        assert "/cueonly" not in blob

    def test_the_look_value_line_precedes_the_step_column(self):
        _execution, payload = _compile(_registry())
        commands = _lines(payload)
        first_step = next(i for i, c in enumerate(commands) if c == "Step 2")
        value_line = next(i for i, c in enumerate(commands) if ";" in c)
        assert value_line < first_step

    def test_the_uniform_attributes_reach_the_report(self):
        _execution, payload = _compile(_registry())
        assert payload["report"]["uniform_attributes"] == list(SCENE_UNIFORM_ATTRIBUTES)

    def test_a_requested_cue_number_lands_in_the_store_line(self):
        _execution, payload = _compile(
            _registry(), {"scene_id": "blue-wave", "group": 11, "cue": 3}
        )
        stores = [c for c in _lines(payload) if c.startswith("Store ")]
        assert " Cue 3 " in stores[0]

    def test_an_occupied_sequence_number_is_refused_before_any_cue_question(self):
        # Why the tool can never reach CUE_OCCUPIED, stated as a test rather
        # than as a comment: `select_sequence_number` (fx's, decision H) refuses
        # an occupied sequence, so the sequence this tool stores into is always
        # new — and a new sequence holds no cues. The CUE_OCCUPIED guard is real
        # but belongs to the compile layer, where test_scene_compile.py holds it.
        execution, payload = _compile(
            _registry(), {"scene_id": "blue-wave", "group": 11, "sequence": 1}
        )
        assert execution.result.is_error is True
        assert payload["reason"] == "sequence_occupied"

    @pytest.mark.parametrize(
        ("key", "value"),
        [("cue", 0), ("cue", 1.5), ("sequence", -1), ("trig_type", "follow")],
    )
    def test_the_timing_argument_schema_is_the_scene_layers_own(self, key, value):
        # `parse_timing` (M1) is where a legal cue number is defined; the tool
        # calls it rather than re-checking the range here.
        execution, payload = _compile(
            _registry(), {"scene_id": "blue-wave", "group": 11, key: value}
        )
        assert execution.result.is_error is True
        assert (
            key.replace("sequence", "sequence_number").replace("cue", "cue_number")
            in payload["error"]
            or key in payload["error"]
        )

    def test_a_trigger_reaches_the_bundle_as_property_lines(self):
        _execution, payload = _compile(
            _registry(),
            {"scene_id": "blue-wave", "group": 11, "trig_type": "Follow", "trig_time": 14},
        )
        commands = _lines(payload)
        assert [c for c in commands if "Property 'TrigType' 'Follow'" in c]
        assert [c for c in commands if "Property 'TrigTime' 14" in c]
        assert not [c for c in commands if "/trig=" in c]

    def test_an_executor_is_only_assigned_when_asked(self):
        _execution, without = _compile(_registry())
        assert not [c for c in _lines(without) if c.startswith("Assign ")]
        _execution, with_executor = _compile(
            _registry(), {"scene_id": "blue-wave", "group": 11, "executor": 7}
        )
        assign = [c for c in _lines(with_executor) if c.startswith("Assign ")]
        assert assign == ["Assign Sequence 3 At Executor 7"]

    def test_a_non_ascii_label_override_is_refused(self):
        # The override lands in the same Store literal as an authored label, so
        # it obeys the same rule — one definition, in the loader.
        execution, payload = _compile(
            _registry(), {"scene_id": "blue-wave", "group": 11, "label": "파란 씬"}
        )
        assert execution.result.is_error is True
        assert "label" in payload["error"]

    def test_an_ascii_label_override_reaches_the_store_line(self):
        _execution, payload = _compile(
            _registry(), {"scene_id": "blue-wave", "group": 11, "label": "OPERATOR NAME"}
        )
        stores = [c for c in _lines(payload) if c.startswith("Store ")]
        assert stores[0].endswith("'OPERATOR NAME'")

    def test_an_fx_only_scene_compiles_without_a_look(self):
        scene = _scene("fx-only", look_id=None)
        _execution, payload = _compile(
            _registry(scenes=(scene,)), {"scene_id": "fx-only", "group": 11}
        )
        assert payload["succeeded"] is True
        assert payload["report"]["uniform_attributes"] == []

    def test_a_broken_reference_is_reported_not_compiled_around(self):
        scene = _scene("broken", look_id="no-such-look")
        execution, payload = _compile(
            _registry(scenes=(scene,)), {"scene_id": "broken", "group": 11}
        )
        assert execution.result.is_error is True
        assert "no-such-look" in payload["error"]


# =============================================================================
# the report's claims survive the tool boundary (REQ-SCENE-014)
# =============================================================================


class TestClaimsReachTheModel:
    def test_the_four_claims_are_separate_keys_in_the_payload(self):
        _execution, payload = _compile(_registry())
        claims = payload["report"]["claims"]
        assert set(claims) == {"artifact", "uniform", "effect", "tracking", "unclaimed"}
        assert claims["effect"] == EFFECT_EVIDENCE_NOTICE
        assert claims["tracking"] == TRACKING_UNOBSERVABLE_NOTICE
        assert claims["unclaimed"] == UNCLAIMED_ENUMERATION_NOTE

    def test_the_effect_notice_is_present_on_the_success_path(self):
        _execution, payload = _compile(_registry())
        assert payload["succeeded"] is True
        assert payload["report"]["claims"]["effect"] == EFFECT_EVIDENCE_NOTICE
        assert EFFECT_EVIDENCE_NOTICE in payload["summary_ko"]

    def test_the_unclaimed_enumeration_reaches_the_payload(self):
        _execution, payload = _compile(_registry())
        # The look sets the core four, the fx drives Dimmer — so the axes this
        # scene never asserts include the ones uniformity cannot close.
        assert "Pan" in payload["report"]["unclaimed_attributes"]
        assert "Tilt" in payload["report"]["unclaimed_attributes"]

    def test_a_failed_command_is_never_reported_as_success(self):
        port = _RecordingPort(failures=frozenset({"ClearAll"}))
        execution, payload = _compile(_registry(port=port))
        assert payload["succeeded"] is False
        assert execution.result.is_error is True

    def test_the_korean_summary_is_two_tier(self):
        _execution, payload = _compile(_registry())
        assert "상세:" in payload["summary_ko"]


# =============================================================================
# reason codes
# =============================================================================


def test_the_cue_occupied_reason_code_is_the_scene_layers_own():
    # Not asserted through the tool (a fresh sequence has no cues); asserted as
    # the contract the tool re-exports when the compiler refuses.
    assert CUE_OCCUPIED == "cue_occupied"
