# SPEC-COPILOT-GROUPGEN-001 — 진행 기록 (progress)

status: **run-phase M0~M6 완료 + amendment v0.5.0 완료 · 잔여 SKIP 0건** · 머지 전 독립 리뷰 4인이 P0 1건(승인 무결성)+P1 3건 소인 · 타입 축 라이브 GO · Gemini 턴 GO · 그룹 축 쇼파일 순변화 **0**

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

- **⚠ 이 항목은 2026-08-04 세션이 정정했다.** 직전 세션은 *"앱이 UDP 9005를 점유하니 있으면 종료"*
  로 인계했으나, **9005의 실제 점유자는 grandMA3 onPC 자신**(`app_gma3` — `UDP *:8000` + `UDP *:9005`
  와일드카드)이고 이는 **정상 상태**다. 코파일럿 앱은 `_ReuseAddrOSCUDPServer`가
  `allow_reuse_address = True`(`server/bridge/osc.py:60` 부근)라 **SO_REUSEADDR로 9005에 공존 바인드된다**.
  본 세션 실측: `SO_REUSEADDR` 바인드 **성공** / 평범 바인드 `errno 48`.
  → **onPC를 종료하면 안 된다.** M0·M6 라이브 프로브가 그 콘솔을 필요로 하며, 종료해도 얻는 것이 없다.
  (LOOKLIB·EXECREF가 *"구동 중 onPC의 9005 점유"*를 **환경적 기존 조건**으로 이미 기록해 둔 그 사실이다.)
- **판별 기준**: 끄고 시작해야 하는 것은 **코파일럿 앱 인스턴스**이며 그 지표는 **TCP 8765**다
  (`lsof -nP -iTCP:8765` · `curl -s http://127.0.0.1:8765/healthz`). UDP 9005 점유는 지표가 아니다.
  본 세션 착수 시 8765는 **비어 있었다**(스테일 인스턴스 0).
- **리그는 원점 상태**: 19대 전부 `(0,0,0)`, 프로그래머 `ClearAll`, 쇼파일 잔여 0.
- **그룹 풀은 손대지 않았다**: 1 / 11 / 12 / 13 / 15 (조사 시점 그대로).
- 앱 설정 정본: `~/Library/Application Support/GrandMA3 Copilot/settings.toml`
  (`console_port = 8000` · `receive_port = 9005` · `osc_slot = 2`).
  **주의**: `console/lua/README.md` §4의 예시 포트 `9000`은 이 설치에서 틀리다(SPATIAL §E.2.0).

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-08-04T00:40:00Z
- plan_status: **audit-ready**
- plan_audit_verdict: **CONDITIONAL-PASS → 조건 해소 완료** (BLOCKER 0 · MAJOR 2 → **0** · MINOR 0)
- plan_audit_report: `.moai/reports/plan-audit/SPEC-COPILOT-GROUPGEN-001-plan-audit.md`
- 산출물: `design.md`(신규) · `acceptance.md`(신규 · AC 37건) · `spec.md` v0.2.0 · `plan.md` v0.2.0
- 결정 기록: `.plan-contract.md` (사용자 승인 3건 + coordinator 증거 확정 6건)
- 소스 코드 diff: **0** (plan-phase는 문서 단계 · 콘솔 무접촉 · 라이브 프로브 0)

### 실행 형태 — Orca 오케스트레이션 3-워커 병렬 + 감사 게이트

Run `run_5f9ccdfbf0b6`. 파일 무교차 계약(`.plan-contract.md` §4)을 사전 고정한 뒤 병렬 1웨이브:

| 워커 | Task / Dispatch | 산출 | 결과 |
|---|---|---|---|
| A | `task_a7abcd6778e4` / `ctx_8d1cce449ea2` | `design.md` | succeeded |
| B | `task_72908baf7b3a` / `ctx_136692c04130` | `acceptance.md` | succeeded |
| C | `task_38ebfd0a126f` / `ctx_a7c03315835c` | `spec.md` + `plan.md` v0.2.0 | succeeded |
| D (게이트) | `task_dc774e9780ab` / `ctx_b0d2879ec52b` | plan-audit 리포트 | succeeded · CONDITIONAL-PASS |

### coordinator가 감사에서 잡아 메운 결함 3건 (워커 자기보고로는 드러나지 않았다)

1. **REQ↔AC 커버리지 공백 (coordinator 자체 감사)** — `REQ-GROUPGEN-031`(안전 게이트 확장)에
   대응 AC가 **없었다**. 원인은 계약 설계 실수다: 워커 C에게 *"신규 REQ는 031부터"*,
   워커 B에게 *"추가 AC는 031부터"* 를 **독립적으로** 지시해 번호가 충돌했다.
   → `AC-GROUPGEN-036` 신설로 해소. **REQ 031 ↔ AC 036이며 번호가 어긋난다**(문서에 명시).
2. **MAJOR-1 스키마 자기모순 (plan-auditor)** — `design.md`가 `TopologyResult.fids_by_bucket`을
   `tuple[tuple[int,...],...]`로 타입 고정하면서, grid 분기에서는 같은 필드에
   `{"depth": …, "lateral": …}` **딕셔너리**를 넣는다고 서술했다. M1∥M2 병렬이 의존하는
   교차 스키마 계약이 바로 그 지점에서 깨진다.
   → 전용 필드 `grid_axes`를 분리하고 **타입 불변식**을 명문화해 해소
   (`kind == "grid"` ⟺ `fids_by_bucket == ()` and `grid_axes is not None`).
   부수로 `Stage Right/Center/Stage Left` → `Centerline` 누락 1건도 정정(D-Q2 위반).
3. **MAJOR-2 뮤테이션 계약 불이행 (plan-auditor)** — `plan.md` §B M5가 뮤테이션 필수 **5항목**을
   약속했는데 `acceptance.md`는 **4개**만 실었다. 누락은 *"임의 작명 금지"* 이며, 대응 AC들이
   전부 **정적 grep**이라 *"금지 로직을 제거하면 빨개지는가"*를 증명하지 못했다.
   → `AC-GROUPGEN-037` 신설(반환값 폐쇄집합 전수 대조 + 적대적 입력 + f-string 보간 뮤테이션)로
   5:5 정합. **정적 grep만으로는 통과시킬 수 없다.**

> **교훈 (다음 소유자에게)**: 워커 4인 전원이 `outcome: succeeded` 로 자기보고했고 그 보고는
> 거짓이 아니었다. 그러나 위 3건은 **어느 워커의 담당 범위 안에도 없었다** — 1은 coordinator가
> 만든 계약의 결함이고, 2·3은 **문서 사이의 경계**에 있었다. `worker_done` 은 산출물 수용이 아니다.
> 병렬 저작에서는 **교차 계약 자체를 감사 대상으로 삼아야 한다.**

### plan→run 경계 (다음 세션이 여기서 시작한다)

- **Implementation Kickoff Approval(HUMAN GATE)은 아직 받지 않았다.** `/moai run` 진입 전 필수.
- **Q1(멤버십 판독 채널)은 `[OPEN-BY-DESIGN]`** — M0 라이브 프로브(run-phase)만이 답한다.
  plan은 GO/NEGATIVE **양 분기를 모두 설계**했다. GO를 기본값으로 가정한 서술 **0건**(감사 확인).
- **기준선 재측정 의무**: run 킥오프 시점에 pytest/vitest 재측정. plan-phase 참고 수치
  (2026-08-03 pytest 4511 · vitest 350) **재사용 금지**(AC-034).
- **의존**: SPATIAL-001 미머지. 본 브랜치는 `115eb6d` 분기 · 현 HEAD `f49020b`.
  `git branch --contains 1c72d3e | grep main` → 비어 있음(정상). **main 머지 후 rebase.**

## §E.2 Run-phase Evidence

### §E.2.0 M0 라이브 프로브 — 세션 조건 (직접 실측 · 이월 0)

승인: Implementation Kickoff Approval **반자율** 획득(2026-08-04). 워크트리 격리 실행 —
`/Users/studiox/orca/workspaces/AI-Lighting_Console/groupgen-m0` @ `5ce471f`
(주 워킹트리는 **타 작업자가 `feature/SPEC-COPILOT-MCP-001`로 점유** 중이라 건드리지 않았다).

