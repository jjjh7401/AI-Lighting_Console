# Design Direction — 연출 컨트롤 패널 (SPEC-COPILOT-SHOWUI-001)

Frontend/UX design exploration artifact. No implementation code here — direction only.
Source context: `ui/src/App.tsx`, `ui/src/styles.css`, `interview.md` (clarity 8/10).

---

## 1. Intent Statement

**Who is this human?**
A lighting operator (조명 오퍼레이터) running a live show on grandMA3 onPC, standing at
front-of-house in a dark room. One hand may be on the real console; the other reaches for
this app. They think in console vocabulary — sequence, executor, cue, look — not in web-app
vocabulary. They are under time pressure: the band is already playing, the MC is already
talking. A mis-fire (wrong look, blackout at the wrong moment) is visible to an entire
audience and cannot be undone.

**What must they accomplish?**
Fire and stop AI-generated looks/effects/cue sequences — plus the console's own sequences —
with **one glance and one press**, without typing, without reading paragraphs, without
hunting through chat history. Secondary: pin a chat-born 연출 to the panel ("패널에 추가")
so it becomes a stable, named, repeatable control.

**What should this feel like?**
Like an extension of the console's executor wing, not like a web dashboard. Solid, dark,
quiet at rest; loud only where something is *live*. Every control answers three questions
before it is pressed: *What will this do? Is it running now? How do I stop it?*
The feeling to aim for: **"버튼을 믿고 누를 수 있다"** — trust under pressure.

---

## 2. Domain Concepts (lighting-console vocabulary the UI must speak)

| Concept | Console meaning | UI translation |
|---|---|---|
| **Executor (익스큐터)** | A physical button/fader slot that a sequence is assigned to; the operator's muscle-memory unit | Each panel item IS an executor-style tile: fixed grid position, big press target, label + number. Position stability matters more than sorting cleverness — items must not reflow mid-show. |
| **Cue / Sequence (큐/시퀀스)** | Ordered list of states; `Go`, `Pause`, `Off` are distinct verbs | Sequence tiles expose console verbs (`Go+`, `Off`), never generic "재생/정지" media metaphors. Show current cue number on running sequences. |
| **Look (룩)** | A static stage picture (color + position + beam) recalled instantly | Look tiles are one-shot recalls: press = apply. Visually flat/static (no motion affordance) to distinguish from effects. |
| **Phaser / Pager (페이저)** | MA3's effect engine — continuously running modulation (circles, dimmer waves, infinite loops) | Effect tiles carry a subtle motion cue (e.g. animated underline only while running) and MUST have an always-visible stop affordance — a running phaser never stops by itself. |
| **MAtricks (엠에이트릭스)** | Grouping/odd-even/wing tools that spread an effect across fixtures | Not a top-level control; surfaces as a badge/parameter chip on a tile ("Odd/Even", "Wings 2") so the operator knows *how* the effect is spread. |
| **Grand Master / Speed Master (그랜드마스터)** | Global fader scaling all output; speed masters scale effect rate | The panel's fader vocabulary: vertical faders with 0–100 scale marks, value readout at thumb, touch-friendly height. Faders map to master/rate — not to arbitrary web sliders. |
| **Off / Release (오프)** | Explicit removal of a playback's contribution; the opposite of Go | "정지" is a first-class, always-reachable action — a global **All Off** control in a fixed corner, plus per-tile Off. Stop must never be buried in a menu. |
| **Appearance color (어피어런스)** | MA3 lets each pool object carry a color swatch for recognition | Each tile carries a color chip derived from its dominant look color — recognition by color before reading text, exactly like a real console pool. |

## 3. Color World (dark-theme console aesthetics)

Extend the existing tokens (`--bg #14161a`, `--panel #1e2128`, `--accent #4f8cff`,
`--ok #3fb950`, `--warn #d29922`, `--bad #f85149`) — do not replace them.

| Entry | Value direction | Role |
|---|---|---|
| **Console black** | keep `#14161a` base, panel wells slightly deeper (`#101216`) | Panel background sits *below* chat surface — a recessed hardware well, not a card. |
| **Live amber** | `#ffb02e` family (hotter than `--warn`) | The single "this is RUNNING" color. Reserved exclusively for active playback state (tile border/underline, running badge). Nothing decorative may use it. |
| **Go green** | reuse `--ok #3fb950` | Momentary press/confirm feedback only — flashes on fire, does not persist. |
| **Stop red** | reuse `--bad #f85149` | Off/All-Off controls and destructive stops only. Never used for "error text" inside the panel to avoid diluting its meaning. |
| **Appearance chips** | full-saturation stage colors (cyan `#00c8ff`, magenta `#ff3fa4`, warm white `#ffd9a0`, UV `#7a5cff`, …) rendered as small emissive chips with a faint glow | Tile identity color = what the look actually puts on stage. The only place saturated color appears at rest. |
| **Dimmed rest state** | text `--muted #9aa0a6`, tile chrome `#2b2f36` 1px lines | At rest the panel is nearly monochrome — dark-adapted eyes are not blasted; color = information, not decoration. |

Contrast rule: everything readable at arm's length in a dark FOH booth — minimum 15px labels
in the panel, state never conveyed by color alone (badge text `RUN`/`OFF` accompanies color).

## 4. Signature Element

**The "Live Rail" tile (라이브 레일 타일).**
Every panel tile — look, effect, sequence — shares one anatomy: appearance color chip (left
edge, full height, emissive), name + type badge, and a **bottom rail** that is the tile's
state voice: dark at rest, animated live-amber sweep while running (sweep speed loosely
follows effect rate for phasers), solid amber for held static looks, and it doubles as the
press-progress indicator for the 2-step arm→fire pattern on destructive actions. One element
carries identity, state, and safety — this rail is the panel's recognizable signature and
appears nowhere else in the app.

## 5. Defaults to Avoid (generic web-app patterns wrong here)

1. **Confirmation modals for firing.** A `window.confirm`-style dialog between operator and
   cue is a show-killer. Safety comes from the arm→fire rail pattern (destructive only:
   All Off, blackout-class looks) and clear state display — never from modal interrupts.
   Conversely, *stopping* must always be single-press, zero-step.
2. **Hover-revealed controls & tooltips as primary affordance.** Touch screens and gloved,
   hurried hands get no hover. Every action visible at rest; tooltips may add detail but
   never carry the only copy of critical info.
3. **Toast notifications for state changes.** A toast saying "시퀀스 41 실행됨" that fades
   after 3s is the opposite of console truth. State lives *on the tile itself*, persistently.
   (Errors from the console reply path may use the existing chat entry stream instead.)
4. **List reflow / auto-sorting.** Sorting tiles by "recently used" or alphabetically moves
   the operator's targets mid-show. Grid positions are stable; new items append; manual
   reorder only in an explicit edit mode.
5. **Media-player metaphors (▶ ⏸ ⏹ icons alone).** MA3 verbs are Go/Pause/Off with
   different semantics (Off releases output; Pause holds a phaser). Use console verb labels,
   optionally paired with icons — never bare transport icons.
6. **Light-theme or auto-theme switching.** The app is used in blackout conditions;
   `color-scheme: dark` is a hard commitment, not a preference.

## 6. Reference to .moai/design/system.md

`.moai/design/system.md` does not exist at time of writing. This document serves as the
seed design direction; if a project design system is later established, its tokens should
be extracted from §3 (Color World) and the existing `ui/src/styles.css` `:root` variables,
which this direction treats as the canonical base palette.
