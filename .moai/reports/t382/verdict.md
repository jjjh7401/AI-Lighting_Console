# t382 판정 — 충돌 회피 양보가 상승 사다리를 덮어쓴다

## 실측한 원인

`server/looks/songcue.py` `_distinct_values_line`(값 라인 충돌-회피 사다리)가
`_climb_rungs`를 통해 회차마다 찍는 액센트(줌/아이리스 좁힘·블라인더)를 얹지만,
헤드룸이 얕은 룩(빔 축이 없거나 밝기 여유가 한 걸음뿐)에서는 다음 두 경로 중
하나로 액센트가 통째로 빠졌다:

1. **양보(`LADDER_DIMMER_YIELD`) 경로** — `_yield_bundle`이 밝기를 한 칸씩 내려
   자리를 찾을 뿐, 찍는 액센트는 전혀 건드리지 않는다.
2. **재배열 뒤 기준값 회귀 경로** — 어떤 회차의 재시도가 마침 비워진 기준값
   자리에 곧바로 안착하면(`_distinct_values_line`의 `previous is None` 분기),
   `rungs=()`로 확정되어 액센트 시도 자체가 없다. 게다가 `_reorder_yields_by_repetition`
   (t369)가 밝기 단조성을 지키려고 `(commands, ladder)` 묶음을 회차 사이에서
   통째로 재배정하기 때문에, 성공적으로 액센트를 받은 회차의 묶음이 다른(더 깊은)
   회차 자리로 옮겨 가고, 그 자리에는 액센트 없는 묶음이 대신 온다.

### 프로브 A (카드 재현, 단일 축 `Dimmer`만, 시작값 95, 후렴 7회) — 고치기 전

```
stored=7 skipped=0
  cue=1 instance=1 ladder=('dimmer_yield',) Dimmer=70.0
  cue=2 instance=2 ladder=('dimmer_yield',) Dimmer=75.0
  cue=3 instance=3 ladder=('dimmer_yield',) Dimmer=80.0
  cue=4 instance=4 ladder=('dimmer_yield',) Dimmer=85.0
  cue=5 instance=5 ladder=('dimmer_yield',) Dimmer=90.0
  cue=6 instance=6 ladder=() Dimmer=95.0
  cue=7 instance=7 ladder=('dimmer_hit',) Dimmer=100.0
```

### 프로브 B (H2 — 회수 자체를 비활성화)

회수를 끄면 1·2회차만 저장되고 나머지는 전부 `value_line_collision`으로
버려진다 — H2("회수 순서가 원인")는 반증됐다. 원인은 회수가 밝기만 다루고
액센트를 안 다룬다는 것이다.

### 프로브 C (H1 대조 — 헤드룸을 넉넉히 준 같은 룩, 시작값 20)

```
cue=1 instance=1 ladder=() Dimmer=20.0
cue=2 instance=2 ladder=('dimmer_hit',) Dimmer=25.0
cue=3 instance=3 ladder=('dimmer_hit', 'dimmer_hit', 'blinder_or_flash') Dimmer=30.0
...
```

여기서는 사다리가 매 회차 정상 깊이에서 성공하므로(양보·재배열 불필요) 결함이
안 켜진다 — 헤드룸 부족이 방아쇠라는 H1을 지지한다.

## 고친 자리

