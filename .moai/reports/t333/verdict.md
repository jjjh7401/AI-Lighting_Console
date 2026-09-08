# t333 — 그 자리의 임자에게 물어 라이브러리 폭 중복을 해소했다

- 카드: t333 (전제 회차는 `preconditions.md`, PR #383 → `4e02016`)
- 측정: 2026-09-08, 실기 onPC, 응답기 1.6.5, 회신 포트 9005
- 기준 트리: `.claude/worktrees/t333`, 브랜치 `WT-mode-slot-resolve`, base `4e02016`
- **콘솔 쓰기 0건** — 두 회차 모두 `apply.entered = false`, `write_count_planned = 0`

## 1. Claim (주장)

1. 라이브러리 판독이 못 좁힌 행을 **그 자리에 이미 앉아 있는 픽스처의 모드**로 확정한다. 실기에서 `mode_overrides` **없이** `already_patched` 62 → **86**, `mode_unresolved` 24 → **0**.
2. 이 변화는 **코드 변경에 귀속된다** — 같은 세션·같은 쇼·수 분 차이로 수정 전 코드를 돌려 62/24 를 재현했다(§2.2).
3. 판별기는 **이름을 비교하지 않는다** — 슬롯으로 조회하므로 t334(같은 이름 타입 둘 중 앞것이 조용히 이긴다)를 원리적으로 우회한다.
4. **능력만 더했다** — 못 풀면 수정 전 동작(`mode_unresolved` + `mode_overrides` 안내)이 그대로 남는다. fail-open 갈래 5종을 테스트로 고정했다.
5. **승인 범위보다 줄였다** — 「페이징 완주」는 필요 없었다(§6).

## 2. Evidence (증거)

### 2.1 단위 시험 — 신설 35개

```
uv run pytest server/tests/test_lxseq_console_mode.py -q
```
```
...................................                                      [100%]
35 passed in 0.07s
```

파서 22 + 갈래 13. 갈래 쪽 내역:

| 시험 | 무엇을 고정하는가 |
|---|---|
| `test_console_mode_resolves_what_the_library_read_cannot` | 폭이 같은 모드 둘일 때 콘솔 임자의 슬롯으로 확정 · `resolved_by == "console_mode"` · 판정은 `already_patched` · 쓰기 0 |
| `test_without_the_branch_these_rows_are_unresolved` | **대조군** — 콘솔에 임자가 없으면 같은 입력이 여전히 못 풀린다 |
| `test_branch_does_not_intercept_a_library_read_that_already_decided` | 기존에 풀리던 갈래를 가로채지 않는다(`width_unique` 유지) |
| `test_an_explicit_override_still_wins` | 감독이 준 값이 콘솔 판독보다 우선 |
| `test_unresolved_survives_when_the_console_mode_cannot_decide` ×5 | 슬롯 미판독 / 라이브러리에 없는 슬롯 / 빈 값 / 판독 실패 / 슬롯 0 → 전부 수정 전 동작 |
| `test_a_different_type_at_that_address_is_not_evidence` | 타입 불일치 → 증거 아님 |
| `test_the_same_type_at_a_different_address_is_not_evidence` | 자리 불일치 → 증거 아님 |
| `test_a_slot_whose_width_was_never_measured_is_not_a_decision` | 폭 미측정 슬롯은 확정이 아니다 |
| `test_an_incomplete_console_read_does_not_feed_the_branch` | 미완전 판독은 계획 자체가 없다 |
| `test_two_fixtures_disagreeing_at_the_same_address_decide_nothing` | 한 자리에 두 모드 → 앞것을 집지 않고 포기 |

**대조군이 왜 필요한가**: 없으면 첫 시험의 통과가 「원래 풀리던 것」인지 「이 갈래가 푼 것」인지 구별되지 않는다. `test_without_the_branch_...` 가 그 구별을 만든다.

**파서 쪽 비공허성**: 거절 케이스 10개만 있으면 「전부 None 을 돌려주는 파서」도 통과한다. `test_parser_is_not_vacuous` 가 그것을 막는다.

### 2.2 실기 대조 — 같은 세션·같은 쇼, 코드만 다름

수정 전 코드를 같은 트리에 되돌려(`git checkout HEAD~1 -- server/prechk/mode_read.py server/lxseq/mapper.py`) 같은 명령을 돌렸다:

```
uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview --listen-port 9005
```

| | CONTROL (수정 전) | AFTER (수정 후) |
|---|---|---|
| `runs` | 0 | 0 |
| `write_count_planned` | 0 | 0 |
| `skipped_total` | 86 | 86 |
| `already_patched` | **62** | **86** |
| `mode_unresolved` | **24** | **0** |
| `types_unresolved` | [] | [] |
| `apply.entered` | false | false |
| `is_error` | false | false |
| `mode_overrides` | 없음 | **없음** |

원문: `live-preview-control-prechange.json` · `live-preview-after.json`.

**이 대조가 t332 의 기준선보다 강하다.** t332 의 62/24 는 약 1시간 전 다른 커밋에서 잰 값이라 「그 사이 쇼가 바뀌었다」는 대안 설명이 남는다. 이 대조는 같은 세션 안에서 코드만 되돌려 수 분 차이로 재현했으므로 그 대안이 닫힌다 — 남은 차이는 코드뿐이다.

복원 후 다시 떠서 86/0 을 재현했다(위 AFTER 열이 복원 후 측정값이다).

### 2.3 회귀 — 전체 시험

```
uv run pytest server/tests -q -x
```
```
12073 passed, 35 skipped, 1 warning in 199.93s (0:03:19)
```

### 2.4 린트·서식

```
uv run ruff check server/prechk/mode_read.py server/lxseq/mapper.py server/tests/test_lxseq_console_mode.py
→ All checks passed!

uv run ruff format --check server/
→ 546 files already formatted
```

## 3. Baseline-attribution (baseline 귀속)

- 트리 `.claude/worktrees/t333` · 브랜치 `WT-mode-slot-resolve` · base `4e02016`
- 정본 CSV: `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` (데이터 86행, Aura XB 24행)
- 실기 응답기 `1.6.5` · 회신 포트 9005 · 콘솔 픽스처 86대
- CONTROL 측정 시각과 AFTER 측정 시각은 같은 세션 안에서 수 분 차이

## 4. Gaps (미검증)

1. **`apply` 경로를 타지 않았다.** 두 회차 모두 preview 다. `console_mode` 로 확정된 폭이 실제 쓰기에서 같은 자리를 밟는지는 코드 독해(`_effective_width` 가 `mode.channels` 를 쓴다)까지이고 실측이 아니다. 🔴이 쇼는 이미 86대가 다 차 있어 `apply` 로 확인할 행이 없다 — 빈 쇼가 필요하다.
2. **`resolved_by` 가 페이로드에 실리지 않는다.** `mode_resolutions` 는 매퍼 밖으로 나가지 않으므로(이 변경 전에도 그랬다) 감독은 **무엇이 이 행을 풀었는지 볼 수 없다** — 62→86 이라는 결과만 보인다. 관측성 개선은 승인 범위 밖이라 하지 않고 후속 카드로 올렸다. 단위 시험이 `resolved_by == "console_mode"` 를 단언하는 것이 현재 유일한 메커니즘 증거다.
3. **한 자리 두 모드**를 실기에서 못 봤다. 이 쇼에는 그런 자리가 없다 — 그 갈래는 단위 시험으로만 고정됐다.
4. **같은 타입이 두 모드로 섞인 쇼**를 못 봤다. 이 쇼는 타입마다 모드가 하나로 균일하다.
5. **라이브러리 폭(`TotalFootprint`)을 직접 재지 않았다.** 매퍼는 `mode_read` 가 준 폭을 쓰고, 그 판독은 기존 코드다. 이 변경이 폭을 새로 만들지는 않는다.
6. **미사용 6종의 `DMXModes`** 는 여전히 열거하지 않았다.
7. **응답기 빌드 대조** 안 함 — 실기 1.6.5 가 이 트리의 `console/lua/copilot_responder.lua` 와 같은 빌드인지 확인하지 않았다.

## 5. Residual-risk (잔여 위험)

- **모드 문자열 형식은 관찰된 규칙이다.** 8종 8건에서 `"<슬롯> <이름>"` 이었을 뿐 콘솔 문서로 확인한 규약이 아니다. 콘솔 버전이 바뀌어 형식이 바뀌면 파서는 `None` 을 돌려주고 **수정 전 동작으로 떨어진다** — 조용히 틀리는 방향이 아니라 조용히 능력을 잃는 방향이다. 그 손실은 `mode_unresolved` 로 보인다.
- **앞 숫자가 슬롯이라는 성질**이 이 판별기의 전제다. 만약 어떤 타입에서 앞 숫자가 슬롯이 아닌 다른 것(예: 모드 번호와 슬롯이 갈리는 라이브러리)이면 **틀린 모드로 확정한다** — 폭까지 그 슬롯의 것을 쓰므로 자리 계산이 갈린다. 8종에서 8/8 이었지만 그것이 규약의 증명은 아니다. 🔴이것이 이 변경의 가장 큰 잔여 위험이다.
- **판정은 `already_patched` 로만 귀결되는 것이 이 쇼의 사정이다.** 자리+타입이 일치하는 임자가 있다는 조건이 곧 `already_patched` 의 조건이므로 원리적으로 그렇지만, 폭이 임자와 다르게 확정되면 `address_occupied` 로 갈 수도 있다. 그 경우를 실기에서 못 봤다.

## 6. 승인 범위보다 줄인 것

착수 승인 시점의 계획 (1)은 「`console_after` 계열 판독을 페이징 완주로 바꾼다」였다. **하지 않았고, 할 필요가 없었다.**

- `read_inventory` 는 이미 전수를 본다 — 이 쇼에서 86대 전부 관측, `missing 0`.
- 잘리던 것은 `console_after` 하나뿐이고(`children_listed: 18`), 그것은 **사후 보고용**이라 해석 단계로 흘러가지 않는다.
- 미완전 판독은 `_judge_console_read` 가 이 갈래보다 **앞에서** 끊는다 — 계획 자체가 서지 않는다. 그 성질을 `test_an_incomplete_console_read_does_not_feed_the_branch` 로 고정했다.

안 고쳐도 되는 것을 고치지 않았다. `console_after` 의 절단은 보고 화면의 문제로 남아 있고, 필요하면 별개 카드다.

## 7. 무엇을 어떻게 바꿨나

### `server/prechk/mode_read.py` — `parse_console_mode_slot`

픽스처 `Mode` 문자열에서 **첫 공백 토큰 하나만** 떼어 슬롯을 얻는다. 이 경계가 장식이 아닌 이유: 실측 모드에 `4 4 channel`·`2 9 channel` 이 있어 **이름 자체가 숫자로 시작한다.** 「숫자를 전부 떼기」류 술어는 둘 다 `channel` 로 만들고, 그 실패는 예외가 아니라 **오답**으로 나타나 계기에 안 잡힌다. `test_parser_keeps_a_name_that_itself_starts_with_a_digit` 가 실측값(슬롯 2 / 나머지 `9 channel`)을 그대로 박아 그 경계를 고정한다.

`None` 은 「이 문자열은 슬롯을 말하지 않는다」이고 부르는 쪽은 그것을 **증거 없음**으로 다룬다. `str.isdigit` 하나로 걸러 부호·소수점·유니코드 숫자꼴이 `int()` 에 닿지 않게 했고, 슬롯은 1부터라 `0` 도 거절한다. 이름이 없는 `"7"` 도 거절한다 — 슬롯만으로는 대조할 것이 없다.

### `server/lxseq/mapper.py` — `_console_mode_slots_by_seat` + `_resolve_mode_from_console_seat`

자리+타입마다 그 자리 임자들이 답한 슬롯 **집합**을 만든다. 집합인 이유: 한 자리에 여러 대가 보고될 수 있고 그때 **앞것을 집으면 안 된다** — 그것이 t334 와 같은 조용한 오답을 이 갈래에 새로 만드는 길이다. 크기가 1일 때만 채택한다.

키에 타입이 들어가는 이유: 어떤 모드인지는 어떤 타입인지가 정해진 뒤에만 의미가 있다. 자리만으로 이으면 다른 타입이 그 자리를 쓰던 경우 그 타입의 슬롯 번호를 이 행의 모드로 읽는데, 번호는 어느 타입에서나 유효해 보여서 그 오답이 조용하다.

해석은 **행 단위**로 판정하고 `(타입, 폭, 라벨)` 키에 캐시하지 않는다. 같은 키의 행들이 서로 다른 자리에 앉아 있어 임자가 있을 수도 없을 수도 있는데, 한 행의 성공을 키에 퍼뜨리면 임자 없는 행까지 그 모드로 확정된다.

`tree_unread` 는 건드리지 않는다 — 그때는 라이브러리 목록 자체가 없어 슬롯을 조회할 대상이 없다.

### 판독 왕복 증가 0건

`FixtureRecord.mode` 와 `ModeChoice.slot` 이 **이미 있었다.** 필요한 데이터가 처음부터 손에 있었고, 해석 단계로 잇지 않은 것이 결함이었다. 콘솔 질의는 한 건도 늘지 않는다.
