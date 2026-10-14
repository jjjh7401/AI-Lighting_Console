# SPEC-LDBARMAP-003 — 구현 계획

> plan-phase 산출물이다(v0.1.3). 아직 어떤 코드도 바꾸지 않았고, 시험도 돌리지 않았다. 착수 승인(Implementation Kickoff Approval) 전에는 run-phase를 시작하지 않는다.

## 1. 접근

- 서버는 바꾸지 않는다. 요청 프레임과 응답 모양은 `server/web/PROTOCOL.md` 26행에 있고 main에 있다.
- 상태 로직은 전부 순수 리듀서(`barMapEntryState.ts`)에 둔다. 소켓 훅과 컴포넌트는 그 리듀서를 호출하거나 props를 받을 뿐이다. 그래서 DOM 없이 시험할 수 있다.
- 입력창은 막지 않는다. 막는 것은 「분석」 버튼(새 것과 기존 것)뿐이다.

## 2. 바뀌는 파일

| 순서 | 파일 | 변경 | 근거 |
|---|---|---|---|
| 1 | `ui/src/protocol.ts` | `buildBarMapAnalyse(firstBeatOffset: number): string`(1451행 근처 `buildSongAudioAnalyse` 옆). 박자표 사본 `BAR_MAP_TIME_SIGNATURE`, 파생 상수 `BAR_MAP_BEATS_PER_BAR`와 `BAR_MAP_METER_LABEL`. 사본 주석에 `server/audio/bar_map_entry.py` 52행을 적는다 | REQ-LDBARUI-001, 010, 011 |
| 2 | `ui/src/protocol.test.ts` | 빌더 프레임 시험. `reduceServerEvent` 기록 시험 한 줄 | REQ-LDBARUI-010, 015 |
| 3 | `ui/src/components/barMapEntryState.ts` (신규) | 순수 리듀서 `barMapEntryReducer`, 이벤트 타입, 안내 문구 상수, `isOffMeter` | REQ-LDBARUI-003~009 |
| 4 | `ui/src/components/barMapEntryState.test.ts` (신규) | 리듀서 전이 시험, `isOffMeter` 시험 | AC-LDBARUI-003~009 |
| 5 | `ui/src/components/BarMapEntry.tsx` (신규) | props만 받는 표시 컴포넌트: 드롭다운, 분석 버튼, 「분석 중」과 「취소」, 안내 줄, 사실 문구. 숫자 4는 상수에서 가져온다 | REQ-LDBARUI-002, 003, 011~013 |
| 6 | `ui/src/components/BarMapEntry.test.tsx` (신규) | `renderToStaticMarkup` 정적 HTML 시험, `styles.css` 텍스트 검사 | AC-LDBARUI-001, 002, 003, 004, 012, 013 |
| 7 | `ui/src/useCopilotSocket.ts` | `sendBarMapAnalyse(offset, songName): boolean`: 연결이 열렸는지 본 뒤 화면 기록을 남기고 보낸다. 열리지 않았으면 `false`. 훅 옵션 `onServerEvent`와 `onSocketClosed`로 수신 프레임과 끊김을 알린다 | REQ-LDBARUI-001, 004, 005 |
| 8 | `ui/src/App.tsx` | (가) 임포트 블록에 `BarMapEntry` 추가. (나) 훅 호출에 옵션 두 개를 넘기고, 그 아래에 `useReducer(barMapEntryReducer, ...)` 상태 선언. (다) 곡 첨부 상태 블록에 `BarMapEntry`를 놓고, 기존 「분석」 버튼의 `disabled`에 대기 상태를 더한다 | REQ-LDBARUI-004, 012, 014 |
| 9 | `ui/src/styles.css` | 입력창 규칙(795~814행 부근)에 `.composer-bar-map` 규칙만 더한다. `beat-grid-` 규칙과 「카드 t630」 블록은 건드리지 않는다 | REQ-LDBARUI-013, 014 |

파일 아홉 개(새 파일 네 개 포함)다. Tier M(5~15개) 범위다.

## 3. 단계 (착수 승인 뒤)

1. RED: 1, 3, 4, 6의 시험을 먼저 쓰고, 구현 전에 실패하는 출력을 확보한다.
2. GREEN: 상수와 빌더(1), 리듀서(3).
3. 컴포넌트(5)와 그 정적 HTML 시험(6).
4. 소켓 훅 옵션과 전송 함수(7).
5. 배선과 스타일(8, 9).
6. 검증(§4)과 시안 대조. 커밋은 단계마다 하고, 모든 커밋 메시지에 카드 id `t648`을 넣는다.

## 4. 검증 명령 (계획만 적었다. 아직 실행하지 않았다)

자동 검사(작업 트리와 기준점 B = `git merge-base origin/main HEAD`):
- `npm --prefix ui run build` — `tsc` 타입 검사와 vite 빌드.
- `npm --prefix ui test -- barMapEntryState BarMapEntry protocol` — 이 카드가 바꾼 시험 파일.
- `npm --prefix ui test -- BeatGridTopBar` — 폭 규칙의 기존 시험이 그대로 통과해야 한다(AC-LDBARUI-014).
- AC-LDBARUI-010, 011의 `grep` 검사(작업 트리에서).
- AC-LDBARUI-014의 `git diff` 검사 네 개(모든 변경을 커밋한 뒤에).
- `uv run pytest server/tests/test_prechk_tool.py -q` — 서버 무변경이므로 허용 목록 회귀 확인용이다.

수동 확인(시험이 아님, 결과를 `.moai/reports/t648/`에 남긴다. 이 경로는 `.gitignore`의 재포함 규칙으로 추적되므로 `git add -f`가 필요 없다):
- 브라우저에서 분석 버튼 클릭 한 번이 프레임 한 개를 보내는지(개발자 도구의 WebSocket 기록).
- 「취소」 뒤 늦은 결과가 안내 줄에 나타나는지.
- 1450, 1490, 1520, 1700px 폭에서 긴 파일명과 긴 거절 사유의 넘침 여부와 스크린샷.

전체 시험 스위트는 CI에 맡긴다. 레인 규약에 따라 로컬에서는 이 카드가 영향을 주는 시험만 돌린다.

## 5. 위험과 대응

- `busy` 귀속(SPEC §4): 분석 중 채팅의 `busy`가 와도 대기는 유지된다. 거절된 요청은 「취소」로 푼다.
- 「취소」 뒤 서버 분석이 계속될 수 있다(SPEC Gaps 1번). 결과는 라벨로 계속 보인다.
- 늦은 결과의 오프셋(SPEC Gaps 2번): 결과 줄에 오프셋을 적지 않는다.
- 입력창 줄 넘침: `composer-bar-map`에 줄바꿈 규칙을 두고, 수동 확인으로 본다. 넘침이 보이면 구현을 멈추고 리드에게 알린다.
- 자리 변경: 감독이 자리를 바꾸면 8단계 배선과 AC-LDBARUI-014만 바뀐다.
