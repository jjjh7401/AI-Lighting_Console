# SPEC-COPILOT-SPATIAL-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 타 SPEC 아티팩트**에만 쓰고, **각 마일스톤 착수 직전 재실측**한다. 근거 등급 `[코드]` · `[문서]` · `[측정]` · `[실측]` · `[인수]` · `[인수-웹]` · `[미확정]` — **`[실측]`은 본 세션의 라이브 콘솔 직접 관측만**이다.

## §0 인수인계 — 여기서 시작한다 (2026-08-03 작성, plan-phase)

### 한 문단

**무엇**: 앱을 배치 인식으로 만드는 양방향 공간 축 — **READ**(패치 3D `posx/posy/posz` + Layout pool 판독 → 행 검출·정렬 → **선택 순서**로 배치에 맞는 연출)와 **WRITE**(사용자 요청 시 grid/row/circle 프리셋으로 픽스처 3D 좌표 기록 — 원좌표 백업·재조회 검증·복원 번들 의무). 핵심 원리는 하나다: **MA3에서 웨이브 방향은 좌표가 아니라 선택 순서가 정한다** — 좌표는 서버측 정렬의 입력일 뿐, 커맨드에 실리지 않는다.

**상태**: **plan-phase 산출물만 존재 (draft v0.2.0 — plan-audit fold-in 반영).** 구현 0 · 커밋 0 · 라이브 0. base `origin/main` = `3176900`, branch `feature/SPEC-COPILOT-SPATIAL-001`. REQ **26** · AC **32** · Out of Scope **12항** · ASSUMPTION **53~60**(전역 카운터 — INTROSPECT-001이 52까지 사용) · 열린 질문 **5건**(plan.md §F D-1~D-5) · 라이브 세션 **2회(M0·M6)**.

**이 SPEC의 한 줄**: *1행×30과 3행×10에 같은 커맨드를 내는 앱은 배치를 모르는 앱이다* — rig context 픽스처 스냅샷에 좌표 축이 0이라는 사실(`tools.py:404-430`)이 이 SPEC을 요구했다.

### 읽는 순서

1. **`spec.md` §A.1(선택 순서 원리) · §A.2(spatial ≠ executor layout) · §A.4(M0 게이트)** — 이 셋이 설계 전체를 규정한다. §A.2를 건너뛰면 `server/looks/layout.py`를 이 SPEC의 것으로 오독한다.
2. `spec.md` §C.1(검증 천장 — 효과는 사람만 본다) → §C.2(ASSUMPTION-53~60) → §D(제외 12항 — 특히 rot* 기록·Gridstore 주경로·선제 재배치)
3. **`design.md` §2(판독 채널 2후보) · §5(M0 프로브 사다리 P1~P9 — 표적 분리 명단) · §6(WRITE 안전) · §7(예산 산술)** — §5가 이 SPEC의 중심 방어선이다.
4. `plan.md` §A.1(리뷰 순서) → §A.3(**M0 축별 분기표 — READ NEGATIVE = SPEC 전체 중단**) → §B(M0~M6) → §F(**열린 질문 5건 — run 진입 전 해소**)
5. `acceptance.md` §C(AC 32건 — 뮤테이션 필수 5건: 004·006·019·020·031) → §F(DoD, 특히 항목 5의 협상 불가 목록)
6. `research.md` §1(인수 웹 조사 — **전건 타 버전 실증, 우리 콘솔 미측정**) · §4(룰북에 실좌표 개념 전건 0) · §7(restore SEND 부재 — 복원=재기록의 근거)

### 함정 (다음 소유자가 알아야 할 것)

