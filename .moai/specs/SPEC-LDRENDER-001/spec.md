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

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-001 | **When** 구간 큐가 조립되고 승인된 층 매핑(`layer_mapping`, SPEC-LDDESIGN-001 결함 6 의 `_confirm_song_layer_mapping` 산출물)에 KEY/FOH·BACK·SIDE·WASH·MOVER·effect 중 2개 이상의 역할이 그룹 번호로 해석되어 있으면, 송신기(`reviewed_song_commands`) **shall** 역할마다 독립된 그룹 주소 값 줄을 낸다 — 현재 `_back_layer_value_lines`(`song_cue_render.py:621`)가 `role == "back"`만 찾는 것을 일반화해, 매핑된 모든 역할을 순회하는 다중 역할 함수로 대체한다. 줄 순서는 기존 규율(전체 기구 키 디머 줄 → 역할별 델타 줄 → 효과 recall → 액센트)을 유지한다 — 콘솔 트래킹(last-wins)이 뒤에 온 역할 줄을 이긴다. | 코드 판독: `song_cue_render.py:621-644` `_back_layer_value_lines`(`role == "back"` 단일 분기). 잰 값: t499 §3 P4("매핑 카드가 KEY·FOH=Key/Front, BACK=Back, BLIND·STROBE·HAZE=Effect/Beam을 제안하고 승인을 받았는데 BACK만 쓰인다") |
| REQ-LDRENDER-002 | **The** 역할→그룹 매핑 어휘(`server/design/rig.py` `_LAYER_GROUP_ALIASES`) **shall** 접두-접미 복합 그룹 이름(`SIDE-L`/`SIDE-R`/`SIDE-ALL`, `WASH-U`/`WASH-D`/`WASH-ALL`, `MOVER-U`/`MOVER-D`/`MOVER-ALL`)을 각각 `side`/`wash`/`mover` 역할로 해석한다 — 접두 토큰(하이픈 앞)만으로 판정하고 부분 문자열 추측(RG5)은 하지 않는다. 이 세 역할은 현재 정확 토큰 미일치로 매핑되지 않은 채 남아 있다(코드 주석이 이미 "접두사/부분 일치 정책 결정이 먼저 필요"로 명시). | 코드 판독: `server/design/rig.py:92-95`("MOVER-U/D/ALL·WASH-U/D/ALL은 접미사가 붙어 있어 여전히 정확 일치하지 않는다 — 별도 카드로 남긴다"). 실측(테스트 고정): `server/tests/test_layer_mapping_effect_role.py:119` `test_mover_and_wash_groups_remain_unmatched_documented_residual` |
| REQ-LDRENDER-003 | **Where** 승인된 층 매핑에 해석된 역할이 1개 이하(단일 레이어 — SPEC-LDDESIGN-001 의 `_SINGLE_LAYER_WARNING` 경로)이면, 송신기 **shall** REQ-001 의 다중 역할 분기를 건너뛰고 오늘과 바이트 동일한 전체 기구 단일 값 송신으로 동작한다 — 매핑이 없는 리그를 이 REQ 가 막지 않는다. | 설계 규율: SPEC-LDDESIGN-001 §3.14(단일 레이어 경고), `_confirm_song_layer_mapping` 회귀 비파괴 요구 |

