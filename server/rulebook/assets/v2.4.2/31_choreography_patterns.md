## Programming looks, cues & effects (choreography)

Patching CREATES fixtures (see the plugin-patterns section: Lua `AddFixtures`, the
console at the Patch destination, and NEVER a `ChangeDestination`). PROGRAMMING is the
opposite job: set values on already-patched fixtures and store them as looks, cues, and
effects. Programming is command-line work via `run_commands` (and Lua `Cmd()` when you
need loops or math). Every pattern below was validated live on onPC 2.4.2.

### CRITICAL — set the programming destination first

Before any programming command, issue exactly once at the start of the bundle:

```
ChangeDestination Root
```

Why: fixture selection (`Fixture 11 Thru 19`) returns **"Illegal object"** when the
console command line is still pointed at the Patch editor — the state it is left in right
after patching. `Root` is the programming context. This is the MIRROR of the patch rule:
patching needs the Patch destination and forbids `ChangeDestination`; programming needs
`Root`. `ChangeDestination Root` is harmless if already there, so prepend it whenever you
program. (This does NOT change the patch rule — a PATCH plugin still must not
`ChangeDestination`.)

### Selecting fixtures (validated)

- Range: `Fixture 11 Thru 19`  — bare keyword, works. Open range: `Fixture 11 Thru`.
- List / subtract: `Fixture 11 + 12 + 13`, `Fixture 11 Thru 19 - 15`
- Group recall selects its members: `Group 11`
- Do NOT prefix with `Select Fixture ...` or use `SelFix ...` — both returned
  "Illegal object" on 2.4.2. Use the bare `Fixture ...` / `Group ...` forms.

### Setting values (validated)

- Intensity: `Attribute 'Dimmer' At 80` (percent), or `At Full` (100) / `At 0`
- Color on RGB movers: `Attribute 'ColorRGB_R' At 100` (also `'ColorRGB_G'`, `'ColorRGB_B'`), 0–100
- Position: `Attribute 'Pan' At 20`, `Attribute 'Tilt' At -15` (percent); exact DMX aim =
  `Attribute 'Pan' At Absolute Decimal8 145` (0–255)
- Chain independent sets on ONE line with `;`: `Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 25`
- `ClearAll` before every fresh look AND after every `Store` — leftover programmer values
  TRACK into the next capture and silently corrupt the following cue.

### Build a look, store a cue (validated)

```
ChangeDestination Root
ClearAll
Group 11
Attribute 'Dimmer' At 80 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 25
Store Sequence 11 Cue 1 'Warm Wash' CueFade 2
ClearAll
```

- The sequence auto-creates on the first store. Add more cues to it:
  `Store Sequence 11 Cue 2 'Blue Wash' CueFade 2 /Merge`.
- Cue numbers carry decimals — insert between existing cues with `1.5`, `1.55`.
- Store flags: `/Merge` adds active attributes, `/Overwrite` replaces (DESTRUCTIVE → the
  safety gate routes it to human approval), `/Remove` subtracts the active attributes out
  of an existing cue, `/CueOnly` stops the change tracking into the next cue.

### Phasers (running effects) — validated command building

A phaser is a multi-step running effect. Build steps, then spread the phase and set speed:

```
ClearAll
Group 11
Attribute 'Pan' At Relative 30          # relative rides on top of the base aim
Attribute 'Pan' At Phase 0 Thru 360     # fan the phase across the selection => a wave
Attribute 'Pan' At Speed 60             # rate (BPM/Hz/sec per the phaser's Speed display)
Store Sequence 12 Cue 1 'Pan Sweep'
ClearAll
```

- Multi-step colors/dimmers: set a value, `Step 2`, set the next value, `Step 3`, etc.
- Sine dimmer curve: two steps, each `Step 1 At Accel -100` + `Step 1 At Decel -100`
  (repeat for `Step 2`).
- Circle / ballyhoo: run Pan and Tilt phasers of the same size 90° apart —
  `Attribute 'Pan' At Phase 0` + `Attribute 'Tilt' At Phase 90` (0°/180° = a diagonal line).
- Reverse the walk direction: `Attribute 'Pan' At Phase 0 Thru -360`.

### MAtricks — shape an effect across the selection (validated)

```
Set Selection MAtricks 'PhaseFromX' 0
Set Selection MAtricks 'PhaseToX' 360   # one wave across the X axis; auto-recalculates
Set Selection MAtricks 'X' 2            # act on every 2nd fixture
Set Selection MAtricks 'XWings' 2       # symmetric mirror from center
Set Selection MAtricks 'XShuffle' 1234  # seeded random order (same seed => same look)
Reset Selection MAtricks                # clear the sub-selection
```

Store a reusable config as a pool object: `Store MAtricks 1` then `Label MAtricks 1 'Wave'`;
recall it with `Call MAtricks 1`.

### Playback (validated)

```
Assign Sequence 11 At Executor 191      # bind the sequence to a playback fader/buttons
Go+ Executor 191                        # next cue   (Go- previous, Goto Cue 2 Sequence 11)
Off Executor 191                        # release the executor
```

Always address `Executor <n>` explicitly so "advance the show" is unambiguous.

### Self-running / auto-advance cues — validated form

Use the PROPERTY form (validated on 2.4.2):

