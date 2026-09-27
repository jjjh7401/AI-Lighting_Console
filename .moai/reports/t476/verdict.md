# t476 판정서 — 승인한 값 줄이 중복 제거로 조용히 빠지던 결함

- 카드: t476 · SPEC-LDDESIGN-001 · lane-2 · 발견 t475(`.moai/reports/t475/verdict.md` §3)
- 브랜치: `WT-dedupe-value-lines`, 기준 `origin/main` c4506a7c (차이 `0 0` 확인)
- 콘솔 쓰기: 0 (가짜 콘솔만 사용)
- 감독 결정(착수 승인 겸, 2026-09-27): 「면제 목록 넓히기」 — 생성기 쪽 우회가 아니라 중복 제거의 면제 판정을 고친다
- 판정: **PASS**

## 0. 요약

`run_commands` 는 한 지시 안에서 이미 성공한 명령과 같은 글자의 줄을 다시 보내지 않는다. 이 규칙의 목적은
**저장물**(Store·Label 로 생기는 콘솔 객체)을 두 번 만들지 않는 것이다(`tools.py` 면제 주석). 그런데 면제
판정이 좁아서 `Fixture 20 + 26 ; Attribute 'Dimmer' At 25` 같은 **선택 + 값 줄**도 걸러졌다. 이 줄은 저장물을
만들지 않는다. 프로그래머에 값을 올릴 뿐이고, 저장은 뒤따르는 `Store` 가 한다. 그래서 같은 값을 쓰는 두 번째
큐는 그 속성을 저장하지 못했고, 콘솔은 앞 큐 값을 이어 받았다.

면제에 「선택 + 값 줄」 꼴 하나를 더했다. 이제 Rain 의 승인 카드 107줄이 콘솔에 107줄 그대로 닿고, 무대 차이는
6건에서 0건이 됐다. `Store`·`Label`·`Delete`·`Assign` 의 중복 방지는 그대로다.

## 1. 원인 판단 — 증상이 아니라 원인인가

- 걸러진 32줄은 모두 값 줄이고, 저장 줄·타이밍 줄은 0줄이다(t475 `tracking_diff.txt`).
- 면제 판정은 줄의 **모양**(맨 선택인가)으로 가르고, 목적(저장물을 만드는가)으로 가르지 않았다. 값 줄은 목적상
  면제 대상인데 모양 때문에 빠졌다. 그래서 원인은 판정이고, 「값 줄이 겹친다」는 증상이다.
- 생성기 쪽에서 글자를 다르게 만드는 우회는 이미 업로드 길이 쓰고 있다(`songcue.py` `_unique_floor_climb`:
  겹치면 밝기를 1% 씩 비껴간다). 이 방식은 연출 값을 바꾸고, 같은 프리셋으로 돌아오는 포지션 줄은 비껴갈 수 없다.
- 같은 결함이 큐시트 반영 길(`cue_sheet_apply`)에도 있다는 lane-1 판독을 재현 시험으로 확인했다(§3).

## 2. 무엇을 바꿨나

| 파일 | 변경 |
|---|---|
| `server/orchestrator/tools.py` | `_PROGRAMMER_STATE_COMMANDS` 에 선택 + 값 줄 패턴 1개. 근거 주석 |
| `server/fx/instantiate.py` | 같은 패턴(이 집합은 tools.py 와 같아야 한다 — 기존 동등성 시험) |
| `server/groupgen/write.py` | 같은 패턴(세 번째 복사본, 같은 이유) |
| `server/tests/test_dedupe_value_lines_t476.py` | 새 시험 24개 |
| `server/tests/test_fx_boundary.py` · `test_groupgen_write.py` | 집합 크기 단언 3 → 4 (의도한 변경) |

면제 패턴이 받는 꼴(대소문자 무시, 줄 전체 일치):

- `<선택> ; Attribute '<이름>' At <수>` — ` ; ` 로 여러 절을 이을 수 있고, 절 사이에 다시 선택(`Group 2 ;`)해도 된다
- `<선택> ; At Preset <풀>.<번호>`
- `<선택>` 은 기존 맨 선택과 같은 문법(`Fixture 20 + 26`, `Group 3`, `Fixture 101 Thru 110`)

