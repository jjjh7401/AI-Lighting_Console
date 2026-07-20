"""Responder provisioning REST API (M4 — REQ-DEPLOY-010/011, AC-DEPLOY-006/007).

Two endpoints let the packaged UI install the bundled CopilotResponder plugin
into the M1-configured onPC plugin-import directory and read the onPC-load guide:

    GET  /api/provision/responder   install status + guide (import dir + port)
    POST /api/provision/responder   copy the bundled plugin into the import dir

Safety boundary (this module is deliberately narrow):

* **No OSC-send surface (AC-DEPLOY-014 ③ / SAFETY-1 / REQ-DEPLOY-024).** This module
  imports ONLY the M1 settings seam (to resolve the import dir + receive port) and
  the FILESYSTEM-ONLY provisioning layer. It never touches a socket, an OSC module,
  or the safety gate. A source scan in ``test_web_provision_api.py`` enforces this.
* **File copy is off-gate; the ``Import Plugin`` console send is NOT.** Provisioning
  here only copies files. The one console command the deploy path may issue
  (``Import Plugin``) transits the single safety gate + audit (REQ-DEPLOY-011a) and
  lives in the safety package — never here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException

# FILESYSTEM-ONLY provisioning layer — the only "install" path. No OSC imports.
from server.deploy.provisioning import (
    RESPONDER_ASSETS,
    ProvisioningError,
    install_responder,
    responder_guide,
    responder_status,
)

# M1 non-sensitive settings seam (config files) — resolves the import dir + the
# feedback receive port. NOT the console-send surface.
from server.deploy.settings import resolve_effective_settings

# Human-friendly Korean surface for an install failure (REQ-DEPLOY-020 error-UX
# lineage — no raw OS error string is surfaced as the primary message).
_INSTALL_FAILED_MESSAGE = (
    "responder 플러그인 설치에 실패했습니다 — "
    "플러그인 임포트 디렉터리 경로와 쓰기 권한을 확인해 주세요."
)


@dataclass
class ProvisionDeps:
    """Everything the provisioning API consumes — composed by serve.py / tests.

    ``settings_path`` / ``seed_path`` are the M1 config locations used to resolve
    the effective plugin import directory + feedback receive port.
    """

    settings_path: Path | None = None
    seed_path: Path | None = None


# @MX:ANCHOR: [AUTO] the responder-provisioning REST surface — the ONLY deploy-shell
#   entry point that installs the bundled responder plugin. High fan_in (create_app
#   wiring, serve.py composition at M6, tests).
# @MX:REASON: AC-DEPLOY-014 ③ / REQ-DEPLOY-023-024 top invariant — this surface MUST
#   reach only the M1 settings seam + the filesystem-only provisioning layer and
#   NEVER the OSC-send path. A new endpoint here that imports a raw socket / OSC
#   module / the safety gate would open an ungated console-command path (a safety
#   regression); the source-scan guard in test_web_provision_api.py enforces it.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def build_provision_router(deps: ProvisionDeps) -> APIRouter:
    """Build the responder-provisioning REST router around one dependency set."""
    router = APIRouter()

    def _resolve() -> tuple[str, int]:
        settings = resolve_effective_settings(
            user_path=deps.settings_path, seed_path=deps.seed_path
        )
        return settings.plugin_import_dir, settings.receive_port

    @router.get("/api/provision/responder")
    def get_status() -> dict:
        import_dir, receive_port = _resolve()
        installed = responder_status(import_dir)
        return {
            "import_dir": import_dir,
            "assets": list(RESPONDER_ASSETS),
            "installed": installed,
            "installed_all": all(installed.values()),
            "guide": responder_guide(receive_port),
        }

    @router.post("/api/provision/responder")
    def install() -> dict:
        import_dir, receive_port = _resolve()
        try:
            result = install_responder(import_dir)
        except (ProvisioningError, OSError) as error:
            raise HTTPException(
                status_code=500,
                detail={"error": "install_failed", "message": _INSTALL_FAILED_MESSAGE},
            ) from error
        return {
            "ok": True,
            "installed": list(result.installed),
            "import_dir": result.import_dir,
            "guide": responder_guide(receive_port),
        }

    return router
