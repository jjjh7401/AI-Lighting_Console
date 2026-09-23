---
id: SPEC-LDDESIGN-001
title: "감독 워크시트 기반 조명 연출 컴파일러 — 컨셉·컬러 스크립트·3층 큐 밀도·회차 에스컬레이션·트래킹/타이밍/MIB"
version: "0.1.0"
status: in-progress
created: 2026-09-21
updated: 2026-09-23
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.0 target"
module: "server/concept/ (신규), server/looks/schema.py, server/looks/songcue.py, server/design/{song_cue_composer,lint,energy,interview,cue_fade,cue_density,cue_sheet_edit}.py, server/web/{session,timeline_draft}.py, server/orchestrator/tools.py, server/director/validate/mib.py, server/director/knowledge_seed/{tracking,staging_cases}.py, server/web/paperwork_api.py, ui/src/components/"
lifecycle: spec-anchored
tags: "lighting-director, concept-layer, color-script, cue-density, chorus-escalation, tracking, timing, mib, worksheet, director-copilot"
tier: L
related_specs: [SPEC-LDRETURN-001, SPEC-LDCLIMAX-001, SPEC-LDACCENT-001, SPEC-COPILOT-SONGSTD-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-CUETIME-001]
depends_on: [SPEC-LDRETURN-001]
---

# SPEC-LDDESIGN-001 — 감독 워크시트 기반 조명 연출 컴파일러

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-21 | 최초 작성. 감독 지적("보고서만으론 무대가 안 바뀜") 후속 — 11편의 오늘 자 보고서(`reports/*-20260921.md`) + 설계 문서(`src/Lighting_Director/AI_Lighting_Copilot_Research_Integration.md`) + 정본(`docs/proposals/song-structure-lighting-standard.md`)을 하나의 실행 가능한 SPEC으로 압축한다. 감독 결정 5건을 전제로 착수(§2.1). |
| 2026-09-21 | **plan-auditor iteration 1 FAIL 대응.** 미해소 클래리피케이션 마커 3건 → plan.md §F 잠정값으로 전환(D1), Tier 예외 §2.4 신설(D2), acceptance.md 검증: 목록 전량 REQ 추적성 보강(D3), REQ-051 조건(2) OR 로직 정정+객석광 제거+SHALL 보강(D4·D6), `_arc_palette` 인용 817→1083행 정정(D5), §2.3 산출물 집합 SSOT 정합화 + design.md 신설(D7), plan.md에 Conditional Design Route 미적용 근거 명시(D8), AC-LDDESIGN-002 문턱값을 v3 실측치 1.0으로 정정(D9), depends_on SPEC-LDRETURN-001 draft 상태 명시(D10). |
| 2026-09-22 | **감독 확인 — M7 대상 화면은 런북 모드.** 감독이 M7 UI 작업 전체가 앱에 이미 존재하는 런북 모드(Runbook Mode) 안의 일이며, grandMA3 콘솔 상태를 비추는 메인 화면은 이 SPEC의 범위 밖임을 확정했다. `src/DESIGN.md`(수령한 디자인, 206행) 대조 결과를 반영: REQ-078을 런북 모드 전제로 재기술(D11), REQ-082의 "기존 12열+2열" 전제를 실측(`CueSheetTimeline.tsx:225` — 이미 14열)으로 정정하고 add/drop 집합을 명시(D12), 런북↔메인 데이터 경계를 REQ-LDDESIGN-086으로 신설(D13), §3.14 말미에 "감독 결정 대기 — 받은 디자인의 범위 확대" 절 신설(D14), AC-LDDESIGN-018·019를 D11·D12·D13에 맞춰 정정(D15), plan.md M7 절 정정(D16). REQ 총량 85→86, §2.4 예외 문구 갱신. |
| 2026-09-22 | **감독 결정 — PLAN CUE 카드 하단의 "수정요청 생성기"를 M7 범위로 확정.** 감독의 결정 사유: 코파일럿에게 대화로 그룹 하나의 색·밝기·프리셋·효과를 바꿔달라고 요청하는 것은 어렵고 직관적이지 않다 — 제안된 큐 카드가 화면에 있으면 무엇을 바꿔야 하는지 이미 보이므로, 그것을 고르고 누르는 것이 자연스러운 입력 경로다. `src/DESIGN.md` §4.5의 "감독 결정 대기" 보류를 해제하고 REQ-LDDESIGN-087~095(9개)로 요구사항화했다(D17). 감독의 재확인: **「일종의 큐 조명연출 수정요청 프롬프트 생성기 — 조명감독이 적기 힘든 프롬프트를 직관적인 선택으로 손쉽게 만들어 주는 용도」다, 그 이상이 아니다.** 명칭을 "PLAN CUE 그룹 편집기"에서 **"PLAN CUE 수정요청 생성기"**로 바꾼다 — "편집기"라는 이름은 구현자가 로컬에서 타임라인을 고치는 코드를 쓰게 만드는 이름이기 때문이다(REQ-087). 타임라인을 직접 고치지 않고, 검증 로직을 UI에 복제하지 않으며(서버 `cue_sheet_edit.py`가 단일 진실 지점, REQ-092), `changes` 매핑은 생성기가 아니라 기존 파서(`parse_cue_sheet_edit_request`)가 만든다(REQ-092). 리뷰 표면은 `src/DESIGN.md:160-161`이 이미 정의한 **변경 스택**(항목별 diff + 상태 라벨 `코파일럿 확인 대기` + 항목에 병기되는 경고)이다 — 별도의 "전송 전 문장 미리보기" 패널은 만들지 않는다(REQ-091). 생성기가 보낸 요청은 감독이 손으로 입력한 요청과 같은 자리(대화 기록)에 같은 형태로 남는다(REQ-094). **측정된 라벨 충돌 정정**: 변경 스택의 취소 버튼이 기존 `CueSheetTimeline.tsx:612`의 `↶ 되돌리기`(`timeline_draft_undo`)와 이름이 겹친다는 것이 실측으로 드러나, 변경 스택 쪽 버튼을 "선택 취소"로 구분하고 서버 미전송을 명시하는 REQ-LDDESIGN-095를 신설했다(3상태 모델 — 선택/요청/초안 반영). 클릭 선택지에 없는 요구를 실어 보내는 자유 입력 한 줄과, 변경 스택 항목별 제거는 승인된 디자인에 없어 REQ화하지 않고 "감독 결정 대기" 절의 제안으로 남긴다. REQ 총량 86→95, §2.4 예외 문구 갱신. |
| 2026-09-22 | **감독 결정 5건 잠금 — §3.14/§3.15의 "감독 결정 대기" 두 절을 해소.** 감독이 오늘 남아 있던 5건 전부를 판정했다: (1) **CUE SHEET는 정확히 14열** — 기존에만 있던 5열(`TC Out`·`Dur`·`Mood`·`Trans`·`Note`) 전부 제거, 19열 과도 상태 언어 삭제(REQ-082 재작성, `Trans` 값의 데이터 모델 존속을 REQ-096으로 신설). (2) **컨셉 패널 "한눈에" 5단계 카드 + 탭 3개 채택** — `src/DESIGN.md` §4.2 전체를 채택, REQ-079/080을 확장하고 REQ-097(5단계 카드 + 파생 원칙)·REQ-098(탭 3개 구조)을 신설. (3) **IBM Plex 웹폰트 미채택, 시스템 폰트로 대체** — `src/DESIGN.md` §2와의 명시적 이탈, `tabular-nums` 완화책을 같은 REQ(099)에 포함. (4) **PLAN CUE 수정요청 생성기 항목별 제거(`✕`) 채택** — REQ-100 신설, REQ-095의 3상태 모델은 불변. (5) **자유 입력 한 줄 채택** — REQ-101 신설, REQ-092 경로 그대로 적용. 5건 반영으로 §3.14/§3.15 말미의 두 "감독 결정 대기" 절이 비어 제거됐고, 신설 REQ 6개(096~101)는 새 §3.16에 모았다. AC-LDDESIGN-019를 14열 확정에 맞춰 재작성하고 AC-LDDESIGN-049~053(5개)을 신설했다. REQ 총량 95→101, AC 총량 48→53, §2.4·acceptance.md 예외 문구 갱신. |
| 2026-09-23 | **비목표 기록 — 색 표현 방식 확장(감독 발의).** 감독 질의("10색만 정의할 필요가 있나, LED 장비는 표현 방법이 많아졌다") 후속 조사를 `docs/proposals/2026-09-23-color-representation-expansion.md`로 남기고, §4에 "색 표현 방식 확장" 절을 신설해 후속 카드 t430~t433(W 채널 구동/젤 번호/CIE 좌표/쇼별 색 사전)로 범위 밖에 둔다. §5에 흰색 웜/쿨 판정이 t430 이전에는 확정되지 않는다는 의존관계를 기록한다. **문서 전용 편집 — REQ 신설 없음.** REQ 총량과 AC 총량은 변하지 않는다(101 / 53). |
| 2026-09-23 | **REQ-062 문장 정정(t438).** 판정 규칙을 "창이 충분하면 dark, 부족하면 mark"에서 "계속 꺼져 있으면 dark / 꺼져 있다가 켜지고 창이 이동+정착 잠정값 이상이면 mark(REQ-063 삽입) / 그 외 live(경고)"로 바로잡았다. 근거: REQ-063(mark일 때 Mark 큐 삽입), `reports/tracking-timing-mib-20260921.md`:70, `server/concept/resolver.py` `mib_verdict`(프로토타입 `final_integrated.py`:114와 같은 규칙). 원래 문장대로면 창이 부족할 때 Mark 큐가 들어갈 자리가 없다. REQ 총량과 AC 총량은 변하지 않는다(101 / 53). |

## 1. 배경

### 1.1 문제 — 보고서만으론 무대가 안 바뀐다

2026-09-21 하루 동안 조사·검증 보고서 11편이 나왔다(§7 참조). 전부 프로토타입
스크립트(`.moai/state/verify/f12e5c95-t429/`, 특히 `final_integrated.py`)로
8곡을 돌린 **실행값**을 갖고 있지만, 아직 저장소 코드가 아니다. 감독의 요구는
명확하다 — 이 실행값들을 실제로 무대에서 볼 수 있는 상태(SPEC → 구현 →
콘솔 검증)로 옮기는 것. 이 SPEC은 그 압축이다: 11편 보고서 + 설계 문서
14개 절 + 정본 §6~§9를 서로 모순 없이 하나의 REQ 집합으로 만든다.

### 1.2 오늘 실측이 보여준 것 (요약 — 상세는 research.md)

- **개선폭**: 후렴 정체성 유지율 실측 0.302(현 업로드 경로, 8곡 평균) →
  0.877(3층 규칙 프로토타입, 동일 8곡). (`lighting-director-verification-
  20260921.md` X1/X3)
- **최종 통합 게이트**: 13개 게이트 × 8곡 = 104칸 — **PASS 98 · n/a 6 ·
  FAIL 0**. (`final-verification-20260921.md`)
- **가장 크게 놓친 것**: §3 컬러 스크립트. 현 코드는 팔레트를 "주색+보조색
  회전"으로만 다루고, `server/web/session.py`의 `_arc_palette`(1083행,
  `origin/main@9dd21171` 실측)가 후렴 회차마다 보조색을 warm white ↔
  magenta로 번갈아 돌린다 — 정체성
  규칙(§4.1)과 **정면으로 충돌**하는 설계가 이미 코드에 들어 있다.
  (`document-gap-audit-20260921.md`)
