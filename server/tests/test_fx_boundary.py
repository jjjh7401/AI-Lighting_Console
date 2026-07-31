"""M6 — the fx layer's boundary as machine checks (AC-FXLIB-015/016/017/018).

M1~M5 each proved its own slice. What no slice could prove is that the slices
together stay INSIDE the boundary the SPEC drew: fx computes, the gate executes,
and neither the safety layer nor the rulebook learns that fx exists. Every claim
below is about the whole tree, not about a function.

* **AC-FXLIB-015** — no fx module reaches the execution path. An AST identifier
  scan, never a raw grep: ``server/fx/__init__.py`` documents the very chokepoint
  it is forbidden to call, so a text scan hits the docstring that STATES the
  invariant. That is the AP-19 correction ``test_looks_boundary.py`` already
  made, inherited here rather than re-litigated.
* **the dedupe exemption sets** — ``server/fx/instantiate.py`` re-declares
  ``_PROGRAMMER_STATE_COMMANDS`` instead of importing it, because ``tools.py``
  imports fx at registration time and a top-level fx->tools import would close a
  cycle. M4 checked the equality BY HAND and left the standing obligation to M6
  (progress.md §E.2 Gaps). Until this file existed, widening the set on the tool
  side let the fx guard wave a line through that the dedupe then dropped —
  silently, because ``Store`` still runs and the console still answers ok. A
  TEST may import both sides; that is not a runtime cycle.
* **AC-FXLIB-016** — LiveLock demotion through the REAL gate. A fake gate that
  hands back the string ``"locked"`` only proves we can read a string we wrote;
  the lock semantics belong to the gate, so the gate is the thing instantiated
  (the pattern ``test_busking_tool.py`` ``TestLiveLockDemotion`` established).
* **AC-FXLIB-017 / AC-FXLIB-018** — safety and rulebook are CONSUMED, not
  extended: the dependency runs one way, and the rulebook carries no fx
  vocabulary (decision G — the tool-schema description is the entire
  discoverability story).

Console contact: zero. Everything below is in-memory or static source reading.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from server.fx.instantiate import build_fx_bundle
from server.fx.loader import DEFAULT_LIBRARY_DIR, load_library_from_dir
from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "server"
FX_DIR = SERVER_DIR / "fx"
SAFETY_DIR = SERVER_DIR / "safety"
RULEBOOK_ASSETS = SERVER_DIR / "rulebook" / "assets" / "v2.4.2"


# =============================================================================
# AC-FXLIB-015 ② — the execution path is not reached from server/fx/**
# =============================================================================

# Symbols that only appear where execution is reached. Mirrors
# ``test_looks_boundary.py`` FORBIDDEN_IDENTIFIERS: the fx layer inherits the
# same single-chokepoint rule as its sister package (REQ-FXLIB-017).
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
    "server.orchestrator.tools",  # the fx->tools cycle the @MX:ANCHOR forbids
    "server.bridge",
)


def _fx_modules() -> list[Path]:
    return sorted(FX_DIR.rglob("*.py"))


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


class TestFxLayerTouchesNoExecutionPath:
    """AC-FXLIB-015 ② — identifier scan, offender count 0."""

    def test_the_scan_reaches_real_code_in_every_fx_module(self):
        # Non-vacuity: a scan that parsed nothing, or that only saw module
        # headers, passes for the wrong reason.
        modules = _fx_modules()
        assert len(modules) >= 6, f"expected the M1~M4 fx modules, saw {[p.name for p in modules]}"
        for path in modules:
            if path.name == "__init__.py":
                continue  # docstring only — its own test below
            count = len(_executable_identifiers(path))
            assert count > 20, f"{path.name} yielded only {count} identifiers"

    def test_the_scan_sees_identifiers_it_should_see(self):
        # A second non-vacuity control keyed to known symbols rather than a
        # count: if these stop appearing, the collector stopped walking bodies.
        identifiers = set(_executable_identifiers(FX_DIR / "instantiate.py"))
        assert "build_fx_bundle" in identifiers
        assert "server.fx.schema" in identifiers

    def test_no_fx_module_names_an_execution_path_symbol(self):
        offenders = [hit for path in _fx_modules() for hit in _offenders(path)]
        assert offenders == []

    def test_the_package_docstring_naming_the_chokepoint_survives_the_scan(self):
        # ``server/fx/__init__.py`` names run_commands -> gate.screen() to STATE
        # the invariant. It is load-bearing documentation, and this scan must
        # not be the reason it disappears (the AP-19 lesson).
        init = FX_DIR / "__init__.py"
        assert "gate.screen()" in init.read_text(encoding="utf-8")
        assert _offenders(init) == []

    def test_the_scan_catches_an_injected_call(self):
        # Mutation control, in-process: the same collector over source that DOES
        # call the execution path must report it. Without this, the empty result
        # above proves nothing about the scan.
        identifiers = _identifiers_of_source("def go(gate, cmds):\n    return gate.screen(cmds)\n")
        assert any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)

    def test_the_scan_catches_an_injected_bridge_import(self):
        identifiers = _identifiers_of_source("from server.bridge.osc import send\n")
        assert any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)

    def test_the_scan_catches_an_injected_tools_import(self):
        # The specific cycle the instantiate.py @MX:ANCHOR forbids: fx must not
        # import the tool layer to read the exemption set from it.
        identifiers = _identifiers_of_source(
            "from server.orchestrator.tools import _PROGRAMMER_STATE_COMMANDS\n"
        )
        assert any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)

    def test_the_scan_ignores_the_same_text_inside_a_docstring(self):
        # The exact discrimination a raw grep cannot make.
        prose = '"""Runs through gate.screen() via server.safety.console."""\nX = 1\n'
        identifiers = _identifiers_of_source(prose)
        assert not any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)
        assert not any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)

    def test_the_scan_ignores_the_same_text_inside_a_comment(self):
        prose = "# never call gate.screen() or import server.bridge here\nX = 1\n"
        identifiers = _identifiers_of_source(prose)
        assert not any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)
        assert not any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)


# =============================================================================
# AC-FXLIB-015 ③ — the architecture allow-lists gained no fx entry
# =============================================================================


class TestFxIsScannedByTheArchitectureGuardNotExemptedFromIt:
    """AC-FXLIB-015 ③ — ``_NAMED_TOOL_EXEMPTIONS`` diff 0.

    An entry here would silently license an OSC import from the fx package. The
    claim is therefore not only "fx is absent" but "the list is still exactly
    the two operator utilities it held before this SPEC" — a widened list is the
    same hole whether or not the new entry says "fx".
    """

    @staticmethod
    def _lists():
        from server.tests.test_architecture import _ALLOWED_PREFIXES, _NAMED_TOOL_EXEMPTIONS

        return _ALLOWED_PREFIXES, _NAMED_TOOL_EXEMPTIONS

    def test_fx_is_in_neither_allow_list(self):
        allowed, exemptions = self._lists()
        assert not any("fx" in prefix for prefix in allowed)
        assert not any("fx" in name for name in exemptions)

    def test_the_exemption_list_is_still_the_two_operator_tools(self):
        # If a THIRD exemption is ever legitimately added, this test is the
        # place that must be updated deliberately — that is what "diff 0" means
        # mechanically. It is not a style rule.
        _allowed, exemptions = self._lists()
        assert exemptions == frozenset(
            {"server/tools/osc_smoke.py", "server/tools/responder_roundtrip.py"}
        )

    def test_every_fx_module_actually_survives_the_architecture_filter(self):
        # Non-vacuity for the two tests above: "fx is not exempted" is worthless
        # if the walk never reaches fx in the first place. Replicate the guard's
        # own skip predicate and assert no fx file is skipped by it.
        allowed, exemptions = self._lists()
        skipped = [
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in _fx_modules()
            if path.relative_to(PROJECT_ROOT).as_posix().startswith(allowed)
            or path.relative_to(PROJECT_ROOT).as_posix() in exemptions
        ]
        assert skipped == []


# =============================================================================
# the dedupe exemption sets — M4's hand check, made mechanical
# =============================================================================


def _pattern_set(patterns) -> set[tuple[str, int]]:
    """A compiled-regex tuple as comparable (pattern text, flags) pairs."""
    return {(p.pattern, p.flags) for p in patterns}


class TestTheDedupeExemptionSetsAreEqual:
    """The obligation M4 recorded in its ``@MX:ANCHOR`` and left to M6.

    ``server/fx/instantiate.py`` decides which of ITS OWN lines the run_commands
    dedupe will compare. If the fx copy is NARROWER than the tool's, the guard
    reports a collision the dedupe would have exempted (a false alarm — loud,
    harmless). If it is WIDER, the guard waves through a line the dedupe then
    drops, and the drop is silent: ``Store`` still runs, the console still
    answers ok, and an incomplete cue is left behind. Only the second direction
    is dangerous, but both are asserted — a set equality has no cheaper form.
    """

    @staticmethod
    def _both():
        from server.fx.instantiate import _PROGRAMMER_STATE_COMMANDS as fx_side
        from server.orchestrator.tools import _PROGRAMMER_STATE_COMMANDS as tool_side

        return fx_side, tool_side

    def test_the_two_declarations_are_the_same_set(self):
        fx_side, tool_side = self._both()
        assert _pattern_set(fx_side) == _pattern_set(tool_side)

    def test_neither_side_is_empty(self):
        # Non-vacuity: two empty tuples are equal and would prove nothing.
        fx_side, tool_side = self._both()
        assert len(_pattern_set(fx_side)) == 3
        assert len(_pattern_set(tool_side)) == 3

    def test_the_comparison_notices_a_widened_tool_side(self):
        # Mutation control, in-process. This is the dangerous direction: the
        # tool exempts MORE than the fx guard knows about.
        fx_side, tool_side = self._both()
        widened = (*tool_side, re.compile(r"ChangeDestination\s+Root", re.IGNORECASE))
        assert _pattern_set(fx_side) != _pattern_set(widened)

    def test_the_comparison_notices_a_changed_flag(self):
        # A same-text pattern with different flags is a different matcher —
        # dropping IGNORECASE on one side alone would silently diverge on
        # "clearall" vs "ClearAll".
        fx_side, tool_side = self._both()
        reflagged = tuple(re.compile(p.pattern) for p in tool_side)
        assert _pattern_set(fx_side) != _pattern_set(reflagged)

    def test_the_comparison_notices_a_narrowed_tool_side(self):
        fx_side, tool_side = self._both()
        assert _pattern_set(fx_side) != _pattern_set(tool_side[:-1])


class TestTheTwoExemptionPredicatesAgreeOnRealBundleLines:
    """The behavioural half of the equality above.

    Two identical regex tuples could still be consumed differently — one side
    uses ``fullmatch``, and a ``search`` on the other would exempt
    ``ClearAll Sequence 1``. So the two PREDICATES are run over the lines the
    library actually produces, plus the near-misses that separate them.
    """

    @staticmethod
    def _predicates():
        from server.fx.instantiate import is_programmer_state as fx_side
        from server.orchestrator.tools import _is_programmer_state as tool_side

        return fx_side, tool_side

    @staticmethod
    def _real_bundle_lines() -> list[str]:
        library = load_library_from_dir(DEFAULT_LIBRARY_DIR)
        lines: list[str] = []
        for index, fx in enumerate(library.fx):
            plan = build_fx_bundle(fx, group=11, sequence=90 + index, label="M6")
            lines.extend(plan.commands)
        return lines

    ADVERSARIAL = (
        "ClearAll",
        "Clear",
        "clearall",
        "Group 11",
        "Group 11 + 12",
        "Group 11 Thru 14",
        "Fixture 3",
        "ClearAll Sequence 1",  # fullmatch says no; a search would say yes
        "Delete Group 11",
        "Store Sequence 98 Cue 1 'x'",
        "ChangeDestination Root",  # shared by every bundle and NOT exempt
        "Step 2",  # the line the cross-call fold turns on
        "  ClearAll  ",  # both sides strip before matching
    )

    def test_the_corpus_is_not_degenerate(self):
        # Non-vacuity: an all-exempt or all-non-exempt corpus makes agreement
        # trivial. Both verdicts must actually occur.
        fx_side, _tool_side = self._predicates()
        lines = self._real_bundle_lines() + list(self.ADVERSARIAL)
        assert len(lines) > 60, f"only {len(lines)} lines — the library did not load"
        verdicts = {fx_side(line) for line in lines}
        assert verdicts == {True, False}

    def test_both_predicates_agree_on_every_line_the_library_emits(self):
        fx_side, tool_side = self._predicates()
        disagreements = [
            (line, fx_side(line), tool_side(line))
            for line in self._real_bundle_lines() + list(self.ADVERSARIAL)
            if fx_side(line) != tool_side(line)
        ]
        assert disagreements == []

    def test_the_shared_first_line_of_every_bundle_is_not_exempt(self):
        # The M5 finding, pinned on both sides: the cross-call fold starts at
        # `ChangeDestination Root`, not at `Step 2`. If either predicate ever
        # exempts it, the second instantiation of an instruction turn stops
        # being detectable.
        fx_side, tool_side = self._predicates()
        assert fx_side("ChangeDestination Root") is False
        assert tool_side("ChangeDestination Root") is False

    def test_a_trailing_object_defeats_the_exemption_on_both_sides(self):
        # The fullmatch-vs-search discriminator, stated as its own case.
        fx_side, tool_side = self._predicates()
        assert fx_side("ClearAll") is True
        assert fx_side("ClearAll Sequence 1") is False
        assert tool_side("ClearAll") is True
        assert tool_side("ClearAll Sequence 1") is False


# =============================================================================
# AC-FXLIB-016 — LiveLock demotion, through the real gate
# =============================================================================

GROUPS_PATH = "DataPool/Groups"
SEQUENCES_PATH = "DataPool/Sequences"


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


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


def _section(path: str, children: list[tuple[int, str]]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": no, "name": name} for no, name in children],
        "node": {"childCount": len(children)},
        "truncated": False,
    }


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


def _fx_registry(gate, port):
    library = load_library_from_dir(DEFAULT_LIBRARY_DIR)
    return build_toolset(
        execution_port=port,
        state_port=_RigStatePort(),
        bundle_gate=gate,
        fx_library=library,
    ), library


def _instantiate_first_fx(tmp_path, *, locked: bool):
    port = _RecordingPort()
    registry, library = _fx_registry(_real_gate(tmp_path, locked=locked), port)
    fx_id = library.fx[0].fx_id
    call = ToolCall(id="c1", name="instantiate_fx", arguments={"fx_id": fx_id, "group": 11})
    execution = registry.dispatch(call, None)
    return execution, json.loads(execution.result.content), port


class TestFxInstantiationUnderLiveLock:
    """AC-FXLIB-016 — the demotion is INHERITED, and inheritance is an argument.

    M5 wired ``instantiate_fx`` to ``run_commands`` and reasoned that the lock
    therefore applies "for free". Nobody had fired a locked fx bundle through
    it. That is what these tests do.
    """

    def test_the_unlocked_control_actually_sends(self, tmp_path):
        # Non-vacuity FIRST: a zero-send verdict is worthless if this fixture
        # cannot send at all. Same registry shape, lock off.
        _execution, payload, port = _instantiate_first_fx(tmp_path, locked=False)
        assert port.executed, "the unlocked control sent nothing — the fixture is broken"
        assert payload["executed"] is True
        assert "ChangeDestination Root" in port.executed

    def test_a_locked_fx_bundle_sends_nothing(self, tmp_path):
        _execution, payload, port = _instantiate_first_fx(tmp_path, locked=True)
        assert port.executed == []
        assert payload["executed"] is False

    def test_the_lock_is_what_stopped_it_not_a_refusal_upstream(self, tmp_path):
        # Discriminating: an unlisted group, a bad fx_id and a grammar failure
        # all also produce zero sends. Only the lock produces gate_status
        # "locked" with the bundle intact underneath.
        _execution, payload, _port = _instantiate_first_fx(tmp_path, locked=True)
        assert payload["gate_status"] == "locked"

    def test_the_whole_bundle_is_proposed_not_a_prefix(self, tmp_path):
        # Measured: without the status co-assertion this survives a gate whose
        # lock check is a no-op — the EXECUTED outcome list has the same shape
        # and the same first and last line, so "first line + a Store is present"
        # passes for a bundle that actually fired. The entries must be
        # proposals, and they must be ALL of them.
        _execution, payload, port = _instantiate_first_fx(tmp_path, locked=True)
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
        assert proposed[-1] == "ClearAll"

    def test_every_proposed_line_carries_the_proposal_status(self, tmp_path):
        _execution, payload, _port = _instantiate_first_fx(tmp_path, locked=True)
        assert {entry["status"] for entry in payload["commands"]} == {"proposal"}

    def test_the_report_still_rides_back_under_the_lock(self, tmp_path):
        # A demotion that loses the Korean report leaves the surface with a bare
        # gate status and no statement of what was NOT done.
        _execution, payload, _port = _instantiate_first_fx(tmp_path, locked=True)
        assert payload["succeeded"] is False
        assert payload["summary_ko"]

    def test_the_demotion_is_reported_as_an_error_result(self, tmp_path):
        # CHARACTERIZATION, not an endorsement. `instantiate_fx` sets
        # is_error = run_commands.is_error OR not report.succeeded, so a lock
        # demotion arrives as is_error=True — unlike `busking_bundle`, which
        # deliberately returns is_error=False so the self-correction loop does
        # not retry into the same lock (tools.py, AC-BUSKWIZ-010). The
        # divergence is real and is recorded in the M6 report as a finding; it
        # is pinned here so a later change to it is a deliberate one.
        # `is_error` alone does not discriminate (M5 measured a mutation that
        # survived exactly that assert), so the lock signature rides along.
        execution, payload, port = _instantiate_first_fx(tmp_path, locked=True)
        assert execution.result.is_error is True
        assert payload["gate_status"] == "locked"
        assert port.executed == []


# =============================================================================
# AC-FXLIB-017 — the safety layer is consumed, never extended
# =============================================================================


class TestSafetyInvariantsAreInherited:
    """AC-FXLIB-017 — ``server/safety/**`` did not learn that fx exists.

    A diff of zero is the AC's own wording, and the git check that produces it
    is run outside pytest. What a test CAN hold is the property the diff is a
    proxy for: the dependency runs one way, and an fx bundle passes the real
    screening semantics without an exception carved for it.
    """

    def test_no_safety_module_names_the_fx_package(self):
        offenders = [
            f"{path.name}: {identifier}"
            for path in sorted(SAFETY_DIR.rglob("*.py"))
            for identifier in _executable_identifiers(path)
            if identifier.startswith("server.fx")
        ]
        assert offenders == []

    def test_the_scan_reaches_the_safety_modules(self):
        # Non-vacuity for the test above.
        modules = sorted(SAFETY_DIR.rglob("*.py"))
        assert len(modules) >= 5
        identifiers = set(_executable_identifiers(SAFETY_DIR / "gate.py"))
        assert "server.safety.lock" in identifiers

    def test_a_real_fx_bundle_clears_the_real_gate_with_no_hold(self, tmp_path):
        # "무보류 통과 집합" — the fx bundle lines land in the no-hold set of the
        # EXISTING classifier. No approval port is wired, so a held line would
        # fail here rather than quietly wait.
        library = load_library_from_dir(DEFAULT_LIBRARY_DIR)
        gate = _real_gate(tmp_path, locked=False)
        for index, fx in enumerate(library.fx):
            plan = build_fx_bundle(fx, group=11, sequence=90 + index, label="M6")
            decision = gate.screen(list(plan.commands))
            assert decision.cleared is True, f"{fx.fx_id}: {decision.status}"

    def test_the_same_gate_still_holds_a_blacklisted_line(self, tmp_path):
        # Non-vacuity: a gate that clears everything would pass the test above
        # for the wrong reason. Same instance, one blacklisted line.
        gate = _real_gate(tmp_path, locked=False)
        decision = gate.screen(["Delete Sequence 98"])
        assert decision.cleared is False


# =============================================================================
# AC-FXLIB-018 — the rulebook carries no fx vocabulary (decision G)
# =============================================================================

FX_TOOL_VOCABULARY = ("find_fx", "instantiate_fx", "fx_id")


def _rulebook_assets() -> list[Path]:
    return sorted(RULEBOOK_ASSETS.rglob("*.md"))


class TestTheRulebookNeverLearnedAboutFx:
    """AC-FXLIB-018 — byte-diff 0 has a property behind it.

    Decision G put the whole discoverability burden on the tool-schema
    description precisely so the fixed prefix would not change: one changed byte
    invalidates the provider cache prefix. A helpful sentence added to the
    rulebook is the failure this guards, and it is exactly the kind of edit that
    reads as harmless.
    """

    def test_no_rulebook_asset_names_an_fx_tool(self):
        offenders = [
            f"{path.name}: {token}"
            for path in _rulebook_assets()
            for token in FX_TOOL_VOCABULARY
            if token in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_the_scan_reads_the_real_asset_text(self):
        # Non-vacuity: `find_looks` IS there, in the fallback sentence M5 found.
        # Scoped to the whole sentence rather than the bare token, because the
        # bare phrase also occurs three other places in the same file and would
        # keep this control green after the sentence itself was rewritten.
        text = (RULEBOOK_ASSETS / "31_choreography_patterns.md").read_text(encoding="utf-8")
        assert "the STEP 1 FALLBACK path, used when `find_looks`" in text

    def test_the_asset_set_is_the_one_the_prefix_is_assembled_from(self):
        # If an asset is added or dropped, the fixed prefix changed even when
        # every surviving file is byte-identical.
        assert [path.name for path in _rulebook_assets()] == [
            "00_grammar.md",
            "10_object_model.md",
            "20_korean_terms.md",
            "30_plugin_patterns.md",
            "31_choreography_patterns.md",
        ]

    @pytest.mark.parametrize("token", FX_TOOL_VOCABULARY)
    def test_the_fx_vocabulary_is_carried_by_the_tool_descriptions_instead(self, token):
        # The other half of decision G: the words are absent from the rulebook
        # BECAUSE the tool DESCRIPTIONS carry them. If they were absent from
        # both, the layer would simply be undiscoverable.
        #
        # Descriptions only — scanning the whole schema would include the tool
        # NAMES, and then two of the three tokens are present no matter what the
        # descriptions say (measured: `find_fx` and `instantiate_fx` are tool
        # names). A name-inclusive scan is green for an empty description.
        registry, _library = _fx_registry(None, _RecordingPort())
        descriptions = "\n".join(
            d.description for d in registry.definitions() if d.name in ("find_fx", "instantiate_fx")
        )
        assert token in descriptions
