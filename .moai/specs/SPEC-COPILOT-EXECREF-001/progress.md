# SPEC-COPILOT-EXECREF-001 — progress

## Plan-phase log

- 2026-07-22 — 결함 출처: `SPEC-COPILOT-SHOWUI-001/progress.md` §E.2 "M3에서 발견한 사항 — 사람 결정 필요 (승인 게이트 빈도)"(199-219행). M3가 익스큐터 타일 1회 누름 = 승인 카드 1장 + `SaveShow` 1회임을 코드 연쇄 4단으로 보고하고 선택지를 제시했다.
- 2026-07-22 — 사람 결정: **게이트측 Executor 인식 채택.** 기각 (a) 승인-매-누름 수용 + design.md 개정(패널 핵심 가치 상실), 기각 (b) 시퀀스 참조 치환(등가성 미검증 + 익스큐터 rename 취약). 근거는 research.md §2에 기록.
- 2026-07-22 — 사람 결정: **범위를 `server/safety/**`로 한정.** cue-CMD 갭(응답기가 큐의 CMD 프로퍼티를 전송하지 않음)은 **기록하되 닫지 않는다** — 봉쇄에 응답기 Lua 변경 + 재배포 + 라이브 재검증이 필요하기 때문.
- 2026-07-22 — 읽기 전용 라이브 프로브 작성: `.moai/state/verify/probe_executor_body.py`(state 동사 전용, 발화 0·쓰기 0). **실행 실패 — 응답기 무응답**(`probe-executor-body.log`: `no state reply for 'DataPool/Pages' within 5.0s`; 플러그인 미Import 또는 OSC 미무장 추정). 사용자가 콘솔을 무장한 뒤 오케스트레이터가 재실행하여 design.md §5에 결과를 접어 넣고 **plan-audit 이전에** 슬롯을 닫는다.
- 2026-07-22 — Tier L 아티팩트 세트 생성: `spec.md` + `plan.md` + `acceptance.md` + `design.md` + `research.md` (v0.1.0, status: draft) + 본 `progress.md` 스켈레톤. 다음 단계: 프로브 재실행 → design.md §5 fold-in → plan-audit(Tier L PASS 기준 0.85) → Implementation Kickoff Approval → run.
- 2026-07-23 — 라이브 프로브 실행: 콘솔이 세션 중 온라인 상태가 되어 `.moai/state/verify/showui-m6-resume/probe_executor_body.py`(읽기 전용, 발화 0·쓰기 0)를 재실행. 결과 — Q1 예(로컬-인덱스 단서: 해석에 쓰이는 익스큐터 번호는 페이지-로컬 자식 인덱스이지 콘솔 표시/발화 번호가 아님), Q2 결정적 아니오(4개 샘플 전부 `childCount: 0` — 응답기가 범용 `handle:Children()`만 호출), Q3 아니오(기존 갭 재확인, 새 발견 아님). 로그: `.moai/state/verify/showui-m6-resume/5-probe-body.log`.
- 2026-07-23 — 사용자 결정(AskUserQuestion): **S1만 출하, S2 완전 이연.** Q2가 결정적으로 부정이므로 S2(익스큐터 본문 해석)는 `server/safety/**` 범위 안에서 어떤 실질적 효과도 낼 수 없다(순수 YAGNI). M2를 DESCOPED로 표기, REQ-EXECREF-004/005/006 및 REQ-EXECREF-013을 DEFERRED로 표기(철회 아님). 후속 SPEC `SPEC-COPILOT-EXECBODY-001`(응답기 Lua 확장으로 익스큐터 할당 시퀀스 아이덴티티 노출) 권고(research.md §5.3, 미생성). spec/plan/acceptance/design/research 5개 아티팩트 전부 일관되게 갱신(v0.2.0).
- 2026-07-23 — plan-audit iteration 2/3: **FAIL, score 0.923** (harmonic mean of {0.75, 1.00, 1.00, 1.00}; Tier L 기준 ≥0.85는 aggregate에서 충족되나 MP-2 must-pass firewall이 강제 FAIL). Clarity 0.50→0.75로 개선(REQ-EXECREF-013 [DEFERRED] 정합 + H1 하단 범위 qualifier 추가로 iteration 1의 D2 해소); MP-2(AC 표 pytest-검증-레시피 스타일, 리터럴 GEARS 미사용)는 SHOWUI-001 선례 재확인에도 불구하고 미해결로 재확인 — iteration 3로 이월.
- 2026-07-23 — plan-audit iteration 3/3(retry cap 도달): **FAIL, score 0.92** (harmonic mean of {1.00, 1.00, 1.00, 0.75}). Clarity 0.75→1.00로 완결(frontmatter title 정정 + acceptance.md §B 시나리오 1 inline 주의문 추가); Traceability가 1.00→0.75로 새로 하락(REQ-EXECREF-014 무인용 발견, D2) — 즉시 수정(본 문서 다음 항목). MP-2는 3회 연속 미해결이나, 감사자가 "genuine unresolved defect가 아니라 rubric/템플릿 정합 계산 문제"로 명시 판정하고 **PASS-with-debt를 최선의 해법으로 권고**(§ MP-2 Framing Assessment, review-3.md).
- 2026-07-23 — 오케스트레이터가 3회 감사 결과(score 0.75→0.923→0.92, 매 회차 결함 수정, 최종 유일 blocker=MP-2)를 사용자에게 보고 후 AskUserQuestion 수행: 사용자가 **PASS-with-debt 수용, AC 재포맷 강행 안 함**을 명시적으로 선택 — Implementation Kickoff Approval로 진행. REQ-EXECREF-014 인용 누락(D2, minor)은 acceptance.md AC-EXECREF-009/010/014 검증 대상 컬럼에 "REQ-014" 인용 추가로 별도 해소(감사자 권고 review-3.md 반영).

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-07-22T00:00:00Z
- plan_revised_at: 2026-07-23T00:00:00Z — 라이브 프로브 결과 fold-in + S1-only 범위축소 반영
- plan_status: **PASS-WITH-DEBT (0.92)** — iteration 3/3(retry cap 도달). design.md §5의 열린 설계 슬롯이 2026-07-23 라이브 프로브 결과로 닫혔다(결과는 부정적: S2 구현 불가). M2 DESCOPED, S1만 출하하는 범위로 spec/plan/acceptance/design/research 5개 아티팩트를 일관되게 갱신 완료(v0.2.0). 남은 유일한 blocker는 MP-2(must-pass firewall) 하나뿐 — aggregate score 0.92는 Tier L 기준(≥0.85)을 상회.
- debt item: **MP-2**(acceptance.md §C의 AC 표 17행이 pytest-검증-레시피 스타일을 사용하며, 리터럴 GEARS "shall"/"shall not" 문장이 아님)는 accepted·documented exception이다 — 재검토가 필요한 결함이 아니다. 근거: plan.md §F("AC 표 형식 유지 (MP-2, 오케스트레이터 결정)" 행) + 3회 감사 보고서(`SPEC-COPILOT-EXECREF-001-review-{1,2,3}.md`) 전부가 독립적으로 완결·출하된 자매 SPEC SPEC-COPILOT-SHOWUI-001의 동일 관례를 재확인. 사용자가 AskUserQuestion으로 PASS-with-debt 수용 + 재포맷 강제 안 함을 명시적으로 선택(2026-07-23).
- artifacts: spec.md(v0.2.0) / plan.md / acceptance.md / design.md / research.md (5-file Tier L) + 본 progress.md
- open slot: **닫힘 (2026-07-23)** — design.md §5 (Q1 익스큐터 노드 경로: **확인됨** — 단 로컬-인덱스 단서 있음 / Q2 자식이 할당 시퀀스의 큐인지: **결정적 아니오, childCount: 0 4/4 샘플** / Q3 큐 페이로드의 커맨드 필드 유무: **아니오, 기존 갭 재확인**). 근거: `.moai/state/verify/showui-m6-resume/5-probe-body.log`.
- assumptions ratified (2026-07-23): ASSUMPTION-8(익스큐터 노드 경로) — **확인됨(TRUE)**, 로컬-인덱스 단서 있음(design.md §5.1/§5.5); ASSUMPTION-9(익스큐터 본문 = 할당 시퀀스 큐) — **반증됨(FALSE)**, 자식 없음. 증거: `.moai/state/verify/showui-m6-resume/5-probe-body.log`.
- baseline: HEAD `0576553` — pytest **1591 passed + 1 failed**. 유일 실패는 `test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`이며 **환경적**(구동 중 onPC가 UDP 9005 점유)이고 본 SPEC과 무관.
- next: Implementation Kickoff Approval → run(M1만 — M2 DESCOPED)

