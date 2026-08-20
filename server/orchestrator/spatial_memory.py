"""Remembered rig geometry (SPEC-COPILOT-SPATIALMEM-001).

Patch coordinates do not decay with time — they change when SOMEBODY changes
them. Measured 2026-08-20 on onPC 2.4.2 with an 80-fixture rig: one
``get_spatial_context`` spends one round trip per fixture at 67 ms, and running
the identical request twice cost 9.58 s BOTH times because nothing was
remembered. Ten geometry-led requests in a programming session therefore spend
96 s re-reading bytes that never moved.

This module remembers a COMPLETE read and re-serves it behind a cheap probe.
Two rules carry the whole design:

* **A partial read is never remembered** (REQ-SPATIALMEM-002). The read path
  deliberately returns a DIFFERENT shape when it could not see the whole rig —
  ``partial_fixtures`` instead of ``fixtures``, plus ``analysis_withheld`` — so
  that a caller cannot quote a confident layout for a rig that does not exist
  (SPEC-COPILOT-TRUNCATE-001). Freezing that shape into memory would turn a
  one-turn shortfall into a permanent lie.
* **A remembered answer says it is remembered** (REQ-SPATIALMEM-009). This
  repository's rule is that success comes only from observation, and an axis
  that would not read is itemised by NAME rather than invented
  (``tools.py`` ``SPATIAL_ROTATION_PROPERTIES``). Serving memory as if it were
  a fresh console read breaks exactly that rule, so every reply carries a
  ``freshness`` block naming its source.

The probe is the compromise between the two costs. A full re-read is 80 round
trips; trusting memory blindly is 0 but cannot see the operator re-patching at
the console. Sampling is 4: one container query for the fixture COUNT (catches
add/remove) plus K fixture coordinate reads (catches a move that leaves the
count intact). It is a probabilistic guarantee, not a proof, and the
``freshness`` text says so.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from server.orchestrator.ports import PropertyQueryPort, StateQueryPort
from server.prechk.query import read_properties

#: How many remembered fixtures the probe re-reads. Three (first / middle /
#: last of the remembered slot order) rather than one: a single sample sits at
#: one end of the rig, and the arrangements this app writes — rows, grids,
#: circles — move whole spans at once, so an end-anchored sample is the most
#: likely one to miss a partial move.
PROBE_SAMPLE_SIZE = 3

#: Axes compared during the probe. Deliberately the POSITION triple only: the
#: probe answers "did this rig move", and rotation is remembered alongside but
#: never the thing that decides staleness (a rotation-only edit still fails the
#: coordinate compare when it accompanies a move, and a pure rotation edit is
#: not something this app's arrangement writes produce).
_PROBE_AXES = ("x", "y", "z")

#: Float compare tolerance for the probe. The console stores float32, so a
#: coordinate written as 9.9 reads back as 9.8999996185303 — the same reason
#: ``arrange_fixtures`` compares numerically instead of by string.
_PROBE_ABS_TOLERANCE = 1e-4


def _coords_match(remembered: float, observed: float) -> bool:
    return abs(remembered - observed) <= _PROBE_ABS_TOLERANCE


def _sample_slots(slots: Sequence[int], size: int = PROBE_SAMPLE_SIZE) -> tuple[int, ...]:
    """First / middle / last of ``slots`` — deduped, order preserved."""
    if not slots:
        return ()
    if len(slots) <= size:
        return tuple(slots)
    picks = [slots[0], slots[len(slots) // 2], slots[-1]]
    seen: list[int] = []
    for slot in picks:
        if slot not in seen:
            seen.append(slot)
    return tuple(seen)


@dataclass(frozen=True, slots=True)
class ProbeOutcome:
    """Why the probe said what it said — carried into the reply, not just logged."""

    fresh: bool
    round_trips: int
    sampled_slots: tuple[int, ...]
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RememberedGeometry:
    """One COMPLETE spatial read, plus what the probe needs to re-check it."""

    path: str
    include_rotation: bool
    reply: dict[str, Any]
    #: slot -> (x, y, z) as first observed. The probe's comparison basis.
    coordinates: dict[int, tuple[float, float, float]]
    #: fid -> container slot, so a verified move can be folded back in by fid.
    slots: dict[int, int]
    #: The console's own child count at read time; the probe's count basis.
    child_count: int | None
    read_at_monotonic: float
    read_at_epoch: float


class SpatialMemory:
    """Process-wide remembered geometry, keyed by ``(path, include_rotation)``.

    Process-wide for the reason ``SnapshotCache`` is (``server/web/app.py``):
    coordinates are CONSOLE state, not per-client state, so N open tabs should
    share one read rather than pay N.

    Thread-safe: ``ChatSession.run_instruction`` runs on a worker thread via
    ``asyncio.to_thread``, so two tabs can genuinely enter this from two OS
    threads at once.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, bool], RememberedGeometry] = {}
        self._lock = threading.Lock()

    # -- storage ---------------------------------------------------------------

    def remember(
        self,
        path: str,
        include_rotation: bool,
        reply: dict[str, Any],
        slots: dict[int, int],
    ) -> bool:
        """Store a COMPLETE read. Returns False when the read was partial.

        REQ-SPATIALMEM-002: the partial shape has no ``fixtures`` key, and that
        absence is the whole signal — so this checks for the key rather than
        re-deriving completeness, which would let the two judgments disagree.

        ``slots`` is ``fid -> container slot`` as collected by
        ``read_spatial_fixtures``' ``slot_sink``. A record whose fid has no slot
        cannot be re-addressed, so the read is not remembered at all rather than
        remembered with a hole the probe would silently skip.
        """
        records = reply.get("fixtures")
        if not isinstance(records, list):
            return False
        coordinates: dict[int, tuple[float, float, float]] = {}
        for record in records:
            if not isinstance(record, dict):
                return False
            fid = record.get("fid")
            if not isinstance(fid, int) or isinstance(fid, bool) or fid not in slots:
                return False
            try:
                coordinates[slots[fid]] = (
                    float(record["x"]),
                    float(record["y"]),
                    float(record["z"]),
                )
            except (KeyError, TypeError, ValueError):
                return False
        coverage = reply.get("coverage")
        child_count = coverage.get("of") if isinstance(coverage, dict) else None
        entry = RememberedGeometry(
            path=path,
            include_rotation=include_rotation,
            # Detached from the caller's dict, and WITHOUT its freshness block:
            # the caller stamps its own "read straight off the console" note on
            # the object it returns, and that note is false the moment this copy
            # is re-served. Every served copy gets a fresh block instead.
            reply={key: value for key, value in reply.items() if key != "freshness"},
            coordinates=coordinates,
            slots=dict(slots),
            child_count=child_count if isinstance(child_count, int) else None,
            read_at_monotonic=time.monotonic(),
            read_at_epoch=time.time(),
        )
        with self._lock:
            self._entries[(path, include_rotation)] = entry
        return True

    def peek(self, path: str, include_rotation: bool) -> RememberedGeometry | None:
        with self._lock:
            return self._entries.get((path, include_rotation))

    def forget(self, path: str | None = None) -> None:
        """Drop everything, or every rotation variant of one path."""
        with self._lock:
            if path is None:
                self._entries.clear()
                return
            for key in [key for key in self._entries if key[0] == path]:
                del self._entries[key]

    # -- invalidation ----------------------------------------------------------

    def apply_verified_move(self, moved: dict[int, tuple[float, float, float]]) -> None:
        """Fold a VERIFIED arrangement read-back into memory (REQ-SPATIALMEM-011).

        ``arrange_fixtures`` re-queries every coordinate it wrote and compares
        numerically before reporting success, so these values are observations,
        not predictions — folding them in keeps memory warm without weakening
        what it claims. Entries whose fid is not in ``moved`` are untouched:
        the tool moves exactly the fixtures it was told to.
        """
        if not moved:
            return
        with self._lock:
            for key, entry in list(self._entries.items()):
                records = entry.reply.get("fixtures")
                if not isinstance(records, list):
                    continue
                coordinates = dict(entry.coordinates)
                updated_records: list[Any] = []
                touched = False
                for record in records:
                    if not isinstance(record, dict):
                        updated_records.append(record)
                        continue
                    fid = record.get("fid")
                    slot = entry.slots.get(fid) if isinstance(fid, int) else None
                    if fid in moved and slot is not None:
                        x, y, z = moved[fid]  # type: ignore[index]
                        record = {**record, "x": x, "y": y, "z": z}
                        coordinates[slot] = (x, y, z)
                        touched = True
                    updated_records.append(record)
                if not touched:
                    continue
                self._entries[key] = RememberedGeometry(
                    path=entry.path,
                    include_rotation=entry.include_rotation,
                    reply={**entry.reply, "fixtures": updated_records},
                    coordinates=coordinates,
                    slots=entry.slots,
                    child_count=entry.child_count,
                    read_at_monotonic=time.monotonic(),
                    read_at_epoch=time.time(),
                )

    # -- probe -----------------------------------------------------------------

    def probe(
        self,
        entry: RememberedGeometry,
        state_port: StateQueryPort,
        property_port: PropertyQueryPort,
    ) -> ProbeOutcome:
        """Is the remembered geometry still true? Cheap, and honest when unsure.

        REQ-SPATIALMEM-007: a probe that cannot reach the console returns
        ``fresh=False``. "Could not check" is not "unchanged" — the whole point
        of this module is to never let an unobserved state pass as observed.
        """
        round_trips = 0
        try:
            payload = state_port.query_state(entry.path)
            round_trips += 1
        except Exception as error:
            return ProbeOutcome(False, round_trips, (), f"container re-read failed: {error}")

        node = payload.get("node")
        observed_count = node.get("childCount") if isinstance(node, dict) else None
        if (
            isinstance(observed_count, int)
            and entry.child_count is not None
            and observed_count != entry.child_count
        ):
            return ProbeOutcome(
                False,
                round_trips,
                (),
                (
                    f"fixture count changed: remembered {entry.child_count}, "
                    f"console {observed_count}"
                ),
            )

        slots = _sample_slots(sorted(entry.coordinates))
        for slot in slots:
            reads = read_properties(property_port, f"{entry.path}/{slot}", ("posx", "posy", "posz"))
            round_trips += 1
            remembered = entry.coordinates[slot]
            for index, axis in enumerate(_PROBE_AXES):
                read = reads.get(f"pos{axis}")
                if read is None or not read.ok or read.value is None:
                    return ProbeOutcome(
                        False,
                        round_trips,
                        slots,
                        f"slot {slot} pos{axis} did not read back",
                    )
                try:
                    observed = float(read.value)
                except (TypeError, ValueError):
                    return ProbeOutcome(
                        False, round_trips, slots, f"slot {slot} pos{axis} is not a number"
                    )
                if not _coords_match(remembered[index], observed):
                    return ProbeOutcome(
                        False,
                        round_trips,
                        slots,
                        (
                            f"slot {slot} moved on {axis}: remembered {remembered[index]}, "
                            f"console {observed}"
                        ),
                    )
        return ProbeOutcome(True, round_trips, slots)


