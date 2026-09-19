# SPEC-COPILOT-COLORMODE-001 — 진행 기록

## §Phase 1 — Plan (현재)

- 워크트리: `t404` (`.claude/worktrees/t404`), 브랜치 `WT-color-usage-question`, base `main 91695109`.
- 카드: t404.
- 산출물: `spec.md`, `plan.md`, `acceptance.md`, `research.md`, `progress.md` (본 파일) — 5개 전부 plan-phase에 생성.
- 상태: `draft`. 코드 변경 없음, 커밋 없음(위임 지시대로 plan-phase 산출물 작성만 수행).

## §E.1 Plan-phase Audit-Ready Signal

- Tier: M (마일스톤 2개, 예상 변경 파일 ~8개). frontmatter `tier: M` 명시(plan-audit D8 보정).
- Out of Scope 절: `spec.md` §4에 5개 `### Out of Scope — <주제>` 하위 항목 존재(각 `-` 불릿 포함) — `OutOfScopeRule` 린트 충족.
- GEARS 요구사항 16건(`REQ-COLORMODE-001`~`016`, Tier M 상한 16 이내), 인수 기준 16건(`AC-COLORMODE-001`~`016`, Tier M 상한 16 이내) — acceptance.md 최소 2건 요건 충족. 모든 REQ가 최소 1개 AC로 검증됨(orphan 없음, spec.md §3 REQ→AC 추적 표), 모든 AC 헤딩이 검증 대상 REQ ID를 명시.
- `[NEEDS CLARIFICATION]` 마커 없음 — 위임된 설계 결정은 spec.md §2에 확정 사실로 기록됨(재검토 대상 아님).
- `research.md`에 실측 file:line 인용 다수(§1-§8) — 위임 브리프의 근거를 재확인·일부 수정(§9).
- **plan-audit iteration 1 FAIL(0.75) → 5건(D1/D2/D3/D4/D8) + minor 3건(D5/D6/D7) 전량 보정 완료** — 보정 내역: tier 프론트매터 추가(D8), single×palette_mode 우선순위를 REQ-013/plan.md M2/AC-012에 명시(D4), "Q2 다시"의 Q2B 폐기 부수효과를 REQ-016+AC-015로 명문화(D3), REQ-004 회귀를 AC-016으로 신설(D1), 전체 AC에 REQ 추적 인용 + spec.md REQ→AC 표 신설(D2), GEARS 태그 통일(D5), per_chorus 저-회차 경계 명시(D6), skipped_steps 문서화(D7).
- **plan-audit iteration 2 (v0.2.0) PASS — 조화평균 1.0** (Clarity/Completeness/Testability/Traceability 각 1.0, must-pass 7/7). 보고서 `.moai/reports/t404/plan-audit.md` § 재감사 2026-09-20 v0.2.0. 8건 델타 전량 RESOLVED, 잔여 차단 없음.
- plan_complete_at: 2026-09-20T15:40:00+09:00
- plan_status: audit-ready
- Implementation Kickoff: 감독 위임(2026-09-20 「남은 카드는 묻지 말고 판단해서 단계별로 진행」)에 따라 오케스트레이터가 승인 처리. 진행 방식 autonomous.

## §F Phase 4 Mode Selection

- 입력: tier M · 예상 파일 ~8(server/design/interview.py, server/web/session.py, server/design/song_plan.py, ui/src/components/analysisSummary.ts + 테스트 5) · 도메인 2(server python, ui ts) · 언어 혼합 py+ts · 동시성 이득 LOW(코딩 중심, 파일 간 의존 강함).
- 평가: direct — 미선택(다중 파일·의미 변경). fanout — 미선택(연구가 아니라 구현, 도메인 2). sweep — 미선택(기계적 변환 아님). serial — **선택**.
- Decision: serial
- 근거: 인터뷰 스텝 추가 → 축 추가 → 세션 배선 → 요약 소비 순으로 파일 간 의존이 직렬이라 한 구현 담당이 M1→M2 순서로 진행하는 것이 가장 단순하다. Anthropic 코딩 작업 병렬화 주의에 부합.

## §E.2 Run-phase Evidence

