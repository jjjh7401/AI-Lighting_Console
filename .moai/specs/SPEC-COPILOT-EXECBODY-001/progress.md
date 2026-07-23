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

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
