# SPEC-COPILOT-SONGCONFIRM-001 — 구현 계획

> 정본은 `spec.md`. 이 문서는 **되돌리기 어려운 결정을 먼저** 놓고 기계적인 작업을 뒤로 미룬 실행 순서다.
> 기준 트리: 워크트리 `.claude/worktrees/agent-ab693b5114839dea5`, HEAD **`f727e11`**(= main, 2026-09-06 `git rev-parse --short HEAD` 실측). 모든 행 번호는 이 HEAD 에서 되읽은 값이다. 개발 방식 TDD. 콘솔 접촉 0.

## A. 맥락

세 결함은 하나의 형태다 — **만들어진 값이 소비되지 않는다.** 구간 선택은 파서가 없어 버려지고, BPM 은 프로퍼티까지만 오고, 도구는 세션을 볼 수 없다. 그래서 이 계획은 「무엇을 새로 만들까」보다 「이미 있는 어느 통로에 꽂을까」의 계획이다. 통로는 둘 다 실측됐다(`spec.md §A.1`): 세션 문맥 노트(`session.py:10399`)와 도구 포트(`build_toolset` 키워드 + 읽기 투과 뷰, `session.py:3820-3826`).

마일스톤 순서는 의존 방향이다. **M1** 이 기록을 만들지 않으면 **M2** 가 꽂을 것이 없다. M2 안에서는 결정 D3·D4 가 스키마와 모델 지시문에 파급되므로 그 둘을 먼저 굳힌다.

## B. 알려진 문제 (착수 전 재측정 대상)

| # | 항목 | 상태 |
|---|---|---|
| B1 | 카드 라벨의 **중복 가능성**. `_format_clock`(`question.py:153-155`)이 밀리초를 초로 접으므로, 같은 초·같은 D 등급인 두 제안은 같은 라벨을 갖는다. 라벨 왕복 대조는 그 둘을 가르지 못한다 | 측정됨(코드 판독). 실제 분석 출력에서 발생하는지는 **미측정** — 합성 픽스처 경계는 최소 4초 간격(`analyze.py` 픽스처 정답 0/16/32/36s). 처방은 §C D1 ③ |
| B2 | `normalise_start_ms`(`songcue.py:160-179`)의 문자열 갈래는 `m:ss.fff` 를 받는다(`_MMSS_PATTERN` fraction). `start_ms` → 문자열 → `start_ms` 왕복이 **손실 0**인지는 착수 시 시험으로 고정한다 | 미측정 — M2 첫 RED 로 잰다 |
| B3 | `_section_dynamics(name)`(`songcue.py:630`; `_map_section_to_look` 은 `:371`)이 중립 이름(`S1`…)을 라이브러리 어휘로 오인하지 않는지 | 미측정 — M2 시험 `requires_explicit_dynamics is True` 로 고정 |
| B4 | 도구 스키마의 `required` 목록을 단언하는 기존 시험 | **측정됨 — 0건**(`grep -n required server/tests/test_songcue_tool.py server/tests/test_songcue_sections.py` → `explicit_dynamics_required` 리터럴 1건뿐) |
| B5 | `'sections' must be` 오류 문자열을 단언하는 기존 시험 | **측정됨 — 0건**. REQ-011 의 바이트 동일은 새 시험이 오늘 문자열을 리터럴로 박아 고정한다 |
| B6 | `_session_context_note()` 가 아무것도 없을 때 `None` 임을 단언하는 시험 | **측정됨** — `test_web_session.py:1013`. 기록 없음 → 노트 무변경이므로 그대로 초록 |
| B7 | 제공자가 도구 스키마의 `required` 를 강제하는지 | 미측정. 강제 여부와 무관하게 `sections` 를 선택으로 내리면 두 경우 모두 안전하다(D4) |
| B8 | 채택 구간 수의 상한. 보고서 카드는 4건이었고, 에너지 기반 분절기라 긴 곡은 더 많을 수 있다. 주입문 길이에 상한을 두지 않는다(§F 위험 W3) | 미측정 |

## C. 결정 기록 (DECIDED)

