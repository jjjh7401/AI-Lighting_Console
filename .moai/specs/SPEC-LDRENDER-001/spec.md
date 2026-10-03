---
id: SPEC-LDRENDER-001
title: "송신 층 연출 복원 — 층별 렌더링"
version: "0.2.0"
status: implemented
created: 2026-10-01
updated: 2026-10-03
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
| 2026-10-01 | **감독 결정 4건 반영 — plan-auditor iteration 2 FAIL(0.68, 점수 역행) D11(major)·D12(critical) 동시 해소.** 리드 경유 감독 결정 4건이 도착해 §5 의 열린 결정 3건을 전부 해소했다(남은 열린 결정 **0건**). (결정 2 — D11+D12 직접 해소) "디머 0(꺼짐)은 층으로 세지 않는다. AC-001 = 모든 구간 큐가 LIT(디머>0) 역할 3개 이상의 서로 다른 값을 받아야 한다(큐 단위, 과반 아님)." REQ-001/AC-001 전면 재작성: "과반 이상" 문구를 전체 삭제하고 "모든 구간 큐"(블랙아웃·MIB 사전이동 큐만 명시 예외)로 교체, LIT-only 집계 규칙(꺼짐/트래킹 상태는 버킷에서 제외)을 REQ-001·REQ-013·REQ-014(R7 게이트)에 동일하게 명문화 — 게이트가 AC-001 과 같은 방식으로 센다. §3.1 의 [HARD—D6] 단락이 주장했던 "key/back/effect 만으로 이미 3층 달성"은 **LIT-only 규칙 하에서는 거짓**임을 확인하고 정정(비액센트 큐의 effect 는 R3 에 의해 항상 꺼져 있어 LIT 버킷에 안 들어간다 — key+back 뿐이면 버킷 2개) — 이로써 REQ-001 의 "3개 이상 LIT 층" 목표는 **결정 1(SIDE/WASH/MOVER 역할 확장)에 실질적으로 의존**하게 됐다. (결정 1 — 역할 어휘 옵션 (a)) `docs/proposals/song-lighting-design-standard.md` §2c(버전 올림) 와 `server/design/rig.py:44` `RIG_LAYER_ROLES` 를 `side`/`wash`/`mover` 로 확장하는 것을 REQ-002 로 승격(더 이상 `[NEEDS CLARIFICATION]` 아님) — 그룹 이름 해석은 하이픈 앞 접두 토큰 그대로(`SIDE-L/R/ALL`→`side`, `WASH-U/D/ALL`→`wash`, `MOVER-U/D/ALL`→`mover`, 부분 문자열 추측 없음), 기존 잔여 테스트(`test_mover_and_wash_groups_remain_unmatched_documented_residual`, `:119`)의 뒤집음을 명시적으로 기술. **표준 문서 자체의 편집은 이 plan-phase 산출물이 하지 않는다** — REQ-002 가 run-phase manager-develop 에게 그 편집(+버전 올림)을 요구하는 형태로만 존재한다(plan.md M2 신설). (결정 3 — R2 층→색 배정) `back`+`mover` = 지배색(원색), `side`+`wash` = 보조색(액센트), `key`(프런트) = 중립/웜 화이트(§4b C3) 로 REQ-004 를 확정하고 §5 결정 3 을 닫았다. **플래그(해소 아님)**: `key` 웜화이트가 §6.3 "최대 2개" 집계에 포함되는지는 엄격한 해석에 따라 상충할 수 있다 — 이 SPEC 은 웜화이트를 그 집계 밖(중립 기준광)으로 읽고 그 읽음을 §3.2 에 명시 플래그한다(발명하지 않음, 감독 재확인 여지를 남김). `color_usage=single` 일 때 보조색이 주색과 같아지면 중복 줄을 내지 않도록(REQ-006 그대로 적용) 그룹을 합쳐 한 줄만 낸다. (결정 4 — R4 옵션 (a) 전면 확정) REQ-011 을 `compose_fx`/`instantiate_fx` 사전 생성 단일 경로로 확정(옵션 (b) 제거), 기존 승인 게이트 재사용(새 무승인 경로 금지)을 명문화하고, 콘솔 풀 재조회로 프리셋 번호 충돌을 사전 검출하는 요구(덮어쓰기 금지, 충돌 보고)를 FXLIB REQ-FXLIB-012 의 기존 거부 의미론(`PRESET_OCCUPIED` 등) 재사용으로 추가, 페이저 2스텝 생성 규율(값→`Step 2`→값, FXLIB/FXGEN 기존 번들 형상 재사용)을 인용 각주로 명시. REQ-002/REQ-011 모두 기존 REQ ID 에 **병합**했다(새 REQ ID 추가 없음) — Tier M 상한(REQ/AC 각 16) 을 넘기지 않기 위함, 넘겼다면 병합하거나 티어 상향을 보고하라는 지시에 따른 선택. REQ 총량·AC 총량은 **16/16 불변**. §5 열린 결정은 **0건**(전부 해소). |
| 2026-10-03 | **sync 전 정렬 — REQ-007/AC-006 문면을 run-phase 리드 결정 (g) 의 실제 구현(outcome-equivalent)에 맞춤.** M5(카드 t501)가 REQ-007 원문이 요구하던 공유 `fids` 자체의 fid 수준 뺄셈을 구현 불가로 확인했다(그룹 멤버십 판독 경로 부재, 2차 반증 — GROUPGEN SPEC M0 + 이 SPEC 자신의 M2 독스트링). 리드는 fid 뺄셈 대신 그룹 주소 override(디머만 0 처리)로 같은 결과를 내는 outcome-equivalent 구현을 결정(2026-10-01, progress.md §M5 완료(결정 g))했고, 이 HISTORY 항목은 그 결정이 아직 spec.md/acceptance.md 문면에 반영되지 않은 drift 를 sync 직전에 해소한다. REQ-007 을 outcome-equivalent 구현(디머 축만 닫음, 색·포지션·페이저 축은 공유 `fids` 그대로 — 범위 밖 잔여로 명시 플래그)으로 재작성하고, AC-006 의 Given/When/Then 을 실제 측정(`measure_m5_a_non_accent_zero.json`/`measure_m5_b_accent_rising.json`)과 일치시켰다 — AC-006 은 디머 축만 PASS 로 좁혔고, 색/포지션/페이저 축의 미검증을 AC 본문에 명시했다. REQ 총량·AC 총량은 16/16 불변(REQ/AC ID 추가·삭제 없음, 문면 교정만). `status`/`lifecycle` 은 불변(여전히 in-progress) — 이 교정은 Status Transition Ownership Matrix 의 상태 전이가 아니라 `spec-frontmatter-schema.md` § Non-transition frontmatter corrections 절의 비전이 교정이다. |

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

