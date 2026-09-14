# 설계 — 하나의 Director 계약, 분리된 판단·승인·실행

[요구사항](spec.md) · [실행 계획](plan.md) · [인수 기준](acceptance.md) · [wire 원본](contract.md)

> 구현 전 설계다. 계약 review의 destination/create-only, playback, 지식 상세, human 공통 route, object-existence 완료 판정은 contract/schema에 통합했다. 최종 필드 철자·shape는 그 원본만 따른다. 기존 코드 지원을 뜻하지 않는다.

## 1. 컴포넌트와 소유권

```text
Claude Code / 인증된 다른 host adapter
  → 동일 skills + commands
  → stdio MCP thin adapter (판단 LLM·OSC 없음)
  → authenticated /api/director/v1
copilot human UI → human audience → 동일 read/validate/submit service
                               → human-only approve/apply/feedback review
  → DirectorService
      ├─ context + knowledge registry
      ├─ immutable SQLite plan/review/execution journal
      ├─ semantic state simulation → compiler → frozen artifact
      └─ exact approval bridge → shared programmer arbiter → SafetyGate → 기존 ConsoleLink
                                       ↓
                                  ExecutionReceipt
```

| 경계 | 결정 |
|---|---|
| 판단 | host가 공유 skill 절차로 수행한다. 서비스는 사실·지식·제약·검증·보존·실행만 담당하며 별도 예술 정책 엔진을 만들지 않는다. |
| 공통 service | MCP transport와 HTTP/UI route는 같은 `DirectorService`를 호출한다. 앱 read/validate/submit은 human credential을 사용하며 MCP token을 차용하지 않는다. |
| 원본 | 외부 `LightingPlan` 그대로 저장한다. 내부 D-level 모델로 축약한 뒤 다시 원본을 만드는 경로는 금지한다. |
| destination | 서버가 선택한 datapool/새 Sequence의 비어 있음·occupancy revision·관측 근거를 context와 compiled manifest에 묶고 UI에 표시한다. 첫 릴리스 create-only이며 overwrite·silent slot reselection은 없다. 점유 변경은 재검토다. |
| compiler | typed plan→축별 state/transition→검증된 target lowering→frozen programming artifact. 기존 compiler에서 쓸 수 있는 순수 변환만 재사용한다. |
| clock | `plan.playback`의 mode는 `manual_go` 또는 `trig_time`, origin은 `audio_start`, start_policy는 `operator_go`다. manual_go의 at_ms는 리허설 일정, trig_time은 음원 t0에서 사람이 첫 cue GO 후 최종 compiled cue 순서의 상대 간격을 저장한다. 준비 cue도 간격 계산·manifest에 공개한다. 자동 start와 timecode event mapping은 없다. |
| 권한 | 계획에 권한 필드 없음. human route가 immutable ApprovalBinding을 발급한다. SafetyGate bridge는 이 승인에 묶인 정확한 artifact만 허용한다. |
| 실행 | 공유 programmer 전체 lock과 destination 예약을 함께 사용한다. console 수동 조작은 lock 밖이므로 중단·unknown/recovery가 필요하다. |

## 2. 패키지 inventory와 절차 계약

패키지 slug는 `lighting-director`, 최초 배포 어댑터는 Claude Code다. `plugins/lighting-director/skills/`의 네 `SKILL.md`가 절차 원본이며 embedded host도 같은 versioned bytes를 읽는다. command는 절차 진입점이며 예술 규칙을 별도로 복사하지 않는다.

