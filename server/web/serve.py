"""Production server composition + CLI (M5 — ``python -m server.web``).

Wires the full stack: provider config (TOML, REQ-MVP-039) -> single active
provider adapter, rulebook fixed prefix (REQ-MVP-007), gate-owned console
stack (``server.safety.bootstrap`` — the chokepoint-preserving composition),
fallback detector (REQ-MVP-040 ii) fed by the round-trip recorder, and the
WebSocket approval channel. Credentials stay in environment variables only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from server.llm.config import DEFAULT_CONFIG_PATH, load_provider_config
from server.llm.factory import build_provider
from server.orchestrator.fallback import FallbackDetector
from server.rulebook.assembly import assemble_prefix
from server.safety.bootstrap import ConsoleStack, build_console_stack
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.measure import RoundTripRecorder

DEFAULT_UI_DIST = Path(__file__).resolve().parents[2] / "ui" / "dist"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m server.web",
        description="grandMA3 AI copilot — Korean chat WebSocket server",
    )
    parser.add_argument("--host", default="127.0.0.1", help="web server bind host")
    parser.add_argument("--port", type=int, default=8765, help="web server port")
    parser.add_argument("--console-host", default="127.0.0.1", help="grandMA3 onPC OSC input host")
    parser.add_argument(
        "--console-port", type=int, default=8000, help="grandMA3 onPC OSC input port"
    )
    parser.add_argument("--receive-port", type=int, default=9000, help="OSC feedback listen port")
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG_PATH), help="provider TOML config path"
    )
    parser.add_argument("--ui-dist", default=str(DEFAULT_UI_DIST), help="built UI directory")
    parser.add_argument(
        "--heartbeat-interval", type=float, default=5.0, help="responder heartbeat seconds"
    )
    parser.add_argument(
        "--backup-poll", type=float, default=30.0, help="periodic-backup poll seconds"
    )
    parser.add_argument(
        "--approval-timeout",
        type=float,
        default=600.0,
        help="pending-approval timeout seconds (deny after)",
    )
    parser.add_argument(
        "--no-session-backup",
        action="store_true",
        help="skip the session-start showfile backup attempt",
    )
    return parser.parse_args(argv)


def build_runtime(args: argparse.Namespace) -> tuple[object, ConsoleStack]:
    """Compose the FastAPI app + console stack from parsed arguments."""
    config = load_provider_config(args.config)
    provider = build_provider(config)
    system_prefix = assemble_prefix()

    recorder = RoundTripRecorder()
    channel = ApprovalChannel(timeout_seconds=args.approval_timeout, recorder=recorder)
    stack = build_console_stack(
        send_host=args.console_host,
        send_port=args.console_port,
        receive_port=args.receive_port,
        approval_port=channel,
        attempt_session_backup=not args.no_session_backup,
    )
    # Judged turns feed the persistent-miss detector; decisions land in the
    # SAME durable audit log the gate writes (REQ-MVP-040 ii).
    recorder.attach_detector(
        FallbackDetector(config.fallback, audit_sink=stack.audit, active_provider=provider.name)
    )

    ui_dist = Path(args.ui_dist)
    deps = WebDeps(
        gate=stack.gate,
        provider=provider,
        system_prefix=system_prefix,
        audit=stack.audit,
        approval_channel=channel,
        recorder=recorder,
        ui_dist=ui_dist if ui_dist.is_dir() else None,
        backup_manager=stack.backup,
        heartbeat_interval_seconds=args.heartbeat_interval,
        backup_poll_seconds=args.backup_poll,
    )
    return create_app(deps), stack


def main(argv: list[str] | None = None, *, run=None) -> int:
    """CLI entry point; ``run`` is injectable (defaults to uvicorn.run)."""
    args = parse_args(argv)
    app, stack = build_runtime(args)
    if run is None:  # pragma: no cover — exercised by real serving only
        import uvicorn

        run = uvicorn.run
    try:
        run(app, host=args.host, port=args.port)
    finally:
        stack.stop()
    return 0
