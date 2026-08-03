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
-- Count/Ptr/GetClass/Get/Property* methods). Dense pool: listing position == pool slot.
function __NODE(name, class, children, props, property_order, property_types)
    local n = {}
    n.name = name
    n._class = class
    n._children = children or {}
    n._props = props or {}
    n._property_order = property_order or {}
    n._property_types = property_types or {}
    if #n._property_order == 0 then
        for key in pairs(n._props) do n._property_order[#n._property_order + 1] = key end
        table.sort(n._property_order)
    end
    function n:Children() return self._children end
    function n:Count() return #self._children end
    function n:Ptr(i) return self._children[i] end
    function n:GetClass() return self._class end
    function n:Get(prop)
        if prop == "name" or prop == "Name" then return self.name end
        return self._props[prop]
    end
    function n:PropertyCount() return #self._property_order end
    function n:PropertyName(i) return self._property_order[i] end
    function n:PropertyType(i)
        local prop = self._property_order[i]
        if prop == nil then return nil end
        return self._property_types[prop] or type(self._props[prop])
    end
    return n
end

-- SPARSE (gapped) pool node: objects sit at explicit, non-contiguous slots —
-- what a real pool looks like once the user deletes or hand-numbers objects.
-- The whole point: Children() returns the COMPACTED object list (the gaps are
-- invisible there, as on the console), so a listing position is NOT the pool
-- slot; Ptr(slot) stays slot-addressed and returns nil for a gap.
--   slots      : table keyed by pool slot -> child node
--   index_form : how (or whether) a child exposes its OWN real slot
--                nil       -> no accessor at all (worst case)
--                "Index"   -> child:Index()
--                "index"   -> child.index property
--                "Index0"  -> child:Index(), but 0-BASED (a skewed accessor)
--   ptr_form   : "slot" (default) -> Ptr(n) is the object AT slot n, nil in a
--                gap; "positional" -> Ptr(n) is the n-th LISTED object, i.e.
--                Ptr carries no slot information at all (2.4.2 unverified)
function __SPARSE(name, class, slots, index_form, ptr_form)
    local n = {}
    n.name = name
    n._class = class
    n._slots = slots or {}
    n._order = {}
    for slot in pairs(n._slots) do n._order[#n._order + 1] = slot end
    table.sort(n._order)
    for _, slot in ipairs(n._order) do
        local child = n._slots[slot]
        child._slot = slot
        if index_form == "Index" then
            function child:Index() return self._slot end
        elseif index_form == "Index0" then
            function child:Index() return self._slot - 1 end
        elseif index_form == "index" then
            child.index = slot
        end
    end
    function n:Children()
        local out = {}
        for _, slot in ipairs(self._order) do out[#out + 1] = self._slots[slot] end
        return out
    end
    function n:Count() return #self._order end
    function n:Ptr(i)
        if ptr_form == "positional" then
            local slot = self._order[i]
            return slot and self._slots[slot] or nil
        end
        return self._slots[i]
    end
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


#: Slot layout of the gapped Groups pool below — the live-demo shape that broke
#: the model ("groups 1, 2, 3 exist" -> `Group 2 + 3` -> illegal object).
GAPPED_GROUP_SLOTS = (1, 5, 7)
GAPPED_GROUP_NAMES = ("Vocals", "Drums", "Keys")


def gapped_groups_env(index_form: str | None = None, ptr_form: str | None = None) -> str:
    """Lua that replaces DataPool/Groups with a pool gapped at slots 1, 5, 7.

    Both console-side unknowns (PROTOCOL.md ASSUMPTION-7) are parameters here,
    because the responder's behaviour must be defensible under every
    combination: ``index_form`` selects the child's self-index accessor
    (``None`` = none, ``"Index"``, ``"index"``, ``"Index0"`` = 0-based/skewed)
    and ``ptr_form`` selects whether the parent's ``Ptr(n)`` is slot-addressed
    (default) or merely ``"positional"``.
    """
    form = "nil" if index_form is None else f'"{index_form}"'
    ptr = "nil" if ptr_form is None else f'"{ptr_form}"'
    entries = ",\n        ".join(
        f'[{slot}] = node("{name}", "Group")'
        for slot, name in zip(GAPPED_GROUP_SLOTS, GAPPED_GROUP_NAMES, strict=True)
    )
    return (
        "local node = __NODE\n"
        '__DATAPOOL = node("Default", "DataPool", {\n'
        f'    __SPARSE("Groups", "Pool", {{\n        {entries},\n    }}, {form}, {ptr}),\n'
        "})\n"
        "function DataPool() return __DATAPOOL end\n"
    )


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
