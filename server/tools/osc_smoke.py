"""Manual OSC smoke test against a real grandMA3 onPC instance (M1 deliverable).

This is a DEV TOOL, not a production execution path — it is exempt from the
REQ-MVP-029 single-chokepoint rule (the M4 import-boundary test whitelists
``server.tools`` explicitly).

Usage (from the project root)::

    uv run python -m server.tools.osc_smoke --host 127.0.0.1 --port 8000 \
        --listen-port 9000 --wait 5 "List"

Prerequisites:
  * grandMA3 onPC 2.4.2 running with OSC enabled and its UDP *input* port set
    to ``--port``.
  * Verify command arrival in the onPC command line history.
  * OSC feedback on ``/copilot/feedback`` requires the console-side Lua
    responder (milestone M2) — with a bare onPC, "no feedback" is EXPECTED
    at M1 and is not a failure.
"""

from __future__ import annotations

import argparse
import queue
import sys

from server.bridge.osc import BridgeConfig, OscBridge, QueueFeedbackConsumer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", help='MA3 command line to send (e.g. "List")')
    parser.add_argument("--host", default="127.0.0.1", help="onPC host (default: %(default)s)")
    parser.add_argument(
        "--port", type=int, default=8000, help="onPC OSC UDP input port (default: %(default)s)"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9000,
        help="local port to listen on for /copilot/feedback (default: %(default)s)",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=5.0,
        help="seconds to wait for feedback before giving up (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    config = BridgeConfig(send_host=args.host, send_port=args.port, receive_port=args.listen_port)
    consumer = QueueFeedbackConsumer()
    with OscBridge(config, consumer=consumer) as bridge:
        print(f"sending to osc.udp://{args.host}:{args.port}/copilot/cmd -> {args.command!r}")
        try:
            bridge.send_command(args.command)
        except ValueError as error:
            print(f"send rejected: {error}", file=sys.stderr)
            return 1
        print(f"listening on udp:{args.listen_port} for /copilot/feedback ({args.wait:.1f}s)...")
        try:
            message = consumer.get(timeout=args.wait)
        except queue.Empty:
            print("no feedback received (expected at M1 without the M2 Lua responder)")
        else:
            print(f"feedback received: {message.address} {message.args}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
