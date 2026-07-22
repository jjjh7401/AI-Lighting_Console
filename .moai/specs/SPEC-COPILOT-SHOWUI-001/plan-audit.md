# SPEC Review Report: SPEC-COPILOT-SHOWUI-001

Iteration: 1/3
Verdict: **FAIL** (near-threshold; no must-pass failure — remediable via bounded fold-in patch)
Overall Score: **0.81** (Tier L PASS threshold: 0.85; harmonic mean of 4 rubric dimensions)

Auditor stance: adversarial fresh-judgment. Reasoning context ignored per M1 Context Isolation. All evidence below is from the artifacts on disk + the actual codebase.

---

## Must-Pass Results

| MP | Verdict | Evidence |
|---|---|---|
| MP-1 REQ number consistency | **PASS** | `grep -o "REQ-SHOWUI-[0-9]*"` over spec.md yields exactly REQ-SHOWUI-001..020, each defined once, contiguous, consistent zero-padding. The two REQ-SHOWUI-021 hits (spec.md:24, spec.md:111) are explicit references to the DELETED draft fader requirement ("초안 REQ-SHOWUI-021 … 삭제"), not definitions — deleting from the tail leaves no gap. |
| MP-2 GEARS format compliance | **PASS** | All 20 REQs carry a valid pattern tag ([Ubiquitous]/[Event-driven]/[State-driven]/[Unwanted]) and structurally match the pattern (e.g. spec.md:56, :57, :70, :92). acceptance.md §B Given-When-Then scenarios are correctly labeled as test scenarios, not mislabeled GEARS. Compound multi-behavior REQs are a quality defect (F4, MAJOR) but not a pattern-compliance failure. |
| MP-3 YAML frontmatter validity | **PASS** | All 12 canonical fields present with correct types (spec.md:1-16): id, title (quoted), version `"0.1.0"` (quoted semver), status `draft` (enum), created/updated `2026-07-22` (ISO), author, priority `P1`, phase, module, lifecycle `spec-anchored`, tags (comma-separated). Optional `tier: L` valid. No rejected snake_case aliases. See F7/F8 (NOTE) for `id` regex literalism and the non-schema `related_specs` field. |
| MP-4 Language neutrality | **N/A** | Single-project UI/server SPEC (React/TS + FastAPI/Python), not multi-language tooling content. Auto-passes. |
| MP-5 D7 cross-SPEC reconciliation | **PASS** | Referenced IDs: SPEC-COPILOT-MVP-001, SPEC-COPILOT-DEPLOY-001. Both exist; both `status: in-progress` (verified via frontmatter grep). Neither retired/superseded/archived → no BLOCKING finding. The in-progress dependency is explicitly reconciled via `related_specs` (spec.md:98, plan.md §F row 5). |
| MP-6 D8 cross-platform discipline | **PASS** | `grep -c syscall` = 0 in spec.md and plan.md → auto-PASS. |
| MP-7 clarification gate | **PASS** | `grep -rn 'NEEDS CLARIFICATION' .moai/specs/SPEC-COPILOT-SHOWUI-001/` → 0 matches (exit 1). DP1 clarifications ①②③ are resolved and folded (spec.md:24, :43-45; plan.md §F). |

---

## Category Scores (rubric-anchored)

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.75 | 0.75 | One genuine safety-relevant textual contradiction (F1: All Off press count, design.md:57 vs :58/:65-66, REQ-012 vs REQ-019) + two minor ambiguities (F5 silent-drop mischaracterization, F6 stop/queue semantics). Weight of evidence (design.md §6, §5 arm bullet, design-direction §5.1, REQ-019) resolves F1 toward 2-step, so implementation divergence risk is bounded. |
| Completeness | 0.90 | 0.75–1.0 | All sections present (HISTORY spec.md:20-24; WHY/WHAT §A; REQUIREMENTS §B ×20; Environment §C; Out of Scope §D with 9 `### Out of Scope — <topic>` H3 sub-headings each with `-` bullets, spec.md:105-140; reference table §E). Gap: no requirement binds panel-payload validation (F3). |
| Testability | 0.85 | 0.75–1.0 | AC table (acceptance.md:54-70) gives concrete pytest/vitest/grep methods; machine vs LIVE items explicitly separated (acceptance.md:3). AC-011's arm→fire clause is non-binary for All Off until F1 is resolved. No weasel words detected. |
| Traceability | 0.75 | 0.75 | **REQ-010 is covered by no AC** — no row in the §C table cites it, and the only behavioral match (AC-014 LIVE, acceptance.md:70) cites no REQ (F2). All other 19 REQs ↔ AC mappings verified bidirectionally (matrix below). |

