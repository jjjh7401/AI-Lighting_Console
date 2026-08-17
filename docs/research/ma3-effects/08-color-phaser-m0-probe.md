# 08. 멀티컬러 페이저 프리셋 10종 — M0 라이브 프로브 결과

`docs/handoff/2026-08-16-session-handoff.md` §2의 M0 지침에 따라, 미검증 문법을 구현 전에
실기(onPC 2.4.2, CopilotResponder 1.6.0)로 확인한 기록이다. `verification-claim-integrity`
원칙에 따라 **관측된 그대로**만 적고, 추정은 GAP으로 명시한다.

- 실기: onPC 2.4.2, CopilotResponder **1.6.0**(ping 응답으로 확인)
- 선택: `Group 11`
- 컬러 풀: `4` (`DataPool/PresetPools/4`, `node.class='Presets'`, `node.name='Color'`)
- 임시 슬롯: `4.50`(팔레트 참조 방식), `4.51`(직접 RGB 방식) — **프로브 종료 후 둘 다 삭제 완료**

---

## 전제 검증

| # | 항목 | 결과 |
|---|---|---|
| 1 | 응답기 버전 | `ping` 응답 payload: `{'version': '1.6.0', ...}` — **PASS** |
| 2 | Color 풀 4.21~4.30 'Warm White'~'Lavender' 실재 | **PASS(간접 확인, 근거는 §3)** — 직접 리스팅으로 4.21/4.30을 눈으로 보지는 못했다(풀 리스팅이 24개 윈도로 잘려 인덱스 20 이상이 창 안에 없었다, §4 GAP 참고). 대신 `At Preset 4.21`/`At Preset 4.30` 둘 다 `ok:true`로 수락됐고, 그 값을 스텝에 담아 저장한 프리셋의 자동 이름이 `[Warm White#2/Lavender#2]`로 나왔다 — 콘솔이 4.21/4.30 슬롯에서 실제로 'Warm White'/'Lavender'라는 라벨을 읽어 자동 이름에 박아넣은 것이므로, 두 슬롯에 그 이름의 프리셋이 존재한다는 증거로 채택한다. |

---

## 1. 스텝 생성 커맨드라인 — 실측 시퀀스 (두 방식 모두 성공)

### 1-A. 팔레트 프리셋 참조 방식 (`At Preset 4.x`)

```
ClearAll
Group 11
At Preset 4.21          # Step 1 = Warm White
Step 2
At Preset 4.30          # Step 2 = Lavender
Store Preset 4.50
```

전부 `{'ok': True, 'result': 'OK'}`. 저장된 프리셋을 곧바로 `state` 재조회하면:

```
DataPool/PresetPools/4/50 →
  node = {'name': '[Warm White#2/Lavender#2]', 'class': 'Preset', 'childCount': 0}
```

**2스텝 페이저가 만들어졌다** — 자동 이름이 두 스텝의 실제 팔레트 라벨(`Warm White`,
`Lavender`)을 대괄호로 묶어 보여준다(`#2`는 GAP, §4 참고).

### 1-B. 직접 RGB 방식 (`Attribute 'ColorRGB_R/G/B' At <n>`)

```
ClearAll
Group 11
Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0   # Step 1 = Red
Step 2
Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 100    # Step 2 = Blue
Store Preset 4.51
```

전부 `{'ok': True, 'result': 'OK'}`. 저장된 프리셋 재조회:

```
DataPool/PresetPools/4/51 →
  node = {'name': 'Preset 51', 'class': 'Preset', 'childCount': 0}
```

**결론: 두 방식 다 문법적으로 수락되고 저장에도 성공한다.** 차이는 §2의 판독 신호뿐 —
직접 RGB로 만든 스텝은 프리셋 참조가 아니므로 자동 이름에 스텝 내용이 나타나지 않는다.

---

## 2. 저장·되읽기 판독 신호 — 실측

