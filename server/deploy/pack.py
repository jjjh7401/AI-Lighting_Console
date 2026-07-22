"""Native grandMA3 plugin-XML packing for the file+Import deploy path (M7 fix).

This module emits the self-contained form grandMA3 itself exports: a
`<UserPlugin>` carrying the Lua source as Base64 blocks
(`<UserPlugin><ComponentLua><FileContent><Block Base64="…"/>…`). That form is
live-proven for this path — every plugin the app has deployed and run went out
this way (`deployed` events in ``server/audit_logs``).

The form it replaced — a `<ComponentLua FileName="…">` pointing at a sibling
.lua — imported with an empty component and ran nothing when tried in THIS
path's `<UserPlugin>` shape (verified live 2026-07-19).

Do NOT generalise that to "a FileName reference cannot work". The bundled
responder wrapper (``console/lua/copilot_responder.xml``) is a
`<GMA3 DataVersion="2.4.2.0"><Plugin>` with `FileName=`, and it demonstrably
does deliver its source: on 2026-07-22 the showfile was found to contain the
responder's site-edited body — an `osc_slot = 2` and a SITE comment that exist
only in the INSTALLED .lua, never in the repo copy. The two wrappers differ in
root element (`Plugin` vs `UserPlugin`), DataVersion and GUIDs as well as in how
the source is carried; which of those differences is the operative one is
UNVERIFIED, and neither observation has been reproduced. Also unverified:
whether such a wrapper embeds at import time or keeps a link and embeds on save.

The engineering conclusion is unchanged — this path uses the Base64 form because
that is the one it has proven. The narrowing matters only so nobody "fixes" the
responder wrapper on the strength of a claim that was never about it.

Why this replaces the OSC ``deploy`` verb for the production path: the verb
(``server.bridge.protocol.build_deploy_request``) embeds the source in ONE
percent-encoded UDP command line — it truncates past ~2 KB — and relies on a
console-side Lua content setter that does not persist on 2.4.2 (ASSUMPTION-6).
File+Import has neither limit (co-located server + console; a remote console
would need a separate file-transfer channel).

Pure module: no bridge, no I/O, no side effects — safe to import anywhere,
including the REQ-MVP-029 chokepoint module ``server.safety.console``.
"""

from __future__ import annotations

import base64
import re
import uuid
from xml.sax.saxutils import quoteattr

# grandMA3 export DataVersion observed on the target build (onPC 2.4.2.2).
DATA_VERSION = "2.4.2.2"
# Raw source bytes per <Block>, matching grandMA3's own export chunking.
BLOCK_SIZE = 1024

_SLUG = re.compile(r"[^A-Za-z0-9._-]+")
_BLOCK = re.compile(r'<Block Base64="([^"]*)"/>')


def _guid() -> str:
    """A fresh grandMA3-style GUID: 16 space-separated uppercase hex byte pairs."""
    return " ".join(f"{b:02X}" for b in uuid.uuid4().bytes)


def build_plugin_xml(name: str, lua_source: str, *, block_size: int = BLOCK_SIZE) -> str:
    """Return a self-contained grandMA3 plugin XML embedding ``lua_source``.

    ``name`` is the plugin pool name (used verbatim as the ``Plugin "<name>"``
    invocation target). The source is stored as Base64 blocks of ``block_size``
    raw bytes each, exactly as grandMA3's own export does.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("plugin name must be a non-empty string")
    if not isinstance(lua_source, str) or not lua_source:
        raise ValueError("lua source must be a non-empty string")
    raw = lua_source.encode("utf-8")
    blocks = [raw[i : i + block_size] for i in range(0, len(raw), block_size)]
    block_xml = "\n".join(
        f'                <Block Base64="{base64.b64encode(chunk).decode("ascii")}"/>'
        for chunk in blocks
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<GMA3 DataVersion="{DATA_VERSION}">\n'
        f"    <UserPlugin Name={quoteattr(name)} "
        f'Guid="{_guid()}" Version="0.0.0.0">\n'
        f'        <ComponentLua Guid="{_guid()}">\n'
        f'            <FileContent Size="{len(blocks)}">\n'
        f"{block_xml}\n"
        "            </FileContent>\n"
        "        </ComponentLua>\n"
        "    </UserPlugin>\n"
        "</GMA3>\n"
    )


def import_slug(name: str) -> str:
    """A filesystem-safe import filename stem (no extension) for a plugin name.

    grandMA3 ``Import Plugin '<stem>'`` reads ``<stem>.xml`` from the plugins
    library folder, so the on-disk file name is decoupled from the plugin's
    pool ``Name`` (which may contain spaces).
    """
    slug = _SLUG.sub("_", name.strip()).strip("_")
    return slug or "copilot_plugin"


def decode_blocks(xml: str) -> bytes:
    """Decode the Base64 blocks of a packed plugin XML back to raw source bytes.

    Round-trip helper for tests and self-verification.
    """
    return b"".join(base64.b64decode(b) for b in _BLOCK.findall(xml))
