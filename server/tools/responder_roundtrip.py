"""Semi-automatic round-trip verification tool against grandMA3 onPC (M2, AC-MVP-012).

This is a DEV TOOL, not a production execution path — exempt from the
REQ-MVP-029 single-chokepoint rule (the M4 import-boundary test whitelists
``server.tools`` explicitly).

Runs the responder protocol steps against a live console (or the test
fake console) and reports PASS/FAIL per step:

1. ``ping``  — plugin liveness (reply on ``/copilot/feedback``, kind=pong)
2. ``state`` — object-tree snapshot query (reply on ``/copilot/state``)
3. ``exec``  — wrapped command execution with result capture
   (reply on ``/copilot/feedback``, kind=result)
4. ``prop``  — OPT-IN single-property read (reply kind=prop). Runs last and
   only when both ``--prop-path`` and ``--prop-name`` are given.

Usage (from the project root)::

    uv run python -m server.tools.responder_roundtrip \
        --host 127.0.0.1 --port 8000 --listen-port 9000 \
        --path "DataPool/Sequences" --exec-command "List" --wait 5

MEASURING an unknown property (non-destructive — ``prop`` reads, and
``--skip-exec`` removes the only step that runs a command)::

    uv run python -m server.tools.responder_roundtrip --skip-exec \
        --prop-path "DataPool/Sequences/1/Cue 1" --prop-name CueFade

The reply's ``ok``/``value``/``error`` are printed VERBATIM. A refusal is a
result, not an error of this tool: what the console says it cannot do is the
finding, and this tool must not paraphrase it into something nobody observed.

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
    build_prop_query,
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


def _check_expected_version(step: StepResult, expect_version: str | None) -> StepResult:
    """Fail the ping step early when the LIVE responder version doesn't match.

    Deployment-reliability tool (console/lua/README.md § Deployment
    Reliability): re-importing an updated plugin over an existing same-named
    one has been observed to NOT refresh its stored Lua source (2026-07-24).
    ``--expect-version`` turns "did my deploy actually take effect?" into one
    fast, definitive check instead of a live state-query round-trip.
    """
    if not step.ok or expect_version is None:
        return step
    live_version = (step.payload or {}).get("version")
    if live_version == expect_version:
        return step
    return StepResult(
        name=step.name,
        ok=False,
        detail=(
            f"live responder version {live_version!r} != expected "
            f"{expect_version!r} (the deploy did not take effect -- re-import "
            "did not refresh the running plugin; see console/lua/README.md "
            "§ Deployment Reliability)"
        ),
        payload=step.payload,
    )


def run_roundtrip(
    config: BridgeConfig,
    *,
    path: str = DEFAULT_PATH,
    exec_command: str = DEFAULT_EXEC_COMMAND,
    wait: float = 5.0,
    skip_exec: bool = False,
    expect_version: str | None = None,
    prop_path: str | None = None,
    prop_name: str | None = None,
) -> RoundtripReport:
    """Execute the ping -> state -> exec protocol steps; never raises on step failure.

    All steps run even after a failure (independent diagnostic evidence).
    ``expect_version``, when given, fails the ping step if the LIVE
    responder's reported version doesn't match -- see
    :func:`_check_expected_version`.
    """
    run_id = uuid.uuid4().hex[:8]
    consumer = QueueFeedbackConsumer()
    steps: list[StepResult] = []
    with OscBridge(config, consumer=consumer) as bridge:
        steps.append(
            _check_expected_version(
                _run_step(
                    bridge,
                    consumer,
                    name="ping",
                    command_line=build_ping(f"{run_id}-1"),
                    reply_kind="pong",
                    request_id=f"{run_id}-1",
                    wait=wait,
                ),
                expect_version,
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
        # The prop step is OPT-IN (both --prop-path and --prop-name given) and
        # runs LAST so a failure here cannot mask the three steps that
        # establish the responder is alive at all.
        #
        # Its reason for existing is measurement, not regression: a property
        # this project has never uttered has an UNKNOWN answer, and the only
        # way to learn it is to ask a live console. `prop` accepts an object
        # path containing SPACES (the responder matches
        # `^(.-)%s+(%S+)%s*$`, non-greedy on the path) while the property name
        # must be one token — so `DataPool/Sequences/1/Cue 1` + `CueFade` is
        # structurally utterable. Whether it ANSWERS is what the measurement
        # settles; do not pre-judge it here.
        if prop_path and prop_name:
            steps.append(
                _run_step(
                    bridge,
                    consumer,
                    name="prop",
                    command_line=build_prop_query(f"{run_id}-4", prop_path, prop_name),
                    reply_kind="prop",
                    request_id=f"{run_id}-4",
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
        "--expect-version",
        default=None,
        help=(
            "fail the ping step if the LIVE responder's version doesn't match "
            "(e.g. '1.5.0') -- a fast, definitive 'did my deploy take effect' "
            "check; run this FIRST after every plugin re-import"
        ),
    )
    parser.add_argument(
        "--prop-path",
        default=None,
        help=(
            "object path for an OPT-IN prop step, spaces allowed "
            "(e.g. 'DataPool/Sequences/1/Cue 1'); needs --prop-name"
        ),
    )
    parser.add_argument(
        "--prop-name",
        default=None,
        help=(
            "single-token property name for the prop step (e.g. 'CueFade'); "
            "needs --prop-path. Use this to MEASURE whether a property this "
            "project has never uttered answers at all — the reply's raw value "
            "is printed verbatim, never interpreted"
        ),
    )
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
        expect_version=args.expect_version,
        prop_path=args.prop_path,
        prop_name=args.prop_name,
    )
    for step in report.steps:
        marker = "PASS" if step.ok else "FAIL"
        print(f"  [{marker}] {step.name}: {step.detail}")
        if step.payload is not None and step.name == "ping":
            print(
                f"         live version={step.payload.get('version')} "
                f"plugin={step.payload.get('plugin')}"
            )
        if step.payload is not None and step.name == "state" and step.ok:
            children = step.payload.get("children", [])
            print(f"         node={step.payload.get('node')} children={len(children)}")
        if step.payload is not None and step.name == "prop":
            # Printed VERBATIM including on failure: for a measurement run the
            # console's own refusal wording IS the finding, and paraphrasing it
            # would report something nobody observed.
            print(
                f"         path={step.payload.get('path')!r} "
                f"property={step.payload.get('property')!r} "
                f"ok={step.payload.get('ok')} "
                f"value={step.payload.get('value')!r} "
                f"error={step.payload.get('error')!r}"
            )
    print(f"result: {'PASS' if report.ok else 'FAIL'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
