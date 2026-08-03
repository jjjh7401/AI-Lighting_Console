# SPEC-COPILOT-SPATIAL-001 — 구현 계획 (plan)

status: draft (v0.2.0, 2026-08-03) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음.

base: `origin/main` = `3176900` · branch: `feature/SPEC-COPILOT-SPATIAL-001`

## §A. 접근 요약 (Context)

본 절은 **되돌리기 어려운 결정을 먼저** 배치한다. 빌드 순서(§B)와 리뷰 순서(§A.1)는 다르며, §A.2가 그 편차를 설명한다.

### §A.1 결정 우선순위 (리뷰 순서 — 빌드 순서 아님)

| 순위 | 결정 | 위치 | 왜 먼저 검토해야 하는가 |
|---|---|---|---|
| **1위** | **판독·기록 채널 확정** — posx 계열이 어느 채널로 읽히고 쓰이는가(기존 `prop` vs 신규 벌크 동사 / 커맨드라인 `Set` vs Lua 대입) | spec.md ASSUMPTION-53/54 · §F D-1/D-2 · **M0** | 와이어·게이트 표면·응답기 버전까지 전부 이 판정에 걸려 있다. 채널이 다르면 M1~M4의 형상이 전부 달라진다. **READ NEGATIVE면 SPEC 전체 중단.** |
| **2위** | **공간 스냅샷 회신·데이터 형상** — fid+xyz 맵의 스키마, 절단·캡 신호, 출처 명시 | spec.md REQ-SPATIAL-001/002/006 · **M1** | D-1이 신규 동사를 채택하면 와이어(콘솔 재배포)라 되돌리기 비용이 최고다. 채택하지 않아도 툴 회신 스키마는 하류(분석·연출·WRITE 리포트) 전부가 소비한다. |
| **3위** | **분석 스키마** — 행/정렬/신뢰 신호의 표현, 폐쇄 정렬 어휘 | spec.md REQ-SPATIAL-009~012/015 · **M2** | 순수 Python이라 되돌리기 비용 자체는 낮지만, 연출 통합(M3)과 룰북 문면(M3)과 WRITE 프리셋(M4)이 전부 이 스키마 위에 선다. |
| **4위** | **WRITE 안전 설계** — 원좌표 백업·복원 번들·승인 흐름·범위 봉쇄 | spec.md REQ-SPATIAL-020~024 · **M4** | 쇼파일을 실제로 변형하는 유일한 축. 설계 결함이 물리 리그 정보 손실로 직결된다. |
| 5위 | 툴 표면 이름·개수, 룰북 문면, 테스트 축 확장 | §F D-4 · **M3/M5** | 기계적 — 상위 결정 확정 후 자연히 따라온다. |

### §A.2 빌드 순서가 리뷰 순서와 다른 이유

빌드는 **M0(라이브 프로브)가 첫 마일스톤**이다. 이 저장소의 교훈이 순서를 강제한다: *"정적 프로브가 답할 수 없는 것은 실사격만 답한다"* — 그리고 여기서 답이 필요한 질문(프로퍼티 이름 대소문자, 판독·기록 채널, FID 주소 가능성, 선택 순서 효과)은 문서·코드·룰북 어디에도 답이 없다(research.md §4: 룰북에 실좌표 개념 전건 0). 웹 인수 조사는 타 버전 실증일 뿐 우리 콘솔의 실측이 아니다.

빌드 순서: **M0(프로브·GO/NO-GO) → M1(공간 판독 툴) → M2(분석 계층) → M3(연출 통합 + 룰북) → M4(WRITE) → M5(회귀·경계) → M6(라이브 E2E)**.

### §A.3 M0 게이트 — 축별 분기 (모두 유효한 출력)

| 축 | GO | NEGATIVE |
|---|---|---|
| **READ (ASSUMPTION-53)** | M1~M6 전체 진행 | **SPEC 전체 중단 — 블로커 보고.** 좌표 없이는 어떤 축도 성립하지 않는다. 대체 정책을 에이전트가 고르지 않는다(REQ-SPATIAL-026 (b)) |
| **WRITE (ASSUMPTION-54)** | M4 진행 | WRITE 축(REQ-SPATIAL-019~024, AC-SPATIAL-018~022/027/031) `[DEFERRED]` 재표기 — **manager-spec 재위임 경유**(§G 재위임 지점). READ 축은 그대로 진행 |
| **Layout pool (ASSUMPTION-55)** | 보조 출처로 포함 | v1은 3D-only — Layout 축(REQ-SPATIAL-003, AC-SPATIAL-003) `[DEFERRED]` |
| **FID 주소 (ASSUMPTION-57)** | 선택 순서 발화 진행 | **연출 통합(M3) 중단·블로커** — 정렬은 되는데 발화 대상을 지정할 수 없다면 사용자 결정이 필요하다 |
| **선택 순서 효과 (ASSUMPTION-58, 사람 관측)** | M3 설계 확정 | M3 중단·블로커 — MAtricks 단독 경로로의 축소는 사용자 결정 |

