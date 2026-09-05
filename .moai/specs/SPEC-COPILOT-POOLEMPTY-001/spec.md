---
id: SPEC-COPILOT-POOLEMPTY-001
title: "빈 풀과 죽은 풀을 가른다 — 열거 신뢰도 마커"
version: "0.1.1"
status: draft
created: 2026-09-06
updated: 2026-09-06
author: manager-spec (plan session, card t270)
priority: P1
phase: "v1.8.1 target"
module: "console/lua/copilot_responder.lua, console/lua/PROTOCOL.md, server/orchestrator/tools.py, server/tools/musicsync_m3a_probe.py, server/safety/responder_version.py"
lifecycle: spec-anchored
tags: "enumeration-reliability, empty-pool-vs-dead-pool, timecode-slot-verdict, responder-1.6.5, backward-compatible, zero-console-write"
tier: M
depends_on: [SPEC-COPILOT-MUSICSYNC-001, SPEC-COPILOT-READBACK-002]
---

# SPEC-COPILOT-POOLEMPTY-001 — 빈 풀과 죽은 풀을 가른다

> **이 SPEC 이 닫는 구멍**: 타임코드가 **하나도 없는 쇼**에서 앱은 **첫 타임코드를 영원히 만들 수 없다.**
>
> 앱의 슬롯 판정 `_timecode_slot_verdict`(`server/orchestrator/tools.py:2814`)는 `DataPool/Timecodes` 가 `childCount 0` 을 답하면 **unknown** 으로 닫고 타임코드 축을 통째로 내려놓는다(`:2876-2880`). 그 신중함은 **오늘 기준으로 정당하다** — 응답기가 두 상태를 구별해 주지 않기 때문이다. `M.safe_children`(`console/lua/copilot_responder.lua:625-653`)은 `handle:Children()` 과 `handle:Count()` **둘 다** pcall 실패하면 `{}` 를 반환하고(`:652`), 그 뒤 `M.build_snapshot`(정의 `:822`, 페이로드 조립 `:846-885`)은 그 빈 테이블을 근거로 `ok = true`, `node.childCount = 0`, `children = []`, `truncated = false` 를 **성공 회신으로** 내보낸다. 빈 풀과 죽은 풀이 **같은 페이로드**다.
>
> **결함은 판정이 아니라 채널이다.** 앱은 자기가 가진 정보로 최선의 답을 하고 있다. 고쳐야 할 것은 「앱이 더 관대해지는 것」이 아니라 **응답기가 자기 열거가 성공했는지를 말하게 하는 것**이다.
>
> **실측 근거(2026-09-05, MUSICSYNC-001 M3-a 1회차)**: `docs/research/ma3-effects/14-musicsync-m3a-timecode-probe.md:9` — 「슬롯 판정이 unknown 다 — DataPool/Timecodes 가 자식 0 을 답했다 — 빈 풀과 실패한 열거가 여기서는 구별되지 않는다. 콘솔 쓰기 0건으로 닫는다」. 프로브는 **무결론**으로 닫았고 쓰기는 0건이었다. 2회차(`…-run2.md`)는 **운영자가 `Timecode 1` 을 손으로 만든 뒤에야** 진행됐다. 같은 전제가 M3-b 리허설도 **새 쇼에서는 항상** 막는다.
>
> **콘솔 쓰기 0.** 이 SPEC 이 콘솔에 발화하는 명령은 없다(REQ-POOLEMPTY-015). 유일한 콘솔 변경은 M3 에서 **운영자가 직접 하는 플러그인 재임포트**다.

## HISTORY

| 날짜 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-06 | 0.1.0 | 최초 작성 (카드 t270, Tier M) | MUSICSYNC-001 M3-a 1회차 무결론 실측 |
| 2026-09-06 | 0.1.1 | plan-audit 1차(FAIL 0.71) 반영 — REQ-016(술어 들어올리기) 추가, REQ-009 앵커·갈래 수 정정, REQ-008 GEARS 표기, 앵커 4건 정정, `depends_on` | `.moai/reports/plan-audit/SPEC-COPILOT-POOLEMPTY-001-review-1.md` |

---

## §1 왜 (WHY)

### 1.1 관측된 손해

새 쇼(타임코드 0개)에서 `prepare_songcue` 는 타임코드 축을 **항상** 내려놓는다. 운영자가 손으로 `Timecode 1` 을 만들어 주기 전까지 앱은 음악 시간축 기능을 **한 번도** 쓸 수 없다. 이것은 성능 저하가 아니라 **기능의 완전한 부재**이며, 가장 흔한 상황(새 쇼)에서만 발생한다는 점에서 더 나쁘다.

