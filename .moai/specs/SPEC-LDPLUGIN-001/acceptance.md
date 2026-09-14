# 인수 기준 — SPEC-LDPLUGIN-001

[요구사항](spec.md) · [계약](contract.md) · [설계](design.md) · [구현 순서](plan.md)

## 1. 증거 상태와 분류

**현재 모든 구현 AC는 미실행이다.** 문서/schema/example 작성, 합성 hash 계산 또는 과거 local 함수 probe는 신규 API/호스트/콘솔/예술 품질 pass가 아니다. 계약 review 보강(destination/playback/지식 상세/human 공통 route/존재 확인 후 applied)을 포함한 최종 계약을 기준으로 인수한다.

| 분류 | 증명하는 것 | 증명하지 못하는 것 |
|---|---|---|
| S — schema/static | shape·버전·closed 필드·상한·signature·권한 surface | state simulation, emitter, 실제 연결 |
| D — deterministic domain | 합성 고정 plan의 의미·hash·CAS·state·fidelity 진단 | 실제 음악·onPC·실행 성공 |
| H — host/app smoke | 실제 Claude Code initialize/tools/list와 실행 앱 왕복·인증/UI | 콘솔 timing/예술 품질 |
| C — onPC 관측 | human-authorized programming trace, cue existence, 지원 attribute readback, 화면·재생 관측 | 미지원 속성 확인, 모든 rig 호환 |
| A — artistic pilot | 확인된 map 기준 held-out paired review·수정시간 | 보편 전문가급 성능·모델 청취 능력 |

증거에는 source revision, schema/compiler build, host/model/target version, rig/context digest, 입력 fixture 또는 허가된 audio ID, 실행 주체·시각, 기대/실제 결과·관측 한계를 기록한다. onPC 실제 evidence와 synthetic fixture는 저장 namespace·environment를 분리한다.

## 2. 요구사항→AC 1:1 추적

모든 행은 Given–When–Then 인수 시나리오다. `Rnnn`은 정확히 `REQ-LDPLUGIN-nnn`의 축약이며 다른 요구를 뜻하지 않는다.

