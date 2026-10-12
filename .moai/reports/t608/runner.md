# t608 — 고정 승인 실행기 (fixed-approval runner)

- 카드: `t608`. 브랜치: `WT-beatgrid-runner`
- 모듈: `server/tools/beatgrid_runner.py`. 시험: `server/tests/test_beatgrid_runner.py`
- 입력 기준: `.moai/reports/t608/payload-all.txt` (주 체크아웃의 추적되지 않은 파일), sha256 `9ca962e47fab66e8e95dc7ce447c2fcec013a4f8e1161d711e53d6329c7faeea`, 184줄
- 이 카드에서 콘솔에 접속하지 않았다. 시험은 가짜 콘솔만 썼고, dry-run 은 파일만 읽었다. 게이트 판정 확인도 가짜 콘솔 안에서만 했다. 실제 콘솔 실행은 리드가 한다.

## 1. 설계

- **송신 경로**: 앱의 기본 조립 `build_console_stack` → `SafetyGate.screen(줄 전체, risk=BatchRisk)` → 줄마다 `gate.execution_port.execute(줄)`. 실제 전송 클라이언트는 앱의 `ConsoleLink` 다. 처음에는 `ConsoleLink` 와 OSC 브리지를 직접 조립했는데, 단일 게이트 경계 검사(REQ-MVP-029, AC-MVP-019, AC-DEPLOY-014)가 그 설계를 막았다. 그래서 게이트 경로로 바꿨다.
- **승인**: `PinnedPayloadApproval`. 게이트는 번들 승인을 한 번 요청하고, 요청된 명령이 고정된 줄과 정확히 같을 때만 승인한다. 입력 sha256 검사를 통과한 뒤에만 이 포트를 만든다.
- **중단 규칙**: 줄의 결과가 `ok` 가 아니면 멈춘다. 그 뒤의 줄은 보내지 않는다. 재시도는 없다.
- **기록**: 줄마다 JSONL 한 줄(`index`, `line`, `sent_at`, `responded_at`, `status`, `detail`). 시작·게이트 판정·끝 레코드도 남긴다. 로그는 새 파일만 쓴다. 기존 파일은 덮어쓰지 않고 거절한다.
- **읽기 전용 점검(`--probe`)**: 게이트의 감사되는 `heartbeat` 로 응답기를 확인하고, 게이트의 상태 포트로 읽는다. `screen` 과 `execution_port` 는 부르지 않는다. 쓰기 메서드가 없는 `ReadOnlyPort` 로 감싸고, 쓰기를 시도하면 `ProbeWriteRefused` 를 내고 종료 5 로 끝난다. 기동 시 세션 백업을 하지 않는다(`attempt_session_backup=False`).
- **입력 검사**: sha256 이 `--expect-sha256` 과 다르면 종료 4 로 거절한다. 포트도 로그도 만들지 않는다. 빈 줄이나 CR 이 있어도 거절한다.

## 2. 사용법

```
# 줄과 sha256 만 출력한다 (콘솔 접속 없음)
uv run python -m server.tools.beatgrid_runner --dry-run --input <payload> --expect-sha256 <sha256> --listen-port <응답포트>

# 읽기 전용 점검 (쓰기 0줄)
uv run python -m server.tools.beatgrid_runner --probe --host <onPC> --port <OSC입력포트> --listen-port <응답포트> --log <새파일.jsonl>

# 송신 (리드가 실행)
uv run python -m server.tools.beatgrid_runner --input <payload> --expect-sha256 <sha256> --host <onPC> --port <OSC입력포트> --listen-port <응답포트> --log <새파일.jsonl> [--wait 5]
```

| 옵션 | 뜻 |
|---|---|
| `--input` | 송신할 입력 파일 (송신, dry-run) |
| `--expect-sha256` | 승인된 sha256, 64자 16진수 (송신, dry-run) |
| `--dry-run` | 검사 후 줄과 sha256 만 출력 |
| `--probe` | 읽기 전용 점검 |
| `--log` | 새 JSONL 파일 (송신은 필수, 점검은 선택) |
| `--host`, `--port` | onPC 주소와 OSC 입력 포트 (`--port` 기본 8000) |
| `--listen-port` | 응답 포트. 공용 도구 규칙에 따라 기본값 없이 필수다. dry-run 에서도 필수다 |
| `--wait` | 응답 대기 초 (기본 5) |

## 3. 종료 코드

| 코드 | 뜻 |
|---|---|
| 0 | 성공 |
| 1 | 실행 실패: 줄이 `ok` 가 아니어서 중단, 게이트 예외, 점검 판정이 확정되지 않음 |
| 2 | 인자 오류 (argparse) |
| 3 | 트리 가드 (`assert_same_tree`) |
| 4 | 송신 전 거절: sha256 불일치, 기대 해시 형식 오류, 입력 오류, 로그 파일이 이미 있음, 게이트가 번들을 거절함, 세션 백업 실패 |
| 5 | 읽기 전용 위반: 점검이 쓰기를 시도함 |

