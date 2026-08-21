# SPEC Review Report: SPEC-COPILOT-LXSEQ-001

Iteration: 1/3
Verdict: **FAIL** (MP-7 clarification gate 미해소 + AC 검증 가능성 차단 결함 5건)
Overall Score: **0.86** (조화평균 — Clarity 0.85 · Completeness 0.95 · Testability 0.70 · Traceability 1.00; Tier M 임계 0.80)
감사 대상: HEAD `453846a` · 브랜치 `jjjh7401/LX-SEQ` · 아티팩트 5종(spec/plan/acceptance/research/progress) · 감사 모델 Claude 단독(`audit_model` 미설정)
M1 Context Isolation: 작성자 추론 맥락은 무시했다. 아티팩트 파일과 저장소 코드·입력 데이터 실물만 읽었다.

> 점수(0.86)는 Tier M 임계(0.80)를 넘지만, 판정은 점수와 독립인 must-pass 화재벽(MP-7)과 AC 정확성 결함(D2~D6)이 가른다. 마커 3건을 오케스트레이터가 닫고 manager-spec이 D2~D6을 고치면 델타 재감사에서 PASS 밴드가 예상된다.

---

## Must-Pass Results

- [PASS] **MP-1 REQ 번호 일관성** — `grep -oE 'REQ-LXSEQ-[0-9]{3}' spec.md | sort -u` → 001~015 연속 15건, 중복·누락 0 (spec.md:60-80).
- [PASS] **MP-2 GEARS 형식(요구 계층 = spec.md REQ-XXX)** — 15건 전부 패턴 태그 + `shall`/`shall not` 구조. Ubiquitous 9(001·004·005·006·008·010·011·014·015) · Event-driven 2(002·007) · Unwanted 2(003·009) · While 1(012) · Where 1(013). 태그 오용 2건은 문장 구조 자체는 GEARS라 PASS 유지하되 optional 결함으로 기록(O1 REQ-013 `[Where]`는 기능 게이트가 아닌 사건이라 `When`이 맞음 spec.md:78; O2 REQ-015 `[Ubiquitous]`이나 본문은 "수정하지 않는다" 금지형이라 `[Unwanted]`가 맞음 spec.md:80). 검증 계층(acceptance.md AC-XXX)은 Given-When-Then이며 여기서 감점하지 않았다.
- [PASS] **MP-3 YAML 프런트매터** — 12필드 전부 존재·타입 적합: `id`(L2) `title`(L3) `version: "0.1.0"`(L4, 인용 semver) `status: draft`(L5) `created/updated: 2026-08-21`(L6-7, ISO) `author`(L8) `priority: P0`(L9) `phase`(L10) `module`(L11) `lifecycle: spec-anchored`(L12) `tags`(L13, 쉼표 문자열). 거부 별칭(`created_at`/`labels`/`spec_id`) 0. 추가 필드 `tier: M`(L14, 스키마 선택 필드) · `related_specs`(L15, 리스트 — 스키마 외 필드, 거부 대상 아님). `mcp__moai__spec_audit` 결과 INFO 3건뿐(era 자동판정 V3R5 · 문서 머리의 "draft (v0.1.0 …)" 문구 캡처) — 차단 없음.
- [N/A] **MP-4 언어 중립성** — Python 단일 언어 백엔드 SPEC. 다언어 툴링 열거 없음.
- [PASS] **MP-5 D7 교차 SPEC** — spec.md 본문 참조 4건 실측: `SPEC-COPILOT-VWX-001` status=draft · `SPEC-COPILOT-AUTOPATCH-001` status=draft · `SPEC-COPILOT-PRECHK-001` status=completed · `SPEC-COPILOT-MVP-001` status=in-progress. retired/superseded/archived 0 → BLOCKING 없음. plan.md §E의 `SPEC-COPILOT-LXSEQ-002/003/004`는 `.moai/specs/`에 없음(SHOULD) — "이름만 예약"으로 명시돼 있어 의도된 부재(정보).
- [PASS] **MP-6 D8 syscall** — `grep -c syscall spec.md` → 0. 자동 PASS.
- [FAIL] **MP-7 clarification gate** — `grep -c '\[NEEDS CLARIFICATION:' plan.md` → **3** (plan.md:50, :51, :52 — ① 입력 채널 ② 이름 접두 ③ 모드 미해결 처리). research.md:109·:132는 마커 본체가 아닌 언급(콜론 없음). spec.md·acceptance.md는 0(요구·인수 계층은 깨끗). 규약상 미해소 마커는 점수와 무관한 must-pass 실패 → D1(critical, "clarification gate"). 해소 주체는 **오케스트레이터**(`AskUserQuestion` 3라운드, Kickoff 전)이며 manager-spec 재작성 대상이 아니다. 답이 나오면 plan.md §A.4를 닫고 `progress.md` M0 절에 기록한다(AC-LXSEQ-001 ⑤가 그 기록을 요구).

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|---|---|---|---|
| Clarity | 0.85 | 0.75~1.0 | 요구 대부분 단일 해석. 감점: REQ-LXSEQ-008(spec.md:70)이 런 경계에 `Group`을 **확정**으로 넣고 "런 12개"를 요구로 못박는데 plan.md:51(§A.4-②)은 같은 결정을 **열린 결정**으로 둔다 — 사용자가 타입 접두를 고르면 REQ-008 문면이 위반된다(D5). REQ-010(spec.md:75) `name_prefix_mode` 기본값이 plan.md 결정에 위임돼 요구 단독으로는 미확정. REQ-005(spec.md:67) 동폭 모드 타이브레이크("숫자·단어 토큰이 모드 이름에 포함되는 것이 하나일 때") 토큰 분할 규칙 미정의. |
| Completeness | 0.95 | 1.0 밴드 | HISTORY(spec.md:24) · 개요/WHY(:32) · 단계 경계/WHAT(:45) · REQ 15(:56-80) · 환경·전제(:84) · Out of Scope H3 5개 + `-` 불릿(:106-135) · 데이터 모델(:139) · 참조 구현(:154). AC는 acceptance.md 16건. 감점: `only_fids`로 걸러진 행의 보고 부류가 닫힌 어휘(spec.md:76)에 없음(O4). |
| Testability | 0.70 | 0.50~0.75 | 16 AC 중 5건에서 **검증 명령이 이 트리에서 돌지 않거나 기대값이 틀린다**: AC-001 ②③ 입력 경로가 워크트리에 없음(D2) · AC-003 ④ 겹침 산술 오류(D3) · AC-011 `-k "closed or thirty"`가 테스트 0건 선택(D4 — 실행 확인: `no tests collected (71 deselected)`) · AC-009 ① 대안 런 수 10은 실제 9(D6) · AC-007 ④ 블라인드스팟 예시 `1.510`이 U2 구간과 무관(D7). 나머지 11건은 이진 판정 가능하며 비공허성 단언을 동반한다(AC-002 ②, AC-008 ②, AC-010 ③, AC-011 ②, AC-013 ③, AC-015 ⑤). 족제비어(appropriate/reasonable) 0건. |
| Traceability | 1.00 | 1.0 | 역추적표(acceptance.md:36-52) REQ 15/15 커버, 모든 AC의 "대상 요구사항"이 존재하는 REQ를 가리킨다. 비추적 AC 2건(001·016)은 사유 명시(acceptance.md:54). plan.md 마일스톤별 AC 배정(:76,:84,:92,:100,:108) = acceptance.md §C.0a(:58-66) 합 16·중복 0 — 직접 대조 일치. |

---

## Per-dimension verification — 오케스트레이터가 지시한 9개 축

