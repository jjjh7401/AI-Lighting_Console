//! Human-readable startup failure reporting (M7.4a — REQ-DEPLOY-018~020).
//!
//! "The backend did not start" is a foreseeable, recoverable condition for a
//! shipped desktop app: a stale or partial bundle, a quarantined binary, a
//! missing PyInstaller runtime payload. The M5 error-UX discipline says such a
//! condition surfaces as a plain-language cause plus a next step.
//!
//! A Rust `panic!` inside Tauri's setup hook does the opposite: it aborts the
//! process (non-unwinding, because the panic crosses the Objective-C app
//! delegate) and the operator gets a stack backtrace in a terminal they may not
//! even have open. This module is the alternative — a native dialog, a tray
//! badge that stays readable, and a process that stays alive so the operator can
//! read the message and quit deliberately.

use tauri::AppHandle;
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

const TITLE: &str = "GrandMA3 Copilot — backend did not start";

/// Report a startup failure to the operator without taking the app down.
///
/// Non-blocking on purpose: this runs on the main thread during setup, and a
/// blocking dialog there would deadlock the very event loop that has to draw it.
pub fn report(app: &AppHandle, cause: &str) {
    let body = format!(
        "{cause}\n\n\
         What to try:\n\
         1. Quit and relaunch the app.\n\
         2. If it keeps failing, the installed copy is incomplete — reinstall it.\n\
         3. Developer builds: run `python packaging/stage_sidecar.py`, then \
         `python packaging/stage_sidecar.py --dev-mirror`.\n\n\
         The app will stay open so this message can be read; use the tray icon to quit."
    );
    // Log the WHOLE message, not just the cause: an operator running from a
    // terminal should see the same guidance the dialog shows.
    eprintln!("[shell] {TITLE}\n{body}");
    crate::tray::set_health(app, crate::tray::HEALTH_STOPPED);
    app.dialog()
        .message(body)
        .kind(MessageDialogKind::Error)
        .title(TITLE)
        .show(|_| {});
}