## 4. 송신 모드에서 콘솔에 일어나는 일 (리드 확인용)

- **기동 시 세션 백업**: 앱의 기본 절차대로 콘솔에 `SaveShow` 를 한 번 보낸다. 실패하면 송신 전에 거절한다(종료 4, `refused_session_backup`).
- **게이트 판정**: 번들 전체를 위험으로 선언하므로 승인 요청이 한 번 나간다. 승인되면 위험 실행 전 백업으로 `SaveShow` 를 한 번 더 보낸다.
- **줄 송신**: `gate.execution_port.execute` → 앱의 `ConsoleLink.execute`. 실행을 감싸서 결과를 확인한다.
- **감사**: 게이트의 감사 기록이 앱의 기본 감사 디렉터리에 남는다.

## 5. 입력 내용에 대한 관찰 (리드 확인용)

- **173–183줄은 삭제 명령이다**: `Delete Timecode 70 /NoConfirm`, `Delete Sequence 700`~`703 /NoConfirm`, `Delete Preset 2.351 / 4.351 / 4.352 / 22.98 / 22.97 / 22.0 /NoConfirm`. 송신하면 이 객체들이 콘솔에서 지워진다. 게이트는 승인된 번들의 일부로 이 줄들을 통과시킨다(§6).
- **덮어쓰기 저장**: 91, 96, 101, 106, 113, 123줄은 `/Overwrite` 로 시퀀스 700·701의 큐를 덮어쓴다. 점검의 점유 판독이 이 전제를 확인하는 용도다.

## 6. 게이트 판정 (가짜 콘솔 안에서만, 송신 없음)

가짜 콘솔은 읽기에 `path segment not found` 를 돌려주고, `execute` 가 호출되면 실패하도록 만들었다. 실제 `SafetyGate.screen(184줄, risk=BatchRisk(...))` 를 `PinnedPayloadApproval` 과 함께 실행한 결과:

```
lines: 184
cleared: True status: cleared
notice:
by_status: {'cleared': 184}
approval requests: 1
request covers pinned lines exactly: True
console calls: {}
not cleared count: 0
```

- 게이트는 184줄을 모두 통과시켰다.
- 승인 요청은 한 번이었고, 고정된 줄과 정확히 같았다.
- 콘솔 호출은 없었다. `execute` 도 없었다.

## 7. 시험과 점검 (실측 출력)

- `uv run pytest server/tests/test_beatgrid_runner.py -q -rs` → `25 passed in 0.32s`
- `uv run pytest server/tests/test_architecture.py::TestSingleChokepointImportBoundary server/tests/test_deploy_safety_invariants.py::TestAcDeploy014SingleGateArchitecture server/tests/test_deploy_safety_invariants.py::TestAcDeploy014OscSendSurfaceAllowlist server/tests/test_probe_port_discipline.py server/tests/test_responder_import_gate.py -q -rs` → `27 passed in 1.13s`
- `uv run ruff check server/tools/beatgrid_runner.py server/tests/test_beatgrid_runner.py` → `All checks passed!`
- `uv run ruff format --check server/tools/beatgrid_runner.py server/tests/test_beatgrid_runner.py` → `2 files already formatted`
- 전체 Python 스위트는 로컬에서 한 번 돌렸다가 중단하지 않고 끝까지 두었다. 결과: `3 failed, 15673 passed, 35 skipped in 261.55s`. 실패 3건은 모두 단일 게이트 경계 검사였다. 원인은 직접 OSC 를 쓰던 첫 설계였고, 게이트 경로로 바꾼 뒤 위의 검사 27건을 다시 돌려 통과를 확인했다. 전체 스위트는 리드 지시에 따라 CI 에 맡긴다.

## 8. dry-run 출력 (실측)

명령: `uv run python -m server.tools.beatgrid_runner --dry-run --input <주 체크아웃>/.moai/reports/t608/payload-all.txt --expect-sha256 9ca962e47fab66e8e95dc7ce447c2fcec013a4f8e1161d711e53d6329c7faeea --listen-port 9000`

