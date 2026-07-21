//! Backend sidecar lifecycle (M7.4a — REQ-DEPLOY-001/002/025, AC-DEPLOY-024).
//!
//! The PyInstaller onedir backend is bundled as a Tauri sidecar and spawned
//! here. Two properties of that spawn are load-bearing and easy to get silently
//! wrong, so both are pinned by a guard test
//! (`server/tests/test_deploy_tauri_shell.py`):
//!
//! 1. **The parent declaration.** See `spawn_backend` — without it the backend's
//!    self-reap watchdog never arms, with no error anywhere.
//! 2. **No compile-time backend address.** The deny-all scan
//!    (`packaging/rust_scan.py`) forbids this crate any loopback or console-port
//!    literal, and a literal would desync from a reconfigured port anyway. The
//!    backend therefore PRINTS its served URL on stdout and the window is built
//!    from what it printed. This module holds no address of any kind.

use std::collections::HashMap;
use std::sync::Mutex;

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// The sidecar program name as the RUST side resolves it.
///
/// Deliberately the bare file name, not the `externalBin` path: the plugin's
/// `relative_command_path` joins whatever it is given onto the executable's own
/// directory (`tauri-plugin-shell` `process/mod.rs`), and Cargo copies the
/// external binary flat into that directory. Passing the configured
/// `binaries/...` path here resolves to a `binaries/` subdirectory that does not
/// exist and the spawn fails with ENOENT. The capability file keeps the
/// configured path because the JS-side scope is matched against the CONFIG
/// value; `SIDECAR_SCOPE_NAME` records that asymmetry so the two cannot drift
/// unnoticed (guarded in server/tests/test_deploy_tauri_shell.py).
pub const SIDECAR_NAME: &str = "copilot-backend";

/// The same sidecar as spelled in `tauri.conf.json` `bundle.externalBin` and in
/// the `shell:allow-execute` capability scope.
pub const SIDECAR_SCOPE_NAME: &str = "binaries/copilot-backend";

/// Env var names read by `server/web/launcher.py::install_parent_watchdog`.
/// Renaming either side without the other is caught by the guard test, which
/// imports these expected values from the Python module rather than repeating
/// them.
pub const PARENT_PIPE_FD_ENV: &str = "COPILOT_PARENT_PIPE_FD";
pub const PARENT_PID_ENV: &str = "COPILOT_PARENT_PID";

/// The env var the per-launch handshake token crosses into the backend on. Read
/// by `server/web/serve.py::build_handshake_policy` — the host mints the token,
/// passes it here, and the backend adopts it INSTEAD of minting its own, so the
/// value the webview is injected with is the value the `/ws` gate checks.
pub const LAUNCH_TOKEN_ENV: &str = "COPILOT_LAUNCH_TOKEN";

/// The webview global the injected launch token lands in — read by the M7.1 UI
/// seam (`ui/src/useCopilotSocket.ts::launchToken`).
pub const TOKEN_GLOBAL: &str = "__COPILOT_LAUNCH_TOKEN__";

/// The webview global the runtime-learned backend base URL lands in — read by
/// `ui/src/launchContext.ts`. The Stage-2 window is served from the bundled app
/// (a `tauri://` app-scheme origin), so it can no longer reach the backend with
/// a same-origin relative path; it needs the absolute base the backend printed.
pub const BACKEND_URL_GLOBAL: &str = "__COPILOT_BACKEND_URL__";

/// fd 0 — the sidecar's own stdin. `tauri-plugin-shell` pipes it and this
/// process holds the write end for its entire lifetime, so ANY death of this
/// process (normal exit, crash, force-quit) closes the last write end and the
/// backend sees EOF immediately. That immediacy is why the pipe is the PRIMARY
/// trigger and the pid poll is only the fallback (plan section C, M7.2).
pub const PARENT_PIPE_FD_VALUE: &str = "0";

/// Line prefixes of the sidecar stdout protocol (`server/web/host_channel.py`).
pub const READY_PREFIX: &str = "@copilot:ready ";
pub const STATUS_PREFIX: &str = "@copilot:status ";
/// The backend's own explanation for a start-up that will never report ready.
/// Without it this shell can only GUESS why the sidecar died, and a guess is a
/// constant — see [`consume_host_lines`] and the `Terminated` branch.
pub const ERROR_PREFIX: &str = "@copilot:error ";

