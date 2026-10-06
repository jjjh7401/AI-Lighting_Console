# 커밋 단독 감사: SPEC-LDRHYTHM-001 plan-doc 수정 (HEAD `aceb9b07`, base `6d2e87f6`)

Reasoning context ignored per M1 Context Isolation — 오케스트레이터가 전달한 "의도된 변경" 서술은 검증 대상 항목 목록으로만 취급했고, 그 서술의 근거 설명은 신뢰하지 않고 모두 파일을 직접 읽어 재확인했다.

**Verdict: PASS** (이 커밋의 변경 범위에 한정)
**Overall Score: 0.95** (근거는 아래 Category Scores)

---

## 범위 고지

이 보고서는 통상의 반복(iteration) plan-audit가 아니라 **한 커밋의 plan-doc 수정**을 검증하는 단발 감사다. `.moai/specs/SPEC-LDRHYTHM-001/` 디렉터리 전체의 역대 모든 결함을 새로 캐는 전면 재감사가 아니라, (a) 지시된 4개 항목이 네 파일에 일관되게 들어갔는지, (b) 이 커밋이 다른 REQ/AC와 충돌을 만들지 않았는지, (c) AC-LDRHYTHM-005가 `m1-love-attack-script.md` 대비 기계적으로 셀 수 있는지, (d) t514/t515 인용이 정확한지를 검증한다. 과정에서 **이 커밋과 무관한 사전 결함 1건**(REQ-LDRHYTHM-012의 GEARS `shall` 누락)을 발견했고, Defects Found에 기록했지만 — 이 커밋이 만든 것이 아니고 과거 3회 감사(iter2 PASS 0.92, t508 정정감사 PASS 0.96)를 이미 통과한 상태라 이 커밋의 PASS 판정을 무효화하지 않는다(§ Defects Found D1 참조, Class: optional).

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 연속성**: `grep -oE "REQ-LDRHYTHM-[0-9]+" spec.md \| sort -u` → REQ-LDRHYTHM-001~012, 12개, 빠짐·중복 없음, zero-padding 3자리 일관. `AC-LDRHYTHM-[0-9]+` → AC-001~012, 12개, 동일하게 연속.
- **[PASS] MP-2 GEARS 형식 준수** (요구사항 계층 — `spec.md`의 REQ-XXX에만 적용, AC-XXX는 Group 4에서 별도 채점): 이 커밋이 수정한 REQ-LDRHYTHM-005(`spec.md:83`)는 "**The** 대본(M1)·시연(M2)·규칙화(M3) **shall** 연출을 두 층으로 나눠 기술한다..." — Ubiquitous 패턴 유지, 수정 전후 모두 준수. 다른 REQ(001~011)도 `**The**`/`**When**`/`**While**` + `**shall**`/`**shall not**` 패턴을 유지한다. **단, REQ-LDRHYTHM-012(`spec.md:107`, 이 커밋이 건드리지 않은 행)에 "shall" 키워드가 없다** — `awk`로 그 행만 추출해 `grep -o shall`을 돌리면 매치 0건. 이는 Defects Found D1로 기록하되, 이 커밋의 diff 밖(사전 존재, iteration 1 D2 이후 미해소로 추정)이므로 이 커밋 자체의 MP-2 판정에는 영향을 주지 않는다.
- **[PASS] MP-3 YAML Frontmatter 유효성**: `spec.md` 1~16행 — 12개 canonical 필드(`id`/`title`/`version`/`status`/`created`/`updated`/`author`/`priority`/`phase`/`module`/`lifecycle`/`tags`) 전부 존재, 타입 정확(`version`/`created`/`updated` 인용된 문자열, `priority: P1` 유효 enum, `status: in-progress` 유효 enum). 금지된 snake_case 별칭(`created_at`/`updated_at`/`labels`/`spec_id`) 없음. 이 커밋은 frontmatter를 건드리지 않았다(`git diff` 확인) — `status`는 전이 없이 `in-progress` 그대로.
- **[N/A] MP-4 Section 22 언어 중립성**: 단일 도메인(grandMA3 조명 콘솔 연출) SPEC — 다국어 도구 열거 대상이 아니므로 N/A, 자동 PASS.
- **[PASS] MP-5 D7 교차-SPEC 정합**: `related_specs`/본문에서 추출한 SPEC-ID 4건(SPEC-COPILOT-FXGEN-001, SPEC-COPILOT-FXLIB-001, SPEC-LDDESIGN-001, SPEC-LDRENDER-001) 전부 `.moai/specs/<ID>/spec.md` 존재 확인, `status:` 각각 `completed`/`completed`/`completed`/`implemented` — `retired`/`superseded`/`archived` 없음 → BLOCKING 없음.
- **[N/A] MP-6 D8 플랫폼 교차 규율**: `grep -c syscall spec.md plan.md acceptance.md progress.md m1-love-attack-script.md` → 전부 0. `syscall` 미언급이므로 자동 PASS(§D8-4).
- **[N/A] MP-7 `[NEEDS CLARIFICATION]` 게이트**: `research.md` 없음(Tier M, 정상), `plan.md`에 `grep -rn '\[NEEDS CLARIFICATION'` → 매치 0.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 1.0 | 1.0 — 모든 요구사항이 단일 해석만 허용 | REQ-005/AC-005/plan.md M1 §E 세 곳 모두 동일한 "네 범주" 어휘와 동일한 괄호 설명("무빙 Pan/Tilt 페이저 — 지금 위치를 중심으로 스피드 마스터 박 주기에 맞춰 계속 움직임")을 글자 그대로 공유한다(`spec.md:83`, `acceptance.md:42`, `plan.md:58`) — 세 문서 사이에 해석 차이가 생길 여지가 없다 |
| Completeness | 1.0 | 1.0 — 모든 필수 섹션 존재 + Out of Scope H3 5건 | `spec.md`에 HISTORY/§0/§1(WHY)/§2(WHAT)/§3(REQUIREMENTS)/§4(Out of Scope, H3 5개: `### Out of Scope — M4+ 앱 구현 자체` 등)/§5 모두 존재. `acceptance.md`에 AC 12개 + Definition of Done |
| Testability | 1.0 | 1.0 — 모든 AC가 이항 판정 가능, 위즐워드 없음 | AC-LDRHYTHM-005의 측정 문구가 이 커밋에서 "오프라인 검사(... 네 범주 밖 행이 0건이어야 PASS)"로 명문화됐다(`acceptance.md:44`) — 실측(아래 참조)으로 0건 확인. "적절히"/"적당히" 류 위즐워드 없음 |
| Traceability | 1.0 | 1.0 — 모든 REQ가 AC로, 모든 AC가 존재하는 REQ로 | REQ-005 ↔ AC-005, REQ-006/007 ↔ AC-006, REQ-001 ↔ AC-001/002/012 등 12개 REQ 전부 최소 1개 AC로 추적됨(이 커밋이 이 매핑을 깨지 않았음을 `acceptance.md` 헤더의 `[REQ-LDRHYTHM-XXX]` 태그로 확인) |

