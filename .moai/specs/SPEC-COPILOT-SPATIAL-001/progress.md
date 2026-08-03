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

### §E.2.0 Run-phase 킥오프 — 전제 검증 (2026-08-03)

| # | 전제 | 결과 | 근거 |
|---|---|---|---|
| 1 | `git branch --show-current` | **PASS** — `feature/SPEC-COPILOT-SPATIAL-001` | [측정] |
| 2 | `git log --oneline -1` | **PASS** — `4d298b8` | [측정] |
| 3 | onPC 기동 + OSC 왕복 ping | **PASS** — `[PASS] ping` / `[PASS] state` | [실측] |

**전제 3 주의**: 문서(`console/lua/README.md` §4)의 예시 `--listen-port 9000`은 **이 설치에서 틀리다**. 앱 설정
(`~/Library/Application Support/GrandMA3 Copilot/settings.toml`)의 `receive_port = 9005` · `osc_slot = 2`가 정본이며,
9000으로 건 첫 ping은 timeout FAIL이었다. 9005 재시도에서 PASS. README §4의 포트는 §2.1 예시(9005)와 불일치한다 — 문서 결함.

**기준선 재측정** (plan.md §B M5 의무 — plan-phase 수치 재사용 금지):

- `uv run pytest server/tests -q` → **4246 passed · 5 skipped · 0 failed** (94.03s) [측정]
- `npx vitest run` (ui) → **350 passed · 15 files · 0 failed** [측정]

### §E.2.1 M0 라이브 프로브 — READ 축 (P1·P2·P3·P7·P9 + 보충)

실행: `scratchpad/spatial_m0/probe_read.py` · `probe_read2.py` — **READ 전용**(`state`/`prop` 동사만).
`exec` 0 · 쇼파일 변형 0 · 오브젝트 생성 0. 표적: `Patch/Stages/1/Fixtures` (19 픽스처, fid 1~19).

**응답기 정합성 선행 확인 (lesson-fabricated-control-probe 적용)**: 라이브 응답기는 **v1.6.1**(SPEC-COPILOT-INTROSPECT-001
계열)이고 본 브랜치 소스는 **v1.5.0**이다. 다른 코드에 대고 잰 실측은 본 브랜치로 이관되지 않으므로, 프로브가 쓰는
`M.build_prop_result` 구현을 두 버전에서 추출해 대조 → **byte-identical (diff 0)**. 따라서 아래 판정은 본 브랜치의
1.5.0 응답기에 그대로 성립한다. 프로브는 `ping`/`state`/`prop`만 사용했고 이 3동사는 전부 1.5.0에 존재한다.

| 전제 | 판정 | 실측 근거 |
|---|---|---|
| **ASSUMPTION-53** (READ 채널) | **GO** | `prop` + `Patch/Stages/1/Fixtures/<slot>` + `posx` → `ok:true, value:"0.0"`. `posx`/`PosX`/`POSX`/`Posx` **4변형 전부 동일 결과 → 프로퍼티 조회는 대소문자 무관**. `posy`/`posz`/`rotx`/`roty`/`rotz`/`fid`/`name` 전부 판독 성공 |
| **REQ-SPATIAL-026 (c)** (날조 대조군) | **변별력 확인** | `poszz`·`posxx`·`NotARealProperty` **3건 전부 `ok:false` + `"property not readable: <name>"`**. SCENE M0의 `/CueOnlyy`(날조가 `ok`로 통과) 선례와 **달리** `prop` 채널은 변별적이다 — `ok`를 증거로 써도 되는 축 |
| **ASSUMPTION-54** (WRITE 채널) | **GO** | 커맨드라인 `Set Fixture <fid> Posz '<v>'` → 재조회 일치. 사용자 승인 후 실행 — 상세 §E.2.6 |
| **ASSUMPTION-55** (Layout pool) | **GO(판독) / 데이터 없음** | `DataPool/Layouts` → 1개(`Default`). `DataPool/Layouts/1` → **childCount 0**(할당 요소 0), `PositionX`/`PositionY` 판독 가능(둘 다 `"0"`). **판독은 되나 이 쇼파일에 좌표 정보가 없다** → 보조 출처로서 무가치 |
| **ASSUMPTION-56** | **`SKIP:` (`CONDITION_NOT_MET`)** | D-3이 Layout 기록을 v1에 포함하지 않는 한 프로브 대상 아님 |
| **ASSUMPTION-57** (FID 주소) | **GO** (기계+사람) | `fid` 판독 19개 전부 상이(1~19). **사람 관측**: `Fixture 14` 선택+딤머 100 → 정확히 1대, 일렬 배치의 왼쪽에서 4번째가 점등 확인 |
| **ASSUMPTION-58** (선택 순서→방향) | **GO** (사람) | 좌표·페이저 문법 **완전 동일**, 선택 순서만 반전 → 웨이브 방향이 반전. 상세 §E.2.7 |
| **ASSUMPTION-59** | **`SKIP:` (`CONDITION_NOT_MET`)** | M6 여유 시 후보 |
| **ASSUMPTION-60** (예산) | **실측 완료** | 아래 §E.2.2 |

### §E.2.2 예산 실측 (ASSUMPTION-60 — D-1 결정 재료)

| 지표 | 실측값 |
|---|---|
| 왕복당 지연 | **66.7 ms** |
| 18 픽스처 × 3축 | **54 왕복 / 3.60 s** (판독 성공 18 · 실패 0) |
| 30 픽스처 × 3축 외삽 | 90 왕복 ≈ **6.0 s** |
| 30 픽스처 × 4축(+fid) 외삽 | 120 왕복 ≈ **8.0 s** |
| 드릴다운 캡(`tools.py:173`) | 16 — 90 왕복은 **5.6배 초과** |

`prop` 루프는 **오늘의 응답기로 동작하며**(재배포 0 · 와이어 확장 0), 30대 리그 6초는 운용상 수용 가능하나
왕복 캡 규율과는 정면 충돌한다. 이것이 D-1의 실측 재료다.

### §E.2.3 절단(truncation) — 라이브 실측

`Patch/Stages/1/Fixtures` 스냅샷: **`childCount: 19` · 반환 `children` 18 · `truncated: true`**.
누락된 slot 19는 `prop` 직접 판독으로 **정상 응답**(`name:"MMX 19"`, `fid:"19"`, `posx:"0.0"`).

