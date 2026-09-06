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

**M1 커밋**: `845658e` — `feat(SPEC-COPILOT-SONGCONFIRM-001): M1 구간 답을 읽고 확정을 기록으로 남긴다 — 라벨 왕복 대조` (5 files changed, 511 insertions(+), 5 deletions(-)).

### M2 — 도달: 도구 · 모델 · 고지 (AC-007 ~ 016)

**RED (구현 전, 시험 파일 작성 직후 — verbatim)**

```
$ .venv/bin/python -m pytest server/tests/test_songcue_confirmed_default.py -q -p no:cacheprovider
…
21 failed, 6 passed, 1 warning in 1.20s
$ … --tb=line   (실패 사유, 중복 제거)
  12 server/tests/test_songcue_confirmed_default.py:89: TypeError: build_toolset() got an unexpected keyword argument 'song_analysis'
   1 …:383: assert not <re.Match object; span=(8566, 8581), match='from server.web'>
   1 …:379: AssertionError: ⑤
   1 …:363: AssertionError: ④
   1 …:360: AssertionError: ③
   1 …:313: IndexError: list index out of range            (AC-009: 노트 없이 대화가 1건뿐)
   1 …:276: assert None is not None                        (AC-008: 세션 노트 None)
   1 …:253: AssertionError: assert '구간 2건 채택' in 'BPM 129.199 로 확정했습니다 (measured). 채택 우선순위: 측정 > 시트 HEAD.BPM > 기본값 120.'
   1 …:232: AssertionError: assert {'genre', 'se...ecode_number'} == {'genre', 'so...ecode_number'}   (AC-013: required 에 sections)
   1 …:222: KeyError: 'sections_source'
```

RED 에서 드러난 **BASE 의 사실**: `server/orchestrator/tools.py:234` 는 BASE `fc65860` 에서 이미 `from server.web.question import UNANSWERED, QuestionOption, QuestionRequest` 를 갖고 있다(`grep -n 'server\.web' server/orchestrator/tools.py` → 그 1행). spec.md §E 「`tools.py` 는 `server.web` 을 import 하지 않는다」는 오늘 상태와 다르다. 이 SPEC 이 지킨 것은 「**새** `server.web` import 를 더하지 않는다」다 — 기록은 `SongAnalysisPort` Protocol 로 받고, `server.web.session` 이나 `ConfirmedSongAnalysis` 를 tools.py 가 import 하지 않는다(시험 `test_tools_adds_no_server_web_import` 가 BASE 의 그 한 줄만 허용한다). SPEC 본문은 손대지 않았다.

**GREEN 1차 (구현 후)** — `2 failed, 25 passed`. ① AC-008 시험이 `_song_analysis` 만 직접 심어 `song_bpm` 이 `None` 인 세션을 만들었다 — 생산에서는 생길 수 없는 상태(REQ-006 불변식 위반). 시험 픽스처 `_hold` 가 두 필드를 같은 객체로 심도록 고쳤다(구현은 그대로: 노트는 `song_bpm` 프로퍼티를 읽는다 — 그것이 REQ-016 이 요구한 `song_bpm` 의 생산 판독자다). ② 층 경계 시험이 내 `ConfirmedSongAnalysisPort` 이름을 부분문자열로 잡았다 — import 행에만 앵커하도록 고쳤다.

**GREEN (M2 게이트, acceptance.md §A M2 명령 — verbatim)**

```
$ .venv/bin/python -m pytest server/tests/test_songcue_confirmed_default.py server/tests/test_song_confirm_sections.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py server/tests/test_web_song_audio.py -q -p no:cacheprovider
555 passed, 1 warning in 5.39s
```

```
$ git diff --name-only fc658606d91cbd61cdcf68b1c7d27b4b973eef4d -- server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py
(출력 0행)
$ git diff --name-only fc658606d91cbd61cdcf68b1c7d27b4b973eef4d -- server/safety server/audio server/looks server/design ui/src src-tauri
(출력 0행)
$ git diff -U0 fc658606d91cbd61cdcf68b1c7d27b4b973eef4d -- server/orchestrator/tools.py | grep '^[+-]' | grep -c 'timecode_slot_verdict'
0
```

