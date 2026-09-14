# 인수 기준 — SPEC-LDEMBED-001

[요구사항](spec.md) · [계획](plan.md) · [공유 계약](../SPEC-LDPLUGIN-001/contract.md) · [선행 인수](../SPEC-LDPLUGIN-001/acceptance.md)

현재 구현 AC는 **모두 미실행**이다. 선행의 synthetic fixtures와 계약 parity는 실제 embedded provider 연결·예술 품질 증거를 대체하지 않는다. S=static/schema, D=deterministic runtime/domain, H=실제 host/app smoke, C=human-authorized onPC/화면 관측, A=artistic pilot로 구분한다.

## 1. 요구사항→AC

| AC | REQ | 층 | Given / When / Then·관측 증거 |
|---|---|---|---|
| AC-LDEMBED-001 | REQ-LDEMBED-001 | S | Given 선행 release evidence, When embedded 착수/출시 검토, Then 선행 G1–G5의 실제 host/receiver/UI/fidelity/pilot 증거와 별도 kickoff 승인이 연결된다. 미충족이면 no-go. |
| AC-LDEMBED-002 | REQ-LDEMBED-002 | S+D | Given 외부 package와 embedded resource, When 네 procedure version/digest 및 fixed inputs 비교, Then 같은 source·knowledge·service 계약을 사용한다. 호스트별 강제 후렴/ending 정책이 없다. |
| AC-LDEMBED-003 | REQ-LDEMBED-003 | D+H | Given 기존 활성 LLMProvider 설정, When 실제 embedded 설계 run, Then complete/neutral tool loop가 동작하고 새 필수 model/key를 요구하지 않는다. provider/model/version/usage 기록. provider 변경 시 이전 opaque payload가 새 provider에 전달되지 않음. |
| AC-LDEMBED-004 | REQ-LDEMBED-004 | D+H | Given 정상·unknown·malformed·권한 없는 tool calls와 한 turn 복수 calls, When dispatch, Then 정확한 순서/상관 ID 결과가 ToolResultsMessage로 반환된다. raw/approve/apply·cross-project 도구는 오류이며 mutation 0. |
| AC-LDEMBED-005 | REQ-LDEMBED-005 | D+H | Given self-repair를 계속하는 model, When 12 model turn 또는 32 tool call/75% input budget에 도달, Then waiting_user이고 추가 call 0. UI에서 진행 절차·남은 budget·pause 이유를 관측. |
| AC-LDEMBED-006 | REQ-LDEMBED-006 | D+H | Given model in-flight와 submit/propose 응답 유실, When cancel/timeout, Then 이후 dispatch 0·checkpoint 저장·late generation 결과 폐기. mutation 결과는 read/idempotency로 확인하며 새 key blind retry 0. cancel 미지원 provider를 즉시 종료했다고 표시하지 않음. |
| AC-LDEMBED-007 | REQ-LDEMBED-007 | D+H | Given process restart·stale context/head·uncommitted tool intent, When same principal resume, Then committed 결과부터 복구하고 미확정 mutation을 reconcile하며 stale는 새 draft 검토. 타 principal 재개 거부·옛 승인 재사용 0. |
| AC-LDEMBED-008 | REQ-LDEMBED-008 | D+H | Given 외부 host 대화 없이 앱에 저장된 brief/context/plan/approved knowledge, When fresh embedded run·context compaction, Then 동일 명시 의도와 immutable refs가 유지된다. audio bytes/secret이 model context에 없고 무근거 요약은 authority가 아님. |
| AC-LDEMBED-009 | REQ-LDEMBED-009 | H | Given 실제 앱의 곡 설계/수정/learn/status·일반 console chat, When 각 진입점을 사용, Then director 절차와 일반 요청이 올바르게 분리되고 run/draft/review/receipt 화면이 같은 plan ID/revision에 연결된다. 취소·재개·오류 화면을 캡처. |
| AC-LDEMBED-010 | REQ-LDEMBED-010 | D+H+C | Given model의 '승인/적용' 문구·오래된 approval·LiveLock·점유 destination, When submit/apply 시도, Then model 권한은 draft/proposal에 머물고 human APP action만 exact binding으로 실행 가능. 선행 shared lock/journal/unknown recovery 유지. |
| AC-LDEMBED-011 | REQ-LDEMBED-011 | S+D+H | Given 옛 인터뷰와 prepare_songcue 두 진입점, When 같은 quiet ending/동일 후렴 brief로 사용, Then 둘 다 shared Director에 연결되고 old producer 예술 정책·호출·fallback은 없다. 일반 compiler/안전 helper는 동작하며 명시 intensity/FX/timing 변경 0. |
| AC-LDEMBED-012 | REQ-LDEMBED-012 | D+H | Given Claude Code 외부 플러그인과 embedded 동시 사용, When 같은 head에 제출, Then 하나만 CAS 성공·다른 것은 REVISION_CONFLICT, owner 표시와 외부 initialize/tools/list/context/submit/feedback 조회가 유지된다. |
| AC-LDEMBED-013 | REQ-LDEMBED-013 | D | Given 동일 fixed context/plan·고정 identity, When 외부 adapter와 embedded dispatcher를 통해 validate/submit, Then §2의 의미 비교가 전 항목 일치하고 원본 digest를 검증한다. 이것은 model을 호출하지 않는 계약 검사다. |
| AC-LDEMBED-014 | REQ-LDEMBED-014 | H+A | Given 같은 confirmed map/brief/skill·knowledge revision·rig, When 외부·내장 model 생성 pilot, Then stochastic 문장/ID 차이를 허용하되 의도 보존·fidelity·paired review·수정시간을 비교한다. §3 품질 gate 결과와 평가자 불일치를 공개. |
| AC-LDEMBED-015 | REQ-LDEMBED-015 | D+H | Given pending/approved/revoked feedback와 이전 요약 checkpoint, When learn→human approve/revoke→resume/search, Then pending은 미검색·revoked는 요약에서도 무효·scope/ACL 범위만 retrieval. model 자체 승인 0. |
| AC-LDEMBED-016 | REQ-LDEMBED-016 | D+H | Given running 내장 run과 partial/unknown execution, When rollout 중단/코드 rollback, Then 신규 run/apply 차단·run checkpoint/journal 보존·외부 plugin 사용 가능. 콘솔 undo/자동 recovery write/old policy fallback 0. |

