---
id: SPEC-LDRENDER-001
title: "송신 층 연출 복원 — 층별 렌더링"
version: "0.1.0"
status: draft
created: 2026-10-01
updated: 2026-10-01
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.1 target"
module: "server/design/{song_cue_render,section_palette,energy,rig,song_cue_composer}.py, server/web/session.py, server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "lighting-render, layer-mapping, color-emission, effect-fixture-isolation, phaser-dispatch, readout-gate, console-send-layer"
tier: M
related_specs: [SPEC-LDDESIGN-001, SPEC-COPILOT-FXGEN-001, SPEC-COPILOT-FXLIB-001, SPEC-COPILOT-COLORMODE-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-LOOKLIB-001]
---

# SPEC-LDRENDER-001 — 송신 층 연출 복원: 층별 렌더링

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-01 | 최초 작성. 입력: t500 리드 8곡 판독 요약(`research-input-design-readout.md`), t499 8곡 오프라인 판독(`.moai/reports/t499/verdict.md`), t498 Rain 실기 파일럿(`.moai/reports/t498/verdict.md`). 감독 확정 범위(2026-10-01): R1·R2·R3·R4·R7 다섯 항목만, R5·R6 은 후속 SPEC. |
| 2026-10-01 | **plan-auditor iteration 1 FAIL(0.74) 대응 — D1~D7 해소, D9·D10 반영.** (D1) t497(승인 밖 `ClearAll`) 의 명시 판정 누락 — §4 에 Out-of-Scope 항목 신설, OUT 판정 + 사유 기록(§4 의 다른 카드 판단 산문도 존재하지 않던 "§5/§6 카드 판단" 상호참조를 걷어내고 제자리 산문으로 정정). (D2) REQ-004 의 층→색 배정을 "확정 사실"에서 "인용 근거(§4b C3/§6.3) 있는 기본값 + §5 열린 결정 3"으로 전환하고, 동시 색 ≤2(지배색 1+액센트 1, §6.3) 가드를 명문화. (D3) REQ-007/AC-LDRENDER-006 의 검증 범위를 "전체 기구 디머 줄 1개"에서 "비액센트 큐가 공유하는 `fids` 선택 전체(색·포지션·페이저 포함)"로 확장. (D6) `rig.py:44` `RIG_LAYER_ROLES = ("key","back","effect","audience")`(closed, `docs/proposals/song-lighting-design-standard.md` §2c 근거) 와 `rig.py:305-308` 의 `declared_layers` 경로 `RigProfileError` 를 반영해 REQ-001 을 기존 3역할(key/back/effect)만으로 "3개 이상 층" 목표가 이미 달성됨을 명시하고, REQ-002(SIDE/WASH/MOVER)를 §5 열린 결정 2(옵션 a/b/c + 권장 기본값)로 재구성, M2 의존성을 plan.md 에 명시. (D7) REQ-009/M1 에 "읽기 전용 — 콘솔 쓰기 없음" 명문화. (D4) AC-LDRENDER-016 의 자기참조 Given(`AC-001~016`)을 `AC-001~015`로 정정. (D5) progress.md 의 AC 총량 오기(17개/AC-016·017)를 실제(16개/AC-015·016)로 정정. (D9, 비차단) REQ-003/011 의 `Where` 를 상태 조건에 더 맞는 `While`/`When` 으로 교체. (D10, 비차단) §5 결정 1건을 정본 `[NEEDS CLARIFICATION: ...]` 마커로 병기. REQ 총량·AC 총량은 16/16 으로 불변. |

## 1. 배경 — 설계 층은 맞게 만드는데 송신 층이 접는다

t499 가 8곡을 오프라인으로 판독한 결과(잰 값, `.moai/reports/t499/verdict.md`), **설계 층**(`song_cue_composer` 번들)은 곡마다 색 조합 2~4종·포지션 6~8종·효과 요청 6~36건을 만든다. 그런데 **송신 층**(`server/design/song_cue_render.py` `reviewed_song_commands`, `:1000`)을 거치면 다음으로 접힌다:

| 항목 | 설계 층 | 송신 층 (8곡 공통) |
|---|---|---|
| 곡 전체 색 | 색 이름 3~4종 | **1색**(7곡), DinoDino 2색은 우연(구간 분할 큐 회전 부작용 — 추정) |
| 기구 선택 | 매핑 카드에서 층별 역할 승인 | **86대 한 묶음**(`reviewed_song_commands` 의 단일 `fids` 인자, `:1000`) |
| 서로 다른 값을 받는 층(8그룹 중) | — | **최대 2개**(전체 값 + BACK) |
| 효과 | 요청 6~36건, 페이저 제안 104큐 | **0줄** |

