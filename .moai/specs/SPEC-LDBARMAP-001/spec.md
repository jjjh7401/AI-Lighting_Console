---
id: SPEC-LDBARMAP-001
title: "마디 지도 — 오프라인 박자·다운비트·마디 경계·마디별 변화 검출"
version: "0.1.0"
status: in-progress
created: 2026-10-10
updated: 2026-10-10
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.2 target"
module: "server/audio/analyze.py(M1 보정 — 읽기·측정 스크립트만, 프로덕션 모듈 수정 0줄), 신규 server/audio/bar_map.py 후보(M2+, 착수 승인 후), .moai/reports/SPEC-LDBARMAP-001-probes(M1 산출물)"
lifecycle: spec-anchored
tags: "bar-map, beat-grid, downbeat-detection, offline-analysis, calibration, love-attack"
tier: M
related_specs: [SPEC-LDRHYTHM-001, SPEC-LDBEAT-001]
---

# SPEC-LDBARMAP-001 — 마디 지도: 오프라인 박자·다운비트·마디 경계·마디별 변화 검출

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-10 | 최초 작성(카드 t527). 입력: `reports/ldbeat-feasibility-roadmap-20261010.md`(리드 작성, §3 항목 1·§5 ② — 진행 순서 LDBEAT → 마디 분석 SPEC(이 SPEC) → 자동 배치 SPEC), `.moai/specs/SPEC-LDRHYTHM-001/spec.md` REQ-LDRHYTHM-012(a)(M4+ 범위 후보 — 이 SPEC이 그 후보를 이어받는다), `server/audio/analyze.py`(이 plan-phase에서 재확인 — 아래 §1 인용), `.moai/specs/SPEC-LDBEAT-001/spec.md` REQ-LDBEAT-006(저장 인터페이스 선례, 이 SPEC의 열린 결정이 참조), `reports/loveattack-music-map-20261006.md`(LOVE ATTACK 손 분석 — 이 SPEC의 유일한 기준점). **plan만 — 코드 변경 0줄, 콘솔 접촉 0건.** |
| 2026-10-10 | **plan-audit iteration 1 FAIL(0.60, 통과선 0.80) 대응(같은 날 후속).** 7개 must-pass 전부 PASS/N/A, FAIL은 집계 점수 미달. **D1(critical)**: `acceptance.md` AC-LDBARMAP-006의 "총 8개 마디 지점"이 자기 Given 절이 나열한 빌드업(14~17·42~45, 8마디)+큰 히트(18·46, 2마디)+킥 멈춤(33·61·82, 3마디) 합 13과 맞지 않았다 — **사건(event) 단위**로 셈을 다시 정의했다: 빌드업 2개(각 구간 전체를 온셋 마디 ±1 허용오차로 판정)+큰 히트 2개+킥 멈춤 3개 = **7개 사건**, 70% 통과선을 "7개 중 5개 이상"으로 명시했다(acceptance.md AC-LDBARMAP-007, 구 AC-006). **D3(critical)**: 음성 대조군이 1박 밀림만 다뤄 1마디(4박) 밀린 날조 격자가 "다음 정답 다운비트에 우연히 맞아" 통과할 위험(최근접 매칭이면 97%대 적중까지 가능)이 있었다 — REQ-LDBARMAP-005에 **엄격한 순서 대응(strict index-aligned matching, 지도 보고서 부록 A 1마디부터 번호 매김)**을 명시하고, 최근접 매칭을 금지했으며, 1박·1마디(2.136초/4박) 두 음성 대조군을 모두 요구하도록 고쳤다(acceptance.md AC-LDBARMAP-002/003, 1마디 대조군 신설). **D2(major)**: REQ-LDBARMAP-010과 (구)REQ-LDBARMAP-012가 한 문장 안에서 `shall`과 `shall not`을 동시에 굵게 표시하는 이중 모달이었다 — REQ-010은 "저장 형태 확정은 이 plan-phase에서 이뤄지지 **shall not**"의 단일 모달로 고치고(기록·결정 시점은 근거 칸의 비요구사항 설명으로 이동), (구)REQ-012는 **REQ-LDBARMAP-012**(LDRHYTHM REQ-012(a) 승계, `shall` 단일)와 **신설 REQ-LDBARMAP-013**(LDRHYTHM 파일 미수정, `shall not` 단일)으로 분리했다 — 이로 인해 구 REQ-013(오디오 비커밋)은 **REQ-LDBARMAP-014**로, 구 REQ-014(plan-phase 자신 제약)는 **REQ-LDBARMAP-015**로 한 칸씩 밀렸다(R5 절 전체 재번호). **D4(major)**: `acceptance.md`의 13개 AC 중 4개만 REQ-ID를 직접 인용했다 — 전체 AC에 `(REQ-LDBARMAP-NNN)` 인용을 추가하고, REQ-LDBARMAP-001(오프라인 전용 경계)을 검증하는 AC가 없던 공백을 **신설 AC-LDBARMAP-015**로 메웠다. **D5(minor)**: `acceptance.md` §A/본문의 "두 배 BPM 함정"이 `224.70`(이론값)으로 적혀 있어 spec.md 자신이 인용한 지도 보고서 원문 `224.69`(실측값)와 어긋났다 — `224.69`로 통일했다. REQ 총량 **14→15개**(REQ-012 분리 신설 1건), AC 총량 **13→15개**(AC-003/AC-015 신설 2건) — Tier M 상한(각 16개) 안에 든다. D6(minor, 선택)은 비용 대비 효과가 낮다고 판단해 이번 교정에서는 적용하지 않았다(§1/§2 헤더 구조는 그대로). |
| 2026-10-10 | **plan-audit iteration 2 FAIL(0.68, 통과선 0.80) 대응(같은 날 후속).** D1~D6(iteration 1)은 전부 RESOLVED로 재확인됐다. iteration 1의 AC-003(1마디 밀림 음성 대조군) 삽입이 그 뒤 모든 AC 번호를 1씩 밀렸는데, `plan.md`가 이 재번호를 반영하지 못해 두 가지 회귀가 생겼다. **D-NEW-1(critical)**: `plan.md` M1/M2/M3의 통과 조건이 옛/틀린 AC 번호를 인용했다 — M1(`plan.md:31`)의 "AC-LDBARMAP-001~005"는 마디 경계 적중률(현재 AC-006)을 빠뜨렸고, M2(`plan.md:38`)의 "AC-LDBARMAP-004/005"도 같은 누락이었으며, M3(`plan.md:45-46`)의 "AC-LDBARMAP-006"은 아예 다른 것(마디 경계 적중률)을 가리켜 M3 자신이 서술하는 이벤트 재현율(현재 AC-007)과 어긋났다 — 세 곳을 "AC-LDBARMAP-001~006"(M1)·"AC-LDBARMAP-005/006"(M2)·"AC-LDBARMAP-007"(M3, 인용·통과조건 둘 다)로 교정했다. **D-NEW-2(minor)**: `acceptance.md` AC-LDBARMAP-009(다운비트 생산자 0건 기준선)가 무관한 REQ-LDBARMAP-008(네 이벤트-검출-대상 범주 정의)을 인용했다 — REQ-LDBARMAP-001(오프라인 분석 범위, 가장 가까운 간접 연결)로 재지정하고 간접 인용임을 명시했다. 이 교정 뒤 `spec.md`·`plan.md`·`research.md`·`progress.md` 전체를 grep해 다른 AC-LDBARMAP 참조를 전수 재확인했다(research.md·progress.md 0건, plan.md 4건 모두 교정, spec.md의 참조는 전부 이 HISTORY 서술 자신 — 옛 번호를 명시적으로 "구 AC-006"이라 표기하는 역사적 인용뿐). REQ/AC 총량 변경 없음(15/15) — 번호·인용 교정만. |

