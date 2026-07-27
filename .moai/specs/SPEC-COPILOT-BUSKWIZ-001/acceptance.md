# SPEC-COPILOT-BUSKWIZ-001 — 인수 기준 (acceptance)

status: draft (v0.1.4, 2026-07-27) · Tier L · 본 문서는 spec.md의 요구를 관측 가능한 검증 기준으로 전개한다.

> **v0.1.4 — 재감사(PASS 0.88) 조건부 지적 반영.** AC 17건·REQ 커버리지·마일스톤 배정 **무변경**. (재D2 부분 닫힘) AC-BUSKWIZ-004 구간 3의 열거에서 **"룩별 in-scope 풀 수 차이"를 삭제**했다 — 값 없는 패밀리는 `SkippedStore`를 만들지 않아(`server/looks/instantiate.py:332-334`) 그 룩은 완전 성공이며 보고할 건너뜀이 없다. 남은 트리거는 **풀 미해석**과 **라벨 충돌** 둘이고 **건너뜀 항목 비공허성** assert를 추가했다. §C.0의 REQ-BUSKWIZ-010 행 비고에 잔존하던 "원장 소진" 표현도 함께 교체했다. (재P3) §E·§F의 슬러그 없는 축약형 4건을 완전 토큰으로 교체 — 6종 전체 스캔 0건.
>
> **v0.1.3 — 독립 plan-audit(FAIL 0.78) 반영.** AC 17건·REQ 커버리지·마일스톤 배정은 **무변경**이며, 고친 것은 **검증 수단의 실효성**이다: AC-BUSKWIZ-004 구간 3(도달 불가 트리거 → 도달 가능 경로) · AC-BUSKWIZ-013 ②(소스 정규식 → 생성 커맨드 전수 + 비공허성) · AC-BUSKWIZ-014(`git diff` 베이스 리비전 + `instantiate.py` 추가) · AC-BUSKWIZ-012 ①(번호 출처를 ASSUMPTION-17과 정합) · AC-BUSKWIZ-002 ③(import 스캔 → AST) · §D 작은따옴표 항(등록부 밖 결정 → 미결 강등) · §E·§F의 게이트 문구.
>
> **v0.1.2 — ASSUMPTION-19 신설 반영.** §A 층위 · 시나리오 6 · §C.0 표 · AC-BUSKWIZ-012 · AC-BUSKWIZ-016(측정 항목 4).
>
> **v0.1.0 — 최초 작성.** AC 17건(001~017), REQ 20건(001~020) 전량 커버. 라이브 AC 2건(AC-BUSKWIZ-016 M0 프로브 / AC-BUSKWIZ-017 M7 종단)은 사용자 확정 ④의 라이브 세션 2회와 1:1 대응한다. §C.0 역추적표와 plan.md §B의 마일스톤별 `- **AC**:` 배정은 **1:1이며 한쪽을 고치면 다른 쪽도 고친다.**

## §A. 개요

성공 기준은 3개 층위로 나뉘고, **아래 층이 위 층을 대체하지 않는다**.

1. **데이터·로직 층 (유닛)** — 장르 조회의 결정론, 슬롯 원장의 비충돌, 번들 문자열의 형상, 보고의 완결성. 인메모리 픽스처로 전량 검증 가능하며 라이브를 요구하지 않는다.
2. **파이프라인 층 (통합)** — 툴 등록·디스패치·단일 실행 경로·LiveLock 강등. 목 포트로 검증한다.
3. **라이브 층** — ASSUMPTION-16/17/18/19의 실측(AC-BUSKWIZ-016)과 종단 왕복(AC-BUSKWIZ-017). 실물 grandMA3 onPC 없이 통과 판정할 수 없으며, **유닛 통과를 라이브 통과로 대체 인용하지 않는다.**

**부분 성공은 부분 성공으로 보고한다.** 저장 일부가 건너뛰어진 실행은 "성공"이 아니라 "부분 성공 + 건너뜀 N건"이며, AC는 그 구분이 관측 가능함을 검증한다.

**DESCOPE는 실패가 아니다.** AC-BUSKWIZ-016이 ASSUMPTION-16/17/19 중 **하나라도** 부정 판정하면 REQ-BUSKWIZ-016은 발동하지 않고, AC-BUSKWIZ-012는 **DESCOPE 경로**로 판정된다(AC-BUSKWIZ-012 ②). 이때 AC-BUSKWIZ-013의 "익스큐터 커맨드 0건"이 그 판정을 기계적으로 고정한다.

## §B. Given-When-Then 시나리오

### 시나리오 1 — 장르 일괄 팔레트 생성 (행복 경로)

- **Given** 리그에 Dimmer·Color 프리셋 풀이 존재하고 점유가 관측되며, 역할 어휘 6종 중 최소 1종이 그룹으로 매핑되고, 라이브러리에 워십 8룩이 있다.
- **When** 사용자가 "이 리그로 워십 버스킹 준비해줘"라고 지시하고 승인 카드를 승인한다.
- **Then** 리그는 **1회만** 해석되고, 8룩이 **하나의 번들**로 구성되며, `ChangeDestination Root`는 **선두 1회**, 각 룩의 프리셋은 **서로 다른 슬롯**에 저장되고, 완료 보고가 집계(생성 N개 / 건너뜀 M개 / 미매핑 역할 K종) + 룩별 판정 8행을 담는다.

### 시나리오 2 — 슬롯 원장의 비충돌 (본 SPEC의 존재 이유)

