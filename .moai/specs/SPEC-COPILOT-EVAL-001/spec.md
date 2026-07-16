---
id: SPEC-COPILOT-EVAL-001
title: "Phase 0: boardop 실사용 평가 및 격차 분석"
version: "0.3.1"
status: in-progress
created: 2026-07-15
updated: 2026-07-16
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
| 0.3.1 | 2026-07-16 | manager-spec | plan-audit amendment-delta iteration 1 (FAIL 0.87) 지적 반영 — F1: REQ-EVAL-014 트리거를 이진 판정형(문서화된 접근 시도 이력 + 오케스트레이터 AskUserQuestion 사용자 확인 기록)으로 재작성, §A에 플랫폼 비호환 문서 증거 기반 + ground truth 접근 시도 이력 기재. F2: AC-EVAL-006에 [문서 폴백 시] 경로 신설(파괴적 시나리오 유지 + REQ-EVAL-015 태그 + 문서 증거 기반 안전장치 평가 + 실행·일회용 쇼파일 절 명시적 N/A), DoD 이중 경로를 001/002/006으로 확장. F3: AC-EVAL-002 폴백 행 단위 출처 인용·탐색 범위 기록 의무 + REQ-EVAL-015 3분류(실행 확인 / 관찰 기반(실행 미확인) / 관찰 불가) 정비 + REQ-EVAL-004 폴백 상응 기록 항목 정의. F4: AC-EVAL-005 체크리스트 ④(스크린샷·프레임 코드 전사 0건) 추가, 품질 게이트 미러 갱신. F6: REQ-EVAL-001에 폴백 시 실측 불가 항목 "관찰 불가 — 라이브 실행 미확보" 표기 절 추가. 영향 REQ: 001, 014, 015 |
| 0.1.0 | 2026-07-15 | manager-spec | 최초 작성 (draft) |
| 0.3.0 | 2026-07-16 | manager-spec | boardop 베타 코드 미공개(접근 채널 폐쇄) + macOS 미지원 확인에 따른 amendment — 실사용 라이브 세션이 확보 불가할 때 문서/영상 관찰 기반 평가로 대체 가능하도록 REQ-EVAL-002/003 및 AC-EVAL-001/002 조정. REQ-EVAL-010 코드 미포함 원칙은 스크린샷 내 코드 전사에도 명시적으로 적용. 신설: REQ-EVAL-014(폴백 트리거)/REQ-EVAL-015(근거 구분 표기). 영향 REQ: 002, 003, 010, 014, 015 |
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

**폴백 평가 방법론 (2026-07-16 amendment; 0.3.1 트리거 이진화)**: boardop 실행 코드는 비공개 베타로, 공개 저장소(`pimteters/boardop`)에는 README와 데모 에셋만 존재하며 실행 코드는 없다. 접근은 별도 베타 신청(이메일 `hello@boardop.dev` 또는 웹폼)으로만 가능하고 응답 시한은 불명확하다. **플랫폼 비호환의 문서화된 증거 기반**: README·웹사이트의 "Windows-first" 명시 + Windows 전용 플랫폼 배지 + Windows 전용 진입점 `run_server.bat` + 모든 공식 표면에서 macOS 언급 0건 (현재 평가 머신은 macOS) — 단순 "미언급"이 아니라 위 증거들의 합을 문서화된 판단 근거로 삼는다. **성의있는 접근 시도 이력 (ground truth)**: (a) 베타 신청 이메일 준비 2026-07-15 (수신처 `hello@boardop.dev`), (b) 공개 저장소 코드 부재 실측 확인 (커밋 c13c274), (c) 위 플랫폼 비호환 문서 증거 확인, (d) 사용자의 폴백 결정이 2026-07-16 오케스트레이터 AskUserQuestion으로 기록됨 ("문서·영상 관찰 기반으로 SPEC 재조정" 선택). 위 접근 시도 이력이 문서화되고 사용자 확인이 기록된 경우, 본 평가는 **문서/영상 관찰 기반 증거**(공개 README, 저장소 내 데모 자산의 프레임 추출 관찰, 발견되는 제3자 리뷰·커뮤니티 논의)로 대체 수행할 수 있다 (REQ-EVAL-014 — 트리거는 문서화된 접근 시도 이력 + 기록된 사용자 확인의 두 요소이며 모두 기록 존재 여부로 이진 판정된다). 라이브 접근이 이후 확보되면 우선 사용된다.

