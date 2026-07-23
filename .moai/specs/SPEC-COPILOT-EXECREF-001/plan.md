# SPEC-COPILOT-EXECREF-001 — 구현 계획 (plan)

status: completed (v0.2.0, 2026-07-23) · Tier L · 본 문서는 spec.md의 요구를 마일스톤으로 전개한다. 구현 코드 없음. M2는 2026-07-23 라이브 프로브 결과로 DESCOPED되었다 — 아래 M2 참조.

## §A. 접근 요약 (Context)

- 변경 표면은 **두 곳뿐**이다: `classify.py:33`의 인식 참조 타입 폐쇄 집합(S1), `console.py`의 익스큐터 본문 해석 경로(S2). `expand.py`·`gate.py`·`blacklist.yaml`·`server/web/**`·`ui/src/**`·`console/lua/**`는 무변경(design.md §2).
- 설계의 형태는 "새 방어를 만든다"가 아니라 "**기존 방어 안으로 참조를 밀어 넣는다**"이다. 신규 방어 코드는 0줄이며, 유일한 위험은 연결이 기존 방어를 우회하도록 잘못 구현되는 것이다 — 그래서 AC가 각 보류 사유를 익스큐터에 대해 개별 검증한다(design.md §4.8).
- 본문 조회는 기존 게이트-감사 `state_port` seam(bootstrap.py:162, gate.py:114-121)만 사용한다. 신규 콘솔 경로·신규 OSC 표면 0.

### §A.1 ⚠️ 리뷰 우선순위 (읽는 순서 — 빌드 순서와 다름)

**변경 가능성이 가장 높은 결정을 먼저 읽어야 한다.**

| 순위 | 결정 | 위치 | 상태 |
|---|---|---|---|
| **1위** | **익스큐터 본문 해석 경로** — 어떤 오브젝트-트리 경로가 익스큐터를 분류 가능한 본문으로 해석하는가, 그리고 fetcher의 템플릿 메커니즘 자체가 바뀌어야 하는가 | design.md **§5** (해소됨) | **해소됨 (2026-07-23) — S2 DESCOPED (YAGNI, Q2 결정적 아니오)** |
| 2위 | cue-CMD 갭을 닫지 않고 `@MX:DEBT`로 기록하는 결정 | design.md §4.2, 본 문서 §D | 사용자 결정 확정 |
| 3위 | `Go+ Page <page>.<executor>` 구문을 범위 밖으로 선언 | spec.md REQ-EXECREF-015 | 확정 (fail-closed) |
| 4위 | 코퍼스의 참조 타입 축 동적 순회 리팩터 | design.md §6.1 | 확정, 작업량은 M1의 대부분 |

### §A.2 빌드 순서가 리뷰 순서와 다른 이유 (의도적 편차)

순수 가역성-우선 배치라면 §5의 열린 슬롯(M2)이 M1이어야 한다. 그러나 **출하 안전성**이 반대 방향을 가리킨다:

- **M1(classify 추가) 단독은 무행동 변화다.** 참조가 `None` 대신 `"Executor 201"`이 되지만 본문 경로가 없으므로 `BodyUnavailable` → `_hold`로 귀결된다. 게이트 결과는 오늘과 동일하고 보류 사유 문자열만 바뀐다(design.md §2.1). 따라서 M1은 fail-closed 방향으로 안전하게 단독 출하 가능하다.
- **M2를 먼저 하면** 아무도 참조하지 않는 타입의 본문 경로를 테스트하게 되어 관측 가능한 계약이 약해진다.

**따라서**: 빌드 순서 M1 → M2 → M3, 리뷰 순서 §A.1. 리뷰어는 M2의 §5 슬롯을 먼저 읽는다.

### §A.3 프로브 실행 완료 (2026-07-23) — plan-audit 선행 조건 충족

`.moai/state/verify/showui-m6-resume/probe_executor_body.py`(읽기 전용, 발화 0·쓰기 0)를 2026-07-23 세션 중 콘솔이 온라인 상태가 되어 재실행했다. 결과는 `.moai/state/verify/showui-m6-resume/5-probe-body.log`에 기록되었고 design.md §5에 접어 넣어졌다: Q1 예(로컬-인덱스 단서 있음), Q2 결정적 아니오(4개 샘플 전부 자식 없음), Q3 아니오(기존 갭 재확인). 결과가 부정적이므로 S2는 구현하지 않는다(M2 DESCOPED, 아래).

