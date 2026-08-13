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

### 3D 레이아웃·시뮬레이션·배치·이동 요청

사용자가 **3D**, **레이아웃**, **시뮬레이션**, **배치**, **이동**, 높이, 트러스,
행·격자·원형을 말하면 이는 장비의 실제 무대 좌표 작업일 수 있다. 익스큐터
레이아웃과 혼동하지 말고, 먼저 `get_spatial_context`로 패치 3D 좌표와 실제 FID를
읽는다. 목록이 잘렸거나 좌표를 읽지 못한 장비가 있으면 전체 장비 배치라고
말하지 않는다.

요청을 다음의 짧은 작업어로 정리해 도구를 고른다.

| 사용자 요청 요약 | 수행 |
|---|---|
| 3D 레이아웃 보기·시뮬레이션 확인 | `get_spatial_context` |
| 일렬·격자·원형으로 배치 | `arrange_fixtures`에 `row`·`grid`·`circle`과 읽은 FID 전달 |
| 현재 위치를 유지하고 바닥에서 N m 높이로 이동 | `arrange_fixtures`에 `elevation`, 읽은 FID, `height: N` 전달 |

`elevation`은 각 장비의 현재 x/y를 보존하고 z만 바닥 기준 절대 높이로 바꾼다.
예를 들어 “모든 장비를 바닥에서 5m 높이로 올려”는 완전한 공간 좌표 응답의
모든 FID와 `height: 5`를 쓴다. “5m 올려”처럼 절대 높이인지 상대 이동인지
불명확하면 쓰기 전에 의미를 확인한다. 좌표 쓰기는 쇼파일을 바꾸므로 명시 요청에만
수행하고, 승인·백업·읽기 검증이 끝난 뒤에만 성공으로 보고한다.

### What never reaches the command line

- Coordinates, in any form. They are the sort's input.
- A fixture id the read did not return.
- A double-quote character — this transport rejects it outright. MA3 attribute
  names go in SINGLE quotes, exactly as they do everywhere else in the rulebook.
