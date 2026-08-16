---
id: SPEC-COPILOT-PRESETGUARD-001
title: "Position 프리셋 덮어쓰기 가드 · 저장 확인 · 재생성 경로 (Preset Guard)"
version: "0.1.0"
status: draft
created: 2026-08-16
updated: 2026-08-16
author: manager-spec
priority: P1
phase: "Phase 2 안전 계층 — 비가역 쓰기 가드"
module: "server/web/session.py (_basic_position_presets · 프리셋 풀 판독 헬퍼 · 신설 재생성 핸들러), server/tests/test_web_session.py"
lifecycle: spec-anchored
tags: "preset-overwrite, irreversible-write, fail-closed, read-back-verification, regeneration, refocus, position-pool, unobserved-completion"
tier: M
related_specs: [SPEC-COPILOT-SPATIAL-001, SPEC-COPILOT-WRITEGATE-001, SPEC-COPILOT-TRUNCATE-001, SPEC-COPILOT-SONGCUE-001]
---

# SPEC-COPILOT-PRESETGUARD-001 — Position 프리셋 덮어쓰기 가드

> **이 SPEC이 닫는 구멍 셋**:
> ① **가장 안전해 보이는 경로에 가드가 없다.** 사용자가 번호를 명시하면(`"21번부터"`) 점유 검사가 **한 번도 실행되지 않는다.** 번호를 명시하지 않았을 때만 빈 구간을 찾는다.
> ② **저장 결과를 되읽지 않는다.** 저장 루프는 `run_commands`를 던지고 *"저장 요청했습니다"* 라고 보고한다. 풀을 다시 읽는 코드가 없다.
> ③ **재생성 입구가 없다.** 프리셋을 다시 만들면 그것을 참조하는 모든 큐가 재조준된다 — 이 원리는 코드 주석에 적혀 있으나, 그 일을 수행하는 핸들러는 존재하지 않는다.
>
> **왜 이것이 중대한가**: `Store Preset 2.n`은 점유 슬롯을 **경고 없이** 덮어쓴다. 이 앱에는 undo가 없고, restore 경로가 없으며, `Delete`는 블랙리스트다. **덮어쓴 프리셋은 사라진다.**
>
> **가설이 아니라 코드다**: `_basic_position_presets`(`server/web/session.py:2800`)의 분기(`:2820`)가 `start_no`를 그대로 받고, 점유 검사 헬퍼 `_position_preset_free_starts()`(`:4536`)는 **else 갈래에서만** 호출된다. 두 헬퍼는 이미 존재하고 이미 동작한다 — **호출되지 않을 뿐이다.**

## A. 배경

### A.1 무엇이 이미 작동하는가 (건드리지 않는다)

| 절 | 상태 | 근거 |
|---|---|---|
| Position 풀 **판독** | ✅ 건강 | `_position_preset_pool_slots()`(`session.py:4505`)가 `DataPool/PresetPools/2`를 조회해 점유 슬롯 집합 또는 `None`(판독 불가)을 낸다 |
| 빈 구간 **탐색** | ✅ 건강 | `_position_preset_free_starts()`(`:4536`) — 10칸 연속 **비어 있는** 시작 번호 |
| 저장된 구간 **탐색** | ✅ 건강 | `_position_preset_ready_starts()`(`:4658`) — 10칸 연속 **저장된** 시작 번호. 오늘은 큐 저장 질문 카드만 쓴다 |
| 물음 채널 | ✅ 건강 | `_ask_one()`(`:6048`) — 한 번에 하나의 결정, 버튼 + 자유 입력 |
| 룩별 독립 번들 | ✅ 건강 | 적용 → `Store` → `Label` → `ClearAll`이 룩마다 별개 `run_commands`(`:2866~`). 한 룩이 거절돼도 나머지 아홉은 산다 |
| 라벨 따옴표 거부 | ✅ 건강 | `position_preset_store_commands()`(`server/spatial/pointing.py:329`)가 `'`·`"`를 담은 라벨에 예외를 던진다 |
| **명시 번호의 점유 검사** | ❌ **오늘 없음** | `session.py:2820~2822` — `start_no = int(start_match.group("no"))`, 그걸로 끝이다 |
| **저장 결과 되읽기** | ❌ **오늘 없음** | 루프 종료 후 풀 재판독 **0회** |
| **재생성 입구** | ❌ **오늘 없음** | `_basic_position_presets`는 언제나 **새** 시작 번호를 묻고 새로 저장한다 |

