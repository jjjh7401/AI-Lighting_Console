# SPEC Review Report: SPEC-LDBEAT-001 (카드 t537 ① plan 개정, 커밋 33bff598)
Iteration: 1/3 (이 개정분만 — 카드 t526 iteration1/2는 이미 별도로 PASS 확정됨)
Verdict: **FAIL**
Overall Score: 0.55

M1 Context Isolation 선언: 프롬프트에 포함된 "지휘 결정(decision being encoded)" 서술과 레인의 사전 측정 메모는 작성자 추론 컨텍스트이므로 판단에 사용하지 않았다. 아래 모든 판정은 `git diff 640235f5 33bff598 -- .moai/specs/SPEC-LDBEAT-001/`로 드러난 spec.md / plan.md / acceptance.md / progress.md의 실제 텍스트와, 그 텍스트가 인용하는 저장소 파일(`reports/effect-arrangement-rules-20261007.md`, `reports/ldbeat-runbook-ui-proposal-20261008.html`, `server/design/beat_grid.py`)만으로 검증했다.

## Must-Pass Results

- [**FAIL**] MP-1 REQ number consistency: `spec.md` REQ-LDBEAT-001~015 15개, gap/dup 없음 (`grep -oE '^\| REQ-LDBEAT-[0-9]+'` 결과 15개 유니크, 001~015 연속). 번호 자체는 PASS지만 아래 MP-2가 FAIL이므로 이 항목은 참고용 PASS로만 기록한다.
- [**FAIL**] MP-2 EARS/GEARS Format Compliance (요구사항 레이어, `spec.md` REQ-XXX에만 적용 — AC는 별도 레이어, 아래 Group 4에서 채점): `spec.md:143` REQ-LDBEAT-006의 신설 (i)·(ii) 하위 절이, 앞서 이 SPEC 자신이 iteration 1(D1·D10)에서 FAIL로 판정하고 고친 것과 **동일한 결함 패턴**(굵은 GEARS 트리거가 붙은 문장 뒤에 트리거 없는 평서문 요구가 이어붙은 것)을 다시 들여왔다.
  - (i) 끝부분: "다섣 필드 모두 값이 없으면 명시적으로 비워 둔 미정(`null`)이고"는 `shall`/`shall not` 트리거가 없는 평서문이며, 단순 서술이 아니라 **독립적으로 테스트 가능한 요구**다(실제로 AC-LDBEAT-016(e)가 이 문장을 직접 검증한다 — "네 프리셋 필드 == `null` assert"). 요구를 테스트하면서 그 요구 자신은 GEARS 트리거가 없다.
  - (ii) 끝부분: "`label` 필드는 레거시 호환용으로 남되, M3 이후 새로 쓰는 칸은 구조화 필드를 채우고 `label`에 의존하지 않는다"는 완전히 트리거 없는 평서문이며, "M3 이후 새 칸은 `label`에 의존하지 않는다"는 (ii)의 핵심 요구(레거시 칸 읽기 규칙)와 무관한 **별도의 새 요구**(향후 칸 쓰기 규칙)다.
  - 이 패턴은 `acceptance.md:7`의 iteration 1 비고가 "REQ-LDBEAT-004/005/011/012/013/015가 하나의 요구사항 칸에 굵은 GEARS 트리거 없는 평서문 부속 요구를 이어붙인 것"이라고 명시적으로 FAIL 처리한 D1급 결함과 바이트 단위로 같은 모양이다. M5 규정대로 "mixed informal/formal within a single requirement = FAIL"이며, 다른 모든 점수와 무관하게 **전체 FAIL**을 강제한다.
- [**PASS**] MP-3 YAML Frontmatter Validity: `spec.md:1-15` 12개 필드 전부 존재·올바른 타입. `version: "0.3.0"`(인용 문자열), `updated: 2026-10-10`, 이전 `"0.2.1"`에서 정확히 증가. 금지된 별칭(`created_at` 등) 없음.
- [**N/A**] MP-4 Section 22 Language Neutrality: 이 SPEC은 조명 콘솔 도메인 전용 단일 프로젝트 SPEC이며 멀티언어 툴링을 다루지 않는다 — 자동 PASS 사유.
- [**PASS**] MP-5 D7 Cross-SPEC Reconciliation: 참조된 SPEC-ID 전부 확인 — `SPEC-LDRHYTHM-001`(in-progress) · `SPEC-LDDESIGN-001`(completed) · `SPEC-LDRENDER-001`(completed) · `SPEC-LDBARMAP-001`(in-progress) · `SPEC-LDARRANGE-001`(draft). retired/superseded/archived 0건 — BLOCKING 없음.
- [**PASS**] MP-6 D8 Cross-Platform Discipline: `grep -n "syscall" .moai/specs/SPEC-LDBEAT-001/{spec,plan,acceptance}.md` 0건 — D8-4 자동 PASS 조건 충족.
- [**PASS**] MP-7 [NEEDS CLARIFICATION] Marker Gate: `grep -rn '\[NEEDS CLARIFICATION' .moai/specs/SPEC-LDBEAT-001/plan.md .moai/specs/SPEC-LDBEAT-001/research.md` 0건(이 SPEC Tier M이라 `research.md` 자체가 없음, `plan.md`는 존재·검사했고 매치 없음).

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 — 여러 요구가 해석을 요함 | `spec.md:143` REQ-LDBEAT-006(i)이 밝기·효과 필드 다섯 개를 정의하면서 "값(value)" 모드와 §4의 실측 수치(아래 D2)의 관계를 명시하지 않아, 구현자가 값을 채워도 되는지 null로 둬야 하는지 각자 다르게 해석할 수 있다. `spec.md:143` REQ-LDBEAT-015(f)도 "프리셋 번호"로 범위를 좁혀 두면서 그 경계 밖(값·페이드초) 처리를 침묵한다. |
| Completeness | 0.50 | 0.50 — 여러 요구의 실질 내용이 비어있음 | D2·D3·D4(아래)가 보이듯, REQ-LDBEAT-006(i)/(ii)/(iii)와 REQ-LDBEAT-003(b)의 실패-경로 절반이 §A AC 매트릭스에서 실질적으로 비어 있다(§A.1의 매핑 주장과 실제 AC 본문이 불일치). 문서 섹션 자체(HISTORY/WHY/WHAT/REQUIREMENTS/AC/Out of Scope)는 전부 존재한다. |
| Testability | 0.50 | 0.50 — 여러 AC가 판단을 요하거나 구현 경로에 따라 성립하지 않음 | D5(AC-LDBEAT-009(c)가 REQ-003(b)이 허용한 두 구현 경로 중 하나에서만 성립) · D6(REQ-006(ii)의 "추측 금지"가 LOVE ATTACK 30큐 밖의 일반 레거시 칸에서는 전혀 검증되지 않음). |
| Traceability | 0.50 | 0.50 — 여러 REQ가 AC 없이 남음 | D3: `acceptance.md:38` §A.1이 "REQ-LDBEAT-006(i)~(iii) ... AC-LDBEAT-016(e)가 검증한다"고 명시하지만, `acceptance.md:33` AC-LDBEAT-016(e)의 Given/When/Then/검증 수단은 전부 REQ-LDBEAT-015(f)(네 프리셋 번호 필드의 null)만을 검사하도록 쓰여 있고 자신의 검증-수단 열에도 "(REQ-LDBEAT-015(f))"라고만 인용한다 — REQ-006(i)의 밝기 단일모드·entry 구조, (ii)의 레거시 읽기·파싱 금지, (iii)의 겹침-독립성 주장은 어느 AC에도 실제로 매핑돼 있지 않다. |