## 실측 — AC-LDRHYTHM-005 기계적 검증 (요청된 핵심 항목)

`m1-love-attack-script.md` §3 대본 표(61행: 박자 57 · 강조 4)를 파싱해 "연출" 열을 네 범주 접두사로 분류했다(스크립트: `/tmp/count_m1.py`, 실행 결과 아래 그대로 인용):

```
layer_counts {'박자': 57, '강조': 4, 'other': 0}
킥/스네어 펄스 20
체이스 한 칸 8
색/위치 한 단계 21
움직임 효과 8
sum 57
moment_values {'기타': 57, '코러스진입': 2, '드롭': 1, '마지막코러스': 1}
unclassified 0
```

**범주별 행 수**(연출 열 접두사 분류, 행 단위): 킥/스네어 펄스 20행 · 체이스 한 칸 8행 · 색/위치 한 단계 21행 · 움직임 효과 8행 — 합 57행, **네 범주 밖 행 0건**. AC-LDRHYTHM-005의 Then 절("모든 박자 층 항목이 이 네 범주 중 하나에 속하고, 범주 밖의 자유 서술은 없다")은 행 단위 분류 기준으로 **PASS**.

이 행-수(20/8/21/8=57)는 대본 §4 "세는 방법" 표의 **이벤트-수**(펄스 173·체이스 120·색/위치 23·움직임 효과 8, 합 324)와 다르다 — 이유는 대본 §4 자체가 밝힌 바와 같이, 펄스/체이스/색위치는 시각 열의 반복 횟수("24회" 등)를 곱해 이벤트 수를 세지만 움직임 효과는 "효과가 시작되는 지점(행 하나 = 1)"으로만 센다(§3 대본 §4, `acceptance.md:44`의 새 문장과 일치). 두 수는 서로 다른 질문(분류 가능성 vs 이벤트 총량)에 답하는 것이라 모순이 아니다.

AC-LDRHYTHM-006(강조 층 검사)도 함께 실측했다:
```
$ grep -c "§10 금지목록 4번" m1-love-attack-script.md → 5  (양성, ≥1 충족)
$ grep -c "§10\.3" m1-love-attack-script.md → 0            (음성, 0 충족)
```
강조 4행의 모멘트유형 분포(코러스진입 2·드롭 1·마지막코러스 1)는 닫힌 어휘 {코러스진입, 드롭, 마지막코러스} 안에 전원 포함 — 위반 0건. **AC-LDRHYTHM-006 PASS.** 두 수치(`cite_10_4 5`, `misquote 0`)는 t514 판정서 §3이 보고한 `count_script.py` 출력과 정확히 일치한다.

