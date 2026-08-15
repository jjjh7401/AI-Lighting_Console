# SONGSTD M2 (R1c director-interview + R4 position/dimmer) — Read-only Feasibility Report

Scope: SPEC-COPILOT-SONGSTD-001, branch `feature/song-design-standard`. M1 (R1/R1b/R2/R3) is
already implemented and merged locally (acceptance.md M1 all checked). This report inspects
what M2 needs to build on top of it. No source files were edited for this report.

## Verdict

**No hard blocker. M2 can be safely implemented now.** Every primitive R1c+R4 need already
exists: the question-card protocol natively carries "N options + free text", the sequential
one-card-at-a-time pattern is inherent to the existing blocking `_ask_one` helper (already used
twice per turn in `_position_cue_sheet` today), and M1's `server/design/profile.py` ships a
`DirectorOverride` dataclass + `resolve_section(..., director_intent=...)` priority chain that is
explicitly documented as "M1's hook for the M2 연출 인터뷰 (interview.py, R1c)". The real work is
wiring, not inventing new mechanism. Three design decisions (not blockers) are flagged below and
should be resolved before/at kickoff.

## 1. Question-card protocol (R1c "3 suggested options + free text")

- `ui/src/components/QuestionCard.tsx` — renders `question.options[]` as buttons (label +
  optional description) AND always renders a free-text form regardless of whether options exist
  (`question-freeform`, lines 56-76). Both paths call the same `onAnswer(request_id, answer)`.
  **This already is exactly "3 options + free text" — no UI/protocol change needed.**
- `ui/src/protocol.ts:624-630` — `PendingQuestion { request_id, prompt, why, steps, options: {label,
  description}[] }`. No `free_text_allowed` flag exists because free text is unconditional.
- `server/web/question.py` — `QuestionOption(label, description)`, `QuestionRequest(prompt, why,
  steps, options)`, `QuestionChannel.ask(request, session_key=...) -> str` (blocks the calling
  worker thread until `.resolve(request_id, answer=...)` from the websocket handler, or times out
  to `UNANSWERED`). `resolve()` accepts **any** string — a button label or hand-typed text are
  indistinguishable on the wire, which is exactly DI3's "자유 입력은 1급" requirement satisfied by
  construction.
- `server/web/session.py:2090-2118` — `Session._ask_one(prompt, *, options=(), why="", steps=())
  -> str | None`. Returns `None` on no-UI/unanswered/empty, else the raw answer string. This is the
  card-issuing primitive every existing question-driven handler in this file already uses.

**Sequential-one-at-a-time is not something to build — it already exists.** `_ask_one` is a
blocking call; a handler that needs N decisions calls it N times in a row, and each call must
return before the next fires. `_position_cue_sheet` (server/web/session.py:1233-1382) already does
this exact thing twice (sequence_no ask at 1280-1295, then preset_start ask at 1300-1319) — the
5-card interview is a direct extension of an established idiom, not a new pattern.

**Skip-if-pre-specified is also an established idiom**, reusable verbatim for R1c's "지시문에
이미 답이 명시된 문항은 카드 생략" clause: at session.py:1276-1319 the sequence number and preset
start are each resolved via `<regex>.search(text)` first, and the question card is issued only in
the `else` branch when the regex found nothing.

## 2. M1's director-override hook (`server/design/profile.py`)

- `DirectorOverride(d_level: int|None, color_tendency: str|None, position_candidates:
  tuple[str,...]|None)` with `.is_complete()` — lines 315-339. Docstring explicitly: *"This is
  M1's hook for the M2 연출 인터뷰 (interview.py, R1c), not that interview itself."*
- `resolve_section(mood_text, profile, *, director_intent=None) -> SectionMoodResolution |
  UnresolvedMood` — lines 424-511. Priority chain per axis: director_intent > section mood-word >
  concept > genre > global default, exactly matching spec.md's "감독 답변 > 구간 무드 > 컨셉 >
  장르 > 전역 기본값" (M2 + DI1). Each axis records its winning tier in `SOURCE_*` string fields
  on `SectionMoodResolution` — a ready-made audit trail primitive (DI6) that only needs to be
  surfaced in the sheet's response text.
- **DI2 ("Q1 답이 Q2~Q4 제안을 재유도") needs no new derivation logic.** `MusicProfile.concept`
  already drives `CONCEPT_SEED_TABLE` lookups inside `resolve_section` (color_tendency +
  position_candidates rungs). Re-running `resolve_section` after rebuilding `MusicProfile` with
  the Q1 answer's concept automatically changes the Q2-Q4 suggestion inputs — no bespoke
  "re-derive" function is required, just re-invocation with an updated profile.

## 3. Energy budgets → cue values (`server/design/energy.py`)

- `axis_budget(d_level, profile: MusicProfile, rig: RigProfile) -> AxisBudget` (lines 276-299+).
  `AxisBudget.dimmer_pct: tuple[float,float]` and `.fade_seconds: tuple[float,float]` are
  **ranges**, not single scalars (§3 table transcribed as ranges deliberately — energy.py
  docstring: "ranges stay ranges rather than being collapsed to an invented single number").

