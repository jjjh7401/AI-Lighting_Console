// Prevents an additional console window on Windows in release. DO NOT REMOVE.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! GrandMA3 Copilot — Stage-2 Tauri v2 shell (SPEC-COPILOT-DEPLOY-001 M7.4a).
//!
//! Three jobs, and deliberately nothing else: spawn the packaged backend as a
//! sidecar, show the page that backend serves in a native window, and draw a
//! tray icon carrying the gate-truth health badge. Everything the app actually
//! DOES — the LLM turn, the safety gate, the single OSC chokepoint — stays in
//! the audited Python process. This shell owns no network surface at all, which
//! `packaging/rust_scan.py` enforces with an EMPTY allowlist (AC-DEPLOY-027).

mod sidecar;
mod startup_error;
mod tray;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let handle = app.handle();
            // Tray first: it is the only surface that exists before the backend
            // reports in, so a slow or failed start is still visible.
            tray::install(handle)?;
            // A failed spawn is REPORTED, never propagated with `?`. Returning
            // Err here makes Tauri panic inside the macOS app delegate, which
            // cannot unwind and aborts the process — the operator would get a
            // backtrace instead of a cause (REQ-DEPLOY-018~020).
            if let Err(cause) = sidecar::spawn_backend(handle) {
                startup_error::report(handle, &cause);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running the GrandMA3 Copilot shell");
}
