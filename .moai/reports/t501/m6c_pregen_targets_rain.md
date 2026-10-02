# t501 M6c — 5절 정지점: 저작 처방 후 Rain 4개 라벨 (WITHOUT SENDING)

🔴 **콘솔 쓰기 0건.** 이 문서는 `server/design/phaser_pregen.py` 순수 함수를
저장된 읽기 전용 풀 스냅샷에 돌려 "지금 보내면 나갈 명령"만 산출한다
(`.moai/reports/t501/m6c_pregen_stop_point.py`). **실제 전송 전 새 읽기 전용
재조회가 반드시 필요하다** — 아래 번호는 스냅샷 시점 계산값이고, 그 이후 다른
저장·삭제가 있었을 수 있다.

## 배경 — M6 의 거부가 M6c 에서 해소됨

M6(`.moai/reports/t501/M6.md`)은 Rain 이 필요로 하는 5개 라벨 중 `Wave CM`
하나만 빌드되고 나머지 4개(`Drop Slam`/`Breathe Warm`/`Breathe Cool`/
`Finale Slam`)는 FXLIB `_guard_collision` 의 `value_line_collision` 으로
거부됨을 측정했다. `Wave CM` 은 이미 감독 승인(21줄)을 거쳐 실기 콘솔에
`Preset 4.9` 로 저장됐다(M6 본편 참조) — **다시 계산하지 않는다**.

M6c(카드 t501, 리드 결정 C)가 저작 쪽에서 처방했다: `Fx.compound_step_values`
축을 추가하고 `pregenerate_phaser_bundle` 이 평범한 폼(오늘, 채널별 한 줄)으로
먼저 시도 → `VALUE_LINE_COLLISION` 으로만 거부될 때 같은 라벨을 `compound_
step_values=True` 로 재시도(스텝의 채널 전부를 `;`-체인 한 줄로 묶음). 자세한
근거와 `_guard_collision`-무변경 증명은 `server/design/phaser_pregen.py` 모듈
독스트링 + `.moai/reports/t501/M6c.md` 참조. 이 처방 뒤 **4개 전부**
`build_fx_preset_bundle` 를 통과한다(측정됨, 직접 재현 가능).

## 공석(vacancy) 판정에 쓴 증거

| 풀 | 번호 | 점유 슬롯(캡처 당시) | 증거 파일 | 캡처 시점 |
|---|---|---|---|---|
| Color | 4 | 1,2,3,4,5,6,7,8,9,32 | `.moai/reports/t501/m6_postsend_reread_20261002.txt` | M6 의 `Wave CM`→`Preset 4.9` 송신 **직후** 읽기 전용 재조회(2026-10-02) — `state` 조회, `truncated: false`, 완전 판독 |
| All 1 | 21 | 1,2,3,4,5,6 | `.moai/reports/t501/m6_pool_reread_readonly.txt` | M6 송신 **직전** 읽기 전용 재조회 — All 1 풀은 그 송신으로 아무것도 저장하지 않았으므로 이후로도 값이 바뀔 사유가 없다 |

**이 두 스냅샷을 고른 이유**: 배차서가 지정한 증거 파일 그대로다 — Color 풀은
`Wave CM` 송신을 반영한 **가장 최신** 읽기(9번 슬롯에 `"Wave CM"` 이 보임),
All 1 풀은 그 송신에 영향받지 않으므로 가장 최신 읽기 전용 재조회를 그대로
쓴다. **두 스냅샷 모두 지금 이 순간의 점유를 보장하지 않는다** — 전송 전
재조회 필수(아래 §잔여 위험).

## 앱의 라벨 처리 순서 시뮬레이션 (누적)