/// The window label the capability file scopes permissions to.
pub const MAIN_WINDOW_LABEL: &str = "main";

const WINDOW_TITLE: &str = "GrandMA3 Copilot";

/// The spawned backend, kept alive for the app's lifetime.
///
/// M7.4b turns this handle into the authoritative process-GROUP kill on
/// `RunEvent::Exit` (see [`reap_backend_group`]) — `CommandChild::kill()` alone
/// reaps only the sidecar pid and leaves any grandchild squatting the ports
/// (AC-DEPLOY-026 ①②).
pub struct BackendProcess(pub Mutex<Option<CommandChild>>);

/// The backend's remembered process GROUP id, captured while the child is
/// demonstrably alive (it is talking on stdout, so it has already `setsid`'d
/// into its own session — `server/web/launcher.py::become_session_leader`).
///
/// Remembering it — rather than reading `getpgid()` at teardown — is what makes
/// the crash path (AC-DEPLOY-026 ②) work: by the time the host observes the
/// sidecar `Terminated`, the leader pid may already be gone, but a grandchild it
/// forked still carries the group, and the remembered gid still reaps it.
pub struct BackendGroup(pub Mutex<Option<i32>>);

/// The per-launch handshake token this host minted, injected into the webview
/// over the initialization script (never written to disk, never on stdout).
pub struct LaunchToken(pub String);

/// Latched true once the backend reports a ready URL — i.e. it started
/// successfully at least once.
///
/// This is the correct discriminator for the sidecar's `Terminated` event:
/// a termination AFTER the backend served (a normal quit, or a
/// crash-after-serving) is NOT a start-up failure and must not raise the
/// "backend did not start" dialog. The live-window check it replaces reads
/// false during a normal quit — the window is torn down before the backend's
/// termination is observed — which wrongly rendered a start-up error on every
/// clean exit (found by running the packaged app, not by reading it).
pub struct BackendReady(pub std::sync::atomic::AtomicBool);

fn mark_backend_ready(app: &AppHandle) {
    if let Some(state) = app.try_state::<BackendReady>() {
        state.0.store(true, std::sync::atomic::Ordering::SeqCst);
    }
}

fn backend_ever_ready(app: &AppHandle) -> bool {
    app.try_state::<BackendReady>()
        .map(|state| state.0.load(std::sync::atomic::Ordering::SeqCst))
        .unwrap_or(false)
}

/// The last start-up cause the backend reported on stdout, if any.
///
/// The cause arrives as a stdout line while the process is still alive; the
/// `Terminated` event that raises the dialog carries only an exit payload. The
/// two facts therefore have to be joined here, which is why the line is latched
/// rather than handled where it is parsed.
pub struct StartupErrorCause(pub Mutex<Option<String>>);

fn remember_startup_error(app: &AppHandle, cause: &str) {
    if let Some(state) = app.try_state::<StartupErrorCause>() {
        if let Ok(mut slot) = state.0.lock() {
            *slot = Some(cause.to_string());
        }
    }
}

fn reported_startup_error(app: &AppHandle) -> Option<String> {
    let state = app.try_state::<StartupErrorCause>()?;
    let slot = state.0.lock().ok()?;
    slot.clone()
}

/// The live sidecar's pid — the observable evidence that the spawn happened.
pub fn backend_pid(app: &AppHandle) -> Option<u32> {
    let state = app.try_state::<BackendProcess>()?;
    let guard = state.0.lock().ok()?;
    guard.as_ref().map(|child| child.pid())
}