## Defects Found (structured defect-list)

D1. **MP2-REPEAT-006** — `spec.md:143`(REQ-LDBEAT-006 (i)·(ii)) — GEARS-MIX 재발: (i) 끝의 "다섣 필드 모두 값이 없으면 명시적으로 비워 둔 미정(`null`)이고"와 (ii) 끝의 "`label` 필드는 레거시 호환용으로 남되, M3 이후 새로 쓰는 칸은 구조화 필드를 채우고 `label`에 의존하지 않는다"가 둘 다 `shall`/`shall not` 굵은 트리거 없이 독립적으로 테스트 가능한 요구를 추가한다 — 이 SPEC의 iteration 1(D1/D4~D6)·iteration 2(D10) plan-audit가 이미 동일 패턴을 FAIL로 판정하고 고친 전례가 있다 — Severity: critical — Class: blocking — Required fix: (i)와 (ii)를 각각 "(i-1)/(i-2)", "(ii-1)/(ii-2)" 같은 서브 레터로 쪼개거나, 각 문장 앞에 굵은 `**The**...**shall**`/`**shall not**` 트리거를 명시적으로 붙인다. 근거·예시 서술(필드 목록, 명명 유래)은 근거 칸으로 옮긴다.

D2. **BRIGHTNESS-FADE-VALUE-GAP** — `spec.md:143`(REQ-LDBEAT-006(i))·`spec.md:143`(REQ-LDBEAT-015(f))·`acceptance.md:33`(AC-LDBEAT-016(e)) — `reports/effect-arrangement-rules-20261007.md:98-115`(§4) 표는 프리셋 **번호**는 0개이지만, 밝기 **퍼센트**(30%·40%·60%·70%·100% 등)와 페이드 **힌트**("2마디 번짐"·"1마디 번짐"·"끊어 바꿈")는 명시돼 있다(직접 재독 확인). REQ-LDBEAT-006(i)의 `brightness` 필드는 "값(value)" 모드를 정의하고 `entry`는 `fade_seconds`를 요구하는데, REQ-LDBEAT-015(f)의 "미정 하드룰"은 범위를 "`brightness`의 디머 프리셋·디머 효과 프리셋 번호·`position_preset_no`·`color_preset_no`·`effect_preset_no`"로만 좁혀, §4가 실제로 가진 값(퍼센트·마디 단위 페이드)에 대해서는 "채워라"도 "미정으로 두라"도 말하지 않는다. 마디→초 환산에 필요한 BPM/환산율은 이 SPEC 다른 곳(`reports/ldbeat-runbook-ui-proposal-20261008.html:620` "1마디 = 1.50초", REQ-LDBEAT-005(b)의 근거로만 인용됨)에 있지만 REQ-006(i)/015(f)는 이를 참조하지 않는다. AC-LDBEAT-016(e)도 네 프리셋 번호 필드의 null만 검사하고 `brightness.value_percent`/`entry.fade_seconds`는 전혀 조회하지 않는다 — Severity: critical — Class: blocking — Required fix: REQ-LDBEAT-006(i) 또는 015에 다섯째 절을 신설해 "`brightness`의 값(value) 모드와 `entry.fade_seconds`는 §4에 적힌 수치만 옮기고(또는: 전부 미정으로 둔다 — 결정 필요), 그 경우 마디→초 환산은 [환산율/결정 보류]를 쓴다"를 명시하고, AC-LDBEAT-016(e) 또는 신설 하위 시나리오가 그 값/null 상태를 실제로 조회해 단언하게 한다.

D3. **TRACE-OVERCLAIM-006** — `acceptance.md:38`(§A.1) vs `acceptance.md:33`(AC-LDBEAT-016(e) 본문·검증 수단) — §A.1은 "REQ-LDBEAT-006(i)~(iii)의 구조화 필드/미정 규칙은 ... AC-LDBEAT-016(e)가 검증한다"고 명시하지만, AC-LDBEAT-016(e)의 Given("LOVE ATTACK 기본값이 REQ-LDBEAT-006(i) 구조화 필드로 옮겨진 상태")·Then·검증 수단은 전부 REQ-LDBEAT-015(f)(네 프리셋 번호의 null)만을 다루고, 검증 수단 열 자체가 "(REQ-LDBEAT-015(f))"로만 인용한다. REQ-006(i)의 밝기 단일모드 강제(REQ-015(c)와 같은 제약이 `BeatGridCue.brightness`에도 적용되는지), (ii)의 레거시 `{bar,label}` 읽기(다섯 필드 null + `label` 그대로 표시 + 파싱 금지), (iii)의 겹침-거절 독립성 주장은 §A 매트릭스의 어느 AC에도 실제로 테스트되지 않는다(AC-007/AC-008은 곡별 기본값 비강제/곡별 저장 격리를 테스트할 뿐 무관) — Severity: major — Class: blocking — Required fix: REQ-006(ii)를 위한 전용 하위 시나리오(임의의 레거시 칸 → 5필드 null + label 유지 + 파싱 코드 grep 0건)와 REQ-006(iii)을 위한 하위 시나리오(겹침 거절이 칸 레벨 변경 전후 동일하게 동작)를 AC-003 또는 새 AC 하위 문자로 추가하고, §A.1의 매핑 주장을 실제 AC 내용과 일치시킨다.

D4. **TRACE-GAP-003b-ERRORPATH** — `spec.md:89`(REQ-LDBEAT-003(b) 후반 "표가 비어 있거나 파싱할 수 없으면 화면은 '미확인'으로 ... 지어낸 PASS를 보여주지 **shall not**") vs `acceptance.md:25`(AC-LDBEAT-009(c)) — AC-009(c)의 Given/When/Then/검증 수단은 "progress.md를 고쳐 쓴 뒤 화면 재조회 → 손 상수 파일 grep 의존 0건 + 화면 값 일치"만 검사하는 happy-path 전용이며, REQ-003(b)가 명시한 실패 경로(표 부재/파싱 실패 → "미확인" 표시, 지어낸 PASS 금지)는 어느 AC에도 매핑돼 있지 않다 — Severity: major — Class: blocking — Required fix: AC-LDBEAT-009에 (d) 하위 시나리오를 추가해 "progress.md가 없거나 M1 표가 깨진 상태 → 화면이 9항목 전부 '미확인'으로 표시되고 임의 PASS 0건"을 기계 검증으로 명문화한다.

D5. **TESTMETHOD-MECHANISM-MISMATCH** — `spec.md:89`(REQ-LDBEAT-003(b) "서버가 그 표를 파싱해 서빙하거나(권고), 빌드 타임에 그 표를 읽어 생성하는 경로 중 하나") vs `acceptance.md:25`(AC-LDBEAT-009(c) 검증 수단 "progress.md의 M1 표를 고쳐 쓴 뒤 화면 재조회") — REQ가 명시적으로 두 구현 경로를 모두 허용하는데, AC의 검증 절차는 "재빌드" 단계 없이 "수정 후 재조회"만 요구한다. 구현이 "빌드 타임 생성" 경로를 택하면 이 AC는 재빌드 없이는 성립하지 않는다 — REQ가 허용한 한 branch에서 AC가 테스트 불가능해지는 모순 — Severity: minor — Class: blocking — Required fix: AC-009(c)에 "(빌드 타임 생성 경로를 택한 경우, 재빌드 후 재조회)"를 조건부로 추가하거나, REQ-003(b)에서 두 경로 중 하나로 확정(권고안인 "서버 파싱" 채택)하여 AC와 REQ가 같은 구현 가정을 공유하게 한다.

