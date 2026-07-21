// NEGATIVE CONTROL fixture — a legitimate Tauri v2 shell. It spawns the
// PyInstaller backend as a sidecar, loads ui/dist in the native window, and
// draws a tray icon. None of that needs a socket to the console: there is no
// UdpSocket, no std net import and no raw send anywhere in this shell — the
// gate owns every console byte. This comment deliberately NAMES the markers so
// the deny-all scan's comment stripping is exercised (a prose disclaimer must
// not false-positive, exactly as in the Python AST scan).

use tauri::Manager;
use tauri_plugin_shell::ShellExt;

fn spawn_backend(app: &tauri::AppHandle) -> Result<(), String> {
    let command = app
        .shell()
        .sidecar("grandma3-copilot-backend")
        .map_err(|error| error.to_string())?;
    let (_rx, _child) = command.spawn().map_err(|error| error.to_string())?;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            spawn_backend(&app.handle()).map_err(|error| -> Box<dyn std::error::Error> {
                Box::from(error)
            })?;
            let _window = app.get_webview_window("main");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running the copilot shell");
}