### 3.2 R2 — 색 전부 쓰기 (REQ-LDRENDER-004~006)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-004 | **When** 큐의 팔레트(`cue.color.palette`, `ColorPlan.palette: tuple[str, ...]`)가 2개 이상의 색을 담고 있으면, 색 송신기(`_song_color_value_lines`, `song_cue_render.py:556`) **shall** 주색(`palette[0]`)은 REQ-001 이 해석한 KEY/FOH·WASH 역할 그룹에, 보조색(`palette[1]` 이후)은 BACK·SIDE 역할 그룹(또는 역할 미해석 시 REQ-003 의 단일-레이어 폴백)에 각각 별도 값 줄로 낸다 — 오늘처럼 `palette[0]` 하나만 내고 나머지를 버리지 않는다. | 코드 판독: `song_cue_render.py:596` `name = palette[0]`(주석 자신이 "보조색·유보색·언더페인팅은 M3 의 몫"이라고 DESCOPE를 명시 — 이 SPEC 이 그 M3 의 색 송신 반쪽을 닫는다). 잰 값: t499 §3 P1("설계 색 이름 3~4종 → 송신 RGB 1") |
| REQ-LDRENDER-005 | **The** 구간 큐 간 색 변화 **shall** 송신 층에서 측정 가능하다 — 설계 층(`_section_palette_choice`/`_arc_palette`, `section_palette.py`)이 구간마다 바꾸는 보조색 칸이 REQ-004 경유로 실제 콘솔 값 줄에 반영되어야 한다. 이 REQ 는 설계 층의 팔레트 로직을 바꾸지 않는다 — 이미 바뀌는 값을 송신이 더 이상 버리지 않는 것만 요구한다. | 잰 값: t499 §3 P2("P1×P2 = 송신 색 변화 0 — 설계는 맞게 '주색 + 바뀌는 보조색'을 만들고, 송신은 안 바뀌는 칸만 보낸다") |
| REQ-LDRENDER-006 | **While** 곡의 `color_usage`/`palette_mode`(SPEC-COPILOT-COLORMODE-001) 가 `modulate` 가 아닌 값(`single`/`per_chorus`)으로 확정되어 있으면, REQ-004 의 보조색 송신 **shall** 그 모드가 `_section_palette_choice` 에서 이미 결정한 베이스/악센트 값을 그대로 소비한다 — 새 색 선택 로직을 이 SPEC 이 만들지 않는다. `single` 모드에서는 보조색 칸도 베이스와 동일해지므로(§D5), REQ-004 는 "다른 값이 없으면 중복 줄을 내지 않는다"로 자연히 처리된다(별도 분기 불필요). | SPEC-COPILOT-COLORMODE-001 §2 D5(`single`/`per_chorus` 동작 정의), 감독 결정 구속 조건 1(기존 곡별 스위치 존중) |

### 3.3 R3 — 효과 기구 분리 (REQ-LDRENDER-007~008)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-007 | **When** 층 매핑이 `effect` 역할(BLIND/STROBE/HAZE 그룹, `_LAYER_GROUP_ALIASES["effect"]`)을 해석하면, 전체 기구 키 디머 값 줄(`PositionCuePlan.dimmer`, `position_cue_bundle` 이 내는 기본 선택)은 **shall not** 그 `effect` 역할 그룹을 포함한다 — 효과 기구는 REQ-008 이 정의하는 액센트 줄에서만 값을 받는다. HAZE 는 LX-SEQ §11.2 작성 규칙 6(분위기 그룹은 Intensity 정합 비교에서 제외하되 트래킹 대상)에 따라 전체 디머에서는 빠지되, 곡 시작/종료 안전 큐(Block/Release, SPEC-LDDESIGN-001 REQ-053~054)에서는 명시적으로 관리된다 — 아무 통제 없이 방치되지 않는다. | 잰 값: t499 §3 P3′("블라인더·스트로브·헤이즈가 매 큐 전체 디머(후렴 100)를 받는다"). 코드 판독: `song_cue_render.py:1000` 의 단일 `fids`(선택 집합에 효과 그룹을 뺄 통로가 없음). 정본: LX-SEQ-SPEC-v2.1 §11.2 규칙 6 |
| REQ-LDRENDER-008 | **When** 액센트 큐(`cue.accent_fixture`, `_accent_fixture_value_lines`, `song_cue_render.py:647`)가 블라인더를 켜면, 그 값 줄 **shall** REQ-007 적용 후 기준(이전 비점등 상태, 통상 0)에서 **상승**하는 명시적 전체 밝기(기구 특성에 맞는 최댓값에 가까운 디머 값)를 낸다 — 오늘처럼 이미 전체 디머 100을 받은 효과 기구에 80을 추가로 덮어써 **역방향 하강**(100→80)이 되는 것을 금지한다. 복귀 큐는 기존대로 0으로 끈다(`_accent_fixture_value_lines` 둘째 분기 무변경). | 잰 값: t499 §3 P3′("절정 블라인더 줄은 오히려 100→80으로 내린다"), §1 비고("왜냐하면 Group 14 Dimmer At 80 의 80이 BACK(80)과 같아서"). t498 §0 큐 11 실측 |

