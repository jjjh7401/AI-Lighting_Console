"""Secure API-key storage adapter (M2 — REQ-DEPLOY-006/006a/007, AC-DEPLOY-004/016).

The packaged app must never store API keys in a committable plaintext file. This
module is the ONLY path a credential takes from the OS credential store into the
running backend: keys are read from the OS store (macOS Keychain / Windows
Credential Manager via ``keyring``) and injected into the backend process
environment at provider-client build time. They are never written to disk.

Stage 1 (this module) accesses ``keyring`` DIRECTLY from the Python backend
(DECIDE-F3); the Stage-1/Stage-2 common key interface is deferred to Stage-2
kickoff. The store is keyed on one stable service name (:data:`SERVICE_NAME`,
the reverse-DNS bundle identifier) — it is an ACL / identity anchor and MUST NOT
churn, since a change re-keys every stored credential.

Security invariants:

* **No plaintext-disk fallback (REQ-DEPLOY-006a / AC-DEPLOY-016).** When the OS
  credential store is unavailable / locked / access-denied, the persistent path
  raises :class:`KeystoreUnavailableError` — it NEVER writes the key to disk.
  The caller may then use the session-only path (:class:`SessionKeyStore`), an
  in-memory store that lives for the process lifetime and is never persisted.
* **Env-only injection (REQ-DEPLOY-007).** Keys reach the provider clients ONLY
  via process env vars (``ANTHROPIC_API_KEY``, ``GEMINI_API_KEY`` /
  ``GOOGLE_API_KEY``), preserving :mod:`server.llm.config`'s existing
  credential-key rejection contract (keys never enter the config file).
* **Env-scrub (DECIDE-M6 / AC-DEPLOY-004).** Any diagnostic / crash dump the app
  writes MUST route the process environment through :func:`scrub_environ`, so an
  env-injected key can never be serialised to disk by an exception logger.

⚠️ FEAS-2 (deferred to M6, re-verified there — NOT here): ``keyring`` selects its
OS backend via ``importlib.metadata`` entry points, which PyInstaller strips in a
frozen bundle -> silent null-backend fallback. This module runs in the dev venv,
so it is unaffected now, but the M6 PyInstaller onedir bundle spec MUST include
``--collect-all keyring`` plus hidden-imports for ``keyring.backends.macOS`` /
``keyring.backends.Windows`` (+ ``pywin32`` on Windows), and the keychain
round-trip below MUST be re-verified inside the frozen onedir smoke build at M6
(AC evidence lands there, not here).
"""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

# Reuse the MVP provider enum verbatim so the keystore and the provider loader
# can never drift on which providers are supported.
from server.llm.config import SUPPORTED_PROVIDERS

# Stable credential-store service name — the reverse-DNS bundle identifier
# (DECIDE-M1). It anchors the Keychain ACL / identity; DO NOT churn it.
SERVICE_NAME = "com.grandma3copilot.app"

# The redaction marker written in place of a credential value in any scrubbed
# environment dump (DECIDE-M6).
REDACTED = "***REDACTED***"

# Provider -> the backend env var name(s) that carry its API key. ``gemini``
# stores ONE key but injects both the primary name and the google-genai alias.
_PROVIDER_ENV_VARS: dict[str, tuple[str, ...]] = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}

# Credential-like substrings used to redact env var *names* in scrub_environ.
# Reuse the same vocabulary as server.llm.config._CREDENTIAL_KEYS (drift-free);
# matched case-insensitively as a substring of the normalised env var name
# (e.g. "ANTHROPIC_API_KEY" -> "anthropic_api_key" contains "api_key").
_CREDENTIAL_NAME_SUBSTRINGS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "credential",
    "password",
)


class KeystoreError(RuntimeError):
    """Base error for the secure key-storage adapter."""


