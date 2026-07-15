---
id: SPEC-COPILOT-EVAL-001
title: "Phase 0: boardop 실사용 평가 및 격차 분석"
version: "0.2.1"
status: draft
created: 2026-07-15
updated: 2026-07-15
author: manager-spec
priority: P0
phase: "Phase 0 — 검증 (v0.1.0 target)"
module: ".moai/project/research/"
lifecycle: exploratory
tags: "evaluation, research, boardop, gap-analysis, fsl-license, grandma3"
tier: S
related_specs: [SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-EVAL-001 — Phase 0: boardop 실사용 평가 및 격차 분석

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-07-15 | manager-spec | 최초 작성 (draft) |
| 0.2.1 | 2026-07-15 | manager-spec | amendment delta re-audit 지적 반영(E-am2): 환경 기록 필드 수 5종 → 6종 정정 (프로바이더 필드 포함 — AC-EVAL-001·GWT 1 갱신) |
| 0.2.0 | 2026-07-15 | manager-spec | 정식 amendment — LLM 프로바이더 전략 반영 (사용자 결정 2026-07-15): 평가는 Anthropic 또는 Gemini API 키로 수행 가능(Gemini 무료 등급 우선 권장, $20 상한은 양 프로바이더 유료분 합산), REQ-EVAL-001/003 개정, REQ-EVAL-013(선택적 Claude/Gemini 비교) 신설. 영향 REQ: 001, 003, 013 |
| 0.1.3 | 2026-07-15 | manager-spec | clarification gate 해소: plan.md §A 마커 2건 전원 결정 기록으로 대체 (최신 안정 v2.x 릴리스 핀, API 예산 상한 $20) |
| 0.1.2 | 2026-07-15 | manager-spec | plan-audit iteration 2 (PASS 0.96) 지적 반영: REQ-EVAL-011의 이중 shall 절을 REQ-EVAL-011/012로 분리, 각기 정확한 GEARS 태그 부여(E-m6) |
| 0.1.1 | 2026-07-15 | manager-spec | plan-audit iteration 1 minor 지적(E-m1~E-m5) 반영: REQ-EVAL-011 추가(파괴적 시나리오 의무화), AC-EVAL-001 no-mock 판별 강화, AC-EVAL-005 이진 체크리스트화, 산출물 형상 비고 추가 |

## A. 개요

본 SPEC은 grandMA3 AI 코파일럿 로드맵의 **Phase 0 (검증)** 을 정의한다. 성격은 **평가/리서치 SPEC**이며, 산출물은 프로덕션 코드가 아니라 **문서**다.

가장 가까운 선행 사례인 **boardop**(FSL-1.1-Apache-2.0 라이선스)을 grandMA3 onPC 환경에서 실제로 구동·평가하여, 자체 MVP(Phase 1, SPEC-COPILOT-MVP-001)가 메워야 할 격차를 확정하고 FSL 라이선스 검토 결론을 문서화한다.

**사전 확정 사실 (재질의 금지):**
- boardop은 아키텍처 벤치마킹 대상일 뿐이며, 그 **코드는 재사용하지 않는다** (FSL-1.1 제약).
- 평가에는 Anthropic API 키 **또는 Google Gemini API 키**가 필요하며(boardop은 Claude/Gemini 듀얼 지원), **Gemini 무료 등급 사용을 우선 권장**한다. MA 하드웨어는 불필요하다 (onPC 개발·프리비즈는 무료). [2026-07-15 amendment]

**산출물 형상 비고 (plan-audit E-m4 반영)**: 본 SPEC은 `tier: S`이나, 수용 기준을 별도 acceptance.md로 분리한 Tier M 형상의 산출물 세트를 의도적으로 채택했다 (안전 관찰 시나리오의 검증 방법을 독립 문서로 관리하기 위한 과제공·over-delivery). 다운스트림 도구는 이 편차를 문서화된 의도로 취급한다.

## B. 요구사항 (GEARS)

### B.1 평가 환경

- **REQ-EVAL-001** [Ubiquitous] — The 평가 환경 기록 **shall** grandMA3 onPC 버전, boardop 버전(커밋 해시 포함), 운영체제, Python 런타임 버전, 사용한 LLM 프로바이더(Anthropic/Google) 및 모델 ID를 명시한다.
- **REQ-EVAL-002** [Event-driven] — **When** grandMA3 onPC와 boardop이 모두 기동되어 상호 통신(OSC 연결)이 수립되면, the 평가자 **shall** 구동 성공 증거(로그 또는 화면 캡처)를 평가 기록에 남긴다.
- **REQ-EVAL-003** [Capability gate] — **Where** Anthropic 또는 Google Gemini API 키가 구성된 환경에서, the boardop 평가 세션 **shall** 실제 LLM API 호출로 수행한다 (모의 응답으로 대체하지 않는다). Gemini 무료 등급 사용을 우선 권장하며, $20 예산 상한(plan.md §A-2)은 **양 프로바이더의 유료 사용분 합산**에 적용된다.

### B.2 시나리오 평가

- **REQ-EVAL-004** [Event-driven] — **When** 대표 프로그래밍 시나리오 1건의 실행이 완료되면, the 평가 기록 **shall** 입력 지시문, boardop이 생성한 명령, 실행 결과(성공/실패), 실패 시 오류 유형을 기록한다.
- **REQ-EVAL-005** [Ubiquitous] — The 시나리오 평가 **shall** 대표 프로그래밍 시나리오를 최소 8종 포함한다.
- **REQ-EVAL-006** [State-driven] — **While** 평가 세션이 진행 중인 동안, the 평가자 **shall** 시나리오별 API 사용량(토큰/비용 추정)을 함께 기록한다.

### B.3 격차 분석

- **REQ-EVAL-007** [Ubiquitous] — The 격차 분석 문서 **shall** `.moai/project/research/boardop-gap-analysis.md` 경로에 산출되며, 다음 4개 평가 축을 모두 다룬다: ① 한국어 UX 부재, ② 안전장치 수준, ③ 도구 커버리지, ④ 신뢰성.
- **REQ-EVAL-008** [Ubiquitous] — The 격차 분석 문서 **shall** 격차 항목을 10개 이상 열거하고, 각 항목에 Phase 1(MVP) 반영 여부(반영 / 보류 / 미반영)와 그 근거를 표기한다.

### B.4 라이선스 검토

- **REQ-EVAL-009** [Ubiquitous] — The 격차 분석 문서 **shall** FSL-1.1-Apache-2.0 라이선스 검토 결론을 독립된 1개 절(section)로 포함하며, "내부 사용·평가 허용, 경쟁 상용 제품에의 코드 재사용은 Apache 전환(릴리스별 2년) 이전까지 제약, 따라서 아키텍처만 벤치마킹하고 코드는 자체 구현"이라는 결론과 근거를 서술한다.
- **REQ-EVAL-010** [Unwanted] — The 본 SPEC의 모든 산출물 **shall not** boardop 소스 코드(원문 또는 파생·번역물)를 포함한다.

### B.5 안전 관찰 시나리오 (plan-audit E-m2 반영)

- **REQ-EVAL-011** [Ubiquitous] — The 시나리오 세트 **shall** 파괴적(블랙리스트성) 명령을 유발하는 시나리오를 1종 이상 포함한다 (격차 축 ② "안전장치 수준"의 증거 공급원).
- **REQ-EVAL-012** [State-driven] — **While** 파괴적 시나리오를 실행하는 동안, the 평가자 **shall** 일회용 테스트 쇼파일만 사용한다.

### B.6 선택적 모델 비교 (2026-07-15 amendment)

- **REQ-EVAL-013** [Capability gate — 선택(may)] — **Where** 예산($20 상한) 여유가 있는 환경에서, the 평가자 **may** 동일 시나리오를 Claude와 Gemini 양쪽으로 실행하여 모델별 오류 특성 비교 데이터를 격차 분석 문서에 포함할 수 있다. 본 요구는 선택 사항이며 미실행이 SPEC 실패를 구성하지 않는다.

## C. 제약사항

- 평가 결과는 SPEC-COPILOT-MVP-001의 범위 확정 입력으로 사용된다 (Phase 1은 본 SPEC 완료에 의존).
- 산출물 언어: 한국어 (코드 인용·식별자는 영어 유지).
- 평가는 onPC 단독 환경에서 수행하며, DMX 실출력 검증은 수행하지 않는다.

## D. 제외 범위 (Exclusions)

다음 항목은 본 SPEC의 out of scope다.

### Out of Scope — 프로덕션 코드 구현
- OSC 브리지, Lua responder, 채팅 UI 등 자체 컴포넌트 구현은 SPEC-COPILOT-MVP-001(Phase 1)의 범위다. 본 SPEC은 문서 산출물만 낸다.

### Out of Scope — boardop 코드 재사용·포크
- boardop 저장소의 코드 복사, 포크 기반 수정, 파생물 제작은 FSL-1.1 제약에 따라 수행하지 않는다. 평가 목적의 설치·구동만 허용된다.

### Out of Scope — MA 하드웨어 실출력 검증
- DMX 실출력에는 MA 하드웨어가 필요하며, Phase 0 평가 범위가 아니다. onPC 내부 상태 확인으로 충분하다.

### Out of Scope — Phase 2~4 기능 평가
- 리그 컨텍스트 인식(showfile/MVR/GDTF), 음악 분석 큐리스트, 라이브 보조 기능에 대한 평가는 수행하지 않는다. 격차 목록에 참고 항목으로 기재하는 것은 허용된다.