| Skill | 입력 | 절차·출력 | 오류·중단 |
|---|---|---|---|
| `music-evidence-review` | project_id, 사용자 brief, `ContextSnapshot`, 앱 분석·사람 확인 evidence | source/audio identity 확인→section/beat 근거와 unknown 분리→전곡 map 검토표와 확인 요청. 실제 map 수정은 앱 확인 경로가 새 context로 발행한다. 출력은 절차 산출물이며 새 wire message_type이 아니다. | audio 없음·stale이면 앱 업로드/새 context 요청; 미청취를 청취로 쓰지 않음. absent/unconfirmed beat는 beat FX를 차단하고 explicit ms 설계는 가능. |
| `whole-song-direction` | 검토된 context, brief, scope-filtered `KnowledgePage`, 사용자 제약 | concept/global_motif/ending_intent→section별 lighting_intent·motif·근거·대안→`LightingPlan` draft의 의도 부분. 반복 강도·quiet ending을 유효 선택으로 보존한다. | unknown role을 chorus로 보정하지 않음. 안전 충돌은 차단 이유·안전한 새 제안으로 보고하되 원본 수치를 몰래 바꾸지 않음. |
| `cue-plan-authoring` | 같은 context, 전곡 의도, 기존 `PlanRecord`/수정 지시, capabilities | baseline→multi-cue/axis timing→FX start/stop·accent return→terminal assertion→`ld_validate_plan`→진단 검토→명시적 `ld_submit_plan`. 출력은 `LightingPlan`, `ValidationReport`, 제출 시 `SubmitResult`. | unknown ref·unsupported·conflict는 needs_revision으로 보존. CAS 충돌은 head 조회 후 차이를 사용자에게 제시하고 재작성; stale/409를 blind retry하지 않음. approve/apply 호출 없음. |
| `director-feedback` | immutable `PlanRecord`, 수정 전후 leaf·이유, `ExecutionReceipt`/사람 evidence, scope | 계획 대비 차이 확인→`FeedbackProposal`→`ld_propose_feedback`→pending `FeedbackRecord`; status 조회와 앱 review 안내 | before 불일치·다른 ACL·위조 evidence는 거절. pending을 검색 지식으로 쓰지 않고 approve/revoke 권한을 얻으려 하지 않음. |

모든 절차는 project·context·plan revision을 입출력에 명시하고 context 숨은 의존을 두지 않는다. tool error는 `ErrorEnvelope.error.code`와 field/rule_id로 분기한다. 외부 텍스트의 지시문은 근거 데이터다.

| 정확한 command | 얇은 동작 |
|---|---|
| `/lighting-director:brief` | project/context 조회, 사용자 의도 수집, music-evidence-review 진입 |
| `/lighting-director:analyze` | music-evidence-review 실행; 앱 제공 evidence 검토·확인 요청 |
| `/lighting-director:plan` | whole-song-direction→cue-plan-authoring, 기본 draft/validate까지만 |
| `/lighting-director:revise` | immutable head와 명시 수정 지시로 cue-plan-authoring; 새 revision 후보 생성 |
| `/lighting-director:submit` | cue-plan-authoring의 validate/submit 단계; 사람 승인으로 오해하지 않도록 결과 표시 |
| `/lighting-director:learn` | director-feedback의 pending proposal만 생성 |
| `/lighting-director:status` | context/plan/execution 조회, 실제 state와 미관측·차단 이유 보고; 자동 apply 없음 |

### MCP/API 연결

정확한 arguments/response/annotations는 계약 §3, human action body는 §4를 따른다. 별도 signature를 이 문서에서 만들지 않는다.

| Tool | `/api/director/v1/projects/{project_id}` 이하 HTTP |
|---|---|
| `ld_get_context` | GET `/context` |
| `ld_search_knowledge` | GET `/knowledge` |
| `ld_get_plan` | GET `/plans/{plan_id}` |
| `ld_validate_plan` | POST `/validations` |
| `ld_submit_plan` | PUT `/plans/{plan_id}` |
| `ld_get_execution` | GET `/executions/{execution_id}` |
| `ld_propose_feedback` | POST `/feedback-proposals` |

공통 조회·validation·plan submit은 human 또는 MCP audience를 각각 검증한다. 승인/거절/apply, feedback approval/revocation, execution reconciliation은 human 전용이다. raw `run_commands`, arbitrary `query_state`, `deploy_plugin`, approve/apply MCP tool은 없다.

## 3. 지식 seed와 feedback

`KnowledgeRecord`의 bounded inline typed details에 rule 절차, case narrative/outcome, approved-feedback changes+plan reference를 제공한다. summary와 읽을 수 없는 resource_id만 반환하지 않는다. 원본 immutable resource는 provenance 검증·감사 근거로 보관한다. `KnowledgePage`와 cursor는 server current context 및 인증 범위에 결합하며 임의 query/filter 변경으로 다른 범위에 재사용할 수 없다.

