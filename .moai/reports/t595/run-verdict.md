# t595 run 판정 — 박자 격자 칸·편집 칸 「⚠ 빈 프리셋」 표식

브랜치 `WT-empty-preset-mark` · 기준 origin/main `56b994b4`(착수 때 `git rev-list --left-right origin/main...HEAD` → `0 0`) · 콘솔 쓰기 0건(가짜 콘솔만) · `beat_grid_apply` 본문 무변경

## 무엇을 했나
t590 은 빈 프리셋을 반영 승인 카드 문구로만 알렸다. 이 카드는 서버가 이미 아는 판정을 격자 이벤트로 내려, 격자 칸과 편집 칸에서 바로 보이게 한다(REQ-LDBEAT-015(i-1) 「그 칸에 표시」).

- 서버 `server/design/beat_grid.py`
  - `classify_empty_preset(value, pool_slots, unknown_pool_unread=)` — 번호 하나의 판정. t590 보류(`split_empty_preset_holds`)와 이번 표식이 **같은 함수**를 쓴다(보류 쪽 동작은 그대로 — 아래 회귀 시험).
  - `empty_preset_cells(grid, pool_slots)` — 칸마다 `{group_name, bar, held, fields:[{field, field_label, value, kind, reason}]}`. `kind` = `empty`/`pool_unread`.
  - `_preset_number_fields(cue)` — 칸의 프리셋 번호 필드 열거를 `pending_preset_fields` 에서 뽑아 냈다(승인과 무관하게 보려고).
- 서버 `server/web/session.py`
  - `_beat_grid_pool_slots` — 이 세션이 마지막으로 완전 판독한 풀. 채우는 곳은 셋뿐: 반영 때 승인 대기 번호의 풀 판독(t590 `_beat_grid_split_empty_presets`), 프리셋 서랍 판독(`beat_grid_preset_drawer`), 「＋ 새 프리셋 만들기」의 빈 번호 확인 판독(t589 `beat_grid_new_preset`, main 합친 뒤 추가). **표식을 위해 콘솔을 따로 읽지 않는다.**
  - `_beat_grid_refresh_unsent_cells` — 격자가 나갈 때마다(편집·반영·로드) `empty_preset_cells` 를 다시 계산해 싣는다.
  - `_beat_grid_learn_pools` — 풀을 새로 읽어 표식이 달라졌을 때만 격자를 한 번 더 보낸다(서랍을 열 때마다 격자를 흔들지 않는다). 반영에서는 승인 카드보다 **먼저** 나간다.
- UI `ui/src/protocol.ts`·`ui/src/components/BeatGrid.tsx`·`ui/src/styles.css`
  - 격자 칸 배지 `⚠ 빈 프리셋(4.99)` — 못 읽은 풀의 번호는 `4.99?`. 툴팁에 서버 사유 + 반영 결과.
  - 편집 칸: 그 번호를 가진 행(밝기·위치·색·효과 프리셋) 아래 한 줄 `⚠ 4.99 — <사유> · <반영 결과>`.
  - UI 는 서버 목록만 읽는다 — 서랍 항목과 대조해 다시 추측하지 않는다(목록이 없으면 배지 0).

## 판정 — 이미 승인된 칸의 빈 번호도 표식 대상인가: **예, 단 `held: false` 로 가른다**
- 근거: 「그 번호가 콘솔 풀에 없다」는 사실은 승인 여부와 무관하다. 그리고 승인된 칸은 t590 가드 D 의 보류 대상이 아니다(가드는 승인 대기만 본다 — t590 판정서 「이미 승인된 칸이 빈 번호를 가리키는 경우는 이 가드 범위 밖」). 즉 승인된 칸의 빈 번호는 반영하면 **빈 번호를 가리킨 큐가 그대로 나간다** — 감독이 가장 알아야 할 경우라 숨기면 안 된다.
- 그래서 문구를 갈랐다: `held: true` → 「⇪ 콘솔에 반영」에서 이 칸은 송신 보류됩니다 / `held: false` → 이미 승인된 칸이라 반영하면 빈 번호를 가리킨 큐가 그대로 나갑니다.
- 단, 승인된 칸의 번호는 **그 풀을 서버가 읽었을 때만** 표식이 붙는다. 반영은 승인 대기 번호의 풀만 읽으므로(t590 그대로), 승인된 칸만 있는 풀은 서랍을 열어야(1·2·4번 풀, 이름으로 찾은 Dimmer/Position/Color) 판정된다. 그 밖의 풀은 판정 없음(표식 없음, 지어내지 않음).
- 이 카드 밖으로 남긴 것: 승인된 칸의 빈 번호를 반영에서 **보류할지**는 가드 D 범위 확장이라 손대지 않았다(표식만). 필요하면 리드가 카드로 판단.

## 하네스 전후 캡처 (가짜 콘솔, t577/t590 FakeConsole — `.moai/reports/t595/capture_harness.py`)
입력 칸: 1마디 승인 대기 `effect 4.99`(빈 번호) · 2마디 승인됨 `color 4.98`(빈 번호) · 3마디 승인 대기 `effect 4.21`(있는 번호, 대조군). 풀 4 = slot 21 만.