[HARD — D11/D12 + 감독 결정 1/2 전제] `server/design/rig.py:44` `RIG_LAYER_ROLES` 는 **닫힌** 어휘였으나(독스트링: "a role outside this set is a caller typo, not a new role the standard recognises"), **감독 결정 1(옵션 a)이 이를 확장하기로 확정했다** — `docs/proposals/song-lighting-design-standard.md` §2c(버전 올림)와 `rig.py:44` 튜플에 `side`/`wash`/`mover` 세 역할을 정식 추가한다(REQ-002, 아래). **LIT-only 집계 규칙(감독 결정 2)**: 디머 값이 0(꺼짐 — 비액센트 큐에서 트래킹으로 이어지는 기본 상태 포함)인 역할은 "층"으로 세지 않는다. 이 규칙을 적용하면 이전 버전(plan-auditor iter1)의 주장 — "key/back/effect 세 역할만으로 3층 목표가 이미 달성된다" — 은 **성립하지 않는다**: R3(REQ-007)에 의해 `effect` 는 비액센트 큐에서 항상 꺼진 상태이므로 LIT 버킷에 들어가지 않고, 남는 것은 key·back 둘뿐이다(버킷 2개). 따라서 **REQ-001 의 "모든 구간 큐 ≥3 LIT 층" 목표는 실질적으로 REQ-002(SIDE/WASH/MOVER 확장)에 의존한다** — key/back 에 더해 side/wash/mover 중 최소 1개가 그 큐에서 점등(디머>0)되어야 LIT 버킷이 3개가 된다. **잔여 미해결 경우(발명하지 않고 플래그)**: 층 매핑이 key/back 둘만 해석하고(그 리그에 SIDE/WASH/MOVER/audience 그룹 자체가 없는 경우) REQ-002 가 구현된 뒤에도 그 곡은 구조적으로 LIT 층 3개에 도달할 수 없다 — 이 SPEC 은 이 2-역할 잔여 리그 케이스를 새 REQ 로 메우지 않는다(감독의 4건 결정 범위 밖).

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-001 | **When** 구간 큐가 조립되고 승인된 층 매핑(`layer_mapping`, SPEC-LDDESIGN-001 결함 6 의 `_confirm_song_layer_mapping` 산출물)에 확장된 `RIG_LAYER_ROLES`(`key`/`back`/`effect`/`audience`/`side`/`wash`/`mover`, REQ-002 적용 후) 중 2개 이상의 역할이 그룹 번호로 해석되어 있으면, 송신기(`reviewed_song_commands`) **shall** 역할마다 독립된 그룹 주소 값 줄을 낸다 — 현재 `_back_layer_value_lines`(`song_cue_render.py:621`)가 `role == "back"`만 찾는 것을 일반화해, 매핑된 모든 역할을 순회하는 다중 역할 함수로 대체한다. 줄 순서는 기존 규율(전체 기구 키 디머 줄 → 역할별 델타 줄 → 효과 recall → 액센트)을 유지한다 — 콘솔 트래킹(last-wins)이 뒤에 온 역할 줄을 이긴다. **완료 조건의 집계 규칙(감독 결정 2, D11/D12 수정)**: AC-001 은 디머>0(LIT)인 역할만 "서로 다른 값을 받는 층"으로 세며, 이 조건은 구간 큐 **전부**(블랙아웃 큐·MIB 사전이동 큐 제외 — 아래 예외)에 적용된다. "과반 이상"/"대다수" 같은 완화된 기준은 **쓰지 않는다**. | 코드 판독: `song_cue_render.py:621-644` `_back_layer_value_lines`(`role == "back"` 단일 분기), `rig.py:44`(`RIG_LAYER_ROLES`, REQ-002 로 확장). 잰 값: t499 §3 P4("매핑 카드가 KEY·FOH=Key/Front, BACK=Back, BLIND·STROBE·HAZE=Effect/Beam을 제안하고 승인을 받았는데 BACK만 쓰인다"), t499 §2 §6.2 위반 정의("무대 층 ≤2 인 큐가 **있으면** 1" — 큐 단위, 과반 아님) |
| REQ-LDRENDER-002 | **The** 역할 어휘 확장(감독 결정 1, 옵션 a) **shall** 두 자산을 함께 바꾼다: ① `docs/proposals/song-lighting-design-standard.md` §2c 의 "role층 → 그룹 매핑" 표에 `side`/`wash`/`mover` 세 역할을 추가하고 문서 버전을 올린다(**run-phase manager-develop 의 작업 — 이 plan-phase 산출물은 표준 문서를 직접 편집하지 않는다**, plan.md M2 참조), ② `server/design/rig.py:44` `RIG_LAYER_ROLES` 튜플에 `"side"`/`"wash"`/`"mover"` 를 추가하고, `rig.py:305-308` `_build_layers` 가 `declared_layers` 경로로 이 세 역할을 받아도 `RigProfileError` 를 던지지 않고 수용함을 확인한다. **그룹 이름 해석**(`_LAYER_GROUP_ALIASES`): 하이픈 앞 접두 토큰만으로 판정한다 — `SIDE-L`/`SIDE-R`/`SIDE-ALL` → `side`, `WASH-U`/`WASH-D`/`WASH-ALL` → `wash`, `MOVER-U`/`MOVER-D`/`MOVER-ALL` → `mover`. 부분 문자열 추측(RG5)은 하지 않는다 — 접두 토큰이 하이픈으로 정확히 분리되는 경우에만 매칭한다. **기존 잔여 테스트의 의도된 뒤집음**: `server/tests/test_layer_mapping_effect_role.py:119` `test_mover_and_wash_groups_remain_unmatched_documented_residual` 는 "SIDE/WASH/MOVER 는 미매칭으로 남는다"를 단언했었다 — 이 REQ 구현 후 그 단언은 **거짓이 된다**(이제 매칭됨). manager-develop **shall** 이 테스트를 뒤집는 것으로 명시적으로 인지하고 테스트명·단언·docstring 을 갱신한다(조용히 깨뜨리지 않는다). | 코드 판독: `server/design/rig.py:44`(`RIG_LAYER_ROLES`), `:92-95`(SIDE/WASH/MOVER 접미 미매칭 주석 — 이 REQ 가 해소), `:305-308`(`RigProfileError` 검증 경로), `server/web/session.py:7550-7556`(`declared_layers` 구성). 정본: `docs/proposals/song-lighting-design-standard.md` §2c. 실측(테스트 고정, 뒤집을 대상): `server/tests/test_layer_mapping_effect_role.py:119` |
| REQ-LDRENDER-003 | **While** 승인된 층 매핑에 해석된 역할이 1개 이하(단일 레이어 — SPEC-LDDESIGN-001 의 `_SINGLE_LAYER_WARNING` 경로)인 동안, 송신기 **shall** REQ-001 의 다중 역할 분기를 건너뛰고 오늘과 바이트 동일한 전체 기구 단일 값 송신으로 동작한다 — 매핑이 없는 리그를 이 REQ 가 막지 않는다. | 설계 규율: SPEC-LDDESIGN-001 §3.14(단일 레이어 경고), `_confirm_song_layer_mapping` 회귀 비파괴 요구 |

