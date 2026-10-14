# t651 범위 보고 — 박자 격자 재연결 뒤 세션 필드 수명

- 카드: t651 · 브랜치 `WT-grid-field-life` · 워크트리 `.claude/worktrees/t651`
- 기준: `origin/main` 00d9b86c (시작할 때 `git fetch origin main` 으로 재확인)
- 재현 시험 커밋: `d46e54c5`
- 범위: 재현과 판정까지. **수정은 하지 않았다.** 콘솔 쓰기에 닿는 수정은 「실행」 뒤에 한다.

## 1. 주장

### 1-1. 필드별 판정

| 세션 필드 | 판정 | 사용자에게 보이나 | 근거 시험 |
|---|---|---|---|
| `_beat_grid_pool_slots` | **결함** | 예. 재연결 뒤 「빈 프리셋」 표식이 사라진다. 콘솔은 그대로인데 | `test_marks_survive_a_new_connection_while_the_console_is_unchanged` **RED** |
| `_beat_grid_empty_marks` | 결함 아님 | 아니오. 재생 때 다시 써져 클라이언트 값과 같이 간다 | `test_a_read_after_reconnect_resends_the_marks_the_client_lacks` 통과 |
| `_beat_grid_suggestions` | **조건부 결함** | 현재 빌드에서는 아니오 (제안 소스가 없다). 소스가 붙으면 예 | `test_apply_after_reconnect_is_refused_with_a_misleading_reason` 통과 (특성 시험) |
| `_preview_approval` | 대상 아님 (배차 지시) | 주석상 세션 시작 1회 승인이다. 재연결은 새 세션이므로 다시 묻는다 (추론, 시험 없음) | 없음 |

### 1-2. 근거

- **`_beat_grid_pool_slots` (결함).** 콘솔 프리셋 풀의 마지막 완전 판독을 쥔다. 빈 프리셋 표식은 여기서만 갈린다 (`server/web/session.py:4172-4177` 주석: 「표식의 유일한 출처」). 연결할 때 서버가 보내는 재생 프레임은 `song_timeline_replay()` → `derive_beat_grid_fields()` 로 만들어진다 (`server/web/app.py:489-491`). 새 세션의 풀 메모리는 비어 있다. 빈 메모리에서 `empty_preset_cells(grid, {})` 는 `[]` 를 돌려준다 (`server/design/beat_grid.py:872` docstring: 「아직 읽지 않은 풀의 번호는 판정하지 않는다」. 기존 시험 `test_pool_never_read_gives_no_mark` 도 같은 사실을 고정한다). 클라이언트는 이 프레임으로 타임라인을 통째로 바꾼다 (`ui/src/protocol.ts:1990`). 결과는 표식 0개다.
- **원인 확인 (C2).** 저장소와 격자는 그대로 두고, 새 세션이 풀을 한 번 읽기만 하면 같은 재생 경로가 bar 1 표식을 되살린다 (`test_marks_come_back_once_the_new_session_reads_the_pool` 통과). 원인은 세션 메모리다. 저장소와 재생 코드는 원인이 아니다.
- **`_beat_grid_empty_marks` (결함 아님).** 곡마다 마지막으로 보낸 표식의 기억이다. 쓰는 곳은 `derive_beat_grid_fields()` 한 곳(`session.py:4058`)이다. 재생 때마다 현재 값으로 다시 써지므로 기억과 클라이언트가 어긋나지 않는다. 재연결 뒤 읽기가 풀을 다시 읽으면 표식을 다시 보낸다. 이 필드는 옮길 필요가 없다.
- **`_beat_grid_suggestions` (조건부 결함).** 보류 제안은 세션 메모리다 (`session.py:4145`). 재연결하면 서버 목록은 비고, 클라이언트의 보류 카드는 남는다. 재연결 때 지우는 `clearPendingRequests` 는 승인·검토 카드만 비운다 (`ui/src/protocol.ts:2193-2199`). 그래서 남은 카드로 「적용」하면 「이미 적용됐거나 만료됐습니다」라는 **틀린 사유**가 뜬다. 승인 카드에 이미 고친 「낡은 카드가 남는다」 결함과 같은 모양이다 (`protocol.ts:2186-2192` 주석).
- **도달성.** 운영 빌드에서는 제안이 생기지 않는다. 제안 소스는 `NullSuggestionSource` 하나다. 저장소 전체에서 소스를 넘기는 곳은 기본값 `session.py` 와 테스트 헬퍼 `test_session_beat_grid_edit_t551.py` 뿐이다 (2-4). 운영 생성자 (`server/web/app.py:396`) 는 소스를 넘기지 않는다.

