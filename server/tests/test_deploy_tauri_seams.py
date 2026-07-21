"""M7.4b — the Stage-2 cross-language seams (AC-DEPLOY-025 Stage-2, AC-DEPLOY-026 ①②).

M7.4a proved the shell can spawn the backend and show its page. Three seams were
left open, and each one is a place where two LANGUAGES have to agree about
something neither compiler checks:

1. **The authoritative group kill (AC-DEPLOY-026 ①②).** The backend's own
   parent-liveness watchdog (M7.2) is the *fallback* — it reacts, up to one
   bounded poll late, to a parent that already died. The *authoritative* teardown
   is the host's: on ``RunEvent::Exit`` the shell signals the backend's process
   GROUP. ``CommandChild::kill()`` reaps only the pid the plugin holds, so a
   backend that ever forks (PyInstaller extraction, a helper subprocess) would
   leave the grandchild squatting the web + OSC ports. The self-kill guard is
   part of the contract: between spawn and the sidecar's own ``setsid`` the child
   is still in the HOST's group, and a group kill in that window would kill the
   app — and, in a terminal launch, the terminal.

2. **The Stage-2 token delivery (AC-DEPLOY-025).** ``handshake.py`` has required
   a token on the Tauri origin since M7.1, but nothing ever delivered one — the
   Stage-2 branch was unreachable code. The host mints the token, hands it to the
   sidecar in its environment, and injects it into the webview through an
   initialization script. Disk plaintext stays 0 and stdout stays secret-free
   (AC-DEPLOY-029): the token crosses only in-process channels.

3. **The second control surface (M7.4a residual).** The M7.4a packaged run served
   ``GET /`` twice and accepted two ``/ws`` sessions. See
   :class:`TestOnlyTheHostWindowIsOpened` — the cause is mechanical, and it left
   a fully-functional live-console UI open in the operator's default browser.
"""

from __future__ import annotations

import argparse
import re

import pytest
from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web import handshake, host_channel, launcher, serve
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.handshake import BASE_SUBPROTOCOL, TOKEN_SUBPROTOCOL_PREFIX, HandshakePolicy

from .test_deploy_tauri_shell import RUST_SRC, function_body, rust_string_consts
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

TOKEN = "seam-test-token-0123456789abcdef"
EVIL_ORIGIN = "https://evil.example"


def _sidecar_source() -> str:
    return (RUST_SRC / "sidecar.rs").read_text(encoding="utf-8")


def _main_source() -> str:
    return (RUST_SRC / "main.rs").read_text(encoding="utf-8")


def _rust_sources() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(RUST_SRC.rglob("*.rs")))


# ------------------------------------------------ AC-DEPLOY-026 ①② group teardown


