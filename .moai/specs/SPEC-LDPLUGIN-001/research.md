# 구현 근거와 위험 — SPEC-LDPLUGIN-001

[요구사항](spec.md) · [설계](design.md) · [계획](plan.md) · [인수](acceptance.md)

작성 기준일 2026-09-13, 계약 통합 2026-09-14. 현재 코드는 변화 중이므로 고정 line number 대신 경로·symbol을 인용한다. 이 문서는 신규 기능을 위한 근거이며 구현/성능 audit의 완료 보고가 아니다. 문서/schema/example 정합성 검사는 실제 앱·호스트·콘솔 검증과 구별한다.

## 1. 관측된 현재 경계

| 증거 | 확인된 사실 | 새 설계에 주는 제약 |
|---|---|---|
| `server/llm/types.py`: LLMProvider.complete, ToolDefinition/ToolCall/ToolResult/ModelTurn; `factory.py`, `runtime.py` | 기존 provider-neutral 호출·활성 provider 교체 경계가 있다. ModelTurn.provider_payload는 provider opaque 값이다. | 미래 embedded host는 이 adapter 경계를 재사용한다. MCP thin adapter가 새 판단 LLM을 부르지 않음. 현재 인터페이스 존재가 새 Director 연결 증거는 아님 |
| `server/web/session.py`: `_build_unified_song_plan` | finale d-level이 chorus 최고값보다 낮으면 `section_arc_invariant`로 올리는 코드가 있다. | quiet ending 명시 의도는 이 producer를 거치면 변형될 수 있다. 외부 canonical intake는 우회; 내장 cutover는 후속 |
| `server/looks/songcue.py`: `map_sections_to_looks`, 반복 사다리 관련 코드 | label/장르 룩 매핑·후렴 반복 accent/밝기 정책이 존재한다. | 동일 Director 외에 두 번째 예술 policy producer가 남지 않도록 후속에서 제거·호출부 치환 |
| `server/design/song_plan.py`: UnifiedSongLightingPlan, SectionDecision, SongTimelineView 관련 타입 | 내부 d/palette/position/texture/fx/accent·timing 모델과 presentation extension이 있다. | 임의 %·독립 축 timing·FX instance/stop·provenance를 보존하는 새 외부 wire와 동일하다고 가정하지 않음 |
| `server/design/song_cue_composer.py`, `cue_sheet_apply.py` | 기존 composition/apply 재사용 seam. design audit는 destination 슬롯 변경을 충분히 확인하지 않는 경계를 지적했다. | 실제 show/content/destination freshness·create-only를 새 승인 binding에 추가. 현재 성공을 주장하지 않음 |
| `server/web/timeline_api.py`: build_timeline_router | `/api/timelines`는 projection 저장/목록/load/delete이며 load는 SongTimelineStore를 갱신한다. | 외부 plan intake API가 아님. 새 `/api/director/v1`와 canonical immutable storage 필요 |
| `server/web/timeline_library.py`: SongTimelineLibrary | JSON temp+os.replace, read fail-open을 쓰며 스스로 read-only projection이라 설명한다. | 이 패턴은 UI projection에 유지. approval/CAS/journal은 transactional SQLite로 fail closed |
| `server/orchestrator/tools.py`: LXSEQ Store Cue bundle | ClearAll→Group→At/At Preset→Store 명령 생성. `per_row_timing`과 `fx_stopped_groups`는 notes이고 individual timing/stop 실제 emit이 아니다. CueFade는 CUE 정보가 없으면 max I-Fade 근사. | schema/parser 성공으로 ready 금지. 전체 compiler gap을 첫 release 구현 대상으로 둠 |
| 같은 emitter의 timing_commands | cue_time.ms를 TrigTime 문자열로 전달하는 경로가 있다. | 새 canonical absolute song time은 최종 compiled cue delta로 명시 lowering해야 함. playback origin/operator_go·manual_go/trig_time 분리 |
| 같은 emitter의 `notice_partial_ship` | 기존 readback 채널이 cue 내용을 제공하지 않는 한계가 명시되어 있다. | object existence·attribute readback·visual/artistic를 분리하고 미관측을 confirmed로 바꾸지 않음 |
| `server/safety/gate.py`, `server/web/app.py`, `approval_bridge.py`에 대한 design audit | gate의 기존 bool 승인과 새 principal/digest-bound 승인은 같지 않으며 shared programmer interleave 위험이 있다. | exact-artifact approval bridge와 모든 writer 공통 중재 필요. 대상 슬롯 lock만으로 부족 |
| `ui/src/components/{RunbookMode,CueSheetTimeline,ApprovalCard,ReviewCard}.tsx` | 기존 review/timeline UI seam이 있다. | 기존 표시 컴포넌트를 재사용하되 새 director receipt/승인 상태를 일반 approve boolean에 합치지 않음 |

## 2. 전달받은 이전 함수 probe의 한계

사전 조사에서 `uv run --frozen --no-sync python -`의 합성 함수 probe가 exit 0으로 끝났다는 기록을 전달받았다. 이번 작성자는 재실행하지 않았다.

