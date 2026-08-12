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

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from server.resources import resource_base

# The responder plugin asset filenames bundled in the deploy artifact
# (REQ-DEPLOY-009). onPC needs the native import XML together with the Lua
# component, so both are installed as a pair.
RESPONDER_ASSETS: tuple[str, ...] = ("copilot_responder.xml", "copilot_responder.lua")

# The per-show OSC connectivity template pair (2026-08-12 recipe, captured by
# reading a live, working onPC show's In & Out > OSC screen and exporting both
# rows via onPC's native OSCData Export). onPC does NOT carry OSC config
# forward to a new show — every fresh show starts with only a default row 1
# and none of the fields this project depends on (prefix, destination, the
# dedicated send-only reply row). Importing these two files via onPC's native
# In & Out > OSC > Import is what makes a brand-new show reachable without
# re-discovering the recipe by hand:
#   row1 = RECEIVE — prefix "copilot" on the console-command port, native
#     "Receive Command" execs an incoming /copilot/cmd payload as a command
#     line (this is how server.bridge.osc.OscBridge.send_command reaches the
#     console — no plugin round trip needed for the send direction).
#   row2 = SEND-only — the responder's reply channel (CONFIG.osc_slot in
#     copilot_responder.lua points at this row's index).
OSC_TEMPLATE_ASSETS: tuple[str, ...] = (
    "copilot_osc_row1_receive.xml",
    "copilot_osc_row2_send.xml",
)


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


def bundled_osc_template_dir() -> Path:
    """Resolve the bundled OSC-connectivity-template directory (dev + frozen).

    Mirrors :func:`bundled_responder_dir` but for the per-show OSC row
    templates: dev checkout resolves to ``<repo>/console/osc``; a frozen
    PyInstaller bundle resolves to ``sys._MEIPASS/console/osc``.
    """
    return resource_base() / "console" / "osc"


# The single CONFIG assignment in the bundled Lua. Anchored to line start (in
# MULTILINE) plus the trailing comma so it cannot match `CONFIG.osc_slot`, which
# is READ three times in the send path — a broader pattern would corrupt them.
_OSC_SLOT_ANCHOR = re.compile(r"^(?P<indent>[ \t]*)osc_slot = \d+,", re.MULTILINE)


def _render_lua(source_text: str, osc_slot: int) -> str:
    """Substitute the site's OSC reply row into the bundled responder source.

    The console's OSC row is per-site (row 1 is a broadcast destination on at
    least one live rig), so the operator used to hand-edit the installed file —
    and a re-install silently copied the bundle default back over it, with no
    backup and no signal beyond a console that stopped replying.

    A miss is raised, never ignored: if the Lua is refactored so the anchor no
    longer matches, installing the DEFAULT slot while the operator configured
    another one reproduces exactly that silent failure. Failing the install is
    the honest outcome.
    """
    rendered, count = _OSC_SLOT_ANCHOR.subn(
        lambda m: f"{m.group('indent')}osc_slot = {osc_slot},", source_text
    )
    if count != 1:
        raise ProvisioningError(
            "responder Lua has no unique `osc_slot = <n>,` assignment to render "
            f"(matched {count} times) — refusing to install a plugin whose reply "
            "row may not be the configured one"
        )
    return rendered


def read_installed_osc_slot(import_dir: Path | str) -> int | None:
    """The OSC reply row currently written in the INSTALLED responder Lua.

    Returns ``None`` when nothing is installed, when the file cannot be read,
    or when it carries no readable ``osc_slot = <n>,`` assignment. ``None``
    means **unknown**, never "the default" — a caller that reported the default
    for an unreadable file would tell the operator the install is in agreement
    with their settings when nobody knows what the file says.

    This exists so a caller can compare against the value it is ABOUT to write
    and stop, rather than discover the disagreement afterwards by way of a
    console that no longer replies.
    """
    lua = Path(import_dir).expanduser() / "copilot_responder.lua"
    try:
        text = lua.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _OSC_SLOT_ANCHOR.search(text)
    if match is None:
        return None
    digits = re.search(r"\d+", match.group(0))
    return int(digits.group(0)) if digits else None


