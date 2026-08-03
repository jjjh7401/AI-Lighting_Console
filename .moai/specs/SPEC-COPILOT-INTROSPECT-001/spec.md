---
id: SPEC-COPILOT-INTROSPECT-001
title: "핸들 자기진단 동사 — 콘솔이 실제로 무엇을 노출하는지 되묻는 도구"
version: "0.1.0"
status: draft
created: 2026-08-03
updated: 2026-08-03
author: manager-spec
priority: P1
phase: "Phase 3 관측 계층 — 발견 도구 (재생 상태 축의 선행 SPEC)"
module: "console/lua/copilot_responder.lua, server/bridge/protocol.py, server/safety/console.py"
lifecycle: spec-anchored
tags: "introspection, lua-responder, wire-protocol, discovery, read-only, payload-budget, truncation-signal, live-probe"
tier: L
related_specs: [SPEC-COPILOT-EXECBODY-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-SCENE-001]
---

# SPEC-COPILOT-INTROSPECT-001 — 핸들 자기진단 동사

> **이 SPEC은 기능 SPEC이 아니라 발견 도구 SPEC이다.** 재생 상태·진행률을 구현하지 않는다. 그것이 *존재하는지*를 추측이 아니라 **증거로 판정할 수 있게 만드는 것**이 범위다. 판정 결과를 소비하는 기능은 후속 SPEC의 몫이며, 그 경계는 §D가 명시적으로 잠근다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|---|---|---|---|
| 0.1.0 | 2026-08-03 | manager-spec | 최초 작성 (draft, Tier L). 출처: 코디네이터 라이브 실측(2026-08-02, onPC 2.4.2 + 응답기 v1.5.0) — Executor 핸들 대상 후보 프로퍼티 전수 소진 후 `Sequence` 핸들에서 `CurrentCue`가 발견된 사건. 그 사건의 오판("한 핸들에서 후보를 소진했으니 그 정보는 없다")을 구조적으로 제거하는 것이 본 SPEC의 존재 이유다. |

## A. 개요

### A.1 무엇이 일어났는가 (실측 — 추측 아님)

코디네이터가 실물 onPC 2.4.2 + 응답기 `copilot_responder.lua` v1.5.0으로 측정한 사실 3건:

1. **Executor 핸들은 거의 아무것도 주지 않는다.** `state` 조회 결과는 `{"class":"Executor","name":"Sequence 80","sequenceNo":80,"childCount":0}`가 전부였다. `prop`으로 본 문서가 이름까지 확정해 열거하는 **후보 21종**(현재 큐 후보 8종 `Cue` `CueNo` `CurrentCue` `ActiveCue` `CueNumber` `Step` `CurrentCueNumber` `Progress` + 실행 상태 후보 13종 `Active` `IsRunning` `Running` `State` `Status` `Faderposition` `On` `Off` `Rate` `Speed` `Phase` `Master` `Value`)을 시도해 전부 `property not readable`이었다(8+13=21). 이 21종 밖의 추가 판독 2건은 더 나쁜 신호였다 — `Index`는 `ok=true`지만 값이 `'function: 0x...'`(Lua 함수 포인터), `Fader`는 `'Master'`(페이더 **이름**)로 실행 여부와 무관.
2. **Sequence 핸들에는 현재 큐가 있다.** `prop DataPool/Sequences/80 CurrentCue` → 정지 시 `'Sequence 80.1'`, `Go+` 2회 후 `'Sequence 80.2'`. **재생에 따라 값이 이동한다.** 같은 핸들의 `CueNo`는 신뢰 불가(정지 시 `'1'`, 진행 후 빈 문자열).
3. **경로가 틀렸을 뿐 채널은 있었다.** 한 핸들에서 후보를 소진했다는 사실이 "그 정보는 존재하지 않는다"를 **함의하지 않았다.**

### A.2 왜 도구를 먼저 만드는가 (사용자 결정)

