# SPEC-COPILOT-PRECHK-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**). 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]`이며 **`[실측]`은 라이브 콘솔 직접 관측만**을 가리킨다.

## §0 인수인계 — 여기서 시작한다 (2026-07-30)

> **이력을 모르는 사람이 처음 읽는 절이다.** 본 문서는 1000행이 넘고 절이 시간순으로 쌓여 있으므로, 아래 읽는 순서를 지키면 앞의 절을 몰라도 현재 상태에 도달한다.

### 한 문단

**무엇**: 조명 콘솔(grandMA3)의 패치를 프리쇼에 점검하는 기능. 리그의 픽스처를 읽어 **관측 픽스처 전량 + 집계 2단**으로 보고하고, 주소 중복·판독 실패·열거 완전성·**수행하지 않은 판정**까지 명시한다. 요청하면 그룹별 점등·소등 매크로를 저작해 사람이 눈으로 응답을 확인하게 한다. 모델이 닿는 표면은 툴 `precheck_patch` 하나다.
**상태**: **머지 완료 — SPEC 종료.** `spec.md status: completed` · AC 17/17 PASS · M0~M8 9개 마일스톤 · 감사 2회(독립 run-audit FAIL 0.695 지적 14건 + 독립 코드 리뷰 지적 14건) 지적 28건 중 27건 처리 · **PR #7 squash 머지**(2026-07-30). 새 `origin/main` = **`b406a7b2bde856f0ecfb445885e6fe60693c68a5`**.
**열린 사용자 접점**: **1건** — 후속 SPEC(구간 겹침 재개)의 **닫힌 어휘 확장 승인**. 리뷰 잔여 2건이 이 결정에 묶여 있다(정밀도 문제이며 정보 손실 아님).

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | **이 SPEC은 끝났다. 다음 담당자가 알아야 할 것** | 본 문서 **§E.9**(머지 사실 · **BASE SHA 두 개를 혼동하지 않는 법** · 후속이 이어받을 5항목) ← **여기서 시작한다.** 리뷰 지적 처리 이력이 필요하면 §E.7 → §E.8 |
| 2 | 무엇을 만들기로 했나 | `spec.md` — REQ 20건 · §C PRESERVE와 **승인된 조건부 예외** · §D Out of Scope |
| 3 | 무엇을 통과해야 하나 | `acceptance.md` — AC 17건 · 역추적표 · 마일스톤별 배정 |
| 4 | **실물 콘솔에서 무엇이 사실로 밝혀졌나** | 본 문서 **§E.2**의 M0 절 — 판정 6건의 접두 행과 실측 원문. 이 SPEC의 모든 설계가 여기서 나온다 |
| 5 | 독립 감사가 무엇을 잡았나 | 본 문서 **§E.2a** — 7축 점수와 지적 14건 처리표 |
| 6 | 왜 이렇게 설계했나 / 왜 이 순서로 만들었나 | `design.md` 슬롯 A~E · `plan.md` §B M0~M8 |
| 7 | 조사 원문(가장 김) | `research.md` — 필요할 때만 |

**§E.1 · §E.1a · §E.3 · §E.3a · §E.4는 시점 기록이다**(plan 신호 · plan-audit · run 신호 · 1차 핸드오프 · sync 신호). 이력 추적이 필요할 때만 본다. **§E.3a는 §E.5가 대체했고, §E.5 · §E.6은 §E.7이 집행했다** — §E.6 ④의 서술 2건은 §E.7이 정정했으므로(`COLLISION_KIND` 추가 0건 · 미확정 술어의 off-by-one) **§E.6 ④를 단독으로 읽지 않는다.**

### 인수인계 시 반드시 알아야 할 함정 4건

1. **OSC 포트는 send 8000 / receive 9005다.** 기본값 9000이 아니다 — 이 값을 읽지 않아 선행 SPEC이 오진 1건을 냈다.
2. **`node.childCount`와 `len(children)`을 함께 본다.** `truncated`는 *"불완전하다"* 만 말하고 *"얼마나"* 를 말하지 않는다. 조사 자신이 반환 수 18을 총수로 오독하고 그 위에 *"정합한 리그"* 를 얹었다(`research.md` §4.8). 이 SPEC의 1급 요구 `REQ-PRECHK-004`가 그 실증에서 나왔다.
3. **`Cmd` 접수 `OK`는 효과 증거가 아니다.** 거부된 커맨드에 `OK`가 온 사례와, **`OK`를 내면서 의도한 대상이 아닌 곳을 덮은 사례**가 둘 다 실측됐다(`Executor 201`이 page 2가 아니라 page 1의 인덱스 101을 조용히 덮었다). 효과는 **재조회로만** 확인한다.
4. **"판독 실패"와 "그런 것이 없음"을 섞으면 결함이다.** 이 계열로 결함이 **3건** 나왔다 — 코드 경로가 방어 가능해도 **사용자가 읽는 문자열이 거짓**이면 결함이다. 새 판독 경로를 추가할 때마다 묻는다: *"읽지 못했을 때 이 문자열이 여전히 참인가?"*

### 인수인계가 온전한지 기계로 확인하는 법

```
git rev-parse --abbrev-ref HEAD                 -> feature/SPEC-COPILOT-PRECHK-001
git status --short                              -> 비어 있음
find server -name __pycache__ -type d -exec rm -rf {} + ; uv run pytest server/tests/ -q
                                                -> 2721 passed · 5 skipped · 0 failed
git diff --stat 95687a0..HEAD -- server/looks/schema.py server/looks/loader.py \
  server/looks/roles.py server/looks/resolver.py server/looks/instantiate.py \
  server/looks/matching.py server/looks/library/ server/web/preview.py console/lua/ \
  server/rulebook/assets/v2.4.2/                -> 빈 출력 (PRESERVE 무변경)
```
**`95687a0`이 이 SPEC의 BASE이며 협상 불가다** — 인자 없는 `git diff`로 대체하면 위반이 커밋돼 있어도 0행을 내며 게이트가 통째로 무력해진다(실측으로 증명, §E.2 M7 절).

### 넘어가지 않는 것 — 그리고 그래도 괜찮은 이유

`.moai/state/verify/prechk-*`의 **616KB가 `.gitignore:206` 대상이라 다른 기계로 넘어가지 않는다** — M0 라이브 원문 로그(282레코드·148KB) · M0·M8 프로브 드라이버 · M8 종단 결과 · run-audit 원문(48KB) · scout 산출 4건(216KB).

**그래도 증거 사슬은 끊기지 않는다.** 이 프로젝트의 확립된 규약은 *원시 로그를 커밋하는 것이 아니라 결론을 요약 없이 전재하는 것*이며(선행 SPEC의 선례), 본 SPEC은 그것을 지켰다. **핵심 라이브 값 10건이 전부 추적되는 정본에 실재함을 확인했다** — `MMX 19` · `2.401` · `On Group 11` · `Group 11 At 0` · `PRECHK Probe` · `function: 0x…` · `Illegal object` · `Cannot Create Object` · `금빛 코러스` · `Ballad Yellow Red`. **정본에 없어 유실될 값은 0건이다.**

**`server/` 안에 추적 불가 경로를 인용하는 코드·테스트는 0건이다**(런타임 의존도, 주석 인용도 없다). 즉 **신규 클론에서 스위트가 그대로 통과한다.**

재생성이 필요하면: M0 프로브 드라이버는 `server/bridge/{osc,protocol}.py`만 쓰고 스텝 종류가 `state`·`prop`·`exec`·`ping` 넷이며, M8 하네스는 `build_console_stack` + `build_toolset` 조립이 전부다 — 둘 다 §E.2의 서술로 재작성 가능하다. **다시 만들 수 없는 것은 라이브 관측 자체이며, 그것은 실물 콘솔이 있어야 한다.**

### 다음 담당자가 먼저 결정할 것 1건

후속 후보 1순위(구간 겹침 재개, §E.6 트랙 B)는 **닫힌 판정 어휘를 늘리는 것**을 요구한다 — 상계 논증은 *"겹침 없음"* 만 증명하고 *"겹침 있음"* 은 증명하지 못하므로 `미확정` 부류가 필요하다. **어휘 확장은 계약 변경이므로 SPEC 문서를 쓰기 전에 사용자 승인을 받는다.**

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
GO: ASSUMPTION-26 literal=Store Macro 91 ; Store Macro 91.1 ; Set Macro 91.1 Property 'Command' 'On Group 11' ; Set Macro 91.1 Property 'Command' 'Group 11 At 0' effect=DataPool/Macros childCount 1에서 2로 증가하고 자식에 'Macro 91' 출현, DataPool/Macros/91 childCount 0에서 1로 증가해 'MacroLine 1' 출현, prop DataPool/Macros/91/1 Command 재조회 값 'On Group 11', 그리고 M4 보강 세션에서 같은 저작 문법으로 소등 페이로드를 저장해 prop DataPool/Macros/91/1 Command 재조회 값 'Group 11 At 0'
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

### 병렬 웨이브 1 — M2·M3 사슬 + M4 (2026-07-30)

§F.1이 확정한 폭 2로 집행했다. 워커 2개, 파일 교집합 0건, 충돌 0건.

| 마일스톤 | 산출 | 테스트 | 뮤테이션 |
|---|---|---|---|
| M2 인벤토리 | `server/prechk/inventory.py` | 27건 | 8건 전건 사망 |
| M3 패치 정합성 | `server/prechk/patch.py` | 42건 | 6건 전건 사망 |
| M4 매크로 | `server/prechk/macro.py` | 73건 | 6건 전건 사망 |

선행 공유 계약은 스폰 이전에 오케스트레이터가 직접 만들었다 — `server/prechk/verdicts.py`(닫힌 어휘 5종 + `validate()`)와 `server/tests/test_prechk_verdicts.py`(8건). 워커에게 계약을 협상시키지 않았다.

**검증한 것과 그 방법.** 워커 보고를 신뢰하지 않고 직접 재고했다. 전체 스위트 2657 passed · 5 skipped · 0 failed. 공유 계약 4파일과 `server/safety/**` · `console/lua/**`의 diff가 빈 출력. `server/prechk/macro.py`에서 `Fixture` 토큰이 독스트링 1건뿐이고 생성 커맨드에 0건. `server.bridge` import 0건(`server/tests/test_architecture.py` 4 passed).

**워커가 내 결함 1건을 수리했다.** 내가 §F.1을 추가하면서 M1 테스트 `test_approval_record_exists_in_progress`의 `progress.split("## §F.")[-1]`이 §F.1만 잡게 됐다. 워커가 §F 전 하위절을 결합하는 형태로 고치고 `len(parts) >= 2` 비공허성 assert를 더했다. 단정은 약화되지 않았음을 diff로 확인했다.

**정본 드리프트 결정 1건.** `design.md` §6.1의 `clean_rig_18`은 *"실측 리그와 같은 정합 주소"*를 주장하지만 실측 리그는 M0에서 19개가 됐다. **합성 픽스처이며 라이브 미러가 아닌 것으로 확정**했다 — 인메모리 픽스처를 현장 쇼파일에 묶으면 리그가 바뀔 때마다 테스트가 깨지고 결정성이 사라진다.

### M5 — 리포트 (AC-PRECHK-012 · 2026-07-30)

`server/prechk/report.py` + `server/tests/test_prechk_report.py` 32건. 뮤테이션 5건 전건 사망(집계만 반환 · 집계와 픽스처별 불일치 · 밑줄 식별자 직접 import · 어휘 밖 코드 조용한 통과 · macro 산출 누락), 비공허 26~31건 통과 동반.

**`AC-PRECHK-012` ④의 재사용 판정을 기록한다.** `server/looks/report.py`에서 **문자열을 재사용할 지점이 0건**이다. 두 어휘가 서로소이고(그쪽은 룩·프리셋 사유, 이쪽은 패치 판정), 유일한 겹치는 키 `complete`는 의미가 다르다 — 그쪽은 *"모든 룩 저장 성공"*, 이쪽은 *"열거가 짧지 않았다"*다. 빌려 쓰면 가장 중요한 수치를 오라벨링한다. 계승한 것은 **패턴**(라벨을 표현 계층의 공개 접근자 뒤에 두고 자산·스키마에 두지 않는다)이며, 밑줄 식별자 import 0건을 AST 스캔이 강제한다.

**라벨 정책이 `server/looks/report.py`와 다른 이유도 코드에 적었다.** 그쪽 `reason_label`은 모르는 코드를 그대로 통과시킨다(`server/looks/report.py:78-84`) — 사유가 콘솔에서 자유 문자열로 올라오므로 지어낸 번역이 원문 검색을 막기 때문이다. 프리체크 판정은 그런 출처가 없고 항상 닫힌 5집합의 원소이므로 모르는 코드는 버그다. 그래서 `label()`은 `validate()`를 먼저 돌려 **실패**한다(`AC-PRECHK-012` ⑤ d).

### M6 — 툴 배선 (AC-PRECHK-014 · 2026-07-30)

`precheck_patch`를 등재 3곳(`TOOL_NAMES` · `definitions` · `handlers`)에 넣고 **디스패치로** 검증했다. 21건. 뮤테이션 5건 전건 사망.

| 뮤테이션 | 결과 |
|---|---|
| `TOOL_NAMES`에서 신규 이름 제거 | 죽었다 (2 failed / 19 passed) |
| 핸들러가 `execution_port`를 직접 호출 | 죽었다 (4 failed / 17 passed) |
| 신규 전송 표면(`APIRouter`) 도입 | 죽었다 (1 failed / 20 passed) |
| 스키마에 그룹·슬롯 인자 추가 | 죽었다 (1 failed / 20 passed) |
| 게이트 보류의 `is_error`를 거짓으로 | 죽었다 (1 failed / 20 passed) |

전송 표면 뮤테이션의 **첫 시도는 무효였다** — `WebSocket`을 모듈 최상단에 두어 `NameError`로 임포트를 깨뜨렸고 19건이 전면 실패했다. 그것은 스캔이 잡은 것이 아니라 임포트가 깨진 것이다. 미실행 함수 안의 `APIRouter()` 참조로 다시 집행해 **스캔이 정확히 1건만** 죽이는 것을 확인했다.

**매크로 슬롯은 파라미터가 아니라 유도값이다.** `AC-PRECHK-014` ③이 스키마에서 리그 식별자를 금지하고, 측정된 리그에서 슬롯 1은 응답기 자신의 `Copilot Go` 매크로가 점유한다. 그래서 핸들러가 `DataPool/Macros`를 읽어 **점유되지 않은 최소 양의 정수**를 고르고, 풀을 읽지 못하면 슬롯 1로 폴백하지 않고 오류로 답한다.

**`build_toolset`에 `property_port`를 추가했고 기존 호출 20곳을 고치지 않았다** — 생략 시 `state_port`가 `query_property`를 가지면 채택한다. 게이트의 포트 객체가 둘을 구현하므로 프로덕션 배선은 무변경으로 능력을 얻고, 좁은 테스트 대역은 좁은 채로 남아 `precheck_patch`가 *"프로퍼티 읽기가 배선되지 않았다"*고 말한다(빈 리포트를 내면 정합한 리그로 읽힌다).

#### M6에서 내가 만든 버그 1건 — 자체 발견·수정

`from server.prechk.report import build_report`가 **`server/looks/report.py`의 동명 심볼을 가렸다**(`server/orchestrator/tools.py:30`에서 이미 import되어 `prepare_busking`이 쓰던 것이다). 전체 스위트에서 busking 12건이 `'GenreBundle' object has no attribute 'to_dict'`로 죽었다 — 내 리포트 빌더가 호출된 것이다. `build_precheck_report` 별칭으로 교정했다. **전체 스위트를 돌리지 않았으면 이 버그가 통과했다** — 신규 파일만 돌린 결과는 21 passed였다.

아울러 `server/tests/test_tools.py`의 툴 계수를 8에서 9로 갱신했다(선언 집합과 등재 집합의 동일성을 고정하는 테스트이며, 툴을 더하면 의도적 갱신이 필요한 형태다).

### M7 — 회귀 · PRESERVE (AC-PRECHK-015 · 2026-07-30)

**baseline은 이 마일스톤이 착수 직전 직접 실측했다**(이월 인용 없음): `uv run pytest server/tests/ -q` → **2710 passed · 5 skipped · 0 failed**.

| 구간 | 결과 |
|---|---|
| ① PRESERVE diff `git diff --stat 95687a0..HEAD -- <10경로>` | **빈 출력** |
| ② 게이트 비공허성 | 주입 2회 전건 적발 후 revert |
| ③ `server/safety/**` diff 대상 | `server/safety/console.py` · `server/safety/gate.py` — **승인된 4지점 안** |
| ④ 전체 스위트 신규 실패 | **0건** |
| ⑤ `ruff check` · `format --check` (신규·변경 18파일) | **All checks passed · already formatted** |

**목록 오타 위양성을 배제했다.** PRESERVE 10경로 전부가 BASE `95687a0`에 실존함을 `git cat-file -e` / `git ls-tree`로 확인했다 — 오타가 있으면 게이트는 언제나 통과한다.

**게이트 비공허성 실증 2회.** (i) `console/lua/PROTOCOL.md`에 개행 1건을 주입해 커밋하니 게이트가 `console/lua/PROTOCOL.md | 1 +`로 적발했고 revert 후 빈 출력으로 돌아왔다. (ii) `server/safety/audit.py`에 같은 주입을 하니 diff 대상 목록에 `audit.py`가 출현했고 revert 후 승인 부분집합만 남았다 — ③의 비공허성이다.