- **Given** Color 풀의 점유가 `(1, 2)`로 관측되었고 장르에 룩이 3개 있다.
- **When** 장르 번들을 구성한다.
- **Then** 세 룩의 Color 프리셋은 슬롯 **3, 4, 5**를 각각 청구하며 **어느 둘도 같은 슬롯을 겨냥하지 않는다.** (선행 구현을 그대로 N회 호출하면 셋 다 슬롯 3을 겨냥한다 — `server/looks/instantiate.py:307-312`, `:358`. 이 시나리오가 그 회귀를 고정한다.)

### 시나리오 3 — 정직한 축소: 점유 미관측

- **Given** Beam 풀의 점유가 관측되지 않았다(`binding.occupied is None`).
- **When** 그 풀에 값을 갖는 룩들의 번들을 구성한다.
- **Then** 해당 저장은 전부 `no_free_slot` 사유로 **건너뛰어지고** 보고에 풀·사유가 명시되며, 슬롯 1을 비었다고 가정한 저장은 **0건**이다.

### 시나리오 4 — 안전 방향의 충돌 처리

- **Given** Color 풀에 이미 이번 장르의 어떤 룩과 **같은 이름**의 프리셋이 있다.
- **When** 번들을 구성한다.
- **Then** 그 저장 1회만 `conflict`로 건너뛰어지고, 같은 룩의 다른 풀 저장과 다른 룩들은 **정상 진행**되며, `Store /Overwrite`와 재슬롯은 **0건**이다.

### 시나리오 5 — LiveLock 강등

- **Given** 시스템이 LiveLock 상태다.
- **When** 사용자가 버스킹 준비를 지시한다.
- **Then** 콘솔 송신은 **0건**이고, 결과는 실행이 아니라 **제안**으로 제시된다.

### 시나리오 6 — 익스큐터 DESCOPE (M0 부정 시)

- **Given** M0 프로브가 ASSUMPTION-16 · ASSUMPTION-17 · ASSUMPTION-19 중 하나라도 부정 판정했다.
- **When** 버스킹 준비를 실행한다.
- **Then** 산출물은 프리셋 팔레트뿐이고, 발화된 커맨드 중 `Executor`·`Page`를 대상으로 하는 것은 **0건**이며, DESCOPE 사유가 progress.md에 기록되어 있다.

## §C. AC (GEARS 형식 — 검증 레시피는 각 AC 하위 상세로 보존)

### §C.0 REQ ↔ AC 역추적표

| REQ | 커버하는 AC | 담당 M | 비고 |
|---|---|---|---|
| REQ-BUSKWIZ-001 | AC-BUSKWIZ-001 | M1 | 절단 없음 + 결정론적 전순서 |
| REQ-BUSKWIZ-002 | AC-BUSKWIZ-002 | M1 | 한/영 별칭 + 정직한 실패 |
| REQ-BUSKWIZ-003 | AC-BUSKWIZ-014 | M6 | PRESERVE diff 빈 출력으로 검증 |
| REQ-BUSKWIZ-004 | AC-BUSKWIZ-003 | M2 | 해석 호출 횟수 assert |
| REQ-BUSKWIZ-005 | AC-BUSKWIZ-004 | M2 | 슬롯 원장 — 시나리오 2 고정 |
| REQ-BUSKWIZ-006 | AC-BUSKWIZ-005 | M2 | 번들 문자열 형상 |
| REQ-BUSKWIZ-007 | AC-BUSKWIZ-006 | M2 | Overwrite·재슬롯 0건 |
| REQ-BUSKWIZ-008 | AC-BUSKWIZ-015 | M6 | 정적 자산 스캔 0건 |
| REQ-BUSKWIZ-009 | AC-BUSKWIZ-007 | M2 | 미관측 ≠ 빈 풀 |
| REQ-BUSKWIZ-010 | AC-BUSKWIZ-004 | M2 | 혼합 부분 성공 — 구간 3(풀 미해석 / 라벨 충돌) |
| REQ-BUSKWIZ-011 | AC-BUSKWIZ-009 | M4 | AST 식별자 스캔 |
| REQ-BUSKWIZ-012 | AC-BUSKWIZ-009 | M4 | 동일 AC 구간 ② |
| REQ-BUSKWIZ-013 | AC-BUSKWIZ-008 | M3 | 집계 + 룩별 2단 |
| REQ-BUSKWIZ-014 | AC-BUSKWIZ-010 | M4 | LiveLock 강등 |
| REQ-BUSKWIZ-015 | AC-BUSKWIZ-008 | M3 | 한국어 1급 — 동일 AC 구간 ④ |
| REQ-BUSKWIZ-016 | AC-BUSKWIZ-012 | M5 | GO/DESCOPE 양 분기 |
| REQ-BUSKWIZ-017 | AC-BUSKWIZ-013 | M5 | page*100 하드코딩 0건 |
| REQ-BUSKWIZ-018 | AC-BUSKWIZ-013 | M5 | dotted form 발화 0건 |
| REQ-BUSKWIZ-019 | AC-BUSKWIZ-011 | M4 | 툴 등록 관례 + is_error 규약 |
| REQ-BUSKWIZ-020 | AC-BUSKWIZ-011 | M4 | 리그 직접 읽기 — 동일 AC 구간 ③ |
| (REQ 무연결 — 전역 게이트) | AC-BUSKWIZ-014 | M6 | 전체 회귀, 협상 불가 |
| (ASSUMPTION-16/17/18/19 실측) | AC-BUSKWIZ-016 (LIVE) | M0 | 라이브 세션 1/2 |
| (종단 통합) | AC-BUSKWIZ-017 (LIVE) | M7 | 라이브 세션 2/2 |

