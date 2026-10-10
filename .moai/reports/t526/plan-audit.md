# SPEC Review Report: SPEC-LDBEAT-001 (카드 t526 개정, v0.2.0)
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.85 (집계 점수는 통과선 0.80을 넘지만, MP-2 위반으로 M5 필수통과 방화벽에 걸려 FAIL — 집계 점수로 상쇄되지 않음)

Reasoning context ignored per M1 Context Isolation — spec.md/plan.md/acceptance.md/progress.md 및 명시된 입력 리포트만으로 판단함.

## Must-Pass Results

- [PASS] MP-1 REQ 번호 일관성: `grep -oE "REQ-LDBEAT-[0-9]{3}"` 결과 REQ-LDBEAT-001~015, 15개 연속, 간격·중복 0건.
- **[FAIL] MP-2 EARS/GEARS 형식 준수 (requirement layer, spec.md §3 REQ-XXX 대상)**: 여러 REQ 칸이 "요구사항" 칸 안에서 하나의 굵은 GEARS 트리거(When/While/Where/The…shall)로 시작한 뒤, **같은 칸 안에 전혀 다른 내용의 새 요구사항을 GEARS 마커 없이 평서문으로 이어붙였다**. 대표 사례:
  - `spec.md:94` REQ-LDBEAT-005 — "**The** 박자 격자의 초기 표시 범위 **shall** 0~25마디..." 뒤에 "재생은 ±10초 스킵 버튼 + 음원 동기(...)를 지원한다."가 붙어 있다. 이 문장은 "초기 표시 범위"와 무관한 **별개의 재생 기능 요구**(±10초 스킵, 음원 동기)이고 GEARS 트리거가 전혀 없다 — EARS/GEARS 다섯 패턴 중 어느 것에도 해당하지 않는 평서문이다.
  - `spec.md:122` REQ-LDBEAT-012 — 본문 shall 절 뒤에 "**미리보기**(Goto Cue/Off Sequence)는 이 절차와 별도로 세션 시작 때 1회 승인받으면 그 세션 동안 반복 가능하다(결정⑤)"가 GEARS 마커 없이 추가돼 있다. 이는 승인 절차에 대한 **별개의 행위 규정**이다.
  - `spec.md:93` REQ-LDBEAT-004 — (a)~(e) 목록 뒤에 "같은 장비를 두 그룹 트랙이 동시에 잡는 배치는 **shall not** 허용한다"가 붙는다 — shall not 마커는 있으나, 하나의 REQ-ID가 "새 블록 추가"와 "중복 트랙 금지"라는 서로 다른 두 행위를 함께 규정한다(아래 Traceability 결함과 연결됨).
  - `spec.md:130` REQ-LDBEAT-013, `spec.md:139` REQ-LDBEAT-015도 같은 패턴(복수의 shall/shall not + GEARS 마커 없는 평서문 "신설한다", "설계해야 한다", "정확한 번호대는 M2/M3가 ... 확정하되")을 보인다.
  - M3 §Scope 는 이 검사가 **requirement layer(REQ-XXX, spec.md)에만** 적용되고 AC-XXX(verification layer)에는 적용되지 않는다고 명시한다 — 위 판정은 전부 REQ-XXX 칸을 대상으로 한 것이며, acceptance.md의 Given/When/Then AC는 이 판정에서 제외했다(올바른 레이어).
  - M5 MP-2 정의 "mixed informal/formal within a single requirement = FAIL"에 정확히 해당한다. 이것이 1~2개의 孤立 사례가 아니라 15개 REQ 중 5개 이상(004·005·011·012·013·015)에서 반복되는 체계적 패턴이므로 다운그레이드하지 않고 FAIL로 판정한다.
- [PASS] MP-3 YAML 프런트매터 유효성: `spec.md:1-16`에 12개 필수 필드(`id,title,version,status,created,updated,author,priority,phase,module,lifecycle,tags`) 전부 존재, 타입 정상, snake_case 별칭(`created_at`/`updated_at`/`labels`/`spec_id`) 없음. `tier: M`·`related_specs: […]`는 선택 필드(스키마에 미등재된 `related_specs`도 금지 별칭이 아니므로 무해).
- [N/A] MP-4 §22 언어 중립성: 이 SPEC은 단일 조명 콘솔 프로젝트(grandMA3) 전용이며 다국어 도구 체계를 다루지 않는다 — N/A 자동 통과.
- [PASS] MP-5 D7 교차-SPEC 정합성: `grep -oE "SPEC-([A-Z][A-Z0-9]+-)+[0-9]+"` 결과 `SPEC-LDBARMAP-001`·`SPEC-LDARRANGE-001`(존재하지 않음, `ls .moai/specs/`로 확인 — 그러나 spec.md §4가 "아직 존재하지 않는 SPEC"이라고 **스스로 명시**해 D7-5의 SHOULD 수준 고지를 이미 충족), `SPEC-LDDESIGN-001`(status: completed)·`SPEC-LDRENDER-001`(status: completed)·`SPEC-LDRHYTHM-001`(status: in-progress) — retired/superseded/archived 상태 0건, BLOCKING 없음.
- [N/A] MP-6 D8 크로스플랫폼 규율: `grep -c "syscall" spec.md plan.md acceptance.md` 결과 0건 — N/A 자동 통과.
- [PASS] MP-7 [NEEDS CLARIFICATION] 게이트: `grep -rn '\[NEEDS CLARIFICATION'` 결과 plan.md 0건, research.md 부재(Tier M이라 정상, research.md는 Tier L 전용 산출물) — 미해결 마커 없음.