| 축 | 판정 | 근거 |
|---|---|---|
| 감독 결정 ① 신규 코드 = 파서+매퍼, 쓰기 경로 신설 금지 | 반영됨 | REQ-LXSEQ-009(spec.md:71) import·식별자·문자열 금지 목록, REQ-010(:75) `patch_fixtures` 내부 `ToolCall` 위임, Out of Scope "신규 콘솔 쓰기 경로"(:126-131). `vectorworks_autopatch`가 형제 핸들러를 `ToolCall`로 부르는 선례 실측: tools.py:2936-2940·2970-2971. |
| 감독 결정 ② 4단계 분할, 본 SPEC = 1단계 | 반영됨 · 누수 0 | Out of Scope "2~4단계"(spec.md:106-111) — `Store Group`·`Store Preset`·시퀀스 코드 0건 명시. spec.md 본문에 2~4단계 동작을 요구하는 REQ 없음. plan.md §E(:130-136) ID 예약만. |
| 감독 결정 ③ 점유 슬롯 불가침 — 기계적 명세 | 반영됨 | REQ-006(spec.md:68) 행 단위 DMX(`occupants_from_patch_values` + 구간 안 시작 규약) + FID(`read_existing_fids`) 선별 **런 생성 전** · REQ-007(:69) 전수 아니면 런 0 · REQ-012(:77) 재실행 멱등 · AC-007/008/013. 근거 코드 실측: `patch_fixtures`는 `fids` 명시 시 검증 없이 그대로 싣는다(tools.py:4039-4041 확인) → 매퍼 선별이 필수라는 spec.md:39 주장 **참**. `address_not_free`는 런 단위(tools.py:3820-4340 status 집합에서 확인). |
| 입력 데이터 실물 | 실물 일치 · **경로 결함** | 절대경로 파일 실측: BOM `EF BB BF` · 헤더 9열 정확 · 86행 · 타입 8종 · 그룹 12종(KEY6 FOH8 BLIND6 STROBE4 HAZE2 MOVER-U8 MOVER-D8 BACK12 SIDE-L6 SIDE-R6 WASH-U10 WASH-D10) · en-dash 86행 · 첫 행 `101,KEY,…,12,1,1` · 마지막 `430,…,5,322` · FID 202=4.026 · 301=4.301 · 501=2.001 · 504=2.118 · 521~528=3.001~ · 최대 FID 622. **그러나** `src/Lighting_Designer/`는 주 체크아웃(`/Users/studiox/Documents/Claude/Code/AI-Lighting_Console`)에 **미추적**(`git status` → `?? src/Lighting_Designer/`)이고 감사 대상 워크트리(`…/orca/workspaces/AI-Lighting_Console/LX-SEQ`)에는 **존재하지 않는다**(D2). |
| 기존 툴 계약(research.md 요약 불신, 코드 직접 판독) | 일치 | `resolve_fixture_type` 3408 · `resolve_patch_address` 3630 · `patch_fixtures` 3820 · `precheck_patch` 2649 · `vectorworks_autopatch` 2923 · `precheck_vectorworks_diff` 2821(`file_content_base64` b64decode validate=True :2830-2836) · ToolDefinition 7437/7476/7525 · handlers 8800(항목 `patch_fixtures` 8817) · `TOOL_NAMES` 226, **33개** · test_tools.py:172 `== 33` · test_architecture.py:48. `patch_fixtures` 인자 스키마 `console_type/console_mode/address/count/channels_per_fixture/fids/name_prefix/plugin_name`, required 3, additionalProperties False — REQ-008 런 인자와 일치. status 집합(`address_not_free/fids_unknown/footprint_unknown/mode_choice_needed/mode_not_chosen/mode_not_found/not_deployed/not_run/unverified` + `judge_staged_patch` 판정 `created/created_partially/created_nothing`) — REQ-010 나열과 일치. `resolve_fixture_type` status `present/ambiguous/absent/library_unreadable` + `awaited_human` + `wait_for_library_addition` 확인. 헬퍼: addressfit.py:86 `occupants_from_patch_values` · :137 `evaluate` · :72 `blind_spot` · :179 `first_free`(tools.py:147에서 `first_free_address`로 alias) · patchplan.py:1395 · mode_read.py:76(`type_found` 필드) · inventory.py:344 · librarywatch `read_snapshot`(tools.py:163에서 `read_library_snapshot` alias) · `CONSOLE_READ_INCOMPLETE` = server/vwx/verdicts.py:81 · session.py:9655/9658. 2026-08-18 라이브 주석 tools.py:4120-4132 실존. 드리프트: research.md:92가 `console_read_caveat`를 inventory.py 행에 두었으나 실제는 server/vwx/apply.py:672(O3). |
| spec/plan/acceptance 수치·ID·파일 목록 일관성 | 일치 | REQ 15 · AC 16 · M 5 · 마커 3 · 결정 7 · ASSUMPTION 72~74 · 툴 33→34 — spec HISTORY(:28) · plan(:5) · acceptance(:3) · progress §E.1(:90-95) 전부 동일. 파일 목록 plan §G "9파일(신규 3 + 테스트 3 + fixture 1 + 수정 2)" = M1~M3 파일 합. |
| `[NEEDS CLARIFICATION]` 배치 | 규약 준수 · **MP-7 FAIL** | plan.md 3건(본체) · research.md 언급 2 · spec/acceptance 0. 배치는 맞으나 감사 시점 미해소 → MP-7. |
| progress.md 골격 | 적합 | §E.1 초안(:79-98, `plan_status: draft`, `base_sha: 453846a`, baseline 실측 문구) · §E.2~E.4 pending · §F 자리(:112-114). §0 인수인계의 기계 확인 명령(:31-37) 중 `tail … src/Lighting_Designer/… -> 86`은 **이 워크트리 cwd에서는 실패**한다(D2와 동일 원인; 실행 cwd가 명시돼 있지 않아 증거 귀속이 불완전). |
| 미검증 전제(콘솔 동작을 사실로 서술) | 1건 주의 | spec.md:38 "60→62 생성 확인" · :42 "`ChangeDestination` 전부 Failed" → tools.py:4120-4132 주석(실측 기록)으로 뒷받침. spec.md:22 "그룹 멤버십은 `query_state`로 읽을 수 없어" → research.md:120이 `[메모리]` "(코드 밖 관측)"으로 표기 — 감독 결정의 인용문이라 허용하되, spec 본문 사실 진술로 읽히므로 출처 표기 권고(O6). ASSUMPTION-72~74는 전제로 올바르게 분리됨. plan.md:46 "원본은 `src/Lighting_Designer/` 아카이브에 그대로" — 저장소 아카이브가 아니라 **미추적 로컬 디렉터리**(D2). |

---

## Defects Found (structured defect-list)

D1. **MP7-CLARIFICATION-GATE** — plan.md:50, :51, :52 — `[NEEDS CLARIFICATION: 입력 채널]` · `[… 픽스처 이름 접두]` · `[… 모드 미해결 시 처리]` 3건 미해소 — Severity: **critical** — Class: **blocking**(해소 주체 = 오케스트레이터) — Required fix: Implementation Kickoff Approval 전 `ToolSearch(select:AskUserQuestion)` → `AskUserQuestion` 3라운드(각 기본안에 `(권장)` 라벨: ① `file_content_base64` 인자 ② `name_prefix_mode="group"` ③ `console_mode` 생략·카드 위임)로 답을 받아 plan.md §A.4 마커를 결정문으로 치환하고 `progress.md` M0 절에 기록. ②의 답은 D5·D6과 연동된다.

D2. **INPUT-PATH-NOT-IN-TREE** — spec.md:43, :167 · acceptance.md:78-79(AC-LXSEQ-001 ②③) · plan.md:46, :75 · progress.md:37 · research.md:25 — 입력 정본 경로 `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv`가 **감사 대상 워크트리에 존재하지 않는다**(`ls src/Lighting_Designer` → No such file). 주 체크아웃에만 있고 그마저 **git 미추적**(`?? src/Lighting_Designer/`). AC-001 ②(`sha256sum` 두 경로) ③(`tail … | wc -l`)과 M0의 "복사" 지시가 run-phase cwd(워크트리)에서 실행 불가. progress.md:37의 "→ 86"은 다른 cwd에서 얻은 값이라 증거 귀속(VCI §2)이 불완전 — Severity: **major** — Class: **blocking** — Required fix: (a) M0 파일 목록에 정본의 **절대경로**(`/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/Lighting_Designer/02_RIG팩/…`)를 적고 AC-001 ②③을 그 경로 + 사본 경로로 고치거나, (b) 입력 디렉터리를 커밋해 두 트리에서 같은 상대경로로 풀리게 한다. 어느 쪽이든 "원본은 아카이브에 그대로"(plan.md:46) 문구를 "미추적 로컬 정본 — 사본의 sha256이 계약"으로 정정. 진행 기록의 기계 확인 명령에는 실행 cwd를 명시.

D3. **AC003-OVERLAP-ARITHMETIC** — acceptance.md:106(AC-LXSEQ-003 ④) — "FID 104 행의 `Address`를 `40`(103과 겹침)으로 바꾸면 `address_overlap_in_file` 2건(103·104)". 실물: 103 = 1.025–036, 104 = 1.037–048, 105 = 1.049–060. 104를 40으로 옮기면 구간 40–51은 **105**(49–60)와 겹치고 103(25–36)과는 겹치지 않는다. 기대값대로 단언하면 올바른 구현이 RED — Severity: **major** — Class: **blocking** — Required fix: "`Address`를 `30`으로 바꾸면 103·104 2건" 또는 "`40`이면 **104·105** 2건"으로 정정(둘 중 하나, 실물 CSV로 재계산).