```text
lines=184 sha256=9ca962e47fab66e8e95dc7ce447c2fcec013a4f8e1161d711e53d6329c7faeea
1	ChangeDestination Root
2	ClearAll
3	Group 4
4	Attribute 'Dimmer' At 100
5	Step 2
6	Attribute 'Dimmer' At 0
7	Attribute 'Dimmer' At Phase 0 Thru 360
8	Attribute 'Dimmer' At Speed 60
9	Store Preset 22.98 'SCR FX' /Universal
10	Label Preset 22.98 'SCR FX'
11	ClearAll
12	Fixture 521 ; Attribute 'Pan' At -65.6 ; Attribute 'Tilt' At 41.6
13	Fixture 522 ; Attribute 'Pan' At -57.5 ; Attribute 'Tilt' At 34.4
14	Fixture 523 ; Attribute 'Pan' At -43.3 ; Attribute 'Tilt' At 26.8
15	Fixture 524 ; Attribute 'Pan' At -17.5 ; Attribute 'Tilt' At 21.1
16	Fixture 525 ; Attribute 'Pan' At 17.5 ; Attribute 'Tilt' At 21.1
17	Fixture 526 ; Attribute 'Pan' At 43.3 ; Attribute 'Tilt' At 26.8
18	Fixture 527 ; Attribute 'Pan' At 57.5 ; Attribute 'Tilt' At 34.4
19	Fixture 528 ; Attribute 'Pan' At 65.6 ; Attribute 'Tilt' At 41.6
20	Store Preset 2.351
21	Label Preset 2.351 'SCR POS'
22	ClearAll
23	ClearAll
24	Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
25	Store Preset 4.351
26	Label Preset 4.351 'SCR COLOR'
27	ClearAll
28	Store Timecode 70
29	Set Timecode 70 Property 'Name' 'LDBEAT Timecode 70'
30	Store Sequence 700
31	Set Sequence 700 Property 'Name' 'LDBEAT FOH'
32	Group 3 ; Attribute 'Dimmer' At 20
33	Store Cue 1 Sequence 700
34	ClearAll
35	Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
36	Set Cue 1 Sequence 700 Property 'TrigTime' 2
37	Group 3 ; Attribute 'Dimmer' At 40
38	Store Cue 2 Sequence 700 CueFade 1
39	ClearAll
40	Set Cue 2 Sequence 700 Property 'TrigType' 'Time'
41	Set Cue 2 Sequence 700 Property 'TrigTime' 4
42	Group 3 ; Attribute 'Dimmer' At 60
43	Store Cue 3 Sequence 700
44	ClearAll
45	Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
46	Set Cue 3 Sequence 700 Property 'TrigTime' 7
47	Group 3 ; Attribute 'Dimmer' At 80
48	Store Cue 4 Sequence 700
49	ClearAll
50	Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
51	Set Cue 4 Sequence 700 Property 'TrigTime' 8
52	Block Sequence 700 Cue 4
53	Group 3 ; Attribute 'Dimmer' At 100
54	Store Cue 5 Sequence 700 CueFade 2 /CueOnly
55	ClearAll
56	Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
57	Set Cue 5 Sequence 700 Property 'TrigTime' 10
58	Assign Sequence 700 At Timecode 70
59	Store Sequence 701
60	Set Sequence 701 Property 'Name' 'LDBEAT BACK'
61	Group 4 ; Attribute 'Dimmer' At 30
62	Store Cue 1 Sequence 701
63	ClearAll
64	Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
65	Set Cue 1 Sequence 701 Property 'TrigTime' 2
66	Group 4 ; Attribute 'Dimmer' At 50
67	Store Cue 2 Sequence 701
68	ClearAll
69	Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
70	Set Cue 2 Sequence 701 Property 'TrigTime' 6
71	Assign Sequence 701 At Timecode 70
72	Store Sequence 702
73	Set Sequence 702 Property 'Name' 'LDBEAT MOVER-D'
74	Assign Sequence 702 At Timecode 70
75	Store Sequence 703
76	Set Sequence 703 Property 'Name' 'LDBEAT WASH-ALL'
77	Assign Sequence 703 At Timecode 70
78	Top Timecode 70
79	Go Timecode 70
80	Off Timecode 70
81	Goto Cue 2 Sequence 700
82	Goto Cue 1 Sequence 701
83	Goto Cue 4 Sequence 700
84	Goto Cue 2 Sequence 701
85	Off Sequence 700
86	Off Sequence 701
87	Off Sequence 702
88	Off Sequence 703
89	Set Sequence 700 Property 'Name' 'LDBEAT FOH'
90	Group 3 ; Attribute 'Dimmer' At 20
91	Store Cue 1 Sequence 700 /Overwrite
92	ClearAll
93	Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
94	Set Cue 1 Sequence 700 Property 'TrigTime' 2
95	Group 3 ; Attribute 'Dimmer' At 65
96	Store Cue 3 Sequence 700 /Overwrite
97	ClearAll
98	Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
99	Set Cue 3 Sequence 700 Property 'TrigTime' 7
100	Group 3 ; Attribute 'Dimmer' At 80
101	Store Cue 4 Sequence 700 /Overwrite
102	ClearAll
103	Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
104	Set Cue 4 Sequence 700 Property 'TrigTime' 8
105	Group 3 ; Attribute 'Dimmer' At 100
106	Store Cue 5 Sequence 700 CueFade 2 /CueOnly /Overwrite
107	ClearAll
108	Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
109	Set Cue 5 Sequence 700 Property 'TrigTime' 10
110	Delete Cue 2 Sequence 700
111	Set Sequence 701 Property 'Name' 'LDBEAT BACK'
112	Group 4 ; Attribute 'Dimmer' At 30
113	Store Cue 1 Sequence 701 /Overwrite
114	ClearAll
115	Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
116	Set Cue 1 Sequence 701 Property 'TrigTime' 2
117	Group 4 ; Attribute 'Dimmer' At 40
118	Store Cue 3 Sequence 701
119	ClearAll
120	Set Cue 3 Sequence 701 Property 'TrigType' 'Time'
121	Set Cue 3 Sequence 701 Property 'TrigTime' 4
122	Group 4 ; Attribute 'Dimmer' At 50
123	Store Cue 2 Sequence 701 /Overwrite
124	ClearAll
125	Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
126	Set Cue 2 Sequence 701 Property 'TrigTime' 6
127	Set Sequence 702 Property 'Name' 'LDBEAT MOVER-D'
128	Group 12 ; At Preset 2.351
129	Store Cue 1 Sequence 702
130	ClearAll
131	Set Cue 1 Sequence 702 Property 'TrigType' 'Time'
132	Set Cue 1 Sequence 702 Property 'TrigTime' 2
133	Set Sequence 703 Property 'Name' 'LDBEAT WASH-ALL'
134	Group 10 ; At Preset 4.351
135	Store Cue 1 Sequence 703
136	ClearAll
137	Set Cue 1 Sequence 703 Property 'TrigType' 'Time'
138	Set Cue 1 Sequence 703 Property 'TrigTime' 2
139	Top Timecode 70
140	Go Timecode 70
141	Off Timecode 70
142	ChangeDestination Root
143	ClearAll
144	Group 4 + 3
145	Attribute 'Dimmer' At 100
146	Step 2
147	Attribute 'Dimmer' At 0
148	Attribute 'Dimmer' At Phase 0 Thru 360
149	Attribute 'Dimmer' At Speed 60
150	Store Preset 22.97 'SCR FX MULTI' /Universal
151	Label Preset 22.97 'SCR FX MULTI'
152	ClearAll
153	ClearAll
154	Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
155	Store Preset 4.352
156	Label Preset 4.352 'SCR DUP'
157	ClearAll
158	ClearAll
159	Group 10 ; Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 50
160	Store Preset 4.352
161	Label Preset 4.352 'SCR DUP'
162	ClearAll
163	ClearAll
164	Fixture 111 ; Attribute 'Dimmer' At 1
165	Store Preset 22.0
166	ClearAll
167	Off Timecode 70
168	Off Sequence 700
169	Off Sequence 701
170	Off Sequence 702
171	Off Sequence 703
172	ClearAll
173	Delete Timecode 70 /NoConfirm
174	Delete Sequence 700 /NoConfirm
175	Delete Sequence 701 /NoConfirm
176	Delete Sequence 702 /NoConfirm
177	Delete Sequence 703 /NoConfirm
178	Delete Preset 2.351 /NoConfirm
179	Delete Preset 4.351 /NoConfirm
180	Delete Preset 4.352 /NoConfirm
181	Delete Preset 22.98 /NoConfirm
182	Delete Preset 22.97 /NoConfirm
183	Delete Preset 22.0 /NoConfirm
184	ClearAll
```