### 3.2 R2 — 색 전부 쓰기 (REQ-LDRENDER-004~006)

[HARD — 감독 결정 3, D2 해소] 층→색 배정이 확정됐다: **`back`+`mover` = 지배색**(팔레트 원색, `palette[0]`), **`side`+`wash` = 보조색**(액센트, `palette[1]`), **`key`(프런트/FOH) = 중립/웜 화이트**(정본 `docs/proposals/song-lighting-design-standard.md` §4b C3 "프런트(키층)는 중립/웜 화이트 유지 — 채도 색은 백층·이펙트층에"). **플래그(해소하지 않고 명시만 함 — D2 류 재발 방지)**: `docs/proposals/song-structure-lighting-standard.md` §6.3 은 "동시에 보이는 색은 최대 2개(지배색 1 + 액센트 1)"를 요구한다. 위 배정대로면 한 큐에서 동시에 보이는 색이 지배색(back+mover)·보조색(side+wash)·중립 웜화이트(key) 셋이 될 수 있다. 이 SPEC 은 **key 의 웜화이트를 §6.3 의 "최대 2개" 집계에 포함하지 않는 것으로 읽는다** — 근거는 `song-lighting-design-standard.md` §4b C1 의 "베이스1+액센트1~2(+화이트/CTO)" 병기 표현으로, 화이트/CTO 를 베이스·액센트 카운트와 별도 축으로 다루는 관행이 정본에 이미 있다. **그러나 이 읽음이 유일한 해석은 아니다** — §6.3 을 엄격히 "보이는 모든 색(중립광 포함) 최대 2개"로 읽으면 위 배정은 충돌한다. 이 SPEC 은 그 충돌을 **발명으로 해소하지 않고 여기 명시 플래그**한다(감독이 이미 결정 3 을 내렸으므로 열린 결정으로 재등록하지는 않지만, run-phase 중 이 해석이 틀렸다고 판명되면 재확인이 필요하다).

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-004 | **When** 큐의 팔레트(`cue.color.palette`, `ColorPlan.palette: tuple[str, ...]`)가 2개 이상의 색을 담고 있으면, 색 송신기(`_song_color_value_lines`, `song_cue_render.py:556`) **shall** 감독 결정 3 의 배정대로 값 줄을 낸다 — `back`+`mover` 역할 그룹에 지배색(`palette[0]`), `side`+`wash` 역할 그룹에 보조색(`palette[1]`), `key` 역할 그룹에 표준 팔레트의 중립/웜 화이트 색(새 RGB 발명 금지 — 표준 10색 중 기존 웜 화이트 항목 재사용). `len(palette) > 2`여도 3번째 이후 색은 이 큐에서 발화하지 않는다(§6.3 동시성 상한 — 위 [HARD] 단락의 집계 플래그 참조, 회차별 회전은 설계 층 R6 영역·§4 Out of Scope). **`palette_mode`/`color_usage="single"`** 일 때(REQ-006) 보조색이 지배색과 같아지면, `back`+`mover`+`side`+`wash` 네 그룹을 **하나로 합친 선택**에 동일 색 한 줄만 낸다 — 같은 값을 두 줄로 중복 발화하지 않는다. 오늘처럼 `palette[0]` 하나만 내고 나머지를 버리는 동작은 종료한다. | 코드 판독: `song_cue_render.py:596` `name = palette[0]`(주석 자신이 "보조색·유보색·언더페인팅은 M3 의 몫"이라고 DESCOPE를 명시 — 이 SPEC 이 그 M3 의 색 송신 반쪽을 닫는다). 잰 값: t499 §3 P1("설계 색 이름 3~4종 → 송신 RGB 1"). 정본: `song-structure-lighting-standard.md` §6.3, `song-lighting-design-standard.md` §4b C1/C3. 전제: REQ-002(side/wash/mover 역할 확장) |
| REQ-LDRENDER-005 | **The** 구간 큐 간 색 변화 **shall** 송신 층에서 측정 가능하다 — 설계 층(`_section_palette_choice`/`_arc_palette`, `section_palette.py`)이 구간마다 바꾸는 보조색 칸이 REQ-004 경유로 실제 콘솔 값 줄에 반영되어야 한다. 이 REQ 는 설계 층의 팔레트 로직을 바꾸지 않는다 — 이미 바뀌는 값을 송신이 더 이상 버리지 않는 것만 요구한다. | 잰 값: t499 §3 P2("P1×P2 = 송신 색 변화 0 — 설계는 맞게 '주색 + 바뀌는 보조색'을 만들고, 송신은 안 바뀌는 칸만 보낸다") |
| REQ-LDRENDER-006 | **While** 곡의 `color_usage`/`palette_mode`(SPEC-COPILOT-COLORMODE-001) 가 `modulate` 가 아닌 값(`single`/`per_chorus`)으로 확정되어 있으면, REQ-004 의 보조색 송신 **shall** 그 모드가 `_section_palette_choice` 에서 이미 결정한 베이스/악센트 값을 그대로 소비한다 — 새 색 선택 로직을 이 SPEC 이 만들지 않는다. `single` 모드에서는 보조색 칸도 베이스와 동일해지므로(§D5), REQ-004 는 "다른 값이 없으면 중복 줄을 내지 않는다"로 자연히 처리된다(별도 분기 불필요). | SPEC-COPILOT-COLORMODE-001 §2 D5(`single`/`per_chorus` 동작 정의), 감독 결정 구속 조건 1(기존 곡별 스위치 존중) |

