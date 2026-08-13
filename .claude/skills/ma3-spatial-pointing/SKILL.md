---
name: ma3-spatial-pointing
description: >
  grandMA3 3D 공간에서 무빙헤드 헤드를 임의의 무대 좌표로 향하게 하는 방법 —
  콘솔 Pan/Tilt 값과 3D 빔 방향의 실측 상관관계, 역산 공식, 명령 문법, 검증 절차.
  "장비가 (x,y,z)를 바라보게", "빔을 무대 중앙으로", "헤드 조준/포인팅", 팬/틸트
  단위·좌표계 질문, 3D 빔 방향이 어긋날 때 사용한다.
---

# MA3 Spatial Pointing — Pan/Tilt ↔ 3D 방향 실측 모델

grandMA3 onPC 2.4.2에서 2026-08-13 라이브 계측으로 확립한 모델이다
(RLB350M1/MMX 40대 리그, `NewShow_2026.08.08`, 패치 회전 전부 0).
계측 방법: 한 픽스처에 알려진 Pan/Tilt를 명령하고 3D 창의 빔 착지점을
스크린샷으로 판독 → 역산 공식으로 40대 전체를 (0,0,0)에 조준해 수렴 확인.

## 1. 실측 좌표·단위 규약 (전부 검증됨)

| 사실 | 측정 근거 |
|---|---|
| `Attribute 'Pan'/'Tilt' At <n>` 은 **물리 도(degree)** (Natural readout) — 퍼센트 아님 | `Tilt At 45` → 정확한 45° 빔 원뿔; 40대 수렴 사진 |
| `Pan 0 / Tilt 0` = 빔이 **수직 아래(−Z)** | 픽스처 (4,0,6) 바로 아래 (4,0,0)에 스팟 |
| `Tilt +` = 빔이 무대 **+Y(업스테이지)** 쪽으로 기움 (Pan 0 기준) | Tilt 45 스팟이 +Y로 이동 |
| `Pan +` = 틸트 방향을 위에서 봐서 **반시계**(+Y→−X at +90) 회전 | Pan 90/Tilt 45 스팟이 −X로 6·tan45 이동 |
| 패치 바디 회전 `Rotz r` 은 Pan 프레임을 같은 방향으로 회전 → 필요한 Pan에서 **r을 빼라** | Rotz 90 + Pan 0/Tilt 45 → 빔이 −X (Pan 90과 동일) |
| 음수 At 값은 따옴표 없이 그대로 동작 (`At -150`) | 40대 번들 실행 0 실패 + 수렴 |
| 픽스처 위치/회전은 `Patch/Stages/1/Fixtures/<slot>` 의 `Posx/Posy/Posz/Rotx/Roty/Rotz` 속성 (responder `prop` verb로 읽기, 슬롯≠FID 주의 — `FID` 속성으로 대조) | pointing_probe 전수 판독 |
| `Rotx`/`Roty` 의 부호·순서는 **미계측** — 0이 아닌 리그에서는 사용 전 재계측 필요 | — |

빔 방향 벡터 (Rotz=0, p/t는 도):

```
d = ( -sin(p)·sin(t),  cos(p)·sin(t),  -cos(t) )
```

## 2. 역산 공식 (target 조준)

픽스처 위치 F, 목표 T, `v = T − F`:

```
tilt = acos( -v_z / |v| )            # 0 = 수직 아래, 도
pan  = atan2( -v_x, v_y ) − Rotz     # (−180, 180] 로 정규화
```

- `|v| ≈ 0` (픽스처가 목표 위에 있음) → 방향 없음, 제외하라.
- tilt > 135° → 헤드 가동범위 밖, 클램프하지 말고 제외·보고하라.
- 구현: `server/spatial/pointing.py` — `aim_pan_tilt()`, `pointing_commands()`.
  단위 테스트: `server/tests/test_spatial_pointing.py` (실측 케이스 고정).

## 2b. 디자인 룩 (LOOK 계열) — 장비 간 상관관계로 값이 정해지는 포지션

한 점 조준(FOCUS)이 아니라 리그의 **관계**가 값을 만든다. 전부 라이브 검증됨:

- **FAN out/in/cross** (`fan_pan_tilt`): 정렬된 체인(x 오름차순 등)의 i번째가
  pan 오프셋 `spread·(2i/(N−1)−1)`을 받는다 (MA3 Align Linear와 동일 분배).
  기본 base = pan 180(객석 방향)/tilt 45. `in`은 오프셋 반전(모임),
  `cross`는 홀수번째 부호 반전(교차빔).
- **RING out/in** (`radial_pan_tilt`): 리그 무게중심 C 기준. `out`은
  `target = F + (F−C)/|F−C|·reach` (바닥, 기본 reach 4m) — 바깥 방사.
  `in`은 중심축 위 한 점 `(C, height)`로 수렴. 중심 위에 선 픽스처는
  out 방사 방향이 없으므로 제외·보고.
- **프리셋 저장** (`position_preset_store_commands`): 조준 번들 직후 프로그래머가
  살아있는 상태에서 `Store Preset 2.<n>` + `Label Preset 2.<n> '<name>'`.
  큐는 프리셋 참조로 빌드하면 재생성만으로 전 큐가 따라온다. 프리셋 번호는
  사용자가 명시했을 때만 사용(임의 슬롯 추측 금지).
- 세션 어휘: "부채살/교차/모아" → FAN, "안쪽·바깥쪽을 바라보게" → RING,
  "프리셋 N로 저장" → 저장 체이닝 (`_look_pan_tilt`, `server/web/session.py`).
  전략 문서: `docs/proposals/pan-tilt-position-preset-strategy.md`.

## 2c. 기본 포지션 10종 시퀀스 (`basic_position_presets`)

