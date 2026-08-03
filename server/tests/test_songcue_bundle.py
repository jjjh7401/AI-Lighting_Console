from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import fields
from pathlib import Path

import pytest

from server.looks.busking import VALUE_LINE_COLLISION
from server.looks.schema import AttributeValue, Look
from server.looks.songcue import (
    EMPTY_SECTIONS,
    ROLE_UNMAPPED,
    SEQUENCE_TRUNCATED,
    SEQUENCE_UNAVAILABLE,
    SongCueBundleError,
    SongCueLookSelection,
    build_songcue_bundle,
    observed_user_cue_count,
    parse_sections,
    render_songcue_report,
    select_sequence_number,
)
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import ToolCall as RegistryToolCall
from server.orchestrator.tools import build_toolset
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_resolver import _code_string_constants

_SONGCUE_MODULE = Path("server/looks/songcue.py")
_STORE_RE = re.compile(r"^Store Sequence (?P<sequence>\d+) Cue (?P<cue>\d+) '(?P<name>[^']+)'$")
_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_FORBIDDEN_COMMANDS = {
    "overwrite": re.compile(r"/overwrite\b", re.IGNORECASE),
    "remove": re.compile(r"/remove\b", re.IGNORECASE),
    "delete": re.compile(r"\bdelete\b", re.IGNORECASE),
    "trig": re.compile(r"/trig\s*=", re.IGNORECASE),
    "label_cue": re.compile(r"^\s*label\s+cue\b", re.IGNORECASE),
    "goto_cue": re.compile(r"^\s*goto\s+cue\b", re.IGNORECASE),
}
_RUN_PHASE_BASE = "38a6e7e2157a4862721fcd868056e0dbbb09c4c0"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PRESERVE_LOOK_FILES = (
    "server/looks/matching.py",
    "server/looks/instantiate.py",
    "server/looks/resolver.py",
    "server/looks/schema.py",
    "server/looks/loader.py",
    "server/looks/roles.py",
)
_TOOLS_PATH = "server/orchestrator/tools.py"
# Snapshot of every tools.py hunk since SONGCUE's run-phase base. It is a
# TRIPWIRE, not a constant: a later SPEC that legitimately edits tools.py must
# update it deliberately, which is the point — the protected-range assertion
# below is the real invariant and it must keep holding while this list grows.
# PRECHK (SPEC-COPILOT-PRECHK-001, M6) added the three hunks at 463 / 475 / 479
# (the prechk imports, the `property_port` parameter and its docstring) and moved
# the first hunk's old start from 32 to 33 by inserting its import block one line
# lower. None of them touches a protected range.
# Grows by one entry per SPEC that registers a tool. FXLIB M5 added 17 (the fx
# imports) and 436 (the fx argument/rig helpers, inserted above ToolRegistry).
# SCENE (SPEC-COPILOT-SCENE-001, M6) added 15 — the `replace` import the label
# override needs — and widened the existing 17 hunk with the scene imports, the
# two handlers and their tool definitions. Still no protected range touched.
# PRESHOW (SPEC-COPILOT-PRESHOW-001) registered preshow_check the same way:
# one import line, one TOOL_NAMES entry, one handler + ToolDefinition + one
# handlers-dict entry. Its handler insertion sits inside the same large
# build_toolset body the earlier SPECs already touch, so unified=0 splits the
# old single hunk at 951 into five (952 / 971 / 989 / 1007 / 1118) instead of
# adding a wholly new start — none of the five overlaps a protected range.
# T-J (tool-registration branch) registered the four previously-unregistered
# paperwork/layout tools the same way: import lines, four TOOL_NAMES entries,
# four handlers + four ToolDefinitions + four handlers-dict entries — all
# widening hunks the earlier SPECs already opened, except ONE genuinely new
# start at 27 (ruff's isort placing the `server.looks.layout` import between
# the existing `server.looks.instantiate` and `server.looks.schema` imports).
# None of it touches a protected range.
# SPATIAL (SPEC-COPILOT-SPATIAL-001) registered get_spatial_context and
# arrange_fixtures: three genuinely new starts — 12 and 14 (ruff's isort placing
# `import math` and the `server.spatial` import block among the existing
# imports) and 425 (the spatial read/write module-level helpers, inserted above
# ToolRegistry beside the fx ones at 436) — plus widening of hunks the earlier
# SPECs already opened. 15 and 1118 disappear from the list because unified=0
# merged them into neighbouring widened hunks, not because anything there was
# reverted.
# None of it touches a protected range (verified: zero overlap).
# The positional list is bookkeeping; the assertion that carries the PRESERVE
# claim is the protected-range overlap check below.
_TOOLS_EXPECTED_HUNK_OLD_STARTS = (
    12,
    14,
    17,
    27,
    33,
    49,
    125,
    425,
    436,
    463,
    475,
    479,
    952,
    971,
    989,
    1007,
    1222,
    1231,
)
_TOOLS_PROTECTED_OLD_RANGES = ((234, 238), (524, 569))
_HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")


