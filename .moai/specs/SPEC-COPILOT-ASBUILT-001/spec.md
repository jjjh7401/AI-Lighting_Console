---
id: SPEC-COPILOT-ASBUILT-001
title: "사전 SPEC 없이 출하된 코파일럿 기능 묶음 — 프리쇼·페이퍼워크·답변 스트리밍·로컬 모델·큐 모니터 (as-built)"
version: "0.1.0"
status: implemented
created: 2026-10-21
updated: 2026-10-21
author: jaihyun
priority: P3
phase: "Lighting Copilot v1.2 target"
module: "server/preshow/, server/paperwork/, server/llm/runtime.py, server/llm/ollama_adapter.py, server/llm/gemini_adapter.py(complete_stream), server/llm/config.py, config/provider.toml, server/orchestrator/runner.py(스트리밍 분기), server/web/messages.py(answer_delta_event·cue_monitor_event), server/web/cue_monitor.py, ui/src/components/CueMonitor.tsx, ui/src/components/TimelineLibrary.tsx, ui/src/protocol.ts(answer_delta)"
lifecycle: spec-anchored
tags: "as-built, preshow, paperwork, answer-streaming, local-llm, ollama, cue-monitor, timeline-library, orphan-spec-ids"
tier: M
related_specs: [SPEC-COPILOT-MVP-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-DASHUI-001, SPEC-LDBEAT-003]
---

