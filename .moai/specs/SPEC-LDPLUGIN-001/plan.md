# 구현 계획 — SPEC-LDPLUGIN-001

[요구사항](spec.md) · [설계](design.md) · [인수](acceptance.md) · [계약](contract.md) · [근거](research.md)

## 1. 착수와 경계

현재 산출물은 문서/schema뿐이며 runtime 변경·설치·콘솔 조작을 승인하지 않는다. Implementation Kickoff Approval 이후 아래 순서로 구현한다. Python/FastAPI·기존 LLMProvider·React UI·SafetyGate/ConsoleLink 경계를 재사용하며 별도 판단 서버·OSC 연결을 만들지 않는다. 신규 경로는 **예정 경로**다. 계약 review의 destination/playback/knowledge/human-read/applied 보강은 contract/schema에 통합했으며 구현 입력은 해당 version을 따른다.

## 2. 단계와 source ownership

| 단계 | 구현 책임·파일 | 완료 산출물·의존 |
|---|---|---|
| M0 계약·증거 baseline | integration owner: SPEC contract/schema/examples; `server/lxseq/cue_parser.py`, `cue_mapper.py`, `server/orchestrator/tools.py`, `server/design/song_plan.py`, `song_cue_composer.py`의 현행 경계 조사 | 승인된 요구 범위·source baseline·compiler gap 목록. synthetic와 runtime 결과 분리. 구현 kickoff 승인 필수 |
| M1 canonical service·저장 | domain owner: 신규 `server/director/{models,store,service,context,knowledge}.py`, `server/director/migrations/001_initial.sql`; 기존 `server/web/serve.py` data-root wiring | strict parsing/JCS·CAS·immutable revisions·resource registry·knowledge seed·context/current target binding. DB 장애 시 fail closed. M0 후 |
| M2 semantic compiler | compiler owner: 신규 `server/director/{validation,state,compiler,capabilities}.py`; 기존 `server/design/song_cue_composer.py`, `rig_preflight.py`, `rig_capability_read.py`, `server/lxseq/cue_mapper.py` 순수 재사용; `server/orchestrator/tools.py` emitter 연결 | 전곡 atomic prevalidation, full expressive subset frozen artifacts, 실제 target별 fidelity table. 예술 producer를 호출하지 않음. M1 후 |
| M3 인증 receiver·실행 | API/safety owner: 신규 `server/web/director_api.py`, `server/director/{auth,approval,execution}.py`, `server/safety/programmer_arbiter.py`; 기존 `server/web/{app,serve,approval_bridge}.py`, `server/safety/{gate,approval,lock}.py`, `server/orchestrator/tools.py`, `server/design/cue_sheet_apply.py`의 모든 shared writer | paired audience/scopes, 공통 human/MCP read/validate/submit, human-only approve/apply/reconcile, destination create-only, durable journal·idempotency·approval bridge·모든 writer 공통 lock. M1/M2 후 |
| M4 host 패키지·지식 | package owner: 신규 `plugins/lighting-director/.claude-plugin/plugin.json`, `.mcp.json`, `skills/{music-evidence-review,whole-song-direction,cue-plan-authoring,director-feedback}/SKILL.md`, `commands/{brief,analyze,plan,revise,submit,learn,status}.md`; 신규 `server/director/mcp_adapter.py`, `server/director/knowledge_seed/` | 네 절차·일곱 alias·정확한 일곱 tools, seed 5주제, 최초 Claude Code pairing/initialize/tools/list. `.mcp.json`은 신규 패키지 안이며 저장소 루트 개발용 파일은 불변. M1/M3 후 |
| M5 UI 왕복 | UI owner: 신규 `ui/src/directorApi.ts`, `ui/src/components/{DirectorInbox,DirectorReview,DirectorExecution,DirectorFeedback}.tsx`; 기존 `ui/src/{App,protocol,useCopilotSocket}.ts*`, `components/{RunbookMode,CueSheetTimeline,ApprovalCard,ReviewCard}.tsx`, `server/web/{session,timeline_api,timeline_library}.py` projection seam | draft/revision diff·근거/상태·freshness·human approve/apply·각 관측·feedback approve/revoke·recovery가 실제 service와 연결됨. M3 후, M4와 같은 contract 사용 |
| M6 통합·인증·pilot | integration owner: `tests/director/`, 관련 기존 테스트, `tests/e2e/`의 실제 프로젝트 convention 확인 후 최소 회귀; package 사용/운영 문서 | acceptance의 schema/static/semantic/host/onPC/artistic 증거, 모델/host/target version 기록, 출시 go/no-go. M1–M5 모두 필요 |

