# progress — SPEC-LDCOMPILE-001

## §E.2 Run-phase Evidence

### C2 시간 해석 완료 (REQ-LDPLUGIN-009 계산부)

워크트리 `.claude/worktrees/ldcompile-c2` · 브랜치 `WT-timing-lower` · 기준 HEAD `d5b8098`
(= `origin/main`, C1 착수 PR #451).

**Claim**: 계약 `LD-TIME-001`~`003` 과 `LD-MIB-001`(음수 ms 부분)을 TDD 로 구현하고, C1
파이프라인 2단(`time_reference`)의 자리표시자를 실제 검사기로 교체했다.

#### Evidence — 기준선 (실제 출력)

```
$ uv run pytest -q          # d5b8098, 신규 파일 전
13122 passed, 35 skipped, 1 warning in 224.21s (0:03:44)
```
파일: `.moai/state/verify/c2/baseline.txt`

**Baseline-attribution**: 이 트리·이 HEAD 에서 직접 실측했다. `plan.md` §5 의
`12928 / 31` 은 **다른 트리(`cde2744`)의 숫자**이며 이 판정의 근거로 쓰지 않았다.

#### Evidence — RED (실제 출력)

```
$ uv run pytest server/tests/test_director_validate_timing.py -q
E   ModuleNotFoundError: No module named 'server.director.validate.timing'
1 error in 0.07s
```
파일: `.moai/state/verify/c2/red.txt`

#### Evidence — GREEN · 회귀 (실제 출력)

```
$ uv run pytest -q
13185 passed, 35 skipped, 1 warning in 180.99s (0:03:00)
```
파일: `.moai/state/verify/c2/green-full.txt`

**Baseline-attribution**: 13122 + 신규 **63** = 13185 — 정확히 일치하며 skipped 불변,
실패 0. 신규 개수는 파일을 명시해 셌다(`uv run pytest server/tests/test_director_validate_timing.py -q`
→ `63 passed`). C1 시험은 깨지지 않았다:

```
$ uv run pytest server/tests/test_director_validate_pipeline.py server/tests/test_director_validate_timing.py -q
103 passed in 0.50s
```

#### Evidence — 경계 (실제 출력)

```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/     → OK - no OSC import
$ grep -rnE "^\s*(from|import)\s+server\.(looks|web)" server/director/ → OK - no artistic producer
$ git diff --name-only origin/main -- server/lxseq server/design       → (없음) OK - PRESERVE 무침해
$ uv run ruff check server/director/validate/ server/tests/test_director_validate_timing.py
All checks passed!
```

#### 착수 조건 — 감독 판정을 받았다

`plan.md` §6 첫 항목(*"`spec.md` §6.3(음수 ms)의 판정을 받기 전에 C2 를 완결하지 않는다"*)의
판정을 2026-09-15 에 받았다: **경로 분리 + 새 원점 안내**.

- Director 경로는 음수 ms 를 `LD-MIB-001` blocking 으로 거부하고, 사유에
  *"원점을 확장한 새 audio/context"* 요청을 담는다.
- 기존 `server/lxseq/cue_time.py` 의 `CUE_TIME_PREROLL` 은 **수정 0**. 그 경로가 살아 있는지를
  `test_lxseq_preroll_path_is_untouched` 가 단언한다 — 「Director 만 거부」와 「기능 제거」를
  구분하는 자리다.
- 계약 개정 없음.

판정을 뒷받침한 실측 둘:

| 실측 | 명령 | 결과 |
|---|---|---|
| pre-roll 소비 범위 | `grep -rn "CUE_TIME_PREROLL" server --include="*.py" \| wc -l` | **8** — 전부 `cue_time.py` 한 파일 안, 외부 소비자 0건 |
| wire 표현 가능성 | `exchange.schema.json` 의 `at_ms`·`delay_ms`·`fade_ms` | 전부 `integer, minimum: 0` — **음수는 스키마에서 표현 불가** |

두 번째가 판정의 성격을 바꾼다: 이 거부는 새 정책이 아니라 **스키마가 이미 집행하던 것을
진단으로 말하는 것**이다.

#### 계약 내부 갈등 하나를 해소했다 (판정 기록)

`LD-TIME-002` 는 *"confirmed 근거 필수"* 라 쓰지만 계약 §6.1 `beat_map` 문단이
*"absent/unconfirmed 에서는 beat 기반 FX 를 실행하지 않는다. `synthetic` 은 합성 harness
에서만 허용한다"* 로 예외를 적었다. 앞 줄만 따르면 계약의 규범 예제
(`examples/context.json` — `status=synthetic`, `environment=synthetic`)가 스스로 막힌다.

채택한 규칙: `confirmed`, **또는** (`synthetic` AND `environment == "synthetic"`).
`environment` 만 `production` 으로 바꾸면 막히는지도 시험으로 고정했다
(`test_synthetic_beat_map_is_allowed_only_in_synthetic_environment`) — synthetic 예외가
production 우회 통로가 되지 않게 하기 위한 것이다.

#### Evidence — 계기가 공허하지 않다는 확인 (전부 실측)

| 확인 | 방법 | 결과 |
|---|---|---|
| 반올림이 계약 규칙인가 | 내장 `round()` 와 비교 단언 | `round_half_up(2.5)==3 != round(2.5)==2`. 구현이 `round()` 로 바뀌면 깨진다 |
| tempo 불명이 숫자를 내지 않는가 | `beat_at`/`ms_at_beat` 에 빈 지도 | `TempoUnknownError`. `None` 을 답하지 않는다 |
| delta 가 절대 시각이 아닌가 | 3큐(0·10000·35000) | 마지막 `relative_ms=25000`. 절대값이면 35000 이 나온다 |
| 준비 cue 가 사슬에 드는가 | 준비 cue 를 중간에 끼움 | `[0, 3000, 2000]`, 합 5000 |
| 큐를 section 밖으로 옮기면 잡는가 | 규범 계획의 cue 3 을 +100000ms | `blocking=1` |
| 검사 밖 필드를 건드리면 통과하는가 | `playback.start_policy` 변조 | `blocking=0` (음성 대조 — 넓게 잡지 않았다) |
| 경계가 반열림인가 | section end 시각·tempo 경계에서 끝나는 FX | 둘 다 정확히 통과 |
| 배선이 실물인가 | `run_stages(broken_plan, context)` | 2단 진단에 `/cues/0/at_ms` blocking 이 나타난다 |

#### 자기 검토에서 찾은 내 결함 (수정 완료)

1. 🔴 **tempo 지도가 곡 뒷부분을 안 덮어도 조용히 통과했다.** 규범 예제의 beat segment 를
   90초로 줄여도 `blocking=0` 이었다. `beat_at` 은 tempo 불명에 예외를 던지지만 **아무도
   큐 시각으로 그것을 부르지 않았기 때문에** 부재가 부재로 남았다 — `LD-TIME-002` 가 막으라는
   바로 그 상황이다. `_check_fx_tempo_coverage` 를 추가하고 `TestFxTempoCoverage` 4개로
   고정했다. 범위를 FX 로 한정했다(일반 cue 의 `at_ms` 는 절대 시각이라 박 계산이 필요 없고,
   거기까지 막으면 tempo 지도 없는 정적 계획이 통째로 막힌다 — 음성 대조로 고정).
2. `zip(sections, sections[1:], strict=True)` 를 쓰려 했다 — 길이가 1 차이라 **예외가 난다.**
   `itertools.pairwise` 로 교체했다.
3. C1 파이프라인 2단이 `timing.py` 를 부르지 않는 상태로 끝낼 뻔했다. 부품 63개가 초록이어도
   경로가 안 이어지면 실제 판정에 도달하지 않는다 — 배선 후 `TestWiredIntoThePipeline` 4개로
   고정했다.

#### 만든 파일 · 고친 파일

```
신규  server/director/validate/timing.py                 beat↔ms · cue 경계 · delta · tempo 근거
신규  server/tests/test_director_validate_timing.py      63 시험
수정  server/director/validate/pipeline.py               2단 배선 + context 주입 (아래)
```

`pipeline.py` 변경의 성격: 6개 단계 함수 시그니처를 `(plan, context)` 로 통일하고,
`run_stages(plan, context=None)` · `PipelineValidator(context=None)` 로 context 를 흘렸다.
**`server/director/service.py` 는 고치지 않았다** — `PlanValidator` seam 은 형제 SPEC 소유이며,
seam 이 계획만 넘기므로 context 는 검증기를 만들 때 주입한다. context 가 없으면 2단은
**blocking** 이다(판정 불능을 수용으로 바꾸면 시간 검사가 조용히 사라진 채 `ready_for_review`
가 나올 수 있다).

### C3 tracking·FX·충돌 완료 (REQ-LDPLUGIN-010·011)

워크트리 `.claude/worktrees/ldcompile-c3` · 브랜치 `WT-tracking-fx` · 기준 HEAD `3405f2e7`
(= `origin/main`) · 구현 커밋 `04f3feef`.

**Claim**: 계약 `LD-STATE-001`·`LD-STATE-002`·`LD-FX-001`·`LD-CONFLICT-001` 을 TDD 로 구현하고,
C1 파이프라인 3단(`tracking_fx`)의 자리표시자를 실제 검사기로 교체했다. C2 가 남긴
`rounding_conflicts` 의 호출자 부재도 같은 배치에서 닫았다.

#### Evidence — 기준선 (실제 출력)

```
$ uv run pytest -q          # 3405f2e7, 신규 파일 전
13185 passed, 35 skipped, 1 warning in 213.70s (0:03:33)
```
파일: `.moai/state/verify/c3/baseline.txt`

**Baseline-attribution**: 이 워크트리·이 HEAD 에서 직접 실측했다. 인계문이 예상한
`13185/35` 와 일치하지만 그 예상을 근거로 쓰지 않았다 — 위 출력이 근거다.

#### Evidence — RED (실제 출력)

```
$ uv run pytest server/tests/test_director_validate_ready.py \
      server/tests/test_director_validate_conflict.py -q
67 failed, 1 passed in 1.44s
```
파일: `.moai/state/verify/c3/red.txt`

통과한 1건이 **내 가드가 공허했다는 증거**다 — 아래 「자기 검토에서 찾은 내 결함」 1번.

#### Evidence — GREEN · 회귀 (실제 출력)

```
$ uv run pytest -q
13255 passed, 35 skipped, 1 warning in 173.80s (0:02:53)
```
파일: `.moai/state/verify/c3/green-full.txt`

**Baseline-attribution**: 13185 + 신규 **70** = 13255 — 정확히 일치하며 skipped 불변, 실패 0.
신규 개수는 파일을 명시해 셌다(두 신규 파일 → `70 passed`). C1·C2 시험은 깨지지 않았다:

```
$ uv run pytest server/tests/test_director_validate_pipeline.py \
      server/tests/test_director_validate_timing.py -q
103 passed in 0.49s
```

#### Evidence — 경계 (실제 출력)

```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/     → OK - no OSC import
$ grep -rnE "^\s*(from|import)\s+server\.(looks|web)" server/director/ → OK - no artistic producer
$ git diff --name-only origin/main -- server/lxseq server/design       → (없음) OK - untouched
$ git diff --name-only origin/main -- server/director/service.py        → (없음) OK - untouched
$ uv run ruff check server/director/ server/tests/test_director_validate_{ready,conflict}.py
All checks passed!
```

#### C2 의 빚을 닫았다 — 호출자 0건 → 1건

```
$ grep -rn "rounding_conflicts(" server --include="*.py" \
    | grep -v "/tests/" | grep -v "def rounding_conflicts("
server/director/validate/pipeline.py:153: ... rounding_conflicts(beat_map, fx_beat_requests(plan, context))
```

`(group, axis, beat)` 목록은 `conflict.fx_beat_requests` 가 만든다 — FX cycle 경계를 박으로
낮춘 것이다. 계약 §7 의 반올림 충돌이 실제로 걸리는 자리는 **박으로 반복되는 것**뿐이며
(일반 cue 의 `at_ms` 는 절대 시각이라 박 계산을 거치지 않는다), 그래서 목록의 출처가 FX 다.

#### Evidence — 계기가 공허하지 않다는 확인 (전부 실측)

| 확인 | 방법 | 결과 |
|---|---|---|
| 규범 예제가 통과하는가 | `check_ready(plan.json)` · `check_conflicts(plan, context)` | 둘 다 blocking 0 |
| 음성 대조 셋이 통과하는가 | 조용한 엔딩(outro 3%) · 동일 후렴 강도(75/75) · 반복 motif(color-blue ×3) | 셋 다 blocking 0 |
| 구간 이름으로 판정하지 않는가 | 같은 계획의 `section_id` 를 intro/chorus/outro/bridge 로 돌림 | 판정 불변 |
| 검사 밖 필드를 건드리면 통과하는가 | `label`·`title` 변조 | blocking 0 (넓게 잡지 않았다) |
| 반올림 배선이 실물인가 | `bpm=60000` + `cycle_beats=0.0625` → `run_stages` | `LD-TIME-002` blocking 등장 |
| 그 배선의 **구멍**도 재는가 | `bpm=120` + `cycle_beats=4` | 반올림 진단 0건 (무조건 막는 것이 아니다) |
| 반열림이 맞는가 | 끝==시작(3000) 통과 / 1ms 겹침(2999) 거부 | 양쪽 다 의도대로 |
| delay 가 예약인가 | `delay=3000,fade=1000` 구간에 1000ms 순간 쓰기 | conflict. 4000ms 는 통과 |
| fixture 전개가 판정 단위인가 | 같은 계획을 겹친 group / 분리된 group context 로 각각 | 겹치면 conflict, 분리하면 통과 |
| 겹치지 않는 fixture 까지 고발하는가 | 진단 문면 검사 | `fixture-2` 만 등장, `fixture-1` 부재 |
| 배열 순서로 덮어쓰는가 | 세 겹침의 순서를 뒤집어 개수·대상 대조 | 동일 |

#### 자기 검토에서 찾은 내 결함 (수정 완료)

1. 🔴 **빚을 닫았다는 내 가드가 구현 전에 통과했다.** `rounding_conflicts` 를 grep 하면서
   여는 괄호를 요구하지 않아 `timing.py:14` 의 **독스트링 언급**을 호출자로 셌다. 도달
   가능성은 정당화가 아니다 — 호출을 세야 한다. `rounding_conflicts(` 로 좁히고 그 사유를
   시험 본문에 남겼다. 이것이 RED 에서 「1 passed」였던 것이다.
2. 🔴 **첫 grep 이 계기가 죽은 채 0 을 답했다.** zsh 가 `--include=*.py` 를 글롭으로 먹어
   `no matches found` 를 내고 `wc -l` 이 0 을 셌다 — 「호출자 0건」이라는 참인 결론이
   거짓 경로로 나왔다. 인용하고 양성 대조(`grep "def "` → 15722건)를 함께 쏴서 다시 셌다.
3. release 뒤 완전한 baseline 을 다시 선언해도 `ownership` 이 `released` 로 남아 양성 대조가
   깨졌다. 쓰면 다시 소유한다 — `simulate` 에서 static 쓰기가 `held` 로 되돌린다. 부분
   재진입은 `_check_release_reentry` 가 따로 막으므로 여기서 완전성을 재판정하지 않는다.
4. 순서 독립 시험이 진단 **문면**까지 같기를 요구해 실패했다. pointer 가 `/cues/0/actions/{j}`
   라 배열 첨자를 담으므로 문면은 당연히 달라진다 — 순서와 무관해야 하는 것은 판정이고,
   관측 가능한 형태는 개수와 대상이다. 단언을 그리로 옮겼다.

#### 만든 파일 · 고친 파일

```
신규  server/director/validate/simulate.py               축별 상태 · baseline · FX 생애 · terminal
신규  server/director/validate/conflict.py               fixture×axis 예약 구간 · FX 축 · 박 요청
신규  server/tests/test_director_validate_ready.py       41 시험 (음성 대조 3 포함)
신규  server/tests/test_director_validate_conflict.py    29 시험 (날조 대조군 + 구멍 포함)
수정  server/director/validate/pipeline.py               3단 배선 + rounding_conflicts 호출
```

`simulate.check_ready` 는 `context` 를 받지 않는다 — 이 판정에 필요한 것은 전부 계획 안에
있고(controlled group·cue·terminal), group membership 은 충돌 검출의 관심사다. 안 쓰는 입력을
받으면 그것을 본다고 오해된다.

### C4 capability 거부 완료 (REQ-LDPLUGIN-008·013 거부부)

워크트리 `.claude/worktrees/ldcompile-c4` · 브랜치 `WT-capability-refuse` · 기준 HEAD
`4c3ed064` (= C3 머지 직후의 `origin/main`) · 구현 커밋 `7ad9cb65`.

**Claim**: 계약 `LD-CAP-001` 을 구현하고 4단의 자리표시자(전 action 동일 문구)를 원인별
사유로 교체했다. **아무것도 열지 않았다** — 4단은 여전히 전부 blocking 이다.

#### 🔴 Gap — RED 을 잡지 못했다 (이 마일스톤의 가장 큰 미검증)

시험 파일을 구현보다 먼저 **작성했지만 구현 전에 실행하지 않았다.** 따라서 test-first 를
반증할 수 있는 pre-GREEN 실패 출력이 **없다.** C2·C3 는 `red.txt` 를 남겼는데 C4 는 없다.

사후에 구현을 치워 두고 돌려서 「RED」라고 적을 수는 있었지만, 그것은 pre-GREEN 증거가
아니라 **사후 재구성**이므로 하지 않았다. 대신 시험이 공허하지 않다는 것을 **뮤테이션으로**
재고 그 출력을 아래에 남긴다 — 이것은 test-first 의 증거가 아니라 「이 시험이 회귀를
잡는다」의 증거이며, 두 주장은 다르다.

#### Evidence — 뮤테이션 (실제 출력)

| 뮤테이션 | 무엇을 깨는가 | 결과 |
|---|---|---|
| `AXIS_TIMING_OBSERVED` 를 6축으로 채움 | 관측 없는 승격 | **12 failed**, 55 passed — 내 시험 + C1 coverage 가드가 함께 잡았다 |
| `_refuse` 의 `after` 에 `present(100)` | clamp 제안 | **1 failed** — `test_no_diagnostic_carries_a_replacement_value` |
| 부재 preset 사유에 `color-amber` 대체안 명시 | fallback preset | **1 failed** — `test_absent_preset_is_not_replaced_with_a_similar_one` |
| (원복) | — | **27 passed** |

두 번째가 설계 의도를 확인해 준다: 5대 금지를 한 문장(*"어떤 진단도 `after` 에 값을 싣지
않는다"*)으로 모았으므로 clamp 를 넣으면 **정확히 그 한 시험**이 깨진다.

#### Evidence — GREEN · 회귀 (실제 출력)

```
$ uv run pytest -q
13283 passed, 35 skipped, 1 warning in 176.01s (0:02:56)
```
파일: `.moai/state/verify/c4/green-full.txt`

**Baseline-attribution**: 기준선은 C3 머지 직후의 `origin/main`(`4c3ed064`) = **13255/35**
이며, 그 숫자는 C3 절에서 이 저장소에 대해 실측한 값이다(C4 워크트리에서 다시 재지 않았다 —
이것이 이 항목의 귀속 한계다). 13255 + 신규 **28** = 13283 으로 정확히 맞물리고 skipped
불변, 실패 0. 신규 개수는 파일을 명시해 셌다(`test_director_validate_capability.py` → 28).

#### 🔴 자기 검토에서 찾은 내 결함 (수정 완료)

1. 🔴 **`context=None` 에서 root 진단 하나로 갈음해 C1 의 coverage 가드 5건을 깨뜨렸다.**
   4단은 계약 §6.3 *"각 요청 action에는 적어도 하나의 diagnostic"* 을 채우는 자리인데
   (`pipeline.py` 독스트링에 그렇게 적혀 있다) 판정 불능을 coverage 면제로 다뤘다. action
   별로 내도록 고치고 `test_missing_context_still_yields_one_diagnostic_per_action` 으로
   박았다. **C1 이 남긴 가드가 이것을 잡았다** — 그 가드가 없었으면 조용히 통과했다.
2. 🔴 **스키마 거부 시험이 거짓 사유로 통과할 뻔했다.** 손으로 짠 최소 계획을
   `parse_exchange` 에 넣으니 rogue op 이 아니라 상위 필드 부재 때문에
   `UNSUPPORTED_SCHEMA_VERSION` 이 먼저 났다 — 두 거절이 모두 「거절」이라 성공/실패
   이분법으로는 구별되지 않는다. 규범 예제에 rogue op 하나만 주입하도록 바꾸고
   **코드(`SCHEMA_INVALID`)를 단언**하며, 손대지 않은 예제가 통과하는 양성 대조를 같은
   시험에 넣었다.
3. `pipeline.py` 에 자리표시자가 쓰던 `_NO_AXIS_EMITTER_REASON`·`_action_pointers` 를 죽은
   채로 남겼다. 지웠고 회귀는 13283 그대로다.

#### Evidence — 경계 (실제 출력)

```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/     → OK - no OSC import
$ grep -rnE "^\s*(from|import)\s+server\.(looks|web)" server/director/ → OK - no artistic producer
$ git diff --name-only origin/main -- server/lxseq server/design server/director/service.py
                                                                       → (없음) OK - untouched
$ uv run ruff check server/director/ server/tests/                     → All checks passed!
```

#### 만든 파일 · 고친 파일

```
신규  server/director/validate/capability.py                op·축·preset·정책별 거부 사유
신규  server/tests/test_director_validate_capability.py     28 시험
수정  server/director/validate/pipeline.py                  4단 교체 + 죽은 코드 제거
```

### C5 dark move·재진입 거부 완료 (REQ-LDPLUGIN-012)

워크트리 `.claude/worktrees/ldcompile-c5` · 브랜치 `WT-dark-move-refuse` · 기준 HEAD
`50623f39` (= C4 머지 직후의 `origin/main`) · 구현 커밋 `26514169` + 수정 `72b4e723`.

**Claim**: 계약 `LD-MIB-001`(dark move 어둠 증명)과 `LD-REENTRY-001`(`random_access` 광고
검증)을 구현하고 5단에 배선했다. C4 가 판정 없이 남긴 `random_access` 축을 닫았다.

#### Evidence — 기준선 (실제 출력)

```
$ uv run pytest -q          # 50623f39, 신규 파일 전
13283 passed, 35 skipped, 1 warning in 215.11s (0:03:35)
```
파일: `.moai/state/verify/c5/baseline.txt`

**Baseline-attribution**: **이 워크트리에서 직접 실측했다.** C4 는 기준선을 C3 절에서
인용했고 그것을 §E.3 에 미검증으로 적었는데, C5 는 그 구멍을 닫았다.

#### Evidence — RED (실제 출력) — C4 의 구멍을 닫았다

```
$ uv run pytest server/tests/test_director_validate_mib.py -q
29 failed, 1 passed in 0.48s
```
파일: `.moai/state/verify/c5/red.txt`

통과한 1건은 `test_safety_gate_ownership_is_still_stated` 이며 **보존 단언**이다 — 「5단이
SafetyGate 소유를 진술하는 문장은 내 변경 뒤에도 살아 있어야 한다」. 보존 시험이 RED 에서
통과하는 것은 정상이다(C3 의 공허한 가드와 다르다: 그것은 아직 없는 것을 있다고 답했고,
이것은 이미 있는 것이 계속 있음을 확인한다).

첫 RED 판에서는 2건이 통과했고, 나머지 1건은 **제가 만든 빈 시험**이었다 — 안 쓰는 import
(`beam`·`color`)를 정당화하려고 `assert callable(...)` 을 넣은 것. import 와 함께 지웠다.

#### Evidence — GREEN · 회귀 (실제 출력)

```
$ uv run pytest -q
13316 passed, 35 skipped, 1 warning in 175.06s (0:02:55)
```
파일: `.moai/state/verify/c5/green-full.txt`

**Baseline-attribution**: 13283 + 신규 **33** = 13316 — 정확히 일치, skipped 불변, 실패 0.
신규 개수는 파일을 명시해 셌다(`test_director_validate_mib.py` → 33). 이 SPEC 범위 전체:

```
$ uv run pytest server/tests/ -k "director_validate" -q
234 passed, 13117 deselected
```

#### 어둠의 창 — 두 조건을 다 요구한다

```
        at_ms   +delay        pan/tilt 중 늦은 완료     +settle_ms
          |-------|=============================|----------|
                  [           어두워야 하는 창             )
```

1. **창에 들어가는 순간의 정착값이 0** 이어야 하고, 그런 쓰기가 실제로 있어야 한다.
   선언이 없으면 미증명이다 — `LD-STATE-001` 이 `safe_state` 상속을 금지한 것과 같은 이유.
2. **창 안에서 진행 중이거나 새로 시작하는 intensity 쓰기가 없어야** 한다. 목표값이 0 인
   fade 도 진행 중이면 미증명이다: **0 으로 가는 중인 것은 0 인 것이 아니다.**

`settle_ms` 가 드디어 제 일을 한다. C4 는 이것을 예약 구간에 넣지 않았고 그 판단을 미검증으로
적었는데, reveal 전 정착시간은 **충돌이 아니라 어둠의 길이**였다 — 창의 끝을 늘린다.

#### Evidence — 계기가 공허하지 않다는 확인 (전부 실측)

| 확인 | 방법 | 결과 |
|---|---|---|
| 증명이 서는 계획은 통과하는가 | baseline 0 + 창 안 무변경 | blocking 0 |
| `move_mode=live` 를 잡지 않는가 | 같은 계획을 live 로 (창 안 intensity 80) | blocking 0 — 넓게 잡지 않았다 |
| 창 끝이 늦은 축인가 | pan fade 500 · tilt fade 4000, 13000ms 에 올림 | blocking. 빠른 축으로 재면 통과해 버린다 |
| 경계가 반열림인가 | 12800(끝) 통과 / 12799 거부 | 양쪽 다 의도대로 |
| `settle_ms` 가 창을 늘리는가 | 같은 계획을 settle 800 / 0 | 800 거부, 0 통과 |
| delay 가 창 시작을 미루는가 | delay 3000, 11000ms 에 0 선언 | 통과 |
| 진행 중 fade 가 미증명인가 | 목표 0 인 fade `[8000,12000)` | 거부 |
| 부재를 0 으로 가정하는가 | intensity 선언 없는 계획 | 거부 |
| intensity FX 만 잡는가 | `fx-pulse`(intensity) 거부 / 같은 FX 를 pan·tilt 로 바꿈 | 후자 통과 |
| 광고가 `false` 면 결함인가 | `random_access=false` | blocking 0 |
| 규범 예제가 `true` 로 광고하는가 | context 실측 | 전 group `true` → 거부 |
| reveal 이동을 제안하는가 | 모든 진단의 `after` | 전부 부재 |
| 음수 ms 를 내는가 | `dark_windows` 의 start·end | 전부 ≥ 0 |

**뮤테이션 셋** — 셋 다 의도한 그 시험이 잡았다:

| 뮤테이션 | 결과 |
|---|---|
| 창 끝을 `min(end)` 으로 (빠른 축) | `test_later_axis_completion_defines_the_window_end` |
| 정착값 부재를 통과로 (`if False`) | `test_never_declared_intensity_is_blocking` |
| 목표 0 인 진행 fade 를 통과로 | `test_a_fade_crossing_into_the_window_is_blocking` |

#### 🔴 자기 검토에서 찾은 내 결함 (수정 완료)

1. 🔴 **제 시험 둘이 서로 모순이었다.** `test_stage_five_is_not_a_placeholder` 는 *"'safety
   단계에 도달했습니다' 가 없어야 한다"* 로 썼는데, 그 문장은 **일부러 남긴** SafetyGate 소유
   진술이고 바로 아래 `test_safety_gate_ownership_is_still_stated` 가 그 존재를 요구한다.
   자리표시자 판별을 **문구의 부재**가 아니라 **판정의 존재**(5단이 `LD-SAFE-001` 수용 외의
   rule_id 를 낸다)로 바꿨다.
2. **안 쓰는 import 를 정당화하는 빈 시험을 만들었다.** `assert callable(beam)` 류는 깨질 수
   없어 계기가 아니다 — import 와 함께 지웠다. 첫 RED 의 「2 passed」 중 하나였다.
3. 🔴 **어둠 검사가 요청 group 만 봐서, 공유 fixture 를 다른 group 이 밝히면 통과했다.**
   처음에는 이것을 §E.3 미검증에 적고 넘기려 했다 — 근거는 「겹침은 `conflict.py` 가 이미
   막는다」였는데 그것을 **재지 않았다.** 계약이 fixture 전개를 요구하는 바로 그 실패
   형태이므로 기록이 아니라 수정으로 닫았다(`72b4e723`): `mib.shadow_groups` 가 겹치는
   group 전부를 내고, 전개 규칙은 복사하지 않고 `conflict.group_fixtures` 를 public 으로
   올려 한 자리를 공유한다. 시험 3개를 더했고 그중 하나는 **구멍 대조군**이다(분리된 group 이
   밝아지는 것은 통과 — 없으면 「다른 group 이 밝으면 무조건 막는다」와 구별되지 않는다).
4. **`ruff check ... | tail -3 && echo "LINT OK"` 가 거짓 초록을 냈다.** 파이프의 종료 코드는
   `tail` 의 것이라 ruff 가 실패해도 `&&` 가 통과한다 — import 정렬 오류 1건이 「LINT OK」로
   보고됐다. 저장소의 `test_overlap_preserve.py::TestTouchedFilesPassLint` 가 잡았다.
   종료 코드를 보려면 파이프 없이 돌려야 한다. zsh 글롭에 먹혀 grep 이 0 을 답한 C3 의 결함과
   같은 계열이다 — **계기의 출력만 보고 계기의 상태를 믿었다.**

#### Evidence — 경계 (실제 출력)

```
$ grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/     → OK - no OSC import
$ grep -rnE "^\s*(from|import)\s+server\.(looks|web)" server/director/ → OK - no artistic producer
$ git diff --name-only origin/main -- server/lxseq server/design server/director/service.py
                                                                       → (없음) OK - untouched
$ uv run ruff check server/director/ server/tests/                     → All checks passed!
```

#### 만든 파일 · 고친 파일

```
신규  server/director/validate/mib.py                  어둠의 창 · random_access 광고 검증
신규  server/tests/test_director_validate_mib.py       30 시험
수정  server/director/validate/pipeline.py             5단에 배선
```

C1~C5 로 **6단 전부가 실물 판정기**가 되었다 — 1단만 계획 단독 판독 범위의 수용이고,
2~5단은 실제 검사를 부르며 6단은 승인 소유를 진술한다. 콘솔 없이 할 수 있는 것은 여기까지다.

## §E.3 Gaps — C2 에서 하지 않은 것

- **「불가능 해상도 차단」(`AC-LDPLUGIN-009` 마지막 항목) 미구현.** emitter 최소 timing
  해상도를 알아야 판정할 수 있고 그 실측은 0건이다(C6). C1 의 capability 단계가 무조건
  blocking 이므로 유보 상태의 기본값은 안전한 쪽이다.
- **`rounding_conflicts` 의 호출자가 없다.** `(group, axis, beat)` 목록을 만들어 넘기는 곳이
  아직 없어서 이 검사는 현재 **경로에 안 이어져 있다**. 그 목록은 FX cycle/phase 를 낮추는
  C3·C6 이 만든다. 부품으로만 초록이라는 뜻이며, 이 문장이 그 사실을 남긴다.
- **FX tempo 교차 검사가 규범 예제에서는 도지 않는다.** 예제의 beat_map 이 단일 segment 라
  내부 경계가 0개여서 조기 반환한다. 합성 2-segment 입력으로만 실측했다.
- **`ContextSnapshot` digest 대조 없음.** `check_timing` 은 dict 둘만 본다. 대조는 상위 층.
- **`spec.md` §6.1(축별 emitter 0건) 판정 미해결.** Tier 재산정은 여전히 열려 있다.
- **독립 감사 없음.** `plan-auditor` 는 이 저장소에서 착수 전 컨텍스트 초과로 죽는다
  (LDSTORE `progress.md` §F 실측 ≈114K 토큰). 오케스트레이터가 구현자이면서 검토자다.
- **CI 는 과금 차단으로 죽어 있어 판정 근거가 아니다.** 위 로컬 출력만 증거로 썼다.

### C3 에서 하지 않은 것

- **`terminal_state` 의 `ownership` 재획득 규칙은 계약 문면이 아니라 내 해석이다.** 계약은
  `held`/`released` 두 값만 적고 재획득을 말하지 않는다. 「쓰면 다시 소유한다」를 택했고
  근거는 부분 재진입을 별도로 막는다는 것뿐이다 — 우산 수준 확인을 받은 것은 아니다.
- **첫 cue 의 `fx_start` 를 blocking 으로 만든 것도 해석이다.** 계약은 *"active FX 없음이
  **target 에서** 확인되어야"* 라고 적었고 그것은 콘솔 관측이다. 계획 문면에서 판정할 수
  있는 근사로 「baseline cue 안에서 FX 를 켜지 않는다」를 택했다. 실기 관측(C6)이 진짜 판정이다.
- **`_MAX_BEAT_REQUESTS_PER_INSTANCE = 10000` 은 상한이며 그 너머를 안 본다.** 상한에 닿는
  입력에서 그 뒤의 반올림 충돌은 검사되지 않는다. 어떤 입력이 상한에 닿는지 실측하지 않았다.
- **`settle_ms` 를 예약 구간에 넣지 않았다.** 계약은 정착시간을 *"마지막 movement fade 완료 후
  reveal 전"* 으로 적어 reveal 타이밍의 개념으로 두었다. 충돌 구간에 더할 근거를 찾지 못해
  넣지 않았고, 이 판단은 검증되지 않았다.
- **`LD-STATE-002` 의 *"마지막 cue 뒤에도 fade 가 남으면 duration 내 완료"* 미구현.** 곡
  duration 은 context 쪽이며 `check_ready` 는 context 를 받지 않는다. 어느 층이 볼 것인지
  정하지 않았다.
- **독립 감사 없음.** `plan-auditor` 는 이 저장소에서 착수 전 컨텍스트 초과로 죽는다
  (LDSTORE `progress.md` §F 실측 ≈114K 토큰). 오케스트레이터가 구현자이면서 검토자다.
- **증거 파일이 이 워크트리에만 있다.** `.moai/state/` 가 gitignore 되므로
  `.moai/state/verify/c3/*.txt` 는 커밋되지 않았고 `git status` 에도 안 나온다. 워크트리를
  지우면 위 인용의 근거가 사라진다.

> **C2 기록 정정 (2026-09-16 실측)**: C2 의 §E.2·§E.3 이 *"CI 는 과금 차단으로 죽어 있어
> 판정 근거가 아니다"* 라고 적었으나, `gh run list --limit 5` 로 재니 최근 5건 중 4건이
> `success`(하나는 `cancelled`)로 **CI 는 살아 있고 초록이다.** C2 의 기록은 그때 참이었을
> 수 있으므로 고치지 않고, 이 정정을 C3 의 사실로 남긴다. 다만 C3 의 위 증거는 전부 로컬
> 출력이며 이 브랜치는 아직 push 되지 않아 CI 판정을 받지 않았다.

## §E.4 Residual-risk

- `TestContractExamplePasses` 는 「계약 fixture 가 timing 단계를 통과한다」를 전제한다. 계약
  의도가 「이 fixture 도 tempo 미확정이라 막혀야 한다」였다면 §6.1 예외 해석부터 다시 봐야
  한다. 근거는 §6.1 문면이며 우산 수준 확인을 받은 것은 아니다.
- 2단이 통과 경로에서 내는 진단은 root pointer 3개뿐이다(cue 16개·action 60개인 규범 예제
  에서도). action별 coverage 는 4단(capability)이 채우므로 계약 §6.3 은 지켜지지만, 2단만
  보면 큐별 확인이 침묵이다. 큐별 판정 결함은 이 층의 출력만으로는 안 보인다.
- `_uncovered_ms` 는 덮인 구간을 시작점부터 이어붙여 본다. segment 가 겹쳐 있는 병리적
  입력에서는 커서가 앞으로만 가므로 보수적으로(막는 쪽으로) 답한다 — 스키마가 겹침을
  막지 않으므로 가능한 입력이다.

### C4 에서 하지 않은 것

- **RED 부재.** 위 §E.2 C4 절에 적은 대로 pre-GREEN 실패 출력이 없다. 이 마일스톤에 대해
  test-first 는 **주장이지 증거가 아니다.** 뮤테이션 셋은 「시험이 회귀를 잡는다」만 보인다.
- **`random_access` 를 판정하지 않았다.** `LD-CAP-001` 이 여섯 축(op·preset·timing 축·cycle·
  dark_move·random_access) 중 하나로 열거했는데 계획 payload 에 이것을 요구하는 필드가
  없다 — `playback` 쪽 개념으로 보이며 어느 층이 볼 것인지 정하지 않았다. C5(`mib.py`)가
  `AC-LDPLUGIN-012` 로 다룰 후보다.
- **`AXIS_TIMING_OBSERVED` 가 채워질 때 무엇이 갈라지는지 시험하지 않았다.** 지금은 빈
  tuple 이라 상시 사유가 모든 축에 붙는다. 일부만 관측된 상태(예: intensity 만)에서 축별로
  갈라지는지는 C6 전까지 재지 않는다 — 그 상태를 합성해 시험할 수는 있었지만, 관측 없이
  「승격 후 동작」을 고정하면 그 시험이 승격의 근거처럼 읽힐 위험이 있어 두지 않았다.
- **`safety_blocked` 를 4단에서 낸다** (정책 상한 초과·금지 preset). 5단이 safety 단계인데
  원인 분류상 4단에 두었다 — `AC-LDPLUGIN-008` 2번이 clamp 금지를 capability AC 에 적었기
  때문이다. 단계 경계가 흐려지는 비용을 감수한 선택이며 우산 확인을 받지 않았다.
- **기준선을 C4 워크트리에서 다시 재지 않았다.** C3 절의 13255 를 기준선으로 인용했다.
  같은 커밋이므로 같아야 하지만, 그것은 재지 않은 추론이다.
- **독립 감사 없음** (C2·C3 와 동일). `plan-auditor` 가 컨텍스트 초과로 죽는다.

### C5 에서 하지 않은 것

- **어둠은 계획 문면에서만 증명된다.** 계약은 *"intensity=0 및 intensity FX 없음이
  증명되어야"* 라고 적었고 진짜 증명은 **target 관측**이다(`AC-LDPLUGIN-012` 콘솔 PASS 조건:
  movement 시작부터 늦은 완료 + `settle_ms` 까지 실제로 어두운지 본다). 이 층이 하는 것은
  계획이 스스로 모순되지 않는지까지이며, 콘솔이 그 계획대로 동작하는지는 C6 이다.
- **`require_dark_move` 를 보지 않는다.** `safety` snapshot 에 이 플래그가 있고 규범 예제는
  `false` 다. `true` 일 때 「모든 position_set 이 dark_move 여야 한다」로 읽는 것이 자연스럽지만
  계약이 그렇게 적지 않아 넣지 않았다 — 읽는 방식을 자식이 정하면 그것이 조용한 규범이 된다.
- ~~다른 group 의 fixture 를 공유하는 경우를 보지 않는다.~~ → **미검증으로 적다가 고쳤다**
  (커밋 `72b4e723`). 아래 「자기 검토」 3번 참조. 처음에는 「겹침은 `conflict.py` 가 이미
  막는다」에 기대어 범위 밖으로 두려 했는데, 그것은 **재지 않은 추론**이었고 계약이 fixture
  전개를 요구하는 바로 그 실패 형태였다.
- **`random_access` 판정이 계획을 보지 않는다.** `check_random_access` 는 context 의 신고만
  본다. 계약 `LD-REENTRY-001` 의 나머지 절(*"compiler 는 이전 cue 를 수동 실행해야만 맞는
  숨은 tracking 상태를 남기지 않는다"*)은 emitter 가 있어야 판정할 수 있어 C6 이다.
- **`dark_windows` 는 pan·tilt timing 이 둘 다 없으면 조용히 건너뛴다.** 스키마가 둘 다
  요구하므로 정상 입력에서는 생기지 않지만, 스키마를 우회한 입력에서는 창이 만들어지지 않아
  어둠 검사가 사라진다. 4단이 축 timing 부재를 blocking 으로 잡지만 그것은 다른 단계의
  검사에 기댄 것이다.
- **독립 감사 없음** (C2~C4 와 동일).

### C5 잔여 위험

- **정착값 판정이 「마지막으로 완료된 쓰기」 하나에 의존한다.** 같은 시각에 끝나는 쓰기가
  둘이면 `(end_ms, start_ms)` 최대값으로 하나를 고르는데, 그 상황 자체가 C3 의 충돌 검사가
  막는 형태다. 즉 이 tie-break 는 **다른 단계가 막아 주는 것에 기댄** 코드이며, 그 검사가
  느슨해지면 여기서 조용히 임의의 값을 고른다.
- **창을 시간 구간으로만 다룬다.** intensity 의 곡선(`curve`)을 보지 않으므로 fade 중간값이
  0 에 매우 가까운 경우도 미증명으로 막는다. 보수적인 방향이라 안전하지만, 실기에서 정당한
  계획이 막히는 사례가 나오면 곡선을 봐야 할 수 있다.
- **이 브랜치는 push 전 CI 판정을 받지 않았다** (C3·C4 와 동일 구조).

### C3 잔여 위험

- **충돌 검출이 전수 쌍 비교다.** 한 `(fixture, axis)` 키의 예약 수 n 에 대해 O(n²) 이다.
  규범 예제(fixture 8 · 축 5 · 예약 수백)에서 0.5초 안에 끝나지만, 큐가 수천인 계획의
  실측은 없다. 인접 쌍만 보는 최적화는 「배열 순서로 덮어쓰지 않는다」를 깨뜨릴 수 있어
  택하지 않았다 — 성능 문제가 실제로 관측되면 그때 정렬 기반 sweep 으로 바꿔야 한다.
- **`overlaps` 의 「같은 시작 시각이면 충돌」 절이 반열림 판정과 별개 규칙이다.** 길이 0
  구간(순간 변경)을 잡기 위한 것인데, 이 절 때문에 *같은 시각에 시작해 곧바로 끝나는*
  두 예약이 항상 충돌한다. 계약 *"한 instant 의 중복 쓰기는 conflict"* 와 일치하지만,
  두 규칙이 한 술어에 얹혀 있어 한쪽을 고치면 다른 쪽이 조용히 바뀔 수 있다.
- **`fx_beat_requests` 가 부동소수 누적으로 박을 전진시킨다** (`beat += cycle`). 반복이
  수천 회면 누적 오차가 ms 반올림 경계를 넘길 수 있다. 곱셈(`start + k*cycle`)이 더
  안전하지만, 그 차이가 실제 판정을 바꾸는 입력을 찾지 못해 바꾸지 않았다.
- **이 브랜치는 push 되지 않아 CI 판정을 받지 않았다.** 위 증거는 전부 이 워크트리의 로컬
  출력이며, 「내 트리에서 초록」은 「머지 후 초록」이 아니다. 기준 HEAD 가 `origin/main` 과
  같으므로 차이가 생길 여지는 작지만, 그것은 재지 않은 추론이다.

### C6 emitter + 프로브 진행 중 (REQ-LDPLUGIN-013) — 미완료, 승격 없음

워크트리 `.claude/worktrees/ldcompile-c6` · 브랜치 `WT-emitter-probe` · 기준 HEAD
`b3819fbf` (= C5 머지 직후의 `origin/main`) · 구현 커밋 `3c74f3cf`.

**Claim**: `server/director/emit.py` — 계약 §145 형태의 manifest + frozen artifact
bytes 를 낸다. 실측된 `CueFade` 만 emit 하고 축별 timing 요청은 거부한다. 콘솔 프로브로
축별 timing 문법 **후보**를 찾았으나, **승격은 하지 않았다** — `AXIS_TIMING_OBSERVED` ·
`RANDOM_ACCESS_OBSERVED` 는 여전히 빈 tuple 이다. **C6 은 미완료**: P1(쓰기·되읽기)과
P2(무대 관측)가 남아 있다.

#### Evidence — 기준선 (이 트리에서 직접 실측)

```
$ uv run pytest -q
13316 passed, 35 skipped, 1 warning in 219.64s (0:03:39)
```

경계 검사 4건 (plan.md §5): OSC import 0 · 예술 producer import 0 · `server.design` 리터럴
import 0 · PRESERVE 무변경.

#### Evidence — emit.py GREEN + 회귀

```
$ uv run pytest server/tests/test_director_emit.py -q
23 passed in 0.05s

$ uv run pytest -q
13339 passed, 35 skipped, 1 warning in 181.21s (0:03:01)   # 13316 + 23, 정확히 일치
```

뮤테이션 2건으로 시험 비공허성 확인: `cue_number = index + 1` → `+ 2` 로 밀면 3 failed;
축별 거부(`if axes:`)를 `if False:` 로 죽이면 5 failed. 원본 복구 후 재확인.

**설계 결정 3건**: (1) digest 는 인자로 받고 `artifact_sha256` 만 자기가 만든 bytes 를
해시 — `compiled_digest` 는 만들지 않는다(JCS 정규화를 stdlib 로 근사하면 깨진다는 이
저장소의 실측 때문). (2) 축별 timing 요청은 조용히 clamp·drop·대체하지 않고 거부
(`AC-LDPLUGIN-008`). (3) `server.design.cue_fade` 를 import 하지 않는다(`plan.md §3`
읽기 전용) — 대신 문면 대조 시험이 두 벌 갈라짐을 잡는다.

**서브에이전트 배차 실패 (두 번째 실측)**: `manager-develop` 에 이 구현을 배차했으나
`Prompt is too long` 으로 첫 파일도 읽기 전에 종료됐다(자동 압축도 빈 응답으로 실패).
`plan.md §7` 이 이미 적어 둔 컨텍스트 초과(≈114K 토큰)가 이번엔 구현 배차에서도
재현됐다 — 직접 구현으로 전환했다.

#### Evidence — P0 ① 콘솔 도달 (읽기 전용, 여러 차례 재측정)

세션 중 콘솔 통로가 여러 번 끊기고 복구됐다. 최종 정상 상태: onPC OSC 1행 수신(8000,
prefix `copilot`) · 2행 송신(`127.0.0.1:9005`, `Send=Yes`) — 응답기 `osc_slot = 2` 와
일치. `curl http://127.0.0.1:8765/healthz` → `{"health":"online"}`, `GET /api/presets`
→ 14개 실기 프리셋 풀.

**부수 소득 — `SendOSC N` 의 의미(실측)**: `SendOSC 3` → `OK`(행 3 존재+Send=Yes),
`SendOSC 4` → `Illegal object`(행 없음), `SendOSC 2` → `Illegal property`(행은 있으나
Send=No). `N` 은 **행 번호 그대로**이며 Send 행만 세는 번호가 아니다. MA3 는 「행 없음」과
「보낼 수 없음」을 다른 오류 문구로 구분한다.

#### Evidence — P0 ② 축별 timing 문법 조회 (읽기 전용, `introspect_probe`)

```
$ uv run python -m server.tools.introspect_probe --path "DataPool/Sequences/13/1/1" \
    --all-pages --listen-port 9005
```

CuePart 레벨에서 발견: `PRESET1FADE`·`PRESET1DELAY` … `PRESET16FADE`·`PRESET16DELAY` ·
`INDIVIDUALTIMING`·`INDIVFADE`·`INDIVDELAY` · `CUEINFADE`·`CUEOUTFADE` 등. 값 읽기 —
`PRESET1FADE`/`PRESET2FADE`/`PRESET4FADE`/`PRESET5FADE` 전부 `ok:true, v:"CueTiming"`
(상속=재정의 통로). Sequence·Cue 레벨(63·23개 필드)에는 없었다 — **저장소 코드 판독**
(`PanFade`·`IndividualFade` 등 0건, `cde2744`)과 **콘솔 판독**은 범위가 달랐을 뿐 모순이
아니다: 콘솔은 같은 능력을 다른 이름(`PRESET<n>FADE`)으로 갖고 있었다.

전체 원자료: `.moai/state/verify/c6/p0-introspect-record.md`,
`introspect-{seq13,cue,cuepart}.json`.

#### Evidence — P1 ① 쓰기 시도 (실측, 감독 승인 후)

감독 승인(빈 시퀀스 1999 새로 생성 → 후보 3종 시도)을 받고 `server/tools/ldcompile_c6_p1_axis_timing_probe.py`
를 새로 만들어 돌렸다(`--approve` 없으면 아무것도 안 쏘는 t60 계열 형태 승계). 매 실행 전후로
`server.web`(주 체크아웃, PID 는 실행마다 다름)을 정확히 같은 방식으로 잠깐 멈추고 재기동했다
— `introspect_probe` 가 자기 OSC 리슨 포트(9005)를 독점으로 열어야 해서 이미 뜬 서버와
공존 못 한다.

**대조군 — `Store Sequence 1999 Cue 1 'LDCOMPILE-C6 SCRATCH DELETABLE' CueFade 1`**: 1차 실행
`ok:true`(시퀀스·큐 생성 성공). 2차 실행(같은 명령 재실행) `"User Canceled Command"` —
이미 존재하는 큐를 다시 Store 하면 콘솔이 확인 팝업을 띄우고, 사람이 없어 자동 취소된 것으로
보인다(재현 검증 안 함, 가설).

**후보 3종 전부 관측 실패** — `AXIS_TIMING_OBSERVED` 는 채우지 않는다:
- `Fixture 'MOVER-ALL'` → `"Illegal object"`. `Fixture` 동사가 그룹 이름을 안 받는다(그룹은
  `Group` 동사일 가능성 — 미검증). 이중인용(`"..."`) 은 이 브릿지 자체가 거부한다
  (`server/bridge/protocol.py:126-130` — 플러그인 인자로 감쌀 때 조기 종료되기 때문. 단일인용
  으로 고쳐 재실행함).
- `Attribute 'Position'` → `"Illegal object"`.
- `PRESET2FADE 3 Enter` / `PRESET2DELAY 1 Enter` (bare 명령 동사로) → `"Illegal object"` 둘 다.
  P0 에서 읽힌 이 이름들은 **속성(property) 이름**이지 **명령줄 동사**가 아니다 — 이 형태로는
  못 쓴다.
- `Fade 3 Enter` / `Delay 1 Enter` / `Store … /Merge` 자체는 매번 `ok:true` 였지만, 앞선
  `Fixture`/`Attribute` 선택이 전부 거절돼 프로그래머가 비어 있었다 — 무엇에도 적용 안 된
  빈 실행이라 의미 있는 결과가 아니다.
- **되읽기로 확정**: `PRESET2FADE`/`PRESET2DELAY` = `"CueTiming"`(상속, 불변) ·
  `INDIVIDUALTIMING` = `"Default"` · `INDIVFADE`/`INDIVDELAY` = `0.0` · `CUEINFADE` = `0.0` —
  세 후보 다 아무 값도 못 썼다. 깨끗한 음성 결과다.
- **부수 발견**: `NAME` 이 의도한 `'LDCOMPILE-C6 SCRATCH DELETABLE'` 이 아니라 콘솔이 붙인
  기본값 `"Sequence 1999"` 로 읽힌다 — Store 의 이름 인용부가 실제로는 안 먹었을 수 있다
  (미조사, cue 이름과 시퀀스 이름 혼동 가능).
- **물리 안전**: `Fixture`/`Group` 선택이 매번 거절돼 프로그래머에 아무 것도 안 올라갔다 —
  실제 무빙헤드가 움직인 흔적 없음(감독 확인 + 명령 응답 둘 다 일치).

**round 2 — `Group 'MOVER-ALL'` (Fixture 대신)**: 이번엔 `ok:true, "OK"` — 그룹 선택 동사는
`Fixture` 가 아니라 `Group` 이었다(가설 확정). 하지만 후속은 그대로 막힘:
- `Attribute 'Position'` → 여전히 `"Illegal object"`. Position 속성에 초점을 맞추는 올바른
  동사/문법은 아직도 못 찾았다.
- `PRESET2FADE 3 Enter` / `PRESET2DELAY 1 Enter` → 여전히 `"Illegal object"`.
- 되읽기 재확인: `PRESET2FADE`/`PRESET2DELAY` = `"CueTiming"` · `INDIVIDUALTIMING` = `"Default"` ·
  `INDIVFADE`/`INDIVDELAY`/`CUEINFADE` = `0.0` — round 1 과 완전히 동일, **여전히 관측 0건**.
  `Group` 만 맞고 Position 값 자체를 프로그래머에 넣는 통로가 없어서, 있지도 않은 Position 데이터에
  개별 timing 을 얹을 수가 없는 것으로 보인다(가설).
- **물리 안전 갱신**: 이번엔 `Group 'MOVER-ALL'` 이 실제로 성공해 그룹이 프로그래머에 올라갔다
  (감독 사전 확인: 지금은 안전한 상태). Position 값은 끝까지 못 넣었으므로 실제 조명 이동은
  없었을 것으로 보이나, **명령 응답만으로 확정한 것이지 무대를 직접 보고 확인한 것은 아니다**.

다음 후보(미시도, 사람 판단 필요): Position 값을 프로그래머에 실제로 넣는 통로(프리셋 풀
번호로 직접 `Recall`/`At Position <pool>.<no>` 형태 등) · Attribute 초점 동사의 정확한 문법 ·
그랜드MA3 정식 문서 또는 감독 실기 조작으로 확인.

#### Evidence — P1 ③ round 3/4 — Position 값 쓰기는 검증됨(선행 자산 재사용), timing 은 여전히 관측 0건

감독이 「이미 있는 코파일럿 기능·과거 작업을 다시 보라」고 정정을 줘서 재조사했다.
`server/spatial/pointing.py`(`aimed_commands`/`preset_recall_command`) + `server/presets/store.py`
가 이미 **검증되고 실전에 쓰인** Position 값 쓰기 통로를 갖고 있었다 — round 1/2 의 실패는
문법을 잘못 짜서였다(기능 부재가 아니었다):
- `Fixture <fid>`(그룹 이름 아님, fid **번호**) ; `Attribute 'Pan' At <deg>` ; `Attribute 'Tilt' At <deg>`
  — Pan·Tilt 는 이미 **독립된 속성**이다(값 레벨). 전제 5의 절반은 이걸로 풀렸다.
- fid 목록은 `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` 실측:
  MOVER-U 501~508(Robe MegaPointe) · MOVER-D 521~528(Robe Spiider) = MOVER-ALL 16대.
  감독 승인 받아 fid **501 하나만** 사용(물리 이동 최소화).
- 임의 각도 대신 이미 존재하는 `Preset 2.1`("POS01 보컬 센터 페이스 · 합성좌표", 콘솔 조회로
  확인)을 그대로 recall — 새 좌표를 지어내지 않았다.

**round 3(Store 없이 값만 설정)**: `Fixture 501 ; At Preset 2.1 Fade 3 Delay 1` → `ok:true`.
`Fixture 501 ; At Preset 2.1` → OK, `Attribute 'Pan' At 200 Fade 3` → OK, `Attribute 'Tilt' At 45
Fade 1` → OK. `IndividualTiming On`(bare) → 여전히 `"Illegal object"`. 매 recipe 끝의 `ClearAll`
이 프로그래머를 비워 아무것도 Cue 에 안 남았다(이 라운드의 결함 — Store 를 안 넣었다).

**round 4(같은 값 설정 뒤 새 Cue 에 Store)**: `Fixture 501 ; At Preset 2.1 Fade 3 Delay 1` →
`Store Sequence 1999 Cue 3 'R4 recall-inline'` — 둘 다 `ok:true`. `Fixture 501 ; At Preset 2.1` →
`Attribute 'Pan' At 200 Fade 3` → `Attribute 'Tilt' At 45 Fade 1` → `Store Sequence 1999 Cue 4
'R4 attribute-inline'` — 넷 다 `ok:true`. **되읽기(Cue 3·Cue 4 둘 다 CuePart 1)**:
`PRESET2FADE`/`PRESET2DELAY` = `"CueTiming"` · `INDIVIDUALTIMING` = `"Default"` ·
`INDIVFADE`/`INDIVDELAY` = `0.0` — **양쪽 다 여전히 기본값**.

**결론(round 1~4 종합)**: Position **값** 쓰기는 완전히 검증되고 동작한다(fid·Attribute
Pan/Tilt·Preset recall 전부 `ok:true`, 실제 fid 501 물리 이동 확인). 하지만 `At`/`Attribute`
클로즈 뒤에 `Fade`/`Delay` 토큰을 이어붙이는 건 콘솔이 **문법 오류 없이 받아주지만**(`Illegal
object` 아님) `PRESET2FADE`/`INDIVIDUALTIMING`/`INDIVFADE`/`INDIVDELAY` 어느 필드에도 **관측
가능한 효과가 없다** — 이건 round 1/2 의 "선택 자체가 막혀서 값이 없었다"는 혼입 변수가 전혀
없는 상태에서 나온 결과라 이전보다 훨씬 강한 음성 증거다. `IndividualTiming` 을 bare 동사로 못
쓰는 것도 재확인됐다. `AXIS_TIMING_OBSERVED` 는 여전히 빈 tuple.

다음 후보(미시도, 사람 판단 필요 — 그랜드MA3 정식 문서 또는 감독 실기 조작 필요): Cue View의
타이밍 그리드에서 UI 로만 되는 편집(명령줄 등가물이 없을 수 있음) · `Assign`/`Copy To` 계열
동사 · 이 필드들이 command-line 이 아니라 오직 매크로/플러그인 API 로만 쓰일 수 있는 가능성.

#### Evidence — P1 ④ round 5 — 인접 카드(t215) 문법 재사용으로 PRESET2FADE/DELAY 관측 성공

라운드 1~4 는 전부 **프로그래머 경로**(`Fixture`/`Attribute`/`At` + `Store`)만 시도했다.
「안 된다」로 다시 결론 내리기 전에 이 저장소 안에서 이 능력의 기존/인접 구현을 넓게
재탐색하라는 지시에 따라 `grep -rliE 'PRESET2FADE|INDIVFADE|...'`을 서버 전체에 다시
돌렸고, **다른 카드 `t215`**(`.moai/reports/t215/verdict.md`, 2026-09-01 실측, 콘솔 접촉)가
전혀 다른 경로 — **`Set Cue <n> Sequence <seq> Property '<name>' <value>`** — 를 이미
발견·되읽기까지 확정해 두고 있었다. t215 의 F1 행이 정확히 `Set Cue 1 Sequence 9 Property
'Preset2Fade' 4` → `ok` → 되읽기 `PRESET2FADE` **4.0** 을 실측했다 — C6 이 4라운드 동안 못
찾은 바로 그 속성명이다.

이 형태를 **다시 추측하지 않고 그대로** `ldcompile_c6_p1_axis_timing_probe.py` 에 Round 5 로
추가해(`server/tools/ldcompile_c6_p1_axis_timing_probe.py:95-128`), C6 의 SEQ_NO(1999) ·
기존 baseline Cue(2) 위에서 재현했다. 물리 접촉 없음(Fixture/Group 선택도, 프로그래머 진입도
전혀 없다 — Set…Property 는 이미 저장된 Cue 의 CuePart 속성을 직접 덮어쓴다).

**실행 (실제 응답, `--listen-port 9005`, server.web 정지 후 재기동)**:

```
$ uv run python -m server.tools.ldcompile_c6_p1_axis_timing_probe --approve --listen-port 9005
"set_property_preset2fade_on_existing_cue"  → Set Cue 2 Sequence 1999 Property 'Preset2Fade' 4     → ok:true "OK"
"set_property_preset2delay_on_existing_cue" → Set Cue 2 Sequence 1999 Property 'Preset2Delay' 1.5  → ok:true "OK"
"set_property_indivfade_on_existing_cue"    → Set Cue 2 Sequence 1999 Property 'IndivFade' 2       → ok:true "OK"
"set_property_indivdelay_on_existing_cue"   → Set Cue 2 Sequence 1999 Property 'IndivDelay' 0.8    → ok:true "OK"
"set_property_individualtiming_on_existing_cue" → Set Cue 2 Sequence 1999 Property 'IndividualTiming' 'On' → ok:false "Illegal value"
```

**되읽기 함정 회피 — 경로를 먼저 검산했다.** `ok:true` 는 값 보존의 증거가 아니다
(t215 자신의 C2 `Zorble` 함정과 같은 계열). 처음 되읽은 경로 `DataPool/Sequences/1999/2/1`
은 전부 기본값을 답해 의심스러웠다 — child-index 를 Cue 번호와 동일시한 **내 가정이
틀렸다**는 신호였다. `NAME` 을 index 1~6 에서 전수로 읽어 오프셋을 확정했다:

| index | NAME | 정체 |
|---|---|---|
| 1 | `OffCue` | 무관 잔존 큐 |
| 2 | `CueZero` | 무관 잔존 큐 |
| 3 | `LDCOMPILE-C6 SCRATCH DELETABLE` | Cue 1 (round 1/2) |
| **4** | `LDCOMPILE-C6 SCRATCH DELETABLE R3` | **Cue 2 (이번 baseline)** |
| 5 | `R4 recall-inline` | Cue 3 |
| 6 | `R4 attribute-inline` | Cue 4 |

즉 이 Sequence 는 child-index = Cue 번호 + 2 다(앞에 무관한 잔존 큐 둘이 있다). 정정된 경로
`DataPool/Sequences/1999/4/1` 되읽기:

```
PRESET2FADE   : string "CueTiming" → number 4.0    ✅ 관측 성공 — 타입까지 바뀌었다
PRESET2DELAY  : string "CueTiming" → number 1.5    ✅ 관측 성공
INDIVFADE     : number 0.0 (불변)                   ❌ ok:true 였지만 값은 그대로 — 진짜 무효과
INDIVDELAY    : number 0.0 (불변)                   ❌ 진짜 무효과
INDIVIDUALTIMING : string "Default" (불변)          — 거절됐으므로 예상대로 불변
```

INDIVFADE/INDIVDELAY 의 무효과는 **경로 오류가 아니다** — 같은 정확한 경로에서 형제
속성(PRESET2FADE/DELAY)이 실제로 바뀌었으므로, 이 무효과는 진짜 음성 결과다. `Set…Property`
동사가 `PRESET<n>FADE/DELAY` 계열에는 통하고 `INDIVFADE`/`INDIVDELAY` 에는 안 통한다 —
후자는 t215 F5 가 관측한 **다른 경로**(bare `Group <n> At <레벨> Fade <시간>` + `Store`,
intensity 대상)로만 확인됐고, 그 경로가 Position 에도 적용되는지는 여전히 미측정이다.

**승격 방식 — 감독 판정을 받았다(2026-09-16).** `PRESET2FADE`/`PRESET2DELAY` 는 Position
**한 preset type 전체**의 값이며 pan·tilt 를 가르지 못한다(§E.3 Gap "pan ≠ tilt 독립성
미확립" 그대로 남는다). `AXIS_TIMING_OBSERVED` 를 그대로 채우면 pan·tilt 에 **다른** 값을
요구하는 요청까지 통과시켜 버린다 — 그런 요청은 이 통로로 충실히 재현할 수 없다(값이
하나로 합쳐진다). 그건 이 SPEC 이 처음부터 막아 온 바로 그 "관측 없는 승격"이 된다. 또한
기존 `emit.py::emit_compiled` 는 `AXIS_TIMING_OBSERVED` 를 전혀 참조하지 않고 축별
timing 이 있으면 무조건 거부했다 — capability 단(4단)만 열어도 emit 단이 그대로 막는
구조적 간극이었다.

**판정: 제한적 승격.** pan==tilt(같은 값 요구)일 때만 관측된 것으로 본다. 두 파일을
같이 고쳤다(TDD, RED→GREEN):

- `server/director/validate/capability.py` — `AXIS_TIMING_OBSERVED = ("pan", "tilt")`.
  `_axis_timing_is_reproducible`(신규)이 pan·tilt 둘 다 선언 + 같은 값일 때만 참을
  반환한다. 하나만 선언했거나(예: pan 만) 값이 다르면 여전히 unsupported — 사유는 값이
  다를 때만 `_POSITION_MISMATCH_REASON`(신규, "관측 0건"이 아니라 "다른 값은 못 나눈다"로
  정확하게)으로 갈린다.
- `server/director/emit.py` — 같은 판정을 거울로 둔다(`AXIS_TIMING_OBSERVED` 를 import 하지
  않고 복제 — `store_with_measured_fade`/design 층의 짝과 같은 이유, 대조 시험이 갈라짐을
  잡는다). pan==tilt 인 `position_set` 은 `_position_timing_commands`(신규)가 `Set Cue <n>
  Sequence <seq> Property 'Preset2Fade'/'Preset2Delay' <값>`(t215 문법, ms→초 변환)을 Store
  뒤에 이어 붙인다. **한 cue 안에서 group 이 다른 position_set 둘이 다른 timing 을 요구하면
  거부한다** — `Preset2Fade`/`Preset2Delay` 는 CuePart 전체에 걸리는 값 하나뿐이라 group 별로
  나눠 담을 수 없기 때문이다(새로 발견한 구조적 제약, `_POSITION_CUE_PART_COLLISION_REASON`).

**RED→GREEN 증거 (실제 출력)**:

```
$ uv run pytest server/tests/test_director_validate_capability.py server/tests/test_director_emit.py -q  # RED (구현 전)
4 failed, 27 passed / 5 failed, 24 passed  # 각각 의도한 신규 시험만 실패

$ uv run pytest server/tests/test_director_validate_capability.py server/tests/test_director_emit.py -q  # GREEN (구현 후)
31 passed / 30 passed

$ uv run pytest server/tests/ -k "director_validate" -q
237 passed, 13140 deselected

$ uv run pytest -q
13349 passed, 35 skipped, 1 warning in 176.09s (0:02:56)
```

**뮤테이션 2건으로 신규 시험 비공허성 확인** — 원복 후 재확인:

| 뮤테이션 | 결과 |
|---|---|
| `_axis_timing_is_reproducible` → 항상 `True` | **7 failed**(옛 시험 5 + 신규 시험 2 — 옛 시험도 여전히 산다) |
| cue-part 충돌 검사 제거(`_position_timing_commands`) | **1 failed** — 의도한 그 시험 정확히 |

**cross-file 회귀 둘을 고쳤다(둘 다 승격의 정당한 결과, 결함이 아니다)**:
1. `test_director_validate_capability.py::TestOpTableCoversTheSchema.test_every_op_receives_a_blocking_diagnostic`
   — `position(GROUPS[0])` 기본값(pan==tilt==0)이 이제 조용히 통과해 이 시험 취지와
   충돌 — pan≠tilt 로 만든 action 으로 교체.
2. `test_director_validate_capability.py::TestUnmeasuredEmitterIsTheStandingReason.test_every_action_in_the_contract_example_is_blocked`
   — 규범 예제의 `action-003`·`action-007`(둘 다 `position_set`, pan==tilt==0)이 이제
   진단 0건으로 통과한다 — 그 둘을 예외로 밝히고, **여전히 재현 가능한 채로 남아
   있는지**(`isdisjoint`)까지 양성으로 단언하도록 강화했다.
3. `test_director_validate_timing.py::TestWiredIntoThePipeline.test_validator_carries_the_injected_context`
   — 같은 두 action 때문에 with/without context 진단 **개수**가 우연히 같아졌다(68==68).
   원래 취지("2단 진단의 내용이 다르다")를 개수 비교에서 **내용 비교**(`!=` 리스트 자체)로
   바꿔 정확하게 만들었다.

**Position **값** 쓰기는 round 3/4 에서 이미 완결됐다** — 이 절은 그 위에 timing 을
얹은 것이며, fid 를 다시 움직이지 않았다(cue 데이터 직접 쓰기뿐, 프로그래머 무접촉).

#### Gaps — C6 에서 아직 하지 않은 것

- **보존 여부 미관측.** 속성이 읽힌다는 것은 존재의 증거이고 보존의 증거가 아니다.
  `AXIS_TIMING_OBSERVED`/`RANDOM_ACCESS_OBSERVED` 는 **의도적으로 빈 tuple 그대로** 둔다.
- **pan ≠ tilt 독립성 미확립 — round 5 이후에도 남는다.** `PRESET2FADE`/`PRESET2DELAY` 가
  관측됐지만(round 5) Position 한 preset type 전체에 걸리는 값이라 pan·tilt 를 여전히
  가르지 못한다. `AC-LDPLUGIN-012` 의 "pan/tilt 다른 종료"가 어느 통로로 되는지 미측정.
- **`MIB*` 필드가 이 객체에서 `property not readable`.** dark move 통로가 CuePart 가
  아닌 다른 자리일 수 있다 — 미조사.
- **P1(쓰기·되읽기) 5라운드 시도함 — PRESET2FADE/PRESET2DELAY 관측 성공, INDIVFADE/INDIVDELAY
  는 Set…Property 로는 여전히 무효과 · P2(무대 관측) 미실행.** Position **값** 쓰기
  (fid·Attribute Pan/Tilt·Preset recall)는 완전히 검증됨(round 3/4, fid 501 실제 이동).
  round 1~4 는 전부 프로그래머 경로였고 timing 관측 0건이었다 — round 5(다른 카드 t215의
  `Set Cue N Sequence M Property '<name>' <value>` 문법 재사용)에서 `PRESET2FADE`/
  `PRESET2DELAY` 가 처음으로 관측됐다(위 "Evidence — P1 ④" 참조). `INDIVFADE`/`INDIVDELAY`
  는 같은 형태로 `ok:true` 를 받았지만 값은 그대로였다(같은 경로에서 형제 속성은 바뀌었으므로
  경로 오류가 아니라 진짜 무효과). `INDIVIDUALTIMING` 에 `'On'` 은 `Illegal value`로 거절—
  속성명은 유효했으나 올바른 enum 문자열은 여전히 미확인. 승격(AXIS_TIMING_OBSERVED 채움)은
  pan≠tilt 독립성 문제 때문에 보류했다 — 사람 판단 필요(§E.2 Evidence — P1 ④ 마지막 문단).
- **한 시퀀스의 한 큐의 한 Part 만 봤다.** 전수 아님.
- **독립 감사 없음** (C2~C5 와 동일).
- **이 브랜치는 push 되지 않아 CI 판정을 받지 않았다.**

#### Residual-risk

- `CueTiming` 문자열의 의미(상속)는 이름에서 온 해석이다 — 값을 써서 되읽어야 확정.
- 승격은 `compiler version/build` + `rig fingerprint` 에 고정해야 한다(`plan.md §3`).
  이번 조회는 이 rig·이 show 전용이며 다른 rig 로 옮길 수 없다.
- 세션 중 OSC 슬롯 추가(제가 권한 것)가 돌아가던 앱의 회신 통로를 깨뜨렸다 — 원인
  진단을 세 번 틀린 뒤(3행 Receive Command·바인드 순서·포트 점유) 콘솔 히스토리의
  `Illegal property:SendOSC 2` 로 확정됐다. 「쇼 데이터를 안 건드린다」≠「부작용 없다」.
