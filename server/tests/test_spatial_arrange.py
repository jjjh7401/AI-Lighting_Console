"""M4 — preset geometry and the coordinate WRITE path (AC-SPATIAL-018~022).

Two halves, and the split matters.

The first half is PURE: ``server/spatial/presets.py`` turns a request into
coordinates with standard-library arithmetic and no console anywhere. Those are
golden tests — the documented defaults (1.0 m spacing about the stage origin,
3.0 m radius, 0 degrees) are part of the contract (design.md §6.6), so a silent
retune has to fail here. Negative coordinates are first-class: the stage origin
is the CENTRE, and the 8-fixture default row this file pins reproduces exactly
the x = -3.5 .. +3.5 placement the M0 P8 probe wrote and read back on the live
console (progress.md §E.2.7).

The second half is the write path, and its fake console is not a convenience —
it is a MODEL OF A MEASURED FAILURE. On onPC 2.4.2, three of five coordinate
write forms answered ``ok:true`` while storing the wrong value or nothing at all
(§E.2.6a), and the console stores float32, so a correct 9.9 reads back as
9.8999996185303. :class:`ArrangeConsole` does all of that: it drops signs when
told to, no-ops silently when told to, and quantises every stored value to
float32 always. A test suite whose fake console is honest cannot see the bug
this tool exists to catch.

Console contact: zero. Everything below is in-memory.
"""

from __future__ import annotations

import json
import re
import struct

import pytest

from server.llm.types import ToolCall
from server.orchestrator import tools
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    ARRANGE_AXES,
    ARRANGE_READ_AXES,
    ARRANGE_VERIFY_ABS_TOLERANCE,
    ARRANGE_VERIFY_REL_TOLERANCE,
    DEFAULT_RIG_CONTEXT_PATHS,
    TOOL_NAMES,
    arrange_restore_commands,
    arrange_scope_violations,
    arrange_values_match,
    arrange_write_commands,
    build_toolset,
)
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock
from server.spatial.presets import (
    SPATIAL_PRESET_DECIMALS,
    SPATIAL_PRESET_DEFAULTS,
    SPATIAL_PRESETS,
    SpatialPresetError,
    spatial_preset_placements,
)

FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]

#: One coordinate write, as the tool is required to spell it. The single quotes
#: are part of the pattern on purpose (§E.2.6a).
SET_COMMAND = re.compile(r"^Set Fixture (\d+) (Pos[xyz]) '(-?\d+(?:\.\d+)?)'$")

#: Anything that touches a fixture's ORIENTATION rather than its position.
#: v1 writes position only (REQ-SPATIAL-022 c), so this must never match.
ORIENTATION_WRITE = re.compile(r"\brot[xyz]\b", re.IGNORECASE)

_MISSING = object()


def _float32(value: float) -> float:
    """What the console actually keeps — single precision (§E.2.6a)."""
    return struct.unpack("f", struct.pack("f", value))[0]


def _console_text(value: float) -> str:
    """How the console renders a stored coordinate back.

    14 significant digits, which is what turns a stored float32 9.9 into the
    literal string ``9.8999996185303`` the live probe read back (§E.2.6a).
    """
    text = f"{value:.14g}"
    if "." not in text and "e" not in text:
        text += ".0"
    return text


