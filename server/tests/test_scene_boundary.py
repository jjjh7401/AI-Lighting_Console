"""M7 — the scene layer's boundary as machine checks (AC-SCENE-017, AC-SCENE-020).

M1~M6 each proved its own slice. What no slice could prove is that the slices
together stay INSIDE the boundary the SPEC drew: the scene layer computes, the
gate executes, and neither the safety layer nor the rulebook learns that scenes
exist. Every claim below is about the whole tree, not about a function.

* **AC-SCENE-017 ②** — no scene module reaches the execution path. An AST
  identifier scan, never a raw grep: ``server/scene/__init__.py`` documents the
  very chokepoint it is forbidden to call, so a text scan would hit the
  docstring that STATES the invariant. That is the correction
  ``test_looks_boundary.py`` made and ``test_fx_boundary.py`` inherited.
* **AC-SCENE-017 ③** — ``_NAMED_TOOL_EXEMPTIONS`` diff 0. An entry there would
  license an OSC import from this package; a widened list is the same hole
  whether or not the new entry says "scene".
* **AC-SCENE-020** — LiveLock demotion through the REAL gate. A fake gate that
  hands back the string ``"locked"`` only proves we can read a string we wrote.
  M6 wired ``compile_scene`` to ``run_commands`` and reasoned the lock therefore
  applies for free — nobody had fired a locked scene bundle through it. fx made
  exactly that inference in its M5 and only measured it in M6
  (``test_fx_boundary.py`` TestFxInstantiationUnderLiveLock); this file does not
  repeat the omission.
* **decision D's price, paid** — the scene layer imports four PRIVATE upstream
  builders. The trade was accepted on the argument that re-implementing them
  would let two copies drift silently (design.md §2.2). The counter-obligation
  is here: the output shape of ``_values_line`` and ``_step_lines`` is pinned
  against known inputs, so an upstream change breaks LOUDLY instead of moving
  the stage.
* **decisions E/K's price, paid** — ``SCENE_UNIFORM_ATTRIBUTES`` is a second
  NAME for the upstream measured band, and ``KNOWN_ATTRIBUTES`` is the universe
  the unclaimed enumeration subtracts from. Both couplings are asserted, so an
  upstream edit fails here before it quietly widens what a report claims.

Console contact: zero. Everything below is in-memory or static source reading.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from server.fx.instantiate import _step_lines
from server.fx.schema import Fx, FxStep, StepValue
from server.llm.types import ToolCall
from server.looks.instantiate import _values_line
from server.looks.schema import CONFIRMED_ATTRIBUTES, KNOWN_ATTRIBUTES, AttributeValue
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock
from server.scene.compile import SCENE_UNIFORM_ATTRIBUTES
from server.scene.loader import DEFAULT_LIBRARY_DIR as SCENE_LIBRARY_DIR
from server.scene.loader import load_library_from_dir as load_scene_library

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "server"
SCENE_DIR = SERVER_DIR / "scene"
RULEBOOK_ASSETS = SERVER_DIR / "rulebook" / "assets" / "v2.4.2"


# =============================================================================
# AC-SCENE-017 ② — the execution path is not reached from server/scene/**
# =============================================================================

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "SafetyGate",
        "screen",  # the ONE screening path
        "execution_port",
        "CommandExecutionPort",
        "ExecutionPort",
        "ConsoleLink",
    }
)

FORBIDDEN_MODULE_PREFIXES = (
    "server.safety.gate",
    "server.safety.console",
    "server.orchestrator.ports",
    "server.orchestrator.tools",  # the scene->tools cycle: tools imports scene
    "server.bridge",
    "pythonosc",
)


def _scene_modules() -> list[Path]:
    return sorted(SCENE_DIR.rglob("*.py"))


def _identifiers_of_source(source: str) -> list[str]:
    """Every identifier in an EXECUTABLE position — attribute, name, import.

    A comment is never an AST node; a docstring is an ``ast.Constant``, never an
    ``Attribute``/``Name``/import name. No exclusion logic is needed, and that is
    the whole point of using the AST instead of a grep.
    """
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            found.append(node.attr)
        elif isinstance(node, ast.Name):
            found.append(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.append(node.module)
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
    return found


def _executable_identifiers(path: Path) -> list[str]:
    return _identifiers_of_source(path.read_text(encoding="utf-8"))


def _offenders(path: Path) -> list[str]:
    hits: list[str] = []
    for identifier in _executable_identifiers(path):
        if identifier in FORBIDDEN_IDENTIFIERS:
            hits.append(f"{path.name}: {identifier}")
        if identifier.startswith(FORBIDDEN_MODULE_PREFIXES):
            hits.append(f"{path.name}: imports {identifier}")
    return hits


class TestSceneLayerTouchesNoExecutionPath:
    """AC-SCENE-017 ② — identifier scan, offender count 0."""

    def test_the_scan_reaches_real_code_in_every_scene_module(self):
        # Non-vacuity: a scan that parsed nothing, or that only saw module
        # headers, passes for the wrong reason.
        modules = _scene_modules()
        assert len(modules) >= 6, (
            f"expected the M1~M5 scene modules, saw {[p.name for p in modules]}"
        )
        for path in modules:
            if path.name == "__init__.py":
                continue  # docstring only — its own test below
            count = len(_executable_identifiers(path))
            assert count > 20, f"{path.name} yielded only {count} identifiers"

    def test_the_scan_sees_identifiers_it_should_see(self):
        # A second non-vacuity control keyed to known symbols rather than a
        # count. These are CALLED and IMPORTED names, not definitions: a
        # `def` name is an `ast.FunctionDef`, which this collector deliberately
        # does not walk — it looks at what the code REACHES, not what it offers.
        identifiers = set(_executable_identifiers(SCENE_DIR / "compile.py"))
        assert "select_sequence_number" in identifiers  # the fx call (decision H)
        assert "_values_line" in identifiers  # the private look builder (decision D)
        assert "server.scene.schema" in identifiers

    def test_no_scene_module_names_an_execution_path_symbol(self):
        offenders = [hit for path in _scene_modules() for hit in _offenders(path)]
        assert offenders == []

    def test_the_package_docstring_naming_the_chokepoint_survives_the_scan(self):
        # ``server/scene/__init__.py`` names run_commands -> gate.screen() to
        # STATE the invariant. It is load-bearing documentation, and this scan
        # must not be the reason it disappears.
        init = SCENE_DIR / "__init__.py"
        assert "gate.screen()" in init.read_text(encoding="utf-8")
        assert _offenders(init) == []

    def test_the_scan_catches_an_injected_call(self):
        # Mutation control, in-process: the same collector over source that DOES
        # reach the execution path must report it.
        identifiers = _identifiers_of_source("def go(gate, cmds):\n    return gate.screen(cmds)\n")
        assert any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)

    def test_the_scan_catches_an_injected_bridge_import(self):
        offenders = [
            i
            for i in _identifiers_of_source("from server.bridge.osc import send\n")
            if i.startswith(FORBIDDEN_MODULE_PREFIXES)
        ]
        assert offenders


# =============================================================================
# AC-SCENE-017 ③ — the architecture guard scans scene, it does not exempt it
# =============================================================================


class TestSceneIsScannedByTheArchitectureGuardNotExemptedFromIt:
    @staticmethod
    def _lists():
        from server.tests.test_architecture import _ALLOWED_PREFIXES, _NAMED_TOOL_EXEMPTIONS

        return _ALLOWED_PREFIXES, _NAMED_TOOL_EXEMPTIONS

    def test_scene_is_in_neither_allow_list(self):
        allowed, exemptions = self._lists()
        assert not any("scene" in prefix for prefix in allowed)
        assert not any("scene" in name for name in exemptions)

    def test_the_exemption_list_is_still_the_two_operator_tools(self):
        # If a THIRD exemption is ever legitimately added, this test is the
        # place that must be updated deliberately — that is what "diff 0" means
        # mechanically. It is not a style rule. SPEC-COPILOT-PRESHOW-001 added
        # the third, deliberately, for the same class of reason (a
        # non-production diagnostic reusing the ping/state round-trip pattern).
        _allowed, exemptions = self._lists()
        assert exemptions == frozenset(
            {
                "server/tools/osc_smoke.py",
                "server/tools/responder_roundtrip.py",
                "server/preshow/osc_check.py",
            }
        )

    def test_every_scene_module_actually_survives_the_architecture_filter(self):
        # Non-vacuity: "scene is not exempted" is worthless if the guard's walk
        # never reaches scene. Replicate its skip predicate and assert nothing
        # in this package is skipped.
        allowed, exemptions = self._lists()
        skipped = [
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in _scene_modules()
            if path.relative_to(PROJECT_ROOT).as_posix().startswith(allowed)
            or path.relative_to(PROJECT_ROOT).as_posix() in exemptions
        ]
        assert skipped == []


# =============================================================================
# AC-SCENE-017 — the rulebook never learned about scenes (spec.md §D)
# =============================================================================

SCENE_TOOL_VOCABULARY = ("find_scene", "compile_scene", "scene_id")


def _rulebook_assets() -> list[Path]:
    return sorted(RULEBOOK_ASSETS.rglob("*.md"))


class TestTheRulebookNeverLearnedAboutScenes:
    """byte-diff 0 has a property behind it.

    The whole discoverability burden sits on the tool-schema description
    precisely so the fixed prefix does not change: one changed byte invalidates
    the provider cache prefix. A helpful sentence added to the rulebook is the
    failure this guards, and it is exactly the kind of edit that reads as
    harmless.
    """

    def test_no_rulebook_asset_names_a_scene_tool(self):
        offenders = [
            f"{path.name}: {token}"
            for path in _rulebook_assets()
            for token in SCENE_TOOL_VOCABULARY
            if token in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_the_scan_reads_the_real_asset_text(self):
        # Non-vacuity: the fallback sentence naming `find_looks` IS there.
        text = (RULEBOOK_ASSETS / "31_choreography_patterns.md").read_text(encoding="utf-8")
        assert "the STEP 1 FALLBACK path, used when `find_looks`" in text


# =============================================================================
# decision K — the unclaimed-enumeration universe is pinned
# =============================================================================

TODAYS_UNIVERSE = frozenset(
    {"Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "Zoom", "Iris", "Pan", "Tilt"}
)


class TestTheUpstreamConstantsThisLayerIsCoupledTo:
    def test_the_uniform_set_equals_the_upstream_measured_band(self):
        # Decision K's price. The scene owns a second NAME for this tuple
        # because the two mean different things (upstream: "measured here";
        # scene: "every scene must assert these"). The cost of the second name
        # is this assertion — if the upstream band grows, this fails FIRST and a
        # human decides whether the uniform set follows (design.md §6.1).
        assert SCENE_UNIFORM_ATTRIBUTES == CONFIRMED_ATTRIBUTES

    def test_the_enumeration_universe_is_exactly_todays_eight_attributes(self):
        # The unclaimed enumeration is `KNOWN_ATTRIBUTES - (look ∪ fx)`. If the
        # upstream vocabulary grows, every report silently starts claiming a new
        # axis "may have carried over" — a claim nobody measured. This shape lock
        # makes that growth loud.
        assert KNOWN_ATTRIBUTES == TODAYS_UNIVERSE
        assert len(KNOWN_ATTRIBUTES) == 8

    def test_the_shape_lock_is_what_catches_a_widened_universe(self):
        # Mutation ⑦ made concrete rather than asserted: with one attribute
        # added upstream, the enumeration a report carries widens by exactly
        # that attribute — no other check in the tree notices, which is why the
        # lock above exists.
        asserted = {"Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B"}
        today = tuple(sorted(KNOWN_ATTRIBUTES - asserted))
        widened = tuple(sorted((KNOWN_ATTRIBUTES | {"Frost"}) - asserted))
        assert widened != today
        assert set(widened) - set(today) == {"Frost"}


# =============================================================================
# decision D — the private upstream builders' output shape is pinned
# =============================================================================


class TestUpstreamOutputShapeIsPinned:
    """§2.2's counter-obligation. A drift here must break LOUDLY.

    The scene layer never re-assembles these strings; it asks the upstream
    builder for them, because the dedupe compares exactly those bytes. The risk
    the trade accepted is that upstream changes the bytes. These tests are where
    that shows up as a red test instead of as a stage that does the wrong thing.
    """

    def test_the_look_value_line_shape_is_a_semicolon_chain_of_absolute_values(self):
        line = _values_line(
            (
                AttributeValue(name="Dimmer", value=80),
                AttributeValue(name="ColorRGB_R", value=10),
            )
        )
        assert line == "Attribute 'Dimmer' At 80 ; Attribute 'ColorRGB_R' At 10"

    def test_the_value_line_takes_its_order_from_the_argument(self):
        # The uniform-set enforcement is an ARGUMENT ORDER choice (design.md
        # §6.1). If the builder ever sorted internally, that enforcement would
        # become a no-op — silently, since today's assets are already ordered.
        reversed_line = _values_line(
            (
                AttributeValue(name="ColorRGB_R", value=10),
                AttributeValue(name="Dimmer", value=80),
            )
        )
        assert reversed_line.startswith("Attribute 'ColorRGB_R' At 10")

    def test_the_step_column_shape_omits_step_one_and_never_chains(self):
        fx = Fx(
            fx_id="pin",
            display_name="핀",
            pattern="pulse",
            steps=(
                FxStep(values=(StepValue(attribute="Dimmer", value=100.0),)),
                FxStep(values=(StepValue(attribute="Dimmer", value=0.0),)),
            ),
        )
        assert list(_step_lines(fx)) == [
            "Attribute 'Dimmer' At 100",
            "Step 2",
            "Attribute 'Dimmer' At 0",
        ]

    def test_the_forbidden_at_step_form_is_not_what_upstream_emits(self):
        # The one form M0 measured as accepted-and-inert. If upstream ever
        # started emitting it, every scene bundle would go quiet on stage with
        # ok:true on every line.
        fx = Fx(
            fx_id="pin2",
            display_name="핀2",
            pattern="pulse",
            steps=(
                FxStep(values=(StepValue(attribute="Dimmer", value=100.0),)),
                FxStep(values=(StepValue(attribute="Dimmer", value=0.0),)),
            ),
        )
        assert not [line for line in _step_lines(fx) if "At Step" in line]


# =============================================================================
# AC-SCENE-020 — LiveLock demotion, fired through the REAL gate
# =============================================================================

GROUPS_PATH = "DataPool/Groups"
SEQUENCES_PATH = "DataPool/Sequences"


def _section(path: str, children: list[tuple[int, str]]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": no, "name": name} for no, name in children],
        "node": {"childCount": len(children)},
        "truncated": False,
    }


class _RigStatePort:
    def __init__(self) -> None:
        self._tree = {
            GROUPS_PATH: _section(GROUPS_PATH, [(11, "Back"), (12, "Front")]),
            SEQUENCES_PATH: _section(SEQUENCES_PATH, [(1, "Opening")]),
        }

    def query_state(self, path: str) -> dict:
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _RefusingConsole:
    def send_command(self, command: str):  # pragma: no cover - must never run
        raise AssertionError(f"a console send was attempted under the live lock: {command!r}")


def _real_gate(tmp_path, *, locked: bool) -> SafetyGate:
    """A REAL SafetyGate. A fake returning the string "locked" proves nothing."""
    lock = LiveLock()
    if locked:
        lock.activate()
    return SafetyGate(
        console=_RefusingConsole() if locked else None,
        audit=AuditLog(tmp_path / "audit"),
        lock=lock,
    )


def _compile_first_scene(tmp_path, *, locked: bool):
    port = _RecordingPort()
    library = load_scene_library(SCENE_LIBRARY_DIR)
    registry = build_toolset(
        execution_port=port,
        state_port=_RigStatePort(),
        bundle_gate=_real_gate(tmp_path, locked=locked),
        scene_library=library,
    )
    scene_id = library.scenes[0].scene_id
    call = ToolCall(id="c1", name="compile_scene", arguments={"scene_id": scene_id, "group": 11})
    execution = registry.dispatch(call, None)
    return execution, json.loads(execution.result.content), port


class TestSceneCompilationUnderLiveLock:
    """AC-SCENE-020 — the demotion is INHERITED, and inheritance is an argument.

    M6 wired ``compile_scene`` to ``run_commands`` and reasoned the lock
    therefore applies "for free". Nobody had fired a locked scene bundle through
    it. That is what these tests do.
    """

    def test_the_unlocked_control_actually_sends(self, tmp_path):
        # Non-vacuity FIRST: a zero-send verdict is worthless if this fixture
        # cannot send at all. Same registry shape, lock off.
        _execution, payload, port = _compile_first_scene(tmp_path, locked=False)
        assert port.executed, "the unlocked control sent nothing — the fixture is broken"
        assert payload["executed"] is True
        assert "ChangeDestination Root" in port.executed

    def test_a_locked_scene_bundle_sends_nothing(self, tmp_path):
        _execution, payload, port = _compile_first_scene(tmp_path, locked=True)
        assert port.executed == []
        assert payload["executed"] is False

    def test_the_lock_is_what_stopped_it_not_a_refusal_upstream(self, tmp_path):
        # Discriminating: an unlisted group, a bad scene_id and a compile
        # refusal all also produce zero sends. Only the lock produces
        # gate_status "locked" with the bundle intact underneath.
        _execution, payload, _port = _compile_first_scene(tmp_path, locked=True)
        assert payload["gate_status"] == "locked"

    def test_the_whole_bundle_is_proposed_including_the_store(self, tmp_path):
        # Without the status co-assertion this survives a gate whose lock check
        # is a no-op — the EXECUTED outcome list has the same shape and the same
        # first and last line. The entries must be proposals, and ALL of them.
        _execution, payload, port = _compile_first_scene(tmp_path, locked=True)
        entries = payload["commands"]
        assert entries, "an empty proposal leaves the operator nothing to review"
        assert {entry["status"] for entry in entries} == {"proposal"}
        assert port.executed == []
        proposed = [entry["command"] for entry in entries]
        assert proposed[0] == "ChangeDestination Root"
        assert any(line.startswith("Store Sequence ") for line in proposed), (
            "the proposal stops before the Store — the operator would review a "
            "bundle that never says what it creates"
        )

    def test_the_report_still_rides_back_under_the_lock(self, tmp_path):
        # A demotion that loses the Korean report leaves the surface with a bare
        # gate status and no statement of what was NOT done.
        _execution, payload, _port = _compile_first_scene(tmp_path, locked=True)
        assert payload["succeeded"] is False
        assert payload["summary_ko"]

    def test_the_demotion_is_an_answer_not_an_error(self, tmp_path):
        # A LiveLock demotion is an ANSWER: the proposal IS the deliverable.
        # `is_error=True` would feed the model's self-correction loop and send it
        # back into the same lock — during a show, which is exactly when the lock
        # is on. `is_error` alone does not discriminate (fx measured a mutation
        # that survived exactly that assert), so the lock signature rides along.
        execution, payload, port = _compile_first_scene(tmp_path, locked=True)
        assert execution.result.is_error is False
        assert payload["gate_status"] == "locked"
        assert port.executed == []
        assert payload["succeeded"] is False

    def test_the_same_gate_still_holds_a_blacklisted_line(self, tmp_path):
        # Non-vacuity: a gate that clears everything would pass the unlocked
        # control for the wrong reason. Same instance, one blacklisted line.
        gate = _real_gate(tmp_path, locked=False)
        decision = gate.screen(["Delete Sequence 98"])
        assert decision.cleared is False


# =============================================================================
# the claim limits survive the whole chain (REQ-SCENE-014)
# =============================================================================


class TestTheClaimLimitsSurviveTheChain:
    @pytest.mark.parametrize("locked", [False, True])
    def test_the_effect_notice_rides_back_on_both_paths(self, tmp_path, locked):
        from server.scene.report import EFFECT_EVIDENCE_NOTICE

        _execution, payload, _port = _compile_first_scene(tmp_path, locked=locked)
        assert payload["report"]["claims"]["effect"] == EFFECT_EVIDENCE_NOTICE

    def test_a_locked_run_never_claims_the_artifact_exists(self, tmp_path):
        from server.scene.report import ARTIFACT_UNVERIFIED_NOTE

        _execution, payload, _port = _compile_first_scene(tmp_path, locked=True)
        assert payload["report"]["claims"]["artifact"] == ARTIFACT_UNVERIFIED_NOTE
