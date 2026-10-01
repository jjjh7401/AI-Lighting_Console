# SPEC Review Report: SPEC-LDRENDER-001
Iteration: 3/3
Verdict: PASS
Overall Score: 0.88

Reasoning context ignored per M1 Context Isolation — re-audit scoped to the D1-D12 delta plus the orchestrator's new checklist, per the Retry Loop Contract. All five artifacts re-read in full against commit `a8ec2bda` ("감독 결정 4건 반영 — 역할 어휘 확장·켜진 층만 셈·층별 색·FXGEN 페이저 생성"). Per the lead's note, this re-audit proceeds despite the iteration-2 score-drop STOP because new director-decision input is a legitimate re-entry condition, not unconditional continuation.

## D1–D12 Final Closure Status

| ID | Status | Evidence (iter3) |
|----|--------|-------------------|
| D1–D10 | **CLOSED** (unchanged from iter2, re-verified present) | spec.md §4 t497 OUT; REQ-004 ≤2-color guard; REQ-007/AC-006 4-value-line scope; AC-016 "AC-001~015"; progress.md "AC 16개"; `While`/`When` keywords; literal `[NEEDS CLARIFICATION:]` markers (now fully resolved, see below). |
| D11 | **CLOSED** | acceptance.md:5-11 AC-001 rewritten: "구간 큐 **전부**... '과반 이상'/'대다수' 등 완화된 기준은 **쓰지 않는다** — 단 1개 큐라도 미달이면 FAIL." spec.md REQ-001 (line 53) carries the identical language. REQ-013/014 (R7 gate, spec.md:87-88) and AC-012/013 (acceptance.md:87-101) apply the same all-cues bar — cross-checked for consistency, no divergence found. |
| D12 | **CLOSED** | spec.md §3.1 `[HARD — D11/D12 + 감독 결정 1/2 전제]` (line 49) explicitly retracts the iter1 "key/back/effect already achieves 3 layers" claim: "LIT-only 집계 규칙... 이 규칙을 적용하면... '키/백/이펙트 세 역할만으로 3층 목표가 이미 달성된다'는 **성립하지 않는다**... 남는 것은 key·back 둘뿐이다(버킷 2개)." AC-001 (acceptance.md:11) makes the dependency explicit: "이 AC는 `key`+`back`만으로는 PASS할 수 없고 `side`/`wash`/`mover`(REQ-002) 중 최소 1개가 그 큐에서 LIT 값을 받아야 한다." The effect-tracked-off state is explicitly excluded from the bucket count (REQ-001, AC-001 Then clause: "디머>0(LIT)인 역할만... 세며"). The gaming vector identified in iteration 2 — reaching "3 buckets" via a non-visible off-state — is structurally closed: 3 LIT buckets now require 3 **actively, distinctly lit** role groups, which is exactly what the director's 0/5 complaint was about. |

**All 12 prior defects are closed with direct textual evidence**, not merely asserted.

## Verification of the 4 Director Decisions — Faithful Encoding (no silent narrowing/widening)