class ArrangeConsole:
    """A fake onPC 2.4.2 that lies the way the real one was measured lying.

    One object plays all three ports (state / property / execution) so that
    reads and writes land in ONE ``calls`` list — which is what makes
    "the backup was read before anything was written" an assertion about ORDER
    rather than about mere presence.

    ``lies`` maps ``(fid, "Posx")`` to what the console will ACTUALLY store when
    that write arrives, and still answer OK:

      * a float -> it stores that instead (the dropped sign, the stray 0.0)
      * ``None`` -> it stores nothing at all (the silent no-op)
    """

    def __init__(
        self,
        fixtures,
        *,
        lies=None,
        unreadable=(),
        truncated=False,
        write_failures=(),
    ):
        self.fixtures = {
            slot: {"fid": fid, "name": name, "posx": x, "posy": y, "posz": z}
            for slot, fid, name, x, y, z in fixtures
        }
        self.lies = dict(lies or {})
        self.unreadable = set(unreadable)
        self.truncated = truncated
        self.write_failures = set(write_failures)
        self.calls: list[tuple[str, str]] = []

    # -- observation ---------------------------------------------------------

    @property
    def writes(self) -> list[str]:
        return [detail for kind, detail in self.calls if kind == "write"]

    @property
    def written_fids(self) -> set[int]:
        return {int(m.group(1)) for m in (SET_COMMAND.match(w) for w in self.writes) if m}

    @property
    def property_reads(self) -> list[str]:
        return [
            detail for kind, detail in self.calls if kind == "read" and detail.startswith("prop")
        ]

    def snapshot(self) -> dict:
        return {slot: dict(row) for slot, row in self.fixtures.items()}

    def slot_of(self, fid: int) -> int:
        return next(slot for slot, row in self.fixtures.items() if row["fid"] == fid)

    def coordinates(self, fid: int) -> tuple[float, float, float]:
        row = self.fixtures[self.slot_of(fid)]
        return (row["posx"], row["posy"], row["posz"])

    # -- ports ---------------------------------------------------------------

    def query_state(self, path: str) -> dict:
        self.calls.append(("read", f"state {path}"))
        if path != FIXTURES_PATH:
            raise LookupError(f"unknown object path: {path}")
        slots = sorted(self.fixtures)
        shown = slots[:-1] if self.truncated else slots
        return {
            "v": 1,
            "kind": "state",
            "path": path,
            "childCount": len(slots),
            "children": [{"i": slot, "name": self.fixtures[slot]["name"]} for slot in shown],
            "truncated": self.truncated,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        self.calls.append(("read", f"prop {path} {property_name}"))
        slot = int(path.rsplit("/", 1)[1])
        key = property_name.lower()
        row = self.fixtures.get(slot)
        if row is None or key not in row or (slot, key) in self.unreadable:
            # The live channel IS discriminating on reads (§E.2.1): a property
            # it cannot serve comes back ok:false with a reason.
            return {"ok": False, "error": f"property not readable: {property_name}"}
        value = row[key]
        return {"ok": True, "value": str(value) if key == "fid" else _console_text(value)}

    def execute(self, command: str) -> ExecutionResult:
        self.calls.append(("write", command))
        if command in self.write_failures:
            return ExecutionResult(ok=False, detail="Illegal property")
        match = SET_COMMAND.match(command)
        if match is None:
            return ExecutionResult(ok=False, detail="Illegal property")
        fid, axis, value = int(match.group(1)), match.group(2), float(match.group(3))
        slot = self.slot_of(fid)
        stored = self.lies.get((fid, axis), _MISSING)
        if stored is _MISSING:
            self.fixtures[slot][axis.lower()] = _float32(value)
        elif stored is not None:
            self.fixtures[slot][axis.lower()] = _float32(stored)
        # stored is None -> nothing changes, and the console still says OK.
        return ExecutionResult(ok=True, detail="OK")


class RefusingConsole:
    """Console link that must never be reached while the live lock is on."""

    def send_command(self, command: str):  # pragma: no cover - must never run
        raise AssertionError(f"a console send was attempted under the live lock: {command!r}")


class _CommandDecision:
    """One row of a gate ScreenDecision (server/orchestrator/ports.py shape)."""

    def __init__(self, command: str, status: str = "rejected"):
        self.command = command
        self.status = status
        self.reasons: tuple[str, ...] = ()


def rig(count: int = 12, *, fid_offset: int = 10, **kwargs) -> ArrangeConsole:
    """A patch container whose SLOT is deliberately not its FID.

    ``rig_object``'s standing warning made concrete: slot 1 holds fid 11. A tool
    that assumed the two were the same would move the wrong fixtures here, and
    every write test below would still pass on a rig where they matched.
    """
    return ArrangeConsole(
        [(slot, slot + fid_offset, f"PAR {slot}", 0.0, 0.0, 0.0) for slot in range(1, count + 1)],
        **kwargs,
    )


def registry(console: ArrangeConsole, *, gate=None):
    return build_toolset(execution_port=console, state_port=console, bundle_gate=gate)


def arrange(console: ArrangeConsole, arguments: dict, *, gate=None):
    execution = registry(console, gate=gate).dispatch(
        ToolCall(id="c1", name="arrange_fixtures", arguments=arguments)
    )
    return execution, json.loads(execution.result.content)


class ScriptedApprovalPort:
    """Records every approval request and answers with a scripted verdict."""

    def __init__(self, approve: bool):
        self.approve = approve
        self.requests: list = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return self.approve


def real_gate(
    tmp_path, *, locked: bool, approve: bool = True, backup=None, approval_port=None
) -> SafetyGate:
    """A REAL gate. A fake handing back the string "locked" proves nothing.

    ``approve`` defaults to True because a coordinate bundle is RISKY since the
    `blacklist.yaml` v2 revision (SPEC-COPILOT-WRITEGATE-001): every write below
    now needs an approval, so a gate with no approval channel could never write
    and every write assertion in this file would pass vacuously on a gate that
    is simply refusing. The fail-CLOSED default is not lost — it is asserted
    directly in ``test_an_unwired_approval_channel_is_not_read_as_pre_approved``.

    Pass ``approval_port`` to keep a handle on the port and inspect the cards it
    was shown, instead of reading the gate's private attribute back out.
    """
    lock = LiveLock()
    if locked:
        lock.activate()
    return SafetyGate(
        console=RefusingConsole() if locked else None,
        audit=AuditLog(tmp_path / "audit"),
        lock=lock,
        approval_port=approval_port or ScriptedApprovalPort(approve),
        backup=backup,
    )


# ==========================================================================
# Preset geometry — pure, golden (AC-SPATIAL-018)
# ==========================================================================


class TestPresetDefaults:
    """The defaults are a CONTRACT, so they are asserted as values."""

    def test_the_documented_defaults_are_the_documented_numbers(self):
        assert SPATIAL_PRESET_DEFAULTS["spacing"] == 1.0
        assert SPATIAL_PRESET_DEFAULTS["origin"] == (0.0, 0.0, 0.0)
        assert SPATIAL_PRESET_DEFAULTS["radius"] == 3.0
        assert SPATIAL_PRESET_DEFAULTS["start_angle"] == 0.0
        assert SPATIAL_PRESET_DEFAULTS["orientation"] == {
            "grid": "xy",
            "row": "x",
            "circle": "xy",
        }

    def test_the_preset_vocabulary_is_closed(self):
        assert SPATIAL_PRESETS == ("grid", "row", "circle")
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("spiral", [1, 2, 3])

    def test_the_resolved_parameters_are_reported_not_merely_applied(self):
        # A report that says "1.0 m about (0,0,0)" is auditable; one that
        # silently applied it is not (design.md §6.6).
        plan = spatial_preset_placements("row", [1, 2, 3])
        assert plan.resolved["spacing"] == 1.0
        assert plan.resolved["origin"] == [0.0, 0.0, 0.0]
        assert plan.resolved["orientation"] == "x"


class TestRowGeometry:
    def test_eight_fixtures_at_the_default_spacing_reproduce_the_live_probe(self):
        # progress.md §E.2.7: fid 11..18 were written to x = -3.5 .. +3.5 at
        # 1.0 m and read back to 8/8 agreement on the real console. If this
        # layer cannot reproduce that placement it disagrees with a measurement.
        plan = spatial_preset_placements("row", list(range(11, 19)))
        assert [p.x for p in plan.placements] == [-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5]
        assert {p.y for p in plan.placements} == {0.0}
        assert {p.z for p in plan.placements} == {0.0}
        assert plan.fids == tuple(range(11, 19))

    def test_negative_coordinates_are_produced_with_their_sign_intact(self):
        # The stage origin is the CENTRE (acceptance.md §D). Half a centred row
        # is negative by construction; a layer that clamped at zero would look
        # fine on every positive-only golden.
        plan = spatial_preset_placements("row", [1, 2, 3, 4])
        assert [p.x for p in plan.placements] == [-1.5, -0.5, 0.5, 1.5]

    def test_an_odd_count_puts_one_fixture_exactly_on_the_origin(self):
        plan = spatial_preset_placements("row", [1, 2, 3, 4, 5])
        assert [p.x for p in plan.placements] == [-2.0, -1.0, 0.0, 1.0, 2.0]

    def test_a_single_fixture_lands_on_the_origin(self):
        plan = spatial_preset_placements("row", [7])
        assert (plan.placements[0].x, plan.placements[0].y, plan.placements[0].z) == (
            0.0,
            0.0,
            0.0,
        )

    def test_spacing_and_origin_are_both_honoured(self):
        plan = spatial_preset_placements(
            "row", [1, 2, 3], {"spacing": 2.5, "origin": [-1.0, 4.0, 6.0]}
        )
        assert [(p.x, p.y, p.z) for p in plan.placements] == [
            (-3.5, 4.0, 6.0),
            (-1.0, 4.0, 6.0),
            (1.5, 4.0, 6.0),
        ]

    def test_orientation_selects_which_axis_the_row_runs_along(self):
        plan = spatial_preset_placements("row", [1, 2], {"orientation": "z"})
        assert [(p.x, p.y, p.z) for p in plan.placements] == [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5)]
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("row", [1, 2], {"orientation": "xy"})


