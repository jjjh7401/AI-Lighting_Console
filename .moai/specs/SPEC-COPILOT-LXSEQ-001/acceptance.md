# SPEC-COPILOT-LXSEQ-001 — 인수 기준 (acceptance)

문서 상태: implemented (v0.2.1, 2026-08-21 — 판정 확정: 17건 중 **16 PASS · AC-LXSEQ-016 PASS-WITH-DEBT**(5행 중 4 PASS · 1 FAIL, 사유는 결함 D2 → 카드 t11) · FAIL 0. 근거는 progress.md §E.2 — 문서 전용: AC-016 입력 전달 현재/목표 분리 · AC-017 주 추가, AC 수 불변) · Tier M · AC **17건**(오프라인 16 + onPC 실기 1). v0.2.0: plan-audit 1회차 델타(D2·D3·D4·D6·D7·O8) + 감독 Kickoff 답 반영(AC-006 `mode_unresolved`/`mode_overrides` · AC-009 9런 · **AC-017 신설** 채팅 붙여넣기 금지). 본 문서는 spec.md의 요구를 관측 가능한 Given-When-Then 검증 기준으로 전개한다. 요구(GEARS)는 spec.md가 소유하며 여기서 되풀이하지 않는다.

> **참조 규약**: 정본(spec.md · 본 문서)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 코드·입력 데이터·타 SPEC 아티팩트에만 쓴다.

---

## §A. 검증의 축

| 축 | 내용 | 왜 축인가 |
|---|---|---|
| ① 파싱 정직성 | 실물 86행을 통째로 읽고, 깨진 행은 예외가 아니라 부류로 낸다 | LX-SEQ 생성기가 보장하는 R1~R3를 파서가 거울처럼 다시 잰다 |
| ② 점유 불가침 | 찬 자리·찬 FID는 절대 쓰지 않고 목록으로 돌려준다 | 감독 결정 ③ — 덮어쓰기는 복구 불가 |
| ③ 실측 우선 | 타입·모드·폭·자리는 콘솔이 답한 값만 쓴다 | 추측 패치는 전량 거부된 실측 선례(2026-08-18) |
| ④ 단일 쓰기 경로 | 쓰기는 `patch_fixtures` 위임뿐, `server/lxseq/`에 쓰기 수단 0 | 감독 결정 ① |

---

## §B. 대표 시나리오 (Given-When-Then)

**시나리오 1 — 빈 콘솔, 실물 CSV**: **Given** 픽스처 0대인 onPC와 실물 CSV 86행, **When** `preview`를 부르면, **Then** 거부 0 · 건너뜀 0 · 런 12개 · 계획 쓰기 86대, FID 매핑표에 CSV의 FID 86개가 그대로 있다.

**시나리오 2 — 일부 점유**: **Given** 콘솔에 `2.001`에 다른 장비 1대와 FID 301이 이미 있음, **When** `preview`/`apply`를 부르면, **Then** FID 501(2.001)은 `address_occupied`, FID 301은 `fid_occupied`로 건너뛰고 두 행은 어느 런에도 없으며, 건너뛴 목록에 점유자가 적혀 있다.

**시나리오 3 — 재실행 멱등**: **Given** 시나리오 1의 `apply`가 86대를 만든 뒤, **When** 같은 파일로 `preview`를 다시 부르면, **Then** 런 0개 · `already_patched` 86건 · `summary_ko`가 "할 일 없음"을 말하고 오류가 아니다.

**시나리오 4 — 타입 부재**: **Given** 콘솔 라이브러리에 `Look Unique 2.1`이 없음, **When** `preview`를 부르면, **Then** HAZE 2행이 `type_unresolved`로 건너뛰고 나머지 84행은 정상 계획된다.

**시나리오 5 — 모드 미해결 → 재호출**: **Given** `Robe Spiider`(실물 CSV MOVER-D 8행 · `Mode 1 49ch` · `Ch=49`)의 실측 모드가 49ch 둘(`A`/`B`)이라 `Ch=49`로 가려지지 않음, **When** `preview`를 부르면, **Then** MOVER-D 8행이 `mode_unresolved` 한 목록에 모이고(카드 0회) 나머지 78행은 정상 계획되며, `mode_overrides={"Robe Spiider": "B"}`로 다시 부르면 8행이 `console_mode="B"`로 런에 들어간다.

---

## §C. 인수 기준

### §C.0 역추적표

