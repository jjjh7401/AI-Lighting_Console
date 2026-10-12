# t609 판정서 — 업로드 길에도 곡 사이 룩 피하기

- 카드: t609 (t491 에서 lane-3 이 찾은 빈자리, 감독 결정 2026-10-12 「앱이 스스로 피함」)
- 트리: `.claude/worktrees/t609`, 브랜치 `WT-upload-look-memory`, 기준 `fedd1e34` (= origin/main, 2026-10-12)
- 콘솔 접촉: 0건. 가짜 실행 포트·가짜 상태 포트만 썼다(t480 업로드 시험과 같은 하네스).
- 시험 쇼 값(색 이름·위치 이름)의 의미는 해석하지 않는다. 같은지 다른지만 센다.

## 1. 결론

**업로드 길(`prepare_songcue`)도 이제 한 쇼 안에서 연속 곡을 앞 곡과 다른 룩으로 연다.** 같은 답 8곡을 한 기억으로 올리면 이웃 쌍 첫 큐 같음이 7/7 → 0/7, 다음 곡 큐 중 앞 곡 룩 재사용이 67/99(68%) → 13/99(13%) 로 내려갔다. 대화 길(t491)과 숫자가 같다.

- 기억 창을 안 넘기면(오늘 main 의 업로드 길) 7/7 · 67/99 다. t491 이 적어 둔 「업로드 길은 효과 0」을 실행으로 확인했다.
- 곡마다 새 기억을 준 대조군도 7/7 · 67/99 다. 효과는 기억에서만 나온다.
- 세션은 대화 길이 쓰는 **그 목록**을 업로드 길에 넘긴다. 한 쇼의 기억은 하나다. 대화 길로 올린 곡 다음에 업로드 길로 올린 곡도 앞 곡을 피한다.

## 2. 측정 전후

`measure_upload_look_reuse.py` — t499 8곡(t491 과 같음), 룩 = `(position.stored, color.palette)`, 구간 큐만, 이웃 쌍 = 이름순 7쌍. 인터뷰 답은 t491 하네스로 대화 길 한 곡을 돌려 그 세션의 기록을 꺼내 8곡 모두에 넘겼다(같은 답). `preset_start` 를 줘서 포지션 축을 켰다.

| 실행 | 이웃 첫 큐 같음 | 다음 곡 재사용 | 룩 공유 이웃 쌍 | 전체 28쌍 첫 큐 같음 | 전체 28쌍 재사용 | 8곡 서로 다른 룩 |
|---|---|---|---|---|---|---|
| `none` — 기억 창 없음(구현 전 = 오늘 main) | 7/7 | 67/99 (68%) | 7 | 28 | 253/405 | 23 |
| `shared` — 8곡 한 기억(구현 후) | **0/7** | **13/99 (13%)** | 3 | 5 | 104/405 | 38 |
| `fresh` — 곡마다 새 기억(대조) | 7/7 | 67/99 | 7 | 28 | 253/405 | 23 |

원자료: `upload_look_reuse.json`, `measure_upload_look_reuse.stdout.txt`(exit 0).

곡별 첫 큐와 고른 오프셋(`shared`): Club Diver `Ring In/블루+cyan`(0) → Cut and Run `Home/cyan+블루`(1) → Ice cream `Vocal DSC/블루+cyan`(2) → Morning `Fan Out/블루+cyan`(6) → Rain `Ring In/블루+cyan`(8, 바닥남 — 가장 오래전 룩) → Too Cool `Home/cyan+블루`(1) → scott-buckley-neon `Vocal DSC/블루+cyan`(2) → 걸그룹DinoDino `Ring In/블루+cyan`(16). 8곡 모두 저장 성공(`executed: true`), 기억 길이 1→8.

대화 길(t491) 숫자와 같은 이유: 두 길은 같은 계획 조립 함수(`_build_unified_song_plan`)를 같은 답으로 부른다 — t480 시험이 「같은 입력이면 같은 계획」을 이미 고정했다. 같은 숫자는 업로드 길이 대화 길과 **같은 고르기**를 탄다는 확인이다.

**대화 길 회귀 확인:** 반복문을 공용 함수로 옮긴 뒤 t491 측정 스크립트를 다시 돌렸다 — `fixed/same_session` 이웃 0/7 · 13/99 그대로, t491 결과 파일은 바이트 동일(`git status` 변경 없음).

## 3. 무엇을 바꿨나

