---
id: SPEC-COPILOT-SPATIAL-001
title: "공간 인식 연출 — 배치 판독(READ) + 배치 생성(WRITE) (Spatial-Aware Choreography)"
version: "0.3.0"
status: completed
created: 2026-08-03
updated: 2026-08-04
author: manager-spec
priority: P1
phase: "Phase 2 연출 계층 — 공간 축 (배치 인식 연출 + 배치 생성)"
module: "server/spatial/ (신규), server/orchestrator/tools.py, console/lua/copilot_responder.lua (조건부), server/rulebook/assets/v2.4.2/32_spatial_design.md (신규)"
lifecycle: spec-anchored
tags: "spatial, layout, position, posx-posy-posz, wave-direction, selection-order, matricks, rig-context, safety-backup, write-probe, fabricated-control"
tier: L
related_specs: [SPEC-COPILOT-SCENE-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-INTROSPECT-001]
---

# SPEC-COPILOT-SPATIAL-001 — 공간 인식 연출

> **이 SPEC이 닫는 구멍**: 앱은 오늘 픽스처가 **어디에 있는지 모른다.** rig context의 픽스처 스냅샷은 `{no, name}` 두 축뿐이고(`server/orchestrator/tools.py:404-430` `rig_object`), 좌표 축은 0이다. 그래서 "왼쪽에서 오른쪽으로 웨이브"라는 지시가 **1행×30대 리그와 3행×10대 리그에서 같은 커맨드**가 된다 — 배치가 다르면 연출이 달라야 하는데, 앱에는 그 차이를 알 채널이 없다.
>
> 본 SPEC은 그 채널을 **양방향으로** 연다. **READ(배치 인식 연출)**: 콘솔의 패치 3D 좌표(`posx`/`posy`/`posz`)와 Layout pool을 판독해, 자연어 연출 지시가 배치에 맞는 커맨드를 내게 한다. **WRITE(배치 생성)**: 사용자가 요청하면 앱이 픽스처의 3D 무대 좌표를 기록해 배치를 만든다("이 파 30대를 3×10 그리드로 정렬").
>
> **파이프라인의 위치**: LOOKLIB(정지 화면) · FXLIB(시간축) · SCENE(합성)이 세운 의도→메모리 파이프라인에 **공간 축**을 더한다. 기존 세 계층은 전부 PRESERVE이며 읽기 import만 한다(plan.md §C.3).

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-08-03 | manager-spec | 최초 작성 (draft, Tier L). 출처: 사용자 미션(양방향 공간 인식) + 코디네이터 인수 웹 조사(MA help/포럼/선례 플러그인 — research.md §1) + 저장소 직접 판독(base `origin/main` = `3176900`). REQ **26건** · AC **30건** · ASSUMPTION **53~60(8건)** · 열린 질문 **5건**(plan.md §F) · 라이브 세션 **2회(M0·M6)**. Lua 프로퍼티 이름 대소문자는 **전건 미검증** — M0 라이브 프로브가 첫 마일스톤이다. 아티팩트 6종 동시 생성. |
| 0.2.0 | 2026-08-03 | manager-spec | **plan-audit fold-in** (PASS-WITH-DEBT 0.86 — 지적 10건 전건 반영). M1: REQ-014 좌표 금지를 **연출 발화** 커맨드로 재범위(WRITE 기록 커맨드는 REQ-019~024 소유 — 모순 해소). M2: REQ-020에 risky 분류 **발동 조건** 절 신설(`gate.py:362` 규칙 ③은 risky 경로 전용) + **AC-SPATIAL-031** 신설(게이트 risky 판정 + `before_risky_execution()` 발동, 뮤테이션 필수). M3: REQ-026에 5판정→4접두 매핑 표 **본문 내장**(SCENE-001 출처 명기 — 포인터 상속 제거). M4: **AC-SPATIAL-032** 신설(look/fx/scene PRESERVE — REQ-018 커버 공백 해소). m5~m10: plan.md(M0 SKIP 행·M6 GUI 대안·WRITE AC 열거)·acceptance.md(AC-024 Ubiquitous 전환·AC-028/030 정박·AC-025 주석)·design.md(§5 표적 공유 근거·§6 프리셋 파라미터 계약) 동반 반영. 최종 카운트: REQ **26건** · AC **32건**(뮤테이션 필수 5건: 004·006·019·020·031). C1(§F D-1~D-5 열린 질문 5건)은 킥오프 게이트 대상으로 **미변경**. |
| 0.3.0 | 2026-08-04 | orchestrator | **sync-phase 인계 5건 소요** (progress.md §E.3 → §E.4). ① **risky 분류 문면 모순 해소** — REQ-020의 *"스크리닝에서 risky로 분류되어야 한다"* 는 run-phase에서 `[DEFERRED]`가 됐다(§E.2.14: `server/safety/` PRESERVE 경계). 본 HISTORY 행과 REQ-020·024의 `[DEFERRED]` 표기를 **정본**으로 삼고 `plan.md §B M4` · `AC-SPATIAL-031`을 같은 표기로 맞췄다. ② `arrange_fixtures`의 **무승인 쇼파일 변형**을 §C.1 검증 천장에 행으로 명기. ③ AC-031 우선순위 근거로 **§E.2.20 결함 2**(요청하지 않은 좌표 기록 54건 무승인 통과)를 인용. ④ **절단 시 모델 미고지**(§E.2.20 결함 1)를 §C.1에 행으로 등록 — 툴 설명문은 지시일 뿐 강제가 아니다. ⑤ **정렬 어휘의 기준 명기**(§E.2.21) — §C.4 신설. 코드 변경 **0** · 문서만. |