// @MX:ANCHOR: [AUTO] launch-token injection boundary — the host mints the /ws
//   handshake secret and hands it to the backend (env) and the webview (init
//   script). The two MUST receive the SAME value or the Stage-2 window can never
//   authenticate.
// @MX:REASON: this is the delivery half of the credential-adjacent boundary the
//   Python handshake (server/web/handshake.py) guards. The plan (§M7.1) rejected
//   every disk / loopback-endpoint delivery because a masquerading local process
//   could read it; the ONLY leak-resistant channels are the sidecar environment
//   (in-process) and the Tauri init script (host↔own-webview IPC). Emitting the
//   token on stdout instead would leak it into the host's inherited stream and
//   any crash dump (AC-DEPLOY-029). Minting a WEAK token (a predictable value, a
//   reused constant) reopens FEAS-9 for the Stage-2 origin.
// @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-002a / AC-DEPLOY-025, 029
/// Mint a fresh unguessable per-launch token: 32 CSPRNG bytes as 64 hex chars.
///
/// Read from the OS CSPRNG (`/dev/urandom`) — no crypto crate, and hex keeps the
/// value inside the RFC 6455 subprotocol token charset it rides in
/// (`copilot-token.<token>`). Windows mints its token on its own path when that
/// platform is un-deferred (PENDING-WINDOWS).
pub fn mint_launch_token() -> String {
    #[cfg(unix)]
    {
        use std::io::Read;
        let mut buf = [0u8; 32];
        if let Ok(mut file) = std::fs::File::open("/dev/urandom") {
            if file.read_exact(&mut buf).is_ok() {
                return buf.iter().map(|byte| format!("{byte:02x}")).collect();
            }
        }
    }
    // Unreachable on a healthy Unix host; a token is still required, so fall
    // back to a per-launch-unique (if not cryptographically strong) value rather
    // than shipping an empty secret that would make the Stage-2 branch trivial.
    format!("fallback-{}", std::process::id())
}

/// Own process group id — the group the SHELL and any not-yet-detached child
/// share. The `killpg` target must never equal this (see [`group_kill_target`]).
#[cfg(unix)]
fn own_pgid() -> i32 {
    // getpgrp() takes no argument and cannot fail.
    unsafe { libc::getpgrp() }
}

/// The live process group of `child_pid`, or `None` if it is gone.
#[cfg(unix)]
fn pgid_of(child_pid: i32) -> Option<i32> {
    let gid = unsafe { libc::getpgid(child_pid) };
    if gid < 0 {
        None
    } else {
        Some(gid)
    }
}

// @MX:ANCHOR: [AUTO] group-kill target decision — refuses to signal the HOST's
//   own process group, the one lethal mistake a process-group teardown can make.
// @MX:REASON: between spawn and the sidecar's own `setsid`, the child is still in
//   the HOST's group; a `killpg` in that window would take down the app itself,
//   and in a terminal launch the terminal. The guard is that the child's group
//   must DIFFER from `own_pgid` (proof the child detached) and be a real group
//   (> 1) before it is ever signalled. Getting this backwards is not a degraded
//   teardown — it is the app killing itself.
// @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-025 / AC-DEPLOY-026 ①②
/// Decide the safe `killpg` target for a child, given the host's own group.
///
/// `Some(gid)` only when `gid` is the child's OWN detached session group — never
/// the host's group, never a nonsense group id.
#[cfg(unix)]
fn group_kill_target(child_pid: i32, own_pgid: i32) -> Option<i32> {
    let child_pgid = pgid_of(child_pid)?;
    if child_pgid == own_pgid {
        return None; // still in the host's group — signalling it kills the app
    }
    if child_pgid <= 1 {
        return None; // 0/1 are not real, killpg-able session groups
    }
    Some(child_pgid)
}

/// Record the backend's session group while it is demonstrably alive.
///
/// Called on the child's stdout (proof it is running and, since Python's
/// `become_session_leader` runs before any output, has detached). Idempotent —
/// only the first successful capture writes.
fn remember_backend_group(app: &AppHandle, child_pid: u32) {
    #[cfg(unix)]
    {
        let Some(state) = app.try_state::<BackendGroup>() else {
            return;
        };
        let Ok(mut guard) = state.0.lock() else {
            return;
        };
        if guard.is_some() {
            return;
        }
        if let Some(gid) = group_kill_target(child_pid as i32, own_pgid()) {
            *guard = Some(gid);
            println!("[shell] backend session group remembered: pgid {gid}");
        }
    }
    #[cfg(not(unix))]
    {
        let _ = (app, child_pid);
    }
}

/// SIGTERM the group, wait a bounded moment for a graceful stop, then SIGKILL
/// whatever is left. The SIGTERM reaches the backend, whose installed handler
/// stops the console stack first (`make_shutdown_handler`), so the graceful
/// ordering is preserved; the SIGKILL only ever hits a wedged straggler.
#[cfg(unix)]
fn signal_group(pgid: i32) {
    // SIGTERM first — the backend's own handler tears the console stack down.
    unsafe { libc::killpg(pgid, libc::SIGTERM) };
    // Bounded grace: the backend watchdog's own reap latency ceiling is 1s, so a
    // group that has not died within that window is wedged and gets SIGKILL.
    let deadline = std::time::Instant::now() + std::time::Duration::from_millis(1000);
    while std::time::Instant::now() < deadline {
        // killpg(pgid, 0) probes existence without signalling; ESRCH => gone.
        if unsafe { libc::killpg(pgid, 0) } != 0 {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(25));
    }
    unsafe { libc::killpg(pgid, libc::SIGKILL) };
}

