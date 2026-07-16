"""pcall compile harness tests (M7 — REQ-MVP-019, AC-MVP-010 ①).

The checker compiles submitted Lua 5.4 source inside an embedded runtime
(lupa — the validated M2 pattern) WITHOUT executing it: ``load(source, name,
"t")`` is the compile step; the chunk is never called. A compile failure is a
structured error that feeds the self-correction loop; it must never reach the
deploy path.
"""

from __future__ import annotations

from server.deploy.compile import CompileResult, LuaCompileChecker


class TestCompileOk:
    def test_valid_source_compiles(self):
        result = LuaCompileChecker().check("local x = 1\nreturn x")
        assert result == CompileResult(ok=True)

    def test_valid_plugin_shaped_source_compiles(self):
        source = (
            "local function main(display_handle, argument)\n"
            '    Cmd("Store Group 3")\n'
            "end\n"
            "return main\n"
        )
        assert LuaCompileChecker().check(source).ok is True

    def test_compile_only_never_executes_the_chunk(self):
        # A chunk that would raise AT RUNTIME must still compile cleanly:
        # proof that check() loads without calling.
        result = LuaCompileChecker().check('error("must never run")')
        assert result.ok is True

    def test_unicode_source_compiles(self):
        assert LuaCompileChecker().check('local s = "샤막 워시"\nreturn s').ok is True


class TestCompileFailure:
    def test_syntax_error_is_reported(self):
        result = LuaCompileChecker().check("function broken( end")
        assert result.ok is False
        assert result.error != ""

    def test_unterminated_string_is_reported(self):
        result = LuaCompileChecker().check('local s = "never closed')
        assert result.ok is False

    def test_error_message_carries_the_lua_diagnostic(self):
        result = LuaCompileChecker().check("return return")
        assert result.ok is False
        # The Lua diagnostic (with the chunk name) is the self-correction feed.
        assert "deploy" in result.error or "unexpected" in result.error.lower()

    def test_chunk_name_appears_in_the_diagnostic(self):
        result = LuaCompileChecker().check("local = 1", chunk_name="cleaner")
        assert result.ok is False
        assert "cleaner" in result.error

    def test_binary_chunk_is_rejected(self):
        # mode "t" (text only): precompiled/binary chunks never load.
        result = LuaCompileChecker().check("\x1bLua\x00\x00")
        assert result.ok is False

    def test_empty_source_is_rejected(self):
        assert LuaCompileChecker().check("").ok is False
        assert LuaCompileChecker().check("   \n  ").ok is False


class TestIsolation:
    def test_each_check_uses_a_fresh_runtime(self):
        checker = LuaCompileChecker()
        # Same checker, two checks: the first source cannot pollute the second.
        assert checker.check("x = 1").ok is True
        assert checker.check("function broken(").ok is False
        assert checker.check("x = 2").ok is True