## A. 개요

### A.1 핵심 원리 — 웨이브 방향은 좌표가 아니라 선택 순서다

MA3에서 공간 이펙트의 방향을 정하는 것은 **선택 순서(selection order)와 선택 그리드**다. 페이저의 `Phase 0 Thru 360`은 선택 그리드 X축을 따라 위상을 편다(`31_choreography_patterns.md:69`, `:85-90` MAtricks). **콘솔에는 "레이아웃 좌표 순서로 그리드를 만든다"는 내장 기능이 없다** — 이것이 본 SPEC의 부가가치 자리다:

```
좌표 판독 → 축 기준 FID 정렬 → 그 순서로 선택 발화 → 페이저/MAtricks 적용
```

**좌표는 커맨드에 실리지 않는다.** 좌표는 서버 측 정렬의 입력일 뿐이고, 콘솔로 나가는 것은 정렬된 순서의 선택 사슬 + 이미 검증된 페이저/MAtricks 문법이다(REQ-SPATIAL-014). 1×30 리그와 3×10 리그의 차이는 **행 검출 결과와 선택 순서의 차이**로 실현된다.

### A.2 어휘 구분 — "spatial" vs "executor layout" (충돌 금지)

저장소에는 이미 **layout이라는 이름의 다른 축**이 있다: `server/looks/layout.py` + `server/orchestrator/layout_occupancy.py`는 **executor layout**(시퀀스→익스큐터→라벨 배선, BUSKWIZ T-F/T-J)이며 픽스처의 공간 배치와 무관하다. 본 SPEC은 그 모듈들을 **무변경**으로 보존하고, 자신의 모든 식별자에 **`spatial` 접두**를 쓴다 — 패키지 `server/spatial/`, 툴 `get_spatial_context`(안), 룰북 `32_spatial_design.md`. "layout"이라는 낱말은 **MA Layout pool**(콘솔 오브젝트)을 가리킬 때만 쓴다.

### A.3 공간 출처 2종 — 패치 3D가 정본, Layout pool은 보조

| 출처 | 내용 | 성질 |
|---|---|---|
| **패치 3D 좌표** (정본) | `Root().ShowData.LivePatch.Stages…` 아래 픽스처별 `posx`/`posy`/`posz`(+`rotx`/`roty`/`rotz`) — 실세계 미터, 3D 뷰어가 직접 반영 | 모든 패치된 픽스처가 가진다. 판독·기록 모두 포럼 실증 사례 있음(research.md §1) — **우리 콘솔에서는 미측정** |
| **Layout pool 2D** (보조) | 2D 레이아웃 요소: 할당 오브젝트 + `PositionX`/`PositionY`. LD가 손으로 큐레이션한 평면도 | 없을 수 있다. 요소는 **요소 번호로만** 주소 가능 — 픽스처→(x,y) 맵은 layout children 반복으로만 구축(research.md §1) |
| 라이브 데이터(폴백) | 둘 다 없음 | 명시 신호 + 기존 비공간 연출로 강등(REQ-SPATIAL-005) |

### A.4 M0 게이트 — 전부 미측정에서 시작한다

이 SPEC의 모든 콘솔 사실은 **타 버전 포럼/문서의 인수 조사**이며, 설치된 onPC 2.4.2에서의 프로퍼티 이름 대소문자·판독 가능성·기록 채널은 **전건 미검증**이다. 이 저장소의 규율 — *"정적 프로브가 답할 수 없는 것은 실사격만 답한다"*, *"콘솔의 `ok`는 미지 이름에 관대할 수 있다"*(SCENE-001 M0: 존재하지 않는 `/CueOnlyy`가 `ok`+저장) — 에 따라 **M0 라이브 프로브가 첫 마일스톤이고, 날조 대조군이 의무**다(REQ-SPATIAL-026). READ가 NEGATIVE면 본 SPEC 전체가 성립하지 않으므로 중단·블로커 보고한다(plan.md §A.3).

## B. 요구사항 (GEARS)

### B.1 공간 컨텍스트 판독 (READ)

