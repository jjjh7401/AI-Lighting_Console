---
id: SPEC-LDEMBED-001
title: "동일 Lighting Director의 copilot 내장 호스트와 기존 producer cutover"
version: "0.1.0"
status: draft
created: 2026-09-13
updated: 2026-09-13
author: jaihyun
priority: P1
phase: "Lighting Director v1.1 embedded-host target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, embedded-host, provider-adapter, contract-parity, cutover"
tier: M
depends_on: [SPEC-LDPLUGIN-001]
---

# SPEC-LDEMBED-001

## 1. 독립 프로젝트의 목적

첫 외부 플러그인 릴리스에서 실증한 **동일 skills·knowledge·DirectorService·wire 계약**을 copilot 안에서 호출한다. 기존 `LLMProvider` adapter와 설정된 단일 활성 provider를 사용하고, 별도 필수 모델이나 제3의 예술 policy engine을 도입하지 않는다. 외부 `lighting-director`는 계속 지원한다.

이 SPEC은 [SPEC-LDPLUGIN-001](../SPEC-LDPLUGIN-001/spec.md)에 의존하는 후속 프로젝트다. 선행의 end-to-end·compiler fidelity·실제 director pilot gate를 통과하기 전에는 내장 전환을 출시하지 않는다. **문서 작성만 요청되었고 Implementation Kickoff Approval은 아직 없다.** 현재 내장 runtime 구현/호스트 parity/예술 품질 통과를 주장하지 않는다.

| 원본 | 적용 |
|---|---|
| [contract.md](../SPEC-LDPLUGIN-001/contract.md), [schema](../SPEC-LDPLUGIN-001/schemas/exchange.schema.json) | 도구·객체·state·권한·playback·destination·hash의 단일 원본; 내장 전용 wire 분기 없음 |
| [선행 design §2–3](../SPEC-LDPLUGIN-001/design.md) | 네 skill procedure, 일곱 command 의미, knowledge seed·scope |
| [plan.md](plan.md) | provider tool loop·checkpoint·UI routing·producer 치환 build order |
| [acceptance.md](acceptance.md) | 요구사항별 증거와 fixed-plan parity·stochastic 생성 평가 분리 |
| [research.md](research.md) | 기존 provider/UI/producer 근거와 제한 |

## 2. 요구사항