Aggregate (harmonic mean, per skeptical-evaluation stance): 4 / (1/0.75 + 1/0.90 + 1/0.85 + 1/0.75) = **0.81**.

---

## REQ ↔ AC Coverage Matrix (audit dimension 3)

| AC | Cited REQ(s) | | REQ | Covering AC(s) |
|---|---|---|---|---|
| AC-001 | 014 | | 001 | AC-002 |
| AC-002 | 001/002 | | 002 | AC-002 |
| AC-003 | 003 | | 003 | AC-003 |
| AC-004a | 004 | | 004 | AC-004a |
| AC-004b | 005 | | 005 | AC-004b |
| AC-005 | 006 | | 006 | AC-005 |
| AC-006 | 007 | | 007 | AC-006 |
| AC-007 | 008 | | 008 | AC-007 |
| AC-008 | 009 | | 009 | AC-008 |
| AC-009 | 011/012/013 | | 010 | **∅ — UNCOVERED (F2)** |
| AC-010 | 015/016 | | 011 | AC-009 |
| AC-011 | 017/018/019/020 | | 012 | AC-009 |
| AC-012 | (full regression — DoD) | | 013 | AC-009 |
| AC-013 LIVE | (composite E2E — DoD) | | 014 | AC-001 |
| AC-014 LIVE | **∅ — UNTRACED (F2)** | | 015/016 | AC-010 |
| | | | 017–020 | AC-011 |

Orphans: 1 uncovered REQ (010), 1 untraced AC (014 LIVE). All other mappings sound.

---

## Research Grounding Spot-Check (audit dimension 4) — 20+ citations, 0 mismatches

| Citation | Verified against codebase | Result |
|---|---|---|
| gate.py:260-264 `@MX:ANCHOR` single screening path | "exactly ONE screening path may exist; a second entry would be a gate bypass by construction"; `screen()` at :265 | **EXACT** |
| messages.py:23 `CLIENT_MESSAGE_TYPES` | `("chat", "approval_decision", "review_decision", "lock", "status_request")` at :23 | **EXACT** |
| protocol.ts:105-116 `SERVER_EVENT_TYPES` | Set of 10 event types at :105-116; `parseServerEvent` v/type null-drop at :119-131 | **EXACT** |
| tools.py:169-212 `_rig_object`/`_rig_section` | `_rig_object` :169-194 (real `no`, meaningful absence), `_rig_section` :197-212 (`truncated`/`total`) | **EXACT** |
| settings.py:383-404 atomic write | `save_user_settings` temp file + `os.replace` :383-405 | **EXACT** |
| useCopilotSocket.ts:102-108 `disconnected` | `onclose` → `dispatch({kind:"disconnected"})` at :102-108 | **EXACT** |
| classify.py:162-230 risk verdict | `classify_command` :162-230 incl. blacklist/unspecified-target/quoted-Cmd smuggling recursion | **EXACT** |
| session.py:354-389 `_last_created` | `_capture_last_created` :354-367, `_session_context_note` :369-389 | **EXACT** |
| session.py:202 `gate.state_port` seam | `state_port=gate.state_port` in `build_toolset` wiring (~:202) | **EXACT** |
| app.py:236-242 chat single-turn lock | `busy_event` on in-flight `current_task` :236-242 | **EXACT** |
| ApprovalCard.tsx:16-26 `createDecisionGuard` | pure one-shot guard at :16-26 | **EXACT** |
| styles.css:24 `.app` 860px cap | `.app { … max-width: 860px … }` :24-30 | **EXACT** |
| settings_api.py:104-112 REST/OSC boundary ANCHOR | "MUST … NEVER the OSC-send path" :104-112 | **EXACT** |
| protocol.ts:308-311 `clearPendingRequests` | :308-311 | **EXACT** |
| gate.py:549-573 clearance 1:1 audit | `_execute_cleared` clearance consumption + audit :549-573; no-clearance block :560-564 | **EXACT** |
| gate.py:318-324 lock-FIRST | REQ-MVP-035 re-check after approval :318-324 | **EXACT** |
| gate.py:598-607 audited state query | `_query_state` audited-even-on-failure :598-607 | **EXACT** |
| tools.py:36-44, 65-76, 81, 88, 100-108 | fixture slot≠FID comment; `DEFAULT_RIG_CONTEXT_PATHS`; `DEFAULT_RIG_DRILLDOWN`; `RIG_DRILLDOWN_QUERY_CAP=16`; distinct `path_not_resolved`/`console_unreachable` | **EXACT** |
| approval_bridge.py:19-27 payload-agnostic; serve.py:329-338 second channel | doc at :20; `review_channel = ApprovalChannel(...)` second instance :329-334 | **EXACT** |
| app.py:108-111, 219-222 status fan-out; ChatView.tsx:5-19 `statusClass` | `status_listeners` :90/:109, `push_status` :219-222; `statusClass` :5-19 | **EXACT** |
| rulebook 31_choreography_patterns.md "Playback" | `### Playback (validated)` :96; `Go+ Executor 191` :100, `Off Executor 191` :101/:125 | **EXACT** |

