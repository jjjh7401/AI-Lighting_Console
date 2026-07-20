"""In-app settings + secure-key REST API (M3 — REQ-DEPLOY-005/007, AC-DEPLOY-003).

The terminal-free replacement for CLI args + manual env injection: four endpoints
let the packaged UI read/write the M1 non-sensitive settings layer and drive the
M2 secure keystore, so an operator configures keys, OSC ports, and the plugin
import directory entirely in-app.

    GET    /api/settings          effective non-sensitive settings + per-provider
                                  "key set: true/false" status (NEVER key values)
    POST   /api/settings          validate + persist non-sensitive settings (M1)
    POST   /api/keys              write a key to the OS store (M2), inject to env
    DELETE /api/keys/{provider}   remove a key from the store + session

Safety invariants (this module is deliberately narrow):

* **No OSC-send surface (AC-DEPLOY-014 ③ / SAFETY-1).** This module imports ONLY
  the M1 settings seam and the M2 keystore seam — never the console-send surface,
  a raw socket, or the safety gate. The settings/key path can touch config files
  and the OS credential store; it can NEVER emit an OSC command. A source scan in
  ``test_web_settings_api.py`` enforces this.
* **Keys are write-only from the client (AC-DEPLOY-004).** ``GET`` returns only a
  per-provider boolean; a key value is never serialised into any response.
* **No plaintext-disk fallback (REQ-DEPLOY-006a / AC-DEPLOY-016).** When the OS
  store is unavailable, ``POST /api/keys`` returns an explicit 503 offering the
  session-only path — it never writes the key to a file.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException

# M2 secure keystore seam (OS credential store + env injection) — the ONLY path a
# credential takes into the backend process env. No OSC/console imports here.
from server.deploy.keystore import (
    KeystoreError,
    KeystoreUnavailableError,
    SessionKeyStore,
    delete_api_key,
    get_api_key,
    inject_key_for_provider,
    set_api_key,
    set_session_api_key,
)

# M1 non-sensitive settings seam (config files) — NOT the console-send surface.
from server.deploy.settings import (
    SettingsError,
    resolve_effective_settings,
    save_user_settings,
)
from server.llm.config import SUPPORTED_PROVIDERS

# Human-friendly Korean surface for the store-unavailable case (REQ-DEPLOY-020
# error-UX lineage — no raw SDK/store error string is exposed to the client).
_KEYSTORE_UNAVAILABLE_MESSAGE = (
    "OS 자격 증명 저장소를 사용할 수 없습니다 (잠금/거부/미가용). "
    "키는 디스크에 저장되지 않았습니다 — 이번 세션에만 사용하려면 세션 전용으로 저장하세요."
)


@dataclass
class SettingsDeps:
    """Everything the settings API consumes — composed by serve.py / tests.

    ``settings_path`` / ``seed_path`` are the M1 config locations; ``session`` is
    the M2 in-memory fallback store; ``environ`` is the injection target (defaults
    to ``os.environ`` when ``None`` — tests pass a throwaway dict for isolation).
    """

    settings_path: Path | None = None
    seed_path: Path | None = None
    session: SessionKeyStore | None = None
    environ: MutableMapping[str, str] | None = None
    providers: tuple[str, ...] = SUPPORTED_PROVIDERS


def _provider_key_status(deps: SettingsDeps) -> tuple[dict[str, bool], bool]:
    """Per-provider "is a key set?" booleans + overall keystore availability.

    Reads the key transiently to test presence but NEVER returns the value. A
    store failure for any provider flips ``keystore_available`` to ``False`` while
    still honouring any session-only key already held in memory.
    """
    keys: dict[str, bool] = {}
    keystore_available = True
    for provider in deps.providers:
        try:
            keys[provider] = get_api_key(provider, session=deps.session) is not None
        except KeystoreUnavailableError:
            keystore_available = False
            session = deps.session
            keys[provider] = session is not None and session.get(provider) is not None
    return keys, keystore_available


def build_settings_router(deps: SettingsDeps) -> APIRouter:
    """Build the settings/key REST router around one composed dependency set."""
    router = APIRouter()

    @router.get("/api/settings")
    def get_settings() -> dict:
        settings = resolve_effective_settings(
            user_path=deps.settings_path, seed_path=deps.seed_path
        )
        keys, keystore_available = _provider_key_status(deps)
        return {
            "settings": asdict(settings),
            "providers": list(deps.providers),
            "keys": keys,
            "keystore_available": keystore_available,
        }

    @router.post("/api/settings")
    def post_settings(payload: dict) -> dict:
        # Reuse the M1 precedence resolver as the validation SSOT: it accepts only
        # the recognised non-sensitive keys (a smuggled credential key is ignored,
        # never persisted) and validates each field's type/range.
        try:
            settings = resolve_effective_settings(
                user_path=deps.settings_path,
                seed_path=deps.seed_path,
                overrides=payload,
            )
        except SettingsError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        save_user_settings(settings, deps.settings_path)
        return {"ok": True, "settings": asdict(settings)}

    @router.post("/api/keys")
    def post_key(payload: dict) -> dict:
        provider = payload.get("provider")
        key = payload.get("key")
        session_only = bool(payload.get("session_only", False))
        try:
            if session_only:
                set_session_api_key(provider, key, session=deps.session)
                mode = "session"
            else:
                set_api_key(provider, key)
                mode = "keystore"
        except KeystoreUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "keystore_unavailable",
                    "provider": provider,
                    "message": _KEYSTORE_UNAVAILABLE_MESSAGE,
                    "session_fallback": True,
                },
            ) from error
        except KeystoreError as error:
            # Bad provider / empty key — a client-side validation error.
            raise HTTPException(status_code=400, detail=str(error)) from error

        # REQ-DEPLOY-007: make the freshly-set key reachable by the provider client
        # via process env (minimal wiring; full launcher rebuild is M6).
        injected = inject_key_for_provider(provider, environ=deps.environ, session=deps.session)
        return {"ok": True, "mode": mode, "injected": injected}

    @router.delete("/api/keys/{provider}")
    def delete_key(provider: str) -> dict:
        try:
            delete_api_key(provider, session=deps.session)
        except KeystoreUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "keystore_unavailable",
                    "provider": provider,
                    "message": _KEYSTORE_UNAVAILABLE_MESSAGE,
                    "session_fallback": False,
                },
            ) from error
        except KeystoreError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"ok": True}

    return router