t498 의 Rain 실기 파일럿(`.moai/reports/t498/verdict.md`)은 이 접힘이 가짜 콘솔만의 현상이 아님을 확인했다 — 가짜 콘솔 송신과 실기 송신이 W 채널 줄을 빼고 순서까지 같다(잰 값, §0). 기계 동작(큐 전환 타이밍·되읽기·기존 쇼 보존)은 전부 PASS 였으나 감독은 **0/5점**을 매겼다: 「조명의 변화가 거의 없어. 색상도 조명연출도 거의 없는데 큐가 구간에 맞게 넘어가는게 뭐가 중요해?」.

## 2. 이 SPEC 의 성격 — 송신 함수 하나의 복구, 설계 층은 거의 그대로

t499 §3 의 결론(코드 판독): **무대에 보이는 변화의 대부분이 송신 함수 한 곳(`reviewed_song_commands`)에서 접힌다** — 단일 `fids`(모든 큐가 86대 전체를 쓴다) · `palette[0]`만 소비 · `_back_layer_value_lines` 가 `role == "back"`만 찾음(그 외 역할은 읽지 않음) · 효과 허용값(`fx.permitted`)을 읽는 송신 경로가 없음 · 콘솔 풀에 없는 페이저는 고지만 되고 큐에서 빠짐. 설계 층의 문제는 디머 대역(§6 이탈, P6)과 Finale 블라인더 근거(P9) 둘뿐이고, 이 SPEC 은 그 둘을 다루지 않는다(§4 Out of Scope — R5/R6은 후속 SPEC).

## 3. 요구사항 (GEARS)

### 3.1 R1 — 층별 렌더링 (REQ-LDRENDER-001~003)

[HARD — D6 전제] `server/design/rig.py:44` `RIG_LAYER_ROLES = ("key", "back", "effect", "audience")` 는 **닫힌** 어휘다(독스트링: "a role outside this set is a caller typo, not a new role the standard recognises" — 정본 근거는 `docs/proposals/song-lighting-design-standard.md` §2c "role층 → 그룹 매핑(key/back/effect/audience)"). `_confirm_song_layer_mapping` → `declared_layers`(`server/web/session.py:7550-7556`) 경로로 이 집합 밖의 역할 문자열이 들어가면 `rig.py:305-308` `_build_layers` 가 `RigProfileError` 를 던진다 — 이것이 D6 가 지목한 실제 충돌 지점이다. 같은 정본 §4a I1 은 세 층(키=프런트/얼굴, 백=실루엣/깊이, 이펙트=빔/에어리얼)만으로 인텐시티 구조를 정의한다 — 즉 **이 SPEC 의 완료 조건("3개 이상 층이 다른 값을 받는다")은 기존 key/back/effect 세 역할만으로 이미 달성 가능하다**(t499 §1 의 "무대 층" 집계 방식 — 값을 안 받은 기구는 트래킹으로 직전 값을 잇는다는 가정 — 을 그대로 적용하면, key 값·back 값·effect 의 트래킹된/액센트 값 셋이 이미 서로 다른 세 버킷이다). 따라서 SIDE/WASH/MOVER 세분화(구 REQ-002)는 **R1 의 필수 요건이 아니라 선택적 확장**이며, 그 결정은 §5 결정 2 로 분리한다.

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-001 | **When** 구간 큐가 조립되고 승인된 층 매핑(`layer_mapping`, SPEC-LDDESIGN-001 결함 6 의 `_confirm_song_layer_mapping` 산출물)에 **닫힌 어휘 `key`/`back`/`effect`(`RIG_LAYER_ROLES`, `audience` 제외 — 이 리그엔 매핑 그룹 없음, `rig.py:109-113` 주석)** 중 2개 이상의 역할이 그룹 번호로 해석되어 있으면, 송신기(`reviewed_song_commands`) **shall** 역할마다 독립된 그룹 주소 값 줄을 낸다 — 현재 `_back_layer_value_lines`(`song_cue_render.py:621`)가 `role == "back"`만 찾는 것을 일반화해, `key`/`back`/`effect` 세 역할을 순회하는 다중 역할 함수로 대체한다(SIDE/WASH/MOVER 는 포함하지 않는다 — §5 결정 2). 줄 순서는 기존 규율(전체 기구 키 디머 줄 → 역할별 델타 줄 → 효과 recall → 액센트)을 유지한다 — 콘솔 트래킹(last-wins)이 뒤에 온 역할 줄을 이긴다. | 코드 판독: `song_cue_render.py:621-644` `_back_layer_value_lines`(`role == "back"` 단일 분기), `rig.py:44`(`RIG_LAYER_ROLES` 닫힌 3+1 역할), `docs/proposals/song-lighting-design-standard.md:167`(I1, 키/백/이펙트 3층 정의). 잰 값: t499 §3 P4("매핑 카드가 KEY·FOH=Key/Front, BACK=Back, BLIND·STROBE·HAZE=Effect/Beam을 제안하고 승인을 받았는데 BACK만 쓰인다") |
| REQ-LDRENDER-002 | [NEEDS CLARIFICATION: SIDE/WASH/MOVER 접두-접미 복합 그룹(`SIDE-L`/`SIDE-R`/`SIDE-ALL`, `WASH-U`/`WASH-D`/`WASH-ALL`, `MOVER-U`/`MOVER-D`/`MOVER-ALL`)의 역할 해석 방법 — §5 결정 2 참조, 3옵션 미확정] — 감독 확정 전까지 이 REQ 는 **보류**다. 세 옵션 모두 `RIG_LAYER_ROLES` 닫힌 어휘(위 [HARD] 단락)와의 충돌 여부가 갈린다: (a) 정본·`RIG_LAYER_ROLES` 튜플에 `side`/`wash`/`mover` 를 신규 역할로 추가, (b) 기존 역할로 흡수(예: MOVER→`effect` — 정본 I1 의 "이펙트=빔·에어리얼" 정의와 직접 부합, SIDE/WASH→`back` — I1 의 "백=실루엣·깊이"), (c) `RIG_LAYER_ROLES`/`declared_layers` 는 무변경, 송신기가 소비하는 원시 `layer_mapping` 리스트(`RigProfile` 를 거치지 않는 별도 경로 — `_back_layer_value_lines` 가 이미 이 리스트를 직접 읽는다)에만 새 역할 토큰을 추가하고 `declared_layers` 구성 시(`session.py:7550-7556`) `RIG_LAYER_ROLES` 소속 역할만 거른다. REQ-001 이 이미 "3개 이상 층" 목표를 충족하므로, 이 REQ 의 **권장 기본값은 "이번 SPEC 에서는 보류 — 별도 결정/후속 카드"**다(아래 §5 결정 2). | 코드 판독: `server/design/rig.py:44`(`RIG_LAYER_ROLES`), `:92-95`(SIDE/WASH/MOVER 접미 미매칭 주석), `:305-308`(`RigProfileError`), `server/web/session.py:7550-7556`(`declared_layers` 구성 — 필터링 전 상태). 실측(테스트 고정): `server/tests/test_layer_mapping_effect_role.py:119` `test_mover_and_wash_groups_remain_unmatched_documented_residual` |
| REQ-LDRENDER-003 | **While** 승인된 층 매핑에 해석된 역할이 1개 이하(단일 레이어 — SPEC-LDDESIGN-001 의 `_SINGLE_LAYER_WARNING` 경로)인 동안, 송신기 **shall** REQ-001 의 다중 역할 분기를 건너뛰고 오늘과 바이트 동일한 전체 기구 단일 값 송신으로 동작한다 — 매핑이 없는 리그를 이 REQ 가 막지 않는다. | 설계 규율: SPEC-LDDESIGN-001 §3.14(단일 레이어 경고), `_confirm_song_layer_mapping` 회귀 비파괴 요구 |

