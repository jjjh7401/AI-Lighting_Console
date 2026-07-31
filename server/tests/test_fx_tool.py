"""M5 wiring — ``find_fx`` / ``instantiate_fx``, the two tools that make the fx
layer reachable from a model turn.

M1 built the schema, M2 the library, M3 the matcher, M4 the bundle builder,
the collision guards and the Korean report. Every one of them passed its own
tests and the chain was still unreachable: nothing in ``TOOL_NAMES`` opened
``match_fx`` or ``build_fx_bundle``, so a model asked for "좌우로 쓸어줘" could
only hand-write a phaser with ``run_commands`` — the one path where the step
grammar M0 measured is not enforced by anything.

These tests enter where a model enters — ``registry.dispatch`` — so a tool that
is not registered fails them all.

Four properties this file exists to hold, beyond "it works":

* The instantiation path reaches the console through ``run_commands`` and
  nothing else (REQ-FXLIB-016/017). Asserted three ways: the gate sees the whole
  bundle as ONE screening, a gate that does not clear yields zero sends, and a
  structural scan of both handlers shows neither ever names the execution port.
* The target group came from the rig. An unlisted group is refused before a
  single command is sent, because ``Group 7`` on a rig without group 7 selects
  nothing and the following ``Store`` then writes an EMPTY cue — silently, since
  a stored phaser is indistinguishable from an empty one (M0).
* A cross-call fold is an explicit failure, never a quiet partial success
  (REQ-FXLIB-011 (b)). The bundle's shared lines are not in the dedupe exemption
  set, so the second instantiation of one instruction turn folds — and the
  ``Store`` still runs.
* Every report carries the effect-evidence limit, on the SUCCESS path too
  (REQ-FXLIB-014 (c)). Nothing downstream re-checks it.

Console contact: zero. Everything below is in-memory.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from server.fx.instantiate import (
    SEQUENCE_OCCUPIED,
    SEQUENCE_TRUNCATED,
    FxInstantiation,
)
from server.fx.matching import EMPTY_QUERY, LOW_CONFIDENCE, NO_MATCH
from server.fx.report import (
    CROSS_CALL_COLLISION,
    EFFECT_EVIDENCE_NOTICE,
    PLANNED,
    REQUERY_LIMIT_NOTICE,
)
from server.fx.schema import Fx, FxLibrary, FxStep, StepValue
from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    TOOL_NAMES,
    ExecutionContext,
    build_toolset,
)

FIND = "find_fx"
INSTANTIATE = "instantiate_fx"
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
    """Answers the two fx sections (groups, sequences) and nothing else."""

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
                    status="ok" if self.cleared else "blocked",
                    reasons=() if self.cleared else ("live lock",),
                )
                for c in commands
            ),
            notice=self.notice,
        )


# -- rig assembly -------------------------------------------------------------
#
# RAW responder payloads, not pre-shaped sections: the tool must build the
# section shape with the producer's own helpers, so a fixture handing it a
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


DEFAULT_GROUPS = ((11, "Back"), (12, "Front"))
DEFAULT_SEQUENCES = ((1, "Opening"), (2, "Ballad"))


def _tree(
    *,
    groups: tuple[tuple[int | None, str], ...] = DEFAULT_GROUPS,
    sequences: tuple[tuple[int | None, str], ...] = DEFAULT_SEQUENCES,
    groups_truncated: bool = False,
    sequences_truncated: bool = False,
    drop: tuple[str, ...] = (),
) -> dict[str, dict]:
    tree = {
        GROUPS_PATH: _payload(
            GROUPS_PATH,
            [_child(n, name) for n, name in groups],
            truncated=groups_truncated,
        ),
        SEQUENCES_PATH: _payload(
            SEQUENCES_PATH,
            [_child(n, name) for n, name in sequences],
            truncated=sequences_truncated,
        ),
    }
    for path in drop:
        tree.pop(path, None)
    return tree


# -- fx -----------------------------------------------------------------------


def _fx(
    *,
    fx_id: str = "test-fx",
    display_name: str = "테스트 이펙트",
    pattern: str = "pulse",
    attribute: str = "Dimmer",
    values: tuple[float, float] = (100.0, 0.0),
    aliases: tuple[str, ...] = ("펄스",),
    mood_keywords: tuple[str, ...] = ("심장박동",),
    phase_from: float | None = 0.0,
    phase_to: float | None = 360.0,
    speed: float | None = 60.0,
) -> Fx:
    return Fx(
        fx_id=fx_id,
        display_name=display_name,
        pattern=pattern,
        steps=tuple(FxStep(values=(StepValue(attribute=attribute, value=v),)) for v in values),
        aliases=aliases,
        mood_keywords=mood_keywords,
        phase_from=phase_from,
        phase_to=phase_to,
        speed=speed,
    )


SECOND_FX = _fx(
    fx_id="other-fx",
    display_name="다른 이펙트",
    pattern="sweep",
    attribute="Pan",
    values=(-30.0, 30.0),
    aliases=("스윕",),
    mood_keywords=("좌우",),
)


def _library(*fx: Fx) -> FxLibrary:
    return FxLibrary(schema_version=1, fx=fx or (_fx(),))


# -- dispatch -----------------------------------------------------------------


def _registry(*, library=None, tree=None, port=None, state=None, gate=None):
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=state or _RigStatePort(tree if tree is not None else _tree()),
        bundle_gate=gate,
        fx_library=library if library is not None else _library(),
    )


def _dispatch(registry, tool: str, arguments: dict, context=None):
    call = ToolCall(id="c1", name=tool, arguments=arguments)
    execution = registry.dispatch(call, context)
    return execution, json.loads(execution.result.content)


def _find(registry, query: str = "펄스"):
    return _dispatch(registry, FIND, {"query": query})


def _instantiate(registry, arguments: dict | None = None, context=None):
    return _dispatch(
        registry,
        INSTANTIATE,
        {"fx_id": "test-fx", "group": 11} if arguments is None else arguments,
        context,
    )


def _definition(registry, tool: str):
    return next(d for d in registry.definitions() if d.name == tool)


def _executed_ok(execution) -> frozenset[str]:
    """The instruction-turn dedupe state a runner would carry forward (runner.py)."""
    return frozenset(o.command for o in execution.command_outcomes if o.status == "executed_ok")


# =============================================================================
# registration
# =============================================================================


class TestToolRegistration:
    def test_both_tools_are_in_the_closed_tool_set(self):
        assert FIND in TOOL_NAMES
        assert INSTANTIATE in TOOL_NAMES

    def test_both_tools_are_offered_to_the_model(self):
        names = [d.name for d in _registry().definitions()]
        assert FIND in names
        assert INSTANTIATE in names

    def test_find_fx_takes_the_operators_own_words(self):
        definition = _definition(_registry(), FIND)
        assert definition.parameters["required"] == ["query"]
        assert definition.parameters["properties"]["query"]["type"] == "string"

    def test_instantiate_fx_takes_the_id_and_the_group_and_nothing_else_required(self):
        # The id is the only stable machine key in a find_fx match — display
        # names are Korean, editable in the assets and may repeat. The group is
        # the one rig number the model supplies; everything else is measured.
        definition = _definition(_registry(), INSTANTIATE)
        assert definition.parameters["required"] == ["fx_id", "group"]
        properties = definition.parameters["properties"]
        assert set(properties) == {"fx_id", "group", "sequence", "executor", "label"}
        assert properties["group"]["type"] == "integer"

    def test_neither_tool_accepts_undeclared_arguments(self):
        for tool in (FIND, INSTANTIATE):
            assert _definition(_registry(), tool).parameters["additionalProperties"] is False


# =============================================================================
# find_fx — the description IS the discoverability surface (decision G)
# =============================================================================


class TestFindFxDescriptionCarriesTheFallbackContract:
    """The rulebook is PRESERVE (REQ-FXLIB-020), so this description is alone.

    The rulebook's mood table names its own trigger — "used when ``find_looks``
    answered with a fallback signal" — and that sentence cannot be edited to add
    ``find_fx`` (byte-diff 0). So the bridge from an fx fallback to the mood
    table exists ONLY here. A test on the rulebook would be testing the wrong
    file; this one tests the only file that can carry the rule.
    """

    @staticmethod
    def _description() -> str:
        return _definition(_registry(), FIND).description

    def test_the_three_fallback_reasons_are_named(self):
        description = self._description()
        for reason in (NO_MATCH, LOW_CONFIDENCE, EMPTY_QUERY):
            assert reason in description

    def test_a_fallback_forbids_picking_from_the_list(self):
        # Scoped to the whole clause, not the memorable fragment: a bare "do NOT
        # pick" would pass on any other prohibition in the same text.
        assert "do NOT pick from the list" in self._description()

    def test_a_fallback_routes_to_the_rulebook_mood_table(self):
        # The measured gap this sentence closes: a pattern-word-only query
        # ('원형으로 돌려줘') ties across that pattern's entries and answers
        # low_confidence, and the rulebook's own fallback sentence names
        # find_looks, not find_fx.
        assert "rulebook's mood table" in self._description()

    def test_the_two_fallback_rules_do_not_stand_in_for_each_other(self):
        # Neighbour independence: neither sentence contains the other, so a
        # mutation deleting one cannot be masked by the other's presence.
        description = self._description()
        assert "do NOT pick from the list" not in "rulebook's mood table"
        assert "rulebook's mood table" not in "do NOT pick from the list"
        assert description.count("do NOT pick from the list") == 1

    def test_a_tie_can_be_narrowed_by_re_asking(self):
        # A low-confidence band is two entries of one pattern (a slow one and a
        # fast one); one more word from the operator resolves it. Without this
        # the model's only documented move is to abandon the library.
        assert "ask again with one more word" in self._description()

    def test_the_description_says_it_sends_nothing(self):
        assert "never sends anything to the console" in self._description()


class TestFindFxAnswers:
    def test_a_match_comes_back_as_the_matcher_saw_it(self):
        _execution, payload = _find(_registry(), "펄스")
        assert payload["selected"] == "test-fx"
        assert payload["fallback"] is False
        assert payload["matches"][0]["fx_id"] == "test-fx"

    def test_a_miss_is_an_answer_not_a_tool_failure(self):
        # An is_error payload feeds the self-correction loop and would invite a
        # retry that can only miss again.
        execution, payload = _find(_registry(), "아무말대잔치zzz")
        assert execution.result.is_error is False
        assert payload["fallback"] is True
        assert payload["fallback_reason"] == NO_MATCH

    def test_a_pattern_word_alone_ties_and_falls_back(self):
        # The finding this milestone was asked to verify: two entries share one
        # pattern, the pattern word narrows to the band and nothing narrows
        # within it. Reported honestly rather than resolved by picking first.
        library = _library(
            _fx(fx_id="slow-one", aliases=(), mood_keywords=("느린",)),
            _fx(fx_id="fast-one", aliases=(), mood_keywords=("빠른",)),
        )
        _execution, payload = _find(_registry(library=library), "펄스로 해줘")
        assert payload["selected"] is None
        assert payload["fallback_reason"] == LOW_CONFIDENCE
        assert {m["fx_id"] for m in payload["matches"]} == {"slow-one", "fast-one"}

    def test_the_tie_is_narrowed_by_one_more_word(self):
        # Non-vacuity for the "ask again" instruction above: re-asking WORKS.
        library = _library(
            _fx(fx_id="slow-one", aliases=(), mood_keywords=("느린",)),
            _fx(fx_id="fast-one", aliases=(), mood_keywords=("빠른",)),
        )
        _execution, payload = _find(_registry(library=library), "빠른 펄스로 해줘")
        assert payload["selected"] == "fast-one"
        assert payload["fallback"] is False

    def test_an_empty_query_is_its_own_reason(self):
        _execution, payload = _find(_registry(), "   ")
        assert payload["fallback_reason"] == EMPTY_QUERY

    def test_a_non_string_query_is_a_structured_error(self):
        execution, payload = _dispatch(_registry(), FIND, {"query": 7})
        assert execution.result.is_error is True
        assert "query" in payload["error"]

    def test_lookup_sends_nothing_to_the_console(self):
        port = _RecordingPort()
        _find(_registry(port=port))
        assert port.executed == []

    def test_a_broken_library_is_a_failure_not_an_empty_result(self, tmp_path, monkeypatch):
        # A silent empty result would read as "no fx matches", which is a claim
        # about the library rather than about the query.
        import server.orchestrator.tools as tools

        broken = tmp_path / "library"
        broken.mkdir()
        (broken / "bad.yaml").write_text("schema_version: 1\nfx: [{fx_id: x}]\n", encoding="utf-8")
        monkeypatch.setattr(tools, "FX_LIBRARY_DIR", broken)
        registry = build_toolset(
            execution_port=_RecordingPort(),
            state_port=_RigStatePort(_tree()),
        )
        execution, payload = _find(registry)
        assert execution.result.is_error is True
        assert "fx library unavailable" in payload["error"]


# =============================================================================
# instantiate_fx — the description pins what the model must not conclude
# =============================================================================


class TestInstantiateFxDescriptionCarriesTheLimits:
    @staticmethod
    def _description() -> str:
        return _definition(_registry(), INSTANTIATE).description

    def test_the_effect_is_declared_not_machine_verifiable(self):
        # REQ-FXLIB-014 (c), unconditional. The console accepts every line with
        # ok:true and no read-back distinguishes a phaser cue from an empty one,
        # so this sentence is the ONLY thing standing between the model and
        # reporting a receipt as an effect.
        description = self._description()
        assert "the effect itself cannot be verified by machine" in description
        assert "a human has to watch the stage" in description

    def test_partial_success_may_not_be_reported_as_full_success(self):
        assert "never report a partial run as a whole one" in self._description()

    def test_the_cross_call_boundary_is_stated(self):
        # One instantiation per instruction turn is an operating boundary, not
        # a style note: the second one folds from its FIRST line.
        assert "ONE instantiate_fx per instruction" in self._description()

    def test_the_group_is_the_only_rig_number_passed_in(self):
        description = self._description()
        assert "the group is the ONLY rig number you pass" in description
        assert "get_rig_context" in description

    def test_fixture_slots_are_refused_by_name(self):
        # 슬롯 ≠ FID. A fixture slot handed in as a group is the invention this
        # sentence exists to pre-empt.
        assert "never a fixture slot" in self._description()

    def test_the_description_points_back_at_find_fx_for_the_id(self):
        assert "find_fx" in self._description()

    def test_the_limits_do_not_stand_in_for_each_other(self):
        # Neighbour independence for the two rules most likely to be collapsed
        # into one sentence by a future edit.
        description = self._description()
        assert description.count("never report a partial run as a whole one") == 1
        assert description.count("the effect itself cannot be verified by machine") == 1
        assert "never report a partial run" not in "the effect itself cannot be verified by machine"


# =============================================================================
# the bound path
# =============================================================================


class TestABoundFxReachesTheConsole:
    def test_the_bundle_runs_in_the_measured_shape(self):
        port = _RecordingPort()
        execution, payload = _instantiate(_registry(port=port))
        assert execution.result.is_error is False
        assert payload["succeeded"] is True
        assert port.executed[0] == "ChangeDestination Root"
        assert port.executed[1] == "ClearAll"
        assert port.executed[2] == "Group 11"
        assert "Step 2" in port.executed
        assert port.executed[-1] == "ClearAll"

    def test_the_store_names_the_measured_free_sequence(self):
        port = _RecordingPort()
        # 1 and 2 are occupied on this rig, so 3 is the first free number. A
        # hardcoded number fails here rather than passing on a rig that agrees.
        _instantiate(_registry(port=port))
        assert any(c.startswith("Store Sequence 3 Cue 1 ") for c in port.executed)

    def test_a_different_rig_moves_the_sequence_number(self):
        port = _RecordingPort()
        tree = _tree(sequences=((1, "a"), (2, "b"), (3, "c"), (4, "d")))
        _instantiate(_registry(port=port, tree=tree))
        assert any(c.startswith("Store Sequence 5 Cue 1 ") for c in port.executed)

    def test_the_report_rides_back_with_the_result(self):
        _execution, payload = _instantiate(_registry())
        report = payload["report"]
        assert report["fx_id"] == "test-fx"
        assert report["group"] == 11
        assert report["step_count"] == 2
        assert report["speed_bpm"] == 60.0

    def test_the_korean_summary_rides_back_too(self):
        _execution, payload = _instantiate(_registry())
        assert "시퀀스 3 큐 1" in payload["summary_ko"]


class TestTheEffectLimitIsOnTheSuccessPathToo:
    """REQ-FXLIB-014 (c) — unconditional, so the SUCCESS path is where it counts."""

    def test_the_structured_report_carries_the_effect_limit(self):
        _execution, payload = _instantiate(_registry())
        assert payload["succeeded"] is True, "non-vacuity: this must be the success path"
        assert payload["report"]["effect_evidence"] == EFFECT_EVIDENCE_NOTICE

    def test_the_korean_summary_carries_the_effect_limit(self):
        _execution, payload = _instantiate(_registry())
        assert EFFECT_EVIDENCE_NOTICE in payload["summary_ko"]

    def test_the_requery_limit_rides_along_separately(self):
        # "The sequence exists" is re-queryable; that is NOT evidence of effect,
        # and the two notices say different things.
        _execution, payload = _instantiate(_registry())
        assert REQUERY_LIMIT_NOTICE in payload["summary_ko"]
        assert EFFECT_EVIDENCE_NOTICE != REQUERY_LIMIT_NOTICE


# =============================================================================
# the target group came from the rig (REQ-FXLIB-016)
# =============================================================================


class TestTheTargetGroupMustBeOnThisRig:
    def test_a_group_this_rig_does_not_list_is_refused(self):
        execution, payload = _instantiate(_registry(), {"fx_id": "test-fx", "group": 3})
        assert execution.result.is_error is True
        assert "group 3" in payload["error"]

    def test_a_refused_group_sends_nothing(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port), {"fx_id": "test-fx", "group": 3})
        assert port.executed == []

    def test_the_refusal_names_the_groups_that_do_exist(self):
        # Otherwise the model's only move is another guess.
        _execution, payload = _instantiate(_registry(), {"fx_id": "test-fx", "group": 3})
        assert payload["groups"] == [11, 12]

    def test_a_group_the_responder_could_not_number_is_not_addressable(self):
        # A name-only entry means "this exists and I could not number it"; using
        # its position as a number is the hallucinated-Group-3 defect.
        tree = _tree(groups=((None, "Back"), (12, "Front")))
        execution, payload = _instantiate(_registry(tree=tree), {"fx_id": "test-fx", "group": 11})
        assert execution.result.is_error is True
        assert payload["groups"] == [12]

    def test_a_truncated_group_listing_says_so_in_the_refusal(self):
        # Absence from a cut list is not evidence of absence — but it is also
        # not licence to address it. Refuse, and say which it was.
        tree = _tree(groups=((11, "Back"),), groups_truncated=True)
        execution, payload = _instantiate(_registry(tree=tree), {"fx_id": "test-fx", "group": 12})
        assert execution.result.is_error is True
        assert payload["groups_truncated"] is True

    def test_a_listed_group_is_addressed_by_number(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port), {"fx_id": "test-fx", "group": 12})
        assert "Group 12" in port.executed

    def test_no_command_ever_targets_a_fixture_slot(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port))
        assert [c for c in port.executed if c.startswith("Fixture")] == []

    def test_a_group_that_is_not_an_integer_is_refused(self):
        execution, payload = _instantiate(
            _registry(), {"fx_id": "test-fx", "group": "백라이트"}
        )
        assert execution.result.is_error is True
        assert "get_rig_context" in payload["error"]

    def test_a_boolean_is_not_a_group_number(self):
        # bool IS an int in Python and True == 1, so on a rig that HAS a group 1
        # the rig check cannot catch it — the type guard has to. Measured: with
        # the default rig (no group 1) this test passed even with the bool guard
        # removed, on the strength of the rig refusal.
        tree = _tree(groups=((1, "Odd"), (11, "Back")))
        execution, payload = _instantiate(_registry(tree=tree), {"fx_id": "test-fx", "group": True})
        assert execution.result.is_error is True
        # The rig-listing refusal carries "groups"; the type refusal does not.
        assert "groups" not in payload
        assert "get_rig_context" in payload["error"]

    def test_the_rig_is_read_on_every_call(self):
        state = _RigStatePort(_tree())
        _instantiate(_registry(state=state))
        assert GROUPS_PATH in state.queried
        assert SEQUENCES_PATH in state.queried

    def test_a_rig_section_that_never_arrived_is_not_an_empty_rig(self):
        state = _RigStatePort(_tree(drop=(GROUPS_PATH,)))
        execution, payload = _instantiate(_registry(state=state))
        assert execution.result.is_error is True
        assert "groups" in payload["rig_unavailable"]


# =============================================================================
# the fx id
# =============================================================================


class TestTheFxId:
    def test_an_unknown_id_is_a_structured_error(self):
        # Unlike a find_fx miss, a retry with the right id succeeds — so this
        # one IS an error result.
        execution, payload = _instantiate(_registry(), {"fx_id": "nope", "group": 11})
        assert execution.result.is_error is True
        assert "find_fx" in payload["error"]

    def test_an_empty_id_is_refused_as_an_argument_not_as_a_lookup_miss(self):
        # Without the argument guard an empty id reaches by_id and comes back as
        # "unknown fx_id" — a true statement about the wrong thing, and a bare
        # is_error assertion cannot tell the two apart.
        execution, payload = _instantiate(_registry(), {"fx_id": "  ", "group": 11})
        assert execution.result.is_error is True
        assert "unknown" not in payload["error"]


# =============================================================================
# store safety carried through the tool (REQ-FXLIB-012)
# =============================================================================


class TestStoreSafetyReachesTheTool:
    def test_a_truncated_sequence_pool_refuses_automatic_assignment(self):
        tree = _tree(sequences_truncated=True)
        port = _RecordingPort()
        execution, payload = _instantiate(_registry(port=port, tree=tree))
        assert execution.result.is_error is True
        assert payload["reason"] == SEQUENCE_TRUNCATED
        assert port.executed == []

    def test_an_occupied_requested_sequence_is_refused(self):
        execution, payload = _instantiate(
            _registry(), {"fx_id": "test-fx", "group": 11, "sequence": 1}
        )
        assert execution.result.is_error is True
        assert payload["reason"] == SEQUENCE_OCCUPIED

    def test_a_free_requested_sequence_is_honoured(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port), {"fx_id": "test-fx", "group": 11, "sequence": 9})
        assert any(c.startswith("Store Sequence 9 Cue 1 ") for c in port.executed)

    def test_nothing_ever_overwrites(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port))
        assert [c for c in port.executed if "/overwrite" in c.lower()] == []


class TestExecutorIsNeverAutomatic:
    def test_an_unspecified_executor_produces_no_assign(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port))
        assert [c for c in port.executed if c.startswith("Assign")] == []

    def test_an_explicit_executor_produces_exactly_one_assign(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port), {"fx_id": "test-fx", "group": 11, "executor": 205})
        assigns = [c for c in port.executed if c.startswith("Assign")]
        assert assigns == ["Assign Sequence 3 At Executor 205"]

    def test_an_explicit_label_reaches_the_store(self):
        port = _RecordingPort()
        _instantiate(_registry(port=port), {"fx_id": "test-fx", "group": 11, "label": "Chorus FX"})
        assert "Store Sequence 3 Cue 1 'Chorus FX'" in port.executed


# =============================================================================
# one execution surface (REQ-FXLIB-016 / 017)
# =============================================================================


class TestInstantiationReachesTheConsoleOnlyThroughRunCommands:
    def test_the_whole_bundle_is_screened_as_one_bundle(self):
        gate = _RecordingGate()
        port = _RecordingPort()
        _instantiate(_registry(port=port, gate=gate))
        assert len(gate.screened) == 1
        assert gate.screened[0] == port.executed

    def test_a_gate_that_does_not_clear_yields_zero_console_sends(self):
        gate = _RecordingGate(cleared=False, status="locked")
        port = _RecordingPort()
        execution, payload = _instantiate(_registry(port=port, gate=gate))
        assert gate.screened, "non-vacuity: the gate must have been consulted"
        assert port.executed == []
        assert payload["gate_status"] == "locked"
        # A LiveLock demotion is an answer, not a failure — see the sibling
        # tools' rationale (REQ-BUSKWIZ-014). The proposal is the deliverable.
        assert execution.result.is_error is False

    def test_a_hold_is_still_an_error_unlike_a_lock(self):
        # The lock carve-out must be scoped to the lock. Any OTHER refusal is
        # still something the model has to act on, so it stays an error —
        # without this, the carve-out would swallow every gate refusal.
        gate = _RecordingGate(cleared=False, status="held")
        port = _RecordingPort()
        execution, payload = _instantiate(_registry(port=port, gate=gate))
        assert port.executed == []
        assert payload["gate_status"] == "held"
        assert execution.result.is_error is True

    def test_a_refused_bundle_is_never_reported_as_executed(self):
        # The trap: the gate's per-command decisions are not execution
        # outcomes, and counting them as such would verdict a blocked bundle
        # "전량 실행".
        gate = _RecordingGate(cleared=False, status="locked")
        _execution, payload = _instantiate(_registry(gate=gate))
        assert payload["succeeded"] is False
        assert payload["report"]["verdict"] == PLANNED
        assert payload["report"]["executed"] is False

    def test_a_refused_bundle_still_comes_back_with_its_report(self):
        gate = _RecordingGate(cleared=False, status="locked")
        _execution, payload = _instantiate(_registry(gate=gate))
        assert payload["report"]["fx_id"] == "test-fx"
        assert EFFECT_EVIDENCE_NOTICE in payload["summary_ko"]

    def test_a_console_failure_stops_the_bundle_and_is_reported(self):
        port = _RecordingPort(failures=frozenset({"Step 2"}))
        execution, payload = _instantiate(_registry(port=port))
        assert execution.result.is_error is True
        assert payload["succeeded"] is False
        assert payload["report"]["failed"] == ["Step 2"]
        assert payload["report"]["not_executed"], "stop-on-first-failure must propagate"


class TestTheHandlersNameNoExecutionSurface:
    """The structural half of the claim above (the M4/M5 AST-scan discipline).

    A behavioural test proves the gate saw THIS bundle; it cannot prove a future
    edit will not add a second route. This one reads each handler's own body:
    ``instantiate_fx`` may name ``run_commands`` and must never name the
    execution port; ``find_fx`` must name neither.
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

    def test_the_instantiate_handler_calls_the_run_commands_tool(self):
        assert "run_commands" in self._identifiers(INSTANTIATE)

    @pytest.mark.parametrize("handler", [FIND, INSTANTIATE])
    def test_no_fx_handler_names_the_execution_port(self, handler):
        identifiers = self._identifiers(handler)
        assert "execution_port" not in identifiers
        assert "execute" not in identifiers

    def test_the_lookup_handler_reaches_no_execution_path_at_all(self):
        assert "run_commands" not in self._identifiers(FIND)

    def test_the_scan_is_not_vacuous(self):
        # The same scan over the handler that DOES execute must see both.
        identifiers = self._identifiers("run_commands")
        assert "execution_port" in identifiers
        assert "execute" in identifiers

    def test_the_handler_body_is_substantial(self):
        # A scan over an empty or wrongly-located function passes for the wrong
        # reason; the handler has a real body.
        assert len(self._identifiers(INSTANTIATE)) > 15


