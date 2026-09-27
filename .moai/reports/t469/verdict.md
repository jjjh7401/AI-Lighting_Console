# t469 — 초안 네 칸(tracking·mib_mode·phaser·position_preset_no) 콘솔 전송 (lane-1)

- 브랜치 `WT-draft-fields-send` · 기준 `origin/main@bdd8902b` (작업 공간을 만들 때 `d59b5ecd`로 잡혀서 `git merge --ff-only`로 당김. 커밋 0 상태에서)
- 감독 확인(이 세션 AskUserQuestion): 시험 시퀀스 **900**, 기구 **Spiider 521·522** · MIB 모드는 **콘솔로 보내지 않고 사유만 고침**
- 도구: 쓰기 `tools/console_probe.py exec:`(브리지 직결, `run_commands`를 거치지 않음) · 읽기 `.moai/reports/t431/probe_t431.py`
- 판정: 되읽기 또는 **감독 캡처(트래킹 시트)**로만. 저장 옵션·키워드 명령의 `OK`는 증거로 쓰지 않았다

## 0. 요약

| 칸 | 결과 | 콘솔 문법(실측) | 근거 |
|---|---|---|---|
| tracking = Release | 🟢 보냄 | `Set Cue N Sequence S Property 'Release' 1` / `0` | 되읽기 `false→true→false`, 가짜 값 `'Blorp'` → `Illegal value` (run4). 코드 경로도 되읽기 `true`, 대조 큐 `false` (run11) |
| tracking = Block | 🟢 보냄 | `Block Sequence S Cue N` / `Unblock …` | 캡처: 큐 13 팬·틸트 **흰색**(t459와 같은 Block 표시) |
| tracking = Cue Only | 🟢 보냄 | 저장 옵션 `Store … /Merge /CueOnly` — **큐 속성이 아니다**(큐 23개·파트 속성 중 CueOnly 없음) | 캡처: Q4에 팬 75 CueOnly 저장 → **Q5 팬 -30이 자홍에서 청록으로** |
| tracking = Track | 🟢 보냄(되돌리기) | 이전 Release → `Release 0`, 이전 Block → `Unblock` | 같은 명령의 역방향. **이전 Cue Only는 되돌리는 명령이 없어** 사유를 달고 건너뜀 |
| position_preset_no | 🟢 보냄(번호가 있을 때만) | `<그룹> ; At Preset 2.<n>` 뒤 `Store … /Merge` | 캡처: 2.2·2.5 들어감. 코드 경로 큐 11 `2.5 POS2.5 POS05` 청록 |
| position(이름만) | ⚪ 건너뜀(사유) | — | 이름→풀 번호는 콘솔을 읽어야 알 수 있다. 순수 계획 함수라 번호를 지어내지 않는다 |
| phaser | ⚪ 건너뜀(사유 갱신) | 싣는 형태는 확인: `At Preset 21.4` 뒤 `/Merge` → 큐에 `21.4 DIM-B…` + `Step 2` | 초안에는 이름만 있고, 카탈로그 이름(`Breathe Soft` 등)은 이 콘솔 풀에 없다(풀 21: DIM-PULSE·PT-CIRCLE·DIM-CHASE·DIM-BREATHE·TILT-SWEEP·DIM-TWINKLE) |
| mib_mode | ⚪ 건너뜀(사유 갱신, 감독 결정) | — | t468: 우리 MIB는 조립기가 사전이동 큐를 직접 넣는다. 콘솔 MIB 속성을 켜면 옮기는 쪽이 둘이 된다 |

## 1. 실측 기록 (시퀀스 900)