## §0. Tier 선택 근거

**Tier M.** 이 SPEC의 M1(보정)은 코드를 만들지 않는다 — 후보 검출기를 LOVE ATTACK에 실행하고 채점하는 측정 스크립트만 쓴다(Tier S 범위). 그러나 M2+(다운비트·마디 경계·마디별 이벤트 검출기 채택, 신규 모듈)로 넘어가면 `server/audio/` 아래 신규 모듈 1~2개 + 보정 하네스 스크립트 + 테스트가 생겨 Tier S 상한(5파일/300LOC)을 넘지만, 저장 인터페이스는 §5 열린 결정으로 **이 SPEC이 확정하지 않으므로** Tier L급(design.md 요구) 아키텍처 결정 분량은 아니다. REQ 15개·AC 15개로 Tier M 상한(각 16개) 안에 든다. `research.md`는 이 SPEC이 기존 코드(`analyze.py`)를 깊이 분석하는 plan-phase 서브페이즈 산출물로 Tier와 무관하게 포함한다(§ Plan Phase 서브페이즈 1).

## 1. 배경 — 곡은 BPM 숫자 하나로만 조명에 닿는다

`reports/ldbeat-feasibility-roadmap-20261010.md`(리드, 2026-10-10)가 "없는 것"으로 적은 첫 항목: 「마디 단위 곡 분석 — `analyze.py` 비트 시각은 BPM 계산에만 쓰고 저장 안 함, 다운비트 생산자 0(LDRHYTHM REQ-012 재확인)」. 이 SPEC은 이 보고서 §5 진행 순서의 **②**다 — ① LDBEAT(손으로 짠 LOVE ATTACK 배치를 화면+송신으로 완성) 다음, ③ 역할×마디 자동 배치(SPEC-LDARRANGE-001, 아직 존재하지 않음 — 이 plan-phase에서 `ls .moai/specs/`로 확인) 이전이다.