프로브 없이 §5.3 후보를 임의 채택하는 반-패턴(design.md AP-7)은 발생하지 않았다 — §5.3 후보 자체가 Q2 부정으로 무의미(moot)해졌다.

## §B. 마일스톤 (M1..M3)

### M1 — 참조 인식 + FN 코퍼스 축 확장 (cycle_type=tdd)

- **S1**: `RECOGNIZED_REFERENCE_TYPES`(classify.py:33)에 `"Executor"` 추가. 폐쇄 집합의 의도적 개정.
- `_extract_reference`(classify.py:117-125)가 `Go+ Executor 191` → `"Executor 191"`을 반환함을 검증. 인용된 토큰 무시·다음 토큰이 참조 번호라는 기존 의미론 그대로.
- **무행동 변화 검증**: M1 단독 상태에서 `Go+ Executor N`은 여전히 보류되며 `hold=True, risky=False`가 유지된다 — 보류 사유 문자열만 변경(AC-EXECREF-008).
- **코퍼스 리팩터 (작업량의 대부분)**: `test_safety_corpus.py`의 `_invoking_commands()`(86-92)와 `_SCENARIOS`(95-110)가 참조 타입을 하드코딩(`Macro`)하고 있으므로, `classify.RECOGNIZED_REFERENCE_TYPES`를 import하여 **참조 타입을 parametrize 축으로** 승격하고 본문 사전을 타입별로 생성한다(design.md §6.1). 동사 축은 축소 금지(REQ-MVP-017 "ALL invoking_verbs entries" 계약).
- 파일: `server/safety/classify.py`, `server/tests/test_safety_classify.py`, `server/tests/test_safety_corpus.py`.

### M2 — 익스큐터 본문 해석 경로 — **DESCOPED (2026-07-23)**

**M2는 착수되지 않고 이연되었다.** 2026-07-23 라이브 프로브(`.moai/state/verify/showui-m6-resume/5-probe-body.log`) 결과 Q2(익스큐터 노드에 자식이 있는가)가 샘플 4개(익스큐터 1, 5, 11, 91) 전부에서 결정적으로 아니오로 확인되었다 — `console/lua/copilot_responder.lua`의 응답기가 범용 `handle:Children()`만 호출하고 익스큐터 전용 확장이 없기 때문(design.md §5.1). 이는 아키텍처적 사실이며, S2를 어떻게 구현하든(어느 페이지-성분 해석 후보를 택하든, design.md §5.3) 결과는 `children: []` → `BodyUnavailable` → `_hold`로 동일하다.

**DESCOPE 근거**: S2 구현은 `server/safety/**` 범위 안에서 행동 변화를 만들 수 없으면서, 콘솔 발화 번호→로컬 인덱스 역매핑이라는 새로운 미검증(페이지 1만 확인됨) out-of-band 주소 가정을 안전-critical 코드에 추가하게 된다 — REQ-EXECREF-007이 이름-파싱을 기각한 것과 동일한 부류의 위험(design.md §5.6). 순수 YAGNI 판단으로 M2를 이연한다.

**원래 M2가 다루려던 요구사항**(REQ-EXECREF-004/005/006) 및 M2에 의존하던 관측 결과 요구사항(REQ-EXECREF-013)은 spec.md §B.2/§B.5에서 각각 **DEFERRED**로 표기되었다 — 철회가 아니라 유효한 미래 요구사항이다. 실제 봉쇄에는 응답기 Lua 확장이 필요하며 본 SPEC 범위 밖이므로, 후속 SPEC `SPEC-COPILOT-EXECBODY-001`로 권고한다(research.md §5.3).

**사용자 결정 (AskUserQuestion, 2026-07-23)**: S1만 출하, S2 완전 이연. 대안(응답기 확장 병합)은 후속 SPEC 검토로 이관.

### M3 — 전체 그린 + 라이브 검증 (S1 no-op 검증으로 갱신, 2026-07-23)

