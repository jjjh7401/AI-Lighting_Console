# SPEC-COPILOT-ASBUILT-001 — 인수 기준 (as-built)

각 AC 는 `AC-ASBUILT-NNN` 이며 `spec.md` 의 같은 번호 REQ(`REQ-ASBUILT-NNN`)를 검증한다. 검증은 **저장소에 이미 있는 시험**을 가리킨다. 이 SPEC 을 쓰며 시험을 실행하지는 않았다(`spec.md` §9). 시험이 없는 곳은 「시험 없음」이라고 적었다. 서버 시험은 `server/tests/`, 화면 시험은 `ui/src/`에 있다.

## AC-ASBUILT-001 — 프리쇼 체크리스트의 세 상태와 신호 [REQ-ASBUILT-001]

- **Given** 점검 항목마다 증거가 있거나 없는 입력
- **When** `run_preshow_checklist` 를 돌리면
- **Then** 모든 항목은 `pass`·`fail`·`skip` 중 하나이고(그 밖의 값은 `ValueError`), 증거가 없는 항목은 `skip` 이다. 전체 신호는 항목에서만 계산돼 `fail` 이 있으면 `red`, 없고 `skip` 이 있으면 `yellow`, 모두 `pass` 면 `green` 이다.
- **시험**: `test_preshow_runner.py`, `test_preshow_models.py`, `test_preshow_checks.py`, `test_preshow_pitfalls.py`, `test_preshow_osc_check.py`

## AC-ASBUILT-002 — 앱 안 배선과 미확인 대체값 공개 [REQ-ASBUILT-002]

- **Given** 생존 확인 포트가 주입된 경우, 주입되지 않은 경우, `osc_slot` 이 배선된 경우와 안 된 경우
- **When** 앱 안에서 체크리스트를 돌리면
- **Then** 주입되면 새 소켓 없이 이미 열린 링크로 OSC 점검이 실제로 돌고, 응답이 없는 생존 확인은 바인딩 실패가 아니라 `skip` 이며, 죽은 콘솔은 낡은 `pass` 가 아니라 `skip` 이다. 생존 확인은 얼어붙은 스냅샷이 아니라 게이트의 가장 최근 하트비트를 반영한다. 주입되지 않으면 기본이 `skip` 이고 확인되지 않았음을 밝히며, 배선된 `osc_slot` 은 안내문에 이름으로 나온다.
- **시험**: `test_preshow_tool_wiring.py`, `test_web_session_preshow.py`

## AC-ASBUILT-003 — 「왜 안 켜져?」 진단 [REQ-ASBUILT-003]

- **Given** 기구 번호와 콘솔 읽기 포트
- **When** `diagnose_fixture_light` 가 읽기만으로 원인 후보를 모으면
- **Then** 읽지 못한 값은 `unknown` 이고 `abnormal` 이 아니며, 앱이 읽을 통로가 없는 항목은 `app_cannot_check` 로 「볼 곳」과 함께 나오고, 쓰기 경로를 import 하지 않는다.
- **시험**: `test_fixture_light_diag_t451.py`
- **부분 확인**: 「쓰기 경로를 import 하지 않는다」를 단언하는 경계 시험이 이 파일에 있는지는 이름으로 확인하지 못했다.

## AC-ASBUILT-004 — 페이퍼워크 네 문서 [REQ-ASBUILT-004]

- **Given** 읽기 포트로 읽은 기구 목록, 시퀀스 풀, 프리셋 풀, 배치
- **When** 각 빌더와 렌더러를 부르면
- **Then** 패치 시트·큐 시트·프리셋 목록·축약 매직 시트가 외부 참조 없는 한 장의 HTML 로 나오고 같은 이름으로 덮어써지며, 패키지의 어떤 모듈도 OSC 송신면이나 실행 가능한 포트를 import 하지 않는다.
- **시험**: `test_paperwork_patch_sheet.py`, `test_paperwork_cue_sheet.py`, `test_paperwork_preset_list.py`, `test_paperwork_magic_sheet.py`, `test_paperwork_output.py`, `test_paperwork_print.py`, `test_paperwork_boundary.py`(`test_no_module_imports_the_bridge_or_osc_layer`, `test_no_module_imports_an_execution_capable_port`)

