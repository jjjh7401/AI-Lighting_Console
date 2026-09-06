# SPEC-COPILOT-SONGCONFIRM-001 — 진행 기록

> 단계별 증거를 적는 자리. plan 단계는 §E.1 만 채우고 §E.2~§E.4 는 각 단계의 소유자가 채운다.

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-09-06
- plan-audit: 1차 FAIL 0.80 → 2차 **PASS 0.96** (`.moai/reports/plan-audit/SPEC-COPILOT-SONGCONFIRM-001-review-{1,2}.md`); 잔여 N1·N2 를 0.1.2 로 반영. 워크트리 `t273`(브랜치 `WT-song-confirm`, base main `72e4ca6` — POOLEMPTY-001 plan 포함).

- SPEC 작성 완료 2026-09-06 — `spec.md` · `plan.md` · `acceptance.md` (Tier M) + 이 파일. 카드 t273.
- SPEC ID 정규식 검사(Bash 실행): `ID="SPEC-COPILOT-SONGCONFIRM-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS`.
- **기준 트리**: 워크트리 `.claude/worktrees/agent-ab693b5114839dea5`, `git rev-parse --short HEAD` → **`f727e11`**(= main, 실브라우저 보고서의 기준과 같은 커밋). 인용한 모든 행 번호는 이 HEAD 에서 되읽었다.
- **예산**: REQ **16건**(REQ-SONGCONFIRM-001~016) / AC **16건**(AC-SONGCONFIRM-001~016). 둘 다 Tier M 상한 16 을 정확히 소진. 하위 ID 없음.
- **결함 재실측(2026-09-06, `f727e11`)**: ① `grep 'proposals|selected|sections' server/web/question.py` → 카드 빌더(`:139-215`)에만 등장, 파서 0건 ② `grep -rn '\.song_bpm\b\|_song_bpm' server --include='*.py' | grep -v /tests/` → `session.py:3781 · :10277 · :10293` 3행(초기화·대입·반환), 생산 판독자 0 ③ `prepare_songcue`(`tools.py:2550`)는 `call.arguments` 만 읽고, 스키마 `required`(`:9721`)에 `sections` 포함 ④ `build_timecode_handoff_card` 생산 호출자 0건(`grep -rn … | grep -v /tests/` → 정의 `question.py:231` 1행) ⑤ `analyse_song_audio` 는 `app.py:585` 가 `to_thread` 인자로 넘긴다(괄호 없는 참조라 `analyse_song_audio(` grep 은 0 이지만 생산 배선은 있다 — MUSICSYNC-001 §E.2 「M2 후속」과 일치).
- **통로 실측**: 세션→모델 `session.py:10399-10440` `_session_context_note` → `:10037` `handle_instruction(session_context=…)` → `runner.py:331-359`(`:357-358` 합성 `UserMessage`) · 세션→도구 `session.py:3795-3826` `build_toolset(… uploaded_sheet=_UploadedSheetView(self))` + `tools.py:1949-1971` 시그니처 + `:527-541` `UploadedSheetPort` + `:6405-6406` `None` 분기 + `:3591-3602` 읽기 투과 뷰 선례 · UI 답 형식 `ui/src/components/QuestionCard.tsx:17-24` `joinChosenLabels`(`", "` 결합) · `:167-170` 자유 입력.
- **하위 호환 실측**: 스키마 `required` 단언 시험 0건 · `'sections' must be` 리터럴 단언 시험 0건 · `_session_context_note() is None` 단언 `test_web_session.py:1013` · 미응답 갈래 `song_bpm.source == "default"` 단언 `test_web_song_audio.py:479-484`(D2 의 근거).
- **결정 6건 확정**(`plan.md §C` D1~D6): 라벨 왕복 대조 문법 · 불변 기록 + `_song_bpm` 무변경 · 재업로드 무효화 · `_session_context_note` 통로 · 명시 인자 우선 + 불일치 보고 + 스키마 `sections` 선택화 · 중립 이름 `S<n>` · `SongAnalysisPort` 읽기 투과 뷰. 결정 대기 **0건**.
- **선행 SPEC 대조**: MUSICSYNC-001(`status: completed`) 의 REQ-015(카드 스키마 무변경)·016(BPM→`MusicProfile`)·017(우선순위)은 재명세하지 않고 읽기만 한다. 그 SPEC 의 부채 2건(`HEAD.BPM` 접합 · 인계 카드 호출자)은 §D 범위 밖으로 명시.
- **미검증**: B1(중복 라벨의 실제 발생) · B2(`start_ms` 문자열 왕복 손실 0) · B3(`S<n>` 이 라이브러리 어휘 밖) · B7(제공자의 `required` 강제 여부) · B8(채택 구간 수 상한) — 전부 `plan.md §B`, 착수 시 재측정. 실브라우저 관측은 보고서 것이며 이 계획 회차가 다시 띄우지 않았다(콘솔 접촉 0).