파일 경계를 넘는 공유 mutation은 integration owner가 한 번에 통합한다. 특히 `tools.py`, `session.py`, `app.py`, `gate.py`를 여러 작성자가 동시에 수정하지 않는다. M2 compiler API와 M3 execution이 주고받는 값은 canonical plan/context, ValidationReport.compiled.manifest와 frozen artifact resource뿐이다. M4/M5는 service의 동일 DTO/API만 소비하고 상태·검증 로직을 복제하지 않는다.

## 3. compiler fidelity: 실제 구현할 작업

현재 코드의 미구현/메타데이터 경로는 **이 SPEC의 구현 작업**이며 후속으로 넘기는 placeholder가 아니다. 현재 parser 수용 여부와 별개로 아래를 완성해야 첫 릴리스를 낼 수 있다.

| 현행 gap | 구현 산출물 | 반드시 측정할 gate |
|---|---|---|
| `tools.py`의 `per_row_timing`은 개별 I/P/C/B 값 기록이며 actual emit이 아님 | `Timing`을 intensity/color/pan/tilt/beam/fx별 실제 target 명령/저장 데이터로 lowering. pan·tilt 독립 delay/fade. scalar CueFade 근사 제거(Director 경로) | 서로 다른 축·그룹 timing이 object/readback/화면에 의도대로 보존; 해상도 미표현은 LD-CAP-001 blocking |
| `fx_stopped_groups`는 stop 메타데이터이고 `fx_rate`의 실제 소비 경로가 확인되지 않음 | known FX preset instance start·cycle_beats/phase_beats·explicit stop fade와 base state 복귀 구현 | 실제 시작·cycle/phase·stop 이후 기여 0, terminal FX 누수 0 |
| `max(row I-Fade)` 기반 CueFade 근사 | contract 축별 timing을 저장하는 compiler 전용 IR과 frozen artifact. authored 값 변경 없이 diagnostic coverage | 원본 leaf→emitted field 대응, 하나도 silent drop/substitute 없음 |
| 절대 cue time을 곧바로 TrigTime에 쓰는 기존 경로 | manual_go는 일정 표시, trig_time은 첫 cue operator GO/audio t0 이후 **최종 compiled cue 순서의 delta** 저장. 준비 cue·cue-number mapping·destination을 manifest에 포함 | first/last cue·accent·준비 cue 포함 재생 시간표를 onPC에서 대조. timecode mapping은 명시 unsupported |
| MIB와 tracking 상태가 다른 내부 모델의 정책에 결합 | canonical plan 직접 simulation, verified baseline, blackout·pan/tilt completion·settle, negative-time 금지, random-access full state/phase lowering | dark movement 중 visible intensity 0, reveal 불변; 중간 fade re-entry 미재현은 unsupported |
| 실제 cue attribute 되읽기 제약 | target/responder에서 지원되는 object 존재·속성 관측만 수집; 필요 시 기존 responder 확장은 증거 수집 범위로 한정 | 모든 생성 cue 존재 확인 없으면 unknown+recovery_required; readback unsupported는 unknown으로 남김 |

특정 console build/rig가 불가능하면 capabilities를 줄이고 그 조합을 비인증 처리한다. **릴리스 필수 표현 항목 전체를 실증한 적어도 하나의 인증 onPC+rig 조합이 있어야 한다.** 무제한 Phaser 저작이나 임의 기종 지원을 추가하지 않는다. compiler version/build와 rig/content fingerprint를 인증 결과에 고정한다.

## 4. 저장·승인·마이그레이션 build order