1. **웹 조사는 실측이 아니다.** research.md §1은 전부 `[인수-웹]`(타 버전 포럼/문서)이다. 프로퍼티 이름 대소문자부터 미검증 — M0 전에 어떤 코드도 이 이름들 위에 세우지 말 것.
2. **READ NEGATIVE = SPEC 전체 중단이다.** WRITE·Layout NEGATIVE는 축별 `[DEFERRED]`지만, 좌표 판독이 안 되면 아무것도 성립하지 않는다. 대체 정책을 에이전트가 고르지 않는다(블로커 보고 — plan.md §A.3).
3. **콘솔의 `ok`는 미지 이름에 관대할 수 있다.** SCENE-001 M0 실측(`/CueOnlyy`가 `ok`+저장). 날조 대조군(P2/P6) 없이 `ok`를 증거로 쓰면 이 SPEC의 전제가 무너진다. 대조군이 `ok`로 통과하면 **그 사실 자체가 판정**이다(`CONDITION_NOT_MET` → 값 대조 대체).
4. **슬롯≠FID.** rig context 픽스처 번호는 컨테이너 내 위치다. 좌표 맵의 식별자는 콘솔이 돌려준 것만 쓰고(REQ-SPATIAL-007), `Fixture <fid>` 주소 가능성은 P8이 판정한다(ASSUMPTION-57).
5. **웨이브 방향은 기계로 확인할 수 없다.** 선택 순서→방향(ASSUMPTION-58)은 사람 GUI 관측만이 판정한다. AC-SPATIAL-028/029에 기계 증거를 주장하면 그 판정이 결함이다(spec.md §C.1).
6. **"layout"이라는 낱말을 조심하라.** `server/looks/layout.py` · `server/orchestrator/layout_occupancy.py`는 executor layout(시퀀스→익스큐터 배선)이며 본 SPEC과 무관·무변경이다. 본 SPEC의 식별자는 전부 `spatial` 접두.
7. **WRITE 프로브는 원상복구까지가 한 프로브다.** 좌표는 재기록으로 되돌릴 수 있어 `Delete` 블랙리스트 문제가 없다 — SCENE M0의 "시퀀스 7개 GUI 삭제" 부채를 만들 이유가 없다. 복구 미완 종료는 즉시 블로커(AC-SPATIAL-027).
8. **showfile 백업은 되돌릴 수단이 아니다.** restore SEND 경로가 의도적으로 없다(T-B2 — research.md §7). WRITE의 복원은 **원좌표 재기록 번들**뿐이다.
9. **응답기 버전 1.6.0은 INTROSPECT-001이 예약했다.** D-1/D-2가 신규 동사를 채택하면 먼저 머지되는 쪽이 1.6.0(plan.md §F D-5). 무단으로 1.6.0을 잡지 말 것.
10. **룰북에는 라이브 확인분만 싣는다.** 31의 "(validated)" 규율 — 32_spatial_design.md에 M0/M6 미확인 문법을 실은 채로 닫으면 DoD 위반(acceptance §F-8).
11. **절단 테스트 재료는 상한을 넘겨야 한다.** 오늘의 리그가 예산 미만이면 절단 코드를 제거해도 통과한다 — 30대 xyz는 1900 경계 부근이라 이 함정이 실재한다(design.md §7).
12. **(0,0,0) 전대는 "데이터 없음"이 아니다.** 판독 성공한 실좌표이며 저신뢰 신호+강등의 대상이다(acceptance §D edge).

### 다음 소유자의 착수 키트

- **다음 단계**: plan-audit → Implementation Kickoff Approval → **M0(라이브 프로브)**. M0는 실물 onPC 접근을 요구하며, 그 전까지 진행 가능한 것은 없다(M1~M6 전부 M0 판정에 걸려 있다).
- **run 진입 전 해소 필요**: plan.md §F의 열린 질문 5건 — D-1(판독 채널) · D-2(기록 채널) · D-3(Layout 기록 범위) · D-4(툴 표면 2툴/개수 20) · D-5(응답기 버전 조율). D-1/D-2는 M0 실측이 결정 재료이므로 "M0 후 확정"으로 승인받는 것이 정직하다.
- **M0 준비물**: 물리 좌표를 아는 픽스처 최소 8대(P1~P9 표적 분리 명단 — design.md §5), 프로브별 기록지, GUI 관측자(사람).
- **기준선 재측정 의무**: run-phase 킥오프 시점에 pytest/vitest 기준선을 **다시 측정한다.** plan-phase 수치 재사용 금지.

---

## §E.1 Plan-phase Audit-Ready Signal

- **산출물**: `spec.md` · `plan.md` · `acceptance.md` · `design.md` · `research.md` · `progress.md` (6종)
- **Tier 판정**: **L** — 콘솔 판독·기록 채널(조건부 Lua 확장) + 신규 순수 패키지 + 툴 2종 + 룰북 신설 + 안전 통합, 예상 변경 10~14파일. 라이브 콘솔 의존 마일스톤 2건(M0·M6) + 축별 분기 게이트 5건(plan.md §A.3). 쇼파일 기록(WRITE) 축 보유. 선례 SPEC-COPILOT-SCENE-001·INTROSPECT-001(동일 형상: 라이브 프로브 선행 + 조건부 응답기 확장)이 Tier L.
- **base**: `origin/main` = `3176900` · branch `feature/SPEC-COPILOT-SPATIAL-001`. 인용 파일의 줄번호는 이 base 기준.
- **SPEC ID 자기검사**: `decomposition: SPEC ✓ | COPILOT ✓ | SPATIAL ✓ | 001 ✓ → PASS` (정규식 `^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$` Bash 실행 결과 `PASS`)
- **구현 범위**: 코드 변경 **0건** · 커밋 **0건** · 라이브 접근 **0건** (plan-phase 계약대로 문서만)
- **열린 질문**: **5건** (plan.md §F D-1~D-5 — run 진입 전 해소 필요; D-1/D-2는 M0 실측 후 확정 권고)
- **미해소 ASSUMPTION**: 53~60 (8건, 전부 M0/M6에 확정 마일스톤 배정됨 — plan.md §A.3 분기표; 미프로브 전제 56/59는 M0 시점 `SKIP:` 행 처리)
- **plan-audit fold-in (v0.2.0)**: PASS-WITH-DEBT 0.86 지적 10건 전건 반영(M1~M4·m5~m10 — spec.md HISTORY 0.2.0 행 참조). 최종 카운트 REQ 26 · AC 32(신설: AC-SPATIAL-031 risky 분류·AC-SPATIAL-032 look/fx/scene PRESERVE; 뮤테이션 필수 5건: 004·006·019·020·031). C1(plan.md §F D-1~D-5)은 킥오프 게이트 대상으로 미변경.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
