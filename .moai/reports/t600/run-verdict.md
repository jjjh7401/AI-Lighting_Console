# t600 run 판정 — 이미 승인된 칸의 빈 프리셋 번호도 반영 때 보류·생성

브랜치 `WT-approved-empty-hold` · 기준 origin/main `eb936648`(착수 때 `git merge-base --is-ancestor eb936648 HEAD` → OK, 고친 뒤 `git rev-list --count --left-right origin/main...HEAD` → `0 1`) · 콘솔 쓰기 0건(가짜 콘솔만)

## 판정: PASS — 리드 방향대로 묶었다

## 구멍 (고치기 전 재현)
t590 가드 D 는 승인 대기 칸의 번호만 풀을 읽어 갈랐다. 에미터의 유일한 관문은 「승인이 있나」(`check_evidence_approval`)라서, 이미 승인된 칸이 콘솔 풀에 slot 이 없는 번호를 가리키면 그대로 나갔다. 시험을 먼저 쓰고 고치기 전에 돌린 출력(`uv run pytest server/tests/test_approved_empty_hold_t600.py`) → `9 failed`, 실패 사유가 구멍 그대로다:
```
E       AssertionError: assert not ['Group 7 ; At Preset 4.99']
E       AssertionError: assert not ['Group 7 ; At Preset 6.5']
E       AssertionError: assert not ['Group 7 ; At Preset 2.71']
```
원인 재확인(증상이 아닌가): 같은 번호를 승인 대기 칸에 두면 가드 D 가 보류한다(t590 시험 그대로 통과) — 차이는 「승인된 칸은 풀 판독 목록에 들어가지 않는다」 하나뿐이었다.

## 고친 것
- `server/design/beat_grid.py`
  - `approved_preset_numbers(grid)` 신설 — 완전한 승인을 가진 칸의 번호를 `pending_preset_approvals` 와 같은 모양 + `"approved": True` 로 낸다.
  - `empty_preset_cells` — `state: "approved"`(그대로 나감) 퇴역. 상태는 `held`/`create` 둘. 승인된 칸의 빈 위치 번호도 `create_on_apply` 후보.
- `server/design/beat_grid_emit.py` — `emit_beat_grid_write_bundle(held_cells=)` 신설. (트랙, 마디) → 사유. 그 칸은 커맨드 0줄, 큐 번호 안 씀(거절 칸과 같음).
- `server/web/session.py` `beat_grid_apply` — 승인 대기 + 승인된 번호를 **한 번의** 풀 판독(`_beat_grid_split_empty_presets`)으로 같은 규칙에 넣고, t592 위치 만들기도 같이 거친다. 승인 기록 대상(`pending_before`)에서는 승인된 칸을 다시 뺀다(이미 승인 — 「새로 만드는 프리셋 N개」에도 안 오름). 승인된 보류 칸은 `held_cells` 로 에미터에 넘긴다. 승인 카드 보류 줄에 「· 이미 승인된 칸」 표식. **승인은 지우지 않는다** — 다음 반영 때 다시 판정.
- UI `ui/src/protocol.ts`·`ui/src/components/BeatGrid.tsx` — `state` 타입에서 `"approved"` 제거, 「그대로 나갑니다」 문구 삭제.
- SPEC(같은 PR, manager-spec): spec.md REQ-LDBEAT-015 **(i-9)(i-9-1)~(i-9-6)** 신설, acceptance.md AC-LDBEAT-016 **(w-6)**, plan.md M11 4단계, version 0.5.2→0.5.3. REQ 25·AC 25 불변. (w-6) 본문의 「한 칸에 승인 대기·승인 번호가 섞이면」 문장은 승인이 칸 단위라 성립하지 않아 사실대로 고쳤다.