Research grounding is exceptional — the single strongest aspect of this SPEC.

---

## Findings Table

| # | Severity | Location | Finding | Evidence |
|---|---|---|---|---|
| F1 | **MAJOR** | design.md:57-58, :65-66; spec.md:76 (REQ-012), :92 (REQ-019); acceptance.md:67 (AC-011) | **All Off press-count contradiction.** design.md §5 stop bullet: "정지(stop): **항상 single-press, zero-step** … 타일별 `Off` + **전역 All Off**. 정지에 arm 단계·모달·메뉴 진입 금지" — explicitly places global All Off in the single-press-no-arm class. The very next bullet (:58) and §6 (:65) and REQ-019 mandate All Off = arm→fire **2-step**. REQ-012/REQ-019 also assert "정지는 항상 single-press" without defining whether All Off ∈ "정지". AC-011 ("파괴적 액션에 2회 상호작용·정지에 1회") is not binary-testable for All Off until the classes are disjoint. | Direct textual contradiction on a safety-relevant control |
| F2 | **MAJOR** | acceptance.md:54-70 (§C table), :70 (AC-014) | **REQ-010 has no covering AC; AC-014 is untraced.** No AC row cites REQ-010 (health≠online / executions_blocked blocking display). AC-014 (LIVE) tests exactly that behavior but cites no REQ, and no machine-verifiable (vitest) AC covers the blocked-state render — even though plan.md M4 ("차단/제안 상태 렌더") and M5 ("health/executions_blocked 엣지 렌더") plan its implementation. AC-008's vitest covers only the `live_lock` render (REQ-009). | Traceability gap both directions |
| F3 | **MAJOR** | spec.md:67 (REQ-006), :75 (REQ-011); plan.md M1/M3; acceptance.md §E "Secured" | **No requirement binds server-side validation of panel message payloads.** `panel_execute`/`panel_stop`/`panel_pin`/`panel_unpin` carry client-controlled targets, and the server constructs command strings from them (`Go+ Executor N`). No REQ requires: (a) target fields validated as integers (messages.py parse-time, per the `review_decision` field-validation precedent messages.py:58-70), (b) membership check against the catalog/pinned set before bundle construction. gate.screen() grammar+classify is real downstream defense, but the SPEC's own Secured gate (acceptance.md:88) claims only "실행 전량 gate.screen() 경유" and never addresses the new client-controlled injection/authz surface — the exact surface audit dimension 8 asks about. Pin content is metadata-only (name/target/type/color — spec.md:62), which structurally excludes arbitrary command content: good, but the target-validation gap remains. | Security-scope completeness gap |
| F4 | **MAJOR** | spec.md:62 (REQ-004), :63 (REQ-005), :68 (REQ-007), :81 (REQ-014), :85 (REQ-015), :92 (REQ-019) | **Compound multi-behavior REQs violate GEARS singularity.** Worst offenders: REQ-019 packs 4 behaviors (modal ban + arm→fire mandate + All Off bundle composition + broad-command ban) under one [Unwanted] tag, mixing positive and negative obligations; REQ-004 packs pin + unpin + edit-scope (two When triggers); REQ-005 mixes two subjects (핀 항목 shall / UI shall not); REQ-007 embeds two shall-nots under [Ubiquitous]; REQ-014 packs three obligations; REQ-015 packs two When triggers. Mitigation: every clause is individually testable and AC-mapped, so this is granularity debt, not untestability. | Audit dimension 2 requires singular REQs |
| F5 | MINOR | spec.md:81 (REQ-014) | **"silent-drop" mischaracterizes the server side.** REQ-014 says "미등록 타입의 silent-drop 계약(protocol.ts:128-129, messages.py:46-49)". Verified: protocol.ts:128-129 silently returns `null`; but messages.py:46-50 **raises `ProtocolError`** → explicit `error_event` reply (app.py:230-234). The contract to preserve differs per side. AC-001 gets it right ("미지 타입 거부" pytest / "null" vitest); the REQ text conflates. | Citation-content mismatch (the only one found) |
| F6 | MINOR | spec.md:75-76 (REQ-011/012); acceptance.md:50, :65 (AC-009, scenario 5) | **Stop-priority vs 1-in-flight semantics underspecified.** REQ-011 establishes busy-response, no-queue serialization for `panel_execute`; REQ-012 and AC-009/scenario-5 speak of "대기 중인 실행 큐"/"대기열을 우회" — a queue that per REQ-011 does not exist. Unstated: whether `panel_stop` is exempt from the 1-in-flight guard and may be screened/sent while a `panel_execute` bundle is mid-flight (two concurrent `gate.screen()` invocations), or whether it cancels/preempts. | Internal terminology inconsistency |
| F7 | NOTE | spec.md:2 | `id: SPEC-COPILOT-SHOWUI-001` does not literally match the schema SSOT regex `^SPEC-[A-Z][A-Z0-9]+-[0-9]{3}$` (single domain segment) — but multi-segment IDs are established project practice (MVP-001, DEPLOY-001 identical shape; the D7 extraction regex explicitly supports multi-segment). Recorded for schema-alignment awareness; no action required in this SPEC. | Schema literalism vs practice |
| F8 | NOTE | spec.md:15, :98; plan.md §F row 5 | `related_specs` is not a recognized field in `spec-frontmatter-schema.md` (Optional Fields lists `depends_on` etc.). It is additive/harmless to the 12-field lint. The **choice over `depends_on` is correctly justified**: the depends_on pre-flight requires strict `status: completed`, and MVP-001 is `in-progress` — declaring `depends_on` would hard-block `/moai run` and force `--ignore-deps` (the DEPLOY-001 D6 lesson the SPEC cites). Deliberate and sound. | Non-schema field, justified |
| F9 | NOTE | design-direction.md:86-87 vs design.md:75 (§7.4) | Seed artifact says "manual reorder only in an explicit edit mode" — predates DP1-③ (v1 = unpin-only, no reorder). design.md §7.4 correctly supersedes with "(reorder는 v1 범위 밖 — DP1-③)". Seed left unreconciled; harmless (design.md is the binding contract, design.md:3), but a one-line annotation in the seed would prevent misreading. | Superseded seed drift |