1. **`_ensure_marking_accent`** (신규, `server/looks/songcue.py`) — 반복 회차
   (`instance >= 2`)가 이미 액센트를 갖고 있지 않으면 하나 골라 얹는다.
   - `force=False`(직접 사다리 경로, `_section_bundle`에서 호출): 이 회차가
     **마땅히 닿았어야 할 깊이**(`_ladder_start`, `instance - 1`)에 실제로
     닿아 있으면 그대로 둔다 — 2회차가 깊이 1(밝기 히트만)에서 곧바로 성공하는
     것은 정본 §7.1 자신의 설계이지 결함이 아니다(헤드룸 넉넉한 곡에서 실측,
     프로브 C). 실제로 닿은 깊이가 그보다 얕으면(기준값 그대로 물려받음)
     강제한다.
   - `force=True`(양보 경로, `_yield_bundle`에서 호출; 재배열 뒤 마무리 훑기,
     `_finalize_marking_accents`에서도 사용): 양보는 사다리 축이 아니므로
     깊이 개념이 없다 — 자리를 얻은 이상 액센트를 받는다.
   - 회전은 `(instance - 2) % len(accents)`에서 시작해 겹치지 않는 자리를
     찾는다. 블라인더·스트로브는 이 룩 자신의 값을 안 바꾸므로 항상 겹치지
     않아 회전은 유한 안에서 반드시 멈춘다.
2. **`_section_bundle`** — `_distinct_values_line` 직후, `emitted` 등록 전에
   `_ensure_marking_accent(force=False)`를 호출해 값·사다리를 갱신한다. 이
   자리가 `_accent_fixture_commands`보다 앞이므로, 강제로 얹힌 액센트가
   블라인더/스트로브를 고르면 그 즉시 리그 그룹 명령까지 낸다(AC-2가 이
   이음매를 직접 잰다).
3. **`_yield_bundle`** — 새 `allow_strobe` 매개변수를 받고, 자리를 찾은 뒤
   `_ensure_marking_accent(force=True)`로 액센트를 마저 얹는다(값이 바뀌면
   `emitted`도 그 값으로 다시 등록).
4. **`_finalize_marking_accents`** (신규) — `_rescue_value_line_collisions`가
   `_reorder_yields_by_repetition`을 부른 **뒤**에 실행하는 마지막 훑기. 재배열이
   `(commands, ladder)` 묶음을 다른 회차 자리로 옮겨 액센트를 잃은 자리를
   최종 위치 기준으로 다시 확인해 채운다. 문자열로만 남은 값 라인에서
   `AttributeValue`를 되돌리는 `_parse_values_line`(신규, `_dimmer_from_values_line`과
   같은 형식 가정)을 쓴다.
5. **`_yield_bundle` 호출부** — `_rescue_value_line_collisions`에서 `allow_strobe`를
   같이 넘기도록 고쳤다.

밝기(`Dimmer`) 자체의 단조 상승·재배열·드롭 무양보 성질(t366·t368·t369)은
전혀 건드리지 않았다 — 아래 RED→GREEN·가드 결과가 그 성질을 실측으로 지킨다.

## RED → GREEN

**RED** (`server/looks/songcue.py`를 `git show HEAD:...`로 되돌린 뒤 새/변경 검사만 실행):

```
$ uv run pytest -q server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py
...
FAILED server/tests/test_songcue_accent_ladder_t382.py::TestEveryRepeatOccurrenceCarriesOneAccent::test_all_seven_survive_with_non_decreasing_brightness_and_one_accent_each
FAILED server/tests/test_songcue_accent_ladder_t382.py::TestEveryRepeatOccurrenceCarriesOneAccent::test_instances_two_three_four_cycle_through_different_accents
FAILED server/tests/test_songcue_accent_ladder_t382.py::TestForcedAccentReachesTheConsoleWhenItPicksTheBlinder::test_a_direct_success_landing_on_the_base_line_still_lights_the_blinder
FAILED server/tests/test_songcue_chorus_rescue.py::TestTheChorusRescueGeneralizesBeyondDrop::test_worship_four_chorus_repeats_all_survive_on_the_real_library
4 failed, 11 passed in 0.47s
```

**GREEN** (구현 복원 후):

```
$ uv run pytest -q server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_ladder.py server/tests/test_songcue_report.py server/tests/test_songcue_accent_fixture.py server/tests/test_songcue_bundle.py
........................................................................ [ 93%]
.....                                                                    [100%]
77 passed in 0.91s
```

## 프로브 A 재실행 — 고친 뒤 (before/after 나란히)