| REQ | 커버 AC | M |
|---|---|---|
| REQ-LXSEQ-001 | AC-LXSEQ-002 | M1 |
| REQ-LXSEQ-002 | AC-LXSEQ-003 | M1 |
| REQ-LXSEQ-003 | AC-LXSEQ-004 | M1 |
| REQ-LXSEQ-004 | AC-LXSEQ-005 | M2 |
| REQ-LXSEQ-005 | AC-LXSEQ-006 | M2 |
| REQ-LXSEQ-006 | AC-LXSEQ-007 | M2 |
| REQ-LXSEQ-007 | AC-LXSEQ-008 | M2 |
| REQ-LXSEQ-008 | AC-LXSEQ-009 | M2 |
| REQ-LXSEQ-009 | AC-LXSEQ-010 | M2 |
| REQ-LXSEQ-010 | AC-LXSEQ-011 · AC-LXSEQ-012 | M3 |
| REQ-LXSEQ-011 | AC-LXSEQ-014 | M3 |
| REQ-LXSEQ-012 | AC-LXSEQ-013 | M3 |
| REQ-LXSEQ-013 | AC-LXSEQ-012 (별 구간) | M3 |
| REQ-LXSEQ-014 | AC-LXSEQ-014 (별 구간) | M3 |
| REQ-LXSEQ-015 | AC-LXSEQ-015 | M3 |
| REQ-LXSEQ-016 | AC-LXSEQ-017 | M3 |

**REQ 16/16 커버, 누락 0.** 역추적표에 없는 AC는 2건이며 의도다 — **AC-LXSEQ-001**(M0 계약 확인 게이트) · **AC-LXSEQ-016**(M4 onPC 실기 — 형상 전체).

### §C.0a 마일스톤별 AC 배정 (정본)

| 마일스톤 | AC | 수 |
|---|---|---|
| M0 — 계약 확인 · 입력 고정 | AC-LXSEQ-001 | 1 |
| M1 — 파서 | AC-LXSEQ-002 · 003 · 004 | 3 |
| M2 — 매퍼 | AC-LXSEQ-005 · 006 · 007 · 008 · 009 · 010 | 6 |
| M3 — 툴 | AC-LXSEQ-011 · 012 · 013 · 014 · 015 · 017 | 6 |
| M4 — onPC 실기 | AC-LXSEQ-016 | 1 |

**합 17 · 중복 0 · 누락 0.**

---

### AC-LXSEQ-001 — 기존 툴 계약 확인 · 입력 고정 게이트 (M0)

**Given** run-phase 착수 시점의 저장소, **When** M0를 마치면, **Then** 4종 툴 계약의 재확인 기록과 입력 사본이 존재한다.

