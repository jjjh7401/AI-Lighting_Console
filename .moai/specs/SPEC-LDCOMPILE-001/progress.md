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
