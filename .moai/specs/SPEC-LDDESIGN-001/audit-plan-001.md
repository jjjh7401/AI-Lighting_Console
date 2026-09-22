# SPEC Review Report: SPEC-LDDESIGN-001

> 이 파일은 반복(iteration)별 이력을 보존한다. 최신 판정이 맨 위, 과거
> iteration은 아래에 원문 그대로 남긴다.

---

## Iteration 3/3 — 2026-09-22 (현재 판정)

Verdict: **PASS**
Overall Score: **0.857** (조화평균 — Clarity 0.75 / Completeness 0.75 / Testability 1.0 / Traceability 1.0. Tier L 통과선 0.85 상회, iteration 2(0.857)와 동률 — 하락 아님, STOP 신호 미해당)

> M1 Context Isolation 준수: 배차 메시지의 추론 배경(무엇이 바뀌었는지 요약)은 "어디를 볼지"의 안내로만 쓰고, 실제 판정은 spec.md·plan.md·acceptance.md·design.md·research.md·spec-compact.md·design/spec-gap.md·design/received-design.md·design/implementation-notes.md·`src/DESIGN.md`(수령 UI 디자인 정본)를 전부 직접 새로 읽고, REQ/AC 카운트는 프로그램적으로 재계산했다. 이전 iteration의 PASS 판정도 다시 신뢰하지 않고, D-NEW1·D-NEW2(iteration 2에서 발견된 미해결 선택 사항)를 포함해 처음부터 재검증했다.

### 변경 요약 (감사 대상 파악용 — 판정 근거 아님)

REQ 86→95(9개 신설, §3.15 PLAN CUE 수정요청 생성기), AC 20→44(24개 신설), M7 대상이 "코파일럿 메인 화면"에서 "런북 모드"로 재확정(REQ-078), REQ-082(CUE SHEET 열 구성)의 "기존 12열" 전제가 "이미 14열"로 정정. 이 변경들이 실제로 올바르게 반영됐는지를 원문 대조로 확인했다(아래).

### 프로그램적 재계산 (믿지 않고 직접 계산)