## Category Scores (0.0-1.0, rubric-anchored)
| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 (일부 REQ에 소수 모호성) | `spec.md:107` REQ-LDBEAT-009가 "Where 특정 그룹에만 적용되는 편집이 필요하면"을 썼다 — GEARS의 `Where`는 capability-gate/feature flag/static config용이지 "필요하면"(이벤트성 조건)에는 `When`이 더 맞다. 또한 REQ 칸마다 섞인 복수 주장(위 MP-2 사례)이 "이 REQ의 진짜 요구사항이 어디까지인가"를 읽는 이에게 판단하게 만든다. |
| Completeness | 1.0 | 1.0 (전 섹션·12필드·Out of Scope 7개 충족) | HISTORY(`spec.md:20-27`)·§0(`29`)·§1 배경(`51`)·§2(`64`)·§3 REQUIREMENTS(`75`)·acceptance.md(별도 파일, Tier M 규격)·§4 Out of Scope 7개 H3 서브헤딩(`spec.md:143,149,160,166,172,178,184`) 전부 `-` 불릿 보유, 프런트매터 12필드 전부 존재. |
| Testability | 1.0 | 1.0 (바이너리 테스트 가능, 위즐워드 없음) | acceptance.md §A 16개 AC 전부 구체적 커맨드/그렙/sha256/카운트 기준을 명시. `적절/합리적/알맞/타당` 류 위즐워드는 §A에 0건(§C 인간 판단 섹션에만 1건, §C는 명시적으로 기계 검사 대상에서 제외됨 — 정상). |
| Traceability | 0.75 | 0.75 (일부 REQ가 간접/부분 매핑) | §A.1 추적표는 REQ-001~015 전부에 ≥1 AC를 매핑했으나(표 자체는 완전), REQ-LDBEAT-004의 "겹치는 그룹 동시 사용 금지" 부속 요구(`spec.md:93` 마지막 문장)와 REQ-LDBEAT-005의 "±10초 재생+음원동기" 부속 요구(`spec.md:94`)는 매핑된 AC-003(`acceptance.md:13`)이 검증하지 않는다(`grep -n "겹치는\|동시에 잡는" acceptance.md` 0건, AC-003은 트랙 렌더·행 개수·2D 무대 좌표만 검사). REQ-LDBEAT-012의 "미리보기 세션 1회 승인 반복 가능" 부속 요구도 §D Definition-of-Done 체크리스트 문장(`acceptance.md:71`)에만 있고 §A의 정식 AC 항목으로 승격돼 있지 않다. |

## Defects Found (structured defect-list)

D1. GEARS-MIX-001 — `spec.md:94` (REQ-LDBEAT-005) — "초기 표시 범위" shall 절 뒤에 GEARS 마커 없는 별개 요구("재생은 ±10초 스킵 버튼 + 음원 동기... 지원한다")가 평서문으로 끼워져 있다 — Severity: critical (MP-2 must-pass 위반) — Class: blocking — Required fix: REQ-LDBEAT-005를 두 개의 REQ로 분리하거나, 재생 ±10초/음원 동기 요구를 별도 REQ-ID(예: REQ-LDBEAT-005a 또는 새 번호, Tier M 상한 16개 이내 확인)로 떼어내 `**When**` 또는 `**The**...**shall**` 형식으로 재작성한다.

D2. GEARS-MIX-002 — `spec.md:122` (REQ-LDBEAT-012) — "미리보기는 세션 시작 1회 승인으로 반복 가능하다" 문장이 GEARS 마커 없이 본문 shall 절에 이어붙어 있다 — Severity: major — Class: blocking — Required fix: 이 문장을 `**Where** 미리보기(Goto Cue/Off Sequence)가 사용되면, 그 승인은 **shall** 세션 시작 시 1회로 그 세션 동안 반복 가능하다` 형태의 독립 GEARS 절로 재작성(같은 REQ-ID 유지 가능하되 칸 안에서 명시적 GEARS 구조로 전환)한다.

D3. GEARS-MIX-003 — `spec.md:93` (REQ-LDBEAT-004), `spec.md:130` (REQ-LDBEAT-013), `spec.md:139` (REQ-LDBEAT-015) — 각 REQ 칸이 3개 이상의 서로 다른 shall/shall not/평서문 주장을 하나의 REQ-ID 아래 묶었다 — Severity: major — Class: blocking — Required fix: 각 REQ를 "하나의 REQ = 하나의 검증 가능한 행위" 원칙으로 재분할하거나, 적어도 모든 부속 주장에 굵은 GEARS 마커를 붙여 "요구사항 칸에 평서문이 없다"는 상태로 교정한다.

D4. TRACE-GAP-001 — `spec.md:93` REQ-LDBEAT-004의 "같은 장비를 두 그룹 트랙이 동시에 잡는 배치는 shall not 허용한다" — 이를 검증하는 전용 AC가 없다(`grep -n "겹치는\|동시에 잡는\|overlap" acceptance.md` 0건) — Severity: major — Class: blocking — Required fix: 전용 AC(예: AC-LDBEAT-017)를 신설해 "MOVER-ALL과 MOVER-U를 동시에 트랙으로 선택 → 거절"을 Given/When/Then으로 검증하고, §A.1 추적표에 REQ-LDBEAT-004 행을 갱신한다.

D5. TRACE-GAP-002 — `spec.md:94` REQ-LDBEAT-005의 "±10초 재생 + 음원 동기" 부속 요구 — AC-LDBEAT-003(`acceptance.md:13`)은 트랙·행·2D 무대 좌표만 검사하고 재생 스킵/음원 동기 동작은 검사하지 않는다 — Severity: major — Class: blocking — Required fix: D1에서 분리된 새 REQ에 전용 AC(재생 위치 ±10초 이동, 음원 재생 위치와 마디 환산 일치 검증)를 신설한다.

D6. TRACE-GAP-003 — `acceptance.md:71` (§D Definition of Done) — REQ-LDBEAT-012의 "미리보기 세션 1회 승인 반복 가능" 요구가 §A의 정식 AC가 아니라 §D 체크리스트 문장에만 존재한다 — Severity: minor — Class: blocking (traceability 기준 위반) — Required fix: §A에 전용 AC(예: AC-LDBEAT-018)를 신설해 "세션 시작 1회 승인 → 이후 Goto/Off 반복 호출이 재승인 없이 통과"를 기계 검증 기준으로 명문화한다.