class TestAuthoritativeGroupKill:
    """🔴 The host's teardown must signal a process GROUP, and never its own."""

    def test_the_run_loop_reaps_on_exit(self):
        source = _main_source()
        assert "RunEvent::Exit" in source, (
            "main.rs handles no RunEvent::Exit — nothing authoritative tears the "
            "backend down on a normal quit (AC-DEPLOY-026 ①)"
        )
        assert "reap_backend_group" in source

    def test_the_reaper_signals_a_group_not_a_single_pid(self):
        body = function_body(_sidecar_source(), "fn signal_group")
        assert body is not None, "no `fn signal_group` — there is no group teardown"
        assert "killpg" in body, (
            "the teardown does not call killpg: CommandChild::kill() reaps only "
            "the bootloader pid and leaves grandchildren holding the ports"
        )

    def test_the_reaper_escalates_from_sigterm_to_sigkill(self):
        body = function_body(_sidecar_source(), "fn signal_group")
        assert "SIGTERM" in body, "a group kill that skips SIGTERM denies a graceful stop"
        assert "SIGKILL" in body, "a wedged group must not get to squat the ports forever"
        assert body.index("SIGTERM") < body.index("SIGKILL"), body[:400]

    def test_the_target_decision_refuses_the_hosts_own_group(self):
        # The window between spawn and the sidecar's own setsid: the child is
        # still in the HOST's process group, and signalling it there kills the
        # app itself (and a terminal launch's terminal).
        body = function_body(_sidecar_source(), "fn group_kill_target")
        assert body is not None, "no `fn group_kill_target` — target chosen inline, untestable"
        assert "own_pgid" in body, body[:400]

    def test_a_terminated_sidecar_is_also_reaped(self):
        # AC-DEPLOY-026 ②: a CRASHED backend leaves no one to reap whatever it
        # forked; the host observes Terminated and finishes the job.
        source = _sidecar_source()
        body = function_body(source, "fn spawn_backend")
        assert "Terminated" in source
        terminated = source[source.index("CommandEvent::Terminated") :]
        assert "reap_backend_group" in terminated[:1200], (
            "the Terminated branch does not reap the group — a crashed backend's "
            "children would survive (AC-DEPLOY-026 ②)"
        )
        assert body is not None

    def test_the_group_is_remembered_from_the_live_child(self):
        # Reading getpgid() only at teardown is a use-after-free of a pid: the
        # leader may already be gone. The group is observed while the child is
        # demonstrably alive (it is talking on stdout) and remembered.
        source = _sidecar_source()
        assert "remember_backend_group" in source, (
            "nothing records the backend's process group while it is alive"
        )


class TestWindowsJobObjectIsDeferredNotFaked:
    """The Windows path is declared N/A, not silently claimed."""

    def test_the_windows_deferral_is_greppable(self):
        source = _sidecar_source()
        assert "PENDING-WINDOWS" in source, (
            "the Windows Job Object teardown is unimplemented and unverifiable "
            "on this host; the deferral must carry the same greppable marker as "
            "the handshake's deferred Windows origin"
        )


# -------------------------------------------- AC-DEPLOY-025 Stage-2 token delivery


class TestStage2TokenDelivery:
    """🔴 The host mints the token, the backend reads it, the webview receives it."""

    def test_the_host_declares_the_same_token_env_the_backend_reads(self):
        consts = rust_string_consts(_sidecar_source())
        assert launcher.LAUNCH_TOKEN_ENV in set(consts.values()), (
            f"no Rust const declares {launcher.LAUNCH_TOKEN_ENV!r} — the backend "
            "would mint its own token and the webview's would never match"
        )

    def test_the_spawn_passes_the_token_in_the_sidecar_environment(self):
        source = _sidecar_source()
        consts = rust_string_consts(source)
        name = next(n for n, v in consts.items() if v == launcher.LAUNCH_TOKEN_ENV)
        body = function_body(source, "fn spawn_backend")
        assert name in body, (
            "the spawn body never references the launch-token env const — the "
            "token would not cross into the backend process"
        )

    def test_the_token_is_minted_by_the_host_not_taken_from_stdout(self):
        # AC-DEPLOY-029: stdout is inherited by the host and lands in crash
        # dumps, so the secret must never ride the ready/status protocol.
        assert "token" not in host_channel.READY_PREFIX.lower()
        assert "token" not in host_channel.STATUS_PREFIX.lower()
        source = _sidecar_source()
        assert "mint_launch_token" in source, "the host does not mint a token"
        consumer = function_body(source, "fn consume_host_lines")
        assert consumer is not None
        assert "token" not in consumer.lower(), (
            "the stdout line parser mentions the token — the secret must not "
            "cross the stdout channel (AC-DEPLOY-029)"
        )

    def test_the_window_receives_the_token_through_an_initialization_script(self):
        source = _sidecar_source()
        assert "initialization_script" in source, (
            "the token reaches the webview by no in-process channel; a disk file "
            "or an unauthenticated loopback endpoint is explicitly rejected by "
            "plan §M7.1"
        )

    def test_the_injected_global_matches_the_name_the_ui_reads(self):
        # Linkage, not duplication: rename either side and this fails loudly
        # instead of leaving the window unable to authenticate. The UI seam that
        # reads the global already exists (M7.1 useCopilotSocket.ts); the shell
        # must inject the SAME name.
        ui_src = RUST_SRC.parents[1] / "ui" / "src"
        consumed: set[str] = set()
        for path in ui_src.rglob("*.ts"):
            consumed |= set(re.findall(r"__COPILOT_[A-Z_]+__", path.read_text(encoding="utf-8")))
        injected = set(re.findall(r"__COPILOT_[A-Z_]+__", _rust_sources()))
        assert injected, "the shell injects no launch-context global at all"
        assert injected <= consumed, f"injected but never read by the UI: {injected - consumed}"

    def test_the_window_loads_the_bundled_app_so_its_origin_is_stage2(self):
        # Loading the backend's URL directly would give the window a Stage-1
        # loopback Origin, where the token is only defence-in-depth — the
        # token-REQUIRED branch would stay unreachable in the real product.
        source = _sidecar_source()
        assert "WebviewUrl::App" in source, (
            "the window is not built on the bundled app protocol, so its Origin "
            "is not the Stage-2 origin and AC-DEPLOY-025's token-required branch "
            "is never exercised"
        )

    def test_the_backend_url_is_still_learned_at_runtime(self):
        # The window no longer NAVIGATES to the backend, but the UI still has to
        # reach it — so the runtime-learned URL must be injected, not dropped.
        consts = rust_string_consts(_sidecar_source())
        assert host_channel.READY_PREFIX in set(consts.values())


