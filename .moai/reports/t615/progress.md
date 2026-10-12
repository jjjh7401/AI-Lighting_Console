# 카드 t615 — 빈 트랙 시퀀스의 자동 Cue 1 (진행 기록)

- 상태: **구현과 전체 시험 녹색.** 리드 결정 (A)「승인하면서 보내기」를 반영했다. 커밋·푸시·PR·CI·머지는 이 기록을 포함해 한 번에 진행한다.
- 콘솔 송신: 0건. 이 세션은 콘솔에 아무것도 보내지 않았다.
- 기준: `1973c481` (= origin/main). 브랜치 `WT-empty-track-cue` (`worktree-t615` 에서 `git branch -m` 으로 개명).
- 변경 파일 (12개 + 이 기록):
  - `server/design/beat_grid_emit.py` — 저장 큐 0개 트랙의 방출 중단 (본 수정). 타임코드 설정 줄도 그런 타임코드에는 내지 않는다.
  - `server/design/beat_grid.py` — `approval_preview_tracks` 추가 (승인 카드 미리보기 사본. 기존 함수는 바꾸지 않음).
  - `server/web/session.py` — 반영 흐름: 미리보기 사본으로 방출, 만들기 줄 기준의 거절 조건, 보류 사유를 거절 사유에 싣기.
  - `server/tests/test_beat_grid_empty_track_t615.py` — 신규 재현 시험 5개.
  - `server/tests/test_beat_grid_store_order_t612.py`, `server/tests/test_beat_grid_emit_t549.py`, `server/tests/test_beat_grid_timecode_track_t614.py` — 옛 계약에 기댄 시험을 새 계약으로 갱신.
  - `server/tests/test_empty_preset_hold_t590.py`, `server/tests/test_position_preset_create_t592.py`, `server/tests/test_effect_preset_create_t593.py`, `server/tests/test_new_color_preset_t594.py`, `server/tests/test_new_preset_dialog_t589.py` — 보류 전용 반영의 기대를 「거절 + 사유」로 갱신 (15곳, 4절).
  - `.moai/reports/t615/progress.md` — 이 기록.

## 1. 주장 (Claim)

1. 저장 큐가 하나도 없는 트랙은 시퀀스·이름·배정·타임코드 설정 줄을 내지 않고, 배정 순번 `k` 를 쓰지 않는다. — 재현 시험 빨강→녹색으로 검증.
2. 맨 `Store Sequence S` 단독이 빈 Cue 1 을 만든다. — 리드의 실기 판별을 원본 기록으로 확인.
3. 승인 대기 칸은 승인 카드에 실린 줄과 함께 한 번에 승인되고 보내진다 (A). 게이트 계약(`check_evidence_approval`, `apply_pending_approval`, `build_write_approval_batch`, 승인 디스패치)은 바꾸지 않았다. — 관련 시험과 전체 시험으로 검증.
4. 보낼 줄이 하나도 없는 반영은 승인 카드를 올리지 않고 거절하며, 보류 칸의 사유를 거절 사유에 싣는다. — 15개 시험 기대 변경으로 검증 (4절).

## 2. 근거 (Evidence)

**a. 실기 판별 (리드 기록 원본 확인).** `.moai/reports/t615/live/` (primary 체크아웃, UTC 13:41).

- `run-p1-store.jsonl`: `Store Sequence 790` 단독 → `ok`, `OK` (13:41:08.921). `readback.txt` 1행: 자식 `OffCue`, `CueZero`, `Cue 1`. 노드 이름은 `Sequence 790` (Name 줄은 나가지 않음; `p2-name.txt` 는 실행 기록이 없다).
- `run-p3-cue2.jsonl`: `Store Sequence 790 Cue 2` → `ok` (13:41:16.188). `readback.txt` 2행: `OffCue`, `CueZero`, `Cue 1`, `Cue 2`.
- `run-p9-cleanup.jsonl`: `Delete Sequence 790 /NoConfirm` → `ok`. `readback.txt` 3행: `path segment not found`.
- 주의: 「Cue 1 재저장은 S4 에서 User Canceled」는 v3 `run-S4`(702)의 기록이다. p 시리즈에는 Cue 1 재저장 시험이 없다. 「충돌은 Cue 1 에만」은 790(Cue 2 성공)과 702(Cue 1 취소)를 맞춰 본 추론이다.