### 3.2 R2 — 색 전부 쓰기 (REQ-LDRENDER-004~006)

[HARD — D2 전제] 두 정본이 동시색 상한과 프런트 처리를 명시한다: `docs/proposals/song-structure-lighting-standard.md` §6.3("동시에 보이는 색은 최대 2개(지배색 1 + 액센트 1)"), `docs/proposals/song-lighting-design-standard.md` §4b C1("팔레트 3~5색: 베이스1+액센트1~2 … 구간은 팔레트 안에서만 순환")·C3("프런트(키층)는 중립/웜 화이트 유지 — 채도 색은 백층·이펙트층에"). 따라서 **팔레트 길이(`len(palette)`)가 2보다 커도 한 큐가 동시에 내보내는 구별 색은 최대 2개로 제한**되어야 하고, **KEY/FOH(프런트 필) 역할 그룹에 채도 있는 팔레트 원색을 그대로 싣는 것은 C3 와 충돌**한다 — 원래 문면(KEY/FOH·WASH 에 `palette[0]`)은 이 두 근거를 인용하지 않은 **미확정 배정**이었다(D2). 아래 REQ-004 는 그 배정을 §5 결정 3 의 열린 결정으로 낮추고, ≤2 색 가드만 REQ 로 확정한다.

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-004 | **When** 큐의 팔레트(`cue.color.palette`, `ColorPlan.palette: tuple[str, ...]`)가 2개 이상의 색을 담고 있으면, 색 송신기(`_song_color_value_lines`, `song_cue_render.py:556`) **shall** 그 큐가 동시에 내보내는 구별 색을 **최대 2개(지배색 1 + 액센트 1, §6.3)**로 제한하여 REQ-001 이 해석한 역할 그룹에 각각 별도 값 줄로 낸다 — `len(palette) > 2`여도 3번째 이후 색은 이 큐에서 발화하지 않는다(버리는 것이 아니라 §6.3 의 동시성 상한을 지키는 것 — 회차별 회전은 설계 층 R6 영역, §4 Out of Scope). **역할→색 배정은 [NEEDS CLARIFICATION: §5 결정 3] 미확정**이다 — 기본값 후보는 지배색을 `back`(채도 색 허용, C3)에, KEY/FOH 는 정본 C3 에 따라 **중립/웜 화이트 성향을 유지**(팔레트 원색을 그대로 받지 않음)하는 것이나, 감독 확인 전에는 송신기가 둘 중 하나를 임의로 확정하지 않는다 — REQ-005/006 의 색-변화 측정과 §6.3 상한 준수는 이 배정 결정과 무관하게 먼저 닫는다. 오늘처럼 `palette[0]` 하나만 내고 나머지를 버리는 동작은 종료한다. | 코드 판독: `song_cue_render.py:596` `name = palette[0]`(주석 자신이 "보조색·유보색·언더페인팅은 M3 의 몫"이라고 DESCOPE를 명시 — 이 SPEC 이 그 M3 의 색 송신 반쪽을 닫는다). 잰 값: t499 §3 P1("설계 색 이름 3~4종 → 송신 RGB 1"). 정본: `song-structure-lighting-standard.md` §6.3, `song-lighting-design-standard.md` §4b C1/C3 |
| REQ-LDRENDER-005 | **The** 구간 큐 간 색 변화 **shall** 송신 층에서 측정 가능하다 — 설계 층(`_section_palette_choice`/`_arc_palette`, `section_palette.py`)이 구간마다 바꾸는 보조색 칸이 REQ-004 경유로 실제 콘솔 값 줄에 반영되어야 한다. 이 REQ 는 설계 층의 팔레트 로직을 바꾸지 않는다 — 이미 바뀌는 값을 송신이 더 이상 버리지 않는 것만 요구한다. | 잰 값: t499 §3 P2("P1×P2 = 송신 색 변화 0 — 설계는 맞게 '주색 + 바뀌는 보조색'을 만들고, 송신은 안 바뀌는 칸만 보낸다") |
| REQ-LDRENDER-006 | **While** 곡의 `color_usage`/`palette_mode`(SPEC-COPILOT-COLORMODE-001) 가 `modulate` 가 아닌 값(`single`/`per_chorus`)으로 확정되어 있으면, REQ-004 의 보조색 송신 **shall** 그 모드가 `_section_palette_choice` 에서 이미 결정한 베이스/악센트 값을 그대로 소비한다 — 새 색 선택 로직을 이 SPEC 이 만들지 않는다. `single` 모드에서는 보조색 칸도 베이스와 동일해지므로(§D5), REQ-004 는 "다른 값이 없으면 중복 줄을 내지 않는다"로 자연히 처리된다(별도 분기 불필요). | SPEC-COPILOT-COLORMODE-001 §2 D5(`single`/`per_chorus` 동작 정의), 감독 결정 구속 조건 1(기존 곡별 스위치 존중) |

