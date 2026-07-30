# SPEC-COPILOT-PRECHK-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**). 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]`이며 **`[실측]`은 라이브 콘솔 직접 관측만**을 가리킨다.

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 6종 작성 (2026-07-29)

착수 SHA **`95687a0`**(= `origin/main`, SONGCUE 머지 직후), 착수 baseline **2490 passed · 5 skipped · 0 failed**(직접 실측, 이월 인용 아님).

| 커밋 | 산출 |
|---|---|
| `d8959f0` | `research.md` — 조사 + 비파괴 라이브 사전 프로브 |
| `a4de0c0` | `research.md` §4.7 — 채널 점유폭 도달 경로 + 절단 시 계수 신뢰성 |
| `284762f` | `spec.md` 최초 작성 + `research.md` §7.4 초크포인트 강제 충돌 |
| `6ef69f6` | `acceptance.md` — AC 17건, REQ 20/20 커버 |
| `ce8cbb6` | `design.md` + `plan.md` — 병렬 오케스트레이션 산출 |

### 조사 방법 — 2층이며 사전 프로브가 요구를 갈랐다

| 층 | 수단 | 산출 |
|---|---|---|
| 정적 | **병렬 read-only scout 4개**(Orca 오케스트레이션) | `.moai/state/verify/prechk-scout/{1-read-surface,2-rig-assets,3-rulebook,4-openq-and-process}.md` 586행 |
| 라이브 | **코디네이터 직접 비파괴 사전 프로브** — 읽기 전용 발화만, 쇼파일 **쓰기 0건** | `research.md` §4 · §5의 `[실측]` 표 |

**사전 프로브를 plan-phase에서 돌린 근거**: 1차 산출물의 성립이 *"픽스처 주소를 읽을 프로퍼티명이 존재하는가"* 하나에 걸려 있었고 scout는 그것을 **`미확정`**으로 남겼다(`prop`은 프로퍼티명을 열거할 수 없다). 그 전제가 거짓이면 6문서가 헛일이 된다. **판정은 M0가 소유하며 조사는 방향만 확립했다** — `ASSUMPTION-25`는 spec.md·acceptance.md·plan.md 전부에서 **"재확인만"**으로 일관 처리했다.

### 제안서 전제 2건이 거짓이었다

| 전제 | 판정 | 근거 |
|---|---|---|
| *"쇼파일 파서가 이미 있어 구현 부담이 낮다"* | **거짓** | `server/showfile/` 부재. XML 파싱은 `server/deploy/`와 `server/safety/console.py`뿐이며 MA3 쇼파일 구조를 읽지 않는다 |
| *"무응답 픽스처 탐지"* | **관측 경로 0건 → DESCOPE** | `build_exec_result`가 `pcall(Cmd, …)` 결과 문자열만 분류하고 하드웨어 피드백을 수집하지 않는다(`console/lua/copilot_responder.lua:690-706`). 동사 디스패치가 5종으로 닫혀 있다(`console/lua/copilot_responder.lua:884-946`). 두 scout가 독립적으로 같은 결론 |

**사용자 재범위 승인 1건**(2026-07-29): 패치 정합성 + 매크로 생성을 남기고 무응답 자동 탐지를 명시적 DESCOPE로 확정.

### 증거 등급 — 사전 프로브가 올린 것과 남긴 것

| 항목 | 착수 시 등급 | 조사 후 |
|---|---|---|
| 픽스처 주소 읽기 (`prop … Patch`) | `미확정` | **`[실측]`** — `'1.001'` 포함, 19개 중 관측된 18개 |
| 픽스처 열거 경로 | `미확정` | **`[실측]`** — `Patch/Stages/1/Fixtures`, `childCount` 19 / 반환 18 / `truncated` 참 |
| 채널 점유폭 도달 | 미조사 | **`[실측]`** — `Patch/FixtureTypes/1/DMXModes/1/DMXChannels` `childCount = 29` |
| 매크로 저작 문법 | T3 | **T3 유지** — 라이브 `OK` 0건. `ASSUMPTION-26`이 M0에서 판정 |
| 픽스처 → 점유폭 연결 | 미조사 | **`[미확정]`** — 표시 문자열뿐. `ASSUMPTION-27` |
| `FID` 값의 의미 | 미조사 | **`[미확정]` 이며 M0가 닫을 수 없다** — 아래 |

### 조사가 정정한 선행 산정 2건