### 3.3 R3 — 효과 기구 분리 (REQ-LDRENDER-007~008)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-007 | **When** 층 매핑이 `effect` 역할(BLIND/STROBE/HAZE 그룹, `_LAYER_GROUP_ALIASES["effect"]`)을 해석하면, 송신기 **shall** 비액센트 구간 큐에서 그 역할 그룹들의 디머(Dimmer) 값을 0 으로 유지한다. **리드 결정 (g)(2026-10-01, outcome-equivalent — 직역 아님, 명시 플래그)**: 이 REQ 가 원래 요구하던 "공유 `fids` 선택 자체에서 effect 기구를 제외"(fid 수준 뺄셈)는 콘솔 그룹 멤버십(그룹 번호→소속 fid)을 읽을 production-safe 경로가 어디에도 없어(GROUPGEN SPEC M0 실측 + 이 SPEC 자신의 M2 `_layer_mapping_from_group_children` 독스트링, 2차 반증 — progress.md §M5 블로커 절) 구현 불가였다. 대신 전체 기구 디머 줄 **뒤**에 역할별 **그룹 주소**로 `Group <n> ; Attribute 'Dimmer' At 0` 줄을 내어(그룹 번호 기반 override, 콘솔 last-wins 트래킹이 이김) 같은 결과(비액센트 큐에서 effect 기구가 어둡다)를 얻는다. **이 REQ 가 닫는 축은 디머뿐이다** — 색·포지션·페이저 값 줄이 겨냥하는 공유 `fids`(`_song_color_value_lines`/`position_cue_bundle`/`_phaser_cue_value_lines` 전체에 공유되는 단일 선택)는 이 결정 하에서도 86대 전체를 그대로 포함하며, 그 세 축에서 effect 기구를 빼는 것은 이 SPEC 의 범위 밖으로 남는다(발명으로 메우지 않음 — 후속 카드 후보). 액센트 큐(`cue.accent_fixture is not None`)에서는 그 액센트가 겨냥하는 그룹만 건너뛴다 — REQ-008 이 정의하는 상승 액센트 값이 그 그룹의 값을 낸다(그 자체의 독립된 `Group <n>` 주소, 공유 `fids` 와 무관). 복귀 큐(앞 큐가 블라인더를 켠 뒤 이 큐에 액센트가 없는 경우)에서는 같은 그룹에 중복된 "At 0" 줄이 나지 않도록 건너뛴다(`_accent_fixture_value_lines` 의 복귀 줄과 겹치지 않음 — 값 줄은 고유 문자열이어야 한다는 불변식). HAZE 는 LX-SEQ §11.2 작성 규칙 6(분위기 그룹은 Intensity 정합 비교에서 제외하되 트래킹 대상)에 따라 포함 대상이다 — 실측(`.moai/reports/t241/verdict.md` §2)상 Haze 기구에는 애초에 Dimmer 애트리뷰트가 없어 이 줄이 무해하며, 곡 시작/종료 안전 큐(Block/Release, SPEC-LDDESIGN-001 REQ-053~054)는 이 송신 경로가 쓰지 않는 별도 트래킹 시스템(`cue_sheet_edit.py` `TRACKING_VALUES`)이라 겹치지 않는다(grep 재확인 0건). | 잰 값: t499 §3 P3′("블라인더·스트로브·헤이즈가 매 큐 전체 디머(후렴 100)를 받는다"). **리드 결정 (g) 및 2차 반증 근거**: `progress.md` §M5(블로커 — fid 멤버십 판독 경로 부재)·§M5 완료(결정 g). 구현: `song_cue_render.py:890-970` `_effect_group_numbers`/`_effect_dimmer_zero_lines`(배선: `reviewed_song_commands` `extra_value_lines`, 역할 디머 줄 직후). 실측: `.moai/reports/t501/measure_m5_a_non_accent_zero.json`(8곡 비액센트 큐 effect>0 위반 0건), `measure_m5_b_accent_rising.json`(액센트 상승 8/8). 해석 노트(직역 아님, outcome-equivalent 플래그): `.moai/reports/t501/M5b.md` §해석 노트. 정본: LX-SEQ-SPEC-v2.1 §11.2 규칙 6 |
| REQ-LDRENDER-008 | **When** 액센트 큐(`cue.accent_fixture`, `_accent_fixture_value_lines`, `song_cue_render.py:647`)가 블라인더를 켜면, 그 값 줄 **shall** REQ-007 적용 후 기준(이전 비점등 상태, 통상 0)에서 **상승**하는 명시적 전체 밝기(기구 특성에 맞는 최댓값에 가까운 디머 값)를 낸다 — 오늘처럼 이미 전체 디머 100을 받은 효과 기구에 80을 추가로 덮어써 **역방향 하강**(100→80)이 되는 것을 금지한다. 복귀 큐는 기존대로 0으로 끈다(`_accent_fixture_value_lines` 둘째 분기 무변경). | 잰 값: t499 §3 P3′("절정 블라인더 줄은 오히려 100→80으로 내린다"), §1 비고("왜냐하면 Group 14 Dimmer At 80 의 80이 BACK(80)과 같아서"). t498 §0 큐 11 실측 |