이 plan-phase가 이 plan-phase 자신의 재측정으로 확정한 것 [잰 값]:

- `grep -rln "downbeat" server` → **0건**(이 plan-phase 재확인, `analyze.py`를 포함한 전체 `server/` 트리). `SPEC-LDRHYTHM-001` §1이 인용한 "다운비트 생산자 0건"과 일치 — 이 공백은 2026-10-03(t502) 이래 바뀌지 않았다.
- `server/audio/analyze.py:352-354` — `librosa.beat.beat_track(...)` 가 돌려주는 `beat_times`는 `_tempo_from_beats(numpy, beat_times)`(`:381-399`, 박 간격의 **중앙값**으로 BPM과 `confidence`를 낸다) 호출 **한 곳**에만 쓰이고, 그 뒤 버려진다 — `AnalysisResult`(`:207-215`, 필드: `bpm, bpm_confidence, boundaries_ms, onsets_ms, rms_curve, d_candidates`)에는 박 시각을 담을 필드가 없다.
- `AnalysisResult.onsets_ms`(`:213`, `:375`)는 필드가 있고 `librosa.onset.onset_detect(...)`(`:355-357`) 결과가 채워진다 — 그러나 **캐시에는 저장되지 않는다**: `.moai/reports/t475/run3/analysis.json`을 이 plan-phase에서 직접 읽은 결과(파이썬으로 키 나열), 저장 키는 정확히 `["sha256", "bpm", "bpm_source", "sections"]` 네 개뿐이다 — `onsets_ms`도, 박 시각도, 다운비트도 없다. 즉 온셋은 `analyze()` 반환값에는 있지만 디스크에 닿기 전에 버려진다.
- 마디 경계 판정(`_boundaries_from_rms`, `:368`)은 BPM을 받아 **구간**(절·후렴 등)을 자르는 데만 쓴다(`_min_segment_ms`, `:402` 이하 — 구간 하한을 "마디 수"로 환산) — 이것은 "**구간**이 몇 마디인가"를 재는 것이지 "**각 마디가 어디서 시작하는가**"를 재는 것이 아니다. 이 SPEC이 메우는 공백은 후자다.