- pytest 전체 + vitest 전체. 기준선(HEAD `0576553`: 1591 passed + 1 환경적 failed) 대비 **신규 실패 0건**.
- `test_architecture.py` 그린 + `server/safety/**` OSC import 경계 grep 무변경.
- **라이브 AC(AC-EXECREF-013)**: M2가 DESCOPED됨에 따라 ASSUMPTION-8/9 비준은 이미 2026-07-23 프로브로 완료되었다(progress.md §E.2, design.md §5.5). 남은 라이브 검증은 S1의 no-op 성질 확인이다 — 익스큐터 참조가 `"Executor N"`으로 인식되지만 여전히 보류됨을 실측한다.
- **라이브 체크(갱신됨 — 마찰 제거가 아니라 no-op을 검증)**: 패널 익스큐터 타일 1회 누름 → **여전히 승인 카드 1장 + `SaveShow` 1회**(변경 없음), 단 보류 사유 문자열이 `"unverifiable reference: no recognizable target object"`에서 `"no body path mapping for 'Executor N'"`(또는 등가 문구)로 바뀌었음을 확인. **이는 목표 미달의 정직한 기록이다** — friction-elimination을 증명하려는 것이 아니라, S1이 안전하게 no-op임을 증명하는 것이다(design.md AP-8).

## §C. 기술 제약

1. **신규 런타임 의존성 0.** 기존 stdlib + 기존 스택만.
2. **@MX:ANCHOR 경계 (위반 불가)**:
   - `server/safety/gate.py:260-264` — 스크리닝 경로는 정확히 하나. 패널 전용 룰셋·expansion 스킵 지름길은 이름만 다른 제2 스크리닝(design.md AP-1).
   - `server/safety/classify.py:158-161` — 분류 의미론은 하나. 익스큐터 전용 분기를 `classify_command` 밖에 두지 않는다(AP-2).
3. **fail-closed는 협상 대상이 아니다.** 완화 범위는 "해석 가능한 익스큐터가 해석된다"이며, "해석 불가능한 익스큐터가 통과한다"가 결코 아니다. 최악 결과는 "마찰이 줄지 않음"이지 "미검증 커맨드 통과"가 아니다(design.md §5.4).
4. **폐쇄 집합 규율**: `RECOGNIZED_REFERENCE_TYPES` 개정은 `blacklist.yaml` 개정과 동일한 무게. 코퍼스는 하드코딩 추가가 아니라 집합 순회로 확장.
5. **범위 경계**: `console/lua/**` 무변경, 와이어 프로토콜 무변경, `server/web/**`·`ui/src/**` 무변경. cue-CMD 갭은 기록만.
6. **측정된 기준선 (run-phase 오인 방지)**: HEAD `0576553`에서 **1591 passed + 1 failed**. 유일한 실패는 `server/tests/test_web_reply_discovery.py::TestDiscovery::test_every_candidate_socket_is_released`이며 **환경적**이다 — 구동 중인 onPC가 UDP 9005를 점유하고 그 포트가 해당 테스트의 후보 집합에 있다. **기존 실패, 본 SPEC과 무관.** 자신이 유발한 회귀로 오인하지 말 것.

## §D. @MX 태그 대상

| 태그 | 대상 | 내용 |
|---|---|---|
| `@MX:DEBT` | `server/safety/console.py` `StateBodyFetcher.fetch_body` 근처 | 본문 라인이 자식의 **이름**이며 큐의 CMD(Command) 프로퍼티가 아니라는 사실. 응답기가 `{name, class, i}`만 전송한다(`copilot_responder.lua:456`). |
| `@MX:CEILING` | 위 DEBT의 하위 라인 | 큐 **이름**만 스크리닝된다 — CMD 프로퍼티에 담긴 실행 커맨드는 게이트에 보이지 않는다. 이는 **모든** 참조 타입에 공통이며 Executor 추가가 만든 것이 아니다. |
| `@MX:UPGRADE` | 위 DEBT의 하위 라인 | 응답기가 자식 페이로드에 CMD/Command 프로퍼티를 전송하게 되면 본문 소스를 이름에서 커맨드로 교체 — 후속 SPEC 권고 `SPEC-COPILOT-CUECMD-001`(research.md §5.3). |
| `@MX:NOTE` | `server/safety/classify.py:33` | `Executor` 추가가 폐쇄 집합의 **의도적 개정**이며 false-negative 검토가 design.md §4에 있음을 표시. |
| `@MX:NOTE` | `server/safety/classify.py:33` (추가 라인) | 인식만으로는 행동 변화가 없음 — 본문 해석 경로(S2)가 2026-07-23 프로브 결과 DESCOPED되어(design.md §5) 익스큐터 참조는 여전히 보류된다. 상세: design.md §5.2/§5.4. |

