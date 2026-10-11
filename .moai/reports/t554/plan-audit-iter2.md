# SPEC Review Report: SPEC-LDBEAT-001
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.80 (참고치 — Must-Pass Firewall(MP-2)로 집계 점수와 무관하게 FAIL)

> Reasoning context ignored per M1 Context Isolation — 배차 프롬프트에 포함된 감독 지시·리드 결정 원문은 디자인 충실도(design fidelity) 검증의 **외부 대조 기준**(스펙 작성자의 자기합리화 근거가 아님)으로만 썼다. SPEC 작성자(manager-spec)의 승인-지향 추론은 이 감사에 전달되지 않았고, spec.md/plan.md/acceptance.md/design.md/research.md/progress.md 파일만 근거로 판정했다.

## Tier 입력 계약

Tier L — spec.md + plan.md + acceptance.md + design.md + research.md 5개 전부 읽음(progress.md도 맥락으로 읽음).

## Must-Pass Results

- [PASS] MP-1 REQ 번호 일관성: `grep -oE 'REQ-LDBEAT-[0-9]{3}' spec.md` → 001~025 연속, 중복·공백 0건. `AC-LDBEAT-[0-9]{3}` → 001~025 연속, 중복·공백 0건.
- [**FAIL**] MP-2 EARS/GEARS 형식 준수(요구사항 계층 — spec.md REQ-XXX에만 적용, AC는 Group 4에서 별도 채점): REQ-016~025 신설분(카드 t554) 전수를 실측 재검사한 결과, 4곳에서 굵은 GEARS 트리거 없는 평서문 또는 트리거 있으나 `**shall**`이 없는 절이 요구사항 칸에 남아 있다 — iteration 1의 D1(REQ-019(b))과 바이트 단위로 같은 유형의 결함이 **다른 REQ 3곳에 재발**했다. 상세는 `## Defects Found` D-NEW-1~D-NEW-4.
- [PASS] MP-3 YAML frontmatter 유효성: spec.md:1-17 — `id`/`title`/`version`/`status`/`created`/`updated`/`author`/`priority`/`phase`/`module`/`lifecycle`/`tags` 12개 전부 존재, snake_case 별칭(`created_at`/`updated_at`/`labels`/`spec_id`) 0건. `priority: P1`(허용 enum), `status: in-progress`(8값 enum 안). 선택 필드 `tier: L`·`related_specs`도 정상.
- [N/A] MP-4 Section 22 언어 중립성: 이 SPEC은 단일 언어(TypeScript/Python) 프로젝트 범위라 적용 대상 아님(자동 PASS).
- [PASS] MP-5 D7 교차 SPEC 정합: `grep -Eo 'SPEC-([A-Z][A-Z0-9]+-)+[0-9]+' *.md | sort -u` → `SPEC-LDARRANGE-001`(status: draft)·`SPEC-LDBARMAP-001`(status: in-progress)·`SPEC-LDDESIGN-001`(status: completed)·`SPEC-LDRENDER-001`(status: completed)·`SPEC-LDRHYTHM-001`(status: in-progress) — `retired`/`superseded`/`archived` 0건. BLOCKING 없음.
- [N/A] MP-6 D8 크로스플랫폼 규율: `grep -i syscall .moai/specs/SPEC-LDBEAT-001/*.md` → 매치 0건(exit 1). 자동 PASS.
- [PASS] MP-7 clarification gate: `grep -rn '\[NEEDS CLARIFICATION' plan.md research.md` → 매치 0건(exit 1).