받지 않는 꼴(계속 중복 제거된다, 시험으로 고정):

- 저장물을 만드는 줄: `Store …`, `Label …`, `Delete …`, `Assign …`
- 값 줄 뒤에 저장 동사를 붙인 줄: `Fixture 1 ; Attribute 'Dimmer' At 50 ; Store Sequence 1 Cue 1`
- 선택 없는 값 줄 `Attribute 'Dimmer' At 50`, 선택에 값을 바로 붙인 `Group 3 Full`·`Fixture 1 Thru 10 At 80`
  — 기존 시험이 이 꼴들을 「면제 아님」의 대조군으로 쓰고 있다. 이 꼴을 스토어 번들에 내는 생산자
  (업로드 길·fx·scene)는 자체 충돌 방어를 갖고 있어 이번 범위 밖에 두었다.

## 3. 완료 조건 판정

### ① 재현 시험 RED → GREEN — PASS

- RED: `uv run pytest server/tests/test_dedupe_value_lines_t476.py -q` → `14 failed, 10 passed` (`pytest_red.txt`)
  - Rain 시험의 실패 모양: 「Right contains 32 more items」 — t475 실측 누락 32줄과 같다
  - 통과한 10개는 대조군(Store·Label·Delete·Assign·선택 없는 값 줄 등이 **계속** 걸러지는가)
- GREEN: 같은 명령 → `24 passed` (`pytest_green.txt`). 그 뒤 세 번째 복사본(groupgen) 단언을 기존 시험 안에
  더했고, 최종 트리에서도 `24 passed` 다(`pytest_mirror.txt` 에 포함).

### ② 대화 길: Rain 번들 107줄 전부 도달 — PASS

- 시험 `test_the_whole_approved_rain_bundle_reaches_the_console`: t475 의 실측 Rain 구간·BPM 을 확정 분석으로
  넣고 대화 길 끝까지 돌려 `console.executed == 승인 카드 명령` 을 단언한다. 계기가 공허하지 않다는 증거로
  승인 카드 안에 드롭 앞 어둠 줄이 2번 이상 있음을 먼저 단언한다.
- 실제 음원 재실행: `uv run python .moai/reports/t475/rehearse_rain.py <Rain.mp3> .moai/reports/t476/rain_after`
  → `commands=107`, `executed_ok 107`, 「readback 검증 완료」.
  `tracking_diff.py` → `승인 카드 명령 107줄 · 콘솔이 받은 명령 107줄 · 빠진 줄 0` / `무대 차이 0건`
  (`tracking_diff_after.txt`). 승인 카드 명령은 t475 와 바이트 동일(`cmp`).

### ③ 큐시트 반영 길(lane-1 판독) — PASS

- 시험 `test_two_cues_with_the_same_value_line_both_reach_the_console`: Sugar 타임라인의 큐 20·70(둘 다
  KEY·BACK, 주색 P2)을 같은 밝기로 고쳐 `plan_console_apply` 로 계획을 세운다. 두 큐의 값 줄이 글자까지 같음을
  먼저 단언하고, 실제 `run_commands` 로 보내 전부 실행됨을 단언한다. 고치기 전에는 큐 70 의 값 줄이 빠졌다(RED).

### ④ 저장물 중복 방지 유지 — PASS

- `test_artifact_lines_are_still_deduped` 10개(위 §2 「받지 않는 꼴」) + 기존
  `test_tools.py::test_a_repeated_store_is_still_deduped`·`test_the_leading_verb_is_the_discriminator_not_the_object_type`·
  `test_a_selection_carrying_a_value_is_still_deduped` 통과.
- 세 복사본(tools·fx·groupgen)이 새 줄과 대조군 줄 모두에서 같은 답을 낸다(`test_every_exemption_definition_agrees_on_the_value_line`,
  기존 동등성 시험 `test_fx_boundary.py`·`test_groupgen_write.py`).

