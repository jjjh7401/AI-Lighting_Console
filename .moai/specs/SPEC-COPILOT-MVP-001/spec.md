---
id: SPEC-COPILOT-MVP-001
title: "Phase 1: 자체 MVP — OSC/Lua 브리지 + 한국어 채팅 UI + 안전 게이트"
version: "0.3.0"
status: draft
created: 2026-07-15
updated: 2026-07-16
author: manager-spec
priority: P1
phase: "Phase 1 — MVP 코파일럿 (v0.2.0 target)"
module: "server/, console/lua/, ui/"
lifecycle: spec-anchored
tags: "osc, lua, anthropic, gemini, multi-provider, tool-runner, fastapi, websocket, safety-gate, korean-ui, prompt-caching, mvp"
tier: L
depends_on: [SPEC-COPILOT-EVAL-001]
---

# SPEC-COPILOT-MVP-001 — Phase 1: 자체 MVP (OSC/Lua 브리지 + 한국어 채팅 UI + 안전 게이트)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.3.0 | 2026-07-16 | manager-spec | §F 격차 fold-in amendment (EVAL 완료 산출물 반영): 반영 격차 11건 disposition 기록(plan.md §F.4 — 기존 커버 8건 추적성 주석 + 신규 3건) — §B.13 신설(REQ-MVP-042 한국어 용어 사전 축 / REQ-MVP-043 크로스플랫폼·오픈 설치 / REQ-MVP-044 오류 표면 정제) + AC-MVP-028~031 신설. AD2-m1 라이더 흡수: REQ-MVP-040(ii) 지속 미충족 감지 규칙을 설정 정의 운영 파라미터로 확정(기본 N=20/M=2). MA3 세부 버전 핀 유입: grandMA3 onPC 2.4.2 (plan.md §A-2). design.md/research.md 사실 불일치 없음(무변경). 영향 REQ: 040, 042~044 |
| 0.1.0 | 2026-07-15 | manager-spec | 최초 작성 (draft) |
| 0.2.1 | 2026-07-15 | manager-spec | amendment delta re-audit 지적 반영: REQ-MVP-040 선정 술어 정련(AC-002 AND AC-003 동시 통과 = eligible, fallback 규칙, 비용 산정 기준 — AM-M1), REQ-MVP-041 측정-조건 의미 명확화(AM-M2c), §A "LLM 추상화 계층 기반 도구 실행 서버" 표기(AM-m1). 영향 REQ: 040, 041 |
| 0.2.0 | 2026-07-15 | manager-spec | 정식 amendment — LLM 프로바이더 전략(멀티 프로바이더 추상화, 사용자 결정 2026-07-15) + 지연 정합 해소: §B.12 신설(REQ-MVP-038~041 — 추상화 계층, Claude+Gemini 설정 전환, 오류율 기반 기본 프로바이더 선정, 프로바이더별 캐싱), REQ-MVP-006 단일-활성-프로바이더로 개정, REQ-MVP-007 캐싱 조건 교차 참조, REQ-MVP-001 `/cmd` → `/copilot/cmd` 정식 반영, Out of Scope 멀티 모델 항목 경계 재정의. 영향 REQ: 001, 006, 007, 038~041 |
| 0.1.3 | 2026-07-15 | manager-spec | clarification gate 해소: plan.md §A 마커 6건 전원 결정 기록으로 대체 (React, Phase 0 버전 승계, 코퍼스 기본값 승인, JSONL 감사 로그 90일, `/copilot/*` OSC 네임스페이스, 왕복 조작적 정의 승인) + acceptance DoD 마커 카운트 정정(m10). 참고: REQ-MVP-001의 `/cmd` → `/copilot/cmd` 정식 개정은 §F fold-in amendment에서 수행 |
| 0.1.2 | 2026-07-15 | manager-spec | plan-audit iteration 2 (PASS-with-debt 0.92) 지적 반영: invoking_verbs 폐쇄 집합화 + 재귀 상한·순환 감지(MVP-M9), Cmd() 스캔 잔여 위험 명시(m5), GEARS 태그 표준화(m6), 왕복 조작적 정의 축소 해석 명시(m7), AC-MVP-024 결정적 재작업(m9) |
| 0.1.1 | 2026-07-15 | manager-spec | plan-audit iteration 1 (FAIL 0.59) 지적 반영: 안전 게이트 우회 봉쇄(B.8, MVP-C1), 장애 모드·부분 실행(B.9, MVP-M4), 블랙리스트 폐쇄 집합화(MVP-M1), 백업 정책 재정의(MVP-M5), 왕복 측정 기준 재정의(MVP-M3), 엣지 케이스 REQ 승격(B.10, MVP-m3), get_rig_context 행위 요구(B.11, MVP-M7), Tier L 산출물(design.md/research.md) 추가(MVP-M6) |

