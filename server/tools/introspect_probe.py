from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts, StateQueryError


def _names_arg(value: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    if not names:
        raise argparse.ArgumentTypeError("--names must include at least one property name")
    return names


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send one gate-audited introspect or props query to a console responder."
    )
    parser.add_argument("--path", required=True, help="Object-tree path to inspect.")
    parser.add_argument(
        "--names",
        type=_names_arg,
        default=None,
        metavar="A,B,C",
        help="Comma-separated property names; omitted sends introspect.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Console OSC send host.")
    parser.add_argument("--port", type=int, default=8000, help="Console OSC send port.")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Local OSC reply host.")
    parser.add_argument("--listen-port", type=int, default=9000, help="Local OSC reply port.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="State-address reply timeout for the single probe.",
    )
    parser.add_argument("--audit-dir", type=Path, default=None, help="Audit directory override.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_host=args.listen_host,
        receive_port=args.listen_port,
        audit_dir=args.audit_dir,
        timeouts=LinkTimeouts(state_query_seconds=args.timeout_seconds),
        attempt_session_backup=False,
    )
    mode = "props" if args.names is not None else "introspect"
    try:
        if args.names is None:
            payload = stack.gate.state_port.enumerate_fields(args.path)
        else:
            payload = stack.gate.state_port.query_properties(args.path, args.names)
    except StateQueryError as error:
        print(f"{mode} failed: {error}", file=sys.stderr)
        return 1
    finally:
        stack.stop()
    print(json.dumps({"mode": mode, "payload": payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
