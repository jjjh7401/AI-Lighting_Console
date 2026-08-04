# SPEC-COPILOT-GROUPGEN-001 — 진행 기록 (progress)

status: **run-phase M0 완료** · 게이트 B **GO**(SPEC 존속) · 게이트 A **NEGATIVE**(제안 전용 강등 — 정책 결정 사용자 대기) · 구현 코드 0 · 잔여 프로브 자산 **`Group 14 'GroupgenProbe'` 1건**(사용자 GUI 삭제 대기)

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

### §E.2.6 잔여 상태 — 정리 미완 (P8)

| 항목 | 상태 |
|---|---|
| 생성된 프로브 자산 | **`Group 14 'GroupgenProbe'` 1건** (멤버: 픽스처 1·2) |
| 기존 그룹 `1·11·12·13·15` | **무접촉** — 재조회로 확인(이름·슬롯 전부 착수 시점과 동일) |
| 프로그래머 | `ClearAll` 로 비움 |
| 픽스처 좌표 | **무변경** (좌표 커맨드 0건) |
| 룰북·소스 | **무변경** |

**정리 경로**: `Delete`는 블랙리스트다(위 표). `plan.md` M0 P8의 사전 합의는
**사용자 GUI 삭제 1건**이다(함정 21 — SCENE M0의 "시퀀스 7개 GUI 삭제" 부채를 1건으로 묶은 설계).
**에이전트가 블랙리스트 파괴 동사를 게이트 우회로 발화하지 않는다.**

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

**미프로브 (승인은 받았으나 미실행)** — 없음. P1~P7 전부 실행, P8만 사용자 GUI 대기.