**마일스톤별 AC 집합**: M0 = {016} · M1 = {001, 002} · M2 = {003, 004, 005, 006, 007} · M3 = {008} · M4 = {009, 010, 011} · M5 = {012, 013} · M6 = {014, 015} · M7 = {017}. **17개 AC가 정확히 한 번씩 나타난다(001~017, 중복·누락 0).**

### §C.1 AC 본문

### AC-BUSKWIZ-001 — 장르 룩 집합의 절단 없는 결정론적 조회

**When** 장르 식별자로 룩 집합을 조회하면, the 시스템 **shall** 그 장르의 모든 룩을 절단 없이, 다이내믹스 오름차순 → `look_id` 사전순의 전순서로 반환한다.

- 대상 요구사항: REQ-BUSKWIZ-001
- 검증 방법: `pytest server/tests/test_busking_genre.py -q` — 4장르 각각에 대해 반환 개수가 라이브러리 실측치(worship 8 / rock 8 / ballad 7 / edm 9)와 일치함을 assert.
- 기대 결과: 전량 PASS.
- 추가 assert: ① **edm 9룩이 9건 그대로 반환**된다 — `MAX_TOOL_MATCHES = 8`(`server/looks/matching.py:71`) 경로를 타지 않았음을 이 한 케이스가 증명한다. ② 반환 리스트에 `truncated` 신호가 존재하지 않는다. ③ 같은 입력에 대해 2회 호출 결과가 리스트 동등(순서 포함).

### AC-BUSKWIZ-002 — 장르 별칭 해석과 정직한 실패

**When** 사용자 발화에서 장르를 해석하면, the 시스템 **shall** 기존 `GENRE_ALIASES`로 한/영 표현을 해석하고, 해석 불가 시 후보 목록과 함께 실패를 반환한다.

- 대상 요구사항: REQ-BUSKWIZ-002
- 검증 방법: `pytest server/tests/test_busking_genre.py -q` — 한국어 표현(워십/록/발라드/EDM)과 영어 슬러그 각각이 동일 장르로 해석됨을 assert.
- 기대 결과: 전량 PASS.
- 추가 assert: ① 미해석 입력("재즈")은 예외가 아니라 **후보 4종을 담은 실패 결과**를 반환한다. ② 미해석 입력이 가장 유사한 장르로 **승격되지 않는다**(반환된 장르 필드가 `None`). ③ 별칭 표는 본 SPEC이 새로 만들지 않고 `server/looks/matching.py`의 것을 참조한다 — **AST 스캔**으로 판정한다: 신규 모듈의 AST에서 장르명 문자열(한/영 어느 쪽이든)을 **키 또는 값으로 갖는 dict/set 리터럴이 0건**이고, `GENRE_ALIASES`·`resolve_genre`에 닿는 경로가 import뿐이다. (import 스캔으로는 판정할 수 없다 — "import도 해 두고 로컬 보정표도 하나 더 둔" 형태가 정확히 이 SPEC이 경계해야 할 모양인데, import의 존재는 그 공존을 배제하지 못한다. REQ-BUSKWIZ-015의 한국어 표현 매핑이 바로 그 유혹을 만든다.)

### AC-BUSKWIZ-003 — 리그 1회 해석의 전 룩 재사용

**When** 장르 번들을 구성하면, the 시스템 **shall** `resolve_roles`와 `resolve_pools`를 각각 정확히 1회만 호출한다.

- 대상 요구사항: REQ-BUSKWIZ-004
- 검증 방법: `pytest server/tests/test_busking_bundle.py -q` — 호출 카운팅 스파이로 룩 8개짜리 장르 번들 구성 시 각 해석 함수의 호출 횟수를 assert.
- 기대 결과: `resolve_roles` 1회, `resolve_pools` 1회. 룩 수에 비례하는 호출은 실패로 판정한다.

### AC-BUSKWIZ-004 — 슬롯 원장: 어떤 두 룩도 같은 슬롯을 겨냥하지 않는다

**When** 하나의 리그 해석으로 N개 룩의 번들을 구성하면, the 시스템 **shall** 풀 패밀리별로 슬롯을 누적 청구하여 동일 슬롯 재청구를 0건으로 만든다.

