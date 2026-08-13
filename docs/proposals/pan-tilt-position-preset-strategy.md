# Pan/Tilt 포지션 프리셋 전략 — 공간(Focus) × 디자인(Look) 이원 체계 제안

웹 리서치(출처 하단)와 이 저장소의 실측 포인팅 모델(`server/spatial/pointing.py`,
`ma3-spatial-pointing` 스킬)을 종합해, 조명연출에 좋은 Pan/Tilt 프리셋 구조를 제안한다.

## 1. 리서치로 확인한 업계 원칙

1. **프리셋(팔레트)은 참조(reference)로 저장된다** — 큐에는 값이 아니라 프리셋
   참조가 들어가므로, 프리셋 하나를 업데이트하면 그것을 쓴 모든 큐가 따라간다.
   투어에서 매일 달라지는 무대에 재포커스가 가능한 이유가 이것이다.
   (On Stage Lighting "Palettes", PLSN "Watch Where You Point That Thing!")
2. **포지션 팔레트는 20개 이하** — 매 공연장마다 전부 업데이트해야 하므로
   과다하면 운영 불능. 흔한 이름: Up / Down / In / Out / Audience / Cross /
   DSC(Down Stage Centre) / Drums. (PLSN "Concert Touring 101",
   On Stage Lighting "Concert Lighting Programming in 30 Minutes")
3. **포지션 프리셋의 최소 저장 속성은 Pan/Tilt(+Zoom)** — 위치의 의미가 줌·셔터와
   함께 있을 때 완성되는 경우 함께 담는다. (Mark LaPierre "The Palettes")
4. **사람 위치를 몰라도 포지션 프리셋으로 먼저 프로그래밍** — 동선이 확정되면
   프리셋만 업데이트한다. (Church Production "Moving Light Programming")
5. **큰 조정 → 절반 → 쌍 → 개별 순서로 잡는다**. 대칭 리그는 절반을 Pan Invert
   하고 Align/Fan으로 편다. (On Stage Lighting "21 Ways")
6. **틸트 먼저, 팬 나중** — 헤드가 아래를 향한 상태에서 팬을 돌리면 변화가 안
   보인다. (LightSoundJournal "The Artistry and Finesse in Programming Moving Lights")
7. **Pan/Tilt를 공연 영역으로 제한한 정적 포지션 몇 개를 먼저 만들고**, 그 위에
   무브먼트를 얹는다. 빠른 움직임은 드롭/피날레용으로 아껴 둔다.
8. **MA3 고유 도구**: `Align`(Linear/Sinus 5모드)이 선택 순서를 따라 값을
   분배한다 — 팬 부채살은 `Align /`+Pan, 틸트 부채살은 `Align <>`+Tilt에 해당.
   교차빔(Crossed Fan)은 팬 부호를 교대로 뒤집는 것이다(FancyFAN 매뉴얼).
   **직선 라인에 정확히 정렬된 fan은 Pan/Tilt Align만으로는 곡선이 진다** —
   MA3 포럼 권장 해법은 XYZ(StageX 가상 속성)에 Align을 거는 것. 우리 시스템은
   XYZ 없이도 좌표 역산으로 같은 결과를 만든다(아래 §3).

## 2. 제안 — 프리셋 풀을 두 계열로 나눈다

포지션은 결정 근거가 다른 두 종류가 있고, 저장·재계산 방식도 달라야 한다.

### A계열 — FOCUS (공간 기준: "어느 점을 비추나")

모든 빔이 무대의 한 3D 점을 통과한다. 픽스처마다 Pan/Tilt가 다르지만 그 값은
**패치 좌표 + 목표점에서 전부 역산 가능**하다 (`aim_pan_tilt`). 즉 이 계열은
사람이 다이얼로 잡는 게 아니라 **좌표로 생성하고, 리그가 움직이면 재생성**한다.

| # | 이름 | 목표점(예) |
|---|---|---|
| P1 | HOME | tilt 0 (수직 아래) — 파킹/리셋 |
| P2 | DSC VOCAL | (0, -4, 1.6) 다운스테이지 센터, 사람 키 높이 |
| P3 | CENTER FLOOR | (0, 0, 0) 무대 중앙 바닥 |
| P4 | DRUMS | 드럼 라이저 좌표 |
| P5 | SL / P6 SR | 무대 좌/우 밴드 위치 |
| P7 | AUDIENCE | 객석 방향 한 점 (하우스 안쪽, tilt 한계 주의) |

### B계열 — LOOK (디자인 기준: "빔들이 어떤 모양을 이루나")

사용자 지적대로, 값이 **장비 간 상관관계**로 결정된다. 일렬 10대의 부채살은
픽스처 인덱스(순서)의 함수이고, 원형 리그의 in/out은 중심에 대한 방위각의
함수다. 핵심: **이것도 전부 기하로 역산 가능하다** — 목표를 "한 점"이 아니라
"픽스처별 규칙"으로 일반화하면 된다.

