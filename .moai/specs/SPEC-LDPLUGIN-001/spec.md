---
id: SPEC-LDPLUGIN-001
title: "Lighting Director 외부 플러그인과 copilot 수신·검토·실행 왕복"
version: "0.1.0"
status: in-progress
created: 2026-09-13
updated: 2026-09-15
author: jaihyun
priority: P1
phase: "Lighting Director v1.0 end-to-end target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, skills, mcp, receiver, human-approval, fidelity"
tier: L
---

# SPEC-LDPLUGIN-001

## 1. 목적과 승인 경계

음악 근거를 확인하고 전곡 의도·큐·효과 종료까지 설계하는 `lighting-director`를 외부 호스트에서 사용하며, 실행 중인 copilot이 계획 원본 수신, 검증, 사람 검토·승인, programming/storing, 피드백 승인을 담당한다. **플러그인만 전달하는 릴리스가 아니라 host→draft→review→approved apply→feedback 왕복이 첫 릴리스다.**

이 문서는 구현을 요청하기 위한 draft다. 문서 작성만 요청되었으며 **Implementation Kickoff Approval은 아직 부여되지 않았다.** 신규 서비스/API/도구·호스트 연결·콘솔 결과·전문가급 연출 품질을 구현되거나 검증된 것으로 표시하지 않는다.

계약 review의 destination/create-only binding, `plan.playback`, inline 지식 상세·current context 결합, human 공통 read/validate/submit·inbox/feedback 조회, cue 존재 확인 후 applied 판정은 contract/schema에 반영했다. 정확한 wire shape의 소유권은 계약에 있다.
| 규범 | 위치 |
|---|---|
| wire shape·tool·HTTP·state·hash·의미 규칙의 단일 원본 | [contract.md](contract.md), [JSON Schema](schemas/exchange.schema.json) |
| 컴포넌트·절차·지식·저장·UI 결정 | [design.md](design.md) |
| 구현 순서·파일 소유권·출시 | [plan.md](plan.md) |
| 요구사항별 증거·go/no-go | [acceptance.md](acceptance.md) |
| 현재 코드 근거·한계 | [research.md](research.md) |
| 동일 Director를 앱에 내장하는 독립 후속 | [SPEC-LDEMBED-001](../SPEC-LDEMBED-001/spec.md) |

## 2. 범위 결정

- 최초 지원 호스트는 **Claude Code**다. stdio MCP adapter는 인증된 `/api/director/v1` HTTP를 호출하며 copilot만 기존 ConsoleLink/OSC를 소유한다. 앱과 플러그인이 동시 실행된다.
- `SPEC-COPILOT-MCP-001`의 S2/REQ-MCP-009 배타 포트·앱 종료 전제는 **이번 범위에서 새 공존 결정으로 대체**한다. 역사적 draft 파일이나 lifecycle은 변경하지 않으며 종속 구현으로 취급하지 않는다.
- 외부 `LightingPlan`은 canonical 원본이다. `UnifiedSongLightingPlan`/`SectionDecision`은 내부 재사용 지점이지 무손실 wire 별칭이 아니다. 기존 timeline은 읽기 projection이며 직접 계획 intake가 아니다.
- 명시적 선택을 finale 상승·후렴 변주·기본 BPM 등의 고정 예술 정책으로 덮어쓰지 않는다. 안전 hard constraint는 유지하고 연출 조언은 advisory로만 표시한다.
- first release 표현 범위는 계약 §7 전체다. 알려진 intensity/color/position/beam, FX start/stop·cycle/phase, 독립 축별 fade/delay, accent 복귀, release, baseline/terminal state, MIB·re-entry의 fidelity까지 구현한다. 불가능한 rig는 차단하되 구현 누락을 영구 unsupported로 남겨 릴리스 범위를 축소하지 않는다.

## 3. 안정 요구사항