후보 소진이 만든 손해는 라운드트립 횟수가 아니다. **틀린 일반화**다. 후보 소진은 "이 핸들에 이 이름이 없다"만 증명하는데, 그것이 "그 정보가 없다"로 확대되면 설계가 잘못된 전제 위에 세워진다. `server/web/cue_monitor.py`(base `3176900`)의 `@MX:REASON` 주석이 그 오판의 흔적을 이미 기록하고 있다 — *"이것은 그런 프로퍼티가 없어서가 아니라 잘못된 오브젝트를 겨냥했기 때문에 실패했다."*

핸들이 **실제로 무엇을 노출하는지 되돌려주는 동사**가 있으면 이 오판 자체가 구조적으로 불가능해진다. 후보를 하나씩 찍는 대신 목록을 받고, "없다"를 추측이 아니라 **열거의 부재**로 판정한다.

따라서 본 SPEC의 산출물은 **능력**이지 기능이 아니다. 재생 상태·진행률이 실제로 존재하는지는 이 도구가 나온 뒤 **증거로** 판정하며(§B.6 발견 산출물), 그 판정을 소비하는 기능은 후속 SPEC이다.

### A.3 두 동사로 나누는 이유 (요청 문법 모호성 — 설계 초반에 다뤄야 함)

기존 `prop` 문법은 *"마지막 비공백 토큰이 프로퍼티 이름, 그 앞 전부가 경로"*다(`PROTOCOL.md` §2). 이 규칙은 경로에 공백이 있어도 동작하도록 만들어졌고, 실제로 본 SPEC이 가장 겨냥하는 경로가 바로 공백을 포함한다 — `Executor 80`.

여기에 "이름 목록"을 뒤에 붙이면 `introspect <id> Executor 80`에서 `80`이 **경로의 일부인지 이름 목록인지 판별 불가능**해진다. 이는 각주로 미룰 수 없는 와이어 설계 문제다.

해결: **동사 2개로 분리한다.**

| 동사 | 형식 | 파싱 규칙 | 모드 |
|---|---|---|---|
| `introspect` | `introspect <id> <object-path>` | 경로 = rest-of-line (기존 `state`와 동일) | 열거 |
| `props` | `props <id> <name-list> <object-path>` | 이름 목록 = **첫** 토큰(공백 불가), 경로 = 나머지 rest-of-line | 명시 이름 일괄 판독 |

두 문법 모두 모호성이 없다. 부수 효과로 M1 판정이 `introspect`만 게이트하고 `props`는 무조건 출하 가능해진다(§A.4).

### A.4 M1 게이트 — DESCOPE는 실패가 아니라 유효한 출력

**MA3 Lua가 핸들의 필드 목록을 열거할 수 있는지 자체가 미확인이다.** 룰북(`server/rulebook/assets/v2.4.2/`)에는 핸들 접근자 API 문서가 **없고**(이 세션 grep 결과 `Dump`/`PropertyCount`/`GetPropertyDisplayName` 전건 0), 이 저장소의 모든 핸들 접근 코드는 예외 없이 pcall 방어 프로브 사다리다. 열거 가능성은 **조사 대상이지 전제가 아니다.**

그래서 M1(라이브 프로브)이 첫 마일스톤이다. 판정에 따라 범위가 갈린다:

- **M1 GO** — 열거원이 하나라도 §B.1의 정합성 게이트를 통과 → `introspect` + `props` 둘 다 출하.
- **M1 NEGATIVE** — 어떤 열거원도 정합성 게이트를 통과하지 못함 → `introspect`는 DESCOPE, **`props`만 출하**. 이 경우에도 22회 라운드트립이 1~2회로 줄고, "없다"의 근거가 개별 추측에서 일괄 판독 기록으로 바뀐다. **부분 성공을 성공으로 위장하지 않되, 부분 성공을 실패로도 위장하지 않는다**(EXECREF-001 → EXECBODY-001로 이어진 규율 계승).

### A.5 선행 조건 (구현 순서가 아니라 배포 현실)

콘솔측 Lua 변경이 포함되므로 순수 Python 변경이 아니다. 확립된 배포 루프를 그대로 따른다: **응답기 Lua 편집 → `server/deploy/pack.py` 재패키징(네이티브 인라인 Base64 XML) → `plugin_import_dir` 파일+Import(동거) 또는 OSC `deploy` 동사(원격) → 라이브 재검증.** 한 사이클마다 실물 콘솔 접근이 필요하며, plan-phase는 이 접근을 가정하지 않는다.

