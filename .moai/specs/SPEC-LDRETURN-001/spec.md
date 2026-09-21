---
id: SPEC-LDRETURN-001
title: "절정 복귀 큐 값 충돌 회피 — 공개 진입점 성공 삽입 경로 확보"
version: "0.2.0"
status: in-progress
created: 2026-09-20
updated: 2026-09-21
author: jaihyun
priority: P2
phase: "Lighting Copilot v1.0 target"
module: "server/looks/songcue.py"
lifecycle: spec-anchored
tags: "songcue, climax-duration-cap, value-line-collision, withheld-return, card-t427"
tier: M
related_specs: [SPEC-LDCLIMAX-001, SPEC-LDACCENT-001]
---

# SPEC-LDRETURN-001 — 절정 복귀 큐 값 충돌 회피

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-20 | 최초 작성. 큐 카드 t427 — SPEC-LDCLIMAX-001 sync-auditor F4(2026-09-20, 브랜치 `WT-color-snap-climax@f6279509`) 후속. `build_songcue_bundle(bpm=...)` 공개 진입점을 통한 절정 지속시간 상한 복귀 큐 삽입이 반복 룩(같은 `look_id`)에서 구조적으로 거의 항상 실패하는 결함을 닫는다. |
| 2026-09-21 | **감독 결정 반영** — §5 의 `[NEEDS CLARIFICATION: Dimmer 넛지 상한]` 마커 해소. 옵션 A(권장안 그대로 채택) — `Dimmer` 넛지에 단계 수 상한을 두지 않는다, `DARKNESS_FLOOR`(20)까지 무제한 탐색. REQ-LDRETURN-001 에 "단계 수 제한 없이" 구절을 더해 이 전제를 명시적으로 굳혔다 — REQ/AC 의 나머지 문면은 애초에 이 전제로 쓰여 있어 의미 변경은 없다. 상세: §5(해소 기록), plan.md §F M1(해소 기록). |

## 1. 배경

### 1.1 실측 (2026-09-20, `origin/main` `42fbd1c8` 기준 — SPEC-LDCLIMAX-001,
PR #473 병합 직후)

