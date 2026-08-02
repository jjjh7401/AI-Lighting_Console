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
import socket
import sys
import threading
from collections.abc import MutableMapping
from dataclasses import replace
from pathlib import Path

from server.deploy.compile import LuaCompileChecker
from server.deploy.keystore import (
    KeystoreUnavailableError,
    SessionKeyStore,
    inject_active_provider_key,
)
from server.deploy.pipeline import DeployPipeline
from server.deploy.settings import resolve_effective_settings
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
from server.web.console_probe import make_console_input_probe
from server.web.handshake import TAURI_ORIGINS, HandshakePolicy, browser_origins_for
from server.web.host_channel import emit_ready, emit_startup_error, make_status_emitter
from server.web.launcher import (
    LAUNCH_TOKEN_ENV,
    PortInUseError,
    apply_keyring_backend_pin,
    assert_keyring_backend,
    become_session_leader,
    generate_launch_token,
    host_declared,
    install_parent_watchdog,
    install_signal_handlers,
    make_shutdown_handler,
    open_app_browser,
    require_ports_available,
    run_self_check,
    serve_local_url,
    wait_until_serving,
)
from server.web.measure import RoundTripRecorder
from server.web.provision_api import ProvisionDeps
from server.web.reply_discovery import make_reply_port_diagnostic
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


# The five settings-backed flags: (arg attribute, settings key). An unpassed flag
# must fall through to the user file, not its argparse literal default (the M7.3
# `console_port` gap, which bit `receive_port` in production — the packaged shell
# spawns the sidecar with NO args, so every one of these was silently the default
# no matter what the user saved).
_SETTINGS_BACKED_FLAGS: tuple[tuple[str, str], ...] = (
    ("host", "web_host"),
    ("port", "web_port"),
    ("console_host", "console_host"),
    ("console_port", "console_port"),
    ("receive_port", "receive_port"),
)


def _explicitly_passed(argv: list[str] | None) -> dict[str, object]:
    """Return only the settings-backed flags the operator ACTUALLY passed.

    argparse fills a default for every flag, so ``args.port`` alone cannot tell
    "the user chose 8765" from "the user chose nothing and it defaulted". A shadow
    parser with ``SUPPRESS`` defaults leaves absent flags off the namespace
    entirely — so its ``vars()`` is exactly the set that was passed, correctly
    handling ``--port 9010``, ``--port=9010`` and argparse abbreviations alike.
    """
    shadow = argparse.ArgumentParser(add_help=False, argument_default=argparse.SUPPRESS)
    shadow.add_argument("--host")
    shadow.add_argument("--port", type=int)
    shadow.add_argument("--console-host")
    shadow.add_argument("--console-port", type=int)
    shadow.add_argument("--receive-port", type=int)
    namespace, _ = shadow.parse_known_args(argv if argv is not None else sys.argv[1:])
    return vars(namespace)


def apply_effective_settings(
    args: argparse.Namespace,
    argv: list[str] | None,
    *,
    user_path: object | None = None,
) -> None:
    """Fill the five host/port args from persisted settings, in place.

    Precedence (``resolve_effective_settings`` — the M1 seam the settings + the
    provision APIs also read, so the runtime bind and the reported value AGREE BY
    CONSTRUCTION): argparse/shipped defaults < user settings file < an EXPLICITLY
    passed CLI flag. An unpassed flag falls through to the user file; a passed one
    still wins (REQ-DEPLOY-026 operator port force).

    Called only on the real-serve entry (the packaged shell path). Test callers
    that build ``args`` directly are unaffected — this never runs for them, so
    their explicit ports stay byte-identical.
    """
    passed = _explicitly_passed(argv)
    overrides = {
        settings_key: passed[arg_name]
        for arg_name, settings_key in _SETTINGS_BACKED_FLAGS
        if arg_name in passed
    }
    resolved = resolve_effective_settings(
        seed_path=args.config,
        user_path=user_path,
        overrides=overrides,
    )
    args.host = resolved.web_host
    args.port = resolved.web_port
    args.console_host = resolved.console_host
    args.console_port = resolved.console_port
    args.receive_port = resolved.receive_port


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


