# 진행 기록 — SPEC-LDACCENT-001

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-09-20
- tier: M
- artifact_count: 4 (spec.md + plan.md + acceptance.md + progress.md)
- REQ/AC 수: 8/6 (Tier M 상한 16/16 — 여유 있음. AC 는 5→6, AC-LDACCENT-006
  신규 추가로 증가)
- depends_on: 없음(선행 SPEC 없음). related_specs: SPEC-COPILOT-SONGCUE-001
  (이 모듈의 원 SPEC, status: completed).
- 근거: 큐 카드 t424(2026-09-20 실측), `.moai/reports/t382/verdict.md`
  "범위 밖으로 남긴 것 — effective-accent filter" 예고, `origin/main`
  (`ca07b329`) 실측 코드(`server/looks/songcue.py`).
- **사람 확인 대기 항목: 0건 — 전량 해소됨(2026-09-20, 2차 저작 패스).**
  1차 판정(plan-auditor iteration 1, verdict FAIL, score 0.625, MP-7 자동
  실패)이 아래 항목을 지적했고, 이번 패스에서 전부 반영했다:
  - **NEEDS CLARIFICATION 마커 해소(MP-7)**: `intent_for_label` 라벨
    미매치 경로를 범위 안으로 들였다(감독 결정) — REQ-001/003 세 번째
    효과 조건으로 편입, AC-LDACCENT-006 신규 추가로 검증. plan.md/spec.md
    에서 마커 자체는 제거됨(`grep -n '\[NEEDS CLARIFICATION' plan.md` →
    0건, 아래 §자기검증 참고).
  - **D1(critical) — REQ-007 절대 불변식 모순**: 이제 D2(브라이트니스
    소진 경로) 를 명시적 예외로 이름 붙여 모순을 해소했다(REQ-007
    본문에 예외 조항 삽입, spec.md §4 새 Out of Scope 절과 정합).
  - **D2(major) — `_unique_floor_climb` 소진 경로(4번째 무영향 갈래)**:
    범위 밖으로 명시적으로 남기고(spec.md §4, 이유 명시), REQ-007 이
    그 예외를 이름 붙여 인용한다 — 침묵한 채 남기지 않았다.
  - **D3(major) — plan.md §B1 호출자 수 오기재**: "다섯 곳" → 직접
    호출자 "네 곳"으로 정정(`_max_climb`/`_finalize_marking_accents`/
    `_climb_rungs`/`_ensure_marking_accent`). `_exhausted_rungs` 는
    호출자가 아니라 M3 에서 새로 배선해야 하는 호출부로 재분류.
  - **D4(critical) — AC-LDACCENT-001 시작값 95≠골든 시험 20**: acceptance.md
    Given 을 20 으로 정정, spec.md §1.1 실측 재현 문단도 함께 정정.
  - **D5(minor) — AC↔REQ 인용 누락**: AC-LDACCENT-001~006 제목에
    "(검증: REQ-LDACCENT-XXX)" 인용 추가.
  - **D6(minor) — REQ-004/008 GEARS 키워드**: REQ-004 `Where`→`When`
    (이벤트-구동), REQ-008 `Where`→`While`(상태-구동)로 정정 + 메모 추가.
  - **D7(minor) — `dict()` 금지 문면 과장**: 실제 AST 가드는 `ast.Dict`
    (`{}` 리터럴)만 재고 `dict()` 함수 호출은 통과한다는 사실을 plan.md
    §B5/§D/§C, acceptance.md 품질 게이트에 반영.
- ⚠️ 로컬 checkout 동기화 필요 — plan.md §A 참고. 이 SPEC 저작 시점의 로컬
  HEAD(`469e41b2`)는 `origin/main`(`ca07b329`)보다 12커밋 뒤졌다. run-phase
  착수 전 `git fetch origin main` + 동기화 확인이 첫 사전 점검이다.

## §E.2 Run-phase Evidence

- run_started_at: 2026-09-20
- HEAD: `ca07b3299ad6ad3a128d80c542bd4e6e604c4d96` (동기화 완료 — `git rev-list --count --left-right origin/main...HEAD` → `0 0`, plan.md §A/§C 사전 점검 통과)
- cycle_type: tdd (RED-GREEN-REFACTOR)
- 변경 파일: `server/looks/songcue.py`(핵심), `server/tests/test_songcue_ladder.py`,
  `server/tests/test_songcue_accent_ladder_t382.py`,
  `server/tests/test_songcue_chorus_rescue.py`,
  `server/tests/test_songcue_accent_fixture.py`(전량 plan.md §A 예고 파일 안에 있음)