즉 이 SPEC은 *"판독을 못 한다"* 를 고치는 것이 **아니다.** 판독은 정확하고 이미 있다. **판독이 위험한 경로에서 호출되지 않는다**를 고친다.

### A.2 결함의 형상 — 가드가 정확히 뒤집혀 있다

```
번호를 안 줬다  → 빈 구간 탐색(_position_preset_free_starts) → 검증된 후보 제시 → 저장   ← 가드 있음
번호를 줬다     →                    (아무 검사도 없음)                        → 저장   ← 가드 없음
```

운영자가 *더 확신을 갖고 행동한 쪽* — 번호를 직접 지목한 쪽 — 이 **보호받지 못한다.** 오타 한 글자(`"21번부터"` → `"2번부터"`)가 열 개 슬롯을 지운다.

### A.3 이 저장소는 이미 "쓰기 전에 되읽는다"를 규율로 갖고 있다

좌표 쓰기 경로 `arrange_fixtures`(`server/orchestrator/tools.py:5318~`)는 **원좌표를 전수 백업하고**(`:5566~`) 백업 실패 시 **아무것도 쓰지 않으며**(`:5606~5613`), 쓰기 후 **재조회로 판정한다.** 같은 파일이 패치 경로에도 같은 규율을 적는다 — *"성공은 관측에서만 나온다"*(`tools.py:3724`), *"실행은 했으나 재조회에 실패했다 — 몇 대가 생겼는지 **모른다**"*(`:3941`).

**프리셋 저장만 요청을 완료로 보고한다.** 그리고 프리셋 저장은 좌표 쓰기와 달리 **백업이 원리적으로 불가능하다** — 프리셋 내용을 되읽어 재기록할 경로가 없다. 백업할 수 없는 쓰기가 확인조차 하지 않는 것이 이 SPEC의 ②다.

> 이 프로젝트는 *"요청했다"*를 *"착지했다"*로 취급하는 대가를 이미 한 번 치렀다(SPEC-COPILOT-WRITEGATE-001, 여전히 in-progress).

### A.4 재생성이 왜 세 번째 요구인가 — 참조의 값

`position_preset_store_commands`의 독스트링(`pointing.py:329~336`)이 원리 전체를 적는다:

> *"Run AFTER the aim bundle, while the values still sit in the programmer — cues built from the preset then hold a REFERENCE, so regenerating the preset re-focuses every cue that uses it."*

큐가 참조를 들고 있다는 것은 **프리셋 하나를 다시 만들면 그것을 쓰는 모든 큐가 따라온다**는 뜻이다. 새 공연장, 리그 재배치, 장비 이동 — 전부 큐를 한 개도 건드리지 않고 해결된다. **그런데 그 재생성을 수행하는 핸들러가 없다.** 오늘 할 수 있는 유일한 일은 *다른* 번호에 새로 저장하는 것이고, 그러면 기존 큐는 **옛 좌표를 계속 가리킨다.**

`_position_preset_ready_starts()`는 이미 *"10칸 연속 저장된 구간"* 을 찾는다 — 재생성이 필요로 하는 바로 그 입력이다. 오늘은 큐 저장 질문 카드만 이 헬퍼를 쓴다.

### A.5 셋을 함께 출하하는 이유 — 카드 하나, 호출자 둘

REQ-1(명시 번호 충돌)과 REQ-3(재생성)은 **같은 결정**을 운영자에게 묻는다: *"2.21~2.30에 있는 것을 덮어씁니다. 진행할까요?"* 차이는 의도뿐이다 — REQ-1에서 충돌은 **사고 가능성**이고, REQ-3에서 충돌은 **목적 그 자체**다. 판정 로직은 동일하다.

