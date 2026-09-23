# t435 — SPEC-LDDESIGN-001 M7 1차 판정 (lane-3)

- 브랜치: `WT-runbook-ui-first` · 기준 `origin/main@7a5432a7` (`git rev-list --count --left-right origin/main...HEAD` → `0 0`, 착수 시)
- 구현 커밋: `00296d4a`
- 작성: 2026-09-23

## 1. 범위 판정 — 데이터 없이 되는 것

리드 배차의 후보 REQ-099·082/096·084/085를 "M2/M3(이후) 데이터 없이 성립하는가"로 갈랐다.

| REQ | 판정 | 근거 (잰 것 / 읽은 것 구분) |
|---|---|---|
| REQ-099 폰트·tabular-nums | **이번에 구현** | [잰 것] `ui/src/styles.css`에서 런북 선택자 `.cst-sheet`·`.cst-tick span`·`.song-timeline-section`의 `tabular-nums`는 0건, 모노 스택은 `Consolas, monospace` 단독(RED 테스트 4건 실패로 확인). |
| REQ-085 스크롤 연동 | **변경 없음 — 이미 구현** | [읽은 것] `ui/src/components/CueSheetTimeline.tsx:307-376`에 가로 레일↔세로 시트 연동이 있다(t280/t287/t288). 되먹임은 cause 플래그(`program`/`user`, `shouldAdoptScroll`)로 막는다. DESIGN §4.7의 lock+80ms와 방식은 다르지만, REQ 원문은 방식을 정하지 않는다. 브라우저에서 직접 굴려 보지는 않았다(§4 참조). 두 번째 절(한글 주 라벨)은 열 헤더 문제라 REQ-082와 함께 처리해야 한다. |
| REQ-084 상태줄 GATE | **보류 — 데이터 의존** | [읽은 것] GATE의 입력은 §3.6~3.11 게이트 산출물이고, 이는 M3~M5가 만든다. 지금 있는 `SongTimelineView.lint`로 채우면 의미를 지어내는 셈이다. |
| REQ-082 CUE SHEET 14열 | **보류 — 데이터 의존** | [읽은 것] 새 5열 중 회차(M4)·MIB 3상태(M5)·Track 예외(M5)·근거 등급은 데이터가 없다. 지금 페이로드에 있는 건 `mib: boolean`뿐이다(`ui/src/protocol.ts:325`). |
| REQ-096 Trans 접근 | **blocker → 리드** | [읽은 것] 열을 지운 뒤 Trans에 닿는 길은 대화창 자연어 경로 하나다(`server/design/cue_sheet_edit.py:45,230`). 생성기에도 둘지는 결정이 필요하다. REQ-082가 보류라 당장 막히는 일은 없다. |

## 2. 변경

`ui/src/styles.css` — 런북 모드 선택자만 고쳤다. 메인 화면 선택자는 건드리지 않았다.

- `.cst-sheet` (CUE SHEET 수치 열): `font-variant-numeric: tabular-nums` 추가
- `.song-timeline-section` (PLAN CUE 카드): `font-variant-numeric: tabular-nums` 추가
- `.cst-tick span` (타임라인 시간 눈금): 스택을 `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`로 바꾸고 `tabular-nums` 추가
- `.cst-sheet td.m`, `.cst-sheet td.fx`: 스택을 `Consolas, monospace`에서 같은 시스템 모노 스택으로 교체

`ui/src/styles.test.ts` — REQ-099 가드 5건 추가(세 자리의 tabular-nums, 웹폰트 참조 0건, 모노 칸 `ui-monospace`).

## 3. 증거

| 주장 | 명령 | 관측 |
|---|---|---|
| RED | `npx vitest run src/styles.test.ts` (수정 전) | `Tests 4 failed \| 22 passed (26)` |
| GREEN | `npx vitest run` (ui 전체) | `Test Files 25 passed (25)` · `Tests 583 passed (583)` |
| 타입 | `npx tsc --noEmit` | exit 0 |
| 빌드 | `npx vite build --outDir <scratchpad>/t435-dist` | `✓ built in 332ms`, 산출물 4파일(index.html·favicon.svg·css·js) |
| AC-051 웹폰트 부재 | 산출물에서 `*.woff*`/`*.ttf`/`*.otf` 검색 · `fonts.googleapis\|fonts.gstatic\|@font-face` grep | 0 · 0 |
| 양성 대조 | 같은 산출물 css에서 `tabular-nums` 개수 | 9 (기존 6 + 신규 3) — grep이 실제로 잡는다는 확인 |
| 가드의 판별력 | `.cst-tick span`의 `tabular-nums` 한 줄을 지우고 재실행 → `git checkout`으로 복구 | `1 failed \| 25 passed` → 복구 후 `26 passed` |

## 4. 안 잰 것 (Gaps)

- **실제 화면을 눈으로 보지 않았다.** 숫자 정렬이 실제로 맞는지 스크린샷으로 확인한 적이 없다. CSS 선언이 있는 것까지만 확인했다.
- **REQ-085는 코드를 읽기만 했다.** 기존 테스트(`CueSheetTimeline.test.tsx`)는 `shouldAdoptScroll` 순수 함수만 검사하고 DOM 스크롤은 검사하지 않는다. AC-020 1절의 브라우저 실측은 하지 않았다.
- **본문 폰트 스택은 그대로 뒀다.** 전역 `body`는 `"Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`다. Pretendard는 싣지 않으므로 웹폰트 의존은 아니지만, 시스템 기본 글꼴이 아니다. `body`는 메인 화면과 같이 쓰는 선택자라, 불가침 지시에 따라 건드리지 않았다.
- `.song-timeline-section`에 건 `tabular-nums`는 카드 안 전체에 상속된다. 숫자 모양만 바뀌고 글자에는 영향이 없다.

## 5. 남은 위험

- `Consolas`가 없는 macOS에서 모노 칸이 `ui-monospace`(SF Mono)로 바뀌므로 글자 폭이 조금 달라진다. `.cst-sheet`의 `min-width: 1100px`는 그대로라 레이아웃이 깨질 가능성은 낮지만, 눈으로 확인하지는 않았다.