고치기 전 (`harness-before.txt`):
```
apply ok: True | reason: None
events: ['execution_preview', 'song_timeline', 'beat_grid_send_status']
song_timeline events: 1
  [0] empty_preset_cells = "<필드 없음>"
```
고친 뒤 (`harness-after.txt`):
```
apply ok: True | reason: None
events: ['song_timeline', 'execution_preview', 'song_timeline', 'beat_grid_send_status']
song_timeline events: 2
  [0] empty_preset_cells = [{"group_name": "BACK", "bar": 1, "held": true, "fields": [{"field": "effect_preset_no", "field_label": "효과 프리셋", "value": "4.99", "kind": "empty", "reason": "빈 프리셋 — 아직 콘솔에 만들 길 없음"}]}, {"group_name": "BACK", "bar": 2, "held": false, "fields": [{"field": "color_preset_no", "field_label": "색 프리셋", "value": "4.98", "kind": "empty", "reason": "빈 프리셋 — 아직 콘솔에 만들 길 없음"}]}]
  [1] (같은 목록)
```
대조군 3마디(4.21)는 두 번 다 목록에 없다.

## 검증 (이 트리, 이 세션에서 실행)
- `pytest server/tests/test_empty_preset_mark_t595.py` → `16 passed`.
- 회귀: `pytest test_beat_grid_*.py test_web_beat_grid_*.py test_apply_time_approval_t577.py test_empty_preset_hold_t590.py test_empty_preset_mark_t595.py test_approval_vs_sent_t549.py test_send_approval_t549.py test_session_beat_grid_edit_t551.py test_messages_beat_grid_t551.py test_app_movement_t548.py test_prechk_tool.py test_write_dispatch_census.py` → `623 passed, 1 skipped`.
- 뮤테이션(서버) — 각각 되돌린 뒤 `grep -c MUTATION` → 0:
  - A 반영 판독 배선 끊기(`_beat_grid_learn_pools` 호출 → `pass`) → `3 failed, 13 passed`.
  - B 승인 구분 지우기(`held` 항상 True) → `3 failed, 13 passed`.
  - C 서랍 판독 배선 끊기 → `3 failed, 13 passed`.
- UI: `tsc --noEmit` → exit 0 · `vitest run` → `55 files, 1198 passed` · 새 시험 `BeatGridEmptyPreset.test.tsx` 7개.
- 뮤테이션(UI) — 격자 배지 그리기 끄기 → `1 failed, 6 passed`, 되돌린 뒤 `grep -c MUTATION` → 0.
- `ruff check`(바뀐 파이썬 4파일) → `All checks passed!` · `ruff format` 적용(내 함수 서명 1곳만 바뀜).

## main 합친 뒤 (t589 「＋ 새 프리셋 만들기」 #633)
- 착수 뒤 main 이 9커밋 앞서 나갔다(`git rev-list --left-right origin/main...HEAD` → `9 0`). 내 커밋 `b2d6f724` 뒤에 `origin/main`(`b297c570`)을 합쳤다 — 글자 충돌 0.
- 뜻 겹침 확인: t589 의 「⚠ 콘솔 빈칸 미확인」은 대화창 답장 문구라 격자 배지와 중복되지 않는다. t589 도 풀을 읽어 빈 번호를 고르므로 그 판독을 표식 출처에 더했다 — 배정 직후 그 칸에 `held: true` 표식(반영에서 보류될 칸과 일치). 시험 `TestNewPresetDialogMarksItsNumber` 추가, 그 배선을 끊으면 `1 failed, 16 passed`(되돌린 뒤 `grep -c MUTATION` → 0).
- 서버 전체 시험은 레인에서 끝까지 돌리지 않았다 — load average 74 에서 10분 넘게 16% 까지만 가서 멈췄다(남은 프로세스 0 확인). 전체는 PR CI 에 맡긴다.
- 합친 트리: `pytest test_empty_preset_mark_t595.py` → `17 passed` · UI `tsc --noEmit` exit 0 · `vitest run` → `1212 passed` · ruff check/format 깨끗.

## 안 잰 것 / 남은 위험
- **편집 칸 안내는 화면 시험이 없다.** 편집 칸은 칸을 클릭해야 열리는데 이 프로젝트엔 jsdom 이 없어 `renderToStaticMarkup` 으로 선택 상태를 못 만든다. 안내 문구 함수(`emptyPresetFieldNote`)만 시험했다. 실제 브라우저 스크린샷도 찍지 않았다.
- **표식은 마지막 판독 기준이다.** 콘솔에서 누가 그 슬롯에 프리셋을 저장해도 다음 서랍 판독·반영 전까지 표식이 남는다(반대 방향도). 세션이 끊기면 기억도 사라진다(다시 읽기 전까지 표식 없음).
- 서랍이 못 읽은 풀은 번호를 모르므로(이름으로 찾다 실패) 「못 읽음」 표식을 남길 수 없다. 반영 판독만 「못 읽음」을 표식한다.
- 실기 콘솔에서 재지 않았다(콘솔 0).
- **lane-1 t592 와 겹칠 수 있는 자리**: `split_empty_preset_holds` 안의 판정을 `classify_empty_preset` 로 뽑았다(동작 동일). t592 가 위치 레시피로 「빈 위치 번호는 만들어서 보낸다」로 바꾸면, 표식 문구 「아직 콘솔에 만들 길 없음」이 위치 번호에는 틀리게 된다 — t592 가 이 판정 함수를 함께 고쳐야 표식이 따라간다.
