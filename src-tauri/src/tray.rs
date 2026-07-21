//! System tray + connection/health indicator (M7.4a — AC-DEPLOY-024 ③).
//!
//! The badge reuses the M5 gate-truth health vocabulary verbatim (`online` /
//! `console_offline` / `responder_degraded`) so the tray and the in-app
//! `StatusBanner` can never disagree: both render the SAME state the safety gate
//! computed. The value arrives on the sidecar's stdout
//! (`server/web/host_channel.py`) because this process owns no socket to ask
//! over (AC-DEPLOY-027 Layer 1).

use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager, Wry};

pub const TRAY_ID: &str = "copilot-tray";

const STATUS_ITEM_ID: &str = "copilot-status";
const SHOW_ITEM_ID: &str = "copilot-show";

/// Shell-side pseudo-states. The three real states below are gate truth.
pub const HEALTH_STARTING: &str = "starting";
pub const HEALTH_STOPPED: &str = "stopped";

/// Handles kept so the badge can be updated after the tray is built.
struct TrayHandles {
    status: MenuItem<Wry>,
}

/// Render one health state as an operator-readable badge line.
///
/// The three gate-truth arms mirror `server/web/session.py` / the M5
/// `healthGuidance` copy; anything else is a shell-side lifecycle state.
pub fn health_label(health: &str) -> &'static str {
    match health {
        "online" => "Online — console responding",
        "console_offline" => "Console offline — new executions blocked",
        "responder_degraded" => "Responder degraded — confirmations delayed",
        HEALTH_STOPPED => "Backend stopped",
        _ => "Starting…",
    }
}

pub fn install(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let status = MenuItem::with_id(
        app,
        STATUS_ITEM_ID,
        health_label(HEALTH_STARTING),
        false, // a read-only badge, not a command
        None::<&str>,
    )?;
    let show = MenuItem::with_id(app, SHOW_ITEM_ID, "Show window", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = PredefinedMenuItem::quit(app, Some("Quit GrandMA3 Copilot"))?;
    let menu = Menu::with_items(app, &[&status, &separator, &show, &quit])?;

    let icon = app
        .default_window_icon()
        .cloned()
        .ok_or("no default window icon is embedded in the bundle")?;

    TrayIconBuilder::with_id(TRAY_ID)
        .icon(icon)
        .menu(&menu)
        .tooltip(health_label(HEALTH_STARTING))
        .show_menu_on_left_click(true)
        .on_menu_event(|app, event| {
            if event.id() == SHOW_ITEM_ID {
                if let Some(window) = app.get_webview_window(crate::sidecar::MAIN_WINDOW_LABEL) {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    app.manage(TrayHandles { status });
    Ok(())
}

/// Push a new health state onto the tray badge. Best-effort: a tray that failed
/// to build must never take the app down, and a stale badge is not worth a panic.
pub fn set_health(app: &AppHandle, health: &str) {
    let label = health_label(health);
    let handle = app.clone();
    let _ = app.run_on_main_thread(move || {
        if let Some(state) = handle.try_state::<TrayHandles>() {
            let _ = state.status.set_text(label);
        }
        if let Some(tray) = handle.tray_by_id(TRAY_ID) {
            let _ = tray.set_tooltip(Some(label));
        }
    });
}