- **회귀**: 최신 `origin/main`에서 프로덕션 업로드 경로(`tools.py:3230`)는
  후렴 2회 이상인 곡 8곡 중 7곡에서 큐 생성 자체가 실패한다
  (`movement_line_collision`, 카드 **t429**). 수정은 브랜치
  `WT-chorus-collision`(커밋 `4d4cc94f`)에 있고 아직 `origin/main`에
  머지되지 않았다 — 이 SPEC의 M0 선행 조건이다(§3.1).

### 1.3 이 SPEC의 성격 — 설계 문서를 코드로 옮기되, 검증된 부분만

설계 문서(`AI_Lighting_Copilot_Research_Integration.md`) 자신이 §10에서
자기 내용을 3등급(Verified / Practitioner Pattern / Designed Rule)으로
나눈다. 이 SPEC이 REQ로 채택하는 것은 **오늘 프로토타입이 8곡에 대해
실행값으로 확인한 것**(§4.3 최종 검증 보고서 "A. 이번 검증이 실행값으로
증명" 15항목)뿐이다. 콘솔 프로브가 필요한 것(B군)과 감독 입력이 필요하거나
현재 리그·판정기 한계로 보류되는 것(C군)은 §4 비목표로 명시한다.

## 2. 범위 결정

### 2.1 감독이 이미 결정한 것 — 재질문 금지

- 목표 무대는 **콘서트**. 방송(카메라 베이스·인텐디드 샷·테이크 변형)은
  이 SPEC의 범위 밖(§4).
- 콘솔은 **grandMA3 전용**. MA2/Eos/MagicQ 어댑터는 범위 밖.
- 후렴 회차 차별화의 **정본은 §4(정본 v3 규칙 — 이 SPEC이 확정하는 회차
  에스컬레이션 규칙)**로 채택한다. `knowledge_seed/staging_cases.py`의
  스테이징 케이스, `looks/songcue.py`의 사다리(`_HIT_STEP` 회차 순환),
  `docs/proposals/song-structure-lighting-standard.md` §7.1의 아껴두기
  사다리 표는 이 SPEC이 §3.7에서 정의하는 회차 규칙으로 **대체**된다.
- **전면 교체도 별도 앱도 아니다.** 기존 하류(콘솔로 나가는 경로 —
  `cue_fade.py`, `lint.py`의 L1~L14, `energy.py`의 D1~D5, 안전 게이트,
  OSC 송신)는 그대로 재사용한다. 새로 생기는 것은 **상류**(컨셉 입력 →
  동작형 큐 모델 v2)뿐이고, 두 큐 생성 경로(`server/web/session.py` 채팅/웹
  세션 경로와 `server/orchestrator/tools.py:3230` LLM 툴 경로)는 이 SPEC의
  M0에서 단일 컴포저로 합쳐진다.
- 컨셉 입력 방식은 **워크시트(YAML)**. 인터뷰(`server/design/interview.py`
  Q1~Q5, Q2B)는 유지하되, 워크시트가 인터뷰 답변을 자동 초안으로 채우고
  감독이 덮어쓸 수 있는 입력 채널로 둔다(§3.3).

### 2.2 이 SPEC 안에서 새로 결정한 것

두 가지는 오늘 실측으로 이 SPEC이 직접 확정했다(§5의 감독 재확인 대상이
아니라, 실측 데이터 자체가 결론이다):

- 구간 어휘는 판정기 출력(5종)이 아니라 설계 문서 §1.1의 **닫힌 9종
  어휘**로 통일한다 — 판정기 출력은 재매핑 표를 거쳐 9종 중 하나로만
  나간다(§3.2).
- 밀도는 분할 단위(마디 수로 기계적으로 쪼개기)가 아니라 **트리거**로
  정한다 — 8곡 전부에서 분할 단위를 낮추면 같은 구간 안에서 색이 바뀌는
  결함이 재현됐다(`cue-density-8songs-20260921.md`).

### 2.3 Tier와 산출물

Tier L(다중 마일스톤 · 다중 파일 · UI 변경 포함). SSOT(`spec-workflow.md`
§ SPEC Complexity Tier)의 Tier L plan-phase 산출물 집합은 정확히
`spec.md` + `plan.md` + `acceptance.md` + `design.md` + `research.md`
5개다 — `design.md`는 run-phase로 미뤄지는 것이 아니라 그 자체가
plan-phase 산출물이다. 이 SPEC은 그 5개 전부를 plan-phase 저작 시점에
만든다: `design.md`는 UI 구성·컨셉 패널·큐 모델 v2 타입 개요를 담는
간결한(≤120행) 별도 파일이다. `spec-compact.md`는 SSOT 5종에 더해진
**추가** 요약 산출물이며, SSOT 집합을 대체하지 않는다. `progress.md`는
Tier와 무관한 별개 개념(모든 Tier 공통 run-phase 추적 파일)으로,
run-phase 진입 시 신설된다.

### 2.4 티어 예외 — 단일 SPEC 통합

이 SPEC은 REQ-LDDESIGN-001~101(101개, 2026-09-22 CUE SHEET 14열 확정·
컨셉 패널 한눈에+탭 3개·시스템 폰트+tabular-nums·PLAN CUE 수정요청
생성기 항목별 제거·자유 입력 한 줄 5건 반영으로 REQ-LDDESIGN-096~101
신설 이전 95개, 그 이전 PLAN CUE 수정요청 생성기 신설 이전 86개, 그
이전 85개)를 한 문서에 둔다 — Tier L 상한 25개의 4.04배다. 이것은
감독 지시(2026-09-21,
"지금까지 모든 내용을 정리해서 포함시키고 스펙문서로")에 따른
**명시적 예외**이지, Tier 분류의 누락이 아니다.

일반적으로 상한 초과는 SPEC 분할 신호이지만, 이 경우 분할은 감독의
명시적 지시(전부를 하나의 스펙 문서로)와 정면으로 충돌한다. 대신 이
SPEC은 **plan.md의 M0~M8 마일스톤이 sub-SPEC 역할**을 하도록 구조화됐다
— 각 마일스톤은 독립적으로 시작·검증·병합 가능한 단위이고(§C 각
마일스톤의 파일 목록·REQ 범위가 서로 배타적이다), run-phase 실행 단계에서
마일스톤별로 `moai todo` 카드를 발행해 실제 작업 단위를 분할한다(칸반
큐 카드 1개 = 마일스톤 1개, `kanban-dispatch.md` § 카드 클래스의 C —
설계 변경 — 적용). 문서는 하나, 실행 단위는 아홉이다.

## 3. 요구사항

REQ 번호는 이 SPEC 전체에서 연속이다(절 단위로 다시 시작하지 않는다).
각 REQ는 어느 게이트(G1~G13, `final-verification-20260921.md` 정의)가
그것을 검증하는지 `[G#]`로 표시한다. 게이트가 없는 REQ(배선·구조 요구)는
표시를 생략한다.

### 3.1 선행 조건 — M0 (REQ-LDDESIGN-001~004)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-001 | **Where** `WT-chorus-collision`(커밋 `4d4cc94f`)의 후렴 재정렬 액센트 제거 수정이 `origin/main`에 머지되어 있지 않으면, 이 SPEC의 M1 이후 마일스톤은 **SHALL NOT** 착수한다 — 후렴 2회 이상 곡 8곡 중 7곡이 큐 생성 자체에 실패하는 트리(카드 t429) 위에 새 계층을 얹으면 검증이 무의미하다. | `lighting-director-verification-20260921.md` X1, 카드 t429 |
| REQ-LDDESIGN-002 | **When** M0이 완료되면, `server/orchestrator/tools.py:3230`(`prepare_songcue` 핸들러, 2954행)의 `build_songcue_bundle(...)` 호출은 **SHALL** `bpm=density_bpm`(이미 `tools.py:3177`에서 계산됨)을 실제로 전달한다 — SPEC-LDRETURN-001이 확보한 값 충돌 회피 경로 위에서 절정 지속시간 상한이 프로덕션에서 처음 발동한다. **Where** SPEC-LDRETURN-001의 `status`가 이 REQ 착수 시점에도 `completed`가 아니면(현재 `draft`), M0은 **SHALL** 그 SPEC의 완료를 대기하거나, 원인을 로그(`.moai/logs/depends-on-override.log`)에 남긴 명시적 override로만 진행한다 — 조용히 우회하지 않는다. | `lighting-director-upgrade-20260921.md` 로드맵 0, SPEC-LDRETURN-001 §4 Out of Scope("후속 SPEC이 bpm=density_bpm 한 줄만 추가하면 배선이 끝난다"), `spec-workflow.md` § Depends_on Pre-flight Check |
| REQ-LDDESIGN-003 | **When** 곡 큐가 생성되면(채팅/웹 세션 경로 `server/web/session.py`의 확정 단계, LLM 툴 경로 `server/orchestrator/tools.py:3230` 둘 다), 두 경로는 **SHALL** 이 SPEC이 §3.4에서 정의하는 단일 컴포저(`server/design/song_cue_composer.py` 확장, 또는 그 자리를 대체하는 신규 모듈)를 거친다 — `server/looks/songcue.py`의 사다리 로직(`_arc_palette`·회차 사다리)은 데이터(§3.7 회차 규칙)로 흡수되고 별도 코드 경로로 남지 않는다. | `lighting-director-upgrade-20260921.md` 구조적 문제 1, 로드맵 1 |
| REQ-LDDESIGN-004 | **When** M0~M6이 완료되면, `server/web/session.py`의 `_arc_palette`(1083행, `origin/main@9dd21171` 실측)와 `_per_chorus_palette`(1124행, `per_chorus` 색 운용 분기)는 **SHALL** 더 이상 후렴 회차마다 보조색을 회전시키지 않는다 — §3.4의 컬러 규칙(정체성 유지 + 회차 회전 폐기)으로 대체된다. | `document-gap-audit-20260921.md` §3 표, `_arc_palette` 실측 (blue,warm white)(blue,magenta) 반복 |

### 3.2 닫힌 어휘 재매핑 (M1) (REQ-LDDESIGN-005~010) `[G1]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-005 | **The** 구간 어휘는 **SHALL** 정확히 9종으로 닫힌다 — Intro · Verse · Pre-Chorus · Chorus · Post-Chorus · Bridge · Rap/Solo/Dance Break · Final Chorus · Outro(문서 §1.1). 이 9종 밖의 이름이 워크시트나 조립 결과에 나타나면 조립은 **SHALL** 거부한다(`VocabError` 계열 예외). | `vocab-closed-verification-20260921.md`, 문서 §1.1 |
| REQ-LDDESIGN-006 | **The** 트리거 어휘는 **SHALL** 문서 8항목(보컬 시작/종료, 악기 추가/제거를 각각 독립 토큰으로 분리해 실제로는 10토큰)으로 닫힌다 — 코드·조성 변화, 빌드업 시작, 드롭 직전의 정적, 핵심 가사, 안무 대형 변화, 중심 멤버·솔로 변경. | 문서 §1.1, `vocab-closed-verification-20260921.md` 한계 절 |
| REQ-LDDESIGN-007 | **The** 원샷 어휘는 **SHALL** 정확히 7종으로 닫힌다 — Kick·Snare·Cymbal accent · Dimmer bump · White hit · 짧은 Strobe · Color bump · Position snap · Blinder hit. | 문서 §1.1 |
| REQ-LDDESIGN-008 | **When** 구간 판정기(현 5종 출력 — 최고 D레벨 기준)가 구간 이름을 내면, 재매핑 계층은 **SHALL** 그것을 9종 어휘 중 하나로 변환하고 원래 판정기 이름을 보존한다(예: 마지막 Chorus → Final Chorus, `Finale` → Outro). Post-Chorus·Rap/Solo/Dance Break·Pre-Chorus는 판정기가 직접 못 내므로, Pre-Chorus는 규칙(§3.6 빌드업 삽입)이 끼워 넣고 나머지 둘은 워크시트에서 감독이 지정한다. | `document-gap-audit-20260921.md` §1, `vocab-closed-verification-20260921.md` §"어휘가 못 채우는 자리" |
| REQ-LDDESIGN-009 | **When** 구간이 재매핑되거나(REQ-008) 규칙이 새 구간(빌드업 Pre-Chorus 등)을 삽입하면, 그 큐는 **SHALL** 화면과 큐시트 출력에 "감독 확인" 표시를 명시적으로 노출한다 — 조용히 넘어가지 않는다. | `vocab-closed-verification-20260921.md`, 문서 §11 "[공개 근거 없음]" 관행과 같은 방향 |
| REQ-LDDESIGN-010 | **Where** 워크시트의 트리거 칸에 오디오 분석으로 검출 불가능한 항목(코드·조성 변화, 핵심 가사, 안무 대형 변화, 중심 멤버·솔로 변경 — 4종)이 필요하면, 그 입력은 **SHALL** 감독이 워크시트에 직접 적는 자유 선택지로만 존재하고 자동 생성되지 않는다. | `vocab-closed-verification-20260921.md` §"채우는 곳" |

### 3.3 워크시트 YAML 스키마 (M1) (REQ-LDDESIGN-011~016)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-011 | **The** 워크시트는 **SHALL** YAML 파일로 입력받으며 최소 다음 4개 최상위 구획을 갖는다 — `palette`(§3.4 팔레트 4칸), `concept`(컨셉 인과 불릿), `sections`(구간·트리거·원샷 줄), `notes`(자유 메모). | 감독 확정(2026-09-21) — "컨셉 입력은 YAML 워크시트" |
| REQ-LDDESIGN-012 | **The** `palette` 구획은 **SHALL** 정확히 4개 필드를 갖는다 — `primary`(주색), `secondary`(보조색), `climax`(클라이맥스 색), `reserved`(유보색 목록, 기본값은 `climax`와 동일). | `apply-candidates-20260921.md` C1, 문서 §2.1 Micro Concept |
| REQ-LDDESIGN-013 | **The** `concept` 구획은 **SHALL** 인과 관계를 기입하는 자유 문장 필드(예: "이 곡은 → 그래서 주조색 → 분위기 → 그래서 효과")를 갖는다 — 이 문장은 UI 컨셉 패널의 인과 불릿(§3.14)을 만드는 원천이다. | 감독 UI 요구 — "연출 설명은 인과 불릿" |
| REQ-LDDESIGN-014 | **The** `sections` 구획의 각 줄은 **SHALL** 최소 다음 필드를 갖는다 — `section`(9종 어휘 중 하나, REQ-005), `occurrence`(회차 번호, 정수), `trigger`(트리거 어휘 또는 생략, REQ-006), `operation`(§3.5 동작 어휘), `memo`(자유 텍스트, 선택). | `vocab-closed-verification-20260921.md` Rain 문서 어휘 큐시트 |
| REQ-LDDESIGN-015 | **The** `sections` 구획은 원샷을 별도 하위 목록 `one_shots`로 **SHALL** 가지며, 각 항목은 `shot`(원샷 어휘 중 하나, REQ-007), `anchor_section`, `anchor_occurrence`, `at`(구간 내 상대 위치 서술 또는 초)를 갖는다. | `cue-density-director-view-20260921.md` §"원샷 8" |
| REQ-LDDESIGN-016 | **When** 워크시트의 `section`·`trigger`·`operation`·`shot` 필드에 각 어휘(REQ-005~007, §3.5)에 없는 값이 오면, 워크시트 로더는 **SHALL** 조립을 거부하고 어느 필드에 어떤 값이 왔는지 명시한 오류를 낸다(`memo`/자유 메모 필드는 이 검사 밖이다). | 감독 확정 — "그 밖의 이름은 스크립트가 거부" |

### 3.4 큐 모델 v2 (M2) (REQ-LDDESIGN-017~025)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-017 | **The** 큐 모델 v2는 **SHALL** 다음 필드를 기존 스키마(`server/looks/schema.py`의 3밴드 속성)에 얹는다 — `layer`(§1.2 5레이어 중 하나 이상), `operation`(§3.5), `tracking`(§3.9), `timing`(§3.10), `evidence`(§3.13), `headroom`(§3.8), `mib`(§3.11). 3밴드 속성 값 자체(Dimmer/ColorRGB/Pan·Tilt/Zoom·Iris)와 리그 바인딩 시점은 이 SPEC이 건드리지 않는다. | `final-verification-20260921.md` 요구사항 A.3, 문서 §8.2 데이터 모델 |
| REQ-LDDESIGN-018 | **The** `layer` 필드는 **SHALL** 문서 §1.2의 5종 중 하나 이상을 값으로 갖는다 — Visibility/Camera Base · Environment · Architecture · Motion · Punctuation. 구간 전환 큐는 레이어 2~3개까지, 프레이즈 전환 큐는 1~2개까지, 비트 액센트 큐는 Punctuation 1개만 허용한다(초과 시 린트 경고, §3.13). | 문서 §1.2 |
| REQ-LDDESIGN-019 | **The** `operation` 필드는 **SHALL** 다음 9종 중 하나다 — `retain`(유지) · `add`(더함, 상한은 기존 값과의 최대값) · `remove`(그룹 끄기, 값을 0으로) · `reduce`(감소, REQ-021의 기준 상태 참조) · `replace`(색 교체) · `isolate`(지정 역할만 남기고 나머지 0) · `expand`(확장, 절대값 지정) · `restore`(REQ-020) · `release`(제어 반환, 값 지정 가능). | `final-verification-20260921.md` 요구사항 A.3, `chorus-escalation-audit-20260921.md` "개선사항 4" (remove 추가) |
| REQ-LDDESIGN-020 | **When** 큐가 `restore` 동작을 수행하면, 대상은 **SHALL** 참조하는 기준 구간(`ref`)의 디머·**색**·모션을 함께 복원한다 — 포지션은 제외한다(SPEC-LDRETURN-001 §4 Out of Scope와 같은 방향으로, 이 SPEC의 `restore`도 값 넛지가 아니라 명시적 기준 재현이지만 포지션은 §3.11 MIB의 어두운 창 규칙을 따로 거친다). | `chorus-escalation-audit-20260921.md` 개선사항 1 — "복원은 색을 포함한다"(색 누락이 8곡 중 4곡에서 언더페인팅 색이 후렴으로 새는 결함을 일으켰다) |
| REQ-LDDESIGN-021 | **When** 큐가 `reduce` 동작을 수행하면, 감소 배율은 **SHALL** 직전 트래킹된 큐 값이 아니라 그 구간의 **기준 상태**(첫 회차 `restore` 대상 또는 구간 자신의 1회차 값)를 참조한다 — 상대 감소가 연쇄로 겹쳐 곱해지지 않는다. | `tracking-timing-mib-20260921.md` "함정 하나 더" — Too Cool 절 밝기 50→25→12로 겹쳐 곱해짐 실측 |
| REQ-LDDESIGN-022 | **The** `evidence` 필드는 **SHALL** 4등급 중 하나를 갖는다 — `verified`(정본·실측 페이드 규칙 등), `practitioner_pattern`(회차 확장·빌드업 등 실무 관행), `designed_rule`(이 SPEC이 새로 구성한 규칙), `director`(구간 판정기 출력을 그대로 옮긴 경우). 문서 §10의 3등급(Verified/Practitioner Pattern/Designed Rule)에 `director`를 더한 것이며, 구간 판정기 출력 자체는 감독의 확정 데이터가 아니라 사용자가 넣은 원 데이터이므로 별도 등급이 필요하다. | 문서 §10, `apply-candidates-20260921.md` C8 |
| REQ-LDDESIGN-023 | **When** 큐 조립이 완료되면, 각 큐는 **SHALL** 자동 생성된 `description`(자연어 한 문장 이상, §3.13)을 갖는다 — 복원 대상, 추가/제거된 그룹, 색 변화, 최대 밝기, 남겨둔 자원(§3.8 헤드룸)을 포함한다. | `apply-candidates-20260921.md` C7, 문서 §2.2 "좋은 Cue Description은 분위기 이름보다 연산이 명확하다" |
| REQ-LDDESIGN-024 | **The** `timing` 필드는 **SHALL** 최소 `kind`(Snap/Short/Long 중 하나, §3.10), `seconds`(초), `attr_split`(색·밝기 등 축별 분리 여부, 불리언 또는 축 목록), `stagger`(순차 딜레이 서술 또는 `null`)를 갖는다. | 문서 §5.4, `tracking-timing-mib-20260921.md` |
| REQ-LDDESIGN-025 | **The** `headroom` 필드는 **SHALL** §3.8이 정의하는 4축 계산 결과(미사용 그룹 수·유보색·유보 효과·남은 단계)를 매 구간 큐마다 담는다. | 문서 §4.4, `chorus-escalation-audit-20260921.md` |

### 3.5 컨셉 계층·컬러 규칙 (M3) (REQ-LDDESIGN-026~035) `[G6][G7]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-026 | **The** 컨셉 계층(`server/concept/`, 신설)은 **SHALL** OSC·콘솔 접근을 하지 않는 순수 데이터 계층으로, 워크시트의 `palette`·`concept`를 입력받아 Color Strip(구간별 주색·보조색·최대 밝기·켜진 그룹 비율=면적·의도 한 문장)을 산출한다. | `lighting-director-upgrade-20260921.md` 로드맵 4, `document-gap-audit-20260921.md` 구체안 2 |
| REQ-LDDESIGN-027 | **When** 유보색(`palette.reserved`)이 설정되면, 그 색을 쓰는 큐는 **SHALL** 그 색이 명시적으로 해제되는 큐(보통 Final Chorus 또는 정책상 지정된 구간) 이전에 나타나지 않는다 — 위반 시 컬러 검사는 실패로 기록된다(G6). | `apply-candidates-20260921.md` C1 8곡 실측 유보색 조기 등장 0/8, `document-gap-audit-20260921.md` 규칙셋 (a) |
| REQ-LDDESIGN-028 | **Where** 후렴(Chorus/Final Chorus) 구간이 3회 이상 반복되면, 클라이맥스 색(`palette.climax`)은 **SHALL** 그 클라이맥스 색이 정식 등장하는 구간보다 앞선 구간에 채도를 낮춘 형태(언더페인팅)로 최소 1회 심긴다 — 후렴 3회 미만인 곡(예: Ice cream)에는 이 규칙을 적용하지 않는다. | `document-gap-audit-20260921.md` 규칙셋 (b), `cue-density-8songs-20260921.md` 결론 3 — "마지막 후렴 흰색 전환은 후렴이 3개 이상일 때만"(Ice cream 규칙 구멍) |
| REQ-LDDESIGN-029 | **The** 인접한 두 구간 큐는 **SHALL** 공통색을 최소 1개 유지한다(브리지) — 위반은 컬러 검사 실패로 기록된다(G6). 단 두 구간이 켜진 그룹 집합을 전혀 공유하지 않으면(예: 완전한 암전 전환) 이 규칙은 적용하지 않는다. | `document-gap-audit-20260921.md` 규칙셋 (c) |
| REQ-LDDESIGN-030 | **The** 후렴(Chorus) 구간 전체는 **SHALL** 동일한 주색을 유지한다(Final Chorus의 클라이맥스 색 전환은 예외) — 8곡 실측 전부 후렴 주색 동일(`apply-candidates-20260921.md` C1 표). | `apply-candidates-20260921.md` C1, G7 정의 |
| REQ-LDDESIGN-031 | **When** 컨셉 계층이 컴파일되면, `server/web/session.py`의 `_arc_palette`(회차마다 보조색 2색 순환)와 `_per_chorus_palette`("한 번에 하나씩" per_chorus 6색 순환, Q2B)는 **SHALL** 후렴 정체성 판정(REQ-030) 경로에서 더 이상 호출되지 않는다 — 회차 축은 색이 아니라 §3.7의 그룹 수·면적·밝기·모션으로 표현한다. | `document-gap-audit-20260921.md` §3 표 마지막 행, §4.1 원칙과 직접 충돌 실측 |
| REQ-LDDESIGN-032 | **The** 워크시트 `concept` 필드는 **SHALL** UI 컨셉 패널(§3.14)의 인과 불릿 원문으로 그대로 노출된다 — 컴파일 과정에서 요약·재작성되지 않는다. | 감독 UI 요구 |
| REQ-LDDESIGN-033 | **The** Color Strip은 **SHALL** 구간 큐(프레이즈·원샷 큐 제외)만을 대상으로 산출한다 — UI 타임라인 띠 색(§3.14)이 이 스트립을 직접 그린다. | `cue-density-director-view-20260921.md` "컬러 스트립(구간 큐만)" |
| REQ-LDDESIGN-034 | **Where** 워크시트에 의상·세트·LED·피부톤 등 고정 제약이 입력되지 않으면, 컨셉 계층은 **SHALL** 그 제약을 빈 값으로 처리하고 관련 린트 규칙(문서 §7.5류 색-피부톤 경고)은 평가하지 않는다 — 안 재고는 안 쓴다. | `document-gap-audit-20260921.md` 구체안 5, 문서 §3.2 절차 3 |
| REQ-LDDESIGN-035 | **The** 컨셉 계층은 **SHALL** 팔레트 4칸(REQ-012)을 워크시트가 아예 채우지 않았을 때, 인터뷰 경로(Q1~Q5, Q2B)의 기존 답변을 자동 초안으로 채워 넣는다 — 인터뷰는 폐기되지 않고 워크시트의 기본값 생성기로 남는다. | 감독 결정 — "인터뷰(`design/interview.py`) 유지, 워크시트가 자동 초안" |

### 3.6 3층 큐 밀도 (M4) (REQ-LDDESIGN-036~041) `[G8][G13]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-036 | **The** 큐 밀도는 **SHALL** 세 층으로 구성된다 — 구간 층(Look 전환, 9종 어휘 각 발생마다 1큐), 프레이즈 층(Cue, 워크시트 트리거 한 줄당 1큐), 원샷 층(Effect, 별도 임시 실행기 — 시퀀스 큐로 세지 않는다). 분할 단위(마디 수로 기계적 분할)를 밀도 결정 수단으로 쓰지 않는다. | `cue-density-director-view-20260921.md` 스펙 요구사항 1, `cue-density-8songs-20260921.md` 결론 2 |
| REQ-LDDESIGN-037 | **When** 후렴(Chorus 또는 Final Chorus) 구간에 진입하고, 그 직전 구간이 후렴이 아니며 그 직전 구간의 길이가 일반 후렴 기준 5마디 이상(Final Chorus 직전은 3마디 이상)이면, 컴파일러는 **SHALL** 그 후렴 진입 전에 빌드업 프레이즈 큐(Pre-Chorus, 트리거 "빌드업 시작")를 삽입한다 — 일반 후렴은 4마디 전, Final Chorus는 2마디 전 지점에 놓는다. | `cue-density-director-view-20260921.md` 스펙 요구사항 2, `apply-candidates-20260921.md` "앞 구간이 후렴이면 빌드업 없음" 정정, `final-verification-20260921.md` G8 |
| REQ-LDDESIGN-038 | **When** 마지막 후렴(Final Chorus)과 Outro 사이의 간격이 3마디 이상이면, 컴파일러는 **SHALL** Outro 진입 직전 1마디 지점에 눈 리셋 프레이즈 큐(밝기를 대폭 낮춤, 트리거 "드롭 직전의 정적")를 삽입한다. | `cue-density-director-view-20260921.md` "피날레 앞 눈 리셋" |
| REQ-LDDESIGN-039 | **The** 프레이즈 큐는 **SHALL** 그 구간 Look의 레이어 1~2개만 바꾼다(REQ-018) — 구간 큐가 이미 확정한 나머지 레이어는 건드리지 않는다. | 문서 §1.2, `cue-density-director-view-20260921.md` 스펙 요구사항 3 |
| REQ-LDDESIGN-040 | **The** 원샷은 **SHALL** 시퀀스 큐 목록(§3.6 구간+프레이즈 큐)과 별도의 원샷 레인에 기록되며, `evidence`(REQ-022)·`headroom`(REQ-025) 계산 대상에서 제외된다 — 큐 밀도 게이트(G13)도 시퀀스 큐만 센다. | `cue-density-director-view-20260921.md` 스펙 요구사항 4, `final-verification-20260921.md` G13 정의("시퀀스 큐 10~45") |
| REQ-LDDESIGN-041 | **The** 시퀀스 큐(구간+프레이즈) 총 개수는 **SHALL** 곡당 10~45개 범위를 기본 기대값으로 한다 — 정본 §9(구간 수 중앙값 10 부근)와 8곡 실측 분포(13~44)를 근거로 한다. 이 범위를 벗어나면 G13 게이트가 실패로 기록되지만, 조립 자체를 막지는 않는다(경고). | 정본 §9, `final-verification-20260921.md` G13, 8곡 실측 |

### 3.7 §4 회차 에스컬레이션 정본 (M4) (REQ-LDDESIGN-042~049) `[G2][G3][G4][G5]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-042 | **When** 후렴(Chorus 2 이상)이 반복되면, 정체성 축(REQ-030 주색, 핵심 포지션, 대표 모티프 — 최소 2종)은 **SHALL** 이전 후렴과 동일하게 유지된다(`restore` 동작, REQ-020) — Final Chorus는 이 정체성 판정에서 항상 유지로 간주한다(클라이맥스 색 전환은 의도된 예외). | 문서 §4.1, `final-verification-20260921.md` G2 정의 |
| REQ-LDDESIGN-043 | **When** 후렴이 반복되면, 각 회차 전환은 **SHALL** 다음 6개 축 중 최소 1개를 새로 확장한다 — 기구군 수, 무대 면적(켜진 그룹 비율), 밝기, 모션 단계, 포지션 방향, 큐 밀도(그 후렴 안의 프레이즈 큐 수). 5회차까지는 새 축이 0인 회차 쌍이 있으면 안 된다(G3). | `chorus-escalation-audit-20260921.md` §4.2 표, G3 정의 |
| REQ-LDDESIGN-044 | **When** 회차 번호가 증가하면, 모션 단계(0~3)는 **SHALL** 전체 후렴 수에 비례해 분배된다(마지막 회차 이전에 최대치에 도달하지 않도록) — 회차 4에서 이미 최대 모션을 쓰면 피날레에 새로 더할 축이 남지 않는다. | `chorus-escalation-audit-20260921.md` 개선사항 3 — v2에서 4곡이 피날레 전 남은 모션 단계 0을 실측 |
| REQ-LDDESIGN-045 | **Where** 후렴이 4회 이상 반복되면, 4회차 이후의 프레이즈 큐는 **SHALL** 후렴당 최대 1개로 제한한다 — 후렴 판정기 과분할(예: Too Cool 13회)이 있어도 밀도가 무한정 늘지 않는다. | `final-verification-20260921.md` "규칙 결함 넷을 추가로 고침" ④ |
| REQ-LDDESIGN-046 | **When** Bridge(또는 Pre-final) 구간에 진입하면, 그 구간의 큐는 **SHALL** `remove` 동작(REQ-019)으로 KEY·BACK을 제외한 그룹을 전부 끄고, 남은 그룹(KEY·BACK)은 밝기 30% 수준으로 축소한다 — 밝기만 줄이고 그룹은 그대로 두는 것(v1의 결함)을 반복하지 않는다. | `chorus-escalation-audit-20260921.md` 개선사항 4, §4.3 "Bridge / Pre-final: 밝기·움직임·기구 수를 의도적으로 제거" |
| REQ-LDDESIGN-047 | **When** Bridge 큐의 감소 여부를 헤드룸 경고(§3.8)로 판정하면, 비교 기준은 **SHALL** 그 큐 직전의 "브릿지가 아닌 구간"이다 — 브릿지가 끄기 큐와 켜기 큐 두 개로 나뉘었을 때 두 번째 큐를 첫 번째 큐와 비교해 "감소 아님"으로 오탐하지 않는다. | `chorus-escalation-audit-20260921.md` 결론 — "검사는 큐 단위가 아니라 구간 단위로 비교해야 한다" |
| REQ-LDDESIGN-048 | **When** Final Chorus에 도달하면, 그 큐는 **SHALL** 모티프를 명시적으로 회수(`restore`, REQ-020)하고, 최소 1개의 새 축(REQ-043)을 더하며, 헤드룸 계산상 직전 구간에 남은 모션 단계가 1 이상이어야 한다(G4). | 문서 §4.3, `final-verification-20260921.md` G4 정의 |
| REQ-LDDESIGN-049 | **Where** 후렴이 6회 이상 반복되면(회차 상승 축이 이미 소진된 이후), 컴파일러는 **SHALL** 같은 상태를 유지하는 것을 결함이 아닌 정상으로 간주한다 — §4.1이 반복 자체를 허용한다. (근본 원인은 구간 판정기 과분할이며, 이 SPEC의 §4 비목표로 남긴다.) | `chorus-escalation-audit-20260921.md` 개선사항 6 |

### 3.8 헤드룸 4축 (M4) (REQ-LDDESIGN-050~052) `[G5]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-050 | **The** 헤드룸 계산은 **SHALL** 매 구간 큐마다 4축을 산출한다 — 미사용 기구 그룹 수, 유보색 목록(아직 등장하지 않은 유보색), 유보 효과 목록(BLIND·STROBE 등 아직 해제되지 않은 효과), 남은 상승 단계(모션·밝기 중 도달 가능한 최대치까지 남은 거리). | 문서 §4.4 YAML 예시 |
| REQ-LDDESIGN-051 | **When** 다음 4조건 중 하나라도 성립하면, 헤드룸 검사는 **SHALL** 경고를 기록한다(G5 실패) — (1) Intro에서 전체 기구 그룹이 이미 켜짐, (2) Chorus 1에서 블라인더 또는 스트로브가 켜져 있거나 색이 순백임(BLIND·STROBE 중 하나라도 켜짐 **OR** 색이 흰색 — AND가 아니라 OR, `final_integrated.py`의 `{'BLIND','STROBE'}&set(c1['on']) or c1['color']=='흰색'` 로직 그대로; "객석광"은 조건 요소가 아니다 — §4 비목표(C군), 현재 리그 18그룹에 없다), (3) Bridge에서도 밝기·그룹 수가 줄지 않음(REQ-047의 구간 단위 비교 적용), (4) Final Chorus에 추가 가능한 새 축이 없음(REQ-048과 같은 조건). | 문서 §4.4 경고 조건 4개, `final_integrated.py` `G['G5 헤드룸 경고 0']` 산정 로직(`w[1]`) |
| REQ-LDDESIGN-052 | **The** 헤드룸 경고는 **SHALL** 조립을 막지 않는다 — 큐시트와 UI 상태줄(§3.14)에 경고로만 노출된다. | `final-verification-20260921.md` G5, 감독 확정 방향("조용히 넘어가지 않는다" — 차단이 아니라 명시) |

### 3.9 트래킹 (M5) (REQ-LDDESIGN-053~057) `[G9]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-053 | **The** `tracking` 필드(REQ-017)는 **SHALL** 4모드 중 하나다 — `Block`(전체 상태 명시, 트래킹 사슬 끊음), `Track`(변경 축만 저장, 이전 값 유지), `Cue Only`(그 큐에서만 적용, 다음 큐로 전파하지 않음), `Release`(제어 반환, 이후 값은 다른 Playback의 기본값을 따름). | 문서 §5.3 |
| REQ-LDDESIGN-054 | **The** 곡의 첫 큐(안전 큐, §3.12)는 **SHALL** `Block`이고, 곡의 마지막 큐(안전 큐)는 **SHALL** `Release`다 — 앞 곡의 색·고보·프리즘·모션·페이저 잔존을 차단하고 종료 시 제어권을 반환한다. | 문서 §5.3 정책, `apply-candidates-20260921.md` C4 |
| REQ-LDDESIGN-055 | **The** 구간 큐(Look 전환)는 **SHALL** 기본값 `Track`이다. | 문서 §5.3 |
| REQ-LDDESIGN-056 | **The** 프레이즈 큐(빌드업·눈 리셋 등 일시적 수정)는 **SHALL** 기본값 `Cue Only`다 — `Track`으로 두면 그 구간이 끝난 뒤에도 값이 다음 구간으로 새어 나간다(8곡 중 6곡에서 실측). | `tracking-timing-mib-20260921.md` — "프레이즈 큐를 Track으로 두면 8곡 중 6곡에서 누출" |
| REQ-LDDESIGN-057 | **When** `Cue Only` 큐가 적용되면, 그다음 큐는 **SHALL** 그 `Cue Only` 큐 이전의 트래킹 상태에서 계산을 시작한다 — 해석기가 이 경계를 보장한다(G9). | `final-verification-20260921.md` G9 정의 |

### 3.10 타이밍 (M5) (REQ-LDDESIGN-058~061) `[G11]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-058 | **The** `timing.kind`(REQ-024)는 **SHALL** 트리거 종류에 따라 기본값이 배정된다 — 드롭·히트·백색 플래시류는 `snap`(0~0.3초), 프레이즈 전환(악기 추가 등)은 `short`(1~2초), 발라드성 공간 확장·아웃트로는 `long`(2~4초), 좌우 파동·중앙→외곽 확산은 순차(`stagger`) 값이 함께 붙는다. | 문서 §5.4 음악적 의미표 |
| REQ-LDDESIGN-059 | **When** 후렴 진입 큐가 생성되면, `timing`은 **SHALL** `kind: snap`과 `stagger`(중앙→외곽 0→0.4초 기본값)를 함께 갖는다 — 실제 콘솔 문법은 §4 B군(콘솔 프로브 후)이며, 이 SPEC은 데이터 필드만 채운다. | `tracking-timing-mib-20260921.md` Rain 실측, 문서 §8.2 예시 |
| REQ-LDDESIGN-060 | **The** `attr_split`(REQ-024)는 **SHALL** 후렴 진입 큐에서 최소 색과 밝기를 분리해 기록한다 — 색은 스냅으로, 밝기는 짧은 페이드로 서로 다른 타이밍을 갖는다는 의도를 데이터로 남긴다. 실제 축별 딜레이 콘솔 명령 방출은 이 SPEC의 범위 밖이다(§4, `AXIS_TIMING_OBSERVED` 관측 0건 — `server/director/emit.py:60`). | 문서 §5.4, `server/director/emit.py:60` |
| REQ-LDDESIGN-061 | **The** 페이드 초는 **SHALL** 기존 `server/design/cue_fade.py`의 `store_with_fade`(`CueFade` 키워드, T11 프로브로 실측된 유일한 문법)를 재사용해 콘솔 명령으로 방출한다 — 새 페이드 문법을 만들지 않는다. `Property 'Fade'` 형태는 계속 금지다. | `server/design/cue_fade.py` 독스트링, `docs/handoff/2026-08-15-timeline-workflow-handoff.md:19` |

### 3.11 MIB — 사전 이동 (M5) (REQ-LDDESIGN-062~067) `[G12]`

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-062 | **When** 포지션(`pos`)이 이전 큐와 달라지면, MIB 검사는 **SHALL** 그 변화 직전 무버가 이미 꺼져 있던 시간을 확인해 셋 중 하나로 판정한다. 무버가 변화 전후 계속 꺼져 있으면 `dark`(어두운 채 이동)다. 꺼져 있다가 이 큐에서 켜지고, 꺼져 있던 창이 이동 시간(plan.md §F 잠정값 — 이동 1.5초 + 정착 0.5초, M8 콘솔 프로브로 실측치 교체 예정) 이상이면 `mark`(REQ-063에 따라 Mark 큐 삽입)다. 그 밖의 경우(창이 부족하거나 무버가 켜진 채 이동)는 `live`(경고)다. | 문서 §5.5, `tracking-timing-mib-20260921.md`:70, REQ-063, `server/concept/resolver.py` `mib_verdict` |
| REQ-LDDESIGN-063 | **When** MIB 판정이 `mark`이면, 컴파일러는 **SHALL** 창이 시작되는 시점에 Mark 큐(포지션만 변경, 밝기는 0 유지)를 자동 삽입한다. | `tracking-timing-mib-20260921.md` Rain 실측 — Mark 삽입 1건(102.0초) |
| REQ-LDDESIGN-064 | **When** 절(Verse) 또는 Bridge 구간에서 무버 계열 그룹(MOVER-U/MOVER-D 등)이 다음 후렴을 위해 포지션을 바꿔야 하면, 컴파일러는 **SHALL** 그 무버를 그 구간 동안 소등(`remove`)한 뒤 어두운 창에서 포지션을 옮긴다 — 켜진 채 포지션을 바꾸지 않는다. | `tracking-timing-mib-20260921.md` 개선사항 5, `final-verification-20260921.md` "절이 무버를 끄면서 동시에 포지션 변경" 수정 |
| REQ-LDDESIGN-065 | **The** 포지션 변경은 **SHALL** 어두운 창(REQ-062 `dark`/`mark` 판정) 안에서만 이뤄진다 — 연속 후렴·연속 브릿지처럼 어두운 창이 없는 구간에서는 포지션을 유지한다(REQ-064의 무버 소등 규칙이 적용될 수 없는 예외 상태). | `final-verification-20260921.md` "규칙 결함 ③ — 연속 후렴·연속 브릿지에서 어두운 창 없는 포지션 변경 → 유지" |
| REQ-LDDESIGN-066 | **When** MIB 판정이 `live`(켜진 채 이동)로 나오면, 컴파일러는 **SHALL** 큐 설명(REQ-023)에 `live_move` 표시를 명시하고 대안(느린 포지션 페이드 또는 어두운 창 확보를 위한 구조 재배치)을 제안 텍스트로 남긴다 — 조용히 넘어가지 않는다. | 문서 §5.5 검사 항목 |
| REQ-LDDESIGN-067 | **The** MIB 검사기는 **SHALL** `songcue`/컨셉 계층 경로에 연결된다 — 현재 `server/director/validate/mib.py`(LD-MIB-001/LD-REENTRY-001)는 director 교환 경로에만 있고 songcue 경로에는 없다(이 SPEC이 닫는 공백). 이 SPEC의 MIB 판정 로직은 `mib.py`의 어두운 창 증명 원칙(정착값 0 + 진행 중인 쓰기 없음, "부재는 증명이 아니다")과 같은 기준을 재사용하되, 자체 데이터 구조(§3.4 `mib` 필드)로 구현한다 — `mib.py` 자체를 songcue가 직접 import하지 않는다(계약 경계가 다르다, `mib.py` 독스트링 "콘솔 무접촉 · OSC 무접촉"과 같은 이유로 이 계층도 순수 계산이어야 한다). | `document-gap-audit-20260921.md` §5 표, `server/director/validate/mib.py` |

### 3.12 안전 큐·큐 설명·근거 등급 (M5) (REQ-LDDESIGN-068~072)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-068 | **The** 곡의 첫 큐는 **SHALL** 안전(프리셋) 큐 Q0.5로, `Block` 트래킹, 최소 조명(예: KEY 10%), 기본 색, 포지션 홈을 명시한다. | 문서 §9 예시 Cue 0.5, `apply-candidates-20260921.md` C6 |
| REQ-LDDESIGN-069 | **The** 곡의 마지막 큐는 **SHALL** 안전 큐로, 모든 그룹을 끄고(`reduce factor=0`) `Release` 트래킹으로 제어를 반환한다. | 문서 §9 예시 Cue 10, `apply-candidates-20260921.md` C6 |
| REQ-LDDESIGN-070 | **When** 큐가 조립되면, `description`(REQ-023)은 **SHALL** 최소 다음을 서술한다 — 무엇을 복원/추가/제거했는지, 색이 바뀌었는지, 최대 밝기, 남겨둔 자원(헤드룸, REQ-050). | `apply-candidates-20260921.md` C7 |
| REQ-LDDESIGN-071 | **The** `evidence` 등급(REQ-022)은 **SHALL** 큐시트 화면에 열로 노출된다 — `verified`는 정본이 실측한 페이드·안전 규칙에만 붙이고, 이 곡에서 직접 검증했다는 뜻이 아님을 UI 설명(§3.14 설명 4칸의 "무슨 뜻")이 명시한다. | `apply-candidates-20260921.md` 한계 절 — "근거 등급 태그의 verified는... 이 곡에서 검증한 것이 아니다" |
| REQ-LDDESIGN-072 | **Where** 워크시트나 판정기가 자동으로 채운 항목에 공개 근거가 없으면(문서 §11), UI는 **SHALL** "[공개 근거 없음]" 류 표시를 그 항목에 노출한다. | 문서 §11 |

### 3.13 기존 하류 브리지·8곡 게이트 고정 (M6) (REQ-LDDESIGN-073~077)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-073 | **When** 큐 모델 v2가 콘솔 명령으로 컴파일되면, 그 경로는 **SHALL** 기존 하류를 그대로 재사용한다 — 린트는 `server/design/lint.py`의 L1~L14, 에너지/헤드룸 예산은 `server/design/energy.py`의 D1~D5, 페이드는 `server/design/cue_fade.py`, MIB는 §3.11이 신설하는 계산기(기존 `mib.py`의 원칙을 재사용, REQ-067). 이 SPEC은 이 넷을 재구현하지 않는다. | 감독 확정 — "기존 하류... 그대로" |
| REQ-LDDESIGN-074 | **The** 큐 모델 v2로 생성된 큐는 **SHALL** 기존 `Sequence + Cue + Timecode` 저장·리드백·승인 흐름(`server/web/paperwork_api.py`, 콘솔 반영 미리보기·승인)을 그대로 통과한다 — 새 승인 경로를 만들지 않는다. | `one-song-director-view-20260921.md` "지금 흐름" §4~5 |
| REQ-LDDESIGN-075 | **The** M6 완료 시점에, `final_integrated.py`가 정의한 13개 게이트(G1~G13)는 **SHALL** 저장소 `server/tests/` 아래의 자동 테스트로 고정된다 — 8곡(pilot_baseline) 기준 최소 오늘 실측치(PASS 98 · n/a 6 · FAIL 0)를 재현해야 병합 가능하다. | `final-verification-20260921.md`, `.moai/state/verify/f12e5c95-t429/final_integrated.py` |
| REQ-LDDESIGN-076 | **Where** 새 규칙 적용으로 8곡 중 어느 한 곡이라도 게이트 결과가 오늘 측정치보다 나빠지면(새 FAIL 발생), 그 마일스톤은 **SHALL** 병합을 보류하고 원인을 `progress.md`에 기록한다 — 회귀를 성공으로 보고하지 않는다. | `verification-claim-integrity.md` 원칙과 정합, 카드 t429 자체가 회귀 사례 |
| REQ-LDDESIGN-077 | **When** M6이 완료되면, `server/looks/songcue.py`의 사다리 로직(회차별 값 넛지·색 순환)은 **SHALL** §3.7 회차 규칙의 데이터 표(§3.4 큐 모델 v2 `operation`/`layer` 조합)로 흡수되어, 더 이상 별도의 독립 코드 경로로 남지 않는다 — 단, SPEC-LDRETURN-001/LDCLIMAX-001/LDACCENT-001이 이미 확정한 절정 지속시간 상한·액센트 사다리 자체(REQ-LDCLIMAX-006~011)는 이 SPEC이 건드리지 않는다(별도 메커니즘, §4 비목표). | REQ-LDDESIGN-003·004, SPEC-LDCLIMAX-001/LDACCENT-001/LDRETURN-001과의 경계 |

### 3.14 UI (M7) (REQ-LDDESIGN-078~086)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-078 | **The** M7의 대상 화면은 런북 모드(Runbook Mode, `ui/src/components/RunbookMode.tsx`, 이미 존재)다 — 코파일럿 메인 화면(리그 대시보드·프리셋 풀 브라우저·큐 모니터·채팅·설정·페이퍼워크, `App.tsx`에서 `runbookMode`가 거짓일 때 렌더되는 화면)과 그 컴포넌트는 이 SPEC이 수정하지 않는다. 런북 모드의 기존 5블록 순서(오늘의 곡·큐 순서 → 타임라인+에너지선+Q줄 → CUE SHEET → PLAN CUE 카드 → 상태줄)는 **SHALL** 유지된다 — 새 최상위 내비게이션 항목을 만드는 것이 아니라, 이미 존재하는 모드 전환(헤더의 「런북 모드」 토글) 안에서 작업한다. | 감독 확정 — `src/DESIGN.md` §0, 실측 `App.tsx:1074`(`runbookMode ? … : …` 분기), `RunbookMode.tsx`(263행, `CueSheetTimeline`·`SongTimeline`을 마운트하는 유일한 지점) |
| REQ-LDDESIGN-079 | **The** UI는 **SHALL** 새 컨셉 패널을 갖는다 — 기본 접힘, 헤더 라벨 `이 곡의 컨셉`. 펼치면 **SHALL** 최상단에 "한눈에" 구획(REQ-LDDESIGN-097)을 두고, 그 아래 탭 3개(REQ-LDDESIGN-098)를 둔다. 탭 안의 항목(불릿·칩)을 클릭하면 **SHALL** 설명 4칸(무슨 뜻 / 무대에서 / 왜 이렇게 제안했나 / 바꾸려면)을 편다. | 감독 확정(2026-09-22) — `src/DESIGN.md` §4.2 전체 채택, REQ-097·098로 확장 |
| REQ-LDDESIGN-080 | **The** 탭 1(`이 곡의 연출`, Master Concept)의 본문은 **SHALL** 인과 불릿(워크시트 `concept` 필드 원문, REQ-013·032 그대로, 요약·윤문 없이 "원문 그대로" 배지와 함께 표시) + 여섯 칸 문법 요약 표(헤더 문자열 고정 `구간 / 색 / 기구·밝기 / 움직임 / 효과 / 그래서 보이는 것`, 표 자체가 세로 스크롤)로 구성된다 — 비유 표현이 아니라 실제 값(실제 색 이름, 실제 밝기 %, 실제 그룹 이름)으로 채운다. **The** 불릿·칩 항목 수는 **SHALL** 곡마다 가변이며, 고정 개수 그리드를 쓰지 않고 칩 wrap 레이아웃을 쓴다. | 감독 확정 — "비유 표현 금지, 실제 값으로"; 감독 확정(2026-09-22) — `src/DESIGN.md` §4.2 |
| REQ-LDDESIGN-081 | **The** 타임라인 블록 색은 **SHALL** Color Strip(REQ-026·033)에서 직접 가져온다 — 원샷·Mark 지점은 점 줄(dot row)로 타임라인에 겹쳐 표시된다. | 감독 UI 요구 |
| REQ-LDDESIGN-082 | **The** CUE SHEET는 **SHALL** 정확히 14열을 갖는다 — 기존 9열(Q#·Section→구간·TC In→시각·Color→색·Intensity→밝기·Fixture Group→기구 그룹·Movement→움직임·Effect→효과·Fade) 유지 + 신규 5열(회차·`Trigger`[REQ-006 어휘]·MIB·`Track 예외`[REQ-053의 `tracking` 값이 기본값 `Track`이 아닐 때만 값을 채움]·근거 등급) 추가. **The** 기존에만 있던 5열(`TC Out`·`Dur`·`Mood`·`Trans`·`Note`)은 **SHALL** 제거된다(감독 결정, 2026-09-22). 실측(`CueSheetTimeline.tsx:225` `SHEET_COLUMNS`) 결과 기존 CUE SHEET는 이미 14열(`Q# / Section / TC In / TC Out / Dur / Mood / Color(주/보조) / Intensity / Fixture Group / Movement / Effect / Trans / Fade / Note`)이었다 — "기존 12열에 2열 추가"라는 최초 전제는 틀렸었다. 제거되는 5열 중 `Trans` 값의 데이터 모델 존속은 REQ-LDDESIGN-096이 별도로 정한다. 행 표시는 **SHALL** 좌측 7px 색 레일(그 큐 구간의 Color Strip 색), 구간 전환 행의 상단 구분선, 밝기 칸의 값+구간색 막대+직전 큐 대비 증감 기호(▲▼), MIB 칸의 기호 3종(`◐ dark`/`◇ mark`/`◑ live`), 선택 행의 좌측 5px 바+아웃라인 표시를 포함한다. | 감독 UI 요구 재확정 + 감독 결정(2026-09-22 — CUE SHEET 14열 확정) — 실측 `CueSheetTimeline.tsx:225-239`, `src/DESIGN.md` §4.4 |
| REQ-LDDESIGN-083 | **The** PLAN CUE 카드는 **SHALL** 하단에 3줄(`Fade/Track`, `MIB/남김`, 헤드룸 요약)과 `Q###` 배지(실행기 번호 규칙 — Page children의 i+100, 기존 배선 그대로)를 추가로 갖는다. | 감독 UI 요구, 기존 실행기 번호 규칙(`project-songcue-on-console-0913.md` 메모리) |
| REQ-LDDESIGN-084 | **The** 상태줄은 **SHALL** GATE 표시(§3.6~3.11의 게이트 통과/경고 요약)를 갖는다. | 감독 UI 요구 |
| REQ-LDDESIGN-085 | **The** UI는 **SHALL** 타임라인의 가로 스크롤과 CUE SHEET의 세로 스크롤을 연동한다(한쪽을 스크롤하면 다른 쪽의 대응 지점이 함께 이동) — 영어 용어(Master Concept 등)는 작은 보조 표기로만 병기하고, 주 라벨은 한글로 유지한다. | 감독 UI 요구 |
| REQ-LDDESIGN-086 | **The** 런북 모드는 **SHALL** 메인 화면의 데이터(프리셋 풀 이름·번호, 콘솔 연결 상태)를 읽어 표시할 수 있다 — 그러나 메인 화면은 런북 모드의 제안(초안) 상태를 **SHALL NOT** 읽는다. 런북의 제안이 콘솔에 닿는 경로는 승인 카드를 거치는 「콘솔에 반영」 한 길뿐이다(`RunbookMode.tsx`의 `onApplyDraft` → `App.tsx`의 `applyDraftToConsole`, 이미 배선됨). 프리셋 풀 팝업은 **SHALL** 메인 화면 컴포넌트(`PresetPoolPopup.tsx`)를 마운트해 재사용하며 재구현하지 않는다. | 감독 확정 — `src/DESIGN.md` §0 "메인 화면과 공유하는 것", 실측 `RunbookMode.tsx:57-58`·`App.tsx:606-607,1145` |

### 3.15 PLAN CUE 수정요청 생성기 (M7) (REQ-LDDESIGN-087~095)

감독 결정(2026-09-22): 코파일럿에게 대화로 그룹 하나의 색·밝기·프리셋·
효과를 바꿔달라고 요청하는 것은 어렵고 직관적이지 않다 — 제안된 큐
카드가 이미 화면에 있으므로, 그 카드에서 바꿀 항목을 고르고 누르는
것이 자연스러운 입력 경로다. 감독의 재확인(같은 날): **이 부품은
「일종의 큐 조명연출 수정요청 프롬프트 생성기 — 조명감독이 적기 힘든
프롬프트를 직관적인 선택으로 손쉽게 만들어 주는 용도」다.** 그 이상이
아니다 — 타임라인을 직접 고치지 않고, 콘솔에도 직접 닿지 않는다. 명칭은
**"PLAN CUE 수정요청 생성기"**로 확정한다("편집기"가 아니다 — 이름이
「편집기」이면 구현자가 로컬에서 타임라인을 고치는 코드를 쓰게 된다).
REQ-LDDESIGN-083(PLAN CUE 카드 하단 3줄 + `Q###` 배지)의 문언은
바꾸지 않는다 — 생성기는 그 카드 하단에 위치하는 별도 조작면이다.
리뷰 표면은 `src/DESIGN.md:160-161`(§4.5 항목 7)이 이미 정의한
**변경 스택**이다(REQ-091) — 별도의 "전송 전 문장 미리보기" 패널은
만들지 않는다. 그 스택의 취소 버튼은 기존 CUE SHEET의 `↶ 되돌리기`와
겹치지 않도록 "선택 취소"로 구분한다(REQ-095). 클릭 선택지에 없는
요구를 실어 보내는 자유 입력 한 줄과 항목별 제거는 감독 결정
(2026-09-22)으로 채택되어 §3.16의 REQ-LDDESIGN-100(항목별 제거)·
REQ-LDDESIGN-101(자유 입력 한 줄)로 요구사항화됐다.

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-087 | **The** PLAN CUE 수정요청 생성기는 **SHALL** REQ-083 PLAN CUE 카드 하단에 위치한 조작면으로 존재하며, M2의 큐 모델 v2(그룹 스코프 `layer`/`operation`, REQ-LDDESIGN-017~025)와 그 파서(`parse_cue_sheet_edit_request`, `server/design/cue_sheet_edit.py`)가 그룹 스코프 표현(선택한 기구 그룹 집합에만 적용되는 값)을 지원할 때만 성립한다 — 이 SPEC은 M2 완료 이후에만 착수 가능하다(M7 내 순서 제약, plan.md 참조). | 감독 클래리피케이션(2026-09-22) ×2, M2(REQ-LDDESIGN-017~025) |
| REQ-LDDESIGN-088 | **The** 생성기는 **SHALL** 기구 그룹 다중 선택을 지원한다 — 선택된 그룹의 값(밝기·색)이 서로 다르면 "혼합"(단일 축 차이) 또는 "혼합 2색"(색상 차이)으로 표시한다. BLIND는 REQ-090의 잠금 대상이다. | `src/DESIGN.md` §4.5, 감독 UI 요구 |
| REQ-LDDESIGN-089 | **The** 생성기 우측 콘솔 반영 값 패널은 **SHALL** 포지션(풀 2)·컬러(풀 4)·딤머(풀 1)·이펙트(풀 21)·페이저를 프리셋 이름으로 표시하고, 값이 그룹마다 다르면 행을 분리한다. 각 행의 `바꾸기`는 **SHALL** 메인 화면의 `PresetPoolPopup.tsx`를 그대로 마운트한다(REQ-086 재사용 규칙, 재구현 금지). 선택 결과는 **SHALL** 이름(`posName`/`dimName`/`effName` 등)을 저장하고 행에 그대로 표시한다 — 값만 저장하면 `Home`·`Wall`·`Center`가 구분되지 않는다. 컬러·딤머는 선택 그룹에만, 포지션·이펙트·페이저는 큐 전체에 적용한다. | `src/DESIGN.md` §4.5 "값만 저장하고 이름을 버리면..." |
| REQ-LDDESIGN-090 | **The** BLIND(리저브) 그룹은 **SHALL** 해제 큐(`palette.reserved` 해제 큐, REQ-027과 같은 기준) 이전에는 생성기에서 잠금 상태로 표시되고 선택할 수 없다. | `src/DESIGN.md` §4.5 "BLIND는 Q023 전까지 잠금" |
| REQ-LDDESIGN-091 | **The** 변경 스택(`src/DESIGN.md` §4.5 항목 7)은 **SHALL** 바꾼 항목만 diff로 누적하고(예: `~ FOH 밝기 90% → 95%`), 상단 또는 헤더에 상태 라벨(`바꾼 것 N — 코파일럿 확인 대기` 류)을 갖는다 — 요청 → 수락 → 반영은 서로 구분되는 상태이며, 감독이 `코파일럿에게 반영 요청`을 누른 것만으로 초안이 바뀌었다고 표시하지 않는다. 규칙 위반 경고는 **SHALL** 스택 하단에 모아 쓰지 않고, 그 경고를 유발한 diff 줄에 병기한다(예: `~ 포지션 Sweep L → Sweep L (팬 ±30°) ⚠ Chorus 6 ±25°와 같아져 정점 구분이 약해진다`, REQ-093의 경고 내용을 이 형식으로 노출). 선택을 버리는 동작은 **SHALL** `선택 취소`로 제공한다(REQ-095 — `되돌리기`가 아니다). 코파일럿(파서 경로)이 거절하면 그 사유 문장은 **SHALL** 해당 diff 줄에 그대로 노출된다(REQ-092). | `src/DESIGN.md:160-161` §4.5 항목 7 + 감독이 확인한 렌더 형태(2026-09-22) |
| REQ-LDDESIGN-092 | **The** 생성기는 **SHALL NOT** 큐시트 타임라인 객체를 로컬에서 변형하거나 `changes` 매핑을 직접 만들어 기존 파서(`parse_cue_sheet_edit_request`)를 우회한다 — 생성기의 산출물은 **문장뿐**이며, 그 문장이 기존 경로(`server/web/session.py:9351` `_cue_sheet_draft_edit` → 파서 → `server/design/cue_sheet_edit.py:392` `apply_cue_sheet_edit`)를 거쳐 `changes`로 변환된다. 값 범위(조도 0-100, 페이드 ≤60초, `TRANS_VALUES` 3종)·부분 적용 금지·거절 사유 문자열은 **SHALL** 서버(`apply_cue_sheet_edit`)가 단일 진실 지점이다 — 생성기는 입력 위젯에 상한·하한을 표시만 하고 최종 판정은 서버 응답을 그대로 표시한다. 두 갈래(생성기 직접 생성 vs 파서 생성)가 생기면 검증 규칙이 갈라진다. | 감독 클래리피케이션(2026-09-22) ×2, `cue_sheet_edit.py:38,392`, `session.py:9351` |
| REQ-LDDESIGN-093 | **The** 생성기는 **SHALL** 다음 6개 파생 경고를 매 요청 조립 시점에 큐 데이터에서 계산한다(하드코딩 금지, REQ-091의 형식으로 diff 줄에 병기) — (1) 밝기가 뒤 후렴(예: C4 92%·C5 94%)을 역전하면 후렴 상승 곡선 경고 [신규], (2) 팬 폭이 정점값(±25°) 이상이면 정점 구분 약화 경고 [신규], (3) 리저브 항목(BLIND·짧은 Strobe·흰색)을 해제 큐 이전에 쓰면 리저브 위반 경고 [REQ-LDDESIGN-027(유보색)·REQ-LDDESIGN-090(BLIND 잠금) 재사용 — 신규 REQ 아님], (4) 잔여 그룹이 4 미만이면 헤드룸 경고 [REQ-LDDESIGN-050의 미사용 그룹 축 재사용, 임계값 "<4"만 신규], (5) MIB 판정이 `live`이면 GATE WARN 예고 [REQ-LDDESIGN-066 재사용 — 신규 REQ 아님], (6) 페이저 스피드가 곡 BPM과 같으면 박자 동기 경고 [신규]. | `src/DESIGN.md` §4.5, 감독 UI 요구; overlap 검토 대상: REQ-LDDESIGN-050~052 |
| REQ-LDDESIGN-094 | **When** 생성기가 요청을 코파일럿에게 보내면, 그 요청은 **SHALL** 감독이 대화창에 손으로 입력한 요청과 같은 자리(대화 기록)에 같은 형태로 남는다 — 사람이 읽을 수 있는 문장으로 표시된다. 승인 경로(REQ-LDDESIGN-086의 `onApplyDraft` → 승인 카드 → 콘솔)는 입력 방식과 무관하게 **SHALL** 동일하게 적용된다 — 생성기는 대화 경로의 우회로를 만들지 않는다. | 감독 클래리피케이션(2026-09-22) |
| REQ-LDDESIGN-095 | **The** 변경 스택은 **SHALL** 3개 상태를 구분한다 — **선택**(미전송, diff만 쌓임) / **요청**(전송됨·미수락) / **초안 반영**(코파일럿 수락됨). "선택" 상태를 버리는 버튼은 **SHALL** `src/DESIGN.md` 표기와 달리 **"선택 취소"**로 표기한다 — 기존 CUE SHEET의 `↶ 되돌리기`(`CueSheetTimeline.tsx:612`, 프로토콜 `timeline_draft_undo`, 배지 `되돌리기 N단계`, `CueSheetTimeline.tsx:246,258`)와 라벨이 겹치면 한 화면에 같은 낱말의 버튼 둘이 서로 다른 일을 한다. "선택 취소"는 **SHALL NOT** 서버에 어떤 메시지도 보내지 않는다 — `timeline_draft_undo`를 호출하지 않는다. 이 둘(선택 취소, 기존 초안 되돌리기)을 같은 핸들러로 묶는 구현은 **SHALL NOT** 이다 — 묶이면 전송된 적 없는 취소가 이미 반영된 초안을 한 걸음 되돌린다. 코파일럿이 요청을 수락하면 변경 스택은 **SHALL** 비워지고, 그 지점부터 되돌릴 대상은 기존 `↶ 되돌리기`(`server/web/timeline_draft.py` `TimelineDraftHistory`, 상한 20단계)로 넘어간다 — 되돌리기 깊이의 진실 지점은 **SHALL** 서버(`TimelineDraftHistory.depth`)이고 화면은 자체 카운터를 두지 않는다. **When** 코파일럿이 요청을 거절하면, 스택은 **SHALL** 그대로 남고 거절 사유(REQ-092)가 표시된다. | 감독 클래리피케이션(2026-09-22) — `CueSheetTimeline.tsx:246,258,612,617` 실측, `server/web/timeline_draft.py` `TimelineDraftHistory` |

### 3.16 M7 확정 — 감독 결정 5건 반영 (2026-09-22) (REQ-LDDESIGN-096~101)

감독이 2026-09-22 §3.14·§3.15 말미에 있던 두 "감독 결정 대기" 절의
항목 5건(CUE SHEET 기존 5열 제거 여부·컨셉 패널 "한눈에"+탭 3개
채택 여부·IBM Plex 웹폰트 채택 여부·PLAN CUE 수정요청 생성기의
항목별 제거·자유 입력 한 줄) 전부를 판정했다 — 두 "감독 결정 대기"
절은 이 판정으로 비게 되어 제거했다. 이 절은 그 5건의 판정을
REQ-LDDESIGN-096~101로 잠근다. REQ-082(CUE SHEET 14열)·REQ-079/080
(컨셉 패널)·REQ-091/092/095(PLAN CUE 수정요청 생성기)의 기존 문언은
바뀌지 않으며, 이 절의 REQ는 그 문언을 확장한다.

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDDESIGN-096 | **The** REQ-LDDESIGN-082가 CUE SHEET에서 제거하는 기존 5열 중 `Trans`(SNAP/XFADE/FADE) 값은 **SHALL** 열 제거와 무관하게 데이터 모델과 수정 경로에서 계속 존재한다 — `server/design/cue_sheet_edit.py`의 `TRANS_VALUES`(38-51행)와 `EDITABLE_FIELD_LABELS["trans"]`는 이 SPEC이 변경하지 않는다. 열이 화면에서 사라지는 것이지 값 자체가 사라지는 것이 아니다. **감독 결정(2026-09-23)**: `Trans`는 화면 열에서 제거한다. 값을 바꾸는 경로는 대화창(`cue_sheet_edit.py:230`) 하나뿐이며, §3.15 생성기에 `Trans` 조작을 추가하지 않는다. 데이터 모델과 `SNAP`→fade 0 접기(`cue_sheet_edit.py:240`)는 그대로 둔다. | 감독 결정(2026-09-22, 2026-09-23 A안) — 실측 `cue_sheet_edit.py:38,51,230,240` |
| REQ-LDDESIGN-097 | **The** 컨셉 패널의 "한눈에" 구획은 **SHALL** 최상단에 한 줄 분석 + 5단계 카드(`시작 → 쌓기 → 강조 → 예고 → 정점→마무리`)로 구성되며, 각 카드는 **SHALL** 색 바·단계명·Q 범위·구간·시간·색 HEX·밝기 범위·한 줄 설명 8개 항목을 갖는다. **The** 카드에 쓰이는 수치(Q 범위·구간·시간·색 HEX·밝기 범위)는 **SHALL** 그 곡의 큐 데이터에서 파생된다 — 하드코딩된 문장을 두지 않는다. 시트와 어긋나는 값이 있으면 감독이 어느 쪽을 믿을지 알 수 없다. | 감독 결정(2026-09-22) — `src/DESIGN.md` §4.2 채택 |
| REQ-LDDESIGN-098 | **The** 컨셉 패널은 **SHALL** "한눈에" 구획 아래에 탭 3개를 고정 라벨로 갖는다 — `이 곡의 연출`(Master Concept) / `이 곡의 재료`(Micro Concept) / `지키는 것·하지 않는 것·아껴 두는 것`(Visual Grammar). 영어 병기(Master Concept 등)는 **SHALL** 작은 보조 표기로만 두고, 주 라벨은 한글을 유지한다. | 감독 결정(2026-09-22) — `src/DESIGN.md` §4.2 채택 |
| REQ-LDDESIGN-099 | **The** UI는 **SHALL NOT** 웹폰트 의존성을 추가한다 — 본문은 시스템 폰트 스택, 수치·ID·프리셋명은 시스템 모노스페이스 스택을 쓴다. `src/DESIGN.md` §2가 확정한 `IBM Plex Sans KR`+`IBM Plex Mono`는 **채택하지 않는다** — 실측(`ui/package.json`) 결과 의존성은 `react`·`react-dom` 둘뿐이며 앱은 현재 웹폰트를 하나도 싣지 않는다; 공연장 오프라인 환경에서 폰트 로딩 실패 위험과 번들 증가를 피한다. **The** 밝기 %·시각(초)·페이드 초·Q 번호가 세로로 정렬되어야 하는 모든 칸(CUE SHEET 수치 열, PLAN CUE 카드 수치, 타임라인 시간 눈금)은 **SHALL** `font-variant-numeric: tabular-nums`를 적용해 숫자 정렬을 유지한다 — 웹폰트를 뺀 대가로 수치 열 정렬이 무너지지 않게 하는 완화책이다. 최소 글자 크기(11px, 데이터 12.5px 이상)와 대비 4.5:1 하한은 `src/DESIGN.md` §2 그대로 유지한다 — 폰트만 바뀐다. | 감독 결정(2026-09-22) — 실측 `ui/package.json` |
| REQ-LDDESIGN-100 | **The** 변경 스택(REQ-091)의 각 diff 줄은 **SHALL** 개별 제거 수단(`✕`)을 갖는다 — 네 항목 중 하나만 물릴 수 있어야 한다. **The** 전체 「선택 취소」(REQ-095)는 **SHALL** 그대로 유지되며, 항목별 제거와 같은 핸들러로 묶이지 않는다 — REQ-095의 3상태 모델(선택/요청/초안 반영)은 이 REQ로 바뀌지 않는다. | 감독 결정(2026-09-22) — `src/DESIGN.md:160-161` §4.5 항목 7 확장 채택 |
| REQ-LDDESIGN-101 | **The** 변경 스택은 **SHALL** 선택으로 만들어지지 않는 요구를 같은 요청에 실어 보낼 수 있는 자유 입력 한 줄을 갖는다(예: "그리고 이 구간 전체를 반 박자 당겨줘"). **The** 이 입력은 **SHALL** 생성된 요청 문장의 끝에 덧붙어 함께 전송되며, REQ-LDDESIGN-092의 규칙을 그대로 따른다 — 생성기가 해석하지 않고 그대로 실어 보내며, 판정은 서버(`parse_cue_sheet_edit_request`)가 한다. | 감독 결정(2026-09-22) |

## 4. 비목표 (Out of Scope)

### Out of Scope — 방송 특화 및 다중 콘솔

- Camera Base 독립 플레이백, Intended Shot, Take Variant, 카메라 컷 번호↔큐 번호
  매핑 등 방송 특화 기능(문서 §7)은 다루지 않는다 — 감독 결정("목표 무대: 콘서트").
- grandMA2/ETC Eos/MagicQ/Avolites 등 MA3 외 콘솔 어댑터(문서 §5.2)는 다루지 않는다.

### Out of Scope — 콘솔 프로브가 필요한 문법 (B군)

- Block/Track/Cue Only/Release의 실제 MA3 명령 문법. §3.9는 데이터 필드까지만
  정의하고, 실제 방출 문법은 콘솔 프로브 이후 별도 SPEC이 잇는다.
- 축별(Pan/Tilt) 딜레이·순차(stagger) 명령 문법. `AXIS_TIMING_OBSERVED`
  관측 0건(`server/director/emit.py:60`) — 프로브 전까지 §3.10은 데이터
  필드만 채우고 실제 방출은 하지 않는다.
- Mark 큐의 실제 콘솔 명령 문법.
- 스트로브 정책(`allow_strobe` 기본값 — plan.md §F 잠정값 `false`, 감독이
  워크시트에서 명시적으로 켜야 스트로브 큐가 생성된다. M8에서 감독
  재확인 대상).
- MIB 이동/정착 초의 실기 실측값(plan.md §F 잠정값 — 이동 1.5초 + 정착
  0.5초, M8 콘솔 프로브로 실측치로 교체).

### Out of Scope — 스키마·리그 확장 (C군)

- 객석광 그룹(현재 리그 18그룹에 없음), Gobo·Prism 속성(스키마 미노출),
  LED·영상 연동은 다루지 않는다 — 리그 결정·콘솔 프로브가 선행돼야 한다.
- 원샷 어휘 7종 중 Kick·Snare·Cymbal accent(`onsets_ms` 미소비), Color
  bump(컬러 스크립트 "순간 색" 항목 미정의), Position snap(포지션 프리셋
  필요)은 어휘 목록에는 존재하되 자동 생성은 하지 않는다(REQ-007과 모순
  아님 — 선택지는 있되 기본값 없음, 감독 워크시트 입력 전용).

### Out of Scope — 색 표현 방식 확장 (2026-09-23 감독 발의)

- 감독 발의: "색상은 웹에 많고 RGB 값으로 얼마든지 정의할 수 있는데
  10가지 색상만 정의할 필요가 있을까? 특히 요즘은 LED 조명장비가 많아서
  색상을 표현하는 방법이 많아졌다." 이 SPEC은 이 확장을 다루지 않는다
  — 10색 고정 표(`server/design/color_names.py`
  `COLOR_PALETTE_SEQUENCE`)를 그대로 유지하며, M2가 배선한 것은 감독
  확정 경로가 그 표 위의 색을 콘솔로 보내는 것뿐이다.
- 🔴 실측된 격차: 기구 능력 판독(`server/web/session.py:10332`)은 DMX
  채널 이름을 부분 문자열 `"ColorRGB"`로 판정하며 이미 `ColorRGB_W`
  (흰색 전용 칩)도 능력 있음으로 세지만, 생산 코드에서 `ColorRGB_W`를
  값으로 내보내는 자리는 0건이다 — 흰색 전용 칩이 달린 기구를 알아보면서도
  그 칩을 한 번도 켜지 않는다.
- 표를 없애는 것은 잘못된 방향이다 — 유보색(REQ-LDDESIGN-027)·후렴
  주색 동일(REQ-LDDESIGN-030) 같은 판정 규칙은 색이 셀 수 있는 이산
  집합이어야 성립한다. 그래서 후속 과제는 표를 없애는 게 아니라 표의
  축을 바꾸는 방향으로 4단계로 잡는다: t430(`ColorRGB_W` 채널 구동 —
  가장 싸고 가장 눈에 보임) · t431(젤(gel) 번호 어휘 — 콘솔 Book 모드
  대조) · t432(CIE `x`·`y` 좌표를 1차 표현으로 — 기구 독립적 색 지정) ·
  t433(고정 10색 표를 기본값으로 강등, 쇼별 색 사전으로 판정 전환).
- 조사 기록은 `docs/proposals/2026-09-23-color-representation-expansion.md`
  전문을 정본으로 한다. M2가 남긴 단일 구현 진입점은
  `server/web/session.py`의 `_song_color_value_lines`다 — W 채널이든
  좌표든, 확장은 여기서 시작한다.

### Out of Scope — 구간 판정기 정확도

- 구간 판정기 자체의 정확도 개선(현재 최고 D레벨 기준, 최고 5종 출력)은
  다루지 않는다. Too Cool의 13회 과분할 같은 사례는 §3.2의 재매핑·감독
  확인 표시로 완화할 뿐, 판정기를 고치지 않는다.
- `onsets_ms`/`rms_curve`를 실제로 소비해 비트 레벨 원샷 정확도를 높이는
  작업은 후속 SPEC으로 미룬다.

### Out of Scope — 학습·리허설 피드백 루프

- 프리셋·타이밍·색 보정을 리허설 결과로부터 자동 학습하는 것(문서 §8.1
  Rehearsal Feedback Loop)은 다루지 않는다 — 기존 `director-feedback`
  패키지 이상으로 확장하지 않는다.

## 5. 감독 결정 기록

2026-09-21 브리핑에서 이미 확정된 5개 결정(§2.1)은 재질문하지 않는다.
이 SPEC 저작 시점에 남은 미확정 항목 3건(MIB 이동/정착 초, 콘솔 문법
3종, 스트로브 정책 기본값)은 plan.md §F에 **잠정값**으로 기록했다 —
잠정값 자체가 이미 확정돼 있어 착수를 막지 않는다(값이 정해지지 않은
빈칸이 아니라, 감독 재확인이 아직 없는 채택값이다). Implementation
Kickoff Approval 시점에 감독이 세 잠정값을 재확인하고, 실제 콘솔 값은
M8 프로브(AC-LDDESIGN-022~024)로 실측치로 교체한다.

2026-09-23 감독 발의로 열린 색 표현 방식 확장(§4 "색 표현 방식 확장")과
관련해, 맨 "흰색"이 Warm White인지 Cool White인지의 판정은 아직 열려
있다. 다만 이 판정은 카드 t430(W 채널 구동)이 그 전제 자체를 바꿀 수
있으므로, t430 이전에는 확정하지 않는다. 카드 t409가 이미 화이트·흰색·
하양을 "감독 판정 대상 목록에는 있었지만 배선 대상은 아니다"로 남겼고,
M2는 그 경계를 그대로 유지했다 — 이 경계를 지키는 시험은
`server/tests/test_cue_sheet_apply.py` 의
`test_words_the_director_did_not_rule_on_still_fail_loudly`다.

## 6. 검증 수단의 한계 (착수 전 고지)

이 SPEC은 순수 계산 계층(§3.1~§3.13)과 UI 계층(§3.14)을 함께 다룬다.
콘솔 왕복이 필요한 요구사항과 순수 로컬 계산으로 닫히는 요구사항을 아래
표로 구분한다.

| REQ 그룹 | 검증 수단 | 콘솔 필요 |
|---|---|---|
| §3.1 선행 조건, §3.2 어휘, §3.3 워크시트, §3.4 큐 모델, §3.5 컨셉·컬러, §3.6 밀도, §3.7 회차, §3.8 헤드룸 | `uv run pytest` — `final_integrated.py`가 정의한 13게이트를 `server/tests/`에 고정한 회귀 시험(REQ-075), 8곡 pilot_baseline 기준 | 아니오 |
| §3.9 트래킹, §3.10 타이밍(데이터 필드까지), §3.11 MIB(판정 로직까지) | `uv run pytest` — 해석기 단위 시험 | 아니오 |
| §3.10 타이밍(축별 딜레이 실제 방출), §3.11 MIB(Mark 실제 명령), §3.9(Block/Release 실제 명령) | 콘솔 프로브(M8) — 이 SPEC 범위 밖(§4 B군), 별도 SPEC | 예 |
| §3.13 기존 하류 브리지 | `uv run pytest` + 8곡 게이트 회귀 | 아니오 |
| §3.14 UI, §3.16 M7 확정 사항(REQ-096~101) | Vitest(`ui/src/components/*.test.tsx` 패턴) + 컴포넌트 스냅샷, `ui/dist` 빌드 산출물 검사(웹폰트 부재) | 아니오 |
| M8(계획된 실기 검증 1곡) | 실기 콘솔 — Sequence + Cue + Timecode 저장 확인, 리드백, 육안 확인(후렴 색 동일) | 예 |

## 7. 근거 보고서 (2026-09-21, 11편)

`reports/lighting-director-upgrade-20260921.md` ·
`reports/lighting-director-verification-20260921.md` ·
`reports/one-song-director-view-20260921.md` ·
`reports/cue-density-director-view-20260921.md` ·
`reports/cue-density-8songs-20260921.md` ·
`reports/document-gap-audit-20260921.md` ·
`reports/apply-candidates-20260921.md` ·
`reports/vocab-closed-verification-20260921.md` ·
`reports/chorus-escalation-audit-20260921.md` ·
`reports/tracking-timing-mib-20260921.md` ·
`reports/final-verification-20260921.md`

상세 디지스트는 `research.md` 참조.
