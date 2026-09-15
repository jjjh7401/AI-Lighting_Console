---
id: SPEC-LDCOMPILE-001
title: "Director 시맨틱 검증·축별 timing lowering·capability 판정"
version: "0.1.0"
status: in-progress
created: 2026-09-14
updated: 2026-09-15
author: jaihyun
priority: P1
phase: "Lighting Director v1.0 target"
module: "server/director"
lifecycle: spec-anchored
tags: "lighting-director, validation, compiler, axis-timing, capability, conflict-detection"
tier: L
---

# SPEC-LDCOMPILE-001

## 1. 목적과 경계

외부 `lighting-director` 플러그인이 만든 계획을 **판정하고, 실제 콘솔이 보존할 수 있는
형태로 낮추는** 층이다. 저장은 하지 않고(형제 `SPEC-LDSTORE-001`), 실행도 하지 않는다
(형제 `SPEC-LDRECV-001`). 이 층이 내는 것은 `ValidationReport` 와 frozen artifact 뿐이다.

이 SPEC 의 핵심 주장은 하나다 — **보존할 수 없으면 지원한다고 말하지 않는다.** parser 가
받아들이는 것과 emitter 가 실제로 콘솔에 남기는 것은 다르고, 그 차이를 조용히 메우는 것
(clamp·quantize·대체 preset·필드 제거)이 이 층이 막아야 하는 실패다.

### 1.1 우산 SPEC 과의 관계

`SPEC-LDPLUGIN-001` 은 **우산으로 유지**된다. wire shape·의미 규칙·hash 의 단일 원본은
우산의 `contract.md` 이며 이 자식은 그것을 재정의하지 않고 참조한다.

| 규범 | 위치 |
|---|---|
| typed action 의미·timing·rule ID | `../SPEC-LDPLUGIN-001/contract.md` §7, §8 |
| `ValidationReport` shape | `../SPEC-LDPLUGIN-001/contract.md` §6.3, `schemas/exchange.schema.json` |
| compiler 불변식 | `../SPEC-LDPLUGIN-001/design.md` §5 |
| 구현할 fidelity 작업 | `../SPEC-LDPLUGIN-001/plan.md` §3 — **단, 전제 셋이 노화했다. §6 참조** |
| 소비할 자료구조 | `SPEC-LDSTORE-001` (`ContextSnapshot`, immutable plan revision) |
| 분할 근거·형제 목록 | `../../reports/ldplugin-001/split-proposal.md` |

### 1.2 REQ / AC id 보존

`../SPEC-LDPLUGIN-001/spec.md:45` 가 id 안정성을 규정하므로 원래 `REQ-LDPLUGIN-0NN` /
`AC-LDPLUGIN-0NN` 을 그대로 승계한다. 새 번호를 붙이면 `contract.md` 의 조항 참조가 끊긴다.

이 SPEC 이 소유하는 id: `REQ-LDPLUGIN-008` ~ `014` (7건).

### 1.3 형제 의존

이 층은 `SPEC-LDSTORE-001` **뒤**다. 검증기는 `LDSTORE` 의 `service.py` 가 이미 열어 둔
주입 seam(`PlanValidator` Protocol)에 들어간다 — 새 통로를 만들지 않는다. `LDSTORE` 의
기본 stub 은 `blocked` 만 답하므로, 이 SPEC 이 닫히는 날 `ready_for_review` 가 처음 도달한다.

## 2. 범위 결정

- **검증 순서는 계약 §8 `LD-VAL-001` 이 정한 그대로다**: source identity → time/reference →
  tracking/FX → capability/fidelity → safety → approval freshness. 순서를 바꾸지 않는다 —
  뒤 단계가 앞 단계의 결론을 전제하므로 순서가 곧 의미다.
- **하나라도 execution-critical blocking 이면 `compiled.available = false`, `outcome = blocked`**
  다. 나머지 action 이 정상이어도 전체가 막힌다. 부분 적용은 이 층이 만들 수 있는 상태가 아니다.
- **진단은 모든 요청 action 에 최소 하나**씩 붙는다. 변경·누락·지원 불가 필드는 leaf JSON
  Pointer 를 추가한다. 조용한 수용은 진단 부재가 아니라 `before/after` 둘 다
  `present=false` + 사유로 표현한다.
- **simulation 은 축별·fixture 별이다.** group 단위로 뭉치면 겹친 group 이 같은 fixture 의
  같은 축을 쓰는 충돌이 안 보인다 (`LD-CONFLICT-001`).
