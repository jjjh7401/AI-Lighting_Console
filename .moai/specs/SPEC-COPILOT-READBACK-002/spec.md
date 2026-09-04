---
id: SPEC-COPILOT-READBACK-002
title: "되읽기 채널의 신뢰 — 응답기 버전 게이트와 타입명 번역"
version: "0.1.1"
status: completed
created: 2026-09-03
updated: 2026-09-04
author: orchestrator (plan session 317272ed)
priority: P1
phase: "v1.7.0 target"
module: "server/safety/, server/web/, ui/src/protocol.ts, server/prechk/, server/vwx/diff.py, server/paperwork/"
lifecycle: spec-anchored
tags: "responder-version-gate, fixture-type-translation, handle-name-translation, query-budget, zero-console-write, evidence-discipline"
tier: M
related_specs: [SPEC-COPILOT-READBACK-001, SPEC-COPILOT-PARITY-001, SPEC-COPILOT-RECVOBS-001, SPEC-COPILOT-VWX-001]
---

# SPEC-COPILOT-READBACK-002 — 되읽기 채널의 신뢰

> **이 SPEC 이 닫는 구멍**: SPEC-COPILOT-READBACK-001 이 되읽기 채널에 **값을 더한다면**, 이 SPEC 은 그 채널이 **믿을 만한지**를 다룬다. 두 자리가 비어 있다.
>
> **첫째, 채널이 자기 버전을 모른다.** `ConsoleLink.ping`(`server/safety/console.py:297-307`, 2026-09-03 실측 확인)은 회신에 실려 오는 `version` 을 **매 하트비트마다 버린다** — 디코드된 payload 를 통째로 버리고 `bool` 만 반환한다. 이 저장소에는 **live-1.6.1 / main-1.6.2 전례**가 이미 기록돼 있다(`server/tests/test_overlap_preserve.py:225-232`) — 즉 「main 에 있다」는 「콘솔에 있다」가 아닌데, 그것을 구별할 수 있는 값이 도착해서 버려지고 있었다.
>
> **둘째, 채널이 이름을 핸들로 답한다.** `read_inventory(..., type_names=)` 키워드 인자는 **이미 존재하고 이미 한 곳에서 옳게 쓰인다**(`server/orchestrator/tools.py:6356`). 나머지 여섯 호출 지점이 그것을 빠뜨려(`:3014, :3206, :3397, :4039, :4433, :4624` — 2026-09-03 grep 실측, 총 7건 중 6건) VWX diff 는 타입별로 **전부 0** 을 세고 패치 시트는 `FixtureType 12` 라는 핸들을 그대로 인쇄한다.
>
> **결함은 기계가 아니라 배관이다.** 번역기(`translate_fixture_type` `server/prechk/inventory.py:147-180`)도, 버전을 싣는 응답기도 이미 옳게 동작한다. 고치는 것은 **도착한 값을 버리는 자리**와 **이미 있는 인자를 안 넘기는 자리** 둘이다.
>
> **콘솔 쓰기 0.** 이 SPEC 은 순수 서버·UI 작업이며 콘솔에 어떤 명령도 쓰지 않는다(REQ-READBACK2-013). 필요한 값은 이미 매 하트비트에 도착하고 있고, 타입명 표는 읽기 조회 하나로 얻는다.

## HISTORY

