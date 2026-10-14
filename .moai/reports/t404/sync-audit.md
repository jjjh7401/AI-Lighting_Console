# Sync Audit — SPEC-COPILOT-COLORMODE-001

워크트리: `.claude/worktrees/t404` (branch `WT-color-usage-question`, HEAD `8f78a6eb`)
검증 기준: plan `1a719464` → HEAD, 실측 재실행(요청받은 명령을 직접 실행, 진행 기록의 주장을 그대로 신뢰하지 않음).

## Overall Verdict: **FAIL**

Must-pass 방화벽(Functionality)이 AC-COLORMODE-006 FAIL로 인해 발동. 다른 3개 차원 점수와 무관하게 전체 판정은 FAIL.

## Dimension Scores

| Dimension | Score | Verdict | Evidence |
|-----------|-------|---------|----------|
| Functionality (40%) | 70/100 | **FAIL** | 16개 AC 중 14개는 실제로 재현·확인됨(아래 표). AC-COLORMODE-006은 acceptance.md 자신이 지정한 검증 지점(`test_web_session.py`의 `_song_run_interview` 루프)을 전혀 실행하지 않는 엔진 레벨 대체 시험으로 PASS 처리되었음 — 뮤테이션 프로브로 실제 회귀 무방비 상태를 증명(F1). AC-COLORMODE-007도 트리거 문자열("Q2B 다시"/"색 운용 다시")이 테스트 전무(F2, 부분 FAIL). |
| Security (25%) | 100/100 | PASS | `grep -rn "secret\|password\|api_key\|eval(\|exec(\|subprocess\|os.system" server/design/interview.py server/design/song_plan.py ui/src/components/analysisSummary.ts` → 0건. `git diff 1a719464..HEAD -- pyproject.toml ui/package.json` → 0줄(신규 의존성 없음). `grep -rn 'dangerouslySetInnerHTML\|innerHTML' ui/src/components/*.tsx` → 0건. |
| Craft (20%) | 78/100 | PASS-with-notes | 전체 회귀 재실행 `13659 passed, 33 skipped, 0 failed`(exit 0) — 진행 기록과 일치. `uv run ruff check server` → `All checks passed!`. `uv run ruff format --check server` → `659 files already formatted`. UI `577/577 passed`, `npm run build` exit 0. 커버리지 실측 일치(interview.py 98%/song_plan.py 80%/session.py 82% — 진행 기록 숫자와 정확히 일치). 다만 §E1의 "63/63 회귀 통과" 인용이 실측(56/56)과 불일치(F3, 저심각도) — 검증-주장 무결성(§2) 경미 위반. |
| Consistency (15%) | 90/100 | PASS | `git diff 1a719464..HEAD --stat` — 변경 파일 15개 전부 spec.md/plan.md 범위(interview.py/session.py/song_plan.py/analysisSummary.ts + 대응 시험 + progress.md/spec.md 상태) 안에 있음. PRESERVE 목록 위반 없음. 코드 스타일·주석 밀도·네이밍이 기존 파일 관례와 일치. |

## Mechanical Verification Batch (verbatim)

```
$ uv run pytest -q
13659 passed, 33 skipped, 1 warning in 182.26s (0:03:02)
[exited with code 0]

$ npm --prefix ui test -- --run
Test Files  25 passed (25)
     Tests  577 passed (577)

$ npm --prefix ui run build
✓ 59 modules transformed.
✓ built in 293ms

$ uv run ruff check server
All checks passed!

$ uv run ruff format --check server
659 files already formatted

$ grep -rn 'AskUserQuestion' server/design server/web | grep -v tests
(no output)

$ git status --short
?? .moai/reports/t404/

$ git diff --stat
(empty — tree byte-identical to HEAD after all mutation probes reverted)
```

## E1 재현 매트릭스 (16/16 AC 명령 재실행)

