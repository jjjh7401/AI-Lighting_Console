---
id: SPEC-LDRECV-001
title: "Director 인증 receiver·사람 승인·실행·중재자"
version: "0.1.0"
status: in-progress
created: 2026-09-16
updated: 2026-09-17
author: jaihyun
priority: P1
phase: "Lighting Director v1.0 target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, auth, human-approval, execution, programmer-arbiter, idempotency, recovery"
tier: L
depends_on: [SPEC-LDSTORE-001, SPEC-LDCOMPILE-001]
---

# SPEC-LDRECV-001

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-16 | 최초 작성. `SPEC-LDPLUGIN-001` 을 쪼갠 여섯 자식 중 세 번째, Tier L, `depends_on: [SPEC-LDSTORE-001, SPEC-LDCOMPILE-001]`(둘 다 completed 확인). |

## 1. 목적과 경계

외부 `lighting-director` 플러그인과 사람이 같은 계획을 두고 **누가 무엇을 확인했고,
누가 승인했고, 무엇이 실제로 콘솔에 적용됐는지**를 책임지는 층이다. 판단(계획 저작)도
검증(계약 준수 판정)도 하지 않는다 — 인증·ACL, human-only 승인/거절, apply 직전 재검사와
SafetyGate 연결, 공유 programmer 쓰기의 직렬화, durable 실행 journal·idempotency, 실패/
불확실 전송 구분, 인증 철회와 recovery 흐름까지다.

이 SPEC 은 `SPEC-LDPLUGIN-001` 을 쪼갠 여섯 자식 중 세 번째다. 형제 `SPEC-LDSTORE-001`
(저장·context·지식)과 `SPEC-LDCOMPILE-001`(검증·컴파일)은 **이미 완료되어 origin/main 에
있다** — 이 문서를 쓴 시점의 로컬 checkout 은 origin/main 보다 6 커밋 뒤져 있었고, 두
SPEC 의 로컬 `spec.md` 가 아직 `status: in-progress` 로 보였다. 실제 상태는 `git show
origin/main:.moai/specs/SPEC-LDCOMPILE-001/spec.md` / `SPEC-LDSTORE-001/spec.md` 로 직접
확인했다 — 둘 다 `status: completed`, 3-phase close 커밋이 origin/main 에 있다
(`dd3c1121`, `f12d590e` 계열). 이 SPEC 의 `depends_on` 사전 검사는 이 사실에 근거한다.

이 층은 사람이 실제로 콘솔에 손을 대는 대신 **정확히 하나의 승인된 artifact**만 적용되게
하는 것이 존재 이유다 — 계획이 아무리 정확해도 승인 경로가 약하면 전체 계약이 무너진다.

| 규범 | 위치 |
|---|---|
| wire shape·tool·HTTP·state·hash·의미 규칙의 단일 원본 | `../SPEC-LDPLUGIN-001/contract.md` §4(APP human routes)·§5(인증)·§9(hash)·§10(state machine), `../SPEC-LDPLUGIN-001/schemas/exchange.schema.json` |
| 컴포넌트·절차·지식·저장·UI 결정 | `../SPEC-LDPLUGIN-001/design.md` §1(컴포넌트·소유권)·§5(불변식) |
| 현재 코드 근거·한계 | `../SPEC-LDPLUGIN-001/research.md` |
| 저장된 immutable plan/revision·CAS·digest | `../SPEC-LDSTORE-001/spec.md`·`store.py`·`service.py`(`PlanValidator` seam) |
| `ValidationReport`·`compiled.manifest`·frozen artifact bytes | `../SPEC-LDCOMPILE-001/spec.md`·`server/director/emit.py` |
| 분할 근거·형제 목록 | `../../reports/ldplugin-001/split-proposal.md` |
| 이 SPEC 고유 seam 결정 3건(SafetyGate 이음새·`tools.py` 접점·destination occupancy) | [design.md](design.md) |