## 지시된 4개 항목 — 파일별 교차 확인

**1) 박자 층 종류 3→4 (움직임 효과 추가)**
- `spec.md` REQ-LDRHYTHM-005(:83) — shall-텍스트 자체에 "**움직임 효과**(무빙 Pan/Tilt 페이저 — ...)" 반영됨 + `[범주 확장 정정 2026-10-06(t517) — 아래 블록쿼트 참조]` 꼬리표. 직후(:87) 블록쿼트에 원래 문면(2026-10-05) 전문이 「」로 인용 보존, 근거 `.moai/reports/t514/verdict.md §4` 명기.
- `acceptance.md` AC-LDRHYTHM-005(:37-44) — Then 절이 "네 범주"로 바뀌었고, 바로 위 블록쿼트에 "범주 확장 정정(2026-10-06, 카드 t517, 근거 t514 §4)" + 원래 Given-When-Then 문면 전문 보존.
- `plan.md` M1 §E(:58-60) — 박자 층 종류 나열에 "움직임 효과" 추가 + 그 아래 2줄 블록쿼트로 원래 문면(2026-10-05)과 정정 메모(2026-10-06, t517) 보존.
- 세 곳 모두 날짜·카드ID·근거 보고서를 명시한 교정 메모 형식을 일관되게 사용 — **PASS**.

**2) progress.md — 감독 M1 승인 기록**
- `progress.md` "### M1 감독 승인 (t517, 2026-10-06)" 섹션에 원문 「통과로 진행」, 승인 대상(`m1-love-attack-script.md`, t514 수정본), PR #557 머지 `6d2e87f6` 전부 기록됨. `spec.md` frontmatter `status: in-progress` 불변 확인(`grep '^status:' spec.md` → `in-progress`) — **PASS**.

**3) plan.md M2 — t515 결론 반영**
- `plan.md` M2 §E에 "반복되는 동작(킥/스네어 펄스·체이스 한 칸·움직임 효과)은 스피드 마스터에 묶은 페이저로 돌리고 ... 장면 경계(색/위치 한 단계)와 강조(BLIND/STROBE)는 타임코드 이벤트로 낸다. **반 박(0.267초) 간격 동작은 타임코드 이벤트로 낼 수 없다**" — t515 판정서 §3("빠른 동작은 ... 페이저여야 한다")과 축어적으로 일치.
- "첫 묶음 순서(t515 §5)": 묶음 0(0~6마디, 다섯 가지 미측정 항목, 카드 t516 **진행 중·보고서 미작성**) → 묶음 1(0~25마디) — t515 판정서 §1 ⑤·§5와 일치, "진행 중" 상태도 정확히 반영(과장 없음).
- **PASS**.

**4) plan.md §D — 감독 작명 규칙**
- `plan.md` §D에 `'<곡명> - <버전>'` 규칙, 예시 `'LOVE ATTACK - M2a'`, "승인 파일에는 ... `Set Timecode/Sequence … Property 'Name' '<곡명> - <버전>'` 줄이 반드시 포함돼야 한다 — 이름 줄이 없는 승인 파일은 AC-LDRHYTHM-012 의 승인 대상에서 제외한다" — t515 판정서 §1 ⑤ "승인 파일 예시" 단락과 일치. **PASS**.

## 추가로 판단 요청받은 항목 — AC-005의 "행 하나 = 1" 문장 (t514 §4 밖의 추가)

`acceptance.md` AC-LDRHYTHM-005의 새 Then 절 끝에 "'움직임 효과'는 계속 도는 페이저라 바퀴 수가 아니라 효과가 시작되는 지점(행 하나 = 1)으로 센다"가 추가됐다. t514 판정서 §4의 "정정안(제안만)" 글머리 목록에는 이 문장이 없다 — §4는 "세 범주"→"네 범주" 명칭 교정만 제안했다.

**판단**: 날조가 아니다. 이 문장은 (a) `m1-love-attack-script.md` §4 "세는 방법" 표 자체("움직임 효과 | 8 | 효과가 시작되는 지점(행 하나 = 1)으로 센다")와 글자 그대로 동일하고, (b) t514 판정서 §3이 보고한 `count_script.py` 출력("events {... '움직임 효과': 8}")의 실제 집계 방식과 일치한다 — 즉 t514 §4의 제안 목록 밖이지만 t514 전체 보고서 본문(§0/§3/스크립트 산출물)에서 근거를 찾을 수 있는, 사실에 기반한 보강이다. 날조된 요구사항이 아니라 **기존에 이미 쓰이던 집계 규칙을 AC 쪽에도 명문화한 것**으로 판단한다.