- **REQ-SPATIAL-001** [Event-driven] — **When** 공간 컨텍스트 판독 툴이 호출되면, the 시스템 **shall** 패치 3D 좌표 경로에서 픽스처별 `(fid, name, x, y, z)`를 판독해 맵으로 반환한다. 좌표는 콘솔이 돌려준 실수 값 그대로이며 단위 환산·반올림 발명을 하지 않는다.
- **REQ-SPATIAL-002** [Ubiquitous] — 공간 출처 우선순위 **shall** 패치 3D(정본) → Layout pool 2D(존재 시 보조)이며, 회신·리포트는 **어느 출처가 답했는지 명시**한다. 두 출처의 좌표를 섞어 하나의 축으로 합성하지 않는다.
- **REQ-SPATIAL-003** [Event-driven] — **When** Layout pool을 판독하면, the 시스템 **shall** layout children 반복으로 요소→할당 오브젝트→`(PositionX, PositionY)` 맵을 구축한다 — 요소는 픽스처 id로 직접 주소할 수 없다는 인수 조사 사실(research.md §1)을 전제로 하며, 반복 외의 지름길을 발명하지 않는다.
- **REQ-SPATIAL-004** [Unwanted] — the 판독 경로 **shall not** 좌표를 발명한다. 판독 불가 픽스처는 **사유와 함께 부재로 보고**되며, 0이나 평균값 등 어떤 기본값으로도 채워지지 않는다.
- **REQ-SPATIAL-005** [Event-driven] — **When** 어떤 출처에서도 공간 데이터를 얻지 못하면, the 시스템 **shall** 명시적 신호를 반환하고 기존 비공간 연출 경로로 강등한다 — 기존 경로 자체는 무변경으로 보존된다.
- **REQ-SPATIAL-006** [Ubiquitous] — 판독 **shall** 왕복·페이로드 예산 아래에서 관측 가능하게 동작한다: 항목이 축소되면 절단 신호가 세워지고, 왕복 캡에 걸리면 캡 신호가 세워진다. 조용한 부분 판독은 금지된다(응답기 `truncated` 규율 계승).
- **REQ-SPATIAL-007** [Ubiquitous] — 좌표 맵의 픽스처 식별자 **shall** 콘솔이 판독으로 돌려준 것만 쓴다 — 목록 위치를 식별자로 대체하지 않는다(슬롯≠FID 규율 계승, `server/orchestrator/tools.py` `rig_object` docstring).
- **REQ-SPATIAL-008** [Ubiquitous] — 기존 `get_rig_context` 10경로·스냅샷 형상 **shall** 무변경이다 — 공간 판독은 별도 표면(신규 툴)이며 기존 rig context 테스트는 무수정 PASS여야 한다(가산성).

### B.2 공간 분석 (순수 계층)

- **REQ-SPATIAL-009** [Ubiquitous] — 신규 패키지 `server/spatial/` **shall** 순수 분석 계층을 제공한다: 행 검출(y축 클러스터링), 정렬(left_to_right / right_to_left / center_out / diagonal), 행별 그룹핑. 전부 콘솔 무접촉이며 단위 테스트만으로 완전 검증 가능하다.
- **REQ-SPATIAL-010** [Ubiquitous] — 분석 **shall** 결정론적이다: 같은 입력 → 같은 출력. 정렬 동률·클러스터 모호는 임의 선택 대신 **명시 신호**로 처리한다(LOOKLIB·FXLIB 동점 None 규율 계승).
- **REQ-SPATIAL-011** [Ubiquitous] — 행 검출 **shall** 1행×30대와 3행×10대를 **구조적으로 구별**한다 — 행 수·행 구성원이 스키마에 드러나며, 같은 지시에 대해 두 리그가 다른 선택 순서를 산출하는 근거가 된다.
- **REQ-SPATIAL-012** [Event-driven] — **When** 배치가 불규칙해 클러스터링 신뢰도가 기준 미달이면, the 분석 **shall** 저신뢰 신호와 함께 반환한다 — 단일행 가정을 조용히 강행하지 않는다.
- **REQ-SPATIAL-013** [Unwanted] — `server/spatial/` **shall not** transport(`server.bridge`/`pythonosc`)·게이트 표면을 import한다 — 기존 `server/tests/test_architecture.py` 전역 스캔에 자동 포섭되며 예외 명단 추가는 금지된다(SCENE REQ-SCENE-019 동형).

### B.3 연출 통합 (선택 순서 발화)

