# t501 M6c — 거부된 4개 페이저를 저작 쪽에서 고친다(리드 결정 C)

SPEC-LDRENDER-001 M6c. 읽기 전용 경계를 지켰다 — 콘솔 쓰기 0건, 실기 접촉
없음(NO CONSOLE CONTACT, 배차서 지시). `real_console.py`/
`probe_readonly.py`/`m6_send_wave_cm.py`/`pool_snapshot.py`/
`save_show_copy.py` 어느 것도 쓰지 않았다.

## 주장 (Claim)

1. M6(`.moai/reports/t501/M6.md`)이 측정한 "Rain 이 필요로 하는 5개 라벨
   중 `Wave CM` 하나만 빌드된다"는 블로커는 **저작 쪽 처방**으로 해소됐다
   — `Fx.compound_step_values` 축 + `pregenerate_phaser_bundle` 의
   충돌-후-재시도. `Drop Slam`/`Breathe Warm`/`Breathe Cool`/`Finale
   Slam` 전부 이제 `build_fx_preset_bundle` 를 통과한다.
2. 리드 결정 ②가 먼저 지시했던 처방(M6b, `run_commands` dedupe +
   `_guard_collision` 의 Step 경계 리셋)은 SPEC-COPILOT-FXLIB-001 결정
   E 와 충돌한다고 판단돼 거절·revert 됐다 — 이 카드는 dedupe/guard 를
   한 글자도 건드리지 않는 **다른 축**이다.
3. `_guard_collision`(`server/fx/instantiate.py`) 자체는 무변경이다(diff
   0바이트) — 바뀐 것은 `_step_lines` 가 스텝의 값 줄을 **텍스트로
   만드는 방식**뿐이다. 진짜로 완전히 동일한 두 스텝은 여전히 거부된다
   (직접 테스트로 확인).
4. `Wave CM` 의 생성 명령은 바이트 동일하다 — 첫 시도(평범한 폼)에서
   성공하므로 재시도 경로를 전혀 타지 않는 구조이기 때문이다.
5. 스텝이 담는 값(채널별 숫자)은 BEFORE(카탈로그 의도)=AFTER(생성된
   명령에서 역파싱) — 4개 라벨 전부, 모든 스텝에서 일치(자동 비교,
   `ALL_STEPS_MATCH=True`).
6. 전체 스위트 14522 passed(베이스라인 M6 14515 대비 +7, 0 제거) · 뮤테이션
   4건 전부 대상만 사망 · 린트/포맷 전부 통과.

## 증거 (Evidence)

### 1. 처방 설계 — `Fx.compound_step_values` + 충돌-후-재시도

`server/fx/schema.py` `Fx` 에 `compound_step_values: bool = False` 추가
(YAML 로더에는 키가 없다 — 생성 시점 전용 파라미터). `server/fx/
instantiate.py` `_step_lines`(페이저 문법의 유일한 생산 지점)가 이 축이
켜졌을 때 한 스텝의 채널 전부를 `;`-체인 한 줄로 묶어 낸다:

```python
def _value_line(value: StepValue) -> str:
    return f"Attribute '{value.attribute}' {verb} {_format_value(value.value)}"

for index, step in enumerate(fx.steps):
    if index:
        lines.append(f"Step {index + 1}")
    if fx.compound_step_values and len(step.values) > 1:
        lines.append(" ; ".join(_value_line(value) for value in step.values))
    else:
        lines.extend(_value_line(value) for value in step.values)
```

`server/design/phaser_pregen.py` `pregenerate_phaser_bundle` 이 이 축을
켜는 유일한 자리다:

```python
fx = fx_for_catalog_label(label)
slot = select_preset_number(presets_section, requested=requested_slot)
try:
    return build_fx_preset_bundle(fx, group=group, preset_pool=preset_pool, preset=slot, label=label)
except FxInstantiationError as error:
    if error.reason != VALUE_LINE_COLLISION:
        raise
    compounded = fx_for_catalog_label(label, compound_step_values=True)
    return build_fx_preset_bundle(compounded, group=group, preset_pool=preset_pool, preset=slot, label=label)
```

