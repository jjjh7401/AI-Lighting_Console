# SPEC-COPILOT-GROUPGEN-001 — 진행 기록 (progress)

status: **pre-plan** · plan-phase 미실행 · 구현 0 · 커밋 0 · 라이브 접근 0(조사 제외)

## §0 인수인계 — 여기서 시작한다 (2026-08-03 작성)

### 한 문단

**무엇**: **배치의 위상(topology)을 판별해 그 성격에 맞는 어휘로 그룹을 만들고 라벨을 붙인다.**
깊이 방향 행이면 Front/Center/Back, 2겹 동심원이면 Inner/Outer, 좌우 분할이면 Left/Right —
**이름은 결과이고 판별이 본체다.** Front/Center/Back은 사용자가 든 하나의 예시일 뿐이며,
고정 사상표를 만드는 것이 아니다.

**왜**: SPATIAL-001의 선택 순서는 프로그래머 상태이고 `ClearAll`로 사라진다 — 웨이브 *방향*에는
충분하나 *"뒷줄만 파랗게"* · *"바깥 링만 반짝"* 은 표현할 수 없다. 그룹은 쇼파일에 **영속**하므로
앱이 `Group <n>` 한 줄로 부분 리그를 잡고 **사용자가 콘솔에서 손으로도** 쓴다.
선택 순서와 그룹은 경쟁이 아니라 보완이다 — **그룹 = 누구, 선택 순서 = 어떤 순서로.**

**상태**: `spec.md`(v0.1.0 · **REQ 30건 · ASSUMPTION 61~67**) + `research.md`(v0.5.0) +
`plan.md`(v0.1.0) 존재. **`acceptance.md`(AC) · `design.md`는 없다** — `/moai plan`이 만든다.
브랜치 준비됨. 구현 0 · 라이브 쓰기 0.

**이 SPEC의 두 축**:
1. **위상 분류기** (신규 · 순수) — 현재 계층은 y축 행 검출 **하나만** 하며, 행이 아닌 위상을
   **고신뢰로 오독한다**(함정 3).
2. **그룹 쓰기** (신규 · 콘솔) — 단, 멤버십 검증 채널의 존재가 **미확정**이다(함정 1).

### 읽는 순서

1. **`research.md` §2 (멤버십을 읽을 수 없다)** — 이 SPEC의 GO/NO-GO다. 먼저 읽어야 나머지 설계가
   왜 그렇게 생겼는지 이해된다.
2. **`research.md` §3 (현재 계층의 고신뢰 오독)** — 2겹 동심원 → 9행 고신뢰. 위상 분류기가 필요한 이유.
3. **`spec.md`** — REQ 30건 · ASSUMPTION 61~67 · 검증 천장(§C.1) · 제외 범위(§D). 요구의 정본이다.
4. **`plan.md` §A.2(결정 우선순위) → §A.4(M0 게이트 분기표) → §C.0(축 제외표) → §B(M0~M6) → §D(열린 질문)**
5. **`research.md` §6 (업계 표준 어휘)** — MA3 공식 축 의미 · 표준 어휘 · stage/house 함정. **어휘를 발명하기 전에 반드시 읽을 것.**
6. **`research.md` §7 (세분화 축 6개)** — 무엇이 범위 밖이고 **왜** 그런지. 축 E가 MAtricks와 중복임을 놓치면 콘솔 기능을 재구현한다.
7. **`research.md` §5(라이브 실측)** — 다시 재지 말고 그대로 쓸 값.
8. **`SPEC-COPILOT-SPATIAL-001/progress.md` §E.2.14 · §E.2.18 · §E.2.20** — AC-031 되돌림의 대가 ·
   미검증 축이 낳은 결함 · 라이브 E2E 결함 2건. **이 SPEC의 위험이 전부 여기서 나온다.**

### 함정 (다음 소유자가 알아야 할 것)

1. **그룹 멤버십을 읽을 수 없다** — `Group 13 'All'`은 `exec`이 `OK`인 실사용 그룹인데 `query_state`는
   `childCount: 0`을 준다(`research.md` §2 실측). `0`은 "비었다"가 아니라 **"이 채널로는 안 보인다"**다.
   → 재조회 검증·백업이 원리적으로 불가할 수 있고, 저장소 최상위 규율(*"`ok`는 증거가 아니다"*)을
   적용할 수단이 사라진다. **M0-P1이 이 SPEC의 GO/NO-GO다.**
2. **점유 슬롯 덮어쓰기는 백업도 복구도 불가** — 멤버십을 못 읽으니 백업 불가, `Delete`는 블랙리스트,
   restore SEND 부재(T-B2). **차단은 선호가 아니라 강제 제약**이다.
3. **현재 분석 계층은 행이 아닌 위상을 고신뢰로 오독한다** — 2겹 동심원을 넣으면
   `rows=9`, 구성 `[1,2,2,2,4,2,2,2,1]`, `low_confidence=False`(실측). 반지름은 2.0/5.0으로 완벽히
   갈리는데 y축 갭에는 안 보인다. **위상 분류기가 이 SPEC의 본체다.**
4. **`Front`·`Back`·`Inner Outer Opp`가 이미 존재한다** (no 11·12·15). 사용자 예시 어휘와 정면 충돌하며
   함정 2에 따라 덮어쓰기는 배제된다.
5. **`Group 11`은 룰북의 검증된 페이저 예시가 쓴다**(`31_choreography_patterns.md:48,67,163`).
   건드리면 룰북 문면이 거짓이 된다.
6. **그룹 슬롯은 비연속**(1·11·12·13·15 — 2~10·14가 빔). "다음 번호"를 세면 틀린다.
   `server/scene/compile.py::_select_cue_number`가 선례이며 **절단이면 자동 할당을 거부**한다.