# =============================================================================
# the instruction-turn boundary (REQ-FXLIB-011 (b))
# =============================================================================


class TestACrossCallFoldIsAnExplicitFailure:
    """The second instantiation of one instruction turn is NOT a success.

    ``executed_ok`` accumulates across tool calls (``runner.py``), and the lines
    every fx bundle shares — ``ChangeDestination Root`` first, then ``Step 2`` —
    are not in the dedupe exemption set. So they fold, while the ``Store`` (whose
    sequence number differs) runs: an INCOMPLETE cue is created and every command
    still comes back ok.
    """

    @staticmethod
    def _second_call(second_fx_id: str, group: int):
        registry = _registry(library=_library(_fx(), SECOND_FX))
        first, _payload = _instantiate(
            registry, {"fx_id": "test-fx", "group": 11, "sequence": 5}
        )
        context = ExecutionContext(executed_ok=_executed_ok(first))
        return _instantiate(
            registry,
            {"fx_id": second_fx_id, "group": group, "sequence": 6},
            context,
        )

    def test_a_second_instantiation_of_the_same_pattern_fails_explicitly(self):
        execution, payload = self._second_call("test-fx", 12)
        assert execution.result.is_error is True
        assert payload["succeeded"] is False
        assert payload["report"]["verdict"] == CROSS_CALL_COLLISION

    def test_a_second_instantiation_of_a_DIFFERENT_pattern_fails_too(self):
        # The lines are shared by every bundle, so pattern independence buys
        # nothing here.
        execution, payload = self._second_call("other-fx", 12)
        assert execution.result.is_error is True
        assert payload["report"]["verdict"] == CROSS_CALL_COLLISION

    def test_the_fold_starts_at_the_destination_line_not_at_step_two(self):
        # design.md §5 named `Step 2` as the shared line. Measured: the FIRST
        # line of every bundle is `ChangeDestination Root`, which is also
        # outside the exempt three — so the fold begins one line earlier.
        _execution, payload = self._second_call("other-fx", 12)
        assert payload["report"]["collided"][0] == "ChangeDestination Root"

    def test_the_exempt_lines_are_not_counted_as_collisions(self):
        # `ClearAll` and the bare group selection repeat legitimately; counting
        # them would make every second call fail for the wrong reason.
        _execution, payload = self._second_call("other-fx", 12)
        assert "ClearAll" not in payload["report"]["collided"]
        assert "Group 12" not in payload["report"]["collided"]

    def test_the_store_still_ran_and_the_report_says_so(self):
        # The whole hazard: an incomplete cue now exists on the console.
        _execution, payload = self._second_call("other-fx", 12)
        assert "불완전한 시퀀스·큐가 이미 생성됐을 수 있습니다" in payload["summary_ko"]

    def test_every_command_came_back_ok_and_it_is_still_not_a_success(self):
        # Non-vacuity for the whole class: run_commands itself is content.
        execution, payload = self._second_call("other-fx", 12)
        assert payload["all_ok"] is True
        assert execution.result.is_error is True

    def test_one_instantiation_per_turn_still_succeeds(self):
        # Non-vacuity in the other direction: the guard does not fire on the
        # first call of a turn.
        registry = _registry(library=_library(_fx(), SECOND_FX))
        execution, payload = _instantiate(registry, {"fx_id": "test-fx", "group": 11})
        assert execution.result.is_error is False
        assert payload["report"]["collided"] == []