### 1.1 우산·형제 SPEC 과의 관계 — 자체 `design.md`/`research.md` 를 전면 복제하지 않는다

`SPEC-LDPLUGIN-001` 은 `superseded` 가 아니라 **우산으로 유지**된다. `contract.md` 가
wire shape·state·hash·의미 규칙의 단일 원본이고, `design.md`·`research.md` 가 컴포넌트·
현재 코드 근거의 단일 원본이다. 이 자식은 그것들을 재정의하지 않고 참조한다.

**선행 형제 `SPEC-LDSTORE-001`(Tier M)·`SPEC-LDCOMPILE-001`(Tier L)은 자체
`design.md`/`research.md` 를 만들지 않고 우산 것을 그대로 참조 원본으로 썼다**
(`.moai/specs/SPEC-LDCOMPILE-001/` 실측 — `design.md`/`research.md` 부재). 이 SPEC 도
원칙적으로 그 관례를 따른다 — `research.md`(코드 근거 탐색)는 만들지 않는다. **다만
plan-audit(2026-09-16, 점수 ≈0.75, FAIL)이 D3 로 지적한 대로, 이 SPEC 고유의 안전
관련 seam 결정 2건(§2.0-가 SafetyGate 이음새, §2.0-나 `tools.py` 접점)과 D5 로 지적한
destination occupancy 결정 1건이 `plan.md` 본문 안에만 있고 독립적으로 검토 가능한
`design.md` 가 없었다.** 이 세 결정은 기존 안전장치의 동작을 바꾸거나 형제 SPEC 의
저장 스키마 경계와 맞닿아 있어 `plan.md` 서술만으로는 사람이 그 판단만 떼어 검토하기
어렵다는 것이 지적의 핵심이었다. 그래서 이 SPEC 은 **최소 분량의 `design.md` 를
새로 만든다** — 우산 `design.md` 를 대체·복제하는 전면 재설계가 아니라, 이 세 seam
결정만 다루는 부속 문서다. **이것은 SPEC 문서 표준 Tier L 산출물 집합(§ SPEC Complexity
Tier)의 통상 `design.md`(컴포넌트 전체 설계)보다 좁은 범위이며, 근거는 두 직계 선행
자식의 확립된 관례를 깨면 세 자식의 문서 구조가 갈라진다는 것이다.** plan-audit
단계에서 재검토를 요청한다 — 사람 검토자가 다른 판단을 하면 이 결정을 뒤집을 수 있다.

### 1.2 REQ / AC id 보존

`../SPEC-LDPLUGIN-001/spec.md:45` 가 *"아래 ID는 구현 파일 이동과 무관하게 유지하며 AC
번호와 1:1 대응한다"* 고 규정한다. 두 선행 형제가 이미 이 관례를 따랐으므로, 이 자식도
원래 `REQ-LDPLUGIN-0NN` / `AC-LDPLUGIN-0NN` id 를 그대로 승계한다. 새 번호를 붙이면
`contract.md` 의 조항 참조가 끊긴다.

이 SPEC 이 소유하는 id: `REQ-LDPLUGIN-018`, `019`, `020`, `021`, `022`, `023`, `024`,
`032` (8건). 아래 §3 표가 그 매핑이다.

