# t531 M1 v3 재승인 묶음

전부 실기 전부-거절(쓰기 0)에서 나온 승인 문면 그대로다. 이 문면과 **글자까지 같은** 묶음만 실행된다.

합계: 수정 줄 10 · 추가 줄 28

## 1. 수정 — 이전 → 새

### ③ 프리셋 수정 전파 — 묶음 4 · 줄 21
- 묶음 1 줄 4: `Attribute 'Color' At Preset 4.9` → `At Preset 4.9`
- 묶음 1 줄 5: `Store Preset 4.301` → `Store Preset 4.302`
- 묶음 1 줄 6: `Set Preset 4.301 Property 'Name' 'LDBEAT M1 - P3 propagation'` → `Set Preset 4.302 Property 'Name' 'LDBEAT M1 - P3 propagation'`
- 묶음 2 줄 4: `Attribute 'Color' At Preset 4.301` → `At Preset 4.302`
- 묶음 3 줄 4: `Attribute 'Color' At Preset 4.5` → `At Preset 4.5`
- 묶음 3 줄 5: `Store Preset 4.301 /Merge` → `Store Preset 4.302 /Merge`

### ⑤ 위치 프리셋 위 상대값 — 묶음 3 · 줄 15
- 묶음 1 줄 4: `Attribute 'Position' At Preset 2.1` → `At Preset 2.1`

### ⑨ circle·발리후·wave — 묶음 5 · 줄 44
- 묶음 1 줄 4: `Attribute 'Position' At Preset 2.1` → `At Preset 2.1`
- 묶음 2 줄 4: `Attribute 'Position' At Preset 2.1` → `At Preset 2.1`
- 묶음 3 줄 4: `Attribute 'Position' At Preset 2.1` → `At Preset 2.1`

## 2. 추가 — 전문

### ⑩ 디머 번갈아 — 위상 펼침 (새 시퀀스 309) — 묶음 3 · 줄 12

- 감독 눈: MOVER-U 가 다 같이 / 물결 / 한 대씩 번갈아 중 무엇인가
- ⑦ 큐1 과 다른 줄은 `Attribute 'Dimmer' At Phase 0 Thru 180` 하나. 문법 근거: `0 Thru 360` 은 t227 에서 콘솔이 받음(`t227/verdict.md:98`). 🔴 끝값 180 과 눈 결과는 미측정.

1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Dimmer' At 0` / `Step 2` / `Attribute 'Dimmer' At 100` / `Attribute 'Dimmer' At Phase 0 Thru 180` / `Store Sequence 309 Cue 1 'LDBEAT M1 - P10 dimmer phase spread'` / `Set Sequence 309 Property 'Name' 'LDBEAT M1 - P10 dimmer phase spread'` / `ClearAll`
2. `Goto Cue 1 Sequence 309`
3. `Off Sequence 309`

### ⑪ t520 실패 재현 — Step 2 한 번 뒤 선택 바꾸기 (새 시퀀스 310) — 묶음 3 · 줄 16

- 감독 눈: MOVER-U 와 바닥 워시가 둘 다 깜빡이나
- ⑦ 큐2 와 다른 것은 `Step 2` 위치 하나(t520 승인 문면 `approval_m2a_batch1_v2.txt:178-209` 꼴). 그룹·속성·값은 같다.

1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Dimmer' At 0` / `Group 10` / `Attribute 'Dimmer' At 0` / `Step 2` / `Group 11` / `Attribute 'Dimmer' At 100` / `Group 10` / `Attribute 'Dimmer' At 100` / `Store Sequence 310 Cue 1 'LDBEAT M1 - P11 t520 step order'` / `Set Sequence 310 Property 'Name' 'LDBEAT M1 - P11 t520 step order'` / `ClearAll`
2. `Goto Cue 1 Sequence 310`
3. `Off Sequence 310`
