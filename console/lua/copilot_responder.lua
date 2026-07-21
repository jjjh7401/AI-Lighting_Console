-- CopilotResponder — grandMA3 console-side Lua 5.4 responder plugin (M2/M7).
-- SPEC-COPILOT-MVP-001: REQ-MVP-003 (object-tree state snapshot) +
-- REQ-MVP-004 (execution result retrieval) + REQ-MVP-019 (plugin deployment).
-- Target: grandMA3 onPC 2.4.2.
--
-- @MX:NOTE: [AUTO] wire protocol v1 — requests arrive as the plugin argument
--   ("<verb> <id> [rest]"); replies are percent-encoded JSON sent as one OSC
--   string to /copilot/state (snapshots) or /copilot/feedback (results).
--   Contract doc: console/lua/PROTOCOL.md (the M3 tool-runner consumes it);
--   Python twin: server/bridge/protocol.py.
--
-- Invocation (rides /copilot/cmd — plan.md §A-5 namespace):
--   Plugin "CopilotResponder" "ping <id>"
--   Plugin "CopilotResponder" "state <id> <object-path>"   e.g. DataPool/Sequences
--   Plugin "CopilotResponder" "exec <id> <ma3-command>"    e.g. exec 7 List
--   Plugin "CopilotResponder" "deploy <id> <enc-name> <enc-source>"  (M7 —
--     both tokens percent-encoded; reviewed source only, see PROTOCOL.md §2)
-- Fallback when plugin arguments are unavailable: set the user variable
--   COPILOT_REQ to the request string, then call the plugin without arguments.
--
-- Honesty contract (Section B / REQ-MVP-032): this responder replies ONLY to
-- requests that actually arrive; it keeps no timers, no retries, no resident
-- loop, and has no side effects beyond the requested Cmd() execution.

-- User-tunable configuration (see console/lua/README.md).
local CONFIG = {
    osc_slot = 1, -- row index in the console's OSC settings used for replies
    state_address = "/copilot/state",
    feedback_address = "/copilot/feedback",
    max_children = 24, -- snapshot child cap (UDP payload budget)
    max_payload = 4000, -- max encoded payload length in bytes
    send_variant = "packed", -- "packed" | "args" | "cmd_keyword" (see PROTOCOL.md §5)
    uservar_name = "COPILOT_REQ",
}

local M = {
    NAME = "CopilotResponder",
    -- 1.1.0: additive deploy verb (M7). 1.2.0: snapshot `i` is the REAL pool
    -- slot and is omitted when unknown (was the loop position). Protocol v1.
    VERSION = "1.2.0",
    PROTO = 1,
    CONFIG = CONFIG,
}

-- -- logging ---------------------------------------------------------------

function M.log(message)
    -- Percent-encoded payloads are full of '%', so never route them through
    -- Printf's format path; message must be a plain short string.
    if type(Printf) == "function" then
        pcall(Printf, message)
    end
end

-- -- JSON encoder (subset: objects, arrays, strings, integers, booleans) ----

local ARRAY_MT = {}

function M.array(t)
    return setmetatable(t or {}, ARRAY_MT)
end

local JSON_ESCAPES = {
    ['"'] = '\\"',
    ["\\"] = "\\\\",
    ["\b"] = "\\b",
    ["\f"] = "\\f",
    ["\n"] = "\\n",
    ["\r"] = "\\r",
    ["\t"] = "\\t",
}

local function json_escape_char(c)
    return JSON_ESCAPES[c] or string.format("\\u%04X", string.byte(c))
end

local function json_string(s)
    -- Byte-explicit escape class: JSON requires escaping only bytes < 0x20,
    -- the quote, and the backslash (DEL kept escaped for safety). The former
    -- '%c' class was locale-dependent and matched C1-range bytes (0x80-0x9F),
    -- corrupting UTF-8 continuation bytes in non-ASCII replies (M7 fix).
    return '"' .. s:gsub('[\0-\31"\\\127]', json_escape_char) .. '"'
end

