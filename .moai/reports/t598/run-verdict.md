# t598 run 판정 — 승인 창 사이 콘솔에서 채워진 번호를 덮어쓰지 않게 송신 직전 재판독

브랜치 `WT-presend-reread` · 기준 origin/main `1c8e4647`(EnterWorktree 가 한 머지 뒤 `f8d7a8a9` 에서 시작해 착수 전에 `git merge --ff-only origin/main` 으로 맞춤, `git merge-base --is-ancestor 1c8e4647 HEAD` → OK) · 콘솔 쓰기 0건(가짜 콘솔만)

## 판정: PASS — 카드 문면에서 하나 바꿈(리드 승인으로 변경)
카드 문면은 「그 줄 보류 + 승인 카드에 사유」였다. **리드 승인(2026-10-12)으로 「묶음 전체 0줄 + 사유」로 변경**했다. 이유: 승인·실행은 `gate.screen` 안에서 승인 → lock-first 재확인 → 백업 → 전부 실행이 한 번에 일어난다. 승인 뒤에 그 줄만 빼면 승인한 것과 보낸 것이 달라지고, 만들기 줄이 빠진 번호를 부르는 큐 줄까지 같이 빼야 한다. 감독이 본 카드와 다른 묶음이 나가는 것이다. 그래서 같은 자리의 lock-first 선례(승인 중 잠금 → 묶음 전체 중단)를 따랐다. 다시 반영하면 그 번호는 t590 규칙대로 「이미 있는 번호」로 판정되어 만들기 줄이 붙지 않는다.

리드 조건 셋:
- ① 사유가 전체화면 런북에 보일 것 → 됨. 다만 t597 거절 사유 길(편집 답장, `editRejectionFor`)은 반영 상태(`beat_grid_send_status`)와 출처가 달라 재사용하지 못했다. 대신 격자 상단 바 바로 아래에 `⚠ 콘솔에 반영 안 됨 — <사유>` 줄을 새로 붙였다. **발견: 이 카드 전에는 화면 어디에서도 반영 실패 사유를 그리지 않았다**(`reason`·`blocked_cells`·`approval_vs_sent` 를 쓰는 곳이 `protocol.ts` 말고 0곳 — `grep -rln "approval_vs_sent\|blocked_cells\|pending_apply_count" ui/src` → `ui/src/protocol.ts` 하나). 그래서 이 줄은 t598 사유만이 아니라 반영 실패 사유를 전부 보인다.
- ② 콜백이 `None` 일 때 바이트 동일 → `TestGateRecheckHook.test_none_recheck_is_byte_identical`(필드 없음과 `recheck=None` 의 `ScreenDecision` 이 같고, `BatchRisk` 도 같다).
- ③ 재판독이 「못 읽음」이어도 중단 → `TestPoolUnreadableOnReread`.

## 구멍 (고치기 전 재현)
`uv run pytest server/tests/test_presend_reread_t598.py`(구현 전) → `6 failed`. 승인 창 안에서 가짜 콘솔의 위치 풀에 71 을 채웠는데 반영이 `ok: True` 로 끝났다 — `Store Preset 2.71` 이 이미 채워진 번호에 나갔다(덮어씀):
```
E       assert True is False      (test_presend_reread_t598.py:68 — status["ok"])
E       assert True is False      (:81 — 다시 못 읽어도 그대로 송신)
E       AssertionError: assert 'DataPool/PresetPools/2' in []   (:105 — 송신 직전 재판독 없음)
E       TypeError: BatchRisk.__init__() got an unexpected keyword argument 'recheck'  (×3)
```