## B. 요구사항 (GEARS)

### B.1 열거 동사 `introspect` (조건부 — M1 GO 시)

- **REQ-INTROSPECT-001** [Event-driven] — **When** 응답기가 `introspect` 요청을 받아 오브젝트 경로를 핸들로 해석하면, the 응답기 **shall** 그 핸들이 **실제로 노출하는 필드 이름의 집합**과 각 이름의 **Lua 값 타입**을 회신한다.
- **REQ-INTROSPECT-002** [Unwanted] — `introspect` 회신 **shall not** 필드의 **값**을 담는다. 이름과 타입만 회신한다. (근거: 값은 페이로드 예산을 예측 불가능하게 만들고 쇼파일 내용 유출 축을 연다 — §B.5. 값이 필요하면 `props`가 담당한다.)
- **REQ-INTROSPECT-003** [Ubiquitous] — `introspect` 회신 **shall** 어떤 열거원이 답했는지를 회신 자체에 명시한다. 출처 불명의 열거 결과는 유효한 회신이 아니다.
- **REQ-INTROSPECT-004** [Ubiquitous] — 열거원의 결과 **shall** 정합성 게이트를 통과한 경우에만 채택되며, 통과하지 못하면 **부분 채택 없이 전량 폐기**된다. 정합성 게이트는 다음을 요구한다: 열거된 이름 집합이, **동일 핸들에서 `prop`으로 독립 확인된 판독 가능 이름 전부를 포함**할 것. (선례 계승: `M.probe_slots`의 "coherent set 전량 채택/전량 폐기" 규율 — 반쯤 믿는 열거는 그럴듯한 오답이 새어 나가는 정확히 그 경로다.)
- **REQ-INTROSPECT-005** [Event-driven] — **When** 어떤 열거원도 REQ-INTROSPECT-004의 게이트를 통과하지 못하면, the 응답기 **shall** 열거 불가를 명시적 실패로 회신한다 — 빈 목록을 성공으로 회신하지 않는다.

### B.2 일괄 판독 동사 `props` (무조건)

- **REQ-INTROSPECT-006** [Event-driven] — **When** 응답기가 명시된 후보 이름 목록과 오브젝트 경로를 담은 `props` 요청을 받으면, the 응답기 **shall** 이름별로 판독 성공 여부·값 타입·값을 **하나의 회신**으로 돌려준다.
- **REQ-INTROSPECT-007** [Ubiquitous] — `props` 회신의 최상위 `ok` **shall** *"요청이 처리되었다"*만을 의미하며, *"모든 이름이 판독되었다"*를 의미하지 않는다. 이름별 성공 여부는 항목별로만 표현된다. (기존 `prop`의 `ok` 의미론과 동일한 계약: `ok`는 "콘솔이 값으로 답했다"이지 "값이 쓸 만하다"가 아니다.)
- **REQ-INTROSPECT-008** [Event-driven] — **When** 개별 값이 항목 예산을 초과하면, the 응답기 **shall** 그 값을 축약하고 **해당 항목에 축약 사실을 표시**한다. 축약 여부를 표시하지 않은 축약 값을 회신하지 않는다.

### B.3 읽기 전용 경계 (협상 불가)

- **REQ-INTROSPECT-009** [Ubiquitous] — 두 동사의 처리 경로 **shall** 읽기 전용이다: `Cmd()`를 호출하지 않고, 열거·판독 과정에서 발견된 **함수 타입 필드를 호출하지 않으며**, 쇼파일을 변경하지 않는다.
- **REQ-INTROSPECT-010** [Unwanted] — 두 동사 **shall not** `exec`/`deploy` 계열의 실행 경로와 공유 분기를 갖는다. 회신은 읽기 계열 주소(`state`/`prop`과 동일한 상태 회신 주소)로만 나간다.
- **REQ-INTROSPECT-011** [Ubiquitous] — 필드 판독은 **전부 pcall 방어**된다. 알려지지 않은 이름에 대한 판독 실패는 정상 경로이며 회신을 중단시키지 않는다.