class TestGridGeometry:
    def test_a_three_by_ten_grid_lands_on_the_expected_corners(self):
        plan = spatial_preset_placements("grid", list(range(1, 31)), {"rows": 3, "columns": 10})
        records = [(p.fid, p.x, p.y, p.z) for p in plan.placements]
        assert len(records) == 30
        assert records[0] == (1, -4.5, -1.0, 0.0)  # front-left
        assert records[9] == (10, 4.5, -1.0, 0.0)  # front-right
        assert records[29] == (30, 4.5, 1.0, 0.0)  # back-right
        assert plan.resolved["rows"] == 3
        assert plan.resolved["columns"] == 10

    def test_row_zero_is_the_low_end_of_the_row_axis(self):
        # The analysis layer orders rows y-ascending (SPATIAL_ROW_ORDER). If the
        # preset filled from the high end, a rig this tool wrote would read back
        # with its rows flipped.
        plan = spatial_preset_placements("grid", list(range(1, 7)), {"rows": 3, "columns": 2})
        assert [p.y for p in plan.placements] == [-1.0, -1.0, 0.0, 0.0, 1.0, 1.0]

    def test_one_dimension_may_be_omitted_and_is_derived(self):
        plan = spatial_preset_placements("grid", list(range(1, 13)), {"rows": 3})
        assert plan.resolved["columns"] == 4

    def test_a_shape_that_does_not_hold_the_named_fixtures_is_refused(self):
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("grid", list(range(1, 11)), {"rows": 3, "columns": 10})
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("grid", list(range(1, 11)), {"rows": 3})

    def test_a_grid_with_no_shape_is_refused_rather_than_guessed(self):
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("grid", list(range(1, 11)))

    def test_the_xz_orientation_stacks_rows_vertically(self):
        plan = spatial_preset_placements(
            "grid", [1, 2, 3, 4], {"rows": 2, "columns": 2, "orientation": "xz"}
        )
        assert [(p.x, p.y, p.z) for p in plan.placements] == [
            (-0.5, 0.0, -0.5),
            (0.5, 0.0, -0.5),
            (-0.5, 0.0, 0.5),
            (0.5, 0.0, 0.5),
        ]