class TestTheShellReportsTheReportedCause:
    """A start-up that never served must be explained by the BACKEND, not guessed.

    The Terminated branch hardcoded "Its runtime files are most likely missing
    or incomplete" — flatly wrong for the commonest real cause, a receive port
    still held by an abnormally-exited prior instance. The shell had no error
    channel at all, so it could only guess, and it guessed the same thing every
    time.
    """

    def test_the_shell_declares_the_same_error_prefix_the_backend_emits(self):
        # Neither compiler checks this agreement; the guard test does.
        consts = rust_string_consts(_sidecar_source())
        assert host_channel.ERROR_PREFIX in set(consts.values()), (
            "sidecar.rs declares no constant equal to host_channel.ERROR_PREFIX "
            f"({host_channel.ERROR_PREFIX!r}) — the shell cannot recognise a "
            "reported start-up cause"
        )

    def test_the_line_parser_consumes_the_error_prefix(self):
        body = function_body(_sidecar_source(), "fn consume_host_lines")
        assert body is not None, "no `fn consume_host_lines` — nothing parses stdout"
        assert "ERROR_PREFIX" in body, (
            "consume_host_lines parses only ready/status lines, so a reported "
            "cause is swallowed as ordinary log output"
        )

    def test_the_reported_cause_is_latched_for_the_terminated_branch(self):
        # The cause arrives on stdout BEFORE the process dies; the Terminated
        # event carries only an exit payload. Without a latch the cause is gone
        # by the time the dialog is raised.
        source = _sidecar_source()
        assert "remember_startup_error" in source or "StartupErrorCause" in source, (
            "nothing retains the reported cause between the stdout line and the "
            "Terminated event that renders it"
        )

    def test_the_terminated_branch_prefers_the_reported_cause(self):
        # Bounded by the brace-matched function, NOT an arbitrary character
        # window: a window drifts out of range the moment a comment is added
        # above the code it was measured against.
        body = function_body(_sidecar_source(), "fn spawn_backend")
        assert body is not None, "no `fn spawn_backend`"
        window = body[body.index("CommandEvent::Terminated") :]
        assert "reported_startup_error" in window, (
            "the Terminated branch still reports a hardcoded cause — a port "
            "conflict is still misdiagnosed as missing runtime files"
        )
        # Ordering IS the contract: the reported cause is consulted FIRST and the
        # hardcoded sentence is only what is reached when nothing was reported.
        assert "missing or incomplete" in window
        assert window.index("reported_startup_error") < window.index("missing or incomplete"), (
            "the hardcoded sentence is chosen before the reported cause is "
            "consulted — the backend's own explanation would be discarded"
        )

    def test_the_hardcoded_text_survives_only_as_a_fallback(self):
        # Not deleted: when the backend died before it could say anything, an
        # incomplete payload really is the likeliest cause.
        source = _sidecar_source()
        assert "missing or incomplete" in source, (
            "the no-cause fallback text was deleted, leaving a silent dialog for "
            "the genuinely-incomplete-payload case"
        )