### 3.4 R4 — 효과 송신 통로 (REQ-LDRENDER-009~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-009 | **When** 이 SPEC 의 run-phase 가 착수되면, 첫 마일스톤은 **shall** `fx.permitted = 0`(8곡 전부, t499 §3 P5a)의 원인을 실기 콘솔에서 측정한다 — 구체적으로 `RigInventory.capability_fids["effect"]`(`server/design/rig.py:170-180`)가 `RigFixtureRecord.capabilities`(패치 레코드의 **명시 선언** 필드, `:138-146` "never inferred from type_name")로만 채워지는 경로와, `build_rig_profile(patch=..., groups={})`(`server/web/session.py:7445`, `:7556`)가 그 `patch` 인자를 어떤 능력-판독 파이프라인(`server/design/rig_capability_read.py`/`capability_verdict.py`, SPEC-COPILOT-PRECHK-001 계열)에서 채우는지를 실기로 대조한다 — 지금까지의 "리그 능력 판독 실패" 서술은 추정이며, 이 REQ 는 그 추정을 코드 판독 + 실기 측정으로 확정하는 것 자체를 완료 조건으로 한다(아래 측정하지 않으면 R4 의 나머지 REQ 는 착수하지 않는다). | 코드 판독: `server/design/energy.py:262-273` `_fx_axes`(`rig.has_capability("effect")` 가 False 면 budget 0) + `rig.py:138-146`(capabilities 비선언=0). 추정 표기(t499 §3 P5a): "원인 추정: energy.py:262 `_fx_axes`가 리그에 `EFFECT_AXIS_CAPABILITY` 기구가 없으면 0" |
| REQ-LDRENDER-010 | **When** 큐의 설계 층 효과 허용값(`fx.permitted`)이 0보다 크고 송신기가 그 효과에 대응하는 페이저 제안 라벨(`_phaser_label_for_cue`, `song_cue_render.py:481`)을 갖고 있으며 콘솔 풀 재조회(`phaser_slots`)가 그 라벨을 해석했으면, 송신기 **shall** `_phaser_cue_value_lines`(이미 존재하는 함수, `:508`)가 내는 recall 줄을 실제로 명령 목록에 포함한다 — 오늘 이 경로가 호출은 되지만 `phaser_slots` 가 항상 빈 매핑으로 넘어와(또는 허용이 0이라 애초에 호출 전제가 안 섬) 8곡 전부 효과 송신 0줄이 되는 지점을 REQ-009 의 측정 결과에 따라 닫는다. | 코드 판독: `song_cue_render.py:508-530`(이미 구현된 recall 함수, 호출부 `:1051` 존재). 잰 값: t499 §3 P5a′("`fx.permitted`를 읽는 곳은 `session.py:1355`(표시용)뿐이고 `reviewed_song_commands`는 안 읽는다") |
| REQ-LDRENDER-011 | **Where** 제안된 페이저 라벨이 콘솔의 현재 풀 재조회 결과에 없으면(`phaser_slots.get(label) is None`), 시스템 **shall** [감독 결정 대기 — 아래 §5 결정 항목 1] 둘 중 하나의 방법으로 처리한다: (a) SPEC-COPILOT-FXGEN-001/FXLIB-001 의 기존 저작 경로(`compose_fx`/`instantiate_fx`, `server/fx/instantiate.py` `build_fx_preset_bundle`/`select_preset_number`)를 호출해 그 페이저를 사전에 풀에 만들고(콘솔 쓰기이므로 기존 승인 게이트를 거친다), 다음 재조회에서 해석되게 한다, 또는 (b) 그 큐의 리뷰/보고 문면에 "페이저 미배정: `<라벨>`" 고지를 유지하되 그 사유를 감독이 보는 리뷰 표면(변경 스택 또는 분석 요약)에 **눈에 띄게** 올린다(오늘처럼 회신에만 묻히지 않는다). 어느 쪽이든 큐의 다른 값 줄(디머·색·포지션)은 영향받지 않는다. | 잰 값: t499 §3 P5b(8곡 전부 "페이저 제안 104큐 → 송신 0, 8곡 회신 모두 '페이저 미배정' 문구 있음"). 구속 조건 4(새 콘솔 쓰기 경로는 감독 승인 필요) |
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

### Out of Scope — 도구 결함 카드(t494·t495·t496)

세 카드 모두 이 SPEC 의 "송신 층 연출 복원"이라는 축과 무관한 **별개 결함**이다(§5 카드 판단 참조).

## 5. 열린 결정 — 감독 확인 필요

1. **R4 방법 선택(REQ-LDRENDER-011)** — 페이저가 콘솔 풀에 없을 때: (a) `compose_fx`/`instantiate_fx` 로 사전 생성(새 콘솔 쓰기 경로, 승인 필요) vs (b) 큐별 고지만 강화(쓰기 없음, 효과는 여전히 0줄). 아래 plan.md §C 가 두 선택지의 비용·리스크를 더 적는다.
2. **R1 역할 매핑 접두 정책(REQ-LDRENDER-002)** — 접두 토큰 매칭(`SIDE-L`→`side`)으로 확정할지, 아니면 접미사까지 보존해 `side_left`/`side_right` 세분 역할을 만들지. 이 SPEC 의 기본안은 전자(굵은 역할만, L/R/U/D 구분은 안 함)이며, AC 는 "그룹마다 선택"(3개 이상 층 구분)까지만 요구한다 — 세분이 필요하면 별도 결정.