## 4. R4 target — `server/spatial/position_cuesheet.py` + `server/spatial/mib.py`

- `build_position_cue_sheet(sections, *, sequence_no, preset_start, fids, fade_seconds=3.0,
  move_seconds=1.0) -> PositionCueSheet` (position_cuesheet.py:123-215). **Currently has zero
  awareness of `server.design.*`** — confirmed via grep, no `from server.design` import anywhere
  in `position_cuesheet.py`, `mib.py`, or `session.py`. Dimmer is hardcoded `_LIT_DIMMER = 100.0`
  (line 54) for every lit cue; `fade_seconds` is one flat value for the whole sheet passed in from
  the caller. This is precisely the acceptance.md M2 gap: "전 큐 100% 금지 — L2 통과" is currently
  failing by construction (every cue is literally 100%).
- `PositionCuePlan` (server/spatial/mib.py:45-62) — `dimmer: float | None`, `fade_seconds: float |
  None`. **Single scalars.** So AxisBudget's range outputs must be collapsed to one number each
  before they reach a `PositionCuePlan` — see Finding A below for why this needs an explicit,
  documented policy (e.g. range midpoint, or ceiling-of-dimmer/floor-of-fade for "reveal" cues).
- Session entry point: `server/web/session.py:1233` `_position_cue_sheet(text)`, triggered by the
  `_POSITION_SHEET_REQUEST` regex on the existing "포지션 큐 시트 …" vocabulary. This is the R4
  integration site — it already resolves sections, sequence_no, preset_start, and fade_seconds (a
  flat default `3.0`, lines 1319-1324) via the ask-or-parse idiom, then calls
  `build_position_cue_sheet` at line 1327. Plan.md's M2 step 2 ("세션 어휘: BPM·장르 파싱") has
  **no existing regex** for BPM/genre in session.py today (grep confirms zero matches) — this is
  net-new, low-risk parsing work following the same `_CUE_FADE`-style regex pattern already in the
  file.

## 5. Test seams (both files have the exact fixture shape needed)

- `server/tests/test_position_cuesheet.py` — pure-function tests, no console/session. A `profile`/
  `rig`-carrying variant of `test_moods_resolve_to_operator_based_presets` is the natural M2 red
  test: same 12-section metal-set-style input, assert dimmer/fade now differ by resolved D-level
  instead of being uniformly 100%/flat — this directly encodes the Seq 114 regression the SPEC
  names (spec.md R4's S clause).
- `server/tests/test_web_session.py:1593-1669` — `_Channel(answers)` fake (`ask()` pops from a
  list, `UNANSWERED` on empty) + `test_a_full_instruction_stores_the_sheet_with_mib` (all values
  pre-specified, zero cards asked) + `test_missing_numbers_ask_two_cards_in_order` (asserts
  `channel.asked` order and prompt substrings) + `test_no_answer_refuses` (UNANSWERED path). This
  triplet is the exact test seam for R1c's "5카드 순차 발행·선택/자유입력/무응답 각 경로" AC —
  extend `_Channel` with 5 queued answers, assert `channel.asked` has 5 entries in Q1→Q5 order,
  and reuse the empty-list-`UNANSWERED` pattern for the "무응답 = 자동 제안값 + 감독 미확정 표기"
  case (DI4).
- `server/orchestrator/tools.py` — `get_rig_context` (existing tool, already used elsewhere in the
  file for groups/inventory/coords) is the plausible source for `build_rig_profile(patch, groups,
  coords, declared_layers=None)`'s three positional arguments; `_read_pointing_coordinates`
  (session.py:753-788) already demonstrates the console-round-trip pattern
  `build_position_cue_sheet`'s caller uses for `fids`/coords today. Full session-side RigProfile
  assembly was not traced end-to-end in this read-only pass (see Gaps).

## Findings that need a decision before/at implementation (not blockers)

**Finding A — AxisBudget carries ranges, PositionCuePlan needs scalars.** `dimmer_pct` and
`fade_seconds` on `AxisBudget` are deliberately left as `(low, high)` tuples (energy.py explicitly
says it never collapses the §3 table to an invented single number). `PositionCuePlan.dimmer` /
`.fade_seconds` are plain `float`. M2's wiring code (in `position_cuesheet.py` or its session
caller) must pick a point in each range — this is undocumented anywhere in spec.md/plan.md and
should be a named, tested policy (e.g., "reveal cues take the range midpoint" or "take the ceiling
of dimmer_pct, floor of fade_seconds beats-converted") rather than an ad-hoc pick buried in the
wiring commit.

**Finding B — DirectorOverride is per-section-call; R1c's 5 questions are per-song.**
`resolve_section(mood_text, profile, director_intent=...)` takes exactly one `DirectorOverride`
per invocation, i.e., per SECTION. R1c's 5 cards (Q1 컨셉, Q2 팔레트, Q3 클라이맥스, Q4 공간
스토리, Q5 질감) are asked **once per song**, and their natural targets are mixed:
- Q1 (컨셉) and Q2 (팔레트) map cleanly to `MusicProfile.concept` / `.palette` — song-level, no
  per-section override needed, `resolve_section` already threads these through the concept/genre
  rungs.
