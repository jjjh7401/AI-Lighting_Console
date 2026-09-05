---
id: SPEC-COPILOT-READBACK-001
title: "되읽기를 값까지 — 응답기 직렬화와 프리셋 값 측정"
version: "0.2.0"
status: completed
created: 2026-09-03
updated: 2026-09-04
author: orchestrator (plan session 317272ed)
priority: P1
phase: "v1.7.0 target"
module: "console/lua/copilot_responder.lua, console/lua/PROTOCOL.md, server/web/presets_api.py, server/lxseq/preset_mapper.py, server/tests/"
lifecycle: spec-anchored
tags: "readback, value-verification, table-serialization, responder-1.6.4, unverified-disclosure, console-write-budget, evidence-discipline"
tier: M
related_specs: [SPEC-COPILOT-READBACK-002, SPEC-COPILOT-INTROSPECT-001, SPEC-COPILOT-RECVOBS-001, SPEC-COPILOT-LXSEQ-003, SPEC-COPILOT-TRUNCATE-001]
---

# SPEC-COPILOT-READBACK-001 — 되읽기를 값까지

> **이 SPEC이 닫는 구멍**: 이 앱은 콘솔에 무언가를 **올렸다는 것**은 말할 수 있지만 **맞게 올라갔다는 것**은 말하지 못한다. 프리셋 임포트가 남기는 `unverified: ["value_match"]`(`server/lxseq/preset_mapper.py:134-135`)는 그 무능의 자백이고, 사용자가 팝업에서 보는 색은 콘솔이 아니라 **앱이 스스로 저장해 둔 팔레트**다(`server/web/presets_api.py:76-84`). 되읽기 채널이 이름과 점유까지만 답하기 때문이다.
>
> **관측된 사실이지 가설이 아니다**: `M.safe_property`(`console/lua/copilot_responder.lua:290-308`, 2026-09-03 실측 확인)는 테이블 값에 `tostring(value)`를 걸어 **주소 문자열**을 회신한다. 같은 회신이 `t="table"`로 **값이 테이블이라는 사실은 이미 정직하게 말하면서** 주소를 건넨다. `docs/runbooks/console-channel-facts.md:93-101`은 이를 「제거 가능한 미구현」으로 분류한다.
>
> **그러나 값 판독은 아직 존재가 확인되지 않았다.** 값 프로퍼티로 추정된 이름들은 라이브 프로브 네 건에서 **전부 `property not readable`** 로 답했다(research.md §R2). 그러므로 본 SPEC은 값 판독을 **약속하지 않고 측정한다** — 있으면 열고, 없으면 **없음을 측정된 사실로 닫는다.** 둘 다 PASS다.
>
> **범위**: 본 SPEC 은 네 요구 중 **R1(응답기 테이블 직렬화)과 R2(프리셋 값 측정)** 두 축만 소유한다. R3(런타임 응답기 버전 게이트)과 R4(FixtureType 핸들→이름 번역)는 SPEC-COPILOT-READBACK-002 로 분리됐다. 두 SPEC 은 서로 의존하지 않으며 병렬로 진행할 수 있다.

## HISTORY