```
Set Cue 1 Sequence 11 Property 'TrigType' 'Follow'   # Go / Time / Follow / Sound / BPM
Set Cue 1 Sequence 11 Property 'TrigTime' 4
```

Trigger tokens are Capitalized (`Follow`, not `follow`). Do NOT emit
`Assign Cue 1 Sequence 11 /trig=follow` — the `/trig=` option form returns "Illegal
object" on 2.4.2 (rejected the same way as the MA2-style `/cmd=`).

### Releasing / clearing (validated)

```
ClearAll                 # clear the whole programmer
Off Fixture 11 Thru 13   # release just these fixtures from the programmer
Off Sequence 11          # release a running sequence's stage output
Off Executor 191         # stop an executor
```

### Tracking model (important)

MA3 is a TRACKING console: a value stored in a cue tracks FORWARD into every later cue
until it is changed, blocked, or released — `ClearAll` between looks does NOT stop this.
To keep a change from tracking into the next cue, store it `/CueOnly`. To freeze a cue's
values against edits to earlier cues, `Block Sequence 11 Cue 5`; `Unblock` removes
redundant blocks.

### Generative choreography with a Lua plugin

When a look needs loops, math, or many computed cues (per-fixture colors, a BPM chase, a
whole cue bank), deploy a Lua plugin whose `main()` loops and calls `Cmd()` with the SAME
command strings you would type. Rules validated live:

- Begin `main()` with `Cmd("ChangeDestination Root")` (same destination rule).
- Write MA3 names in SINGLE quotes inside the DOUBLE-quoted Lua string:
  `Cmd("Attribute 'Dimmer' At 80")` — no escaping needed, never nest same-type quotes.
- A loop that steps values over TIME must `coroutine.yield(seconds)` between steps
  (seconds, fractional OK) or it freezes the single Lua engine. A short build loop that
  just stores cues does not need to yield.
- End with a final `Cmd("ClearAll")`.
- Deploy with `deploy_plugin(name, source)`, then run with `run_commands(["Plugin 'Name'"])`.

Example — an 8-cue rainbow bank, validated live (built Sequence 16, then bound it to an
executor):

```lua
local function main()
  Cmd("ChangeDestination Root")
  Cmd("ClearAll")
  for i = 1, 8 do
    local h = (i - 1) / 8
    local r = math.floor(math.max(0, math.cos(h * 2 * math.pi)) * 100)
    local g = math.floor(math.max(0, math.cos((h - 1/3) * 2 * math.pi)) * 100)
    local b = math.floor(math.max(0, math.cos((h - 2/3) * 2 * math.pi)) * 100)
    Cmd("Group 11")
    Cmd(string.format("Attribute 'ColorRGB_R' At %d ; Attribute 'ColorRGB_G' At %d ; Attribute 'ColorRGB_B' At %d", r, g, b))
    Cmd(string.format("Store Sequence 16 Cue %d 'Hue %d' /Overwrite /nc", i, i))
  end
  Cmd("ClearAll")
  Cmd("Assign Sequence 16 At Executor 193")
end
return main
```

### Concept / mood instructions — resolve the rig FIRST

When the instruction gives a MOOD or CONCEPT ("warm ballad", "energetic club", "eerie",
"sunrise build") instead of explicit fixtures / colors / ids, DO NOT guess object ids.
First call `get_rig_context` to see the ACTUAL patched fixtures and the existing groups /
presets, then design against those real objects:

- Select real targets only: recall an existing group by its EXACT listed name
  (`Group 'Copilot Movers'`) or by its listed number (`Group 11`) — for groups and
  preset pools that number IS the pool number you address.
- A fixture's number in `get_rig_context` is its SLOT in the stage patch list,
  NOT its fixture id, and `Fixture 11` addresses FID 11 — the two are equal only by
  coincidence. NEVER paste a fixture's rig-context number into a `Fixture ... Thru ...`
  range: MA3 accepts it silently and stores the look against whichever fixtures own
  those FIDs. Prefer a group. To address fixtures directly, first confirm the real
  FIDs — `query_state` on the stage patch entry (its `fid` property), or ask the
  operator — and only then write the range.
- NEVER invent a `Group 3` that `get_rig_context` did not list —
  a missing group selects nothing and the whole look stores empty.
- Then map the mood to values you already know how to set (dimmer / color / movement /
  speed), `Store` cues, and `Assign ... At Executor`. Remember `ChangeDestination Root` first.

Rough mood → design starting points (pick concrete numbers, then adjust):

| mood | dimmer | color (ColorRGB) | movement |
|---|---|---|---|
| warm / ballad / intimate | 40–70% | amber (R high, G low, B ~0) | none, or slow Tilt sway, Speed 10–20 |
| cool / calm / night | 30–60% | blue / cyan | slow, gentle |
| energetic / club / party | 80–100% | saturated, cycling (2-color chase or rainbow) | fast Pan/Tilt sweep or circle, Speed 90–180 |
| dramatic / build | rising across successive cues | deep color → white | accelerating |

Build it as one or more cues in a fresh sequence and put it on an executor so the operator
can run it. When the concept implies MULTIPLE looks (a build, a verse→chorus), store several
cues in the same sequence with sensible `CueFade` times.
