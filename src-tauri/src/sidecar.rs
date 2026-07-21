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

/// fd 0 — the sidecar's own stdin. `tauri-plugin-shell` pipes it and this
/// process holds the write end for its entire lifetime, so ANY death of this
/// process (normal exit, crash, force-quit) closes the last write end and the
/// backend sees EOF immediately. That immediacy is why the pipe is the PRIMARY
/// trigger and the pid poll is only the fallback (plan section C, M7.2).
pub const PARENT_PIPE_FD_VALUE: &str = "0";

/// Line prefixes of the sidecar stdout protocol (`server/web/host_channel.py`).
pub const READY_PREFIX: &str = "@copilot:ready ";
pub const STATUS_PREFIX: &str = "@copilot:status ";

/// The window label the capability file scopes permissions to.
pub const MAIN_WINDOW_LABEL: &str = "main";

const WINDOW_TITLE: &str = "GrandMA3 Copilot";

/// The spawned backend, kept alive for the app's lifetime.
///
/// M7.4b takes this handle and turns it into the authoritative
/// process-GROUP kill on `RunEvent::Exit` — `CommandChild::kill()` alone
/// reaps only the sidecar pid (AC-DEPLOY-026 ①②). M7.4a's obligation is to
/// spawn it correctly and hold it.
pub struct BackendProcess(pub Mutex<Option<CommandChild>>);

/// The live sidecar's pid — the `killpg` target M7.4b needs, and the observable
/// evidence that the spawn actually happened.
pub fn backend_pid(app: &AppHandle) -> Option<u32> {
    let state = app.try_state::<BackendProcess>()?;
    let guard = state.0.lock().ok()?;
    guard.as_ref().map(|child| child.pid())
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
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(chunk) => {
                    consume_host_lines(&handle, &String::from_utf8_lossy(&chunk));
                }
                CommandEvent::Stderr(chunk) => {
                    eprint!("[backend] {}", String::from_utf8_lossy(&chunk));
                }
                CommandEvent::Terminated(payload) => {
                    if handle.get_webview_window(MAIN_WINDOW_LABEL).is_some() {
                        // It ran, served, and then stopped — the window is up and
                        // the tray badge is enough.
                        eprintln!("[backend] sidecar terminated: {payload:?}");
                        crate::tray::set_health(&handle, crate::tray::HEALTH_STOPPED);
                    } else {
                        // It never got as far as reporting a URL: a startup
                        // failure the operator needs told about in words. The
                        // commonest cause by far is an incomplete payload — the
                        // executable exists, its runtime tree does not.
                        crate::startup_error::report(
                            &handle,
                            &format!(
                                "The backend process exited during start-up before it \
                                 reported a ready address ({payload:?}). Its runtime \
                                 files are most likely missing or incomplete."
                            ),
                        );
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
            open_main_window(app, url.trim());
        } else if let Some(health) = line.strip_prefix(STATUS_PREFIX) {
            crate::tray::set_health(app, health.trim());
        } else if !line.trim().is_empty() {
            println!("[backend] {line}");
        }
    }
}

/// Build the native window on the URL the backend just reported.
///
/// The page it loads is the very same built SPA (`ui/dist`) the Stage-1 browser
/// mode loads — served by the backend, so the window's Origin is the loopback
/// origin the `/ws` handshake already allowlists (M7.1). Injecting the
/// per-launch token over Tauri IPC, which would let the window use the
/// token-REQUIRED Stage-2 origin instead, is M7.4b.
fn open_main_window(app: &AppHandle, url: &str) {
    if app.get_webview_window(MAIN_WINDOW_LABEL).is_some() {
        return; // already open — a restarted backend reuses the window
    }
    let parsed = match url.parse::<tauri::Url>() {
        Ok(value) => value,
        Err(error) => {
            eprintln!("[shell] backend reported an unparseable url {url:?}: {error}");
            return;
        }
    };
    let handle = app.clone();
    let result = app.run_on_main_thread(move || {
        let built = WebviewWindowBuilder::new(&handle, MAIN_WINDOW_LABEL, WebviewUrl::External(parsed))
            .title(WINDOW_TITLE)
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
