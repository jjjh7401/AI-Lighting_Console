# Lighting Director 외부 교환·권한·실행 계약

- 계약 버전: `1.0.0`; 문서 상태: 구현 전 draft; 작성일: 2026-09-13.
- 소유 SPEC: `SPEC-LDPLUGIN-001`. 후속 `SPEC-LDEMBED-001`은 같은 계약을 사용한다.
- 이 문서는 앞으로 구현할 규범이다. 현재 MCP 연결, 컴파일 지원, 실제 콘솔 실행 또는 예술적 품질을 증명하지 않는다.
- 구조의 기계적 원본은 `schemas/exchange.schema.json`, 구조를 넘어서는 의미의 원본은 이 문서의 `LD-*` 규칙이다. 두 문서가 충돌하면 구현을 진행하지 말고 계약 결함으로 해결한다.

## 1. 경계와 배치

외부 `lighting-director` 패키지는 Skills·commands·MCP adapter로 구성한다. 최초 호스트는 Claude Code이며, 로컬 stdio MCP process는 인증된 HTTP `/api/director/v1`로 실행 중인 copilot에 전달하는 thin adapter다. 음악 판단을 위한 별도 서버 LLM 호출이나 OSC 연결을 만들지 않는다. copilot만 기존 ConsoleLink와 OSC를 소유한다. 외부 플러그인과 앱은 동시에 실행한다.

Skills는 `music-evidence-review`, `whole-song-direction`, `cue-plan-authoring`, `director-feedback`이다. Commands `/lighting-director:brief`, `:analyze`, `:plan`, `:revise`, `:submit`, `:learn`, `:status`는 이 절차의 얇은 별칭이다. `:analyze`는 앱이 제공한 evidence를 검토하고 필요한 사람 확인·업로드를 앱에서 요청한다. 실제 듣지 않은 audio를 청취했다고 쓰지 않는다. `:learn`은 feedback proposal만 만든다. 다른 호스트는 같은 절차·domain service를 재사용하되 transport, 인증, capabilities, 초기 연결·도구 목록·권한 거부를 별도로 인증해야 한다. ChatGPT 등에서 자동 호환되거나 이미 배포되었다고 표시하지 않는다.

이 작업의 공존 구조는 역사적 draft `SPEC-COPILOT-MCP-001`의 단독 연결 전제(S2/REQ-MCP-009)를 **이 범위에서 대체하는 새 결정**이다. 기존 파일·lifecycle은 수정하지 않는다. 기존 개발용 `.mcp.json`은 앱 서비스가 아니다. `UnifiedSongLightingPlan`/`SectionDecision`은 내부 재사용 지점이며 외부 무손실 wire format이라는 뜻이 아니다. canonical director plan을 별도 보관하고 기존 timeline은 손실 가능한 projection으로만 사용한다. projection을 다시 읽어 원본을 덮어쓰지 않는다.

기존 `src/Lighting_Designer/99_플러그인/lighting-designer-v0.1.1.plugin`은 `lighting-designer`라는 별도 이름의 archive다. cue-sheet/stage-setup/console-transfer 지식과 CUE/CUE-EX·tracking 절차는 검토 후 provenance와 함께 재사용한다. 후렴 90/95/100, 6–8색은 조건부 예시이지 강제 정책이 아니다. 그 archive가 수동으로 남긴 individual timing, Phaser, POS, Stomp, TC 또는 미래 MCP를 이미 지원하는 것으로 포장하지 않는다. 내장 dataset script·pycache를 복사하지 않는다. 기존 archive는 그대로 두며 설치 전 기존 director 활성 여부를 보여주고 사용자가 하나의 orchestration owner를 선택하도록 한다. 조용히 두 director를 동시에 설치·실행하지 않는다.

## 2. 공통 wire 규칙

| 이름 | 정확한 타입·의미 |
|---|---|
| `Id` | ASCII `[A-Za-z0-9][A-Za-z0-9._-]{0,95}` string. 경로·URL·실행문이 아니다. 서버 발급 ID는 opaque하게 취급한다. |
| `Revision` | 1..2147483647 integer. `base_revision`/`expected_revision`만 0 허용. |
| `Digest` | `sha256:` + 소문자 64 hex. 형식 검사는 진위 검사가 아니다. |
| `Time` | UTC RFC3339 date-time string, 끝은 `Z`. 서버가 calendar/date-time 유효성도 검사한다. |
| `Ms` | 0..86400000 integer. duration은 1 이상. 모든 `at_ms`, delay/fade는 이 단위다. |
| `environment` | `synthetic` 또는 `production`. 서버 deployment와 일치해야 한다. 클라이언트가 synthetic로 바꾸어 production 안전 검사를 우회할 수 없다. |
| `schema_version` | 정확히 `1.0.0`. 모든 교환 객체에 필요하다. |
| `message_type` | `context_snapshot`, `lighting_plan`, `validation_report`, `feedback_record`, `execution_receipt` 중 하나. |

모든 객체는 closed-world이다. schema의 `additionalProperties:false`를 envelope와 tool arguments에도 적용한다. 명시적으로 optional인 필드 이외에는 전부 required다. `null`은 어디에서도 사용하지 않는다. absent·미확정·정지는 각각 별개다. 빈 배열이 허용된 것은 미완성 draft 또는 관측 없음 표현이지 ready 허가가 아니다. JSON은 UTF-8, 중복 key/NaN/Infinity/비유한 수/invalid UTF-8을 거부한다. ID와 array의 고유성·상호참조는 별도 의미 검사다. 최대 structured plan 2 MiB, 2048 cues, 256 controlled groups, cue당 128 actions다. object key 순서는 의미 없고 array 순서는 의미 있다. unknown 필드를 무시하지 않는다. closed-world 호환성 때문에 optional 필드 추가도 구버전 수신기에는 자동 호환이 아니다. 새 wire version을 명시적으로 협상한다.

## 3. MCP signatures와 HTTP mapping

다음 서명은 이름·입력·응답의 규범이다. `?`만 optional이며 omission으로만 표현한다. `P`는 `/api/director/v1/projects/{project_id}`이다. HTTP content type은 `application/json`; 인증은 §5를 따른다. path·query와 body의 project/plan ID 불일치는 `422 IDENTITY_MISMATCH`다.