## A. 개요

본 SPEC은 grandMA3 AI 코파일럿의 **Phase 1 MVP**를 정의한다. 사용자의 한국어 자연어 지시를 grandMA3 커맨드/Lua 플러그인으로 변환·실행하고, 콘솔 상태를 읽어 피드백 루프를 도는 자체 구현 시스템이다. 구성 요소: OSC 브리지, Lua 5.4 responder 플러그인, LLM 추상화 계층 기반 도구 실행 서버, 3단계 안전 게이트, 한국어 채팅 UI.

**사전 확정 사실 (재질의 금지):**
- LLM 전략 (2026-07-15 amendment): **멀티 프로바이더 추상화** — Anthropic Claude(기본 후보 `claude-opus-4-8`) + Google Gemini, 설정 파일로 전환(코드 변경 없음). 기본 프로바이더는 문법 오류율 측정 결과로 결정한다 (§B.12). 활성 구성은 항상 단일 프로바이더·단일 모델.
- 통신: OSC 브리지 — 자체 네임스페이스 `/copilot/*` 채택(2026-07-15 결정), 명령 송신 `/copilot/cmd`(UDP), 콘솔측 Lua responder가 상태 스냅샷·실행 결과 회수 담당.
- UI: 한국어 채팅 웹 UI.
- 안전 게이트는 **필수**: 블랙리스트 명령은 인간 승인 없이는 절대 실행 불가, 라이브 잠금 모드는 read-only.
- boardop 코드는 재사용하지 않는다 (아키텍처 벤치마킹만, FSL-1.1 제약).

## B. 요구사항 (GEARS)

### B.1 OSC 브리지

- **REQ-MVP-001** [Event-driven] — **When** 안전 게이트를 통과한 명령 시퀀스의 실행이 요청되면, the OSC 브리지 **shall** 각 명령을 OSC 주소 `/copilot/cmd`로 UDP 전송한다 (자체 네임스페이스 `/copilot/*` — 2026-07-15 결정, boardop 비호환 의도적).
- **REQ-MVP-002** [Event-driven] — **When** 콘솔로부터 OSC 피드백 메시지가 수신되면, the OSC 브리지 **shall** 이를 실행 결과 확인 경로로 전달한다.

### B.2 Lua responder (콘솔측)

- **REQ-MVP-003** [Event-driven] — **When** 상태 조회 요청이 도착하면, the Lua responder **shall** 지정된 콘솔 오브젝트 트리 경로(예: DataPool/Sequences)의 상태 스냅샷을 반환한다.
- **REQ-MVP-004** [Event-driven] — **When** 명령 실행이 완료되면, the Lua responder **shall** 실행 결과(성공 여부·오류 메시지)를 서버가 회수할 수 있도록 제공한다.

### B.3 AI 오케스트레이터 (tool-runner 서버)