| AC | REQ | 분류 | Given / When / Then 및 제출 증거 |
|---|---|---|---|
| AC-LDPLUGIN-001 | REQ-LDPLUGIN-001 | H+C | Given 인증 host·앱·onPC, When draft→검토→human 승인→apply→feedback 승인·검색, Then 모든 단계가 같은 immutable plan 참조로 연결된다. host 기록/UI 캡처/receipt/검색 결과를 함께 제출. 하나라도 끊기면 미완료. |
| AC-LDPLUGIN-002 | REQ-LDPLUGIN-002 | S+H | Given copilot OSC 연결이 활성, When stdio adapter를 함께 시작, Then 앱 종료 없이 tools 사용 가능하고 adapter의 ConsoleLink 생성·OSC bind·추가 판단 LLM 호출은 0. 프로세스/연결 관측 기록. |
| AC-LDPLUGIN-003 | REQ-LDPLUGIN-003 | S+H | Given 설치 패키지, When 네 skill과 일곱 정확한 command를 실행, Then design §2의 입력·출력·실패가 일치하고 command별 별도 정책이 없다. 특히 analyze는 evidence 미확정 안내, learn은 pending만 반환. |
| AC-LDPLUGIN-004 | REQ-LDPLUGIN-004 | D+H | Given 동일 slot의 preset/content 또는 group/show/compiler/destination occupancy 변경, When context 조회/승인 재검사, Then digest/binding이 바뀌고 이전 승인 사용이 차단된다. unreadable을 confirmed로 승격하지 않는다. |
| AC-LDPLUGIN-005 | REQ-LDPLUGIN-005 | D+H | Given audio/beat/role 일부 미확정, When analyze/plan, Then unknown·confidence·출처가 남고 앱 확인 요청이 표시된다. 120 BPM/chorus/청취 완료를 만들지 않으며 explicit ms 계획은 가능한 범위만 검증. |
| AC-LDPLUGIN-006 | REQ-LDPLUGIN-006 | D+A | Given 동일 후렴 70%·quiet ending·반복 motif 의도, When plan 작성 및 compile, Then 의도·provenance가 유지되고 finale 자동 상승·불필요 변주가 없다. 고정 plan diff와 사람 검토 기록. |
| AC-LDPLUGIN-007 | REQ-LDPLUGIN-007 | S+D | Given 다섯 정상 fixture와 unknown field/version/null/NaN/중복 key/invalid UTC/초과 크기·cue·group·action·잘못된 ref 입력, When 수신, Then 정상 shape만 허용하고 계약 code·pointer를 반환한다. invalid 제출은 revision·write 0. |
| AC-LDPLUGIN-008 | REQ-LDPLUGIN-008 | D+C | Given 모든 §7 op·독립 timing·FX cycle/phase·accent return·release를 쓰는 plan, When compile/apply, Then 요청 leaf가 실제 artifact와 target에 보존된다. raw 문자열·silent clamp·drop·substitution은 거부. 표현 범위별 trace matrix. |
| AC-LDPLUGIN-009 | REQ-LDPLUGIN-009 | D+C | Given manual_go/trig_time·준비 cue·tempo change·동일 ms·반올림 경계, When lowering, Then 원음 t0·최종 cue delta·cycle 분할이 계약과 일치한다. 첫 GO는 사람이 수행하고 apply가 시작하지 않는다. timecode mode·음수 준비·불가능 해상도는 차단. |
| AC-LDPLUGIN-010 | REQ-LDPLUGIN-010 | D+C | Given 누락 baseline/stop/terminal 또는 released 이후 부분 재진입, When validation, Then blocking. 완전 baseline→hold→stop→safe release plan은 simulation terminal과 일치하며 실제 clean baseline 관측 없이 ready 불가. |
| AC-LDPLUGIN-011 | REQ-LDPLUGIN-011 | D | Given 겹친 group의 동일 fixture×axis, FX affects_axes·delay/fade 겹침, When 검증, Then 동일 값이어도 conflict. transition 끝=다음 시작은 허용하며 배열 순서로 덮어쓰지 않는다. |
| AC-LDPLUGIN-012 | REQ-LDPLUGIN-012 | D+C | Given pan/tilt 다른 종료와 settle, 중간 fade·active FX re-entry, When preview/compiler, Then blackout 유지·reveal 불변·full state/phase 복원을 관측한다. 불가하면 unsupported; 미지원 random_access를 true로 광고하지 않음. |
| AC-LDPLUGIN-013 | REQ-LDPLUGIN-013 | D+C | Given parser만 지원하거나 timing/stop 메타데이터만 생성하는 compiler, When capability 광고/ready 판정, Then unsupported+blocking. 구현한 조합에서 plan §3 각 gap의 실제 emit/target 관측이 있어야 지원으로 승격. |
| AC-LDPLUGIN-014 | REQ-LDPLUGIN-014 | D | Given 한 critical 불가 action과 나머지 정상 action, When validation, Then 전체 blocked/compiled.available=false·write 0이며 모든 action 및 변경/누락 leaf에 진단이 있다. advisory는 hard limit을 완화하지 않음. |
| AC-LDPLUGIN-015 | REQ-LDPLUGIN-015 | D+H | Given head revision N에 두 제출자, When 같은 expected_revision으로 동시 submit, Then 하나만 N+1·다른 것은 REVISION_CONFLICT. 재시작/과거 revision 조회 시 원본 bytes 의미·digest·base_revision 불변. |
| AC-LDPLUGIN-016 | REQ-LDPLUGIN-016 | H | Given unsupported/stale/새 head와 기존 timeline projection, When UI review/edit/load, Then 원본 값·진단·digest·destination/cue mapping이 보이고 projection load는 승인/원본을 변경하지 않는다. 수정은 새 CAS revision. 실제 화면 캡처. |
| AC-LDPLUGIN-017 | REQ-LDPLUGIN-017 | S+H | Given 실제 Claude Code, When initialize/tools/list 및 일곱 tool 정상/오류 call, Then 계약 exact schema·structuredContent/text·isError·HTTP code가 일치하고 approve/apply/raw tool이 없다. 연결 transcript. |
| AC-LDPLUGIN-018 | REQ-LDPLUGIN-018 | D+H | Given expired/revoked/wrong-audience·scope/교차 project·bad Host/Origin/CSRF 요청, When replay 포함 호출, Then 401/403/404 등 계약 오류이며 정보 유출·mutation 0. human read/submit은 자기 credential로 성공, MCP token 차용 없음. |
| AC-LDPLUGIN-019 | REQ-LDPLUGIN-019 | D+H | Given 위조 human_confirmed/approved 문구·prompt injection·arbitrary resource와 audio 외부 전송 요청, When 조회/검증, Then 서버 evidence ACL로 판정하고 명시 앱 동의 전 audio 전송 0. secret이 모델/로그에 없는 증거. |
| AC-LDPLUGIN-020 | REQ-LDPLUGIN-020 | D+H | Given ready plan, When human approve와 MCP/legacy WS boolean 위조를 각각 시도, Then human만 exact binding을 생성. revision/context/artifact/policy/target/만료 변경 뒤 승인 재사용은 거부. 승인 알림의 타 principal fallback 0. |
| AC-LDPLUGIN-021 | REQ-LDPLUGIN-021 | D+C | Given 승인 후 LiveLock/target occupancy/content 변경, When apply 직전 검사, Then send 0. 정상 apply는 exact-artifact bridge와 기존 SafetyGate 각 단계 trace를 남기며 destination create-only·기존 Sequence overwrite 0. |
| AC-LDPLUGIN-022 | REQ-LDPLUGIN-022 | D+C | Given director ClearAll/Group/At/Store bundle 중 동시 chat/import mutation, When 실행 경쟁, Then TARGET_BUSY이며 명령 interleave 0. 대상 Sequence가 달라도 shared programmer를 보호. operator 간섭은 unknown으로 중단. |
| AC-LDPLUGIN-023 | REQ-LDPLUGIN-023 | D | Given 같은 key 동시 apply와 응답 유실/재시작, When replay, Then execution 하나·추가 write 0·최초 응답 동일. 다른 payload는 IDEMPOTENCY_CONFLICT. 최초 send 이전 DB commit 및 승인 소비 trace. |
| AC-LDPLUGIN-024 | REQ-LDPLUGIN-024 | D+C | Given 첫 실패·socket send 뒤 DB commit 전 crash·applying 재시작, When 회수, Then 후속 not_sent 보존·unknown 우선·recovery_required 및 명확한 failed/partial 구분. blind resend/자동 rollback 0. |
| AC-LDPLUGIN-025 | REQ-LDPLUGIN-025 | D+H+C | Given sent-only·cue 존재 미확인, When receipt 판정, Then unknown+recovery_required이며 applied 아님. 모든 생성 cue 존재 확인 후에도 값/visual/artistic/terminal은 별개. reconciliation은 write 0, recovery는 새 revision/승인만 허용. |
| AC-LDPLUGIN-026 | REQ-LDPLUGIN-026 | D+H | Given pending feedback와 scope별 같은/다른 곡·show·user, When propose→approve→search→revoke→search, Then 승인 관련 범위에서만 검색되고 revoke 즉시 제외. before mismatch/위조 review/충돌 CAS는 거부. |
| AC-LDPLUGIN-027 | REQ-LDPLUGIN-027 | S+D+H | Given design §3의 5주제 seed, When 검색, Then bounded typed rule 절차/case 내용·outcome/feedback 변경 상세가 inline 제공되고 provenance·조건·예외·검토 revision·권리 범위가 남는다. current context 변경 시 cursor stale; 미승인 지식 0. |
| AC-LDPLUGIN-028 | REQ-LDPLUGIN-028 | S+H | Given legacy lighting-designer 설치, When 새 패키지 활성화, Then 두 이름과 역할을 표시하고 사용자 owner 선택 전 중복 orchestration 없음. archive 불변·data script/pycache 미복사·수동 기능 지원 과장 없음. |
| AC-LDPLUGIN-029 | REQ-LDPLUGIN-029 | S+H | Given ChatGPT/다른 adapter 후보, When 별도 transport/auth/tool listing/권한 거부/왕복 인증, Then host·계정·version별 pass/fail과 지원 상태 기록. 미실행 후보는 미인증이며 Claude Code pass로 대체하지 않음. |
| AC-LDPLUGIN-030 | REQ-LDPLUGIN-030 | S+D+H+C+A | Given release 후보, When §3 gate 검토, Then 층별 증거가 분리되고 모든 필수 gate를 충족해야 go. synthetic ready/receipt를 실제 console proof로 인용하지 않음. |
| AC-LDPLUGIN-031 | REQ-LDPLUGIN-031 | D | Given 같은 context와 **동일 fixed LightingPlan**을 external adapter/직접 service contract harness에 주입, When validate/submit, Then plan/context/compiled 의미·진단·권한 결과 동일. model 생성 비교를 이 검사에 섞지 않음. |
| AC-LDPLUGIN-032 | REQ-LDPLUGIN-032 | D+H | Given partial/unknown 후 서비스 중단·코드 rollback, When 운영 runbook 수행, Then 새 apply 차단·credential 철회·journal 보존·명시 recovery 가능. 콘솔 undo/자동 ClearAll/과거 승인 재활성화 없음. |

