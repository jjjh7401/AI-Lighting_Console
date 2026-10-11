# t601 run 판정 — 송신 중복 제거가 한 묶음 안의 정당한 같은 줄을 조용히 건너뛰던 결함

- 카드: t601 · lane-2 · 브랜치 `WT-dedupe-legit-repeat` · 기준 origin/main `97533166`
- 콘솔 쓰기 0 · 콘솔 접촉 0(가짜 포트만)
- 바뀐 코드: `server/orchestrator/tools.py` `run_commands` 실행 고리 **2줄**(+ 주석). 시험 3파일.

## 왜 생겼나 (리드 요청: 고치기 전에 먼저 읽기)

`git log -S` 로 찾은 순서:

| 날짜 | 커밋 | 무엇 | 근거 |
|---|---|---|---|
| 07-16 | `099ce765` | `run_commands` 탄생. 중복 제거 = `context.executed_ok`(**앞선 호출**에서 성공한 줄)만 건너뜀 | REQ-MVP-033: 「부분 실행 뒤 자가 수정 루프는 미실행 잔여분과 신규 수정 명령에만 — **기실행 명령 중복 실행 금지**」. 재전송 때 이미 나간 줄을 또 보내지 말라는 뜻 |
| 07-18 | `82b83abc` (M6c-6) | 같은 호출 안에서 성공한 줄도 기억 → **같은 묶음 안 두 번째 등장도 건너뜀** | 실제 사고 없음. 리뷰 백로그(「M6c 종합 MEDIUM」)와 합성 시험 `["cmd1","cmd1"]` 하나 |
| 07-26 | `4dd48e8f` | `ClearAll`·맨 선택 줄을 면제 | **사고**: 룩 묶음이 끝 `ClearAll` 을 잃고, 계열별 캡처가 둘째 사이클부터 경계를 잃어 앞 사이클 프로그래머를 저장. 커밋 원칙: 「중복 제거는 **영속 산출물**만 막는다」 |
| 08-04 | `db555da9` | 그룹 쓰기를 그룹마다 따로 보냄 + 묶음 겹침 가드 | **사고(P0)**: 같은 장비 그룹 둘의 선택 체인이 건너뛰어져 `Store Group N` 이 빈 프로그래머에서 발화. 「승인한 카드와 콘솔이 받은 것이 다르다」 |
| (t476) | — | 선택+값 줄 면제 | **실기 사고**: Rain 반영에서 승인 107줄 / 송신 75줄. 두 큐가 같은 값을 쓰면 둘째 큐 값 줄이 빠져 Verse 3·4 어둠 25%→100%, Chorus 6 위치가 앞 큐 값으로 나감 |
| 10-12 | t593 | 반영당 효과 1개로 우회 | 효과 묶음마다 `Step 2` 가 같아 둘째 효과가 빈 채 저장될 자리 |

판정: 「막던 사고」는 REQ-MVP-033 의 **재전송 중복**이다 — 그건 `context.executed_ok` 로 지금도 막는다. 묶음 안 건너뛰기(07-18)는 막은 사고가 기록에 없고, 대신 사고를 네 번 냈다. 매번 면제를 하나씩 넓히는 식으로 땜질했고(`4dd48e8f`·t476), 그 밖은 쓰는 쪽이 묶음을 쪼개거나 겹침 가드를 다는 식으로 피했다(`db555da9`·`fx/instantiate.py _guard_collision`·`looks/busking.py`·`scene/compile.py`·t593).

## 무엇을 고쳤나

- `already_executed = set(context.executed_ok)` → `already_executed = context.executed_ok`, 그리고 고리 안 `already_executed.add(command)` 삭제(`server/orchestrator/tools.py:2522`, `:2549` 부근). 이제:
  - 앞선 호출에서 실행된 줄 → 그대로 `skipped_already_executed`(REQ-MVP-033 원뜻, 면제 규칙도 그대로).
  - 같은 묶음 안 반복 → 승인된 그대로 전부 실행.
- 그 자리에 `@MX:WARN` — 이 집합에 무엇을 넣느냐가 「조용히 건너뜀」의 범위라는 경고와 사고 이력.
- 면제 목록(`_PROGRAMMER_STATE_COMMANDS`)·`fx/instantiate.py` 쌍둥이·게이트(`gate.screen`)·자가 수정 루프(`runner.py:498` 이 `executed_ok` 를 호출 사이에 누적)는 **안 건드렸다**.

## 기존 시험 기대값을 바꾼 곳 (뜻이 바뀐 시험 6건 → 같은 성질을 앞선 호출 기준으로)

- `test_tools.py`
  - `test_in_bundle_duplicate_command_is_not_re_executed` → `test_in_bundle_repeat_runs_each_time_it_appears`(07-18 확장을 못박던 시험, 이제 반대를 잠근다).
  - `test_a_repeated_store_is_still_deduped` → `test_a_store_a_prior_call_executed_is_still_deduped`.
  - `test_the_leading_verb_is_the_discriminator_not_the_object_type`·`test_a_selection_carrying_a_value_is_still_deduped` — 면제 판별(맨 선택형만 면제)은 그대로 재고, 기준만 앞선 호출 집합으로.
- `test_dedupe_value_lines_t476.py::test_artifact_lines_are_still_deduped`(10 케이스) — 앞선 호출 기준으로. 세 면제 정의(`tools`·`fx`·`groupgen`)가 모두 False 인 단언은 그대로.

