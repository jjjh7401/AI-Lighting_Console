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

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