**이 8건이 이 SPEC 안에서 연속되지 않는(018-024 다음 032) 것은 의도된 정책이며, 결함이
아니다.** 우산 ID 를 그대로 승계하는 정책(위 인용, `../SPEC-LDPLUGIN-001/spec.md:45`)은
"구현 파일 이동과 무관하게 ID 를 유지"하라고 명시적으로 규정하며, 그 유지 대상은
**우산 문서에서 부여된 원래 번호**이지 자식 SPEC 내부에서 다시 매긴 연속 번호가
아니다. 두 완료된 형제가 이미 같은 패턴을 썼다 — `SPEC-LDSTORE-001` 은
`REQ-LDPLUGIN-004/007/015/027`(4건, 우산 순서 그대로 비연속)을,
`SPEC-LDCOMPILE-001` 은 `REQ-LDPLUGIN-008~014`(7건, 자식 안에서는 연속이지만 이는
우산에서 그 구간이 원래 연속이었기 때문이지 자식이 재배번했기 때문이 아니다)을 그대로
승계했다(각 SPEC 의 `spec.md` §3 실측). 이 SPEC 의 8건(018-024, 032)이 우산에서
비연속인 것은 우산 분할 시점에 032 가 다른 구간(운영 중단)에 배정됐기 때문이며, 이
SPEC 이 그 구간을 상속하면서 번호를 재부여하면 오히려 `contract.md` 의 조항 참조와
다른 두 형제 SPEC 의 승계 관례가 동시에 끊긴다. 이후 감사에서 이 비연속성이 다시
질문되지 않도록 이 문단을 남긴다.

## 2. 범위 결정

- **인증은 두 축이다.** MCP credential(`aud=director-mcp`, scope
  `context:read knowledge:read plan:read plan:validate plan:submit execution:read
  feedback:propose`)과 앱 human credential(위 공통 scope +
  `plan:approve plan:reject plan:apply feedback:read feedback:approve feedback:revoke
  execution:reconcile`)은 서로 다른 자격이며, 어느 쪽도 다른 쪽을 차용하지 않는다
  (LD-AUTH-001).
- **승인은 human-only 새 메커니즘이다.** `server/web/approval_bridge.py`(M4 안전 게이트의
  일반 WS 승인 채널, REQ-MVP 계열)를 director 승인으로 **재사용하지 않는다** — 계약이
  명시적으로 금지한다(LD-APPROVAL-001, 계약 §1). 두 메커니즘은 이름이 비슷해 보이지만
  (`server/safety/approval.py` vs 이 SPEC 이 만들 director 승인) 서로 다른 것이며, 이
  혼동을 plan.md §2.0 에서 명시적으로 다룬다.
- **apply 는 큐/객체 programming·storing 뿐이다.** playback 시작·GO·timecode arm/start·
  executor 실행은 포함하지 않는다 (계약 §4). `applied` 는 음악을 재생했다는 뜻이 아니다.
- **destination 은 server-selected 새 Sequence create-only 다.** overwrite·silent
  reselection 은 금지한다 (LD-TARGET-001).
- **기존 3단 안전 게이트(`server/safety/gate.py` `SafetyGate.screen()`)를 우회하지 않는다.**
  단, `screen()` 이 내부적으로 호출하는 **일반 `ApprovalPort`(사람 채팅/WS 승인)는
  director 승인과 별개**다 — REQ-021 이 우회를 금지하는 대상은 "문법·위험·백업·health·
  audit" 이며 이 목록에 "승인" 은 없다. 이 구분이 §2.0(plan.md)의 핵심 설계 발견이다.
- **공유 programmer 쓰기는 전부 하나의 중재자로 직렬화한다.** director·chat·import 등
  모든 mutation 경로가 대상이며, director 경로만 잠그면 의미가 없다 (LD-EXEC-001).
- **durable journal 이 첫 write 보다 먼저다.** OSC 전송과 SQLite commit 을 원자
  transaction 이라고 주장하지 않는다 (계약 §10).
- **불확실성은 후속 쓰기 중단이다.** blind retry·atomic OSC rollback 을 주장하지 않는다
  (LD-EXEC-002).
- **release/운영 중단은 코드 rollback 이 아니다.** 인증 철회·신규 apply 차단·journal 보존·
  명시 recovery 를 제공하되, 앱 코드 deploy rollback 을 console write undo 로 표시하지
  않는다 (계약 §10).

## 3. 안정 요구사항