D6. **LEGACY-PARSE-BAN-UNDERTESTED** — `spec.md:143`(REQ-LDBEAT-006(ii) "`label`의 자유 텍스트를 파싱해 구조화 필드를 역산·추측하는 것은 **shall not**이다") — 이 금지는 임의의 레거시 칸 전반에 적용되는 요구인데, 유일하게 관련된 AC-LDBEAT-016(e)는 LOVE ATTACK의 특정 30개 큐만을 대상으로 하고 그마저 네 프리셋 번호 필드의 null 여부만 확인하며, 출력이 null인 것이 "파싱 코드가 존재하지 않는다"는 것의 증거가 되지 못한다(우연히 항상 null을 반환하는 파싱 함수도 이 assert를 통과한다) — 다른 REQ(예: REQ-LDBEAT-005 AC-005)는 `grep -rn "parse_cue_sheet_edit_request\|apply_cue_sheet_edit" <소스>` 식의 코드-부재 확인을 AC 검증 수단에 명시하는 선례가 있다 — Severity: minor — Class: blocking — Required fix: AC-LDBEAT-005 패턴을 본떠, 격자 레거시-읽기 경로 소스에 `label` 파싱용 정규식/문자열 분해 함수가 없음을 grep으로 확인하는 검증 수단을 AC-016(e) 또는 신설 하위 시나리오에 추가한다.

D7. **CITATION-OFFBYONE** — `spec.md:31`("`reports/ldbeat-runbook-ui-proposal-20261008.html`(전체 **656행** 재검증)") — 실측: `wc -l reports/ldbeat-runbook-ui-proposal-20261008.html` → **655**(파일이 개행으로 끝나 실제 줄 수와 일치, 오프바이원 아님 재확인). "656행"은 실제보다 1줄 많다 — Severity: minor — Class: optional — Required fix: "656행"을 "655행"으로 정정한다(사실 서술 정확성 — 요구/AC 본문에는 영향 없음).

D8. **CITATION-LABEL-MISMATCH** — `spec.md:31`("acceptance.md에 AC-LDBEAT-003(d)·AC-LDBEAT-009(c)·AC-LDBEAT-016(**f**) 하위 시나리오를 추가했다") vs `acceptance.md:11,33,38`(실제로는 전부 "AC-LDBEAT-016(**e**)")·`progress.md:191`(역시 "AC-LDBEAT-016(e)") — spec.md의 HISTORY 행만 유일하게 "(f)"로 잘못 인용한다. 같은 커밋 안에서 세 문서 중 하나가 다른 둘과 다른 레터를 인용하는 내부 불일치 — Severity: minor — Class: optional — Required fix: `spec.md:31`의 "AC-LDBEAT-016(f)"를 "AC-LDBEAT-016(e)"로 정정한다.

D9. **SCHEMA-POOL-COVERAGE-AMBIGUITY** — `spec.md:143`(REQ-LDBEAT-006(i) "효과 프리셋(`effect_preset_no`, 위치 효과 풀 ...)") vs `spec.md:143`(REQ-LDBEAT-015(b) "효과 프리셋은 종류별 풀에 나눠 담긴다 — 위치 효과는 위치 풀, **색 효과는 색 풀**(기본 색 풀과 분리), 밝기 효과는 디머 풀, 밝기·색 등이 섞인 효과만 이 곡 전용 All 풀") — REQ-015(b)는 위치·색·밝기(디머)·혼합(All) 네 종류의 "효과 풀"을 정의하지만, REQ-006(i)의 `BeatGridCue` 구조화 필드 다섯 개(brightness/position_preset_no/color_preset_no/effect_preset_no/entry) 중 `effect_preset_no`는 그 괄호 설명으로 "위치 효과 풀"에만 명시적으로 고정돼 있다. "색 효과"(정적 색 프리셋이 아니라 색 체이스/펄스 같은 동적 효과)나 "밝기·색 혼합 All 풀" 효과가 참조될 때 어느 구조화 필드에 담기는지 REQ-006(i)에 자리가 없다 — Severity: minor — Class: optional — Required fix: REQ-006(i)에 색 효과·혼합 효과가 들어갈 자리(예: `color_preset_no`가 색 효과도 겸하는지, 또는 별도 필드가 필요한지)를 M2/M3 결정 대상으로 명시하거나, §5 열린 결정에 항목을 추가한다.

## Regression Check

이 보고서는 카드 t537의 첫 iteration이다 — 이전 iteration의 defect 목록이 없으므로 회귀 확인 대상 없음. (카드 t526의 iteration 1/2 defect는 이미 `.moai/reports/t526/plan-audit.md`에서 별도로 PASS 확정됐으며, 본 보고서의 범위는 commit 33bff598의 diff로 한정한다.)

## Recommendation

FAIL — 아래 순서로 수정할 것을 권고한다(결정 번복 비용 순):

1. **D1 (Must-Pass, 최우선)**: `spec.md:143` REQ-LDBEAT-006(i)·(ii)의 트리거 없는 평서문 두 곳을 각각 굵은 GEARS 트리거가 있는 별도 서브 레터로 쪼갠다. 이 SPEC은 이미 두 차례(iteration 1 D1/D10, iteration 2 D10) 같은 패턴을 직접 고친 전례가 있으므로 같은 재구조화 공식을 그대로 적용하면 된다.
2. **D2 (Must-fix, 완전성)**: §4의 밝기 퍼센트/페이드 마디 힌트를 `brightness.value_percent`/`entry.fade_seconds`에 어떻게 반영할지(옮긴다/미정으로 둔다/결정 보류) 명시하고, 보류라면 §5 열린 결정에 항목을 신설한다. 옮긴다면 AC-016(e)에 그 값을 검증하는 하위 절을 추가한다.
3. **D3·D4 (traceability)**: §A.1의 매핑 주장과 AC-016(e)의 실제 검증 범위를 일치시키고, REQ-006(ii)/(iii)와 REQ-003(b) 실패-경로를 위한 전용 AC 하위 시나리오를 추가한다.
4. **D5·D6 (testability)**: AC-009(c)를 REQ-003(b)가 허용한 두 구현 경로 모두에서 성립하도록 조건부 문구를 추가하거나 REQ 쪽에서 경로를 확정한다. AC-016(e)에 파싱-코드-부재 grep 검증을 추가한다.
5. **D7·D8 (사소, optional)**: "656행"→"655행", "AC-LDBEAT-016(f)"→"(e)" 두 인용을 정정한다.
6. **D9 (optional)**: 색 효과/혼합 효과의 구조화 필드 귀속을 M2/M3 결정 대상으로 명시한다.

수정 후 이 보고서의 D1~D9 범위로 한정한 재감사(delta 스코프)를 요청한다 — iteration 2.

커밋 SHA: 이 보고서 작성 후 커밋(아래 참조).

## Iteration 2

M1 Context Isolation 선언: 이 재감사 프롬프트에 포함된 지휘/배차 서술은 작성자 추론 컨텍스트이므로 판단에 사용하지 않았다. 아래 모든 판정은 `git diff 638c02ae 41b4925c -- .moai/specs/SPEC-LDBEAT-001/`로 드러난 spec.md/plan.md/acceptance.md/progress.md의 실제 텍스트와, 그 텍스트가 인용하는 저장소 파일(`reports/effect-arrangement-rules-20261007.md:98-115`, `reports/ldbeat-runbook-ui-proposal-20261008.html`, `server/design/beat_grid.py`)을 직접 재독·grep해 검증했다. 재감사 범위는 iteration 1 defect D1~D9의 delta scope로 한정했다(Retry Loop Contract).

