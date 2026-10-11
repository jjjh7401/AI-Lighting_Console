# t565 run 판정서 — 박자 격자 2D 무대에 실제 장비 연결

- 카드: t565 (「앱에서 무대가 비어 있다」)
- 범위: SPEC-LDBEAT-001 REQ-022 — 박자 격자 WS 로 장비 좌표 + 그룹→소속 장비를 내려 `BeatGrid` `fixtures` 에 연결
- 브랜치: `WT-stage-fixtures-wire` (작업 트리 `.claude/worktrees/t565`), 기준 `e41ec326` (= origin/main, 착수 시 확인)
- 콘솔: **읽기 1회만**, 쓰기 0건(아래 §3)

## 0. 배차 전제 정정 (리드 승인 2026-10-11)

배차서는 그룹 소속 판독이 서버에 이미 있다고 했다(「t525 SELECTIONDATA 그룹 소속」). 실제로는 서버 판독 함수가 0건이었고, t525 `probe_groups.py`·t531 `group_members.py` 는 `.moai/reports` 의 프로브 스크립트뿐이었다. 전체 소속을 실기로 읽은 기록도 0건이었다(t531 `group_members_refusal.txt` = 응답기 1.6.5 거부 1회). 착수 전에 리드에게 보고했고, 리드가 「응답기에 이미 있는 §4.8 나눠 읽기 + t525 실측 sf_index→fid 규칙을 서버로 옮기는 것은 프로브 승격」으로 승인했다.

## 1. 바뀐 것

| 파일 | 내용 |
|---|---|
| `server/bridge/protocol.py` | `build_props_query(..., offset=None)` — PROTOCOL.md §4.8 그대로: `None` 은 예전 바이트 그대로, `0` 도 토큰을 싣는다(창 모드는 토큰이 있을 때만), 이름이 정확히 하나일 때만 허용 |
| `server/safety/console.py` · `server/safety/gate.py` · `server/orchestrator/ports.py` | `query_properties` 에 `offset` 키워드를 통과(창이 있을 때만 넘김 — `enumerate_fields` 와 같은 규칙). 감사 기록은 그대로 경로+이름만 |
| `server/design/beat_grid_stage.py` (신규) | `read_beat_grid_stage` — 좌표는 `read_spatial_fixtures`(생산 함수 그대로, `slot_sink` 로 슬롯 주소), 그룹 목록은 `server.rig.paging.paged_children`, 소속은 SELECTIONDATA §4.8 창 읽기(offset 반향이 진전의 증거), sf_index→fid 는 장비별 `SUBFIXTUREINDEX`. 실패는 예외가 아니라 `unread` 이유로 |
| `server/web/messages.py` · `app.py` · `session.py` | 요청 `beat_grid_stage_request`(페이로드 없음) → 응답 `beat_grid_stage {fixtures, groups, unread}`. 경로는 `rig_paths`(코드 상수 아님) |
| `server/tests/test_prechk_tool.py` | 웹 표면 동결 목록에 두 메시지 등재(t551 선례와 같은 방식) |
| `server/tests/test_safety_console.py` | 선언 표면 고정 시험의 `query_properties` 인자 목록에 `offset` 추가 — 의도한 확장(`enumerate_fields` 의 offset 과 같은 이유) |
| `ui/src/protocol.ts` · `useCopilotSocket.ts` · `App.tsx` | 타입·요청·상태. 박자 격자 전체화면을 열 때(곡이 바뀔 때도) 한 번 요청 |
| `ui/src/components/beatGridStageModel.ts` (신규) | 판독 → 장비 점. 소속은 이름 **목록**(`confirmedGroupNames`) — 한 장비가 부모·자식 그룹에 함께 든다. 판정 함수 `fixtureBelongsTo` 하나 |
| `ui/src/components/BeatGrid.tsx` · `beatGridTransition.ts` | 색·흐림·무대 영역·장비 수 네 곳이 `fixtureBelongsTo` 를 쓰게(예전 한 개짜리 필드도 그대로 인정). `stageNotes` prop |
| `ui/src/components/BeatGridStage.tsx` · `beatGridPanels.css` | 못 읽은 이유를 무대 칸 아래 그대로 표시 |

### 프로토콜 (리드 채택, t560 공유)

```
요청  {type:"beat_grid_stage_request"}
응답  {type:"beat_grid_stage",
       fixtures:[{fid,name,x,y,z}],
       groups:[{group_no, group_name, member_fids:number[], complete:boolean}],
       unread:string[]}
```

`groups` 는 박자 격자 **트랙 이름과 같은** 콘솔 그룹만 담는다(대소문자만 무시, 이름 앞부분 추정 없음).

## 2. 시험 (이 트리, 이 실행)