| 회차 | 고치기 전 ladder | 고치기 전 Dimmer | 고친 뒤 ladder | 고친 뒤 Dimmer |
|---|---|---|---|---|
| 1 | `('dimmer_yield',)` | 70.0 | `('blinder_or_flash', 'dimmer_yield')` | 70.0 |
| 2 | `('dimmer_yield',)` | 75.0 | `('zoom_pinch', 'dimmer_yield')` | 75.0 |
| 3 | `('dimmer_yield',)` | 80.0 | `('iris_pinch', 'dimmer_yield')` | 80.0 |
| 4 | `('dimmer_yield',)` | 85.0 | `('blinder_or_flash', 'dimmer_yield')` | 85.0 |
| 5 | `('dimmer_yield',)` | 90.0 | `('dimmer_yield', 'zoom_pinch')` | 90.0 |
| 6 | `()` | 95.0 | `('iris_pinch',)` | 95.0 |
| 7 | `('dimmer_hit',)` | 100.0 | `('dimmer_hit', 'iris_pinch')` | 100.0 |

밝기(`Dimmer`) 값은 모든 회차에서 고치기 전과 완전히 동일하다(70/75/80/85/90/95/100,
단조 증가). 1회차만 액센트가 없어도 되는 자리(카드 t382 범위 밖)인데, 이 예시에서는
회수 체인(1회차가 물러서서 4회차에게 자리를 냄)이 1회차 자신을 다시 물리는 바람에
1회차도 액센트를 받았다 — 요구되지는 않지만 해가 되지 않는다(1회차는 예외 대상이지
금지 대상이 아니다).

## 검사 결과

### 새/변경 검사 (t382)

```
$ uv run pytest -q server/tests/test_songcue_ladder.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_report.py server/tests/test_songcue_accent_ladder_t382.py
............................................
44 passed in 0.52s
```

### 전체 스위트

```
$ uv run pytest -q
13673 passed, 35 skipped, 1 warning in 183.58s
```

(고치기 전 전체 스위트: 2건 실패했으나 둘 다 lint/format 자체 검사
`test_overlap_preserve.py::TestTouchedFilesPassLint`였고, `ruff format` 적용 후
해소됐다 — 로직 회귀가 아니다.)

### lint/format (변경 파일)

```
$ uv run ruff check server/looks/songcue.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_ladder_t382.py
All checks passed!
$ uv run ruff format --check server/looks/songcue.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_ladder_t382.py
3 files already formatted
```

## 안 잰 것 (Gaps)

- **실제 룩 라이브러리의 다양한 축 조합**(줌만/아이리스만/줌+아이리스/셋 다 없음)에서
  이 회전이 매번 겹치지 않는 자리를 찾아내는지는 이 카드가 재현한 단일 축·실기
  라이브러리 대조군(`test_songcue_chorus_rescue.py`) 둘로만 확인했다 — 전수는 아니다.
- **`_finalize_marking_accents`가 강제로 얹은 액센트가 블라인더/스트로브를 고른
  경우, 콘솔 그룹 명령까지 실제로 나가는지는 확인하지 않았다.** `_section_bundle`
  경로(AC-2)는 확인했지만, 재배열 이후 마무리 훑기 경로는 문자열만 다루므로
  `accent_fixture` 필드·그룹 명령 생성 로직을 안 태운다 — 그 회차의 `ladder`에는
  `blinder_or_flash`/`strobe_hit`가 실리지만 무대에는 아무것도 안 나갈 수 있다.
  기존 독스트링(`SongCueSectionBundle.accent_fixture`)이 이미 "칸은 회전했지만
  무대엔 안 나갈 수 있다"는 모양을 문서화하므로 구조적으로는 새로운 실패 모드가
  아니지만, 그 정확한 발생 조건(재배열로 액센트를 잃었다가 되찾은 회차가 하필
  블라인더를 고르는 경우)은 실측하지 않았다.
- **콘솔 실기·실제 곡 시각적 확인**은 하지 않았다(이 저장소의 다른 SPEC들과 같은
  잔여 위험 — 콘솔 0회 관측).