D7. UNVERIFIED-UI-001 — `spec.md:93` REQ-LDBEAT-004(b) "화면 우상단에 모드 전환 버튼(타임라인 ↔ 상세) 하나를 둔다" — 카드 입력 보고서(`reports/ldbeat-runbook-ui-proposal-20261008.html`/`.md`, `reports/ldbeat-runbook-mockup-20261008.html`/`.md`)를 전수 검색한 결과 "타임라인 ↔ 상세" 류의 전역 모드-전환 버튼은 등장하지 않는다. 실제 설계는 3단 상시-동시-표시 레이아웃(곡 전체 지도 → 장비그룹 줄 타임라인 → 상세 창)이며, 큐(막대)를 누르면 타임라인 바로 오른쪽에 편집 칸이 열리는 방식이다(`reports/ldbeat-runbook-ui-proposal-20261008.html:159`). 유일하게 발견된 "전환" 버튼은 큐-사이 전환(트리거/딜레이/MIB) 편집을 여닫는 버튼(`reports/ldbeat-runbook-ui-proposal-20261008.html:92-93`, "「전환」 버튼: 편집 칸 오른쪽 위(✕ 옆)")으로, "타임라인 ↔ 상세" 전역 모드 전환과는 무관한 기능이다. HTML 내 `VIEW="board"`/`.vtabs`/`.vt` 토글 코드(`reports/ldbeat-runbook-ui-proposal-20261008.html:101,561,574,576`)도 CSS만 선언돼 있고 실제 마크업에 인스턴스화된 곳이 없어 사용되지 않는 죽은 코드다. 로드맵의 "전환 버튼"(`reports/ldbeat-feasibility-roadmap-20261010.md:54`)도 큐-사이 전환 편집 버튼을 가리키는 것으로 읽힌다 — Severity: major — Class: blocking (카드 요구사항 8 "입력에 없는 사실을 지어내지 않는다" 위반) — Required fix: REQ-LDBEAT-004(b)를 삭제하거나, 실제 입력 보고서에 있는 "큐-사이 전환 편집 버튼"(이음매 ◆ 를 누르면 열리는 전환 편집)으로 정확히 재기술한다. 만약 "타임라인 ↔ 상세" 토글이 run-phase에서 실제로 필요하다고 판단되면, 그 근거를 입력 보고서가 아니라 이 plan-phase 자신의 설계 결정으로 명시하고 "실측"이 아닌 "제안"으로 표시해야 한다.

(블로킹이 아닌 참고 사항 — Class: optional)

D8. OPTIONAL-001 — `spec.md:107` REQ-LDBEAT-009 — `Where` 트리거가 GEARS의 capability-gate/feature-flag 의미보다 이벤트성 조건("필요하면")에 가깝게 쓰였다 — Severity: minor — Class: optional — Required fix: `**When** 특정 그룹에만 적용되는 편집이 제출되면`으로 바꾸거나, 현재 표현을 레거시 EARS Optional 패턴으로 간주하고 그대로 유지(6개월 하위호환 창 안에 있으므로 당장 블로킹은 아님).

D9. OPTIONAL-002 — `spec.md:15` `related_specs: […]` 필드 — 프런트매터 스키마의 12개 필수 필드도 아니고 문서화된 선택 필드 목록(`issue_number/depends_on/lint.skip/bc_id/amendment_of/tier`)에도 없는 커스텀 필드다. 금지된 snake_case 별칭은 아니므로 MP-3 위반은 아니지만, SSOT에 미등재된 필드다 — Severity: minor — Class: optional — Required fix: 필요하다면 스키마 선택 필드 목록에 `related_specs`를 공식 추가하거나, 기존 `tags`/HISTORY 서술로 대체한다.

## Regression Check (Iteration 2+ only)
N/A — 이번 호출은 이 플랜-오딧터 세션 기준 iteration 1이다. `.moai/reports/plan-audit/`에 이전 iteration 리포트 파일이 현재 작업트리에 남아 있지 않음(`ls .moai/reports/plan-audit/` → `.gitkeep`뿐, 과거 리뷰 파일은 로컬 아티팩트로 정리됨). spec.md HISTORY(`spec.md:25-26`)가 기록한 과거 "iteration 1 FAIL(0.71)→대응" 및 "오케스트레이터 검토 D1~D3 대응"은 **카드 t526 개정 이전**의 별도 라운드이며, 이번 심사는 카드 t526이 추가한 변경분(확정된 감독 결정 1~5, REQ-013 재교정, 트랙 모양 교정, 2D 무대, REQ-015 신설)에 대한 독립 첫 심사다.

## Recommendation

FAIL — 다음을 수정한 뒤 재심사를 요청할 것(우선순위 순):

1. (필수, MP-2) D1·D2·D3 — REQ-LDBEAT-004/005/011/012/013/015의 "요구사항" 칸에서 GEARS 마커 없는 평서문 부속 요구를 제거하거나 독립 GEARS 절로 재작성한다. 특히 REQ-005의 "±10초 재생+음원동기"는 완전히 다른 기능이므로 분리를 권고한다.
2. (필수, Traceability) D4·D5·D6 — 분리/명시된 부속 요구마다 전용 AC를 신설하고 §A.1 추적표를 갱신한다. REQ/AC 수가 Tier M 상한(각 16개)을 넘으면 Tier 재검토 또는 범위 축소를 먼저 감독과 확인한다(현재 AC 16/16으로 이미 경계치이므로, 신설 전에 기존 AC 통합 여지를 먼저 검토할 것을 권고 — optional 수준의 조언).
3. (필수, 입력 정합성) D7 — "모드 전환 버튼(타임라인 ↔ 상세)"을 입력 보고서에 실제로 있는 "큐-사이 전환 편집 버튼"으로 교정하거나, 삭제 또는 plan-phase 자체 제안으로 재분류한다.
4. (선택) D8·D9 — 다음 개정 때 함께 정리해도 무방하다.

수정 후 이 리포트의 D1~D7을 "RESOLVED" 여부로 재확인하는 범위-한정 재심사(iteration 2)를 수행할 것을 권고한다.