| 일자 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-03 | 0.1.0 | 최초 초안. 보고서 `reports/app-fresh-eyes-review-20260903.md` §3.2·§3.4·§4 P1 을 네 요구 모듈(R1 직렬화 · R2 값 판독 측정 · R3 버전 게이트 · R4 타입명 번역)로 분해. 조사 근거는 동봉 `research.md`(기준 `origin/main adae0ac`, 읽기 전용). | 보고서 P1 · research.md |
| 2026-09-03 | 0.1.1 | plan-audit iteration 1 (FAIL 0.795) 대응. REQ 번호 연속화 · 모든 AC 에 `↔ REQ` 명기 · 범위 밖 불릿 전환 · 조회 예산 REQ 신설 · 어긋난 행 앵커 9건 정정 · 프로세스 주어 REQ 5건 교체 · 미커버 절 4건 AC 보강. | `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-1.md` |
| 2026-09-03 | 0.2.0 | **SPEC 분할.** plan-audit iteration 2 (PASS 0.925) 가 D11 로 Tier M 예산(REQ 16 / AC 16) 2배 초과를 지적했다(REQ 32 / AC 33). 감독이 2026-09-03 에 **두 Tier M SPEC 으로 분할**을 결정했고, 분할선은 `plan.md` 가 이미 「순수 서버 · 병렬 가능」으로 떼어 둔 자리를 그대로 썼다. 본 SPEC 은 **R1+R2** 를 보유하고, R3+R4 는 SPEC-COPILOT-READBACK-002 로 이관됐다. 횡단 규율 5건(옛 REQ-028~032)은 구속하는 자리의 모듈 REQ 로 접었고, 한 문장짜리 REQ 는 부정 대조군을 잃지 않는 선에서 병합했다. 결과 **REQ 15 / AC 16**. D12(잔존 산출물 주어 4건) · D13(하위 ID 설명) · D14(조사 노트 판정의 기계화)도 함께 해소했다. | `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-2.md` §D11-D14 · 감독 결정 2026-09-03 |

---

## A. 배경

### A.1 지금 무엇이 이미 건강한가 (건드리지 않는다)

| 절 | 상태 | 근거 |
|---|---|---|
| 회신이 타입을 말하는 것 | ✅ 건강 | `t="table"` 이 이미 실린다 — 응답기는 **거짓말하고 있지 않다**(`copilot_responder.lua:290-308`) |
| JSON 인코더의 존재 | ✅ 존재 | `M.json_encode` `:133-166`, 외부 라이브러리 0 (`require` 없음) |
| 절단 고지 | ✅ 건강 | `truncated` 플래그 + 페이징 `offset` 에코 무진행 방어(`server/rig/paging.py:97-99`) |
| 미검증 자백 | ✅ 건강 | `unverified: ["value_match"]` 가 **이미 정직하다**(`preset_mapper.py:134-135`) |
| 재임포트 경로와 그 게이트 | ✅ 건강 | `server/safety/console.py:323` → `:463`, 자기 삭제 방어 `:426` |
| 값 판독 능력 | ❌ **미측정** | 추정 이름 전부 `property not readable`, **전수 조사는 아직 없다** |

즉 본 SPEC 은 *"응답기가 거짓말한다"* 를 고치는 것이 **아니다.** 응답기는 자기가 모르는 것을 모른다고 말하고 있다. 고치는 것은 **알고 있는 것을 안 풀어서 못 건네는 자리**(R1) 하나이고, R2 는 고치는 것이 아니라 **재는 것**이다.

### A.2 R1 은 R2 의 전제이지 R2 의 답이 아니다

Part 계층에서 구조적으로 유사한 결과가 이미 기록돼 있다(`console-channel-facts.md:93-101`): `PRESETDATA`·`REFERENCES` 는 `""` 를 답하는데 `SELECTIONDATA`·`DEPENDENCIES` 는 **테이블 주소**를 답한다. 즉 이 콘솔에는 테이블 값을 실제로 내주는 프로퍼티가 존재한다.

그러나 **프리셋 객체가 그런 프로퍼티를 갖는지는 아무도 재지 않았다.** t95 가 기록한 것은 「프리셋 객체가 138개 프로퍼티를 답했고 그중 27개만 한 회신에 들어왔다」이며(`server/tests/test_overlap_preserve.py:180-186`), 페이징(1.6.2)이 나머지 111개의 **이름**을 도달 가능하게 만들었을 뿐이다. `console/lua/PROTOCOL.md:359-361` 이 그 경계를 문면으로 적는다 — *"Paging opens the NAME list; it says nothing about readability."*

