# t519 판정서 — BACK(역광) 201~212가 무대 화면에서 안 보이는 원인 판독

> **정정 2026-10-07**: 문제는 「안 보임」이 아니라 「역광 방향이 아님(빔이 수직 아래)」이었다(감독 원문, §3-1 정정). 아래 §요약·§2의 원인 표는 잘못 전달된 문제를 기준으로 쓴 것이다. 현재 판정과 다음 단계는 §3-1 정정과 §7에 있다.

- 카드: t519 · 브랜치 `WT-back-visibility`(기준 `53a2bd9b`)
- 범위: 실기 읽기, 가짜 콘솔 리허설, 실기 전부-거절, 승인 요청까지 했다. 실기 쓰기는 리드 「실행」 뒤 §3-1의 201 Posz 두 번(바꾸기와 되돌리기)뿐이다. 콘솔에 남은 변경은 없다. `server/` 수정 0, 쇼 저장 송신 0.
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

## 3-1. 시험 결과 (2026-10-07, 리드 「실행」 두 번 — ①② 한 번, ③ 한 번)

| 단계 | 기록 | 결과 |
|---|---|---|
| ① `d1_live` | 사전 `BACK 201 · POSZ 6.1999998092651 · ROT 0` → 사후 POSZ `1.2000000476837` | 승인 문면 = 송신 1줄 · executed/command 1 |
| ② `r248_live` | 이름 사전 판독 `RHYTHM PROBE v5 - F1 AURA DIMMER 100` 일치 · Goto → 20초 → Off | 승인 문면 = 송신 2줄 · executed/command 2 |
| ③ `d1rev_live` | 사전 POSZ `1.2000000476837` → 사후 POSZ `6.1999998092651` · ROT 0 | 승인 문면 = 송신 1줄 · executed/command 1 |

- 실행 전에는 매번 `lsof -iUDP:9005`로 응답기 포트를 확인했다. 쥔 프로세스는 `app_gma3`(PID 60211)뿐이었다. SaveShow 0이다.
- 감독 관찰(원문, 리드 경유): 「201,301 모두 켜져」
- ~~판정: 원인은 높이(6.2 m)다.~~ → **정정(2026-10-07, 아래)**

> **정정 2026-10-07 — 리드 전달 오류.** 감독 원문(리드 경유, 정정 메시지): 「이전에도 켜졌어. 다만 역광방향으로 비춰지지 않았다는거야」.
> BACK은 6.2 m에서도 **켜져 있었다.** 카드의 문제 서술(「무대 화면에서 안 보임」, t516 §4-14 「F1·F2 모두 안 보였다」)은 리드가 감독 관찰을 잘못 옮긴 것이다. 실제 문제는 점등이 아니라 **방향**이다. 빔이 수직 아래로만 떨어져서, 무대 뒤에서 객석 쪽으로 비추는 역광 방향이 아니었다.
> 그래서 높이 시험은 다음처럼 다시 읽는다. **「1.2 m에서도 켜짐 = 점등 문제가 아님」.** 이 시험은 원인을 가르지 못했다. 가를 문제가 처음부터 없었다. 「원인 = 높이」 판정과 §2의 H1·H2는 철회한다. 판독(§1)은 사실로 남는다. 패치 회전 0이라 빔이 수직 아래를 향한다는 것이 감독이 본 「역광 방향이 아님」과 맞는다.
> 감독 결정: **A — 객석 쪽으로 기울인다(Tilt).** §7 참조.

- 201은 원래 높이 6.2로 돌아왔다. 콘솔에 남은 변경은 없다.

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

## 7. 감독 결정 A — 객석 쪽으로 기울이기 (승인 요청, 실행 신호 대기)

### 7-1. 방향 판독 (읽기 전용)

- 객석은 −Y 쪽이다. FOH 111~118은 Y −6.5, KEY 101~106은 Y −9.0이고, BACK 201~212는 Y +4.5에 높이 6.2다(t516 `diag7_patch.txt`). 바닥은 ±15 m다.
- 유형 8(Mac Aura XB) `Extended - Extended` 채널(`r11_type8_channels.txt`, `r13_pantilt_range.txt`):
  - `Yoke_Main Module_Pan`: 물리 270 → −270°, 기본값은 DMX 가운데(0°)
  - `Main Module_Tilt`: 물리 −116 → 116°, 기본값은 가운데(0°)
  - `Main Module_Zoom`: 53 → 11°, 기본값은 가운데(약 32°, 추론)
