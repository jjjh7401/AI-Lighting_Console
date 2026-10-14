# t652 판정 — 재연결 시 보류 제안 카드 지우기 + 끊김 처리 일원화

- 카드: t652 · 브랜치: `WT-drop-suggestion` · 기준: `origin/main` `3f67e525`
- 감독 결정: 보류 제안은 연결 수명이다. 재연결하면 버린다.
- 이 문서는 증거만 담는다. 판정과 카드 닫기는 리드가 한다.

## 1. 주장 (Claim)

| # | 주장 |
|---|---|
| C1 | 끊김·재연결 시 보류 beat-grid 제안 카드가 지워진다 (`clearOnDisconnect` 가 `pendingBeatGridSuggestion` 을 비운다) |
| C2 | 끊김 경로가 하나다. 소켓의 disconnected 액션은 `clearOnDisconnect` 만 호출한다 |
| C3 | 재연결 뒤 제안 적용 거절 사유가 원인을 틀리게 말하지 않는다 (「만료」 제거, 「재연결」 명시) |
| C4 | 보류 저장소는 연결(세션 객체)마다 따로다. 연결 수명을 시험으로 고정한다 |

## 2. 증거 (Evidence)

### 2-1. RED — 수정 전 (시험만 추가·변경)

UI (`npm --prefix ui run test -- src/protocol.test.ts src/useCopilotSocket.test.ts`):

```
 FAIL  src/protocol.test.ts > clearOnDisconnect — beat-grid suggestion is connection-lifetime (t652) > drops a pending beat-grid suggestion on disconnect
 FAIL  src/useCopilotSocket.test.ts > reducer — disconnect clears stale pending cards > is the same single path as clearOnDisconnect — the suggestion card goes too (t652)
 Test Files  2 failed (2)
      Tests  2 failed | 141 passed (143)
```

서버 (`uv run pytest -q server/tests/test_beat_grid_field_life_t651.py`):

```
FAILED server/tests/test_beat_grid_field_life_t651.py::TestPendingSuggestionAcrossReconnect::test_apply_after_reconnect_is_refused_with_a_misleading_reason
E         '만료' is contained here:
E           (이미 적용됐거나 만료됐습니다). 콘솔에는 아무것도 쓰지 않았습니다.", "commands": []}
1 failed, 10 passed, 1 warning in 2.82s
```

### 2-2. GREEN — 수정 후 (대상 시험)

```
UI:    Test Files  2 passed (2)   Tests  143 passed (143)
서버:  11 passed, 1 warning in 1.20s
```

### 2-3. CI 재현 — 전체

| CI 단계 | 명령 | 결과 (출력 요약 그대로) |
|---|---|---|
| UI 시험 | `npm --prefix ui run test` | `Test Files  60 passed (60)` / `Tests  1278 passed (1278)` |
| UI 빌드 | `npm --prefix ui run build` | `tsc && vite build` 성공 · `✓ built in 389ms` |
| 서버 시험 | `uv run pytest -q -rs` | `15730 passed, 33 skipped, 1 warning in 205.60s (0:03:25)` |
| 린트 | `uv run ruff check <변경 파일 2개>` | `All checks passed!` |

서버 전체 시험은 두 번 돌렸다. 첫 실행에서 `test_overlap_preserve.py::TestTouchedFilesPassLint` 1건이 실패했다 (`E501 Line too long (102 > 100)`, `session.py:4164`). 내가 쓴 주석 한 줄이었고, 두 줄로 나눠 고쳤다. 나눈 뒤 전체를 다시 돌려 위 결과를 얻었다.

### 2-4. 변경 범위

```
 server/tests/test_beat_grid_field_life_t651.py |  26 ++++++++++++++++++++------
 server/web/session.py                          |   7 ++++++-
 ui/src/protocol.test.ts                        |  16 ++++++++++++++++
 ui/src/protocol.ts                             |  25 +++++++++++++++++--------
 ui/src/useCopilotSocket.test.ts                |  23 ++++++++++++++++++++-
 ui/src/useCopilotSocket.ts                     |   4 ++--
 6 files changed, 83 insertions(+), 18 deletions(-)
```

## 3. 기준선 귀속 (Baseline-attribution)

- `git fetch origin main` 후 `origin/main` = `3f67e525` (워크트리 생성 전에 확인).
- `git worktree add -b WT-drop-suggestion <t652> origin/main` 직후 `HEAD is now at 3f67e525`.
- 모든 실행은 `.claude/worktrees/t652`에서, 위 변경 6개 파일을 포함한 트리 상태로 수행했다.
- 의존성: `npm --prefix ui ci` (`added 101 packages`), `uv sync` (새 워크트리의 `.venv`).

## 4. 범위 경계 (Scope boundary)

- 콘솔 쓰기 경로(`beat_grid_edit`와 그 호출부)는 바꾸지 않았다.
- `session.py` 변경은 주석 4줄과 **제안 없음(찾을 수 없음) 거절 문구 1줄**뿐이다. `beat_grid_suggestion_apply`의 성공 경로(`return self.beat_grid_edit(...)`)는 그대로다. `git diff -- server/web/session.py`로 확인했다.
- 클라이언트의 `clearPendingRequests`는 모듈 내부 함수가 되었다. 외부 참조는 없다. `git grep clearPendingRequests -- ui/src`의 결과는 `protocol.ts` 안의 정의와 `clearOnDisconnect` 내부 호출 두 줄뿐이다.

## 5. 미검증 (Gaps)

- 실제 앱 화면에서 재연결을 눌러 보지 않았다. 검증은 리듀서와 서버 시험 수준이다.
- 끊김 경로를 `clearOnDisconnect`로 일원화하면서, 운영 끊김 때 실행 상태 비우기와 최신 표시 해제가 새로 실제로 적용된다. 이 효과들은 기존 `clearOnDisconnect` 시험 묶음으로 고정되어 있지만, 화면에서의 체감은 확인하지 않았다.
- PR의 CI 결과는 이 문서 작성 시점에 아직 없다.

## 6. 잔여 위험 (Residual-risk)

- 거절 문구는 가능한 원인을 나열한다. 서버는 재연결을 알 수 없어서 원인을 확정하지 못한다. 그래서 「…일 수 있습니다」로 쓰았다.
- 다른 워크트리(t651 등)와 메인 체크아웃은 건드리지 않았다.