### B.4 가산성·예산·절단 신호

- **REQ-INTROSPECT-012** [Ubiquitous] — 응답기 확장 **shall** 가산적이다: 기존 동사 5종(`ping`/`state`/`prop`/`exec`/`deploy`)과 기존 회신 kind 6종의 형상은 무변경이며, **와이어 프로토콜 버전은 1을 유지**한다. (선례: v1.1.0의 `deploy`, v1.5.0의 `prop` — 둘 다 가산 추가 후 `PROTOCOL.md` 상단 Revision note에 기록하고 버전 1 유지.)
- **REQ-INTROSPECT-013** [Event-driven] — **When** 회신 페이로드가 예산을 초과하면, the 응답기 **shall** 항목 집합을 축소하고 **축소 사실을 신호로 드러낸다.**
- **REQ-INTROSPECT-014** [Unwanted] — 응답기 **shall not** 축소 신호 없이 축소된 목록을 회신한다. **조용한 절단은 금지**다.
- **REQ-INTROSPECT-015** [Ubiquitous] — `introspect` 회신 **shall** 축소 이전에 관측한 **전체 필드 수**를 담는다 — 소비자가 몇 개가 누락되었는지 계산할 수 있어야 한다. (`state`의 `node.childCount`가 `children` 캡과 무관하게 실제 총계를 나르는 것과 동일한 계약.)
- **REQ-INTROSPECT-016** [Ubiquitous] — 요청 측 예산 **shall** 서버 빌더에서 강제된다: `props`의 이름 목록은 개수 상한과 인코딩 길이 상한을 가지며, 상한을 넘는 요청은 **송신 전에 거부**된다. (요청은 MA3 커맨드 라인을 타고 나가며 그 한계는 실측 2048바이트다 — `server/tests/test_lua_responder_payload_budget.py`가 이미 고정한 상수.)

### B.5 민감정보 경계

- **REQ-INTROSPECT-017** [Unwanted] — 본 SPEC **shall not** 한 요청으로 **모든 필드의 값**을 돌려주는 모드를 제공한다. 값은 호출자가 이름을 명시한 것만 나간다.
- **REQ-INTROSPECT-018** [Ubiquitous] — 감사 로그 항목 **shall** 경로와 요청된 이름만 담으며, **판독된 값을 담지 않는다.** (기존 `property_query` 감사 항목이 `f"{path} {property_name}"`을 주체로 쓰는 것과 동일한 수준 — 값은 감사 대상이 아니다.)

### B.6 발견 산출물 (이 SPEC의 실질적 가치)

- **REQ-INTROSPECT-019** [Event-driven] — **When** 자기진단 능력이 라이브로 검증되면, the SPEC **shall** 그 능력을 **Executor 핸들과 Sequence 핸들**에 실제로 적용하고, 관측된 필드 목록(또는 `props` 일괄 판독 기록)을 증거로 기록한다.
- **REQ-INTROSPECT-020** [Ubiquitous] — REQ-INTROSPECT-019의 기록 **shall** *"실행 여부·진행률에 해당하는 필드가 발견되었는가"*에 대해 명시적 결론을 남긴다. **"발견되지 않았다"도 유효한 결론**이며, 그것은 후보 추측이 만들 수 없었던 종류의 증거다.
- **REQ-INTROSPECT-021** [Unwanted] — 본 SPEC **shall not** REQ-INTROSPECT-019/020의 관측 결과를 소비하는 기능(재생 상태 표시, 진행률, 페이드 잔여시간)을 구현한다 — §D.

### B.7 소비 경로 규율

- **REQ-INTROSPECT-022** [Ubiquitous] — 서버측 소비 경로 **shall** 기존 게이트 소유 포트 규율을 따른다: 좁은 포트 프로토콜 → 게이트 구현 → 콘솔 링크. 오케스트레이터/세이프티 모듈의 OSC 브리지 import 경계는 **기준선 대비 무변경**이어야 한다.
- **REQ-INTROSPECT-023** [Ubiquitous] — 1 송신 = 1 감사 항목 규율 **shall** 유지된다: 타임아웃으로 실패한 조회도 OSC 요청을 이미 **보냈으므로** 감사에 남는다(기존 `_query_state`/`_query_property`와 동일).
- **REQ-INTROSPECT-024** [Unwanted] — 본 SPEC **shall not** LLM 대면 툴을 추가한다. 닫힌 툴 집합은 **18개**로 유지된다. v1의 소비자는 개발자·에이전트용 진단 경로이며, 쇼 진행 중 모델이 쇼파일을 훑는 표면을 열지 않는다. (기록된 결정 — §F D-4.)