**AC-014 다섯 grep (변경 뒤 트리 — verbatim; BASE 대조군은 위 「AC-014 대조군」 전부 0)**

```
① grep -rn 'parse_confirmed_sections(' server --include='*.py' | grep -v /tests/ | grep -v 'def parse_confirmed_sections'
server/web/session.py:10321:        verdict = parse_confirmed_sections(answer, proposals=proposals)
② grep -rn 'ConfirmedSongAnalysis(' server --include='*.py' | grep -v /tests/ | grep -v 'class ConfirmedSongAnalysis'
server/web/session.py:10325:            record = ConfirmedSongAnalysis(
③ grep -n 'song_analysis=' server/web/session.py
3856:            song_analysis=_SongAnalysisView(self),
④ grep -n 'song_analysis\.current' server/orchestrator/tools.py | grep -v ':[[:space:]]*#'
2619:        confirmed = song_analysis.current if song_analysis is not None else None
   grep -c 'song_analysis: SongAnalysisPort' server/orchestrator/tools.py
1
⑤ grep -rn '\.song_bpm\b\|_song_bpm' server --include='*.py' | grep -v /tests/ | grep -v ':[[:space:]]*#' | grep -v 'self._song_bpm: BpmResolution' | grep -v 'self._song_bpm = resolution' | grep -v 'return self._song_bpm'
server/web/session.py:10534:            bpm = self.song_bpm
```

**전량 검사 (plan.md §E 「전량 검사 (M2 끝)」)**

```
$ .venv/bin/python -m pytest server/tests -q -p no:cacheprovider
11321 passed, 12 skipped, 1 warning in 159.83s (0:02:39)   (exit=0 · 로그 .venv/full-suite.log, 워크트리 밖으로는 안 남김)
$ .venv/bin/ruff check server
All checks passed!
$ .venv/bin/ruff format --check server
502 files already formatted
```

**W3 실측 (주입문 길이, 채택 3건 기록)**: `_session_context_note()` → 484 자 / 497 바이트(영문 지시문). 채택 구간 하나당 `, #<i> m:ss–m:ss · D<n>` 약 20자가 늘어난다. 상한은 두지 않았다(plan.md §F W3).

**B2 실측**: `normalise_start_ms(bare int)` 는 초로 읽으므로 기본 구간은 `m:ss.mmm` 문자열로 넘긴다(`_confirmed_section_input`). 왕복 손실 0 을 8값(0 · 7 · 999 · 59999 · 60000 · 61001 · 3599999 · 3600000)으로 고정(`test_start_ms_round_trips_without_loss`). **B3 실측**: `resolve_dynamics("S1"/"S2"/"S12")` → `None` → `requires_explicit_dynamics is True`.

