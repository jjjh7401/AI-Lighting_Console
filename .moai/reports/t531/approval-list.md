# t531 M1 — 실기 승인 목록

전부-거절(2026-10-10 15:26)에서 나온 승인 문면 그대로다. `--approve .moai/reports/t531/denyall/p<n>` 은
이 문면과 **글자까지 같은** 묶음만 승인한다(t506 RecordingApproval).

합계: 묶음 36 · 줄 181

첫 낱말별 줄 수: 34 Attribute, 27 ClearAll, 23 Off, 19 Store, 14 Set, 14 Group, 13 Goto, 13 ChangeDestination, 8 At, 7 Assign, 4 Step, 2 Go, 2 cd, 1 Label

## P1 ① 타임코드 트랙 6개 — 묶음 4 · 줄 18
1. `Store Timecode 30` / `Set Timecode 30 Property 'Name' 'LDBEAT M1 - P1 six tracks'` / `Set Timecode 30 Property 'Duration' 10 'AutoStop' 0` / `Store Timecode 30.1`
2. `Assign Sequence 228 At Timecode 30.1.1` / `Assign Sequence 229 At Timecode 30.1.2` / `Assign Sequence 230 At Timecode 30.1.3` / `Assign Sequence 231 At Timecode 30.1.4` / `Assign Sequence 232 At Timecode 30.1.5` / `Assign Sequence 233 At Timecode 30.1.6`
3. `Go Timecode 30`
4. `Off Timecode 30` / `Off Sequence 228` / `Off Sequence 229` / `Off Sequence 230` / `Off Sequence 231` / `Off Sequence 232` / `Off Sequence 233`

## P2 ② Goto 2번 이후·여러 시퀀스 — 묶음 2 · 줄 6
1. `Goto Cue 3 Sequence 221` / `Goto Cue 3 Sequence 226` / `Goto Cue 1 Sequence 11`
2. `Off Sequence 221` / `Off Sequence 226` / `Off Sequence 11`

## P3 ③ 프리셋 수정 전파 — 묶음 4 · 줄 21
1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 4.9` / `Store Preset 4.302` / `Set Preset 4.302 Property 'Name' 'LDBEAT M1 - P3 propagation'` / `ClearAll`
2. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 4.302` / `Store Sequence 300 Cue 1 'LDBEAT M1 - P3 ref cue'` / `Set Sequence 300 Property 'Name' 'LDBEAT M1 - P3 preset propagation'` / `ClearAll`
3. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 4.5` / `Store Preset 4.302 /Merge` / `ClearAll`
4. `ClearAll`

## P4 ④ 효과 프리셋 SM15·Measure — 묶음 4 · 줄 20
1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Dimmer' At 0` / `Step 2` / `Attribute 'Dimmer' At 100` / `Attribute 'Dimmer' At Measure 1` / `Attribute 'Dimmer' At SpeedMaster 15` / `Store Preset 21.301 'LDBEAT M1 - P4 SM15 MEASURE' /Universal` / `Label Preset 21.301 'LDBEAT M1 - P4 SM15 MEASURE'` / `ClearAll`
2. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 21.301` / `Store Sequence 301 Cue 1 'LDBEAT M1 - P4 recall'` / `Set Sequence 301 Property 'Name' 'LDBEAT M1 - P4 recall SM15 measure'` / `ClearAll`
3. `Goto Cue 1 Sequence 301`
4. `Off Sequence 301`

## P5 ⑤ 위치 프리셋 위 상대값 — 묶음 3 · 줄 15
1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 2.1` / `Attribute 'Pan' At Relative 12` / `Attribute 'Tilt' At Relative 8` / `Attribute 'Pan' At Phase 0` / `Attribute 'Tilt' At Phase 90` / `Attribute 'Pan' At Speed 60` / `Attribute 'Tilt' At Speed 60` / `Store Sequence 302 Cue 1 'LDBEAT M1 - P5 relative-on-preset'` / `Set Sequence 302 Property 'Name' 'LDBEAT M1 - P5 relative-on-preset'` / `ClearAll`
2. `Goto Cue 1 Sequence 302`
3. `Off Sequence 302`

