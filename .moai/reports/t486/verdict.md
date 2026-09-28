# t486 판정서 — 쪼갠 큐 이름 · 죽은 코드 정리 · 큐 설명 밝기 불일치

- 카드: t486(t480·t482 후속 정리). 근거: `.moai/reports/t480/verdict.md` §6 2번·5번, `.moai/reports/t482/verdict.md` §3·§6
- 레인: lane-1 · 워크트리 `.claude/worktrees/t486` · 브랜치 `WT-cue-name-cleanup` · 기준 `b29bc497`(착수 시점 `origin/main`)
- 콘솔 접속 0. 리드 결정: ② `session.py` 3줄 삭제 승인, ③ 처방 (A), UI 표식 문구 변경 승인(모두 2026-09-28)

## 1. 요약

| 항목 | 전 | 후 | 커밋 |
|---|---|---|---|
| ① 쪼갠 큐 콘솔 이름 | `Chorus 3 12` · `Chorus 3 22` | `Chorus 3 1 of 2` · `Chorus 3 2 of 2` | `37c51bc9` |
| ② 죽은 코드 | 사다리 컨셉 어댑터 · `SongLookMemory` 배선 · `reuse_reason` 잔존 | 제거(10파일, +36 −170) | `c1f8a53d` |
| ③ 큐 설명 밝기 | 설명 「최대 N%」가 CUE SHEET KEY 와 10구간 중 1구간만 일치 | 설명에서 수치 제거, 변화 서술은 유지 | `80464c5a`(원인) · `f0d2dd58`(처방) |

## 2. ① 쪼갠 큐 이름

**원인.** 마디 분할(`_disambiguate_split_names`)이 붙인 `(1/2)` 를 콘솔 라벨 정리(`_safe_song_cue_name`)의 허용 문자 표 `[A-Za-z0-9 _-]` 가 괄호·빗금만 지워 숫자 둘이 붙었다.

**처방.** 허용 문자 표는 넓히지 않았다. 괄호·빗금이 콘솔 명령(`Store Sequence N Cue M 'name'`)의 따옴표 안에서 안전한지는 이 카드가 재지 않았기 때문이다. 대신 접미사만 허용 문자 안의 모양 `1 of 2` 로 옮긴다(`server/design/song_cue_render.py` `_SPLIT_SUFFIX`). 화면 이름(CUE SHEET·G7 판정이 읽는 `(1/2)`)은 그대로다.

## 3. ② 죽은 코드

호출처는 제거 직전에 다시 쟀다. 대상 이름 grep 이 정의·배선·시험을 모두 찾아냈으므로(양성 대조) 계기는 눈멀지 않았다.

| 대상 | 운영 호출처 | 처리 |
|---|---|---|
| `session_bridge.build_concept_report_from_songcue_sections` | 0 — 정의와 `__all__` 뿐 | 함수 삭제. 입력 도우미 `_raw_sections_from_pairs` 는 시험 세 파일(t452·t455·t461)이 컨셉 파이프라인에 곡을 넣는 입구로 쓰므로 남김 |
| `SongLookMemory`(`server/looks/song_history.py`) | 0 — `session.py` 가 만들어 `build_toolset(song_look_memory=)` 로 넘기지만 `build_toolset` 본문이 읽지 않음 | 모듈 삭제, `session.py` 3줄(import · 생성 · 인자) · `tools.py` 3곳(import · 인자 · 독스트링 문단) 삭제 |
| `LOOK_POOL_EXHAUSTED` | 상수 자체는 t480 D3 에서 이미 사라짐. 남은 것은 `SongCueLookSelection.reuse_reason` 필드와 그 독스트링 — 값을 넣는 곳 0 | 필드 삭제 |

**문서.** `docs/proposals/song-structure-lighting-standard.md` §12 의 「항목 2 는 절반이 닫혔다 — `song_history.py` 가 막는다」에 **만료 고지**를 붙였다. 날짜가 박힌 기록이라 문장은 고치지 않았다. **곡 사이 룩 재사용을 막는 장치는 t480 이후 없다** — t486 이 없앤 것이 아니라, 이미 동작하지 않던 배선을 지운 것이다.

## 4. ③ 큐 설명과 CUE SHEET 밝기 불일치

### 4.1 원인(실측)

