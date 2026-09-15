---
id: SPEC-LDSTORE-001
title: "Director 교환 스키마·불변 저장·context snapshot·지식 seed"
version: "0.1.0"
status: in-progress
created: 2026-09-14
updated: 2026-09-15
author: jaihyun
priority: P1
phase: "Lighting Director v1.0 target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, exchange-schema, immutable-store, context-snapshot, knowledge-seed"
tier: M
---

# SPEC-LDSTORE-001

## 1. 목적과 경계

외부 `lighting-director` 플러그인이 만든 계획을 copilot 이 **받아서 보관하고, 무엇을 근거로
만들었는지 되짚을 수 있게** 하는 층이다. 판단은 하지 않는다 — 스키마 검사, 불변 저장,
context 제공, 검토된 지식 제공까지다.

이 SPEC 은 `SPEC-LDPLUGIN-001` 을 쪼갠 여섯 자식 중 **의존 뿌리**다. 나머지 다섯은 모두
이 층의 canonical plan/revision 자료구조와 `ContextSnapshot` 을 소비한다.

### 1.1 우산 SPEC 과의 관계

`SPEC-LDPLUGIN-001` 은 `superseded` 가 아니라 **우산으로 유지**된다. wire shape·tool·HTTP·
state·hash 의 단일 원본은 우산의 `contract.md` 이고, 컴포넌트·절차·지식·저장·UI 결정은
우산의 `design.md`, 현재 코드 근거·한계는 우산의 `research.md` 다. 이 자식은 그것들을
재정의하지 않고 참조한다.

| 규범 | 위치 |
|---|---|
| wire shape·state·hash·의미 규칙 | `../SPEC-LDPLUGIN-001/contract.md`, `../SPEC-LDPLUGIN-001/schemas/exchange.schema.json` |
| 컴포넌트·저장·지식 결정 | `../SPEC-LDPLUGIN-001/design.md` |
| 현재 코드 근거·한계 | `../SPEC-LDPLUGIN-001/research.md` |
| 분할 근거·형제 목록 | `../../reports/ldplugin-001/split-proposal.md` |

### 1.2 REQ / AC id 보존

`../SPEC-LDPLUGIN-001/spec.md:45` 가 *"아래 ID는 구현 파일 이동과 무관하게 유지하며 AC
번호와 1:1 대응한다"* 고 규정한다. 따라서 이 자식은 **원래 `REQ-LDPLUGIN-0NN` / `AC-LDPLUGIN-0NN`
id 를 그대로 승계**한다. 새 번호를 붙이면 `contract.md` 의 조항 참조가 끊긴다.

이 SPEC 이 소유하는 id: `REQ-LDPLUGIN-004`, `007`, `015`, `027` (4건).

## 2. 범위 결정

- 저장은 **SQLite** 다 (`server/director/migrations/001_initial.sql`). 기존 앱의 data-root
  wiring(`server/web/serve.py`)을 재사용하며 별도 DB 서버를 세우지 않는다.
- 제출된 계획은 **불변**이다. 수정은 새 revision 이며, 과거 revision 의 원본 bytes·의미·
  digest·`base_revision` 은 바뀌지 않는다.
- 동시 제출은 `base_revision = expected_revision` **CAS** 로 직렬화한다. 하나만 성공하고
  나머지는 `REVISION_CONFLICT` 다.
- 기존 `SongTimelineLibrary` / UI timeline 은 **읽기 projection 으로만** 남는다. timeline JSON
  을 계획 원본으로 역변환해 intake 하지 않는다.
- DB 장애 시 **fail closed** — 불완전한 resource 는 승인에 쓸 수 없다.
- 읽을 수 없는 값을 `confirmed` 로 승격하지 않는다. 특히 `COUNT 0` 은 부재의 증거가 아니다
  (내용 있는 Group 이 0 을 답한 실측 사례가 있다 — 우산 `research.md`).

## 3. 안정 요구사항