## 검증

- 재현 먼저: `server/tests/test_dedupe_legit_repeat_t601.py` 를 쓰고 고치기 전 실행 → `2 failed, 3 passed`. 효과 묶음 둘(`sweep-soft-wide`·`wave-soft-rise`, 22.1·22.2)에서 **둘째 묶음의 `ChangeDestination Root` 와 `Step 2` 두 줄이 빠졌다**(`At index 11 diff: 'ClearAll' != 'ChangeDestination Root'`, `Right contains 2 more items`). 카드가 적은 `Step 2` 만이 아니었다.
- 원인 재확인(「증상이 아니라 원인인가」): 빠진 두 줄 모두 면제 아닌 줄이고, 같은 묶음 앞쪽에서 이미 성공한 글자다 — 고리 안 `add` 를 없애자 같은 시험이 통과했다(아래 뮤테이션 R 이 반대 방향을 잰다).
- 고친 뒤: `pytest test_dedupe_legit_repeat_t601.py test_tools.py test_dedupe_value_lines_t476.py` → `100 passed`.
- 뮤테이션(`.moai/reports/t601/mutate.py`, 각각 되돌린 뒤 `grep -c MUTATION server/orchestrator/tools.py` → 0):
  - R 수정 되돌리기(묶음 안 성공을 다시 기억) → `3 failed, 97 passed`.
  - P 앞선 호출 건너뛰기 끄기(REQ-MVP-033 무력화) → `16 failed, 84 passed` — 원래 기능도 시험이 지킨다.
- 서버 전체: `uv run pytest -q -p no:cacheprovider -rf server` → `15482 passed, 35 skipped, 1 warning in 223.00s`, `FAILED` 0(`server-pytest.log`). 시험 기대값을 옮기기 전 첫 실행은 `10 failed`(전부 위 t476 시험).
- `uv run ruff check server .moai` → `All checks passed!` · `ruff format --check` → `817 files already formatted`.

## t593 「반영당 효과 1개」 우회를 풀 수 있나 — **예, 다음 카드로**

- 반영(`beat_grid_apply`)은 디스패치마다 새 `ExecutionContext(risk=…, approval_owned_by_caller=True)`(`server/web/session.py:11509`)를 쓴다 → `executed_ok` 가 비어 있어 앞선 호출 건너뛰기가 끼어들 자리가 없다. 이번 수정으로 묶음 안 반복은 전부 나가므로, 효과 묶음 여럿을 한 반영에 실어도 줄이 빠지지 않는다(도구 단위 시험 `test_two_effect_bundles_send_every_line` 이 그 꼴을 잰다).
- 풀 때 걷어낼 것: `beat_grid_effect_presets.effect_preset_outcomes` 의 겹침 검사(`EFFECT_BATCH_COLLISION`), `session.py` 의 「효과 줄이 큐 줄과 겹치면 반영 중단」 가드, t593 시험 2건(`TestOnlyOneEffectPerBatch`·`test_two_new_effects_send_only_one_store`)·`test_overlap_with_a_cue_line_stops_the_whole_apply`. 이 PR 에서는 범위 밖이라 손대지 않았다(리드 판단).
- 같은 이유로 이제 불필요해진 쓰는 쪽 우회: `fx/instantiate.py _guard_collision`(묶음 안 같은 줄 거절), `groupgen/write.py guard_bundle_collision`·그룹마다 따로 보내기, `looks/busking.py`·`scene/compile.py` 의 `_guard_collision`. 해롭지 않아 그대로 둔다 — 걷을지 리드 판단.

## 안 잰 것 / 남은 위험

- **같은 묶음 안 같은 `Store` 두 번**: 이제 둘 다 나간다. 콘솔이 이미 있는 대상에 다시 `Store` 를 받으면 무엇을 하는지(덮어쓰기·합치기·확인 창·오류)는 재지 않았다. 지금 어느 생산 경로도 같은 `Store` 줄을 한 묶음에 두 번 내지 않는다(생산 경로는 번호가 다르다 — 코드 판독, 실측 아님). 모델이 직접 짠 묶음에 그런 줄이 있으면 승인 카드에 두 줄이 그대로 보인다. → t602 실기 항목 후보.
- **호출을 건너는 겹침은 그대로다**: 모델 대화 한 차례 안에서 효과 도구를 두 번 부르면 둘째 호출의 `Step 2` 는 앞선 호출에서 나갔으므로 여전히 건너뛴다 — REQ-MVP-033 이 정한 동작이고, `fx/instantiate.py collided_lines`(CROSS_CALL_COLLISION)가 그 경우를 거절해 알린다. 이 카드는 그 경계를 바꾸지 않았다.
- **실기 0회**: 묶음 안 반복이 콘솔에서 의도대로 동작하는 것은 t476(값 줄)·`4dd48e8f`(ClearAll 21줄 왕복) 선례로 보고, 효과 둘을 한 묶음에 섞는 꼴은 t602 ⑨ 에 있다.
- lane-3 t598 이 `gate.screen` 근처를 만지는 중 — 이 PR 의 변경은 게이트 아래 실행 고리 두 줄뿐이라 글자 충돌 가능성은 낮지만, 늦게 합치는 쪽이 푼다.
