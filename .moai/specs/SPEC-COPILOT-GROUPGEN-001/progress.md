# SPEC-COPILOT-GROUPGEN-001 — 진행 기록 (progress)

status: **pre-plan** · plan-phase 미실행 · 구현 0 · 커밋 0 · 라이브 접근 0(조사 제외)

## §0 인수인계 — 여기서 시작한다 (2026-08-03 작성)

### 한 문단

**무엇**: 배치를 그룹으로 굳힌다. `arrange_fixtures`가 만든 공간 구조(검출된 행)를 콘솔 Group 풀의
**영속 자산**으로 저장하고, 행마다 의미 있는 이름(Front / Center / Back …)을 붙여 기존 연출·이펙트
경로(`Group <n>` → 페이저 / MAtricks)에 바로 쓰이게 한다.

**왜**: SPATIAL-001의 선택 순서는 프로그래머 상태이고 `ClearAll`로 사라진다. 매 발화가 순서를 다시 세운다.
그룹은 쇼파일에 남으므로, **배치 인식의 결과를 사용자가 콘솔에서 손으로도 쓸 수 있는 자산으로 바꾼다.**

**상태**: **`research.md` 하나만 존재한다.** `spec.md` · `plan.md` · `acceptance.md` · `design.md`는
없다 — `/moai plan`이 만든다. 브랜치는 준비됨.

### 읽는 순서

1. **`research.md` §3 (라이브 실측)** — 직전 세션이 실제 콘솔에서 잰 값이다. 다시 재지 말고 그대로 쓸 것.
2. **`research.md` §4 (열린 질문 Q1~Q8)** — plan-phase가 닫아야 하는 것 전부. Q3(이름 충돌)과
   Q6(승인 흐름)이 가장 무겁다.
3. **`research.md` §5 (승계할 규율)** — SPATIAL이 값을 치르고 배운 7가지. 특히 7번(그룹은 `Delete`가
   블랙리스트라 프로브 정리 경로를 **설계 단계에서** 정해야 한다).
4. **`SPEC-COPILOT-SPATIAL-001/progress.md` §E.2.14 · §E.2.18 · §E.2.20** — 각각 AC-031 되돌림의
   대가 · Z축 미검증 축이 낳은 결함 · 라이브 E2E에서 관측된 결함 2건. 이 SPEC의 위험이 전부 여기서 나온다.

### 함정 (다음 소유자가 알아야 할 것)

1. **`Front`·`Back` 그룹이 이미 존재한다** (no 11, 12 — `research.md` §3.1 실측). 사용자가 예시로 든
   이름과 **정면 충돌**한다. 덮어쓰면 LD 자산이 사라진다. 에이전트가 조용히 고르지 않는다.
2. **`Group 11`은 룰북의 검증된 예시가 쓰고 있다** (`31_choreography_patterns.md:48,67,163`).
   11을 건드리면 룰북 문면이 거짓이 된다.
3. **그룹 슬롯은 비연속이다** (1, 11, 12, 13, 15). "다음 번호"를 **세면 틀린다** — 재조회 실측으로
   빈 슬롯을 찾는다. `server/scene/compile.py::_select_cue_number`가 그 패턴의 선례다.
4. **그룹은 좌표보다 되돌리기 어렵다.** 좌표는 재기록으로 복원되지만, 점유 슬롯에 `Store Group`을 쏘면
   기존 멤버십이 사라지고 **복구 경로가 없다**(`Delete`는 블랙리스트, restore SEND 부재 — T-B2).
5. **`Store Group`(무플래그)은 블랙리스트에 없다.** 점유 슬롯 덮어쓰기가 게이트를 통과하는지 **미확정** — M0 프로브 대상.
6. **좌표 기록이 현재 무승인으로 나간다.** AC-SPATIAL-031 `[DEFERRED]` 때문이며, 요청하지 않은 기록
   54건이 실제로 통과한 관측 사례가 있다(SPATIAL §E.2.20 결함 2). 그룹 생성을 승인 없이 열면 같은 사고가
   **되돌릴 수 없는 자산**에서 일어난다. Q6이 이 SPEC의 최우선 결정이다.
7. **절단**: `childCount 19` vs 반환 **18**. 18대만 담긴 그룹이 조용히 만들어져 **영속**할 수 있다.
   선택은 사라지지만 잘못된 그룹은 남는다.
8. **`ok`는 증거가 아니다.** 재조회로 멤버십을 확인해야 한다. 선례 2건이 `research.md` §5-1에 있다.
9. **의존: SPATIAL-001이 미머지다.** 본 브랜치는 그 위에서 분기했다. **main에 머지되면 rebase할 것.**
10. **Gemini 스키마**: `additionalProperties`는 이미 자동 제거된다(커밋 `a5fa16a`). 단 다른 미지원
    키워드를 쓰면 요청 전체가 400으로 죽는다 — `_GEMINI_UNSUPPORTED_KEYS`는 DENY 리스트다.
11. **한 턴 예산**: `DEFAULT_MAX_MODEL_CALLS = 12`. *"배치 + 그룹 + 연출"* 복합 지시는 이 예산을 넘겨
    `loop_limit`(부분 실행)이 된다 — 실측 확인됨. 툴 표면을 설계할 때 왕복 수를 고려할 것.

### 착수 키트

- **첫 명령**: `/moai plan SPEC-COPILOT-GROUPGEN-001` (브랜치 준비됨 — `--branch` 불필요)
- **ASSUMPTION 번호**: **61부터** (전역 카운터: INTROSPECT ~52, SPATIAL 53~60)
- **M0 라이브 프로브가 필요하다**: Q1(그룹 생성 채널)·Q4(점유 슬롯 안전)는 실사격만 답한다.
  물리 onPC 접근 + **정리 경로 사전 결정**(함정 4) 필요.
- **기준선 재측정 의무**: run-phase 킥오프 시점에 pytest/vitest를 **다시 측정**한다.
  참고 수치(2026-08-03, GROUPGEN 착수 시점): pytest **4511 passed · 5 skipped · 0 failed** ·
  vitest **350 passed**. ruff는 손대지 않은 파일의 기존 부채 **3건**(`server/safety/console.py` ×2 ·
  `server/tests/test_web_dash.py` ×1)이 있으며 이는 신규 결함이 아니다.

### 환경 상태 (직전 세션이 남긴 것)

- **앱이 실행 중일 수 있다** — `http://127.0.0.1:8765`, 수신 포트 **9005** 점유.
  새 세션에서 앱을 다시 띄우려면 **먼저 기존 인스턴스를 끄거나** `ReceivePortInUseError`로 실패한다
  (`server/bridge/osc.py:242` — *"No automatic port fallback"*, SPATIAL §E.2.10에서 실증).
  확인: `curl -s http://127.0.0.1:8765/healthz` · 종료: 해당 프로세스 종료(포트 8765/9005 점유자).
- **리그는 원점 상태**: 19대 전부 `(0,0,0)`, 프로그래머 `ClearAll`, 쇼파일 잔여 0.
- **그룹 풀은 손대지 않았다**: 1 / 11 / 12 / 13 / 15 (조사 시점 그대로).
- 앱 설정 정본: `~/Library/Application Support/GrandMA3 Copilot/settings.toml`
  (`console_port = 8000` · `receive_port = 9005` · `osc_slot = 2`).
  **주의**: `console/lua/README.md` §4의 예시 포트 `9000`은 이 설치에서 틀리다(SPATIAL §E.2.0).

## §E.1 Plan-phase Audit-Ready Signal

_<pending plan-phase>_

## §E.2 Run-phase Evidence

_<pending run-phase>_