> **그러므로 R1 은 「테이블이 나오면 풀어서 준다」는 능력이고, R2 는 「프리셋에 그런 테이블이 있는가」라는 질문이다.** 능력이 있어도 질문의 답은 「없다」일 수 있고, 그 경우에도 R1 은 Part 계층에서 이미 값을 낸다. 두 요구는 **의존하되 동치가 아니다.**

### A.3 R2 의 가장 큰 위험은 실패가 아니라 성공처럼 보이는 실패다

`unverified` 에서 `"value_match"` 를 빼는 것은 **주장 등급의 상향**이다 — 「무언가 저장됐다」가 「맞게 저장됐다」로 바뀐다. 그리고 이 앱에는 이미 **콘솔에서 오지 않은 색**이 화면에 떠 있다(`presets_api.py:70-155` 의 팔레트 재구성 계층). 값 판독이 열리는 순간 그 팔레트는 **두 번째 진실 후보**가 되고, 둘이 갈릴 때 화면이 어느 쪽을 보여주는지가 곧 정직성의 정의가 된다.

`_already_present_from`(`preset_mapper.py:170-177`)이 이미 같은 규율을 한 줄로 적어 뒀다 — 「이미 있음」은 「맞게 있음」이 아니다. 본 SPEC 은 그 문장을 **값 축으로 연장**한다.

### A.4 콘솔 쓰기 예산은 정확히 하나다

이 저장소의 규율은 **판독 경로가 쓰기를 획득해서는 안 된다**는 것이다. R2 는 읽기 전용 조회이며, **R1 만이 `console/lua/` 를 건드린다.** 그 비용은 **운영자 승인 재임포트 1회**로 고정된다. 자기 삭제는 응답기 안에서 불가능하고(`server/safety/console.py:426`), 순진한 delete-then-import 는 `User Canceled Command` 를 돌려주며 `ReloadAllPlugins` 는 아무것도 리로드하지 않고 `ok:true` 를 답했다(`docs/research/ma3-effects/12-introspect-v161-redeploy-probe.md §1.1-1.3`).

같은 이유로 SPEC-COPILOT-READBACK-002(R3+R4)는 **쓰기 0** 이며, 본 SPEC 의 1회가 두 SPEC 을 합친 전체 예산이다.

---

## B. 요구사항 (GEARS)

> REQ 번호는 **001-015 연속**이다. 절 구분은 번호 공백이 아니라 §B.1~§B.3 표제가 한다.
> 각 REQ 를 검증하는 AC 는 §C 표의 「AC」 열과 `acceptance.md` §H 커버리지 표가 정본이다.

### B.1 R1 — 응답기 테이블 직렬화 (1.6.4)