### 1.2 왜 지금 판정을 그냥 완화하면 안 되는가

`childCount 0` 을 무조건 free 로 읽으면, **열거에 실패한 살아 있는 풀**도 free 로 읽힌다. 그 뒤 `Store Timecode <n>` 이 나가면 **운영자의 쇼를 덮는다.** 같은 함정이 `_free_macro_slot`(`server/orchestrator/tools.py:2903`, 함정 본문 `:2932-2946`)에도 그대로 있고, 그쪽 주석은 그 대가를 명시한다 — 응답기 자신의 `Copilot Go` 매크로를 덮으면 **이 시스템이 말하는 통로 자체가 끊긴다.**

따라서 완화의 전제는 하나뿐이다: **열거가 성공했다는 것을 응답기가 말해 줄 것.**

### 1.3 왜 응답기 쪽인가

`M.safe_children` 은 이미 세 갈래를 **안에서** 구별하고 있다 — `Children()` 성공(`:627-638`), `Count()`+`Ptr()` 성공(`:639-651`), 둘 다 실패(`:652`). 그 구별은 함수 경계에서 **버려진다.** 정보는 이미 있고, 새로 재는 것이 아니라 **내보내기만** 하면 된다.

---

## §2 무엇을 (WHAT)

응답기(`VERSION` `1.6.4` → `1.6.5`)가 모든 `state` 회신에 **열거 신뢰도 마커**를 싣고, 앱은 그 마커가 「성공」이라고 말할 때에만 `childCount 0` 을 **비었음**으로 읽는다. 마커가 없는(구버전) 응답기는 **오늘 동작 그대로** unknown 을 유지한다 — 완화가 아니라 **엄격한 하위 호환**이다.

---

## §3 요구사항 (GEARS)

### 3.1 응답기 (Lua)

- **REQ-POOLEMPTY-001** [Ubiquitous] — the `M.safe_children`(`console/lua/copilot_responder.lua:625`) **shall** 항목 배열과 함께 **열거 신뢰도**를 명시적으로 반환한다. 두 성공 경로(`:627-638` `Children()`, `:639-651` `Count()`+`Ptr()`)는 「성공」을, `:652` 의 폴스루는 「실패」를 답한다. 반환 형태는 plan.md §C 가 정한다.
- **REQ-POOLEMPTY-002** [Ubiquitous] — the `M.build_snapshot`(정의 `:822`, 페이로드 조립 `:846-885`) **shall** 성공 회신(`ok = true`)의 `node` 객체에 열거 신뢰도 필드를 **한 개** 싣는다. 값은 `"ok"` 또는 `"failed"` 두 가지뿐이며, 최상위 페이로드 형상은 바꾸지 않는다.
- **REQ-POOLEMPTY-003** [Event-driven] — **When** `handle:Children()` 과 `handle:Count()` 가 **둘 다** pcall 실패하면, the 응답기 **shall** `node.childCount = 0` 과 열거 신뢰도 `"failed"` 를 함께 답한다. `ok`·`children`·`truncated` 의 오늘 값(`true` / `[]` / `false`)은 그대로 둔다.
- **REQ-POOLEMPTY-004** [Event-driven] — **When** 풀이 성공적으로 **빈 목록**을 답하면, the 응답기 **shall** `node.childCount = 0` 과 열거 신뢰도 `"ok"` 를 함께 답한다.
- **REQ-POOLEMPTY-005** [Ubiquitous] — the 응답기 **shall** `M.safe_children` 의 나머지 두 호출 지점(`:690` `M.find_child`, `:1219` `M.set_plugin_source`, 정의 `:1217`)에서 관측 가능한 동작을 바꾸지 않는다. `grep -n 'safe_children(' console/lua/copilot_responder.lua` 는 2026-09-06 `f727e11` 에서 **4행**(정의 `:625` + 호출 `:690`·`:846`·`:1219`)을 답한다.
- **REQ-POOLEMPTY-006** [Ubiquitous] — the 응답기 **shall** `VERSION`(`:98`)을 `"1.6.4"` 에서 `"1.6.5"` 로 올리고, `console/lua/PROTOCOL.md` 는 1.6.5 revision note 와 §4.2 의 새 필드 문서를 싣는다.

### 3.2 앱 (Python)