### 3.4 R4 — 효과 송신 통로 (REQ-LDRENDER-009~012)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-009 | **When** 이 SPEC 의 run-phase 가 착수되면, 첫 마일스톤은 **shall** `fx.permitted = 0`(8곡 전부, t499 §3 P5a)의 원인을 실기 콘솔에서 측정한다 — **이 측정은 읽기 전용이다(응답기 `state`/`prop` 류 조회만 — 콘솔 쓰기 0건, `exec`/`Store` 류 커맨드 발화 금지)**. 구체적으로 `RigInventory.capability_fids["effect"]`(`server/design/rig.py:170-180`)가 `RigFixtureRecord.capabilities`(패치 레코드의 **명시 선언** 필드, `:138-146` "never inferred from type_name")로만 채워지는 경로와, `build_rig_profile(patch=..., groups={})`(`server/web/session.py:7445`, `:7556`)가 그 `patch` 인자를 어떤 능력-판독 파이프라인(`server/design/rig_capability_read.py`/`capability_verdict.py`, SPEC-COPILOT-PRECHK-001 계열)에서 채우는지를 실기로 대조한다 — 지금까지의 "리그 능력 판독 실패" 서술은 추정이며, 이 REQ 는 그 추정을 코드 판독 + 실기 측정으로 확정하는 것 자체를 완료 조건으로 한다(아래 측정하지 않으면 R4 의 나머지 REQ 는 착수하지 않는다). | 코드 판독: `server/design/energy.py:262-273` `_fx_axes`(`rig.has_capability("effect")` 가 False 면 budget 0) + `rig.py:138-146`(capabilities 비선언=0). 추정 표기(t499 §3 P5a): "원인 추정: energy.py:262 `_fx_axes`가 리그에 `EFFECT_AXIS_CAPABILITY` 기구가 없으면 0" |
| REQ-LDRENDER-010 | **When** 큐의 설계 층 효과 허용값(`fx.permitted`)이 0보다 크고 송신기가 그 효과에 대응하는 페이저 제안 라벨(`_phaser_label_for_cue`, `song_cue_render.py:481`)을 갖고 있으며 콘솔 풀 재조회(`phaser_slots`)가 그 라벨을 해석했으면, 송신기 **shall** `_phaser_cue_value_lines`(이미 존재하는 함수, `:508`)가 내는 recall 줄을 실제로 명령 목록에 포함한다 — 오늘 이 경로가 호출은 되지만 `phaser_slots` 가 항상 빈 매핑으로 넘어와(또는 허용이 0이라 애초에 호출 전제가 안 섬) 8곡 전부 효과 송신 0줄이 되는 지점을 REQ-009 의 측정 결과에 따라 닫는다. | 코드 판독: `song_cue_render.py:508-530`(이미 구현된 recall 함수, 호출부 `:1051` 존재). 잰 값: t499 §3 P5a′("`fx.permitted`를 읽는 곳은 `session.py:1355`(표시용)뿐이고 `reviewed_song_commands`는 안 읽는다") |
| REQ-LDRENDER-011 | **When** 제안된 페이저 라벨이 콘솔의 현재 풀 재조회 결과에 없으면(`phaser_slots.get(label) is None`), 시스템 **shall** (감독 결정 4, 옵션 a 확정 — 더 이상 양자택일이 아니다) SPEC-COPILOT-FXGEN-001/FXLIB-001 의 기존 저작 경로(`compose_fx`/`instantiate_fx`, `server/fx/instantiate.py` `build_fx_preset_bundle`/`select_preset_number`)를 호출해 그 페이저를 사전에 풀에 만들고, 다음 재조회에서 해석되게 한다. **승인 경로**: 이 생성은 콘솔 쓰기이므로 **기존 승인 게이트**(`run_commands` → `gate.screen()`, 기존 승인 카드)를 그대로 거친다 — 새 무승인 경로를 만들지 않는다. **충돌 사전 검출**: 생성 직전 콘솔 풀을 재조회해 지정하려는 프리셋 번호가 이미 점유돼 있으면 **덮어쓰지 않고** 생성을 거부·보고한다 — 이것은 FXLIB 가 이미 정의한 거부 의미론(`select_preset_number`/REQ-FXLIB-012 (c) 의 `PRESET_POOL_UNAVAILABLE`/`PRESET_POOL_TRUNCATED`/`PRESET_NUMBER_UNAVAILABLE`/`PRESET_OCCUPIED` 사유 코드)을 **그대로 재사용**하는 것이지 새 충돌 검사를 발명하는 것이 아니다. **2스텝 생성 규율**: 페이저는 멀티스텝 커맨드다(`<값>` → `Step 2` → `<값>`, FXLIB/FXGEN 이 이미 검증한 번들 형상 — `server/fx/instantiate.py` 모듈 독스트링) — 이 REQ 는 그 기존 생성 로직을 재사용할 뿐 새 페이저 저작 문법을 만들지 않는다. 생성 완료까지 큐의 다른 값 줄(디머·색·포지션)은 영향받지 않는다. | 잰 값: t499 §3 P5b(8곡 전부 "페이저 제안 104큐 → 송신 0, 8곡 회신 모두 '페이저 미배정' 문구 있음"). 코드 판독: FXLIB `select_preset_number`/REQ-FXLIB-012 (c)(충돌 거부 의미론), `server/fx/instantiate.py`(2스텝 번들 형상). 구속 조건 4(새 콘솔 쓰기 경로는 감독 승인 필요 — 이 REQ 는 새 경로가 아니라 기존 게이트 재사용임을 명시) |
| REQ-LDRENDER-012 | **When** 효과 송신(REQ-010·011)이 결정되면, 보고기(기존 2단 보고 선례, `server/looks/report.py`)의 효과 관련 문면 **shall** 요청(`fx.requested`)·허용(`fx.permitted`)·송신(실제 recall 줄 수) 3계를 구분해 적는다 — t499 요약표(§1)와 같은 3열 구조를 운영 리뷰 표면에도 노출한다. | t499 §1 표 구조("효과: 요청/허용/페이저 제안 큐 → 송신 줄") |