| # | 주제 | 채택 | 기각 | 기각 사유 | 파급 파일 | 결정일 |
|---|---|---|---|---|---|---|
| **D1** | **답 문법** | **라벨 왕복 대조** — ① 카드 라벨이 답에 하나라도 있으면 있는 것만 채택 ② 하나도 없으면 전부 채택 ③ 미응답·자유입력 표식은 판정 없음. 라벨은 **전체 문자열**로 대조하고, 중복 라벨은 같은 판정을 공유하며 그 사실을 기록에 남긴다(B1 처방) | (a) 산문 문법(이름·시각·「빼 줘」) (b) 구조화 답(`selected_indexes[]`) | (a) UI 가 이미 라벨을 그대로 되돌려 주므로 새 문법은 **두 번째 정본**이 된다 — 라벨과 산문이 어긋날 때 무엇이 이기는지 정할 수 없다. 그리고 `parse_confirmed_bpm` 이 「답 안의 아무 숫자」를 거부한 이유(`question.py:275-276`)가 그대로 적용된다: 라벨 안의 초 숫자가 편집 지시로 오독된다. (b) 와이어·렌더러·`QuestionRequest` 3층 변경이고 MUSICSYNC-001 이 이미 기각한 길이다(design.md §4.3) | `server/web/question.py` (새 순수 함수) | 2026-09-06 |
| **D2** | **기록의 형상과 정체성** | 불변 데이터클래스 `ConfirmedSongAnalysis`(정체성: `source_sha256` · `source_file_name` · `confirmed_at` ISO-8601 UTC; 본문: `bpm: BpmResolution` · `sections: tuple[ConfirmedSongSection, …]`; 파생: `accepted` · `dropped_count`). `question.py` 에 `SongSectionProposal` 옆에 둔다. 세션 필드 `_song_analysis: ConfirmedSongAnalysis \| None`, 프로퍼티 `song_analysis`. **`_song_bpm` 대입은 오늘 그대로** 두고, 기록이 있을 때 `song_analysis.bpm is song_bpm` 을 불변식으로 건다 | `_song_bpm` 을 기록 안으로 흡수해 프로퍼티를 기록에서 파생 | 기존 시험이 미응답 갈래에서 `song_bpm.source == "default"` 를 단언한다(`test_web_song_audio.py:479-484`). 미응답이면 기록이 없으므로 파생하면 `None` 이 되어 그 시험이 깨진다 — 하위 호환 위반 | `server/web/question.py` · `server/web/session.py` | 2026-09-06 |
| **D2-b** | **무효화 시점** | `upload_song_audio` 가 `_song_analysis = None`. `_song_bpm` 은 손대지 않는다. 생산 판독자는 전부 `song_analysis` 를 먼저 보고 그 안의 `bpm` 을 쓰므로, 낡은 BPM 은 생산 경로에서 도달 불가다 | 재업로드 시 `_song_bpm` 도 `None` | 오늘 거동 변경이며 판독자가 `song_analysis` 로 게이트되면 이득이 없다 | `server/web/session.py` | 2026-09-06 |
| **D3** | **모델 주입 통로** | `_session_context_note`(`session.py:10399-10440`)에 `Session context — …` 문단 하나 추가. 통로는 `handle_instruction(session_context=…)`(`:10037`) → `runner.py:357-358` 합성 `UserMessage`. 형제 3건과 같은 자리·같은 어조 | (a) 시스템 프리픽스(`assemble_prefix`)에 삽입 (b) 도구 결과로 되돌려 주기 (c) `history` 에 주입 | (a) 프리픽스는 룰북 버전으로 잠긴 정적 문서(`rulebook/assembly.py:73`)라 세션 값을 넣을 자리가 아니다 (b) 모델이 먼저 도구를 불러야 알 수 있어 「`sections` 없이 부르라」는 지시가 닿을 수 없다 (c) `history` 는 사용자 가시 대화의 정본이라 합성 문장을 섞으면 되읽기(`restore_history`)가 오염된다 | `server/web/session.py` | 2026-09-06 |
| **D4** | **기본값 대 명시 인자 · 스키마** | `sections` 부재 + 기록 있음 → 기본값 · 둘 다 → **명시 인자 채택** + 불일치 보고 · 부재 + 기록 없음 → 오늘 오류 바이트 동일. 스키마 `required` 에서 `sections` 를 빼고 설명에 기본값 규칙을 적는다. 결과 페이로드에 `sections_source` 를 항상 싣는다(값 `"explicit"` \| `"confirmed_analysis"`) | (a) 기록이 있으면 기록이 이긴다 (b) 둘 다 있으면 오류 | (a) 운영자가 채팅에서 다른 구간을 말했는데 도구가 조용히 확정본을 쓰면 「명시한 것이 버려지는」 사고다 — 이 저장소가 반복해서 막아 온 형태 (b) 모델이 습관적으로 `sections` 를 채우면 큐 리스트를 영영 못 만든다. 불일치는 오류가 아니라 **보고**다 | `server/orchestrator/tools.py` (핸들러 · 스키마) | 2026-09-06 |
| **D5** | **기본 구간의 이름** | 중립 ASCII `S<n>`(`n` 은 채택 순서 1부터). `dynamics` 는 `d_level` 을 그대로 넘겨 `explicit_dynamics` 경로(`tools.py:2610-2618` → `_map_section_to_look:377`)를 탄다 | 라벨(`0:00–0:15 · D1`)을 이름으로 · D 등급을 라이브러리 이름(`Drop` 등)으로 번역 | 라벨은 큐 이름에 실리기엔 길고 홑따옴표·특수문자 처리가 별도 문제다. 라이브러리 이름으로 번역하면 `_section_dynamics` 가 그 이름의 dynamics 를 다시 매겨 `d_level` 과 **두 정본**이 된다 | `server/orchestrator/tools.py` | 2026-09-06 |
| **D6** | **도구가 세션에 닿는 방법** | `build_toolset(… song_analysis: SongAnalysisPort \| None = None)` + 구조적 `Protocol`(`current` 프로퍼티 하나 — 기록 또는 `None`) + 세션 쪽 읽기 투과 뷰 `_SongAnalysisView(self)`. `UploadedSheetPort` 선례(`tools.py:527-541` · `session.py:3826`) 그대로 | 세션 객체 자체를 넘기기 · 기록을 `ExecutionContext` 에 싣기 | 세션을 넘기면 `tools.py` 가 `server.web` 에 의존한다(층 경계). `ExecutionContext`(`tools.py:501-504`)는 지시문 스코프의 dedupe 상태라 세션 수명의 값을 담을 자리가 아니다 | `server/orchestrator/tools.py` · `server/web/session.py` | 2026-09-06 |