**NEGATIVE는 실패가 아니라 정직한 조사 결과다.** 단 READ NEGATIVE만은 SPEC의 존재 이유를 소거하므로 부분 진행 없이 중단한다.

## §B. 마일스톤 (M0..M6)

### M0 — 라이브 프로브: 판독·기록·대소문자·대조군 (cycle_type=ddd, 조사 중심 · **LIVE 필수**)

**목적**: ASSUMPTION-53~58(+60 예산 관측)을 닫는다. 코드 변경 0 · 기존 쇼파일 오브젝트 생성 0. **write 프로브는 좌표만 건드리고 반드시 원상복구한다** — SCENE M0의 시퀀스 7개 GUI 삭제 잔여 같은 정리 부채를 만들지 않는다(좌표 revert는 툴 경로로 가능하므로 `Delete` 블랙리스트 문제가 없다).

- **프로브 사다리(READ)**: 픽스처 1대를 표적으로 ① 기존 `prop` 동사에 LivePatch 경로 + `posx` 후보 변형(`posx`/`PosX`/`POSX`/`Posx`) 순차 시도 ② 성공 변형으로 `posy`/`posz`/`rotx` 판독 ③ **날조 대조군**: 존재하지 않는 `poszz` 판독이 **실패해야** 채널이 변별적이다 — `ok`로 돌아오면 그 사실 자체를 `CONDITION_NOT_MET`으로 기록하고 값 대조(물리적으로 아는 좌표와의 일치)로 판정을 대체한다.
- **프로브(WRITE — 별도 픽스처 표적)**: ① 현재값 판독·기록 ② 후보 채널 순차 시도 — (a) 커맨드라인 `Set` 계열(게이트 경유 exec — 성공 시 최선: 신규 게이트 표면 불요), (b) 일회용 프로브 플러그인의 Lua 대입(`fixture.posz = <v>`) ③ 재조회로 새 값 확인 ④ **날조 대조군**: 날조 프로퍼티에 기록 시도 → 실좌표 무변화 확인 ⑤ **원상복구**: 원값 재기록 + 재조회 일치. ①~⑤가 한 프로브다.
- **프로브(Layout pool)**: `DataPool().Layouts` children 반복 판독 — 요소 수·할당 오브젝트·`PositionX` 판독 가능성. 레이아웃이 쇼파일에 없으면 `SKIP:`(전제 미성립).
- **프로브(FID + 선택 순서 — 사람 관측, 별도 픽스처들)**: 판독된 fid로 `Fixture <fid>` 선택 → 사용자가 GUI에서 의도 개체 선택 확인(ASSUMPTION-57). 이어 서로 다른 두 순서의 가산 선택 + 딤머 페이저 → **웨이브 방향이 순서를 따라 달라지는지 사람이 관측**(ASSUMPTION-58). 프로그래머 상태는 `ClearAll`로 정리(쇼파일 무변형).
- **예산 관측**: 실제 리그 전대 좌표 판독의 왕복 수·회신 크기·절단 여부 실측(ASSUMPTION-60 재료).
- **판정 기록**: 전 판정을 `progress.md §E.2`에 폐쇄 어휘 + 행두 접두 행으로 기록(REQ-SPATIAL-026). **프로브별 표적 분리 명단을 실행 전에 적는다.** 미프로브 전제도 행을 받는다: ASSUMPTION-56(D-3이 Layout 기록을 v1에 포함하지 않는 한 프로브 없음)·ASSUMPTION-59(M6 여유 시 후보)는 M0 시점에 `SKIP:`(`CONDITION_NOT_MET`) 행으로 기록해 8행(53~60) 요건(AC-SPATIAL-025)을 충족한다.
- 산출물: 프로브 로그, 판정 8건, design.md §5 fold-in, §F D-1/D-2 결정 재료.

### M1 — 공간 컨텍스트 판독 툴 (`get_spatial_context` 안)

