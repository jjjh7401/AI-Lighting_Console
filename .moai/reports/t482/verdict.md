# t482 — 컨셉 패널 원천 데이터: 큐 설명 연결 + 「한눈에」 5단계 (AC-018 일부·AC-049)

- 카드: t482 (SPEC-LDDESIGN-001, `sync-evidence/ac_ui_closeout.md` §3 AC-018·049 FAIL 후속)
- 워크트리 `.claude/worktrees/t482`, 브랜치 `WT-concept-glance-data`, 기준 `4ecbf879`(= origin/main, PR #532 머지). PR 직전 `origin/main` 재확인 — 뒤처짐 0(t480 미머지).
- 커밋 `faeb2c89`(구현) · `258d7f3b`(출처 표식). 콘솔 접속 0. 서버 변경은 `server/concept/session_bridge.py` 하나 — `server/design`·`tools.py`·`session.py` 0줄.

## 1. 리드 결정(2026-09-28)과 이 카드가 한 것

| 항목 | 결정 | 결과 |
|---|---|---|
| 큐 설명 | A — `describe()` 연결, 「무대에서」 칸 | **연결함.** `concept_report.rows[].description`. 4칸 설명의 「무대에서」 칸에 표시 |
| 「한눈에」 5단계 | 리드 제안 규칙으로 구현, `rule:"lead-proposed-2026-09-28"` 표식 | **구현함.** 서버는 단계 배정만, 카드 수치는 UI 가 CUE SHEET 와 같은 구간 데이터에서 계산 |
| 인과 불릿 | B 는 t480 머지 뒤 별도 카드 | 「데이터 없음 — 워크시트 concept 원문이 서버에서 오지 않는다」 유지 |
| 「그래서 보이는 것」·4칸 나머지 | 데이터 없음 유지 + 사유 | 유지. 「무슨 뜻」·「왜 이렇게 제안했나」·「바꾸려면」은 각자 사유를 단 데이터 없음 |

## 2. 무엇을 바꿨나

**서버 — `session_bridge.py`**
- `_concept_rows`: 행마다 `description = describe(직전 상태, 이 상태, 행 ops, compute_cue_headroom(이 상태))`. 첫 큐의 직전 상태는 `resolve_sequence` 초기 상태(`dim={}, color=None, pos="home", motion=0`)와 같다. `describe()`(REQ-023/070)는 구현돼 있었지만 시험에서만 불리고 있었다.
- `glance_stages(roles)` + `GLANCE_STAGES`·`GLANCE_RULE`: 역할(`SectionDecision.role`) 목록만 보고 단계별 화면 구간 위치를 낸다. 규칙: 첫 후렴 f, 마지막 후렴 l, 끝에서 둘째 후렴 p — 시작 = f 앞 intro · 쌓기 = f 앞 나머지 · 강조 = f..p · 예고 = p 와 l 사이 · 정점→마무리 = l..끝. 후렴이 없으면 끝의 finale 연속 구간을 정점→마무리로 둔다. 빈 단계는 사유를 단다. **역할이 하나라도 없으면 배정하지 않는다**(`available: false` + 사유).
- `build_concept_report`(plan 경로)는 리포트가 만들어졌을 때만 `glance` 를 붙인다. 리포트를 못 만든 경우의 `{available: False, reason}` 두 키 계약은 바꾸지 않았다(기존 시험 4건이 이 계약을 고정). 사다리 경로(`build_concept_report_from_songcue_sections`)는 역할 원천이 없어 `glance.available: false` + 사유.

**UI**
- `conceptGlance.ts` `glanceView(timeline)`: 카드 수치(Q 범위·구간·시간·색 HEX·밝기 범위)를 CUE SHEET 와 같은 `sections` 와 같은 도우미(`cueLabel`·`formatTc`·`sectionEndMs`·`sectionHex`)로 계산한다. 한 줄 설명은 수치로만 조립한다(「구간 2개 · 24.0초 · 밝기 32–70%」). 맨 위 한 줄 분석도 수치 + 규칙 표식(「… 규칙 lead-proposed-2026-09-28(감독 확인 전)」). 서버 배정 위치가 구간 수 범위를 벗어나면 배정 전체를 믿지 않는다.
- `explanationCells(report, position)`: 표의 구간 행을 누르면 4칸 설명. 「무대에서」 = 그 구간 section 행의 `description` + **출처 표식**(§3).
- `ConceptPanel` 이 `timeline` 을 받아 카드와 4칸 설명을 그린다. `RunbookMode` 는 한 줄 연결만 했다.

## 3. 찾은 것 — 큐 설명과 CUE SHEET 밝기가 다르다

같은 곡에서 Chorus 1 의 CUE SHEET 밝기는 **KEY 100 / BACK 80**, 큐 설명은 **「색 red · 최대 75%」** 다(`glance_probe.json` `sheet[3]` / `payload_roles.json` rows sp 3). 설명은 컨셉 파이프라인의 해석 상태에서, 시트는 조립기 경로에서 나온다. 큐 생성 경로가 아직 둘이라서(REQ-003, AC-017 UNVERIFIED) 생기는 차이다. 설명 자체는 지어낸 값이 아니지만, 출처 없이 시트 옆에 두면 REQ-097 이 경고한 "어느 쪽을 믿을지 모르는" 상태가 된다. 그래서 「무대에서」 칸에 출처 표식 「컨셉 파이프라인 계산 — CUE SHEET 밝기와 다를 수 있다(큐 생성 경로 미통합, REQ-003)」을 붙였다(`258d7f3b`). **두 경로를 합치는 일(REQ-003·AC-017)은 이 카드 범위 밖이다.**

## 4. 증거

| 항목 | 명령 | 결과 | 원본 |
|---|---|---|---|
| 서버 RED | `pytest server/tests/test_concept_glance_t482.py`(구현 전) | 수집 오류 — `GLANCE_RULE` import 실패 | `red_server.txt` |
| 서버 GREEN | 같은 명령 | 12 passed | `green_server.txt` |
| 서버 범위 | `pytest server/tests -k "concept or timeline or session_bridge or songcue"` | **1092 passed**, 4 skipped. 처음 14 failed → 원인 두 가지: 행/리포트 키 **정확 일치 잠금**(t455·t457 — t461 과 같은 "추가만" 관례로 새 키를 명시 추가), 리포트 실패 시 두 키 계약(→ glance 를 리포트가 있을 때만 붙이도록 코드를 고침, 시험은 그대로) | `pytest_scope.txt` |
| UI RED | `vitest run src/components/conceptGlance.test.ts`(구현 전) | 모듈 없음으로 실패 | `red_ui.txt` |
| UI 전체 | `vitest run --reporter=verbose` | 32 파일 · **728 passed** | `vitest_full.txt` |
| 타입 | `tsc --noEmit -p ui` | 제품 코드 오류 0(측정 때 1건은 임시 하니스 — 측정 뒤 삭제) | `tsc.txt` |
| 린트 | `ruff format` + `ruff check`(바뀐 .py 5개) | All checks passed | — |
| 가드 변이 | `python3 mutate.py` | **6/6 CAUGHT**(강조에 마지막 후렴 포함 · 역할 없이 배정 · 고정 문장 설명 · 카드 밝기 상수 · 카드 색을 다른 원천에서 · 출처 표식 제거). 실행 뒤 추적 파일 복원 확인 | `mutation.txt` |
| 실경로 페이로드 | `uv run python make_payload.py` — 10구간, 역할은 **실제 판정기** `_infer_confirmed_role`(D 레벨 순위)로 | 역할 `intro verse verse chorus verse verse chorus bridge chorus finale` → 배정 시작[0] 쌓기[1,2] 강조[3..6] 예고[7] 정점→마무리[8,9]. 설명 예 「+KEY · 색 blue · 최대 10%」 | `payload_roles.json` |
| 브라우저 | `glance_probe.js`(헤드리스 Chrome 1600×1000) — 카드 값을 **같은 화면의 CUE SHEET 에서 읽은 값**과 대조 | 카드 5장 × (Q 범위·시작 시각·색 HEX·밝기 범위) **20/20 일치**, 구간 목록 5/5 일치. 패널 기본 접힘. 구간 행(Chorus 1) 클릭 → 4칸, 「무대에서」 = 서버 행 설명과 같음 + 출처 표식. 인과 불릿·「그래서 보이는 것」은 데이터 없음 유지. 페이지 오류 0 | `glance_probe.json`, `concept_panel_open.png` |

## 5. 판정

- AC-049(「한눈에」 5단계 카드가 큐 데이터에서 파생·하드코딩 없음): **FAIL → PASS(조건부)** — 수치는 시트와 20/20 일치, 값을 바꾸면 카드가 따라 바뀐다(단위 시험), 변이로 상수·다른 원천을 넣으면 시험이 잡는다. **조건: 구간→단계 배정 규칙은 리드 제안이며 감독 확인 전**(화면에 표식으로 보인다).
- AC-018(컨셉 패널): 4칸 설명이 **펴진다** — 이전에는 항목 자체가 없었다. 「무대에서」 1칸만 원천이 있고 나머지 3칸·인과 불릿·「그래서 보이는 것」은 사유를 단 데이터 없음 → **여전히 일부 FAIL**(원천 없음, 리드 결정대로).

## 6. 감독 확인 항목

1. 「한눈에」 구간→단계 배정 규칙(§2 서버 규칙) — 감독이 확정하면 `GLANCE_RULE` 표식을 바꾼다.
2. 큐 설명(「무대에서」)과 CUE SHEET 밝기가 다른 문제(§3) — 두 경로를 합치는 REQ-003/AC-017 작업이 필요하다.
3. 4칸 설명을 여는 항목으로 **표의 구간 행**을 골랐다(REQ-079 는 "탭 안의 항목(불릿·칩)"이라 적었지만 불릿·칩 원천이 아직 없다).

## 7. 안 잰 것

- 앱 본체(App + 웹소켓 + 서버)가 아니라 하니스로 띄웠다. 페이로드는 서버 실경로(`_song_timeline_payload`)로 만들었지만 곡은 합성곡 하나(10구간)다.
- 실제 앱의 역할 판정은 두 가지다 — 자연어 판독(`_section_role`)과 D 레벨 대체 판정(`_infer_confirmed_role`). 브라우저 확인은 뒤의 것만 썼다.
- 사다리 경로(Rain 류 `prepare_songcue`)는 역할 원천이 없어 「한눈에」가 항상 데이터 없음이다 — 그 경로의 곡 화면으로는 띄워 보지 않았다.
- 카드 폭이 좁은 화면(모바일)은 안 쟀다.