---

## Iteration 2 — 범위 한정 재심사 (2026-10-10, 같은 카드)

Reasoning context ignored per M1 Context Isolation. 아래 판정은 전부 (a) 현재 `spec.md`/`plan.md`/`acceptance.md`/`progress.md` 본문, (b) `reports/ldbeat-runbook-ui-proposal-20261008.html`의 실제 줄 번호, (c) `grep`/`sed`로 재확인한 소스 트리 사실에만 근거한다.

### D1~D9 FIXED/NOT FIXED 판정

| ID | 판정 | 증거 |
|----|------|------|
| D1 (GEARS-MIX-001, REQ-005 재생±10초/음원동기 혼입) | **FIXED** | `spec.md:94`(현재 REQ-LDBEAT-005 행) — "(a)와 (b)는 서로 무관한 두 요구이고 각각 독립 GEARS 절이다"로 명시 재분리. (a) `**The** ... **shall** 0~25마디...`, (b) `**The** 재생 컨트롤 **shall** ±10초 스킵 버튼과 음원 동기...를 지원한다.` 둘 다 굵은 트리거 보유. 근거 칸 인용 재확인: `reports/ldbeat-runbook-ui-proposal-20261008.html:164`(`⏪ 10초` 버튼)·`:166`(`10초 ⏩` 버튼)·`:168`(음원 파일 입력)·`:620`(`음원 0초 = 앞박, 1마디 = 1.50초`) — 전부 실측 확인(`sed -n`). |
| D2 (GEARS-MIX-002, REQ-012 미리보기 반복 혼입) | **FIXED** | `spec.md:123` REQ-LDBEAT-012 — "(a)·(b) 각각 독립 GEARS 절"로 재구조화. (a) `**The** ... **shall** ... 따른다 ... **shall not**이다`(쓰기 승인), (b) `**Where** 미리보기(...)가 쓰기와 별도로 사용되면, 그 승인은 **shall** 세션 시작 시 1회로 충분하며 ... **shall not**한다`(미리보기 반복). 둘 다 굵은 트리거. |
| D3 (GEARS-MIX-003, REQ-004/013/015 다중 평서문 혼입) | **FIXED** | `spec.md:94`(REQ-004 (a)~(h), 8개 절 전부 굵은 트리거), `spec.md:131`(REQ-013 (a)~(c)), `spec.md:140`(REQ-015 (a)~(e)) — 전부 재확인, 평서문(굵은 트리거 없는 새 요구) 0건. |
| D4 (TRACE-GAP-001, REQ-004 겹침 금지 미검증) | **FIXED** | `acceptance.md:15` AC-LDBEAT-003에 "**(b, 겹침 금지 — 신설, plan-audit D4)**" Given/When/Then 추가 — "그 추가는 거절되고 겹치는 그룹 중 하나는 트랙에서 제외된다(REQ-LDBEAT-004(h))" + 검증 수단 "겹치는 그룹 조합 추가 요청 → 트랙 목록에 두 그룹 동시 존재 0건 assert". |
| D5 (TRACE-GAP-002, REQ-005 재생/음원동기 미검증) | **FIXED** | `acceptance.md:15` 같은 AC-003에 "**(c, 재생+음원동기 — 신설, plan-audit D5)**" 추가 — "±10초 이동 ... 음원 재생 위치가 ... 환산 초와 일치" + 검증 수단 "`bBack10`/`bFwd10` 클릭 전후 ... 델타 == ±10 ... 허용 오차 ≤0.1초". |
| D6 (TRACE-GAP-003, REQ-012 미리보기 반복 미검증) | **FIXED** | `acceptance.md:14` AC-LDBEAT-002에 "**(b, 미리보기 승인 반복 — 신설, plan-audit D6)**" 추가 — "2회차 이후의 미리보기 호출은 재승인 프롬프트 없이 통과한다" + 검증 수단 "승인 프롬프트 발생 횟수 == 1 assert". §A.1 매핑은 불변(REQ-012→AC-015 그대로)이지만 REQ-012(b)는 이제 AC-002(b)가 검증 — 두 AC에 걸쳐 REQ-012가 커버되는 모양은 §A.1 표에 "AC-015" 단독 표기로 남아 약간의 비고 누락이 있으나(§A.1은 AC-015만 적음), AC-002(b)가 실질적으로 그 부속 요구를 검증하므로 traceability 결함 자체는 해소됐다고 판정한다(bookkeeping 표기 정밀도는 optional급 지적). |
| D7 (UNVERIFIED-UI-001, "모드 전환 버튼" 날조) | **FIXED — 가장 정밀하게 교정됨** | 오케스트레이터의 지적대로 토글 자체는 실재했다(`id="tgTr"`) — 다만 "타임라인 ↔ 상세" 전역 전환이 아니라 **큐 편집 칸 헤더 우측의 "큐 편집 ↔ 들어오는-전환 편집" 토글**이었다. `spec.md:94` REQ-LDBEAT-004(d)가 이를 정확히 재기술: "그 큐 편집 칸 shall 칸 헤더 우측(✕ 옆)에 '전환' 토글 버튼 하나를 포함하며, When 그 버튼이 눌리면, 패널은 shall 큐 편집 뷰와 들어오는-전환 편집 뷰(...) 사이를 전환한다. While 선택된 큐가 그 곡의 첫 큐인 동안, 그 버튼은 shall '곡 첫 큐 — 들어오는 전환 없음' 제목과 함께 비활성 상태를 유지한다." 직접 재검증(`sed -n '495,503p;504p;519p'`): `:495`(`id="tgTr"`, `disabled title="곡 첫 큐 — 들어오는 전환 없음"`, 큐 편집 칸 헤더), `:497-501`(mainView — 밝기/위치/색/움직임), `:504`(`trViewHTML` — 들어오는-전환 뷰, 페이드/트리거/딜레이/트래킹), `:519`(갱신 핸들러) — 전부 바이트 단위로 spec.md의 인용과 일치. (a)(b)(e)(h)의 재검증 인용(`:155,376,196-200,238`)도 전부 실측 일치(아래 "추가 재확인" 참조). |
| D8 (optional, REQ-009 Where→When) | **FIXED** | `spec.md:108` — `[카드 t526 plan-audit D8: Where→When 교정 ...] **When** 특정 그룹에만 적용되는 편집(...)이 제출되면, ...`. |
| D9 (optional, `related_specs` 비표준 필드) | **NOT FIXED — 의도적 보류, 수용 가능** | `acceptance.md:7` "D9 — 선택 사항, 이번 라운드에서는 다루지 않음(related_specs 필드는 manager-spec 자체 관행으로 유지)." optional 등급 지적이었고 명시적으로 보류를 선언했으므로 M6 기준 수용 가능 — 미해결이 FAIL 사유가 되지 않는다. |

