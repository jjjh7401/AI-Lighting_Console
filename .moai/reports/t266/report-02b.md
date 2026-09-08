### t132 — ALIVE (split) / UNMEASURED (partial)
claim: CSV 재-임포트(preset-dim.csv/preset-col.csv)가 앱이 이미 쓴 20개 슬롯(dim 10+col 10)과 충돌하는가.
ran: grep -n "_color_pool_and_capable_fids\|_store_position_preset_sequence\|_dimmer_preset_material" server/web/session.py ; sed -n '5921,6000p' server/web/session.py ; grep -n "preset-dim\|preset-col" server/web/session.py ; grep -rn "preset-dim\|preset-col" server/lxseq/*.py | grep -v preset_parser.py
saw: session.py:5921 `_store_position_preset_sequence` 주석 — "Store Preset은 기존 슬롯을 경고 없이 덮어쓰므로 시작 번호는 운영자가 정해야 합니다"(occupancy check 없음, 프롬프트로만 경고). session.py 안에서 preset-dim/preset-col 은 오직 `_SHEET_ROW_COUNTERS`(3293-3294행, 행수 카운터)에만 등장 — 콘솔 쓰기 호출부 0건. server/lxseq/*.py 도 preset_parser.py 밖에서 이 두 kind 를 참조하지 않음.
so: CSV 경로(preset_parser.py)는 값의 storability 를 분류만 하고 콘솔에 쏘는 코드 경로가 이 저장소 안에서 발견되지 않았다 — 앱의 실제 풀 슬롯 쓰기(`_store_position_preset_sequence`)와는 별개 시스템이라 "재-임포트가 슬롯을 덮어쓴다"는 카드 전제가 이 두 경로 간에는 적용되지 않는다(ALIVE: 앱 쓰기 경로 자체는 무방비로 덮어씀 — 이건 사실). 다만 CSV 분류 결과가 다른 어딘가(테스트 하니스·CLI)에서 콘솔에 쏘일 가능성은 전수 검색을 못 했다 — UNMEASURED: `grep -rn "preset_parser\|classify_storability" --include=*.py .` (worktree 전체) 필요.

### t139 — ALIVE
claim: preset_mapper.py's `_ACCEPTED_ATTRIBUTES` prefix-match over-accepts unmeasured BM attributes (IrisPulseOpen, ZoomModeBeam, Zoomed, DimmerCurve).
ran: grep -n "_attribute_tokens\|_ACCEPTED_ATTRIBUTES\|CONFIRMED_ATTRIBUTES\|PROBE_GATED_ATTRIBUTES" server/lxseq/preset_mapper.py server/lxseq/preset_parser.py server/looks/schema.py; sed -n '245,262p' server/lxseq/preset_parser.py; sed -n '39,50p' server/looks/schema.py
saw: preset_mapper.py — zero matches (mechanism not there). preset_parser.py:250-256 — `_attribute_tokens`: `for token in re.findall(_WORD, value): for known in known_names: if token.lower().startswith(known.lower()) and known not in found: found.append(known)`. schema.py:39-44 CONFIRMED_ATTRIBUTES = ("Dimmer","ColorRGB_R","ColorRGB_G","ColorRGB_B"); schema.py:50 PROBE_GATED_ATTRIBUTES = ("Zoom","Iris").
so: the card's file citation (preset_mapper.py) is wrong — the real home is preset_parser.py's `_attribute_tokens`/`classify_storability` — but the underlying defect is real: "Iris" prefix-matches IrisPulseOpen, "Zoom" prefix-matches Zoomed/ZoomModeBeam, and "Dimmer" prefix-matches DimmerCurve, so all four named attributes are confirmed to over-accept via the prefix rule; verdict is ALIVE at a corrected location, not DEAD.

### t136 — ALIVE
claim: SPEC-COPILOT-COLORPRESET-001's lifecycle ledger is still open (no acceptance.md, status draft) unlike comparable closed SPECs.
ran: ls .moai/specs/SPEC-COPILOT-COLORPRESET-001/ .moai/specs/SPEC-AXISCORE-001/ .moai/specs/SPEC-CUETIME-001/ .moai/specs/SPEC-LXSEQ-002/ .moai/specs/SPEC-PRESETIDEM-001/; sed -n '1,6p' .moai/specs/SPEC-COPILOT-COLORPRESET-001/spec.md
saw: COLORPRESET-001 dir contains only plan.md, progress.md, spec.md (no acceptance.md); the other four SPECs each list acceptance.md; spec.md line 5: `status: draft`.
so: the comparison set confirms COLORPRESET-001 is the odd one out with no acceptance.md and a draft status — the ledger closure claim is current and verified, not stale.

### t138 — DECISION
claim: Gobo is deliberately excluded from in-scope pool families; card asks whether this exclusion should be revisited.
ran: sed -n '55,72p' server/lxseq/preset_parser.py; grep -n "_OUT_OF_SCOPE\|IN_SCOPE_POOL_FAMILIES" server/lxseq/preset_parser.py server/looks/schema.py
saw: preset_parser.py:122 `_OUT_OF_SCOPE = ("Gobo","Position","Control","Shapers","Video")`; schema.py:55-57 `IN_SCOPE_POOL_FAMILIES: tuple[str,...] = ("Dimmer","Color","Beam","Focus")  # Position/All/Gobo/Control/Shapers/Video are out of scope (spec.md §D)`; preset_parser.py:60-64 comment confirms schema.py's out-of-scope names exist only as docstring prose there, no tuple (documented cross-file gap).
so: this is a real, current, consistently-applied architectural decision (not a defect) — verdict is DECISION: whether to bring Gobo in scope, with the current exclusion confirmed intentional and documented on both sides.

### t133 — DECISION (partial DEAD)
claim: card asks which Kelvin→RGB color-temperature conversion model the codebase should adopt for warm/cool white presets.
ran: grep -n "3200K\|5600K" server/lxseq/preset_parser.py; sed -n '2525,2531p' server/web/session.py
saw: preset_parser.py's `~3200K`/`~5600K` literals are tied only to `HOLD_NO_RGB_VALUE = "no_rgb_value"` (a CSV hold/refusal marker), unrelated to RGB conversion. session.py:2528-2529: `("Warm White", (100,75,40))`, `("Cool White", (85,95,100))` — plain RGB tuples with no Kelvin cross-reference or comment linking them.
so: the narrow claim "an existing Kelvin→RGB mapping is defective" is DEAD — no such mapping exists in code to be defective; the broader claim "no conversion model has been chosen yet" survives as DECISION.

### t143 — ALIVE (citation confirmed accurate; underlying ledger issue unresolved)
claim: commit ef0103a's diffstat claims (3 files touched, test file +548/0) are accurate, and a verdict.md already exists for t136's SPEC.
ran: git show --numstat --format="" ef0103a; ls -la .moai/reports/t136/verdict.md; wc -c .moai/reports/t136/verdict.md
saw: numstat — `23 0 .moai/specs/SPEC-COPILOT-COLORPRESET-001/progress.md`, `548 0 server/tests/test_web_session.py`, `607 82 server/web/session.py` (exactly 3 files, test file matches 548/0 verbatim). verdict.md exists at 11285 bytes (not read further — size-checked only, per team-lead's read-before-size rule; content not needed to settle this card's decidable claim).
so: the commit's own file/line-count citation is verified accurate against git, but per team-lead's explicit warning, an accurate commit citation is not proof the card's underlying goal (SPEC ledger closure, per t136) was met — that remains ALIVE as settled under t136 above; a pre-existing verdict.md's presence is noted but its content is UNMEASURED (would require reading it, out of scope for this decidable claim).

### TALLY
DEAD: (none outright dead — t133 partially dead, see below)
ALIVE: t132, t136, t139, t143
CONSOLE-BLOCKED: (none)
DECISION: t138, t133(broader framing)
SUPERSEDED-CANDIDATE: (none)
UNMEASURED: t132(partial — CSV classification reach beyond preset_parser.py)
NOTE: t133 is split — DEAD for the narrow "existing Kelvin→RGB mapping is defective" claim, DECISION for the broader "no conversion model chosen" framing.
