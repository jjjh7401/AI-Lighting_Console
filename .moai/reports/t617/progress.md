# t617 — `store_sequence_commands` 필드 제거

- 기준: origin/main `bd476393` (t616 머지 반영). 브랜치 `WT-drop-store-seq-field`.
- t615 뒤 이 필드는 항상 빈 튜플이었다. 소비처를 grep 으로 전수 확인(추적 파일 기준):
  `beat_grid_emit.py`(정의·`commands` 프로퍼티·생성 2곳), `beat_grid_send.py`(필터 후 `replace` 인자),
  `web/session.py`(칸 목록 재구성), 시험 2곳(`== ()` 단언). 의미 재정의가 아니라 **제거**.
- 동작 변화 없음: `commands` 는 `cue 줄 + 배정 줄` 그대로(빈 튜플 + … 이던 것).
- 건드리지 않은 것: `.moai/reports/t549/gen_sample.py`(과거 보고서 스크립트, 현재 코드로 돌지 않음).

## 증거 (이 트리에서 실행)

1. 시험 먼저: 두 단언을 「필드가 없다」로 바꾸자 수정 전 `2 failed, 34 passed`.
2. 제거 후 `-k "beat_grid or songcue or approval"`: `1132 passed, 2 skipped, 14604 deselected`.
3. `ruff check` — All checks passed / `ruff format --check` — 5 files already formatted.

## Gaps

- 전체 서버 시험은 CI 에 맡김. 콘솔 송신 0건.
- `gen_sample.py` 는 실행해 보지 않음(제거로 깨짐 — 과거 보고서 산출용 스크립트).