> **그러므로 확인 카드는 하나로 설계하고 호출자를 둘 둔다.** 카드를 둘로 나누면 문면이 갈라지고, 한쪽만 fail-closed가 되는 드리프트가 생긴다.

## B. 요구 (GEARS)

### B.1 점유 가드 — 명시 번호도 검사받는다

- **REQ-PRESETGUARD-001** [Event-driven] — **When** 기본 포지션 저장이 시작 번호 `N`을 확정하면, the 핸들러 **shall** `_position_preset_pool_slots()`를 판독해 구간 `2.N … 2.N+9`의 **충돌 집합**을 계산한다. 검사는 `start_no`가 **확정된 시점**에 걸리며 그 값의 출처(명시 번호 / 질문 카드 응답 / 자유 입력)를 구별하지 않는다.
  - **왜 출처 무관인가**: 질문 카드는 제안 버튼 외에 **자유 입력을 항상 제공한다**(`_ask_one` 독스트링, `session.py:6060`). 따라서 else 갈래에서 운영자가 손으로 타이핑한 번호는 명시 번호 경로와 **정확히 같은 정도로 무방비**다. 가드를 if 갈래 안에 두면 이 구멍이 남는다.
- **REQ-PRESETGUARD-002** [Event-driven] — **When** 충돌 집합이 비어 있지 않으면, the 핸들러 **shall** 확인 카드를 **한 번** 띄우고, **긍정 응답 없이는 그 구간에 대해 `Store Preset` 명령을 단 하나도 디스패치하지 않는다.** 카드는 **어느 슬롯이 사라지는지 번호로 열거한다** — *"이미 있는 번호는 덮어씁니다"* 같은 총칭 경고는 이 요구를 만족하지 않는다.
- **REQ-PRESETGUARD-003** [Unwanted] — the 확인 카드 **shall not** 무응답을 승낙으로 해석한다. `_ask_one()`이 `None`을 내면(UI 미연결 **또는** 타임아웃/연결 끊김 — `session.py:6065~6067`) the 핸들러 **shall** 저장을 수행하지 않고 그 사유를 회신에 적는다. **침묵은 동의가 아니며 손실은 복구 불가다.**
  - **기존 카드와의 대비**: 시작 번호 카드의 `None`은 *질문 한 번의 비용*이다. 이 카드의 `None`은 *운영자의 프리셋*이다. 같은 반환값이 다른 무게를 갖는다.
- **REQ-PRESETGUARD-004** [Event-driven] — **When** `_position_preset_pool_slots()`가 `None`(판독 불가)을 내면, the 핸들러 **shall** 오늘의 동작대로 저장을 진행하되 **점유를 확인하지 못했음을 회신에 명시한다.** the 핸들러 **shall not** 판독 불가를 *"충돌 없음"* 으로 접는다 — **미상과 검증된-빈칸은 다른 상태**이며 회신은 둘을 구별해야 한다.
- **REQ-PRESETGUARD-005** [Unwanted] — the 가드 **shall not** 검증된 빈 구간에 카드를 띄운다. 충돌 집합이 비어 있고 풀 판독이 성공했으면 **질문 없이 진행**한다. 마찰은 손실 가능성이 있는 자리에만 놓인다.

### B.2 저장 되읽기 — 요청은 완료가 아니다