- **REQ-READBACK-001** [Event-driven] — **When** `M.safe_property` 가 읽은 값의 `type(value)` 가 `"table"` 이면, the 응답기 **shall** `tostring(value)` 대신 `M.json_encode` 로 인코딩한 **JSON 텍스트**를 값 문자열로 회신하며, 회신의 `t` 는 `"table"` 로, `v` 는 **JSON 을 담은 문자열**로 유지하고 **새 형제 필드를 신설하지 않는다.** 분기는 `console/lua/copilot_responder.lua:290-308` **한 자리**에서 일어나고 `prop`·`props` 두 빌더는 무변경으로 그 결과를 받는다. 형상을 그대로 두는 이유는 「응답기는 해석하지 않는다」는 계약(`PROTOCOL.md:315-317`, `:388-390`)과 기존 디코드 지점 단일성(`server/bridge/protocol.py:77-113`)을 보존하기 위함이다.
- **REQ-READBACK-002** [Unwanted] — the 직렬화 **shall not** 메타메소드를 호출한다. `__index`·`__tostring`·`__pairs` 어느 것도 발동시키지 않으며, 함수 값 필드는 오늘과 같이 **호출되지 않고** 타입만 보고된다(`copilot_responder.lua:294-297` 의 읽기 전용 경계, REQ-INTROSPECT-009 계승).
- **REQ-READBACK-003** [Ubiquitous] — the 인코더 **shall** 깊이 상한과 순환 탐지를 갖는다. 상한 초과 노드는 값을 버리고 **초과 사실을 실은 표식**으로 대체하며, 이미 방문한 테이블은 재방문하지 않는다. 근거: 오늘의 `M.json_encode`(`:133-166`)에는 **깊이 제한도 순환 탐지도 없어** 자기참조 테이블이 운영자의 쇼 도중 응답기를 멈춰 세울 수 있다.
- **REQ-READBACK-004** [Ubiquitous] — the 인코더 **shall** 배열/객체 판정을 **명시적으로** 내리고 객체 키를 결정적으로 정렬한다. 오늘의 휴리스틱(`getmetatable(value) == ARRAY_MT or value[1] ~= nil`, `:147`)은 `[1]` 키를 가진 해시를 배열로 인코딩해 **나머지 키를 소실시킨다.** 키가 `1..n` 의 연속 정수 전체가 아닌 테이블은 객체로 인코딩되고 모든 키가 보존되며, 정렬은 `:158` 의 `table.sort(keys)` 를 계승한다.
- **REQ-READBACK-005** [Event-driven] — **When** 직렬화 결과가 값 길이 상한을 넘으면, the 응답기 **shall** **구조적으로** 절단한다 — 후행 엔트리를 통째로 제거하고 재인코딩하여 `v` 가 **끝까지 파싱 가능한 JSON** 으로 남게 하며, 절단 사실을 기존 절단 고지 경로로 보고한다. 바이트 단위 절단(`safe_truncate` `:658-670`)을 테이블 값에 적용하는 것은 **금지**다 — 잘린 JSON 조각은 파싱 불가이므로 절단 고지가 있어도 소비자가 쓸 수 없다.
- **REQ-READBACK-006** [Where] — **Where** 값 길이 상한(`max_prop_value = 240`, `copilot_responder.lua:43`)이 테이블 값에 대해 상향되는 경우, the 상향폭 **shall** `server/tests/test_lua_responder_payload_budget.py` 가 검증하는 2048 산술 안에서만 정해지며 `max_payload = 1900`(`:41`)은 **변경하지 않는다.**
- **REQ-READBACK-007** [Ubiquitous] — the 1.6.4 개정 커밋 작성자 **shall** `console/lua/` 잠금 규약을 같은 커밋 안에서 이행한다: 날짜 붙은 산문 승인 블록 + `server/tests/test_overlap_preserve.py:227-231` 의 **두 다이제스트 재고정**(`copilot_responder.lua`, `PROTOCOL.md`) + `PROTOCOL.md` 개정 + 버전 리터럴 갱신(`test_lua_responder.py:81`, `test_responder_deploy.py:177`, `test_responder_roundtrip.py:125,128,136`) + `VERSION`(`:82`) 을 `1.6.4` 로.
- **REQ-READBACK-008** [Ubiquitous] — the 재임포트 실행자 **shall** 본 SPEC 전체의 콘솔 쓰기를 **응답기 재임포트 정확히 1회**로 제한하고, 그 1회를 운영자 승인을 받아 머지와 **분리된 행위**로 수행하며, 배포 완료의 근거로 **`ping` 이 `1.6.4` 를 답한 것만**을 채택한다. main 브랜치의 파일 내용은 근거가 아니다 — 이 저장소에는 **live-1.6.1 / main-1.6.2 전례**가 기록돼 있다(`server/tests/test_overlap_preserve.py:225-232`, 실측 확인).

### B.2 R2 — 프리셋 값 되읽기 (측정 우선 · 양쪽 다 고지)