- **REQ-MVP-005** [Ubiquitous] — The AI 오케스트레이터 **shall** `run_commands`, `query_state`, `deploy_plugin`, `get_rig_context` 4종 도구를 제공한다.
- **REQ-MVP-006** [Ubiquitous] — The AI 오케스트레이터 **shall** 단일 활성 프로바이더·단일 모델 구성으로 동작한다 — Anthropic 선택 시 `claude-opus-4-8`, Google Gemini 선택 시 설정 파일에 핀된 Gemini 모델. 활성 프로바이더는 REQ-MVP-039의 설정으로 선택되며, 동시 다중 모델 라우팅은 Out of Scope를 유지한다 (2026-07-15 amendment).
- **REQ-MVP-007** [Ubiquitous] — The 시스템 프롬프트 **shall** MA3 문법 룰북(+오브젝트 모델 요약)을 고정 프리픽스로 포함하고 프롬프트 캐싱을 적용한다 (프로바이더별 캐싱 적용 조건은 REQ-MVP-041).
- **REQ-MVP-008** [Unwanted] — The 룰북 고정 프리픽스 **shall not** 타임스탬프·세션 ID 등 턴마다 변하는 값을 포함한다 (캐시 무효화 방지).
- **REQ-MVP-009** [Event-driven] — **When** 콘솔이 명령 실행 오류를 반환하면, the 오케스트레이터 **shall** 오류 내용을 모델에 회신하여 자가 수정을 시도한다.
- **REQ-MVP-010** [Unwanted] — The 자가 수정 루프 **shall not** 동일 지시에 대해 재시도를 3회 초과하여 수행한다 (상한 도달 시 사용자에게 실패 보고).

### B.4 안전 게이트 (3단계) + 감사

- **REQ-MVP-011** [Event-driven] — **When** 모델이 명령 시퀀스를 생성하면, the 안전 게이트 **shall** ① 문법 밸리데이터 → ② 위험 분류(블랙리스트) → ③ (위험 시) 인간 승인의 순서로 검사를 통과한 명령만 실행 경로로 전달한다.
- **REQ-MVP-012** [Event-driven] — **When** 문법 밸리데이터가 파싱 불가 명령을 감지하면, the 안전 게이트 **shall** 해당 명령의 실행을 차단하고 차단 사유를 자가 수정 루프로 회신한다.
- **REQ-MVP-013** [Event-driven] — **When** 블랙리스트 명령이 감지되면, the 안전 게이트 **shall** 인간 승인 결정이 도착할 때까지 실행을 보류한다. 블랙리스트는 버전 관리되는 열거형 설정 파일(단일 SSOT)로 정의되는 **폐쇄 집합**이며, 초기 집합은 정확히 다음 6종이다: `Delete`, `Remove`, `Off Everything`, `Store /overwrite`, `Shutdown`, `Format`. 집합의 변경은 설정 파일 개정으로만 허용된다 (열린 목록 표기 금지).
- **REQ-MVP-014** [Unwanted] — The 시스템 **shall not** 인간 승인 없이 블랙리스트 명령을 실행한다. (어떤 경로로도 예외 없음)
- **REQ-MVP-015** [Event-driven] — **When** 승인 대상 번들(다중 명령) 중 어느 하나라도 거부되면, the 안전 게이트 **shall** 번들 전체를 미실행 처리한다 (all-or-nothing).
- **REQ-MVP-016** [State-driven] — **While** 라이브 잠금 모드가 활성인 동안, the 시스템 **shall** 콘솔에 어떤 명령도 전송하지 않고(read-only) 제안 카드만 생성한다.
- **REQ-MVP-017** [Ubiquitous] — The 시스템 **shall** 다음 규칙으로 쇼파일 백업을 수행한다: ① 세션 시작 시 1회, ② 주기적 백업(기본 10분 간격, 설정 가능), ③ 인간 승인 대상(위험) 명령의 실행 직전 1회 추가 백업. 비위험 명령의 실행 경로에는 백업이 개입하지 않는다 (왕복 시간 예산 REQ-MVP-025와의 충돌 제거).
- **REQ-MVP-018** [Ubiquitous] — The 감사 로그 **shall** 모든 실행 명령·승인·거부·차단 이벤트를 타임스탬프와 함께 기록한다.

### B.5 Lua 플러그인 배포

- **REQ-MVP-019** [Event-driven] — **When** Lua 플러그인 배포가 요청되면, the 시스템 **shall** pcall 컴파일 검증과 인간 리뷰 게이트를 모두 통과한 경우에만 배포를 수행한다.

### B.6 한국어 채팅 UI

- **REQ-MVP-020** [Ubiquitous] — The 채팅 UI **shall** 한국어 자연어 입출력을 지원하고 WebSocket으로 서버와 실시간 통신한다.
- **REQ-MVP-021** [Event-driven] — **When** 승인 대기 명령이 발생하면, the UI **shall** 대상 명령과 위험 사유를 표시하는 승인/거부 인터페이스를 제공하고, 사용자 결정을 안전 게이트로 전달한다.
- **REQ-MVP-022** [Event-driven] — **When** 명령 실행이 완료되거나 실패하면, the UI **shall** 결과를 한국어로 사용자에게 보고한다.