| AC | 판정 | 재실행 결과 | 비고 |
|----|------|------------|------|
| AC-001 | PASS | `test_design_interview.py::TestQ2bColorUsageOptions` → 3 passed | — |
| AC-002 | PASS | `TestQ2bBlankAnswerIsDefaultAccepted` → 2 passed | 뮤테이션 (a)로 KILLED 확인(아래) |
| AC-003 | PASS | `test_song_cue_composer.py::test_color_usage_default_accepted_decision_never_generates_a_requery` → 1 passed | `DirectorDecision`을 직접 생성해 검증(엔진 산출 경로 자체는 별도 검증 필요 없음 — REQ-010 대상은 `_requery_requirements`뿐) |
| AC-004 | PASS | `TestQ2bOptionAndFreeTextResolveAllThreeValues` → 9 passed | — |
| AC-005 | PASS | `TestQ2bUnresolvedFreeTextReAsks` → 1 passed | — |
| **AC-006** | **FAIL (claimed-PASS)** | `TestExistingRestartsUnaffectedByQ2bInsertion` → 1 passed, but **테스트 대상이 acceptance.md가 지정한 지점이 아님** | 상세 F1 |
| AC-007 | **PARTIAL (claimed-PASS)** | `TestQ2bRestart` → 1 passed, but 트리거 문자열 미검증 | 상세 F2 |
| AC-008 | PASS | 세션 페이로드 2건 → 2 passed | — |
| AC-009 | PASS | `analysisSummary` vitest → 14 passed(3건 신규 모드 포함) | — |
| AC-010 | PASS | 위와 동일 | default_accepted 마커 검증 포함 |
| AC-011 | PASS | `TestModulateIsByteIdenticalToPreSpec` → 2 passed + t402/t403/t405/t406 회귀 56 passed | 진행 기록의 "63/63"은 오기재(F3) |
| AC-012 | PASS | `TestSingleReturnsBaseEverywhere` → 3 passed | 뮤테이션 (b)로 KILLED 확인 |
| AC-013 | PASS | `TestPerChorusConsecutiveAccentsDiffer` → 4 passed | 뮤테이션 (c)로 KILLED 확인 |
| AC-014 | PASS | `test_full_choice_flow_previews_before_any_write_and_asks_for_approval` → 1 passed | 카드 7장, `asked[2]` = Q2B 확인 |
| AC-015 | PASS | `TestQ2RestartDiscardsQ2b` → 1 passed | — |
| AC-016 | PASS | `TestQ2bDoesNotChangeOtherStepsBlankBehavior` → 5 passed | — |

## Mutation Probe Table

| # | 프로브 | 대상 | 결과 |
|---|--------|------|------|
| (a) | `default_confirms` 효과 제거(`if False and card.default_confirms:`) | `server/design/interview.py:1194` | **KILLED** — `TestQ2bBlankAnswerIsDefaultAccepted` 2건 FAIL |
| (b) | `single`이 `_arc_palette`로 폴백(`if color_usage == "single" and False:`) | `server/web/session.py:1825` | **KILLED** — `TestSingleReturnsBaseEverywhere` 2건 FAIL |
| (c) | `per_chorus`가 매 회차 같은 악센트 반환(`accent = ladder[0]`) | `server/web/session.py:1155` | **KILLED** — `TestPerChorusConsecutiveAccentsDiffer::test_per_chorus_consecutive_accents_differ` FAIL |
| (d) | restart를 사전-SPEC `STEP_ORDER[N-1]` 암묵 인덱싱으로 복원 | `server/web/session.py:8706-8710` | **SURVIVED** — `test_web_session.py::TestSongDesignInterviewSession` 전체(72건 상당) + `test_design_interview.py` 전체(98건) 재실행, **0건 실패**. plan.md §E가 "이 SPEC에서 가장 위험한 리팩터 지점"이라 명시한 바로 그 결함이 무방비 상태. |

모든 프로브는 실행 후 `git checkout -- <file>`로 원상 복구, `git status --short`/`git diff --stat`로 트리 무변경 확인(위 배치 참고).

## Findings (구조화 결함 목록)

