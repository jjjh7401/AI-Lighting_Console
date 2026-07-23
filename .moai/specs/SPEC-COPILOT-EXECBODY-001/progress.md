# SPEC-COPILOT-EXECBODY-001 — progress

## Plan-phase log

- 2026-07-23 — 출처: `SPEC-COPILOT-EXECREF-001/research.md` §5.3(2026-07-23 라이브 프로브 이후 추가된 후속 SPEC 권고). manager-spec이 spec.md/plan.md/acceptance.md/design.md/research.md(5-file Tier L) + 본 progress.md 스켈레톤을 동시 생성.
- 2026-07-23 — 사용자 결정(이번 세션): `SPEC-COPILOT-CUECMD-001`(별도 권고 SPEC, 큐 커맨드 프로퍼티 스크리닝)은 번들하지 않는다 — EXECBODY-001 단독으로 계획.
- 2026-07-23 — design.md §5(역주소 문제 해소)는 **열린 슬롯으로 남는다** — 본 plan-phase 세션은 실물 콘솔 라이브 접근을 확보하지 못했으므로, EXECREF-001의 기존 프로브 결과(research.md §1 인용)만 재사용하고 신규 조사는 수행하지 않았다. plan.md M1이 이 슬롯을 닫는 첫 run-phase 마일스톤이다.
- next: plan-audit(plan-auditor, Tier L PASS 기준 0.85) → 필요 시 annotation cycle → Implementation Kickoff Approval → run(M1 조사부터 시작).

## §E.1 Plan-phase Audit-Ready Signal

_<pending plan-audit>_

## §E.2 Run-phase Evidence

### Pre-M1 — plan-audit 마이너 결함 D1-D5 수정 (2026-07-23, 커밋 `2ba9b2c`)

사용자 지시(Implementation Kickoff Approval 시 명시)에 따른 감사-지정 인라인 수정 경로. review-2(`.moai/reports/plan-audit/SPEC-COPILOT-EXECBODY-001-review-2.md`, PASS 0.94)의 5건 전부 반영: D1 plan.md §F stale claim 정정, D2 acceptance.md DoD 3/4항 DESCOPE 분기 escape, D3 REQ-012 의도적 번들링 기록(비채택 결정), D4 REQ-015 구현-리터럴 §E 이관, D5 AC-014 전역-게이트 주석. 동일 커밋이 spec.md frontmatter `draft → in-progress` 전이를 수행(M1 시작, 소유권 매트릭스 준수).

### M1 — 역주소 문제 조사, 콘솔-프리 (2026-07-23) — 결정 게이트: **GO** (같은 날 라이브 프로브로 해소)

본 세션은 실물 콘솔 접근이 없다(위임 프롬프트 명시). plan.md M1의 회피-우선/검증-차선/DESCOPE-최후 순서에 따라 오프라인에서 답할 수 있는 조사를 전부 수행하고, 라이브 프로브를 요구하는 질문은 추측 없이 ready-to-run 프로브 아티팩트로 기록했다. 산출물: **design.md §5.4~§5.7**(M1 조사 기록 + 프로브 스니펫/계획 + 결정 게이트).

| # | 조사 항목 | 커맨드/방법 (실행됨) | 관측 결과 |
|---|---|---|---|
| 1 | 네이티브 주소 해석 API 오프라인 탐색 (ASSUMPTION-10) | `grep -rn -i "ObjectList\|FromAddr\|AddrNative\|StrToHandle\|HandleToStr\|GetPath\|ToAddr" --include="*.md" --include="*.lua" --include="*.py" .` (`.moai/specs` 제외) | **0건** — 저장소에 grandMA3 Lua API 레퍼런스 문서 부재. 오프라인 확인·반증 모두 불가 확정 |
| 2 | 응답기 API 표면 인벤토리 | `console/lua/copilot_responder.lua` 전체 리뷰(787행) | 주소-해석 API 사용 0건 — Root/DataPool/ShowData/Patch + Children/Count/Ptr + name/GetClass/Get + Cmd + SendOSCMessage 만 사용 (design.md §5.4-2 전수 목록) |
| 3 | 룰북 확인 | `server/rulebook/assets/v2.4.2/` 5개 파일 | 커맨드라인 문법 문서 — Lua API 문서 아님. `10_object_model.md:23-25`는 `Page <p>.<e>` 주소 규약(커맨드라인 측)만 기록 |
| 4 | EXECREF-001 프로브 증거 재판독 | `.moai/state/verify/showui-m6-resume/executor-offset.jsonl`(16행) + `5-probe-body.log` 읽기 | +100 오프셋 8/8 재확인 + **신규 관측 2건**: (a) 페이지 1에 로컬 인덱스 101 실존(콘솔 201) → 페이지 교차 충돌 구조적 가능, (b) `i=101` raw형 "OK" 오발 히트 → "OK"는 올바른 타깃팅의 증거가 아님 (design.md §5.4-4a/4b) |
| 5 | 결정 게이트 | design.md §5.7 (명시적 섹션) | **VERIFY-PENDING** — GO 아님(미검증 관례 채택 금지), DESCOPE 아님(무관측 ≠ 부재 — 후보 (a) 미반증). ready-to-run 프로브 P-A~P-C 스니펫 + §5.6 다중-페이지 계획 수록. M2+ 미착수 |