Verdict: **PASS**
Overall Score: 0.90 (Tier M 임계 0.85 이상 — `spec-workflow.md` § SPEC Complexity Tier)

### D1~D9 결함별 판정

- **D1 (GEARS-MIX 재발) — RESOLVED.** `spec.md:100` REQ-LDBEAT-006의 (i)·(ii)가 (i-1)~(i-7)·(ii-1)~(ii-5)로 재구조화됐다. 전수 재독(`grep -n "^| REQ-LDBEAT-006" spec.md`로 추출한 전체 셀 텍스트) 결과 (i-1)~(i-7)·(ii-1)~(ii-5)·(iii) 13개 서브 레터 **전부**가 굵은 GEARS 트리거(`**The**…**shall**`/`**shall not**`/`**When**…**shall**`/`**While**…**shall**`)를 갖는다 — 트리거 없는 평서문은 더 이상 없다. 다만 (i-3)·(i-4)는 다른 서브절(예: (i-1)(i-2)(i-6)(ii-2)(ii-3))과 달리 `**The**` 없이 바로 `` `effect_preset_no` **shall**... ``/`` `entry` 필드 **shall**... ``로 시작한다 — 트리거(`**shall**`/`**shall not**`) 자체는 굵게 있어 M3 rubric의 GEARS 트리거 요건은 충족하지만, 같은 REQ 안에서 트리거 앞 주어 표기 스타일이 섞여 있다(cosmetic). 이 비일관성은 트리거 부재가 아니므로 MP-2 FAIL 조건("informal language ... 없이")에 해당하지 않는다 — **optional** 등급으로만 아래 새 발견 N1에 기록한다.
- **D2 (BRIGHTNESS-FADE-VALUE-GAP) — RESOLVED.** `spec.md:100` REQ-LDBEAT-006(i-4)~(i-7)에 `entry.fade_bars`(마디 수, 초 아님)와 `source_ref` 필드를 신설하고, §4의 밝기 퍼센트/페이드 힌트 전사 규칙을 명시했다. `reports/effect-arrangement-rules-20261007.md:104,106,108,109,110` 전수 재독(직접 `awk`/`sed`로 재확인) 결과 `acceptance.md:36-40` "§A 보충 — 전사값 기대표"가 적은 네 자리(BACK(그룹4)@7마디=60%`:106`·@18마디=100%`:109`·@22마디=100%`:110`, BLIND(그룹14)@18마디=100%`:109`)가 §4 원문과 정확히 일치한다. `server/design/beat_grid.py:194-263` `_love_attack_tracks()`를 직접 재독해 BACK 트랙(`group_no=4`)의 cue(bar=7/18/22)와 BLIND 트랙(`group_no=14`)의 cue(bar=18)가 그 값을 실제로 갖고 있음을 확인했고, 나머지 26개 큐(SIDE-ALL 7·MOVER-U 7·MOVER-D 7·BLIND 나머지 1·STROBE 0) 어디에도 숫자 퍼센트가 없음을 전수 확인했다 — 전사 대상이 "이 넷뿐"이라는 SPEC의 주장은 실측과 바이트 단위로 일치한다. `entry.fade_bars`에 대응하는 숫자 페이드 힌트("2마디 번짐"·"끊어 바꿈"·"1마디 번짐")는 전부 SCENE 열(`:104,106,109,110`)에만 있고 SCENE은 `_love_attack_tracks()`의 트랙이 아니므로(`server/design/beat_grid.py:179` 주석 "SCENE은 트랙에서 뺐다" 직접 확인) 30개 큐 전부의 `fade_bars`가 `null`이라는 주장도 실측과 일치한다.
- **D3·D4 (TRACE-OVERCLAIM / TRACE-GAP) — RESOLVED.** `acceptance.md:34` AC-LDBEAT-016에 (f)(값·페이드 전수 대조)·(g)(레거시 읽기 + `label`-파싱 부재 grep, REQ-006(ii-1)(ii-2))·(h)(겹침 독립성, REQ-006(iii)) 세 하위 시나리오가 신설됐고, `acceptance.md:27` AC-LDBEAT-009에 (d)(M1 실패-경로, REQ-003(b))가 신설됐다. `acceptance.md:53` §A.1의 "REQ-LDBEAT-006 → AC-016(e)(f)(g)(h)" 매핑 주장이 이제 AC-016 본문의 실제 Given/When/Then/검증수단과 일치한다(각 레터가 각자의 REQ 서브 레터를 인용 — (f)→(i-5)~(i-7), (g)→(ii-1)(ii-2), (h)→(iii)).
- **D5 (TESTMETHOD-MECHANISM-MISMATCH) — RESOLVED.** `acceptance.md:27` AC-LDBEAT-009(c)의 검증 수단에 "서버 파싱 경로인 경우 즉시 재조회로 충분하고, 빌드 타임 생성 경로를 택한 경우 재빌드 후 재조회" 조건부 문구가 추가돼, REQ-LDBEAT-003(b)가 허용한 두 구현 경로 모두에서 AC가 성립한다.
- **D6 (LEGACY-PARSE-BAN-UNDERTESTED) — RESOLVED.** `acceptance.md:34` AC-LDBEAT-016(g)의 검증 수단에 "`grep -rn` 레거시-읽기 경로 소스에서 라벨 파싱 함수 부재 확인(AC-LDBEAT-005 패턴과 동일)"이 추가됐다 — 출력이 우연히 `null`을 반환하는 파싱 함수를 걸러내는 코드-부재 확인 방식이다.
- **D7 (CITATION-OFFBYONE) — RESOLVED.** `spec.md:31`(HISTORY 2026-10-10 행)의 "전체 656행 재검증"이 "전체 655행 재검증"으로 정정됐다. 재실측: `wc -l reports/ldbeat-runbook-ui-proposal-20261008.html` → **655** — 정정된 문면과 일치.
- **D8 (CITATION-LABEL-MISMATCH) — RESOLVED.** 같은 HISTORY 행의 "AC-LDBEAT-016(f)" 오기가 "AC-LDBEAT-016(e)"로 정정돼, `acceptance.md`·`progress.md`의 기존 인용("(e)")과 일치한다.
- **D9 (SCHEMA-POOL-COVERAGE-AMBIGUITY) — RESOLVED.** `spec.md:100` REQ-LDBEAT-006(i-3)에 `effect_kind`(`"position"|"color"|"dimmer"|"mixed"|null`) 필드가 신설돼 `effect_preset_no`가 위치 효과 풀에만 고정됐던 결함을 교정했고, `spec.md:209`(§5 열린 결정 7항)에 색·혼합 효과의 구체 실례를 M2/M3 재확인 대상으로 명시했다. `plan.md:146-154`(M7 (1))도 `effect_kind`·`fade_bars`·`source_ref`로 갱신돼 spec.md와 일치한다.

### 새로 발견한 결함 (이번 수정이 들여온 것)