- **REQ-SPATIAL-014** [Ubiquitous] — 공간 연출의 실현 축 **shall** 선택 순서다: 좌표로 FID를 정렬해 그 순서로 선택을 발화하고, 그 위에 기존 검증된 페이저/MAtricks 문법을 적용한다. **좌표 수치는 연출 발화 커맨드에 실리지 않는다** — 좌표가 커맨드에 실리는 유일한 축은 WRITE의 기록 커맨드이며, 그 축은 REQ-SPATIAL-019~024가 소유한다.
- **REQ-SPATIAL-015** [Event-driven] — **When** 채팅 지시가 공간 한정어(예: "왼쪽에서 오른쪽", "가운데부터 바깥으로", "대각선")를 담으면, the 매칭기 **shall** 폐쇄 정렬 어휘로 해석한다. 미지 한정어는 폴백 신호로 처리하며 임의 매핑을 발명하지 않는다(LOOKLIB 매칭 규율 계승).
- **REQ-SPATIAL-016** [Ubiquitous] — 룰북 **shall** `32_spatial_design.md` 1개 파일만 신설한다(정렬 순서상 `31_choreography_patterns.md` 뒤): sort-select-phaser 레시피 + 공간 한정어 안내. 접두 조립은 byte-stable을 유지하고(REQ-MVP-007/008 계승, `server/tests/test_rulebook.py`), 기존 자산 5개는 byte-diff 0이다. **라이브로 검증되지 않은 커맨드 문법은 룰북에 싣지 않는다**(31의 "(validated)" 규율 계승 — M6 검증 후 문면 확정).
- **REQ-SPATIAL-017** [Unwanted] — 신설 룰북 파일 **shall not** per-show 값(그룹 번호·FID·좌표 수치·시퀀스 번호)을 포함한다(캐시 접두 안정성).
- **REQ-SPATIAL-018** [Ubiquitous] — look/fx/scene 계층과의 통합 **shall** 읽기 import + 신규 표면에서만 이뤄진다 — `server/looks/**`·`server/fx/**`·`server/scene/**`은 PRESERVE이며 본 SPEC이 수정하지 않는다.

### B.4 배치 생성 (WRITE)

- **REQ-SPATIAL-019** [Event-driven] — **When** 사용자가 배치 생성을 명시 요청하면(예: "3×10 그리드로 정렬"), the 시스템 **shall** 프리셋 형상(grid / row / circle)의 목표 3D 좌표(미터)를 결정론적으로 계산하고, 대상 픽스처의 패치 좌표에 기록한다.
- **REQ-SPATIAL-020** [Ubiquitous] — the 기록 경로 **shall** 기록 전에 대상 전 픽스처의 **현재 좌표를 판독·기록(원좌표 백업)**하고, 복원 경로(원좌표 재기록 번들)를 리포트에 싣는다. 이 원좌표 백업·복원 번들 의무는 **구현됐고 라이브에서 작동했다**(§E.2.20 복구가 이 경로로 이뤄졌다). ⚠ **`[DEFERRED]` — showfile 백업 규칙 ③ 연동 부분만**: 게이트는 RISKY 분류 커맨드만 백업하므로(`server/safety/gate.py:362` — 규칙 ③ `before_risky_execution()`은 risky 경로 전용) 좌표 기록 번들이 **스크리닝에서 risky로 분류되어야** 규칙 ③이 발동하는데, 그 분류 확장은 run-phase에서 **되돌려졌다**(§E.2.14 — `server/safety/` PRESERVE 경계를 넘고 기존 테스트 10건이 깨진다). 따라서 좌표 기록은 **오늘 `safe`로 분류되어 승인 카드 없이 콘솔에 나가고 규칙 ③ 백업도 발동하지 않는다**(§C.1 · 관측 사례 §E.2.20 결함 2). 남은 방어선은 **본 SPEC 자체의 원좌표 백업·재조회 검증·복원 번들·범위 봉쇄**이며 이들은 작동한다. risky 분류 확장은 `server/safety/`를 함께 소유하는 후속 SPEC의 몫이다(AC-SPATIAL-031 `[DEFERRED]`).
- **REQ-SPATIAL-021** [Ubiquitous] — 기록 검증 **shall** 재조회로 한다: 기록 후 대상 픽스처의 좌표를 재판독해 목표값 일치를 확인한다. `ok:true` 단독은 증거가 아니며(SCENE M0 실측 계승), 재조회 불일치는 명시 실패로 보고된다.
- **REQ-SPATIAL-022** [Unwanted] — the 기록 경로 **shall not**: (a) 명시 대상 외 픽스처의 좌표를 건드리고, (b) 사용자 요청 없이 선제 재배치를 제안·실행하며, (c) v1에서 `rotx`/`roty`/`rotz`를 기록한다(판독은 허용 — 기록은 방향 미측정 축이므로 제외).
- **REQ-SPATIAL-023** [State-driven] — **While** LiveLock이 활성인 동안, 배치 기록 **shall** 제안(Proposal) 전용으로 강등되고 콘솔 송신은 0건이다 — 강등은 실패가 아니라 답이다(SCENE REQ-SCENE-020 계승).
- **REQ-SPATIAL-024** [Ubiquitous] — 좌표 기록 **shall** 게이트 단일 관문을 경유한다 — 커맨드라인 경로든 응답기 신규 동사든, 스크리닝·감사·승인 흐름 없이 콘솔에 도달하는 기록 경로는 존재하지 않는다. ⚠ **부분 `[DEFERRED]`**: **단일 관문·스크리닝·감사**는 충족된다(모든 기록이 `gate.screen()`을 지나고 감사 로그에 남는다 — §E.2.20이 54건 전부를 감사 로그로 재구성했다). **승인 흐름만** REQ-020의 risky 분류에 종속되어 `[DEFERRED]`다 — `safe` 분류이므로 승인 카드가 뜨지 않는다. 즉 "확인 없이 콘솔에 도달하는 경로는 없다"는 **감사 의미로는 참이고 승인 의미로는 오늘 거짓**이다. 이 문장을 두 뜻으로 읽을 수 있게 둔 것이 §E.2.20 결함 2를 놓친 문면상의 원인이다.

