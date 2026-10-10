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
