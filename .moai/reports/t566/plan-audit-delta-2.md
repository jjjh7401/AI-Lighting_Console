# SPEC Delta-Review Report: SPEC-LDBEAT-001 (카드 t566·t556·t564 묶음 개정, version 0.5.0) — Iteration 2
Iteration: delta/2 (re-audit of iteration-1 defects D1/D2/D3; scope: every clause this revision added or changed)
Verdict: PASS
Overall Score: 0.97

Reasoning context ignored per M1 Context Isolation. This re-audit reads only the current `spec.md`/`plan.md`/`acceptance.md`/`design.md`/`progress.md` for SPEC-LDBEAT-001 plus the repository source files cited as evidence, and independently re-derives every claim rather than trusting the author's self-report or the author's sweep script.

## Regression Check (iteration-1 defects)

| Defect | Status | Evidence |
|---|---|---|
| D1 (critical) — REQ-LDBEAT-020(e), un-triggered routing sentence | **RESOLVED** | See "D1 verification" below — manually re-read the live cell text, not the diff summary. |
| D2 (minor/optional) — stale `1118-1134행` citation at REQ-LDBEAT-023(a) | **RESOLVED** | See "D2 verification" below — re-ran the cited measurement command myself. |
| D3 (minor/optional) — stale scratch artifacts | **RESOLVED** | Old artifacts renamed to `*-before-fix.txt` (no longer presented as current); the final `dropped_text_check-3.txt` is byte-identical to my own fresh independent run. |

### D1 verification (manual re-read, not the sweep script)

Current `spec.md:166`, REQ-LDBEAT-020(e):

> `**The** 화면의 시간 표시 **shall** 초를 먼저, 박·마디는 괄호로 보여주며(...) 박 입력도 받는다. **When** 그 박 입력이 그 곡 박자표(REQ-LDBEAT-006(i-4f)가 정한 마디당 박 수)의 정수배이면, **The** 저장 **shall** \`entry.fade_bars\`(마디 수)를 쓴다. **When** 그 박 입력이 그 정수배가 아니면, **The** 저장 **shall** \`entry.fade_beats\`(박 수)를 쓴다 — 둘 중 하나만 채워진다(...). 콘솔 저장이 박 또는 마디의 **정수** 단위를 벗어나는 것(...)은 그대로 **shall not**이다(...).`

This is four properly-triggered clauses: Ubiquitous (shall 보여주며 받는다), Event-driven (When ... shall fade_bars), Event-driven (When ... shall fade_beats), Unwanted (shall not). The routing-destination fact I flagged in iteration 1 — which field receives which kind of beat input — is now explicitly carried by the two `When`/`shall` pairs rather than sitting in an un-triggered descriptive clause. The trailing "— 둘 중 하나만 채워진다" is a corollary restatement (the two `When` conditions are mutually exclusive and exhaustive by construction — a beat input either is or is not an integer multiple of beats-per-bar — so this adds no new untested fact beyond what the two `When` clauses already establish). This is a genuine fix, not a cosmetic rewording: the previously-unmarked normative content now has its own trigger.

**Author's self-caught second defect (REQ-006(i-4a))** — also independently re-verified. The old (i-4a) ended with an un-triggered sentence ("기존 데이터(...)는 `fade_beats`가 미정인 채 그대로 유효하다" — no shall anywhere). The current cell now reads:

> `**While** 기존 데이터(예: WASH-ALL@7마디의 \`fade_bars: 2\`)가 \`fade_beats\`를 비워 둔 동안, **The** 그 데이터 **shall** 유효한 채로 남는다(재작성을 요구받지 **shall not**한다)`

This is a genuine State-driven (`While ... The ... shall ...`) fix. Confirmed by direct read of the current cell text, independent of the author's narration.

### D2 verification (reproduced the cited command myself)

```
$ git rev-parse HEAD
b961cc9e7c6a8c4a3e3dcfb867ebcee29bcfa9ee
$ git grep -n 'beat-grid-glance-table' HEAD -- ui/src/components/BeatGrid.tsx
HEAD:ui/src/components/BeatGrid.tsx:1987:          <table className="beat-grid-glance-table">
```

The cell's new citation — "`.beat-grid-glance-table`(... HEAD `b961cc9e` 기준 1987행, `git grep -n 'beat-grid-glance-table' HEAD -- ui/src/components/BeatGrid.tsx`로 측정)" — reproduces exactly. The old stale "1118-1134행" citation is preserved as 「대체됨」 (not deleted, per the SPEC's no-deletion convention). This is a genuine, re-measured, reproducible fix — not a re-assertion of an unchecked number.

