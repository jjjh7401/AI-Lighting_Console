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
- **2축 부채살 (pan/tilt fan)**: 일자·반원·삼각형·사각형처럼 펼쳐진 배치의
  표준 룩. `tilt_spread`가 중심 대칭 V(`Align <>` on Tilt 상당)를 더한다 —
  중앙 장비는 base tilt, 끝 장비는 ±tilt_spread만큼 더 젖힘(음수 = 끝이
  내려감). 끝 장비 tilt가 한계(135°)를 넘으면 전체 거부. 어휘: "팬 45도
  틸트 20도 부채살", "팬틸트 모두/틸트도/입체 부채살"(기본 틸트 ±15도).
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

## 2d. 무드 → 포지션 제안 (`position_moods.py`)

연출 의도만 말해도 포지션을 제안한다 — 단 **실행이 아니라 카드 제안**이 기본:
무드 키워드 + 포지션 의도어(포지션/포커스/바라보/잡아/연출 등)가 함께 있을 때
`_position_mood_suggestion`이 추천 1 + 대안 2 + "적용 안 함" 카드를 띄우고,
선택된 룩만 `basic_position_presets` 계산으로 적용한다. 거절·무응답이면 아무
명령도 보내지 않는다.

매핑(키워드 무겹침 — 테스트 고정): 발라드·잔잔 → Vocal DSC / 오프닝·등장 →
Center / 웅장·피날레 → Ring In / 후렴·클럽·드롭 → Cross / 화려·펼침 →
Fan Out / 관객·떼창 → Audience / 커튼·합창 → Wall / 리셋·대기 → Home.
득점(키워드 수) 최다 항목이 이긴다. 무드만 있고 포지션 의도어가 없으면
색·룩 요청일 수 있으므로 모델 경로(find_looks)에 남긴다. 룰북
`32_spatial_design.md`의 "연출 의도 → 포지션 어휘" 절이 모델 경로의 근거.

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
- **큐 페이저 함정 (라이브 계측)**: 페이저(컬러 체이스 등)가 든 큐에 포지션만
  담긴 프로그래머를 `Store Cue <n> ... /merge`로 병합하면 **페이저가 평탄화**
  된다 — 재생 시 무지개가 멎은 정지 스프레드만 남는다. ok 응답으로는 구분
  불가(룰북의 "ok ≠ 움직임"과 같은 결). 올바른 절차: 포지션 프리셋 리콜과
  페이저를 **한 프로그래머 상태**에 함께 만든 뒤 `/Overwrite`로 저장한다.
  검증은 3D 두 프레임 픽셀 diff(정지=0px, 구동=수만 px)로 한다.
- 익스큐터 배정의 검증 문법은 `Assign Sequence <n> At Executor <m>` —
  `At Page 1.<x>` 형태는 Cannot Create Object로 거부될 수 있다.

## 3b. 포지션 큐 트랜지션 (T1 실측 — SPEC-COPILOT-CUETIME-001)

검증된 번들(빌더 `position_cue_store_commands` + `preset_recall_command`,
세션 어휘 "프리셋 N을 시퀀스 S 큐 C로 저장, 페이드 F초"):

```
Fixture 20 + 26 + … ; At Preset 2.28
Store Sequence 101 Cue 1 'Pos 2.28' CueFade 5
ClearAll
```

- 라이브 확인: 페이드 중 3D 프레임 diff 13만~40만 px, 페이드 종료 후
  연속 프레임 diff 5 px(정지). 픽스처 시트 PanTilt 열이 값이 아니라
  "2.28 Cro…" **프리셋 참조**로 표시 — 참조 저장 성립.
- **큐 이름의 점(.)은 MA3가 삼킨다**: `'Pos 2.28'`로 저장하면 실제 큐
  이름은 `Pos 228`이 된다. 이름으로 오브젝트를 다시 찾을 때(prop/state
  경로) 점 없는 이름을 써야 한다.
- **CueFade readback**: Cue 오브젝트의 `CueFade`/`Fade` prop은
  `property not readable`. 실제 값은 **큐 Part**에 `CueInFade`로 산다 —
  `prop:DataPool/Sequences/<n>/<cueName>/<partName>|CueInFade` (part
  이름은 큐 이름과 동일; 실측 5.0 readback). CueFade는 state snapshot에도
  없다(songcue_report.py PROPERTY_UNOBSERVED_NOTE) — ok 응답만으로 페이드
  검증 금지.
- 시퀀스 번호는 운영자 결정(카드 1장) — Store는 기존 큐 슬롯에 그대로
  얹힌다. `/Merge`·`/Overwrite`는 쓰지 않는다(페이저 평탄화·블랙리스트).

