// Launch context injected by the Stage-2 desktop shell (src-tauri/src/sidecar.rs)
// through an initialization script that runs BEFORE any page script.
//
// In Stage-2 the operator window is served from the bundled app
// (origin `tauri://localhost`), so it is CROSS-origin to the Python backend and
// cannot reach it with a same-origin relative path — the shell injects the
// absolute backend base URL it learned from the backend's stdout at runtime.
//
// In Stage-1 browser mode nothing injects these globals: `backendBase()` returns
// the empty string, so `apiUrl("/api/x")` is byte-identical to the old relative
// `"/api/x"` and every request stays same-origin exactly as before. The two
// modes share ONE code path; only the injected value differs.

type LaunchGlobals = {
  __COPILOT_BACKEND_URL__?: string;
};

// The webview global the shell injects. Kept as a named constant so a rename on
// either side is a single, greppable edit (the Rust side pins the same string as
// `BACKEND_URL_GLOBAL`).
export const BACKEND_URL_GLOBAL = "__COPILOT_BACKEND_URL__";

export function backendBase(): string {
  const raw = (globalThis as LaunchGlobals).__COPILOT_BACKEND_URL__;
  // A trailing slash would double up against the leading slash of every path.
  return raw ? raw.replace(/\/+$/, "") : "";
}

// Prefix an app-relative path with the backend base. Same-origin ("") in Stage-1
// browser mode; the absolute `http://127.0.0.1:<port>` base in Stage-2.
export function apiUrl(path: string): string {
  return `${backendBase()}${path}`;
}