### 착수 전 기준선

- `uv run pytest -q server/tests/test_songcue_ladder.py server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_fixture.py server/tests/test_songcue_report.py server/tests/test_song_accent_ladder_t403.py`
  → `64 passed in 1.57s`
- `uv run pytest -q` (전체, origin/main 동기화 직후) → `13685 passed, 35 skipped in 228.91s`
- `uv run pytest -q server/tests/test_songcue_sections.py::test_parser_imports_the_section_vocabulary_and_defines_no_mapping_literals` → `1 passed` (`{}` 매핑 리터럴 금지 AST 가드)

### RED — 신규/확장 시험이 고치기 전 구현에 대해 실패한 것을 확인

수정 전 구현(필터 없음)으로 신규 대조군(`TestEffectiveBlinderStillRotatesAndReachesTheConsole`,
`TestLabelWithoutSixRowExcludesBlinderEvenWithAGroup`, `TestZoomOnlyLookExcludesIrisFromRotation`)과
`TestHeadroomCaseIsUntouched`/`TestEveryRepeatOccurrenceCarriesOneAccent`/
`test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking`/
`TestTheChorusRescueGeneralizesBeyondDrop::test_worship_four_chorus_repeats_all_survive_on_the_real_library`/
`TestAccentGroupAbsentMeansNoConsoleCommand`를 이 SPEC 의 새 단언대로 먼저 작성하면
전량 RED 였다(구현 전 실측, 실패 사유는 전부 "무영향 칸이 `.ladder`에 남아 있다" 또는
"`accent_withheld`가 `None`이다" 형태) — 예:

```
$ uv run pytest -q server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_fixture.py
FAILED ...TestEveryRepeatOccurrenceCarriesOneAccent::test_all_seven_survive_with_non_decreasing_brightness_and_one_accent_each
FAILED ...TestEveryRepeatOccurrenceCarriesOneAccent::test_instances_two_three_four_cycle_through_different_accents
FAILED ...TestHeadroomCaseIsUntouched::test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after
FAILED ...TestTheChorusRescueGeneralizesBeyondDrop::test_worship_four_chorus_repeats_all_survive_on_the_real_library
FAILED ...TestAccentGroupAbsentMeansNoConsoleCommand::test_no_blind_group_in_the_rig_means_no_accent_command
6 failed, 58 passed in 0.66s
```

(모듈 최상단 `_MARKING = _marking_accents(allow_strobe=False)`가 새 시그니처와
충돌해 최초 1회는 수집 단계 `TypeError`로 실패했다 — `_MARKING_ACCENTS` 상수
직접 참조로 정정.)

### GREEN — 구현 후 동일 시험 전량 통과

```
$ uv run pytest -q server/tests/test_songcue_ladder.py server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_fixture.py server/tests/test_songcue_report.py server/tests/test_song_accent_ladder_t403.py server/tests/test_songcue_sections.py
........................................................................ [ 96%]
...                                                                      [100%]
75 passed in 0.72s
```

### 착수 후 전체 스위트 (기준선과 나란히)

```
$ uv run pytest -q
13689 passed, 35 skipped, 1 warning in 187.51s (0:03:07)
```

착수 전(`13685 passed, 35 skipped`) 대비 **회귀 0건**, 신규 통과 시험 net +4
(`TestEffectiveBlinderStillRotatesAndReachesTheConsole` 1, `TestLabelWithoutSixRowExcludesBlinderEvenWithAGroup`
1, `TestZoomOnlyLookExcludesIrisFromRotation` 1, `TestHeadroomCaseIsUntouched::test_at_least_one_repeat_occurrence_is_withheld`
1 — 나머지는 기존 시험의 이름 변경/본문 갱신으로 개수가 그대로다).

### 린트/포맷

```
$ uv run ruff check server/looks/songcue.py server/tests/test_songcue_ladder.py server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_fixture.py
All checks passed!
$ uv run ruff format --check server/looks/songcue.py server/tests/test_songcue_ladder.py server/tests/test_songcue_accent_ladder_t382.py server/tests/test_songcue_chorus_rescue.py server/tests/test_songcue_accent_fixture.py
5 files already formatted
```

