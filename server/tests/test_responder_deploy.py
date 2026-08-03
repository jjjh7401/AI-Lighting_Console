"""Responder deploy-verb tests (M7 — PROTOCOL.md §2 ``deploy``, ASSUMPTION-6).

Runs the production ``console/lua/copilot_responder.lua`` in embedded Lua 5.4
(lupa — the validated M2 pattern) with a mocked plugin pool. The deploy verb
percent-decodes name + source, RE-COMPILES the source in the console runtime
(defense in depth behind the server-side pcall harness), then creates or
updates the plugin object through pcall-guarded accessor probes.

Mocked-fidelity bound (same M2 discipline): the MA3 plugin-object creation API
is onPC-unverified (ASSUMPTION-6) — the mock implements ONE plausible surface
(pool:Acquire() + component ``content`` property).
"""

from __future__ import annotations

import urllib.parse

import pytest

from server.bridge.protocol import decode_payload

from .lua_mock_env import ResponderHarness

FEEDBACK_ADDRESS = "/copilot/feedback"

# A mocked plugin pool grafted onto the M2 default tree: plugins support
# component acquisition; components are plain nodes with a `content` field.
PLUGIN_POOL_ENV = r"""
local node = __NODE
local function plugin_node(name)
    local p = node(name, "Plugin", {})
    function p:Acquire()
        local c = node("PluginComponent 1", "PluginComponent", {})
        table.insert(self._children, c)
        return c
    end
    return p
end
__PLUGINS = node("Plugins", "Pool", {})
function __PLUGINS:Acquire()
    local p = plugin_node("")
    table.insert(self._children, p)
    return p
end
table.insert(__DATAPOOL._children, __PLUGINS)
"""


def _enc(text: str) -> str:
    return urllib.parse.quote(text, safe="")


def _deploy_request(request_id: str, name: str, source: str) -> str:
    return f"deploy {request_id} {_enc(name)} {_enc(source)}"


@pytest.fixture()
def harness() -> ResponderHarness:
    return ResponderHarness(extra_env=PLUGIN_POOL_ENV)


def _last_reply(harness):
    (sent) = harness.sent()
    assert sent, "no OSC reply captured"
    message = sent[-1]
    return message.address, decode_payload(message.payload)


def _pool_plugins(harness):
    return harness.lua.eval(
        "(function()\n"
        "  local out = {}\n"
        "  for i, p in ipairs(__PLUGINS._children) do\n"
        "    local content = nil\n"
        "    if p._children[1] then content = p._children[1].content end\n"
        "    out[i] = { name = p.name, content = content }\n"
        "  end\n"
        "  return out\n"
        "end)()"
    )


SOURCE = 'local function main()\n    Cmd("Store Group 3")\nend\nreturn main\n'


class TestDeployHappyPath:
    def test_deploy_creates_the_plugin_with_the_source(self, harness):
        harness.main(None, _deploy_request("d1", "Cleaner", SOURCE))
        address, payload = _last_reply(harness)
        assert address == FEEDBACK_ADDRESS
        assert payload["kind"] == "deploy"
        assert payload["id"] == "d1"
        assert payload["ok"] is True
        assert payload["name"] == "Cleaner"
        assert payload["created"] is True
        plugins = _pool_plugins(harness)
        assert plugins[1]["name"] == "Cleaner"
        assert plugins[1]["content"] == SOURCE

    def test_redeploy_updates_the_existing_plugin(self, harness):
        harness.main(None, _deploy_request("d1", "Cleaner", SOURCE))
        updated = SOURCE.replace("Group 3", "Group 4")
        harness.main(None, _deploy_request("d2", "Cleaner", updated))
        _, payload = _last_reply(harness)
        assert payload["ok"] is True
        assert payload["created"] is False
        plugins = _pool_plugins(harness)
        assert harness.lua.eval("#__PLUGINS._children") == 1
        assert plugins[1]["content"] == updated

    def test_unicode_name_round_trips(self, harness):
        harness.main(None, _deploy_request("d1", "샤막 정리", SOURCE))
        _, payload = _last_reply(harness)
        assert payload["ok"] is True
        assert payload["name"] == "샤막 정리"

    def test_source_with_quotes_and_newlines_round_trips(self, harness):
        source = "Cmd(\"Store Cue 5\")\nCmd('List')\n"
        harness.main(None, _deploy_request("d1", "Quoted", source))
        _, payload = _last_reply(harness)
        assert payload["ok"] is True
        plugins = _pool_plugins(harness)
        assert plugins[1]["content"] == source