### D7 보조 재검증 (오케스트레이터 지적 반영)

`reports/ldbeat-runbook-ui-proposal-20261008.html` 재측정:
- `:495` → `const head=\`<h5>...<button class="tg ${trView?"on":""}" id="tgTr" ${t?"":"disabled title=\"곡 첫 큐 — 들어오는 전환 없음\""}>전환</button>...` — **확인**, 큐 편집 칸 헤더 우측(✕ 옆), 첫 큐 비활성화 title 포함.
- `:504` → `const trViewHTML=t?\`<div ...>전환 — Cue ${k-1} ... → Cue ${k}</div> ... 페이드 ... 트리거 ... 딜레이 ... MIB ... 트래킹 ...\`:""` — **확인**, 들어오는-전환 편집 뷰.
- `:519` → `if(trView){const upd=()=>{t.fade=... t.trigBeat=... t.delay=... t.trk=...};...}` — **확인**, 트리거 박/딜레이/트래킹 갱신 핸들러.
- 추가 재확인: `:155`(3단 상시-동시-표시 레이아웃 + 한 화면 높이 서술) **확인**, `:376`(`id="fAll"` "모두 접기/펴기") **확인**, `:196-200`(`#cmdIn`/`#bRule`/`#bAi` 명령창) **확인**, `:238`("정정" 절의 겹치는 그룹 동시 사용 금지 서술) **확인**, `:497-501`(mainView 밝기/위치/색/움직임 필드) **확인**.

D7은 수정 전 "입력에 없는 사실을 지어냈다"는 FAIL 판정 자체가 틀렸다는 뜻이 아니라, **그 판정이 가리킨 원문 서술("타임라인 ↔ 상세" 전역 모드 전환)은 실제로 입력 보고서에 없었고, 지금의 재기술("전환" 토글, 큐 편집 칸 내부)이 입력 보고서가 실제로 담고 있는 것과 정확히 일치한다**는 것으로 재확인됐다. 교정은 정확했다.

### MP-2 전 REQ(001~015) 전수 재검사

이전 iteration은 D1~D9에 오른 REQ(004/005/009/011/012/013/015)만 검사했다. 이번 iteration은 오케스트레이터 지시대로 **15개 REQ 전부**를 재검사했다.

- REQ-001, 003, 006, 007, 008, 009, 010, 014: 굵은 GEARS 트리거 1개(또는 REQ-008처럼 같은 주체에 대한 shall+shall not 쌍) 보유, 부속 서술은 근거/배경 설명이며 새 평서문 요구를 숨기지 않음 — **PASS**.
- REQ-004, 005, 011, 012, 013, 015: 위 D1~D3 교정으로 **PASS**.
- **REQ-002 — `spec.md:85` — 미발견·미수정 상태로 남은 동일 패턴.** 핵심 절 `**When** M1 프로브가 실행되면, 그 절차는 **shall** ... 따르고, 코드 diff 0줄·기존 번호 덮어쓰기 0건이다.` 뒤에 굵은 트리거 없는 두 개의 추가 평서문이 이어진다: (i) `각 프로브는 위 9항목 중 하나를 가르는 최소 단위로 설계한다(...)` — 프로브 설계 단위에 대한 별개의 규범. (ii) `**M1은 응답기 긴 값 나눠 읽기 확장도 포함한다**: ... M1은 이 응답기에 offset 기반 나눠 읽기(...)를 추가해 그룹 소속 전체가 읽히는지 확인한다 — 이 확장은 코드 diff 0줄 원칙의 예외다(...).` — 이것은 "M1 프로브가 t516/t519/t520 패턴을 따른다"와는 **무관한 별개의 요구**(응답기 lua 코드 확장)이며, REQ-005에서 교정된 "±10초 재생" 혼입과 **구조가 동일**하다. 이 REQ는 iteration 1의 D1~D9 목록에 없었고(이번 재검사에서 처음 식별), 이번 rewrite도 건드리지 않았다 — **FAIL, MP-2 잔존 위반**.

### Traceability 잔존 결함 (REQ-002의 부속 요구와 연동)

REQ-LDBEAT-002의 "응답기 긴 값 나눠 읽기 확장" 부속 요구를 검증하는 전용 `§A` AC가 없다. `grep -n "offset\|나눠 읽기\|응답기" acceptance.md` 결과는 `§B 엣지 케이스`(`acceptance.md:58`, "응답기 미확장 상태에서 그룹 전체 색칠 시도" — 2D 무대 색칠 동작만 검사, 응답기 자체의 offset 읽기 성공/실패는 검사 대상이 아님)와 `§D Definition of Done`(`acceptance.md:71`, "결과가 기록됨"이라는 bookkeeping 문장)뿐이다 — 이는 D4~D6에서 고친 것과 **정확히 같은 모양의 결함**(전용 Given/When/Then 없이 체크리스트 문장에만 존재)이다.

### 집계 재평가