| AC | 상태 | 검증 명령 | 실제 출력 |
|---|---|---|---|
| AC-SONGCONFIRM-007 | PASS | `TestTheConfirmationNoticeNamesSectionsAndTheNextStep` 2건(미응답 갈래 오늘 문면 동일 대조군 포함) | M2 게이트 `555 passed` 에 포함 |
| AC-SONGCONFIRM-008 | PASS | `TestTheSessionNoteCarriesTheRecord` 2건(기록 없음 → `None` 대조군) | 위와 같음 |
| AC-SONGCONFIRM-009 | PASS | `TestTheNoteReachesTheModel` 2건 — `ScriptedProvider` 가 받은 대화에서 지시문 바로 앞 `UserMessage` 에 `prepare_songcue` + 채택 라벨 3개; 기록 없으면 대화 1건 | 위와 같음 |
| AC-SONGCONFIRM-010 | PASS (판독 주의) | `TestConfirmedSectionsAreTheDefault` 2건 | `is_error False` · `sections_source == "confirmed_analysis"` · `report.sections` 길이 3 · 이름 `S1..S3` ASCII · `requires_explicit_dynamics True` · 골라진 룩 dynamics 1/3/5(명령의 `Attribute 'Dimmer' At 10/30/50`) · 번들이 `run_commands` → 가짜 실행 포트 `executed` 에 `Store Timecode 7` · `Store Sequence …`. **판독 주의**: AC 문면의 「`report.sections` 각 구간의 `start_ms`」 — `report.sections[]` 는 `server/looks/songcue_report.py` 가 만들며 오늘 `start_ms` 키가 없고, 그 파일은 REQ-014 보존 경계 안이라 키를 더할 수 없다. 손실 0 은 tools.py 소유 페이로드 `confirmed_sections[].start_ms`(정확히 0/15952/32020)와, 같은 raw 구간을 `parse_sections` 에 다시 넣은 `SongCueSection.start_ms` 로 판정했다 |
| AC-SONGCONFIRM-011 | PASS | `TestExplicitSectionsWinAndMismatchIsReported` 2건 | `sections_source == "explicit"` · 이름 `Intro`/`Chorus` · `confirmed_analysis_mismatch.matches False` · `explicit_count 2` · `confirmed_count 3` · `start_pairs[1] == [20000, 15952]` · `start_pairs[2] == [null, 32020]`; 대조군(시작·개수 일치) `matches True` |
| AC-SONGCONFIRM-012 | PASS | `TestNoRecordMeansTodaysError` 3건(포트 없음 · `current None` · 기록 없이 명시 인자 → 불일치 보고 없음) | 오류 본문 == `'sections' must be a non-empty array of song sections` |
| AC-SONGCONFIRM-013 | PASS | `TestTheSchemaMakesSectionsOptional` + `test_songcue_tool.py::TestRegistrationConvention` 3건 무수정 초록 | `required == {"song_title","genre","timecode_number"}` · `sections.description` 에 `confirmed` · `timecode_number.description` 오늘 문면 |
| AC-SONGCONFIRM-014 | PASS | 위 다섯 grep(verbatim) + `TestEveryNewEntryPointHasAProductionCaller` 6건 | ①②③④⑤ 각 1행, 키워드 인자 1 |
| AC-SONGCONFIRM-015 | PASS | 위 세 diff 술어 | 0행 · 0행 · `0`. 콘솔 접촉 0: 전 시험이 `FakeConsole` / `_RecordingPort` / `_AnsweringChannel` / `ScriptedProvider` 위에서 돌고 conftest `_refuse_live_console_port` 무변경(보존 경계 diff 0행이 `server/tests/conftest.py` 를 포함하진 않으므로 별도로 `git diff --name-only $BASE -- server/tests/conftest.py` 는 아래 §E.3 에 적는다) |
| AC-SONGCONFIRM-016 | PASS | M2 게이트 + 전량 검사 + 다섯 파일 diff | `555 passed` · 전량 결과 위 블록 · 0행 |

M2 변경 파일: `server/orchestrator/tools.py`(`ConfirmedSectionPort` · `ConfirmedSongAnalysisPort` · `SongAnalysisPort` · `_confirmed_section_input` · `build_toolset(song_analysis=…)` · `prepare_songcue` 기본값/불일치/`sections_source` · 스키마) · `server/web/session.py`(`_SongAnalysisView` · `build_toolset` 키워드 · `_session_context_note` 문단 · 확정 고지 · 미응답 재분석 시 기록 해제) · `server/tests/test_songcue_confirmed_default.py`(신규) · 이 파일.

### 미검증 · 잔여 위험 (5절 형식의 Gaps / Residual-risk)