**1. 절단 원인이 둘이다.** SONGCUE는 `max_children = 24`를 근거로 *"자식이 24를 넘으면"* 절단된다고 산정했다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:403`). **픽스처 19개에서 절단이 떴다**(`childCount` 19 / 반환 18) `[실측]`. 코드에 독립된 경로가 둘이다 `[코드]` — ① 자식 수 상한(`console/lua/copilot_responder.lua:610`, `cap`은 `console/lua/copilot_responder.lua:581`) ② **페이로드 예산 루프**(`console/lua/copilot_responder.lua:634-639`, `max_payload = 1900`). 픽스처는 이름이 길어 24에 닿기 전에 ②가 먼저 발동한다. `SONGCUE-F3/G3`(절단 거동 미실측)를 승계해 닫았다.

**2. 절단되어도 계수는 정확하다.** `node.childCount = total`이고(`console/lua/copilot_responder.lua:607`, `total`은 `console/lua/copilot_responder.lua:580`) 페이로드 루프는 `items`만 제거한다 `[코드]`. **"몇 개인가"는 정확하고 "무엇인가"만 불완전하다** — 그래서 완전성을 `truncated` 플래그가 아니라 **읽은 개수와 `childCount`의 비교**로 판정하고 못 읽은 개수를 수치로 보고한다(`AC-PRECHK-003`).

### `FID` — 정직하게 갈랐다

`console/lua/PROTOCOL.md:305-324`가 이 함정을 **본 조사보다 정확하게** 이미 문서화해 두었다 `[문서]`. 결정적 문장은 `console/lua/PROTOCOL.md:322-324`다 — *"the site calibration showfile has slot == FID by coincidence and so **CANNOT distinguish a correct FID probe from a slot probe**"*.

| 사실 | 등급 |
|---|---|
| `prop <fixture> FID`가 `ok=true`와 값 `'1'`을 반환한다 | `[실측]` — 새 사실. 위 문서는 `prop`이 없던 v1.4.1 시점에 쓰였다 |
| 그 값이 슬롯이 아니라 FID라는 것 | **`[미확정]`** — 이 쇼파일은 슬롯 == FID라서 원리적으로 판별 불가 |

**이것은 `ASSUMPTION`이 아니다** — 어떤 라이브 세션도 현재 쇼파일로 닫을 수 없고 **슬롯 ≠ FID로 패치된 쇼파일이 선행 조건**이다(사용자 GUI 작업). 본 SPEC은 그것을 기다리지 않고 **FID를 판정 근거에서 배제한 형상**으로 출하한다(`REQ-PRECHK-005`).

### 함정 3건을 요구로 승격했다

| # | 함정 | 승격된 요구 |
|---|---|---|
| T-1 | `ok=true`인데 값이 Lua 함수 참조(`'function: 0x105b0f048'`) — `safe_property`가 `handle[name]`을 그대로 반환한다(`console/lua/copilot_responder.lua:204-217`) | `REQ-PRECHK-003` · `AC-PRECHK-002` |
| T-2 | 공백 포함 프로퍼티명은 조회 불가 — `server/bridge/protocol.py:141`이 단일 토큰만 허용 | `AC-PRECHK-001` ③ |
| T-3 | 프로퍼티명을 열거할 수 없다 | `REQ-PRECHK-001`의 화이트리스트 |

### 강제 충돌 1건 — 착수 전에 발견했다

**`prop`은 프로덕션 경로로 도달할 수 없고 그 경로는 PRESERVE다**(`research.md` §7.4).

OSC 송신 표면을 import할 수 있는 디렉터리가 `server/bridge/` · `server/safety/` · `server/tests/` 셋으로 **테스트에 의해 강제**되고(`server/tests/test_architecture.py:27-39`, `server/tests/test_architecture.py:48-61` — `REQ-MVP-029`), `build_prop_query`에는 **프로덕션 소비자가 0건**이다 `[코드]`. 주소는 프로퍼티에만 있으므로 신규 모듈은 **구조적으로** 주소를 읽을 수 없다. 유일한 경로는 초크포인트에 조회 메서드를 추가하는 것이고 `server/safety/**`는 BUSKWIZ·SONGCUE가 잠갔다.

우회 4종을 전수 배제했다 — `state`로 주소 얻기(구조적 불가) · `exec` 결과 문자열(`List`가 `OK`만 반환) · `server/tools/` 예외 증설(운영 유틸용이며 기능을 유틸로 위장하는 것) · 응답기 확장(`console/lua` PRESERVE + 페이로드 예산 악화).

**따라서 `spec.md` §C에 조건부 예외를 순수 추가 4지점으로 한정해 명시하고, 승인 절차를 `plan.md`의 사용자 접점에 두었다. 승인 전에는 M1에 착수하지 않는다.**

> **SONGCUE의 실수를 반복하지 않았다.** 그 SPEC에서는 오케스트레이터가 정본 PRESERVE를 읽지 않고 워커에게 잠긴 파일 변경을 지시했고 **발견자가 워커**였다. 본 SPEC은 **착수 전에 발견해 문서에 적었다.**

### 재사용 계약

`server/prechk/`(신규)는 `server.bridge`를 import하지 않는다. 라벨 재사용은 `server/looks/report.py`의 **공개 접근자**를 통하며 밑줄 식별자를 직접 import하지 않는다. 검증은 raw 텍스트 grep이 아니라 **AST 식별자 스캔**이며 동형 구현이 이미 저장소에 있다(`server/tests/test_busking_tool.py` · `server/tests/test_looks_tool.py`).

### plan-phase 실행 형태 — 병렬은 계약이 닫힌 뒤에만

| 국면 | 형태 | 근거 |
|---|---|---|
| 조사 | **병렬 scout 4개** | 읽기 전용이고 콘솔을 쓰지 않아 충돌이 없다. 실제 폭 4 |
| 정본 3종(`research`·`spec`·`acceptance`) | **코디네이터 단독 · 순차** | 6문서는 독립 슬라이스가 아니라 한 설계의 투영이며 상호 정합성을 감사가 검사한다. SONGCUE가 감사 2회전에서 받은 지적 34건의 대부분이 문서 간 드리프트였고, 6개 에이전트에 뿌리면 그 드리프트를 **보장**하는 셈이다 |
| `design.md` + `plan.md` | **병렬 2** | 정본 3종이 닫혀 **계약이 고정된 뒤**에만 정당하다. 계약(REQ 20 · AC 17 · M0~M8 · ASSUMPTION 25~30 · PRESERVE)을 `CONTRACT.md`로 양쪽에 명시 배포하고 코디네이터가 전수 검증했다 |
| `progress.md` | **코디네이터 단독** | 계수·신호가 5문서 실측에서 나온다 |
| plan-audit | **독립 감사 1** | 작성자가 아닌 주체가 채점한다 |

### 감독 실패 1건 — 기록해 둔다

`plan.md` 워커의 **첫 디스패치가 죽었다.** Codex CLI가 자동 업데이트를 실행하고 TUI가 셸로 빠져나갔다(`Update ran successfully! Please restart Codex`). **메시지 0건**이라는 비대칭이 이미 신호였으나(design 워커는 메시지를 보냈다) task 상태 `dispatched`만 보고 롤링 대기를 12회전 계속해 약 24분을 낭비했다. `terminal show` 프리뷰로 원인을 특정하고 터미널을 재생성해 재디스패치했다.

**교훈**: task 상태와 메시지만으로는 죽은 워커를 구별할 수 없다. 이후 감독은 **터미널 활동(alive)과 산출 파일 크기**를 함께 본다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-29
spec_version: "0.1.0"
base_sha: 95687a0
head_sha: ce8cbb6
baseline_measured: "2490 passed · 5 skipped · 0 failed (착수 SHA에서 직접 실측, 이월 인용 아님)"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
artifact_lines: "research 369 · design 338 · acceptance 329 · plan 291 · spec 165"
requirements: 20           # REQ-PRECHK-001~020 — spec.md 정의 20 = 고유 토큰 20
acceptance_criteria: 17    # AC-PRECHK-001~017 — acceptance.md 절 제목 17 = 고유 토큰 17
milestones: 9              # M0~M8. M0·M8만 cycle_type=none (측정 세션, 코드 변경 0)
assumptions_open: 6        # ASSUMPTION-25~30 — 전부 M0 라이브 측정 대상
live_sessions_planned: 2   # M0 프로브(AC-PRECHK-016) + M8 종단(AC-PRECHK-017)
decisions_closed: 7        # plan.md 결정 등록부 A~G
decisions_open: 0
design_slots_closed: 5     # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
machine_gates:
  requirements_counted: "20 — spec.md 정의 20 = 고유 토큰 20"
  req_to_ac_coverage: "20/20 — acceptance.md 역추적표 REQ 행 20, 커버 누락 0"
  acceptance_criteria_counted: "17 — acceptance.md 절 제목 17 = 고유 토큰 17"
  ac_milestone_assignment: "17 — M0 1 · M1 1 · M2 4 · M3 5 · M4 2 · M5 1 · M6 1 · M7 1 · M8 1. 중복 0 · 누락 0. plan.md 마일스톤별 AC 줄과 1:1 대조 완료"
  ac_absent_from_traceability_table: "3 — AC-PRECHK-015(형상 전체) · AC-PRECHK-016(전제 판정) · AC-PRECHK-017(종단 통합). acceptance.md가 의도로 명시"
  abbreviated_tokens_all_artifacts: 0     # 정규식 [^A-Z-](AC|REQ)-[0-9]{3} — 5문서 합 0
  clarification_markers_all_artifacts: 0  # 미해결 표시어 3종(대문자 약어) 대소문자 무관 검색 — 5문서 합 0
  own_ssot_line_anchors: 0                # 본 SPEC의 spec.md·acceptance.md를 줄번호로 인용한 곳 0. 발견된 14건은 전부 타 SPEC 아티팩트(LOOKLIB·DASHUI·BUSKWIZ·SONGCUE)이며 규약이 허용한다
  design_citation_coordinates: "29 — 전 좌표 파일 존재 · 줄 범위 내 확인"
  cycle_type_correctness: "M0·M8 = none(코드 변경 0), M1~M7 = tdd. plan.md 헤딩 전수 확인"
  mutations_proposed: 35    # design.md §6.3 — 각 뮤테이션이 어느 AC를 죽이는지 명시
preflight_probe:
  showfile_writes: 0        # 사전 프로브는 전량 읽기 전용. 쇼파일 무변경
  fixtures_read: "19개 중 18 — childCount 19이고 반환 18이다. FID · Patch · FixtureType · Mode를 관측된 18개에서 읽었다. 전수가 아니다"
  address_scheme: "'<유니버스>.<주소>' — 1.001~1.437(유니버스 1), 2.001~2.351(유니버스 2)"
  rig_verdict: "**관측된 18개 범위에서** 주소 중복 0 · FID 중복 0. 19번째가 미관측이므로 정합성을 단정하지 않는다 — 그 단정은 REQ-PRECHK-010이 금지하는 형태다(research.md §4.8). 탐지 로직 검증에는 결함 심은 인메모리 픽스처가 필수(design.md §6.1)"
  traps_found: 3            # ok=true인 함수 참조 · 공백 프로퍼티명 거부 · 프로퍼티명 열거 불가
  truncation_observed: "childCount 19 / 반환 18 / truncated=true. 원인은 페이로드 예산(1900B)이며 자식 수 상한(24)이 아니다. 조사가 최초에 반환 18을 총수로 오독했고 최종 검증에서 잡았다 — research.md §4.8"
blocking_for_run: "**승인 2건은 2026-07-29에 확보되었다**(§F 사용자 접점 표) — `server/safety/**` 조건부 예외 승인 + M0 라이브 세션 접근 가능성(실측 확인: onPC PID 38963 · 응답기 v1.5.0 · roundtrip 3/3 PASS). 따라서 착수 차단은 **해소되었다.** 남은 기술적 블로킹은 `ASSUMPTION-26`(매크로 저작 문법, 등급 T3) **1건뿐**이고 그것도 부정이면 M4가 DESCOPE로 완료된다 — 저작 차단이 아니다. `ASSUMPTION-27`은 동작 축소, `ASSUMPTION-28/29/30`은 BUSKWIZ 후속 측정이라 본 SPEC의 어느 마일스톤도 막지 않는다. **승인의 집행 범위는 순수 추가 4지점으로 한정되며 우회 4종은 승인 후에도 금지다**(§F). 절차적 제약 1건: **M0 이전에 M1에 착수하지 않는다** — M0가 `REOPEN_SCOPE`를 내면 범위 재개정이 선행한다."
known_gaps:
  - "`FID` 값의 의미는 어떤 라이브 세션도 현재 쇼파일로 닫을 수 없다 — 슬롯 == FID이기 때문이다(`console/lua/PROTOCOL.md:322-324`). 슬롯 ≠ FID로 패치된 쇼파일이 선행 조건이며 사용자 GUI 작업이다. 본 SPEC은 FID를 판정 근거에서 배제한 형상으로 출하한다."
  - "절단 복구 경로의 인덱스 정의역을 모른다 — 풀이 희소할 수 있고(SONGCUE가 시퀀스에서 실측) 절단된 목록은 어느 슬롯이 존재하는지 알려주지 않는다. design.md 슬롯 A가 경계 있는 범위 탐색으로 결정하고 `index_domain_unknown`을 스키마에 두어 숨기지 않는다."
  - "매크로 저작 문법은 등급 T3이며 라이브 `OK` 0건이다. M0의 생성 프로브만이 판정할 수 있다 — 부정 프로브로는 갈리지 않는다(날조 키워드도 `Illegal object`를 준다)."
  - "라이브 원문 로그와 scout 산출물이 `.moai/state/`(`.gitignore:206`) 아래에만 있다. 커밋되는 사본은 `research.md`와 본 문서이며 그래서 커맨드·응답 문자열을 요약 없이 전재했다."
  - "plan-audit 1회차는 **FAIL 0.76**을 냈고 지적 11건(P1 4 · P2 6 · P3 1)을 **전건 닫았다**(§E.1a). 계수는 불변이다. **다만 감사가 재검증하지 않았다** — 1회차 정정이 새 불일치를 만들지 않았다는 증명은 없고 run-phase 각 마일스톤의 착수 직전 실측이 덮는다. 2회차를 열지 않은 근거는 §E.1a에 있다."
  - "감사의 축약 토큰 검출이 코디네이터의 정규식보다 정확했다 — 완전 토큰 뒤에 중점으로 이어 붙인 **3자리 숫자만의 항목**은 슬러그도 `AC-` 접두도 없어 코디네이터가 쓴 패턴에 걸리지 않는다. 이후 게이트는 **중점 뒤 3자리 숫자**도 함께 센다."
  - "M0 결과 어휘 4값(`GO` · `NEGATIVE` · `CONDITION_NOT_MET` · `REOPEN_SCOPE`)과 접두 행 4종은 **감사 지적으로 신설된 것이며 아직 라이브에서 쓰인 적이 없다.** M0가 그 형식을 실제로 산출하는지는 착수 시 확인된다."
  - "**조사가 스스로 절단 함정에 빠졌다가 최종 검증에서 잡았다**(`research.md` §4.8). 최초 프로브가 `len(children)` = 18만 출력하고 `node.childCount` = 19를 출력하지 않아 **반환 수를 총수로 기록**했고, 그 위에 *'정합한 리그'*라는 단정을 얹었다 — `REQ-PRECHK-010`이 금지하는 바로 그 형태다. 픽스처 수 서술과 정합 판정을 5개 절에서 한정 표현으로 정정했다. **이 오류가 `REQ-PRECHK-004`의 개수 비교가 이론적 방어가 아님을 실증한다** — `truncated` 플래그가 참이었는데도 오독을 막지 못했고, 플래그는 '얼마나 불완전한지'를 말하지 않는다. 미관측 1개는 M0가 슬롯별 보강 조회로 채운다."
next: "**Kickoff 접점 2건 승인 완료 · §F 작성 완료**(첫 run-phase 스폰 전 요건 충족). 다음은 **run-phase 착수 — M0 라이브 프로브부터**다. M0는 `cycle_type=none`(코드 변경 0)이며 `ASSUMPTION-25`~`ASSUMPTION-30` 6건에 결과 어휘 4값 중 하나를 배정하고 접두 행 4종(`GO:` · `DESCOPE:` · `SKIP:` · `REOPEN:`, 합 6행)으로 기록한다. **미관측 픽스처 1개(19번째)를 슬롯별 보강 조회로 채운다**(`research.md` §4.8). 쇼파일은 원상 복구하고 재조회로 확인한다. 그 뒤 M1(승인된 4지점만) → M2 → M3 → M4 → M5 → M6 → M7 → M8. plan-audit는 1회차 FAIL 0.76 → 11건 전건 처리로 종료하고 2회차를 열지 않는다."
```

## §E.1a Plan-audit 결과

### 1회차 — FAIL 0.76 → 지적 11건 전건 처리 (2026-07-29)

독립 감사자(작성자가 아닌 주체)가 5문서를 채점했다. `progress.md`는 작성 병행 중이어서 감사 대상에서 제외됐다. 원문은 `.moai/state/verify/prechk-scout/AUDIT-1.md`이며 그 경로가 `.gitignore:206` 대상이므로 **본 절이 추적되는 사본이다.**

**Verdict: FAIL · 가중합 0.76 / 기준선 0.85.**

| 축 | 가중치 | 점수 | 감사 요지 |
|---|---:|---:|---|
| 인용 정확성 | 20% | 0.88 | 경로 없는 좌표 1건 + shorthand 13건 |
| 교차 정합 | 30% | 0.70 | 매크로 요구와 설계·AC 불일치, M0 폐쇄 의미가 문서별로 다름 |
| 요구-AC 정합 | 15% | 0.72 | `REQ-PRECHK-011` · `REQ-PRECHK-017`의 실제 검증이 약함 |
| AC 기계검증성 | 15% | 0.68 | **M0 GO 판정의 기계 판독 형식이 없음** + 비공허성 누락 3건 |
| 증거 등급 규율 | 10% | 0.82 | 정적 파일시스템 사실을 `[실측]`으로 표기 |
| 범위 경계 | 5% | 0.82 | 초크포인트 승인 게이트는 일관되나 매크로 범위가 요구와 다름 |
| 미결 은닉 | 5% | 0.72 | 조건부 미측정을 "전부 판정 확정"으로 셈 |

**감사가 재현해 정확하다고 확인한 계수**: REQ 정의 20 · 고유 20 · AC 절 17 · 고유 17 · 역추적표 REQ 행 20 · 마일스톤 9 · 마일스톤별 AC 배정 합 17(중복 0 · 누락 0) · `ASSUMPTION-25`~`ASSUMPTION-30` 6 · clarification 마커 0 · 결정 등록부 열린 0 · 설계 슬롯 열린 0 · scout 산출물 586행. **명시적 `파일:줄` 인용 126발생 / 62고유 중 내용 불일치 1건.**

#### 지적 11건 처리 표 — 전건 닫았다

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| **P1-1** | P1 | `REQ-PRECHK-011`이 *"픽스처를 하나씩"* 점등을 요구하는데 설계·AC는 **그룹 대상**으로 고정 — 요구가 검증되지 않는다 | **닫힘** — 요구를 **그룹 기반으로 낮췄다.** 픽스처 개별 선택은 FID를 요구하고 그것은 `REQ-PRECHK-005`가 배제했으므로 **강제된 축소**다. 그 강제성을 요구 본문에 적고, 검증 가능한 형상(그룹 1개당 점등·소등 1쌍, 그룹 수 × 2 = 쌍 수)을 `AC-PRECHK-010` ④로 신설 |
| **P1-2** | P1 | M0 폐쇄 의미가 문서 간 불일치 — 조건부 미측정을 "판정 확정"으로 셈. `ASSUMPTION-25`의 차단 대상도 문서마다 다름 | **닫힘** — **닫힌 결과 어휘 4값을 신설**(`GO` · `NEGATIVE` · `CONDITION_NOT_MET` · `REOPEN_SCOPE`)하고 각각의 DoD 인정 여부를 표로 고정. *"6건 전부 판정 확정"*이 `GO` 6건이 아니라 **4값 중 하나 배정**임을 명시 |
| **P1-3** | P1 | **M0 GO 판정의 기계 판독 형식이 없다** — `AC-PRECHK-010` ①이 비교할 정본 데이터를 갖지 못한다 | **닫힘** — `GO: ASSUMPTION-nn literal=… effect=…` **접두 행을 신설**하고 `SKIP:` · `REOPEN:`도 함께 정의. **네 접두어 합이 6행**이라는 기계 판정을 만들었다. `AC-PRECHK-010` ①이 `literal=`을 파싱해 대조하며 **그 행이 없으면 GO 구간을 통과시키지 않는다** |
| **P1-4** | P1 | 정본 마일스톤 표(§C.0a)가 축약 토큰 8건 사용 — 자기 규약 위반 | **닫힘** — 전량 완전형으로 전개 |
| **P2-1** | P2 | 한국어 요구가 기계검증되지 않음 | **닫힘** — `AC-PRECHK-012` ⑤ 신설: 어휘 집합과 라벨 표 키 집합의 **정확한 일치** · `summary_ko` 비공백 · 라벨이 표에서 오는지 AST 확인 · **어휘 밖 값의 조용한 통과 금지** |
| **P2-2** | P2 | 절단 보강 조회와 *"complete로 승격하지 않음"*이 핵심 설계인데 AC가 없다 | **닫힘** — `AC-PRECHK-003` ④⑤ 신설: 보강 후에도 불완전 유지 · `recovery_boundary`·`index_domain_unknown` 노출 · `observed + still_unobserved == child_count` 산술 닫힘 |
| **P2-3** | P2 | "0건" 판정 3곳에 비공허성 assert 누락 | **닫힘** — `AC-PRECHK-001` ③(화이트리스트 길이 ≥ 1 + 공백 이름 주입 시 실패 확인) · `AC-PRECHK-011` ①②(커맨드 목록·페이로드 필수 키 존재) · `AC-PRECHK-013` ①(스캔 방문 파일 수·import 노드 수 ≥ 1) |
| **P2-4** | P2 | `ASSUMPTION-25`의 톤이 문서마다 다르고 spec이 판정을 선점 | **닫힘** — P1-2의 결과 어휘가 이것을 흡수한다. 부정 시 `REOPEN_SCOPE`이며 **폐쇄 아님**으로 정의되어 세 문서가 같은 게이트 효과를 갖는다 |
| **P2-5** | P2 | `server/showfile/` 부재라는 **저장소 파일시스템 사실**을 `[실측]`으로 표기 — 규약은 `[실측]`을 라이브 콘솔 관측으로 제한 | **닫힘** — `[코드]`(저장소 정적 조사 — 라이브 실측이 아니다)로 교정 |
| **P2-6** | P2 | **`AC-PRECHK-003` ②의 근거가 코드와 맞지 않는다** — 두 절단 경로가 **둘 다** `truncated = true`를 세우므로 "플래그 하나로는 원인을 놓친다"는 설명이 성립하지 않는다 | **닫힘** — 지적이 옳다. 근거를 정정했다: 개수 비교가 필요한 이유는 (a) **못 읽은 개수 산출**(플래그는 그것을 주지 않는다) (b) 플래그 누락·오염에 대한 **방어적 검증**이며, 그 테스트는 (b)를 고정하는 뮤테이션이다 |
| **P3-1** | P3 | 경로 없는 좌표 1건 + shorthand 13건 | **닫힘** — shorthand **16건**을 full 좌표로 전개(`progress.md` 5건 포함). `tools.py:33-36`은 **LOOKLIB 원문 인용 내부**로 한정하고 본 SPEC의 직접 좌표를 분리 명시 |

#### 처리 후 게이트 재측정

| 게이트 | 값 |
|---|---|
| 축약 토큰(**감사 검출 방식** — 중점 뒤 3자리 + 슬러그 없는 토큰) | **0** |
| clarification 마커 | **0** |
| shorthand 좌표 | **0** |
| 경로 없는 좌표 | **1 — LOOKLIB 원문 인용 내부로 한정, 의도** |
| M0 결과 접두어 정의 | **4종**(`GO:` · `DESCOPE:` · `SKIP:` · `REOPEN:`) |

> **감사의 검출이 코디네이터의 게이트보다 정확했다.** P1-4의 축약 토큰 8건은 코디네이터가 쓴 정규식(`[^A-Z-](AC|REQ)-[0-9]{3}`)으로는 **0건으로 나왔다** — 완전 토큰 하나를 적고 중점으로 **3자리 숫자만** 이어 붙인 항목은 `AC-` 접두가 없어 그 패턴에 걸리지 않는다. 재측정에는 감사의 검출 방식(중점 뒤 3자리 숫자)을 채택했다.

**2회차를 열지 않고 사용자 Kickoff 접점으로 진행한다** — 11건을 닫으면서 새 요구·AC·마일스톤·`ASSUMPTION`을 만들지 않았고 계수가 불변이다(REQ 20 · AC 17 · M0~M8 · `ASSUMPTION-25`~`ASSUMPTION-30`). P1 4건은 전부 **기계검증성과 문서 정합** 층이다. **다만 감사가 재검증하지 않은 상태를 기록한다** — 1회차 정정이 새 불일치를 만들지 않았다는 증명은 없으며, run-phase 각 마일스톤의 착수 직전 실측이 그것을 덮는다.

#### 감사 자신이 적은 한계

라이브 콘솔에 접속하지 않았으므로 **`research.md`의 `[실측]` 표 원문을 재현 검증하지 못했다.** `progress.md`는 대상 외였다. 대형 인용 범위는 시작·끝과 핵심 심볼만 열었다.

## §E.2 Run-phase Evidence

### M0 — 라이브 프로브 (AC-PRECHK-016 · cycle_type=none · 2026-07-30)

`.moai/state/`는 `.gitignore:206` 대상이므로 커밋되지 않는다. **본 절이 M0의 추적되는 정본이며 실측 원문을 요약 없이 전재한다.**

#### 세션 조건 — 착수 직전 직접 측정 (조사 문서 값을 이월하지 않았다)

| 항목 | 측정값 |
|---|---|
| 응답기 | `version=1.5.0` · `plugin=CopilotResponder` |
| OSC | send 8000 / receive 9005 (기본 9000 아님) |
| `responder_roundtrip --expect-version 1.5.0` | ping · state · exec **3/3 PASS** |
| 코드 baseline | `uv run pytest server/tests/ -q` → **2490 passed · 5 skipped · 0 failed** |
| 저장소 diff | `git status --short` **빈 출력** — 코드 변경 0건 |

쇼파일 착수 baseline: `DataPool/Sequences` childCount 17 인덱스 `[1,2,11,12,13,14,15,16,17,20,30,41,50,62,71,80,90]` · `DataPool/Timecodes` childCount 0 · `Patch/Stages/1/Fixtures` **childCount 19 / 반환 18 / truncated true** · `DataPool/Groups` childCount 4 인덱스 `[1,11,12,13]` · `DataPool/Macros` childCount 1 (`Copilot Go`) · `DataPool/Pages` childCount 1 (`Page 1`) · `DataPool/Pages/1` childCount 9 자식 `['Sequence 50','Sequence 17','Sequence 30','Sequence 41','Sequence 80','Sequence 14','Sequence 16','Sequence 62','Ballad Yellow Red']`.

#### 판정 — 접두 행 합 6행, 한 `ASSUMPTION`이 두 행을 갖지 않는다

```
GO: ASSUMPTION-25 literal=prop Patch/Stages/1/Fixtures/<slot> Patch effect=슬롯 1~19 전량에서 Patch·FixtureType·Mode·Name 76건 조회 전부 ok=true, 판독 실패 0건, 미관측 19번째를 Patch/Stages/1/Fixtures/19 단일 조회로 채워 name='MMX 19' Patch='2.401' 실측
GO: ASSUMPTION-26 literal=Store Macro 91 ; Store Macro 91.1 ; Set Macro 91.1 Property 'Command' 'On Group 11' effect=DataPool/Macros childCount 1에서 2로 증가하고 자식에 'Macro 91' 출현, DataPool/Macros/91 childCount 0에서 1로 증가해 'MacroLine 1' 출현, prop DataPool/Macros/91/1 Command 재조회 값 'On Group 11'
DESCOPE: ASSUMPTION-27 표시 문자열 파싱 없이 점유폭에 도달하는 경로가 0건이며 이 판정은 후보 전수 12건을 닫은 뒤에 내렸다. 객체 경로 순회 3종(Patch/Stages/1/Fixtures/1/FixtureType 그리고 같은 픽스처의 /Mode 와 /DMXChannels)이 전부 path segment not found이고 픽스처 노드 childCount는 0이다. 인덱스 반환 후보 프로퍼티 11종 중 판독 가능은 No(값 '1' — 슬롯이며 타입 인덱스가 아니다)와 Index(ok=true인데 값이 'function: 0x…' 형태의 Lua 함수 참조)뿐이다. 동등 조인 프로퍼티는 없다 — Patch/FixtureTypes/1 의 판독 가능 프로퍼티는 Name 'Robin MMX Spot' · ShortName 'RMMXSm1' · No '1' · Manufacturer 'Robe'이고 픽스처가 주는 'FixtureType 1'과 일치하는 값이 0건이다. 역방향 열거도 없다 — Patch/FixtureTypes/1 의 자식 8종은 전부 정의 컨테이너이고 픽스처 목록이 아니다. Patch 루트의 다른 주소공간 컨테이너도 부정이다 — DmxUniverses 와 DmxAddresses 와 RTChannels 와 UIChannels 와 FixtureTypesOverview 를 열거하고 프로퍼티까지 발화했으나 어느 노드도 픽스처 연결이나 채널 점유를 싣지 않는다. 폭 유일성 우회도 성립하지 않는다 — 모드 4의 DMXChannels childCount 가 31이고 모드 1과 2와 3의 29와 다르다. 구간 겹침 판정만 미수행이고 주소 중복 판정은 어느 분기에서도 수행된다
GO: ASSUMPTION-28 literal=Store Page 2 ; Label Page 2 'PRECHK Probe' effect=DataPool/Pages childCount 1에서 2로 증가하고 자식에 'Page 2' 출현, prop DataPool/Pages/2 Name 재조회 값 'PRECHK Probe'
GO: ASSUMPTION-29 literal=Assign Sequence 20 At Executor 103 ; Delete Executor 103 effect=열거에 부재했던 인덱스 3이 배정 뒤 DataPool/Pages/1 자식으로 출현(childCount 9에서 10)하고 삭제 뒤 다시 사라져 childCount 9로 복귀, 즉 열거 부재가 빈 익스큐터를 뜻하고 그 인덱스가 주소형 <인덱스 더하기 100>으로 도달 가능하다
DESCOPE: ASSUMPTION-30 두 연언 중 page 이상 2 일반화가 부정이므로 축이 꺼진다. Assign Preset 4.1 At Executor 202는 효과가 확인됐다(테스트 익스큐터 102의 Name이 'Ballad Yellow Red'에서 '금빛 코러스'로 재조회 변경 — BUSKWIZ G2의 파싱만 확인된 항목을 효과까지 닫았다). 그러나 page x 100 + slot의 page 이상 2는 성립하지 않는다: Assign Sequence 1 At Executor 201이 Cmd ok를 내면서 page 2가 아니라 page 1의 인덱스 101을 덮었고, Assign Sequence 1 At Executor 2.1은 Cannot Create Object이며, 생성된 page 2는 세션 종료까지 childCount 0을 유지했다
```

접두어 계수: `GO:` 4행 · `DESCOPE:` 2행 · `SKIP:` 0행 · `REOPEN:` 0행 = **합 6행.** `REOPEN_SCOPE` 0건이므로 범위 재개정 접점은 발생하지 않았고, `CONDITION_NOT_MET` 0건이므로 미측정을 폐쇄로 세는 항목도 없다.

#### `ASSUMPTION-25` 실측 원문 — 19슬롯 전량

| 슬롯 | `Name` | `Patch` | `FixtureType` | `Mode` |
|---|---|---|---|---|
| 1 | `RMMXSm1 1` | `1.001` | `FixtureType 1` | `1 Mode 1` |
| 2 | `Copilot MMX 2` | `1.101` | `FixtureType 1` | `1 Mode 1` |
| 3 | `Copilot MMX 3` | `1.143` | `FixtureType 1` | `1 Mode 1` |
| 4 | `Copilot MMX 4` | `1.185` | `FixtureType 1` | `1 Mode 1` |
| 5 | `Copilot MMX 5` | `1.227` | `FixtureType 1` | `1 Mode 1` |
| 6 | `Copilot MMX 6` | `1.269` | `FixtureType 1` | `1 Mode 1` |
| 7 | `Copilot MMX 7` | `1.311` | `FixtureType 1` | `1 Mode 1` |
| 8 | `Copilot MMX 8` | `1.353` | `FixtureType 1` | `1 Mode 1` |
| 9 | `Copilot MMX 9` | `1.395` | `FixtureType 1` | `1 Mode 1` |
| 10 | `Copilot MMX 10` | `1.437` | `FixtureType 1` | `1 Mode 1` |
| 11 | `MMX 11` | `2.001` | `FixtureType 1` | `1 Mode 1` |
| 12 | `MMX 12` | `2.051` | `FixtureType 1` | `1 Mode 1` |
| 13 | `MMX 13` | `2.101` | `FixtureType 1` | `1 Mode 1` |
| 14 | `MMX 14` | `2.151` | `FixtureType 1` | `1 Mode 1` |
| 15 | `MMX 15` | `2.201` | `FixtureType 1` | `1 Mode 1` |
| 16 | `MMX 16` | `2.251` | `FixtureType 1` | `1 Mode 1` |
| 17 | `MMX 17` | `2.301` | `FixtureType 1` | `1 Mode 1` |
| 18 | `MMX 18` | `2.351` | `FixtureType 1` | `1 Mode 1` |
| **19** | **`MMX 19`** | **`2.401`** | `FixtureType 1` | `1 Mode 1` |

**19번째가 실측으로 채워졌다.** 인덱스 정의역은 경계 있는 범위 탐색으로 닫았다 — `Patch/Stages/1/Fixtures/20`부터 `Patch/Stages/1/Fixtures/30`까지 11건이 전부 `path segment not found`이고, 관측 18 + 미관측 1 = `childCount` 19로 **산술이 닫힌다.** 단 이것은 이 쇼파일의 실측이며, `design.md` 슬롯 A의 일반 규칙(보강 조회가 completeness를 `complete`로 승격하지 않는다)은 유지된다 — 상한을 코드로 아는 것이 아니라 탐색으로 확인했기 때문이다.

#### `REQ-PRECHK-003`의 오염 사례를 라이브에서 재현했다

`prop Patch/Stages/1/Fixtures/1 Index`가 **`ok=true`와 함께 `'function: 0x105b0f048'`** 을 반환했다. 응답기의 `safe_property`가 `handle:Get(name)` 실패 뒤 `handle[name]`을 `tostring`하기 때문이다(`console/lua/copilot_responder.lua:204-217`). `ok` 참만으로 값을 채택하면 Lua 함수 참조가 판정 입력으로 들어간다. **`REQ-PRECHK-003`은 이론적 방어가 아니고 이 쇼파일에서 재현되는 실측 현상이다.** M2는 이 문자열을 판독 실패 픽스처 fixture로 쓴다.

#### `ASSUMPTION-26`의 부수 실측 — 룰북 리터럴만으로는 부족하다

`research.md` §5가 기록한 라인 추가 리터럴 `Set Macro <m>.<line> Property 'Command' '<cmd>'`를 **선행 없이 발화하면 실패한다.** 실측 순서와 결과는 이렇다.

| 순서 | 발화 | `Cmd` 접수 | 재조회 효과 |
|---|---|---|---|
| 1 | `Store Macro 91` | `OK` | `DataPool/Macros` childCount 1 → 2, `'Macro 91'` 출현 |
| 2 | `Set Macro 91.1 Property 'Command' 'On Group 11'` | **`Illegal object`** | `DataPool/Macros/91` childCount 0 유지 — 효과 0 |
| 3 | `Store Macro 91.1` | `OK` | `DataPool/Macros/91` childCount 0 → 1, `'MacroLine 1'` 출현 |
| 4 | `Set Macro 91.1 Property 'Command' 'On Group 11'` | `OK` | `prop DataPool/Macros/91/1 Command` = `'On Group 11'` |

**즉 라인 개체 생성(`Store Macro <m>.<line>`)이 프로퍼티 설정에 선행해야 한다.** 순서 2의 `Illegal object`는 "문법 없음"이 아니라 "대상 없음"이었고, `research.md` §5가 경고한 대로 **부정 프로브로는 그 둘이 갈리지 않았다** — 갈라낸 것은 생성 프로브와 재조회다. **M4는 3단계 순서를 그대로 저작해야 하며 룰북의 2리터럴만 발화하면 실패한다.**

#### `Assign … At Executor <N>` 의 주소 기전 — 안전 관련 실측

발화 5건의 관측을 모으면 기전이 하나로 정해진다: **`N`은 page 1 익스큐터 인덱스 `N` 빼기 100으로 해석된다.**

| 발화 | `Cmd` 접수 | 관측된 대상 | 효과 |
|---|---|---|---|
| `Assign Sequence 1 At Executor 201` | `OK` | page 1 인덱스 101 | 기존 `'Ballad Yellow Red'`를 `'Default'`로 **덮어씀** |
| `Assign Sequence 1 At Executor 2.1` | `Cannot Create Object` | 없음 | 효과 0 |
| `Assign Sequence 20 At Executor 202` | `OK` | page 1 인덱스 102 | 부재 인덱스에 **신규 생성** |
| `Assign Sequence 20 At Executor 195` | `OK` | page 1 인덱스 95 | 기존 `'Sequence 62'`를 덮어씀 |
| `Assign Sequence 20 At Executor 103` | `OK` | page 1 인덱스 3 | 부재 인덱스에 신규 생성 |
| `Assign Sequence 20 At Executor 1` · `Assign Sequence 20 At Executor 3` | `Cannot Create Object` | 없음 | 효과 0 (`N` 빼기 100이 1보다 작다) |

`N`이 101부터 200까지면 `page x 100 + slot` 공식이 page 1에서 정확히 성립한다(인덱스 = `slot`). **그러나 `N`이 201 이상이면 page 성분이 존중되지 않고 page 1의 인덱스 공간으로 누출된다** — `Executor 201`은 page 2가 아니라 page 1 인덱스 101을 조용히 덮었다. 생성된 page 2는 선택(`Page 2` 발화 `OK`) 뒤에도 어떤 익스큐터도 받지 못하고 childCount 0을 유지했다. **이것이 `ASSUMPTION-30`을 부정으로 만든 근거이며, 동시에 `Cmd` 접수 `OK`가 의도한 대상에 닿았음을 뜻하지 않는다는 실측 사례다** — 슬롯을 FID로 오인해 엉뚱한 리그를 조용히 선택하는 형태(`console/lua/PROTOCOL.md:305-324`)와 같은 계열의 위험이다.

#### 정리 기록 — 프로브가 남긴 것, 그 무해성, 원상 복구 증거

생성 프로브가 쇼파일을 5지점 변경했고 **전건 복구했다.**

| # | 변경 | 복구 발화 | 복구 후 재조회 |
|---|---|---|---|
| 1 | `Macro 91` 신규 + `MacroLine 1` | `Delete Macro 91` | `DataPool/Macros` childCount 1 · 자식 `['Copilot Go']` |
| 2 | `Page 2` 신규(라벨 `PRECHK Probe`) | `Delete Page 2` | `DataPool/Pages` childCount 1 · 자식 `['Page 1']` |
| 3 | page 1 인덱스 101이 `'Ballad Yellow Red'`에서 `'Default'`로 변경 | `Assign Sequence 20 At Executor 201` — **관측된 매핑을 그대로 역전시켰고 새 주소형을 도입하지 않았다** | 인덱스 101 = `'Ballad Yellow Red'` |
| 4 | page 1 인덱스 95가 `'Sequence 62'`에서 `'Ballad Yellow Red'`로 변경 | `Assign Sequence 62 At Executor 195` | 인덱스 95 = `'Sequence 62'` |
| 5 | page 1 인덱스 102·인덱스 3 신규 생성 | `Delete Executor 202` · `Delete Executor 103` | 두 인덱스 모두 자식 목록에서 사라짐 |

부수로 선택 페이지를 `Page 2`로 옮겼고 `Page 1` 발화로 되돌렸다(쇼파일 내용이 아니라 세션 선택 상태다).

**최종 대조 — 착수 baseline 전항 일치:**

```
응답기 1.5.0 CopilotResponder
DataPool/Sequences        childCount=17 인덱스 일치 truncated=false
DataPool/Timecodes        childCount=0  인덱스 일치 truncated=false
Patch/Stages/1/Fixtures   childCount=19 반환 18 truncated=true  (baseline과 동일)
DataPool/Groups           childCount=4  인덱스 일치 truncated=false
DataPool/Macros           childCount=1  자식 ['Copilot Go']
DataPool/Pages            childCount=1  자식 ['Page 1']
DataPool/Pages/1          childCount=9  자식 ['Sequence 50','Sequence 17','Sequence 30','Sequence 41','Sequence 80','Sequence 14','Sequence 16','Sequence 62','Ballad Yellow Red']
```

**잔여물 0건.** 조건부 접점(`ASSUMPTION-28` GO 이후 테스트 오브젝트 잔여 시 복구 증거 공유)은 잔여가 0이므로 위 표가 그 증거다.

#### `ASSUMPTION-27` 후보 전수 12건 — 판정 전에 닫았다

최초 발화는 순회 3종과 인덱스 프로퍼티 11종만 닫은 상태였고, 그 부분집합 위에 부정을 단정한 것은 `REQ-PRECHK-010`이 금지하는 형태였다. 독립 scout가 후보를 전수 12건으로 열거하고 그중 5건이 라이브 검증 대상임을 지적했으므로 같은 세션에서 나머지를 발화해 닫았다. **불완전한 후보 집합 위의 판정을 정정한 기록이다.**

| 후보 | 내용 | 닫힌 방법 | 결과 |
|---|---|---|---|
| C-1 · C-2 · C-3 | 픽스처 노드 하위 도달 | 라이브 순회 3종 + 픽스처 childCount 0 | 부정 |
| C-4 | 이름 키 경로 도달 수단 | 도달 수단일 뿐 조인 키가 아니다 | 해당 없음 |
| C-5 | 동등 조인 프로퍼티 | `Patch/FixtureTypes/1`의 판독 가능 프로퍼티 전수 발화 — `Name` `'Robin MMX Spot'` · `ShortName` `'RMMXSm1'` · `No` `'1'` · `Manufacturer` `'Robe'`. 픽스처의 `'FixtureType 1'`과 일치 0건 | 부정 |
| C-6 | 직접 인덱스 프로퍼티 | 후보 11종 발화 — 판독 가능은 `No`(슬롯)와 `Index`(함수 참조) | 부정 |
| C-7 | 타입에서 픽스처로 역방향 열거 | `Patch/FixtureTypes/1` 자식 8종 = `['AttributeDefinitions','Wheels','PhysicalDescriptions','Models','Geometries','DMXModes','Revisions','Protocols']` — 픽스처 목록 없음 | 부정 |
| C-8 | `Patch` 루트의 다른 주소공간 컨테이너 | 루트 자식 14종 전량 열거 후 `DmxUniverses`(childCount 1024) · `DmxAddresses` · `RTChannels` · `UIChannels` · `FixtureTypesOverview`를 하위까지 발화. `Patch/DmxUniverses/1`은 자식 1개(`'DMX 2'`)이고 그 노드는 `Name`과 `No`만 판독되며 `Fixture` · `Patch` · `Address` · `Universe`가 전부 판독 불가 | 부정 |
| C-9 | 폭 유일성 우회 | 모드 4종의 `DMXChannels` childCount = 29 · 29 · 29 · **31** — 폭이 유일하지 않다 | 부정 |
| C-10 · C-11 · C-12 | 저장소 정적 조사로 이미 닫힘 | scout 산출 | 부정 |

**후보 0건이 아니라 후보 12건 전건 부정이다.** 이 구별이 중요하다 — 후속 SPEC이 다른 쇼파일에서 재측정할 때 무엇을 이미 시도했는지 알 수 있다.

부수 실측 2건: `Patch` 루트 자식 14종은 `['DmxCurves','AttributeDefinitions','Layers','Classes','PsrExtraData','FixtureTypes','Stages','UIChannels','RTChannels','IDTypes','DmxUniverses','DmxAddresses','FixtureTypesOverview','PatchFilter']`다. 그리고 `DMXChannels` 열거는 `truncated=true`인데 `childCount`가 참값 29 또는 31을 준다 — 절단과 계수 정확성의 비대칭이 픽스처 풀 밖에서도 성립한다는 확인이다.

#### 독립 scout 지적에 대한 처리 — 5건

M0 실행과 병행한 읽기 전용 scout 4개가 정본 드리프트와 판정 함정을 지적했다. 처리 결과를 남긴다.

| # | 지적 | 처리 |
|---|---|---|
| 1 | `design.md` 슬롯 A는 보강 조회 경계를 `1..node.childCount` 하드 캡으로 못박았으나 `console/lua/PROTOCOL.md:172-174`는 상한 없는 정지 규칙이고 예시 리터럴이 27개 풀의 슬롯 150이다. 희소 풀에서 캡은 과소복구한다 | **이월.** 이 쇼파일에서는 19번째가 슬롯 19에서 잡혀 캡(19)이 충분했고 캡 밖 20부터 30까지 11건도 발화해 전부 부재를 확인했다. 즉 이번엔 두 규정이 같은 답을 준다. 그러나 **희소 풀에서 캡이 과소복구한다는 판정 자체는 유효**하므로 아래 이월 항목에 넣는다 |
| 2 | 슬롯 값이 `probe_slots` 분기에서 왔는지 `slot_confirms` 분기에서 왔는지 조밀 풀에서는 가릴 수 없다 | **닫혔다 — 같은 세션의 다른 풀이 갭 풀이었다.** 처음엔 열린 채로 기록했으나 scout가 내 로그를 재검토해 `DataPool/Pages/1`의 자식 `i`가 `[1, 2, 5, 11, 91, 92, 93, 95, 101]`로 **희소**임을 지적했다. 판별자(`console/lua/PROTOCOL.md:289-291`)가 그 형태를 분기 (a) 작동으로 규정하고, 위치 승격 경로는 구조적으로 연속값만 낸다(`console/lua/copilot_responder.lua:391-393`). 판별용 갭 풀을 따로 만들 필요가 없었다 — 이미 찍혀 있었다. 아래 부수 실측 3에 전개한다 |
| 3 | `completeness=incomplete`와 19슬롯 전량 관측을 한 문장에 넣으면 독자가 `AC-PRECHK-003` ④가 반증됐다고 읽는다 | **분리 서술 채택.** 전자는 열거 **실행**의 성질(루트가 절단됐고 인덱스 정의역 상한이 코드로 닫히지 않는다)이고 후자는 이 세션의 사실이다. `AC-PRECHK-003` ④는 유효하며 M0가 그것을 반증하지 않았다 |
| 4 | `design.md` §6.1과 `acceptance.md` `AC-PRECHK-009`의 `clean_rig_18`이 *"실측 리그와 같은 정합 주소"*를 주장하는데 실측 리그는 19개가 됐다 | **결정: 합성 픽스처이며 라이브 미러가 아니다.** 확장하지 않는다. 인메모리 픽스처를 현장 쇼파일에 묶으면 리그가 바뀔 때마다 테스트가 깨지고 결정성이 사라진다. M2는 `clean_rig_18`을 **의도적 합성 리그**로 쓰고, 라이브 19슬롯 표는 본 절의 실측 기록으로만 쓴다 |
| 5 | `Index`의 포인터 값 `0x105b0f048`이 사전 프로브와 동일 주소로 재현됐다 — 주소를 하드코딩하는 유혹이 생긴다 | **판별자 규칙 고정.** M2 형태검증기의 판별자는 **`function: 0x` 접두사**이며 특정 주소가 아니다. 동일 재현은 Lua 런타임에서 함수 객체가 안정적이라는 뜻일 뿐이고 판정 근거가 아니다 |

scout가 정적으로 예측한 것 1건이 라이브와 일치했다 — **`page × 100 + slot`은 페이지 축을 넘으면 단사가 아니다**: page 1 슬롯 101과 page 2 슬롯 1이 둘 다 `201`로 사상된다. 내 관측(`Executor 201`이 page 1 인덱스 101을 덮음)은 그 충돌의 실측 재현이며, `N` 빼기 100이라는 서술보다 **비단사 사상**이라는 서술이 기전을 정확히 말한다.

#### 측정하지 못한 것

1. **`FID` 의미.** 이 쇼파일은 슬롯과 `FID`가 같아 어떤 라이브 세션도 닫을 수 없다(`console/lua/PROTOCOL.md:322-324`). 본 SPEC은 `FID`를 판정 근거에서 배제한 형상으로 출하한다. 별도 쇼파일 준비가 선행 조건이다.
2. **익스큐터 인덱스 정의역의 상한.** 인덱스 3과 인덱스 102가 배정 가능함은 실측했으나 유효 인덱스의 상한은 모른다. 픽스처 슬롯과 같은 `index_domain_unknown` 계열이다.
3. **`Executor 201`이 page 1 인덱스 101에 닿은 기전의 내부 이유.** 관측은 비단사 사상으로 일관되지만 MA3 내부에서 page 성분이 어떻게 인덱스 공간으로 접히는지는 응답기 밖의 일이라 관측 경로가 없다.
4. **무응답 픽스처.** 패치 메타데이터에는 응답 여부가 없다. 사용자가 이미 범위에서 제외했다.
5. **픽스처 인덱스 정의역의 *일반* 상한.** 이 쇼파일에서는 1부터 19까지로 닫혔다(아래 부수 실측 3 참조). 그러나 임의의 쇼파일에서 상한을 코드로 아는 방법은 여전히 없다 — `design.md` 슬롯 A의 `index_domain_unknown`은 유지된다.
6. **희소 풀에서의 보강 조회 경계.** `design.md` 슬롯 A의 `1..node.childCount` 하드 캡은 이 조밀 풀에서는 충분했으나 **희소 풀에서는 과소복구한다** — `console/lua/PROTOCOL.md:172-174`의 정지 규칙은 상한이 없고 예시 리터럴이 27개 풀의 슬롯 150이다. 본 SPEC은 캡으로 출하하고, 희소 픽스처 풀을 가진 쇼파일이 나오면 그 경계 서술을 개정해야 한다. **이것이 실측으로 확인된 잠재 미명세이며 이번 쇼파일이 조밀했을 뿐이다.**

#### 후속 SPEC에 넘기는 신규 실측 3건

1. **`DataPool/PresetPools`가 살아 있다** — childCount 14, 자식 `['Dimmer','Position','Gobo','Color','Beam','Focus','Control','Shapers','Video','All 1','All 2','All 3','All 4','All 5']`이고 `truncated=false`. 각 풀은 `class='Presets'`이며 `DataPool/PresetPools/1`과 `DataPool/PresetPools/4`가 각각 childCount 7로 LOOKLIB 산출물(`['금빛 코러스','벌스 사이드','프리코러스 빌드','리프 그린','코러스 히트','화이트 슬램','마지막 폭발']`)을 담고 있다. **`DataPool/Presets`와 `DataPool/AllPresets`는 `path segment not found`** 로 `REQ-PRECHK-002`의 사망 판정을 재확인했다 — 즉 프리셋의 살아 있는 경로는 `DataPool/PresetPools/<풀>`이다. 본 SPEC의 범위 밖이지만 프리셋을 읽는 후속 SPEC이 추측으로 경로를 고르지 않도록 기록한다.
2. **`DataPool` 최상위 자식 16종** — `['Worlds','Filters','GeneratorTypes','PresetPools','Groups','Sequences','Plugins','Quickeys','MAtricks','Configurations','Pages','Layouts','Timecodes','Timers','Shapes']`에 `Macros`를 포함한 16개이고 `truncated=false`. 경로 추측을 대체하는 열거 근거다.
3. **`ASSUMPTION-7`(자식 풀 슬롯)이 2.4.2에서 분기 (a)로 충족됨이 실측됐다.** `DataPool/Pages/1` 열거가 자식 `i`를 `[1, 2, 5, 11, 91, 92, 93, 95, 101]`로 냈다 — **희소이며 번호 없는 항목이 0건**이다. `console/lua/PROTOCOL.md:289-291`의 판별자가 정확히 이 형태를 규정한다(`1,5,7` = (a) 작동 · `1` 더하기 번호 없는 항목 = (b) 전용 · `1,2,3` = 어느 것도 아님). `slot_confirms` 경로는 슬롯을 목록 위치로 승격하므로(`console/lua/copilot_responder.lua:391-393`) 구조적으로 연속값만 낼 수 있고, 따라서 희소값은 자식 자신의 인덱스 접근자에서 온 것이다 — **`probe_slots`가 이 콘솔·빌드에서 작동한다.** 귀결 둘: (i) `console/lua/PROTOCOL.md:283-286`이 최악으로 적은 실패 모드("(a) 부재 + (b) 위치형 = 콘솔 측에서 탐지 불가능한 원래 결함")가 **이 빌드에서는 발생하지 않는다.** (ii) 픽스처 풀의 `i` 1부터 19까지가 **자기보고 슬롯**이므로 19번째가 슬롯 19에서 잡힌 것은 위치 우연이 아니라 풀이 진짜로 조밀하다는 뜻이고, 캡 밖 20부터 30까지의 부재 확인과 합쳐 **이 쇼파일의 픽스처 인덱스 정의역은 정확히 1부터 19까지로 닫힌다.** 갭 풀 스냅샷을 따로 만들지 않았고 페이지 풀이 갭 풀이어서 우연히 판별이 성립했다 — 본 SPEC 범위 밖이지만 여러 선행 SPEC이 걸려 있는 응답기 계약의 미확정이라 남긴다.

#### M0 결론

`ASSUMPTION-25`부터 `ASSUMPTION-30`까지 **6건 전부에 결과 어휘가 배정됐고 폐쇄 아님(`REOPEN_SCOPE`)이 0건**이다. 유일한 블로킹 전제였던 `ASSUMPTION-26`이 GO이므로 산출물 2(응답 확인 매크로)가 성립한다. `ASSUMPTION-27` 부정으로 구간 겹침 판정이 빠지고 주소 중복 판정만 남는다(`REQ-PRECHK-008`의 정의된 축소). **M1 착수 차단이 해소됐다.**

### M1 — 초크포인트 프로퍼티 조회 (AC-PRECHK-013 · cycle_type=tdd · 2026-07-30)

#### 착수 전제 확인

| 항목 | 값 |
|---|---|
| baseline (착수 직전 직접 실측) | `uv run pytest server/tests/ -q` → **2490 passed · 5 skipped · 0 failed** |
| 승인 기록 (`AC-PRECHK-013` ④) | §F의 사용자 접점 표 — `server/safety/**` 조건부 예외 **승인** |
| M0 결과 | `REOPEN_SCOPE` 0건 → 범위 재개정 선행 조건 없음. 착수 가능 |

#### 집행한 변경 — 승인된 4지점 + 신규 경로

| # | 파일 | 변경 | 동형 대상 |
|---|---|---|---|
| 1 | `server/safety/console.py` | `build_prop_query` import 1건 · `ConsolePort`에 `query_property` 선언 1건 · `ConsoleLink.query_property(path, property_name) -> dict` 1건 | `ConsoleLink.query_state` |
| 2 | `server/orchestrator/ports.py` | 신규 `PropertyQueryPort` 프로토콜 | `StateQueryPort` |
| 3 | `server/safety/gate.py` | `_GateStatePort.query_property` 위임 1건 · `SafetyGate._query_property` 감사 구현 1건 · 클래스 독스트링 1행 | `_GateStatePort.query_state` · `SafetyGate._query_state` |
| 4 | `server/measurement/mock_provider.py` | `OfflineConsole.query_property` 1건 | `OfflineConsole.query_state` |
| 5 | 신규 `server/prechk/__init__.py` · `server/prechk/query.py` | 포트만 소비하는 프로퍼티 판독 계층 | 없음 (신규 경로) |

**기존 심볼·시그니처 변경 0건**이며 테스트가 그것을 고정한다 — `ConsoleLink.query_state` · `_GateStatePort.query_state` · `StateQueryPort.query_state`의 파라미터 목록이 `["self", "path"]`임을 `inspect.signature`로 assert한다.

**지점 1이 두 hunk인 이유를 기록한다.** 승인 표의 지점 1은 `query_property` 추가 1건이지만, 게이트가 `self._console.query_property(...)`를 호출하므로 그 능력이 `ConsolePort`에 선언되지 않으면 게이트가 프로토콜에 없는 멤버에 의존한다. 그래서 같은 파일 안에서 선언 1행을 함께 넣었다. `ConsolePort`는 `runtime_checkable`이 아니므로(`server/llm/types.py:97`의 `LLMProvider`와 달리) 기존 대역의 런타임 계약을 깨지 않으며, 기존 4개 멤버의 시그니처는 그대로다. **`server/safety/**`의 hunk는 이 목록 밖으로 나가지 않는다.**

`server/prechk/`를 M1에서 만든 이유도 기록한다 — `plan.md` §B는 그 경로를 M2 신규 파일로 적었으나, `AC-PRECHK-013` ①의 **비공허성**(스캔 방문 파일 1 이상 · import 노드 1 이상)이 그 디렉터리의 실존을 요구한다. 빈 디렉터리에서는 "`server.bridge` import 0건"이 자동 성립해 게이트가 무력해진다. M1이 만든 `server/prechk/query.py`는 스텁이 아니라 M2 인벤토리가 소비하는 판독 계층이며, 형태 검증은 M2 소관으로 남겼다.

#### 뮤테이션 3건 — 전건 죽었다

`plan.md` §B M1이 지정한 3건을 집행하고 원본을 복원했다. **비공허성**: 각 뮤테이션에서 통과 테스트가 함께 보고되므로 "테스트가 돌지 않아 실패한" 오탐이 아니다.

| # | 뮤테이션 | 결과 |
|---|---|---|
| ① | `server/prechk/query.py`가 `server.bridge`를 import | **죽었다** — 신규 경계 테스트(1 failed · 3 passed)와 **기존** `server/tests/test_architecture.py`(1 failed · 3 passed) 양쪽 |
| ② | `_NAMED_TOOL_EXEMPTIONS`에 `server/prechk/query.py` 추가 | **죽었다** (1 failed · 1 passed) |
| ③ | 기존 `query_state`에 키워드 파라미터 추가 | **죽었다** (1 failed · 2 passed) |

①의 첫 시도는 셀렉터 오류로 `no tests ran`을 내면서 `rc != 0`이 됐다. **그것을 통과로 세지 않고 재집행했다** — 종료 코드만 보면 뮤테이션이 검증되지 않은 채 게이트가 통과한다.

#### 검증

| 항목 | 결과 |
|---|---|
| 신규 테스트 | `server/tests/test_prechk_inventory.py` **17 passed** |
| 전체 스위트 | **2507 passed · 5 skipped · 0 failed** (baseline 2490 대비 신규 17건) |
| `ruff check` (신규·변경 파일) | `server/prechk/` · 신규 테스트 · `ports.py` · `gate.py` · `mock_provider.py` **All checks passed** |
| `ruff format --check` | 위 6파일 **already formatted** |

**기존 비-clean 지점 1건을 손대지 않고 기록한다** — `server/safety/console.py`는 `E501` 2건(292행 · 346행)과 미포맷 상태를 **BASE 95687a0에서 이미** 갖고 있다. `git show 95687a0:server/safety/console.py`를 꺼내 같은 검사를 돌려 확인했다: `E501` 2건 · `Would reformat` 1건. `AC-PRECHK-015` ⑤가 무관 재포맷을 금지하므로 본 SPEC은 그 파일을 포맷하지 않았고, 내 hunk 자체는 `E501`을 만들지 않았다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

> 본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다. `plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다. 어긋나면 **본 절이 이긴다.** 이 헤딩은 v0.1.0 착수 시점에 **선제 생성**되었다 — 선행 SPEC에서 `plan.md`가 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목해 끊어진 참조를 만든 사례가 있었고(`.moai/specs/SPEC-COPILOT-LOOKLIB-001/plan.md:289`), BUSKWIZ가 선제 생성으로 그것을 고쳤다. 본 SPEC은 그 교정을 계승한다. 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이며, 비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록이다.

### Decision: **sub-agent (순차)** — `plan.md` §G의 권고를 **확정한다**

작성 시각 2026-07-29, **첫 run-phase `Agent()` 스폰 이전.** `plan.md` §G가 낸 권고(`sub-agent`)를 검토해 **그대로 확정**한다. 기각하지 않는다.

#### 착수 SHA (M7 PRESERVE 게이트의 `<BASE>`)

```
BASE = 95687a0    # = origin/main (SONGCUE squash 머지 직후)
```

**이 값이 `AC-PRECHK-015` ①의 `git diff --stat <BASE>..HEAD -- <목록>` 게이트가 쓰는 유일한 기준점이다.** 인자 없는 `git diff`로 대체하는 것은 협상 불가 — 커밋 직후 항상 빈 출력이라 게이트가 통째로 무력해진다.

#### 병렬을 기각하는 근거 — plan-phase의 경험이 이것을 뒷받침한다

`plan.md` §G의 입력 파라미터를 검토했고 전부 수용한다: tier L · 예상 13~16 파일 · **domain count 1** · Python + markdown 단일 언어 · **parallel benefit LOW**.

결정적인 것은 **사슬이 셋 겹친다**는 것이다.

| 사슬 | 내용 |
|---|---|
| **승인 사슬** | **M1이 승인 게이트에 걸려 있고 M1이 프로퍼티 조회를 제공한다.** 승인이 없으면 M2 이후 전부 정지한다 — 이것은 정책이 아니라 물리다 |
| **데이터 사슬** | M2 인벤토리 → M3 판정 → M5 리포트. M3·M4의 결과 형상이 M5의 입력이고 M6 툴 반환 형상을 정한다 |
| **모듈 사슬** | `server/prechk/`의 `inventory.py` → `patch.py` → `report.py`가 층으로 쌓인다. SONGCUE에서 `songcue.py` 하나를 M1~M4가 순차로 키운 것과 같은 형상이다 |

**SONGCUE의 경험이 이 판단을 강화한다.** 그 SPEC에서 폭 2가 나온 것은 M0가 **우연히 제2 도메인**(Lua 응답기)을 만들었기 때문이고, 본 SPEC의 M0는 그런 것을 만들지 않는다 — `ASSUMPTION-28`~`ASSUMPTION-30`은 **측정 대상이지 산출물이 아니다**(spec.md §D). **폭을 미리 약속하지 않는다**: M0 실측이 새 도메인을 만들면 그때 §F를 개정하고 그 사유를 적는다.

**단 plan-phase에서 검증된 병렬 형태 하나는 run-phase에서도 유효하다** — **읽기 전용 scout**다. 이번 plan-phase가 scout 4개를 동시에 돌려 586행을 냈고 충돌이 0이었다. run-phase에서 조사가 필요해지면 같은 형태를 쓴다.

#### 사용자 접점 — **2건 모두 승인됨 (2026-07-29)**

| # | 접점 | 상태 | 근거 |
|---|---|---|---|
| 1 | **`server/safety/**` PRESERVE 조건부 예외** | **승인** | 사용자 승인(2026-07-29). 강제 사유는 `research.md` §7.4 — 픽스처 주소는 프로퍼티에만 있고 `prop`은 프로덕션 경로로 도달 불가하며(`server/tests/test_architecture.py:27-39`, `server/tests/test_architecture.py:48-61`), `build_prop_query`에 프로덕션 소비자가 0건이다. 우회 4종 전수 배제 |
| 2 | **M0 라이브 세션 접근 가능성** | **승인 · 실측 확인** | onPC 2.4.2 PID 38963 · 응답기 **v1.5.0** · `responder_roundtrip --expect-version 1.5.0` **3/3 PASS** · 쇼파일 베이스라인 인계 기록값과 전량 일치 |

**승인 1의 집행 범위는 순수 추가 4지점으로 한정한다.** 이 목록 밖의 hunk가 `server/safety/**`에 생기면 `AC-PRECHK-015` ③이 실패로 판정한다.

| # | 파일 | 추가 | 금지 |
|---|---|---|---|
| 1 | `server/safety/console.py` | `query_property(path, property_name) -> dict` — 기존 `query_state`(`server/safety/console.py:372-386`)와 **동형** | 기존 심볼·시그니처 변경 |
| 2 | `server/orchestrator/ports.py` | 프로퍼티 조회 포트 프로토콜 — `StateQueryPort`(`server/orchestrator/ports.py:68-73`)와 동형 | 기존 프로토콜 변경 |
| 3 | `server/safety/gate.py` | 위임 노출 — `query_state`(`server/safety/gate.py:120`)와 동형 | 게이트 스크리닝 의미론 변경 |
| 4 | `server/measurement/mock_provider.py` | 테스트 대역 동형 1건 | — |

**우회 4종은 승인 후에도 금지다** — `server.bridge` 직접 import · `server/tools/` 운영 유틸 예외 목록 증설(`REQ-PRECHK-020`) · 응답기 확장(`console/lua/**`는 PRESERVE) · `exec` 결과 문자열 파싱. 승인은 **초크포인트를 통과하는 경로 하나**를 연 것이고 경계를 푼 것이 아니다. `REQ-MVP-029`의 단일 초크포인트 원칙은 이 변경으로 **강화된다**.

#### 남은 접점 1건과 조건부 접점

**M7 완료 직후 — M8 라이브 세션 접근 가능성 재확인.** 미도래. M8은 완성된 파이프라인이 대상이라 M0와 병합할 수 없다(라이브 회계 2회는 `plan.md` §C가 정본).

조건부 접점은 `plan.md` §G의 4건을 그대로 승계한다 — `ASSUMPTION-26` 부정 시 고지 · `ASSUMPTION-25` 부정 시 범위 재개정 요청 · `ASSUMPTION-28` GO 후 테스트 오브젝트 잔여 시 복구 증거 공유 · M8과 M0 판정 불일치 시 후속 판단 요청.

#### 착수 순서 — 이 순서를 지킨다

1. **M0 라이브 프로브**(`cycle_type=none`, 코드 변경 0) — `ASSUMPTION-25`~`ASSUMPTION-30` 6건에 결과 어휘 4값 중 하나를 배정하고 접두 행 4종으로 기록한다. **미관측 픽스처 1개(19번째)를 슬롯별 보강 조회로 채운다**(`research.md` §4.8). 쇼파일 원상 복구 + 재조회 확인.
2. **M1 초크포인트** — 승인된 4지점만. `AC-PRECHK-013` ④가 승인 기록의 존재를 착수 전제로 삼으며 **본 절이 그 기록이다.**
3. M2 → M3 → M4 → M5 → M6 → M7 → M8 순차.

**M0 이전에 M1에 착수하지 않는다** — M0가 `REOPEN_SCOPE`를 내면 범위 재개정이 선행하므로 초크포인트 변경이 헛일이 될 수 있다.
