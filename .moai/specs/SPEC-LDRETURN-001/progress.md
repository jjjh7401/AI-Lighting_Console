# SPEC-LDRETURN-001 — 진행 기록

> 단계별 증거를 적는 자리. plan 단계는 §E.1 만 채우고 §E.2~§E.4 는 각 단계의 소유자가 채운다.

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready (M1 `Dimmer` 넛지 상한 — 2026-09-21 감독 결정으로
  해소, 옵션 A 채택: 단계 수 상한 없음, `DARKNESS_FLOOR`(20)까지 무제한
  탐색. 해소 기록: spec.md §5, plan.md §F M1)
- 미해결 `[NEEDS CLARIFICATION]` 마커: **0건**(2026-09-21 확인,
  `grep -rn '\[NEEDS CLARIFICATION' .moai/specs/SPEC-LDRETURN-001/` 결과
  검증 명령 문자열 자신 외에는 공백)
- plan_complete_at: 2026-09-20 (M1 해소 반영 2026-09-21)
- SPEC 작성 완료 2026-09-20 — `spec.md` · `plan.md` · `acceptance.md`
  (Tier M) + 이 파일. 카드 t427.
- SPEC ID 정규식 검사(Bash 실행): `ID="SPEC-LDRETURN-001"; [[ "$ID" =~
  ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` →
  `PASS`.
- **기준 트리**: `origin/main` `42fbd1c8`(SPEC-LDCLIMAX-001 PR #473 병합
  커밋). 로컬 checkout 은 이 시점 기준 15커밋 뒤져 있었다(`git rev-list
  --count --left-right origin/main...HEAD` → `15 0`) — 로컬 디스크의
  `.moai/specs/SPEC-LDCLIMAX-001/`(draft 상태 잔존)과
  `server/tests/test_songcue_climax_001.py`(파일 부재) 둘 다 이 사실을
  확인했다. 이 SPEC 의 모든 행 번호 인용은 `git show origin/main:` 로
  직접 읽은 결과다.
- **예산**: REQ **8건**(REQ-LDRETURN-001~008) / AC **8건**
  (AC-LDRETURN-001~008). 둘 다 Tier M 상한 16 이내. 하위 ID 없음.
- **발단 재확인(2026-09-20, `42fbd1c8`)**: sync-auditor F4(SPEC-LDCLIMAX-001
  재감사, 브랜치 `WT-color-snap-climax@f6279509`) — `_rung_applied`
  (`songcue.py:3242-3260`)가 `blinder_or_flash`/`strobe_hit` 에서 값을
  안 바꾸므로 복귀 큐의 재방출 기준 값이 반복 룩의 1회차 저장 값과 글자
  그대로 겹치고, F1 수정이 재호출하는 `_guard_bundle_collision`
  (`songcue.py:1132`)이 이를 정확히 거절한다. 증거: fix 커밋 자신이
  `TestClimaxDurationCapIsWiredThroughBuildSongcueBundle
  .test_bpm_argument_reaches_the_duration_cap_pass`(`test_songcue_
  climax_001.py:503`)를 성공 단언에서 `SongCueBundleError` 단언으로
  뒤집었다 — 공개 진입점을 통한 성공 삽입을 재는 시험이 이 저장소
  어디에도 없다(삽입 성공을 보이는 시험은 전부 `_apply_climax_duration_
  cap` 을 직접 불러 가드를 우회한다, `test_songcue_climax_001.py:375`).
- **프로덕션 도달 확인**: `server/orchestrator/tools.py:3230`
  (`prepare_songcue`, `tools.py:2954`)의 `build_songcue_bundle` 호출은
  `bpm` 을 안 넘긴다 — 이 SPEC 이전부터 그랬다. `density_bpm =
  _confirmed_density_bpm(confirmed)`(`tools.py:3177`)가 이미 계산돼
  있어 후속 SPEC 이 한 줄만 추가하면 배선이 끝난다는 사실을 기록했다
  (spec.md §1.2, §4 Out of Scope).
