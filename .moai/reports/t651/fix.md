# t651 수정 기록 — 재연결 뒤 빈 프리셋 표식 소실 (수정 A)

- 카드: t651 · 브랜치 `WT-grid-field-life` · 워크트리 `.claude/worktrees/t651`
- 기준: `origin/main` 00d9b86c
- 커밋: `563f5d1f` 수정 · `53c3d16c` 추정 시험 보강 · `c6bbf9b6` 콘솔 변화 시험 재구성 (뮤테이션 결과에 따라 나눴다)
- 실행 근거: 리드 메시지의 「실행」. 리드는 감독 AskUserQuestion 「실행 (권장)」 선택을 전했다. 이 세션이 직접 확인한 것은 아니다.
- 범위: `scope.md` 6절 수정 A. 리드가 승인한 한 줄 추가는 `server/web/timeline_api.py` 로드 응답이다.

## 1. 주장

1. 재연결 뒤 새 세션은 저장소의 풀 판독 기억으로 표식을 가른다. 콘솔이 그대로면 표식은 재연결 전과 같다. 수정 전에는 RED 였던 `test_marks_survive_a_new_connection_while_the_console_is_unchanged` 가 초록이다.
2. 5절 위험의 처방은 판독 시각이다. 재생·로드 응답의 `beat_grid.empty_preset_read_at` 이 판독한 풀의 시각을 싣는다. 이 키는 판독이 한 번이라도 있을 때만 생긴다.
3. 추정(송신 성공으로 만든 번호)은 저장소에 남아 새 연결에도 「있음」으로 보이고, 판독 시각을 바꾸지 않는다. 카드 t595 의 구별을 지킨다.
4. 콘솔 쓰기 판정은 풀 메모리를 읽지 않는다. 판정은 판독 호출이 그 자리에서 채운 지역 값으로 한다 (5절 근거).
5. 로드 응답(`POST /api/timelines/{id}/load`)의 표식은 재생 프레임과 같다.
6. 손대지 않은 것: `_beat_grid_empty_marks`, `server/web/app.py`, `_beat_grid_suggestions`. 제안은 수정 B 가 아니라 특성 시험을 그대로 둔다 (감독 결정 1).

## 2. 증거

### 2-1. 재현 시험이 초록이 됐다 (HEAD `c6bbf9b6`)

명령:

```
unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && uv run pytest -v --tb=short server/tests/test_beat_grid_field_life_t651.py; echo "t651_exit=$?"
```

출력 (발췌 없이 전문):

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t651/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t651
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.14.2
collecting ... collected 10 items