### B.5 툴 표면 + 라이브 판정 기록

- **REQ-SPATIAL-025** [Ubiquitous] — the 툴 표면 **shall** READ 1종(안: `get_spatial_context`) + WRITE 1종(안: `arrange_fixtures`)으로 구성되고, 닫힌 툴 집합은 18 → **20**으로 갱신된다(개수 고정 테스트 동반 갱신 — 호출 사건과 무관한 정적 구성 속성이다). 최종 툴 이름·개수는 킥오프 게이트에서 확정한다(plan.md §F D-4).
- **REQ-SPATIAL-026** [Ubiquitous] — 라이브 세션(M0 프로브 · M6 종단)의 각 판정 **shall** `progress.md §E.2`에 폐쇄 판정 어휘(`GO` / `NEGATIVE` / `CONDITION_NOT_MET` / `INCONCLUSIVE` / `REOPEN_SCOPE`)와 행두 접두 행(`GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`)으로 기록된다 — 매핑 표는 아래에 **본문 내장**한다(출처: SCENE-001 REQ-SCENE-021. SCENE-001 자신이 교차 SPEC 포인터 상속을 결함으로 판정했으므로, 아래 표가 본 SPEC의 정본이다). 세부 4항: (a) 접수와 효과는 언제나 별개 판정, (b) 전제 부정 시 중단·블로커 보고(에이전트의 대체 정책 선택은 결정 월권), (c) `ok`를 증거로 쓰기 전 **날조 대조군 1발**로 그 축의 변별력을 확립, (d) **프로브별 별도 표적** 배정(SCENE M0의 표적 공유 결함 계승 금지) + **write 프로브는 원상복구 왕복까지가 한 프로브다**.

| 판정 어휘 | 행두 접두 | 비고 |
|---|---|---|
| `GO` | `GO:` | 전제 성립 — 해당 축 진행 |
| `NEGATIVE` | `DESCOPE:` | 전제 부정 — 해당 축 강등·중단 |
| `INCONCLUSIVE` | `DESCOPE:` + `verdict=INCONCLUSIVE` 키 **의무** | 판정 불능 — DESCOPE 행 안에서 키로 구분한다 |
| `CONDITION_NOT_MET` | `SKIP:` | 전제 미성립(프로브 불가·미실행) |
| `REOPEN_SCOPE` | `REOPEN:` | 범위 재개 필요 |

## C. 환경 및 전제

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존, OSC `127.0.0.1` UDP. site config는 effective 값에서만 읽는다.
- **기능 전제**: MVP 파이프라인(`run_commands`·`gate.screen()` 단일 관문·승인/제안 카드), 응답기 v1.5.0(`prop` 동사 — 기존 판독 문), rig context + 드릴다운(쿼리 캡 16 — `tools.py:173`), LOOKLIB/FXLIB/SCENE(전부 completed). 전부 `related_specs`(비차단) 참조.
- **스테이지 전제 상속**: 픽스처는 stage slot 1에서 읽는다(`DEFAULT_RIG_CONTEXT_PATHS["fixtures"] = "Patch/Stages/1/Fixtures"`, `tools.py:150-161` — 라이브 실측 근거 주석 포함). 다중 스테이지는 §D 제외.
- **실행 특성(선행 실측 전재)**: `run_commands` stop-on-first-failure, 줄당 ~66ms, 응답기 회신 예산 `max_payload = 1900`(초과 시 `cmd_keyword` 조용한 드롭 — 테스트가 유일한 그물).

### C.1 검증 천장 — 무엇이 기계로 확인되고 무엇이 안 되는가

**이 표가 인수 설계 전체를 지배한다.** NO 행에 기계 증거를 주장하는 문면·AC는 그 자체로 결함이다.

