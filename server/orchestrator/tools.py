"""The four Phase 1 tools (REQ-MVP-005) built on the execution/state ports.

Tools never touch the OSC bridge — they depend on :mod:`server.orchestrator.ports`
only (REQ-MVP-029 forward design). ``deploy_plugin`` (M7) drives the deploy
pipeline — pcall compile harness + destructive scan + human review gate
(REQ-MVP-019); without a wired pipeline it stays a safe structured error and
never sends anything.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol

from server.fx.instantiate import FxInstantiationError
from server.fx.instantiate import instantiate_fx as bind_fx
from server.fx.loader import DEFAULT_LIBRARY_DIR as FX_LIBRARY_DIR
from server.fx.loader import FxSchemaError
from server.fx.loader import load_library_from_dir as load_fx_library_from_dir
from server.fx.matching import match_fx
from server.fx.report import build_report as build_fx_report
from server.fx.report import to_korean as fx_report_to_korean
from server.fx.schema import FxLibrary
from server.groupgen.write import (
    GroupSlotError,
    build_group_write_plan,
    guard_bundle_collision,
)
from server.llm.types import ToolCall, ToolDefinition, ToolResult
from server.looks.busking import build_genre_bundle, select_genre
from server.looks.instantiate import (
    CAPTURE_PER_FAMILY,
    CAPTURE_SHAPES,
    CAPTURE_SHARED,
    LookInstantiationError,
    build_instantiation,
    resolve_pools,
)
from server.looks.layout import build_layout_commands, plan_layout
from server.looks.loader import LookSchemaError, load_library_from_dir
from server.looks.matching import match_looks
from server.looks.report import build_report, to_korean
from server.looks.resolver import resolve_roles
from server.looks.schema import LookLibrary
from server.looks.songcue import (
    EXPLICIT_DYNAMICS_REQUIRED,
    SectionTimeError,
    SequenceNumberError,
    SongCueBundleError,
    build_songcue_bundle,
    build_songcue_timing,
    map_sections_to_looks,
    parse_sections,
)
from server.looks.songcue_report import build_songcue_report
from server.orchestrator.layout_occupancy import check_occupancy
from server.orchestrator.ports import (
    BundleGate,
    CommandExecutionPort,
    PropertyQueryPort,
    StateQueryPort,
)
from server.prechk.footprint import WalkOutcome, walk_mode_widths
from server.prechk.inventory import InventoryReadError, read_inventory
from server.prechk.macro import MacroPolicy, MacroResult, build_response_check_macro
from server.prechk.macro import groups_from_snapshot as read_group_pool
from server.prechk.patch import evaluate_patch
from server.prechk.query import PropertyRead, read_properties
from server.prechk.report import build_report as build_precheck_report
from server.preshow.osc_check import LivenessPort as PreshowLivenessPort
from server.preshow.runner import run_preshow_checklist
from server.safety.approval import (
    ApprovalItem,
    ApprovalPort,
    ApprovalRequest,
    DenyAllApprovalPort,
)
from server.scene.compile import SceneCompilationError
from server.scene.compile import compile_scene as build_scene_bundle
from server.scene.loader import DEFAULT_LIBRARY_DIR as SCENE_LIBRARY_DIR
from server.scene.loader import SceneSchemaError
from server.scene.loader import load_library_from_dir as load_scene_library_from_dir
from server.scene.loader import parse_timing as parse_scene_timing
from server.scene.loader import validate_label as validate_scene_label
from server.scene.matching import match_scene
from server.scene.report import build_report as build_scene_report
from server.scene.report import to_korean as scene_report_to_korean
from server.scene.schema import SceneLibrary
from server.spatial import (
    SpatialAnalysisError,
    analyze_spatial_records,
    spatial_analysis_to_dict,
    spatial_fixtures_from_records,
)
from server.spatial.fixture_type import (
    FixtureTypeAnalysisError,
    analyze_fixture_type_records,
    fixture_type_analysis_to_dict,
)
from server.spatial.naming import (
    name_concentric_bucket,
    name_depth_bucket,
    name_lateral_bucket,
    name_vertical_bucket,
)
from server.spatial.presets import (
    SPATIAL_PRESETS,
    SpatialPlacement,
    SpatialPresetError,
    spatial_placements_to_records,
    spatial_preset_placements,
)
from server.spatial.topology import TopologyResult
from server.spatial.topology import classify as classify_topology

if TYPE_CHECKING:  # policy types only — no runtime import cycle
    from server.deploy.pipeline import DeployOutcome

# The dependency runs ONE way: this module reads the look layer, the look layer
# never reads this one. M3 kept the two rig-context failure reasons unenumerated
# in the resolver for exactly this reason — the reverse edge would close a cycle
# (tools -> matching -> resolver -> tools).
TOOL_NAMES = (
    "run_commands",
    "query_state",
    "deploy_plugin",
    "get_rig_context",
    "find_looks",
    "instantiate_look",
    "prepare_busking",
    "prepare_songcue",
    "precheck_patch",
    "preshow_check",
    "find_fx",
    "instantiate_fx",
    "find_scene",
    "compile_scene",
    "build_patch_sheet",
    "build_cue_sheet",
    "build_preset_list",
    "plan_executor_layout",
    "get_spatial_context",
    "arrange_fixtures",
    "classify_arrangement_topology",
    "create_arrangement_groups",
)

# Object-tree paths for the rig-context summary (REQ-MVP-037). LIVE-CALIBRATED
# against grandMA3 onPC 2.4.2: the previous placeholders "Patch/Fixtures" and
# "DataPool/Presets" DO NOT EXIST on 2.4.2 (both reply "path segment not
# found"), so patch and preset vocabulary reached the model as an "unavailable"
# section on EVERY call and only groups ever got through. Override via
# build_toolset(rig_paths=...).
#
# What each path actually yields (read live, one tree level deep):
#   fixtures     - the stage's patched fixtures. An entry's "no" is its slot in
#                  that list; whether that slot equals the fixture id (FID) is
#                  NOT established by this snapshot, so it is never presented
#                  as an FID.
#   groups       - the group pool; here "no" IS the pool number you address
#                  (Group <no>).
#   preset_pools - the preset TYPES (Dimmer, Position, Gobo, Color, ...), i.e.
#                  ONE LEVEL ABOVE the individual stored presets. Those live
#                  INSIDE each pool ("DataPool/PresetPools/<no>") — opened by
#                  the drill-down below, because "a Color pool exists" and "a
#                  colour is stored in it" are different answers and only the
#                  second one tells you whether a recall will do anything.
#   sequences    - the cue lists a look is stored into.
#   pages        - executor pages; their CHILDREN are the executors, which are
#                  the only surface that actually fires a stored look.
#   macros /
#   plugins      - what already automates this show.
#   matricks /
#   worlds       - selection shaping and filtering vocabulary.
#
# Every path here was read back from a live onPC 2.4.2 on 2026-07-22 before
# being made a default. Guessed paths are how "Patch/Fixtures" and
# "DataPool/Presets" shipped dead for the whole of Stage 1.
#
# ASSUMPTION (stage slot, live-observed on ONE showfile): fixtures are read
# from stage slot 1. 2.4.2 creates "Stage 1" at slot 1 by default and the
# calibration showfile matches, but a show whose stage sits at another slot
# resolves nothing here. Stage auto-discovery is deliberately NOT implemented;
# the failure is made legible instead — get_rig_context reports such a section
# with reason "path_not_resolved" (a configuration defect) rather than the soft
# "unavailable" string that let the two dead paths above survive unnoticed.
# Point rig_paths= at the real stage to override.
DEFAULT_RIG_CONTEXT_PATHS = {
    "fixture_types": "Patch/FixtureTypes",
    "fixtures": "Patch/Stages/1/Fixtures",
    "groups": "DataPool/Groups",
    "sequences": "DataPool/Sequences",
    "preset_pools": "DataPool/PresetPools",
    "macros": "DataPool/Macros",
    "plugins": "DataPool/Plugins",
    "pages": "DataPool/Pages",
    "matricks": "DataPool/MAtricks",
    "worlds": "DataPool/Worlds",
}

# Sections whose children are CONTAINERS worth opening. A depth-1 snapshot of
# these answers "does it exist"; the show-readiness question is "is anything IN
# it", and that needs one query per child.
DEFAULT_RIG_DRILLDOWN = ("preset_pools", "pages")

# Ceiling on second-level queries per get_rig_context call. Each drill query is
# a UDP round trip through the gate + audit, so an unbounded walk would make rig
# context cost scale with the size of the showfile. When the ceiling stops the
# walk the section says so ("drilldown_capped") rather than presenting a partial
# walk as a complete one.
RIG_DRILLDOWN_QUERY_CAP = 16

# The two sections a look must be bound against: the groups its position roles
# resolve to, and the preset pools its values are stored into. Named rather
# than derived, so a rig_paths override that drops either one fails loudly
# instead of binding a look against half a rig.
# `SafetyGate._check_lock`가 LiveLock에서 발화하는 게이트 상태
# (`server/safety/gate.py:478`). per-command status "proposal"과 다른 층이다.
_LOCKED = "locked"

LOOK_RIG_SECTIONS = ("groups", "preset_pools")
SONGCUE_RIG_SECTIONS = ("groups", "sequences")

# The two sections an fx must be bound against: the group its steps are captured
# on, and the sequence pool a free number is MEASURED from. Same naming
# discipline as the two above — a rig_paths override that drops either one fails
# by name rather than by storing a phaser onto a number nobody read.
FX_RIG_SECTIONS = ("groups", "sequences")

# A scene is bound against the same two sections as an fx — the group its values
# are captured on, and the sequence pool a free number is MEASURED from. Named
# separately rather than aliased to `FX_RIG_SECTIONS`: the two layers are free
# to diverge, and a shared name would make that divergence a silent edit here.
SCENE_RIG_SECTIONS = ("groups", "sequences")

# The two sections the pre-check's macro axis is wired against: the group pool it
# reads its targets from, and the macro pool it derives a free slot from. Named
# for the same reason as the two above — a rig_paths override that drops either
# one must fail by NAME, not by an IndexError rendered as a pool that failed to
# read (independent PR #7 review, P3).
PRECHK_RIG_SECTIONS = ("groups", "macros")

# The rig-context section the footprint bound needs. A SEPARATE tuple from
# PRECHK_RIG_SECTIONS on purpose: that guard sits INSIDE the `create_macro`
# branch, so adding a section to it would make one and the same override omission
# behave differently depending on an argument — an error when a macro was asked
# for, silence when it was not. The bound axis does not care about `create_macro`,
# so it gets its own always-checked tuple.
#
# A missing section here does NOT fail the call. It cannot: the two tests that
# pin the macro guard's message (`server/tests/test_prechk_tool.py:895-905`,
# `:907`) pass an override with neither this section nor the macro ones, and an
# error raised first would replace the message they assert. It should not either
# — refusing the whole call would DISCARD the fixture inventory this tool exists
# to produce, the same shape as the zero-target macro defect below. So the check
# names the missing section in the report and the overlap axis grades itself
# `not_performed`.
PRECHK_FOOTPRINT_SECTIONS = ("fixture_types",)

# Query ceiling for the three-tier footprint walk: one root read, one per fixture
# type, one per mode. The type count is UNMEASURED on any rig, so this is a
# deliberate over-provision rather than a fitted number, and exhaustion is safe by
# construction — the walk returns an incomplete outcome and the axis grades itself
# `not_performed` rather than folding a bound over a partial mode set. Kept beside
# RIG_DRILLDOWN_QUERY_CAP so the two ceilings are read together; they are separate
# because they bound separate walks reached by separate tools.
PRECHK_FOOTPRINT_QUERY_CAP = 40

# The macro-line property that holds the command text, on both the authoring side
# (`Set Macro <slot>.<line> Property 'Command' ...`) and the read-back side.
# `server/safety/classify.py:140-141` screens the same name.
_MACRO_COMMAND_PROPERTY = "Command"

# Stand-in slot for the branch that authors NOTHING. `MacroPolicy.available`
# requires a positive slot, and `build_response_check_macro` answers every
# zero-target case BEFORE it reads `policy.macro_slot`
# (`server/prechk/macro.py:441-457`), so on that branch no slot is ever spoken
# and the pool read that would derive a real one is pure cost. Deliberately NOT
# 1: slot 1 holds the responder's own `Copilot Go` macro on the measured rig, so
# if that early return ever stopped holding, a placeholder of 1 would make
# overwriting the console link the quiet failure mode. The handler additionally
# refuses to execute anything produced under this policy, which is what keeps the
# number off the wire rather than trust in another module's control flow.
_UNSPOKEN_MACRO_SLOT = 9999

# The preset-pool drill is not optional on the look path. Occupancy is what
# makes "is this slot free" answerable at all; without it every store is
# skipped as unobserved — safe, and useless. get_rig_context's own drilldown
# configuration is left untouched.
_LOOK_DRILLDOWN = frozenset({"preset_pools"})


# Why a rig-context section is missing. The two causes are NOT interchangeable
# and used to be indistinguishable — both surfaced as one soft "unavailable"
# string, which is exactly how the two dead default paths above went unnoticed
# for the whole of Stage 1:
#   path_not_resolved   - a SIBLING section answered, so the console is
#                         demonstrably reachable and THIS path is wrong for
#                         this showfile: a configuration defect, fix the path.
#   console_unreachable - nothing answered, so no path can be blamed: an
#                         operational condition, retry when the console is up.
#
# Public because the show-control panel builds its catalog from the SAME two
# sections and must reach the same verdict (REQ-SHOWUI-002); two copies of this
# split would be two chances to merge them back into one soft "unavailable".
REASON_UNRESOLVED = "path_not_resolved"
REASON_UNREACHABLE = "console_unreachable"
_FAILURE_MESSAGES = {
    REASON_UNRESOLVED: (
        "this path does not exist in the loaded showfile — other sections "
        "answered, so the console IS reachable"
    ),
    REASON_UNREACHABLE: "no section answered — the console did not respond",
}


@dataclass(frozen=True)
class ExecutionContext:
    """Instruction-scoped dispatch context (self-correction dedupe state)."""

    executed_ok: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CommandOutcome:
    """Per-command execution status within one run_commands bundle.

    Execution statuses: "executed_ok" | "failed" | "not_executed" |
    "skipped_already_executed". Gate screening statuses (M4, when a bundle
    gate is wired): "blocked" | "rejected" | "proposal" | "held".
    """

    command: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class ToolExecution:
    """One dispatched tool call: the model-facing result + runner-facing outcomes."""

    result: ToolResult
    command_outcomes: tuple[CommandOutcome, ...] = ()


_Handler = Callable[[ToolCall, ExecutionContext], ToolExecution]

_EMPTY_CONTEXT = ExecutionContext()


# -- the dedupe exemption (M4 follow-up) ---------------------------------------
#
# Dedupe exists to prevent a duplicated DURABLE side effect. A command that
# establishes programmer state has no durable artifact to duplicate — it is
# idempotent in effect but POSITION-DEPENDENT in meaning. `ClearAll` appearing
# twice is not the same instruction twice; it is one instruction that must run
# at two different moments.
#
# The set is enumerated, not inferred, and deliberately small: the two
# programmer clears (00_grammar.md:57-58), and the BARE selection form of the
# two object types that select fixtures into the programmer. It is anchored on
# the command's LEADING token, because that is the discriminator between a bare
# selection and a command that creates or destroys something: `Store Group 7`,
# `Label Group 7 'Vocals'`, `Delete Group 3` and `Store Fixture 5` all carry a
# selection operand, and all leave an artifact behind (00_grammar.md "Frequently
# used functions"). A selection carrying a value is out too — `Group 3 Full` and
# `Fixture 1 Thru 10 At 80` set rather than merely select.
#
# `Clear` and `ClearAll` are SEPARATE patterns, matched independently under
# fullmatch, so neither can be caught by the other's pattern and no test for one
# can pass on the strength of the other.
#
# The operand grammar (`3`, `11 + 12`, `1 Thru 10`, `11 Thru`, `11 Thru 19 - 15`)
# is 00_grammar.md:17-22, where `Thru` / `+` / `-` are general object-reference
# operators — `Cue 3 Thru 7` is the rulebook's own non-Fixture example — so the
# two types share one operand pattern rather than being spelled out twice.
# Matching is case-insensitive because the console is (audit finding D14).
#
# NOT exempt, and not a style call: the `Select ...` prefix form. It is a
# command this project is forbidden to EMIT at all — `Select Fixture ...` and
# `SelFix ...` both returned "Illegal object" on live 2.4.2 and the rulebook
# directs the bare `Fixture ...` / `Group ...` forms instead
# (31_choreography_patterns.md:30-31; the measurement is on the Fixture forms,
# the bare-form directive covers Group). Exempting it from dedupe would
# pre-approve a command that can only ever fail. Secondary reason: admitting one
# benign leading verb costs the discriminator its "a leading verb means it
# creates or destroys something" simplicity.
#
# A wide selection is still the GATE's business, not this predicate's: an
# open-ended `Thru` is screened upstream (server/safety/classify.py) before any
# of this runs, so exempting one from dedupe never widens what may execute.
_SELECTION_OPERAND = r"\d+(?:\s*[-+]\s*\d+|\s+Thru(?:\s+\d+)?)*"
_PROGRAMMER_STATE_COMMANDS = (
    re.compile(r"Clear", re.IGNORECASE),  # step clear (selection -> values)
    re.compile(r"ClearAll", re.IGNORECASE),  # clear the whole programmer
    re.compile(rf"(?:Fixture|Group)\s+{_SELECTION_OPERAND}", re.IGNORECASE),  # bare selection
)


def _is_programmer_state(command: str) -> bool:
    """True for a command that establishes programmer state (exempt from dedupe)."""
    text = command.strip()
    return any(pattern.fullmatch(text) is not None for pattern in _PROGRAMMER_STATE_COMMANDS)


class DeployPipelinePort(Protocol):
    """The M7 deploy pipeline surface consumed by the deploy_plugin tool."""

    def deploy(self, name: str, lua_source: str) -> DeployOutcome: ...


# DeployOutcome.status -> per-command outcome status on the chat surface.
# "blocked" statuses count toward the self-correction retry cap; a human
# review rejection is NOT a technical failure (mirror of the M4 rule).
_DEPLOY_OUTCOME_STATUS = {
    "deployed": "executed_ok",
    "blocked_input": "blocked",
    "blocked_compile": "blocked",
    "blocked": "blocked",
    "review_rejected": "rejected",
    "deploy_failed": "failed",
}


# -- shared rig-shape helpers --------------------------------------------------
#
# ``rig_object`` / ``rig_section`` / ``drill_into`` are PURE (they touch only
# their arguments and the injected state port) and are public because a second
# reader of the same console shape now exists: the show-control panel's catalog
# builder (``server/web/panel.py``, SPEC-COPILOT-SHOWUI-001 REQ-SHOWUI-001).
# Sharing them rather than re-deriving the shape is what keeps ONE answer to the
# questions this snapshot is ambiguous about — the real-`no`-not-position rule,
# the truncation signal, and the unopened-vs-verified-empty distinction. Two
# copies would be two chances to answer one of them differently.


# @MX:NOTE: [AUTO] rig-context exposes the REAL pool number ('no'), not a bare
# positional index — stops the model mapping "the Nth item" onto "object N" and
# inventing a non-existent object on a non-contiguous rig (a hallucinated
# "Group 3" when groups live at pool 1, 2, 7). Live-demo finding #3,
# SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-029 / AC-DEPLOY-020.
def rig_object(child: dict) -> dict[str, object]:
    """One rig-context object: its REAL slot number (``no``) + ``name``.

    For a pool (groups, preset pools) that slot IS the pool number the console
    addresses (``Group <no>``); for a container that is not a pool (the stage's
    fixture list) it is the position the responder established within that
    container, which the tool description explicitly declines to present as a
    fixture id. Either way it is a number the responder READ, never one this
    code counted.

    The responder emits ``{"i": <pool-slot>, "name": ..., "class": ...}`` but
    ONLY when it positively established that slot; a child whose slot it could
    not establish arrives WITHOUT ``i`` (``console/lua/copilot_responder.lua``
    build_snapshot / safe_children, PROTOCOL.md §4.2 — the responder never
    substitutes the listing position, and ``server/safety/console.py`` relies
    on the same guarantee for its slot arithmetic).

    That absence is meaningful, not a glitch: it degrades to a name-only entry
    so the model has no number to address — it must resolve the real one (e.g.
    via ``query_state``) instead of counting list positions.
    """
    number = child.get("i")
    name = child.get("name", "")
    if number is None:
        return {"name": name}
    return {"no": number, "name": name}


def rig_section(objects: list[dict[str, object]], payload: dict) -> dict[str, object]:
    """Wrap a resolved section with what the responder said about its OWN
    completeness (PROTOCOL.md §4 ``truncated`` / ``node.childCount``).

    A short list with no completeness signal is worse than no list at all: the
    model would reason, confidently, over a rig it could not fully see. Absence
    of a real ``childCount`` reads as an unknown total, never as "the count
    equals what arrived".
    """
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None
    return {
        "objects": objects,
        "truncated": bool(payload.get("truncated", False)),
        "total": child_count if isinstance(child_count, int) else None,
    }


def drill_into(
    state_port: StateQueryPort,
    objects: list[dict[str, object]],
    base_path: str,
    entry: dict[str, object],
    budget: int,
) -> int:
    """Open each object in ``objects`` as a container, IN PLACE, spending at
    most ``budget`` queries total (shared across every drilled section in one
    get_rig_context call).

    Distinguishes a verified-EMPTY container (``contents: []``) from one the
    drill could not reach (``contents_unavailable: True``) — collapsing the two
    would make a console that failed mid-walk look identical to a show with
    nothing configured, which is exactly the ambiguity a readiness check exists
    to remove.

    When the budget runs out before every object is opened, the section is
    marked ``drilldown_capped`` rather than silently presenting a partial walk
    as a complete one — each query is a UDP round trip through the gate +
    audit, so an unbounded walk would make rig-context cost scale with the
    size of the showfile.
    """
    capped = False
    for obj in objects:
        number = obj.get("no")
        if number is None:
            continue  # no real address to drill into (degraded name-only entry)
        if budget <= 0:
            capped = True
            break
        budget -= 1
        try:
            child_payload = state_port.query_state(f"{base_path}/{number}")
        except Exception:
            obj["contents_unavailable"] = True
            continue
        children = child_payload.get("children", [])
        obj["contents"] = [rig_object(c) for c in children if isinstance(c, dict)]
    if capped:
        entry["drilldown_capped"] = True
    return budget


def collect_rig_sections(
    state_port: StateQueryPort,
    paths: Mapping[str, str],
    drilldown: frozenset[str],
    budget: int,
) -> tuple[dict[str, object], int, int]:
    """Read each named section, drilling the ones in ``drilldown``.

    Returns ``(summary, resolved, failed)``. A failed section is replaced by the
    ``{"reason": ...}`` shape, classified by the SAME rule for every caller: a
    sibling section answering means this path is wrong for this showfile
    (``path_not_resolved``), nothing answering means no path can be blamed
    (``console_unreachable``).

    Shared rather than re-derived because a second caller of the same shape now
    exists (``instantiate_look``), and two copies of that classification would
    be two chances to collapse it back into one soft "unavailable" — the exact
    regression the two dead default paths hid behind for the whole of Stage 1.
    The sample size differs (ten sections vs two) and the rule does not: with
    one sibling answering, "the console is up and this path is wrong" is the
    same inference it is with nine.
    """
    summary: dict[str, object] = {}
    failures: dict[str, tuple[str, str]] = {}
    resolved = 0
    for section, path in paths.items():
        try:
            payload = state_port.query_state(path)
        except Exception as exc:
            # Placeholder keeps the section's position; classified below, once
            # every section's outcome is known.
            summary[section] = None
            failures[section] = (path, str(exc))
            continue
        # A resolved path proves the console ANSWERED — even with zero children
        # (a real shape: an empty preset pool).
        resolved += 1
        children = payload.get("children", [])
        objects = [rig_object(child) for child in children if isinstance(child, dict)]
        entry = rig_section(objects, payload)
        if section in drilldown:
            budget = drill_into(state_port, objects, path, entry, budget)
        summary[section] = entry
    reason = REASON_UNRESOLVED if resolved else REASON_UNREACHABLE
    for section, (path, detail) in failures.items():
        summary[section] = {
            "reason": reason,
            "path": path,
            "error": f"{_FAILURE_MESSAGES[reason]}: {detail}",
        }
    return summary, resolved, len(failures)


# -- spatial read helpers (SPEC-COPILOT-SPATIAL-001 M1) ------------------------
#
# @MX:NOTE: [SPEC] The READ channel is candidate A — the responder's EXISTING
#   ``prop`` verb, one fixture at a time, no new wire (design.md §2.1, adopted
#   as decision D-1 in progress.md §E.2.8). Candidate B (a bulk ``spatial``
#   verb) was deliberately left unbuilt: it costs a responder branch, a
#   PROTOCOL.md revision, a protocol builder, a console redeploy and a version
#   negotiation, and the live round-trip measurement below says the per-fixture
#   loop fits the budget without any of them. Do not promote this to a new verb
#   without a MEASUREMENT saying the loop stopped fitting.
# @MX:SPEC: SPEC-COPILOT-SPATIAL-001 REQ-SPATIAL-001/004/006/007.

#: Which source answered (REQ-SPATIAL-002). A fixed string rather than a
#: computed one: the Layout-pool source is DEFERRED by decision D-3 — the
#: measured showfile's only layout has zero assigned elements, so it holds no
#: coordinate to prefer — and a reply that could not name its provenance is
#: exactly the shape this field exists to prevent.
SPATIAL_SOURCE_PATCH3D = "patch3d"

#: The properties ONE fixture costs. All four were read back from a live onPC
#: 2.4.2 on all 19 fixtures of the calibration rig (progress.md §E.2.1), where
#: property lookup also proved case-INSENSITIVE — so the spelling here is a
#: style choice, not a probe result. ``name`` is deliberately absent: the
#: container snapshot already carries it, and spending a round trip to re-read
#: a string we already hold is the whole difference between the 4-per-fixture
#: budget below and a 5-per-fixture one.
SPATIAL_FIXTURE_PROPERTIES = ("fid", "posx", "posy", "posz")

#: Reply axis -> console property, ordered. The order is observable: the FIRST
#: axis that fails to read is the reason the whole fixture is reported absent.
SPATIAL_AXES = (("x", "posx"), ("y", "posy"), ("z", "posz"))

#: Ceiling on property round trips per ``get_spatial_context`` call — 30
#: fixtures at ``SPATIAL_FIXTURE_PROPERTIES`` each. Not a round number picked
#: for looks: one round trip is a MEASURED 66.7 ms (progress.md §E.2.2, where
#: 18 fixtures x 3 axes took 3.60 s), so 120 trips is ~8.0 s — the exact
#: 30-fixture cost design.md §7 tabulated and decision D-1 accepted. A larger
#: rig stops AT the ceiling and says so; the one thing it must never do is
#: return most of a rig as if it were all of it.
SPATIAL_PROPERTY_QUERY_CAP = 120

#: Why a container child was never queried at all. Distinct from a property
#: read that FAILED: the responder declined to establish this child's slot, so
#: there is no path to read a coordinate off (``rig_object``'s degraded
#: name-only entry rests on the same responder guarantee).
_SPATIAL_NO_SLOT_REASON = "container slot not established by the responder"


def _spatial_absence(name: str, reason: str, fid: int | None = None) -> dict[str, object]:
    """One entry in ``unreadable``: a fixture that has NO coordinate here, and why.

    Carries ``fid`` only when the console actually returned one — the same
    slot-is-not-an-identifier rule ``rig_object`` applies to ``no``
    (REQ-SPATIAL-007 / AC-SPATIAL-007). A fixture whose ``fid`` read failed
    comes back name-only, because there is no number anybody observed.
    """
    if fid is None:
        return {"name": name, "reason": reason}
    return {"fid": fid, "name": name, "reason": reason}


# @MX:ANCHOR: [SPEC] the coordinate-invention guard (REQ-SPATIAL-004 /
#   AC-SPATIAL-004, mutation-required).
# @MX:REASON: A fixture reaches ``fixtures`` only when the console answered for
#   fid AND all three axes. Every other outcome returns ``(None, absence)``, so
#   there is no branch on which a missing coordinate can be filled with 0, with
#   a neighbour's value or with a rig average. This matters more here than
#   anywhere else in the SPEC: a fabricated 0 is INDISTINGUISHABLE from the
#   all-(0,0,0) rig that was actually measured (progress.md §E.2.4), so the
#   moment a default is filled in, "this choreography matches your rig" becomes
#   a claim nobody can check — quietly, and on exactly the rigs where it is
#   false. Absence is an ITEM, never a zero.
def spatial_fixture_record(
    name: str, reads: Mapping[str, PropertyRead]
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """One fixture's property reads -> a coordinate record, or the reason it has none.

    Returns ``(record, None)`` or ``(None, absence)`` — never both, and never a
    record with an axis filled in that the console did not answer for.

    Values arrive as the responder's strings (``"19"``, ``"0.0"``, ``"-3.5"``)
    and are parsed here rather than downstream: an unparseable value is a read
    that produced no usable coordinate, which is the same event as a read that
    failed, and both belong in ``unreadable`` with the console's own words.
    Non-finite floats are refused for the same reason — ``float("nan")`` parses
    and would then sort unpredictably, which is the silent-arbitrary-order
    failure AC-SPATIAL-010 forbids.
    """
    fid_read = reads[SPATIAL_FIXTURE_PROPERTIES[0]]
    if not fid_read.ok:
        return None, _spatial_absence(name, fid_read.error or "fid not readable")
    try:
        fid = int(str(fid_read.value).strip())
    except ValueError:
        return None, _spatial_absence(name, f"fid is not a number: {fid_read.value!r}")
    record: dict[str, object] = {"fid": fid, "name": name}
    for axis, prop in SPATIAL_AXES:
        read = reads[prop]
        if not read.ok:
            return None, _spatial_absence(name, read.error or f"{prop} not readable", fid)
        try:
            value = float(str(read.value).strip())
        except ValueError:
            return None, _spatial_absence(name, f"{prop} is not a number: {read.value!r}", fid)
        if not math.isfinite(value):
            return None, _spatial_absence(name, f"{prop} is not finite: {read.value!r}", fid)
        record[axis] = value
    return record, None


def read_spatial_fixtures(
    state_port: StateQueryPort,
    property_port: PropertyQueryPort,
    fixtures_path: str,
    budget: int,
) -> dict[str, object]:
    """Read ``(fid, name, x, y, z)`` for every fixture in the stage patch container.

    READ ONLY: one snapshot of ``fixtures_path`` plus ``SPATIAL_FIXTURE_PROPERTIES``
    property reads per fixture, both through the gate-audited query ports. No
    command line is composed and the execution port is never reached from here.

    Returns ONE OF TWO SHAPES (SPEC-COPILOT-TRUNCATE-001). A complete read
    returns the list under ``fixtures``; an incomplete one returns it under
    ``partial_fixtures``, WITHOUT a ``fixtures`` key, plus ``missing``. Every
    caller must handle both — see the anchor on the return below for why the
    key MOVES instead of a flag being raised beside it.

    Raises whatever the state port raises when the container itself does not
    answer — a rig with no enumerable patch is a failed call, not an empty one.
    """
    payload = state_port.query_state(fixtures_path)
    children = [child for child in (payload.get("children") or []) if isinstance(child, dict)]
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None

    # @MX:ANCHOR: [SPEC] item-drop signal (REQ-SPATIAL-006 / AC-SPATIAL-006,
    #   mutation-required). Read TWO ways on purpose: the responder's own
    #   ``truncated`` flag, and the arithmetic it is derived from
    #   (``node.childCount`` against the children that actually arrived).
    # @MX:REASON: The live rig already crosses this boundary — the measured
    #   container answered childCount 19 with 18 children and truncated:true
    #   (progress.md §E.2.3), and slot 19 read back perfectly well when asked
    #   directly. So the missing fixture is NOT unreadable and NOT absent; it
    #   is unseen, and a reply that did not say so would describe an 18-fixture
    #   rig that does not exist. Keeping the arithmetic alongside the flag means
    #   a responder that ever drops the flag still cannot make the loss silent.
    truncated = bool(payload.get("truncated", False)) or (
        isinstance(child_count, int) and child_count > len(children)
    )

    # @MX:ANCHOR: [SPEC] coverage signal (REQ-GROUPGEN-024 amendment,
    #   2026-08-04 — the discriminate-path guard, not the write-path guard).
    #   ``of`` is the rig's real fixture count (``node.childCount`` when the
    #   console reported one; otherwise the best available fallback is the
    #   ``children`` array length actually returned). ``judged`` is filled in
    #   by the caller once fixture records are parsed — this function only
    #   knows the container-level shape, not which parsed records later fail
    #   coordinate parsing, so the caller (``classify_arrangement_topology``)
    #   completes ``judged`` from ``len(fixtures)`` in its own payload.
    total_fixture_count = child_count if isinstance(child_count, int) else len(children)

    fixtures: list[dict[str, object]] = []
    unreadable: list[dict[str, object]] = []
    roundtrip_capped = False
    per_fixture = len(SPATIAL_FIXTURE_PROPERTIES)
    for child in children:
        # @MX:ANCHOR: [SPEC] round-trip cap signal (REQ-SPATIAL-006). A SEPARATE
        #   field from ``truncated`` — the console shortened its answer, this
        #   code stopped asking, and only the second one is fixable by asking
        #   again (design.md §2.3, acceptance.md §D "값 축약과 항목 탈락은 다른
        #   사건").
        # @MX:REASON: Every read here is a UDP round trip through the gate and
        #   the audit log at a measured 66.7 ms, so an unbounded walk makes this
        #   tool cost scale with the showfile. Stopping is fine; stopping
        #   QUIETLY is the recurring defect this project already paid for once
        #   (the eight vanished looks), because a caller that cannot see the cut
        #   will happily choreograph the fixtures it was never shown.
        if budget < per_fixture:
            roundtrip_capped = True
            break
        name = child.get("name", "")
        if not isinstance(name, str):
            name = str(name)
        slot = child.get("i")
        if not isinstance(slot, int) or isinstance(slot, bool):
            # Never queried, so no budget was spent: there is no address to
            # spend it on. Reported as absent rather than skipped, because a
            # fixture missing from BOTH lists is a fixture nobody mentioned.
            unreadable.append(_spatial_absence(name, _SPATIAL_NO_SLOT_REASON))
            continue
        budget -= per_fixture
        reads = read_properties(
            property_port, f"{fixtures_path}/{slot}", SPATIAL_FIXTURE_PROPERTIES
        )
        record, absence = spatial_fixture_record(name, reads)
        if record is None:
            unreadable.append(absence)  # type: ignore[arg-type]
        else:
            fixtures.append(record)
    # REQ-GROUPGEN-024 amendment coverage signal — "judged" is how many
    # fixtures actually fed a topology judgment, "of" is the rig's real
    # total; "complete" is False whenever EITHER the container listing
    # was truncated OR the per-fixture property walk was budget-capped
    # OR the two counts simply disagree.
    complete = not truncated and not roundtrip_capped and len(fixtures) == total_fixture_count
    coverage = {"judged": len(fixtures), "of": total_fixture_count, "complete": complete}

    # @MX:ANCHOR: [SPEC] the reply-SHAPE divergence (SPEC-COPILOT-TRUNCATE-001
    #   REQ-TRUNCATE-001/002 / AC-TRUNCATE-001/002, mutation-required). ONE
    #   predicate decides it — ``complete``, the coverage formula computed
    #   directly above and nowhere else. No new judgment is introduced: the
    #   truncation test (flag OR arithmetic) and the coverage arithmetic are
    #   untouched (REQ-TRUNCATE-011); only where their result is PLACED
    #   changes.
    # @MX:REASON: A boolean beside the data is ignorable, and WAS ignored. On
    #   the measured 18-of-19 read the model quoted the row analysis and said
    #   nothing about the 19th fixture (SPATIAL progress.md:485-499), because
    #   ``truncated: true`` sits next to a payload that reads perfectly well
    #   without it. An ABSENT key is not ignorable — there is nothing left to
    #   ignore: code written for the complete shape gets a KeyError, and a
    #   prompt written for it finds nothing to quote. So a partial read does
    #   not return a flagged ``fixtures`` list; it returns a DIFFERENT reply.
    if complete:
        return {
            "source": SPATIAL_SOURCE_PATCH3D,
            "path": fixtures_path,
            "fixtures": fixtures,
            "unreadable": unreadable,
            "truncated": truncated,
            "roundtrip_capped": roundtrip_capped,
            "coverage": coverage,
        }
    return {
        "source": SPATIAL_SOURCE_PATCH3D,
        "path": fixtures_path,
        # NOT "fixtures". Every coordinate in this list was read off the
        # console and is true of the fixture it names, but the LIST is not
        # the rig — so it does not get to sit under the key a whole rig uses.
        "partial_fixtures": fixtures,
        "unreadable": unreadable,
        # Still SEPARATE fields (REQ-TRUNCATE-005 / REQ-SPATIAL-006): only
        # ``roundtrip_capped`` is fixable by asking again. What the shape
        # divergence unifies is the BRANCH, never the two signals.
        "truncated": truncated,
        "roundtrip_capped": roundtrip_capped,
        "coverage": coverage,
        # The shortfall as ARITHMETIC, not as an adjective (REQ-TRUNCATE-004):
        # "19 expected, 18 received, 1 unseen", never "incomplete" — a flag
        # does not say HOW MANY, and how many is what the reader needs.
        # ``expected`` is the console's OWN count and stays None when it
        # reported none: the unknown-total rule ``rig_section`` already fixes,
        # and precisely the case where "the count equals what arrived" would
        # be the lie. ``unseen_count`` is expected - received, so it covers a
        # fixture the responder never delivered AND one whose coordinates
        # would not parse; the latter are itemised in ``unreadable``.
        "missing": {
            "expected": child_count if isinstance(child_count, int) else None,
            "received": len(fixtures),
            "unseen_count": (
                max(child_count - len(fixtures), 0) if isinstance(child_count, int) else None
            ),
        },
    }


# -- arrange_fixtures: the coordinate WRITE axis (REQ-SPATIAL-019~024) ---------
#
# @MX:NOTE: [MANUAL] the adopted write channel is the ORDINARY COMMAND LINE.
# @MX:SPEC: SPEC-COPILOT-SPATIAL-001 D-2 (progress.md §E.2.6/§E.2.8). The M0
#   live probe landed a coordinate write on the FIRST candidate, so the
#   responder gained no write verb, `PROTOCOL.md` gained no revision and the
#   gate gained no second surface: this bundle rides `run_commands` ->
#   `gate.screen()` exactly like every other mutating tool. A future reader
#   tempted to "just add a responder verb for speed" should read that section
#   first — the measurement is why the wire stayed closed.

#: The writable position axes: the attribute on a placement, and the console
#: property that stores it. THREE axes, and only these three — v1 writes
#: position and nothing else (REQ-SPATIAL-022 c). Orientation properties are
#: excluded from the write axis entirely: their sign convention and units are
#: unmeasured on this console, and on a physical rig a moving head aimed the
#: wrong way is worse than one standing in the wrong place. Nothing here can
#: emit one — the bundle is built from this tuple and then sealed against the
#: whitelist below.
ARRANGE_AXES: tuple[tuple[str, str], ...] = (("x", "Posx"), ("y", "Posy"), ("z", "Posz"))

#: The same three axes as the responder wants them for a READ. Property lookup
#: is case-insensitive live (progress.md §E.2.1); lower case matches the read
#: tool so both paths ask for one spelling.
ARRANGE_READ_AXES: tuple[str, ...] = ("posx", "posy", "posz")

#: The ONE command form for a coordinate write — LIVE-MEASURED, and the single
#: quotes are not decoration (progress.md §E.2.6a). Of five forms probed on
#: onPC 2.4.2, THREE answered `ok:true` while storing the wrong value or
#: nothing at all:
#:     Set Fixture 11 Posx -3.5     -> stored 3.5   (sign silently dropped), OK
#:     Set Fixture 11 Posx - 3.5    -> stored nothing (silent no-op),        OK
#:     Set Fixture 11 Posx 0-3.5    -> stored 0.0    (wrong value),          OK
#:     Set Fixture 11 Posx '-3.5'   -> stored -3.5                           OK
#: Stage coordinates are negative left of the origin, so the trap sits on this
#: tool's MAIN path, not an edge. Double quotes are not an alternative: the
#: exec request builder rejects the character outright
#: (`server/bridge/protocol.py:109`).
ARRANGE_COMMAND_TEMPLATE = "Set Fixture {fid} {axis} '{value}'"

#: What a line of this tool's bundle may look like — a positive whitelist, so
#: the scope seal below refuses anything else BY CONSTRUCTION rather than by
#: blacklisting the forms someone thought of.
_ARRANGE_COMMAND = re.compile(r"^Set Fixture (?P<fid>\d+) (?P<axis>Pos[xyz]) '(?P<value>[^']+)'$")

#: A coordinate as plain decimal text. Both the values this tool emits and the
#: values it reads back must match: anything else (scientific notation, a
#: quote, a unit suffix) is not something that can be quoted back onto a
#: command line and re-stored, so it fails the backup instead of being guessed
#: at.
_ARRANGE_VALUE = re.compile(r"-?\d+(?:\.\d+)?")

#: Re-query tolerance. The console stores float32: 9.9 is written and reads
#: back as 9.8999996185303 (progress.md §E.2.6a), so STRING equality would
#: report a correct write as a failure. float32's relative epsilon is ~1.2e-7,
#: so 1e-6 clears the drift with an ~8x margin while staying two orders of
#: magnitude below the preset layer's 1e-4 m quantisation — two distinct target
#: coordinates can never alias into one tolerance band, so a WRONG value cannot
#: pass either.
ARRANGE_VERIFY_REL_TOLERANCE = 1e-6
ARRANGE_VERIFY_ABS_TOLERANCE = 1e-6

#: Ceiling on the fid -> slot resolution walk. A fixture's SLOT in the patch
#: container is not its FID (`rig_object` docstring), so every named target's
#: slot is MEASURED — one property read per slot, stopping the moment the last
#: target is located. 120 is design.md §7's 30-fixture arithmetic (~66.7 ms per
#: round trip, ~8 s); a walk that hits the ceiling says so rather than
#: presenting a partial resolution as a complete one.
ARRANGE_SLOT_QUERY_CAP = 120


@dataclass(frozen=True)
class ArrangeBackup:
    """One target's coordinates as they were BEFORE the write.

    ``raw`` keeps the console's own strings, not a re-rendered float: the
    restore bundle re-writes exactly the text the console handed back, so a
    float32 value like ``9.8999996185303`` restores bit-for-bit instead of
    through a decimal round trip that could land one ulp away.
    """

    fid: int
    slot: int
    name: str
    raw: tuple[str, str, str]
    values: tuple[float, float, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "fid": self.fid,
            "slot": self.slot,
            "name": self.name,
            "x": self.values[0],
            "y": self.values[1],
            "z": self.values[2],
        }


def arrange_format_value(value: float) -> str:
    """Render one computed coordinate as command-line text.

    ``repr`` gives the shortest decimal that round-trips, which for a value the
    preset layer already quantised to 1e-4 is at most four decimals. The guard
    is not theatre: a value large enough to render as ``1e+16`` would reach the
    console as a token it does not read as that number.
    """
    text = repr(float(value))
    if not _ARRANGE_VALUE.fullmatch(text):
        raise SpatialPresetError(f"coordinate {value!r} does not render as plain decimal text")
    return text


def arrange_write_commands(placements: Sequence[SpatialPlacement]) -> tuple[str, ...]:
    """The write bundle: one line per axis per placement, x then y then z."""
    return tuple(
        ARRANGE_COMMAND_TEMPLATE.format(
            fid=placement.fid,
            axis=axis_property,
            value=arrange_format_value(getattr(placement, attribute)),
        )
        for placement in placements
        for attribute, axis_property in ARRANGE_AXES
    )


# @MX:ANCHOR: [MANUAL] the restore bundle — the ONLY route back from a
#   coordinate write.
# @MX:REASON: REQ-SPATIAL-020 / AC-SPATIAL-019. `server/safety/backup.py` takes
#   showfile snapshots but has NO restore SEND path (T-B2; `gate.py:283` marks
#   the seat as deliberately unimplemented), so a snapshot cannot undo this
#   tool. Re-writing the original coordinates is the entire recovery story, and
#   it only works if the bundle covers EVERY target — `run_commands` stops on
#   the first failure, so a partial write is the expected failure mode and a
#   restore bundle that only covered the written prefix would strand it.
def arrange_restore_commands(backups: Sequence[ArrangeBackup]) -> tuple[str, ...]:
    """The re-write bundle that puts every backed-up target back where it was."""
    return tuple(
        ARRANGE_COMMAND_TEMPLATE.format(fid=backup.fid, axis=axis_property, value=backup.raw[index])
        for backup in backups
        for index, (_attribute, axis_property) in enumerate(ARRANGE_AXES)
    )


def arrange_scope_violations(commands: Sequence[str], fids: Sequence[int]) -> tuple[str, ...]:
    """Every way ``commands`` exceeds the explicitly named target set.

    A STATIC check (AC-SPATIAL-021): the bundle is text, the target set is a
    list of integers, and the answer needs no console. Run before the bundle is
    handed to ``run_commands`` so a scope escape is refused rather than sent —
    "the builder can only emit position lines" is an argument about code that
    was true right up until someone edited the builder.
    """
    allowed = set(fids)
    violations: list[str] = []
    for command in commands:
        match = _ARRANGE_COMMAND.match(command)
        if match is None:
            violations.append(f"not a position write: {command!r}")
            continue
        if int(match["fid"]) not in allowed:
            violations.append(f"fid {match['fid']} was never named as a target: {command!r}")
    return tuple(violations)


def arrange_values_match(expected: float, actual: float) -> bool:
    """Compare a written coordinate with its read-back NUMERICALLY.

    Never by string equality — see :data:`ARRANGE_VERIFY_REL_TOLERANCE`.
    """
    return abs(actual - expected) <= max(
        ARRANGE_VERIFY_ABS_TOLERANCE, ARRANGE_VERIFY_REL_TOLERANCE * abs(expected)
    )


def _error_result(call: ToolCall, message: str) -> ToolExecution:
    return ToolExecution(
        result=ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": message}, ensure_ascii=False),
            is_error=True,
        )
    )


def _fx_error_result(call: ToolCall, message: str, **extra: object) -> ToolExecution:
    """``_error_result`` plus the machine-readable facts behind the refusal.

    The fx refusals are the ones a model can act on — which groups DO exist, why
    the sequence pool could not be measured — and a reason code the caller can
    branch on beats re-parsing the message text.
    """
    return ToolExecution(
        result=ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": message, **extra}, ensure_ascii=False),
            is_error=True,
        )
    )


def _positive_int(value: object) -> int | None:
    """``value`` as a positive console number, or ``None``.

    ``bool`` is excluded explicitly: it is an ``int`` in Python, so ``True``
    would otherwise address ``Group 1`` on a rig that may well have one.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _addressable_groups(groups_section: object) -> list[int]:
    """The group numbers this rig listed AND numbered, ascending.

    A name-only entry is dropped rather than counted from its position: the
    responder omits ``i`` precisely when it could not establish the slot, and
    turning that into a number is the hallucinated-``Group 3`` defect the rig
    context exists to prevent.
    """
    objects = groups_section.get("objects") if isinstance(groups_section, Mapping) else None
    if not isinstance(objects, list):
        return []
    return sorted(
        {
            entry["no"]
            for entry in objects
            if isinstance(entry, Mapping) and isinstance(entry.get("no"), int)
        }
    )