/// The authoritative teardown: reap the backend's WHOLE process group.
///
/// Runs on `RunEvent::Exit` (normal quit — AC-DEPLOY-026 ①) and on the sidecar's
/// `Terminated` (backend crash — AC-DEPLOY-026 ②). Prefers the group remembered
/// while the child was alive; if none was captured (the child died before its
/// first stdout) it recomputes from the live child, and if THAT is gone too
/// there is nothing left holding the ports. Idempotent and best-effort: a double
/// call (ExitRequested then Exit, or Terminated then Exit) second-times into an
/// already-dead group, which `killpg` answers with a harmless ESRCH.
pub fn reap_backend_group(app: &AppHandle) {
    #[cfg(unix)]
    {
        let remembered = app
            .try_state::<BackendGroup>()
            .and_then(|state| state.0.lock().ok().and_then(|guard| *guard));
        let target = remembered.or_else(|| {
            backend_pid(app).and_then(|pid| group_kill_target(pid as i32, own_pgid()))
        });
        match target {
            Some(pgid) => {
                println!("[shell] reaping backend process group pgid {pgid}");
                signal_group(pgid);
            }
            None => {
                // Nothing detached to reap. The direct child, if any, is torn
                // down by the plugin; leaving the host's own group untouched is
                // the whole point of group_kill_target's refusal.
                eprintln!("[shell] no detached backend group to reap");
            }
        }
    }
    #[cfg(not(unix))]
    {
        // PENDING-WINDOWS — the authoritative teardown on Windows is a
        // KILL_ON_JOB_CLOSE Job Object the sidecar is spawned into, so the OS
        // reaps the whole tree when the host handle closes. It is NOT wired here
        // because M7 has no Windows runner to verify it against, and an
        // unverified teardown is how a lifecycle guarantee silently rots. The
        // deferral mirrors the handshake's PENDING-WINDOWS origin.
        let _ = app;
    }
}

// @MX:ANCHOR: [AUTO] sidecar parent-declaration boundary — the ONLY place the
//   spawning host tells the backend it exists, and therefore the only thing
//   that arms the backend's parent-liveness watchdog.
// @MX:REASON: the failure is SILENT. Drop the env entries below and everything
//   still builds, launches and looks healthy; nothing logs, nothing fails. The
//   damage only appears on a Unix force-quit, where `RunEvent::Exit` never
//   fires, the Rust group-kill therefore never runs, and the disarmed backend
//   survives as an orphan squatting the web and OSC ports until the next launch
//   dies on `require_ports_available`. Same defect class as the Stage-1
//   unmounted-router P0, so it is pinned by a guard test that FAILS when the
//   declaration is missing rather than by review
//   (server/tests/test_deploy_tauri_shell.py::TestSidecarParentDeclaration).
// @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-025 / AC-DEPLOY-024, 026 ③
/// Where the shell plugin will look for the sidecar, resolved the same way it
/// resolves it: `current_exe().parent().join(name)`, no target-triple suffix
/// (`tauri-plugin-shell` `process/mod.rs::relative_command_path`).
///
/// Recomputed here purely so the path is OBSERVABLE. A spawn that fails with a
/// bare "No such file or directory" is undiagnosable — the whole question is
/// WHICH file, and under a double-clicked `.app` the executable's directory is
/// not the one the filesystem inspection would suggest.
pub fn resolved_sidecar_path() -> Option<std::path::PathBuf> {
    let exe = std::env::current_exe().ok()?;
    Some(exe.parent()?.join(SIDECAR_NAME))
}

fn resolved_sidecar_report() -> String {
    match resolved_sidecar_path() {
        Some(path) => {
            let exists = path.try_exists().unwrap_or(false);
            format!("{} (exists: {exists})", path.display())
        }
        None => "<could not resolve the executable's own directory>".to_string(),
    }
}