| 자리 | 바꾼 것 |
|---|---|
| `server/design/song_look_memory.py` | `compose_avoiding_previous(build, history, enabled)` — t491 이 `session._song_compose` 안에 둔 「오프셋 0,1,2 … 조립 → 회전 한 바퀴에서 멈춤 → 고르기」 반복문을 옮겼다. 두 길이 같은 함수를 쓴다 |
| `server/web/session.py` `_song_compose` | 위 공용 함수를 부른다(동작 같음) |
| `server/design/upload_song_plan.py` `build_upload_song_plan` | `look_offset`(기본 0)을 `_build_unified_song_plan` 에 넘긴다 |
| `server/orchestrator/tools.py` | `SongLookMemoryPort`(창 — `history` 목록 하나), `build_toolset(song_look_memory=)` 인자 |
| `tools.py` `prepare_songcue` | 공용 함수로 오프셋을 골라 조립. 콘솔 저장이 끝난 곡만 기억에 덧붙임(오류·감독 거절이면 안 넣음). 회신에 `look_offset`, 돌렸으면 `look_note_ko`(끄는 문구 포함) |
| `prepare_songcue` 도구 인자 | `avoid_previous_looks`(불리언, 기본 켬) — 업로드 길에는 계획 수정 단계가 없어서 곡별 끔을 도구 인자로 뒀다. 운영자가 「앞 곡 룩 허용」이라고 하면 모델이 false 로 넘긴다 |
| `session.py` | `_SongLookMemoryView` — 세션의 `_song_look_history` 목록 자체를 돌려준다. `build_toolset` 에 넘긴다 |

기억 범위·바닥나면 가장 오래전·곡별 끔은 t491 그대로다. 상수는 넣지 않았다.

## 4. 시험

`server/tests/test_upload_look_memory_t609.py` — 6개 통과.

- 기억 창을 받은 업로드 길: 둘째 곡의 첫 큐가 첫 곡과 다르고, 기억 2곡, 회신에 끄는 문구
- 창이 없으면 오프셋 0(오늘과 같음)
- `avoid_previous_looks=false` 면 오프셋 0, 그래도 저장됐으니 기억에 들어감
- 불리언이 아닌 값은 거절
- 콘솔이 `Store Sequence` 를 거부한 곡은 기억에 안 들어감
- 세션이 `build_toolset` 에 넘긴 창의 `history` 가 세션 목록 **그 자체**(`is`) — 죽은 배선이 아니다

**돌연변이 확인:**

| 돌연변이 | 결과 |
|---|---|
| 저장 성공 뒤 기억 기록 줄 제거 | 2개 실패 |
| 세션이 `song_look_memory=` 를 안 넘김(t486 의 죽은 배선 꼴) | 1개 실패 |
| 저장 성공 판정에서 `is_error` 조건 제거 | 1개 실패(저장 거부 시험) |
| 처음 넣었던 `store_failed`(명령 결과에 실패가 있는지) 조건 제거 | **살아남음** → 조사했다(아래) |

**살아남은 돌연변이.** `probe_store_fail.py` 로 재 보니 저장 거부 시험은 실제로 `Store Sequence 3 Cue 1 …` 을 보냈고 콘솔이 거부했으며, 그때 `run_commands` 가 결과를 오류(`is_error: True`)로 돌려줬다. 그래서 `is_error` 조건이 이미 막고 있었고 `store_failed` 조건은 중복이었다. 중복 조건을 지우고, `is_error` 조건이 시험에 걸리는 것(위 셋째 줄)을 확인했다. 모든 돌연변이는 되돌렸다(`grep -c MUTANT` → 0).

**기존 시험:** `pytest server/tests -k "song or chorus or palette or composer or web_session or songcue or timeline or arc or accent or ldrender or upload or concept or beat_grid or preset or tools"` → 3722 passed, 8 skipped. `make ci-local` → exit 0. 전체 묶음은 CI 가 잰다.

## 5. 안 잰 것

- **감독 거절(`gate_status == "rejected"`) 때 기억에 안 들어가는지는 시험하지 않았다.** 코드 조건은 있지만, 거절을 내는 가짜 게이트를 이 시험에 붙이지 않았다. 저장 거부(콘솔)만 시험했다.
- **실제 모델이 「앞 곡 룩 허용」을 듣고 `avoid_previous_looks=false` 를 넘기는지는 안 쟀다.** 도구 설명에 그렇게 적었을 뿐이다.
- **대화 길 곡 → 업로드 길 곡이 한 세션에서 이어지는 흐름을 끝까지 돌리지는 않았다.** 두 길이 같은 목록을 쓴다는 것(`is`)까지만 시험했다.
- **가짜 콘솔에서만 쟀다.** 업로드 길이 콘솔 위치 풀을 라벨로 찾는 부분은 t480 가짜 콘솔의 기본 10라벨을 썼다.
- 무대에서 다르게 보이는지·팔레트 맞바뀜의 효과는 t491 과 같이 실기 항목이다(리드 결정).
- 실제 DSP 경로·실제 감독 답의 다양성은 t491 §5 와 같이 안 쟀다.

## 6. 산출물

| 파일 | 내용 |
|---|---|
| `measure_upload_look_reuse.py` · `.stdout.txt` | 업로드 길 측정(세 가지 실행), exit 0 |
| `upload_look_reuse.json` | 곡별 큐·룩 원자료와 쌍별 통계 |
| `probe_store_fail.py` | 살아남은 돌연변이 조사 탐침 |