- **REQ-POOLEMPTY-007** [Where + While] — **Where** 회신이 열거 신뢰도 `"ok"` 를 싣고 **While** `node.childCount == 0` 인 동안, the `_timecode_slot_verdict`(`server/orchestrator/tools.py:2814`) **shall** 슬롯을 **free**(점유자 없음, 타임코드 축 유지)로 판정한다.
- **REQ-POOLEMPTY-008** [Event-driven] — **When** `node.childCount == 0` 인데 열거 신뢰도 필드가 **없거나** `"failed"` 이면, the `_timecode_slot_verdict` **shall** 오늘과 동일하게 **unknown** 으로 닫고 현행 사유 문자열(`:2877-2880`)을 그대로 보고한다.
- **REQ-POOLEMPTY-009** [Unwanted] — the `_timecode_slot_verdict` **shall not** 나머지 다섯 unknown 갈래를 완화한다 — 판독 예외(`:2860-2861`), 비-매핑 페이로드(`:2862-2863`), `truncated`(`:2864-2865`), `childCount` 부재(`:2869-2870`), 짧은 열거(`:2871-2875`). 이 SPEC 이 건드리는 것은 `childCount == 0` 갈래(`:2876-2880`) **하나**다.
- **REQ-POOLEMPTY-010** [Ubiquitous] — the `server/tools/musicsync_m3a_probe.py` `slot_verdict`(`:140`) **shall** 앱과 **같은 술어 객체**를 쓴다(REQ-016 의 들어올린 함수를 임포트). 오늘은 재구현이라 두 술어가 갈리면 프로브의 판정이 앱 판정의 증거가 아니게 된다 — 이 SPEC 이 그 이중화를 없앤다.
- **REQ-POOLEMPTY-011** [Ubiquitous] — the `server/safety/responder_version.py` **shall** `EXPECTED_RESPONDER_VERSION`(`:35`)을 `"1.6.5"` 로 올린다. 이 리터럴은 서버측 **유일한** 출처이며, 검사는 Lua 파일에서 값을 읽어 대조한다(`server/tests/test_responder_roundtrip.py:114`).
- **REQ-POOLEMPTY-012** [State-driven] — **While** 기대보다 낮은 응답기가 콘솔에 살아 있는 동안, the 안전 게이트 **shall** READBACK-002 의 low 갈래(`server/safety/gate.py:435-439`, 분기 머리 `:435`, 「응답기 버전 불일치 — 재임포트 필요」)로 차단한다. 이 SPEC 은 그 분기를 **상속만** 하며 새 분기를 만들지 않는다.
- **REQ-POOLEMPTY-016** [Ubiquitous] — the `_timecode_slot_verdict` 의 순수 판정부 **shall** 모듈 수준 함수 `timecode_slot_verdict(port, path, wanted)`(`server/orchestrator/tools.py`, 툴셋 빌더 **밖**)로 들어올려지고, 툴셋 빌더의 유일 호출자(`:2709`)와 프로브 `slot_verdict`(`server/tools/musicsync_m3a_probe.py:140`)는 이를 **임포트**한다. 근거(2026-09-06 `f727e11` 코드 판독): 클로저가 잡는 이름은 자기 안의 `_suppressed`(`:2849`, `SongCueTimingAxes` 만 사용)와 모듈 임포트 `SongCueTimingAxes`(`:75`) 둘뿐이라 들어올리기의 폭발 반경이 함수 본문(`:2814-2885`)에 갇힌다. 이로써 REQ-010 의 술어 이중화는 **사라진다** — 프로브는 재구현이 아니라 임포트다.

### 3.3 검증

- **REQ-POOLEMPTY-013** [Ubiquitous] — the 오프라인 검사(`server/tests/test_lua_responder.py`, lupa 로 실제 `.lua` 를 구동) **shall** 두 경우를 각각 단언한다 — 성공적으로 빈 풀은 `"ok"` + `childCount 0`, `Children()` 과 `Count()` 가 **둘 다** 예외를 던지는 핸들은 `"failed"` + `childCount 0`.
- **REQ-POOLEMPTY-014** [Event-driven] — **When** 운영자가 응답기 1.6.5 를 재임포트하고 `DataPool/Timecodes` 를 비운 뒤 슬롯 판정을 실행하면, the 앱 **shall** **free** 를 답한다. 같은 회차에 **음성 대조군**(열거할 수 없는 경로)을 쏘아 **unknown** 이 나오는 것까지 확인한다 — 대조군 없는 free 는 증거가 아니다.
- **REQ-POOLEMPTY-015** [Unwanted] — the 앱 **shall not** 이 SPEC 의 검증 과정에서 콘솔에 어떤 쓰기 명령도 발화한다. 이 SPEC 의 콘솔 예산은 **읽기 전용**이며, 유일한 콘솔 변경은 운영자가 직접 수행하는 플러그인 재임포트다.

