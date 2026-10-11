# t553 Part ② — 실기 승인 목록 (8트랙 재측정 + MOVER-U 기운 기준 Pan)

두 전부-거절(2026-10-11)에서 나온 승인 문면 그대로다. `--approve .moai/reports/t553/denyall_8track`(P1b)와 `--approve .moai/reports/t553/denyall_u_pan`(추가 묶음)은 각각의 문면과 **글자까지 같은** 묶음만 승인한다(t506 RecordingApproval).

합계: 묶음 10 · 줄 46
approval_t553.txt sha256: cc7f58817254a0d1d9bcfb71357f7826af8ea71571169ea19b8b98e8c556902e
approval_t553.txt 줄 수: 46

## P1b — 8트랙 타임코드 재측정 (TC 32, 시퀀스 226~233 참조) — 묶음 4 · 줄 22
1. `Store Timecode 32` / `Set Timecode 32 Property 'Name' 'LDBEAT T553 - P1b eight tracks'` / `Set Timecode 32 Property 'Duration' 10 'AutoStop' 0` / `Store Timecode 32.1`
2. `Assign Sequence 226 At Timecode 32.1.1` / `Assign Sequence 227 At Timecode 32.1.2` / `Assign Sequence 228 At Timecode 32.1.3` / `Assign Sequence 229 At Timecode 32.1.4` / `Assign Sequence 230 At Timecode 32.1.5` / `Assign Sequence 231 At Timecode 32.1.6` / `Assign Sequence 232 At Timecode 32.1.7` / `Assign Sequence 233 At Timecode 32.1.8`
3. `Go Timecode 32`
4. `Off Timecode 32` / `Off Sequence 226` / `Off Sequence 227` / `Off Sequence 228` / `Off Sequence 229` / `Off Sequence 230` / `Off Sequence 231` / `Off Sequence 232` / `Off Sequence 233`

## 추가 — MOVER-U(Group 11) 기운 기준 Pan 물결 재시험 (시퀀스 336, 새) — 묶음 6 · 줄 24
1. `ChangeDestination Root` / `ClearAll` / `Group 11 ; Attribute 'Dimmer' At 70` / `Group 11 ; Attribute 'Tilt' At 45`
2. `ClearAll`
3. `ChangeDestination Root` / `ClearAll` / `Group 11 ; Attribute 'Dimmer' At 70` / `Group 11 ; Attribute 'Tilt' At 45` / `Group 11 ; Attribute 'Pan' At Relative -30` / `Step 2` / `Attribute 'Pan' At Relative 30` / `Step 1 At Accel -100` / `Step 1 At Decel -100` / `Step 2 At Accel -100` / `Step 2 At Decel -100` / `Attribute 'Pan' At Phase 0 Thru 360` / `Attribute 'Pan' At Speed 56` / `Store Sequence 336 Cue 1 'T553 - MOVERU pan wave 2 beats tilted base'` / `ClearAll` / `Set Sequence 336 Property 'Name' 'T553 - MOVERU pan wave 2 beats tilted base'`
4. `Goto Cue 1 Sequence 336`
5. `Off Sequence 336`
6. `ClearAll`