`SHALL`은 필수다. 아래 ID는 구현 파일 이동과 무관하게 유지하며 AC 번호와 1:1 대응한다. 데이터 필드·enum을 재정의하지 않고 계약 조항을 참조한다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDPLUGIN-001 | The system **SHALL** 외부 플러그인·receiver·UI·approved apply·승인 피드백 검색 왕복 전체를 한 릴리스로 제공하고 단독 플러그인을 완료로 표시하지 않는다. | 계약 §1, §11 |
| REQ-LDPLUGIN-002 | **While** 앱과 Claude Code가 동시에 실행 중이면 adapter는 **SHALL** stdio→인증 HTTP만 사용하고 OSC/두 번째 ConsoleLink/별도 판단 LLM을 생성하지 않는다. | 계약 §1 |
| REQ-LDPLUGIN-003 | **When** 사용자가 연출 절차를 요청하면 패키지는 **SHALL** design §2의 4개 skill과 7개 command를 같은 절차 정의로 실행하고 입력·출력·실패 경계를 유지한다. | 계약 §1; design §2 |
| REQ-LDPLUGIN-004 | **When** context를 요청하면 서비스는 **SHALL** audio·show·group membership·preset 내용·compiler·capability·정책·identity·만료를 묶은 server-owned ContextSnapshot을 반환한다. | LD-CTX-001, LD-HASH-001 |
| REQ-LDPLUGIN-005 | **When** 음악 근거가 부족하면 skill은 **SHALL** unknown/confidence와 근거 범위를 보존하고 앱에서 업로드·사람 확인을 요청하며 청취·tempo를 지어내지 않는다. | 계약 §6.1; LD-TIME-002 |
| REQ-LDPLUGIN-006 | The director **SHALL** 전곡 concept/global motif/ending intent, 음악 구간과 독립적인 조명 의도, 반복 motif, cue별 rationale·provenance를 작성하고 동일 후렴 강도와 quiet ending을 허용한다. | 계약 §6.2; LD-STATE-002 |
| REQ-LDPLUGIN-007 | **When** 교환 객체를 수신하면 서비스는 **SHALL** 다섯 message_type, exact version, closed schema, 유한 수·UTC 시각·상한·ID/ref를 검사하고 unknown field/version을 거부한다. | 계약 §2, §5; LD-REF-001 |
| REQ-LDPLUGIN-008 | **When** typed action을 검증·컴파일하면 서비스는 **SHALL** 계약 §7 전체 expressive subset을 보존하며 임의 MA/Lua/OSC 문자열, clamp·quantize·대체 preset을 허용하지 않는다. | LD-CAP-001 |
| REQ-LDPLUGIN-009 | **When** cue/FX 시간을 해석하면 compiler는 **SHALL** 원음 첫 sample=0ms, 전곡 분할, 동일 시각 semantic cue, 독립 축 timing, confirmed beat 연속성·반올림·tempo 분할과 `playback`의 manual_go/trig_time·operator_go 의미를 보존한다. trig_time은 준비 cue를 포함한 최종 cue 순서의 delta를 저장하며 timecode event mapping은 지원하지 않는다. | LD-TIME-001/002; design §1 |
| REQ-LDPLUGIN-010 | **When** ready를 판정하면 validator는 **SHALL** omission=hold, 첫 full baseline·clean FX, explicit off/stop/release, 전 그룹 terminal assertion을 simulation으로 확인한다. | LD-STATE-001/002, LD-FX-001 |
| REQ-LDPLUGIN-011 | **When** 겹친 group/FX/transition이 있으면 validator는 **SHALL** 실제 fixture×axis로 충돌을 검출하고 순서 덮어쓰기나 누락으로 해결하지 않는다. | LD-CONFLICT-001 |
| REQ-LDPLUGIN-012 | **When** dark_move 또는 임의 시점 re-entry를 요청하면 compiler는 **SHALL** blackout·settle·full state·중간 fade·FX phase 복원을 증명하거나 blocking을 반환하고 authored reveal을 미루지 않는다. | LD-MIB-001, LD-REENTRY-001 |
| REQ-LDPLUGIN-013 | The capability service **SHALL** 실제 compiler+rig+target 출력으로 지원을 광고하며 기존 LXSEQ timing/FX stop/rate 메타데이터 갭을 plan §3의 실제 emitter 구현·관측으로 해소한다. | LD-CAP-001; plan §3 |
| REQ-LDPLUGIN-014 | **When** 검증하면 서비스는 **SHALL** source→time/ref→tracking/FX→fidelity→safety→freshness 순으로 전 계획을 검사하고 action/leaf JSON Pointer·before/after·이유로 진단하며 하나라도 critical blocking이면 compiled.available=false로 한다. | LD-VAL-001 |
| REQ-LDPLUGIN-015 | **When** 제출·갱신하면 저장소는 **SHALL** immutable plan/revision, base_revision=expected_revision CAS, server digest·state 연결을 SQLite transaction으로 기록하고 timeline JSON을 원본으로 사용하지 않는다. | 계약 §9–10 |
| REQ-LDPLUGIN-016 | **When** 사용자가 검토하면 UI는 **SHALL** 원본 의도·구간/큐·field 변경/누락·capability·근거·stale·승인 대상 digest를 표시하고 projection edit/load로 원본이나 승인을 덮어쓰지 않는다. | 계약 §1, §6.3; design §4 |
| REQ-LDPLUGIN-017 | **When** MCP가 initialize/tools/list 또는 domain call을 수행하면 adapter는 **SHALL** 계약 §3의 정확한 7 tool·schema·structuredContent·isError·HTTP 오류 매핑만 제공한다. | 계약 §3, §5 |
| REQ-LDPLUGIN-018 | **When** pairing/요청이 발생하면 서버는 **SHALL** audience·scope·principal/project/session ACL·Host/Origin·만료/철회·CSRF를 검증하고 secret을 OS credential store 밖의 package/log/model context에 넣지 않는다. 공통 read/validate/submit은 human 자체 credential도 허용하되 MCP credential을 차용하지 않는다. | LD-AUTH-001/002/003 |
| REQ-LDPLUGIN-019 | **While** 외부 evidence/지식을 소비하면 서비스는 **SHALL** 텍스트 지시문·origin·actor_ref를 권한으로 신뢰하지 않고 immutable 서버 근거를 역참조하며 audio의 외부 전송은 앱 명시 동의로 제한한다. | LD-AUTH-003/004 |
| REQ-LDPLUGIN-020 | **When** 승인·거절을 요청하면 서버는 **SHALL** human APP route만 허용하고 exact revision/세 digest/principal/target/policy/만료를 묶으며 일반 chat/WS boolean이나 MCP로 승인을 생성하지 않는다. | LD-APPROVAL-001; 계약 §4 |
| REQ-LDPLUGIN-021 | **When** apply를 요청하면 서버는 **SHALL** lock 안에서 첫 write 직전 current bindings·target/destination occupancy·LiveLock·승인을 다시 검사하고 exact artifact에 승인 bridge를 연결하되 SafetyGate의 문법/위험/백업/health/audit를 우회하지 않는다. destination은 server-selected 새 Sequence create-only이며 overwrite·silent reselection은 금지한다. | LD-SAFE-001, LD-APPROVAL-001 |
| REQ-LDPLUGIN-022 | **While** programming bundle을 적용하면 서버는 **SHALL** director/chat/import 등 모든 shared programmer mutation을 하나의 중재자로 직렬화하고 충돌 요청을 TARGET_BUSY로 거부한다. | LD-EXEC-001 |
| REQ-LDPLUGIN-023 | **When** mutation/idempotent replay가 발생하면 서버는 **SHALL** 첫 write 전에 승인 소비·execution·bundle journal·fingerprint를 durable 저장하고 동일 요청을 최초 응답으로 replay하며 다른 payload를 409로 거부한다. | 계약 §9–10; LD-EXEC-001 |
| REQ-LDPLUGIN-024 | **When** 실패·간섭·crash·불확실 전송이 발생하면 실행기는 **SHALL** 후속 bundle을 중단하고 partial/unknown/failed를 구분하며 blind retry나 atomic OSC rollback을 주장하지 않는다. | LD-EXEC-002; 계약 §10 |
| REQ-LDPLUGIN-025 | **When** 실행 결과·recovery를 조회하면 UI/서비스는 **SHALL** transport/object/readback/visual/artistic/terminal 관측을 분리하고 모든 생성 cue 존재 확인 후에만 applied로 판정한다. sent-only는 unknown+recovery_required이며 reconciliation 뒤 새 revision·새 human approval로만 recovery를 실행한다. | 계약 §4, §6.5, §10 |
| REQ-LDPLUGIN-026 | **When** learn 또는 수정 피드백을 요청하면 서비스는 **SHALL** immutable plan의 before/after·rationale·scope·evidence를 가진 pending 제안만 만들고 승인/철회 CAS 후 approved·non-revoked·ACL·관련 scope만 검색한다. | LD-FEEDBACK-001 |
| REQ-LDPLUGIN-027 | The knowledge service **SHALL** design §3의 검토된 rule/case seed를 provenance·조건·예외·저작권 범위와 bounded inline typed details로 제공하고 page/cursor를 current context에 결합한다. 사례·retrieval memory를 강제 법칙이나 weight training으로 표시하지 않는다. | 계약 §3, §6.4 |
| REQ-LDPLUGIN-028 | **When** legacy lighting-designer를 함께 발견하면 설치 흐름은 **SHALL** design §6 migration matrix와 단일 orchestration owner 선택을 적용하고 archive·dataset script·pycache를 새 director 실행 엔진으로 복사하지 않는다. | 계약 §1 |
| REQ-LDPLUGIN-029 | **When** ChatGPT 등 다른 host adapter를 제공하면 배포자는 **SHALL** 동일 계약 위 transport/auth/capability/권한 거부를 개별 인증하고 미시험 호스트를 자동 호환·출시 완료로 표시하지 않는다. | 계약 §1; acceptance §3 |
| REQ-LDPLUGIN-030 | **When** first-release 후보를 평가하면 팀은 **SHALL** schema/static, synthetic semantic, 실제 host smoke, human-authorized onPC fidelity/visual/readback, 예술 pilot을 별도 증거와 go/no-go로 판정한다. | LD-SYN-001; acceptance §3 |
| REQ-LDPLUGIN-031 | **When** 동일 fixed plan을 다른 host 경계로 전달하면 서비스는 **SHALL** 동일 validation·compiled 의미·권한 결과를 내고 model의 확률적 새 생성과 계약 parity를 분리한다. | 계약 §11; acceptance AC-LDPLUGIN-031 |
| REQ-LDPLUGIN-032 | **When** release/운영 중단을 결정하면 운영 흐름은 **SHALL** 인증 철회·신규 apply 차단·journal 보존·명시 recovery를 제공하고 앱 코드 rollback을 console write undo로 표시하지 않는다. | 계약 §10; plan §5 |

## 4. 비목표

### Out of Scope — 무제한 조명 생성·자동 라이브 실행
- 임의 Phaser 제작, 미등록 preset·raw console code, GO/playback/timecode arm/start, 전 기종·전 콘솔 기능의 포괄 지원은 포함하지 않는다.
- 고급 자동 음악 의미 분석 모델, 새 필수 모델·가중치 학습, 감독을 대체한다는 품질 보장, 출처 없는 음악 청취 주장은 포함하지 않는다.

### Out of Scope — 원격 공개 서비스·역사 수정
- 공개 cloud MCP/TLS 인프라와 무시험 ChatGPT 배포, 개발용 `.mcp.json` 변경, 기존 SPEC lifecycle 변경, legacy archive 재패키징은 포함하지 않는다.
- 앱 내부 director runtime과 두 기존 예술 producer의 전면 cutover는 후속 SPEC이다. 이 릴리스에서 외부 plan 경로에는 그 producer를 적용하지 않는다.