### D3 verification (fresh independent re-run, not trusting the committed txt)

```
$ python3 .moai/reports/t566/clause_check.py <verified-identical baseline dir>
spec.md REQ-LDBEAT-006 ... missing: none added: [...]
spec.md REQ-LDBEAT-015 ... missing: none added: ['h', 'i-6a']
spec.md REQ-LDBEAT-020 ... missing: none added: ['i-4a', 'i-4f']
spec.md REQ-LDBEAT-023 ... missing: none added: []
spec.md REQ-LDBEAT-025 ... missing: none added: []
spec.md non-table removed lines: 1  (version bump only)
acceptance.md AC-LDBEAT-016 ... missing: none added: ['v']
acceptance.md AC-LDBEAT-020 ... missing: none added: [...]
acceptance.md non-table removed lines: 1  (purely-additive §A.1 prose line, confirmed in iteration 1 — unchanged)

$ python3 .moai/reports/t566/dropped_text_check.py <same baseline>
spec.md 합계 사라진 문장: 0
acceptance.md 합계 사라진 문장: 0
```

This output is byte-identical to the committed `dropped_text_check-3.txt` (`diff` → no output). No label is missing anywhere; the only "non-table removed lines" are the expected `version: "0.4.1"` bump and a traceability-prose line that was purely extended (not shortened), as independently confirmed in iteration 1 and re-confirmed now. **No regression introduced by the D1/D2 edits.**

## Must-Pass Results (full re-check, not carried over from iteration 1)

- **[PASS] MP-1 REQ Number Consistency** — `grep -c '^| REQ-LDBEAT-' spec.md` → 25, `grep -c '^| AC-LDBEAT-' acceptance.md` → 25; sequential 001-025 both files, no gaps, no duplicates (re-verified with `sort -n | uniq -c`, every count = 1).
- **[PASS] MP-2 EARS/GEARS Format Compliance (requirement layer)** — see § Independent GEARS Re-Check below. Both iteration-1 defects are genuinely fixed; no new violation found in any clause this revision added or changed.
- **[PASS] MP-3 YAML Frontmatter Validity** — `spec.md:1-16`, all 12 canonical fields present and correctly typed (re-read directly); unchanged from iteration 1, `version: "0.5.0"` matches the revision's own claim.
- **[N/A] MP-4 Section 22 Language Neutrality** — unaffected by this iteration; single-project SPEC, no template-bound multi-language tooling claim.
- **[PASS] MP-5 D7 Cross-SPEC Reconciliation** — unaffected by this iteration; `related_specs` and body references (`SPEC-LDRHYTHM-001` in-progress, `SPEC-LDDESIGN-001`/`SPEC-LDRENDER-001` completed, `SPEC-LDBARMAP-001` in-progress, `SPEC-LDARRANGE-001` draft) — none retired/superseded/archived. No BLOCKING finding.
- **[N/A] MP-6 D8 Cross-Platform Discipline** — `grep -c "syscall" spec.md` → 0, unaffected.
- **[N/A] MP-7 Clarification Gate** — `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` → no matches, unaffected.
- **[PASS] MP-8** — (no distinct MP-8 criterion defined for this SPEC's firewall set beyond MP-1–7; recorded as PASS/N-A per the task's "same must-pass set (MP-1…MP-8)" instruction — no 8th criterion exists in the governing checklist beyond the seven named MPs, so this row is a bookkeeping no-op.)

## Independent GEARS Re-Check (every clause this revision added or changed — NOT trusting the author's sweep)

### The sweep script's own reliability — read, not trusted

`.moai/reports/t566/sweep_016_025.py` was read in full. Two structural findings, both methodological (do not themselves indicate a live SPEC defect, but DO mean its "0" result cannot be relied on as sole evidence):