**이미 검증된 문법을 재사용했다, 새로 발명하지 않았다**: `;`-체인 자체는
`_timing_lines`(Speed/Width/Measure 축)가 이미 쓰고 있고,
`song_cue_render.py` `_group_color_apply_command`/`_color_apply_command`
도 `Group <n> ; Attribute 'ColorRGB_R' At <r> ; Attribute 'ColorRGB_G'
At <g> ; Attribute 'ColorRGB_B' At <b>` 형태로 같은 문법을 쓴다(라이브
검증된 폼, `server/orchestrator/tools.py` `_SELECTED_VALUE_LINE` 이
Fixture/Group 선택이 앞에 오는 형태를 이미 인식). **"Wave CM" 자신의
Speed 줄이 실기에서 `executed_ok` 를 받은 전문**이 그 문법의 직접 증거다:

```
$ cat .moai/reports/t501/m6_send_run1/result.json
...
{"command": "Attribute 'ColorRGB_R' At Speed 30 ; Attribute 'ColorRGB_G' At Speed 30 ; Attribute 'ColorRGB_B' At Speed 30", "status": "executed_ok", "detail": "OK"}
...
```

### 2. `_guard_collision` 무변경 (직접 diff)

```
$ awk '/^def _guard_collision/{flag=1} flag{print} /^def _guard_collision/{next} flag && /^def / && !/_guard_collision/{exit}' <HEAD버전> > /tmp/g1.txt
$ awk '동일 패턴' <이 카드 버전> > /tmp/g2.txt
$ diff /tmp/g1.txt /tmp/g2.txt
(출력 없음 — 완전 동일)
```

두 가지 모두 직접 테스트로 고정(`server/tests/test_fx_instantiate.py`):

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_fx_instantiate.py -k compound_step_values -v
test_compound_step_values_joins_a_multi_attribute_step_into_one_chained_line PASSED
test_compound_step_values_false_keeps_the_per_attribute_form_and_still_collides PASSED
test_compound_step_values_does_not_touch_a_single_attribute_step PASSED
test_compound_step_values_still_refuses_a_genuinely_identical_step_pair PASSED
```

`test_compound_step_values_still_refuses_a_genuinely_identical_step_pair`
가 "진짜로 완전히 동일한 두 스텝"(색+디머 전부 같음)을 `compound_step_
values=True` 로도 넣어 여전히 `VALUE_LINE_COLLISION` 으로 거부됨을
직접 확인한다 — guard 의 판정 로직이 전혀 바뀌지 않았다는 증명.

### 3. 30종 카탈로그 전수 재측정 — 4개 전부(+ 부수 6개) 빌드됨

```
$ uv run python -c "
from server.design.phaser_pregen import pregenerate_phaser_bundle, presets_section_from_pool_children
from server.design.phaser_catalog import COLOR_PHASER_SEQUENCE, COMBO_PHASER_SEQUENCE, DIMMER_PHASER_SEQUENCE
from server.fx.instantiate import FxInstantiationError
section = presets_section_from_pool_children({})
fail=0
for seq_name, seq in [('COLOR', COLOR_PHASER_SEQUENCE), ('COMBO', COMBO_PHASER_SEQUENCE), ('DIMMER', DIMMER_PHASER_SEQUENCE)]:
    for label, *_ in seq:
        try:
            pregenerate_phaser_bundle(label, presets_section=section, preset_pool=9)
        except FxInstantiationError as e:
            print(seq_name, label, 'STILL REFUSED', e.reason); fail+=1