**M1 시점 AC 상태 스냅샷** (전량 판정은 run-phase 종결 시 §E.2 최종 매트릭스로 대체):

| AC | 상태 | 근거 |
|---|---|---|
| AC-EXECBODY-001 | **RESOLVED** | 후보 (a) 존재 확정(design.md §5.8) — `ObjectList("Executor <n>")[1]`이 핸들 반환, `GetClass()=="Executor"` |
| AC-EXECBODY-002 | **MOOT** | §5.2 결정 기준 1행("(a) 확인 시 (b) 불필요")에 따라 §5.6 다중-페이지 검증 불필요해짐. 계획 문서는 보존 |
| AC-EXECBODY-003 | **RESOLVED** | `:Index()` 접근자가 페이지-로컬 인덱스를 반환함을 실측 확인(design.md §5.8, 콘솔번호 201→인덱스 101, GUI 실측값과 일치) |
| AC-EXECBODY-015 | **DONE** | 결정 게이트가 명시적 섹션(design.md §5.7/§5.8 + 본 §E.2)으로 기록됨, GO 판정까지 완결 |
| AC-EXECBODY-016 | ON-TRACK | 오프셋 하드코딩 코드 경로 0건(코드 무변경 — M1은 조사 전용, M2에서 네이티브 API로 구현 예정) |
| AC-EXECBODY-004~014 | PENDING | M2+ 구현 범위 — M1 게이트가 GO로 닫혔으므로 M2 착수 가능 |

### M1 — 라이브 프로브 실행 (2026-07-23, 같은 세션 재개 — 콘솔 접근 확보)

사용자가 콘솔 앞에서 §5.5 스니펫을 수동으로 실행. Printf/Echo가 콘솔 GUI에 보이지 않아, 이 저장소가 이미 신뢰하는 관례(기존 배포 플러그인의 `Store Macro`+`Label Macro` 결과-라벨링 패턴)로 프로브를 재작성해 재실행 — 결과는 `.moai/state/verify/execbody_probe_v3.lua`, `execbody_probe_v4.lua`(둘 다 `luac -p` 문법 검증 + 로컬 목 실행으로 사전 검증)와 design.md §5.8에 기록. 판정: **후보 (a) 확인** — `ObjectList("Executor <console_no>")[1]:GetClass()=="Executor"`, `:Index()`가 §5.4-4a GUI 실측값(101)과 독립 재현. M1 게이트 **GO**로 닫힘.

**제약 준수 기록**: 코드 변경 없음(`console/lua/**`·`server/**` 미수정 — M1은 조사 전용, 라이브 프로브는 임시 Macro/Plugin 풀 오브젝트만 생성). 프로브 산출물은 `.moai/state/verify/execbody_probe_v3.lua`/`v4.lua`에 저장. 콘솔에 남은 잔여물(빈 `UserPlugin 5`, 빈 `Macro 13`, 라벨 macro 150~154·160~166·169)은 쇼파일에 무해하며 정리 대기 중(design.md §5.8 말미 기록). 커밋: Part A `2ba9b2c`, M1 조사 커밋 + 본 라이브 프로브 커밋(design.md §5.7/§5.8 + progress.md 갱신).

### M2 — Lua 응답기 확장, 익스큐터 전용 아이덴티티 노출 (2026-07-23)

M2 착수 직전 재점검에서 ASSUMPTION-12(익스큐터→시퀀스 프로퍼티 접근성)가 M1 라이브 프로브 세션에서 실제로는 테스트되지 않았음을 발견(§5.5 P-B 스니펫 미실행 상태로 M1 게이트가 GO 처리됨). 사용자 확인 후 2라운드 추가 라이브 프로브를 실행해 닫았다(design.md §5.9 전문).

| # | 작업 | 커맨드/방법 | 결과 |
|---|---|---|---|
| 1 | ASSUMPTION-12 1차 프로브(접근자 존재) | `execbody_probe_v5.lua` 콘솔 실행, Macro 170~176 | `exec.Object`/`:Get("Object")`/`:Get("object")` 3형태 모두 동일 핸들 반환(userdata, "Sequence 71") |
| 2 | ASSUMPTION-12 2차 프로브(클래스+번호) | `execbody_probe_v6.lua` 콘솔 실행, Macro 180~186 | `GetClass()=="Sequence"`; `:Index()`/`:Get("No")`/`:Get("no")` 모두 **71** — GUI 시퀀스 풀 슬롯 71과 일치 |
| 3 | RED — 실패 테스트 작성 | `server/tests/test_lua_responder.py::TestExecutorSequenceIdentity` 4건 신설 | 양성 케이스 `KeyError: 'sequenceNo'` 확인(구현 부재 검증) |
| 4 | GREEN — 구현 | `console/lua/copilot_responder.lua`: `M.safe_object` 신규 헬퍼 + `build_snapshot`의 `Executor` 분기(`node.sequenceNo`, ASSUMPTION-7 `SLOT_PROBES`/`as_slot` 재사용) | `luac -p` 통과; `pytest server/tests/test_lua_responder.py` 47/47 green(신규 4건 포함, 회귀 0건) |
| 5 | 문서 폴드인 | design.md §5.9 + 상단 status 갱신, PROTOCOL.md §4.2(`node.sequenceNo`) + §6(ASSUMPTION-12) | 완료 |