1. SQLite schema·unique/CAS·JCS 및 immutable bytes 저장을 먼저 완성한다. DB와 artifact 저장은 검증 완료 후 연결하며 불완전 resource는 승인에 사용할 수 없다.
2. 기존 `SongTimelineLibrary`는 읽기 projection으로 남긴다. reviewed memory만 provenance/review evidence를 보존해 이관하고 검토 증거 없는 항목은 pending 후보로 격리한다. UI timeline을 역변환하여 승인 원본으로 import하지 않는다.
3. context는 live show/session, group membership, frozen preset content/명시 attestation, compiler build, destination의 비어 있음·occupancy를 묶는다. observation freshness를 못 확인하면 새 context/사람 확인 없이는 ready/approval을 유지하지 않는다.
4. 서버에서 validation을 생성하고 UI에 원본/진단/manifest를 표시한다. human ApprovalBinding을 생성한 뒤 SafetyGate exact-artifact bridge를 연결한다. legacy approval boolean 경로와 섞지 않는다.
5. shared programmer arbiter를 모든 director/chat/import write seam에 연결한 후에만 Director apply를 활성화한다. target reservation만 넣고 중재가 완료되었다고 판정하지 않는다.
6. durable execution allocation→approval consume→idempotency 저장→bundle journal을 첫 write 전에 commit한다. crash point마다 unknown 회수·후속 not_sent가 가능해야 한다.
7. app feedback review와 scope-filtered knowledge retrieval까지 연결한다. 모델의 learn 호출은 pending만 만든다.

## 5. rollout·중단·복구

| 단계 | 허용 | 금지·중단 조건 |
|---|---|---|
| local read/draft | pairing, context/knowledge/validate/submit, UI review | console 쓰기 0; production에 synthetic evidence 혼입 시 중단 |
| human-authorized onPC pilot | 검증된 rig·새 Sequence, preview 이후 별도 human approve/apply; playback은 사람이 별도 수행 | 기존 Sequence overwrite·자동 GO/timecode start 없음. 대상 점유/identity 변경 시 재검토 |
| first release | AC 전체 및 gate 통과한 Claude Code+target 조합, unknown/recovery UI와 운영 runbook | plugin-only, metadata-only timing/stop, 미인증 host를 지원으로 표시 금지 |
| 다른 host adapter | 동일 service+skills, transport/auth/account capability를 개별 인증 | ChatGPT 자동 호환·구독/계정별 가용성 보장 금지 |
| 코드 rollback/서비스 중단 | 신규 apply 차단, credential 철회, journal/미완료 execution 보존, 이전 호환 앱으로 read-only 진단 | DB/승인 기록 폐기로 replay 허용 금지. **앱 rollback은 이미 보낸 OSC/콘솔 저장을 되돌리지 않는다.** |

부분/불확실 실행은 원본 receipt를 보존한다. readback/reconciliation 후 recovery plan의 새 revision을 검증·승인하여 `recovery_of`로 적용한다. 별도 operator cleanup도 evidence/attestation을 구분한다. 자동 rollback·blind resend·silent ClearAll은 없다.

## 6. 위험 실험과 판정

- 대상 console build에서 개별 축 timing/FX phase/stop·cue existence를 실제로 표현·관측할 수 있는지 먼저 onPC prototype으로 측정한다. 실패 시 해당 구현/범위를 정정하고 승인된 필수 범위를 완료하기 전에는 출시하지 않는다.
- 실제 음악 map 품질과 연출 품질을 분리한다. 처음에는 사람이 확인한 map으로 연출을 평가하고 자동 분석은 별도 대조군으로 측정한다.
- 강제 후렴 상승을 없앤 설계가 더 나은지는 held-out blind pair·수정시간으로 판정한다. 개선율이나 전문가 수준을 선포하지 않는다.
- 문서/schema/example 정합성 검사는 실제 구현·호스트·콘솔 검증과 분리한다. 향후 구현 증거의 기준은 [acceptance.md](acceptance.md)에 두며 문서 검사 결과로 구현 AC를 pass 처리하지 않는다.