- M0가 확정한 채널로 픽스처별 `(fid, name, x, y, z)` 판독 — 신규 툴 1종. `get_rig_context`는 무변경(REQ-SPATIAL-008).
- 출처 명시(patch/layout) + 판독 불가 픽스처의 사유 있는 부재 보고(REQ-SPATIAL-004) + 절단·캡 신호(REQ-SPATIAL-006).
- D-1이 신규 벌크 동사를 채택한 경우: 응답기 분기 가산 추가 + `PROTOCOL.md` Revision note + `server/bridge/protocol.py` 빌더 + lupa 하네스 테스트 + **M.VERSION 조율**(§F D-5 — INTROSPECT-001과의 1.6.0 충돌).
- Layout pool 축은 ASSUMPTION-55 GO 시에만.

### M2 — 공간 분석 계층 (`server/spatial/` — 순수, 콘솔 무접촉)

- 행 검출(y축 클러스터링 — design.md §3), 정렬 4종(left_to_right / right_to_left / center_out / diagonal), 행별 그룹핑.
- 결정론 + 동률·모호 명시 신호(REQ-SPATIAL-010) + 저신뢰 신호(REQ-SPATIAL-012).
- golden 픽스처: 1×30, 3×10, 불규칙 배치, 동률 케이스. **1×30 vs 3×10 구조 구별이 단위 테스트로 고정**(AC-SPATIAL-009).
- 경계: transport/게이트 import 0 — `test_architecture.py` 자동 포섭 확인(REQ-SPATIAL-013).

### M3 — 연출 통합 + 룰북 `32_spatial_design.md`

- 공간 한정어 → 폐쇄 정렬 어휘 매칭(REQ-SPATIAL-015, LOOKLIB 매칭 규율 미러 — 한국어 조사 처리·폴백·동점 None).
- 선택 순서 발화: 정렬 fid의 가산 선택 사슬 + 기존 페이저/MAtricks 문법 결합(design.md §4). **커맨드에 좌표 0**(AC-SPATIAL-014).
- 룰북 `32_spatial_design.md` 신설 — sort-select-phaser 레시피. **문면의 커맨드 문법은 M0에서 라이브 확인된 형태만** 싣고, 미확인 문법은 M6 검증 후 확정 커밋(31의 validated 규율). 접두 byte-stable 테스트 + 기존 자산 byte-diff 0(AC-SPATIAL-016/017).
- 착수 게이트: ASSUMPTION-57·58 **GO**.

### M4 — WRITE: 배치 생성 (`arrange_fixtures` 안)

- 프리셋 좌표 계산(grid / row / circle — 순수 산술, golden 테스트) → M0 확정 채널로 기록.
- **기록 전 원좌표 백업 의무 + 복원 번들 리포트 동봉**(REQ-SPATIAL-020) + showfile 백업 규칙 ③ 연동 — 기록 번들의 **risky 스크리닝 분류 확장** 포함(규칙 ③ `before_risky_execution()`은 risky 경로 전용 — AC-SPATIAL-031).
- 기록 후 **재조회 검증** — 목표값 불일치는 명시 실패(REQ-SPATIAL-021).
- 범위 봉쇄: 명시 대상 외 0건 · rot* 기록 0건 · LiveLock 제안 강등(REQ-SPATIAL-022/023).
- 착수 게이트: ASSUMPTION-54 **GO**.

### M5 — 회귀 · 경계 · 안전 불변식

- 전체 pytest/vitest: run-phase 킥오프 기준선 대비 신규 실패 0건(기준선은 킥오프 시점 재측정 — plan-phase 수치 재사용 금지).
- 경계 grep: `server/spatial/` transport/게이트 import 0 · 룰북 기존 자산 byte-diff 0 · rig context 기존 테스트 무수정 PASS.
- 툴 개수 고정 테스트 갱신(18 → 확정 개수) — 개수·이름·설명 일관.
- **뮤테이션 필수 5건 실행**(AC-SPATIAL-004/006/019/020/031): 각 가드 제거 시 반드시 빨개짐 — 통과하면 재료 선택 오류로 재작성.
- D-1 신규 동사 분기: 기존 5동사·6 kind 회귀 전량 무수정 PASS(가산성).

### M6 — 라이브 E2E (**LIVE 필수**)

- **같은 지시, 두 리그**: "왼쪽에서 오른쪽으로 웨이브"를 1행 배치와 3행 배치에서 실행(3행 배치는 WRITE GO면 배치 생성으로, WRITE `[DEFERRED]`면 **사용자 GUI 패치 편집**으로 구성 — AC-SPATIAL-029는 어느 분기에서든 판정 가능하다) — 발화 커맨드가 구조적으로 다름(기계) + 무대 관측이 배치에 맞음(사람) + 결론 문장 기록(AC-SPATIAL-029).
- WRITE 왕복: 배치 생성 → 재조회 일치 → 3D 뷰어 사람 확인 → 복원 번들로 원상복구 → 재조회 일치(AC-SPATIAL-027 라이브 재확인).
- 룰북 문면 확정(M3의 미확정분이 있으면 이 시점 검증 후 커밋).
- 실패 시 해당 M으로 회귀하며 SPEC 실패로 집계하지 않는다.