### B.7 성능·품질 (비기능)

- **REQ-MVP-023** [Ubiquitous] — The 시스템 **shall** 대표 프로그래밍 작업 10종(그룹 생성, 프리셋 저장, 큐 스토어, 시퀀스→executor 할당, 페이지 셋업, 매크로 생성, 이펙트 적용, 페이더 제어, 상태 조회, Lua 플러그인 배포)을 한국어 자연어 지시로 수행할 수 있어야 한다.
- **REQ-MVP-024** [Ubiquitous] — The 시스템이 생성하는 명령의 문법 오류율 **shall** 5% 미만이어야 한다 (측정 방법은 acceptance.md에 정의).
- **REQ-MVP-025** [Ubiquitous] — The 지시→실행 왕복 시간 **shall** 측정 코퍼스에 대한 **중앙값(median) 기준 10초 미만**이어야 한다. 측정 시작/종료 이벤트, 제외 규칙(인간 승인 대기, 웜캐시 조건), 재시도 턴 분리 집계는 acceptance.md의 "왕복 시간 측정 방법" 정의를 따른다.

### B.8 안전 게이트 우회 경로 봉쇄 (plan-audit MVP-C1 반영)

- **REQ-MVP-026** [Event-driven] — **When** 생성된 명령 시퀀스에 참조 호출 명령(매크로/시퀀스/플러그인을 호출·실행하는 명령)이 포함되면, the 안전 게이트 **shall** 호출 대상 오브젝트의 본문을 조회·전개하여 위험 분류를 적용하고, 본문을 확인할 수 없는(미검증) 참조 호출은 인간 승인 대상으로 보류한다 (전개-또는-보류 원칙). 참조 호출 인식 동사(invoking verbs)는 블랙리스트와 **동일한 SSOT 설정 파일**의 `invoking_verbs` 키로 정의되는 **폐쇄 집합**이며, MA3 v2.x 기준 초기 집합은 정확히 다음과 같다: 동사 10종 `Go`, `Go+`, `Go-`, `Goto`, `On`, `Off`, `Toggle`, `Temp`, `Flash`, `Call` + 베어 오브젝트 호출 2형 `Macro <n>`, `Plugin <n>`. 집합 변경은 설정 파일 개정(버전 증가)으로만 허용된다. 본문 전개의 재귀 깊이는 **최대 3단계**로 제한하며, 깊이 초과 또는 참조 순환(cycle) 감지 시 해당 호출은 보류 경로로 처리한다.
- **REQ-MVP-027** [Event-driven] — **When** `deploy_plugin`으로 제출된 Lua 소스에서 블랙리스트 명령을 포함하는 `Cmd()` 호출이 감지되면, the 리뷰 게이트 **shall** 파괴적 내용 스캔 결과를 리뷰어에게 명시적으로 표시하고, 승인 시 해당 플러그인을 "파괴적" 플래그와 함께 등록한다. **잔여 위험 명시**: 정적 `Cmd()` 스캔은 최선 노력(best-effort) 통제다 — Lua 문자열 연결 등 동적 조립으로 회피될 수 있으므로, **인간 리뷰 게이트가 권위 있는(authoritative) 통제로 유지**되며 스캔은 리뷰어 보조 신호로 위치한다.
- **REQ-MVP-028** [Ubiquitous] — The 시스템 **shall** 배포된 플러그인의 호출(실행)을 명령 실행 경로로 취급하여 안전 게이트를 통과시키며, "파괴적" 플래그가 부여된 플러그인의 호출은 블랙리스트 명령과 동일하게 매회 인간 승인을 요구한다.
- **REQ-MVP-029** [Ubiquitous] — The 안전 게이트 **shall** 콘솔로 향하는 모든 명령이 통과하는 **유일한 관문(single chokepoint)** 이어야 하며, 안전 게이트 이외의 어떤 모듈도 OSC 송신 표면에 직접 도달할 수 없어야 한다 (아키텍처 테스트로 검증 가능해야 함).