## 3. Go / no-go gates

| Gate | Go에 필요한 측정값·증거 | No-go |
|---|---|---|
| G0 착수 | 사용자 Implementation Kickoff Approval 및 최종 contract/schema 동결 | 현재 문서 요청을 코드 승인으로 간주 |
| G1 계약·domain | 다섯 fixtures의 schema/hash/ref 일치, negative/semantic/CAS/idempotency/auth 시나리오 전부 통과; critical false-ready 0·무승인 write 0 | schema pass만으로 ready, 누락 진단, silent coercion |
| G2 host+UI | 실제 Claude Code initialize/tools/list→context→validate→submit·revision review·feedback 승인/철회 검색 완주. 앱 동시 실행·정확한 인증 | mock host만 연결, receiver/UI 미연결, plugin-only 완료 |
| G3 onPC fidelity | 기록된 한 compiler build+console build+rig 조합에서 §7 전체 subset 보존. preview 후 별도 human 승인, create-only, 모든 생성 cue existence, 축 timing·FX cycle/phase/stop·quiet ending·MIB 관측. 값 오차는 target 표현 정밀도 이내이며 원래 ms를 그 정밀도로 표현 불가하면 blocking. 측정 장비/화면 시간 분해능도 기록 | per_row_timing/fx_stopped_groups만 보고 지원, sent-only applied, 정확한 시간 mapping 불명, FX 누수, 기존 Sequence 덮어쓰기 |
| G4 실패 안전 | write 전후 crash·동시 writer·stale approval·operator 간섭 시나리오에서 blind resend 0·interleave 0·unknown 공개·새 recovery 승인 | OSC exactly-once/atomic rollback 보장 주장, 불확실 상태 숨김 |
| G5 artistic pilot | 개발 seed에 쓰지 않은 6곡 이상(quiet ending·동일 후렴 의도 포함), 사람 확인 map 고정, 동일 rig/brief의 기존 방식과 새 방식 blind paired review(감독 2인). 의도 보존·음악 대응·전환·공간 사용·실행 가능성 각 1–5점 및 수정시간/수정수/중대 의도위반 기록. 새 방식의 두 평가자 합산 평균이 기존보다 낮지 않고 중대 명시 의도위반 0, 최종 운영 감독이 pilot 채택을 승인 | 표본·기준 없는 전문가급 주장. 비교 평균 저하·중대 의도위반이면 개선 후 재평가; 임의 30% 개선 약속 없음 |
| G6 release | G1–G5 모두 충족·권리 검토·인증 조합/미지원 목록·복구 운영 문서 존재 | 다른 host 미인증을 숨김, 코드 rollback을 콘솔 undo로 설명 |