**이 SPEC이 이어받는 후보**: `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a) — 「비트·다운비트·킥 검출 — 지금은 BPM 숫자 하나만 렌더러에 닿는다」(M4+ 범위 **후보**로만 기록되고 확정되지 않은 항목). 이 SPEC은 그 후보를 실제로 설계·검증하는 작업이다. **LDRHYTHM 쪽 파일은 이 plan-phase가 수정하지 않는다** — REQ-LDRHYTHM-012(a)가 "후보"로만 기록한 것을 이 SPEC이 실제로 다룬다는 사실은 LDRHYTHM 쪽에 교차참조 한 줄을 추가하는 **별도 sync 후속 작업**으로 남긴다(§5 플래그 1).

## 2. 이 SPEC의 성격 — 보정(calibration)이 먼저, 채택은 그다음

감독이 `SPEC-LDRHYTHM-001`에서 이미 한 번 확정한 방법론(코드를 먼저 쓰고 실기로 검증받는 순서를 뒤집어, 사람의 판단을 먼저 받는다)을 이 SPEC은 **기계 채점**에 적용한다 — 검출기 후보를 바로 채택하지 않고, LOVE ATTACK 손 분석(`reports/loveattack-music-map-20261006.md`, 이하 "지도 보고서")을 **정답지**로 놓고 먼저 채점한 뒤에야 다음 마일스톤으로 넘어간다. 지도 보고서가 §6에서 스스로 구분한 **[잰 값]**(명령 출력)과 **[추정]**(해석)의 구분을 이 SPEC의 정답지 신뢰도 등급으로 그대로 가져온다 — "잰 값"으로 표기된 항목(BPM·마디별 음량/저역·큰 히트 위치)은 높은 신뢰도 정답, "추정"으로 표기된 항목(구간 이름·비트 드롭 위치)은 낮은 신뢰도 참고로 다룬다(REQ-LDBARMAP-009 근거).

## 3. 요구사항 (GEARS)

### 3.1 R1 — 범위와 보정 게이트 (REQ-LDBARMAP-001~003)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMAP-001 | **The** 마디 지도 기능 **shall** 오프라인(비실시간) 분석으로만 동작한다 — 곡 재생 중 실시간으로 비트·다운비트를 검출해 그 자리에서 타임코드 이벤트를 만드는 것은 범위 밖이다(§4 Out of Scope). | 카드 지시("Real-time detection is OUT of scope"), `SPEC-LDBEAT-001` §4 Out of Scope("오디오 분석 기반 실시간 타임코드 자동 생성")와 동일 경계 |
| REQ-LDBARMAP-002 | [HARD] **While** M1(보정) 마일스톤이 감독 승인을 받지 못한 상태인 동안, 어떤 주체도 LOVE ATTACK 외의 곡에 대한 검출기를 `server/` 아래 프로덕션 코드로 커밋하지 **shall not** — M1 자신도 측정·채점 스크립트만 쓰고 `server/` 아래 어떤 파일도 수정하지 않는다. | `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-002 선례("대본 우선 게이트")를 채점 보정에 적용 |
| REQ-LDBARMAP-003 | **When** M1이 착수되면, 산출물은 **shall** (a) 후보 검출기 2개 이상을 LOVE ATTACK에 실행한 결과, (b) 각 후보를 지도 보고서 대비 채점한 수치표(REQ-LDBARMAP-004의 네 지표), (c) 코드 diff 0줄·콘솔 쓰기 0건을 모두 포함한다. | 카드 지시("milestone 1 = run detector candidates on LOVE ATTACK and score against ground truth before adopting any detector"), `.moai/reports/SPEC-LDBARMAP-001-probes/` 경로(§ module) |

