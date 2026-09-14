# 인수기준 — SPEC-LDCOMPILE-001

[요구사항](spec.md) · [구현 계획](plan.md) · 우산 계약: [contract.md](../SPEC-LDPLUGIN-001/contract.md)

## 1. 판정 수단과 그 한계

**CI 는 저장소 전체가 과금 차단으로 죽어 있다.** `uv run pytest` 로컬 실행이 유일한 자동
판정 근거다. 기준선 (2026-09-14, HEAD `cde2744`, 이 프로젝트에서 실측):
`12928 passed, 31 skipped`. 회귀 판정은 이 숫자와의 대조다.

**그리고 이 SPEC 은 로컬만으로 닫히지 않는다.** 아래 7건 중 셋(008·012·013)은 **실기 콘솔
또는 인증 onPC+rig 관측**을 PASS 조건에 포함한다. 그 항목의 로컬 부분만 초록으로 만들고
AC 를 닫으면, 실측되지 않은 표현이 지원으로 광고된다 — `LD-CAP-001` 이 정확히 그것을 막는다.

**증거 규율**: 각 기준의 PASS 는 그 기준의 검증 명령을 **실제로 돌려서 본 출력**으로만
주장한다. 명령을 안 돌린 항목은 PASS 가 아니라 **Gap** 으로 적는다. 실패 신호가 없다는 것은
통과의 증거가 아니다.

**대조군 규율**: 이 SPEC 의 시험 대부분이 "거부하는가" 를 잰다. **전부 거부하는 검증기는 그
시험을 모두 통과한다.** 따라서 모든 거부 시험에는 통과해야 하는 양성 대조가 짝으로 있어야
하고, 짝이 없는 거부 시험은 공허하다. 각 절에 대조를 명시했다.

## 2. 기준 — REQ 와 1:1

id 는 우산에서 승계한다 (`../SPEC-LDPLUGIN-001/spec.md:45`).

| AC | REQ | 종류 | 콘솔 | 기준 |
|---|---|---|---|---|
| AC-LDPLUGIN-008 | 008 | D+C | **예** | **Given** 모든 §7 op·독립 timing·FX cycle/phase·accent return·release 를 쓰는 plan, **When** compile/apply, **Then** 요청 leaf 가 실제 artifact 와 target 에 보존된다. raw 문자열·silent clamp·drop·substitution 은 거부. 표현 범위별 trace matrix. |
| AC-LDPLUGIN-009 | 009 | D+C | 부분 | **Given** manual_go/trig_time·준비 cue·tempo change·동일 ms·반올림 경계, **When** lowering, **Then** 원음 t0·최종 cue delta·cycle 분할이 계약과 일치한다. 첫 GO 는 사람이 수행하고 apply 가 시작하지 않는다. timecode mode·음수 준비·불가능 해상도는 차단. |
| AC-LDPLUGIN-010 | 010 | D+C | 부분 | **Given** 누락 baseline/stop/terminal 또는 released 이후 부분 재진입, **When** validation, **Then** blocking. 완전 baseline→hold→stop→safe release plan 은 simulation terminal 과 일치하며 실제 clean baseline 관측 없이 ready 불가. |
| AC-LDPLUGIN-011 | 011 | D | 아니오 | **Given** 겹친 group 의 동일 fixture×axis, FX affects_axes·delay/fade 겹침, **When** 검증, **Then** 동일 값이어도 conflict. transition 끝=다음 시작은 허용하며 배열 순서로 덮어쓰지 않는다. |
| AC-LDPLUGIN-012 | 012 | D+C | **예** | **Given** pan/tilt 다른 종료와 settle, 중간 fade·active FX re-entry, **When** preview/compiler, **Then** blackout 유지·reveal 불변·full state/phase 복원을 관측한다. 불가하면 unsupported; 미지원 random_access 를 true 로 광고하지 않음. |
| AC-LDPLUGIN-013 | 013 | D+C | **예** | **Given** parser 만 지원하거나 timing/stop 메타데이터만 생성하는 compiler, **When** capability 광고/ready 판정, **Then** unsupported+blocking. 구현한 조합에서 plan §3 각 gap 의 실제 emit/target 관측이 있어야 지원으로 승격. |
| AC-LDPLUGIN-014 | 014 | D | 아니오 | **Given** 한 critical 불가 action 과 나머지 정상 action, **When** validation, **Then** 전체 blocked/compiled.available=false·write 0 이며 모든 action 및 변경/누락 leaf 에 진단이 있다. advisory 는 hard limit 을 완화하지 않음. |