## AC-ASBUILT-005 — 인수인계 묶음의 부분 실패 [REQ-ASBUILT-005]

- **Given** 속성 조회 포트가 없거나 시퀀스 풀을 읽지 못한 경우
- **When** `build_handover_pack` 을 부르면
- **Then** 해당 문서만 빠지고 나머지는 만들어지며, 색인이 빠진 이유를 닫힌 어휘로 적고 각 문서가 콘솔의 얼마만큼을 봤는지를 첫 화면에서 밝힌다.
- **시험**: `test_paperwork_bundle.py`

## AC-ASBUILT-006 — 툴 노출과 웹 표면 은퇴 [REQ-ASBUILT-006]

- **Given** `origin/main` `e4bf3f03` 의 작업 트리
- **When** 페이퍼워크 웹 표면의 파일을 찾고 오케스트레이터 툴 목록을 보면
- **Then** `server/web/paperwork_api.py` 와 `ui/src/components/PaperworkPanel.tsx` 가 없고, 툴 목록에는 `build_patch_sheet`·`build_cue_sheet`·`build_preset_list`·`build_magic_sheet`·`build_handover_pack` 이 있으며, 툴 결과는 HTML 본문이 아니라 쓴 파일 경로와 작은 수치 요약을 싣는다.
- **측정(이 SPEC 을 쓰며 한 것)**: `ls server/web/paperwork_api.py ui/src/components/PaperworkPanel.tsx` 가 두 파일 모두 `No such file or directory` 였고, `git show --stat 35749ec9` 가 삭제 목록(`paperwork_api.py` 411줄, `PaperworkPanel.tsx` 396줄 등 11개 파일)을 보였고, `grep -n "paperwork" server/orchestrator/tools.py` 가 위 툴 이름들을 보였다.
- **시험 없음**: 툴 핸들러가 HTML 본문을 결과에 싣지 않는다는 점을 이름으로 단언하는 시험은 확인하지 못했다.

## AC-ASBUILT-007 — 스트리밍 분기와 대체 경로 [REQ-ASBUILT-007]

- **Given** 받는 곳이 있거나 없는 오케스트레이터, 스트리밍이 있거나 없는 공급자, 스트림 도중 실패하는 공급자, 예외를 던지는 받는 함수
- **When** 한 턴을 돌리면
- **Then** 받는 곳이 없으면 스트리밍 경로를 타지 않고, 공급자에 스트리밍이 없어도 답이 나오며, 조각을 이은 결과가 최종 본문과 같고, 도구 턴도 루프를 돌며, 스트림이 깨지면 한 번에 받는 경로로 떨어지고, 받는 함수의 예외가 턴을 죽이지 않는다.
- **시험**: `test_answer_streaming.py`(7개: `test_without_a_sink_the_streaming_path_is_not_taken`, `test_a_provider_without_streaming_still_answers`, `test_the_deltas_reassemble_into_the_final_text`, `test_a_tool_turn_still_drives_the_loop`, `test_a_broken_stream_falls_back_to_the_buffered_call`, `test_a_throwing_sink_does_not_kill_the_turn`, `test_seq_starts_at_one_and_increases`)

## AC-ASBUILT-008 — `answer_delta` 이벤트 [REQ-ASBUILT-008]