class TestCircleGeometry:
    def test_four_fixtures_land_on_the_quarter_points(self):
        # cos(pi/2) is 6.1e-17, not 0. The quantisation is what makes this a
        # clean 0.0 instead of a coordinate in scientific notation.
        plan = spatial_preset_placements("circle", [1, 2, 3, 4])
        assert [(p.x, p.y, p.z) for p in plan.placements] == [
            (3.0, 0.0, 0.0),
            (0.0, 3.0, 0.0),
            (-3.0, 0.0, 0.0),
            (0.0, -3.0, 0.0),
        ]

    def test_radius_and_start_angle_are_honoured(self):
        plan = spatial_preset_placements("circle", [1, 2], {"radius": 2.0, "start_angle": 90.0})
        assert [(p.x, p.y) for p in plan.placements] == [(0.0, 2.0), (0.0, -2.0)]

    def test_an_off_axis_point_is_quantised_not_left_full_precision(self):
        plan = spatial_preset_placements("circle", [1, 2, 3, 4, 5, 6, 7, 8], {"radius": 2.0})
        assert (plan.placements[1].x, plan.placements[1].y) == (1.4142, 1.4142)
        for placement in plan.placements:
            assert placement.x == round(placement.x, SPATIAL_PRESET_DECIMALS)

    def test_a_shifted_origin_moves_the_whole_ring(self):
        plan = spatial_preset_placements("circle", [1, 2], {"origin": {"x": -5.0, "y": 1.0}})
        assert [(p.x, p.y, p.z) for p in plan.placements] == [(-2.0, 1.0, 0.0), (-8.0, 1.0, 0.0)]


class TestPresetRefusals:
    def test_an_unknown_parameter_is_refused_not_ignored(self):
        # A misspelled radius that is quietly dropped writes the rig to the
        # wrong size and answers OK.
        with pytest.raises(SpatialPresetError, match="radiuss"):
            spatial_preset_placements("circle", [1, 2], {"radiuss": 4.0})

    def test_a_parameter_belonging_to_another_preset_is_refused(self):
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("row", [1, 2], {"radius": 4.0})

    def test_a_duplicate_fid_is_refused(self):
        with pytest.raises(SpatialPresetError, match="twice"):
            spatial_preset_placements("row", [1, 2, 1])

    def test_non_positive_spacing_is_refused(self):
        with pytest.raises(SpatialPresetError):
            spatial_preset_placements("row", [1, 2], {"spacing": 0})

    def test_an_absurd_coordinate_is_refused_before_it_reaches_a_command(self):
        # Past ~1e16 repr switches to scientific notation and the console would
        # not read the token as the number meant.
        with pytest.raises(SpatialPresetError, match="sanity bound"):
            spatial_preset_placements("row", [1, 2], {"spacing": 999999.0})

    def test_the_same_request_always_yields_the_same_coordinates(self):
        first = spatial_preset_placements("circle", [3, 1, 2], {"radius": 1.7})
        second = spatial_preset_placements("circle", [3, 1, 2], {"radius": 1.7})
        assert first.placements == second.placements


# ==========================================================================
# Command form + scope seal — static (AC-SPATIAL-021)
# ==========================================================================


class TestCommandForm:
    def test_every_value_is_single_quoted(self):
        # §E.2.6a: `Posx -3.5` stores 3.5 and answers OK. The quotes are the
        # whole difference between a correct write and a silent wrong one.
        plan = spatial_preset_placements("row", list(range(11, 19)))
        commands = arrange_write_commands(plan.placements)
        assert commands[0] == "Set Fixture 11 Posx '-3.5'"
        for command in commands:
            assert SET_COMMAND.match(command), command

    def test_no_double_quote_is_ever_emitted(self):
        # server/bridge/protocol.py:109 rejects the character outright.
        plan = spatial_preset_placements("grid", list(range(1, 7)), {"rows": 2, "columns": 3})
        for command in arrange_write_commands(plan.placements):
            assert '"' not in command

    def test_only_the_three_position_axes_are_written(self):
        plan = spatial_preset_placements("grid", list(range(1, 7)), {"rows": 2, "columns": 3})
        commands = arrange_write_commands(plan.placements)
        assert len(commands) == 6 * 3
        assert {SET_COMMAND.match(c).group(2) for c in commands} == {"Posx", "Posy", "Posz"}
        assert [ax for _attr, ax in ARRANGE_AXES] == ["Posx", "Posy", "Posz"]
        assert list(ARRANGE_READ_AXES) == ["posx", "posy", "posz"]
        for command in commands:
            assert not ORIENTATION_WRITE.search(command), command

    def test_the_scope_seal_names_every_foreign_fid(self):
        plan = spatial_preset_placements("row", [11, 12, 13])
        commands = arrange_write_commands(plan.placements)
        assert arrange_scope_violations(commands, [11, 12, 13]) == ()
        violations = arrange_scope_violations(commands, [11, 12])
        assert len(violations) == 3
        assert all("13" in v for v in violations)

    def test_the_scope_seal_rejects_anything_that_is_not_a_position_write(self):
        assert arrange_scope_violations(["Delete Fixture 11"], [11])
        assert arrange_scope_violations(["Set Fixture 11 Rotx '90.0'"], [11])
        assert arrange_scope_violations(["Set Fixture 11 Posx -3.5"], [11])


class TestVerificationTolerance:
    def test_float32_drift_is_within_tolerance(self):
        # The exact live pair (§E.2.6a).
        assert arrange_values_match(9.9, 9.8999996185303) is True

    def test_a_dropped_sign_is_not_within_tolerance(self):
        assert arrange_values_match(-3.5, 3.5) is False

    def test_a_silent_no_op_is_not_within_tolerance(self):
        assert arrange_values_match(-3.5, 0.0) is False

    def test_the_tolerance_cannot_swallow_two_distinct_targets(self):
        # The band has to stay well below the preset layer's quantisation, or a
        # wrong-but-nearby value would verify as correct.
        quantum = 10.0**-SPATIAL_PRESET_DECIMALS
        assert quantum > ARRANGE_VERIFY_ABS_TOLERANCE
        assert quantum > ARRANGE_VERIFY_REL_TOLERANCE * 10.0
        assert arrange_values_match(1.0, 1.0 + quantum) is False