- 프로브 A 재실행에서 1회차가 액센트를 받는 것이 매 헤드룸·회차 수 조합에서
  항상 그런지(회수 체인이 1회차를 다시 무는 조건)는 전수로 확인하지 않았다 —
  카드 t382의 요구 범위(instance >= 2) 밖이라 해가 없다는 것만 확인했다.

## 잔여 위험

- `_finalize_marking_accents`는 `_parse_values_line`으로 값 라인 문자열을
  되돌리는데, 이 파서는 `_values_line`(`server/looks/instantiate.py`)이 내는
  고정 형식 하나만 가정한다 — 그 형식이 바뀌면(다른 카드에서) 이 파서도 같이
  깨진다(기존 `_dimmer_from_values_line`과 같은 위험을 공유한다).
- 회전이 매번 4개 후보(스트로브 허용 시 4번째 포함) 안에서 겹치지 않는 자리를
  찾는다는 보증은 "블라인더·스트로브가 값을 안 바꾼다"는 불변식에 의존한다 —
  그 불변식이 깨지면(예: 미래에 블라인더에 값 효과가 생기면) 회전이 실패할 수
  있다(`return values, rungs`로 조용히 액센트 없이 남는다, 예외를 던지지 않는다).

## 후속 — 오케스트레이터 재측정 D1·D2 (커밋 `fix(t382): 1회차엔 액센트를 안
붙이고, 액센트 표엔 명령이 따라간다`)

af494681 배포 뒤 오케스트레이터가 프로브
(`t382_accent_probe.py`)로 재측정해 두 결함을 잡았다:

- **D1** — 1회차가 `blinder_or_flash`를 실었다(7·4회차 곡 모두). 원인은
  `_reorder_yields_by_repetition`(t369)가 (값 라인, 사다리) 묶음을 밝기
  오름차순으로 회차 사이에서 통째로 바꿔치기하기 때문 — 액센트를 실은 다른
  회차의 묶음이 가장 어두운 값을 가지면 1회차 자리로 옮겨 붙는다.
- **D2** — 사다리가 `blinder_or_flash`를 가리켜도 무대 명령(그룹 선택)이 없는
  경우가 있었다. 실측해 보니 원인이 하나 더 있었다: `_reorder_yields_by_repetition`는
  `commands[3:]`(프론트 필·액센트·움직임·Store)를 **안 옮긴다** — 이 번들
  자신이 원래 계산한 것을 그대로 둔 채 `ladder`만 바꿔치기한다. 그래서 재배열
  뒤에는 사다리가 가리키는 액센트와 실제 무대 명령이 서로 다른 회차 것일 수
  있다(`FULL_RIG`에는 애초에 블라인더 그룹이 없어 이전 AC-2는 이 어긋남을
  가릴 수 없었다 — 명령이 있으나 없으나 결과가 같아 보였다).

**고친 자리**:
- `_yield_bundle`에서 t382 최초 커밋이 더했던 액센트 결정 로직을 걷어 냈다
  (밝기만 다룬다, 원래 형태로 복귀) — 액센트는 이제 오직 한 자리
  (`_finalize_marking_accents`)에서만 결정한다.
- `_finalize_marking_accents`를 3단계로 재구성했다:
  1. `_strip_marking_accent_from_base_occurrence` — 1회차가 재배열로 물려받은
     액센트를 값 라인·사다리 양쪽에서 걷어 낸다(D1).
  2. 기존 "빠진 액센트 채우기" 훑기(instance >= 2, 이번엔 걷어내기로 비워진
     자리도 자연히 다시 채워진다).
  3. `_reconcile_accent_fixture` — **모든** 저장 큐의 무대 명령을 지금
     확정된 사다리에 맞춰 다시 짓는다: `bundle.accent_fixture`가 있으면(재배열이
     안 건드리므로 "commands[3:]에 지금 명령이 있는가"를 정확히 말해 준다)
     그 두 줄을 걷어 내고 `emitted`도 지운 뒤, 확정된 사다리가 블라인더·
     스트로브를 가리키면 `_accent_fixture_commands`로 다시 만들어 붙인다(D2).
- `_finalize_marking_accents`에 `resolution: RoleResolution` 매개변수를
  더했다(호출부는 `_rescue_value_line_collisions`에 이미 있는 것을 그대로
  넘긴다).

**RED → GREEN** (새 4개 검사: D1×2, D2×2 — `test_songcue_accent_ladder_t382.py`의
`TestEveryRepeatOccurrenceCarriesOneAccent::test_the_base_occurrence_never_carries_a_marking_accent_{seven,four}_choruses`
+ `TestBlinderLadderAlwaysCarriesItsConsoleCommand` 2건, `FULL_RIG` + `BLIND`
그룹 하나를 더한 리그로 재현):

```
$ (server/looks/songcue.py 를 af494681 상태로 되돌린 뒤)
$ uv run pytest -q server/tests/test_songcue_accent_ladder_t382.py
4 failed, 7 passed in 0.36s
FAILED ...test_the_base_occurrence_never_carries_a_marking_accent_seven_choruses
FAILED ...test_the_base_occurrence_never_carries_a_marking_accent_four_choruses
FAILED ...test_every_blinder_ladder_entry_matches_a_console_command_seven_choruses
FAILED ...test_every_blinder_ladder_entry_matches_a_console_command_four_choruses