| MCP tool / 정확한 arguments | HTTP | 성공 body / HTTP status | annotations |
|---|---|---|---|
| `ld_get_context({project_id:Id})` | `GET P/context` | `ContextSnapshot` / 200 | readOnlyHint=true, destructiveHint=false, idempotentHint=true, openWorldHint=false |
| `ld_search_knowledge({project_id:Id,query:string,limit:integer,cursor?:string})` | `GET P/knowledge?query=...&limit=...[&cursor=...]` | `KnowledgePage` / 200 | 위와 동일 |
| `ld_get_plan({project_id:Id,plan_id:Id,revision?:Revision})` | `GET P/plans/{plan_id}[?revision=...]` | `PlanRecord` / 200 | 위와 동일 |
| `ld_validate_plan({project_id:Id,plan:LightingPlan})` | `POST P/validations`, body `{plan:LightingPlan}` | `ValidationReport` / 200 | 위와 동일; 짧은 report 저장은 허용, console 불변 |
| `ld_submit_plan({project_id:Id,plan:LightingPlan,expected_revision:integer,idempotency_key:Id})` | `PUT P/plans/{plan.plan_id}`, body `{plan:LightingPlan,expected_revision:integer,idempotency_key:Id}` | `SubmitResult` / 신규 201, 후속 200 | readOnlyHint=false, destructiveHint=false, idempotentHint=true, openWorldHint=false |
| `ld_get_execution({project_id:Id,execution_id:Id})` | `GET P/executions/{execution_id}` | `ExecutionReceipt` / 200 | readOnlyHint=true, destructiveHint=false, idempotentHint=true, openWorldHint=false |
| `ld_propose_feedback({project_id:Id,feedback:FeedbackProposal,idempotency_key:Id})` | `POST P/feedback-proposals`, body `{feedback:FeedbackProposal,idempotency_key:Id}` | `FeedbackRecord` / 201 | readOnlyHint=false, destructiveHint=false, idempotentHint=true, openWorldHint=false |

MCP success `structuredContent`는 표의 body 객체 그대로이며 `content`는 `[{type:"text",text:<동일 객체의 JSON 직렬화>}]`, `isError:false`다. client는 structuredContent를 우선한다. domain error는 아래 ErrorEnvelope를 structuredContent와 같은 text에 넣고 `isError:true`로 전달한다. JSON-RPC framing/method/arguments 오류는 MCP protocol error다. HTTP 인증 실패를 성공 text로 숨기지 않는다. initialize 시 MCP protocol version은 호스트와 정식 협상하고 tools/list의 inputSchema/outputSchema는 이 계약의 closed shapes로 제공한다. annotation은 권한이 아니다.

### Envelope 정의

아래 정의는 schema의 다섯 top-level exchange와 구분되는 transport envelope다. `LightingPlan` 등은 `$defs`의 같은 이름(snake_case)이다.

- `PlanRecord = {plan:LightingPlan,revision:Revision,state:PlanState,plan_digest:Digest,validation_id?:Id,approval_id?:Id,execution_id?:Id}`. `plan`은 제출 그대로이며 `base_revision`을 서버 revision으로 덮어쓰지 않는다. 생략된 연결 ID는 아직 없는 관계다. 최신 revision 생략 GET은 head를 반환한다. 상태는 해당 revision 상태이며 과거 revision을 명시 조회할 수 있다.
- `SubmitResult = {record:PlanRecord,validation:ValidationReport}`. shape-valid지만 실행 불가능한 draft도 저장하고 `needs_revision`을 반환한다. schema-invalid payload는 저장하지 않는다.
- `FeedbackProposal`은 `FeedbackRecord`에서 **정확히 `revision`, `review` 두 필드를 제거한 shape**다. `message_type:"feedback_record"` 등 나머지는 그대로 required다. 클라이언트는 feedback ID를 생성하며 충돌 시 409다. response의 `revision:1`, `review:{status:"pending"}`은 서버가 부여한다. 저장된 record 전체를 다시 proposal로 보내면 unknown field로 거부한다.
- `KnowledgePage = {context_id:Id,context_digest:Digest,items:KnowledgeRecord[],next_cursor?:string}`. 서버의 현재 project context에 검색 범위를 고정한다. query 1..2048 chars, limit 1..50, cursor 1..2048 chars. next_cursor 없으면 끝. cursor는 project/principal/query/context_id/context_digest/retrieval revision에 묶인 opaque 서버 값이다. 곡·context·승인/철회 지식 revision이 바뀌면 409 `CURSOR_STALE`다.
- `KnowledgeRecord = {record_id:Id,kind:"rule"|"case"|"approved_feedback",scope:"this_song"|"this_show"|"user_style",summary:string,applicability:string[],exceptions:string[],provenance:Provenance,evidence_refs:Id[],resource_id:Id,reviewed_revision:Revision,details:KnowledgeDetails}`. 문자열은 1..4096 chars, applicability/exceptions 최대 32개다. `details`는 kind=rule이면 `{procedure:string[],avoid:string[]}`(각 최대 32개), kind=case이면 `{music_context:string,sequence:{section_role:string,intent:string,actions_summary:string,transition_summary:string}[],outcome:string,limitations:string[]}`(sequence 최대 64개, limitations 최대 32개), kind=approved_feedback이면 `{feedback_id:Id,plan_id:Id,plan_revision:Revision,plan_digest:Digest,changes:FeedbackChange[]}`(최대 128개)다. `FeedbackChange`는 feedback_record.changes의 item과 같은 closed shape다. kind와 details variant는 일치해야 한다. record 직렬화 상한 64 KiB, page 상한 256 KiB이며 상세를 잘라 성공으로 반환하지 않는다. 페이지는 limit보다 적게 반환하고 cursor로 계속할 수 있으며 단일 초과 record는 `413 PAYLOAD_TOO_LARGE`다. 검토된 revision만 반환하며 승인 feedback은 approved/non-revoked/ACL/scope를 조회 시 재검사한다. resource_id는 출처 식별자일 뿐 별도 접근이 필요 없는 inline 상세를 제공한다. 사례는 법칙이 아니며 조건·예외·권리 범위를 보존한다.
- `PlanState = submitted | needs_revision | ready_for_review | approved | applying | applied | partial | unknown | failed | rejected | superseded`.
- `ErrorEnvelope = {error:{code:string,message:string,details:{field:string,rule_id?:string,message:string}[],request_id:Id,supported_schema_versions?:string[]}}`. field는 JSON Pointer 또는 빈 문자열. details 최대 128, message 최대 4096 chars. 버전 거부에만 supported_schema_versions가 required다. stack trace·token·filesystem은 출력하지 않는다.

## 4. APP 전용 human routes

모든 route는 MCP와 다른 `aud=director-app-human` 자격, 실제 로그인 사용자, CSRF 방어, exact-origin을 요구한다. 앱 bridge가 인증된 UI human action을 서버 principal과 연결한다. body의 principal/role/approved boolean, 채팅 message, legacy WS 승인 boolean은 권한으로 인정하지 않는다. MCP에는 아래 route를 전달하거나 approval token을 발급·relay하는 tool이 없다. ID 자체는 bearer 권한이 아니다.

§3의 공통 GET·validation·plan submit은 `director-mcp`와 `director-app-human` 두 audience를 허용하며 각 route의 동일 scope를 검사한다. 앱은 자기 credential로 조회·검증·PUT plan을 수행한다. human 수정도 `expected_revision`/`base_revision`/idempotency와 같은 immutable revision 계약을 사용하며 private DB나 timeline projection을 직접 수정하지 않는다. feedback proposal 또한 두 audience의 `feedback:propose`를 허용한다. 이 절의 approval/apply/reconciliation/revoke는 human-only다.

