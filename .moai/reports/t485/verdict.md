# t485 — 컨셉 패널 탭 1 인과 불릿 (SPEC-LDDESIGN-001 AC-018 잔여 · REQ-013/032/080)

- 카드: t485 · 워크트리 `.claude/worktrees/t485` · 브랜치 `WT-concept-bullets`
- 기준: 착수 시점 `origin/main` = `b29bc497` 이후. PR 직전 `origin/main`(`5cab05b7`, 문서 2개만 바뀜 — t488 `src/DESIGN.md`) 병합 `e1183297`.
- 커밋: `049577bd`(구현) · `b79103b0`(실제 호출 지점 시험). 콘솔 접촉 0(가짜 콘솔).
- 바뀐 코드: `server/concept/session_bridge.py` · `server/web/session.py` · `ui/src/protocol.ts` · `ui/src/components/ConceptPanel.tsx` · `ui/src/components/conceptBullet.ts`(신규) · `ui/src/styles.css`. 시험: `server/tests/test_concept_bullet_t485.py` · `ui/src/components/conceptBullet.test.ts`.

## 판정

- **AC-018 인과 불릿 부분: FAIL → PASS(조건부).** 감독이 인터뷰 Q1 에 준 글자가 런북 타임라인으로 가서 탭 1 에 "원문 그대로" 배지·출처와 함께 바이트 그대로 보인다. 원문이 없으면 빈칸 + 사유. 조건: 원천은 **인터뷰 Q1** 이다(§2 — 워크시트 YAML 은 앱에서 안 읽힌다).
- **AC-018 전체: 여전히 일부 FAIL.** 남은 것은 §4(「그래서 보이는 것」)·§6(불릿 클릭 4칸·탭 2·3 본문).

## 1. 무엇을 바꿨나

**서버**
- `concept_bullet(records)` — `DirectorInterview.audit_trail()` 에서 Q1 기록을 찾아 감독이 실제로 준 글자만 싣는다.
  - 직접 입력(`free_text`) → 친 글자 그대로(해석값 `value` 가 아니다), 제안 선택(`option`) → 고른 제안, 요청 문장(`pre_specified`) → 지시문에서 읽은 부분. 출처 표식이 셋 다 다르다.
  - 글자는 기존 `render_concept_bullet`(REQ-032 항등 함수)을 통과시킨다 — 요약·윤문 0.
  - **빈 답 자동 초안(`auto_draft`, confirmed False) 은 원문으로 싣지 않는다.** 그 값은 카드의 첫 제안이지 감독 말이 아니다. 「원문 그대로」 배지를 달면 감독이 하지 않은 말을 감독 말로 보이게 된다.
  - 기록 없음·빈 문자열도 `available: False` + 사유.
- `_song_timeline_payload(..., interview_records=())` → `concept_bullet` 키 추가(추가만). 유일한 호출 지점 `_song_send_timeline` 이 `state.records` 를 넘긴다.

**UI**
- `conceptBulletView` — 줄바꿈으로 불릿을 나누고 빈 줄만 버린다. 각 줄의 글자(앞뒤 공백 포함)는 바꾸지 않는다(CSS `white-space: pre-wrap`).
- `ConceptPanel` 탭 1: 배지 「원문 그대로」 + 출처(예: 「인터뷰 Q1 — 직접 입력」) + 불릿. 없으면 「인과 불릿 · 데이터 없음 — <서버 사유>」.

## 2. 원천 판정 — 왜 인터뷰 Q1 인가