G5 수치는 출시를 위한 **사전 판정 기준**이지 달성 결과가 아니다. 평가자 불일치와 수정시간 분포를 숨기지 않는다. 자동 음악 분석은 확인 map 평가와 별도 실험하여 어느 단계 오류인지 분리한다.

## 4. parity의 비교 규칙

동일 fixed plan 검사에서 title/concept/rationale/provenance·실제 action 값·순서·timing·refs·hash 입력은 제거하지 않는다. service가 발급한 request/validation/execution ID와 생성 시각은 비교 보고서에서 역할별 대응표로 치환하고, 승인 principal은 동일 시험 principal을 사용한다. digest는 원본 payload 기준으로 먼저 검증하며 정규화해 계산하지 않는다. compiler manifest의 semantic bundle/action/cue/destination mapping은 일치해야 한다. 생성 ID가 artifact bytes를 바꾸는 경우 동일 고정 ID를 주입한 fixture를 사용한다. provider_payload·token usage·호스트 표시 문자열은 wire 바깥이므로 비교 대상이 아니다. 실제 내장 model runtime 비교는 [후속 인수](../SPEC-LDEMBED-001/acceptance.md)에서 수행한다.

## 5. 문서 패키지 검증 기록 — 2026-09-14

이 절은 **문서 산출물 검사**이며 위 구현 AC/G1–G6의 통과 기록이 아니다.