def install_responder(
    import_dir: Path | str,
    *,
    source_dir: Path | str | None = None,
    osc_slot: int | None = None,
) -> InstallResult:
    """Copy the bundled responder assets into ``import_dir`` (filesystem only).

    Creates ``import_dir`` (and parents) if absent and overwrites existing files,
    so a re-install is idempotent. ``source_dir`` defaults to the bundled asset
    directory; an explicit value lets callers install from a staged location.

    ``osc_slot`` renders the site's OSC reply row into the Lua as it is copied,
    which is what makes that idempotence safe: without it, re-provisioning
    reverts the operator's hand-edited row. ``None`` copies verbatim, so callers
    that do not care keep byte-identical behaviour. Only the Lua is rendered —
    the XML carries no runtime config.

    Raises :class:`ProvisioningError` if a bundled asset is missing, or if the
    Lua cannot be rendered (see :func:`_render_lua`). NO OSC / console-send
    happens here (AC-DEPLOY-014 ③) — substitution is still pure filesystem.
    """
    source = Path(source_dir) if source_dir is not None else bundled_responder_dir()
    dest = Path(import_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    for name in RESPONDER_ASSETS:
        src = source / name
        if not src.is_file():
            raise ProvisioningError(f"bundled responder asset missing: {src}")
        if osc_slot is not None and name.endswith(".lua"):
            rendered = _render_lua(src.read_text(encoding="utf-8"), osc_slot)
            (dest / name).write_text(rendered, encoding="utf-8")
        else:
            shutil.copyfile(src, dest / name)
        installed.append(name)
    return InstallResult(installed=tuple(installed), import_dir=str(dest))


# Matches the single ``Port="<digits>"`` attribute on the template's one
# <OSCData .../> element. Anchored the same way as ``_OSC_SLOT_ANCHOR``: a
# render must hit exactly one attribute, never zero (silently shipping the
# bundled port) and never more than one (a template edit gained a second
# Port attribute and the substitution now touches the wrong one).
_OSC_PORT_ANCHOR = re.compile(r'Port="\d+"')


def _render_osc_port(source_text: str, port: int) -> str:
    """Substitute the site's port into a bundled OSCData template.

    Row 1's port must track ``console_port`` (server.bridge.osc.OscBridge's
    send target) and row 2's must track ``receive_port`` (this app's bound
    feedback listener) — both configurable per site, so both must render
    the same way ``osc_slot`` renders into the Lua (see ``_render_lua``).
    """
    rendered, count = _OSC_PORT_ANCHOR.subn(f'Port="{port}"', source_text)
    if count != 1:
        raise ProvisioningError(
            'OSC template has no unique `Port="<n>"` attribute to render '
            f"(matched {count} times) — refusing to install a row that may "
            "not carry the configured port"
        )
    return rendered


def install_osc_templates(
    osc_import_dir: Path | str,
    *,
    source_dir: Path | str | None = None,
    console_port: int | None = None,
    receive_port: int | None = None,
) -> InstallResult:
    """Copy the bundled OSC row templates into ``osc_import_dir`` (filesystem only).

    Mirrors :func:`install_responder`: creates the directory if absent,
    overwrites existing files (idempotent re-install), and renders the
    site's ports into the templates as they are copied — row 1's from
    ``console_port``, row 2's from ``receive_port``. Leaving either ``None``
    copies that template verbatim, keeping the bundled default port.

    This does NOT configure onPC — it only stages the two files where onPC's
    native In & Out > OSC > Import can read them. The operator (or a
    computer-use driven setup pass) still performs one Import per new show;
    see :func:`osc_bootstrap_guide` for the exact steps. NO OSC / console-send
    happens here (AC-DEPLOY-014 ③) — this stays pure filesystem, same as
    :func:`install_responder`.
    """
    source = Path(source_dir) if source_dir is not None else bundled_osc_template_dir()
    dest = Path(osc_import_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    ports = {
        "copilot_osc_row1_receive.xml": console_port,
        "copilot_osc_row2_send.xml": receive_port,
    }
    installed: list[str] = []
    for name in OSC_TEMPLATE_ASSETS:
        src = source / name
        if not src.is_file():
            raise ProvisioningError(f"bundled OSC template missing: {src}")
        port = ports.get(name)
        if port is not None:
            rendered = _render_osc_port(src.read_text(encoding="utf-8"), port)
            (dest / name).write_text(rendered, encoding="utf-8")
        else:
            shutil.copyfile(src, dest / name)
        installed.append(name)
    return InstallResult(installed=tuple(installed), import_dir=str(dest))


def osc_template_status(osc_import_dir: Path | str) -> dict[str, bool]:
    """Per-asset "is it staged?" booleans for the configured OSC import directory."""
    dest = Path(osc_import_dir).expanduser()
    return {name: (dest / name).is_file() for name in OSC_TEMPLATE_ASSETS}


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


def osc_bootstrap_guide(console_port: int, receive_port: int) -> dict:
    """Per-show OSC bootstrap steps (2026-08-12 recipe — see ``OSC_TEMPLATE_ASSETS``).

    A brand-new onPC show carries NO OSC config forward — Interface binding,
    Enable Output/Input, and every OSCData row reset to onPC's own defaults.
    Without this one-time-per-show pass the responder plugin can be installed
    and imported correctly and the console will still never reply: the
    verified failure mode is an OSCData row bound to the machine's Wi-Fi/
    Ethernet interface (``en0``) instead of loopback, which silently drops
    127.0.0.1 traffic even after every port number is right.

    ``install_osc_templates`` stages the two row files so steps 3-4 are an
    Import + file pick rather than re-typing every field; the interface and
    enable toggles have no export/import path in onPC 2.4.2 and must still be
    set by hand (or by a computer-use pass driving the same screen).
    """
    return {
        "console_port": console_port,
        "receive_port": receive_port,
        "steps": [
            "Menu > Settings > In & Out > OSC 화면을 연다.",
            (
                "Interface를 lo0 (127.0.0.1)로 설정한다 — "
                "en0/Wi-Fi로 두면 127.0.0.1 트래픽이 조용히 사라진다."
            ),
            (
                f'OSC 1 행(copilot_osc_row1_receive.xml, prefix "copilot")을 '
                f"Import한다 — 콘솔 명령 수신 포트({console_port})."
            ),
            (
                f"OSC 2 행(copilot_osc_row2_send.xml)을 Import한다 — "
                f"이 앱의 피드백 수신 포트({receive_port})."
            ),
            "Enable Output과 Enable Input을 둘 다 켠다(노란색으로 표시되면 켜진 상태).",
            'Plugin "CopilotResponder" "ping <id>"를 콘솔 명령줄에서 한 번 실행해 왕복을 확인한다.',
        ],
    }