`brightness_probe.py`: t482 실경로 페이로드와 같은 10구간 곡을 두 번 만들었다. 두 번째는 Chorus 1 의 D 레벨만 5 → 2 로 바꿨다(재려는 축 하나만 건드림).

| 구간 | D | 시트 KEY | 컨셉 구간 이름 | 설명 「최대 %」 |
|---|---|---|---|---|
| Intro | 2 | 50 | Intro | 25 |
| Verse 1 | 3 | 70 | Verse | 45 |
| Pre-Chorus 1 | 4 | 40 | Rap/Solo/Dance Break | 45 |
| Chorus 1 | 5 | 100 | Chorus | 75 |
| Verse 2 | 3 | 70 | Verse | 38 |
| Pre-Chorus 2 | 4 | 40 | Rap/Solo/Dance Break | 38 |
| Chorus 2 | 5 | 100 | Chorus | 76 |
| Bridge | 2 | 20 | Bridge | 30 |
| Chorus 3 | 5 | 100 | Final Chorus | 100 |
| Outro | 3 | 70 | Rap/Solo/Dance Break | 100 |

- 시트 == 설명: **1/10**
- 대조군(Chorus 1 D 5 → 2): 시트 100 → **50**, 설명 75 → **75**(안 움직임)

**원인.** 두 값은 서로 다른 밝기 모델에서 나온다.
- 시트 KEY: 조립기 `song_cue_composer._dimmer_data`(`:715`) — 구간 D 레벨 예산 `dimmer_pct` 의 중간값
- 설명: `session_bridge._raw_sections` 가 컨셉 파이프라인에 넘기는 것은 라벨·시각·팔레트뿐이다. D 레벨·예산은 넘기지 않는다. 컨셉 파이프라인은 밝기를 자체 고정 사다리(`server/concept/density.py` — 1번 후렴 `:448` 75, 2·3번 `min(100, 60 + 8k)`, Final Chorus 100)에서 낸다

**근본 원인 재확인.** 「설명이 시트와 다른 원천을 읽는다」가 증상이 아니라 원인인가? 대조군이 답했다. 입력의 D 를 바꾸면 시트는 따라가고 설명은 안 따라간다. 즉 설명의 밝기는 **입력 계약상 D 에 닿을 길이 없다**. 두 큐 생성 경로를 합치는 일(REQ-003)이 끝나기 전에는 어느 쪽을 고쳐도 한쪽이 지어낸 값이 된다.

### 4.2 처방(리드 결정 A)

틀린 숫자는 없는 숫자보다 나쁘다. 화면으로 나가는 유일한 자리 `session_bridge._concept_rows` 에서 `describe()` 문장의 「최대 N%」 절만 뺀다(`_screen_description`). 절을 뺐더니 남는 것이 없는 행은 「그룹·색 변화 없음」을 낸다. `describe()` 자체(REQ-023, 다른 시험 둘이 직접 재는 함수)는 바꾸지 않았다. UI 출처 표식(`ui/src/components/conceptGlance.ts` `DESCRIPTION_SOURCE`)은 「밝기 수치는 CUE SHEET 기준」으로 바꿨다.

**처방 뒤 대조군 재실행**(`brightness_probe_after.txt`): 10구간 모두 설명의 `%` 수치가 **0건**(`None`). 대조군도 D 5 → 2 에서 시트는 100 → 50 으로 움직이고 설명은 숫자를 내지 않는다.

**다른 카드로 넘긴 것.** 재매핑이 `Pre-Chorus`·`Outro` 를 `Rap/Solo/Dance Break` 로 분류하는 문제(`server/concept/gates.py:156`)는 리드가 **t489** 로 뺐다. 이 카드에서 고치지 않았다.