## 2. fixed-plan parity와 정규화

- **계약 parity 입력**은 선행 [다섯 fixtures](../SPEC-LDPLUGIN-001/examples/plan.json)와 negative variants를 그대로 사용한다. model completion은 호출하지 않는다. 같은 principal/context/plan/revision·compiler build·destination을 고정하고 두 dispatcher 경계만 바꾼다.
- strict equality 대상: 입력 LightingPlan의 모든 의미 필드·provenance, capability/diagnostic rule_id·pointer·before/after·blocking, outcome, compiled action coverage·cue order/timing·destination mapping, revision/state/error code·권한 거부, feedback scope/review 동작.
- 서버 생성 request/validation/execution ID·시각은 **비교 보고서에서만** 역할별 stable ID로 정규화한다. 실제 artifact 생성에 영향을 주는 ID는 동일 고정 fixture 값을 주입한다. 실제 hash는 원본 JCS/bytes로 먼저 검증하고 정규화된 JSON을 hash 원본으로 사용하지 않는다.
- provider_payload·token usage·호스트 표시 prose는 wire contract 밖이므로 제외한다. title/concept/rationale/provenance나 actions를 무분별하게 제거하여 parity를 만들지 않는다.
- **stochastic generation**은 별도 H/A 실험이다. 같은 prompt라도 byte equality를 기대하지 않으며 고정 계획 전송의 parity 실패를 모델 확률성으로 변명하지 않는다.

## 3. Go / no-go

| Gate | Go 기준 | No-go |
|---|---|---|
| E-G0 | 선행 G1–G5, schema/skill/compiler pin, 별도 kickoff 승인 | 선행 누락을 embedded 프로젝트로 전가 |
| E-G1 deterministic | AC-002/004–008/010–013/015–016의 D 시나리오 통과, 무권한 write·tool 중복 mutation·stale 승인 0, fixed-plan 의미 diff 0 | allowlist 우회·checkpoint 유실·정규화로 의미차 삭제 |
| E-G2 실제 UI/provider | 현재 지원 활성 provider 중 최소 1개 실제 설정으로 start→tool loop→draft→review→human apply→feedback 왕복, cancel/late reply/resume/reconnect 화면 증거. 외부 Claude Code smoke도 유지 | provider mock만 사용, 새 모델 강제, 외부 host 파손 |
| E-G3 cutover | 두 실제 진입점에서 동일 shared orchestration을 관측, duplicate producer/policy fallback 0. 동일 명시 quiet ending·FX stop·timing 보존 | 세 번째 엔진 추가·옛 정책이 explicit plan 재해석 |
| E-G4 품질 | 선행 held-out 6곡 이상을 포함한 별도 blind paired 외부/내장 비교, confirmed map·동일 rig/brief. 명시 의도 위반 0, 선행 인수의 5개 1–5 평가축 평균이 외부보다 낮지 않음. 수정시간 분포 기록·운영 감독 승인 | stochastic byte diff만으로 실패/성공 판정, 예술 품질 미측정 또는 평균 저하 |
| E-G5 운영 | E-G0–4 모두 통과·cancel/resume·external 선택·unknown recovery runbook 존재 | 코드 rollback이 console undo라고 설명 |

새 provider adapter별 지원 범위는 별도 smoke와 권한 거부 검증이 끝난 조합만 인증한다. 내장 host 성공이 ChatGPT transport 인증을 대신하지 않는다. 위 수치는 미래 인수 기준이며 현재 측정 결과가 아니다.
