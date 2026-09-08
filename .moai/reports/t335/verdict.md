# t335 — 무엇이 모드를 풀었는지가 보고에 실린다 (+ t333 결함 하나 회수)

- 카드: t335
- 측정: 2026-09-08, 실기 onPC, 응답기 1.6.5, 회신 포트 9005
- 기준 트리: `.claude/worktrees/t335`, 브랜치 `WT-resolved-by-visible`, base `802d2b9`
- **콘솔 쓰기 0건**

## 1. Claim (주장)

1. `resolved_by` 가 **행마다** 보고에 실린다 — 런과 건너뛴 행 양쪽. 실기에서 `{"width_unique": 62, "console_mode": 24}` 로 t333 의 62/24 분할이 처음으로 눈에 보인다.
2. **키 표가 아니라 행에 실었다.** `mode_resolutions` 는 `(타입, 폭, 라벨)` 키마다 하나라 같은 키의 행이 갈리면 표현할 자리가 없다.
3. 🔴 **그 설계를 검증하다 t333 의 실제 결함을 회수했다** — t333 은 자리 판독 결과를 키 표에 써 넣었고, 같은 키의 다음 행이 그것을 물려받아 **자기 자리에 임자가 없는데도** 확정되어 쓰기 계획이 됐다. 관측성 문제가 아니라 정합성 문제다(§2.2).
4. 페이로드 크기 델타는 **+3,674 bytes (+7.2%)** — 추정이 아니라 실측이다(§2.4).

## 2. Evidence (증거)

### 2.1 실기 — 분할이 보인다

```
uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview --listen-port 9005
```

digest:
```json
{"runs": 0, "write_count_planned": 0, "skipped_total": 86,
 "skipped_by_kind": {"already_patched": 86},
 "resolved_by": {"width_unique": 62, "console_mode": 24}, ...}
```

행 단위 대조(`plan.skipped` 전수 집계):
```
Counter({('already_patched', 'width_unique'): 62,
         ('already_patched', 'console_mode'): 24})
```

t333 회차에는 `already_patched: 86` 만 있었고 그 86이 무엇으로 만들어졌는지는 페이로드 어디에도 없었다. 이제 **실기 관측 자체가 메커니즘을 증언한다** — t333 의 gap 4-2 가 닫혔다. 원문: `live-preview-with-resolved-by.json`.

### 2.2 🔴 t333 결함 회수 — 자리 판독이 키를 통해 샜다

t333 은 이 코드를 심었다:

```python
if from_seat is not None:
    mode = from_seat
    if mode_resolutions[resolution_key].resolution != "resolved":
        mode_resolutions[resolution_key] = from_seat   # ← 여기
```

그 바로 위 캐시 주석이 금지한 일이다: **같은 키의 다음 행이 그 값을 물려받는다.** 그러면 자기 자리에는 임자가 없는 행이 그 모드로 확정되고, `mode_unresolved` 로 걸러지지 않고 **`placeable` 로 넘어가 런이 된다** — 이 앱에 실행 취소는 없으므로 되돌릴 수 없는 쓰기로 이어지는 경로다.

**t333 회차에 드러나지 않은 이유**: 그 쇼의 Aura 24행이 **전부** 자리에 임자를 가져, 물려받은 값과 실측값이 우연히 같았다. 임자가 일부에만 있는 배치가 그 우연을 제거한다.

**어떻게 잡혔나**: t335 의 `test_a_key_whose_rows_split_reports_per_row` — 임자를 첫 행에만 두는 배치 — 가 `KeyError` 로 터졌다. 나머지 행이 `skipped` 에 없었기 때문이고, 그 행들은 **런이 되어 있었다.**

수정: 키 표에 쓰지 않는다. 표는 라이브러리 판독의 결과로 남고, 행마다 다른 해석은 행에 실린다.

회귀 고정: `test_a_seat_resolution_never_leaks_to_a_row_with_no_seat` — 단언의 핵심은 「나머지 행이 런이 되지 않는다」다. 해석이 새면 그 행은 건너뛴 행이 아니라 런으로 나타나고, 그것이 쓰기로 이어지는 경로다.