# ==========================================================================
# The write path (AC-SPATIAL-019/020/021/022)
# ==========================================================================


class TestToolRegistration:
    def test_arrange_fixtures_is_a_registered_tool(self):
        assert "arrange_fixtures" in TOOL_NAMES
        names = {d.name for d in registry(rig()).definitions()}
        assert "arrange_fixtures" in names

    def test_its_schema_closes_the_preset_vocabulary(self):
        definition = next(d for d in registry(rig()).definitions() if d.name == "arrange_fixtures")
        assert definition.parameters["properties"]["preset"]["enum"] == list(SPATIAL_PRESETS)
        assert definition.parameters["required"] == ["preset", "fids"]
        assert definition.parameters["additionalProperties"] is False


class TestBackupPrecedesTheWrite:
    """AC-SPATIAL-019 — mutation-grade, and the assertion is about ORDER."""

    def test_every_target_is_read_before_the_first_write_is_sent(self):
        console = rig()
        targets = [11, 12, 13, 14]
        _execution, payload = arrange(console, {"preset": "row", "fids": targets})
        assert payload["verified"] is True

        kinds = [kind for kind, _ in console.calls]
        assert "write" in kinds, "the fixture sent nothing — the assertion would be vacuous"
        first_write = kinds.index("write")
        before_the_write = set(console.calls[:first_write])
        for fid in targets:
            slot = console.slot_of(fid)
            for axis in ARRANGE_READ_AXES:
                assert ("read", f"prop {FIXTURES_PATH}/{slot} {axis}") in before_the_write, (
                    f"fid {fid}'s {axis} was not backed up before the first write"
                )

    def test_the_backup_is_reported_with_the_pre_write_values(self):
        console = ArrangeConsole(
            [(1, 11, "PAR 1", 1.25, -2.5, 4.0), (2, 12, "PAR 2", -1.25, 2.5, 4.0)]
        )
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert payload["backup"] == [
            {"fid": 11, "slot": 1, "name": "PAR 1", "x": 1.25, "y": -2.5, "z": 4.0},
            {"fid": 12, "slot": 2, "name": "PAR 2", "x": -1.25, "y": 2.5, "z": 4.0},
        ]

    def test_a_target_whose_coordinates_cannot_be_read_cancels_the_whole_write(self):
        # Not "skip that one": a coordinate written with no backup has no way
        # back, so the whole bundle is refused (REQ-SPATIAL-020).
        console = rig(unreadable={(3, "posy")})
        execution, payload = arrange(console, {"preset": "row", "fids": [11, 12, 13, 14]})
        assert console.writes == []
        assert execution.result.is_error is True
        assert payload["executed"] is False
        assert [entry["fid"] for entry in payload["unreadable"]] == [13]
        assert "posy" in payload["unreadable"][0]["reason"]

    def test_a_target_that_no_slot_claims_cancels_the_whole_write(self):
        console = rig()
        execution, payload = arrange(console, {"preset": "row", "fids": [11, 99]})
        assert console.writes == []
        assert execution.result.is_error is True
        assert [entry["fid"] for entry in payload["unreadable"]] == [99]

    def test_a_session_with_no_property_read_capability_writes_nothing(self):
        class StateOnly:
            def __init__(self, console):
                self._console = console

            def query_state(self, path):
                return self._console.query_state(path)

        console = rig()
        toolset = build_toolset(execution_port=console, state_port=StateOnly(console))
        execution = toolset.dispatch(
            ToolCall(id="c1", name="arrange_fixtures", arguments={"preset": "row", "fids": [11]})
        )
        assert console.writes == []
        assert execution.result.is_error is True
        assert "back up" in json.loads(execution.result.content)["error"]


class TestRequeryVerification:
    """AC-SPATIAL-020 — mutation-grade. ``ok:true`` is not evidence."""

    def test_a_console_that_reports_ok_but_stored_a_different_value_is_caught(self):
        # The exact live failure: a negative x comes back positive, and every
        # command answered OK (§E.2.6a).
        console = rig(lies={(11, "Posx"): 3.5})
        execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert all(outcome.status == "executed_ok" for outcome in execution.command_outcomes), (
            "the console accepted every line — only the re-query can tell"
        )
        assert execution.result.is_error is True
        assert payload["verified"] is False
        assert payload["succeeded"] is False
        assert payload["status"] == "verification_failed"
        mismatch = next(m for m in payload["mismatches"] if m["axis"] == "Posx")
        assert mismatch["fid"] == 11
        assert mismatch["expected"] == -0.5
        assert mismatch["actual"] == 3.5

    def test_a_silent_no_op_write_is_caught(self):
        # `Posx - 3.5` changed nothing and still answered OK.
        console = rig(lies={(12, "Posy"): None})
        console.fixtures[console.slot_of(12)]["posy"] = 7.0
        execution, payload = arrange(
            console, {"preset": "row", "fids": [11, 12], "origin": [0.0, 1.0, 0.0]}
        )
        assert execution.result.is_error is True
        mismatch = next(m for m in payload["mismatches"] if m["fid"] == 12)
        assert mismatch["axis"] == "Posy"
        assert mismatch["actual"] == 7.0

    def test_float32_read_back_drift_is_a_pass_not_a_failure(self):
        # 9.9 is written, 9.8999996185303 comes back. String equality would
        # call a correct write a failure.
        console = rig()
        _execution, payload = arrange(
            console, {"preset": "row", "fids": [11, 12, 13], "spacing": 9.9}
        )
        assert payload["verified"] is True
        assert payload["succeeded"] is True
        stored = console.coordinates(13)[0]
        assert stored != 9.9, "the fake stored full precision — the drift is not modelled"
        assert repr(stored).startswith("9.8999996")
        # Two lossy steps, not one: float32 storage AND the console's 14-digit
        # rendering. The reported read-back is what the console SAID, which is
        # a third distinct double from both 9.9 and the stored float32 — and
        # all three verify as the same coordinate. Only a numeric comparison
        # can say that.
        reported = payload["readback"][2]["x"]
        assert reported == 9.8999996185303
        assert reported != stored
        assert arrange_values_match(9.9, reported) is True

    def test_a_read_back_that_cannot_be_read_is_a_mismatch_not_a_pass(self):
        console = rig()
        original_query = console.query_property
        state = {"written": False}

        def failing(path, property_name):
            if state["written"] and property_name.lower() == "posz":
                return {"ok": False, "error": "property not readable: posz"}
            return original_query(path, property_name)

        console.query_property = failing  # type: ignore[method-assign]
        original_execute = console.execute

        def executing(command):
            state["written"] = True
            return original_execute(command)

        console.execute = executing  # type: ignore[method-assign]
        execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert execution.result.is_error is True
        assert payload["verified"] is False
        assert payload["mismatches"]

    def test_the_reported_tolerance_is_the_one_that_was_applied(self):
        console = rig()
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert payload["tolerance"] == {
            "relative": ARRANGE_VERIFY_REL_TOLERANCE,
            "absolute": ARRANGE_VERIFY_ABS_TOLERANCE,
        }