| 항목 | 값 |
|---|---|
| 콘솔 | grandMA3 onPC 2.4.2 · `app_gma3` pid **1106** (2026-08-02 19:31 기동) |
| OSC | send `127.0.0.1:8000` / receive **9005** · `osc_slot` 2 |
| 앱(코파일럿) | **미기동**(TCP 8765 비어있음) — 프로브는 `.moai/reports/m0-probe/fx_probe.py` **bridge 직결** |
| 채널 등급 | `gate.screen()` **미경유**(LOOKLIB M0와 동일 매체 갭 — 콘솔 *능력* 프로브이므로 정당) |
| 소켓 | **낡지 않음** — 첫 시도에 ping+state 응답(`Enable` 사이클 불요) |
| 기준선(AC-034 재측정) | pytest **4511 passed · 5 skipped · 0 failed**(93s) · vitest **350 passed** |

**⚠ 응답기 버전 발산 (프로브 충실도)** — 콘솔 설치본 **v1.6.1**(1219줄) vs 본 브랜치 **v1.5.0**(988줄),
diff 299줄. 설치본에만 `props`·`introspect`가 있으며 출처는 **INTROSPECT-001**(미머지).
`prop` 디스패치 블록이 **바이트 동일**함을 확인한 뒤 **1.5.0 부분집합(`prop`·`state`·`exec`)으로만**
프로브했다. `introspect`/`props`는 **한 번도 쓰지 않았다** — 그것으로 얻은 GO는 본 브랜치에서
**재현 불가한 거짓 신호**이기 때문이다(`plan.md` §C *"응답기 무변경 목표"*).
SPATIAL §E.2가 **같은 발산을 독립적으로 기록**해 두었다(교차 확인).

**대조군 양 축 확립 (FXLIB 선례 — `ok`를 쓰기 전에 먼저 한다)**
- 음성: `prop … ZzzBogusProperty` → `ok:false "property not readable"` (그룹 13·14 **양쪽에서** 재현)
- 양성: `prop … Name` → `ok:true "All"` / `"GroupgenProbe"`
→ **ASSUMPTION-62 = GO.** `prop` 채널은 변별적이며, 본 세션에서 `ok`는 *속성 판독 가능성*의 증거로
  사용 가능하다(값의 *의미*에 대한 증거는 아니다).

### §E.2.1 게이트 판정 (폐쇄 어휘 · 행두 접두)

```
NEGATIVE: ASSUMPTION-61  멤버십 판독 채널 — 기존 3동사로는 없다 (단 Lua에 채널이 실재)
GO:       ASSUMPTION-62  날조 속성 판독은 실패한다 — prop 채널 변별적
GO:       ASSUMPTION-63  Store Group <n> 이 그룹을 만든다 — 재조회로 확인
GO:       ASSUMPTION-64  Label Group <n> '<name>' 이 적용된다 — 재조회로 확인
NEGATIVE: ASSUMPTION-65  점유 슬롯은 조용히 덮이지 않는다 — 대신 GUI 확인 다이얼로그 (강화, 실패 아님)
GO:       ASSUMPTION-66  Store/Label Group 은 안전 게이트에서 safe 로 분류된다 (= 무승인 통과)
SKIP:     ASSUMPTION-67  CONDITION_NOT_MET — 카테고리 축이 v1 범위 밖(D-Q9) · 리그도 동종
```

| 게이트 | 판정 | 귀결 |
|---|---|---|
| **A. 멤버십 판독 채널** | **NEGATIVE** | 자동 생성 축 중단 → **제안 전용 강등**(정책 결정은 사용자 몫) |
| **B. `Store Group` 생성** | **GO** | **SPEC 존속** — M3 진행 가능 |
| **C. 점유 슬롯 덮어쓰기** | **NEGATIVE-강화** | REQ-022 정적 차단이 **더욱 절대적** |
| **D. 절단 시 슬롯 안전** | 분기 없음 | D-Q6 거부 정책 유지 |

### §E.2.2 게이트 A — 멤버십은 읽을 수 없다 (**증명됨, 추론 아님**)

`state DataPool/Groups/13`(`'All'`, 실사용 그룹) → `childCount: 0` — research §2 **재확인**.

| 후보 속성 | Group 13 | **Group 14 (우리가 만든 것 — 멤버 정답 기지: 픽스처 1·2)** |
|---|---|---|
| `Object` · `Fixtures` · `Content` · `Members` | `ok:false` | `ok:false` |
| `Count` | `ok:true` → `"function: 0x1063df3b0"` | `ok:true` → `"function: 0x1063df3b0"` |
| `Selection` | `ok:true` → `"table: 0x…"` | `ok:true` → `"table: 0x600002c680c0"` |
| `state …/14` | — | `childCount: 0` |

**주소 안정성 대조 실험 (핸들의 정체 판별)**
- `Selection`을 **같은 그룹**에 2회 → `0x600002db2680` → `0x600002c78440` = **주소 불안정**
  → 접근마다 **새 테이블을 조립**한다(실재 데이터 구조). 주소 비교는 판별력 없음.
- `Count`를 **다른 그룹**(13·12)에 → **동일 주소** `0x1063df3b0` = **클래스 메서드**다.
  값을 얻으려면 `obj:Count()` **호출**이 필요한데 `prop`은 절대 호출하지 않는다.

**결론**: 멤버십은 Lua에서 **도달 가능**하나(`obj:Count()` + `Selection` 순회), **직렬화에 신규 동사가
필요**하다. `plan.md` §C의 예비 조항이 정확히 이 경우다 — *"신규 동사가 필요하면 `M.VERSION` 1.7.0"*.

**결정적 근거**: 멤버를 **정확히 아는** Group 14에서도 판독 채널이 없었다. 남의 그룹을 읽어서 낸
추론이 아니라, **정답을 아는 표본에서의 반증**이다.

**⚠ 주장하지 않는 것 (과약속 금지)** — `Selection`이 *그룹 멤버*를 담는다는 것은 **미증명**이다.
룰북 `31_choreography_patterns.md:85-90`의 `Set Selection MAtricks …`는 `Selection`을
**현재 프로그래머 선택**을 가리키는 커맨드 키워드로 쓴다 — 이는 오히려 **반대 가설을 지지**한다.
`Count`가 멤버 수를 준다는 것도 미증명이다(호출하지 않았으므로). 정직한 서술은
**"후보 핸들이 존재하나 내용 미검증"** 이다.

### §E.2.3 게이트 B — `Store Group` 은 만든다 (GO)

```
exec ClearAll                → ok:true "OK"
exec Fixture 1 Thru 2        → ok:true "OK"        (fid 1~19 — SPATIAL §E.2 실측 계승)
exec Store Group 14          → ok:true "OK"
state DataPool/Groups        → childCount 5 → 6 · 슬롯 14 출현 · name "Group 14"
exec Label Group 14 'GroupgenProbe'  → ok:true "OK"
prop DataPool/Groups/14 Name → ok:true value "GroupgenProbe"      ← 재조회가 증거
```

`ok:true`를 증거로 쓰지 않았다 — **풀 재조회(childCount 5→6)와 이름 재조회**가 증거다.
기본 작명은 `"Group 14"`(슬롯 번호 기반)이며 `Label`이 이를 덮는다 — REQ-013의 *"자동 작명과
사용자 의도는 구별 가능하다"* 가 그룹 축에서도 성립한다.

**표적 슬롯 실측**: 착수 시 점유 `1·11·12·13·15`, `truncated:false` → 빈 슬롯 `2~10·14·16+`.
`state DataPool/Groups/14` → `ok:false "path segment not found: '14'"` 로 **쓰기 직전 재실측**.
14를 고른 이유는 13·15 사이 **고립 간극**이라 2~10 연속 구간을 보존하기 때문이다.

### §E.2.4 게이트 C — 조용히 덮지 않는다. **더 나쁜 방식으로 덮는다** (NEGATIVE-강화)

```
exec ClearAll                → ok:true
exec Fixture 5 Thru 7        → ok:true          (앞의 1·2와 다른 픽스처)
exec Store Group 14          → ok:false  "User Canceled Command"     ← 점유 슬롯
prop DataPool/Groups/14 Name → ok:true "GroupgenProbe"   (덮이지 않음 — 재조회 확인)
state DataPool/Groups        → childCount 6 유지
```