**t333 의 시험 하나가 이 결함을 단언하고 있었다.** `test_console_mode_resolves_what_the_library_read_cannot` 이 키 표의 `resolution == "resolved"` 를 확인했는데, 그 표에 쓰는 행위가 곧 누출이었다 — 시험이 검사하던 통로가 누출 통로였다. 단언을 행으로 옮기고 이유를 시험 안에 적었다.

### 2.3 단위 시험 — 신설 16개

```
uv run pytest server/tests/test_lxseq_resolved_by_visible.py \
              server/tests/test_lxseq_console_mode.py -q
→ 51 passed
```

| 시험 | 고정하는 것 |
|---|---|
| `test_a_run_carries_what_resolved_its_mode` | 런에 해석이 실린다 |
| `test_a_run_resolved_by_override_says_so` | 같은 모드 이름도 무엇이 정했는지가 갈린다 |
| `test_an_already_patched_row_says_what_resolved_it` | 62/24 분할이 보이는 자리 |
| `test_a_row_skipped_before_the_mode_was_decided_reports_none` | 못 풀었으면 `None` — 빈 문자열·`"unknown"` 이 아니다 |
| `test_a_type_unresolved_row_reports_none` | 타입 미해석 행도 같은 규율 |
| `test_a_key_whose_rows_split_reports_per_row` | 🔴 키가 갈릴 때 행마다 다르게 보고 |
| `test_the_key_table_alone_would_have_been_misleading` | 위 시험의 전제를 명시 — 키는 하나, 행은 여럿 |
| `test_the_plan_aggregates_resolved_by` | 집계 |
| `test_the_aggregate_counts_runs_and_skipped_together` | 런과 건너뛴 행을 함께 센다 |
| `test_the_aggregate_total_always_equals_the_row_count` | 5가지 조합에서 합 = 행 수 |
| `test_an_unresolvable_seat_leaves_the_row_uncounted_as_resolved` ×3 | 못 푼 자리는 `None` |
| `test_a_seat_resolution_never_leaks_to_a_row_with_no_seat` | 🔴 t333 회귀 |
| `test_the_key_table_stays_at_the_library_read_verdict` | 표는 라이브러리 판독 결과로 남는다 |
| `test_every_run_reports_a_resolution_from_the_vocabulary` | 런이 해석을 잃지 않는다 |

**공허성 방어**: `_records()` 가 행 수 ≥ 2 를 단언한다 — 행이 하나면 「행별 vs 키별」 구별을 만들 수 없어 핵심 시험들이 조용히 공허해진다. 합계 시험은 5가지 갈래 조합을 돌려 「세지 못한 행」이 생기면 깨진다.

### 2.4 페이로드 크기 — 실측

| | bytes |
|---|---|
| t333 (변경 전) | 51,192 |
| t335 (변경 후) | 54,866 |
| 델타 | **+3,674 (+7.2%)** |
| 행당 | 42.7 bytes × 86행 |

카드가 「먼저 정할 것」으로 지목한 항목이다. 추정으로 넘기지 않고 같은 쇼·같은 명령으로 재서 비교했다.

### 2.5 회귀 · 린트

```
uv run pytest server/tests -q
→ 12089 passed, 35 skipped (3분 25초)   [t333: 12073 → +16]

uv run ruff check server/          → All checks passed!
uv run ruff format --check server/ → 547 files already formatted
```

## 3. Baseline-attribution (baseline 귀속)

- 트리 `.claude/worktrees/t335` · 브랜치 `WT-resolved-by-visible` · base `802d2b9`
- 정본 CSV: `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` (86행)
- 크기 비교 기준: `.moai/reports/t333/live-preview-after.json` (커밋된 파일)
- 실기 응답기 `1.6.5` · 포트 9005

## 4. Gaps (미검증)

