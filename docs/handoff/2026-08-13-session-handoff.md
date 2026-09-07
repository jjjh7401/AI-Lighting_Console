# 세션 핸드오프 — 2026-08-13 (Copilot 대화·의도·레이아웃 개선)

다음 세션이 이어받을 수 있게 이번 작업을 정리한다. 대상은 grandMA3 Copilot
(`server/` FastAPI + `ui/` React, 활성 provider = Claude Code / model = opus).

## 1. 이번 세션이 해결한 것 (모두 커밋됨, 서버 테스트 green)

1. **대화 맥락 유지 (근본 원인 수정)** — `Orchestrator.handle_instruction`가 매 턴
   대화를 새로 만들어 모델이 이전 턴을 전혀 못 봤다. `ChatSession._history`(롤링,
   최근 16 메시지)를 만들어 `handle_instruction(text, history=…, session_context=…)`로
   전달. 이제 후속 질문이 맥락 위에서 답한다. (`server/web/session.py`,
   `server/orchestrator/runner.py`)

2. **모델별 특성 활용 (프로파일)** — `ClaudeCodeAdapter`에 `_ModelProfile` 도입.
   opus=추론 우선(`reasoning` 스크래치패드 필수·맨앞), sonnet=균형, fable=속도
   우선(`reasoning` 선택). 구조화 출력(`--json-schema`)이 죽이던 사고 과정을
   `reasoning` 선행 필드로 복원 → 의도 파악 개선. (`server/llm/claude_code_adapter.py`)

3. **한 번에 하나씩 ask_user 카드** — 질문 카드 파이프라인(QuestionChannel→
   question_request→QuestionCard→answer)은 이미 있었다. 직접 핸들러가 산문 대신
   `_ask_one()`으로 카드를 한 개씩 띄우도록 전환. 모델 계약(도구 설명 + 어댑터
   지시문)도 "질문은 한 번에 하나씩 ask_user, 채팅 본문에 여러 질문/표 금지"로 강화.

4. **레이아웃 직접 실행 핸들러** (모델 경로의 hang/"No such tool"/산문 벽 회피):
   - `_all_fixtures_elevation` (전체 5m 높이, FID 캐시 재사용)
   - `_repeating_type_columns_layout` (MMX/MMX/350 반복 열; 완전 열 전부 배치 + 잔여 보고)
   - `_typed_two_row_layout`, `_vocabulary_layout`(그리드/일렬/원형)
   - **`_multi_ring_circle_layout`** (이번 핵심): `parse_ring_layout`로 다중 원 파싱 →
     반지름·번갈아 순서를 카드로 한 개씩 수집 → 실제 FID 읽어 링별 `arrange_fixtures
     preset=circle` 실행. 라우팅 순서는 `run_instruction` 참고.
   - 그리드는 `row_spacing`/`column_spacing` 분리 지원(`server/spatial/presets.py`,
     `arrange_fixtures` 스키마).

5. **오케스트레이터 "No such tool" 환각 교정** — 도구 0개 턴에서 본문이 "도구 없음"을
   주장하면(마커 감지) 1회 교정 메시지를 넣고 재시도. 무한 루프 방지(cap=1).
   (`server/orchestrator/runner.py` `_claims_tool_unavailable`, `_TOOLS_ARE_AVAILABLE`)

6. **반사적 캔드 클래리파이어 제거** — 키워드 하나로 정해진 한 줄을 뱉던
   `_layout_vocabulary_clarification` / `_grid_layout_clarification` 삭제. 어휘는
   `layout_terms_guidance()`로 **모델 추론 보조**(세션 노트)로 전환.

7. **선행 버그 수정** — `server/llm/config.py`의 `ClaudeCodeSettings` **중복 정의(F811)**
   제거.

## 2. 라이브 검증 (실제 콘솔 연결 상태, 이번 세션 확인)

요청: "장비를 여러 겹의 원형으로 배치… 안쪽 MMX 8, 2번째 RLB350 12, 3번째 남은 것 번갈아".
결과 (WS로 카드·승인 자동 응답):
- 카드 2개 순차: ①각 원 지름 → `4·6·8m` ②마지막 원 번갈아 순서 → `FID 오름차순`
- 링별 승인 3회(24·36·60 items) → 승인
- 최종: 1원(r2m)8대 / 2원(r3m)12대 / 3원(r4m)20대, **executed_ok 120건, 실패 0**
- 3번째 원 순서 `9,32,10,33,…,16,39,17,18,19,40` (교대 후 잔여 연속) 정확.

## 3. 운영 주의 — 포트 8765 단일 서버 규칙

`python -m server.web`는 **8765 자동 폴백 없음**. 인스턴스를 2개 이상 띄우면 나중에
뜬 게 바인딩 실패로 즉시 종료된다("요청 넣으면 서버가 꺼진다"의 정체 = 포트 충돌,
서버 크래시 아님). 정식 앱은 hub 프로세스 **`grandma3-web-stable`**
(`.venv/bin/python -m server.web`, persistent, restart=no). 테스트용 별도 서버를
띄우지 말고 이 하나에 붙여 검증할 것.

## 4. 남은 이슈 / 안 한 것 (이번 작업과 무관, 커밋 전부터 존재)

