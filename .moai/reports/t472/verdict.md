# t472 판정서 — 런북 MIB 칸에 「켜진 채 이동」 경고 표시

- 카드: t472 · SPEC-LDDESIGN-001 t471 후속(화면) · REQ-LDDESIGN-066 · 근거 `.moai/reports/t471/verdict.md` §4
- 브랜치: `WT-mib-warning-ui`, 기준 `origin/main` ea91c389
- 콘솔 쓰기: 0
- 판정: **PASS**

## 0. 감독용 요약

런북 CUE SHEET 의 MIB 칸이 이제 「⚠ 어둠 2.07초 — 켜진 채 이동」처럼 경고를 띄운다.
무빙을 어둠 속에서 미리 옮기려는데 어둠이 모자라(필요 4.6초) 불이 켜진 채 움직이는 큐다.
조립기는 이 경고를 이미 계산하고 있었지만(카드 t471) 화면까지 오지 않았다.

## 1. 변경

| 파일 | 변경 |
|---|---|
| `server/web/session.py` `_song_timeline_payload` | 사전이동 큐가 있는 구간에만 `dark_window_seconds`(초, 모르면 null)·`live_move`(참/거짓) 두 키 추가. 사전이동이 없는 구간의 사전은 그대로(추가만) |
| `ui/src/protocol.ts` `SongTimelineSection` | 두 선택 필드 추가 |
| `ui/src/components/runbookM7.ts` | `liveMoveWarning()` 신설. `mibCellText`(컨셉 짝 없음 경로)는 경고가 있으면 경고 문구, `conceptCells`(컨셉 짝 있음 경로)는 기호 뒤에 경고를 덧붙임 |
| `server/tests/test_timeline_mib_warning_t472.py` | 서버 시험 3개 |
| `ui/src/components/runbookMibWarning.test.tsx` | 화면 시험 6개 |

**카드 문면보다 한 곳 넓혔다 — 이유.** 카드는 `mibCellText` 만 지목했지만, 그 함수는 컨셉 리포트가 짝지어지지
**않았을 때만** 쓰인다(`conceptCells` 가 `concept === null` 일 때 부른다). 짝지어진 리포트가 정상 경로이고(t458,
`runbookServerPayload.json` 에서 20행이 8구간에 짝지어짐), 그때 MIB 칸은 컨셉 3상태 기호(◐ dark 등)를 쓴다.
`mibCellText` 만 고치면 정상 경로에서 경고가 여전히 안 보인다. 그래서 두 경로 모두에 붙였다. 경고가 없는 칸은
두 경로 모두 지금과 글자 그대로다.

## 2. 판정

| 확인 | 명령 | 결과 |
|---|---|---|
| 서버 RED | `uv run pytest server/tests/test_timeline_mib_warning_t472.py -q` (고치기 전) | `2 failed, 1 passed` — KeyError `dark_window_seconds` |
| 서버 GREEN | 같은 명령 (고친 뒤) | `3 passed` |
| 화면 RED | `npx vitest run src/components/runbookMibWarning.test.tsx` (고치기 전) | `5 failed, 1 passed` |
| 화면 전체 | `npx vitest run` (ui) | `31 files, 697 passed` — `vitest_all.txt` |
| 타입 | `npx tsc --noEmit -p ui` | 오류 0 |
| 서버 관련 | `uv run pytest -q server/tests -k "timeline or runbook or mib or song_cue or session or concept or cue_sheet"` | `1565 passed, 22 skipped` — `pytest_affected.txt` |
| 린트 | `ruff check`·`ruff format --check` (서버 두 파일) | 통과 |
| 표에 닿는가 | `CueSheetTimeline.tsx:733,777` — `conceptCells(...)` 의 `mib` 를 그 칸에 그린다 | 코드 판독 |

- 서버 시험이 고정하는 것: 어둠 2초 → `live_move: true`, 10초 → `false`, 사전이동 없는 구간에는 두 키가 **없다**.
- 화면 시험이 고정하는 것: 문구 `⚠ 어둠 2.07초 — 켜진 채 이동`(2초면 `2초`), 경고 없으면 `사전이동 있음`/`◐ dark` 그대로.

## 3. 안 잰 것

- **실제 곡에서 경고가 몇 건 뜨는지**: t471 과 같은 한계 — 조립기를 실제 곡에 돌린 산출물이 없다.
- **브라우저 화면**: 렌더 함수·표 연결은 시험과 코드로 확인했지만, 실제 앱 화면을 띄워 보지는 않았다.
- 서버 실출력 사본(`ui/src/components/runbookServerPayload.json`)은 두 키가 없는 옛 사본 그대로다 — 추가만이라 기존 시험은 영향 없음.

## 4. 남은 위험

- 컨셉 기호(컨셉 판정기 G12 기준)와 조립기 경고가 서로 다른 말을 할 수 있다 — 예: `◐ dark ⚠ 어둠 2.07초 — 켜진 채 이동`.
  두 판정은 입력이 다르다(컨셉 파이프라인 행 vs 실제 콘솔로 나갈 큐). 화면은 둘을 나란히 보일 뿐 합치지 않는다.
- `manual_go` 곡에서는 어둠 길이가 곡 시각 기준이다 — 조작자가 GO 를 늦게 누르면 실제 어둠은 더 길다(t471 §5).
