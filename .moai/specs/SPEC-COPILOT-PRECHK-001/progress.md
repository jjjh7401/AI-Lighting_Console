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
| 픽스처 주소 읽기 (`prop … Patch`) | `미확정` | **`[실측]`** — `'1.001'` 포함 18개 전수 |
| 픽스처 열거 경로 | `미확정` | **`[실측]`** — `Patch/Stages/1/Fixtures` 18개 |
| 채널 점유폭 도달 | 미조사 | **`[실측]`** — `Patch/FixtureTypes/1/DMXModes/1/DMXChannels` `childCount = 29` |
| 매크로 저작 문법 | T3 | **T3 유지** — 라이브 `OK` 0건. `ASSUMPTION-26`이 M0에서 판정 |
| 픽스처 → 점유폭 연결 | 미조사 | **`[미확정]`** — 표시 문자열뿐. `ASSUMPTION-27` |
| `FID` 값의 의미 | 미조사 | **`[미확정]` 이며 M0가 닫을 수 없다** — 아래 |

### 조사가 정정한 선행 산정 2건

**1. 절단 원인이 둘이다.** SONGCUE는 `max_children = 24`를 근거로 *"자식이 24를 넘으면"* 절단된다고 산정했다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:403`). **픽스처 18개에서 절단이 떴다** `[실측]`. 코드에 독립된 경로가 둘이다 `[코드]` — ① 자식 수 상한(`console/lua/copilot_responder.lua:610`, `cap`은 `console/lua/copilot_responder.lua:581`) ② **페이로드 예산 루프**(`console/lua/copilot_responder.lua:634-639`, `max_payload = 1900`). 픽스처는 이름이 길어 24에 닿기 전에 ②가 먼저 발동한다. `SONGCUE-F3/G3`(절단 거동 미실측)를 승계해 닫았다.

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
  fixtures_read: 18         # FID · Patch · FixtureType · Mode 전수
  address_scheme: "'<유니버스>.<주소>' — 1.001~1.437(유니버스 1), 2.001~2.351(유니버스 2)"
  rig_verdict: "정합 — 주소 중복 0 · FID 중복 0. 결함이 없으므로 탐지 로직 검증에는 결함 심은 인메모리 픽스처가 필수(design.md §6.1)"
  traps_found: 3            # ok=true인 함수 참조 · 공백 프로퍼티명 거부 · 프로퍼티명 열거 불가
  truncation_observed: "픽스처 18개에서 truncated=true. 원인은 페이로드 예산(1900B)이며 자식 수 상한(24)이 아니다"
blocking_for_run: "**승인 대기 1건이 최대 위험이다** — `server/safety/**` PRESERVE의 조건부 예외가 승인되지 않으면 M1에 착수할 수 없고, M1이 프로퍼티 조회를 제공하므로 M2 이후도 정지한다. 우회 4종(bridge 직접 import · server/tools 예외 증설 · 응답기 확장 · exec 문자열 파싱)은 전부 금지이며 plan.md가 명시한다. 기술적 블로킹은 `ASSUMPTION-26`(매크로 저작 문법) 1건뿐이고 그것도 부정이면 M4가 DESCOPE로 완료된다 — 저작 차단이 아니다. `ASSUMPTION-27`은 동작 축소이며, `ASSUMPTION-28/29/30`은 BUSKWIZ 후속 측정이라 본 SPEC의 어느 마일스톤도 막지 않는다."
known_gaps:
  - "`FID` 값의 의미는 어떤 라이브 세션도 현재 쇼파일로 닫을 수 없다 — 슬롯 == FID이기 때문이다(`console/lua/PROTOCOL.md:322-324`). 슬롯 ≠ FID로 패치된 쇼파일이 선행 조건이며 사용자 GUI 작업이다. 본 SPEC은 FID를 판정 근거에서 배제한 형상으로 출하한다."
  - "절단 복구 경로의 인덱스 정의역을 모른다 — 풀이 희소할 수 있고(SONGCUE가 시퀀스에서 실측) 절단된 목록은 어느 슬롯이 존재하는지 알려주지 않는다. design.md 슬롯 A가 경계 있는 범위 탐색으로 결정하고 `index_domain_unknown`을 스키마에 두어 숨기지 않는다."
  - "매크로 저작 문법은 등급 T3이며 라이브 `OK` 0건이다. M0의 생성 프로브만이 판정할 수 있다 — 부정 프로브로는 갈리지 않는다(날조 키워드도 `Illegal object`를 준다)."
  - "라이브 원문 로그와 scout 산출물이 `.moai/state/`(`.gitignore:206`) 아래에만 있다. 커밋되는 사본은 `research.md`와 본 문서이며 그래서 커맨드·응답 문자열을 요약 없이 전재했다."
  - "plan-audit 1회차는 **FAIL 0.76**을 냈고 지적 11건(P1 4 · P2 6 · P3 1)을 **전건 닫았다**(§E.1a). 계수는 불변이다. **다만 감사가 재검증하지 않았다** — 1회차 정정이 새 불일치를 만들지 않았다는 증명은 없고 run-phase 각 마일스톤의 착수 직전 실측이 덮는다. 2회차를 열지 않은 근거는 §E.1a에 있다."
  - "감사의 축약 토큰 검출이 코디네이터의 정규식보다 정확했다 — 완전 토큰 뒤에 중점으로 이어 붙인 **3자리 숫자만의 항목**은 슬러그도 `AC-` 접두도 없어 코디네이터가 쓴 패턴에 걸리지 않는다. 이후 게이트는 **중점 뒤 3자리 숫자**도 함께 센다."
  - "M0 결과 어휘 4값(`GO` · `NEGATIVE` · `CONDITION_NOT_MET` · `REOPEN_SCOPE`)과 접두 행 4종은 **감사 지적으로 신설된 것이며 아직 라이브에서 쓰인 적이 없다.** M0가 그 형식을 실제로 산출하는지는 착수 시 확인된다."
next: "**Kickoff 사용자 접점 2건**(`server/safety/**` 조건부 예외 승인 · M0 라이브 세션 접근 가능성) → Implementation Kickoff Approval(plan→run HUMAN GATE) → §F 작성(첫 run-phase 스폰 전) → run(M0 프로브부터). **승인 없이 M1에 착수하지 않는다.** plan-audit는 1회차 FAIL 0.76 → 11건 전건 처리로 종료하고 2회차를 열지 않는다."
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

_<pending run>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

> 본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다. `plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다. 어긋나면 **본 절이 이긴다.** 이 헤딩은 v0.1.0 착수 시점에 **선제 생성**되었다 — 선행 SPEC에서 `plan.md`가 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목해 끊어진 참조를 만든 사례가 있었고(`.moai/specs/SPEC-COPILOT-LOOKLIB-001/plan.md:289`), BUSKWIZ가 선제 생성으로 그것을 고쳤다. 본 SPEC은 그 교정을 계승한다. 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이며, 비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록이다.

_<pending orchestrator>_
