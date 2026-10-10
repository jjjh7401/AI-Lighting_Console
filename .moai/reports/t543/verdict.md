# t543 판정서 — SPEC-LDBEAT-001 데이터 채우기 (LOVE ATTACK 0~25마디)

- 카드: t543 · 레인: lane-3 · 브랜치 `WT-ldbeat-data-fill` (기준 `651b7d2c`)
- 날짜: 2026-10-10 · 콘솔: grandMA3 onPC, 응답기 **1.6.6**(ping 실측) · **콘솔 쓰기 0**(ping·state·introspect·props 만 보냄)

## 한눈에

| 단계 | 결과 | 근거 |
|---|---|---|
| ① 콘솔 목록 | **다 읽었다** — 프리셋 풀 14개, 그룹 18개, 개수 모두 콘솔 childCount 와 일치 | `r1_pools.json` |
| ① 그룹 소속 | **18개 그룹 전량** 읽었다 — 1.6.6 나눠 읽기로 잘림 없이, 소속 장비가 이름과 전부 일치 | `r2_group_members.jsonl` · `r4_group_fids.txt` |
| ② 트랙 추가 | **FOH(G3)·WASH-ALL(G10)** 을 데이터 파일에만 추가. 코드 상수 0줄 | `server/design/beat_grid_data/love_attack.yaml` |
| ③ 기입표 | **큐 31개 × 프리셋 4칸, 전부 빈칸** + 풀 목록 후보 + 메모 6개 | `fill-in-table.md` |
| ④ 색 막대 | **막힘(실측)** — 색 프리셋 필드 135개를 읽었는데 색 값이 담긴 칸이 없다. 빗금 유지 | `r5_color_values.json` |

## ① 콘솔 읽기 전용 목록

명령: `.venv/bin/python .moai/reports/t543/probe_pools.py > r1_pools.json` (state 를 offset 으로 끝까지)

| 풀 | 개수 | 내용 |
|---|---|---|
| 1 Dimmer | 7 | 1.1 풀 · 1.2 쇼 하이 OLD · 1.3 미드 · 1.4 로우 · 1.5 잔광 · 1.6 아웃 · 1.7 쇼 하이 |
| 2 Position | 16 | 2.1~2.6 POS01~06(합성좌표) · 2.21~2.30 Home·Wall·Audience·Center·Vocal DSC·Fan Out·Fan In·Cross·Ring Out·Ring In |
| 4 Color | 13 | 4.1~4.8 골드 앰버·핫 핑크·딥 퍼플·터쿼이즈·선셋 오렌지·딥 블루·웜 화이트·뉴트럴 화이트 · 4.9 Breathe Warm · 4.10 Wave CM · 4.32 · 4.301·4.302(t531 프로브 잔여) |
| 21 All 1 (효과) | 8 | 21.1 DIM-PULSE · 21.2 PT-CIRCLE · 21.3 DIM-CHASE · 21.4 DIM-BREATHE · 21.5 TILT-SWEEP · 21.6 DIM-TWINKLE · 21.7 Finale Slam · 21.301(t531 프로브 잔여) |
| 22 All 2 | 1 | 22.1 Piano Solo |
| 3·5·6·7·8·9·23·24·25 | 0 | 비어 있음 |

그룹 풀(18): 1 ALL · 2 KEY · **3 FOH** · 4 BACK · 5 SIDE-L · 6 SIDE-R · 7 SIDE-ALL · **8 WASH-U · 9 WASH-D · 10 WASH-ALL** · 11 MOVER-U · 12 MOVER-D · 13 MOVER-ALL · 14 BLIND · **15 STROBE** · 16 HAZE · 17 ODD · 18 EVEN

### 그룹 소속 (SELECTIONDATA, t525 방식 + 1.6.6 나눠 읽기)

명령: `.venv/bin/python .moai/reports/t531/group_members.py 1 … 18 > r2_group_members.jsonl` → 패치 트리 재측정 `probe_patch_tree.py > r3_patch_tree.json`(t525 r4 와 **바이트 동일**, 패치 그대로) → `map_members.py > r4_group_fids.txt`

| 그룹 | 받은/전체 | fid |
|---|---|---|
| 3 FOH | 8/8 | 111~118 |
| 8 WASH-U | 10/10 | 401~410 |
| 9 WASH-D | 10/10 | 421~430 |
| 10 WASH-ALL | 20/20 | 401~410 · 421~430 |
| 15 STROBE | 4/4 | 611~614 |
| 1 ALL | 86/86 | 전 장비 |

18개 그룹 모두 `unknown=0`, 서브픽스처 칸 0. t525 가 「앞 2대만」이라 했던 한계는 응답기 1.6.6 에서 풀렸다(t525 이후 응답기가 바뀜, 실기 ping 1.6.6).

## ② 데이터 파일에 FOH·WASH-ALL 트랙 추가

- 그룹 번호·이름은 `love_attack.yaml` 에만 있다. `server/design/beat_grid.py` 는 바꾸지 않았다(감독 원칙: 다른 장비·디자인에서도 동작).
- 트랙 순서는 시안 ROLES 순서 그대로: FOH → WASH-ALL → BACK → SIDE-ALL → MOVER-U → MOVER-D → BLIND → STROBE. 층 역할은 공용 판정기가 FOH=`key`, WASH-ALL=`wash` 로 붙였다(실행 결과).
- 워시 줄은 WASH-U·WASH-D 를 함께 잡는 **WASH-ALL 하나**로 뒀다. 둘을 따로 두면 겹침 검증(`find_overlapping_group_tracks`)이 WASH-ALL 과 동시에 쓰는 것을 막는다.
- **SCENE 칸 옮기기는 기존 「세 조건」 규칙을 그대로 적용했다.**
  - bar 7 「FOH 켬」 → FOH 트랙 큐로 옮김(FOH 를 글자 그대로 부름 · 번호 확인 · 빈 자리). 밝기 숫자는 §4 에 없어 비움.
  - bar 7 「라벤더 워시 40%(2마디 번짐)」, bar 14 「워시 25% 덜어냄」 → **메모로 남김.** 칸은 「워시」라고 부르는데 트랙 이름은 `WASH-ALL` 이다. 기존 시험도 이 칸을 `"WASH"` 로 다뤄 바이트 일치로만 판정한다. 「워시 = WASH-ALL」로 넓혀 읽는 건 레인이 정하지 않는다 → **리드 결정 1**.
