# 카드 t572 — run 판정 (SPEC-LDBEAT-001 REQ-011~013, 「다시 반영」 정책)

- 리드 결정: 다시 반영 = 이 앱이 이 곡에 직전에 써 넣은 시퀀스·타임코드 번호에만 덮어쓰기. 앱이 만들지 않은 객체는 거절 + 이유. 기록은 곡별로 서버에.
- 트리: `.claude/worktrees/t572`, 브랜치 `WT-reapply-overwrite`, 기준 `3e118327` → main 9커밋을 합침(충돌 0)
- 게이트·승인=송신 대조: 바꾸지 않았다. 실기 콘솔 쓰기: 0

## 1. 소유 기록

- **어디에**: `SongTimelineStore`의 새 키 `beat_grid_allocations`. 사용자 데이터 폴더 JSON에 원자적으로 저장된다. 셋리스트의 `setlist_sequence_nos`와 같은 "실행된 할당" 기록이다. 곡 파일이나 격자 데이터에는 넣지 않았다(t563 때 리드가 기각한 B안).
- **모양**(곡 키 = `_beat_grid_song_key`, §6에서 `cues` = {마디: 큐 번호}로 바뀜):
  ```json
  {"timecode_number": 20, "timecode_name": "LDBEAT Timecode 20",
   "tracks": {"BACK": {"sequence_number": 1, "sequence_name": "LDBEAT BACK", "cues": {"1": 1, "2": 2}}}}
  ```
- **이름 한 곳에서**: 에미터가 쓰는 이름을 `beat_grid_sequence_label()`·`beat_grid_timecode_label()`로 뽑아 냈다. 기록·비교·생성이 같은 함수를 쓰므로 서로 어긋날 수 없다.
- **언제 쓰나**: 승인=송신 대조가 맞을 때만. 거절·막힘이면 기록은 그대로다.

## 2. 다시 반영의 명령 모양

| 대상 | 첫 반영 | 다시 반영(소유 확인 통과) |
|---|---|---|
| 소유 시퀀스 | `Store Sequence s` + 이름 | `Store Sequence` 뺌, 이름 줄만 |
| 소유 타임코드 | `Store Timecode m` + 이름 | 둘 다 뺌 |
| 소유 트랙의 타임코드 배정 | `Assign Sequence s At Timecode m` | 뺌(다시 배정하면 트랙이 둘이 된다) |
| 소유 트랙의 큐 | `Store Cue k Sequence s` | `Store Cue k Sequence s /Overwrite` |
| 이번에 사라진 옛 큐 | — | `Delete Cue k Sequence s` |
| 새로 생긴 트랙 | 새 번호 | 새 번호 + `Store Sequence` + 소유 타임코드에 `Assign` |
| 기록엔 있지만 격자에서 빠진 트랙 | — | 건드리지 않음, 상태 메시지 `stale_tracks`로 알림 |

**거절**(전부 콘솔 0줄):
- 기록 없음 + 타임코드가 남의 것 점유
- 시퀀스 이름이 기록과 다름(두 이름을 같이 보여 줌)
- 기록한 시퀀스 번호가 콘솔에 없음
- 타임코드 점유자 이름이 다름
- 타임코드가 비어 있음(기록이 낡음 — 조용히 다시 만들지 않음)
- 풀을 못 읽거나 잘림

## 3. 증거 (이 트리에서 직접 잼)

| 주장 | 명령 | 관측 |
|---|---|---|
| 새 시험이 먼저 실패 | 구현 에이전트가 구현 파일을 되돌린 채 실행(보고 인용) | 15개 중 11개 실패 (`'SongTimelineStore' object has no attribute 'beat_grid_allocation'` 등) |
| 관련 시험 | `uv run pytest -q test_beat_grid_reapply_t572.py test_beat_grid_send_t563.py test_web_beat_grid_send_t563.py test_beat_grid_t532.py test_prechk_tool.py` | `151 passed` |
| **뮤테이션 확인** | `beat_grid_send.py`의 이름 비교를 `if False and …`로 끄고 t572 시험 실행 → 원복 | 끈 상태: `1 failed, 14 passed` (`test_record_exists_but_console_sequence_name_differs_is_refused`) · 원복 뒤 `15 passed` · `git status` 깨끗 |
| 서버 전량(CI 순서) | `npm --prefix ui run build` → `uv run pytest -q -rs` | `15186 passed, 33 skipped` exit 0 |
| UI 전량 | `npm --prefix ui run test` | `Test Files 47 passed` · `Tests 1075 passed` |
| 빌드 | `npm --prefix ui run build` | `✓ built in 433ms` |

t572 시험 15개 구성: 다시 반영 성공(번호 재사용·소유 객체 재생성 없음·`/Overwrite`·승인 묶음 1개·대조 일치) · 칸 삭제 → `Delete Cue` · 새 트랙 → 새 번호 + `Assign` · 거절 5갈래 · 기록 수명(거절·막힘 시 불변, 저장소 다시 열어도 유지, 두 곡 독립) · **타임코드 세 갈래(없음·점유·모름) 각각**(t563에서 비었던 칸).

## 4. 안 잰 것 (Gaps)

