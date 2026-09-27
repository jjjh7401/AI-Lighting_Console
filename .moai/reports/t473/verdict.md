# t473 — 콘솔에서 페이저 프리셋 속도·팬 흔들림 진폭 읽기 (lane-1)

- 브랜치 `WT-phaser-speed-read` · 기준 `origin/main@9587a41a` · **콘솔 쓰기 0** (모든 호출이 `state`·`props`·`introspect`)
- 도구: `.moai/reports/t431/probe_t431.py` (응답기 `console/lua/copilot_responder.lua` VERSION 1.6.5)
- 입력: `.moai/reports/t467/verdict.md` — 생성기 경고 2종(팬 폭 ±25°, 페이저 속도 = BPM)의 재료가 서버에 없다

## 0. 판정

| 값 | 판정 | 근거 |
|---|---|---|
| 페이저 속도 | 🔴 **지금 도구로는 못 읽는다** | 프리셋 속성 138개 중 속도 후보(`SPEEDMASTER`=`None`, `SPEEDSCALE`=0, `SPEEDFROMX/TOX`=`None`, `RELATIVESPEED`=false)는 MAtricks·마스터 설정이고, 페이저의 Speed 층 값이 아니다 |
| 팬 흔들림 진폭 | 🔴 **지금 도구로는 못 읽는다** | 진폭은 스텝 값(또는 Relative 값)의 차이다. 스텝 값을 담은 `PRESETDATA`를 응답기가 꺼내지 못한다 |
| `PRESETDATA` 빈 문자열의 뜻 | 🟢 **계기의 한계**(데이터가 없는 게 아님) | 값이 있다고 확인된 포지션 2.2(t469 캡처)도 `""` · 음성 대조 `NOSUCHPROPT473` → `property not readable` |
| 부산물: `OWNDATAPRESENT` | 🟡 **완전히 빈 프리셋만 가린다** | 2.1 `false`, 2.2~2.6 `true` — 그런데 t469 캡처에서 2.3·2.4·2.6은 521·522에 값을 못 넣었다. 「어떤 기구든 값이 있다」일 뿐 「고른 기구의 값이 있다」가 아니다 |

→ 이 카드의 결론은 **「읽히지 않는다」**다. 카드 지시대로 payload 노출·경고 활성은 하지 않았다(읽을 값이 없음). 대신 §3에서 읽을 수 있게 하는 경로를 제안한다.

## 1. 실측 (읽기 전용)

| run | 호출 | 결과 |
|---|---|---|
| run1 | `state`·`introspect` `PresetPools/21/2` (PT-CIRCLE, 팬·틸트 페이저) | 자식 0 · 속성 138개. 페이저 관련 이름은 `PHASERTRANSFORM`·`SPEEDMASTER`·`SPEEDSCALE`·`PRESETDATA`(Custom)·`SELECTIONDATA`(Custom)·X/Y/Z별 `SPEEDFROM/TO`·`FADEFROM/TO`·`PHASEFROM/TO` |
| run2 | `props` 16개 | `PRESETDATA` `""` · `SELECTIONDATA` `{}` · `STOREDDATA` `Universal` · `SPEEDMASTER` `None` · `SPEEDSCALE` `0` · `OWNDATAPRESENT` `true` · `SPEEDFROMX/TOX` `None` · `RELATIVESPEED` `false` · `PHASERTRANSFORM` `None` · `RELATIVE` `true` |
| run3 | 대조: 2.2(값 있음 확인됨) · 21.4 DIM-BREATHE · 2.1 · 가짜 속성 | 2.2 `PRESETDATA ""`, `SELECTIONDATA {}` → 빈 값이 계기 한계임을 확인 · 21.4 같은 모양 · 가짜 속성 거절 |
| run4 | `OWNDATAPRESENT` 2.1~2.6 | 2.1 `false`(STOREDDATA `""`), 2.2~2.6 `true`(Selective) |

응답기 동사는 `ping`·`state`·`prop`·`props`·`introspect`·`exec`·`deploy` 일곱 개다(`copilot_responder.lua` 1365~1443행). 프리셋 내부 데이터를 꺼내는 동사는 없다.

룰북 `server/rulebook/assets/v2.4.2/33_effect_editors.md` 22~35행: 페이저 속도는 속성별 층 값(`At Speed <bpm>` 또는 `At SpeedMaster <n>`)이고, 흔들림은 스텝 값(또는 `At Relative <n>`)이 만든다. 둘 다 프리셋 내부 데이터이지 프리셋 객체의 속성이 아니다. 저장소에서 `GetPresetData`를 쓴 곳이나 문서화한 곳은 0건이다(`git grep -i GetPresetData` → 0).

## 2. 안 잰 것 (Gaps)

- grandMA3 Lua에 프리셋 내부 데이터를 표로 돌려주는 함수가 있는지 — 저장소에 근거가 없고, 이 카드는 응답기를 바꾸지 않았다
- 콘솔 화면(Phaser Editor)에서 이 프리셋들의 실제 속도·진폭 값 — 감독 화면 판독은 요청하지 않았다(읽기 전용 프로브 범위)
- 다른 풀(21 외 22~25)의 페이저 프리셋 — 같은 객체 클래스라 같은 한계로 본다(추정)

## 3. 후속 제안 (별도 카드)

1. **응답기 읽기 동사 추가 (예: `presetdata`)**: 콘솔 Lua에서 프리셋 내부 데이터(속성별 스텝 값·Speed·Phase 층)를 표로 꺼내 JSON으로 돌려준다. 순서: ① Lua API 존재·모양 실측(읽기) ② 응답기 1.6.6 배포는 콘솔 쪽 변경이라 감독 승인 필요
2. **앱이 만든 페이저는 앱이 기록한다**: 카탈로그 30종(`COLOR/DIMMER/COMBO_PHASER_SEQUENCE`)은 스텝 값을 이미 서버가 안다 — 진폭은 서버에서 계산할 수 있다. 속도는 지금 콘솔 기본값에 맡기므로, 만들 때 `At Speed`를 명시해 기록하면 서버가 안다. 콘솔에 원래 있던 프리셋(DIM-PULSE 등)은 여전히 1번이 필요하다
3. **t477(이름→번호 조회)과 묶을 것**: `OWNDATAPRESENT=false`는 완전히 빈 프리셋(2.1)을 반영 전에 거를 수 있다. 다만 「고른 기구 값 없음」(2.3·2.4·2.6)은 못 거른다 — 1번의 동사가 있으면 기구별로 가릴 수 있다

## 4. 증거 파일

`.moai/reports/t473/` — `run1_preset_ptcircle.txt` · `run2_preset_props.txt` · `run3_controls.txt` · `run4_owndata.txt`