| 구분 | Iteration 1 | Iteration 2 |
|------|-------------|--------------|
| MP-1 | PASS | PASS (불변, 15/16 재확인) |
| MP-2 | **FAIL** | **FAIL — 원인 교체** (D1~D3 전부 FIXED, 그러나 REQ-002에서 동일 패턴 잔존 재발견) |
| MP-3 | PASS | PASS (불변) |
| MP-4 | N/A | N/A |
| MP-5 | PASS | PASS (불변 — LDBARMAP/LDARRANGE 부재는 자체 고지, LDDESIGN/LDRENDER completed·LDRHYTHM in-progress) |
| MP-6 | N/A | N/A |
| MP-7 | PASS | PASS (불변) |
| Clarity | 0.75 | 0.75 (REQ-004/005/009/011/012/013/015의 모호성은 해소됐으나 REQ-002 1건이 같은 유형으로 남음 — "한두 개 요구사항의 소소한 모호성" 밴드 그대로) |
| Completeness | 1.0 | 1.0 (불변) |
| Testability | 1.0 | 1.0 (불변 — 신설 AC-002(b)/AC-003(b)(c) 전부 바이너리 검증 가능, 위즐워드 0건) |
| Traceability | 0.75 | 0.75 (D4~D6 해소분은 상쇄, REQ-002 부속 요구의 동형 결함이 대체) |
| Overall Score | 0.85 | 0.875 (평균치 — MP-2 방화벽으로 무효) |

### 새로 발견된 결함 (이번 rewrite가 만든 결함이 아니라, 전수 재검사로 처음 식별된 잔존 결함)

D10. GEARS-MIX-004 (NEW, iteration 1에서 누락됨) — `spec.md:85`(REQ-LDBEAT-002) — M1 리허설-절차 요구 뒤에 굵은 트리거 없는 "프로브 최소 단위 설계" 규범과 "응답기 긴 값 나눠 읽기 확장" 요구가 평서문으로 이어붙어 있다 — D1(REQ-005)과 동일한 결함 유형 — Severity: critical (MP-2 must-pass) — Class: blocking — Required fix: REQ-LDBEAT-002를 (a)(b)(c) 라벨 하위 절로 재구조화한다. 예: (a) `**When** M1 프로브가 실행되면, 그 절차는 **shall** t516/t519/t520 패턴을 따른다`(기존 핵심 절), (b) `**The** 각 프로브는 **shall** 로드맵 §4의 9항목 중 정확히 하나를 가르는 최소 단위로 설계된다`, (c) `**The** M1은 **shall** 응답기 `console/lua/copilot_responder.lua`의 긴 값 나눠 읽기 확장(offset 기반)을 포함한다 — 이는 코드 diff 0줄 원칙의 예외다`. REQ 총량을 15개로 유지하려면 새 REQ-ID를 만들지 않고 이 라벨링 패턴(D1~D3와 동일 패턴)을 그대로 적용하면 된다.

D11. TRACE-GAP-004 (NEW, D10과 동반) — `acceptance.md:58,71` — REQ-LDBEAT-002(c)(위 D10에서 분리 제안한 응답기 확장 요구)를 검증하는 전용 `§A` AC가 없다 — `§B`/`§D` 체크리스트 문장뿐 — Severity: major — Class: blocking — Required fix: D10의 (c)를 검증하는 Given/When/Then을 AC-LDBEAT-009(이미 M1 프로브 결과를 다루는 AC)의 하위 시나리오로 확장하거나(AC 상한 16/16 유지), AC-009에 "(c, 응답기 확장 — 신설)" 절을 추가해 "offset 기반 나눠 읽기 후 그룹 소속 전체(18개 그룹)가 읽히는지" 검증을 명문화한다.

## Iteration 2 Verdict

**Verdict: FAIL**
**Overall Score: 0.875** (MP-2 필수통과 방화벽 위반으로 집계 점수는 무효 — M5 규정상 다른 점수로 상쇄되지 않음)

D1~D9 중 8개(D1~D8)는 FIXED로 확인됐고 D9(optional)는 의도적으로 보류됐다 — 이것 자체는 매우 정확하고 꼼꼼한 교정이었다(D7 재검증은 특히 바이트 단위로 정확했다). 그러나 이번 iteration이 지시받은 "15개 REQ 전수 재검사"에서 REQ-LDBEAT-002가 iteration 1이 놓친 동일 유형의 MP-2 위반(D1과 같은 패턴)을 갖고 있음이 새로 드러났다 — 이로써 MP-2는 원인이 교체된 채로 FAIL 상태를 유지한다. 반드시 고쳐야 할 항목은 D10(REQ-002 GEARS 재구조화)과 D11(그 응답기 확장 부속 요구의 AC 신설/확장) 두 가지뿐이다 — 둘 다 D1~D6에서 이미 검증된 동일한 수선 패턴을 REQ-002 한 곳에 반복 적용하면 되므로, 수정 범위는 작다.

## Recommendation (Iteration 2)

1. (필수, MP-2) D10 — `spec.md:85` REQ-LDBEAT-002를 (a)(b)(c) 라벨 독립 GEARS 절로 재구조화한다.
2. (필수, Traceability) D11 — 응답기 확장 요구에 전용 AC 시나리오(기존 AC-009 확장 권장, 새 AC-ID 불필요)를 추가한다.
3. 두 수정 모두 REQ/AC 총량(15/16)을 바꾸지 않고, 이번 iteration에서 이미 입증된 재구조화 패턴을 그대로 복제하면 된다 — iteration 3 재심사는 D10/D11 두 항목의 FIXED/NOT FIXED 확인으로 범위를 좁힐 것을 권고한다.

---

## Iteration 3 — 범위 한정 재심사 (2026-10-10, 같은 카드, 최종)

Reasoning context ignored per M1 Context Isolation. 판정은 현재 `spec.md`/`acceptance.md` 본문과 `.moai/reports/t525/verdict.md`(실측 원본)만으로 근거했다.

### D10/D11 FIXED/NOT FIXED 판정