| run | 내용 | 결과 |
|---|---|---|
| run1 | 큐 속성 전수(시퀀스 1999 큐, 읽기) | 23개. 트래킹 관련은 `RELEASE`뿐 |
| run2·run3 | 프리셋 풀 판독(읽기) | 풀 2: POS01~POS06 · 풀 21: DIM-PULSE 등 6 · 시퀀스 17개(900 없음) |
| run4 | Q1~Q4 구성, Release 켜고 끄기 | 되읽기 `true`/`false`, 가짜 값 거절 |
| run5 | `/CueOnlyzz`(가짜) → Q3 이름이 **`zz`로 바뀜**, `OK` · `/CueOnly` · Q2에 `At Preset 2.1` · Q4에 `At Preset 21.4` | 전부 `OK`. 캡처 1: Q2 **변화 없음**(팬 30), Q4 `21.4 DIM-B…` + Step 2 |
| run6 | Q5(조도 80만) 추가 | 캡처 1: Q5 팬 -30 자홍(기준) |
| run7 | Q6~Q10에 프리셋 2.2~2.6, Q4에 팬 75 `/Merge /CueOnly` | 캡처 2: Q5 팬 **-30 청록** · Q6 `2.2 POS02` 청록 · Q9 `2.5 POS05` 청록 · Q7·Q8·Q10 자홍(값 없음) |
| run8 | 그룹 풀(읽기) | MOVER-D = 12 |
| run9·run10 | `gen_planner_commands.py`가 만든 **실제 코드의 명령 15줄**을 그대로 발사 | 전부 `OK` |
| run11 | 되읽기 | 큐 11 `RELEASE=true`, 큐 12·13 `false` · 캡처 3: 큐 11 `2.5 POS2.5 POS05` 청록(521·522·523), 큐 12 조도 60, 큐 13 팬·틸트 흰색(Block) |
| run12 | 삭제·되읽기 | §4 |

### 콘솔이 조용히 넘어가는 두 가지 (방출 계층 주의)

1. **저장 옵션은 가짜여도 `OK`가 돌아온다.** `/CueOnlyzz`는 거절되지 않았고, 콘솔이 뒷부분을 이름으로 받아 큐 이름이 `zz`로 바뀌었다
2. **선택 기구 값이 없는 프리셋을 recall해도 `OK`가 돌아오고 아무것도 실리지 않는다.** 2.1·2.3·2.4·2.6(이 풀의 "합성좌표" 프리셋)은 521·522 값이 없었고, 빈 프로그래머로 저장한 큐까지 생겼다(Q7·Q8·Q10). 반영 요약에 `포지션 2.<n>`을 적어 감독이 화면에서 확인하게 했다

### `run_commands` 중복 제거 결함(리드 참고, lane-2 t475)과의 관계

- 이 카드의 실측 로그에서 `skipped_already_executed`는 **0건**이다(`grep -c` 결과). 실측 도구는 `run_commands`를 거치지 않는다
- 「큐는 생겼는데 값이 없음」(2.1·2.3·2.4·2.6)은 줄마다 명령 문자열이 달라 중복 제거 대상이 아니다 → 프리셋에 값이 없다는 해석을 유지한다
- **반영 경로 영향**: `run_commands`는 `ClearAll`과 순수 선택(`Group 12`)만 면제한다. 한 반영 안에서 두 큐의 값 줄이 같으면(예: `Group 12 ; Attribute 'Dimmer' At 90`) 두 번째가 건너뛰어져 빈 저장이 된다. 원래 있던 결함이고, 수정은 t476이 맡는다. 이 카드가 추가한 트래킹 줄은 큐 번호를 품어서 줄마다 다르다

## 2. 코드 변경

