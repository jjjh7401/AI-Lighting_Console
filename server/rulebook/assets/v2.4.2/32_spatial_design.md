## Spatial design — firing the rig in the ORDER it is hung

The choreography section sets VALUES on a selection. Spatial design decides what
that selection's ORDER is, so that "a wave from stage left" comes out different
on one long bar than on a three-row grid instead of identical on both. Every
command in this section was validated live on onPC 2.4.2.

### The principle — direction is selection order, not coordinates (measured)

A phaser fans its phase across the SELECTION, in selection order. MA3 has no
built-in "build a selection grid out of the rig's real positions", so the order
is what you have to build: read the patch coordinates, sort the fixture ids by a
stage axis, and utter the selection in that sorted order.

This was measured, not assumed. With the coordinates and every phaser line held
IDENTICAL, and only the selection chain reversed, the observed wave reversed
with it. So:

- A coordinate is an INPUT to the sort. It never appears in a programming
  command — there is no MA3 grammar that would accept one, and a wave aimed the
  wrong way looks like a working wave in every log.
- Reversing the chain is the whole reversal mechanism. Do not reach for a
  negative phase span to flip a spatial wave when the order can flip instead.

### Step 1 — read the positions: `get_spatial_context`

Fixture positions live in the patch, not in the rig snapshot, so
`get_rig_context` cannot answer this question. `get_spatial_context` returns one
entry per fixture — its real fixture id, its name and its three stage
coordinates — alongside the reads that failed and whether the answer was cut
short.

Three things in that reply change what you do next:

- A fixture that could not be read comes back in the UNREADABLE list, with a
  reason, instead of in the coordinate list. It is not a fixture sitting at the
  origin: do not put it in the chain, and do not fill a coordinate in for it.
- A truncated or round-trip-capped reply is a PARTIAL rig. A chain built from it
  has holes, so say the read was cut short rather than presenting the short
  chain as the whole rig.
- Every fixture reading the SAME point means the show is patched but was never
  positioned. That is a successful read, not a missing one, and there is no
  spatial order to be had from it — fall back to the non-spatial choreography
  patterns and say why, rather than sorting fixture ids and calling the result
  a wave from stage left.

### The sort vocabulary — four names, closed

| sort | order | Korean qualifiers |
|---|---|---|
| `left_to_right` | x ascending, within each detected row | 왼쪽에서 오른쪽(으로), 좌에서 우로 |
| `right_to_left` | x descending, within each detected row | 오른쪽에서 왼쪽(으로), 우측에서 좌측으로 |
| `center_out` | outward from each row's midpoint | 가운데부터 바깥으로, 센터에서 양옆으로 |
| `diagonal` | row order and within-row order combined into one sweeping wavefront | 대각선(으로), 사선 |

The list is closed. An instruction that names none of them is not a spatial
instruction — program it with the ordinary choreography patterns. An instruction
that names TWO ("대각선으로 왼쪽에서 오른쪽") has named none of them: ask which
one is meant instead of picking whichever was recognised first.

### Step 2 — the recipe: sort, select, phaser (validated)

```
ChangeDestination Root
ClearAll
Fixture <first fid> + Fixture <next fid> + ... + Fixture <last fid>
Attribute 'Dimmer' At 0
Step 2
Attribute 'Dimmer' At 100
Attribute 'Dimmer' At Phase 0 Thru 360
Attribute 'Dimmer' At Speed 30
ClearAll
```

- The chain is ADDITIVE and one `Fixture` keyword per element — `Fixture <a> +
  Fixture <b>`, never a `Thru` range. A range is a numeric span, and the order
  the sort computed is exactly what a span throws away.
- Every element of the chain is a real fixture id that came back from the read,
  and the elements stay in the order the sort returned them. Do not re-sort,
  de-duplicate or tidy the chain on the way out: the order IS the direction.
- The chain and the phaser are one bundle. Selection is programmer state, so it
  does not survive the closing `ClearAll` — a later bundle rebuilds the order
  rather than referring back to it.
- To reverse the wave, reverse the sort (`left_to_right` <-> `right_to_left`)
  and re-utter the chain. Nothing else in the bundle changes.

### A phaser needs TWO steps (measured)

The two dimmer lines either side of `Step 2` are not decoration. A phaser fans
phase ACROSS steps, so a single static value has nothing to fan.

Measured: a bundle that set one value and then applied `At Phase 0 Thru 360` to
it returned ok on every single line and left the stage lit and MOTIONLESS. Ok on
a phaser line means the line parsed, never that anything is moving. Always build
the low value, `Step 2`, then the high value, and only then spread the phase and
set the speed.

### What never reaches the command line

- Coordinates, in any form. They are the sort's input.
- A fixture id the read did not return.
- A double-quote character — this transport rejects it outright. MA3 attribute
  names go in SINGLE quotes, exactly as they do everywhere else in the rulebook.