- **REQ-PRESETGUARD-006** [Event-driven] — **When** 저장 루프가 끝나면, the 핸들러 **shall** Position 풀을 **정확히 한 번** 다시 읽어 기대 슬롯 집합과 대조한다. 재판독은 루프 **밖에서 1회**이며 룩마다 반복하지 않는다(왕복 비용 — §C.1).
- **REQ-PRESETGUARD-007** [Ubiquitous] — the 회신 **shall** 대조 결과를 **산술로** 운반한다: 기대 슬롯 수 · 확인된 수 · **확인되지 않은 슬롯 번호의 열거**. *"저장했습니다"* 나 *"정상 저장됨"* 같은 형용사는 이 요구를 만족하지 않는다. 예: `"2.21–2.30 중 10개 확인"` · `"2.27 미확인"`.
- **REQ-PRESETGUARD-008** [Unwanted] — the 재판독이 `None`을 내면 the 회신 **shall** 그것을 **미검증**으로 보고하며 **shall not** 확인됨으로 보고한다. **판독 불가는 통과가 아니다.**
- **REQ-PRESETGUARD-009** [Event-driven] — **When** 저장 명령이 승인 대기(`proposal`) 또는 차단(`locked` · `blocked` · `rejected`) 상태로 남으면, the 대조 **shall** 그 슬롯의 부재를 **결함이 아니라 미착지로** 분류하고 회신에 그 사유를 구별해 적는다.
  - **왜 이 조항이 필요한가**: 안전 게이트는 명령을 `proposal`로 보류할 수 있다(`server/safety/` 상태값 — `proposal`·`locked`·`blocked`·`rejected`·`ok`·`failed`·`unconfirmed`·`cleared`). 승인 대기 중인 저장은 **당연히** 풀에 없다. 이를 *"저장 실패"* 로 보고하면 정상 워크플로에 거짓 경보가 상시 발생하고, 그 경보는 곧 무시되며, 무시되는 경보는 진짜 미착지도 함께 가린다.
- **REQ-PRESETGUARD-010** [Unwanted] — the 대조 **shall not** 재시도를 유발하거나 회신을 오류 상태로 만들지 않는다. 되읽기는 **보고**이며 자기수정 루프의 입력이 아니다.

### B.3 재생성 — 지금 배치로 다시 잡는다

- **REQ-PRESETGUARD-011** [Event-driven] — **When** 지시가 재생성 의도를 담으면(*"지금 배치로 기본 포지션 다시 잡아줘"* 계열), the 핸들러 **shall** `_position_preset_ready_starts()`로 **이미 저장된 10칸 연속 구간**을 찾아 그 자리를 표적으로 삼는다. **새 시작 번호를 묻지 않는다** — 새 자리에 저장하면 기존 큐가 옛 좌표를 계속 가리키므로 재생성이 성립하지 않는다.
- **REQ-PRESETGUARD-012** [Event-driven] — **When** 표적 구간이 확정되면, the 핸들러 **shall** REQ-PRESETGUARD-002가 도입하는 **동일한 확인 카드**를 통과시킨 뒤에만 저장한다. 재생성에서 덮어쓰기는 **의도된 것**이나 *어느 구간을* 덮어쓰는지는 여전히 운영자의 결정이다. REQ-PRESETGUARD-003의 fail-closed 규칙이 **동일하게** 적용된다.
- **REQ-PRESETGUARD-013** [Event-driven] — **When** `_position_preset_ready_starts()`가 빈 목록을 내거나(저장된 10칸 구간 없음) 후보가 **둘 이상**이면, the 핸들러 **shall** 어느 구간인지 묻고 **shall not** 추측한다. 풀 판독 자체가 `None`이면 **저장하지 않고 사유를 회신한다** — 재생성은 표적 구간의 존재를 전제로 하므로, 미상 위에서 진행할 수 없다.
- **REQ-PRESETGUARD-014** [Ubiquitous] — the 재생성 **shall** 열 개 룩을 **현재 리그 좌표에서 다시 계산한다**(기존 `_read_pointing_coordinates` → `basic_position_presets(fixtures)` 경로 재사용). the 재생성 **shall not** 큐·시퀀스를 읽거나 쓰지 않는다 — 참조를 든 큐는 프리셋 갱신만으로 따라온다(§A.4).
- **REQ-PRESETGUARD-015** [Event-driven] — **When** 한 지시가 재생성 트리거와 기존 신규-저장 트리거에 **동시에** 걸리면, the 디스패치 **shall** 재생성 핸들러로 라우팅한다. 우선순위는 **등록 순서로 강제**되며 테스트로 고정된다.
  - **왜 배제가 아니라 우선순위인가 (실측)**: 기존 `_BASIC_POSITIONS_REQUEST`(`session.py:1579`)는 `(?:기본|…)…(?:포지션|…).*?(?:저장|만들|**잡아**|생성)`이며, `잡아`가 이미 대안에 있다. 재생성 문장 *"기본 포지션 다시 잡아줘"* 를 **이 정규식이 매치한다** — 2026-08-16 직접 실행으로 확인(4개 후보 문장 전건 `True`). 따라서 **두 트리거의 교집합은 공집합이 아니며**, 공집합으로 만들려면 이미 출하된 트리거를 좁혀야 한다(기존 매치 퇴행 위험). 본 요구는 교집합을 없애는 대신 **겹치는 입력의 행선지를 결정적으로 고정**한다.