| 명령 | 결과 | 파일 |
|---|---|---|
| `uv run pytest -q server/tests/test_beat_grid_stage.py` (구현 전) | `ModuleNotFoundError` — RED | `red-1.txt` |
| `npx vitest run src/components/beatGridStageModel.test.ts` (구현 전) | `Test Files 1 failed` — RED | `red-2.txt` |
| 관련 pytest 12파일 | `388 passed` | `pytest-related.txt` |
| `npx tsc --noEmit -p ui` | exit 0 | `tsc.txt` |
| `npx vitest run --root ui` | `Test Files 40 passed (40)` · `Tests 971 passed (971)` | `vitest.txt` |
| `ruff check` (바꾼 파이썬 파일 11개) | `All checks passed!` | — |

새 시험: 서버 17건(명령 조립 4·나눠 읽기 4·무대 판독 6·메시지/세션 3), UI 7건.

## 3. 실기 읽기 1회 (콘솔 읽기만)

- 명령: `uv run python .moai/reports/t565/live_stage_read.py > .moai/reports/t565/live_stage_read.json` (stderr 0바이트)
- 길: 생산 함수 `read_beat_grid_stage` 를 `SafetyGate.state_port`(감사 포트)로 — 앱과 같은 길. 실행 포트 미사용. 응답기가 1.6.6 이 아니면 읽지 않고 멈추게 짰다.
- 응답기: `ping True`, `1.6.6`
- 요청 수: **256** (`state` 69 · `props` 187). props = 좌표 일괄 86 + SUBFIXTUREINDEX 86 + SELECTIONDATA 창 15.
- 결과: 장비 **86대**, 트랙 그룹 **8/8** 찾음, 전부 `complete: true`, `unread` **0건**

| 그룹 번호 | 그룹 | 소속 장비 수 | complete | 창(offset) |
|---|---|---|---|---|
| 3 | FOH | 8 | true | 0, 7 |
| 4 | BACK | 12 | true | 0, 7 |
| 7 | SIDE-ALL | 12 | true | 0, 7 |
| 10 | WASH-ALL | 20 | true | 0, 7, 14 |
| 11 | MOVER-U | 8 | true | 0, 7 |
| 12 | MOVER-D | 8 | true | 0, 7 |
| 14 | BLIND | 6 | true | 0 |
| 15 | STROBE | 4 | true | 0 |

창 하나에 SELECTIONDATA 항목 7개가 왔다(응답 한도 1900바이트). sf_index 는 전부 본체 장비에 대응했다(대응 안 된 번호 0건) — t525 의 「그룹은 본체 번호를 담는다」가 8그룹 전체에서 유지됐다. 소속 장비 번호가 그룹 이름과 맞는다(FOH 111~118, BACK 201~212, BLIND 601~606, STROBE 611~614).

## 4. 안 잰 것

- **앱 화면 0회.** 실기 읽기는 스크립트로 했고, 앱(브라우저)에서 무대가 그려지는 것은 안 봤다. 판독 → 장비 점 → 무대 그림 사이는 UI 시험(렌더·모델)으로만 확인했다.
- 판독 시간은 안 쟀다(256 왕복). 앱은 busy-guard 아래 스레드로 돌린다.
- 회전은 읽지 않는다(무대 그림은 위에서 본 X·Y만 쓴다).
- 전체 pytest 결과는 커밋 시점에 아래 §6 에 적는다.

## 5. 리드 판단이 필요한 것

1. **(리드 결정 2026-10-11 — 확장 안 함)** `groups` 는 트랙 이름과 같은 그룹만 읽으므로 SIDE-L·SIDE-R(트랙 아님)은 응답에 없다. 리드 결정: t560 의 L·R 나누기는 콘솔의 SIDE-L/R 그룹 이름에 기대지 않고, 부모 그룹(SIDE-ALL)의 `member_fids` 를 무대 x 좌표로 나눠 만든다 — 리그와 무관한 기준이다. 그래서 지금 응답(SIDE-ALL 12대 + 좌표)으로 충분하고, 이 카드는 범위를 넓히지 않았다.
2. 콘솔 그룹 이름이 트랙 이름과 다르면(대소문자 외) 그 트랙은 회색으로 남고 `unread` 에 「콘솔에 '…' 그룹이 없음」이 뜬다 — 의도한 동작(이름 추정 금지).

## 6. 전체 pytest

첫 PR 푸시 뒤 로컬 전체 실행이 끝났다: `uv run pytest -q` → `1 failed, 15091 passed, 35 skipped` (`pytest-full.txt`). 실패 1건은 이 카드가 만든 것이다 — `test_responder_roundtrip.py::test_the_constant_is_the_only_server_side_occurrence` 는 응답기 버전 문자열이 `server/safety/` 에서 `responder_version.py` 한 곳에만 있기를 요구하는데, `console.py` 설명문에 버전 숫자를 적었다. 숫자를 「PROTOCOL.md §4.8」로 바꿔 고쳤다: `grep -rln '1\.6\.6' server/safety` → `responder_version.py` 하나, 해당 시험 포함 `56 passed`. 고친 뒤 전체를 다시 끝까지 돌리지는 않았다 — CI 결과를 정본으로 한다.