앱의 `_pregenerate_missing_phasers`(`server/web/session.py`)는 대기 중인
라벨을 `sorted()` 순서로 처리하고 라벨마다 풀을 다시 읽는다 — 그래서 같은
풀을 쓰는 두 라벨(`Breathe Cool`/`Breathe Warm`, 둘 다 Color; `Drop Slam`/
`Finale Slam`, 둘 다 All 1) 사이에서 번호가 **누적**된다. 콘솔에 실제로
쓰지 않으므로 `m6c_pregen_stop_point.py` 는 그 누적을 로컬 변수로 흉내 낸다
(한 라벨이 계산한 target slot 을 그 풀의 점유 집합에 더해 다음 라벨 계산에
반영).

처리 순서(`sorted(["Drop Slam", "Breathe Warm", "Breathe Cool", "Finale Slam"])`):

1. `Breathe Cool`
2. `Breathe Warm`
3. `Drop Slam`
4. `Finale Slam`

## 결과 — 번호·이름 전부 + 판정 (직접 계산, 하드코드 아님)

| 라벨 | 풀.슬롯(제안) | 판정 | 계산에 쓰인 점유 집합 |
|---|---|---|---|
| Breathe Cool | Color(4).**10** | **WOULD_SEND** | {1..9, 32} (스냅샷 그대로) |
| Breathe Warm | Color(4).**11** | **WOULD_SEND** | {1..9, 10, 32} (Breathe Cool 의 10 누적) |
| Drop Slam | All 1(21).**7** | **WOULD_SEND** | {1..6} (스냅샷 그대로) |
| Finale Slam | All 1(21).**8** | **WOULD_SEND** | {1..7} (Drop Slam 의 7 누적) |

배차서가 명시한 기대값(Breathe Cool 4.10, Breathe Warm 4.11, Drop Slam 21.7,
Finale Slam 21.8)과 **정확히 일치** — `select_preset_number` 의 공석 측정
알고리즘(1부터 증가하며 점유 집합과 대조)을 직접 호출해 계산한 값이다.

## 스텝 값 동치 증명 (BEFORE = 카탈로그 의도, AFTER = 생성된 명령에서 역파싱)

`.moai/reports/t501/m6c_step_value_equivalence.py` 가 아래 표 전부를
자동으로 만들고 `ALL_STEPS_MATCH=True` 를 확인했다 — 저작 처방이 스텝의
**텍스트 형태**만 바꿨을 뿐 채널별 숫자 값은 카탈로그가 의도한 것과
정확히 같다는 증거(전문: `.moai/reports/t501/m6c_step_value_equivalence.json`).

### Drop Slam (콤보, All 1.7)

| 스텝 | ColorRGB_R | ColorRGB_G | ColorRGB_B | Dimmer | BEFORE=AFTER |
|---|---|---|---|---|---|
| 1 | 100 | 0 | 0 | 100 | 일치 |
| 2 | 100 | 0 | 0 | 0 | 일치 |

### Breathe Warm (색, Color.11)

| 스텝 | ColorRGB_R | ColorRGB_G | ColorRGB_B | BEFORE=AFTER |
|---|---|---|---|---|
| 1 (Warm White) | 100 | 75 | 40 | 일치 |
| 2 (Amber) | 100 | 55 | 5 | 일치 |

### Breathe Cool (색, Color.10)

| 스텝 | ColorRGB_R | ColorRGB_G | ColorRGB_B | BEFORE=AFTER |
|---|---|---|---|---|
| 1 (Cool White) | 85 | 95 | 100 | 일치 |
| 2 (Blue) | 5 | 20 | 100 | 일치 |

### Finale Slam (콤보, All 1.8)

| 스텝 | ColorRGB_R | ColorRGB_G | ColorRGB_B | Dimmer | BEFORE=AFTER |
|---|---|---|---|---|---|
| 1 (Warm White) | 100 | 75 | 40 | 100 | 일치 |
| 2 (Red) | 100 | 0 | 0 | 0 | 일치 |

## 보낼 명령 전문