- **N1 (optional, cosmetic)** — `spec.md:100` REQ-LDBEAT-006(i-3)·(i-4)가 다른 서브 레터((i-1)(i-2)(i-5)(i-6)(i-7)(ii-1)~(ii-5)(iii))와 달리 `**The**` 굵은 주어 마커 없이 바로 `` `effect_preset_no` **shall**... ``/`` `entry` 필드 **shall**... ``로 시작한다. GEARS 트리거(`**shall**`/`**shall not**`) 자체는 굵게 존재하므로 MP-2 FAIL 조건(트리거 부재)에는 해당하지 않으나, 같은 REQ 내부에서 주어-마커 볼드 스타일이 비일관적이다 — Severity: minor — Class: optional — Required fix(선택): (i-3)·(i-4) 앞에도 `**The**`를 붙여 스타일을 통일한다.
- **N2 (optional, bundling)** — `spec.md:100` (i-4)와 (i-7)이 각각 한 서브 레터 안에 서로 다른 두 개의 독립 GEARS 단언(예: (i-4) "entry shall 마디 수로 담는다" + "초 단위 저장은 shall not", (i-7) "그 자리는 shall null이다" + "추측해 채우는 것은 shall not이다")을 묶어 담고 있다. 둘 다 트리거가 명시적이라 MP-2 FAIL은 아니지만, 이후 테스트 작성 시 한 레터에 두 개의 독립 검증 포인트가 생겨 AC 쪽에서 1:1 대응이 흐려질 위험이 있다 — Severity: minor — Class: optional — Required fix(선택): 필요시 (i-4)를 (i-4a)/(i-4b), (i-7)을 (i-7a)/(i-7b)로 더 쪼갠다. 현재 AC-016(f)/(g)가 이미 실질적으로 양쪽을 커버하고 있어 지금 당장 blocking은 아니다.

둘 다 M6 Finding-consumption discipline상 **optional**로 분류한다 — MP-2 자체는 트리거가 모두 존재하므로 PASS이고, 이 두 발견은 스타일 통일성 문제일 뿐 SPEC의 정합성·완전성·테스트 가능성을 해치지 않는다. 오케스트레이터 재량으로 남긴다(강제 수정 유발 금지).

### SCENE 제외의 정직한 고지 여부 (질의 3)

**명시적으로 기술돼 있다 — 숨겨진 손실이 아니다.** 아래 세 자리에서 일관되게 서술:

1. `acceptance.md:40` §A 보충: "30개 큐 전부의 `entry.fade_bars`는 `null`이다 — §4의 마디 단위 페이드 힌트는 모두 SCENE 열에 있고, SCENE은 `_love_attack_tracks()`에 트랙으로 없다(`server/design/beat_grid.py` docstring "SCENE은 트랙에서 뺐다") — 대응하는 큐가 없으므로 전사 대상이 아니다. SCENE 자신의 밝기 퍼센트(0~2행 30%:104, 7~10행 40%:106, 18~21행 70%:109)와 14~17행 "워시 25% 덜어냄"(...)도 같은 이유 + REQ-LDBEAT-006(i-6)(상대 서술 미전사 규칙)로 전사되지 않는다."
2. `spec.md:100` REQ-LDBEAT-006(i-4)~(i-7) 근거 칸: "`_love_attack_tracks()`의 실제 30개 큐 중 이 퍼센트가 대응하는 자리는 acceptance.md § 보충(...)에 전수 enumeration했다 — SCENE 열의 퍼센트·페이드 힌트는 SCENE이 트랙에 없어(...) 대응 큐가 없으므로 전사 대상이 아니다."
3. `plan.md:146,154` M7(1): "SCENE 열의 30%·40%·70%·'2마디 번짐'·'끊어 바꿈'·'1마디 번짐'(:104,106,109,110)은 SCENE이 트랙에 없어 ... 대응 큐가 없으므로 전사하지 않는다" — 그리고 `plan.md:26`(§B 위험 14)는 이를 M7이 빠뜨리지 않도록 명시적으로 경고하는 위험 항목으로 올렸다: "§4의 밝기 퍼센트·마디 페이드 힌트를 'SCENE 열이니까 전사 대상 없음'으로 뭉뚱그려 생략하지 마라... M7 (1)이 이 넷을 빠뜨리고 '전부 null'로 단순화하면 REQ-LDBEAT-006(i-5)를 위반한다."

세 문서가 SCENE 자신의 수치(30%/40%/70%, 재독으로 값까지 정확 재확인)를 구체적으로 적시하면서 "트랙이 아니므로 전사하지 않는다"는 이유를 매번 함께 적었다 — 수치를 감추거나 뭉뚱그려 생략한 흔적이 없다. 질의 3은 **결함 아님**으로 판정한다.

### 재발 방지 확인 (Stagnation Check)

D1(GEARS-MIX)은 iteration 1(D1/D10)·iteration 2(D10)에 이어 이 카드 t537 round에서도 3회째 같은 패턴으로 재발했었으나, 이번 수정으로 **13개 서브 레터 전수**가 트리거를 갖도록 재구조화됐고 cosmetic 잔여(N1/N2)만 남았다 — stagnation(동일 결함 무진전)이 아니라 진전으로 판정한다.

## Must-Pass Results (Iteration 2)

- [**PASS**] MP-1 REQ number consistency: `grep -oE '^\| REQ-LDBEAT-[0-9]+' spec.md | sort -u | wc -l` → 15, 001~015 연속·중복 없음 (불변).
- [**PASS**] MP-2 EARS/GEARS Format Compliance: REQ-LDBEAT-006의 (i-1)~(i-7)·(ii-1)~(ii-5)·(iii) 13개 서브 레터 전수가 굵은 트리거(`**The**…**shall**`/`**shall not**`/`**When**…**shall**`/`**While**…**shall**`)를 갖는다(`spec.md:100` 직접 재독, 트리거 없는 평서문 0건). N1(일부 서브 레터가 `**The**` 없이 바로 `**shall**`로 시작)은 트리거 자체는 존재하므로 FAIL 조건에 해당하지 않는 cosmetic 비일관성이다.
- [**PASS**] MP-3 YAML Frontmatter Validity: `spec.md:1-15` 12개 필드 전부 존재·올바른 타입 유지(`version: "0.3.0"`, `updated: 2026-10-10`) — 이번 수정은 REQ/AC 본문만 바꿨고 frontmatter 변경 없음.
- [**N/A**] MP-4 Section 22 Language Neutrality: 단일 프로젝트 SPEC, 멀티언어 툴링 미해당 (불변).
- [**PASS**] MP-5 D7 Cross-SPEC Reconciliation: `grep -oE 'SPEC-([A-Z][A-Z0-9]+-)+[0-9]+' spec.md | sort -u` → SPEC-LDARRANGE-001·SPEC-LDBARMAP-001·SPEC-LDBEAT-001·SPEC-LDDESIGN-001·SPEC-LDRENDER-001·SPEC-LDRHYTHM-001 — retired/superseded/archived 0건, BLOCKING 없음 (불변).
- [**PASS**] MP-6 D8 Cross-Platform Discipline: `grep -n "syscall" spec.md plan.md acceptance.md` 0건 — D8-4 자동 PASS (불변).
- [**N/A**] MP-7 [NEEDS CLARIFICATION] Marker Gate: `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` — Tier M이라 `research.md` 자체가 없음(N/A 사유), `plan.md` 매치 0건.