잘못된 해시를 넣으면 송신 없이 거절한다 (`--expect-sha256 000…0`):

```
refused: sha256 mismatch: file=9ca962e47fab66e8e95dc7ce447c2fcec013a4f8e1161d711e53d6329c7faeea expected=0000000000000000000000000000000000000000000000000000000000000000
```

종료 코드 4.

## 9. 검증되지 않은 것 (Gaps)

- 실제 콘솔에서 송신이나 점검을 하지 않았다(카드 지시: 콘솔 송신 금지). 콘솔의 응답 형식과 게이트의 실제 판정은 콘솔 실행 때에야 확인된다.
- 타임코드 경로 `DataPool/Timecodes` 는 검증되지 않았다. 앱 주석 근거이며, 점검에서 `path_status: unverified` 로 표시한다. 컨테이너 자체가 없으면 `path_unverified` 로 기록하고 빈 칸으로 보지 않는다.
- 프리셋 풀 페이징은 앱의 `paged_pool_children` 규칙을 그대로 따른다. 시험은 24개 자식 창 두 개로 확인했다.
- 세션 백업과 위험 실행 전 백업이 실제 콘솔에서 어떻게 기록되는지는 콘솔 실행 때 확인해야 한다.

## 10. PR·CI

- PR: 생성 후 기록
- CI: 생성 후 기록