- **누락은 hold 다.** 지정하지 않은 action/axis 를 이전 show 나 programmer 값으로 상속하지
  않는다 (`LD-STATE-001`).
- **`derived` 는 계산·준비가 필요하다는 뜻이고 예술적 값을 바꿀 허가가 아니다** (계약 §6.3).
- **capability 는 실제 출력으로만 광고한다.** 선언·문서·parser 수용은 근거가 아니다
  (`LD-CAP-001`). 이 규칙이 §5 의 콘솔 게이트를 만든다.
- 기본 BPM 120 을 가정하지 않는다. tempo 불명은 `unsupported` 이지 기본값 대입이 아니다
  (`LD-TIME-002`).

## 3. 안정 요구사항

`SHALL` 은 필수다. 아래 7건은 `../SPEC-LDPLUGIN-001/spec.md` §3 에서 그대로 승계했다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDPLUGIN-008 | **When** typed action을 검증·컴파일하면 서비스는 **SHALL** 계약 §7 전체 expressive subset을 보존하며 임의 MA/Lua/OSC 문자열, clamp·quantize·대체 preset을 허용하지 않는다. | LD-CAP-001 |
| REQ-LDPLUGIN-009 | **When** cue/FX 시간을 해석하면 compiler는 **SHALL** 원음 첫 sample=0ms, 전곡 분할, 동일 시각 semantic cue, 독립 축 timing, confirmed beat 연속성·반올림·tempo 분할과 `playback`의 manual_go/trig_time·operator_go 의미를 보존한다. trig_time은 준비 cue를 포함한 최종 cue 순서의 delta를 저장하며 timecode event mapping은 지원하지 않는다. | LD-TIME-001/002/003; design §1 |
| REQ-LDPLUGIN-010 | **When** ready를 판정하면 validator는 **SHALL** omission=hold, 첫 full baseline·clean FX, explicit off/stop/release, 전 그룹 terminal assertion을 simulation으로 확인한다. | LD-STATE-001/002, LD-FX-001 |
| REQ-LDPLUGIN-011 | **When** 겹친 group/FX/transition이 있으면 validator는 **SHALL** 실제 fixture×axis로 충돌을 검출하고 순서 덮어쓰기나 누락으로 해결하지 않는다. | LD-CONFLICT-001 |
| REQ-LDPLUGIN-012 | **When** dark_move 또는 임의 시점 re-entry를 요청하면 compiler는 **SHALL** blackout·settle·full state·중간 fade·FX phase 복원을 증명하거나 blocking을 반환하고 authored reveal을 미루지 않는다. | LD-MIB-001, LD-REENTRY-001 |
| REQ-LDPLUGIN-013 | The capability service **SHALL** 실제 compiler+rig+target 출력으로 지원을 광고하며 기존 LXSEQ timing/FX stop/rate 메타데이터 갭을 plan §3의 실제 emitter 구현·관측으로 해소한다. | LD-CAP-001; plan §3 |
| REQ-LDPLUGIN-014 | **When** 검증하면 서비스는 **SHALL** source→time/ref→tracking/FX→fidelity→safety→freshness 순으로 전 계획을 검사하고 action/leaf JSON Pointer·before/after·이유로 진단하며 하나라도 critical blocking이면 compiled.available=false로 한다. | LD-VAL-001 |

## 4. 비목표

### 4.1 Out of Scope — 저장·인증·실행

- **저장·CAS·digest 계산은 포함하지 않는다** (`SPEC-LDSTORE-001`). 이 층은 저장된 immutable
  plan 을 읽고 판정만 한다.
- **사람 승인·apply·콘솔 쓰기는 포함하지 않는다** (`SPEC-LDRECV-001`). frozen artifact 를
  만들되 그것을 보내지 않는다. `ApprovalBinding` 을 발급하지 않는다.
- **MCP adapter·검토 UI 는 포함하지 않는다** (`SPEC-LDHOST-001` / `SPEC-LDUI-001`).
- 이 층은 OSC 를 만지지 않는다. `server/bridge/osc.py` 가 서버 전체의 유일한 송신 표면이며
  그 유일성은 아키텍처 테스트(AC-MVP-019)가 지킨다. frozen artifact 는 **bytes** 이고
  발화가 아니다.

### 4.2 Out of Scope — 예술 판정

- **무엇이 좋은 조명인가를 판정하지 않는다.** 이 층은 "요청한 것이 보존되는가" 만 답한다.
  finale 자동 상승·후렴 변주·에너지 기반 밝기 보정을 주입하지 않는다.
