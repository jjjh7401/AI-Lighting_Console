# SPEC-COPILOT-READBACK-001 — 되읽기를 값까지 · Research

> 조사 일자 2026-09-03 · 기준 `origin/main adae0ac` · 읽기 전용(파일 변경 0, 콘솔 접촉 0)
> 출처: 보고서 `reports/app-fresh-eyes-review-20260903.md` §3.2·§3.4·§4 P1, Explore 심층 조사
>
> **2026-09-03 분할 고지 — 이 문서는 네 요구를 모두 담고 있고, 본문은 그대로 둔다.** SPEC 이 두 개로 갈리면서 §R1·§R2 는 SPEC-COPILOT-READBACK-001(본 디렉터리)의 근거이고, **§R3·§R4 는 SPEC-COPILOT-READBACK-002 의 근거**가 됐다. 002 의 `research.md` 는 이 파일의 두 절을 가리키는 짧은 포인터다.

## Scope note on the console-write budget (applies to all four)

The repository's discipline is that a read path must not acquire a write. Three of the four requirements are pure-server (R2 partially, R3, R4) and need **zero** console commands. R1 is the only one that touches `console/lua/`, and shipping it costs exactly **one operator-approved responder re-import** — the precedent, the mechanism, and its failure modes are all already recorded:

- The re-import path is `server/safety/console.py:323` `_deploy_via_file_import` → `Import Plugin <slot> '<slug>'` at `server/safety/console.py:463`, and it transits the single safety gate (pinned by `server/tests/test_responder_import_gate.py:1-20`).
- Self-deletion is impossible from inside the responder — `server/safety/console.py:426` refuses `Delete Plugin <own slot>`; the working alias dance is `server/safety/console.py:508-606`. The live discovery is `docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md §1.1-1.3` — naive delete-then-import returned `User Canceled Command`, and `ReloadAllPlugins` answered `ok:true` without reloading anything.
- The lock that makes a `.lua` edit a governance event: `server/tests/test_overlap_preserve.py:160-228`. `console/lua/` is byte-locked; `copilot_responder.lua` and `PROTOCOL.md` are pinned by **content digest** (`:229-232`) and each revision must re-pin with a dated prose grant. A 1.6.4 change therefore requires a new grant block plus two new digests.

---

## R1 — Responder serialization of Lua tables

### Current mechanism

The whole `table: 0x…` defect is one line. `M.safe_property` at `console/lua/copilot_responder.lua:290-308`:

```lua
local ok, value = pcall(function() return handle:Get(property_name) end)
if ok and value ~= nil then
    return tostring(value), nil, type(value)
end
```

`tostring()` on a Lua table yields the address string. The `type(value)` third return already reaches the wire as the `t` field, so a `props` reply today looks like `{"n":"SELECTIONDATA","ok":true,"t":"table","v":"table: 0x7f…"}` — **the reply already announces that the value is a table** and hands back an address anyway. `docs/runbooks/console-channel-facts.md:93-101` names it: 「테이블 주소는 값은 거기 있는데 응답기가 문자열로 안 풀었다 — 제거 가능한 미구현」.

Three verbs funnel through that one function:

| verb | builder | call site |
|---|---|---|
| `prop` | `M.build_prop_result` | `console/lua/copilot_responder.lua:767`, read at `:783` |
| `props` | `M.build_props_result` | `:798`, read at `:817` |
| `introspect` | contrast gate only (no values) | `:883-898` via `M.missing_introspect_contrast_names` |

`introspect` deliberately emits **no values** (`console/lua/PROTOCOL.md:319-330`).

### The exact seam

**`M.safe_property` (`console/lua/copilot_responder.lua:290-308`) is the single seam.** A table-serializing branch belongs there — when `type(value) == "table"`, walk it with the existing `M.json_encode` (`:133-165`) and return the encoded JSON text as the string value, with `t` staying `"table"`.

- **A JSON encoder already exists, hand-rolled, no external lib.** `M.json_encode` at `:133-165` handles objects, arrays (via `ARRAY_MT` at `:105-109`), strings, numbers, booleans, nil. **No `cjson`, no `dkjson`, no `require`** — the sandbox is Lua 5.4 base + MA3 globals (mock surface `server/tests/lua_mock_env.py:22-48`). The array-vs-object heuristic (`getmetatable(value) == ARRAY_MT or value[1] ~= nil`, `:146`) is a trap: a hash with a `[1]` key encodes as an array and loses keys. The fallback at `:165` — `json_string(tostring(value))` — is the address-emitting path.
- **Percent-encoding is applied after JSON** (`M.encode_payload` `:179-181` → `M.percent_encode` `:170-177`), so a nested JSON string inflates ~3× on the wire.