`@MX:ANCHOR`는 신규 추가하지 않는다 — 기존 두 앵커(gate.py:260-264, classify.py:158-161)를 소비만 한다.

## §E. 테스트 스캐폴딩 계획 (기존 관례 준수)

- **순수 함수 우선**: `classify` / `expand`는 이미 순수 모듈이며 fetcher는 주입된다(`DictBodyFetcher`, test_safety_expand.py). 익스큐터 테스트도 인메모리 fetcher로 결정론 유지 — 스크리닝 경로에 OSC 0.
- **코퍼스 축 확장**: `classify.RECOGNIZED_REFERENCE_TYPES`를 import해 parametrize. 케이스 수가 타입 수만큼 곱해짐(현재 10 동사 × 4 시나리오 = 40 → 4 타입이면 160) — 실행 시간 확인 필요.
- **fail-closed 3종 개별 테스트** (병합 금지, design.md §6.2).
- **관측 형상 assert**: `console.executed`(FakeConsole) 기준으로 `["Go+ Executor N"]` 정확 일치, `"SaveShow"` 부재.
- **run-phase 자기 검증 커맨드(예상)**:
  - `.venv/bin/python -m pytest server/tests/test_safety_classify.py server/tests/test_safety_expand.py server/tests/test_safety_corpus.py server/tests/test_safety_ruleset.py server/tests/test_safety_console.py server/tests/test_safety_gate.py -q`
  - `.venv/bin/python -m pytest server/tests/test_web_panel_execute.py server/tests/test_architecture.py -q`
  - `.venv/bin/python -m pytest -q` (전체, 기준선 대비 신규 실패 0건)
  - `grep -rn "bridge.osc\|from server.bridge" server/safety/` (기준선 대비 무변경)
  - `grep -rn "@MX:DEBT" -A 2 server/safety/console.py` (CEILING/UPGRADE 하위 라인 동반 확인)

## §F. 결정 기록 (재질의 금지)

| 결정 | 내용 | 반영 위치 |
|---|---|---|
| 접근 채택 | 게이트측 Executor 인식. 기각 (a) 승인-매-누름 수용 + design.md 개정 — 패널의 핵심 가치 상실. 기각 (b) 시퀀스 참조 치환 — 등가성 미검증 + 익스큐터 rename 취약 | research.md §2 |
| 범위 | `server/safety/**` 한정. 응답기 Lua·와이어 프로토콜·UI 무변경 | spec.md §D |
| cue-CMD 갭 | **기록하되 닫지 않음.** design.md §4.2가 개선이 아닌 **패리티**를 증명하고, 노출 확대는 명시. `@MX:DEBT`(§D) + 후속 SPEC 권고 | design.md §4.2, research.md §5.3 |
| `Go+ Page N.M` | 범위 밖. 계속 `None` → 보류 = fail-closed(안전). 침묵 생략 대신 REQ로 명시 | spec.md REQ-EXECREF-015 |
| 마일스톤 순서 | 빌드 M1(classify)→M2(본문)→M3(라이브). 순수 가역성-우선(M2 먼저)에서 **의도적으로 편차** — M1 단독이 무행동 변화라 안전 출하 가능하기 때문. 리뷰 순서는 §A.1로 분리 | 본 문서 §A.2 |
| frontmatter 참조 | `related_specs`(비차단) — MVP-001/SHOWUI-001 모두 `completed`가 아니므로 `depends_on` pre-flight 차단 회피 | spec.md frontmatter·§C |
| ASSUMPTION 번호 | ASSUMPTION-8(익스큐터 노드 경로) / ASSUMPTION-9(익스큐터 본문 = 할당 시퀀스 큐). 비준 기록은 progress.md §E.2 | design.md §5.5 |
| PROTOCOL.md §6 등재 | **범위 밖 — 선택 항목.** 라이브 확정 후 ASSUMPTION-8/9를 `console/lua/PROTOCOL.md` §6에 등재하는 것은 `server/safety/**` 밖이므로 sync-phase에 **별도 승인**을 받아 수행하거나 생략한다. 승인 없이 수행하지 않는다 | design.md §5.5 |
| M2 DESCOPE | 2026-07-23 라이브 프로브로 Q2 결정적 아니오 확인 → S2 구현은 행동 변화 없이 새 미검증 주소 가정만 추가함. YAGNI 판단으로 M2 이연, S1만 출하. 후속 SPEC `SPEC-COPILOT-EXECBODY-001` 권고(미생성) | design.md §5, §5.6, plan.md M2, research.md §5.3, 증거: `.moai/state/verify/showui-m6-resume/5-probe-body.log` |
| AC 표 형식 유지 (MP-2, 오케스트레이터 결정) | acceptance.md §C의 AC 표는 "pytest 검증 레시피" 스타일(리터럴 GEARS "shall" 문장이 아님)을 그대로 **유지한다** — 재포맷하지 않는다. 근거: 완결·출하된 자매 SPEC SPEC-COPILOT-SHOWUI-001의 acceptance.md가 동일한 관례를 전체 AC 표에 걸쳐 사용하고 있으며, plan-auditor가 iteration 1과 iteration 2 검토 양쪽에서 이 일치를 독립적으로 재확인했다. 17개 AC 행을 인위적인 "shall" 문구로 재포맷하는 것은 이미 출하된 선례에는 적용되지 않았던 더 엄격한 루브릭 해석을 충족시키기 위함일 뿐, 검증 가능성에서 실질적 이득 없이 확립된 프로젝트 관례에서 이탈하는 것이다. acceptance.md의 AC 행 형식 자체는 변경하지 않는다 | `.moai/reports/plan-audit/SPEC-COPILOT-EXECREF-001-review-1.md`, `.moai/reports/plan-audit/SPEC-COPILOT-EXECREF-001-review-2.md` (증거 추적) |