| APP route | 정확한 body | 응답 |
|---|---|---|
| `POST P/plans/{plan_id}/revisions/{revision}/approvals` | `{validation_id:Id,plan_digest:Digest,context_digest:Digest,compiled_digest:Digest,idempotency_key:Id}` | 201 `{approval:ApprovalBinding,record:PlanRecord}` |
| `POST P/plans/{plan_id}/revisions/{revision}/rejections` | `{reason:string,idempotency_key:Id}` | 200 `PlanRecord` |
| `POST P/plans/{plan_id}/revisions/{revision}/apply` | `{approval_id:Id,expected_revision:Revision,idempotency_key:Id,recovery_of?:Id}` | 202 `ExecutionReceipt`; GET execution으로 추적 |
| `POST P/feedback-proposals/{feedback_id}/approvals` | `{expected_revision:Revision,idempotency_key:Id}` | 200 `FeedbackRecord` |
| `POST P/feedback-proposals/{feedback_id}/revocations` | `{expected_revision:Revision,reason:string,idempotency_key:Id}` | 200 `FeedbackRecord` |
| `POST P/executions/{execution_id}/reconciliations` | `{observations:ReconciliationObservation[],reason:string,idempotency_key:Id}` | 200 `ExecutionReceipt`; 재실행 아님 |

다음 읽기 route도 human audience 전용이며 MCP tools를 추가하지 않는다.

| APP route | query·scope | 200 응답 |
|---|---|---|
| `GET P/plans` | `limit:1..50,cursor?:string,state?:PlanState`; `plan:read` | `{items:PlanSummary[],next_cursor?:string}` |
| `GET P/validations/{validation_id}` | query 없음; `plan:read` | 해당 plan revision의 immutable `ValidationReport` |
| `GET P/feedback-proposals` | `limit:1..50,cursor?:string,status?:"pending"|"approved"|"revoked"`; `feedback:read` | `{items:FeedbackSummary[],next_cursor?:string}` |
| `GET P/feedback-proposals/{feedback_id}` | `revision?:Revision`; `feedback:read` | `FeedbackRecord`, revision 생략은 head |
| `GET P/artifacts/{artifact_resource_id}` | query 없음; `plan:read` | 그 project의 frozen compiled artifact bytes, `application/octet-stream`, attachment; ID→registry lookup만 허용 |

`PlanSummary={plan_id:Id,revision:Revision,state:PlanState,title:string,plan_digest:Digest,context_digest:Digest}`이며 title은 plan과 같은 상한이다. `FeedbackSummary={feedback_id:Id,revision:Revision,plan_id:Id,plan_revision:Revision,status:"pending"|"approved"|"revoked",scope:"this_song"|"this_show"|"user_style"}`다. 목록은 권한 범위의 head만 ID 오름차순으로 반환한다. cursor는 1..2048 chars의 opaque token이고 principal/project/filter/목록 revision에 결합하며 변경 시 409 `CURSOR_STALE`다. 페이지 최대 256 KiB, 초과 시 limit보다 적게 반환하고 next_cursor로 계속한다. plan 원문은 §3 GET으로 별도 읽는다. 앱 inbox·review·feedback는 이 route를 사용하며 DB 직접 읽기나 websocket 타 사용자 fallback을 만들지 않는다.

`reason`은 1..4096 chars. `ApprovalBinding`은 schema의 `approval_binding`이며 모든 필드 required다: `approval_id`, `plan_id`, `plan_revision`, `plan_digest`, `context_digest`, `compiled_digest`, `principal_id`, `console_id`, `session_id`, `safety_policy_revision`, `approved_at`, `expires_at`. 서버가 시간·principal·target을 부여하고 human UI가 본 artifact digest와 일치시킨다. 승인 만료는 생성 시각+10분과 validation/context 만료 중 가장 빠른 값이다. human approval과 예술적 평가 `artistic_approval`은 서로 다르다.

`ReconciliationObservation = {bundle_id:Id,aspect:"object_existence"|"attribute_readback"|"visual_observation"|"terminal_state_observation"|"artistic_approval",status:"confirmed"|"mismatch"|"unknown"|"not_observed",evidence_refs:Id[],note:string}`; 최대 8192개, evidence_refs 최대 128, note 1..4096 chars. 전역 aspect 둘도 해당 execution의 마지막 bundle ID를 지정한다. evidence는 앱 업로드/관측 서비스가 발급한 immutable record여야 한다. 이 route는 사용자의 주장만으로 transport나 readback을 confirmed로 승격하지 않고 evidence kind·범위·관측 시각을 검증한다. 미지원 readback은 unknown으로 남는다. reconciliation은 승인 갱신이나 쓰기가 아니다.

`apply`의 뜻은 **큐/객체 programming·storing뿐**이다. playback 시작, GO, timecode arm/start, executor 실행은 포함하지 않는다. 별도로 사용자가 수행하는 playback은 이 계약의 외부다. `applied`는 음악을 재생했다는 뜻이 아니다. preview·validation·approval은 console 쓰기를 발생시키지 않는다.

## 5. 인증·신뢰·오류

- **LD-AUTH-001**: 최초 pairing은 앱에서 사용자가 승인한다. MCP credential은 `aud=director-mcp`, project/user/session 고정, 만료·철회 가능 scope `context:read knowledge:read plan:read plan:validate plan:submit execution:read feedback:propose`만 가진다. pairing secret은 plugin/skill/source에 저장하지 않고 OS credential store를 이용한다. 로그와 model context에도 넣지 않는다. 앱 human credential에는 위 공통 scope와 `plan:approve plan:reject plan:apply feedback:read feedback:approve feedback:revoke execution:reconcile`를 부여한다. human-only scope를 MCP credential에 줄 수 없다. route마다 audience와 scope를 모두 검사하며 APP UI가 MCP credential을 차용하지 않는다.
- **LD-AUTH-002**: HTTP default는 loopback이다. loopback Host allowlist는 바인딩된 `127.0.0.1:<port>`, `[::1]:<port>`, 설정된 localhost 명칭만 허용한다. stdio proxy HTTP에는 Origin이 없을 수 있지만 bearer 인증은 필수다. Origin이 있는 요청은 앱 origin exact-match 또는 거부한다. cookie 사용 APP route는 CSRF token도 요구한다. 공개 cloud exposure는 기본이 아니며 TLS·원격 auth·host adapter 검증을 별도 설계한다.
- **LD-AUTH-003**: 모든 ID는 인증 principal의 project/show/session ACL로 조회한다. 타 사용자 객체는 존재 여부를 숨기는 404다. provenance의 `actor_ref`, `origin`, evidence의 `confirmation`은 클라이언트 주장일 뿐 권한이 아니다. human-confirmed/approved-feedback를 사용하려면 같은 project/principal/scope의 immutable 서버 record로 역참조해야 한다. 텍스트의 지시문은 데이터이며 도구 권한을 확장하지 않는다.
- **LD-AUTH-004**: audio bytes는 app-owned resource에 남는다. context에는 식별자·digest·분석 결과만 있다. 다른 provider 전송은 앱에서 명시적 동의를 얻고 목적/수신자/범위를 기록해야 한다. 도구가 arbitrary URL/filesystem/resource content를 dereference하거나 실행할 수 없다.