| 일자 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-03 | 0.1.0 | 최초 초안. SPEC-COPILOT-READBACK-001 v0.1.1 의 **분할로 신설**됐다. plan-audit iteration 2(PASS 0.925)가 D11 로 Tier M 예산(REQ 16 / AC 16) 2배 초과를 지적했고(REQ 32 / AC 33), 감독이 2026-09-03 에 두 Tier M SPEC 으로 분할을 결정했다. 본 SPEC 은 **R3(런타임 응답기 버전 게이트) + R4(FixtureType 핸들→이름 번역)** 를 이관받았다. 옛 REQ-015~027 이 본 SPEC 의 REQ-001~012 로, 옛 AC-015~027a/b 가 AC-001~013a/b 로 재번호됐다. 조사 근거는 `../SPEC-COPILOT-READBACK-001/research.md` §R3·§R4(기준 `origin/main adae0ac`)이며 본 디렉터리의 `research.md` 는 그 포인터다. | `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-2.md` §D11-D14 · 감독 결정 2026-09-03 |
| 2026-09-03 | 0.1.1 | plan-audit iteration 1(FAIL 0.75, must-pass 7/7)의 결함 6건을 반영. **D1**: REQ-READBACK2-012 의 재사용 의무를 걷어냈다 — `TypeModeRead`·`WalkOutcome` 어느 쪽도 (슬롯, 이름) 쌍을 호출자에게 반환하지 않아, 기존 루트 판독의 재사용은 `server/prechk/**` 변경 없이는 불가능하고 그 변경은 REQ-READBACK2-010 이 금지한다. 재사용은 **허용이지 의무가 아니며**, 상한은 지점당 1회로 남는다. AC-013b 는 「증가 0」 요구에서 **상한 초과 부정 대조군**(N+2 → FAIL)으로 바뀌었다. **D2**: AC-007 의 계기를 줄 경계에 의존하는 grep 에서 `ast` 호출 계수로 바꿨다(`pyproject.toml:59` `line-length = 100` 때문에 수리 후 다섯 자리가 여러 줄로 쪼개진다). **D3**: AC-014 의 「세션 명령 로그」에 실제 경로를 적었다. **D4**: AC-013a 의 기준 N 보관처를 `progress.md` §E.2 로 지정. **D5·D6**: 앵커 4건 정정(`gate.py:419→420` · `inventory.py:147-181→147-180` · `protocol.ts:1192-1205→1190-1207` · `test_overlap_preserve.py:227-231→227-230`). REQ 14 / AC 16 불변. | `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-002-review-1.md` D1-D6 · 감독 결정 2026-09-03 · 실측 HEAD `adae0ac` |

---

## A. 배경

### A.1 지금 무엇이 이미 건강한가 (건드리지 않는다)

| 절 | 상태 | 근거 |
|---|---|---|
| 응답기가 버전을 싣는 것 | ✅ 건강 | `pong` 회신에 `version` 이 실려 도착한다. 버리는 쪽은 서버다(`console.py:297-307`) |
| 타입명 번역 기계 | ✅ 존재 | `translate_fixture_type`(`server/prechk/inventory.py:147-180`) + `read_inventory(type_names=)` kwarg(`:529-534`) |
| 옳게 구현된 호출 지점 한 곳 | ✅ 참조 구현 | `tools.py:6326` `types_root` → `:6352` `read_fixture_type_names` → `:6356` `read_inventory(..., type_names=)` |
| 조회 예산 가드 | ✅ 비준됨 | `_name_handle_types` 문서 문면(`inventory.py:469-473`)이 「이 저장소는 query-budget guard 를 조정 대상이 아니라 비준된 것으로 취급한다」고 명시 |
| 건강 상태 배너 계층 | ✅ 건강 | `SafetyGate._check_health`(`server/safety/gate.py:415-437`) → `ScreenDecision` → `ui/src/protocol.ts:1190-1207` 라벨(`HEALTH_LABELS` `:1190-1194`)/가이던스(`HEALTH_GUIDANCE` `:1203-1207`) |

### A.2 버전 게이트는 오프라인 판정보다 **엄격히 하류**다

`_check_health`(`gate.py:415-437`)는 오늘 두 상태만 안다: `CONSOLE_OFFLINE` → `blocked_console_offline`, 그 밖의 비정상 → `blocked_responder_degraded`. 버전 불일치는 **성공한 ping 이후에만** 판정할 수 있으므로, 오프라인 판정이 이미 성립한 상황에서 버전 사유가 그것을 대체해 표시되면 운영자는 **틀린 행동**을 한다 — 콘솔이 꺼져 있는데 재임포트를 시도하게 된다.