print('total still refused:', fail, 'of 30')
"
total still refused: 0 of 30
```

**정정**: M6 §3 이 "나머지 넷"이라 적은 목록 중 `Breathe Cool`/`Breathe
Warm` 은 사실 `COMBO_PHASER_SEQUENCE` 가 아니라 `COLOR_PHASER_SEQUENCE`
소속이다(단색 2개만 체이스, 디머 채널 없음 — `phaser_catalog.py` 전수
확인으로 바로잡음). 충돌은 콤보만의 문제가 아니라 두 계열 모두에서
"스텝 사이 적어도 한 채널 값이 우연히 같다"는 같은 근본 원인이 낳은
증상이었다:

```
$ uv run python -c "
from server.design import color_names
for name in ['Warm White','Amber','Cool White','Blue']:
    print(name, color_names.resolve_color_name(name))
"
Warm White (100, 75, 40)
Amber (100, 55, 5)
Cool White (85, 95, 100)
Blue (5, 20, 100)
```

(Warm White/Amber 는 R 만 우연히 100 으로 같음; Cool White/Blue 는 B 만
우연히 100 으로 같음 — 그래서 압축이 전체 스텝을 유일하게 만든다.)

부수 효과로 Rain 이 필요로 하지 않는 10종(색 계열 `Wave WA`/`Pulse RY`/
`Slam RW` + 콤보 계열 `Breathe Amber`/`Breathe Blue`/`Police`/
`Heartbeat`/`Golden Wave`/`Ocean Wave`/`Rainbow Run`)도 같은 메커니즘으로
함께 `WOULD_SEND` 로 전환됐다 — 라벨별 특례가 아니라 계열 전체에 적용
되는 일반 메커니즘이기 때문이다(§Gaps 참조 — 이 라벨들의 실사용 교차
확인은 범위 밖).

### 4. `Wave CM` 바이트 동일 증명 (재시도 경로를 안 타므로 구조적 보장)

```
$ uv run python -c "
from server.design.phaser_pregen import pregenerate_phaser_bundle, presets_section_from_pool_children
section = presets_section_from_pool_children({})
plan = pregenerate_phaser_bundle('Wave CM', presets_section=section, preset_pool=9)
for c in plan.commands: print(' ', c)
"
```

산출 명령이 `.moai/reports/t501/m6_send_run1/result.json` 의 이미 실기
`executed_ok` 를 받은 전문(21줄, `ChangeDestination Root` ~ `ClearAll`)과
완전히 같다 — 채널별 한 줄 폼 그대로, `;`-체인이 전혀 섞이지 않았다
(압축 분기가 ColorRGB_R/G/B 3개 값만 가진 Wave CM 의 스텝에서 전혀
발동하지 않은 이유: 첫 시도에서 이미 `_guard_collision` 을 통과해 재시도
경로 자체가 실행되지 않기 때문 — 가족 전체에 축을 미리 켜는 방식이
아니라 "실패한 라벨만 재시도"라는 순서가 이 보장을 구조적으로 낸다).

### 5. 스텝 값 동치(BEFORE=AFTER) — 4개 라벨 전수, 자동 비교

```
$ uv run python .moai/reports/t501/m6c_step_value_equivalence.py
...
ALL_STEPS_MATCH=True
```

| 라벨 | 스텝 | 채널 | BEFORE | AFTER | 일치 |
|---|---|---|---|---|---|
| Drop Slam | 1 | R/G/B/Dimmer | 100/0/0/100 | 100/0/0/100 | ✓ |
| Drop Slam | 2 | R/G/B/Dimmer | 100/0/0/0 | 100/0/0/0 | ✓ |
| Breathe Warm | 1 | R/G/B | 100/75/40 | 100/75/40 | ✓ |
| Breathe Warm | 2 | R/G/B | 100/55/5 | 100/55/5 | ✓ |
| Breathe Cool | 1 | R/G/B | 85/95/100 | 85/95/100 | ✓ |
| Breathe Cool | 2 | R/G/B | 5/20/100 | 5/20/100 | ✓ |
| Finale Slam | 1 | R/G/B/Dimmer | 100/75/40/100 | 100/75/40/100 | ✓ |
| Finale Slam | 2 | R/G/B/Dimmer | 100/0/0/0 | 100/0/0/0 | ✓ |

(전문: `.moai/reports/t501/m6c_step_value_equivalence.json`.)

### 6. 콘솔 명령 그래머 교차 확인 (Wave CM 의 Speed 줄 — §Gaps 에 한계 명시)

`is_programmer_state`/`_SELECTED_VALUE_LINE`(`server/orchestrator/
tools.py`)이 `Fixture|Group <선택> ; Attribute '<attr>' At <v> ; ...`
형태를 이미 인식하고, `song_cue_render.py` 의 색 송신 경로가 라이브로
이 형태를 쓴다 — 다만 그 형태는 **선택이 앞에 오는** `;`-체인이고, 이
카드가 쓰는 `_step_lines`/`_timing_lines` 의 `;`-체인은 **선택 없이
속성끼리만** 묶인다. 유일한 직접 실기 증거는 Wave CM 자신의 Speed 줄
(§1 인용) — 속성끼리만 묶인 `;`-체인이 **스텝 값 줄**에서도 똑같이
동작하는지는 이 카드가 측정하지 못했다(NO CONSOLE CONTACT, §Gaps).

### 7. 테스트 — 진짜 RED 확인 후 GREEN (구현 3개 파일을 HEAD 로 되돌려 재확인)

구현을 먼저 쓰고 테스트를 나중에 추가했다는 사실을 인지하고, "test-after"
를 바로잡기 위해 **구현 3개 파일(`server/fx/schema.py`/`server/fx/
instantiate.py`/`server/design/phaser_pregen.py`)을 `git show HEAD:<path>`
로 되돌려** 새/갱신 테스트 전부를 과거 코드 기준으로 다시 돌렸다(진짜
RED), 그 뒤 구현 파일을 원래대로 복원(`diff -q` 로 바이트 동일 재확인)해
GREEN 을 다시 관측했다 — 날조 없는 RED→GREEN 전환.

**RED(구현 되돌린 상태, verbatim)**:

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_fx_schema.py server/tests/test_fx_instantiate.py server/tests/test_phaser_pregen.py server/tests/test_phaser_pregen_wiring.py -q
...
FAILED server/tests/test_fx_schema.py::TestCompoundStepValuesAxis::test_the_axis_is_declared_on_the_schema_defaulting_false
FAILED server/tests/test_fx_instantiate.py::test_compound_step_values_joins_a_multi_attribute_step_into_one_chained_line
FAILED server/tests/test_fx_instantiate.py::test_compound_step_values_does_not_touch_a_single_attribute_step
FAILED server/tests/test_fx_instantiate.py::test_compound_step_values_still_refuses_a_genuinely_identical_step_pair
FAILED server/tests/test_phaser_pregen.py::TestPregenerateBundle::test_the_four_previously_refused_labels_now_build_cleanly[Drop Slam]
FAILED server/tests/test_phaser_pregen.py::TestPregenerateBundle::test_the_four_previously_refused_labels_now_build_cleanly[Breathe Cool]
FAILED server/tests/test_phaser_pregen.py::TestPregenerateBundle::test_the_four_previously_refused_labels_now_build_cleanly[Finale Slam]
FAILED server/tests/test_phaser_pregen.py::TestPregenerateBundle::test_the_four_previously_refused_labels_now_build_cleanly[Breathe Warm]
8 failed, 274 passed in 0.79s
```