| # | Director decision (as relayed) | SPEC encoding | Verdict |
|---|---|---|---|
| 1 | Role vocabulary option (a) — extend `song-lighting-design-standard.md` §2c with side/wash/mover (version bump) + extend `RIG_LAYER_ROLES`, in this SPEC's scope | REQ-002 (spec.md:54) requires BOTH the doc §2c edit+version-bump AND the `RIG_LAYER_ROLES` tuple extension as one `shall` ("두 자산을 함께 바꾼다"); plan.md M2 (new milestone, lines 83-89) scopes the doc edit as an in-SPEC run-phase deliverable, not deferred. Matches the decision exactly — no narrowing (doc edit was NOT dropped as "out of this SPEC"), no widening (no extra roles beyond side/wash/mover introduced). | **Faithful** |
| 2 | Dimmer-0 layers do NOT count; AC = every section cue has ≥3 LIT layers with distinct values, no majority wording | AC-001/REQ-001/REQ-013/REQ-014 all rewritten in lockstep (see D11/D12 table above); "과반"/"대다수" literal-grepped absent from acceptance.md and spec.md (re-confirmed this iteration: `grep -n "과반\|대다수" acceptance.md spec.md` → 0 matches outside the historical HISTORY-log sentence describing what was *removed*). Two narrow, pre-existing, named exceptions (blackout cues, MIB pre-move cues) are added — both are structurally non-"normal-lit" cue kinds already distinct in the codebase (`cue.dimmer.blackout`, `cue.kind == "mib_premove"`), not a reintroduction of a broad leniency; MIB pre-move cues were never part of the "구간 큐" (section-cue, `kind=="section"`) population to begin with, so that exception is a clarification rather than a new carve-out. | **Faithful, no majority-loophole re-creation** |
| 3 | Layer→colour: back+mover=primary, side+wash=secondary, key=warm white (§4b C3) | REQ-004 (spec.md:63): "`back`+`mover` 역할 그룹에 지배색(`palette[0]`), `side`+`wash` 역할 그룹에 보조색(`palette[1]`), `key` 역할 그룹에... 중립/웜 화이트" — verbatim match. | **Faithful** |
| 4 | R4 option (a) — create missing phasers via FXGEN/FXLIB, through existing approval gate, pool-number collision read as an AC | REQ-011 (spec.md:80) confirms option (a) as the sole path (option (b) explicitly "제거"), mandates gate reuse ("기존 승인 게이트... 새 무승인 경로를 만들지 않는다") and adds collision detection reusing FXLIB's existing reason-code enum. AC-010 (acceptance.md:70-78) encodes BOTH the gate-reuse requirement and a dedicated collision-control Given/When/Then with its own measurement command. Collision reason codes verified against actual source: `server/fx/instantiate.py:47-50,81-84,296,339` — `PRESET_POOL_UNAVAILABLE`/`PRESET_POOL_TRUNCATED`/`PRESET_NUMBER_UNAVAILABLE`/`PRESET_OCCUPIED` all exist exactly as cited, `select_preset_number` exists at line 296. | **Faithful, citations verified accurate** |

No decision was silently narrowed (scope quietly dropped) or widened (unrequested scope added) in translation into REQ/AC text.

## REQ-002 Test-Inversion Statement — Confirmed Present in All 3 Artifacts

`server/tests/test_layer_mapping_effect_role.py:119` `test_mover_and_wash_groups_remain_unmatched_documented_residual` is explicitly named as a test whose assertion **must be deliberately inverted** (not silently broken) in:
- spec.md REQ-002 body (line 54): "그 단언은 **거짓이 된다**(이제 매칭됨)... 테스트명·단언·docstring을 갱신한다(조용히 깨뜨리지 않는다)."
- plan.md M2 step ⑥ (line 85): "**의도적으로 뒤집는다** — 테스트명·단언·docstring을 함께 갱신"
- acceptance.md AC-002 item (5) (line 18): "뒤집음이 테스트명·단언·docstring 갱신과 함께 명시적으로 이뤄졌다(조용히 깨지지 않았다)"

All three consistently require the same disciplined inversion (rename + reassert + re-docstring), not a bare flip. **Confirmed adequately stated.**

## R4 Gate-Reuse and Collision AC — Measurability Check

- **No new ungated path**: AC-010 (acceptance.md:74) requires "그 생성 커맨드는 **기존** `run_commands` → `gate.screen()` 승인 게이트를 통과한다(새 무승인 경로가 생기지 않았음을 `grep`으로 확인 가능해야 한다)" — a concrete, re-runnable grep-based check, not a prose assurance. plan.md §D also restates this as a hard constraint ("M6의 페이저 생성도 이 단일 관문을 통과한다 — 새 무승인 실행 표면 금지").
- **Collision AC measurable**: AC-010's second Given/When/Then block (acceptance.md:75-77) names the exact reason-code enum and ties it to `grep -rn "gate.screen\|run_commands" <페이저 생성 모듈>` + `pytest ... -k "preset_occupied or collision"` + a new unit test. This is binary-testable (either the grep finds the gate call, either the reused reason code fires, or not).

**Confirmed adequately gated and measurable.**

## The Two Author Flags — Surfaced Correctly, Director-Decision Assessment

