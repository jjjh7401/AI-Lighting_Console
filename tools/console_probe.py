"""Generic live grandMA3 object/property probe — bridge-direct, gate-bypassed.

**Why this lives OUTSIDE ``server/``.** It imports ``server.bridge`` directly, and
the single-chokepoint guard (``server/tests/test_architecture.py``) admits only a
file-exact whitelist under ``server/tools/``. That whitelist is deliberately
frozen: FXLIB, SCENE, PRECHK, and PRECHK-tool each pin it with a test that fails
if it *grows* (``test_the_exemption_list_is_still_the_two_operator_tools`` ·
``test_operator_utility_exemptions_did_not_grow`` ·
``test_the_operator_tool_exemption_list_is_unchanged``), and AC-DEPLOY-014 keeps a
second allowlist of its own. Four SPECs ratified "these files and no more", so
this probe stays outside the scanned tree instead of widening a safety boundary
for an operator convenience. Run it by path, not as ``-m``.

**Deliberately beneath the gate.** An M0 measurement session has no audit log by
design: the evidence is the verbatim console reply printed here plus the
operator's GUI observation. Routing it through an approval channel would destroy
what it measures. Nothing may import it, and nothing does.

Measured with this tool across three SPECs: FXLIB M0 · SPATIAL-001 M0/M6 ·
GROUPGEN-001 M0/M6 — group-pool reads, patch coordinate reads, the 2-hop fixture
type lookup, and the ``props COUNT`` membership probe that proved gate A NEGATIVE.

Usage (from the project root, with grandMA3 onPC running the responder)::

    .venv/bin/python tools/console_probe.py --listen-port 9005 STEP [STEP ...]

STEP forms::

    exec:<MA3 command line>            fire a command line
    state:<object path>                read an object (children + childCount + truncated)
    prop:<object path>|<PropertyName>  read one property

Prerequisites: the console runs the Lua responder (``console/lua``) and its OSC
input/feedback ports match ``--port`` / ``--listen-port``. Nothing here is
screened, audited, or approved — never point it at a live show.
"""

from __future__ import annotations

import argparse
import json
import queue
import sys
import time
import uuid

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer
from server.bridge.protocol import (
    ProtocolError,
    build_exec_request,
    build_prop_query,
    build_state_query,
    decode_payload,
)


def _await(consumer, *, kind: str, request_id: str, wait: float) -> dict:
    deadline = time.monotonic() + wait
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timeout {wait:.1f}s kind={kind} id={request_id}")
        try:
            message = consumer.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError(f"timeout {wait:.1f}s kind={kind} id={request_id}") from None
        if not message.args:
            continue
        try:
            payload = decode_payload(message.args[0])
        except ProtocolError:
            continue
        if payload.get("kind") == kind and payload.get("id") == request_id:
            return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("steps", nargs="+")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-port", type=int, default=9005)
    parser.add_argument("--wait", type=float, default=6.0)
    parser.add_argument("--pause", type=float, default=0.25)
    args = parser.parse_args(argv)

    config = BridgeConfig(send_host=args.host, send_port=args.port, receive_port=args.listen_port)
    consumer = QueueFeedbackConsumer()
    failures = 0

    with OscBridge(config, consumer=consumer) as bridge:
        for raw in args.steps:
            rid = uuid.uuid4().hex[:8]
            if raw.startswith("exec:"):
                body = raw[5:]
                # the responder answers an exec request with kind="result"
                # (copilot_responder.lua build_exec_result), not kind="exec"
                line, kind, label = build_exec_request(rid, body), "result", f"exec {body!r}"
            elif raw.startswith("state:"):
                body = raw[6:]
                line, kind, label = build_state_query(rid, body), "state", f"state {body!r}"
            elif raw.startswith("prop:"):
                path, _, prop = raw[5:].partition("|")
                line, kind, label = (
                    build_prop_query(rid, path, prop),
                    "prop",
                    f"prop {path!r} {prop!r}",
                )
            else:
                print(f"!! unknown step form: {raw}", file=sys.stderr)
                failures += 1
                continue

            print(f"\n>>> {label}")
            bridge.send_command(line)
            try:
                payload = _await(consumer, kind=kind, request_id=rid, wait=args.wait)
            except TimeoutError as error:
                print(f"<<< TIMEOUT: {error}")
                failures += 1
            else:
                print("<<< " + json.dumps(payload, ensure_ascii=False, sort_keys=True))
                if payload.get("ok") is False:
                    failures += 1
            time.sleep(args.pause)

    print(f"\n=== steps={len(args.steps)} not_ok_or_timeout={failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
