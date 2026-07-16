# grandMA3 Object Model Summary (v2.4.2)

The console show file is an object tree. The objects you address in commands:

## Patch (rig definition)

- **Fixture** — a patched lighting instrument with a fixture id (`Fixture 101`).
  Fixtures have a FixtureType (Spot / Wash / Beam / conventional dimmer, etc.)
  and DMX address data.
- **FixtureType** — the library definition (attributes, wheels, channel layout).
- **Stage** — physical arrangement context for fixtures.

## DataPool (programming objects)

The default DataPool holds the objects created while programming:

- **Group** — a stored fixture selection (`Group 3`). The fastest way to select.
- **Preset** — stored attribute values, organized in pools by attribute family:
  Dimmer, Position, Gobo, Color, Beam, Focus, Control, Shapers, Video, All.
  Addressed as `Preset <pool>.<slot>` (e.g. `Preset 4.1` = Color pool slot 1).
- **Sequence** — an ordered list of **Cue** objects with timing and tracking.
  Cues are addressed inside their sequence: `Cue 5 Sequence 2`.
- **Executor** — a playback handle (fader/button) on a **Page**, addressed as
  `Page <page>.<executor>` (e.g. `Page 1.201`). Sequences are assigned to
  executors for live playback.
- **Macro** — a stored list of command lines (`Macro 3`).
- **Plugin** — a Lua plugin object (`Plugin 'CopilotResponder'`).

## Programmer

The programmer is the live editing buffer: selecting fixtures and setting values
happens there first; `Store` writes programmer content into objects; `Clear` /
`ClearAll` empty it. Values in the programmer have priority over playback until
cleared.

## Attribute families (for presets and value commands)

- Dimmer (intensity), Position (pan/tilt), Color (mix/wheels, CTC color
  temperature), Gobo (wheels), Beam (iris/prism/frost), Focus (zoom/focus),
  Shapers (framing), Control (lamp/reset).
