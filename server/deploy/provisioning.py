"""CopilotResponder provisioning (M4 — REQ-DEPLOY-009/010/011, AC-DEPLOY-006/007).

The packaged app bundles the CopilotResponder Lua plugin (``copilot_responder.lua``
+ its native import XML) and installs it into the operator's onPC plugin-import
directory (REQ-DEPLOY-005 setting). This layer is FILESYSTEM-ONLY: it copies the
bundled files and returns an onPC-load guide; it never opens a socket, imports an
OSC module, or reaches the safety gate.

Boundary (AC-DEPLOY-014 ③ / SAFETY-1 / REQ-DEPLOY-024): only the file copy is
outside the safety gate. The ONE console command provisioning MAY issue as part
of the working "deploy verb → file+Import" mechanism — ``Import Plugin`` — is
issued by the gate-owned console link behind the single safety gate's deploy
surface (REQ-MVP-029) and is audit-logged 1:1 (REQ-DEPLOY-011a). That send is
deliberately NOT in this module (see the gate-transit regression guard,
``test_responder_import_gate.py``, AC-DEPLOY-017).

Frozen-bundle note (FEAS-1): :func:`bundled_responder_dir` resolves the assets in
BOTH a dev checkout (``<repo>/console/lua``) and a frozen PyInstaller bundle
(``sys._MEIPASS/console/lua``). ⚠️ M6 OBLIGATION: the PyInstaller onedir bundle
spec MUST ship these assets via ``--add-data 'console/lua:console/lua'`` (or the
onedir ``_internal`` equivalent) so the resolver finds them in the frozen app.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from server.resources import resource_base

# The responder plugin asset filenames bundled in the deploy artifact
# (REQ-DEPLOY-009). onPC needs the native import XML together with the Lua
# component, so both are installed as a pair.
RESPONDER_ASSETS: tuple[str, ...] = ("copilot_responder.xml", "copilot_responder.lua")


class ProvisioningError(RuntimeError):
    """Raised when a bundled responder asset is missing or cannot be installed."""


@dataclass(frozen=True)
class InstallResult:
    """The outcome of one :func:`install_responder` call."""

    installed: tuple[str, ...]  # asset filenames copied into the import dir
    import_dir: str  # the absolute import directory the files landed in


def bundled_responder_dir() -> Path:
    """Resolve the bundled responder-asset directory (dev + frozen).

    Dev checkout resolves to ``<repo>/console/lua``; a frozen PyInstaller bundle
    resolves to ``sys._MEIPASS/console/lua`` (onedir or onefile). Routes through
    the shared :func:`server.resources.resource_base` resolver (M6 generalisation
    of this module's original ``sys._MEIPASS`` pattern) so every frozen-sensitive
    path shares one resolver. See the module docstring for the ``--add-data``
    obligation.
    """
    return resource_base() / "console" / "lua"


def install_responder(
    import_dir: Path | str,
    *,
    source_dir: Path | str | None = None,
) -> InstallResult:
    """Copy the bundled responder assets into ``import_dir`` (filesystem only).

    Creates ``import_dir`` (and parents) if absent and overwrites existing files,
    so a re-install is idempotent. ``source_dir`` defaults to the bundled asset
    directory; an explicit value lets callers install from a staged location.

    Raises :class:`ProvisioningError` if a bundled asset is missing. NO OSC /
    console-send happens here (AC-DEPLOY-014 ③).
    """
    source = Path(source_dir) if source_dir is not None else bundled_responder_dir()
    dest = Path(import_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    for name in RESPONDER_ASSETS:
        src = source / name
        if not src.is_file():
            raise ProvisioningError(f"bundled responder asset missing: {src}")
        shutil.copyfile(src, dest / name)
        installed.append(name)
    return InstallResult(installed=tuple(installed), import_dir=str(dest))


def responder_status(import_dir: Path | str) -> dict[str, bool]:
    """Per-asset "is it installed?" booleans for the configured import directory."""
    dest = Path(import_dir).expanduser()
    return {name: (dest / name).is_file() for name in RESPONDER_ASSETS}


def responder_guide(receive_port: int) -> dict:
    """onPC-load steps + the OSC-output-port instruction (REQ-DEPLOY-011).

    The steps are the human-facing surface the guide UI renders; ``receive_port``
    is the app's feedback receive port the operator must point onPC's OSC output
    at (REQ-DEPLOY-011 / AC-DEPLOY-007). User-facing text follows the app's
    Korean UI convention (matching SettingsPanel / OnboardingBanner).
    """
    return {
        "receive_port": receive_port,
        "steps": [
            "설치된 플러그인 파일이 onPC 플러그인 라이브러리 폴더에 있는지 확인합니다.",
            "onPC의 Plugins 풀 창에서 CopilotResponder 플러그인을 임포트(로드)합니다.",
            "임포트한 플러그인을 실행해 responder를 활성화합니다.",
            f"onPC의 OSC 출력(Output)을 이 앱의 피드백 수신 포트({receive_port})로 설정합니다.",
        ],
    }