같은 이유로 「기대보다 낮은 버전」과 「인식할 수 없는 버전」도 갈라야 한다. 전자는 재임포트고 후자는 조사다.

### A.3 조회 예산도 예산이다 — 그리고 그 가드는 이미 비준돼 있다

R4 의 수리는 여섯 호출 지점에 `type_names=` 를 넘기는 것인데, 그 인자를 만들려면 `read_fixture_type_names(state_port, root=types_root)` 를 읽어야 한다. 그 읽기는 **`query_state` 정확히 1회**다(`server/prechk/mode_read.py:141` — *"Query count is 1 - the type listing, nothing per type."*).

`_name_handle_types` 의 문서 문면(`server/prechk/inventory.py:469-473`)은 이 설계를 **「번역이 필요한 호출자는 이미 자기 이유로 fixture-type 트리를 걷고 있다」**는 전제 위에 세운다. 그러므로 여섯 호출 지점이 그 전제를 만족하는지는 **가정이 아니라 측정 대상**이며(plan.md §B B5 에 실측표: 예 3 / 아니오 3), 늘어나는 조회는 REQ-READBACK2-012 가 상한으로 묶는다.

그리고 그 전제를 만족하는 지점에서도 **「호출자가 조회를 냈다」는 「호출자가 페이로드를 쥐고 있다」가 아니다.** `TypeModeRead`(`server/prechk/mode_read.py`)는 `attempted`/`type_found`/`modes`/`detail` 만 돌려주고, `WalkOutcome`(`server/prechk/footprint.py`)은 `queried_paths` 로 **경로 문자열**만 돌려준다 — 둘 다 함수 안에서 루트를 읽지만 (슬롯, 이름) 쌍은 호출자에게 반환하지 않는다. 그 쌍을 흘리려면 `server/prechk/**` 를 고쳐야 하는데 REQ-READBACK2-010 이 그것을 금지한다. 따라서 비준 문면의 전제는 **조회 계수의 근거로는 참이지만 재사용 가능성의 근거로는 참이 아니다**. REQ-READBACK2-012 는 이 사실 위에서 재사용을 의무가 아니라 허용으로 두고 상한만 건다.

### A.4 핸들 형태 가정은 완전하지 않고, 그 사실은 열어 둔다

`HANDLE_TEXT = re.compile(r"^FixtureType (\d+)$")`(`server/prechk/inventory.py:111`)이 번역의 방아쇠다. 여섯 소비자를 고쳐도 **미관측 제3 형태는 표식 없이 통과**한다 — 코드 자신이 그렇게 적어 뒀다(`inventory.py:479-485`: *"a value in some THIRD form nobody has seen is passed through as if it were a name, unmarked"*). 본 SPEC 은 그 구멍을 **메우지 않고 명시**한다.

---

## B. 요구사항 (GEARS)

> REQ 번호는 **001-014 연속**이다. 절 구분은 번호 공백이 아니라 §B.1~§B.3 표제가 한다.
> 각 REQ 를 검증하는 AC 는 §C 표의 「AC」 열과 `acceptance.md` §H 커버리지 표가 정본이다.

### B.1 R3 — 런타임 응답기 버전 게이트