| ID | 패턴·필수 동작 |
|---|---|
| REQ-LDEMBED-001 | **When** 내장 host를 출시하면 팀은 **SHALL** 선행 SPEC의 end-to-end·전체 필수 expressive subset·onPC/감독 pilot 증거를 entry gate로 확인하고 plugin-only 또는 synthetic-only 상태에서는 전환하지 않는다. |
| REQ-LDEMBED-002 | The embedded host **SHALL** 선행 패키지의 versioned 네 skill 절차와 동일 knowledge/DirectorService를 재사용하고 호스트별 예술 규칙·별도 wire shape·제3 policy engine을 만들지 않는다. |
| REQ-LDEMBED-003 | **When** model을 호출하면 runtime은 **SHALL** 기존 LLMProvider.complete·ToolDefinition/ToolCall/ToolResult/ModelTurn 및 활성 provider 설정을 사용하고 임의 새 모델을 필수로 강제하지 않는다. |
| REQ-LDEMBED-004 | **When** model이 tool call을 반환하면 runtime은 **SHALL** 계약의 일곱 ld_* tool을 allowlist·closed argument validation·principal ACL로 dispatch하고 correlated ToolResultsMessage로 결과를 돌려주며 raw/approve/apply 호출을 거부한다. |
| REQ-LDEMBED-005 | **While** 내장 run이 진행되면 runtime은 **SHALL** 사용자에게 현재 절차·도구·draft·오류를 표시하고 run별 12 model turn·32 tool call·provider context 한도의 75% input budget에서 pause하여 무한 self-repair를 막는다. |
| REQ-LDEMBED-006 | **When** 사용자가 취소하거나 provider가 timeout/오류로 끝나면 runtime은 **SHALL** 추가 model/tool dispatch를 중단하고 durable checkpoint를 남기며 진행 중 mutation의 결과를 read로 확인하기 전 재전송하지 않는다. |
| REQ-LDEMBED-007 | **When** restart/resume을 요청하면 runtime은 **SHALL** 같은 principal/project의 checkpoint와 committed tool 결과를 복구하고 context/head/version freshness를 재확인하며 stale 승인·모델의 미완성 출력을 재사용해 실행하지 않는다. |
| REQ-LDEMBED-008 | The context builder **SHALL** brief·확인된 music/context·immutable plan refs·scoped approved knowledge·수정 history를 앱 저장소에서 재구성하고 외부 host의 숨은 채팅 내용·audio bytes·secret에 의존하지 않는다. |
| REQ-LDEMBED-009 | **When** 사용자가 앱에서 곡 설계/수정/learn/status를 요청하면 UI는 **SHALL** 동일 procedure로 라우팅하고 연결된 draft/review/receipt/feedback을 보여주며 일반 console chat 요청과 director run을 명확히 구분한다. |
| REQ-LDEMBED-010 | **When** 내장 draft를 승인·적용하면 시스템은 **SHALL** 선행 human-only 승인·exact digest·create-only destination·shared writer lock·LiveLock·journal/recovery 경계를 유지하고 model completion·대화의 승인 문구를 실행 권한으로 쓰지 않는다. |
| REQ-LDEMBED-011 | **When** old producer에서 cutover하면 구현은 **SHALL** `server/web/session.py::_build_unified_song_plan`의 예술 policy 생산과 `server/looks/songcue.py::map_sections_to_looks`의 예술 매핑 생산을 동일 Director orchestration으로 치환하고 모든 호출부에서 두 중복 정책 경로를 제거한다. |
| REQ-LDEMBED-012 | **While** 외부 플러그인과 내장 host가 공존하면 서비스는 **SHALL** 같은 canonical store·CAS·knowledge·capability를 제공하고 orchestration owner를 사용자에게 표시하며 동시 제출 충돌을 silent overwrite하지 않는다. |
| REQ-LDEMBED-013 | **When** 동일 fixed plan/context를 외부·내부 경계에 주입하면 서비스는 **SHALL** 동일 semantic validation·compiled artifact 의미·state/권한 결과를 보장하고 ID/시각 정규화와 실제 원본 hash 검증을 구분한다. |
| REQ-LDEMBED-014 | **When** 모델 생성 결과의 품질을 비교하면 평가자는 **SHALL** 동일 prompt/근거/skill version을 고정하되 stochastic 결과의 byte 일치를 요구하지 않고 명시 의도·fidelity·paired review·수정시간을 별도 평가한다. |
| REQ-LDEMBED-015 | **When** 내장 run이 피드백을 생성/조회하면 runtime은 **SHALL** pending proposal만 만들고 approved/non-revoked·scope·ACL을 service에서 적용하며 기억 요약으로 revoked 근거를 되살리지 않는다. |
| REQ-LDEMBED-016 | **When** embedded rollout을 중단·되돌리면 운영자는 **SHALL** 새 run/신규 apply를 차단하고 외부 plugin 경로와 durable 기록을 보존하며 이미 보낸 OSC를 되돌렸다고 주장하지 않는다. |

## 3. 비목표

### Out of Scope — 새 판단 엔진·자동 라이브 실행
- 새 필수 모델, 복수 모델 동시 라우팅, 학습 가중치 변경, 별도 내장용 예술 규칙, 무제한 자가 개선은 포함하지 않는다.
- model tool loop는 approval/apply/GO/timecode start를 실행하지 않는다. 사람이 앱에서 programming을 승인하며 playback은 계약대로 별도 operator action이다.

### Out of Scope — 선행 구현 누락의 전가
- 선행의 FX stop·축 timing·receiver/UI·approved apply·feedback 왕복을 이 프로젝트로 미루지 않는다.
- 외부 플러그인 폐기, 역사적 SPEC lifecycle 수정, legacy `.plugin` archive 수정은 포함하지 않는다.