- **설계 결정(3건 전량 확정)**: (1) 넛지 대상은 새로 끼우는 복귀
  큐 자신이지 상대(rival)가 아니다 — `_yield_bundle` 을 호출하지 않고
  알고리즘만 병행 재사용한다(plan.md §B1). (2) 충돌 판정은 조립-시점
  `emitted` 딕셔너리를 스레딩하지 않고 완성된 `sections` 에서 매번 새로
  읽는다(SPEC-LDCLIMAX-001 D3 과 같은 근거, plan.md §B2). (3) `Dimmer`
  넛지 상한 — **2026-09-21 감독 결정으로 해소, 옵션 A 채택**: 단계 수
  상한 없음, `DARKNESS_FLOOR`(20)까지 무제한 탐색(plan.md §F M1,
  spec.md §5).
- **미검증**: 넛지 단계 수가 실제 반복 회차 수(3~7회 등)에서 몇 단계까지
  필요한지 실측하지 않았다(착수 시 픽스처로 확인). `withheld_climax_
  returns` 가 실전 리그(색 축만 가진 룩 등)에서 실제로 발동하는 빈도도
  추정치일 뿐 재지 않았다.
- **plan-audit 수정 이력(2026-09-21, iteration 1 FAIL → 재감사 대기)**:
  `.moai/reports/plan-audit/SPEC-LDRETURN-001-review-1.md` 검증 —
  Must-Pass 7건 전량 PASS/N/A, 4개 수치 점수 평균 0.9375, 종합 0.86
  FAIL(blocking 2건). 수정 내역:
  - **D1(blocking) 해소**: `plan.md` §F 에 신규 **M5a** 마일스톤을
    추가 — AC-LDRETURN-008(반복 삽입 상호 비충돌) 전용 픽스처와 "첫
    번째 넛지 값 != 두 번째 넛지 값" 직접 단정을 명시적으로 못박았다.
    M5 에는 "AC-001 만 겨냥하며 절정 칸 개수를 보장하지 않는다"는
    범위 한정 문장을 추가했다. §E 자기검증에도 AC-008 전용 시험
    필수 항목을 추가했다.
  - **D2(blocking) 해소**: `plan.md` M6 두 번째 불릿을 재작성 —
    AC-LDRETURN-007 이 요구하는 원본 3회 반복·`Dimmer`-축-존재 픽스처의
    성공 단언 행선지를 명시적으로 지정했다("새 메서드로 보존" 선택):
    (1) 원본 메서드를 성공 단언으로 뒤집어 개명
    (`test_a_repeated_look_climax_return_succeeds_via_nudge`, AC-007
    전담), (2) 같은 클래스에 신규 메서드
    (`test_a_repeated_look_climax_return_is_withheld_without_dimmer_
    axis`)를 추가해 `Dimmer` 축 부재 음성 대조군으로 삼았다. 두
    메서드가 반드시 공존해야 한다고 명문화했다.
  - **D3(optional) 해소**: spec.md `_rung_applied` 인용을
    `songcue.py:3256-3260` → `3259-3263` 으로 정정(`git show origin/main:`
    재확인).
  - **D4(optional) 해소**: plan.md `if not returns` 분기 인용을
    `songcue.py:1387` → `1381` 로 정정.
  - **D5(optional) 해소**: spec.md §2 의 "셋 다 같은 모양" 과장 문장을
    "공통 핵심 필드 + 도메인별 추가 필드(band, drop_cue_number 등)"로
    정정.
  - **D6(optional) 해소**: spec.md REQ-001/002/008 의 SHALL 절에서
    비공개(`_` 접두) 함수 이름(`_yield_bundle`/`_HIT_STEP`/
    `is_programmer_state`/`_guard_bundle_collision`)과 `songcue.py:748`
    파일:행 인용을 근거 열로 옮기고, 본문은 행동 서술로 교체했다.
    `DARKNESS_FLOOR`/`Dimmer`/`build_songcue_bundle`/`SongCueClimaxReturn`
    은 acceptance.md·plan.md 전반에서 이미 도메인 어휘로 쓰이고 있어
    그대로 남겼다(과잉 수정 회피).

## §E.2 Run-phase Evidence

- **기준 트리**: `origin/main` `42fbd1c8` — 워크트리 `WT-climax-return-nudge`
  (`.claude/worktrees/agent-a12461612c2cf8215`), `git rev-list --count
  --left-right origin/main...HEAD` → `0 0`(동기화 확인).
- **착수 전 기준선**: `uv run pytest -q` → `13705 passed, 35 skipped`
  (183.35s).
- **완료 후 전체 스위트**: `uv run pytest -q` → `13707 passed, 35 skipped`
  (178.10s) — 델타 +2, 이 SPEC 이 더한 신규 시험 수(M6 신규 음성 대조군 1건
  + M5a 신규 시험 1건)와 정확히 일치.