### Byte budget and truncation rules

| axis | value | where |
|---|---|---|
| child count cap | `max_children = 24` | `copilot_responder.lua:33` |
| payload budget | `max_payload = 1900` bytes (encoded) | `:42`, sweep comment `:34-41` — 2000 delivered, 2100 dropped, MA3 CLI ~2048 |
| per-value cap | `max_prop_value = 240` raw bytes | `:44` |
| names per `props` | `max_props_names = 16` | `:43` |

Shrink loops re-encode after every removal: snapshot `:757-762`, `props` list `:836-846`, `props` **item** `:820-826` (`safe_truncate`), `introspect` `:966-968`, error branch `:681-694`. `safe_truncate` (`:658-670`) avoids splitting UTF-8.

🔴 **The item-level cap (240 bytes) is the binding constraint for R1.** A byte-cut JSON fragment marked `truncated:true` is not parseable. Either grow the cap for table values, truncate **structurally** (drop trailing entries, re-encode), or the contract must say "read `truncated` first".

### How the server parses replies

- **One decode point**: `server/bridge/protocol.py:77-113` `decode_payload` (`@MX:ANCHOR` at `:69-75`). Raw JSON first, then percent-decode. No schema validation — a `v` whose content is JSON arrives as a string.
- Builders: `build_prop_query` `:279`, `build_props_query` `:286`, `build_introspect_query` `:245`, `build_state_query` `:219`. Request cap `MAX_PLUGIN_CALL_BYTES = 2048` at `:50` (comment `:33-49`: not the measured console limit).
- **Paging**: `server/rig/paging.py` `paged_children` `:82-102`; no-progress defence is the **`offset` echo** (`:97-99`); `claims_more` `:70-79`; `PAGE_CAP = 10` at `:57`. Docstring `:1-40`: `childCount 86` arrived as windows of 19 and 18 — **byte-bound, not count-bound**.
- Consumers: `server/web/presets_api.py:219-222`, `server/web/session.py`.

### Implicit contracts / side effects

1. **Read-only boundary**: `copilot_responder.lua:294-297` — function-valued fields are never invoked. A table serializer must not call `__index`/`__tostring` metamethods. Everything runs under `pcall`.
2. **The responder never interprets** (`PROTOCOL.md:315-317`, `:388-390`). A table-shaped value must stay a **string containing JSON** (contract-preserving) or gain a new sibling field (PROTOCOL revision).
3. **Determinism**: `json_encode` sorts object keys (`:157`); array serialization must use `ipairs` or explicit order.
4. **Recursion**: `json_encode` has **no depth limit and no cycle detection** (`:133-166`). A self-referential console table would hang the responder inside the operator's show. Depth cap + visited set are non-optional.

### The 1.6.3 changelog block

`copilot_responder.lua:52-84` — comment block above `VERSION = "1.6.3"` (`:82`), `PROTO = 1` (`:83`). Entries `-- <ver>: <what> (<ticket>)` + additivity note. A 1.6.4 entry appends and bumps `:82`; pins to update: `server/tests/test_lua_responder.py:81`, `test_responder_deploy.py:177`, `test_responder_roundtrip.py:125,128,136`, digest map `test_overlap_preserve.py:229-232`.

### Tests covering this area

- `server/tests/test_lua_responder.py` — 102 tests; runs the **real** `.lua` under lupa via `server/tests/lua_mock_env.py` (`__NODE` with `Get`/`PropertyCount`/`PropertyName`/`PropertyType` at `:50-83`).
- `test_lua_responder_payload_budget.py` — parses `CONFIG.max_payload` from source (`:26-31`), asserts encoded payload + `SendOSC` wrapper ≤ 2048.
- `test_responder_protocol.py` (55), `test_introspect_paging_stack.py`, `test_state_paging_callsite.py`, `test_truncate_disclosure.py`, `test_overlap_preserve.py` (governance).

### Risks

- The mock `__NODE:Get` can plant a table and prove serialization offline, but the **real shape** of `SELECTIONDATA`/`DEPENDENCIES` is listed under 안 잰 것 (`console-channel-facts.md:121`). Offline tests will pass on a shape nobody has observed.
- A serialized selection over 86 fixtures will exceed both 240 and 1900. R1 may ship a mechanism whose every real answer is truncated.