| 항목 | 기계 검증 | 경로 |
|---|---|---|
| 패치 좌표 값(`posx`/`posy`/`posz`) | **조건부 YES** — ASSUMPTION-53 GO 시 | `prop` 재조회 (또는 신규 벌크 동사) |
| Layout 요소 위치(`PositionX`/`PositionY`) | **조건부 YES** — ASSUMPTION-55 GO 시 | layout children 반복 판독 |
| 행 검출·정렬·프리셋 좌표 계산의 정확성 | **YES** | 순수 Python — 콘솔 무접촉 |
| 발화 커맨드의 선택 순서·좌표 부재 | **YES** | 산출 문자열 정적 검사 |
| 기록된 좌표 값 | **조건부 YES** | 기록 후 재조회 (REQ-SPATIAL-021) |
| **선택 순서가 실제 웨이브 방향을 정하는가** | **NO** | 사람의 GUI/무대 관측이 유일 (ASSUMPTION-58) |
| **3D 뷰어의 시각적 반영** | **NO** (기계) | 좌표 값 재조회는 YES, 시각 확인은 사람 |
| 미지 프로퍼티 이름에 대한 `ok`의 변별력 | **미측정 — M0 날조 대조군이 판정** | SCENE M0 선례: 축마다 다르다 |
| **좌표 기록의 승인 카드** | **NO — 오늘 뜨지 않는다** | `Set Fixture … Pos*`가 `safe`로 분류된다(AC-031 `[DEFERRED]`, §E.2.14). 라이브 관측: 요청하지 않은 좌표 기록 **54건**이 무승인 통과(§E.2.20 결함 2). 같은 턴의 `Go+ Page 1.202`는 정상적으로 카드를 띄웠다 — **게이트는 건강하고 좌표 기록만 그물을 통과한다** |
| **절단된 리그에서 모델이 불완전성을 고지하는가** | **NO — 강제 수단이 없다** | 툴은 `truncated: true`를 보고하고 설명문이 *"say so"* 를 명령형으로 적지만, 모델은 받은 일부에 대한 좌우 정렬을 제시하고 **불완전성을 말하지 않았다**(§E.2.20 결함 1, fid 19 탈락). **툴 설명은 지시일 뿐 강제가 아니다** — `server/looks/**`가 쓰는 방식의 한계를 그대로 물려받는다. 구조적 강제(부분 리그 상태값 또는 정렬 결과 보류)는 **후속 과제** |

### C.2 미검증 전제 (ASSUMPTION — INTROSPECT-001이 46~52를 사용, 본 SPEC은 53부터)

각 전제가 막는 대상은 서로 다르다. 판정 마일스톤은 plan.md §A.3이 소유한다.

- **ASSUMPTION-53 (패치 3D 판독)** — LivePatch 경로의 픽스처에서 `posx`/`posy`/`posz`가 기존 `prop` 계열 채널로 판독된다. **프로퍼티 이름 대소문자 미검증** — M0가 후보 변형을 사다리로 시도한다. **NEGATIVE면 본 SPEC 전체 중단**(READ 없이는 어떤 축도 성립하지 않는다).
- **ASSUMPTION-54 (패치 3D 기록)** — 패치 좌표가 기록 가능하다(포럼 실증: Lua에서 `.posz = 5.0` 설정으로 3D 이동 — research.md §1). **기록 채널은 미확정**(커맨드라인 `Set` 계열 vs Lua 대입 — plan.md §F D-2). NEGATIVE면 WRITE 축 `[DEFERRED]`, READ 축은 진행.
- **ASSUMPTION-55 (Layout pool 판독)** — `DataPool().Layouts` children 반복으로 요소·할당 오브젝트·`PositionX`/`PositionY`가 판독된다. NEGATIVE면 v1은 3D-only(Layout 축 `[DEFERRED]`).
- **ASSUMPTION-56 (Layout 요소 기록)** — `Set Layout <l>.<e> "PositionX" <v>` 커맨드가 동작한다(포럼 moderator 확인 — 타 버전). Layout 기록이 v1 범위에 드는 경우에만 판정 대상(plan.md §F D-3).
- **ASSUMPTION-57 (FID 주소 가능성)** — 패치 판독이 돌려주는 픽스처 식별자로 `Fixture <fid>` 선택이 **의도한 개체를** 잡는다. 슬롯≠FID 함정(EXECBODY/SHOWUI 실측 계열)이 이 축에서 재발할 수 있다 — M0가 판정한다.
- **ASSUMPTION-58 (선택 순서 → 방향)** — 정렬된 순서의 가산 선택(`Fixture a + Fixture b + …`) 위에 페이저를 적용하면 웨이브가 그 순서를 따른다. **효과 축이므로 기계 검증 불가** — M0/M6 사람 GUI 관측만이 판정한다(§C.1).
- **ASSUMPTION-59 (Grid store)** — `Grid store`로 커스텀 그리드를 영속화할 수 있다는 인수 조사는 **룰북 근거 0건·라이브 실측 0건**이다. v1 주경로가 아니며(§D 제외), M6에서 여유가 있을 때만 측정 후보다.
- **ASSUMPTION-60 (벌크 판독 예산)** — 30대 리그의 fid+xyz 회신이 페이로드 예산(1900) 안에 절단 없이 들어가거나, 절단 신호가 정확히 동작한다. 산술 고정 테스트 + M0 실측이 판정한다(design.md §7).

### C.3 상속 제약 (선행 SPEC 실측 — 재발 방지)