- Q3 (클라이맥스) and Q4 (공간 스토리) are naturally section-scoped ("which section is the
  climax", "how the rig should move through space") — these need the interview layer to construct
  a `DirectorOverride` **per affected section**, or a small new mapping type; nothing in
  `profile.py` currently expresses "override section N's D-level to 5" as a song-level statement.
- Q5 (질감/texture) has **no landing spot in the M1 data model at all**. `energy.py`'s own
  docstring says genre-texture notes ("스냅 위주, 히트 정밀 타이밍, 하드 스냅 등") are
  deliberately NOT owned by `axis_budget` ("이 모듈이 소유한 §3 축이 아니므로 그대로 둔다"). For
  M2, Q5's answer most likely needs to land only in the audit trail (DI6: satisfies "감독 미확정"
  disclosure without driving any computed value) rather than any energy/lint axis, since no §3/§7
  field currently represents "texture". This should be made explicit in the M2 delegation prompt
  so the implementer doesn't silently invent a texture axis.

**Finding C — acceptance.md M2 live-check references color, which is R5/M3 scope.**
acceptance.md's M2 section includes: "라이브: 앱 UI 인터뷰 전 과정 → 자유 입력 팔레트가 큐
컬러에 반영." But spec.md scopes color integration to R5 (M3), and today `PositionCuePlan`/
`build_position_cue_sheet` never write a color attribute — only preset recall + dimmer. Either
(a) this acceptance bullet is premature and should move to M3, or (b) M2 is expected to at least
surface the palette free-text answer in the response text/audit trail without it driving an actual
cue color value yet. This is a spec/acceptance inconsistency worth a one-line clarification before
M2 sign-off; it does not block starting M2's position+dimmer work.

## Gaps in this read-only pass (things not fully traced)

- Did not trace the exact `get_rig_context` tool-call shape end-to-end against
  `build_rig_profile(patch, groups, coords, declared_layers=None)`'s parameter contract — grep
  confirms the tool exists and returns groups/inventory/fixtures, but a live
  `session._registry.dispatch(...)`-shaped adapter from tool JSON to `build_rig_profile`'s three
  positional args was not written/verified. Low risk (mechanical mapping, same shape as the
  existing `_read_pointing_coordinates` adapter), but worth a first-milestone spike before the
  full 5-card interview is built on top of it.
- Did not read `server/design/lint.py`'s L1-L14 rule bodies in detail (R3, already M1-complete per
  acceptance.md) — only confirmed `lint_sheet(sheet, profile, rig) -> LintReport` exists as the
  R4 "린트 위반은 결과 텍스트에 보고" hook.
- Did not run any tests or the server (task scope: read-only, no broad suites).

## Minimally risky implementation sequence

1. `position_cuesheet.build_position_cue_sheet`: add optional `profile: MusicProfile | None =
   None` (and implicitly `rig`, or pass a pre-resolved per-section `AxisBudget` sequence) —
   default `None` preserves every existing test byte-for-byte (backward compatible). When
   provided, resolve each section via `resolve_section` + `axis_budget`, apply Finding A's scalar
   policy, and build `PositionCuePlan` from the resolved D-level's dimmer/fade instead of
   `_LIT_DIMMER`/the flat fade parameter.
2. Extend `test_position_cuesheet.py` with a `profile`-carrying regression test asserting
   dimmer/fade differ by D-level (the direct Seq 114 fix), before touching session.py.
3. Add BPM/genre regex parsing to `_position_cue_sheet` in session.py (new, low-risk, follows the
   existing `_CUE_FADE`-style pattern).
4. Build `server/design/interview.py` as a **pure** module (no console handle, matching
   profile.py/rig.py/energy.py's stated purity constraint): expose something like
   `build_question(step, profile, rig, prior_answers) -> QuestionSpec` (suggestion label + 2
   alternatives + why) and `apply_answer(step, raw_answer, profile) -> ProfileUpdate |
   DirectorOverride` per Finding B's per-question target mapping. `session.py` drives the actual
   `_ask_one` loop and the skip-if-pre-specified regex checks (reusing the sequence_no/preset_start
   idiom), never `interview.py` itself — preserving the console-untouched purity boundary the rest
   of `server/design/` already follows.
5. Wire the 5-card loop into `_position_cue_sheet`, feeding the resulting `MusicProfile` +
   per-section `DirectorOverride`s into step 1's extended `build_position_cue_sheet`.
6. Surface the 5-question audit trail (question, chosen source, suggested vs. answered) in the
   `InstructionResult.text`, reusing `SOURCE_*` tags already present on `SectionMoodResolution`.
7. Extend `test_web_session.py` with the 5-sequential-card test (extend `_Channel`), the
   skip-if-answered-in-instruction test, the Q1-changes-Q2-suggestion test, and the
   UNANSWERED/"감독 미확정" audit-trail test — all direct extensions of the existing
   `_position_cue_sheet` test block (lines ~1593-1669).