### subagent-boundary grep (회귀 확인)

```
$ grep -rn "AskUserQuestion" server/looks/ | grep -v "_test.go" | grep -v "// "
(출력 없음 — 0건)
```

### REQ PASS/FAIL 표

| REQ | 판정 | 판정 명령/근거 |
|---|---|---|
| REQ-LDACCENT-001 | PASS | `_accent_is_effective`(축 보유·그룹 보유·§6 행 보유 AND) — `TestEffectiveBlinderStillRotatesAndReachesTheConsole` + `TestZoomOnlyLookExcludesIrisFromRotation` |
| REQ-LDACCENT-002 | PASS | `TestZoomOnlyLookExcludesIrisFromRotation::test_iris_and_blinder_never_appear_only_zoom_rotates` — `iris_pinch` 축 부재 시 후보 제외 |
| REQ-LDACCENT-003 | PASS | `TestLabelWithoutSixRowExcludesBlinderEvenWithAGroup` — 그룹 있어도 라벨 §6 행 없으면 제외(AND) |
| REQ-LDACCENT-004 | PASS | `test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking` — 4회차가 blinder 대신 iris 로, 5회차가 zoom 으로 넘어간다(같은 회전 순서 유지, 포기 없음) |
| REQ-LDACCENT-005 | PASS | `TestHeadroomCaseIsUntouched::test_at_least_one_repeat_occurrence_is_withheld`, `TestEveryRepeatOccurrenceCarriesOneAccent`(전량 유보), `TestTheChorusRescueGeneralizesBeyondDrop`(4회차 충돌 소진도 유보) |
| REQ-LDACCENT-006 | PASS | `_collect_withheld_accents` + `SongCueBundle.withheld_accents`/`SongCueSectionBundle.accent_withheld` — 위 시험들이 두 층위 모두 단언 |
| REQ-LDACCENT-007 | PASS | `TestAccentGroupAbsentMeansNoConsoleCommand::test_no_blind_group_in_the_rig_means_the_ladder_never_names_it` — 무영향 칸이 `.ladder`에 없음. 명시적 예외(D2, `_unique_floor_climb` 소진)는 비목표로 남김(변경 없음) |
| REQ-LDACCENT-008 | PASS | 기존 `TestOneMarkingAccentPerCue` 전량 + `_marking_count(ladder) <= 1` 불변식 유지(회귀 없음) |

### AC PASS/FAIL 표

| AC | 판정 | 판정 명령 |
|---|---|---|
| AC-LDACCENT-001 | PASS | `TestHeadroomCaseIsUntouched` (두 시험) |
| AC-LDACCENT-002 | PASS | `test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking` |
| AC-LDACCENT-003 | PASS | `TestEffectiveBlinderStillRotatesAndReachesTheConsole` |
| AC-LDACCENT-004 | PASS | `TestHeadroomCaseIsUntouched::test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after`(Dimmer 20/25/30/35/40/45/50 바이트 동일 재확인) |
| AC-LDACCENT-005 | PASS | `TestOneMarkingAccentPerCue`(4개 시나리오 전량 회귀 통과) |
| AC-LDACCENT-006 | PASS | `TestLabelWithoutSixRowExcludesBlinderEvenWithAGroup` |

### §D 제약 준수 확인

- `TestOneMarkingAccentPerCue`/`TestHeadroomCaseIsUntouched` 두 시험의 **의도**(하나뿐인
  액센트 불변식, 밝기 값 바이트 동일성) 유지 — `expected_ladders`/개별 `.ladder` 리터럴만
  구체 픽스처에 한해 갱신(spec.md §2 허용 범위 그대로).