---

## Dimension Verdicts (parent audit dimensions 1–8)

1. **Frontmatter**: PASS (12/12 fields, valid enums; F7/F8 NOTEs). `related_specs` vs `depends_on` choice explicitly justified — spec.md:98.
2. **GEARS**: PASS on pattern validity (all 20 tagged and structurally conformant); **MAJOR debt on singularity** (F4).
3. **REQ↔AC coverage**: **FAIL on completeness** — REQ-010 uncovered, AC-014 untraced (F2). 19/20 REQs cleanly mapped.
4. **Research grounding**: PASS — 20+ citations spot-checked, **zero mismatches** (one characterization error F5, not a citation error).
5. **Safety-invariant completeness**: PASS with one gap. Single screening path (REQ-006/007 + AC-006 machine-verified via `test_architecture.py` + grep), live_lock demotion + lock-FIRST (REQ-009), fail-closed disconnect (REQ-015/016 + AC-010), approval flow all-or-nothing (REQ-008 + AC-007), no-OSC-import boundary (REQ-007, plan §C.2), catalog reads audited via `gate.state_port` (REQ-002). No gate-bypass path found: execution is WS-only via `gate.screen()`, REST execution endpoints are Out of Scope (spec.md:118-120), stop priority is explicitly "스케줄링 속성이지 게이트 우회가 아니다" (REQ-012). Residual gap = F3 (payload validation upstream of the gate).
6. **Scope integrity**: PASS. DP1-① fader excluded (§D:109-112, draft REQ-021 deleted); DP1-② All Off bounded enumeration with stated limitation (§A:48-50, REQ-019, design §6, plan R7, AC-013 ⑦ live-verifies the limitation); DP1-③ unpin-only (REQ-004, §D:130-132). No scope creep; F9 is superseded seed drift only.
7. **Milestone feasibility**: PASS. M1(protocol contract)→M2(store/catalog)→M3(gated execution)→M4(UI)→M5(fail-closed)→M6(green+live) dependency order sound; decision-reversibility-first rationale stated (plan §A); file-touch lists match implementing REQs; M4 partial parallelism correctly gated on M1 contract freeze.
8. **Security scope**: PARTIAL — pins are metadata-only (good structural exclusion of arbitrary command content), credentials excluded (REQ-005 + AC-004b), but the client-controlled target surface lacks a validation requirement (F3, MAJOR).