- 대상 요구사항: 없음 — 전제 게이트.
- 검증 방법: `progress.md` M0 절 + 아래 명령. 입력 정본은 주 체크아웃에만 있는 git 미추적 로컬 파일이라 워크트리·CI에는 없다 — 저장소 안 계약은 plan-phase v0.2.0에서 복사해 이 카드 커밋에 넣은 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`(sha256 `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3`, 2026-08-21 `shasum -a 256`로 정본과 동일 실측)이며, 본 AC의 명령은 **사본만** 읽는다. 사본이 없으면 아래 ②가 **명시적으로 FAIL**한다(건너뛰기가 통과로 읽히는 형태 금지).
- 기대 결과:
  - ① `grep -n "def patch_fixtures\|def resolve_fixture_type\|def resolve_patch_address\|def precheck_patch" server/orchestrator/tools.py` 4건이 `progress.md`에 **그 시점 줄번호로** 적혀 있고 `research.md` §2와의 차이가 표로 기록된다.
  - ② `test -f server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv || { echo FAIL: fixture missing; exit 1; }` 가 통과하고, `shasum -a 256 server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` → `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3`(`progress.md` §0/v0.2.0에 기록된 정본 해시와 동일; 다르면 FAIL).
  - ③ `tail -n +2 server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv | wc -l` → `86`; `uv run python -c "print(open('server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv',encoding='utf-8-sig').readline().strip())"` → `FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position`.
  - ④ `uv run pytest server/tests -q` 착수 baseline이 `progress.md`에 적혀 있다(이월 아님).
  - ⑤ 결정 H·I·J(plan.md §A.3 — 2026-08-21 감독 Kickoff 답 ①②③, ③은 대안 채택)가 `progress.md` "M0 — Kickoff 결정 기록" 절에 적혀 있다.

### AC-LXSEQ-002 — 실물 CSV 86행 판독 · 이름 기반 컬럼 (M1)

**Given** 실물 CSV 사본, **When** 파서를 부르면, **Then** 86개 레코드 · 거부 0 · 제외 0이다.

- 대상 요구사항: REQ-LXSEQ-001
- 검증 방법: `uv run pytest server/tests/test_lxseq_parser.py -q -k "real_csv or header"`
- 기대 결과:
  - ① `len(records) == 86`, `rejected == ()`, `excluded == ()`; 첫 레코드 `fid=101, universe=1, address=1, channels=12, group="KEY"`, 마지막 `fid=430, universe=5, address=322`.
  - ② BOM을 뗀 같은 내용 · 열 순서를 뒤섞은 같은 내용에서도 ①과 동일한 레코드가 나온다(위치 해석 금지의 비공허성 — 섞은 CSV의 첫 열이 `Position`이어도 `fid`가 101이다).
  - ③ 정규 9열 중 `AddrRange`를 뺀 CSV는 레코드 0 + 파일 단위 실패 `missing_columns: ["AddrRange"]`.
  - ④ 정규 밖 컬럼(`Note`)을 더한 CSV에서 `extra["Note"]`가 원문 그대로 있다.
  - ⑤ `Position`의 한국어(`FOH 브리지`)가 깨지지 않고 보존된다.

### AC-LXSEQ-003 — 행 검증 7부류 · 예외 없음 (M1)

**Given** 실물 CSV를 메모리에서 변형한 입력들, **When** 파서를 부르면, **Then** 변형 행만 닫힌 부류로 거부되고 나머지는 정상이다.

- 대상 요구사항: REQ-LXSEQ-002
- 검증 방법: `uv run pytest server/tests/test_lxseq_parser.py -q -k "reject or overflow or duplicate or overlap"`
- 기대 결과:
  - ① FID 101 행의 `Address`를 `500`으로 바꾸면(500+12-1=511 — 통과), `502`로 바꾸면 `universe_overflow` 1건, 나머지 85 정상.
  - ② FID 102 행의 `AddrRange`를 `1.013–023`으로 바꾸면 `addr_range_mismatch` 1건; `1.013-024`(hyphen) 또는 `1.013—024`(em-dash)면 거부 0(구분자 관용).
  - ③ FID 103 행을 복제하면 `duplicate_fid` **2건**(관여 행 전부), 84 정상.
  - ④ FID 104 행의 `Address`를 `40`으로 바꾸면(104 구간이 1.040–051이 되어 **105**의 1.049–060과 겹친다; 103의 1.025–036과는 겹치지 않는다) `address_overlap_in_file` **2건**(**104·105** 둘 다), 103은 정상. 실물 CSV 86행으로 직접 계산한 값이다(겹침 쌍 `[(104,105)]`; 이전 기대값 103·104로 단언하면 올바른 구현이 RED — plan-audit D3).
  - ⑤ `Ch`를 `abc`로 바꾸면 `non_integer_field` 1건.
  - ⑥ `Ch=0` 행(FOLLOW-1 수동 운용)을 더하면 `excluded` 1건이고 `rejected`는 0.
  - ⑦ 위 어느 경우에도 예외가 호출자까지 올라오지 않는다(`pytest.raises` 0건으로 단언).

### AC-LXSEQ-004 — FID는 주소가 아니다 (M1)

**Given** 실물 CSV와 FID·Group·Position만 바꾼 변형본, **When** 각각을 파싱해 자리 튜플 집합을 비교하면, **Then** 동일하다.

- 대상 요구사항: REQ-LXSEQ-003
- 검증 방법: `uv run pytest server/tests/test_lxseq_parser.py -q -k "fid_is_not_an_address"`
- 기대 결과:
  - ① 모든 FID에 +1000을 더한 CSV의 `{(universe,address)}` 집합이 원본과 같다.
  - ② `server/lxseq/` AST 스캔에서 `fid` 식별자가 `universe`/`address` 계산식·`normalize_address` 인자에 등장하지 않는다(비공허성 — 스캔된 함수 수 ≥ 3을 함께 단언).

### AC-LXSEQ-005 — 타입 해석은 resolve_fixture_type 계약으로만 (M2)

**Given** 녹화된 `resolve_fixture_type` payload 4종, **When** 매퍼를 부르면, **Then** `present`만 런에 들어간다.

- 대상 요구사항: REQ-LXSEQ-004
- 검증 방법: `uv run pytest server/tests/test_lxseq_mapper.py -q -k "type_resolution"`
- 기대 결과:
  - ① `present`(`resolved="Robin Spiider"`) → 해당 8행의 런 `console_type == "Robin Spiider"`(CSV 표기 `Robe Spiider`가 런에 나타나지 않는다).
  - ② `ambiguous`(candidates 2) → 그 타입 행 전부 `type_unresolved`, `detail`에 candidates 2개 동봉, 런에 0행.
  - ③ `absent` → `type_unresolved`, `detail`에 "콘솔에서 타입 추가" 안내.
  - ④ `library_unreadable` → 86행 전부 `type_unresolved`, `detail`에 "없다고 단정하지 않는다".
  - ⑤ 서로 다른 타입 8종에 대해 해석 호출이 **정확히 8회**(행 수 86회가 아니다).

### AC-LXSEQ-006 — 모드는 실측 폭으로 유일할 때만 (M2)

**Given** 타입별 실측 모드 목록, **When** 매퍼를 부르면, **Then** `console_mode`는 유일 일치일 때만 채워진다.

- 대상 요구사항: REQ-LXSEQ-005
- 검증 방법: `uv run pytest server/tests/test_lxseq_mapper.py -q -k "mode_resolution"`
- 기대 결과:
  - ① 모드 목록 `[("Mode 1", 39), ("Mode 2", 34)]` + `Ch=39` → `console_mode="Mode 1"`, `mode_resolution.resolution=="resolved"`.
  - ② `[("Basic", 25), ("Extended", 25)]` + `Ch=25`, `Mode="Extended 25ch"` → 토큰 `Extended`가 하나에만 포함 → `"Extended"`.
  - ③ `[("A", 49), ("B", 49)]` + `Ch=49`, `Mode="Mode 1 49ch"`(실물 `Robe Spiider` MOVER-D 8행의 값 — `Mode`·`1`·`49ch` 어느 토큰도 `A`/`B`에 없어 토큰으로도 못 가름) → 그 타입의 행 **전부** `skipped` `kind=="mode_unresolved"`, 런에 0행, `mode_resolution.resolution=="unresolved"`, `detail`에 `measured_modes` 2개와 `mode_overrides` 재호출 안내 문자열; 질문 카드(`question_port`) 호출 **0회**(결정 J — 카드 위임 없음).
  - ③-b 같은 입력 + `mode_overrides={"Robe Spiider": "B"}` → `console_mode=="B"`, `resolved_by=="override"`, 그 행들이 런에 들어간다; `mode_overrides={"Robe Spiider": "C"}`(실측 목록에 없음) → 여전히 `mode_unresolved`, `detail`에 "실측 목록에 없음"; 대소문자만 다른 `"b"`는 채택된다.
  - ④ 모드 트리 미판독(`type_found=False`) → `channels_per_fixture=Ch` + `footprint_source="caller_unverified"`, `resolution=="tree_unread"`; override가 있으면 그 이름이 검증 없이 `console_mode`로 실린다.
  - ⑤ 어느 경우에도 CSV `Mode` 문자열이 그대로 `console_mode`로 들어가지 않는다(`"Mode 1 39ch"`가 런에 0회).
  - ⑥ 비공허성: ③에서 `mode_unresolved` 건수 == 그 타입의 행 수(MOVER-D 8)이고, 다른 7타입의 런은 ③ 적용 전과 동일하다.

### AC-LXSEQ-007 — 점유 행은 건너뛰고 목록으로 (M2)

**Given** 인벤토리에 `2.001`(타입 X)·`4.026`(같은 타입 `Robin MAC Aura XB`) 점유, FID 집합에 301 포함, **When** 매퍼를 부르면, **Then** 해당 행만 건너뛴다.

- 대상 요구사항: REQ-LXSEQ-006
- 검증 방법: `uv run pytest server/tests/test_lxseq_mapper.py -q -k "occupied"`
- 기대 결과:
  - ① FID 501(2.001) → `address_occupied`, `occupant.address=="2.1"`, 런에 없음.
  - ② FID 202(4.026, 같은 타입·같은 시작 주소) → `already_patched`(별 부류), 런에 없음.
  - ③ FID 301 → `fid_occupied`, `occupied_fid==301`.
  - ④ 구간 **안에서 시작**하는 점유(`2.020`이 FID 501 구간 2.001~039 안)도 `address_occupied`; 구간 **앞**에서 시작해 뻗는 장비는 잡지 않는다 — **FID 502**(구간 2.040~078)에 대해 `2.030`(폭 미지) 점유자는 `address_occupied`가 **아니고** 계획에 `blind_spot` 문구가 동봉된다(`addressfit.evaluate("2.040", count=1, width=39, occupants=[2.030])` → `ok=True`·`collisions=0`·`blind_spot` 비어 있지 않음 — 실코드로 확인; 대조군 `2.050` 점유자는 `ok=False`·충돌 1). FID 501은 2.001 앞 주소가 없어 이 예시를 만들 수 없다(plan-audit D7).
  - ⑤ 건너뛴 3~4행을 뺀 나머지 행 수 == 런의 `count` 합(비공허성).
  - ⑥ 어떤 런의 `fids`/`address`에도 건너뛴 FID·자리가 없다.

### AC-LXSEQ-008 — 읽기가 전수가 아니면 런 0 (M2)

**Given** 절단된 인벤토리(`CONSOLE_READ_INCOMPLETE`) 또는 `read_existing_fids` 미해결>0, **When** 매퍼를 부르면, **Then** 런 0 · 전 행 `console_read_incomplete`.

- 대상 요구사항: REQ-LXSEQ-007
- 검증 방법: `uv run pytest server/tests/test_lxseq_mapper.py -q -k "read_incomplete"`
- 기대 결과:
  - ① 인벤토리 caveat 분기·FID 판독 분기 각각에서 `runs == []`, `skipped` 86건 전부 `console_read_incomplete`.
  - ② 같은 입력에서 읽기가 전수로 바뀌면 런이 생긴다(비공허성 — 게이트가 입력에 반응함).
  - ③ 계획에 `console_read.complete_enough_to_judge_absence == False`와 사유가 실린다.

### AC-LXSEQ-009 — 런 묶기 · FID 매핑표 (M2)

**Given** 실물 CSV · 빈 콘솔 · 타입 8종 `present` · 모드 전부 유일, **When** 매퍼를 부르면, **Then** 런 12개 · 86대.

- 대상 요구사항: REQ-LXSEQ-008
- 검증 방법: `uv run pytest server/tests/test_lxseq_mapper.py -q -k "runs"`
- 기대 결과:
  - ① `len(runs) == 12`(기본값 `name_prefix_mode="group"` — 결정 I 확정, 단언값 고정), `sum(r.count) == 86`, 각 런의 `address`가 그 런 첫 행의 `"U.A"`, `fids`가 CSV FID 그대로·순서대로. 런마다 `name_prefix`가 그 런의 `Group`이다(`"KEY"`, `"MOVER-D"` …).
  - ①-b `name_prefix_mode="type"`(비기본 선택 경로)이면 `Group`을 경계에서 빼고 묶어 `len(runs) == 9`·`sum == 86` — KEY+FOH(1.001–168, 14대) · BACK+SIDE-L(4.001–450, 18대 = BACK 12 + SIDE-L 6, 25ch) · WASH-U+WASH-D(5.151–330, 20대)가 각각 한 런으로 합쳐진다(실물 CSV 86행 직접 계산 — 10이 아니다, plan-audit D6).
  - ② 런 인자 키 집합 ⊇ `{"console_type","address","count","fids","name_prefix"}`이며 `patch_fixtures` `ToolDefinition.parameters.properties` 키의 부분집합이다(스키마 밖 키 0).
  - ③ KEY 런: `address=="1.1"`, `count==6`, `fids==[101..106]`, `channels_per_fixture==12`; MOVER-D 런: `address=="3.1"`, `count==8`, `fids==[521..528]`.
  - ④ `fid_map`의 키 집합 == CSV FID 86개, 값의 `run_index`가 전부 유효.
  - ⑤ 건너뛴 행이 런 중간(예: FID 504)에 있으면 MOVER-U가 **런 2개**(501~503 / 505~508)로 갈린다.

### AC-LXSEQ-010 — server/lxseq에 쓰기 수단 0 (M2)

**Given** `server/lxseq/**` 소스, **When** AST로 import·이름·문자열을 스캔하면, **Then** 금지 항목 0.

- 대상 요구사항: REQ-LXSEQ-009
- 검증 방법: `uv run pytest server/tests/test_lxseq_mapper.py -q -k "no_write_surface"` + `uv run pytest server/tests/test_architecture.py -q`
- 기대 결과:
  - ① import 모듈 중 `server.bridge`·`pythonosc`·`server.vwx.luagen`·`server.vwx.stagedpatch`·`server.deploy` 0건.
  - ② 식별자 `execution_port`·`deploy_pipeline`·`run_commands`·`deploy_plugin`·`AddFixtures`·`ChangeDestination` 0건; 문자열 리터럴에 `Plugin '` 0건.
  - ③ 스캔된 파일 수 ≥ 2(비공허성).

### AC-LXSEQ-011 — 툴 4지점 등재 · preview 쓰기 0 (M3)

**Given** 가짜 포트로 만든 `build_toolset`, **When** `import_lxseq_patch(action="preview")`를 부르면, **Then** 계획이 나오고 쓰기 포트는 한 번도 불리지 않는다.

- 대상 요구사항: REQ-LXSEQ-010 (preview 구간)
- 검증 방법: `uv run pytest server/tests/test_tools.py -q -k test_the_registered_tools_are_exactly_the_declared_set && uv run pytest server/tests/test_lxseq_tool.py -q -k "preview"`
- 선택자 비공허성(plan-audit D4 — 이전 `-k "closed or thirty"`는 0건 수집): `uv run pytest server/tests/test_tools.py --collect-only -q -k test_the_registered_tools_are_exactly_the_declared_set` → `server/tests/test_tools.py::TestRegistry::test_the_registered_tools_are_exactly_the_declared_set` / `1/71 tests collected (70 deselected)` (2026-08-21 실측). 뮤테이션 확인: 스크래치 사본에서 단언 상수 33→34로 바꿔 같은 `-k`로 돌리면 `1 failed, 70 deselected`(RED) — 선택자가 실제 단언에 닿는다(저장소 파일 무변경, `git status --short server/` 빈 출력).
- 기대 결과:
  - ① `sorted(definition names) == sorted(TOOL_NAMES)` 이고 `len(TOOL_NAMES) == 34`, `"import_lxseq_patch" in TOOL_NAMES`; 위 `-k` 선택자가 ≥1건을 수집한다(수집 0건이면 게이트가 공허 — FAIL로 친다).
  - ② `action` 생략 시 preview; 가짜 `deploy_pipeline.deploy` 호출 0회 · 가짜 `execution_port.execute` 호출 0회(호출 기록 리스트로 단언, 비공허성 — 같은 가짜로 `patch_fixtures`를 직접 부르면 1회 이상 기록됨).
  - ③ 페이로드에 `plan.runs` 12개 · `apply.entered == False` · `plan.write_count_planned == 86`.
  - ④ `file_content_base64`가 없거나 base64가 아니면 `is_error=True`와 한국어 사유.

### AC-LXSEQ-012 — apply는 patch_fixtures 위임 · 순차 · 중단 (M3)

**Given** 가짜 포트(재조회가 계획대로 생긴 것처럼 응답), **When** `apply`를 부르면, **Then** 런 순서대로 위임되고 첫 실패에서 멈춘다.

- 대상 요구사항: REQ-LXSEQ-010 (apply 구간), REQ-LXSEQ-013
- 검증 방법: `uv run pytest server/tests/test_lxseq_tool.py -q -k "apply"`
- 기대 결과:
  - ① 12런 전부 `created` 시나리오: `apply.runs` 12개 status 전부 `created`, 가짜 `deploy_pipeline.deploy` 호출 12회(타입별 플러그인), `run_commands` 경유 실행 12회, `summary_ko`에 "86대".
  - ② 3번째 런이 `created_partially`인 시나리오: `apply.runs[2].status=="created_partially"`, `apply.stopped_at==2`, 4~12번 런 `not_attempted`, `deploy` 호출 3회(4회 아님).
  - ③ `patch_fixtures`가 질문 카드로 모드를 묻는 시나리오(`question_port` UNANSWERED): 해당 런 `not_run`, 결과 `awaited_human` 전달, 이후 런 미실행.
  - ④ 위임은 `patch_fixtures` 핸들러를 **내부 `ToolCall`**로 부른다 — 가짜 포트 기록상 AddFixtures Lua 출처가 `luagen`(`FixtureTypes["…"]` 문자열 존재)이고 `server/lxseq/`는 Lua를 만들지 않는다(AC-LXSEQ-010과 교차).
  - ⑤ `only_fids=[101,102]`면 런 1개 · count 2.

### AC-LXSEQ-013 — 재실행 멱등 (M3)

**Given** ①차 `apply`가 86대를 만들어 가짜 콘솔 상태가 갱신됨, **When** 같은 파일로 `preview`와 `apply`를 다시 부르면, **Then** 런 0 · 쓰기 0.

- 대상 요구사항: REQ-LXSEQ-012
- 검증 방법: `uv run pytest server/tests/test_lxseq_tool.py -q -k "idempotent"`
- 기대 결과:
  - ① 2회차 `preview`: `plan.runs == []`, `skipped` 86건 전부 `already_patched`(타입 동일·주소 동일).
  - ② 2회차 `apply`: `deploy` 호출 0회, `apply.entered == True`이되 `apply.runs == []`, `summary_ko`에 "할 일 없음"류 문구, `is_error == False`.
  - ③ 절반(43대)만 만들어진 상태에서 재실행하면 남은 43대만 런에 들어가고 만들어진 43대는 `already_patched`(비공허성 — 부분 상태에서 게이트가 정확히 가른다).

### AC-LXSEQ-014 — 구조화 페이로드 · 한국어 · 성공 과장 금지 (M3)

**Given** 위 시나리오들의 페이로드, **When** 스키마와 문구를 검사하면, **Then** 닫힌 키·닫힌 어휘·정직한 요약이다.

- 대상 요구사항: REQ-LXSEQ-011, REQ-LXSEQ-014
- 검증 방법: `uv run pytest server/tests/test_lxseq_tool.py -q -k "payload or summary"`
- 기대 결과:
  - ① 최상위 키 집합 == `{source, types, console_read, plan, apply, summary_ko, guidance}`.
  - ② `skipped[*].kind` ⊆ 8종 닫힌 어휘; `source.rejected[*].kind` ⊆ 7종.
  - ③ 부분 생성(`created` 합 < 계획 합) 페이로드의 `summary_ko`에 "성공"·"완료" 문자열이 없고 "부분"이 있다; 전량 생성이면 "86대 … 확인".
  - ④ `apply.entered == False`일 때만 `summary_ko`에 "쓰기 0건"이 나온다(apply 후 `created_nothing`이면 "0건 생성"은 되지만 "쓰기 0건"은 아니다).
  - ⑤ `guidance`에 "status == created"·"덮어쓰지"·"콘솔에서 타입" 세 구절이 있다. 한국어 아닌 사용자 대면 문장 0건.

### AC-LXSEQ-015 — 회귀 · PRESERVE · 툴 수 (M3)

**Given** M3 완료 트리, **When** 전체 스위트와 diff 게이트를 돌리면, **Then** 회귀 0 · PRESERVE 0-diff.

- 대상 요구사항: REQ-LXSEQ-015
- 검증 방법: 아래 명령 전부.
- 기대 결과:
  - ① `uv run pytest server/tests -q` → 실패 0(착수 baseline 대비 증가분만 있고 감소 0).
  - ② `git diff --stat <BASE>..HEAD -- console/lua server/safety server/prechk server/vwx server/paperwork server/rulebook/assets` → 빈 출력(`<BASE>`는 `progress.md` §E.1 `base_sha`; 인자 없는 `git diff`로 대체 금지).
  - ③ `git diff <BASE>..HEAD -- server/orchestrator/tools.py | grep -c '^-[^-]'` ≤ **3**(등재 편집으로 허용되는 삭제 줄 상한 — `TOOL_NAMES` 튜플 · `ToolDefinition` 목록 · `handlers` 맵의 닫는 줄/끝 쉼표 줄 각 1), 그리고 `git diff <BASE>..HEAD -- server/orchestrator/tools.py | grep '^-[^-]'`로 나온 각 줄이 닫는 괄호·쉼표 줄임을 `progress.md`에 그대로 붙여 기록한다(기존 핸들러 본문 삭제 0).
  - ④ `uv run ruff check server/lxseq server/tests/test_lxseq_*.py` → 0건.
  - ⑤ 게이트 비공허성: PRESERVE 경로에 임시 한 줄을 넣으면 ②가 비지 않음을 확인하고 되돌린다.

### AC-LXSEQ-017 — 채팅 붙여넣기 금지 · 바이트 출처 대조 (M3)

**Given** `build_toolset`의 툴 정의와 실물 CSV 사본 바이트, **When** 정의·`guidance`·페이로드를 검사하면, **Then** 붙여넣기 금지가 명문이고 받은 바이트의 해시가 페이로드에 실린다.

- 대상 요구사항: REQ-LXSEQ-016 (결정 H — 입력 채널 `file_content_base64`, 바이트는 파일(현재 절차 t9: 로컬 하네스 스크립트가 읽음 / t10 이후: UI 파일 선택기)에서만 — 채팅 본문 텍스트에서는 절대 아니다; 서버는 파일 경로를 받지 않는다)
- 주: 감독이 금지한 것은 "사람이 CSV 본문을 채팅에 붙여넣어 그 텍스트로 바이트를 만드는 것"이며, M4에서 허용되는 것은 "로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출하는 것"이다 — 서버는 파일 경로를 받지 않는다(①의 키 집합 그대로); 채팅 경유 호출은 t10 이후. 따라서 본 AC의 붙여넣기 금지 보루와 AC-LXSEQ-016의 하네스 스크립트 절차는 양립한다.
- 검증 방법: `uv run pytest server/tests/test_lxseq_tool.py -q -k "paste or sha256"`
- 기대 결과:
  - ① `import_lxseq_patch`의 `ToolDefinition.description`과 `parameters.properties.file_content_base64.description`에 "붙여넣" 과 "파일 선택기" 두 구절이 있고("파일 선택기" 구절은 목표 상태 t10을 가리키는 문구로 쓴다 — 보루의 본질은 붙여넣은 텍스트 거부), `parameters.properties` 키 집합 == `{"file_content_base64","action","name_prefix_mode","only_fids","mode_overrides"}`, `required == ["file_content_base64"]`, `additionalProperties == False`.
  - ② `preview` 페이로드 `guidance`에 "붙여넣" 구절이 있다(모델에게 채팅 본문으로 base64를 만들지 말라고 말한다).
  - ③ 사본 바이트를 base64로 넘긴 `preview` 페이로드의 `source.sha256` == `hashlib.sha256(사본 바이트).hexdigest()`, `source.byte_length` == 사본 길이(비공허성 — 바이트 한 개를 바꾸면 `sha256`이 달라진다).
  - ④ 세션 업로드 포트(`vectorworks_upload`)는 이 툴이 읽지 않는다 — 가짜 포트 호출 기록 0회(결정 H 기각안 불사용).
  - ⑤ 이 AC는 UI가 실제로 파일 선택기로 인자를 채우는지를 검증하지 **않는다**(UI 전달 경로는 후속 카드 **t10**으로 위임됨 — plan.md §A.4 ① 잔여 메모); 툴 측 보루만 검증한다.

### AC-LXSEQ-016 — onPC 실기 확인 (M4 · 라이브 · 사용자 수행)

**Given** onPC 2.4.2.2에서 Patch 편집기를 연 빈 패치(또는 기록된 시작 상태) · 실물 CSV, **When** 사용자가 `preview` → `apply` → `preview` 순으로 부르면, **Then** 86대 생성이 재조회로 확인되고 재실행은 0건 쓰기다.

- 대상 요구사항: 없음 — 형상 전체(감독 결정 ② 실기 검증).
- 검증 방법: **이 검증은 기계 로컬이다(CI 대상 아님)** — 사용자 수행 + `progress.md` M4 절(명령·페이로드·콘솔 스크린샷 경로). 입력은 정본 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv`(사용자 측 절대경로)이다. **현재 절차(t9)**: 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님; `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview|apply --listen-port 9005`, `busking_e2e`·`groupgen_e2e`와 같은 DEV TOOL 계열)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출한다 — **서버는 파일 경로를 받지 않는다**(인자 집합 불변). 채팅 경유 호출은 t10 이후. **목표 상태(t10 이후)**: UI 파일 선택기로 올린다(본 카드 범위 밖). 어느 쪽이든 채팅 붙여넣기 금지(REQ-LXSEQ-016 — 금지 대상은 채팅 본문 텍스트로 바이트를 만드는 것이지 스크립트가 파일을 읽는 것이 아니다); 페이로드 `source.sha256`이 `sha256sum` 출력과 같음을 기록한다.
- 기대 결과:
  - ① `preview`: 타입 8종 해석 결과 기록(ASSUMPTION-72 판정) · 모드 해석 8건 기록(ASSUMPTION-73 — `mode_unresolved`가 나오면 `mode_overrides`로 재호출한 인자와 결과도 기록) · `console_read.complete_enough_to_judge_absence == True`(ASSUMPTION-74).
  - ② `apply`: 런마다 `status == created`, 합 86; 콘솔 Patch 창에서 FID 101~622 · 주소가 CSV와 일치(표본 6대 이상 육안 대조 기록).
  - ③ 재`preview`: 런 0 · `already_patched` 86.
  - ④ 시작 상태에 의도적으로 1대(예: `2.001`에 다른 타입)를 두고 시작했다면 그 행이 `address_occupied`로 건너뛰어지고 콘솔의 그 픽스처가 **변하지 않았다**(감독 결정 ③ 실기).
  - ⑤ 미통과 시 M4는 PASS로 닫히지 않고 결함이 블로커 보고로 M1~M3에 돌아간다.

---

## §D. 품질 게이트 · Definition of Done

- TRUST 5: 신규 모듈 커버리지 ≥ 85%(`uv run pytest --cov=server/lxseq`), `ruff check`/`ruff format --check` 0건, 비밀 0, Conventional Commits(`feat(SPEC-COPILOT-LXSEQ-001): M1 …`).
- DoD: AC-LXSEQ-001~015·017 PASS(오프라인) + AC-LXSEQ-016 PASS(사용자 실기) + PRESERVE 0-diff + `progress.md` §E.2/§E.3 채움. AC-LXSEQ-016이 미수행이면 `implemented`는 가능하나 `completed`는 불가(감독 결정 ②).