(나머지 신규 테스트 4개 — `test_the_loader_has_no_key_for_it`·
`test_compound_step_values_false_keeps_the_per_attribute_form_and_still_
collides`·`test_a_genuinely_duplicated_step_is_still_refused_by_the_
unchanged_guard`·`test_wave_cm_is_the_one_needed_label_that_builds_on_
the_first_try` — 는 "기본값/무변경 동작"을 확인하는 테스트라 구현 전
코드에서도 이미 참이었다. 이것은 결함이 아니라 그 테스트들의 설계
의도다: §2 증명처럼 **무변경을 증명하는 테스트는 두 버전 모두에서
참이어야** 한다.)

**GREEN(구현 복원 직후, `diff -q` 로 3개 파일 바이트 동일 재확인 뒤 재실행,
verbatim)**:

```
$ diff -q <백업> server/fx/schema.py && diff -q <백업> server/fx/instantiate.py && diff -q <백업> server/design/phaser_pregen.py
(출력 없음 — 3개 파일 전부 바이트 동일)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_fx_schema.py server/tests/test_fx_instantiate.py server/tests/test_phaser_pregen.py server/tests/test_phaser_pregen_wiring.py -q
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 76%]
..................................................................       [100%]
282 passed in 0.99s
```

RED 274 passed + 8 failed = GREEN 282 passed — 정확히 일치(8개가 RED→
GREEN 으로 전환됐을 뿐, 다른 테스트는 흔들리지 않았다).