### 3.2 R2 — 채점 철학: 정답지·단위·날조 대조군 (REQ-LDBARMAP-004~007)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMAP-004 | [HARD] **The** 채점 지표 **shall** 다음 네 가지를 지도 보고서(`reports/loveattack-music-map-20261006.md`) 대비 수치로 낸다 — (1) BPM 오차율(목표 112.35 BPM 대비, 단위 %), (2) 다운비트 적중률(허용오차 ±60ms, 단위 % — 매칭 규칙은 REQ-LDBARMAP-005와 동일한 엄격한 순서 대응), (3) 마디 경계 적중률(허용오차 ±60ms, 단위 % — 4/4 박자인 이 곡에서는 다운비트와 같은 사건이지만 별도 지표로 채점한다, 근거 칸 참조), (4) 마디별 변화 이벤트 재현율(REQ-LDBARMAP-008의 네 종류, 지도 보고서 기준 7개 사건, 허용오차 ±1마디, 단위 %). 모든 허용오차는 숫자와 단위를 함께 적는다(REQ-LDBARMAP-007). | 카드 지시("Acceptance = numeric agreement rate ... Define the metric, tolerance and threshold explicitly"); 허용오차 산출 근거: 112.35 BPM → 박 간격 0.534초 → 1/8박 ≈ 67ms, 이 SPEC은 이를 반올림해 60ms로 채택(acceptance.md §A 각주); 지도 보고서 §3(다운비트 근거 — 화성 변화·저역 도약·후렴 히트가 모두 같은 위상을 가리킴, 확신 근거 다수)·부록 A(82마디 다운비트 표) |
| REQ-LDBARMAP-005 | [HARD] **The** 채점 스크립트 **shall** 날조/이동된 마디 지도 두 가지 — (i) 전체를 1박(0.534초) 밀어낸 격자, (ii) 전체를 1마디(2.136초, 4박) 밀어낸 격자 — 를 입력받아 모두 통과선 미달(FAIL)로 판정한다. 채점은 **엄격한 순서 대응(strict index-aligned matching)** 을 쓴다 — 검출된 n번째 마디는 정답지(지도 보고서 부록 A, 1마디부터 번호 매김)의 n번째 마디와만 비교되고, 허용오차 안의 "가장 가까운 아무 정답 마디"를 허용하는 최근접 매칭은 쓰지 않는다 — 그래야 1마디(한 다운비트 주기) 밀린 격자가 "다음 정답 다운비트에 우연히 맞아" 통과선을 넘는 것을 막는다. | `lesson-the-guard-itself-can-be-vacuous.md`(이 저장소 메모리, "검사 자신이 공허할 수 있다"), 카드 지시("Include a negative control ... so the scorer itself is not vacuous"); plan-audit iteration 1 D3(최근접 매칭이면 1마디 밀린 격자가 ≈97% 적중으로 통과할 위험을 지적) |
| REQ-LDBARMAP-006 | **While** BPM을 추정하는 동안, 검출기 **shall** 절반·두 배 후보와의 박자격자 정합도를 비교해 최종 BPM을 채택한 근거를 기록한다 — 원 추정치를 그대로 쓰지 않는다. | 지도 보고서 §한눈에보기 1번("절반(56.17) 격자는 타악이 박에 붙는 비율이 0.34로 떨어진다(112.35 격자는 0.65, 우연 수준 0.20). 두 배(224.69) 격자는 비율이 더 높지만(0.81)... 8분음표 하이햇이 그 격자에 걸리는 것으로 본다"); `lesson-check-the-baseline-before-reading-the-gauge.md`·`lesson-a-fixed-unit-with-a-wrong-input-is-the-same-defect.md`(이 저장소 메모리, BPM 배수 오류 반복 사례) |
| REQ-LDBARMAP-007 | [HARD] **The** 이 SPEC의 모든 산출물(spec.md·plan.md·acceptance.md) 안 문턱값 **shall** 단위(마디·박·밀리초 중 하나)를 숫자와 같은 자리에 명시한다 — 단위 없는 "초" 기준을 음악적 경계에 쓰지 않는다. | `lesson-a-constant-borrowed-across-units-is-silently-wrong.md`(이 저장소 메모리, "초는 음악의 단위가 아니다(3초=1.75마디)"); 카드 지시("Beware ... seconds-vs-bars unit confusion; make the unit ... explicit in every threshold") |