class TestScopeSealing:
    """AC-SPATIAL-021 — nothing outside the named set, and no orientation."""

    def test_only_the_named_fixtures_are_written_and_the_rest_are_untouched(self):
        console = rig(count=12)
        targets = [11, 13, 15, 17]
        before = console.snapshot()
        _execution, payload = arrange(
            console, {"preset": "grid", "fids": targets, "rows": 2, "columns": 2}
        )
        assert payload["verified"] is True
        assert console.written_fids == set(targets)
        untouched = [slot for slot, row in before.items() if row["fid"] not in targets]
        assert len(untouched) == 8
        for slot in untouched:
            assert console.fixtures[slot] == before[slot]

    def test_no_orientation_property_is_ever_written(self):
        console = rig()
        arrange(console, {"preset": "circle", "fids": [11, 12, 13, 14]})
        assert console.writes
        for command in console.writes:
            assert not ORIENTATION_WRITE.search(command), command
        assert {SET_COMMAND.match(c).group(2) for c in console.writes} == {
            "Posx",
            "Posy",
            "Posz",
        }

    def test_the_slot_of_every_target_is_measured_not_assumed(self):
        # slot != fid on this rig. A tool that addressed the container by fid
        # would read slot 11 (fid 21) and back up the wrong fixture.
        console = rig(count=12)
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert [entry["slot"] for entry in payload["backup"]] == [1, 2]
        assert console.property_reads[0] == f"prop {FIXTURES_PATH}/1 fid"

    def test_the_walk_stops_as_soon_as_the_last_target_is_located(self):
        console = rig(count=12)
        arrange(console, {"preset": "row", "fids": [11, 12]})
        fid_reads = [read for read in console.property_reads if read.endswith(" fid")]
        assert len(fid_reads) == 2

    def test_a_bundle_that_escaped_its_scope_is_refused_on_its_way_to_the_gate(self, monkeypatch):
        # The seal is not a belief about the builder — it is a check on the
        # TEXT. Corrupt the builder and the handler must still refuse before a
        # single line reaches run_commands.
        console = rig()
        real_builder = tools.arrange_write_commands

        def leaking(placements):
            return (*real_builder(placements), "Set Fixture 99 Posx '0.0'")

        monkeypatch.setattr(tools, "arrange_write_commands", leaking)
        execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert console.writes == []
        assert execution.result.is_error is True
        assert payload["status"] == "refused"
        assert any("99" in violation for violation in payload["scope_violations"])
        # ...and the backup is still in the report, because it was taken first.
        assert len(payload["restore_bundle"]) == 6