콘솔은 **거부하지 않았다**. **GUI 확인 다이얼로그를 띄웠고**, 조작자가 없어 취소로 귀결됐다.
세 가지가 드러난다:

1. **결과가 사람 판단에 위임된다** — 조작자가 OK를 누르면 **덮인다**. 백업·복구 불가 자산인데.
2. **앱 관점에서 비결정적** — 무인이면 `ok:false`, 사람이 클릭하면 `ok:true`. 같은 커맨드, 다른 답.
3. **라이브 콘솔에 모달을 띄운다** — 공연 중 무인 발화가 콘솔 UI를 붙잡을 수 있다.
   **어디에도 기록되지 않은 운영 위험이며 본 세션이 처음 관측했다.**

→ REQ-022(점유 슬롯 **정적** 차단)는 선호가 아니라 **강제**임이 실측으로 확정됐다.
  후속 3커맨드가 정상 응답했으므로 모달 잔류는 없다.

### §E.2.5 게이트 분류 (ASSUMPTION-66) — **D-Q4를 경험적으로 정당화한다**

`classify_command(validate(cmd), load_ruleset())` 직접 실행:

| 커맨드 | category | risky |
|---|---|---|
| **`Store Group 14`** | **`safe`** | **False** |
| **`Label Group 14 'GEO Downstage'`** | **`safe`** | **False** |
| `Store Group 14 /overwrite` | `blacklisted` | True |
| `Delete Group 14` | `blacklisted` | True |
| `ClearAll` · `Fixture 1 Thru 2` | `safe` | False |

`blacklist.yaml`은 `"Delete"`와 `"Store /overwrite"`만 담는다 — **무플래그 `Store`는 없다**.
즉 **현행 게이트는 그룹 생성을 승인 카드 없이 콘솔로 내보낸다.** 함정 8(요청하지 않은 좌표 기록
54건 무승인 통과)이 **복구 불가 자산**에서 그대로 재현될 구조다.

→ **REQ-031(D-Q4 `server/safety` 확장)이 없었다면 GROUPGEN은 이 결함을 안고 출하됐다.**
  사용자 승인 결정이 실측으로 뒷받침됐다.

### §E.2.6 P8 정리 — **완료. 쇼파일 원상복구 확인**

| 항목 | 상태 |
|---|---|
| 프로브 자산 `Group 14 'GroupgenProbe'` | **삭제됨** (사용자 GUI, 2026-08-04) |
| 정리 후 풀 재조회 | `{1: Copilot Grp, 11: Back, 12: Front, 13: All, 15: Inner Outer Opp}` · `childCount: 5` |
| 슬롯 14 재조회 | `ok:false "path segment not found: '14'"` — **비어있음 확정** |
| 기존 그룹 `1·11·12·13·15` | **무접촉** — 이름·슬롯 전부 착수 시점과 **문자 그대로 동일** |
| 프로그래머 | `ClearAll` 로 비움 |
| 픽스처 좌표 | **무변경** (좌표 커맨드 0건) |
| 룰북·소스 | **무변경** |

→ **M0의 쇼파일 순변화 = 0.** 프로브 전후 상태가 재조회로 동일함이 확인됐다.
`ok:true`가 아니라 **풀 재조회 + 슬롯 부재 재조회**가 증거다.

**정리 경로 (기록 — 후속 M0류가 재사용할 선례)**: `Delete`는 블랙리스트다(§E.2.5 표).
`plan.md` M0 P8의 사전 합의대로 **사용자 GUI 삭제 1건**으로 끝냈다
(함정 21 — SCENE M0의 "시퀀스 7개 GUI 삭제" 부채를 1건으로 묶은 설계가 의도대로 작동했다).
**에이전트는 블랙리스트 파괴 동사를 게이트 우회 하네스로 발화하지 않았다** —
`fx_probe.py`가 bridge 직결이라 기술적으로는 가능했으나 규율을 지켰다.

### §E.2.7 M0 종합 — SPEC은 존속하되 축 하나가 잘렸다

게이트 B가 GO이므로 **SPEC 전체 중단은 없다**. 그러나 게이트 A가 NEGATIVE이므로
`plan.md` §A.4에 따라 **자동 생성 축은 제안 전용으로 강등**되며, 이 정책 결정은
*"대체 정책을 에이전트가 고르지 않는다 — 블로커 보고"* 규율에 따라 **사용자에게 올린다**.

**M0가 바꾼 것 (plan/spec 개정 대상)**
1. **REQ-023**(생성 후 멤버십 재조회 검증) — 기존 3동사로는 **이행 불가**. 게이트 A NEGATIVE 분기
   (검증 불가 명시 + 제안 전용 강등)가 **실제 경로**가 된다.
2. **REQ-022** — 정적 차단의 근거가 "조용한 덮어쓰기"에서 **"조작자 의존 + 모달 위험"**으로 바뀐다.
   더 강한 근거다. `design.md` §6의 차단 서술에 이 실측을 반영해야 한다.
3. **REQ-031** — `Store`/`Label`이 `safe`라는 실측이 확보됐다. `AC-GROUPGEN-036`의 뮤테이션
   (*"게이트에서 그룹 쓰기 참조 타입 인식을 제거하면 빨개진다"*)이 **현행 동작을 정확히 기술**한다.
4. **신규 관측 — 모달 위험**: 점유 슬롯 `Store`가 라이브 콘솔 UI를 블로킹할 수 있다.
   `spec.md` §C.1 검증 천장 또는 §C.3 상속 제약에 신규 항목으로 추가할 것.

**미프로브** — 없음. **P1~P8 전부 완료** (P8 = 사용자 GUI 삭제, §E.2.6). M0 종결.

### §E.2.8 게이트 A 사후 심층 — **응답기 한계가 아니라 MA3 플랫폼 한계다** (2026-08-04)

§E.2.2의 결론(*"신규 동사(1.7.0)가 필요하다"*)은 **한 사다리만** 타서 나온 것이었다
(Group 오브젝트의 Lua 인덱싱 속성). 정책 결정 (a)/(b) 자문 요청을 받고 **나머지 사다리를
전부** 타 봤다. 결과가 결론을 바꿨다.

#### 추가로 닫은 채널 (전부 읽기 전용 · 쇼파일 변경 0 · 프로그래머는 `ClearAll` 원복)

| 사다리 | 프로브 | 결과 |
|---|---|---|
| **간접 — 픽스처 측 선택 상태** | `prop Patch/Stages/1/Fixtures/1` × `Selected`/`IsSelected`/`Sel`/`Selection` | **4/4 `ok:false`** — 날조 대조군 `ZzzBogusProp`와 동일. `ClearAll` → `Group <n>` → 픽스처에서 선택 판독하는 우회로는 **없다** |
| **심층 자식** | `state DataPool/Groups/13/1` | `ok:false "path segment not found: '1'"` |
| **개수·멤버 의미 속성 5종** | `SelectionCount` · `FixtureCount` · `NoFixtures` · `Subfixtures` · `Class` | **5/5 `ok:false`** |
| **1.6.1 `introspect`** (설치본 능력 측정 — 본 브랜치 판정 아님) | `introspect DataPool/Groups/13` | `ok:true` · `class: Group` · **`total: 101` · `truncated: true` · 반환 28** · `source: property_accessors` |
| **1.6.1 `props`** (접근자 경로 판독) | `props COUNT,NAME,NO` × 그룹 `13`·`12`·`11`·`1` | **`COUNT` 4/4 = `"0"`** · `NAME`은 전부 정확 |
| 같은 배치 날조 대조군 | `props ZzzBogus,COUNT DataPool/Groups/13` | `ZzzBogus` `ok:false` / `COUNT` `ok:true` `"0"` |

#### 왜 이것이 결론을 바꾸는가

`introspect`가 `COUNT`를 **`UInt32` 읽기 가능 속성**으로 열거했고, `prop`이 `"function: 0x…"`를
준 것은 **응답기가 Lua 인덱싱으로 읽어 동명 메서드에 먼저 걸린** 구현 문제였다 —
여기까지는 *"접근자 경로로 읽는 신규 동사면 풀린다"*는 §E.2.2 가설을 지지했다.

