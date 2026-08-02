# `preshow_check` tool registration — draft diff for `server/orchestrator/tools.py`

Not applied (out of this task's write set — `server/preshow/` + `server/tests/`
only). Paste these four hunks into `server/orchestrator/tools.py` by hand.

Design note: the registered handler wires **only** `state_port` (via
`run_preshow_checklist(state_port=...)`) — it never passes `osc_config`, so it
never needs to import `server.preshow.osc_check` or anything that touches
`server.bridge`. This keeps `server/orchestrator/tools.py` at zero bridge
imports, satisfying
`test_architecture.py::test_orchestrator_and_llm_packages_have_zero_bridge_imports`
unchanged. The live OSC round-trip / receive-port-binding checks always
report `skip` through this path — by design, the same way `precheck_patch`
never touches the bridge directly and relies on the wired `state_port` /
`property_port` instead. A live OSC probe stays a `server/tools/` /
`server/preshow/osc_check.py` operator diagnostic, run out-of-band.

## Hunk 1 — import (near the other `server.prechk` imports, ~line 65)

```diff
 from server.prechk.query import read_properties
 from server.prechk.report import build_report as build_precheck_report
+from server.preshow.runner import run_preshow_checklist
```

## Hunk 2 — `TOOL_NAMES` (~line 84)

```diff
     "precheck_patch",
+    "preshow_check",
     "find_fx",
```

## Hunk 3 — handler (near `precheck_patch`'s closing brace, before the
`# -- find_fx` section, ~line 1512-1560; mirrors `precheck_patch`'s
`property_port is None` guard)

```diff
+    # -- preshow_check (SPEC-COPILOT-PRESHOW-001 — the pre-show checklist) ----
+    #
+    # @MX:NOTE: read-only diagnostic; reuses the same state_port precheck_patch
+    #   already depends on. Never touches server.bridge (see
+    #   server/preshow/TOOLS_REGISTRATION.md for the rationale) — the live OSC
+    #   round-trip / receive-port-binding checks always report "skip" here.
+    def preshow_check(call: ToolCall, context: ExecutionContext) -> ToolExecution:
+        report = run_preshow_checklist(
+            state_port=state_port,
+            sequences_path=rig_paths.get("sequences", "DataPool/Sequences"),
+            preset_pools_path=rig_paths.get("preset_pools", "DataPool/PresetPools"),
+        )
+        content = json.dumps(report.to_dict(), ensure_ascii=False)
+        return ToolExecution(
+            result=ToolResult(
+                tool_call_id=call.id,
+                name=call.name,
+                content=content,
+                is_error=report.signal == "red",
+            ),
+        )
+
```

## Hunk 4 — `ToolDefinition` (append after the `precheck_patch` `ToolDefinition`
block, ~line 2645, before `find_fx`'s definition)

```diff
+        ToolDefinition(
+            name="preshow_check",
+            description=(
+                "Run the standard pre-show checklist in one pass: sequence/"
+                "executor presence, preset (look) library integrity, and the "
+                "project's known field pitfalls (stale OSC socket advisory, "
+                "osc_slot Send=Yes row, feedback-port drift). Returns a "
+                "traffic-light signal — green (every check passed), yellow "
+                "(at least one check could not be verified — SKIP, never a "
+                "silent pass), or red (at least one check failed). The live "
+                "OSC round-trip and receive-port checks always report SKIP "
+                "through this tool; run the operator-facing "
+                "server/preshow/osc_check.py diagnostic separately for those. "
+                "Takes no arguments."
+            ),
+            parameters={
+                "type": "object",
+                "properties": {},
+                "required": [],
+                "additionalProperties": False,
+            },
+        ),
```

## Hunk 5 — `handlers` dict (~line 2997)

```diff
         "precheck_patch": precheck_patch,
+        "preshow_check": preshow_check,
         "find_fx": find_fx,
```

## Verification after applying

```bash
uv run pytest server/tests/test_architecture.py server/tests/test_prechk_tool.py \
    server/tests/test_preshow_runner.py -q
```

`test_orchestrator_and_llm_packages_have_zero_bridge_imports` must still pass
unchanged — the whole point of the design above.