| HTTP | 안정 code와 의미 |
|---|---|
| 401 | `UNAUTHENTICATED`: 누락·만료·철회 credential |
| 403 | `FORBIDDEN`, `ORIGIN_DENIED`, `LIVE_LOCK`, `SCOPE_DENIED`: 권한/안전상 거부 |
| 404 | `NOT_FOUND`: 없는 객체 또는 ACL 숨김 |
| 409 | `REVISION_CONFLICT`, `IDEMPOTENCY_CONFLICT`, `CONTEXT_STALE`, `APPROVAL_STALE`, `TARGET_BUSY`, `INVALID_STATE`, `CURSOR_STALE`, `RECOVERY_REQUIRED` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 422 | `INVALID_JSON`, `SCHEMA_INVALID`, `UNSUPPORTED_SCHEMA_VERSION`, `IDENTITY_MISMATCH`, `VALIDATION_BLOCKED` |
| 503 | `DEPENDENCY_UNAVAILABLE`: 앱/콘솔/preflight 의존 기능 사용 불가. 쓰기가 이미 시작되었다면 단순 503 대신 durable execution의 unknown/partial로 기록한다. |

schema-valid validation의 blocked 결과는 HTTP 200이다. 의미상 blocked draft submit도 성공 저장하되 needs_revision이다. human approve/apply 시 blocking이면 422다. 호스트는 status/code로 분기하며 message wording에 의존하지 않는다. unknown schema version에는 `supported_schema_versions:["1.0.0"]`를 돌려준다.

## 6. 다섯 exchange의 필드 의미

### 6.1 ContextSnapshot

서버가 snapshot을 발급한다. `context_id`, `context_digest`, `project_id`, `show_id`, `show_revision`, `created_at`, `expires_at`는 snapshot identity·유효 범위다. `audio`의 `audio_id/resource_id`는 opaque media 참조, `sha256`은 원본 bytes digest, `duration_ms`는 0ms origin부터의 전체 길이, `source_kind`는 실제 업로드/합성 구분이다. `music_revision`, `rig_revision`, `capability_revision`, `safety_policy_revision`은 별도 monotonic revision이다.

`GET context`는 source revision과 live binding이 그대로이고 미만료이면 같은 current snapshot을 반환한다. 매 GET마다 created_at만 바꾸어 pending plan을 stale로 만들지 않는다. 실제 재관측은 frozen snapshot의 show/group/preset/destination identity와 비교하며 관측 시각 자체를 source 변경으로 보지 않는다. source 변경·expiry 후 발급한 새 context는 새 ID/digest를 갖는다.

`compiler={compiler_id,version,build_digest}`는 실제 emitter build이다. `target={console_id,session_id,identity_status,identity_evidence_refs,mode,destination}`는 현재 show/session과 연결된다. identity_status는 observed/attested/unreadable/synthetic이며 mode는 onpc/console/synthetic이다. `destination={datapool_id:Id,sequence_number:integer,occupancy:"empty",occupancy_revision:Revision,evidence_refs:Id[]}`는 앱에서 사용자가 선택·검토한 server-owned 목적지다. sequence_number는 1..2147483647이며 실제 console 범위는 capability가 추가 검증한다. 첫 버전은 **새 Sequence create-only**이고 기존 객체 overwrite/merge는 지원하지 않는다. 해당 datapool/slot의 빈 상태와 revision을 apply 직전 재조회하고 lock으로 예약한다. 점유되었으면 차단하며 다른 빈 슬롯을 조용히 고르지 않는다. 재연결/show load/inventory/preset/목적지 변경은 승인을 무효화한다.

`sources[]`는 `source_id,kind,resource_id,label`의 출처 catalog다. `evidence[]`는 `evidence_id,kind,resource_id,confirmation,start_ms,end_ms,summary,provenance`다. evidence 구간은 `[start_ms,end_ms]` 설명 범위로 0..duration을 벗어나지 않는다. non-temporal rig evidence는 전곡 구간을 사용한다. `music_sections[]`는 `section_id,start_ms,end_ms,role,confidence,energy,repeat_of,evidence_refs`; role과 energy는 음악 판단이고 조명 강도가 아니다. role unknown/confidence 0이 허용되며 unknown을 chorus로 채우지 않는다. repeat_of는 0 또는 1개 이전 section ID다.

`beat_map={status,segments[]}`; segment는 `start_ms,end_ms,start_beat,bpm,evidence_ref`다. bpm은 20..400, start_beat는 0..1000000 finite number다. 수동 확인 지도도 유효하다. absent/unconfirmed에서는 beat 기반 FX를 실행하지 않는다. `synthetic`은 합성 harness에서만 허용한다.

`groups[]`는 `group_id,membership_revision,fixture_ids,safe_state`. fixture 집합과 membership revision 모두 context digest에 묶인다. `presets[]`는 `preset_id,content_revision,content_digest,content_status,kind,label,group_ids,affects_axes,settle_ms,evidence_refs`; slot만 같다고 같은 preset으로 보지 않는다. content_digest는 서버가 보관한 실제 frozen preset export bytes를 해시한다. 읽을 수 없는 content에는 immutable operator attestation bytes와 범위를 저장하고 digest를 묶되 status=attested로 표시한다. attestation은 측정 검증이 아니다. unreadable이고 attestation도 없으면 ready를 막는다. `settle_ms`는 마지막 movement fade 완료 후 reveal 전 필요 정착시간이다. color는 color 축, position은 pan+tilt, beam은 beam 축으로 제한하고 FX의 affects_axes는 실제 preset이 바꾸는 축 전부다.

`capabilities[]`는 group별 `operations,timing_axes,fx_cycle_beats,dark_move,random_access`를 제공한다. 모든 advertised 기능은 **현재 compiler+rig+target 조합의 실제 출력**이 보존하는 것만 true/목록에 넣는다. `safety={max_intensity_pct,forbidden_preset_refs,live_lock,require_dark_move}`는 표시용 snapshot이며 서버 정책이 우선이다. 클라이언트 수정으로 안전을 완화할 수 없다. `limits`는 고정 전송 상한이다.

### 6.2 LightingPlan

`plan_id`, `base_revision`, `project_id`, `bindings`는 제출 identity다. bindings의 `context_id,context_digest,audio_sha256,music_revision,rig_revision,capability_revision,safety_policy_revision` 모두 current snapshot과 일치해야 한다. show/preset/compiler 내용은 context digest를 통해 묶인다. plan에는 approval, token, ready, compiled commands, execution authority 필드가 **없다**.

`title,concept,global_motif,ending_intent`는 사람이 검토할 전체 의도다. `provenance={origin,actor_ref,source_refs,evidence_refs,rationale}`를 plan/motif/section/cue/action 각각에 둔다. origin은 authored/derived/observed/human_confirmed/synthetic이며 authority가 아니다. `evidence_refs`는 근거 목록, `controlled_group_ids`는 소유할 모든 group이다. `motifs[]`는 `motif_id,description,provenance`; `sections[]`는 context의 section을 가리키는 `section_id,lighting_intent,motif_ref,provenance`다. musical role은 context에서 참조하고 lighting_intent와 혼합하지 않는다.

