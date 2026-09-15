# 인수기준 — SPEC-LDSTORE-001

[요구사항](spec.md) · [구현 계획](plan.md) · 우산 계약: [contract.md](../SPEC-LDPLUGIN-001/contract.md)

## 1. 판정 수단과 그 한계

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한 판정
근거다. 아래 모든 기준은 로컬에서 판정 가능하도록 작성했으며, 원격 체크 초록에 의존하는
기준은 없다.

기준선 (2026-09-14, HEAD `98a822e`, 이 프로젝트에서 실측): `12794 passed, 31 skipped` — 166.21s.
회귀 판정은 이 숫자와의 대조다.

**증거 규율**: 각 기준의 PASS 는 그 기준의 검증 명령을 **실제로 돌려서 본 출력**으로만
주장한다. 명령을 안 돌린 항목은 PASS 가 아니라 **Gap** 으로 적는다. 실패 신호가 없다는 것은
통과의 증거가 아니다.

## 2. 기준 — REQ 와 1:1

id 는 우산에서 승계한다 (`../SPEC-LDPLUGIN-001/spec.md:45` — id 는 파일 이동과 무관하게 유지).

| AC | REQ | 종류 | 기준 |
|---|---|---|---|
| AC-LDPLUGIN-007 | 007 | S+D | **Given** 다섯 정상 message_type fixture 와, unknown field · 잘못된 version · null · NaN · 중복 key · invalid UTC · 초과 크기/cue/group/action · 잘못된 ref 입력, **When** 수신, **Then** 정상 shape 만 허용하고 계약 code + JSON Pointer 를 반환한다. invalid 제출은 revision 0 · write 0. |
| AC-LDPLUGIN-015 | 015 | D+H | **Given** head revision N 에 두 제출자, **When** 같은 `expected_revision` 으로 동시 submit, **Then** 하나만 N+1 이고 다른 것은 `REVISION_CONFLICT`. 재시작 후 과거 revision 조회 시 원본 bytes 의미 · digest · `base_revision` 이 불변이다. |
| AC-LDPLUGIN-004 | 004 | D+H | **Given** 동일 slot 의 preset/content 또는 group/show/compiler/destination occupancy 변경, **When** context 조회 또는 승인 재검사, **Then** digest/binding 이 바뀌고 이전 승인 사용이 차단된다. unreadable 을 confirmed 로 승격하지 않는다. |
| AC-LDPLUGIN-027 | 027 | S+D+H | **Given** design §3 의 5주제 seed, **When** 검색, **Then** bounded typed rule 절차 · case 내용/outcome · feedback 변경 상세가 inline 제공되고 provenance · 조건 · 예외 · 검토 revision · 권리 범위가 남는다. current context 변경 시 cursor 는 stale 이고, 미승인 지식은 0 이다. |

종류 표기는 우산 `acceptance.md` 와 같다 — S=schema/static, D=결정적(합성 입력), H=사람 확인.

## 3. 기준별 검증 명령

### AC-LDPLUGIN-007 — 교환 스키마 strict parsing

```bash
uv run pytest server/tests/test_director_exchange_schema.py -q
```

**PASS 조건**: 다섯 정상 fixture 통과 + 아래 거부 케이스가 **각각** 계약 code 와 JSON Pointer 를
동반해 거부. **거부 사유 code 문자열을 단언한다** — 단순히 "거절됨" 은 불충분하다
(거짓 사유로 먼저 거절되면 참 사유가 안 보인다).

code 는 우산 `contract.md` §5 의 안정 code 표에서 가져온 실제 값이다.

| 거부 케이스 | 기대 code | HTTP | 추가 단언 |
|---|---|---|---|
| unknown field | `SCHEMA_INVALID` | 422 | `details[].field` 가 해당 필드의 JSON Pointer, revision 생성 0 |
| `schema_version` ≠ `1.0.0` | `UNSUPPORTED_SCHEMA_VERSION` | 422 | 응답에 `supported_schema_versions: ["1.0.0"]` **필수** |
| 파싱 불가 JSON | `INVALID_JSON` | 422 | revision 생성 0 |
| `null` 사용 (어느 필드든) | `SCHEMA_INVALID` | 422 | 계약 §2 — `null` 은 어디에서도 쓰지 않는다 |
| NaN / Infinity / 비유한 수 | `SCHEMA_INVALID` | 422 | 계약 §2 |
| 중복 key | `SCHEMA_INVALID` | 422 | **JCS 정규화 *전에* 거부** (§9) |
| invalid UTF-8 | `SCHEMA_INVALID` | 422 | 계약 §2 |
| `Time` 이 `Z` 로 끝나지 않음 / 달력상 불가 | `SCHEMA_INVALID` | 422 | RFC3339 UTC + 달력 유효성 |
| `Id` 가 `[A-Za-z0-9][A-Za-z0-9._-]{0,95}` 위반 | `SCHEMA_INVALID` | 422 | |
| `Digest` 가 `sha256:` + 소문자 64 hex 아님 | `SCHEMA_INVALID` | 422 | 형식 검사는 진위 검사가 아님을 주석에 남긴다 |
| `Revision` 0 (단, `base_revision`/`expected_revision` 제외) | `SCHEMA_INVALID` | 422 | 범위 1..2147483647 |
| `Ms` 범위 초과 (0..86400000) / duration 0 | `SCHEMA_INVALID` | 422 | |
| plan > 2 MiB | `PAYLOAD_TOO_LARGE` | 413 | |
| cues > 2048 / controlled groups > 256 / cue당 actions > 128 | `SCHEMA_INVALID` | 422 | 계약 §2 상한 |
| `environment` 가 서버 deployment 와 불일치 | `SCHEMA_INVALID` | 422 | 클라이언트가 `synthetic` 으로 바꿔 production 검사를 우회 못 함 |
| path/body 의 project/plan ID 불일치 | `IDENTITY_MISMATCH` | 422 | |
| 잘못된 ref | 의미 검사 (LD-REF-001) | — | 스키마가 아니라 의미 층. §2 참고 |

