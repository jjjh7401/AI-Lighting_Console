# t519 판정서 — BACK(역광) 201~212가 무대 화면에서 안 보이는 원인 판독

- 카드: t519 · 브랜치 `WT-back-visibility`(기준 `53a2bd9b`)
- 범위: 실기 읽기, 가짜 콘솔 리허설, 실기 전부-거절, 승인 요청까지 했다. **실기 쓰기는 0건이다.** `server/` 수정 0, 쇼 저장 송신 0.
- 대상 콘솔: 이 Mac의 grandMA3 onPC(응답기 `CopilotResponder` 1.6.5, 보내기 `127.0.0.1:8000`, 받기 `9005`). 읽기를 시작할 때 9005를 쥔 프로세스는 `app_gma3`(PID 60211)뿐이었다(`lsof -iUDP:9005`). 다른 레인의 프로브와 겹치지 않았다.

## 요약

| 의심한 원인 | 결과 | 근거 |
|---|---|---|
| 패치 회전(바닥 워시와 같은 문제) | **아니다** — 201~212 모두 ROTX/Y/Z 0, 켜지는 301도 0 | `r2_diff.txt`, t516 `v4f_floor.txt` |
| 3D 숨김·선택 불가·반전·오프셋 | **아니다** — 201과 301이 같다(VISIBLE3D true, HIDDEN false, INVERT/OFFSET 0) | `r2_diff.txt` |
| 기종·모드·주소 충돌 | **아니다** — 같은 유형 8 `1 Extended`, CONFLITEDPATCH false | t516 `diag7_patch.txt` |
| 빔이 바닥 밖으로 떨어짐 | **아니다** — 바닥(StageElement 1)이 X·Y ±15 m, Z 0이고, BACK 아래 지점(Y 4.5)은 바닥 안이다 | `r5_floor_poly.txt` |
| 무대 물체가 가림 | **아니다(읽은 범위 안에서)** — 패치 86개가 모두 조명이다. Space는 바닥 하나뿐이다 | `r3_space.txt`, `r4_space_el.txt`, t516 `diag7_patch.txt` |
| **높이(거리)** | **남은 가설 1순위, 안 잰 것** | 아래 §2 |
| 프로그래머·다른 재생이 201 속성을 쥠 | **못 잰 것** — 응답기로 프로그래머 값을 읽을 수 없다. 시퀀스 `CURRENTCUE`로는 실행 여부를 가를 수 없었다 | `r7_seq_status.txt` |

## 1. 잰 것 (2026-10-07, 실기 읽기만)

### 1-1. BACK 201과 SIDE-L 301의 패치 속성 전수 비교

`uv run python .moai/reports/t519/diff_reads.py` → `r2_diff.txt`. Fixture의 스칼라 속성 78개를 모두 읽었다(introspect 108개 중 Handle·Custom 제외). 두 기구에서 값이 다른 속성은 아래 9개뿐이다.

```
INDEX / NO / FID / NAME            (번호·이름)
OLDSUBFIXTUREINDEX / SUBFIXTUREINDEX  70 vs 94
POSX  -6.0 vs -7.0
POSY   4.5 vs  3.0
POSZ   6.2 vs  1.2
```

서브픽스처 `[Instance2#2]`도 비교했다. 다른 속성은 색인 2개뿐이다. ROTX/Y/Z, VISIBLE3D, SELECTABLE3D, HIDDEN, DMXINVERT/INVERT3D/ENCINVERT, OFFSETPAN/TILT, SCALE, MASTERREACT(Grand), BEAMANGLE(0)는 두 기구가 같다.

### 1-2. 위치(t516 `diag7_patch.txt`, 2026-10-06 실기 판독)

| 역할 | FID | X | Y | Z(높이) |
|---|---|---|---|---|
| BACK | 201~212 | -6.0 ~ 6.0 | 4.5 | 6.2 |
| SIDE-L/R | 301~316 | ±7.0 | 3.0 · 0.5 | 1.2 · 2.6 · 4.0 |
| MOVER-U(보임) | 501~508 | -1.5 ~ 5.5 | 2.5 | 6.8 |

### 1-3. 빔 정의(`geom_walk.py` → `r9_geom_walk.txt`)