- **REQ-READBACK-009** [Ubiquitous] — the 조사 스윕 **shall** 값 판독을 구현하기 **전에**, 프리셋 객체 1개에 대한 `introspect` 전수 열거(138 이름, 1.6.2 페이징)와 그 이름 전부에 대한 `props` 판독 결과를 **양성 대조군과 음성 대조군을 포함하여** 조사 노트로 기록하고, 그 노트에서 「0 건」과 「재지 못함」을 구별해 적는다. 이 채널의 빈 답·0 은 **부재의 증거가 아니다** — 내용이 있는 Group 객체가 `COUNT 0` 을 답한 사례가 이미 기록돼 있다(SPEC-COPILOT-INTROSPECT-001 계열, t95). 판독 실패는 실패한 이름과 사유 문자열을 그대로 싣는다. 이 노트가 R2 의 진입 조건이다.
- **REQ-READBACK-010** [Where] — **Where** 조사에서 테이블 값 또는 판독 가능한 값 프로퍼티가 **발견된 경우**, the 프리셋 API **shall** `GET /api/presets/{pool_no}` 회신에 이름 옆에 값을 함께 싣고, 그 값의 출처가 콘솔임을 필드로 구별한다. (주입 지점과 반환 형상의 설계는 plan.md §E M2 후속 표가 소유한다.)
- **REQ-READBACK-011** [Event-driven] — **When** 라이브 되읽기 값이 앱이 **변환해서 쓴** 값(`col_rgb_percents` `server/lxseq/preset_parser.py:521` · `dim_level_percent` `:346` · `kelvin_to_rgb` `:419`)과 일치하면, the 임포트 매퍼 **shall** 해당 프리셋의 `unverified` 에서 `"value_match"` 를 제거한다. 일치 판정은 변환 후 값 기준이며, 비교 없이 제거하는 경로는 존재하지 않는다.
- **REQ-READBACK-012** [Where] — **Where** 조사가 값 프로퍼티를 **하나도 찾지 못한 경우**, the 조사 노트 **shall** `시도한 이름` · `사유` · `대조군` · `실행일` 네 표제를 **문자열 그대로** 갖추어 각각의 내용을 싣고, the 임포트 매퍼 **shall** `_VALUE_MATCH_REASON`(`preset_mapper.py:64-68`) 문면을 「아직 안 했다」가 아니라 「이 채널에는 없다, 다음 명령들을 이 날짜에 쏴서 확인했다」로 강화한다. 네 표제를 리터럴로 못박는 이유는 R2 종료 판정이 사람의 독해가 아니라 **grep 으로 이진 판정**되게 하기 위함이다. **이것은 실패가 아니라 유효한 PASS 결과다.**
- **REQ-READBACK-013** [Unwanted] — the 값 회신 **shall not** 앱이 저장한 팔레트 스와치를 콘솔 판독값으로 제시한다. 두 출처는 회신에서 **구별 가능한 필드**에 담기며, 콘솔이 답하지 않은 값은 어떤 필드에도 콘솔 유래로 실리지 않는다(`presets_api.py:76-84` 의 기존 정직성 규율 계승).
- **REQ-READBACK-014** [Unwanted] — the `value_match` 고정 테스트 3건(`test_lxseq_preset_mapper.py:239-241, :443, :445-448`) **shall not** 라이브 되읽기 증거와 **분리된 커밋**에서 완화된다. 세 고정은 주장 상향의 트립와이어다. 아울러 the 임포트 매퍼 **shall not** REQ-READBACK-009 의 조사 노트 없이 `unverified` 에서 `"value_match"` 를 제거한다 — 기록이 제거보다 먼저다.

### B.3 횡단 — 증거 규율

- **REQ-READBACK-015** [Ubiquitous] — the 완료 보고 작성자 **shall** 되읽기 주장을 `.claude/rules/moai/core/verification-claim-integrity.md` 의 5절 형식(주장·증거·기준 귀속·미검증·잔여 위험)으로 싣고, 증거 절 어디에서도 `exec: ok` 를 효과의 증거로 인용하지 않는다. 효과는 되읽은 결과로만 증명되며, 페이징 판독은 `childCount` 대조와 `truncated` 판독을 **함께** 수행한 뒤에만 완전하다고 말할 수 있다. 특히 **미검증 절이 비어 있는 보고는 「아무것도 안 잰 것이 없다」는 강한 주장**이며 그 자체가 참이어야 한다.

