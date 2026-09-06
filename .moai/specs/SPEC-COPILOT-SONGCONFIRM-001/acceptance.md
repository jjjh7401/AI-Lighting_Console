# SPEC-COPILOT-SONGCONFIRM-001 — 인수 기준

> 각 항목은 **이진 판정 가능**해야 한다. 부정 대조군이 없는 항목은 통과해도 계기 고장과 구별되지 않는다.
> **전 항목이 오프라인이다.** 콘솔 쓰기 0 · 조회 0(REQ-SONGCONFIRM-014). 실측 기준 HEAD 는 `f727e11` 이었으나, diff 술어의 기준은 리터럴이 아니라 **`BASE=$(git merge-base origin/main HEAD)`** 다 — M1 착수 시 그 값을 `progress.md §E.2` 에 적는다. 형제 SPEC-COPILOT-POOLEMPTY-001 이 `_timecode_slot_verdict` 를 모듈 수준 `timecode_slot_verdict` 로 옮기므로(두 SPEC 은 독립이며 나중에 착지하는 쪽이 rebase 한다), 슬롯 판정 술어는 밑줄 없는 `timecode_slot_verdict` 로 두 이름을 함께 잡는다.
> AC 는 `001`~`016` 연속 16건(Tier M 상한). 하위 ID 없음. 「AC 번호는 REQ 번호를 함의하지 않는다」 — `↔` 표기가 정본이다.

## A. 실행 명령

```bash
# M1 — 판독과 기록
uv run pytest server/tests/test_song_confirm_sections.py server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py -q

# M2 — 도달
uv run pytest server/tests/test_songcue_confirmed_default.py server/tests/test_song_confirm_sections.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py server/tests/test_web_song_audio.py -q

# 기준 (progress.md §E.2 에 값을 적는다)
BASE=$(git merge-base origin/main HEAD)

# 기존 시험 파일 무수정 (REQ-015)
git diff --name-only "$BASE" -- server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py
# → 출력 0행

# 보존 경계 (REQ-014)
git diff --name-only "$BASE" -- server/safety server/audio server/looks server/design ui/src src-tauri
# → 출력 0행

# 슬롯 판정 무변경 (REQ-012) — 밑줄 없는 이름은 `_timecode_slot_verdict` 와 `timecode_slot_verdict` 둘 다 잡는다
git diff -U0 "$BASE" -- server/orchestrator/tools.py | grep '^[+-]' | grep -c 'timecode_slot_verdict'
# → 0

# 생산 호출자 (REQ-016) — 아래 AC-014 참조
```

---

## B. M1 — 판독과 기록

**AC-SONGCONFIRM-001** — 카드를 그대로 받아들이면 전부 채택된다 ↔ REQ-001 · 002 · 003 ② · 006
Given 제안 4건(`0:00–0:15 · D1` / `0:15–0:32 · D3` / `0:32–0:36 · D5` / `0:36–0:40 · D2`)으로 카드가 서고
When 답이 네 라벨 전부를 `", "` 로 이은 문자열(UI `joinChosenLabels` 형식)이면
Then `session.song_analysis` 는 `None` 이 아니고, `sections` 4건 전부 `selected is True`, `accepted` 길이 4, `dropped_count == 0`, `source_sha256` 은 업로드 고지의 sha256 과 같고 `source_file_name` 은 업로드한 파일명과 같으며, `confirmed_at` 은 ISO-8601 형식(`datetime.fromisoformat` 이 받는다)이고, `sections[i]` 의 `label` · `start_ms` · `end_ms` · `d_level` 이 제안 `i` 의 값과 같고, `song_analysis.bpm is session.song_bpm` 이다(REQ-006 — 같은 객체).

**AC-SONGCONFIRM-002** — 체크를 푼 구간은 제외된다 ↔ REQ-001 · 003 ①
Given 같은 카드에서
When 답이 첫째와 셋째 라벨만 이은 문자열이면
Then `sections[0].selected`·`sections[2].selected` 는 `True`, `sections[1]`·`sections[3]` 은 `False`, `accepted` 는 `index` `(0, 2)` 순서, `dropped_count == 2`. 제외된 구간도 기록에 **남아 있다**(목록 길이 4).