def browser_open_enabled(
    args: argparse.Namespace,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> bool:
    """Whether the launcher should open the served URL in the default browser.

    Two independent suppressors, either of which disables the open:

    * ``--no-browser`` — the explicit operator/test opt-out (unchanged).
    * a spawning **host declaration** — a Stage-2 sidecar's window is provided
      by the Tauri shell, so opening the default browser too would put a SECOND,
      fully-functional live-console UI outside the shell (the M7.4a residual: a
      ``GET /`` ×2 with a stray Chrome ``/ws`` session the shell never closes and
      no tray badge covers). The sidecar cannot be told ``--no-browser`` — the
      capability scopes the spawn with ``"args": false`` — so the suppression is
      inferred from the same declaration that arms the watchdog (:func:
      `launcher.host_declared`), keeping the three host-spawn behaviours in lock
      step.
    """
    if getattr(args, "no_browser", False):
        return False
    return not host_declared(environ=environ)


def _announce_when_serving(url: str, host: str, port: int) -> None:  # pragma: no cover
    """Emit the host ready line once uvicorn is actually accepting on ``port``.

    A timeout still announces: a slow bind is better answered with a window that
    retries by reload than with an app that never opens one. ``--port 0`` is the
    exception — the announced URL would be unreachable by construction.
    """
    if not wait_until_serving(host, port) and port == 0:
        return
    emit_ready(url)


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
        # The SAME endpoint the gate sends OSC to (``console_host``/
        # ``console_port``) is the console's OSC INPUT port — so binding it is
        # what tells a console_offline state apart from a stopped responder.
        # Built from the resolved args, so an operator's saved console port is
        # the one probed (the M7.3 settings-fallthrough discipline).
        console_input_probe=make_console_input_probe(args.console_host, args.console_port),
        # SPEC-COPILOT-PRESHOW-001 T-G2: stack.receive_port is the port the
        # bridge ACTUALLY bound (bridge.receive_port), not the requested
        # args.receive_port value — the two can differ for an ephemeral
        # request (port 0), so the real bound value is what ChatSession
        # needs to wire the pre-show OSC checks correctly.
        preshow_receive_port=stack.receive_port,
    )
    # REQ-DEPLOY-018/026 follow-up: a grandMA3 OSC entry has ONE port for BOTH
    # directions, so the port the console replies THROUGH and the port the app
    # listens ON are two hand-synchronised numbers with no feedback when they
    # drift. This finds where a reply actually lands and REPORTS it — the ping is
    # the gate's own heartbeat (no new send surface) and nothing is ever adopted
    # automatically (REQ-DEPLOY-026: the app must not change its effective port
    # behind the operator's back).
    reply_diagnostic = make_reply_port_diagnostic(
        send_ping=stack.gate.heartbeat,
        receive_host="127.0.0.1",  # the address the receiver itself binds
        receive_port=args.receive_port,
        console_port=args.console_port,
    )
    deps.reply_port_probe = reply_diagnostic.verdict
    app = create_app(deps)
    # A finished discovery changes no health state, and the heartbeat loop only
    # pushes status on a CHANGE — without this fan-out the verdict would be
    # computed correctly and never reach the operator.
    reply_diagnostic.set_on_complete(
        lambda: [notify() for notify in tuple(deps.status_listeners)]
    )
    # M7.4a (AC-DEPLOY-024 ③): mirror every gate-truth health change onto the
    # sidecar's stdout so the Stage-2 tray badge shows the SAME state the web UI
    # does. stdout is the shell's only inbound channel — it owns no socket
    # (AC-DEPLOY-027 Layer ①). A no-op wherever nothing reads the stream.
    deps.status_listeners.add(make_status_emitter(lambda: stack.gate.status["health"]))
    app.state.deps = deps  # composition introspection seam (tests/diagnostics)
    return app, stack