## Category Scores (0.0-1.0, rubric-anchored) — Iteration 2

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 0.75~1.0 경계 — 거의 모든 요구가 단일 해석 | D2 수정으로 `brightness.value_percent`/`entry.fade_bars`의 출처·단위·전사 규칙이 명시됐다(`spec.md:100` (i-4)~(i-7)). N1/N2의 스타일 비일관성만 남아 1.0에는 못 미친다. |
| Completeness | 0.90 | 0.75~1.0 경계 | §A 보충 전사값 기대표(`acceptance.md:36-40`)와 §5 열린 결정 7항(`spec.md:209`)이 신설돼 D2/D9가 비워 둔 내용을 채웠다. 모든 섹션·frontmatter 존재. |
| Testability | 0.90 | 0.75~1.0 경계 | AC-LDBEAT-016(f)(g)(h)·AC-LDBEAT-009(d)가 전부 기계 검증(grep/assert) 수단을 명시한다(`acceptance.md:34,27`). N2가 지적한 번들링(한 서브 레터에 두 단언)만 남아 1.0에는 못 미친다. |
| Traceability | 0.90 | 0.75~1.0 경계 | `acceptance.md:53` §A.1의 "REQ-006 → AC-016(e)(f)(g)(h)" 매핑이 AC-016 본문과 일치하고, AC-009(d)가 REQ-003(b) 실패-경로를 커버한다. REQ-006(ii-3)(ii-4)(ii-5)(M3 이후 대상)는 AC-016(g)의 Given/Then에 포괄적으로만 걸려 레터 단위 1:1은 아니나, M3 미착수 단계에서 이는 선택적(optional) 간극이다. |

## Overall Score 산정

(0.90+0.90+0.90+0.90)/4 = 0.90. Tier M plan-auditor PASS threshold(`spec-workflow.md` § SPEC Complexity Tier) 이상 — Must-Pass 7개 전부 PASS/N/A, 블로킹 결함 0건.

## Regression Check (Iteration 2)

Iteration 1 defect D1~D9 전부 위 "D1~D9 결함별 판정"에서 RESOLVED로 확인했다 — UNRESOLVED 0건. 새로 발견한 N1·N2는 둘 다 optional(cosmetic/번들링)이며 blocking 등급의 신규 결함이 아니다.

## Recommendation (Iteration 2)

PASS — Must-Pass 7개(MP-1~MP-7) 전부 PASS 또는 N/A, D1~D9 전부 해소, aggregate 0.90은 Tier M 임계 이상이다. N1·N2(optional)는 오케스트레이터 재량으로 다음 plan 개정 시 반영하거나 보류해도 되며, 강제 수정 대상이 아니다. run-phase 착수 전 Implementation Kickoff Approval(감독 승인)은 별도로 필요하다(본 PASS가 그 승인을 대체하지 않음).

커밋 SHA (iteration 2 재감사 대상): 41b4925c (fix) — 직전 638c02ae (iteration 1 FAIL 보고서 커밋) 대비 diff 전수 재독으로 판정.

## Iteration 3 — SCENE 메모·리그 일반화 개정

**대상**: `git diff 10ae09e7 21338bfe -- .moai/specs/SPEC-LDBEAT-001/` (커밋 `21338bfe`, 카드 t537) — iteration 2가 PASS(0.90) 확정한 `(i)~(iii)`/`(a)~(h)` 본문은 건드리지 않은 순수 추가분(spec.md REQ-LDBEAT-006(iv-1)~(iv-4)·(v-1)(v-2) 신설, acceptance.md AC-LDBEAT-016(i)(j)(k)(l)(m) 신설). 코드 변경 0줄(`git diff --stat 10ae09e7 21338bfe` → 4개 문서 파일만, +13/-5) — spec.md/acceptance.md/plan.md/progress.md만.

M1 Context Isolation 선언: 프롬프트에 포함된 작성자 쪽 근거·추론(리드 지시 인용, 감독 원칙 인용, "선택 사항으로 남긴다"는 자체 평가)은 판단에 사용하지 않았다. 아래 모든 판정은 diff가 드러낸 spec.md/acceptance.md/plan.md/progress.md 실제 텍스트와, 그 텍스트가 인용하는 저장소 파일(`server/design/beat_grid.py`, `server/design/beat_grid_data/love_attack.yaml`, `ui/src/protocol.ts`, `ui/src/components/BeatGrid.tsx`, `ui/src/components/BeatGrid.test.tsx`, `server/tests/test_beat_grid_t537.py`, `server/tests/test_beat_grid_t532.py`, `reports/effect-arrangement-rules-20261007.md`)을 직접 읽고 대조해서만 내렸다.

### Must-Pass Results (이 개정분)

- [**PASS**] MP-1 REQ number consistency: `grep -oE '^\| REQ-LDBEAT-[0-9]+' spec.md \| sort -u \| wc -l` → 15, 001~015 연속·중복 없음(불변, 새 REQ-ID 없음).
- [**PASS**] MP-2 EARS/GEARS Format Compliance: 신설 (iv-1)~(iv-4)·(v-1)(v-2) 6개 서브 레터 전수가 굵은 트리거(`**The**…**shall**`/`**shall not**`, `**While**…**shall**`, `**When**…**shall**`)를 갖는다(`spec.md:101` 직접 재독). 트리거 없는 평서문 0건 — iteration 1/2의 D1(GEARS-MIX) 재발 없음.
- [**PASS**] MP-3 YAML Frontmatter Validity: `spec.md:1-15` 12개 필드 전부 존재·올바른 타입, `version: "0.3.0"→"0.3.1"` 정확히 증가, `updated: 2026-10-10` 유지.
- [**N/A**] MP-4 Section 22 Language Neutrality: 단일 프로젝트 SPEC, 멀티언어 툴링 미해당.
- [**PASS**] MP-5 D7 Cross-SPEC Reconciliation: `related_specs`의 SPEC-LDRHYTHM-001(`status: in-progress`)·SPEC-LDDESIGN-001(`status: completed`)·SPEC-LDRENDER-001(`status: completed`) 전부 재확인 — retired/superseded/archived 0건, BLOCKING 없음.
- [**N/A**] MP-6 D8 Cross-Platform Discipline: 이 개정분에 `syscall` 언급 0건 — D8-4 자동 PASS.
- [**N/A**] MP-7 [NEEDS CLARIFICATION] Marker Gate: Tier M이라 `research.md` 자체가 없음(N/A 사유, `ls`로 부재 확인). `grep -rn '\[NEEDS CLARIFICATION' plan.md` 매치 0건.

Must-Pass 7개 전부 PASS 또는 N/A — Firewall에 의한 강제 FAIL은 없다. 그러나 아래 Category Scores가 이 개정분 단독으로 Tier M PASS 임계를 못 넘긴다.

### Category Scores (이 개정분, 0.0-1.0)

| Dimension | Score | 근거 |
|---|---|---|
| Clarity | 0.75 | (iv-1)~(v-2) 전수가 단일 해석 가능한 GEARS 문장이다. 다만 D4(아래)가 지적하는 "기계" 라벨 오용이 "무엇이 실제로 검증됐는가"에 대한 해석 모호성을 만든다. |
| Completeness | 0.75 | HISTORY(`acceptance.md:15`)·DoD 체크리스트(`acceptance.md` §D 2건 추가)·§A.1 매핑 갱신은 모두 들어갔다. 다만 D1(아래) — REQ-LDBEAT-006(iv-3) 전체가 AC-016(i)~(m) 어디에도 없어 커버리지가 완전하지 않다. |
| Testability | 0.50 | 신설 AC 5개(i~m) 중 3개(k·l·m)의 "검증 수단"(기계) 칸이 실제로 존재하지 않거나(D2) 다른 AC/다른 파일로 잘못 귀속되거나(D3) 수작업 대조를 "기계"로 오표기한다(D4). |
| Traceability | 0.50 | D1 — REQ-LDBEAT-006(iv-3)이 완전히 미추적(AC 0개). D2 — AC-016(l)이 존재하지 않는 테스트를 인용. D3 — AC-016(m)의 Then 절 일부가 인용된 테스트 클래스 밖(다른 파일)에서만 검증된다. |