| ID | 판정 | 증거 |
|----|------|------|
| D10 (GEARS-MIX-004, REQ-LDBEAT-002) | **FIXED** | `spec.md:86` — "**재구조화(카드 t526 plan-audit iteration 2 D10)**: (a)~(c) 각각 독립 GEARS 절"로 재작성됨. (a) `**When** M1 프로브가 실행되면, 그 절차는 **shall** ...`, (b) `**The** 각 프로브는 **shall** 로드맵 §4의 9항목 중 정확히 하나를 가르는 최소 단위로 설계된다`, (c) `**The** M1은 **shall** 응답기 ... 긴 값 나눠 읽기 확장(offset 기반)을 포함한다 ...` — 3개 절 전부 굵은 트리거 보유, 평서문 0건. 근거 칸도 (a)(b)(c)로 분리돼 각 절의 출처를 따로 인용한다. |
| D11 (TRACE-GAP-004, REQ-LDBEAT-002(c) 응답기 확장 미검증) | **FIXED** | `acceptance.md:23` AC-LDBEAT-009에 "**(b, 응답기 확장 — 신설, plan-audit iteration 2 D11)**" Given/When/Then 추가 — Given: "그룹의 SELECTIONDATA 값이 ... max_prop_value = 240을 넘는 상태"; When: "앱이 그 그룹의 소속을 확장된 offset 기반 나눠 읽기 경로로 읽는다"; Then: "그 그룹의 멤버 전체가 반환되고, 결과에 truncated 플래그가 없다"; 검증 수단: "반환된 멤버 수 == 그 그룹의 실제 멤버 수 assert + ... 절단 플래그 부재 확인 (REQ-LDBEAT-002(c))". `acceptance.md:32` §A.1에도 "plan-audit iteration 2 D11: REQ-LDBEAT-002의 (c) 하위 절(...)은 ... AC-LDBEAT-009(b)(신설 하위 시나리오)가 구체적으로 검증한다"는 비고가 추가됨 — 요청받은 "§A.1 note"도 확인됨. |

### MP-2 전 REQ(001~015) 재검사 (3회차)

전 REQ를 다시 전수 재확인했다 — REQ-002(현재 `spec.md:86`, (a)(b)(c) 독립 절), REQ-004(`:95`, (a)~(h)), REQ-005(`:96`, (a)(b)), REQ-009(`:109`, When), REQ-011(`:123`, (a)~(c)), REQ-012(`:124`, (a)(b)), REQ-013(`:132`, (a)~(c)), REQ-015(`:141`, (a)~(e)) — 전부 유지되고 있으며 모든 절이 굵은 GEARS 트리거를 갖는다. REQ-001·003·006·007·008·010·014는 불변이고 기존 판정(PASS)이 유지된다. **MP-2: 15개 REQ 전부 PASS — 잔존 위반 0건.**

### REQ/AC 총량 재확인

`grep -oE "REQ-LDBEAT-[0-9]{3}" spec.md | sort -u | wc -l` → **15**. `grep -oE "AC-LDBEAT-[0-9]{3}" acceptance.md | sort -u | wc -l` → **16**. 새 ID 추가/삭제 없음 — 요청받은 15 REQ / 16 AC 확인 완료.

### 새로 발견된 결함 (이번 D10/D11 수정이 만든 결함)

**D12. FACT-ERROR-001 (NEW) — `acceptance.md:23` AC-LDBEAT-009(b) Then 절 — "네 그룹 실측 기준 각 8대"는 그 측정의 출처(`.moai/reports/t525/verdict.md`)와 직접 불일치하는 틀린 수치다.**

`.moai/reports/t525/verdict.md:41-53`의 실측 표(r1 요약)를 직접 재확인했다:

| 그룹 | 대수 (t525 실측) |
|---|---|
| BLIND | **6**대 (601–606) |
| SIDE-L | **6**대 (301–306) |
| BACK | **12**대 (201–212) |
| MOVER-ALL | 표에 직접 명시되지 않음 — `MOVER-U` 8대(501–508)와 `MOVER-D` 8대(521–528)가 별도 그룹으로 측정됐을 뿐, "MOVER-ALL"이라는 합산 그룹의 대수는 이 검증서에 단독으로 나오지 않는다(부모-자식 그룹이라면 16대에 가까울 것이나, 이 역시 실측되지 않았다) |

AC-009(b)의 Given 절은 이 네 그룹(MOVER-ALL·BACK·SIDE-L·BLIND)을 "네 그룹 모두 163바이트에서 절단"이라고 정확히 인용했으나(이는 t525:89와 일치, 참), Then 절이 거기서 더 나아가 "그 그룹의 멤버 전체(네 그룹 실측 기준 **각 8대**)"라고 쓴 것은 **지어낸 숫자**다 — BLIND·SIDE-L은 6대, BACK은 12대로 8대가 아니며, MOVER-ALL의 대수는 애초에 측정된 바 없다. 이는 이 심사가 iteration 1의 D7에서 지적한 것과 같은 유형의 결함(입력/실측에 없는 "사실"을 측정값으로 서술)이 이번 iteration 2의 D11 수정 자체 안에서 새로 발생한 것이다.

다행히 같은 셀의 **검증 수단** 칸("확장된 읽기 경로 호출 → 반환된 멤버 수 == **그 그룹의 실제 멤버 수** assert")은 고정 숫자를 쓰지 않고 일반화된 올바른 형태를 유지하고 있다 — 결함은 Then 절의 **서술 문구**에 한정되며, 실행 가능한 검증 로직 자체는 깨지지 않았다. 그래도 Then 절이 "실측 기준"이라고 주장하며 틀린 숫자를 적어 두면, 이 AC를 읽고 구현하는 사람이 "각 그룹 8대가 되는지"를 리터럴하게 확인하려다 BLIND/SIDE-L(6대)·BACK(12대)에서 거짓 FAIL을 내게 된다.

- Severity: major
- Class: **blocking** (M6 기준 — 이 문서 자신이 "실측"이라고 명시한 수치가 그 실측 출처와 불일치 → 내부 정합성 결함 + 이 SPEC 자신이 명시한 기준과의 불일치)
- Required fix: `acceptance.md:23` Then 절의 "네 그룹 실측 기준 각 8대"를 삭제하고, 검증 수단 칸과 같은 일반형으로 통일한다. 예: "그 그룹의 멤버 전체(그 그룹의 실제 멤버 수 — 그룹마다 다르다: 예시로 측정된 BLIND·SIDE-L 6대, BACK 12대)가 반환되고". 고정 숫자를 Then 절에 다시 넣지 않는다.