---

## R2 — Preset value readback (colour RGB / kelvin, dimmer %)

### What the console answers today: name and occupancy only

Read path `GET /api/presets/{pool_no}` in `server/web/presets_api.py:224-286`: one `query_state` on `DataPool/PresetPools/<no>` (`:236`), paged (`:253`), mapped to **`no` and `name`, nothing else**. Pool path `DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]` at `server/orchestrator/tools.py:345`.

**The colour a user sees in the popup does not come from the console.** `presets_api.py:76-84`: "The console does NOT expose a preset's colour (Appearance/Color props answered "not readable", live-probed 2026-08-16), so the ONLY honest colour source is the palette the app itself stored." App-side reconstruction: `_palette_hex_by_label` (`:70-88`), `_phaser_hexes_by_label` (`:91-108`), `_combo_phaser_hexes_by_label` (`:111-133`), `_dimmer_hex_by_label` (`:136-155`), joined **by name, scoped by pool** in `_with_swatches` (`:179-211`).

`server/web/cue_monitor.py:145-165` `_cue_items` is the same on the cue axis: `no`, `name`, `cueNo` — never a value.

### What the object model says

`server/rulebook/assets/v2.4.2/10_object_model.md:18-20`: Preset = stored attribute values by family. No property named that exposes the map.

Live probes exhaust the obvious candidates — all `property not readable`:
- `docs/research/ma3-effects/08-color-phaser-m0-probe.md:264-268` — `StepCount`, `Steps`
- `10-combo-phaser-m0-probe.md:67-75` — `Dimmer`, `ColorRGB_R`, `FeatureCount`, `Features`
- `13-phaser-assumption-verify-probe.md:45,155-158` — `TRANSITION`/`ACCEL`/`DECEL`/`PHASE`
- `04-programmatic-phasers.md:148` — `Phase`/`Speed`

🔴 **The `introspect` measurement that would settle it is incomplete.** `test_overlap_preserve.py:180-186` records t95: a preset object answered **138 properties, 27 fit one reply**. Paging (1.6.2) now reaches the other 111, but nobody has re-run the full enumeration against a preset and `props`-read the names. `PROTOCOL.md:359-361`: "Paging opens the NAME list; it says nothing about readability."

The structurally analogous positive result is the Part layer (`console-channel-facts.md:83-95`): `PRESETDATA`/`REFERENCES` answer `""`, while `SELECTIONDATA`/`DEPENDENCIES` answer a table address. **If a preset carries an equivalent table-valued property, R1 is the mechanism that unlocks R2** — R2 is downstream of R1.

### Where `unverified: ["value_match"]` is produced, and who reads it

| site | field |
|---|---|
| `server/lxseq/preset_mapper.py:134-135` | default `unverified = ("value_match",)`, reason `_VALUE_MATCH_REASON` (`:64-68`) |
| `preset_mapper.py:307-311` | live branch; appends `NAME_COLLISION_UNVERIFIED`; threaded `:353-354`, `:374-375` |
| `server/lxseq/cue_mapper.py:478-479, 885-889, 977-978` | cue twin — `("value_match", "tracked_value")` |

Consumers: `server/orchestrator/tools.py:5136-5137` (`import_lxseq_presets` payload), `:5864-5865` (cue tool), `server/tools/lxseq_pos_e2e.py:264-265`, `groupgen_e2e.py:239`. `server/lxseq/mapper.py:251-255` refuses on `fixture_type_untranslated` (R4 axis).

`_already_present_from` (`preset_mapper.py:170-177`): 「이미 있음」은 「맞게 있음」이 아니다.

### The exact seam for R2

- **Server-side**: `presets_api.py:265-285` (`read_pool` return, where `values` would sit) fed by a new `props`/`introspect` round trip. The router holds a **`PoolStatePort` only** (`:44-54`); adding a property port to `PresetsDeps` (`:57-67`) is the injection point.
- **Verification-side**: `preset_mapper.py:307-311` — `unverified` drops `"value_match"` only when a read-back confirmed the value. Compare against the **converted** values the app wrote: `col_rgb_percents` (`preset_parser.py:521`), `dim_level_percent` (`:346`), `kelvin_to_rgb` (`:419`); kelvin approximation disclosure `tools.py:1786-1807`.

### Tests