- **실기 미측정 명령 둘**: `Store Cue k Sequence s /Overwrite`와 `Delete Cue k Sequence s`. 이 저장소에서 실기로 확인된 선례가 0건이다. 기존 쓰기 경로들은 `/Overwrite`를 일부러 피하고 `/Merge`를 쓴다 — 게이트가 사람 승인으로 보내는 파괴적 옵션이기 때문이다. 다시 반영은 바로 그 승인을 받는 쪽이라 선택은 맞지만, 콘솔이 이 정확한 문법을 받는지는 모른다. 두 자리에 `@MX:WARN`을 달았다. **실기 확인 첫 항목으로 이 두 줄을 먼저 쏴 봐야 한다.**
- ~~승인≠송신 바이트 불일치일 때 기록이 안 바뀌는지 전용 시험 없음~~ → **§6에서 시험 추가**. 원래 문면: t563 때부터 있던 `if verdict.passed:` 분기를 그대로 탄다.
- 다시 반영 중 시퀀스 풀이 잘린 경우, 일부 트랙만 소유가 맞는 복합 경우는 전용 시험이 없다. 코드는 "하나라도 어긋나면 묶음 전체 거절"이다.
- UI는 바꾸지 않았다(`stale_tracks`는 상태 메시지에만 실었고, 화면에 띄우는 일은 하지 않았다).

## 5. 남은 위험 · 리드에게

1. ~~막힌 칸의 옛 큐가 지워진다~~ → **§6에서 해결**(리드 결정: 지우지 않음). 전에 보냈던 칸이 이번에 M1 게이트 등으로 막히면, 그 칸은 "이번에 안 내는 큐"로 잡혀 `Delete Cue`가 나간다. 게이트 판정이 뒤로 물러나는 경우에만 생기지만, 그 칸이 콘솔에서 사라진다. 막힌 칸의 옛 큐는 지우지 않고 남기는 쪽이 더 안전할 수 있다 — 결정이 필요하다.
2. ~~큐 번호가 밀린다~~ → **§6에서 해결**(마디에 번호 고정). 원래 문면: 그래서 칸이 앞쪽에 하나 끼면 뒤 큐들이 모두 한 칸씩 밀려 `/Overwrite`된다. 결과는 맞지만, 콘솔에서 손으로 큐에 붙여 둔 것이 있다면 번호가 바뀐다.
3. 기록 키는 `(곡 제목, 타임라인 시퀀스 번호)`다. 곡 제목을 바꾸면 새 곡으로 보고 기록이 없어진다 → 그 뒤 첫 반영은 "남의 객체"로 거절된다(안전한 쪽으로 실패).

## 6. 리드 결정 반영 — 막힌 칸의 옛 큐는 지우지도 덮어쓰지도 않는다 (2026-10-11 후속)

- **찾은 구조 문제**: 에미터는 보내는 칸에만 큐 번호를 1부터 차례로 매겼다(`beat_grid_emit.py` 옛 529-544행). 소유 기록은 번호 목록뿐이었다. 그래서 가운데 칸이 막히면 뒤 칸이 앞 번호로 당겨져 `/Overwrite`됐다 — Delete를 꺼도 막힌 칸의 옛 큐는 덮어쓰기로 사라졌다. 리드에게 보고했고, 아래 방식으로 승인받았다.
- **바꾼 것**:
  - 소유 기록 `tracks.<group>.cues = {마디: 큐 번호}`(옛 `cue_numbers` 목록 대체).
  - 에미터에 `recorded_cue_numbers` 인자를 추가했다. 기록된 마디는 같은 번호를 쓰고, 새 마디는 그 트랙 최대 번호 다음 정수를 받는다(소수점 번호 없음). 인자를 생략하면 지금과 똑같다.
  - `/Overwrite`는 기록된 마디에만 붙인다. `Delete Cue`는 **초안에서 정말 비워진 칸**(격자에서 빠짐 또는 낼 내용 없음)에만 나간다. 막힌 칸은 번호·기록 모두 그대로 둔다.
  - **트랙 통째 막힘도 보존한다**: 에미터가 칸 목록을 비워 돌려주는 경우다. 이걸 "다 비웠다"로 읽으면 전부 지우게 되는 구멍이 있었다.
  - 승인 카드(`risk_reasons`) 문구: 「막혀서 그대로 둔 칸 N개: 트랙 마디(사유)」 · 「번호 순서와 시간 순서가 다른 큐 N개」(리드 추가 지시).
  - **기존 버그 수정**: 반영 성공 시 격자의 모든 트랙을 기록하던 것을 "원래 소유했거나 이번에 실제로 만든 트랙"만 기록하게 바꿨다. 통째로 막힌 새 트랙을 기록하면, 다음 반영이 "기록한 시퀀스가 콘솔에 없다"로 영영 거절된다.
- **시험(+5, 합계 20)**:
  - 막힌 칸: Delete 0줄 + 그 번호에 다른 내용 덮어쓰기 0 + 뒤 칸은 원래 번호로 `/Overwrite` + 기록 유지 + 승인 카드 문구
  - 진짜 비운 칸: `Delete Cue`
  - 트랙 통째 막힘: Delete 0, 기록 그대로
  - 사이에 낀 새 마디: 최대+1 정수, 소수점 없음, 「순서 다른 큐 1개」
  - **승인≠송신 불일치 → 기록 불변**(§4의 빈칸을 채움)
- **뮤테이션 확인**: 에미터가 기록 번호를 무시하게(`recorded_number = None`) 바꾸면 `4 failed, 16 passed` → 원복 뒤 `20 passed`.
- **재검증**: `ruff check`·`format --check` 통과 · `npm --prefix ui run build` 통과 · `uv run pytest -q -rs` → `15191 passed, 33 skipped` exit 0. UI 파일은 바꾸지 않았다.
- **남는 것**: `/Overwrite`·`Delete Cue`의 실기 선례 0건은 그대로다(`@MX:WARN` 유지, 실기 확인 1번). 순서 어긋난 큐의 타임코드 재생은 실기 확인 2번(리드 기록).