D4. **AC011-K-SELECTOR-VACUOUS** — acceptance.md:201(AC-LXSEQ-011 검증 방법) — `uv run pytest server/tests/test_tools.py -q -k "closed or thirty"`를 이 트리에서 실행하면 **`no tests collected (71 deselected)`**. 실제 테스트명은 `TestRegistry::test_the_registered_tools_are_exactly_the_declared_set`(test_tools.py:122)이고 "closed"·"thirty" 토큰이 없다. 게이트가 공허 통과(또는 exit 5로 `&&` 체인 중단) — Severity: **major** — Class: **blocking** — Required fix: `-k "registered_tools_are_exactly_the_declared_set"`(또는 `-k TestRegistry`)로 교체하고, 이 명령이 ≥1건 수집함을 ①의 비공허성 단언에 포함.

D5. **REQ008-VS-OPEN-DECISION** — spec.md:70(REQ-LXSEQ-008) ↔ plan.md:19, :51(§A.1-3 · §A.4-②) ↔ acceptance.md:179(AC-009 ①) — REQ-008은 런 경계를 "(확정 콘솔 타입, 모드 해석 결과, 유니버스, **`Group`**)"로 **확정**하고 "런 12개"를 요구로 못박는다. 그런데 plan은 `Group` 포함 여부를 Kickoff에서 닫을 **열린 결정**으로 두고, AC-009 ①은 "둘 다 코드 상수로 고정"으로 양다리를 걸친다. 사용자가 타입 접두(대안)를 고르면 REQ-008 문면과 spec.md:34 "런 12개"가 그대로 위반된다 — Severity: **major** — Class: **blocking** — Required fix: D1-②의 답에 따라 REQ-008을 닫든지(Group 확정 → AC-009 ①의 대안 분기 삭제), 아니면 REQ-008을 `name_prefix_mode`에 매개변수화("`name_prefix_mode=group`이면 `Group`을 경계에 포함, `type`이면 제외")하고 spec.md:34·HISTORY의 "12런" 수치를 조건부로 고친다.

D6. **AC009-ALT-RUN-COUNT** — acceptance.md:179(AC-LXSEQ-009 ①) · plan.md:51 — "타입 접두 결정이면 **10**런". 실물 CSV로 REQ-008 규칙(타입·모드·유니버스 동일 + 주소 연속)을 `Group` 없이 계산하면 KEY+FOH(1.001–168) · BACK+SIDE-L(4.001–325) · **WASH-U+WASH-D(5.151–330, 같은 RUSH PAR 9ch·연속)** 3쌍이 합쳐져 **9**런이다(86행 직접 계산). 10은 WASH 병합을 빠뜨린 값 — Severity: **major** — Class: **blocking** — Required fix: 10 → 9로 정정(D5 처리 후 대안 분기가 남는 경우). 계산 근거를 acceptance에 한 줄로 남긴다.

D7. **AC007-BLINDSPOT-EXAMPLE** — acceptance.md:157(AC-LXSEQ-007 ④) — "구간 **앞**에서 시작해 뻗는 장비(`1.510` 폭 미지)는 잡지 않고" — FID 501의 구간은 **2**.001–039다. `1.510`은 유니버스 1이라 U2 구간과 무관하고, 어차피 2.001 앞에서 시작하는 주소는 존재하지 않아 이 행으로는 블라인드스팟 예시를 만들 수 없다 — Severity: **minor** — Class: **blocking**(기대값이 물리적으로 불성립) — Required fix: 구간 앞이 있는 행으로 바꾼다 — 예: FID 502(2.040–078)에 대해 `2.030`(폭 미지) 점유자는 `address_occupied`로 잡히지 않고 `blind_spot` 문구만 동봉.

O1. REQ-LXSEQ-013 — spec.md:78 — `[Where]` 태그이나 내용은 사건("핸들러가 질문 카드로 요청하면") — Severity: minor — Class: optional — Fix: `[Event-driven] When`으로 재태깅.
O2. REQ-LXSEQ-015 — spec.md:80 — `[Ubiquitous]`이나 본문은 금지형 — Severity: minor — Class: optional — Fix: `[Unwanted] shall not`로 재구성(허용 변경 2건을 예외절로).
O3. research.md:92 — `console_read_caveat(inventory)`를 inventory.py 행에 기재했으나 실제 위치는 `server/vwx/apply.py:672` — Severity: minor — Class: optional — Fix: 좌표 정정(M0 드리프트 대조에서 잡힘).
O4. REQ-LXSEQ-010/011 — spec.md:75-76 — `only_fids`로 제외된 행의 보고 부류가 닫힌 어휘 8종에 없음 — Severity: minor — Class: optional — Fix: `not_selected` 추가하거나 "제외 행은 `skipped`가 아니라 `source.excluded`에 싣는다"로 명시.
O5. REQ-LXSEQ-002/011 — spec.md:61, :76 — `universe_overflow`가 행 거부 부류(rejected)와 건너뛰기 어휘(skipped) 양쪽에 등장 — 어느 목록에 실리는지 모호 — Severity: minor — Class: optional — Fix: skipped 어휘에서 제거(파서 거부로 일원화).
O6. spec.md:22 — "그룹 멤버십은 `query_state`로 읽을 수 없어" — research.md:120이 `[메모리]`·코드 밖 관측으로 분류한 주장을 spec 본문이 사실로 서술 — Severity: minor — Class: optional — Fix: "(라이브 관측 2026-xx, 메모리 `grandma3-group-membership-not-readable`)" 출처 병기.
O7. REQ-LXSEQ-010 — spec.md:75 — plan.md:42 결정 C("`apply`가 내부에서 계획을 다시 만든다")가 spec 요구에 없음(preview→apply 사이 콘솔 변화 TOCTOU) — Severity: minor — Class: optional — Fix: REQ-010에 "`apply`는 호출 시점에 점유 판정과 계획을 새로 계산하며 이전 `preview` 결과를 받지 않는다" 한 문장 추가.
O8. AC-LXSEQ-015 ③ — acceptance.md:254 — "리뷰로 확인"은 판단 호출 — Severity: minor — Class: optional — Fix: `git diff <BASE>..HEAD -- server/orchestrator/tools.py | grep -c '^-[^-]'` ≤ N(등재 편집으로 허용되는 삭제 줄 수 상한)으로 수치화.

---

## Must-fix list (재감사 진입 조건)

1. **D1** — 오케스트레이터: `AskUserQuestion` 3라운드로 plan.md §A.4 마커 3건 해소 → plan.md 결정문 치환 + progress.md M0 기록.
2. **D2** — manager-spec: 입력 정본 경로를 워크트리에서 풀리는 형태(절대경로 또는 커밋)로 고치고 AC-LXSEQ-001 ②③·plan M0·progress §0 명령을 정정, "아카이브" 문구 정정.
3. **D3** — manager-spec: AC-LXSEQ-003 ④ 겹침 예시 재계산.
4. **D4** — manager-spec: AC-LXSEQ-011 `-k` 선택자를 실존 테스트명으로 교체.
5. **D5 + D6** — manager-spec: D1-②의 답에 맞춰 REQ-LXSEQ-008을 닫거나 매개변수화; 대안 분기가 남으면 "10런"을 "9런"으로 정정(spec.md:34·:70, plan.md:51, acceptance.md:179).
6. **D7** — manager-spec: AC-LXSEQ-007 ④ 블라인드스팟 예시를 구간 앞이 존재하는 행으로 교체.

Optional O1~O8은 오케스트레이터 재량(M6 — 다수의 optional이 FAIL 근거가 되지는 않는다).

---

## Regression Check

Iteration 1 — 해당 없음.

---

## Recommendation

