# 구현 계획 — SPEC-LDSTORE-001

[요구사항](spec.md) · [인수](acceptance.md) · 우산: [계약](../SPEC-LDPLUGIN-001/contract.md) · [설계](../SPEC-LDPLUGIN-001/design.md) · [근거](../SPEC-LDPLUGIN-001/research.md)

## 1. 착수 경계

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 다 —
`.moai/config/sections/quality.yaml` `constitution.development_mode: tdd`.

이 계획은 **Implementation Kickoff Approval 을 아직 받지 않았다.** 우산
`SPEC-LDPLUGIN-001/spec.md:23` 과 같은 조건이 승계된다. 승인 없이 구현을 시작하지 않는다.

## 2. 마일스톤

| 단계 | REQ | 파일 소유 | 완료 산출물 | 얇은 왕복 기여 |
|---|---|---|---|---|
| M1 교환 스키마·불변 저장 | 007, 015 | 신규 `server/director/{__init__,models,store,service}.py`, `server/director/migrations/001_initial.sql`; 기존 `server/web/serve.py` data-root wiring **EXTEND** | 다섯 message_type strict parsing, closed schema 거부, immutable plan/revision, `base_revision=expected_revision` CAS, server digest, SQLite transaction | **예 — 필수** |
| M2 ContextSnapshot | 004 | 신규 `server/director/context.py` | audio·show·group membership·preset 내용·compiler·capability·정책·identity·만료를 묶은 server-owned snapshot + digest/binding 재검사 | **예 — 최소판만** |
| M3 지식 seed | 027 | 신규 `server/director/knowledge.py`, `server/director/knowledge_seed/` | design §3 의 검토된 rule/case seed 5주제, provenance·조건·예외·권리 범위, bounded inline typed details, cursor↔current context 결합 | 아니오 — 유보 |

M1 → M2 → M3 순서. M2 는 M1 의 revision/digest 를 binding 에 쓰므로 M1 뒤다. M3 는 독립이지만
얇은 왕복에 필요하지 않으므로 마지막이다.

### 2.0 형제와의 이음새 — validator seam (계약 읽고 발견, 2026-09-14)

계약 §3 이 `SubmitResult = {record:PlanRecord, validation:ValidationReport}` 로 정의한다. 즉
**제출이 검증을 호출한다.** 그런데 검증은 `SPEC-LDCOMPILE-001` 의 소유다 — 이 자식이 혼자
`ld_submit_plan` 을 완결할 수 없다.

**해결: validator 를 주입 가능한 seam 으로 둔다.** `service.py` 는 검증기를 인자로 받고
직접 구현하지 않는다. M1 단계의 기본 구현은 *"검증 미구현"* 을 blocked 로 답하는 stub 이다.

이것이 계약 위반이 아닌 근거 — 계약 §10 이 이미 그 상태를 정의한다:

> *"저장 성공 후 validation이 blocked면 needs_revision, 통과하면 ready_for_review.
> submitted는 저장 후 검증이 끝나기 전 durable 내부 상태이며 처리 장애 시 재개한다."*

따라서 M1 은 `submitted → needs_revision` 경로를 정직하게 구현하고, `ready_for_review` 는
`LDCOMPILE` 이 실제 검증기를 끼울 때 처음 도달한다. **stub 이 통과를 답하게 만들면 안 된다** —
검증 없이 `ready_for_review` 를 내는 것은 계약이 막으려는 바로 그 상태다.

[HARD] stub validator 는 **blocked 만** 답한다. 이걸 테스트로 고정한다.

### 2.1 얇은 왕복(내부 마일스톤)에서 이 층이 내는 것

감독 결정(2026-09-14): 얇은 왕복은 **출시가 아니라 내부 마일스톤**이다. 표현 범위 축소는
"영구 unsupported" 가 아니라 "아직 안 만든 단계"이며, 출시 조건은 우산 계약 §7 전체로
그대로 남는다 (우산 `spec.md:41` 과 충돌하지 않는다).

이 층이 얇은 왕복에 내는 것은 **M1 전체 + M2 최소판**이다:

- M1 전체 — 스키마·저장·CAS 는 줄일 수 없다. 계획을 받아 보관하지 못하면 왕복이 성립하지 않는다.
- M2 최소판 — 아래 규칙을 따른다. **줄이는 것은 각 축의 풍부함이고, 축의 존재가 아니다.**
- M3 (지식 seed) — 유보. 왕복 관측에 필요하지 않다.

#### M2 최소판의 불변식 (안전 구멍 방지)

[HARD] **아홉 축 전부가 snapshot 에 존재해야 하고, digest 는 아홉 축 전부로 계산해야 한다.**
못 읽는 축은 값을 `unknown` 으로 남기되 축 자체를 빼지 않는다.

아홉 축: audio · show · group membership · preset 내용 · compiler · capability · 정책 ·
identity · 만료 (`REQ-LDPLUGIN-004`).

근거: `AC-LDPLUGIN-004` 는 *"동일 slot 의 preset/content 또는 group/show/compiler/destination
occupancy 변경 → digest/binding 이 바뀌고 이전 승인 사용이 차단된다"* 를 요구한다. digest 를
일부 축으로만 계산하면 **빠진 축이 바뀌어도 이전 승인이 유효하게 남는다** — preset 내용이
바뀐 리그에 옛 승인이 적용될 수 있다. 승인 무효화가 안전 장치이므로 그 장치에 구멍을 내는
축소는 허용하지 않는다.