**b. 재현 시험 — 빨강 → 녹색.** `uv run pytest -q -rf --tb=line server/tests/test_beat_grid_empty_track_t615.py server/tests/test_beat_grid_store_order_t612.py`

- 빨강 (방출 수정 전): `6 failed, 4 passed`. 빈 트랙이 `Store Sequence 700`, `Set Sequence 700 Property 'Name' …`, `Assign Sequence 700 At Timecode 70.1.1`, `Store Timecode 70` 을 내는 것을 가리켰다.
- 녹색 (방출 수정 후): `10 passed`.

**c. 방출 줄 전후.** 저장 큐 0개 트랙 (FOH, 시퀀스 700, 타임코드 70).

- 전: `Store Sequence 700` · `Set Sequence 700 Property 'Name' 'LDBEAT FOH'` · `Assign Sequence 700 At Timecode 70.1.1`, 타임코드 설정 `Store Timecode 70` · `Set Timecode 70 Property 'Name' …` · `Store Timecode 70.1`.
- 후: 줄 없음 (`commands == ()`). 칸별 사유 (`cues[].blocked_reason`)는 그대로 남는다.
- 같은 타임코드의 둘째 트랙 (칸 있음): 전 `…70.1.2` → 후 `…70.1.1`.

**d. 승인 흐름 (A) — 구현 내용.**

- 방출 입력을 `approval_preview_tracks(tracks, pending_before, held_presets)` 로 바꿨다. 승인 대기 칸 가운데 보류가 걸리지 않고, 열거된 (필드, 번호)가 그 칸의 승인 대기 전부인 칸만 「승인되었다고 가정한」 `evidence.approval` 을 단 **사본**으로 방출된다. 원본 격자와 게이트 함수는 그대로다. 사본은 방출기에 넘겨 줄을 만드는 데만 쓰고 저장하지 않는다.
- 승인 카드(`cells`)에 그 줄이 실린다. 승인이 통과하면 같은 묶음이 나가고, 기존 로직이 `apply_pending_approval` 로 같은 칸의 증거를 적는다 (`apply_pending_approval` 의 조건과 미리보기 조건이 같다).
- 거절 조건: 보낼 줄도 만들기 줄도 없으면 거절. 보류 칸이 있으면 사유를 거절 사유에 싣는다 (「콘솔에 반영할 내용이 없습니다 · 빈 프리셋 — …(송신 보류) N개: …」).

**e. 보류 전용 반영의 시험 기대 변경 (15곳).** 옛 방출은 보낼 칸이 하나도 없는 반영도 맨 Store 줄 덕분에 승인 카드를 열었다. 게이트는 줄이 있어야 받으므로, 줄 없는 카드는 만들 수 없다. 그래서 이런 반영은 승인 카드 없이 거절하고, 보류 사유는 거절 사유로 옮겼다.

- t589: 직접 고른 새 번호 (1). 
- t590: 빈 번호 보류 (카드 목록, 풀 읽기 실패, 칸 전체 보류, 「보류 칸은 송신으로 세지 않음」은 `approval_vs_sent is None` 과 콘솔 쓰기 0건으로 바꿈) (4).
- t592: 위치 풀 읽기 실패, 레시피 없음 (2).
- t593: 효과 풀 읽기 실패, 레시피 없음 (2).
- t594: 색 프리셋 풀 읽기 실패, 여러 그룹, 멤버 읽기 실패, 채널 읽기 실패, CMY 전용, RGB 누락 (6).
- 각 시험은 같은 안전 단언을 유지한다: 콘솔 쓰기 0건, 보류 번호 미송신, 증거 미기록. 바뀐 것은 승인 카드를 찾던 단언을 거절 사유 단언으로 바꾼 것이다.

**f. 시험 결과.**

- 관련 시험 (`server/tests/test_beat_grid_*.py`, `test_web_beat_grid_*.py`, `test_approved_empty_hold_t600.py`): `441 passed`.
- 승인 흐름 2건 (t563 `test_apply_resets_pending_count_and_approved_vs_sent_matches`, t600 `test_pending_cell_still_gets_recorded_alongside`): 녹색.
- 보류 시험 5개 파일 (t589, t590, t592, t593, t594): `198 passed`.
- 전체 서버 시험 (`uv run pytest -q -rf --tb=line server/tests`): `15698 passed, 35 skipped, 0 failed` (215 s).
- 린트: `uv run ruff check` (변경 12개 파일) → `All checks passed!`. `uv run ruff format --check` → `12 files already formatted`.