**FAIL — 재감사는 D1~D7 델타 범위로 한정한다.** 구조(프런트매터 12/12, REQ 연속 15, GEARS 형식, Out of Scope H3 5개, REQ↔AC 15/15, 감독 결정 ①②③의 요구 반영, 쓰기 경로 단일화, 행 단위 점유 선별의 기계적 명세)는 전부 증거로 확인되었고, 기존 툴 계약 서술은 `tools.py` 본문과 일치한다(`fids` 무검증 4039-4041 · 런 단위 `address_not_free` · status 집합 · ToolDefinition 스키마 · 2026-08-18 라이브 주석). 판정을 가른 것은 두 가지다. 첫째, plan.md의 `[NEEDS CLARIFICATION]` 3건은 규약상 점수와 무관한 must-pass(MP-7)이며 Kickoff 전 오케스트레이터의 AskUserQuestion으로만 닫힌다. 둘째, 인수 기준 5건(AC-001·003·007·009·011)의 검증 명령·기대값이 이 트리에서 실행 불가이거나 실물 CSV와 맞지 않아(입력 디렉터리가 워크트리에 없고 git 미추적, 겹침 산술 오류, `-k` 0건 수집, 대안 런 수 10≠9, 유니버스 불일치 예시), 그대로 run-phase에 넘기면 올바른 구현이 RED가 되거나 게이트가 공허 통과한다. 모두 한두 줄 수정이며 설계 변경은 없다. 마커 3건을 닫고 D2~D7을 고친 뒤 델타 재감사를 요청하면 PASS 밴드(0.9 이상)가 예상된다.

---

## Iteration 2 (delta)

Iteration: 2/3 · 범위: 1회차 must-fix D1~D7 델타 + 회귀 확인(O1·O2·O3·O8, 카운트 일관성, 단계 누수, 쓰기 경로, 마커, progress 골격, 작업 트리 변경 범위) + **감사 도중 착지한 v0.2.1(문서 전용 개정: UI 전달 경로 t10 위임 · M4 "직접 호출")까지 포함**
Verdict: **FAIL** (must-pass 7/7 통과 · 점수 임계 이상 · 1회차 D1~D7 전부 해소 — 그러나 v0.2.1이 새로 넣은 입력 채널 문장이 REQ-010/AC-017 ①의 닫힌 인자 집합과 **모순**(N1, blocking) → 1문장~2문장 수정 후 3회차 델타 재감사 대상)
Overall Score: **0.88** (조화평균 — Clarity 0.75 · Completeness 0.95 · Testability 0.85 · Traceability 1.00; Tier M 임계 0.80; 1회차 0.86 → 상승, 회귀 없음 → STOP 신호 없음)
감사 대상: HEAD `453846a` · 브랜치 `jjjh7401/LX-SEQ` · 미커밋(아티팩트 6종 + fixture 1 전부 untracked) · 최종 감사 대상 md5(13:54 v0.2.1): spec `1ef49dbb…` · plan `d45d8293…` · acceptance `e59a6978…` · research `09b1a6a3…` · progress `54d80d66…`. (감사 시작 시점 v0.2.0 md5 `75613a2c…/4e9f1afd…/d40dc688…/462bb54f…/632f5773…`에서 D1~D7 판정을 마친 뒤 v0.2.1 변경분을 추가로 읽어 판정을 갱신했다. 리드 요청 1줄 편집 2건 — acceptance AC-016 "기계 로컬(CI 대상 아님)" · plan §E 블록인용 — 포함.)
M1 Context Isolation: 작성자의 "변경 주장"은 가설로만 취급하고 파일·코드·CSV 실물로 전부 재검증했다.

### Must-Pass (재확인, v0.2.1 기준)

- [PASS] **MP-1** `grep -oE 'REQ-LXSEQ-[0-9]{3}' spec.md | sort -u | wc -l` → 16, 001~016 연속·중복 0.
- [PASS] **MP-2** 16건 전부 GEARS 태그+구조: Ubiquitous 8 · Event-driven 3(002·007·**013** — O1 적용) · Unwanted 4(003·009·**015** — O2 적용·**016** 신설 `[Unwanted] The 툴 shall not …`) · While 1(012). 판정 계층 = spec.md REQ; acceptance.md AC는 Given-When-Then(감점 대상 아님).
- [PASS] **MP-3** 12필드 존재(spec.md:2-13), `version: "0.2.1"`(HISTORY 0.2.1 행 존재), `tier: M`. `mcp__moai__spec_audit` → INFO만(era 자동판정 · 문서 머리 "draft (v0.1.0 …)" 쓰기 시점 캡처), 차단 0.
- [N/A] **MP-4** Python 단일 언어.
- [PASS] **MP-5** D7 verb: `SPEC-COPILOT-AUTOPATCH-001 status=draft` · `SPEC-COPILOT-MVP-001 status=in-progress` · `SPEC-COPILOT-PRECHK-001 status=completed` · `SPEC-COPILOT-VWX-001 status=draft` → BLOCKING 0.
- [PASS] **MP-6** `grep -c syscall spec.md` → 0.
- [PASS] **MP-7** `grep -c 'NEEDS CLARIFICATION' {spec,plan,acceptance,research}.md` → `0 0 0 0`; `grep -rn '\[NEEDS CLARIFICATION' <SPEC dir>` → 본 보고서 1회차 본문에서만 매치. progress.md의 1건은 마커가 아니라 확인 명령 문자열.

### 카테고리 점수

| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.75 | 0.75 | 결정 H·I·J는 spec/plan/acceptance/progress 4곳에서 같은 문장으로 닫혔다. 감점: **(N1)** v0.2.1 REQ-010(spec.md:77)·REQ-016(:83)·AC-016(acceptance.md:284)·AC-017 주(:269)·plan.md M4(:111)·research.md §6-6(:134)가 "현재 절차: 툴을 **직접 호출(채팅/스크립트)하며 파일 경로를 지정**하고 **서버가 파일을 읽어** `file_content_base64`를 구성한다"를 쓰는데, 같은 REQ-010과 AC-017 ①은 인자 집합을 `{file_content_base64(필수), action, name_prefix_mode, only_fids, mode_overrides}` · `additionalProperties == False`로 닫아 둔다 — 경로를 받을 인자가 없고(`tools.py`에 로컬 파일을 읽는 핸들러도 0건: `grep -c 'open(' server/orchestrator/tools.py` → 0, `"path"` 인자는 `query_state`의 콘솔 오브젝트 트리 경로뿐 :6790), "채팅으로 직접 호출해 경로 지정"은 모델이 파일 바이트를 얻을 수단이 없어 성립하지 않는다. 두 독법 모두 문제: (가) 새 인자 `file_path`를 암시 → REQ-010 인자 목록·AC-017 ① 키 집합과 모순, 서버 임의 경로 읽기라는 **새 입력 채널**(감독 답 ①은 세션 포트 재사용·신규 엔드포인트를 기각했고 경로 읽기는 결정된 바 없음) (나) "스크립트"가 파일을 읽어 base64를 핸들러에 넘긴다 → "서버가 읽는다"·"채팅" 문구가 틀리고, 그 스크립트의 소재·소유(M4는 "코드 변경 0")가 미정의. (R1) REQ-008은 `Group` 포함을 무조건으로 쓰고 REQ-010/AC-009 ①-b는 `type` 경로에서 제외(9런) — 조건절 부재(plan.md §A.1 행 3이 의미를 풀어 둠). (기존) REQ-005 토큰 분할 규칙 미정의. |
| Completeness | 0.95 | 1.0 | 1회차와 동일(O4 미적용). REQ-016/AC-017 신설로 결정 H의 금지 조항이 요구·검증 양 계층에 들어갔다. |
| Testability | 0.85 | 0.75~1.0 | 1회차에 깨져 있던 AC 5건(001·003·007·009·011)이 전부 이 트리에서 실행 가능·기대값 실물 일치(아래 D2~D7 표). 감점: AC-016 "현재 절차" 문장이 존재하지 않는 메커니즘을 전제(N1) — 절차대로 수행 불가. minor 2건: (R2) AC-009 ①-b의 BACK+SIDE-L 병합 구간 `4.001–325`는 실물 `4.001–450`(12×25 + 6×25; 18대·9런 수치는 맞고 구간은 단언 대상 아님) · (R3) 시나리오 5·AC-006 ③이 `Robe Spiider`에 25ch 모드 둘+`Extended 25ch`를 두나 실물 Spiider는 `Mode 1 49ch`/`Ch=49`(`Extended 25ch`는 MAC Aura XB 24행) — 문자 그대로 테스트해도 RED는 아니나 "동폭 둘·토큰 불가" 분기가 MOVER-D에서 실행되지 않는다(②의 합성 Ch=25 예가 그 분기를 덮어 뮤테이션 킬은 유지). |
| Traceability | 1.00 | 1.0 | 역추적표 REQ 16/16(acceptance.md §C.0) · AC 17(`^### AC-LXSEQ-` 001~017) · §C.0a 1+3+6+6+1=17 · plan.md 마일스톤 `- **AC**:` 5줄 합 17 중복 0 · progress §E.1 `requirements: 16`/`acceptance_criteria: 17` · spec HISTORY 0.2.0/0.2.1 — 전부 일치. |