**AC-SONGCONFIRM-003** — 자유 입력으로 BPM 만 고쳐도 구간은 카드대로 채택된다 ↔ REQ-003 ② · 004
Given 같은 카드에서
When 답이 `BPM 130` 이면(라벨 0건)
Then `song_bpm.bpm == 130.0` 이고, `song_analysis.accepted` 길이 4, `dropped_count == 0`. **대조군**: 답이 `두 번째는 빼 줘` 여도 결과는 동일하다(산문은 구간 편집이 아니다).

**AC-SONGCONFIRM-004** [부정 대조군] — 답이 없으면 기록도 없고 오늘 거동은 그대로다 ↔ REQ-002
Given 같은 카드에서
When 답이 `UNANSWERED` 또는 `ANSWER_FREEFORM` 이면
Then `session.song_analysis is None` 이고, `session.song_bpm.source == "default"` · `song_bpm.bpm is None` — 즉 `test_web_song_audio.py:479-484` 가 오늘 단언하는 값과 같다.

**AC-SONGCONFIRM-005** [부정 대조군] — 라벨은 전체로만 대조된다 ↔ REQ-003 · 004
Given 같은 카드에서
When 답이 (a) 카드에 없는 라벨 `9:59–9:59 · D9` 하나뿐 (b) 라벨의 조각 `0:15` 하나뿐 (c) 등급 조각 `D5` 하나뿐이면
Then 세 경우 모두 규칙 ②(라벨 0건 → 전부 채택)가 적용돼 `accepted` 길이 4 이고, 기록의 어느 구간도 `9:59` 를 담지 않는다. **양성 대조군**: 같은 시험 안에서 실제 라벨 하나를 주면 `accepted` 길이 1 로 떨어진다(계기가 공허하지 않음).
(d) **접두 충돌 대조군**: 제안이 `1:00–1:15 · D1` 과 `11:00–11:15 · D1` 인 카드(`_format_clock` 은 분을 0 으로 채우지 않으므로 앞 라벨이 뒤 라벨의 부분문자열이다)에서 답이 `11:00–11:15 · D1` 하나뿐이면 `accepted` 길이 **1** 이고 그 `index` 는 뒤 구간이다 — 부분문자열 대조라면 2 가 나온다.

**AC-SONGCONFIRM-006** — 다른 곡을 올리면 이전 확정은 무효가 된다 ↔ REQ-005
Given 확정 기록이 있는 세션에서
When 두 번째 오디오를 업로드하면
Then `session.song_analysis is None` 이고, 업로드 고지에 리터럴 `이전 분석 확정` 과 `무효` 가 둘 다 들어 있다. **대조군**: 기록이 없는 세션의 첫 업로드 고지는 `'{file}' 첨부됨 — 오디오 · sha256 {sha} · {n}바이트. 아직 분석한 것은 없습니다 — 무엇을 할지 말씀해 주세요.` 와 **문자열 동일**하다(`session.py:10209-10212` 오늘 문면).

---

## C. M2 — 도달: 운영자 · 모델 · 도구

**AC-SONGCONFIRM-007** — 확정 고지가 구간 결과와 다음 단계를 말한다 ↔ REQ-013
Given AC-002 의 답(2 채택 · 2 제외)으로 확정하면
When 고지 문자열을 읽으면
Then 오늘의 BPM 문장(`BPM {bpm:g} 로 확정했습니다 ({source}).`)이 그대로 들어 있고, 리터럴 `구간 2건 채택` 과 `2건 제외` 가 이 두 문자열 그대로, 그리고 `큐 리스트` 와 `말씀해 주세요` 가 들어 있다. **대조군**: AC-004 갈래(미응답)의 고지는 오늘 문면(`session.py:10279-10288` 이 조립하는 문자열)과 **문자열 동일**하다.

**AC-SONGCONFIRM-008** — 세션 노트가 기록을 싣는다 ↔ REQ-007 · 008
Given 확정 기록(파일 `track.wav`, sha `373351cd…`, BPM 129.199 measured, 채택 3 · 제외 1)이 있으면
When `session._session_context_note()` 를 부르면
Then 반환 문자열에 `Session context —` · `track.wav` · sha 앞 8자 `373351cd` · `129.199` · `measured` · 채택 구간 세 개의 `m:ss–m:ss` 와 `D<n>` 전부 · `1` 과 제외를 뜻하는 단어 · `prepare_songcue` · `sections` · `timecode_number` 가 모두 들어 있다. **대조군**: 기록이 없는 세션에서 `_session_context_note()` 는 `None`(`test_web_session.py:1013` 과 동일).