- REQ-013 은 원천을 **워크시트 YAML `concept` 필드**로 적었다. 로더 `server/concept/worksheet.py:248 load_worksheet` 는 있지만 **시험 밖에서 부르는 곳이 0** 이다(`grep -rn "load_worksheet\|concept.worksheet import" server ui/src` → 정의 1줄 + `color_strip.py` 의 `Palette` 타입 import 1줄, 호출 0). 앱 경로에 워크시트가 들어올 입구가 없다.
- 앱에서 감독이 컨셉을 말하는 자리는 인터뷰 Q1 하나다(`server/design/interview.py` `Q1_CONCEPT`, 자유 입력은 `_parse_free_text` 가 그대로 돌려준다 — `interview.py:1082`).
- 그래서 원천은 Q1 이고, 화면 출처 표식이 「인터뷰 Q1 — …」 로 그 사실을 보인다. **워크시트 입구를 앱에 여는 것은 이 카드 범위 밖**이다(감독 결정 필요 — §7).
- 업로드 길(`tools.py` `build_upload_song_plan`)은 런북 타임라인 이벤트를 내지 않고 채팅 도구 결과로 끝난다(`tools.py:3250-3600` 에 `timeline` 0회). 그래서 싣지 않았다 — 읽는 화면이 없다.

## 3. 증거

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| 서버 RED | `pytest server/tests/test_concept_bullet_t485.py`(구현 전) | 수집 오류 — `concept_bullet` import 실패 | `red_server.txt` |
| 서버 GREEN | 같은 명령 | **11 passed** | `green_server.txt` |
| 서버 범위 | `pytest server/tests -k "concept or timeline or session_bridge or songcue or interview"` | 1024 passed, 4 skipped, 0 failed | `pytest_scope.txt` |
| 서버 전체 | `pytest server/tests`(커밋 `049577bd` 뒤) | **14369 passed, 35 skipped, 0 failed** | `pytest_full.txt` |
| main 병합 뒤 | t485·t482·배선 시험 | 28 passed | `pytest_after_merge.txt` |
| UI RED | `vitest run src/components/conceptBullet.test.ts`(구현 전) | 모듈 없음 | `red_ui.txt` |
| UI 전체 | `vitest run` | 33 파일 · **734 passed**(병합 뒤 같음) | `vitest_full.txt`, `vitest_after_merge.txt` |
| 타입 | `tsc --noEmit -p ui` | 오류 0 | `tsc.txt` |
| 린트 | `ruff check` + `ruff format --check`(바뀐 .py + 증거 .py) | All checks passed | — |
| 가드 변이 | `uv run python .moai/reports/t485/mutate.py` | **6/6 CAUGHT**, 각각 의도한 시험이 잡음(아래). 실행 뒤 추적 파일 복원 확인(`git status`) | `mutation.txt` |
| 실제 세션 페이로드 | `uv run python .moai/reports/t485/make_payload.py` — 가짜 콘솔 세션을 인터뷰부터 돌려 나간 `song_timeline` 이벤트 | 두 줄 인과 문장 → `available: true`, 글자 동일 / 빈 답 → 자동 초안 사유 | `payload_causal.json`, `payload_blank.json` |
| 브라우저 | `bullet_probe.js`(헤드리스 Chrome 1600×1000) | 패널 기본 접힘 · 탭 1 활성 · 배지 「원문 그대로」 · 출처 일치 · **화면 불릿 2줄 = 서버 원문 2줄**(바이트 비교 `lines_match: true`) · 빈 답 곡은 사유 표시 · 페이지 오류 0(우회 적용 시 — §5) | `bullet_probe.json`, `concept_bullet_causal.png`, `concept_bullet_blank.png` |

변이별로 잡은 시험:

| 변이 | 잡은 시험 |
|---|---|
| S1 호출 지점이 기록을 안 넘김 | `TestRealSendSiteCarriesTheBullet` 2건(페이로드 함수를 직접 부르는 시험은 이 변이에 초록이다 — 그래서 실제 세션 시험을 따로 넣었다) |
| S2 자동 초안도 원문 인정 | `test_auto_draft_is_not_the_directors_words` + 실제 세션 빈 답 시험 |
| S3 친 글자 대신 해석값 | `test_free_text_wins_over_value_when_they_differ` |
| S4 공백 접기(윤문) | `test_free_text_is_carried_byte_for_byte` + 페이로드 시험 |
| U1 화면에서 줄 공백 깎기 | `keeps every line byte-for-byte…` |
| U2 배지 문자열 변경 | `badge text is fixed` |

