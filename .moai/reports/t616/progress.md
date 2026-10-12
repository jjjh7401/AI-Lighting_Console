# t616 — 자동 Cue 1 이 있는 시퀀스는 Cue 2 부터 저장 (감독 결정 A안)

- 기준: origin/main `01d1c843` (t615 머지 반영). 브랜치 `WT-reapply-cue2`.
- 변경: `server/design/beat_grid_emit.py` — 소유 기록에 이름은 있고 큐가 0개인 트랙의 첫 큐 번호를 2 로.
  `recorded_cue_numbers` 에 키가 없거나(미소유) 기록이 비어 있지 않으면 종전 그대로.
- 기존 큐는 건드리지 않음. `beat_grid_send.py` 변경 없음(기록된 마디가 아니므로 `/Overwrite` 안 붙음).

## 증거 (이 트리에서 실행)

1. 재현 시험 먼저 — 수정 전: `3 failed, 2 passed`
   (`server/tests/test_beat_grid_reapply_cue2_t616.py`; 실패 3건 = 빈 기록 트랙이 Cue 1 을 받음 / 저장 줄 / 다음 기록 `{2: 1}`).
2. 수정 후 관련 시험: `50 passed` (t616 + t615 + t572 + t576).
3. 수정 후 `-k beat_grid` 전체: `496 passed, 15242 deselected`.
4. `ruff check` — All checks passed / `ruff format --check` — 2 files already formatted.

## Gaps (안 잰 것)

- 콘솔 송신 0건(지시). `Store Sequence S Cue 2` 는 t615 live p3 선례, 뒤따르는 `TrigTime` 줄만 실기 미확인.
- 사람이 콘솔에서 직접 넣은 큐가 있는 시퀀스는 구별 못 함 — 이 변경은 번호 2 부터라 덮어쓰지 않는다.
- 전체 서버 시험(15k)은 돌리지 않음 — CI 에 맡김.

## Residual risk

- 시퀀스에 빈 자동 Cue 1 이 영구히 남는다(수동 Go 시 한 번 지나감). 정리하려면 `Delete Cue` 문법 실기 확인 필요.