### 3.3 R3 — 검출 대상 (REQ-LDBARMAP-008~009)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMAP-008 | **The** 마디 지도 **shall** 다음 네 종류의 마디별 변화 이벤트를 검출 대상으로 삼는다 — 킥 진입(kick entry, 벌스/후렴 시작의 음량·저역 도약), 빌드업(build, 연속 3마디 이상 음량·저역 상승), 드롭(drop, 보컬 대역이 비고 저역이 강한 구간), 브레이크(break, 킥이 1마디 이상 빠지는 구간). | 카드 요청(beats, downbeats, bar boundaries, and per-bar change events — kick entry, build, drop, break); 지도 보고서 §2.1(빌드업 14~17·42~45, 킥 멈춤 33·61·82), §2.3(드롭 후보 63~66) |
| REQ-LDBARMAP-009 | **The** 채점 시 정답지로 쓰는 지도 보고서의 각 항목 **shall** 그 보고서 §6이 스스로 매긴 신뢰도 갈래(**[잰 값]** / **[추정]** / **[미확정]**)를 그대로 이어받는다 — "잰 값"(BPM·마디별 음량/저역·큰 히트 위치·킥 멈춤 위치)은 높은 신뢰도 정답으로, "추정"(구간 이름·드롭을 63~66마디로 본 것)은 참고로만 쓰고 미달 판정의 유일한 근거로 쓰지 않는다. | 지도 보고서 §6("잰 것과 추정한 것"); `feedback-sheet-values-are-test-data.md`(이 저장소 메모리, 시트 값의 용도 한계) |

### 3.4 R4 — 저장 인터페이스 (열린 결정, REQ-LDBARMAP-010~011)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMAP-010 | [HARD] **The** 마디 지도 산출물의 저장 형태(데이터 모델) 확정 **shall not** 이 plan-phase에서 이루어진다 — (비요구사항 설명: §5 열린 결정 0에 옵션과 트레이드오프만 기록하고, 결정 자체는 M2+ 착수 시 감독과 함께 내린다, REQ-LDBARMAP-011 참조.) | 카드 지시("List the interface as an explicit OPEN DECISION with options ... and the trade-offs; do not pick one"); plan-audit iteration 1 D2(이중 모달 교정 — 원문은 `shall`·`shall not`을 한 문장에 동시에 굵게 표시했다) |
| REQ-LDBARMAP-011 | **The** §5 열린 결정 0 **shall** `SPEC-LDBEAT-001` REQ-LDBEAT-006(타임라인 사전의 새 키로 임베드하는 권고 — `server/web/session.py:3486` `SongTimelineStore`, `:3831`/`:8505` `TimelineDraftHistory`, `server/web/timeline_library.py:48` `SongTimelineLibrary`)을 첫 번째 옵션으로 인용하고, `SPEC-LDARRANGE-001`(아직 `.moai/specs/`에 존재하지 않음 — 이 plan-phase에서 `ls`로 확인)을 장래 소비자로 명시한다. | `SPEC-LDBEAT-001` REQ-LDBEAT-006, `reports/ldbeat-feasibility-roadmap-20261010.md` §SPEC 진행안(순서 3) |

### 3.5 R5 — 교차참조·안전 제약 (REQ-LDBARMAP-012~015)

