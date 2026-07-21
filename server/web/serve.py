"""Production server composition + CLI (M5 — ``python -m server.web``).

Wires the full stack: provider config (TOML, REQ-MVP-039) -> single active
provider adapter, rulebook fixed prefix (REQ-MVP-007), gate-owned console
stack (``server.safety.bootstrap`` — the chokepoint-preserving composition),
fallback detector (REQ-MVP-040 ii) fed by the round-trip recorder, and the
WebSocket approval channel. Credentials stay in environment variables only.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from server.deploy.compile import LuaCompileChecker
from server.deploy.keystore import (
    KeystoreUnavailableError,
    SessionKeyStore,
    inject_active_provider_key,
)
from server.deploy.pipeline import DeployPipeline
from server.llm.config import DEFAULT_CONFIG_PATH, load_provider_config
from server.llm.factory import build_provider
from server.llm.types import LLMProvider
from server.orchestrator.fallback import FallbackDetector
from server.orchestrator.runner import SwitchableProvider
from server.resources import resource_base
from server.rulebook.assembly import assemble_prefix
from server.safety.bootstrap import ConsoleStack, build_console_stack
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.handshake import TAURI_ORIGINS, HandshakePolicy, browser_origins_for
from server.web.launcher import (
    LAUNCH_TOKEN_ENV,
    PortInUseError,
    apply_keyring_backend_pin,
    assert_keyring_backend,
    generate_launch_token,
    install_signal_handlers,
    make_shutdown_handler,
    open_app_browser,
    require_ports_available,
    run_self_check,
    serve_local_url,
)
from server.web.measure import RoundTripRecorder
from server.web.provision_api import ProvisionDeps
from server.web.settings_api import SettingsDeps


def default_ui_dist() -> Path:
    """Resolve the built-UI directory (dev root or frozen ``_MEIPASS``).

    Routes through :func:`server.resources.resource_base` so a frozen bundle finds
    ``ui/dist`` under ``sys._MEIPASS`` (research §A.4, M6).
    """
    return resource_base() / "ui" / "dist"


# Computed at import; inside a frozen bundle the module is imported with
# sys.frozen set, so this constant already resolves under _MEIPASS.
DEFAULT_UI_DIST = default_ui_dist()


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
        "--no-browser",
        action="store_true",
        help="do not open the default browser at start (headless / CI runs)",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help=(
            "run the OS-keyring backend + roundtrip self-check and exit "
            "(the mode the packaged binary runs to prove the frozen keychain)"
        ),
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


def build_handshake_policy(args: argparse.Namespace) -> HandshakePolicy:
    """Compose the ``/ws`` Origin+token policy for this launch (REQ-DEPLOY-002a).

    The token comes from the spawning host when there is one (the Stage-2 Tauri
    shell mints it and passes it in the sidecar's environment, M7.4); a
    standalone Stage-1 launch mints its own. It is never written to disk and
    never re-exported into the parent environment (AC-DEPLOY-029).

    Stage-1 browser origins are token-OPTIONAL by design: a browser has no
    leak-resistant channel to receive the token, so there the Origin allowlist
    is the real CSWSH closer and the token is defense-in-depth (plan §M7.1).
    """
    return HandshakePolicy(
        token=os.environ.get(LAUNCH_TOKEN_ENV) or generate_launch_token(),
        trusted_origins=TAURI_ORIGINS,
        browser_origins=browser_origins_for(args.host, args.port),
    )


def build_runtime(args: argparse.Namespace) -> tuple[object, ConsoleStack]:
    """Compose the FastAPI app + console stack from parsed arguments."""
    config = load_provider_config(args.config)
    config_path = Path(args.config)

    # @MX:NOTE: [AUTO] REQ-DEPLOY-028 startup active-provider key injection — the
    #   packaged app has no terminal to export env vars, so the active provider's
    #   stored key must cross into the process env BEFORE build_provider() builds
    #   the client (which reads its key from env). overwrite=False so an operator's
    #   already-set env key wins; a locked/denied store degrades to the REQ-DEPLOY-
    #   006a settings-UI session path without aborting start-up (never writes disk).
    try:
        inject_active_provider_key(seed_path=config_path, overwrite=False)
    except KeystoreUnavailableError as error:
        print(
            f"[startup] OS credential store unavailable ({error}); no API key "
            "injected — enter one in the settings UI (session-only fallback).",
            file=sys.stderr,
        )
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
    # M10 Part D: compose the M3/M4 deploy-shell REST routers into WebDeps — the
    # M6 "serve.py composition" obligation (settings_api/provision_api docstrings)
    # that was missed, so the packaged app 404'd its entire in-app config surface.
    # settings_path defaults to None -> the OS-standard user config dir (writable
    # under a frozen bundle); seed_path honours --config; the SessionKeyStore is
    # the REQ-DEPLOY-006a in-memory fallback for a store-unavailable key write.
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
        settings=SettingsDeps(seed_path=config_path, session=SessionKeyStore()),
        provision=ProvisionDeps(seed_path=config_path),
        handshake=build_handshake_policy(args),
    )
    app = create_app(deps)
    app.state.deps = deps  # composition introspection seam (tests/diagnostics)
    return app, stack


def main(argv: list[str] | None = None, *, run=None, keyring_module=None) -> int:
    """CLI entry point; ``run`` and ``keyring_module`` are injectable (tests).

    Process-start wiring (M6): keyring backend pin + fail-closed guard
    (research §B.3), port-in-use fail-loud (no silent random-port fallback,
    REQ-DEPLOY-026), browser open + graceful process-tree shutdown. ``--self-check``
    runs the frozen keyring roundtrip (research §B.4) and exits.
    """
    args = parse_args(argv)

    # --self-check: the keyring backend + roundtrip verification the PACKAGED
    # binary runs (dist/<app>/<app> --self-check). Exits without serving.
    if args.self_check:
        apply_keyring_backend_pin()
        return run_self_check(keyring_module=keyring_module)

    real_serve = run is None
    if real_serve:
        # Pin the OS keyring backend BEFORE the first backend selection (§B.3).
        apply_keyring_backend_pin()

    # Fail-closed: refuse to boot on the wrong keyring backend (REQ-DEPLOY-006a).
    # Enforced on the real-serve path (the packaged app) and whenever a test
    # injects an explicit ``keyring_module``; an injected ``run`` without a
    # keyring_module is a serve-wiring test and does not exercise the guard
    # against (possibly mutated) global keyring state.
    if real_serve or keyring_module is not None:
        assert_keyring_backend(keyring_module=keyring_module)

    if real_serve:
        try:
            require_ports_available(
                [
                    (args.host, args.port, "web UI"),
                    ("127.0.0.1", args.receive_port, "OSC feedback listen"),
                ]
            )
        except PortInUseError as error:  # pragma: no cover — needs an occupied port
            print(error.guidance, file=sys.stderr)
            return 2

    app, stack = build_runtime(args)
    try:
        if real_serve:  # pragma: no cover — exercised by real serving only
            import threading

            import uvicorn

            install_signal_handlers(make_shutdown_handler(stack))
            url = serve_local_url(args.host, args.port)
            threading.Timer(
                1.0,
                open_app_browser,
                kwargs={"url": url, "enabled": not args.no_browser},
            ).start()
            uvicorn.run(app, host=args.host, port=args.port)
        else:
            run(app, host=args.host, port=args.port)
    finally:
        stack.stop()
    return 0