**ErrorEnvelope shape 단언** (계약 §3):
`{error:{code, message, details:[{field, rule_id?, message}], request_id, supported_schema_versions?}}`
— `field` 는 JSON Pointer 또는 빈 문자열, `details` 최대 128, `message` 최대 4096 chars.
**stack trace · token · filesystem 경로가 출력에 없어야 한다** (이것도 단언한다).

**양성 대조 필수**: 정상 fixture 다섯(`context_snapshot`·`lighting_plan`·`validation_report`·
`feedback_record`·`execution_receipt`)이 실제로 통과하는지 같은 실행에서 확인한다. 전부 거부하는
파서도 모든 거부 케이스를 "통과"시키므로, 양성 대조 없이는 이 기준이 공허하다.

**양성 대조 필수**: 정상 fixture 다섯이 실제로 통과하는지 같은 실행에서 확인한다. 전부 거부하는
파서도 모든 거부 케이스를 "통과"시키므로, 양성 대조 없이는 이 기준이 공허하다.

### AC-LDPLUGIN-015 — 불변 저장 · CAS

```bash
uv run pytest server/tests/test_director_store_cas.py -q
```

**PASS 조건** (계약 §10 · §9.2 · §9.7):
1. `expected_revision` 은 `plan.base_revision` 과 **같아야 한다**. 다르면 거부.
2. **신규 plan_id** → 둘 다 `0`, 서버 revision `1`. **기존 plan_id** → 현재 head 와 같아야 하고
   revision = head+1. 어긋나면 `REVISION_CONFLICT` (409).
3. 같은 `expected_revision` 두 제출 → 정확히 하나가 N+1, 다른 하나가 `REVISION_CONFLICT` (409).
   둘 다 성공하거나 둘 다 실패하면 FAIL.
4. schema-invalid 제출은 **revision 을 만들지 않는다** — `SELECT count(*)` 불변 (write 0).
5. 프로세스 재시작 후 과거 revision 조회 → 원본 bytes 의미 · plan digest · `base_revision` 이
   제출 시점과 동일. plan digest 는 `sha256(UTF-8(JCS(LightingPlan 전체)))` 이며
   **envelope 의 `expected_revision`/`idempotency_key` 와 서버 PlanRecord metadata 는 제외**,
   `base_revision`·`provenance`·`rationale` 은 **포함**한다 (§9.2).
6. **`PlanRecord.plan` 은 제출 그대로다 — `base_revision` 을 서버 revision 으로 덮어쓰지
   않는다** (§3 Envelope). 이걸 별도로 단언한다.
7. 저장 성공 후 상태: validation blocked → `needs_revision`, 통과 → `ready_for_review`.
   `submitted` 는 검증 완료 전 durable 내부 상태다.
8. 멱등: 같은 `(project_id, principal_id, operation, idempotency_key)` + 같은 request
   fingerprint → 최초 status·body 그대로 replay. 같은 key + 다른 request → `IDEMPOTENCY_CONFLICT`
   (409). fingerprint 는 `sha256(JCS({operation, project_id, principal_id, request}))` 이고
   `request` 는 body 에서 `idempotency_key` 만 제거한 객체다 (§9.7).

**주의**: DB 파일을 지우고 다시 만드는 방식으로 "불변"을 확인하지 않는다. 재시작 후 **같은
파일에서 되읽어** 확인한다.

**JCS 주의** (§9): key 정렬 + 규정 number 직렬화. **Unicode normalization 은 하지 않는다.**
중복 key 는 **정규화 전에** 거부한다. raw bytes digest 에는 JCS 를 적용하지 않는다.

### AC-LDPLUGIN-004 — ContextSnapshot 과 binding 무효화

```bash
uv run pytest server/tests/test_director_context_snapshot.py -q
```

**PASS 조건**:
1. snapshot 이 audio · show · group membership · preset 내용 · compiler · capability · 정책 ·
   identity · 만료 아홉 축을 **모두** 담는다 (필드 존재를 단언).