- 시험: `server/tests/test_beat_grid_t532.py`·`test_beat_grid_t537.py` 의 고정값을 새 데이터에 맞췄다(트랙 6→8, 큐 30→31, FOH/WASH-ALL 번호·역할 단언 추가, 순서에 기댄 `tracks[0]` 은 이름 조회로).

```
$ .venv/bin/python -m pytest server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_probes_t537.py -q
58 passed
$ .venv/bin/python -m pytest server/tests -q -k "beat_grid or runbook or ldbeat or timeline"
203 passed, 2 skipped
$ ruff check (변경 파일 + 이 폴더) → All checks passed!
```

데이터를 먼저 바꾼 뒤 같은 시험을 돌리면 10개가 실패했다(트랙 이름 목록·개수·`tracks[0]`=BACK 가정·메모 bar 집합). 고친 뒤 58개 통과.

## ③ 기입표 — 리드에 넘김

`fill-in-table.md` (생성: `make_fill_table.py`, 앱 로더가 돌려주는 실제 격자에서 뽑음 — 손 전사 없음)

- 큐 31개마다 마디·트랙(그룹 번호)·§4 원문·지금 값(§4 에 숫자가 있던 % 만) + 빈 기입 칸 4개(밝기 프리셋 / 위치 / 색 / 효과).
- 후보는 풀 목록 전체를 그대로 붙였다. 레인이 고른 번호 0개.
- 트랙에 못 얹은 SCENE 메모 6개와 그 이유도 같이 실었다.

## ④ 색 막대 `colorPresetHex` — 막힘

명령: `.venv/bin/python .moai/reports/t543/probe_color_values.py > r5_color_values.json` (색 프리셋 4.1·4.2, introspect 전량 + props)

- 필드 138개, 읽기 135개 중 성공 117 · 실패 18(`APPEARANCE` 포함).
- 데이터는 **있다**: `OWNDATAPRESENT=true`, `MEMORYFOOTPRINT=2376`, `FEATUREGROUP=Color`.
- 그런데 값이 들어 있을 칸은 **비어 있다**: `PRESETDATA=""`, `SELECTIONDATA={}`, 자식 노드 0개. 비어 있지 않은 23개 필드 중 색 값(RGB·HSB 등)은 0개.
- t538 r27 은 위치 프리셋만 쟀다. 이번에 색 풀을 직접 재서 같은 결과를 확인했다.
- 따라서 이름(「골드 앰버」 등)으로 색을 추정하지 않았다. 막대는 빗금 그대로이고 `ui/` 는 손대지 않았다.
- 길: 응답기가 프리셋의 채널 값을 내주는 새 읽기(코드 카드) 또는 감독이 색을 직접 적기.

## 리드 결정할 것

1. **「워시」= WASH-ALL 로 볼지.** 보면 bar 7(40%, 2마디 번짐)·bar 14(25%)를 WASH-ALL 큐로 옮긴다 — 데이터 파일과 `classify` 시험 몇 줄만 바꾸면 된다. 지금은 메모로 둠.
2. **STROBE 그룹 번호.** 콘솔 실측으로 **15**(611~614)가 확인됐다. 데이터 파일엔 아직 `null` 이다 — 이 카드 범위(WASH·FOH) 밖이라 넣지 않았다.
3. ③ 기입표를 감독께 어떤 형식으로 드릴지(지금은 markdown).

## 안 잰 것

- 프리셋 **내용**(어느 장비에 어떤 값). 이름만 읽었다. 이름이 실제 모양·색과 다를 수 있다(t538: `21.2 PT-CIRCLE` 은 원이 아님).
- 색 프리셋은 4.1·4.2 두 개만 필드를 훑었다. 나머지 11개도 같은 모양일 것으로 보이지만 재지 않았다.
- 화면(`ui/`)에서 새 트랙 두 줄이 어떻게 보이는지 — 브라우저로 열어 보지 않았다. 화면 시험(`BeatGrid.test.tsx`)은 자체 가짜 데이터라 이 변경과 무관하고, 돌리지 않았다.
- 전체 시험은 돌리지 않았다(관련 묶음 203개만). 전체는 CI 에 맡긴다.
- 그룹 16 HAZE 의 `total` 은 응답에 없었다(받은 2개로 끝, 잘림 표시 없음).

## 부산물 (콘솔에 남은 것)

없음 — 이 카드는 콘솔에 아무것도 쓰지 않았다.

## 파일

| 파일 | 내용 |
|---|---|
| `probe_pools.py` · `r1_pools.json` | 프리셋 풀·그룹 풀 목록 |
| `r2_group_members.jsonl` | 그룹 18개 SELECTIONDATA 전량(t531 `group_members.py` 실행) |
| `r3_patch_tree.json` | 패치 트리 재측정(t525 `probe_patch_tree.py` 실행) |
| `map_members.py` · `r4_group_fids.txt` | sf_index → fid 대응표 |
| `make_fill_table.py` · `fill-in-table.md` | ③ 기입표 |
| `probe_color_values.py` · `r5_color_values.json` | ④ 색 프리셋 필드 실측 |