`playback={mode:"manual_go"|"trig_time",origin:"audio_start",start_policy:"operator_go"}`는 필수다. manual_go에서 at_ms는 리허설용 음악 위치이며 모든 저장 큐는 수동 GO다. trig_time은 첫 cue의 operator GO를 음원 t=0에 맞추고 이후 cue를 상대 시간으로 저장한다. 오디오 플레이어 시작을 동기화하거나 보장하는 기능은 없다. timecode event/offset/arm은 이 wire version에서 지원하지 않으며 mode를 임의 변환하지 않는다.

`cues[]`는 `cue_id,section_id,at_ms,label,actions,provenance`이며 `at_ms` 오름차순, 중복 time 금지다. 하나의 musical section에 여러 cue가 들어간다. `terminal_state[]`는 group별 `{group_id,state}`. state는 `{intensity_pct,color_ref,position_ref,beam_ref,active_fx,ownership}`이며 모든 controlled group에 정확히 하나 필요하다. 첫 release 이후 다시 사용하려면 완전한 baseline을 선언해야 한다. terminal_state는 실행문이 아니라 계획을 simulation한 마지막 값에 대한 assertion이다.

### 6.3 ValidationReport

`validation_id,project_id,plan_id,plan_digest,context_digest,created_at,expires_at,outcome,diagnostics,compiled`로 구성한다. outcome은 blocked/ready_for_review. validation 만료는 생성 후 10분과 context 만료 중 빠른 값이다. diagnostics는 `diagnostic_id,rule_id,pointer,status,blocking,before,after,reason,evidence_refs`다. pointer는 **submitted plan root** 기준 JSON Pointer이며 `""`는 전체 plan이다. status는 accepted/derived/unsupported/unresolved/conflict/safety_blocked. 각 요청 action에는 적어도 하나의 diagnostic이 있어야 하고 변경/누락/지원 불가 필드는 leaf pointer를 추가한다. derived는 계산·준비가 필요하다는 뜻이며 입력의 예술적 값을 바꾸는 허가가 아니다.

`before/after={present:boolean,value?:string|number|boolean|Id[]}`이다. present=true면 value가 반드시 있고 false면 없어야 한다. object 전체는 value로 넣지 않고 해당 leaf에 진단한다. action 전체 단순 수용은 before/after 둘 다 present=false로 하고 변경 없음임을 reason에 밝힌다. 숫자는 finite -1e9..1e9이다. `compiled`는 `{available:false}` 또는 `{available:true,compiled_digest,manifest}`. manifest는 `{compiler_id,compiler_version,compiler_build_digest,plan_digest,context_digest,target:{console_id,session_id,destination},playback,bundles}`이며 destination/playback은 context/plan과 같다. bundle은 `{bundle_id,cue_id,action_ids,at_ms,cue_number,trigger:{type:"manual_go"|"time",relative_ms},artifact_resource_id,artifact_sha256}`다. 최종 bundle 순서에 cue_number 1..N을 배정하고 번호·trigger mapping을 UI에 보인다. manual_go의 relative_ms는 0이다. trig_time은 첫 bundle만 manual_go/0이고 이후 relative_ms=현재 at_ms−직전 최종 bundle at_ms다. 준비 cue도 최종 순서와 delta 계산에 포함하며 의미가 바뀌거나 지원하지 않는 변환은 차단한다. frozen artifact는 앱에 보관하며 MCP에 raw console commands로 반환하지 않는다.

### 6.4 FeedbackRecord

`feedback_id,revision,project_id,show_id,plan_id,plan_revision,plan_digest,scope,summary,changes,evidence_refs,provenance,review`다. scope는 this_song/this_show/user_style. changes는 `{pointer,before,after,rationale}`이며 pointer는 해당 immutable plan root다. 변경 요청이지 즉시 plan mutation은 아니다. before는 실제 원본 leaf와 맞아야 한다. this_song은 plan의 audio_sha256, this_show는 show_id, user_style은 인증 user로 서버가 scope binding을 보관한다. 동일 plan에 새 revision이 생겨도 기존 feedback의 참조는 바뀌지 않는다.

review는 pending 단독, approved+review_id/principal_id/reviewed_at, revoked+같은 필드+revocation_reason 중 하나다. pending→approved→revoked만 허용하고 revision을 1씩 증가시킨다. revoke 후 새 제안은 새 feedback ID다. approved/revoked record는 서버 response로만 만든다. retrieval은 approved AND non-revoked AND ACL AND scope relevance를 모두 만족해야 한다. pending은 학습·검색 근거에 넣지 않는다. 이는 retrieval memory이며 weight training을 했다는 뜻이 아니다.

### 6.5 ExecutionReceipt

`execution_id,project_id,plan_id,plan_revision,plan_digest,context_digest,compiled_digest,approval,created_at,updated_at,state,recovery_required,bundles,artistic_approval,terminal_state_observation,recovery_of`다. recovery_of는 0 또는 1개 원래 execution ID다. state는 applying/applied/partial/unknown/failed. bundle은 `bundle_id,cue_id,state,transport,object_existence,attribute_readback,visual_observation,error_codes`다. state와 transport는 not_sent/sent/acknowledged/failed/unknown 중 하나. object/readback/visual과 전역 artistic/terminal observation은 `{status,evidence_refs,note}`이고 status는 confirmed/mismatch/unknown/not_observed다.

transport sent는 OS socket 전송 성공까지만, acknowledged는 실제 지원되는 acknowledgment를 관측했을 때만 쓴다. UDP send 성공을 acknowledged로 바꾸지 않는다. **applied는 모든 programming bundle에 대응하는 생성 cue 객체의 존재가 같은 execution/context 근거로 confirmed일 때만 허용**한다. sent-only·객체 존재 미관측은 unknown+recovery_required다. 객체 존재는 attribute 값 일치가 아니고 attribute 일치는 visual/artistic 승인도 아니다. 따라서 applied에서도 value/visual/artistic은 unknown/not_observed일 수 있다. terminal_state_observation은 실제 playback 종료 관측 없이는 not_observed/unknown이다. playback을 안 한 apply 시각에 confirmed로 채우지 않는다.

## 7. Typed action 의미와 timing

모든 action의 공통 required 필드는 `op,action_id,group_id,provenance`다. action ID는 plan 전체에서 유일하다. known group/preset ID만 허용하고 MA/Lua/OSC command string, 임의 query, 임의 channel address를 허용하지 않는다.

| op | 추가 필드 | 정확한 상태 의미 |
|---|---|---|
| `intensity_set` | `value_pct:number 0..100`, `timing:{intensity:Timing}` | group의 base intensity를 선형 fade. 0은 명시 off. 실제 preset FX 영향과 충돌하면 차단. |
| `color_set` | `preset_ref:Id`, `timing:{color:Timing}` | kind=color, 해당 group 호환 preset으로 변경. palette slot 숫자로 대체하지 않는다. |
| `position_set` | `preset_ref:Id`, `move_mode:live|dark_move`, `timing:{pan:Timing,tilt:Timing}` | one-shot 위치 이동. preset의 pan/tilt 목표를 별도 delay/fade로 수행. 지속 운동은 이 op가 아니다. |
| `beam_set` | `preset_ref:Id`, `timing:{beam:Timing}` | kind=beam의 알려진 구성 전체. 지원하지 않는 구성 일부만 버리지 않는다. |
| `fx_start` | `instance_id:Id,preset_ref:Id,cycle_beats:number 0.0625..256,phase_beats:number 0..256,timing:{fx:Timing}` | kind=fx preset 인스턴스를 시작. phase_beats는 cycle_beats 미만이며 effect cycle offset이다. 시작 시점의 base state를 보존하고 preset 동작을 혼합한다. |
| `fx_stop` | `instance_id:Id,timing:{fx:Timing}` | 같은 group의 active instance를 explicit stop. fade 완료 후 해당 인스턴스 기여 0, 저장된 base state로 복귀. 임의 console stomp 문자열이 아니다. |
| `group_release` | `timing:{intensity:Timing,color:Timing,pan:Timing,tilt:Timing,beam:Timing}` | 모든 FX가 이미 정지한 group을 context.safe_state로 전환 후 ownership=released. 과거 programmer 값으로 복귀하지 않는다. |