1. **콘솔의 `ok`는 미지 이름에 관대할 수 있다** `[실측 전재]` — SCENE-001 M0: 존재하지 않는 `/CueOnlyy`가 `ok`+저장. 본 SPEC의 프로퍼티 축에서도 같을 수 있으므로 **날조 대조군 없이 `ok`를 증거로 채택하지 않는다**(REQ-SPATIAL-026 (c)).
2. **슬롯≠FID** `[실측 전재]` — rig context 픽스처 항목의 번호는 컨테이너 내 위치이지 FID가 아니다(`rig_object` docstring). 공간 맵의 식별자 규율(REQ-SPATIAL-007)과 M0의 ASSUMPTION-57 판정이 이 함정을 전담한다.
3. **효과는 사람만 본다** `[확립]` — 모션·발색·웨이브 방향은 기계 확인 채널이 없다. 리포트 문면은 이 한계를 무조건 싣는다(FXLIB `EFFECT_EVIDENCE_NOTICE` 동형 상수).
4. **프로브 표적 분리** `[실측 전재]` — SCENE M0에서 프로브 A/B가 같은 표적을 공유해 대조군이 표적을 점유했다. 본 SPEC의 프로브는 픽스처·값 축에서 표적을 분리한다(REQ-SPATIAL-026 (d)).

### C.4 정렬 어휘의 기준 — `left/right`는 house(객석)다 `[실측, 소급 발견]`

**코드 동작은 옳고 용어가 기준을 말하지 않는다.** 후속 SPEC(GROUPGEN-001) 조사 중 발견해 §E.2.21에 기록했다.

MA Lighting 공식 문서 `[인수-웹, 규범]`: **+x = stage left** · *"Stage right will be negative numbers"* · +y = upstage · +z = height.
무대 관례상 **stage left/right는 배우 기준**이고 **house left/right는 객석 기준**이며 **둘은 정반대**다.

실증(x = −4 / 0 / +4 3대 리그): `left_to_right = (1, 2, 3)` 에서 `fid 1: x=−4.0` = stage **RIGHT** = house **LEFT**.

> **따라서 폐쇄 정렬 어휘 `left_to_right`는 house left → house right, 즉 stage RIGHT → stage LEFT 다.**
> 조명 디자이너가 *"stage left에서 stage right로"* 라고 하면 **이 정렬의 역방향**을 뜻한다.
> 한국어 "왼쪽/오른쪽"도 동일하게 house 기준으로 해석된다.

**개명하지 않는 이유**: `left_to_right`·`right_to_left`는 이미 출하된 폐쇄 집합이므로 개명은 파괴적 변경이다.
P8 라이브 관측에서 사용자가 3D 뷰의 "왼쪽"을 최소 x로 확인했고 코드가 그렇게 정렬했으므로 **동작·판정은 전부 유효하다**.
`SPATIAL_ROW_ORDER = "y_ascending"`("stage front to back")도 의미는 맞고 낱말만 비표준이다 — 표준 어휘는 `Downstage → Upstage`.

**후속 SPEC의 대응 선례**: GROUPGEN-001은 그룹 이름에 맨 `Left`/`Right`를 쓰지 않고 **기준을 이름에 박았다**
(`GEO Stage Right N` / `GEO Stage Left N`, 폐쇄 어휘 `_LATERAL_2/_3`). 그 버킷 index 0은 최소 x = stage right이므로
MA3 공식 축 의미와 일치한다 — 두 SPEC의 좌우 판정은 **같은 좌표를 같은 방향으로** 읽는다.

## D. 제외 범위 (Out of Scope)

### Out of Scope — 선제 재배치 제안

- 사용자 요청 없이 앱이 먼저 배치 변경을 제안·실행하는 축 일체. WRITE는 명시 요청 전용이다(REQ-SPATIAL-022 (b)).

### Out of Scope — 회전축 기록 (rotx/roty/rotz)

- v1은 회전값을 **기록하지 않는다**(판독은 허용). 회전 방향·단위의 실측이 없고, 잘못된 회전은 물리 리그에서 좌표 오류보다 위험하다(무빙 헤드 조사 방향).

### Out of Scope — GUI 레이아웃 뷰 전환

- 콘솔 GUI가 표시하는 레이아웃을 바꾸는 축 일체 — **Lua API가 존재하지 않는다는 것이 인수 조사로 확인됐다**(research.md §1). 화면 전환은 사용자 손에 남는다.

### Out of Scope — 서브픽스처 좌표

- 멀티셀 픽스처의 셀 단위 좌표·레이아웃 일체(선례 플러그인 gabe927/gma3-subfixture-layout의 영역). v1의 공간 단위는 픽스처 1대다.

### Out of Scope — MVR / GDTF 임포트

- 외부 파일 포맷 기반 배치 반입 일체. v1의 좌표 출처는 콘솔 판독뿐이다.

### Out of Scope — 물리 검증

- 트러스 구조·충돌·중력 등 물리적 타당성 검증 일체. WRITE의 좌표는 사용자 요청 형상의 산술일 뿐이다.

### Out of Scope — 다중 스테이지