- 유형 8(Mac Aura XB)
  - Pan/Tilt 축 아래 빔 `Body#4/…/Main Module#4/Beam`: 밝기 10000, 필드 25°, Wash.
  - 최상위 `Aura`·`Aura#2`·`Aura#3` 빔(움직이지 않는 아우라)도 밝기 10000, 25°, Wash다.
- 유형 11(MegaPointe, 6.8 m에서 보임): 빔 밝기 10000, 필드 25°, **Spot**.

## 2. 원인 가설과 근거

**가설 H1 — 높이 6.2 m에서 넓은 워시 빔이 바닥에 너무 옅게 퍼진다.** 판독값에서 낸 추론이고, 안 잰 것이다.

- 201과 301의 패치 차이는 위치뿐이다(§1-1). 같은 큐(248·249)에서 같은 줄(`Fixture 201 ; Attribute 'Dimmer' At 100`, `Fixture 301 ; …`)을 받았는데 301만 보였다(t516 §4-14).
- 회전 0은 매달린 자세라 빔이 바로 아래를 향한다(t516 §4-10 문서 근거, 바닥 워시 실측으로 확인).
  - 바닥에 닿는 원의 지름은 필드 25°에서 6.2 m면 약 2.75 m, 1.2 m면 약 0.53 m다.
  - 거리 제곱 비로 바닥 밝기는 약 **27배** 차이 난다. 3D 화면이 거리 감쇠를 이렇게 그리는지는 **안 잰 것**이다.
- 6.8 m의 MegaPointe가 보이는 것과는 어긋날 수 있다. 다만 MegaPointe는 Spot 빔이고, t516 v4에서는 움직이는 모습을 봤다. 같은 조건의 바닥 밝기 비교가 아니다.

**가설 H2 — 프로그래머나 다른 재생이 201의 Shutter·Dimmer·Tilt를 쥐고 있다.** 이것도 못 잰 것이다. 응답기에는 속성 값을 읽는 동사가 없다. H1 시험에서 201이 1.2 m에서 보이면 H2는 거의 빠진다(같은 기구, 같은 큐, 높이만 바뀜).

## 3. 가르는 시험 — 1대 먼저 (승인 요청)

변수는 하나다. **201의 높이만 6.2 → 1.2로 바꾼다.** 새 번호를 쓰지 않는다. 패치 1개 값만 바꾸고 되돌린다. 바닥 워시 1b 단계와 같은 꼴, 같은 실행기(`floor_place.py`)를 쓴다.

| 순서 | 파일 | 줄 | sha256 | 내용 |
|---|---|---|---|---|
| ① | `approval_back_d1.txt` | 1 | `d38a0ccf2130fef4b87026a666ac13cfe3259ad879a5b7d03de7584be1b2e15f` | `Set Fixture 201 Posz '1.2'` |
| ② | `approval_replay_248.txt` | 2 | `8fcb4edb9369b52101386ba5e130cd8f811ad6474b23c22e5ef31a9f3167ed5f` | `Goto Cue 1 Sequence 248` → 20초 → `Off Sequence 248` (쓰기 아님) |
| ③ | `approval_back_d1_revert.txt` | 1 | `77d8436051b4fe35b3f6b1609cf5c14fc431c020498a0147f55da72bfff62a80` | `Set Fixture 201 Posz '6.2'` |

- 각 단계에서 일어나는 일
  - ①은 사전 판독이 NAME `BACK 201`, ROTX/Y/Z 0, POSZ 6.2가 아니면 보내지 않는다. 사후에는 POSZ 1.2를 되읽어 판정한다.
  - ②는 재생 전에 248의 이름을 읽어 v5 이름과 다르면 재생하지 않는다. 248은 201·201.1·301·301.1에 Dimmer 100만 준다(t516 `approval_rhythm_probe_v5.txt:30-33`). 301이 대조군이다.
  - ③은 사전에 POSZ 1.2를 요구한다.
- 리허설(가짜 콘솔) 결과
  - 세 파일 모두 exit 0이었다.
  - 보낸 문면이 파일과 같다(`d1_rehearse`·`d1rev_rehearse`·`r248_rehearse` 모두 `rehearse==file True`).