- **Given** 스트리밍되는 한 턴
- **When** 서버가 조각을 낼 때마다 이벤트를 보내면
- **Then** `seq` 는 1부터 단조증가하고 조각을 순서대로 이으면 최종 본문이 되며, 이벤트는 판정을 싣지 않는다.
- **시험**: `test_answer_streaming.py`(`test_seq_starts_at_one_and_increases`, `test_the_deltas_reassemble_into_the_final_text`)
- **시험 없음**: 「이벤트가 판정(상태·명령 목록)을 싣지 않는다」를 직접 단언하는 시험은 확인하지 못했다 — `answer_delta_event` 의 시그니처(`delta`, `seq` 만)로 확인된다.

## AC-ASBUILT-009 — 화면 누적과 버림 [REQ-ASBUILT-009]

- **Given** `answer_delta` 와 `chat_response` 를 차례로 받는 화면 상태
- **When** 조각이 순서대로, 또는 늦게, 또는 종결 프레임과 함께 도착하면
- **Then** 조각은 이어 붙고, `seq` 가 현재 이하인 조각은 무시되고, 대화록에는 쌓이지 않으며, `chat_response` 가 누적분을 버린다.
- **시험**: `ui/src/protocol.test.ts`(`describe("answer_delta")` 다섯 개)
- **시험 없음**: `error` 종결 프레임이 누적분을 버리는 것을 이름으로 단언하는 시험은 확인하지 못했다(`protocol.ts` 의 `error` 분기가 `streamingAnswer: null` 로 되돌린다).

## AC-ASBUILT-010 — 공급자 설정 [REQ-ASBUILT-010]

- **Given** 출하 `config/provider.toml` 과 시험용 설정들
- **When** `load_provider_config` 와 `build_provider` 를 부르면
- **Then** 활성 공급자는 정확히 하나이고, 알 수 없는 공급자·복수 활성·활성 누락·모델 핀 누락·설정 파일 속 자격 증명은 거절되며, `ollama` 는 지원 공급자이고 팩토리가 설정에서 만든다. 출하 설정은 로컬 모델 항목을 가진다.
- **시험**: `test_llm_config.py`(`test_unknown_provider_rejected`, `test_multiple_active_providers_rejected`, `test_missing_active_rejected`, `test_credentials_in_config_rejected`), `test_ollama_adapter.py`(`test_ollama_is_a_supported_provider`, `test_the_factory_builds_it_from_config`, `test_the_shipped_config_carries_a_local_model`)

## AC-ASBUILT-011 — Ollama 요청 구성 [REQ-ASBUILT-011]

- **Given** 대화와 도구 결과 왕복을 담은 요청
- **When** Ollama 요청 본문을 만들면
- **Then** 시스템 프리픽스가 첫 메시지이고 도구 결과 왕복 뒤에도 첫 메시지로 남으며, `keep_alive` 가 항상 실리고, 추론이 꺼져 있다.
- **시험**: `test_ollama_adapter.py`(`test_the_system_prefix_is_the_first_message`, `test_a_tool_result_round_trip_keeps_the_prefix_first`, `test_keep_alive_is_always_sent`, `test_reasoning_is_off`)

## AC-ASBUILT-012 — 도구 미지원 모델과 스트림 조립 [REQ-ASBUILT-012]

- **Given** 도구를 지원하지 않는 모델에 대한 Ollama 거절 응답
- **When** 어댑터가 분류하면
- **Then** 재시도할 수 없는 오류로 분류된다. 스트리밍 응답 조각은 한 봉투로 조립돼 같은 해석기로 파싱된다.
- **시험**: `test_ollama_adapter.py`(`test_a_model_without_tools_is_a_non_retryable_invalid_request`, `test_an_unreadable_tool_call_is_refused_rather_than_guessed`, `test_the_deltas_reassemble_into_the_turn_text`, `test_a_streamed_tool_call_survives_into_the_turn`)

## AC-ASBUILT-013 — 큐 모니터 현재 큐 읽기 [REQ-ASBUILT-013]