조화평균 = 4 / (1/0.75 + 1/0.75 + 1/0.50 + 1/0.50) = 4 / 6.667 ≈ **0.60**. iteration 2가 확정한 전체 문서 점수(0.90)와는 별도로, **이 개정분 자체는 Tier M PASS 임계(0.90대, iteration 2 기준)에 크게 못 미친다.**

### Defects Found (이 개정분)

D1. **REQ-LDBEAT-006(iv-3) 완전 미추적** — `spec.md:101`(iv-3: "**When** (iv-1)의 메모가 화면에 노출되면, UI는 **shall** 그 칸에 명시적 '미정' 표시와 §4 원문 텍스트 + `source_ref`를 함께 보여준다")와 `acceptance.md:36` AC-LDBEAT-016(i)(j)(k)(l)(m) 전체를 대조한 결과, 이 UI 렌더링 요구에 대응하는 AC 서브-레터가 **하나도 없다**(i)=데이터 대조, (j)=트랙 부재, (k)=세 조건, (l)=시그니처, (m)=로더 일반화 — 전부 서버/데이터 레벨이고 UI 렌더링을 다루는 것이 없음). 실제 구현은 존재한다(`ui/src/components/BeatGrid.tsx:1000-1003`, `⚠ {viewBarSceneMemo.text}` + `source_ref` 동시 렌더)지만, 그 구현을 검증하는 어떤 렌더링 단언도 `ui/src/components/BeatGrid.test.tsx`에 없다 — 같은 파일의 `sceneMemoForBar` 유닛 테스트(345-367행)는 데이터 선택 로직만 검증하고 DOM 렌더는 검증하지 않는다(`grep -n "getByText\|⚠" BeatGrid.test.tsx`에 메모 관련 매치 0건, 확인함). — Severity: major — Class: blocking — 수정: AC-LDBEAT-016에 새 하위 시나리오(예: (n), Tier M AC 상한 16개는 "새 AC-ID" 금지이므로 기존 (i)의 Then에 UI 표시절을 추가하거나 §A 보충에 별도 렌더링 체크리스트 항목으로 편입) + `BeatGrid.test.tsx`에 memo가 있을 때 "⚠" 배지·원문 텍스트·`source_ref`가 **함께** 렌더되는지 확인하는 RTL 테스트를 추가한다.

D2. **AC-LDBEAT-016(l)의 "기계" 검증 수단이 실제로 존재하지 않음** — `acceptance.md:36`은 (l)의 검증 수단을 "`inspect.getsource(find_overlapping_group_tracks)`/`inspect.getsource(validate_beat_grid_tracks)` 소스에 `scene_memos` 참조 0건 확인 + 두 함수의 매개변수 목록에 `scene_memos` 부재 확인"이라고 명시한다. `grep -n "scene_memos\|getsource" server/tests/test_beat_grid_t537.py` 전수 재확인 결과, 이 파일에서 `inspect.getsource`를 쓰는 곳은 `test_find_overlapping_group_tracks_has_no_song_specific_branch`(323행) 단 한 곳이고, 그 단언은 리그 전용 리터럴(`"BACK"` 등) 부재만 확인한다 — `scene_memos` 참조·매개변수 부재를 확인하는 코드는 이 파일에도, 저장소 전체 `grep -rn "scene_memos" server/tests/`에도 없다. 실제 코드 속성 자체는 참(수동 재확인: `server/design/beat_grid.py:186` `find_overlapping_group_tracks(group_names: Sequence[str])`, `:226` `validate_beat_grid_tracks`, 둘 다 `scene_memos` 미참조)이지만, AC가 인용한 검증 수단은 **지금 존재하지 않는 테스트를 가리키는 "관측되지 않은 검증" 주장**이다(verification-claim-integrity.md §1.1 surface 2/3에 해당하는 패턴). — Severity: major — Class: blocking — 수정: `TestOverlapIndependentOfCellStructuring`에 `inspect.getsource` 기반의 `scene_memos` 부재 단언을 실제로 추가하거나, (l)의 검증 수단 문구를 지금 존재하는 테스트(`test_overlap_rejection_reads_group_name_only_not_cue_content`, 192-217행 — 이것도 `scene_memos`를 직접 언급하진 않으므로 부분적으로만 대응)로 정정한다.

D3. **AC-LDBEAT-016(m)의 Then 절 일부가 인용된 테스트 밖에서만 검증됨** — `acceptance.md:36` (m)의 Then: "가짜 곡은 그 데이터를 그대로 ... 돌려주고, **미등록 곡은 빈 트랙+"이 곡의 기본값 없음" 안내를 돌려주며**, `find_overlapping_group_tracks` 소스에 리그 전용 리터럴 0건이다" — 검증 수단 칸은 이 전체를 `TestLoaderIsRigAndSongAgnostic`(`server/tests/test_beat_grid_t537.py:277-330`) 하나로 귀속한다. 그런데 그 클래스의 테스트 둘(`test_a_different_songs_registered_data_comes_back_unchanged_by_any_love_attack_logic`·`test_find_overlapping_group_tracks_has_no_song_specific_branch`) 중 "미등록 곡 → 빈 트랙 + 안내" 절을 검증하는 것은 **없다** — 그 동작은 `server/tests/test_beat_grid_t532.py:112,120,285`(AC-LDBEAT-007 소관, 이 개정 이전부터 존재)에서만 검증된다. 동작 자체는 실제로 성립하지만(코드 확인: `beat_grid.py:355-359` `_load_song_default_document`가 `None`이면 `tracks=[]`·`note=_NO_DEFAULT_NOTE`), AC(m)이 자기 완결적으로 인용한 검증 수단은 그 절을 커버하지 못한다. — Severity: major — Class: blocking — 수정: (m)의 검증 수단에 `test_beat_grid_t532.py:112,120,285`를 명시적으로 추가 인용하거나, `TestLoaderIsRigAndSongAgnostic`에 미등록 곡 케이스를 자체 테스트로 복제한다.

D4. **AC-LDBEAT-016(k)의 "기계" 검증이 실제로는 수작업 텍스트 대조이고, REQ-006(iv-2)의 "세 조건" 규칙 자체가 코드로 강제되지 않음** — `acceptance.md:36` (k)의 검증 수단: "기계 — `beat_grid_data/love_attack.yaml`의 세 조건 전수 재검토 주석과 여섯 메모의 사유가 1:1 대응하는지 대조" — 이것은 pytest가 단언할 수 있는 바이너리 조건이 아니라 사람이 YAML 주석(산문)과 메모 사유(산문)를 읽고 대응을 판단하는 절차다. 실제로 `server/design/beat_grid.py` 전체를 재확인한 결과 "그룹 직접 지칭 AND 그룹 번호 확인 AND 기존 큐와 충돌 없음 → 트랙, 아니면 메모"를 계산하는 함수가 **없다** — `_build_track_from_data`/`_build_scene_memo_from_data`는 YAML의 `tracks`/`scene_memos` 섹션을 그대로 옮기기만 한다(244·295·308행). 즉 REQ-LDBEAT-006(iv-2)의 "세 조건" 규칙은 LOVE ATTACK 한 곡에 대해서만 `love_attack.yaml` 작성 시점에 사람이 수동으로 정확히 지켰는지 재검토한 것이고, 다음 곡 추가 시 이 규칙을 지키도록 강제하는 코드는 전혀 없다 — `TestSceneMemos.test_all_six_scene_values_become_memos`(153행)도 "여섯 값 전부가 메모가 된다"는 LOVE ATTACK 1곡의 golden-value만 단언할 뿐, 세 조건의 일반 로직을 파라미터화해 검증하지 않는다. — Severity: minor — Class: blocking(Testability 기준 위반, "기계" 오표기) — 수정: (k)의 검증 수단 표기를 "기계"에서 "수동 검토(사람이 YAML 주석과 메모 사유 대조)"로 정정하거나, 세 조건을 입력으로 받아 트랙/메모 배정을 계산하는 순수 함수를 신설해 파라미터화 테스트를 추가한다.

