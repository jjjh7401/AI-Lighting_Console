"""Rust/Tauri **deny-all** static scan (M7.3, AC-DEPLOY-027 / SAFETY-2 Layer ①;
M7.6, AC-DEPLOY-028 ① key custody).

Two INVARIANTS are scanned by the same machinery and reported separately, so a
finding always says which one it broke:

``network`` (AC-DEPLOY-027 Layer ①)
    The shell must own no console byte — see the raw-socket rationale below.

``credential`` (AC-DEPLOY-028 ①)
    Key custody is deliberately Python-side: the backend sidecar reaches the OS
    keychain via Python ``keyring`` (``server/deploy/keystore.py``), and the
    Rust host does sidecar spawn + lifecycle ONLY (plan.md §A.2, decision F5').
    So credential-store access anywhere in the shell — source marker, direct
    dependency, or TRANSITIVE lock entry — is by definition an architecture
    violation, not a judgement call. The allowlist is EMPTY here too.

The Stage-1 Python guards (``server/tests/test_architecture.py`` import boundary,
``server/tests/test_deploy_safety_invariants.py`` AST allowlist) are blind to a
second language. A Tauri shell written in Rust can open ``std::net::UdpSocket``
and send to ``127.0.0.1:<console port>`` without importing a single Python
module — a complete gate bypass that no Python scan can see.

The legitimate work of the Tauri shell is: spawn the PyInstaller backend as a
sidecar, load ``ui/dist`` in a native window, and draw a tray icon. **None of
that needs a socket to the console.** So the allowlist here is EMPTY: any raw
socket marker, any OSC/raw-socket crate, and any loopback/console-port literal
in the shell's Rust source or manifests is a violation.

Fail-closed contract (the vacuous-pass hazard this module exists to close):

* An **absent** or **empty** tree is ``blocked`` — a FAIL, never a pass. A scan
  that read nothing found nothing, which is not the same as "found nothing bad".
* Every result carries ``files_scanned`` (plus per-category counts) so a caller
  can assert the scan was non-vacuous. ``ScanResult.ok`` is False whenever the
  scan was blocked, so 0 files can never render as "0 violations, PASS".

Comment handling: markers are matched against **comment-stripped** source, with
the stripper string-literal-aware. A doc comment that DISCLAIMS raw sockets
("this shell never opens a UdpSocket") must not false-positive — the same prose
tolerance the Python AST scan has — but a marker hidden inside a string literal
(``"http://127.0.0.1:8000"``, whose ``//`` would fool a naive line-comment
stripper) must still be flagged. Stripping is fail-closed in that direction.

Pure stdlib, no third-party imports: this runs in CI (via
``server/tests/test_deploy_cross_language_scan.py``) and inside the packaged E2E
host (``packaging/verify_packaged_e2e.py``).
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The Stage-2 Tauri shell root. It does NOT exist until M7.4 — scanning it today
# yields a BLOCKED result by design (see the fail-closed contract above).
SRC_TAURI_DIR = REPO_ROOT / "src-tauri"

# Console-facing port literals. The console input port (send_port) defaults to
# 8000 and the feedback receive port to 9000 (server/bridge/osc.py BridgeConfig);
# either literal appearing in the shell's Rust source means the shell knows how
# to talk to the console directly, which it must never need to.
DEFAULT_PORT_LITERALS = (8000, 9000)

# Build output — never scanned. Counting it would let a genuinely empty source
# tree fake a non-vacuous scan.
_IGNORED_DIRS = frozenset({"target", ".git", "node_modules", "gen"})

_SOURCE_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("udp_socket", re.compile(r"\bUdpSocket\b")),
    ("std_net", re.compile(r"\bstd\s*::\s*net\s*::")),
    # Both the method form (``sock.bind(..)``) and the path form
    # (``UdpSocket::bind(..)``) — a deny-all scan must not miss either.
    ("socket_bind", re.compile(r"(?:\.|::)bind\s*\(")),
    ("socket_connect", re.compile(r"(?:\.|::)connect\s*\(")),
    ("socket_send_to", re.compile(r"(?:\.|::)send_to\s*\(")),
    ("osc_crate", re.compile(r"\b(?:rosc|nannou_osc|async_osc|oscpack|rust_osc)\b")),
    ("loopback_literal", re.compile(r"\b127\.0\.0\.1\b")),
)

# @MX:ANCHOR: [AUTO] credential-store marker set — the ONLY static detector for
#   Rust-side key access; the Python keystore guards cannot see this language
# @MX:REASON: key custody is Python-side by architecture (plan.md §A.2 F5'), so
#   loosening a marker here silently re-opens a path where the Rust host reads
#   the OS keychain directly — the exact breach AC-DEPLOY-028 ① exists to block.
#   Markers are DELIBERATELY narrow (credential-STORE APIs only): the shell
#   legitimately mints and carries a per-launch handshake token, so generic
#   words like "token"/"secret"/"credential" are NOT markers — they would
#   false-positive on sidecar.rs and force the set to be weakened.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
#   The store-name markers match as a SUBSTRING, not on a word boundary: a
#   shell writes `fn open_keychain()` or `let keyring_entry = ...`, where `\b`
#   never fires because `_` is a word character. These names are distinctive
#   enough that any identifier containing them IS about the credential store.
_CREDENTIAL_SOURCE_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("credential_keyring", re.compile(r"keyring", re.IGNORECASE)),
    ("credential_keychain", re.compile(r"keychain", re.IGNORECASE)),
    # Security.framework symbols, incl. `SecItemCopyMatching` / `SecKeychainAdd…`.
    ("credential_security_framework_api", re.compile(r"\bSec(?:Item|Keychain)\w*", re.IGNORECASE)),
    ("credential_security_framework_crate", re.compile(r"security[_-]framework", re.IGNORECASE)),
    ("credential_keytar", re.compile(r"keytar", re.IGNORECASE)),
    ("credential_wincred", re.compile(r"wincred", re.IGNORECASE)),
    # Win32 credential-manager entry points: `CredReadW` / `CredWriteW` / …
    ("credential_windows_cred_api", re.compile(r"\bCred(?:Read|Write)\w*", re.IGNORECASE)),
    ("credential_secret_service", re.compile(r"secret[_-]service", re.IGNORECASE)),
)

# Credential-store crates denied ANYWHERE, including as a TRANSITIVE Cargo.lock
# entry. Nothing a sidecar-spawning shell legitimately needs pulls a credential
# crate, so a transitive appearance is itself the finding — `security-framework`
# is the Rust binding to the macOS Security framework that houses the Keychain
# APIs, and it arrives through a TLS stack the shell already denies directly.
_DENIED_CREDENTIAL_CRATES = frozenset(
    {
        "keyring",
        "security-framework",
        "security-framework-sys",
        "keytar",
        "wincred",
        "windows-credentials",
        "secret-service",
        "keyutils",
        "linux-keyutils",
    }
)

# Marker names belonging to the ``credential`` invariant (source + manifest).
CREDENTIAL_MARKERS = frozenset(
    {marker for marker, _ in _CREDENTIAL_SOURCE_MARKERS}
    | {"denied_credential_crate_direct", "denied_credential_crate_transitive"}
)


def credential_source_marker_names() -> tuple[str, ...]:
    """Distinct source-marker names of the ``credential`` invariant."""
    return tuple(dict.fromkeys(marker for marker, _ in _CREDENTIAL_SOURCE_MARKERS))

# Crates denied ANYWHERE, including as a TRANSITIVE Cargo.lock entry: nothing in
# a legitimate Tauri dependency graph pulls an OSC or raw-UDP crate, so a
# transitive appearance is itself the finding.
_DENIED_CRATES_TRANSITIVE = frozenset(
    {
        "rosc",
        "nannou_osc",
        "nannou-osc",
        "async-osc",
        "async_osc",
        "oscpack",
        "osc",
        "udp-socket",
        "udp_socket",
        "laminar",
    }
)

# Additional crates denied only as a DIRECT dependency of the shell manifest.
# tokio/hyper legitimately pull socket2 + mio TRANSITIVELY (denying those in
# Cargo.lock would make this gate unpassable at M7.4), but the shell declaring
# one itself is a deliberate choice to own a network surface.
_DENIED_CRATES_DIRECT_ONLY = frozenset(
    {
        "socket2",
        "mio",
        "net2",
        "quinn",
        "reqwest",
        "ureq",
        "hyper",
        "tungstenite",
        "tokio-tungstenite",
        "websocket",
        "tauri-plugin-http",
        "tauri-plugin-websocket",
        "tauri-plugin-upload",
    }
)

_DEPENDENCY_TABLES = ("dependencies", "dev-dependencies", "build-dependencies")

# Tauri v2 capability permission namespaces that grant a network surface. The
# shell must deny all of them; ``shell:`` is permitted ONLY for sidecar spawn
# (scoped in the capability file — the concrete scope is an M7.4 obligation).
_DENIED_CAPABILITY_PREFIXES = ("http:", "websocket:", "upload:", "geolocation:")

_LOCK_NAME = re.compile(r'^\s*name\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def _normalise_crate(name: str) -> str:
    """Crate names compare hyphen-insensitively and case-insensitively."""
    return name.replace("_", "-").lower()


_NORMALISED_CREDENTIAL_CRATES = frozenset(_normalise_crate(c) for c in _DENIED_CREDENTIAL_CRATES)
_NORMALISED_NETWORK_CRATES_TRANSITIVE = frozenset(
    _normalise_crate(c) for c in _DENIED_CRATES_TRANSITIVE
)
_NORMALISED_NETWORK_CRATES_DIRECT = frozenset(
    _normalise_crate(c) for c in (_DENIED_CRATES_TRANSITIVE | _DENIED_CRATES_DIRECT_ONLY)
)


@dataclass(frozen=True)
class Violation:
    """One deny-all finding: what tripped, where, and the offending text."""

    path: str
    marker: str
    line: int
    detail: str

    @property
    def invariant(self) -> str:
        """Which invariant this finding broke: ``credential`` or ``network``."""
        return "credential" if self.marker in CREDENTIAL_MARKERS else "network"

    def __str__(self) -> str:  # pragma: no cover - diagnostic sugar
        return f"{self.path}:{self.line} [{self.invariant}/{self.marker}] {self.detail}"


@dataclass(frozen=True)
class ScanResult:
    """Outcome of one deny-all tree scan.

    ``blocked`` is the fail-closed signal (absent/empty tree). ``ok`` is True
    ONLY when the scan actually read files AND found nothing.
    """

    root: str
    files_scanned: int
    rust_files_scanned: int
    manifest_files_scanned: int
    capability_files_scanned: int
    violations: tuple[Violation, ...] = ()
    blocked: bool = False
    blocked_reason: str = ""
    scanned_paths: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return not self.blocked and not self.violations and self.files_scanned > 0

    @property
    def credential_violations(self) -> tuple[Violation, ...]:
        """Findings that broke key custody (AC-DEPLOY-028 ①)."""
        return tuple(v for v in self.violations if v.invariant == "credential")

    @property
    def network_violations(self) -> tuple[Violation, ...]:
        """Findings that broke the console send-surface (AC-DEPLOY-027 Layer ①)."""
        return tuple(v for v in self.violations if v.invariant == "network")

    def summary(self) -> str:
        if self.blocked:
            return f"BLOCKED ({self.blocked_reason})"
        verdict = "PASS" if self.ok else "FAIL"
        line = (
            f"{verdict} — {self.files_scanned} file(s) scanned "
            f"(rust={self.rust_files_scanned}, manifest={self.manifest_files_scanned}, "
            f"capability={self.capability_files_scanned}), "
            f"{len(self.violations)} violation(s)"
        )
        if not self.violations:
            # The clean PASS line is quoted verbatim as run-phase evidence — a
            # second invariant must not reformat it.
            return line
        return (
            f"{line} [network={len(self.network_violations)}, "
            f"credential={len(self.credential_violations)}]"
        )


# ------------------------------------------------------------------ source scanning


def strip_rust_comments(source: str) -> str:
    """Blank out ``//`` and ``/* */`` comments, preserving string literals.

    Newlines are preserved so line numbers stay accurate. String literals are
    kept verbatim: a marker inside ``"http://127.0.0.1"`` must still be seen
    (a naive stripper would treat the ``//`` as a comment start and swallow it,
    which is fail-OPEN).
    """
    out: list[str] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                out.append(source[i])
                if source[i] == "\\" and i + 1 < n:
                    out.append(source[i + 1])
                    i += 2
                    continue
                if source[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i < n and not (source[i] == "*" and i + 1 < n and source[i + 1] == "/"):
                if source[i] == "\n":
                    out.append("\n")
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# @MX:ANCHOR: [AUTO] deny-all Rust marker scan — the ONLY cross-language
#   detector for BOTH the OSC send surface (AC-DEPLOY-027 Layer ①) and Rust-side
#   credential-store access (AC-DEPLOY-028 ①) in the Stage-2 Tauri shell
# @MX:REASON: the Python AST/import guards cannot see Rust; loosening either
#   marker set or adding an allowlist entry silently re-opens the raw-UDP
#   gate-bypass path the Stage-1 scans were built to close, or the Rust-reads-
#   the-keychain path that breaks Python-side key custody
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def scan_rust_source(
    source: str,
    rel_path: str,
    *,
    port_literals: tuple[int, ...] = DEFAULT_PORT_LITERALS,
) -> list[Violation]:
    """Return every deny-all violation in one Rust source file."""
    stripped = strip_rust_comments(source)
    markers = list(_SOURCE_MARKERS) + list(_CREDENTIAL_SOURCE_MARKERS)
    for port in port_literals:
        markers.append(("console_port_literal", re.compile(rf"(?<![\w.]){port}(?![\w.])")))

    violations: list[Violation] = []
    for line_no, line in enumerate(stripped.splitlines(), start=1):
        for marker, pattern in markers:
            match = pattern.search(line)
            if match is not None:
                violations.append(
                    Violation(
                        path=rel_path,
                        marker=marker,
                        line=line_no,
                        detail=f"{match.group(0)!r} in {line.strip()[:120]!r}",
                    )
                )
    return violations


# ------------------------------------------------------------------ manifest scanning


def scan_cargo_toml(text: str, rel_path: str) -> list[Violation]:
    """Reject denied DIRECT dependencies (and an unparseable manifest).

    Credential-store crates are denied as a direct dependency too, and are
    reported under their own marker so the finding names the broken invariant.
    """
    try:
        manifest = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        # Fail-closed: a manifest we cannot read is a manifest we cannot clear.
        return [Violation(rel_path, "unparseable_manifest", 1, str(error))]

    violations: list[Violation] = []
    tables: list[tuple[str, dict]] = []
    for table in _DEPENDENCY_TABLES:
        section = manifest.get(table)
        if isinstance(section, dict):
            tables.append((table, section))
    targets = manifest.get("target")
    if isinstance(targets, dict):
        for triple, spec in targets.items():
            if not isinstance(spec, dict):
                continue
            for table in _DEPENDENCY_TABLES:
                section = spec.get(table)
                if isinstance(section, dict):
                    tables.append((f"target.{triple}.{table}", section))

    for table, section in tables:
        for crate in section:
            normalised = _normalise_crate(crate)
            if normalised in _NORMALISED_CREDENTIAL_CRATES:
                violations.append(
                    Violation(
                        rel_path,
                        "denied_credential_crate_direct",
                        1,
                        f"[{table}] declares credential-store crate {crate!r}",
                    )
                )
            elif normalised in _NORMALISED_NETWORK_CRATES_DIRECT:
                violations.append(
                    Violation(
                        rel_path,
                        "denied_crate_direct",
                        1,
                        f"[{table}] declares denied crate {crate!r}",
                    )
                )
    return violations


def scan_cargo_lock(text: str, rel_path: str) -> list[Violation]:
    """Reject denied crates anywhere in the resolved graph (transitive included).

    Covers both invariants: OSC/raw-socket crates (network) and credential-store
    crates (key custody), each under its own marker.
    """
    violations: list[Violation] = []
    for match in _LOCK_NAME.finditer(text):
        crate = match.group(1)
        normalised = _normalise_crate(crate)
        if normalised in _NORMALISED_CREDENTIAL_CRATES:
            marker = "denied_credential_crate_transitive"
            detail = f"resolved graph contains credential-store crate {crate!r}"
        elif normalised in _NORMALISED_NETWORK_CRATES_TRANSITIVE:
            marker = "denied_crate_transitive"
            detail = f"resolved graph contains denied crate {crate!r}"
        else:
            continue
        line = text.count("\n", 0, match.start()) + 1
        violations.append(Violation(rel_path, marker, line, detail))
    return violations


def scan_capability(text: str, rel_path: str) -> list[Violation]:
    """Reject Tauri v2 capability permissions that grant a network surface."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        return [Violation(rel_path, "unparseable_capability", 1, str(error))]

    permissions = document.get("permissions") if isinstance(document, dict) else None
    if not isinstance(permissions, list):
        return []
    violations: list[Violation] = []
    for entry in permissions:
        name = entry if isinstance(entry, str) else (entry or {}).get("identifier", "")
        if not isinstance(name, str):
            continue
        if name.startswith(_DENIED_CAPABILITY_PREFIXES):
            violations.append(
                Violation(
                    rel_path,
                    "denied_capability",
                    1,
                    f"capability grants network permission {name!r}",
                )
            )
    return violations