### 3.3 R3 — 효과 기구 분리 (REQ-LDRENDER-007~008)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-007 | **When** 층 매핑이 `effect` 역할(BLIND/STROBE/HAZE 그룹, `_LAYER_GROUP_ALIASES["effect"]`)을 해석하면, 비액센트 구간 큐가 내는 **모든 값 줄**(전체 기구 디머·색·포지션 프리셋·페이저 recall — `reviewed_song_commands` 가 `position_cue_bundle(sequence_no, plan, fids, extra_value_lines=(*color_lines, ..., *_phaser_cue_value_lines(cue, fids, ...), ...))` 호출 전체에 **공유하는 단일 `fids` 선택**)은 **shall not** 그 `effect` 역할 그룹의 기구를 포함한다 — 즉 송신기는 비액센트 큐의 공유 `fids` 자체에서 effect 역할 기구를 제외하며(디머 줄 하나만 좁히는 2차 선택을 따로 만들지 않는다), 색·포지션·페이저 줄도 같은 제외로 자동 적용된다(D3 — STROBE 가 Dimmer 외 다른 attribute 로 독립 구동될 가능성을 봉쇄). 효과 기구는 REQ-008 이 정의하는 액센트 줄(그 자체의 독립된 `Group <n>` 주소, 공유 `fids` 와 무관)에서만 값을 받는다. HAZE 는 LX-SEQ §11.2 작성 규칙 6(분위기 그룹은 Intensity 정합 비교에서 제외하되 트래킹 대상)에 따라 공유 `fids` 제외 대상이되, 곡 시작/종료 안전 큐(Block/Release, SPEC-LDDESIGN-001 REQ-053~054)에서는 명시적으로 관리된다 — 아무 통제 없이 방치되지 않는다. | 잰 값: t499 §3 P3′("블라인더·스트로브·헤이즈가 매 큐 전체 디머(후렴 100)를 받는다"). 코드 판독: `song_cue_render.py:1000-1055` `reviewed_song_commands`(단일 `fids` 가 `position_cue_bundle` 호출 + `_song_color_value_lines(cue, fids, ...)` + `_phaser_cue_value_lines(cue, fids, ...)` 전체에 공유됨, `:1028`·`:1044-1053`). 정본: LX-SEQ-SPEC-v2.1 §11.2 규칙 6 |
| REQ-LDRENDER-008 | **When** 액센트 큐(`cue.accent_fixture`, `_accent_fixture_value_lines`, `song_cue_render.py:647`)가 블라인더를 켜면, 그 값 줄 **shall** REQ-007 적용 후 기준(이전 비점등 상태, 통상 0)에서 **상승**하는 명시적 전체 밝기(기구 특성에 맞는 최댓값에 가까운 디머 값)를 낸다 — 오늘처럼 이미 전체 디머 100을 받은 효과 기구에 80을 추가로 덮어써 **역방향 하강**(100→80)이 되는 것을 금지한다. 복귀 큐는 기존대로 0으로 끈다(`_accent_fixture_value_lines` 둘째 분기 무변경). | 잰 값: t499 §3 P3′("절정 블라인더 줄은 오히려 100→80으로 내린다"), §1 비고("왜냐하면 Group 14 Dimmer At 80 의 80이 BACK(80)과 같아서"). t498 §0 큐 11 실측 |

