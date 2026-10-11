# SPEC Delta-Review Report: SPEC-LDBEAT-001 (카드 t566·t556·t564 묶음 개정, version 0.4.1 → 0.5.0)
Iteration: delta/1 (full-document re-audit out of scope per task; this is a targeted delta audit of the in-place revision described below)
Verdict: FAIL
Overall Score (category average, informational only — see Must-Pass Firewall): 0.94

Reasoning context ignored per M1 Context Isolation. This audit reads only `spec.md`, `plan.md`, `acceptance.md`, `design.md`, `progress.md` for SPEC-LDBEAT-001 (Tier L) plus the repository source files the revision cites as evidence, and verifies every factual claim against the actual tree at HEAD `b961cc9e` (branch `WT-spec-entry-wording`).

## Scope of this audit

The revision bundles four cards into one HISTORY entry (2026-10-11, "카드 t566·t556·t564 묶음 개정 + 카드 t555 반영 재확인"):

- ① 카드 t566 — REQ-LDBEAT-006(i-4a)–(i-4f) 신설(`entry` 저장 스키마 확장) + REQ-LDBEAT-020(e) 재교정 + AC-LDBEAT-020(f)–(k) 신설
- ② 카드 t556 — AC-LDBEAT-016(a)/(e), AC-LDBEAT-025(d) 재교정(문면-구현 정합)
- ③ 카드 t564 — REQ-LDBEAT-023(a) 근거 칸 오기 교정
- ④ 카드 t555 후속 — REQ-LDBEAT-015(h) 신설 + AC-LDBEAT-016(v) 신설 (`fresh_approval_cue` 명문화)

version bumped 0.4.1 → 0.5.0. Claimed invariants: REQ 25/25, AC 25/25, 0 deletions, 0 code diff.

## Must-Pass Results

- **[PASS] MP-1 REQ Number Consistency** — `grep -oE '^\| REQ-LDBEAT-[0-9]+' spec.md` and the AC equivalent both enumerate 001–025 exactly once each, no gaps, no duplicates, consistent 3-digit zero-padding. Verified directly (not taken from the HISTORY claim).

- **[FAIL] MP-2 EARS/GEARS Format Compliance (requirement layer only)** — `spec.md:166`, REQ-LDBEAT-020(e), the sub-clause this very revision rewrote ("재교정(카드 t566)"), mixes a formal shall-clause with an un-triggered informal normative sentence:

  > `**The** 화면의 시간 표시 **shall** 초를 먼저, 박·마디는 괄호로 보여준다(...) — 박 입력도 허용하며, 정수 마디로 떨어지는 입력은 \`entry.fade_bars\`에, 정수 마디로 떨어지지 않는 박 입력(예: 1박)은 \`entry.fade_beats\`에 저장된다(...). 콘솔 저장이 박 또는 마디의 **정수** 단위를 벗어나는 것(...)은 그대로 **shall not**이다(...).`

  The middle clause — "정수 마디로 떨어지는 입력은 `entry.fade_bars`에, ... 떨어지지 않는 박 입력은 `entry.fade_beats`에 저장된다" — asserts a NEW, independently-testable fact (which of the two storage fields receives a given input, based on bar-integer-divisibility) that is governed by no GEARS trigger anywhere in the cell. It is not a restatement of the adjacent `shall`/`shall not` clauses: the leading `shall` governs the display-order fact ("show seconds first, bars/beats in parens"); the trailing `shall not` governs a *different* fact (storage must stay in integer bar/beat units, never seconds). The routing-destination fact sits between the two, in plain descriptive present tense ("-에 저장된다"), with no `When`/`While`/`Where`/`shall`/`shall not` marker of its own. This is a textbook instance of "mixed informal/formal within a single requirement" (M5 MP-2) and of the SPEC's own previously-named defect class D1/D-NEW-1~4 ("요구사항 칸에 shall 트리거 없는 문장").

  **This is new content, confirmed via the baseline diff.** `clause_check.py` run against the verified-identical pre-revision baseline (`/private/tmp/.../scratchpad/old-spec.md`, confirmed byte-identical to `git show HEAD:...spec.md`) shows the OLD (e) read only: "박 입력도 허용하되, 콘솔 저장과 `entry.fade_bars`(...)의 저장 단위는 **shall not** 바뀐다" — i.e. the old bridging phrase ("허용하되, ...") led directly into a single shall-governed clause with no intervening unmarked assertion. Card t566 inserted the routing-destination sentence between the lead-in and the trailing shall-not, and that insertion carries no trigger of its own.

  **Regression against the SPEC's own established QA practice.** `progress.md` (iteration-2 HISTORY entry, same SPEC) records that a prior plan-audit finding (D-NEW-1~4) was closed by running "REQ-016~025 전체의 요구사항 칸을 글자별 절로 쪼개 'shall' 부재 문장을 검사" and reaching 0 matches. This exact sweep was not re-run after card t566 edited REQ-LDBEAT-020(e), and the defect it is designed to catch slipped back in.

  **Layer discipline note**: this finding is scored against the `REQ-XXX` requirement layer (`spec.md` §3), not against any `AC-XXX` entry — AC-LDBEAT-020 remains correctly Given/When/Then and is not penalized here (see Group 4 below).

  (i-4a) and (i-4b) in the same revision contain a superficially similar shape — a positive restatement immediately mirrored by a trailing `shall`/`shall not` clause covering the *same* fact (e.g. "정확히 하나만 비-미정이거나 둘 다 미정이다" mirrored by "둘 다 동시에 숫자를 갖는 것은 shall not이다"). Those are judged acceptable elaboration (the positive and negative framings describe one constraint, not two), and are not counted as a second MP-2 failure. REQ-020(e)'s routing sentence is different in kind: it states a fact the shall/shall-not pair never covers.