`Timing={delay_ms:Ms,fade_ms:Ms,curve:"linear"}`이다. 모든 axis timing을 명시하며 기본값 상속은 없다. 시작은 `cue.at_ms+delay_ms`, 완료는 거기에 fade_ms를 더한다. fade=0은 순간 변경이다. number는 IEEE754 finite, JSON JCS 범위에서 해석하며 beat→ms 최종 경계는 가장 가까운 integer ms(정확한 .5는 +방향)로 반올림한다. rounding으로 충돌이 생기면 거부한다. emitter 최소 timing 해상도로 값을 정확히 재현할 수 없으면 unsupported다. 자동 quantize/clamp/substitute하지 않는다.

## 8. 안정 semantic rule IDs

아래 rule ID를 validation diagnostics와 구현 acceptance에 그대로 사용한다.

| Rule ID | MUST 규칙 |
|---|---|
| **LD-REF-001** | 모든 ID는 자기 namespace에서 유일하다. group/preset/section/motif/instance/plan/evidence/source 참조는 동일 snapshot 또는 허용된 immutable server knowledge registry로 해소한다. 다른 project, 순환 출처, nonexistent reference는 blocking이다. |
| **LD-CTX-001** | audio identity와 모든 bindings가 server-owned snapshot과 일치하고 미만료여야 한다. preset 내용·group membership·live show·session·compiler build 변경은 stale다. 현재 identity가 unreadable이면 requery/범위가 명확한 operator attestation 없이는 승인을 유지하지 않는다. |
| **LD-TIME-001** | 원점은 업로드 audio의 첫 sample=0ms, 중간 trim/offset 없음. context sections는 전곡 [0,duration)를 겹침·공백 없이 분할한다. plan sections는 각각 한 번 모두 참조한다. cue는 자기 section의 start<=at<end, 첫 cue=0, 모든 delay/fade/settle는 duration 이내다. 같은 ms는 단일 semantic cue로 묶고 action array 순서는 deterministic emit order로만 사용한다. array 뒤 action으로 앞 conflict를 덮어쓰지 않는다. |
| **LD-TIME-002** | `beat(t)=start_beat+(t-start_ms)*bpm/60000`. segment는 [start,end), 인접 beat 값 연속, confirmed 근거 필수다. FX 한 instance의 active 구간이 다른 bpm segment를 가로지르면 explicit stop+새 start로 분할하거나 unsupported. tempo 불명인데 120 BPM을 가정하지 않는다. phase는 실제 start 시점 기준으로 계산한다. |
| **LD-TIME-003** | playback.mode를 explicit하게 compile한다. manual_go는 모든 cue의 수동 진행이고 at_ms는 음악 참조다. trig_time은 operator가 audio t0에 첫 GO, 나머지는 최종 bundle 순서의 절대 시각 차이를 relative_ms로 저장한다. 기존 emitter에 절대 at_ms를 그대로 TrigTime으로 넘기지 않는다. timecode mode·숨은 offset·자동 GO는 거부한다. |
| **LD-TARGET-001** | context의 datapool/빈 Sequence 목적지를 manifest와 approval digest에 묶는다. lock 안에서 첫 write 직전 empty identity/revision을 재확인·예약한다. 점유/읽기 불가/지원 범위 밖 번호는 blocking이며 overwrite나 silent reselection은 없다. 실행된 revision의 수정은 별도 reviewed empty 목적지의 새 context/revision으로 저장한다. |
| **LD-STATE-001** | 누락 action/axis는 hold이다. ready plan 첫 cue는 controlled group 전부의 intensity/color/position/beam baseline을 완전히 지정하고 active FX 없음이 target에서 확인되어야 한다. 이전 show/programmer state를 상속하지 않는다. clean 상태를 확인할 수 없으면 차단하고 human이 별도 recovery를 승인한다. schema-valid 빈 cue/terminal 배열은 draft만 허용한다. |
| **LD-STATE-002** | timeline을 축별 simulation하고 모든 group의 terminal_state와 정확히 일치시킨다. quiet ending/동일 후렴 강도는 유효하다. role=outro라는 이유로 intensity를 올리지 않는다. 마지막 cue 뒤에도 fade가 남으면 duration 내 완료해야 한다. |
| **LD-FX-001** | instance_id는 plan-wide 유일한 한 start에 대응하고 한 stop이 있어야 한다. stop 없는 FX, 시작 전 stop, 중복 start/stop, group mismatch는 blocking이다. active_fx의 terminal 값은 항상 빈 배열. stop fade는 base state로 복귀하므로 영향을 받는 base 축은 FX active 동안 바꾸지 않는다. |
| **LD-CONFLICT-001** | fixture별 attribute를 실제 group membership으로 확장한다. 같은 fixture/axis의 겹치는 fade/delay transition, 한 instant의 중복 쓰기, FX affects_axes와 static/다른 FX의 겹침은 동일 값이라도 conflict다. transition 끝==다음 시작은 허용한다. FX stop fade가 끝난 뒤에만 그 축을 다시 쓸 수 있다. delay 구간은 새 transition 예약 구간이며 다른 변경으로 시작값을 바꾸지 못한다. |
| **LD-CAP-001** | group별 op/preset/timing 축/cycle/dark_move/random_access가 compiler+rig 실제 capability와 맞아야 한다. parser가 받아도 emitter가 보존하지 못하면 unsupported+blocking. 요청 field 제거, fallback preset, percent clamp는 금지. |
| **LD-MIB-001** | dark_move는 movement 시작부터 pan/tilt의 늦은 완료+settle_ms까지 intensity=0 및 intensity FX 없음이 증명되어야 한다. visible reveal 시각을 미뤄 맞추지 않는다. compiler 준비 동작은 negative ms 금지, authored timing 불변, derived 진단과 artifact에 포함한다. 불가능하면 blocking과 명시 pre-roll/new plan 요청; 이 버전에는 음수 clock/pre-roll 필드가 없으므로 원점을 확장한 새 audio/context 또는 사람이 사전 준비한 verified baseline이 필요하다. |
| **LD-REENTRY-001** | 임의 cue index preview/re-entry는 baseline부터 해당 시간까지 simulation하여 full state와 active FX phase를 복원한다. 중간 fade의 현재 값·remaining duration, beat 위치가 재현되지 않으면 random_access=false/unsupported다. compiler는 이전 cue를 수동 실행해야만 맞는 숨은 tracking 상태를 남기지 않는다. 실제 GO/re-entry playback은 본 apply API로 시작하지 않는다. |
| **LD-SAFE-001** | server safety policy와 기존 SafetyGate hard check를 유지한다. max intensity/forbidden preset/LiveLock/MIB/target readiness 위반은 safety_blocked다. artistic advisory는 별도 nonblocking이며 hard limit을 완화할 수 없다. |
| **LD-VAL-001** | source identity→time/reference→tracking/FX→capability/fidelity→safety→approval freshness 순으로 검사한다. 어떤 execution-critical diagnostic이라도 blocking이면 compiled.available=false, outcome=blocked. ready에는 모든 requested action의 fidelity와 전체 semantic 규칙 통과가 필요하다. false ready를 metadata 성공으로 대신하지 않는다. |
| **LD-HASH-001** | §9의 scope로 hash를 검증한다. payload 자체에 claimed digest가 있다고 신뢰하지 않는다. 서버가 plan/compiled digest를 계산하며 approval은 세 digest와 exact revision/target/policy를 묶는다. |
| **LD-APPROVAL-001** | ready_for_review에서 human APP route만 승인한다. mutation/context/compiler/target/policy 변경·만료·head 변경 시 approval 무효. generic chat/WS approve boolean을 director 승인으로 재사용하지 않는다. apply 직전 durable human approval을 exact compiled artifact digest에 묶은 SafetyGate bridge에서 소비한다. |
| **LD-EXEC-001** | 전체 plan을 먼저 검증하고 첫 write 전 SQLite에 execution+approval 소비+idempotency+bundle journal을 transaction으로 저장한다. 모든 director/chat/import shared programmer mutation을 하나의 server lock으로 직렬화한다. transaction 중 competing ClearAll/Group/At/Store 등은 TARGET_BUSY로 거부하고 오래 대기시켜 낡은 승인을 실행하지 않는다. |
| **LD-EXEC-002** | operator intervention, session change, transport uncertainty, 첫 실패에서 후속 bundle을 중단한다. operator가 programmer를 바꾸면 pause 의미의 unknown+recovery_required로 전환한다. OSC에는 atomic rollback/exactly-once 보장이 없다. 재시작 시 applying은 unknown으로 회수하고 blind retry하지 않는다. |
| **LD-FEEDBACK-001** | proposal은 pending만 만든다. approve/revoke는 human route+CAS; retrieval은 approved/non-revoked/ACL/scope 전부 만족. before leaf와 immutable plan digest가 맞지 않으면 제안도 거부한다. 인용문·provenance가 스스로 승인할 수 없다. |
| **LD-SYN-001** | synthetic evidence/status/digest는 fixture-only다. production ready/apply에 synthetic identity/audio/evidence/compiler를 사용할 수 없다. 합성 expected report/receipt를 runtime 검증으로 보고하지 않는다. |