# SPEC-COPILOT-ASBUILT-001 — 사전 SPEC 없이 출하된 코파일럿 기능 묶음 (as-built)

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-10-21 | 최초 작성. **as-built 묶음 SPEC** — 커밋에 이미 인용된 SPEC ID 넷(`SPEC-COPILOT-PRESHOW-001`, `SPEC-COPILOT-PAPERWORK-001`, `SPEC-COPILOT-STREAM-001`, `SPEC-COPILOT-LOCALLM-001`)은 `.moai/specs/` 에 디렉터리가 없다(인벤토리 §3.4 (C), §4.4). 개별 SPEC 넷을 만들 가치는 없다고 보아(각 1~2커밋) 절 하나씩으로 두어 **추적성을 보존한다**. 거기에 "SPEC 없음"으로 명시한 채 출하된 큐 진행 모니터(`CueMonitor`, 커밋 #15 "T-C", 코드 주석 「Ad-hoc contract, no SPEC on file」)와 타임라인 라이브러리 패널을 절로 더했다. 코드·시험·UI·콘솔·서버 런타임은 바꾸지 않았다. |

## §0. as-built SPEC 읽는 법

1. 요구사항은 현재 동작의 기술이다. 「코드 근거」는 이 SPEC 을 쓰며 읽은 `파일:함수`, 「시험」은 저장소에 있는 시험 파일이다. 시험이 없으면 「시험 없음」이다.
2. 절 제목의 원 ID 는 커밋 메시지에만 남아 있던 ID 다. 이 SPEC 은 그 ID 를 새 SPEC 으로 되살리지 않고 **절 이름으로만** 보존한다. 파일명·frontmatter `id` 는 `SPEC-COPILOT-ASBUILT-001` 이다.
3. 소스 PR/커밋은 인벤토리 §4.4 값이다. 이 SPEC 을 쓰며 머지 커밋을 직접 확인한 것은 §B 의 `35749ec9`(#857)뿐이다.
4. 인벤토리와 코드가 달랐던 곳은 §8 에 적었다. 둘이 다르면 코드를 따랐다.
5. 시험을 실행하지 않았다. 「시험」 열은 존재 증거이지 통과 증거가 아니다(§9).

## §1. 절 목록과 원 ID

| 절 | 원 ID(커밋에만 있던 것) | 소스 | 현재 상태 |
|---|---|---|---|
| §A 프리쇼 체크리스트 | `SPEC-COPILOT-PRESHOW-001` | #14 (2026-08-02) | 살아 있음 — 오케스트레이터 툴 `preshow_check`·`diagnose_fixture_light` |
| §B 페이퍼워크 | `SPEC-COPILOT-PAPERWORK-001` | #13 (2026-08-02) | **웹 표면 은퇴**(#857, 2026-10-20), 패키지·오케스트레이터 툴은 살아 있음 |
| §C 답변 스트리밍 | `SPEC-COPILOT-STREAM-001` | #70 (2026-08-20) | 살아 있음 — Gemini·Ollama 만 스트리밍 |
| §D 로컬 모델(Ollama) | `SPEC-COPILOT-LOCALLM-001` | #70 (2026-08-20) 및 인근 | 살아 있음 — 출하 설정의 활성 공급자는 아님 |
| §E 큐 진행 모니터 | (ID 없음 — 「T-C, wave 2」, 커밋 #15) | #15 (2026-08-02) | 살아 있음 |
| §F 타임라인 라이브러리 패널 | (ID 없음) | 사용자 요청 2026-08-14 | 살아 있음 — 상세는 `SPEC-LDBEAT-003` |

## §2. §A 프리쇼 체크리스트 (원 ID `SPEC-COPILOT-PRESHOW-001`)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-ASBUILT-001 | **The** 프리쇼 체크리스트 **shall** 한 번에 다음을 점검해 항목마다 닫힌 세 상태(`pass`·`fail`·`skip`) 중 하나로 보고한다: OSC 왕복(ping/state)과 수신 포트 바인딩, 시퀀스/실행기 존재, 프리셋 풀 존재, 프리셋(룩) 라이브러리 로드 무결성, 지난 소켓 복구 권고, 콘솔 OSC 설정 행(`osc_slot`)이 `Send = Yes` 인지, 응답 포트 드리프트. 점검에 필요한 증거가 없으면 조용한 `pass` 가 아니라 `skip` 으로 내리고(「warn」 상태는 일부러 없다), 전체 신호는 항목에서 계산한다 — 하나라도 `fail` 이면 `red`, 아니면 `skip` 이 있으면 `yellow`, 모두 `pass` 일 때만 `green`. | `server/preshow/runner.py:run_preshow_checklist`; `models.py:CheckResult`, `PreshowReport.signal`; `checks.py`; `pitfalls.py`; `osc_check.py` | `server/tests/test_preshow_runner.py`, `test_preshow_models.py`, `test_preshow_checks.py`, `test_preshow_pitfalls.py`, `test_preshow_osc_check.py` |
| REQ-ASBUILT-002 | **When** 앱 안에서 돌아가면, 체크리스트 **shall** 이미 열린 콘솔 링크의 생존 확인(`liveness_port`)을 새 소켓을 열지 않고 쓰며 앱이 이미 쥔 수신 포트를 다시 묶지 않는다. 생존 확인이 주입되지 않으면 OSC 점검은 `skip` 이다. 사이트의 실제 `osc_slot` 이 배선되지 않았으면 기본값을 이름으로 쓰되 그 값이 확정된 사이트 설정이 아닌 미확인 대체값임을 점검 결과에 밝힌다. 이 점검은 `ping` 과 `state` 만 보내고 `exec` 동사를 보내지 않는다. | `runner.py`(`liveness_port` 분기, `configured_osc_slot`); `osc_check.py:check_osc_roundtrip_via_liveness`, `check_receive_port_binding_via_liveness`; `server/orchestrator/tools.py:preshow_check`; `server/web/app.py`(`preshow_receive_port`, `preshow_osc_slot`) | `test_preshow_tool_wiring.py`, `test_web_session_preshow.py` |
| REQ-ASBUILT-003 | **When** 감독이 「왜 안 켜져?」를 물으면, 한 기구의 점등 조건 진단(`diagnose_fixture_light`, 카드 t451) **shall** 콘솔에서 읽기만으로 켜지는 기구와 나란히 읽어 차이를 찾는다. 상태는 여섯(`ok`·`abnormal`·`candidate`·`info`·`unknown`·`app_cannot_check`)이고 읽지 못한 것은 `abnormal` 이 아니라 `unknown` 이다. 앱이 읽을 통로가 없는 것(3D 창의 Beam 페이더·GPU 경고 등)은 지어내지 않고 「볼 곳」과 함께 `app_cannot_check` 로 돌려준다. 이 모듈은 쓰기 포트를 받지 않고 쓰기 경로를 import 하지 않으며, 네트워크 DMX 출력은 참고로만 적는다. | `server/preshow/fixture_light.py:diagnose_fixture_light`; `tools.py:diagnose_fixture_light` | `test_fixture_light_diag_t451.py` |

## §3. §B 페이퍼워크 (원 ID `SPEC-COPILOT-PAPERWORK-001`) — 웹 표면은 은퇴

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-ASBUILT-004 | **The** 페이퍼워크 **shall** 콘솔 상태를 읽기만 하는 인쇄용 문서 넷 — 패치 시트, 큐 시트(시퀀스를 큐까지 한 단계 내려), 프리셋 목록(프리셋 풀을 프리셋까지), 축약 매직 시트(이름·패치 요약·배치 표) — 를 같은 게이트 감사 질의 포트로 만들고, 각각 외부 스타일시트·스크립트·글꼴·이미지 참조가 없는 한 장의 HTML 로 렌더한다. 이 패키지는 OSC 송신면과 실행 포트를 import 하지 않는다. 파일은 결정적 이름으로 덮어써 다시 만들어도 디렉터리가 어지러워지지 않고, 쓰기 위치는 동결 앱 여부를 따른다. | `server/paperwork/data.py:build_patch_sheet`, `build_cue_sheet`, `build_preset_list`, `build_magic_sheet`; `render.py`; `output.py:resolve_paperwork_dir`, `write_paperwork_html` | `test_paperwork_patch_sheet.py`, `test_paperwork_cue_sheet.py`, `test_paperwork_preset_list.py`, `test_paperwork_magic_sheet.py`, `test_paperwork_output.py`, `test_paperwork_print.py`, `test_paperwork_boundary.py` |
| REQ-ASBUILT-005 | **The** 인수인계 묶음 **shall** 위 네 문서에 이를 잇는 `index.html` 한 장을 더해 한 폴더로 낸다. 일부만 실패해도 전체가 실패하지 않는다 — 속성 조회 포트가 없거나 기구 목록을 못 읽으면 패치 시트만, 콘솔이 답하지 않은 풀이면 그 시트만 빠지고 나머지는 만들어진다. 빠진 문서의 이유는 닫힌 어휘로 색인에 적고, 각 문서가 콘솔의 얼마만큼을 봤는지를 첫 화면에서 밝힌다. | `server/paperwork/bundle.py:build_handover_pack`, `HANDOVER_STATUSES`; `tools.py:build_handover_pack` | `test_paperwork_bundle.py` |
| REQ-ASBUILT-006 | **The** 오케스트레이터 **shall** 위 문서를 툴(`build_patch_sheet`·`build_cue_sheet`·`build_preset_list`·`build_magic_sheet`·`build_handover_pack`)로 노출하되 HTML 본문은 툴 결과에 싣지 않고 쓴 파일 경로와 작은 수치 요약만 싣는다. **Where** 페이퍼워크 웹 표면(UI 패널 `PaperworkPanel`·`/api/paperwork` 라우트·`server/web/paperwork_api.py`)은 2026-10-20 #857(`35749ec9`)로 제거되어 **더는 존재하지 않는다**. `server/paperwork` 패키지는 오케스트레이터 툴이 계속 쓰므로 남아 있다(`server/vwx` 는 독스트링에서 언급만 하고 import 하지 않는다). | `server/orchestrator/tools.py`(툴 등록); `git show 35749ec9`(제거 목록) | 툴 경로(`build_*` 핸들러)를 이름으로 겨냥한 시험은 이 조사에서 확인하지 못했다(`test_paperwork_*` 는 빌더·렌더러·묶음을 덮는다). 은퇴한 웹 표면의 시험(`test_web_paperwork_api.py`, `PaperworkPanel.test.tsx`)은 같은 커밋에서 삭제됨 |

## §4. §C 답변 스트리밍 (원 ID `SPEC-COPILOT-STREAM-001`)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-ASBUILT-007 | **Where** 오케스트레이터에 답변 받는 곳(`AnswerSink`)이 있고 공급자에 `complete_stream` 이 있으면, 모델 호출 **shall** 답변 본문을 도착하는 대로 흘려보낸다. 받는 곳이 없거나 공급자에 스트리밍이 없으면 종전의 한 번에 받는 경로를 쓴다 — 스트리밍은 선택적 가속이고 턴의 판정 결과는 두 경로에서 같다. 스트리밍 호출이 `ProviderError` 가 아닌 예외로 실패하면 같은 턴을 한 번에 받는 경로로 다시 시도한다. 받는 쪽 함수가 예외를 던져도 턴은 죽지 않는다. 공급자 슬롯(`ProviderSlot`)은 호출마다 선택된 공급자의 스트리밍 능력을 판정해 전달한다 — 정적으로 광고하면 스트리밍 없는 공급자를 막거나 모든 공급자의 스트리밍을 꺼 버린다(2026-08-20 실측에서 델타 0개였다고 코드 주석이 적었다). | `server/orchestrator/runner.py`(`call_model`); `server/llm/runtime.py:ProviderSlot.complete_stream` | `server/tests/test_answer_streaming.py`(7개) |
| REQ-ASBUILT-008 | **The** 서버 **shall** 답변 조각을 `answer_delta` 이벤트(`delta`, `seq`)로 보내며 이는 누적 채널이다 — 받는 쪽이 `delta` 를 순서대로 이어 붙이면 지금까지의 본문이 된다. `seq` 는 턴 안에서 1부터 단조증가한다. 이 채널은 판정(상태·명령 목록·요약)을 싣지 않고 그것은 계속 `chat_response` 의 몫이므로 채널이 통째로 유실돼도 답은 온전하다. | `server/web/messages.py:answer_delta_event`; `server/web/session.py`(`_send(answer_delta_event(...))`) | `server/tests/test_answer_streaming.py`(`test_seq_starts_at_one_and_increases`, `test_the_deltas_reassemble_into_the_final_text`) |
| REQ-ASBUILT-009 | **The** 화면 **shall** `answer_delta` 조각을 `seq` 가 현재보다 클 때만 이어 붙이고(늦게 도착한 옛 조각은 무시해 본문이 중복되지 않게), 턴 종결 프레임(`chat_response` 와 `error`)에서 조각 버퍼를 버리고 `chat_response` 의 본문으로 갈아 끼운다 — 두 벌을 남기면 같은 답이 두 번 보이기 때문이다. 조각은 대화록에 쌓지 않는 소멸성 상태다. 스트리밍을 구현한 공급자는 Gemini(`generate_content_stream`)와 Ollama 둘뿐이며 Anthropic·Claude Code 어댑터에는 `complete_stream` 이 없어 한 번에 받는 경로를 쓴다. | `ui/src/protocol.ts`(`answer_delta` 리듀서, `streamingAnswer`); `server/llm/gemini_adapter.py:complete_stream`; `server/llm/ollama_adapter.py:complete_stream` | `ui/src/protocol.test.ts`(`describe("answer_delta")` 다섯 개: 이어 붙이기, 늦은 조각 무시, 대화록에 안 쌓음, `chat_response` 가 누적분 버림, `error` 가 턴을 끝냄) |

## §5. §D 로컬 모델 (원 ID `SPEC-COPILOT-LOCALLM-001`)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-ASBUILT-010 | **The** 공급자 설정 **shall** `ollama` 를 지원 공급자(`anthropic`·`claude_code`·`gemini`·`ollama`)의 하나로 둔다. 설정 파일은 활성 공급자를 정확히 하나만 두고, 자격 증명을 담지 않으며(키는 환경 변수), 알 수 없는 공급자나 복수 활성은 거절한다. 출하 설정(`config/provider.toml`)의 `[provider.ollama]` 는 모델 `gemma4:26b`, 주소 `http://127.0.0.1:11434`, `keep_alive = "60m"` 이고 활성 공급자(`active`)는 현재 `gemini` 이므로 로컬 모델을 쓰려면 `active` 를 바꾸고 다시 시작한다. | `server/llm/config.py:load_provider_config`, `OllamaSettings`, `SUPPORTED_PROVIDERS`; `server/llm/factory.py:build_provider`; `config/provider.toml` | `test_llm_config.py`, `test_ollama_adapter.py`(`test_ollama_is_a_supported_provider`, `test_the_factory_builds_it_from_config`, `test_the_shipped_config_carries_a_local_model`) |
| REQ-ASBUILT-011 | **The** Ollama 어댑터 **shall** 시스템 프리픽스를 모든 요청의 첫 메시지로 보내고 순서를 바꾸지 않는다 — 프리픽스 캐시가 성능의 전부이기 때문이다(코드 주석의 2026-08-20 실측: 약 28,100 토큰 프리픽스에서 첫 호출은 gemma4:26b 54초, 같은 프리픽스의 이후 호출은 약 0.25초). 모델을 상주시키는 `keep_alive` 를 기본값에 맡기지 않고 매 요청에 명시하며, 추론(reasoning)은 끈다. 도구 결과가 오가는 왕복에서도 프리픽스가 첫 메시지로 남는다. | `server/llm/ollama_adapter.py:_messages`, `OllamaAdapter`, `DEFAULT_KEEP_ALIVE` | `test_ollama_adapter.py`(`test_the_system_prefix_is_the_first_message`, `test_a_tool_result_round_trip_keeps_the_prefix_first`, `test_keep_alive_is_always_sent`, `test_reasoning_is_off`) |
| REQ-ASBUILT-012 | **When** 모델이 도구를 지원하지 않아 Ollama 가 요청을 거절하면(`does not support tools`), 어댑터 **shall** 재시도할 수 없는 오류로 분류한다 — 가중치에 없는 능력은 재시도로 생기지 않기 때문이다. 스트리밍은 줄바꿈으로 구분된 JSON 조각을 받아 하나의 응답 봉투로 모은 뒤 한 번에 받는 경로와 같은 해석기로 파싱하므로 스트리밍 턴과 버퍼링 턴은 같은 객체다. 키가 필요 없는 공급자에 키 주입을 시도해도 충돌하지 않는다(무동작). | `ollama_adapter.py:_NO_TOOLS_MARKER`, `complete_stream`, `_parse_reply` | `test_ollama_adapter.py`(`test_injecting_a_keyless_provider_is_a_no_op_not_a_crash` 포함) |

## §6. §E 큐 진행 모니터 (ID 없음 — 「T-C, wave 2」)

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-ASBUILT-013 | **When** 화면이 `cue_monitor_request` 를 보내면, 서버 **shall** 이미 콘솔에서 확인된 실행기 번호마다(번호 해석은 `dash.py:resolved_executor_nos` 가 한 곳에서 한다) `Executor <n>` 정체 질의로 시퀀스를 알아내고 그 시퀀스의 큐 목록을 읽어 `cue_monitor` 이벤트 하나로 답한다. 현재 큐는 시퀀스 핸들의 `CurrentCue`(`<이름>.<번호>`)에서 읽고 실행기 핸들에서는 읽지 않는다. 마지막 `.` 뒤가 맨 정수가 아니면 지어내지 않고 「읽을 수 없음」으로 둔다. 진행률과 타이머 필드는 계약상 없다. 실행기 행은 감독의 계획된 진행 순서(`planned_sequence_nos`)로 정렬할 수 있다. | `server/web/cue_monitor.py:cue_monitor_snapshot`, `build_cue_progress`, `parse_current_cue_index`, `planned_show_order`, `order_by_show_plan`; `server/web/messages.py:cue_monitor_event` | `test_web_cue_monitor.py` |
| REQ-ASBUILT-014 | **The** 최근 실행 이력 **shall** 콘솔 접속 없이 감사 로그(`AuditLog`)만 읽어 만든다 — 콘솔이 닿지 않아도 모니터가 그리는 바닥이다. 이력은 `kind == "command"` 인 실행만 오래된 순으로 담아(게이트 자신의 상태·속성 질의·하트비트·배포 탐색은 빼서 모니터가 자기 읽기 트래픽으로 이력을 오염시키지 않게 한다) 한도까지 거꾸로 읽다가 멈추고, 각 행에 `(target_kind, target_no)` 귀속을 달되 귀속하지 못한 행도 버리지 않는다. | `cue_monitor.py:recent_execution_history`, `_parse_command_target`, `_last_app_action_for_executor` | `test_web_cue_monitor_history.py` |
| REQ-ASBUILT-015 | **The** 화면의 상태 칩 **shall** 세 등급 — 확인됨(✓, 앱이 명령을 보냈고 콘솔이 ok 로 받음), 실패(✕, 보냈으나 실패·무응답), 알 수 없음(○, 앱이 이 실행기에 아무것도 보낸 적 없음) — 을 색뿐 아니라 글자와 기호로 구분하며, 이 칩은 「콘솔이 지금 재생 중이다」를 뜻하지 않고 오직 「앱이 마지막으로 무엇을 보냈고 콘솔이 받았는가」만 뜻한다. 맥박 효과는 방금 확인된 이벤트 뒤 몇 초만이고 움직임 줄이기 설정에서는 정적 강조로 바뀐다. 모든 행의 현재 큐 읽기가 같은 이유로 실패하면 그 사실을 패널 수준에서 한 번만 말하고 행에는 짧은 자리표시자만 둔다. 이유가 행마다 갈리면 배너를 보류하고 행마다 말한다. | `ui/src/components/CueMonitor.tsx`(`currentCueBannerState`, `currentCueRowView`) ; `server/web/cue_monitor.py`(`last_app_action`) | `ui/src/components/CueMonitor.test.tsx` |

## §7. §F 타임라인 라이브러리 패널

| REQ | 요구사항 | 코드 근거 | 시험 |
|---|---|---|---|
| REQ-ASBUILT-016 | **The** 타임라인 라이브러리 패널(런북의 곡 타임라인 위, 2026-08-14 사용자 요청)은 이름·버전이 있는 저장본을 저장·불러오기·삭제하는 화면이다. 접힌 상태에서도 저장본 개수를 말하고 못 읽었으면 개수를 꾸미지 않는다. 불러오기 보호·음원 링크·재접속 등 수명주기 동작은 `SPEC-LDBEAT-003` REQ-LDBEAT3-005~010 이 기술하므로 여기서 되풀이하지 않는다. | `ui/src/components/TimelineLibrary.tsx:TimelineLibraryView`; `server/web/timeline_api.py` | `ui/src/components/TimelineLibrary.test.tsx`, `ui/src/timelineLibrary.test.ts` |

## §8. 인벤토리와 코드가 달랐던 곳

| 인벤토리 서술 | 코드에서 읽은 것 |
|---|---|
| 「답변 스트리밍 + 로컬 gemma4:26b / Ollama」를 한 덩어리로 서술 | 스트리밍을 구현한 공급자는 Gemini 와 Ollama 둘이다. Anthropic·Claude Code 어댑터에는 `complete_stream` 이 없다(REQ-ASBUILT-009). |
| 로컬 모델이 앱의 모델처럼 읽힘 | 출하 설정의 `active` 는 `gemini` 다. Ollama 는 설정을 바꿔야 쓰는 오프라인 백업 경로다(REQ-ASBUILT-010, `provider.toml` 주석). |
| `server/paperwork/` 를 은퇴 대상으로 서술하는 듯한 문면 | 은퇴한 것은 웹 표면(UI 패널·`/api/paperwork`)뿐이다. 패키지와 오케스트레이터 툴 다섯은 살아 있다(REQ-ASBUILT-006). |
| `SPEC-COPILOT-PRESHOW-001` 의 `server/preshow/` 7개 파일 모두를 한 SPEC 으로 서술 | `fixture_light.py`(766줄)는 카드 t451 의 별개 진단이며 이 SPEC 이 REQ-ASBUILT-003 으로 따로 적는다. |

## §9. 검증하지 못한 것

- 시험을 실행하지 않았다. 「시험」 열은 `ls`·`grep` 으로 존재와 이름을 확인한 것이다.
- 코드 주석이 적은 실측(프리픽스 54초·0.25초, 델타 0개 등)은 이 SPEC 을 쓰며 재측정하지 않았다.
- 프리쇼 체크리스트의 일부 점검이 실제 콘솔에서 `pass` 를 내는지는 확인하지 않았다.
- `CueMonitor.tsx`(904줄)는 머리 주석과 시험 이름 수준에서 읽었고 전체 분기를 따라가지 않았다.
- 소스 PR/커밋 번호는 인벤토리 값이다.

## §10. 제외 범위

### Out of Scope — 새 동작과 코드 변경

- 이 SPEC 은 사후 기록이다. 코드·시험·UI·콘솔·서버 런타임을 바꾸지 않는다.
- 은퇴한 페이퍼워크 웹 표면을 되살리는 일은 하지 않는다.

### Out of Scope — 다른 SPEC 이 맡는 동작

- `precheck_patch` 등 패치 점검은 `SPEC-COPILOT-PRECHK-001` 이 맡는다. 프리쇼 체크리스트는 그 읽기 포트를 재사용할 뿐이다.
- 대시보드 UI 는 `SPEC-COPILOT-DASHUI-001`, 큐 모니터가 쓰는 실행기 번호 해석은 `server/web/dash.py` 소관이다.
- 공급자 선택·폴백 판정(`REQ-MVP-039/040`)은 `SPEC-COPILOT-MVP-001` 이 맡는다.
- 타임라인 라이브러리의 수명주기 동작은 `SPEC-LDBEAT-003` 이 맡는다.
