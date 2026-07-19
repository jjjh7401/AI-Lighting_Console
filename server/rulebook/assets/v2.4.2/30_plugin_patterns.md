## Plugin patterns (patching + programming)

Some operations are command-line-only, some are Lua-plugin-only. Choose the
right tool:

- **Programming** (select fixtures, set values, store cues/groups/presets):
  command lines via `run_commands`. NO plugin needed.
- **Patching** (creating fixtures): Lua-only via `AddFixtures` — deploy a plugin
  with `deploy_plugin`, then run it with `run_commands`.

### Patching fixtures — AddFixtures (Lua plugin)

Command lines CANNOT create fixtures. The patch is exactly TWO steps, in order:

1. `deploy_plugin(name, lua_source)` — a plugin whose `main()` calls
   `AddFixtures`.
2. `run_commands(["Plugin 'YourName'"])` — the ONLY command in this call
   (single quotes — a double quote is rejected). NOTHING else.

CRITICAL — never touch the destination. Do NOT issue a `ChangeDestination` (or
`CD`) command at any point — not inside the plugin, and NOT via `run_commands`.
`AddFixtures` reads the console's CURRENT command destination, which is already
the patch fixtures layer (the prompt reads `…/Patch/Stages/Stage 1/Fixtures>`
because the user is in the Patch editor). A `ChangeDestination` command you send
either fails outright or moves the destination somewhere `AddFixtures` cannot
use — so an in-plugin OR a run_commands ChangeDestination makes the patch return
nil and create nothing. Just deploy the plugin and run `Plugin 'YourName'`; do
nothing about the destination. If a patch still adds no fixtures, tell the user
to open the Patch editor (Patch > Fixtures) first, then run it again.

`AddFixtures{...}` fields:
- `mode` (required): the DMX-mode handle, e.g.
  `Patch().FixtureTypes["Robin MMX Spot"].DMXModes["Mode 1"]`. Use bracket
  notation for names containing spaces; success returns non-nil, nil = failure.
- `amount` (required, integer), `fid` (string), `idtype = "Fixture"`,
  `name` (string).
- `patch` (optional): `{ "universe.address", ... }` e.g. `{ "1.101" }`. Space
  fixtures by the mode's DMX footprint so they do not overlap.

Example — patch 9 "Robin MMX Spot" (Mode 1) as FID 2..10 in universe 1:

```lua
local function main()
  local mode = Patch().FixtureTypes["Robin MMX Spot"].DMXModes["Mode 1"]
  local addr = 101
  for fid = 2, 10 do
    AddFixtures({ mode = mode, amount = 1, fid = tostring(fid),
      idtype = "Fixture", name = "MMX " .. fid, patch = { "1." .. addr } })
    addr = addr + 42
  end
end
return main
```

### Programming looks and cues (command lines)

Use `run_commands` for these — no plugin:
- Select: `Fixture 1 Thru 10`
- Dimmer: `At 100`
- Attributes (single-quote the name, never double-quote):
  `Attribute 'Pan' At 45`, `Attribute 'Tilt' At 60`, `Attribute 'ColorRGB_R' At 100`
- Store a cue: `Store Sequence 2 Cue 1`
- Clear the programmer: `Clear`