**뮤테이션 실증 2건.** `console/lua/copilot_responder.lua`에 주입한 상태에서 두 게이트 형태를 나란히 측정했다: **인자 없는 `git diff --stat -- <목록>`은 0행**(위반이 커밋돼 있는데도 무력화)이고 `<BASE>..HEAD`는 `copilot_responder.lua | 1 +`로 적발했다. 즉 `<BASE>..HEAD` 범위가 협상 불가라는 `AC-PRECHK-015` ①의 규정이 실측으로 뒷받침된다. 동시에 *"`console/lua/**`를 수정한다"*는 M7 뮤테이션도 이 사이클이 죽였다.

**③의 hunk 내역을 전수 기록한다.** `server/safety/console.py`는 **hunk 3개 전부 순수 추가**이고 삭제 0행이다(import 1행 · `ConsolePort` 선언 2행 · `ConsoleLink.query_property` 33행). `server/safety/gate.py`는 추가 2개(`_GateStatePort.query_property` 위임 · `SafetyGate._query_property` 감사 구현)와 **삭제 1행**이며, 그 1행은 `_GateStatePort`의 **독스트링**이다 — `"StateQueryPort implementation ..."`을 `"StateQueryPort + PropertyQueryPort ..."`로 정정했다. 심볼도 시그니처도 게이트 스크리닝 의미론도 아니며, 두 포트를 구현하게 된 클래스가 하나만 구현한다고 적어 두면 거짓 주석이 된다. **승인 표의 금지 항목(기존 심볼·시그니처 변경 · 프로토콜 변경 · 스크리닝 의미론 변경)에 해당하는 hunk는 0건이다.**

**⑤의 기존 비-clean 지점.** `server/safety/console.py`는 `E501` 2건(292행 · 346행)과 미포맷 상태를 **BASE `95687a0`에서 이미** 갖고 있다. `git show 95687a0:server/safety/console.py`를 꺼내 같은 검사를 돌려 확인했다. 무관 재포맷을 피해 손대지 않았고 내 hunk는 `E501`을 만들지 않았다.

#### 선행 SPEC 트립와이어 1건을 의도적으로 갱신했다

`server/tests/test_songcue_bundle.py`의 `_TOOLS_EXPECTED_HUNK_OLD_STARTS`가 SONGCUE 자체 run-phase BASE 기준 `server/orchestrator/tools.py`의 hunk 시작점을 못박고 있었고, M6의 정당한 편집으로 깨졌다. **이 가드의 실제 불변식은 두 번째 단정**(보호 구간 `(234, 238)`과 `(524, 569)` 무침범)이며 그것은 그대로 통과한다. 첫 단정은 후속 SPEC이 tools.py를 건드릴 때 **의도적 갱신을 강제하는 트립와이어**이므로, 스냅샷을 `(33, 49, 125, 463, 475, 479, 951, 1222, 1231)`로 갱신하고 무엇이 왜 늘었는지를 상수 위 주석에 적었다 — PRECHK가 구 시작점 463과 475와 479에 hunk 3개(프리체크 import 그리고 `property_port` 파라미터 그리고 그 독스트링)를 더했고, import 블록을 한 행 아래에 넣어 첫 hunk의 구 시작점이 32에서 33으로 옮겼다. **보호 구간을 건드린 hunk는 0건이다.**

### M8 — 종단 라이브 (AC-PRECHK-017 · cycle_type=none · 2026-07-30)

**세션 조건 재측정** — `responder_roundtrip --expect-version 1.5.0` **3/3 PASS** · 응답기 `v1.5.0` · OSC send 8000 / receive 9005. `plan.md` §C가 고정한 라이브 회계 2회의 두 번째다.

**우회 배선 0건.** 콘솔 스택은 제품 조립 루트 `build_console_stack`이 세우고 툴은 `ChatSession`이 쓰는 것과 같은 `build_toolset`으로 만들었다. 하네스는 `.moai/state/verify/prechk-m8/e2e.py`(`.gitignore:206` 대상)이며 **코드 변경 0건**이다.

**쓰기 0건으로 실행했다.** `precheck_patch`를 `create_macro=false`로 발화했다 — `AC-PRECHK-017`의 기대 결과 6항은 전부 읽기·판정·보고 통합에 관한 것이고 매크로 발화를 요구하지 않는다. `attempt_session_backup`도 껐다(세션 백업은 쓰기다). 매크로 저작 경로의 라이브 증명은 M0가 이미 갖고 있다(리터럴 3단 + 재조회 효과 확인).

| 기대 결과 | 관측 |
|---|---|
| ① 픽스처 목록이 재조회 실측과 일치 | 슬롯 19개 전량, **불일치 0건**. 슬롯 19 = `name 'MMX 19'` · `patch_raw '2.401'` · `universe 2` · `address 401` |
| ② 완전성 3수치가 실제 `childCount`·읽은 개수에서 나온다 | `child_count 19` · `observed_count 19` · `missing_count 0` · `recovered_count 1` · `completeness incomplete` |
| ③ 정합 리그이므로 충돌 0건, 오탐 없음 | `address_duplicates 0` · `range_overlaps 0` · `read_failures 0` |
| ④ 집계 = 픽스처별 합 | `observed_clear 19`가 픽스처별 합과 일치, `not_assessed 0 == missing_count 0` |
| ⑤ 증거는 감사 로그 대조 | `property_query` **95건** · `state_query` **27건** · `command` **0건**. 감사에 나타난 슬롯 집합이 리포트의 슬롯 집합과 동일 |
| ⑥ M0 `ASSUMPTION` 재측정 금지 | 재측정 0건. `skipped_checks`가 `range_overlap_descope` / `ASSUMPTION-27`로 축소를 명시 |

**불완전 경로를 실물에서 밟았다** — 이것이 이 AC의 핵심이다. 루트 열거가 19에서 절단되자 슬롯별 보강 조회가 발동해 19번째를 회수했고(`recovered_count 1`), 그럼에도 `completeness`는 `complete`로 **승격되지 않았다**(`index_domain_unknown true` · `recovery_boundary 19`). `design.md` 슬롯 A가 설계로 적은 것이 실물에서 그대로 동작했다.

**쇼파일 원상 복구.** `command` 감사 이벤트가 0건이므로 이 세션은 콘솔에 아무것도 발화하지 않았다. 착수 baseline 6경로의 `childCount`가 전항 일치한다(`DataPool/Sequences 17` · `DataPool/Timecodes 0` · `Patch/Stages/1/Fixtures 19` · `DataPool/Groups 4` · `DataPool/Macros 1` · `DataPool/Pages 1`).

**한계를 결과에 명시했다.** 무응답 여부는 판정하지 않으며 검증은 패치 메타데이터 수준이다. `macro` 키는 이 실행에 없다(요청하지 않았다).

#### M8이 잡은 결함 1건 — 라이브 실행이 없으면 통과했다

`summary_ko`의 첫 문장이 `열거 불완전 — 못 읽은 픽스처가 있다`였는데 이 세션의 `missing_count`는 **0**이었다. 보강 조회가 19개를 다 읽었으므로 그 문장은 **거짓**이고, 사용자가 가장 먼저 읽는 문자열에서 거짓을 말한 것이다. 라벨이 서로 다른 두 사실을 뒤섞고 있었다 — *"루트 열거가 짧았다"*(참)와 *"못 읽은 것이 남았다"*(이 경우 거짓).

라벨을 `열거 불완전 — 루트 열거가 짧았고 인덱스 정의역 상한을 모른다`로 교정하고 회귀 테스트를 신설했다(`test_the_incomplete_label_does_not_claim_unread_fixtures`) — 보강으로 전량 관측했는데도 `incomplete`인 인벤토리에서 요약이 미관측을 주장하지 않음을 고정한다. **옛 라벨로 되돌리면 그 테스트가 죽는 것을 확인했다**(1 failed / 32 passed). 못 읽은 개수는 0보다 클 때만 별도로 싣는다.

**라이브 세션에서 코드를 고치지 않았다.** 스택을 닫은 뒤 교정했고, 라이브 관측을 통과시키기 위한 수정이 아니라 관측이 드러낸 거짓 서술을 고친 것이다. 교정 후 하네스를 재실행해 같은 결과와 교정된 요약을 확인했다.

전체 스위트 **2711 passed · 5 skipped · 0 failed**(회귀 테스트 1건 추가). `ruff check` / `format --check` clean.

## §E.2a Run-audit 1회차 — FAIL 0.695 → 지적 14건 처리 (2026-07-30)

독립 감사자(작성자가 아닌 주체)가 커밋 `b355469` 시점의 run-phase를 채점했다. 원문은 `.moai/state/verify/prechk-runaudit/AUDIT-1.md`이며 그 경로가 `.gitignore:206` 대상이므로 **본 절이 추적되는 사본이다.**

**Verdict: FAIL · 가중합 0.695 / 기준선 0.85 · 지적 14건(P1 4 · P2 7 · P3 3).**

| 축 | 가중치 | 점수 | 감사 요지 |
|---|---:|---:|---|
| 인용 정확성 | 20% | 0.76 | `server/orchestrator/tools.py` 좌표 18건 중 17건이 M6 편집으로 어긋남 · 룰북 인용 2건이 리터럴을 담지 않음 · 계수 오류 2건 |
| 교차 정합 | 30% | 0.58 | P1 4건이 전부 이 축 — 출하 코드가 `REQ-PRECHK-012`·`acceptance.md` §D·`AC-PRECHK-014` ④와 어긋남 |
| 요구-AC 정합 | 15% | 0.74 | REQ 20/20 커버·역추적 20행·배정 17은 전건 재현. 감점은 `REQ-PRECHK-012` 미준수와 계수 비교가 두 풀 중 하나에만 적용된 것 |
| AC 기계검증성 | 15% | 0.72 | 게이트가 결함을 **비껴간** 지점 4곳 |
| 증거 등급 규율 | 10% | 0.72 | 오등급 0건이나 §E.2 이후 등급 태그가 0개 |
| 범위 경계 | 5% | 0.94 | 모범적 — PRESERVE·초크포인트·예외목록 전건 통과 |
| 미결 은닉 | 5% | 0.62 | 자기 결함 3건 자진 보고는 강한 긍정. 감점은 `REQ-PRECHK-012` 이탈 미기록 |

**감사가 재현해 정확하다고 확인한 것**: 계수 8종 전건 일치(REQ 20 · AC 17 · 역추적 20행 · 마일스톤 9 · AC배정 17 · `ASSUMPTION` 6 · 슬롯 5 · 결정 7) · 접두 행 6행 동일 분포 · **`GO:` 4행의 `effect=`가 4/4 재조회이며 `Cmd` 접수만 인용한 행 0건** · M8 기대결과 6/6 원시 산출물 일치 · 전체 스위트 2711·5·0 정확 재현 · PRESERVE diff 빈 출력 + 10경로 BASE 실재 · `server/safety/**` 삭제 1행이 **정말로 독스트링** · `test_architecture.py`가 BASE와 바이트 동일 · 뮤테이션 3건 직접 재현(전건 비공허 사망 + sha256 복원 + 재통과) · **`AC-PRECHK-017`이 매크로 발화를 요구하지 않는다는 작성자 판단이 원문 대조로 옳음**.

### 처리 표 — 14건

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| **P1-1** | P1 | 매크로 소등 라인 `Group <n> At 0`이 **M0 미실측 리터럴**이며(`steps.jsonl`의 `exec` 24건에 `At 0`·`Off ` 0건) `REQ-PRECHK-012`·`AC-PRECHK-010` ①을 위반. 게이트가 구조적으로 비껴감(대조 전 페이로드 삭제 + ON 한정 필터) + 소등 형태가 테스트에 전사 | **닫힘 — 라이브로 측정했다.** M4 보강 세션에서 `Set Macro 91.1 Property 'Command' 'Group 11 At 0'`을 발화하고 재조회로 `Command` = `'Group 11 At 0'` 확인. 대조군으로 `Off Group 11`도 저장 가능함을 확인해 **치환 이유가 저장 가능성이 아니라 프로덕션 게이트의 재귀 분류**임을 입증. `GO: ASSUMPTION-26` 접두 행에 그 리터럴을 추가하고, 테스트를 **ON 한정 필터 제거 + 전 페이즈 대조**로 바꾸고 전사를 정본 대조로 교체. 쇼파일 복구 후 baseline 6경로 전항 일치 |
| **P1-2** | P1 | 그룹 풀 판독 실패를 빈 풀로 치환해 *"리그에 그룹이 없어…"* 라는 **거짓 문자열**과 `is_error=False`를 냄. `acceptance.md` §D는 `is_error=True`를 요구하고 같은 SPEC의 `server/prechk/inventory.py:75-81`이 정반대 규율을 못박음 | **닫힘** — `server/orchestrator/tools.py`가 그룹 풀 판독 실패를 `_error_result`로 답한다(전송 실패와 `ok=false` 양쪽). 회귀 테스트 2건 신설 |
| **P1-3** | P1 | `_free_macro_slot`이 `node.childCount`를 보지 않아 **절단된 매크로 풀에서 점유 슬롯을 골라 기존 매크로를 덮어쓴다.** 본 SPEC의 유일한 쓰기 경로가 본 SPEC의 1급 요구(`REQ-PRECHK-004` 계수 비교)를 지키지 않음 | **닫힘** — 계수 비교를 넣고 불완전 열거에서는 슬롯을 고르지 않고 오류로 답한다. 슬롯 인덱스가 없는 자식도 거부. 회귀 테스트 3건(절단 거부 · 비공허 정상경로 · 인덱스 부재 거부) |
| **P1-4** | P1 | `AC-PRECHK-014` ④의 **LiveLock 강등이 구현·테스트 양쪽에 없다.** 형제 툴 2개에는 있음. 게이트 보류(참)와 LiveLock(거짓)을 한 덩어리로 뭉갬 | **닫힘** — `gate_status == _LOCKED`면 `is_error=False`로 강등한다. `LockedGate` 대역과 회귀 테스트 3건(락은 답변 · 리포트·상태 보존 · 보류는 여전히 오류) |
| **P2-1** | P2 | 그룹 열거가 **전부 절단**돼도 같은 거짓 라벨이 나가고 절단 신호가 버려짐. `acceptance.md` §D는 같은 케이스를 *"불완전 보고"* 로 정의 | **닫힘** — `groups.truncated`면 `PARTIAL_GROUP_COVERAGE`로 답한다. 회귀 테스트 2건(절단은 절단으로 · **진짜 0그룹은 여전히 부재로** — 비공허성) |
| **P2-2** | P2 | `tests_added: 216`이 자기 내역 합(221)과 스위트 델타(221) 양쪽과 어긋남 | **닫힘** — §E.3을 실측값으로 정정. 수정 후 현재값은 **231** |
| **P2-3** | P2 | 뮤테이션 회계 불성립 — M0·M8 미집행 사유 미기록, M2·M3·M4의 20건이 집계만이라 채점 불가, `mutations_executed: 34`가 어떤 재구성과도 불일치 | **부분 닫힘** — 아래 「뮤테이션 회계」 절에서 미집행 사유를 적고 계수를 정정한다. **M2·M3·M4 20건의 개별 증거는 복원하지 못한다** — 워커 로그가 `.gitignore:206` 아래에 있고 그 20건은 워커가 자기 보고로만 남겼다. **증거 부재로 기록하고 재집행하지 않았다**(재집행하면 다른 사람이 다른 뮤테이션을 돌린 것이 되어 원래 주장을 검증하지 못한다) |
| **P2-4** | P2 | `AC-PRECHK-006` ④의 둘째 연언이 테스트에서 반대로 단정되는데 17/17 PASS로 계상 | **닫힘** — `acceptance.md` `AC-PRECHK-006` ④와 `design.md` §6.1의 `clean_rig_18` 행을 **의도적 합성·열거 완전**으로 정정하고, 불완전 입력의 한정 유지는 `truncated_parent`와 `AC-PRECHK-009`가 소유함을 명시 |
| **P2-5** | P2 | `ASSUMPTION-27` 부정이 **한정 없이** 단정됐고 후보 12건이 전수가 아님(감사가 2건 추가) | **닫힘** — 아래 「`ASSUMPTION-27` 주장 범위 정정」 절에서 주장을 *"변경하지 않은 응답기 읽기 표면 위에서, 실제 발화한 프로퍼티명 집합에 한정해 0건"* 으로 좁히고 감사의 후보 2건을 미측정으로 등재 |
| **P2-6** | P2 | 증거 등급 규약이 §E.2 전체에서 버려짐(오등급 0건, 무등급) | **부분 닫힘** — 아래 「증거 등급 규약」 절에서 §E.2의 규약을 **절 단위**로 선언한다. 563행에 태그를 소급 부착하지는 않았다 |
| **P2-7** | P2 | `server/orchestrator/tools.py` 좌표 18건 중 17건이 어긋났고 sync 정책상 정정 경로가 닫힘 | **닫힘(해소 방식 변경)** — 17건을 재작성하지 않고 아래 「좌표 해소 규칙」을 둔다. 재작성은 plan-phase 산출물의 provenance를 흐리고, 규칙 하나면 전건이 결정적으로 해소된다 |
| **P3-1** | P3 | 추적 불가 증거 4지점(C-10·C-11·C-12 + `MacroAuthoringProbe.md:138`) | **닫힘** — C-10·C-11·C-12 내용을 아래에 전재하고, `server/prechk/macro.py`의 추적 불가 인용을 추적되는 좌표(`server/safety/classify.py` · `server/safety/blacklist.yaml` · 본 문서 접두 행)로 교체 |
| **P3-2** | P3 | `AC-PRECHK-015`에 실행 가능한 테스트 0건(위반은 아니나 후속 SPEC이 PRECHK PRESERVE를 깨도 스위트가 못 잡음) | **이월** — 선행 SPEC의 상시 테스트 선례(`server/tests/test_songcue_bundle.py:212`·`:216`)를 채택하는 것이 옳다. 본 SPEC의 AC는 절차로 규정했으므로 요구 위반이 아니며, 상시화는 별도 변경이라 이월한다 |
| **P3-3** | P3 | §E.2 M5의 *"두 어휘가 서로소"* 가 과장 — `server/looks/report.py:72`의 `UNADDRESSABLE`과 `server/prechk/macro.py`의 `GROUPS_UNADDRESSABLE`이 같은 사실을 말함 | **닫힘** — 아래 정정: 서로소는 **리포트의 판정 어휘 표**에 한정해 참이고, 사유 코드 층에는 의미가 겹치는 라벨이 1쌍 있다 |

