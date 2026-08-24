# SPEC-COPILOT-LXSEQ-002 — 인수 기준 (acceptance)

문서 상태: draft (v0.1.0, 2026-08-24). Tier M. AC **16건**(오프라인 15에 onPC 실기 1). 본 문서는 spec.md의 요구를 관측 가능한 Given-When-Then 검증 기준으로 전개한다. 요구(GEARS)는 spec.md가 소유하며 여기서 되풀이하지 않는다.

> **참조 규약**: 정본(spec.md와 본 문서)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. 파일과 줄 좌표는 코드, 입력 데이터, 타 SPEC 아티팩트에만 쓴다.

---

## A. 검증의 축

| 축 | 내용 | 왜 축인가 |
|---|---|---|
| ① 멤버십 무추측 | 멤버 FID는 패치표와 코드의 닫힌 규칙에서만 온다. 산문 열을 해석하지 않고, 이름을 유추하지 않는다 | 쓴 것이 어느 채널로도 되읽히지 않았다. 오해석이 조용히 영속하고 사후 적발이 없다 |
| ② 어긋나면 0건 | 슬롯이 어긋나거나 FID 실측이 불완전하면 계획을 내지 않는다 | 부분 계획이 최악의 결과다(`guard_plan_size` 독스트링). 반쯤 맞는 그룹이 쇼파일에 남는다 |
| ③ 발화 전 측정 | 번들 바이트를 발화 전에 재고 예산 밖이면 건너뛴다 | 전송 상한 초과는 **조용한 누락**이다. 발화 후에는 탐지 수단이 없다 |
| ④ 단일 쓰기 경로 | 쓰기는 `create_arrangement_groups` 위임뿐. `server/lxseq/` 에 쓰기 수단 0 | 감독 결정 ①. 001의 축을 그대로 계승한다 |
| ⑤ 등급 정직성 | 멤버십은 **미측정**이라 적는다. 단정하지 않는다 | 판정 전제가 만료됐다(RESTORE-001 survey A.2, A.5). 낡은 단정을 되살리면 다음 사람이 재측정을 안 한다 |

---

## B. 대표 시나리오 (Given-When-Then)

**시나리오 1 — 빈 그룹 풀, 패치된 콘솔, 실물 두 CSV**: **Given** 픽스처 86대가 패치돼 있고 그룹 풀이 비어 있는 onPC와 실물 그룹 CSV 18행, **When** preview 를 부르면, **Then** 거부 0, 건너뜀 0, 배치 2개(기본 12와 파생 6), 슬롯 대조 일치(1부터 18까지), 번들 바이트 목록에 18개 값이 전부 있다.

**시나리오 2 — 파생 규칙 검산**: **Given** 시나리오 1과 같은 입력, **When** preview 의 배치를 읽으면, **Then** ODD 는 정확히 501, 503, 505, 507, 521, 523, 525, 527 여덟이고 EVEN 은 502, 504, 506, 508, 522, 524, 526, 528 여덟이며, ALL 은 86개이고 FOLLOW 계열 FID가 하나도 없다.

**시나리오 3 — 슬롯이 어긋남**: **Given** 그룹 풀에 이미 그룹 하나가 슬롯 3에 있음, **When** preview 를 부르면, **Then** 측정된 빈 슬롯이 1, 2, 4, 5로 시작해 시트의 1, 2, 3, 4와 어긋나므로 **배치 0개**이고 `slot_number_divergence` 대조표가 두 순열을 나란히 싣는다.

**시나리오 4 — 이름 미해결**: **Given** 그룹 CSV에 `Name` 이 `SPECIAL-X` 인 행이 하나 추가됨, **When** preview 를 부르면, **Then** 그 행만 `unknown_group_name` 으로 건너뛰고 나머지 18행은 정상 계획되며, 건너뛴 목록에 그 이름이 적혀 있다.

**시나리오 5 — 번들이 예산 밖**: **Given** 선언된 바이트 예산을 ALL 의 실측 번들 길이보다 작게 설정한 트리, **When** preview 를 부르면, **Then** ALL 만 `bundle_over_budget` 으로 건너뛰고 목록에 실측 바이트 수가 적히며, 나머지 17개는 정상 계획된다.

**시나리오 6 — 재실행**: **Given** 시나리오 1의 apply 가 18개를 만든 뒤, **When** 같은 파일로 preview 를 다시 부르면, **Then** 18슬롯이 전부 점유이므로 배치 0개이고, 오류가 아니라 「할 일 없음」이다.

---

## C. 인수 기준

### C.0 역추적표