**MP-2가 FAIL이므로 M5 필수통과 방화벽에 따라 다른 모든 PASS/점수와 무관하게 전체 Verdict는 FAIL이다.**

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — 한두 개 요구사항에 가벼운 모호함 | spec.md:163(REQ-020(a))·164(REQ-021(b))·167(REQ-024(b)(c)) 네 곳의 비-GEARS 평서문이 "이것이 구속력 있는 shall 절인가"를 모호하게 만든다. 나머지 REQ-016~025 21개 절은 전부 굵은 트리거로 명확(실측 재확인, 아래 참조). |
| Completeness | 1.0 | 1.0 — 전 섹션·frontmatter 완비 | spec.md: HISTORY(L20)·§0 Tier 근거(L41)·§1~2 배경(L63,76)·§3 REQUIREMENTS(L87)·§4 Out of Scope(L170, H3 서브헤딩 8개 전부 `-` 불릿 보유, 카드 t554 신설분 L220-226도 포함)·§5 열린 결정(L228). frontmatter 12/12(L1-17). Tier L 5아티팩트(spec/plan/acceptance/design/research) 전부 존재·완비. |
| Testability | 0.75 | 0.75 — AC 하나가 바이너리 테스트 아님(근사치로만 측정 가능) | AC-LDBEAT-017(c)·019(e)·022(c)는 `getComputedStyle(...).height/maxWidth` 정확값 assert로 완전 바이너리. 그러나 REQ-LDBEAT-024(a)의 ⏮처음/스페이스바/콘솔같이 토글과 (b)의 "재생 위치 실시간 동기+타임라인 자동스크롤"·"마디 클릭 시 이어재생" 주장은 AC-LDBEAT-024의 Given/When/Then 어디에도 대응 검증 행이 없어(아래 D-NEW-5 참조) 지금 문면으로는 PASS/FAIL 판정 수단이 없다. |
| Traceability | 0.75 | 0.75 — REQ 하나가 간접 매핑 | §A.1(acceptance.md:76-106)은 REQ-LDBEAT-017~025 전부를 AC-LDBEAT-017~025에 1:1로, REQ-016은 DoD로 명시 매핑한다(완전). 그러나 REQ-LDBEAT-024는 (a)의 절반(⏮처음/스페이스바/콘솔같이)과 (b) 전체가 AC-024의 실제 Given/When/Then에 대응 행이 없다(REQ 레벨 매핑은 있으나 하위-레터 단위에서 공백 — D-NEW-5). |

조화평균(참고용 집계): 4 / (1/0.75 + 1/1.0 + 1/0.75 + 1/0.75) ≈ 0.80. **이 점수는 Must-Pass Firewall을 대체하지 않는다 — Verdict는 FAIL이다.**

## Regression Check (Iteration 2) — iteration 1 defects (`.moai/reports/t554/plan-audit.md`)