---

## C. 성공 기준

| # | 기준 | 판정 수단 | AC |
|---|---|---|---|
| C1 | 테이블 값이 파싱 가능한 JSON 으로 도착하고 회신 형상이 그대로다 | 오프라인 — `lua_mock_env.py` 에 테이블을 심고 `props` 회신의 `v` 를 `json.loads` | AC-READBACK-001 |
| C2 | 순환·심층·해시-with-`[1]`·절단 테이블이 응답기를 멈추거나 키를 잃지 않는다 | 오프라인 부정 대조군 4종 | AC-READBACK-002 · 003 · 004 · 005 |
| C3 | 페이로드 예산과 `console/lua/` 잠금 규약이 이행된다 | 오프라인 — 예산 산술 테스트 + 다이제스트 재고정 | AC-READBACK-006 · 007 |
| C4 | 프리셋 값 프로퍼티의 존재 여부가 **측정된 사실**로 기록된다 | 조사 노트 + 양성/음성 대조군 | AC-READBACK-008 · 009 · 010 · 011 · 012 · 013 · 014 |
| C5 | 콘솔 쓰기 총계가 1 이고 배포가 `ping` 으로만 확인된다 | 세션 명령 로그 + 라운드트립 | AC-READBACK-015 |
| C6 | 완료 보고가 5절 형식을 갖추고 미검증 절이 비어 있지 않다 | 보고서 검사 | AC-READBACK-016 |

세부 Given/When/Then 과 REQ↔AC 양방향 대응은 `acceptance.md`(§H 커버리지 표)가 정본이다.

---

## D. 범위 밖 (Out of Scope)

### Out of Scope — 런타임 응답기 버전 게이트 (R3)

- `ConsoleLink.ping` 이 버리는 `version` 값의 보존, 기대 버전 단일 상수, `SafetyGate._check_health` 의 버전 불일치 차단 분기는 **SPEC-COPILOT-READBACK-002** 가 소유한다.
- 본 SPEC 은 그 게이트가 감시할 **버전 값 자체**(1.6.3 → 1.6.4)를 만들 뿐, 게이트를 세우지 않는다.
- 두 SPEC 은 서로 의존하지 않는다 — 002 는 1.6.4 배포를 기다리지 않고 진행할 수 있다.

### Out of Scope — FixtureType 핸들→이름 번역 (R4)

- `read_inventory(..., type_names=)` 를 빠뜨린 여섯 호출 지점, `build_patch_sheet` 의 매개변수화, VWX diff 의 타입별 대수, 패치 시트 렌더 경계, 조회 예산 상한은 **SPEC-COPILOT-READBACK-002** 가 소유한다.
- 본 SPEC 은 `server/prechk/**` · `server/vwx/**` · `server/paperwork/**` 를 읽지도 고치지도 않는다.

### Out of Scope — 앱 쪽 타임코드 트랜스포트

- 음악 동기·타임코드 재생 축은 SPEC-COPILOT-MUSICSYNC-001 이 소유한다.
- 본 SPEC 은 그 SPEC 의 **선행 조건**이지 그 일부가 아니다 — 값 되읽기가 없으면 동기 결과를 검증할 수단이 없기 때문에 순서가 앞설 뿐이다.

### Out of Scope — R1 직렬화가 노출하는 범위를 넘는 큐 내용 되읽기

- 큐 내용의 열 단위 판독(트래킹된 값, 페이드/딜레이의 참조 해석)은 본 SPEC 이 열지 않는다.
- R1 이 테이블 값을 풀어주는 만큼만 부수적으로 보이게 되며, 그 이상은 별도 카드다.

