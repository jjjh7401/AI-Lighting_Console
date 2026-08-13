"""Live placement-adaptation verification for the basic position sequence.

Rearranges the demo rig (bar / semicircle / triangle), applies one
representative look per placement through server.spatial.pointing, and
restores the original coordinates EXACTLY (raw console strings) afterwards.
Bridge-direct like console_probe.py — run with the web app STOPPED.

Usage: .venv/bin/python tools/placement_verify.py snapshot|<phase>
Phases: line | semicircle | triangle | restore  (snapshot first).
"""

from __future__ import annotations

import json
import math
import queue
import sys
import time
import uuid
from pathlib import Path

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer
from server.bridge.protocol import (
    ProtocolError,
    build_exec_request,
    build_prop_query,
    decode_payload,
)
from server.spatial.pointing import (
    aimed_commands,
    basic_position_presets,
)

SNAPSHOT = Path("/tmp/placement_snapshot.json")
FIXTURES_PATH = "Patch/Stages/1/Fixtures"
MOVER_SLOTS = range(1, 41)  # slot 41 is the origin marker sphere


class Probe:
    def __init__(self) -> None:
        self._config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
        self._consumer = QueueFeedbackConsumer()
        self._bridge = OscBridge(self._config, consumer=self._consumer)

    def __enter__(self) -> Probe:
        self._bridge.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._bridge.__exit__(*args)

    def _await(self, kind: str, rid: str, wait: float = 5.0) -> dict:
        deadline = time.monotonic() + wait
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timeout kind={kind} id={rid}")
            try:
                message = self._consumer.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"timeout kind={kind} id={rid}") from None
            if not message.args:
                continue
            try:
                payload = decode_payload(message.args[0])
            except ProtocolError:
                continue
            if payload.get("kind") == kind and payload.get("id") == rid:
                return payload

    def prop(self, path: str, name: str) -> str:
        rid = uuid.uuid4().hex[:8]
        self._bridge.send_command(build_prop_query(rid, path, name))
        reply = self._await("prop", rid)
        if reply.get("ok") is not True:
            raise RuntimeError(f"prop {path}|{name}: {reply}")
        return str(reply["value"])

    def exec(self, body: str) -> None:
        rid = uuid.uuid4().hex[:8]
        self._bridge.send_command(build_exec_request(rid, body))
        reply = self._await("result", rid)
        if reply.get("ok") is not True:
            raise RuntimeError(f"exec {body!r}: {reply}")
        time.sleep(0.03)


def snapshot(probe: Probe) -> list[dict]:
    rows = []
    for slot in MOVER_SLOTS:
        path = f"{FIXTURES_PATH}/{slot}"
        rows.append(
            {
                "fid": int(probe.prop(path, "FID")),
                "raw": [probe.prop(path, axis) for axis in ("Posx", "Posy", "Posz")],
            }
        )
    SNAPSHOT.write_text(json.dumps(rows))
    return rows


def write_positions(probe: Probe, placements: list[tuple[int, float, float, float]]) -> None:
    for fid, x, y, z in placements:
        for axis, value in (("Posx", x), ("Posy", y), ("Posz", z)):
            probe.exec(f"Set Fixture {fid} {axis} '{value}'")


def apply_look(
    probe: Probe, fixtures: list[tuple[int, tuple[float, float, float]]], label: str
) -> None:
    looks = {name: (aims, skipped) for name, aims, skipped in basic_position_presets(fixtures)}
    aims, skipped = looks[label]
    probe.exec("ClearAll")
    for command in aimed_commands(aims, dimmer=100.0):
        probe.exec(command)
    print(f"applied {label}: {len(aims)} fixtures, skipped {list(skipped)}")


def placements_for(phase: str, fids: list[int]) -> list[tuple[int, float, float, float]]:
    n = len(fids)
    if phase == "line":
        return [(fid, round(-9.75 + 19.5 * i / (n - 1), 4), 0.0, 6.0) for i, fid in enumerate(fids)]
    if phase == "semicircle":
        return [
            (
                fid,
                round(7.0 * math.cos(math.pi * i / (n - 1)), 4),
                round(7.0 * math.sin(math.pi * i / (n - 1)), 4),
                6.0,
            )
            for i, fid in enumerate(fids)
        ]
    if phase == "triangle":
        vertices = [(-8.0, -5.0), (8.0, -5.0), (0.0, 7.0)]
        points: list[tuple[float, float]] = []
        per_side = n // 3
        extra = n - per_side * 3
        for side in range(3):
            ax, ay = vertices[side]
            bx, by = vertices[(side + 1) % 3]
            count = per_side + (1 if side < extra else 0)
            for i in range(count):
                t = i / count
                points.append((round(ax + (bx - ax) * t, 4), round(ay + (by - ay) * t, 4)))
        return [(fid, x, y, 6.0) for fid, (x, y) in zip(fids, points, strict=True)]
    raise SystemExit(f"unknown phase {phase!r}")


LOOK_FOR = {"line": "Fan Out", "semicircle": "Ring Out", "triangle": "Center"}


def main() -> int:
    phase = sys.argv[1]
    with Probe() as probe:
        if phase == "snapshot":
            rows = snapshot(probe)
            print(f"snapshot: {len(rows)} movers -> {SNAPSHOT}")
            return 0
        rows = json.loads(SNAPSHOT.read_text())
        fids = [row["fid"] for row in rows]
        if phase == "restore":
            for row in rows:
                for axis, raw in zip(("Posx", "Posy", "Posz"), row["raw"], strict=True):
                    probe.exec(f"Set Fixture {row['fid']} {axis} '{raw}'")
            probe.exec("ClearAll")
            check = probe.prop(f"{FIXTURES_PATH}/1", "Posx")
            print(f"restored {len(rows)} movers; slot1 Posx readback = {check}")
            return 0
        placements = placements_for(phase, fids)
        write_positions(probe, placements)
        fixtures = [(fid, (x, y, z)) for fid, x, y, z in placements]
        apply_look(probe, fixtures, LOOK_FOR[phase])
    return 0


if __name__ == "__main__":
    sys.exit(main())
