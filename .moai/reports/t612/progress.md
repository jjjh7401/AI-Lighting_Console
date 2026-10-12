# 카드 t612 — 박자 격자 에미터: 첫 큐 저장이 시퀀스를 만들고 Name 은 그 뒤로

- 배차: 리드 세션(배차 메시지, 카드 본문 `moai todo` 의 t612). 분류 Class B (plan 생략, run → sync).
- 작업 트리: `.claude/worktrees/t612` · 브랜치 `WT-beatgrid-store-order`
- 기준: `origin/main` `7e5903d0` (작업 시작 시 분기 차이 `0 0`)
- 콘솔: 송신 없음(배차 지시). 실기 확인은 리드의 감독 「실행」 뒤 다음 접속에서.

## 3.1 주장 (Claim)

1. 큐 저장 줄이 `Store Cue N Sequence S` 에서 `Store Sequence S Cue N` 으로 바뀌었다.
2. 맨 `Store Sequence S` 줄은 저장되는 큐가 하나라도 있으면 더 나가지 않는다. 첫 큐 저장이 시퀀스를 만든다.
3. `Set Sequence S Property 'Name'` 줄은 첫 큐 저장 바로 뒤에 온다.
4. 저장되는 큐가 하나도 없는 트랙은 옛 순서(맨 Store Sequence + Name)를 유지한다. 배정 줄이 가리킬 시퀀스가 있어야 하기 때문이다.
5. 재적용의 `/Overwrite` 부착 대상(`beat_grid_send._overwrite_store_cue`)도 같은 어순을 따른다.

## 3.2 증거 (Evidence)

### 실기 근거 — `.moai/reports/t608/run-1012.jsonl` (주 체크아웃, 추적되지 않은 파일)

```
{"index": 30, "line": "Store Sequence 700", "sent_at": "2026-10-12T09:32:35.250+00:00", "responded_at": "2026-10-12T09:32:35.318+00:00", "status": "ok", "detail": "OK"}
{"index": 31, "line": "Set Sequence 700 Property 'Name' 'LDBEAT FOH'", "sent_at": "2026-10-12T09:32:35.318+00:00", "responded_at": "2026-10-12T09:32:35.418+00:00", "status": "ok", "detail": "OK"}
{"index": 32, "line": "Group 3 ; Attribute 'Dimmer' At 20", "sent_at": "2026-10-12T09:32:35.418+00:00", "responded_at": "2026-10-12T09:32:35.484+00:00", "status": "ok", "detail": "OK"}
{"index": 33, "line": "Store Cue 1 Sequence 700", "sent_at": "2026-10-12T09:32:35.484+00:00", "responded_at": "2026-10-12T09:32:35.551+00:00", "status": "failed", "detail": "User Canceled Command"}
{"event": "end", "sent": 33, "stopped_at": 33, "status": "stopped", "ended_at": "2026-10-12T09:32:35.551+00:00"}
```

### 수정 전 — 재현 시험 (RED)

명령: `uv run pytest server/tests/test_beat_grid_store_order_t612.py -q -p no:cacheprovider`

```
4 failed, 1 passed in 0.36s
```

실패한 튜플(같은 입력: FOH · 그룹 3 · 시퀀스 700 · 타임코드 70 · 마디 3 큐 1개):

```
('Store Sequence 700', "Set Sequence 700 Property 'Name' 'LDBEAT FOH'", 'Group 3 ; At Preset 2.1', 'Store Cue 1 Sequence 700', 'ClearAll', "Set Cue 1 Sequence 700 Property 'TrigType' 'Time'", ...)
```

앞의 네 줄이 실기 run-1012 의 index 30–33 과 같은 순서다. 통과한 1개는 저장 큐가 없는 트랙 가드(3.1 의 4번)다.

### 수정 후 — 같은 시험 (GREEN)

명령: 위와 같음 → `5 passed in 0.12s`

### 수정 전후 생성 줄 diff (같은 입력)

수정 전(위 튜플을 줄 단위로 옮김, 뒤쪽 `TrigTime`·`Assign` 은 생략):

```
Store Sequence 700
Set Sequence 700 Property 'Name' 'LDBEAT FOH'
Group 3 ; At Preset 2.1
Store Cue 1 Sequence 700
ClearAll
Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
...
```

수정 후 — 큐 1개 (수정 후 `emit_beat_grid_write_bundle` 실제 출력):

```
Group 3 ; At Preset 2.1
Store Sequence 700 Cue 1
Set Sequence 700 Property 'Name' 'LDBEAT FOH'
ClearAll
Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
Set Cue 1 Sequence 700 Property 'TrigTime' 5
Assign Sequence 700 At Timecode 70
```

수정 후 — 큐 2개: 첫 큐 뒤에만 Name 이 있고, 둘째 큐는 `Store Sequence 700 Cue 2` 한 줄이다.

수정 후 — 저장 큐 없음: `Store Sequence 700` · `Set Sequence 700 Property 'Name' 'LDBEAT FOH'` · `Assign Sequence 700 At Timecode 70`.

### 회귀 시험 (에미터 관련만, 배차 지시대로)