# =============================================================================
# an empty bundle is an answer
# =============================================================================


class TestAnEmptyBundleIsAnAnswerNotAFailure:
    """Defensive branch — deliberately doubled at the seam the handler consumes.

    ``build_fx_bundle`` always emits a destination, a clear, a selection and a
    store, so this branch is unreachable through the real builder today. It is
    kept because the alternative — reporting an empty bundle as executed — is
    exactly the silent success this SPEC exists to prevent, and a branch nobody
    can exercise is a claim nobody can check. Hence the double.
    """

    def test_an_empty_bundle_executes_nothing_and_is_not_an_error(self, monkeypatch):
        import server.orchestrator.tools as tools

        def _empty(fx, **kwargs):
            return FxInstantiation(
                fx_id=fx.fx_id,
                display_name=fx.display_name,
                pattern=fx.pattern,
                group=kwargs["group"],
                sequence=3,
                label="x",
                commands=(),
            )

        monkeypatch.setattr(tools, "bind_fx", _empty)
        port = _RecordingPort()
        gate = _RecordingGate()
        execution, payload = _instantiate(_registry(port=port, gate=gate))
        assert execution.result.is_error is False
        assert payload["executed"] is False
        assert port.executed == []
        assert gate.screened == []
        assert payload["report"]["fx_id"] == "test-fx"