### Must-Pass 결과 (최종)

| 기준 | 판정 |
|------|------|
| MP-1 | PASS |
| MP-2 | **PASS** (15/15 REQ, 잔존 위반 0건 — D10으로 최종 해소) |
| MP-3 | PASS |
| MP-4 | N/A |
| MP-5 | PASS |
| MP-6 | N/A |
| MP-7 | PASS |

7개 필수통과 기준 전부 PASS 또는 N/A다. 그러나 D12는 M6 기준 **blocking**으로 분류된 비-필수통과(non-MP) 결함이며, M6은 "blocking findings are fixed before the verdict is revisited"라고 규정한다 — 즉 must-pass 방화벽을 통과했다고 해서 blocking 결함을 보유한 상태로 PASS를 선언할 수 없다.

## Iteration 3 Verdict (FINAL)

**Verdict: FAIL**
**Overall Score: ~0.94** (Clarity 1.0 · Completeness 1.0 · Testability 0.75[D12 1건] · Traceability 1.0 — 참고용 평균치; must-pass 자체는 전부 PASS/N/A이지만 D12 blocking 결함으로 verdict는 FAIL)

D10과 D11은 정확히, 요청받은 그대로 FIXED됐다 — 15개 REQ 전부 MP-2를 통과하고, REQ-002의 응답기 확장 부속 요구에 전용 AC + §A.1 비고가 생겼다. **그러나 그 수정 자체가 새 결함(D12)을 만들었다**: AC-LDBEAT-009(b)의 Then 절이 이 SPEC 자신의 실측 산출물(t525 verdict)과 불일치하는 틀린 수치("각 8대")를 "실측 기준"이라고 서술한다. 다행히 검증 수단 칸은 이미 올바른 일반형이므로, 수정 범위는 Then 절 한 문장을 지우거나 고치는 것으로 국한된다.

**Retry Loop Contract 고지 — iteration 3 상한 도달.** 이 SPEC의 plan-auditor 재심사는 iteration 3이며, `.claude/agents/moai/plan-auditor.md` § Retry Loop Contract의 "max 3 iterations per SPEC plan-phase" 상한에 도달했다. 이번 iteration이 FAIL로 끝났으므로, 같은 조항에 따라 전체 결함 이력과 함께 사용자 개입을 권고하는 최종 에스컬레이션을 제공한다(아래).

### 전체 결함 이력 (iteration 1~3)

- Iteration 1: D1~D9 발견(D1~D7 blocking, D8 optional-fixed, D9 optional-deferred).
- Iteration 2: D1~D8 전부 FIXED 확인, D9는 의도적 보류(수용). 전수 재검사로 D10(REQ-002 GEARS 혼입)·D11(REQ-002(c) traceability 공백) 신규 식별.
- Iteration 3: D10·D11 전부 FIXED 확인. 그 수정이 D12(AC-009(b) Then 절의 실측-불일치 수치)를 새로 만들었다.

**정체(stagnation) 여부**: 3회 모두 FAIL이었지만, 매 회차 사유가 바뀌었고(1→2: D1~D7 전부 해소, 2→3: D10/D11 전부 해소) 두 회차 모두 구체적 진전이 있었다 — `.claude/agents/moai/plan-auditor.md` § Retry Loop Contract의 "3회 연속 동일 결함 무변화" stagnation 정의에는 해당하지 않는다. 매번 결함이 "교체"됐을 뿐 "반복"되지는 않았다.

### Recommendation (Final — per Retry Loop Contract escalation)

1. (유일한 필수 수정) D12 — `acceptance.md:23` AC-LDBEAT-009(b) Then 절의 "각 8대"를 삭제하고 검증 수단 칸과 같은 일반형 문구로 교체한다. 이것은 한 문장짜리 수정이다.
2. 이 SPEC은 3회의 plan-audit iteration을 모두 사용했다 — `.claude/agents/moai/plan-auditor.md` § Retry Loop Contract 및 `spec-workflow.md` § SPEC Complexity Tier의 LEAN Workflow Additions("Max 3 iterations cap")에 따라, 오케스트레이터는 사용자에게 다음 세 선택지를 제시할 것을 권고한다: (a) D12만 수정한 뒤 PASS-with-debt로 착수 승인, (b) 이번에도 범위를 좁혀 iteration 4(명시적 사용자 승인 필요)로 한 번 더 확인, (c) 범위를 줄여 재계획. 수정 자체가 한 문장 교정이므로, 실무적으로는 (a)가 비용 대비 가장 합리적이다 — 다만 이 선택은 사용자/오케스트레이터의 권한이며 이 리포트가 대신 결정하지 않는다.

## Iteration 3 이후 — 레인 직접 수정 (D12, 감사 상한 도달 후)

- 결함: `acceptance.md:23` AC-LDBEAT-009(b) Then 절의 「네 그룹 실측 기준 각 8대」 — 잰 적 없는 숫자.
- 근거(레인이 다시 잼): `grep -n "SELECTIONDATA" .moai/reports/t525/verdict.md` → `:130` 「`SELECTIONDATA` 는 그룹당 **앞 2칸만** 봤다. 3번째 이후가 같은 꼴인지·전체 개수는 모른다.」
- 수정: 「콘솔에 저장된 실제 멤버 수 — t525는 앞 2칸만 읽어 전체 개수를 재지 못했다, `.moai/reports/t525/verdict.md:130`」 로 교체. 검증 수단 칸(반환 멤버 수 == 실제 멤버 수)은 원래 일반형이라 손대지 않음.
- 상태: plan-auditor 재확인(4회차)은 **하지 않았다** — Retry Loop 상한 3회. 4회차 확인 또는 PASS-with-debt 판정은 리드/감독 결정 사항으로 넘긴다.