종류 표기는 우산 `acceptance.md` 와 같다 — S=schema/static, D=결정적(합성 입력),
C=콘솔/onPC 관측, H=사람 확인. 「콘솔=부분」은 계산부는 로컬, fidelity 부는 관측이 필요하다는
뜻이다.

## 3. 기준별 검증 명령

### AC-LDPLUGIN-014 — 검증 순서와 진단 (뿌리)

```bash
uv run pytest server/tests/test_director_validate_pipeline.py -q
```

**PASS 조건**:

1. 검사 순서가 `LD-VAL-001` 의 6단(source identity → time/reference → tracking/FX →
   capability/fidelity → safety → approval freshness)과 같다. **순서를 단언한다** — 통과
   여부만 보면 순서가 뒤바뀐 구현도 초록이다.
2. 요청 action N 개에 진단이 **최소 N 개**. 개수를 세고, 전체 action 수와 나란히 적는다.
3. critical blocking 하나 + 나머지 정상 → `outcome == "blocked"` **그리고**
   `compiled == {"available": false}` **그리고** 정상 action 에도 진단이 있다.
4. 조용한 수용이 `before/after` 둘 다 `present=false` + 사유로 표현된다.
   `present=true` 면 `value` 가 반드시 있고 `false` 면 없어야 한다.
5. pointer 가 **submitted plan root** 기준이며 `""` 가 전체 plan 이다. `~` 와 `/` 를 담은
   key 가 `~0` `~1` 로 escape 된다.
6. `advisory` 진단은 `blocking=false` 이고, advisory 만 있으면 `outcome` 이 blocked 가 아니다.

**양성 대조 (필수)**: 계약 §11 의 `examples/validation.json` 을 우리 출력과 대조하고,
`server.director.models.parse_exchange` 로 왕복시켜 스키마를 통과시킨다. 이 대조가 없으면
"전부 blocked 를 답하는 검증기" 가 위 1~6 을 모두 통과한다.

**음성 대조 (필수)**: advisory 만 있는 plan 은 `blocked` 가 **아니어야** 한다.

### AC-LDPLUGIN-009 — 시간 해석

```bash
uv run pytest server/tests/test_director_validate_timing.py -q
```

**로컬 PASS 조건** (계산부):

| 검사 | 기대 |
|---|---|
| 원점 | 업로드 audio 첫 sample = 0ms, 중간 trim/offset 없음 |
| 전곡 분할 | context sections 가 `[0,duration)` 를 겹침·공백 없이 덮는다 |
| cue 경계 | 자기 section 의 `start <= at < end`, 첫 cue = 0 |
| 동일 시각 | 같은 ms 는 **단일 semantic cue** 로 묶인다. array 뒤 action 이 앞 conflict 를 덮지 않는다 |
| beat 연속성 | `beat(t)=start_beat+(t-start_ms)*bpm/60000`, 인접 segment 경계에서 값이 연속 |
| 반올림 | 최종 ms 는 가장 가까운 integer, **정확한 .5 는 +방향**. 반올림으로 충돌이 생기면 거부 |
| tempo 교차 | FX 한 instance 의 active 구간이 다른 bpm segment 를 가로지르면 분할 아니면 `unsupported` |
| trig_time delta | 첫 bundle 만 `manual_go`/`relative_ms=0`. 이후 `relative_ms = at_ms − 직전 최종 bundle at_ms`. **준비 cue 도 최종 순서와 delta 계산에 포함** |
| manual_go | 모든 저장 큐가 수동 GO. `at_ms` 는 음악 참조일 뿐 |
| timecode | `timecode` mode·offset·arm 요청은 **거부**. 변환해서 흉내내지 않는다 |
| 기본 BPM | tempo 불명에 120 을 대입하지 않는다 — `unsupported` |
| 음수 준비 | **`spec.md` §6.3 의 판정 전까지 이 항목은 판정하지 않는다** (계약은 금지, 코드는 PRE-ROLL 경로 보유) |

**양성 대조 (필수)**: 계약 §11 의 정상 plan 예제가 통과하고, 그 예제의 cue 시각·delta 가
계약이 적은 값과 같다.

**콘솔 PASS 조건**: first/last cue·accent·준비 cue 를 포함한 재생 시간표를 onPC 에서 대조
(우산 `plan.md` §3). **미측정 상태로 이 AC 를 닫지 않는다.**

### AC-LDPLUGIN-010 — ready 판정

```bash
uv run pytest server/tests/test_director_validate_ready.py -q
```

**PASS 조건**:

1. 누락 action/axis 는 **hold** 다. 이전 show·programmer 값을 상속하면 FAIL.
2. 첫 cue 가 controlled group **전부**의 intensity/color/position/beam baseline 을 완전히
   지정하지 않으면 blocking. active FX 없음이 target 에서 확인되어야 한다.
3. stop 없는 FX / 시작 전 stop / 중복 start·stop / group mismatch 는 blocking
   (`LD-FX-001`). `instance_id` 는 plan 전체에서 한 start 와 한 stop 에 1:1.
4. `active_fx` 의 terminal 값은 **항상 빈 배열**.
5. `terminal_state` 가 축별 simulation 결과와 **정확히 일치**. 모든 controlled group 에
   정확히 하나.
6. 첫 release 이후 재사용은 완전한 baseline 선언을 요구한다.

**음성 대조 (필수 · 예술 정책 주입 탐지)**: 아래 셋은 **통과해야 한다.**
- 조용한 엔딩(outro intensity 가 낮음) — `role=outro` 를 이유로 올리면 FAIL
- 두 후렴의 강도가 동일 — 변주를 강제하면 FAIL
- 반복 motif — 반복 자체를 결함으로 보면 FAIL

이 셋이 빨간 것은 검증기가 정확한 것이 아니라 **예술 정책을 주입한 것**이다
(`LD-STATE-002` 가 유효하다고 명시했다).

**콘솔 PASS 조건**: 실제 clean baseline 관측 없이 ready 로 올리지 않는다.

### AC-LDPLUGIN-011 — 충돌 검출

```bash
uv run pytest server/tests/test_director_validate_conflict.py -q
```

**PASS 조건**:

1. fixture 별 attribute 를 **실제 group membership 으로 확장**해서 본다. group 단위로
   뭉치면 겹친 group 의 충돌이 안 보인다.
2. 같은 fixture×axis 의 겹치는 fade/delay transition 은 **동일 값이어도 conflict**.
3. 한 instant 의 중복 쓰기는 conflict.
4. FX `affects_axes` 와 static/다른 FX 의 겹침은 conflict.
5. `transition 끝 == 다음 시작` 은 **허용**.
6. FX stop fade 가 끝난 뒤에만 그 축을 다시 쓸 수 있다.
7. `delay` 구간도 예약 구간이다 — 다른 변경이 시작값을 바꾸지 못한다.
8. 배열 순서로 앞 충돌을 덮어쓰지 않는다.

**양성 대조 (필수)**: 겹치지 않는 두 group 의 동시 변경은 통과한다. 5·7 이 그 자체로 대조다.

**계기 주의**: 충돌 개수를 셀 때 `|A|−|B|` 를 `A\B` 로 읽지 않는다 — 개수 차는 방향이 둘이고
한쪽만 보면 반대 방향 누락이 부재로 숨는다.

### AC-LDPLUGIN-008 — 표현 보존 (콘솔 게이트)

```bash
uv run pytest server/tests/test_director_validate_capability.py -q   # 거부부만
```

**로컬 PASS 조건** (거부):

1. 임의 MA/Lua/OSC command string·임의 query·임의 channel address 는 거부.
2. **silent clamp 금지** — `value_pct` 가 정책 상한을 넘으면 clamp 가 아니라 진단이다.
3. **silent quantize 금지** — emitter 최소 해상도로 정확히 재현할 수 없으면 `unsupported`.
4. **대체 preset 금지** — 호환되지 않는 preset 을 비슷한 것으로 바꾸지 않는다.
5. **필드 제거 금지** — 지원하지 않는 구성의 일부만 버리지 않는다 (`beam_set` 전체 구성).
6. 7개 op 각각에 대해 위 다섯이 시험된다. **op 표가 7건 전부를 덮는지 단언한다** — 표가
   새면 그 op 은 시험되지 않는다.

**콘솔 PASS 조건**: 표현 범위별 **trace matrix** — 요청 leaf → emitted field 대응을 실제
artifact/target 에서 관측하고, silent drop/substitute 0건임을 보인다.

[HARD] **로컬 거부 시험만 초록으로 만들고 이 AC 를 닫지 않는다.** 거부는 절반이며, 나머지
절반(보존)은 관측이다. 현재 축별 timing emitter 는 **0건**이므로(`spec.md` §6.1) 착수
시점의 정직한 상태는 「거부 초록 + 보존 미측정」이다.

### AC-LDPLUGIN-012 — dark move·re-entry (콘솔 게이트)

```bash
uv run pytest server/tests/test_director_validate_mib.py -q   # 거부부만
```