## §E.2 Run-phase Evidence

> 실행 주체: manager-develop(`cycle_type=tdd`), 카드 t273. 워크트리 `.claude/worktrees/agent-a70e9596cb7f1b7e8`, 브랜치 `WT-song-confirm-run`. 모든 명령은 이 워크트리 루트에서 실행했고 출력은 그 실행에서 그대로 옮긴 것이다(잘라 낸 자리는 `…` 로 표시).

### 기준값 (BASE · 인터프리터)

- `git log --oneline -1` → `fc65860 feat(SPEC-COPILOT-SONGCONFIRM-001): 곡 분석 확정의 도달 — … (plan) (#319)`; `git rev-parse --short origin/main` → `fc65860`.
- **`BASE=$(git merge-base origin/main HEAD)` → `fc658606d91cbd61cdcf68b1c7d27b4b973eef4d`** (M1 착수 시 기록. 이하 모든 diff 술어의 기준).
- 인터프리터: `uv sync --python 3.11` 로 워크트리 안에 `.venv` 생성(exit=0). `.venv/bin/python --version` → `Python 3.11.15`; `.venv/bin/python -c "import sys; print(sys.executable)"` → `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/agent-a70e9596cb7f1b7e8/.venv/bin/python`; 하위 디렉터리(`server/`)에서 `import server; print(server.__file__)` → `…/agent-a70e9596cb7f1b7e8/server/__init__.py` (이 트리의 소스).
- 착수 전 기준 회귀(BASE 트리, 변경 0): `.venv/bin/python -m pytest server/tests/test_tree_identity.py server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py -q -p no:cacheprovider` → `528 passed, 1 warning in 32.35s`.

### AC-014 대조군 — BASE 트리에서 다섯 grep (변경 0 상태에서 실측)

```
$ grep -rn 'parse_confirmed_sections(' server --include='*.py' | grep -v /tests/ | grep -v 'def parse_confirmed_sections' | wc -l   → 0
$ grep -rn 'ConfirmedSongAnalysis(' server --include='*.py' | grep -v /tests/ | grep -v 'class ConfirmedSongAnalysis' | wc -l     → 0
$ grep -n 'song_analysis=' server/web/session.py | wc -l                                                                           → 0
$ grep -n 'song_analysis\.current' server/orchestrator/tools.py | grep -v ':[[:space:]]*#' | wc -l                                 → 0
$ grep -c 'song_analysis: SongAnalysisPort' server/orchestrator/tools.py                                                           → 0
$ grep -rn '\.song_bpm\b\|_song_bpm' server --include='*.py' | grep -v /tests/ | grep -v ':[[:space:]]*#' | grep -v 'self._song_bpm: BpmResolution' | grep -v 'self._song_bpm = resolution' | grep -v 'return self._song_bpm' | wc -l   → 0
```

### M1 — 판독과 기록 (AC-001 ~ 006)

**RED (구현 전, 시험 파일 작성 직후 — verbatim)**

```
$ .venv/bin/python -m pytest server/tests/test_song_confirm_sections.py -q -p no:cacheprovider
==================================== ERRORS ====================================
_________ ERROR collecting server/tests/test_song_confirm_sections.py __________
ImportError while importing test module '…/server/tests/test_song_confirm_sections.py'.
…
server/tests/test_song_confirm_sections.py:22: in <module>
    from server.web.question import (
E   ImportError: cannot import name 'parse_confirmed_sections' from 'server.web.question' (…/server/web/question.py)
=========================== short test summary info ============================
ERROR server/tests/test_song_confirm_sections.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.10s
```