| ID | 설명 | 상태 | 증거 |
|----|------|------|------|
| D1 | REQ-LDBEAT-019(b)가 비-shall 문장을 요구사항 칸에 섞음 | **RESOLVED** | spec.md:162 REQ-LDBEAT-019의 요구사항 칸은 지금 `(a)...(c)...(d)...`만 있고 `(b)`가 없다(파이썬으로 정확히 컬럼 분리해 재확인, `python3 -c "re.split(...)"` → 요구사항 칸 원문에 "(b)" 부재). (b) 내용은 근거 칸으로 옮겨져 "**(b, 비고 — shall 절 아님, plan-audit iteration 1 D1 대응으로 요구사항 칸에서 제거)**"로 명시돼 있다. 참조 무결성: `grep -n "REQ-LDBEAT-019(b)" *.md` → design.md:40 1곳뿐이고 그 문맥("유효(겹침 금지는 이미 REQ-LDBEAT-004(h)/AC-LDBEAT-003(b)가 검증 — 이 절은 화면 목록 완전성 기록)")이 근거-칸 위치와 일치해 댕글링 참조 0건. |
| D2 | REQ-LDBEAT-016(b)의 440px/1640px·97%/1450px 치수에 구체 검증 수단 없음 | **RESOLVED** | acceptance.md:51(AC-LDBEAT-017(c), `getComputedStyle(...).maxWidth === '1640px'` + `min(폭×0.97,1640)` assert)·53(AC-LDBEAT-019(e), `.beat-grid-mid`/`.beat-grid-lanes` `height === '440px'` + 내부 스크롤 assert)·56(AC-LDBEAT-022(c), `.beat-grid-stage-pane` `height === '320px'` assert 보강). 310px(AC-021(b))·1450px(AC-017(a)(b))는 기존에 이미 구체적임을 재확인(acceptance.md:55,51). |
| D3 | research.md §10 집계 오류(선언 9·16·24·0=49, 실제 54행) | **RESOLVED** | 독립 재측정: `awk '/^## §1\./,/^## §10\./' research.md \| grep "^\| " \| grep -v 분류 \| grep -v '^\|---' \| wc -l` → `54`. 분류별 정확 집계(`**구현**`/`**부분**`/`**미구현**`/`**상충**` + 소괄호-부기 변형 전수, 두 가지 독립 grep 방식으로 교차검산) → 구현 10(플레인 6+부기 4)·부분 15(플레인 15+부기 0)·미구현 29(플레인 27+부기 2)·상충 0, 합 54 — research.md:129-132가 선언한 10/15/29/0과 **정확히 일치**. |
| D4 | plan.md M9에 REQ-LDBEAT-021 전용 단계 없음 | **RESOLVED** | plan.md:192 "4. **(신설, plan-audit iteration 1 D4 대응)** 편집 칸의 남은 필드 + 표→편집 연동을 완성한다(REQ-LDBEAT-021(a)(b))" — M9 step 목록이 1~9로 연속(재확인: `sed -n '185,230p' plan.md \| grep "^[0-9]\."` → 1~9 순서대로, 기존 단계 삭제·순서 재배치 없이 번호만 밀림). |
| D5 | `RunbookMode.tsx` "281행" 오기 | **RESOLVED** | `wc -l ui/src/components/RunbookMode.tsx` → `280`. plan.md:5,8,247과 research.md:14 전부 "280행"으로 일치, spec.md:24,78도 "280행"으로 일관. |

**5건 전부 RESOLVED — 스태그네이션 신호 없음.**

## Defects Found (structured defect-list) — iteration 2 신규 발견

이번 라운드는 D1~D5 회귀 확인에 더해, 배차 지시에 따라 REQ-016~025 전수를 바이트 단위로 재검사했다. 그 결과 D1과 동형인 MP-2 위반이 **다른 3개 REQ, 4개 절**에서 발견됐다 — iteration 1은 D1(REQ-019(b))만 잡고 같은 패턴의 나머지 사례는 놓쳤다.

D1. **GEARS-MIX-NEW-01** — `spec.md:163`(REQ-LDBEAT-020(a)) — 요구사항 칸 (a) 절 안에 굵은 트리거(`**When**`/`**The**`/`**shall**` 어느 것도) 없는 평서문이 그대로 남아 있다: 「3줄 이상이 같은 마디에서 동시에 바뀌면 그 마디에 장면 전환 알약이 나타나고, 누르면 그 순간 전체 표 + 「모두 끊기/모두 1박 페이드」를 보여준다.」 이 문장은 "진짜 요구사항"이다(AC-LDBEAT-020(a) Then이 "장면전환알약"을 실제로 검증한다 — acceptance.md:54) — 삭제 대상이 아니라 GEARS로 재포맷할 대상이다. — Severity: critical — Class: blocking — Required fix: 이 문장을 독립 레터 하위 절로 쪼개거나 (a) 안에 `**When** 3줄 이상이 같은 마디에서 동시에 바뀌면, **The** 그 마디 **shall** 장면 전환 알약을 보여주고, **When** 그 알약이 눌리면 **The** 화면 **shall** 그 순간 전체 표 + 「모두 끊기/모두 1박 페이드」를 보여준다` 형태로 명시적 트리거를 단다.