### B.9 장애 모드 및 부분 실행 (plan-audit MVP-M4 반영)

- **REQ-MVP-030** [Event-driven] — **When** 콘솔 미응답(하트비트 또는 조회 타임아웃)이 감지되면, the 시스템 **shall** "콘솔 오프라인" 상태를 UI에 표시하고 신규 명령 실행을 차단한다.
- **REQ-MVP-031** [Event-driven] — **When** Lua responder의 미응답이 감지되면, the 시스템 **shall** 상태 조회·결과 회수 기능을 저하(degraded) 상태로 보고하고, 결과 확인이 불가능한 상태에서는 부수효과 있는 명령의 실행을 개시하지 않는다.
- **REQ-MVP-032** [Event-driven] — **When** 명령 송신 후 결과 확인이 타임아웃되면(송신 UDP 유실과 피드백 유실은 관측상 구분 불가), the 시스템 **shall** 해당 명령을 "실행 미확인" 상태로 사용자에게 보고하고, 부수효과 있는 명령을 자동 재전송하지 않는다.
- **REQ-MVP-033** [Event-driven] — **When** 번들 실행 중 k번째 명령의 실패가 감지되면, the 시스템 **shall** 잔여 명령 실행을 즉시 중단하고(stop-on-first-failure), 이미 실행된 1..k−1 명령을 자동 재전송하지 않으며, 부분 실행 상태를 사용자에게 보고한다. 자가 수정 루프(REQ-MVP-009)는 미실행 잔여분과 신규 수정 명령에만 적용된다 (기실행 명령 중복 실행 금지 — 실행 시점 원자성 규칙).
- **REQ-MVP-034** [Event-driven] — **When** 쇼파일 백업 실패가 감지되면, the 시스템 **shall** 예정된 명령 실행을 차단하고 사용자에게 백업 실패를 통지한다 (fail-safe).

### B.10 추가 안전 요구 — 엣지 케이스 승격 (plan-audit MVP-m3 반영)

- **REQ-MVP-035** [Event-driven] — **When** 인간 승인 대기 중 라이브 잠금이 활성화되면, the 안전 게이트 **shall** 보류 중이던 위험 명령을 실행 불가 상태로 전환한다 (잠금이 승인보다 우선).
- **REQ-MVP-036** [Unwanted + Event-driven] — (a) The 시스템 **shall not** 대상이 불명확한(다의적) 지시로부터 파괴적 명령을 임의 추측으로 생성하거나 실행한다. (b) **When** 파괴적 명령에서 명시적 대상 지정의 결여(미특정·광역 패턴)가 감지되면, the 안전 게이트 **shall** 해당 명령을 자동 실행하지 않고 인간 승인 대상으로 보류하며, the UI **shall** 대상 미특정 경고를 표시한다. (b)는 결정적 하네스 수준 통제이며, 모델의 대상 확인 질문 품질은 모니터링 지표로 관리한다 (AC-MVP-024).

### B.11 리그 컨텍스트 도구 (plan-audit MVP-M7 반영)

- **REQ-MVP-037** [Event-driven] — **When** `get_rig_context` 도구가 호출되면, the 도구 **shall** 로드된 showfile로부터 패치·그룹·프리셋 어휘의 요약을 반환한다 (Phase 1 범위: showfile 기반 기본 요약 — Out of Scope 절의 MVR/GDTF 제외와 정합).

### B.12 LLM 프로바이더 추상화 (2026-07-15 amendment)