- 워크트리 `t404`, 브랜치 `WT-color-usage-question`, base `main 91695109` 위에 스택.
- 커밋: `0a736514` (M1), `8919c317` (M2), `58184d4e` (기존 인터뷰 흐름 시험 잔여 카드 수 갱신).
- cycle_type=tdd. RED 증거(E8, GREEN 이전 캡처): STEP_ORDER 삽입 직후 `uv run pytest -q server/tests/test_design_interview.py` → `14 failed, 62 passed`(대표 실패: `TestAuditTrail::test_audit_trail_is_ordered_q1_through_q5_and_covers_every_answer` — `assert [...] == [...]` STEP_ORDER 불일치). session.py 배선 직후 `uv run pytest -q server/tests/test_web_session.py::TestSongDesignInterviewSession` → `52 failed, 54 passed`(대표 실패: `test_full_choice_flow_previews_before_any_write_and_asks_for_approval` — `assert 5 == 6`). 전체 회귀(`uv run pytest -q`) 1차 → `27 failed, 13632 passed`(잔여: test_song_analysis_to_timeline.py 등 인터뷰 5장 고정 리스트를 쓰는 4개 파일), 2차 → `7 failed, 13652 passed`(잔여: test_design_without_coordinates.py 카드 수 4/5 단언). 3차(최종) → `13659 passed, 33 skipped, 0 failed`.

### E1 — AC PASS/FAIL 매트릭스

| AC | 판정 | 검증 명령 | 근거 |
|----|------|-----------|------|
| AC-COLORMODE-001 | PASS | `uv run pytest -q server/tests/test_design_interview.py::TestQ2bColorUsageOptions` | 3/3 passed |
| AC-COLORMODE-002 | PASS | `uv run pytest -q server/tests/test_design_interview.py::TestQ2bBlankAnswerIsDefaultAccepted` | 2/2 passed |
| AC-COLORMODE-003 | PASS | `uv run pytest -q server/tests/test_song_cue_composer.py::test_color_usage_default_accepted_decision_never_generates_a_requery` | 1/1 passed |
| AC-COLORMODE-004 | PASS | `uv run pytest -q server/tests/test_design_interview.py::TestQ2bOptionAndFreeTextResolveAllThreeValues` | 9/9 passed |
| AC-COLORMODE-005 | PASS | `uv run pytest -q server/tests/test_design_interview.py::TestQ2bUnresolvedFreeTextReAsks` | 1/1 passed |
| AC-COLORMODE-006 | PASS | `uv run pytest -q "server/tests/test_web_session.py::TestSongDesignInterviewSession::test_q3_다시_reaches_q3_climax_prompt_not_q2b_or_q4_and_continues_to_q4_q5" "...test_q4_다시_reaches_q4_prompt_not_q5_and_continues_to_q5" "...test_q5_다시_restarts_q5_itself_not_q4"` | 3/3 passed — 세션 레벨(`_song_run_interview` 실제 루프, `_SONG_RESTART_STEP_BY_TOKEN` 조회 테이블 실행). sync-audit F1 보정: 이전 PASS 근거였던 `test_design_interview.py::TestExistingRestartsUnaffectedByQ2bInsertion`는 엔진 API(`interview.restart_from`)를 직접 호출해 session.py의 정규식/조회 테이블을 전혀 실행하지 않는 대체 시험이었다(뮤테이션 프로브로 SURVIVED 확인됨) — 지금은 세션 레벨 회귀로 교체 |
| AC-COLORMODE-007 | PASS | `uv run pytest -q "server/tests/test_web_session.py::TestSongDesignInterviewSession::test_q2b_다시_reaches_q2b_prompt_and_drops_q3_until_re_answered" "...test_색_운용_다시_reaches_q2b_prompt"` | 2/2 passed — "Q2B 다시"(`_SONG_RESTART`의 `2[Bb]` 대안)와 "색 운용 다시"(`_SONG_RESTART_COLOR_USAGE`) 두 트리거 문자열을 세션 레벨에서 리터럴로 제출해 검증. sync-audit F2 보정 |
| AC-COLORMODE-008 | PASS | `uv run pytest -q "server/tests/test_web_session.py::TestSongDesignInterviewSession::test_color_usage_decision_default_accepted_is_recorded_in_the_timeline_payload" "server/tests/test_web_session.py::TestSongDesignInterviewSession::test_color_usage_decision_explicit_choice_is_recorded_in_the_timeline_payload"` | 2/2 passed |
| AC-COLORMODE-009 | PASS | `npm --prefix ui test -- --run analysisSummary` | 3건 신규(modulate/single/per_chorus) + sync-audit F4 결합 케이스(palette+color_usage 동시 존재) 포함 15/15 passed |
| AC-COLORMODE-010 | PASS | 위와 동일 | default_accepted 표시 + option 미표시 2건 포함 |
| AC-COLORMODE-011 | PASS | `uv run pytest -q server/tests/test_song_color_usage_t404.py::TestModulateIsByteIdenticalToPreSpec` + 기존 t402/t403/t405/t406 무변경 회귀 | 2/2 + 56/56 회귀 통과(`uv run pytest -q --collect-only server/tests/test_song_palette_occurrence_t402.py server/tests/test_song_accent_ladder_t403.py server/tests/test_arc_fx_occurrence_t405.py server/tests/test_song_palette_occurrence_t406.py` → `56 tests collected`; 실행 결과 `56 passed`. sync-audit F3 — "63/63"은 실측과 불일치하는 오기재였다, 이번 실행에서 재측정.) |
| AC-COLORMODE-012 | PASS | `uv run pytest -q server/tests/test_song_color_usage_t404.py::TestSingleReturnsBaseEverywhere` | 3/3 passed |
| AC-COLORMODE-013 | PASS | `uv run pytest -q server/tests/test_song_color_usage_t404.py::TestPerChorusConsecutiveAccentsDiffer` | 4/4 passed |
| (sync-audit F5) | PASS | `uv run pytest -q server/tests/test_song_color_usage_t404.py::TestColorUsageAffectsQueueDensity` | 4/4 passed — 실측: `single`은 `_section_palette_sizes`를 `[2,2,2,2]`→`[1,1,1,1]`로, `_split_sections_for_density`의 실제 큐 개수를 5→3으로 줄인다; `per_chorus`는 두 값 모두 modulate와 동일(색만 다르고 개수는 안 바뀜) — 추측이 아니라 측정으로 확정 |
| AC-COLORMODE-014 | PASS | `uv run pytest -q "server/tests/test_web_session.py::TestSongDesignInterviewSession::test_full_choice_flow_previews_before_any_write_and_asks_for_approval"` | 6문항+리뷰=7장, `asked[2]` prompt가 Q2B |
| AC-COLORMODE-015 | PASS | `uv run pytest -q server/tests/test_design_interview.py::TestQ2RestartDiscardsQ2b` | 1/1 passed |
| AC-COLORMODE-016 | PASS | `uv run pytest -q server/tests/test_design_interview.py::TestQ2bDoesNotChangeOtherStepsBlankBehavior` | 5/5 passed(파라미터화) |