7. **절단**: `childCount 19` vs 반환 **18**. 18대만 담긴 그룹이 조용히 **영속**한다.
   선택은 `ClearAll`로 사라지지만 잘못된 그룹은 남는다.
8. **좌표 기록이 현재 무승인으로 나간다** — AC-SPATIAL-031 `[DEFERRED]`. 요청하지 않은 기록 54건이
   실제로 통과한 관측 사례가 있다(SPATIAL §E.2.20 결함 2). 같은 사고가 **복구 불가 자산**에서 일어나면
   끝이다. `plan.md` Q4가 이 SPEC의 최우선 결정이다.
9. **어휘를 발명하지 말 것 — 업계 표준이 있다**(`research.md` §6). 깊이는 `Front/Back`이 아니라
   **Downstage / Center / Upstage**다. 그리드는 이미 표준 9칸 명명(`DSR…USL`)이 있다.
   **동심원만 표준이 없다** — 그 사실을 명시해야 한다.
10. **⚠ 좌우는 기준이 반대다.** stage left/right(배우 기준)와 house left/right(객석 기준)는 정반대이며
    MA3는 **+x = stage left**로 정의한다(공식 문서). 실증 결과 **SPATIAL의 `left_to_right`는 실제로
    house left → house right(= stage RIGHT → stage LEFT)** 다 — 디자이너가 "stage left에서
    stage right로"라고 하면 역방향이다. **그룹 이름에 맨 `Left`/`Right`를 쓰지 말 것.**
11. **전문가는 위치가 아니라 기능으로 묶는다** — 실제 단위는 **"system"**(front light system ·
    backlight system · cross-left/right sidelight system)이며 채널 번호도 그걸로 조직한다.
    기하 그룹은 기능 그룹을 **대체하지 않고 보완**한다. `Downstage`를 쓰는 이유가 표준 준수만이
    아니라 **기능 어휘 충돌 회피**이기도 하다 — `Front`는 front light system으로 읽힌다.
12. **장비 종류(C1)는 2-hop으로 읽힌다** `[실측]` — 픽스처 `fixturetype` → `'FixtureType 1'` →
    `Patch/FixtureTypes/1` → `name`(`'Robin MMX Spot'`) · `ShortName`(`'RMMXSm1'`) ·
    `Manufacturer`(`'Robe'`). 날조 대조군 3/3 FAIL로 채널 변별적. **단 GDTF 스펙에 `Categories`
    필드가 없어** Spot/Wash/Beam은 **타입명 토큰 매칭**뿐이다 — 폐쇄 어휘 + 무매칭→그룹없음.
13. **⚠ 장비 명칭(C2)으로 그룹을 자동 생성하지 말 것.** 우리 리그 실측: 동일 타입 19대에 명명 패턴
    **3가지**(자동 `RMMXSm1 1` = `ShortName`+번호 · 사용자 `Copilot MMX n` · 사용자 `MMX n`).
    이름 그룹은 의미 없는 3그룹을 **영속**시킨다. 자동 작명 패턴은 구별 가능하므로 *제안*까지만.
14. **이 리그는 완전 동종이다**(`Patch/FixtureTypes` childCount **1**). 타입 축은 여기서 아무것도
    나누지 못한다 — golden은 **합성 이종 리그**로 만들고, M6 타입 판정은 `SKIP:` 이 정직하다.
15. **`Blinder`는 관객을 비춘다.** 무대 위상 그룹에 섞이면 연출이 관객을 때린다 — 분리 규칙 필수.
16. **⚠ 세분화 축 6개 중 4개가 범위 밖이다**(`research.md` §7 · `plan.md` §C.0).
    특히 **축 E(홀짝·윙·블록·셔플)는 MAtricks가 이미 한다** — MA3 공식 기능이고 룰북 `31:85-90`이
    검증된 문법으로 싣고 있다. **그룹으로 재구현하면 콘솔 기능 중복이다.**
    3층 관계를 기억할 것: 그룹=누구 · 선택순서=어떤 순서로 · MAtricks=어떻게 재성형.
17. **과약속 금지** — *"연출 의도에 맞게"* 는 *"의도를 자동 해석한다"* 가 아니다. 좌표는 장비가
    어디 있는지만 안다. 정직한 약속은 **"연출에 쓸 수 있는 형태로 위치 그룹을 만들어 둔다"**.
18. **의존: SPATIAL-001 미머지.** 본 브랜치는 `115eb6d`에서 분기했다. **main 머지 후 rebase할 것.**
19. **Gemini 스키마**: `additionalProperties`는 자동 제거된다(커밋 `a5fa16a`). 단
    `_GEMINI_UNSUPPORTED_KEYS`는 DENY 리스트라 다른 미지원 키워드는 요청 전체를 400으로 죽인다.
20. **한 턴 예산** `DEFAULT_MAX_MODEL_CALLS = 12` — *"배치 + 그룹 + 연출"* 복합 지시는 `loop_limit`
    (부분 실행)이 된다. 실측 확인됨.
21. **M0 프로브 정리 경로를 프로브 전에 정하라** — `Delete`가 블랙리스트다. SCENE M0가 "시퀀스 7개
    GUI 삭제" 부채를 남긴 실수를 반복하지 말 것. **빈 슬롯 1개만** 표적으로 쓴다.

### 착수 키트

- **첫 명령**: `/moai plan SPEC-COPILOT-GROUPGEN-001` (브랜치 준비됨 — `--branch` 불필요).
  `spec.md`가 이미 있으므로 plan-phase는 **AC 도출 + design 확정 + 열린 질문 닫기**가 주 업무다.
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