- **F1** [High] [blocking] `server/web/session.py:8706-8710`, `server/tests/test_design_interview.py:774-789` — AC-COLORMODE-006이 claimed-PASS이나 실제로는 검증되지 않았다. acceptance.md는 "`_song_run_interview` 루프 도중 답변으로 'Q3 다시'가 들어오면"을 Given/When으로, 판정 위치를 `server/tests/test_web_session.py`로 명시한다. 그러나 progress.md §E1에 PASS로 기록된 테스트(`test_design_interview.py::TestExistingRestartsUnaffectedByQ2bInsertion`)는 `interview.restart_from(Q3_CLIMAX)`를 파이썬 API로 직접 호출할 뿐, session.py가 이 SPEC에서 실제로 바꾼 정규식(`_SONG_RESTART`의 `2[Bb]|[1-5]` 교체)과 `_SONG_RESTART_STEP_BY_TOKEN` 조회 테이블을 전혀 실행하지 않는다. 뮤테이션 프로브 (d)로 실증: session.py의 조회 테이블 호출을 SPEC 이전의 `STEP_ORDER[int(no)-1]` 암묵 인덱싱으로 되돌려도 `test_web_session.py`/`test_design_interview.py` 전체가 0건 실패로 그린을 유지한다 — "Q3 다시"가 조용히 `Q2B_COLOR_USAGE`로 잘못 라우팅되는, plan.md §E가 이 SPEC의 최고 위험으로 명시한 바로 그 결함이 지금 아무 회귀망도 없이 재발 가능하다. Required fix: `test_web_session.py`에 `session.run_instruction`을 통해 실제로 "Q3 다시"(및 "Q4 다시"/"Q5 다시") 답변을 제출하고, 결과 타임라인이 Q3(또는 Q4/Q5) 재시작을 반영함을 단언하는 케이스를 추가한다.

- **F2** [Medium] [blocking] `server/web/session.py:454, 8711-8713` — AC-COLORMODE-007의 트리거("Q2B 다시" 또는 "색 운용 다시" 자유 텍스트)가 테스트 스위트 전체에서 리터럴로 단 한 번도 등장하지 않는다(`grep -rn '"Q2B 다시"\|"색 운용 다시"' server/tests/*.py` → 0건). PASS로 기록된 `test_design_interview.py::TestQ2bRestart`는 `interview.restart_from(Q2B_COLOR_USAGE)`를 직접 호출해 "재시작 이후 상태"만 검증하고, 이 SPEC이 실제로 추가한 신규 코드(`_SONG_RESTART`의 `2[Bb]` 대안 + 신규 `_SONG_RESTART_COLOR_USAGE` 정규식)의 "입력 인식" 자체는 어디서도 실행되지 않는다. 정규식 자체는 수동 확인상 올바르게 동작하지만(`python3 -c "..."`로 확인), 자동화된 회귀 방어가 전무하다. Required fix: `test_web_session.py`에 "Q2B 다시"와 "색 운용 다시" 각각을 `_song_run_interview` 경로로 제출하는 케이스 추가.

- **F3** [Low] [optional] `.moai/specs/SPEC-COPILOT-COLORMODE-001/progress.md:50` — AC-COLORMODE-011 행이 "63/63 회귀 통과"를 인용하나, `uv run pytest -q server/tests/test_song_palette_occurrence_t402.py server/tests/test_song_accent_ladder_t403.py server/tests/test_arc_fx_occurrence_t405.py server/tests/test_song_palette_occurrence_t406.py`의 실측 결과는 `56 passed`(6+9+32+9, `--collect-only` 확인)이다. 56건 전부 통과하므로 기능 결함은 아니나, verification-claim-integrity §2(baseline 귀속)가 요구하는 "이번 실행에서 관측한 값"과 불일치하는 인용 — 근거 없이 옮겨 적힌 숫자로 보인다. Required fix: 다음 보고 시 verbatim 재측정.

- **F4** [Low] [optional] `ui/src/components/analysisSummary.test.ts` (AC-009/010 신규 케이스) — 각 케이스가 `director_decisions`에 `color_usage` 축 하나만 담아 검증하고, `palette` 축과 `color_usage` 축이 동시에 존재할 때 두 문장이 `·` 구분자로 정상 이어붙는지 확인하는 결합 케이스가 없다. `buildColorLine`의 구현(독립적인 `parts.push` 두 번)상 상호작용 버그 가능성은 낮으나, 결합 시나리오 커버리지 공백.

