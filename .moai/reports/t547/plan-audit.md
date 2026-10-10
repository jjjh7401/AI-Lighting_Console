# SPEC Review Report: SPEC-LDBARMAP-001 (card t547 amendment — REQ-LDBARMAP-006 redesign)
Iteration: 1/3 (scoped delta audit — card t547 amendment only; earlier HISTORY rows out of scope per audit brief)
Verdict: FAIL
Overall Score: 0.667 (harmonic mean; pass line 0.80)

Reasoning context ignored per M1 Context Isolation. This audit used only the uncommitted diff
`git -C <worktree> diff -- .moai/specs/SPEC-LDBARMAP-001/` plus the cited evidence files under
`.moai/reports/t547/` and `.moai/reports/t546/`.

## Scope note

This SPEC's plan-phase has already passed a prior full audit (iteration 8, PASS 0.86,
`.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-8.md`) and subsequent part-amendments
(t539, t541). This report audits **only the card-t547 amendment** — the REQ-LDBARMAP-006
redesign (fixed-grid comparison → beat-grid-relative sign test) and its corresponding
AC-LDBARMAP-004(a-d) rewrite. Pre-existing document structure (frontmatter, other REQ/AC
entries, Out-of-Scope sections) is verified only where this amendment touches it.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: `grep -oE 'REQ-LDBARMAP-[0-9]+' spec.md | sort -u | wc -l` → 16, sequential REQ-LDBARMAP-001..016, no gaps/duplicates. Confirmed via direct grep against `.moai/specs/SPEC-LDBARMAP-001/spec.md`.
- [PASS] MP-2 EARS/GEARS format compliance (scoped to the touched requirement layer, REQ-LDBARMAP-006 only): `spec.md:72` — `(재설계 — 카드 t547, 2026-10-10) **While** BPM을 추정하는 동안, 검출기 **shall** ...` is a valid GEARS state-driven (`While ... shall`) pattern. The verification-layer AC-LDBARMAP-004a-d (`acceptance.md:52-72`) are correctly Given-When-Then and are NOT GEARS-checked per M3 § Scope (two-layer table) — judged under Group 4, not here.
- [PASS] MP-3 YAML frontmatter validity: all 12 canonical fields present and typed correctly; only `version:` changed (`"0.1.6"` → `"0.1.7"`, valid quoted semver) — `spec.md:3`. No snake_case aliases introduced.
- [N/A] MP-4 Section 22 language neutrality: this SPEC is a single-domain audio-analysis SPEC (Python, `server/audio/bar_map.py`), not multi-language tooling. N/A auto-passes.
- [PASS] MP-5 D7 cross-SPEC reconciliation: `grep -E '^\+' /tmp/t547_spec_diff.txt | grep -oE 'SPEC-[A-Z][A-Z0-9]*-[0-9]+' | sort -u` → only `SPEC-LDBARMAP-001` (self). The pre-existing mentions of `SPEC-LDARRANGE-001` / `SPEC-LDBEAT-001` / `SPEC-LDRHYTHM-001` in the diff output are unchanged HISTORY-table context lines (no `+` prefix), not new content this amendment introduces. No new cross-SPEC reference → nothing to reconcile.
- [PASS] MP-6 D8 cross-platform discipline: `grep -n "syscall" spec.md plan.md acceptance.md research.md` → no matches in any of the four artifacts. D8-4 auto-PASS.
- [N/A] MP-7 clarification gate: `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` → no matches (command ran, zero output — treated as PASS evidence, not N/A); no unresolved markers found.

