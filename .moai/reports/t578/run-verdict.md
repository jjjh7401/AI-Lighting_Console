# 카드 t578 — run 판정 (SPEC-LDBEAT-001 REQ-LDBEAT-024(a) 「콘솔 같이」)

- 할 일: 플레이 묶음의 「콘솔 같이」를 켜면 게이트를 거쳐 타임코드 재생·정지를 보낸다. 음원은 `console_audio_offset.yaml`의 실측 지연 뒤에 시작한다.
- 트리: `.claude/worktrees/t578`, 브랜치 `WT-console-sync-play`, 기준 `origin/main` `aa4ef279`(검증 시점 main과 동일)
- 실기 콘솔 쓰기: 0. 새 생쓰기 경로: 0 — t563 미리보기 길(`_beat_grid_dispatch_preview`: 세션 시작 1회 승인 → `run_commands` → 게이트)을 그대로 쓴다.

## 1. 명령 문면 — 저장소 실측 선례 (`.moai/reports/t520/verdict.md`)

| 동작 | 보내는 줄 | 선례 |
|---|---|---|
| ▶ (콘솔 같이 켬) | `Top Timecode N` → `Go Timecode N` | `Top Timecode N` → CURSOR 0.00(§20-1, 이 콘솔 첫 측정) · `Go Timecode` 송신 OK(t520 b2r 묶음, t512 대조 PASS) |
| ❚❚ (콘솔 같이 켬) | `Off Timecode N` | `Off Timecode N`(t520 §19-2 — 커서를 되감지 않음) |

`Off`가 되감지 않으므로 재생은 늘 `Top` 다음 `Go`다. 그래서 「콘솔 같이」 재생은 곡 처음부터 시작한다(중간 위치에서 이어 재생하는 문면은 선례가 없다).

## 2. 타임코드 번호

- **출처**: t572 소유 기록(`SongTimelineStore.beat_grid_allocation`)에서만 가져온다. 번호를 지어내지 않는다.
- **기록이 없을 때**: 거절하고 「먼저 ⇪ 콘솔에 반영」 이유를 돌려준다. 콘솔 0줄.
- **기록이 있을 때**: 콘솔의 그 타임코드 이름이 기록과 같은지 `_resolve_beat_grid_timecode_number`(`timecode_slot_verdict`)로 확인한다.
  - 다르면 → 남의 객체로 보고 거절, 콘솔 0줄.
  - 비었으면 → 기록이 낡았다고 보고 거절, 콘솔 0줄.

## 3. UI 흐름

1. 토글 「콘솔 같이 끔/켬」은 App이 송신 함수 둘(`onConsolePlay`·`onConsoleStop`)을 넘길 때만 켤 수 있다. 안 넘기면 기존처럼 비활성 + 이유.
2. 켬 + ▶ → 서버에 `beat_grid_console_play`를 보낸다. 음원은 여기서 틀지 않는다.
3. `beat_grid_send_status`(`last_action: "console_play"`)가 오면 `resolveConsolePlayResponse`(순수 함수)가 판단한다.
   - 성공 → 시계를 0초에 두고, `console_audio_offset_seconds`(서버 데이터 파일) 만큼 기다렸다 음원·시계를 0초부터 시작한다.
   - 거절 → 그 이유를 토글 옆에 보이고, 음원만 따로 틀지 않는다.
   - 성공인데 지연 측정값이 없음 → 지어내지 않고 거절과 똑같이 멈춘다.
4. **낡은 응답 오인 방지**: 서버 응답은 상태에 마지막 하나로 덮어써진다. 그래서 「기다리는 중」을 ref로 두고, **새 응답이 도착할 때만** 판단한다. 이전 재생 응답이 남아 있어도 ▶ 를 누르는 순간 바로 음원을 틀지 않는다.
5. 켬 + ❚❚ → 음원을 멈추고, 걸려 있던 음원 시작 타이머를 지우고, `beat_grid_console_stop`을 보낸다.

## 4. 증거 (이 트리에서 직접 잼)