D2. **GEARS-MIX-NEW-02** — `spec.md:164`(REQ-LDBEAT-021(b)) — 같은 패턴: 「같은 칸에 전환 편집·장면 전환·AI 제안도 열리며, 아무것도 선택하지 않았을 때는 안내문을 보여준다.」 — 트리거 0건. AC-LDBEAT-025(c)·AC-LDBEAT-020(d)가 이 내용을 간접적으로 다루지만 REQ 문면 자체는 비-GEARS다. — Severity: critical — Class: blocking — Required fix: `**The** 같은 칸 **shall** 전환 편집·장면 전환·AI 제안도 열며, **While** 아무것도 선택되지 않은 동안 **The** 그 칸 **shall** 안내문을 보여준다`로 재작성.

D3. **GEARS-MIX-NEW-03(트리거 있으나 shall 없음)** — `spec.md:167`(REQ-LDBEAT-024(b) 두 번째 문장) — 「**When** 재생 중 마디를 클릭하면, 재생은 그 자리부터 이어진다.」 굵은 `**When**` 트리거는 있으나 GEARS 패턴이 요구하는 `**shall**`가 없다 — "재생은 ~이어진다"는 평서형이다. 이 문서의 다른 모든 When-패턴(예: REQ-020(d), REQ-021(a))은 예외 없이 `**The** <subject> **shall** <response>`를 동반하는데, 이 절만 깨져 있다. — Severity: major — Class: blocking — Required fix: `**When** 재생 중 마디를 클릭하면, **The** 재생 **shall** 그 자리부터 이어진다`로 교정.

D4. **GEARS-MIX-NEW-04** — `spec.md:167`(REQ-LDBEAT-024(c) 두 번째 문장) — 「연결되면 버튼은 체크(✓)와 파일명을 보여주고, 불러오기가 끝나기 전에 ▶를 눌러도 준비되는 즉시 재생을 시작하며, 연결에 실패하면 그 이유를 표시한다.」 트리거 0건. 이 내용은 AC-LDBEAT-024(a)(b)(c)가 이미 검증하므로(acceptance.md:58) 내용 자체는 맞고 GEARS 포맷만 빠졌다. — Severity: critical — Class: blocking — Required fix: 세 개의 독립 `**When**/**shall**` 절로 재작성(예: `**When** 자동 연결이 성공하면, **The** 버튼 **shall** 체크(✓)와 파일명을 보여준다. **While** 불러오기가 끝나기 전인 동안 ▶가 눌리면, **The** 재생 **shall** 준비되는 즉시 시작된다. **When** 연결이 실패하면, **The** 화면 **shall** 그 이유를 표시한다`).