$ (구현 복원 후)
$ uv run pytest -q server/tests/test_songcue_accent_ladder_t382.py
11 passed in 0.33s
```

**전체 검사** — `server/tests/test_songcue_ladder.py` +
`test_songcue_chorus_rescue.py` + `test_songcue_report.py` +
`test_songcue_accent_ladder_t382.py` + `test_songcue_accent_fixture.py` +
`test_songcue_bundle.py` = 81 passed. `uv run pytest -q` 전체 스위트 = 13677
passed, 35 skipped(t382 첫 커밋 대비 +4, 이번에 더한 검사 수와 일치).
`ruff check`/`ruff format --check` 셋 다 clean.

**오케스트레이터 프로브 재실행** (`t382_accent_probe.py`, 7·4회차 `Dimmer` 95):
1회차 ladder가 `('dimmer_yield',)`로 돌아왔다(액센트 없음) — 위 D1 판정과
일치. `FULL_RIG`에 블라인더 그룹이 없어 이 프로브 자체는 D2를 직접 못 보여
주므로(그룹 명령이 원래 안 나가는 리그), D2는 별도로 `FULL_RIG` + `BLIND`
그룹 하나를 더한 리그로 확인했다(위 GREEN 결과 및 신규 검사).

**범위 밖으로 남긴 것 (follow-up 카드 후보 — "effective-accent filter")**:
오케스트레이터 지시대로, 사다리 회전이 그 룩에 없는 축(줌만 있는 룩에
아이리스를 고르는 경우 등)이나 리그에 없는 그룹(블라인더 없는 리그에
`blinder_or_flash`를 고르는 경우)을 그대로 고르는 기존 동작은 손대지 않았다.
그 경우 `ladder`에는 칸 이름이 실리지만 무대 효과는 전혀 없다 — 이 카드
이전부터 있던 모양이고(`SongCueSectionBundle.accent_fixture` 독스트링이 이미
"칸은 회전했지만 무대엔 안 나갈 수 있다"를 문서화한다), `_reconcile_accent_fixture`도
이 조합에서는 "리그에 그 그룹이 없으니 명령 없음"을 그대로 반환한다(정확한
동작 — D2가 고친 것은 "명령이 있어야 하는데 없다"는 어긋남이지 "애초에 낼
수 없다"가 아니다). 후속 카드 후보: 회전이 후보를 고르기 **전에** 이 룩·이
리그에서 실제로 효과가 있는 액센트만 후보로 거르는 "effective-accent filter"
— 그러면 무영향 액센트가 애초에 사다리에 오르지 않는다.