1. 🔴 **한 런에 해석이 섞이지 않는다**를 시험으로 증명하지 못했다. `boundary_key` 에 `resolved_by` 를 넣어 막았지만, 섞임을 만들려면 같은 타입에서 CSV 라벨이 다른 두 키가 같은 콘솔 모드·같은 폭에 닿아야 하고 정본 fixture 에는 타입마다 라벨이 하나뿐이다. `test_every_run_reports_a_resolution_from_the_vocabulary` 는 **그 주장을 하지 않는다** — 런이 해석을 잃지 않는다만 고정한다. 방어는 코드 주석으로만 지켜진다.
2. **t333 누출이 실기에서 오답을 냈는지는 확인할 수 없다.** 그 쇼는 24행 전부 임자가 있어 물려받은 값과 실측값이 같았다 — 즉 t333 의 86/0 결과는 이 결함에도 **옳았다**. 다른 쇼에서 틀렸을 것이라는 것은 코드 독해와 단위 시험의 결론이고 실기 관측이 아니다.
3. **`apply` 경로 여전히 미실측** (t333 그대로). 이 쇼는 86대가 다 차 있어 확인할 행이 없다.
4. `boundary_key` 변경이 런 분할을 바꿀 수 있다 — 이 쇼에서는 런이 0개라 **분할 변화를 관측하지 못했다.** 전체 시험이 통과했다는 것이 유일한 신호다.
5. 미사용 타입 6종·라이브러리 폭·응답기 빌드 대조 — t333 그대로.

## 5. Residual-risk (잔여 위험)

- **`boundary_key` 에 성분을 더한 것은 관측성 카드의 범위를 넘는다.** 런 분할이 달라질 수 있고, 그 결과는 `patch_fixtures` 호출 횟수와 런당 대수의 변화다. 이 쇼는 런 0개라 그 변화를 볼 수 없었다. 넣지 않으면 런의 `resolved_by` 가 머리 행의 거짓이 되므로 **거짓을 싣는 것과 분할을 건드리는 것 중** 후자를 택했다(§7).
- **`None` 을 `"null"` 문자열로 바꿔 JSON 키로 쓴다.** 모드 이름에 `"null"` 이 있을 수는 없으나 충돌 가능성을 원리적으로 배제한 것은 아니다.
- 집계는 런을 `count` 로, 건너뛴 행을 1로 센다. 두 단위를 한 표에 담으므로 「행 수」의 의미가 「대수」다 — 런이 여러 대를 묶을 때 그 표는 대수를 말한다. 시험이 합 = 행 수를 고정하지만 이 쇼는 런 0개라 그 등식이 런 쪽에서 실기 검증되지 않았다.

## 6. 무엇을 어떻게 바꿨나

- `SkippedRow.resolved_by` · `PatchRun.resolved_by` 추가. 모드 확정 **전에** 걸러진 행은 `None` — 빈 문자열이나 `"unknown"` 으로 채우면 「풀렸는데 이름을 잃었다」와 구별되지 않고, 두 상태는 감독의 다음 행동이 다르다.
- `ImportPlan.resolved_by_counts` — 런(`count`)과 건너뛴 행(1)을 **함께** 센다. 한쪽만 세면 합이 행 수에 못 미치고 그 결손은 「0건이었다」로 읽힌다.
- 자리 판독 결과를 키 표에 쓰지 않는다 (§2.2).
- `boundary_key` 에 `resolved_by` 추가 (§5).
- 페이로드: `runs[].resolved_by` · `skipped[].resolved_by` · `plan.resolved_by_counts`; digest `resolved_by`.

## 7. 범위를 넓힌 곳 — 고지

카드는 관측성만 요구했다. `boundary_key` 변경은 그 범위를 넘고, 런 분할이라는 **동작**을 건드린다.

넓힌 이유 하나: 넣지 않으면 런의 `resolved_by` 가 머리 행의 값이 되어 **보고가 거짓이 될 수 있다.** 도달 가능한 조합이다(같은 타입, 다른 CSV 라벨, 같은 콘솔 모드·폭). 관측성을 붙이는 카드가 거짓말하는 필드를 싣는 것은 목적에 반한다.

기존 코드가 폭에 대해 이미 같은 처방을 걸어 두었고(`폭이 빠지면 … 런 폭은 머리 행 값이 된다`) 그 주석을 근거로 삼았다. 그래도 이것은 승인 범위 밖이므로, 되돌리길 원하시면 `boundary_key` 한 줄과 관련 주석만 빼면 됩니다 — 그 경우 §4-1 의 미검증이 「미검증」에서 「알려진 거짓 가능성」으로 승격합니다.