`test_web_presets_api.py` (29), `test_web_cue_monitor.py` (51), `test_lxseq_preset_mapper.py` (`:239-241`, `:443`, `:445-448` pin `value_match`), `test_lxseq_preset_tool.py:230-231`, `test_lxseq_preset_value_path.py:113`, `test_lxseq_preset_kelvin.py`, `test_lxseq_preset_col_scale.py`, `test_presets_store.py`.

### Risks

- Removing `"value_match"` is a **claim escalation**; the three pinned tests are the tripwire and should stay red until a live read is in hand.
- The palette-swatch layer becomes a second, weaker source of truth the moment a real value read exists.

---

## R3 — Runtime responder version gate

### How `ping` is issued and parsed

- Wire: `build_ping` `server/bridge/protocol.py:213-217` → `Plugin "CopilotResponder" "ping <id>"`; reply `kind=pong`.
- Responder: `M.build_pong` `copilot_responder.lua:645-654` — carries `plugin`, **`version = M.VERSION`**, `proto`. Contract `PROTOCOL.md:180-186`.
- 🔴 **Runtime discards the version.** `ConsoleLink.ping` at `server/safety/console.py:297-306` returns `bool`; the decoded payload with `version` is dropped at `:305-306`. **The version already arrives on every heartbeat and nothing reads it.**

Only two readers: `server/preshow/osc_check.py:106` (cosmetic detail string) and `server/tools/responder_roundtrip.py:140-163` `_check_expected_version` (CLI `--expect-version` at `:297`; docstring `:141-148` records the 2026-07-24 observation that re-import over a same-named plugin did not refresh the source).

### Where offline / degraded status is computed and surfaced

- State machine `server/safety/monitor.py:25-72`: `ONLINE`/`CONSOLE_OFFLINE`/`RESPONDER_DEGRADED` (`:28-30`); `executions_blocked` `:47-50`; `note_ping_success` `:58-61`; `_classify_silence` `:71-76`.
- Gate: `SafetyGate.heartbeat` `server/safety/gate.py:209-221`; `status` `:200-202`.
- **The block path to reuse**: `SafetyGate._check_health` `gate.py:415-437` — runs first (`:323-325`), audits via `_audit.log_blocked` (`:430-431`), returns `ScreenDecision(cleared=False, status="blocked_console_offline"|"blocked_responder_degraded")`. Send-time re-check `:546-557`, `:613`.
- Surface: `server/web/session.py:3996-4009` `status_snapshot` → `status_event`; pushed on connect (`app.py:447`), on change (`:381-384`, `:255`), on request (`:751-752`); `GET /healthz` `app.py:328-331`. Protocol `server/web/PROTOCOL.md:57`, `:329-339`.
- Korean labels: `ui/src/protocol.ts:1190-1194`, guidance `:1202-1207`, `:1218-1221`; pinned by `ui/src/protocol.test.ts:185-260`.

### The exact seam

1. `console.py:297-306` — retain `version` on the link (`last_pong_version` attribute). `ConsolePort.ping() -> bool` (`:165-175`) — widening ripples into every `FakeConsole` (`test_safety_gate.py:49-52`); an attribute is cheaper.
2. A new health verdict keyed on mismatch. Reusing `RESPONDER_DEGRADED` gets block+audit+banner free but lies about the cause; a fourth state is honest but ripples into `protocol.ts:1190-1207`, `PROTOCOL.md:57`, `protocol.test.ts`.
3. `_check_health` `gate.py:415-437` — add the branch there to inherit audit record and `ScreenDecision` shape.

### The live-1.6.1 / main-1.6.2 precedent

`test_overlap_preserve.py:220-228`: "Deployment is confirmed BY VERSION — `ping` must answer 1.6.3; a rig answering 1.6.2 does not carry the aliases whatever main contains (this repo has the live-1.6.1 / main-1.6.2 precedent)." Earlier occurrences `:172-179`, `:188-192`. Single source for expected version: **none** — `"1.6.3"` exists only as test literals. R3 must create the constant, pinned against `copilot_responder.lua:82`.

### Tests

`test_responder_roundtrip.py` (16), `test_safety_lock_monitor.py` (11), `test_safety_gate.py`, `test_deploy_health_ux.py`, `test_web_app.py`, `test_web_session.py`, `test_preshow_osc_check.py`, `ui/src/protocol.test.ts:185-260`.

### Risks

- A blunt version gate turns a cosmetic mismatch into a hard stop mid-show. Distinguish "rig older than expected" from "unrecognised version"; consider blocking only verbs whose contract changed.
- The gate fires only after a successful ping; it is strictly downstream of the offline block and must not shadow it.