## 9. Hash와 canonical scopes

모든 JSON digest는 `sha256(UTF-8(RFC8785/JCS(value)))`를 `sha256:<hex>`로 표시한다. JCS는 object key를 정렬하고 JSON number를 규정대로 직렬화한다. 예쁜 출력·공백·key 순서는 무관하며 array 순서는 유지한다. 별도 Unicode normalization을 하지 않는다. 중복 key는 canonicalization 전에 거부한다. raw bytes digest에는 JCS를 적용하지 않는다.

1. `context_digest`: ContextSnapshot 전체에서 **최상위 `context_digest` key 하나만 제거한 객체**. compiler/safety/identity/만료·모든 metadata 포함. nested content_digest 등은 제거하지 않는다.
2. plan digest: 제출된 `LightingPlan` 전체. plan에는 digest self-field가 없다. API envelope의 expected_revision/idempotency_key, 서버 PlanRecord metadata는 제외한다. base_revision·provenance·rationale도 포함한다.
3. `compiled_digest`: ValidationReport.compiled.manifest 객체 전체. compiled.available/compiled_digest/validation timestamps·diagnostics는 제외한다. manifest의 각 artifact_sha256은 **서버가 실제 보낼 frozen artifact bytes**를 해시한다. compiler version/build, target, plan/context digest, ordered bundles와 action coverage가 묶인다. artifact content가 바뀌면 재검증·재승인한다.
4. `audio.sha256`/`bindings.audio_sha256`: 실제 업로드 bytes. waveform/분석 JSON 또는 filename의 해시가 아니다.
5. `compiler.build_digest`/manifest.compiler_build_digest: 재현 가능한 emitter build artifact bytes. preset.content_digest는 frozen preset export/명시 attestation bytes. 서버 resource registry가 immutable bytes와 digest를 같이 보관한다.
6. validation/feedback/execution에는 독립 self-digest가 없다. 이들의 plan/context/compiled digest는 위 원본 참조다. feedback revision과 review audit는 서버 append-only record로 보호한다. 자체 hash가 없다는 이유로 외부 입력을 server receipt로 신뢰하지 않는다.
7. idempotency request fingerprint: `JCS({operation,project_id,principal_id,request})`의 SHA256. operation은 `METHOD /api/director/v1/...`의 **실제 percent-decoded ID를 넣은 route**; query가 있는 mutation은 이 버전에 없다. request는 HTTP body에서 idempotency_key만 제거한 객체다. key 자체는 별도 `(project_id,principal_id,operation,idempotency_key)` unique index에 저장한다.

### 합성 예제 digest 재현 규칙

아래 byte 정의와 JCS scope를 사용해 합성 예제 digest를 계산한다. 이 digest는 실제 음원이나 MA 명령을 검증했다는 의미가 아니다.

- audio fixture bytes는 정확한 UTF-8 `Lighting Director synthetic audio fixture v1\n` (마지막 LF 1개). 실제 audio가 아닌 identity fixture다.
- compiler fixture bytes는 정확한 UTF-8 `Lighting Director synthetic compiler fixture v1\n`.
- 각 preset fixture bytes는 UTF-8 `synthetic-preset:<preset_id>\n` (ID를 그대로 치환, LF 1개).
- 각 bundle artifact fixture bytes는 UTF-8 `synthetic-bundle:<bundle_id>\n`. MA 명령이 아닌 contract용 bytes다. 따로 artifact JSON을 만드는 대신 이 규범 문자열로 해시한다.
- 위 raw digests를 context와 manifest compiler_build_digest, plan audio binding에 채운다. context_digest 계산 후 context root, plan bindings, validation root/manifest, execution root/approval에 전파한다.
- 완성된 plan의 digest를 계산해 validation root/manifest, feedback.plan_digest, execution root/approval에 채운다.
- 각 manifest bundle artifact_sha256을 채운 후 manifest compiled_digest를 계산해 validation.compiled, execution root/approval에 채운다.
- 마지막에 모든 reference/hash/cross-field를 검증한다. 계산이 완료되어도 synthetic 표시와 실제 실행을 주장하지 않는 설명은 유지한다.

## 10. Revision·승인·실행 state machine