class TestStage2OriginIsTrustedByDefault:
    def test_a_default_launch_trusts_the_stage2_origin(self, tmp_path):
        args = argparse.Namespace(host="127.0.0.1", port=8765)
        policy = serve.build_handshake_policy(args)
        assert handshake.TAURI_ORIGINS[0] in policy.trusted_origins
        assert policy.token

    def test_the_windows_origin_is_still_deferred(self):
        # Constraint: M7.4b must not widen the allowlist to a platform it cannot
        # run (an unverifiable allowlist entry is how a security allowlist rots).
        assert handshake.TAURI_ORIGINS == ("tauri://localhost",)
        assert "PENDING-WINDOWS" in (handshake.__doc__ or "") or "PENDING-WINDOWS" in (
            (RUST_SRC.parents[1] / "server" / "web" / "handshake.py").read_text(encoding="utf-8")
        )


# ------------------------------------------- the Stage-2 window's HTTP reachability


def _app(tmp_path, *, handshake_policy):
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)
    deps = WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        handshake=handshake_policy,
    )
    return create_app(deps)


def _policy() -> HandshakePolicy:
    return HandshakePolicy(
        token=TOKEN,
        trusted_origins=handshake.TAURI_ORIGINS,
        browser_origins=("http://127.0.0.1:8765",),
    )


class TestStage2WindowCanReachTheApi:
    """🔴 A window on the Stage-2 origin is CROSS-origin to the backend.

    Every ``/api/*`` call the M4/M5 settings + provisioning UI makes is a
    cross-origin request once the window stops being served BY the backend. With
    no CORS response the webview blocks the read and the settings panel breaks —
    silently, because the fetch rejects rather than erroring visibly.

    The allowlist is exactly the handshake's Stage-2 origins: no new literal, no
    wildcard, and no widening beyond the origins the ``/ws`` gate already trusts.
    """

    def test_the_stage2_origin_may_read_the_api(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake_policy=_policy()))
        response = client.get("/healthz", headers={"Origin": handshake.TAURI_ORIGINS[0]})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == handshake.TAURI_ORIGINS[0]

    def test_a_preflighted_write_from_the_stage2_origin_is_allowed(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake_policy=_policy()))
        response = client.options(
            "/api/settings",
            headers={
                "Origin": handshake.TAURI_ORIGINS[0],
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code in (200, 204), response.text
        assert response.headers.get("access-control-allow-origin") == handshake.TAURI_ORIGINS[0]

    def test_an_arbitrary_origin_is_not_granted_cors(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake_policy=_policy()))
        response = client.get("/healthz", headers={"Origin": EVIL_ORIGIN})
        assert response.headers.get("access-control-allow-origin") is None

    def test_no_credentials_are_granted(self, tmp_path):
        # Nothing authenticates with cookies; allow-credentials would only widen
        # what a mistaken origin entry could reach.
        client = TestClient(_app(tmp_path, handshake_policy=_policy()))
        response = client.get("/healthz", headers={"Origin": handshake.TAURI_ORIGINS[0]})
        assert response.headers.get("access-control-allow-credentials") is None

    def test_an_ungated_launch_grants_no_cors_at_all(self, tmp_path):
        client = TestClient(_app(tmp_path, handshake_policy=None))
        response = client.get("/healthz", headers={"Origin": handshake.TAURI_ORIGINS[0]})
        assert response.headers.get("access-control-allow-origin") is None

    def test_the_stage2_window_still_needs_the_token_for_ws(self, tmp_path):
        # CORS must not have become a second, weaker door: the /ws gate is
        # unchanged and still rejects the Stage-2 origin without the token.
        from starlette.websockets import WebSocketDisconnect

        client = TestClient(_app(tmp_path, handshake_policy=_policy()))
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect("/ws", headers={"Origin": handshake.TAURI_ORIGINS[0]}),
        ):
            pass  # pragma: no cover
        with client.websocket_connect(
            "/ws",
            headers={"Origin": handshake.TAURI_ORIGINS[0]},
            subprotocols=[BASE_SUBPROTOCOL, f"{TOKEN_SUBPROTOCOL_PREFIX}{TOKEN}"],
        ) as socket:
            assert socket.receive_json()["type"]


