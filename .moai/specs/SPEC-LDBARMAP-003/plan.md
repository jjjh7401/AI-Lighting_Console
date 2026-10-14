# SPEC-LDBARMAP-003 — 구현 계획

> plan-phase 산출물이다. 아직 어떤 코드도 바꾸지 않았고, 시험도 돌리지 않았다. 착수 승인(Implementation Kickoff Approval) 전에는 run-phase를 시작하지 않는다.

## 1. 접근

- 서버는 바꾸지 않는다. 요청 프레임과 응답 모양은 `server/web/PROTOCOL.md` 26행에 있고 main에 있다.
- 클라이언트는 세 층이다. ① 요청 빌더와 시험(`protocol`), ② 전송과 응답 상태(`useCopilotSocket`), ③ 컨트롤과 배선(`BarMapEntry`, 입력창).
- D4는 「나」로 정해졌다(SPEC §4). 그래서 파일과 배선 위치가 확정됐다.

## 2. 바뀌는 파일

| 순서 | 파일 | 변경 | 근거 |
|---|---|---|---|
| 1 | `ui/src/protocol.ts` | `buildBarMapAnalyse(firstBeatOffset: number): string` 추가. 1451행의 `buildSongAudioAnalyse` 옆 | 빌더가 곧 클라이언트 등록이다(REQ-LDBARUI-010) |
| 2 | `ui/src/protocol.test.ts` | 프레임 모양 시험 `{v: 1, type: "bar_map_analyse", first_beat_offset: N}`. `reduceServerEvent` 기록 시험 한 줄 | REQ-010, 016 |
| 3 | `ui/src/useCopilotSocket.ts` | `sendBarMapAnalyse(offset)`: `dispatch`로 기록을 남기고 `send`(505행 근처 패턴). 대기와 결과 상태는 응답 처리(330행 근처)에서 `chat_response`·`error`·`busy`를 보고 갱신. 기존 `responding` 값을 쓴다 | REQ-001, 004~009 |
| 4 | `ui/src/components/BarMapEntry.tsx` (신규) | 드롭다운(「선택」 + 0~3), 「마디 지도 분석」 버튼, 「분석 중」 표시, 결과와 거절 사유 표시 | REQ-002~009 |
| 5 | `ui/src/components/BarMapEntry.test.tsx` (신규) | 상태 전이 시험 | AC-001~009, 012, 013, 014 |
| 6 | `ui/src/App.tsx` | 입력창 곡 첨부 상태 줄(`songAudioName` 블록, 1031~1042행)에 `BarMapEntry`를 놓는다. 기존 「분석」 버튼은 그대로 둔다 | REQ-012, 014, 015 |
| 7 | `ui/src/styles.css` | 입력창 규칙(`.composer-status`, `.composer-song-analyse`, 795~810행 근처)에 새 클래스를 더한다. 4279~4400행(「카드 t630」 폭 규칙)은 건드리지 않는다 | REQ-015 |

파일 일곱 개다. Tier M(5~15개) 범위다.

## 3. 단계 (착수 승인 뒤)

1. RED: 1·2·4·5의 시험을 먼저 쓰고, 구현 전에 실패하는 출력을 확보한다.
2. GREEN: 빌더와 등록(1, 2).
3. 전송과 상태(3).
4. 컴포넌트(4).
5. 배선과 스타일(6, 7).
6. 검증(§4)과 시안 대조. 스크린샷은 `.moai/reports/t648/`에 남긴다. 이 경로는 `.gitignore` 대상이라 `git add -f`로 넣는다.
7. 커밋. 모든 커밋 메시지에 카드 id `t648`을 넣는다.

## 4. 검증 명령 (계획만 적었다. 아직 실행하지 않았다)

- `npm --prefix ui run build` — `tsc` 타입 검사와 vite 빌드.
- `npm --prefix ui test -- BarMapEntry protocol` — 이 카드가 바꾼 시험 파일.
- `git diff --name-only origin/main -- ui/src/components/BeatGridTopBar.tsx ui/src/components/BeatGridTopBar.test.tsx` — 출력이 없어야 한다(AC-LDBARUI-015).
- `git diff -U0 origin/main -- ui/src/styles.css` — hunk의 원본 범위가 4279~4400행과 겹치지 않아야 한다(AC-LDBARUI-015).
- `git diff -U0 origin/main -- ui/src/App.tsx` — hunk가 입력창 곡 첨부 상태 줄 블록 안에만 있어야 한다(AC-LDBARUI-015).
- 폭 확인: 1450·1490·1520·1700px에서 곡 첨부 상태 줄이 한 줄로 보이는지 스크린샷으로 확인한다. 1490과 1520은 폭 규칙의 경계다.
- `uv run pytest server/tests/test_prechk_tool.py -q` — 서버 무변경이라 허용 목록 회귀 확인용이다.
- 전체 시험 스위트는 CI에 맡긴다. 레인 규약에 따라 로컬에서는 이 카드가 영향을 주는 시험만 돌린다.

## 5. 위험과 대응

- 대기 표시 오류(응답 식별): SPEC §4와 Gaps 1번. 결과 표시는 라벨로 판별하므로 틀리지 않는다.
- 입력창 줄 넘침: 새 컨트롤이 곡 첨부 상태 줄에서 넘치면 입력창 배치가 바뀐다. 상단 바와 무대 규칙은 건드리지 않는다. 넘침이 확인되면 구현을 멈추고 리드에게 알린다.
- 자리 변경: 감독이 자리를 바꾸면 6단계 배선과 AC-LDBARUI-014·015만 바뀐다.