server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_control_same_session_replay_keeps_the_marks PASSED [ 10%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_a_never_read_store_gives_no_marks_on_connect PASSED [ 20%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_marks_survive_a_new_connection_while_the_console_is_unchanged PASSED [ 30%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyPresetMarksAcrossReconnect::test_replay_says_when_the_marks_were_read PASSED [ 40%]
server/tests/test_beat_grid_field_life_t651.py::TestEmptyMarkMemoAfterReconnect::test_a_console_change_after_reconnect_still_resends_the_marks PASSED [ 50%]
server/tests/test_beat_grid_field_life_t651.py::TestCreationEstimateAcrossConnections::test_a_creation_estimate_survives_and_keeps_the_read_time PASSED [ 60%]
server/tests/test_beat_grid_field_life_t651.py::TestLoadResponseParity::test_load_response_and_connect_replay_show_the_same_marks PASSED [ 70%]
server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_default_source_creates_no_pending_suggestion_in_this_build PASSED [ 80%]
server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_same_connection_apply_finds_the_pending_suggestion PASSED [ 90%]
server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_apply_after_reconnect_is_refused_with_a_misleading_reason PASSED [100%]

======================== 10 passed, 1 warning in 0.94s =========================
t651_exit=0
```

### 2-2. 영향 범위 시험 — 수정 전후 대조

명령(같은 21개 파일): `uv run pytest -q --tb=no -rfE <21개 파일>`

- 수정 전 (HEAD `0fc18790`): `1 failed, 835 passed, 1 warning in 11.47s` — 실패 1건은 재현 시험, 기대한 RED 다.
- 수정 후 (HEAD `c6bbf9b6`): `839 passed, 1 warning in 7.73s`, 종료 코드 `affected_set_exit=0`.
- 대조: 시험 파일 밖의 829건은 두 번 모두 통과했다. 835 = 829 + 6, 839 = 829 + 10. 이 카드 시험 파일은 7개에서 10개가 됐다 (4절).

### 2-3. 린트

명령: `uv run ruff check server/web/session.py server/web/timeline_api.py server/tests/test_beat_grid_field_life_t651.py && uv run ruff format --check <같은 3개 파일>`

출력:

```
All checks passed!
3 files already formatted
```

### 2-4. 뮤테이션 — 시험이 자기 일을 하는지 (protocol §3.3)

각 뮤턴트는 메커니즘 하나만 건드렸다. 끝나면 `git checkout -- <파일>` 로 커밋본으로 되돌렸고, 되돌린 뒤 `git status --short` 는 비어 있었다.

| 뮤턴트 | 건드린 것 | 결과 |
|---|---|---|
| M1 | 풀 기억을 연결 안에만 둠 (저장소 연결 끊음) | 4건 빨강: 재현, 콘솔 변화, 추정, 로드 패리티 |
| M2 | 로드 응답이 풀 기억을 안 씀 (`pool_slots={}`) | 1건 빨강: 로드 패리티 |
| M3 | 추정 경로가 판독 시각을 다시 찍음 | 1건 빨강: 추정 |
| M4 | 재생이 메모(`_beat_grid_empty_marks`)를 다시 쓰지 않음 | 첫 시험판은 0건 빨강 (살아남음). 학습 경로 시험으로 재구성한 뒤 1건 빨강: 콘솔 변화 |
| M5 | 판독 시각을 연결 안에만 둠 | 2건 빨강: 판독 시각, 추정 |

살아남은 뮤턴트를 어떻게 다뤘나.

- **M1 의 첫 실행**에서 추정 시험이 통과했다. 풀 기억이 통째로 없으면 표식이 빈 목록이라 「없음」과 같아 보였다. 빈 번호 4.50(bar 2)을 더해, 풀 기억이 살아 있어야 bar 2 표식이 남도록 고쳤다 (`53c3d16c`).
- **M4 의 첫 실행**에서 콘솔 변화 시험이 통과했다. 반영의 마지막 격자 송신이 같은 표식을 실어서, 메모가 없어도 통과가 다른 경로로 얻어졌다. 메모의 중복 송신 판정만 부르는 학습 경로 시험으로 바꿨다 (`c6bbf9b6`).

### 2-5. 바뀐 곳 (줄 번호는 HEAD `c6bbf9b6` 기준)

- `server/web/session.py`
  - `SongTimelineStore.beat_grid_pool_slots`, `beat_grid_pool_read_at` (3723, 3726행). 프로세스 단위, 파일에 저장하지 않는다.
  - `ChatSession.__init__` 의 카드 t595 주석 아래 — 두 풀 기억이 저장소 사전을 공유한다 (4195행부터).
  - `derive_beat_grid_fields(..., pool_read_at=None)` (4033행) — 판독이 있을 때만 `empty_preset_read_at` 을 싣는다.
  - `_beat_grid_refresh_unsent_cells` (10254행) — `pool_read_at` 을 넘긴다.
  - `_beat_grid_remember_pool_read` (10290행, 새 헬퍼) — 판독 성공은 시각을 찍고, 못 읽음(`None`)은 풀과 시각을 지운다.
  - 효과·위치·색 판독 세 곳과 `_beat_grid_learn_pools` (10304행) 가 이 헬퍼를 거친다.
  - `_beat_grid_note_created_presets` (10277행) — 바뀌지 않았다. 추정은 시각을 찍지 않는다.
- `server/web/timeline_api.py` (78, 80행) — 로드 응답이 저장소의 풀 기억과 판독 시각을 쓴다. 주석도 고쳤다. 리드 승인 범위의 한 줄이다.
- `server/tests/test_beat_grid_field_life_t651.py` — 4절.

## 3. 5절 위험의 처방 — 고른 쪽과 이유

고른 쪽: **판독 시각을 붙인다.** `empty_preset_read_at` 은 {풀 번호: UTC ISO 8601 시각}이다. 판독이 한 번도 없었으면 키가 없다.

버린 쪽: **재연결 때 한 번 재판독.** 버린 이유는 셋이다.

1. 카드 t595 가 정한 「표식을 위해 따로 콘솔을 읽지 않는다」를 어긴다 (`ChatSession.__init__` 의 카드 t595 주석).
2. 재생은 연결 핸드셰이크 안에서 기다려진다 (`server/web/app.py` 489-491행). 콘솔 왕복을 넣으면 연결이 느려지고, 콘솔이 응답하지 않으면 재생이 멈춘다. `app.py` 주석은 콘솔 왕복 한 번의 지연을 5초 단위로 적고 있다.
3. 판독 시각은 콘솔을 더 읽지 않고도 표식의 나이를 말해 준다.

처방의 한계를 분명히 적는다. 시각은 싣지만 화면은 아직 그리지 않는다. 그래서 낡은 표식을 **화면에서 막지는 않는다.** 막는 것은 콘솔 쓰기 판정이고, 그것은 낡은 표식으로 결정되지 않는다 (5절). 시각을 화면에 그리는 일은 후속 카드다.

## 4. 시험 구성 — 무엇을 바꿨나

- 시험 수는 7개에서 10개가 됐다.
- **교체 두 개.** 「재연결 직후 표식 0개」와 「재연결 뒤 읽기가 0개를 보고 다시 보냄」은 결함 상태를 적은 단언이었다. 수정 뒤에는 거짓이라 바꿨다.
  - `test_marks_come_back_once_the_new_session_reads_the_pool` → `test_a_never_read_store_gives_no_marks_on_connect` (판독 전 저장소는 표식이 없다. 대조군)
  - `test_a_read_after_reconnect_resends_the_marks_the_client_lacks` → `test_a_console_change_after_reconnect_still_resends_the_marks` (메모가 콘솔 변화를 가리지 않는다)
- **추가 세 개.** `test_replay_says_when_the_marks_were_read` (판독 시각), `test_a_creation_estimate_survives_and_keeps_the_read_time` (추정, t595 구별), `test_load_response_and_connect_replay_show_the_same_marks` (로드 패리티, 감독 요청).
- **그대로.** 같은 연결 대조군, 재현 시험(RED 에서 초록), 제안 특성 시험 세 개.

## 5. 쓰기 판정이 메모리를 읽지 않는다는 근거

명령: `grep -n "_beat_grid_pool_slots" server/web/session.py`

출력:

```
3720:        # None). ``ChatSession._beat_grid_pool_slots`` 와 같은 사전을 여기서 공유한다. 연결마다
4195:        self._beat_grid_pool_slots: dict[int, dict[int, str | None] | None] = (
10259:            pool_slots=self._beat_grid_pool_slots,
10286:            slots = self._beat_grid_pool_slots.get(pool_no) if pool_no is not None else None
10298:            self._beat_grid_pool_slots[pool_no] = None
10301:        self._beat_grid_pool_slots[pool_no] = dict(children)
10317:        marks = empty_preset_cells(latest["beat_grid"], self._beat_grid_pool_slots)
```

읽기 지점은 셋뿐이다. 표시용 파생(`derive`, 10259행), 추정의 제자리 갱신(10286행), 격자 송신 여부 판정(`_beat_grid_learn_pools`, 10317행). 콘솔에 쓰는 판정은 이 메모리를 읽지 않는다. 판정 함수는 판독 호출이 그 자리에서 채운 지역 값을 받는다. 반영 직전 재판독 `_beat_grid_recheck_new_presets` (11592행의 `fresh`), 승인 대기 판독 `_beat_grid_split_empty_presets` (11626-11627행의 `pool_slots` 와 `split_empty_preset_holds`).

## 6. 미검증 (Gaps)

- 실제 WebSocket 연결 루프는 시험하지 않았다. 세션 층과 REST 층을 시험했다. `app.py` 489-491행은 읽기 근거다.
- 클라이언트는 읽기로만 확인했다. `parseServerEvent` (`ui/src/protocol.ts:1149-1161`) 는 JSON 과 `v`·`type` 만 확인하므로 `beat_grid` 안의 새 키를 거부하지 않는다. 화면 동작은 실행하지 않았다.
- 실기 콘솔 접촉 0건. FakeConsole 만 썼다.
- 전체 스위트는 돌리지 않았다. 영향 범위 21개 파일을 돌렸다 (lane-local 원칙).
- 두 탭이 열려 있으면 한 탭의 판독은 다른 탭 화면을 즉시 바꾸지 않는다. 다음 격자 송신 때 보인다. 이것은 전에도 있던 한계다. 기억의 수명만 길어졌다.
- 저장소 사전을 잠금 없이 공유한다. t635 스냅샷과 같은 수준이다. 두 연결이 같은 순간 판독하면 마지막 쓰기가 이긴다.
- 파일 저장은 하지 않는다. 재시작하면 빈 기억이다. 세션 기억도 재시작에 사라졌으므로 바뀐 것은 없다.

## 7. 잔여 위험

- 낡은 표식이 화면에 그려져도 운영자는 판독 시각을 볼 수 없다. 「판독 시각」 표시를 후속 카드로 권한다.
- 시각은 UTC 문자열이다. 화면에 보일 때 현지 시각으로 바꿔야 한다. 화면 몫이다.
- 추정은 재연결을 넘어 남는다. 의도한 동작이다. 다만 콘솔 쪽에서 그 번호가 누가 지워지면 메모가 틀린다. 다음 판독에서 교정된다.

## 8. 배차·범위와 다른 점

- `server/web/timeline_api.py` 한 줄: 리드 승인 범위다 (리드 메시지 확인).
- 시험 두 개를 교체했다. 결함 상태를 적은 단언이라서다 (4절). 리드에게 알린다.
- M4 재구성: 첫 시험판이 살아남았다 (2-4절). 커밋 `c6bbf9b6` 에 따로 남겼다.
- 제안 (`_beat_grid_suggestions`) 은 건드리지 않았다. 감독 결정 1 대로 별도 카드다.