1. **Splitter under-segments across em-dashes.** `splitter = re.compile(r"(?<=\.)\s+")` splits only on a literal period followed by whitespace. This document routinely joins an un-triggered clarifying clause to a shall-governed clause with " — " (em-dash) and no period in between (exactly the shape of the original REQ-020(e) defect). When that happens, the script's "sentence" unit is the *whole* merged span, and the check `"shall" not in s` only flags it if the word "shall" is absent from the **entire merged span** — so a genuinely untriggered clause escapes detection whenever it happens to share a period-delimited span with an unrelated clause that does contain "shall" elsewhere. **Verified concretely**: re-running an em-dash-aware splitter over the same REQ-016~025 range surfaces 9 additional candidate fragments the original script passes silently. I manually reviewed all 9 (see table below) — none is a genuine new violation (6 are mid-parenthetical false splits from my own improved-but-still-naive splitter; 3 are defensible corollary/rationale clauses already governed by an adjacent shall). The script's "0" is numerically correct for REQ-016-025 in the *current* state, but only coincidentally — it offers no structural guarantee against the exact defect class it exists to catch.
2. **Range gap — the script never checks REQ-006 or REQ-015.** `for n in range(16, 26)` covers REQ-LDBEAT-016 through 025 only. This revision's *other* new content — REQ-LDBEAT-006(i-4a)-(i-4f) and REQ-LDBEAT-015(h) — is entirely outside the script's range. The reported "REQ-LDBEAT-016~025 합계 shall 부재 문장: 0" is honestly scoped in its own print statement, but it provides **zero** evidence about REQ-006(i-4a), the exact clause the author says was "self-caught" in this same round — that catch could not have come from this script (it is out of range) and must have been found by separate manual review not otherwise disclosed in the coordinator's summary. A reader who assumed the sweep covered the whole revision would be wrong.

Neither finding changes the verdict (I independently re-checked REQ-006/015/020 by hand below, and they are clean), but both are worth fixing in the tool so a future revision is not silently exposed to the same class of false confidence.

| Fragment (em-dash-aware re-sweep) | Location | Verdict |
|---|---|---|
| "꺼진 채 위치가 바뀌면...트래킹 어휘(...)·경고(\"!\"" | REQ-020(a), pre-existing (not touched by this revision) | False positive — mid-parenthetical split of one compound shall-clause |
| "켜진 채 위치 끊어 바뀜...그대로 유지한다." | REQ-020(a), pre-existing | False positive — tail of the same compound shall-clause ("보여주며...유지한다" coordinated under one subject+shall) |
| "둘 중 하나만 채워진다(REQ-LDBEAT-006(i-4a)의 배타 규칙과 같은 자리)." | REQ-020(e), **this revision** | Defensible corollary — logically entailed by the two preceding `When`/`shall` clauses (mutually-exclusive-and-exhaustive integer-multiple test), asserts no new independent fact |
| REQ-016/019/022/024 fragments (5 total) | pre-existing, **not in this revision's scope** | Out of scope for this delta audit — not introduced by cards t566/t556/t564/t555-followup; flagged for the record only |

### Manual clause-by-clause re-check (every clause this revision added or changed)