**그런데 접근자 경로로 실제 읽으니 `COUNT`가 실사용 그룹 4개 전부 `0`이다.**
`Group 13 'All'`은 `exec`이 `executed_ok`인 그룹이고 `Group 11 'Back'`은 룰북의 검증된
페이저 예시가 쓰는 그룹이다. 같은 배치의 날조 대조군이 `ok:false`인데 `COUNT`는 `ok:true`이므로
**`0`은 오류가 아니라 실제 판독값**이다. 오브젝트 트리의 `childCount: 0`과 정확히 일치한다.

→ **그룹 멤버십을 오브젝트·속성 표면에 노출하지 않는 것은 MA3의 성질이다.**
응답기를 고쳐서 닿을 수 있는 곳에 데이터가 없다. 저장소 교훈
`grandma3-group-membership-not-readable`가 이름 그대로 옳았다.

#### 정직한 천장 (주장하지 않는 것)

- Group 속성 **101개 중 73개는 보지 못했다**(`introspect` payload 절단, `max_payload = 1900`).
  그 안에 멤버 열거 필드가 있을 가능성을 **배제하지 못한다**. `introspect`에는 offset 인자가 없다.
- `Selection`(불투명 테이블)의 **내용**은 여전히 미확인이다. 다만 MA3 자신의 `COUNT`가 0을
  말하는 상황에서 이 테이블에 SPEC을 거는 것은 근거 없는 낙관이다.
- 위 두 항목을 뚫으려면 **`props`를 후보 이름으로 무한 추측**하거나 응답기에 페이지네이션을
  넣어야 한다. 둘 다 **본 SPEC의 범위 밖**이며, 성공 근거가 아니라 희망에 기반한다.

#### 정책 결정에 대한 함의

- **(b) 응답기 1.7.0 확장은 증거상 사망했다.** 가장 유망한 두 접근자 경로(`COUNT` 속성 ·
  오브젝트 트리)가 실사용 그룹에서 **0**을 답한다. 신규 동사가 무엇을 직렬화할 것인지
  가리킬 수 있는 대상이 없다. INTROSPECT-001이 목적 구축한 발견 기계(101필드 열거)조차
  멤버십 필드를 보이지 못했다.
- **멤버십 검증은 이 플랫폼에서 원리적으로 불가**하다고 기록한다. REQ-023의 GO 분기는
  **도달 불가 분기**이며, `acceptance.md` AC-023의 GO 열은 `SKIP: CONDITION_NOT_MET`이
  정직한 표기다(NEGATIVE 분기만 실재).
- 단 **검증 가능한 것이 남아 있다**(M0 실측): 슬롯 존재(`state` 재조회) · **이름**
  (`prop NAME` 재조회 — `"GroupgenProbe"`로 실증) · 절단 거부 · 점유 슬롯 차단.
  *"아무것도 검증 못 한다"*가 아니라 **"멤버십만 검증 못 한다"**가 정확하다.

### §E.2.9 M6 라이브 E2E — 같은 지시, 세 배치 (2026-08-04)

승인: 사용자 "진행해줘". 하네스 `.moai/reports/m0-probe/groupgen_m6_e2e.py` (gitignored DEV TOOL) —
**실물 게이트 스택**(`build_console_stack` → `build_toolset(bundle_gate=, group_approval_port=)`)을
세워 **`registry.dispatch`**, 즉 *모델이 닿는 그 지점*으로 진입했다(FXLIB M7 `fx_e2e.py` 선례).
bridge 직결 프로브는 콘솔 *능력*만 증명하고, 툴 사슬은 이렇게만 증명된다.

#### §E.2.9.0 세션 조건 — 리그가 커졌다 (사용자가 장비 추가)

| 항목 | 값 |
|---|---|
| 픽스처 | **39대**, 슬롯 `1..39` 연속(40 → not found) |
| 슬롯 `1..20` → **fid `20..39`** | `Robin LEDBeam 350` (`RLB350M1 n`) — 신규 |
| 슬롯 `21..39` → **fid `1..19`** | `Robin MMX Spot` (`Copilot MMX n`·`MMX n`) — 기존 |
| `Patch/FixtureTypes` | **3슬롯**: `1 Robin MMX Spot` · `2 FixtureType 2` · `3 Robin LEDBeam 350` |
| 목록 응답 | 반환 **18/39** · `truncated: True` (퍼센트 인코딩 후 `max_payload 1900` 초과) |

**⚠ 슬롯 ≠ fid.** 첫 시도가 fid `1..18`(= 슬롯 21~38, 목록에 안 보이는 MMX)을 노렸고,
`arrange_fixtures`가 *"the original coordinates of 18 of 18 targets could not be read, so
NOTHING was written — a coordinate write with no backup has no way back (REQ-SPATIAL-020)"*로
**fail-closed 거부**했다. 백업 없는 좌표 쓰기를 막은 것이며 **이 거부 자체가 M6 증거**다.
보이는 18대의 fid는 **`20..37`**.

**⚠ 워크트리 import 함정 (기록)**: 스크립트를 하위 디렉터리에서 실행하면 `sys.path[0]`가
스크립트 디렉터리라서 `server` 패키지가 **editable 설치를 통해 주 체크아웃**(다른 브랜치)에서
로드된다. `PYTHONPATH=$PWD` 없이는 이 워크트리가 아닌 코드를 재게 된다.
**M0 프로브 증거는 유효함을 확인**했다 — `server/bridge/{osc,protocol}.py`가 두 트리에서
바이트 동일(sha256 대조)이고 주 트리에 미커밋 변경 0이었다.

#### §E.2.9.1 판정 — 같은 지시가 세 배치에서 서로 다른 위상·어휘를 냈다

```
GO: 3x6 그리드   -> grid          depth[6,6,6] + lateral[3x6]
                   GEO Downstage/Center/Upstage + GEO Stage Right 3..1 / Stage Left 1..3
GO: 2겹 동심원   -> concentric    buckets [6, 12]   -> GEO Inner / GEO Outer
GO: 좌우 분할    -> lateral_split buckets [9, 9]    -> GEO Stage Right / GEO Stage Left
GO: 전대 원점    -> None + 저신뢰 (REQ-004 — 위상을 발명하지 않는다)
```

- **`grid` 불변식 라이브 준수**: `fids_by_bucket == []` + `grid_axes` not-None (design.md §2.2).
- **`Boom` 소인이 라이브 확인**: 좌우 6분할이 `GEO Stage Right 3`…`GEO Stage Left 3`.
  리깅 하드웨어 어휘 0건(spec.md §D).
- **coverage 표기 라이브 동작**: `{judged: 18, of: 39, complete: false}` + `topology_partial: true`.
  `truncated: true` 만으로는 "39대 중 18대"를 말하지 못한다 — W6 신규 필드가 제 몫을 했다.

#### §E.2.9.2 M6가 잡은 경합 결함 2건 — **단위 테스트로는 나올 수 없었다**

**결함 1 — 미러 아티팩트.** 좌우 대칭 평면 배치(x=±3…±11, y=z=0)에서 원점 반지름이 `|x|`로
붕괴해 **모든 반지름이 정확히 한 쌍**을 갖는다. `concentric`이 완벽 분리로 **score 20.0** 을 얻어
`lateral_split`(0.75)을 압도하고 **"9개의 2대짜리 링"** 을 답했다.
→ **이것은 이 SPEC이 고치려던 결함의 거울상**이다(research §3: 2겹 동심원을 9행으로 오독).
디자이너가 "좌/우"라 부르는 리그를 "9개 링"이라 답하는 것은 같은 등급의 오답이다.
수정: 모든 반지름 버킷이 정확히 2이고 `bilateral_pairs`가 고신뢰면 그것은 **대칭의 대수적
서명**이므로 반지름 판독을 경합에서 강등한다(`concentric_reading_is_a_mirror_artefact`).

**결함 2 — `bilateral_pairs`가 경합에서 이겼다.** 결함 1을 고치자 대칭 신호가 승자가 됐다.
그런데 **D-Q10은 대칭이 그룹이 되지 않는다**고 못박았고 `naming.py`에 어휘가 **없다** —
선택되면 산출 그룹이 0이 되어 조작자에게 *"아무것도 못 찾았다"*로 읽힌다(실제로는 이름 붙이면
안 되는 대칭 리그를 찾은 것이다). 수정: `scored`에서 제외. `candidates`에는 **그대로 보고**된다.