## 3c. MIB (Move In Black) — T2 실측 (룰북 무전례, 이 계측이 근거)

규칙(`server/spatial/mib.py::apply_mib`): 마지막 명시 디머가 0(다크)이고
다음 큐가 "새 프리셋 + 디머 >0"(리빌+이동)이면, 두 큐 번호의 중간에
**포지션 전용 선이동 큐**(기본 CueFade 1)를 삽입하고 리빌 큐에서 포지션을
제거한다. 트래킹이 선이동 큐의 디머를 0으로 유지하므로 디머 라인은 넣지
않는다. 시작 상태 불명(명시 디머 없음)은 **점등으로 간주** — 보일지 모르는
리그에 유령 선이동을 넣으면 MIB가 없애려는 스윙을 오히려 만든다.

라이브 A/B 계측 (onPC 2.4.2, 40대 링, Wide 2.26→Black→Cross 2.28):

| 측정 | MIB (Seq 102, 큐 1/2/2.5/3) | 대조군 (Seq 103, 선이동 없음) |
|---|---|---|
| 다크 선이동 중 가시 변화 | 0 px (잔여 UI 58px 불변) | — |
| 리빌 t0.5s→t2.5s moved_away | **0 px** (밝기만 성장) | **4,731 px** (빔이 자리를 떠남) |
| 리빌 초반↔후반 기하 IoU (Otsu) | 0.70 | 0.54 |

- 판독법: moved_away = 초반에 밝던 픽셀이 후반에 어두워진 수 — 페이드 중
  빔이 스윙하면 커지고, 이미 주차된 빔이 페이드 인만 하면 0이다.
- 측정은 3D 뷰포트만 크롭해서 하라 — 창 전체를 diff하면 픽스처 시트의
  숫자 갱신이 잡음으로 들어온다.
- 고정 임계값 이진화는 밝기 차이에 눌려 판별력이 없다(실측: moved_away가
  양쪽 다 0으로 나옴) — 프레임별 Otsu 임계값을 써라.
- `Delete Sequence <n> /NoConfirm` 은 probe(게이트 밖 계측 경로)에서 확인
  팝업 없이 동작 — 서버 경로에서는 여전히 블랙리스트(승인 필요).
- **선이동 큐는 반드시 `TrigType 'Follow'`** (실측, Seq 113→114): Store만
  하면 TrigType이 Go로 남아 선이동이 스스로 발화하지 않는다 — 운영자가
  드롭 타이밍에 누른 Go가 "보이지 않는 다크 이동"을 재생하고 리빌이 한
  박자 늦는다. 저장 직후
  `Set Cue <k.5> Sequence <n> Property 'TrigType' 'Follow'` 를 붙여라
  (`premove_follow_command`). Follow면 암전 큐 완료 시 자동 발화 —
  Go 횟수 = 곡 구간 수. 검증: Go 12번으로 14큐 시트 완주, 리빌 첫 Go에서
  즉시 점등(moved_away 0 px).

## 3d. 곡 구조 포지션 큐 시트 (T3 — songcue × moods × MIB 결합)

세션 어휘: `"포지션 큐 시트, 시퀀스 S, 프리셋 P번부터[, 페이드 F초]:
이름 시각 무드, 이름 시각 무드, …"` (시각 = `m:ss` 또는 `N초`).
구현: `server/spatial/position_cuesheet.py::build_position_cue_sheet` —
구간 무드를 `position_moods`로 풀어 운영자 기준(P=Home 슬롯) 프리셋
참조 큐로 빌드하고, "암전" 구간은 디머 0 큐, 그 뒤 리빌에는 `apply_mib`가
다크 선이동 큐를 자동 삽입한다. 무드가 표와 안 맞는 구간은 추측 없이
건너뛰고 번호만 소비(songcue 관례). 라이브 검증(Seq 110, 5구간): 구간 간
기하 IoU 0.12~0.16(전부 다른 포지션), 암전·선이동 가시 변화 0 px,
리빌 moved_away 0 px.
E2E(실제 앱 UI, Seq 112 — 1분 헤비메탈 12구간·14큐·페이드 0.5초): 암전
히트 2회 뒤 MIB 3.5/7.5 자동 삽입, 점등 룩 7종 기하 전부 구별(IoU
0.01~0.65), 반복 프리셋 리콜은 픽셀 단위 결정론. 함정: 한글+숫자
구간명("브레이크1")은 ASCII 정리 후 숫자만 남아 큐 이름이 '1'로 퇴화 —
digits-only 남으면 'Section n' 폴백(코드에 반영).

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