## §C. 기술 제약

### §C.1 공통

- **신규 런타임 의존성 0.** 클러스터링은 표준 라이브러리 산술로 충분하다(design.md §3 — sklearn 등 금지).
- **와이어 프로토콜 버전 1 유지.** D-1 채택 시에도 가산 추가만(INTROSPECT-001과 동일 규율).
- **회신 예산**: `CONFIG.max_payload = 1900` — 초과는 조용한 드롭이므로 산술 고정 테스트가 유일한 그물(design.md §7).
- **읽기·기록 분리**: READ 경로에서 `Cmd()`·기록 0. WRITE 경로는 게이트 단일 관문 + 승인 흐름 필수(REQ-SPATIAL-024).
- 코드 주석·커밋 메시지는 영어(`language.yaml`), SPEC 문서는 한국어(저장소 관례).

### §C.2 PRESERVE 목록 (본 SPEC이 수정하지 않는 것)

| 대상 | 성질 |
|---|---|
| `server/looks/**` · `server/fx/**` · `server/scene/**` | PRESERVE — 읽기 import만(REQ-SPATIAL-018) |
| `server/looks/layout.py` · `server/orchestrator/layout_occupancy.py` | PRESERVE — executor layout, 본 SPEC과 무관(spec.md §A.2) |
| `server/rulebook/assets/v2.4.2/00~31` (5개 파일) | PRESERVE — byte-diff 0. 신설은 `32_spatial_design.md`만 |
| `server/safety/**` | PRESERVE — 게이트·백업·블랙리스트는 소비만 |
| `console/lua/copilot_responder.lua` · `PROTOCOL.md` · `server/bridge/protocol.py` | **조건부** — D-1이 신규 동사를 채택하면 EXTEND(가산), 아니면 PRESERVE |
| `ui/src/**` | PRESERVE — v1 표면은 기존 채팅 + 툴 |
| `get_rig_context` 경로·스냅샷 형상 | PRESERVE — 기존 테스트 무수정 PASS(REQ-SPATIAL-008) |

## §D. @MX 태그 대상 (예상 — 실제 배치는 run-phase에서 확정)

| 위치 | 태그 | 사유 |
|---|---|---|
| 좌표 발명 금지 가드(판독 부재 처리) | `@MX:ANCHOR` + `@MX:REASON` | 기본값 채움이 들어오는 순간 "배치에 맞는 연출"이 조용히 거짓이 된다 |
| 선택 순서 조립 지점 | `@MX:ANCHOR` + `@MX:REASON` | 순서가 곧 연출 방향 — 정렬 결과와 발화 순서의 1:1이 계약 지점 |
| WRITE 원좌표 백업 + 복원 번들 | `@MX:ANCHOR` + `@MX:REASON` | 물리 리그 정보의 마지막 방어선. restore SEND 부재(T-B2) 환경에서 유일한 복구 경로 |
| 기록 후 재조회 검증 | `@MX:WARN` + `@MX:REASON` | `ok:true`는 증거가 아니다(SCENE M0 실측) — 재조회 생략은 즉시 위험 |
| 절단·캡 신호 지점 | `@MX:ANCHOR` + `@MX:REASON` | 조용한 부분 판독은 이 프로젝트의 반복 결함(8룩 소실 선례 계열) |
| M0 채택 채널(판독·기록) | `@MX:NOTE` + `@MX:SPEC` | 어느 채널이 왜 채택됐는지 — 미래의 "다른 채널도 써보자"를 막는 근거 |

## §E. 테스트 스캐폴딩 계획