두 수정 모두 **뮤테이션 RED 증명**: 강등 제거 → 1 failed · `bilateral` 재투입 → 2 failed.
**비공허성 가드**: 진짜 2겹 동심원(6·12)은 여전히 `concentric` (강등은 "모든 버킷이 정확히 2"
+ bilateral 고신뢰 조건에서만 발화 — 좁게 설계).

**테스트 설계 실패도 기록한다**: 기대치를 먼저 적어 둔 덕에 불일치가 발견으로 남았다.
첫 좌우 배치는 3×3 격자 2개였고 y축도 3행으로 유의해 `grid`가 이겼다 — **분류기가 아니라
배치 설계의 결함**이었으므로 **기대치를 완화하지 않고 배치를 고쳤다**. 두 번째 배치(순수 x축
2클러스터)가 결함 1을 드러냈다.

#### §E.2.9.3 정책 (c) 라이브 검증 — 그룹 쓰기 1회

동심원 배치에서 `create_arrangement_groups` 1회 실행:

```
status: created   executed: true   승인 요청 번들 = 1   (툴 계층 승인 게이트 정확히 1회 경유)
verified_steps:
  slot 2  GEO Inner  fids [20..25]   slot_exists: true   name_verified: true
  slot 3  GEO Outer  fids [26..37]   slot_exists: true   name_verified: true
unverified: ["membership"]            fixture_list_truncated: true
human_check_commands: ["Group 2", "Group 3"]
```

**독립 교차 확인**(bridge 직결 프로브, 툴을 믿지 않고): 풀 `childCount 5 → 7`,
`{1 Copilot Grp, 2 GEO Inner, 3 GEO Outer, 11 Back, 12 Front, 13 All, 15 Inner Outer Opp}`.
기존 슬롯 `1·11·12·13·15` **무접촉**. `ok:true`가 아니라 **재조회**가 증거다.

정책 (c) 4층이 전부 실물에서 동작했다 — 승인 강제 · 검증 가능분(슬롯·이름) 재조회 검증 ·
멤버십 미검증 구조적 고지 · 사람 확인 커맨드 동봉.

#### §E.2.9.4 ⚠ 라이브로 재확인된 범위 밖 결함

**좌표 쓰기가 무승인으로 나갔다.** `arrange_fixtures`가 `status: arranged`로 좌표를 기록하는데
`승인 요청 번들 = 0`이었다 — AC-SPATIAL-031 `[DEFERRED]`(함정 8)의 라이브 재현이다.
본 SPEC의 그룹 쓰기는 승인을 강제하지만(REQ-031) **좌표 축은 여전히 무승인**이다.
GROUPGEN 범위 밖이며 SPATIAL 후속 SPEC 소관이다 — 침묵하지 않고 기록한다.

#### §E.2.9.5 사람 무대 관측 — **GO** (2026-08-04, 사용자 직접 확인)

```
GO: 사람 관측  Group 2 -> 내륜 6대만 · Group 3 -> 외륜 12대만. 의도대로 갈렸다.
```

사용자가 콘솔에서 `ClearAll` → `Group 2` → `ClearAll` → `Group 3` → `ClearAll`을 실행하고
무대를 직접 관측해 **내륜/외륜이 의도대로 갈렸음**을 확인했다.

**이것이 왜 결정적인가**: 멤버십은 MA3가 노출하지 않으므로(§E.2.8) 기계로는
*"슬롯이 생겼다 + 이름이 맞다"*까지만 확인된다. **그룹이 실제로 의도한 픽스처를 잡는지는
사람 관측만이 답할 수 있고**(spec.md §C.1), 그 관측이 이제 확보됐다.
즉 정책 (c)의 잔여 위험(*"이름은 맞는데 멤버가 다를 수 있다"*)이 **이 배치에 대해 해소**됐다.

**증거 등급**: **(세션)** — 라이브 관측이며 저장소 아티팩트로 재확인할 수단이 없다.
상향하지 않는다. 재현하려면 같은 배치를 다시 만들고 다시 봐야 한다.

#### §E.2.9.5a 여전히 미검증으로 남는 것 (정직한 천장)

- **`SKIP: CONDITION_NOT_MET` — 타입 축 라이브**: 리그가 이제 이종(2 실타입:
  `Robin MMX Spot` · `Robin LEDBeam 350`)이지만 M6는 `fixture_type_records`를 호출자가
  넘기는 경로를 쓰지 않았다. ASSUMPTION-67은 여전히 SKIP이며, **이종 리그가 확보된 만큼
  후속 세션에서 닫을 수 있다** — 이제 막는 것은 리그가 아니라 실행뿐이다.
- **`SKIP` — 실제 Gemini 턴**: M6는 `registry.dispatch` 직결이다. 모델이 *"배치에 맞게 그룹
  잡아줘"* 를 듣고 이 툴을 **선택**하는지는 LOOKLIB M7처럼 별도 라이브 채팅 턴이 필요하다.
  툴이 동작함은 증명됐고, 모델이 그것에 닿는지는 미증명이다 — 다른 사건이다.

#### §E.2.9.6 정리 — **완료. 그룹 축 순변화 0**

| 항목 | 상태 |
|---|---|
| 프로브 그룹 `Group 2`·`Group 3` | **삭제됨** (사용자 GUI, 2026-08-04) |
| 정리 후 풀 재조회 | `{1 Copilot Grp, 11 Back, 12 Front, 13 All, 15 Inner Outer Opp}` · `childCount 5` |
| 슬롯 2·3 재조회 | `ok:false "path segment not found"` — **비어있음 확정** |
| 기존 그룹 `1·11·12·13·15` | **무접촉** — 이름·슬롯 전부 착수 시점과 **문자 그대로 동일** |
| 슬롯 `21..39`(fid 1~19) | 무접촉 — 목록에 안 보여 배치 대상이 아니었다 |
| **픽스처 좌표** | ⚠ 슬롯 `1..18`(fid 20~37)이 **2겹 동심원 배치 상태로 남아 있다**. 착수 시 원점이었다 |

**→ 그룹 축의 쇼파일 순변화 = 0** (M0와 동일하게 재조회로 확인).
`ok:true`가 아니라 **풀 재조회 + 슬롯 부재 재조회**가 증거다.

**좌표는 의도적으로 남겼다**: M6가 만든 동심원 배치가 그대로 있어 후속 세션이 타입 축
라이브(§E.2.9.5a)나 Gemini 턴을 **재배치 없이 바로** 실행할 수 있다. 원점 복귀가 필요하면
`arrange_fixtures`로 되돌릴 수 있으나(SPATIAL 백업·복원 번들) 그 자체가 또 하나의 무승인
좌표 쓰기다(§E.2.9.4) — 사용자 판단 사항으로 남긴다.

### §E.2.10 M6 종합 — SPEC의 주장이 실물에서 성립한다

> **판별이 본체다.** 같은 지시가 세 배치에서 서로 다른 위상을 내고, 그 위상에 맞는 폐쇄 어휘로
> 이름이 붙고, 사람이 무대에서 그 그룹이 의도한 픽스처를 잡는 것을 확인했다.

M0~M6 전 구간에서 라이브가 잡은 것 중 **단위 테스트로는 원리적으로 나올 수 없었던 것**:

1. **게이트 A NEGATIVE가 플랫폼 한계임**(§E.2.8) — 응답기를 고쳐도 닿을 데이터가 없다.
2. **점유 슬롯 `Store`가 GUI 모달을 띄운다**(§E.2.4) — 무인이면 취소, 사람이 누르면 덮인다.
   라이브 콘솔 UI 블로킹 위험은 어디에도 기록돼 있지 않았다.
3. **`Store Group`이 `safe`로 분류된다**(§E.2.5) — D-Q4를 경험적으로 정당화했다.
4. **절단 가드가 틀린 곳에 있었다**(REQ-024 정정) — ~18대 초과 리그 전부에서 실사용 불가였다.
5. **미러 아티팩트**(§E.2.9.2) — 이 SPEC이 고치려던 결함의 거울상.
6. **`bilateral_pairs`가 경합에서 이겼다**(§E.2.9.2) — D-Q10 위반이 산출 0으로 나타났다.
7. **슬롯 ≠ fid**(§E.2.9.0) — `arrange_fixtures`의 fail-closed 거부가 이를 드러냈다.