class KeystoreUnavailableError(KeystoreError):
    """The OS credential store is unavailable, locked, or access was denied.

    Raised instead of ever falling back to plaintext-disk storage
    (REQ-DEPLOY-006a / AC-DEPLOY-016). The caller surfaces this explicitly and
    may offer the session-only in-memory path (:class:`SessionKeyStore`).
    """


def _require_provider(provider: object) -> str:
    if not isinstance(provider, str) or provider not in SUPPORTED_PROVIDERS:
        raise KeystoreError(f"provider must be one of {SUPPORTED_PROVIDERS}, got {provider!r}")
    return provider


def _require_key(key: object) -> str:
    if not isinstance(key, str) or not key.strip():
        raise KeystoreError("api key must be a non-empty string")
    return key


class SessionKeyStore:
    """Process-lifetime, in-memory API-key store (REQ-DEPLOY-006a fallback).

    Used only when the OS credential store is unavailable/locked/denied: the key
    lives in memory for the process lifetime and is NEVER written to disk. A
    fresh instance can be injected into the module functions for test isolation;
    otherwise the module-default instance is used.
    """

    __slots__ = ("_keys",)

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def set(self, provider: str, key: str) -> None:
        self._keys[_require_provider(provider)] = _require_key(key)

    def get(self, provider: str) -> str | None:
        return self._keys.get(_require_provider(provider))

    def delete(self, provider: str) -> None:
        self._keys.pop(_require_provider(provider), None)

    def clear(self) -> None:
        self._keys.clear()


# The controlled module-default session store. Encapsulated (not a bare global
# dict) with an explicit clear() so callers/tests reset it deterministically.
_DEFAULT_SESSION = SessionKeyStore()


def _resolve_session(session: SessionKeyStore | None) -> SessionKeyStore:
    return session if session is not None else _DEFAULT_SESSION


def env_vars_for_provider(provider: str) -> tuple[str, ...]:
    """The backend env var name(s) that carry ``provider``'s API key."""
    return _PROVIDER_ENV_VARS[_require_provider(provider)]


def set_api_key(provider: str, key: str) -> None:
    """Persist ``key`` for ``provider`` in the OS credential store.

    NEVER falls back to plaintext disk: if the store is unavailable/locked/denied
    this raises :class:`KeystoreUnavailableError` (REQ-DEPLOY-006a). The caller
    handles that explicitly (e.g. offer the session-only path).
    """
    provider = _require_provider(provider)
    key = _require_key(key)
    try:
        keyring.set_password(SERVICE_NAME, provider, key)
    except KeyringError as error:
        raise KeystoreUnavailableError(
            f"cannot store key for {provider!r}: OS credential store unavailable "
            f"({error}). The key was NOT written to disk."
        ) from error


def set_session_api_key(provider: str, key: str, *, session: SessionKeyStore | None = None) -> None:
    """Store ``key`` for ``provider`` in the session-only in-memory store.

    The session path (REQ-DEPLOY-006a) is the explicit fallback when the OS
    credential store is unavailable — the key stays in memory and is never
    persisted.
    """
    _resolve_session(session).set(provider, key)


def get_api_key(provider: str, *, session: SessionKeyStore | None = None) -> str | None:
    """Resolve ``provider``'s API key: session store first, then the OS store.

    Returns ``None`` when no key is configured. When the OS store errors and no
    session key exists, raises :class:`KeystoreUnavailableError` (explicit error,
    AC-DEPLOY-016 (2)).
    """
    provider = _require_provider(provider)
    session_key = _resolve_session(session).get(provider)
    if session_key is not None:
        return session_key
    try:
        return keyring.get_password(SERVICE_NAME, provider)
    except KeyringError as error:
        raise KeystoreUnavailableError(
            f"cannot read key for {provider!r}: OS credential store unavailable ({error})"
        ) from error