- 수정 직후, 옛 튜플을 고정하던 기존 테스트 15개 실패(다른 테스트는 통과): `15 failed, 550 passed, 15155 deselected, 1 warning in 43.45s`. 전부 옛 어순 literal 또는 옛 Name 위치를 고정하던 단정이었고, 새 계약으로 갱신했다.
- 갱신 후: `uv run pytest server/tests -q -p no:cacheprovider -k "beat_grid or beatgrid or approved_empty or approval_vs_sent"` → `565 passed, 15155 deselected, 1 warning in 8.57s` (경고 1개는 fastapi TestClient 의 httpx 사용 안내, 이번 변경과 무관).
- 린트: `uv run ruff check` (변경 파일 7개) → `All checks passed!` · `uv run ruff format --check` → `7 files already formatted`.

## 3.3 기준선 귀속 (Baseline-attribution)

- 트리 `.claude/worktrees/t612`, HEAD `7e5903d0` = `origin/main`. 위의 모든 명령은 이 트리에서 이 실행에 대해 돌렸다.
- 실기 기준선: run-1012 (t608, 2026-10-12 09:32 UTC). 원래 번들은 `efb40e03` 기준으로 만들었다(`approval-list.md` 머리말) — 기준 커밋이 다르다.

## 3.4 미검증 (Gaps)

1. **실기 콘솔 미접속**(배차 지시: 콘솔 송신 금지). 새 어순과 「첫 큐 저장이 시퀀스를 만든다」는 실기에서 확인되지 않았다. 선례는 라벨(`'name'`)이 붙은 `Store Sequence 309 Cue 1 'name'`(t531) 과 `CueFade` 가 붙은 `Store Sequence S Cue N CueFade x /Merge`(cue_sheet_apply) 다. 라벨도 페이드도 없는 `Store Sequence S Cue N` 형은 저장소에 선례가 없다.
2. **전체 테스트 스위트 미실행**(배차 지시: 에미터 관련만, 전체는 CI).
3. **t608 페이로드 재생성 미수행** — 아래 「페이로드 상태」.
4. `Store Sequence S Cue N … /Overwrite` 형은 실기 미측정이다(옛 `Store Cue … /Overwrite` 도 미측정이었다).
5. `Delete Cue k Sequence s` 는 바꾸지 않았다. 실기 선례가 없는 옛 가설 그대로다.

## 3.5 잔여 위험 (Residual-risk)

- 실기가 새 어순을 거절하면 되돌릴 자리는 두 곳이다. `beat_grid_emit._emit_cue` 의 store 줄 어순, `beat_grid_send._overwrite_store_cue` 의 target 한 줄. 두 줄만 고치면 된다. 초 환산·트리거·트래킹 판정은 그대로다.
- 이름 줄이 큐 저장 뒤로 옮겨졌다. 선례(t531)와 같은 자리지만, 이 에미터 출력으로 실기 확인은 아직 없다.
- 저장 큐 없는 트랙의 옛 순서 유지는 테스트로 고정했다(`TestTrackWithoutAStoredCueStillCreatesItsSequence`).

## 페이로드 상태 (t608 번들)

- `.moai/reports/t608/payload-all.txt` (주 체크아웃, 추적 안 됨): sha256 `9ca962e47fab66e8e95dc7ce447c2fcec013a4f8e1161d711e53d6329c7faeea` — 확인했고 변경하지 않았다. `runner.md` 의 기록과 같다.
- 이 파일에는 옛 어순 큐 저장 줄 16개(`Store Cue N Sequence S …`)와 맨 `Store Sequence N` 줄 4개(줄 30·59·72·75)가 있다. **이 번들은 그대로 송신하면 안 된다** — 실기에서 index 33 이 거절됐다.
- 재생성을 하지 않은 이유(`approval-list.md` §0·§8·§9 에 적힌 사실): 번들은 ⓪~⑫ 열두 항목의 합본이고, ⑪·⑫ 는 앱 생산 경로가 없어 손으로 이어 붙였다. 생성 스크립트는 세션 스크래치에만 있었고 사라졌다. 그래서 생성 함수를 한 번 호출하는 것으로는 같은 번들을 얻을 수 없다.
- 리드가 정할 것: 다음 감독 실행에서 무엇을 확인할지. 옛 항목 ②(옛 어순 검사)는 새 어순 검사로 바뀌어야 한다. 그 뒤에 승인 목록을 다시 만들고 sha 를 갱신한다.

## 3.6 변경 파일

- `server/design/beat_grid_emit.py` — 큐 저장 어순, 이름 줄 위치, 저장 큐 없는 트랙의 옛 순서 유지.
- `server/design/beat_grid_send.py` — `/Overwrite` 부착 대상을 새 어순으로.
- `server/tests/test_beat_grid_store_order_t612.py` (신규) — 재현 시험 5개.
- `server/tests/test_beat_grid_emit_entry_t576.py`, `test_beat_grid_emit_t549.py`, `test_beat_grid_reapply_t572.py`, `test_beat_grid_send_t563.py` — 옛 어순 literal 을 고정하던 단정을 새 계약으로 갱신.
- `.moai/reports/t612/progress.md` (이 파일).
