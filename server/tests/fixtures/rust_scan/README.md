# Rust deny-all scan fixtures (AC-DEPLOY-027 Layer ①)

Committed control trees for `packaging/rust_scan.py`, exercised by
`server/tests/test_deploy_cross_language_scan.py`.

These are **fixtures, not a crate**: there is no workspace member here, nothing
builds them, and `src-tauri/` (the real Stage-2 shell root, created at M7.4)
deliberately does **not** exist yet. They exist so the deny-all mechanism is
proven NOW rather than asserted in prose.

| Tree | Role | Must |
|---|---|---|
| `rogue/` | positive control — raw `UdpSocket` send to `127.0.0.1:8000`, direct `rosc` + `socket2` deps | FAIL |
| `rogue_lock/` | positive control — clean source and manifest, OSC crate only as a **transitive** `Cargo.lock` entry | FAIL |
| `rogue_capability/` | positive control — clean source, capability grants `http:default` | FAIL |
| `clean/` | negative control — legitimate Tauri shell (sidecar spawn, window, tray), benign transitive `socket2`/`mio`, sidecar-scoped shell capability | PASS |

`clean/src/main.rs` also carries a prose disclaimer naming `UdpSocket` in a
comment: comment stripping must tolerate it (the same prose tolerance the Python
AST scan has) while a marker hidden inside a string literal stays flagged.