### B.4 범위 봉쇄

- **REQ-PRESETGUARD-016** [Unwanted] — the 개정 **shall not** 새 툴을 신설하거나 폐쇄 툴 집합을 변경한다. 본 SPEC은 **세션 계층 동작**이며 기존 툴(`query_state` · `run_commands` · `get_spatial_context`)과 기존 풀 판독 헬퍼 위에서만 성립한다.
- **REQ-PRESETGUARD-017** [Unwanted] — the 개정 **shall not** `server/spatial/**`를 변경한다. 해당 계층은 **순수 기하**이며 콘솔을 읽지 않고 풀 점유·판독 완전성을 알지 못한다. 점유 판정과 확인 카드는 전부 `server/web/session.py`에 산다. `pointing.py` 변경이 불가피하다고 판단되면 **그 자체를 블로커로 보고**하고 근거를 제시한다.
- **REQ-PRESETGUARD-018** [Unwanted] — the 개정 **shall not** `server/orchestrator/tools.py`를 변경한다. `server/tests/test_songcue_bundle.py`가 해당 파일의 **diff hunk 위치를 고정**하고 있어(트립와이어) 무심한 편집이 무관한 테스트를 깨뜨린다. 불가피하면 그 핀을 **재실측**해야 하며, 이는 범위 확대로 취급한다.
- **REQ-PRESETGUARD-019** [Unwanted] — the 개정 **shall not** 기존 안전 동작을 퇴행시킨다: 룩별 독립 번들(적용 → `Store` → `Label` → `ClearAll`) 유지 · `/Merge`·`/Overwrite` 플래그 **영구 금지** · 라벨의 따옴표 거부 유지 · 좌표 판독 실패 시 거부 유지.
- **REQ-PRESETGUARD-020** [Unwanted] — the 개정 **shall not** 새 MA3 문법을 도입한다. 사용하는 명령은 전부 이미 라이브 검증된 것(`Store Preset 2.n` · `Label Preset 2.n '<text>'` · `ClearAll` · `query_state`)이다. **따라서 실기 콘솔 세션이 필요 없다** — 하드웨어 일정을 잡지 않는다.

## C. 환경 및 전제

### C.1 검증 가능성

| 항목 | 기계 검증 | 수단 |
|---|---|---|
| 명시 번호 충돌 시 `Store Preset` 0건 | **YES** | 단위 — 디스패치된 `ToolCall` 목록에 `run_commands` 부재 |
| 카드가 **사라지는 슬롯 번호**를 열거 | **YES** | 단위 — 카드 프롬프트 문자열에 충돌 슬롯 번호 전건 등장 |
| `_ask_one` → `None`에서 fail-closed | **YES** | 단위 — `_Channel([])`(UNANSWERED) 투입 → 쓰기 0건 |
| 판독 불가 ≠ 충돌 없음 (회신 문면 구별) | **YES** | 단위 — 풀 판독 오류 리그와 검증-빈칸 리그의 회신 문면 상이 |
| 검증된 빈 구간에 카드 미출현 | **YES** | 단위 — `channel.asked == []` |
| 되읽기 산술이 회신에 실림 | **YES** | 단위 — 회신 텍스트에 기대/확인 수 + 미확인 슬롯 번호 |
| 되읽기 불가 → 미검증 보고 | **YES** | 단위 — 재판독 오류 리그 |
| `proposal` 상태의 미착지 분류 | **YES** | 단위 — 스텁 레지스트리가 `proposal` 반환(기존 픽스처가 이미 그렇다) |
| 재생성이 기존 구간을 표적 | **YES** | 단위 — `ready_starts` 리그에서 `Store Preset 2.<기존>` 디스패치 |
| 재생성이 큐/시퀀스를 건드리지 않음 | **YES** | 단위 — 디스패치 명령에 `Store Sequence`·`Cue` 부재 |
| `server/spatial/**` · `tools.py` 무변경 | **YES** | byte-diff |
| **실기 콘솔에서의 최종 동작** | **불필요** | 새 문법 0건(REQ-019) — 기존 검증분만 사용 |

