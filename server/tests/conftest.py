"""Suite-wide pytest fixtures for the server tests.

Autouse keyring neutralisation
------------------------------
Every test in this suite runs against a fresh in-memory keyring backend instead
of the real OS credential store (macOS Keychain / Windows Credential Manager).
This keeps the suite deterministic and unattended: REQ-DEPLOY-028 wired the
active-provider key read into ``server.web.serve.build_runtime`` at start-up, and
``GET /api/settings`` reads per-provider key presence (``_provider_key_status``),
so on a machine that already has a key stored under the app's service name those
paths would otherwise block on an interactive Keychain access prompt.

The fixture is deliberately override-friendly. A test that installs its own
backend — ``test_deploy_keystore.py::memory_keyring`` / ``broken_keyring``,
``test_web_serve.py::broken_keyring`` and its autouse ``_isolate_real_keyring``,
the AC-DEPLOY-016 store-unavailable simulations, etc. — still wins: its
``keyring.set_keyring`` call runs after this autouse default and replaces the
in-memory backend for that test. This fixture then restores the real backend
afterwards, so nothing leaks between tests.

An in-memory (rather than a null) backend is chosen because it round-trips
``set``/``get``: whichever backend is active when a seed-and-read test runs, the
seeded key is readable. Reads for keys that were never seeded return ``None``,
exactly as the previous real store did for an absent item — with no prompt.
"""

from __future__ import annotations

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

from server.deploy import keystore


class _InMemoryKeyring(KeyringBackend):
    """Deterministic in-memory keyring backend — never touches the real OS store."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self._store[(service, username)]
        except KeyError as error:
            raise PasswordDeleteError("not found") from error


@pytest.fixture(autouse=True)
def _neutralize_os_keyring():
    """Autouse — pin a fresh in-memory keyring for EVERY test so none touches the
    real OS Keychain.

    A per-test fixture that installs its own backend overrides this default (its
    ``set_keyring`` runs after), and the real backend captured here is restored
    on teardown. Session-only keys are cleared afterwards so the module-default
    ``SessionKeyStore`` never leaks across tests.
    """
    original = keyring.get_keyring()
    keyring.set_keyring(_InMemoryKeyring())
    try:
        yield
    finally:
        keyring.set_keyring(original)
        keystore.clear_session_keys()