**로컬 PASS 조건**: 증명할 수 없으면 `blocking`. `random_access` 를 미지원인데 `true` 로
광고하면 FAIL. authored reveal 시각을 미뤄서 맞추면 FAIL. compiler 준비 동작에 음수 ms 를
쓰면 FAIL(단 `spec.md` §6.3 판정 대기).

**콘솔 PASS 조건**: movement 시작부터 pan/tilt 의 늦은 완료 + `settle_ms` 까지 **intensity=0
및 intensity FX 없음**을 관측. 중간 fade 의 현재 값·잔여 duration·beat 위치가 재현되는지 관측.

### AC-LDPLUGIN-013 — capability 승격 (콘솔 게이트)

```bash
uv run pytest server/tests/test_director_validate_capability.py -q
```

**로컬 PASS 조건**: parser 만 지원하거나 메타데이터만 만드는 compiler 조합에서
`unsupported + blocking` 을 답한다.

**콘솔 PASS 조건 (승격의 유일한 근거)**: 우산 `plan.md` §3 표의 각 gap 에 대해 실제
emit/target 관측이 있어야 그 항목을 지원으로 올린다. 승격은 `compiler version/build` +
`rig/content fingerprint` 에 고정한다.

**착수 시점 실측 (2026-09-14, `cde2744`, `server/` 아래 `.py` 601개. 계기 확인: 양성 대조
`CueFade` 87건 · `Property 'Fade'` 3건)**:

| 후보 emitter | 건수 | 의미 |
|---|---|---|
| `PanFade`·`TiltFade`·`ColorFade`·`BeamFade` | 각 **0** | 축별 fade 통로 없음 |
| `IndividualFade`·`AttributeFade`·`IndividualTime` | 각 **0** | 개별 시간 통로 없음 |
| `delay_ms` (`.py`) | **0** | 축별 delay 개념 없음 |
| `CueFade` | **87** | 큐 단위 **스칼라 하나** — 축을 구분 못 함 |
| `Property 'Fade'` | 3 (전부 **금지** 근거 주석) | 이 경로는 막혀 있다 |

따라서 착수 시점의 정직한 capability 는 **축별 timing 전부 unsupported** 다. 이것을
「미구현이니 나중에」로 적지 않고 AC 의 초기 상태로 적는다 — 그래야 승격이 관측 없이
일어나지 않는다.

## 4. 경계 기준 (모든 마일스톤 공통)

```bash
# 이 층은 OSC 를 만지지 않는다 — 주석이 아니라 실제 import 를 본다
grep -rnE "^\s*(from|import)\s+server\.bridge" server/director/ && echo "FAIL" || echo "PASS"

# 이 층은 예술 producer 를 호출하지 않는다
grep -rnE "^\s*(from|import)\s+server\.(looks|web)" server/director/ && echo "FAIL" || echo "PASS"

# PRESERVE — 기존 LXSEQ/design 경로를 수정하지 않았다
git diff --name-only origin/main -- server/lxseq server/design | grep . && echo "FAIL" || echo "PASS"

# 형제 저장층을 수정하지 않았다 (seam 에 꽂을 뿐)
git diff --name-only origin/main -- server/director/models.py server/director/store.py \
  server/director/service.py server/director/digest.py | grep . && echo "FAIL" || echo "PASS"

# 회귀
uv run pytest -q
```

## 5. 이 SPEC 을 닫을 수 없는 조건 (명시)

아래가 남아 있으면 SPEC 은 `implemented` 가 아니다. 로컬 초록만으로 닫는 것을 막기 위해
적는다.

1. **실기 콘솔(또는 인증 onPC+rig) 관측 0회** — AC-008·012·013 의 콘솔 조건.
2. **`spec.md` §6.3(음수 ms) 판정 미완** — 계약과 코드가 다른 상태로 C2 를 확정할 수 없다.
3. **C6 프로브가 축별 timing 문법을 못 찾은 상태** — 그 경우 계약 §7 의 축별 독립 timing 이
   이 하드웨어 조합에서 영구 `unsupported` 이며, 우산 `spec.md:41`(첫 릴리스 표현 범위)에
   대한 판정이 필요하다. 자식이 조용히 축소할 수 없다.
4. **독립 판정 없음** — `plan-auditor` 는 이 저장소에서 착수 전 컨텍스트 초과로 죽는다
   (실측 적재 ≈114K 토큰). 이 문서의 품질 판단은 전부 orchestrator 자기 검수이며 그것은
   독립 감사보다 약하다.