- **F5** [Low] [optional, 이미 자진 고지됨] `server/web/session.py:1843-1916`(`_section_palette_sizes`/`_split_sections_for_density`) — `color_usage`를 두 호출부에 스레딩한 것은 plan.md M2가 명시적으로 요구한 배선이며 순수 통과가 아니라 실질적 동작 변경이다(`single`/`per_chorus`의 팔레트 길이가 `modulate`와 달라 큐 밀도 분할 결과가 바뀔 수 있음). progress.md 자신의 잔여 위험 절에 이미 정직하게 고지되어 있고, `modulate` 기본 경로는 전체 회귀로 재확인됨 — 은폐된 공백이 아니라 알려진 채로 남은 단위 시험 공백. 후속 시험 권고.

## Scope Judgment (item 3)

`git diff 1a719464..HEAD --stat` 15개 파일 전부가 spec.md §2 D1-D6 / plan.md M1-M2 범위 안에 있다. `_section_palette_sizes`/`_split_sections_for_density`로의 `color_usage` 스레딩(`server/web/session.py:1846, 1883, 1900-1906`)은 plan.md §C M2 1번 항목이 두 호출부를 명시적으로 지정("두 호출부(`_section_palette_sizes` 1764행, `_build_unified_song_plan` 내부 1949행 부근) 모두에 `color_usage`를 전달")한 대로다 — **(i) SPEC이 요구한, `_section_palette_choice`에 도달하기 위한 필수 배선**으로 판단한다. 다만 F5에서 지적한 대로 이것이 "순수 통과"는 아니고(`single`/`per_chorus`에서 실제로 산출 길이가 달라질 수 있음) 실질적 동작 변화이며, 이는 REQ-013/014가 이미 요구한 값을 두 번째 선언된 호출부까지 일관되게 전달하는 것이므로 SPEC이 요청하지 않은 범위 확장(ii)은 아니다.

## Recommendations

1. (F1, blocking) `test_web_session.py`에 "Q3 다시"/"Q4 다시"/"Q5 다시"를 `session.run_instruction`으로 실제 제출하는 세션-레벨 회귀 케이스 추가 — plan.md §E가 명시한 최고 위험 지점의 실제 방어망 확보.
2. (F2, blocking) "Q2B 다시"/"색 운용 다시" 리터럴 트리거 문자열을 세션 레벨에서 검증하는 케이스 추가.
3. (F3, optional) progress.md의 회귀 카운트 재측정·정정.
4. (F4, optional) palette + color_usage 결합 렌더링 케이스 추가.
5. (F5, optional) `single`/`per_chorus`가 실제로 밀도 분할 개수를 바꾸는 시나리오의 단위 시험 추가.

## 재감사 d7bb16ae

워크트리 동일(`t404`, branch `WT-color-usage-question`), HEAD `d7bb16ae`(fix commits `df17ab41`, `d7bb16ae`). F1-F5 보정 확인. 검증 기준: `8f78a6eb` → HEAD, 실측 재실행.

### 프로덕션 코드 무변경 확인

```
$ git diff 8f78a6eb..HEAD --stat
 .moai/specs/SPEC-COPILOT-COLORMODE-001/progress.md |  39 +++-
 server/tests/test_song_color_usage_t404.py         | 122 +++++++++++-
 server/tests/test_web_session.py                   | 212 +++++++++++++++++++++
 ui/src/components/analysisSummary.test.ts          |  18 ++
 4 files changed, 383 insertions(+), 8 deletions(-)

$ git diff 8f78a6eb..HEAD -- server/web/session.py server/design/interview.py server/design/song_plan.py ui/src/components/analysisSummary.ts | wc -l
0
```

`session.py`가 정확히 diffstat에서 빠져 있음 — claimed byte-identical 확인. 이번 재감사는 순수하게 시험 추가 + progress.md 보정임.

### F1/F2 재검증 — 결합 뮤테이션 프로브 (지시받은 그대로)

`_SONG_RESTART`에서 `2[Bb]` 대안 제거 + `_SONG_RESTART_COLOR_USAGE`를 매칭 불가 패턴(`(?!)`)으로 무력화 + 호출부를 `STEP_ORDER[int(no)-1]` 암묵 인덱싱으로 복원(사전-SPEC 결함 재현):