**왕복 비용**: 프리셋 풀 판독은 `query_state` **1왕복**이다. 본 SPEC이 추가하는 왕복은 최대 **2회**(가드 1 + 되읽기 1)이며 저장 10회 × 3~5명령의 기존 부하 대비 무시 가능하다. 재생성 경로도 동일하다.

### C.2 PRESERVE

- `server/spatial/**` — **무변경**(REQ-016). 순수 기하 계층은 콘솔·풀 점유를 모르는 상태로 유지한다.
- `server/orchestrator/tools.py` — **무변경**(REQ-017). `test_songcue_bundle.py` hunk 핀 트립와이어.
- `server/safety/**` — **무접촉**. 본 SPEC은 게이트 판정을 바꾸지 않고 그 **결과를 읽을 뿐**이다(REQ-009).
- `_position_preset_pool_slots` · `_position_preset_free_starts` · `_position_preset_ready_starts` — **시그니처 무변경**. 세 헬퍼는 이미 옳다. 호출자만 는다.
- `position_preset_store_commands` · `aimed_commands` · `basic_position_presets` — **무변경**.
- 시작 번호 질문 카드(else 갈래)와 `_ask_position_preset_start` — **문면 보존**. 새 가드는 그 **뒤에** 놓이며 그것을 대체하지 않는다.
- `console/lua/**` · `server/web/dash.py` · `server/web/panel.py` — 무접촉.

### C.3 ASSUMPTION

레포 전역 최대 사용 id는 **80**이다. 본 SPEC은 **81-85만** 사용한다.

- **ASSUMPTION-81 (풀 판독의 신뢰성)** — `_position_preset_pool_slots()`가 내는 슬롯 집합이 콘솔의 실제 점유와 일치한다. **부분 검증** — 헬퍼는 이미 출하돼 큐 저장 카드에서 쓰이고 있으나, *"저장돼 있다고 보고된 슬롯이 실제로 비어 있는"* 반례는 측정된 적이 없다. NEGATIVE면 가드가 **거짓 충돌**을 만들어 불필요한 카드를 띄운다(안전 방향의 오류 — 손실 없음).
- **ASSUMPTION-82 (`children[].i`의 의미)** — 응답기가 슬롯 번호를 `i`로 보낸다(헬퍼 주석이 PROTOCOL §4.2를 인용). **인수** — 기존 코드의 전제를 그대로 승계하며 본 SPEC은 이를 재검증하지 않는다. 틀렸다면 이미 출하된 큐 저장 카드가 함께 틀린 것이므로 본 SPEC 고유의 위험이 아니다.
- **ASSUMPTION-83 (재생성 트리거의 변별력)** — ~~*"다시 잡아줘"* 계열이 기존 `_BASIC_POSITIONS_REQUEST`와 충돌하지 않는다~~ → **반증됨 (측정, 2026-08-16).** 기존 정규식(`session.py:1579`)의 동사 대안에 `잡아`가 **이미 있어** 재생성 문장을 그대로 매치한다. 직접 실행 결과 후보 4문장(*"기본 포지션 다시 잡아줘"* · *"지금 배치로 기본 포지션 다시 잡아줘"* · *"기본 포지션 프리셋 재생성"* · 기존 저장 문장) **전건 `True`**.
  - **귀결**: 트리거 배제(교집합 공집합화)는 **채택하지 않는다** — 이미 출하된 정규식을 좁히면 기존 매치가 퇴행할 수 있다. 대신 **디스패치 우선순위로 행선지를 고정**한다(REQ-PRESETGUARD-015). 전제가 반증됐으므로 이 조항은 **선택적 방어가 아니라 필수**다.