## §E.3 Run-phase Audit-Ready Signal

- run_complete_at: 2026-08-04
- run_status: **audit-ready**
- 완료 신호: M0~M6 전 마일스톤 완료(§E.2.0~§E.2.10) · Implementation Kickoff Approval 반자율 획득 · 사람 무대 관측 GO(§E.2.9.5)

### AC 충족 요약 (§E.2 인용 — 수치 재산출 없음)

| 게이트/AC | 판정 | 근거 (§E.2 참조) |
|---|---|---|
| 게이트 A (멤버십 판독) | **NEGATIVE**(플랫폼 한계) | §E.2.8 — `props COUNT` 실사용 그룹 4/4 = 0, 날조 대조군과 변별 |
| 게이트 B (`Store Group` 생성) | **GO** | §E.2.3 — 재조회 childCount 5→6 |
| 게이트 C (점유 슬롯 덮어쓰기) | **NEGATIVE-강화** | §E.2.4 — GUI 모달, 조작자 의존 |
| AC-GROUPGEN-036 (REQ-031 대응) | PASS | §E.2.5 — `Store`/`Label` `safe` 분류 실측 |
| REQ-024 (절단 가드 위치) | 정정 완료 | §E.2.9.0 — 판별 경로 이동, `coverage`/`topology_partial` 신설 |
| M6 3개 배치 판정 | GO×3 + SKIP-정당 | §E.2.9.1 — grid/concentric/lateral_split/None |
| 정책 (c) 그룹 쓰기 라이브 | GO | §E.2.9.3 — 독립 교차 확인(childCount 5→7) |
| 사람 무대 관측 | **GO** | §E.2.9.5 — 내륜 6대/외륜 12대 |

### 기준선/최종 수치

- 기준선(run 킥오프, §E.2.0): pytest **4511 passed · 5 skipped**(93s) · vitest **350 passed**
- 최종(sync 시점 재측정 없음 — coordinator 3-phase close가 일괄 재측정): pytest **4676 passed · 7 skipped · 0 failed** · vitest **350 passed**(UI byte 무변경) · ruff 기존 부채 3건(신규 0) · `server/safety` byte-diff **0** · 룰북 byte-diff **0**
- 뮤테이션: **6/6 RED**(§E.2.9.2 미러 아티팩트 강등 제거 1건 · bilateral 재투입 1건 + plan-audit MAJOR-3 해소 AC-GROUPGEN-037 4항목 포함 5:5 정합)

### 경계 확인

- `TOOL_NAMES` 20 → 22 (`classify_arrangement_topology` · `create_arrangement_groups`)
- 그룹 축 쇼파일 순변화 **0**(§E.2.6 M0 정리 · §E.2.9.6 M6 정리, 전부 재조회로 확인)
- 좌표는 M6 동심원 배치 상태로 **의도적으로 남김**(§E.2.9.6) — 후속 타입 축 라이브가 재배치 없이 이어받을 수 있게

## §E.4 Sync-phase Audit-Ready Signal

- sync_complete_at: 2026-08-04
- sync_status: **audit-ready**
- CHANGELOG 반영 확인: `CHANGELOG.md` `[Unreleased]` §Added에 `SPEC-COPILOT-GROUPGEN-001` 항목 추가(핵심 요약 + M0/M6 근본원인 7건 + 정정 2건 + 알려진 천장). `grep -c 'GROUPGEN' CHANGELOG.md` > 0 확인.
- frontmatter 전이: `spec.md` `status: draft → completed` · `updated: 2026-08-04`. **본문 diff 0**(frontmatter 헝크만).

### ⚠ lifecycle drift 기록 (은폐하지 않는다)

`.claude/rules/moai/development/spec-frontmatter-schema.md`의 Status Transition Ownership Matrix에 따르면
`draft → in-progress` 전이는 **manager-develop이 첫 run-phase 커밋(M1)에서 수행**해야 한다.
**본 SPEC은 그 전이를 건너뛰었다** — `git log`상 M0~M6 전 run-phase 커밋(`bca04d0` 이하 ~ `601eedd`)이
`spec.md` frontmatter의 `status:` 필드를 한 번도 갱신하지 않았고, `status: draft`인 채로 run-phase
전체를 마쳤다. 본 sync 커밋이 `draft → completed`로 **직접 점프**한다 — 정상 경로라면
`draft → in-progress`(run 킥오프) → `in-progress → implemented → completed`(sync)의 2단계였을 것이다.
**드리프트를 조용히 넘기지 않고 여기에 기록한다.** 원인은 run-phase 델리게이션 프롬프트가 frontmatter
전이 의무를 명시적으로 지시하지 않은 것으로 추정되나, 본 sync 워커의 소유 범위(frontmatter status/updated만)
밖이라 근본 원인 조사는 하지 않았다.

### 남은 SKIP 2건

1. **타입 축 라이브**(`ASSUMPTION-67`, `SKIP: CONDITION_NOT_MET`) — M6 시점 리그가 이종(Robin MMX Spot ·
   Robin LEDBeam 350)이 됐으나 M6가 `fixture_type_records` 호출자 전달 경로를 쓰지 않았다. 막는 것은
   이제 리그가 아니라 실행뿐이다(§E.2.9.5a).
2. **실제 Gemini 턴** — M6는 `registry.dispatch` 직결이다. 모델이 자연어 지시를 듣고 이 툴을 **선택**하는지는
   LOOKLIB M7처럼 별도 라이브 채팅 턴이 필요하다. 툴 동작은 증명됐고 모델 도달은 미증명(§E.2.9.5a).

### 별도 SPEC 후보 3건

1. **채팅 경로 무승인 그룹 생성** — 본 SPEC 툴을 경유하지 않는 직접 `Store Group` 발화는 여전히
   무승인(spec.md §C.1.1). 본 SPEC 범위 밖.
2. **무승인 좌표 쓰기** — `arrange_fixtures`가 `status: arranged`로 좌표를 기록하는데 승인 요청 번들이
   0이다(§E.2.9.4). AC-SPATIAL-031 `[DEFERRED]`의 라이브 재현. SPATIAL 후속 SPEC 소관.
3. **`corpus.yaml` 큰따옴표 미노출 결함** — `group_create`가 `Label Group 3 "Vocal"`을 쓰는데
   `protocol.py:109`가 이 형태를 거부한다(mock 전용 코퍼스라 실행 경로에 미노출된 기존 잠재 결함).

## §E.5 amendment v0.4.0 — 잔여 SKIP 2건 종결 (2026-08-04)

`975d7b0`에서 `status: completed`였던 SPEC을 **in-place amendment**로 열어(`completed -> in-progress`,
`amendment_of` 자기참조, HISTORY `## Amendments`) 남은 두 SKIP을 라이브로 닫았다.

### §E.5.1 SKIP 1 — 타입 축 라이브 검증 → **GO** (ASSUMPTION-67 종결)

라이브 리그가 이질(異質)이라 타입 축이 실제로 분할된다는 것이 처음으로 실측됐다.

| 항목 | 실측 |
|---|---|
| 리그 규모 | 39대 (`fid 1..19` Robin MMX Spot · `fid 20..39` Robin LEDBeam 350) |
| `type_name` 축 | **2개로 분할** → `Robin MMX Spot`(19대) · `Robin LEDBeam 350`(20대) |
| `manufacturer` 축 | 분할 **없음** — 전부 `Robe` |
| 2-hop 경로 | `Fixtures/<n> fixturetype` → `FixtureType <k>` → `Patch/FixtureTypes/<k>` (`ShortName` = `RLB350M1 n`) |

이 실측이 **결함 2건**을 드러냈고, 둘 다 amendment로 소인했다(`server/spatial/fixture_type.py`):

1. **축별 침묵 영성(silent per-axis zero)** — `_groups_for_axis`가 분할 없는 축에서 빈 튜플을 조용히
   반환했다. `manufacturer`가 균일해서 사라진 것인지 읽기가 실패한 것인지 호출자가 구분할 수 없었다.
   → `FixtureTypeAxisReport` 신설. `FIXTURE_TYPE_AXES`의 **모든** 축이 매 호출마다 명시적으로 보고된다
   (`uniform_across_rig` / `all_values_unreadable`). 침묵하는 축은 이제 없다.