- **미검증**: 실브라우저·실기 콘솔 관측 0건(설계상 — 콘솔 접촉 0). 제공자가 스키마 `required` 를 강제하는지(B7)는 재지 않았다 — `sections` 를 선택으로 내렸으므로 강제 여부와 무관하게 안전하다. 실제 분석 출력에서 중복 라벨(B1)이 나는지는 재지 않았다 — 파서·기록·고지가 그 경우를 다루는지만 합성 제안으로 고정했다. 채택 구간 수 상한(B8) 미측정 — W3 길이만 적었다.
- **문서 부정확 2건(SPEC 본문 무수정, manager-spec/manager-docs 판단 대상)**: (a) acceptance.md AC-005 (d) 괄호 전제「앞 라벨이 뒤 라벨의 부분문자열」— 실측 False(위 M1 GREEN 1차). (b) spec.md §E 「`tools.py` 는 `server.web` 을 import 하지 않는다」— BASE 에 이미 `tools.py:234` 가 있다(위 M2 RED). 둘 다 이 SPEC 이 만드는 것에는 영향이 없다.
- **잔여 위험**: `_session_context_note` 의 기록 문단은 영문 지시문이며 모델이 따를지는 시험이 보증하지 않는다(W4 — 따르지 않으면 명시 인자가 이기고 불일치가 **보고**된다). `confirmed_at` 은 `datetime.now(UTC)` 로 세션에 시계 주입 관례가 없어 시험은 형식만 단언한다(W5). 기록은 세션 수명이라 재시작·`history_restore` 로 되살아나지 않는다(범위 밖, spec.md §D).

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-06
run_commit_sha: d28ebd6   # M2 커밋(백필 — 커밋은 자기 해시를 모른다, D3 예외). M1 = 845658e
run_status: implemented-pending-sync
ac_pass_count: 16
ac_fail_count: 0
preserve_list_post_run_count: 0   # git diff --name-only $BASE -- server/safety server/audio server/looks server/design ui/src src-tauri → 0행; git diff --name-only $BASE -- server/tests/conftest.py → 0행
l44_pre_commit_fetch: "git fetch origin main → origin/main fc65860 (BASE 와 동일)"
l44_post_push_fetch: "git push -u origin WT-song-confirm-run → exit 0, [new branch]; origin/WT-song-confirm-run == HEAD d28ebd6 (rev-list --left-right 0 0). 푸시 직전 fetch: origin/main 은 fc65860 → 4453631 로 1건 전진(SPEC-COPILOT-POOLEMPTY-001 M1·M2 run, #320 — server/orchestrator/tools.py 165행 · server/tests/test_songcue_tool.py 152행 포함, _timecode_slot_verdict → timecode_slot_verdict 개명). 이 브랜치는 BASE fc65860 기준 그대로다 — 나중에 착지하는 쪽이 rebase 한다는 spec.md §A.1 규칙대로 통합은 리드 판단(rebase / merge). 읽기 전용 사전 검사: git merge-tree --write-tree origin/main HEAD → exit 0, CONFLICT 0행(결과 트리 83793cef); 그 트리를 git archive 로 .venv/merged-tree 에 풀어 이 SPEC 의 게이트 8파일을 돌리면 596 passed, 1 failed — 실패 1건은 test_tree_identity.py::test_own_tree_runs_normally 로 풀어 놓은 사본(인터프리터 트리 ≠ 사본 트리)에서 트리 동일성 가드가 맞게 거절한 것이며 이 SPEC 의 코드가 아니다."
new_warnings_or_lints_introduced: 0   # ruff check server → All checks passed!; ruff format --check server → 502 files already formatted
prepush_hook: "실행됨 — .git/hooks/pre-push 가 make -C <repo-root> -s ci-local 을 돌렸고(stdout 은 훅이 /dev/null 로 버린다) 훅 자신의 로그 .moai/logs/prepush-bypass.log 에 '1788661294\tstudiox\tWT-song-confirm-run\tpass\t17s'. SKIP_MOAI_PREPUSH 미사용"
cross_platform_build:
  applicable: false   # Python 서버 — 빌드 단계 없음; 인터프리터 .venv Python 3.11.15