`SHALL` 은 필수다. 아래 4건은 `../SPEC-LDPLUGIN-001/spec.md` §3 에서 그대로 승계했다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDPLUGIN-004 | **When** context를 요청하면 서비스는 **SHALL** audio·show·group membership·preset 내용·compiler·capability·정책·identity·만료를 묶은 server-owned ContextSnapshot을 반환한다. | LD-CTX-001, LD-HASH-001 |
| REQ-LDPLUGIN-007 | **When** 교환 객체를 수신하면 서비스는 **SHALL** 다섯 message_type, exact version, closed schema, 유한 수·UTC 시각·상한·ID/ref를 검사하고 unknown field/version을 거부한다. | 계약 §2, §5; LD-REF-001 |
| REQ-LDPLUGIN-015 | **When** 제출·갱신하면 저장소는 **SHALL** immutable plan/revision, base_revision=expected_revision CAS, server digest·state 연결을 SQLite transaction으로 기록하고 timeline JSON을 원본으로 사용하지 않는다. | 계약 §9–10 |
| REQ-LDPLUGIN-027 | The knowledge service **SHALL** design §3의 검토된 rule/case seed를 provenance·조건·예외·저작권 범위와 bounded inline typed details로 제공하고 page/cursor를 current context에 결합한다. 사례·retrieval memory를 강제 법칙이나 weight training으로 표시하지 않는다. | 계약 §3, §6.4 |

## 4. 비목표

### 4.1 Out of Scope — 판단·검증·실행

- **시맨틱 컴파일·검증 판정은 포함하지 않는다.** 축별 timing lowering, FX start/stop·
  cycle/phase, 충돌 검출, MIB·re-entry 증명, capability 광고는 `SPEC-LDCOMPILE-001` 이다.
- **인증·사람 승인·콘솔 실행은 포함하지 않는다.** pairing/ACL, human approve, lock 안
  재검사, 중재자, journal/idempotency 는 `SPEC-LDRECV-001` 이다.
- **MCP adapter·플러그인 패키지는 포함하지 않는다** (`SPEC-LDHOST-001`).
- **검토 UI 는 포함하지 않는다** (`SPEC-LDUI-001`).
- 이 층은 OSC 를 만지지 않는다. `server/bridge/osc.py` 가 서버 전체의 유일한 송신 표면이며
  그 유일성은 아키텍처 테스트(AC-MVP-019)가 지킨다.

### 4.2 Out of Scope — 예술 정책·기존 producer

- **두 기존 예술 producer(`server/looks/songcue.py`, `server/web/session.py` 의 `_ARC_*`)의
  cutover 는 포함하지 않는다.** 우산 `spec.md:90` 이 이를 후속으로 명시했고, 이 릴리스에서
  외부 plan 경로에는 그 producer 를 적용하지 않는다.

  담는 SPEC 은 `SPEC-LDCUTOVER-001` 이다 (`../../reports/ldplugin-001/split-proposal.md` §1.1).
  아직 작성되지 않았으며 `SPEC-LDCERT-001` 뒤에 온다 — 옛 producer 를 지우려면 새 Director
  경로가 먼저 돌아야 하고, 그 전에 지우면 앱이 조명 출력을 아무것도 내지 못한다.
  이름을 남기는 이유는 주인 없는 "후속"은 일어나지 않기 때문이다.
- finale 상승·후렴 변주·기본 BPM 같은 고정 예술 정책을 이 층에서 주입하지 않는다.

### 4.3 Out of Scope — 인프라

- 공개 cloud MCP / TLS 인프라, 개발용 `.mcp.json` 변경, legacy archive 재패키징은 포함하지
  않는다.
- 별도 DB 서버·ORM 도입은 포함하지 않는다. 표준 `sqlite3` 와 명시적 SQL 을 쓴다.

## 5. 검증 수단의 한계 (착수 전 고지)

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한 판정
근거다. 이 SPEC 의 모든 인수기준은 로컬 pytest 로 판정 가능하도록 작성했고, 원격 체크
초록에 의존하는 기준은 두지 않았다.

기준선 (2026-09-14, HEAD `98a822e` 실측): `12794 passed, 31 skipped` — 166.21s.

이 층은 콘솔 게이트가 **없다.** 실기 콘솔 없이 전부 닫을 수 있다 — 형제 중
`LDCOMPILE`(013) · `LDRECV`(021·024) · `LDCERT`(030) 가 콘솔 게이트를 가진다.