## 4. 「그래서 보이는 것」 칸 — rows description 과 겹치는가

**판단: 겹친다. 채우지 않는다(데이터 없음 유지).**

t482 가 서버 실경로로 만든 10구간 페이로드(`.moai/reports/t482/payload_roles.json`)에서 section 행 설명 10개를 같은 표의 칸과 대조했다.

- 설명의 구성은 「직전 큐 대비 그룹 증감(+BACK, -FOH…) · 색 X · 최대 N%」 이다 — 전부 **색·기구·밝기 축**이다. 표에는 이미 「색」·「기구·밝기」 칸이 있다.
- 색을 말한 설명 **8/8** 이 같은 줄 「색」 칸과 같은 색이다 → 순수 중복.
- 「최대 N%」 는 같은 구간 CUE SHEET 밝기(KEY 값)와 **1/10** 만 같다(예: Chorus 1 설명 75% ↔ 시트 KEY 100, Bridge 30% ↔ KEY 20). t482 §3 이 이미 찾은 두 경로 차이(REQ-003·AC-017)다.
- 따라서 이 설명을 「그래서 보이는 것」에 넣으면 (1) 앞 칸을 되풀이하고 (2) 한 줄에 **서로 다른 밝기 숫자 두 개**가 생겨 REQ-097 이 경고한 "어느 쪽을 믿을지 모르는" 상태가 된다.
- **t486 병합 뒤 재측정(§8)**: t486 이 설명에서 「최대 N%」 를 뺐다. 같은 곡을 병합 트리로 다시 내면(`remeasure_desc.py` → `payload_roles_after_t486.json`) 설명은 「그룹 증감 · 색 X · (Y 복원)」 만 남고 밝기 숫자는 0/10 이다. 밝기 모순 근거는 사라졌지만 **색 8/8 중복은 그대로**이고 설명은 여전히 "무엇이 바뀌었나"다 — 결론(비워 둠)은 바뀌지 않는다.
- REQ-080 의 이 칸은 앞 다섯 칸의 결과(관객이 보는 효과)를 말하는 자리다. 그 원천은 현재 서버에 없다 — 설명은 "무엇이 바뀌었나"이지 "그래서 무엇이 보이나"가 아니다. 4칸 설명의 「무대에서」 칸(t482)에 출처 표식과 함께 이미 쓰이고 있으므로 원천이 버려지는 것도 아니다.

## 5. 찾은 것 — 재질의 대기 타임라인에서 런북 화면 전체가 빈다(기존 결함, 범위 밖)

- 재현: 실제 세션 페이로드(`payload_causal.json`, `lifecycle: requires_requery`)를 그대로 런북에 먹이면 `CueSheetTimeline` 이 `Cannot read properties of null (reading 'toFixed')` 로 터지고 **`#root` 가 빈다(길이 0)**. `bullet_probe.json` `raw_payload_without_workaround`: `panel_missing: true`, 페이지 오류 4건.
- 원인: 번들이 없을 때 서버가 구간마다 `"fade_seconds": null` 을 싣는다(`server/web/session.py:1498` `fade_by_section.get(...)`). 화면은 `undefined` 만 막는다(`ui/src/components/CueSheetTimeline.tsx:773-775`, 타입은 `fade_seconds?: number` — `null` 이 타입 밖).
- 이 카드의 diff 는 두 줄 어디도 건드리지 않았다(`git diff origin/main...HEAD --stat` 8파일 중 `CueSheetTimeline.tsx`·`fade` 0). 확인용 하니스에서만 `null` 을 빼는 우회를 넣고 패널을 봤다(`acuiHarness.tsx.txt`, `?raw` 면 우회 없음).
- **리드에게 새 카드로 올린다** — 재질의 카드가 떠 있는 동안 감독 화면이 통째로 비는 결함이다.