- `server/looks/songcue.py` 밖(라이브러리 룩 YAML·`resolver.py`·`section_intent.py`)은
  읽기만 했고 수정하지 않음 — `grep`으로 diff 대상 파일 목록을 재확인(§E.2 상단 "변경
  파일" 목록이 diff 전체와 일치).
- `{}` 매핑 리터럴 신규 추가 없음 — `_MARKING_ACCENT_AXIS`도 `dict(...)` 함수 호출
  형태(`_ACCENT_FIXTURE_ROLE` 관행 그대로), AST 가드 시험 재통과로 확인.
- `server/safety/`, `server/bridge/`(콘솔 전송 경로) 미변경.

### 편차(plan.md 대비)

- REQ-LDACCENT-005 의 유보 트리거를 plan.md M1 이 명시한 "유효 집합이 애초에 비어
  있는" 경우보다 **한 겹 넓혔다** — `_ensure_marking_accent`의 회전 루프가 유효
  후보를 전부 시도했는데도(각각 이미 나간 값과 겹쳐) 착지하지 못하면(`test_worship_four_chorus_repeats_all_survive_on_the_real_library`
  의 4회차가 실측 사례) 그때도 유보로 기록한다. 근거: REQ-LDACCENT-005 원문
  "REQ-004의 탐색을 다 거쳐도... 유효한 후보가 하나도 남지 않으면"은 탐색 자체의
  소진을 가리키지 애초의 공집합만 가리키지 않는다 — 이 갈래를 셀 이름 없이 조용히
  넘기면(고치기 전 블라인더가 항상 값-불변 안전판으로 막아 주던 자리가 이제 없으므로)
  REQ-007이 금지하는 "확인 안 된 채 남는 칸"은 아니지만 REQ-005가 요구하는 "빈 칸으로
  조용히 넘어가지 않는다"를 어길 뻔한 자리였다. `_no_effective_candidate_detail`이
  두 갈래(공집합/충돌 소진)를 구분해 detail 문면에 정확히 적는다. spec.md §4의
  `_unique_floor_climb` 소진(D2) 명시적 예외와는 다른 층(그건 블라인더/스트로브
  **밝기** 자체가 못 정해지는 경우, 이건 룩 **값 라인**이 겹치는 경우)이라 그 비목표
  범위를 침범하지 않는다.
- plan.md M5가 이름 붙이지 않은 두 시험(`TestEveryRepeatOccurrenceCarriesOneAccent`,
  `TestAccentGroupAbsentMeansNoConsoleCommand`)도 같은 단일-축·FULL_RIG 시나리오라
  SPEC 의도상 함께 갱신이 필요해 M5 범위로 편입했다 — plan.md가 명시한
  `TestHeadroomCaseIsUntouched`/`test_the_fourth_occurrence_swaps...` 두 자리와
  동일한 근본 원인(무영향 칸 필터링)이므로 별도 SPEC 분리 없이 이 SPEC 안에서
  처리했다.

## §E.3 Run-phase Audit-Ready Signal

- run_status: complete
- run_complete_at: 2026-09-20
- ac_pass_count: 6
- ac_fail_count: 0
- preserve_list_post_run_count: 0 (§D PRESERVE 대상인 `server/safety/`·`server/bridge/`·라이브러리 룩 YAML·`resolver.py`·`section_intent.py` 전부 미변경 확인)
- total_run_phase_files: 5 (`server/looks/songcue.py` + 4개 시험 파일)
- m1_to_mN_commit_strategy: 단일 커밋(Tier M, 파일 5개·마일스톤 6개 — 상호 의존성이 높아 분할 시 중간 커밋이 컴파일은 되어도 시험이 일관되게 통과하지 않음)

## §E.4 Sync-phase Audit-Ready Signal

- sync_complete_at: 2026-09-20
- sync_commit_sha: pending-backfill-LDACCENT-001-sync (다음 커밋에서 실제 SHA 백필)
- sync_status: complete
- b12_self_test_a: PASS — `grep -c 'SPEC-LDACCENT-001' CHANGELOG.md` → 사전 조회 0건, 본 sync 커밋에서 최초 삽입
- b12_self_test_b: PASS — `acceptance.md` 고유 AC-LDACCENT-ID 6개(`grep -oE 'AC-LDACCENT-[0-9]+' acceptance.md | sort -u | wc -l` → 6), CHANGELOG 항목이 AC-LDACCENT-001~006 전부 인용
- b12_self_test_c: PASS — CHANGELOG가 인용한 파일 경로(`server/looks/songcue.py`) `ls` 로 존재 확인
- changelog_entry_position: `[Unreleased]` 섹션 신규 `### Fixed` 서브섹션(기존 `### Changed`/`### Added` 위)
- frontmatter_status_transitions.spec_md: draft → completed (본 커밋)
- frontmatter_status_transitions.plan_md: n/a — plan.md/acceptance.md/progress.md는 frontmatter 블록이 없음(spec.md만 canonical 12필드 frontmatter를 가짐, `spec-frontmatter-schema.md` 확인)
- canary_compliance_check: n/a — 이 SPEC은 forward-looking policy를 정의하지 않음