function M.json_encode(value)
    local t = type(value)
    if t == "nil" then
        return "null"
    elseif t == "boolean" then
        return value and "true" or "false"
    elseif t == "number" then
        if math.type(value) == "integer" then
            return string.format("%d", value)
        end
        return string.format("%.10g", value)
    elseif t == "string" then
        return json_string(value)
    elseif t == "table" then
        if getmetatable(value) == ARRAY_MT or value[1] ~= nil then
            local parts = {}
            for i = 1, #value do
                parts[#parts + 1] = M.json_encode(value[i])
            end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        local keys = {}
        for key in pairs(value) do
            keys[#keys + 1] = tostring(key)
        end
        table.sort(keys) -- deterministic output for debugging/diffing
        local parts = {}
        for _, key in ipairs(keys) do
            parts[#parts + 1] = json_string(key) .. ":" .. M.json_encode(value[key])
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return json_string(tostring(value))
end

-- -- percent encoding (comma/quote/space-free wire form) --------------------

function M.percent_encode(s)
    -- Encode every byte outside the unreserved set, including all UTF-8
    -- bytes: the wire payload stays pure-ASCII and never contains the ','
    -- delimiter of MA3's packed OSC-send string form.
    return (s:gsub("[^A-Za-z0-9%-%._~]", function(c)
        return string.format("%%%02X", string.byte(c))
    end))
end

function M.encode_payload(payload)
    return M.percent_encode(M.json_encode(payload))
end

function M.percent_decode(s)
    return (s:gsub("%%(%x%x)", function(hex)
        return string.char(tonumber(hex, 16))
    end))
end

-- -- request parsing --------------------------------------------------------

function M.parse_request(s)
    if type(s) ~= "string" then
        return nil, "request must be a string"
    end
    local kind, id, rest = s:match("^%s*(%S+)%s+(%S+)%s*(.*)$")
    if not kind then
        if s:match("^%s*(%S+)%s*$") then
            return nil, "missing request id (expected: <verb> <id> [rest])"
        end
        return nil, "empty request"
    end
    return { kind = kind:lower(), id = id, rest = rest }
end

-- -- MA3 handle accessors (defensive: exact 2.4.2 surface verified live) ----

function M.safe_name(handle)
    local ok, value = pcall(function() return handle.name end)
    if ok and type(value) == "string" and value ~= "" then
        return value
    end
    ok, value = pcall(function() return handle:Get("name") end)
    if ok and type(value) == "string" and value ~= "" then
        return value
    end
    ok, value = pcall(function() return tostring(handle) end)
    if ok and type(value) == "string" then
        return value
    end
    return "?"
end

function M.safe_class(handle)
    local ok, value = pcall(function() return handle:GetClass() end)
    if ok and type(value) == "string" and value ~= "" then
        return value
    end
    ok, value = pcall(function() return handle.class end)
    if ok and type(value) == "string" and value ~= "" then
        return value
    end
    return "?"
end

-- -- pool-slot resolution (the listing position is NOT an address) -----------

-- @MX:ANCHOR: [AUTO] pool-slot contract — a child's slot is reported ONLY when
--   it was positively established; an unestablished slot is reported as
--   *nothing*, never as the child's position in the listing.
-- @MX:REASON: cross-layer contract boundary (fan_in >= 3: build_snapshot's
--   wire `i`, server/orchestrator/tools.py `_rig_object` -> the LLM-facing pool
--   number, server/safety/console.py free-slot + `Delete Plugin <slot>` math).
--   Children() COMPACTS gaps away, so position N is object N only on a dense
--   pool; emitting it as an address made the model issue `Group 2 + 3` on a
--   pool holding 1/5/7 — the console rejected the object AFTER
--   `ChangeDestination Root` and `ClearAll` had already executed.
-- @MX:SPEC: SPEC-COPILOT-DEPLOY-001

-- Two independent sources answer "which slot is this child in", in priority
-- order:
--   1. the child's OWN index accessor — authoritative, because the object
--      knows where it lives. Accepted only as a COHERENT SET (see
--      M.probe_slots), never per child.
--   2. the listing position — only ever a GUESS, accepted per child solely
--      when the parent hands this same object back for it (M.slot_confirms).
-- Source 2 deliberately does NOT get to veto source 1: if Ptr() turned out to
-- be positional rather than slot-addressed on 2.4.2, a veto would throw away
-- a CORRECT self-reported slot and re-emit the listing position — the exact
-- defect, wearing a confirmation badge.

-- Self-index accessors, most authoritative first. Which (if any) exists on
-- 2.4.2 is unverified — PROTOCOL.md §6 ASSUMPTION-7 — so every form is probed
-- pcall-guarded and the whole set is sanity-gated before it is believed.
local SLOT_PROBES = {
    function(child) return child:Index() end,
    function(child) return child.index end,
    function(child) return child.no end,
    function(child) return child:GetIndex() end,
    function(child) return child:Get("no") end,
}

local function as_slot(value)
    if type(value) == "string" then
        value = tonumber(value)
    end
    if type(value) ~= "number" then
        return nil
    end
    local slot = math.tointeger(value)
    if slot and slot >= 1 then
        return slot
    end
    return nil
end

-- Asks the PARENT for a candidate slot and checks that it hands this same
-- object back — what turns a guessed position into an established slot. A gap
-- (Ptr returns nil) or a different object both refute the guess.
function M.slot_confirms(handle, slot, child)
    local ok, other = pcall(function() return handle:Ptr(slot) end)
    if not ok or other == nil then
        return false -- no Ptr, or nothing lives there: nothing established
    end
    if other == child then
        return true
    end
    -- Two handles may be distinct wrappers around one console object, so an
    -- identity miss alone is not a contradiction; name+class equality is the
    -- fallback (duplicate names inside one pool are the known blind spot).
    return M.safe_name(other) == M.safe_name(child)
        and M.safe_class(other) == M.safe_class(child)
end

-- Self-reported slots for a whole listing, or nil. Accepted only as a coherent
-- SET: one value per child, each a positive integer, strictly increasing in
-- listing order. A silent, 0-based, or unordered accessor fails that gate and
-- is discarded WHOLE — a half-trusted numbering is exactly how a plausible
-- wrong number gets out.
function M.probe_slots(children)
    local slots = {}
    local previous = 0
    for i = 1, #children do
        local value
        for _, probe in ipairs(SLOT_PROBES) do
            local ok, raw = pcall(probe, children[i])
            if ok then
                value = as_slot(raw)
                if value then
                    break
                end
            end
        end
        if not value or value <= previous then
            return nil
        end
        slots[i] = value
        previous = value
    end
    return slots
end

-- Returns an array of { obj = <handle>, slot = <integer|nil> } in console
-- listing order; `slot` is the real pool slot or nil when it could not be
-- established. Callers MUST NOT substitute the array position for a nil slot.
function M.safe_children(handle)
    local ok, children = pcall(function() return handle:Children() end)
    if ok and type(children) == "table" then
        local probed = M.probe_slots(children)
        local out = {}
        for i = 1, #children do
            local slot = probed and probed[i] or nil
            if not slot and M.slot_confirms(handle, i, children[i]) then
                slot = i -- the pool really is dense this far: position IS slot
            end
            out[#out + 1] = { obj = children[i], slot = slot }
        end
        return out
    end
    local okc, count = pcall(function() return handle:Count() end)
    if okc and type(count) == "number" then
        local out = {}
        for i = 1, count do
            local okp, child = pcall(function() return handle:Ptr(i) end)
            if okp and child then
                -- This branch ADDRESSES by index: we asked for slot i and the
                -- console handed an object back, so i is that object's slot.
                out[#out + 1] = { obj = child, slot = i }
            end
        end
        return out
    end
    return {}
end

-- -- object-tree path resolution (REQ-MVP-003) ------------------------------

-- Root aliases let paths start at well-known MA3 Lua entry points; unknown
-- first segments fall back to navigation from Root().
local ROOT_ALIASES = {
    datapool = function() return DataPool and DataPool() or nil end,
    root = function() return Root and Root() or nil end,
    showdata = function() return ShowData and ShowData() or nil end,
    patch = function() return Patch and Patch() or nil end,
}

function M.find_child(handle, segment)
    local children = M.safe_children(handle)
    if segment:match("^%d+$") then
        -- A numeric segment addresses the POOL SLOT — the same number a
        -- snapshot reports as `i` (PROTOCOL.md §2). It degrades to the legacy
        -- positional meaning ONLY when no slot at all could be established;
        -- mixing the two would make 'Groups/5' on a 1/5/7 pool silently
        -- resolve to the 5th listed object (or, worse, a neighbour).
        local wanted_slot = tonumber(segment)
        local any_slot_known = false
        for _, entry in ipairs(children) do
            if entry.slot then
                any_slot_known = true
                if entry.slot == wanted_slot then
                    return entry.obj
                end
            end
        end
        if any_slot_known then
            return nil -- that slot is empty (a gap), not "the Nth object"
        end
        local entry = children[wanted_slot]
        return entry and entry.obj or nil
    end
    local wanted = segment:lower()
    for _, entry in ipairs(children) do
        if M.safe_name(entry.obj):lower() == wanted then
            return entry.obj
        end
    end
    return nil
end

function M.resolve_path(path)
    if type(path) ~= "string" or path == "" then
        return nil, "empty object path"
    end
    local segments = {}
    for segment in path:gmatch("[^/]+") do
        segments[#segments + 1] = segment
    end
    if #segments == 0 then
        return nil, "empty object path"
    end
    local handle
    local start_index = 1
    local alias = ROOT_ALIASES[segments[1]:lower()]
    if alias then
        local ok, aliased = pcall(alias)
        if ok and aliased then
            handle = aliased
            start_index = 2
        end
    end
    if not handle then
        local ok, root = pcall(function() return Root() end)
        if not ok or not root then
            return nil, "cannot resolve tree root (Root() unavailable)"
        end
        handle = root
    end
    for i = start_index, #segments do
        local child = M.find_child(handle, segments[i])
        if not child then
            return nil, string.format("path segment not found: '%s' (in %s)", segments[i], path)
        end
        handle = child
    end
    return handle
end

-- -- payload builders --------------------------------------------------------

function M.build_pong(id)
    return {
        v = M.PROTO,
        kind = "pong",
        id = id,
        plugin = M.NAME,
        version = M.VERSION,
        proto = M.PROTO,
    }
end

-- Backs off from a raw byte cut point so a truncation never splits a
-- multi-byte UTF-8 sequence (a continuation byte lives in 0x80-0xBF).
local function safe_truncate(s, max_len)
    if max_len <= 0 then
        return ""
    end
    if #s <= max_len then
        return s
    end
    local cut = max_len
    while cut > 0 and string.byte(s, cut) >= 0x80 and string.byte(s, cut) < 0xC0 do
        cut = cut - 1
    end
    return s:sub(1, cut)
end

function M.build_snapshot(id, path)
    local handle, err = M.resolve_path(path)
    if not handle then
        local payload = { v = M.PROTO, kind = "state", id = id, path = path, ok = false, error = err }
        -- Size guard (M6c-4 fix): the success branch below already bounds
        -- its reply to CONFIG.max_payload by dropping children; this
        -- failure branch used to echo the full, unbounded query path
        -- (sometimes twice, via `err`) with no truncation at all. Apply the
        -- same UDP-budget guard here by shrinking the echoed error/path
        -- strings (PROTOCOL.md §4).
        while #M.encode_payload(payload) > CONFIG.max_payload
            and (#payload.error > 0 or #payload.path > 0) do
            if #payload.error > 0 then
                payload.error = safe_truncate(payload.error, math.floor(#payload.error / 2))
            elseif #payload.path > 0 then
                payload.path = safe_truncate(payload.path, math.floor(#payload.path / 2))
            end
        end
        return payload
    end
    local children = M.safe_children(handle)
    local total = #children
    local cap = math.min(total, CONFIG.max_children)
    local items = M.array({})
    for i = 1, cap do
        local entry = children[i]
        local item = { name = M.safe_name(entry.obj), class = M.safe_class(entry.obj) }
        -- `i` carries the REAL pool slot and is OMITTED when that slot could
        -- not be established (PROTOCOL.md §4.2) — a consumer must then resolve
        -- the number before addressing the object, not count list positions.
        if entry.slot then
            item.i = entry.slot
        end
        items[#items + 1] = item
    end
    local payload = {
        v = M.PROTO,
        kind = "state",
        id = id,
        path = path,
        ok = true,
        node = {
            name = M.safe_name(handle),
            class = M.safe_class(handle),
            childCount = total,
        },
        children = items,
        truncated = cap < total,
    }
    -- Size guard: drop trailing children until the encoded payload fits the
    -- UDP budget (documented in PROTOCOL.md §4).
    while #M.encode_payload(payload) > CONFIG.max_payload and #items > 0 do
        table.remove(items)
        payload.truncated = true
    end
    return payload
end

-- @MX:NOTE: [AUTO] Cmd() result classification is an assumption pending live
--   2.4.2 verification (PROTOCOL.md §6 ASSUMPTION-3): nil/""/"ok" = success,
--   any other string = failure with the raw string as the error message.
local SUCCESS_RESULTS = { [""] = true, ["ok"] = true }

function M.classify_result(result)
    if result == nil then
        return true, ""
    end
    if type(result) ~= "string" then
        result = tostring(result)
    end
    local normalized = result:lower():gsub("^%s+", ""):gsub("%s+$", "")
    return SUCCESS_RESULTS[normalized] == true, result
end

function M.build_exec_result(id, command)
    local ok, result = pcall(Cmd, command)
    if not ok then
        return {
            v = M.PROTO,
            kind = "result",
            id = id,
            ok = false,
            error = "lua error: " .. tostring(result),
        }
    end
    local success, raw = M.classify_result(result)
    if success then
        return { v = M.PROTO, kind = "result", id = id, ok = true, result = raw }
    end
    return { v = M.PROTO, kind = "result", id = id, ok = false, result = raw, error = raw }
end

-- -- plugin deployment (M7 — REQ-MVP-019, ASSUMPTION-6) -----------------------

-- @MX:WARN: [AUTO] unverified MA3 API surface — plugin-object creation and
--   Lua-component source assignment are 2.4.2 assumptions (PROTOCOL.md §6
--   ASSUMPTION-6); every accessor form is pcall-guarded and probed in order
-- @MX:REASON: no live console was available at M7 implementation time; the
--   deploy verb is exercised only against the mocked pool surface — verify
--   on-site with a harmless plugin before relying on deployment

function M.plugin_pool()
    local ok, pool = pcall(function()
        return M.find_child(DataPool(), "Plugins")
    end)
    if ok and pool then
        return pool
    end
    return nil, "plugin pool not found (DataPool/Plugins)"
end

local function acquire_child(handle)
    for _, method_name in ipairs({ "Acquire", "Append" }) do
        local ok, child = pcall(function()
            return handle[method_name](handle)
        end)
        if ok and child then
            return child
        end
    end
    return nil
end

function M.find_or_create_plugin(name)
    local pool, err = M.plugin_pool()
    if not pool then
        return nil, false, err
    end
    local existing = M.find_child(pool, name)
    if existing then
        return existing, false
    end
    local created = acquire_child(pool)
    if not created then
        return nil, false, "cannot create plugin object (Acquire/Append probes failed)"
    end
    local named = pcall(function()
        created.name = name
    end)
    if not named or M.safe_name(created) ~= name then
        pcall(function()
            created:Set("name", name)
        end)
    end
    return created, true
end

function M.set_plugin_source(plugin, source)
    local component
    local children = M.safe_children(plugin)
    if #children > 0 then
        component = children[1].obj
    else
        component = acquire_child(plugin)
    end
    if not component then
        return false, "cannot create plugin component (Acquire/Append probes failed)"
    end
    local setters = {
        function()
            component.content = source
        end,
        function()
            component.Content = source
        end,
        function()
            component:Set("content", source)
        end,
        function()
            component:SetContent(source)
        end,
    }
    for _, setter in ipairs(setters) do
        if pcall(setter) then
            local readable, value = pcall(function()
                return component.content or component.Content
            end)
            -- Only a CONFIRMED readback (matches what was written) counts as
            -- success; an unreadable or nil/mismatched readback means this
            -- accessor form did NOT actually persist the source (M6c-4 fix
            -- — the prior logic wrongly treated an unconfirmed write, i.e.
            -- readback returning nil, as success).
            if readable and value == source then
                return true
            end
        end
    end
    return false, "cannot confirm plugin source write (readback did not match any setter form)"
end

function M.build_deploy_result(id, name, source)
    local function fail(message)
        return { v = M.PROTO, kind = "deploy", id = id, ok = false, name = name, error = message }
    end
    -- Defense in depth behind the server-side pcall harness: re-compile in
    -- the REAL console runtime BEFORE touching the plugin pool. The chunk is
    -- loaded text-only and never called here.
    local chunk, err = load(source, "=" .. name, "t")
    if not chunk then
        return fail("lua compile failed: " .. tostring(err))
    end
    local plugin, created, perr = M.find_or_create_plugin(name)
    if not plugin then
        return fail(perr)
    end
    local ok, serr = M.set_plugin_source(plugin, source)
    if not ok then
        return fail(serr)
    end
    return { v = M.PROTO, kind = "deploy", id = id, ok = true, name = name, created = created }
end

-- -- OSC reply transport ------------------------------------------------------

function M.pack_message(address, encoded)
    return address .. ",s," .. encoded
end

-- @MX:WARN: [AUTO] unverified MA3 API surface — SendOSCMessage signature and
--   the SendOSC command keyword are 2.4.2 assumptions (PROTOCOL.md §5
--   ASSUMPTION-2); every variant is pcall-guarded with a cmd_keyword fallback
-- @MX:REASON: no live console was available at M2 implementation time; the
--   semi-automatic AC-MVP-012 round-trip (server/tools/responder_roundtrip.py)
--   is the designated verification path — adjust CONFIG.send_variant on-site
function M.send_reply(address, payload)
    local encoded = M.encode_payload(payload)
    local senders = {
        packed = function()
            SendOSCMessage(CONFIG.osc_slot, M.pack_message(address, encoded))
        end,
        args = function()
            SendOSCMessage(CONFIG.osc_slot, address, encoded)
        end,
        cmd_keyword = function()
            Cmd(string.format('SendOSC %d "%s"', CONFIG.osc_slot, M.pack_message(address, encoded)))
        end,
    }
    local variant = CONFIG.send_variant
    local sender = senders[variant] or senders.packed
    if pcall(sender) then
        return true
    end
    if variant ~= "cmd_keyword" and pcall(senders.cmd_keyword) then
        return true
    end
    M.log("copilot_responder: OSC reply send failed (check CONFIG.osc_slot / send_variant)")
    return false
end

-- -- dispatch ------------------------------------------------------------------

function M.handle_request(request)
    local parsed, err = M.parse_request(request)
    if not parsed then
        local payload = { v = M.PROTO, kind = "error", id = "-", ok = false, error = err }
        M.send_reply(CONFIG.feedback_address, payload)
        return payload
    end
    local payload
    if parsed.kind == "ping" then
        payload = M.build_pong(parsed.id)
        M.send_reply(CONFIG.feedback_address, payload)
    elseif parsed.kind == "state" then
        if parsed.rest == "" then
            payload = {
                v = M.PROTO,
                kind = "state",
                id = parsed.id,
                ok = false,
                error = "missing object path (expected: state <id> <path>)",
            }
        else
            payload = M.build_snapshot(parsed.id, parsed.rest)
        end
        M.send_reply(CONFIG.state_address, payload)
    elseif parsed.kind == "exec" then
        if parsed.rest == "" then
            payload = {
                v = M.PROTO,
                kind = "result",
                id = parsed.id,
                ok = false,
                error = "missing command (expected: exec <id> <command>)",
            }
        else
            payload = M.build_exec_result(parsed.id, parsed.rest)
        end
        M.send_reply(CONFIG.feedback_address, payload)
    elseif parsed.kind == "deploy" then
        local enc_name, enc_source = parsed.rest:match("^(%S+)%s+(%S+)$")
        if not enc_name then
            payload = {
                v = M.PROTO,
                kind = "deploy",
                id = parsed.id,
                ok = false,
                error = "malformed deploy request (expected: deploy <id> <enc-name> <enc-source>)",
            }
        else
            payload = M.build_deploy_result(
                parsed.id,
                M.percent_decode(enc_name),
                M.percent_decode(enc_source)
            )
        end
        M.send_reply(CONFIG.feedback_address, payload)
    else
        payload = {
            v = M.PROTO,
            kind = "error",
            id = parsed.id,
            ok = false,
            error = "unknown request kind: " .. parsed.kind,
        }
        M.send_reply(CONFIG.feedback_address, payload)
    end
    return payload
end

-- -- plugin entry point ---------------------------------------------------------

local function main(display_handle, argument)
    local request = argument
    if request == nil or request == "" then
        local ok, value = pcall(function()
            return GetVar(UserVars(), CONFIG.uservar_name)
        end)
        if ok and type(value) == "string" and value ~= "" then
            request = value
        end
    end
    if request == nil or request == "" then
        M.log(
            "copilot_responder v" .. M.VERSION
                .. ' - no request. Usage: Plugin "CopilotResponder" "ping <id>"'
        )
        return
    end
    M.handle_request(request)
end

-- Test hook: inert on the console (COPILOT_TEST_EXPORT is nil there); the
-- pytest lupa harness sets it before loading this file to reach module internals.
if COPILOT_TEST_EXPORT then
    COPILOT_TEST_EXPORT.module = M
end

return main
