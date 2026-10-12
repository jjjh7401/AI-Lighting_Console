# t619 진행 기록 — 혼합 효과 풀 22 슬롯 0 배정 결함

## Card

혼합 효과 풀 번호대(`mixed_all`)가 새 프리셋 번호로 슬롯 0("22.0")을 내줬다. 콘솔에는 슬롯 0이 없다. 실기 콘솔에서 풀 22에 슬롯 1 "Piano Solo"만 있는 상태로 `Store Preset 22.0`을 보내자, 슬롯 0은 비어 있는 채로 남고 슬롯 2에 "Preset 2"가 새로 생겼다. 원인은 두 곳이다. `server/design/beat_grid_data/preset_pools.yaml`의 `mixed_all` 시작값이 `"22.0"`이었고, `first_free_preset_number`는 정책의 시작 슬롯부터 그대로 돌았다. 이 카드는 `first_free_preset_number`가 슬롯 0을 배정하지 않게 막고, 출하 정책의 시작 슬롯을 `"22.1"`로 고친다.

## Reproduction

RED 커밋 `a47982cc`(rebase 전 `3385912b`). 소스를 고치기 전 `server/tests/test_preset22_slot_zero_t619.py`(시험 4건)를 실행했다.

명령: `uv run pytest server/tests/test_preset22_slot_zero_t619.py -q` (exit=1)

```
E       AssertionError: assert ('22.0', None, None) == ('22.2', None, None)
E       AssertionError: assert ('22.0', None, None) == ('22.1', None, None)
E       AssertionError: assert ('22.0', None, None) == ('22.2', None, None)
E       AssertionError: assert '22.0' == '22.1'
=========================== short test summary info ============================
FAILED server/tests/test_preset22_slot_zero_t619.py::test_shipped_policy_skips_slot_zero_when_piano_solo_is_the_only_preset
FAILED server/tests/test_preset22_slot_zero_t619.py::test_shipped_policy_offers_slot_one_on_empty_pool
FAILED server/tests/test_preset22_slot_zero_t619.py::test_stale_policy_declaring_slot_zero_never_offers_it
FAILED server/tests/test_preset22_slot_zero_t619.py::test_shipped_mixed_band_starts_at_slot_one
4 failed in 0.16s
```

로그 전문: `.moai/reports/t619/red.log`

## Fix