### Out of Scope — `max_payload` 의 2048 산술 밖 상향

- `max_payload = 1900`(`console/lua/copilot_responder.lua:41`)은 **측정된 스윕 결과**다(2000 전달, 2100 유실).
- 값 길이 상한은 2048 산술 안에서만 조정되며, 페이로드 예산 자체의 재협상은 별도 측정 카드다.

### Out of Scope — LXSEQ-003 AC 판정

- LXSEQ-003 의 미결 AC 판정은 별도 카드가 소유한다.
- 본 SPEC 은 그 SPEC 의 `value_match` 소비 지점을 **읽기만** 하고 그 SPEC 의 판정을 대신 내리지 않는다.

### Out of Scope — 새 콘솔 쓰기 동사

- 본 SPEC 은 어떤 새 쓰기 명령·동사·툴도 정의하지 않는다.
- 폐쇄 툴 집합에 대한 추가는 물론, 기존 툴에 쓰기 능력을 더하는 개정도 범위 밖이다.
- 유일한 쓰기는 §B.1 REQ-READBACK-008 의 재임포트 1회다.

### Out of Scope — 팔레트 스와치 계층의 철거

- 값 판독이 열려도 앱 저장 팔레트 계층(`server/web/presets_api.py:70-155`)은 이 SPEC 에서 제거되지 않는다.
- 두 출처를 **구별 가능하게 만드는 것**(REQ-READBACK-013)까지가 범위이며, 어느 쪽을 화면의 기본 표시로 삼을지는 감독 결정이다.

---

## E. 제약

- **개발 방식**: TDD(`.moai/config/sections/quality.yaml` `constitution.development_mode`) — RED-GREEN-REFACTOR. R1 은 오프라인 하네스가 **실제 `.lua` 를 lupa 로 실행**하므로(`server/tests/lua_mock_env.py`) 라이브 없이 RED 를 만들 수 있다.
- **잠금 경계**: `console/lua/` 는 바이트 잠금이며 다이제스트로 고정된다(`test_overlap_preserve.py:227-231`). 승인 없는 편집은 테스트가 거부한다.
- **회신 디코드 단일성**: `server/bridge/protocol.py:77-113` 이 유일한 디코드 지점이며 스키마 검증이 없다. `v` 안의 JSON 은 **소비자가 명시적으로 파싱**해야 한다.
- **쓰기 예산**: 콘솔 쓰기 1회(재임포트). SPEC-COPILOT-READBACK-002 는 쓰기 0 이므로 이 1회가 두 SPEC 을 합친 전체다.

---

## F. 교차 참조

- `research.md` (동봉) — 네 요구의 코드 좌표·기존 테스트·위험 전수. §R1·§R2 가 본 SPEC 의 근거이고 §R3·§R4 는 SPEC-COPILOT-READBACK-002 를 위해 남는다.
- `reports/app-fresh-eyes-review-20260903.md` §3.2·§3.4·§4 P1 — 발원
- `.moai/reports/plan-audit/SPEC-COPILOT-READBACK-001-review-1.md` · `-review-2.md` — iteration 1·2 감사(0.1.1 개정과 0.2.0 분할의 근거)
- `docs/runbooks/console-channel-facts.md` §4 — 콘솔 채널 실측 사실 · 「안 잰 것」 목록
- `console/lua/PROTOCOL.md` §4.6·§4.8 — `prop`/`props` 회신 계약
- SPEC-COPILOT-READBACK-002 — R3 버전 게이트 · R4 타입명 번역 (병렬 · 무의존)
- SPEC-COPILOT-INTROSPECT-001 — 페이징과 읽기 전용 경계
- SPEC-COPILOT-RECVOBS-001 — 회신 수신 관측 가능성
- SPEC-COPILOT-TRUNCATE-001 — 절단 고지의 형상 규율
- SPEC-COPILOT-LXSEQ-003 — `value_match` 소비 지점