### D1~D7 델타 판정표 (명령 + 출력 그대로)

| 항목 | 판정 | 증거(명령 → 출력) |
|---|---|---|
| **D1** 마커 3건 | **RESOLVED** (단, ①의 v0.2.1 후속 문장이 N1을 낳음) | `grep -c 'NEEDS CLARIFICATION' spec/plan/acceptance/research.md` → `0 0 0 0`. plan.md §A.3 결정 H·I·J(L49-51) + §A.4 기각안/잔여 메모(L53-59). progress.md "M0 — Kickoff 결정 기록" 표 ①②③ 기재 → AC-LXSEQ-001 ⑤ 요건 충족. ③ **비기본(대안) 채택** 명시(plan.md:23·51·59, progress 표, spec HISTORY). ① → REQ-LXSEQ-016 `[Unwanted]` + AC-LXSEQ-017 신설(spec.md:83, acceptance.md:266-277). ② → REQ-010 기본값 `"group"`(spec.md:77). ③ → REQ-005 `mode_unresolved`/`mode_overrides`(spec.md:69), REQ-010 인자·REQ-011 어휘, `ModeResolution`(spec.md §E), AC-006 ③/③-b/④/⑥. |
| **D2** 입력 경로 | **RESOLVED** | `ls -la server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` → `-rw-r--r--@ … 7258 Aug 21 13:45`; `shasum -a 256` → `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3`; `tail -n +2 … \| wc -l` → `86`; `head -c 3 \| xxd` → `efbb bf`; 헤더 → `FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position`. 정본(주 체크아웃 절대경로) `shasum -a 256` → **동일 해시**(7258 B) — "정본과 동일" 실측 참. `ls src/Lighting_Designer`(워크트리) → `No such file or directory`. `grep -n "src/Lighting_Designer\|/Users/studiox" acceptance.md` → **284행(AC-016 라이브)만**. AC-001 ② `test -f … \|\| { echo FAIL…; exit 1; }` 명시적 FAIL. plan.md 결정 G "git 미추적 로컬 정본"(아카이브 문구 정정). progress.md §0 명령이 사본 경로(L37-39). |
| **D3** AC-003 ④ | **RESOLVED** | 실물 CSV 재계산: 103=`1.025–036` · 104=`1.037–048` · 105=`1.049–060`; 104 `Address=40` → 겹침 쌍 `[(104, 105)]`(기본 `[]`). acceptance.md AC-003 ④ "**104·105** 둘 다, 103은 정상" 일치. |
| **D4** AC-011 선택자 | **RESOLVED** | `uv run pytest server/tests/test_tools.py --collect-only -q -k test_the_registered_tools_are_exactly_the_declared_set` → `server/tests/test_tools.py::TestRegistry::test_the_registered_tools_are_exactly_the_declared_set` / `1/71 tests collected (70 deselected) in 0.16s`(exit 0). 구 선택자 `-k "closed or thirty"` → `no tests collected (71 deselected)`. 뮤테이션(스크래치 사본 `== 33`→`== 34`; 저장소 무변경 — `git status --short -- server/tests/test_tools.py` 빈 출력) → `test_tools_mut.py:172: AssertionError … 1 failed, 70 deselected` → 선택자가 단언에 닿는다(RED). AC-011 ①에 "수집 0건이면 FAIL" 비공허성 포함. |
| **D5** REQ-008 vs 열린 결정 | **RESOLVED(핵심) · 잔여 R1** | 감독 답 ② `group` → REQ-008 문면("…`Group`… 런 12개")이 결정과 일치, 본문 무변경. REQ-010 기본값 `"group"`. AC-009 ① "단언값 고정" 12. 잔여 R1: `type` 경로 조건절 부재(Clarity 감점). |
| **D6** 대안 런 수 | **RESOLVED** | 실물 CSV 재계산(타입·모드·유니버스 동일 + 주소 연속, `Group` 제외) → **9**; `Group` 포함 → **12**(정렬 순서 무관). 병합 3쌍 KEY+FOH(14대·1.001–168) · BACK+SIDE-L(18대) · WASH-U+WASH-D(20대·5.151–330). plan.md:21·50·58 · acceptance.md AC-009 ①-b · research.md:29 전부 **9**. (구간 문구 `4.001–325`만 오기 — R2, 실물 `4.001–450`; 이 숫자는 1회차 D6 서술에서 **감사자가 잘못 적은 것**을 작성자가 옮긴 것이다.) |
| **D7** AC-007 ④ | **RESOLVED** | CSV: FID 502 = `2.040–078`(MegaPointe 39ch). 실코드 `from server.vwx import addressfit as af; af.evaluate("2.040", count=1, width=39, occupants=af.occupants_from_patch_values([("2.030","X","TypeX")]))` → `ok=True · collisions=0 · blind_spot="구간보다 앞에서 시작해 뒤로 뻗어 들어오는 장비는 잡지 못한다 — …"`; 대조군 `2.050` → `ok=False · collisions=1`; 구간 안 `2.020`(FID 501 구간) → `ok=False · collisions=1`. AC-007 ④ 기대값 전부 일치. |

### 회귀 확인 (1회차 optional + 교차 축)

- O1 REQ-013 `[Event-driven] When` ✔ · O2 REQ-015 `[Unwanted] shall not`+예외 2건 ✔ · O3 research.md §3 `console_read_caveat` → `server/vwx/apply.py:672` ✔(`grep -rn "def console_read_caveat" server/` → `server/vwx/apply.py:672`) · O8 AC-015 ③ `grep -c '^-[^-]'` ≤ 3 + 줄 목록 기록 ✔. O4~O7 미적용(작성자 명시, 재량).
- 카운트 일관성: spec HISTORY(0.2.0·0.2.1) · plan.md:5 · acceptance.md:3·57·69 · progress.md §0·§E.1 → REQ 16 · AC 17 · M 5 · 결정 10 · 마커 0 전부 동일. plan.md 마일스톤 AC 배정 = acceptance §C.0a 1:1(M3에 017).
- 단계 2~4 누수 0: spec.md의 `Store Group/Preset`·시퀀스·큐 언급은 phase 필드·감독 결정 인용·"하지 않는 것" 표·Out of Scope H3에만, REQ 본문 0건. plan.md §E 블록인용(그룹 12 vs README 18)은 "범위 밖·조사하지 않음" 명시 — README 실물 `그룹 18` 확인, 주장 참.
- 신규 콘솔 쓰기 동사 0: REQ-009 금지 목록 유지, REQ-010 `apply` = `patch_fixtures` 내부 `ToolCall` 위임, REQ-016 "세션 업로드 포트 재사용·신규 엔드포인트 둘 다 안 함". 코드 대조: `session.py:9655 upload_vectorworks_export` → `:9658 run_instruction(_VECTORWORKS_UPLOAD_INSTRUCTION)` · `build_toolset(… vectorworks_upload …)` tools.py:1605 · `precheck_vectorworks_diff` `b64decode(validate=True)` tools.py:2830-2836 · `patch_fixtures` ToolDefinition `console_mode` 속성 존재 · `mode_read.TypeModeRead.type_found`(mode_read.py:57) · `ui/src/App.tsx` FileReader 2곳 · `protocol.ts buildVectorworksExportUpload/buildLayoutImageUpload` · `grep -rn file_content_base64 ui/src` → 0 — research §4/§6-6 주장 전부 참.
- progress.md: §E.1 초안(`plan_status: draft`, `spec_version: "0.2.1"`, `base_sha: 453846a`, 16/17/5/10/0) ✔ · §E.2~E.4 pending ✔ · §F 자리 ✔ · v0.2.1 로그 절 추가.
- 작업 트리: `git status --short --untracked-files=all -- server ui` → `?? server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` **1건만**. 그 밖 `M CLAUDE.md`·`.claude/`·`.moai/` 규칙 변경은 본 SPEC 무관.
- 잔여 우려 #1(UI 파일 선택기 → `file_content_base64` 전달 경로 부재): 범위 밖 처리 자체는 **plan-phase 수용 가능**(v0.2.1에서 후속 카드 t10으로 위임 — 감독 판정 기록). **그러나** 그 자리를 메운 "직접 호출 + 서버 파일 읽기" 문장이 N1을 만든다 — 판정은 아래.

### Defects Found (iteration 2 — 신규/잔여)