같은 AC 의 *"unreadable 을 confirmed 로 승격하지 않는다"* 가 바로 이 경우를 위한 조항이다 —
읽히지 않는 축은 `unknown` 으로 정직하게 남기면 되고, 그래도 digest 에는 참여한다.

**M2 최소판에서 실제로 유보되는 것** (풍부함만):
- audio — 근거 요약 수준까지. 전체 분석 산출물 연결은 M2 나머지.
- preset 내용 — 점유·이름까지 (값은 애초에 못 읽는다 — 우산 `research.md`).
- capability — 선언된 범위까지. 실제 compiler+rig+target 출력 기반 광고는 `LDCOMPILE`(013).

**M2 최소판에서 유보되지 않는 것**: 아홉 축의 존재, digest 계산 범위, binding 무효화 동작.

## 3. PRESERVE — 건드리지 않는다

우산 `research.md` 와 인계 문서 §3 이 "이미 작동한다"고 기록한 것들. 이 SPEC 의 범위 밖이다.

| 영역 | 파일 |
|---|---|
| OSC 송신 (서버 유일 표면) | `server/bridge/osc.py` — 이 층은 import 하지 않는다 |
| 3단 안전 게이트 | `server/safety/{gate,grammar,classify,expand,lock,approval,backup}.py` |
| 리그·공간 | `server/spatial/{pointing,mib,preflight,presets}.py` |
| 라이브러리 | `server/fx/`, `server/looks/` (FX 22개 · 룩 34개) |
| 예술 producer 둘 | `server/looks/songcue.py`, `server/web/session.py` `_ARC_*` — cutover 는 후속 SPEC |
| 앱 표면 | `server/web/{app,messages,handshake}.py`, `ui/src/` |
| 데스크톱 빌드 | `src-tauri/` |

`server/web/serve.py` 는 **EXTEND** 대상이다 (data-root wiring 한 곳). 그 외 기존 파일 수정 없음.

### 3.1 공유 파일 직렬화

우산 `plan.md` §2 가 동시 작성을 금지한 넷 — `server/orchestrator/tools.py`,
`server/web/session.py`, `server/web/app.py`, `server/safety/gate.py` — 중
**이 SPEC 이 쓰는 것은 하나도 없다.** 충돌 없음.

## 4. TDD 순서 (M1 예시)

1. **RED** — `server/tests/test_director_exchange_schema.py`: 다섯 정상 fixture 통과 +
   unknown field / 잘못된 version / null / NaN / 중복 key / invalid UTC / 초과 크기 / 잘못된
   ref 가 각각 계약 code + JSON Pointer 로 거부되는지. 먼저 실패를 확인한다.
2. **GREEN** — `models.py` + strict parser 최소 구현.
3. **RED** — `server/tests/test_director_store_cas.py`: 같은 `expected_revision` 동시 submit →
   하나만 N+1, 다른 것은 `REVISION_CONFLICT`. 재시작 후 과거 revision 의 bytes 의미·digest·
   `base_revision` 불변.
4. **GREEN** — `store.py` + `001_initial.sql`.
5. **REFACTOR** — `service.py` 로 facade 정리. 테스트 초록 유지.

각 단계마다 `uv run pytest` 전체를 돌려 기준선 `12794 passed, 31 skipped` 가 깨지지 않는지 본다.

## 5. 검증 명령

```bash
# 이 SPEC 범위
uv run pytest server/tests/test_director_ -q

# 회귀 (기준선 대조)
uv run pytest -q          # 기대: 12794 + 신규 통과, skipped 31, 실패 0

# 경계: 이 층이 OSC 를 import 하지 않는지
grep -rn "server.bridge.osc\|from server.bridge" server/director/ || echo "OK - no OSC import"

# 경계: 예술 producer 를 호출하지 않는지
grep -rn "songcue\|_ARC_\|map_sections_to_looks" server/director/ || echo "OK - no artistic producer"
```

**CI 는 과금 차단으로 죽어 있어 판정 근거가 아니다.** 위 로컬 명령의 출력만 증거로 쓴다.

## 6. 중단 조건

- 스키마 strict parsing 이 우산 `contract.md` §2/§5 와 어긋나는 것이 발견되면 **중단하고
  보고한다.** 계약이 단일 원본이므로 자식이 임의로 다르게 구현하지 않는다.
- `contract.md` 52.7KB 전문은 이 계획을 세울 때 읽지 않았다(§7 미검증). M1 착수 전에
  §2·§5·§9·§10 을 읽어 스키마·저장 조항을 대조하는 것이 첫 작업이다.
- DB 스키마가 형제(`LDRECV` 의 journal·idempotency)와 충돌하면 중단하고 우산 수준에서 조정한다.

## 7. 미검증 (착수 전 남은 것)

- **우산 `contract.md`(52.7KB) 전문 미독.** §2·§5(교환)·§9·§10(저장) 을 M1 착수 시 읽어야 한다.
- **우산 `design.md`(15.9KB) §3(지식 seed 5주제) 미독.** M3 착수 시 필요하다.
- **LOC 추정 없음.** Tier M(300~1000 LOC)으로 잡았지만 실제 규모는 재지 않았다.
- **계획 내용에 대한 독립 판정 없음.** 우산의 Phase 1 Plan Audit Gate 는 감사관이 컨텍스트
  초과로 죽어 통과하지 못했다(INCONCLUSIVE). 이 자식에 대한 plan-audit 은 별도로 필요하다.
