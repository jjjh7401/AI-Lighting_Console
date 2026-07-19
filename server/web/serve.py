"""Production server composition + CLI (M5 — ``python -m server.web``).

Wires the full stack: provider config (TOML, REQ-MVP-039) -> single active
provider adapter, rulebook fixed prefix (REQ-MVP-007), gate-owned console
stack (``server.safety.bootstrap`` — the chokepoint-preserving composition),
fallback detector (REQ-MVP-040 ii) fed by the round-trip recorder, and the
WebSocket approval channel. Credentials stay in environment variables only.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from server.deploy.compile import LuaCompileChecker
from server.deploy.pipeline import DeployPipeline
from server.llm.config import DEFAULT_CONFIG_PATH, load_provider_config
from server.llm.factory import build_provider
from server.llm.types import LLMProvider
from server.orchestrator.fallback import FallbackDetector
from server.orchestrator.runner import SwitchableProvider
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
    parser.add_argument(
        "--plugin-import-dir",
        default=str(
            Path.home() / "MALightingTechnology" / "gma3_library" / "datapools" / "plugins"
        ),
        help=(
            "onPC plugins-library folder for the file+Import deploy path "
            "(co-located server + console). Pass an empty string to fall back "
            "to the OSC deploy verb (remote console with no shared filesystem)."
        ),
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
        plugin_import_dir=(args.plugin_import_dir or None),
    )

    # AC-MVP-027 part 3 (REQ-MVP-039/040 ii): only when a fallback target is
    # configured do we build a SECOND adapter and wrap the active one in the
    # runtime-swappable indirection — a persistent-miss decision then actually
    # switches which adapter subsequent turns call, not merely a config value
    # a human must apply by restarting the process. Absent a target (today's
    # shipped default — the target is a still-pending M6b-3 human decision),
    # wiring is byte-identical to before: one adapter, decision-only audit.
    active_provider: LLMProvider = provider
    on_fallback = None
    if config.fallback.target_provider is not None:
        target_adapter = build_provider(replace(config, active=config.fallback.target_provider))
        switchable = SwitchableProvider(
            {config.active: provider, config.fallback.target_provider: target_adapter},
            active_name=config.active,
        )
        active_provider = switchable
        on_fallback = switchable.switch_to

    # Judged turns feed the persistent-miss detector; decisions land in the
    # SAME durable audit log the gate writes (REQ-MVP-040 ii).
    recorder.attach_detector(
        FallbackDetector(
            config.fallback,
            audit_sink=stack.audit,
            active_provider=provider.name,
            on_fallback=on_fallback,
        )
    )

    # M7 deploy review flow: a SECOND channel instance (distinct request type,
    # same quadruple-deny semantics) + the deny-by-default deploy pipeline
    # over the gate-owned deploy surface and the gate-shared flag registry.
    review_channel = ApprovalChannel(
        timeout_seconds=args.approval_timeout, recorder=recorder, id_prefix="review"
    )
    deploy_pipeline = DeployPipeline(
        compile_checker=LuaCompileChecker(),
        ruleset=stack.ruleset,
        deploy_port=stack.gate,
        registry=stack.registry,
        audit=stack.audit,
        review_port=review_channel,
    )

    ui_dist = Path(args.ui_dist)
    deps = WebDeps(
        gate=stack.gate,
        provider=active_provider,
        system_prefix=system_prefix,
        audit=stack.audit,
        approval_channel=channel,
        review_channel=review_channel,
        deploy_pipeline=deploy_pipeline,
        recorder=recorder,
        ui_dist=ui_dist if ui_dist.is_dir() else None,
        backup_manager=stack.backup,
        heartbeat_interval_seconds=args.heartbeat_interval,
        backup_poll_seconds=args.backup_poll,
    )
    app = create_app(deps)
    app.state.deps = deps  # composition introspection seam (tests/diagnostics)
    return app, stack


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
