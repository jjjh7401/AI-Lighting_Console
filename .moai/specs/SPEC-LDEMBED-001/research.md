# 근거·이식 위험 — SPEC-LDEMBED-001

[요구사항](spec.md) · [계획](plan.md) · [인수](acceptance.md) · [선행 근거](../SPEC-LDPLUGIN-001/research.md)

2026-09-13 기준 구현 전 후속 프로젝트다. 아래 source는 읽기 조사이며 신규 runtime·provider 연결·콘솔·예술 품질 검증은 실행하지 않았다. 공유 계약의 문서/schema/example 정합성 검사는 해당 runtime 인수와 구별한다.

## 1. 재사용할 기존 경계

| 기존 경로·symbol | 관측 | 구현 결정 |
|---|---|---|
| `server/llm/types.py::LLMProvider.complete` | system_prefix/conversation/tools→ModelTurn의 provider-neutral 인터페이스 | 새로운 LLM SDK 직접 호출 경로를 만들지 않고 embedded host adapter로 감싼다. 추가 context limit 정보가 필요하면 adapter-neutral metadata로 제공 |
| `ToolDefinition`, `ToolCall`, `ToolResult`, `ToolResultsMessage` | schema parameters, call id/name/arguments, correlated error 결과, 한 turn의 결과 묶음 | 계약의 동일 7 tool definitions를 변환·dispatch하고 structured tool loop를 명시 구현 |
| `ModelTurn.provider_payload` | 같은 provider에 echo하기 위한 opaque payload; 다른 provider는 neutral fields로 재구성 | checkpoint에서 provider 경계 유지. parity 비교에서는 제외하지만 같은 provider resume 보존 조건을 따로 검증 |
| `server/llm/factory.py::build_provider`, `runtime.py::ProviderSlot` | 설정된 단일 provider 구성·다음 turn에 적용하는 교체 seam | 임의 새 모델 의무화 금지. run 중 교체는 waiting_user 후 명시 resume·neutral context 재구성 |
| `server/llm/claude_code_adapter.py` 및 anthropic/gemini/ollama adapter 파일 | 여러 provider adapter 구현 파일이 존재 | 파일 존재는 모든 account/model의 실제 가용성 인증이 아니다. 이번 SPEC의 실제 smoke 조합을 별도 명시 |
| `server/web/session.py`와 `ui/src/{App,protocol,useCopilotSocket}.ts*` | 기존 세션과 UI event 경계 | durable run state/event cursor·same principal routing·cancel/resume를 이 경계에 연결 |
| `server/web/timeline_api.py`, `timeline_library.py` | timeline save/load는 projection-only. library JSON 읽기 fail-open | canonical plan·run checkpoint는 director SQLite 원본 사용. projection에서 승인·원본을 재구성하지 않음 |

## 2. 두 예술 producer의 clean cutover

| 현재 생산 경로 | 근거·문제 | 후속 변경 |
|---|---|---|
| `server/web/session.py::_build_unified_song_plan`과 호출부 | 내부 SectionDecision 생산, finale를 chorus floor로 올리는 section_arc_invariant 코드 존재 | 인터뷰 의도와 evidence를 shared embedded host 입력으로 바꾸고 canonical plan을 받는다. old arc/강도/역할 재해석 정책·obsolete 호출 제거 |
| `server/orchestrator/tools.py::prepare_songcue`→`server/looks/songcue.py::map_sections_to_looks` | 별도 label/genre→look 선택, 반복 ladder·accent 관련 정책 존재 | 같은 Director 절차로 라우팅하고 별도 예술 mapping 제거. math·rig 검증·표시 등 독립적으로 유용한 helper는 그대로 재사용 |

사전 전달받은 합성 probe는 D `[3,3,3,3,3]`의 역할 생성, D1 override가 finale에서 D5로 상승, 직접 typed plan의 D1 보존 및 ready 차단을 보여주었다. 이는 기존 producer와 compiler를 구별할 근거이지 내장 모델의 우월성 증거가 아니다. 재실행하지 않았다.

선행 외부 intake는 이미 두 producer를 우회해야 한다. 후속에서는 앱의 두 기존 진입점을 치환하고 old artistic fallback을 남기지 않는다. 역사적 결과·timeline 표시를 위해 필요한 데이터 readers는 보존하지만 새 생성 producer로 재활성화하지 않는다.

## 3. 선행 의존과 변하지 않는 경계

- [공유 계약](../SPEC-LDPLUGIN-001/contract.md)이 wire·state·권한을 소유한다. context에 실제 show/group/preset/compiler/destination·freshness를 묶고 create-only 새 Sequence·명시 playback을 유지한다.
- applied는 모든 생성 cue 존재 확인을 요구한다. 값/readback/visual/artistic/terminal은 별도 관측이며 sent-only는 unknown+recovery_required다. 내장 UI가 이 분리를 단일 성공 badge로 축약하지 않는다.
- 모델은 same ld_* read/validate/submit/propose 범위다. human 공통 read/submit route와 human-only approve/apply를 구분한다. 앱 내부라는 이유로 model에 human approval scope를 부여하지 않는다.
- legacy `lighting-designer-v0.1.1.plugin`의 provenance/Proprietary·조건부 예술 예시·수동 기능 한계는 [선행 migration matrix](../SPEC-LDPLUGIN-001/design.md)를 그대로 적용한다. 내장 host가 archive scripts/pycache를 실행 엔진으로 수입하지 않는다.
- 역사적 [SPEC-COPILOT-MCP-001](../SPEC-COPILOT-MCP-001/spec.md)의 단독 OSC/앱 종료 전제는 선행의 scope-level 공존 결정으로 대체된 범위다. 파일/lifecycle은 수정하지 않는다.

## 4. 불확실성에 대한 실험 설계

| 위험 | 구체 실험 | 판정 |
|---|---|---|
| 동기 provider가 cancel을 지원하지 않음 | delayed complete 중 UI cancel, 늦은 응답, resume generation 검사 | UI 응답·추가 dispatch 0·late 결과 폐기. 실제 provider 종료를 보장한다고 표시하지 않음 |
| mutation 완료와 checkpoint 사이 crash | submit/propose 전후 crash point·idempotency replay/GET | canonical record 하나·blind 신규 key retry 0. 미확정이면 waiting_user |
| 압축 후 intent/철회 지식 유실 | 긴 대화·quiet ending·FX stop·revoked record와 재시작 | immutable plan/의도 보존, revoked context 제거, stale면 재검토 |
| host 차이를 model 차이로 오인 | model 없는 fixed-plan dispatcher parity와 실제 모델 generation 비교를 분리 | 전자는 semantic diff 0, 후자는 blind paired 품질/수정시간으로 평가 |
| 중복 정책 잔존 | old 두 진입점 실제 smoke·quiet ending/같은 후렴 강도 입력 | 새 shared runtime으로만 생산·정책 덮어쓰기 0 |
| 외부 plugin regression | embedded 활성 상태에서 실제 Claude Code tools/context/submit/feedback | external workflow 계속 동작·동시 CAS 충돌 공개 |

현재 advanced 자동 음악 분석·실제 audio 청취·전문 감독 수준은 입증되지 않았다. 선행 confirmed-map pilot을 prerequisite로 삼고 후속 host 이식 품질을 따로 측정한다. 예술적 성공률·수정시간 개선율을 사전 보장하지 않는다.
