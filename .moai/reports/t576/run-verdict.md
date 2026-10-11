# 카드 t576 — run 판정 (SPEC-LDBEAT-001 0.5.0, REQ-006 entry·011~013)

- 할 일: 박자 격자 에미터가 칸의 전환 `entry`를 콘솔 큐 명령에 싣게 한다. 박을 초로 바꾸는 일은 송신 때 곡 BPM으로 하고, 저장은 음악 단위 그대로 둔다. 실기 미확인 필드는 보내지 않고 이유를 표시한다.
- 트리: `.claude/worktrees/t576`, 브랜치 `WT-emit-entry`, 기준 `origin/main` `46e4fb27`(검증 시점 main과 동일, 합칠 것 없음)
- 실기 콘솔 쓰기: 0. 게이트·승인=송신 대조는 손대지 않았다(새 줄도 같은 승인 묶음에 들어감).

## 1. 필드별 처리 — 저장소 실기 선례부터

| entry 필드 | 콘솔로 보내는 모양 | 선례 | 비고 |
|---|---|---|---|
| `fade_bars` | `Store Cue k Sequence s CueFade <마디×박×60/BPM>` | `CueFade` 키워드: `cue_fade.store_with_fade`(실측 `Store Sequence S Cue N CueFade x /Merge`) | ⚠ 어순 미측정(아래) |
| `fade_beats` | `… CueFade <박×60/BPM>` | 위와 같음 | `fade_bars`와 둘 다 숫자면 그 칸을 막음(짐작 안 함) |
| `trigger_beat` | `TrigTime` = 마디 시작 + (박−1)×60/BPM | `TrigTime`(t549 에미터) | 1~마디당 박 밖이면 그 칸을 막음. 미정 = 1박(지금과 같음) |
| `tracking` Release | 저장 뒤 `Set Cue k Sequence s Property 'Release' 1` | `cue_sheet_apply._tracking_command`(t469 실측) — 함수를 그대로 import | |
| `tracking` Block | 저장 뒤 `Block Sequence s Cue k` | 같음 | |
| `tracking` Cue Only | 저장 옵션 `/CueOnly` (`CueFade` 뒤) | 같음(t469, 실측 순서: 키워드 뒤 옵션) | 되돌리는 명령 없음(t469와 같은 성질) |
| `tracking` Track | 없음 | 콘솔 기본값 | |
| `delay_beats` | **보내지 않음** + 이유 | 선례 0건 | t580 실기 확인 뒤 |
| `position_late_beats` | **보내지 않음** + 이유 | 선례 0건 | t580 실기 확인 뒤 |
| `mib_mode`(none 제외) | **보내지 않음** + 이유 | `cue_sheet_apply`도 "MIB는 콘솔 값이 아니다"로 안 보냄 | 앱이 사전이동 큐를 넣는 방식이라 |

- **초는 저장하지 않는다**: 초 환산은 `_entry_plan`에서 송신할 때만 한다. 시험이 저장된 `entry`가 바뀌지 않음을 확인한다.
- **entry가 비면 바이트 동일**: 시험이 t549 때의 다섯 줄과 정확히 같음을 확인한다.
- **이유를 보여 주는 곳**: 보내지 않은 칸은 `CueEmitResult.skipped_fields`에 실린다. 승인 카드 `risk_reasons`에도 「보내지 않은 전환 칸 N개: 트랙 마디(이유)」로 나온다 — 감독이 승인 전에 본다.
- **t572와 맞물림**: 다시 반영의 `/Overwrite`는 원래 `Store Cue k Sequence s`와 **똑같은 줄**에만 붙었다. 그래서 페이드·`/CueOnly`가 붙으면 덮어쓰기가 빠지는 문제가 있었다. 이제 같은 줄이거나 공백으로 이어지는 줄에 맨 끝으로 붙인다(`… CueFade 4 /CueOnly /Overwrite`). `Sequence 1`과 `Sequence 10`이 섞이지 않게 공백 경계로 고른다.

## 2. 증거 (이 트리에서 직접 잼)

| 주장 | 명령 | 관측 |
|---|---|---|
| 새 시험이 먼저 실패 | `uv run pytest -q server/tests/test_beat_grid_emit_entry_t576.py`(구현 전) | `16 failed, 3 passed` |
| 새 시험 통과 | 같은 명령 | `20 passed` |
| 관련 시험 | `… test_beat_grid_emit_entry_t576.py test_beat_grid_emit_t549.py test_beat_grid_reapply_t572.py test_beat_grid_send_t563.py test_web_beat_grid_send_t563.py` | `109 passed`(세션 시험 추가 전) |
| 뮤테이션 확인 | 저장 줄에 페이드를 안 싣게(`entry_plan.fade_seconds` → `None`) 바꿔 실행 → 원복 | 바꾼 상태 `6 failed, 14 passed` · 원복 `20 passed` |
| 세션 경로 | `TestSessionApplyCarriesEntry` | 페이드·Block 줄이 승인 묶음 1개 안에 있고 그대로 송신, `approval_vs_sent.match = True`, 딜레이 0줄, 승인 카드에 「보내지 않은 전환 칸 1개 … delay_beats」 |
| 린트 | `uv run ruff check` / `ruff format --check`(바뀐 4파일) | `All checks passed!` / formatted |
| 서버 전량(CI 순서) | `npm --prefix ui run build` → `uv run pytest -q -rs` | `15215 passed, 33 skipped` exit 0 |

UI 파일은 바꾸지 않았다.

## 3. 안 잰 것 (Gaps) — t580 실기 확인 목록에 올릴 줄

1. **`Store Cue k Sequence s CueFade x`(+ `/CueOnly`) 어순**: `CueFade` 키워드는 실측됐지만 실측 문면의 어순은 `Store Sequence S Cue N …`이다. 이 에미터의 어순과 붙인 선례는 0건이다. `@MX:WARN`을 달았다.
2. **트래킹 표시가 다시 반영(`/Overwrite`) 뒤에도 남는지**: Block→Track으로 바꿔 다시 반영할 때 이 에미터는 Track이면 아무것도 보내지 않는다(Unblock 안 보냄). `/Overwrite`가 큐의 Block 표시를 지우는지 모르므로, 옛 Block이 남을 수 있다. Release도 같다.
3. `delay_beats`·`position_late_beats`의 콘솔 문법(보내지 않음 — 실기 확인 뒤 별도 카드).
4. 실기 콘솔 왕복 0회.

## 4. 남은 위험

- `trigger_beat`이 마디 안에서 트리거를 미루면 `TrigTime`이 마디 시작보다 뒤가 된다. 다음 마디 큐의 트리거보다 늦어질 수는 없다(박 ≤ 마디당 박). 다만 이 칸의 페이드 길이가 다음 칸 트리거를 넘는 겹침은 검사하지 않는다(화면 경고 영역, REQ-020).
- MIB를 보내지 않는 판단은 큐시트 선례를 따른 것이다. 박자 격자에서 「앱이 위치 전용 큐를 삽입」(REQ-020)하는 기능은 아직 없다 — 그 기능이 생기기 전까지 `mib_mode`는 승인 카드에 "보내지 않음"으로만 보인다.