- **ASSUMPTION-84 (`proposal` 상태의 관측 가능성)** — 저장 명령의 게이트 상태가 `CommandOutcome.status`로 핸들러에 되돌아와 REQ-009의 분류가 가능하다. **코드 확인 완료** — 기존 테스트 스텁이 `CommandOutcome(command="Fixture 20", status="proposal")`을 반환하며 `_basic_position_presets`가 이미 `executed.command_outcomes`를 수집한다(`session.py:2874`).
- **ASSUMPTION-85 (재생성의 운영 수용성)** — 재생성이 후보 구간을 **항상** 확인 카드에 건다(단일 후보여도). **결정됨 (에이전트, 2026-08-16) — 항상 건다.** 근거: 손실이 복구 불가이고, 단일 후보라는 사실은 *"운영자가 그 구간을 의도했다"* 를 증명하지 않는다(다른 쇼의 프리셋일 수 있다). 마찰 1회 대 복구 불가 손실의 비대칭. 저마찰 변형을 원하면 §F 열린 결정 D-2로 승격한다.

## D. 범위 밖 (Out of Scope)

### Out of Scope — 프리셋 내용 백업 · undo · 복원 경로
- 덮어쓰기 **전에 기존 프리셋 내용을 읽어 보관**하고 사후 복원하는 설계는 범위 밖이다. 프리셋 내용(픽스처별 Pan/Tilt 값 집합)을 되읽어 재기록하는 경로가 이 앱에 **없고**, 그것을 만드는 일은 응답기 확장과 별도 SPEC을 요구한다. 본 SPEC은 *"되돌릴 수 있게 만든다"* 가 아니라 *"덮어쓰기 전에 반드시 묻는다"* 만 책임진다.
- 좌표 쓰기(`arrange_fixtures`)가 백업을 갖는 것은 좌표가 **재기록으로 되돌려지기 때문**이다(SPATIAL `progress.md` §0 함정 7). 프리셋에는 그 대칭이 없다.

### Out of Scope — 다른 풀의 덮어쓰기 가드
- Color(4) · Beam · Gobo 등 **다른 프리셋 풀**, 그리고 Group · Macro · Layout 풀의 동종 가드는 범위 밖이다. Position 풀을 먼저 하는 이유는 **거기에 판독 헬퍼 3종이 이미 있고**, 자동 생성 경로(10개 일괄 저장)가 **거기에만** 있기 때문이다. 다른 풀의 동종 결함은 아직 가설이다.
- 본 SPEC이 **확인 카드의 첫 선례를 만들므로**, 후속은 규약을 재발명하지 않고 풀별 판독 헬퍼만 다루면 된다.

### Out of Scope — 시퀀스 · 큐 쓰기 경로
- `Store Sequence` / `Store Cue` 계열의 점유 가드는 범위 밖이다. 해당 경로는 **이미 다른 규율을 갖는다** — `_song_pick_sequence()`(`session.py:4678~`)가 표적 시퀀스를 사전 점유 검사하고 비어 있는 후보를 제안한다. 프리셋 경로에 없는 것이 시퀀스 경로에는 있다.

### Out of Scope — 큐 재조준의 검증
- 프리셋 재생성이 실제로 큐를 재조준하는지 **라이브로 관측하는 일**은 범위 밖이다. 그것은 사람 육안 판정이며(무대 조명이 실제로 움직이는가), 본 SPEC의 성공 기준은 **프리셋이 그 자리에 다시 저장됐다**까지다. 참조 원리 자체는 룰북(`32_spatial_design.md`)과 `pointing.py:329` 독스트링이 이미 기록한 확인분이다.

### Out of Scope — 임의 시작 번호의 빈 구간 제안
- `_position_preset_free_starts()`가 `range(1, 92, span)`만 훑어 **10의 배수 + 1**(1, 11, 21, …)만 제안한다는 사실은 범위 밖이다. 본 SPEC은 제안 품질이 아니라 **확정된 번호의 검사 유무**를 다룬다.