`server/design/cue_sheet_apply.py`
- `CuePlan`에 `store_options`(예: `/CueOnly`)와 `tracking_ops`(`release_on`·`release_off`·`block`·`unblock`)를 추가했다. 문면은 시퀀스 번호를 아는 `plan_console_apply`가 `_tracking_command`로 짓는다(t304: 큐 판정은 번호를 모른다)
- `_tracking_plan`: 이전→새 전환표(§0). 모르는 값은 짐작하지 않고 건너뛴다. 이전이 Cue Only면 되돌리는 명령이 없어 사유를 단다
- `_position_recall`: `position_preset_no`가 `2.<n>`일 때만 값 줄 끝에 `; <그룹 선택> ; At Preset 2.<n>`을 붙인다. 보조 컬러가 선택을 back 그룹으로 옮겼을 수 있어 선택을 다시 적는다(`Group 12`를 두 번 선택해도 풀리지 않음을 캡처 3에서 확인)
- 곡 전체 반영(`previous=None`)에서는 사유를 달지 않는다: 그때 `position`은 조립기의 움직임 이름(`STATIC`·`TILT-UP @slow`)이지 감독이 고른 프리셋이 아니다 — 기존 UNSOURCED 칸과 같은 원칙. 이걸 놓쳤을 때 사전 점검 시험이 「일부만 나가는 큐 2건」 → 18건으로 깨져서 잡았다
- `UNSOURCED_FIELD_REASONS`: `tracking`·`position`을 뺐다. `mib_mode`(t468 근거)·`phaser`(형태는 실측, 번호는 모름) 사유를 새로 적었다. `CONSOLE_APPLIABLE_FIELDS`에 `tracking`·`position_preset_no`를 추가했다(이 파일 밖 소비자 0)

`server/tests/test_cue_sheet_apply_t469.py` 20건 · `test_cue_sheet_edit_vocab_t466.py`의 건너뜀 시험을 `mib_mode`·`phaser` 두 칸으로 좁혔다(트래킹·포지션은 이제 나간다)

## 3. 증거

| 확인 | 명령 | 결과 |
|---|---|---|
| RED | `uv run pytest server/tests/test_cue_sheet_apply_t469.py -q` (변경 전) | `11 failed, 7 passed` — `pytest_red.txt`. 통과한 7건은 「안 보낸다」 쪽이라 변경 전에도 참 |
| GREEN | 반영·사전 점검 5파일 | `140 passed` — `pytest_green.txt` |
| 관련 묶음 | `uv run pytest -q server/tests -k "cue_sheet or preflight or draft or apply or web_session or session"` | `1237 passed, 22 skipped` — `pytest_affected.txt` |
| 린트 | `ruff check` / `ruff format --check` (고친 파일 전부) | 통과 |
| 코드 경로 실측 | `gen_planner_commands.py` → 15줄 발사 → 되읽기·캡처 | §1 run9~11 |

## 4. 정리 (run12)

- `ClearAll` → `Delete Sequence 900 /NoConfirm`
- `Sequences/900` → `path segment not found`. 시퀀스 풀 17개 `[1..15, 1999, 2000]`로 착수 전과 같다
- Page 1 실행기 4개(바뀐 것 없음) · 프리셋 풀 2는 6개 그대로 · 선택 0
- 쇼 저장 0회. 프리셋은 recall만 하고 저장·변경은 하지 않았다. 시퀀스 900 밖의 쓰기 0

## 5. 안 잰 것 (Gaps)

- 코드 경로의 **Cue Only 효과**: 큐 12 다음 큐(13)에 조도가 직접 박혀 효과가 안 보였다. 효과는 Q4→Q5(`Fixture` 선택)로 확인했고, 명령 줄 형태(`/Merge /CueOnly`)는 같다
- `CueFade`와 `/CueOnly`를 함께 쓴 저장 줄(`Store … CueFade 2 /Merge /CueOnly`)은 쏘지 않았다
- 실제 `run_commands` 경로(승인 카드·LiveLock)를 통한 반영 — 이번엔 브리지 직결로 같은 줄을 쐈다
- 이름만 있는 포지션·페이저를 콘솔 풀에서 번호로 찾는 경로 — 후속 제안 §6
- UI에서 네 칸을 고치는 화면(`SongTimelineSection` 타입) — t466 §7 제안, 이 카드 범위 밖

## 6. 후속 제안

- 이름→프리셋 번호 조회: 반영 전에 세션이 콘솔 풀(2·21 등)을 읽어 초안의 포지션·페이저 이름을 번호로 채우면, 지금 건너뛰는 두 경우가 풀린다. 세션에는 이미 `_resolve_position_preset_labels`가 있다
- 방출 계층 경고: 「recall한 프리셋에 선택 기구 값이 없음」을 반영 전에 알 수 있으면 좋다(지금은 요약의 번호로 감독이 확인)