- **REQ-MVP-038** [Ubiquitous] — The LLM 클라이언트 **shall** 프로바이더 교체 가능한 추상화 계층 뒤에 위치한다 — 도구 호출, 시스템 프롬프트 구성, 응답 파싱이 프로바이더 중립 인터페이스로 분리되어야 하며, 상위 계층(오케스트레이터·안전 게이트·UI)은 활성 프로바이더를 알지 못한 채 동작한다.
- **REQ-MVP-039** [Ubiquitous] — The 시스템 **shall** Anthropic Claude와 Google Gemini 2개 프로바이더를 지원하며, 프로바이더 선택은 설정 파일로 이루어진다 — 코드 변경 없이 전환 가능해야 한다.
- **REQ-MVP-040** [Ubiquitous] — The 기본(default) 프로바이더 **shall** 다음 술어로 결정된다 (사용자 규칙 "오류율 통과 → 비용 우선"의 정련 — 기각 아님):
  - **(i) 적격(eligible) 조건**: 프로바이더는 **AC-MVP-002(pooled 문법 오류율 <5%)와 AC-MVP-003(왕복 중앙값 <10초)를 모두** 해당 프로바이더 기준으로 측정하여 통과한 경우에만 기본 프로바이더 적격이다. 적격 프로바이더가 복수이면 **비용이 낮은 쪽을 우선**한다.
  - **(ii) 폴백 규칙**: 운영 중 비용-우선 선정 프로바이더가 AC-MVP-003 조건을 지속적으로 충족하지 못하면, the 시스템 **shall** 다른 적격 프로바이더로 폴백한다 — 폴백은 설정 전환(REQ-MVP-039)으로 수행되며 감사 로그에 기록된다. **지속 미충족 감지 규칙 (AD2-m1 반영, 2026-07-16)**: "지속적으로 충족하지 못함"의 감지는 **설정 정의 운영 파라미터**다 — 기본값: 최근 **N=20** 판정 대상 턴(재시도 턴 제외 — acceptance "왕복 시간 측정 방법" §4와 동일 코퍼스 규칙)의 롤링 윈도우 중앙값이 10초를 초과하는 윈도우가 **M=2회 연속**이면 폴백을 트리거한다. N/M은 설정 파일로 재정의 가능하며, 감지 규칙의 동작은 AC-MVP-031로 검증한다.
  - **(iii) 비용 산정 기준**: 비용은 **측정 코퍼스 1회 실행의 실측 API 청구액** 기준이다. 무료 등급 사용분은 0으로 계상한다 — 단, 무료 등급 rate limit로 AC-MVP-003을 통과하지 못하면 (i)에서 적격 탈락하므로 "무료=0" 계상과 지연 요건 사이에 모순이 없다.
- **REQ-MVP-041** [Capability gate] — **Where** 활성 프로바이더가 프롬프트 캐싱을 지원하는 경우(Anthropic prompt caching / Gemini context caching), the 시스템 **shall** 해당 프로바이더의 캐싱 메커니즘으로 룰북 고정 프리픽스 캐싱을 적용한다. 캐싱 미지원 또는 최소 토큰 임계 미달 구성에서는 성능·비용 저하를 수용한다 (명시적 트레이드오프). **측정-조건 명확화 (AM-M2c)**: "웜캐시 가능 조건 기준"은 **측정 조건**의 의미다 — 왕복 시간은 활성 프로바이더가 제공하는 최선의 캐시 상태(웜캐시 가능 시 웜캐시, 비캐시 구성 시 비캐시 그대로)에서 측정한다는 뜻이며, **판정 기준(중앙값 <10초)의 완화(waiver)가 아니다**. plan.md §A-7의 사용자 승인 판정 기준은 불변이다 — 비캐시 프로바이더가 이 기준을 넘지 못하면 REQ-MVP-040 (i)에서 적격 탈락한다.

### B.13 EVAL 격차 반영 요구 (2026-07-16 §F fold-in amendment — G-02/G-10/G-11)