def freshness_from_console(round_trips: int) -> dict[str, Any]:
    """The ``freshness`` block for a reply read directly off the console.

    REQ-SPATIALMEM-010: the fresh path carries a source too. A model that only
    ever sees the key on remembered replies learns "key present = suspect"
    instead of "read the key" — so both shapes carry it and the VALUE differs.
    """
    return {
        "source": "console",
        "read_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "age_seconds": 0,
        "round_trips": round_trips,
        "note": "이 좌표는 방금 콘솔에서 직접 읽은 값입니다.",
    }


def freshness_from_memory(entry: RememberedGeometry, outcome: ProbeOutcome) -> dict[str, Any]:
    """The ``freshness`` block for a remembered reply (REQ-SPATIALMEM-009).

    The Korean note is the part that reaches the operator. It states the read
    time, that only a SAMPLE was re-checked, and what the operator should do if
    they edited the patch on the console themselves — the one change this app
    cannot observe (ASSUMPTION-87).
    """
    age = max(time.monotonic() - entry.read_at_monotonic, 0.0)
    minutes = int(age // 60)
    when = time.strftime("%H:%M", time.localtime(entry.read_at_epoch))
    sampled = ", ".join(str(slot) for slot in outcome.sampled_slots) or "없음"
    return {
        "source": "remembered",
        "read_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(entry.read_at_epoch)),
        "age_seconds": round(age, 1),
        "round_trips": outcome.round_trips,
        "revalidated": {
            "fixture_count": True,
            "sampled_slots": list(outcome.sampled_slots),
            "method": "표본 재확인 (전수 아님)",
        },
        "note": (
            f"이 좌표는 {when}에 콘솔에서 읽어 기억해 둔 값입니다"
            f"({minutes}분 전). 방금 픽스처 개수와 표본 {sampled}번을 다시 확인해 "
            "일치했습니다. 다만 전수 재확인은 아니므로, 그 사이 콘솔에서 직접 "
            "패치를 바꾸셨다면 '무대 좌표 다시 읽어줘'라고 알려주세요."
        ),
    }