"기본 포지션 10개를 프리셋에 저장" 요청의 표준 시퀀스. 1번은 **항상 'Home'**,
이후 기본→변형 큰 순서. 전부 리그 좌표에서 유도되므로 일자·원형·사각형·삼각형·
반원 어떤 배치에도 같은 이름 체계가 적용된다 (중심=무게중심, 보컬점=전면 모서리
−2m/높이 1.6m, 수렴콘=중심 위 3m):

| # | 이름 | 정의 |
|---|---|---|
| 1 | Home | 전 대 pan0/tilt0 (수직 아래) |
| 2 | Wall | 전 대 pan180/tilt45 — 평행 빔 커튼 |
| 3 | Audience | 전 대 pan180/tilt100 — 객석 공중 |
| 4 | Center | 무게중심 바닥 FOCUS |
| 5 | Vocal DSC | (cx, ymin−2, 1.6) FOCUS |
| 6 | Fan Out | x정렬 체인 팬 ±30° |
| 7 | Fan In | 오프셋 반전 (모임) |
| 8 | Cross | 홀수번째 부호 반전 (교차) |
| 9 | Ring Out | 방사 바깥 (reach 4m 바닥) |
| 10 | Ring In | 중심 위 3m 수렴콘 |

- 저장 플로우(`_basic_position_presets`): 시작 번호가 지시문에 없으면 질문 카드
  **한 장**으로 묻는다 — `Store Preset`은 경고 없이 덮어쓰므로 번호는 운영자 결정.
  "N번부터"가 있으면 카드 생략. 프리셋마다 적용→`Store`→`Label`→`ClearAll`을
  별도 번들로 실행해 하나가 거부돼도 나머지가 살아남는다.
- 리콜: `Fixture <sel> ; At Preset 2.<n>` (라이브 검증: 2.28 'Cross' 재현 확인).
- MA3는 프리셋 이름 중복 시 `#2` 접미사를 자동으로 붙인다(대소문자 무시) —
  같은 이름을 재저장하기 전에 옛 슬롯을 지워라.
- Fan 체인은 리그의 **지배축**을 따른다 (`fan_chain`): x/y 스팬이 큰 쪽으로
  정렬, 동률(링·정사각형)이면 x — 세로 일자 배치에서도 부채살이 성립한다.
- 배치 적응 라이브 검증 완료 (tools/placement_verify.py — 재배치→룩 적용→
  원좌표 비트단위 복원): 일자 40대 Fan Out, 반원 Ring Out(무게중심 기준
  바깥 방사), 삼각형 둘레 Center(무게중심 수렴) 모두 3D에서 확인.

## 3. 명령 문법 — 픽스처당 한 줄로 체이닝 (필수)

```
Fixture 20 ; Attribute 'Dimmer' At 100 ; Attribute 'Pan' At 90 ; Attribute 'Tilt' At 33.7
Fixture 26 ; Attribute 'Dimmer' At 100 ; Attribute 'Pan' At -90 ; Attribute 'Tilt' At 33.7
```

- **한 픽스처 = 한 줄** (`;` 체이닝). 줄을 쪼개면 안 된다: 실행 경로가 같은
  지시 안에서 **동일한 명령 텍스트를 중복 실행 방지로 건너뛴다**
  (라이브 계측: 분리형 160줄 중 84줄이 `skipped_already_executed`).
  대칭 리그에서는 두 픽스처가 같은 Tilt 값을 갖는 일이 흔하므로 반드시
  `Fixture <fid>` 접두로 줄을 유일하게 만든다.
- 값은 0.1° 반올림이면 충분 (6 m 트림에서 ~1 cm 오차).
- 서버 경로: `run_commands` 도구 (승인 게이트 통과). 직접 핸들러
  `_point_fixtures_at_target` (`server/web/session.py`)가
  "…중앙/(x,y,z)…바라보게" 요청을 모델 없이 처리한다.
  명령 생성은 `server/spatial/pointing.py::pointing_commands()`.

## 4. 검증 절차 (재계측 레시피)

1. `grandma3-web-stable` 프로세스를 잠시 중지 (feedback 포트 9005 단독 점유).
2. `tools/console_probe.py` / `tools/pointing_probe.py` 로 패치 좌표 판독.
3. 한 픽스처: `ClearAll` → 선택 → Dimmer 100 → 알려진 Pan/Tilt → onPC 3D 창
   스크린샷(`screencapture -l <windowid>`) → 스팟 위치로 방향 확인.
4. 전 리그 역산 조준 → 스팟이 한 점에 수렴하면 모델 유효.
5. 실험 후 `ClearAll`, 바꾼 패치 값(Rotz 등) 원복, 서버 재시작.

## 5. 함정

- 룰북 31_choreography_patterns.md 의 "Pan/Tilt At = percent" 표기는 오류다.
  단, 그 파일은 바이트 단위로 핀된 보존 자산이라 수정 금지 — 정정된 규약은
  `32_spatial_design.md` 의 "Pan/Tilt 조준" 절에 있다(이 절이 뒤에 로드되어
  우선한다). 도 단위가 맞다.
- 사용된 3D 뷰 카메라는 원근이라 스크린샷의 +Y 이동이 작아 보인다 —
  단위 판정은 반드시 큰 각도(45°+)와 산술 비교로 하라.
- `Set Fixture <fid> Posx -3.5` 는 부호를 삼킨다 — 패치 좌표 쓰기는 반드시
  작은따옴표(`'-3.5'`). Attribute `At` 는 해당 없음.
- 원점에 놓인 마커 오브젝트(FID 41 Sphere 등)는 목표와 좌표가 겹쳐
  조준 불능 — 제외 대상.