- 서버 테스트 5건 실패(HEAD에서도 동일 — pre-existing): `test_paperwork_patch_sheet`
  x2(채널폭 상계 렌더링), `test_prechk_tool::test_the_axis_adds_no_web_surface`(웹
  라우트 열거 가드), `test_songcue_bundle::test_tools_hunks…`(tools.py diff 형태 가드),
  `test_tools.py::TestRegistry`(등록 도구 집합에 `build_handover_pack` 중복 + vwx 항목).
  → 이번 대화·레이아웃 작업과 무관. 다음 세션 별도 처리 권장(특히 tool-registry
  중복은 config F811처럼 실제 데이터 버그일 수 있음).
- UI: `ui/src/components/PaperworkPanel.test.tsx` 11건 실패(pre-existing, 페이퍼워크
  전용). 연결/소켓 관련 테스트(App/useCopilotSocket)는 통과, `vite build` 성공.
- 모델 경로 신뢰성: opus가 교정 후에도 드물게 도구 미사용/산문으로 빠질 여지 존재.
  근본 개선(배치·이동 요청 시 첫 tool_call 강제 등)은 미착수.
- 복합 요청(배치+높이 동시)은 여전히 한 턴에 하나만 직접 처리.

## 5. 이번 커밋에 넣지 않은 워킹트리 변경 (로컬 유지)

런타임 로그/인프라·미검증 항목은 커밋에서 제외(로컬 워킹트리에 남아 다음 세션에서
그대로 보임): `.moai/*.jsonl`, `.moai/archive/`, `.moai/config/sections/`, `.claude/*`,
`ui/*`(연결 수정 arc — 자체 테스트/빌드는 통과, 원하면 별도 커밋), `server/deploy/settings.py`
+`test_deploy_settings.py`, `server/rulebook/assets/v2.4.2/32_spatial_design.md`
+`test_rulebook.py`, `CHANGELOG.md`, `.github/labels.yml`, `docs/reports/2026-08-12-*`,
`docs/curriculum/.moai/`, `src/`.

## 6. 검증·재현 방법

```bash
# 서버 (내 작업 범위 — green)
uv run ruff check server/web/session.py server/orchestrator/runner.py \
  server/orchestrator/tools.py server/llm/claude_code_adapter.py server/llm/config.py \
  server/spatial/presets.py server/spatial/vocabulary.py
uv run pytest server/tests/test_web_session.py server/tests/test_spatial_arrange.py \
  server/tests/test_spatial_vocabulary.py server/tests/test_runner_self_correction.py \
  server/tests/test_claude_code_adapter.py -q
# 라이브: grandma3-web-stable 하나만 띄우고 WS로 요청 → 카드/승인 응답 → executed_ok 확인
```

핵심 파일: `server/web/session.py`(핸들러 라우팅 + `run_instruction`),
`server/spatial/vocabulary.py`(`parse_ring_layout`, `layout_terms_guidance`),
`server/llm/claude_code_adapter.py`(프로파일/스키마), `server/orchestrator/runner.py`(history+교정).


## 7. 핸드오프 이후 같은 날 추가 작업 (모두 커밋·푸시됨)

1. **provider 전환: Claude Code → Gemini (`53e45f2` 이전 런타임 설정)** — Claude Code
   CLI가 `--tools ""` 구조화 출력에서 tool_call을 비신뢰적으로 방출("No such tool
   available" confabulation, 툴 요청 73~113s). Gemini는 정식 function-calling으로
   같은 tool-read가 **51s·완전 정답**. `/api/settings`로 `active_provider: gemini`
   전환(라이브 토글, 재시작 불필요). ask_user 카드도 Gemini 경유로 정상 동작 확인.
2. **UI 개선 일괄 (`53e45f2`, 14파일 +814/-127)** — 설정 패널(모델 셀렉터
   프로바이더별), 접기 4종(실행 결과·미리보기·승인 카드·응답 첫 문장), 컴포저
   2줄+Enter 전송, 응답 중 대기열(순차 실행·취소), 대화 localStorage 유지(200건
   상한)+"대화 지우기", Vite ws 프록시 수정.
3. **새로고침 후 모델 기억 재주입 (`23de232`, 9파일 +216/-1)** — `history_restore`
   클라이언트 메시지(役割 검증·16건 창·4000자 절단) + `session.restore_history`
   (빈 세션만 시드, 라이브 턴 불가침) + onopen 재전송(멱등). 라이브 검증:
   대화→새로고침→"방금 말한 색?"→정답.
4. **주소 규칙** — UI는 항상 `http://127.0.0.1:8765`로 열 것(localStorage origin
   고정). `localhost`로 열면 대화 기록이 빈 것처럼 보인다.
5. **어댑터 후속(이 커밋)** — 전 프로파일 `reasoning` 선택화(필수 스크래치패드가
   Opus 12s/call×멀티툴 턴을 70s+ "서버 꺼짐" 체감으로 만들던 것 해소), CLI
   타임아웃 120s 유지. + 이전 아크 잔여분 커밋: `claude_code_model` 설정 필드,
   룰북 3D 배치·elevation 절, CHANGELOG.