결정 대기 항목은 **0건**이다.

## D. 제약

- **콘솔 쓰기 0 · 조회 0.** 전 마일스톤. 시험은 가짜 포트(`test_songcue_tool.py` 의 `_SongCueStatePort`·`_RecordingPort`)와 `_AnsweringChannel` 위에서만 돈다.
- **보존 경계 무변경**: `server/safety/**` · `server/audio/**` · `server/looks/**` · `server/design/**` · `ui/src/**` · `src-tauri/**`. `tools.py` 안의 슬롯 판정 함수(`_timecode_slot_verdict`, POOLEMPTY-001 착지 뒤엔 모듈 수준 `timecode_slot_verdict`) 본문과 그 호출 위치 무변경 — diff 술어는 밑줄 없는 `timecode_slot_verdict` 로 잰다. 기준은 `BASE=$(git merge-base origin/main HEAD)`(M1 착수 시 값을 `progress.md §E.2` 에 기록).
- **기존 시험 파일 무수정**: `test_song_confirm_card.py` · `test_web_song_audio.py` · `test_songcue_tool.py` · `test_web_session.py` · `test_runner_self_correction.py`. 새 시험은 새 파일 둘(`test_song_confirm_sections.py` · `test_songcue_confirmed_default.py`)에 산다.
- **층 경계**: `tools.py` 는 `server.web` 을 import 하지 않는다.
- TDD. 마일스톤마다 RED 를 먼저 관측하고 `progress.md §E.2` 에 그대로 싣는다.

---

## E. 마일스톤

### M1 — 판독과 기록 (결정 D1 · D2 · D2-b)

가장 되돌리기 어려운 것은 **기록의 형상**이다. 필드가 굳으면 M2 의 주입문·도구 기본값·시험이 전부 그 위에 선다.

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/web/question.py` | MODIFY | `ConfirmedSongSection` · `ConfirmedSongAnalysis`(frozen dataclass, `SongSectionProposal:138-150` 옆) · `parse_confirmed_sections(answer, *, proposals) -> tuple[bool, …] \| None` 순수 함수(`parse_confirmed_bpm:264-285` 옆, 같은 규칙 서술 방식). `QuestionRequest` 스키마 무변경 |
| `server/web/session.py` | MODIFY | `__init__` 에 `self._song_analysis = None`(`:3781` 옆) · `analyse_song_audio`(`:10215-10288`)에서 답 판정 뒤 기록 생성(미응답·자유입력이면 생성 안 함, `_song_bpm` 대입 `:10277` 무변경) · `upload_song_audio`(`:10185-10213`)에서 무효화 + 있었을 때만 고지 한 문장 · `song_analysis` 프로퍼티(`:10291` 옆) |
| `server/tests/test_song_confirm_sections.py` | NEW | 파서 단위(규칙 ①②③ · 라벨 전체 대조 · 없던 라벨 무시 · 중복 라벨 공유 판정) + 세션 층(기록 생성 · 미응답 무기록 · 재업로드 무효화 · `song_analysis.bpm is song_bpm`) |

**게이트(M1)**:

```bash
uv run pytest server/tests/test_song_confirm_sections.py server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py -q
BASE=$(git merge-base origin/main HEAD)
git diff --name-only "$BASE" -- server/tests/test_song_confirm_card.py server/tests/test_web_song_audio.py   # → 0행
```

### M2 — 도달: 모델 · 도구 · 고지 (결정 D3 · D4 · D5 · D6)

D4 가 스키마를 바꾸고 D3 가 모델 지시문을 정하므로 그 둘을 이 마일스톤의 첫 RED 로 세운다. 고지 문장은 마지막이다 — 가장 되돌리기 쉽다.

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/orchestrator/tools.py` | MODIFY | `SongAnalysisPort` Protocol(`UploadedSheetPort:527-541` 옆) · `build_toolset` 키워드 `song_analysis`(`:1969` 옆, 기본 `None`) · `prepare_songcue`(`:2550`) 의 `raw_sections` 분기(`:2565-2567`) 앞에 기본값 분기 + `sections_source` + 불일치 보고 · 스키마 `sections` 선택화(`:9677-9707` 설명 갱신 · `:9721` `required` 에서 제거) |
| `server/web/session.py` | MODIFY | `_SongAnalysisView`(`_LayoutImageUploadView:3591` 옆) · `build_toolset(… song_analysis=_SongAnalysisView(self))`(`:3826` 옆) · `_session_context_note`(`:10399-10440`)에 기록 문단 · 확정 고지(`:10279-10288`)에 구간 결과 + 다음 단계 문장(기록 없으면 무변경) |
| `server/tests/test_songcue_confirmed_default.py` | NEW | 도구 기본값 · 명시 우선 + 불일치 · 기록 없음 오늘 오류 리터럴 · 스키마 `required` · `start_ms` 왕복 손실 0(B2) · 중립 이름 `requires_explicit_dynamics`(B3) · 세션 노트 내용 · `handle_instruction` 을 지나 합성 `UserMessage` 에 실림 · 고지 문장 · 생산 호출자 grep · 보존 경계 diff |