> **plan-audit iteration 1 D2 교정**: (구)REQ-LDBARMAP-012가 한 문장 안에서 "이어받되(shall) ... 수정하지 않는다(shall not)"를 동시에 굵게 표시하는 이중 모달이었다 — 둘 다 독립적으로 유의미한 구속(승계 의무 vs 소유권 경계)이라 하나로 합치지 않고 REQ-012/013 두 개로 분리했다. 이로 인해 (구)REQ-013(오디오 비커밋)·(구)REQ-014(plan-phase 자신 제약)는 각각 REQ-014·REQ-015로 한 칸씩 밀렸다 — 내용은 바뀌지 않았다.

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDBARMAP-012 | **The** 이 SPEC **shall** `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a)(비트·다운비트·킥 검출 M4+ 범위 후보)를 이어받는다 — 이어받은 사실은 이 SPEC의 sync-phase에서 LDRHYTHM 쪽에 교차참조 한 줄을 추가하는 **별도 후속 작업**으로 남긴다(§5 열린 결정 2). | `SPEC-LDRHYTHM-001` REQ-LDRHYTHM-012(a) |
| REQ-LDBARMAP-013 | [HARD] **The** LDRHYTHM 쪽 파일(`spec.md`/`plan.md`/`acceptance.md`/`progress.md`) **shall not** 이 plan-phase에서 수정된다 — 교차참조 추가는 REQ-LDBARMAP-012가 명시한 sync-phase 후속 작업이 처리하며, 이 plan-phase는 읽기만 한다. | 에이전트 소유권 경계(SPEC artifact ownership — 다른 SPEC 본문은 그 SPEC의 plan-phase 소유) |
| REQ-LDBARMAP-014 | [HARD] **The** 이 작업 **shall not** LOVE ATTACK 원곡 오디오 또는 그 파생 wav/mp3 파일을 이 저장소에 커밋한다 — 원곡은 저장소 밖(`/Users/studiox/Music/AI-Lighting_Console-listen/`) 경로를 참조한다. | 카드 지시("Never commit audio files"), `SPEC-LDRHYTHM-001` §5 플래그 4 선례(LOVE ATTACK 원곡을 의도적으로 저장소 밖에 둠) |
| REQ-LDBARMAP-015 | **The** 이 문서를 작성하는 plan-phase 자신 **shall not** 콘솔에 어떤 커맨드도 보내거나 `server/` 아래 어떤 파일도 수정한다 — 이 plan-phase의 산출물은 `.moai/specs/SPEC-LDBARMAP-001/` 안의 문서 5개뿐이다. | 카드 지시("Plan only — write zero production code, touch no console") |

## 4. 제외 범위 (Out of Scope)

### Out of Scope — 실시간 검출

곡 재생 중 비트·다운비트를 실시간으로 검출해 그 자리에서 타임코드 이벤트 시각을 생성하는 것은 이 SPEC의 범위 밖이다(REQ-LDBARMAP-001). 오프라인(비실시간) 분석만 다룬다.

- 실시간 오디오 스트림 분석, 재생 중 타임코드 이벤트 즉시 생성 로직.

### Out of Scope — 역할×마디 배치 자동 생성

마디 지도(이 SPEC의 산출물)를 입력받아 역할별 배치를 자동으로 짜는 것은 `SPEC-LDARRANGE-001`(아직 존재하지 않음)의 몫이다 — 이 SPEC은 지도만 만든다.

- 역할×마디 배치 자동 생성 알고리즘, AI 제안 카드 로직.

### Out of Scope — 저장 인터페이스 확정

§5 열린 결정 0이 명시하듯, 마디 지도의 저장 형태를 확정하는 것은 이 plan-phase의 일이 아니다(REQ-LDBARMAP-010).

- 신규 저장소 모듈 또는 `timeline` 사전 신규 키 구현.

### Out of Scope — 원곡 오디오·파생물 커밋

LOVE ATTACK 원곡 mp3/wav 및 그 파생 파일을 이 저장소에 커밋하는 것은 범위 밖이다(REQ-LDBARMAP-014).

- 오디오 원본·클릭 트랙 wav 파일의 저장소 커밋.

### Out of Scope — 콘솔 쓰기·`server/` 코드 변경(이 plan-phase 자신)

이 문서를 작성하는 plan-phase 자신은 콘솔에 어떤 커맨드도 보내지 않고 `server/` 아래 어떤 파일도 수정하지 않는다(REQ-LDBARMAP-015).

- 이 plan-phase 세션의 콘솔 접촉(조회·쓰기 모두 포함), `server/` 아래 프로덕션 코드 수정.

## 5. 열린 결정

0. **[열린 결정 — M2+에서 확정] 마디 지도의 저장 인터페이스**(REQ-LDBARMAP-010~011). 두 방향이 있다:
   - **옵션 A — 기존 `timeline` 사전의 새 키로 임베드.** `SPEC-LDBEAT-001` REQ-LDBEAT-006이 박자 격자 데이터에 대해 이미 권고한 방식과 같다 — `server/web/session.py:3486` `SongTimelineStore`(프로세스-전역 현재 타임라인)·`:3831`/`:8505` `TimelineDraftHistory`(되돌리기, 전체 타임라인 사전을 깊은 사본으로 쌓는 generic 메커니즘)·`server/web/timeline_library.py:48` `SongTimelineLibrary`(이름=곡·버전 저장소) 셋이 **코드 추가 없이** 마디 지도 편집의 되돌리기·버전 관리를 덮는다. 단점: 마디 지도가 82마디 × 여러 필드(비트·다운비트·이벤트 타입)로 박자 격자보다 무거울 수 있어, 매 편집마다 전체 사전을 복사하는 `TimelineDraftHistory`의 비용이 커질 수 있다.
   - **옵션 B — 독립 저장소(신규 모듈).** 마디 지도 전용 저장 모듈을 신설한다. 장점: 생명주기(곡당 1개, 버전 거의 없음 — 재분석 시 덮어쓰기)가 `timeline` 사전의 편집 이력과 다르므로 분리가 더 정직할 수 있다. 단점: 신규 코드, `SPEC-LDBEAT-001`·`SPEC-LDARRANGE-001`과의 배선이 추가로 필요하다.
   - 이 plan-phase는 **어느 쪽도 채택하지 않는다.** M2+ 착수 시 감독과 함께 결정한다(REQ-LDBARMAP-010).
1. **마디 지도와 역할×마디 배치(SPEC-LDARRANGE-001, 아직 없음)의 경계.** 이 SPEC은 "지도"(비트·다운비트·마디 경계·마디별 변화 이벤트)까지만 만든다 — 그 지도를 읽어 "역할을 어디에 배치할지" 짜는 것은 후속 SPEC의 일이다. 두 SPEC이 같은 저장 인터페이스(열린 결정 0)를 공유할지는 M2+에서 정한다.
2. **LDRHYTHM 쪽 교차참조는 이 plan-phase의 산출물이 아니다.** REQ-LDBARMAP-012(승계)·REQ-LDBARMAP-013(미수정)이 명시하듯, `SPEC-LDRHYTHM-001` 파일에 한 줄을 추가하는 것은 이 SPEC의 sync-phase 몫이며, 이 plan-phase는 그 작업이 필요하다는 사실만 기록한다.
3. **다운비트와 마디 경계는 이 곡(4/4박자)에서 같은 사건이다.** REQ-LDBARMAP-004가 둘을 별도 지표로 채점하는 이유는 다른 박자(3/4 등)로 확장될 때를 대비한 설계이지, LOVE ATTACK 자체에서 둘이 다른 값을 내리라는 뜻이 아니다 — M1 보정에서 두 지표가 사실상 같은 숫자로 나오면 그것이 정상이다.