- 대상 요구사항: REQ-BUSKWIZ-005 / REQ-BUSKWIZ-010
- 검증 방법: `pytest server/tests/test_busking_bundle.py -q` — 구간별 개별 테스트(병합 금지).
- 기대 결과: 전량 PASS.
- 검증 구간:
  1. **비충돌**: 점유 `(1,2)` + 룩 3개 → Color 슬롯 청구가 `{3,4,5}`이고 중복 0건.
  2. **선행 구현 회귀 고정**: 같은 입력을 `build_instantiation`에 룩마다 동일 `PoolIndex`로 직접 N회 호출하면 **전부 슬롯 3**이 나옴을 별도로 assert한다 — 결함이 실재함과 본 SPEC의 계층이 그것을 감쌌음을 함께 고정한다.
  3. **혼합 부분 성공 (도달 가능한 트리거 — v0.1.3 감사 D2, v0.1.4에서 열거 1건 삭제)**: 같은 번들 안에서 어떤 룩은 저장되고 어떤 룩은 건너뛰어지는 상태를, **실제로 발생 가능한** 두 경로로 각각 고정한다 — (i) 특정 풀만 `pool_unresolved`/`pool_unaddressable`이라 그 풀 대상 저장만 전량 건너뛰어진다(`_plan_stores`의 `binding.reason` 분기, `server/looks/instantiate.py:336-345`), (ii) 콘솔에 같은 이름의 프리셋이 있어 `conflict`로 건너뛰어진다(`:359-371`). 두 경우 모두 저장 가능한 것은 저장되고 전량 실패로 되돌아가지 않으며 **건너뜀 항목이 비어 있지 않다**(비공허성). **삭제된 열거 — "룩별 in-scope 풀 수 차이"는 부분 성공이 아니다**: 값이 없는 패밀리는 `if not values: continue`로 넘어가 `SkippedStore`를 만들지 않으므로(`:332-334`) `planned=P, skipped=0, complete=True`가 나온다(실행 확인: `ballad-single-key` P=4 / `ballad-moonlight` P=2 둘 다). 이 경로로 "건너뜀이 있다"를 assert하면 거짓이 된다. **"슬롯 상한 소진"도 검증 대상이 아니다** — `_first_free_slot`(`:307-312`)에 상한이 없고 리포지토리에 풀 용량 상수가 0건이며 `_observed_contents`(`:195-215`)가 풀 크기를 보고하지 않으므로 그 상태는 발생할 수 없고, 테스트하려면 SPEC이 정의한 적 없는 용량 상수를 발명해야 해 REQ-BUSKWIZ-008을 위반한다.
  4. **패밀리 독립**: Dimmer 원장과 Color 원장은 서로 영향을 주지 않는다.
  5. **관측 우선**: 원장의 시작값은 항상 콘솔이 보고한 `occupied`이며, 원장이 있다고 해서 미관측 풀이 사용 가능해지지 않는다(AC-BUSKWIZ-007과 한 쌍).
  6. **라벨 원장**: 표시 이름이 같은 두 룩을 담은 합성 라이브러리로 번들을 구성하면, 두 번째 룩의 저장이 `conflict`로 건너뛰어진다 — 콘솔에 기존 라벨이 없어도 그렇다(`_plan_stores`는 `binding.labels`만 보므로 이 판정은 원장이 만든다).

### AC-BUSKWIZ-005 — 번들 형상: `ChangeDestination Root` 정확히 1회

**When** 장르 번들이 구성되면, the 번들 **shall** `ChangeDestination Root`를 선두에 정확히 1회 포함하고 룩 단위 `ClearAll` 규율을 유지한다.

- 대상 요구사항: REQ-BUSKWIZ-006
- 검증 방법: `pytest server/tests/test_busking_bundle.py -q` — 번들 커맨드 튜플에 대한 문자열 수준 assert.
- 기대 결과: 전량 PASS.
- 추가 assert: ① `commands.count("ChangeDestination Root") == 1` 이고 `commands[0]`이 그것이다. ② 각 룩 캡처 사이클 앞과 각 `Store` 후에 `ClearAll`이 있고 번들 말미도 `ClearAll`이다. ③ 룩별 번들을 단순 연접한 형상이 아님을 고정 — 룩 2개 번들에서 `ChangeDestination Root`가 2회 나타나면 실패. ④ 이 형상이 `run_commands` dedupe를 통과해도 **한 줄도 잃지 않음**을 목 실행 포트로 확인(`skipped_already_executed` 0건). ⑤ **캡처 형상이 `shared_capture`로 고정**되어 있다 — 장르 번들 빌더에 `per_family_capture`로 진입하는 경로가 0건이고, 4장르 32룩 전수에 대해 **한 번들 안의 값 라인 문자열 중복이 0건**임을 assert한다(중복이 생기면 두 번째 값 라인이 dedupe로 탈락해 빈 프로그래머로 `Store`가 실행된다 — spec.md REQ-BUSKWIZ-006 하위 절).

### AC-BUSKWIZ-006 — 파괴적 저장 0건

**The** 번들 **shall not** `Store /Overwrite`를 발화하거나 점유된 슬롯을 재슬롯한다.

- 대상 요구사항: REQ-BUSKWIZ-007
- 검증 방법: `pytest server/tests/test_busking_bundle.py -q` + `grep -rniE "store\s*/\s*overwrite" server/looks/ server/orchestrator/` → 0건.
- 기대 결과: 모든 생성 번들에서 `/Overwrite` 포함 라인 0건. 라벨 충돌 케이스에서 슬롯이 재계산되어 다른 슬롯에 저장되는 일이 없음(충돌 = 건너뛰기 하나).

### AC-BUSKWIZ-007 — 점유 미관측은 빈 풀이 아니다

**While** 어떤 in-scope 풀의 점유가 관측되지 않았으면, the 시스템 **shall** 그 풀 대상 저장을 전부 `no_free_slot`으로 건너뛴다.

- 대상 요구사항: REQ-BUSKWIZ-009
- 검증 방법: `pytest server/tests/test_busking_bundle.py -q` — `occupied=None` 픽스처로 assert.
- 기대 결과: 해당 풀의 `Store Preset` 라인 0건, 건너뜀 항목에 풀 번호와 사유가 담김. `occupied=()`(검증된 빈 풀)와 `occupied=None`(미관측)이 **서로 다른 결과**를 내는 것을 별도 테스트로 고정.

### AC-BUSKWIZ-008 — 집계 + 룩별 2단 구조화 보고 (한국어 1급)

**When** 버스킹 준비가 완료되면, the 시스템 **shall** 집계와 룩별 판정을 함께 담은 구조화 요약을 한국어 1급으로 보고한다.