FIX 커밋 `bab96e8f`(rebase 전 `ce5050b8`). 바꾼 줄은 8줄 추가, 6줄 삭제다. 이 두 커밋은 하위 에이전트의 워크트리 브랜치 `worktree-agent-ab0c7229a5428f50d`에서 만들어졌고, 오케스트레이터가 `WT-preset22-start`로 fast-forward 했다. 그 뒤 origin/main `b673f451`(PR #662 merge) 위로 rebase했다. rebase 때문에 SHA가 바뀌었을 뿐 내용은 같다.

- `server/design/beat_grid_data/preset_pools.yaml`: `mixed_all` 시작값을 `"22.0"`에서 `"22.1"`로 바꿨다. 바로 위에 이유를 적은 주석 한 줄을 달았다. 나머지 번호대는 손대지 않았다.
- `server/design/beat_grid_presets.py`: `first_free_preset_number`의 반복을 `range(max(slot_start, 1), slot_end + 1)`로 바꾸고 주석 한 줄을 달았다. 정책 파일이 낡아 슬롯 0을 다시 선언하더라도 슬롯 0은 후보에 오르지 않는다.
- `server/tests/test_mixed_pool_by_number_t607.py`: 옛 결함을 기대값으로 굳혀 둔 단언 두 개(`preset_no == "22.0"`, `number == "22.0"`)를 `"22.1"`로 바꿨다. "22.0을 내준다"고 적힌 낡은 주석 두 줄도 새 동작에 맞게 고쳤다.

## Verification

하위 에이전트 실행 (exit=0, rebase 전):

```
...................................................                      [100%]
51 passed in 1.34s
```

ruff (대상: `server/design/beat_grid_presets.py`, `server/tests/test_mixed_pool_by_number_t607.py`, `server/tests/test_preset22_slot_zero_t619.py`):

```
All checks passed!
check exit=0
3 files already formatted
format exit=0
```

오케스트레이터 재실행 (rebase 전 `ce5050b8`, 이 워크트리):

- `uv run pytest server/tests/test_preset22_slot_zero_t619.py server/tests/test_mixed_pool_by_number_t607.py server/tests/test_new_preset_dialog_t589.py -q` → `51 passed in 1.69s`
- `uv run pytest server/tests/test_beat_grid_presets_t551.py server/tests/test_beat_grid_effect_kind_t557.py -q` → `25 passed in 0.19s`
- `uv run ruff check` (위 3개 파일) → `All checks passed!`
- `uv run ruff format --check` (위 3개 파일) → `3 files already formatted`

rebase 후 (origin/main `b673f451` 위, 같은 코드):

- 5개 시험 파일 → `76 passed in 0.59s`
- `ruff check` → `All checks passed!`, `ruff format --check` → `3 files already formatted`

## Probe — 차용 결함을 시험이 잡는지 확인 (오케스트레이터 실행)

목적: 고친 뒤에도 "다른 풀의 점유를 빌려 쓰는" 결함을 시험이 잡는지 확인한다.

방법: `server/design/beat_grid_presets.py`의 후보 점유 조회 `console_children.get(pool_no)`를 `console_children.get(21)`로 임시로 바꿔, 풀 21 점유를 빌려 쓰게 한 뒤 같은 3개 파일을 돌렸다. 확인이 끝난 뒤 `git checkout -- server/design/beat_grid_presets.py`로 복원했고, `git diff HEAD --stat`은 비어 있다.

결과: `7 failed, 44 passed in 0.51s`

- t589 실패 4건: `test_first_free_slot_in_an_empty_band`, `test_skips_a_number_the_console_already_occupies`, `test_skips_an_occupied_slot_whose_name_is_empty`, `test_a_different_pools_children_never_mark_a_candidate_occupied`(교차 점유 단위 시험)
- t619 실패 3건: `test_shipped_policy_skips_slot_zero_when_piano_solo_is_the_only_preset`, `test_shipped_policy_offers_slot_one_on_empty_pool`, `test_stale_policy_declaring_slot_zero_never_offers_it`. 풀 21 조회가 None이 되어 "빈칸 미확인" 경고 경로로 빠지며 실패했다(간접 실패).
- t607 실패 0건.

## Commits

rebase 후 SHA (origin/main `b673f451` 위):

```
bab96e8f fix(t619): 혼합 효과 풀 22 번호대를 슬롯 1부터 배정 (카드 t619)
a47982cc test(t619): 혼합 효과 풀 22 슬롯 0 배정 재현 시험 추가 (카드 t619)
```

이 기록 커밋(`docs(t619): 진행 기록 ...`)은 이 두 커밋 위에 있다.

## Not verified

- 전체 시험은 돌리지 않았다. 관련 파일(t551, t557, t589, t607, t619)만 돌렸다. `test_preshow_runner.py`, `test_web_dash.py`는 실행하지 않았다(정책 값을 기대하지 않는다는 점은 grep으로만 확인했다).
- 실기 콘솔에서 재확인하지 않았다(콘솔 통신 0건이 이 카드의 조건이다).
- `test_beatgrid_runner.py:136`의 `"preset:22.0": "empty"`는 정책이 아니라 러너 페이로드의 대상 목록으로 보여 그대로 두었다. 실행해서 확인하지는 않았다.
- YAML은 ruff 대상이 아니어서 린트하지 않았다. 대신 `load_preset_pool_policy()`가 시험 d에서 `"22.1"`을 읽는 것으로 파싱을 확인했다.
- 모듈 독스트링 9행에 `22.0~22.99`가 남아 있다. 역사 설명으로 두었다.
- **t607 시험 공백 (프로브로 확인, 하위 에이전트 보고를 정정):** 프로브에서 t607 시험은 하나도 실패하지 않았다. 따라서 `test_pool_21_occupancy_never_blocks_a_pool_22_candidate`(156행), `test_a_slot_free_in_21_but_occupied_in_22_is_correctly_skipped`(168행), `test_renaming_the_pools_arbitrarily_gives_the_same_result`(219행)는 차용 결함을 잡지 못한다. 하위 에이전트가 "22.8이 나와 여전히 잡는다"고 쓴 `test_pool_21_occupancy_does_not_block_assignment_from_pool_22`(203행)도 이 프로브에는 반응하지 않았다. 실제 세션 경로는 풀 22만 읽어서 풀 21 점유가 들어오지 않기 때문이다. 차용을 잡는 단위 시험은 t589의 `test_a_different_pools_children_never_mark_a_candidate_occupied`다.
- 후속 권고(예상, 아직 실행 확인 전): t607의 156·219에서 풀 21 점유를 슬롯 0에서 슬롯 1로 옮기고, 168에서 풀 22 점유를 슬롯 1로 옮겨 기대값을 `"22.2"`로 바꾸면 차용을 다시 잡을 것으로 보인다. 이 PR에는 넣지 않고 후속 카드 후보로 남긴다.