def delete_api_key(provider: str, *, session: SessionKeyStore | None = None) -> None:
    """Remove ``provider``'s key from both the OS store and the session store.

    Idempotent: a missing key is not an error. A store failure (unavailable /
    locked / denied) raises :class:`KeystoreUnavailableError`.
    """
    provider = _require_provider(provider)
    _resolve_session(session).delete(provider)
    try:
        keyring.delete_password(SERVICE_NAME, provider)
    except PasswordDeleteError:
        pass  # nothing stored — idempotent delete
    except KeyringError as error:
        raise KeystoreUnavailableError(
            f"cannot delete key for {provider!r}: OS credential store unavailable ({error})"
        ) from error


# @MX:ANCHOR: [AUTO] credential -> process-env boundary — the SOLE point where a
#   stored API key crosses into the backend process environment for provider
#   client construction. High fan_in (provider client build, inject_active_
#   provider_key, tests).
# @MX:REASON: REQ-DEPLOY-007/AC-DEPLOY-004 security invariant — a key must reach
#   ONLY the process env, never a file on disk. A new call site that writes the
#   resolved key anywhere but an in-memory environ mapping is a plaintext-leak
#   regression.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def inject_key_for_provider(
    provider: str,
    *,
    environ: MutableMapping[str, str] | None = None,
    session: SessionKeyStore | None = None,
) -> list[str]:
    """Inject ``provider``'s API key into ``environ`` (default ``os.environ``).

    Resolves the key (session first, then OS store) and writes it into every env
    var name for the provider. Env-only — never touches disk. Returns the list
    of env var names set (empty when no key is configured).
    """
    provider = _require_provider(provider)
    target = os.environ if environ is None else environ
    key = get_api_key(provider, session=session)
    if key is None:
        return []
    names = list(_PROVIDER_ENV_VARS[provider])
    for name in names:
        target[name] = key
    return names


def inject_active_provider_key(
    *,
    environ: MutableMapping[str, str] | None = None,
    session: SessionKeyStore | None = None,
    user_path: object = None,
    seed_path: object = None,
) -> list[str]:
    """Inject the key for the *active* provider (M1 settings integration seam).

    Reads the active provider from ``resolve_effective_settings`` (the M1
    precedence chain) and injects its key. This is the one call the provider
    client bootstrap makes at start-up.
    """
    # Lazy import — mirrors settings.py's own lazy import to avoid paying the
    # settings-resolution import cost when only the low-level API is used.
    from server.deploy.settings import resolve_effective_settings

    settings = resolve_effective_settings(user_path=user_path, seed_path=seed_path)
    return inject_key_for_provider(settings.active_provider, environ=environ, session=session)


def _is_credential_name(name: str) -> bool:
    normalised = name.lower()
    if name in _PROVIDER_ENV_VARS.get("anthropic", ()) or name in _PROVIDER_ENV_VARS.get(
        "gemini", ()
    ):
        return True
    return any(token in normalised for token in _CREDENTIAL_NAME_SUBSTRINGS)


# @MX:ANCHOR: [AUTO] env-scrub boundary — the guard every diagnostic/crash path
#   MUST route the process environment through before serialising it (DECIDE-M6).
# @MX:REASON: AC-DEPLOY-004 — REQ-DEPLOY-007 injects keys into process env, so a
#   crash handler/exception logger that serialises a raw os.environ would write a
#   plaintext key to disk. Redacting credential-like vars here is the single
#   defence; bypassing it re-opens the exact leak vector.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def scrub_environ(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a copy of ``environ`` (default ``os.environ``) with credential-like
    values redacted, safe for inclusion in any diagnostic / crash dump.

    NEVER serialise a raw ``os.environ`` into a file the app writes — always
    route it through this function first (DECIDE-M6 / AC-DEPLOY-004). The input
    mapping is not mutated.
    """
    source = os.environ if environ is None else environ
    return {
        name: (REDACTED if _is_credential_name(name) else value) for name, value in source.items()
    }


def clear_session_keys(session: SessionKeyStore | None = None) -> None:
    """Clear all session-only keys (call at session end / test teardown)."""
    _resolve_session(session).clear()