**AC-SONGCONFIRM-009** — 노트가 실제로 모델까지 간다 ↔ REQ-007
Given 대화를 붙잡는 가짜 제공자(`test_runner_self_correction.py:281-314` 형태)로 세션을 세우고 확정 기록이 있으면
When 채팅 지시문 하나를 보내면
Then 제공자가 받은 대화에서 마지막 사용자 메시지 **바로 앞** 메시지의 본문에 `prepare_songcue` 와 채택 구간 라벨이 들어 있다. **대조군**: 기록이 없으면 사용자 메시지는 지시문 하나뿐이다(`test_runner_self_correction.py:304` 와 같은 형상).

**AC-SONGCONFIRM-010** — `prepare_songcue` 가 확정 구간으로 번들을 만든다 ↔ REQ-009
Given 채택 구간 3건(`start_ms` 0 / 15952 / 32020, `d_level` 1 / 3 / 5)을 든 포트를 `build_toolset(song_analysis=…)` 로 넘기고
When `prepare_songcue` 를 `song_title` · `genre` · `timecode_number` 만으로 부르면
Then 결과 `is_error` 가 `False`, 페이로드 `sections_source == "confirmed_analysis"`, `report.sections` 길이 3, 각 구간의 `start_ms` 가 **정확히** 0 / 15952 / 32020(손실 0), 각 구간 이름은 ASCII 이고 `parse_sections` 를 통과한 `SongCueSection.requires_explicit_dynamics is True` 이며, 선택된 룩의 `dynamics` 가 1 / 3 / 5 다. 가짜 실행 포트가 받은 번들은 오늘 `test_songcue_tool.py::TestPayload` 가 받는 형태와 같은 경로(`run_commands`)로 왔다.

**AC-SONGCONFIRM-011** — 명시 인자가 이기고 불일치가 보고된다 ↔ REQ-010
Given AC-010 의 포트와
When `sections` 2건(`Intro 0:00` · `Chorus 0:20`)을 **함께** 주면
Then `sections_source == "explicit"`, `report.sections` 길이 2 이고 이름이 `Intro`·`Chorus`, 페이로드 `confirmed_analysis_mismatch.matches is False`, `.explicit_count == 2`, `.confirmed_count == 3`, `index 1` 의 시작 쌍이 `(20000, 15952)` 로 나란히 실린다. **대조군**: 명시 인자가 확정 구간과 시작·개수 모두 같으면 `matches is True`.

**AC-SONGCONFIRM-012** [부정 대조군] — 기록이 없으면 오늘 오류가 바이트 동일하다 ↔ REQ-011 · 015
Given `song_analysis` 포트를 **넘기지 않은** `build_toolset` 과, 넘겼으되 `current` 가 `None` 인 포트 둘에서
When `prepare_songcue` 를 `sections` 없이 부르면
Then 두 경우 모두 `is_error is True` 이고 오류 본문이 리터럴 `'sections' must be a non-empty array of song sections` 을 담는다(`tools.py:2567` 오늘 문면).

**AC-SONGCONFIRM-013** — 스키마가 기본값을 말하고 필수 셋은 남는다 ↔ REQ-011 · 012
Given 등록된 `prepare_songcue` 도구 정의에서
When `parameters.required` 와 `properties.sections.description` 을 읽으면
Then `required` 는 정확히 `{"song_title", "genre", "timecode_number"}` 집합이고 `sections` 는 없으며, `sections.description` 에 `confirmed` 가 들어 있고, `timecode_number.description` 은 오늘 문면 그대로다. `test_songcue_tool.py::TestRegistrationConvention` 3건은 무수정으로 초록이다.

---

## D. 횡단 — 생산 호출자 · 경계 · 회귀

**AC-SONGCONFIRM-014** — 새 진입점마다 생산 호출자가 있고 `song_bpm` 이 읽힌다 ↔ REQ-016
Given 구현이 끝난 트리에서
When 아래 다섯 grep 을 실행하면
Then 각각의 출력 행 수가 명시된 하한 이상이다(정의 행은 제외).