## 고친 것
- `server/safety/gate.py` — `BatchRisk.recheck`(선택, 기본 `None`, `compare=False`). `screen()` 이 승인 뒤·lock-first 재확인 바로 뒤에 부른다. 사유가 오면 `status="blocked_precondition"`, 0줄 실행, 명령마다 감사 `blocked`, `notice` = 사유. 거절된 묶음에서는 부르지 않는다.
- `server/web/session.py` `beat_grid_apply` — 묶음이 프리셋을 만들 때만(`position_plan.creations`) recheck 를 싣는다. `_beat_grid_recheck_new_presets` 가 그 풀을 다시 완전 판독한다. 채워졌으면 「승인 창이 떠 있는 사이 콘솔에서 2.71이(가) 채워져, 덮어쓰지 않으려고 아무것도 보내지 않았습니다 — 다시 반영하세요」, 다시 못 읽으면 「송신 직전 프리셋 풀을 다시 읽지 못해 … — 다시 반영하세요」. 승인 기록 없음. 새로 읽은 풀은 표식 출처로 남긴다(`_beat_grid_learn_pools`). 상태 문구표에 `blocked_precondition` 추가.
- UI `ui/src/components/BeatGrid.tsx` `applyFailureNote` + `.beat-grid-apply-fail`(`ui/src/styles.css`).
- SPEC(같은 PR, manager-spec): REQ-LDBEAT-015 **(i-10)(i-10-1)~(i-10-4)**, AC-LDBEAT-016 **(w-7)**, plan.md M12 한 단계, version 0.5.3→0.5.4. REQ 25·AC 25 불변. 표 구조 확인: 바뀐 행의 이스케이프 안 된 `|` 개수가 HEAD 와 같다(AC-016 11, REQ-015 매핑 3).

## 검증 (이 트리, 이 세션)
- `uv run pytest server/tests/test_presend_reread_t598.py` → `6 passed`.
- 서버 전체 `uv run pytest server -q` → `15443 passed, 35 skipped` (`full-server.txt`).
- UI `npx tsc --noEmit` exit 0 · `npx vitest run` → `56 files, 1222 passed`(새 `BeatGridApplyFailure.test.tsx` 5개).
- `ruff check`/`ruff format` 바꾼 파이썬 3파일 깨끗.
- 뮤테이션(각각 `git checkout --` 로 되돌림, 끝에 `git status --short` → `?? ui/.moai/`(훅 상태 파일)뿐):
  - A 세션이 recheck 를 안 실음 → `3 failed, 3 passed`
  - B 게이트가 recheck 결과를 무시 → `4 failed, 2 passed`
  - C 다시 못 읽음을 통과로 취급 → `1 failed, 5 passed`
  - D UI 실패 줄 숨김 → `1 failed, 4 passed`

## 안 잰 것 / 남은 위험
- **실기 콘솔 0회.** 실기에서 승인 창 사이 누군가 저장하는 경우는 재현하지 않았다.
- **재판독과 실행 사이에도 아주 짧은 틈이 남는다.** 재판독 직후 백업·실행 사이에 누가 저장하면 여전히 덮어쓴다. 승인 창(사람이 읽는 시간)이라는 큰 틈을 판독 한 번의 작은 틈으로 줄인 것이지 없앤 것은 아니다. 완전히 막으려면 콘솔 쪽 원자적 「비었을 때만 저장」이 필요하다(지금 명령 문법으로는 없음 — 확인 안 함).
- 대상은 이 묶음이 **만드는** 번호뿐이다. 이미 있다고 판정해 그대로 부르는 번호가 승인 창 사이 지워지는 경우는 덮어쓰기 위험이 아니라서 다루지 않았다.
- 재판독은 게이트 안(프로그래머 중재자를 쥔 채)에서 콘솔 읽기를 한다. 가짜 콘솔에서는 문제없었지만, 실기에서 읽기 지연이 길면 중재자를 그만큼 오래 쥔다 — 재지 않았다.
- 반영 실패 줄은 「마지막 반영 상태」만 보인다. 미리보기 등 다른 동작이 오면 그 상태로 바뀌어 사라진다(서버 상태 REPLACE 규칙 그대로).
- t593(효과)·t594(색)가 같은 반영 묶음에 만들기 줄을 붙이면 `position_plan.creations` 만 보는 이 recheck 를 그 종류까지 넓혀야 한다 — lane-2 t593 이 칸 판정을 공용 함수로 빼는 중이라 늦게 합치는 쪽이 맞춘다.