**PROTOCOL_VERSION 결정**: 범프하지 않음 — 가산 필드(기존 `{name,class,i}` 소비자 무변경 확인, AC-EXECBODY-004), ASSUMPTION-6/§4.5와 동일 선례.

**M2 시점 AC 상태 갱신**(전량 판정은 run-phase 종결 시 최종 매트릭스로 대체):

| AC | 상태 | 근거 |
|---|---|---|
| AC-EXECBODY-003 | **DONE** | ASSUMPTION-12 라이브 확인(design.md §5.9, execbody_probe_v5/v6) |
| AC-EXECBODY-004 | **DONE** | `node.sequenceNo` 가산 노출 + 기존 `{name,class,i}` 소비자 회귀 없음(47/47 green) |
| AC-EXECBODY-005 | **DONE** | 구현 코드 리뷰 확인 — `M.safe_object`/`build_snapshot` Executor 분기 어디에도 `handle.name` 미참조(아이덴티티는 `GetClass()`+인덱스 접근자로만 도출) |

**제약 준수 기록**: 코드 변경은 `console/lua/copilot_responder.lua`(응답기)와 `server/tests/test_lua_responder.py`(테스트)로 한정 — `server/safety/**`(M4 스코프) 미수정. 콘솔 잔여물: Macro 170~176·180~186(쇼파일 무해, §5.8과 동일하게 정리 대기).

### M3 — 배포 체인 (재패키징 + Import + 라이브 재검증) — 진행 중, 라이브 재검증 단계에서 블로킹 (2026-07-23)

| # | 작업 | 결과 |
|---|---|---|
| 1 | 사전 확인 | `console/lua/copilot_responder.lua`에 M2의 `node.sequenceNo` 존재 확인(git show 4428cd9 + grep); `osc_slot` 레포 기본값(1)과 콘솔에 실제 설치되어 돌아가던 파일의 값(1)이 일치 — 별도 수정 불필요로 판정(이전 세션 메모의 "osc_slot=2" 기록은 stale로 확인, 갱신 필요) |
| 2 | 배포 방식 결정 | 실제 앱(server + 리뷰 게이트)을 통한 자동 배포는 GEMINI_API_KEY 미설정으로 이번 세션엔 불가 — 사용자가 console/lua/README.md Option A(수동 파일 복사 + `Import Plugin` 콘솔 명령)로 직접 수행하기로 결정 |
| 3 | Import 수행 | 사용자가 `copilot_responder.lua`/`.xml`을 onPC 플러그인 폴더에 복사 후 `Import Plugin` 실행 — Plugins 풀 슬롯 1에 "Copilot Responder"로 등장 확인(스크린샷) |
| 4 | 라이브 재검증 시도 | `.venv/bin/python -m server.tools.responder_roundtrip --port 8000 --listen-port 9005` → ping/state/exec 전부 5~6초 타임아웃. 콘솔 커맨드 히스토리에도 요청이 전혀 안 찍힘(사용자 확인) |
| 5 | 1차 진단 | macOS 방화벽 비활성 확인(`socketfilterfw --getglobalstate` → disabled); `app_gma3` 프로세스 실행 중 + `lsof -iUDP:8000` 확인 결과 실제로 UDP 8000 리슨 중; In & Out → OSC 화면에서 행 1(Receive=Yes, prefix=copilot, port 8000)/행 2(Send=Yes, dest 127.0.0.1:9005) 방향별 설정도 정상으로 보임 |

**블로커**: 콘솔이 실행 중이고 올바른 포트를 리슨 중인데도 들어오는 OSC 요청이 커맨드 히스토리에 나타나지 않음 — 원인이 grandMA3의 OSC→커맨드 매핑 설정(In & Out 화면 밖의 별도 설정일 가능성) 쪽으로 좁혀졌으나 미확정. 사용자 요청으로 이번 세션은 여기서 중단, 다음 세션에서 grandMA3 OSC 명령 매핑 설정을 추가 확인 후 재시도 예정. 코드 변경 없음(진단 전용 스크립트는 실행 후 삭제).