## 2. 증거 (명령과 출력 전문)

### 2-1. 재현 시험 — 커밋 `d46e54c5`, 환경 격리 형식

명령:

```
unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && uv run pytest -v --tb=short server/tests/test_beat_grid_field_life_t651.py; echo "exit=$?"
```

출력 전문:

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t651/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t651
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.14.2
collecting ... collected 7 items

server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_control_same_session_replay_keeps_the_marks PASSED [ 14%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_marks_come_back_once_the_new_session_reads_the_pool PASSED [ 28%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_marks_survive_a_new_connection_while_the_console_is_unchanged FAILED [ 42%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyMarkMemoAfterReconnect::test_a_read_after_reconnect_resends_the_marks_the_client_lacks PASSED [ 57%]
server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_default_source_creates_no_pending_suggestion_in_this_build PASSED [ 71%]
server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_same_connection_apply_finds_the_pending_suggestion PASSED [ 85%]
server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_apply_after_reconnect_is_refused_with_a_misleading_reason PASSED [100%]

=================================== FAILURES ===================================
_ TestEmptyPresetMarksAcrossReconnect.test_marks_survive_a_new_connection_while_the_console_is_unchanged _
server/tests/test_beat_grid_field_life_t651.py:103: in test_marks_survive_a_new_connection_while_the_console_is_unchanged
    assert marked == [1], f"재연결 뒤 빈 프리셋 표식이 사라짐 — 재생 프레임 표식 bar: {marked}"
E   AssertionError: 재연결 뒤 빈 프리셋 표식이 사라짐 — 재생 프레임 표식 bar: []
E   assert [] == [1]
E     
E     Right contains one more item: 1
E     
E     Full diff:
E     + []
E     - [
E     -     1,
E     - ]
=========================== short test summary info ============================
FAILED server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_marks_survive_a_new_connection_while_the_console_is_unchanged
========================= 1 failed, 6 passed in 0.41s ==========================
exit=1
```

- 종료 코드 `exit=1`: 7건 중 6건 통과, 1건 실패. 실패는 의도한 재현(RED)이다.
- 이 워크트리의 자체 `.venv` (`uv sync --group dev`, Python 3.11.15) 로 돌렸다. 빌린 venv 가 아니다.

### 2-2. 린트 — 같은 파일

명령: `uv run ruff check server/tests/test_beat_grid_field_life_t651.py; uv run ruff format --check server/tests/test_beat_grid_field_life_t651.py`

출력:

```
All checks passed!
1 file already formatted
```

### 2-3. 줄 번호 근거 (`d46e54c5` 기준)

명령: `grep -n "def song_timeline_replay\|def _beat_grid_refresh_unsent_cells\|def beat_grid_suggest(\|def beat_grid_suggestion_apply\|def _beat_grid_learn_pools\|def _beat_grid_split_empty_presets\|def beat_grid_apply\|def _beat_grid_recheck_new_presets\|def derive_beat_grid_fields\|_beat_grid_pool_slots: dict\|_beat_grid_empty_marks: dict\|self._beat_grid_suggestions = \|self._preview_approval = " server/web/session.py`

출력:

```
4024:def derive_beat_grid_fields(
4145:        self._beat_grid_suggestions = PendingSuggestionStore()
4178:        self._beat_grid_pool_slots: dict[int, dict[int, str | None] | None] = {}
4179:        self._beat_grid_empty_marks: dict[tuple[object, object], list[dict[str, object]]] = {}
4180:        self._preview_approval = PreviewApprovalSession()
10229:    def _beat_grid_refresh_unsent_cells(self, timeline: dict) -> dict:
10238:    def song_timeline_replay(self) -> dict | None:
10264:    def _beat_grid_learn_pools(
10408:    def beat_grid_apply(self) -> dict:
10991:    def beat_grid_suggest(self, bar: int, target: str) -> dict:
11024:    def beat_grid_suggestion_apply(self, suggestion_id: str) -> dict:
11531:    def _beat_grid_recheck_new_presets(self, creations: Mapping[str, object]) -> str | None:
11566:    def _beat_grid_split_empty_presets(
```

풀 메모리 쓰기 지점 (읽기가 성공했을 때만): `session.py` 9963 (효과 풀), 10068 (위치 풀), 10150 (색 풀), 10271 (`_beat_grid_learn_pools` 갱신). 판독 호출처: 9534 (서랍), 11553 (송신 직전 재판독), 11587 (승인 대기 판독).

### 2-4. 제안 소스 전수 검색

명령: `grep -rln "beat_grid_suggestion_source" --include='*.py' . --exclude-dir=.venv --exclude-dir=node_modules`

출력:

```
server/web/session.py
server/tests/test_session_beat_grid_edit_t551.py
```

명령: `grep -n "ChatSession(" server/web/app.py`

출력:

```
396:        session = ChatSession(
```

운영 생성자 호출 (396행부터) 의 인자 목록에 `beat_grid_suggestion_source` 가 없다.

### 2-5. 연결 재생 경로 (읽기 근거)

- `server/web/app.py:489-491`: `replay = session.song_timeline_replay()` → `if replay is not None:` → `await _safe_send(websocket, replay)`. 새 연결마다 한 번 보낸다.
- `server/web/session.py:10238` `song_timeline_replay` → `10229` `_beat_grid_refresh_unsent_cells` → `derive_beat_grid_fields(... pool_slots=self._beat_grid_pool_slots, empty_marks=self._beat_grid_empty_marks)`.

### 2-6. 클라이언트 (읽기 근거 — 실행하지 않았다)

- `ui/src/useCopilotSocket.ts:65`: `if (action.kind === "disconnected") return clearPendingRequests(state);`
- `ui/src/protocol.ts:2193-2199`: `clearPendingRequests` 는 `pendingApprovals`·`pendingReviews` 만 비운다. `pendingBeatGridSuggestion` 은 건드리지 않는다.
- `ui/src/protocol.ts:2002-2014`: 제안은 `beat_grid_suggestion` 으로 생기고 `beat_grid_suggestion_consumed` 로만 지워진다.
- `ui/src/protocol.ts:1990`: `song_timeline` 은 타임라인을 `{ timeline: event.timeline, stale: false }` 로 통째로 바꾼다.
- `ui/src/components/BeatGrid.tsx:1476-1477`: 표식은 `grid?.empty_preset_cells` 에서만 읽는다.
- `ui/src/protocol.ts:2219` `clearOnDisconnect`: 운영 호출처가 없다. 명령 `grep -rn "clearOnDisconnect(" ui/src --include='*.ts' --include='*.tsx' | grep -v "\.test\."` 의 결과는 정의 한 줄뿐이다.

### 2-7. 프로덕션 코드 변경 0

명령: `git show --stat HEAD` 의 결과는 테스트 파일 하나 (`179 insertions`) 다. 프로덕션 코드는 바뀌지 않았다.

## 3. 기준선 귀속

- 측정 커밋: `d46e54c5` (`git rev-parse --short HEAD`). 브랜치 `WT-grid-field-life`. 기준 `origin/main` 00d9b86c (`git rev-parse --short origin/main`). `git status --short` 는 시험 전후로 비어 있었다.
- 모든 값은 이 실행에서 잰 것이다. t642 의 값은 근거로 쓰지 않았다. t642 시험 파일의 구조만 본떴다.
- 이 보고는 별도 커밋 (`docs(t651)`) 에 담는다.

## 4. 미검증 (Gaps)

- **실제 WebSocket 재연결은 돌리지 않았다.** 세션 층의 `song_timeline_replay()` 를 직접 불렀다. app.py 489-491 이 보내는 것과 같은 함수지만, 연결 루프 자체는 실행하지 않았다.
- **클라이언트 동작은 코드 읽기로만 확인했다.** `ui/` 테스트와 실행은 하지 않았다 (이 워크트리에 `node_modules` 를 설치하지 않았다). 「카드가 남는다」「표식이 지워진다」는 읽기 근거다.
- **실기 콘솔 접촉 0건.** `FakeConsole` 만 썼다. 실기 풀의 실제 상태는 재지 않았다.
- **수정 후 GREEN 확인 안 함.** 수정은 「실행」 뒤다. 고쳐진 코드에서 이 시험이 통과할지는 아직 모른다.
- **뮤테이션 미실행.** 프로덕션 코드는 건드리지 않았다 (범위 밖). 대신 원인 되묻기 시험으로 경계를 확인했다.
- **전체 스위트 미실행.** 변경이 테스트 파일 하나라 영향 범위는 이 파일이다 (lane-local verification). 그래서 회귀 없음을 주장하지 않는다.
- **`_preview_approval` 시험 없음.** 배차가 제외했다. 판정 근거는 주석 (`session.py:4155-4156`) 과 추론뿐이다.

## 5. 잔여 위험

- 결함을 고칠 때 **메모리 수명이 연결에서 프로세스로 늘어난다.** 콘솔을 이 앱 밖에서 바꾸면 표식이 다음 판독까지 옛 값을 보일 수 있다. 세션 안에서도 같은 문제가 있지만 수명이 길어진다. 수정 때 판독 시각을 붙이거나, 재연결 때 한 번 재판독하는 방식 중 하나를 고른다.
- **판독과 추정의 구별을 깨뜨리지 마라.** `_beat_grid_note_created_presets` 는 송신 성공에서 나온 추정을 더하고, 다음 판독은 풀 전체를 갈아 끼운다 (t595 설계, `session.py:4172-4177` 근처). 풀 메모리를 통째로 저장소에 넣으면 이 구별이 접힌다.
- `test_apply_after_reconnect_is_refused_with_a_misleading_reason` 은 **틀린 사유를 고정하고 있다.** 결정이 나면 단언을 바꿔야 한다.
- 4-2 의 「결함 아님」 판정은 「재생 때 기억을 다시 쓴다」는 현재 구조에 기댄다. `test_a_read_after_reconnect_resends_the_marks_the_client_lacks` 가 그 구조를 지킨다.

## 6. 수정 제안 (실행 전 — 아직 하지 않았다)

**수정 A — 결함 (`_beat_grid_pool_slots`).** 풀 판독 메모리를 `SongTimelineStore` 로 옮긴다. 수명은 t635 의 `beat_grid_snapshots` 와 같다. 콘솔이 하나이므로 프로세스 단위다.

- 바꿀 곳: `server/web/session.py` 4178 (초기화), 쓰기 9963·10068·10150·10271, 읽기 10229-10236, 생성자의 `timeline_store` 인자 경로.
- 바꾸지 않을 곳: `server/web/app.py` (연결 코드), `_beat_grid_empty_marks` (4179, 4-2 판정).
- 검증: 이 파일의 RED 가 GREEN 이 되는지, 그리고 `server/tests/test_empty_preset_mark_t595.py` 와 `server/tests/test_web_first_connect_apply_t635.py` 가 회귀하지 않는지. env-isolated 형식으로 돌린다.
- 주의: 5절의 두 위험.

**수정 B — 조건부 (`_beat_grid_suggestions`).** 결정 1 이 나기 전에는 하지 않는다. 운영에 제안 소스가 붙기 전에는 우선순위가 낮다.

## 7. 결정 필요 (리드 / 감독)

1. **보류 제안은 재연결을 넘어야 하나?**
   - (a) 아니오. 제안을 연결 수명으로 명시하고, 클라이언트도 재연결 때 `pendingBeatGridSuggestion` 을 지운다. 승인 카드와 같은 처방이다 (`clearPendingRequests` 확장).
   - (b) 예. 저장소로 옮긴다.
   - 현재는 영향이 없다. 운영에 소스가 없기 때문이다.
2. **수정 A 를 「실행」할지.** 콘솔 쓰기 경로는 아니지만, 서버 상태의 수명을 바꾼다.

## 8. 배차서와 다른 점 (레인 규약 6절에 따라 알림)

- **0번 `ExitWorktree(keep)`**: no-op 을 예상했다. 실제로는 세션을 주 체크아웃으로 되돌렸다. 응답은 t642 트리를 「branch worktree-t642」로 적었는데, `git worktree list` 는 `WT-beat-grid-reconnect` 로 본다. 이름이 어긋난다. 정리하지 않았다.
- **1번 base**: `git fetch origin main` 으로 00d9b86c 를 확인한 뒤 `EnterWorktree(name: "t651")` 로 만들었다. 생긴 브랜치 `worktree-t651` 을 `git branch -m WT-grid-field-life` 로 바꿨다. HEAD 는 00d9b86c 다.
- 배차의 값 (브랜치 이름, 기준, 파일 목록) 은 바꾸지 않았다.
- 서브에이전트는 띄우지 않았다. 이 워크트리에 커밋한 것은 `d46e54c5` 와 이 보고 커밋뿐이다.
- 주 체크아웃에서는 아무것도 쓰지 않았다. 읽기 명령 (`pwd`, `git branch --show-current`, `git worktree list`) 만 실행했다.

## 9. 범위 밖 관찰 (손대지 않았다)

- `ui/src/protocol.ts:2219` `clearOnDisconnect` 에는 운영 호출처가 없다. 주석은 「한 함수로 모든 끊김을 처리한다」고 말하지만, 실제 끊김 경로는 `useCopilotSocket.ts:65` 의 `clearPendingRequests` 만 탄다. 두 경로가 갈려 있다.