total_run_phase_files: 5   # server/web/question.py · server/web/session.py · server/orchestrator/tools.py · server/tests/test_song_confirm_sections.py · server/tests/test_songcue_confirmed_default.py (+ spec.md frontmatter, progress.md)
m1_to_mN_commit_strategy: "마일스톤당 커밋 1건(M1 845658e · M2), 브랜치 WT-song-confirm-run 푸시, PR 은 열지 않음(리드 소유)"
```

## §E.4 Sync-phase Audit-Ready Signal

> 실행 주체: manager-docs, 카드 t273. 워크트리 `.claude/worktrees/agent-ab6103b1e18f4ebc7`, 브랜치 `WT-song-confirm-sync`, base `origin/main b216a38`(run PR #321 + CI 복구 #322 포함, `rev-list --left-right 0 0`). 인터프리터 `uv sync --python 3.11` → `.venv/bin/python` 3.11.15(이 트리).

```yaml
sync_complete_at: 2026-09-06
sync_commit_sha: 1b9a422   # 백필 — sync 커밋은 자기 해시를 모른다(D3 예외). 이 값은 둘째 커밋이 적었다
sync_status: completed
b12_self_test_a: "grep -c 'SONGCONFIRM-001' CHANGELOG.md → 편집 전 0 · 편집 후 1"
b12_self_test_b: "grep -oE 'AC-([A-Z0-9]+-)*[0-9]+' acceptance.md | sort -u → 전체 ID 16건(AC-SONGCONFIRM-001~016) + 본문 축약 참조 4건(AC-002·004·010·014, 같은 항목의 줄임말) = raw 20; CHANGELOG 는 16 을 적는다 — acceptance.md 기준, progress.md 아님"
b12_self_test_c: "CHANGELOG 가 든 경로 전부 ls 로 확인 — server/web/question.py · server/web/session.py · server/orchestrator/tools.py · .moai/specs/SPEC-COPILOT-SONGCONFIRM-001/progress.md 존재; reports/musicsync-e2e-song-to-cuelist-20260906.md 는 주 체크아웃에 존재하되 git 미추적(이 트리엔 없음 — CHANGELOG 에 그 사실을 적었다)"
changelog_entry_position: "[Unreleased] › ### Added 첫 항목(READBACK-001 위)"
frontmatter_status_transitions:
  spec_md: "in-progress → implemented → completed (단일 sync 커밋에 병합) · updated 2026-09-06 유지(같은 날)"
  plan_md: "frontmatter 없음 — 무변경"
  acceptance_md: "frontmatter 없음 — 무변경"
  progress_md: "frontmatter 없음 — 이 절만 추가"
docs_synced:
  readme: "README.md § Music sync 2번 항목에 확정 뒤 다음 단계 문단 1개 + Implementation 줄에 배관 파일 3개·SPEC 링크"
  docs_site: "해당 없음 — 이 저장소에 4-locale docs-site 없음; docs/capability-index.md 는 곡 조명 표준 색인이라 이 흐름을 다루지 않아 무변경"
mx_tag_report:
  added: 1   # server/web/question.py section_label — @MX:ANCHOR (fan_in 3: build_song_confirmation_card · parse_confirmed_sections · session.analyse_song_audio) + @MX:REASON + @MX:SPEC
  removed: 0
  updated: 0
  scan: "parse_confirmed_sections 생산 호출자 1 · _confirmed_section_input 1 · ConfirmedSongAnalysis( 1 → MUST 아님, 태그 없음"
sync_verification:
  tests: ".venv/bin/python -m pytest server/tests/test_song_confirm_sections.py server/tests/test_songcue_confirmed_default.py -q -p no:cacheprovider → 61 passed, 1 warning (MX 태그 추가 전) · 재실행은 커밋 전 아래 5절 보고에"
  spec_lint: "moai spec lint — 아래 5절 보고에 결과"
canary_compliance_check:
  applicable: false   # 이 SPEC 은 자기 sync 가 시험하는 전향 정책을 정의하지 않는다
spec_body_findings_for_manager_spec:   # 본문 무수정 — 소유권 밖. 차단 아님(sync 산출물에 영향 없음)
  - "acceptance.md AC-005 (d) 괄호 전제「앞 라벨이 뒤 라벨의 부분문자열」— 실측 False(§E.2 M1 GREEN 1차). Then 절은 통과"
  - "spec.md §E「tools.py 는 server.web 을 import 하지 않는다」— BASE 에 이미 tools.py:234 import 1행. 이 SPEC 이 지킨 것은 「새 import 를 더하지 않는다」"
```