### B.8 배포·문서 동기화

- **REQ-INTROSPECT-025** [Event-driven] — **When** 응답기가 변경되면, the 변경 **shall** `M.VERSION` 범프(base는 `1.5.0`)와 `console/lua/PROTOCOL.md` 상단 Revision note 추가를 동반한다 — 기존 4개 Revision note와 동일한 형식. **도달 버전 번호를 이 요구에 고정하지 않는다**: 소인으로 인한 추가 범프가 정당하며, 리터럴을 박으면 그것이 요구 위반으로 읽힌다(2026-08-03 실측).
- **REQ-INTROSPECT-026** [Ubiquitous] — Python 트윈(`server/bridge/protocol.py`) **shall** 두 동사의 요청 빌더를 제공하며, 기존 빌더들과 동일한 검증 규율(요청 id 토큰, 큰따옴표 금지, 단일 라인)을 적용한다.

## C. 환경 및 전제 (Environment / Assumptions)

### C.1 환경

- **대상 환경**: grandMA3 onPC 2.4.2, 앱과 콘솔 동일 머신 로컬 공존. OSC는 `127.0.0.1` UDP. site config(`osc_slot`, `receive_port`, `reply_port`)는 항상 effective 값에서 읽는다 — 하드코딩 금지.
- **기준선**: base `origin/main` = `3176900`. 응답기 `M.VERSION = "1.5.0"`, `M.PROTO = 1`. `CONFIG.max_children = 24`, `CONFIG.max_payload = 1900`. 닫힌 툴 집합 **18개**. 이 4개 수치는 본 세션에서 base 트리 직접 판독으로 확인했다.
- **기술 스택**: 기존 스택 그대로. **신규 런타임 의존성 0.** Lua 측도 기존 grandMA3 Lua API 표면 안에서 해결한다.
- **콘솔측 변경 대상**: `console/lua/copilot_responder.lua`. 배포 루프(§A.5) 필요.
- **run-phase 기준선 재측정 의무**: run-phase 킥오프 시점에 신선한 pytest/vitest 기준선을 재측정한다 — 본 plan-phase 세션의 수치를 그대로 재사용하지 않는다(baseline-integrity).

### C.2 검증 천장 (먼저 적는다)

- **Printf/Echo는 콘솔 GUI에서 보이지 않는다.** 응답기 자신의 `M.log`조차 이 이유로 짧은 평문만 다루도록 제한되어 있다. 따라서 M1 프로브의 증거 채널은 **OSC 왕복** 또는 **`Store Macro` + 라벨/프로퍼티 재조회**뿐이다.
- **효과와 발화는 다르다.** 이 SPEC은 값 판독만 다루므로 "발화했으나 효과 미상" 축은 좁지만, **열거 결과의 정확성**은 콘솔이 스스로 신고하지 않는다 — 그래서 REQ-INTROSPECT-004의 교차 확인 게이트가 유일한 그물이다.
- **미지 이름에 대한 콘솔의 응답은 비변별적일 수 있다.** SPEC-COPILOT-SCENE-001 M0 실측(2026-08-01)이 남긴 사실: 존재하지 않는 store 플래그 `/CueOnlyy`가 `ok`를 받고 저장까지 됐다. 즉 **콘솔의 `ok`가 항상 "그 이름을 이해했다"를 뜻하지는 않는다.** `props`의 이름별 `ok`를 "그 프로퍼티가 실재한다"로 읽으면 안 되며, `ok=true`는 오직 *"판독 시도가 값을 돌려주었다"*다. 이는 실제로 관측된 함정이다 — Executor 핸들의 `Index`가 `ok=true`에 값 `'function: 0x...'`이었던 것이 같은 계열이다.