```bash
# ① 구간 파서 — session.py 가 부른다
grep -rn 'parse_confirmed_sections(' server --include='*.py' | grep -v /tests/ | grep -v 'def parse_confirmed_sections'   # ≥ 1
# ② 기록 생성 — session.py 가 만든다
grep -rn 'ConfirmedSongAnalysis(' server --include='*.py' | grep -v /tests/ | grep -v 'class ConfirmedSongAnalysis'      # ≥ 1
# ③ 도구 포트 — session.py 의 build_toolset 호출에 실린다
grep -n 'song_analysis=' server/web/session.py                                                                            # ≥ 1
# ④ 도구 기본값 분기 — 핸들러가 포트의 current 를 읽는다 (주석 행 제외: 행 첫 비공백이 # 인 행만 버린다)
grep -n 'song_analysis\.current' server/orchestrator/tools.py | grep -v ':[[:space:]]*#'                                  # ≥ 1
grep -c 'song_analysis: SongAnalysisPort' server/orchestrator/tools.py                                                     # = 1 (build_toolset 키워드 인자)
# ⑤ song_bpm 생산 판독자 — 정의·대입·프로퍼티 3행 밖에서, 주석 행 제외
grep -rn '\.song_bpm\b\|_song_bpm' server --include='*.py' | grep -v /tests/ | grep -v ':[[:space:]]*#' | grep -v 'self._song_bpm: BpmResolution' | grep -v 'self._song_bpm = resolution' | grep -v 'return self._song_bpm'   # ≥ 1
```

**대조군**: 같은 명령을 `$BASE` 에서 실행하면 ①~④ 는 0 행, ⑤ 는 0 행이다(오늘의 상태 — 이 AC 가 재는 것이 「변화」임을 고정).

**AC-SONGCONFIRM-015** — 콘솔 접촉 0 · 보존 경계 · 슬롯 판정 무변경 ↔ REQ-012 · 014
Given 구현이 끝난 트리에서
When §A 의 세 diff 명령을 실행하면
Then 보존 경계 `git diff --name-only` 는 0행, `timecode_slot_verdict`(밑줄 유무 무관)를 담은 diff 행은 0, 그리고 M1·M2 전 시험에서 가짜 실행 포트의 `sent`/`executed` 목록에 콘솔 명령이 **AC-010·011 의 `run_commands` 번들 외에는** 0건이다(그 번들도 가짜 포트에 머문다 — 실기 0).

**AC-SONGCONFIRM-016** — 기록이 없으면 전부 오늘과 같다 ↔ REQ-015
Given 기준 `$BASE` 의 다섯 시험 파일(`test_song_confirm_card.py` · `test_web_song_audio.py` · `test_songcue_tool.py` · `test_web_session.py` · `test_runner_self_correction.py`)이 **한 줄도 바뀌지 않은 채**
When M2 게이트와 전량 검사(`uv run pytest -q -p no:cacheprovider server/tests`)를 돌리면
Then 다섯 파일 전부 초록이고 전량 검사에 실패 0 건이며, `git diff --name-only "$BASE" -- <다섯 파일>` 은 0행이다.

---

## E. 품질 게이트 · 완료 정의

- **게이트**: §A 명령 전부 통과 · `uv run ruff check server` · `uv run ruff format --check server` · 전량 `server/tests` 실패 0.
- **완료 정의(DoD)**: AC 16/16 PASS(PASS-WITH-DEBT 는 사유와 함께 §E.2 에 적는다) · REQ→AC 역방향표(§F) 미대응 0 · `progress.md §E.2` 가 5절 형식(주장 · 증거 · 기준 귀속 · 미검증 · 잔여 위험)으로 마일스톤별 RED 증거와 게이트 출력을 그대로 싣는다 · 콘솔 접촉 0 을 숫자로 적는다.

## F. REQ → AC 역방향표

| REQ | AC |
|---|---|
| 001 | 001 · 002 |
| 002 | 001 · 004 |
| 003 | 001 · 002 · 003 · 005 |
| 004 | 003 · 005 |
| 005 | 006 |
| 006 | 001 |
| 007 | 008 · 009 |
| 008 | 008 |
| 009 | 010 |
| 010 | 011 |
| 011 | 012 · 013 |
| 012 | 013 · 015 |
| 013 | 007 |
| 014 | 015 |
| 015 | 012 · 016 |
| 016 | 014 |

미대응 REQ **0건**.