# --------------------------------------- the second control surface (M7.4a residual)


class TestOnlyTheHostWindowIsOpened:
    """🔴 The M7.4a double load, diagnosed.

    Observed on the packaged ``.app``: ``GET /`` twice, two ``/ws`` sessions
    accepted. ``lsof`` named the second client — Google Chrome. The launcher
    schedules ``open_app_browser`` on a 1 s timer for every real serve, and the
    sidecar cannot be told otherwise: the capability scopes the spawn with
    ``"args": false``, so the host cannot pass ``--no-browser``.

    It is not cosmetic. The operator gets a second, fully-functional live-console
    UI outside the shell — one the shell never closes, one no tray badge covers,
    and one that keeps a WebSocket open to the gate after the window is gone.

    The signal that a host will provide the window is the one already used to arm
    the watchdog and to detach into an own session: the host declaration.
    """

    def test_a_standalone_launch_still_opens_the_browser(self):
        args = argparse.Namespace(no_browser=False)
        assert serve.browser_open_enabled(args, environ={}) is True

    def test_an_explicit_no_browser_still_wins(self):
        args = argparse.Namespace(no_browser=True)
        assert serve.browser_open_enabled(args, environ={}) is False

    def test_a_host_spawned_sidecar_opens_no_browser(self):
        args = argparse.Namespace(no_browser=False)
        for declaration in (
            {launcher.PARENT_PIPE_FD_ENV: "0"},
            {launcher.PARENT_PID_ENV: "4242"},
            {launcher.PARENT_PIPE_FD_ENV: "0", launcher.PARENT_PID_ENV: "4242"},
        ):
            assert serve.browser_open_enabled(args, environ=declaration) is False, declaration

    def test_the_serve_path_uses_the_decision(self):
        source = (RUST_SRC.parents[1] / "server" / "web" / "serve.py").read_text(encoding="utf-8")
        assert "browser_open_enabled(" in source, (
            "serve.py never consults browser_open_enabled — the real-serve path "
            "still schedules the browser open unconditionally"
        )
        assert 'enabled=not args.no_browser' not in source, (
            "the real-serve path still passes enabled=not args.no_browser, "
            "ignoring the host declaration"
        )

    def test_the_declaration_predicate_is_shared_with_the_watchdog(self):
        # One predicate, three consumers (watchdog arming, session detach,
        # browser suppression) — so a host that declares itself cannot be
        # Stage-2 for one of them and Stage-1 for another.
        assert launcher.host_declared(environ={}) is False
        assert launcher.host_declared(environ={launcher.PARENT_PID_ENV: "1"}) is True
        assert launcher.host_declared(environ={launcher.PARENT_PIPE_FD_ENV: "0"}) is True


# ----------------------------- persisted settings vs the actual bind (live fix)


