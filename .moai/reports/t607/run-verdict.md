# t607 run 판정 — 새 프리셋 창 효과 번호 배정이 풀을 번호로 읽는다

판정: **PASS** (콘솔 쓰기 0)
브랜치 `WT-mixed-pool-number` · 기준 origin/main `da01ae82` · 구현 커밋 `d6463a0d`

## 결함 (t604 에서 찾음)
- 실측(`.moai/reports/t543/r1_pools.json`): 이름 "All 1" = 풀 21(슬롯 1~7, 301), "All 2" = 풀 22(슬롯 1 "Piano Solo").
- 창의 효과 번호 배정은 혼합 종류를 **이름** "All 1" 로 읽었다(풀 21). 하지만 번호대는 `mixed_all: 22.0~22.99` 다. `first_free_preset_number` 는 후보의 풀 번호를 대조하지 않아서, 풀 21 의 점유로 22.x 의 빈칸 여부를 판정했다. 풀 22 의 실제 점유는 창에 보이지 않았다.

## 고친 것
1. `read_effect_pools_by_number`(`server/design/beat_grid_presets.py`, 새 함수): 종류의 번호대가 가리키는 **풀 번호**(`preset_pools.yaml`)로 직접 읽는다. 이름 규칙은 0개다. 디머처럼 서브 밴드가 같은 풀이면 한 번만 읽는다. 못 읽은 풀은 지도에 넣지 않는다.
2. `first_free_preset_number`: 콘솔 점유를 `{풀 번호: {슬롯: 이름}}` 로 받는다. 후보 `pool.slot` 은 **자기 풀 번호의 판독으로만** 대조한다. 그 풀을 못 읽었으면 예전처럼 배정하고 「⚠ 콘솔 빈칸 미확인」 경고를 단다(문구 그대로).
3. 세션 창(`beat_grid_new_preset`)이 위 함수를 쓴다. t595 빈 프리셋 표식용 판독 기억(`_beat_grid_pool_slots[풀 번호]`)도 유지한다.

## 증거 (이 트리 `d6463a0d`, origin/main 대비 0 뒤)
- `uv run pytest -q -p no:cacheprovider -o addopts=""` 대상: t607 · t589 · t603 · t599 · t594 · t595 · t593 · t600 · t598 → `255 passed in 2.33s`
- `ruff check`(4 파일) → `All checks passed!` · `ruff format --check` → `4 files already formatted`
- 뮤테이션: 후보 풀 번호를 무시하고 처음 읽힌 풀을 쓰게 바꾸면(옛 동작) → `3 failed, 44 passed`(t607 2건, t589 1건). 되돌린 뒤 `git status` 깨끗함.
- 구현 에이전트 보고: 구현 두 파일만 되돌렸을 때 RED 확인(t589 3 failed + 새 모듈 ImportError). 이 항목은 내가 재현하지 않았고 위 뮤테이션으로 대신했다.
- 새 시험이 덮는 것: 실측 꼴(21/22)에서 22.1 을 고르지 않음, 풀 이름을 아무렇게나 바꿔도 결과 동일, 풀 22 판독 실패 → 경고 달고 배정, 위치·색·디머 효과도 자기 풀 번호로.

## 일부러 안 고친 것 (범위 밖)
- 이름으로 효과를 찾는 기능(`resolve_effect_preset_name`, `EFFECT_SEARCH_POOL_NAMES` 의 "All 1")과 페이저의 "All 1" 판독. 둘 다 쇼에 원래 있는 All 1 프리셋(실측: DIM-PULSE 등 풀 21)을 이름으로 찾는 정당한 판독이고, 창의 번호 배정과 코드 경로를 공유하지 않는다.
- `effect_kind_to_pool_name` 은 이제 부르는 곳이 없다. 지우지 않았다(드라이브바이 삭제 금지). 리드가 원하면 정리 카드로.

## 안 잰 것
- 실기 콘솔 0회. 전체 시험은 CI 에 맡긴다.
- 쇼 파일마다 번호대 풀 번호 자체가 맞는지는 `preset_pools.yaml`(`confirmed: false`)의 숙제로 남는다.