---

## §4 범위 제외 (Exclusions)

이 절은 **만들지 않을 것**을 적는다. 아래 항목은 out of scope 이며, 이 SPEC 의 어떤 마일스톤도 이들을 건드리지 않는다.

### Out of Scope — 형제 결함 `_free_macro_slot`

- `server/orchestrator/tools.py:2903`(함정 본문 `:2932-2946`)의 매크로 슬롯 헬퍼는 **같은 함정**을 같은 이유로 안고 있다(`childCount 0` → `_MacroPoolIncomplete`). 이 SPEC 이 응답기에 마커를 심으면 그 헬퍼도 같은 방식으로 고칠 **재료가 생기지만**, 폭발 반경이 다르다(매크로 1번 슬롯은 응답기 자신의 `Copilot Go` 매크로다). 별도 카드로 남긴다.
- `_timecode_slot_verdict` 외의 어떤 `childCount 0` 소비 지점도 이 SPEC 에서 변경하지 않는다.

### Out of Scope — 타임코드 기능 자체의 확장

- `Store Timecode` 명령의 발화, 녹화 무장/해제 경로, `operator_handoff` 인계 문구는 MUSICSYNC-001 의 소유이며 이 SPEC 은 손대지 않는다.
- M3-b 리허설의 재실행, 재생 명령 후보 판별, 프로브의 쓰기 예산(`MAX_WRITES = 8`) 소비는 이 SPEC 의 산출물이 아니다 — 이 SPEC 은 그 시도를 **막고 있던 전제**만 걷어낸다. MUSICSYNC-001 은 `completed` 이되 M3-b 리허설은 무결론으로 닫혔으므로, 이 SPEC 이 닫히면 **「빈 풀에서 M3-b 재실행」을 새 카드로 올린다**(sync 단계 산출물).
- 타임코드 슬롯 번호의 자동 선택(빈 슬롯 탐색)은 도입하지 않는다. 번호는 오늘과 같이 호출자가 지정한다.

### Out of Scope — 프로토콜의 구조 변경

- 와이어 프로토콜 버전(`"v": 1`)은 올리지 않는다. 이 변경은 `node` 객체에 필드 하나를 더하는 **가산적** 변경이다.
- `console/lua/PROTOCOL.md` §6 에 새 `ASSUMPTION-<n>` 항목을 추가하지 않는다(2026-09-06 실측: 해당 문서의 §6 계열은 `ASSUMPTION-52` 까지 소비).
- `state` 외의 회신 종(`prop`·`props`·`introspect`·`pong`)에는 이 필드를 싣지 않는다.

---

## §5 제약 (Constraints)

- **하위 호환은 엄격한 방향으로만.** 마커가 없는 회신은 오늘과 **바이트 동일한 판정**(unknown)을 받는다. 구버전 응답기에서 새 앱이 더 관대해지는 경로는 없다.
- **콘솔 쓰기 0.** §3.3 REQ-POOLEMPTY-015.
- **UDP 예산.** `M.build_snapshot` 은 `CONFIG.max_payload` 를 넘으면 children 을 떨어뜨린다. `node` 에 필드가 하나 늘면 그만큼 children 창이 좁아진다 — 회귀 검사는 페이징 동작이 그대로인지 확인해야 한다.
- **버전 핀은 한 줄.** `EXPECTED_RESPONDER_VERSION` 과 Lua `VERSION` 은 반드시 같은 커밋에서 함께 움직인다. 검사가 Lua 파일을 읽어 대조하므로 한쪽만 올리면 검사가 빨강이 된다.
- **실기 검증은 운영자 게이트.** M3 은 운영자가 플러그인을 재임포트하고 `DataPool/Timecodes` 를 비워 준 뒤에만 실행 가능하다.

---

## §6 성공 기준

- `acceptance.md` 의 AC-POOLEMPTY-001..015 전부 통과.
- 오프라인 검사 스위트(`server/tests/`) 초록, 새 회귀 0건.
- 실기 1회차에서 빈 풀 → **free**, 음성 대조군 → **unknown**.
- 콘솔 쓰기 명령 발화 0건.