- **REQ-READBACK2-001** [Ubiquitous] — the `ConsoleLink` **shall** `pong` 회신에 실려 온 `version` 을 폐기하지 않고 링크 속성으로 보존한다. 현재 `server/safety/console.py:297-307` 은 디코드된 payload 를 버리고 `bool` 만 반환한다(2026-09-03 실측 확인). `ConsolePort.ping()` 시그니처는 **넓히지 않는다** — 모든 `FakeConsole` 로 파급되기 때문이다.
- **REQ-READBACK2-002** [Ubiquitous] — the 안전 모듈(`server/safety/`) **shall** 기대 응답기 버전을 **단일 상수**로 정의하고 `console/lua/copilot_responder.lua:82`(`VERSION = "1.6.3"`, 실측 확인)에 고정한다. 오늘 기대 버전은 테스트 리터럴로만 존재하며 단일 출처가 없다.
- **REQ-READBACK2-003** [Event-driven] — **When** 하트비트가 성공했고 보고된 버전이 기대 상수와 다르면, the 안전 게이트 **shall** `SafetyGate._check_health`(`server/safety/gate.py:415-437`)의 **분기로서** 자체 status 문자열과 한국어 라벨(「응답기 버전 불일치 — 재임포트 필요」)을 실은 차단 판정을 반환한다. 분기를 그 자리에 두는 이유는 감사 기록(`_audit.log_blocked` `:429`)과 `ScreenDecision` 형상과 전송 시점 재검사(`:546-557`)를 **그대로 상속**하기 위함이다.
- **REQ-READBACK2-004** [Ubiquitous] — the 버전 게이트 **shall** 「기대보다 낮은 버전」과 「인식할 수 없는 버전」을 **구별해 보고**한다. 두 경우의 운영자 행동이 다르다 — 전자는 재임포트, 후자는 조사다.
- **REQ-READBACK2-005** [Unwanted] — the 버전 게이트 **shall not** 콘솔 오프라인 차단을 가린다. 게이트는 **성공한 ping 이후에만** 발동하므로 오프라인 판정보다 엄격히 하류이며, `blocked_console_offline`(리터럴은 `gate.py:420`, 그 분기 조건은 `:419`)이 이미 성립한 상황에서 버전 사유가 그것을 대체해 표시되어서는 안 된다.

### B.2 R4 — FixtureType 핸들→이름 번역