### 뮤테이션 회계 (P2-3)

**M0와 M8은 `cycle_type=none`이며 코드 변경이 0건이다.** `design.md` §6.3이 그 두 마일스톤에 제안한 뮤테이션(*"매크로 저작 GO를 재조회 없이 기록한다"* · *"부정 판정에서 `DESCOPE:` 접두 행을 빼고 산문만 남긴다"* · *"툴을 거치지 않고 빌더를 직접 실행해 종단 검증한다"* · *"감사 로그 대조 없이 툴 반환만으로 검증한다"*)은 **코드 결함이 아니라 기록·절차 결함**이다. 주입 대상이 소스가 아니라 산출 기록이므로 코드 뮤테이션으로 집행할 수 없고, 그 대신 **기계 판정이 그 자리를 대신한다** — 접두 행 파싱(`server/tests/test_prechk_macro.py`의 `measured_authoring_literal`), 행 존재 판정(`server/tests/test_prechk_patch.py`), 감사 로그 대조(M8 하네스). **집행하지 않았고 그 사유가 이것이다** — 이전 기록에 이 사유가 없던 것이 감사 지적이며 여기서 채운다.

**계수 정정.** 개별 기재된 뮤테이션은 M1 3 · M5 5 · M6 5 · M7 2(+주입 3회) = **15건**이고, M2 8 · M3 6 · M4 6 = **20건은 집계 수치만** 있다. `mutations_executed: 34`는 그 둘을 합산하며 M7의 주입 3회를 중복 계산한 값이었다. 감사 후 신설한 뮤테이션 5건(P1·P2 수정의 방어)을 더해 정정값은 **개별 20 + 집계 20 = 40건**이다. **집계 20건은 개별 증거가 없으므로 "검증됨"으로 세지 않는다.**

### `ASSUMPTION-27` 주장 범위 정정 (P2-5)

접두 행과 출하 코드가 *"후보 12건 전건 부정"* 을 **무한정**으로 적었다. 정확한 주장은 이렇다 — **변경하지 않은 응답기 읽기 표면(`state`·`prop`) 위에서, 실제 발화한 프로퍼티명 집합에 한정해 0건.** 응답기는 프로퍼티명을 열거할 수 없으므로(`console/lua/copilot_responder.lua:204-217`) **어떤 프로퍼티 프로브 집합도 부재 증명이 될 수 없다.** 이것은 §E.3a 규율 1(*"불완전한 집합에 판정을 단정하지 않는다"*)이 같은 항목에서 두 번째로 미끄러진 형태다.

감사가 표에 없던 후보 2건을 열거했다. **둘 다 미측정이며 `NEGATIVE` 판정을 뒤집지 않는다** — 관측 없이 닫을 수 없고 어느 쪽이든 출하 형상의 축소(주소 중복만 수행)를 정당화한다.

| 후보 | 내용 | 왜 표에 없었나 |
|---|---|---|
| I-14 | `deploy` + `exec`로 콘솔측 프로브 플러그인을 올려 `handle:Get("FixtureType")`의 실제 반환 타입을 판독. 응답기의 닫힌 5동사 안이고 저장소 파일을 건드리지 않아 `console/lua/**` PRESERVE를 침범하지 않는다 | 추적 불가 부록에서 *"측정 가치가 없다"* 로 기각됐고 12행 표에 진입하지 않았다 |
| I-15 | 열거 가능한 모드 집합에 대한 **보수적 점유폭 상계** — 폭 ∈ {29, 31}, 실측 최소 주소 간격 42. 42 > 31이므로 연결 없이 겹침 0건이 증명된다 | C-9가 더 엄격한 게이트(*"전 모드 폭 동일"*)를 써서 배제했다. `server/prechk/patch.py`의 `FootprintPolicy`가 `enabled` 이진 게이트라 "경계 있는 폭" 형상을 표현할 수 없는 것이 구조적 이유다 |

**I-15는 후속 SPEC이 가장 먼저 볼 후보다** — 라이브 측정 없이 기존 실측만으로 구간 겹침을 되살릴 여지가 있다. 본 SPEC은 `FootprintPolicy`가 그 형상을 표현하지 못하고 `SKIPPED_CHECK_KIND`에 대응 부류가 없어 채택하지 않았고, 그 구조적 이유를 여기 남긴다.

### 추적 불가였던 후보 3건 전재 (P3-1)

| 후보 | 내용 | 기각 근거 |
|---|---|---|
| C-10 | `exec` 결과 문자열 파싱으로 타입·모드 해석 | **금지.** `plan.md` §A.2와 `research.md` §7.4가 `exec` 문자열 파싱 우회를 전수 배제. 코드로도 `build_exec_result`는 `Cmd()` 접수 결과만 분류한다(`console/lua/copilot_responder.lua:690-706`) |
| C-11 | 쇼파일 파일 직접 파싱 | **범위 밖.** `spec.md` §D Out of Scope · `research.md` §8 |
| C-12 | 콘솔 주소형 API(`ObjectList`)로 타입·모드 직접 해석 | **사망.** `resolve_path`가 특수 처리하는 주소형은 `Executor <n>` 하나뿐이다(`console/lua/copilot_responder.lua:467-486`). 다른 주소형 추가는 응답기 변경(PRESERVE 위반)이며 `Fixture <n>`은 `REQ-PRECHK-005`가 별도로 금지 |

### 증거 등급 규약 — §E.2의 절 단위 선언 (P2-6)

머리말이 선언한 태그(`[실측]`·`[코드]`·`[문서]`·`[미확정]`)를 §E.2는 인라인으로 쓰지 않았다. 소급 부착 대신 **절 단위 규약**을 선언한다.

- **M0 절과 M8 절, 그리고 M4 보강 측정** — 라이브 세션 기록이다. 그 안의 수치·응답 문자열·재조회 값은 **전부 `[실측]`** 이며 원시 산출물은 `.moai/state/verify/prechk-m0/steps.jsonl`과 `.moai/state/verify/prechk-m8/result.json`이다. 예외는 명시적으로 *"기전"* · *"내부 이유"* 로 적은 서술이며 그것은 `[추론]`이다.
- **M1·M2·M3·M4·M5·M6·M7 절** — 저장소 정적 사실과 명령 출력이다. 전부 `[코드]`이며 인용한 명령을 다시 돌리면 재현된다.
- **§E.2a(본 절)** — 감사 산출물 인용은 `[문서]`, 감사가 재현한 수치는 `[코드]`, 감사가 라이브를 재현하지 못한 항목은 감사 자신이 §5에 한계로 적었다.

**이 선언이 인라인 태그보다 약하다는 것을 인정한다.** 감사가 걸린 지점은 *"어느 주장을 재현할 수 있는가"* 였고, 절 단위 규약은 그 판별을 절 경계까지만 좁힌다. 후속 SPEC은 처음부터 인라인으로 붙이는 편이 낫다.

### 좌표 해소 규칙 (P2-7)

M6가 `server/orchestrator/tools.py`에 프리체크 import 블록과 `property_port`를 더해 파일이 아래로 밀렸다 — `_PROGRAMMER_STATE_COMMANDS`가 BASE의 247행에서 258행으로, `def run_commands`가 496행에서 517행으로 옮겼다. 그 결과 `plan.md` · `design.md` · `research.md`가 `server/orchestrator/tools.py`를 가리키는 좌표 **18건 중 17건**이 어긋났다.

**17건을 재작성하지 않는다.** plan-phase 산출물은 그 시점의 판단 기록이고, 사후 재작성은 *"무엇을 보고 그렇게 결정했는가"* 를 흐린다. 대신 규칙 하나를 둔다.

> **`plan.md` · `design.md` · `research.md`가 인용하는 `server/orchestrator/tools.py:<줄>` 좌표는 전부 BASE `95687a0` 기준이다.** 해소는 `git show 95687a0:server/orchestrator/tools.py`로 한다. 그 세 문서는 M6 이전에 작성됐고 M6가 같은 파일을 편집했으므로 HEAD 기준으로는 맞지 않는다. `progress.md`(run-phase가 직접 쓴 좌표)는 **HEAD 기준**이다.

**규약의 전제가 이 SPEC 자신에 의해 깨졌음을 기록한다.** 정본을 줄번호로 인용하지 않고 코드만 인용한 근거는 *"코드는 커밋 없이 움직이지 않는다"* 였다. 움직인 커밋이 본 SPEC의 것이다. **후속 SPEC은 자신이 편집할 파일의 좌표를 plan-phase에서 인용할 때 BASE 기준임을 명시하는 편이 낫다.**

### M5 라벨 재사용 서술 정정 (P3-3)

*"두 어휘가 서로소"* 는 **리포트의 판정 어휘 표**(`server/prechk/report.py`의 5개 표)에 한정해 참이다. 사유 코드 층으로 넓히면 `server/looks/report.py:72`의 `UNADDRESSABLE`(*"그룹은 있으나 번호가 없음"*)과 `server/prechk/macro.py`의 `GROUPS_UNADDRESSABLE`(*"그룹은 있으나 번호가 없어 대상으로 쓸 수 없습니다"*)이 **같은 사실을 말한다.** `AC-PRECHK-012` ④의 기계 요구(밑줄 식별자 직접 import 0건)는 충족되지만, *"재사용 지점 0건"* 이라는 서술은 그만큼 좁혀 적는 편이 정확하다.

### 뮤테이션 방법론 위험 1건 — 감사가 아니라 이 수정 사이클이 드러냈다

P1·P2 수정을 뮤테이션으로 검증한 직후 전체 스위트가 **존재하지 않는 실패**를 보고했다 — `server/prechk/macro.py:305`가 `Group 11 At 0`인데 테스트는 `Group 11 At 5`를 관측했다. 원인은 **stale `__pycache__`** 다. 뮤테이션 쓰기와 복구 쓰기가 같은 초 안에 일어나면 pyc가 기록한 소스 mtime(1초 해상도)이 복구된 소스의 mtime과 같아져 **캐시가 유효로 판정되고 뮤테이션된 바이트코드가 재사용된다.** `find server -name __pycache__ -type d -exec rm -rf {} +` 후 재실행하면 사라진다.

**이것은 뮤테이션 방법론의 실제 위험이다.** 복구 직후의 검증 실행이 뮤테이션 코드를 볼 수 있고, 반대로 **뮤테이션 실행이 복구된 코드를 볼 수도 있다** — 후자면 뮤테이션이 "살아남았다"로 오판된다. 본 사이클의 뮤테이션 5건은 각각 1 failed를 냈으므로 오판 방향이 아니었으나, **이후 뮤테이션 절차는 매 사이클 전후로 `__pycache__`를 지운다.**

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: audit-ready
base_sha: 95687a0
milestones_closed: 9   # M0~M8
assumption_verdicts:
  ASSUMPTION-25: GO
  ASSUMPTION-26: GO
  ASSUMPTION-27: NEGATIVE
  ASSUMPTION-28: GO
  ASSUMPTION-29: GO
  ASSUMPTION-30: NEGATIVE
prefix_rows: 6          # GO 4 · DESCOPE 2 · SKIP 0 · REOPEN 0
reopen_scope: 0
live_sessions: 3        # M0 프로브 · M8 종단 · M4 보강 (plan.md §C는 2회로 회계했고 감사 수정이 1회를 추가했다 — 사유는 §E.2a P1-1)
suite: "2721 passed · 5 skipped · 0 failed (감사 수정 반영)"
suite_baseline_at_kickoff: "2490 passed · 5 skipped · 0 failed"
tests_added: 231        # 스위트 델타 2721-2490. 파일별 verdicts 8 · inventory 44 · patch 42 · macro 75 · report 33 · tool 29
mutations_individually_recorded: 20   # M1 3 · M5 5 · M6 5 · M7 2 · 감사수정 5
mutations_aggregate_only: 20          # M2 8 · M3 6 · M4 6 — 개별 증거 없음(§E.2a P2-3). "검증됨"으로 세지 않는다
mutations_not_executed: "M0 4 · M8 2 — cycle_type=none이라 주입 대상이 소스가 아니라 기록·절차다. 사유는 §E.2a"
mutations_survived: 0
preserve_diff: "빈 출력 (git diff --stat 95687a0..HEAD -- <10경로>)"
preserve_gate_nonvacuity: "주입 3회 전건 적발 후 revert"
safety_diff_files: ["server/safety/console.py", "server/safety/gate.py"]
safety_diff_outside_approval: 0
ruff: "신규·변경 파일 clean · 기존 비-clean(server/safety/console.py E501 2건)은 BASE에서 이미 존재하므로 손대지 않음"
run_audit: "1회차 FAIL · 가중합 0.695 / 기준선 0.85 · 지적 14건(P1 4 · P2 7 · P3 3). P1 4건 + P2 5건 + P3 2건 닫힘 · P2 2건 부분 닫힘 · P3 1건 이월. 전문 사본은 §E.2a. 2회차를 열지 않은 근거도 §E.2a"
mode: "sub-agent — 폭 1(M0·M1) -> 폭 2(M2·M3 사슬 + M4) -> 폭 1(M5~M8). §F.1이 개정 근거를 기록"
user_touchpoints:
  - "server/safety/** 조건부 예외 — 승인(2026-07-29)"
  - "M0 라이브 세션 접근 가능성 — 승인·실측(2026-07-29)"
  - "M8 라이브 세션 접근 가능성 재확인 — 실측으로 충족(2026-07-30, roundtrip 3/3 PASS). 사용자가 착수 지시에서 차단 없음을 명시했고 접근 가능성은 기계 측정 대상이므로 재질의하지 않았다"
defects_found_and_fixed:
  - "M6: server.prechk.report.build_report가 server.looks.report의 동명 심볼을 가려 prepare_busking이 잘못된 함수를 호출(busking 12건 실패). 별칭으로 교정. 전체 스위트를 돌리지 않았으면 통과했다"
  - "M8: summary_ko의 incomplete 라벨이 missing_count 0에서도 '못 읽은 픽스처가 있다'고 단정. 라벨 교정 + 회귀 테스트 신설. 라이브 실행이 없으면 통과했다"
  - "M0: ASSUMPTION-27을 후보 부분집합 위에서 부정 단정. scout 지적으로 후보 전수 12건을 닫은 뒤 재확정. 그 뒤 run-audit가 12건도 전수가 아님을 지적해 주장 범위를 좁혔다(§E.2a P2-5)"
  - "M4: 소등 라인 'Group <n> At 0'이 M0 미실측 리터럴이었다(REQ-PRECHK-012 위반). run-audit 적발 -> M4 보강 라이브 세션에서 측정해 정본에 등재. 게이트가 페이로드를 대조 전에 지우고 ON만 필터해 구조적으로 못 잡던 것도 고쳤다"
  - "M6: 그룹 풀 판독 실패를 '리그에 그룹이 없다'로 보고하고 is_error=False를 냈다 — M8 라벨 결함과 같은 계열. run-audit 적발 -> 오류로 답한다"
  - "M6: _free_macro_slot이 childCount를 보지 않아 절단된 풀에서 점유 슬롯을 골라 기존 매크로를 덮어쓸 수 있었다 — 본 SPEC의 유일한 쓰기 경로가 본 SPEC의 1급 요구를 어긴 지점. run-audit 적발 -> 계수 비교 추가"
  - "M6: AC-PRECHK-014 ④의 LiveLock 강등이 구현·테스트에 없었다(형제 툴 2개에는 있음). run-audit 적발 -> 강등 + 회귀 테스트 3건"
  - "M4: 그룹 열거가 전부 절단돼도 '그룹이 없다'로 단정했다. run-audit 적발 -> 절단으로 답한다"
carried_forward:
  - "FID 의미 — 슬롯 != FID로 패치된 쇼파일이 선행 조건(사용자 GUI 작업). 본 SPEC은 FID를 판정 근거에서 배제한 형상으로 출하"
  - "희소 풀에서 design.md 슬롯 A의 1..childCount 캡이 과소복구한다 — 이번 쇼파일이 조밀했을 뿐"
  - "익스큐터 인덱스 정의역 상한 미확정"
  - "Assign ... At Executor <N>의 page 성분 누출 기전(비단사 사상)의 내부 이유"
  - "ASSUMPTION-30의 프리셋 효과는 GO로 실측됐으나 page >= 2 일반화 부정으로 축이 꺼짐 — 후속 SPEC이 쓸 수 있는 실측"
new_measurements_for_successors:
  - "DataPool/PresetPools 생존(14개) · DataPool/Presets·AllPresets 사망 재확인"
  - "DataPool 최상위 자식 16종 · Patch 루트 자식 14종 전량 열거"
  - "ASSUMPTION-7(자식 풀 슬롯)이 분기 (a) probe_slots로 충족됨을 갭 풀(DataPool/Pages/1)로 실측"