# =============================================================================
# provider neutrality (AC-FXLIB-019)
# =============================================================================


class TestProviderNeutrality:
    """Neither the fx package nor the two handlers know which LLM is talking."""

    ADAPTERS = ("anthropic", "gemini", "factory", "AnthropicAdapter", "GeminiAdapter")

    def test_the_fx_package_imports_no_provider_adapter(self):
        import server.fx

        offenders = []
        for path in sorted(Path(server.fx.__file__).parent.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                elif isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                else:
                    continue
                offenders += [
                    f"{path.name}: {m}"
                    for m in modules
                    if any(adapter in m for adapter in self.ADAPTERS)
                ]
        assert offenders == []

    def test_the_scan_covers_a_real_file_set(self):
        import server.fx

        names = {p.name for p in Path(server.fx.__file__).parent.glob("*.py")}
        assert {"matching.py", "instantiate.py", "report.py"} <= names

    @pytest.mark.parametrize("handler", [FIND, INSTANTIATE])
    def test_no_handler_names_a_provider(self, handler):
        identifiers = TestTheHandlersNameNoExecutionSurface._identifiers(handler)
        assert not {i for i in identifiers if any(a in i for a in self.ADAPTERS)}

    def test_both_tools_work_with_no_adapter_wired_at_all(self):
        # The registry in every test above is built from two ports and a
        # library; no provider is constructible from it.
        registry = _registry()
        find, find_payload = _find(registry)
        instantiate, instantiate_payload = _instantiate(registry)
        assert find.result.is_error is False
        assert find_payload["selected"] == "test-fx"
        assert instantiate.result.is_error is False
        assert instantiate_payload["succeeded"] is True