## 3. 기준 귀속 (Baseline-attribution)

- 시험·린트 출력: 이 worktree 에서 이번 세션이 실행한 명령과 그 원문. 기준 `1973c481` + 위 변경분.
- 실기 기록: 리드가 남긴 원본 파일을 직접 읽어 확인했다 (2a).
- 옛 사례 (t612 시험 머리글, 메모리의 2/2 취소)는 인용이다. 재측정하지 않았다.

## 4. 리드 결정과 판단 사항

- 리드 결정 (2026-10-12): (A) 「승인하면서 보내기」. 게이트 계약 변경 금지. 판단 사항 3건 승인: (i) 빈 타임코드의 설정 줄 미방출, (ii) 빈 트랙은 타임코드 상한 계산에 계속 셈, (iii) `store_sequence_commands` 정리는 후속.
- 증거 기록 순서 (리드 말: 「승인 뒤 증거를 남긴 다음 같은 묶음으로 보낸다」): 구현은 **승인 통과 → 송신 → 송신 성공 뒤 증거 기록**이다. 기존 순서를 그대로 두었다. 게이트의 승인과 실행이 한 호출 (`_dispatch_declared`)에 묶여 있어, 증거를 송신 앞에 적으려면 게이트 호출을 쪼개야 한다. 그것은 게이트 계약 변경이라 하지 않았다. 송신이 실패하면 증거는 적히지 않는다 (기존 동작).
- 판단 사항 (리드 승인 범위 안): 타임코드 설정 줄은 저장 큐 0개 트랙만 쓰는 타임코드에 내지 않는다. 빈 트랙은 상한 계산에 계속 센다 (보수적, 기존 동작). `store_sequence_commands` 는 항상 빈 튜플이다 (필드 호환을 위해 남김, 정리는 후속).

## 5. 미검증 (Gaps)

- 콘솔 재확인: 방출·승인 흐름 변경 후 실기 동작은 측정하지 않았다 (콘솔 송신 금지).
- 승인 카드의 화면 표시: 카드가 미리보기 줄을 어떻게 보여 주는지는 시험하지 않았다 (시험은 카드의 위험 사유 문구와 승인 요청 수로 확인).
- 790 사전 부재 되읽기 기록은 없다 (OK 응답으로 추정).
- 「충돌은 Cue 1 에만」: 서로 다른 두 기록 (790, 702)을 맞춘 추론이다.
- 컨텍스트 사용률: 측정 불가. `.moai/state/context-usage.json` 의 `session_id` 가 `bef0579d-…` 로 이 세션 (`0c96e895-…`)과 달라 읽지 않았다.

## 6. 잔여 위험 (Residual risk)

- 증거가 송신 뒤에 적히므로, 송신 직후·증거 기록 전에 프로세스가 끊기면 콘솔에는 줄이 있고 앱은 승인 대기로 본다. 다음 반영에서 같은 칸이 승인 카드에 다시 오르고, 재승인 뒤 같은 줄이 다시 나간다. 같은 번호에 같은 줄을 다시 쓰는 경로가 되므로, 이 경우의 콘솔 동작은 실기에서 확인해야 한다.
- 보낼 칸이 하나도 없는 반영의 거절 사유 문구가 바뀌었다. 운영자가 보던 승인 카드 대신 거절 사유로 보류를 본다.
- 이미 콘솔에 남은 빈 시퀀스 (옛 적용이 만든 자동 Cue 1)의 재반영은 여전히 충돌한다. 범위 밖이다 (7절).

## 7. 후속 (리드가 생성한 카드)

- t616 (또는 리드가 붙인 번호): 재반영 때 콘솔에 이미 있는 빈 시퀀스 (자동 Cue 1) 처리. /Overwrite 또는 소유 기록. 되읽기로 큐 내용이 안 보이므로 설계 결정이 먼저다.
- t617 (또는 리드가 붙인 번호): `store_sequence_commands` 필드 정리 (항상 빈 튜플). 소비자 두 곳 (`beat_grid_send`, `web/session`)을 함께 고친다.

## 8. 기록 원본

- `.moai/reports/t615/live/` (primary 체크아웃): 리드가 남긴 실기 기록 (p1·p3·p9, readback).
- `.moai/reports/t608/v3/` (primary 체크아웃): 이전 판별 기록 (S1b·S4·probe-after-S1b).