| 주장 | 명령 | 관측 |
|---|---|---|
| 서버 시험이 먼저 실패 | `uv run pytest -q server/tests/test_beat_grid_console_play_t578.py`(구현 전) | `6 failed` |
| 서버 시험 | 같은 파일 + `test_web_beat_grid_console_play_t578.py` | `9 passed` (세션 6 + WS 왕복 3) |
| 게이트 목록 | `test_prechk_tool.py`·`test_write_dispatch_census.py`·`test_web_beat_grid_send_t563.py` 함께 | `97 passed, 1 skipped` |
| **뮤테이션 확인** | 재생 명령에서 `Top`을 빼고(`("Go",)`) 실행 → 원복 | 뺀 상태 `2 failed, 7 passed` · 원복 `9 passed` |
| UI 판단 함수 | `consoleSyncAudio.test.ts` | `9 passed` |
| UI 전량 | `npm --prefix ui run test` | `Test Files 52 passed` · `Tests 1142 passed` |
| 빌드(tsc 포함) | `npm --prefix ui run build` | 통과 |
| 린트 | `ruff check` / `ruff format --check`(바뀐 서버 6파일) | 통과 |
| 서버 전량(CI 순서) | `uv run pytest -q -rs` | `15224 passed, 33 skipped` exit 0 |

새 WS 타입 2개(`beat_grid_console_play`·`beat_grid_console_stop`)를 `test_prechk_tool.py` 고정 목록에 올렸다. 쓰기 진입점 조사표(`test_write_dispatch_census.py`)는 바꾸지 않았다 — 새 메서드는 이미 등재된 `_beat_grid_dispatch_preview`를 부르므로 새 디스패치 자리가 없다(시험 통과로 확인).

## 5. 🔴 전제 위험 — 리드 판단 / t581 실기 확인

**3.002초 지연이 박자 격자 타임코드에 맞는 값인지 모른다.** 카드 지시대로 `console_audio_offset.yaml` 값을 그대로 쓰지만, 두 가지가 어긋난다.

- **측정한 쇼가 다르다**: 그 값은 t520 쇼에서 잰 것이다. t520은 「타임코드 시각 = 음악 시각 + 3초(LEAD)」로 앞에 3초를 일부러 비운 쇼였다(t520 verdict 105행).
- **박자 격자 에미터는 그 여유가 없다**: 큐의 `TrigTime`을 음원 시각(`bar_map`의 `start_ms`) 그대로 적는다. LEAD가 없다.
- **결과**: 이 조합에서는 음원을 3.002초 늦게 틀면 조명이 음악보다 약 3초 빠를 수 있다.
- **더 근본적인 미확인**: 에미터의 큐는 `TrigType 'Time'`이고, 타임코드에는 `Assign Sequence … At Timecode`만 한다. 그래서 `Go Timecode`가 이 큐들을 실제 시각에 맞춰 부르는지 자체가 실기로 확인되지 않았다.

그래서 실기 확인 순서를 이렇게 제안한다: ① 박자 격자로 반영한 곡에서 `Top`/`Go Timecode` 뒤 첫 큐가 몇 초에 서는지 재기 ② 그 값으로 `console_audio_offset.yaml`(또는 곡별 값)을 다시 정하기.

## 6. 안 잰 것 (Gaps)

- 실기 콘솔 왕복 0회(위 전제 포함).
- 브라우저에서 실제로 토글을 눌러 3초 뒤 음원이 나는지(DOM 시험대가 없어 판단 함수와 정적 마크업까지만 시험했다).
- 재생 중 다른 곡으로 바꾸거나 화면을 떠날 때 콘솔 타임코드를 자동으로 끄지는 않는다(음원 타이머만 지운다).
- `Top`이 안 되는(점유자 이름은 맞지만 다른 쇼로 바뀐) 경우의 커서 확인은 하지 않는다 — t520 실행기는 `Go` 전에 CURSOR가 0 근처인지 읽었지만, 이 경로는 읽지 않는다.