| 수행 | 결과·범위 |
|---|---|
| `moai spec lint .moai/specs/SPEC-LDPLUGIN-001/spec.md` | exit 0, No findings |
| `moai spec lint .moai/specs/SPEC-LDEMBED-001/spec.md` | exit 0, No findings |
| stdin 일회성 검사: `uv run --no-project --with jsonschema --with rfc8785 --with rfc3339-validator python -` | 최종 exit 0. 프로젝트 의존성·production 파일 변경 없이 수행 |
| Draft 2020-12 + format checker | context/plan/validation/feedback/execution 5종 모두 통과 |
| SHA256/JCS | 계약 §9의 합성 raw resource·context·plan·compiled manifest digest와 각 binding 일치 |
| 합성 시나리오 | 16 cue·60 action·4 FX active interval. first baseline, terminal assertion, 구간 소속·시간 오름차순·종료시각, 그룹/축 transition 및 FX 충돌, tempo segment 내 FX, 최종 cue-number/relative trigger mapping 일치 |
| 참조 | source/evidence/group/preset/section/action/cue/bundle ID, diagnostic pointer·feedback before값, pending feedback와 sent-only unknown receipt 일치 |
| negative 7종 | unknown field, 버전 불일치, null title, intensity 101, timecode mode, destination 누락, 존재하지 않는 UTC 날짜를 schema/format 단계에서 거부 |
| negative 4종 | FX stop 누락, terminal 값 불일치, cue 동시시각, 미존재 preset을 일회성 의미 검사에서 거부 |
| 문서 추적 | LDPLUGIN 32개·LDEMBED 16개 REQ가 각 AC와 1:1 대응. 두 폴더의 Markdown 상대 링크 대상 존재 |

검사 중 `jsonschema` 기본 설치만으로는 date-time checker가 등록되지 않아 `2026-02-30T00:00:00Z`가 거부되지 않았다. `rfc3339-validator`를 검사 환경에 추가하고 checker 등록 자체를 assert한 뒤 전체 검사가 통과했다. 구현도 format annotation을 쓰는 것만으로 날짜를 검증했다고 간주하지 말고 이 음성 대조군을 반드시 포함한다.

초기 독립 설계/계약 검토에서 제기한 shared programmer 중재·principal/출처 신뢰·legacy migration·destination/playback·앱 읽기 권한·지식 상세·sent-only 완료 판정 문제를 통합했다. 마지막 두 문서 전용 재검토 에이전트 호출은 실행기 오류로 결과를 반환하지 못했다. 위 최종 결과는 통합 담당자의 직접 문서 검토와 실행한 검사 결과이며, **최종 독립 재검토 통과로 표시하지 않는다.**

검사기는 stdin에서만 실행했고 저장소에 임시 script를 남기지 않았다. 새 API·MCP 서버·플러그인 설치·provider 호출·onPC·readback·시각적/예술적 검증·전체 프로젝트 테스트는 수행하지 않았다. release/implementation 상태는 계속 draft이며 kickoff 승인이 필요하다.
