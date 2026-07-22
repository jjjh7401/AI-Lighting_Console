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
    read_installed_osc_slot,
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

# Rendering the OSC reply row from settings keeps a re-install from reverting
# site config — but only when the setting is the right one. The shipped default
# is row 1 while at least one live rig replies on row 2, so installing before
# setting the row silently re-breaks the link: the console keeps logging the
# request while the app reports it offline. Refuse instead, and name both
# numbers so the operator can tell which way to resolve it.
_OSC_SLOT_CONFLICT_MESSAGE = (
    "설치를 중단했습니다 — 설정의 OSC 응답 행과 이미 설치된 파일의 값이 다릅니다. "
    "설정 값으로 덮어쓰면 콘솔이 회신하지 않을 수 있습니다. "
    "설정을 설치본에 맞추거나, 설정 값이 맞다면 덮어쓰기를 확인해 주세요."
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

    def _resolve() -> tuple[str, int, int]:
        settings = resolve_effective_settings(
            user_path=deps.settings_path, seed_path=deps.seed_path
        )
        return settings.plugin_import_dir, settings.receive_port, settings.osc_slot

    def _slot_conflict(import_dir: str, configured: int) -> tuple[bool, int | None]:
        """``(conflict?, installed slot)`` — the slot is None when unreadable.

        Only an ESTABLISHED agreement clears the install: an unreadable slot on
        an existing file is a conflict too, because that file is the one case
        where the operator most needs to look before it is replaced.

        Returned as a pair rather than "a slot, or False": ``bool`` is an ``int``
        subclass, so a sentinel-in-the-value-space encoding invites exactly the
        confusion ``_require_port`` already guards against in the settings layer.
        """
        if not (Path(import_dir).expanduser() / "copilot_responder.lua").is_file():
            return False, None  # first install — nothing to disagree with
        installed = read_installed_osc_slot(import_dir)
        return installed != configured, installed

    @router.get("/api/provision/responder")
    def get_status() -> dict:
        import_dir, receive_port, osc_slot = _resolve()
        installed = responder_status(import_dir)
        mismatch, installed_slot = _slot_conflict(import_dir, osc_slot)
        return {
            "import_dir": import_dir,
            "assets": list(RESPONDER_ASSETS),
            "installed": installed,
            "installed_all": all(installed.values()),
            "guide": responder_guide(receive_port),
            "configured_osc_slot": osc_slot,
            "installed_osc_slot": installed_slot,
            "osc_slot_mismatch": mismatch,
        }

    @router.post("/api/provision/responder")
    def install(confirm_osc_slot: bool = False) -> dict:
        import_dir, receive_port, osc_slot = _resolve()

        mismatch, installed_slot = _slot_conflict(import_dir, osc_slot)
        if mismatch and not confirm_osc_slot:
            # 409, not 400: the request is well-formed and the server state is
            # the reason it cannot proceed. Nothing is written on this path.
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "osc_slot_mismatch",
                    "message": _OSC_SLOT_CONFLICT_MESSAGE,
                    "configured_osc_slot": osc_slot,
                    "installed_osc_slot": installed_slot,
                },
            )
        try:
            # Rendered, not copied verbatim: a plain copy reverts the site's
            # OSC reply row on every re-install (live 2026-07-22).
            result = install_responder(import_dir, osc_slot=osc_slot)
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