- 기존 예술 producer 둘(`server/looks/songcue.py`, `server/web/session.py` 의 `_ARC_*`)의
  cutover 는 `SPEC-LDCUTOVER-001` 이다. 이 층은 그것들을 호출하지 않는다.
- `artistic advisory` 는 nonblocking 이며 hard limit 을 완화할 수 없다 (`LD-SAFE-001`).

### 4.3 Out of Scope — 표현 범위 확장

- **무제한 Phaser 저작·임의 기종 지원을 추가하지 않는다** (우산 `plan.md` §3 마지막 문단).
- `timecode` event mapping·숨은 offset·자동 GO 는 이 wire version 에서 **지원하지 않는다**.
  변환해서 흉내내지 않고 거부한다 (`LD-TIME-003`).

## 5. 검증 수단의 한계 — 이 SPEC 은 콘솔 게이트다

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한 자동
판정 근거다. 기준선 (2026-09-14, HEAD `cde2744` 실측): `12928 passed, 31 skipped`.

그러나 이 SPEC 은 **로컬 pytest 로 닫을 수 없다.** `REQ-LDPLUGIN-013` 과 `LD-CAP-001` 이
capability 광고의 근거를 *"현재 compiler+rig+target 조합의 실제 출력"* 으로 못박았으므로,
축별 timing·FX cycle/phase·dark move 가 실제로 보존되는지는 **실기 콘솔(또는 인증 onPC+rig)
관측** 없이 확정할 수 없다.

로컬로 닫을 수 있는 것과 없는 것을 미리 갈라 둔다:

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| 검증 순서·진단 pointer·blocking 전파 (014) | 합성 입력 + pytest | 아니오 |
| 충돌 검출 (011) | fixture×axis simulation + pytest | 아니오 |
| ready 판정·terminal assertion (010) | simulation + pytest | 아니오 |
| 시간 해석·반올림·delta 계산 (009 의 계산부) | 순수 함수 + pytest | 아니오 |
| **emitter 가 축별 timing 을 실제로 보존하는가 (008·009 의 fidelity부)** | 콘솔/onPC 관측 | **예** |
| **capability 승격 (013)** | 콘솔/onPC 관측 | **예** |
| **dark move blackout·settle 실측 (012)** | 콘솔/onPC 관측 | **예** |

**미보존을 unsupported 로 답하는 것은 콘솔 없이 닫을 수 있다.** 즉 이 SPEC 의 안전한 부분
전체(거부·blocking·진단)는 로컬에서 완결되고, 콘솔이 필요한 것은 **지원으로 승격하는 쪽**
뿐이다. 이 비대칭이 착수 순서를 정한다 — 먼저 정직하게 전부 blocking 으로 만들고, 실측된
것만 하나씩 연다.

## 6. 착수 전 중단 조건 — 실측된 갈등 셋

우산 `plan.md` §3 은 이 SPEC 의 구현 작업 목록이다. **그 전제 다섯 중 셋이 노화했다**
(2026-09-14 실측, `cde2744` 트리, `server/` 아래 `.py` 601개 기준. 계기 확인: 양성 대조
`CueFade` 87건 · `Property 'Fade'` 3건).

### 6.1 축별 timing emitter 가 0건이다 — 규모 재산정 필요

계약 §7 은 `Timing={delay_ms,fade_ms,curve}` 를 intensity/color/pan/tilt/beam/fx **각각**에
요구하고 *"모든 axis timing을 명시하며 기본값 상속은 없다"* 고 규정한다. 저장소 실측:

| 후보 emitter | 건수 |
|---|---|
| `PanFade` · `TiltFade` · `ColorFade` · `BeamFade` | 각 **0** |
| `IndividualFade` · `AttributeFade` · `IndividualTime` | 각 **0** |
| `delay_ms` (`.py` 범위) | **0** |
| `CueFade` | **87** — 큐 단위 **스칼라 하나** |

그리고 `Property 'Fade'` 경로는 **금지**다 (`server/design/cue_fade.py:12` →
`docs/handoff/2026-08-15-timeline-workflow-handoff.md:19`).

즉 계약이 요구하는 표현의 핵심에 실측된 통로가 **하나도 없고**, 유일한 통로는 축을 구분하지
못한다. `LD-CAP-001` 을 그대로 적용하면 착수 시점의 정직한 답은 **모든 축별 timing =
unsupported + blocking** 이다.

