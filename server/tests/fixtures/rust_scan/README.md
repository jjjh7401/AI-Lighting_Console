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
| `rogue_credential/` | positive control (AC-DEPLOY-028 ①) — **network-clean** source, but `keyring` + `SecItemCopyMatching` in source, `keyring` as a direct dep, `security-framework` as a **transitive** lock entry | FAIL |
| `clean/` | negative control — legitimate Tauri shell (sidecar spawn, window, tray), benign transitive `socket2`/`mio`, sidecar-scoped shell capability | PASS |

`clean/src/main.rs` also carries a prose disclaimer naming `UdpSocket`,
`keyring`, `keychain` and `SecItemCopyMatching` in a comment: comment stripping
must tolerate it (the same prose tolerance the Python AST scan has) while a
marker hidden inside a string literal stays flagged.

Two INVARIANTS are scanned, and every violation reports which one it broke:

| Invariant | Markers | AC |
|---|---|---|
| `network` | `UdpSocket`, `std::net::`, `.bind/.connect/.send_to`, OSC crates, loopback/console-port literals, network capability grants | AC-DEPLOY-027 Layer ① |
| `credential` | `keyring`, `keychain`, `SecItem*`/`SecKeychain*`, `security-framework`, `keytar`, `wincred`, `CredRead`/`CredWrite`, `secret-service` | AC-DEPLOY-028 ① |

`rogue_credential/` is the fixture that proves the two classes are reported
separately: its network-violation list is EMPTY while its credential list is
not, so a credential breach can never be mistaken for (or masked by) a socket
finding.