---

## R4 — FixtureType handle→name translation for `precheck_vectorworks_diff` and `build_patch_sheet`

### The gap (README.md:289-302)

Closed half: `import_lxseq_patch` translates slot→name before the `already_patched` comparison (offline-only, not re-verified). Open half: VWX diff counts by type string (every type reports 0) and the patch sheet prints the handle verbatim.

### The existing translation, end to end

1. **Read the table** — `read_fixture_type_names(reader, *, root)` `server/prechk/mode_read.py:138-175` → `TypeNameRead` (`:78-135`), `by_slot()` `:122-135`.
2. **Translate one value** — `translate_fixture_type` `server/prechk/inventory.py:147-181`; `HANDLE_TEXT = ^FixtureType (\d+)$` at `:110`; non-handle values pass unchanged (`:170-172`); five untranslated reasons `:139-144`.
3. **Apply across inventory** — `_name_handle_types(records, type_names)` `inventory.py:457-522`. Takes the **read**, not the mapping (`:462-469`). Performs **no read of its own** (`:471-476` — "query-budget guard as ratified").
4. **Entry point** — `read_inventory(port, policy=None, *, type_names=None)` `inventory.py:529-537`, calls `_name_handle_types` at `:658`. **The kwarg already exists.** Fields `FixtureRecord.fixture_type` `:292`, `fixture_type_untranslated` `:305`.

### The one caller that supplies the table

`import_lxseq_patch` `server/orchestrator/tools.py:6339-6355`: `types_root = rig_paths.get("fixture_types")` (`:6327`, → `"Patch/FixtureTypes"` `:342`) → `read_fixture_type_names` → `read_inventory(..., type_names=type_names)`. `None`-vs-`TypeNameRead(attempted=False)` distinction at `:6346-6350`. Reaches `already_patched` via `occupants_from_patch_values` (`:6367-6369`) → `_occupancy_skip` `server/lxseq/mapper.py:371-421` (comparison `:399`).

### The two untranslated consumers

**(a) VWX diff** — `precheck_vectorworks_diff` `tools.py:3182`; call `:3206` `read_inventory(_InventoryPort(state_port, property_port))` **without `type_names=`** → `compare_vectorworks_rig` `:3238` → `server/vwx/diff.py:117`; `_console_rows` `:108-115`; histogram `:171-175`; `fuzzy_type_equal` `:181-184` → `console_count` 0 at `:185-187` → `QuantityMismatchEntry` `:188-194`. Also defeats the per-address `found` check `:148`.

**(b) Patch sheet** — `build_patch_sheet(port, *, policy=None, walk=None)` `server/paperwork/data.py:83-140`; call `:102` `read_inventory(port, policy)` without `type_names=`; rows `:114-124`, `fixture_type=` `:120`; `PatchRow.fixture_type` `:54`; rendered raw `server/paperwork/render.py:87`. Consumers: `server/web/paperwork_api.py:59,145`, tools.py sheet tool, `server/paperwork/bundle.py`.

### Where the table can be injected

- **(a)**: `tools.py:3206` becomes the two lines at `:6351-6355`. One extra `query_state` per call. **Nothing in `server/prechk/` or `server/vwx/` changes.** The same omission exists at `tools.py:3014` (`precheck_patch`), `:3397` (`apply_vectorworks_patch`), `:4039`, `:4433`, `:4624` — **six call sites**, one correct at `:6353`. Audit as one set.
- **(b)**: add `type_names: TypeNameRead | None = None` to `build_patch_sheet` and forward at `:102`; pushes the read onto callers (`paperwork_api.py:145`, `bundle.py`, tools.py), consistent with the ratified no-read rule. Letting `build_patch_sheet` read the tree itself violates that rule.
- **Rendering**: `render.py:87` should surface `fixture_type_untranslated`, or the print boundary discards the honesty the read boundary bought.

### Tests

`test_prechk_handle_types.py` (AC-PARITY-007..010), `test_prechk_inventory.py` (65), `test_lxseq_tool.py:492-506, :555`, `test_lxseq_mapper.py:401-415`, `test_vwx_diff.py` (13), `test_vwx_typegap.py`, `test_vwx_tool.py`, `test_paperwork_patch_sheet.py` (18), `test_paperwork_boundary.py`, `test_web_paperwork_api.py`, `test_address_verdict_parity.py`.

### Risks