| REQ | 커버 AC | M |
|---|---|---|
| (M0 계약 확인) | AC-LXSEQ2-001 | M0 |
| REQ-LXSEQ2-001 | AC-LXSEQ2-002 | M1 |
| REQ-LXSEQ2-002 | AC-LXSEQ2-003 | M1 |
| REQ-LXSEQ2-003 | AC-LXSEQ2-004 | M1 |
| REQ-LXSEQ2-006 | AC-LXSEQ2-005 | M2 |
| REQ-LXSEQ2-004 | AC-LXSEQ2-006 | M2 |
| REQ-LXSEQ2-005 | AC-LXSEQ2-007 | M2 |
| REQ-LXSEQ2-007 | AC-LXSEQ2-008 | M2 |
| REQ-LXSEQ2-008 | AC-LXSEQ2-009 | M2 |
| REQ-LXSEQ2-009 | AC-LXSEQ2-010 | M2 |
| REQ-LXSEQ2-010 | AC-LXSEQ2-011 | M2 |
| REQ-LXSEQ2-011 | AC-LXSEQ2-012 | M2 |
| REQ-LXSEQ2-012, REQ-LXSEQ2-013 | AC-LXSEQ2-013 | M3 |
| REQ-LXSEQ2-014 | AC-LXSEQ2-014 | M3 |
| REQ-LXSEQ2-015, REQ-LXSEQ2-016 | AC-LXSEQ2-015 | M3 |
| (라이브 종단) | AC-LXSEQ2-016 | M4 |

합 16건, 중복 0, 누락 0. REQ 16건이 전부 최소 한 AC에 걸린다.

### C.1 M0 — 계약과 입력 정본

**AC-LXSEQ2-001**. **Given** run-phase 착수 시점의 트리, **When** M0를 수행하면, **Then** 다음 넷이 progress.md에 기록돼 있다.