## B. 요구사항 (GEARS)

### B.1 평가 환경

- **REQ-EVAL-001** [Ubiquitous] — The 평가 환경 기록 **shall** grandMA3 onPC 버전, boardop 버전(커밋 해시 포함), 운영체제, Python 런타임 버전, 사용한 LLM 프로바이더(Anthropic/Google) 및 모델 ID를 명시한다. **Where** REQ-EVAL-014 폴백이 적용되는 환경에서는, 라이브 실행 없이 실측 불가한 항목(예: 모델 ID, 실측 토큰/비용)을 누락하는 대신 "관찰 불가 — 라이브 실행 미확보"로 명시 기록한다 (AC-EVAL-001 폴백 경로와 정합). [2026-07-16 amendment; 0.3.1]
- **REQ-EVAL-002** [Capability gate] — **Where** grandMA3 onPC와 boardop이 모두 기동되어 상호 통신(OSC 연결)이 수립되는 라이브 실행 접근이 확보된 환경에서, the 평가자 **shall** 구동 성공 증거(로그 또는 화면 캡처)를 평가 기록에 남긴다. 라이브 실행 접근이 확보되지 않는 경우의 대체 절차는 REQ-EVAL-014(폴백 트리거)를 따른다. [2026-07-16 amendment]
- **REQ-EVAL-003** [Capability gate] — **Where** Anthropic 또는 Google Gemini API 키가 구성되고 라이브 실행 접근이 확보된 환경에서, the boardop 평가 세션 **shall** 실제 LLM API 호출로 수행한다 (모의 응답으로 대체하지 않는다). Gemini 무료 등급 사용을 우선 권장하며, $20 예산 상한(plan.md §A-2)은 **양 프로바이더의 유료 사용분 합산**에 적용된다. 라이브 실행 접근이 확보되지 않는 경우의 대체 절차는 REQ-EVAL-014(폴백 트리거)를 따른다. [2026-07-16 amendment]

### B.2 시나리오 평가

- **REQ-EVAL-004** [Event-driven] — **When** 대표 프로그래밍 시나리오 1건의 실행이 완료되면, the 평가 기록 **shall** 입력 지시문, boardop이 생성한 명령, 실행 결과(성공/실패), 실패 시 오류 유형을 기록한다.
- **REQ-EVAL-005** [Ubiquitous] — The 시나리오 평가 **shall** 대표 프로그래밍 시나리오를 최소 8종 포함한다.
- **REQ-EVAL-006** [State-driven] — **While** 평가 세션이 진행 중인 동안, the 평가자 **shall** 시나리오별 API 사용량(토큰/비용 추정)을 함께 기록한다.

### B.3 격차 분석

- **REQ-EVAL-007** [Ubiquitous] — The 격차 분석 문서 **shall** `.moai/project/research/boardop-gap-analysis.md` 경로에 산출되며, 다음 4개 평가 축을 모두 다룬다: ① 한국어 UX 부재, ② 안전장치 수준, ③ 도구 커버리지, ④ 신뢰성.
- **REQ-EVAL-008** [Ubiquitous] — The 격차 분석 문서 **shall** 격차 항목을 10개 이상 열거하고, 각 항목에 Phase 1(MVP) 반영 여부(반영 / 보류 / 미반영)와 그 근거를 표기한다.

### B.4 라이선스 검토