전문은 `.moai/reports/t501/m6c_pregen_commands_rain.txt` 에 저장했다(4개
라벨 전부 WOULD_SEND — REFUSED 사유가 더는 없다). 요약(각 라벨의 스텝 값
줄이 이제 `;`-체인 압축 폼이다 — `_guard_collision` 이 통과시킨 텍스트
그대로):

```
# Breathe Cool -> Preset 4.10
...
Attribute 'ColorRGB_R' At 85 ; Attribute 'ColorRGB_G' At 95 ; Attribute 'ColorRGB_B' At 100
Step 2
Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100
...
Store Preset 4.10 'Breathe Cool' /Universal
Label Preset 4.10 'Breathe Cool'
ClearAll

# Breathe Warm -> Preset 4.11
...
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 40
Step 2
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 55 ; Attribute 'ColorRGB_B' At 5
...
Store Preset 4.11 'Breathe Warm' /Universal
Label Preset 4.11 'Breathe Warm'
ClearAll

# Drop Slam -> Preset 21.7
...
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0 ; Attribute 'Dimmer' At 100
Step 2
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0 ; Attribute 'Dimmer' At 0
...
Store Preset 21.7 'Drop Slam' /Universal
Label Preset 21.7 'Drop Slam'
ClearAll

# Finale Slam -> Preset 21.8
...
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 40 ; Attribute 'Dimmer' At 100
Step 2
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0 ; Attribute 'Dimmer' At 0
...
Store Preset 21.8 'Finale Slam' /Universal
Label Preset 21.8 'Finale Slam'
ClearAll
```

`Group 1`(=All)은 저작 시점 스크래치 선택일 뿐이다 — `Store Preset ...
/Universal` 로 저장되므로 recall 대상 기구를 제한하지 않는다(M6 본편과
동일한 전제).

## 잔여 위험 — 전송 전 재확인 필요 (명시)

- **풀 점유 스냅샷이 두 가지 다른 시점이다.** Color(4번)는 M6 송신
  직후(가장 최신), All 1(21번)은 M6 송신 직전(그 송신에 영향받지 않음) —
  둘 다 **이 카드(M6c) 작업 시점보다 과거** 캡처다. 전송 직전
  `select_preset_number` 의 재조회(§D "콘솔 풀 재조회로 프리셋 번호 충돌을
  사전 검출" 요구) 없이 이 문서의 슬롯 번호(4.10/4.11/21.7/21.8)를 그대로
  쓰면 안 된다.
- **앱의 누적 시뮬레이션은 로컬 계산이지 실기 재조회가 아니다.** 실제 전송
  시점에 앱이 라벨마다 진짜로 풀을 다시 읽으면, 이 문서가 시뮬레이션한
  번호와 다를 수 있다(다른 세션이 그 사이 같은 풀에 저장했다면).
- **phase/curve 문법 괴리(M6 §잔여 위험, 미해소).** `build_fx_preset_bundle`
  이 쓰는 FXLIB 표준 문법이 실기로 "같은 시각 효과"를 내는지는 이 저장소가
  측정한 바 없다 — M6c 는 이 축을 건드리지 않았다.
- **R7 게이트(`cue.fx.permitted`)와는 독립된 축** — 이 문서의 4개 라벨은
  전부 "제안됐다"고 가정한 것이지, 실제 Rain 송신이 그 순간 예산을 비우지
  않았는지는 별도로 확인해야 한다(REQ-010, M6 본편 참조).
- **`;`-체인 압축 폼의 실기 교차 확인은 Wave CM 의 Speed 줄 하나뿐이다.**
  스텝 값 줄 자체를 `;`-체인으로 묶어 보내는 실기 검증(콘솔이 정확히
  이 폼의 `Attribute 'X' At <v> ; Attribute 'Y' At <v2>`(Speed 가 아닌
  스텝 값)를 똑같이 해석하는지)은 이 카드가 하지 않았다 — NO CONSOLE
  CONTACT 제약(배차서) 때문에 측정 불가, 다음 송신 카드의 선결 과제로
  남긴다.