# ------------------------------------------------------------------ tree scanning


def _iter_scannable(root: Path):
    """Yield (path, category) for every scannable file under ``root``."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _IGNORED_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if path.suffix == ".rs":
            yield path, "rust"
        elif path.name == "Cargo.toml":
            yield path, "cargo_toml"
        elif path.name == "Cargo.lock":
            yield path, "cargo_lock"
        elif path.suffix == ".json" and "capabilities" in path.relative_to(root).parts[:-1]:
            yield path, "capability"


# @MX:ANCHOR: [AUTO] fail-closed tree gate — an absent or zero-file src-tauri/
#   tree returns blocked=True (FAIL), never an empty-and-therefore-clean PASS
# @MX:REASON: AC-DEPLOY-027 Layer ① ①/② exist because 0 files scanned reported
#   as 0 violations is the vacuous pass that would let the Stage-2 Rust shell
#   ship an unscanned raw-UDP path; callers assert files_scanned > 0 through this
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def scan_rust_tree(
    root: Path | str,
    *,
    port_literals: tuple[int, ...] = DEFAULT_PORT_LITERALS,
) -> ScanResult:
    """Deny-all scan of a Rust/Tauri tree. Absent/empty => blocked (FAIL)."""
    root = Path(root)
    if not root.is_dir():
        return ScanResult(
            root=str(root),
            files_scanned=0,
            rust_files_scanned=0,
            manifest_files_scanned=0,
            capability_files_scanned=0,
            blocked=True,
            blocked_reason=(
                f"{root} does not exist — a deny-all scan of an absent tree is a "
                "FAIL (blocked), not a pass (AC-DEPLOY-027 Layer ① ①)"
            ),
        )

    violations: list[Violation] = []
    counts = {"rust": 0, "cargo_toml": 0, "cargo_lock": 0, "capability": 0}
    scanned: list[str] = []

    for path, category in _iter_scannable(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        counts[category] += 1
        scanned.append(rel)
        if category == "rust":
            violations.extend(scan_rust_source(text, rel, port_literals=port_literals))
        elif category == "cargo_toml":
            violations.extend(scan_cargo_toml(text, rel))
        elif category == "cargo_lock":
            violations.extend(scan_cargo_lock(text, rel))
        else:
            violations.extend(scan_capability(text, rel))

    files_scanned = sum(counts.values())
    if files_scanned == 0:
        return ScanResult(
            root=str(root),
            files_scanned=0,
            rust_files_scanned=0,
            manifest_files_scanned=0,
            capability_files_scanned=0,
            blocked=True,
            blocked_reason=(
                f"{root} contains no scannable files (*.rs / Cargo.toml / Cargo.lock / "
                "capabilities/*.json) — a 0-file scan is a FAIL (blocked), not 0 violations"
            ),
        )

    return ScanResult(
        root=str(root),
        files_scanned=files_scanned,
        rust_files_scanned=counts["rust"],
        manifest_files_scanned=counts["cargo_toml"] + counts["cargo_lock"],
        capability_files_scanned=counts["capability"],
        violations=tuple(violations),
        scanned_paths=tuple(scanned),
    )


if __name__ == "__main__":  # pragma: no cover - operator entry point
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC_TAURI_DIR
    outcome = scan_rust_tree(target)
    print(f"deny-all Rust/Tauri scan: {outcome.root}")
    print("invariants: network (AC-DEPLOY-027 Layer ①), credential (AC-DEPLOY-028 ①)")
    print(outcome.summary())
    for violation in outcome.violations:
        print(f"  {violation}")
    sys.exit(0 if outcome.ok else 1)