`ld_submit_plan`은 expected_revision과 plan.base_revision이 같아야 한다. 새 ID는 둘 다 0이며 서버 revision=1. 기존 ID는 현재 head와 같아야 하고 revision=head+1. 요청자 ID가 같은 것만으로 다른 author의 초안을 덮어쓸 수 없으며 ACL도 검사한다. schema-invalid는 revision을 만들지 않는다. 저장 성공 후 validation이 blocked면 needs_revision, 통과하면 ready_for_review. submitted는 저장 후 검증이 끝나기 전 durable 내부 상태이며 처리 장애 시 재개한다.

허용 전이는 submitted→needs_revision/ready_for_review, ready_for_review→approved/rejected, approved→applying, applying→applied/partial/unknown/failed다. needs_revision에서 내용 변경은 새 revision이다. 새 head가 생기면 이전 **미실행** revision은 superseded되고 승인은 폐기한다. applied/partial/unknown/failed/rejected의 역사적 결과는 superseded로 덮어쓰지 않는다. stale 승인 제거 시 아직 실행 전 revision은 needs_revision으로 돌아가 current context로 새 revision 제출을 요구한다. applying 중 해당 plan head 변경은 TARGET_BUSY로 거부한다. rejected/superseded revision은 다시 승인하지 않는다. failed/partial/unknown을 같은 revision로 재apply하지 않는다.

APP apply는 head revision/CAS, approval 미만료·미소비, digests·current context·show identity·target·policy·LiveLock을 **lock 안에서 첫 write 직전** 다시 검사한다. current context를 확인할 수 없으면 fail closed한다. target reservation과 shared programmer lock은 director뿐 아니라 chat/import 등 모든 write path에 적용한다. 긴 queue는 두지 않는다. legacy 경로도 이 reservation 검사를 우회하지 못해야 한다.

SQLite(stdlib sqlite3)를 revision/CAS/idempotency/approval/execution journal의 transaction 원본으로 사용한다. 기존 local persistence 패턴과 reviewed memory를 명시 migration하고 UI timeline JSON을 진실의 원본으로 삼지 않는다. 동일 key+동일 request fingerprint는 최초 저장한 status와 body를 그대로 replay한다(202 초기 receipt라면 그대로 replay, 최신 상태는 GET). 동일 key+다른 request는 409. concurrent 동일 key는 하나의 execution만 생성한다. durable key는 project audit retention 동안 보관하고 임의 TTL로 삭제하여 재write 가능하게 만들지 않는다. retention 삭제는 project 폐기 절차로만 수행한다. 인증·ACL은 replay 때도 다시 검사한다.

승인은 첫 execution allocation 시 소비된다. 이후 다른 idempotency key로 같은 approval을 apply하면 INVALID_STATE 또는 RECOVERY_REQUIRED다. write 전 실패도 소비를 몰래 되돌리지 않고 receipt를 남긴다. journal에는 bundle planned→sending(디스크 commit)→sent/acknowledged/failed/unknown과 시간·오류·evidence를 남긴다. OSC 전송과 DB commit을 원자 transaction이라고 주장하지 않는다. socket send 뒤 저장 전 crash는 unknown이다.

`failed`는 어떤 bundle도 적용되었다고 확인되지 않고 미확정 전송도 없는 명확한 실패. `partial`은 일부 전송 성공과 이후 명확한 실패가 있는 상태. `unknown`은 하나라도 적용 여부를 알 수 없거나 operator 간섭이 있는 상태로 partial보다 우선한다. not_sent 후속 bundle을 receipt에 보존한다. partial/unknown은 recovery_required=true. 첫 쓰기 이전 failed는 false일 수 있으나 재apply에는 새 approval/revision이 필요하다.

Recovery는 readback/reconciliation으로 현재 상태를 공개한 뒤 **새 recovery plan revision을 작성→검증→사람 승인→apply(recovery_of)** 하는 별도 흐름이다. create-only이므로 새 empty Sequence destination을 선택한 context가 필요하고 원본의 부분 저장 Sequence를 덮어쓰지 않는다. original execution은 역사로 남긴다. recovery_of는 같은 project/console_id/session_id를 요구하되 위 새 destination은 허용한다. 원본 show/session이 바뀌어 이 조건을 충족할 수 없으면 복구 apply를 차단하고 별도 operator reconciliation으로 정리한다. 새 Sequence 저장 자체는 원본의 부분 객체/FX를 정리한 증거가 아니며, 원본 정리가 관측·승인되어 해결된 경우에만 original recovery_required를 false로 할 수 있다. 당시 partial/unknown 기록은 삭제하지 않는다. 자동 rollback·blind resend·silent ClearAll은 없다. 운영자가 console에서 독립적으로 정리한 경우도 immutable evidence와 attestation 구분을 남긴다. 앱 코드 deploy rollback은 console write undo가 아니다.

## 11. 예제 묶음과 구현 인수 경계

`examples/context.json`, `plan.json`, `validation.json`, `feedback.json`, `execution.json`은 한 synthetic 180초 곡·8 fixture·2 disjoint group을 공유한다. intro→verse-a→chorus-a→verse-b→chorus-b→bridge→outro, 두 후렴은 모두 70%와 같은 motif를 사용한다. color/position/beam preset ref, pan/tilt의 다른 fade·delay, 35초 악센트와 35.3초 복귀, 각 후렴의 FX start와 종료 전 stop, 15%→3%→0% quiet ending, 모든 group의 explicit terminal state를 포함한다. 밝기가 계속 상승해야 한다는 규칙은 없다.

validation.ready_for_review는 **예상 wire 상태를 보여주는 synthetic fixture**다. execution은 programming 전송만 가정하고 모든 관측을 not_observed로 남겼으므로 **unknown+recovery_required**다. 실제 emitter 실행/console storing/ack/readback/화면/예술 승인 결과가 아니다. feedback은 pending 제안이며 계획을 바꾸지 않는다. schema/hash/semantic 검사도 실제 console proof와 구분한다.

JSON Schema는 타입·범위·variant·required·unknown-field만 보장한다. 다음은 의미 검사로 반드시 증명한다: ID uniqueness와 모든 refs, state simulation, source authority, hash 정합성, plan revision CAS, first/terminal state, overlap·FX completion, time/beat/MIB 가능성, 실제 emitter field fidelity, 안전 정책, 승인 freshness, shared writer exclusion, durable idempotency, unknown recovery. format checker를 끈 validator에서는 date-time까지 보장되지 않는다. independent 구현자는 schema pass만으로 ready를 반환하면 안 된다.

첫 release의 완료 범위는 외부 host의 initialize/tools/list/context/submit, 앱 review·human approve·approved apply, feedback approve/revoke/retrieval까지 end-to-end다. synthetic 외부/내부 host parity, negative schema와 stale/forged authority/unknown refs/overflow/capability/FX leak/overlap, CAS 및 idempotency 동시성, 공유 programmer 충돌·restart unknown을 검사한다. 실제 timing/FX stop/storing은 preview 후 human-authorized onPC trace와 실제 visual/readback evidence로 따로 검증한다. 현재 LXSEQ parser 수용을 emitter 지원으로 오인하지 않는다. 예술적 평가는 confirmed music map으로 시작해 held-out song과 blind paired director review·수정시간을 비교하며 임의의 개선율을 보장하지 않는다.