- **[PASS] MP-3 YAML Frontmatter Validity** — `spec.md:1-16`: all 12 canonical fields present with correct types against the SSOT (`id`, `title`, quoted `version: "0.5.0"`, `status: in-progress`, ISO `created`/`updated`, `author`, `priority: P1`, `phase` (a release-target string, not a lifecycle-stage name), `module`, `lifecycle: spec-anchored`, comma-separated `tags`). No rejected snake_case aliases present. `tier: L` and `related_specs: [...]` optional fields also present and well-typed.

- **[N/A] MP-4 Section 22 Language Neutrality** — N/A: single-project lighting-console SPEC (grandMA3/Lua/Python/TypeScript are the project's own fixed stack, not a template-bound multi-language tooling surface). No language-specific tool is presented as a universal/template-bound choice.

- **[PASS] MP-5 D7 Cross-SPEC Reconciliation** — Extracted `SPEC-([A-Z][A-Z0-9]+-)+[0-9]+` references: `SPEC-LDARRANGE-001` (draft), `SPEC-LDBARMAP-001` (in-progress), `SPEC-LDDESIGN-001` (completed), `SPEC-LDRENDER-001` (completed), `SPEC-LDRHYTHM-001` (in-progress). None has status ∈ {retired, superseded, archived}. No BLOCKING finding.

- **[N/A] MP-6 D8 Cross-Platform Discipline** — `grep -c "syscall" spec.md` → `0`. The verification verb's trigger condition (literal substring present) does not fire; D8 is auto-PASS per its own §4 clause, recorded here as N/A per the MP-6 template option.

- **[N/A] MP-7 Clarification Gate** — `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` → no matches. No unresolved markers.

## Factual-Accuracy Verification (MP-5-adjacent, verified against the repository — not taken on the SPEC's word)

All of the following were independently re-derived from the live tree, not accepted from the SPEC text:

1. **12-cell preset-number count (AC-LDBEAT-016(e)/REQ-015(f) basis)**: counted all non-null `preset_no`/`effect_preset_no`/`position_preset_no` occurrences in `server/design/beat_grid_data/love_attack.yaml` by direct grep + bar-range cross-reference against `group_name:`/`bar:` markers. Result: exactly 12 cells, matching the claimed enumeration verbatim — FOH@7=1.1 (dimmer), BACK@3/7/18/22=21.1 (effect), SIDE-ALL@11/14=21.3 (effect), MOVER-U@14=21.5(effect)/@18=2.1(position), MOVER-D@14=21.5(effect)/@18=2.1(position), BLIND@17=1.6 (dimmer). All 12 carry `evidence.approval: {by: supervisor, date: "2026-10-10", source: ".../proposal-table.md#N"}` with the exact row numbers claimed (#1,#5,#6,#9,#10,#14,#15,#22,#23,#29,#30,#32). **Claim verified exactly.**
2. **`preset_pools.yaml` `confirmed: false`** — read directly; matches the claim underlying AC-LDBEAT-016(a)'s re-correction and §5 item 11.
3. **`confirmed`-gated warn-vs-reject + `fresh_approval_cue` same-change-only rule** — `server/design/beat_grid_edit.py:465-469` (`fresh_approval_cue = merged if "evidence" in changes else {**merged, "evidence": None}`) and the `policy.get("confirmed")` branch at ~line 484 (warning when `false`, `BeatGridEditError` when `true`) both confirmed present and matching the cited behavior and line range.
4. **`TRACKING_VALUES`** — `server/design/cue_sheet_edit.py:63` = `("Track", "Block", "Cue Only", "Release")`, matching REQ-LDBEAT-006(i-4e)'s claimed reuse exactly.
5. **`parseBeatsPerBar`** — `ui/src/components/beatGridTransition.ts:33` exists, matching REQ-LDBEAT-006(i-4f)'s cited precedent.
6. **Card t560 merged** — `git log --oneline origin/main` (after `git fetch origin main`) shows `37baf843 feat(SPEC-LDBEAT-001): M9 글랜스 표 6칼럼·L·R 분리 ...` under `Merge pull request #609`, confirming the revision's "발견(범위 밖)" claim. `origin/main` is 12 commits ahead of HEAD, which is expected and explicitly scoped out by the revision's own text.
7. **`.beat-grid-glance-table` is 2-column** (card t564's correction target) — `ui/src/components/BeatGrid.tsx:1987-1996` confirmed: exactly `<td>{track.group_name}</td><td>{cue ? cue.label : "—"}</td>`, no chip/brightness/position/color/changed-marker rendering. The correction's substance is accurate.

   **However — one factual residue was NOT re-verified by this revision and is stale.** The same REQ-LDBEAT-023(a) 근거 cell (`spec.md:169`) still cites the glance table's location as `.beat-grid-glance-table(1118-1134행)`. The actual current location is `BeatGrid.tsx:1987` (lines 1118-1134 in the current tree contain unrelated code — `onSelectAudio`/`seek`). This stale line-number citation already existed verbatim in the pre-revision baseline (confirmed via `grep` against `old-spec.md`) and card t564 reused it unchanged while correcting the surrounding "구현" overclaim — the one specific claim this revision explicitly set out to re-verify ("열 이름 완전 일치는 미측정"→"2칼럼" correction) was re-measured; the co-located line-number citation in the same sentence was not. See D2 below.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity a reasonable engineer would resolve consistently | The REQ-020(e) un-triggered routing sentence (D1 below) is the sole clarity gap in this delta; everything else in the revision (REQ-006(i-4a)-(i-4f), REQ-015(h), the three AC re-corrections) reads as a single unambiguous interpretation. |
| Completeness | 1.0 | 1.0 — all sections present, frontmatter complete | `spec.md` HISTORY/§0-§5 structure, `acceptance.md` §A/§D, `plan.md` M9 precondition note, `design.md` footnote, `progress.md` entry — all five artifacts carry a corresponding, internally-consistent addition; no section left sparse by this delta. |
| Testability | 1.0 | 1.0 — every new/changed AC is binary-testable | AC-LDBEAT-020(f)-(k), AC-LDBEAT-016(v), the re-corrected AC-016(a)/(e) and AC-025(d) each specify a concrete mechanical/manual verification command with a stated PASS/FAIL condition; no weasel words ("적절"/"충분" hits in `acceptance.md` are pre-existing, unrelated prose, not inside this delta's new criteria). |
| Traceability | 1.0 | 1.0 — every new REQ has an AC and vice versa | §A.1 prose explicitly adds: REQ-015(h)→AC-016(v); REQ-006(i-4a)-(i-4f)→AC-020(f)-(k). Verified these mappings exist in the matrix (not just asserted in prose) by reading the full AC-LDBEAT-016 and AC-LDBEAT-020 rows. |

(Group 5 Language Neutrality: N/A per MP-4 — single-project SPEC.)

## Defects Found

D1. **MP-2-GEARS-20e** — `spec.md:166` (REQ-LDBEAT-020(e)) — The revision's new routing-destination sentence ("정수 마디로 떨어지는 입력은 `entry.fade_bars`에, 정수 마디로 떨어지지 않는 박 입력은 `entry.fade_beats`에 저장된다") is a new, independently-testable normative claim with no GEARS trigger (`When`/`While`/`Where`/`shall`/`shall not`) anywhere in the sentence — Severity: **critical** — Class: **blocking** — Required fix: split into two triggered clauses, e.g. "**When** 정수 마디로 떨어지는 박 입력이 제출되면, **The** 그 값 **shall** `entry.fade_bars`에 저장된다. **When** 정수 마디로 떨어지지 않는 박 입력(예: 1박)이 제출되면, **The** 그 값 **shall** `entry.fade_beats`에 저장된다." (preserve REQ-LDBEAT-006(i-4a) cross-reference and the existing trailing shall-not clause verbatim). Re-run the project's own established full-sweep check (`REQ-016~025 전체를 글자별 절로 쪼개 'shall' 부재 문장을 검사`, previously used to close D-NEW-1~4) after the fix, and record the 0-match result in progress.md the same way iteration 2 did.

D2. **STALE-LINE-023a** — `spec.md:169` (REQ-LDBEAT-023(a) 근거) — the cell still cites `.beat-grid-glance-table(1118-1134행)`; the actual current location is `BeatGrid.tsx:1987` (lines 1118-1134 now contain unrelated code). This revision (card t564) re-verified the column-count claim in the same sentence but not the co-located line-number citation — Severity: **minor** — Class: **optional** (근거/evidence-column citation, not a shall clause; does not change any requirement's meaning or testability) — Required fix: re-run `grep -n "beat-grid-glance-table" ui/src/components/BeatGrid.tsx` and update the citation to the current line (1987 at the time of this audit; re-measure at fix time since the file is actively growing).

D3. **STALE-ARTIFACT-t566** — `.moai/reports/t566/clause_check.txt`, `dropped_text_check-1.txt` — these pre-staged verification artifacts were generated against an intermediate, not-yet-final state of `acceptance.md` (confirmed: re-running `clause_check.py`/`dropped_text_check.py` myself against the verified-identical baseline produces materially different output — e.g. `clause_check.txt` reports AC-LDBEAT-016 "missing: ['e']" and a smaller character count than the current file actually has; my independent re-run against the same baseline shows "missing: none"). `dropped_text_check-2.txt` (the final one, timestamped last) does match my independent re-run. — Severity: **minor** — Class: **optional** (does not affect the SPEC's own correctness; affects only the trustworthiness of a scratch audit aid, and the final `-2` artifact is itself correct) — Required fix: none required of the SPEC; if these scratch files are retained for future reference, delete or relabel the stale `-1` txt/`clause_check.txt` so a future reader does not mistake it for current.

No other defects found. MP-1/3/5/6/7 all independently verified PASS/N/A with concrete evidence above; all cross-checked factual claims (12-cell count, confirmed:false, fresh_approval_cue line range, TRACKING_VALUES, parseBeatsPerBar, card-t560-merged, 2-column glance table) hold exactly as stated.

## Regression Check

Not applicable — this is iteration 1 of a delta audit for the t566/t556/t564 bundle (distinct from the prior t554 iteration-1/iteration-2 sequence and the separate t555 delta, both already closed PASS). No prior-iteration defect list exists for this specific bundle to check for recurrence.

## Recommendation

**FAIL — fix D1 (blocking) before re-audit; D2/D3 are optional cleanup.**

1. Rewrite `spec.md:166` REQ-LDBEAT-020(e)'s inserted routing-destination sentence into two `When ... The ... shall ...` clauses as specified in D1's required fix. Do not touch the sentence's substance (which field receives which input) — only add the missing GEARS triggers.
2. Re-run the SPEC's own established shall-less-sentence sweep across REQ-016~025 (the same check that closed D-NEW-1~4 in the iteration-2 HISTORY entry) and record the result in `progress.md`.
3. Optionally correct the stale `1118-1134행` citation at `spec.md:169` (D2) to the current `BeatGrid.tsx` glance-table line (re-measure at fix time).
4. Optionally delete or relabel the stale `.moai/reports/t566/clause_check.txt` / `dropped_text_check-1.txt` scratch artifacts (D3) so they are not mistaken for current verification evidence.

Everything else in this revision — REQ-LDBEAT-006(i-4a)-(i-4f), REQ-LDBEAT-015(h), AC-LDBEAT-020(f)-(k), AC-LDBEAT-016(v), the AC-016(a)/(e) and AC-025(d) re-corrections, the REQ/AC count invariants, the zero-deletion invariant, and the zero-code-diff invariant — is independently verified accurate and GEARS/Given-When-Then compliant. A re-audit after D1's fix, scoped to REQ-LDBEAT-020(e) and the re-run sweep evidence, should be sufficient to reach PASS.