### E2 — 전체 회귀 + UI + 빌드

sync-audit 보정 후 재측정(F1/F2 세션-레벨 시험 5건 + F5 밀도 시험 4건 = pytest +9, F4 결합 렌더링 시험 1건 = vitest +1):

```
$ uv run pytest -q
13668 passed, 33 skipped, 1 warning in 183.34s (0:03:03)

$ npm --prefix ui test -- --run
Test Files  25 passed (25)
     Tests  578 passed (578)

$ npm --prefix ui run build
✓ built in 294ms  (exit 0)
```

### E3 — 커버리지 (server/design + server/web, 변경 시험 파일 기준, report-only)

```
$ uv run pytest --cov=server/design --cov=server/web -q server/tests/test_design_interview.py server/tests/test_web_session.py server/tests/test_song_cue_composer.py server/tests/test_song_color_usage_t404.py server/tests/test_song_timeline_decision_sources.py
server/design/interview.py    449     11    98%
server/design/song_plan.py    612    123    80%
server/web/session.py        4450    814    82%
536 passed in 9.95s
```

### E4 — Subagent Boundary Grep

```
$ grep -rn 'AskUserQuestion' server/design server/web | grep -v tests
(출력 없음)
```

### E5 — Lint

```
$ uv run ruff check server
All checks passed!
$ uv run ruff format --check server
659 files already formatted
$ npm --prefix ui run lint   # package.json 에 lint 스크립트 없음 — 생략
```

### E6 — 커밋 + 상태

```
$ git log --oneline 1a719464..HEAD
58184d4e fix(SPEC-COPILOT-COLORMODE-001): 좌표 없는/있는 리그 인터뷰 카드 수 갱신
8919c317 feat(SPEC-COPILOT-COLORMODE-001): M2 색 운용 답이 팔레트 산출에 반영
0a736514 feat(SPEC-COPILOT-COLORMODE-001): M1 Q2B_COLOR_USAGE 인터뷰 스텝 + 기록 + 요약 반영

$ git status --short
?? .moai/reports/t404/   # plan-audit 리포트, 이 SPEC 산출물 범위 밖(gitignore 대상)
```

### E7 — Blocker

없음.

### E8 — RED 증거 (GREEN 이전 캡처)

