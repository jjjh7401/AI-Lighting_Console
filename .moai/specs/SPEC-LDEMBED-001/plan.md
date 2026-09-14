# 구현 계획 — SPEC-LDEMBED-001

[요구사항](spec.md) · [인수](acceptance.md) · [근거](research.md) · [공유 계약](../SPEC-LDPLUGIN-001/contract.md)

## 1. entry gate와 소유 경계

선행 SPEC의 실제 Claude Code→앱→approved programming→feedback 왕복, full expressive compiler fidelity, 실제 감독 pilot 증거를 먼저 확인한다. 이후 별도 Implementation Kickoff Approval을 받아 내장 runtime을 구현한다. 선행 미완료를 이 프로젝트가 대신 완성하는 구조가 아니다.

- `DirectorService`는 canonical context/plan/knowledge/validation/submit/receipt/feedback를 소유한다. 내장 runtime은 host adapter이며 승인·compiler·예술 규칙의 새 소유자가 아니다.
- 공유 네 skill은 `plugins/lighting-director/skills/{music-evidence-review,whole-song-direction,cue-plan-authoring,director-feedback}/SKILL.md`의 versioned source를 읽는다. 배포 build가 같은 source digest의 packaged resource를 제공하고 runtime에 로컬 checkout 경로를 강제하지 않는다.
- 외부 host는 stdio→HTTP, 내장 host는 같은 service의 application interface로 dispatch한다. 둘 다 같은 principal/project scope와 DTO validation을 거친다. 호출 방식만 다르며 내부 privileged shortcut이 없다.
- SQLite director store에 run/checkpoint를 추가하되 plan state enum은 바꾸지 않는다. 아래 runtime 상태는 **내부 orchestration 상태**이며 교환 message_type/PlanState가 아니다.

## 2. structured runtime tool loop

| 항목 | 확정 구현 |
|---|---|
| 내부 상태 | idle→running 이후 waiting_user/completed/cancelled/failed 중 하나. waiting_user에서 명시 resume으로 running. process restart 시 running은 waiting_user로 회수. run_id/generation 번호로 늦은 응답을 구분 |
| 입력 | authenticated principal/project, brief, 선택한 procedure, context_id/digest, plan_id/revision(있을 때), skill version, provider name/model_id. server가 권한 범위를 결정 |
| 호출 | 기존 LLMProvider.complete(system_prefix, conversation, tools). 네 절차 원본+안전 경계+tool schemas는 stable prefix, context/검색 결과/사용자 변경은 conversation |
| dispatch | ToolDefinition→ToolCall.name/arguments 검증→7개 ld_* service 함수. 같은 turn의 calls는 순차 dispatch하여 validation/submit 의존 순서 유지. 각 tool_call_id에 정확히 하나의 ToolResult, 같은 turn 전체를 ToolResultsMessage 하나로 전달 |
| 제한 | run당 model turn 12·tool call 32, context input은 provider adapter가 제공하는 model context 한도의 75% 이내. 토큰 산정은 기존 provider 사용량/가용 tokenizer를 사용하고 미확정 한도는 호출 전에 configuration error로 중단. output/tool-result 공간 25% 예약 |
| 오류 | ProviderError를 사용자 오류·인증·timeout·rate/의존 장애로 표시. 자동 무한 재시도 없음. JSON/권한/tool 오류는 is_error로 상관관계를 유지하고 남은 budget 안에서 모델이 수정할 수 있음 |
| 종료 | tool_calls 없는 정상 ModelTurn은 draft/요약과 completed. model의 '승인됨/적용됨' 텍스트는 실제 PlanRecord/ExecutionReceipt state로 검증하여 표시. 새 plan을 제출하지 않은 생성 결과는 draft 후보일 뿐 |
| pause | budget 소진/사람 입력 필요/복구 불확실은 waiting_user. 현재 draft·원인·재개 시 수행할 절차를 보여주고 사용자가 새 budget으로 resume해야 함 |
| cancel | cancel generation을 durable 기록하고 이후 dispatch 금지. 동기 complete는 worker executor에서 수행하여 UI를 막지 않는다. provider 자체 cancel 미지원이면 in-flight 반환을 폐기하고 cancelled로 남김; provider 비용/서버 처리가 즉시 멈췄다고 주장하지 않음 |
| mutation 중 cancel | 이미 전송한 submit/propose의 intent·idempotency key를 먼저 저장. 응답 유실 시 같은 operation의 저장 응답/GET을 확인한 뒤 상태를 정리. 새 key로 맹목 재전송 금지. runtime에는 apply tool이 없어 자동 console write는 없음 |

provider를 run 도중 바꾸면 현재 호출 결과를 같은 provider context에만 기록하고 다음 단계는 waiting_user로 전환한다. 사용자 resume 시 neutral conversation으로 새 provider를 시작하며 이전 provider_payload는 전달하지 않는다. 임의 추가 모델 설치/선택을 필수로 요구하지 않는다.

## 3. persistent context와 resume

`server/director/run_store.py`가 기존 director SQLite migration에 `director_runs`, `director_run_events`, `director_tool_intents`, `director_checkpoints`를 추가한다. 각 row에 principal/project/run/generation과 append sequence를 결합한다. event는 user input, model neutral output, tool intent/result, state transition, budget usage를 저장한다. secret/raw audio는 저장하지 않는다. provider_payload가 재사용에 필요한 경우 같은 provider 전용 최소 데이터만 앱 보호 저장소에 저장하고 다른 provider에는 보내지 않는다.