## 5. 시험

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| ① RED | `pytest server/tests/test_split_cue_console_name_t486.py`(고치기 전) | 4 failed · 2 passed(대조군 둘은 고치기 전에도 초록) — `['Chorus 3 12', 'Chorus 3 22']` | `red_name.txt` |
| ① GREEN | 같은 명령 | 6 passed | `green_name.txt` |
| ③ RED | `pytest server/tests/test_concept_description_no_brightness_t486.py`(고치기 전) | 3 failed · 2 passed(서술 유지 불변식 둘) | `red_desc.txt` |
| ③ GREEN | 위 파일 + `test_concept_glance_t482.py` | 16 passed | `green_desc.txt` |
| 뮤테이션 | `uv run python .moai/reports/t486/mutate.py` | **4/4 CAUGHT**(분할 접미사 변환 제거 · 허용 문자에 괄호·빗금 추가 · 설명 원문 그대로 · 대체 문구 제거). 회차마다 `assert mutated != original`, 끝에 추적 파일 복원 확인 | `mutation.txt` |
| 서버 범위 | `RUFF_NO_CACHE=true pytest server/tests -k "concept or songcue or song_ or session or tools or timeline or upload or split or cue_render or runbook or glance or looks or overlap or lint or preserve or hunk"`(커밋 뒤) | 2939 passed · 24 skipped | `pytest_scope.txt` |
| 서버 범위(main 머지 뒤) | 위 선택 + `design` | 3257 passed · 24 skipped | `pytest_scope_after_merge.txt` |
| UI 전체 | `npx vitest run` | 32 파일 · 728 passed | `vitest_full.txt` |
| 타입 | `tsc --noEmit -p ui` | 오류 0 | `tsc.txt` |
| 린트 | `ruff check --no-cache` + `ruff format --no-cache --check`(바뀐 .py 전부) | All checks passed | — |

**첫 범위 실행의 빨강 하나.** 커밋 뒤 첫 실행에서 `test_songcue_bundle.py::test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state` 가 빨갰다. `tools.py` 헝크 재고 94 → 93 — `build_toolset` 의 `song_look_memory` 인자와 독스트링 문단을 지우자 기준 968·971 두 헝크가 하나로 합쳐졌다. 새 시작점 0, 보호 구간 겹침은 t476 허용분 `(237, 0)` 그대로(`measure_hunks.txt`). 재고를 갱신했다(`98b68d68`, 커밋 뒤 측정).

**시험 회계.** 추가 11(① 6 · ③ 5) · 삭제 2(t444 `test_mismatched_palette_count_is_reported_not_raised`, t482 `test_songcue_path_has_no_role_source` — 둘 다 은퇴한 어댑터만의 동작) · 입구만 바꾼 것 7(session_bridge 4 · t444 2 · t452 1, 공통 실행기 `_run_concept_pipeline` 로) · 단언을 바꾼 것 1(t482 `test_description_is_exactly_describe_over_the_resolved_states` → `_screen_description(describe(...))` 와 대조) · 재고 상수 1(헝크). 순증 +9.

## 6. 안 잰 것

- **전체 서버 시험(14,000여 개)은 로컬에서 돌리지 않았다.** 범위 선택만 돌렸고 전체는 PR CI 가 잰다. 그래서 「직전 상태 대비 통과 수 차이」는 범위 선택 안에서만 말할 수 있고, 같은 선택을 기준 커밋에서 돌리지는 않았다 — 회계는 위 §5 의 추가·삭제 목록으로 대신한다.
- **실기 콘솔.** `Chorus 3 1 of 2` 가 콘솔 큐 목록에 그대로 서는지 쏘지 않았다. 허용 문자 안이라 정리 단계에서는 안 지워지지만, MA3 가 공백·소문자 `of` 를 바꾸는지는 모른다.
- **괄호·빗금이 따옴표 안에서 안전한가.** 재지 않았다. 그래서 허용 문자 표를 넓히지 않았다.
- **브라우저 화면.** 서버 설명 문자열과 UI 상수만 바꿨고, 헤드리스 브라우저로 컨셉 패널을 다시 띄우지는 않았다(t482 의 `glance_probe.js` 재실행 안 함).
- **t485 와의 병합.** 이 판정서를 쓰는 시점에 t485 는 main 에 없다. 리드 조건대로 t485 가 먼저 머지되면 main 을 다시 합치고 서버·UI 시험을 다시 돌려 여기에 덧붙인다.

## 7. 남은 위험

- REQ-023 은 설명에 「최대 밝기」를 넣으라고 적는다. `describe()` 는 여전히 넣지만 **화면은 뺀다.** SPEC 문면과 화면이 갈린다 — 두 경로 통합(REQ-003) 뒤에는 시트 KEY 로 되살릴 수 있다.
- 곡 사이 룩 재사용 방지 장치가 없다(§3). t480 이후 이미 그랬고, 표준 문서에 고지했다.
- 컨셉 파이프라인의 재매핑 오분류(t489)는 남아 있다 — 설명의 그룹·색 서술도 그 분류 위에 선다.
