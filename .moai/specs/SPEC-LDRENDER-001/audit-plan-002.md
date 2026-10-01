# SPEC Review Report: SPEC-LDRENDER-001
Iteration: 2/3
Verdict: FAIL — **STOP (score regression)**
Overall Score: 0.68 (iter1: 0.74 → iter2: 0.68, regression)

Reasoning context ignored per M1 Context Isolation — this re-audit is scoped to the D1-D10 delta from iteration 1 plus the two orchestrator-spotted concerns, per the Retry Loop Contract; it is not a from-scratch audit. All five artifacts (spec.md, plan.md, acceptance.md, research.md, progress.md) were re-read in full against commit `4f7c73a6` ("감사 1차 반영").

## LEAN Workflow STOP Signal

Per the plan-auditor Retry Loop Contract's LEAN Workflow Additions: iter(N+1) aggregate score (0.68) is **lower** than iter(N) (0.74). This triggers a mandatory STOP — the orchestrator MUST NOT iterate further unconditionally and must present the user three options (reduce scope / accept-with-debt / explicit override), per `askuser-protocol.md`. Rationale for the regression: the revision correctly closed all 10 iteration-1 defects (see delta below), but in doing so it surfaced — rather than introduced — a deeper, pre-existing structural problem in REQ-001/AC-001 that the orchestrator's fresh read caught and iteration 1 missed: the "3-layer-bucket" completion criterion can be satisfied by a trio (key/back/effect) that includes one member (effect) counted only because it is tracked *off*, which does not correspond to any new stage-visible lighting layer. This is not a cosmetic regression; it goes to the SPEC's own stated reason for existing (the director's 0/5 "연출 부재" verdict) — see D12.

## D1–D10 Delta — Closure Status

| ID | iter1 finding | iter2 status | Evidence |
|----|---------------|--------------|----------|
| D1 | t497 judgment missing | **CLOSED** | spec.md:123-127 new `### Out of Scope — 승인 게이트 밖 ClearAll(카드 t497)` section: explicit OUT judgment + rationale (gate-fidelity axis vs. render-restoration axis) + queued-not-dropped disposition. |
| D2 | REQ-004 uncited color-role assignment, §6.3/§6.2 risk | **CLOSED** (assignment → open decision; risk → hard guard) | spec.md:58,62 cites `song-structure-lighting-standard.md` §6.3 and the newly-introduced `docs/proposals/song-lighting-design-standard.md` §4b C1/C3 (verified: C1 "팔레트 3~5색: 베이스1+액센트1~2", C3 "프런트(키층)는 중립/웜 화이트 유지 — 채도 색은 백층·이펙트층에" — citations accurate). REQ-004 now states an explicit, testable ≤2-simultaneous-color cap as a firm REQ (not contingent on the open decision); the specific role→color assignment is correctly demoted to §5 결정 3 `[NEEDS CLARIFICATION: ...]`. AC-004(b) adds the ≤2 machine check independent of decision 3. |
| D3 | AC-006 narrow (dimmer-line-only) verification scope | **CLOSED** | REQ-007 (spec.md:70) and M4 (plan.md:92) now explicitly scope the exclusion to the **shared `fids`** feeding `position_cue_bundle`'s dimmer AND `_song_color_value_lines` AND `_phaser_cue_value_lines` (all four — confirmed against the actual call site `song_cue_render.py:1043-1053` read in iteration 1). AC-006 (acceptance.md:41-46) now asserts the exclusion against all 4 value-line categories individually. |
| D4 | AC-016 self-referential Given (`AC-001~016`) | **CLOSED** | acceptance.md:118 now reads "AC-001~015". |
| D5 | progress.md AC-count error (17/AC-016·017) | **CLOSED** | progress.md:7 now reads "AC 16개(AC-015·016은 전체 REQ 공통 비파괴/인간 판정)" — correct, matches the 16-heading count in acceptance.md. |
| D6 | `RIG_LAYER_ROLES` closed-vocabulary gap, unaddressed | **CLOSED (but see D12)** | spec.md:48 `[HARD — D6 전제]` block + REQ-001 (spec.md:52) scoped to `key`/`back`/`effect` only (within the closed tuple); REQ-002 demoted to `[NEEDS CLARIFICATION: §5 결정 2]` with a 3-option cost table (spec.md:53, plan.md:43-53) correctly identifying the `declared_layers`→`RigProfileError` propagation hazard and a concrete mitigation (option c: filter at `declared_layers` construction). This closes the *immediate implementation-blocking* risk — M2 can proceed without touching `RIG_LAYER_ROLES`. However, the specific device used to close it (restricting the "3+ layer" claim to key/back/effect) is the direct cause of the new D12 finding below — the architectural fix is sound, but the downstream completion-criterion claim built on top of it is not. |
| D7 | REQ-009/M1 read-only not stated | **CLOSED** | spec.md:77 REQ-009 now states "이 측정은 읽기 전용이다(응답기 `state`/`prop` 류 조회만 — 콘솔 쓰기 0건, `exec`/`Store` 류 커맨드 발화 금지)"; plan.md:55-57 adds a dedicated `[HARD]` "M1 읽기 전용 경계 (D7)" subsection; plan.md:71 M1 milestone text repeats "콘솔 쓰기 0건". |
| D8 | (refuted in iter1 — AC-013 two-arm control intact) | **unchanged, still refuted** | acceptance.md:92-100 AC-013 text unchanged; no new issue found. |
| D9 | REQ-003/011 `Where`-keyword nuance (optional) | **CLOSED** | REQ-003 (spec.md:54) now uses `While`; REQ-011 (spec.md:79) now uses `When`. HISTORY (spec.md:25) confirms the intent. |
| D10 | Open decisions not using canonical `[NEEDS CLARIFICATION: ...]` marker (optional) | **CLOSED** | spec.md REQ-002 (line 53), REQ-011 (line 79), §5 결정 1/2/3 (lines 135,137,143) all now carry literal `[NEEDS CLARIFICATION: ...]` markers; progress.md:8 confirms "미해소 `[NEEDS CLARIFICATION]` 마커 3건". |