### Out of Scope — 물음 채널의 타임아웃 정책
- `_ask_one()`이 `None`을 내는 두 사유(UI 미연결 / 타임아웃)를 **구별하도록 채널을 개정하는 일**은 범위 밖이다. 본 SPEC은 두 경우 모두 **동일하게 fail-closed**로 처리하므로 구별이 필요하지 않다(REQ-003). 회신 문면이 두 가능성을 함께 적는다.

## E. 성공 기준

**모든 기준은 기계 검증 가능하다** — 라이브 콘솔에 의존하는 항목은 성공 기준에 **없다**(REQ-019).

| 기준 | 확인 수단 | 성격 |
|---|---|---|
| 명시 번호 충돌 시 `Store Preset` 디스패치 0건 | 단위 + 뮤테이션 | **구조** |
| 확인 카드가 사라지는 슬롯을 번호로 열거 | 단위 (프롬프트 문자열) | **구조** |
| `_ask_one` → `None`에서 쓰기 0건 | 단위 + 뮤테이션 | **구조 (fail-closed)** |
| 풀 판독 불가와 검증-빈칸의 회신 문면이 상이 | 단위 (양쪽 짝) | **구조** |
| 검증된 빈 구간에서 카드 미출현 (비공허성) | 단위 | 회귀 |
| 되읽기 산술(기대/확인/미확인 번호)이 회신에 존재 | 단위 + 뮤테이션 | **구조** |
| 되읽기 불가가 확인됨으로 보고되지 않음 | 단위 + 뮤테이션 | **구조** |
| `proposal` 슬롯이 결함이 아니라 미착지로 분류 | 단위 | **구조** |
| 재생성이 기존 저장 구간을 표적 | 단위 | **구조** |
| 재생성이 같은 카드·같은 fail-closed를 통과 | 단위 + 뮤테이션 | **구조** |
| 겹치는 문장이 **재생성으로** 결정적 라우팅 | 단위 + 뮤테이션 | **구조** |
| 재생성이 큐/시퀀스 명령을 내지 않음 | 단위 | **구조** |
| 룩별 독립 번들 · `/Merge` 부재 · 라벨 따옴표 거부 | 기존 회귀 | 회귀 |
| `server/spatial/**` · `tools.py` byte-diff 0 | byte-diff | 회귀 |
| 전체 스위트 무회귀 | `uv run pytest server/tests -q` | 회귀 |

## F. 열린 결정

- **D-1 — 재생성 트리거의 문면.** *"다시 잡아줘"* 외에 어떤 표현을 잡을 것인가(*"재생성"*, *"업데이트"*, *"지금 배치로"*, *"refocus"*). ASSUMPTION-83이 반증돼 **배제가 아니라 우선순위**로 방향이 정해졌으므로(REQ-015), 남은 결정은 어휘 폭뿐이다. **에이전트 판단 가능** — 넓게 잡을수록 신규 저장이 재생성으로 새어들 위험이 커지므로 M3에서 코퍼스로 양방향 고정한다.
- **D-3 — 기존 트리거를 좁힐 것인가.** REQ-015는 우선순위 라우팅을 택했고 `_BASIC_POSITIONS_REQUEST`는 무변경이다. 대안은 기존 정규식에서 `잡아`를 빼거나 *"다시"* 를 부정 전방탐색으로 배제하는 것이며, 이는 **이미 출하된 트리거의 파괴적 변경**이다(*"기본 포지션 잡아줘"* = 신규 저장이 매치되지 않게 된다). **현 결정: 좁히지 않는다 · 사용자 재검토 대상.**
- **D-2 — 단일 후보 구간에서도 카드를 띄우는가.** ASSUMPTION-85에서 *"항상 띄운다"* 로 결정했다. 운영자가 반복 재생성 시 마찰을 호소하면 *"직전 턴에서 확인된 구간은 같은 세션 내 재확인 생략"* 변형이 가능하나, 그것은 **호출 간 상태면**을 새로 만든다. **현 결정 유지 · 사용자 재검토 대상.**

## HISTORY

| 버전 | 날짜 | 변경 |
|---|---|---|
| 0.1.0 | 2026-08-16 | 최초 작성. REQ 19 · ASSUMPTION 81-85 · Out of Scope 6항 · 열린 결정 2건. Tier M. |
