"""Shared lupa (Lua 5.4) mock environment for the grandMA3 responder tests.

Loads the REAL plugin file ``console/lua/copilot_responder.lua`` into an
embedded Lua 5.4 runtime with the MA3 API surface mocked (``Cmd``, ``Printf``,
``SendOSCMessage``, ``UserVars``/``GetVar``, ``Root()``/``DataPool()`` object
tree). Only the console API is simulated — the plugin logic under test is the
production artifact byte-for-byte.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lupa.lua54 as lua54

RESPONDER_PATH = Path(__file__).resolve().parents[2] / "console" / "lua" / "copilot_responder.lua"

# Mocked MA3 Lua API surface + capture tables.
MOCK_ENV_LUA = r"""
__SENT = {}
function SendOSCMessage(slot, a, b)
    table.insert(__SENT, { slot = slot, a = a, b = b })
end

__CMD_LOG = {}
__CMD_RESULT = "OK"
__CMD_RAISE = false
function Cmd(line)
    table.insert(__CMD_LOG, line)
    if __CMD_RAISE then error("mock cmd failure") end
    return __CMD_RESULT
end

__PRINTED = {}
function Printf(...)
    local parts = {}
    for _, v in ipairs({ ... }) do parts[#parts + 1] = tostring(v) end
    table.insert(__PRINTED, table.concat(parts, " "))
end

__USER_VARS = {}
function UserVars() return __USER_VARS end
function GetVar(store, name) return store[name] end
function SetVar(store, name, value) store[name] = value end

-- Mock object-tree node: mimics an MA3 handle (name property + Children/
-- Count/Ptr/GetClass methods).
function __NODE(name, class, children)
    local n = {}
    n.name = name
    n._class = class
    n._children = children or {}
    function n:Children() return self._children end
    function n:Count() return #self._children end
    function n:Ptr(i) return self._children[i] end
    function n:GetClass() return self._class end
    return n
end
"""

DEFAULT_TREE_LUA = r"""
local node = __NODE
__DATAPOOL = node("Default", "DataPool", {
    node("Sequences", "Pool", {
        node("Sequence 1", "Sequence"),
        node("Sequence 2", "Sequence"),
        node("Sequence 3", "Sequence"),
    }),
    node("Groups", "Pool", {
        node("Vocals", "Group"),
    }),
})
function DataPool() return __DATAPOOL end
__ROOT = node("Root", "Root", {
    node("ShowData", "ShowData", {
        node("DataPools", "Pool", { __DATAPOOL }),
    }),
})
function Root() return __ROOT end
"""


@dataclass(frozen=True)
class SentMessage:
    """One captured OSC send from the mocked console side."""

    slot: int
    address: str
    payload: str


class ResponderHarness:
    """One loaded responder instance inside an embedded Lua 5.4 runtime."""

    def __init__(self, extra_env: str = ""):
        self.lua = lua54.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCK_ENV_LUA)
        self.lua.execute(DEFAULT_TREE_LUA)
        if extra_env:
            self.lua.execute(extra_env)
        self.lua.globals()["COPILOT_TEST_EXPORT"] = self.lua.table()
        source = RESPONDER_PATH.read_text(encoding="utf-8")
        self.main = self.lua.execute(source)
        self.module = self.lua.globals()["COPILOT_TEST_EXPORT"]["module"]

    @property
    def config(self):
        return self.module["CONFIG"]

    def sent(self) -> list[SentMessage]:
        """Captured sends, normalized across packed/args SendOSCMessage forms."""
        out: list[SentMessage] = []
        table = self.lua.globals()["__SENT"]
        for index in range(1, self.lua.eval("#__SENT") + 1):
            item = table[index]
            if item["b"] is not None:  # args variant: (slot, address, payload)
                out.append(SentMessage(item["slot"], item["a"], item["b"]))
            else:  # packed variant: (slot, "addr,s,payload")
                packed = item["a"]
                address, typetag, payload = packed.split(",", 2)
                assert typetag == "s", f"unexpected typetag in packed form: {packed!r}"
                out.append(SentMessage(item["slot"], address, payload))
        return out

    def raw_packed(self) -> list[str]:
        """Raw packed strings (packed variant only) for wire-safety assertions."""
        table = self.lua.globals()["__SENT"]
        return [
            table[i]["a"] for i in range(1, self.lua.eval("#__SENT") + 1) if table[i]["b"] is None
        ]

    def cmd_log(self) -> list[str]:
        table = self.lua.globals()["__CMD_LOG"]
        return [table[i] for i in range(1, self.lua.eval("#__CMD_LOG") + 1)]
