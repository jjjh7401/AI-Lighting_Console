# SPEC-LDBARMAP-003 — 구현 계획

> plan-phase 산출물이다(v0.1.2). 아직 어떤 코드도 바꾸지 않았고, 시험도 돌리지 않았다. 착수 승인(Implementation Kickoff Approval) 전에는 run-phase를 시작하지 않는다.

## 1. 접근

- 서버는 바꾸지 않는다. 요청 프레임과 응답 모양은 `server/web/PROTOCOL.md` 26행에 있고 main에 있다.
- 클라이언트는 세 층이다. ① 요청 빌더와 상수 사본(`protocol`), ② 전송과 대기 상태(`useCopilotSocket`), ③ 컨트롤과 배선(`BarMapEntry`, 입력창).
- D4는 「나」다(SPEC §4). 입력창은 막지 않는다. 막는 것은 「분석」 버튼(새 것과 기존 것)뿐이다.

## 2. 바뀌는 파일

| 순서 | 파일 | 변경 | 근거 |
|---|---|---|---|
| 1 | `ui/src/protocol.ts` | `buildBarMapAnalyse(firstBeatOffset: number): string`(1451행 근처 `buildSongAudioAnalyse` 옆). 상수 `BAR_MAP_BEATS_PER_BAR`(사본, 출처 주석 포함) | REQ-LDBARUI-001, 009, 010 |
| 2 | `ui/src/protocol.test.ts` | 빌더의 프레임 모양 시험. `reduceServerEvent` 기록 시험 한 줄 | REQ-LDBARUI-009, 015 |
| 3 | `ui/src/useCopilotSocket.ts` | `sendBarMapAnalyse(offset)`: 연결 확인 → 기록 → 전송 → 대기 시작(`send`는 열리지 않은 소켓에서 조용히 버리므로, 보내기 전에 `readyState`를 본다). 응답 처리(330행 근처)에서 라벨·오류를 보고 대기를 끝낸다. `busy`는 안내만 넘긴다. 끊김 처리(340~348행 근처)에서 대기를 끝내고 안내를 남긴다 | REQ-LDBARUI-001, 004~008 |
| 4 | `ui/src/components/BarMapEntry.tsx` (신규) | 드롭다운(「선택」 + 0~3), 「마디 지도 분석」 버튼, 「분석 중」과 「취소」, 결과·거절·오류·busy 안내 줄, 4/4 사실 문구(상수에서 만든다), 파일명 줄 | REQ-LDBARUI-002~008, 010, 013 |
| 5 | `ui/src/components/BarMapEntry.test.tsx` (신규) | 컴포넌트 상태 시험 | AC-LDBARUI-001~008 |
| 6 | `ui/src/App.tsx` | (가) 임포트 블록(23~47행 부근)에 `BarMapEntry` 추가. (나) 훅 구조분해(404~429행 부근, `sendSongAudioAnalyse` 옆)에 새 멤버 추가. (다) 곡 첨부 상태 블록(1031~1042행)에 컨트롤을 놓고, 기존 「분석」 버튼에 대기 중 비활성을 더한다 | REQ-LDBARUI-004, 011, 013, 014 |
| 7 | `ui/src/App.test.tsx` | 배선 시험: 두 버튼 분리, 보낸 프레임 집합, 파일명 줄과 넘침, 대기 중 버튼 비활성 | AC-LDBARUI-004, 011~013 |
| 8 | `ui/src/styles.css` | 입력창 규칙(795~814행 부근)에 새 클래스를 더한다. 4386~4401행(폭 규칙)과 `beat-grid-` 규칙은 건드리지 않는다 | REQ-LDBARUI-013, 014 |

파일 여덟 개다. Tier M(5~15개) 범위다.

## 3. 단계 (착수 승인 뒤)

1. RED: 1·2·4·5·7의 시험을 먼저 쓰고, 구현 전에 실패하는 출력을 확보한다.
2. GREEN: 빌더와 상수 사본(1, 2).
3. 전송과 대기 상태(3).
4. 컴포넌트(4).
5. 배선과 스타일(6, 8).
6. 검증(§4)과 시안 대조. 스크린샷은 `.moai/reports/t648/`에 남긴다. 이 경로는 `.gitignore`의 `!.moai/reports/t[0-9]*/` 규칙으로 추적되므로 `git add -f`가 필요 없다(확인 2026-10-14).
7. 커밋. 모든 커밋 메시지에 카드 id `t648`을 넣는다.

## 4. 검증 명령 (계획만 적었다. 아직 실행하지 않았다)

- 기준점 B = `git merge-base origin/main HEAD`. 구현을 시작할 때 한 번 고정한다.
- `npm --prefix ui run build` — `tsc` 타입 검사와 vite 빌드.
- `npm --prefix ui test -- BarMapEntry App protocol` — 이 카드가 바꾼 시험 파일.
- `npm --prefix ui test -- BeatGridTopBar` — 폭 규칙의 기존 시험이 그대로 통과해야 한다(AC-LDBARUI-014).
- `git diff --name-only B -- ui/src/components/BeatGridTopBar.tsx ui/src/components/BeatGridTopBar.test.tsx ui/src/components/BeatGridStage.tsx ui/src/components/beatGridStageModel.ts` — 출력이 없어야 한다.
- `git diff -U0 B -- ui/src/styles.css` — 원본 쪽 hunk가 795~815행 안에 있어야 한다.
- `git diff -U0 B -- ui/src/App.tsx` — 원본 쪽 hunk가 23~47행, 404~429행, 1031~1042행 안에만 있어야 한다.
- 폭 확인: 1450·1490·1520·1700px에서 곡 첨부 상태 블록이 블록 밖으로 넘치지 않는지 스크린샷으로 본다. 1490과 1520은 폭 규칙의 경계다.
- `uv run pytest server/tests/test_prechk_tool.py -q` — 서버 무변경이라 허용 목록 회귀 확인용이다.
- 전체 시험 스위트는 CI에 맡긴다. 레인 규약에 따라 로컬에서는 이 카드가 영향을 주는 시험만 돌린다.

## 5. 위험과 대응

- `busy` 귀속(SPEC §4): 분석 중 채팅의 `busy`가 와도 대기는 유지된다. 거절된 요청은 「취소」로 푼다. 리드가 「busy로 바로 풀기」를 고르면 4단계의 대기 규칙만 바뀐다.
- 「취소」 뒤 서버 분석이 계속될 수 있다(SPEC Gaps 1번). 결과는 라벨로 계속 보인다.
- 입력창 줄 넘침: 새 컨트롤이 곡 첨부 상태 블록에서 넘치면 입력창 배치가 흐트러진다. 상단 바와 무대 규칙은 건드리지 않는다. 넘침이 확인되면 구현을 멈추고 리드에게 알린다.
- 자리 변경: 감독이 자리를 바꾸면 6단계 배선과 AC-LDBARUI-011~014만 바뀐다.
