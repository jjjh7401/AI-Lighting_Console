"""CONFIG.max_payload must respect the MA3 command-line length limit.

Live-measured on onPC 2.4.2 (2026-07-24, SPEC-COPILOT-DASHUI-001 M6 root-cause
probe): the responder's working reply transport is the ``cmd_keyword`` variant
(``Cmd('SendOSC <slot> "<address>,s,<payload>"')``), and the MA3 command line
silently drops commands past ~2048 bytes — ``Cmd()`` still reports success, so
an oversize snapshot reply simply never leaves the console (payload sweep:
2000 bytes delivered, 2100 dropped). The reproducer was the DataPool/Macros
snapshot: 27 leftover probe macros with long names built a ~4000-byte payload
under the old ``max_payload = 4000`` and every reply vanished.

This test pins the budget arithmetic at the SOURCE level (no lupa needed):
encoded payload + the longest wrapper the responder emits must fit 2048.
"""

import re
from pathlib import Path

LUA_SOURCE = Path(__file__).resolve().parents[2] / "console" / "lua" / "copilot_responder.lua"

MA3_COMMAND_LINE_LIMIT = 2048


def _config_value(name: str) -> str:
    text = LUA_SOURCE.read_text(encoding="utf-8")
    match = re.search(rf"^\s*{name}\s*=\s*([^,\n]+),", text, re.MULTILINE)
    assert match, f"CONFIG.{name} not found in {LUA_SOURCE}"
    return match.group(1).strip()

def test_max_payload_fits_the_ma3_command_line_limit():
    max_payload = int(_config_value("max_payload"))
    state_address = _config_value("state_address").strip('"')
    feedback_address = _config_value("feedback_address").strip('"')
    longest_address = max(state_address, feedback_address, key=len)
    # Cmd('SendOSC <slot> "<address>,s,<payload>"') — worst-case wrapper.
    wrapper = len('SendOSC 99 "') + len(longest_address) + len(",s,") + len('"')
    assert max_payload + wrapper <= MA3_COMMAND_LINE_LIMIT, (
        f"max_payload={max_payload} + wrapper={wrapper} exceeds the live-measured "
        f"MA3 command-line limit ({MA3_COMMAND_LINE_LIMIT}); replies would be "
        "silently dropped (Cmd() does not raise on rejection)"
    )

def test_max_payload_is_not_zero_or_negative():
    assert int(_config_value("max_payload")) > 0