# @MX:NOTE: [AUTO] the protocol is declared PER ROW — the web UI is TCP, the OSC
#   feedback listener is UDP. They are separate port spaces, so an unqualified
#   (TCP) probe of the receive port reports it free no matter which process holds
#   it: the preflight would pass and the real bind would then fail. Extracted from
#   main() because the real-serve path is untestable in-process.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-026
def startup_port_specs(args: argparse.Namespace) -> list[tuple[str, int, str, int]]:
    """The fixed ports the real-serve path pre-checks, each with its protocol."""
    return [
        (args.host, args.port, "web UI", socket.SOCK_STREAM),
        ("127.0.0.1", args.receive_port, "OSC feedback listen", socket.SOCK_DGRAM),
    ]


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
        # M7.4b: resolve the host/port bind through the SAME settings seam the
        # settings + provision APIs read, so a user's saved receive_port /
        # console_port / web_host / web_port actually takes effect at the bind
        # (the packaged shell passes no CLI args). Before this the bind used the
        # argparse literal defaults while the API reported the file value — a
        # UI-vs-runtime divergence that silently sent console feedback to a port
        # nothing bound. An explicitly passed flag still wins.
        apply_effective_settings(args, argv)
        # M7.4a (AC-DEPLOY-026 ①②): when a Stage-2 host spawned us, lead our own
        # session so a single killpg reaps this process AND every descendant —
        # Tauri's shell plugin cannot make us a group leader from its side, and
        # CommandChild::kill() would otherwise leave grandchildren on the ports.
        # A no-op for a Stage-1 launch, which must keep its controlling terminal.
        become_session_leader()
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
            require_ports_available(startup_port_specs(args))
        except PortInUseError as error:  # pragma: no cover — needs an occupied port
            print(error.guidance, file=sys.stderr)
            # stdout is the shell's ONLY inbound channel: without this line it
            # sees a sidecar that died before reporting ready and falls back to
            # its hardcoded "runtime files are missing" guess.
            emit_startup_error(error.guidance)
            return 2

    # The preflight above is a pre-check, not a guarantee: it cannot cover a
    # --port 0 row, an injected-``run`` test path, or a port taken in the window
    # between the probe and the real bind. build_console_stack() performs the
    # ACTUAL receive-port bind (with its own same-port rebind retries), so this
    # is the last place a port failure can still be turned into operator words
    # instead of a traceback the Tauri shell then misdiagnoses.
    try:
        app, stack = build_runtime(args)
    except PortInUseError as error:
        print(error.guidance, file=sys.stderr)
        emit_startup_error(error.guidance)
        return 2
    url = serve_local_url(args.host, args.port)
    try:
        if real_serve:  # pragma: no cover — exercised by real serving only
            import uvicorn

            # M7.4a (AC-DEPLOY-024 ②): hand the spawning Tauri host the served
            # URL — the shell may not hold it as a Rust literal (the deny-all
            # scan forbids loopback/port literals), so this line IS how the
            # native window learns where to go. Announced only once the port is
            # really bound: the shell has no socket to retry with, so a window
            # opened one moment early shows connection-refused forever.
            threading.Thread(
                target=_announce_when_serving,
                args=(url, args.host, args.port),
                name="host-ready-announcer",
                daemon=True,
            ).start()
            install_signal_handlers(make_shutdown_handler(stack))
            # M7.2 (REQ-DEPLOY-025): when a Stage-2 host spawned us, self-reap
            # this process group if that host dies — a Unix force-quit never
            # fires Tauri's RunEvent::Exit. A no-op for a Stage-1 standalone
            # launch, which declares no host.
            install_parent_watchdog()
            # M7.4b: a host-spawned sidecar opens NO browser — the shell already
            # provides the window. Suppressing it here closes the M7.4a residual
            # (a second live-console UI in the default browser).
            threading.Timer(
                1.0,
                open_app_browser,
                kwargs={"url": url, "enabled": browser_open_enabled(args)},
            ).start()
            uvicorn.run(app, host=args.host, port=args.port)
        else:
            emit_ready(url)
            run(app, host=args.host, port=args.port)
    finally:
        stack.stop()
    return 0