pub fn spawn_backend(app: &AppHandle) -> Result<(), String> {
    println!("[shell] sidecar resolves to {}", resolved_sidecar_report());
    let mut environment = HashMap::new();
    environment.insert(
        PARENT_PIPE_FD_ENV.to_string(),
        PARENT_PIPE_FD_VALUE.to_string(),
    );
    // FALLBACK trigger. The backend cross-checks this against its real parent
    // and prefers the real one, so an unexpected intermediary cannot make the
    // very first poll fire.
    environment.insert(PARENT_PID_ENV.to_string(), std::process::id().to_string());

    // M7.4b: mint the per-launch handshake token HERE and hand it to the backend
    // in its environment. The backend adopts it (build_handshake_policy prefers
    // COPILOT_LAUNCH_TOKEN over minting its own), and the same value is injected
    // into the webview (open_main_window) — the two-in-process-channels delivery
    // the plan requires. Never on stdout, never on disk (AC-DEPLOY-029).
    let token = mint_launch_token();
    environment.insert(LAUNCH_TOKEN_ENV.to_string(), token.clone());
    app.manage(LaunchToken(token));
    app.manage(BackendGroup(Mutex::new(None)));
    app.manage(BackendReady(std::sync::atomic::AtomicBool::new(false)));
    app.manage(StartupErrorCause(Mutex::new(None)));

    let command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|error| {
            format!(
                "The backend program could not be found.\n\
                 Looked for: {}\n\
                 Configured as: {SIDECAR_SCOPE_NAME} (tauri.conf.json bundle.externalBin)\n\
                 Underlying error: {error}",
                resolved_sidecar_report()
            )
        })?
        .envs(environment);

    let (mut events, child) = command.spawn().map_err(|error| {
        format!(
            "The backend program was found but could not be started.\n\
             Program: {}\n\
             Underlying error: {error}",
            resolved_sidecar_report()
        )
    })?;

    app.manage(BackendProcess(Mutex::new(Some(child))));
    if let Some(pid) = backend_pid(app) {
        println!("[shell] backend sidecar spawned as pid {pid}");
    }

    let handle = app.clone();
    let child_pid = backend_pid(app);
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(chunk) => {
                    // The child is alive and (since become_session_leader runs
                    // before any Python output) has detached: capture its group
                    // now, so a later crash path can still reap its children.
                    if let Some(pid) = child_pid {
                        remember_backend_group(&handle, pid);
                    }
                    consume_host_lines(&handle, &String::from_utf8_lossy(&chunk));
                }
                CommandEvent::Stderr(chunk) => {
                    eprint!("[backend] {}", String::from_utf8_lossy(&chunk));
                }
                CommandEvent::Terminated(payload) => {
                    // AC-DEPLOY-026 ②: a CRASHED backend leaves no one to reap
                    // whatever it forked. CommandChild's own reap covered only
                    // the bootloader pid; sweep the remembered GROUP so no
                    // extracted grandchild survives to squat the ports.
                    reap_backend_group(&handle);
                    if backend_ever_ready(&handle) {
                        // It ran, served, and then stopped — a normal quit or a
                        // crash-after-serving. NOT a start-up failure: the tray
                        // badge is enough. (A live-window check here reads false
                        // during a normal quit, because the window is torn down
                        // before this event arrives — which wrongly raised the
                        // "did not start" dialog on every clean exit.)
                        eprintln!("[backend] sidecar terminated: {payload:?}");
                        crate::tray::set_health(&handle, crate::tray::HEALTH_STOPPED);
                    } else {
                        // It never got as far as reporting a URL: a startup
                        // failure the operator needs told about in words.
                        //
                        // Prefer the cause the BACKEND reported over any guess
                        // this shell could make. The guess used to be
                        // unconditional, so a receive port still held by an
                        // abnormally-exited prior instance — the commonest real
                        // cause, and a recoverable one — was reported as a broken
                        // installation, sending the operator to reinstall
                        // something that was never damaged.
                        let cause = match reported_startup_error(&handle) {
                            Some(reported) => reported,
                            // Nothing reported: the backend died before it could
                            // say anything, and then an incomplete payload really
                            // is the likeliest cause.
                            None => format!(
                                "The backend process exited during start-up before it \
                                 reported a ready address ({payload:?}). Its runtime \
                                 files are most likely missing or incomplete."
                            ),
                        };
                        crate::startup_error::report(&handle, &cause);
                    }
                }
                _ => {}
            }
        }
    });

    Ok(())
}