---

## Chain-of-Verification Pass

Second-look actions taken: (a) re-read all 20 REQs individually — found F5 and F6 on the second pass; (b) REQ sequencing verified end-to-end via grep count, not spot-check; (c) traceability verified for every REQ in both directions (matrix above) — F2 found this way; (d) Out of Scope checked for specificity — 9 H3 `### Out of Scope — <topic>` sub-headings each with concrete bullets (spec.md:105-140), not just presence; (e) cross-requirement contradiction sweep — found F1 (the most consequential finding) by cross-reading REQ-012 against REQ-019 against design.md §5's two adjacent bullets; (f) re-verified the remaining §E reference-table citations (approval_bridge, serve.py, status fan-out, statusClass, rig paths) — all exact. No further defects found on the second pass.

---

## Required Remediations (fix route for manager-spec — re-audit will be scoped to this delta)

1. **(F1)** Define the classes disjointly and fix the design.md §5 stop bullet: 정지 = **타일별 Off** (single-press, no arm); **All Off = 파괴적 발화 액션** governed by arm→fire (2-step). Remove "전역 All Off" from the single-press bullet (design.md:57); add one clarifying clause to REQ-012 and REQ-019 ("정지(타일별 Off)는 single-press; All Off는 파괴적 액션으로 arm→fire"). Update AC-011 wording to name the classes.
2. **(F2)** Add a machine AC for REQ-010 (vitest: `health ≠ online` / `executions_blocked` → panel-level blocked banner + tile disable render; pytest: blocked execution result surfaced, not swallowed), and annotate AC-014 with "REQ-010" in its 검증 대상 cell.
3. **(F3)** Extend REQ-006 (or REQ-014's parse contract) with: `panel_execute`/`panel_stop` target fields MUST be validated at `parse_client_message` time (integer `no`, per the review_decision field-validation precedent) and MUST reference an item present in the current catalog or pin store — unknown/malformed targets receive an explicit error event, never a constructed bundle. Add rejection cases to AC-005. Do NOT number a new requirement REQ-SHOWUI-021 (that number is burned as the deleted fader draft — reuse would corrupt the HISTORY record).
4. **(F4)** Split or sub-clause the compound REQs — at minimum REQ-019 (→ 019a modal-ban/arm→fire, 019b All Off bounded-enumeration composition) and REQ-004 (pin / unpin). Alternatively, record singularity debt explicitly in the HISTORY with rationale if v0.2.0 chooses to keep them merged.
5. **(F5)** Reword REQ-014: "TS측은 미지 타입 silent-drop(null, protocol.ts:128-129), 서버측은 ProtocolError 명시 거부(messages.py:46-50) — 양측 계약 각각 회귀 없이 보존".
6. **(F6)** Delete the "대기 중인 실행 큐" phrasing (there is no queue per REQ-011); state explicitly whether `panel_stop` is exempt from the 1-in-flight guard and may proceed while an execute is in flight (recommended: yes, exempt — with a note that `gate.screen()` per-session clearance semantics tolerate the concurrent stop bundle, gate.py:269-272).

Estimated remediation surface: text-only edits to spec.md (REQ-004/006/012/014/019), design.md (§5), acceptance.md (§C table +1 AC, AC-005/011/014 cells). No architectural rework. A clean fold-in should clear the 0.85 Tier L threshold at iteration 2.

---

*plan-auditor · iteration 1/3 · 2026-07-22 · evidence: 20+ codebase citations verified, 0 mismatches*

---
---

# SPEC Review Report: SPEC-COPILOT-SHOWUI-001 — Iteration 2

Iteration: 2/3 (re-audit of the v0.2.0 remediation delta + full must-pass re-verification)
Verdict: **PASS**
Overall Score: **0.93** (Tier L threshold 0.85; harmonic mean; trajectory 0.81 → 0.93, no regression — no STOP signal)

Reasoning context ignored per M1 Context Isolation. All six remediation claims were re-verified against the artifacts on disk; none was accepted on assertion.

---

## Regression Check (iteration-1 defects)

| # | Iteration-1 defect | Status | Evidence |
|---|---|---|---|
| F1 | All Off press-count contradiction | **RESOLVED** | Classes now disjoint everywhere: REQ-012 (spec.md:79) defines `panel_stop` = 타일별 Off = 정지 클래스 and states "전역 All Off는 이 정지 클래스에 속하지 않는다"; REQ-024 (spec.md:96) owns arm→fire for the destructive fire-class and states the classes are 서로소; design.md:57 stop bullet now reads "정지 클래스는 **타일별 `Off`만**을 뜻한다 … **전역 All Off는 정지 클래스가 아니다**" — "전역 All Off" removed from the single-press class; design.md:20 §2 row consistent; §9 traceability rows updated (019 modal-ban / 024 arm→fire / 012 stop-class / 025-026 All Off). AC-011 (acceptance.md:67) rewritten binary: destructive fire-class = exactly 2 interactions with **0 commands issued after press 1 (assert)**; stop class = exactly 1 press. Residual-contradiction sweep (grep "전역 All Off" + full re-read of §2/§3/§4/§5/§6/§7): no residual contradiction in binding artifacts. (Seed design-direction.md retains its pre-DP1 tension — F9 NOTE, unchanged, optional.) |
| F2 | REQ-010 uncovered / AC-014 untraced | **RESOLVED** | New **AC-SHOWUI-015** (acceptance.md:71): vitest blocked-banner + tile-disable render assert AND pytest blocked-result-surfaced assert — machine coverage for REQ-010. AC-014 (acceptance.md:70) now cites "REQ-010" in its 검증 대상 cell. DoD updated to "AC-SHOWUI-001..012 + AC-SHOWUI-015" (acceptance.md:9). Full matrix rebuilt below — zero orphans both directions. |
| F3 | Panel payload validation unbound | **RESOLVED** | New **REQ-SHOWUI-022** (spec.md:70): parse-time integer validation of target (messages.py:58-70 precedent) + pre-bundle catalog/pin-store membership check; malformed (non-integer/negative/missing) and unknown targets → explicit error event, with "그 어떤 경우에도 커맨드 번들이 구성되거나 `gate.screen()`이 호출되지 않는다". Two-stage separation (stateless parse-time type check vs handler-time membership) is technically sound. AC-005 (acceptance.md:61) adds the rejection cases incl. `gate.screen()` 미호출 assert; edge case #10 added (acceptance.md:84); Secured gate claim extended (acceptance.md:90). The security surface is bound. |
| F4 | Compound REQs (singularity) | **RESOLVED (split + explicit debt)** | REQ-004→004(pin, spec.md:63)+023(unpin, spec.md:64); REQ-019→019(modal-ban only, spec.md:95)+024(arm→fire, :96)+025(bounded composition, :97)+026(broad-target ban, :98) — each singular, correctly pattern-tagged. Residual compounds (005/007/014/015) recorded as **singularity debt** in the HISTORY 0.2.0 row (spec.md:25) with the each-clause-AC-mapped rationale — the exact alternative offered in iteration-1 remediation #4. |
| F5 | "silent-drop" server-side mischaracterization | **RESOLVED (in spec.md)** | REQ-014 (spec.md:84) now states per-side contracts: TS silent-drop (`parseServerEvent` → `null`, protocol.ts:128-129) vs server `ProtocolError` explicit reject + error event (messages.py:46-50, app.py:230-234) — both verified against the code in iteration 1. Residual undifferentiated phrasing survives in plan.md §C.3:62 and §E R2:78 → new NOTE R2 (binding surfaces REQ-014/AC-001 are correct). |
| F6 | Queue phrasing / stop-vs-busy-guard ambiguity | **RESOLVED** | grep "대기열\|대기 중인 실행 큐" over all artifacts: zero matches in normative content (only the HISTORY row describing the deletion and this report). REQ-012 (spec.md:79): stop **면제** from the 1-in-flight busy guard, immediate processing, concurrent `gate.screen()` explicitly permitted, gate never bypassed. Scenario 5 (acceptance.md:50) and AC-009 (acceptance.md:65 — "busy 가드 면제 … 동시 `gate.screen()` 허용 assert") consistent with REQ-012. New MINOR R3 on the supporting citation introduced by this fix (below). |
| F7-F9 | NOTEs (id regex literalism / `related_specs` / seed drift) | **STAND** | No action was required; unchanged and non-blocking. |

No iteration-1 required-fix defect remains unresolved. No stagnant defect (nothing survived unchanged from iteration 1's required list).

---

## Must-Pass Re-verification (v0.2.0)

| MP | Verdict | Evidence |
|---|---|---|
| MP-1 REQ numbers | **PASS** | First-token definition extraction: 25 unique definitions (001-020, 022-026), zero duplicate definitions. The 021 gap is an **explicitly documented burned number** — HISTORY 0.2.0 row (spec.md:25): "REQ-SHOWUI-021은 소각(burned) … **영구 결번**이며 신규 번호는 022부터 이어진다"; all 3 remaining 021 mentions (spec.md:24, :25, :70, :117) are reference-only tombstones. The burn was mandated by iteration-1 remediation #3 (do NOT reuse 021); a documented, auditor-mandated tombstone gap is not a numbering defect. |
| MP-2 GEARS | **PASS** | All 25 REQs pattern-tagged and structurally conformant, including the 5 new ones (022/023 Event-driven, 024/025 Ubiquitous, 026 Unwanted — the "shall not … ~하지 않는다" rendering matches the document's established v0.1.0 house style, e.g. REQ-003/005/013/016). |
| MP-3 Frontmatter | **PASS** | 12 fields unchanged; `version: "0.2.0"` bumped with matching HISTORY row; `updated: 2026-07-22` consistent. |
| MP-4 | **N/A** | Unchanged (single-project SPEC). |
| MP-5 D7 | **PASS** | Re-grep: SPEC-COPILOT-MVP-001 and SPEC-COPILOT-DEPLOY-001 both `status: in-progress` — no retired/superseded/archived reference; `related_specs` reconciliation unchanged. |
| MP-6 D8 | **PASS** | `grep -c syscall` = 0 in spec.md and plan.md. |
| MP-7 clarification gate | **PASS** | grep over the SPEC directory: the only "NEEDS CLARIFICATION" strings are inside this audit report's own quoted verification command — zero markers in plan.md/research.md or any artifact. |

---

## Rebuilt Coverage Matrix (25 REQs ↔ AC-001..015) — zero orphans

REQ→AC: 001→AC-002 · 002→AC-002 · 003→AC-003 · 004→AC-004a · 005→AC-004b · 006→AC-005 · 007→AC-006 · 008→AC-007 · 009→AC-008 · **010→AC-014(LIVE)+AC-015** · 011→AC-009 · 012→AC-009 · 013→AC-009 · 014→AC-001 · 015→AC-010 · 016→AC-010 · 017→AC-011 · 018→AC-011 · 019→AC-011 · 020→AC-011 · **022→AC-005** · **023→AC-004b** · **024→AC-011** · **025→AC-011** (+AC-013 ⑦ LIVE) · **026→AC-011**.
AC→REQ: every AC row cites valid, defined REQs (AC-004b now "REQ-005/023"; AC-005 now "REQ-006/022"; AC-011 now "REQ-017/018/019/020/024/025/026"; AC-014 now "REQ-010"; AC-015 "REQ-010"); AC-012/013 remain composite DoD items. **Zero orphans in both directions.**

---

## Category Scores (iteration 2)

| Dimension | Score | Evidence |
|-----------|-------|----------|
| Clarity | 0.90 | F1/F6 resolved; residual: one mis-attributed supporting citation in REQ-012 (R3) + plan.md phrasing echo (R2) — no requirement is ambiguous in its normative content. |
| Completeness | 0.95 | F3 bound; all sections intact; residual: plan.md version-header lag (R1). |
| Testability | 0.90 | AC-011 now binary for both classes; AC-015 added; residual: AC-011 method cell lacks the explicit positive-composition assert for REQ-025 (R4 — target cell cites it; AC-013 ⑦ live-verifies). |
| Traceability | 1.00 | 25/25 REQs covered, 15 AC entries all traced, zero orphans both directions (matrix above). |

Harmonic mean = 4 / (1/0.90 + 1/0.95 + 1/0.90 + 1/1.00) = **0.93** ≥ 0.85 → PASS.

---

## Remaining Findings (non-blocking debt)

| # | Severity | Location | Finding |
|---|---|---|---|
| R1 | MINOR | plan.md:3 | plan.md status header still reads "v0.1.0" while spec.md frontmatter/HISTORY, acceptance.md:3, and design.md:3 all record v0.2.0. plan.md WAS content-updated (M3 anchors → REQ-025/026 at :32; §F DP1-② → 025/026, DP1-③ → 004/023/005 at :90-91) but the version line was not bumped. One-line fix; fold into the next plan.md touch or the run-phase M1 commit. |
| R2 | NOTE | plan.md:62 (§C.3), :78 (§E R2) | Undifferentiated "한쪽 누락 시 silent-drop" phrasing survives in plan.md context sections (mirroring research.md Risk 11). Half-accurate: a TS-side registration omission silent-drops (true); a server-side omission raises `ProtocolError` → error event (loud, not silent). The binding surfaces (REQ-014, AC-001) are correct, so this cannot mislead implementation — align wording opportunistically. |
| R3 | MINOR | spec.md:79 (REQ-012 parenthetical) | **Mis-attributed supporting citation introduced by the F6 fix.** REQ-012 justifies concurrent stop/execute screening with "게이트의 clearance 소비는 번들 단위이므로 동시 stop 번들과 양립한다 — gate.py:269-272". The cited code shows the opposite mechanism: `screen()` **resets THIS session's clearance Counter** on each new bundle (`self._clearances[session_key] = Counter()`, M6c-1 Finding 2 comment) — i.e., whichever bundle screens second invalidates the first bundle's unconsumed clearances within the same session key. Consequences are fail-safe (over-block, never bypass): stop-screens-during-execute preempts the execute's remaining sends (arguably the desired semantics), but the reverse order could block a stop mid-bundle if an execute screens while the stop's clearance is unconsumed. The normative requirement (exemption + gating) stands and AC-009's concurrent assert will mechanically surface this interaction in pytest at M3. Required correction (before M3 implementation): reword the parenthetical to acknowledge the same-session re-screen invalidation and require the implementation to account for it (e.g., bundle-atomic screen→consume, or distinct gate session scoping for panel bundles — mechanism is run-phase choice). |
| R4 | NOTE | acceptance.md:67 (AC-011) | AC-011's 검증 대상 cell cites REQ-025 (bounded composition) but the method cell's All Off check states only the REQ-026 negative assert (`Thru`/`*`/`Everything` absence). Add the positive assert — bundle == exactly one `Off Executor N` per tracked running executor (and edge: 0 running → empty bundle/no-op per edge case #6). AC-013 ⑦ already live-verifies the bounded behavior. |
| F7/F8/F9 | NOTE | (unchanged) | Stand as recorded in iteration 1 — id multi-segment regex literalism; `related_specs` non-schema field (justified); design-direction.md seed drift (superseded by design.md). |

---

## Chain-of-Verification Pass (iteration 2)

Second-look actions: (a) re-read all 25 REQ definitions individually — R3 found this way (the F6 fix's citation checked against the gate.py:269-272 text captured in iteration 1); (b) definition uniqueness verified mechanically via first-token extraction (25 unique; the raw grep's apparent duplicates were cross-references inside definition lines); (c) residual-contradiction sweep for F1 across design.md §2/§3/§5/§6/§7 and spec.md §A — none in binding artifacts; (d) full coverage matrix rebuilt from scratch for the enlarged REQ set rather than patching the iteration-1 matrix — R4 found this way; (e) version/HISTORY discipline checked across all four artifacts — R1 found this way; (f) burned-021 mentions enumerated (reference-only, all tombstone contexts). No further defects found.

---

## Recommendation

**PASS — proceed to Implementation Kickoff Approval.** All six iteration-1 remediations are verified resolved with file:line evidence; must-pass 7/7 clean; score 0.93 ≥ 0.85 (Tier L). Non-blocking debt to fix forward, ideally before/at run-phase M1-M3:

1. (R1) Bump plan.md header to v0.2.0 — one line.
2. (R3) Correct the REQ-012 parenthetical per the finding above **before M3** (gate-adjacent; the current wording would hand manager-develop a false compatibility assumption; AC-009's concurrent assert is the backstop either way).
3. (R2, R4) Opportunistic wording alignments — no gate impact.

*plan-auditor · iteration 2/3 · 2026-07-22 · verdict PASS 0.93 (0.81 → 0.93) · 6/6 remediations verified resolved · 2 MINOR + 4 NOTE residual debt*