- The handle **form** is an assumption (`inventory.py:100-111`); an unseen third form passes through unmarked (`:497-502`). Fixing consumers does not close that.
- Each fixed consumer costs one more `query_state` on a budget-guarded path.

---

## Risks and open questions

**R1.** Shipping a serializer whose every real answer is truncated (`max_prop_value = 240`, `max_payload = 1900`); a byte-cut JSON fragment is unparseable. Encoder has no depth limit / cycle detection (`:133-166`) — a self-referential table hangs the responder in the operator's show; array heuristic (`:146`) drops keys. Shape of `SELECTIONDATA`/`DEPENDENCIES` unmeasured (`console-channel-facts.md:121`). Open: `v` stays a JSON string, or a structured sibling field (PROTOCOL §4.6/§4.8 revision + second digest re-pin)?

**R2.** Claim escalation: dropping `"value_match"` converts 「무언가 저장됐다」 into 「검증됨」. Four live probes refused every guessed value property; paging a name into view does not make it readable. Open: does a preset carry a table-valued property analogous to `SELECTIONDATA`? If yes, R2 is downstream of R1; if no, R2 has no console-side answer and must be scoped to *disclosure*. Secondary: the swatch layer becomes a competing source of truth.

**R3.** The gate can block a show; `_check_health` is all-or-nothing ahead of grammar. Strictly downstream of the offline block. Widening `ConsolePort.ping()` ripples into every fake. Open: own health state (UI+PROTOCOL ripple) or reuse `responder_degraded`? Single source of expected version?

**R4.** Corrects two of at least six `read_inventory` call sites (`tools.py:3014, 3206, 3397, 4039, 4433, 4624` vs `:6353`). Handle-form assumption survives. Open: `build_patch_sheet` takes `type_names` (read pushed to four callers) or reads itself? Does `render.py:87` surface `fixture_type_untranslated`?

---

## Recommended approach

**R1 — serialize at `safe_property`, defensively, and pay the version bump once.** One seam: `copilot_responder.lua:290-308`, a `type(value) == "table"` branch returning `M.json_encode`d text with `t = "table"` kept. Harden the encoder first — depth cap, visited-set cycle detection, explicit array-vs-object decision; never invoke metamethods. Truncate table values **structurally** so `v` stays parseable; raise `max_prop_value` only as far as `test_lua_responder_payload_budget.py`'s 2048 arithmetic allows. Ship as 1.6.4: changelog block `:52-84`, bump `:82`, update `PROTOCOL.md` §4.6/§4.8, re-pin both digests in `test_overlap_preserve.py:229-232` with a dated grant, update four version literals. Prove offline by planting a table in `lua_mock_env.py`'s `__NODE._props`; then spend the single approved re-import (confirmed by `--expect-version 1.6.4`) and re-run a read-only probe against a real Part to record the actual `SELECTIONDATA` shape in `console-channel-facts.md §4`.

**R2 — measure before you promise; disclose either way.** Do not touch `unverified` first. Run a read-only `introspect` sweep over a preset object with 1.6.2 paging (138 names), then `props`-read every plausible name and record the outcome — including the negative — as a research note beside `docs/research/ma3-effects/`. Only if a table-valued property appears, widen `PresetsDeps` with a `PropertyQueryPort` and return values beside `presets` at `presets_api.py:265-285`, keeping the "never invented" rule. Only when a live read-back compares against the *converted* RGB and dimmer percent may `"value_match"` leave `preset_mapper.py:307`; update the three pinned tests in the same commit. If the sweep finds nothing, close R2 as *measured-absent* and strengthen `unverified_reason` prose.

**R3 — retain what already arrives, then reuse the existing block.** Stop discarding `version` at `console.py:305-306`; store as an attribute on `ConsoleLink`. Define one expected-version constant pinned against `copilot_responder.lua:82`. Add a fourth branch to `_check_health` (`gate.py:415-437`) inheriting audit, `ScreenDecision`, send-time re-check, and the status frame. Own status string + Korean label beside `protocol.ts:1190-1194` ("re-import the responder" is a different operator action). Zero console writes.

**R4 — pass the kwarg that already exists, and audit the whole set.** `tools.py:3206` becomes the two lines at `:6351-6355`. Add `type_names` to `build_patch_sheet` (`data.py:83`) and forward at `:102`, pushing the read to callers; make `render.py:87` render `fixture_type_untranslated` visibly. Audit and fix the four sibling omissions (`:3014, 3397, 4039, 4433, 4624`) as one set. All offline; zero console writes.
