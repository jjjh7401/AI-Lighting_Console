# SPEC-LDBARMAP-003 — 구현 계획

> 이 문서는 plan-phase 산출물이다. 아직 어떤 코드도 바꾸지 않았고, 어떤 시험도 돌리지 않았다. 착수 승인(Implementation Kickoff Approval) 전에는 run-phase를 시작하지 않는다.

## 1. 접근

- 서버는 바꾸지 않는다. 요청 프레임 `bar_map_analyse`와 응답 모양은 이미 main에 있다(PR #693).
- 클라이언트는 세 층으로 나눈다. ① 요청 빌더와 등록(`protocol.ts`), ② 전송 노출(`useCopilotSocket.ts`), ③ 화면 컴포넌트(`BarMapEntry.tsx`)와 배선(`App.tsx`).
- ①과 ②, ③의 본체는 화면 자리와 무관하다. D4(화면 자리)가 정해지면 바뀌는 것은 배선 위치뿐이다. 그래서 D4 결정을 기다리는 동안에도 ①부터 ⑤까지는 진행할 수 있다.

## 2. 바뀌는 파일 (예상이며 확정이 아니다)

| 순서 | 파일 | 변경 | D4 의존 |
|---|---|---|---|
| 1 | `ui/src/protocol.ts` | `buildBarMapAnalyse(firstBeatOffset: number): string` 추가. `buildSongAudioAnalyse`(1451행)와 같은 모양. 클라이언트 등록 | 없음 |
| 2 | `ui/src/protocol.test.ts` | 프레임 모양 시험(`{v: 1, type: "bar_map_analyse", first_beat_offset: N}`) | 없음 |
| 3 | `ui/src/useCopilotSocket.ts` | `sendBarMapAnalyse(offset)` 노출. `dispatch`로 화면 기록을 남기고 `send` | 없음 |
| 4 | `ui/src/components/BarMapEntry.tsx` (신규) | 입력 칸, 분석 버튼, 대기 표시, 결과 표시, 파일명 표시 | 없음 |
| 5 | `ui/src/components/BarMapEntry.test.tsx` (신규) | 상태 전이 시험(대기, 성공, 거절, 첨부 없음, 사용 중) | 없음 |
| 6 | `ui/src/App.tsx` | 컴포넌트를 화면에 배선하고 상태를 잇는다 | 있음 |
| 7 | D4 자리 파일 | (가) `BeatGridTopBar.tsx` / (나) 곡 첨부 위젯(위치 미확인, run-phase에서 찾는다) / (다) 새 패널 | 있음 |

파일 수는 대략 일곱 개로 본다. Tier M(5~15개) 범위다. 이 수치는 추정이다.

## 3. 단계 (착수 승인 뒤)

1. 시험 먼저(RED). `protocol.test.ts`와 `BarMapEntry.test.tsx`에 수락 기준의 시험을 쓰고, 구현 전에 실패하는 출력을 남긴다.
2. 요청 빌더와 등록(GREEN).
3. 전송 노출.
4. 컴포넌트와 상태 전이.
5. D4 자리에 배선. 이 단계는 감독 결정이 있어야 한다.
6. 검증(§4)과 시안 대조.
7. 커밋. 모든 커밋 메시지에 카드 id `t648`을 넣고, 증거는 `.moai/reports/t648/`에 둔다(이 경로는 `.gitignore` 대상이라 `git add -f`로 넣는다).

## 4. 검증 명령 (계획만 적었고 아직 실행하지 않았다)

- `npm --prefix ui run build` — `tsc` 타입 검사와 vite 빌드를 함께 본다.
- `npm --prefix ui test -- BarMapEntry protocol` — 이 카드가 바꾼 시험 파일만 먼저 돌린다.
- `uv run pytest server/tests/test_prechk_tool.py -q` — 서버 무변경이므로 허용 목록 회귀 확인용이다.
- 시안 대조 — 화면 자리가 정해진 뒤 스크린샷을 `.moai/reports/t648/`에 남긴다.
- 전체 시험 스위트는 CI에 맡긴다. 레인 규약에 따라 로컬에서는 이 카드가 영향을 주는 시험만 돌린다.

## 5. 위험과 대응

- 응답 식별: 요청에 번호가 없다. 고정 `summary` 라벨로 가리고, 대기 중에는 다른 전송을 막는다(SPEC §4).
- D4 지연: 감독 결정이 늦으면 5~6단계가 멈춘다. 1~4단계는 그 전에 끝낼 수 있다.
- 파일명 표시: 첨부된 곡과 타임라인의 곡이 같은지는 확인하지 않는다(SPEC-LDBARMAP-002 E3). 화면은 파일명을 보여 줄 뿐 막지 않는다.