N1. **M4-INPUT-MECHANISM-CONTRADICTION** — spec.md:77(REQ-010 "현재: 직접 호출로 지정한 경로를 서버가 읽음") · :83(REQ-016 "툴을 직접 호출하며 파일 경로를 지정하고 서버가 파일을 읽는 것") · acceptance.md:269(AC-017 주) · :284(AC-016 "서버가 파일을 읽어 `file_content_base64`를 구성") · plan.md:22·49·111·156·165 · research.md:110·134 · progress.md §0 — 툴의 닫힌 인자 집합(REQ-010, AC-017 ①: 5키 · `file_content_base64` 필수 · `additionalProperties False`)에는 경로 인자가 없고, `tools.py`에 로컬 파일을 읽는 핸들러도 없다(`open(` 0건; `"path"` 인자는 `query_state` 콘솔 트리 경로). "채팅 직접 호출로 경로 지정"은 모델이 바이트를 얻을 수단이 없어 불성립. 새 인자(`file_path`)라면 REQ-010/AC-017 ① 모순 + 감독이 결정하지 않은 **서버 임의 경로 읽기 채널** 신설; 스크립트라면 "서버가 읽는다"가 거짓이고 스크립트의 소재·소유 미정의(M4 "코드 변경 0") — Severity: **major** — Class: **blocking**(내부 모순 + 입력 채널 결정 범위 이탈 가능성) — Required fix(둘 중 하나, 한두 문장): **(가·권장, 설계 변경 0)** "현재 절차(t9): 로컬 하네스 스크립트(예: `server/tests/fixtures/lxseq/` 옆 또는 스크래치, `build_toolset` 가짜 포트 패턴의 실포트 버전)가 정본 경로의 파일을 읽어 base64로 `file_content_base64`를 채워 핸들러를 호출한다 — 서버는 경로를 받지 않고 읽지도 않는다; 채팅 호출은 t10 이후"로 REQ-010·REQ-016·AC-016·AC-017 주·plan M4/§A.1/§F/§G·research §4/§6-6·progress §0을 통일하고, 그 스크립트의 파일명·소유(M4 산출물, 커밋 여부)를 M4 파일 줄에 적는다. **(나)** 정말로 서버가 경로를 읽게 하려면 감독 승인 후 REQ-010 인자에 `file_path`(택1 필수 — `file_content_base64`와 상호배타)를 명시하고 AC-017 ① 키 집합·`required`를 고치며 경로 제한(허용 디렉터리·심볼릭 링크·존재 검증)을 REQ에 추가한다. 어느 쪽이든 "둘은 충돌하지 않는다"는 문장은 메커니즘을 적은 뒤에만 참이 된다.
R1. **REQ008-TYPE-PATH-CLAUSE** — spec.md:72(REQ-008) ↔ :77(REQ-010 `name_prefix_mode ∈ {"group","type"}`) ↔ acceptance.md AC-009 ①-b(9런) — REQ-008 문면은 `Group`을 무조건 경계에 포함하고 "런 12개"를 요구, `type` 경로는 `Group` 제외 9런 — Severity: minor — Class: blocking(내부 일관성; 기본 경로 영향 0, plan.md §A.1 행 3이 의미 명시) — Fix: REQ-008에 "`name_prefix_mode="type"`이면 `Group`을 경계에서 제외(실물 CSV 9런)" 1문장, 또는 `type` 옵션을 REQ-010·AC-009 ①-b에서 제거.
R2. **AC009-ALT-SPAN-TEXT** — acceptance.md AC-009 ①-b · plan.md:58 · research.md:29 — "BACK+SIDE-L(4.001–325)" → 실물 **`4.001–450`**(BACK 12×25=4.001–300 + SIDE-L 6×25=4.301–450). 18대·9런은 맞음, 구간은 단언 대상 아님 — Severity: minor — Class: optional — Fix: 세 곳 `325`→`450`. (출처: 1회차 D6 감사 문안의 오기 — 감사자 귀책.)
R3. **AC006-SPIIDER-WIDTH** — acceptance.md 시나리오 5 · AC-006 ③/③-b/⑥ — `Robe Spiider`에 25ch 모드 둘·`Mode="Extended 25ch"`를 두나 실물 Spiider는 `Mode 1 49ch`/`Ch=49`(`Extended 25ch`는 MAC Aura XB) — 문자 그대로 테스트해도 RED는 아니나 "동폭 둘·토큰 불가" 분기가 실물 행에서 실행되지 않음 — Severity: minor — Class: optional — Fix: ③ 목록을 `[("A",49),("B",49)]`·`Mode="Mode 1 49ch"`로(또는 타입을 MAC Aura XB·`Ch=25`·24행으로).
R4. **O4~O7 미적용** — 1회차 optional 그대로(재량). Class: optional.
R5. **STRAY-STATE-DIR** — `.moai/specs/SPEC-COPILOT-LXSEQ-001/.moai/state/{config-cache,context-usage,github/counts}.json` + 빈 `.claude/` — SPEC 디렉터리 cwd에서 moai가 돈 흔적(`.gitignore:248`에 가려짐) — Severity: minor — Class: optional — Fix: 삭제.
R6. **FIXTURE-UNTRACKED** — `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` untracked — plan/spec이 "plan-phase 커밋에 포함"이라 서술하므로 plan 커밋 시 **명시적 pathspec**으로 함께 `git add`(스윕 금지). Class: optional(절차 메모).

### Regression Check (1회차 결함)

- D1 — RESOLVED(v0.2.1 후속 문장이 N1 유발) · D2 — RESOLVED · D3 — RESOLVED · D4 — RESOLVED · D5 — RESOLVED(핵심; 잔여 R1) · D6 — RESOLVED · D7 — RESOLVED. 1회차 결함 미해결 0, 정체(stagnation) 0. 점수 0.86 → 0.88(회귀 없음).

### Remaining must-fix (3회차 재감사 진입 조건)

1. **N1** — manager-spec: M4 입력 전달 메커니즘을 닫힌 인자 집합과 모순 없이 한 가지로 적는다(권장 (가): 로컬 하네스 스크립트가 읽어 base64 전달, 서버는 경로를 받지 않음; "채팅 직접 호출" 문구 삭제; 스크립트 소재·소유를 M4 파일 줄에 기재). 영향 파일: spec REQ-010/REQ-016 · acceptance AC-016/AC-017 주 · plan §A.1 4·결정 H·M4·§F·§G · research §4·§6-6 · progress §0. (나)를 택하면 감독 승인 기록 + REQ-010 인자·AC-017 ① 갱신 + 경로 제한 REQ가 함께 필요하다.
2. **R1**(권장, 1문장) — REQ-008 `type` 경로 조건절. R2·R3도 같은 편집에서 처리 권장(셋 다 카운트 불변).

### 채무(debt) 목록 (FAIL 해소 후 남길 수 있는 것)

R2 구간 문구 · R3 Spiider 폭 · R4 O4~O7 · R5 stray `.moai/state` · R6 fixture 명시적 add · (기존) REQ-005 토큰 분할 규칙 미정의 · t10 카드(UI 전달 경로)는 이 SPEC의 `completed` 전제가 아니다(M4는 (가)의 스크립트로 수행 가능) — 단 t10이 착지하기 전까지 운영자는 채팅으로 이 툴을 쓸 수 없음을 progress §0에 한 줄로 남길 것.

### Recommendation

**FAIL — 3회차 재감사는 N1(+R1~R3 적용 여부) 델타로 한정한다.** 1회차 판정을 가른 두 축은 닫혔다 — 마커 3건은 결정 H·I·J로 plan/progress에 기록됐고(MP-7 PASS, AC-001 ⑤ 충족), AC 5건의 실행 불가·기대값 오류는 사본 fixture(해시 동일)·겹침 104·105·선택자 1/71 수집+뮤테이션 RED·대안 9런·FID 502/`2.030` 블라인드스팟으로 전부 실물·실코드와 일치한다. REQ 16/AC 17 카운트와 역추적은 5개 문서에서 일관되고, 단계 누수·신규 쓰기 동사·절대경로 누출(AC-016 1곳 제외) 0, SPEC 디렉터리 밖 변경은 fixture 1파일뿐이다. 판정을 FAIL로 둔 유일한 이유는 감사 중 착지한 v0.2.1이 M4 입력 전달을 "직접 호출로 경로 지정 → 서버가 읽어 base64 구성"으로 적으면서, 같은 문서가 닫아 둔 5키 인자 집합(경로 인자 없음)·`tools.py`의 파일 읽기 0건·감독 답 ①의 채널 결정(세션 포트·신규 엔드포인트 기각, 경로 읽기 미결정)과 모순을 만든 것이다 — 올바른 구현(5키 툴)으로는 적힌 절차를 수행할 수 없고, 절차를 살리려면 결정되지 않은 입력 채널이 생긴다. (가)안이면 설계 변경 없이 문장 통일로 닫힌다. 수정 뒤 3회차 델타 재감사에서 PASS 밴드(≥0.90)가 예상된다.

