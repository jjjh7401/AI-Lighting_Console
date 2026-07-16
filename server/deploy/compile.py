"""pcall compile harness (M7 — REQ-MVP-019, AC-MVP-010 ①).

Compiles submitted Lua 5.4 source inside an embedded runtime (lupa — the
validated M2 pattern for exercising console-side Lua server-side) WITHOUT
executing it: ``load(source, chunk_name, "t")`` is the whole check. The chunk
is never called, so model-generated source cannot run on the server; mode
``"t"`` additionally rejects binary chunks. A failure returns the raw Lua
diagnostic — the structured error the self-correction loop feeds back to the
model (acceptance GWT scenario 5).

Each check uses a FRESH runtime: one submission can never pollute the next.
"""

from __future__ import annotations

from dataclasses import dataclass

import lupa.lua54 as lua54


@dataclass(frozen=True)
class CompileResult:
    """The compile verdict for one Lua source submission."""

    ok: bool
    error: str = ""


class LuaCompileChecker:
    """Embedded Lua 5.4 compile check — load-only, never executes."""

    def check(self, lua_source: str, *, chunk_name: str = "deploy") -> CompileResult:
        """Compile one Lua source; returns the Lua diagnostic on failure."""
        if not isinstance(lua_source, str) or not lua_source.strip():
            return CompileResult(ok=False, error="empty Lua source")
        try:
            runtime = lua54.LuaRuntime(unpack_returned_tuples=True)
            lua_load = runtime.globals()["load"]
            # Compile ONLY: the returned chunk is deliberately never called.
            result = lua_load(lua_source, f"={chunk_name}", "t")
        except Exception as error:  # runtime construction / load call failure
            return CompileResult(ok=False, error=f"lua load failed: {error}")
        if isinstance(result, tuple):
            # Lua convention: load() returns (nil, message) on compile error.
            message = result[1] if len(result) > 1 and result[1] else "unknown compile error"
            return CompileResult(ok=False, error=str(message))
        if result is None:
            return CompileResult(ok=False, error="unknown compile error")
        return CompileResult(ok=True)