def test_sequence_one_and_cues_one_to_n_for_six_and_ten_sections():
    for size in (6, 10):
        bundle = _bundle_for_size(size)
        stores = _store_refs(bundle.commands)

        assert len(stores) == size
        assert {sequence for sequence, _cue, _name in stores} == {bundle.sequence_number}
        assert [cue for _sequence, cue, _name in stores] == list(range(1, size + 1))


def test_naive_per_section_next_cue_defect_is_real_but_bundle_uses_a_ledger():
    bundle = _bundle_for_size(4)
    sections = [plan.section for plan in bundle.sections]

    assert _naive_next_cues(sections) == [1, 1, 1, 1]
    assert [plan.cue_number for plan in bundle.sections] == [1, 2, 3, 4]


def test_sequence_number_comes_from_complement_and_rejects_unknown_snapshots():
    assert select_sequence_number(_sequences(1, 2, 4)) == 3
    assert select_sequence_number(_sequences(1, 2, 3)) == 4
    assert select_sequence_number({"children": [{"i": 1, "name": "Sequence 1"}]}) == 2

    with pytest.raises(Exception) as failed:
        select_sequence_number({"reason": "path_not_resolved"})
    assert failed.value.reason == SEQUENCE_UNAVAILABLE

    with pytest.raises(Exception) as truncated:
        select_sequence_number(_sequences(1, 2, truncated=True))
    assert truncated.value.reason == SEQUENCE_TRUNCATED


def test_implicit_system_cues_are_subtracted_and_truncation_is_rejected():
    payload = {"node": {"childCount": 8}, "truncated": False}

    assert observed_user_cue_count(payload) == 6
    with pytest.raises(Exception) as raised:
        observed_user_cue_count({"node": {"childCount": 24}, "truncated": True})
    assert raised.value.reason == SEQUENCE_TRUNCATED