No must-pass firewall failure. The FAIL verdict below is driven entirely by the aggregate category score (§ below), not by any MP criterion.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | "Multiple requirements require interpretation. A reasonable engineer might implement them differently than intended." | `acceptance.md:58` and `acceptance.md:70` — 2 of the 4 AC-LDBARMAP-004 sub-criteria (b, d) describe their synthetic "Given" scenario as "112 BPM 킥/스네어 패턴" (kick/snare pattern), but the cited "Then" statistics (w_mid=0.24/p_mid=8.98e-12 for 004b; w_mid=0.46/p_mid=0.195 for 004d) are measured from `probe_synth.txt`'s "112 박+8분 하이햇 0.3"/"0.7" rows — a **uniform-intensity beat** + hi-hat pattern (`[[1.0, 0.3]]` / `[[1.0, 0.7]]` in `probe_synth.py:32-39`), NOT the kick/snare-alternating pattern (`[[1.0,0.3],[0.6,0.3],[1.0,0.3],[0.6,0.3]]`, the "112 킥/스네어 1.0/0.6 +8분0.3" row). An implementer building the literal "Given" scenario (kick/snare alternation) would not reproduce the cited primary numbers. |
| Completeness | 1.0 | "All required sections present... frontmatter complete." | §A constants table gained the α/symmetry-point rows with units (`acceptance.md:16-17`); REQ-006 rewritten with `While...shall` + evidence column (`spec.md:72`); plan.md §E risk row + new §C "M-추가" milestone with explicit in-scope/out-of-scope/pass-condition subsections (`plan.md:65-71`); research.md §11 (5 sub-sections) backs the redesign with verbatim command+output citations (`research.md:109-153`); HISTORY row added (`spec.md:33`); REQ/AC counts held at 16/16 (Tier M ceiling, not exceeded). |
| Testability | 0.50 | "Several ACs contain weasel words or require judgment calls to evaluate." | No weasel words, but AC-LDBARMAP-004b/d (`acceptance.md:58`, `:70`) are not reliably binary-testable **as literally written**: the Given/Then mismatch (see Clarity row) means a tester following the Given text builds a different synthetic signal than the one that actually produced the cited numbers — determinism requires reading past the primary sentence to the "같은 조건에서 ... 도" secondary clause to find the correctly-labeled kick/snare numbers. AC-004a and AC-004c are cleanly testable (AC-004a explicitly names the `probe_synth.py` case string; AC-004c cites `probe_sign.txt` real-song data verified exactly below). |
| Traceability | 1.0 | "Every REQ-XXX has at least one AC. Every AC references a valid REQ-XXX." | `acceptance.md:46` — `### AC-LDBARMAP-004 (REQ-LDBARMAP-006)` explicit header citation. `plan.md:71` cross-references `AC-LDBARMAP-004(a~d)` as the M-추가 milestone's pass condition. No orphaned REQ/AC. |

Harmonic mean: 4 / (1/0.50 + 1/1.0 + 1/0.50 + 1/1.0) = 4/6 = **0.667** < 0.80 pass line → **FAIL**.

## Numeric-citation verification (independent re-derivation against source files)

All numeric claims in the diff were independently re-derived against the cited `.txt` evidence files (not merely pattern-matched):