[HARD] **그 unsupported 는 착수 시점의 정직한 상태이지 종착지가 아니다.** 우산
`spec.md:41` 이 두 가지를 함께 못박았다 — *"first release 표현 범위는 계약 §7 전체다.
알려진 intensity/color/position/beam, FX start/stop·cycle/phase, **독립 축별 fade/delay**,
accent 복귀, release, baseline/terminal state, MIB·re-entry의 fidelity까지 구현한다"* 그리고
*"구현 누락을 영구 unsupported로 남겨 릴리스 범위를 축소하지 않는다."*

따라서 C6(emitter 프로브)은 **선택 사항이 아니다.** 축별 timing 은 이름이 그대로 첫 릴리스
범위에 적혀 있고, 실측 통로가 0건이라는 사실이 그 요구를 면제해 주지 않는다. 이 SPEC 이
할 수 있는 것은 (가) 실측되기 전까지 정직하게 막는 것과 (나) emitter 를 만들어 실측하는
것 둘이며, (다) "영구 unsupported 로 두고 넘어가기"는 우산이 금지했다.

Tier L 로 잡았으나 **LOC 는 재지 않았다** — 새 emitter 문법을 프로브로 찾는 작업이
포함되므로 규모는 이 SPEC 의 첫 작업에서 재산정한다.

### 6.2 `fx_rate` 는 부재가 아니라 설계된 제외다

우산 `plan.md` §3 은 *"`fx_rate` 의 실제 소비 경로가 확인되지 않음"* 이라 적었다. 실측:
`server/design/profile.py:416-449` 가 소비한다 — 단 **대조 전용**이고 어느 분기에서도
`source` 가 되지 않는다. 코드가 사유를 함께 적어 두었다: *"사이클당 박수가 사람의 의도라
역산이 일의적이지 않아 채택 후보에 오르지 않습니다."*

[HARD] **이 제외를 "미구현"으로 읽고 `fx_rate` 를 BPM 근거로 승격하지 않는다.** 정책적
배제이며, 뒤집으면 사람의 의도(사이클당 박수)를 기계가 추측한 값으로 갈아끼운다. 계약
§7 의 `cycle_beats` 는 plan 이 명시하는 값이지 역산 대상이 아니다.

### 6.3 음수 ms — 계약과 코드가 정면으로 충돌한다

- 계약 §7: *"beat→ms 최종 경계는 ... 반올림"*, `LD-MIB-001`: *"compiler 준비 동작은
  negative ms 금지 ... 이 버전에는 음수 clock/pre-roll 필드가 없으므로"*.
- 코드 `server/lxseq/cue_time.py:26`: `CUE_TIME_PREROLL` — *"음수(PRE-ROLL) — `TrigTime` 에만
  쓰고 타임라인 투사에서는 뺀다."* 이미 구현된 경로다.

두 규범이 다르므로 **자식이 임의로 한쪽에 맞추지 않는다.** 착수 첫 작업에서 우산 수준으로
올려 판정을 받는다. 세 갈래가 있다: (가) Director 경로는 음수를 안 쓰고 기존 LXSEQ 경로만
쓴다 (경로 분리), (나) 계약을 개정해 pre-roll 필드를 넣는다, (다) `LD-MIB-001` 이 말한
*"원점을 확장한 새 audio/context"* 로 우회한다. 계약이 (다)를 이미 지시하므로 그것이 기본값
후보이지만, 기존 경로와의 관계는 판정이 필요하다.

### 6.4 노화하지 않은 전제 둘 (그대로 유효)

- `per_row_timing` 은 값 기록이고 actual emit 이 아니다 — `server/orchestrator/tools.py:6723`
  이 `dict[str, str]` 을 만들고 `:6760` 이 문자열로 join 해 `:6803` 에서 메타데이터로 전달한다.
- `fx_stopped_groups` 는 stop 메타데이터다 — `server/orchestrator/tools.py:6804` 한 자리.

## 7. 미검증 (착수 전 남은 것)

- **우산 `contract.md`(52.7KB) 전문 미독.** 이 SPEC 을 세울 때 §6.1·§6.3·§7·§8·§9 를 읽었다.
  §4(승인)·§10(state)·§11(예제·parity) 은 착수 시 읽어야 한다.
- **LOC 추정 없음.** §6.1 때문에 Tier L 이라는 등급 자체가 재산정 대상이다.
- **독립 판정 없음.** `plan-auditor` 는 이 저장소에서 착수 전 컨텍스트 초과로 죽는다
  (실측 적재 ≈114K 토큰). 이 SPEC 의 품질 판단은 전부 orchestrator 자기 검수이며,
  그 사실은 숨기지 않고 여기 적는다.
- **실기 콘솔 관측 0회.** §5 의 콘솔 게이트 항목 전부가 미측정이다.