**8 of 10 fully closed, 1 closed-with-a-caveat (D6), 1 unchanged-and-still-correct (D8).** This is a genuinely competent revision on the process/governance axis. The FAIL verdict below rests entirely on the two orchestrator-spotted concerns, which the delta review above did not surface on its own (they are downstream of the D6 fix, not independent of it).

## Orchestrator-Spotted Concern 1 — "과반 이상" (majority) silent weakening

**CONFIRMED — blocker, undeclared.**

- Card AC (canonical, re-verified via `jq -r '.items[] | select(.id=="t500") | .text' /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.moai/state/kanban/backlog.json`): "...구간 큐 다른 값 층 ≥3..." — a per-section-cue phrasing, no "majority"/"most" qualifier.
- t499's own violation-counting definition for the exact axis this AC exists to fix (`.moai/reports/t499/verdict.md` §2, row "§6.2 층"): "구간 큐 중 무대 층 ≤2 인 큐가 **있으면** 1" — i.e., the pass bar is **zero** cues with ≤2 layers (any single violating cue counts), not "a minority of cues may still violate." This is the exact metric spec.md:28-38 and AC-001 cite as the defect to close.
- acceptance.md:9 (AC-LDRENDER-001, unchanged across both iterations — this was present in iteration 1 too and the iteration-1 audit did not catch it): "...구간 큐가 **전체 구간 큐 중 과반 이상**이다..." — a majority-of-cues bar, strictly weaker than both the card's per-cue phrasing and t499's zero-violating-cues bar.
- No entry in spec.md §5 (open decisions) or anywhere in the revision's HISTORY (spec.md:25) states or justifies this weakening as a director-confirmed decision. It is presented as settled fact.
- **Severity: major — Class: blocking.** Required fix: either (a) tighten AC-001 to "전체 구간 큐 전부" (all cues, matching the card and t499's own bar), carving out only mechanically-necessary exceptions (blackout cues, MIB pre-move cues — already modeled elsewhere in this SPEC, e.g. REQ-003's single-layer bypass) with each exception named explicitly, or (b) if a majority bar is genuinely intended, add it to spec.md §5 as an explicit open decision with a stated rationale, so the director can confirm or reject the weakening before Implementation Kickoff Approval.

## Orchestrator-Spotted Concern 2 — REQ-001/AC-001 metric gaming via the effect-tracked-off bucket

**CONFIRMED — blocker, critical to the SPEC's own purpose.**

Mechanism, traced through the revision's own text and the actual code:

1. REQ-001 (spec.md:52) and its `[HARD — D6 전제]` justification (spec.md:48) restrict the "3+ different-value layers" claim to exactly `key`/`back`/`effect` — SIDE/WASH/MOVER are explicitly excluded and deferred to §5 결정 2, which is itself unconfirmed. AC-001 (acceptance.md:9) states this explicitly: "SIDE/WASH/MOVER 세분화... 없이도 이 AC 는 PASS 해야 한다."
2. AC-001's Then clause names the three buckets as: `key`(또는 전체 기본) 값 · `back` 값 · `effect`(비액센트 큐에서는 공유 `fids` 제외로 **트래킹된 별개 상태**) 값.
3. Per R3/M4 (spec.md:70, plan.md:92 — correctly fixed, see D3 above), `effect`-role fixtures are excluded from the shared `fids` on every non-accent cue — meaning they receive **no command at all** on those cues and simply hold (track) whatever value they last had, which per the song's start/Block safety cue is 0 (off).
4. `back`'s value is `key_pct * 0.8` (or declared `back_pct`) — this relationship **already existed** before this SPEC, and was already measured by t499 as the SPEC's starting point: `.moai/reports/t499/verdict.md` §1 explicitly records the **pre-fix** Rain/8-song baseline as having **2** distinct value buckets already ("최대 2 = 「전체 값」 + 「BACK 만 key×0.8」") — the exact 0-point baseline the director scored "연출이 거의 없다" on.
5. Therefore the *only* bucket this SPEC's R1 work adds, under the current wording, is `effect = 0 (tracked-off)` — a fixture state that is, by construction, **dark** and indistinguishable on stage from "no effect fixture present at all." It is not a new lit layer; it is the restored correctness of R3's independent fix (effect fixtures should stay dark outside accent cues), double-counted here as if it were new audience-visible layering.
6. Meanwhile — exactly as the orchestrator's concern states — `KEY`/`FOH`/`SIDE`/`WASH`/`MOVER` fixtures (the groups with no role assigned, pending §5 결정 2) continue to receive the **same single shared global dimmer/color/position value** they did in the 0-point Rain pilot, because SIDE/WASH/MOVER role recognition is deferred and REQ-001 does not touch the shared `fids` selection for non-effect, non-back fixtures.
7. Cross-checked against the standard's own definition of what a "layer" is meant to mean: `docs/proposals/song-structure-lighting-standard.md` §6.2 (re-verified this iteration): "기구는 세 층으로 역할을 나눈다 — 앰비언트 워시 / 텍스처(고보·소프트 빔) / 에너지(스트로브·빠른 빔)" — three *visually functioning* roles, not "three numerically distinct values including an off-state." `docs/proposals/song-lighting-design-standard.md` §4a I1 (re-verified this iteration): "키(프런트,얼굴)/백(실루엣·깊이)/이펙트(빔·에어리얼)" — again, three roles defined by what the audience sees them *doing*, not by whether their numeric state differs from zero.