- **Given** 확인된 실행기 번호들과 시퀀스 핸들의 `CurrentCue` 값
- **When** `cue_monitor_snapshot` 을 만들면
- **Then** `CurrentCue` 의 마지막 `.` 뒤 정수를 큐 번호로 해석하고(시퀀스 이름에 점이 있어도 같다), 정수가 아니거나 비어 있으면 파싱에 실패해 「읽을 수 없음」으로 두며, 큐 목록에서 실제 큐 번호로 먼저 맞추고 없으면 풀 슬롯으로 맞추며 어느 큐에도 없으면 `None` 이다. 실행기 정체 질의가 실패하면 그 실행기는 읽을 수 없음이다.
- **시험**: `test_web_cue_monitor.py`

## AC-ASBUILT-014 — 큐 모니터 이력 [REQ-ASBUILT-014]

- **Given** 감사 로그에 명령과 탐색 이벤트가 섞여 있는 경우
- **When** `recent_execution_history` 를 부르면
- **Then** 파일 경계를 넘어도 최신부터 읽히고, 거꾸로 읽은 결과를 뒤집으면 앞으로 읽은 결과와 같으며, 이력은 최신 한도만큼 오래된 순이고, 탐색(probe) 종류는 이력에 들어가지 않으며, 한도에서 스캔을 멈춘다.
- **시험**: `test_web_cue_monitor_history.py`

## AC-ASBUILT-015 — 큐 모니터 상태 칩과 배너 [REQ-ASBUILT-015]

- **Given** 실행기 행들과 현재 큐 읽기 결과(모두 같은 이유로 실패, 이유가 갈림)
- **When** 화면이 그리면
- **Then** 상태 칩은 확인됨·실패·알 수 없음 세 등급으로 매겨지고(보낸 적 없는 실행기는 아무것도 그리지 않으며 「미확인」은 문제가 아니다), 방금 전·몇 초·몇 분으로 경과를 말하고, 맥박은 방금 확인된 동작 뒤 창이 지나면 꺼진다. 현재 큐를 못 읽으면 빈 칸이 아니라 이유를 말하고 진행률·카운트다운은 그리지 않는다. 모든 행이 같은 이유로 실패하면 배너 하나와 행별 짧은 자리표시자, 이유가 갈리면 배너 없이 행마다 말한다.
- **시험**: `ui/src/components/CueMonitor.test.tsx`(`grades an ok action as confirmed`, `grades a failed action as failed`, `renders NOTHING for an untouched executor …`, `never renders a percentage or a countdown`, `explains WHY it is unavailable rather than rendering a blank`, `is false once the pulse window has elapsed`)
- **부분 확인**: 「모든 행이 같은 이유」 배너 분기와 움직임 줄이기 동작은 이 SPEC 을 쓰며 시험 이름으로 확인하지 못했다(앞 30개 이름만 읽었다. 움직임 줄이기는 CSS 소관).

## AC-ASBUILT-016 — 타임라인 라이브러리 패널 [REQ-ASBUILT-016]

- **Given** 저장본이 0개, 여러 개, 못 읽음인 라이브러리
- **When** 패널을 그리면
- **Then** 접힌 손잡이가 개수(0이면 「저장된 것 없음」)를 말하고 못 읽었으면 말하지 않으며, 저장·불러오기·삭제 버튼이 항목 상태에 맞게 켜지고 꺼진다.
- **시험**: `ui/src/components/TimelineLibrary.test.tsx`, `ui/src/timelineLibrary.test.ts`

## Definition of Done (as-built)

- [x] 요구사항 16개가 코드 `파일:함수` 로 추적된다(`spec.md` §2~§7).
- [x] AC 16개가 존재하는 시험 파일에 대응한다. 직접 단언을 확인하지 못한 곳은 「시험 없음」·「부분 확인」으로 적었다.
- [ ] 위 시험들을 `origin/main` `e4bf3f03` 이후 트리에서 실행한 통과 증거 — 이 SPEC 에는 없다. 후속 sync 검증 몫이다.
- [ ] 실기 콘솔 확인 — 이 SPEC 은 대체하지 않는다.
