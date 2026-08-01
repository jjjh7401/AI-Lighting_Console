# SPEC-COPILOT-SCENE-001 — Plan-Phase Research

> **근거 등급**: `[코드]`(리포지토리 소스 직접 판독) · `[문서]`(룰북·SPEC 산문 — **룰북의 "validated live" 선언 포함**) · `[실측]`(라이브 콘솔 직접 관측만 — **본 plan-phase에는 0건**, 선행 SPEC 전재는 원출처 표기) · `[미확정]`(어느 것도 아님 → ASSUMPTION).
>
> 조사 방법: 코디네이터 직접 판독(전수 grep · 소스 직접 읽기 · 선행 SPEC 아티팩트 대조 · baseline 직접 실행). 줄 앵커는 2026-08-01 `main`=`e4bc78e` 기준 실측이며 **각 마일스톤 착수 직전 재실측**한다.
>
> ---
>
> ⚠️ **v0.2.0 개정 고지 (2026-08-01) — 본 문서는 plan-phase 조사 기록이며 개정 후에도 그대로 보존된다.** 그러나 **§2가 조사한 `/CueOnly` 정책은 M0 라이브 프로브 이후 폐기됐다.** §2의 조사 결론(*"발화 이력 0건이므로 접수를 실측해야 한다"*)은 **옳았고 실제로 M0 1순위가 됐으며**, 그 프로브가 정책을 무너뜨렸다 — 미지 store 플래그가 조용히 접수되어 접수 판정의 기계 채널이 소진됐고, 큐 생성이 실질 append-only라 `/CueOnly`의 보정 대상이 존재할 수 없음이 드러났다. **§2는 "왜 그 조사가 필요했는가"의 기록으로 읽고, 현행 정책은 `design.md §6`(균일 집합 + 미주장 열거)을 볼 것.** 판정 정본 `progress.md §E.2` · 개정 근거 조사 `.moai/reports/scene-uniform-attribute-set-proposal.md`(**gitignore — 저장소에 없다**). §5(SONGCUE 상속 부채)는 **범위가 축소**됐다 — 씬도 무플래그가 되어 플래그 정책 분기가 사라졌고, 남는 대비는 균일 집합 축뿐이다(design.md §6.4).
>
> **정정 (sync-phase, 2026-08-01 — 독립 감사 지적).** 이 고지의 이전 판본은 *"§3·§4·§6은 개정 영향 없음"* 으로 닫았는데 **§3은 영향이 있다.** `§3.1`이 *"씬은 fx의 Store를 재사용할 수 없다 — 임의 큐 번호 불가 **+ `/CueOnly` 부재**"* 라 적고 `§11` 기각 (b)가 같은 논거를 반복하는데, **씬도 D1 개정으로 무플래그가 됐으므로 `/CueOnly` 부재는 더 이상 fx와 씬을 가르는 축이 아니다.** `design.md §5`와 `plan.md` 결정 I는 이 약화를 명시 정정했고 **research.md만 정정도 승계 포인터도 없었다** — 게다가 이 고지가 그 절을 "영향 없음"으로 배제해 독자가 확인할 유인마저 없앴다. **본문 §3.1·§11은 조사 스냅샷이라 고쳐 쓰지 않는다**; 현행 판단은 `design.md §5` · `plan.md` 결정 I가 정본이며, **결정 I의 살아 있는 논거는 "`/CueOnly` 부재"가 아니라 "fx 번들에 룩 값 라인을 끼울 자리가 없다"** 이다. §4·§6은 영향 없음이 맞다.

## §1. 출처 — 발명이 아니라 예약된 좌석의 이행

`SPEC-COPILOT-FXLIB-001/spec.md` 전수 판독 결과, FXLIB은 **세 곳에서 명시적으로** 씬 컴파일러를 후속 소유자로 지목한다. `[문서]`