### 3.4 R4 — 효과 송신 통로 (REQ-LDRENDER-009~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-009 | **When** 이 SPEC 의 run-phase 가 착수되면, 첫 마일스톤은 **shall** `fx.permitted = 0`(8곡 전부, t499 §3 P5a)의 원인을 실기 콘솔에서 측정한다 — **이 측정은 읽기 전용이다(응답기 `state`/`prop` 류 조회만 — 콘솔 쓰기 0건, `exec`/`Store` 류 커맨드 발화 금지)**. 구체적으로 `RigInventory.capability_fids["effect"]`(`server/design/rig.py:170-180`)가 `RigFixtureRecord.capabilities`(패치 레코드의 **명시 선언** 필드, `:138-146` "never inferred from type_name")로만 채워지는 경로와, `build_rig_profile(patch=..., groups={})`(`server/web/session.py:7445`, `:7556`)가 그 `patch` 인자를 어떤 능력-판독 파이프라인(`server/design/rig_capability_read.py`/`capability_verdict.py`, SPEC-COPILOT-PRECHK-001 계열)에서 채우는지를 실기로 대조한다 — 지금까지의 "리그 능력 판독 실패" 서술은 추정이며, 이 REQ 는 그 추정을 코드 판독 + 실기 측정으로 확정하는 것 자체를 완료 조건으로 한다(아래 측정하지 않으면 R4 의 나머지 REQ 는 착수하지 않는다). | 코드 판독: `server/design/energy.py:262-273` `_fx_axes`(`rig.has_capability("effect")` 가 False 면 budget 0) + `rig.py:138-146`(capabilities 비선언=0). 추정 표기(t499 §3 P5a): "원인 추정: energy.py:262 `_fx_axes`가 리그에 `EFFECT_AXIS_CAPABILITY` 기구가 없으면 0" |
| REQ-LDRENDER-010 | **When** 큐의 설계 층 효과 허용값(`fx.permitted`)이 0보다 크고 송신기가 그 효과에 대응하는 페이저 제안 라벨(`_phaser_label_for_cue`, `song_cue_render.py:481`)을 갖고 있으며 콘솔 풀 재조회(`phaser_slots`)가 그 라벨을 해석했으면, 송신기 **shall** `_phaser_cue_value_lines`(이미 존재하는 함수, `:508`)가 내는 recall 줄을 실제로 명령 목록에 포함한다 — 오늘 이 경로가 호출은 되지만 `phaser_slots` 가 항상 빈 매핑으로 넘어와(또는 허용이 0이라 애초에 호출 전제가 안 섬) 8곡 전부 효과 송신 0줄이 되는 지점을 REQ-009 의 측정 결과에 따라 닫는다. | 코드 판독: `song_cue_render.py:508-530`(이미 구현된 recall 함수, 호출부 `:1051` 존재). 잰 값: t499 §3 P5a′("`fx.permitted`를 읽는 곳은 `session.py:1355`(표시용)뿐이고 `reviewed_song_commands`는 안 읽는다") |
| REQ-LDRENDER-011 | **When** 제안된 페이저 라벨이 콘솔의 현재 풀 재조회 결과에 없으면(`phaser_slots.get(label) is None`), 시스템 **shall** [NEEDS CLARIFICATION: R4 방법 선택 — 아래 §5 결정 1] 둘 중 하나의 방법으로 처리한다: (a) SPEC-COPILOT-FXGEN-001/FXLIB-001 의 기존 저작 경로(`compose_fx`/`instantiate_fx`, `server/fx/instantiate.py` `build_fx_preset_bundle`/`select_preset_number`)를 호출해 그 페이저를 사전에 풀에 만들고(콘솔 쓰기이므로 기존 승인 게이트를 거친다), 다음 재조회에서 해석되게 한다, 또는 (b) 그 큐의 리뷰/보고 문면에 "페이저 미배정: `<라벨>`" 고지를 유지하되 그 사유를 감독이 보는 리뷰 표면(변경 스택 또는 분석 요약)에 **눈에 띄게** 올린다(오늘처럼 회신에만 묻히지 않는다). 어느 쪽이든 큐의 다른 값 줄(디머·색·포지션)은 영향받지 않는다. | 잰 값: t499 §3 P5b(8곡 전부 "페이저 제안 104큐 → 송신 0, 8곡 회신 모두 '페이저 미배정' 문구 있음"). 구속 조건 4(새 콘솔 쓰기 경로는 감독 승인 필요) |
| REQ-LDRENDER-012 | **When** 효과 송신(REQ-010·011)이 결정되면, 보고기(기존 2단 보고 선례, `server/looks/report.py`)의 효과 관련 문면 **shall** 요청(`fx.requested`)·허용(`fx.permitted`)·송신(실제 recall 줄 수) 3계를 구분해 적는다 — t499 요약표(§1)와 같은 3열 구조를 운영 리뷰 표면에도 노출한다. | t499 §1 표 구조("효과: 요청/허용/페이저 제안 큐 → 송신 줄") |

