"""Remembered rig geometry (SPEC-COPILOT-SPATIALMEM-001).

Measured 2026-08-20 on onPC 2.4.2 with an 80-fixture rig: ``get_spatial_context``
spends one round trip per fixture at 67 ms, and the identical request run twice
cost 9.58 s BOTH times because nothing was remembered.

Every test here defends one of the four properties that make remembering safe
rather than merely fast, and each has to go RED when its guard is deleted:

  * **a hit costs a PROBE, not a walk** — the whole point, asserted as round
    trips against the console double rather than as wall clock.
  * **a probe that disagrees re-reads** — a fixture count change, a moved
    coordinate and a probe that could not reach the console all fall back to
    the full read. "Could not check" is never "unchanged".
  * **a partial read is never remembered** — the read path returns a DIFFERENT
    shape when it could not see the whole rig, and freezing that shape would
    keep answering for a rig nobody finished reading.
  * **a remembered reply says so** — `freshness.source` distinguishes the two,
    because this repository's rule is that success comes only from observation.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.spatial_memory import PROBE_SAMPLE_SIZE, SpatialMemory
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, build_toolset
from server.tests.test_spatial_context import (
    FIXTURES_PATH,
    RecordingExecutionPort,
    SpatialRig,
    _bar,
    _fixture,
)

TOOL = "get_spatial_context"
ARRANGE = "arrange_fixtures"


def _registry(rig, memory, execution_port=None):
    return build_toolset(
        execution_port=execution_port or RecordingExecutionPort(),
        state_port=rig,
        spatial_memory=memory,
    )


def _read(registry, **arguments) -> dict:
    execution = registry.dispatch(ToolCall(id="c", name=TOOL, arguments=dict(arguments)))
    assert execution.result.is_error is False
    return json.loads(execution.result.content)


class TestAHitCostsAProbeNotAWalk:
    def test_the_second_read_does_not_walk_every_fixture(self):
        rig = SpatialRig(_bar(12))
        registry = _registry(rig, SpatialMemory())

        first = _read(registry)
        walked = len(rig.property_calls)
        rig.property_calls.clear()
        second = _read(registry)

        # Same answer, and the fixtures are the ones the console gave.
        assert [f["fid"] for f in second["fixtures"]] == [f["fid"] for f in first["fixtures"]]
        # The probe reads three axes on at most PROBE_SAMPLE_SIZE fixtures.
        assert len(rig.property_calls) <= PROBE_SAMPLE_SIZE * 3
        # Non-vacuity: the first read really did cost a per-fixture walk, so
        # the comparison above is measuring a reduction and not an empty rig.
        assert walked >= 12
        assert len(rig.property_calls) < walked

    def test_the_probe_re_reads_the_container_exactly_once(self):
        rig = SpatialRig(_bar(8))
        registry = _registry(rig, SpatialMemory())
        _read(registry)
        rig.state_calls.clear()

        _read(registry)

        assert rig.state_calls == [FIXTURES_PATH]

    def test_a_rotation_read_is_remembered_apart_from_a_position_read(self):
        # Different property sets are different reads. Serving one for the
        # other would either invent rotations or drop measured ones.
        rig = SpatialRig(_bar(4))
        registry = _registry(rig, SpatialMemory())
        _read(registry)
        rig.property_calls.clear()

        _read(registry, include_rotation=True)

        # A walk, not a probe: this key had nothing remembered.
        assert len(rig.property_calls) > PROBE_SAMPLE_SIZE * 3


class TestAProbeThatDisagreesReReads:
    def test_a_moved_fixture_forces_a_full_re_read(self):
        rig = SpatialRig(_bar(6))
        registry = _registry(rig, SpatialMemory())
        _read(registry)

        # The operator drags a fixture on the console — the one change this
        # app cannot observe. Slot 1 is in the probe's sample.
        rig.fixtures[1]["posx"] = "99.0"
        rig.property_calls.clear()
        reply = _read(registry)

        assert reply["freshness"]["source"] == "console"
        assert [f["x"] for f in reply["fixtures"]][0] == 99.0
        assert len(rig.property_calls) > PROBE_SAMPLE_SIZE * 3

    def test_a_changed_fixture_count_forces_a_full_re_read(self):
        rig = SpatialRig(_bar(6))
        registry = _registry(rig, SpatialMemory())
        _read(registry)

        rig.fixtures[7] = _fixture(7, "7", "PAR 7", x="6.0")
        rig.declared = 7
        reply = _read(registry)

        assert reply["freshness"]["source"] == "console"
        assert len(reply["fixtures"]) == 7

    def test_a_probe_that_cannot_reach_the_console_re_reads(self):
        # REQ-SPATIALMEM-007. A probe failure is not a hit: "could not check"
        # must never pass as "unchanged".
        rig = SpatialRig(_bar(5))
        memory = SpatialMemory()
        registry = _registry(rig, memory)
        _read(registry)
        entry = memory.peek(FIXTURES_PATH, False)
        assert entry is not None

        class _Dead:
            def query_state(self, path):
                raise ConnectionError("console gone")

        outcome = memory.probe(entry, _Dead(), rig)
        assert outcome.fresh is False
        assert outcome.reason is not None

    def test_a_sampled_axis_that_stops_reading_is_not_a_hit(self):
        rig = SpatialRig(_bar(5))
        memory = SpatialMemory()
        registry = _registry(rig, memory)
        _read(registry)
        entry = memory.peek(FIXTURES_PATH, False)
        assert entry is not None

        rig.fixtures[1]["posy"] = None  # the console stops answering for it

        outcome = memory.probe(entry, rig, rig)
        assert outcome.fresh is False
        assert "posy" in (outcome.reason or "")

    def test_force_refresh_walks_even_when_the_probe_would_pass(self):
        rig = SpatialRig(_bar(9))
        registry = _registry(rig, SpatialMemory())
        _read(registry)
        rig.property_calls.clear()

        reply = _read(registry, force_refresh=True)

        assert reply["freshness"]["source"] == "console"
        assert len(rig.property_calls) > PROBE_SAMPLE_SIZE * 3


class TestAPartialReadIsNeverRemembered:
    def test_a_truncated_rig_is_not_stored(self):
        # The console says it holds 9 but hands over 4 and the slot probe
        # cannot recover the rest, so the reply carries `partial_fixtures`.
        rig = SpatialRig(_bar(4), declared=9, flag=True)
        memory = SpatialMemory()
        registry = _registry(rig, memory)

        reply = _read(registry)

        assert "partial_fixtures" in reply
        assert memory.peek(FIXTURES_PATH, False) is None

    def test_a_partial_read_still_walks_on_the_next_call(self):
        rig = SpatialRig(_bar(4), declared=9, flag=True)
        registry = _registry(rig, SpatialMemory())
        _read(registry)
        rig.property_calls.clear()

        _read(registry)

        assert len(rig.property_calls) > PROBE_SAMPLE_SIZE * 3


class TestARememberedReplySaysSo:
    def test_a_console_read_is_labelled_console(self):
        registry = _registry(SpatialRig(_bar(3)), SpatialMemory())
        assert _read(registry)["freshness"]["source"] == "console"

    def test_a_remembered_read_is_labelled_and_dated(self):
        rig = SpatialRig(_bar(3))
        registry = _registry(rig, SpatialMemory())
        _read(registry)

        freshness = _read(registry)["freshness"]

        assert freshness["source"] == "remembered"
        assert freshness["revalidated"]["sampled_slots"]
        assert freshness["age_seconds"] >= 0
        # The operator-facing sentence has to name the one thing the probe
        # cannot see, or the disclosure is decoration.
        assert "콘솔에서 직접" in freshness["note"]

    def test_every_reply_carries_a_freshness_block(self):
        # REQ-SPATIALMEM-010: a key present only on remembered replies teaches
        # "key present = suspect" instead of "read the key".
        rig = SpatialRig(_bar(3))
        registry = _registry(rig, SpatialMemory())
        assert "freshness" in _read(registry)
        assert "freshness" in _read(registry)


class TestTheWriteAxisKeepsMemoryHonest:
    def _elevation(self, registry, fids, height):
        return registry.dispatch(
            ToolCall(
                id="w",
                name=ARRANGE,
                arguments={
                    "preset": "elevation",
                    "fids": list(fids),
                    "height": height,
                },
            )
        )

    def test_a_verified_move_updates_memory_instead_of_dropping_it(self):
        rig = SpatialRig(_bar(3))
        memory = SpatialMemory()
        registry = _registry(rig, memory)
        _read(registry)

        memory.apply_verified_move({2: (1.0, 2.0, 6.0)})

        entry = memory.peek(FIXTURES_PATH, False)
        assert entry is not None
        moved = next(f for f in entry.reply["fixtures"] if f["fid"] == 2)
        assert (moved["x"], moved["y"], moved["z"]) == (1.0, 2.0, 6.0)
        assert entry.coordinates[entry.slots[2]] == (1.0, 2.0, 6.0)

    def test_an_untouched_fixture_keeps_its_measured_coordinates(self):
        rig = SpatialRig(_bar(3))
        memory = SpatialMemory()
        registry = _registry(rig, memory)
        before = _read(registry)["fixtures"]

        memory.apply_verified_move({2: (1.0, 2.0, 6.0)})

        entry = memory.peek(FIXTURES_PATH, False)
        assert entry is not None
        untouched = next(f for f in entry.reply["fixtures"] if f["fid"] == 1)
        assert untouched == next(f for f in before if f["fid"] == 1)

    def test_forgetting_drops_every_rotation_variant_of_one_path(self):
        rig = SpatialRig(_bar(3))
        memory = SpatialMemory()
        registry = _registry(rig, memory)
        _read(registry)
        _read(registry, include_rotation=True)

        memory.forget(FIXTURES_PATH)

        assert memory.peek(FIXTURES_PATH, False) is None
        assert memory.peek(FIXTURES_PATH, True) is None


class TestUnwiredMemoryChangesNothing:
    def test_without_a_store_every_call_walks_the_rig(self):
        # REQ-SPATIALMEM-004. The default has to stay byte-identical to the
        # pre-SPEC path, because the existing suites count round trips.
        rig = SpatialRig(_bar(7))
        registry = build_toolset(execution_port=RecordingExecutionPort(), state_port=rig)
        registry.dispatch(ToolCall(id="a", name=TOOL, arguments={}))
        first = len(rig.property_calls)
        rig.property_calls.clear()

        registry.dispatch(ToolCall(id="b", name=TOOL, arguments={}))

        assert len(rig.property_calls) == first
        assert first >= 7


def test_the_default_rig_path_is_the_one_under_test():
    # Guards the import above: a renamed default would silently make every
    # peek() in this file look at a key nothing was ever stored under.
    assert DEFAULT_RIG_CONTEXT_PATHS["fixtures"] == FIXTURES_PATH