def test_commands_are_ascii_and_report_keeps_korean_in_presentation_only():
    section = parse_sections((("후렴", "0:00"),))[0]
    look = _look("k", dynamics=4)
    bundle = build_songcue_bundle(
        "사랑 노래",
        (SongCueLookSelection(section=section, requested_dynamics=(4,), look=look),),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    assert bundle.commands
    assert all(command.isascii() for command in bundle.commands)
    assert _has_hangul(render_songcue_report(bundle))
    assert all(field.name.isascii() for field in fields(Look))


def test_repeated_section_names_are_disambiguated_in_store_names():
    sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:30")))
    looks = (_look("a", dynamics=4, value=40), _look("b", dynamics=5, value=50))
    bundle = build_songcue_bundle(
        "Song",
        tuple(
            SongCueLookSelection(section=section, requested_dynamics=(look.dynamics,), look=look)
            for section, look in zip(sections, looks, strict=True)
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    assert [name for _sequence, _cue, name in _store_refs(bundle.commands)] == [
        "Chorus 1",
        "Chorus 2",
    ]


def test_forbidden_command_scanner_is_generated_tuple_based_and_nonempty():
    bundle = _bundle_for_size(3)

    assert bundle.commands
    assert _forbidden_hits(bundle.commands) == []
    assert all("/Merge" not in command for command in bundle.commands)


def test_forbidden_command_scanner_catches_injected_forms_case_insensitively():
    planted = (
        "Store Cue 5 /overwrite",
        "Store Cue 6 /Remove",
        "Delete Sequence 7",
        "Cue 1 /trig=Time",
        "Label Cue 1 'X'",
        "Goto Cue 2 Sequence 5",
    )

    hits = _forbidden_hits(planted)

    assert {name for name, _command in hits} == set(_FORBIDDEN_COMMANDS)


def test_destination_is_once_at_head_and_clearall_cycles_survive():
    bundle = _bundle_for_size(4)

    assert bundle.commands[0] == _DESTINATION
    assert bundle.commands.count(_DESTINATION) == 1
    assert bundle.commands.count(_CLEAR) == 8
    assert bundle.commands[1] == _CLEAR
    assert bundle.commands[-1] == _CLEAR


def test_label_sequence_is_after_first_store_once():
    bundle = _bundle_for_size(2)
    store_indexes = [
        index
        for index, command in enumerate(bundle.commands)
        if command.startswith("Store Sequence ")
    ]
    label = f"Label Sequence {bundle.sequence_number} '{bundle.sequence_name}'"

    assert bundle.commands.count(label) == 1
    assert bundle.commands[store_indexes[0] + 1] == label


def test_bundle_goes_through_run_commands_without_dedupe_loss():
    bundle = _bundle_for_size(5)
    port = _RecordingPort()
    registry = build_toolset(execution_port=port, state_port=_StatePort())
    execution = registry.dispatch(
        RegistryToolCall(
            id="songcue", name="run_commands", arguments={"commands": list(bundle.commands)}
        )
    )
    statuses = [outcome.status for outcome in execution.command_outcomes]

    assert statuses
    assert "skipped_already_executed" not in statuses
    assert set(statuses) == {"executed_ok"}
    assert port.executed == list(bundle.commands)


def test_preserve_gate_uses_run_phase_base_to_head_range():
    command = _preserve_diff_command()

    assert command[:4] == ["git", "diff", "--stat", f"{_RUN_PHASE_BASE}..HEAD"]
    assert command[4] == "--"
    assert tuple(command[5:]) == _PRESERVE_LOOK_FILES


def test_preserve_look_files_are_unchanged_from_run_phase_base():
    result = subprocess.run(
        _preserve_diff_command(),
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert _PRESERVE_LOOK_FILES
    assert result.stdout == ""


def test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state():
    hunks = _tools_hunks_from_run_phase_base()

    assert hunks
    assert tuple(start for start, _count in hunks) == _TOOLS_EXPECTED_HUNK_OLD_STARTS
    assert [
        (start, count)
        for start, count in hunks
        for protected_start, protected_end in _TOOLS_PROTECTED_OLD_RANGES
        if _overlaps(start, count, protected_start, protected_end)
    ] == []


def test_value_line_collision_skips_later_section_without_pulling_next_cue():
    chorus_a, chorus_b, verse = parse_sections(
        (("Chorus", "0:00"), ("Chorus", "0:30"), ("Verse", "1:00"))
    )
    chorus_look = _look("chorus", dynamics=4, value=80)
    verse_look = _look("verse", dynamics=2, value=45)
    bundle = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(section=chorus_a, requested_dynamics=(4, 5), look=chorus_look),
            SongCueLookSelection(section=chorus_b, requested_dynamics=(4, 5), look=chorus_look),
            SongCueLookSelection(section=verse, requested_dynamics=(2, 3), look=verse_look),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    stores = _store_refs(bundle.commands)
    assert [cue for _sequence, cue, _name in stores] == [1, 3]
    assert [plan.cue_number for plan in bundle.sections] == [1, 2, 3]
    assert len(bundle.skipped) == 1
    assert bundle.skipped[0].reason == VALUE_LINE_COLLISION
    assert bundle.skipped[0].collides_with_section_index == chorus_a.index
    assert bundle.skipped[0].collides_with_cue_number == 1


def test_value_line_collision_bundle_still_executes_without_dedupe_loss():
    chorus_a, chorus_b = parse_sections((("Chorus", "0:00"), ("Chorus", "0:30")))
    look = _look("chorus", dynamics=4, value=80)
    bundle = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(section=chorus_a, requested_dynamics=(4, 5), look=look),
            SongCueLookSelection(section=chorus_b, requested_dynamics=(4, 5), look=look),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
    port = _RecordingPort()
    execution = build_toolset(execution_port=port, state_port=_StatePort()).dispatch(
        RegistryToolCall(
            id="songcue", name="run_commands", arguments={"commands": list(bundle.commands)}
        )
    )

    assert bundle.commands
    assert execution.result.is_error is False
    assert "skipped_already_executed" not in [
        outcome.status for outcome in execution.command_outcomes
    ]
    assert port.executed == list(bundle.commands)


def test_distinct_value_lines_do_not_trigger_collision():
    first, second = parse_sections((("Chorus", "0:00"), ("Verse", "0:30")))
    bundle = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(
                section=first, requested_dynamics=(4,), look=_look("a", dynamics=4, value=80)
            ),
            SongCueLookSelection(
                section=second, requested_dynamics=(2,), look=_look("b", dynamics=2, value=45)
            ),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )

    assert bundle.skipped == ()
    assert [cue for _sequence, cue, _name in _store_refs(bundle.commands)] == [1, 2]


def test_zero_sections_rejects_one_section_succeeds_and_unmapped_roles_are_answer():
    with pytest.raises(SongCueBundleError) as raised:
        build_songcue_bundle(
            "Song", (), sequences_section=_sequences(), groups_section=_groups(*FULL_RIG)
        )
    assert raised.value.reason == EMPTY_SECTIONS

    section = parse_sections((("Intro", "0:00"),))[0]
    normal = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(
                section=section, requested_dynamics=(1,), look=_look("intro", dynamics=1)
            ),
        ),
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
    assert [cue for _sequence, cue, _name in _store_refs(normal.commands)] == [1]

    unresolved = build_songcue_bundle(
        "Song",
        (
            SongCueLookSelection(
                section=section, requested_dynamics=(1,), look=_look("intro", dynamics=1)
            ),
        ),
        sequences_section=_sequences(),
        groups_section=_groups((99, "Unmatched")),
    )
    assert unresolved.is_error is False
    assert unresolved.commands == ()
    assert unresolved.skipped[0].reason == ROLE_UNMAPPED


def test_static_scans_find_no_command_number_literals_or_numeric_rig_defaults():
    strings = _code_string_constants(_SONGCUE_MODULE)
    assert strings
    numbered_object = re.compile(
        r"\b(Group|Pool|Preset|Sequence|Cue|Fixture|Executor|Page|FID|Slot)\s+\d"
    )
    assert [value for value in strings if numbered_object.search(value)] == []

    tree = ast.parse(_SONGCUE_MODULE.read_text(encoding="utf-8"))
    assert _numeric_fstring_constants(tree) == []
    assert _numeric_rig_defaults(tree) == []


def test_static_scanners_catch_injected_forbidden_shapes():
    numbered_object = re.compile(
        r"\b(Group|Pool|Preset|Sequence|Cue|Fixture|Executor|Page|FID|Slot)\s+\d"
    )
    assert numbered_object.search("Store Sequence 3 Cue 1")

    fstring_tree = ast.parse('def x(slot):\n    return f"Preset {4}.{slot}"\n')
    assert _numeric_fstring_constants(fstring_tree)

    default_tree = ast.parse("def store(look, *, group_number: int = 7) -> None: ...")
    assert _numeric_rig_defaults(default_tree)


def _bundle_for_size(size: int):
    sections = parse_sections(tuple((f"Section {index}", index + 1) for index in range(size)))
    selections = tuple(
        SongCueLookSelection(
            section=section,
            requested_dynamics=(1,),
            look=_look(f"look-{section.index}", dynamics=1, value=20 + section.index),
        )
        for section in sections
    )
    return build_songcue_bundle(
        "테스트 곡",
        selections,
        sequences_section=_sequences(1, 2, 4),
        groups_section=_groups(*FULL_RIG),
    )


def _look(look_id: str, *, dynamics: int, value: float = 50) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre="rock",
        dynamics=dynamics,
        roles=("백라이트",),
        attributes=(AttributeValue("Dimmer", value),),
    )


def _sequences(*numbers: int, truncated: bool = False) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": truncated,
        "total": len(numbers),
    }