class TestDeployCompileGuard:
    def test_console_side_recompile_rejects_broken_source(self, harness):
        harness.main(None, _deploy_request("d1", "Broken", "function broken( end"))
        _, payload = _last_reply(harness)
        assert payload["ok"] is False
        assert "compile" in payload["error"]
        # Compile failure happens BEFORE any pool mutation.
        assert harness.lua.eval("#__PLUGINS._children") == 0


class TestDeployErrors:
    def test_missing_arguments_is_an_error_reply(self, harness):
        harness.main(None, "deploy d1 onlyname")
        address, payload = _last_reply(harness)
        assert address == FEEDBACK_ADDRESS
        assert payload["kind"] == "deploy"
        assert payload["ok"] is False
        assert "deploy" in payload["error"]

    def test_missing_plugin_pool_is_reported(self):
        bare = ResponderHarness()  # M2 default tree — no Plugins pool
        bare.main(None, _deploy_request("d1", "Cleaner", SOURCE))
        message = bare.sent()[-1]
        payload = decode_payload(message.payload)
        assert payload["ok"] is False
        assert "plugin pool" in payload["error"].lower()


class TestVersionBump:
    def test_responder_version_is_1_6_0_with_proto_1(self, harness):
        # The plugin version tracks console-side behaviour changes while the
        # wire protocol stays v1: 1.1.0 added the deploy verb (additive),
        # 1.2.0 made the snapshot `i` the real pool slot and made it optional
        # (parse-compatible both ways), 1.3.0 made send_reply try every send
        # variant rather than only the configured one plus cmd_keyword,
        # 1.4.0 (SPEC-COPILOT-EXECBODY-001 M6) resolves the "Executor <n>"
        # console-address form via ObjectList() instead of failing "path
        # segment not found" (PROTOCOL.md revision notes). 1.4.1
        # (SPEC-COPILOT-DASHUI-001 M6) lowers max_payload 4000 -> 1900: the
        # cmd_keyword reply transport dies silently past the live-measured
        # MA3 ~2048-byte command-line limit. 1.5.0 adds prop readback and
        # Cue child cueNo. 1.6.0 (SPEC-COPILOT-INTROSPECT-001 M2) adds the
        # additive props/introspect verbs — bulk property readback and
        # handle field enumeration via the M1-adopted property accessors —
        # all without changing protocol v1.
        assert harness.module["VERSION"] == "1.6.0"
        assert harness.module["PROTO"] == 1


# Finding 1 (HIGH, M6c-4): a plugin pool whose component accessor forms all
# silently drop writes on readback — `content`/`Content` assignment is
# accepted (no error) but never actually persists, and the method-based
# setters (`Set`/`SetContent`) don't exist at all. This simulates "the write
# didn't take" across all four probed accessor forms.
STUBBORN_PLUGIN_POOL_ENV = r"""
local node = __NODE
local function stubborn_component()
    local mt = {
        __newindex = function() end,  -- accept the write, never store it
        __index = function() return nil end,  -- every read comes back nil
    }
    return setmetatable({}, mt)
end
local function plugin_node(name)
    local p = node(name, "Plugin", {})
    function p:Acquire()
        local c = stubborn_component()
        table.insert(self._children, c)
        return c
    end
    return p
end
__PLUGINS = node("Plugins", "Pool", {})
function __PLUGINS:Acquire()
    local p = plugin_node("")
    table.insert(self._children, p)
    return p
end
table.insert(__DATAPOOL._children, __PLUGINS)
"""


class TestSetPluginSourceUnconfirmedWrite:
    """Finding 1 (HIGH, M6c-4): when NONE of the four accessor forms confirm
    the write on readback, the deploy must report failure — not ``ok=true``.
    """

    def test_all_four_accessors_unconfirmed_reports_failure(self):
        harness = ResponderHarness(extra_env=STUBBORN_PLUGIN_POOL_ENV)
        harness.main(None, _deploy_request("d1", "Cleaner", SOURCE))
        _, payload = _last_reply(harness)
        assert payload["ok"] is False
        assert "cannot" in payload["error"].lower()