| 축 | 파일(예상) | 내용 |
|---|---|---|
| 공간 분석 | `server/tests/test_spatial_analysis.py` (신규) | 행 검출 golden(1×30/3×10/불규칙/동률), 정렬 4종, 결정론, 저신뢰 신호 |
| 판독 툴 | `server/tests/test_spatial_context.py` (신규) | 출처 명시, 발명 금지(뮤테이션), 절단·캡 신호(뮤테이션), FID 규율, 강등 신호 |
| WRITE | `server/tests/test_spatial_arrange.py` (신규) | 프리셋 좌표 golden, 백업 선행(뮤테이션), 재조회 검증(뮤테이션), 범위 봉쇄, LiveLock 강등 |
| 룰북 | `server/tests/test_rulebook.py` 확장 | 32 파일 포함 정렬 순서, 접두 byte-stable, per-show 값 부재 |
| 경계 | `server/tests/test_architecture.py` | `server/spatial/` 자동 포섭 확인, 게이트 관문 무우회 |
| 와이어 (D-1 조건부) | `test_lua_responder*.py` 확장 | 신규 동사 성공/실패/절단, 기존 5동사·6 kind 무수정 회귀, 예산 산술 |
| 가산성 | 기존 rig context·툴 테스트 전량 | 무수정 PASS + 툴 개수 고정 갱신 |

**뮤테이션 재료 주의(승계)**: 절단 테스트 재료는 반드시 예산 상한을 넘는 크기로 만든다 — 오늘의 실제 리그가 상한 미만이면 절단 코드를 제거해도 통과한다.

## §F. 열린 질문 (run-phase 진입 전 해소 필요)

- **[NEEDS CLARIFICATION: D-1 판독 채널 — 신규 벌크 동사 vs 기존 `prop` 루프]** — 30대 리그의 xyz는 prop 루프로 90왕복(왕복당 게이트+감사)이고, 벌크 동사면 1~2왕복이나 콘솔 재배포 + 와이어 확장 + INTROSPECT-001 버전 조율이 든다. M0의 예산 실측(ASSUMPTION-60)과 design.md §7 산술이 결정 재료다. **기본 권고: M0 실측 후 결정** — 실측 없이 와이어를 늘리지 않는다.
- **[NEEDS CLARIFICATION: D-2 기록 채널 — 커맨드라인 `Set` vs Lua 대입 동사]** — 커맨드라인이 동작하면 기존 exec/게이트 경로 그대로(최선). Lua 대입만 동작하면 응답기에 **기록 동사**가 생기며 이는 응답기 최초의 쓰기 표면이라 게이트·감사·승인 재설계가 필요하다. M0가 판정한다.
- **[NEEDS CLARIFICATION: D-3 Layout pool 기록의 v1 포함 여부]** — 3D 좌표 기록만으로 "배치 생성"이 충족되는가, Layout 뷰 요소 배치까지 필요한가. 3D-only가 기본 권고(Layout은 판독 보조만) — GUI 전환 API 부재로 Layout 기록의 가시 효과가 제한적이다.
- **[NEEDS CLARIFICATION: D-4 툴 표면 — 2툴(read/write 분리) vs 1툴(모드 인자)]** — 기본 권고 2툴 분리(`get_spatial_context` / `arrange_fixtures`): 읽기와 쇼파일 변형을 한 툴에 두면 승인 카드 분류가 흐려진다. 닫힌 툴 집합 18→20 갱신 확정 필요.
- **[NEEDS CLARIFICATION: D-5 응답기 버전 조율 — INTROSPECT-001과의 1.6.0 충돌]** — SPEC-COPILOT-INTROSPECT-001(draft)이 `M.VERSION` 1.6.0을 예약했다. 본 SPEC이 D-1/D-2에서 신규 동사를 채택하면 **먼저 머지되는 쪽이 1.6.0, 나중이 1.7.0**으로 조율한다. 두 SPEC 다 프로토콜 버전 1 유지·가산 추가이므로 충돌은 번호뿐이다.

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

### 입력 파라미터

- 도메인 수: 3~4 (콘솔 판독·기록 채널 / Python 분석·툴 / 룰북·매칭 / [조건부] 와이어)
- 예상 변경 파일: 10~14 (D-1 채택 시 +3)
- 라이브 콘솔 의존 마일스톤: 2 (M0, M6)
- 분기 게이트: M0 축별 5건 (§A.3)

### Decision: sub-agent (Mode 5, 순차)

### 정당화

마일스톤이 **직렬 의존**한다: M0 판정이 M1의 채널과 M3·M4의 착수 가능성을 정하고, M2 스키마가 M3·M4의 입력이다. 병렬화할 독립 축이 없고, 라이브 콘솔은 직렬 자원이다. 코딩 중심 작업의 기본 모드이기도 하다.

### 재위임 필요 지점

- **M0 WRITE NEGATIVE** → WRITE 축 REQ/AC `[DEFERRED]` 재표기는 spec.md 본문 편집 — **오케스트레이터 경유 manager-spec 재위임** 필요.
- **M0 READ NEGATIVE** → SPEC 전체 중단 — 블로커 보고 후 사용자 결정(폐기/재설계).
- M0 완료 보고에 이 두 지점을 명시할 것.