### 3.5 R7 — 연출 판독 게이트 (REQ-LDRENDER-013~016)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-013 | **The** 시스템 **shall** t499 의 판독 도구(`.moai/reports/t499/readout.py`)의 핵심 판정 로직(송신 색 수·구간 큐당 다른 값 받는 층 수·송신 효과 줄 수)을 제품 코드로 승격한 재사용 가능한 게이트 함수를 제공한다 — 보고서 전용 스크립트가 아니라 송신 경로가 호출할 수 있는 모듈 함수로 만든다. | 카드 지시문 R7, `.moai/reports/t499/readout.py`(364행, 기존 로직 소재) |
| REQ-LDRENDER-014 | **When** 콘솔에 쓰기 직전인 곡의 송신 명령 목록이 REQ-013 의 게이트를 거쳐 다음 중 하나라도 만족하면(색 2~3종 미만, 구간 큐 중 다른 값을 받는 층이 3개 미만인 큐 존재, 효과를 요청한 곡인데 송신 효과 줄 0), 시스템 **shall** 감독에게 경고를 띄운다 — 송신을 차단하지 않는다(SPEC-LDDESIGN-001 REQ-052 의 비차단 경고 선례를 따른다). | 카드 지시문 R7 완료 조건, 구속 조건(헤드룸 경고 비차단 선례) |
| REQ-LDRENDER-015 | **While** 곡의 `palette_mode`/`color_usage` 가 기본값(`modulate`)이 아니면, REQ-014 의 색 수 경고 **shall** 그 축에 한해 n/a(미해당)로 처리된다 — 비기본 모드를 결함으로 오판하지 않는다. | 구속 조건 1(조명 규칙은 기본값, 전곡 강제 아님) |
| REQ-LDRENDER-016 | **The** REQ-013 게이트 **shall** 양성·음성 대조군 둘로 검증 가능하다 — 고치기 전 Rain 송신 목록(t498 §0, 색 1·층 2·효과 0)에서는 경고가 발동하고, 통과 기준을 만족하는 합성 송신 목록에서는 발동하지 않는다. | AC 완료 조건(아래 §5 AC 매핑), 날조 대조군 관례(moai-memory 교훈 — 안 쏘면 검사가 아니다) |

## 4. 제외 범위 (Out of Scope)

### Out of Scope — R5 구간 밝기 대역

구간 역할(intro/verse/chorus/bridge)별 §6 밝기 대역 일치(P6)는 이 SPEC 의 범위 밖이다. t499 가 확인한 대로 이것은 **송신 붕괴가 아니라 설계 층(`song_cue_composer.py:715` `_dimmer_data`, D 레벨 중앙값 산정) 값의 문제**이고, 송신은 그 값을 그대로 옮길 뿐이다. 후속 SPEC 이 D 레벨 표(`_D_LEVEL_ROWS`)와 구간 역할의 관계를 다룬다.