D5. **(optional, cosmetic)** `server/design/beat_grid_data/love_attack.yaml:107-108`의 주석 "나머지 셋(11~13·18~21·22~25)은 칸 자체가 그룹 이름을 부르지 않는다"가 bar 14(14~17행)를 빠뜨렸다 — 실제로 bar 14의 SCENE 텍스트("워시 25% 덜어냄")도 확인된 트랙 그룹 이름을 직접 부르지 않으므로 같은 분류에 속하고, `acceptance.md:36` AC(k)의 서술은 이미 "11/14/18/22(그룹 미지칭)"로 네 개를 올바르게 묶었다 — YAML 주석 쪽만 "나머지 셋"으로 하나 빠져 있다. — Severity: minor — Class: optional — 수정: YAML 주석을 "나머지 넷(11~13·14~17·18~21·22~25)"으로 교정.

D6. **(optional, cosmetic)** `.moai/specs/SPEC-LDBEAT-001/progress.md`의 이번 개정 후기 항목이 YAML 규칙을 "두 조건 전수 재검토 주석"으로 지칭하는 반면, `spec.md:101` REQ-LDBEAT-006(iv-2)는 같은 규칙을 "세 조건"(그룹 직접 지칭·그룹 번호 확인됨·기존 큐와 충돌 없음)으로 정의한다 — 실질은 같다(이름+확인 두 조건에 충돌-없음을 별도 오버라이드로 얹은 것 = 세 조건의 AND), 용어만 어긋난다. — Severity: minor — Class: optional — 수정: progress.md 문구를 "세 조건"으로 통일하거나 "두 조건 + 충돌 오버라이드 = 세 조건과 동치"임을 한 줄로 명시.

### 체크리스트 항목별 결론 (프롬프트 지정 검사)

- **GEARS 형식(굵은 트리거, 서브-레터당 단언 1개)**: (iv-1)~(v-2) 전수 PASS — MP-2 재확인란 참조. 일부 서브레터(iv-1, v-1)가 한 문장에 두 단언을 묶지만 이는 iteration 1/2가 이미 받아들인 이 SPEC의 기존 스타일(예: (i-5))과 같은 패턴이라 신규 결함으로 잡지 않음(optional 수준).
- **신설 REQ 서브-절마다 실제로 그것을 검증하는 AC 서브-시나리오가 있는가**: iv-1(부분적으로 i+j)·iv-2(k, 단 D4)·iv-4(l, 단 D2)·v-1/v-2(m, 단 D3) 는 있으나 **iv-3은 없음(D1)**.
- **인용된 코드 줄번호가 존재하고 주장한 내용과 일치하는가**: `server/design/beat_grid.py:123,138,169,186,244,295,308,316,328`·`ui/src/protocol.ts:442,470` **전수 PASS**(직접 Read로 재확인, 전부 정확히 일치) — 이 부분은 매우 정밀하게 작성됨.
- **기존 REQ/AC(REQ-004(h), REQ-015(f), AC-016(e)~(h))와의 모순**: 없음 — (iv-4)는 REQ-004(h)와 같은 두 함수를 다른 독립성 축(칸 구조화 vs scene_memos)으로 재확인할 뿐 모순되지 않는다.
- **AC(m)의 "소스 리터럴 없음" grep의 유효성**: **유효한 검사다(vacuous 아님)** — `find_overlapping_group_tracks`(`beat_grid.py:186-223`)는 실제로 접두사 분리 규칙만 쓰는 순수 일반 코드이고, 리그 전용 분기를 추가하면 이 그렙이 즉시 깨진다(회귀 방지 효과 있음). 단, 문자열을 쪼개 이어붙이는 식으로 쉽게 우회 가능한 신택틱 검사라는 한계는 있다(기존 AC-LDBEAT-005 패턴과 같은 수준의 한계이므로 신규 결함으로는 잡지 않음).

### Verdict (Iteration 3)

**FAIL** — Overall Score(이 개정분): **0.60**. Must-Pass 7개 전부 PASS/N/A이지만, Traceability·Testability가 0.50으로 Tier M 임계에 크게 못 미친다. D1(blocking)은 REQ 서브-절 하나가 완전히 미추적이고, D2·D3(blocking)은 AC가 인용한 "기계" 검증 수단이 실제로는 존재하지 않거나 다른 파일에만 부분적으로 존재하는 **관측되지 않은 검증 주장**이다 — `verification-claim-integrity.md`의 "an actor MUST NOT assert a verification ... it did not actually verify" 원칙에 정면으로 걸리는 패턴이다. D4(blocking, minor severity)는 "기계" 라벨이 붙은 수작업 검토다.

### Regression Check — iteration 2 결함(D1~D9, N1·N2)

iteration 2에서 PASS 처리된 D1~D9 범위(spec.md (i)~(iii)/(a)~(h) 본문)는 이번 diff가 **건드리지 않았다**(git diff 확인, 해당 라인 변경 없음) — RESOLVED 상태 불변, 재발 없음. N1·N2(iteration 2의 optional 잔여)도 이번 diff 범위 밖이라 불변.

### Recommendation (Iteration 3)

1. (최우선, D1) `acceptance.md`의 AC-LDBEAT-016(i) 또는 별도 §A 보충 체크리스트에 REQ-LDBEAT-006(iv-3)의 UI 표시 요구(배지+원문 텍스트+source_ref 동시 노출)를 검증하는 Given/Then/검증수단을 추가하고, `ui/src/components/BeatGrid.test.tsx`에 RTL 렌더링 테스트를 추가한다.
2. (D2) `AC-LDBEAT-016(l)`이 인용하는 `inspect.getsource` 기반 `scene_memos` 부재 테스트를 `server/tests/test_beat_grid_t537.py`에 실제로 추가하거나, 검증 수단 문구를 지금 존재하는 테스트로 정정한다.
3. (D3) `AC-LDBEAT-016(m)`의 검증 수단에 `test_beat_grid_t532.py`의 기존 테스트를 명시적으로 추가 인용하거나, `TestLoaderIsRigAndSongAgnostic`에 미등록 곡 케이스를 자체 복제한다.
4. (D4) `AC-LDBEAT-016(k)`의 "기계" 표기를 정정하거나, 세 조건 배정 로직을 파라미터화 가능한 순수 함수로 추출해 실제 기계 테스트를 추가한다.
5. (D5·D6, optional) YAML 주석의 "나머지 셋" 누락과 progress.md의 "두 조건"/spec.md의 "세 조건" 용어 불일치를 다음 편집 때 정리한다.

재감사는 위 D1~D4(blocking) 해소분에 한정된 delta 스코프로 충분하다(기존 (i)~(iii)/(a)~(h)는 재검토 불필요).