SPEC-LDCLIMAX-001 이 만든 절정 지속시간 상한 메커니즘(정본 §6 "절정의 지속
시간에 상한이 있다")은 `_apply_climax_duration_cap`(`server/looks/
songcue.py:1331`)이 `blinder_or_flash`/`strobe_hit` 를 실은 저장 큐마다 상한
박수 뒤에 복귀 큐를 끼운다. 복귀 큐(`_climax_return_bundle`,
`songcue.py:1283`)는 그 절정 큐가 **사다리를 오르기 전의 기준 값**
(`climax.selection.look.attributes`)을 그대로 재방출한다(REQ-LDCLIMAX-007).

같은 SPEC 이 F1(critical, sync-auditor)로 고친 결함이 이 SPEC 의 발단이다
— 고치기 전에는 삽입된 복귀 큐가 `_guard_bundle_collision`(`songcue.py:2320`)
을 **우회**했다. 고친 뒤(`build_songcue_bundle`, `songcue.py:1041`, 1132행에서
`_apply_climax_duration_cap` 반환 직후 `_guard_bundle_collision(capped)` 를
재호출)에는 가드가 정상 작동하지만, 그 결과 **새로운 결함(F4)이 드러났다**:

1. **`blinder_or_flash`/`strobe_hit` 는 룩 자신의 값을 바꾸지 않는다**
   (`_rung_applied`, `songcue.py:3259-3263` — 두 칸 모두 `return tuple(values)`,
   실제 무대 명령은 `_accent_fixture_commands` 가 별도 그룹으로 낸다). 따라서
   복귀 큐가 재방출하는 "기준 값"은, 같은 룩이 (경쟁 없이) **처음 저장됐을
   때의 값 라인과 글자 그대로 같다** — 같은 룩이 반복되는 곡에서는 그 값을
   이미 쥔 큐가 거의 항상 존재한다(1회차).
2. **`_guard_bundle_collision` 은 이 충돌을 정확히 잡아 거절한다.** 면제
   대상(`is_programmer_state` — `Clear`/`ClearAll`/`Fixture <n>`/`Group <n>`)이
   아닌 명령이 번들 안에서 두 번 나오면 `SongCueBundleError` 를 던진다
   (`songcue.py:2320-2337`). 복귀 큐의 값 라인이 1회차 저장 큐의 값 라인과
   충돌하면 이 예외가 던져지고, **번들 전체 조립이 실패한다** — 이 곡의
   다른 모든 큐까지 포함해서.
3. **증거: fix 커밋 자신이 성공 단언을 실패 단언으로 뒤집었다.**
   `TestClimaxDurationCapIsWiredThroughBuildSongcueBundle
   .test_bpm_argument_reaches_the_duration_cap_pass`(`server/tests/
   test_songcue_climax_001.py:503`)는 원래 삽입 성공(`climax_returns`
   비어있지 않음)을 단언했으나, F1 수정 뒤에는 같은 6회 반복 코러스
   픽스처가 `SongCueBundleError` 를 던지는 것을 단언하도록 뒤집혔다 —
   즉 그 배선 확인 시험 자신이 **결함 재현 사례**로 판명됐다. 새로
   추가된 `TestClimaxReturnCueCollisionIsGuarded`(`songcue.py:539`)도
   같은 결함을 3회 반복 픽스처로 직접 재확인한다.
4. **삽입 성공을 보이는 시험은 전부 가드를 우회한다.**
   `TestClimaxReturnIsInsertedForALongClimax`(`test_songcue_climax_001.py:375`)는
   `songcue_module._apply_climax_duration_cap` 을 **직접** 불러 삽입
   성공을 확인한다 — `_guard_bundle_collision` 재호출이 있는 공개 진입점
   `build_songcue_bundle(bpm=...)` 을 거치지 않는다. **공개 진입점을 통한
   성공 삽입을 재는 시험이 이 저장소 어디에도 없다** — 이것이 이 SPEC 이
   닫는 결함이다.

### 1.2 지금 당장 터지지 않는 이유

유일한 프로덕션 호출부 `server/orchestrator/tools.py:3230`
(`prepare_songcue` 안, `tools.py:2954`)의 `build_songcue_bundle(...)` 호출은
`bpm` 인자를 넘기지 않는다(SPEC-LDCLIMAX-001 이전부터 그랬다 — 이 SPEC
직전 실측 확인). `bpm=None` 이면 `_apply_climax_duration_cap` 은 즉시
`bundle` 을 그대로 돌려준다(REQ-LDCLIMAX-009, "안 재고는 안 쓴다") — 상한
패스 자체가 안 돌아 F4 도 발동하지 않는다. 다만 근처에 이미
`density_bpm = _confirmed_density_bpm(confirmed)`(`tools.py:3177`)가 계산돼
있어, 후속 SPEC 이 `bpm=density_bpm` 한 줄만 추가하면 배선이 끝난다 —
그 순간 F4 가 프로덕션에서 발동한다. `bpm` 프로덕션 배선은 이 SPEC 의
범위 밖이다(§4 Out of Scope) — 이 SPEC 은 그 배선이 도달했을 때 실패하지
않을 선행 조건만 만든다.

## 2. 범위 결정

이 SPEC 은 `_apply_climax_duration_cap` 이 복귀 큐를 끼우는 순간의 **값
충돌 회피** 한 가지만 다룬다. 절정 지속시간 상한 메커니즘 자체(상한 박수
계산, 삽입 조건, 재번호 매기기)는 SPEC-LDCLIMAX-001 이 이미 확정했고 이
SPEC 은 건드리지 않는다 — 오직 "끼우려는 복귀 큐의 값 라인이 이미 번들
안에 있을 때 무엇을 하는가"만 새로 정의한다.

기존 저장소가 값 충돌을 다루는 두 선례를 재사용 후보로 조사했다
(카드 t427 이 직접 지목):

- **`_yield_bundle`(`songcue.py:1950`)** — 드롭/3회차 이상 반복 라벨에
  자리를 비켜주려고 **상대(rival)** 의 `Dimmer` 를 `_HIT_STEP`(5) 만큼
  `DARKNESS_FLOOR`(20) 쪽으로 단계적으로 내려, 충돌하지 않는 첫 값을
  찾는다. 못 찾으면 `None` — 원래 스킵이 그대로 선다.
- **`SongCueWithheldAccent`(`songcue.py:730`) 계열** — 채울 수 없는 이유를
  숨기지 않고 명시적으로 보고하는 패턴. `SongCueWithheldMovement`/
  `Darkness`/`Accent` 셋 다 `section`/`cue_number`/`reason`/`detail` 을
  공통 핵심 필드로 갖되, 도메인별 추가 필드가 있다(`Movement` 는 `band`,
  `Darkness` 는 `drop_cue_number` + `cue_number: int | None`) — 완전히
  같은 모양은 아니다.

## 3. 요구사항

### 3.1 값 충돌 회피 — 복귀 큐 자신의 넛지 (REQ-LDRETURN-001~005)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRETURN-001 | **When** 절정 지속시간 상한이 복귀 큐를 끼우려는데 그 복귀 큐의 값 라인이 이미 이 번들 안(이 패스에서 앞서 끼운 다른 복귀 큐 포함, 프로그래머 상태 명령 면제 대상 제외)에 존재하면, 복귀 큐 조립은 **SHALL** 그 복귀 큐 자신의 `Dimmer` 값을 고정된 단계 크기만큼, **단계 수 제한 없이** `DARKNESS_FLOOR` 에 닿을 때까지 반복해서 내려가며 비충돌 값을 탐색한다(감독 결정 2026-09-21, 옵션 A — §5) — **기존에 저장된 다른 어떤 큐의 값도 바꾸지 않는다**(원본 절정 큐를 포함해서). | 카드 t427, `_yield_bundle`(단계 크기 `_HIT_STEP`) 선례의 탐색 알고리즘 재사용 — 면제 판정은 `is_programmer_state` 재사용. 감독 결정 2026-09-21 |
| REQ-LDRETURN-002 | **When** REQ-001 의 탐색이 비충돌 값을 찾으면, 복귀 큐는 **SHALL** 그 값으로 저장되어 번들 충돌 가드를 통과하고, `build_songcue_bundle(bpm=...)` 공개 진입점을 통해 성공적으로 삽입된다. | F4 가 지적한 공개 진입점 성공 경로 부재를 닫는다 — 충돌 가드 구현은 `_guard_bundle_collision` |
| REQ-LDRETURN-003 | **Where** 절정 큐의 룩이 `Dimmer` 축을 갖지 않거나, REQ-001 의 탐색이 `DARKNESS_FLOOR` 에 닿을 때까지도 비충돌 값을 찾지 못하면, 복귀 큐 조립은 **SHALL** 그 복귀 큐의 삽입을 유보하고 사유를 명시적으로 보고한다(REQ-008) — 원본 절정 큐의 값은 바뀌지 않는다. `DARKNESS_FLOOR` 도달이 유일한 탐색 종료 조건이다(감독 결정 2026-09-21, 옵션 A — 별도 단계 수 상한은 두지 않는다). | `SongCueWithheldAccent` 선례, "조용히 넘어가지 않는다" 보고 규율, 감독 결정 2026-09-21 |
| REQ-LDRETURN-004 | **While** REQ-001~003 의 충돌 회피가 적용되는 동안, 절정 지속시간 상한이 새로 끼우는 복귀 큐가 아닌 기존 큐(원본 절정 큐 포함)의 값 라인과 사다리·유보 보고(SPEC-LDACCENT-001)는 **SHALL** 이 SPEC 이전과 동일하게 유지된다. | REQ-LDCLIMAX-011 의 "기존 큐 값 결정 경로를 안 건드린다" 를 새로 끼우는 복귀 큐 자신에게만 좁혀 확장 |
| REQ-LDRETURN-005 | **When** 충돌이 전혀 없는 경우(SPEC-LDCLIMAX-001 골든 시험이 재는 시나리오), 복귀 큐 조립은 **SHALL** 이 SPEC 이전과 바이트 동일한 값(사다리를 오르기 전 기준 값)을 재방출한다 — 충돌 회피 로직은 실제 충돌이 있을 때만 개입한다. | `TestClimaxReturnIsInsertedForALongClimax` 골든 대조군 무회귀 |

### 3.2 공개 진입점 배선 확인 (REQ-LDRETURN-006~007)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRETURN-006 | **When** `build_songcue_bundle(bpm=...)` 가 반복 룩(같은 `look_id`)이 `blinder_or_flash`/`strobe_hit` 에 도달하고 다음 큐가 상한 밖에 있는 조합을 받으면, 공개 진입점은 **SHALL** `SongCueBundleError` 를 던지지 않고 성공적으로 번들을 반환한다(REQ-001~002 의 넛지 경로) — 이것이 sync-auditor F4 가 지적한, "공개 진입점을 통해 삽입 성공을 재는 시험이 없다"는 커버리지 공백을 닫는다. | F4, 카드 t427 필수 요구 |
| REQ-LDRETURN-007 | **Where** 이 곡의 BPM 이 선언되지 않았으면(REQ-LDCLIMAX-009), 이 SPEC 의 충돌 회피 메커니즘은 **SHALL** 아무 것도 하지 않는다 — 상한 패스 자체가 안 돌므로 이 SPEC 이전과 바이트 동일하다. | REQ-LDCLIMAX-009 와 같은 방향, "안 재고는 안 쓴다" |

### 3.3 유보 보고 (REQ-LDRETURN-008)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRETURN-008 | **When** 복귀 큐가 유보되면(REQ-003), 번들 보고는 **SHALL** 그 사실을 원래의 절정 지속시간 삽입 보고(`SongCueClimaxReturn`)와 구분 가능한 별도의 명시적 필드로 노출한다 — 조용히 넘어가지 않는다. | `SongCueWithheldMovement`/`Darkness`/`Accent` 와 같은 "명시적이고 눈에 보이는" 보고 패턴 — `SongCueClimaxReturn` 정의는 `songcue.py:748` |

## 4. 비목표 (Out of Scope)

### Out of Scope — bpm 프로덕션 배선

- `server/orchestrator/tools.py:3230`(`prepare_songcue`)의
  `build_songcue_bundle` 호출에 `bpm=density_bpm` 을 실제로 넘기는 배선은
  이 SPEC 이 하지 않는다. 이 SPEC 은 그 배선이 도달했을 때 실패하지 않을
  **선행 조건**만 만든다. `density_bpm` 이 이미 `tools.py:3177` 에서
  계산되고 있다는 사실만 후속 SPEC 을 위해 기록해 둔다.

### Out of Scope — 다축 충돌 회피

- `Dimmer` 축이 없거나 소진됐을 때 `Zoom`/`Iris`/색 축으로 확장해 추가
  탐색하는 것은 이 SPEC 의 범위 밖이다. `_yield_bundle` 이 이미 정립한
  `Dimmer` 전용 관행만 재사용하고, 그 관행이 실패하면 유보(REQ-003)로
  접는다.

### Out of Scope — 재번호 매기기의 교차 참조 갱신

- `collides_with_cue_number`, `withheld_movement`/`withheld_darkness`/
  `withheld_accents` 안의 `cue_number` 등, 복귀 큐 삽입으로 뒤 큐 번호가
  밀릴 때 갱신되지 않는 교차 참조 필드들은 SPEC-LDCLIMAX-001 의 `design.md`
  §2.2 가 이미 이 SPEC 의 판정 범위 밖으로 명시했고, 이 SPEC 도 그 경계를
  그대로 물려받는다.

### Out of Scope — 상대(rival) 값 넛지

- `_yield_bundle` 처럼 **이미 저장된 실제 큐**(예: 1회차)의 값을 물러서게
  하는 방식은 이 SPEC 이 채택하지 않는다 — plan.md B1 이 이미 확정한
  설계 결정이며(넛지 대상은 새로 끼우는 복귀 큐 자신뿐, REQ-LDCLIMAX-011
  위반 회피), §5 감독 결정(2026-09-21)의 대상이 아니다. §5 는 오직
  `Dimmer` 넛지 단계 상한만 다룬다.

## 5. 감독 결정 기록 (2026-09-21 해소)

plan.md §F M1 의 `[NEEDS CLARIFICATION: Dimmer 넛지 상한]` 마커가 다루던
질문은 감독 확인으로 해소됐다. 마커가 요약하던 질문:

값 충돌 회피가 복귀 큐 자신의 `Dimmer` 를 넛지하면(REQ-001), 재방출되는
값은 더는 "사다리를 오르기 전 기준 값"과 **바이트 동일하지 않다** —
근처 값(±5 단위)이 된다. 정본 §6 은 "통제된 룩으로 복귀한다"고만 말하고
바이트 동일성을 요구하지 않지만, REQ-LDCLIMAX-007 의 현재 문면("기준
값(통제된 룩)으로 되돌린다")과 그 골든 시험(`test_a_return_cue_lands_at_
the_two_beat_cap`, `Dimmer At 60` 단정)은 정확한 재현을 전제로 쓰여 있다
(단, 이 시험은 REQ-005 무충돌 시나리오라 이 SPEC 이전과 바이트 동일하게
남는다 — 이 절의 결정 대상이 아니다). 실제 충돌이 있을 때 `Dimmer` 를
최대 몇 단계까지 넛지하는 것이 "통제된 룩"의 허용 범위인가?

**결정 — 옵션 A(권장안 그대로 채택): 상한 없음, `DARKNESS_FLOOR`(20)까지
무제한 탐색.** 복귀 큐 자신의 `Dimmer` 값을 `_HIT_STEP`(5) 단위로
`DARKNESS_FLOOR` 쪽으로 내려가며 비충돌 값을 찾는다 — 몇 단계가 걸리든
상한을 두지 않는다. 유보(REQ-003, `SongCueWithheldClimaxReturn`)는
`Dimmer` 축이 없거나, 넛지가 `DARKNESS_FLOOR` 까지 내려갔는데도 비충돌
값을 못 찾았을 때만 발동한다 — 그 밖의 경우엔 단계 수만으로 유보하지
않는다.

**근거(감독이 수용한 이유)**: 절정이 끝난 뒤에도 무대가 극단적인 절정
룩에 그대로 머무르는 상태가, 사다리 회차와 정확히 같지 않은 값으로
복귀하는 것보다 나쁘다 — 정본 §6 이 직접 금지하는 상태가 바로 그것이다
("절정의 지속시간에 상한이 있다... 그 뒤 통제된 룩으로 복귀한다"). 작은
상한(기각된 옵션 B — 예: 2단계 = ±10)을 뒀다면 유보 빈도가 늘어 오히려
§6 위반 상태(절정 룩 고착)가 더 자주 남는다. 옵션 A 는 유보를 최소화해
"통제된 룩으로 복귀"를 실제로 대부분의 경우 지킨다 — 단, `Dimmer` 만
바뀌고 색·빔은 그대로이므로(§4 Out of Scope, AC-LDRETURN-002) 시각적으로는
"더 차분해진 같은 색 룩"일 뿐이다. 셋째 옵션(계속 `SongCueBundleError`
를 던지되 메시지만 개선)은 사용자가 요구한 AC(공개 진입점을 통한 성공
삽입)를 원천 봉쇄하므로 이미 기각됐다 — 이번 해소로도 바뀌지 않는다.

**이 결정이 REQ/AC 문면을 바꾸지 않는 이유**: REQ-LDRETURN-001~008 과
AC-LDRETURN-001~008 은 애초에 "`DARKNESS_FLOOR` 까지 무제한" 을
전제로 쓰여 있었다 — REQ-001 의 "`DARKNESS_FLOOR` 쪽으로", REQ-003 의
"`DARKNESS_FLOOR` 에 닿을 때까지도" 는 별도 단계 상한을 두지 않는
서술이었다. 이 해소는 그 전제를 감독이 사후 확정한 것이지, REQ/AC 의
의미를 바꾸는 새 결정이 아니다 — REQ-001 에 "단계 수 제한 없이" 구절을
추가해 이 전제를 명시적인 문면으로 굳혔을 뿐이다.

Implementation Kickoff Approval 은 이 해소를 전제로 통과한다.

## 6. 검증 수단의 한계 (착수 전 고지)

이 SPEC 은 순수 로컬 계산 계층(`server/looks/songcue.py`)만 건드린다 —
콘솔 왕복이 필요한 요구사항이 없다. 판정은 전부 `uv run pytest` +
`ruff check`/`ruff format --check` 로 닫힌다.

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| REQ-001~002, 005 (넛지 성공 경로, 무충돌 회귀) | pytest, `_apply_climax_duration_cap` 단위 + `build_songcue_bundle` 공개 진입점 | 아니오 |
| REQ-003, 008 (유보 경로 + 보고) | pytest, `Dimmer` 축 없는 룩 / 바닥 소진 픽스처 | 아니오 |
| REQ-004 (기존 큐 불변) | 기존 SPEC-LDCLIMAX-001/LDACCENT-001 골든 시험 재실행 | 아니오 |
| REQ-006 (공개 진입점 성공 삽입 — F4 커버리지 공백을 직접 닫는 시험) | pytest, `build_songcue_bundle(bpm=...)` 반복 룩 픽스처, `climax_returns` 비어있지 않음 + 예외 없음 단언 | 아니오 |
| REQ-007 (`bpm=None` 무영향) | pytest, 기존 `TestUndeclaredBpmIsANoOp` 재실행 | 아니오 |