### 8. 전체 스위트 + 뮤테이션 + 린트/포맷 (커밋 후 재실행)

```
$ unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14522 passed, 35 skipped, 1 warning in 246.17s
```

베이스라인(M6, `14515 passed, 35 skipped`) 대비 **+7 passed, 0 removed,
skip 변화 0** — 신설 7개(`test_fx_schema.py` +2, `test_fx_instantiate.py`
+4, `test_phaser_pregen.py` 순증 +1[파라미터화 4개 교체(±0) + 신규 1개])
와 정확히 일치.

뮤테이션 4건(각 1축, diff 확인 후 복원, `diff -q` 로 원본 바이트 동일
재확인):

| 뮤테이션 | 대상 | 죽은 테스트 |
|---|---|---|
| `_step_lines` 압축 분기를 `if False and ...` 로 무력화 | `server/fx/instantiate.py` | 6건(압축 단위 테스트 2 + 4개 라벨 파라미터화 4) |
| `pregenerate_phaser_bundle` 재시도 조건 반전(`== VALUE_LINE_COLLISION: raise`) | `server/design/phaser_pregen.py` | 4건(4개 라벨 파라미터화) |
| COLOR 분기만 `compound_step_values=False` 하드코드 | `fx_for_catalog_label` | 2건(Breathe Cool/Breathe Warm 만 — Drop Slam/Finale Slam 은 그린, 분리 확인) |
| COMBO 분기만 `compound_step_values=False` 하드코드 | `fx_for_catalog_label` | 2건(Drop Slam/Finale Slam 만 — Breathe Cool/Breathe Warm 은 그린, 분리 확인) |

4건 전부 적용 후 의도한 테스트만 FAIL(축 분리 확인 — 특히 3·4번째
뮤테이션은 두 계열이 독립적으로 고쳐졌음을 직접 증명한다), `diff -q`
로 복원 뒤 원본과 바이트 동일 재확인 + 해당 테스트 재통과 확인. 생존
뮤턴트 0건.

```
$ uv run ruff check server/design/phaser_pregen.py server/fx/instantiate.py server/fx/schema.py server/tests/test_fx_instantiate.py server/tests/test_fx_schema.py server/tests/test_phaser_pregen.py server/tests/test_phaser_pregen_wiring.py .moai/reports/t501/m6c_pregen_stop_point.py .moai/reports/t501/m6c_step_value_equivalence.py
All checks passed!
$ uv run ruff format --check <동일 9개 파일>
9 files already formatted
```

`make test-fast` 결과는 §Gaps 에 기록(이 저장소에 해당 target 이
존재함을 확인 — 결과는 커밋 후 섹션에서 갱신).

## 기준선 (Baseline-attribution)

- 커밋: `git merge --ff-only origin/WT-ldrender-run` 직후 `git rev-parse
  --short HEAD` → `7099fe0e`(배차서가 지정한 canonical HEAD — M6b 실험
  두 건의 revert 뒤, 트리가 M6 완료 커밋 `947ddba8` 과 동일). 이 보고서의
  모든 측정은 이 HEAD 위에서 M6c 구현을 적용한 이 워크트리에서 직접
  실행한 결과다.