**Conclusion**: a song can satisfy REQ-001/AC-001 as currently worded — reaching "3+ different-value layers" on a majority (or, per Concern 1, possibly even all) of its section cues — while the stage output for every non-accent cue remains visually identical to the 0-point Rain pilot: one shared value across KEY/FOH/SIDE/WASH/MOVER, one derived BACK value, and effect fixtures sitting dark (which they should be, but which contributes nothing the director would perceive as "more lighting design"). This is the precise failure mode the SPEC exists to fix (spec.md:38, the director's verbatim 0/5 complaint), reproduced inside the very AC meant to prove it is fixed.

- **Severity: critical — Class: blocking.** Required fix, in order of preference:
  1. Redefine the layer-diversity metric to count only buckets that correspond to an **actively lit, role-assigned** fixture group receiving a **non-degenerate** value this cue (i.e., exclude a role's bucket from the count when that role's value is the "held/tracked/off" state rather than an explicit this-cue command) — this directly targets the gaming mechanism.
  2. Alternatively, make REQ-001/AC-001 PASS **contingent on** §5 결정 2 resolving to option (a) or (c) (i.e., SIDE/WASH/MOVER actually gaining distinct values) rather than allowing the AC to pass on key/back/effect alone — this removes the thin 3-role trio as a sufficient basis and requires the genuinely new layer R1 was meant to deliver.
  3. At minimum, if the director accepts that key/back/effect-only is an acceptable **first increment** (R1 landing before §5 결정 2 resolves), the SPEC must say so explicitly as an open decision with the stage-visual caveat spelled out ("this increment does not yet change what the audience sees in non-accent cues beyond the existing BACK differential; genuine new layering awaits §5 결정 2"), so Implementation Kickoff Approval is informed rather than silently accepting a metric-passing-but-visually-unchanged M2/M4 landing.

## Updated Category Scores

| Dimension | iter1 | iter2 | Rationale for iter2 |
|-----------|-------|-------|----------------------|
| Clarity | 0.75 | 0.80 | D4/D9 fixed; D2's assignment properly separated into an open decision. Docked for D11/D12's unflagged weakening/gaming. |
| Completeness | 0.70 | 0.85 | D1 (t497) and D5 (AC count) fixed; §5 now carries 3 well-structured open decisions with cost tables. |
| Testability | 0.80 | 0.70 | D3 fixed (AC-006 now covers all 4 value lines) — but D11/D12 mean AC-001, the SPEC's flagship completion criterion, is satisfiable without the underlying claim ("3+ layers look different") being true in the way the card and the director's complaint require. A test that can PASS on a non-fix is a testability defect, not merely a clarity one. |
| Traceability | 0.90 | 0.90 | Unchanged — REQ→AC table still complete and orphan-free. |

Overall: (0.80+0.85+0.70+0.90)/4 = 0.8125 raw category average, but per the skeptical-evaluation stance (harmonic-mean-like penalty for a must-fix blocking the SPEC's own purpose) and the critical-severity D12, the aggregate is capped below the Tier M PASS threshold (0.80) regardless of category averaging — **Overall Score: 0.68**, reflecting that D12 is not a peripheral defect but a direct threat to whether this SPEC, once implemented exactly as written, would produce the outcome it was commissioned to produce.

## Must-Pass Results (unchanged from iteration 1 except as noted)

- [PASS] MP-1 REQ numbering — still 16, sequential, no gaps.
- [PASS] MP-2 GEARS compliance — D9 fix improved this; no new violations introduced.
- [PASS] MP-3 Frontmatter — unchanged, all 12 fields present.
- [N/A] MP-4 — unchanged.
- [PASS] MP-5 D7 — unchanged, all related_specs completed/non-blocking.
- [N/A] MP-6 — unchanged, no syscall.
- [PASS] MP-7 — unchanged, no literal unresolved marker outside the now-canonical §5 decisions (which are, correctly, declared-open rather than silently-unresolved).

No must-pass criterion fails. As in iteration 1, the FAIL verdict is driven by the Defects list (specifically D12's critical severity) under the M5/M6 framework, not by a must-pass firewall trip.

## Defects Found (new/updated this iteration)

D11. **ac-001-majority-qualifier-unauthorized-weakening** — `acceptance.md:9` — "과반 이상" (majority) silently weakens the card's per-cue "구간 큐 다른 값 층 ≥3" criterion and t499's own zero-violating-cue bar for the identical metric (§6.2), with no §5 open-decision entry or rationale. — Severity: **major** — Class: **blocking** — Required fix: tighten to "all section cues" with named mechanical exceptions, or formally open-decision it.

D12. **req-001-ac-001-layer-diversity-metric-gaming** — `spec.md:48,52`, `acceptance.md:7-9` — The "3+ distinct-value layers" completion criterion is satisfiable using `key`/`back`/`effect` alone, where the `effect` bucket's distinctness comes entirely from its tracked-off (0) state rather than any new actively-lit, audience-visible layer; `KEY`/`FOH`/`SIDE`/`WASH`/`MOVER` continue to share one global value exactly as in the director's 0-point Rain baseline. The AC can PASS while the stage output for non-accent cues remains visually unchanged from what scored 0/5. — Severity: **critical** — Class: **blocking** — Required fix: see the three ordered options above (gaming-proof metric redefinition / gate on §5 결정 2 / explicit increment caveat at Kickoff Approval).

## Recommendation

**FAIL — STOP (score regression).** Per the LEAN Workflow Additions, do not iterate unconditionally. Present the director/orchestrator with:

1. **Reduce scope** — split R1 into "R1a: key/back/effect trio (ships now, explicitly labeled as not yet changing non-accent-cue stage appearance)" and "R1b: SIDE/WASH/MOVER genuine layering (blocked on §5 결정 2)", with AC-001 scoped to R1a only and a separate AC gating R1b.
2. **Accept-with-debt** — proceed with the current REQ-001/AC-001 wording, but record D11/D12 as known debt in progress.md with an explicit director sign-off that the first increment will not visibly change non-accent cues, so the next director review is not another surprise 0/5.
3. **Explicit override** — director confirms the current wording is intentional (e.g., if R3's dark-effect-fixture fix is itself considered the primary deliverable of this pass and SIDE/WASH/MOVER genuinely is a "later" problem) — rare, but must be a conscious choice per the Retry Loop Contract, not silent continuation.

If iteration 3 is run, scope it to D11+D12 only (per the Retry Loop Contract's delta-audit discipline), plus a regression check that D1-D10's closures (confirmed above) remain intact.