## 6. 안 잰 것

- 앱 본체(App + 웹소켓)가 아니라 하니스로 띄웠다. 페이로드는 실제 세션 경로(`_song_send_timeline`)가 낸 이벤트 그대로다(가짜 콘솔).
- 제안 선택(`option`)·요청 문장(`pre_specified`) 출처는 단위 시험으로만 쟀다. 브라우저는 직접 입력·빈 답 두 곡만 봤다.
- 요청 문장 출처의 글자는 `_SONG_CONCEPT_HINT` 정규식이 잘라 낸 부분이다 — 감독 문장 전체가 아니다. 그 자르기의 경계는 재지 않았다(이 카드 이전부터 있던 동작).
- REQ-079 의 「항목(불릿·칩) 클릭 → 4칸 설명」 은 불릿에 붙이지 않았다 — 불릿 4칸(무슨 뜻·왜 이렇게 제안했나·바꾸려면)을 채울 원천이 없다. 4칸은 여전히 표 구간 행에서 편다(t482).
- 탭 2·3 본문은 여전히 데이터 없음.
- 좁은 화면(모바일)은 안 쟀다.

## 7. 감독 확인 항목

1. 인과 불릿 원천을 **인터뷰 Q1** 로 둔 것(REQ-013 은 워크시트를 적었다). 워크시트 YAML 입구를 앱에 열지는 별도 결정.
2. 「그래서 보이는 것」 은 §4 대로 비워 둔다 — 채우려면 구간별 "결과 효과" 원천이 필요하다.

## 8. t486(PR #539) 병합 — 충돌 해소와 재검증

- `origin/main` = `7f8990fc`(t486) 병합, 병합 커밋 `107420f1`.
- 충돌 1곳: `server/concept/session_bridge.py` `__all__`. t486 이 사다리 경로 어댑터 `build_concept_report_from_songcue_sections` 를 은퇴시켰고(함수 정의도 삭제 — 병합 트리 `grep "def build_concept_report_from_songcue_sections"` → 0) 이쪽은 `concept_bullet` 을 더했다 → `concept_bullet` 만 남겼다. `session.py` 는 자동 병합(t486 의 SongLookMemory 삭제와 이쪽 `concept_bullet` 줄이 겹치지 않음).
- 의미 충돌 없음: 인과 불릿의 원천은 인터뷰 Q1 이고, t486 이 바꾼 것은 큐 설명(`rows[].description`)과 그 출처 문구(`conceptGlance.ts` `DESCRIPTION_SOURCE` 「밝기 수치는 CUE SHEET 기준」)다. 두 원천이 다르고 이 카드는 그 문구를 건드리지 않는다. 영향은 판정서 §4 의 근거 하나(밝기 불일치)뿐이라 §4 를 재측정값으로 고쳤다.
- 재검증(병합 커밋 뒤):
  - 서버 전체 `pytest server/tests` → **14380 passed, 35 skipped, 0 failed** (`pytest_full_after_t486.txt`)
  - UI `vitest run` → 33 파일 · **734 passed** (`vitest_after_t486.txt`) · `tsc --noEmit` 오류 0 (`tsc_after_t486.txt`)
  - 주의: 병합을 커밋하기 **전에** 돌린 첫 전체 실행은 2 failed 였다 — `test_overlap_preserve` 의 건드린 파일 집합(t486 이 지운 `server/looks/song_history.py` 를 git 은 세고 게이트는 못 봄)과 `test_songcue_bundle` 헝크 대조. 둘 다 `<BASE>..HEAD` 를 보는 커밋 경계 가드다(규약 §3.1). 병합 커밋 뒤 두 파일 86 passed(`gates_after_merge_commit.txt`), 이어서 위 전체 실행 0 failed.