- stage slot 1 외의 스테이지 판독·기록. `DEFAULT_RIG_CONTEXT_PATHS`의 stage 1 전제(라이브 실측 근거 주석)를 그대로 상속하며, 스테이지 자동 탐색을 발명하지 않는다.

### Out of Scope — Grid store 영속화 주경로

- `Grid store`로 커스텀 그리드를 그룹에 영속화하는 축을 v1 주경로로 삼는 것. 룰북 근거 0건·실측 0건(ASSUMPTION-59)이므로 v1은 매 발화마다 선택 순서로 실현한다. M6 여유 시 측정 후보로만 남긴다.

### Out of Scope — 기존 룰북 자산 변경

- `server/rulebook/assets/v2.4.2/00~31` 5개 파일 일체(PRESERVE — byte-diff 0). 신설은 `32_spatial_design.md` 1개뿐이다(REQ-SPATIAL-016).

### Out of Scope — executor layout 축 변경

- `server/looks/layout.py` · `server/orchestrator/layout_occupancy.py`(executor layout — 시퀀스→익스큐터 배선) 일체 무변경. 본 SPEC의 "spatial"과는 이름만 겹치는 다른 축이다(§A.2).

### Out of Scope — 콘솔측 응답기 무단 확장

- plan.md §F D-1이 신규 벌크 동사를 **채택하는 경우에만** `console/lua/copilot_responder.lua` + `PROTOCOL.md` + `server/bridge/protocol.py`가 EXTEND 대상이 된다. 채택하지 않으면 셋 다 PRESERVE다. 어느 분기든 기존 5동사·6 kind 형상과 프로토콜 버전 1은 무변경이다(가산성 — INTROSPECT-001과 동일 규율).

### Out of Scope — 재생 상태 판독

- 실행 여부·진행률·현재 큐 판독 축 일체 — SPEC-COPILOT-INTROSPECT-001의 영역이다.

## E. 참조 (연구 근거 — research.md, 구속력 있음)

| 필요 패턴 | 참조 원본 (file:line — 착수 직전 재실측 관례 적용) |
|---|---|
| rig context 픽스처 스냅샷에 좌표 축 0 | `server/orchestrator/tools.py:404-430` `rig_object` — `[코드]` |
| rig context 10경로 + stage 1 전제 | `server/orchestrator/tools.py:150-161` `DEFAULT_RIG_CONTEXT_PATHS` — `[코드]` |
| 드릴다운 쿼리 캡 16 + `drilldown_capped` 신호 | `server/orchestrator/tools.py:173, :455-491` — `[코드]` |
| 기존 판독 문(`prop` 동사) | `console/lua/copilot_responder.lua:643` `build_prop_result` · `PROTOCOL.md` §2(:55-70) — `[코드]` |
| 디스패치 가산 확장 지점 | `console/lua/copilot_responder.lua:876` `M.handle_request` — `[코드]` |
| 회신 예산 1900 + 조용한 드롭 | 응답기 `CONFIG.max_payload` + `server/tests/test_lua_responder_payload_budget.py` — `[코드]`+`[실측 전재]` |
| 패치 3D 좌표 판독·기록 (타 버전 실증) | research.md §1 — MA 포럼/help — `[인수-웹]` |
| Layout pool 구조 + 요소 주소 방식 + GUI 전환 API 부재 | research.md §1 — MA help/포럼 — `[인수-웹]` |
| 페이저 위상·MAtricks (검증된 문법) | `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:69, :82-94` — `[문서]` |
| 룰북에 실좌표 개념 0건·Grid 0건 | `server/rulebook/assets/v2.4.2/*.md` grep — `[측정]` |
| 룰북 정렬 조립 + byte-stable 접두 | `server/rulebook/assembly.py:62-63` · `server/tests/test_rulebook.py:1-33` — `[코드]` |
| 포지션 롤 6종 폐쇄 어휘 (통합 지점) | `server/looks/roles.py:1-16` — `[코드]` |
| executor layout ≠ spatial (어휘 구분) | `server/looks/layout.py:1-22` · `server/orchestrator/layout_occupancy.py:1-15` — `[코드]` |
| showfile 백업 3규칙 + restore SEND 부재(T-B2) | `server/safety/backup.py:1-26` — `[코드]` |
| 게이트 단일 관문 + 경계 AST 스캔 | `server/tests/test_architecture.py` · `test_looks_boundary.py` — `[코드]` |
| `ok` 비변별 실측 (날조 대조군 의무의 근거) | `SPEC-COPILOT-SCENE-001/progress.md §E.2` — `[실측 전재]` |
| 슬롯≠FID | `rig_object` docstring + SHOWUI 실측(실번호=i+100) — `[코드]`+`[실측 전재]` |
| 닫힌 툴 집합 18 | `server/orchestrator/tools.py` `build_toolset` `ToolDefinition(` 18건 — `[측정]` |
| 프로브 표적 분리 규율 | SCENE-001 M0 승계 결함 기록 — `[실측 전재]` |