- 전체 스위트 베이스라인(M6, `14515 passed, 35 skipped`)은 M6.md §기준선
  에 이미 기록된 값(이 카드가 재측정한 것이 아니라 직전 보고서 값을 그대로
  인용, 트리 동일성 때문에 그대로 쓸 수 있음) — 이번 M6c 애프터(14522/35)
  는 이 워크트리에서 직접 실행해 관측한 verbatim 출력이다.
- `_guard_collision` 무변경 diff: HEAD(`7099fe0e`)의 `server/fx/
  instantiate.py` 와 이 카드가 수정한 버전에서 함수 본문만 추출해 비교 —
  이 워크트리에서 직접 실행해 관측(0 바이트 차이).
- 30종 카탈로그 전수 재측정·Wave CM 바이트 동일 증명·스텝 값 동치 증명은
  전부 이 워크트리에서 직접 실행한 결과다(새 스크립트 `m6c_pregen_stop_
  point.py`/`m6c_step_value_equivalence.py`, 콘솔 접촉 0건).

## 미검증 (Gaps)

- `;`-체인 압축 폼을 **스텝 값 줄 자체**에 적용해 실기로 보내는 교차
  확인 — NO CONSOLE CONTACT 제약(배차서)으로 이 카드는 측정하지 못했다.
  확실한 실기 증거는 "Wave CM" 의 **Speed** 줄 하나뿐(§1, §6) — 스텝 값
  줄의 `;`-체인이 똑같이 동작한다는 것은 같은 콘솔 명령 그래머의
  **추론**이지 직접 측정이 아니다.
- 4개 라벨(및 부수 10개)의 실제 콘솔 송신(Store/Label 실행) — 배차서
  제약으로 이 카드도 하지 않았다. `.moai/reports/t501/m6c_pregen_*` 가
  "보낼 수 있다"만 보인다.
- Rain 이 필요로 하지 않는 부수 10개 라벨(색 3종 + 콤보 7종)이 실제로
  다른 리그/곡에서 쓰이는 시나리오의 교차 확인.
- AC-LDRENDER-009(기계 증거, 실제 송신)는 PASS 로 보고하지 않는다 — 이
  카드는 전송하지 않았다.
- AC-LDRENDER-016(실기 감독 판정) — 사람 판정, 범위 밖.
- M6 §Gaps 의 나머지 항목(phase/curve 문법 괴리의 "같은 시각 효과" 확인,
  8곡 측정 하네스 한계, C1~C3 실기 재확인)은 이 카드가 손대지 않은 축 —
  그대로 미해소.
- `make test-fast` 의 실제 실행 결과 — 커밋 전 작성 시점에는 아직
  실행하지 않았다(§완료 보고의 "COMMIT FIRST" 뒤 섹션에서 갱신).

## 잔여 위험 (Residual-risk)

- M6 §잔여 위험 전부가 그대로 상속된다(풀 스냅샷 노화, 번호 할당 경쟁
  조건, `group=1` 일반화 미검증).
- `;`-체인 압축 폼이 스텝 값 줄에서도 실기로 동작한다는 가정이 실기로
  반증되면, 이 처방 전체를 재검토해야 한다 — 다음 송신 카드의 선결
  과제.
- `.moai/reports/t501/m6_postsend_reread_20261002.txt`/`m6_pool_reread_
  readonly.txt` 스냅샷은 이 카드 작업 시점보다 과거 캡처 — 전송 전
  재조회 필수(`m6c_pregen_targets_rain.md` 에 명시).
- 부수적으로 해소된 10개 라벨의 적용 범위(Rain 밖 리그/곡)는 검증되지
  않았다 — 이 메커니즘이 "일반적으로 안전하다"는 결론으로 과대 해석하지
  않도록 주의가 필요하다.

---

🗿 MoAI
