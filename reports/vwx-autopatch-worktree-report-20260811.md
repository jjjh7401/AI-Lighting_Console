# AI Lighting Console — Vectorworks 자동 패치 구현 현황

- 기준일: 2026-08-11
- 범위: 이 워크트리의 소스 트리, Vectorworks 자동 패치 경로, UI/콘솔 통합, 패키징 현황. `node_modules`, 빌드 산출물, JSONL 감사 로그는 제외했다.
- 결론: 파일 해석·콘솔 대조·충돌/타입 해결 대화·검토 가능한 Lua 계획 생성·사람 실행 후 재검증까지 구현됐다. 서버가 grandMA3의 Patch Editor에 `AddFixtures`를 직접 실행하는 완전 자동 쓰기는 구현하지 않았고 의도적으로 금지한다.

## 구현됨

| 영역 | 구현 상태 | 주요 위치 |
|---|---|---|
| 입력 | `.csv`, `.txt`, `.xlsx`, `.mvr` 업로드; UI에서 8 MiB·빈 파일·확장자 제한 | `ui/src/App.tsx`, `server/web/messages.py` |
| Vectorworks/MVR 판독 | 컬럼 별칭, 주소 정규화, MVR ZIP/XML/GDTF/DMX 모드 판독 | `server/vwx/reader.py`, `columns.py`, `address.py`, `mvr.py` |
| 설계 리그/대조 | 도면 리그 모델, MA3 읽기 전용 인벤토리와의 대조, 이미 패치됨/누락/주소 충돌 분류 | `server/vwx/rig.py`, `diff.py`, `server/orchestrator/tools.py` |
| 주소/타입 계획 | DMX 폭·유니버스 경계·주소 겹침 검사, 콘솔 라이브러리 대조와 타입 별칭 확인 | `server/vwx/addressfit.py`, `typemap.py`, `librarywatch.py`, `patchplan.py` |
| 대화형 보완 | 해결 불가능한 Fixture Type, 주소, FID만 질문 카드로 보류; 답으로 이어서 재계획 | `server/web/question.py`, `session.py`, `ui/src/components/QuestionCard.tsx` |
| 실행 인계 | Lua `AddFixtures` 초안과 실행·읽기 재검증 인계를 생성. 서버는 직접 실행하지 않음 | `server/vwx/luagen.py`, `apply.py`, `stagedpatch.py`, `server/orchestrator/tools.py` |
| 안전/통합 | OSC responder, 단일 safety gate, 승인/라이브 잠금/백업/감사 로그, WebSocket UI | `console/lua/`, `server/bridge/`, `server/safety/`, `server/web/`, `ui/` |
| 배포 기반 | macOS arm64 PyInstaller 패키지와 Tauri sidecar shell | `packaging/`, `src-tauri/` |

## 실제 흐름

1. 사용자가 VWX export 또는 MVR을 올린다.
2. 서버가 설계 리그를 만들고 현재 MA3 인벤토리를 읽어 차이를 계산한다.
3. 일치 항목은 재생성하지 않는다. 안전하게 확정할 수 없는 항목만 질문 카드로 보낸다.
4. 사용자의 선택을 반영해 주소·타입·FID를 다시 계획한다.
5. 검토 가능한 Lua와 콘솔에서 실행할 절차를 만든다.
6. 사용자가 MA3에서 실행한 뒤 서버가 인벤토리를 다시 읽어 결과를 확인한다.

## 구현하지 않음 / 남은 제한

| 항목 | 상태 | 이유 또는 필요한 사용자 행동 |
|---|---|---|
| 서버의 `AddFixtures` 직접 실행 | 미구현·의도적 금지 | 실 onPC에서 여러 실행 경로가 생성 0대를 보였다. 잘못된 주소·타입을 쇼파일에 쓰지 않도록 사람이 최종 실행한다. |
| MA3 Patch Editor 자동 진입/조작 | 미구현 | 안전한 OSC/GUI 제어 경로가 검증되지 않았다. Patch Editor에 들어가는 것은 사용자 행동이다. |
| 누락 Fixture Type의 추측 매핑 | 미구현·금지 | 오매핑은 실제 조명 동작을 바꿀 수 있다. 콘솔에서 타입 선택 또는 MVR/GDTF 제공이 필요하다. |
| GDTF를 콘솔 라이브러리에 자동 설치 | 미구현 | 사용자가 `.gdtf`를 MA3의 fixturetypes 경로에 배치하고 Library에서 확인해야 한다. |
| 실제 생성까지 끝나는 종단 라이브 검증 | 미완료 | 2026-08-11 onPC 시험은 40대 인벤토리 읽기와 수동 해결 질문까지 확인했다. 누락 타입 때문에 생성 명령은 실행하지 않았다. |
| 교차 플랫폼 서명·공증·자동 업데이트 | 미완료 | macOS arm64용 패키징 기반만 있음. Developer-ID 인증서, Windows 빌드 호스트, Stage-2 auto-update가 필요하다. |

## 라이브 관찰 기록 (2026-08-11)

- grandMA3 onPC 2.4.2.2 연결과 responder 포트 정렬 후 UI는 콘솔 온라인/실행 가능, 인벤토리 40대를 표시했다.
- `demoshow_grandma3.mvr`을 UI로 올렸다.
- 콘솔에 없는 `MAC Encore Performance CLD`를 발견해 자동 생성 대신 선택지를 제시했다.
- 해당 타입을 건너뛰자 `Rush Par 2 RGBW Zoom`에 대해 다음 질문을 이어서 제시했다.
- 생성 명령은 실행하지 않았고 인벤토리는 40대로 유지됐다.

## 현재 검증 (2026-08-11)

| 명령 | 결과 | 증명 범위 |
|---|---:|---|
| `uv run pytest server/tests/test_autopatch_tool.py server/tests/test_vwx_tool.py server/tests/test_web_messages.py server/tests/test_web_app.py -q` | 367 passed, warning 1 | 업로드·파싱·계획·메시지·웹 계약 |
| `uv run pytest server/tests/test_vwx_mvr.py server/tests/test_web_question_channel.py server/tests/test_web_session.py server/tests/test_autopatch_tool.py::TestUploadedVectorworksAutopatch -q` | 70 passed | MVR 판독, 질문 채널, 세션 업로드 자동 패치 |
| `npm test -- --run src/protocol.test.ts src/useCopilotSocket.test.ts src/App.test.tsx` | 114 passed | WebSocket 프로토콜, 상태 reducer, 업로드 UI |
| `npm run build` | success | TypeScript 검사와 Vite production build |

이 테스트들은 서버·브라우저 계약을 검증한다. MA3에서 실제 픽스처가 생성되는 것은 검증하지 않는다.