## 고친 뒤
`uv run pytest server/tests/test_approved_empty_hold_t600.py` → `9 passed`. 확인하는 것:
- 승인된 칸의 빈 효과 번호 4.99 → 송신 0줄, 대조군 4.21 은 `At Preset 4.21` 송신, 카드에 `빈 프리셋 — 아직 콘솔에 만들 길 없음(송신 보류) 1개`, 승인=송신 `match: True`, 그 칸 승인 유지.
- 못 읽은 풀(6) → `풀을 못 읽어 …` 사유로 보류.
- 칸 단위 — 4.21+4.99 한 칸 → 칸 전체 보류(`같은 칸에 보류 번호가 있어 함께 보류`).
- 승인 대기 칸과 같이 있을 때 승인 대기 칸은 그대로 승인 기록.
- 승인된 칸의 빈 위치 번호 2.71(목표 좌표·이름 있음) → `Store Preset 2.71` 이 그 큐의 `At Preset 2.71` 보다 앞, 같은 묶음에서 송신, `match: True`. 목표 좌표 없으면 보류 + 「이미 승인된 칸」.
- 표식 `held`/`create`, 에미터 `held_cells` 단위 시험(보류 칸이 큐 번호를 안 먹음).

## 기존 시험에 생긴 변화 (의도된 것)
- t563·t572·t576 시험의 승인된 칸은 `1.1`·`2.2` 등을 가리키는데 가짜 콘솔에 프리셋 풀이 없었다 → 이제 「풀 못 읽음」으로 보류되어 13건 실패. 새 동작이 맞다(fail-closed). 픽스처에 풀 1~4(slot 1~5)를 심었다(`_EXISTING_PRESET_POOLS`).
- t595 시험 4건의 `"approved"` 기대 → `"held"`/`"create"` 로 갱신. 「승인된 칸만 가리키면 만들지 않는다」 시험은 뜻이 뒤집혀 「만든다」로 바꿨다.

## 검증 (이 트리, 이 세션)
- 묶음 회귀(beat_grid·web_beat_grid·t577·t590·t592·t595·t549·t551·t548·prechk·write census·t600) → `674 passed, 1 skipped` (`regression.txt`).
- 서버 전체 `uv run pytest server -q` → `15437 passed, 35 skipped` (`full-server.txt`, load 9).
- UI `npx tsc --noEmit` exit 0 · `npx vitest run` → `55 files, 1213 passed`.
- `ruff check`(바꾼 파이썬 8파일) → `All checks passed!`, `ruff format` 적용.
- 뮤테이션(각각 `git checkout --` 로 되돌림, 뒤에 `git status` 깨끗):
  - A 세션→에미터 `held_cells` 끊기 → `5 failed, 4 passed`
  - B 승인된 번호를 판독 목록에서 빼기 → `6 failed, 3 passed`
  - C 에미터가 `held_cells` 무시 → `6 failed, 3 passed`
  - D 표식에 `approved` 상태 되살리기 → `1 failed, 8 passed`

## 안 잰 것 / 남은 위험
- **실기 콘솔 0회.** 가짜 콘솔만. 실기에서 승인된 칸이 보류될 때 승인 카드 문구를 감독이 눈으로 본 적 없다.
- **반영 때 콘솔 읽기가 늘었다.** 이제 승인된 칸이 쓰는 풀도 반영마다 읽는다(풀 번호당 1회 완전 판독). 승인된 칸이 많은 곡은 반영 전 판독 시간이 늘 수 있다 — 재지 않았다.
- **풀을 못 읽으면 승인된 칸도 막힌다.** 전에는 그냥 나가던 칸이다. 콘솔 판독이 불안정한 환경에서는 「보낼 게 없음」이 더 자주 뜰 수 있다(의도된 fail-closed).
- 재반영 때 보류된 승인 칸은 콘솔의 옛 큐를 그대로 둔다(t572 「막혀서 그대로 둔 칸」과 같은 길) — 그 표시 문구를 승인 카드에서 따로 확인하지는 않았다.
- t593(효과)·t594(색)가 들어오면 `create_on_apply` 판정과 이 반영 묶음을 그 종류까지 넓혀야 한다(카드 본문 그대로).
- SPEC 잔여 드리프트(manager-spec 보고, 이 카드 밖): HISTORY 에 t592·t595 개정 행이 없고, AC-016 (w-1)~(w-5) 「전부 미구현」 표기, plan.md M12 「착수 전」 머리말이 낡았다 → sync 카드 몫.