### 3.5 R7 — 연출 판독 게이트 (REQ-LDRENDER-013~016)

| REQ | 요구사항 | 근거 |
|---|---|---|
| REQ-LDRENDER-013 | **The** 시스템 **shall** t499 의 판독 도구(`.moai/reports/t499/readout.py`)의 핵심 판정 로직(송신 색 수·구간 큐당 LIT 상태로 다른 값 받는 층 수·송신 효과 줄 수)을 제품 코드로 승격한 재사용 가능한 게이트 함수를 제공한다 — 보고서 전용 스크립트가 아니라 송신 경로가 호출할 수 있는 모듈 함수로 만든다. **집계 규칙은 REQ-001·AC-001 과 바이트 동일하다**(감독 결정 2): 디머>0(LIT)인 역할만 "다른 값 받는 층"으로 세고, 판정은 구간 큐 단위다(과반·평균 아님) — 게이트가 AC-001 과 다른 셈법으로 세면 게이트 PASS 와 실제 송신 품질이 어긋난다. | 카드 지시문 R7, `.moai/reports/t499/readout.py`(364행, 기존 로직 소재). 집계 규칙 동치성: REQ-001 [HARD] 단락 |
| REQ-LDRENDER-014 | **When** 콘솔에 쓰기 직전인 곡의 송신 명령 목록이 REQ-013 의 게이트(REQ-001 과 동일한 LIT-only·큐-단위 집계)를 거쳐 다음 중 하나라도 만족하면(색 2~3종 미만, **LIT** 상태로 다른 값을 받는 층이 3개 미만인 구간 큐가 **하나라도** 존재, 효과를 요청한 곡인데 송신 효과 줄 0), 시스템 **shall** 감독에게 경고를 띄운다 — 송신을 차단하지 않는다(SPEC-LDDESIGN-001 REQ-052 의 비차단 경고 선례를 따른다). | 카드 지시문 R7 완료 조건, 구속 조건(헤드룸 경고 비차단 선례), t499 §2 §6.2 위반 정의("있으면 1" — 큐 단위) |
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