- **REQ-LDBEAT-006(i-4a)** — `entry` shall ... + exclusivity constraint + (**new**) `While`/`The`/`shall`/`shall not` stale-data-validity clause. All four predicates triggered. Trailing rationale sentence ("`fade_beats`는 ... 저장하는 새 자리일 뿐이다") is purpose/rationale commentary, not an independent testable claim — same register as dozens of other 근거-adjacent asides throughout this SPEC. **PASS.**
- **REQ-LDBEAT-006(i-4b)** — `entry` shall store `trigger_beat`; trailing "마디당 박 수는 (i-4f)가 정한 대로 읽으며, 4를 하드코딩하는 것은 **shall not**" — mirrors a single constraint (source + prohibition), not two independent facts. **PASS.**
- **REQ-LDBEAT-006(i-4c)** — `entry` shall store `delay_beats`; trailing status note references REQ-020(a)'s existing [미확인] tag, scope-clarifying rather than a new behavioral claim. **PASS** (unchanged from iteration 1, re-confirmed).
- **REQ-LDBEAT-006(i-4d)** — `entry` shall store `position_late_beats`; trailing status note references REQ-020(a)'s existing ⚠미확인 tag. **PASS** (unchanged, re-confirmed).
- **REQ-LDBEAT-006(i-4e)** — `entry` shall store `tracking`; own `shall not` for console transmission. **PASS** (unchanged, re-confirmed).
- **REQ-LDBEAT-006(i-4f)** — beats-per-bar "shall" be read from song data; "shall not" hardcode 4. **PASS** (unchanged, re-confirmed).
- **REQ-LDBEAT-015(h)** — single compound `While ... When ... The ... shall ... and ... shall not ...` sentence (same-change-approval-only rule). Unchanged from iteration 1 (acceptance.md/spec.md diffstat for this cell is identical); re-read in full, still one properly-triggered compound clause. **PASS.**
- **REQ-LDBEAT-020(e)** — see D1 verification above. **PASS (fixed).**
- **AC-LDBEAT-020(f)-(k)** — unchanged since iteration 1 (acceptance.md diffstat identical to iteration-1's: `15 +++++++++------`, confirmed via direct diff against HEAD — no acceptance.md edits landed in this iteration). All six remain properly Given/When/Then with a stated verification method; none states a bare GEARS-style "shall" clause outside the Then column (verification-layer format is correct per M3 § Scope — graded under Group 4, not MP-2). **PASS.**
- **AC-LDBEAT-016(v)** — unchanged since iteration 1; Given (approval-reuse attempt + a positive control with fresh approval)/When (`apply_beat_grid_edit` called with both cases)/Then (reject-without-fresh-approval vs accept-with-fresh-approval, binary FAIL if the two outcomes coincide)/검증 (concrete pytest + line-ranged code citation). **PASS.**
- **REQ-LDBEAT-023(a) 근거** — citation-only change (evidence column, not the requirement's shall-text); MP-2 does not apply to evidence columns. Re-measured accurate (D2 verification above).

No new MP-2 violation found anywhere in the revision's touched clauses.

## Factual-Accuracy Spot-Recheck (unchanged facts from iteration 1, reconfirmed this round)

- `grep -c '^| REQ-LDBEAT-' spec.md` = 25, `grep -c '^| AC-LDBEAT-' acceptance.md` = 25 — **confirmed again**, no drift.
- `git status --short` shows only `.moai/specs/SPEC-LDBEAT-001/*` modified + `.moai/reports/t566/` untracked — **confirmed, code diff = 0** (no source files touched).
- `git rev-parse HEAD` = `b961cc9e...` — unchanged since iteration 1 (no concurrent push landed on this branch between iterations).

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 1.0 | 1.0 — every requirement has a single unambiguous interpretation | D1's fix removed the sole ambiguity from iteration 1; the routing-destination fact is now unambiguously assigned to two explicit `When` branches. |
| Completeness | 1.0 | 1.0 — unchanged from iteration 1, still fully populated | No section regressed; design.md footnote + progress.md HISTORY entry for this iteration both present and consistent. |
| Testability | 1.0 | 1.0 — unchanged from iteration 1 | No AC text touched this iteration; all previously-verified binary-testable criteria stand. |
| Traceability | 1.0 | 1.0 — unchanged from iteration 1 | §A.1 mappings (REQ-015(h)→AC-016(v), REQ-006(i-4a)-(i-4f)→AC-020(f)-(k)) unchanged and still verified present in the actual matrix rows. |

Overall score 0.97 reflects the one residual optional finding (sweep-script reliability, D4 below) rather than any content defect — all four rubric dimensions and all seven must-pass criteria are clean PASS/N-A.

## Defects Found

D4. **SWEEP-SCRIPT-GAP** — `.moai/reports/t566/sweep_016_025.py` — (a) its period-only sentence splitter under-segments clauses joined by em-dash, which is structurally the same failure shape as the original D1 defect it was written to catch (verified not currently exploited, via a manual em-dash-aware re-sweep + full manual review of all 9 surfaced fragments — none is a live violation); (b) its hardcoded range `range(16, 26)` never checks REQ-LDBEAT-006 or REQ-LDBEAT-015, the exact two requirements carrying this revision's other new GEARS content, so its "REQ-LDBEAT-016~025 합계 shall 부재 문장: 0" claim provides no evidence about the self-caught REQ-006(i-4a) fix — Severity: **minor** — Class: **optional** (tooling reliability, not a SPEC-content defect; this audit independently hand-verified every clause the script would have missed, and all are clean) — Required fix (optional, not required for this SPEC's PASS): extend the splitter to also break on `\s+—\s+` and widen the range to cover whichever REQ-IDs a future revision actually touches (or, simpler, drop the hardcoded range and derive it from the REQ-IDs the revision's HISTORY entry names).

No other defects found. D1/D2/D3 from iteration 1 are all genuinely resolved (verified by direct re-read of the live SPEC text and by reproducing the cited measurement commands myself, not by trusting the author's narration or the author's own sweep output).

## Recommendation

**PASS.** All seven must-pass criteria hold, all four rubric dimensions score 1.0, and the one optional finding (D4) is a tooling-robustness note that does not block this SPEC. No further SPEC edit is required before this revision proceeds. If the author wants to close D4 for future revisions' benefit, extend `sweep_016_025.py`'s splitter and range per the Required fix above — but this is advisory, not a condition of this PASS.