① `create_arrangement_groups` 의 인자 계약과 `build_group_write_plan` 의 반환 필드를 소스에서 재확인한 결과(드리프트가 있으면 그 내용).
② `DEFAULT_GROUP_PLAN_CAP` 의 **실제 읽은 값**. 16이 아니면 결정 M의 배치 분할 근거가 바뀌므로 블로커 보고다.
③ 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv` 의 존재, sha256 `bc7aced27b0bc06938f2aed2b52c2cff8e2e6ec362ceac154694d5ef64af0172`, 19줄, 헤더 4열. **하나라도 다르면 명시적 FAIL이며 건너뛰기가 아니다.**
④ 착수 전 전체 스위트 baseline 수치.

### C.2 M1 — 파서

**AC-LXSEQ2-002**. **Given** 실물 그룹 CSV 사본, **When** 파서를 부르면, **Then** ① BOM이 있어도 첫 열 이름이 `GroupNo` 로 읽힌다. ② 열 순서를 섞은 CSV도 같은 18개 레코드를 낸다(위치가 아니라 이름으로 매칭한다는 증거). ③ 4열 중 하나를 지운 CSV는 파일 단위로 실패하고 레코드를 0개 낸다.

**AC-LXSEQ2-003**. **Given** 각 거부 부류를 하나씩 심은 CSV 5종, **When** 파서를 부르면, **Then** ① 예외가 하나도 발생하지 않는다. ② 부류가 `groupno_not_int`, `groupno_out_of_range`, `groupno_duplicate`, `name_empty`, `name_has_quote` 각각으로 정확히 붙는다. ③ 심지 않은 행은 전부 정상 레코드로 나온다(비공허성 — 거부 목록이 전부인 CSV로는 이 AC를 통과할 수 없다).

**AC-LXSEQ2-004**. **Given** `Members` 열을 전부 빈 문자열로 바꾼 CSV, **When** 파서를 부르면, **Then** 18개 레코드가 그대로 나오고 `Members` 필드만 빈 문자열이다. 파서가 그 열을 판정에 쓰지 않는다는 증거다.

### C.3 M2 — 매퍼

**AC-LXSEQ2-005**. **Given** `Name` 이 `SPECIAL-X` 인 행을 추가한 CSV, **When** 매퍼를 부르면, **Then** ① 그 행만 `unknown_group_name` 으로 건너뛴다. ② 건너뛴 목록에 그 이름 문자열이 있다. ③ 나머지 18행은 배치에 들어간다. ④ 그 이름에 대해 FID가 하나도 만들어지지 않는다(추측 0).

**AC-LXSEQ2-006**. **Given** 001 패치 CSV 사본에서 만든 라벨 표, **When** 기본 12종의 멤버를 만들면, **Then** 각 그룹의 FID 수가 BACK 12, BLIND 6, FOH 8, HAZE 2, KEY 6, MOVER-D 8, MOVER-U 8, SIDE-L 6, SIDE-R 6, STROBE 4, WASH-D 10, WASH-U 10 이고 합이 86이며, 어느 FID도 두 기본 그룹에 동시에 속하지 않는다.

**AC-LXSEQ2-007**. **Given** 같은 라벨 표, **When** 파생 6종의 멤버를 만들면, **Then** ① ALL 이 86개이고 FOLLOW 계열 FID가 0개다. ② SIDE-ALL 이 12개(301에서 306, 311에서 316). ③ WASH-ALL 이 20개. ④ MOVER-ALL 이 16개. ⑤ ODD 가 정확히 501, 503, 505, 507, 521, 523, 525, 527. ⑥ EVEN 이 정확히 502, 504, 506, 508, 522, 524, 526, 528. ⑦ ODD와 EVEN의 합집합이 MOVER-ALL과 같고 교집합이 비어 있다.

**AC-LXSEQ2-008**. **Given** `Members` 를 `KEY 7대` 로 바꾼 행 하나, **When** 매퍼를 부르면, **Then** ① KEY 만 `member_count_mismatch` 로 건너뛴다(실제 6, 시트 7). ② 목록에 두 수가 모두 적혀 있다. ③ 개수를 안 적은 행(`SIDE-L + SIDE-R` 같은)은 이 대조를 받지 않고 통과한다.

**AC-LXSEQ2-009**. **Given** 콘솔 FID 실측에서 FID 205를 뺀 단면, **When** 매퍼를 부르면, **Then** ① BACK과 ALL 이 205를 포함하지 않는다. ② 그리고 **FID 실측이 전수가 아닌 경우**(`console_read_incomplete` 표지가 선 단면)에는 배치가 **0개**이고 부분 계획을 내지 않는다.

**AC-LXSEQ2-010**. **Given** 슬롯 3이 점유된 그룹 풀 단면, **When** 매퍼를 부르면, **Then** ① 배치가 0개다. ② `slot_number_divergence` 보고에 시트 순열(1부터 18)과 측정 순열(1, 2, 4, 5, ...)이 나란히 실린다. ③ 어느 그룹도 슬롯 번호를 옮겨 배정받지 않는다.

**AC-LXSEQ2-011**. **Given** 빈 그룹 풀 단면과 실물 두 CSV, **When** 매퍼를 부르면, **Then** ① 배치가 정확히 2개다. ② 1차가 기본 12개, 2차가 파생 6개다. ③ 어느 배치도 `DEFAULT_GROUP_PLAN_CAP` 을 넘지 않는다. ④ 두 배치를 하나로 합치면 `guard_plan_size` 가 `GROUP_PLAN_TOO_LARGE` 를 던진다는 것을 같은 테스트가 함께 단언한다(분할이 필요하다는 근거의 비공허성).

**AC-LXSEQ2-012**. **Given** 선언된 바이트 예산과 실물 입력, **When** 매퍼를 부르면, **Then** ① 각 그룹의 조립 번들 인코딩 바이트가 보고에 실린다. ② ALL 의 선택 줄 길이가 1201로 관측된다. ③ **예산을 ALL 의 실측 번들 길이보다 작게 낮춘 뮤테이션에서 이 AC가 빨개진다** — 안 빨개지면 게이트가 공허하므로 이 항목이 게이트의 유일한 비공허성 증거다. ④ 예산을 넘은 그룹만 `bundle_over_budget` 으로 빠지고 나머지는 남는다.

### C.4 M3 — 툴과 배선

**AC-LXSEQ2-013**. **Given** 가짜 포트로 조립한 툴셋, **When** `import_lxseq_groups` 를 부르면, **Then** ① 툴이 정확히 1종 등재되고 `test_tools.py` 의 툴 수 상수가 1 늘어난다. ② action 을 안 주면 preview 로 동작한다. ③ **preview 에서 콘솔 쓰기가 0건이다** — 가짜 실행 포트의 호출 기록이 비어 있고, 동시에 읽기 호출은 비어 있지 않다(비공허성). ④ apply 는 배치를 **순서대로** `create_arrangement_groups` 에 위임하고, 1차 배치가 실패하면 2차를 부르지 않는다. ⑤ `server/lxseq/` 전체에 대한 AST 스캔에서 쓰기 수단(`run_commands`, `deploy_pipeline`, `execution_port`, Lua 생성 모듈)의 식별자가 0건이고, 같은 스캔이 `server/orchestrator/tools.py` 에 대해서는 0이 아니다(스캐너가 실제로 찾는다는 증거).

**AC-LXSEQ2-014**. **Given** `group` 행이 추가된 시트 종류 레지스트리, **When** 기존 검사 `server/tests/test_sheet_kind_consumers.py` 를 돌리면, **Then** ① 전부 통과한다. ② 동반 4지점(`SHEET_KIND_ACTIONS` 항목, 행 계수기 항목, 래퍼 스키마 passthrough 인자, 래퍼 action enum) 중 **어느 하나를 빼도 그 검사가 빨개진다** — 넷을 각각 뺀 4회 뮤테이션으로 확인한다. ③ 그룹 CSV 헤더를 `discriminate` 에 넣으면 `group` 하나로 판정되고 `patch` 나 `vectorworks` 로 흐르지 않는다. ④ 패치 CSV 헤더를 넣으면 여전히 `patch` 로 판정된다(신규 행이 기존 판정을 흔들지 않는다).

**AC-LXSEQ2-015**. **Given** 툴 스키마와 preview 페이로드, **When** 둘을 읽으면, **Then** ① 툴 설명문과 `guidance` 에 채팅 붙여넣기 금지가 명시돼 있다. ② 페이로드에 `source.sha256` 과 `byte_length` 가 있다. ③ 페이로드의 `unverified` 목록에 `membership` 이 있고 `unverified_reason` 이 비어 있지 않다. ④ **금지어 grep이 대상 범위에서 0건이다.** 대상 범위는 run 단계가 만든 것 — `server/lxseq/` 의 코드와 주석, 툴 설명문과 `guidance`, 툴 페이로드 문자열 — 이며, **금지어를 정의하는 SPEC 문서(spec.md, plan.md, acceptance.md, progress.md)는 대상이 아니다.** 그 문서들은 금지어를 금지하기 위해 반드시 인용하므로, 범위에 넣으면 이 검사는 구조적으로 0을 낼 수 없다 — 검사 토큰을 문서가 인용하면 그 검사가 영영 초록이 안 되는 형태이며, 이 저장소가 이미 세 번 겪은 함정이다. 그리고 같은 grep이 하향 이전 문면을 심은 대조 파일에 대해서는 1건 이상을 낸다(스캐너 비공허성 — 대조군 없이 나온 0은 증거가 아니다). ⑤ `unverified_reason` 문자열에 「미측정」이 들어 있다.

### C.5 M4 — onPC 실기 (라이브 1건)

**AC-LXSEQ2-016**. **Given** onPC 2.4.2, 픽스처 86대 패치 완료, 그룹 풀 childCount 0, **When** 사용자가 preview 와 apply 를 순서대로 수행하면, **Then** 다음 다섯 행이 전부 관측된다.

① **preview**: 배치 2개(12와 6), 슬롯 대조 일치, 건너뛴 행 0, 번들 바이트 18개 값이 전부 보고에 있다.
② **apply**: 배치마다 `status: created` 를 관측하고, 그룹 풀 childCount 가 0에서 12로, 다시 12에서 18로 오른다.
③ **사람 확인**: `human_check_commands` 를 콘솔에서 실행해 조명감독이 눈으로 멤버를 확인한다. **이 단계는 기계 검증이 아니며, 그렇게 적는다** — 멤버십은 미측정이고 툴은 슬롯 존재와 이름만 재조회한다.
④ **재실행**: 같은 입력으로 preview 를 다시 부르면 배치 0개이고 사유가 `GROUP_SLOT_OCCUPIED` 다. 오류가 아니라 「할 일 없음」이다.
⑤ **ASSUMPTION 판정**: 80(풀이 비었는가), 81(번들이 상한 안이었는가 — **여기서 처음 측정된다**), 82(픽스처 이름이 라벨에 FID 꼴인가)를 각각 참거짓으로 적는다.

⑥ 위 다섯 중 **하나라도 미통과면 M4는 PASS로 닫히지 않는다.** 실패한 행 수만큼 실패한 AC를 센다.

---

## D. Definition of Done

| 조건 | 판정 |
|---|---|
| AC 16건 중 오프라인 15건 전부 PASS | `implemented` 진입 요건 |
| AC-LXSEQ2-016 (라이브) PASS | `completed` 진입 요건 |
| 뮤테이션 목록(plan.md의 각 M절) 전부 검산 | 필수. 특히 AC-012의 예산 낮추기와 AC-014의 4지점 빼기 |
| PRESERVE 목록(plan.md A.5) 무변경 | `git diff` 로 확인 |
| 열린 결정 2건이 progress.md에 답과 함께 기록 | Kickoff 산출물 |

**미통과 시**: 라이브가 실패하면 `implemented` 에서 멈추고 `completed` 로 가지 않는다. 001의 선례와 같다.

---

## E. 이 문서가 검증하지 않는 것

- **멤버십이 실제로 맞는가.** 기계로 확인할 수단이 없다. AC-016의 셋째 항은 사람 확인이며, 그것을 기계 검증으로 세지 않는다.
- **전송 상한의 정확한 값.** AC-012는 예산을 **선언하고 지키는지**를 재지, 상한 자체를 재지 않는다. 상한 실측은 AC-016의 다섯째 항에서 처음 일어난다.
- **그룹이 있는 쇼파일에서의 판독 가능성.** 카드 t22와 t46 소유다.