/// Parse one stdout chunk of the sidecar protocol. Unrecognised lines are the
/// backend's ordinary logging and are passed through untouched.
fn consume_host_lines(app: &AppHandle, chunk: &str) {
    for line in chunk.lines() {
        if let Some(url) = line.strip_prefix(READY_PREFIX) {
            // Latch "started successfully" the moment a ready URL arrives, so a
            // later Terminated (quit or crash-after-serving) is never mistaken
            // for a start-up failure.
            mark_backend_ready(app);
            open_main_window(app, url.trim());
        } else if let Some(health) = line.strip_prefix(STATUS_PREFIX) {
            crate::tray::set_health(app, health.trim());
        } else if let Some(cause) = line.strip_prefix(ERROR_PREFIX) {
            // Latched, not reported here: the backend is still exiting, and the
            // dialog belongs to the Terminated branch that decides whether this
            // was a start-up failure at all.
            eprintln!("[backend] start-up error reported: {}", cause.trim());
            remember_startup_error(app, cause.trim());
        } else if !line.trim().is_empty() {
            println!("[backend] {line}");
        }
    }
}

/// Build the JS the webview runs before any page script: it sets the two launch
/// globals the SPA reads. The values are serialized with `serde_json` so no
/// value can break out of its string literal.
///
/// * `TOKEN_GLOBAL` — the per-launch `/ws` handshake token (M7.1 UI seam).
/// * `BACKEND_URL_GLOBAL` — the runtime-learned backend base URL. The window is
///   served from the bundled app (a `tauri://` scheme origin), NOT from the
///   backend, so the SPA reaches the backend cross-origin with this absolute
///   base instead of a same-origin relative path.
fn launch_context_script(token: &str, backend_url: &str) -> String {
    // `to_string` on a &str yields a complete, escaped JS string literal.
    let token_literal = serde_json::to_string(token).unwrap_or_else(|_| "\"\"".to_string());
    let url_literal = serde_json::to_string(backend_url).unwrap_or_else(|_| "\"\"".to_string());
    format!(
        "window.{TOKEN_GLOBAL} = {token_literal};\n\
         window.{BACKEND_URL_GLOBAL} = {url_literal};\n"
    )
}

// @MX:ANCHOR: [AUTO] Stage-2 window boundary — builds the operator window on the
//   BUNDLED app origin (the `tauri://` app scheme) and injects the launch
//   context that authenticates it to the backend.
// @MX:REASON: the origin choice is load-bearing. `WebviewUrl::App` gives the
//   window the Stage-2 origin, which is the token-REQUIRED branch of the `/ws`
//   handshake (server/web/handshake.py) — building on `External(backend_url)`
//   instead would give it a Stage-1 loopback origin where the token is only
//   defence-in-depth, leaving the real product forever on the weaker branch.
//   Because the window is no longer served BY the backend, the injected backend
//   URL is the ONLY way the SPA can find it; dropping it strands the UI.
// @MX:SPEC: SPEC-COPILOT-DEPLOY-001 REQ-DEPLOY-002a / AC-DEPLOY-025
/// Build the native window: the bundled SPA on the Stage-2 origin, with the
/// launch token + backend base URL injected before the page loads.
///
/// `backend_url` is the address the backend just reported on stdout — used ONLY
/// as an injected value (so the cross-origin SPA can reach the backend), never
/// as the page the window navigates to.
fn open_main_window(app: &AppHandle, backend_url: &str) {
    if app.get_webview_window(MAIN_WINDOW_LABEL).is_some() {
        return; // already open — a restarted backend reuses the window
    }
    let token = app
        .try_state::<LaunchToken>()
        .map(|state| state.0.clone())
        .unwrap_or_default();
    let script = launch_context_script(&token, backend_url);
    let handle = app.clone();
    let result = app.run_on_main_thread(move || {
        let built = WebviewWindowBuilder::new(
            &handle,
            MAIN_WINDOW_LABEL,
            WebviewUrl::App("index.html".into()),
        )
        .title(WINDOW_TITLE)
        .initialization_script(&script)
        .inner_size(1180.0, 820.0)
        .min_inner_size(900.0, 600.0)
        .resizable(true)
        .build();
        if let Err(error) = built {
            eprintln!("[shell] could not open the main window: {error}");
        }
    });
    if let Err(error) = result {
        eprintln!("[shell] could not reach the main thread: {error}");
    }
}