- **REQ-MVP-042** [Ubiquitous] — The MA3 문법 룰북 고정 프리픽스 **shall** 한국어 현장 조명 용어 ↔ MA3 오브젝트/키워드 매핑 사전 축을 포함한다 (예: "샤막" → 대응 픽스처 그룹/오브젝트 어휘, "워시" → Wash 계열 픽스처/프리셋 어휘). 사전 축은 룰북 고정 프리픽스의 일부로서 REQ-MVP-008의 캐시 프리픽스 안정성 제약(턴마다 변하는 값 금지)을 동일하게 따른다. (격차 G-02 반영 — boardop은 영어 전용 설계로 현장 용어 처리 개념 자체가 부재)
- **REQ-MVP-043** [Ubiquitous] — The 서버·UI 구성요소 **shall** macOS를 포함한 크로스플랫폼에서 구동 가능해야 하며, 재현 가능한 오픈 설치 경로 — 문서화된 설치 절차 + 의존성 버전 핀(lockfile) — 를 제공한다. 설치 경로는 비공개 자원(베타 신청·수동 배포 번들 등)에 의존하지 않는다. 콘솔측 Lua responder는 grandMA3 onPC가 지원하는 플랫폼 범위를 따른다. (격차 G-10 반영 — boardop의 클로즈드 베타·Windows 전용 배포와의 차별점)
- **REQ-MVP-044** [Unwanted + Event-driven] — (a) The 시스템 **shall not** LLM SDK/프로바이더의 raw 오류·경고 원문을 채팅 표면에 그대로 노출한다. (b) **When** 프로바이더 SDK 오류·경고가 발생하면, the UI **shall** 한국어로 번역된 사용자 오류 메시지를 표시하고, the 시스템 **shall** 원문 상세를 감사·진단 로그에만 기록한다. (REQ-MVP-022 오류 보고의 확장 — 격차 G-11 반영; boardop의 raw SDK 경고 사용자 터미널 노출 관찰이 직접 근거)

## C. 제약사항

- 서버는 Python 3.11+, 콘솔측은 grandMA3 Lua 5.4 환경을 대상으로 한다.
- 지원 MA3 버전은 v2.x로 고정하며, 세부 버전 핀은 plan.md 결정 사항을 따른다.
- 라이브 쇼 실시간 자율 운영은 설계상 배제된다 (라이브 잠금은 안전장치이지 라이브 운영 기능이 아니다).
- 자가 수정 루프·토큰 사용은 비용 폭주 방지를 위해 상한이 있어야 한다 (재시도 ≤3회).

## D. 제외 범위 (Exclusions)

다음 항목은 본 SPEC의 out of scope다.

### Out of Scope — propose_plan 도구
- DESIGN.md §3 다이어그램에 언급된 5번째 도구이나, Phase 1 도구 세트는 4종(run_commands / query_state / deploy_plugin / get_rig_context)으로 확정되었다. propose_plan은 Phase 2 이후 검토.

### Out of Scope — 리그 컨텍스트 고도화 (MVR/GDTF, 추상 지시 해석)
- MVR/GDTF 파서 전면 구현과 "코러스에서 금색 톤으로 웅장하게" 수준의 추상 지시 해석은 Phase 2 범위다. Phase 1의 `get_rig_context`는 showfile 기반 기본 요약(패치·그룹·프리셋 어휘) 수준으로 한정한다.

### Out of Scope — 음악 분석·큐리스트 자동화
- 음악 구간/BPM/에너지 분석과 타임코드 큐리스트 초안 생성은 Phase 3 범위다.

### Out of Scope — 라이브 보조 기능
- 다음 큐 제안, 버스킹 팔레트 추천, 이상 감지 알림은 Phase 4 범위다. (라이브 잠금 모드 자체는 Phase 1 필수 — 잠금 상태에서의 능동적 보조 기능만 제외)

### Out of Scope — 동시 멀티 모델 라우팅·모델 티어링
- `claude-haiku-4-5` 의도 라우팅, `claude-fable-5` 대규모 기획 옵션 등 **동시 다중 모델 라우팅·티어링**은 비용 데이터 축적 후 도입한다. Phase 1은 단일 활성 프로바이더·단일 모델 구성이다.
- 경계 명확화 (2026-07-15 amendment): **멀티 프로바이더 추상화 계층과 설정 기반 프로바이더 전환(§B.12)은 IN scope**다 — 제외되는 것은 한 세션에서 여러 모델을 동시에 라우팅하는 것뿐이다.

### Out of Scope — 음성 입력 옵션
- STT 기반 음성 입력은 DESIGN.md에 옵션으로만 언급되었으며 Phase 1 범위가 아니다.

### Out of Scope — 파라미터 가드레일 (광과민성 경고)
- 스트로브 주파수·디머 급변 경고는 DESIGN.md §5의 추가 안전 요소이나, Phase 1 안전 게이트 v1(문법 검증 + 블랙리스트 + 승인 UI) 범위 밖이다.

### Out of Scope — boardop 코드 재사용
- FSL-1.1 제약에 따라 boardop 코드의 어떤 부분도 재사용·이식하지 않는다. 모든 컴포넌트는 자체 구현이다.