class TestRestoreBundle:
    """AC-SPATIAL-019 — the bundle is the ONLY way back, so it covers all."""

    def test_the_bundle_covers_every_target_on_the_happy_path(self):
        console = ArrangeConsole(
            [(slot, slot + 10, f"PAR {slot}", float(slot), -1.0, 2.0) for slot in range(1, 5)]
        )
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12, 13, 14]})
        assert payload["restore_bundle"] == [
            "Set Fixture 11 Posx '1.0'",
            "Set Fixture 11 Posy '-1.0'",
            "Set Fixture 11 Posz '2.0'",
            "Set Fixture 12 Posx '2.0'",
            "Set Fixture 12 Posy '-1.0'",
            "Set Fixture 12 Posz '2.0'",
            "Set Fixture 13 Posx '3.0'",
            "Set Fixture 13 Posy '-1.0'",
            "Set Fixture 13 Posz '2.0'",
            "Set Fixture 14 Posx '4.0'",
            "Set Fixture 14 Posy '-1.0'",
            "Set Fixture 14 Posz '2.0'",
        ]

    def test_the_bundle_covers_every_target_when_the_write_stops_at_the_first_failure(self):
        # run_commands is stop-on-first-failure, so a partial write is the
        # EXPECTED failure mode. A bundle covering only the written prefix
        # would strand exactly the fixtures that did move.
        console = rig(count=6)
        failing = "Set Fixture 13 Posx '0.5'"
        console.write_failures = {failing}
        execution, payload = arrange(console, {"preset": "row", "fids": [11, 12, 13, 14]})
        assert execution.result.is_error is True
        assert payload["executed"] is False
        assert failing in console.writes
        assert console.coordinates(11)[0] == -1.5, "the prefix really did move"
        assert console.coordinates(14)[0] == 0.0, "the tail really did not"
        restored_fids = {int(SET_COMMAND.match(c).group(1)) for c in payload["restore_bundle"]}
        assert restored_fids == {11, 12, 13, 14}
        assert len(payload["restore_bundle"]) == 12

    def test_running_the_bundle_back_actually_restores_the_original_coordinates(self):
        console = ArrangeConsole(
            [
                (1, 11, "PAR 1", -0.75, 2.25, 3.5),
                (2, 12, "PAR 2", 9.9, -4.0, 0.0),
                (3, 13, "PAR 3", 0.0, 0.0, 0.0),
            ]
        )
        before = {fid: console.coordinates(fid) for fid in (11, 12, 13)}
        toolset = registry(console)
        arranged = json.loads(
            toolset.dispatch(
                ToolCall(
                    id="c1",
                    name="arrange_fixtures",
                    arguments={"preset": "row", "fids": [11, 12, 13], "spacing": 2.0},
                )
            ).result.content
        )
        assert arranged["verified"] is True
        assert console.coordinates(11) != before[11]

        restore = toolset.dispatch(
            ToolCall(
                id="c2",
                name="run_commands",
                arguments={"commands": arranged["restore_bundle"]},
            )
        )
        assert restore.result.is_error is False
        for fid, original in before.items():
            assert console.coordinates(fid) == pytest.approx(original, abs=1e-6)

    def test_the_bundle_is_present_even_when_verification_fails(self):
        console = rig(lies={(11, "Posx"): 3.5})
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]})
        assert payload["verified"] is False
        assert len(payload["restore_bundle"]) == 6

    def test_the_bundle_re_writes_the_consoles_own_text_not_a_reparse(self):
        # A float32 value restores bit-for-bit only if the exact string the
        # console handed back goes straight back out.
        console = ArrangeConsole([(1, 11, "PAR 1", _float32(9.9), 0.0, 0.0)])
        _execution, payload = arrange(console, {"preset": "row", "fids": [11]})
        assert payload["restore_bundle"][0] == "Set Fixture 11 Posx '9.8999996185303'"

    def test_the_helper_emits_three_lines_per_backed_up_target(self):
        console = rig(count=3)
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12, 13]})
        assert len(payload["restore_bundle"]) == 9
        assert payload["restore_bundle"] == list(
            arrange_restore_commands(
                # rebuilt from the reported backup, so the report and the
                # helper cannot drift apart silently
                [
                    _BackupRow(entry["fid"], (entry["x"], entry["y"], entry["z"]))
                    for entry in payload["backup"]
                ]
            )
        )


class _BackupRow:
    """Minimal stand-in with the two attributes ``arrange_restore_commands`` reads."""

    def __init__(self, fid, values):
        self.fid = fid
        self.raw = tuple(_console_text(value) for value in values)


class TestLiveLockDemotion:
    """AC-SPATIAL-022 — a demotion is an ANSWER, and it sends NOTHING."""

    def test_the_unlocked_control_actually_writes(self, tmp_path):
        # Non-vacuity first: a zero-send verdict is worthless if the fixture
        # cannot send at all.
        console = rig()
        _execution, payload = arrange(
            console, {"preset": "row", "fids": [11, 12]}, gate=real_gate(tmp_path, locked=False)
        )
        assert console.writes, "the unlocked control sent nothing — the fixture is broken"
        assert payload["verified"] is True

    def test_a_locked_arrangement_sends_nothing_at_all(self, tmp_path):
        console = rig()
        execution, payload = arrange(
            console, {"preset": "row", "fids": [11, 12]}, gate=real_gate(tmp_path, locked=True)
        )
        assert console.writes == []
        # The backup read is itself a console round trip, so it is demoted with
        # everything else (acceptance.md §D): ZERO sends means zero reads too.
        assert console.calls == []

    def test_the_demotion_is_an_answer_not_a_failure(self, tmp_path):
        execution, payload = arrange(
            rig(), {"preset": "row", "fids": [11, 12]}, gate=real_gate(tmp_path, locked=True)
        )
        assert execution.result.is_error is False
        assert payload["status"] == "proposal"
        assert payload["succeeded"] is False
        assert payload["executed"] is False
        assert payload["gate_status"] == "locked"

    def test_the_whole_bundle_is_proposed_not_a_prefix(self, tmp_path):
        _execution, payload = arrange(
            rig(),
            {"preset": "grid", "fids": [11, 12, 13, 14], "rows": 2, "columns": 2},
            gate=real_gate(tmp_path, locked=True),
        )
        assert len(payload["proposed_commands"]) == 4 * 3
        assert {int(SET_COMMAND.match(c).group(1)) for c in payload["proposed_commands"]} == {
            11,
            12,
            13,
            14,
        }

    def test_the_lock_is_what_stopped_it_not_a_refusal_upstream(self, tmp_path):
        # Discriminating: a bad preset, an unknown fid and a failed backup all
        # also produce zero writes. Only the lock produces a proposal.
        console = rig()
        _execution, payload = arrange(
            console, {"preset": "row", "fids": [11, 99]}, gate=real_gate(tmp_path, locked=False)
        )
        assert console.writes == []
        assert payload.get("status") == "refused"