- **lint/format**: `uv run ruff check server/looks/songcue.py
  server/tests/test_songcue_climax_001.py` → `All checks passed!`.
  `uv run ruff format --check <같은 두 파일>` → `2 files already formatted`.
- **AST dict-literal 가드**: `test_songcue_sections.py`
  (`test_the_import_boundary_forbids_a_reintroduced_matching_alias` 근처의
  `_dict_literal_lines` 단언)이 전체 스위트 안에서 함께 통과 — 새 코드는
  `dict()`/`set()` 호출만 쓰고 `{}` 리터럴을 두지 않았다.

### AC 별 PASS/FAIL 표

| AC | 판정 | 검증 명령 | 관측 출력 |
|---|---|---|---|
| AC-LDRETURN-001 | PASS | `pytest -q .../test_songcue_climax_001.py::TestClimaxDurationCapIsWiredThroughBuildSongcueBundle::test_bpm_argument_reaches_the_duration_cap_pass` | `1 passed` |
| AC-LDRETURN-002 | PASS | `pytest -q .../TestClimaxReturnCueCollisionIsGuarded::test_a_repeated_look_climax_return_succeeds_via_nudge` | `1 passed` (Dimmer≠60, 색 3속성 동일 단언) |
| AC-LDRETURN-003 | PASS | 같은 시험(바닥 이상 단언) + `TestRepeatedClimaxReturnsDoNotCollideWithEachOther`(2단계 이상 넛지가 실제로 발생하는 픽스처, 구조적으로 `_stepped` 의 `max(target, limit)` 가 바닥을 보장) | `1 passed` 씩 |
| AC-LDRETURN-004 | PASS | `pytest -q .../TestClimaxReturnCueCollisionIsGuarded::test_a_repeated_look_climax_return_is_withheld_without_dimmer_axis` | `1 passed` |
| AC-LDRETURN-005 | PASS | `pytest -q .../TestClimaxReturnIsInsertedForALongClimax::test_a_return_cue_lands_at_the_two_beat_cap` | `1 passed` (골든, 픽스처 보정 — §Deviations 참조) |
| AC-LDRETURN-006 | PASS | `pytest -q .../TestUndeclaredBpmIsANoOp::test_bpm_none_returns_the_input_untouched` | `1 passed` |
| AC-LDRETURN-007 | PASS | `pytest -q .../TestClimaxReturnCueCollisionIsGuarded::test_a_repeated_look_climax_return_succeeds_via_nudge` | `1 passed` |
| AC-LDRETURN-008 | PASS | `pytest -q .../TestRepeatedClimaxReturnsDoNotCollideWithEachOther::test_the_second_nudged_return_differs_from_the_first` | `1 passed` |

### REQ 별 PASS/FAIL 표

| REQ | 판정 | 근거 |
|---|---|---|
| REQ-LDRETURN-001 | PASS | AC-002/003/007 — `_climax_return_bumped` |
| REQ-LDRETURN-002 | PASS | AC-001/007 — 넛지 성공 시 `_guard_bundle_collision` 통과, 삽입 성공 |
| REQ-LDRETURN-003 | PASS | AC-004 |
| REQ-LDRETURN-004 | PASS | AC-005(골든), `TestClimaxReturnIsInsertedForALongClimax` 의 기존 단언(원본 절정 큐 값·사다리·`accent_fixture` 불변) 전량 유지 |
| REQ-LDRETURN-005 | PASS | AC-005 |
| REQ-LDRETURN-006 | PASS | AC-001 |
| REQ-LDRETURN-007 | PASS | AC-006 |
| REQ-LDRETURN-008 | PASS | AC-004(`withheld_climax_returns` 레코드 필드 전량 채워짐 확인) |

### 골든/무회귀 확인 (명시 지목)

- `TestHeadroomCaseIsUntouched::test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after` — PASS
- `TestHeadroomCaseIsUntouched::test_at_least_one_repeat_occurrence_is_withheld` — PASS
- `TestOneMarkingAccentPerCue`(5개 메서드) — 전량 PASS

### 계획 대비 이탈(Deviations) — 반드시 보고