### C.3 미확인 전제 (ASSUMPTION — 저장소 전역 카운터 계승, 최고 사용 번호 45 다음)

| # | 전제 | 상태 | 확정 마일스톤/방법 |
|---|---|---|---|
| **ASSUMPTION-46** | MA3 2.4.2의 오브젝트 핸들에서 **필드 이름 집합을 열거하는 경로가 하나라도 존재한다** (메타테이블 `__index` 테이블 순회, `__pairs` 메타메서드, 카운트+이름 접근자 쌍, 덤프 반환값 중 어느 하나). | **미검증** — 룰북에 문서 0건, 저장소 내 선례 0건 | **M1** 라이브 프로브. 부정이면 `introspect` DESCOPE(§A.4) |
| **ASSUMPTION-47** | 열거원이 존재할 경우, 그 결과가 **REQ-INTROSPECT-004의 교차 확인 게이트를 통과한다** (`prop`으로 독립 확인된 이름을 전부 포함). | **미검증** | **M1** — 동일 프로브에서 `prop` 대조군과 교차 대조 |
| **ASSUMPTION-48** | 프로브 플러그인이 `SendOSCMessage`로 **자신의 회신을 서버에 직접 보낼 수 있다** (응답기가 그 API를 쓰는 것과 동일한 플러그인 컨텍스트). | **미검증**(응답기 선례로부터의 추론) | **M1** — 실패 시 `Store Macro` + 재조회 채널로 폴백(쇼파일 쓰기 발생 → 사용자 GUI 삭제 필요) |
| **ASSUMPTION-49** | 임의의 미지 이름에 대한 필드 판독(`handle[name]` / `handle:Get(name)`)이 **부작용 없이** 실패하거나 값을 돌려준다 — 판독 자체가 콘솔 상태를 바꾸지 않는다. | **미검증**(기존 `prop`이 22회 수행하고 부작용이 관측되지 않았다는 간접 증거만 있음) | **M1** — 판독 전후 대상 오브젝트 재조회로 무변화 확인 |
| **ASSUMPTION-50** | `props`의 이름 목록 상한 하에서 요청 커맨드 라인이 **2048바이트 한계 안에 들어간다.** | **부분 검증** — 한계값 2048은 실측 고정, 상한 설계값은 미검증 | **M3** 산술 고정 테스트 + **M6** 라이브 최대 길이 요청 |
| **ASSUMPTION-51** | 열거 결과가 **핸들 클래스마다 안정적이다** (같은 클래스의 서로 다른 인스턴스가 같은 필드 집합을 신고한다). | **미검증** | **M7** — 최소 2개 인스턴스 대조. 불안정하면 그 사실 자체를 기록하고 "클래스 단위 일반화 금지"를 후속 SPEC에 인계 |
| **ASSUMPTION-52** | Executor 또는 Sequence 핸들에 **실행 여부·진행률에 해당하는 필드가 존재한다.** | **미검증 — 그리고 본 SPEC은 이것이 참임을 요구하지 않는다** | **M7** — 참/거짓 어느 쪽도 유효한 산출물(REQ-INTROSPECT-020) |

## D. 제외 범위 (Out of Scope)

### Out of Scope — 재생 상태·진행률 기능

- 실행기가 재생 중인지, 진행률이 얼마인지, 페이드 잔여시간이 얼마인지를 **표시·판정·소비하는 기능.** 본 SPEC은 그 정보가 존재하는지를 판정할 **도구**만 만든다(REQ-INTROSPECT-021). 판정 결과를 소비하는 것은 후속 SPEC의 몫이며, 그 후속 SPEC은 본 SPEC의 §M7 산출물을 입력으로 받는다.

### Out of Scope — LLM 대면 툴 추가

- 자기진단 능력을 모델의 툴로 등재하는 것. 닫힌 툴 집합은 **18개**로 유지된다(REQ-INTROSPECT-024, 결정 D-4). v1 소비자는 개발자·에이전트용 진단 경로다.

### Out of Scope — 전 필드 값 일괄 덤프

- 한 요청으로 모든 필드의 **값**을 돌려주는 모드(REQ-INTROSPECT-017). 페이로드 예산과 민감정보 경계 양쪽에서 방어할 수 없다.