- **REQ 번호**: `grep -oE 'REQ-LDDESIGN-[0-9]+' spec.md`로 전수 추출 → 유니크 95개, 1~95 연속, 갭 0, 중복 0.
- **AC 번호**: `acceptance.md`의 `## AC-LDDESIGN-NNN` 헤더 44개, 1~44 연속, 갭 0, 중복 0.
- **REQ→AC 추적성**: acceptance.md 전체 텍스트에서 `REQ-LDDESIGN-NNN`(단독·범위 `~`·쉼표 나열 축약형 모두 포함, 예: "REQ-LDDESIGN-027, 029") 정규식으로 전수 추출 → 1~95 집합과 대조 → **95/95 전량 인용, 누락 0**.
- **GEARS 마커**: 95개 REQ 행 전부가 `**The**`/`**When**`/`**While**`/`**Where**` 중 하나로 시작 (정규식 검증, 예외 0건). 95개 REQ 행 전부가 최소 1개의 `**SHALL**` 또는 `**SHALL NOT**`을 포함 (예외 0건).
- **syscall**: spec.md·plan.md·acceptance.md·design.md·research.md 전체에서 0건 → MP-6 D8 자동 PASS.
- **[NEEDS CLARIFICATION]**: plan.md·research.md·spec.md·acceptance.md·design.md·spec-compact.md·design/*.md 전체에서 0건 → MP-7 PASS.

### Must-Pass 결과

- **[PASS] MP-1 REQ 번호 연속성**: 95개 고유, 1~95, 갭·중복 0(재계산, 위 참조).
- **[PASS] MP-2 GEARS 형식 준수**: 95/95 REQ가 GEARS 마커로 시작하고 최소 1개의 SHALL/SHALL NOT을 가짐(재계산). 신규 9개(REQ-087~095)를 개별 검사 — 전부 The/When 패턴 + SHALL/SHALL NOT 보유, GEARS 위반 없음. **단, 2건의 부절(sub-clause) 스타일 결함을 확인**(D5·D7 참조, iteration 2 precedent에 따라 optional 처리 — 주절에 SHALL이 이미 있으므로 REQ 전체가 GEARS 분류를 벗어나지 않음): REQ-002(iteration 2 D-NEW1, 여전히 미수정)와 REQ-095(신규, 마지막 문장 "거절되면 스택은 그대로 남고 거절 사유가 표시된다"가 SHALL 없이 끝남 — 다만 이 내용은 REQ-091에 이미 SHALL로 규정돼 있어 실질적 정보 손실은 없음).
- **[PASS] MP-3 YAML frontmatter 유효성**: 12개 canonical 필드 전부 존재·타입 정합. `status: draft`, `priority: P1`, `phase: "Lighting Copilot v1.0 target"`(금지된 단계명 아님), `updated: 2026-09-22`(created 이후, 유효). snake_case 별칭 없음.
- **[N/A] MP-4 언어 중립성**: 단일 도메인(조명 연출), 다중 프로그래밍 언어 툴링 아님.
- **[PASS] MP-5 D7 교차-SPEC 정합**: `related_specs`/`depends_on` 6개 SPEC을 전부 재조회 — SPEC-LDRETURN-001·LDCLIMAX-001·LDACCENT-001 `status: draft`, SPEC-COPILOT-LOOKLIB-001 `status: completed`. **retired/superseded/archived 참조 0건 — BLOCKING 없음.** 참고(informational, MP-5에 영향 없음): SPEC-COPILOT-SONGSTD-001·CUETIME-001은 레거시(프론트매터 없는) 형식이라 `status:` 필드 자체가 없다 — D7 체크리스트의 D7-4(retired 등)에도 D7-5(파일 부재)에도 해당하지 않는 미모델링 경계 사례이며, 기계적 grep이 빈 값을 반환할 뿐 오류가 아니다.
- **[PASS] MP-6 D8 크로스플랫폼**: syscall 0건, 자동 PASS.
- **[PASS] MP-7 clarification gate**: 전체 산출물 grep 0건(위 참조). plan.md §F의 잠정값 3건(MIB 1.5s+0.5s·콘솔 문법 3종·`allow_strobe=false`)은 오케스트레이터 지시대로 "값이 정해지지 않은 빈칸"이 아니라 "이미 채택된 잠정값"이므로 MP-7 위반이 아니다.

### 지시받은 항목별 검증 결과

1. **REQ-087·092·094·095의 생성기 아키텍처 불변식** — `SHALL NOT` 절을 전수 확인. REQ-092가 "큐시트 타임라인 객체를 로컬에서 변형"·"`changes` 매핑을 직접 만들어... 우회"를 명시적으로 금지하고, 값 범위·거절 사유는 서버(`apply_cue_sheet_edit`)가 단일 진실 지점임을 명시(생성기는 상한·하한을 "표시만" — 판정 로직 복제 아님). REQ-094가 "승인 경로... 입력 방식과 무관하게 동일하게 적용"·"우회로를 만들지 않는다"를 명시. `spec.md` 전체에서 "콘솔에 직접"·"승인 없이"·"즉시 반영"·"자동 반영" 패턴 0건. **네 불변식 모두 위반 없음 확인**.
2. **되돌리기 라벨 충돌(REQ-095) 3상태 모델** — 선택/요청/초안 반영 3상태가 acceptance.md AC-042~044로 개별 검증됨(서버 미전송·라벨 유일성·수락 후 스택 초기화). `grep`으로 spec.md·plan.md·acceptance.md·design.md·research.md 전체에서 "되돌리기"의 다른 용례를 확인 — CUE SHEET 기존 버튼(`CueSheetTimeline.tsx:612`) 지칭 외에는 전부 "선택 취소"로 정확히 구분돼 있다. **내적 일관성 확인, 라벨 재충돌 없음**.
3. **M2 의존성 배선** — REQ-087이 "이 SPEC은 M2 완료 이후에만 착수 가능"을 명시하고, plan.md M7 절의 "M7 구현 순서 — 읽기 전용 표면 먼저, 생성기는 마지막(M2 의존)"이 생성기 관련 작업(6번, 마지막)을 읽기 전용 표면(1~5번) 뒤로 명시적으로 배치. **plan.md가 REQ-087의 순서 제약을 정확히 반영함을 확인**.
4. **범위 보류 5건(감독 결정 대기) 무단 채택 여부** — `grep`으로 "한눈에"·"탭 3"·"IBM Plex"·"자유 입력"·"항목별 제거/✕"가 REQ·AC 어디에도 등장하지 않고 두 "감독 결정 대기" 절(§3.14 말미, §3.15 말미)에만 존재함을 확인. **5건 전부 미채택 상태 유지 확인**. 단, CUE SHEET 열 제거 후보(5건 중 하나)의 프레이밍에 내적 모순 발견 — 아래 D1 참조.
5. **경고 중복 회피(REQ-093)** — REQ-093이 (3)(4)(5)를 각각 "REQ-027·REQ-090 재사용", "REQ-050 재사용, 임계값만 신규", "REQ-066 재사용"으로 명시하고, AC-040이 "별도 재계산 로직을 갖지 않는다(코드 검사)"로 이진 검증한다. **REQ-050~052·066과의 중복 정의 없음, 재사용 관계만 확인**.
6. **`src/DESIGN.md` 대조** — SPEC이 DESIGN.md와 모순되는 서술 없음(§4.5 헤더의 "그룹 기반 편집기"라는 DESIGN.md 자체 표현과 SPEC의 "생성기" 명칭 차이는 SPEC의 HISTORY가 명시적 근거와 함께 기록한 의도적 이탈이지 결함이 아니다). DESIGN.md가 요구하지만 REQ가 안 덮는 항목은 없음(§4.7 구현 세부는 REQ-085의 HOW이므로 의도적으로 implementation-notes.md에 위임, IBM Plex 폰트는 의도적으로 보류 절에 남김). **단, design.md(SPEC 산출물)가 DESIGN.md 대조표를 잘못 계산한 오류 발견 — 아래 D2 참조**.

### 새로 발견된 결함(iteration 3 도입분)

**D1 (major, blocking)** — `spec.md:284`(REQ-LDDESIGN-082) vs `spec.md:345-349`(§3.14 말미 "감독 결정 대기") — "감독 결정 대기" 절은 "CUE SHEET 기존 5열 제거 후보(TC Out·Dur·Mood·Trans·Note)"의 "기존 기능 손실인지 감독이 의도한 정리인지"가 **5개 전부** 미확인이라고 서술하지만, REQ-082의 "SHALL NOT 제거되고 유지된다" 안전 기본값은 **TC Out·Note 2개에만** 적용된다 — 나머지 3개(Dur·Mood·Trans)는 REQ-082의 "목표 14열" 목록에 애초에 없으므로 감독 확인 없이 이미 정상 제거 대상으로 확정된 상태다. SPEC 본문은 이 3개가 왜 나머지 2개와 다른 확실성 수준을 갖는지 설명하지 않는다 — "5개 전부 미확인"이라는 프레이밍과 "3개는 이미 결정됨"이라는 실제 규범 내용이 어긋난다. AC-LDDESIGN-019(`acceptance.md:224-243`)가 같은 프레이밍을 그대로 물려받는다. 필요한 조치: "감독 결정 대기" 절을 "TC Out·Note 2개만 실사용 여부 미확인(안전 기본값으로 유지), Dur·Mood·Trans 3개는 이미 제거 확정"으로 재기술하거나, 구별 근거(예: 세 열이 실사용 0건임을 실측)를 REQ-082에 추가한다.

**D2 (minor, blocking)** — `design.md:132,138` — design.md §2.3의 CUE SHEET 대조표가 "기존에 있었지만 target 14열에 없는 것 (4개): TC Out·Mood·Trans·Note"라고 명시하지만, 같은 절이 스스로 밝힌 "겹치는 개념 9개"와 대조하면 산수가 맞지 않는다(9+4=13≠14) — 실측 기존 14열에서 "Dur"가 누락됐다. spec.md REQ-082(`spec.md:284`)는 같은 사실을 "5열(TC Out·Dur·Mood·Trans·Note)"로 정확히 기술하므로, design.md와 spec.md가 같은 사실에 대해 서로 다른 개수를 주장하는 상태다. spec.md가 정본(REQ 본문)이므로 실무 영향은 제한적이나, design.md는 Tier L 필수 plan-phase 산출물이고 본 감사가 직접 인용을 요구받은 문서다. 필요한 조치: design.md:132를 "(5개): TC Out·Dur·Mood·Trans·Note"로 정정.

**D3 (minor, optional)** — `research.md:64` — "§3.14 UI가 이 흐름 위에 컨셉 패널·2열·3줄·상태줄만 추가한다"가 2026-09-22 정정(D11~D17) 이전의 낡은 전제(REQ-082 "12열+2열")를 그대로 담고 있다 — 현재는 5열 추가 + §3.15(9개 REQ, 생성기) 신설로 바뀌었다. research.md는 11편 보고서의 압축 다이제스트라 소급 갱신 의무가 약하지만, 이 한 줄은 현재 REQ-082와 직접 모순되는 구체적 숫자를 담고 있어 다음 정정 때 갱신을 권장한다.

**D4 (minor, optional)** — `design/implementation-notes.md:76`, `design/received-design.md`의 "(a)(b)행"·"(c)행"·"(d)행"·"(e)행" 인용 — 이 lettered anchor들은 현재 `design/spec-gap.md`(숫자 항목 1~7, 레터 없음)에 존재하지 않는다 — 참조가 끊어져 있다. 또한 implementation-notes.md:76은 "기존 헤드룸 경고 4종(REQ-051)과의 중복 여부는 확인되지 않았다"고 적지만, spec.md REQ-093(`spec.md:325`)은 이미 그 중복 여부를 명시적으로 해소했다(REQ-050 재사용, 임계값만 신규) — implementation-notes.md가 spec.md의 최종 정정을 반영하지 못한 낡은 상태다. 이 세 파일은 Tier L SSOT 5종에 속하지 않는 작업 노트(spec.md 반영을 위한 입력 문서)이므로 채점에는 반영하지 않되, 위생 차원에서 기록한다.

**D5 (carried from iteration 2, minor, optional, 미해결)** — `spec.md:145`(REQ-LDDESIGN-002) — iteration 2의 D-NEW1이 그대로 남아 있다: "M0은 그 SPEC의 완료를 대기하거나... 명시적 override로만 진행한다"에 SHALL이 없다. 주절(bpm=density_bpm 전달)에는 SHALL이 있어 MP-2 위반은 아니다. 선택 조치 미적용 상태.

**D6 (carried from iteration 2, minor, optional, 미해결)** — `acceptance.md:402`(AC-LDDESIGN-031) — iteration 2의 D-NEW2가 그대로 남아 있다: REQ-026·028·032·033·034·035(6개)가 한 AC로 압축돼 있다. 선택 조치(run-phase 개별 assert 분리) 미적용 상태.

**D7 (new, minor, optional)** — `spec.md:326`(REQ-LDDESIGN-095 마지막 문장) — "거절되면 스택은 그대로 남고 거절 사유(REQ-092)가 표시된다."에 SHALL/SHALL NOT이 전혀 없다(D5의 REQ-002 사례보다 더 완전히 비어 있다 — 그쪽은 같은 절에 SHALL이 공존, 이쪽은 이 문장 자체가 독립적으로 비어 있다). 다만 같은 내용(거절 사유의 diff 줄 노출)이 REQ-091에 이미 SHALL로 규정돼 있어 실질적 규범 공백은 아니다 — 순수 표현 결함. 필요한 조치(선택): "**When** 코파일럿이 요청을 거절하면, 스택은 **SHALL** 그대로 남고 거절 사유가 표시된다"로 재기술하거나 REQ-091 인용으로 대체.

**D8 (new, minor, optional)** — `acceptance.md:522-533`(AC-LDDESIGN-040) — "리저브 위반" 경고 재사용 근거를 REQ-LDDESIGN-027만 인용하고 REQ-LDDESIGN-090(BLIND 잠금)은 누락했다 — spec.md REQ-093(`spec.md:325`)은 이 조건의 재사용 근거로 REQ-027과 REQ-090 둘 다 명시한다. AC-037이 REQ-090을 별도로 검증하므로 추적성 공백의 실무 영향은 작다.

### 카테고리 점수 (재계산)

| 차원 | 점수 | 루브릭 밴드 | 근거 |
|---|---|---|---|
| Clarity | 0.75 | 0.75 (한두 개 REQ에서 해석에 따라 다르게 구현될 여지) | D1(CUE SHEET 5열 제거 후보 프레이밍 불일치)이 한 REQ군(REQ-082)에 국한된 모호성. D5·D7(SHALL 누락 부절)은 주절/타 REQ가 이미 규범을 담고 있어 정보 손실은 없음. |
| Completeness | 0.75 | 0.75 (비핵심 섹션 하나가 약함) | 전 섹션·frontmatter 12필드 정상. Tier L 필수 산출물인 design.md의 CUE SHEET 대조표(§2.3)가 자체 산수 오류(D2, 9+4≠14)로 spec.md와 어긋남 — "비핵심(요약) 섹션의 부정확"으로 분류. |
| Testability | 1.0 | 1.0 (모든 AC가 이진 판정 가능) | 약어("적절히" 등) 0건. AC-019가 열 개수 초과 예외("FAIL 아님")까지 명시적으로 이진화해 둠. 44개 AC 전부 Given-When-Then + 구체적 수치/문자열. |
| Traceability | 1.0 | 1.0 (모든 REQ가 AC를 가짐, 고아 AC 없음) | 95/95 REQ 전량 acceptance.md에 인용(프로그램적 재계산, 누락 0). 44개 AC 전부 존재하는 REQ를 인용. |

조화평균 = 4 / (1/0.75 + 1/0.75 + 1/1.0 + 1/1.0) = 4/4.667 ≈ **0.857** → Tier L 통과선(0.85) 상회, iteration 2(0.857)와 동률 — **하락 아님, STOP 신호 미해당**.

### 회귀 확인 (iteration 2 → 3)

| # | iteration 2 결함 | 상태 |
|---|---|---|
| D-NEW1 (REQ-002 SHALL 누락) | UNRESOLVED — `spec.md:145` 문구 변동 없음. 선택 조치이므로 PASS 판정에 영향 없음. |
| D-NEW2 (AC-031 6-REQ 압축) | UNRESOLVED — `acceptance.md:402` 구조 변동 없음. 선택 조치이므로 PASS 판정에 영향 없음. |

두 항목 모두 3회 연속 등장은 아니다(iteration 1에는 존재하지 않았고 iteration 2에서 처음 발견됨 — 정체(stagnation) 기준인 "3회 연속 동일 결함"에는 해당하지 않는다). iteration 2→3 사이 SPEC 본문이 M7 전면 정정 + §3.15 9개 REQ 신설이라는 실질적 확장을 거쳤음에도 두 항목이 우연히 손대지 않은 영역이라 남아 있을 뿐이며, 의도적 회피 정황은 없다.

### 권고

1. (권장, D1) §3.14 말미 "감독 결정 대기" 절의 CUE SHEET 5열 항목을 "TC Out·Note만 미확인, Dur·Mood·Trans는 이미 제거 확정"으로 재기술한다.
2. (권장, D2) `design.md:132`의 "(4개)"를 "(5개): TC Out·Dur·Mood·Trans·Note"로 정정한다.
3. (선택, D3·D4) research.md·design/implementation-notes.md의 2026-09-22 이전 낡은 서술(REQ-082 "2열" 전제, REQ-093 미해소 표기)을 갱신하고, design/received-design.md의 끊어진 "(a)~(e)행" 인용을 spec-gap.md의 실제 항목 번호로 교체한다.
4. (선택, D5·D7) REQ-002·REQ-095의 SHALL 누락 부절을 정리한다.
5. (선택, D6·D8) AC-031을 run-phase 개별 assert로 분리하고, AC-040에 REQ-090 인용을 추가한다.
6. 그 외 필수 조치 없음 — PASS 판정으로 Implementation Kickoff Approval 단계로 진행 가능(§2.4 예외 아래 있으므로 M0~M8을 `moai todo` 카드로 분할해 배차할 것 — 특히 신설 §3.15의 M2 의존 순서를 plan.md M7 구현 순서 6번 그대로 지킬 것).

🗿 MoAI

---

## Iteration 2/3 — 2026-09-21 (과거 판정, 원문 보존)

Verdict: **PASS**
Overall Score: **0.86** (조화평균 — Clarity 0.75 / Completeness 1.0 / Testability 0.75 / Traceability 1.0. Tier L 통과선 0.85를 근소하게 상회)

> M1 Context Isolation 준수: 조정자(coordinator) 메시지의 추론 배경은 참고만 하고, spec.md·plan.md·acceptance.md·design.md·research.md·spec-compact.md 6개 파일(design.md 신설로 Tier L 5종 + 추가 요약)을 새로 읽어 직접 재검증했다. 특히 "10건 전부 반영됐다"는 조정자 주장은 **믿지 않고** 매 항목을 파일 재독·grep·프로그램적 재계산으로 재확인했다.

### 이사회 승인 사항(Director-authorized) 검증 결과

- **Defect 1 (MP-7 clarification gate) — 해소 확인됨.** `grep -rn '\[NEEDS CLARIFICATION' spec.md plan.md acceptance.md design.md research.md spec-compact.md` → **0건**(이 audit-plan-001.md 자신의 과거 iteration-1 인용만 예외로 존재, 지시대로 정당). plan.md §F가 "잠정값 — M8 콘솔 프로브로 확정"으로 3건을 명시값(MIB 1.5s+0.5s · 콘솔 문법 3종은 M8 전까지 주석/메타로만 출력 · `allow_strobe` 기본 `false`)으로 전환했고, spec.md §5·acceptance.md AC-022~024가 Implementation Kickoff Approval 재확인 + M8 프로브 확정 경로를 일관되게 명시한다. **MP-7 = PASS**로 재판정.
- **Defect 2 (Tier-L REQ 예산 85 vs 25) — 해소 확인됨(실측 재계산).** spec.md §2.4가 감독 지시("지금까지 모든 내용을 정리해서 포함시키고 스펙문서로")를 인용해 예외를 명문화했다. "M0~M8 마일스톤이 sub-SPEC 역할을 하도록 REQ 범위가 서로 배타적"이라는 주장을 **믿지 않고** spec.md 각 §3.N 절 헤더의 REQ 범위를 직접 대조·합산했다: M0=001~004(4) · M1=005~016(12) · M2=017~025(9) · M3=026~035(10) · M4=036~052(17) · M5=053~072(20) · M6=073~077(5) · M7=078~085(8). 합계 4+12+9+10+17+20+5+8=**85**, 경계 겹침 0, 빈틈 0 — **주장이 실제로 참**임을 확인. Tier 예외는 문서화됐고 구조적으로 정합하다.

### 나머지 iteration-1 결함 9건 재검증(직접 재독·재계산, 주장 신뢰 안 함)

| # | 항목 | 재검증 방법 | 결과 |
|---|---|---|---|
| D3 | Traceability(85개 REQ 전량 AC 인용) | acceptance.md 전문 파싱 스크립트로 `REQ-LDDESIGN-NNN`(콤마·틸드 범위 포함) 전수 추출 → 1~85 집합과 대조 | **85/85 전량 인용 확인**(누락 0). 이전 27개(32%)에서 85개(100%)로 개선, DoD의 포괄 문구가 아니라 각 AC "검증:" 목록에 구체적으로 박혀 있다. |
| D4 | REQ-051 OR 로직·객석광 제거·SHALL | spec.md:226 재독 | 조건 (2)가 `final_integrated.py`의 실제 OR 로직(`{'BLIND','STROBE'}&on or color=='흰색'`)을 정확히 인용하고, "객석광은 조건 요소가 아니다 — §4 비목표(C군)"를 명시. SHALL 보강 확인. **완전 해소**. |
| D5 | `_arc_palette` 817→1083행 | spec.md:47,144 재독 | 두 곳 모두 `1083행, origin/main@9dd21171 실측`으로 정정됨. `_per_chorus_palette` 1124행은 원래도 정확했음. **해소**. |
| D6 | REQ-051 SHALL 누락 | spec.md:226 재독 | SHALL 보강 확인. 단, **새 결함 발견**(아래 D-NEW1) — REQ-002가 D10 대응 중 유사 패턴을 새로 만들었다. |
| D7 | §2.3 산출물 집합 + design.md | spec.md:101-112, design.md 전문 | §2.3이 SSOT(5종=spec+plan+acceptance+design+research)를 정확히 재서술하고 spec-compact.md를 "추가" 산출물로 명확히 구분. design.md(105행)는 M2 큐모델 7필드 dataclass 개요 + M7 UI 블록 다이어그램을 담고 있으며 spec.md의 REQ 정의(레이어 5종·연산 9종·트래킹 4종 등)와 **모순 없음**을 필드별로 대조 확인. **해소**. |
| D8 | Conditional Design Route 미적용 근거 | plan.md:157-170 재독 | UI-surface 휴리스미스틱이 형식상 성립함을 인정한 뒤, 기존 레이아웃 유지(REQ-078) + `final-verification-20260921.html`이 이미 시안 역할을 한다는 두 근거로 미적용을 논증. **해소**. |
| D9 | AC-002 낡은 문턱값(0.80/0.86) | acceptance.md:27-38 재독 | `1.0`으로 정정, `chorus-escalation-audit-20260921.md`의 v3 실측치(8곡 전부 1.0)와 REQ-042의 엄밀한 서술 양쪽과 정합. **해소**. |
| D10 | depends_on draft 상태 미기재 | spec.md:142(REQ-002 Where절), plan.md:58-65(M0) 재독 | 두 곳 모두 SPEC-LDRETURN-001의 `status: draft`를 명시하고 `spec-workflow.md` § Depends_on Pre-flight Check의 wait/override/abort 3-옵션 절차를 인용해 M0 착수 조건으로 배선. `.moai/specs/SPEC-LDRETURN-001/spec.md`를 재조회해 **현재도 `status: draft`**임을 재확인(변동 없음, 문서 서술과 일치). **해소**. |

### 새로 발견된 결함(iteration 2 도입분)

**D-NEW1 (minor, optional)** — `spec.md:142`(REQ-LDDESIGN-002) — D10 대응으로 추가된 두 번째 문장("**Where** SPEC-LDRETURN-001의 `status`가... M0은 그 SPEC의 완료를 대기하거나, ... 진행한다")이 SHALL 서술어 없이 "대기하거나/진행한다"로 끝난다 — REQ-051에서 고친 것과 같은 종류의 결함이 다른 REQ에 새로 생겼다. 단, REQ-002의 **주 절**(bpm=density_bpm 전달)은 SHALL을 정확히 갖고 있어 REQ 항목 전체가 GEARS 패턴 분류 자체를 벗어나지는 않는다(REQ-051 원래 결함은 그 REQ의 유일한 서술문 자체가 SHALL이 없었던 경우였고, 이번은 주절에 이미 SHALL이 있고 부절만 누락된 경우라 성격이 다르다) — MP-2 must-pass FAIL로 판정하지 않고 optional 편집 결함으로 분류. 필요한 조치: "M0은 **SHALL** 그 SPEC의 완료를 대기하거나 명시적 override로만 진행한다"로 정정.

**D-NEW2 (minor, optional)** — `acceptance.md:385-402`(AC-LDDESIGN-031) — REQ-026·028·032·033·034·035(6개 REQ)를 한 AC에 묶어 하나의 Given-When-Then으로 검증한다. 각 조건은 개별적으로 이진 판정 가능하지만, 이 AC 하나가 FAIL할 경우 6개 조건 중 어느 것이 실패했는지 AC 번호만으로는 즉시 드러나지 않는다(Then 절 안에 조건별 결과가 나열돼 있어 실무상 큰 문제는 아니다). 필요한 조치(선택): run-phase 테스트 작성 시 AC-031의 6개 조건을 개별 assert로 나누어 실패 지점을 구분한다(AC 번호 분할은 불필요).

### Must-Pass 결과 (iteration 2)

- **[PASS] MP-1** REQ 번호 연속성 — 85개 고유, 갭·중복 0(재실측).
- **[PASS] MP-2** GEARS 형식 — 85/85 REQ가 SHALL/SHALL NOT을 가짐(재실측). D-NEW1은 부절 스타일 결함으로 optional 처리.
- **[PASS] MP-3** frontmatter — 12필드 전부 유효(재확인, 변동 없음).
- **[N/A] MP-4** 언어 중립성 — 단일 도메인, 해당 없음.
- **[PASS] MP-5** D7 교차-SPEC — SPEC-LDRETURN-001 `status: draft`(재조회로 변동 없음 확인) 등 어느 참조도 retired/superseded/archived 아님, BLOCKING 없음. depends_on 리스크는 REQ-002·M0에 명시적으로 배선돼 더는 미고지 상태가 아니다.
- **[PASS] MP-6** D8 크로스플랫폼 — syscall 0건, 자동 PASS.
- **[PASS] MP-7** clarification gate — 이사회 승인 해소 확인(위 참조), 6개 산출물 전체 0건 grep 재확인.

### 카테고리 점수 (재계산)

| 차원 | 점수 | 근거 |
|---|---|---|
| Clarity | 0.75 | REQ-051·`_arc_palette` 모두 정정됨(1.0에 근접). D-NEW1(REQ-002 부절 SHALL 누락) 잔존으로 0.75 유지. |
| Completeness | 1.0 | 섹션·frontmatter 전부 정상, §2.3 산출물 서술이 SSOT와 정합, design.md 신설·내용 충실(spec.md와 모순 없음, 필드별 대조 완료). |
| Testability | 0.75 | 약어 0건, AC-002 문턱값 정합화 완료. AC-031의 6-REQ 압축(D-NEW2)으로 완전한 1.0은 유보. |
| Traceability | 1.0 | 85/85 REQ 전량 acceptance.md에 구체적으로 인용됨(프로그램적 재계산으로 확인, 0 누락). |

조화평균 = 4 / (1/0.75 + 1/1.0 + 1/0.75 + 1/1.0) ≈ **0.857** → Tier L 통과선(0.85) 상회. 근소한 우위이므로 D-NEW1·D-NEW2(둘 다 optional)를 다음 정정 시 반영 권장.

### 회귀 확인 (iteration 1 → 2)

- D1~D10 전부 RESOLVED — 각 항목을 "주장을 믿지 않고" 파일 재독·grep·프로그램적 재계산으로 독립 재검증했다(위 표).
- 점수 추이: 0.62(iteration 1, FAIL) → 0.86(iteration 2, PASS) — **상승**이므로 STOP 신호(점수 하락 시 발동) 해당 없음.
- 정체(stagnation) 없음 — 3회 연속 동일 결함 반복 사례 없음.

### 권고

1. (선택) D-NEW1: REQ-LDDESIGN-002 두 번째 문장에 SHALL 보강.
2. (선택) D-NEW2: run-phase 테스트 작성 시 AC-031의 6개 조건을 개별 assert로 분리.
3. 그 외 필수 조치 없음 — PASS 판정으로 Implementation Kickoff Approval 단계로 진행 가능(이 SPEC은 §2.4 예외 아래 있으므로 M0~M8을 `moai todo` 카드로 분할해 배차하는 것을 잊지 말 것).

🗿 MoAI

---

## Iteration 1/3 — 2026-09-21 (과거 판정, 원문 보존)

Verdict: FAIL
Overall Score: 0.62 (근사 — Clarity 0.50 / Completeness 0.75 / Testability 0.75 / Traceability 0.50 평균. Must-Pass 위반으로 점수와 무관하게 FAIL)

> M1 Context Isolation 준수: 프롬프트에 포함된 추론 컨텍스트(감독 결정 배경 설명 등)는 무시하고 spec.md·plan.md·acceptance.md·research.md·spec-compact.md 5개 산출물(Tier L 입력 계약)만 근거로 감사했다.

### Must-Pass 결과

- **[FAIL] MP-1 REQ 번호 연속성**: `REQ-LDDESIGN-001~085` 85개 고유 번호, 표 행 85개, 갭·중복 0건(`grep -oE 'REQ-LDDESIGN-[0-9]{3}'`로 실측). 이 항목 자체는 PASS이나 §MP-2·별도 발견(D2) 참조 — REQ 번호는 연속이지만 **85개**는 Tier L 상한 25개의 3.4배다.
- **[FAIL] MP-2 GEARS 형식 준수**: spec.md:202 REQ-LDDESIGN-051이 `**When** ... 헤드룸 검사는 경고를 기록한다`로 SHALL 서술어가 빠졌다(다른 84개 REQ는 전부 SHALL/SHALL NOT을 갖는다, `grep -c SHALL` 실측). 85개 중 1개뿐이지만, M2 적대적 태도("의심스러우면 FAIL")에 따라 FAIL로 판정한다. 요구사항 계층(REQ-XXX)에만 적용한 판정이며, AC-XXX(검증 계층, Given-When-Then)에는 적용하지 않았다.
- **[PASS] MP-3 YAML frontmatter 유효성**: 12개 canonical 필드 전부 존재·타입 정합(`id/title/version/status/created/updated/author/priority/phase/module/lifecycle/tags`), snake_case 별칭 없음. `status: draft`, `priority: P1` 유효. `phase: "Lighting Copilot v1.0 target"`은 금지된 단계명(plan/run/sync/mx)이 아니다.
- **[N/A] MP-4 언어 중립성**: 이 SPEC은 단일 도메인(조명 연출) 프로젝트로, 다중 프로그래밍 언어 툴링을 다루지 않는다. N/A 자동 PASS.
- **[PASS] MP-5 D7 교차-SPEC 정합**: `related_specs`/`depends_on`에 인용된 SPEC 6개 중 4개 존재 확인(SPEC-LDRETURN-001·LDCLIMAX-001·LDACCENT-001은 `status: draft`, SPEC-COPILOT-LOOKLIB-001은 `status: completed`). SPEC-COPILOT-SONGSTD-001·CUETIME-001은 레거시(프론트매터 없는) 형식이라 `status` 필드 자체가 없다. `retired/superseded/archived` 상태를 가진 참조는 0건 — BLOCKING 없음.
- **[PASS] MP-6 D8 크로스플랫폼**: `grep -n syscall spec.md acceptance.md plan.md research.md spec-compact.md` → 0건. D8-4에 따라 자동 PASS.
- **[FAIL] MP-7 clarification gate**: `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` → plan.md에 3건 실측(207행 MIB 이동/정착 초, 214행 콘솔 문법 3종, 220행 스트로브 정책 기본값). §5·plan.md §F 자체가 "Implementation Kickoff Approval 이전에 해소" 예정임을 명시하지만, MP-7 규칙은 **감사 시점(iteration 1)**에 미해소 마커가 존재하면 점수와 무관하게 FAIL이라고 명시한다("score-independent... a high aggregate score never auto-resolves an open clarification marker"). 오케스트레이터가 AskUserQuestion으로 3건을 해소한 뒤 재감사해야 한다.

### 카테고리 점수 (0.0-1.0, 루브릭 앵커)

| 차원 | 점수 | 루브릭 밴드 | 근거 |
|---|---|---|---|
| Clarity | 0.50 | 0.50 (여러 REQ가 해석에 따라 다르게 구현될 수 있음) | spec.md:202 REQ-051이 실제 프로토타입 로직(OR)과 다른 조건(AND, 존재하지 않는 "객석광" 그룹)을 기술 — §D4. spec.md:46/120의 `_arc_palette` 인용 행번호 오류(817행, 실제 1083행) — §D5 |
| Completeness | 0.75 | 0.75 (비핵심 섹션 하나가 약함) | HISTORY/배경/범위/요구사항/AC/비목표/frontmatter 전부 존재, Out of Scope H3 서브헤딩 5개+불릿 정상. 단 §2.3의 Tier L 산출물 집합 서술이 SSOT와 어긋남(design.md를 spec-compact.md로 대체, design.md를 run-phase로 미룬다는 서술 오류) — §D7 |
| Testability | 0.75 | 0.75 (AC 1개가 정밀한 이진 판정이 아님) | 약어("적절히" 등) 0건, 대부분 8곡 픽스처 기준 구체적 수치. AC-LDDESIGN-002(G2)가 오늘 최종 프로토타입 실측치(1.0, 8/8)가 아니라 이전 단계 보고서의 낡은 수치(0.80/0.86)를 문턱값으로 인용 — §D9 |
| Traceability | 0.50 | 0.50 (다수 REQ가 AC 없음) | REQ 85개 중 acceptance.md에 구체적으로 인용된 것은 27개(32%)뿐 — 나머지 58개(68%)는 Definition of Done의 "REQ-LDDESIGN-001~085 전량 PASS" 포괄 문구로만 덮인다. §D3 |

### 발견된 결함 (구조화 defect-list)

D1. MP7-CLARIFY — `plan.md:207,214,220` — 미해소 [NEEDS CLARIFICATION] 마커 3건(MIB 이동/정착 초, 콘솔 문법 3종, 스트로브 정책 기본값)이 감사 시점에 존재 — Severity: critical — Class: blocking — 필요한 조치: 오케스트레이터가 `AskUserQuestion`으로 세 주제를 사용자(감독)와 함께 해소(또는 명시적으로 M8 프로브 결과 대기로 확정)한 뒤 iteration 2 재감사.

D2. TIER-BUDGET — `spec.md:14,108` — `tier: L`인데 REQ가 85개(spec-workflow.md § SPEC Complexity Tier의 Tier L 상한 25개의 3.4배). 이 규칙은 "상한 초과는 상위 Tier로 올리거나 SPEC을 분할하라는 신호"라고 명시하는데, L이 최상위 Tier이므로 유일한 해법은 분할이다 — Severity: critical — Class: blocking — 필요한 조치: M0(선행조건)·M1(어휘/워크시트)·M2(큐모델)·M3(컨셉/컬러)·M4(밀도/회차)·M5(트래킹/타이밍/MIB)·M7(UI) 경계를 따라 4~6개의 독립 SPEC으로 분할하거나, 분할하지 않는 명시적 예외 사유를 사용자에게 제시하고 승인받는다.

D3. TRACE-GAP — `acceptance.md` 전체 — REQ-LDDESIGN-085개 중 58개(68%)가 acceptance.md에 구체적으로 인용되지 않음(`REQ-LDDESIGN-NNN` 리터럴도, `NNN~MMM` 범위 표기도 없음) — 예: M2 큐모델 REQ-017~019·022~025(9개 중 6개 미인용), §3.12 안전큐·근거등급 REQ-068~072(5개 전부 미인용), §3.13 하류 브리지 REQ-073~077(5개 전부 미인용), UI REQ-078·080·081·082·084(8개 중 5개 미인용) — Severity: major — Class: blocking — 필요한 조치: 각 REQ가 최소 하나의 구체적 AC(또는 기존 AC의 "검증:" 목록 확장)로 추적되도록 acceptance.md를 보강. Definition of Done의 포괄 문구("REQ-LDDESIGN-001~085 전량 PASS")는 개별 추적성을 대체하지 못한다.

D4. LOGIC-MISMATCH — `spec.md:202`(REQ-LDDESIGN-051) — 조건 (2) "Chorus 1에서 순백·블라인더·객석광·스트로브가 **모두** 사용됨"이 (a) 이 SPEC이 근거로 인용하는 `final_integrated.py`의 실제 로직(`{'BLIND','STROBE'}&set(c1['on'])) or c1['color']=='흰색'` — 블라인더 **또는** 스트로브 **또는** 순백, AND가 아니라 OR)과 다르고, (b) 존재하지 않는 "객석광" 그룹을 조건 요소로 명시해 spec.md §4 비목표(C군)의 "객석광 그룹(현재 리그 18그룹에 없음)... 은 다루지 않는다"와 정면으로 모순된다 — Severity: major — Class: blocking — 필요한 조치: 조건 (2)를 "블라인더 또는 스트로브가 사용되거나 색이 순백"으로 수정하고 "객석광" 언급을 제거(또는 리그 확장을 명시적으로 제안하고 비목표 C군과 조정).

D5. CITATION-ERROR — `spec.md:46,120` — `server/web/session.py`의 `_arc_palette` 인용 행번호가 817행으로 적혀 있으나, 이 SPEC이 지정한 측정 트리(`origin/main@9dd21171`, plan.md §A)에서 실측하면 1083행이다(`_per_chorus_palette`의 1124행 인용은 정확함) — Severity: minor — Class: blocking — 필요한 조치: 817행 → 1083행으로 정정.

D6. GEARS-MODAL — `spec.md:202`(REQ-LDDESIGN-051) — SHALL 서술어 누락(다른 84개 REQ는 전부 SHALL/SHALL NOT을 가짐) — Severity: minor — Class: blocking — 필요한 조치: "헤드룸 검사는 **SHALL** 경고를 기록한다"로 수정.

D7. ARTIFACT-SET — `spec.md:101-104`(§2.3) — "Tier L의 전체 산출물 집합 — design.md·progress.md — 는 착수 승인 이후 run-phase 진입 시 채워진다"는 서술이 SSOT(`spec-workflow.md` § SPEC Complexity Tier)와 어긋난다. SSOT는 Tier L의 5개 plan-phase 산출물을 spec.md+plan.md+acceptance.md+**design.md**+research.md로 정의하며(spec-compact.md는 포함되지 않음), design.md는 run-phase로 미뤄지는 것이 아니라 plan-phase 산출물이다. progress.md는 애초에 Tier 산출물 집합표에 속하지 않는 별개 개념(모든 Tier 공통 run-phase 추적 파일)이다 — Severity: minor — Class: optional — 필요한 조치: design.md를 실제 plan-phase 산출물로 추가하거나, spec-compact.md로 대체한 근거를 명시적으로 남기고 서술을 정정.

D8. DESIGN-ROUTE — `spec.md:11`(module), `plan.md` M7 — `tier: L` + `module:`에 `ui/src/components/` 포함 + acceptance.md AC-018~020이 실제 UI 컴포넌트(ConceptPanel·SongTimeline·CueSheetTimeline·StatusBanner)를 대상으로 함 — spec-workflow.md § Conditional Design Route의 UI-surface 휴리스틱(두 조건 모두 충족)에 해당해 `plan → design → run`(manager-design D1-D5) 경로 적용 대상일 수 있으나, spec.md·plan.md 어디에도 이 경로 적용 여부가 언급되지 않는다 — Severity: minor — Class: optional — 필요한 조치: plan.md에 Conditional Design Route 적용 여부를 명시(적용 시 M7 이전에 별도 설계 마일스톤 표기).

D9. STALE-THRESHOLD — `acceptance.md:27-28`(AC-LDDESIGN-002) — G2 정체성 문턱값을 "0.80(Rain·Chorus 5 기준) 이상... 8곡 평균 0.86 이상"으로 정의했는데, 이 수치는 이전 단계 보고서(`cue-density-8songs-20260921.md`)의 것이다. 이 SPEC이 회귀 기준선으로 삼는 최종 프로토타입(`final_integrated.py` v3, `chorus-escalation-audit-20260921.md` 9행·33-41행)은 8곡 전부 정체성 **1.0**을 실측했고, REQ-LDDESIGN-042도 "이전 후렴과 동일하게 유지된다"는 엄밀한(비율이 아닌) 표현을 쓴다. Definition of Done도 "오늘 실측치 이하로 떨어뜨리지 않아야"라고 못박는데, 오늘 실측치는 0.86이 아니라 1.0이다 — Severity: minor — Class: optional — 필요한 조치: AC-002의 Then 절을 v3 실측치(1.0, 구조상 적용 가능한 모든 후렴 쌍에서 동일) 기준으로 갱신.

D10. DEP-STATUS — `spec.md:16`(depends_on) — `depends_on: [SPEC-LDRETURN-001]`의 실제 `status`는 `draft`(progress.md §E.2~E.4 run-phase 증거 전부 공란)인데, spec.md §1.1·REQ-LDDESIGN-002 배경 서술은 "SPEC-LDRETURN-001이... 확보했다"처럼 이미 완료된 것으로 읽힌다. `build_songcue_bundle`의 `bpm` 키워드 인자는 실측 결과 코드에 이미 존재하므로 기술적으로는 문제가 없으나, `spec-workflow.md`의 Depends_on Pre-flight Check(엄격 정의: `status: completed`만 충족)에 따라 run-phase 진입 시 블로커로 걸릴 수 있다 — Severity: minor — Class: optional — 필요한 조치: run-phase 진입 전 SPEC-LDRETURN-001의 상태를 갱신하거나 `--ignore-deps` 오버라이드 근거를 미리 문서화.

### 회귀 확인 (2회차 이상에서만)

해당 없음 — 이번이 iteration 1이다.

### 권고

1. (필수, D1) 오케스트레이터가 `AskUserQuestion`으로 plan.md §F의 [NEEDS CLARIFICATION] 마커 3건을 해소(또는 M8 프로브 대기로 명시적 합의)한다.
2. (필수, D2) 85개 REQ를 Tier L 상한(25) 이내로 줄이도록 SPEC을 분할하거나, 분할하지 않을 명시적 예외 승인을 받는다.
3. (필수, D3) acceptance.md의 각 AC "검증:" 목록을 확장해 현재 미인용 REQ 58개가 최소 1개의 구체적 AC로 추적되게 한다.
4. (필수, D4) REQ-LDDESIGN-051 조건 (2)를 프로토타입의 실제 OR 로직으로 정정하고 "객석광" 언급을 제거하거나 정당화한다.
5. (권장, D5·D6) `_arc_palette` 행번호(817→1083)와 REQ-051의 SHALL 누락을 수정한다.
6. (권장, D7·D8·D9·D10) 산출물 집합 서술, Conditional Design Route 적용 여부, AC-002 문턱값, SPEC-LDRETURN-001 의존성 상태를 각각 정정·명시한다.

🗿 MoAI