live_sessions_total: 3   # M0 프로브 · M8 종단 · M4 보강(소등 페이로드 측정). 셋 다 쇼파일 원상 복구 확인
next: "run-audit 1회차 FAIL을 지적 14건 처리로 닫았다. **2회차를 열지 않는 근거**: P1 4건이 전부 코드 결함이었고 각각 뮤테이션으로 방어를 확인했으며(5건 전건 사망, 비공허 동반), 계수·경계·회귀 층은 1회차가 이미 전건 재현으로 통과시켰다. 남은 열린 항목은 P2-3의 집계 20건(증거 부재 — 재집행하면 원래 주장을 검증하는 것이 아니게 된다)과 P3-2(PRESERVE 상시 테스트, 이월)뿐이며 둘 다 코드 정합이 아니라 기록·강화 층이다. 다음은 sync-phase(§E.4)다."
```

## §E.3a 핸드오프 — 다음 단계 착수 지시 (2026-07-30)

> **이 절은 §E.5가 대체한다(2026-07-30).** 작성 시점은 **run-audit 이전**이며 그 「다음 단계」 3단(run-audit → sync-phase → PR)은 **전건 집행됐다.** 남긴 이유는 두 가지다 — (1) *"감사를 세울 것을 권고한다"*는 판단이 실제로 P1 4건을 잡았으므로 그 권고가 옳았다는 기록이고, (2) 규율 11건과 후속 SPEC 후보표는 여전히 유효하다. **현재 상태와 다음 단계는 §E.5를 본다.**

### 지금 어디까지 왔나

**run-phase 완결.** M0부터 M8까지 9개 마일스톤 전건 닫힘. `REOPEN_SCOPE` 0건이므로 범위 재개정 없이 출하 형상이 확정됐다. 다음은 **sync-phase**이며 그 앞에 **run-audit**를 세울 것을 권고한다.

| 마일스톤 | 산출 | AC | 상태 |
|---|---|---|---|
| M0 라이브 프로브 | 판정 6건(접두 행 6) | AC-PRECHK-016 | 닫힘 |
| M1 초크포인트 | 승인된 4지점 + `server/prechk/query.py` | AC-PRECHK-013 | 닫힘 |
| M2 인벤토리 | `server/prechk/inventory.py` | AC-PRECHK-001 · AC-PRECHK-002 · AC-PRECHK-003 · AC-PRECHK-004 | 닫힘 |
| M3 패치 정합성 | `server/prechk/patch.py` | AC-PRECHK-005 · AC-PRECHK-006 · AC-PRECHK-007 · AC-PRECHK-008 · AC-PRECHK-009 | 닫힘 |
| M4 매크로 | `server/prechk/macro.py` | AC-PRECHK-010 · AC-PRECHK-011 | 닫힘 |
| M5 리포트 | `server/prechk/report.py` | AC-PRECHK-012 | 닫힘 |
| M6 툴 배선 | `precheck_patch` in `server/orchestrator/tools.py` | AC-PRECHK-014 | 닫힘 |
| M7 회귀·PRESERVE | 게이트 실증 | AC-PRECHK-015 | 닫힘 |
| M8 종단 라이브 | `.moai/state/verify/prechk-m8/result.json` | AC-PRECHK-017 | 닫힘 |

**AC 17건 전량 PASS.** 소프트웨어 15건은 기계 검증, 라이브 2건(AC-PRECHK-016 · AC-PRECHK-017)은 실물 grandMA3 onPC 2.4.2 세션.

### 재개 시 검증할 전제 (어긋나면 멈추고 보고할 것)

```
git branch --show-current  -> feature/SPEC-COPILOT-PRECHK-001
git log --oneline -1       -> 본 핸드오프 커밋 (§E.3a 추가). 그 부모가 f8619f8 (M8 종단 라이브 + run-phase 신호)
git status --short         -> 비어 있음
git rev-parse --short origin/main -> 95687a0 · ahead 25 / behind 0
원격 PRECHK 브랜치 없음(미푸시) · 열린 PR 없음
uv run pytest server/tests/ -q -> 2711 passed · 5 skipped · 0 failed
OSC: send 8000 / receive 9005 (기본 9000 아님) · 응답기 v1.5.0
```

**BASE는 `95687a0`이며 협상 불가다** — `AC-PRECHK-015` ①의 `git diff --stat <BASE>..HEAD` 게이트가 쓰는 유일한 기준점이다. 인자 없는 `git diff`로 대체하면 위반이 커밋돼 있어도 0행을 내며 게이트가 통째로 무력해진다(M7이 실측으로 증명).

### 다음 단계 — 이 순서

**[1] run-audit (권고 · 미착수).** 작성자가 아닌 주체가 §E.2와 산출 코드를 채점한다. 근거: plan-audit 1회차가 **FAIL 0.76**으로 지적 11건을 냈고, 이번 run-phase에서도 독립 scout가 내 오류 2건을 잡았다. 반면 내 자체 게이트는 오탐 2건(`'2.351'`의 `, 351`을 축약 토큰으로 · 셀렉터 오류의 `no tests ran`을 뮤테이션 사망으로)을 냈다. **자기 감사의 한계가 이 세션에서 실측됐다.**
  감사에 특히 볼 것을 지목한다 — (a) M0 판정 6건의 `effect=` 증거가 재조회에서 나온 것인지, (b) `ASSUMPTION-27` 후보 12건이 실제로 전수인지, (c) 뮤테이션 34건이 각각 해당 AC를 죽였는지와 비공허성 동반 여부, (d) `server/safety/**` hunk가 승인 4지점을 벗어나지 않는지.

**[2] sync-phase.** SONGCUE의 §E.4 형상을 따른다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md:823-853`). 갱신 대상과 각각의 근거:

| 대상 | 편집 | 근거 |
|---|---|---|
| `CHANGELOG.md` | `[Unreleased] Added` 최상단에 PRECHK 항목 | SONGCUE가 같은 자리에 있다 |
| `.moai/specs/SPEC-COPILOT-PRECHK-001/spec.md` frontmatter | `status: draft` → `completed` | 선례 동일 |
| **`spec.md` §C 조건부 예외 문단** | *"이 예외는 아직 승인되지 않았다"* 를 **승인·집행 완료**로 정정 | **필수** — 현재 문장이 실제와 어긋난다. 승인은 2026-07-29이고 M1이 4지점을 집행했다 |
| `acceptance.md` 상태 줄 | `status: completed` · AC 17/17 PASS 명시 | 선례 동일 |
| `progress.md` §E.4 | sync 신호 작성 | 본 문서 |

**`spec.md` 버전 판단이 열려 있다.** SONGCUE는 PRESERVE 목록을 실제로 개정해 `0.1.0` → `0.2.0`을 올렸다. PRECHK는 **PRESERVE 목록 자체를 바꾸지 않았다** — 조건부 예외가 이미 v0.1.0 본문에 있었고 승인 상태만 바뀌었다. 그래서 (i) 승인 상태 문장 정정을 편집으로 보고 `0.2.0`을 올리는 안과 (ii) 목록 불변이므로 `0.1.0`을 유지하는 안이 갈린다. **sync 착수자가 결정하고 사유를 §E.4에 적는다.**

**갱신하지 않을 것도 미리 적는다** — `plan.md` · `design.md` · `research.md` 본문(소유권 매트릭스상 sync는 고치지 않는다) · `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md`(역사적 스냅샷이며 선행 3 SPEC도 갱신하지 않았다) · `README.md`(**실측으로 확정** — `precheck_patch` 언급 0건이고 툴 목록 서술이 없어 갱신 대상이 아니다. SONGCUE가 같은 근거로 제외한 선례를 따른다).

**[3] PR.** `feature/SPEC-COPILOT-PRECHK-001` → `main`. **원격에 브랜치가 없으므로 push가 선행한다.** `origin/main`이 `95687a0`이고 behind 0이므로 리베이스 불필요 — 선행 SPEC들이 이미 머지된 위에 스택돼 있지 않은 단일 브랜치다.

### 후속 SPEC 후보 — 우선순위와 각각의 벽

| 후보 | 상태 | 벽 |
|---|---|---|
| **FID 축** | 착수 가능하나 **사용자 GUI 작업이 선행** | 슬롯 ≠ FID로 패치된 쇼파일이 필요하다(`console/lua/PROTOCOL.md:322-324`). 현재 쇼파일은 슬롯과 FID가 같아 어떤 라이브 세션도 닫을 수 없다. **※ 2026-08-07 정정 — 선행 조건이 이미 충족됐을 가능성**: GROUPGEN M6가 슬롯 ≠ fid 리그를 실측했다(`SPEC-COPILOT-GROUPGEN-001/progress.md:424-426` — 슬롯 1..20 → fid 20..39). **착수 전 현 쇼파일 상태를 재확인할 것** |
| ~~구간 겹침 재개~~ | **출하 완료(2026-08-07 정정) — `SPEC-COPILOT-OVERLAP-001`(`spec.md:5` `status: completed`)** | 상계 형태로 출하됐다 — 모드 최대폭 `W`로 *"갭 ≥ W이면 겹칠 수 없다"* 만 증명한다. **정확폭 조인은 여전히 0건**이며(후보 12건 전건 부정, §E.2) 그 비대칭이 설계의 핵심이다(`server/prechk/footprint.py:1-15`). 다른 쇼파일·다른 응답기 버전에서 재측정할 때 **무엇을 이미 시도했는지** §E.2의 표를 먼저 읽을 것 |
| **페이지·익스큐터 저작** | `ASSUMPTION-28`·`ASSUMPTION-29` GO · `ASSUMPTION-30` 부정 | 저작은 되지만 `Assign … At Executor <N>`이 **page 성분을 page 1 인덱스 공간으로 누출**한다(비단사 사상). **선행 조건 정정(2026-08-07): 막는 것은 안전 설계가 아니라 빈 익스큐터 식별이다** — `SPEC-COPILOT-BUSKWIZ-001/progress.md:306`이 *"비어 있음"과 "존재하지 않음"이 구별되지 않음*을 부정 실측으로 확정했다. 안전 설계는 그 다음 문제다. **자동 배치는 불가**이며, 사용자가 번호를 명시 지정하는 축소형은 `SPEC-COPILOT-FXLIB-001/spec.md:98`(REQ-FXLIB-013)이 **이미 출하했다** |
| ~~프리셋 읽기~~ | **소비자 출하 완료(2026-08-07 정정)** — `server/paperwork/data.py:196-206` `build_preset_list` | `DataPool/PresetPools/<풀>`이 정답이고 `DataPool/Presets`는 사망이다. 추측으로 경로를 고르지 말 것 |
| SONGCUE 잔여 | 미착수 | 벽에 걸리지 않는다 |
| ~~P2-4 자동 페이퍼워크~~ | **출하 완료(2026-08-07 정정) — `SPEC-COPILOT-PAPERWORK-001`**(`server/paperwork/`) | **이 행의 원래 판정이 틀렸다.** 페이퍼워크는 큐 내용 벽에 막혀 있지 않았고, **쇼파일 파서 없이 라이브 질의 포트만으로** 출하됐다(`server/paperwork/data.py:1-11`). 출하 3종은 patch sheet · cue sheet · preset list. **미포함 3건과 그 사유**: ① **매직시트** — 그룹 멤버십이 MA3 플랫폼상 판독 불가(`SPEC-COPILOT-GROUPGEN-001/spec.md:361-363`) ② **훅업 차트의 채널 범위** — 정확 채널폭 조인 0건, 상계 표기까지만 ③ **큐시트의 "얼마나 밝나"** — `CueFade`와 큐 내용은 반환 경로가 없다(`SPEC-COPILOT-SCENE-001/spec.md:231-232`) |
| P2-5 볼런티어 런북 | 미착수 | **불가-축소.** 큐의 **내용(저장된 값)** 은 반환 경로가 존재하지 않는다(`SPEC-COPILOT-SCENE-001/spec.md:232`). 단 **벽이 부분적으로 무너졌다** — 응답기 v1.5.0의 `prop` 동사로 `TrigType`/`TrigTime`은 읽힌다(`:230`). 실현형은 큐 **이름 + `cueNo` + `TrigType`/`TrigTime`**까지의 진행표이며, *"다음 Go가 무엇을 하는가"* 는 **앱이 직접 만든 큐에 한해서만** 답할 수 있다(생성 시점 지식 보관) |

### 이 세션에서 확립되어 반복할 규율

1. **불완전한 집합에 판정을 단정하지 않는다.** 내가 `ASSUMPTION-27`을 후보 부분집합 위에서 부정 단정했고 scout가 잡았다. `REQ-PRECHK-010`이 금지하는 바로 그 형태를 요구 작성자가 반복했다.
2. **종료 코드만 보고 뮤테이션 사망을 세지 않는다.** `no tests ran`도 비영 종료 코드를 낸다. 통과 잔여 건수를 함께 보고해 비공허성을 보인다.
3. **임포트를 깨뜨리는 뮤테이션은 무효다.** 전면 실패는 게이트가 잡은 것이 아니다. 미실행 경로에 심어 스캔이 **정확히 해당 테스트만** 죽이는지 본다.
4. **전체 스위트를 돌린다.** 신규 파일만 돌린 M6는 21 passed였고 그 상태에서 `build_report` 심볼 가림 버그로 busking 12건이 죽어 있었다.
5. **라이브 종단 실행은 유닛이 못 잡는 것을 잡는다.** `summary_ko`의 거짓 서술은 인메모리 테스트 32건을 전부 통과했다.
6. **`node.childCount`와 `len(children)`을 함께 본다.** `truncated`는 '불완전하다'만 말하고 '얼마나'를 말하지 않는다.
7. **비파괴 프로브로 판정 불가면 생성 프로브를 쓴다.** 단 쇼파일을 원상 복구하고 **재조회로** 베이스라인 일치를 확인한다. M0는 5지점을 바꾸고 전건 복구했다.
8. **부정 프로브로 문법 존부를 판정하지 않는다.** 날조 키워드도 `Illegal object`를 준다. 다만 `Illegal value` · `Illegal property` · `Cannot Create Object` · `User Canceled Command`는 변별적이다(scout 실측).
9. **병렬은 계약이 닫힌 뒤에만.** 공유 계약(`server/prechk/verdicts.py`)은 스폰 이전에 오케스트레이터가 직접 만든다. 읽기 전용 scout 병렬은 항상 안전하고 실제로 값을 냈다.
10. **위임 전 `spec.md` §C PRESERVE 정본을 읽는다.** `plan.md`의 좁은 목록만 보면 SONGCUE가 겪은 응답기 오지시가 반복된다.
11. **라이브 세션에서 코드를 고치지 않는다.** M8의 라벨 결함은 스택을 닫은 뒤 고쳤다.

## §E.4 Sync-phase Audit-Ready Signal

```yaml
sync_status: audit-ready
sync_complete_at: 2026-07-30
gate_sync_1: "PASS — 작업 트리에 sync 편집 외 잔여 0, `uv run pytest server/tests/ -q` 2721 passed · 5 skipped · 0 failed (오케스트레이터 직접 실측, `__pycache__` 정리 후)"
artifacts_updated:
  - "CHANGELOG.md — `[Unreleased] Added` 최상단에 PRECHK 항목(M0~M8 + M0 안전 관련 실측 2건 + 부수 폐쇄 3건 + 자체 발견 결함 3건 + run-audit P1 4건 + 정직한 잔여 6건)"
  - "spec.md frontmatter — status: draft -> completed, updated: 2026-07-30. **version은 0.1.0 유지**"
  - "spec.md §C — 조건부 예외의 승인 상태를 '아직 승인되지 않았다'에서 '승인·집행 완료(승인 2026-07-29 · 집행 2026-07-30)'로 정정하고 hunk 내역 참조를 추가. 거부 분기 서술은 후속 SPEC의 선례로 남겼다"
  - "acceptance.md 상태 줄 — status: completed, AC 17/17 PASS 명시 + run-audit 처리 기록 참조"
  - "acceptance.md `AC-PRECHK-006` ④ · design.md §6.1 `clean_rig_18` 행 — 실제 픽스처와 어긋난 서술을 '의도적 합성·열거 완전'으로 정정(run-audit P2-4)"
  - "progress.md §E.2a(run-audit 처리) · §E.3(run-phase 신호 정정) · §E.3a(핸드오프) · 본 절"
artifacts_unchanged:
  - "README.md — `precheck_patch` 언급 0건이고 툴 목록 서술이 없어 갱신 대상 아님(실측 확인). SONGCUE가 같은 근거로 제외한 선례"
  - "docs/proposals/2026-07-26-lighting-direction-feature-proposal.md — P2-6을 제안으로 서술한 역사적 스냅샷이며 살아 있는 상태 문서가 아니다. 선행 3 SPEC도 갱신하지 않았다"
  - "plan.md · design.md · research.md 본문 — sync는 고치지 않는다(소유권 매트릭스). design.md §6.1은 예외이며 정본 정합 정정이라 위 목록에 있다"
spec_version_decision:
  kept: "0.1.0"
  reason: "SONGCUE는 PRESERVE **목록을 실제로 개정**해 0.2.0을 올렸다(REQ 개정 주석 동반). PRECHK는 목록도 REQ 20건도 Out of Scope도 **바꾸지 않았다** — 조건부 예외는 이미 v0.1.0 본문에 있었고 바뀐 것은 그 **승인 상태의 기록**이다. 상태 기록 갱신에 버전을 올리면 버전이 규범 변경 신호로서의 의미를 잃는다. `updated` 필드가 그 변화를 담는다"
spec_divergence:
  requirements_implemented: "20/20"
  scope_reductions: 0
  scope_additions: 0
  descoped_by_live_verdict: "2건 — ASSUMPTION-27(구간 겹침 미수행) · ASSUMPTION-30(page >= 2 일반화). 둘 다 `DESCOPE:` 접두 행으로 기록되고 리포트의 `skipped_checks`가 사용자에게 축소를 말한다. 매크로 축(ASSUMPTION-26)은 GO이므로 산출물 2는 성립한다"
  live_sessions: "3 — plan.md §C가 2회로 회계했고 run-audit P1-1 수정이 M4 보강 1회를 추가했다. 계획 초과이며 그 사유가 §E.2a에 있다"
honest_residuals:
  - "`FID` 의미는 현재 쇼파일로 닫을 수 없다(슬롯 == FID). 슬롯 != FID로 패치된 쇼파일이 선행 조건이며 사용자 GUI 작업이다"
  - "무응답 픽스처 자동 탐지는 관측 경로가 존재하지 않아 DESCOPE — 제안서 원문의 요구였고 사용자 확정으로 범위에서 제외됐다"
  - "구간 겹침 미수행. run-audit가 추가 후보 2건을 열거했고 그중 보수적 점유폭 상계는 **라이브 측정 없이** 되살릴 여지가 있다 — FootprintPolicy가 이진 게이트라 그 형상을 표현하지 못하는 것이 구조적 이유다"
  - "희소 풀에서 design.md 슬롯 A의 `1..childCount` 캡이 과소복구한다 — 이번 쇼파일이 1..19 조밀했을 뿐이다"
  - "M2·M3·M4의 뮤테이션 20건은 집계 수치만 남아 개별 증거가 없다(워커 로그가 `.gitignore:206` 아래). '검증됨'으로 세지 않았고 재집행하지도 않았다 — 재집행은 다른 사람이 다른 뮤테이션을 돌린 것이 되어 원래 주장을 검증하지 못한다"
  - "`AC-PRECHK-015`의 PRESERVE 게이트가 상시 테스트가 아니다(1회성 수동 절차) — 후속 SPEC이 PRECHK의 PRESERVE를 깨도 스위트가 잡지 못한다. 선행 SPEC에 상시화 선례가 있으므로 채택이 옳고 이월한다"
  - "라이브 원문 로그가 `.moai/state/`(`.gitignore:206`) 아래에만 있다 — 커밋되는 사본은 §E.2와 §E.2a이며 그래서 커맨드·응답 문자열을 요약 없이 전재했다. run-audit도 이 한계를 §5에 적었다"
orchestrator_errors_recorded: "4건 — (1) `ASSUMPTION-27`을 후보 부분집합 위에서 부정 단정(발견자는 읽기 전용 scout, 그 뒤 run-audit가 12건도 전수가 아님을 재지적). (2) `server.prechk.report.build_report`가 동명 심볼을 가려 busking 12건을 깨뜨렸다 — 신규 파일만 돌려서 놓쳤고 전체 스위트가 잡았다. (3) `summary_ko`의 incomplete 라벨이 거짓을 말했다 — 인메모리 32건을 통과했고 라이브 종단만이 잡았다. (4) §F.1을 추가하면서 내 M1 테스트의 §F 파싱을 깨뜨렸다 — 워커가 수리했다. 추가로 절차 실수 1건: 뮤테이션 복구 직후 `__pycache__`를 지우지 않아 유령 실패를 쫓았다(§E.2a에 방법론 위험으로 기록)"
pr: "**#7 OPEN · MERGEABLE** — https://github.com/jjjh7401/AI-Lighting_Console/pull/7 · feature/SPEC-COPILOT-PRECHK-001 -> main · +7671/-5 · 27파일. push는 2026-07-30에 수행했고(원격에 브랜치가 없었다) `origin/main`이 95687a0에 behind 0이라 리베이스는 불필요했다. **머지 전략은 merge commit으로 사용자가 확정** — 개별 커밋이 M0~M8 마일스톤 경계와 run-audit 수정을 구분해 담아 '무엇이 계획된 구현이고 무엇이 감사 지적의 결과인가'가 이력에서 읽힌다. 커밋 27개 중 2건은 M7의 PRESERVE 게이트 비공허성 실증 주입·revert 쌍이며 그것도 게이트 작동의 기록이다. `auto_pr: false`(`.moai/config/sections/git-strategy.yaml`)이므로 사용자 확인 후 수동 생성했다"
next: "**PR #7 리뷰·머지 대기.** 머지 후 후속 SPEC 착수 순서는 §E.3a의 후보표를 따른다 — FID 축은 사용자 GUI 작업(슬롯 != FID 쇼파일)이 선행하고, 구간 겹침 재개는 run-audit가 추가한 후보 I-15(보수적 점유폭 상계)가 **라이브 측정 없이** 되살릴 여지가 있어 가장 값싸며, 페이지·익스큐터 저작은 `Assign … At Executor <N>`의 비단사 사상 때문에 안전 설계가 선행 조건이다. 이월 1건(`AC-PRECHK-015` PRESERVE 상시 테스트)은 다음 SPEC의 M7에 흡수하는 편이 자연스럽다."
```

## §E.5 핸드오프 2회차 — PR 이후 (2026-07-30)

> **이것이 현재 상태의 정본이다.** §E.3a는 run-audit 이전에 쓰였고 그 다음 단계는 전건 집행됐다. `.moai/state/`는 커밋되지 않으므로 재개에 필요한 사실은 전부 여기와 §E.2 · §E.2a에 있다.

### 실측한 현재 상태

```
git branch --show-current  -> feature/SPEC-COPILOT-PRECHK-001
git log --oneline -1       -> 12ad143 (PR #7 기록) 또는 그 이후의 §E.5 커밋
git status --short         -> 비어 있음
origin/main                -> 95687a0 · ahead 28 / behind 0 (리베이스 불필요)
uv run pytest server/tests/ -q -> 2721 passed · 5 skipped · 0 failed
PR #7                      -> OPEN · mergeable=MERGEABLE · mergeState=CLEAN · reviewDecision 없음
CI                         -> **체크 0건** (`gh pr checks 7` -> no checks reported)
```

**phase 진행**: plan 완결 → run 완결(M0~M8) → **run-audit 1회차 FAIL 0.695 → 지적 14건 처리** → sync 완결 → **PR #7 열림**. 열린 사용자 접점 0건.

### 이 저장소에 CI가 없다 — 다음 단계를 바꾸는 사실

`gh pr checks 7`이 *"no checks reported"* 를 낸다. **PR을 자동으로 검증하는 것이 아무것도 없다.** 귀결 셋:

1. **머지 전 유일한 관문은 사람 리뷰다.** 로컬 검증(스위트 2721 · ruff · PRESERVE 게이트 · 뮤테이션)은 전부 **내가 돌린 것**이고 PR에 증거로 붙어 있을 뿐 재실행되지 않는다.
2. **후속 SPEC이 PRECHK의 PRESERVE를 깨도 아무것도 막지 않는다.** `AC-PRECHK-015`의 게이트가 1회성 수동 절차인 것과 겹쳐 위험이 이중이다(이월 항목 P3-2).
3. **그래서 독립 코드 리뷰가 값이 있다.** run-audit는 **SPEC 프로세스**를 채점했다(요구-AC 정합 · 증거 · 경계). 코드 품질·보안 축은 아직 아무도 보지 않았다 — 감사 자신도 §5에서 좌표 검증이 표본이었음을 적었다.

### 다음 단계 — 3안

| # | 안 | 근거 | 비용 |
|---|---|---|---|
| **1** | **PR #7 독립 코드 리뷰** (권고) | CI가 0건이므로 코드 품질·보안 축을 본 주체가 없다. run-audit는 프로세스 축이었다. 리뷰 대상은 `server/prechk/` 7파일 + `server/orchestrator/tools.py` 핸들러 + `server/safety/` 4지점 | 중 |
| 2 | 바로 머지 | 로컬 검증이 두텁고(스위트 2721 · 뮤테이션 · 게이트 실증) run-audit가 경계·회귀 층을 0.94로 통과시켰다. `mergeState=CLEAN` | 소 |
| 3 | 후속 SPEC 선행 조사 | PR 리뷰를 기다리는 동안 **라이브 세션이 필요 없는** 후보 I-15를 조사할 수 있다 | 중 |

**1과 3은 동시에 가능하다** — 리뷰는 읽기 전용이고 I-15 조사도 읽기 전용이라 충돌이 없다. 2를 먼저 하면 1의 지적이 main에 들어간 뒤에 오므로 후속 커밋이 된다.

### 후속 SPEC 우선순위 — run-audit가 순서를 바꿨다

| 순위 | 후보 | 왜 이 순위인가 | 선행 조건 |
|---|---|---|---|
| **1** | ~~구간 겹침 재개 (후보 I-15)~~ — **출하 완료, `SPEC-COPILOT-OVERLAP-001`(2026-08-07 정정)** | run-audit가 열거한 **보수적 점유폭 상계** — 폭 ∈ {29, 31}이고 실측 최소 주소 간격이 42이므로 **42 > 31로 겹침 0건이 연결 없이 증명된다.** `ASSUMPTION-27` 부정을 우회하지 않고 **라이브 측정 없이** 기능을 되살릴 여지가 있는 유일한 후보다 | **없음** — 기존 실측만으로 착수 가능. 구조적 장애는 `FootprintPolicy`가 `enabled` 이진 게이트라 "경계 있는 폭"을 표현하지 못하는 것과 `SKIPPED_CHECK_KIND`에 대응 부류가 없는 것 |
| **2** | `AC-PRECHK-015` PRESERVE 게이트 상시화 | CI가 0건인 저장소에서 PRESERVE를 지키는 유일한 수단이 상시 테스트다. 선행 SPEC에 선례가 있다(`server/tests/test_songcue_bundle.py`의 `test_preserve_look_files_are_unchanged_from_run_phase_base`) | 없음 — 다음 SPEC의 M7에 흡수하는 편이 자연스럽다 |
| 3 | 페이지·익스큐터 저작 | `ASSUMPTION-28`·`ASSUMPTION-29` GO로 저작은 가능하다. 그러나 `Assign … At Executor <N>`이 **page 성분을 page 1 인덱스 공간으로 누출**한다(비단사 사상 — `Executor 201`이 page 1 인덱스 101을 조용히 덮었다) | **선행 조건 정정(2026-08-07): 빈 익스큐터 식별이 먼저다** — `SPEC-COPILOT-BUSKWIZ-001/progress.md:306`이 식별 불가를 부정 실측으로 확정했다. 안전 설계는 그 다음이다. 자동 배치는 불가이며 사용자 명시 지정 축소형은 `SPEC-COPILOT-FXLIB-001/spec.md:98`이 이미 출하했다 |
| 4 | FID 축 | `REQ-PRECHK-005`가 배제한 것을 되살리면 픽스처 개별 선택이 열린다 | **사용자 GUI 작업** — 슬롯 ≠ FID로 패치된 쇼파일이 필요하다(`console/lua/PROTOCOL.md:322-324`). **※ 2026-08-07 — GROUPGEN M6가 슬롯 ≠ fid 리그를 실측했다(`SPEC-COPILOT-GROUPGEN-001/progress.md:424-426`). 충족 여부 재확인 필요** |
| 5 | ~~프리셋 읽기~~ | 살아 있는 경로가 `DataPool/PresetPools/<풀>`로 실측 확정됐다 | **소비자 출하 완료(2026-08-07 정정)** — `server/paperwork/data.py:196-206` `build_preset_list` |
| 6 | ~~P2-4 자동 페이퍼워크~~ | 제안서의 남은 항목 | **출하 완료(2026-08-07 정정) — `SPEC-COPILOT-PAPERWORK-001`.** 큐 내용 벽에 막혀 있지 않았고 라이브 질의 포트로 출하됐다. 미포함: 매직시트(멤버십 판독 불가) · 훅업 채널 범위(정확폭 0건) · 큐시트의 "얼마나 밝나"(`CueFade`·큐 내용). 상세는 §E.3a 후보표 |
| 7 | P2-5 볼런티어 런북 | 제안서의 남은 항목 | **불가-축소.** 큐 내용은 반환 경로가 없다(`SPEC-COPILOT-SCENE-001/spec.md:232`). `TrigType`/`TrigTime`은 v1.5.0 `prop`으로 읽힌다(`:230`) — 실현형은 이름 + `cueNo` + 트리거까지의 진행표 |

### 규율 — §E.3a의 11건에 이번 사이클이 더한 4건

12. **독립 감사를 실제로 세운다.** 권고로 남기면 집행되지 않는다. 이번 run-audit가 **P1 4건**을 냈고 그중 하나는 **유일한 쓰기 경로가 기존 데이터를 덮어쓸 수 있는** 결함이었다. 작성자의 자체 게이트는 같은 세션에서 오탐 2건을 냈다.
13. **게이트가 결함을 "비껴가는" 형태를 의심한다.** 테스트가 있는데도 통과한 결함이 2건이었다 — 대조 전에 페이로드를 지우는 정규화, 한 페이즈만 보는 필터. **테스트 존재는 커버를 뜻하지 않는다.**
14. **뮤테이션 사이클마다 `__pycache__`를 지운다.** 복구 쓰기가 같은 초 안에 일어나면 pyc의 mtime 검증(1초 해상도)을 통과해 **뮤테이션된 바이트코드가 재사용된다.** 유령 실패를 쫓게 되고, 반대 방향이면 **뮤테이션이 살아남았다고 오판된다.**
15. **"판독 실패"와 "그런 것이 없음"을 절대 섞지 않는다.** 이번에 같은 계열 결함이 **3건** 나왔다(완전성 라벨 · 그룹 풀 판독 실패 · 그룹 열거 전부 절단). 코드가 방어 가능해도 **사용자가 읽는 문자열이 거짓**이면 결함이다. 새 판독 경로를 추가할 때마다 이 질문을 한다 — *"읽지 못했을 때 이 문자열이 여전히 참인가?"*

## §E.6 다음 세션 착수 키트 (2026-07-30)

> §E.5가 **무엇을 할지**를 적었다. 이 절은 **바로 착수할 수 있게** 재발견 비용을 0으로 만든다 — 검증 커맨드, 산출물 인벤토리, 두 트랙의 실행 브리프.

### 1. 착수 전 검증 (커맨드와 기대값)

```
git branch --show-current                       -> feature/SPEC-COPILOT-PRECHK-001
git status --short                              -> 비어 있음
git rev-list --left-right --count origin/main...HEAD -> 0  29   (behind 0 / ahead 29)
gh pr view 7 --json state,mergeStateStatus      -> OPEN · CLEAN
gh pr checks 7                                  -> no checks reported  (CI 없음 — 의도된 사실)
find server -name __pycache__ -type d -exec rm -rf {} + ; uv run pytest server/tests/ -q
                                                -> 2721 passed · 5 skipped · 0 failed
```

**어긋나면 멈추고 보고한다.** 특히 `behind`가 0이 아니면 누군가 main을 진행시킨 것이므로 리베이스 판단이 선행한다.

라이브 세션이 필요한 작업이면 추가로:
```
uv run python -m server.tools.responder_roundtrip --listen-port 9005 --wait 5 --expect-version 1.5.0
                                                -> 3/3 PASS · version=1.5.0
```
**OSC는 send 8000 / receive 9005다**(기본 9000이 아니다 — 이 값을 안 읽어 선행 SPEC이 오진 1건을 냈다).

### 2. 산출물 인벤토리 — 무엇이 살아남고 무엇이 사라지나

| 산출물 | 위치 | 추적? | 신규 클론에서 |
|---|---|---|---|
| 요구·인수·설계·계획·진행 6문서 | `.moai/specs/SPEC-COPILOT-PRECHK-001/` | **추적됨** | 있음 |
| 구현·테스트 | `server/prechk/` · `server/tests/test_prechk_*.py` | **추적됨** | 있음 |
| M0 라이브 원문 로그 | `.moai/state/verify/prechk-m0/steps.jsonl` (152KB, 266+ 레코드) | `.gitignore:206` | **없음** |
| M0 프로브 드라이버 | `.moai/state/verify/prechk-m0/probe.py` | `.gitignore:206` | **없음** |
| M8 종단 하네스·결과 | `.moai/state/verify/prechk-m8/{e2e.py,result.json}` | `.gitignore:206` | **없음** |
| run-audit 원문 | `.moai/state/verify/prechk-runaudit/AUDIT-1.md` (48KB) | `.gitignore:206` | **없음** |
| scout 산출 4건 | `.moai/state/verify/prechk-m0/*.md` (216KB) | `.gitignore:206` | **없음** |

**추적되지 않는 것의 결론은 §E.2 · §E.2a에 요약 없이 전재했다** — 라이브 커맨드·응답 문자열, 판정 6건의 접두 행, 감사 7축 점수와 지적 14건, C-10~C-12 후보 내용. **`server/` 안에 추적 불가 경로를 인용하는 코드·테스트는 0건이다**(실측 확인 — 런타임 의존도 주석 인용도 없다). 즉 **신규 클론에서 스위트가 깨지지 않는다.**

재생성이 필요하면: 드라이버는 `server/bridge/{osc,protocol}.py`만 쓰므로 §E.2의 서술로 재작성 가능하고(스텝 종류는 `state`·`prop`·`exec`·`ping`), M8 하네스는 `build_console_stack` + `build_toolset` 조립이 전부다.

### 3. 트랙 A 브리프 — PR #7 독립 코드 리뷰

**왜**: `gh pr checks 7`이 0건이다. PR을 자동으로 검증하는 것이 없고, run-audit는 **SPEC 프로세스**(요구-AC 정합·증거·경계)를 채점했으므로 **코드 품질·보안 축은 아직 아무도 보지 않았다.** 감사도 좌표 검증이 표본이었음을 스스로 적었다.

**리뷰 대상** (우선순위 순):
1. `server/orchestrator/tools.py`의 `precheck_patch` 핸들러와 `_free_macro_slot` — **유일한 쓰기 경로**다. run-audit P1-3이 여기서 나왔고 수정 후에도 슬롯 유도 로직이 남아 있다.
2. `server/prechk/{inventory,patch}.py` — 절단 복구와 주소 정규화. 경계값(빈 풀 · 1개 · 전부 절단 · 파싱 불가)의 처리.
3. `server/safety/{console,gate}.py` 4지점 — 초크포인트 확장이 감사 경로를 우회하지 않는지.
4. `server/prechk/{macro,report}.py` — 사용자 대면 문자열이 **읽지 못했을 때도 참인지**(이 계열 결함이 이번에 3건 나왔다).

**특히 볼 것**: 새 판독 경로마다 *"읽지 못했을 때 이 문자열이 여전히 참인가"* 를 묻는다(규율 15). 그리고 `except Exception`으로 넓게 잡는 지점이 **판독 실패를 리그 사실로 바꾸지 않는지** — P1-2가 정확히 그 형태였다.

**보지 않을 것**: 요구-AC 정합·계수·PRESERVE 경계는 run-audit가 이미 전건 재현했다(§E.2a). 중복 채점은 값이 없다.

### 4. 트랙 B 브리프 — 후보 I-15 (구간 겹침 재개)

**핵심 통찰**: `ASSUMPTION-27`이 부정인 것은 *"픽스처를 자기 점유폭에 잇는 조인 키가 없다"* 는 뜻이다. 그러나 **조인 없이도 상계는 안다** — 열거 가능한 모드 전체의 폭 중 최대값이다.

**실측으로 산술이 닫힌다**(§E.2와 M8 산출물에서 재계산):
- 모드별 폭: `Patch/FixtureTypes/1/DMXModes/{1,2,3}/DMXChannels` = **29**, 모드 4 = **31** → **상계 31**
- 실측 주소 간격: 유니버스 1은 `[100, 42, 42, 42, 42, 42, 42, 42, 42]`, 유니버스 2는 `[50] × 8` → **최소 42**
- **42 > 31 이므로 어느 픽스처가 어느 모드를 쓰는지 몰라도 겹침이 불가능하다**

**판정의 비대칭이 설계의 핵심이다.** 상계 논증은 **"겹침 없음"을 증명할 수 있으나 "겹침 있음"은 증명할 수 없다** — 간격이 상계보다 작으면 그것은 충돌이 아니라 **미확정**이다. 현재 어휘에는 그 값이 없다. 새 SPEC은 다음을 요구한다:
1. `server/prechk/patch.py`의 `FootprintPolicy(enabled, widths, source)`는 **슬롯별 정확한 폭**을 받는 이진 게이트다. **경계 있는 폭**(모드 집합의 최대값 + 그 근거)을 표현하는 형상이 필요하다.
2. `server/prechk/verdicts.py`의 `COLLISION_KIND`와 `SKIPPED_CHECK_KIND`에 **"상계로 겹침 없음이 증명됨"** 과 **"간격이 상계 이하라 미확정"** 에 해당하는 부류가 없다. 닫힌 어휘를 늘리는 것은 계약 변경이므로 SPEC 층에서 결정해야 한다.
3. `Patch/FixtureTypes` 열거 자체가 절단될 수 있다 — 모드 집합이 불완전하면 **상계도 상계가 아니다.** `REQ-PRECHK-004`의 계수 비교를 여기에도 적용해야 하며, 불완전하면 상계 논증을 쓰지 않는다.

**착수 시 필요한 라이브 세션: 없다.** 폭과 간격이 모두 실측되어 있다. 다만 다른 쇼파일에서는 상계가 달라지므로 **런타임에 읽어야 한다**(하드코딩 금지 — `Patch/FixtureTypes/<t>/DMXModes` 열거 + 각 모드의 `DMXChannels` childCount).

### 5. 함께 넣을 것 — 이월 1건

`AC-PRECHK-015`의 PRESERVE 게이트가 1회성 수동 절차다. **CI가 0건인 저장소에서 PRESERVE를 지키는 유일한 수단은 상시 테스트**이며 선행 SPEC에 선례가 있다(`server/tests/test_songcue_bundle.py`의 `test_preserve_look_files_are_unchanged_from_run_phase_base`와 그 앞의 범위 검증 테스트). 다음 SPEC의 M7에 흡수하는 것이 자연스럽고, 그때 **PRECHK의 PRESERVE 10경로 + `server/safety/**` 승인 4지점 제한**도 같은 형태로 박는다.

### 6. 착수 순서 권고

1. **트랙 A와 트랙 B를 병렬로** 띄운다 — 둘 다 읽기 전용이라 충돌이 0이다. A는 `reviewer`, B는 `scout`가 맞다.
2. A의 지적이 P1급이면 **머지 전에** 고친다. P2 이하면 PR에 적고 머지 후 후속 커밋으로 처리한다.
3. B의 산출은 다음 SPEC의 `research.md` 초안 재료다 — **SPEC 문서를 바로 쓰지 말고** 사용자에게 범위(어휘 확장 승인 여부)를 먼저 확인한다. 닫힌 어휘를 늘리는 것은 계약 변경이다.
4. 머지 후 `origin/main`이 새 SHA가 되므로 **다음 SPEC의 BASE는 그 SHA다** — `95687a0`이 아니다.

## §E.7 트랙 A·B 집행 — 독립 코드 리뷰가 P1 4건을 냈다 (2026-07-30)

> §E.6이 착수 키트를 적었고 이 절이 그 집행 결과다. **§E.6 ②의 규정("A의 지적이 P1급이면 머지 전에 고친다")을 그대로 적용했다** — P1 4건을 이 브랜치에서 수정하고 PR #7에 얹었다.

### 착수 검증 — §E.6 ①의 6줄

| 커맨드 | 기대값 | 실측 |
|---|---|---|
| `git branch --show-current` | `feature/SPEC-COPILOT-PRECHK-001` | 일치 |
| `git status --short` | 비어 있음 | 일치 |
| `git rev-list --left-right --count origin/main...HEAD` | `0 29` | **`0 31`** — behind 0 일치, ahead가 2 크다(§E.5·§E.6 커밋 추가분이며 §E.6 작성 시점 이후의 정상 증가) |
| `gh pr view 7` | OPEN · CLEAN | 일치 (`reviewDecision` 없음) |
| `gh pr checks 7` | no checks reported | 일치 — **CI 0건 재확인** |
| `uv run pytest server/tests/ -q` | 2721 passed · 5 skipped · 0 failed | 일치 |

PRESERVE 게이트도 함께 돌렸다 — `git diff --stat 95687a0..HEAD -- <10경로>` **빈 출력**. `95687a0`의 40자 전체 SHA는 **`95687a0e0eba90b325daf76efbd0ac197e69e2fc`**다(이월 1건이 요구하는 값이며 여기 기록해 재조회를 없앤다).

### 실행 형태 — 폭 3 병렬, 충돌 0건

§E.6 ⑥이 트랙 A(`reviewer`) · 트랙 B(`scout`) 폭 2를 권고했다. **A를 2슬라이스로 쪼개 폭 3으로 확정했다** — PR 신규분이 5210행이고 §E.6의 리뷰 우선순위 4항목이 쓰기 경로(①③)와 판독 경로(②④)로 파일 교집합 없이 갈린다. 전 트랙 읽기 전용이라 충돌은 구조적으로 0이다.

| 트랙 | 에이전트 | 대상 | 산출 |
|---|---|---|---|
| A1 | `reviewer` | `server/orchestrator/tools.py` 핸들러·`_free_macro_slot` · `server/prechk/{macro,query}.py` · 승인 4지점 | 지적 6건(P1 2 · P2 2 · P3 2) · `overall: incorrect` |
| A2 | `reviewer` | `server/prechk/{inventory,patch,report,verdicts}.py` · 대응 테스트 3파일 | 지적 8건(P1 2 · P2 3 · P3 3) · `overall: incorrect` |
| B | `scout` | 후보 I-15 구조적 장애 3건 + 이월 1건 | 장애 3건 해소 형상 + 소비자 전수 14지점 + **전제 정정 1건** |

**두 리뷰어가 전 지적을 실행으로 재현했다** — 주장이 아니라 PR 자신의 테스트 더블로 돌려 출력을 붙였다. 이것이 값을 냈다: 14건 중 P1 4건이 전부 재현된 결함이다.

### P1 4건 — 전건 수정하고 커밋했다 (`5f89701`)

| # | 트랙 | 결함 | 근거 | 수정 |
|---|---|---|---|---|
| **1** | A1 | **`_free_macro_slot`이 자식 0건 매크로 풀을 신뢰한다.** `M.safe_children`는 `Children()`과 `Count()`가 **둘 다** pcall 실패하면 빈 테이블을 돌려주고(`console/lua/copilot_responder.lua:412`) `childCount`는 그 같은 빈 판독에서 파생된다(`:580`·`:607`) — 즉 **열거 전면 실패와 진짜 빈 풀이 한 페이로드**이며 `ok=true`·`truncated=false`다. 전 가드를 통과해 `slot = 1`이 나오고 `Store Macro 1`이 응답기 자신의 `Copilot Go`를 덮는다 | **재현됨** — 수정 전 툴이 번들 전량을 `is_error=False`로 실행했다. 함수 자신의 docstring(`server/orchestrator/tools.py:1252-1256`)과 호출부 주석(`:1324-1325`)이 "절대 일어나선 안 된다"고 적은 바로 그 폴백이다 | `child_count == 0`을 `_MacroPoolIncomplete`로 거부. `childCount`의 `bool` 배제도 함께(A1-P3, 같은 SPEC의 형제 판독기 `server/prechk/macro.py:222`·`:245`가 이미 하는 것) |
| **2** | A1 | **LiveLock이 비오류 리포트로 "매크로를 실행해 눈으로 확인하라"를 낸다.** 락이면 `run_commands`가 `execution_port`에 닿기 전에 반환하는데 `macro.created=true`와 그 reason이 그대로 실려 나가고, 락은 ANSWER이므로 `is_error`가 이 사실을 나를 수 없다 | **재현됨** — `is_error=False` · `macro.created=true` · 커맨드 9건 · 시각 확인 고지까지 전부 실렸고 콘솔에는 매크로가 없다. **run-audit P1-2와 같은 형태가 락 경로에서 생존한 것** | `payload["macro"]["executed"] = not inner.result.is_error`. 형제 핸들러 `prepare_songcue`(`server/orchestrator/tools.py:1202`)가 이미 같은 구분을 발행한다 |
| **3** | A2 | **`root_was_short`가 "자식이 슬롯 인덱스 `i`를 못 실었다"와 "`i` 중복"을 "루트 열거가 짧았다"로 접는다.** 그 자식들은 **반환됐다.** `i` 생략은 가정이 아니라 문서화된 응답기 거동(`console/lua/PROTOCOL.md` §4.2)이고 `server/tests/test_lua_responder.py:486`이 그 경로를 테스트한다 | **재현됨** — `childCount=2`에 `i` 없는 자식 2건(전량 반환)에서 사용자가 `열거 불완전 — 루트 열거가 짧았고…`를 읽었다. **이번 사이클 "판독 실패 vs 부재" 계열의 4번째 사례** | 술어를 `child_count > len(children)`로 좁혔다 — 쓰기 경로가 쓰는 것과 같은 계수-대-반환 비교다. `incomplete` 라벨은 원인 단정을 버리고 **모든 불완전 경우에 참인 것만** 말한다 |
| **4** | A2 | **보강 스윕이 `ok=true`만 보고 노드 정체를 대조하지 않는다.** 숫자 경로 세그먼트는 자식 중 **하나도** 슬롯이 확립되지 않았을 때 `children[wanted_slot]` — 목록 위치 — 로 열화하고(`console/lua/copilot_responder.lua:444-448`), **그 상태가 바로 스윕을 촉발하는 조건**이다. 스윕이 자기를 깨뜨리는 조건에서만 돈다 | **재현됨** — 슬롯 없는 짧은 열거에서 스윕이 `(1,2,3)`을 **순수 위치로** 회수했다. `server/prechk/inventory.py:329-331`이 명시적으로 금지한 승격이고, 응답기 주석(`:249-251`)이 기록한 사고(풀 1/5/7 오발행)의 재발 경로다 | 스윕에 **확립된 슬롯 1개 이상**을 앵커 조건으로 요구한다(`slots_established`) |

#### 게이트가 결함을 비껴갔다 — 규율 13의 3번째 실증

**수정 전에도 스위트 2721개가 전부 통과했다.** 4건 모두 커버가 0이었다. 그래서 신규 테스트 6건을 넣고 **각각이 수정 전 코드에서 실제로 실패하는지 역방향으로 검증했다**(소스만 되돌려 실행 → 6/6 FAIL → 패치 복원). 통과만 확인하고 넘기면 그 자체가 규율 13이 말하는 비껴가는 게이트가 된다.

| 신규 테스트 | 죽이는 결함 | 수정 전 |
|---|---|---|
| `test_a_zero_child_macro_pool_refuses_instead_of_taking_slot_one` | P1-1 | FAIL — `is_error=False`로 번들 실행 |
| `test_a_locked_gate_says_the_macro_was_not_stored` | P1-2 | FAIL — `KeyError: 'executed'` |
| `test_a_hold_says_the_macro_was_not_stored_either` | P1-2 | FAIL |
| `test_a_cleared_gate_says_the_macro_was_stored`(비공허) | P1-2 | FAIL |
| `test_a_child_without_an_index_is_not_reported_as_a_short_root` | P1-3 | FAIL — `index_domain_unknown` True |
| `test_recovery_is_skipped_when_no_child_established_a_slot` | P1-4 | FAIL — `recovered_slots=(1,2,3)` |
| `test_recovery_still_runs_when_a_slot_is_established`(비공허) | P1-4 가드가 회수를 죽이지 않음 | PASS(의도) |

**수정 후: 2728 passed · 5 skipped · 0 failed.** PRESERVE 게이트 빈 출력 유지 · `server/safety/**` 이 커밋에서 무변경 · 손댄 5파일 전부 ruff check·format 통과.

#### 계약을 건드리지 않았다 — 의도적 한정

수정은 **닫힌 판정 어휘와 리포트 페이로드 스키마를 손대지 않는다.** 둘 중 어느 쪽이든 확장은 계약 변경이고 사용자 승인이 선행한다(§0의 "먼저 결정할 것"). P1 4건의 **인과는 코드 층에서 전부 끊었으므로** 어휘 확장 없이 닫힌다. 대가는 두 가지를 포기한 것이다 — ① 스윕을 건너뛴 사유를 `skipped_checks`로 고지하지 못한다(새 어휘값이 필요) ② 어느 행이 보강에서 왔는지 리포트에 노출하지 못한다(`FixtureVerdict.to_dict()` 키 추가 = `design.md` §5.1 스키마 변경). 둘 다 P2로 남기고 아래에 적었다.

### 남은 지적 10건 — 머지 후 후속 커밋 (§E.6 ②의 P2 이하 처리)

| # | 등급 | 좌표 | 요지 |
|---|---|---|---|
| A1-1 | P2 | `server/orchestrator/tools.py` 매크로 실행 직후 | **재조회로 효과를 확인하지 않는다.** 형제 `prepare_songcue`는 실행 후 `query_state`로 재조회해 `requery_payload`를 리포트에 싣는다(`:1192-1200`). 이 SPEC이 저작 문법을 확정한 방법 자체가 재조회였다(§E.2 M0 `ASSUMPTION-26`) |
| A1-2 | P2 | `server/orchestrator/tools.py` 매크로 슬롯 유도 지점 | **대상 그룹이 0건이어도 슬롯을 먼저 유도한다.** 그룹 없음은 ANSWER인데(`AC-PRECHK-014` ④) 쓰이지도 않을 슬롯의 풀 판독 실패가 호출 전체를 오류로 만들고 성공적으로 읽은 인벤토리를 버린다. 감사 OSC 송신 1회도 낭비한다 |
| A1-3 | P3 | `server/orchestrator/tools.py` `rig_paths` 인덱싱 | `rig_paths` 오버라이드가 섹션을 빼면 `KeyError`가 "group pool unreadable"로 렌더링된다 — 조회하지도 않은 풀에 배선 실수를 전가한다. 형제 핸들러 3개는 전부 명시 가드로 시작한다(`:769`·`:891`·`:1112`) |
| A2-1 | P2 | `server/prechk/inventory.py` `missing_count` 클램프 | `max(child_count - observed_count, 0)`이 `AC-PRECHK-003`의 `observed + still_unobserved == child_count`를 **신호 없이** 깬다. 재현: `childCount=2`에 `i` 1·2·3 → `observed 3 / missing 0 / completeness complete`이며 요약이 `관측 3개 / 보고된 자식 수 2개`를 찍으면서 "완전"을 선언한다. 도달 가능성은 `[미확정]`(출하 응답기는 이 페이로드를 못 만든다, `read_inventory`는 임의 포트를 받는 공개 API다) |
| A2-2 | P2 | `server/prechk/inventory.py` 형태 게이트 | 판별자가 `function: 0x` 하나뿐인데 결함 근원은 `safe_property`의 `tostring` 폴백(`console/lua/copilot_responder.lua:204-217`)이라 `table:`·`userdata:`·`thread:`가 **값으로 채택된다.** 응답기가 돌려줄 수 있는 포인터 형태는 4종인데 게이트는 1종이다 |
| A2-3 | P2 | `server/prechk/patch.py` `_range_overlaps` | **폭이 없는 픽스처를 표시 없이 겹침 판정에서 뺀다.** 형제 배제(`type_mode_ok`)는 `reasons`에 코드를 남기고 verdict를 내리는데 폭 부재만 비대칭적으로 침묵하고 `observed_clear`를 준다. 부분 폭 맵은 설계상 정상 결과다. 출하 경로가 이 축을 켜지 않아 P2 |
| A2-4 | P3 | `server/prechk/report.py` `shape_invalid` 라벨 | 라벨이 형태 2종을 열거하지만 실제 분류 대상은 4종이며 그중 하나(슬롯 인덱스 `i` 부재)는 값 형태 문제가 아니다 |
| A2-5 | P3 | `server/prechk/report.py` `summary_ko` | `scope_note`를 버리고 무조건 `충돌 N건`을 적는다. 문단 전체를 읽으면 뒤집히지만 숫자만 보는 독법(로그 grep·알림)에는 관측 범위 밖까지 다룬 수치로 읽힌다 |
| A2-6 | P3 | `server/prechk/inventory.py` `_probe_slot` | 포트 예외·타임아웃과 `ok=false`를 모두 `None`으로 접어 **기록을 0건 남긴다.** 형제 `read_properties`는 같은 상황을 `PropertyRead(ok=False, error=…)`로 붙잡는다. 판정 수치는 보수적이라 P3이지만 링크 장애와 희소 풀이 리포트상 구분되지 않는다 |
| A2-7 | P3 | `server/tests/test_prechk_report.py` | 집계 검증 테스트가 `not_assessed`를 명시적으로 `continue`한다 — **행에서 파생되지 않는 유일한 수치**이며 A2-1을 통과시킨 게이트다. 나머지 두 테스트는 동어반복(대입문을 되읽는다) |

**A2-1 · A2-3 · A2-6은 어휘 또는 스키마를 건드리므로 후속 SPEC의 계약 결정과 함께 처리하는 것이 자연스럽다.** A1-1 · A1-2 · A1-3 · A2-2 · A2-4는 계약 무변경으로 닫을 수 있다.

### 트랙 B 산출 — 전제 1건을 정정했고 승인 대상이 좁아졌다

§E.6 ④가 세운 3개 구조적 장애는 **전부 가법적 변경으로 해소 가능**하다. 다만 조사가 §E.6 ④의 서술 2건을 정정했다.

**정정 1 — `COLLISION_KIND`에 추가할 것이 0건이다.** §E.6 ④②는 `COLLISION_KIND`와 `SKIPPED_CHECK_KIND`에 "부류가 없다"고 적었고 그것은 참이지만 **결론이 추가는 아니다.** `상계로 겹침 없음이 증명됨`은 **충돌도 미수행도 아닌 긍정 결과**다 — `COLLISION_KIND`에 넣으면 깨끗한 리그를 `충돌`로 라벨하고 전 슬롯에 `COLLISION`을 찍고, `SKIPPED_CHECK_KIND`에 넣으면 **수행된** 판정을 `미수행`이라 쓴다. **둘 다 거짓 문자열이므로 새 축이 필요하다.** 제안: 신규 어휘 `overlap_basis` = {`exact_widths`, `bound_proves_clear`, `bound_inconclusive`, `not_performed`} + `SKIPPED_CHECK_KIND` += `range_overlap_bound_inconclusive` 1값. **`FIXTURE_VERDICT`는 건드리지 않는다**(건드리면 `server/prechk/patch.py`의 수기 카운트 dict와 테스트 2곳이 깨진다).

**정정 2 — off-by-one이 잠복해 있다.** §E.6 ④의 *"간격이 상계 **이하**라 미확정"*은 틀렸다. `server/prechk/patch.py`가 구간을 `(start, start + width - 1)` **닫힌 끝**으로 만들므로 겹침 조건은 `간격 < 폭`이다. 따라서 `간격 == 상계`는 **증명 가능하게 깨끗하다**(폭 31이 1~31을 점유하면 32는 자유). 올바른 술어는 `간격 < 상계 → 미확정` · `간격 ≥ 상계 → 겹침 없음 증명`. **현재 쇼파일에서는 42 > 31이라 두 표현이 같은 답을 내므로 오류가 드러나지 않는다** — 간격이 정확히 상계인 리그에서 처음 드러나고 그때 깨끗한 리그를 미확정으로 보고한다. SPEC 문안과 코드 양쪽에서 고쳐야 한다.

#### 어휘 확장이 왜 계약 변경인지 — 실체가 확인됐다

`server/prechk/verdicts.py`의 `validate()`가 어휘 밖 값을 `UnknownVerdict`로 실패시키고, **`server/prechk/report.py`가 그 계약을 라벨표와 import 시점에 이중 결속한다.** 라벨을 빠뜨리면 스위트 실패가 아니라 **`import server.prechk.report` 자체가 실패**하고 툴셋 전체가 죽는다. 확장은 ① `verdicts.py` 어휘 ② `report.py` 라벨표 ③ `report.py` 가드 튜플 ④ `server/tests/test_prechk_verdicts.py`의 재타이핑된 정본 — **4곳을 원자적으로** 움직여야 한다. 깨지는 소비자는 전수 14지점이며 그중 하드 브레이크는 어휘 순서 있는 리스트 단정 · `collisions` 정확 dict 단정 · `test_every_queried_path_stays_under_the_fixture_root` 3건이다.

#### 미확정 분기는 라이브로 증명할 수 없다

실측 주소로 계산하면 **17개 인접쌍 전부가 상계를 통과한다** — 유니버스 1 최소 간격 42, 유니버스 2는 50, 상계 31. 즉 **`미확정` 부류를 발동시키는 입력이 현재 쇼파일에 0건이다.** 그 분기는 합성 인메모리 리그만이 덮을 수 있고 그것이 이미 확립된 선례다(`range_overlap_go()`의 폭은 주입값이며 라이브 미러가 아니다). **따라서 미확정 분기에 라이브 증거를 요구하는 AC는 충족 불가능하므로 쓰지 않는다.**

#### 조사가 새로 찾은 것 3건

1. **오늘 도달 가능한 거짓 문자열 1건.** `FootprintPolicy(enabled=True, widths={})`면 겹침 축이 켜진 것으로 판정되는데 전 픽스처가 폭 없음으로 걸러져 `충돌 0건`만 찍히고 **미수행 고지가 없다** — 사용자는 구간 겹침이 수행되고 깨끗했다고 읽는다. 프로덕션은 이 입력을 만들지 않지만(`evaluate_patch(inventory)`로 인자 생략) **다음 SPEC이 정확히 이 입력을 만든다.** A2-3과 같은 뿌리다.
2. **`source` 필드가 한 번도 읽히지 않는다.** `FootprintPolicy.source`의 소비자가 0건이다 — 근거를 받아 버린다. `bound_source`를 추가하면서 `PatchEvaluation.to_dict()`에 내보내는 키를 함께 만들지 않으면 그것도 똑같이 죽는다.
3. **절단 계수 비교가 구현 3개·재사용 헬퍼 0개로 흩어져 있다**(`server/prechk/inventory.py` · `server/prechk/macro.py` · `server/orchestrator/tools.py`의 `_free_macro_slot`, 셋째는 `build_toolset` 내부 클로저라 import 불가). 경로를 인자로 받는 열거 헬퍼로 수렴시키는 것이 `Patch/FixtureTypes` 순회의 최소 변경이기도 하다.

#### 하드코딩 금지 요건의 비용

3단 순회 비용은 `1 + T + Σ M_t` 회 `query_state`다(`T` = 픽스처 타입 수, `M_t` = 타입 t의 모드 수). 현재 쇼파일은 `T=1`·`M=4` 가정 시 6회지만 **`Patch/FixtureTypes`의 `childCount` 자체가 미기록이라 `[미확정]`**이며 순회가 런타임에 읽어야 한다. 최악은 무계이므로 기존 선례(`RIG_DRILLDOWN_QUERY_CAP` + 자식당 예산 + 소진 시 표기)를 그대로 쓴다. **결정적 차이 1건**: 거기서 예산 소진은 정보지만 여기서는 **모드 집합을 불완전하게 만들어 상계를 무효화**한다 — 캡 도달 시 `겹침 없음 증명`이 아니라 `미수행`을 내야 한다. *"부분 상계"* 같은 것은 없다.

**새 화이트리스트 항목은 필요 없다** — 순회는 프로퍼티를 0개 읽고 `childCount`만 쓴다. **경로 상수도 이미 있다**: `DEFAULT_RIG_CONTEXT_PATHS["fixture_types"]`가 2026-07-22 라이브 검증 후 기본값으로 승격돼 있으므로 핸들러가 `rig_paths["groups"]`·`rig_paths["macros"]`와 **똑같이** 넘기면 된다. `server/prechk/` 안에 리터럴로 박으면 `rig_paths` 오버라이드 이음새를 우회한다.

#### 유니버스 경계 — 새 `[미확정]` 1건

간격은 **각 유니버스 내부에서만** 계산하고 전 유니버스에 대해 최소를 취한다(기존 두 판정이 이미 유니버스를 서로소 공간으로 다룬다). 남는 문제는 **꼬리 초과**다 — 유니버스 마지막 픽스처의 점유가 512를 넘어 다음 유니버스로 걸치는가. 실측 리그는 둘 다 여유가 있어 발생하지 않지만 **유니버스당 채널 상한이 512라는 근거를 저장소에서 찾지 못했고**(`Patch/DmxUniverses` `childCount 1024`는 유니버스 **개수**다) 라이브 관측도 없다. **다음 SPEC의 명시적 `ASSUMPTION`으로 세운다** — 512를 코드에 박으면 미검증 관례의 하드코딩이다.

### 이월 1건 — 구현 형상이 확정됐다

`AC-PRECHK-015` PRESERVE 게이트의 상시 테스트는 신규 `server/tests/test_prechk_preserve.py`로 만든다(**선례 파일을 확장하지 않는다** — 상수가 SONGCUE BASE 상대이고 한 모듈에 두 BASE를 섞는 것이 혼동의 원인이다).

| 요소 | 형상 |
|---|---|
| BASE 고정 | `_PRECHK_BASE = "95687a0e0eba90b325daf76efbd0ac197e69e2fc"`(40자, 선례와 동형). **범위 고정 테스트를 반드시 짝으로 넣는다** — argv 4번째 원소가 정확히 `f"{_PRECHK_BASE}..HEAD"`임을 단정. 없으면 누군가 인자 없는 `git diff`로 "단순화"하고 게이트가 영구히 0행을 낸다(§E.2 M7이 그 무력화를 실측했다) |
| PRESERVE 10경로 | `spec.md`의 목록 그대로. 디렉터리는 git pathspec이 재귀 포함하므로 `**` 전개 불필요 |
| **비공허성(선례보다 강하게)** | 선례는 목록이 비지 않았음만 단정하지만 **존재하지 않는 경로는 `--stat`에 조용히 0행을 기여한다** — 오타 1글자로 게이트가 영구 통과한다. 각 경로에 `exists()`를 단정해 이 부류를 잡는다 |
| `server/safety/**` 4지점 한정 | 여기는 **diff가 비어 있지 않아야 정상**이라 선례 형태를 그대로 못 쓴다. 3중 단정: ① 파일집합 봉쇄(`--name-only`가 정확히 `{console.py, gate.py}`) ② **순수 추가 봉쇄** — "순수 추가"의 실체는 hunk 위치가 아니라 **삭제 0행**이다. `console.py`는 삭제 0행, `gate.py`는 승인된 삭제 1행이 **독스트링**이므로 `≤ 1` **그리고** 그 1행이 `"""`로 시작함을 함께 단정한다(없으면 의미 있는 삭제가 허용치 아래로 숨는다). **이것이 선례의 hunk 시작점 스냅샷보다 강하다 — 어디가 아니라 무엇이 바뀌었는지를 제약한다** ③ 보호 심볼 무침범(선례 `_overlaps()` 재사용) |
| 승인 4지점 중 `server/safety/` 밖 2건 | `server/orchestrator/ports.py`·`server/measurement/mock_provider.py`는 별도 튜플로 같은 단정 |
| BASE 상대 좌표 | `_PROGRAMMER_STATE_COMMANDS`는 BASE에서 **247-257**(HEAD 258-268), `_GateStatePort` BASE **114**·`query_state` BASE **120**·`_query_state` BASE **598**, `server/safety/console.py` `query_state` BASE **372**(프로토콜 선언 **96**). **§E.6 시점 `[미확정]` 3건 중 2건을 여기서 닫았다** — 남은 1건은 `Patch/FixtureTypes`의 `childCount`이며 라이브가 필요하다 |

### 판단 — 머지 준비 상태

**P1 4건이 닫혔고 커밋됐다(`5f89701`).** §E.5의 3안 중 **1(독립 코드 리뷰)이 값을 냈다** — 그것을 건너뛰고 2(바로 머지)를 골랐다면 응답기 자신의 매크로를 덮는 경로와 위치를 슬롯으로 위조하는 경로가 main에 들어갔다. **CI 0건인 저장소에서 사람 리뷰가 유일한 관문이라는 §E.5의 판단이 실증됐다.**

남은 P2·P3 10건은 머지 후 후속 커밋이며 그중 3건은 후속 SPEC의 계약 결정과 묶인다. **사용자 결정이 필요한 것은 1건뿐이다** — 트랙 B가 요구하는 **어휘 확장 승인**(신규 축 `overlap_basis` 4값 + `SKIPPED_CHECK_KIND` 1값). 그것은 계약 변경이므로 SPEC 문서 착수 전에 받는다(§0이 이미 그렇게 규정했다).

## §E.8 후속 지적 처리 — 계약 무변경으로 9건을 닫았다 (2026-07-30)

> §E.7이 P1 4건을 닫고 P2·P3 10건을 표로 남겼다. 이 절이 그중 **계약(닫힌 어휘·리포트 스키마)을 건드리지 않고 닫을 수 있는 9건**의 처리 기록이다. 커밋 `dde8372`.

### 실행 형태 — 폭 2 병렬

§E.7의 10건을 파일 축으로 갈랐다. **쓰기 경로(`server/orchestrator/tools.py`) 3건은 판독 사슬과 파일 교집합이 0**이고, 판독 3파일은 `inventory.py → patch.py → report.py`로 **층이 쌓여** §F가 지목한 모듈 사슬에 해당한다.

| 슬라이스 | 담당 | 파일 | 처리 |
|---|---|---|---|
| 쓰기 경로 | 워커 1(병렬) | `server/orchestrator/tools.py` · `server/tests/test_prechk_tool.py` | A1-1 · A1-2 · A1-3 |
| 판독 사슬 | 코디네이터 직접 | `server/prechk/{inventory,patch,report}.py` + 대응 테스트 3파일 | A2-1 · A2-2 · A2-3 · A2-4 · A2-5 · A2-6 · A2-7 |

**판독 사슬을 쪼개지 않은 근거**: `report.py`의 라벨 변경이 `inventory.py`의 분류 변경에 종속되고(A2-4 ↔ A2-1/A2-6), `patch.py`의 폭 판정이 `report.py`의 요약 문자열로 나간다(A2-3 → A2-5). plan-phase가 이미 적은 이유가 그대로 적용된다 — *"6개 에이전트에 뿌리면 그 드리프트를 **보장**하는 셈이다."*

### 처리 9건

#### 쓰기 경로

| # | 무엇을 바꿨나 | 왜 이 형상인가 |
|---|---|---|
| **A1-1** | 번들이 오류 없이 나간 경우에만 **저장된 라인 1개**를 `prop <macros>/<슬롯>/1 Command`로 재조회해 `macro_requery`로 발행한다. 재조회 실패는 **"재조회가 실패했다"**로 말하고 **"매크로가 없다"로 바뀌지 않으며** 저작 결과를 지우지 않는다 | 이 SPEC이 저작 문법을 확정한 수단 자체가 재조회다(§E.2 M0). 전량 재조회는 그룹 수 × 2만큼 감사 OSC를 늘리므로 **라인 1개로 고정**했다 — 그 1개가 M0에서 실측된 라인이다 |
| | **불일치를 `is_error`로 승격하지 않았다** | 워커가 승격을 먼저 검토하고 **철회**했다. 저장 후 정확 문자열 일치는 **리그 1대·라인 1개에서만 실측**됐으므로, 콘솔이 저장 시 문자열을 정규화한다면 **모든 정상 사전점검이 오류가 된다** — 같은 결함 계열의 *허위경보* 버전이다. `matches:false` + 양쪽 값 노출로 전량 보고한다 |
| **A1-2** | 대상 그룹이 있을 때만 매크로 풀을 조회한다 | 그룹 0건은 ANSWER인데(`AC-PRECHK-014` ④) 쓰이지도 않을 슬롯의 판독 실패가 호출 전체를 오류로 만들고 **성공적으로 읽은 인벤토리(툴의 주 산출물)를 버렸다.** 감사 OSC 1회도 절감된다. **폴백 금지 성질은 보존**된다 — 대체 슬롯은 콘솔에 발화될 수 없다 |
| **A1-3** | `rig_paths` 섹션 누락을 형제 3핸들러와 같은 명시 가드로 잡고 **부족한 섹션을 이름으로 말한다** | 기존에는 `KeyError`가 `group pool unreadable`로 렌더링돼 **조회하지도 않은 풀에 배선 실수를 전가**했다 |

#### 판독 사슬

| # | 무엇을 바꿨나 | 왜 이 형상인가 |
|---|---|---|
| **A2-1** | 자기 자식 수를 초과 관측한 스냅샷을 **`InventoryReadError`로 거부**하고 클램프를 없앴다 | `max(child_count - observed_count, 0)`이 불일치를 흡수해 `AC-PRECHK-003`의 등식이 **거짓으로 닫혔다** — `관측 3개 / 보고된 자식 수 2개`를 찍으면서 같은 문장에서 `complete`를 선언했다. 런타임 검증이 0건이었고 **독스트링이 주장만** 했다. 이제 등식이 **구성에 의해** 성립한다 |
| **A2-2** | 포인터 판별을 4종(`function`·`table`·`userdata`·`thread`)으로 넓혔다 | 결함 근원이 함수가 아니라 `safe_property`의 `tostring` 폴백이고 Lua는 **모든 비원시 타입**을 `<type>: 0x<addr>`로 만든다. 기존 게이트는 4종 중 1종만 잡아 나머지를 **값으로 채택**했다 — 타입 자리에 포인터 문자열이 인쇄되거나, 응답기 아티팩트가 **패치 주소 잘못으로 전가**됐다. 비공허 테스트로 유사 정상값(`table` · `table: value` · `0x105b0f048`)이 통과하는 것도 고정했다 |
| **A2-6** | `_probe_slot`가 **예외(타임아웃)와 `ok=false`를 분리**한다. 전자는 기록하고 후자는 침묵을 유지 | 둘을 접어 **모든 보강 조회 실패가 리포트에서 사라졌고**, 링크 장애와 희소 풀이 구분되지 않아 운영자가 링크를 의심할지 패치 공백을 의심할지 알 수 없었다. **판정 수치는 불변** — 진단만 살아난다. 양방향 테스트로 고정했다(희소 풀은 여전히 침묵) |
| **A2-3** | 폭 없는 픽스처를 **고지한다.** 폭 판정을 `_footprint_width` **단일 출처**로 모아 검사와 고지가 드리프트할 수 없게 했다 | 기존에는 `continue` 하나로 흔적 없이 빠졌는데 **형제 배제는 코드를 남기고 verdict를 내린다.** 즉 **비교되지 않은 픽스처가 "이상 없음"으로 보고**됐다. `enabled=True, widths={}`면 `충돌 0건`만 찍히고 미수행 고지가 없어 **판정이 수행되고 깨끗한 것처럼** 읽혔다. `widths`에 전체성 제약이 없고 출처가 실패 가능한 타입별 조회이므로 **부분 맵이 정상 결과**다 |
| **A2-4** | `shape_invalid` 라벨에서 형태 열거를 뺐다 | 4종을 담는 코드에 2종만 열거해 **사용자가 없는 함수 참조를 찾으러 갔다.** 집계 행은 `detail`을 달지 않으므로 라벨이 유일한 설명이었다 |
| **A2-5** | 불완전 판독에서 `충돌 N건`에 `관측된 범위에서`를 붙인다 | `scope_qualified`가 정확히 이 주장을 위해 있는데 문단이 그것을 버렸다. 문단 전체를 읽으면 뒤집히지만 **숫자만 보는 독법(로그 grep·알림 요약)**에는 리그 전체를 다룬 수치로 읽힌다 — `REQ-PRECHK-010`이 거러내려는 독법이다. 비공허 테스트로 완전 판독에서는 한정어가 **붙지 않는** 것도 고정했다 |
| **A2-7** | 집계 테스트의 `continue`를 없애고 **선언된 개체 수와 대조**하며 **전체 인구가 닫히는지** 단정한다 | `not_assessed`는 **행에서 파생되지 않는 유일한 수치**이고 나머지 두 테스트는 대입문을 되읽는 동어반복이었다. 이것이 A2-1을 통과시킨 게이트다 |

### 계약 결정을 기다리는 2건

| 항목 | 왜 지금 못 하나 |
|---|---|
| 부분 커버리지 고지의 **슬롯 단위 정밀도** | 어느 슬롯이 비교되지 않았는지를 `skipped_checks`의 **부류**로 구분하려면 `SKIPPED_CHECK_KIND`에 새 값이 필요하다. 현재는 사유 문장(자유 텍스트)에 슬롯을 열거해 정보는 전달하나 부류로는 `range_overlap_descope`와 합쳐진다 |
| **어느 리포트 행이 보강에서 왔나** | `FixtureVerdict.to_dict()`에 키 추가 = `design.md` §5.1 스키마 변경이며 `server/tests/test_prechk_patch.py`가 fixture 행의 키 집합을 **정확 일치**로 단정한다. `Inventory` 블록도 같은 형태로 잠겨 있다 |

### 게이트 규율 — 이번에도 역방향으로 검증했다

**신규 테스트 30건 중 26건이 수정 전 코드에서 실패함을 확인했다**(소스만 되돌려 실행 → 복원). 통과한 4건은 **회귀 테스트가 아니라고 코드에 명시**했다 — 비공허성 보증 3건과 불변식 가드 1건이다.

워커가 그중 한 축에서 한 걸음 더 갔다: 재조회를 **하지 않아야 하는** 3경로(hold · lock · 실패)의 테스트는 수정 전 재조회가 아예 없어 **공허하게 통과**했으므로, `if not inner.result.is_error:` → `if True:`로 **직접 돌연변이를 넣어 정확히 그 3건만 실패하는 것**을 확인했다. 이것이 규율 13("게이트가 결함을 비껴가는 형태를 의심한다")의 올바른 집행 형태다.

### 검증

**2758 passed · 5 skipped · 0 failed**(§E.7 시점 2728 → 신규 30). PRESERVE 게이트(`95687a0e0eba90b325daf76efbd0ac197e69e2fc`) 빈 출력 · **`server/safety/**`는 이 커밋에서 무변경** · 손댄 8파일 전부 ruff check·format 통과.

### 새로 생긴 `[미확정]` 2건

1. **저장 후 `Command` 값의 정규화 여부.** M0 실측은 ON 라인 1건뿐이다. 콘솔이 문자열을 재포맷하면 `matches:false`가 오탐이 된다. **갈리는 지점**: 라이브에서 `Set Macro N.2 Property 'Command' 'Group 11 At 0'` 직후 `prop DataPool/Macros/N/2 Command`를 실측하면 확정된다. 그래서 재조회 대상을 **실측된 라인 1로 고정**했다.
2. **`MacroResult.lines`가 빈 채 `commands`가 채워지는 경로.** 코드 경로로는 불가라고 판단하고 근거를 코드에 적었다. **갈리는 지점**: `server/prechk/macro.py`의 저작 루프가 바뀌면 재검토가 필요하다.

### 남은 상태

**P1 4건 + P2·P3 9건이 닫혔다. 리뷰 지적 14건 중 남은 것은 계약 결정에 묶인 2건뿐이며 둘 다 정보 손실이 아니라 정밀도 문제다.** PR #7은 `MERGEABLE`·`CLEAN`이고 CI는 여전히 0건이므로 **머지 관문은 사람 리뷰 그대로다.**

## §E.9 머지 — SPEC 종료 (2026-07-30)

> **이 SPEC은 끝났다.** 후속 SPEC 담당자가 알아야 할 것은 두 가지다: 새 BASE SHA와, 이 저장소가 여전히 CI 0건이라는 사실.

### 머지 사실

| 항목 | 값 |
|---|---|
| 방식 | **squash** — 직전 SPEC(SONGCUE, `#6`)의 관례를 따랐다. 그것이 이 SPEC의 BASE `95687a0`을 만든 형태다 |
| PR | `#7` → `MERGED` (2026-07-30T08:47:42Z) |
| **머지 커밋 = 새 `origin/main`** | **`b406a7b2bde856f0ecfb445885e6fe60693c68a5`** |
| feature 브랜치 | **보존**(`origin/feature/SPEC-COPILOT-PRECHK-001`). SONGCUE·BUSKWIZ 브랜치도 남아 있다 |
| 사용자 승인 | 머지 요청을 명시적으로 받았다. §E.5가 *"머지 전 유일한 관문은 사람 리뷰다"*라고 규정했고 에이전트 리뷰가 그것을 대체하지 않으므로, 승인 없이는 머지하지 않았다 |

### BASE SHA 두 개를 혼동하지 않는다 — 이것이 유일한 함정이다

| 용도 | SHA |
|---|---|
| **다음 SPEC의 BASE** | **`b406a7b2bde856f0ecfb445885e6fe60693c68a5`** (= 새 `origin/main`) |
| **본 SPEC의 PRESERVE 게이트 기준점** | `95687a0e0eba90b325daf76efbd0ac197e69e2fc` — **불변이다.** `AC-PRECHK-015` ①이 쓰는 값이고, §E.7 이월 항목의 상시 테스트 `_PRECHK_BASE`도 이 값이어야 한다 |

**이월 테스트를 쓸 때 이 둘을 섞으면 게이트가 무력해진다.** PRECHK의 PRESERVE 무변경을 새 main 기준으로 검사하면 커밋 직후 항상 0행이 나온다 — §E.2 M7이 실측으로 증명한 무력화와 같은 형태다. 그리고 한 모듈에 두 BASE를 섞지 않는다는 §E.7의 규정이 이제 **세 SPEC 사이의 규정**이 됐다(SONGCUE `38a6e7e` · PRECHK `95687a0` · 다음 SPEC `b406a7b`).

### 머지된 main을 독립 검증했다

커밋 메시지의 주장을 믿지 않고 **신규 워크트리를 `origin/main`에 붙여 실측했다** — squash가 전부 실었는지, 그리고 §0이 주장한 *"신규 클론에서 스위트가 그대로 통과한다"*가 참인지 확인하는 유일한 방법이다.

| 검사 | 결과 |
|---|---|
| `server/prechk/` 7파일 존재 | 확인 |
| prechk 테스트 6파일 | **268 passed** |
| 전체 스위트 | **2756 passed · 7 skipped · 0 failed** |
| PRESERVE(`95687a0..origin/main`, 10경로) | **빈 출력** |
| `server/safety/` diff 파일집합 | `console.py` · `gate.py` **2개뿐** — 승인 4지점 밖의 파일이 생기지 않았다 |

**계수 차이 2건을 설명해 둔다.** 브랜치에서는 `2758 passed · 5 skipped`였고 새 워크트리에서는 `2756 passed · 7 skipped`다. 이동한 2건은 `server/tests/test_deploy_tauri_shell.py`의 **빌드 산출물 의존 테스트**(`.app` 번들이 없으면 skip)이며, 작업 디렉터리에는 이전에 빌드한 번들이 있어 실행됐다. **prechk 관련 skip은 0건이고 유실은 0건이다** — 2756 + 2 = 2758로 정확히 닫힌다.

### 후속 SPEC이 이어받을 것

| 항목 | 상태 | 어디 |
|---|---|---|
| **닫힌 어휘 확장 승인** | **사용자 결정 대기 — 유일하게 열린 접점** | §E.7 트랙 B(신규 축 `overlap_basis` 4값 + `SKIPPED_CHECK_KIND` 1값) · 정정 2건 포함 |
| 리뷰 잔여 2건 | 위 승인에 묶임. **정밀도 문제이며 정보 손실은 아니다** | §E.8 말미 |
| `AC-PRECHK-015` PRESERVE 상시 테스트 | 구현 형상 확정, 미착수 | §E.7 이월 1건 — BASE 40자 SHA · 3중 단정 · 선례 좌표 전부 기재 |
| 후속 후보 우선순위 | 1순위 = 구간 겹침 재개(라이브 불필요) | §E.5 후속 표 · §E.7 트랙 B |
| **CI는 여전히 0건이다** | 변하지 않았다 | 그래서 위 상시 테스트가 PRESERVE를 지키는 **유일한** 수단이다 |

### 이 사이클이 남긴 교훈 1건 — 규율 16

16. **"스위트가 통과한다"는 "결함이 없다"가 아니다.** 이번에 P1 4건이 **2721개 스위트가 전부 통과하는 상태에서 살아 있었다.** 넷 다 독립 코드 리뷰가 찾았고 넷 다 재현됐으며, 그중 하나는 응답기 자신의 매크로를 덮는 경로였다. 그래서 이 사이클부터 **신규 테스트는 수정 전 코드에서 실패하는 것을 역방향으로 확인하고**, 통과하는 테스트는 *회귀 테스트가 아니라고 코드에 명시*한다(비공허성 보증 · 불변식 가드). 재조회 3경로처럼 수정 전 공허하게 통과하는 테스트는 **직접 돌연변이를 넣어** 그것이 무엇을 막는지 증명한다. 규율 13이 "의심한다"였다면 이것은 **"측정한다"**다.

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

### §F.1 개정 1회차 — M0 실측 후 M4를 병렬 슬라이스로 분리한다 (2026-07-30)

> 본 절은 §F가 스스로 예고한 개정 조항의 집행이다: *"**폭을 미리 약속하지 않는다**: M0 실측이 새 도메인을 만들면 그때 §F를 개정하고 그 사유를 적는다."* 개정 시점은 **M1 커밋 직후, M2 이후의 첫 스폰 이전**이다.

#### 무엇이 바뀌었나

M0 이전의 M4는 **미지 축**이었다. `ASSUMPTION-26`이 등급 T3이고 라이브 `OK` 기록이 0건이었으므로, M4에 워커를 배정하는 것은 판정 전에는 산출물이 있는지도 모르는 상태에서 배정하는 것이었다. 그래서 §F 원안은 M4를 순차 사슬에 넣었다.

M0가 그 미지를 닫았다. `ASSUMPTION-26`은 **GO**이고 저작 리터럴이 3단으로 실측됐으며(`Store Macro <n>` → `Store Macro <n>.<line>` → `Set Macro <n>.<line> Property 'Command' '<cmd>'`), 대상 그룹도 실측됐다(`DataPool/Groups` 자식 4개, `No` 값 1 · 11 · 12 · 13, 이름 `'Copilot Grp'` · `'Back'` · `'Front'` · `'All'`). **즉 M4는 이제 입력이 전부 확정된 자립 슬라이스다.**

#### 독립성 검증 — 파일과 데이터 양쪽에서

| 축 | M2·M3 사슬 | M4 |
|---|---|---|
| 구현 파일 | `server/prechk/inventory.py` · `server/prechk/patch.py` | `server/prechk/macro.py` |
| 테스트 파일 | `server/tests/test_prechk_inventory.py` · `server/tests/test_prechk_patch.py` | `server/tests/test_prechk_macro.py` |
| 입력 | 열거 페이로드와 프로퍼티 판독 | M0 실측 리터럴과 그룹 목록 |
| 상호 의존 | 없음 — M4는 인벤토리 산출을 읽지 않는다(대상은 그룹이고 픽스처가 아니다, `design.md` 슬롯 D) | 없음 |

**파일 교집합 0건 · 데이터 의존 0건.** 두 슬라이스는 M5 리포트에서 처음 만난다. §F 원안이 지목한 사슬 셋 중 **데이터 사슬은 M2 → M3 → M5이고 M4는 그 사슬의 원소가 아니다** — 원안의 서술도 M4를 데이터 사슬에 넣지 않았고, `plan.md` §G도 *"`ASSUMPTION-26`은 M4의 매크로 저작 분기만 막고"*라고 적었다. 막던 것이 풀린 지금 M4는 병렬 원소다.

#### 확정

**Decision: sub-agent — 폭 2 (M2·M3 사슬 1워커 + M4 1워커).** M5 이후는 다시 폭 1이다(M5가 두 슬라이스의 산출을 합치고 M6 툴 형상을 정한다).

승인 사슬과 모듈 사슬은 개정하지 않는다 — 승인 사슬은 M1로 이미 해소됐고, 모듈 사슬(`inventory.py` → `patch.py` → `report.py`)은 한 워커가 순차로 키우므로 그대로다.

#### 교차 슬라이스 계약 — 오케스트레이터가 선행 구현했다

워커에게 협상시키지 않는다. 공유 선행물은 **스폰 이전에** 직접 만들어 커밋했다.

| 산출물 | 내용 | 소유 |
|---|---|---|
| `server/prechk/verdicts.py` | 닫힌 판정 어휘 5종(`design.md` 슬롯 C 그대로) + `validate()` — 어휘 밖 값은 `UnknownVerdict`로 실패하고 조용히 통과하지 않는다 | 오케스트레이터 |
| `server/tests/test_prechk_verdicts.py` | 어휘 집합 동일성 · 레지스트리 불변성 · 교차 어휘 누출 거부 (8 tests) | 오케스트레이터 |
| 리포트 최상위 키 | `design.md` §5.1 표를 그대로 쓴다. M4는 `macro` 키의 값 형상만 만들고 리포트를 만들지 않는다 | `design.md` |

**읽기 전용 scout 병렬은 이 개정과 무관하게 계속 유효하다** — M0 세션과 병행해 scout 4개를 돌렸고 충돌 0건이었으며, 그중 2개가 판정 오류 1건(`ASSUMPTION-27`을 불완전한 후보 집합 위에서 단정)과 미해결 1건(슬롯 확립 분기)을 잡아냈다. **독립 감사를 세운 것이 실제로 값을 냈다.**