### ⑤ 업로드 길 — 바이트 동일 PASS

- 명령: `uv run python .moai/reports/t476/upload_path_bytes.py` → `BYTE-IDENTICAL`,
  양쪽 `sha256=022bf9926dd0c49be7e91ebcf6068223a787bbbbcecad03bdd08f98c83cde738` (`upload_path_bytes.txt`).
  업로드 길은 조립 안에서 면제 판정을 쓰므로, 같은 프로세스에서 예전 판정으로 갈아 끼운 조립과 비교했다.
  범위는 t462 dump_b 와 같은 16조합이고, 해시도 t462 판정서의 값과 같다.
- 대조군: `upload_path_control.py` → `predicate_calls=1500`, `selected_value_lines_in_upload_bundles=0`.
  판정은 실제로 불렸고, 업로드 번들에는 새 면제 꼴의 줄이 없다. 그래서 바뀌지 않는다(판정을 안 타서가 아니다).

### 회귀

- 영향받는 시험 236파일(`affected_tests.txt`: tools·fx·scene·looks·web·cue_sheet_apply 를 부르는 파일):
  `uv run pytest @.moai/reports/t476/affected_tests.txt -q` → `7594 passed, 29 skipped` (`pytest_affected.txt`)
- 8곡 게이트: `PASS 75 · n/a 29 · FAIL 0`
- `ruff check`·`ruff format --check`: 고친 파일 + 새 시험 + 증거 스크립트 통과

## 4. 안 잰 것

- **실기 콘솔**에 보내지 않았다. 같은 값 줄을 한 번들에서 두 번 받았을 때 콘솔이 두 번 다 받아들이는지는 t474 가 잰다.
  (프로그래머 값 설정은 멱등이라 문제될 근거는 없다 — 가정이다.)
- **전체 시험 스위트**는 돌리지 않았다. 영향받는 236파일만 돌렸다. 전체는 CI 가 PR head 에서 돈다.
- **모델이 직접 보내는 경로**(자가 수정 재시도)에서 같은 값 줄이 두 번째 도구 호출에 다시 나오면 이제 다시
  실행된다. 값 설정은 멱등이라 무대 결과는 같지만, 감사 로그에 같은 줄이 두 번 남는다. 이 동작 변화의 영향은
  시험으로만 봤고(7594 통과) 실사용 로그로 재지 않았다.
- **`songcue.py` 의 MX 주석 두 곳**(2148행·2741행)과 `spatial/choreography.py` 391행은 면제 집합을 「Clear·ClearAll·
  맨 선택뿐」이라고 적고 있다. 그 주석들이 다루는 줄(맨 `Attribute …` 값 줄·`Step 2`·반복형 선택)에 대해서는
  여전히 맞아서 고치지 않았다. 집합 목록으로 읽으면 이제 불완전하다.

## 5. 남은 위험

- **선택 없는 값 줄**(`Attribute 'Dimmer' At 50`)은 여전히 걸러진다. 이 꼴을 스토어 번들에 내는 생산자는 지금
  자체 방어(비껴가기·거절)를 갖고 있다. 새 생산자가 방어 없이 이 꼴을 내면 같은 결함이 다시 생긴다.
- 업로드 길의 비껴가기(`_unique_floor_climb`, 충돌 회수)는 이제 선택 + 값 줄에 대해서는 필요 없지만, 업로드 길은 그
  꼴을 내지 않으므로 그대로 두었다. 업로드 길이 나중에 선택 + 값 꼴로 바뀌면 비껴가기를 걷어낼 수 있다.

## 6. 증거 파일

`.moai/reports/t476/` — `pytest_red.txt`·`pytest_green.txt`(재현 시험), `pytest_mirror.txt`(복사본·동등성 5파일 353 통과),
`affected_tests.txt`·`pytest_affected.txt`(회귀), `rain_after/`·`rain_after.log`·`tracking_diff_after.txt`(실제 음원 재실행),
`upload_path_bytes.py`·`.txt`·`upload_path_control.py`·`.txt`(업로드 길).