def _store_refs(commands: tuple[str, ...]) -> list[tuple[int, int, str]]:
    refs: list[tuple[int, int, str]] = []
    for command in commands:
        match = _STORE_RE.fullmatch(command)
        if match:
            refs.append(
                (int(match.group("sequence")), int(match.group("cue")), match.group("name"))
            )
    return refs


def _forbidden_hits(commands: tuple[str, ...]) -> list[tuple[str, str]]:
    return [
        (name, command)
        for command in commands
        for name, pattern in _FORBIDDEN_COMMANDS.items()
        if pattern.search(command)
    ]


def _naive_next_cues(sections) -> list[int]:
    return [1 for _section in sections]


def _has_hangul(value: str) -> bool:
    return any("가" <= char <= "힣" for char in value)


def _preserve_diff_command() -> list[str]:
    return ["git", "diff", "--stat", f"{_RUN_PHASE_BASE}..HEAD", "--", *_PRESERVE_LOOK_FILES]


def _tools_hunks_from_run_phase_base() -> list[tuple[int, int]]:
    result = subprocess.run(
        ["git", "diff", "--unified=0", f"{_RUN_PHASE_BASE}..HEAD", "--", _TOOLS_PATH],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    hunks: list[tuple[int, int]] = []
    for line in result.stdout.splitlines():
        match = _HUNK_RE.match(line)
        if match is not None:
            hunks.append((int(match.group("old_start")), int(match.group("old_count") or "1")))
    return hunks


def _overlaps(old_start: int, old_count: int, protected_start: int, protected_end: int) -> bool:
    old_end = old_start + max(old_count, 1) - 1
    return old_start <= protected_end and protected_start <= old_end


def _numeric_fstring_constants(tree: ast.AST) -> list[ast.FormattedValue]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FormattedValue)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, int | float)
    ]


def _numeric_rig_defaults(tree: ast.AST) -> list[tuple[str, str]]:
    rig_param = re.compile(r"sequence|cue|group|pool|slot|fid|fixture|executor|page", re.IGNORECASE)
    offenders: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        pairs = list(
            zip(
                node.args.args[len(node.args.args) - len(node.args.defaults) :],
                node.args.defaults,
                strict=True,
            )
        ) + list(zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True))
        for arg, default in pairs:
            if (
                default is not None
                and rig_param.search(arg.arg)
                and isinstance(default, ast.Constant)
                and isinstance(default.value, int | float)
            ):
                offenders.append((node.name, arg.arg))
    return offenders


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _StatePort:
    def query_state(self, path: str) -> dict:
        return {}