## 5. 열린 결정 — 전부 해소 (0건)

2026-10-01 리드 경유 감독 결정 4건으로 이전 버전의 열린 결정 3건이 전부 해소됐다. 기록으로 남긴다:

1. ~~R4 방법 선택~~ → **감독 결정 4: 옵션 (a) 확정**(REQ-011 — `compose_fx`/`instantiate_fx` 사전 생성, 기존 승인 게이트 재사용, 충돌 사전 검출 추가).
2. ~~R1 SIDE/WASH/MOVER 역할 해석~~ → **감독 결정 1: 옵션 (a) 확정**(REQ-002 — 정본 §2c 버전 올림 + `RIG_LAYER_ROLES` 확장, 접두 토큰 그룹 이름 해석).
3. ~~R2 층→색 배정~~ → **감독 결정 3: `back`+`mover`=지배색, `side`+`wash`=보조색, `key`=중립/웜 화이트 확정**(REQ-004). §3.2 [HARD] 단락에 미해소 플래그(웜화이트의 §6.3 집계 포함 여부) 1건을 남긴다 — 이것은 "열린 결정"이 아니라 "결정은 났으나 해석 긴장이 플래그된 것"이다(발명 금지 원칙에 따라 조용히 묻지 않는다).

추가로 **감독 결정 2**(디머=0 은 층으로 안 센다, 큐 단위 전수 판정)가 plan-auditor D11(과반 문구의 무단 완화)·D12(key/back/effect 트리오의 메트릭 게이밍)를 동시에 해소했다 — REQ-001/013/014 와 acceptance.md AC-001/012/013 전체에 반영.