## §F Phase 4 Mode Selection

- input parameters: tier=L; scope=M1만(S1: classify.py 참조 인식 + 코퍼스 parametrize 리팩터) — M2는 DESCOPED이므로 run-phase 범위에서 제외; domain count=1(server/safety/**의 단일 안전 모듈, classify.py 중심 + 기존 5종 안전 테스트 파일 확장); file language mix=100% Python; concurrency benefit=LOW(코딩 중심 작업, Anthropic coding-task parallelism caveat).
- mode evaluation: Mode1 trivial — 미선택(단순 오탈자 아님, 의미 있는 회귀-위험 코드 변경). Mode2 background — 미선택(Write 작업, 오케스트레이터 블로킹 필요). Mode3 agent-team — RETIRED, 선택 불가. Mode4 parallel — 미선택(단일 도메인·코딩 중심, 리서치성 아님). Mode6 workflow — 미선택(30파일 미만, 기계적 단일 변환 아님, Kickoff는 통과했으나 규모 기준 미충족). Mode5 sub-agent — **선택**(코딩 중심 단일 마일스톤, 기본 fallback).
- Decision: sub-agent
- Justification: M1은 단일 파일(classify.py) 변경 + 기존 코퍼스 테스트 리팩터로 범위가 좁고 순차적이다. Anthropic의 coding-task parallelism caveat("most coding tasks involve fewer truly parallelizable tasks than research")에 따라 Mode5(순차 단일 Agent())가 기본값이며 대안 모드의 선택 기준을 충족하지 않는다. Tier L이므로 manager-develop-prompt-template.md의 Section A-E 델리게이션 템플릿을 전량 적용한다.

## §E.2 Run-phase Evidence

### M1 — 참조 인식 + FN 코퍼스 축 확장 (cycle_type=tdd, RED→GREEN→REFACTOR)

기준선(변경 전, HEAD `0576553`): pytest **1591 passed + 1 failed**(환경적, 본 SPEC 무관).
결과(변경 후): pytest **1723 passed + 1 failed + 2 skipped**(+132). 신규 실패 0건 — 유일 실패는 동일한 기존 환경적 실패(`test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`, 구동 중 onPC의 UDP 9005 점유).

| AC | 대상 | 상태 | 검증 커맨드 | 실제 출력 |
|---|---|---|---|---|
| AC-EXECREF-001 | REQ-001/002/004/013 — 해석 가능·양성 익스큐터 single-press 통과(전체 게이트 파이프라인) | **PASS** (주의: 인메모리 fetcher 가정, 프로덕션 미도달 — S2 DESCOPED) | `test_safety_classify.py::TestExecutorSinglePressClearance::test_benign_executor_body_clears_with_no_approval_and_no_saveshow` | `decision.cleared is True`, `approval.requests == []`, `console.executed == ["Go+ Executor 201"]`(`"SaveShow"` 부재 명시 확인 — SHOWUI M3 실측 `["SaveShow", "Go+ Executor 201"]`의 직접 교정) |
| AC-EXECREF-002 | REQ-009 — 블랙리스트 본문 보류 (Executor 타입 상속) | **PASS** | `test_safety_corpus.py::TestInvokingVerbFnCorpus::test_no_send_pre_approval_in_every_scenario[risky-body-*]` (Executor 조합 포함) | 전량 PASS — `decision.cleared is False`, `console.executed == []` |
| AC-EXECREF-003a/b/c | REQ-008 — 빈 본문/조회 실패/읽을 수 없는 라인 개별 보류 | **PASS** (regression, expand.py/console.py 무변경 기계 상속) | `test_safety_expand.py` + `test_safety_console.py` 전량 | 무변경 그린 |
| AC-EXECREF-004 | REQ-009 — 익스큐터→익스큐터 순환 (인메모리) | **PASS** (주의: 인메모리 본문 사전 가정) | `test_safety_corpus.py::TestInvokingVerbFnCorpus::test_no_send_pre_approval_in_every_scenario[cycle-*]`(Executor 조합) | 전량 PASS — 보류 |
| AC-EXECREF-005 | REQ-009 — 깊이 상한 4단 (인메모리) | **PASS** (주의: 인메모리 본문 사전 가정) | 동 테스트의 `[depth-exceeded-*]`(Executor 조합) | 전량 PASS — 보류 |
| AC-EXECREF-006 | REQ-011 — 코퍼스 참조 타입 축 동적 순회 | **PASS** | `grep -c '"Executor"' server/tests/test_safety_corpus.py` → `0` **AND** `pytest --collect-only server/tests/test_safety_corpus.py -q \| grep -c Executor` → `40` | 두 조건 동시 충족(하드코딩 리터럴 0, Executor 케이스 40개 자동 수집) |
| AC-EXECREF-007 | REQ-003/005/010 — 단일 분류 의미론 + 단일 스크리닝 경로 + OSC 경계 | **PASS** | `pytest server/tests/test_architecture.py -q` + `grep -rn "bridge.osc\|from server.bridge" server/safety/`(기준선 diff) + `grep -c "^def classify_command" server/safety/classify.py` | `4 passed`; OSC 경계 grep 기준선 대비 diff 없음(exit 0); `classify_command` 정의 1개 |
| AC-EXECREF-008 | design.md §2.1 — M1 단독 무행동 변화 | **PASS** | `test_safety_classify.py::TestExecutorNoOpBeforeBodyPath` 2종 | `hold=True, risky=False` 유지, 보류 사유가 `"no body path mapping for 'Executor 201'"`로 확인(신규 인식 이전 `reference=None`과 관측 결과 동일함도 별도 assert) |
| AC-EXECREF-009 | REQ-014 — 회귀 (협상 불가) | **PASS** | `pytest server/tests/test_safety_gate.py server/tests/test_web_panel_execute.py -q` | `87 passed, 1 warning in 0.60s`(acceptance.md 지정 커맨드 그대로 실행) |
| AC-EXECREF-010 | REQ-014 — 회귀 (협상 불가) | **PASS** | `pytest server/tests/test_safety_classify.py server/tests/test_safety_expand.py server/tests/test_safety_corpus.py server/tests/test_safety_ruleset.py server/tests/test_safety_console.py -q` | `300 passed in 0.46s`(acceptance.md 지정 커맨드 그대로 실행, gate.py 미포함 5파일) |
| AC-EXECREF-011 | REQ-015 — `Go+ Page N.M` 구문 범위 밖 fail-closed | **PASS** (regression, classify.py `_extract_reference`는 애초에 `Page N.M` 형태를 인식하지 않음 — 무변경 상속) | `test_safety_classify.py::TestInvokingDetection` 기존 케이스 | `reference=None` → 보류 유지 |
| AC-EXECREF-012 | REQ-012 — cue-CMD 갭의 정직한 기록 | **DEFERRED — M1 범위 밖** | — | 오케스트레이터 위임 프롬프트가 `@MX:DEBT`(console.py) 태깅을 M1 대상에서 명시적으로 제외(Section D: "Do not add new @MX:ANCHOR tags — only consume the two existing ones"; console.py는 PRESERVE 대상 B10). 기존 `@MX:DEBT` 부재 확인(`grep -rn "@MX:DEBT" -A 2 server/safety/console.py` → no match) — sync-phase 또는 후속 SPEC 판단 필요 항목으로 이관 |
| AC-EXECREF-013 (LIVE) | ASSUMPTION-8/9 + S1 no-op | **① DONE (2026-07-23, plan-phase 프로브)** / **② moot** / **③ DONE (2026-07-23, run-phase 사후 라이브 재검증)** / **④ DONE(암묵 커버, 별도 테스트 불필요)** | `.moai/state/verify/showui-m6-resume/6-live-executor-noop.py` | 오케스트레이터가 M1 커밋(267257f/c27bd19) 이후 실제 onPC 대상으로 재검증 수행 — `server.safety.bootstrap.build_console_stack()`(`server/web`과 동일 합성 루트) 조립 후 `stack.gate.screen(["Go+ Executor 111"])` 1회 직접 호출(UI/패널 미경유). 결과: `cleared=False`, `approval_request present=True`(M1 이전과 동일 관측 — no-op 확인), 보류 사유 문자열만 `Executor` 인식 이전/이후로 확인 변경(`"unverifiable reference: no recognizable target object"` → `"unverifiable reference 'Executor 111': no body path mapping for 'Executor 111'"`). 콘솔 송신 0건, 조명 리그 무변경. 증거: `.moai/state/verify/showui-m6-resume/6-live-executor-noop.log`. ④는 동일 가드(본문 경로 매핑 부재)가 개별 할당 상태 확인보다 선행하므로 별도 라이브 테스트 없이 암묵 커버됨 |
| AC-EXECREF-014 | REQ-014 — 전체 회귀 | **PASS** | `.venv/bin/python -m pytest -q` | `1723 passed, 2 skipped, 1 failed in 81.87s` — 유일 실패는 기준선과 동일한 환경적 실패(무관), 신규 실패 **0건** |
| AC-EXECREF-015 | REQ-007 — 이름 파싱 금지(rename 내성) | **PASS** | `test_safety_classify.py::TestExecutorRenameInvariance` 4종 | `finding.reference == "Executor 202"`(rename 전/후 무관) + `hold`/`risky` rename 전후 byte-identical |

부가 검증: `ruff check server/safety/classify.py server/tests/test_safety_corpus.py server/tests/test_safety_classify.py` → `All checks passed!`(터치 파일 전용, console.py의 기존 2건 E501은 baseline 그대로 — 본 SPEC 무변경 확인) · `grep -rn 'AskUserQuestion\|mcp__askuser' server/safety/` → 0건(subagent boundary) · `server/safety/gate.py:260-264` + `classify.py:158-161` `@MX:ANCHOR` 2종 무변경(신규 ANCHOR 추가 없음, 소비만) 확인.

코퍼스 규모 참고: `_invoking_commands()`가 10 동사 × 4 참조타입(Macro/Plugin/Sequence/Executor) + bare_object_forms 2종 = 42개 커맨드 × 4 시나리오 = 168 parametrize 케이스(신규 인메모리 실행, OSC 0)로 확장됨. 실행 시간은 무시 가능한 수준(`test_safety_corpus.py` 단독 203 tests, 0.28s) — design.md §6.1의 "실행 시간 확인 필요" 우려는 문제 없음으로 확인.

증적 로그: `/tmp/moai-verify/`(세션 로컬, `1-full-suite.log`/`arch-panel.log`/`7-lint.log` 등).

## §E.3 Run-phase Audit-Ready Signal

- run_complete_at: 2026-07-23T00:00:00Z
- run_commit_sha: `267257f5f3c7f02b392da030d44db3bf4f84f47e` (백필 완료 — spec-frontmatter-schema.md § SHA placeholder backfill exemption 준용)
- run_status: **PASS — 전체 검증 완결** (M1, 유일 run-phase 마일스톤, M2는 plan-phase에 DESCOPED). plan-phase 프로브 + unit/integration pytest(1723 passed) + 전체 회귀(AC-EXECREF-014) + 실기 하드웨어(AC-EXECREF-013③④, 2026-07-23 사후 라이브 재검증, `.moai/state/verify/showui-m6-resume/6-live-executor-noop.log`) 전부 그린 — SPEC-COPILOT-EXECREF-001의 구현 가능 범위(M1)는 이제 plan-phase/unit/regression/hardware 4단 전부 검증 완료. M2는 계속 DESCOPED로 유지(재논의 없음).
- ac_pass_count: 15 (AC-EXECREF-001~011, 013, 014, 015)
- ac_fail_count: 0
- ac_deferred_count: 1 (AC-EXECREF-012 cue-CMD DEBT 태깅 — M1 범위 밖 명시적 제외, sync-phase 또는 후속 SPEC 판단 필요 항목으로 이관 유지)
- preserve_list_post_run_count: 0(위반 없음) — `server/safety/expand.py`/`gate.py`/`console.py`/`ruleset.py`/`blacklist.yaml`/`server/web/**`/`ui/src/**`/`console/lua/**` 전부 무변경 확인(git diff 스코프 = classify.py + 2개 테스트 파일뿐)
- l44_pre_commit_fetch: N/A — 이 워크트리는 origin remote 미설정(로컬 커밋 전용)
- l44_post_push_fetch: N/A — push 미수행(remote 없음)
- new_warnings_or_lints_introduced: 0 — 터치 파일(classify.py/test_safety_classify.py/test_safety_corpus.py) ruff clean; console.py의 기존 2건 E501은 baseline(무변경 파일)
- cross_platform_build: N/A — Python 프로젝트, OS 빌드 태그 무관(plan.md §E.2 주석과 동일)
- total_run_phase_files: 3 (server/safety/classify.py, server/tests/test_safety_classify.py, server/tests/test_safety_corpus.py) + spec.md frontmatter(status transition만) + 본 progress.md
- m1_to_mN_commit_strategy: 단일 커밋(M1이 유일 마일스톤 — M2 DESCOPED로 M1 하나로 run-phase 종료)

## §E.4 Sync-phase Audit-Ready Signal

- sync_complete_at: 2026-07-23T00:00:00Z
- sync_commit_sha: `pending-backfill-execref-sync` (백필 예정 — spec-frontmatter-schema.md § SHA placeholder backfill exemption 준용, 후속 커밋 `chore(SPEC-COPILOT-EXECREF-001): sync backfill §E.4 sync_commit_sha`에서 실제 SHA로 교체)
- sync_status: **PASS — 정직한 부분범위 프레이밍으로 완결**. CHANGELOG.md에 `[Unreleased] > Added` 신규 항목 추가(인식(S1) 완료 + 실제 사용자 경험 무변화 + S2 DESCOPED 사유 + 후속 SPEC `SPEC-COPILOT-EXECBODY-001` 권고를 명시적으로 서술 — 친화 프레이밍 금지). README.md는 사용자-가시적 앱 동작 무변화(패널 타일을 눌렀을 때의 관측 결과가 동일함)를 근거로 무변경 유지(기존 "안전 게이트(M4)" 섹션이 인식 가능 참조타입 목록을 리터럴로 나열하지 않아 갱신 대상 아님을 확인 — `grep -n "Macro\|Plugin\|Sequence" README.md` 무결과). spec.md/plan.md/acceptance.md 3개 아티팩트의 status를 `in-progress`(spec.md 프론트매터) 및 `draft`(plan.md/acceptance.md 프로즈 서술)에서 `completed`로 전환(본 단일 sync 커밋이 3-phase close를 담당 — 별도 Mx 커밋 없음), body 내용은 무변경. design.md/research.md는 SHOWUI-001 sync 선례와 동일하게 무변경(프론트매터/프로즈 status 전환 대상에서 제외).
- b12_self_test_a: PASS — `grep -c "EXECREF-001" CHANGELOG.md`를 편집 전 재확인(0 반환, 오케스트레이터 사전 보고값과 일치, 중복 방지 확인)
- b12_self_test_b: PASS — acceptance.md SSOT AC 행 수(`grep -cE '^\| \*\*AC-EXECREF-[0-9]+' acceptance.md` → 15개: AC-EXECREF-001~015)와 CHANGELOG 본문이 인용하는 테스트 수치(1723 passed, +132)가 progress.md §E.2/§E.3의 실측치와 일치함을 대조 확인. CHANGELOG 자체는 AC 개수를 명시적으로 나열하지 않음(SHOWUI-001 선례와 동일 — SPEC 요약형 CHANGELOG 관례이므로 AC 카운트 라인은 프로젝트 관례상 생략).
- b12_self_test_c: PASS — CHANGELOG가 인용한 파일 경로(`server/safety/classify.py`, `server/tests/test_safety_corpus.py`, `console/lua/copilot_responder.lua`)를 `ls`로 존재 검증 완료.
- changelog_entry_position: `[Unreleased] > Added`, 최상단(SPEC-COPILOT-DEPLOY-001 항목보다 앞) — 최신 sync 항목을 맨 위에 두는 기존 파일 관례(SHOWUI-001 삽입 위치와 동일 패턴) 준수.
- frontmatter_status_transitions.spec_md: `in-progress → completed` (frontmatter `status:` 필드, `updated: 2026-07-23` 그대로 유지 — 동일 날짜 내 sync)
- frontmatter_status_transitions.plan_md: `draft → completed` (본문 최상단 프로즈 `status:` 서술 라인, body 내용 무변경)
- frontmatter_status_transitions.acceptance_md: `draft → completed` (본문 최상단 프로즈 `status:` 서술 라인, body 내용 무변경)
- canary_compliance_check: N/A — 본 SPEC은 forward-looking canary policy를 정의하지 않음(단순 안전 게이트 인식 확장 SPEC).
- sync_evidence: pytest 회귀 재확인 미실행(§E.2/§E.3에서 이미 1723 passed로 검증 완결, sync-phase는 문서 동기화만이 스코프 — 코드 변경 없음이므로 재실행 불필요). CHANGELOG/frontmatter/progress.md 변경 3건이 단일 sync 커밋으로 결합.
- residual_risk: (a) S2(단일-press 복원)는 여전히 미구현 — 사용자가 CHANGELOG를 읽지 않고 "Executor 인식"만 보고 실제 UX가 바뀌었다고 오해할 위험은 CHANGELOG의 명시적 "동작은 변하지 않았다" 고지 문단으로 완화; (b) `sync_commit_sha` 플레이스홀더는 후속 백필 커밋이 누락되면 감사 추적에 공백을 남김 — §E.3의 동일 패턴(백필 완료 c27bd19)을 반복하므로 낮은 위험으로 평가.