| # | 이름 | 규칙 (픽스처 i, N대 / 링 중심 C) |
|---|---|---|
| P11 | FAN OUT | 기준 방향에 pan 오프셋 `spread·(2i/(N−1) − 1)` — 끝 장비가 바깥으로 |
| P12 | FAN IN (CONVERGE) | FAN OUT의 부호 반전, 또는 리그 위 한 점을 FOCUS로 조준 |
| P13 | CROSS | 팬 오프셋 부호를 짝/홀 교대로 — 교차빔 |
| P14 | WALL (PARALLEL) | 전 대 동일 Pan/Tilt — 평행 빔 커튼 (tilt 0 = 수직 기둥) |
| P15 | RING OUT | 원형 리그: 각 픽스처가 중심 반대 방향, `target = F + k·(F−C)` 수평성분 |
| P16 | RING IN | 각 픽스처가 중심축 위/아래 한 점을 조준 (converge 콘) |
| P17 | AUD SWEEP BASE | 객석 쪽 낮은 틸트의 기준 포지션 — 스윕 FX의 출발점 |

FAN 곡률 주의: 직선 트러스에서 빔 착지선을 **직선**으로 만들려면 pan 등간격이
아니라 **착지점 등간격**(바닥의 등간격 점들을 FOCUS 역산)으로 잡아야 한다 —
MA3 포럼이 XYZ Align으로 푸는 문제를 우리는 좌표 역산으로 정확히 풀 수 있다.

### 저장 규칙

- MA3 **Position 프리셋 풀**(Preset 2.x)에 **Selective 프리셋**으로 저장한다
  (픽스처별 값이 다르므로 Universal/Global이 아닌 Selective가 맞다).
  절차: 픽스처별 Pan/Tilt 프로그래머 설정 → `Store Preset 2.<n> "이름"` → `ClearAll`.
- 큐/시퀀스는 반드시 프리셋 참조로 빌드한다(§1-1). 리그 이동·공연장 변경 시
  **프리셋만 재생성**하면 모든 큐가 따라온다.
- 총 개수는 FOCUS ≤ 8, LOOK ≤ 8로 상한 (§1-2의 20개 원칙).
- 이름은 역할 언어로 (DSC VOCAL, FAN OUT), 좌표·각도값을 이름에 넣지 않는다.

## 3. 이 시스템에서의 구현 경로

1. `server/spatial/pointing.py` 확장:
   - `fan_pan_tilt(fixtures, base, spread, mode=out|in|cross)` — 정렬된 선택
     순서(기존 `spatial_sorted_fids` 재사용) 위에 팬 오프셋 분배.
   - `radial_aim(fixtures, center, mode=in|out, drop)` — 링 in/out. in은
     중심축 위 한 점 조준, out은 `F + k·(F−C)` 방향(기존 `aim_pan_tilt` 재사용).
   - 직선 착지 fan: 바닥 등간격 점 배열을 만들어 픽스처별 FOCUS 역산.
2. 명령 채널은 기존과 동일: 픽스처당 `Fixture <fid> ; Attribute 'Pan' At … ;
   Attribute 'Tilt' At …` 한 줄 체이닝 → `run_commands`(승인 게이트) →
   `Store Preset 2.<n>` → `ClearAll`.
3. 세션 어휘: "부채살로 펼쳐/모아", "교차빔", "안쪽/바깥쪽 보게", "관객석으로"
   → LOOK 계열, "…를 비춰/바라보게" → FOCUS 계열로 라우팅.
4. 프리셋 재생성 커맨드(리그 이동 후 일괄 갱신)를 운영 루틴으로 제공.

## 4. 출처

- On Stage Lighting — Moving Light Control: Palettes / 21 Ways to an Easier
  Programming Life / Concert Lighting Programming in 30 Minutes
  (https://www.onstagelighting.co.uk/)
- PLSN — Concert Touring 101, Watch Where You Point That Thing!
  (https://plsn.com/)
- Church Production — Moving Light Programming
  (https://www.churchproduction.com/education/moving-light-programming/)
- Mark LaPierre — Lighting Music Basics 3: The Palettes
  (https://www.mlp-lighting.com/programming/lighting-music-basics-3-the-palettes/)
- MA Lighting — grandMA3 Align 매뉴얼
  (https://help.malighting.com/grandMA3/2.2/HTML/operate_align.html),
  MA3 포럼 "Create fan position with all tilt on one line"
  (https://forum.malighting.com/forum/thread/69166-…) — XYZ StageX Align 권장
- FancyFAN for MA3 사용자 매뉴얼 — Crossed Fan 모드
  (https://addondesk.com/wp-content/uploads/2024/05/FancyFAN-User-Manual.pdf)
- LightSoundJournal — The Artistry and Finesse in Programming Moving Lights
  (https://www.lightsoundjournal.com/2018/11/18/…)