```diff
-_SONG_RESTART = re.compile(r"[Qq]\s*(?P<no>2[Bb]|[1-5])\s*(?:만)?\s*다시")
-_SONG_RESTART_COLOR_USAGE = re.compile(r"색\s*운용\s*다시")
+_SONG_RESTART = re.compile(r"[Qq]\s*(?P<no>[1-5])\s*(?:만)?\s*다시")
+_SONG_RESTART_COLOR_USAGE = re.compile(r"(?!)")  # MUTATION: never matches
@@ call site @@
-                    token = restart_match.group("no").lower()
-                    interview.restart_from(_SONG_RESTART_STEP_BY_TOKEN[token])
+                    from server.design.interview import STEP_ORDER as _MUT_STEP_ORDER
+                    interview.restart_from(_MUT_STEP_ORDER[int(restart_match.group("no")) - 1])
```

```
$ uv run pytest -q server/tests/test_web_session.py::TestSongDesignInterviewSession -k "q3_다시 or q4_다시 or q5_다시 or q2b_다시 or 색_운용_다시" -v
...
FAILED ...::test_q3_다시_reaches_q3_climax_prompt_not_q2b_or_q4_and_continues_to_q4_q5
FAILED ...::test_q4_다시_reaches_q4_prompt_not_q5_and_continues_to_q5
FAILED ...::test_q5_다시_restarts_q5_itself_not_q4
FAILED ...::test_q2b_다시_reaches_q2b_prompt_and_drops_q3_until_re_answered
FAILED ...::test_색_운용_다시_reaches_q2b_prompt
======================= 5 failed, 68 deselected in 1.22s =======================
```

**5개 신규 시험 전부 RED 확인** — F1/F2가 지목한 정확한 결함(STEP_ORDER 삽입 후 암묵 인덱싱이 "Q3 다시"를 Q2B로, "Q4 다시"를 Q3으로, "Q5 다시"를 Q4로 잘못 라우팅하고, "Q2B 다시"/"색 운용 다시"는 아예 인식되지 않아 무시됨)가 지금은 이 5개 시험으로 실제 회귀 방어망을 가진다.

복구 후:

```
$ git checkout -- server/web/session.py
$ git diff --stat server/web/session.py
(empty)
$ uv run pytest -q server/tests/test_web_session.py::TestSongDesignInterviewSession server/tests/test_design_interview.py
........................................................................ [ 42%]
........................................................................ [ 84%]
...........................                                              [100%]
171 passed in 1.31s
```

GREEN 확인, 트리 바이트 동일(`git status --short` → `.moai/reports/t404/`만 표시, `git diff --stat` → 빈 출력).

### F3 재검증 — 56/56 인용 정정

```
$ uv run pytest -q --collect-only server/tests/test_song_palette_occurrence_t402.py server/tests/test_song_accent_ladder_t403.py server/tests/test_arc_fx_occurrence_t405.py server/tests/test_song_palette_occurrence_t406.py
56 tests collected in 0.25s
$ uv run pytest -q server/tests/test_song_palette_occurrence_t402.py server/tests/test_song_accent_ladder_t403.py server/tests/test_arc_fx_occurrence_t405.py server/tests/test_song_palette_occurrence_t406.py
........................................................                 [100%]
56 passed in 0.41s
```

progress.md §E1 AC-COLORMODE-011 행이 이제 "56/56"으로 정정되었고, 실측 명령까지 인용에 포함됨(`--collect-only` 근거 명시) — 검증-주장 무결성 §2 기준 충족. **F3 해소.**

> 잔여 미세 불일치(비차단): `progress.md` §E.3(151-156행)의 요약 줄이 아직 구값(`13659 passed... UI 577/577`)을 인용한다 — §E.2의 최신 값(`13668 passed... UI 578/578`)과 어긋난다. 기능 결함 아님, 문서 정합성 정정 권고.

### F4 재검증 — 결합 렌더링 시험

```
$ npm --prefix ui test -- --run analysisSummary
✓ src/components/analysisSummary.test.ts (15 tests) 2ms
Test Files  1 passed (1)
     Tests  15 passed (15)
```