D5. **TRACE-GAP-NEW-01** — `spec.md:167`(REQ-LDBEAT-024(a) 후반 — ⏮처음/❚❚스페이스바/콘솔 같이 토글)와 REQ-LDBEAT-024(b) 전체(재생 위치 실시간 동기+타임라인 자동스크롤, 마디 클릭 시 이어재생) — `acceptance.md:58`(AC-LDBEAT-024)의 실제 Given/When/Then을 전수 확인한 결과(`grep -n "마디를 클릭\|타임라인이 따라\|재생 위치 선" acceptance.md` → 매치 0건) 이 세 가지 행위 주장에 대응하는 검증 행이 하나도 없다. AC-LDBEAT-024의 When 목록(a)~(f)는 음원 자동연결·로딩타이밍·실패·⏪10초/10초⏩·갈라짐·화면오류 여섯 가지뿐이고, ⏮/스페이스바/콘솔같이/재생위치동기/마디클릭이어재생은 다루지 않는다 — §A.1(acceptance.md:106)은 REQ-024→AC-024를 1:1로 선언하지만 그 선언이 REQ-024의 하위 절 전부를 실제로 덮는지는 검증되지 않았다(design.md:53 #21행도 "플레이 묶음·실시간 동기는 REQ-LDBEAT-024(a)(b)"라고 매핑하면서 같은 공백을 물려받았다). — Severity: major — Class: blocking — Required fix: AC-LDBEAT-024에 새 AC-ID 없이 하위 체크 행 추가 — (g) ⏮처음/스페이스바/콘솔같이(Top Timecode→Go Timecode) 토글 각각의 DOM/핸들러 확인, (h) 재생 중 재생위치선 갱신 + 무대/표/편집칸 동기 + 타임라인 자동스크롤 assert, (i) 재생 중 임의 마디 클릭 → 그 자리부터 이어재생 assert(정지 상태 클릭과 구분).

D6. **XREF-MISLABEL-01** — `acceptance.md:27`·`acceptance.md:97`·`design.md:59`·`design.md:71`·`spec.md:39`(5곳 전부 카드 t554가 신설 — `git show bee51823:.../spec.md | grep -c "spec.md §D"` → `0`, 즉 이 개정 이전에는 이 표현이 전혀 없었다) — DoD(Definition of Done) 섹션은 실제로 `acceptance.md` §D(acceptance.md:123 `## §D Definition of Done`)에 있는데, 다섯 곳 모두 "spec.md §D DoD"로 지칭한다. spec.md 자신의 섹션 목록(`grep -n "^## " spec.md`)은 HISTORY→§0→감독결정→§1~§3→§4 Out of Scope→§5 열린 결정으로 끝나며 **§D는 존재하지 않는다**. 이탈 승인·치수 보존 조항(REQ-LDBEAT-016)을 찾는 구현자가 "spec.md §D"를 spec.md 안에서 찾다가 실패할 수 있다. — Severity: minor — Class: blocking(문서 내부 정합성 오류이지 희망사항이 아님) — Required fix: 5곳 전부 "acceptance.md §D DoD"로 교정(또는 cross-file 참조를 명확히 하는 공통 표기 "§D(acceptance.md) DoD"로 통일).

## Recommendation

**FAIL — iteration 3 재감사 전에 다음을 수정한다 (델타 스코프: D-NEW-1~D-NEW-6만, D1~D5는 RESOLVED로 재확인 불필요):**

1. `spec.md:163` REQ-LDBEAT-020(a) 끝의 "3줄 이상이..." 문장에 `**When**`/`**shall**` GEARS 트리거를 명시적으로 단다(D-NEW-1).
2. `spec.md:164` REQ-LDBEAT-021(b) 끝의 "같은 칸에..." 문장에 GEARS 트리거를 명시적으로 단다(D-NEW-2).
3. `spec.md:167` REQ-LDBEAT-024(b) 두 번째 문장("재생은 그 자리부터 이어진다")에 `**shall**`을 추가한다(D-NEW-3).
4. `spec.md:167` REQ-LDBEAT-024(c) 끝의 "연결되면 버튼은..." 문장을 독립 GEARS 절들로 재작성한다(D-NEW-4).
5. `acceptance.md`의 AC-LDBEAT-024에 ⏮/스페이스바/콘솔같이·재생위치동기+자동스크롤·마디클릭이어재생 세 가지를 검증하는 하위 체크 행을 추가한다(D-NEW-5, 새 AC-ID 없이).
6. "spec.md §D DoD" 5곳을 "acceptance.md §D DoD"로 교정한다(D-NEW-6).

새 REQ/AC-ID는 필요 없다 — 전부 기존 REQ-016~025/AC-017~025의 하위 절 재포맷·보강이다. REQ 25/AC 25(Tier L 상한)는 수정 후에도 불변으로 유지된다.

**iteration 1 대비 집계 점수는 상승(0.75→0.80 참고치)했으므로 LEAN 워크플로 STOP-on-regression 조건(iter(N+1) < iter(N))은 발동하지 않는다 — 정상적인 델타 스코프 재감사로 iteration 3을 진행한다.**