- 대상 요구사항: REQ-BUSKWIZ-013 / REQ-BUSKWIZ-015
- 검증 방법: `pytest server/tests/test_busking_report.py -q`
- 기대 결과: 전량 PASS.
- 검증 구간:
  1. **집계**: 생성 프리셋 수 · 건너뜀 수 · 미매핑 역할 수가 룩별 합계와 산술적으로 일치한다(불일치는 실패).
  2. **(a) 생성 목록**: 모든 생성 프리셋의 풀·슬롯·이름이 빠짐없이 담긴다.
  3. **(b) 미매핑 역할**: 매칭 판정 3종(`ambiguous`·`no_match` — `server/looks/roles.py:22-23`; `unaddressable` — `server/looks/resolver.py:50`)과 **섹션 실패 전파 사유**(`server/looks/resolver.py:128-137`가 모든 역할에 그대로 붙이는 문자열)가 **서로 다른 부류로 구분되어** 담긴다. 그룹 섹션이 오지 않은 픽스처로 실행했을 때 결과가 "매칭 실패"로 보고되면 실패로 판정한다. 집계 단위는 `(룩, 역할)` 쌍이고 distinct 역할 목록은 별도 필드로 병기된다.
  4. **(c) 건너뜀 단위**: 건너뜀 카운트의 단위가 **프리셋 저장 1회**임을 고정 — 한 룩에서 2개 풀이 건너뛰어지면 카운트는 1이 아니라 2다.
  5. **(d) 룩별 판정**: 장르의 모든 룩이 정확히 한 번씩 `complete` / `partial` / `none` 중 하나로 나타난다.
  6. **(e) 미실행과 건너뜀의 분리**: `run_commands`가 stop-on-first-failure로 남긴 `not_executed`(`server/orchestrator/tools.py:527-536`, `:562`)가 건너뜀 카운트와 **별도 항목**으로 실린다. 한 실행 결과에 두 종류가 함께 있을 때 두 수를 합산한 단일 숫자만 내는 보고는 실패로 판정한다. 자동 재시도 경로가 존재하지 않음도 함께 assert.
  7. **한국어**: 사용자 대면 문자열이 한국어이며, 그 매핑이 라이브러리 자산이나 스키마가 아니라 **표현 계층 코드**에 있다(자산 파일 diff 빈 출력으로 교차 확인 — AC-BUSKWIZ-014).

### AC-BUSKWIZ-009 — 단일 실행 경로

**When** 번들이 실행되면, the 시스템 **shall** 기존 `run_commands` → `gate.screen()` 경로로만 실행한다.

- 대상 요구사항: REQ-BUSKWIZ-011 / REQ-BUSKWIZ-012
- 검증 방법: `pytest server/tests/test_busking_tool.py -q` + AST 식별자 스캔.
- 기대 결과: 전량 PASS.
- 검증 구간:
  1. **AST 스캔**: 본 SPEC이 신규·수정한 모듈에서 `ast.Attribute.attr` / `ast.Name.id` / import 이름 중 `execution_port` · `ConsoleLink` 직접 접근이 **0건**. (raw 텍스트 grep이 아니라 AST인 이유: 텍스트 스캔은 "호출"과 "호출을 설명하는 독스트링"을 구분하지 못한다 — `LOOKLIB spec.md:34` v0.3.2가 같은 이유로 수단을 교체했고 `server/tests/test_looks_resolver.py:509-529`에 동형 스캔이 이미 있다.)
  2. **신규 실행 표면 0**: 신규 REST 라우트·웹소켓 메시지 타입 추가 0건.
  3. **게이트 통과 확인**: 목 게이트가 승인 보류를 반환하면 콘솔 송신이 0건이다.

### AC-BUSKWIZ-010 — LiveLock 제안 강등

**While** LiveLock 상태이면, the 시스템 **shall** 실행하지 않고 제안으로 강등한다.

- 대상 요구사항: REQ-BUSKWIZ-014
- 검증 방법: `pytest server/tests/test_busking_tool.py -q`
- 기대 결과: LiveLock 픽스처에서 실행 포트 호출 0건, 반환이 제안 형태이며 `is_error=False`(답변인 결과이지 기술적 실패가 아니다).

### AC-BUSKWIZ-011 — 툴 등록 관례 준수

**The** 신규 툴 **shall** 기존 등록 관례를 그대로 따르고, 리그 데이터를 모델 인자로 받지 않는다.

- 대상 요구사항: REQ-BUSKWIZ-019 / REQ-BUSKWIZ-020
- 검증 방법: `pytest server/tests/test_busking_tool.py -q`
- 기대 결과: 전량 PASS.
- 검증 구간:
  1. **등록 정합**: `TOOL_NAMES`·`definitions`·`handlers` 3곳에 신규 툴이 모두 존재하고 이름이 일치한다(하나라도 누락 시 실패).
  2. **is_error 규약**: 정정 가능한 실수(알 수 없는 장르 키)는 `is_error=True`, **답변인 실패**(저장 0건, LiveLock 강등)는 `is_error=False`.
  3. **리그 직접 읽기**: 툴 파라미터 스키마에 그룹·풀·슬롯·픽스처를 담는 필드가 **0개**이며, 핸들러가 `collect_rig_sections` 계열로 직접 읽는다.

### AC-BUSKWIZ-012 — 익스큐터 레이아웃 GO/DESCOPE 양 분기

**Where** ASSUMPTION-16 · ASSUMPTION-17 · ASSUMPTION-19가 **셋 다** M0에서 긍정 실측된 경우, the 시스템 **shall** 익스큐터 레이아웃을 생성한다. 그렇지 않으면 관련 커맨드를 0건 발화하고 사유를 기록한다.