## §G. Phase 4 Mode Selection — 사전 평가 (오케스트레이터 확정용 권고)

> 구속력 있는 기록은 `progress.md` §F이며 오케스트레이터 소유다(첫 run-phase `Agent()` 스폰 전 작성). 본 절은 plan-phase 권고이며 오케스트레이터가 확정·기각한다.

### 입력 파라미터

- **tier**: L (6-artifact 세트)
- **scope (file count)**: 8~10 파일 (M1~M3 누계 — 구현 2, 테스트 6~8)
- **domain count**: **1** (Python / `server/safety/**` 단일 도메인)
- **file language mix**: Python 100%. 코딩 중심(안전 로직 수정 + 테스트 리팩터)
- **concurrency benefit**: **LOW** — M1의 참조 인식이 M2의 본문 해석 의미를 규정하는 순차 의존. 게다가 M2는 프로브 결과에 게이트되어 있음
- **Agent Teams prereqs**: 해당 없음 (Mode 3 RETIRED)

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 단일 라인 변경이 아님 — 안전 경계 완화 + 코퍼스 리팩터 + fail-closed 테스트 8종 |
| 2 | background | 미선택 | 쓰기 작업(Write/Edit) 포함 |
| 3 | agent-team | 미선택 | RETIRED (tombstone) |
| 4 | parallel | 미선택 | 도메인 1개(<3), 파일 8~10개(<10 경계), 코딩 중심 — Anthropic coding-task parallelism caveat상 순차가 안전 |
| 5 | **sub-agent** | **선택** | 단일 도메인 + 순차 의존 체인 + 코딩 중심. Tier L이므로 Section A-E 전체 위임 템플릿 적용 |
| 6 | workflow | 미선택 | ~30 파일 미만, 단일 균일 변환 규칙 아님(안전 의미론 판단 포함) |

### Decision: sub-agent

### 정당화

단일 도메인(`server/safety/**`)이고 M1의 참조 인식 결정이 M2의 본문 해석 계약을 규정하는 순차 의존 체인이므로 병렬화 이득이 없다. Anthropic의 coding-task parallelism caveat상 코딩 중심 작업의 안전한 기본값은 순차 sub-agent이며, 특히 안전 게이트 완화 작업은 마일스톤 간 검증이 누적되어야 한다. M2는 프로브 결과에 게이트되어 있어 병렬 진입 자체가 불가능하다. Tier L이므로 `manager-develop` 위임에는 Section A-E 전체 템플릿을 적용한다.

### 경계 사례

파일 수 8~10은 Mode 4의 `≥10 files` 임계 경계에 있다. tie-breaker 규칙("임계 ±1에서는 단순한 모드로")과 도메인 수 1(<3)이 모두 Mode 5를 가리키므로 경계 모호성 없이 해소된다.
