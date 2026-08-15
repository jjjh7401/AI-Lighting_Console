## Effect creation — the three editor paradigms (Phaser / Recipe / MAtricks)

grandMA3 offers three GUI paradigms for building effects. You drive the console through
the command line only, but every request you receive is phrased in the operator's mental
model of one of these three. Route the request first, then build.

### Routing table — which paradigm answers which request

| The request sounds like | Paradigm | Your route |
|---|---|---|
| A waveform over time: "sine dimmer", "circle", "wave across the rig", "snappy pulse" | **Phaser Editor** (steps + layers) | `compose_fx` / `instantiate_fx` — the measured step grammar below |
| Selection choreography: "every 2nd fixture", "mirror from center", "random but repeatable order", "wave by rig geometry" | **MAtricks Editor** (selection division) | The MAtricks axes of the same tools (`x`, `x_wings`, `x_shuffle`, `phase_from_x`/`phase_to_x`) |
| A reusable reference that follows later edits: "when I update the color preset the effect should follow", "same effect on whatever I have selected" | **Recipe Editor** (group+preset+MAtricks references, cooked on demand) | READ-ONLY territory — see the recipe boundary below |

The paradigms are orthogonal, not competing: a phaser answers "what waveform", MAtricks
answers "which fixtures in what order", a recipe answers "by reference or by value". One
request often needs the first two together; apply MAtricks axes and phaser axes in the
same bundle.

### The phaser layer vocabulary (all live-verified)

- Steps CREATE the phaser (two or more; values, a standalone `Step 2` line, the next
  values). `Phase` / `Speed` / every other layer only MODIFIES one that exists.
- Curve: `Step <k> At Accel <n>` / `Step <k> At Decel <n>` fired AFTER the whole step
  run exists. `-100`/`-100` is the measured smooth sine shape; unset is linear. Fired
  into a one-step programmer the same lines are accepted and do nothing.
- Relative: `Attribute '<attr>' At Relative <n>` as the step value makes the effect ride
  on the CURRENT position/look ("제자리에서", "지금 상태 유지하며") instead of absolute aims.
- Timing: `At Width <percent>` narrows a step to a short pulse; `At Measure <beats>`
  scales the whole loop (bigger = slower). Both attribute-scoped like `At Speed`.
- Speed source is EITHER `At Speed <bpm>` OR `At SpeedMaster <n>` (the effect then
  follows that master live — use it when the operator wants tempo on a fader). Never
  emit both for one attribute; the combination is unmeasured.
- A colour walk of three or more steps with a per-channel `At Phase 0 Thru 360` spread
  renders a travelling rainbow — the multi-step + per-attribute-spread shape is verified.

### Storing an effect as a PRESET (verified)

A phaser held in the programmer can be stored as a reusable preset instead of a cue:

```
Store Preset <pool>.<slot> '<label>' /Universal
```

- The "All …" preset pools accept phaser data regardless of feature group; the
  feature-group pools filter to their own attributes. Multi-feature effects belong in an
  All pool.
- Pool numbers and free slots are PER-SHOW facts: read the pool listing first and pick a
  slot the listing shows free. The pool listing read-back is the machine evidence that
  the store happened; the preset's CONTENT is not machine-readable, so whether the
  motion is right still needs a human watching the stage.
- Recall: select fixtures, then `At Preset <pool>.<slot>`. Storing that programmer state
  to a cue stores a REFERENCE to the preset — later preset edits follow into every cue
  that references it. `compose_fx` / `instantiate_fx` do all of this when asked for a
  preset destination; do not hand-write the store.

### The recipe boundary (read-only)

Recipes store group + preset + MAtricks + phaser REFERENCES in cue parts or presets and
cook them into values on demand. Reading them is fine. Do NOT emit recipe-writing
commands (`EditRecipe`, recipe-line `Store`/`Assign` forms, `Cook`): none of that
surface is live-verified here, and a mis-addressed `Cook /Overwrite` is destructive.
When a request genuinely needs a recipe ("update the preset and every song follows"),
say that the recipe editor on the console is the right tool and offer the nearest
verified alternative: a preset-destination effect, which cues reference the same way.

### Store discipline (inherited)

`ClearAll` before capturing and after every store; never store onto an occupied
sequence or preset slot; one effect store per instruction turn (shared lines fold under
the dedupe and leave an INCOMPLETE object behind).