def _write_user_settings(path, **fields) -> None:
    lines = ["[settings]"]
    for key, value in fields.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestPersistedSettingsDriveTheBoundPorts:
    """🔴 The packaged app must BIND the ports the user saved — not the defaults.

    The live defect: the shell spawns the sidecar with NO CLI args, and
    ``serve.py`` built the console stack from the argparse literal defaults, so a
    user's ``receive_port = 9005`` in the settings file was ignored at the bind
    while ``GET /api/settings`` still reported 9005 (the API reads the file). The
    console's feedback then went to a port nothing bound — a permanent
    responder_degraded, masked only by M18's same-port rebind recovery.

    The fix routes the bind through the SAME ``resolve_effective_settings`` seam
    the settings/provision APIs read, so the reported value and the bound port
    agree by construction. These tests assert the ACTUAL bound port
    (``ConsoleStack.receive_port`` = ``getsockname()``), not just the resolver.
    """

    def _boot(self, args, audit_dir):
        # Boot only the console stack — the exact composition build_runtime uses
        # for the bind — driven by the resolved args. No provider/keyring weight.
        from server.safety.bootstrap import build_console_stack
        from server.web.approval_bridge import ApprovalChannel

        return build_console_stack(
            send_host=args.console_host,
            send_port=args.console_port,
            receive_port=args.receive_port,
            approval_port=ApprovalChannel(timeout_seconds=1.0),
            attempt_session_backup=False,
            audit_dir=audit_dir,
        )

    def test_an_unpassed_port_falls_through_to_the_user_file(self, tmp_path):
        user_file = tmp_path / "settings.toml"
        _write_user_settings(user_file, receive_port=29005, console_port=28001)
        args = serve.parse_args([])  # NO flags — exactly the packaged-shell case
        serve.apply_effective_settings(args, [], user_path=user_file)

        assert args.receive_port == 29005, "the saved receive_port was ignored"
        assert args.console_port == 28001, "the saved console_port was ignored"

        stack = self._boot(args, tmp_path / "audit")
        try:
            assert stack.receive_port == 29005, (
                f"the stack BOUND {stack.receive_port}, not the saved 29005 — "
                "the UI-vs-runtime divergence is back"
            )
        finally:
            stack.stop()

    def test_the_api_seam_reports_the_same_value_the_bind_uses(self, tmp_path):
        # Agree-by-construction: the settings API reads resolve_effective_settings;
        # the bind now reads it too, so the two can never diverge again.
        from server.deploy.settings import resolve_effective_settings

        user_file = tmp_path / "settings.toml"
        _write_user_settings(user_file, receive_port=29006)
        args = serve.parse_args([])
        serve.apply_effective_settings(args, [], user_path=user_file)
        reported = resolve_effective_settings(user_path=user_file).receive_port
        assert reported == args.receive_port == 29006

    def test_an_explicit_flag_still_overrides_the_user_file(self, tmp_path):
        # REQ-DEPLOY-026 operator force: a passed flag beats the saved file.
        user_file = tmp_path / "settings.toml"
        _write_user_settings(user_file, receive_port=29005)
        argv = ["--receive-port", "29010"]
        args = serve.parse_args(argv)
        serve.apply_effective_settings(args, argv, user_path=user_file)
        assert args.receive_port == 29010

    def test_no_user_file_keeps_the_shipped_defaults(self, tmp_path):
        from server.deploy.settings import DEFAULT_RECEIVE_PORT

        missing = tmp_path / "absent.toml"
        args = serve.parse_args([])
        serve.apply_effective_settings(args, [], user_path=missing)
        assert args.receive_port == DEFAULT_RECEIVE_PORT

    def test_web_host_and_port_also_resolve_from_the_file(self, tmp_path):
        user_file = tmp_path / "settings.toml"
        _write_user_settings(user_file, web_port=28770, console_host="127.0.0.1")
        args = serve.parse_args([])
        serve.apply_effective_settings(args, [], user_path=user_file)
        assert args.port == 28770
        assert args.console_host == "127.0.0.1"
