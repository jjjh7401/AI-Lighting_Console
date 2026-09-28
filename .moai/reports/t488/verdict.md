# t488 판정서 — src/DESIGN.md 저장소 커밋

- 카드: t488 (Class A — 파일 1개, 설계 판단 없음)
- 브랜치: `WT-runbook-design-doc` (배차서대로, 이름 변경 없음)
- 워크트리: `.claude/worktrees/t488`
- base: `b29bc49783b0b9ebbc12cfdeee88d494362cd6f2` = 착수 시점 `origin/main` (`git rev-list --left-right --count origin/main...HEAD` → `0 0`)
- 산출 커밋: `437a2269`

## 판정: PASS

## 1. 원본과 사본이 바이트 동일하다

| 대상 | 명령 | 값 |
|---|---|---|
| 원본 (주 체크아웃, 미추적) | `shasum <primary>/src/DESIGN.md` | `7685af2e9d8703c3d4b7a2c30cd1557b4e587887` |
| 워크트리 사본 (복사 직후) | `shasum src/DESIGN.md` | `7685af2e9d8703c3d4b7a2c30cd1557b4e587887` |
| 커밋된 blob | `git show 437a2269:src/DESIGN.md \| shasum` | `7685af2e9d8703c3d4b7a2c30cd1557b4e587887` |
| 배차서가 준 값 | — | `7685af2e9d8703c3d4b7a2c30cd1557b4e587887` |

넷 다 같다. 줄 수 206(`wc -l`), 카드 본문의 「206줄」과 일치.

## 2. 복사 전 확인

- `git ls-tree origin/main -- src/DESIGN.md` → 빈 출력. main 에 같은 경로 파일이 없어 덮어쓰는 것이 아니다.
- `git check-ignore -v src/DESIGN.md` → 종료코드 1(무시 규칙 없음). 강제 추가가 필요 없었다.
- 내용을 끝까지 읽었다. 화면 설계 문서이며 비밀값·자격증명·개인정보 없음.

## 3. 커밋 diff

```
git show --stat --format= 437a2269
 src/DESIGN.md | 206 +++++
 1 file changed, 206 insertions(+)
```

제품 변경은 파일 1개. 이 판정서는 관행(t450~t460, t480, t484 판정서가 main 에 추적 중)에 따라 별도 커밋으로 강제 추가한다.

## 4. 이 커밋이 고치는 것 — 주석의 빈 인용 7곳

`grep -rn 'DESIGN\.md' server ui/src` 결과 7곳이 전부 **주석**이다(런타임에 파일을 읽는 코드 0).

| 위치 | 인용 절 |
|---|---|
| `server/design/cue_sheet_edit.py:62` | §4.5 |
| `server/concept/session_bridge.py:101` | §4.2 |
| `server/concept/session_bridge.py:103` | §4.2 |
| `ui/src/components/RunbookGateBar.tsx:5` | §2 |
| `ui/src/styles.css:3834` | §2 |
| `ui/src/components/runbookM7.test.tsx:169` | §4.4 |
| `ui/src/components/CueSheetTimeline.tsx:230` | §4.4 |

커밋 전에는 이 인용이 가리킬 파일이 저장소에 없었다. 인용 절 넷을 파일 본문과 대조했다:
§2 GATE 4상태(66행) · §4.2 「한눈에」 5단계(112~113행) · §4.4 정확히 14열(134행) · §4.5 Track 4택(158행). 넷 다 인용한 내용과 맞는다.
`runbookM7.test.tsx:169~185` 의 열 이름 14개도 134행과 이름·순서가 전부 같다(대조함).

## 5. 안 잰 것

- **로컬 테스트를 돌리지 않았다.** 근거: 이 파일을 읽는 코드가 0이고(§4), 저장소의 어떤 검사도 `src/*.md` 를 훑지 않는다(`server/tests` 의 `src/` 참조는 `ui/src/App.tsx` 와 Rust 픽스처뿐). 전체 스위트는 CI 가 PR 헤드에서 돌린다 — 그 결과는 PR 에서 읽는다.
- `styles.css:3834` 가 「§2 토큰 그대로」라고 한 **토큰 값 전수 대조는 하지 않았다**(이 카드는 파일을 옮기는 일이지 CSS 를 검수하는 일이 아니다). `session_bridge.py:103` 의 부재 주장(「§4.2 는 배정 규칙을 적지 않았다」)은 4.2 절을 읽어 맞음을 확인했다.
- 주 체크아웃 원본은 **지우지 않았다**(카드 지시: 머지 확인 뒤 리드가 정리).