- 실기 전부-거절 결과(①·②)
  - `d1_denyall`: 사전 판독 `BACK 201 · POSZ 6.1999998092651 · ROTX/Y/Z 0.0`이 통과했다. 감사 로그는 `executed/props_query 1`, `rejected/t519_back_place 1`이다.
  - `r248_denyall`: 이름 사전 판독 `RHYTHM PROBE v5 - F1 AURA DIMMER 100`이 통과했다. 감사 로그는 `executed/props_query 1`, `rejected 2`이다(재생기의 위험 분류 이름은 `t516_replay_v5`를 그대로 쓴다).
  - 두 실행 모두 콘솔 쓰기 0건이다. 요청 문면은 파일과 같다(`live==file True`).
- ③은 전부-거절을 돌릴 수 없다. 사전 기대값(POSZ 1.2)이 ①을 실행한 뒤의 상태이기 때문이다. 문면은 리허설에서 땄다.
- 실행(리드 「실행」 뒤에만)
  1. `uv run python .moai/reports/t519/back_place.py .moai/reports/t519/d1_live --stage d1 --approve .moai/reports/t519/d1_denyall`
  2. `uv run python .moai/reports/t519/replay_248.py .moai/reports/t519/r248_live --approve .moai/reports/t519/r248_denyall`
  3. 감독 관찰이 끝난 뒤: `uv run python .moai/reports/t519/back_place.py .moai/reports/t519/d1rev_live --stage d1-revert --approve .moai/reports/t519/d1rev_rehearse`
     - 되돌리기는 전부-거절 폴더가 없어서 리허설 기록의 문면으로 고정한다.

### 결과 읽는 법

- **201이 1.2 m에서 보인다:** 원인은 높이(거리)다. 기구 고장도 패치 문제도 아니다. 고치는 방법은 감독이 정한다.
  - 높이를 그대로 두고 연출로 푸는 방법: 역광답게 Tilt를 객석 쪽으로 기울여 빔 줄기를 보이게 하거나, Zoom을 좁혀 밝기를 모은다. 큐 쓰기라 새 번호가 필요하고, t520과 번호를 나눠야 한다.
  - 높이 자체를 낮추는 방법: 12대 `Posz` 변경이다. 패치 쓰기이고, 실제 리그 높이와 달라진다.
- **201이 1.2 m에서도 안 보인다:** 높이가 원인이 아니다. 201 쪽 값(H2)이나 서브픽스처 구조를 의심한다. 다음은 같은 자리에 301을 옮겨 보는 대조가 될 것이다.

## 4. 안 잰 것

- 3D 화면이 거리에 따라 바닥 밝기를 줄이는지, 감독 화면의 카메라 위치와 빔 표시 설정.
- 201의 현재 프로그래머 값(Dimmer, Shutter, Tilt, Zoom). 응답기로 읽을 수 없다.
- 시퀀스 `CURRENTCUE`는 꺼진 프로브 시퀀스에도 값이 있었다(`r7_seq_status.txt`). 이 값으로는 지금 켜져 있는지를 가를 수 없다. 대신 무엇이 켜져 있는지는 감독 화면에서 본다.
- 202~212는 패치 속성을 개별 비교하지 않았다. 위치·회전·반전은 t516 판독으로 12대 모두 같다.

## 5. 잔여 위험

- ① 실행 뒤 ③을 돌리지 않으면 201이 1.2 m에 남는다. 쇼를 저장하기 전에 ③을 돌려야 한다.
- 248을 켜면 301도 켜진다. 대조군이라 의도한 것이다.
- lane-2의 t520도 응답기를 쓴다. 실행하기 전에 `lsof -iUDP:9005`로 겹치는지 확인한다.

## 6. 읽기 도구와 기록

| 파일 | 내용 |
|---|---|
| `tabulate_prior.py` | t516 판독 파일에서 201~212·301~316 줄만 뽑기(콘솔 송신 0) |
| `diff_reads.py` → `r2_diff.txt` | 201 대 301 속성 전수 비교 |
| `r1_introspect.txt`, `r3_space.txt`, `r4_space_el.txt`, `r5_floor_poly.txt` | 기구·Stage·Space·바닥 다각형 |
| `seq_status.py` → `r7_seq_status.txt` | 시퀀스 49개 상태 |
| `geom_walk.py` → `r9_geom_walk.txt` | 유형 8·11 빔 정의 |
| `back_place.py`, `replay_248.py` | 시험 실행기(t516 `floor_place.py`·`replay_v5.py` 재사용) |