2. **전체-호출 raise가 부분 결손을 삼킴** — 장비 1대의 구조 필드가 빈 문자열이면 `FixtureTypeAnalysisError`가
   호출 전체를 죽였다. 읽을 수 있는 38대의 타입 축이 1대 때문에 통째로 사라졌다.
   → **항목별 강등**으로 변경. `FixtureTypeUnreadable` 목록으로 빠지고 나머지 축 참여는 유지된다
   (`fid 11`의 `manufacturer`가 비어도 `type_name` 축에는 정상 참여함을 검증). 키 누락·타입 오류는 여전히 raise.

### §E.5.2 SKIP 2 — 실제 Gemini 턴 → **GO** (모델이 툴을 고른다)

앱 기동(`--receive-port 9005`) 후 `/ws`로 한국어 지시 **1건**을 넣었다: *"지금 배치에 맞게 그룹 잡아줘"*.
승인 카드는 **거부**해서 쓰기 경로를 막고, 모델이 무엇을 고르는지만 관측했다.

| 관측 | 증거 (감사 로그 + 응답 본문) |
|---|---|
| 모델이 위상 분류 툴을 **선택** | `05:59:53~58` `property_query` **72건** — `Patch/Stages/1/Fixtures/{1..18}` 의 `fid/posx/posy/posz`. `classify_arrangement_topology`의 `read_spatial_fixtures` 서명 그대로 |
| 슬롯 실측도 실행 | `06:00:02` · `06:00:37` `state_query DataPool/Groups` (`state_query` = 읽기) |
| **폐쇄 어휘를 그대로 사용** | 응답이 `GEO Inner` / `GEO Outer`를 씀. 창작 이름 **0건** |
| **coverage 공시가 사용자에게 도달** | *"전체 패치에는 39대의 장비가 존재하지만, 나머지 21대(Robin MMX Spot 등)는 … 이번 공간 배치 분석에서 제외되었습니다"* — `coverage{judged:18, of:39}` + `topology_partial`이 자연어로 전달됐다 |
| 위상 판정 일치 | 모델이 *"동심원(Concentric Rings) 형태 … 18대(FIDs 20~37)"* 로 보고. 반지름 약 2m / 약 6m 까지 정확 |
| **쓰기 0건** | 턴 창 내 `Store|Label Group` **0건** · `commands: []` · 모델이 승인 요청에서 멈췄다. 턴 후 풀 = `{1,11,12,13,15}` (기준선 동일, 슬롯 2·3 비어 있음) |

기존 감사 로그의 `Store/Label Group` 4건은 `04:26:21` — §E.2.8 하네스 실행분이며 이 턴과 무관하다.
`ws_handshake_rejected` 1건은 첫 시도에서 `Origin` 헤더를 빼서 게이트가 정상 거부한 것(감사됨).

#### §E.5.2a ⚠ 이 턴에서 새로 드러난 조종 위험 (범위 밖 · 기록만)

모델은 승인을 청하면서 **원시 명령 체인을 산문으로 적었다** —
`ChangeDestination Root / ClearAll / Fixture 20 + Fixture 21 + … / Store Group 2 / Label Group 2 'GEO Inner'`.
사용자가 *"진행해줘"* 라고 답할 때 모델이 `create_arrangement_groups`를 부르지 않고 그 체인을
`run_commands`로 흘려보낼 경로가 열려 있다. 그러면 우리 툴의 **슬롯 재실측 · 멤버십 재조회 · coverage 공시**가
전부 우회된다. 툴 설명(description)의 조종 문제이며 코드 결함은 아니다 — 다음 SPEC 후보.

### §E.5.3 검증

- `pytest` **4682 passed · 7 skipped · 0 failed** (amendment 전 4676 → +6)
- `server/safety/**` · `server/rulebook/**` byte-diff **0** (PRESERVE 유지)
- 콘솔 그룹 축 순변화 **0** — 턴 전후 풀 동일

## §E.6 머지 전 독립 리뷰 4인 병렬 — P0 1건 + P1 3건 (2026-08-04)

PR #24를 열고 **머지 전에** 독립 리뷰어 4인을 병렬로 붙였다(SCENE-001 선례 §E.2.10 계승).
자기검토는 값이 낮으므로 리뷰어에게 *"주장을 반증하려 적극적으로 시도하라"* 를 지시하고
파일 무교차 4축(안전 경계 · 위상 정확성 · 툴 표면 · 증거 정합성)으로 나눴다.

**결과: 머지를 멈춰야 하는 P0 1건을 잡았다.** 그리고 그 P0은 **리뷰어 2인이 서로 다른 축에서
독립적으로 수렴**했다 — 우연한 발견이 아니라는 뜻이다.

### §E.6.1 P0 — 승인 무결성 붕괴 (dedupe가 선택 줄을 탈락시킨다)

`_is_programmer_state`는 `Fixture 7`을 dedupe에서 면제하지만 **가산 체인은 면제하지 않는다**:

```
_is_programmer_state('Fixture 7')                      -> True
_is_programmer_state('Fixture 1 + Fixture 2 + Fixture 3') -> False   <- 여기
```

`create_arrangement_groups`가 승인된 계획 전진을 **하나의** `run_commands` 번들로 넘겼으므로,
번들 내 dedupe가 둘째 그룹의 동일한 선택 줄을 `skipped_already_executed`로 떨어뜨렸다.
코디네이터 재현(수정 전):

```
사람이 승인한 카드         │ 콘솔이 실제로 받은 것
──────────────────────────┼──────────────────────────
ClearAll                  │ ClearAll
Fixture 1 + 2 + 3         │ Fixture 1 + 2 + 3
Store Group 1             │ Store Group 1
Label Group 1 '…'         │ Label Group 1 '…'
ClearAll                  │ ClearAll
ClearAll                  │ ClearAll
Fixture 1 + 2 + 3         │        ← 사라졌다
Store Group 2             │ Store Group 2   ← 빈 프로그래머에서 발화
```

**사람이 승인한 것과 콘솔이 받은 것이 다르다** — 이 SPEC이 세우려던 바로 그 속성이 깨진다.

왜 평범한 경우에 터지는가: 제조사·모델이 1:1인 리그(대부분의 실사용 리그)에서
`type_axis_groups`가 두 축에 대해 **바이트 동일한** fid 튜플을 낸다. 그리고 **v0.4.0 개정이
축을 전부 보고하게 만들어 오히려 발화를 쉽게 했다** — 내 수정이 다른 결함의 도달 범위를 넓혔다.

**왜 이것이 P0인가**: 멤버십은 이 플랫폼에서 판독 불가(§E.2.1 게이트 A NEGATIVE)이므로
**탐지도 복구도 원리적으로 불가**하다. 리뷰어 재현에서 쓰기를 반영하는 콘솔 더블을 쓰면
`status:"created"` · `slot_exists:true` · `name_verified:true` 로 **빈 그룹을 긍정 확인**했다.

#### 결정적 근거 — 저장소가 이미 세 곳에서 같은 형상을 가드한다

- `server/looks/busking.py::_guard_collision` + `VALUE_LINE_COLLISION` — 토상 주석: *"두 번째 값 라인이
  탈락하면 빈 프로그래머 상태로 Store가 실행되고 콘솔은 성공으로 답한다"*
- `server/scene/compile.py::_guard_collision` — `VALUE_LINE_COLLISION` raise
- `server/fx/instantiate.py:113-124` `@MX:ANCHOR` — *"the guard below decides which of ITS OWN lines the
  dedupe will compare … the drop is silent, because `Store` still runs and the console still answers ok."*

`server/groupgen/write.py`는 **같은 형상의 신규 빌더인데 가드가 없었다.** 판단 미스가 아니라
**이미 문서화된 패턴을 놓친 것**이다. 이건 이 세션에서 가장 값비싼 교훈이다.

#### 수정 — 두 겹

1. **주 수정**(`tools.py`): 그룹당 한 번들을 **각기 새 `ExecutionContext`** 로 발화. 승인은 여전히
   전 계획 1통(카드 분할 금지). 그룹 번들은 `ClearAll`로 여닫으므로 이전 툴 호출 상태에 의지하지
   않는다 — 새 컨텍스트가 안전한 이유다. 부분 실패는 신규 `slot_outcomes`/`partial_write`로
   **쓴 슬롯과 못 쓴 슬롯을 구분**하고 `executed`는 실패 시 `False`를 유지한다.
