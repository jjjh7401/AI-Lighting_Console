"""Semi-automatic round-trip verification tool against grandMA3 onPC (M2, AC-MVP-012).

This is a DEV TOOL, not a production execution path — exempt from the
REQ-MVP-029 single-chokepoint rule (the M4 import-boundary test whitelists
``server.tools`` explicitly).

Runs the three responder protocol steps against a live console (or the test
fake console) and reports PASS/FAIL per step:

1. ``ping``  — plugin liveness (reply on ``/copilot/feedback``, kind=pong)
2. ``state`` — object-tree snapshot query (reply on ``/copilot/state``)
3. ``exec``  — wrapped command execution with result capture
   (reply on ``/copilot/feedback``, kind=result)

Usage (from the project root)::

    uv run python -m server.tools.responder_roundtrip \
        --host 127.0.0.1 --port 8000 --listen-port 9000 \
        --path "DataPool/Sequences" --exec-command "List" --wait 5

Prerequisites (see console/lua/README.md for the full onPC 2.4.2 setup):
  * onPC running with OSC enabled: input port = ``--port``, an OSC output row
    targeting this host at ``--listen-port``.
  * The CopilotResponder plugin imported/created in the showfile (M2).

Troubleshooting: run ``--diagnose`` to print EVERY OSC message arriving at the
listen port for ``--wait`` seconds (e.g. to detect a console that prepends its
OSC prefix to reply addresses, yielding ``/copilot/copilot/state``).
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer
from server.bridge.protocol import (
    ProtocolError,
    build_exec_request,
    build_ping,
    build_state_query,
    decode_payload,
)

DEFAULT_PATH = "DataPool/Sequences"
DEFAULT_EXEC_COMMAND = "List"


@dataclass(frozen=True)
class StepResult:
    """Outcome of one protocol step."""

    name: str
    ok: bool
    detail: str
    payload: dict | None = None


@dataclass(frozen=True)
class RoundtripReport:
    """All step outcomes of one round-trip run."""

    steps: list[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.steps) and all(step.ok for step in self.steps)


def _await_reply(
    consumer: QueueFeedbackConsumer, *, kind: str, request_id: str, wait: float
) -> dict:
    """Wait for the reply matching (kind, id); tolerate unrelated messages."""
    deadline = time.monotonic() + wait
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timeout after {wait:.1f}s waiting for kind={kind} id={request_id}")
        try:
            message = consumer.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError(
                f"timeout after {wait:.1f}s waiting for kind={kind} id={request_id}"
            ) from None
        if not message.args:
            continue
        try:
            payload = decode_payload(message.args[0])
        except ProtocolError:
            continue  # not a responder payload — ignore
        if payload.get("kind") == kind and payload.get("id") == request_id:
            return payload


def _run_step(
    bridge: OscBridge,
    consumer: QueueFeedbackConsumer,
    *,
    name: str,
    command_line: str,
    reply_kind: str,
    request_id: str,
    wait: float,
) -> StepResult:
    bridge.send_command(command_line)
    try:
        payload = _await_reply(consumer, kind=reply_kind, request_id=request_id, wait=wait)
    except TimeoutError as error:
        return StepResult(name=name, ok=False, detail=str(error))
    ok = bool(payload.get("ok", True))  # pong carries no "ok" field — liveness IS the pass
    detail = "ok" if ok else f"responder error: {payload.get('error', '?')}"
    return StepResult(name=name, ok=ok, detail=detail, payload=payload)


def run_roundtrip(
    config: BridgeConfig,
    *,
    path: str = DEFAULT_PATH,
    exec_command: str = DEFAULT_EXEC_COMMAND,
    wait: float = 5.0,
    skip_exec: bool = False,
) -> RoundtripReport:
    """Execute the ping -> state -> exec protocol steps; never raises on step failure.

    All steps run even after a failure (independent diagnostic evidence).
    """
    run_id = uuid.uuid4().hex[:8]
    consumer = QueueFeedbackConsumer()
    steps: list[StepResult] = []
    with OscBridge(config, consumer=consumer) as bridge:
        steps.append(
            _run_step(
                bridge,
                consumer,
                name="ping",
                command_line=build_ping(f"{run_id}-1"),
                reply_kind="pong",
                request_id=f"{run_id}-1",
                wait=wait,
            )
        )
        steps.append(
            _run_step(
                bridge,
                consumer,
                name="state",
                command_line=build_state_query(f"{run_id}-2", path),
                reply_kind="state",
                request_id=f"{run_id}-2",
                wait=wait,
            )
        )
        if not skip_exec:
            steps.append(
                _run_step(
                    bridge,
                    consumer,
                    name="exec",
                    command_line=build_exec_request(f"{run_id}-3", exec_command),
                    reply_kind="result",
                    request_id=f"{run_id}-3",
                    wait=wait,
                )
            )
    return RoundtripReport(steps=steps)


def run_diagnose(
    listen_host: str,
    listen_port: int,
    *,
    duration: float = 10.0,
    on_message=None,
) -> None:
    """Print every OSC message arriving at the listen port for ``duration`` seconds."""
    if on_message is None:

        def on_message(address: str, args: tuple) -> None:
            print(f"received: {address} {args}")

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(lambda address, *args: on_message(address, tuple(args)))
    server = ThreadingOSCUDPServer((listen_host, listen_port), dispatcher)
    thread = threading.Thread(target=server.serve_forever, name="osc-diagnose", daemon=True)
    thread.start()
    try:
        time.sleep(duration)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1", help="onPC host (default: %(default)s)")
    parser.add_argument(
        "--port", type=int, default=8000, help="onPC OSC UDP input port (default: %(default)s)"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9000,
        help="local port for /copilot/state + /copilot/feedback replies (default: %(default)s)",
    )
    parser.add_argument(
        "--path", default=DEFAULT_PATH, help="object-tree path to query (default: %(default)s)"
    )
    parser.add_argument(
        "--exec-command",
        default=DEFAULT_EXEC_COMMAND,
        help="benign MA3 command for the exec step (default: %(default)s)",
    )
    parser.add_argument("--wait", type=float, default=5.0, help="per-step reply timeout in seconds")
    parser.add_argument("--skip-exec", action="store_true", help="skip the exec step")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="listen-only: print every OSC message on --listen-port for --wait seconds",
    )
    args = parser.parse_args(argv)

    if args.diagnose:
        print(f"diagnose: listening on udp:{args.listen_port} for {args.wait:.1f}s ...")
        run_diagnose("0.0.0.0", args.listen_port, duration=args.wait)
        return 0

    config = BridgeConfig(send_host=args.host, send_port=args.port, receive_port=args.listen_port)
    print(f"round-trip against osc.udp://{args.host}:{args.port} (replies on {args.listen_port})")
    report = run_roundtrip(
        config,
        path=args.path,
        exec_command=args.exec_command,
        wait=args.wait,
        skip_exec=args.skip_exec,
    )
    for step in report.steps:
        marker = "PASS" if step.ok else "FAIL"
        print(f"  [{marker}] {step.name}: {step.detail}")
        if step.payload is not None and step.name == "state" and step.ok:
            children = step.payload.get("children", [])
            print(f"         node={step.payload.get('node')} children={len(children)}")
    print(f"result: {'PASS' if report.ok else 'FAIL'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