**게이트(M2)**:

```bash
uv run pytest server/tests/test_songcue_confirmed_default.py server/tests/test_song_confirm_sections.py server/tests/test_songcue_tool.py server/tests/test_web_session.py server/tests/test_runner_self_correction.py server/tests/test_web_song_audio.py -q
BASE=$(git merge-base origin/main HEAD)
git diff --name-only "$BASE" -- server/safety server/audio server/looks server/design ui/src src-tauri   # → 0행
git diff "$BASE" -- server/orchestrator/tools.py | grep -c 'timecode_slot_verdict'                     # → 0 (밑줄 유무 무관)
```

### 전량 검사 (M2 끝)

```bash
uv run pytest -q -p no:cacheprovider server/tests
uv run ruff check server && uv run ruff format --check server
```

---

## F. 위험

| # | 위험 | 처방 |
|---|---|---|
| W1 | 중복 라벨(B1)로 두 제안이 한 판정을 공유한다 | 기록에 `label_shared: bool` 을 남기고 고지에 「같은 라벨 N쌍은 함께 판정」을 덧붙인다. 라벨 형식 변경은 카드 시험(`test_song_confirm_card.py:74`)을 깨므로 하지 않는다 |
| W2 | 제공자가 스키마 `required` 를 강제하지 않아 오늘도 `sections` 를 빼먹을 수 있었다면, 기본값 분기가 **기록이 없을 때** 오늘 오류를 그대로 내는 것이 하위 호환의 전부다 | AC-012 가 오류 문자열 리터럴로 고정 |
| W3 | 채택 구간이 많으면 주입문이 길어진다(B8) | 상한을 두지 않는다 — 잘라 내면 모델이 모르는 구간이 생기고 그것이 이 SPEC 이 막는 결함이다. 길이를 `progress.md` 에 숫자로 적는다 |
| W4 | 모델이 지시문을 무시하고 `sections` 를 채워 부른다 | D4 — 명시 인자가 이기고 불일치가 **보고**된다. 운영자는 보고를 읽고 재요청할 수 있다 |
| W5 | `confirmed_at` 시각이 시험을 비결정적으로 만든다 | 세션의 기존 시계 주입 관례를 따르고, 시험은 값이 아니라 형식(ISO-8601)만 단언한다 |

## G. 후속 카드 후보 (이 SPEC 밖, 선택)

- 「이 구간으로 큐 만들기」 UI 버튼 — 고지 문장이 충분하지 않다는 관측이 생기면.
- `_song_design_interview` 의 BPM 정규식 기본값을 확정 기록으로 — 콘솔 쓰기 경로라 별도 규율 필요.
- `HEAD.BPM` 접합 · `build_timecode_handoff_card` 생산 호출자 — MUSICSYNC-001 부채 그대로.

## H. 교차 참조

`spec.md` · `acceptance.md` · `progress.md` · `SPEC-COPILOT-MUSICSYNC-001/{plan,progress}.md` · `reports/musicsync-browser-check-20260906.md` · `.claude/rules/moai/core/verification-claim-integrity.md`