다만 지적할 점: acceptance.md 블록쿼트의 출처 표기("근거 `.moai/reports/t514/verdict.md §4`")는 이 추가 문장의 실제 출처(§0/§3, 스크립트 본문)가 아니라 범주-명칭 교정의 출처만 가리킨다 — 인용 정밀도가 살짝 거칠다. 사실관계 오류는 아니며 PASS/FAIL에 영향 없음. **Severity: minor, Class: optional**(§6 참조).

## 다른 REQ/AC와의 충돌 검사

- **REQ-007**(박자 층·강조 층 시각 구분, "박자 동기 무빙") — 이번 교정이 "박자 동기 무빙"을 네 번째 범주로 흡수해도 충돌하지 않는다는 점이 spec.md:87 블록쿼트 끝줄에 명시적으로 다뤄져 있다("REQ-LDRHYTHM-007의 "박자 동기 무빙"은 이미 움직임을 박자 층으로 보고 있어 이 교정과 충돌하지 않는다") — 충돌 없음, 명시적으로 해소됨.
- **AC-003**(6칸 표, 층/모멘트유형 닫힌 어휘) — "연출" 열의 내용(어떤 범주인지)을 제약하지 않으므로 이번 범주 확장과 간섭 없음. 실측상 층 열 분포(박자 57·강조 4·other 0)도 AC-003 요건과 그대로 부합.
- **AC-006**(강조 층 배치) — 박자 층 범주 확장은 강조 층 쪽 규칙(REQ-006)에 손대지 않았고, 실측으로도 위반 0건 확인(위 참조).
- **M2 AC들**(AC-008 스피드마스터, AC-012 승인=송신) — plan.md M2 §E의 새 구현방식 서술은 REQ-009/010과 상충하지 않는다(여전히 스피드마스터 결속, 오디오 입력 미사용). §D의 작명-줄 요구는 AC-012의 측정 절차 자체(sha256 비교)를 변경하지 않고, "승인 대상에서 제외"라는 추가 입장(入場) 조건만 얹었다 — AC-012 본문과 모순되지 않는다.
- **D7/D8** — 위 Must-Pass 참조, 문제 없음.

## Defects Found (structured defect-list)

D1. FrontmatterFormat — `spec.md:107` (REQ-LDRHYTHM-012) — "The 다음 항목은 ... 범위 후보로만 기록된다"에 GEARS 필수어 `shall`이 없다(Ubiquitous/When/While/Where/Unwanted 다섯 패턴 중 어디에도 해당하지 않는 평서문) — Severity: major — Class: optional (이 커밋의 diff 밖, 2026-10-05 iteration 1 D2에서 이미 "shall-주체 분리" 처리가 있었으나 그 결과 `shall` 자체가 사라진 것으로 보임, 이후 3회 감사에서 미포착) — Required fix: REQ-LDRHYTHM-012를 "**The** 다음 항목 **shall** M4+(앱 구현) 단계의 범위 후보로만 기록된다" 형태로 `shall`을 복원하거나, HISTORY에 왜 이 REQ가 비요구사항적 기록용 REQ로 의도적으로 예외인지 명시한다. 별도 카드로 처리 권장 — 이 커밋의 PASS 판정을 뒤집지 않는다.

D2. CitationPrecision — `acceptance.md:38` (AC-LDRHYTHM-005 블록쿼트) — "움직임 효과는 ... 행 하나 = 1로 센다" 문장의 출처가 블록쿼트 머리의 "근거 t514 §4"로 뭉뚱그려 표기돼 있으나, 실제 근거는 t514 §4(범주-명칭 정정안)가 아니라 t514 §0/§3와 `m1-love-attack-script.md` §4의 집계 규칙이다 — Severity: minor — Class: optional — Required fix: 블록쿼트 인용을 "근거 `.moai/reports/t514/verdict.md` §4(범주 명칭) + 대본 §4(집계 규칙)"로 분리 표기.

No other defects found in the scope of this commit.

## Recommendation

PASS. 네 가지 지시 항목이 네 파일(spec.md/acceptance.md/plan.md/progress.md)에 일관되고 정확하게 반영됐고, 원문 보존 + 날짜 있는 정정 메모 요건을 모두 충족했다. AC-LDRHYTHM-005는 대본 대비 기계적으로 0건 위반(20/8/21/8=57행, 범주 밖 0)으로 실측 확인됐다. t514/t515 인용은 두 보고서의 실제 내용과 일치한다. 이 커밋 밖의 범위(server/)는 변경되지 않았다(`git log cea25c04..HEAD -- server/` → 0건). 발견된 D1(REQ-012 `shall` 누락)은 이 커밋이 만든 결함이 아니므로 별도 카드로 분리해 처리할 것을 권고한다.