## P6 ⑥ 타임코드 중간 재생 — 묶음 4 · 줄 13
1. `Store Timecode 31` / `Set Timecode 31 Property 'Name' 'LDBEAT M1 - P6 mid-start'` / `Set Timecode 31 Property 'Duration' 10 'AutoStop' 0` / `Store Timecode 31.1` / `Assign Sequence 228 At Timecode 31.1.1` / `Store Type 'CmdSubTrack' Timecode 31.1.1.1` / `cd Timecode 31.1.1.1.1` / `Store Property 'Time' 5 'AbsTime' 5 'Token' 'Go+'` / `cd root`
2. `Goto Time 5 Timecode 31`
3. `Go Timecode 31`
4. `Off Timecode 31` / `Off Sequence 228`

## P7 ⑦ 선택 하나 + Step 2 (대조 큐 포함) — 묶음 6 · 줄 25
1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Dimmer' At 0` / `Step 2` / `Attribute 'Dimmer' At 100` / `Store Sequence 303 Cue 1 'LDBEAT M1 - P7 cue1 single-selection step2'` / `ClearAll`
2. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Dimmer' At 0` / `Step 2` / `Attribute 'Dimmer' At 100` / `Group 10` / `Attribute 'Dimmer' At 0` / `Step 2` / `Attribute 'Dimmer' At 100` / `Store Sequence 303 Cue 2 'LDBEAT M1 - P7 cue2 two-selections step2'` / `Set Sequence 303 Property 'Name' 'LDBEAT M1 - P7 single-vs-double'` / `ClearAll`
3. `Goto Cue 1 Sequence 303`
4. `Off Sequence 303`
5. `Goto Cue 2 Sequence 303`
6. `Off Sequence 303`

## P8 ⑧ 같은 그룹 두 시퀀스 — 묶음 4 · 줄 19
1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Dimmer' At 100` / `Store Sequence 304 Cue 1 'LDBEAT M1 - P8 dimmer-only'` / `Set Sequence 304 Property 'Name' 'LDBEAT M1 - P8 dimmer'` / `ClearAll`
2. `ChangeDestination Root` / `ClearAll` / `Group 11` / `Attribute 'Pan' At Relative 10` / `Attribute 'Tilt' At Relative 10` / `Store Sequence 305 Cue 1 'LDBEAT M1 - P8 pantilt-only'` / `Set Sequence 305 Property 'Name' 'LDBEAT M1 - P8 pantilt'` / `ClearAll`
3. `Goto Cue 1 Sequence 304` / `Goto Cue 1 Sequence 305`
4. `Off Sequence 304` / `Off Sequence 305`

## P9 ⑨ circle·발리후·wave — 묶음 5 · 줄 44
1. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 2.1` / `Attribute 'Pan' At Relative 12` / `Attribute 'Tilt' At Relative 8` / `Attribute 'Pan' At Phase 0` / `Attribute 'Tilt' At Phase 90` / `Attribute 'Pan' At Speed 60` / `Attribute 'Tilt' At Speed 60` / `Store Sequence 306 Cue 1 'LDBEAT M1 - P9 circle'` / `Set Sequence 306 Property 'Name' 'LDBEAT M1 - P9 circle'` / `ClearAll`
2. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 2.1` / `Attribute 'Pan' At Relative 20` / `Attribute 'Tilt' At Relative 10` / `Attribute 'Pan' At Phase 0` / `Attribute 'Tilt' At Phase 90` / `Attribute 'Pan' At Speed 120` / `Attribute 'Tilt' At Speed 120` / `Store Sequence 307 Cue 1 'LDBEAT M1 - P9 ballyhoo'` / `Set Sequence 307 Property 'Name' 'LDBEAT M1 - P9 ballyhoo'` / `ClearAll`
3. `ChangeDestination Root` / `ClearAll` / `Group 11` / `At Preset 2.1` / `Attribute 'Tilt' At Relative 12` / `Attribute 'Tilt' At Phase 0 Thru 360` / `Attribute 'Tilt' At Speed 60` / `Store Sequence 308 Cue 1 'LDBEAT M1 - P9 wave'` / `Set Sequence 308 Property 'Name' 'LDBEAT M1 - P9 wave'` / `ClearAll`
4. `Goto Cue 1 Sequence 306` / `Off Sequence 306` / `Goto Cue 1 Sequence 307` / `Off Sequence 307` / `Goto Cue 1 Sequence 308`
5. `Off Sequence 306` / `Off Sequence 307` / `Off Sequence 308`