- **REQ-READBACK2-006** [Ubiquitous] — the `read_inventory` 호출 지점 **shall** 타입명 표를 넘긴다. 2026-09-03 grep 실측 기준 일곱 호출 중 여섯(`server/orchestrator/tools.py:3014, 3206, 3397, 4039, 4433, 4624`)이 `type_names=` 를 빠뜨리고 하나(`:6356`)만 옳다. **여섯을 한 집합으로 감사하고 한 집합으로 고친다** — 하나만 고치면 나머지가 같은 결함으로 남아 있다는 사실이 보이지 않게 된다.
- **REQ-READBACK2-007** [Ubiquitous] — the `build_patch_sheet`(`server/paperwork/data.py:82-143`) **shall** `type_names` 매개변수를 받아 `read_inventory`(`:102`)로 전달하며, 표 자체를 **스스로 읽지 않는다.** 근거: 비준된 조회 예산 규칙 — `_name_handle_types` 는 매핑이 아니라 **읽은 결과**를 받고 자체 조회를 수행하지 않는다(`server/prechk/inventory.py:469-473`). 읽기는 호출자(`server/web/paperwork_api.py`, `server/paperwork/bundle.py`, tools.py 시트 툴)로 밀려난다.
- **REQ-READBACK2-008** [Ubiquitous] — the 패치 시트 렌더러(`server/paperwork/render.py:87`, 실측 확인: `escape(row.fixture_type or '')`) **shall** `fixture_type_untranslated` 를 가시적으로 표면화한다. 판독 경계에서 산 정직성이 인쇄 경계에서 버려지면 시트를 읽는 사람은 번역 실패와 번역 성공을 구별할 수 없다.
- **REQ-READBACK2-009** [Event-driven] — **When** 패치된 리그에 대해 `precheck_vectorworks_diff` 가 실행되면, the VWX diff **shall** 타입별 실제 콘솔 대수를 보고한다. 오늘 `server/vwx/diff.py:179-185` 는 `fuzzy_type_equal`(정의는 `server/vwx/rig.py:58`, 사용은 `diff.py:180`)로 핸들 문자열과 도면 타입명을 비교해 `console_count` 를 **모든 타입에서 0** 으로 만들고, 그 0 이 `QuantityMismatchEntry`(`:188-192`)로 흘러 주소별 `found` 검사(`:150`)까지 무력화한다.
- **REQ-READBACK2-010** [Unwanted] — the `server/prechk/**` · `server/vwx/**` 번역 기계 **shall not** 본 SPEC 에서 변경된다. 결함은 번역기가 아니라 **호출자가 인자를 안 넘기는 것**이며, 수리 범위는 호출 지점과 렌더 경계에 한정된다.
- **REQ-READBACK2-011** [Unwanted] — the 조사 노트 **shall not** 핸들 형태 가정(`^FixtureType (\d+)$`, `server/prechk/inventory.py:111`)이 완전하다고 주장한다. 여섯 소비자를 고쳐도 **미관측 제3 형태는 표식 없이 통과**한다(`server/prechk/inventory.py:479-485`). 그 구멍은 열린 채로 남고 완료 보고의 미검증 절에 명시된다.
- **REQ-READBACK2-012** [Ubiquitous] — the 수리된 호출 지점 **shall** 호출 지점당 **최대 1회**의 추가 `query_state` 만 소비한다. 그 1회는 `read_fixture_type_names`(`server/prechk/mode_read.py:138-141`, 문서 문면 「Query count is 1」)의 타입 목록 조회다. **이미 자기 이유로 fixture-type 루트를 읽는 지점에서 그 판독을 재사용하는 것은 허용이며 의무가 아니다** — `TypeModeRead` 와 `WalkOutcome` 어느 쪽도 (슬롯, 이름) 쌍을 호출자에게 반환하지 않으므로(§A.3), 그 재사용은 `server/prechk/**` 를 고쳐야만 가능하고 REQ-READBACK2-010 이 그것을 금지한다. 재사용은 **`server/prechk/**` 변경 없이 가능한 자리에서만** 수행한다 — 구체적으로 한 핸들러 호출 안에서 이미 만들어 둔 이름 표가 스코프에 있는 자리(`tools.py:4433`·`:4624` 는 같은 `patch_fixtures` 호출이다)에서는 그 표를 나눠 쓰고 두 번째 목록 조회를 발행하지 않는다. 여섯 지점의 조회 증가분은 지점별로, 그리고 재사용하지 않은 자리는 그 사유와 함께 완료 보고에 계상된다.

### B.3 횡단 — 쓰기 예산과 증거

- **REQ-READBACK2-013** [Unwanted] — the 본 SPEC 의 구현자 **shall not** 콘솔에 어떤 명령도 쓰지 않는다. 본 SPEC 의 콘솔 쓰기 총계는 **0** 이다 — R3 이 필요로 하는 버전 값은 이미 매 하트비트에 도착하고 있고, R4 가 필요로 하는 타입명 표는 읽기 조회 하나로 얻는다. 응답기 재임포트를 포함한 모든 쓰기는 SPEC-COPILOT-READBACK-001 의 예산이며 본 SPEC 은 그 예산을 소비하지 않는다.
- **REQ-READBACK2-014** [Ubiquitous] — the 완료 보고 작성자 **shall** 주장을 `.claude/rules/moai/core/verification-claim-integrity.md` 의 5절 형식(주장·증거·기준 귀속·미검증·잔여 위험)으로 싣고, 미검증 절에 REQ-READBACK2-011(제3 핸들 형태)을 명시하며, 호출 지점별 조회 증가분(REQ-READBACK2-012)을 계상하고, 증거 절 어디에서도 `exec: ok` 를 효과의 증거로 인용하지 않는다. **미검증 절이 비어 있는 보고는 「아무것도 안 잰 것이 없다」는 강한 주장**이며 그 자체가 참이어야 한다.

---

## C. 성공 기준