**Flag (i) — does `key` warm-white count toward §6.3's max-2 simultaneous colors?**
Correctly surfaced as an explicit, un-silenced flag: spec.md §3.2 `[HARD]` (line 59) states both readings, names the SPEC's chosen interpretation (warm-white excluded from the count, grounded in §4b C1's "+화이트/CTO" aside), and explicitly says "이 읽음이 유일한 해석은 아니다" — not resolved by invention. AC-004(b) (acceptance.md:32) and the 경계 사례 section (acceptance.md:153) both repeat the flag and tie it to AC-004(b)'s measurement. **Correctly flagged, not silently resolved.**
- **Director-decision recommendation: YES, recommend a quick confirmation before Implementation Kickoff Approval** (not a hard blocker to PASS, but cheap to ask now vs. expensive to discover after M4 lands). The SPEC's own stance is to defer re-confirmation to "if run-phase proves it wrong" — given M4 is a non-trivial color-rendering milestone and the interpretation bears directly on compliance with a cited normative design standard (§6.3), asking the one-line question ("does warm-white count toward the 2-color cap?") at Kickoff costs one AskUserQuestion round and forecloses a possible M4 rework.

**Flag (ii) — does a rig with no side/wash/mover groups structurally fail AC-001?**
Correctly surfaced: spec.md §3.1 `[HARD]` (line 49), plan.md §B 위험 8 / M3 precondition (line 97), and acceptance.md 경계 사례 (line 150) all state the same boundary case — explicitly declared out of the 4 decisions' scope, not papered over. **Correctly flagged, not silently resolved.**
- **Director-decision recommendation: NOT needed before run, but a cheap M1/M2 pre-flight verification is worth adding.** Cross-checking against already-measured evidence from this SPEC's own inputs: `.moai/reports/t498/verdict.md` §"리허설 대 실기 차이 전량 분류" records that the actual production rig's realtime fixture-name readout (`run4_w_fixture_names.txt`) already identified `MOVER-D 521~528` and `WASH-U 401~410`/`WASH-D 421~430` groups physically present on console. So for the actual 8-song production rig, the "2-role residual rig" edge case this flag warns about is likely **not live** — WASH and MOVER groups already exist. SIDE-group presence was not independently confirmed in the artifacts read. Recommend M1 or M2 add one read-only check (console group-list re-query) confirming SIDE-L/R or at minimum that ≥1 of side/wash/mover resolves on the target rig, so the structural-failure case is ruled out mechanically rather than discovered at AC-001 measurement time.

## Tier M Ceilings and the REQ-002/REQ-011 Merge

- **REQ count**: 16 (`grep -c "^| REQ-LDRENDER-"` → 16), **AC count**: 16 (`grep -c "^## AC-LDRENDER-"` → 16) — both exactly at the Tier M ceiling (16/16), neither exceeded. Per spec-workflow.md, being at the ceiling is compliant; it does mean the SPEC has **zero headroom** left on either axis — a minor process note, not a defect: if run-phase's Re-planning Gate surfaces a genuine need for a 17th REQ or AC, the SPEC would need either a merge-again or a Tier bump, not a simple addition.
- **Merge-induced testability check**: progress.md:8 and spec.md HISTORY both explicitly confirm the REQ-002/REQ-011 merge was deliberate, done specifically to stay within the 16/16 cap, per instruction ("넘겼다면 병합하거나 티어 상향을 보고하라는 지시에 따른 선택").
  - **REQ-011 / AC-010**: the merge bundles gate-reuse + pre-generation + collision-detection + 2-step-pattern into one REQ, but AC-010 structures this as TWO independent Given/When/Then scenarios (normal generation; collision), each separately measurable — not degraded by the merge.
  - **REQ-002 / AC-002**: the merge bundles FIVE conjunctive assertions into one AC — (1) doc version bump, (2) `RIG_LAYER_ROLES` tuple contains the three roles, (3) `_build_layers` accepts without `RigProfileError`, (4) prefix-token group-name interpretation, (5) the named test's deliberate inversion. Each individual condition is independently measurable (AC-002's "측정" line lists 4 distinct commands covering all 5), but **AC-002 does not state whether partial satisfaction (e.g., 4 of 5 pass, the test-inversion forgotten) counts as AC-002 PASS or FAIL** — unlike AC-013, which explicitly states "두 대조군이 한 쌍으로 PASS해야... 어느 한쪽만 PASS하면 공허한 검사." This is a minor testability gap, not an untestability — AC-002 remains testable as a conjunction (each sub-condition has a command), but the PASS/FAIL aggregation rule for the bundle is implicit rather than stated.

## Updated Category Scores