신규 케이스("palette 축과 color_usage 축이 함께 있으면 한 색 줄에 둘 다 담긴다")가 `colorLines).toHaveLength(1)`(같은 줄에 담김) + `colorLine.text`가 팔레트 문구("Q2 PALETTE", "블루/퍼플")와 색 운용 문구("색 운용", "색 계열로만 유지") 양쪽을 모두 포함함을 단언 — 두 파트가 실제로 공존함을 검증. **F4 해소.**

### F5 재검증 — 실측(추측 아님) 확인

```
$ uv run pytest -q server/tests/test_song_color_usage_t404.py::TestColorUsageAffectsQueueDensity -v
collected 4 items
....
4 passed in 0.24s
```

신규 클래스가 `_section_palette_sizes`/`_split_sections_for_density`를 직접 호출해 구체적 수치를 단언: `single`은 팔레트 크기를 `[2,2,2,2]`→`[1,1,1,1]`로, 실제 큐 분할 개수를 5→3으로 **실측**해서 줄이고(`assert len(single_expanded) < len(modulate_expanded)`뿐 아니라 `== 5`/`== 3` 구체값 단언), `per_chorus`는 두 값 모두 modulate와 동일함을 실측 확인 — 가정이 아니라 `plan_cue_density`/`_section_palette_choice`를 실제로 구동한 결과. **F5 해소.**

### Re-Scored Dimensions

| Dimension | Score | Verdict | Evidence |
|-----------|-------|---------|----------|
| Functionality (40%) | 98/100 | **PASS** | 16/16 AC 재현 PASS. AC-006/007이 이제 session.py의 실제 `_song_run_interview` 루프·`_SONG_RESTART`/`_SONG_RESTART_COLOR_USAGE`/`_SONG_RESTART_STEP_BY_TOKEN`을 실행하는 5개 세션-레벨 시험으로 검증되며, 결합 뮤테이션 프로브(STEP_ORDER[N-1] 복원 + 2[Bb] 제거 + COLOR_USAGE 규칙 무력화)로 전부 SURVIVED→KILLED 전환 확인. 전체 회귀 `13668 passed, 33 skipped, 0 failed`(exit 0, 재실행 확인). 2점 감점: progress.md §E.3의 스테일 요약 줄(문서 정합성, F3 잔여 미세 불일치) — 기능적 영향 없음. |
| Security (25%) | 100/100 | PASS | 재확인: `grep` 시크릿/eval/exec/subprocess/innerHTML → 0건. 신규 의존성 없음(`git diff 8f78a6eb..HEAD -- pyproject.toml ui/package.json` → 0줄). |
| Craft (20%) | 95/100 | PASS | `ruff check`/`ruff format --check` 클린 재확인. UI `578/578`, build exit 0. F3(56/56 정정) + F5(실측 밀도 시험) 완전 해소. 5점 감점: 위 문서 정합성 잔여 미세 불일치(F3 잔여). |
| Consistency (15%) | 92/100 | PASS | 신규 시험 6건(session-level 5 + density 4 − 중복 없음) + 결합 렌더링 1건 모두 기존 클래스 구조·주석 밀도·네이밍 관례를 따름. sync-audit 참조 주석("sync-audit F1/F2", "sync-audit.md F5")으로 근거가 추적 가능하게 남음. |

### Overall Verdict: **PASS**

Must-pass 방화벽(Functionality/Security) 모두 충족 — Functionality 98/100(FAIL→PASS 전환, 뮤테이션 프로브로 실증), Security 100/100. 가중 평균 ≈ 96.7/100.

### Remaining Blocker

**없음.** F1-F5 전부 해소 확인(F1/F2는 뮤테이션 프로브로 RED→GREEN 실증, F3/F4/F5는 재실행으로 확인). 유일한 잔여 항목은 비차단 문서 정합성 하나: `progress.md` §E.3(151-156행) 요약 줄의 스테일 숫자(`13659`/`577`)를 §E.2의 최신 값(`13668`/`578`)으로 갱신 권고 — 병합을 막을 사유 아님.