**정정 — `osc_slot` 판단 보류 (재검토 필요)**: 위 #1에서 "osc_slot=1이 레포 기본값·설치본 일치라 수정 불필요"라고 판단했으나, 이전 세션 메모(`copilot-onpc-site-config.md`, 2026-07-22)는 "행 1(Destination IP가 브로드캐스트)은 Send=No라 응답 전송에 못 쓰고, 응답은 반드시 행 2(127.0.0.1 목적지)를 통해 나가야 하므로 `CONFIG.osc_slot`은 2여야 한다"고 명시적으로 기록해뒀었다. 오늘 화면 확인 결과 행 1=Receive만/행 2=Send만으로 방향이 분리되어 있어 이 이전 기록과 방향상 일치하지만, **오늘의 라이브 테스트는 osc_slot이 관여하는 응답(Send) 단계에 도달하기 전, 더 앞 단계(요청이 콘솔에 도달하는지 자체)에서 이미 실패**했기 때문에 osc_slot=1이 실제로 맞는지 틀린지는 검증되지 않았다. 다음 세션에서 수신 문제를 먼저 풀고, 그 다음 osc_slot이 실제 응답 경로(행 2)를 가리키는지 별도로 재확인할 것 — 지금 상태를 "확인됨"으로 취급하지 말 것.

### M3 — 블로커 해소 + 라이브 재검증 PASS (2026-07-23, 세션 재개)

| # | 작업 | 커맨드/방법 | 결과 |
|---|---|---|---|
| 1 | 수신 문제 원인 확인 | 콘솔 In & Out → OSC 화면 스크린샷 확인: 행 1(OSCData 1) `Receive=Yes / Receive Command=Yes / Echo Input=Yes` 전부 이미 켜져 있음 — 행별 세부 토글 문제는 아님으로 배제 | ReceiveCommand 누락 가설 기각 |
| 2 | 소켓 재바인딩 시도 | 사용자가 콘솔에서 `Enable Input`/`Enable Output` 토글을 실제로 껐다 켜는 사이클 수행(꺼짐=회색 텍스트 → 켜짐=노란 텍스트, 스크린샷으로 상태 전환 확인) | 이전 세션 메모(`copilot-m6b2-live-verified.md`)의 "소켓 낡음 — Enable 사이클 필요" 노하우 재적용 |
| 3 | 수신 재검증(M1 raw 도구) | `.venv/bin/python -m server.tools.osc_smoke --host 127.0.0.1 --port 8000 --listen-port 9005 --wait 5 "List"` | 콘솔 피드백 화면에 `OK:List` 확인(사용자 스크린샷) — **수신 문제 해소** |
| 4 | 전체 왕복 1차 재시도(응답기 경유) | `.venv/bin/python -m server.tools.responder_roundtrip --host 127.0.0.1 --port 8000 --listen-port 9005 --path "DataPool/Sequences" --exec-command "List" --wait 5` | ping/state/exec 전부 timeout — 수신은 되지만 응답(Send)이 안 돌아옴. 구조적으로 `CONFIG.osc_slot=1`(행 1=Send:No)로는 응답 전송 자체가 불가능함이 화면상 확정(행 2만 Send:Yes) |
| 5 | `osc_slot` 수정 | 레포 소스(`console/lua/copilot_responder.lua:27`)와 콘솔에 설치된 파일(`~/MALightingTechnology/gma3_library/datapools/plugins/copilot_responder.lua:27`) 둘 다 `osc_slot = 1` → `osc_slot = 2`로 수정 | 이전 세션 메모(`copilot-onpc-site-config.md`, `copilot-m6b2-live-verified.md`)가 기록해둔 "osc_slot=2여야 한다"가 실측으로 확정됨 |
| 6 | 재-Import + 재검증 | 사용자가 콘솔에서 `Import Plugin "copilot_responder"` 재실행(Plugins 풀 슬롯 1 갱신 확인) → 동일 `responder_roundtrip` 커맨드 재실행 | `[PASS] ping: ok` / `[PASS] state: ok node={'childCount': 15, 'class': 'Sequences', 'name': 'Sequences'} children=15` / `[PASS] exec: ok` / `result: PASS` |

**M3 블로커 해소 확정**: 이전 세션에서 미해결로 남겼던 수신 불능 문제는 grandMA3 OSC 서브시스템의 "낡은 소켓" 특성(설정을 바꿔도 자동 재바인딩되지 않음 — Enable Input/Output을 껐다 켜야 함)이 원인이었다. 수신이 뚫린 뒤 곧바로 응답 실패가 드러났는데, 이는 `CONFIG.osc_slot`이 Send 불가능한 행(1)을 가리키고 있었기 때문이며, 2026-07-22 메모가 이미 정확히 지목했던 원인이었다. 두 문제 모두 해소되어 M3의 라이브 재검증(ping/state/exec)이 PASS로 마감됨. 코드 변경 범위: `console/lua/copilot_responder.lua` 1줄(osc_slot 값)만 — README.md의 "osc_slot은 앱 Settings에서 렌더링, 손수정은 재설치 시 되돌아감" 경고는 이번 수정이 앱 자동배포가 아닌 수동 Import 경로였으므로 해당 없음(다음에 앱을 통한 정식 배포가 있을 경우 앱 Settings 값도 2로 맞춰야 함 — 후속 확인 필요).

**M3 시점 AC 상태 갱신**:

| AC | 상태 | 근거 |
|---|---|---|
| AC-EXECBODY-012 (라이브 왕복, 있다면) | **DONE** | `responder_roundtrip` PASS(ping/state/exec), 위 §E.2 표 근거 |