2. 아홉 축 중 하나라도 바뀌면 digest 가 바뀌고, 이전 digest 로 만든 승인은 차단된다.
3. **읽을 수 없는 값은 `unknown` 으로 남는다.** `confirmed` 로 승격하면 FAIL.
   특히 `COUNT 0` 을 "부재 확인" 으로 기록하면 FAIL — 내용 있는 Group 이 0 을 답한 실측
   사례가 있다 (우산 `research.md`).

**계기 주의**: 필드가 `None` 인 것과 키가 없는 것은 다르다. `.get()` 은 둘을 같은 `None` 으로
답하므로, 키 유무는 `in` 으로 단언한다.

### AC-LDPLUGIN-027 — 지식 seed

```bash
uv run pytest server/tests/test_director_knowledge_seed.py -q
```

**PASS 조건**:
1. seed 주제가 정확히 5개이고, 각 항목이 provenance · 조건 · 예외 · 검토 revision · 권리 범위를
   가진다 (다섯 필드 존재를 단언).
2. 검색 결과가 bounded inline typed details 를 담는다 — 요약 문자열이 아니라 typed 구조여야 한다.
3. current context 가 바뀌면 이전 cursor 가 `stale` 로 답한다.
4. 미승인 지식이 검색에 노출되지 않는다 (`count == 0`).
5. 응답 어디에도 사례/retrieval memory 를 "강제 법칙" 또는 "학습된 가중치" 로 표시하지 않는다.

### 경계 기준 (모든 마일스톤 공통)

```bash
# 이 층은 OSC 를 만지지 않는다
grep -rn "server.bridge" server/director/ ; test $? -ne 0 && echo "PASS: no OSC import"

# 이 층은 예술 판정을 호출하지 않는다
grep -rn "songcue\|_ARC_\|map_sections_to_looks" server/director/ ; test $? -ne 0 && echo "PASS: no artistic producer"

# 회귀
uv run pytest -q
```

**PASS 조건**: 두 grep 이 각각 0 매치. `uv run pytest` 가 기준선 대비 실패 0 · skipped 31 유지.

**양성 대조**: grep 자체가 동작하는지 확인한다 — `grep -rn "def " server/director/` 가 매치를
내는지 같은 회차에서 본다. 매치 0 이 "깨끗함" 인지 "grep 이 헛돎" 인지 구분되지 않으면
이 기준은 공허하다.

## 4. go / no-go

**go 조건 (전부 충족)**:
- 위 네 AC 가 각각 PASS — 검증 명령을 실제로 돌린 출력이 인용되어 있다.
- 경계 기준 두 grep 이 0 매치이고 양성 대조가 매치를 냈다.
- `uv run pytest` 실패 0, skipped 31.
- 계약 §2·§5·§9·§10 과 구현 스키마의 대조가 기록되어 있다.

**no-go**:
- AC 중 하나라도 검증 명령 출력 없이 PASS 로 표시된 경우.
- 계약과 구현 스키마가 어긋난 채 남은 경우.
- 회귀 실패가 하나라도 있는 경우.

## 5. 이 SPEC 이 판정하지 않는 것

- **콘솔 게이트 없음.** 이 층은 실기 콘솔 없이 전부 닫힌다. 형제 중
  `LDCOMPILE`(013) · `LDRECV`(021·024) · `LDCERT`(030) 가 실기 게이트를 가진다.
- **연출 품질을 판정하지 않는다.** 이 층은 판단을 하지 않으므로 예술 품질 기준이 없다.
- **왕복 전체를 판정하지 않는다.** 얇은 왕복의 관측은 `LDUI` 와 `LDRECV` 쪽 기준이다.

## 6. 미검증 (Gaps — 작성 시점)

- 우산 `contract.md` 는 **§2(wire 규칙)·§3(envelope·ErrorEnvelope)·§5(인증·오류 code)·
  §6.1(ContextSnapshot)·§6.2(LightingPlan)·§9(hash)·§10(state machine·저장) 을 읽었다**
  (2026-09-14). AC-007·AC-015 의 code·pointer·digest scope 는 그 실제 값으로 채웠다.
  **아직 안 읽은 절**: §4(APP human routes)·§6.3~6.5·§7(typed action 의미·timing)·
  §8(semantic rule IDs)·§11(예제 묶음). §7·§8 은 `LDCOMPILE` 의 것이고 §4 는 `LDRECV` 의
  것이므로 이 자식의 범위 밖이다.
- 우산 `design.md` §3 의 지식 seed 5주제가 무엇인지 확인하지 않았다. AC-LDPLUGIN-027 의
  "5개" 는 우산 REQ 본문의 "design §3의 검토된 rule/case seed" 와 `plan.md` §2 M4 의
  "seed 5주제" 표기에서 가져온 숫자이며, design 본문으로 대조하지 않았다.
- 이 자식 SPEC 에 대한 독립 plan-audit 이 없다.