| 입력·관측 | 해석 |
|---|---|
| D `[3,3,3,3,3]`→intro,chorus,chorus,chorus,finale | D-level 기반 role 생산이 음악 근거와 다른 문제임을 드러내는 합성 관측 |
| DirectorOverride(d_level=1)은 D1/director_intent로 해소되나 chorus D5 후 `_build_unified_song_plan`이 finale를 D5/section_arc_invariant로 올림 | 명시 의도가 producer 정책에서 변형되는 경계. compiler가 의도를 이해하지 못한다는 단독 증명은 아님 |
| explicit typed D1 plan은 D1로 compile되지만 ready_for_commit=false; unresolved position은 bundle None+requery 1 | 입력 선택 보존과 실행 준비는 별도. 새 계약/실제 콘솔 지원을 입증하지 않음 |

실제 음악 청취·모델 생성·grandMA3 onPC/console·visual·예술 품질은 이 probe로 확인하지 않았다.

## 3. legacy archive 조사

`src/Lighting_Designer/99_플러그인/lighting-designer-v0.1.1.plugin`은 ZIP member를 읽어 확인했다. manifest의 name은 lighting-designer, version 0.1.1, license Proprietary다. cue-sheet/stage-setup/console-transfer, coordinator, 생성 scripts와 sample data·pycache가 포함된다.

- cue-sheet는 CUE→CUE-EX, tracking/explicit Dim 0, DERIVED 표시, 전곡 확인, 예시 후렴 90/95/100·6–8색을 제시한다.
- stage-setup은 실제 footprint 확인·preset 의미·현장 POS record가 중요하다고 설명한다. 그 서술은 현재 앱 inventory의 실측값이 아니다.
- console-transfer는 individual timing·Phaser·POS·Stomp·TC 이벤트를 `[MANUAL]`로 남기며 future MCP를 예정 기능이라고 쓴다. 이를 구현된 연결/효과로 간주하지 않는다.
- 마이그레이션의 규범은 [design §6](design.md)이다. 지식의 조건·예외·출처만 검토하여 재사용하고 archive 및 sample scripts를 새 runtime으로 복제하지 않는다.

## 4. 충돌하는 역사와 기술 선택

[역사적 SPEC-COPILOT-MCP-001](../SPEC-COPILOT-MCP-001/spec.md)은 draft에서 S2/REQ-MCP-009로 앱 동시 구동을 금지하고 MCP 단독 포트를 요구한다. 이번 사용자 요구는 플러그인과 실행 중인 copilot receiver의 공존이므로 **새 범위 결정**으로 stdio→HTTP·copilot 단독 OSC 소유를 선택한다. 옛 SPEC의 status/lifecycle이나 루트 개발용 `.mcp.json`은 수정하지 않는다.

`.moai/project/tech.md`는 Python/FastAPI/OSC·provider abstraction을 설명하지만 UI 미정 등 초기 계획이 섞여 있다. 현재 존재하는 React UI·LLMProvider·local persistence seam을 우선한다. stdlib sqlite3 채택은 approval/revision/journal 원자 기록을 위한 명시 결정이며 새로운 cloud database는 추가하지 않는다.

## 5. 호스트 자료와 인증 한계

사전 조사에서 확인한 1차 자료 URL은 다음과 같다. 내용은 호스트 통합의 방향을 제공할 뿐 이 프로젝트 패키지의 현재 연결 증거가 아니다.

- Claude 연결 개념: https://claude.com/docs/connectors/building/what-to-build
- Claude Code MCP: https://code.claude.com/docs/en/mcp
- 다른 호스트 plugin 배포 가이드: https://developers.openai.com/plugins/guides/submit-claude-plugin.md
- Secure MCP tunnels: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

최초 호스트는 Claude Code로 고정한다. ChatGPT/다른 adapter는 계정·transport·auth·schema/capabilities·권한 거부를 별도 실기 인증한 조합만 지원으로 표기한다. URL 존재나 일반 plugin 형식이 자동 이식 가능성을 보장하지 않는다. 공개 tunnel은 기본 배치가 아니다.

## 6. 위험→실험→판정

| 위험 | 구현 단계 실험 | 실패 시 결정 |
|---|---|---|
| timing/FX cycle/stop 실제 저장 fidelity | 축별 독립 값·비대칭 pan/tilt·짧은 accent·explicit stop을 onPC trace/readback/visual로 대조 | 해당 capability false, ready 차단; 필수 subset 인증 조합 없으면 release no-go |
| show/preset/destination가 승인 후 변경 | 관측/attestation freshness·empty occupancy를 바꾼 뒤 apply | stale·write 0. 관측 불가를 성공으로 대체하지 않음 |
| model/audio 근거 혼동 | confirmed map 실험과 자동 분석 실험을 분리 | 출처/오류 단계를 표시하고 자동 분석 품질을 연출 품질로 포장하지 않음 |
| 중복 producer·이중 director | 외부 intake 경로의 고정 plan 보존·설치 owner 선택 | 정책 재해석·중복 orchestration 발생 시 no-go |
| 예술 품질 불확실 | held-out blind paired director review와 수정시간 | [인수 G5](acceptance.md)의 사전 기준으로 판정, 보장 개선율 없음 |
| sent-only를 완료로 오인 | 일부/전체 cue 존재 미관측 fixture·실기 관측 | unknown+recovery_required, object 존재 후에도 attribute/visual/artistic 별개 |

합성 [예제](examples/plan.json)와 validation/execution 예상 shape는 실제 실행 증거가 아니다. digest는 계약 §9의 fixture bytes/JCS로 계산하며 실제 audio/MA artifact digest가 아니다. schema·hash·참조·시간/state 예제 검사는 문서 일관성의 증거이고 구현 AC/host/onPC/artistic 인수 통과를 뜻하지 않는다.