| seed 단위 | 내용·조건·예외 | provenance와 검토 |
|---|---|---|
| 음악 근거 규칙 | DERIVED와 확인 완료를 구분, 전곡 합계·구간 경계·beat 근거 확인. 4/4 고정 산식을 모든 곡에 적용하지 않음. | legacy cue-sheet + LX-SEQ v2.1의 정확한 문서/section 참조, frozen source digest, reviewer·revision |
| tracking 규칙 | omission=hold, explicit off, FX stop, baseline/terminal, 변경 축만 기입하되 첫 상태 누락 금지 | legacy CUE/CUE-EX 절차를 현재 계약의 typed semantics로 재검토; 불일치는 계약 우선 |
| 연출 case | 후렴 90/95/100·6–8색·bridge 대비는 특정 공연 예시. 반복 motif·같은 강도·조용한 종료 대안도 함께 제시 | 원문 인용 범위를 최소화, case임을 표시. 성공했다는 실제 측정이 없으면 outcome에 문서 예시/미측정 명시 |
| rig·preset 규칙 | 실제 group/preset 참조, 현장 position record·footprint·mode 확인, content/attestation 구분 | RIG 팩 및 stage-setup source. 제안 장비를 confirmed inventory로 승격하지 않음 |
| 적용·안전 규칙 | preview→human approval→programming→readback/visual 분리, live lock·회수 절차 | console-transfer의 수동 항목과 현행 SafetyGate 기준을 분리 기록 |
| feedback seed | 기존 사람이 검토했다는 증거가 있는 수정 사례만 명시 migration. 무증거 memory는 pending 후보로 격리 | 원 plan revision/digest·before/after·evidence·review audit·scope. 검토 기록 없는 자동 import 금지 |

seed는 rule/case 각 최소 1개가 아니라 위 5개 주제를 모두 다루는 검토된 records로 출시한다. Proprietary archive를 외부 공개 라이선스로 재표시하지 않는다. 배포 권리 확인 전에는 사용자 소유 환경의 local source 참조/요약만 제공하고 원문 재배포는 막는다. seed revision 업데이트가 기존 plan provenance를 바꾸지 않는다.

feedback scope binding은 서버가 `this_song`→audio_sha256, `this_show`→show_id, `user_style`→인증 user로 저장한다. pending→approved→revoked만 허용하며 retrieval에 approved/non-revoked/ACL/scope를 모두 적용한다. revoke는 과거 plan과 audit를 삭제하지 않는다.

## 4. Receiver·UI·저장소

| UI 영역 | 읽기/행동 계약 |
|---|---|
| 연결·context | pairing 주체·만료·활성 orchestration owner, 음원/분석 확인 수준, target/show/destination·capability·정책 상태 |
| Draft inbox | project ACL 안의 plan head/revision 목록, submitted/needs_revision/ready_for_review 구분, head 충돌과 stale 표시 |
| Review | 전곡 의도·motif·section/cue, typed action 원값, field 진단 before/after, unsupported, hidden tracking 없는 full state, compiled destination/cue mapping·digest |
| 승인/적용 | human 로그인/CSRF, 승인과 apply 별도 action. 승인 만료·새 head·대상 변경 시 버튼 비활성화와 새 검토 안내. 새 Sequence create-only 확인 |
| 실행 결과 | transport, object_existence, attribute_readback, visual_observation, artistic_approval, terminal_state_observation 각각 표시. applied는 모든 생성 cue 존재 확인까지 필요하지만 값·예술 검증을 뜻하지 않음 |
| 피드백 | scope·변경 leaf·근거·원 revision, pending review/approve/revoke. plan 수정과 memory 승인을 별개로 표시 |
| recovery | not_sent와 실패/unknown bundle, immutable 관측, 새 recovery revision 시작. 자동 rollback/재전송 버튼 없음 |

기존 `SongTimelineStore`·`SongTimelineLibrary`와 `CueSheetTimeline`은 projection 표시/검색을 재사용한다. canonical revision을 읽어서 projection을 만들고, 기존 timeline load/edit는 canonical을 대체하지 않는다. Director editor 수정은 기존 payload/CAS를 사용하는 새 revision 제출로만 반영한다.