`SHALL` 은 필수다. 아래 8건은 `../SPEC-LDPLUGIN-001/spec.md` §3 에서 그대로 승계했다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDPLUGIN-018 | **When** pairing/요청이 발생하면 서버는 **SHALL** audience·scope·principal/project/session ACL·Host/Origin·만료/철회·CSRF를 검증하고 secret을 OS credential store 밖의 package/log/model context에 넣지 않는다. 공통 read/validate/submit은 human 자체 credential도 허용하되 MCP credential을 차용하지 않는다. | LD-AUTH-001/002/003 |
| REQ-LDPLUGIN-019 | **While** 외부 evidence/지식을 소비하면 서비스는 **SHALL** 텍스트 지시문·origin·actor_ref를 권한으로 신뢰하지 않고 immutable 서버 근거를 역참조하며 audio의 외부 전송은 앱 명시 동의로 제한한다. | LD-AUTH-003/004 |
| REQ-LDPLUGIN-020 | **When** 승인·거절을 요청하면 서버는 **SHALL** human APP route만 허용하고 exact revision/세 digest/principal/target/policy/만료를 묶으며 일반 chat/WS boolean이나 MCP로 승인을 생성하지 않는다. | LD-APPROVAL-001; 계약 §4 |
| REQ-LDPLUGIN-021 | **When** apply를 요청하면 서버는 **SHALL** lock 안에서 첫 write 직전 current bindings·target/destination occupancy·LiveLock·승인을 다시 검사하고 exact artifact에 승인 bridge를 연결하되 SafetyGate의 문법/위험/백업/health/audit를 우회하지 않는다. destination은 server-selected 새 Sequence create-only이며 overwrite·silent reselection은 금지한다. | LD-SAFE-001, LD-APPROVAL-001 |
| REQ-LDPLUGIN-022 | **While** programming bundle을 적용하면 서버는 **SHALL** director/chat/import 등 모든 shared programmer mutation을 하나의 중재자로 직렬화하고 충돌 요청을 TARGET_BUSY로 거부한다. | LD-EXEC-001 |
| REQ-LDPLUGIN-023 | **When** mutation/idempotent replay가 발생하면 서버는 **SHALL** 첫 write 전에 승인 소비·execution·bundle journal·fingerprint를 durable 저장하고 동일 요청을 최초 응답으로 replay하며 다른 payload를 409로 거부한다. | 계약 §9–10; LD-EXEC-001 |
| REQ-LDPLUGIN-024 | **When** 실패·간섭·crash·불확실 전송이 발생하면 실행기는 **SHALL** 후속 bundle을 중단하고 partial/unknown/failed를 구분하며 blind retry나 atomic OSC rollback을 주장하지 않는다. | LD-EXEC-002; 계약 §10 |
| REQ-LDPLUGIN-032 | **When** release/운영 중단을 결정하면 운영 흐름은 **SHALL** 인증 철회·신규 apply 차단·journal 보존·명시 recovery를 제공하고 앱 코드 rollback을 console write undo로 표시하지 않는다. | 계약 §10; plan §5 |

## 4. 비목표

### Out of Scope — 판단·저장·표현 범위 확장

- 계획의 예술적 의도 작성, 시맨틱 검증·축별 timing lowering·capability 판정, frozen
  artifact bytes 생성은 포함하지 않는다 — 각각 `lighting-director` 플러그인 자체,
  `SPEC-LDCOMPILE-001` 이다. 이 SPEC 은 이미 만들어진 artifact 를 승인받고 보낸다.
- immutable plan/revision 저장·CAS·digest 계산·ContextSnapshot 발급·지식 seed 는
  포함하지 않는다 (`SPEC-LDSTORE-001`). 이 SPEC 은 그 저장소를 읽기만 한다.
- MCP adapter·플러그인 패키지·검토 UI 는 포함하지 않는다 (`SPEC-LDHOST-001` /
  `SPEC-LDUI-001`). 이 SPEC 은 그 둘이 호출할 human/HTTP route 를 제공할 뿐이다.