| Claim (file:line) | Source file / row | Verified |
|---|---|---|
| LOVE ATTACK grid-lock raw 0.29→0.61 (med→reg) — `spec.md:72`, `research.md:117-120` | `probe_songs.txt:2` (`0.29`/`0.61` in the raw columns) | ✅ exact |
| 3/10 songs flip to false-double at reg BPM (LOVE ATTACK/Let's Dance/LoveMe) — `spec.md:72` | `probe_songs.txt:2,6,7` (adopt@reg columns doubled: 224.004/240.061/199.988) | ✅ exact, and the other 7 rows do not double |
| LOVE ATTACK n=326, p_mid=2.34e-38 — `acceptance.md:66` | `probe_sign.txt:2` | ✅ exact |
| max real-song p_mid=9.37e-04 (Ice cream, n=122) — `acceptance.md:66` | `probe_sign.txt:5` — max of column across all 10 rows confirmed by hand (2.34e-38, 7.00e-10, 2.07e-10, 9.37e-04, 6.52e-18, 7.02e-28, 6.31e-57, 3.21e-27, 3.10e-85, 7.96e-05) | ✅ exact |
| 6/10 songs significant on p_two at α=0.01 — `acceptance.md:72`, `research.md:153` | `probe_sign.txt` p_two column: significant = Club Diver, Let's Dance, LoveMe, Rain, Too Cool, scott-buckley-neon (6); not significant = LOVE ATTACK, Cut and Run, Ice cream, Morning (4) | ✅ exact, 6/10 |
| AC-004a: w_mid=0.54/p_mid=0.845 (224→112) and w_mid=0.62/p_mid=0.999 (240→120) — `acceptance.md:54` | `probe_synth.txt` rows "224 같은 세기(참 224)" and "240 같은 세기(참 240)" | ✅ exact |
| AC-004b: w_mid=0.24/p_mid=8.98e-12 and (secondary) p_mid=2.63e-06 — `acceptance.md:60` | `probe_synth.txt` rows "112 박+8분 하이햇 0.3" and "112 킥/스네어 1.0/0.6 +8분0.3" | ✅ exact, but see Clarity/Testability — the **primary** number is sourced from the non-kick/snare row despite the Given labeling it as kick/snare |
| AC-004d: w_mid=0.46/p_mid=0.195; p_two=4.11e-11 (56+8th) / 1.83e-04 (kick/snare+8th) — `acceptance.md:72` | `probe_synth.txt` rows "112 박+8분 하이햇 0.7", "56 박+8분 0.3(참 56)", "112 킥/스네어 1.0/0.6 +8분0.3" | ✅ exact, same mislabel issue on the primary case |

No fabricated or unverifiable number was found anywhere in the diff.

## Supervisor Principle (Group 1) — no violation found

REQ-LDBARMAP-006's two new constants (α=0.01, symmetry point 0.5, `acceptance.md:18-19`) are
general statistical conventions, not fitted to the 10-song set: `probe_sign.py:29`/`probe_synth.py:49`
hardcode `binomtest(..., 0.5, alternative="greater")` — the 0.5 null and the `alternative="greater"`
one-sidedness are scipy's standard binomial-test parameterization, independent of any observed data.
The measured margins give no evidence of tuning: all 10 real songs land at p_mid ≤ 9.37e-04, roughly
an order of magnitude below even the looser conventional α=0.05, so the classification outcome for
every probed case (real-song and synthetic) is unchanged whether α=0.01 or α=0.05 is used — the
specific α value was not load-bearing for making the 10-song set "pass." AC-LDBARMAP-004c explicitly
disclaims circularity ("이 결과는 문턱... 을 정하는 근거가 아니라 로컬 대조군이다", `acceptance.md:66`) and
plan.md:69 states the same ("순환 금지"). One process-hygiene observation (not a demonstrated
violation, listed as D3 below): the real-song probe (`probe_sign.py`) was run before the synthetic
ground-truth probe (`probe_synth.py`) by file mtime (23:49 vs 23:50), which is the methodologically
backward order (synthetic ground-truth calibration should precede real-data application) — flagged
as optional, since the robustness margin above shows no actual overfitting resulted.

## Logic coverage (Group 5) — no gap found

The three-way judgment table (`p_mid < α` → keep; `p_mid ≥ α AND w_mid ≥ 0.5` → adopt_double; else →
keep+ambiguous, `acceptance.md:48`) is exhaustive and non-overlapping over the (p_mid, w_mid) domain.
"Half is never auto-adopted" is stated consistently in both `spec.md:72` and `acceptance.md:72`, and
AC-004d explicitly makes the non-distinguishability itself a PASS condition ("이 구별 불가능성 자체가
PASS 조건이다", `acceptance.md:72`). The known out-of-scope split (median-vs-regression BPM basis) is
explicitly named in `plan.md:70` as already separated by card t546 and not assumed by this redesign.

## Defects Found

D1. GIVEN-THEN-MISMATCH-004b — `acceptance.md:58` — AC-LDBARMAP-004b's **Given** clause ("112 BPM 킥/스네어 패턴에 세기 0.3의 8분음표 하이햇이 섞인 합성 신호") describes a kick/snare-alternating pattern, but the primary cited **Then** statistics (w_mid=0.24, p_mid=8.98e-12, `acceptance.md:60`) are measured from `probe_synth.py`'s uniform-intensity "112 박+8분 하이햇 0.3" case (`pattern=[[1.0, 0.3]]`, line 33), not from the actual kick/snare case ("112 킥/스네어 1.0/0.6 +8분0.3", `pattern=[[1.0,0.3],[0.6,0.3],[1.0,0.3],[0.6,0.3]]`, line 35, which the AC cites separately with only its p_mid=2.63e-06, no matching w_mid). — Severity: major — Class: blocking — Required fix: rewrite the AC-004b Given to accurately describe the primary rendered case ("112 BPM 균일한 세기의 박에 세기 0.3의 8분음표 하이햇이 섞인 합성 신호"), and keep the genuine kick/snare case as the explicitly-labeled secondary confirmation it already is in the Then clause.

D2. GIVEN-THEN-MISMATCH-004d — `acceptance.md:70` — Same defect pattern: AC-LDBARMAP-004d's **Given** ("112 BPM 킥/스네어 패턴에 세기 0.7(강함)의 8분음표 하이햇이 섞인 합성 신호") mislabels the case producing the cited Then numbers (w_mid=0.46, p_mid=0.195, `acceptance.md:72`), which are measured from the uniform-intensity "112 박+8분 하이햇 0.7" row (`pattern=[[1.0, 0.7]]`, `probe_synth.py:34`). Unlike AC-004b, there is no corresponding kick/snare+0.7 case anywhere in `probe_synth.py`'s `CASES` list (lines 31-39) to even serve as a secondary confirmation — the "킥/스네어" framing here has no supporting measurement at all. — Severity: major — Class: blocking — Required fix: correct the Given to "112 BPM 균일한 세기의 박에 세기 0.7(강함)의 8분음표 하이햇이 섞인 합성 신호"; if a genuine kick/snare+0.7 ambiguous-boundary case is desired as evidence, add it to `probe_synth.py`'s `CASES` and re-run, citing the new measured numbers.

D3. PROBE-ORDERING-HYGIENE — `.moai/reports/t547/probe_sign.py` (mtime 23:49) vs `probe_synth.py` (mtime 23:50) — the real-song sign-test probe was executed before the synthetic ground-truth calibration probe, the methodologically backward order for establishing a threshold without circularity. No overfitting is evidenced (per Supervisor Principle section above — all 10 real songs clear α=0.01 by roughly 10x margin, and the classification is insensitive to α within the 0.01-0.05 conventional range), so this is process hygiene rather than a demonstrated defect. — Severity: minor — Class: optional — Required fix: none required for this amendment; for future redesigns of this kind, write and run the synthetic ground-truth probe first, then the real-song local-control probe, to make the non-circularity structurally evident rather than argued after the fact.

D4. GEARS-COMPOUND-REQ-STYLE — `spec.md:72` — REQ-LDBARMAP-006 carries one explicit "shall" (the beat-grid-basis mandate) followed by several further normative behaviors in plain present tense (the keep/adopt_double/ambiguous classification logic, and the "매 판정마다 ... 전부 기록한다" per-judgment logging requirement) without a repeated modal. This mirrors the SPEC's pre-existing compound-REQ style (REQ-LDBARMAP-004 and REQ-LDBARMAP-005 use the same single-shall-plus-plain-tense-elaboration pattern), so it is not a defect newly introduced by this amendment, but is flagged per M3's single-modal-per-REQ scrutiny as a point the author should be aware the convention carries forward. — Severity: minor — Class: optional — Required fix: none required to accept this amendment (would require a SPEC-wide style change affecting REQ-004/005 too, out of this amendment's scope); optionally hoist the logging/classification obligations into their own "shall" clauses in a future full style pass.

## Regression Check (Iteration 2+ only)

Not applicable — this is iteration 1 of the card-t547 amendment's delta audit. No prior iteration of this specific amendment exists to check for regression.

## Recommendation

FAIL — fix D1 and D2 (both blocking) before re-audit:

1. In `acceptance.md:58`, rewrite AC-LDBARMAP-004b's **Given** sentence to describe the actual primary synthetic case ("112 BPM 균일한 세기의 박에 세기 0.3의 8분음표 하이햇이 섞인 합성 신호", matching `probe_synth.py`'s "112 박+8분 하이햇 0.3" row) rather than a kick/snare pattern. Keep the existing secondary kick/snare sentence as-is (it is correctly labeled and correctly cited).
2. In `acceptance.md:70`, apply the same correction to AC-LDBARMAP-004d's **Given** sentence ("112 BPM 균일한 세기의 박에 세기 0.7(강함)의 8분음표 하이햇이 섞인 합성 신호"). Since no kick/snare+0.7 case exists in `probe_synth.py`, either drop the kick/snare framing entirely or add the case to the script and cite the newly-measured numbers if that confirmation is wanted.
3. D3 and D4 are optional — no action required to pass re-audit, but D3's probe-ordering note may be worth carrying into `research.md` §11 as a documented methodological caveat for future redesigns.
4. After the Given-clause corrections, re-run the numeric-citation verification table above for the two affected rows (should remain unchanged, since only the Given prose — not the cited numbers — needs to change) and re-submit for a scoped re-audit of AC-LDBARMAP-004b/d only.

---

# Iteration 2 — Scoped Delta Re-Audit (card t547, D1/D2 fix + PASS-condition redesign)
Verdict: PASS
Overall Score: 0.923 (harmonic mean; pass line 0.80)

Reasoning context ignored per M1 Context Isolation. Re-read only the current
`git -C <worktree> diff -- .moai/specs/SPEC-LDBARMAP-001/` plus `.moai/reports/t547/probe_synth.py`'s
source (for the shared-RNG claim check below). Per the Retry Loop Contract, this re-audit is scoped to
the enumerated iteration-1 defect delta (D1, D2) plus the coordinator's one named extra change
(PASS-condition redesign) — not a from-scratch full re-audit.

## Diff-scope verification (what actually changed since iteration 1)

Confirmed via `git diff --numstat` + byte-identical hunk comparison against the iteration-1 diff
snapshot (`/tmp/t547_spec_diff.txt`): **only `acceptance.md` and `progress.md` changed.**
`spec.md`, `plan.md`, and `research.md` diff hunks are byte-identical to what iteration 1 reviewed —
confirmed with `diff` against saved iteration-1 hunks (zero output beyond the `diff --git` header
line consumed by the range-extraction `awk`). REQ-LDBARMAP-006's GEARS text, the §A constants
table, the judgment-table logic, and the Group-5 logic-coverage findings from iteration 1 therefore
all still hold unchanged and are not re-litigated here.

- `acceptance.md`: 32 insertions / 6 deletions (iteration-1 total was lower; the delta is the new
  "교정 이력 2" blockquote at `acceptance.md:50` plus reworded Given/Then text in AC-004a-d).
- `progress.md`: 9 insertions / 0 deletions — new line `progress.md:44` recording the iteration-1
  fix.
- `spec.md` / `plan.md` / `research.md`: unchanged (confirmed, not merely assumed).

## Must-Pass Results (re-verified, all unaffected by this delta)

- [PASS] MP-1 REQ number consistency: unchanged, 16 sequential IDs confirmed again (`grep -oE 'REQ-LDBARMAP-[0-9]+' spec.md | sort -u | wc -l` → 16).
- [PASS] MP-2 EARS/GEARS format compliance: `spec.md` byte-identical to iteration 1 — REQ-LDBARMAP-006's `While...shall` form unchanged.
- [PASS] MP-3 YAML frontmatter validity: unchanged (version still `"0.1.7"`).
- [N/A] MP-4: unchanged, single-domain SPEC.
- [PASS] MP-5 D7 cross-SPEC reconciliation: `grep -E '^\+' /tmp/t547_spec_diff_iter2.txt | grep -oE 'SPEC-[A-Z][A-Z0-9]*-[0-9]+' | sort -u` → only `SPEC-LDBARMAP-001` (self). No new cross-SPEC reference introduced by this delta.
- [PASS] MP-6 D8 cross-platform discipline: `grep -n "syscall" acceptance.md progress.md` → no matches in the changed files.
- [PASS] MP-7 clarification gate: `plan.md`/`research.md` unchanged (and already clean at iteration 1).
- REQ/AC ceiling re-confirmed: 16/16, unchanged.

No must-pass firewall failure.

## D1/D2 resolution check

**D1 (acceptance.md:58, AC-LDBARMAP-004b) — RESOLVED.** The Given now reads "112 BPM **균일한 세기**의
박에 세기 0.3의 8분음표 하이햇이 섞인 합성 신호가 결정적 시드로 1회 렌더된 상태에서(`probe_synth.py`
"112 박+8분 하이햇 0.3" 케이스 — 박 자체는 킥/스네어 교대가 아니라 균일 세기다, plan-audit D1 교정)" —
accurately describes the case that produces the cited primary Then numbers. The Then clause now
additionally and explicitly flags which sentence is the genuine kick/snare confirmation: "이 두 번째
문장만 실제로 킥/스네어 패턴을 쓴다" — this is a clean, unambiguous resolution; better than merely
correcting the noun, it also pre-empts the reader making the same mistake again.

**D2 (acceptance.md:70, AC-LDBARMAP-004d) — RESOLVED.** The Given now reads "112 BPM **균일한 세기**의
박에 세기 0.7(강함)의 8분음표 하이햇이 섞인 합성 신호가 결정적 시드로 1회 렌더된 상태에서(`probe_synth.py`
"112 박+8분 하이햇 0.7" 케이스 — 균일 세기 박이며 킥/스네어 패턴이 아니다; `probe_synth.py`의 `CASES`
목록에는 킥/스네어+0.7 조합 케이스가 존재하지 않는다, plan-audit D2 교정)" — this goes further than the
minimum fix by also stating the absence of a kick/snare+0.7 case in the script, which was the original
D2 finding's second half (no measurement existed to even confirm a kick/snare framing). Fully resolved.

Numeric-citation re-verification (the decimals must be unchanged, only their framing should differ):
all `참고 실측` (reference-measurement) parentheticals in AC-004a-d — w_mid=0.54/p_mid=0.845 (224),
w_mid=0.62/p_mid=0.999 (240), w_mid=0.24/p_mid=8.98e-12 (004b primary), p_mid=2.63e-06 (004b
secondary kick/snare), p_mid=2.34e-38/n=326 (004c), p_mid=9.37e-04/Ice cream/n=122 (004c secondary),
w_mid=0.46/p_mid=0.195 (004d), p_two=4.11e-11 and p_two=1.83e-04 (004d secondary) — are byte-identical
to the numbers independently re-derived from `probe_synth.txt`/`probe_sign.txt` in the iteration-1
table above. No new numeric error introduced.

## No new inconsistency found

- `acceptance.md` §A constants table (lines 16-24, the 56.175/224.69 footnotes and the new α/0.5 rows)
  is byte-identical to iteration 1 — untouched by this delta.
- The "교정 이력 2" blockquote (`acceptance.md:50`) is append-only (stacked under the existing "교정
  이력" blockquote at line 48), matching this SPEC's established HISTORY-preservation convention
  (e.g., the `spec.md` HISTORY table's D1-D8 chained-correction rows) — no prior record was deleted
  or silently rewritten.
- `progress.md:44` accurately summarizes the fix and correctly names D1/D2 and the outcome+inequality
  redesign; consistent with the `acceptance.md` content it describes.
- The REQ/AC-count-unchanged claims ("16/16 그대로") in both the new `acceptance.md:50` blockquote and
  `progress.md:44` are re-confirmed true by direct grep (above), not merely asserted.

## The coordinator's extra change — PASS-condition redesign (outcome+inequality, decimals demoted)

This is a genuine, well-justified improvement, not cosmetic hedging. Verified against
`probe_synth.py` source: `rng = np.random.default_rng(547)` is a **single module-level RNG object**
consumed by both `click()` and `render()`, and the `for name, bpm, pat in CASES:` loop
(`probe_synth.py:42`) calls `render()` **sequentially across all 8 cases using that one shared RNG**.
This means each case's exact noise realization depends on the RNG stream position left behind by
every case rendered before it in the loop — re-rendering a single case in isolation (as a future
run-phase test fixture would do, not re-running the whole 8-case script) consumes a *different*
segment of the RNG stream and will NOT reproduce the exact `probe_synth.txt` decimal, even with the
same seed=547. The "교정 이력 2" blockquote's claim — "run-phase 테스트가 같은 시드로 재렌더해도 그
값이 정확히 재현되지 않는다" — is therefore **technically accurate**, not a defensive overstatement.
Demoting the probe decimals to "참고 실측" and making the PASS condition the keep/adopt_double/
ambiguous **outcome** plus the **deciding inequality** (`p_mid < α` / `p_mid ≥ α AND w_mid ≥ 0.5` /
else) is the correct fix — the outcome and the inequality are robust to the RNG-stream-position
difference for every case except the one sitting closest to the decision boundary (see below).

## AC-LDBARMAP-004d testability assessment (coordinator's specific question)

**Testable, but with a real residual risk that should not be waved off.** Two things are true at once:

1. **The literal test, once implemented, is deterministic.** `beat_track`, `onset_strength`, and
   `binomtest` are all deterministic algorithms given a fixed input signal; AC-004d's own instruction
   — "run-phase 테스트는 이 AC가 결정적 시드로 직접 생성하는 신호에 대해 outcome=keep AND
   ambiguous=true를 단언해야 하며, probe의 소수값 재현을 목표로 삼지 않는다" — correctly tells the
   implementer to assert against self-generated output rather than hunt for the probe's exact decimal.
   This is sound test design and is NOT flaky in the conventional sense (same seed + same code path →
   same result, every run).

2. **The specific case chosen is explicitly near the decision boundary** — w_mid=0.46 is only 0.04
   away from the adopt_double threshold (0.5), and this is the AC's own framing ("판정 경계 가까이
   있다"). Per the RNG-sharing mechanics above, whatever render context a future run-phase test
   fixture actually uses (which seed, isolated call vs. looped-through-prior-cases) will NOT
   necessarily reproduce `probe_synth.txt`'s observed w_mid=0.46/p_mid=0.195 — it will reproduce
   *some* deterministic (w_mid, p_mid) pair for that specific render, but there is no guarantee that
   pair lands in the `keep+ambiguous` region rather than tipping into `adopt_double` (if noise pushes
   w_mid just over 0.5 while p_mid stays ≥ α) or plain `keep` (if noise pushes p_mid under α). The AC
   commits to a specific expected outcome without pinning the exact render call (seed value +
   isolation from the other 7 cases' RNG consumption) needed to reliably reproduce it.

**Net assessment: this is a real, specific implementation risk for the run-phase milestone — not a
defect in the plan-phase document's internal correctness, traceability, or logical coverage.** It is
recorded below as D5 (optional, not blocking this iteration's PASS) because the AC's conceptual
claim (the design has an honest ambiguous boundary, and that boundary is exercisable by a synthetic
case) is sound and well-evidenced; what's missing is pinning the concrete render parameters so a
future implementer does not have to re-derive them under time pressure.

## Category Scores (0.0-1.0, rubric-anchored) — iteration 2

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 1.0 | "Every requirement has a single, unambiguous interpretation." | D1/D2 resolved — AC-004a-d Given clauses now accurately describe their rendered scenarios (`acceptance.md:58,70`), and the Then clauses' PASS condition is now unambiguously the outcome+inequality, not a decimal. |
| Completeness | 1.0 | unchanged — all sections present, now with the additional "교정 이력 2" record and `progress.md:44`. |
| Testability | 0.75 | "One AC is not precisely binary-testable but is measurable with minor interpretation." | AC-004a/b/c are now cleanly, robustly testable (outcome+inequality, far from any boundary). AC-004d (1 of 4 sub-criteria) carries the near-boundary seed-realization risk detailed above — testable as literally instructed, but fragile without a pinned render context. |
| Traceability | 1.0 | unchanged — REQ-006 ↔ AC-004(a-d) traceability intact; no orphaned REQ/AC. |

Harmonic mean: 4 / (1/1.0 + 1/1.0 + 1/0.75 + 1/1.0) = 4/4.333 = **0.923** ≥ 0.80 pass line → **PASS**.

## Defects Found — iteration 2

D1, D2 (iteration 1) — RESOLVED, confirmed above with evidence.
D3, D4 (iteration 1) — still optional/informational, unchanged status, not re-litigated (no new evidence to add).

D5. AC-004D-BOUNDARY-FRAGILITY (new) — `acceptance.md:70-72` — AC-LDBARMAP-004d asserts a specific outcome (`keep` + `ambiguous`) for a synthetic case explicitly described as near the decision boundary (w_mid=0.46 vs. the 0.5 adopt_double threshold), but does not pin the exact render parameters (seed value AND isolation from the other 7 `CASES` entries' shared-RNG consumption in `probe_synth.py:42`) that a run-phase test fixture must reuse to reliably reproduce that outcome. Because `probe_synth.py`'s `rng = np.random.default_rng(547)` is a single object consumed sequentially across all 8 cases in the loop, re-rendering this one case in isolation (as a standalone run-phase test fixture naturally would) consumes a different RNG-stream segment and is not guaranteed to land in the same `keep+ambiguous` outcome bucket. — Severity: major — Class: optional (does not block this iteration's PASS; is a run-phase implementability risk, not a plan-document correctness defect) — Required fix (before or during run-phase M-추가 implementation): either (a) pin the exact render call the run-phase test must use — e.g. "call `probe_synth.py`'s `render(112, 90.0, [[1.0, 0.7]])` with a freshly-seeded `np.random.default_rng(547)` passed as an explicit parameter, not the shared module-level RNG" — and verify once at implementation time that this reproduces `keep+ambiguous`; or (b) pick/construct a less boundary-adjacent ambiguous case (larger margin from w_mid=0.5) so the outcome is robust to reasonable variation in render context, while keeping AC-004d's conceptual purpose (demonstrate the self-acknowledged ambiguous-boundary limitation) intact.

## Recommendation

PASS. No blocking defects remain. D5 is recorded as a named, evidenced residual risk for manager-develop
to address when implementing AC-LDBARMAP-004d's test fixture during the M-추가 milestone (either option
(a) or (b) in D5's Required fix) — it does not require another plan-audit iteration, since it is a
run-phase implementation concern rather than a plan-phase document defect. Proceed to Implementation
Kickoff Approval for the M-추가 milestone (`_check_bpm_half_double` rewrite) per `plan.md:65-71`.