| 앵커 | 문맥 | 인용 |
|---|---|---|
| `:42` | 사용자 확정 ② (저장 형태) | "프리셋 저장은 명시적 비목표다 … 그 축은 **씬 컴파일러 후속 SPEC의 몫이다**(§D)." |
| `:70` | REQ-FXLIB-001 (스키마 정의) | "**후속 소비자(씬 컴파일러·큐리스트 이펙트 축)가 소비 가능한 형상이어야 한다.**" |
| `:140` | §D 제외 범위 — 프리셋 저장 형태 | "**이 축은 씬 컴파일러 후속 SPEC의 몫이다.**" |

`:70`이 가장 구속력이 크다 — FXLIB 스키마가 **본 SPEC의 소비를 전제로 설계됐다**는 선언이므로, 씬 컴파일러는 상류 계약의 **이행자**이지 사후 개조자가 아니다. 이는 결정 D(상류 비공개 함수 읽기 import)의 정당성 근거이기도 하다: 상류가 소비를 의도했다.

**제안서 대조**: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md`에 씬 합성 항목은 없다. 비제안서 출처 선례는 OVERLAP(1번째)·FXLIB(2번째)이고 본 SPEC이 **3번째**다. `[문서]`

## §2. 조사 ① — `/CueOnly` 전수 grep (본 SPEC에서 가장 중요한 실측)

2026-08-01 코디네이터 직접 실행. **명령과 원문 출력**:

```
$ grep -rn "CueOnly\|Block Sequence\|Unblock" server/ ui/src/ console/
server/rulebook/assets/v2.4.2/31_choreography_patterns.md:59:  of an existing cue, `/CueOnly` stops the change tracking into the next cue.
server/rulebook/assets/v2.4.2/31_choreography_patterns.md:132:To keep a change from tracking into the next cue, store it `/CueOnly`. To freeze a cue's
server/rulebook/assets/v2.4.2/31_choreography_patterns.md:133:values against edits to earlier cues, `Block Sequence 11 Cue 5`; `Unblock` removes
```

**판독**: 세 토큰 모두 **코드 발화 0건**이다. 유일한 출현이 룰북 **산문 2곳**(`:59` 플래그 목록, `:132-133` 트래킹 모델 절)이며, `server/**` · `ui/src/**` · `console/**` 어디에도 이 플래그를 **발화하는** 코드가 없다. `[코드]`

**귀결 3건**:

1. **`/CueOnly`는 이 SPEC이 처음 쏘는 커맨드다.** 근거 등급이 `[문서]`뿐이므로 `[실측]`을 주장할 수 없다 → **ASSUMPTION-41**(접수)이 M0 1순위가 되고, 그 판정 없이는 M4 번들 형상을 저작할 수 없다.
2. **`Block Sequence` / `Unblock`도 미사용이다.** 트래킹 제어의 **어떤 축도** 이 저장소에서 행사된 적이 없다 — 즉 D1은 저장소에 처음 도입되는 정책 축이다.
3. **트래킹 모델 자체는 룰북이 명시한다**(`:130-134`): *"MA3 is a TRACKING console: a value stored in a cue tracks FORWARD into every later cue until it is changed, blocked, or released — `ClearAll` between looks does NOT stop this."* 이 문장이 D1의 동기이자, §5 상속 부채의 근거다.

## §3. 조사 ② — 기존 코드 슬롯 (씬은 그린필드가 아니다)

### §3.1 fx가 남긴 것 — 소비 가능한 표면과 소비 불가능한 표면

| 항목 | 앵커 | 씬에 대한 함의 |
|---|---|---|
| `MIN_STEPS = 2` + `@MX:ANCHOR` | `server/fx/schema.py:66` | 페이저는 2스텝 이상 필요. `@MX:REASON`이 이유를 적는다: *"`Relative`/`Phase`/`Speed` MODIFY an existing phaser rather than create one"* → **결합 순서의 강제 근거** |
| `Step 1` 미발화 | `server/fx/instantiate.py:326-342` `_step_lines` 독스트링: *"`Step 1` is never emitted — the first step is the current one"* | **스텝 1 = 현재 프로그래머 상태 = 룩의 자리** → D2 "룩 먼저"가 강제됨 |
| `_CUE_NUMBER = 1` (상수 고정) | `server/fx/instantiate.py:96`, Store 라인 `:481` | **씬은 fx의 Store를 재사용할 수 없다** — 임의 큐 번호 불가 + `/CueOnly` 부재. 씬은 자기 조립기를 갖는다(결정 I) |
| `is_programmer_state` — **공개** | `server/fx/instantiate.py:144`, `__all__` `:61` | **면제 집합 사본을 만들 필요가 없다** → 결정 E. fx가 `:113-129` `@MX:ANCHOR`로 진 동치 의무를 씬은 상속하지 않는다 |
| `collided_lines` — **공개** | `server/fx/instantiate.py:537`, `__all__` `:59` | 2차 가드 재사용 가능(결정 G). 독스트링이 경계를 정확히 적는다: *"a second instantiation in one turn folds from `Step 2` onward — that line is common to every pattern"* |
| `select_sequence_number` — **공개, `requested=` 지원** | `server/fx/instantiate.py:218` | 씬이 소비. 점유 번호 거부 + `truncated` 거부가 이미 구현돼 있다 |
| `_step_lines` / `_phase_lines` / `_speed_line` / `_matricks` — **비공개** | `:326` / `:345` / `:411` / `:424` | 씬이 값 라인 생성에 소비. 비공개 결합의 대가는 §4.3에서 다룬다 |
| `_guard_collision` = **raise** | `server/fx/instantiate.py:432` | 1차 가드 정책 선례 1 — 독스트링: *"It refuses rather than skips because an fx bundle is ONE store; there is no surviving remainder to report."* |

### §3.2 looks가 남긴 것

| 항목 | 앵커 | 씬에 대한 함의 |
|---|---|---|
| `_values_line` — **비공개**, 그러나 2곳에서 이미 크로스 import | `server/looks/instantiate.py:286`; 소비처 `busking.py:30`, `songcue.py:11` | 룩 값 라인의 단일 출처. **비공개 import의 저장소 선례가 확립돼 있다** → 결정 D |
| 비공개 import의 명시 논거 | `server/looks/busking.py:30` 주석 "dedupe가 비교하는 문자열의 단일 출처" + `:250-251` "**여기서 다시 조립하면 두 곳이 갈라진다**" | 씬이 같은 계산을 그대로 승계 |
| `_guard_collision` = **skip** | `server/looks/busking.py:240` | 1차 가드 정책 선례 2. skip 이유(`:248-249`): *"룩 하나의 저작 결함으로 장르 전량을 실패시키면 버스킹 준비가 아무 산출도 내지 못한다"* → **씬에는 "전량"이 없으므로 논거 미적용** |
| `emitted` 원장 = **skip + 구멍** | `server/looks/songcue.py:436` + 원장 `:243` | 1차 가드 정책 선례 3. 다중 큐 산출물 전제 → 씬(단일 큐)에 미적용 |
| **2차 가드 대응물 없음** | `server/looks/**` 전수 — `collided_lines` 동형 0건 | **비대칭 실증**: 지시 턴 경계 가드는 fx에만 존재한다 |
| 시퀀스 라벨 위치 | `server/looks/songcue.py:258-266`, `_first_store_index:520` | 첫 Store **직후**에 `Label Sequence` 삽입 |
| 트리거 PROPERTY 형태 | `server/looks/songcue.py:488-499` `_auto_advance_commands` | `Set Cue <c> Sequence <s> Property 'TrigType'` + `'TrigTime'` 2줄. **`ClearAll` 뒤 별도 생성** — 캡처 사이클 밖 |
| `select_sequence_number` 2번째 판 | `server/looks/songcue.py:286` | `requested=` 없음. 씬은 fx 판을 쓴다(결정 H) — **세 번째 판을 만들지 않는다** |
| 3주장 분리 상수 선례 | `server/looks/songcue_report.py:15` `PROPERTY_UNOBSERVED_NOTE` | 리포트가 판독 가능/불가 경로를 분리 서술하는 구현 형상 |

### §3.3 tools.py — 툴 핸들러의 형상

> **승계 포인터 (sync-phase 감사 지적 — 2026-08-01)**: 본 절의 `tools.py` 줄 앵커는 **plan-phase 스냅샷**(`main`=`e4bc78e`)이며 **지금은 전부 썩었다** — 이 SPEC이 M6에서 `tools.py`에 툴 2종을 등재하며 뒤쪽 전부가 밀려났다(+19 ~ +34행). **본문은 조사 기록이라 고쳐 쓰지 않는다.** 현행 좌표가 필요하면 **각 줄이 함께 적고 있는 심볼명**(`_PROGRAMMER_STATE_COMMANDS` · `run_commands` · `instantiate_look` · `prepare_songcue` · `instantiate_fx`)으로 찾아라 — 그것이 썩지 않는 앵커다. PRESERVE 구역 지정의 정본은 `plan.md §A.5`이며 그쪽은 심볼 앵커로 교체됐다.
- **dedupe 판정 + 축적 경계**: `server/orchestrator/tools.py:688-712`. 판정 라인 `:699` (`command in already_executed and not _is_programmer_state(command)`) + 주석 원문 `:700-703`: *"either **in a prior tool call** (context.executed_ok) or earlier in **THIS bundle**"*. 비교 집합은 `ExecutionContext.executed_ok`(`:252-256`)로 **지시 턴 전체에 걸쳐 축적**된다. `[코드]`
- **면제 3종**: `_PROGRAMMER_STATE_COMMANDS` `:327-331` — `Clear` / `ClearAll` / bare `(?:Fixture|Group)\s+<operand>`(fullmatch, 대소문자 무관). `[코드]`
- **툴 핸들러 = `run_commands`의 caller**: `run_commands` 클로저 `:638`; `@MX:ANCHOR` 3곳이 같은 규율을 적는다 — `instantiate_look` `:848-858`, `prepare_songcue` `:1116`, `instantiate_fx` `:1688-1698`. 공통 문면: *"This handler is a CALLER of run_commands, never a second execution surface … Reaching execution_port directly from here would be the second path the SPEC forbids, and it would be invisible to the gate."* → 씬 핸들러가 계승할 형상. `[코드]`

## §4. 조사 ③ — 가드 3선례 비교 (씬이 선택해야 했던 지점)

정책이 **갈려 있다**. 이것은 씬이 상속만으로 결정할 수 없고 **선택**해야 했던 유일한 축이다.

| 선례 | 위치 | 범위 | 위반 시 | 산출물 형태 |
|---|---|---|---|---|
| fx | `server/fx/instantiate.py:432` | 이 번들 | **raise** `FxInstantiationError(VALUE_LINE_COLLISION)` | **단일 Store** |
| busking | `server/looks/busking.py:240` | 이 번들 | **skip**(빈 계획 + 사유) | 다중 프리셋 |
| songcue | `server/looks/songcue.py:436` + `emitted:243` | 번들 전체 | **skip** → 큐리스트 구멍(명시 수용) | 다중 큐 |

**판정: 씬은 fx를 따른다.** 결정적 변수는 **산출물 형태**다 — 씬 번들은 정확히 하나의 Store이므로 fx의 독스트링 논거(*"there is no surviving remainder to report"*)가 그대로 성립하고, busking/songcue의 skip 논거(부분 산출이 남는다)는 성립하지 않는다. `[코드]` → design.md §4.1.

**추가 관측**: 씬 번들은 **룩 값 라인 + fx 스텝 값 라인**을 함께 담으므로 비면제 라인 수가 fx 단독 번들보다 크다 → **충돌 표면이 넓고 가드 등급이 높다**.

## §5. 조사 ④ — 상속된 부채: SONGCUE는 오늘 무플래그로 쓴다

`server/looks/songcue.py:462-466` Store 라인 판독:

```python
f"Store Sequence {sequence_number} Cue {cue_number} '{cue_name}'",
```

**플래그가 없다.** 그리고 SONGCUE는 이 저장소의 **유일한 다중 큐 작성자**다(fx는 `Cue 1` 단일, looks는 프리셋). 룰북 트래킹 모델(`:130-134`)과 결합하면: **SONGCUE가 만든 큐리스트의 값은 오늘 앞으로 트래킹되고 있다.** `[코드]` + `[문서]`

**대조 조사**: SONGCUE spec/plan/acceptance 전수에서 트래킹 정책 결정·단언·측정이 **0건**이다. 즉 이것은 의도적 선택의 기록이 아니라 **결정되지 않은 채 남은 축**이다 — 그래서 "잠재 부채"다.

**본 SPEC의 처분**: 기록하되 고치지 않는다(결정 J). `server/looks/**`는 PRESERVE이고, 소급 정책 변경은 별도 SPEC의 결정이다. 기록의 목적은 후속 소유자가 "왜 씬과 SONGCUE의 정책이 다른가"를 재발견하느라 시간을 쓰지 않게 하는 것이다. → design.md §6.1, spec.md §D.

**정직 표기**: 이것을 "결함"으로 부르지 않는다. 트래킹은 MA3의 **정상 동작**이고, SONGCUE의 큐리스트가 트래킹되는 것이 잘못이라는 **측정 근거는 없다** — 곡 진행에서 값이 이어지는 것이 오히려 의도일 수 있다. 확인된 사실은 *"결정 기록이 없다"* 뿐이며, 그 이상을 주장하지 않는다.

## §6. 조사 ⑤ — 검증 천장 (인수 설계를 지배하는 사실)

| 항목 | 기계 검증 | 근거 |
|---|---|---|
| 큐 **존재** / 이름 / 실제 `cueNo` | **YES** | `state` 재조회 — SONGCUE가 라이브로 사용(`SPEC-COPILOT-SONGCUE-001/progress.md:337-344` 표의 `childCount` 열) `[실측]` 전재 |
| 시퀀스 이름 / `childCount` | **YES** | 동상 |
| `TrigType` / `TrigTime` | **YES — 단 게이트 우회 직결 경로** | 응답기 `prop` 동사 → `server/safety/console.py:391` `query_property` `[코드]`. 라이브 사용 실증: `SPEC-COPILOT-SONGCUE-001/progress.md:500-502` `[실측]` 전재 |
| `CueFade` | **NO** | `property not readable: CueFade` — 양 경로 모두. `songcue_report.py:15` 상수가 이 사실을 문면화 `[코드]` |
| **큐의 내용(저장된 값)** | **NO** | 반환 경로 부재. FXLIB M0가 측정된 경계로 확정(`FXLIB spec.md:99` — *"큐 트리는 `Cue → Part(childCount 0)`에서 바닥나 내용 있는 큐와 빈 큐가 구별되지 않는다"*) `[실측]` 전재 |
| **효과 / 모션 / 발색** | **NO** | 사람 GUI가 유일. FXLIB `REQ-FXLIB-014 (c)` + `report.py:52` `EFFECT_EVIDENCE_NOTICE` `[코드]` |
| **트래킹 전파** | **NO** | 관측 주체 부재 — `ui/src/components/ExecutionPreviewCard.tsx:61` `[코드]` |

**`Cmd()` OK ≠ 효과 증거**의 라이브 실증: FXLIB M0가 *"스텝 쌍 없이 변형 라인만 발화하면 `ok:true` 전량에 모션 0"* 을 3회 관측했다(`FXLIB spec.md:50`) `[실측]` 전재.

## §7. 조사 ⑥ — Store 플래그 라이브 실측 (D3의 근거)

`SPEC-COPILOT-SONGCUE-001/progress.md:337-344` 표 전재 `[실측]` — 원출처는 SONGCUE M0 라이브 세션:

| 시퀀스 | 발화 | 재조회 childCount | 사용자 큐 | 앞 큐 |
|---|---|---|---|---|
| 101 | `Store … Cue 1 'PROBEA1' CueFade 2` | 3 | 1 | — |
| 101 | `Store … Cue 2 'PROBEA2' CueFade 2 /Merge` | **4** | **2** | **보존** |
| 102 | `Store … Cue 1 'PROBEB1' CueFade 2` | 3 | 1 | — |
| 102 | `Store … Cue 2 'PROBEB2' CueFade 2` (**`/Merge` 없음**) | **4** | **2** | **보존** |
| 102 | `Store … Cue 1 'PROBEB3' CueFade 2` (**기존 큐**, `/Merge` 없음) | 4 (불변) | 2 | **거부 — `Not allowed`** |

SONGCUE의 판정 문장 전재: *"새 큐 번호에는 두 형태 모두 가산이고, **기존 큐 번호에는 플래그 없는 `Store`가 `Not allowed`로 거부되며 쇼파일은 불변**이다 … 실측상 **`/Merge`는 새 큐 번호에 대해 불필요**하다."*

**D3의 도출**: `/Merge`는 새 번호에서 **실익 0**이고, 달면 기존 번호의 `Not allowed` 안전망만 잃는다 — `server/fx/instantiate.py:225`가 *"the LAST line of defence"* 라 부르는 바로 그 안전망이다. `[코드]`

**`/Overwrite` 봉쇄 4곳** (전부 `[코드]` 직접 확인):
- 룰북 `31_choreography_patterns.md:57-58` — DESTRUCTIVE 표시 + 게이트 라우팅
- `server/safety/blacklist.yaml:18` — `- "Store /overwrite"`
- `DESIGN.md:133` — 위험 분류 표
- `server/web/preview.py:80-81, :113` — `store_overwrite` 액션

**대소문자 무관 assert 논거**: `SPEC-COPILOT-BUSKWIZ-001/design.md:209` — 런타임 매칭이 이미 대소문자 무관(`classify.py:71-73`, `:63-65`, `preview.py:100`)이므로 **대소문자 고정 assert는 빌더가 `/overwrite`를 내도 조용히 통과하는 위양성 테스트**다. `[문서]`

## §8. 조사 ⑦ — 트리거 축

- **PROPERTY 형태만 검증됨**: `31_choreography_patterns.md:106-117` — *"Use the PROPERTY form (validated on 2.4.2)"*. 토큰은 Capitalized(`Follow`, not `follow`), 폐쇄 집합은 `Go / Time / Follow / Sound / BPM`. `[문서]`
- **`/trig=` 금지**: 같은 절 `:115-117` — *"Do NOT emit `Assign Cue 1 Sequence 11 /trig=follow` — the `/trig=` option form returns \"Illegal object\" on 2.4.2."* `[문서]`
- **`TrigTime`은 절대 초**: `SPEC-COPILOT-SONGCUE-001/progress.md:502` 라이브 2점 판별 `[실측]` 전재 — Cue 1에 `TrigTime 10`, Cue 2에 `TrigTime 14`를 넣고 readback이 각각 `"10.0"` / `"14.0"`. 상대 지연 해석이었다면 Cue 2는 `"4.0"`으로 관측됐어야 한다. **판정: 시퀀스 시작 기준 절대 시각.**
- **큐 사후 개명 경로 부재**: `Label Cue`를 독립 동사로 쓴 룰북 근거 0건 → 큐 이름은 **Store 시점에 고정**된다(SONGCUE REQ-SONGCUE-008). 씬의 라벨은 Store 리터럴 인라인이 유일 경로다. `[문서]`
- **게이트 참조 종별에 `Cue` 부재**: `server/safety/classify.py:44` — `RECOGNIZED_REFERENCE_TYPES = ("Macro", "Plugin", "Sequence", "Executor")`. `Goto Cue` 류를 열려면 게이트 어휘 확장이 필요하므로 §D 제외. `[코드]`

## §9. 조사 ⑧ — 미검증 축 5건 → ASSUMPTION-41~45

> **이 표는 M0 이전(plan-phase) 조사 스냅샷이다 — 승계됨.** "현 상태" 열은 프로브 발화 전의 근거 등급이며(전부 `[미확정]`), 41~45의 **확정 판정은 `progress.md §E.2`와 `spec.md §C.2`가 정본**이다(41 `CONDITION_NOT_MET`→moot · 42 `INCONCLUSIVE`→moot · **43 `GO`** — v1 범위 = 정수·신규·오름 한정 · 44 `GO` · 45 `GO`). 특히 43 행의 "부분 검증"은 **REQ-SCENE-021의 폐쇄 어휘 밖 표현**이며, 판정 surface에서는 `GO`로 교체됐다 — 이 행은 조사 시점 기록으로 보존한다.

| # | 축 | 현 상태 | 막는 대상 | 판정 소비처 |
|---|---|---|---|---|
| **41** | `/CueOnly` **접수** | **발화 이력 0건**(§2) — 근거는 룰북 산문뿐 | **M4 번들 형상 전체** | M0 1순위. 부정 = **중단** |
| **42** | `/CueOnly`의 **트래킹 차단 효과** | 관측 채널 부재(§6) — **기계로는 영원히 미검증** | **없음** | M0(사람 GUI, A/B 대조). 리포트 문면 정직도만 좌우 |
| **43** | 임의 큐 번호 Store | **부분 검증** — SONGCUE가 `Cue 2` 라이브 성립(§7). 소수 큐만 미검증 | **없음** | v1은 정수 큐만. 소수 큐는 §D 제외 |
| **44** | **룩 값 라인 + fx 스텝 열 결합** | 두 계층 결합 실측 **0건** | **M4 번들 형상 + M2 저작** | M0 2순위. 부정 = 결합 순서 재설계 블로커 |
| **45** | 충돌 승자 관측 | 큐 내용 판독 불가(§6) | **없음** | M0(사람 GUI). 열거는 **정적 계산**이라 관측 무관하게 정확 |

전부 `[미확정]`. **41과 44만이 저작을 막는다** — 42/45는 저작을 막지 않으므로 같은 세션에 배칭한다(FXLIB이 ASSUMPTION-38/39에 적용한 것과 같은 기준: **저작을 막지 않는 측정은 배칭한다**).

**41의 부정 분기가 다른 SPEC과 다른 점**: 통상 부정 실측은 "정직한 축소"(유효한 완료)지만, **41 부정은 중단이다** — D1이 사용자 확정 정책이므로 에이전트가 무플래그 폴백을 골라 진행하는 것은 결정 월권이다(plan.md §A.3 예외).

## §10. 조사 ⑨ — 병렬 웨이브 불변식 이행 가능성

`.moai/reports/handoff/TEMPLATE-병렬웨이브-파이프라인.md:76-81`의 HARD 불변식 6항을 본 SPEC 문맥에서 점검했다. **전부 이행 가능**하며 매핑은 plan.md §F.4가 소유한다(§F.4는 이 **템플릿 6항**에 v0.2.0 개정이 신설한 뮤테이션 재료 규율 1항을 더해 **7항**으로 이행한다 — 개수 차이는 그 신설분이다). 특기 사항 2건:

1. **불변식 3(`/Overwrite` 금지)을 본 SPEC은 `/Merge`까지 확장한다** — 템플릿보다 좁은 어휘를 쓴다.
2. **불변식 4(`Cmd()` OK ≠ 효과 증거)의 본 SPEC 적용은 3주장 분리다** — 템플릿은 "재조회로만 확인"이라 적지만, 씬에서는 재조회로 확인 가능한 것이 **큐의 존재뿐**이므로 효과·트래킹 두 축을 별도로 부정 표기해야 한다.

## §11. 고려하고 기각한 대안

- **기각 (a) — `instantiate_look` → `instantiate_fx` 툴 연쇄**: 한 지시 턴에서 **원리적으로 성립하지 않는다.** dedupe 경계가 지시 턴 전체이므로 2회차가 접힌다(FXLIB `spec.md:146-148` 명문화). 게다가 두 툴은 각자 다른 산출물(프리셋 / `Cue 1` 시퀀스)을 Store하므로 **하나의 큐가 나오지 않는다.** → design.md §2.1.
- **기각 (b) — `build_fx_bundle` 호출 후 Store 라인 치환**: fx Store는 `Cue 1` 고정 + `/CueOnly` 부재라 두 축 모두 씬 정책과 다르다. 문자열 치환은 §3.2가 경계한 재조립보다 나쁘다. → 결정 I.
- **기각 (c) — 씬 전용 값 라인 재구현**: 두 벌이 갈라지고 **갈라짐은 무음**이다(효과가 기계로 확인되지 않으므로). 저장소 선례 2건이 같은 계산으로 비공개 import를 택했다. → 결정 D.
- **기각 (d) — 씬 전용 면제 집합 사본**: `is_programmer_state`가 공개 API이므로 사본이 불필요하고, 사본은 fx가 진 동치 단언 의무를 새로 만든다. → 결정 E.
- **기각 (e) — `server/fx/`에 `cue_number` 파라미터 추가**: PRESERVE 위반. 승인을 구할 실익도 없다 — 씬이 자기 조립기를 갖는 편이 `/CueOnly` 축까지 함께 해결한다.
- **기각 (f) — 큐 편집(기존 큐 수정) 축 포함**: 기존 큐 번호를 건드리므로 `Not allowed` 안전망과 정면 충돌한다. `/Overwrite` 없이는 성립하지 않고 그것은 블랙리스트다. → §D 제외.
- **기각 (g) — SONGCUE를 `/CueOnly`로 소급 수정**: PRESERVE 위반 + 트래킹이 SONGCUE의 의도였을 가능성이 배제되지 않았다(§5). 기록만 한다. → 결정 J.
- **채택 — `server/scene/` 미러 패키지 + 상류 값 라인 소비 + 자기 조립기**: LOOKLIB·FXLIB 형상 검증 완료 선례의 최소 위험 경로이며, 상류가 `:70`에서 소비를 명시 전제했다.

## §12. 측정된 기준선

2026-08-01 코디네이터 직접 실행, `main` = `e4bc78e`(clean):

```
$ uv run pytest server/tests/ -q
3432 passed, 5 skipped, 1 warning in 88.44s (0:01:28)
```

vitest 기준선 223(오케스트레이터 세션 전재). **이 수치는 참고이며, 각 마일스톤의 대조 기준은 착수 직전 직접 실측분이다**(baseline-integrity 원칙 — plan-phase 수치 이월 금지).

## §13. 핵심 참조 파일

spec.md §E 표가 정본(중복 회피). 본 조사가 그 표의 전 행을 직접 판독 또는 원출처 표기로 커버했다.

## §14. 알려진 미결 지점 — 0건

- **clarification 마커 0건** — 사용자 확정 D1~D4가 결정 공간을 닫았고, 남는 미지수는 전부 ASSUMPTION-41~45로 구조화되어 M0가 소비한다.
- **승인 대기 0건** — 어휘·안전·PRESERVE 어느 축도 신규 승인 불요다: `/CueOnly`는 블랙리스트가 아니고(닫힌 블랙리스트 하에서 무보류 통과), `server/safety/**` 변경이 0이며, 게이트 어휘 확장을 요구하는 축(`Goto Cue`)은 §D로 제외했다.
- **열린 결정 0건** — 결정 **A~K**(11건) 전부 해소(plan.md §A.4가 정본. K = 미주장 열거 유니버스 = 상류 상수 `KNOWN_ATTRIBUTES` 읽기 import — v0.2.0 개정에서 신설됐다).