- 회전 0, Pan 0, Tilt 0이면 빔은 수직 아래로 떨어진다. 감독이 본 「역광 방향이 아님」과 맞는다.
- 방향 모델은 `.claude/skills/ma3-spatial-pointing` §1을 따른다(2026-08-13, **다른 리그 RLB350M1에서 실측**).
  - Tilt를 +로 주면 빔이 +Y(무대 뒤) 쪽으로 기운다.
  - Pan 180이 객석 방향이다(FAN 기본 base).
  - 그래서 **Pan 180에 Tilt t를 주면 빔이 −Y(객석) 쪽으로 숙는다.**
  - 🔴 Aura XB에서 이 부호를 잰 적은 없다. 빔이 무대 뒤로 가면 부호가 반대라는 뜻이고, 그때는 다음 판을 Pan 0으로 바꾼다.

### 7-2. 후보 3개 (201 한 대, 새 번호 260~262)

| Seq | Tilt | 바닥 착지(계산) | 이름 |
|---|---|---|---|
| 260 | 30 | Y 0.9 — 무대 가운데 | `BACK AIM PROBE - PAN 180 TILT 30` |
| 261 | 45 | Y −1.7 — 무대 앞쪽 | `BACK AIM PROBE - PAN 180 TILT 45` |
| 262 | 60 | Y −6.2 — 객석(FOH 줄) | `BACK AIM PROBE - PAN 180 TILT 60` |

- 큐마다 들어가는 줄: `Fixture 201 ; Attribute 'Dimmer' At 100 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At <t>` + `Fixture 201.1 ; Attribute 'Dimmer' At 100`. 248(v5 F1)과 같은 꼴에 Pan/Tilt만 더했다.
- 재생: 각 시퀀스를 8초 켜고 끈 뒤 2초 쉰다. 순서는 260 → 261 → 262.
- 승인 파일 `approval_back_aim.txt`: 27줄, sha256 `ae9bff36243288462ab3c8e8ecfc8667670f8b0d02dca162887f13ecbb07a4bf`. 묶음 9개(저장 3, 재생 6)다.
- 리허설(`aim_rehearse`): exit 0, 9묶음 모두 진행.
- 실기 전부-거절(`aim_denyall`):
  - 사전 판독에서 Sequence 260·261·262 모두 `path segment not found`가 나왔다. 빈 번호라는 뜻이다.
  - 감사 로그는 `rejected/t519_back_aim 9`이고, executed command는 0이다.
  - 요청 문면이 리허설과 같다(27줄 `live==rehearse True`).
- 쇼 저장은 없다. 기존 번호 덮어쓰기·삭제도 없다. 패치는 바꾸지 않는다.
- 실행(리드 「실행」 뒤에만): `uv run python .moai/reports/t519/back_aim.py .moai/reports/t519/aim_live --approve .moai/reports/t519/aim_denyall`
- 감독이 고른 각도는 lane-2 t520의 SCENE 시퀀스에 넣는다(리드 배차).
- 남는 것: Sequence 260~262(`BACK AIM PROBE - …`). 지울지는 리드·감독이 정한다.

### 7-3. 실기 실행 (리드 「실행」, 2026-10-07)

- 실행 전 확인: sha256 `ae9bff36…`가 일치했고, 응답기 포트를 쥔 프로세스는 `app_gma3`뿐이었다.
- `aim_live`: exit 0. 9묶음이 모두 진행됐다(store 3, Goto/Off 6).
- 승인 = 송신 대조: `uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t519/approval_back_aim.txt .moai/reports/t519/aim_live/audit` 결과는 송신 27줄, sha256 같음, 송신 안 됨 0, 승인 안 됨 0, not-ok 0으로 **PASS**다(`aim_live_approval_vs_sent.txt`). SaveShow 0.
- 콘솔에 남은 것: Sequence 260·261·262(`BACK AIM PROBE - PAN 180 TILT 30/45/60`).
- 감독 관찰: 대기 중이다(리드 경유).

### 7-4. 감독 관찰과 결정값

- 감독 관찰(원문, 리드 경유): 「80도 정도는 되어야겠어」
- 판독:
  - 30/45/60은 모두 부족했다.
  - 방향(Pan 180 = 객석 쪽)은 맞는 것으로 읽는다. 다만 **부호 확인은 감독 관찰로 간접 확인한 것**이다. 감독이 반대 방향을 지적하지 않았다는 데서 낸 판단이고, 기계로 잰 것은 아니다.
- **결정값: BACK Pan 180 · Tilt 80.** 리드가 lane-2 t520 SCENE에 넘겼다.
  - Tilt 80은 Aura XB 범위(±116) 안이다.
  - 계산상 바닥 착지는 Y ≈ 4.5 − 6.2·tan80 ≈ −30.7로, 바닥(±15) 밖이다. 빔이 객석 위 공중으로 뻗는다(추론, 감독이 3D에서 본다).
- 80도는 이 시험에서 재생해 본 각도가 아니다. t520이 처음 넣는 값이다.
- 잔류: Sequence 260·261·262(`BACK AIM PROBE - PAN 180 TILT 30/45/60`). 지울지는 리드·감독이 정한다. 쇼에 저장됐는지는 이 레인이 모른다(SaveShow 송신 0).