- **REQ-EVAL-009** [Ubiquitous] — The 격차 분석 문서 **shall** FSL-1.1-Apache-2.0 라이선스 검토 결론을 독립된 1개 절(section)로 포함하며, "내부 사용·평가 허용, 경쟁 상용 제품에의 코드 재사용은 Apache 전환(릴리스별 2년) 이전까지 제약, 따라서 아키텍처만 벤치마킹하고 코드는 자체 구현"이라는 결론과 근거를 서술한다.
- **REQ-EVAL-010** [Unwanted] — The 본 SPEC의 모든 산출물 **shall not** boardop 소스 코드(원문 또는 파생·번역물)를 포함한다. 이 제약은 스크린샷·영상 프레임에 노출된 코드(예: 플러그인 리뷰 화면의 Lua 스니펫)의 전사(transcription)에도 동일하게 적용된다 — 동작을 서술하되 코드 원문을 옮겨 적지 않는다. [2026-07-16 amendment: 스크린샷 코드 전사 명시화]

### B.5 안전 관찰 시나리오 (plan-audit E-m2 반영)

- **REQ-EVAL-011** [Ubiquitous] — The 시나리오 세트 **shall** 파괴적(블랙리스트성) 명령을 유발하는 시나리오를 1종 이상 포함한다 (격차 축 ② "안전장치 수준"의 증거 공급원).
- **REQ-EVAL-012** [State-driven] — **While** 파괴적 시나리오를 실행하는 동안, the 평가자 **shall** 일회용 테스트 쇼파일만 사용한다.

### B.6 선택적 모델 비교 (2026-07-15 amendment)

- **REQ-EVAL-013** [Capability gate — 선택(may)] — **Where** 예산($20 상한) 여유가 있는 환경에서, the 평가자 **may** 동일 시나리오를 Claude와 Gemini 양쪽으로 실행하여 모델별 오류 특성 비교 데이터를 격차 분석 문서에 포함할 수 있다. 본 요구는 선택 사항이며 미실행이 SPEC 실패를 구성하지 않는다.

### B.7 실행 접근 불가 시 폴백 평가 (2026-07-16 amendment)

- **REQ-EVAL-014** [Event-driven] — **Where** 실행 가능한 boardop 인스턴스 확보를 위한 성의있는 접근 시도 이력(일자·채널·응답/무응답 결과)이 평가 기록에 문서화된 환경에서, **When** 문서/영상 관찰 기반 평가로의 전환이 오케스트레이터의 AskUserQuestion 사용자 확인 기록으로 확정되면, the 평가자 **shall** 문서/영상 관찰 기반 평가(공개 README, 저장소 내 데모 자산의 프레임 추출 관찰, 발견되는 제3자 리뷰·커뮤니티 논의)로 전환하고, 접근 시도 이력과 전환 확정 기록(확인 일자·선택 내용)을 평가 기록에 남긴다. 두 트리거 요소(문서화된 접근 시도 이력, 기록된 사용자 확인)는 각각 기록의 존재 여부로 이진 판정하며, 평가자 자체 판단("합리적 대기 기간")은 트리거 요건이 아니다. 본 SPEC의 ground truth 접근 시도 이력과 2026-07-16 사용자 확인 기록은 §A(폴백 평가 방법론)에 기재되어 있다. [2026-07-16 amendment; 0.3.1 트리거 이진화]
- **REQ-EVAL-015** [State-driven] — **While** 문서/영상 관찰 기반 폴백 평가가 적용되는 동안, the 평가 기록 **shall** 각 평가 근거 행을 다음 3분류 중 하나로 명시 구분한다: "실행 확인" / "관찰 기반(실행 미확인)" / "관찰 불가". "관찰 기반(실행 미확인)" 행은 근거 출처(README 절, 데모 자산 파일명 + 프레임 타임스탬프·인덱스, 또는 URL)를 행 단위로 인용하고, "관찰 불가" 행은 탐색 범위(확인한 자산·문서 목록)를 기록한다. [2026-07-16 amendment; 0.3.1 분류 확장]

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