| # | 기준 | 판정 수단 | AC |
|---|---|---|---|
| C1 | 도착한 버전이 버려지지 않고 소스에 고정된 기대값과 대조된다 | 오프라인 게이트 테스트 | AC-READBACK2-001 · 002 |
| C2 | 기대와 다른 응답기 버전이 차단으로 이어지고, 오프라인을 가리지 않으며, 낮은 버전과 미인식이 갈린다 | 오프라인 부정 대조군 3종 | AC-READBACK2-003 · 004 · 005 · 006 |
| C3 | 일곱 호출자가 전수 정합하고 패치된 리그의 VWX diff 가 타입별 실제 대수를 답한다 | `ast` 호출 계수 + 오프라인 diff 테스트 | AC-READBACK2-007 · 008 |
| C4 | 시트가 이름을 인쇄하고 번역 실패가 숨지 않으며 시트가 스스로 읽지 않는다 | 오프라인 시트 테스트 + 조회 계수 포트 | AC-READBACK2-009 · 010 · 011 |
| C5 | 번역 기계가 무변경이다 | diff 검사 | AC-READBACK2-012 |
| C6 | 수리의 조회 증가분이 호출 지점당 1회를 넘지 않고, 한 핸들러의 두 자리가 목록 조회를 두 번 내지 않는다 | 조회를 세는 가짜 포트 (양성 N+1 / 상한 초과 부정 대조군 N+2 → FAIL) | AC-READBACK2-013a · 013b |
| C7 | 콘솔 쓰기 총계가 0이다 | `FakeConsole.executed` (오프라인) + `server/audit_logs/audit-*.jsonl` 의 `kind:"command"` 행 (라이브 세션) | AC-READBACK2-014 |
| C8 | 완료 보고가 5절 형식을 갖추고 미검증 절이 비어 있지 않다 | 보고서 검사 | AC-READBACK2-015 |

세부 Given/When/Then 과 REQ↔AC 양방향 대응은 `acceptance.md`(§H 커버리지 표)가 정본이다.

---

## D. 범위 밖 (Out of Scope)

### Out of Scope — 응답기 테이블 직렬화 (R1)

- `M.safe_property` 의 테이블 분기, `M.json_encode` 의 깊이 상한·순환 탐지·구조적 절단, 1.6.4 개정과 `console/lua/` 잠금 규약은 **SPEC-COPILOT-READBACK-001** 이 소유한다.
- 본 SPEC 은 `console/lua/` 아래의 어떤 파일도 편집하지 않는다. `copilot_responder.lua:82` 의 `VERSION` 리터럴은 **읽기만** 한다(REQ-READBACK2-002 의 고정 대상).
- 따라서 본 SPEC 은 1.6.4 배포를 **기다리지 않는다** — 버전 게이트는 기대 상수가 무엇이든 동작하며, 001 이 상수를 `1.6.4` 로 올릴 때 그 한 줄만 따라간다.

### Out of Scope — 프리셋 값 되읽기 측정 (R2)

- 프리셋 객체 전수 조사 스윕, `unverified: ["value_match"]` 의 제거 조건, 팔레트 스와치와 콘솔 판독값의 구별은 **SPEC-COPILOT-READBACK-001** 이 소유한다.
- 본 SPEC 은 `server/lxseq/**` 와 `server/web/presets_api.py` 를 읽지도 고치지도 않는다.

### Out of Scope — 핸들 형태 제3 유형의 발견

- `^FixtureType (\d+)$` 밖의 미관측 핸들 형태를 찾아내는 조사는 별도 카드다.
- REQ-READBACK2-011 이 그 구멍을 명시적으로 열어 두는 것까지가 본 SPEC 의 몫이다.
- 그 구멍을 메우려면 값을 트리가 선언한 이름 집합에 대고 검사해야 하는데(`inventory.py:479-485`), 그것은 표를 쥔 경로에서만 가능하고 조회 예산 재협상을 부른다.