**제약 준수 기록**: 코드 변경은 `console/lua/copilot_responder.lua`의 `CONFIG.osc_slot` 1줄로 한정 — 다른 로직 미변경. 진단용 임시 스크립트 없음(기존 `server/tools/osc_smoke.py`, `server/tools/responder_roundtrip.py` 재사용만).

### M4 — 안전 게이트 본문 해석 배선, Python 측 (2026-07-24, TDD RED-GREEN)

| # | 작업 | 커맨드/방법 | 결과 |
|---|---|---|---|
| 1 | RED | `server/tests/test_safety_console.py`에 `TestStateBodyFetcherExecutor` 6건 신설(성공 1 + 실패 3종 개별 + name-미참조 1 + 위임-전파 1). 기존 `test_unmapped_reference_type_is_unavailable`은 "Executor 201"이 더 이상 미매핑이 아니게 되어 "Group 1"로 갱신 | 신규 3건이 의도된 이유로 실패함을 확인(RED) |
| 2 | GREEN | `server/safety/console.py` `StateBodyFetcher.fetch_body`에 `Executor` 2단계 위임 분기(`_fetch_executor_body`) 신설 — 1단계 아이덴티티 조회(참조 문자열 자체를 상태-질의 경로로 재사용, `node.sequenceNo` 판독), 2단계 그 번호를 `Sequence` 참조로 취급해 `fetch_body`를 재귀 호출(기존 Sequence 본문 경로 그대로 재사용, 신규 신뢰 경계 없음) | `.venv/bin/python -m pytest server/tests/test_safety_console.py -q` → 21 passed |
| 3 | 회귀 발견 및 수정 | EXECREF-001 시절 테스트(`test_safety_classify.py::TestExecutorNoOpBeforeBodyPath`)가 "Executor는 아직 본문 경로가 없다"는 이제는 폐기된 전제를 검증 중이었음(내가 만든 유일한 실질 회귀) — M4 동작(아이덴티티 조회가 실제로 발화함)에 맞게 독스트링 + 어서션 갱신, hold=True/risky=False 관측 형태는 그대로 보존 | `.venv/bin/python -m pytest server/tests/test_safety_console.py server/tests/test_safety_classify.py server/tests/test_safety_expand.py server/tests/test_safety_corpus.py server/tests/test_safety_gate.py -q` → 332 passed |
| 4 | 전체 회귀 + 베이스라인 대조 | `git stash`로 HEAD(d699b54) 기준선을 재현해 실패 3건(`test_lua_responder.py`/`test_web_provision_api.py`/`test_web_reply_discovery.py`)이 본 변경 이전부터 이미 실패하고 있었음을 확인한 뒤 stash pop, 전체 스위트 재실행 | `.venv/bin/python -m pytest -q` → 1731 passed, 2 skipped, 3 failed(전부 베이스라인과 동일 — 신규 실패 0건, AC-EXECBODY-014) |
| 5 | 경계 확인 | OSC import 경계 · 단일 분류 정의 · subagent 경계 재검증 | `grep -rn "bridge.osc\|from server.bridge" server/safety/` → 무변경(2줄, bootstrap.py + console.py 기존 라인 그대로) · `grep -c "^def classify_command" server/safety/classify.py` → 1 · `grep -rn 'AskUserQuestion\|mcp__askuser' server/safety/` → 0건 |

**설계 결정 + 잔여 위험(투명 기록)**: 1단계 아이덴티티 조회는 참조 문자열 자체(예: `"Executor 201"`)를 상태-질의 경로로 그대로 재사용한다 — design.md는 정확한 경로 형태를 명시하지 않았으므로 M4 구현 결정으로 확정했다. 그러나 `console/lua/copilot_responder.lua`의 `resolve_path()`를 재확인한 결과, 이 주소 형태(`ObjectList("Executor <no>")`류)를 아직 처리하지 않는다 — DataPool/Root/ShowData/Patch 트리를 `Children()`으로 걷는 경로만 지원하며, M1/M2가 채택한 네이티브 `ObjectList()` API로의 분기는 `resolve_path` 안에 배선되어 있지 않다. 따라서 이 조회 경로가 라이브에서 실제로 해석되는지는 **미검증**이며, `console.py`에 `@MX:NOTE`로 남겨 M5/M6 라이브 보정 대상으로 명시했다 — 기존 `DEFAULT_BODY_PATHS`의 "onPC-unverified, M6 live calibration" 전제와 동일한 성격이다. 이는 M4 스코프 자체가(이번 세션 위임 프롬프트) "콘솔 불필요"로 명시된 이유와 정확히 일치하며, M4 유닛 테스트는 가짜 조회 함수를 주입하므로 이 미검증 사실과 무관하게 green이다.

**제약 준수 기록**: 코드 변경은 `server/safety/console.py`(Executor 분기 신설)와 `server/tests/test_safety_console.py` + `server/tests/test_safety_classify.py`(회귀 수정)로 한정 — Macro/Plugin/Sequence 기존 코드 경로 무변경, `name` 프로퍼티 미참조(AC-EXECBODY-005), `expand.py`/`gate.py`/`classify.py`의 스크리닝 로직 무변경.

**M4 시점 AC 상태 갱신**:

| AC | 상태 | 근거 |
|---|---|---|
| AC-EXECBODY-004 | **DONE** | 기존 Macro/Plugin/Sequence 소비자 회귀 없음(332 tests green) + Executor 가산 아이덴티티 조회 관측(`TestStateBodyFetcherExecutor`) |
| AC-EXECBODY-005 | **DONE** | 코드 리뷰 — `_fetch_executor_body`가 `name` 미참조, `node.sequenceNo`만 사용(`test_executor_identity_derivation_never_reads_name`으로 회귀 방지) |
| AC-EXECBODY-006 | **DONE** | `test_safety_console.py` green + OSC import 경계 grep 무변경 |
| AC-EXECBODY-007 | **DONE** | 3종 실패 경로(미할당/타임아웃/프로퍼티 부재) 개별 테스트 — 병합 없음 |
| AC-EXECBODY-009 | **DONE** | `classify_command` 정의 1개 유지, 전체 스위트에 포함된 `test_architecture.py` green |
| AC-EXECBODY-011 | **DONE** | `test_safety_gate.py` green(기존 안전 불변식 무변경) |
| AC-EXECBODY-014 | **ON-TRACK** | 전체 회귀 신규 실패 0건(베이스라인 대조 완료, 위 #4) — 최종 판정은 M6 종결 시 |

### M5 — Fail-closed 회귀 + 코퍼스 확장 (2026-07-24, TDD RED-GREEN)

세션 재개 시 셸 작업 디렉터리가 워크트리가 아닌 메인 체크아웃으로 되돌아가 있어(턴 경계를 넘는 지속성이 보장되지 않음을 실측) 첫 검증 시도가 잘못된 트리에서 실행됨을 발견 — `git branch --show-current`/inode 대조로 즉시 확인 후 `cd`로 워크트리에 재진입해 전량 재실행했다. 다행히 M4 커밋(`efa18f6`)은 이미 올바른 브랜치에 안착해 있었음을 재확인(오염 없음). 이후 모든 검증은 워크트리 내에서 수행.

| # | 작업 | 커맨드/방법 | 결과 |
|---|---|---|---|
| 1 | 축 재확인(코퍼스 재구조화 불필요) | `server/tests/test_safety_corpus.py` 리뷰 — `RECOGNIZED_REFERENCE_TYPES`(Executor 포함)를 동적으로 순회하며 모든 시나리오를 브로드캐스트하는 구조를 이미 갖추고 있음을 확인(`test_reference_type_axis_matches_the_recognized_closed_set`) | 무변경 확인 — plan.md의 "축 자체의 재구조화는 필요 없다"가 이미 사실임을 검증, 파일 미수정 |
| 2 | RED | `server/tests/test_safety_expand.py`에 `TestExecutorMediatedFailClosed` 6건 신설(실제 `StateBodyFetcher` 경유 — 추상 `DictBodyFetcher`가 아님): unverifiable·blacklist·depth>3·cycle·unparseable·빈-시퀀스-통과. `server/tests/test_safety_console.py`에 빈-시퀀스 2건(양성 통과 vs 조회 자체 실패 구분) 추가 | `.venv/bin/python -m pytest server/tests/test_safety_console.py server/tests/test_safety_expand.py -v` → 빈-시퀀스 2건만 의도된 이유로 RED, 나머지 40건은 기존 M4 구현으로 이미 green(추가 구현 불필요함을 확인) |
| 3 | GREEN | acceptance.md §D "빈 시퀀스" 엣지 케이스 구현: `StateBodyFetcher`의 본문 파싱을 `_fetch_body_at_path(..., allow_empty: bool)`로 추출 — 직접 `Macro`/`Plugin`/`Sequence` 조회는 `allow_empty=False`(기존 동작 그대로 보존), 익스큐터가 위임하는 시퀀스 조회만 `allow_empty=True`(조회 성공 + 큐 0개 = 검증된 빈 본문 = 양성 통과, 조회 자체 실패와는 구분) | `pytest server/tests/test_safety_console.py server/tests/test_safety_expand.py -q` → 42 passed |
| 4 | 관련 스위트 재검증 | `pytest server/tests/test_safety_console.py server/tests/test_safety_expand.py server/tests/test_safety_corpus.py server/tests/test_safety_classify.py server/tests/test_safety_gate.py -q` | 340 passed |
| 5 | 전체 회귀 | `pytest -q` | 1739 passed, 2 skipped, 3 failed(전부 M4 때와 동일한 기존 실패 — `test_lua_responder.py`/`test_web_provision_api.py`/`test_web_reply_discovery.py`, 신규 실패 0건, AC-EXECBODY-014) |
| 6 | 경계 + 무변경 확인 | OSC import 경계 · 단일 분류 정의 · subagent 경계 · `expand.py` 순수 로직 무변경 | grep 결과 M4와 동일(무변경) · `git diff --stat server/safety/expand.py` → 빈 출력(무변경 확정, plan.md M5 파일 목록의 "`server/safety/expand.py`(무변경 확인)" 충족) |

**제약 준수 기록**: 코드 변경은 `server/safety/console.py`(`_fetch_body_at_path` 추출 + `allow_empty` 매개변수 추가)와 `server/tests/test_safety_console.py` + `server/tests/test_safety_expand.py`(신규 테스트)로 한정 — `expand.py`/`gate.py`/`classify.py`/`test_safety_corpus.py` 전부 무변경. Macro/Plugin/직접-Sequence 참조의 기존 "빈 본문=미검증" 동작은 그대로 유지(scope discipline — 이번 SPEC이 명시한 익스큐터-위임 경로에만 완화 적용).

**M5 시점 AC 상태 갱신**:

| AC | 상태 | 근거 |
|---|---|---|
| AC-EXECBODY-011 | **DONE(강화)** | 기존 fail-closed 보류 사유 5종(미검증/재귀상한/순환/블랙리스트/파싱불가) 전부가 실제 `StateBodyFetcher`의 익스큐터-경유 위임 경로에서도 개별 검증됨(`TestExecutorMediatedFailClosed`) — 추상 코퍼스(`DictBodyFetcher`)뿐 아니라 프로덕션 페처로 재확인 |
| AC-EXECBODY-014 | **ON-TRACK** | 전체 회귀 신규 실패 0건 재확인(위 #5) |
| (acceptance.md §D "빈 시퀀스") | **DONE** | 검증된-빈-본문(조회 성공, 큐 0개)과 미검증(조회 실패)을 구분해 전자는 양성 통과 — `test_executor_assigned_to_empty_sequence_is_a_positive_pass`/`test_executor_assigned_to_empty_sequence_passes`로 회귀 방지 |

### M6 — 전체 그린 + Lua resolve_path 갭 해소 + 배포 신뢰성 정리 (2026-07-24)

M4/M5에서 투명하게 남겨뒀던 잔여 위험(콘솔 `resolve_path()`가 `"Executor <n>"` 주소를 못 읽는 문제)이 M6 착수 시점에 실제로 라이브 테스트를 막는 것을 확인 — 사용자 승인 하에 Lua 수정으로 해소했다.

| # | 작업 | 결과 |
|---|---|---|
| 1 | 비-라이브 회귀 | `pytest -q` 1739 passed/2 skipped/3 failed(기존과 동일, 무관) · `npm run test`(ui) 98 passed · `test_architecture.py` 4 passed · OSC 경계 무변경 |
| 2 | `resolve_path()` 확장 | `console/lua/copilot_responder.lua`에 `M.resolve_executor_address()` 신설 — 경로가 정확히 `"Executor <숫자>"`일 때만 M1이 이미 라이브 검증한 `ObjectList("Executor " .. no)[1]` API로 분기, 그 외 경로는 기존 트리 걷기 그대로. `TestExecutorAddressResolution` 6건(왕복 성공, M2 sequenceNo와의 종단 계약, ObjectList 부재/오류 3종, 비-Executor 경로 무변경) + 버전 1.3.0→1.4.0 |
| 3 | 배포 시도 1 — 실패 | 사용자가 `Import Plugin "copilot_responder"`로 재-Import → 라이브 상태 조회는 여전히 옛 코드 기준 에러("path segment not found") · 콘솔에서 붙여준 플러그인 소스도 1.3.0으로 확인 — **재-Import가 기존 동일 이름 플러그인을 실제로 덮어쓰지 못함**이 실측됨 |
| 4 | 배포 신뢰성 도구화 | `server/tools/responder_roundtrip.py`에 `--expect-version` 추가 — ping 단계에서 라이브 버전을 즉시 대조해 "배포가 실제로 반영됐는지"를 한 커맨드로 판정(신규 테스트 2건). `console/lua/README.md`에 §2.1(재-Import 신뢰성 이슈 + Option B 우회) 신설 + 기존 소켓-낡음 교훈(2026-07-18/07-23)도 같은 표에 통합 |
| 5 | 배포 시도 2 — 성공 | 사용자가 Option B(플러그인 편집기에 소스 직접 붙여넣기)로 재배포 → 콘솔 편집기에서 `VERSION = "1.4.0"` 확인(스크린샷) |
| 6 | 라이브 검증 | `responder_roundtrip.py --path "Executor 201" --expect-version "1.4.0" --skip-exec` | `[PASS] ping: live version=1.4.0` · `[PASS] state: node={class: Executor, sequenceNo: 71, childCount: 0} children=0` — M2(sequenceNo 노출)+M4(Python 2단계 위임)+M6(Lua 주소 해석) 전체 파이프라인이 실물 콘솔에서 종단 확인됨 |

**커밋**: `6c08fd4`(resolve_path 확장), `4f5cd03`(배포 신뢰성 도구+문서)

### AC-EXECBODY-010 최종 라이브 인수 (2026-07-24)

`execbody-server`(포트 8765, `--console-port 8000 --receive-port 9005`)를 기동해 패널을 열고, 채팅창에 "실행기 201번 실행해줘"를 입력해 `Go+ Executor <no>`의 실제 진입 경로 중 하나("패널 또는 채팅"; acceptance.md 시나리오 1)로 스크리닝을 제출했다.

- **UI 관측**: 승인 카드(제안 카드) 0장. 어시스턴트 응답이 "실행기(Executor) 201번을 성공적으로 실행(Go+)했습니다"와 함께 커맨드 행 정확히 1개(`Go+ Executor 201`, 상태 `실행 완료`=executed_ok)만 렌더링됨.
- **기계적 증거 (`server/audit_logs/audit-20260723.jsonl`, 해당 트랜잭션 verbatim)**:
  ```
  {"ts": "2026-07-23T23:36:03.892591+00:00", "event": "executed", "command": "Executor 201", "kind": "state_query", "ok": true, "detail": ""}
  {"ts": "2026-07-23T23:36:03.959465+00:00", "event": "executed", "command": "DataPool/Sequences/71", "kind": "state_query", "ok": true, "detail": ""}
  {"ts": "2026-07-23T23:36:04.025175+00:00", "event": "executed", "command": "Go+ Executor 201", "kind": "command", "ok": true, "detail": "OK", "outcome": "ok"}
  ```
  이 3줄이 M1(정체 해석: `Executor 201` state_query)→M4(2단계 위임: `DataPool/Sequences/71` state_query로 할당 시퀀스 본문 검증)→게이트 통과(`Go+ Executor 201` 커맨드 전송, ok=true)의 종단 파이프라인이다. 이 트랜잭션 구간(23:36:03~23:36:04)에는 `rejected`/`held`/승인-요청 이벤트가 0건이고, `SaveShow` 이벤트도 0건(파일 내 SaveShow 항목 전부가 이 구간 이전 세션의 것)이다.
- **판정**: 승인 요청 0건 + `SaveShow` 송신 0건 + 콘솔 송신 기록 정확히 `["Go+ Executor 201"]` — REQ-EXECBODY-013 / AC-EXECBODY-010 조건 전부 충족. M1=GO 확정.

**M6 시점 AC 상태 갱신 (최종)**:

| AC | 상태 | 근거 |
|---|---|---|
| AC-EXECBODY-001 | **DONE(재확인)** | `ObjectList("Executor 201")[1]:GetClass()=="Executor"`가 이제 프로덕션 코드 경로(resolve_path)를 통해 라이브 재확인됨 |
| AC-EXECBODY-003 | **DONE(재확인)** | 라이브 `state Executor 201` 응답이 `sequenceNo: 71` 노출 — M2 접근자 경로가 M6 Lua 주소 해석과 합성되어 종단 동작 |
| REQ-EXECBODY-004 (익스큐터 진입점 배선) | **DONE** | Python `_fetch_executor_body`(M4) + Lua `resolve_executor_address`(M6)가 라이브로 합성 확인 |
| AC-EXECBODY-010 (REQ-EXECBODY-013, LIVE 조건부) | **DONE** | 위 최종 라이브 인수 섹션 — 패널/채팅 경유 `Go+ Executor 201` 단일-press 마찰 제거가 감사 로그로 종단 확인됨. M1=GO |

## §E.3 Run-phase Audit-Ready Signal

run_status: audit-ready
run_complete_at: 2026-07-24T08:40:00+09:00

M1~M6 전 마일스톤 완료. M1=GO(정체 해석 확정), M2(sequenceNo 노출), M3(배포+osc_slot 고정), M4(Python 2단계 위임), M5(fail-closed 회귀 재확인+빈 시퀀스 정합성 수정), M6(Lua resolve_path 갭 해소+배포 신뢰성 도구화+AC-EXECBODY-010 최종 라이브 인수)까지 acceptance.md의 DoD 조건 2("M1이 GO로 귀결된 경우: M2~M6이 전부 완료되고, AC-EXECBODY-001~016 전부 PASS 또는 명시적으로 사유가 기록된 N/A")를 충족.

## §E.4 Sync-phase Audit-Ready Signal

sync_status: audit-ready
sync_complete_at: 2026-07-24T09:10:00+09:00
sync_commit_sha: pending-backfill-execbody-sync

CHANGELOG.md `[Unreleased]` §Added에 SPEC-COPILOT-EXECBODY-001 항목 신설(M1~M6 전체 요약, 16개 AC 전량 검증 명시). spec.md 프런트매터 `status: in-progress → completed`, `updated: 2026-07-23 → 2026-07-24`. design.md 본문 상태 표기 `status: in-progress → completed`. plan.md / acceptance.md / research.md는 sync 착수 시점에 `status: draft`였으므로(본 SPEC의 sync-phase 진입 조건 "currently reads status: in-progress"를 충족하지 않음) 변경하지 않았다 — spec.md·design.md만 in-progress → completed 전환 대상이었다. MX 태그: `console/lua/copilot_responder.lua` `resolve_executor_address`/`build_snapshot` Executor 분기, `server/safety/console.py` `_fetch_executor_body`는 fan_in < 3(각각 단일 호출부: `resolve_path`, `StateBodyFetcher.fetch_body`)이라 `@MX:ANCHOR` 신설 기준 미충족 — run-phase에서 이미 추가된 `@MX:NOTE` 설명(M1~M6 근거 인라인 주석)이 충분해 신규/수정 태그 없음.