- 임의 Phaser 제작, 미등록 preset·raw console code, GO/playback/timecode arm/start 는
  포함하지 않는다 (우산 §4).

### Out of Scope — 예술 정책·기존 producer·인프라

- 두 기존 예술 producer(`server/looks/songcue.py`, `server/web/session.py` 의 `_ARC_*`)의
  cutover 는 포함하지 않는다 — 담는 SPEC 은 아직 작성되지 않은 `SPEC-LDCUTOVER-001` 이다
  (`../../reports/ldplugin-001/split-proposal.md` §1.1). 이 릴리스에서 외부 plan 경로에는
  그 producer 를 적용하지 않는다.
- 기존 `server/web/approval_bridge.py`·`server/safety/approval.py` 의 일반 승인 채널
  자체를 재설계하지 않는다 — director 는 그 옆에 새 채널을 만들되, 두 채널의 관계를
  정확히 규정한다 (§2, plan.md §2.0).
- 공개 cloud MCP / TLS 인프라, 개발용 `.mcp.json` 변경, legacy archive 재패키징은
  포함하지 않는다.

## 5. 검증 수단의 한계 (착수 전 고지)

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한
자동 판정 근거다. 기준선은 착수 시점에 재측정한다 — 선행 형제들의 마지막 실측은
`SPEC-LDCOMPILE-001` 종료 시점 기준이며 이 SPEC 착수 시 다시 잰다(로컬 checkout 이
origin/main 보다 뒤져 있었으므로 이 문서에 적힌 숫자를 그대로 베끼지 않는다).

**이 SPEC 은 부분적으로 콘솔 게이트다.** `REQ-LDPLUGIN-021`·`024` 는 "실제로 적용됐는가"·
"전송이 실제로 실패/불확실했는가"를 실기 콘솔(또는 인증 onPC+rig) 관측 없이 확정할 수
없다. 반면 거부·차단·직렬화·journal 의 정직성은 합성 입력만으로 로컬에서 완결된다 —
형제 `SPEC-LDCOMPILE-001` 이 세운 비대칭과 같다: **거부는 로컬로 닫히고, 승격만 콘솔이
필요하다.**

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| 인증·ACL·CSRF·Origin 검증 (018) | 합성 credential + pytest | 아니오 |
| evidence/actor_ref 불신·audio 동의 경계 (019) | 합성 입력 + pytest | 아니오 |
| 승인/거절 route·ApprovalBinding 발급·CAS/만료 (020) | 합성 입력 + pytest | 아니오 |
| apply 직전 재검사 로직(거부 방향) — stale approval·점유·LiveLock (021 의 거부부) | 합성 입력 + pytest | 아니오 |
| **apply 가 실제로 콘솔에 적용됐는가 (021 의 승격부, object-existence 확인)** | 콘솔/onPC 관측 | **예** |
| 중재자 직렬화·TARGET_BUSY (022) | 동시 요청 합성 시나리오 + pytest | 아니오 |
| durable journal·idempotent replay (023) | 합성 crash/재시작 시나리오 + pytest | 아니오 |
| 실패/간섭 시 후속 중단·상태 분류 로직(failed/partial/unknown 갈림) | mock 전송 실패 + pytest | 아니오 |
| **실제 전송 성공/실패/불확실이 실기와 일치하는가 (024 의 관측부)** | 콘솔/onPC 관측 | **예** |
| 인증 철회·apply 차단·journal 보존 (032) | 합성 입력 + pytest | 아니오 |
| **recovery apply 가 실제로 적용됐는가 (032 의 실행부)** | 콘솔/onPC 관측 | **예** |

이 층은 형제 `SPEC-LDCOMPILE-001`(013) · `SPEC-LDCERT-001`(030, 미작성)과 함께 콘솔
게이트를 가진다. `SPEC-LDSTORE-001` 은 콘솔 게이트가 없다.