- 대상 요구사항: REQ-BUSKWIZ-016
- 검증 방법: `pytest server/tests/test_busking_executor.py -q` — M0 판정 결과에 따라 아래 둘 중 **정확히 하나**를 실행한다.
- 기대 결과:
  - ① **GO 분기**: 발화되는 익스큐터 커맨드가 **AC-BUSKWIZ-016 측정 항목 4(ASSUMPTION-19)가 실측한 형식 하나뿐**이고, 그 안의 익스큐터 번호는 **AC-BUSKWIZ-016 측정 항목 2가 GO로 판정한 "빈 익스큐터 식별 경로"가 반환한 번호**에서만 온다. **`resolved_executor_nos`를 출처로 못박지 않는다(v0.1.3 — 감사 D5)**: 그 함수는 `meta["resolved"] is True` 항목만 반환하므로(`server/web/dash.py:309-327`) 출력이 정의상 **점유된** 익스큐터 목록이고, 그것을 출처로 쓰면 운영자가 쓰던 플레이백을 덮는다(design.md 위험 #4 — "라벨 검사로 걸러지지 않는다"). ASSUMPTION-17이 묻는 것은 정확히 그 반대(**비어 있는** 익스큐터의 판별)이므로, GO는 곧 **지금 없는 새 질의 경로가 발견되었다**는 뜻이며 번호의 출처도 그 경로다. 따라서 AC-BUSKWIZ-016 측정 항목 2의 산출물에는 **그 경로의 식별자와 반환 형상**이 포함되어야 한다.
  - ② **DESCOPE 분기**: 생성 번들에 `Executor`·`Page`를 대상으로 하는 커맨드가 0건이고, DESCOPE 사유가 progress.md M0 절에 기록되어 있다.
- 비고: 두 분기 중 실행되지 않은 쪽은 `skip` 사유를 명시한 채 남긴다 — 삭제하지 않는다(후속 SPEC이 게이트를 다시 열 때 필요하다).

### AC-BUSKWIZ-013 — 익스큐터 주소 금지 규율

**The** 시스템 **shall not** `page_no*100 + slot`을 일반 규칙으로 하드코딩하거나 `Page <p>.<e>` dotted 주소형을 발화한다.

- 대상 요구사항: REQ-BUSKWIZ-017 / REQ-BUSKWIZ-018
- 검증 방법: 정적 스캔 + `pytest server/tests/test_busking_executor.py -q`
- 기대 결과: 전량 PASS.
- 추가 assert: ① 본 SPEC이 추가한 코드에서 리터럴 `100`을 익스큐터 번호 산술에 쓰는 지점 **0건**(AST 스캔). ② **소스 정규식이 아니라 빌더가 실제로 생성한 커맨드 튜플 전수**에 대해 `Page \d+\.\d+` 패턴 **0건**임을 assert하고, **그 스캔이 빈 리스트가 아님**(비공허성)을 함께 assert한다. **소스 grep은 쓰지 않는다(v0.1.3 — 감사 D3)**: REQ-BUSKWIZ-008이 번호 리터럴을 이미 0건화했으므로 dotted form이 실제로 발화되는 유일한 형태는 `f"Page {page}.{executor}"` 같은 변수 조립이고, 그 소스 문자열에는 숫자가 없어 `[0-9]+\.[0-9]+`가 결코 매치하지 않는다 — 즉 소스 스캔은 **금지 대상이 구현될 수 있는 유일한 경로를 구조적으로 볼 수 없다.** 같은 규율을 AC-BUSKWIZ-009 구간 1이 이미 적용했다(raw 텍스트 → AST). ③ 익스큐터 번호가 `page*100+slot`로 **계산되어** 커맨드에 들어가는 경로 0건 — 번호는 조회 결과에서만 온다.

### AC-BUSKWIZ-014 — PRESERVE 무변경 + 전체 회귀

**The** 본 SPEC **shall not** PRESERVE 목록의 파일을 변경하며, 기존 테스트 스위트에 신규 실패를 만들지 않는다.

- 대상 요구사항: REQ-BUSKWIZ-003 + (전역 게이트)
- 검증 방법: `git diff --stat <BASE>..HEAD -- server/looks/schema.py server/looks/loader.py server/looks/roles.py server/looks/resolver.py server/looks/instantiate.py server/looks/library/ server/safety/ server/web/preview.py console/lua/ server/rulebook/assets/` → **빈 출력**. `<BASE>`는 **run-phase 킥오프에서 기록한 착수 SHA**이며 progress.md §E.2에 남긴다. 이어서 전체 스위트 실행.
- 기대 결과: PRESERVE diff 빈 출력. 전체 스위트의 신규 실패 **0건**(baseline은 각 마일스톤이 착수 직전 직접 실측한 수에 귀속한다 — 이월 인용 금지).
- **베이스 리비전이 필수인 이유 (v0.1.3 — 감사 D4)**: 인자 없는 `git diff`는 **워킹트리 vs 인덱스**를 비교하므로, 마일스톤마다 커밋을 남기는 이 워크플로에서는 PRESERVE 파일을 실제로 고쳤더라도 M6 시점에는 출력이 비어 있다 — 그 게이트는 "지키고 있는지"가 아니라 "**방금** 손대지 않았는지"만 본다. 본 SPEC은 baseline 이월 인용을 금지할 만큼 측정 규율에 엄격하므로(spec.md §C "측정된 기준선"), PRESERVE 검증도 기준점을 갖는다.
- 추가 assert: `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 dedupe 블록이 **무변경**임을 같은 `<BASE>..HEAD` diff로 확인 — 본 SPEC의 `tools.py` 변경은 신규 툴 등록으로 한정된다(§D). `server/looks/instantiate.py`가 목록에 있는 것은 **결정 E의 반증을 기계적으로 드러내기 위함**이다(spec.md §A PRESERVE 하위 절) — 이 파일에 diff가 생기면 "원장이 바깥에서 감싼다"는 형상이 성립하지 않았다는 뜻이고, 그것은 사용자 확인이 필요한 사건이다.

### AC-BUSKWIZ-015 — per-show 값의 정적 진입 금지

**The** 본 SPEC **shall not** 그룹·풀·슬롯·FID·익스큐터 번호를 정적 데이터에 넣는다.

- 대상 요구사항: REQ-BUSKWIZ-008
- 검증 방법: 신규·수정 파일 전체에 대한 정적 스캔.
- 기대 결과: 번호 리터럴이 커맨드 문자열 조립에 직접 쓰이는 지점 **0건**. 모든 번호는 리그 조회 결과 객체의 필드에서 온다.
- 추가 assert: 신규 YAML·JSON 자산 **0개**(본 SPEC은 자산을 추가하지 않는다). 풀 번호를 `4`(Color) 같은 룰북 예시 값으로 기본값 지정하는 코드 0건.

### AC-BUSKWIZ-016 — M0 라이브 프로브 (LIVE — 2건 중 1번째, M0)

**When** 실물 grandMA3 onPC 2.4.2에서 M0 프로브를 수행하면, the 프로브 **shall** ASSUMPTION-16/17/18/19 각각에 대해 GO 또는 DESCOPE 판정을 근거와 함께 확정한다.

- 대상 요구사항: (ASSUMPTION-16/17/18/19 실측 — REQ-BUSKWIZ-016의 게이트)
- 검증 방법: 실물 콘솔 세션. 코드 변경 0. 측정 결과는 `progress.md` §E.2 M0 절에 원문 로그와 함께 기록한다.
- 기대 결과: **4건 전부** 판정 확정. **판정 미확정으로 M1을 착수하지 않는다** — ASSUMPTION-18이 미확정이면 번들 규모 정책이 미정이고, 16/17/19 중 하나라도 미확정이면 REQ-BUSKWIZ-016의 발동 여부가 미정이다.
- 측정 항목:
  1. **ASSUMPTION-16**: 페이지·익스큐터 저작 커맨드가 2.4.2에서 수용되는가. 측정은 **콘솔이 실제로 받아들이는 문자열**을 찾는 것이지 `corpus.yaml`의 mock 문자열을 확인하는 것이 아니다(`corpus.yaml:8-10`이 mock 전용임을 자인).
  2. **ASSUMPTION-17**: 비어 있는 익스큐터를 열거·판별할 수 있는가. 현재 드릴다운은 존재하는 자식만 열거한다(`server/web/dash.py:200-206`).
  3. **ASSUMPTION-18**: **87행 번들**(edm · 4풀 — spec.md §A "번들 규모의 실측")이 한 번의 왕복에서 절단·타임아웃 없이 왕복하는가. 실측 최대는 21줄이므로 미측정 구간은 약 4배다. 더 작은 합성 번들에서의 통과는 GO 근거가 되지 못하며, **실제로 몇 줄을 보냈는지**를 수치로 남긴다. 함께: 중도 실패 시 어느 지점에서 끊기고 프로그래머 상태가 어떻게 남는지(REQ-BUSKWIZ-013 (e)).
  4. **ASSUMPTION-19**: 프리셋을 익스큐터에 직접 얹는 문법이 존재하는가. 리포지토리 근거 0건이며(`Assign Preset` · `Preset <p>.<s> At (Executor|Page) <n>` · `Store Executor` 계열 전부 0건), 라이브 검증된 바인딩의 목적어는 시퀀스다(`31_choreography_patterns.md:99`). **찾지 못하면 답은 DESCOPE이며, 시퀀스를 만들어 우회하는 측정은 하지 않는다**(§D가 시퀀스 생성을 금지하므로 그 측정은 범위 밖 기능의 근거가 된다).
  5. **정리 기록**: 프로브가 쇼파일에 남긴 것과 그 무해성을 기록한다.
  6. **미검증 항목(Gaps)**: 측정하지 못한 것을 명시적으로 남긴다.
- 비고: 라이브 접근 불가 시 M1 착수를 **보류**하고 사유를 progress.md에 기록한다. 예외 진행은 **익스큐터 축을 DESCOPE로 선(先)확정**하는 것으로만 성립하며(그 경우 REQ-BUSKWIZ-016은 발동하지 않고 AC-012는 ② 분기로 판정), ASSUMPTION-18은 여전히 미확정이므로 번들 규모 위험이 열린 채 남는다는 사실을 함께 기록한다.

### AC-BUSKWIZ-017 — 종단 라이브 검증 (LIVE — 2건 중 2번째, M7)

**When** 실물 콘솔에서 장르 1개의 버스킹 준비를 종단 실행하면, the 시스템 **shall** 계획한 번들과 콘솔이 실제로 실행한 것이 일치함을 보이고, 생성 결과를 재조회로 확인한다.

- 대상 요구사항: (종단 통합 — B.1~B.3 전체)
- 검증 방법: 실물 콘솔 세션. 툴 반환의 per-command status와 감사 로그를 대조한다.
- 기대 결과:
  1. `console.executed == plan.commands` — **한 줄도 잃지 않는다**(특히 `ChangeDestination Root` 1건과 모든 `ClearAll`).
  2. `skipped_already_executed` **0건** — AC-BUSKWIZ-005 ④의 유닛 판정이 실물에서 재현된다.
  3. 생성된 프리셋이 재조회에서 **서로 다른 슬롯**에 존재한다(슬롯 원장의 라이브 확인).
  4. 보고의 집계 수치가 재조회 실측과 일치한다.
- 비고: 응답기는 프리셋 **내용**을 읽을 수 없다는 LOOKLIB M0 교차 발견을 계승한다 — 검증은 슬롯·라벨의 존재 수준이며, 그 한계를 결과에 명시한다.

## §D. Edge Cases

- **장르에 룩이 1개뿐**: 원장은 정상 동작하며 단일 룩 경로와 동일한 번들이 나온다(퇴화 케이스가 특수 분기를 만들지 않는다).
- **역할이 하나도 매핑되지 않음**: 선택할 그룹이 없으므로 번들은 **빈 채로** 반환되고 미매핑 역할 전량이 보고된다 — 대체 그룹을 발명하지 않는다(`server/looks/instantiate.py:456-460` 계승).
- **드릴다운 상한 도달**: `drilldown_capped` 신호가 보고에 그대로 전달된다 — 상한에 걸린 관측을 완전한 관측으로 취급하지 않는다.
- **룩 표시 이름에 작은따옴표**: `LookInstantiationError`가 발생한다(`instantiate.py:315-322`). 장르 번들이 **그 룩 하나만 실패로 보고하고 나머지를 계속**할지, 번들 전체를 거부할지는 **v1이 정하지 않는다 — 미결로 남긴다(v0.1.3 — 감사 D6).** 현행 32룩의 `display_name`에 작은따옴표는 **0건**이고 라이브러리 증보는 §D Out of Scope이므로 이 분기는 **도달 불가**다. v0.1.2까지 여기에 "번들 전체 거부(fail-closed)"라고 적혀 있었으나 그것은 (i) 어느 REQ에도 근거가 없는 **결정 등록부 밖의 8번째 결정**이었고, (ii) "저장 가능한 것을 저장하고 전량 실패로 되돌리지 않는다"(REQ-BUSKWIZ-010 · plan.md §A.3 정직한 축소)와 **반대 방향**이었다. 라이브러리에 해당 이름이 들어오는 순간 이것은 정식 결정 항목으로 열리며, 그때 사용자 확인을 거친다.
- **같은 장르를 연속 2회 실행**: 1회차가 만든 프리셋의 라벨이 2회차에서 `conflict`로 전량 건너뛰어진다 — 멱등이 아니라 **정직한 중복 거부**이며, 보고가 "N개 건너뜀(이미 존재)"을 명시한다.
- **번들이 danger로 승격되는 경우**: 프리셋 값에 `At 100`/`Full`이 있으면 `caution`(`server/web/preview.py:159-172`). 라이브러리에 스트로브/셔터는 0건이므로 `danger` 승격 경로는 v1에 없다 — 있다면 그것은 라이브러리 오염 신호다.

## §E. Quality Gate 기준

- `pytest server/tests/ -q` — 신규 실패 0건.
- `ruff check` — 신규 경고 0건. (기존 비-clean 지점은 무관 재포맷을 피해 손대지 않으며, 그 사실을 progress.md에 기록한다.)
- PRESERVE 목록 `git diff --stat <BASE>..HEAD` — **빈 출력**(AC-BUSKWIZ-014; `<BASE>` = run-phase 착수 SHA, 인자 없는 `git diff`는 커밋 후 항상 비므로 금지).
- `@MX:ANCHOR` 무변경 — `server/safety/gate.py:260-265`, `server/orchestrator/tools.py:686-696`.
- 정적 스캔 0건: `Store /Overwrite` · `Page <n>.<n>` 발화 · 익스큐터 번호 산술 리터럴 · per-show 번호 정적 진입.
- 라이브 산출물 2건: M0 프로브 기록(AC-BUSKWIZ-016), M7 종단 기록(AC-BUSKWIZ-017).

## §F. Definition of Done

1. REQ-BUSKWIZ-001~020 전량이 §C.0 역추적표에서 최소 1개 AC로 커버되어 있고, 표가 최종 REQ 목록과 일치한다.
2. AC-BUSKWIZ-001~017이 전부 PASS 또는 (익스큐터 축의 경우) **정의된 DESCOPE**로 판정되었다.
3. 장르 4종 각각에 대해 일괄 팔레트 생성이 유닛 층에서 종단 통과한다.
4. **슬롯 원장이 기계적으로 고정되어 있다** — AC-BUSKWIZ-004 구간 2가 선행 구현의 결함과 본 계층의 해소를 함께 assert한다.
5. **번들 무손실이 유닛과 라이브 양쪽에서 확인되었다** — AC-BUSKWIZ-005 ④ + AC-BUSKWIZ-017 ①②.
6. 보고가 집계와 룩별 판정을 모두 담고, 건너뜀 단위가 프리셋 저장 1회다.
7. 익스큐터 축이 GO/DESCOPE 중 하나로 **명시 판정**되었고, DESCOPE면 관련 커맨드 0건이 스캔으로 확인된다.
8. PRESERVE 무변경 확인: 위 §E의 `git diff --stat <BASE>..HEAD`가 빈 출력이다(`server/looks/instantiate.py` 포함). `tools.py`의 변경이 신규 툴 등록으로 한정됨이 확인된다.
9. P1-1 기능(음원 분석·타임코드·시퀀스 생성)과 포지션 팔레트·무브먼트 인스턴스화가 본 SPEC의 커밋 범위에 등장하지 않는다(§D 범위 경계).