class ToolRegistry:
    """The closed set of Phase 1 tools with neutral definitions + dispatch."""

    def __init__(self, definitions: tuple[ToolDefinition, ...], handlers: dict[str, _Handler]):
        self._definitions = definitions
        self._handlers = handlers

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return self._definitions

    def dispatch(self, call: ToolCall, context: ExecutionContext | None = None) -> ToolExecution:
        context = context if context is not None else _EMPTY_CONTEXT
        handler = self._handlers.get(call.name)
        if handler is None:
            return _error_result(call, f"unknown tool: {call.name!r}")
        return handler(call, context)


def build_toolset(
    *,
    execution_port: CommandExecutionPort,
    state_port: StateQueryPort,
    rig_paths: dict[str, str] | None = None,
    rig_drilldown: tuple[str, ...] | None = None,
    bundle_gate: BundleGate | None = None,
    deploy_pipeline: DeployPipelinePort | None = None,
    look_library: LookLibrary | None = None,
    fx_library: FxLibrary | None = None,
    scene_library: SceneLibrary | None = None,
    property_port: PropertyQueryPort | None = None,
    preshow_liveness_port: PreshowLivenessPort | None = None,
    preshow_receive_port: int | None = None,
    preshow_osc_slot: int | None = None,
    group_approval_port: ApprovalPort | None = None,
) -> ToolRegistry:
    """Build the tool registry wired to the given ports (REQ-MVP-005).

    When ``bundle_gate`` is provided (M4 production wiring), every
    run_commands bundle is screened as a WHOLE before any per-command
    execution starts (REQ-MVP-011 pipeline + REQ-MVP-015 all-or-nothing);
    a non-cleared decision returns the block/hold reasons as an error tool
    result, feeding the self-correction loop (REQ-MVP-012).

    ``look_library`` is optional: production wiring passes nothing and the
    built-in library is read from disk on the first ``find_looks`` call, so a
    toolset that never looks up a look pays no file read. ``fx_library`` is the
    same arrangement for the fx layer, read on the first ``find_fx`` or
    ``instantiate_fx`` call, and ``scene_library`` for the scene layer, read on
    the first ``find_scene`` or ``compile_scene`` call.

    ``property_port`` is the pre-check's extra read (REQ-PRECHK-019). When it is
    omitted it is adopted from ``state_port`` if that object also implements
    ``query_property`` — the gate's port object implements both, so production
    wiring needs no change and gains the capability, while a narrow test double
    stays narrow and ``precheck_patch`` says the capability is missing instead of
    reporting an empty rig.

    ``preshow_liveness_port`` (SPEC-COPILOT-PRESHOW-001 T-G) wires an
    already-open console link's liveness probe into ``preshow_check`` so the
    OSC round-trip / receive-port checks actually run instead of always
    reporting ``skip``. Omitted by default (unchanged backward-compatible
    behavior for every existing caller) — this module still imports nothing
    from ``server.bridge``; ``preshow_liveness_port`` is a structural
    duck-typed object the caller constructs (e.g. adapting
    ``server.safety.gate.SafetyGate.heartbeat``), never a bridge type.
    ``preshow_receive_port`` is the numeric port that link already owns, used
    for reporting and feedback-port-drift comparison.

    ``preshow_osc_slot`` (SPEC-COPILOT-PRESHOW-001 T-G3) is the site's real
    ``osc_slot`` setting (``server.deploy.settings.UserSettings.osc_slot``).
    Omitted by default (unchanged backward-compatible behavior): the
    ``osc_slot_send_row`` check then falls back to the hardcoded default AND
    discloses that fallback explicitly, rather than naming an unconfirmed
    value as if it were the confirmed site setting.

    ``group_approval_port`` (SPEC-COPILOT-GROUPGEN-001 §7 — the tool-layer
    approval seam) is the ONLY route ``create_arrangement_groups`` has to a
    console send: it reuses ``server.safety.approval.ApprovalPort`` (the same
    human-approval channel the M4 gate wires for risky commands), because
    ``Store Group``/``Label Group`` classify as ``safe`` (design.md §7.3,
    ``server/safety/**`` stays byte-diff 0) and so never reach the gate's own
    approval stage on their own. Omitted (the default), it falls back to
    ``DenyAllApprovalPort`` — fail-closed, matching the port's own module
    docstring: with no approval channel wired, nothing is ever sent.
    """
    rig_paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)
    group_approval = group_approval_port or DenyAllApprovalPort()
    drilldown = frozenset(rig_drilldown if rig_drilldown is not None else DEFAULT_RIG_DRILLDOWN)
    looks = look_library
    fx_lib = fx_library
    scene_lib = scene_library
    if property_port is None and hasattr(state_port, "query_property"):
        property_port = state_port

    # -- run_commands (REQ-MVP-001 upstream, REQ-MVP-009/033 semantics) --------

    def run_commands(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        commands = call.arguments.get("commands")
        if (
            not isinstance(commands, list)
            or not commands
            or not all(isinstance(c, str) and c.strip() for c in commands)
        ):
            return _error_result(call, "'commands' must be a non-empty list of command lines")
        if bundle_gate is not None:
            decision = bundle_gate.screen(commands)
            if not decision.cleared:
                gate_outcomes = tuple(
                    CommandOutcome(command=d.command, status=d.status, detail="; ".join(d.reasons))
                    for d in decision.commands
                )
                content = json.dumps(
                    {
                        "all_ok": False,
                        "gate_status": decision.status,
                        "notice": decision.notice,
                        "commands": [
                            {
                                "command": d.command,
                                "status": d.status,
                                "reasons": list(d.reasons),
                            }
                            for d in decision.commands
                        ],
                    },
                    ensure_ascii=False,
                )
                return ToolExecution(
                    result=ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=content,
                        is_error=True,
                    ),
                    command_outcomes=gate_outcomes,
                )
        outcomes: list[CommandOutcome] = []
        failed = False
        # MEDIUM backlog item (M6c 종합, tools.py:145): ``context.executed_ok``
        # is a frozenset seeded from a PRIOR tool call — it is never updated
        # as commands succeed WITHIN this loop. A local, mutable copy (seeded
        # from the same starting set) tracks successes as they happen in THIS
        # call, so an in-bundle duplicate command (the same string appearing
        # twice in one ``commands`` list) is correctly recognized as
        # already-executed on its second occurrence instead of being
        # re-executed and duplicating its console side effect.
        already_executed = set(context.executed_ok)
        for command in commands:
            if failed:
                # Stop-on-first-failure: remaining commands are never executed.
                outcomes.append(
                    CommandOutcome(
                        command=command,
                        status="not_executed",
                        detail="not executed (stopped after an earlier failure)",
                    )
                )
            elif command in already_executed and not _is_programmer_state(command):
                # Never re-execute a command that already succeeded — either
                # in a prior tool call (context.executed_ok) or earlier in
                # THIS bundle — re-execution duplicates its console effect.
                # Programmer-state commands are exempt: they duplicate no
                # artifact, and their repeats are MOMENTS, not repetitions
                # (_is_programmer_state above).
                outcomes.append(
                    CommandOutcome(
                        command=command,
                        status="skipped_already_executed",
                        detail="already executed successfully in this instruction",
                    )
                )
            else:
                result = execution_port.execute(command)
                if result.ok:
                    already_executed.add(command)
                    outcomes.append(
                        CommandOutcome(command=command, status="executed_ok", detail=result.detail)
                    )
                else:
                    outcomes.append(
                        CommandOutcome(command=command, status="failed", detail=result.detail)
                    )
                    failed = True
        content = json.dumps(
            {
                "all_ok": not failed,
                "commands": [
                    {"command": o.command, "status": o.status, "detail": o.detail} for o in outcomes
                ],
            },
            ensure_ascii=False,
        )
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id, name=call.name, content=content, is_error=failed
            ),
            command_outcomes=tuple(outcomes),
        )

    # -- query_state (REQ-MVP-003 via the M2 protocol path) --------------------

    def query_state(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        path = call.arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            return _error_result(call, "'path' must be a non-empty object-tree path")
        try:
            payload = state_port.query_state(path)
        except Exception as exc:
            return _error_result(call, f"state query failed for {path!r}: {exc}")
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
            )
        )

    # -- deploy_plugin (M7 — REQ-MVP-019 pipeline: compile + scan + review) ------

    def deploy_plugin(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        if deploy_pipeline is None:
            # Unwired session: deployment stays unavailable BY DESIGN and
            # never sends anything toward the console (deny-by-default).
            return _error_result(
                call,
                "deploy_plugin is not wired in this session: plugin deployment "
                "requires the pcall compile check and the human review gate",
            )
        name = call.arguments.get("name")
        lua_source = call.arguments.get("lua_source")
        if not isinstance(name, str) or not name.strip():
            return _error_result(call, "'name' must be a non-empty plugin name string")
        if not isinstance(lua_source, str) or not lua_source.strip():
            return _error_result(call, "'lua_source' must be non-empty Lua 5.4 source code")
        outcome = deploy_pipeline.deploy(name, lua_source)
        status = _DEPLOY_OUTCOME_STATUS.get(outcome.status, "failed")
        command_label = f'deploy_plugin "{name}"'
        deployed = outcome.status == "deployed"
        content: dict[str, object] = {
            "deployed": deployed,
            "plugin": name,
            "status": outcome.status,
            "destructive": outcome.destructive,
            "detail": outcome.detail,
        }
        if not deployed:
            content["error"] = outcome.detail
        if outcome.compile_error:
            content["compile_error"] = outcome.compile_error
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(content, ensure_ascii=False),
                is_error=not deployed,
            ),
            command_outcomes=(
                CommandOutcome(command=command_label, status=status, detail=outcome.detail),
            ),
        )

    # -- get_rig_context (REQ-MVP-037 — showfile-based basic summary) -----------

    def get_rig_context(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        summary, resolved, failed = collect_rig_sections(
            state_port, rig_paths, drilldown, RIG_DRILLDOWN_QUERY_CAP
        )
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(summary, ensure_ascii=False),
                # Partial vocabulary is still usable; returning NOTHING is a
                # failed call, not a quiet success.
                is_error=bool(failed) and resolved == 0,
            )
        )

    # -- find_looks (REQ-LOOKLIB-015/016/017 — lookup only, sends nothing) -----

    def find_looks(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        query = call.arguments.get("query")
        if not isinstance(query, str):
            return _error_result(call, "'query' must be a string — the operator's own words")
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                # A broken library is a structured failure, never a silent
                # empty result that would read as "no look matches".
                return _error_result(call, f"look library unavailable: {error}")
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(match_looks(query, looks).to_dict(), ensure_ascii=False),
                # A miss is an ANSWER (REQ-LOOKLIB-017), not a tool failure:
                # an is_error payload feeds the self-correction loop and would
                # invite a retry that can only miss again.
                is_error=False,
            )
        )

    # -- instantiate_look (REQ-LOOKLIB-010/013/019 — the look layer's ONE route) -
    #
    # @MX:ANCHOR: [AUTO] the only model-reachable entry to the instantiation
    #   chain (find_looks -> role resolution -> bundle -> gate.screen()).
    # @MX:REASON: REQ-LOOKLIB-010/019. This handler is a CALLER of run_commands,
    #   never a second execution surface: it re-enters the local run_commands
    #   closure above, so the bundle inherits that path's gate screening,
    #   execution preview, dedupe and audit log without any of them being
    #   duplicated for looks. Reaching execution_port directly from here would
    #   be the second path the SPEC forbids, and it would be invisible to the
    #   gate. The M4 layer was correct and had NO caller for exactly one
    #   milestone; that is what this tool repairs, so do not un-register it
    #   without giving the chain another model-reachable door.

    def instantiate_look(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        look_id = call.arguments.get("look_id")
        if not isinstance(look_id, str) or not look_id.strip():
            return _error_result(
                call, "'look_id' must be the look_id string returned by find_looks"
            )
        shape = call.arguments.get("capture_shape", CAPTURE_SHARED)
        if shape not in CAPTURE_SHAPES:
            # Never silently corrected to the default: a shape the model chose
            # deliberately and got wrong is worth one visible failure.
            return _error_result(
                call, f"'capture_shape' must be one of {list(CAPTURE_SHAPES)}, not {shape!r}"
            )
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        try:
            look = looks.by_id(look_id.strip())
        except KeyError:
            # An id this library does not hold is a correctable mistake, so it
            # IS an error result — unlike a find_looks miss, a retry with the
            # right id succeeds.
            return _error_result(
                call,
                f"unknown look_id {look_id!r} — call find_looks and pass back the "
                f"look_id from one of its matches",
            )
        missing = [section for section in LOOK_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a look cannot be "
                f"bound to this rig without them",
            )
        # The rig is READ here, never accepted as an argument: a model retyping
        # a rig section can paraphrase a name, drop the truncation signal or
        # supply a number the console never gave. Every number this bundle puts
        # on the command line has to come from the console itself (AP-16).
        sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in LOOK_RIG_SECTIONS},
            drilldown | _LOOK_DRILLDOWN,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            # A section that never arrived is NOT a rig that answered "no such
            # group". Reporting the roles as unmapped here would state a fact
            # about a rig nobody observed.
            content = json.dumps(
                {
                    "error": (
                        "the rig sections a look is bound against did not arrive: "
                        + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items())
                    ),
                    "rig_unavailable": unavailable,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            plan = build_instantiation(
                look,
                resolution=resolve_roles(sections["groups"]),  # type: ignore[arg-type]
                pools=resolve_pools(sections["preset_pools"]),  # type: ignore[arg-type]
                shape=shape,
            )
        except LookInstantiationError as error:
            return _error_result(call, f"look {look.look_id!r} cannot be instantiated: {error}")
        report = plan.to_dict()
        if not plan.commands:
            # The rig addressed none of this look's roles. An empty bundle is
            # the honest output, and it is an ANSWER rather than a failure: a
            # retry cannot bind a role this rig does not have.
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps({"executed": False, "report": report}, ensure_ascii=False),
                    is_error=False,
                )
            )
        execution = run_commands(
            ToolCall(id=call.id, name="run_commands", arguments={"commands": list(plan.commands)}),
            context,
        )
        payload = json.loads(execution.result.content)
        payload["executed"] = not execution.result.is_error
        payload["report"] = report
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=execution.result.is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- prepare_busking (REQ-BUSKWIZ-011/012/014/019/020 — 장르 팔레트 1왕복) ---
    #
    # @MX:ANCHOR: [AUTO] the busking wizard's ONE model-reachable entry.
    # @MX:REASON: REQ-BUSKWIZ-011/012. Like instantiate_look this handler is a
    #   CALLER of run_commands, never a second execution surface: the genre
    #   bundle inherits gate screening, LiveLock, dedupe and the audit log from
    #   that one path. Reaching execution_port from here would be invisible to
    #   the gate. The rig is READ here for the same reason instantiate_look
    #   reads it (:735-738) — a model retyping a section can paraphrase a name
    #   or supply a number the console never gave.

    def prepare_busking(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        genre = call.arguments.get("genre")
        if not isinstance(genre, str) or not genre.strip():
            return _error_result(
                call, "'genre' must be the operator's own word for the genre (e.g. '록', 'EDM')"
            )
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        selection = select_genre(looks, genre)
        if selection.genre is None:
            # A genre this library does not hold is a CORRECTABLE mistake: the
            # candidate list makes the retry succeed. Promoting the query to the
            # nearest genre instead would leave a palette the operator never
            # asked for in their showfile.
            content = json.dumps(
                {
                    "error": f"unknown genre {genre!r}",
                    "reason": selection.reason,
                    "candidates": list(selection.candidates),
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        missing = [section for section in LOOK_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a busking palette "
                f"cannot be built without them",
            )
        sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in LOOK_RIG_SECTIONS},
            drilldown | _LOOK_DRILLDOWN,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            # A section that never arrived is NOT a rig that answered "no such
            # group" — the same split instantiate_look makes at :750.
            content = json.dumps(
                {
                    "error": (
                        "the rig sections a busking palette is built against did not "
                        "arrive: "
                        + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items())
                    ),
                    "rig_unavailable": unavailable,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            bundle = build_genre_bundle(
                selection.genre,
                selection.looks,
                resolution=resolve_roles(sections["groups"]),  # type: ignore[arg-type]
                pools=resolve_pools(sections["preset_pools"]),  # type: ignore[arg-type]
            )
        except LookInstantiationError as error:
            return _error_result(call, f"genre {selection.genre!r} cannot be instantiated: {error}")
        if not bundle.commands:
            # The rig addressed none of this genre's roles. Storing nothing is
            # an ANSWER, not a failure: a retry cannot bind roles this rig does
            # not have. The report still says which look died and why.
            report = build_report(bundle)
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "executed": False,
                            "genre": bundle.genre,
                            "report": report.to_dict(),
                            "summary_ko": to_korean(report),
                        },
                        ensure_ascii=False,
                    ),
                    is_error=False,
                )
            )
        execution = run_commands(
            ToolCall(
                id=call.id, name="run_commands", arguments={"commands": list(bundle.commands)}
            ),
            context,
        )
        payload = json.loads(execution.result.content)
        is_error = execution.result.is_error
        if payload.get("gate_status") == _LOCKED:
            # LiveLock demotion is an ANSWER (REQ-BUSKWIZ-014): the proposal IS
            # the deliverable. is_error=True would feed the self-correction loop
            # and send the model back into the same lock.
            is_error = False
        report = build_report(bundle, execution.command_outcomes)
        payload["executed"] = not execution.result.is_error
        payload["genre"] = bundle.genre
        payload["report"] = report.to_dict()
        payload["summary_ko"] = to_korean(report)
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- prepare_songcue (REQ-SONGCUE-018/019 — song sections to one cue list) -
    #
    # @MX:ANCHOR: [AUTO] the song-cue generator's ONE model-reachable entry.
    # @MX:REASON: REQ-SONGCUE-018/019. Like prepare_busking this handler is a
    #   CALLER of run_commands, never a second execution surface: it reads the
    #   rig itself, builds the sequence/cue/timing bundle, and re-enters the
    #   local run_commands closure so gate.screen(), LiveLock demotion, dedupe
    #   and audit stay owned by the same path.

    def prepare_songcue(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        song_title = call.arguments.get("song_title")
        if not isinstance(song_title, str) or not song_title.strip():
            return _error_result(call, "'song_title' must be a non-empty song title string")
        genre = call.arguments.get("genre")
        if not isinstance(genre, str) or not genre.strip():
            return _error_result(call, "'genre' must be the operator's own word for the genre")
        timecode_number = call.arguments.get("timecode_number")
        if (
            isinstance(timecode_number, bool)
            or not isinstance(timecode_number, int)
            or timecode_number < 1
        ):
            return _error_result(call, "'timecode_number' must be a positive integer")
        raw_sections = call.arguments.get("sections")
        if not isinstance(raw_sections, list | tuple) or not raw_sections:
            return _error_result(call, "'sections' must be a non-empty array of song sections")
        raw_explicit = call.arguments.get("explicit_dynamics")
        explicit_dynamics: dict[int, int] | None = None
        if raw_explicit is not None:
            if not isinstance(raw_explicit, Mapping):
                return _error_result(
                    call,
                    "'explicit_dynamics' must map zero-based section indexes to dynamics 1..5",
                )
            explicit_dynamics = {}
            for key, value in raw_explicit.items():
                if isinstance(value, bool) or not isinstance(value, int):
                    return _error_result(call, "'explicit_dynamics' values must be integers")
                try:
                    explicit_dynamics[int(key)] = value
                except (TypeError, ValueError):
                    return _error_result(
                        call, "'explicit_dynamics' keys must be zero-based section indexes"
                    )
        try:
            sections = parse_sections(raw_sections)
        except SectionTimeError as error:
            content = json.dumps(
                {
                    "error": "song sections are not strictly increasing",
                    "reason": error.reason,
                    "index": error.index,
                    "previous_start_ms": error.previous_start_ms,
                    "start_ms": error.start_ms,
                    "sections": [
                        {"index": section.index, "name": section.name, "start_ms": section.start_ms}
                        for section in error.sections
                    ],
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        except ValueError as error:
            return _error_result(call, f"song sections cannot be parsed: {error}")
        for index, raw_section in enumerate(raw_sections):
            if not isinstance(raw_section, Mapping) or "dynamics" not in raw_section:
                continue
            value = raw_section["dynamics"]
            if isinstance(value, bool) or not isinstance(value, int):
                return _error_result(call, "'sections[].dynamics' values must be integers")
            if explicit_dynamics is None:
                explicit_dynamics = {}
            explicit_dynamics[index] = value
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        genre_selection = select_genre(looks, genre)
        if genre_selection.genre is None:
            content = json.dumps(
                {
                    "error": f"unknown genre {genre!r}",
                    "reason": genre_selection.reason,
                    "candidates": list(genre_selection.candidates),
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            selections = map_sections_to_looks(
                sections,
                looks,
                genre_selection.genre,
                explicit_dynamics=explicit_dynamics,
            )
        except ValueError as error:
            return _error_result(call, f"song sections cannot be mapped: {error}")
        unknown_sections = [
            {"index": selection.section.index, "name": selection.section.name}
            for selection in selections
            if selection.reason == EXPLICIT_DYNAMICS_REQUIRED
        ]
        if unknown_sections:
            content = json.dumps(
                {
                    "error": "unknown section names need explicit dynamics",
                    "reason": EXPLICIT_DYNAMICS_REQUIRED,
                    "unknown_sections": unknown_sections,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        missing = [section for section in SONGCUE_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a song cue list "
                f"cannot be built without them",
            )
        rig_sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in SONGCUE_RIG_SECTIONS},
            drilldown,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in rig_sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            content = json.dumps(
                {
                    "error": (
                        "the rig sections a song cue list is built against did not "
                        "arrive: "
                        + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items())
                    ),
                    "rig_unavailable": unavailable,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            bundle = build_songcue_bundle(
                song_title,
                selections,
                sequences_section=rig_sections["sequences"],  # type: ignore[arg-type]
                groups_section=rig_sections["groups"],  # type: ignore[arg-type]
            )
            timing = build_songcue_timing(bundle, timecode_number=timecode_number)
        except (SequenceNumberError, SongCueBundleError, ValueError) as error:
            return _error_result(call, f"song cue list cannot be built: {error}")
        if not bundle.commands:
            report = build_songcue_report(bundle)
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "executed": False,
                            "song_title": bundle.song_title,
                            "sequence": bundle.sequence_number,
                            "report": report.to_dict(),
                            "summary_ko": report.to_korean(),
                            "timing": {
                                "commands": [],
                                "timecode_commands": [],
                                "auto_advance_commands": [],
                                "skipped_axes": [],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    is_error=False,
                )
            )
        command_bundle = bundle.commands + timing.commands
        execution = run_commands(
            ToolCall(id=call.id, name="run_commands", arguments={"commands": list(command_bundle)}),
            context,
        )
        payload = json.loads(execution.result.content)
        is_error = execution.result.is_error
        if payload.get("gate_status") == _LOCKED:
            is_error = False
        requery_payload = None
        if not execution.result.is_error:
            try:
                requery_payload = state_port.query_state(
                    f"{rig_paths['sequences']}/{bundle.sequence_number}"
                )
            except Exception as error:
                payload["requery_error"] = str(error)
        report = build_songcue_report(
            bundle, execution.command_outcomes, requery_payload=requery_payload
        )
        payload["executed"] = not execution.result.is_error
        payload["song_title"] = bundle.song_title
        payload["sequence"] = bundle.sequence_number
        payload["report"] = report.to_dict()
        payload["summary_ko"] = report.to_korean()
        payload["timing"] = {
            "commands": list(timing.commands),
            "timecode_commands": list(timing.timecode_commands),
            "auto_advance_commands": list(timing.auto_advance_commands),
            "skipped_axes": [
                {"axis": skipped.axis, "reason": skipped.reason} for skipped in timing.skipped_axes
            ],
        }
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- precheck_patch (REQ-PRECHK-018 — the pre-show rig check) --------------
    #
    # @MX:ANCHOR: [AUTO] the pre-check's ONE model-reachable entry.
    # @MX:REASON: REQ-PRECHK-018. Like prepare_busking and prepare_songcue this
    #   handler READS the rig and, when it has to speak, calls ``run_commands``
    #   above rather than ``execution_port`` — the gate screens the whole macro
    #   bundle before a single line reaches the console.

    class _InventoryPort:
        """The two reads the inventory needs, joined from the wired ports."""

        def __init__(self, state: StateQueryPort, prop: PropertyQueryPort) -> None:
            self._state = state
            self._prop = prop

        def query_state(self, path: str) -> dict:
            return self._state.query_state(path)

        def query_property(self, path: str, property_name: str) -> dict:
            return self._prop.query_property(path, property_name)

    class _MacroPoolIncomplete(RuntimeError):
        """The macro pool enumeration was short, so no slot can be called free."""

    def _free_macro_slot(payload: object) -> int:
        """Lowest positive slot the macro pool does not already occupy.

        The slot is DERIVED, never taken as a parameter: ``AC-PRECHK-014`` ③ bans
        rig identifiers from the schema, and slot 1 holds the responder's own
        macro on the measured rig, so a default would make overwriting it the
        quiet outcome.

        The occupied set is trusted ONLY when the enumeration is complete.
        ``node.childCount`` is the true total while ``children`` may be truncated
        (``console/lua/copilot_responder.lua:634-639`` — the path this SPEC
        demonstrated live at nineteen fixtures). A short read makes the occupied
        set a SUBSET, so the "lowest free" answer can name an occupied slot and
        the following ``Store Macro <n>`` would overwrite the operator's macro.
        That is the same count-vs-flag discipline ``REQ-PRECHK-004`` makes a
        requirement, applied to the one path in this SPEC that writes.
        """
        if not isinstance(payload, dict):
            raise _MacroPoolIncomplete("macro pool payload is not a mapping")
        children = [c for c in (payload.get("children") or ()) if isinstance(c, dict)]
        node = payload.get("node")
        child_count = node.get("childCount") if isinstance(node, dict) else None
        if not isinstance(child_count, int) or isinstance(child_count, bool):
            raise _MacroPoolIncomplete("macro pool reported no childCount")
        if child_count > len(children):
            raise _MacroPoolIncomplete(
                f"macro pool enumeration is short: childCount {child_count} "
                f"but {len(children)} children returned"
            )
        if child_count == 0:
            # A wholesale enumeration failure arrives as this exact payload:
            # ``M.safe_children`` returns an empty table when BOTH ``Children()``
            # and ``Count()`` pcall-fail, and ``childCount`` is derived from that
            # same empty read -- so "the pool is empty" and "the pool did not
            # read" are one payload with ``ok=true`` and ``truncated=false``.
            # Trusting it makes the occupied set empty, "lowest free" answers 1,
            # and the following ``Store Macro 1`` overwrites the responder's own
            # ``Copilot Go`` macro -- the plugin this whole system talks through.
            # Refusing costs a rig with a genuinely empty pool one slot; adopting
            # it costs the console link.
            raise _MacroPoolIncomplete(
                "macro pool reported zero children — a failed enumeration and an "
                "empty pool are indistinguishable here"
            )
        taken = {c["i"] for c in children if isinstance(c.get("i"), int)}
        if len(taken) != len(children):
            raise _MacroPoolIncomplete("macro pool children did not all carry a slot index")
        slot = 1
        while slot in taken:
            slot += 1
        return slot

    def _requery_macro_line(macro: MacroResult, prop: PropertyQueryPort) -> dict[str, object]:
        """Read ONE stored macro line back off the console.

        A command receipt is not evidence of effect. This SPEC measured both
        halves of that live: a console answering ``OK`` for a command it had
        REJECTED, and a console answering ``OK`` while writing somewhere other
        than the named target (``Executor 201`` landed on page 1 index 101, not
        page 2). The same session established this very macro grammar by
        requerying ``DataPool/Macros/91/1 Command`` and reading back
        ``On Group 11`` — the M0 GO record. So the stored line is READ BACK
        rather than inferred from ``all_ok``.

        ONE line, not all of them: a full sweep costs two extra audited property
        reads per group, and the failures this guards against — nothing stored,
        or stored somewhere else — are already visible on the first line. Line 1
        is also the exact line the M0 measurement covered.

        A requery that does not answer is reported AS an unanswered requery.
        It is NEVER rendered as "the macro is not there", and it never rewrites
        the authoring result: substituting absence for a failed read is the
        defect class this SPEC has now fixed on three separate read paths.

        ``lines[0]`` is safe by construction, not by luck: the caller only reaches
        here with a non-empty ``commands``, which the authoring module emits only
        after appending a line per target, and the handler's own zero-target
        branch refuses a result that carries commands.
        """
        line = macro.lines[0]
        path = f"{rig_paths['macros']}/{macro.macro_slot}/{line.number}"
        read = read_properties(prop, path, (_MACRO_COMMAND_PROPERTY,))[_MACRO_COMMAND_PROPERTY]
        requery: dict[str, object] = {
            "path": path,
            "property": _MACRO_COMMAND_PROPERTY,
            "line": line.number,
            "expected": line.payload,
            "read": read.ok,
            "value": read.value,
            # null, NOT false, when the requery did not answer: false would say
            # the console stored the wrong text, which is a claim about a value
            # nobody read.
            "matches": (read.value == line.payload) if read.ok else None,
            "error": read.error,
        }
        if not read.ok:
            requery["summary_ko"] = (
                f"재조회 실패 — 매크로 {macro.macro_slot}.{line.number}의 저장 효과를 "
                f"확인하지 못했다. 매크로가 없다는 뜻은 아니다(저작·전송은 별도로 "
                f"보고된다): {read.error}"
            )
        elif requery["matches"]:
            requery["summary_ko"] = (
                f"재조회 확인 — 매크로 {macro.macro_slot}.{line.number}에 "
                f"'{line.payload}'가 저장되어 있다"
            )
        else:
            # Deliberately NOT promoted to is_error: exact string equality on a
            # requeried `Command` was measured on ONE line of ONE rig (M0), so a
            # console that normalises the text it stores would make every real
            # pre-check an error — the false-alarm version of the same defect.
            # The observation is reported in full instead, and the human who has
            # to look at the lights anyway (REQ-PRECHK-014) can judge it.
            requery["summary_ko"] = (
                f"재조회 불일치 — 매크로 {macro.macro_slot}.{line.number}에 저작한 값은 "
                f"'{line.payload}'인데 콘솔이 돌려준 값은 '{read.value}'다. "
                f"콘솔에서 직접 확인하라"
            )
        return requery

    def precheck_patch(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        create_macro = call.arguments.get("create_macro", False)
        if not isinstance(create_macro, bool):
            return _error_result(call, "'create_macro' must be a boolean")
        if property_port is None:
            # Never answer "zero fixtures" when the capability is missing: an
            # empty report reads as a clean rig (REQ-PRECHK-010).
            return _error_result(
                call,
                "property reads are not wired — build_toolset needs property_port "
                "(or a state_port that also implements query_property)",
            )
        try:
            inventory = read_inventory(_InventoryPort(state_port, property_port))
        except InventoryReadError as error:
            return _error_result(call, f"fixture inventory unreadable: {error}")
        # ASSUMPTION-27 is NEGATIVE (progress.md §E.2 M0): the EXACT-width
        # range-overlap check stays off and says so in skipped_checks. Address
        # duplicates still run, and so does the weaker axis below: an upper bound
        # on the footprint needs no fixture-to-mode linkage, so it survives the
        # refutation that killed the exact widths.
        missing_sections = [
            section for section in PRECHK_FOOTPRINT_SECTIONS if section not in rig_paths
        ]
        if missing_sections:
            # Named, not blamed on a read: nothing was queried, so nothing may be
            # called unreadable. The report survives; only the bound is lost.
            walk = WalkOutcome(
                complete=False,
                failure=REASON_UNRESOLVED,
                failure_detail=(
                    f"리그 컨텍스트에 {missing_sections} 경로가 설정되지 않아 점유폭 상계를 "
                    "계산하지 않았다 — 조회를 시도하지 않았으므로 판독 실패가 아니다."
                ),
            )
        else:
            walk = walk_mode_widths(
                state_port,
                root=rig_paths["fixture_types"],
                budget=PRECHK_FOOTPRINT_QUERY_CAP,
                # The fixture inventory above already answered on this console, so
                # a walk that cannot read its own root is a WRONG PATH for this
                # showfile rather than a dead console. The walk cannot see that
                # from inside: production raises one exception type for both.
                sibling_answered=True,
            )
        evaluation = evaluate_patch(inventory, walk=walk)
        macro = None
        if create_macro:
            # Named up front, exactly like the three sibling handlers: indexing
            # `rig_paths` inside the try blocks below made a MISSING section
            # surface as `group pool unreadable: 'groups'`, blaming a pool that
            # was never queried for a wiring mistake (independent PR #7 review,
            # P3). The two causes stay separate here for the same reason the
            # rig-context module keeps `path_not_resolved` apart from
            # `console_unreachable`.
            missing = [section for section in PRECHK_RIG_SECTIONS if section not in rig_paths]
            if missing:
                return _error_result(
                    call,
                    f"rig context has no path configured for {missing} — the response-"
                    f"check macro cannot be built without them",
                )
            try:
                groups_payload = state_port.query_state(rig_paths["groups"])
            except Exception as error:
                # A console that did not answer is NOT a rig without groups.
                # Substituting an empty pool would put "리그에 그룹이 없어…" in front
                # of the user about a rig whose group pool we never read — the same
                # class of defect M8 caught in the completeness label. The sibling
                # read below treats its own failure this way, and `acceptance.md`
                # §D fixes it: 조회 실패 → is_error=True (정정 가능).
                return _error_result(call, f"group pool unreadable: {error}")
            try:
                pool = read_group_pool(groups_payload)
            except Exception as error:
                return _error_result(call, f"group pool unreadable: {error}")
            if pool.targets:
                try:
                    slot = _free_macro_slot(state_port.query_state(rig_paths["macros"]))
                except Exception as error:
                    # Never fall back to slot 1 — it holds the responder's own
                    # macro on the measured rig, so a fallback would overwrite it
                    # quietly.
                    return _error_result(call, f"macro pool unreadable, no free slot: {error}")
                macro = build_response_check_macro(pool, MacroPolicy.available(slot))
            else:
                # Zero targets: nothing will be stored, so the macro pool is not
                # read at all. Deriving a slot first cost one audited OSC send on
                # a pool no command would name, and — worse — let its failure
                # turn a rig with no groups (an ANSWER under `AC-PRECHK-014` ④)
                # into an error that DISCARDS the fixture inventory this tool
                # exists to produce (independent PR #7 review, P2).
                macro = build_response_check_macro(
                    pool, MacroPolicy.available(_UNSPOKEN_MACRO_SLOT)
                )
                if macro.created or macro.commands:
                    # Unreachable while `build_response_check_macro` answers the
                    # zero-target cases before it reads the slot. If that ever
                    # changes, refusing here is what keeps the placeholder off the
                    # wire instead of storing a macro into slot 9999.
                    return _error_result(
                        call,
                        "macro authoring produced commands for zero targets — no free "
                        "slot was derived, so nothing may be stored",
                    )
        payload = build_precheck_report(evaluation, macro=macro).to_dict()
        if macro is not None and macro.commands:
            inner = run_commands(
                ToolCall(
                    id=call.id,
                    name="run_commands",
                    arguments={"commands": list(macro.commands)},
                ),
                context,
            )
            payload["macro_execution"] = json.loads(inner.result.content)
            # A LiveLock demotion and a gate hold both send NOTHING, yet the
            # macro block still says ``created`` and its reason tells the user to
            # go run the macro on the console and watch the lights. On the lock
            # path ``is_error`` is demoted below, so without this key the model
            # reads a non-error report about a macro that does not exist -- the
            # same shape as the read-failure-reported-as-absence defects this SPEC
            # already fixed three times. The sibling handler publishes the same
            # distinction as ``executed``.
            payload["macro"]["executed"] = not inner.result.is_error
            if not inner.result.is_error:
                # Only when the bundle actually went out. A gate hold and a
                # LiveLock demotion both send NOTHING, and requerying a slot the
                # console was never asked to write would manufacture a read
                # failure — noise about a macro that was never attempted. The
                # sibling handler gates its own requery on the same raw flag,
                # BEFORE the lock demotion is applied below.
                payload["macro_requery"] = _requery_macro_line(macro, property_port)
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(payload, ensure_ascii=False),
                    # A gate hold or a failed line IS an error: the model must
                    # react. Two things are NOT errors — a rig with no groups is
                    # an ANSWER, and a LiveLock demotion is the lock doing its
                    # job, which `AC-PRECHK-014` ④ separates from a hold. The
                    # sibling tools demote the same way.
                    is_error=False
                    if payload["macro_execution"].get("gate_status") == _LOCKED
                    else inner.result.is_error,
                ),
                command_outcomes=inner.command_outcomes,
            )
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=False,
            ),
            command_outcomes=(),
        )

    # -- preshow_check (SPEC-COPILOT-PRESHOW-001 — the pre-show checklist) ----
    #
    # @MX:NOTE: read-only diagnostic; reuses the same state_port precheck_patch
    #   already depends on. Never imports server.bridge directly — when
    #   preshow_liveness_port is wired (T-G), the OSC round-trip /
    #   receive-port-binding checks probe through that already-open link
    #   instead of opening a new socket; left unwired (default) they still
    #   report "skip", exactly as before.
    def preshow_check(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        report = run_preshow_checklist(
            state_port=state_port,
            liveness_port=preshow_liveness_port,
            liveness_receive_port=preshow_receive_port,
            configured_osc_slot=preshow_osc_slot,
            sequences_path=rig_paths.get("sequences", "DataPool/Sequences"),
            preset_pools_path=rig_paths.get("preset_pools", "DataPool/PresetPools"),
        )
        content = json.dumps(report.to_dict(), ensure_ascii=False)
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=content,
                is_error=report.signal == "red",
            ),
        )

    # -- find_fx (REQ-FXLIB-015 — lookup only, sends nothing) ------------------
    #
    # @MX:ANCHOR: [AUTO] the only model-reachable entry to the fx MATCHER
    #   (match_fx -> the closed pattern vocabulary).
    # @MX:REASON: REQ-FXLIB-015 + decision G. The rulebook is PRESERVE
    #   (REQ-FXLIB-020, byte-diff 0) and its mood-table fallback sentence names
    #   `find_looks`, not this tool — so nothing in the fixed prefix routes an fx
    #   fallback anywhere. The description below is the ONLY surface carrying
    #   that route; deleting a sentence from it silently removes the model's
    #   documented move, and an fx invented instead of matched is indetectable
    #   afterwards (the effect is not machine-verifiable, REQ-FXLIB-014 (c)).

    def find_fx(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal fx_lib
        query = call.arguments.get("query")
        if not isinstance(query, str):
            return _error_result(call, "'query' must be a string — the operator's own words")
        if fx_lib is None:
            try:
                fx_lib = load_fx_library_from_dir(FX_LIBRARY_DIR)
            except FxSchemaError as error:
                # A broken library is a structured failure, never a silent empty
                # result that would read as "no fx matches".
                return _error_result(call, f"fx library unavailable: {error}")
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(match_fx(query, fx_lib).to_dict(), ensure_ascii=False),
                # A miss is an ANSWER (REQ-FXLIB-008), not a tool failure: an
                # is_error payload feeds the self-correction loop and would
                # invite a retry that can only miss again.
                is_error=False,
            )
        )

    # -- instantiate_fx (REQ-FXLIB-016/017 — the fx layer's ONE route) ---------
    #
    # @MX:ANCHOR: [AUTO] the only model-reachable entry to the fx instantiation
    #   chain (find_fx -> rig read -> bundle -> gate.screen()).
    # @MX:REASON: REQ-FXLIB-016/017. This handler is a CALLER of run_commands,
    #   never a second execution surface: it re-enters the local run_commands
    #   closure above, so the bundle inherits that path's gate screening, live
    #   lock, execution preview, dedupe and audit log without any of them being
    #   duplicated for fx. Reaching execution_port directly from here would be
    #   the second path the SPEC forbids, and it would be invisible to the gate.
    #   M1-M4 built the whole chain with no model-reachable door; that is what
    #   this tool repairs, so do not un-register it without giving the chain
    #   another one.

    def instantiate_fx(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal fx_lib
        fx_id = call.arguments.get("fx_id")
        if not isinstance(fx_id, str) or not fx_id.strip():
            return _error_result(call, "'fx_id' must be the fx_id string returned by find_fx")
        group = _positive_int(call.arguments.get("group"))
        if group is None:
            return _error_result(
                call,
                "'group' must be a positive integer group number that get_rig_context "
                "listed on this rig — not a group name, and not a fixture slot",
            )
        sequence = call.arguments.get("sequence")
        if sequence is not None and _positive_int(sequence) is None:
            return _error_result(
                call,
                "'sequence' must be a positive integer, or omitted so this tool "
                "measures a free number from the rig",
            )
        executor = call.arguments.get("executor")
        if executor is not None and _positive_int(executor) is None:
            return _error_result(call, "'executor' must be a positive integer executor number")
        label = call.arguments.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            return _error_result(
                call, "'label' must be a non-empty label string, or omitted for the fx's own name"
            )
        if fx_lib is None:
            try:
                fx_lib = load_fx_library_from_dir(FX_LIBRARY_DIR)
            except FxSchemaError as error:
                return _error_result(call, f"fx library unavailable: {error}")
        try:
            fx = fx_lib.by_id(fx_id.strip())
        except KeyError:
            # An id this library does not hold is a correctable mistake, so it IS
            # an error result — unlike a find_fx miss, a retry with the right id
            # succeeds.
            return _error_result(
                call,
                f"unknown fx_id {fx_id!r} — call find_fx and pass back the fx_id "
                f"from one of its matches",
            )
        missing = [section for section in FX_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — an fx cannot be "
                f"bound to this rig without them",
            )
        # The rig is READ here even though the group arrives as an argument: the
        # argument says WHICH group, this read says whether that group exists.
        # The sequence number is never an argument the tool trusts blind either —
        # it is measured from this same read (AP-16).
        sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in FX_RIG_SECTIONS},
            drilldown,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            # A section that never arrived is NOT a rig that answered "no such
            # group". Refusing the group here would state a fact about a rig
            # nobody observed.
            return _fx_error_result(
                call,
                "the rig sections an fx is bound against did not arrive: "
                + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items()),
                rig_unavailable=unavailable,
            )
        groups_section = sections["groups"]
        addressable = _addressable_groups(groups_section)
        if group not in addressable:
            # Refused BEFORE anything is sent. `Group 7` on a rig without group 7
            # selects nothing, and the `Store` that follows then writes an EMPTY
            # cue — silently, because a stored phaser cue and an empty one are
            # indistinguishable on read-back (M0). A truncated listing does not
            # license the number either: absence from a cut list is not evidence
            # of absence, but it is not evidence of presence, which is what
            # addressing it would assume.
            truncated = bool(groups_section.get("truncated"))  # type: ignore[union-attr]
            return _fx_error_result(
                call,
                f"group {group} is not addressable on this rig"
                + (
                    " and the group listing was truncated, so it may exist unlisted — "
                    "re-read the rig or name one of the groups below"
                    if truncated
                    else " — use one of the groups below"
                ),
                groups=addressable,
                groups_truncated=truncated,
            )
        try:
            plan = bind_fx(
                fx,
                group=group,
                sequences_section=sections["sequences"],  # type: ignore[arg-type]
                sequence=sequence,
                executor=executor,
                label=label,
            )
        except FxInstantiationError as error:
            return _fx_error_result(
                call, f"fx {fx.fx_id!r} cannot be instantiated: {error}", reason=error.reason
            )
        if not plan.commands:
            # Defensive: the builder always emits a destination, a clear, a
            # selection and a store, so this is unreachable today. It stays
            # because the alternative — sending an empty bundle and reporting it
            # as executed — is the silent success this SPEC exists to prevent.
            report = build_fx_report(plan)
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        {
                            "executed": False,
                            "succeeded": False,
                            "report": report.to_dict(),
                            "summary_ko": fx_report_to_korean(report),
                        },
                        ensure_ascii=False,
                    ),
                    is_error=False,
                )
            )
        execution = run_commands(
            ToolCall(id=call.id, name="run_commands", arguments={"commands": list(plan.commands)}),
            context,
        )
        payload = json.loads(execution.result.content)
        # A gate refusal carries per-command DECISIONS, not execution outcomes.
        # Feeding them to the report would count zero failures and zero folds and
        # verdict a bundle that never left the process "전량 실행".
        outcomes = () if "gate_status" in payload else execution.command_outcomes
        report = build_fx_report(plan, outcomes)
        payload["executed"] = report.executed
        payload["succeeded"] = report.succeeded
        payload["report"] = report.to_dict()
        payload["summary_ko"] = fx_report_to_korean(report)
        # `run_commands` is content when every line came back ok — and a
        # cross-call fold does exactly that while leaving an INCOMPLETE cue
        # behind (REQ-FXLIB-011 (b)). Only a COMPLETE verdict is a success;
        # anything else is an error the model must report.
        is_error = execution.result.is_error or not report.succeeded
        if payload.get("gate_status") == _LOCKED:
            # ...except a LiveLock demotion, which is an ANSWER, not a failure:
            # the proposal IS the deliverable. `is_error=True` would feed the
            # self-correction loop and send the model back into the same lock —
            # during a show, which is precisely when the lock is on. The sibling
            # tools demote the same way (`prepare_busking` REQ-BUSKWIZ-014,
            # `precheck_patch` AC-PRECHK-014 ④); fx diverged until M6 measured it.
            is_error = False
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- find_scene (REQ-SCENE-018 — lookup only, sends nothing) ---------------
    #
    # @MX:ANCHOR: [AUTO] the only model-reachable entry to the scene MATCHER
    #   (match_scene -> the two-axis look/fx split).
    # @MX:REASON: REQ-SCENE-007/008/018. The rulebook is PRESERVE (spec.md §D,
    #   byte-diff 0) and learned nothing about scenes, so this description is
    #   the ONLY surface that routes the model here. A scene invented instead of
    #   matched is undetectable afterwards — the effect is not machine-verifiable
    #   (REQ-SCENE-014 (b)).

    def find_scene(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal scene_lib
        query = call.arguments.get("query")
        if not isinstance(query, str):
            return _error_result(call, "'query' must be a string — the operator's own words")
        if scene_lib is None:
            try:
                scene_lib = load_scene_library_from_dir(SCENE_LIBRARY_DIR)
            except SceneSchemaError as error:
                # A broken library is a structured failure, never a silent empty
                # result that would read as "no scene matches".
                return _error_result(call, f"scene library unavailable: {error}")
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(match_scene(query, scene_lib).to_dict(), ensure_ascii=False),
                # A miss is an ANSWER (REQ-SCENE-009), not a tool failure.
                is_error=False,
            )
        )

    def _scene_requery(
        state: object, sequence: int, cue: float
    ) -> tuple[dict[str, object] | None, str | None]:
        """Read the stored sequence back and pin ONLY what the read answered.

        A command receipt is not evidence of effect — the doctrine this whole
        SPEC is built on. `prepare_songcue` set the precedent (requery after a
        successful send, `requery_error` when the read itself fails), and the
        scene report has carried the consuming half since M5:
        `ARTIFACT_CONFIRMED_NOTE` is reached ONLY when a requery mapping
        arrives. Until this wiring existed the tool never passed one, so every
        production scene report filed claim (a) as UNVERIFIED.

        Returns `(mapping, None)` when the read confirms this cue, else
        `(None, reason)`. A reason is NEVER "the cue is absent": the console
        does not return cue CONTENT (spec.md §C.1), so absence is a claim
        about a value nobody could read. The caller files the reason as a
        mismatch and the report keeps (a) unconfirmed.

        Two refusals beyond "no such cueNo", both following the songcue
        sibling (`songcue_report.py` admits an observation only for a real
        number plus a real name):

        * a non-number `cueNo` — `bool` is an `int` in Python, and every other
          responder-child read in this repo excludes it by name;
        * a matched cue whose name (or its sequence's name) did not arrive.
          `ARTIFACT_CONFIRMED_NOTE` says the requery confirmed the NAMES, so
          confirming a nameless read would state something nobody read — and
          the summary would print `시퀀스 'None' · 큐 'None'`.
        """
        if not isinstance(state, dict):
            return None, "재조회 응답이 상태 객체가 아니다"
        node = state.get("node")
        children = state.get("children")
        if not isinstance(children, list):
            return None, "재조회 응답에 children 목록이 없다"
        for child in children:
            if not isinstance(child, dict) or child.get("class") != "Cue":
                continue
            raw = child.get("cueNo")
            # System cues (`OffCue`) arrive as class Cue with NO cueNo, so a
            # missing key is ordinary, not an error — skip to the next child.
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                continue
            if float(raw) != float(cue):
                continue
            cue_name = child.get("name")
            sequence_name = node.get("name") if isinstance(node, dict) else None
            if not isinstance(cue_name, str) or not isinstance(sequence_name, str):
                return None, (
                    f"시퀀스 {sequence}의 큐 {cue}를 찾았으나 재조회가 이름을 담지 않았다 — "
                    "확인 문면은 이름까지 확인됐다고 말하므로 확인으로 올리지 않는다"
                )
            return {
                "sequence": sequence,
                "sequence_name": sequence_name,
                "cue_name": cue_name,
                "cue_no": float(raw),
            }, None
        return None, (
            f"재조회가 응답했으나 시퀀스 {sequence}에서 큐 {cue}를 찾지 못했다 — "
            "큐가 없다는 뜻은 아니다(저작·전송은 별도로 보고된다). 콘솔에서 직접 확인하라"
        )

    # -- compile_scene (REQ-SCENE-018 — the scene layer's ONE route) -----------
    #
    # @MX:ANCHOR: [AUTO] the only model-reachable entry to the scene compilation
    #   chain (find_scene -> rig read -> look+fx bundle -> gate.screen()).
    # @MX:REASON: REQ-SCENE-018/019. This handler is a CALLER of run_commands,
    #   never a second execution surface: it re-enters the local run_commands
    #   closure above, so the bundle inherits that path's gate screening, live
    #   lock, execution preview, dedupe and audit log. Reaching execution_port
    #   directly from here would be the second path REQ-SCENE-019 forbids, and
    #   the gate would not see it. The single-tool shape is also FORCED, not
    #   preferred: chaining instantiate_look then instantiate_fx in one
    #   instruction turn folds from the shared `Step` lines onward and stores two
    #   different artifacts, so one cue can never come out of it (design.md §2.1).

    def compile_scene(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal scene_lib, looks, fx_lib
        scene_id = call.arguments.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id.strip():
            return _error_result(
                call, "'scene_id' must be the scene_id string returned by find_scene"
            )
        group = _positive_int(call.arguments.get("group"))
        if group is None:
            return _error_result(
                call,
                "'group' must be a positive integer group number that get_rig_context "
                "listed on this rig — not a group name, and not a fixture slot",
            )
        # Timing is validated by the scene layer's OWN argument schema, not by a
        # second copy here: `parse_timing` is where "a legal cue number" is
        # defined (REQ-SCENE-006), and the closed trigger vocabulary with it.
        timing_args = {
            key: call.arguments[key]
            for key in ("sequence", "cue", "trig_type", "trig_time")
            if call.arguments.get(key) is not None
        }
        try:
            timing = parse_scene_timing(
                {
                    **(
                        {"sequence_number": timing_args["sequence"]}
                        if "sequence" in timing_args
                        else {}
                    ),
                    **({"cue_number": timing_args["cue"]} if "cue" in timing_args else {}),
                    **{k: v for k, v in timing_args.items() if k in ("trig_type", "trig_time")},
                },
                source="compile_scene",
            )
        except SceneSchemaError as error:
            return _error_result(call, str(error))
        executor = call.arguments.get("executor")
        if executor is not None and _positive_int(executor) is None:
            return _error_result(call, "'executor' must be a positive integer executor number")
        label = call.arguments.get("label")
        if label is not None:
            try:
                label = validate_scene_label(label, source="compile_scene")
            except SceneSchemaError as error:
                return _error_result(call, str(error))
        if scene_lib is None:
            try:
                scene_lib = load_scene_library_from_dir(SCENE_LIBRARY_DIR)
            except SceneSchemaError as error:
                return _error_result(call, f"scene library unavailable: {error}")
        try:
            scene = scene_lib.by_id(scene_id.strip())
        except KeyError:
            return _error_result(
                call,
                f"unknown scene_id {scene_id!r} — call find_scene and pass back the "
                f"scene_id from one of its matches",
            )
        # The scene holds REFERENCES; the values live upstream and are read here.
        look = None
        if scene.look_id is not None:
            if looks is None:
                try:
                    looks = load_library_from_dir()
                except LookSchemaError as error:
                    return _error_result(call, f"look library unavailable: {error}")
            try:
                look = looks.by_id(scene.look_id)
            except KeyError:
                return _error_result(
                    call,
                    f"scene {scene.scene_id!r} references look {scene.look_id!r}, which "
                    "the look library does not hold",
                )
        fx = None
        if scene.fx_id is not None:
            if fx_lib is None:
                try:
                    fx_lib = load_fx_library_from_dir(FX_LIBRARY_DIR)
                except FxSchemaError as error:
                    return _error_result(call, f"fx library unavailable: {error}")
            try:
                fx = fx_lib.by_id(scene.fx_id)
            except KeyError:
                return _error_result(
                    call,
                    f"scene {scene.scene_id!r} references fx {scene.fx_id!r}, which the "
                    "fx library does not hold",
                )
        missing = [section for section in SCENE_RIG_SECTIONS if section not in rig_paths]
        if missing:
            return _error_result(
                call,
                f"rig context has no path configured for {missing} — a scene cannot be "
                f"bound to this rig without them",
            )
        # The rig is READ here even though the group arrives as an argument: the
        # argument says WHICH group, this read says whether that group exists.
        sections, _resolved, _failed = collect_rig_sections(
            state_port,
            {section: rig_paths[section] for section in SCENE_RIG_SECTIONS},
            drilldown,
            RIG_DRILLDOWN_QUERY_CAP,
        )
        unavailable = {
            name: entry
            for name, entry in sections.items()
            if isinstance(entry, dict) and "reason" in entry
        }
        if unavailable:
            # A section that never arrived is NOT a rig that answered "no such
            # group" — refusing here would state a fact about a rig nobody read.
            return _fx_error_result(
                call,
                "the rig sections a scene is bound against did not arrive: "
                + "; ".join(f"{n}: {e['reason']}" for n, e in unavailable.items()),
                rig_unavailable=unavailable,
            )
        groups_section = sections["groups"]
        addressable = _addressable_groups(groups_section)
        if group not in addressable:
            # Refused BEFORE anything is sent. `Group 7` on a rig without group 7
            # selects nothing and the `Store` that follows writes an EMPTY cue —
            # silently, because a stored cue's content is not machine-readable
            # (spec.md §C.1). A truncated listing does not license the number
            # either: absence from a cut list is not evidence of presence.
            truncated = bool(groups_section.get("truncated"))  # type: ignore[union-attr]
            return _fx_error_result(
                call,
                f"group {group} is not addressable on this rig"
                + (
                    " and the group listing was truncated, so it may exist unlisted — "
                    "re-read the rig or name one of the groups below"
                    if truncated
                    else " — use one of the groups below"
                ),
                groups=addressable,
                groups_truncated=truncated,
            )
        # The cue pool of a sequence that does not exist yet. This is DERIVED,
        # not invented: `select_sequence_number` (fx's, decision H) only ever
        # returns a number the sequence listing showed as free, and refuses a
        # requested number that is occupied — so the sequence this bundle stores
        # into holds no cues. Passing a measured-looking pool we did not read
        # would be the fabrication REQ-SCENE-013 (d) forbids; passing this one
        # states exactly the fact the sequence listing established.
        empty_cue_pool = rig_section([], {"truncated": False, "node": {"childCount": 0}})
        try:
            compilation = build_scene_bundle(
                scene,
                look=look,
                fx=fx,
                group=group,
                sequences_section=sections["sequences"],  # type: ignore[arg-type]
                cues_section=empty_cue_pool,
                sequence_number=timing.sequence_number,
                cue_number=timing.cue_number,
                trig_type=timing.trig_type,
                trig_time=timing.trig_time,
                executor=executor,
            )
        except SceneCompilationError as error:
            return _fx_error_result(
                call,
                f"scene {scene.scene_id!r} cannot be compiled: {error}",
                reason=error.reason,
            )
        if label is not None and label != compilation.label:
            # The operator's label replaces the authored one AFTER the bundle is
            # built, by rebuilding it — never by editing the Store string, which
            # would be the reassembly design.md §2.2 forbids.
            try:
                compilation = build_scene_bundle(
                    replace(scene, label=label),
                    look=look,
                    fx=fx,
                    group=group,
                    sequences_section=sections["sequences"],  # type: ignore[arg-type]
                    cues_section=empty_cue_pool,
                    sequence_number=timing.sequence_number,
                    cue_number=timing.cue_number,
                    trig_type=timing.trig_type,
                    trig_time=timing.trig_time,
                    executor=executor,
                )
            except SceneCompilationError as error:
                return _fx_error_result(
                    call,
                    f"scene {scene.scene_id!r} cannot be compiled: {error}",
                    reason=error.reason,
                )
        execution = run_commands(
            ToolCall(
                id=call.id,
                name="run_commands",
                arguments={"commands": list(compilation.commands)},
            ),
            context,
        )
        payload = json.loads(execution.result.content)
        # A gate refusal carries per-command DECISIONS, not execution outcomes.
        # Feeding them to the report would verdict a bundle that never left the
        # process as "전량 실행".
        outcomes = () if "gate_status" in payload else execution.command_outcomes
        # The evidence channel for claim (a). Gated on the RAW execution flag,
        # BEFORE the LiveLock demotion below: a gate hold and a demotion both
        # send NOTHING, and requerying a sequence the console was never asked
        # to write would manufacture a read failure about a cue nobody
        # attempted (the sibling `precheck_patch` gates its macro requery on
        # the same raw flag for the same reason).
        requery = None
        requery_error = None
        requery_mismatch = None
        if not execution.result.is_error:
            try:
                state = state_port.query_state(f"{rig_paths['sequences']}/{compilation.sequence}")
            except Exception as error:  # noqa: BLE001 — a failed READ, reported as one
                # NEVER "the cue is not there": substituting absence for a
                # failed read is the defect class the sibling read paths fixed.
                # The console's own failure text ("path segment not found: …")
                # IS a sentence stating absence, so the report frames it with
                # the disclaimer FIRST and quotes the console second.
                requery_error = str(error)
                payload["requery_error"] = requery_error
            else:
                requery, requery_mismatch = _scene_requery(
                    state, compilation.sequence, compilation.cue
                )
                if requery_mismatch is not None:
                    payload["requery_mismatch"] = requery_mismatch
        # Three states, three sentences. "Attempted and did not confirm" is a
        # DIFFERENT fact from "not attempted", and before these two arguments
        # existed the report said the latter for both.
        report = build_scene_report(
            compilation,
            outcomes,
            requery=requery,
            requery_error=requery_error,
            requery_mismatch=requery_mismatch,
        )
        payload["executed"] = report.executed
        payload["succeeded"] = report.succeeded
        payload["report"] = report.to_dict()
        payload["summary_ko"] = scene_report_to_korean(report)
        # A cross-call fold comes back with every line ok while leaving an
        # INCOMPLETE cue behind (REQ-SCENE-015 (b)). Only COMPLETE is success.
        is_error = execution.result.is_error or not report.succeeded
        if payload.get("gate_status") == _LOCKED:
            # ...except a LiveLock demotion, which is an ANSWER, not a failure:
            # the proposal IS the deliverable (REQ-SCENE-020). The sibling tools
            # demote the same way.
            is_error = False
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=is_error,
            ),
            command_outcomes=execution.command_outcomes,
        )

    # -- build_patch_sheet / build_cue_sheet / build_preset_list (T-J — paperwork
    #    read-only wiring) -------------------------------------------------------
    #
    # Every builder here rides the SAME gate-audited query ports every other
    # rig-context tool uses; server/paperwork/data.py never imports the OSC send
    # surface (server/tests/test_paperwork_boundary.py). The self-contained HTML
    # a renderer produces is NEVER put in the tool result content — a model has
    # no use for 3-6KB of markup, and a human opens the file in a browser — so
    # the result carries only the written file's path plus a small numeric
    # summary. The write location is frozen-aware
    # (server.paperwork.output.resolve_paperwork_dir, the same split
    # server.safety.bootstrap.resolve_runtime_audit_dir makes for audit logs)
    # and the basename is a fixed, deterministic constant, so a rebuild
    # overwrites the same file rather than littering the directory.

    def build_patch_sheet(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        # Deferred (function-local), not module-level: server.paperwork.data
        # itself imports DEFAULT_RIG_CONTEXT_PATHS/collect_rig_sections from
        # THIS module (server.orchestrator.tools), so a module-level import
        # here would close an import cycle (tools -> paperwork -> tools) that
        # fails at interpreter load time. Deferring to call time is safe:
        # both modules are fully initialized long before any handler runs.
        from server.paperwork.data import build_patch_sheet as build_patch_sheet_query
        from server.paperwork.output import write_paperwork_html
        from server.paperwork.render import render_patch_sheet

        if property_port is None:
            # Same missing-capability wording precheck_patch uses — never answer
            # "zero fixtures" when the capability is simply unwired.
            return _error_result(
                call,
                "property reads are not wired — build_toolset needs property_port "
                "(or a state_port that also implements query_property)",
            )
        try:
            sheet = build_patch_sheet_query(_InventoryPort(state_port, property_port))
        except InventoryReadError as error:
            return _error_result(call, f"fixture inventory unreadable: {error}")
        try:
            path = write_paperwork_html("patch_sheet.html", render_patch_sheet(sheet))
        except OSError as error:
            return _error_result(call, f"patch sheet could not be written to disk: {error}")
        content = json.dumps(
            {
                "path": str(path),
                "fixture_count": sheet.observed_count,
                "child_count": sheet.child_count,
                "completeness": sheet.completeness,
            },
            ensure_ascii=False,
        )
        return ToolExecution(
            result=ToolResult(tool_call_id=call.id, name=call.name, content=content, is_error=False)
        )

    def build_cue_sheet(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        # Deferred import — see build_patch_sheet's comment above.
        from server.paperwork.data import build_cue_sheet as build_cue_sheet_query
        from server.paperwork.output import write_paperwork_html
        from server.paperwork.render import render_cue_sheet

        listing = build_cue_sheet_query(
            state_port,
            sequences_path=rig_paths.get("sequences", DEFAULT_RIG_CONTEXT_PATHS["sequences"]),
        )
        if listing.unavailable_reason is not None:
            content = json.dumps(
                {
                    "error": (f"the sequences pool did not arrive: {listing.unavailable_reason}"),
                    "reason": listing.unavailable_reason,
                    "detail": listing.unavailable_detail,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            path = write_paperwork_html("cue_sheet.html", render_cue_sheet(listing))
        except OSError as error:
            return _error_result(call, f"cue sheet could not be written to disk: {error}")
        content = json.dumps(
            {
                "path": str(path),
                "sequence_count": len(listing.pools),
                "cue_count": sum(len(pool.items) for pool in listing.pools),
                "truncated": listing.truncated,
                "drilldown_capped": listing.drilldown_capped,
            },
            ensure_ascii=False,
        )
        return ToolExecution(
            result=ToolResult(tool_call_id=call.id, name=call.name, content=content, is_error=False)
        )

    def build_preset_list(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        # Deferred import — see build_patch_sheet's comment above.
        from server.paperwork.data import build_preset_list as build_preset_list_query
        from server.paperwork.output import write_paperwork_html
        from server.paperwork.render import render_preset_list

        listing = build_preset_list_query(
            state_port,
            preset_pools_path=rig_paths.get(
                "preset_pools", DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]
            ),
        )
        if listing.unavailable_reason is not None:
            content = json.dumps(
                {
                    "error": (f"the preset pools did not arrive: {listing.unavailable_reason}"),
                    "reason": listing.unavailable_reason,
                    "detail": listing.unavailable_detail,
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        try:
            path = write_paperwork_html("preset_list.html", render_preset_list(listing))
        except OSError as error:
            return _error_result(call, f"preset list could not be written to disk: {error}")
        content = json.dumps(
            {
                "path": str(path),
                "pool_count": len(listing.pools),
                "preset_count": sum(len(pool.items) for pool in listing.pools),
                "truncated": listing.truncated,
                "drilldown_capped": listing.drilldown_capped,
            },
            ensure_ascii=False,
        )
        return ToolExecution(
            result=ToolResult(tool_call_id=call.id, name=call.name, content=content, is_error=False)
        )

    # -- plan_executor_layout (T-J — server/looks/layout.py wiring) ------------
    #
    # PLANS ONLY, NEVER SENDS: this handler never calls run_commands and never
    # touches execution_port. It reuses select_genre's own result object as the
    # "bundle" plan_layout expects — a GenreSelection already carries exactly
    # the (genre, looks) shape plan_layout reads, so no preset-pool/group
    # resolution (and no console write surface at all) is needed to place looks
    # on executors; that is a SEPARATE concern instantiate_look/prepare_busking
    # already own. The occupancy check (check_occupancy) is the one live read
    # this handler performs, and only to CLASSIFY conflicts in the answer —
    # never to act on them. Conflicted items are excluded from the returned
    # commands (server/looks/layout.py::build_layout_commands), which the
    # caller must pass to run_commands itself to actually apply — gate
    # screening, LiveLock and the audit log all still apply unchanged there.

    def plan_executor_layout(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        nonlocal looks
        genre = call.arguments.get("genre")
        if not isinstance(genre, str) or not genre.strip():
            return _error_result(
                call, "'genre' must be the operator's own word for the genre (e.g. '록', 'EDM')"
            )
        raw_sequence_numbers = call.arguments.get("sequence_numbers")
        if not isinstance(raw_sequence_numbers, Mapping) or not raw_sequence_numbers:
            return _error_result(
                call,
                "'sequence_numbers' must be a non-empty object mapping each look_id to an "
                "EXISTING sequence number on this rig — this tool never creates a sequence",
            )
        sequence_numbers: dict[str, int] = {}
        for key, value in raw_sequence_numbers.items():
            if (
                not isinstance(key, str)
                or isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
            ):
                return _error_result(
                    call,
                    "'sequence_numbers' keys must be look_id strings and values must be "
                    "positive integers",
                )
            sequence_numbers[key] = value
        page_no = call.arguments.get("page_no", 1)
        if isinstance(page_no, bool) or not isinstance(page_no, int) or page_no < 1:
            return _error_result(call, "'page_no' must be a positive integer")
        start_slot = call.arguments.get("start_slot", 1)
        if isinstance(start_slot, bool) or not isinstance(start_slot, int) or start_slot < 1:
            return _error_result(call, "'start_slot' must be a positive integer")
        if looks is None:
            try:
                looks = load_library_from_dir()
            except LookSchemaError as error:
                return _error_result(call, f"look library unavailable: {error}")
        selection = select_genre(looks, genre)
        if selection.genre is None:
            content = json.dumps(
                {
                    "error": f"unknown genre {genre!r}",
                    "reason": selection.reason,
                    "candidates": list(selection.candidates),
                },
                ensure_ascii=False,
            )
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id, name=call.name, content=content, is_error=True
                )
            )
        plan = plan_layout(selection, sequence_numbers, page_no=page_no, start_slot=start_slot)
        plan = check_occupancy(state_port, plan)
        commands = build_layout_commands(plan)
        content = json.dumps(
            {
                "executed": False,
                "genre": plan.genre,
                "page_no": plan.page_no,
                "complete": plan.complete,
                "items": [
                    {
                        "look_id": item.look_id,
                        "display_name": item.display_name,
                        "sequence_number": item.sequence_number,
                        "label": item.label,
                        "page_no": item.page_no,
                        "slot": item.slot,
                        "executor_no": item.executor_no,
                        "conflict": item.conflict,
                        "conflict_reason": item.conflict_reason,
                        "conflict_detail": item.conflict_detail,
                    }
                    for item in plan.items
                ],
                "skipped": [
                    {"look_id": skip.look_id, "reason": skip.reason, "detail": skip.detail}
                    for skip in plan.skipped
                ],
                "commands": list(commands),
            },
            ensure_ascii=False,
        )
        return ToolExecution(
            result=ToolResult(tool_call_id=call.id, name=call.name, content=content, is_error=False)
        )

    # -- get_spatial_context (SPEC-COPILOT-SPATIAL-001 M1 — REQ-SPATIAL-001/
    #    004/005/006/007) ---------------------------------------------------------
    #
    # The READ half of the spatial axis, and a strict sibling of
    # get_rig_context rather than an extension of it: rig context answers
    # "which objects exist", this answers "where they are", and REQ-SPATIAL-008
    # makes that separation non-negotiable — the ten rig-context paths and the
    # snapshot shape are unchanged, and their tests pass unedited.
    #
    # Reads only. It obtains its console seam exactly the way get_rig_context
    # does (the injected query ports, never the execution port), composes no
    # command line and mutates nothing, so there is no gate surface for it to
    # need. The WRITE half — the one that does compose command lines and does
    # ride the gate — is a separate tool on purpose (decision D-4): folding a
    # showfile mutation into the tool a model calls to LOOK at the rig would
    # blur which approval card the operator is being shown.

    def get_spatial_context(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        fixtures_path = rig_paths.get("fixtures")
        if not fixtures_path:
            # Fail by NAME, like every other rig-section guard here — a
            # rig_paths override that drops the stage patch must not read as a
            # rig that has no fixtures.
            return _error_result(
                call,
                "rig context has no 'fixtures' path configured — the stage patch "
                "cannot be read for coordinates without it",
            )
        if property_port is None:
            # Same missing-capability wording precheck_patch and
            # build_patch_sheet use. Coordinates live ONLY in properties, so an
            # unwired port means the answer is unavailable, never "no fixtures
            # have coordinates".
            return _error_result(
                call,
                "property reads are not wired — build_toolset needs property_port "
                "(or a state_port that also implements query_property)",
            )
        try:
            reply = read_spatial_fixtures(
                state_port, property_port, fixtures_path, SPATIAL_PROPERTY_QUERY_CAP
            )
        except Exception as exc:
            return _error_result(
                call, f"stage patch enumeration failed for {fixtures_path!r}: {exc}"
            )
        # @MX:ANCHOR: [SPEC] the WITHHELD analysis (SPEC-COPILOT-TRUNCATE-001
        #   REQ-TRUNCATE-003 / AC-TRUNCATE-002, mutation-required). Branch on
        #   the SHAPE the read returned, never on a second reading of the
        #   coverage — `read_spatial_fixtures` already judged it once, and a
        #   handler that re-judged could disagree with the payload it is
        #   annotating.
        # @MX:REASON: This is the half of the design that carries the load,
        #   and the moved key is only the half that makes it visible.
        #   `analyze_spatial_records` takes records and NOTHING else
        #   (server/spatial/rows.py) — no truncation argument exists, so its
        #   output is structurally incapable of knowing it describes part of a
        #   rig. On the measured 18-of-19 read it therefore reported
        #   `low_confidence: False` ("high confidence, one row") — a confident
        #   layout asserted for a rig that does not exist. Flagging it is not
        #   an option: the ability would have to come from `server/spatial/**`,
        #   which REQ-TRUNCATE-012 keeps as a pure geometry layer that knows
        #   nothing about read completeness. So the tool layer withholds. A
        #   model that ignores a boolean can still quote a row ordering; it
        #   cannot quote a key that was never computed.
        if "partial_fixtures" in reply:
            reply["analysis_withheld"] = {
                "withheld": "analysis",
                "reason": (
                    "row structure was NOT computed for this read and is not in "
                    "this reply. The analysis takes the coordinate records alone "
                    "and has no way to know the list is incomplete, so folding it "
                    "over a partial rig produces a confident layout for a rig "
                    "that does not exist — measured: low_confidence false on an "
                    "18-of-19 read. See 'missing' for the shortfall. If you need "
                    "an order, derive it from the coordinates in "
                    "'partial_fixtures' yourself AND say which fixtures are "
                    "absent from it."
                ),
            }
        else:
            try:
                reply["analysis"] = spatial_analysis_to_dict(
                    analyze_spatial_records(reply["fixtures"])  # type: ignore[arg-type]
                )
            except SpatialAnalysisError as error:
                # The coordinate map plus the absence report is the mandatory
                # deliverable; row structure is a fold-in over it. A read defect
                # the pure layer refuses (two records claiming one fid) costs the
                # analysis, never the map the caller can still inspect.
                reply["analysis"] = None
                reply["analysis_error"] = str(error)
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(reply, ensure_ascii=False),
                # A rig that answered with no usable coordinates is an ANSWER,
                # carrying its own demotion signal in analysis.low_confidence
                # (REQ-SPATIAL-005). Marking it an error would feed the
                # self-correction loop a retry that can only read the same rig
                # again. Only a container that never answered is a failed call,
                # and that returned above.
                is_error=False,
            )
        )

    # -- arrange_fixtures (REQ-SPATIAL-019~024 — the coordinate WRITE axis) ----
    #
    # The ONE order this tool may run in, and none of it is negotiable:
    #
    #   read + retain EVERY target's current coordinates   (backup)
    #     -> gate screening + approval                     (run_commands)
    #       -> write                                       (run_commands)
    #         -> read the coordinates back and COMPARE     (verification)
    #           -> restore bundle in the report            (always)
    #
    # Like `instantiate_look` this handler is a CALLER of `run_commands`, never
    # a second execution surface: the bundle inherits gate screening, the live
    # lock, dedupe and the audit log from that one path (REQ-SPATIAL-024).

    def arrange_fixtures(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        preset = call.arguments.get("preset")
        if not isinstance(preset, str) or preset not in SPATIAL_PRESETS:
            return _error_result(
                call, f"'preset' must be one of {list(SPATIAL_PRESETS)}, not {preset!r}"
            )
        fids = call.arguments.get("fids")
        if not isinstance(fids, list) or not fids:
            return _error_result(
                call,
                "'fids' must be a non-empty list of the fixture ids to move — this tool "
                "moves exactly what it is told to and never widens the set itself",
            )
        params = {
            key: value for key, value in call.arguments.items() if key not in ("preset", "fids")
        }
        try:
            plan = spatial_preset_placements(preset, fids, params)
        except SpatialPresetError as error:
            return _error_result(call, f"{preset!r} arrangement cannot be computed: {error}")
        targets = plan.fids

        def _arrange_payload(**extra: object) -> dict[str, object]:
            """The report skeleton every branch returns, in one place."""
            payload: dict[str, object] = {
                "preset": plan.preset,
                "resolved": plan.resolved,
                "targets": list(targets),
                "planned": spatial_placements_to_records(plan.placements),
            }
            payload.update(extra)
            return payload

        def _arrange_result(
            payload: Mapping[str, object],
            *,
            is_error: bool,
            outcomes: tuple[CommandOutcome, ...] = (),
        ) -> ToolExecution:
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(payload, ensure_ascii=False),
                    is_error=is_error,
                ),
                command_outcomes=outcomes,
            )

        # LiveLock is checked BEFORE the backup read, not after. Every other
        # mutating tool learns about the lock from `run_commands`, but this one
        # reaches the console one step earlier: the backup is itself a console
        # round trip, and REQ-SPATIAL-023 demotes the WHOLE bundle to a proposal
        # with ZERO sends — backup read included (acceptance.md §D). The gate
        # stays authoritative for the write; this probe only decides whether to
        # start reading. It is duck-typed on the wired gate for the same reason
        # `property_port` is adopted from `state_port` above: a narrow test
        # double stays narrow instead of being forced to grow a lock.
        # `SafetyGate.status` is a PROPERTY returning
        # `{"health": ..., "live_lock": bool}` (gate.py:186); a callable is
        # accepted too so a differently-shaped gate is not silently read as
        # unlocked.
        lock_status = getattr(bundle_gate, "status", None)
        live_locked = False
        try:
            if callable(lock_status):
                lock_status = lock_status()
            if isinstance(lock_status, Mapping):
                live_locked = bool(lock_status.get("live_lock"))
        except Exception:  # a gate that cannot answer is not a locked gate
            live_locked = False
        if live_locked:
            proposed = arrange_write_commands(plan.placements)
            notice = (
                "live lock active (read-only) — proposal only. Nothing was read and "
                "nothing was written: the original-coordinate backup this tool "
                "requires is itself a console round trip, so it is proposed too."
            )
            return _arrange_result(
                _arrange_payload(
                    status="proposal",
                    gate_status=_LOCKED,
                    executed=False,
                    succeeded=False,
                    verified=False,
                    backup=[],
                    restore_bundle=[],
                    proposed_commands=list(proposed),
                    notice=notice,
                ),
                # A demotion is an ANSWER, not a failure (REQ-SPATIAL-023): an
                # is_error payload would feed the self-correction loop and send
                # the model back into the same lock, during a show.
                is_error=False,
                outcomes=tuple(
                    CommandOutcome(command=command, status="proposal", detail=notice)
                    for command in proposed
                ),
            )

        fixtures_path = rig_paths.get("fixtures")
        if not fixtures_path:
            return _error_result(
                call,
                "rig context has no path configured for 'fixtures' — coordinates "
                "cannot be backed up or written without it",
            )
        if property_port is None:
            # Not a degraded mode: a write with no way to read the original
            # coordinates back is exactly what REQ-SPATIAL-020 prohibits.
            return _error_result(
                call,
                "arrange_fixtures needs a property-read capability to back up the "
                "original coordinates; this session has none, so nothing is written",
            )
        reader: PropertyQueryPort = property_port

        def _arrange_locate() -> tuple[dict[int, tuple[int, str]], list[int], dict[str, object]]:
            """Measure which container slot holds each named fid.

            A slot is NOT an fid (`rig_object` docstring, REQ-SPATIAL-007), so
            every target's slot is read rather than assumed. The walk stops as
            soon as the last target is found.
            """
            snapshot = state_port.query_state(fixtures_path)
            children = snapshot.get("children") if isinstance(snapshot, dict) else None
            if not isinstance(children, list):
                raise LookupError(f"{fixtures_path} returned no children list")
            remaining = list(targets)
            found: dict[int, tuple[int, str]] = {}
            queries = 0
            capped = False
            for child in children:
                if not remaining:
                    break
                if queries >= ARRANGE_SLOT_QUERY_CAP:
                    capped = True
                    break
                if not isinstance(child, dict) or not isinstance(child.get("i"), int):
                    continue
                slot = int(child["i"])
                queries += 1
                read = read_properties(reader, f"{fixtures_path}/{slot}", ("fid",))["fid"]
                if not read.ok or read.value is None:
                    continue
                try:
                    fid = int(str(read.value).strip())
                except ValueError:
                    continue
                if fid in remaining:
                    remaining.remove(fid)
                    found[fid] = (slot, str(child.get("name") or "").strip())
            walk = {
                "slot_queries": queries,
                "roundtrip_capped": capped,
                # `snapshot` is a dict by here — the children guard above
                # raised otherwise.
                "truncated": bool(snapshot.get("truncated")),
            }
            return found, remaining, walk

        def _arrange_read(slot: int) -> tuple[list[str], list[float], str | None]:
            """Read one slot's three position axes; report the first failure."""
            reads = read_properties(reader, f"{fixtures_path}/{slot}", ARRANGE_READ_AXES)
            raw: list[str] = []
            values: list[float] = []
            for axis in ARRANGE_READ_AXES:
                read = reads[axis]
                if not read.ok or read.value is None:
                    return raw, values, read.error or f"property not readable: {axis}"
                text = str(read.value).strip()
                if not _ARRANGE_VALUE.fullmatch(text):
                    return raw, values, f"{axis} read back as {text!r}, not a plain decimal"
                raw.append(text)
                values.append(float(text))
            return raw, values, None

        try:
            located, unresolved, walk = _arrange_locate()
        except Exception as error:
            return _error_result(call, f"the patch container could not be read: {error}")

        # @MX:ANCHOR: [MANUAL] the backup-before-write guard. EVERY target's
        #   current coordinates are read and retained here, before a single
        #   command line is built, and any target that cannot be backed up
        #   cancels the WHOLE write rather than being skipped.
        # @MX:REASON: REQ-SPATIAL-020 / AC-SPATIAL-019. `server/safety/backup.py`
        #   snapshots the showfile but has NO restore SEND path (T-B2;
        #   `gate.py:283` marks the seat deliberately unimplemented), so a
        #   snapshot cannot undo this tool — re-writing the original coordinates
        #   is the only recovery that exists. Backing up per target as the
        #   writes go would satisfy the letter and lose the point: run_commands
        #   stops on the first failure, so a partial write is the EXPECTED
        #   failure mode and only an up-front backup of every target keeps it
        #   recoverable. Reordering this below the write, or letting an
        #   unreadable target through, removes the last defence a physical rig's
        #   surveyed positions have.
        backups: list[ArrangeBackup] = []
        unreadable: list[dict[str, object]] = []
        for fid in targets:
            if fid not in located:
                unreadable.append(
                    {
                        "fid": fid,
                        "reason": (
                            "no patch slot answered with this fid"
                            + (
                                " (the container snapshot was truncated, so it may "
                                "simply not have been read)"
                                if walk["truncated"] or walk["roundtrip_capped"]
                                else ""
                            )
                        ),
                    }
                )
                continue
            slot, name = located[fid]
            raw, values, failure = _arrange_read(slot)
            if failure is not None:
                unreadable.append({"fid": fid, "slot": slot, "name": name, "reason": failure})
                continue
            backups.append(
                ArrangeBackup(
                    fid=fid,
                    slot=slot,
                    name=name,
                    raw=(raw[0], raw[1], raw[2]),
                    values=(values[0], values[1], values[2]),
                )
            )
        if unreadable:
            return _arrange_result(
                _arrange_payload(
                    status="refused",
                    executed=False,
                    succeeded=False,
                    verified=False,
                    backup=[backup.to_dict() for backup in backups],
                    restore_bundle=list(arrange_restore_commands(backups)),
                    unreadable=unreadable,
                    walk=walk,
                    error=(
                        "the original coordinates of "
                        f"{len(unreadable)} of {len(targets)} targets could not be read, "
                        "so NOTHING was written — a coordinate write with no backup has "
                        "no way back (REQ-SPATIAL-020)"
                    ),
                ),
                is_error=True,
            )

        commands = arrange_write_commands(plan.placements)
        restore_bundle = arrange_restore_commands(backups)
        violations = arrange_scope_violations(commands, targets)
        if violations:
            # Unreachable while the builder is correct, which is the point: the
            # seal is a static assertion about the TEXT on its way to the gate,
            # not a belief about the code that produced it (AC-SPATIAL-021).
            return _arrange_result(
                _arrange_payload(
                    status="refused",
                    executed=False,
                    succeeded=False,
                    verified=False,
                    backup=[backup.to_dict() for backup in backups],
                    restore_bundle=list(restore_bundle),
                    scope_violations=list(violations),
                    error="the arrangement bundle left its declared scope; nothing was sent",
                ),
                is_error=True,
            )

        execution = run_commands(
            ToolCall(id=call.id, name="run_commands", arguments={"commands": list(commands)}),
            context,
        )
        gate_payload = json.loads(execution.result.content)
        gate_status = gate_payload.get("gate_status")
        executed = not execution.result.is_error
        payload = _arrange_payload(
            backup=[backup.to_dict() for backup in backups],
            restore_bundle=list(restore_bundle),
            commands=gate_payload.get("commands", []),
            walk=walk,
            executed=executed,
        )
        if gate_status is not None:
            payload["gate_status"] = gate_status
        if "notice" in gate_payload:
            payload["notice"] = gate_payload["notice"]
        if gate_status == _LOCKED:
            # The lock won a race against the probe above: the backup was read,
            # but not one write left. Still an ANSWER, not a failure.
            payload["status"] = "proposal"
            payload["succeeded"] = False
            payload["verified"] = False
            payload["proposed_commands"] = list(commands)
            return _arrange_result(payload, is_error=False, outcomes=execution.command_outcomes)
        if not executed:
            payload["status"] = "failed"
            payload["succeeded"] = False
            payload["verified"] = False
            payload["error"] = (
                "the arrangement bundle did not complete. run_commands stops on the "
                "first failure, so some targets may already have moved — run "
                "'restore_bundle' to put every target back where it was"
            )
            return _arrange_result(payload, is_error=True, outcomes=execution.command_outcomes)

        # @MX:WARN: [MANUAL] `ok: true` from the console is NOT evidence that a
        #   coordinate was stored. This re-query is the only evidence there is.
        # @MX:REASON: REQ-SPATIAL-021 / AC-SPATIAL-020, live-measured on onPC
        #   2.4.2 (progress.md §E.2.6a): of five write forms probed, THREE
        #   answered OK while storing the wrong value or nothing at all — a
        #   dropped minus sign, a silent no-op and a 0.0. Delete this block and
        #   the tool reports success for a rig it never moved, with a report
        #   that looks identical to a correct one. The comparison is NUMERIC
        #   with a tolerance and must stay that way: the console stores float32,
        #   so a correct 9.9 reads back as 9.8999996185303 and string equality
        #   would fail it.
        readback: list[dict[str, object]] = []
        mismatches: list[dict[str, object]] = []
        for placement, backup in zip(plan.placements, backups, strict=True):
            raw, values, failure = _arrange_read(backup.slot)
            if failure is not None:
                mismatches.append({"fid": placement.fid, "reason": failure})
                continue
            entry: dict[str, object] = {"fid": placement.fid}
            for index, (attribute, axis_property) in enumerate(ARRANGE_AXES):
                expected = float(getattr(placement, attribute))
                actual = values[index]
                entry[attribute] = actual
                if not arrange_values_match(expected, actual):
                    mismatches.append(
                        {
                            "fid": placement.fid,
                            "axis": axis_property,
                            "expected": expected,
                            "actual": actual,
                            "raw": raw[index],
                            "reason": "the console reported OK but stored a different value",
                        }
                    )
            readback.append(entry)
        payload["readback"] = readback
        payload["verified"] = not mismatches
        payload["succeeded"] = not mismatches
        payload["status"] = "arranged" if not mismatches else "verification_failed"
        payload["tolerance"] = {
            "relative": ARRANGE_VERIFY_REL_TOLERANCE,
            "absolute": ARRANGE_VERIFY_ABS_TOLERANCE,
        }
        if mismatches:
            payload["mismatches"] = mismatches
            payload["error"] = (
                f"{len(mismatches)} coordinate(s) did not read back as written — the "
                "console answered OK but the rig does not hold the requested "
                "arrangement. Run 'restore_bundle' to put every target back where it was"
            )
        return _arrange_result(
            payload, is_error=bool(mismatches), outcomes=execution.command_outcomes
        )

    # -- classify_arrangement_topology (SPEC-COPILOT-GROUPGEN-001 M1/M2/M3, --
    #    REQ-GROUPGEN-028 read half — design.md §8) --------------------------
    #
    # READS ONLY: reuses the same patch enumeration `get_spatial_context` does
    # (`read_spatial_fixtures`), then runs the pure `topology.classify()` +
    # `naming.py` + `fixture_type.py` modules over the result. No command is
    # composed and `execution_port`/`bundle_gate` are never reached — the
    # safety gate has nothing to screen here (decision D-4, arrange_fixtures'
    # own precedent for splitting a read tool from its write sibling).

    def _name_topology_buckets(result: TopologyResult) -> list[dict[str, object]]:
        """The selected topology's buckets, named (design.md §4) — a NAMING
        PROPOSAL, never a write. ``bilateral_pairs`` is reported as a property
        only (§5.3, contract D-Q10: the group-write path never consumes it),
        so it is never turned into a suggested group here, and neither is an
        unconfident/``None`` result — there is no structure to name."""
        if result.kind == "grid":
            axes = result.grid_axes or {}
            depth_buckets = axes.get("depth", ())
            lateral_buckets = axes.get("lateral", ())
            groups = [
                {"name": name_depth_bucket(index, len(depth_buckets)), "fids": list(fids)}
                for index, fids in enumerate(depth_buckets)
            ]
            groups.extend(
                {"name": name_lateral_bucket(index, len(lateral_buckets)), "fids": list(fids)}
                for index, fids in enumerate(lateral_buckets)
            )
            return groups
        namer = {
            "depth_rows": name_depth_bucket,
            "lateral_split": name_lateral_bucket,
            "concentric": name_concentric_bucket,
            "vertical_levels": name_vertical_bucket,
        }.get(result.kind)
        if namer is None or result.low_confidence:
            return []
        total = len(result.fids_by_bucket)
        return [
            {"name": namer(index, total), "fids": list(fids)}
            for index, fids in enumerate(result.fids_by_bucket)
        ]

    def _topology_result_to_dict(result: TopologyResult) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": result.kind,
            "low_confidence": result.low_confidence,
            "reason": result.reason,
            "fids_by_bucket": [list(bucket) for bucket in result.fids_by_bucket],
        }
        if result.grid_axes is not None:
            payload["grid_axes"] = {
                axis: [list(bucket) for bucket in buckets]
                for axis, buckets in result.grid_axes.items()
            }
        return payload

    def classify_arrangement_topology(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        fixtures_path = rig_paths.get("fixtures")
        if not fixtures_path:
            return _error_result(
                call,
                "rig context has no 'fixtures' path configured — arrangement "
                "topology cannot be classified without the stage patch",
            )
        if property_port is None:
            return _error_result(
                call,
                "property reads are not wired — build_toolset needs property_port "
                "(or a state_port that also implements query_property)",
            )
        try:
            reply = read_spatial_fixtures(
                state_port, property_port, fixtures_path, SPATIAL_PROPERTY_QUERY_CAP
            )
        except Exception as exc:
            return _error_result(
                call, f"stage patch enumeration failed for {fixtures_path!r}: {exc}"
            )
        # The read reply now comes in TWO shapes (REQ-TRUNCATE-001/002): a
        # complete read carries `fixtures`, a partial one carries
        # `partial_fixtures` and NO `fixtures` key at all. This handler is the
        # ONE in-process consumer of that reply, migrated in the same window
        # (REQ-TRUNCATE-007) — and the KeyError a shape-blind reader would
        # take here is the enforcement working in-process, not an accident to
        # paper over with `.get(...)`. Both shapes hold the SAME kind of
        # record; what differs is whether the list is the whole rig, and the
        # coverage read below is where that difference is already handled.
        records = reply["partial_fixtures"] if "partial_fixtures" in reply else reply["fixtures"]
        try:
            fixtures = spatial_fixtures_from_records(records)  # type: ignore[arg-type]
        except SpatialAnalysisError as error:
            return _error_result(call, f"fixture coordinates could not be parsed: {error}")

        classification = classify_topology(fixtures)

        # REQ-GROUPGEN-024 amendment (2026-08-04) — the DISCRIMINATE-path
        # guard: a topology judged from a partial rig read must be marked
        # low-confidence structurally, never silently treated as
        # authoritative. This is entirely SEPARATE from the WRITE path
        # (create_arrangement_groups / build_group_write_plan), which is
        # unaffected by rig-listing truncation because it consumes
        # caller-supplied fids, not this container listing.
        coverage = reply.get("coverage") or {
            "judged": len(fixtures),
            "of": len(fixtures),
            "complete": True,
        }
        topology_partial = not bool(coverage.get("complete", False))
        topology_partial_reason = (
            "the topology judgment above is based on a PARTIAL rig read "
            f"({coverage.get('judged')} of {coverage.get('of')} fixtures) — "
            "the container listing was truncated or the per-fixture property "
            "walk was budget-capped, so 'topology.selected' is NOT "
            "authoritative for the full rig; treat it as a low-confidence "
            "hint pending a follow-up read"
            if topology_partial
            else ""
        )

        # Geometric-axis groups (design.md §4 GEO prefix) are DERIVED from
        # the same partial-rig read as the topology judgment above, so they
        # carry "axis": "geometry" + the SAME topology_partial annotation.
        suggested_groups: list[dict[str, object]] = [
            {**group, "axis": "geometry", "topology_partial": topology_partial}
            for group in _name_topology_buckets(classification.selected)
        ]

        fixture_type_records = call.arguments.get("fixture_type_records")
        fixture_type_payload: dict[str, object] | None = None
        if fixture_type_records is not None:
            if not isinstance(fixture_type_records, list):
                return _error_result(
                    call,
                    "'fixture_type_records' must be a list of "
                    "{'fid', 'manufacturer', 'type_name'} records",
                )
            try:
                type_analysis = analyze_fixture_type_records(fixture_type_records)
            except FixtureTypeAnalysisError as error:
                return _error_result(call, f"'fixture_type_records' could not be parsed: {error}")
            fixture_type_payload = fixture_type_analysis_to_dict(type_analysis)
            # Species groups reuse the patch's own structured field as the name
            # verbatim (design.md §4.1 "종류" row / §5.1 REQ-GROUPGEN-009) — no
            # "GEO " prefix, which is reserved for the geometric axes (§D-Q3).
            # "axis": "species" — the caller supplies fixture_type_records
            # directly, so these groups are UNRELATED to rig-read coverage;
            # they never carry a "topology_partial" key (there is nothing
            # partial about a caller-supplied record list).
            suggested_groups = [
                *suggested_groups,
                *(
                    {"name": group["value"], "fids": list(group["fids"]), "axis": "species"}
                    for group in fixture_type_payload["type_axis_groups"]
                ),
            ]

        payload = {
            "source": "topology",
            "truncated": reply.get("truncated", False),
            "roundtrip_capped": reply.get("roundtrip_capped", False),
            "unreadable": reply.get("unreadable", []),
            "coverage": coverage,
            "topology_partial": topology_partial,
            "topology_partial_reason": topology_partial_reason,
            "topology": {
                "selected": _topology_result_to_dict(classification.selected),
                "candidates": [
                    _topology_result_to_dict(candidate) for candidate in classification.candidates
                ],
                "partial": topology_partial,
                "partial_reason": topology_partial_reason,
            },
            "fixture_types": fixture_type_payload,
            "suggested_groups": suggested_groups,
            "notice": (
                "suggested_groups is a NAMING PROPOSAL only — nothing was sent to "
                "the console. Pass a chosen subset as 'groups' to "
                "create_arrangement_groups to actually write it, which itself "
                "requires explicit human approval before anything is stored."
            ),
        }
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=False,
            )
        )

    # -- create_arrangement_groups (REQ-GROUPGEN-028 write half — design.md ---
    #    §6/§7/§10 policy (c)) --------------------------------------------------
    #
    # The ONE order this tool may run in (design.md §7.2), and none of it is
    # negotiable:
    #
    #   build_group_write_plan(...)         # pure assembly (server/groupgen/write.py)
    #     -> approval_port.request_approval  # the ONLY route to a console send
    #       -> not approved -> SEND NOTHING, return the plan only (fail-closed)
    #       -> approved -> fire via run_commands (gate/LiveLock/dedupe/audit inherited)
    #         -> re-query slot existence + label (never membership — policy (c))
    #
    # [HARD] structural enforcement (design.md §7.2): there is no code path to
    # `run_commands` below that does not pass through
    # `group_approval.request_approval(...)` first and observe `True` — no
    # argument short-circuits it, and `server/safety/**` stays byte-diff 0
    # (Store Group/Label Group are classified "safe" there and would otherwise
    # never see ANY approval stage). Deleting the approval check is a RED
    # mutation, not a silent behavior change.

    # Why the acknowledgement is an ENUMERATION and not a boolean — read this
    # before touching the checks below.
    #
    # `classify_arrangement_topology` has stamped every geometric group with
    # `topology_partial` since the GROUPGEN-024 amendment (2026-08-04), and
    # this handler read it ZERO times: the flag rode all the way into a
    # console write and did nothing. Closing that hole with a boolean
    # (`acknowledge_partial: true`) would have reproduced the exact defect
    # this SPEC exists to close — a boolean beside the data gets filled in
    # reflexively, without reading what is missing, which is precisely how
    # `truncated: true` was ignored on the measured 18-of-19 read. An
    # ENUMERATION cannot be produced without reading the reply: naming the
    # fids a read never saw means looking at `missing` and at the fixtures
    # that did arrive. A SPEC whose thesis is "an instruction is not an
    # enforcement mechanism" has to hold its OWN acknowledgement to that bar.
    def _unread_acknowledgement_refusal(
        acknowledged: object,
        partial_group_names: Sequence[str],
        write_fids: frozenset[int],
        shortfall: int | None,
    ) -> str | None:
        """Why this acknowledgement is not one — or ``None`` when it is valid."""
        named = ", ".join(repr(name) for name in partial_group_names)
        if not isinstance(acknowledged, list) or not acknowledged:
            return (
                f"{named} came from a PARTIAL rig read (topology_partial: true). "
                "Writing them needs 'acknowledged_unread_fids': a non-empty list "
                "of the fixture ids that read never saw. There is no boolean "
                "acknowledgement here — name them. get_spatial_context's "
                "'missing' says how many are unseen and 'partial_fixtures' says "
                "which ones did arrive."
            )
        if not all(isinstance(fid, int) and not isinstance(fid, bool) for fid in acknowledged):
            # `True` IS an `int` in Python, so this bool exclusion is the one
            # line that refuses a boolean wearing a list: delete it and
            # `[True]` passes as an enumeration of one fixture id, which is
            # the reflexive acknowledgement this whole argument shape exists
            # to prevent.
            return (
                "'acknowledged_unread_fids' must hold fixture ids as integers. A "
                "boolean is not a fixture id, and it is not an acknowledgement "
                "either."
            )
        if len(set(acknowledged)) != len(acknowledged):
            return (
                "'acknowledged_unread_fids' names the same fid more than once — "
                "an unseen fixture is unseen once, and a repeat inflates the "
                "count checked against the shortfall."
            )
        overlap = sorted(write_fids.intersection(acknowledged))
        if overlap:
            return (
                f"'acknowledged_unread_fids' names {overlap}, which this same "
                "call is writing into a group. A fixture you are grouping is one "
                "the read DID see — the enumeration is for the ones it did not, "
                "which is why it cannot be produced without reading the list."
            )
        if shortfall is not None and len(acknowledged) != shortfall:
            return (
                f"'acknowledged_unread_fids' names {len(acknowledged)} fixture "
                f"id(s), but the fixture container reports {shortfall} unseen. "
                "Acknowledge exactly the fixtures that are missing — if the "
                "container now lists the whole rig, re-run "
                "classify_arrangement_topology and write its fresh groups "
                "instead."
            )
        return None

    def create_arrangement_groups(call: ToolCall, context: ExecutionContext) -> ToolExecution:
        groups_arg = call.arguments.get("groups")
        if (
            not isinstance(groups_arg, list)
            or not groups_arg
            or not all(
                isinstance(entry, Mapping)
                and isinstance(entry.get("name"), str)
                and entry.get("name")
                and isinstance(entry.get("fids"), list)
                and entry.get("fids")
                and all(
                    isinstance(fid, int) and not isinstance(fid, bool)
                    for fid in entry.get("fids", [])
                )
                for entry in groups_arg
            )
        ):
            return _error_result(
                call,
                "'groups' must be a non-empty list of {'name': str, 'fids': "
                "[int, ...]} entries — the groups to Store and Label",
            )

        groups_path = rig_paths.get("groups")
        fixtures_path = rig_paths.get("fixtures")
        if not groups_path or not fixtures_path:
            return _error_result(
                call,
                "rig context has no 'groups'/'fixtures' path configured — a "
                "group write needs both the group pool and the fixture "
                "container to measure an empty slot",
            )

        buckets = {str(index): tuple(entry["fids"]) for index, entry in enumerate(groups_arg)}
        names = {str(index): entry["name"] for index, entry in enumerate(groups_arg)}

        sections, _resolved, _failed = collect_rig_sections(
            state_port, {"groups": groups_path, "fixtures": fixtures_path}, frozenset(), 0
        )
        groups_section = sections["groups"]
        fixtures_section = sections["fixtures"]

        # @MX:ANCHOR: [SPEC] the partial-read write refusal
        #   (SPEC-COPILOT-TRUNCATE-001 REQ-TRUNCATE-008 / AC-TRUNCATE-008,
        #   mutation-required). Deleting this block restores the measured hole:
        #   a group derived from a rig the tool never fully saw is written
        #   without anybody naming what was missed.
        # @MX:REASON: Placed AFTER the rig sections are read — they are the
        #   shortfall's only source — and BEFORE the plan is built, so a
        #   refusal costs exactly the two READS this call already makes and
        #   reaches neither the approval card nor the console. The truthiness
        #   test is deliberate rather than `is True`: fail-closed, an
        #   unexpected value refuses. Species groups carry no
        #   `topology_partial` key at all and are unaffected, and a group
        #   flagged False passes straight through — this gate demands reading,
        #   not abstinence.
        partial_group_names = [
            entry["name"] for entry in groups_arg if entry.get("topology_partial")
        ]
        if partial_group_names:
            fixtures_total = fixtures_section.get("total")
            arrived = len(fixtures_section.get("objects") or [])  # type: ignore[arg-type]
            refusal = _unread_acknowledgement_refusal(
                call.arguments.get("acknowledged_unread_fids"),
                partial_group_names,
                frozenset(fid for entry in groups_arg for fid in entry["fids"]),
                # `total` is None when the responder reported no childCount —
                # `rig_section`'s unknown-total rule. The size check simply
                # does not apply then; the other three still do.
                max(fixtures_total - arrived, 0) if isinstance(fixtures_total, int) else None,
            )
            if refusal is not None:
                return _error_result(call, refusal)

        try:
            plan = build_group_write_plan(
                buckets=buckets,
                names=names,
                groups_section=groups_section,
                fixtures_section=fixtures_section,
            )
        except GroupSlotError as error:
            return _error_result(call, f"{error.code}: {error.message}")
        except ValueError as error:
            return _error_result(call, str(error))

        # [HARD] ONE run_commands bundle PER GROUP — never one bundle for the
        # whole plan. `run_commands` folds a line that already succeeded in the
        # same bundle into `skipped_already_executed`, and a group chain's
        # SELECTION line is NOT dedupe-exempt (only a single bare
        # `Fixture <operand>` is; `Fixture 1 + Fixture 2 + Fixture 3` is not —
        # `_is_programmer_state` above). Two groups over the same fids — which
        # `classify_arrangement_topology` produces on any rig whose
        # manufacturer:model mapping is 1:1, because `type_axis_groups` then
        # emits byte-identical fid tuples for two axes — would therefore lose
        # the SECOND group's selection, and `Store Group N` would fire against
        # the programmer its own leading `ClearAll` just emptied. The console
        # answers ok either way and membership is unreadable
        # (progress.md §E.2.8), so the human would have approved one plan and
        # the console would have received another, undetectably.
        #
        # `bundles` is the ONE definition of what gets fired; the guard below
        # and the execution loop both consume it, so re-concatenating the plan
        # cannot slip past the guard.
        bundles = [(step, list(step.commands)) for step in plan.steps]
        all_commands = [command for _step, bundle in bundles for command in bundle]
        # exec 큰따옴표 금지 계승 — write.py already refuses a double-quoted
        # name (`_label_command`), so this is a static re-assertion over the
        # assembled text on its way to the gate, not a belief about the
        # builder that produced it (same shape as arrange_fixtures' own
        # `arrange_scope_violations` seal).
        assert all('"' not in command for command in all_commands)
        # The same shape of re-assertion for the dedupe hazard, against the
        # exact lists that will be fired (write.py already guarded each step
        # it built — this re-checks the BUNDLING, which is this layer's call).
        try:
            for _step, bundle in bundles:
                guard_bundle_collision(bundle)
        except GroupSlotError as error:
            return _error_result(call, f"{error.code}: {error.message}")

        def _plan_payload(**extra: object) -> dict[str, object]:
            payload: dict[str, object] = {
                "plan": [
                    {
                        "slot": step.slot,
                        "name": step.name,
                        "fids": list(step.fids),
                        "commands": list(step.commands),
                        "verification": list(step.verification),
                    }
                    for step in plan.steps
                ],
                # Policy (c), design.md §10 — a STRUCTURAL field, never prose:
                # `unverified` always carries "membership" (write.py already
                # guarantees this), so a caller cannot lose the caveat by
                # skipping a docstring (함정 6).
                "unverified": list(plan.unverified),
                "unverified_reason": plan.unverified_reason,
                "human_check_commands": list(plan.human_check_commands),
                # REQ-GROUPGEN-024 amendment (2026-08-04) — a STRUCTURAL
                # notice, never docstring-only prose (함정 6): a truncated
                # re-queried fixture listing never blocks this write (the
                # group's membership is the caller's explicit fids), but the
                # fact is still surfaced here for a human reviewer.
                "fixture_list_truncated": plan.fixture_list_truncated,
                "fixture_list_truncated_reason": plan.fixture_list_truncated_reason,
            }
            payload.update(extra)
            return payload

        approval_request = ApprovalRequest(
            items=tuple(
                ApprovalItem(
                    command=command,
                    risk_reasons=(
                        "group write — membership cannot be re-verified after "
                        "Store (grandMA3 exposes no membership read channel, "
                        "progress.md §E.2.8)",
                        *(
                            (plan.fixture_list_truncated_reason,)
                            if plan.fixture_list_truncated
                            else ()
                        ),
                    ),
                )
                for command in all_commands
            )
        )
        approved = group_approval.request_approval(approval_request)
        if not approved:
            # Fail-closed (design.md §7.2 ②③): approval withheld, unconfirmed
            # or the port itself absent (DenyAllApprovalPort) all converge
            # here — ZERO console sends, the plan demoted to a proposal.
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        _plan_payload(
                            status="proposal",
                            executed=False,
                            notice=(
                                "approval was not granted — nothing was sent to the "
                                "console. Re-call with the same 'groups' once a human "
                                "has approved the plan above."
                            ),
                        ),
                        ensure_ascii=False,
                    ),
                    # A withheld approval is an ANSWER, not a failure (same
                    # shape as arrange_fixtures' LiveLock demotion) — it must
                    # not feed the self-correction loop back into re-asking
                    # for the same approval.
                    is_error=False,
                )
            )

        # Approval was ONE request over the whole plan (the human saw every
        # line at once); only the FIRING is split. Each bundle gets a FRESH
        # context: `ExecutionContext.executed_ok` accumulates across every tool
        # call in one instruction turn (server/orchestrator/runner.py:216,
        # 222-223), so a selection line an earlier call already fired — a
        # self-correction retry (REQ-MVP-012) is enough — would be folded out
        # of a group chain even when this call asks for a single group. A group
        # chain opens AND closes with `ClearAll`, so it depends on no state a
        # previous tool call established; a fresh context is therefore safe as
        # well as necessary.
        outcomes: list[CommandOutcome] = []
        command_reports: list[dict[str, object]] = []
        slot_outcomes: list[dict[str, object]] = []
        failure: dict[str, object] | None = None
        for step, bundle in bundles:
            if failure is not None:
                # Stop-on-first-failure, inherited across bundles: a later
                # group is never written on top of a broken one, and its
                # slot is reported as untouched rather than omitted.
                for command in bundle:
                    outcomes.append(
                        CommandOutcome(
                            command=command,
                            status="not_executed",
                            detail="not executed (an earlier group's bundle failed)",
                        )
                    )
                    command_reports.append(
                        {
                            "command": command,
                            "status": "not_executed",
                            "detail": "not executed (an earlier group's bundle failed)",
                        }
                    )
                slot_outcomes.append(
                    {"slot": step.slot, "name": step.name, "status": "not_attempted"}
                )
                continue
            execution = run_commands(
                ToolCall(id=call.id, name="run_commands", arguments={"commands": bundle}),
                _EMPTY_CONTEXT,
            )
            bundle_payload = json.loads(execution.result.content)
            outcomes.extend(execution.command_outcomes)
            # Passed through verbatim rather than re-serialized from
            # `outcomes`: a gate block reports `reasons` (a list), not `detail`.
            command_reports.extend(bundle_payload.get("commands", []))
            if execution.result.is_error:
                failure = bundle_payload
                slot_outcomes.append({"slot": step.slot, "name": step.name, "status": "failed"})
            else:
                slot_outcomes.append({"slot": step.slot, "name": step.name, "status": "executed"})

        if failure is not None:
            written = [entry for entry in slot_outcomes if entry["status"] == "executed"]
            return ToolExecution(
                result=ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content=json.dumps(
                        _plan_payload(
                            status="failed",
                            # "the write completed as planned" — never "nothing
                            # reached the console". `slot_outcomes` carries the
                            # per-slot truth so a partial write cannot read as
                            # either a clean success or a clean no-op.
                            executed=False,
                            partial_write=bool(written),
                            slot_outcomes=slot_outcomes,
                            gate_status=failure.get("gate_status"),
                            notice=failure.get("notice"),
                            commands=command_reports,
                            error=(
                                "the group write stopped at the first failing bundle — "
                                f"{len(written)} of {len(bundles)} group slots were "
                                "written before it; see 'slot_outcomes' for which, and "
                                "'commands' for the per-command gate/execution outcome. "
                                "A written slot is NOT rolled back: grandMA3 exposes no "
                                "membership read channel (progress.md §E.2.8), so a "
                                "human must check the slots marked 'executed'."
                            ),
                        ),
                        ensure_ascii=False,
                    ),
                    is_error=True,
                ),
                command_outcomes=tuple(outcomes),
            )

        # Re-query evidence (design.md §10 policy (c) automated-verification
        # layer): slot existence and the LABEL, never membership. `ok:true`
        # from the write above is NOT evidence — only this re-query is.
        verified_steps: list[dict[str, object]] = []
        for step in plan.steps:
            slot_path = f"{groups_path}/{step.slot}"
            try:
                snapshot = state_port.query_state(slot_path)
                slot_exists = bool(snapshot)
            except Exception:
                slot_exists = False
            name_verified: bool | None = None
            if property_port is not None:
                try:
                    name_read = read_properties(property_port, slot_path, ("Name",))["Name"]
                    name_verified = name_read.ok and str(name_read.value).strip() == step.name
                except Exception:
                    name_verified = False
            verified_steps.append(
                {
                    "slot": step.slot,
                    "name": step.name,
                    "fids": list(step.fids),
                    "slot_exists": slot_exists,
                    "name_verified": name_verified,
                }
            )

        succeeded = all(
            entry["slot_exists"] and entry["name_verified"] is not False for entry in verified_steps
        )
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(
                    _plan_payload(
                        status="created" if succeeded else "verification_failed",
                        executed=True,
                        succeeded=succeeded,
                        verified_steps=verified_steps,
                        commands=command_reports,
                    ),
                    ensure_ascii=False,
                ),
                is_error=not succeeded,
            ),
            command_outcomes=tuple(outcomes),
        )

    definitions = (
        ToolDefinition(
            name="run_commands",
            description=(
                "Execute MA3 command lines on the console, in order. Call this to "
                "carry out the user's instruction once you know the exact commands. "
                "Execution stops at the first failing command; the result reports "
                "each command's status (executed_ok / failed / not_executed / "
                "skipped_already_executed)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "MA3 command lines, one command per entry.",
                    }
                },
                "required": ["commands"],
            },
        ),
        ToolDefinition(
            name="query_state",
            description=(
                "Read a console object-tree snapshot (e.g. 'DataPool/Sequences'). "
                "Call this when you need current console state before deciding on "
                "commands."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Object-tree path, e.g. 'DataPool/Sequences'.",
                    }
                },
                "required": ["path"],
            },
        ),
        ToolDefinition(
            name="deploy_plugin",
            description=(
                "Deploy a Lua 5.4 plugin to the console. The source is compile-"
                "checked (a compile error comes back for correction), scanned "
                "for destructive Cmd() content, and shown to a human reviewer "
                "who must approve the deployment before anything reaches the "
                "console. A rejection is a final human decision — do not retry."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plugin name."},
                    "lua_source": {"type": "string", "description": "Lua 5.4 source code."},
                },
                "required": ["name", "lua_source"],
            },
        ),
        ToolDefinition(
            name="get_rig_context",
            description=(
                "Build a picture of THIS showfile — call this FIRST, before "
                "designing any look, and whenever the instruction uses venue/"
                "field terms (e.g. Korean field vocabulary) that must resolve "
                "to actual objects. One call covers everything a lighting "
                'instruction is made of: "fixture_types" (patched fixture '
                'types), "fixtures" (the stage\'s patched fixtures), "groups" '
                '(the group pool — what to select), "sequences" (stored cue '
                'lists — what a look is stored INTO), "preset_pools" (the '
                "preset TYPES — Dimmer, Position, Gobo, Color, ... — with each "
                'pool\'s STORED CONTENTS opened inline, see "contents" below), '
                '"macros" and "plugins" (what already automates this show), '
                '"pages" (executor pages — the ONLY surface that actually '
                'FIRES a stored look: each page\'s "objects" already lists its '
                'executors, e.g. Sequence 30 sitting on Executor 5), "matricks" '
                'and "worlds" (selection-shaping vocabulary).\n'
                "\n"
                'Each section is {"objects": [...], "truncated": bool, "total": '
                "<real count, or null if unknown>}. truncated=true means the "
                "responder cut the list short — total names the REAL count, so "
                "you know the objects you have are NOT everything; never treat "
                "a truncated list as complete.\n"
                "\n"
                'Each object is {"no": <number>, "name": <name>}; ALWAYS '
                'reference it by its REAL "no", NEVER by positional order — '
                "numbers may be non-contiguous (e.g. 1, 2, 7), so the Nth "
                "listed item is NOT necessarily object N. An entry with a "
                '"name" but NO "no" means its number is UNKNOWN: do not guess '
                "one — resolve it with query_state before addressing that "
                "object. For groups, sequences, macros, plugins and pages the "
                '"no" IS the address you use (e.g. Group 2, Sequence 5). For '
                'fixtures the "no" is the fixture\'s slot in the stage patch '
                "list and is NOT guaranteed to be its fixture id (FID) — "
                "confirm the FID with query_state before addressing a fixture "
                "by number.\n"
                "\n"
                'In "preset_pools" and "pages", each object additionally '
                'carries "contents": the pool\'s stored presets, or the '
                "page's executors, already fetched — an empty list means "
                "VERIFIED empty (nothing stored yet), not unknown. "
                '"contents_unavailable": true means that ONE object could not '
                "be opened (console busy or the object vanished) — its "
                "contents are genuinely unknown, distinct from a verified-"
                'empty pool. A section may also carry "drilldown_capped": '
                "true, meaning there were more objects than this call's "
                "per-request query budget allowed opening — the rest still "
                'have "no"/"name" but no "contents"; call query_state on '
                "those specific paths if you need them.\n"
                "\n"
                'A section may instead come back as {"reason": ...}: '
                '"path_not_resolved" means that vocabulary does not exist in '
                'THIS showfile (other sections answered), "console_unreachable" '
                "means nothing answered. In both cases you did NOT receive "
                "that vocabulary — say so and ask, never invent objects for it."
            ),
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="find_looks",
            description=(
                "Ask the built-in look library BEFORE inventing any colour or "
                "intensity — call this the moment an instruction names a mood, "
                "a genre or a song section rather than explicit values (e.g. "
                "'a grand golden chorus', 'a calm ballad intro', 'the EDM "
                "drop'). A stored look is a DESIGNED answer; the values you "
                "would otherwise pick are a guess at the same question, so "
                "designing a mood from scratch without asking here first is "
                "the one thing this tool exists to prevent.\n"
                "\n"
                "This is the VALUES half of a mood instruction and "
                "get_rig_context is the OBJECTS half — they do not compete, "
                "and a mood instruction needs BOTH: ask here for the look, "
                "then bind it to the real rig. Pass the operator's own words; "
                "Korean is first-class, and the genre may be written either "
                "way (워십 / worship, 록 / rock, 발라드 / ballad, EDM).\n"
                "\n"
                "This tool READS ONLY — it never sends anything to the "
                'console. Each match is {"look_id", "display_name", "genre", '
                '"dynamics" (1 static .. 5 climax), "roles" (position roles, '
                'NOT rig objects), "attributes" (concrete values), "score" and '
                '"matched" (the library words your query hit)}. The list is '
                'ranked; "total" and "truncated" say whether it was cut '
                "short.\n"
                "\n"
                'When "fallback" is true NOTHING matched well enough — '
                '"no_match" (nothing answered), "low_confidence" (several '
                'looks tied and nothing narrows them) or "empty_query". In '
                "that case do NOT pick from the list: fall back to designing "
                "the mood yourself from the rulebook's mood table. The library "
                "never invents a look, and neither should you.\n"
                "\n"
                "A look carries NO group number, preset slot or fixture id. To "
                "put one on THIS rig, resolve its roles against "
                "get_rig_context and store it with run_commands."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The mood / genre / section wording to match, in "
                            "the operator's own language."
                        ),
                    }
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="instantiate_look",
            description=(
                "Put a look FROM find_looks onto THIS rig. Pass the look_id of "
                "the match you chose; do NOT hand-write the bundle with "
                "run_commands, because this tool is the only thing that binds "
                "a look's position roles to the rig's real groups.\n"
                "\n"
                "It reads the rig itself — the current groups and preset pools "
                "— so you do not pass any rig data in, and you must not retype "
                "anything from get_rig_context: every group and pool number it "
                "puts on the command line comes from the console on THIS call. "
                "It then stores ONE preset per in-scope pool (Dimmer, Color, "
                "and Beam / Focus when the look has those values), labels each "
                "one with the look's name, and runs the whole bundle through "
                "the SAME execution path as run_commands — so the live lock, "
                "the safety screening and the approval gate all apply "
                "unchanged.\n"
                "\n"
                "It creates PRESETS ONLY. It does not create a cue, a sequence "
                "or an executor assignment, so nothing is left running on "
                "stage. If the operator needs something they can fire, build "
                "that afterwards with run_commands, recalling the presets this "
                "tool reports.\n"
                "\n"
                'The result carries "executed", a per-command "commands" list '
                'exactly like run_commands, and a "report":\n'
                '- "created": every preset stored, with its pool, slot and '
                "label.\n"
                '- "unmapped": each position role the rig could NOT address, '
                'with a reason — "no_match" (no group named anything like it), '
                '"ambiguous" (a group name claimed by two roles) or '
                '"unaddressable" (a group matched but carries no number). An '
                "unmapped role emits NO command and gets NO substitute: report "
                "it to the operator, never aim it at another group.\n"
                '- "skipped": each preset store that did NOT happen, with its '
                'reason — "conflict" (that pool already holds a preset with '
                'this name), "no_free_slot" (occupancy was not observed, so no '
                'slot can be claimed free), "pool_unresolved" (this rig has no '
                'pool of that type) or "pool_unaddressable" (it has one with '
                "no number). Nothing is ever overwritten and nothing is "
                "re-slotted; the unit is one preset store, so a look can be "
                "partly created and partly skipped.\n"
                '- "complete": false whenever anything was unmapped or '
                "skipped. Say so — never report a partial run as a whole one.\n"
                "\n"
                "An empty bundle (nothing executed, no created presets) means "
                "the rig addressed none of this look's roles. That is an "
                "answer, not a transient failure: do not retry it, report the "
                "unmapped roles instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "look_id": {
                        "type": "string",
                        "description": "The look_id of a find_looks match, copied verbatim.",
                    },
                    "capture_shape": {
                        "type": "string",
                        "enum": list(CAPTURE_SHAPES),
                        "description": (
                            "Optional. Leave unset — the default stores every "
                            "family from one capture. Use "
                            f"'{CAPTURE_PER_FAMILY}' only if a previous run "
                            "visibly over-captured (e.g. a Dimmer preset that "
                            "also holds the colour); it isolates one capture "
                            "cycle per family at the cost of a longer bundle."
                        ),
                    },
                },
                "required": ["look_id"],
            },
        ),
        ToolDefinition(
            name="prepare_busking",
            description=(
                "Prepare a busking palette for one genre: store the genre's whole "
                "look set as colour/position/beam/dimmer presets on THIS rig, in a "
                "single bundle needing one approval. Call this when the operator "
                "asks to get ready for a rock / ballad / worship / EDM set rather "
                "than to realise one specific look. The rig is read here — never "
                "pass groups, pools or slot numbers. Returns a two-tier report: "
                "totals plus a per-look verdict, so a partially stored palette says "
                "which look is missing and why."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "genre": {
                        "type": "string",
                        "description": (
                            "The operator's own word for the genre, Korean or "
                            "English (e.g. '록', 'ballad', '워십', 'EDM'). An "
                            "unrecognised word is answered with the genres this "
                            "library actually holds."
                        ),
                    },
                },
                "required": ["genre"],
            },
        ),
        ToolDefinition(
            name="prepare_songcue",
            description=(
                "Prepare one song-structure cue list on THIS rig. Provide the song "
                "title, genre, section names and section start times; the tool reads "
                "the current groups and sequences itself, maps sections through the "
                "look library, stores one Sequence with one Cue per section, adds the "
                "measured Timecode and TrigType/TrigTime commands, and sends the "
                "whole bundle through the same run_commands path as any direct "
                "console execution. Do not pass rig numbers or copied rig sections."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "song_title": {
                        "type": "string",
                        "description": "Song title used for the generated cue-list report.",
                    },
                    "genre": {
                        "type": "string",
                        "description": (
                            "The operator's own word for the genre, Korean or English "
                            "(e.g. '록', 'ballad', '워십', 'EDM')."
                        ),
                    },
                    "timecode_number": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Positive Timecode object number to create for this draft.",
                    },
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": (
                                        "Section name, such as Intro, Verse, Chorus or Drop."
                                    ),
                                },
                                "start": {
                                    "description": "Start time as mm:ss, mm:ss.mmm, or seconds.",
                                },
                                "dynamics": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 5,
                                    "description": (
                                        "Optional explicit dynamics for section names the library "
                                        "does not recognise."
                                    ),
                                },
                            },
                            "required": ["name", "start"],
                        },
                        "description": (
                            "Song sections in input order. The tool rejects duplicate or "
                            "backward start times instead of sorting them."
                        ),
                    },
                    "explicit_dynamics": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                        },
                        "description": (
                            "Optional map from zero-based section index to explicit dynamics "
                            "for unknown section names."
                        ),
                    },
                },
                "required": ["song_title", "genre", "timecode_number", "sections"],
            },
        ),
        ToolDefinition(
            name="precheck_patch",
            description=(
                "Pre-show check of THIS rig's patch. Reads the patched fixtures and "
                "their addresses itself, reports every observed fixture plus the "
                "aggregate, and names address collisions, unreadable properties, "
                "enumeration completeness and any check it did NOT perform. Set "
                "create_macro to also author a response-check macro that turns each "
                "rig group on and off, sent through the same run_commands path as any "
                "direct console execution. When that bundle IS sent, one stored macro "
                'line is read back off the console and reported as "macro_requery" — a '
                'command receipt alone is not evidence of effect. "read": false there '
                "means the READ-BACK did not answer, so the store is UNCONFIRMED; it "
                "does NOT mean the macro is absent, and the authoring result stands "
                "unchanged. It does NOT decide whether a fixture "
                "answered — no console read reports that, so a human still has to "
                "watch the rig. Do not pass rig numbers: there are none to pass."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "create_macro": {
                        "type": "boolean",
                        "description": (
                            "Also author and run the response-check macro. Omit or set "
                            "false to report the patch without touching the showfile."
                        ),
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="preshow_check",
            description=(
                "Run the standard pre-show checklist in one pass: sequence/"
                "executor presence, preset (look) library integrity, and the "
                "project's known field pitfalls (stale OSC socket advisory, "
                "osc_slot Send=Yes row, feedback-port drift). Returns a "
                "traffic-light signal — green (every check passed), yellow "
                "(at least one check could not be verified — SKIP, never a "
                "silent pass), or red (at least one check failed). The live "
                "OSC round-trip and receive-port checks always report SKIP "
                "through this tool; run the operator-facing "
                "server/preshow/osc_check.py diagnostic separately for those. "
                "Takes no arguments."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="find_fx",
            description=(
                "Ask the built-in effect library BEFORE hand-writing any "
                "movement — call this the moment an instruction asks for "
                "something that MOVES or CHANGES OVER TIME rather than for a "
                "static picture (e.g. '좌우로 쓸어줘', 'a slow wave', 'make it "
                "pulse with the beat', 'fast colour chase'). find_looks is the "
                "STILL-PICTURE half of the vocabulary and this is the MOTION "
                "half; an instruction can need both.\n"
                "\n"
                "Every entry here carries a step pair — a phaser only exists "
                "once two steps hold different values — plus its phase and "
                "speed. A phaser you write yourself from one value and a Phase "
                "line is accepted by the console with ok:true and does not "
                "move, which is why this library exists and why guessing is "
                "worse here than anywhere else.\n"
                "\n"
                "This tool READS ONLY — it never sends anything to the "
                'console. Each match is {"fx_id", "display_name", "pattern" '
                "(sweep / wave / circle / diagonal / pulse / chase), "
                '"attributes" (what moves), "speed" (BPM), "reverse", "score" '
                'and "matched" (the library words your query hit)}. The list '
                'is ranked; "total" and "truncated" say whether it was cut '
                "short.\n"
                "\n"
                'When "fallback" is true NOTHING matched well enough, and '
                '"fallback_reason" says which: "no_match" (nothing answered), '
                '"low_confidence" (several entries tied and nothing narrows '
                'them) or "empty_query" (nothing was asked). In that case do '
                "NOT pick from the list.\n"
                "\n"
                "A low_confidence answer is usually a whole pattern band — the "
                "operator named the shape ('원형으로', 'chase') but not which "
                "of that pattern's entries — so ask again with one more word "
                "from the operator, typically the speed ('빠른 체이스', 'slow "
                "circle'). If it still falls back, design the movement "
                "yourself from the rulebook's mood table (its movement "
                "column), the same fallback path a look fallback takes. The "
                "library never invents an effect, and neither should you.\n"
                "\n"
                "An fx carries NO group number, sequence number or executor. "
                "To put one on THIS rig, pass its fx_id to instantiate_fx."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The movement / mood wording to match, in the operator's own language."
                        ),
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="instantiate_fx",
            description=(
                "Put an effect FROM find_fx onto THIS rig as a sequence + cue. "
                "Pass the fx_id of the match you chose; do NOT hand-write the "
                "bundle with run_commands, because this tool is the only thing "
                "that emits the measured step grammar (values, then a "
                "standalone 'Step 2' line, then the next values, and only "
                "THEN the Phase / Speed lines). Written in any other order the "
                "console answers ok:true and the rig stands still.\n"
                "\n"
                "Apart from the fx_id, the group is the ONLY rig number you "
                "pass: give a group number get_rig_context listed on THIS rig "
                "— never a group you have not seen listed, and never a fixture "
                "slot, which is not a group and not a fixture id. Everything "
                "else is measured here: the tool re-reads the rig on this call, "
                "refuses a group this rig does not list, and picks a FREE "
                "sequence number from the pool it just read. Leave sequence "
                "unset unless the operator named one; pass executor only when "
                "the operator asked for one, because an executor is assigned "
                "to nothing by default. The whole bundle runs through the SAME "
                "execution path as run_commands, so the live lock, the safety "
                "screening and the approval gate all apply unchanged.\n"
                "\n"
                "It creates ONE sequence with ONE cue, and assigns an executor "
                "only if you passed one. It never overwrites an existing "
                "sequence.\n"
                "\n"
                'The result carries "succeeded", a per-command "commands" list '
                'exactly like run_commands, a Korean "summary_ko" for the '
                'operator, and a "report" whose "verdict" is one of:\n'
                '- "complete": every command ran.\n'
                '- "partial": something failed, and everything after it was '
                "not executed — both lists are in the report.\n"
                '- "planned": nothing was sent (the gate did not clear).\n'
                '- "cross_call_collision": lines this bundle shares with an '
                "EARLIER instantiation in the same instruction were dropped as "
                "already-executed, so the cue that got stored is INCOMPLETE. "
                "Report it as a failure and tell the operator the sequence may "
                "need deleting.\n"
                'Only "complete" is a success — never report a partial run '
                "as a whole one.\n"
                "\n"
                "Because of that last verdict, run ONE instantiate_fx per "
                "instruction. A second one in the same instruction folds from "
                "its very first line. If the operator wants two effects, do "
                "the second after they reply.\n"
                "\n"
                "Finally, and this holds even when every command came back "
                "ok: the effect itself cannot be verified by machine. The "
                "console reports that the commands were accepted, and a stored "
                "phaser cue reads back exactly like an empty one — no query "
                "returns its phase, its speed or its motion. So a human has to "
                "watch the stage. Say so; never present a receipt, or the "
                "existence of the sequence, as evidence that anything moved."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "fx_id": {
                        "type": "string",
                        "description": "The fx_id of a find_fx match, copied verbatim.",
                    },
                    "group": {
                        "type": "integer",
                        "description": (
                            "The group number to run the effect on, as listed "
                            "by get_rig_context on THIS rig."
                        ),
                    },
                    "sequence": {
                        "type": "integer",
                        "description": (
                            "Optional. Leave unset — a free number is measured "
                            "from the rig. Pass one only when the operator "
                            "named it; an occupied number is refused."
                        ),
                    },
                    "executor": {
                        "type": "integer",
                        "description": (
                            "Optional. Only when the operator asked for the "
                            "effect to sit on a specific executor. Nothing is "
                            "assigned automatically."
                        ),
                    },
                    "label": {
                        "type": "string",
                        "description": (
                            "Optional cue label. Defaults to the fx's own display name."
                        ),
                    },
                },
                "required": ["fx_id", "group"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="find_scene",
            description=(
                "Ask the built-in SCENE library when one instruction names a "
                "still picture AND a movement at once — '파란 백라이트가 천천히 "
                "웨이브하는 씬', 'a warm look that pulses with the beat'. A "
                "scene is ONE cue holding both: the look's values and the "
                "effect's step column, stored together.\n"
                "\n"
                "This is not a third vocabulary. A scene only REFERENCES a "
                "find_looks entry and a find_fx entry, so nothing here can be "
                "combined that those two libraries do not already hold.\n"
                "\n"
                "This tool READS ONLY — it never sends anything to the "
                'console. The answer carries the two axes SEPARATELY: "look" '
                'and "fx" each report what they matched, and "kind" is one of '
                '"both_matched", "look_only", "fx_only" or "fallback". A '
                "one-axis answer is a real answer — a look-only scene and an "
                "fx-only scene are both legal — but the axis that did NOT "
                "match is left empty on purpose. Do not fill it in yourself.\n"
                "\n"
                'When "fallback" is true there is nothing here to compile and '
                '"fallback_reason" says why. Four of the five are about the '
                'axes ("no_match", "low_confidence", "ambiguous", '
                '"empty_query"): ask the operator for one more word rather '
                "than picking from the list; if it still falls back, use "
                "find_looks and find_fx separately.\n"
                "\n"
                'The fifth is different — "no_scene_composes_axes" means both '
                "axes DID resolve but this library holds no scene combining "
                'them, so "selected_look_id" and "selected_fx_id" are still '
                "valid: take them to find_looks/find_fx and place the two "
                "halves separately, or ask the operator which one they "
                "meant.\n"
                "\n"
                "A scene carries NO group, sequence, cue or executor number. "
                "To put one on THIS rig, pass its scene_id to compile_scene."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The scene wording to match, in the operator's own language."
                        ),
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="compile_scene",
            description=(
                "Put a scene FROM find_scene onto THIS rig as ONE sequence "
                "with ONE cue holding the look AND the effect together. Pass "
                "the scene_id of the match you chose.\n"
                "\n"
                "Do NOT try to build this by calling instantiate_look and then "
                "instantiate_fx. That does not work and the failure is silent: "
                "the two tools store two different things (a preset and a "
                "sequence), and the second bundle of one instruction folds "
                "from its shared step lines onward, so a cue gets stored with "
                "values missing. This tool is the only path that emits both "
                "halves in ONE bundle, in the measured order — the look's "
                "values first, because the effect's first step IS the current "
                "programmer state, then the step column, then phase and "
                "speed.\n"
                "\n"
                "Apart from the scene_id, the group is the ONLY rig number you "
                "pass: give a group number get_rig_context listed on THIS rig "
                "— never a group you have not seen listed, and never a fixture "
                "slot, which is not a group and not a fixture id. Everything "
                "else is measured here: the tool re-reads the rig, refuses a "
                "group this rig does not list, and picks a FREE sequence "
                "number from the pool it just read. Leave sequence and cue "
                "unset unless the operator named them. It never overwrites an "
                "existing cue and never emits a store flag. The whole bundle "
                "runs through the SAME execution path as run_commands, so the "
                "live lock, the safety screening and the approval gate all "
                "apply unchanged.\n"
                "\n"
                'The result carries "succeeded", a per-command "commands" '
                'list exactly like run_commands, a Korean "summary_ko", and a '
                '"report" whose "verdict" is one of "complete", "partial", '
                '"planned" (nothing was sent) or "cross_call_collision" '
                "(lines shared with an earlier bundle in this instruction were "
                "dropped as already-executed, so the stored cue is "
                'INCOMPLETE). Only "complete" is a success. Run ONE '
                "compile_scene per instruction; a second one folds.\n"
                "\n"
                "The report keeps four claims APART, and so must you when you "
                "speak to the operator:\n"
                "- whether the cue EXISTS. When the bundle IS sent, the tool "
                "reads the sequence back and reports it as the report's "
                '"requery" — a command receipt alone is not evidence. Three '
                "outcomes, and they are DIFFERENT: a mapping under "
                '"requery" means the read found the cue and its name and '
                'cueNo are confirmed; "requery_error" means the READ did not '
                "answer, so existence is UNCONFIRMED — it does NOT mean the "
                'cue is absent; "requery_mismatch" means the read answered '
                "and did not confirm this cue — either it was not there or it "
                "arrived without the names the confirmation claims — which is "
                "still not a claim of absence. In the last two the authoring "
                "result stands unchanged, the report says so in its own "
                "sentence, and existence stays UNCONFIRMED. Nothing is read "
                "back when the bundle was not sent (a gate hold, a live-lock "
                "proposal or a failed line). One case reads back even though "
                'THIS call sent nothing: a "cross_call_collision", where an '
                "earlier bundle in the same instruction already stored the "
                "cue — the read then confirms THAT cue, so report the "
                "collision verdict alongside it and never as this call's "
                "store;\n"
                "- the value line carried the uniform attribute set (checked "
                "in the emitted text);\n"
                "- the EFFECT — the motion, the colour on stage — cannot be "
                "verified by machine at all. A human has to watch;\n"
                '- "unclaimed_attributes" lists what this scene does NOT set. '
                "Those axes MAY still hold a previous scene's value. Say "
                '"may" — nothing can observe whether they did.\n'
                "Never present the receipt, or the existence of the cue, as "
                "evidence that anything moved or that tracking was handled."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "scene_id": {
                        "type": "string",
                        "description": "The scene_id of a find_scene match, copied verbatim.",
                    },
                    "group": {
                        "type": "integer",
                        "description": (
                            "The group number to build the scene on, as listed "
                            "by get_rig_context on THIS rig."
                        ),
                    },
                    "sequence": {
                        "type": "integer",
                        "description": (
                            "Optional. Leave unset — a free number is measured "
                            "from the rig. An occupied number is refused."
                        ),
                    },
                    "cue": {
                        "type": "integer",
                        "description": (
                            "Optional whole cue number. Leave unset unless the "
                            "operator named one; decimals are not supported."
                        ),
                    },
                    "trig_type": {
                        "type": "string",
                        "description": (
                            "Optional cue trigger, Capitalized: Go, Time, "
                            "Follow, Sound or BPM. Lowercase is refused."
                        ),
                    },
                    "trig_time": {
                        "type": "number",
                        "description": (
                            "Optional trigger time in seconds, measured from "
                            "the START of the sequence (not from the previous "
                            "cue). Zero is allowed."
                        ),
                    },
                    "executor": {
                        "type": "integer",
                        "description": (
                            "Optional. Only when the operator asked for the "
                            "scene to sit on a specific executor. Nothing is "
                            "assigned automatically."
                        ),
                    },
                    "label": {
                        "type": "string",
                        "description": (
                            "Optional ASCII cue label. Defaults to the scene's own stored label."
                        ),
                    },
                },
                "required": ["scene_id", "group"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="build_patch_sheet",
            description=(
                "Build a printable patch sheet — every observed fixture's "
                "slot, universe/address, fixture type and mode — from the "
                "SAME fixture inventory precheck_patch reads. READS ONLY, "
                "sends nothing.\n"
                "\n"
                "This tool does NOT return the document itself. A patch "
                "sheet is a self-contained HTML page meant for a HUMAN to "
                "open in a browser and print, not for you to read — so the "
                "result carries only the file path it was written to plus a "
                "small numeric summary (fixture_count, child_count, "
                "completeness). Tell the operator the path; do not try to "
                "quote or summarize the HTML.\n"
                "\n"
                "'completeness' mirrors the fixture inventory's own verdict "
                '— when it is not "complete" the enumeration was partial '
                "and the sheet says so at the top, same as get_rig_context."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        ToolDefinition(
            name="build_cue_sheet",
            description=(
                "Build a printable cue sheet — every sequence, drilled one "
                "level into its stored cues — from the same sequences pool "
                "get_rig_context lists. READS ONLY, sends nothing.\n"
                "\n"
                "Like build_patch_sheet this tool returns a file path plus a "
                "small numeric summary (sequence_count, cue_count, "
                "truncated, drilldown_capped), never the HTML itself — the "
                "document is for a human to open, not for you to read."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        ToolDefinition(
            name="build_preset_list",
            description=(
                "Build a printable preset list — every preset-pool type "
                "(Dimmer, Color, Position, ...), drilled into the presets "
                "actually stored inside it — from the same preset pools "
                "get_rig_context lists. READS ONLY, sends nothing.\n"
                "\n"
                "Like build_patch_sheet this tool returns a file path plus a "
                "small numeric summary (pool_count, preset_count, "
                "truncated, drilldown_capped), never the HTML itself — the "
                "document is for a human to open, not for you to read."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        ToolDefinition(
            name="plan_executor_layout",
            description=(
                "Plan which executor each look of an already-chosen genre "
                "palette lands on — page, slot, the console's REAL executor "
                "number (page*100+slot) and an ASCII label — and return the "
                "two rulebook-validated command lines per look "
                "('Assign Sequence <n> At Executor <m>' and "
                "'Label Sequence <n> \\'<name>\\''). "
                "\n\n"
                "THIS TOOL NEVER SENDS ANYTHING TO THE CONSOLE. It only "
                "plans and returns command TEXT — to actually apply the "
                "layout you must pass the returned 'commands' list to "
                "run_commands yourself, which is where gate screening, the "
                "live lock and the audit log apply, unchanged.\n"
                "\n"
                "'sequence_numbers' must map each look_id (from find_looks / "
                "the genre's palette) to a sequence number that ALREADY "
                "EXISTS on this rig — this tool never creates a sequence, it "
                "only decides which executor an existing one lands on. A "
                "look with no entry is reported under 'skipped' "
                "(reason 'sequence_not_provided') and never guessed at.\n"
                "\n"
                "Before returning, this tool reads back every target "
                "executor's live state (the ONE read it performs) and marks "
                "any that are already occupied or could not be confirmed. A "
                "conflicted item stays in 'items' with 'conflict': true and "
                "a 'conflict_reason' of either 'occupied' (an existing "
                "sequence is already bound there) or 'unconfirmed' (the read "
                "did not answer, so it is NOT assumed free) — and it is "
                "EXCLUDED from 'commands'. Never overwrite a conflicted "
                "target yourself; re-plan onto a different page/slot or ask "
                "the operator."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "genre": {
                        "type": "string",
                        "description": (
                            "The operator's own word for the genre (e.g. '록', 'EDM') "
                            "— the same vocabulary prepare_busking accepts."
                        ),
                    },
                    "sequence_numbers": {
                        "type": "object",
                        "description": (
                            "Map of look_id -> an EXISTING sequence number on this "
                            "rig. A look_id missing from this map is skipped, never "
                            "assigned a placeholder."
                        ),
                        "additionalProperties": {"type": "integer"},
                    },
                    "page_no": {
                        "type": "integer",
                        "description": (
                            "Optional, defaults to 1. Only page 1's slot->executor "
                            "arithmetic is live-verified; other pages compute the "
                            "same formula unverified."
                        ),
                    },
                    "start_slot": {
                        "type": "integer",
                        "description": "Optional, defaults to 1. The first slot to place onto.",
                    },
                },
                "required": ["genre", "sequence_numbers"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="get_spatial_context",
            description=(
                "Read WHERE this rig physically is — every patched fixture's "
                "3D stage coordinates from the console's own patch data. Call "
                "this before any instruction that names a DIRECTION or a "
                "SHAPE across the rig ('left to right', 'from the centre "
                "out', 'diagonally', 'the back row', '왼쪽에서 오른쪽으로', "
                "'가운데부터 바깥으로'). get_rig_context tells you which "
                "objects exist; this tells you where they stand, and a "
                "directional instruction needs both.\n"
                "\n"
                "READS ONLY — it sends no command and changes nothing.\n"
                "\n"
                "Returns ONE OF TWO SHAPES, and which one you got is itself "
                "the completeness signal.\n"
                "\n"
                'COMPLETE read: {"source": "patch3d", "fixtures": [...], '
                '"unreadable": [...], "truncated": false, '
                '"roundtrip_capped": false, "coverage": {...}, '
                '"analysis": {...}}.\n'
                "\n"
                'INCOMPLETE read: there is NO "fixtures" key and NO "analysis" '
                "key. The coordinates that did arrive are under "
                '"partial_fixtures"; "missing" is {"expected", "received", '
                '"unseen_count"}; "analysis_withheld" says why no row '
                'structure was computed. Reaching for "fixtures" and not '
                "finding it MEANS this read was partial — report that, and "
                "never present the part you received as the rig.\n"
                "\n"
                'Each fixture is {"fid", "name", "x", "y", "z"} in metres, '
                'and "fid" is the fixture id the CONSOLE returned — it is the '
                "number you address (Fixture <fid>), unlike the patch-list "
                "slot get_rig_context shows. Negative coordinates are normal: "
                "the stage origin has sides.\n"
                "\n"
                '"unreadable" lists fixtures that have NO coordinate here, '
                "each with the console's own reason. Their positions are "
                "genuinely unknown — never assume 0, a neighbour's value or "
                "the middle of the stage for them; leave them out of the "
                "choreography or ask the operator.\n"
                "\n"
                "Two DIFFERENT incompleteness signals, never merged: "
                '"truncated": true means the console shortened its own '
                "fixture list, so fixtures exist that this call was never "
                'shown; "roundtrip_capped": true means this call hit its own '
                "query budget and stopped asking part-way through a rig "
                "bigger than it can read in one go. Only the second one is "
                "fixable by asking differently, which is why they stay "
                "separate — but EITHER produces the incomplete shape above, "
                'and so does a "childCount" that simply disagrees with what '
                'arrived. "missing" gives you the arithmetic: how many the '
                "console counted, how many you got, how many you never saw.\n"
                "\n"
                '"analysis" is present ONLY in the complete shape. It is the '
                "row structure detected from those "
                'coordinates: "row_count", "rows" (each with its "fids" in '
                'stage order), "row_order" and "low_confidence". This is what '
                "makes one 30-fixture bar and a 3x10 grid produce DIFFERENT "
                'choreography. When "low_confidence" is true the layout was '
                'not established — "no_spatial_spread" means every fixture '
                "reports the same point, which is a real reading of a rig "
                "that was patched but never positioned (NOT a failed read). "
                "In that case fall back to non-spatial choreography and say "
                "why; do not invent a left-to-right order the patch does not "
                "support."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        ToolDefinition(
            name="arrange_fixtures",
            description=(
                "MOVE fixtures in the patch: compute a grid / row / circle "
                "arrangement and WRITE the resulting 3D stage coordinates "
                "(metres) onto the fixtures you name. This CHANGES THE "
                "SHOWFILE — call it only when the operator explicitly asked "
                "for an arrangement ('line these 8 PARs up', 'lay this out as "
                "a 3x10 grid'). Never call it to 'tidy up' a rig on your own "
                "initiative, and never as a step toward some other goal.\n"
                "\n"
                "'fids' is the EXPLICIT target list and it is also the ORDER "
                "they occupy the shape in: fids[0] takes the first slot "
                "(leftmost of a row, front-left of a grid, start_angle of a "
                "circle). Fixtures you do not name are never touched. Only "
                "position is written; fixture orientation is never changed.\n"
                "\n"
                "The stage origin is the CENTRE, so negative coordinates are "
                "normal and expected. Unspecified 'spacing' is 1.0 m, "
                "'origin' is (0,0,0), 'radius' is 3.0 m, 'start_angle' is 0 "
                "degrees; the effective values come back under 'resolved'.\n"
                "\n"
                "Before writing anything the tool READS and retains every "
                "target's current coordinates, and the reply always carries a "
                "'restore_bundle' — the exact command lines that put every "
                "target back where it was. That bundle is the ONLY way to undo "
                "this call, so keep it: pass it to run_commands to revert. If "
                "any target's coordinates cannot be read, NOTHING is written.\n"
                "\n"
                "After writing, the tool reads every coordinate back and "
                "compares numerically. Report success ONLY when 'verified' is "
                "true: this console has been measured answering OK while "
                "storing the wrong value, so a cleared command list is not "
                "evidence. 'mismatches' names every coordinate that did not "
                "land, and the restore bundle still applies.\n"
                "\n"
                "Whether the rig LOOKS right on stage or in the 3D viewer is "
                "not machine-checkable — the operator has to look."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "preset": {
                        "type": "string",
                        "enum": list(SPATIAL_PRESETS),
                        "description": (
                            "The arrangement shape. 'row' spreads the fixtures "
                            "along one axis, 'grid' fills rows x columns, "
                            "'circle' spaces them evenly around a ring."
                        ),
                    },
                    "fids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": (
                            "The fixture ids to move, in the order they should "
                            "occupy the shape. These are FIDs as the console "
                            "reports them (get_spatial_context returns them), "
                            "not positions in a list."
                        ),
                    },
                    "rows": {
                        "type": "integer",
                        "description": (
                            "grid only. Give 'rows' and/or 'columns'; the "
                            "product must equal the number of fids. One may be "
                            "omitted and is derived. Never defaulted — the "
                            "shape is the request."
                        ),
                    },
                    "columns": {
                        "type": "integer",
                        "description": "grid only — see 'rows'.",
                    },
                    "spacing": {
                        "type": "number",
                        "description": (
                            "grid/row only. Metres between neighbours. Defaults to 1.0."
                        ),
                    },
                    "radius": {
                        "type": "number",
                        "description": "circle only. Ring radius in metres. Defaults to 3.0.",
                    },
                    "start_angle": {
                        "type": "number",
                        "description": (
                            "circle only. Degrees counter-clockwise from the +X "
                            "axis for the FIRST fid. Defaults to 0, which puts "
                            "it stage-right of the origin."
                        ),
                    },
                    "origin": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": (
                            "[x, y, z] centre of the shape in metres. Defaults "
                            "to the stage origin [0, 0, 0]."
                        ),
                    },
                    "orientation": {
                        "type": "string",
                        "description": (
                            "Which axis or plane to lay out on. row: 'x' "
                            "(default, left-right), 'y' (upstage depth) or 'z' "
                            "(height). grid/circle: 'xy' (default, floor plan) "
                            "or 'xz' (a vertical wall or truss array)."
                        ),
                    },
                },
                "required": ["preset", "fids"],
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="classify_arrangement_topology",
            description=(
                "Classify WHAT STRUCTURE the current rig's positions form "
                "(rows, a left/right split, concentric rings, vertical "
                "levels, a grid, or mirror-symmetric pairs) and propose GROUP "
                "NAMES for it, plus fixture-type groups when you already have "
                "them. Call this BEFORE create_arrangement_groups when the "
                "operator wants position-based groups but has not named the "
                "buckets themselves ('group these up by position', "
                "'위치별로 그룹 만들어줘').\n"
                "\n"
                "READS ONLY — it sends no command and changes nothing. It "
                "reads the same stage patch coordinates get_spatial_context "
                "does; call get_spatial_context first if you also need the "
                "raw coordinates or the row/'analysis' view.\n"
                "\n"
                "'topology.selected' is the ONE winning structure (or "
                "kind:null with low_confidence:true when nothing was clear); "
                "'topology.candidates' lists every hypothesis considered, for "
                "audit. 'suggested_groups' is the actionable output: a list "
                "of {'name', 'fids'} — pass a chosen subset straight through "
                "as create_arrangement_groups's 'groups' argument. This is a "
                "NAMING PROPOSAL ONLY; nothing is written until "
                "create_arrangement_groups is called AND approved.\n"
                "\n"
                "Optionally pass 'fixture_type_records' — "
                "{'fid','manufacturer','type_name'} entries you already read "
                "off Patch/FixtureTypes — to also get species-axis groups "
                "(named after the patch's own type/manufacturer string "
                "verbatim, never a guessed category like 'Spot' or 'Wash'). "
                "Omit it and 'fixture_types' comes back null — this tool "
                "does not read fixture types itself."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "fixture_type_records": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fid": {"type": "integer"},
                                "manufacturer": {"type": "string"},
                                "type_name": {"type": "string"},
                                "short_name": {"type": "string"},
                            },
                            "required": ["fid", "manufacturer", "type_name"],
                        },
                        "description": (
                            "Optional. Already-read patch structured fields per "
                            "fixture — adds a species/manufacturer axis to "
                            "'suggested_groups'. Omit to skip it."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        ),
        ToolDefinition(
            name="create_arrangement_groups",
            description=(
                "STORE named position/type groups into the showfile: "
                "Store Group + Label Group for each entry in 'groups'. This "
                "CHANGES THE SHOWFILE — call it only when the operator "
                "explicitly asked for groups to be created, typically after "
                "classify_arrangement_topology proposed names.\n"
                "\n"
                "Every write here requires EXPLICIT HUMAN APPROVAL before "
                "anything reaches the console — Store Group/Label Group are "
                "NOT flagged risky by the safety gate on their own "
                "(server/safety/** is unchanged by this tool), so this tool "
                "enforces its own approval step. If approval is withheld, "
                "unavailable or unconfirmed, NOTHING is sent — the reply "
                "carries 'status':'proposal' and the plan only, and calling "
                "again with the same 'groups' after a human approves is how "
                "you proceed. Never claim a group was created because this "
                "call returned without an error; check 'status'.\n"
                "\n"
                "Targets are ALWAYS empty slots, measured fresh from the "
                "group pool — an occupied slot is never targeted, silently "
                "skipped or overwritten. A truncated group pool or fixture "
                "list refuses the whole call with a structured error rather "
                "than guessing.\n"
                "\n"
                "'unverified' ALWAYS lists 'membership': grandMA3 exposes no "
                "channel to read back which fixtures actually landed in a "
                "group, so that fact is never verified and never silently "
                "assumed true. What IS verified (after a successful write, "
                "under 'verified_steps'): the slot exists and its label "
                "reads back correctly. 'human_check_commands' gives you a "
                "'Group <n>' line per group so the operator can confirm the "
                "arrangement by eye on stage — that is the only way "
                "membership is ever actually confirmed.\n"
                "\n"
                "If a group you pass carries 'topology_partial': true — "
                "classify_arrangement_topology stamps that on every geometric "
                "group it derived from a rig read that was NOT complete — "
                "this call is REFUSED unless you also pass "
                "'acknowledged_unread_fids'. There is no boolean form of that "
                "acknowledgement on purpose: a flag can be set without "
                "reading anything, and naming the fids cannot."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "groups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": (
                                        "The group's label. Typically taken "
                                        "verbatim from classify_arrangement_"
                                        "topology's 'suggested_groups', or the "
                                        "operator's own words."
                                    ),
                                },
                                "fids": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "The fixture ids this group holds.",
                                },
                            },
                            "required": ["name", "fids"],
                        },
                        "description": (
                            "The groups to Store and Label, in order. Each "
                            "one becomes exactly one showfile group at a "
                            "freshly-measured empty slot."
                        ),
                    },
                    "acknowledged_unread_fids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": (
                            "Required ONLY when a group carries "
                            "'topology_partial': true. The fixture ids the "
                            "partial rig read never saw, named one by one — "
                            "non-empty, distinct, and none of them among the "
                            "fids you are grouping (those were seen). Take "
                            "them from get_spatial_context: 'missing' says "
                            "how many are unseen and 'partial_fixtures' says "
                            "which ones arrived. NOT a boolean — a flag can "
                            "be set without reading what is absent, which is "
                            "the failure this argument exists to prevent."
                        ),
                    },
                },
                "required": ["groups"],
                "additionalProperties": False,
            },
        ),
    )
    handlers: dict[str, _Handler] = {
        "run_commands": run_commands,
        "query_state": query_state,
        "deploy_plugin": deploy_plugin,
        "get_rig_context": get_rig_context,
        "find_looks": find_looks,
        "instantiate_look": instantiate_look,
        "prepare_busking": prepare_busking,
        "prepare_songcue": prepare_songcue,
        "precheck_patch": precheck_patch,
        "preshow_check": preshow_check,
        "find_fx": find_fx,
        "instantiate_fx": instantiate_fx,
        "find_scene": find_scene,
        "compile_scene": compile_scene,
        "build_patch_sheet": build_patch_sheet,
        "build_cue_sheet": build_cue_sheet,
        "build_preset_list": build_preset_list,
        "plan_executor_layout": plan_executor_layout,
        "get_spatial_context": get_spatial_context,
        "arrange_fixtures": arrange_fixtures,
        "classify_arrangement_topology": classify_arrangement_topology,
        "create_arrangement_groups": create_arrangement_groups,
    }
    return ToolRegistry(definitions, handlers)