## Iteration 3 (delta)

Iteration: 3/3 · 범위: 2회차 must-fix **N1**(blocking) + **R1**(blocking·minor) + R2·R3·R5(optional) 델타 + 카운트·머스트패스 회귀 확인. 감사 대상 v0.2.2(문서 전용 개정).
Verdict: **PASS-WITH-DEBT** (must-pass 7/7 · blocking 결함 0 · 남은 것은 전부 optional 채무)
Overall Score: **0.94** (조화평균 — Clarity 0.90 · Completeness 0.95 · Testability 0.90 · Traceability 1.00; Tier M 임계 0.80; 2회차 0.88 → 상승, 회귀 없음 → STOP 신호 없음)
감사 대상: HEAD `453846a` · 브랜치 `jjjh7401/LX-SEQ` · 미커밋. 감사 시작 md5 = 종료 md5(변동 0): spec `3d63b7ab…` · plan `32685782…` · acceptance `8fb73e0a…` · research `8f8869cd…` · progress `8c09a9e0…`. 모든 명령은 워크트리 루트에서 실행(SPEC 디렉터리로 cd 하지 않음).
M1 Context Isolation: 오케스트레이터가 전달한 "수정 주장"은 가설로만 취급하고 파일·코드·fixture CSV 실물로 재검증했다.

### Must-Pass (재확인, v0.2.2)

- [PASS] **MP-1** `grep -oE 'REQ-LXSEQ-[0-9]{3}' spec.md | sort -u` → 001~016 연속 16건, 중복 0(`grep -c '^- \*\*REQ-LXSEQ-[0-9]\{3\}\*\*'` → 16).
- [PASS] **MP-2** REQ 16건 전부 GEARS 태그 보유(Ubiquitous 8 · Event-driven 3 · Unwanted 4 · While 1 — `tagged=16`). 이번 개정으로 문장이 늘어난 REQ-008/010/016도 태그·`shall`/`shall not` 구조 유지. 판정 계층 = spec.md REQ; acceptance AC는 Given-When-Then(감점 대상 아님).
- [PASS] **MP-3** 12필드 존재(spec.md:2-13) · `version: "0.2.2"` · HISTORY 0.2.2 행(spec.md:31) · `updated: 2026-08-21` · `tier: M`.
- [N/A] **MP-4** Python 단일 언어.
- [PASS] **MP-5** D7 verb → `AUTOPATCH-001 draft · LXSEQ-001 draft(자기 참조) · MVP-001 in-progress · PRECHK-001 completed · VWX-001 draft` → BLOCKING 0.
- [PASS] **MP-6** `grep -c syscall spec.md` → 0.
- [PASS] **MP-7** `grep -c 'NEEDS CLARIFICATION' spec/plan/acceptance/research.md` → `0 0 0 0`; `grep -n '\[NEEDS CLARIFICATION' plan.md research.md` → 매치 없음(progress.md 1건은 확인 명령 문자열, plan-audit.md 매치는 본 보고서 자체).

### 항목별 판정표 (명령 + 출력 그대로)

| 항목 | 판정 | 증거(명령 → 출력) |
|---|---|---|
| **N1** 입력 메커니즘 모순 — (가)안 | **RESOLVED** | `grep -n "서버는 파일 경로를 받지 않는다" <SPEC>/*.md` → spec.md:**78**(REQ-010)·**84**(REQ-016)·31(HISTORY) / plan.md:3·5·24(§A.1 4)·**51**(결정 H)·59(§A.4 ①)·113·**116**(M4)·158(§F) / acceptance.md:269·270(AC-017 대상·주)·**284**(AC-016) / research.md:110(§4)·134(§6-6) / progress.md:11·46·92·105 — 요구·검증·계획·조사·진행 5문서 전부 같은 부정문. REQ-016 본문(spec.md:84) 인용: "…`server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출하는 것 — **서버는 파일 경로를 받지 않는다**(REQ-LXSEQ-010의 인자 집합 불변); 채팅 경유 호출은 t10 이후". `grep -n "서버가 파일을 읽" <SPEC>/*.md` → **spec.md:31(HISTORY 0.2.2 행, 과거 문구 인용) · progress.md:92(v0.2.2 로그 표, 인용) · plan-audit.md:126·155(본 보고서)** — 요구·AC·계획 본문 0건. `grep -n "채팅/스크립트\|직접 호출(채팅\|경로를 지정\|file_path"` → spec.md:30·31(HISTORY) · plan.md:51(결정 H — "`file_path` 류 인자 신설 없음" 부정문) · progress.md:76(v0.2.1 로그 절, "v0.2.2에서 정정" 주석 포함)·92(로그) — 본문 잔존 0. 인자 집합: AC-017 ① `{"file_content_base64","action","name_prefix_mode","only_fids","mode_overrides"}` · `required == ["file_content_base64"]` · `additionalProperties == False`(acceptance.md:273) ↔ REQ-010 인자 5종(spec.md:78) 동일, 경로 인자 없음. AC-016(:284) "하네스가 읽어 base64 → 핸들러 직접 호출" ↔ AC-017 주(:270) "양립" — 모순 없음. |
| **N1** 하네스 소재·소유·패턴 | **RESOLVED** | plan.md:**116** M4 파일 줄: "신규 **검증 도구(제품 코드 아님)** `server/tools/lxseq_e2e.py` — **소유 M4**(run 단계 파일 목록에 포함, 커밋 대상), 소재 `server/tools/`(`busking_e2e.py`·`groupgen_e2e.py`와 같은 DEV TOOL 계열 — `build_console_stack` + `build_toolset` 실포트 조립 … `server.bridge` import 0이라 `test_architecture.py` 면제 불필요, `--approve` 없으면 `DenyAllApprovalPort`)". 실물 대조: `ls server/tools/` → `busking_e2e.py groupgen_e2e.py introspect_probe.py osc_smoke.py provider_smoke.py responder_roundtrip.py`; `sed -n 1,15p busking_e2e.py` → docstring 3행 "This is a DEV TOOL, not a production execution path", `from server.orchestrator.tools import build_toolset`(:27) · `from server.safety.bootstrap import build_console_stack`(:29) · `--listen-port`(:56) · `DenyAllApprovalPort`(:15); groupgen_e2e.py 동일 패턴("the same class as ``busking_e2e``"); `grep -c server.bridge {busking,groupgen}_e2e.py` → `0 0`; `test_architecture.py:42-43` 화이트리스트는 `osc_smoke`·`responder_roundtrip`뿐(bridge 접촉 모듈 한정) → "면제 불필요" 주장과 일치. `ls server/tools/lxseq_e2e.py` → **No such file**(M4 산출물이므로 plan 단계 부재가 정상; §G "검증 도구 1 … + fixture 1 — plan-phase 커밋에 선반영" 문구는 fixture에만 걸리는 것으로 읽히나 경계가 흐림 — O9 optional). |
| **R1** REQ-008 `type` 경로 조건절 | **RESOLVED** | spec.md:73 말미: "비기본 `name_prefix_mode="type"`(REQ-LXSEQ-010)이면 `Group`을 런 경계에서 **제외**하고 나머지 조건은 같다 — 실물 CSV는 **9런**(KEY+FOH · BACK+SIDE-L · WASH-U+WASH-D가 각각 한 런으로 병합)". fixture 재계산(86행, 키=타입·모드·유니버스[+Group] + `address == 직전.next`): Group 포함 **12런/합 86** · Group 제외 **9런/합 86** — REQ-008·REQ-010·AC-009 ①-b 일치. |
| **R2** BACK+SIDE-L 구간 | **RESOLVED** | fixture 재계산: U4 18행 = BACK 12(`4.001–025`…`4.276–300`) + SIDE-L 6(`4.301–325`…`4.426–450`), 전부 `Martin MAC Aura XB`·`Extended 25ch`·Ch 25 → 병합 구간 **`4.001–450`**. `grep -n "4\.001" <SPEC>/*.md` → acceptance.md:185(AC-009 ①-b `4.001–450, 18대 = BACK 12 + SIDE-L 6`) · plan.md:60(§A.4 ② `4.001–450`) · research.md:29(§1.1 `4.001–450`) · progress.md:94(로그). `325` 잔존은 plan-audit.md(본 보고서)와 progress 로그의 "→" 좌변뿐. 9런 전체 구간: `1.001–168(14)·1.169–192(6)·1.193–248(4)·1.249–252(2)·2.001–312(8)·3.001–392(8)·4.001–450(18)·5.001–150(6)·5.151–330(20)`. |
| **R3** Spiider 모드 폭 | **RESOLVED** | fixture 재계산: `Robe Spiider` 8행 = MOVER-D · U3 · `Mode 1 49ch` · `Ch=49`; `Extended 25ch` 24행은 전부 `Martin MAC Aura XB`(BACK·SIDE-L·SIDE-R). acceptance.md:30 시나리오 5 "`Robe Spiider`(실물 CSV MOVER-D 8행 · `Mode 1 49ch` · `Ch=49`) … 49ch 둘(`A`/`B`)" · :146 AC-006 ③ "`[("A", 49), ("B", 49)]` + `Ch=49`, `Mode="Mode 1 49ch"` … 토큰으로도 못 가름" · :147 ③-b `mode_overrides={"Robe Spiider": "B"}` — "동폭 둘·토큰 불가" 분기가 실물 행으로 실행된다. AC-006 ②의 합성 `(Basic,25)/(Extended,25)` 예는 유지(토큰 분기). |
| **R5** stray 비-md 파일 | **RESOLVED(최종 관측) — 단 플래핑** | 1차 `find <SPEC> -type f -not -name '*.md'` (감사 초반) → `.moai/state/context-usage.json` · `.moai/state/github/counts.json`(**mtime 14:11**, 아티팩트 편집 14:08 이후 재생성; `config-cache.json`은 없음 → 삭제는 실제로 있었고 2건이 되살아난 것); 같은 경로 `cat` 시점엔 `No such file`; **최종** `find …` → **빈 출력**. 해석: SPEC 디렉터리를 cwd로 둔 세션이 살아 있는 동안 statusline이 `.moai/state/*.json`을 다시 쓴다(manager-spec 자기 메모 `project_spec_dir_cwd_state.md`도 같은 관찰). `.gitignore:248` `.moai/specs/*/.moai/`로 커밋에는 안 들어가지만, 커밋 직전 `find`로 재확인할 것. |
| 카운트 안정성 | **PASS** | REQ 16 · AC 17(`grep -c '^#\{2,3\} AC-' acceptance.md` → 17, 001~017 전부) · `version: "0.2.2"` + HISTORY 0.2.2 행(spec.md:31) · progress §E.1 `spec_version: "0.2.2"` · `requirements: 16` · `acceptance_criteria: 17` · `plan_status: draft`(3회차 PASS 후 `audit-ready` 갱신 예정 — progress.md:44·144) · `base_sha: 453846a`. `git status --short --untracked-files=all -- server ui` → `?? server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` **1건만**. 워크트리 전체에서 본 SPEC 관련 변경 = SPEC 디렉터리 6 md + fixture 1 + (신규 발견) SPEC 디렉터리 안 `.claude/agent-memory/manager-spec/` 3파일(R7). |