| Dimension | iter2 | iter3 | Rationale |
|-----------|-------|-------|-----------|
| Clarity | 0.80 | 0.92 | D11/D12 fully resolved with explicit, repeated "every cue, no majority" language cross-checked across 5 locations (REQ-001/013/014, AC-001/012/013). Two residual flags correctly surfaced, not hidden. |
| Completeness | 0.85 | 0.92 | §5 open decisions: 0 remaining (all 4 director decisions encoded); HISTORY log fully documents the D11/D12 resolution mechanism. |
| Testability | 0.70 | 0.85 | D3's 4-value-line scope holds; R4 gate/collision ACs are concretely measurable (grep + pytest); residual gap is AC-002's unstated bundle-aggregation rule (minor, not blocking). |
| Traceability | 0.90 | 0.92 | REQ→AC table unchanged in structure, still orphan-free; 16/16 ceiling reached on both axes with no slack — informational note, not a traceability defect. |

Weighted toward the skeptical-evaluation stance (no must-fail present this iteration, per-dimension average ≈0.90, light discount for the two optional findings below): **Overall Score: 0.88** — clears the Tier M PASS threshold (0.80).

## Must-Pass Results

- [PASS] MP-1 REQ numbering — 16, sequential, no gaps/dupes (re-confirmed via grep).
- [PASS] MP-2 GEARS compliance — unchanged, no regressions introduced by the merge (REQ-002/REQ-011 both still single `shall`-bearing GEARS statements with sub-clauses, not mixed informal language).
- [PASS] MP-3 Frontmatter — unchanged, all 12 fields present and correct.
- [N/A] MP-4 — unchanged, single-language project.
- [PASS] MP-5 D7 — unchanged, all related_specs completed/non-blocking; new citation to SPEC-COPILOT-FXLIB-001 REQ-FXLIB-012 verified (`status: completed`, re-checked this iteration — no change from prior iterations).
- [N/A] MP-6 — unchanged, no syscall mentions.
- [PASS] MP-7 — **0 remaining `[NEEDS CLARIFICATION: ...]` markers** (re-confirmed via `grep -n '\[NEEDS CLARIFICATION:' spec.md plan.md acceptance.md research.md progress.md` → no matches outside a HISTORY-log sentence describing a retired iteration-1 marker). All 4 director decisions close out the markers that existed in iteration 2.

All must-pass criteria PASS or N/A.

## Defects Found (new/residual)

D13. **ac-002-bundle-aggregation-rule-unstated** — `acceptance.md:14-19` — AC-002 bundles 5 conjunctive, independently-measurable sub-conditions (doc version bump / tuple extension / no-exception acceptance / prefix-token naming / deliberate test inversion) under one REQ-002/AC-002 pair (a deliberate Tier-M-ceiling-driven merge, confirmed in HISTORY), but does not state whether all 5 must hold for AC-002 to PASS, unlike AC-013's explicit "두 대조군이 한 쌍으로 PASS해야" discipline for its own two-scenario bundle. — Severity: **minor** — Class: **optional** — Suggested fix (non-blocking): add one sentence to AC-002 — "다섯 조건 전부가 성립해야 AC-002 PASS이다 — 일부만 성립은 FAIL" — matching AC-013's precedent.

D14. **tier-m-ceiling-saturated** — `progress.md:8`, REQ/AC counts — Both REQ (16/16) and AC (16/16) ceilings are now exactly reached, leaving no headroom for a run-phase Re-planning-Gate-triggered new requirement without a merge-again or a Tier bump. — Severity: **informational** — Class: **optional** — No fix required; noted for awareness during run-phase scope-change handling.

(No blocking or major defects this iteration — a genuine improvement over iteration 2's critical D12.)

## Recommendation

**PASS.** Proceed toward Implementation Kickoff Approval. One pre-Kickoff item worth a quick `AskUserQuestion` round to the director (not a blocker, but cheap insurance):

- **Confirm flag (i)**: does `key`'s warm-white count toward §6.3's "max 2 simultaneous colors," or is the SPEC's current reading (excluded) correct? A wrong assumption here risks M4 rework after the fact.

Optional, non-blocking for M1/M2 implementation:
- Add a one-line pre-flight check to M1 or M2 confirming the target rig resolves ≥1 of side/wash/mover (flag ii) — low cost, forecloses a late AC-001 surprise.
- Consider D13's one-sentence AC-002 aggregation-rule addition.

This is iteration 3 of 3 (the Retry Loop Contract ceiling) and the verdict is PASS, so no further escalation is required under the LEAN Workflow STOP provisions.