| 신호 | 팔레트 참조(4.50) | 직접 RGB(4.51) |
|---|---|---|
| `state` 최상위 `node.name` | `[Warm White#2/Lavender#2]` — **멀티스텝 콘텐츠가 이름에 그대로 노출** | `Preset 51` — 기본 이름, 스텝 내용 없음 |
| `state` 최상위 `node.childCount` | `0` | `0` |
| `children` 배열 | `[]` (빈 배열) | `[]` (빈 배열) |

**GAP(정직한 한계 고지)**: `state DataPool/PresetPools/4/50` 단일 쿼리로는 스텝을 자식
오브젝트로 열거할 수 없다(`childCount:0`, `children:[]`) — 이 프로토콜 경로로는 "몇 스텝인지"
"각 스텝 값이 뭔지"를 직접 셀 수 없다. 유일한 관측 가능 신호는 **팔레트 참조로 만든
멀티스텝 프리셋의 자동 생성 이름**뿐이며, 이마저도 (a) 우리가 항상 `Label Preset`으로
커스텀 라벨을 즉시 덮어씌울 계획이라 실제 카탈로그 저장 후에는 사라지고, (b) 직접 RGB
스텝에는 애초에 나타나지 않는다. 향후 "저장이 진짜 멀티스텝으로 됐는지" 기계 검증이
필요하면 `prop` 쿼리로 `StepCount` 류 프로퍼티가 존재하는지 별도 프로브가 필요하다 —
이번 세션 범위 밖(미측정, 추정 금지).

풀 전체(`DataPool/PresetPools/4`)의 `node.childCount`는 저장/삭제에 정확히 연동됐다
(정량 증거): 27 → (4.50 저장) 28 → (4.51 저장) 29 → (둘 다 삭제) 27. 저장·삭제 둘 다
부작용 없이 정확히 원복됨을 확인.

---

## 3. 함정 검증 결과

### 함정 ① `Store Preset ... Step 2` 직접 저장 — 스텝1 삭제 부작용 주장

**핸드오프 문서의 이 주장은 이번 라이브 테스트에서 재현되지 않았다.** 두 시퀀스(A, B) 모두
`Step 2`로 진입해 값을 입력한 **직후**, Step 1로 되돌아가지 않고 곧바로 `Store Preset
4.50`/`4.51`을 호출했다 — 즉 "Step 2가 현재 활성 스텝인 상태에서 Store"를 정확히 재현했다.
결과: 시퀀스 A의 되읽기 이름이 `[Warm White#2/Lavender#2]`로 **Step 1(Warm White)과
Step 2(Lavender) 둘 다** 담겼다 — Step 1이 삭제되지 않았다.

이 세션에서 실측한 한도 내에서는(팔레트 참조 방식, 컬러 전용, `Group 11`) 트랩이 재발하지
않았다 — 스텝1 삭제 부작용을 관측하지 못했다는 뜻이지, 모든 조건에서 트랩이 없다고
일반화하지는 않는다(예: `Store Preset ... Step 2`처럼 Store 명령 자체에 `Step 2` 토큰을
**결합**해 보내는 변형은 이번에 시도하지 않았다 — 우리는 항상 `Step 2`와 `Store Preset`을
별개 명령으로 분리해서 보냈다). 카탈로그 구현체도 이 분리된 순서(Step 명령 →
값 명령 → 별도의 Store 명령)를 그대로 재사용하면 안전하다.

### 함정 ② 컬러 전용 페이저는 Color 풀 수용

**확인됨.** 두 시퀀스 다 순수 컬러 속성(`ColorRGB_R/G/B`, 팔레트 프리셋 recall도 결국
컬러 속성만 채움)만 프로그래머에 실었고, `Store Preset 4.5x`(Color 풀, 입력 필터 있는
Feature Group 풀)가 거부 없이 성공했다 — `All` 풀로 우회할 필요가 없었다.

### 함정 ③ Form(Sine)·Phase·Speed 문법

시퀀스 B에서 Sine 근사(§ `05-phaser-editor.md` §4 문서 근거)와 Phase/Speed를 함께 실었다:

```
Attribute 'ColorRGB_R' At Accel -100
Attribute 'ColorRGB_R' At Decel -100
Attribute 'ColorRGB_G' At Accel -100
Attribute 'ColorRGB_G' At Decel -100
Attribute 'ColorRGB_B' At Accel -100
Attribute 'ColorRGB_B' At Decel -100
Attribute 'ColorRGB_R' At Phase 0
Attribute 'ColorRGB_R' At Speed 60
```