- 구간 역할별 디머 대역 재산정, `_dimmer_data`/`_D_LEVEL_ROWS` 로직 변경.

### Out of Scope — R6 후렴 상승·드롭 앞 어둠

연속 후렴이 같은 룩을 유지하면서 새 요소 하나씩 더하는 상승 사다리(§7, P7)와 첫 후렴 진입 전 어둠(§8, P8)은 이 SPEC 이 다루지 않는다. 둘 다 설계 층의 회차 간 비교·눈 리셋 로직을 건드리는 **다른 종류의 작업**이며, 감독이 2026-10-01 에 다음 SPEC 으로 명시적으로 분리했다.

- 연속 후렴 포지션/모션 상승 사다리 로직.
- 첫 후렴 진입 전 눈 리셋/감광 큐 삽입 로직.

### Out of Scope — 색 정밀 매칭(크로스 기구 색 일치)

주색·보조색을 **보내는 것**(R2)과 그 색이 서로 다른 기종 간에 정확히 같은 색으로 보이도록 **맞추는 것**(CIE 좌표 기반 정밀 매칭, 카드 t432/t433/t478)은 다른 문제다. 이 SPEC 은 후자를 다루지 않는다 — 표준 팔레트 10색의 RGB 값을 그대로 송신한다.

- CIE 색공간 정밀 매칭, 기구별 색 보정 테이블.
- 표준 팔레트 10색 자체의 확장(SPEC-COPILOT-COLORPRESET-001 영역).

### Out of Scope — 곡 사이 룩 재사용 방지

연속한 두 곡이 같은 룩/색 조합을 고르는지 여부(카드 t491)는 **곡 내부 송신 복원**이라는 이 SPEC 의 축과 다른 축(곡 간 다양성)이다. t491 자신이 "착수 전 재실측·감독 재확인 필요"로 적어 둔 상태이며, 이 SPEC 의 R-항목 어디에도 그 축이 없다.

- `SongLookMemory`/곡 간 색-룩 반복 방지 장치 복원.

### Out of Scope — UI 컨셉 패널 데이터 원천(카드 t492)

SPEC-LDDESIGN-001 의 완료 후속으로 감독이 2026-09-28 에 명시적으로 분리한 항목(불릿 클릭 설명 원천, 탭 2·3 데이터)이다. 이 SPEC 은 **송신 층**(콘솔로 나가는 명령)만 다루고 **UI 컨셉 패널**(화면 표시)은 건드리지 않는다.

### Out of Scope — 승인 게이트 밖 ClearAll(카드 t497)

t497(「전부-거절」 모드에서도 앱이 승인 카드 밖으로 `ClearAll` 1줄을 내보낸 사실, t474 run5 실측)은 **OUT**이다 — 사유: t497 은 **승인 게이트 충실도**(콘솔에 보내는 줄이 승인받은 목록과 정확히 일치하는가) 결함이고, 이 SPEC 의 축은 **송신 층이 설계 층의 연출 의도를 얼마나 보존해 렌더링하는가**(층·색·효과 복원)다 — 둘은 같은 송신 경로를 지나지만 서로 다른 성질의 문제다(하나는 "승인 안 된 줄이 나간다", 다른 하나는 "승인된 색·층·효과가 줄어든다"). 카드 자신의 문면("개별 배차 금지 — 8곡 실기 테스트를 끝낸 뒤 수정 사항을 모아 SPEC 으로 진행")은 "이 SPEC 의 입력"이라는 뜻이지 "이 SPEC 의 REQ 로 만들라"는 뜻이 아니며, t497 이 가리키는 수정 대상(`run_commands`/`gate.screen()` 의 dedupe·면제 집합 또는 프로그래머 상태 커맨드 분류)은 R1·R2·R3·R4·R7 어디에도 해당하지 않는다. **이 SPEC 의 R7 게이트(REQ-013~016)는 콘솔 쓰기 직전의 "연출 품질" 사전 경고일 뿐, 승인 밖으로 나가는 개별 커맨드 줄을 탐지·차단하는 장치가 아니다** — R7 이 t497 을 대신 닫는다고 오인하지 않도록 명시한다. 카드는 큐에 남긴다(queued) — 승인 게이트 충실도를 다루는 후속 SPEC/카드의 몫이다.

- 승인 밖 커맨드(`ClearAll` 등) 탐지·차단, `run_commands`/dedupe/면제 집합(`_PROGRAMMER_STATE_COMMANDS`) 로직 변경.

### Out of Scope — 도구 결함 카드(t494·t495·t496)