→ **오늘의 리그가 이미 절단 경계를 넘는다.** design.md §7이 경고한 뮤테이션 함정("재료가 상한 미만이면 절단 코드를
제거해도 통과한다")은 이 표적에서 **성립하지 않는다** — 19 픽스처 컨테이너가 그대로 유효한 절단 테스트 재료다.
값 절단이 아니라 **항목 탈락**(`truncated`)이라는 점도 확인(design.md §2.3의 두 신호 구분).

### §E.2.4 ⚠ 핵심 발견 — 리그가 공간적으로 축퇴(degenerate)해 있다

**19 픽스처 전부 `(posx, posy, posz) = (0.0, 0.0, 0.0)`. 서로 다른 xyz 조합은 1가지뿐.**

이것은 판독 결함이 **아니다**. 같은 채널·같은 왕복에서 `fid`는 19개 서로 다른 값을, `name`은 19개 서로 다른
문자열을 돌려줬다 — 채널은 개체별 실값을 반환하고 있고, **좌표가 실제로 전부 0**이다.
acceptance.md §D edge의 *"(0,0,0) 전대는 데이터 없음이 아니다 — 판독 성공한 실좌표이며 저신뢰 신호+강등의 대상"*
이 가설이 아니라 **이 쇼파일의 현재 상태**다.

파급:

1. **축 의미(semantics) 미확인** — 전 값이 0이므로 `posx`가 무대 X축에 대응하는지 **값 대조로 판별 불가**(P3의 값 대조 절반이 무력). 닫으려면 WRITE 프로브(알려진 값 기록→재조회→3D 뷰어 확인)나 실좌표 리그가 필요하다.
2. **M6 라이브 E2E("같은 지시, 두 리그")가 좌표 없이는 구성 불가** — plan.md §B M6이 예비한 두 분기(WRITE 생성 / 사용자 GUI 패치 편집) 중 하나가 **필수**가 된다. WRITE는 선택 축이 아니라 이 SPEC의 실증 경로다.
3. **M1/M2는 영향 없음** — M1은 판독 형상, M2는 순수 분석(golden 합성 픽스처)이라 축퇴 리그와 무관하게 진행 가능하다. 오늘의 리그에 대해서는 M1이 저신뢰+강등을 **올바르게** 보고하는 것이 정답 동작이다.

### §E.2.5 D-5 조기 해소 — 응답기 버전 (실측)

plan.md §F D-5는 INTROSPECT-001이 **1.6.0**을 예약했다고 적었으나, 라이브 실측은 **1.6.1**이다
(`introspect rejects enumerators missing same-handle prop-readable names`). **1.6.0·1.6.1 둘 다 소진**되었으므로
본 SPEC이 D-1/D-2에서 신규 동사를 채택하면 **`M.VERSION = 1.7.0`**이다. `1.6.0`을 잡으면 충돌한다.

부수 발견: 라이브 콘솔은 **본 브랜치에 없는 응답기**(1.6.1)를 돌리고 있다. `.moai/specs/SPEC-COPILOT-INTROSPECT-001/`은
이 브랜치에서 **untracked**다. M1이 신규 동사를 채택할 경우 두 SPEC의 머지 순서가 실제 의존이 된다.

### §E.2.6 M0 WRITE 축 — P4·P6 (사용자 승인 후 실행)

실행: `scratchpad/spatial_m0/probe_write.py`. 표적 분리 준수 — P1/P2는 slot 1, P3은 slot 2, **WRITE는 slot 5(C)·6(D)**.
원값을 **먼저** 전부 판독해 보관하고, 복구는 `finally`에 두어 예외 경로에서도 실행된다.

| 프로브 | 판정 | 실측 |
|---|---|---|
| **P4** 커맨드라인 `Set` | **GO — 첫 후보에서 성립** | `Set Fixture 5 Posz 2.5` → `ok:true, result:"OK"` → **재조회 `posz="2.5"`**. 기존 exec/게이트 경로 그대로이며 **응답기 기록 동사 불요** |
| **P5** Lua 대입 | **불필요 — 미실행** | P4가 성립하여 사다리를 내려갈 이유가 없다. 프로브 플러그인 Import 0 → GUI 삭제 부채 0 |
| **P6** 날조 기록 대조군 | **변별력 확인** | `Set Fixture 6 Poszz 2.5` · `... NotARealProperty 2.5` → 둘 다 **`ok:false` + `result:"Illegal property"`**, 실좌표 6축 **변화 0** |
| **P4b** 축 의미 | **1:1 확인** | `Posx 1.0` → x만 이동 · `Posy 2.0` → y만 · `Posz 3.0` → z만. 축 이름과 무대 축이 독립·정확히 대응 |
| **복구** | **완료** | slot 5·6 6축 전부 원값(`0.0`) 복귀, 재조회 일치. 쇼파일 잔여 **0** |

**D-2 해소**: 기록 채널 = **커맨드라인 `Set`**. plan.md §F D-2가 우려한 "응답기 최초의 쓰기 표면 + 게이트·감사·승인 재설계"는
**발생하지 않는다**. 기존 승인·감사 경로를 그대로 탄다.

#### ⚠ §E.2.6a 기록 문법의 함정 — `ok`가 거짓말하는 축을 찾았다

READ의 `prop`은 변별적이었지만(§E.2.1), **기록은 그렇지 않다.** 음수 좌표 기록을 5가지 형태로 대조한 실측:

| 발화 | 재조회 결과 | 콘솔 응답 |
|---|---|---|
| `Set Fixture 11 Posx '-3.5'` | **-3.5 — 정확** | OK |
| `Set Fixture 11 Posx (-3.5)` | 무변화 | `Not allowed` (정직한 실패) |
| `Set Fixture 11 Posx -3.5` | **3.5 — 부호 소실** | **OK** |
| `Set Fixture 11 Posx - 3.5` | **무변화 (조용한 무동작)** | **OK** |
| `Set Fixture 11 Posx 0-3.5` | **0.0 — 엉뚱한 값** | **OK** |

**5건 중 3건이 `OK`를 돌려주면서 틀린 값을 쓰거나 아무것도 쓰지 않았다.** 이것이 REQ-SPATIAL-021(기록 후 재조회 검증)이
장식이 아니라는 라이브 증거다. 무대 좌표계는 원점 좌우로 음수가 정상이므로(acceptance §D) 이 함정은 M4의 주경로에 있다.

→ **M4 계약**: 값은 **항상 작은따옴표로 감싼다** — `Set Fixture <fid> <Axis> '<value>'`. 양수·음수 모두 이 형태로 정상 동작한다.

**부수 제약 2건**:

1. **`exec`는 큰따옴표를 거부한다** (`protocol.py:109` `_validate_rest`). MA3 문서 관용인 `Set ... "Posz" "2.5"`는 이 채널로
   보낼 수 없다. 다행히 작은따옴표가 동작하므로 M4는 제약 안에서 성립한다.
2. **float32 정밀도 드리프트** — `9.9`를 기록하면 `9.8999996185303`으로 읽힌다. **재조회 검증을 문자열 동등성으로 하면
   정상 기록을 실패로 오판한다.** M4의 검증은 반드시 **수치 허용오차** 비교여야 한다(AC-SPATIAL-019/020 구현 시 필수).

### §E.2.7 M0 P8 — FID 주소 + 선택 순서 (사람 관측, ASSUMPTION-57/58)

실행: `scratchpad/spatial_m0/probe_p8.py` (stage1/stage2/stage3/revert). 표적 fid 11~18 — READ/WRITE 프로브와 분리.
원좌표는 디스크(`p8_backup.json`)에 보관해 프로세스가 바뀌어도 복구가 성립하게 했다.

축퇴 리그(전대 0,0,0)에서는 웨이브를 볼 수 없으므로, **P4에서 확정한 기록 채널로 fid 11~18을 일시적으로 1×8 가로열**
(x = −3.5 … +3.5, 1.0 간격)로 배치한 뒤 관측하고 되돌렸다.

| 단계 | 발화 | 관측 |
|---|---|---|
| stage1 | 8대 좌표 기록 → 재조회 | 8/8 일치(음수 포함, 허용오차 비교) |
| stage1 | `Fixture 14` + `Attribute 'Dimmer' At 100` | **사람: 정확히 1대, 왼쪽에서 4번째** → ASSUMPTION-57 **GO** |
| stage2 | 순서 A `Fixture 11 + … + Fixture 18` + 2스텝 딤머 페이저 | **사람: 웨이브가 왼쪽 → 오른쪽** |
| stage3 | 순서 B `Fixture 18 + … + Fixture 11` (**나머지 전부 동일**) | **사람: 웨이브가 오른쪽 → 왼쪽 — 반전** |
| revert | `ClearAll` + 원좌표 8대 복원 | 8/8 복원 확인, 백업 파일 삭제. 쇼파일 잔여 **0** |

**ASSUMPTION-58 GO.** 좌표도 페이저 문법도 동일하고 **선택 순서만** 바꿨는데 방향이 뒤집혔다 —
*"MA3에서 웨이브 방향은 좌표가 아니라 선택 순서가 정한다"*(spec.md §A.1)는 이 SPEC의 존재 근거가 라이브로 확인됐다.

**중간 실패 기록(정직한 조사 결과)**: 첫 시도는 `Attribute 'Dimmer' At 100` 단일값 위에 `At Phase 0 Thru 360`을 걸었고,
전 발화가 `OK`였으나 **페이저가 돌지 않았다**(사람 관측: 켜진 채 정지). 페이저는 **최소 2스텝**이 필요하다 —
단일 정적값에는 팬할 대상이 없다(룰북 31:75 "set a value, `Step 2`, set the next value"). 수정 후 정상 동작.
`OK`가 효과를 보증하지 않는다는 또 하나의 사례이며, **32_spatial_design.md 문면에는 2스텝 형태만 싣는다.**

### §E.2.8 킥오프 결정 (D-1~D-5) — M0 실측 기반 확정

| # | 결정 | 근거 |
|---|---|---|
| **D-1** 판독 채널 | **후보 A(기존 `prop` 루프)로 v1**, B는 실사용 후 재평가 | 오늘의 1.5.0 응답기로 동작 · 재배포 0 · 와이어 확장 0 · INTROSPECT 의존 0. 30대 6.0s는 수용 가능. 왕복 캡(16) 충돌은 스키마의 `roundtrip_capped` 신호로 명시. 가산 추가라 후일 B 승격 비용이 낮다 |
| **D-2** 기록 채널 | **커맨드라인 `Set`** (값은 작은따옴표 필수) | P4 첫 후보 성립 — 응답기 기록 동사·신규 게이트 표면 불요(§E.2.6) |
| **D-3** Layout 기록 v1 포함 | **미포함 — 3D-only** | `Default` 레이아웃 할당 요소 0, `PositionX/Y` 전부 0 — 판독은 되나 정보가 없다(§E.2.1). REQ-SPATIAL-003·AC-SPATIAL-003 `[DEFERRED]` |
| **D-4** 툴 표면 | **2툴 분리** — `get_spatial_context` / `arrange_fixtures`, 닫힌 툴 집합 18 → 20 | 읽기와 쇼파일 변형을 한 툴에 두면 승인 카드 분류가 흐려진다. `test_tools.py:140`의 `== 18` 고정 테스트 갱신 대상 |
| **D-5** 응답기 버전 | **해소 — 신규 동사 채택 시 1.7.0** | 라이브 실측 1.6.1 → 1.6.0·1.6.1 모두 소진(§E.2.5). 단 D-1=A이므로 **v1은 응답기 무변경**, 버전 조율 자체가 불발동 |

**사용자 결정(2026-08-03)**: WRITE 프로브 실행 승인 · D-1은 A로 v1 · P8 사람 관측 즉시 수행 · INTROSPECT 분기 무시(1.5.0 표면만 사용).
D-1=A + D-2=커맨드라인의 결과로 **본 SPEC은 `console/lua/copilot_responder.lua` · `PROTOCOL.md` · `server/bridge/protocol.py`를
전혀 건드리지 않는다** — plan.md §C.2의 "조건부 EXTEND" 3건이 전부 **PRESERVE**로 확정됐다.

### §E.2.9 M2 — 공간 분석 계층 (`server/spatial/`)

M0 READ GO 확정 직후 착수. M1과 파일 무교차이므로 **병렬 실행**했다(§E.2.10).

- 신설: `server/spatial/{__init__,schema,rows,sorting}.py` · `server/tests/test_spatial_analysis.py`
- **신규 의존성 0** — 계측 결과 비표준 모듈 유입 **NONE**(`statistics`/`collections`/`dataclasses`만)
- **경계(AC-SPATIAL-013)** — `server/spatial/`에 `server.bridge|server.safety|server.orchestrator|pythonosc` grep **0건**
- 임계 상수 2종: `SPATIAL_ROW_NOISE_SPAN = 0.05`(m, 리깅 공차 절대 하한) · `SPATIAL_ROW_GAP_RATIO = 4`(중앙값 갭 배수)
- 테스트: **49 passed** (`test_spatial_analysis.py`) · `test_architecture.py` 포함 53 passed

**라이브 데이터 대조 스모크(합성 golden이 아닌 실측 입력)**:

| 입력 | 결과 |
|---|---|
| **오늘의 실제 리그**(19대 전부 0,0,0) | `rows=1` · `low_confidence=True` · `reason=no_spatial_spread` — acceptance §D edge의 정답 동작 |
| 1×30 | `rows=1` · 고신뢰 |
| 3×10 | `rows=3` · 고신뢰 → **AC-SPATIAL-009 구별 성립** |
| **P8이 라이브로 만든 1×8 행** | `left_to_right → (11…18)` · `right_to_left → (18…11)` |

마지막 행이 이 마일스톤의 닫힘이다: 분석 계층이 산출한 두 fid 사슬이 **무대에서 실제로 좌→우·우→좌 웨이브를 만든
바로 그 두 선택 순서와 일치**한다(§E.2.7). 순수 계층의 출력과 라이브 관측이 같은 것을 가리킨다.

### §E.2.10 병렬 실행 검증 (오케스트레이션 판정)

요청은 "병렬 진행 가능한지 검증"이었다. plan.md §G는 "병렬화할 독립 축이 없다"고 적었으나 **부분적으로 과장**이다.

| 축 | 병렬 가능? | 근거 |
|---|---|---|
| **M0·M6(라이브)** | **불가 — 물리적으로 강제됨** | 동시 클라이언트 2개를 실측 시도 → 두 번째가 `ReceivePortInUseError` (`server/bridge/osc.py:242`, *"No automatic port fallback"*). 수신 포트 9005는 단일 점유이며 코드가 **명시적으로 폴백을 거부**한다. 관례가 아니라 아키텍처 제약 |
| **M0 사람 관측(P8)** | 불가 | 사람 눈이 유일 채널이며 직렬 |
| **M1 ∥ M2** | **가능 — 실제로 병렬 실행함** | 파일 무교차: M1은 `server/orchestrator/tools.py`, M2는 신설 `server/spatial/`. **M2는 M0의 산출(채널 결정)에 의존하지 않는다** — 입력 스키마 `(fid,name,x,y,z)`는 design.md §2.3이 채널과 무관하게 고정했다. M2는 READ GO 여부에만 걸린다 |
| **M1 ∥ M3 ∥ M4** | **가능 — 실제로 3-way 병렬 실행함** | M0 전 게이트 GO 확정 후 세 마일스톤이 동시 착수 가능해졌다. M1·M4는 `tools.py`를 공유하지만 각자 자기 툴 항목만 추가하는 계약을 사전 고정해 충돌 없이 병합됐다(`TOOL_NAMES` 최종 20). M3는 `tools.py` 무접촉 |
| 킥오프 기준선 측정 | 가능 — 병렬 실행함 | pytest/vitest 기준선을 프로브 준비와 동시 실행 |

**결론**: 진입점 M0는 병렬 불가(물리 자원 + 사람 관측)이나, **M0 게이트 GO 직후 병렬 창이 열린다.** 본 세션은 그 창을 두 번 사용했다
— 1차 M2 단독, 2차 M1∥M3∥M4 3-way. plan.md §G의 Mode 5(순차) 판정은 **M0 구간에는 맞고, M1 이후 구간에는 틀리다.**
사전 고정한 교차 계약(툴 이름 분담·기록 문법·허용오차·M2 공개 API)이 병렬화를 가능하게 한 조건이다.

### §E.2.11 M1 — 공간 판독 툴 `get_spatial_context`

- `server/orchestrator/tools.py`: `TOOL_NAMES` += `get_spatial_context` · 핸들러 · 스키마 · 디스패치. `server/tests/test_spatial_context.py` 신설(32 테스트). `test_tools.py` 툴 개수 `18 → 20`
- 채널: D-1 후보 A(기존 `prop`) — **응답기 무변경**. 왕복 캡 **120**(30대 × 4프로퍼티 = 실측 8.0s). `name`은 컨테이너 스냅샷이 이미 주므로 프로퍼티로 읽지 않는다
- 캡 도달은 **픽스처 단위로** 중단 → 반쪽 읽힌 픽스처를 내보내지 않는다. 캡으로 못 본 픽스처는 `unreadable`이 아니라 **미관측**(acceptance §D의 미판독 vs 판독실패 구분)
- 절단은 **두 경로**로 판정 — 응답기 `truncated` 플래그 **또는** `childCount > len(children)` 산술. 각각 독립 테스트로 방어되어 한쪽만 삭제해도 빨개진다
- 뮤테이션 **8종 전건 RED**: 좌표 0 기본값 채움 · `truncated` 플래그 미판독 · `childCount` 산술 삭제 · 캡 무제한 · fid←슬롯 · fid←열거순서 · unreadable 누락 · `source` 오문자열

### §E.2.12 M3 — 연출 통합 + 룰북 `32_spatial_design.md`

- `server/spatial/choreography.py` · `server/rulebook/assets/v2.4.2/32_spatial_design.md` · `server/tests/test_spatial_choreography.py` 신설. `test_rulebook.py`에 12 테스트 추가
- 한정어 매칭은 **한국어 출발 조사**(에서/부터/에서부터/로부터/으로부터)로 방향을 읽는다 — 어순에 의존하지 않으므로 "오른쪽 무버를 왼쪽에서 오른쪽으로"도 `left_to_right`로 정확히 해석된다. LOOKLIB 규율 승계(폐쇄 어휘·NFC 정규화·조사 1개 허용·**동점 None**)
- 발화 9행: `ChangeDestination Root` / `ClearAll` / fid 사슬 / `Attribute 'Dimmer' At 0` / `Step 2` / `At 100` / `At Phase 0 Thru 360` / `At Speed <n>` / `ClearAll`
- **AC-SPATIAL-014**: 발화 전문에 좌표 실수값 0 — 정적 스캔 테스트로 고정. golden은 **P8이 라이브로 만든 1×8 리그(fid 11~18)** 기준
- 룰북 문면은 **본 세션 라이브 확인분만** — 특히 페이저는 2스텝 형태로만 싣는다(단일 정적값은 `OK`면서 무동작, §E.2.7 실측)
- **AC-SPATIAL-017**: 기존 5개 자산 `git diff --stat` **0** — 신설은 32 하나뿐

### §E.2.13 M4 — WRITE 툴 `arrange_fixtures`

- `server/spatial/presets.py`(순수 grid/row/circle) · `server/tests/test_spatial_arrange.py`(64 테스트) 신설. `tools.py`에 `arrange_fixtures` 추가
- 순서: **[fid→slot 실측 해석] → [전 대상 3축 원값 판독·보관] → [정적 범위 봉쇄] → [`run_commands`→`gate.screen()`] → [전축 재조회·수치 비교] → [복원 번들 동봉(전 분기)]**
- 발화 형태는 **양성 화이트리스트 정규식**으로 강제 — `Set Fixture <fid> <Pos[xyz]> '<v>'` 외에는 빌더를 떠날 수 없다. `rot*` 기록 0
- 허용오차 `1e-6`(상대·절대) — float32 상대 epsilon ≈1.2e-7의 8배 여유이면서 프리셋 양자화 `1e-4`보다 두 자릿수 작다. 따라서 **서로 다른 목표 좌표가 같은 허용대역으로 별칭되지 않는다** → 틀린 값이 통과할 수 없다
- LiveLock은 **백업 판독보다 먼저** 확인 → 잠금 시 프로퍼티 읽기까지 0송신
- 프리셋 기본값: spacing 1.0m(**P8 라이브 실측 배치와 동일**) · origin (0,0,0) 무대 중앙 · circle radius 3.0m · grid의 rows/columns는 **기본값 없음**(배치 형상 추측 금지)
- 뮤테이션 **7종 전건 RED**: 백업 판독 · 백업 부재 거부 · 재조회 불일치 검출 · 허용오차→문자열 동등성 · LiveLock 확인 · 범위 봉쇄 호출 · 부분 백업

### §E.2.14 AC-SPATIAL-031 — **`[DEFERRED]`** (게이트 risky 분류)

M4 위임 브리프가 `server/safety/**`를 do-not-touch로 묶어 하위 에이전트가 이 AC를 열어둔 채 **정직하게 보고**했다.
제약을 건 쪽이 오케스트레이터이므로 직접 닫으려 시도했고 — **되돌렸다.** 경과를 남긴다.

**설계 사실**: `SafetyGate.screen(commands)`는 커맨드 시퀀스만 받는다 — **호출자가 risky를 선언할 seam이 없다.**
툴 정의에도 승인 요구 플래그가 없다(`deploy_plugin`은 자체 배포 파이프라인의 별도 리뷰 게이트를 쓰며 재사용 불가).
게이트가 risky를 판정하는 유일한 경로는 `blacklist.yaml` 폐쇄집합이다. 따라서 AC-031은 **`server/safety/` 개정을 요구한다.**

1차 구현은 `blacklist.yaml` v1→v2에 `"Set Fixture"`를 넣어 성립했다(규칙 ③ 발동 순서·승인 거부 시 0송신·MAtricks 무영향
3건 통과, 뮤테이션 RED 확인). **그러나 두 개의 독립 가드가 반대했다**:

1. **spec.md §C.2** — `server/safety/**`는 *"PRESERVE — 게이트·백업·블랙리스트는 **소비만**"*
2. **`test_overlap_preserve.py::TestSafetyChokepointFileSet`** — SPEC-COPILOT-OVERLAP-001의 **상시 불변식 게이트**가
   safety 변경 파일셋을 `{audit, backup, console, gate}`로 고정한다. `blacklist.yaml`이 5번째로 추가되며 실패했다.
   이 모듈은 스스로 *"NOT regression tests — INVARIANT GATE"*, 잡는 대상은 *"a FUTURE edit crossing a boundary nobody
   re-checks"*라고 적는다. 즉 정확히 설계된 대로 작동했다.

**사용자 결정(2026-08-03)**: **되돌림 — AC-SPATIAL-031 `[DEFERRED]`, 후속 SPEC 이양.** 저장소가 독립된 두 경로로
"safety는 이 SPEC의 소유가 아니다"라고 말하는데 가드를 고쳐 통과하는 선례를 남기지 않는다. plan.md §B M4의
*"risky 스크리닝 분류 확장"* 문면도 함께 `[DEFERRED]`로 읽어야 한다.

**되돌린 것**: `blacklist.yaml`(v1 복귀) · `test_safety_ruleset.py` · `test_safety_gate.py` — 3파일 모두 `4d298b8` 상태로 복원.

#### ⚠ 되돌림의 대가 — 정직하게 적는다

`Set Fixture … Pos*`는 다시 **`safe`로 분류**된다. 결과:

- **`arrange_fixtures`에 승인 카드가 없다.** 게이트가 그대로 통과시킨다 → **REQ-SPATIAL-024("승인 흐름 필수")는 현재 미충족**이며 AC-031과 함께 `[DEFERRED]`로 읽어야 한다.
- **showfile 스냅샷이 없다.** 백업 규칙 ③ `before_risky_execution()`은 risky 경로 전용이므로 발동하지 않는다.
- **여전히 남아 있는 방어선**(게이트 판정과 무관하게 동작): 기록 전 원좌표 백업 의무 · 재조회 수치 검증 · 복원 번들(전 분기 반환) · 범위 봉쇄 · rot* 기록 0 · LiveLock 강등. M4의 뮤테이션 7종은 전부 이것들을 지킨다.
- **트립와이어를 심었다** — `test_spatial_arrange.py::test_a_coordinate_bundle_is_not_yet_classified_risky`가 현재 상태(`risky is False`)를 **테스트로 고정**한다. 후속 SPEC이 분류를 추가하면 이 테스트가 빨개지며 "승인 흐름 단언으로 교체하라"는 메시지를 낸다. 갭을 방치가 아니라 **감시**로 전환한 것이다.

### §E.2.15 회귀 (M5 축)

| 시점 | pytest | vitest |
|---|---|---|
| 킥오프 기준선 | 4246 passed · 5 skipped · **0 failed** | 350 passed · 15 files |
| M2 후 | 4295 passed · 5 skipped · 0 failed (Δ +49 = M2 신규분) | — |
| M1·M3·M4 후 (1차) | 4492 passed · **1 failed** | — |
| 블랙리스트 개정 후 (2차) | 4499 passed · **2 failed** | 350 passed |
| Z축 검증·AC-031 되돌림 후 (3차) | 4507 passed · **3 failed** | — |
| **최종** | **4506 passed · 5 skipped · 0 failed** | **350 passed · 15 files** |

**1차 실패 1건의 정체**: `test_fx_boundary.py::test_the_asset_set_is_the_one_the_prefix_is_assembled_from` — 룰북 자산 목록을
5개로 핀한 테스트가 32 추가를 잡았다. **이 테스트는 제 일을 했다**(자산 추가·삭제 시 고정 접두가 바뀐다는 경고). 32 추가는
본 SPEC의 의도된 변경이므로 기대 목록에 32를 추가해 **비준**했다. 회귀가 아니다.

**2차 실패 2건의 정체**: `test_spatial_arrange.py`의 `test_the_unlocked_control_actually_writes` ·
`test_the_bundle_is_screened_before_anything_is_executed`. AC-SPATIAL-031로 `Set Fixture`가 risky가 되자, 승인 포트 없이 만든
테스트 게이트(기본 `DenyAllApprovalPort`)가 번들을 **정상적으로 보류**했다 — 제품 동작이 옳고 픽스처가 낡은 경우였다.
당시엔 승인 포트를 하네스에 주입해 해소했으나, **AC-031을 되돌리면서 이 하네스 변경도 함께 원복**했다(§E.2.14).
`Set Fixture`가 다시 `safe`이므로 게이트가 승인 없이 통과시키는 것이 현재의 정상 동작이다.

**3차 실패 3건의 정체**: 타 SPEC의 상시 불변식 게이트 3건 — §E.2.19에 전건 기록. 전부 설계대로 작동했고,
각각 비준·트립와이어 갱신·사용자 승인 정밀화로 처리했다. 회귀가 아니다.

**경계 검증**:

- `server/spatial/` → `server.bridge|server.safety|server.orchestrator|pythonosc` grep **0건** (AC-SPATIAL-013)
- `server/spatial` 임포트 시 비표준 모듈 유입 **NONE** (신규 의존성 0)
- 룰북 기존 5개 자산 `git diff --stat` **0** (AC-SPATIAL-017)
- 닫힌 툴 집합 **20** (`get_spatial_context` · `arrange_fixtures` 포함)
- 뮤테이션 필수 5건 전건 확인: AC-004/006(M1 8종) · AC-019/020(M4 7종) · **AC-031(블랙리스트 제거 → 3 failed RED)**

### §E.2.16 M6 — 라이브 E2E: 같은 지시, 두 리그 (AC-SPATIAL-029)

**설계 요점**: 두 리그를 단순히 1행/3행으로만 나누면 fid 순서와 공간 순서가 우연히 일치해 사슬이 **같아진다**(1차 시도에서 실측).
그러면 아무것도 증명하지 못한다. 그래서 **패치 순서 ≠ 설치 순서**인 현실적 리그를 구성했다.

같은 9대(fid 11~19) · 같은 지시 `"왼쪽에서 오른쪽으로 웨이브"` · 같은 페이저 문법:

| 리그 | 물리 배치 | 검출 | 앱이 낸 선택 사슬 | 사람 관측 |
|---|---|---|---|---|
| **A** | 1행 9대, **패치 역순 설치**(fid 11이 맨 오른쪽) | 1행 | `Fixture 19 + 18 + 17 + 16 + 15 + 14 + 13 + 12 + 11` | **왼쪽 → 오른쪽** ✓ |
| **B** | 3행×3열, **열 단위 패치**(11/12/13 = 왼쪽 열) | **3행** | `Fixture 11 + 14 + 17 + 12 + 15 + 18 + 13 + 16 + 19` | **왼쪽 → 오른쪽** ✓ |

- **기계 판정**: 두 사슬이 구조적으로 다르다(행 수 1 vs 3, 순서 완전 상이). 발화 전문에 **좌표 리터럴 0건**(라이브 번들 대상 재확인)
- **사람 판정**: 두 경우 모두 무대에서 지시대로 왼쪽→오른쪽으로 흘렀다
- **핵심**: 리그 A에서 fid 순서(11→19)로 불렀다면 **오른쪽→왼쪽으로 후진**했을 것이다. 실측 좌표로 정렬해 사슬을 반전시킨 결과가
  지시와 일치했다 — *"1행×30과 3행×10에 같은 커맨드를 내는 앱은 배치를 모르는 앱이다"*(§0)의 반증 대상이 사라졌다
- **원상복구**: 9대 3축 전부 원값 복귀 확인 → 최종 전수 검사에서 **19대 전부 원점**, 프로그래머 `ClearAll`. 쇼파일 잔여 **0**

### §E.2.17 M0/M6 라이브 세션 정리 — 쇼파일 잔여 0

본 SPEC은 라이브 콘솔에 총 6회 기록했다(P4/P6 WRITE 프로브 · P8 1×8 · M6 리그A · M6 리그B · Z 수직열 · Z 수직벽).
**전부 원상복구 확인**했다.

- 최종 전수 검사: 19 픽스처 × 6축 전부 원값(`0.0`) — 이탈 **0건**
- 프로그래머: `ClearAll` — 잔여 선택·값 0
- 생성 오브젝트 **0** · 삭제한 오브젝트 **0** · 프로브 플러그인 Import **0**(P4가 첫 후보에서 성립해 P5 불필요)
- SCENE-001 M0가 남긴 "시퀀스 7개 GUI 삭제" 류의 정리 부채 **없음**
- 프로브 스크립트는 스캐폴딩이므로 세션 종료 시 제거했다 — 판정·발화 형태·수치는 전부 본 §E.2에 기록되어 재현 가능하다

### §E.2.18 ⚠ Z축(높이) 검증 — 사용자 지적으로 발견한 미검증 축과 그 결함

**지적**: *"x, y축의 배열만 테스트했고 Z축 배열은 검증하지 않았다."* 정확했다.

**갭의 정확한 범위**: `posz`는 **프로퍼티 단위로만** 검증돼 있었다 — P3 판독(`0.0`)· P4b 기록(1대에 `Posz 3.0` → 재조회 일치,
타축 무영향)· P6 날조 대조군. 반면 **배열 단위 검증은 0**이었다: P8·M6 리그A·M6 리그B **전부 z=0.0 고정**.
그런데 `presets.py`는 z 배열을 **지원한다** — `row:"z"`(수직 열)· `grid:"xz"`(수직 벽)· `circle:"xz"`(수직 링).
즉 **출하된 기능 경로가 한 번도 실행되지 않았다.** 또한 x는 사람 관측("왼쪽에서 4번째")이 있었지만 **z는 아무 관측도 없었다.**

#### 라이브 검증 (프로덕션 빌더 `spatial_preset_placements` + `arrange_write_commands` 사용)

| 대상 | 기록 | 결과 |
|---|---|---|
| 수직 열 (`row`/`z`, 6대) | z = −2.5 … +2.5 (**절반이 음수**) | 6/6 재조회 일치 |
| 수직 벽 (`grid`/`xz`, 2×3) | x = −1/0/+1 × z = −0.5/+0.5 | 6/6 재조회 일치 |

**사람 관측 2건 (신규)**:

- 수직 열 → *"수직으로 쌓였고 fid 11이 제일 낮고 fid 16이 제일 높다"* → **`posz` = 높이, `+z` = 위** 확정. 이로써 세 축 전부 사람 관측 근거를 갖는다(x=좌우 · y=깊이/행 · z=높이).
- 수직 벽 → *"2단×3열 수직 벽 — 바닥 그리드 아님"* → `xz` 평면이 수직임 확정.

#### 발견한 결함 2건과 수정

**(1) `no_spatial_spread`가 거짓을 말했다.** 5m 수직 열에 대해 *"공간 확산 없음"*을 반환했다. 확산은 5m 있었고, 다만 분석이
쓰지 않는 축에 있었다. 더 나쁜 것은 이 신호가 **진짜 축퇴 리그(전대 0,0,0)와 같은 값**이라, *"쇼파일에 좌표가 없다"*와
*"의도된 수직 리그인데 이 어휘에 표현할 말이 없다"*는 완전히 다른 두 상황이 한 신호로 붕괴했다.

→ 폐쇄집합에 **`vertical_spread_only`** 신설. 두 상황이 이제 서로 다른 사유를 받는다.

**(2) 수직 벽을 `rows=1` + 고신뢰로 보고했다.** `arrange_fixtures`가 `resolved.rows=2`로 만든 리그를 `get_spatial_context`가
자신 있게 1행이라 답했다 — 기록층과 판독층이 같은 리그를 두고 조용히 불일치했다.

→ **`rows`의 정의는 바꾸지 않았다.** 행은 y축 기반이 SPEC 설계(design.md §3.1)이고 평면도에서는 그게 옳다. 수직 벽의
**깊이 행이 1개인 것은 사실**이다. 문제는 `row_count: 1`만 말하면 평평한 바로 읽힌다는 것 — 그래서 **`vertical_span`(측정된
z 범위)을 스키마·회신에 1급 필드로 추가**했다. 측정하고, 말하고, 행 분할에는 쓰지 않는다. **분석이 무시하기로 한 축에 대한
침묵이 판정을 실제보다 완전해 보이게 만든다.**

**오탐 방지**: 실제 트러스는 수 cm 편차로 걸린다. 3cm 편차 1×6 바는 **고신뢰 유지**(`vertical_span=0.03`) — 가장 흔한 리그에서
경보가 울리지 않는다. 높이가 행을 만들지 않는다는 것도 테스트로 고정했다(평평한 바에 z를 더해도 행 수 불변).

- 신규 테스트 **8건**(`TestVerticalAxisIsMeasuredAndReported`) · 뮤테이션 **2종 RED**: 사유 붕괴 복원 → 2 failed · `vertical_span` 미보고 → 4 failed
- 이 결함은 **z 배열을 한 번도 실행하지 않았기 때문에** M0~M6 전 과정을 통과했다. 프로퍼티 검증이 배열 검증을 대신하지 못한다는 사례로 남긴다.

### §E.2.19 타 SPEC 불변식 게이트와의 충돌 — 3건

커밋 후 상시 게이트 3건이 실패했다. **전부 정확히 설계된 대로 작동한 것**이며, 각각 성질이 달랐다.

| 게이트 | 성질 | 처리 |
|---|---|---|
| `test_fx_boundary.py` 룰북 자산 목록 핀(5개) | 자산 추가·삭제 시 고정 접두가 바뀐다는 경고 | 32 추가는 본 SPEC 의도 → 기대 목록에 추가해 **비준** |
| `test_songcue_bundle.py` tools.py 헝크 목록 | 파일 주석이 *"TRIPWIRE, not a constant — 나중 SPEC이 정당하게 tools.py를 고치면 의도적으로 갱신해야 한다"*고 명시. FXLIB·SCENE·PRESHOW·PRECHK·T-J가 각각 같은 절차를 밟았다 | 헝크 목록 갱신 + 본 SPEC이 무엇을 추가했는지 주석. **진짜 불변식(`_TOOLS_PROTECTED_OLD_RANGES` 겹침 0)은 별도 검증 — 겹침 NONE 실측** |
| `test_overlap_preserve.py` 룰북 디렉터리 락 | OVERLAP-001의 상시 불변식 게이트가 `server/rulebook/assets/v2.4.2/` **전체**를 락 | **사용자 승인 후 정밀화**(아래) |

**룰북 게이트 정밀화(사용자 승인)**: 룰북 접두는 설계상 자라는 자산 집합(00→10→20→30→31→32)이므로 디렉터리 전체 락은
모든 미래 룰북 마일스톤을 영구 봉쇄하면서 "보존된 경계"처럼 읽힌다. 실제로 중요한 경계는 **기존 5자산의 byte-identity**다.
이 파일에 이미 있던 **2026-08-02 사용자 승인 예외 선례**(looks 라이브러리, 정확한 줄 텍스트로 핀)를 그대로 따랐다:

- `_PRESERVE_PATHS`의 디렉터리는 문서화된 경계로 **남기고**, diff에서는 **5개 명명 자산으로 치환**(looks 라이브러리와 동일 방식)
- 추가도 무제한 허용이 아니다 — 신규 `TestRulebookGrantedAddition` 4건이 **추가된 경로를 이름으로 핀 + 디렉터리 전체 삭제 0** 요구. 다른 새 파일이나 기존 파일 1바이트 삭제는 **여전히 실패**한다
- 비공허성: 락 목록을 실제 디렉터리 목록과 대조해 오타 경로가 영구 통과하는 것을 막는다

**safety 게이트는 정밀화하지 않고 되돌렸다** — §E.2.14.

### §E.2.20 라이브 앱 E2E — 자연어 지시 한 건을 끝까지 (2026-08-03)

마일스톤 검증이 아니라 **사용자 요구로 실행한 실사용 시연**이다. 대상 지시:

> *"모든 장비를 5미터 높이에 자연스럽게 배치하고 컬러와 딤머 이펙트를 사용해서 조명연출을 해줘"*

시뮬레이션이 아니다 — 실제 앱(`python -m server.web`)을 띄우고, UI가 쓰는 것과 같은 `/ws` 엔드포인트에 같은 `chat`
프레임을 보내고, 같은 Gemini 프로바이더·같은 툴 레지스트리·같은 안전 게이트·같은 라이브 onPC를 통과시켰다.

#### 선행 블로커 — Gemini 경로가 전부 죽어 있었다 (선재 결함, 별도 커밋)

첫 지시가 *"AI 서비스가 요청을 거부했습니다"*(`invalid_request`)로 실패했다. `_to_gemini_schema`가 미지 키를 그대로
통과시켜 `additionalProperties`가 Gemini function-declaration 스키마로 전달됐고, Gemini는 이를 400
`INVALID_ARGUMENT`로 거부한다. **실패는 툴 단위가 아니라 요청 단위**여서 캐시 경로·비캐시 폴백 모두 죽었다.

**책임 소재를 실측으로 갈랐다**: base `4d298b8` 워크트리에서 **동일 11종이 이미** 이 키를 갖고 있었다(툴 18개 시절).
본 SPEC이 추가한 2종은 같은 관례를 따른 것이며 원인이 아니다. 앱이 아예 기동 후 무응답이 되므로 수정했다 —
커밋 `a5fa16a`(DENY 리스트 · 테스트 5종 · 뮤테이션 4 failed RED). 중립 스키마는 그대로 두어 Anthropic 경로 무영향.

#### 실행 결과 — 한 턴으로는 불가, 내용은 양쪽 다 나왔다

한 턴 결과는 **`loop_limit`**이다. `DEFAULT_MAX_MODEL_CALLS = 12`(SPEC-COPILOT-MVP-001 §C 비용 상한, 런어웨이 가드)를
초과했고 앱은 *"일부 명령만 실행되었습니다 (부분 실행)"*로 **정직하게 보고**했다. 성공을 위장하지 않았다.

감사 로그(`server/audit_logs/audit-20260803.jsonl`)가 실제 실행을 증언한다:

| 시각 | 실행 내용 |
|---|---|
| 08:54:53 | `arrange_fixtures` — 단일 행(x −10.2…+10.2, 1.2m 간격), **18대 전부 z=5.0** |
| 08:55:37 | `Group 13` + 마젠타→시안 **컬러 2스텝 + 딤머 페이저 + ColorRGB 3축 페이저 + Speed 30** |
| — | 여기서 `loop_limit` |
| 08:57:48 | **공간 선택 사슬** `Fixture 1 + Fixture 2 + … + Fixture 18` + 시안 + `Attribute 'Dimmer' At Phase 0 Thru 360` |
| 08:58:07 | `arrange_fixtures` — **4행 테이퍼**(y=3.0/1.0/−1.0/−3.0, 6·5·4·3대), 전부 z=5.0 |

- **"5미터 높이"** ✅ — 두 배치 모두 `posz='5.0'`, 재조회 일치
- **"컬러와 딤머 이펙트"** ✅ — 컬러는 기존 룩/프리셋 계층에서, 딤머 웨이브는 본 SPEC의 공간 사슬에서
- **"자연스럽게"** ✅ — **모델이 `arrange_fixtures`를 fid 부분집합으로 4번 호출해 테이퍼를 합성**했다
  (`1–6→y=3.0` · `7–11→y=1.0` · `12–15→y=−1.0` · `16–18→y=−3.0`). `grid`는 등길이 행만 내므로 **단일 프리셋 호출로는
  만들 수 없는 형상**이다 — 폐쇄 프리셋 3종이 조합으로 열린 형상을 낼 수 있다는 실측이며, 이는 설계 의도의 확인이다
- **Z축 수정이 실사용에서 작동** — 전부 z=5.0이므로 `vertical_span = 0.0`(max−min), x 확산으로 1행 고신뢰.
  §E.2.18의 필드가 모델에게 정확히 전달되는 것을 확인했다

#### ⚠ 결함 1 — 픽스처 19가 배치에서 탈락했고 모델이 알리지 않았다

`Patch/Stages/1/Fixtures` 스냅샷은 `childCount 19` / 반환 18 / `truncated: true`다(§E.2.3). 따라서 `arrange_fixtures`는
**18대만** 배치했고, 최종 실측에서 **fid 19만 원점(0,0,0)에 남았다** — 1~18은 z=5.0.

**툴은 제 몫을 다했다**: `truncated: true` 보고 · `unreadable: []` · fid 19 좌표 **발명 0**. 앱에 원본 값을 물어 확인했다.
그리고 `get_spatial_context`의 설명문은 이미 명령형으로 적혀 있다:

> *"Either way the list is NOT the whole rig — **say so** rather than presenting a left-to-right order over the part you happened to receive."*

모델은 **금지된 바로 그것**을 했다 — 받은 일부에 대한 좌우 정렬을 제시하고 불완전성을 말하지 않았다.
**툴 결함이 아니라 모델 준수 갭**이며, *툴 설명은 지시일 뿐 강제가 아니다*라는 천장의 실측 사례다.
`server/looks/**`가 쓰는 방식(설명문이 규율을 운반)의 한계를 그대로 물려받는다.

→ 강제하려면 툴 계층이 `truncated: true`일 때 회신을 구조적으로 다르게 만들어야 한다(예: 부분 리그임을 나타내는
별도 상태값, 또는 정렬 결과 자체의 보류). **본 SPEC 범위 밖 — 후속 과제로 기록한다.**

#### ⚠ 결함 2 — 요청하지 않은 쇼파일 변형 (AC-031 되돌림의 실측 대가)

08:58:07의 두 번째 배치는 **요청하지 않은 것**이다. 해당 턴의 지시는 *"지금 배치된 좌표를 읽어서, 왼쪽에서 오른쪽으로
흐르는 딤머 웨이브에 컬러를 얹어 연출해줘"* — 연출만이다. 모델은 세션 대화 이력에 남아 있던 미완의 "자연스럽게 배치"
목표를 이어서 완성했다. 의도 자체는 합리적이다.

문제는 **그 사이에 사람이 없었다**는 것이다. `Set Fixture … Pos*`는 `[DEFERRED]` 결정으로 다시 `safe`이므로
(§E.2.14) 게이트가 승인 카드 없이 통과시켰고, showfile 백업 규칙 ③도 발동하지 않았다.
**사용자가 요청하지 않은 쇼파일 변형 54건이 아무 확인 없이 콘솔에 나갔다.**

이것이 §E.2.14에 *"되돌림의 대가"*로 적어둔 위험의 **관측 사례**다. 가설이 아니라 실제로 일어났다.
같은 턴의 `Go+ Page 1.202`(reference-invoking)는 정상적으로 승인 카드를 띄웠다 — 즉 **게이트는 건강하고,
좌표 기록만 그 그물을 통과한다.** AC-SPATIAL-031을 여는 후속 SPEC의 우선순위 근거로 이 관측을 인용할 것.

남아 있던 방어선은 설계대로 작동했다: 원좌표 백업·재조회 검증·복원 번들·범위 봉쇄. 복구도 그 경로로 했다.

#### 세션 정리

- 최종 전수 검사 후 **19대 전부 (0,0,0) 복귀** 확인, 프로그래머 `ClearAll`. 쇼파일 잔여 **0**
- 라이브 기록 누계: M0 프로브 2 · P8 1 · M6 2 · Z축 2 · **앱 E2E 2** = 8회, 전부 원상복구 확인

### §E.2.21 ⚠ 소급 발견 — 정렬 어휘 `left_to_right`의 기준이 house(객석)다

후속 SPEC(GROUPGEN-001) 조사 중 발견. **코드 동작은 정상이고 용어가 모호하다.**

**MA Lighting 공식 문서** (`help.malighting.com/grandMA3/2.2/HTML/qsg_3d_setup.html` ·
`.../patch_position_fixtures.html`) `[인수-웹, 규범]`:

- **X축 = stage left/right, 양수 = stage left 방향** · *"Stage right will be negative numbers"*
- **Y축 = downstage/upstage, 양수 = upstage**
- Z축 = height, 양수 = 바닥 위 · 기본 무대 30m×30m, 중앙 0 · Z 0~15m

무대 관례 `[인수-웹]`: **stage left/right는 배우 기준**(객석을 향해 선 배우의 좌우)이고
**house left/right는 객석 기준**이며 **둘은 정반대**다.

**실증** (x = −4 / 0 / +4 3대 리그):

```
left_to_right = (1, 2, 3)
  fid 1: x=-4.0 → stage RIGHT = house LEFT
  fid 3: x=+4.0 → stage LEFT  = house RIGHT
```

→ **`left_to_right`는 house left → house right, 즉 stage RIGHT → stage LEFT 다.**
조명 디자이너가 *"stage left에서 stage right로"* 라고 하면 **이 정렬의 역방향**을 뜻한다.

**결함의 성질**:

- **동작은 옳다.** P8 라이브 관측에서 사용자가 3D 뷰를 보며 최소 x를 "왼쪽에서 4번째"로 확인했고
  이는 객석 시점과 일치한다. M6의 두 리그 판정도 유효하다 — 사용자가 본 "왼쪽"이 house left였고
  코드가 그렇게 정렬했다.
- **용어가 기준을 명시하지 않는다.** `left_to_right`·`right_to_left`·한국어 "왼쪽/오른쪽" 모두
  누구 기준인지 말하지 않는다. 전문 용어로는 house 기준임을 밝혀야 한다.
- **`SPATIAL_ROW_ORDER = "y_ascending"`("stage front to back")은 의미는 맞고 낱말이 틀렸다** —
  표준 어휘는 `Downstage → Upstage`다.

**조치**: 폐쇄 정렬 어휘 개명은 **출하된 집합의 파괴적 변경**이므로 이 SPEC에서 하지 않는다.
**sync-phase 인계**: `spec.md`/`design.md`에 *"정렬 어휘의 left/right는 house(객석) 기준이며,
무대 기준 stage left/right와는 반대"* 를 명기한다. GROUPGEN-001은 그룹 이름에 맨 `Left`/`Right`를
쓰지 않고 `Stage Left`/`Stage Right`처럼 기준을 이름에 박는 것으로 대응한다
(`SPEC-COPILOT-GROUPGEN-001/research.md` §6.3).

## §E.3 Run-phase Audit-Ready Signal

- **마일스톤**: M0 ✓ · M1 ✓ · M2 ✓ · M3 ✓ · M4 ✓ · M5 ✓ · M6 ✓ (전 7개 완료) + Z축 검증 보강(§E.2.18)
- **ASSUMPTION 53~60**: 8건 전건 판정 — GO 5(53·54·55판독·57·58) · `SKIP:`(`CONDITION_NOT_MET`) 2(56·59) · 실측완료 1(60). 미해소 **0**
- **열린 질문 D-1~D-5**: **전건 해소**(§E.2.8). D-1=A · D-2=커맨드라인 `Set` · D-3=3D-only · D-4=2툴/20 · D-5=1.7.0(단 v1 응답기 무변경으로 불발동)
- **신규 파일**: `server/spatial/{__init__,schema,rows,sorting,choreography,presets}.py` · `server/rulebook/assets/v2.4.2/32_spatial_design.md` · 테스트 4종(`test_spatial_{analysis,context,choreography,arrange}.py`)
- **수정 파일**: `server/orchestrator/tools.py` · 테스트 6종(`test_tools` · `test_rulebook` · `test_fx_boundary` · `test_songcue_bundle` · `test_overlap_preserve` · 신규 4종). **`server/safety/**` 무변경**(§E.2.14 되돌림)
- **PRESERVE 확인**: `console/lua/copilot_responder.lua` · `console/lua/PROTOCOL.md` · `server/bridge/protocol.py` **무변경**(D-1=A의 결과). `server/looks/**` · `server/fx/**` · `server/scene/**` · `server/safety/**` · `ui/src/**` 무변경. 룰북 기존 5자산 byte-diff 0 · 삭제 0
- **테스트**: pytest **4511 passed · 5 skipped · 0 failed** · vitest **350 passed** (기준선 4246/350 대비 신규 실패 **0**)
- **뮤테이션**: AC-004·006(M1 8종) · AC-019·020(M4 7종) · Z축 수정(2종) · Gemini 스키마 수정(1종) 전건 RED. **AC-031은 `[DEFERRED]`이므로 뮤테이션 대상에서 제외**
- **라이브 증거**: M0 8판정 + M6 2리그 + Z축 2배열 + **앱 E2E 자연어 지시 1건**(§E.2.20) — **사람 관측 5회**(ASSUMPTION-57 · 58 · AC-029×2 · Z축 높이·수직벽). 라이브 기록 **8회** 전부 복구, 쇼파일 잔여 **0**
- **실사용 확인**(§E.2.20): 실제 앱 · 실제 `/ws` · 실제 Gemini · 실제 게이트 · 실제 onPC로 *"모든 장비를 5미터 높이에 자연스럽게 배치하고 컬러와 딤머 이펙트로 연출"* 실행. 5m 높이 ✅ · 컬러+딤머 이펙트 ✅ · "자연스럽게" → 프리셋 4회 조합으로 테이퍼 합성 ✅. **한 턴으로는 `loop_limit`**(`max_model_calls=12` 비용 상한) → 부분 실행을 정직하게 보고
- **선재 결함 1건 수정**(본 SPEC 범위 밖, 커밋 `a5fa16a`): Gemini가 `additionalProperties`를 거부해 **모든 턴이 400으로 실패**하고 있었다. base `4d298b8`에서 11종이 이미 보유 — 원인이 본 SPEC이 아님을 워크트리 실측으로 확인. 앱이 기동 후 무응답이라 수정
- **`[DEFERRED]` 3건**: ① Layout 기록(REQ-SPATIAL-003 · AC-SPATIAL-003) — ASSUMPTION-55 실측 근거 ② **AC-SPATIAL-031 risky 분류** — safety PRESERVE 경계(§E.2.14) ③ **REQ-SPATIAL-024 승인 흐름** — ②에 종속. ②③은 후속 SPEC이 `server/safety/`와 함께 소유해야 한다
- **sync-phase 인계 5건**: ① spec.md §C.2와 plan.md §B M4의 risky 분류 문면 모순 → §C.2를 정본으로 삼고 plan.md M4·AC-031을 `[DEFERRED]` 재표기 ② `arrange_fixtures`가 승인 카드 없이 쇼파일을 변형한다는 사실을 spec.md의 알려진 천장에 명기 ③ **AC-031 우선순위 근거로 §E.2.20 결함 2를 인용** — 요청하지 않은 좌표 기록 54건이 무승인 통과한 관측 사례 ④ **절단 시 모델 미고지**(§E.2.20 결함 1) — 툴 설명문만으로는 강제되지 않으므로 구조적 강제를 후속 과제로 등록 ⑤ **정렬 어휘의 기준 명기**(§E.2.21) — `left_to_right`는 house(객석) 기준이며 무대 기준과 반대다. MA3 공식 축 의미(+x = stage left)와 함께 `design.md`에 기록


## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