전부 `{'ok': True, 'result': 'OK'}` — **컬러 채널(R/G/B 세 속성 모두)에 Accel/Decel/
Phase/Speed 레이어를 얹는 문법이 문법 수준에서 수락된다**. 이 조합이 저장된 4.51에도
반영됐는지(레이어가 프리셋에 실제로 실렸는지)는 §2 GAP과 같은 이유로 `state` 경로로는
직접 셀 수 없었다 — `ok:true` 수락 + 저장 성공(`childCount` 증분)까지만 관측했다.

**Rectangle Form**은 이번 세션에서 시도하지 않았다 — `05-phaser-editor.md` §4가 이미
"Form 버튼에 대응하는 단일 명령 키워드가 없다"고 기록했고, Sine(Accel/Decel -100/-100)
외의 정확한 Accel/Decel 수치 조합은 공식 문서에 없다(§8.7 기존 GAP). 날조하지 않고
미검증으로 남긴다 — 카탈로그의 Rectangle 항목(#3 Chase RB, #4 Chase CM, #10 Slam RW)은
구현 전 별도 실측이 필요하다.

---

## 4. GAP — 이번 프로브가 채우지 못한 것

1. **저장된 프리셋의 실제 스텝 개수/값을 기계로 셀 방법** — `state` 최상위 쿼리는
   `childCount:0`을 반환해 스텝을 자식으로 셀 수 없다. 유일한 신호(팔레트 참조 시
   자동 이름)는 라벨을 덮어쓰면 사라진다. `prop` 쿼리로 개별 프로퍼티(예:
   `StepCount`, `Steps`)가 존재하는지는 미측정.
2. **자동 이름의 `#2` 의미** — `[Warm White#2/Lavender#2]`의 `#2`가 무엇을 세는지
   (픽스처 타입 수? 선택 픽스처 수?) 확인하지 못했다. `Group 11`의 정확한 멤버
   구성을 세지 않아서다 — 추정하지 않는다.
3. **컬러 풀 4.21~4.30 직접 리스팅** — 첫 페이지(offset 0)가 24개 캡에 걸려 인덱스
   20 이상을 보여주지 않았다(§전제검증 2의 간접 증거로 대체). offset 페이징
   재조회는 이번 세션에서 시간상 생략.
4. **Rectangle Form의 정확한 Accel/Decel 수치** — 미검증(공식 문서에도 없음, §3 참고).
5. **`At Speed`/`At Phase`가 저장된 프리셋에 실제로 실렸는지** — 문법 수락만 확인,
   값 자체의 프리셋 반영 여부는 미검증(§3 참고).

---

## 5. 다음 세션(카탈로그 구현)에 대한 시사점

- 스텝 생성 순서는 **팔레트 참조**(`At Preset 4.x`)를 기본으로 채택할 근거가 생겼다 —
  직접 RGB보다 값 하나로 스텝이 채워지고(중복 RGB 3줄 불필요), 저장 직후 자동 이름으로
  "제대로 담겼는지" 사람이 눈으로 확인하기도 쉽다(다만 최종적으로는 `Label Preset`으로
  우리 라벨을 덮어씌우므로 이 이점은 저장 직후 검증 순간에만 유효).
- `Step 2` 상태에서 곧바로 `Store Preset`을 호출해도 안전하다(함정①) — 기존
  `_preset_store_commands`/`_store_position_preset_sequence` 몸통을 스텝 대응만
  확장하면 되고, "Step 1로 복귀 후 저장" 같은 별도 안전장치는 이번 프로브 결과로는
  불필요해 보인다(단, §GAP 5의 조건부 표현 유지).
- Rainbow(#7, 3스텝)·Rectangle 계열(#3/#4/#10)은 이번에 검증한 범위 밖 — 구현 전
  별도 라이브 확인이 필요하다.

---

## 6. T1b 보강 프로브 — Rectangle Form · 3스텝 · Phase 분산 · prop 쿼리

같은 실기(onPC 2.4.2, 응답기 1.6.0)에서 §4의 GAP 1·3·4·5 중 카탈로그 구현을 막는 항목을
후속 세션이 이어서 실측했다. `Group 11`, Color 풀(4), 임시 슬롯 `4.50`/`4.52`(둘 다
프로브 후 삭제 확인). 슬롯 번호는 `COLOR_PALETTE_SEQUENCE`(session.py) 순서로 산출했다
— 인덱스 1부터 `20+인덱스`: Warm White=21, Cool White=22, **Red=23**, Amber=24,
Yellow=25, **Green=26**, Cyan=27, **Blue=28**, Magenta=29, Lavender=30 (지시문 초안의
"Green=4.24?"는 실제로는 4.26이 맞다 — Amber가 4번째라 4.24는 Amber).

### 6.1 Rectangle Form 후보 (Transition 0 / Accel 0 / Decel 0)

```
ClearAll
Group 11
At Preset 4.23          # Step 1 = Red
Step 2
At Preset 4.28          # Step 2 = Blue
Attribute 'ColorRGB_R' At Transition 0
Attribute 'ColorRGB_G' At Transition 0
Attribute 'ColorRGB_B' At Transition 0
Attribute 'ColorRGB_R' At Accel 0
Attribute 'ColorRGB_R' At Decel 0
Store Preset 4.50
```

전부 `{'ok': True, 'result': 'OK'}` — **거부 없이 수락됐다.** 되읽기:
`node.name == '[Red#2/Blue#2]'` (`Store Preset` 이후 그대로 저장 성공, `childCount`
증분/원복도 §2와 동일 패턴으로 확인).

**정직한 한계**: `Transition 0`/`Accel 0`/`Decel 0`이 명령줄 수준에서 **거부되지 않고
수락**된다는 것만 관측했다 — §2/§4와 같은 이유로 `state` 경로는 프리셋에 실제로
어떤 파형이 저장됐는지(하드컷인지 여전히 완만한 커브인지) 셀 수 없다. 즉 "명령이
받아들여진다"는 확인이지 "Rectangle 파형이 만들어졌다"는 시각적/수치적 확인이 아니다
— 그 확인에는 라이브에서 픽스처를 실제로 재생시켜 눈으로 하드컷 여부를 보는 절차가
필요하며 이번 세션 범위 밖이다(OSC/Lua만 쓰는 이 저장소의 구조적 한계이기도 하다,
`05-phaser-editor.md` 서두 참고).

`05-phaser-editor.md` §4가 05번 문서 조사 시점에 이미 "Form 버튼 = Transition+Accel+
Decel 레이어의 단축키일 뿐, 이 세 레이어의 정확한 Rectangle 수치 조합은 공식 문서에
없다"고 기록했다(§8.7 기존 GAP과 동일). 이번 프로브는 그 GAP을 없애지 못했다 — 대신
"Transition/Accel/Decel을 0으로 지정하는 명령 자체는 거부되지 않는다"는 새 사실만
추가했다. **카탈로그 구현 시 대체안**: Rectangle 항목(#3 Chase RB, #4 Chase CM,
#10 Slam RW)은 이 세션이 실측한 `Transition 0 / Accel 0 / Decel 0` 조합을 "가장 근접한
근사치"로 채택하되, 구현 SPEC에 "라이브 시각 확인 전까지 ASSUMPTION"으로 명시하고,
M0 라이브 데모(픽스처 재생 관찰) 단계를 별도 마일스톤으로 남기는 편이 안전하다 —
공식 수치가 없는 채로 "검증됨"이라 쓰면 안 된다.

### 6.2 3스텝 (Red → Green → Blue)

```
ClearAll
Group 11
At Preset 4.23          # Step 1 = Red
Step 2
At Preset 4.26          # Step 2 = Green
Step 3
At Preset 4.28          # Step 3 = Blue
Store Preset 4.52
```

전부 `{'ok': True, 'result': 'OK'}`. 되읽기: `node.name == '[Red#2/Green#2/Blue#2]'` —
**3색 다 담겼다.** `Step 3`으로 진입 후 바로 `Store`를 호출했음에도(§3 함정①과 같은
패턴) Step 1·2가 삭제되지 않고 전부 보존됐다 — 함정①의 무재현 결론(§3)이 3스텝에서도
동일하게 성립함을 추가로 확인. `Rainbow`(카탈로그 #7)처럼 3스텝 이상 팔레트-참조
페이저를 만드는 문법은 이 순서(`At Preset` → `Step N` → `At Preset` → …)를 그대로
반복하면 된다는 근거가 됐다.

### 6.3 Phase 분산 문법

```
ClearAll
Group 11
At Preset 4.21           # Step 1 = Warm White
Step 2
At Preset 4.30           # Step 2 = Lavender
Attribute 'ColorRGB_R' At Phase 0 Thru 360
Attribute 'ColorRGB_R' At Phase 180
```

둘 다 `{'ok': True, 'result': 'OK'}` — **`At Phase 0 Thru 360` 문법과 단일값 `At Phase
180` 문법 모두 거부되지 않고 수락된다.** (이 시퀀스는 저장하지 않고 `ClearAll`로
종료했다 — Phase는 §5(레이어 총정리)에 따르면 "스텝 1 아래에서만" 전역 레이어로
나타나는 픽스처별 오프셋 개념이라, 픽스처 1대뿐인 `state` 되읽기로는 분산 여부를
확인할 수 없어 저장 검증은 §2/§4 GAP과 동일하게 생략).

### 6.4 prop 쿼리 — StepCount/Steps 존재 여부

```
prop DataPool/PresetPools/4/52 :: StepCount  → {'ok': False, 'error': 'property not readable: StepCount'}
prop DataPool/PresetPools/4/52 :: Steps      → {'ok': False, 'error': 'property not readable: Steps'}
```

**둘 다 응답기가 "property not readable"로 명시 거부했다** — 그럴듯한 이름을 추측해본
결과이지 확정된 프로퍼티명이 아니다. 이는 §4 GAP 1의 "저장된 프리셋의 실제 스텝
개수를 기계로 셀 방법"이 **여전히 미해결**이라는 뜻이다 — `state`(children 없음)와
`prop`(이 두 이름 모두 거부) 둘 다 막혔다. 다음 후보로 시도해볼 만한 프로퍼티명은
미탐색(예: `NumSteps`, `PresetType`, `Multistep` 류) — 이번 세션 범위 밖으로 남긴다.
스텝 개수를 반드시 기계로 검증해야 하는 요구가 생기면, 이 프로퍼티명 탐색을 별도
프로브로 이어가거나, "자동 이름의 대괄호 패턴"(§2, 라벨을 아직 안 붙인 시점에만
유효)을 저장 직후 1회성 검증 신호로 채택하는 절충안을 고려할 것.

### 6.5 T1b 결론 요약

| GAP(§4) | 결과 |
|---|---|
| 1. 스텝 개수 기계 검증 | **여전히 미해결** — `StepCount`/`Steps` prop 둘 다 거부(§6.4). 대체 프로퍼티명 미탐색 |
| 3. 4.21~4.30 직접 리스팅 | 이번엔 미수행(범위 밖) — 대신 개별 슬롯(4.23/4.26/4.28) 팔레트 recall이 매번 `ok:true` + 정확한 이름으로 되읽혀 존재 확인을 보강 |
| 4. Rectangle 수치 | 정확한 공식 수치는 **여전히 미확정**(GAP 유지) — `Transition 0/Accel 0/Decel 0`은 명령줄 수준에서 거부되지 않음을 새로 확인(§6.1), 시각적 하드컷 확인은 미수행 |
| 5. Speed/Phase 프리셋 반영 여부 | Phase 문법(`0 Thru 360`, `180`) 자체는 수락 확인(§6.3), 저장 반영 여부는 여전히 미검증(구조적 한계, §6.1과 동일 이유) |
| (추가) 3스텝 | **확인** — Red/Green/Blue 3스텝 모두 저장·되읽기 성공, 함정① 무재현이 3스텝에서도 유지 |