### Out of Scope — 조회 예산 가드 자체의 재협상

- `query_state` 예산 가드는 이 저장소가 **비준된 것으로 취급**한다(`server/prechk/inventory.py:469-473`).
- 본 SPEC 은 그 가드 안에서 증가분을 상한으로 묶을 뿐(REQ-READBACK2-012), 가드의 값이나 정책을 바꾸지 않는다.

### Out of Scope — `fuzzy_type_equal` 의 매칭 폭 조정

- `server/vwx/rig.py:58` 의 포함관계 매칭 자체는 본 SPEC 이 건드리지 않는다.
- 오늘 `console_count` 가 0 인 이유는 매칭 폭이 아니라 **비교 대상이 핸들 문자열**이기 때문이며, 이름을 넘기면 같은 함수가 그대로 옳게 동작한다.

### Out of Scope — 새 콘솔 쓰기 동사

- 본 SPEC 은 어떤 새 쓰기 명령·동사·툴도 정의하지 않으며, 기존 툴에 쓰기 능력을 더하지도 않는다.
- 콘솔 쓰기 총계는 0 이다(REQ-READBACK2-013).

### Out of Scope — 앱 쪽 타임코드 트랜스포트

- 음악 동기·타임코드 재생 축은 SPEC-COPILOT-MUSICSYNC-001 이 소유한다.
- 본 SPEC 과는 의존 관계가 없다.

---

## E. 제약

- **개발 방식**: TDD(`.moai/config/sections/quality.yaml` `constitution.development_mode`) — RED-GREEN-REFACTOR. 전 범위가 순수 서버·UI 이므로 라이브 없이 RED 를 만들 수 있다.
- **`ConsolePort.ping()` 시그니처 무변경**: 넓히면 모든 `FakeConsole` 로 파급된다(REQ-READBACK2-001).
- **조회 예산**: `read_inventory` 소비자마다 `query_state` 가 하나씩 늘어날 수 있다. 그 **상한**(지점당 1회)과 **스코프 안 재사용**(한 핸들러 호출의 두 자리는 이름 표를 나눠 쓴다)은 REQ-READBACK2-012 가 `shall` 로 묶으며, AC-READBACK2-013a·013b 가 이진 판정한다. 기존 루트 판독의 재사용은 의무가 아니다 — `server/prechk/**` 무변경 제약(REQ-READBACK2-010) 아래에서 도달 불가능하기 때문이다(§A.3).
- **UI 파급 수용**: 자체 health state 채택(plan.md §C C-1)의 대가로 `server/web/PROTOCOL.md:57` 의 `health` enum 과 `ui/src/protocol.ts:1190-1207` 의 라벨·가이던스, `ui/src/protocol.test.ts` 가 함께 바뀐다. 이 파급은 결정에서 **의도적으로 수용**됐다.
- **쓰기 예산 0**: 본 SPEC 은 콘솔에 쓰지 않는다. 001 과 병렬로 돌아도 쓰기 충돌이 원리적으로 발생하지 않는다.

---

## F. 교차 참조

- `research.md` (동봉, 포인터) → `../SPEC-COPILOT-READBACK-001/research.md` §R3·§R4 — 두 요구의 코드 좌표·기존 테스트·위험 전수
- `reports/app-fresh-eyes-review-20260903.md` §3.4·§4 P1 — 발원
- `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-2.md` §D11 — 본 SPEC 신설의 근거
- SPEC-COPILOT-READBACK-001 — R1 직렬화 · R2 값 측정 (병렬 · 무의존)
- SPEC-COPILOT-PARITY-001 — 핸들 타입 번역 AC 계열
- SPEC-COPILOT-RECVOBS-001 — 회신 수신 관측 가능성
- SPEC-COPILOT-VWX-001 — VWX diff 판정 계열
- `.claude/rules/moai/core/verification-claim-integrity.md` — 5절 형식의 정본