class TestGateChokepoint:
    """AC-SPATIAL-023 — the bundle reaches the console through the one gate."""

    def test_the_bundle_is_screened_before_anything_is_executed(self, tmp_path):
        screened: list[list[str]] = []
        gate = real_gate(tmp_path, locked=False)
        real_screen = gate.screen

        def recording(commands):
            screened.append(list(commands))
            return real_screen(commands)

        gate.screen = recording  # type: ignore[method-assign]
        console = rig()
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]}, gate=gate)
        assert len(screened) == 1
        assert screened[0] == console.writes
        assert payload["verified"] is True

    # AC-SPATIAL-031 — RESOLVED by SPEC-COPILOT-WRITEGATE-001.
    #
    # This replaces the deferred-gap tripwire that used to stand here
    # (`test_a_coordinate_bundle_is_not_yet_classified_risky`). That test
    # asserted `risky is False` and carried an instruction in its own failure
    # message: when the follow-up SPEC landed, it "must be replaced by the
    # approval-flow assertions it was standing in for". These are those
    # assertions. The MAtricks pin it also carried is kept below — a tripwire
    # being lifted is the classic moment to drop a guard that rode along with
    # it, so it moves here rather than disappearing.
    #
    # The gap it named is closed by a closed-set revision (`blacklist.yaml`
    # v1 -> v2, entry "Set Fixture"), not by code: a coordinate bundle now
    # classifies risky, so the gate raises a card AND fires showfile backup
    # rule 3. The four defences that carried this path while the gap was open
    # — original-coordinate backup, re-query verification, restore bundle,
    # scope seal — are unchanged and still asserted elsewhere in this file.
    def test_a_coordinate_write_is_classified_risky(self):
        from server.safety.classify import classify_command
        from server.safety.grammar import validate
        from server.safety.ruleset import load_ruleset

        ruleset = load_ruleset()
        parsed = validate("Set Fixture 11 Posx '-3.5'")
        assert parsed.ok
        finding = classify_command(parsed.parsed, ruleset)
        assert finding.risky is True
        assert finding.category == "blacklisted"
        assert finding.matched_entry == "Set Fixture"

        # The MAtricks programmer form must STAY safe — carried over from the
        # replaced tripwire. `PhaseFromX` is a quoted token, and quoted tokens
        # never match keywords, so the widening cannot reach it.
        matricks = validate("Set Selection MAtricks 'PhaseFromX' 0")
        assert matricks.ok
        assert classify_command(matricks.parsed, ruleset).risky is False

    def test_the_bundle_raises_one_card_and_takes_a_showfile_snapshot(self, tmp_path):
        """AC-SPATIAL-031's two halves: the card AND backup rule ③."""
        snapshots: list[str] = []

        class RecordingBackup:
            def before_risky_execution(self):
                snapshots.append("pre_risky")

        port = ScriptedApprovalPort(approve=True)
        gate = real_gate(tmp_path, locked=False, approval_port=port, backup=RecordingBackup())
        console = rig()
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]}, gate=gate)

        assert len(port.requests) == 1, "exactly one card per bundle"
        approved = port.requests[0]
        assert len(approved.items) == 6, "every line of the bundle is on the card"
        assert all(item.risk_reasons for item in approved.items), (
            "a card with no stated reason asks the operator to approve a blank"
        )
        assert snapshots == ["pre_risky"], "backup rule ③ fires on the risky path"
        assert payload["verified"] is True
        assert console.writes, "approval granted — the write proceeds"

    def test_a_withheld_approval_sends_nothing_and_still_hands_back_the_way_out(self, tmp_path):
        console = rig()
        _execution, payload = arrange(
            console,
            {"preset": "row", "fids": [11, 12]},
            gate=real_gate(tmp_path, locked=False, approve=False),
        )
        assert console.writes == [], "refused approval means ZERO console writes"
        assert payload["succeeded"] is False
        assert len(payload["restore_bundle"]) == 6, (
            "the restore bundle rides along even on the refused path"
        )

    def test_an_unwired_approval_channel_is_not_read_as_pre_approved(self, tmp_path):
        """The fail-CLOSED default, asserted rather than assumed.

        `real_gate` passes an approval port explicitly, so this builds a gate
        the way production would if nobody wired the channel: the constructor
        falls back to `DenyAllApprovalPort`. Safety asymmetry — an absent
        approver must read as "no", never as "yes".
        """
        lock = LiveLock()
        gate = SafetyGate(console=None, audit=AuditLog(tmp_path / "audit"), lock=lock)
        console = rig()
        _execution, payload = arrange(console, {"preset": "row", "fids": [11, 12]}, gate=gate)
        assert console.writes == []
        assert payload["succeeded"] is False

    def test_a_gate_rejection_leaves_the_rig_untouched(self, tmp_path):
        class _Decision:
            def __init__(self, commands):
                self.cleared = False
                self.status = "rejected"
                self.notice = "rejected by the approver"
                self.commands = tuple(_CommandDecision(command) for command in commands)

        class RejectingGate:
            status = None

            def screen(self, commands):
                return _Decision(commands)

        console = rig()
        before = console.snapshot()
        execution, payload = arrange(
            console, {"preset": "row", "fids": [11, 12]}, gate=RejectingGate()
        )
        assert console.writes == []
        assert execution.result.is_error is True
        assert payload["executed"] is False
        assert console.snapshot() == before
        assert len(payload["restore_bundle"]) == 6