2. **백업 수정**(`write.py`): `GROUP_LINE_COLLISION` + `guard_bundle_collision` — **write.py가 자기가
   생산한 줄을 스스로 분류**한다(`fx/instantiate.py` 선례 그대로). `tools.py` import는 순환이라
   면제 집합을 지역 재선언하고 **동일성을 테스트가 단정**한다(비교 자체의 판별력 3건 + 비공허성 1건 포함).

**[HARD] `_PROGRAMMER_STATE_COMMANDS` 자체는 넓히지 않았다** — 넓히면 looks/scene/fx의 dedupe 면제가
동시에 넓어져 본 PR 밖으로 파급된다. `test_fx_boundary.py` 그린 유지로 확인.

**교차 호출 트리거도 함께 닫혔다**: `ExecutionContext.executed_ok`가 한 지시 내 누적되므로
자기수정 재시도(REQ-MVP-012)만으로도 그룹 1개짜리 호출이 오염됐다.

### §E.6.2 P1 — 미러 아티팩트 강등이 리그 "지문"에 걸려 있었다

§E.2.8이 고쳤다고 적은 결함이 **여분 장비 1대만 추가하면 재발**했다. 강등 조건(*모든 반지름 버킷이
정확히 2* ∧ *`bilateral` 고신뢰*)이 전부 **그 18대 리그의 우연한 성질**이었고 — 여분 1대가 두 조건을
동시에 깬다 — 현상의 성질이 아니었다.

**진짜 현상**: 평면이 평평하면 `math.hypot(x, y)`가 `|x|`로 붕괴해 **반지름 축이 좌우 축을 x=0에
대해 접은 사본**일 뿐 독립 가설이 아니다. 붕괴 조건 1개(`y_span <= SPATIAL_ROW_NOISE_SPAN`)로 교체했다.
평면 미러-바 계열 스윕에서 `concentric` **6/15 → 0/15**.

> 같은 결함을 **두 번** 놓쳤다. 첫 수정이 *증상이 나타난 리그*를 고정했을 뿐 *원인*을 고정하지
> 않았기 때문이다. 골든이 회귀를 막아주지만 **골든과 같은 형상만** 막아준다.

### §E.6.3 P1 — depth 점수 영성 + 축 우선순위 (사용자 도메인 결정)

`_compute_depth`의 `and analysis.gaps.median_gap > 0` 절이 **완벽 정렬 행 리그의 점수를 0.0**으로
만들었다. `rows.py` 자신의 docstring이 *"한 행의 픽스처는 깊이를 공유하므로 행 내 갭이 0으로 붕괴"* 라
적으므로 다행 리그의 `median_gap`은 **항상** 0이다. 실측 역전:

| 리그 | depth score |
|---|---|
| 정렬 3×10 그리드 (완벽한 답) | **0.0** |
| 2겹 동심원 — 이 SPEC의 **창립 오독** | **36.6** |

**도달 범위가 이 PR 자신이다**: `arrange_fixtures`의 grid 프리셋이 `_centred_offsets`로 행당 y를
완전 정렬해 쓰므로 **앱이 직접 쓴 리그를 자기 분류기가 오독한다.** 코디네이터 재현:

```
전기바 3개(깊이+트림 각기 다름): depth_rows[5,5,5] 고신뢰인데 vertical_levels 가 이김  (어휘 손실)
3행 x 2트림                  : depth_rows[5,5,5] 버리고 vertical_levels[10,5]        (파티션 손실)
```

**수정**: 절 삭제(정렬 3×10 `0.0 → 60.0`, 동심원 36.6 불변) + **깊이 우선 정책**(사용자 확정) —
`depth_rows` 고신뢰 ∧ 버킷 ≥2면 `vertical_levels`를 경합에서 제외. `vertical`은 `candidates`에
고신뢰 그대로 남는다(`bilateral_pairs`의 *"보고하되 선택하지 않음"* 형상 승계).

⚠ **남는 질문(후속)**: 영성을 고쳐도 점수만으로는 depth 60 vs vertical 80이다. 이 배제 규칙이 없으면
여전히 vertical이 이긴다 — 근본적으로 **축 간 점수 비교 가능성**이 미해결이다.

### §E.6.4 P1 — AC 인용 20건이 해석되지 않았다

`acceptance.md`의 pytest 인용 **35건 중 20건**이 존재하지 않는 파일·테스트를 가리켰다
(plan-phase에서 지은 이름을 구현 후 반영하지 않음). 실체는 다른 이름으로 커버되지만
**AC 문면대로 돌리면 `no tests ran` / `ERROR: not found`** 가 나온다 — 즉 그 AC들은 재검증 불가였다.
41건으로 정리해 전수 해석을 확인했고, 유일한 미해석분(`AC-014`, `[Optional]`)은 인용 지점에 SKIP을 명기했다.

### §E.6.5 ⚠ 코디네이터의 자기 정정 — 내가 남의 정확한 숫자를 틀렸다고 단정했다

v0.4.0에서 W8이 AC-043의 뮤테이션 카운트를 "3 failed"라 적었고, 나는 이를 **1건 과대**라 정정했다.
**그 정정이 틀렸다**:

```
뮤테이션 후 -k axis_reports (내가 쓴 범위)  : 2 failed
뮤테이션 후 파일 전체 (AC 가 함의한 범위)    : 3 failed
```

W8이 옳았다. 나는 **더 좁은 선택 범위로 재고** 그 차이를 상대의 오류로 귀속시켰다.
`lesson-single-hypothesis-analyzer-lies-confidently`를 **검증하는 쪽이** 저지른 형태다 —
"검증했다"는 사실이 "옳게 검증했다"를 함의하지 않는다. **범위를 명기하지 않은 AC 문면**이
공범이므로 두 숫자를 모두 범위와 함께 기록했다.

### §E.6.6 리뷰가 **찾지 못한** 것 (정직한 천장)

리뷰어 4인이 각각 반증을 시도했고 실패한 항목은 그 자체로 증거다:

- fail-closed 승인(`DenyAllApprovalPort` 기본값)은 **우회 경로가 발견되지 않았다** — 승인 없이는 `commands: []`
- 폐쇄 어휘의 폐쇄성 — 입력이 그룹 이름으로 흘러드는 경로 **0건**
- `server/safety/**` 간접 변경(monkeypatch·기본 인자·전역 상태) **0건**
- 신규 툴 4종의 스키마가 Gemini/Anthropic 양쪽에서 거부되지 않음
- 절단된 목록으로 쓰기가 막히는 것(`FIXTURE_LIST_TRUNCATED`)은 실제로 발화

### §E.6.7 범위 밖 발견 — 타 브랜치 작업이 쓸려 들어왔다

코디네이터가 diff 경계를 감사하다 `SPEC-COPILOT-INTROSPECT-001` **6파일(1,271줄)** 이
`68db44f`의 `git add -A`로 추적에 들어온 것을 발견했다. `spec/introspect-001`은 **main 기준 15커밋
앞선 타 작업자 브랜치**이고 우리 사본은 6파일 **전부** 그쪽과 다르다 — 즉 남의 진행 중 작업의
**낡은 스냅샷**을 main에 밀어넣는 상태였다. 결정적으로 SPATIAL 자신의 `progress.md`가
*"`.moai/specs/SPEC-COPILOT-INTROSPECT-001/`은 이 브랜치에서 **untracked**다"* 라 적고 있었다 —
**문서가 트리와 모순되며 문서 쪽이 의도에 맞았다.** `git rm`으로 제거했다.

### §E.6.8 검증

- `pytest` **4716 passed · 7 skipped · 0 failed** (리뷰 전 4682 → **+34**)
- `vitest` **350 passed / 15 files** (UI byte 무변경)
- `ruff check server/` **3건** — 전부 base 부채(E501) · `ruff format --check` 16파일 이미 정렬
- `server/safety/**` byte-diff **0** · `server/rulebook/**` 기존 파일 수정 **0**(신규 자산 추가만)
- 뮤테이션 RED 실측: 미러 지문 복원 → **8 failed** · depth 영성 복원 → **1 failed** ·
  깊이 우선 제거 → **1 failed** · 둘 다 → **3 failed** · P0 두 계층 각각 RED 확인