### Out of Scope — 프로퍼티 쓰기

- `Set`/할당 계열 동사. 본 SPEC은 읽기 전용이다(REQ-INTROSPECT-009). 쓰기는 기존 `exec` 경로가 게이트를 통과해 수행하는 영역이며, 본 SPEC이 그 경계를 건드리지 않는다.

### Out of Scope — `state`의 무페이징 계약 변경

- `PROTOCOL.md` §4.2가 명시한 *"페이징은 없다"* 계약과 그 우회책(슬롯별 개별 조회)을 바꾸는 것. 본 SPEC은 신규 동사에 대해서만 절단 신호와 총계를 정의하며, 기존 `state` 회신의 형상·의미론은 무변경이다.

### Out of Scope — cue_monitor 현행 경로 변경

- `server/web/cue_monitor.py`의 `CurrentCue` 판독 경로(Sequence 핸들 경유, 라이브 검증됨)를 바꾸는 것. 그 경로는 이미 실측으로 확인된 정답이며, 본 SPEC은 그것을 **재확인할 도구**를 만들 뿐 교체하지 않는다.

### Out of Scope — UI 표면

- `server/web/**`의 라우터·이벤트 형상과 `ui/src/**` 전부. 본 SPEC은 와이어·응답기·포트 계층에서 끝난다.

### Out of Scope — 다른 콘솔 버전 대응

- 2.4.2 이외 버전에서의 열거원 존재 여부. 본 SPEC의 모든 판정은 2.4.2 실측에 한정되며, 버전 일반화를 주장하지 않는다.

### Out of Scope — 다른 오브젝트 클래스의 의미론 해석

- Group/Preset/World/MAtricks 등의 필드가 **무엇을 뜻하는지** 해석하는 것. 본 SPEC은 이름·타입·값을 있는 그대로 나르며, 의미 부여는 하지 않는다(REQ-INTROSPECT-002의 "응답기는 파싱·정규화·의미 추론을 하지 않는다"는 기존 `prop` 계약 계승).

## E. 참조 구현 (연구 근거 — research.md, 구속력 있음)

인용은 base `3176900` 트리 기준이며, 아래 4개 파일은 본 세션에서 **워킹 트리와 base가 바이트 동일**함을 확인했다. 줄번호는 마일스톤 착수 직전 재실측한다 — 심볼 앵커가 정본이다.

| 필요 패턴 | 참조 원본 |
|---|---|
| 동사 디스패치(정확 일치, 신규 분기 추가 지점) | `console/lua/copilot_responder.lua` `M.handle_request` (`parsed.kind == ...` 연쇄, ~876-958행) |
| 단일 프로퍼티 판독의 2단 시도 사다리 | 같은 파일 `M.safe_property` (~204-217행) — `handle:Get(name)` → `handle[name]`, 둘 다 pcall |
| **정합 집합 전량 채택/전량 폐기 규율**(REQ-INTROSPECT-004의 선례) | 같은 파일 `SLOT_PROBES`(~269-275행) + `M.probe_slots`(~314-335행) — "반쯤 믿는 numbering은 그럴듯한 오답이 새어 나가는 경로" |
| 페이로드 예산 축소 루프 + 절단 신호 | 같은 파일 `M.build_snapshot` 말미 size guard(~634-639행), `CONFIG.max_payload = 1900`(~39행) |
| 회신 인코딩(percent-encoded JSON, 콤마/따옴표 free) | 같은 파일 `M.encode_payload` / `M.percent_encode`(~139-150행) + `PROTOCOL.md` §3 |
| 회신 전송 변형 사다리(모든 변형 시도, `cmd_keyword` 최후) | 같은 파일 `M.send_reply`(~840-872행) + `PROTOCOL.md` §5 |
| 가산 추가 선례(버전 1 유지 + Revision note) | `console/lua/PROTOCOL.md` 상단 Revision note 4건(1.5.0 `prop`, 1.3.0, 1.2.0, 1.1.0 `deploy`) |
| 요청 빌더 검증 규율 | `server/bridge/protocol.py` `_validate_request_id` / `_validate_rest` / `build_prop_query` |
| 좁은 포트 프로토콜 분리 근거 | `server/orchestrator/ports.py` `PropertyQueryPort` docstring — *"소비자가 필요한 능력만 정확히 선언하게 한다"* |
| 콘솔 링크 왕복(동일 id 상관, 동일 타임아웃 예산, 동일 예외 타입) | `server/safety/console.py` `ConsoleLink.query_property` |
| 1 송신 = 1 감사 항목 규율 | `server/safety/gate.py` `_query_state` / `_query_property` |
| 판독 실패를 포착하되 전파하지 않는 소비 패턴 | `server/prechk/query.py` `read_properties` — *"하나의 판독 실패가 판독 가능한 것들을 버리게 해서는 안 된다"* |
| 후보 소진 오판의 흔적(본 SPEC의 동기) | `server/web/cue_monitor.py` `CURRENT_CUE_PROPERTY_CANDIDATES`의 `@MX:ANCHOR`/`@MX:REASON` |
| 커맨드 라인 2048 한계 고정 | `server/tests/test_lua_responder_payload_budget.py` `MA3_COMMAND_LINE_LIMIT = 2048` |
| lupa 기반 Lua 테스트 하네스(실제 플러그인 파일 로드) | `server/tests/lua_mock_env.py` |
| 배포 패키징(네이티브 인라인 Base64 XML) | `server/deploy/pack.py`, `server/deploy/provisioning.py` `install_responder` |