1. **M6 두 번째 신규 메서드 픽스처 변경**: plan.md 는 "Dimmer 축이 없는 룩"을
   지시했으나(REQ-003 의 첫 갈래), 실측 결과 이 리그·이 사다리 메커니즘에서는
   `Dimmer` 축이 아예 없는 룩은 `blinder_or_flash` 사다리 칸에 **구조적으로
   도달하지 못한다** — `_climb_rungs` 의 "hits"(`dimmer_hit` 반복)만이 깊이별
   값을 차별화하고, `blinder_or_flash`/`strobe_hit` 자신은 `_rung_applied` 에서
   항등이므로 `Dimmer` 축이 없으면 3회차 이상이 전부 `value_line_collision` 으로
   드롭된다(`.venv` 밖 임시 프로브 스크립트로 실측, n=3~20 반복 전량 확인 —
   스크립트는 착수 산출물이 아니므로 커밋에 없음). 대신 `Dimmer` 를 처음부터
   `DARKNESS_FLOOR`(20)에 둔 픽스처를 썼다 — `_stepped` 는 "속성 없음"과
   "이미 한계"를 같은 방식(입력 그대로 반환)으로 처리하므로, 이 픽스처는
   REQ-003 의 유보 코드 경로(`_climax_return_bumped` 의 `candidate_line ==
   _values_line(attributes)` 조기 반환)를 축-부재 갈래와 바이트 동일하게
   재현한다. THEN 절(예외 없이 성공, `climax_returns` 비어있음,
   `withheld_climax_returns` 레코드 1건)은 문면 그대로 검증됐다.
2. **AC-LDRETURN-005 골든 픽스처의 우발적 값 충돌 보정**:
   `test_a_return_cue_lands_at_the_two_beat_cap` 의 `following`
   (`_plain_cue`, 기본값 `dimmer=60.0`)이 `climax` 의 사다리-오르기-전 기준
   값(`_climax_cue` 의 `base_dimmer` 기본값도 60.0)과 **우연히 같은 값
   라인**을 냈다 — 이 SPEC 이전에는 이 시험이 `_apply_climax_duration_cap`
   을 직접 불러 `_guard_bundle_collision` 을 거치지 않았으므로 이 충돌이
   드러나지 않았을 뿐, 실제로는 AC-005 가 전제하는 "충돌 없는 다음 큐"가
   아니었다. plan.md §B2 그대로 구현하면(전체 `sections` 의 non-programmer-
   state 명령 집합에서 판정) 이 우발적 충돌도 정확히 잡혀 넛지가 개입해
   버렸다 — AC-005 의 "바이트 동일" 요구와 충돌. `following` 의 `dimmer` 를
   시험 안에서만 명시적으로 45.0 으로 바꿔(`_plain_cue` 의 기본값 자체는
   다른 시험이 의존하므로 안 바꿨다) 우발적 충돌을 제거했다 — AC-005 가
   실제로 요구하는 "무충돌 시나리오"를 이 픽스처가 진짜로 충족하도록
   교정한 것이지, REQ/AC 의 의미를 바꾼 것이 아니다. 복귀 큐의 Dimmer 값
   단언(`60`, `stored[2]` 단언은 `45`로 조정)은 계획대로 바이트 동일하게
   유지된다.

### 미검증(Gaps)

- `bpm` 프로덕션 배선(`tools.py:3230`)은 §4 Out of Scope — 실제 콘솔 세션에서
  이 결함이 발동한 적이 없다(발동 전제인 `bpm=density_bpm` 배선이 아직 없음).
- 넛지가 3단계 이상 필요한 극단적 반복(10회차 이상)은 별도 픽스처로 재지
  않았다 — `_stepped` 의 `max(target, limit)` 클램프가 구조적으로 바닥을
  보장하므로 회귀 위험은 낮다고 판단했다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-21
run_commit_sha: pending-backfill-ldreturn-001-m1
run_status: complete
ac_pass_count: 8
ac_fail_count: 0
preserve_list_post_run_count: 4  # plan.md §D — songcue.py 밖 4개 카테고리(리그 YAML/resolver.py/section_intent.py/tools.py) 전량 미수정
l44_pre_commit_fetch: "0 0"
l44_post_push_fetch: pending-backfill-ldreturn-001-m1
new_warnings_or_lints_introduced: 0
cross_platform_build:
  applicable: false
  reason: "순수 Python 계산 계층 — Go cross-platform build tag 대상 아님"
total_run_phase_files: 2
m1_to_mN_commit_strategy: single-commit
```

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