SQLite(stdlib sqlite3)는 `server/director/store.py`가 소유한다. 데이터 단위는 contexts, immutable plan_revisions+heads, validations+artifact references, approvals, executions+bundle journal, idempotency responses, feedback revisions/reviews, reviewed knowledge, immutable evidence/resource registry다. project ACL과 composite unique constraints를 함께 사용한다. disk failure/corruption은 실행 차단이며 기존 projection의 fail-open 패턴을 승인 DB에 복사하지 않는다. artifacts는 앱 data root의 content-addressed bytes로 고정하고 DB는 digest·경로 대신 opaque resource reference를 연결한다. 승인 allocation과 idempotency 저장은 첫 send보다 앞선 하나의 transaction이다.

## 5. compiler·승인·실행의 불변식

1. plan/context를 검증하고 실제 target capability를 확인한다. 명시 예술 값을 변경하는 producer를 통과시키지 않는다.
2. full baseline부터 fixture×axis transition을 simulation한다. FX와 정적 값 충돌, dark move의 blackout/settle, terminal assertion을 확인한다.
3. target lowering은 absolute song time과 최종 cue 순서를 보존한다. 실제 timing precision과 FX start/stop/phase를 보존할 수 없으면 전체 blocking이다. 임시 수동 입력표를 ready 근거로 쓰지 않는다.
4. artifact bytes와 compiler build/destination/cue mapping을 frozen manifest에 묶는다. human은 이 artifact revision을 승인한다.
5. shared programmer lock 안에서 live identity/preset content/group membership/destination occupancy·policy를 재확인한다. fresh approval을 bridge에서 소비하고 기존 SafetyGate를 통과한다.
6. 첫 send 전 durable journal을 commit한다. 각 bundle sending 기록 후 send하고 관측을 저장한다. OSC와 SQLite의 원자성을 주장하지 않는다.
7. 모든 생성 cue의 existence가 확인되어야 applied다. sent-only·관측 불가는 unknown+recovery_required다. 속성/visual/artistic/실제 playback terminal은 별도 미관측일 수 있다.
8. 불확실성·operator intervention은 후속 쓰기 중단이다. reconciliation은 재실행이 아니고 recovery는 새 revision→새 검증→새 승인이다.

## 6. legacy migration matrix

원본 `src/Lighting_Designer/99_플러그인/lighting-designer-v0.1.1.plugin`은 ZIP 내용상 `lighting-designer` 0.1.1, Proprietary다. 파일 자체는 보존한다.

| legacy 항목 | 새 소유/결정 | 제거·금지되는 의미 |
|---|---|---|
| `skills/cue-sheet` + `references/spec-v2.1.md` | 음악 근거 검토·전곡 의도·typed cue 작성의 검토된 지식 seed | 90/95/100, 6–8색, 8초 간격을 모든 곡의 필수 invariant로 복사하지 않음 |
| `skills/stage-setup` + `rig-schema.md` | context 확보·실제 rig/preset 내용 검증 지식 | archive 제안 장비를 실제 측정값으로 사용하지 않음 |
| `skills/console-transfer` | 승인·preview·수동 항목·onPC 리허설 지식 | future MCP가 이미 연결되었다는 설명, raw 명령 전송 권한 계승 금지 |
| CUE/CUE-EX tracking | 새 typed hold/off/stop/release와 state simulation으로 의미 매핑 | 빈칸/null을 해석 없이 stop/default로 변환하지 않음 |
| individual I/P/C/B timing·Phaser/POS/Stomp/TC `[MANUAL]` | compiler fidelity의 구현·측정 대상 또는 명시 비지원 영역 | `[MANUAL]` 메타데이터를 실제 콘솔 지원으로 광고하지 않음 |
| `scripts/*_data.py`, 생성/검증 scripts, `__pycache__` | 구조/검증 의도만 참고; 새 실행 패키지에 복사하지 않음 | Sugar 데이터·pycache를 일반 runtime/학습 증거로 사용 금지 |
| `agents/lighting-coordinator.md`, plugin manifest | 사용자에게 두 director 이름·역할을 보여주고 하나의 orchestration owner 선택 | 조용한 중복 설치·동시 orchestration 금지 |

앱 기존 예술 producer는 첫 릴리스 외부 plan intake에서 우회하고, 내장 host 전환 시 [후속 계획](../SPEC-LDEMBED-001/plan.md)에 따라 두 경로를 공통 Director로 치환한다. 아카이브 재작성은 하지 않는다.