**GREEN 1차 (구현 후)** — `1 failed, 107 passed`. 실패는 `test_a_label_is_matched_whole_not_as_a_prefix` 의 **시험 쪽 전제 단언** `assert labels[0] in labels[1]` 였다: 실측 `"1:00–1:15 · D1" in "11:00–11:15 · D1"` → `False`(끝 시각 `1:15` ≠ `11:15`). acceptance.md AC-005 (d) 괄호 문장(「앞 라벨이 뒤 라벨의 부분문자열이다 … 부분문자열 대조라면 2」)의 전제는 이 라벨 형식에서 성립하지 않는다 — 유효한 구간(start<end)의 어느 라벨도 다른 라벨의 부분문자열이 될 수 없다. AC 의 **관측 가능한 Then 절**(accepted 길이 1 · index 는 뒤 구간)은 그대로 통과하며, 완전 일치 ↔ 부분문자열을 실제로 가르는 대조군은 `test_a_label_inside_a_longer_item_is_not_a_match`(라벨이 더 긴 항목 안에 통째로 들어 있는 답 → 규칙 ② 전부 채택)로 추가했다. SPEC 본문은 손대지 않았다 — §E.2 끝의 「미검증·잔여 위험」에 적는다.

**GREEN (M1 게이트, acceptance.md §A M1 명령 — verbatim)**

```
$ .venv/bin/python -m pytest server/tests/test_song_confirm_sections.py server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py -q -p no:cacheprovider
109 passed, 1 warning in 2.08s
```

```
$ git diff --name-only fc658606d91cbd61cdcf68b1c7d27b4b973eef4d -- server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py
(출력 0행)
$ git diff --name-only fc658606d91cbd61cdcf68b1c7d27b4b973eef4d -- server/safety server/audio server/looks server/design ui/src src-tauri
(출력 0행)
$ .venv/bin/ruff check server/web/question.py server/web/session.py server/tests/test_song_confirm_sections.py
All checks passed!
$ .venv/bin/ruff format --check server/web/question.py server/web/session.py server/tests/test_song_confirm_sections.py
3 files already formatted
```

| AC | 상태 | 검증 명령 | 실제 출력 |
|---|---|---|---|
| AC-SONGCONFIRM-001 | PASS | `pytest server/tests/test_song_confirm_sections.py -q` (`TestAcceptingTheCardRecordsEverySection` 2건) | M1 게이트 `109 passed` 에 포함 |
| AC-SONGCONFIRM-002 | PASS | 같은 파일 `TestUncheckedSectionsAreDroppedButKept` | 위와 같음 |
| AC-SONGCONFIRM-003 | PASS | `TestATypedBpmKeepsTheCardSections` 2건(대조군 「두 번째는 빼 줘」 포함) | 위와 같음 |
| AC-SONGCONFIRM-004 | PASS | `TestNoAnswerMeansNoRecord` (`UNANSWERED` · `ANSWER_FREEFORM`) | 위와 같음 |
| AC-SONGCONFIRM-005 | PASS | 파서 `TestRuleTwoAcceptsEverythingWhenNoLabelIsPresent` (a)(b)(c)+양성 대조군 · `TestRuleOneKeepsOnlyTheLabelsPresent` (d) 접두 카드 · 세션 `TestLabelsAreMatchedWholeThroughTheSession` | 위와 같음 — (d) 전제 문장의 부정확은 위 GREEN 1차 참조 |
| AC-SONGCONFIRM-006 | PASS | `TestANewUploadInvalidatesTheRecord` 2건(첫 업로드 고지 문자열 동일 대조군 포함) | 위와 같음 |

M1 변경 파일: `server/web/question.py`(`section_label` · `ConfirmedSongSection` · `ConfirmedSongAnalysis` · `parse_confirmed_sections`; `QuestionRequest` 스키마 무변경, 카드 라벨 문자열 무변경) · `server/web/session.py`(`_song_analysis` 필드 · `analyse_song_audio` 기록 생성 · `upload_song_audio` 무효화+조건부 고지 · `song_analysis` 프로퍼티; `_song_bpm` 대입 무변경) · `server/tests/test_song_confirm_sections.py`(신규). `spec.md` frontmatter `status: draft → in-progress`(`updated: 2026-09-06` 는 M1 커밋일과 같아 그대로).

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