## F. 결정 기록 (재질의 금지)

| # | 결정 | 근거 |
|---|---|---|
| **D-1** | 동사를 **2개로 분리**한다(`introspect` 열거 / `props` 일괄 판독). 단일 동사에 선택적 이름 목록을 붙이지 않는다. | 요청 문법 모호성(§A.3) — `Executor 80` 같은 공백 포함 경로에서 판별 불가. 부수 이익: M1 판정이 `introspect`만 게이트한다. |
| **D-2** | `introspect`는 **이름과 타입만** 회신하고 값은 회신하지 않는다. | 값은 예산을 예측 불가능하게 만들고 민감정보 축을 연다. 타입만으로도 코디네이터가 겪은 함정(`Index` → 함수 포인터)은 즉시 판별된다. |
| **D-3** | `prop`과 `props`의 한 글자 차이를 **테스트로 봉쇄**한다(이름을 바꾸지 않는다). | 디스패치는 정확 일치이므로 기계적 위험은 없다. 사람의 오독 위험은 회귀 테스트(`props` 요청이 `prop` 분기로 가지 않고, 그 역도 아님)와 `PROTOCOL.md` §2 인접 배치로 봉쇄한다. 이름 변경은 어휘를 더 늘릴 뿐이다. |
| **D-4** | **LLM 툴을 추가하지 않는다.** 닫힌 툴 집합 18개 유지. | v1 소비자는 발견을 수행하는 개발자·에이전트다. 쇼 진행 중 모델이 임의 핸들을 훑는 표면을 여는 것은 별개 결정이며 별개 SPEC에서 다룬다. 툴 개수는 어느 쪽이든 AC로 고정된다. |
| **D-5** | 열거원 채택은 **전량/전무**이며 부분 채택하지 않는다. | `M.probe_slots` 선례. 그럴듯한 부분 열거는 "없다"의 오판을 만드는 정확히 그 재료다 — 본 SPEC이 없애려는 결함을 새 표면에서 재생산하게 된다. |
| **D-6** | M1 NEGATIVE 시 `props`만 출하하며, 이를 **정직한 부분 성공**으로 기록한다. | EXECREF-001 → EXECBODY-001 규율 계승. `props` 단독으로도 22회 → 1~2회이며 "없다"의 근거가 기록 가능해진다. |
| **D-7** | 프로브 증거 채널은 **OSC 직접 회신 우선, 매크로 라벨 폴백**. | 매크로 경로는 쇼파일 쓰기를 발생시키고, `Delete`가 블랙리스트라 사용자 GUI 정리를 요구한다(SCENE-001 M0가 시퀀스 7개를 남긴 선례). 쓰기 0이 가능하면 그쪽이 옳다. |