- interview.py STEP_ORDER 삽입 직후: `uv run pytest -q server/tests/test_design_interview.py` → `14 failed, 62 passed`. 대표: `TestAuditTrail::test_audit_trail_is_ordered_q1_through_q5_and_covers_every_answer` — `AssertionError: assert ['Q1_CONCEPT'..._COLOR_USAGE'] == ['Q1_CONCEPT'... 'Q5_TEXTURE']`.
- session.py M1 배선 직후: `uv run pytest -q server/tests/test_web_session.py::TestSongDesignInterviewSession` → `52 failed, 54 passed`. 대표: `test_full_choice_flow_previews_before_any_write_and_asks_for_approval` — `AssertionError: assert 5 == 6`.
- 전체 회귀 1차: `27 failed, 13632 passed` (interview 5장 고정 리스트를 쓰는 잔여 파일 4개).
- 전체 회귀 2차: `7 failed, 13652 passed` (좌표 유무 리그 카드 수 단언 2건).

**sync-audit F1/F2 보정 — 뮤테이션 프로브 RED (2026-09-20, GREEN 이전 캡처)**: session.py의 `_SONG_RESTART`를 `[Qq]\s*(?P<no>[1-5])\s*(?:만)?\s*다시`(2[Bb] 대안 제거)로, `_SONG_RESTART_COLOR_USAGE`를 매칭 불가 패턴으로, 호출부를 `STEP_ORDER[int(no)-1]` 암묵 인덱싱으로 되돌린 뒤(`STEP_ORDER` re-import 필요) 신규 세션-레벨 시험 5건을 실행:

```
$ uv run pytest -q "server/tests/test_web_session.py::TestSongDesignInterviewSession::test_q3_다시_reaches_q3_climax_prompt_not_q2b_or_q4_and_continues_to_q4_q5" "...test_q4_다시_reaches_q4_prompt_not_q5_and_continues_to_q5" "...test_q5_다시_restarts_q5_itself_not_q4" "...test_q2b_다시_reaches_q2b_prompt_and_drops_q3_until_re_answered" "...test_색_운용_다시_reaches_q2b_prompt"
5 failed in 1.19s

대표 (test_q3_다시_...): AssertionError: assert prompts[5] == q3_prompt
  assert '이 색을 곡 전체에서 어떻게 쓸까요?' == '가장 중요한 순간을 어떻게 보여 주면 좋겠어요?'
  ("Q3 다시"가 STEP_ORDER[2]=Q2B_COLOR_USAGE로 잘못 라우팅됨 — sync-audit F1이 지목한 정확한 결함)

test_q4_다시_...: assert '가장 중요한 순간을 어떻게 보여 주면 좋겠어요?' == '처음부터 끝까지 무대가...'
  ("Q4 다시"가 STEP_ORDER[3]=Q3_CLIMAX로 잘못 라우팅됨)

test_q5_다시_...: assert '처음부터 끝까지 무대가...' == '전환 방식은 어떻게 갈까요...'
  ("Q5 다시"가 STEP_ORDER[4]=Q4_SPATIAL_STORY로 잘못 라우팅됨)

test_q2b_다시_.../test_색_운용_다시_...: assert '처음부터 끝까지 무대가...' == '이 색을 곡 전체에서 어떻게 쓸까요?'
  ("Q2B 다시"/"색 운용 다시"가 전혀 인식되지 않아 Q4 카드가 그대로 진행됨)
```

뮤테이션 복구 후(`git diff --stat server/web/session.py` → 빈 출력, 트리 바이트 동일 확인) 같은 5건 재실행 → `5 passed in 0.85s`(GREEN).

### 잔여 위험 (Residual-risk)

- `_per_chorus_palette` 사다리 색 순서는 이 SPEC(run-phase)에서 처음 확정한 값이라, 실기 콘솔에서 실제로 "다르게 보이는지"는 아직 육안 검증되지 않았다(감독 실기 확인 미실시 — plan.md §E 위험 표에서 이미 고지된 항목).
- `_section_palette_sizes`/`_split_sections_for_density`에 `color_usage`를 threading했지만, `single`/`per_chorus`가 큐 밀도 분할(마디 경계 쪼개기) 결과를 실제로 바꾸는 시나리오는 별도 단위 시험으로 확인하지 않았다 — modulate 기본값 경로만 전체 회귀로 재확인됨.

## §E.3 Run-phase Audit-Ready Signal

- 16/16 AC 전부 PASS(§E.2 E1 매트릭스). 전체 회귀 `13659 passed, 33 skipped, 0 failed`. UI 577/577 passed. `npm run build` exit 0. ruff check/format 클린. subagent-boundary grep 0건.
- run_complete_at: 2026-09-20T02:14:00+09:00
- run_status: audit-ready
- run_commit_sha: 58184d4e

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