### 카테고리 점수

| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.90 | 0.75~1.0 | N1·R1 해소 — 입력 메커니즘이 5문서에서 한 문장으로 닫혔고 REQ-008 `type` 경로 조건절이 들어갔다. 잔여: (기존) REQ-005 토큰 분할 규칙 미정의 · O9 §G 파일 수 문구의 "plan-phase 선반영" 범위 경계 흐림(fixture만인지 하네스 포함인지 — M4 줄은 "소유 M4·run 단계"로 명확). |
| Completeness | 0.95 | 1.0 | 2회차와 동일(O4 미적용). |
| Testability | 0.90 | 0.75~1.0 | AC-016 절차가 실존 가능한 메커니즘(하네스 스크립트, 기존 DEV TOOL 패턴)으로 바뀌어 수행 가능; R2·R3 기대값 실물 일치. 감점: AC-016은 M4가 만들 스크립트에 의존(plan 단계엔 부재 — run 단계 정상) · REQ-005 토큰 규칙. |
| Traceability | 1.00 | 1.0 | REQ 16/AC 17 역추적 2회차와 동일, 변동 0. |

### Defects Found (iteration 3 — 신규/잔여)

R7. **STRAY-AGENT-MEMORY-IN-SPEC-DIR** — `.moai/specs/SPEC-COPILOT-LXSEQ-001/.claude/agent-memory/manager-spec/{MEMORY.md,feedback_audit_delta_fixes.md,project_spec_dir_cwd_state.md}`(14:09, `git status` `??` — **gitignore 대상 아님**) — manager-spec이 SPEC 디렉터리 cwd로 돌며 자기 메모를 잘못된 위치에 썼다(정위치 `<root>/.claude/agent-memory/manager-spec/`에는 별도 `project_lxseq_stage1_patch_spec.md`만 있음). Severity: minor — Class: optional — Fix: 두 메모를 루트 agent-memory로 옮기고(내용은 유효한 교훈) SPEC 디렉터리의 `.claude/`를 지운다; plan 커밋은 **명시적 pathspec**(6 md + fixture)로만 `git add`.
O9. **PLAN-G-FILECOUNT-WORDING** — plan.md §G "검증 도구 1 `server/tools/lxseq_e2e.py` + fixture 1 — plan-phase 커밋에 선반영 + 수정 2" — "선반영"이 fixture에만 걸리는지 하네스까지인지 문장 경계가 흐림(M4 줄·§F는 하네스=M4 산출물로 명확). Severity: minor — Class: optional — Fix: "fixture 1(plan-phase 커밋에 선반영)"로 괄호를 fixture에 붙인다.

### Regression Check (2회차 결함)

- N1 — **RESOLVED** · R1 — **RESOLVED** · R2 — **RESOLVED** · R3 — **RESOLVED** · R4(O4~O7) — 미적용(optional, 재량) · R5 — RESOLVED(최종 관측; 플래핑 주의) · R6 — 절차 메모 유지. 2회차 blocking 미해결 **0** · 정체 0 · 점수 0.88 → 0.94(회귀 없음).

### Remaining must-fix

**없음.** Kickoff Approval 진입을 막는 결함 0.

### 채무(debt) 목록 (carried forward)

1. R4 — O4~O7(1회차 optional) 미적용.
2. R5 — SPEC 디렉터리 cwd 세션이 살아 있는 동안 `.moai/state/*.json`이 되살아난다(gitignore로 커밋 차단됨; 커밋 직전 `find` 재확인).
3. R6 — fixture `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` untracked → plan 커밋 시 명시적 pathspec으로 함께 add(스윕 금지).
4. R7 — SPEC 디렉터리 안 stray `.claude/agent-memory/manager-spec/` 3파일(gitignore 아님) → 루트로 이전 후 삭제.
5. O9 — §G 파일 수 문구 경계.
6. (기존) REQ-005 토큰 분할 규칙 미정의.
7. t10 전까지 운영자는 채팅으로 이 툴을 쓸 수 없음 — progress.md:11 §0 ④에 기재 확인됨(채무 이행 완료, 기록 유지).
8. M4 하네스 `server/tools/lxseq_e2e.py`는 run 단계 M4 산출물(현재 부재가 정상) — `server.bridge` import 0을 지켜야 `test_architecture.py` 면제가 불필요하다는 전제는 구현 시 기계 확인 대상.

### Recommendation

**PASS-WITH-DEBT — progress §E.1 `plan_status`를 `audit-ready`로 갱신하고 Implementation Kickoff Approval로 진행 가능.** 2회차 FAIL의 유일한 blocking 사유였던 N1은 (가)안으로 닫혔다: 요구(REQ-010/016)·검증(AC-016/017)·계획(§A.1·결정 H·§A.4·M4·§F·§G)·조사(§4·§6-6)·진행(§0·M0 표)이 "로컬 하네스 `server/tools/lxseq_e2e.py`가 읽어 base64로 핸들러 직접 호출 — 서버는 파일 경로를 받지 않는다 — 채팅 경유는 t10 이후"라는 한 문장으로 통일됐고, 5키 인자 집합은 불변이며, 하네스의 소재·소유·패턴(`busking_e2e`/`groupgen_e2e` DEV TOOL 계열)은 실물 파일·import 구조와 일치한다. R1~R3은 fixture CSV 직접 재계산(9/12런 · `4.001–450` · Spiider 49ch)과 일치. 남은 채무는 전부 optional(stray 파일·커밋 절차·문구 1건·기존 REQ-005)이며 Kickoff를 막지 않는다. 커밋 시 스윕 금지·명시적 pathspec만 지킬 것.
