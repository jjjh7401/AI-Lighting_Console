from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts, StateQueryError
from server.tools.probe_preflight import add_listen_port_argument
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)


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
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help=(
            "introspect only: 0-based start into the enumerated name list "
            "(responder 1.6.2). Ignored with --names."
        ),
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help=(
            "introspect only: page from --offset until the responder reports no "
            "more names, then print the merged field list. Advances by entries "
            "RECEIVED, never by a fixed page size."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Console OSC send host.")
    parser.add_argument("--port", type=int, default=8000, help="Console OSC send port.")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Local OSC reply host.")
    add_listen_port_argument(parser)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="State-address reply timeout for the single probe.",
    )
    parser.add_argument("--audit-dir", type=Path, default=None, help="Audit directory override.")
    return parser


def _page_to_exhaustion(state_port, path: str, start: int) -> dict:
    """Walk every introspect window and merge the field lists.

    Advances by entries RECEIVED, never by a fixed page size: the window width
    belongs to the responder's payload budget, so a fixed stride skips names.

    Two stop conditions beyond the normal one, both there because the failure
    they prevent is a silent loop rather than an error:

    - a window that reports no `offset` echo is a pre-1.6.2 responder that
      folded the token into the path; paging cannot work, so stop and say so
      instead of re-reading window 1 forever.
    - a window that returns nothing new also stops -- a responder that ignores
      the offset answers the same first window every time.
    """
    fields: list[dict] = []
    offset = start
    windows: list[dict] = []
    while True:
        payload = state_port.enumerate_fields(path, offset=offset)
        echoed = payload.get("offset")
        windows.append(
            {
                "requested_offset": offset,
                "echoed_offset": echoed,
                "received": len(payload.get("fields") or []),
                "truncated": payload.get("truncated"),
            }
        )
        if echoed is None:
            return {
                **payload,
                "paging": "unsupported",
                "paging_detail": (
                    "reply carried no `offset` echo -- this responder predates 1.6.2 "
                    "and folded the token into the path. Not paged."
                ),
                "windows": windows,
            }
        window = list(payload.get("fields") or [])
        fields.extend(window)
        if not window or not payload.get("truncated"):
            return {
                **payload,
                "fields": fields,
                "offset": start,
                "paging": "complete",
                "windows": windows,
            }
        if echoed != offset:
            return {
                **payload,
                "fields": fields,
                "paging": "stalled",
                "paging_detail": (
                    f"asked for offset {offset} and the responder answered {echoed} -- "
                    "stopped rather than loop on the same window."
                ),
                "windows": windows,
            }
        offset += len(window)


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
        if args.names is not None:
            payload = stack.gate.state_port.query_properties(args.path, args.names)
        elif args.all_pages:
            payload = _page_to_exhaustion(stack.gate.state_port, args.path, args.offset)
        elif args.offset:
            payload = stack.gate.state_port.enumerate_fields(args.path, offset=args.offset)
        else:
            # Unpaged call stays byte-identical -- a port (or responder) that
            # predates 1.6.2 paging still answers it.
            payload = stack.gate.state_port.enumerate_fields(args.path)
    except StateQueryError as error:
        print(f"{mode} failed: {error}", file=sys.stderr)
        return 1
    finally:
        stack.stop()
    print(json.dumps({"mode": mode, "payload": payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