세 카드 모두 이 SPEC 의 "송신 층 연출 복원"이라는 축과 무관한 **별개 결함**이다 — t494(`moai spec drift` 파서가 이 SPEC 과 무관한 다른 SPEC 을 누락), t495(주석 한 줄의 만료 정정), t496(UI 테스트 사본 drift 방지 대조 시험) 전부 도구/문서 결함이며 송신 층 렌더링과 무관하다.

## 5. 열린 결정 — 감독 확인 필요

1. [NEEDS CLARIFICATION: R4 방법 선택 — REQ-LDRENDER-011] 페이저가 콘솔 풀에 없을 때: (a) `compose_fx`/`instantiate_fx` 로 사전 생성(새 콘솔 쓰기 경로, 승인 필요) vs (b) 큐별 고지만 강화(쓰기 없음, 효과는 여전히 0줄). 아래 plan.md §C 가 두 선택지의 비용·리스크를 더 적는다. 권장 기본값: 없음(안전·효과 트레이드오프라 감독 판단이 선행해야 함) — M5 착수 전 확정 필요.

2. [NEEDS CLARIFICATION: R1 SIDE/WASH/MOVER 역할 해석 — REQ-LDRENDER-002] `RIG_LAYER_ROLES` 닫힌 어휘(D6, 위 §3.1 [HARD] 단락)와의 관계를 포함해 3옵션 중 하나를 고른다:
   - **(a) 정본·`RIG_LAYER_ROLES` 확장** — `docs/proposals/song-lighting-design-standard.md` §2c 와 `rig.py:44` 튜플에 `side`/`wash`/`mover` 를 신규 역할로 추가. 비용: 정본 문서 개정(이 SPEC 범위를 넘는 거버넌스 결정) + `RigProfile` 를 소비하는 다른 모든 곳(예: `song_cue_composer.py` 의 `has_layer()` 호출부)에 새 역할이 파급되는지 전수 재검토 필요. 리스크: 낮음(구현) / 중간(거버넌스 — 감독이 "표준이 인정하는 역할"을 늘리는 결정).
   - **(b) 기존 역할로 흡수** — `_LAYER_GROUP_ALIASES` 에 새 역할 문자열을 추가하지 않고 기존 토큰 집합에 합류시킨다(예: `MOVER-*`→`effect`, 정본 I1 "이펙트=빔·에어리얼"과 직접 부합; `SIDE-*`/`WASH-*`→`back`, I1 "백=실루엣·깊이"). 비용: 가장 낮음(기존 역할의 `frozenset` 에 토큰만 추가, `RigProfileError` 위험 없음). 리스크: SIDE/WASH/MOVER 가 BACK/effect 와 **같은 값**을 받으므로, REQ-001 이 이미 달성한 "3개 이상 층" 목표에 **추가 층 구분을 더하지 못한다**(새 값 버킷이 생기지 않는다) — 순수 어휘 정리 효과만 있다.
   - **(c) 역할 어휘는 닫아 두고 원시 주소만 확장** — `RIG_LAYER_ROLES`/`declared_layers`(`session.py:7550-7556`)는 무변경(새 역할 필터링 유지)하되, 송신기가 직접 읽는 원시 `layer_mapping` 리스트(`RigProfile` 를 거치지 않는, `_back_layer_value_lines` 가 이미 쓰는 그 경로)에만 `side`/`wash`/`mover` 토큰을 추가해 **역할 이름 없이 그룹 번호로만** 차등 렌더링한다. 비용: 중간(두 역할-어휘 계층이 생긴다는 것을 코드 주석·plan.md 에 명확히 남겨야 함 — 안 그러면 다음 독자가 혼동). 리스크: `has_layer()` 류 규칙(I1~I3·L6/L7)은 이 신규 그룹을 여전히 인식하지 못한다(의도된 제약 — 렌더링 전용 확장이므로).
   - **권장 기본값**: REQ-001 이 이미 key/back/effect 세 역할만으로 완료 조건을 충족하므로, **이 SPEC 에서는 보류** — SIDE/WASH/MOVER 세분화는 별도 카드/후속 SPEC 으로 미루고 M2 는 (a)/(b)/(c) 결정과 무관하게 착수 가능하다. 감독이 세분화를 지금 원하면 (c)를 2순위 기본값으로 권한다(정본 미개정 + 코드 변경 최소).

3. [NEEDS CLARIFICATION: R2 층→색 배정 — REQ-LDRENDER-004] 어느 역할이 지배색(채도 있는 팔레트 원색)을 받고 어느 역할이 중립/웜 화이트를 유지하는지(§4b C3). 권장 기본값: 지배색은 `back`, `key`(KEY/FOH)는 중립/웜 화이트 유지 — 단 이 배정은 색-변화(REQ-005)·≤2색 상한(REQ-004 본문) 자체를 막지 않으므로 M3 는 착수 가능하고, 배정만 감독 확인 후 확정한다.