| 복구 대상 | 처리 |
|---|---|
| 확정 facts | context/plan/evidence/knowledge revision의 immutable refs로 재조회. 요약 문자열을 권위로 사용하지 않음 |
| 긴 conversation | budget 전 기존 도구 결과를 ref+검증된 요약으로 압축. 사용자 명시 intent·미해결 진단·terminal/FX·scope를 삭제하지 않음. 실제 typed plan은 별도 원본으로 보존 |
| revoked knowledge | resume 시 current approved/non-revoked scope-filtered retrieval을 다시 수행. 기존 요약의 철회된 record ID를 제거/무효 표시 |
| stale context/head | 새 context/head를 보여주고 새 draft revision에 rebase 제안. 예전 승인 재사용 금지 |
| 미완료 tool intent | idempotency 저장 응답/객체 read로 확인 후 결과를 확정. 결과를 모르면 waiting_user이며 unbounded retry 없음 |
| socket 재연결 | same principal/project/run event cursor 이후만 replay. 다른 사용자 socket으로 알림 fallback 금지 |

## 4. milestones와 concrete paths

아래 신규 경로는 구현 계획이며 현재 존재/구현을 주장하지 않는다.

| 단계 | 소유·파일 | 완료 기준 |
|---|---|---|
| E0 선행 증거·계약 pin | integration owner: 선행 SPEC artifact/인증 report, `server/llm/{types,factory,runtime}.py` | shared contract/skills/compiler version 고정, adapter 지원 범위·context 한도 확정, kickoff 승인 |
| E1 host runtime | runtime owner: 신규 `server/director/{embedded_host,run_store,context_builder}.py`, `server/director/migrations/002_embedded_runs.sql`; 기존 `server/llm/{types,runtime}.py`는 필요한 adapter-neutral budget metadata만 확장 | structured tool loop·budget·cancel·checkpoint/resume. service/approval logic 복제 없음 |
| E2 app route/UI | UI owner: 기존 `server/web/{session,app,director_api}.py`, `ui/src/{App,protocol,useCopilotSocket}.ts*`, `components/{RunbookMode,ChatView,DirectorReview}.tsx`; 신규 `ui/src/components/DirectorRun.tsx` | 명시 director mode+자연어 곡 설계 intent가 동일 절차로 연결, start/progress/pause/cancel/resume·draft/review 화면. 일반 console chat은 기존 도구로 유지하되 shared lock 유지 |
| E3 두 producer cutover | integration owner: `server/web/session.py::_build_unified_song_plan` 및 호출부, `server/orchestrator/tools.py::prepare_songcue`, `server/looks/songcue.py::map_sections_to_looks`, 관련 `server/design/song_plan.py`, `song_cue_composer.py` 경계 | 기존 인터뷰·prepare_songcue 두 진입점은 같은 embedded orchestration을 요청하고 canonical plan을 받음. old fixed arc/role/반복 사다리 정책·obsolete imports/branches 제거. 수학적 timing/검증/표시 helper는 독립 유용성 있을 때만 유지 |
| E4 parity·운영 전환 | integration owner: `tests/director/` 기존 contract regressions, 관련 producer/UI 기존 tests, package 운영 문서 | fixed plan parity·실제 model smoke·cancel/resume·external 유지·의도 보존 pilot 인수, 배포·rollback 절차 |

공유 `session.py`, `tools.py`, provider types 변경은 integration owner가 직렬 통합한다. runtime owner는 same service contracts, UI owner는 durable run event를 소비한다. 관련 테스트가 old finale 상승/반복 강제 정책 자체를 정답으로 고정했다면 폐기하고 사용자 의도 보존 contract만 남긴다. 파일 이름에 맞추기 위한 호환 alias·old producer fallback은 두지 않는다.

## 5. cutover·배포·복구

1. read/draft 전용으로 내장 host를 켜고 외부와 fixed plan parity를 확인한다. UI에 현재 orchestration owner(external/embedded)를 표시한다.
2. 기존 인터뷰와 prepare_songcue 진입점의 모든 소비자를 새 shared orchestration으로 치환한다. 자동 테스트만 아니라 두 실제 UI/명령 진입점을 smoke한다. 기존 문서/timeline을 canonical plan으로 무손실 재해석하지 않는다.
3. 두 예술 producer의 obsolete policy와 호출부를 제거한 빌드를 출시한다. 장애 시 old policy 자동 fallback은 없다; 사용자가 외부 host를 선택하거나 read-only로 전환한다.
4. external/embedded가 같은 plan을 동시 수정하면 CAS conflict를 그대로 보여준다. owner 선택은 orchestration 중복을 막는 UX이며 ACL/CAS를 대체하지 않는다.
5. rollback은 내장 신규 run 비활성·기존 run waiting_user 회수·기록 보존·외부 경로 사용으로 진행한다. schema migration은 기존 immutable records를 보존하는 additive migration이며 rollback 중 승인·journal을 삭제하지 않는다. **앱 코드 rollback은 OSC undo가 아니다.** partial/unknown은 선행 recovery 절차를 유지한다.

검증 층·측정 gate·각 요구사항의 인수는 [acceptance.md](acceptance.md)에서 판정한다. 이 계획의 단계 완료는 현재 성과가 아니다.
