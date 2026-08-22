---
id: SPEC-COPILOT-PARITY-001
title: "가짜 콘솔 ↔ 실물 콘솔 괴리 — D2(핸들↔이름) 정합과 번짐 범위 실측"
version: "0.1.0"
status: draft
created: 2026-08-22
updated: 2026-08-22
author: plan 레인 (칸반 카드 t11)
priority: P1
phase: "카드 t11 — LXSEQ-001 sync 감사가 남긴 blocking 결함 F1(D2)의 처분"
module: "server/prechk/inventory.py (판독 경계), server/lxseq/mapper.py (비교 지점), server/tests/test_lxseq_tool.py (FakeConsole 충실도), server/vwx/ · server/paperwork/ (번짐 후보 — 실측 대상)"
lifecycle: spec-anchored
tags: "fake-console, fidelity, fixture-type, handle, already-patched, fid-occupied, offline-blind-spot, grandma3"
tier: M
related_specs: [SPEC-COPILOT-LXSEQ-001, SPEC-COPILOT-TRUNCATE-001, SPEC-COPILOT-VWX-001, SPEC-COPILOT-PRECHK-001]
---

# SPEC-COPILOT-PARITY-001 — 가짜 콘솔 ↔ 실물 콘솔 괴리: D2 정합과 번짐 범위 실측

> **칸반 카드 t11.** `SPEC-COPILOT-LXSEQ-001` sync 단계의 독립 감사가 남긴 blocking 결함 **F1(D2)** 을 닫는다. D2는 「콘솔에서 읽은 픽스처 타입이 이름이 아니라 핸들 문자열이라, 이름과의 비교가 항상 어긋나 건너뛰기 사유가 틀리게 붙는」 결함이다.
>
> **리드 배차 지시(2026-08-22) — 구속력 있음.** ① SPEC 작성 전용 · 콘솔 무접촉 · 제품 코드 수정 0건. ② 이미 측정된 것은 다시 재지 말고 읽는다(`.moai/probes/t11-d2-probe.md`). ③ 「정방향을 넣으면 초록이 된다」는 **목표이지 전제가 아니다** — AC에 「이미 그렇다」로 적지 않는다. ④ 핸들 형식 `FixtureType <슬롯>` 은 **가정**이며 AC에 명시한다. ⑤ 슬롯 12의 정체는 **추정하지 않는다**. ⑥ 큐 변경은 감독 몫 — 이 SPEC은 카드를 추가하지 않고 제안까지만 적는다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-22 | plan 레인 | 최초 작성(draft, Tier M). REQ **9건**, AC **12건**, 마일스톤 **2개**(M1·M2) + 별도 카드 권고 2건. 리드 배차의 M1/M2 분할을 **재분할**했다 — 근거는 §A.3의 번짐 범위 실측(호출 지점 8곳). 설계 결정 1건(§A.4 결정 A: 번역 지점)은 **대안 채택을 권고**하되 최종 판단을 Kickoff에 남긴다. |

---

## A. 개요

**한 줄**: 콘솔에서 픽스처의 `FixtureType` 속성을 읽으면 실기에서는 **이름이 아니라 핸들 문자열**(`"FixtureType 10"`)이 돌아오는데, 코드는 그 값을 **이름과 직접 비교**한다. 비교가 항상 어긋나므로 「이미 패치됨」 갈래가 실기에서 한 번도 발화하지 않고, 대신 「FID가 이미 있다」로 잘못 분류된다. 출하된 가짜 콘솔은 이 자리에서 이름을 돌려주므로 오프라인 스위트는 이 갈래를 **원리적으로 볼 수 없다**. 이 SPEC은 (M1) 가짜 콘솔에 핸들 갈래를 더해 오프라인에서 잡히게 하고 정방향(핸들→이름) 해석을 넣어 D2를 닫으며, (M2) 같은 값을 소비하는 나머지 지점들이 같은 결함을 갖는지 **실측**한다.

### A.1 결함 D2의 경로 — 이 세션이 코드에서 직접 확인했다

HEAD `0948ccd` 기준, 다섯 마디가 이어져 결함을 만든다. 각 마디는 파일·행으로 지목되며 이 세션이 원문을 읽어 확인했다.

| # | 자리 | 원문 | 무엇을 하는가 |
|---|---|---|---|
| ① | `server/prechk/inventory.py:57` | `PROPERTY_WHITELIST = ("Patch", "FixtureType", "Mode", "Name")` | 픽스처마다 `FixtureType` 속성을 읽는다 |
| ② | `server/prechk/inventory.py:460` | `fixture_type=values["FixtureType"]` | 읽은 값을 그대로 `ConsoleFixture.fixture_type`에 담는다 — **번역하지 않는다** |
| ③ | `server/orchestrator/tools.py:4523` | `(record.patch_raw, record.name, record.fixture_type) for record in inventory.fixtures` | 그 값을 그대로 `Occupant.fixture_type`으로 옮긴다 |
| ④ | `server/lxseq/mapper.py:415` | `console_types[csv_type] = resolution.get("resolved") or csv_type` | 비교의 반대쪽 `console_type`을 만든다 — **이름이다**(근거는 아래) |
| ⑤ | `server/lxseq/mapper.py:325` | `(first.fixture_type or "") == console_type` | **핸들 == 이름**을 비교한다 → 실기에서 항상 거짓 |

④가 이름이라는 것은 이 세션이 독립으로 확인했다: `resolution["resolved"]`는 `server/orchestrator/tools.py:3469` `payload["resolved"] = exact[0]`에서 오고, `exact`는 `[name for name in snapshot.names if name == requested]`(`:3465`)이므로 **라이브러리 이름 목록의 원소**다. 폴백 `csv_type`도 CSV의 `FixtureType` 열, 즉 이름이다. 리드도 같은 결론을 별도로 냈고, 두 판독이 일치한다.

⑤가 거짓이면 제어는 `server/lxseq/mapper.py:341`의 `fid_occupied` 갈래로 떨어진다. 따라서 **실기에서 재실행하면 이미 패치된 86행 전부가 「FID {n}는 콘솔에 이미 있다」로 보고된다** — 사실은 「같은 타입이 같은 자리에 이미 있다 — 이미 패치됨」이다.

### A.2 심각도 — 라벨 결함이지 쓰기 안전 결함이 아니다

**쓰기는 어느 쪽으로 분류되든 0건이다.** `SPEC-COPILOT-LXSEQ-001/progress.md:1003`(감사 F13 정정)이 이를 대조로 확인했다: 라벨을 따라 FID를 바꿔 다시 넣어도 **두 번째 가드(주소 점유)** 가 잡아 86행 전부 `address_occupied`로 건너뛰며 `deploy 0 · exec 0 · 콘솔 불변`이다. 즉 타입 판정과 무관한 가드가 하나 더 있어 중복 리그는 이 경로로 생기지 않는다.

따라서 D2는 **진단 라벨과 사용자 안내가 틀리는 결함**이며, 무대 사고를 만드는 결함이 아니다. 이 구분을 SPEC 앞머리에 두는 이유는 두 가지다 — 심각도를 근거 없이 부풀리지 않기 위해서이고, 「쓰기가 0이니 고칠 필요 없다」로도 넘어가지 않기 위해서다. 조명감독이 재실행 결과를 읽고 「FID가 충돌한다」고 이해하면 있지도 않은 FID 충돌을 해결하려 들 것이고, 그 오해가 손을 움직이게 한다.

**이 결함이 사용자용 문서로 나가지는 않았다** — 같은 §E.4 정정이 README는 정확함을 확인했다(`"Writes stay at zero either way; only the label is wrong."`).

### A.3 번짐 범위 — 이 SPEC이 새로 찾은 것 (호출 지점은 측정, 영향은 미측정)

리드 배차는 D2를 「매퍼에 정방향 해석을 넣는」 문제로 틀 지었다. 그 틀은 ⑤ 한 자리만 본다. 그러나 ②가 만든 값 `ConsoleFixture.fixture_type`을 소비하는 자리는 **매퍼 밖에도 있다.** 이 세션이 `server/` 전역(테스트 제외)에서 세었다:

| # | 자리 | 원문 | 이름을 기대하는가 (판정) |
|---|---|---|---|
| C1 | `server/lxseq/mapper.py:325` | `(first.fixture_type or "") == console_type` | **그렇다 — 확인된 결함(D2 본체)** |
| C2 | `server/vwx/apply.py:503` | `console_type = _resolve_library_type(fixture.fixture_type, library)` | 그럴 것으로 보인다 — **미측정** |
| C3 | `server/vwx/diff.py:113` | `rows.append((fixture.slot, …, fixture.fixture_type))` | 그럴 것으로 보인다(도면 타입명과 대조) — **미측정** |
| C4 | `server/paperwork/data.py:108` | `fixture_type=fixture.fixture_type` | 표시용 — **미측정** |
| C5 | `server/paperwork/render.py:87` | `escape(row.fixture_type or "")` 를 `<td>`에 넣는다 | 표시용, 사람이 읽는 서류 — **미측정** |
| C6 | `server/orchestrator/tools.py:3734` | `"fixture_type": occupant.fixture_type` | 표시용 응답 필드 — **미측정** |
| C7 | `server/prechk/patch.py:236` | `"fixture_type": self.record.fixture_type` | 표시용 — **미측정** |
| C8 | `server/prechk/patch.py:714` | `record.fixture_type is not None and record.mode is not None` | **아니다 — 널 검사뿐**이라 형식과 무관할 것으로 보인다 |

[HARD] **이 표의 오른쪽 칸은 판정이지 측정이 아니다.** 이 세션이 측정한 것은 **호출 지점이 존재한다는 사실과 그 원문**뿐이다. 각 지점이 실기에서 실제로 어긋나는지는 **아무도 재지 않았다.** C1만이 관측으로 뒷받침된다(§A.5의 프로브). 나머지 7건은 「같은 생산자(`read_inventory`)의 같은 필드를 쓴다」는 구조적 사실에서 나온 **가설**이며, 가설을 결함으로 승격하려면 M2의 측정이 필요하다.

이 발견이 설계를 가른다: **번역을 ⑤ 한 자리에만 넣으면 C2~C7이 남고, 같은 수정을 나중에 또 하게 된다.** 그래서 §A.4에 번역 지점을 설계 결정으로 세운다.

### A.4 설계 결정 A — 핸들→이름 번역을 어디서 하는가

세 갈래가 있다.

| 안 | 자리 | 번짐 | 대가 |
|---|---|---|---|
| **A-1 판독 경계** | `server/prechk/inventory.py` — 읽는 즉시 번역해 하류 전체가 이름을 본다 | C1~C7 **동시 해결** | 공용 표면을 바꾼다. `FixtureTypes` 트리 판독이 1회 추가된다. 판독 실패·절단 시 처리를 설계해야 한다 |
| **A-2 툴 경계** | `server/orchestrator/tools.py` — `occupants` 구성 직전에 번역 | C1만 해결 | 파급 최소. C2~C7은 남고 같은 수정을 반복하게 된다 |
| **A-3 비교 지점** | `server/lxseq/mapper.py:325` — 비교 직전에 번역 | C1만 해결 | 대응표를 `build_import_plan`까지 인자로 끌고 가야 한다. 매퍼가 콘솔 판독 개념을 새로 알게 된다 |

**권고: A-1.** 근거 셋 —

1. **번역은 이름 입력에 대해 항등이다.** 값이 이미 이름이면 그대로 돌려주므로, 출하된 가짜 콘솔(이름을 주는 쪽)로 도는 기존 스위트는 **동작이 바뀌지 않는다**. 공용 표면을 건드리는 안치고는 회귀 위험이 낮다.
2. **정방향에 새 판독이 필요 없다.** 슬롯↔이름 대응은 툴이 이미 수행하는 `FixtureTypes` 트리 판독 안에 들어 있고(`server/prechk/mode_read.py:62` `_named_children`가 (슬롯, 이름) 쌍을 이미 뽑는다 — 이 세션이 원문 확인), 라이브 기록에서 이 트리는 `truncated false · listed 15/15`로 온전히 읽혔다.
3. **C2~C7을 가설로 남겨두고 A-2/A-3를 고르면, 나중에 그 가설이 참으로 판명될 때 같은 결함을 세 번째로 만나게 된다.** D1(절단) → D2(핸들) → 다음, 이 SPEC이 다루는 계열이 정확히 그것이다.

**A-1의 대가를 회피하지 않고 적는다**: 트리 판독이 실패하거나 절단되면 대응표가 불완전해진다. 그때 **원값을 그대로 두고 「번역되지 않았다」를 구조화 필드로 남긴다** — 조용히 추측한 이름으로 채우지 않는다(REQ-PARITY-005). 픽스처 열거는 실기에서 19대에서 잘린다는 것이 D1에서 이미 관측됐으므로, 절단은 가상의 위험이 아니다.

[HARD] 이 권고는 리드 배차의 「정방향 해석을 매퍼에 넣고」와 **다르다.** 배차를 조용히 따르지도, 조용히 무시하지도 않는다 — 근거(§A.3의 호출 지점 8곳)와 함께 대안을 세워 두고, **최종 선택은 Kickoff 승인의 몫**으로 남긴다. Kickoff가 A-2를 고르면 REQ-PARITY-004·005는 lxseq 경계로 좁아지고 M2의 결론은 후속 카드 재료가 된다.

### A.5 이미 측정된 것 — 다시 재지 않는다

`.moai/probes/t11-d2-probe.md`(170행, 커밋 `0948ccd`, run 레인 session 71f784af 측정)가 정본이다. 이 SPEC이 재현하지 않고 인용한다.

| 실험 | 관측 |
|---|---|
| A 대조군 — 손대지 않은 `FakeConsole` | `Counter({already_patched: 86})` (원문은 홑따옴표 키) |
| B 변형 — 프로퍼티 판독 한 곳이 핸들을 돌려줌 | `Counter({fid_occupied: 86})` (원문은 홑따옴표 키) |
| C 비공허성 | 판독값이 `ETC S4 LED S3 Lustr X8` → `FixtureType 1` 로 실제 변화 |

여기서 곧바로 따라오는 두 문장을 갈라 둔다.

- **출하된 가짜 콘솔로는 `fid_occupied 86`이 나오지 않는다.** 따라서 오프라인 스위트는 이 갈래를 원리적으로 못 본다 — 가짜에 갈래가 하나 빠져 있다.
- **그러나 이것은 「오프라인이 볼 수 없는 자리」가 아니다.** 갈래를 더하면 잡힌다. 선례가 있다: `server/tests/test_lxseq_tool.py:90` `truncate_at`은 D1을 같은 이유로 오프라인에 끌어들인 생성자 인자이고, 그 주석이 이유를 그대로 적고 있다 — *「절단되지 않는 가짜는 판독 게이트의 한 갈래를 통째로 가리므로(결함 D1이 실기에서야 드러난 이유) 이 변형을 둔다」*.

실기 관측 1건도 인용한다(이 세션이 재현하지 않았다): `SPEC-COPILOT-LXSEQ-001/progress.md:621` — `{"address": "1.1", "name": "KEY 101", "fixture_type": "FixtureType 10"}`.

### A.6 이 SPEC이 하는 것 / 하지 않는 것

| 하는 것 | 하지 않는 것 |
|---|---|
| 가짜 콘솔에 핸들 갈래 추가(선택식, 기본 꺼짐) | 가짜 콘솔을 실물과 전면 일치시키기 |
| 정방향(핸들→이름) 번역과 D2 해소 | 역방향(이름→슬롯) 해소 — `Robin Spiider` 4/12 모호성은 **별개 결정** |
| C2~C8 여덟 자리의 영향 **실측 및 분류** | 실측 결과 드러난 C2~C7 결함의 **수정**(A-1 채택 시 구조적으로 함께 닫히는 부분은 예외) |
| 오프라인 완결 — 콘솔 무접촉 | 실기 확인 · onPC 접속 · 슬롯 12 재판독 |
| 「전수조사 방법 설계」를 별도 카드로 **권고** | 전수조사 자체 · 큐에 카드 추가 |

---

## B. 요구사항 (GEARS)

### 판독 충실도

**REQ-PARITY-001** `[Ubiquitous]`
`FakeConsole`은 픽스처 프로퍼티 판독이 **이름을 돌려주는 갈래**와 **핸들 문자열을 돌려주는 갈래**를 모두 표현할 수 있어야 한다. 갈래 선택은 생성자 인자로 하며 **기본값은 현재 동작(이름)** 이다 — `truncate_at`(`server/tests/test_lxseq_tool.py:90`)과 같은 모양이다.

**REQ-PARITY-002** `[Event-driven]`
핸들 갈래가 켜진 가짜 콘솔로 같은 계획을 두 번 돌리면(`apply` → `preview`), 건너뛰기 사유는 프로브가 관측한 `fid_occupied`로 나와야 한다 — **수정 전 기준선으로서**. 즉 이 테스트는 수정 전에 실패(RED)를 재현하는 것이 목적이며, 수정 후에는 `already_patched`로 뒤집혀야 한다.

**REQ-PARITY-003** `[Ubiquitous]`
`FixtureTypes` 트리 열거는 핸들 갈래가 켜져 있어도 **이름을 그대로 돌려주어야 한다.** 실기에서도 그쪽은 이름이 나오며(프로브 §1 주석), 두 판독을 함께 핸들로 바꾸면 재현이 실기와 어긋난다.

### 번역

**REQ-PARITY-004** `[Event-driven]`
콘솔에서 읽은 픽스처 타입 값이 **핸들 형식**일 때, 시스템은 이를 `FixtureTypes` 트리의 (슬롯, 이름) 대응으로 **이름으로 번역한 뒤** 하류에 넘겨야 한다. 번역 방향은 **정방향(슬롯→이름)** 뿐이다.

**REQ-PARITY-005** `[Unwanted]`
대응표를 얻지 못했거나(트리 판독 실패·절단) 핸들의 슬롯이 대응표에 없으면, 시스템은 **추측한 이름으로 채워서는 안 된다.** 원값을 그대로 두고 「번역되지 않았다」를 구조화된 필드로 남겨야 한다.

**REQ-PARITY-006** `[Ubiquitous]`
값이 이미 이름이면 번역은 **항등**이어야 한다 — 입력을 그대로 돌려주며, 기존 소비자의 동작을 바꾸지 않는다.

**REQ-PARITY-007** `[Unwanted]`
시스템은 **이름→슬롯(역방향)** 해석을 이 SPEC의 범위에서 수행해서는 안 된다. 라이브 관측상 `Robin Spiider`가 슬롯 4와 12 둘 다에 있어 역방향은 모호하며, 그 처분은 별개 결정이다.

### 번짐 범위

**REQ-PARITY-008** `[Ubiquitous]`
§A.3의 여덟 자리(C1~C8) 각각에 대해, 시스템 문서는 **「핸들이 들어오면 어긋나는가」를 측정 결과로** 분류해야 한다 — 판정은 근거(테스트 또는 원문 인용)를 동반한다.

**REQ-PARITY-009** `[Unwanted]`
분류표는 측정하지 않은 자리를 **결함으로 적어서는 안 되며**, 측정한 자리를 **미측정으로 남겨서도 안 된다.** 각 행은 「측정됨/미측정」을 명시한다.

---

## C. 범위 경계와 선행 조건

- **콘솔 무접촉.** 이 SPEC의 모든 검증은 오프라인이다. onPC 접속이 필요한 항목은 하나도 없다.
- **슬롯 12 미판독.** 「같은 이름을 가진 두 슬롯 중 어디로 새로 패치하는가」는 이 SPEC이 답하지 않는다. 추정하지 않는다.
- **실기 슬롯 번호와 오프라인 슬롯 번호는 다르다.** 가짜는 CSV 8종(슬롯 1~8), 실기 라이브러리는 15종(관측된 슬롯 4·8·9·10·11·13·14·15). **재현되는 것은 갈래이지 번호가 아니다.**

---

## D. 미검증 (Gaps) — 이 SPEC이 재지 않은 것

리드 배차가 지목한 항목을 그대로 옮기고, 이 세션이 추가로 확인한 것을 덧붙인다.

1. **콘솔 라이브 0건.** onPC에 접속하지 않았다. 슬롯 12 재판독, 86대 상태 재조회, 실기 `FixtureType` 판독 — 전부 하지 않았다.
2. **감사관 재현 절차 미확인.** 감사관이 `fid_occupied 86`을 어떤 명령으로 얻었는지 원문을 보지 못했다. 프로브의 B와 수치가 같다는 것만 관측됐다. 감사관이 변형을 더했는지 라이브 관측을 오프라인 재현으로 적었는지는 **확인되지 않았다** — 추정하지 않는다.
3. **전체 스위트 미실행.** 이 plan 세션은 테스트를 돌리지 않았다. 기록된 값도 배차마다 다르다 — `progress.md:858`은 `9691 passed`(배차 t9-d3d4), `progress.md:917`은 `9681 passed`(sync-close, HEAD `2b328c6`). **run 단계는 기준선을 새로 재야 하며, 이 두 수치를 기준선으로 인용해서는 안 된다.**
4. **D2 수정 시도 0건.** 정방향 해석을 실제로 넣어보지 않았다 — **그것이 초록을 내는지는 미측정이다.** 이것은 M1의 목표이지 전제가 아니다.
5. **핸들 형식은 가정이다.** `FixtureType <슬롯>`은 라이브 관측 1건(`"FixtureType 10"`)과 일치하지만, 다른 클래스·다른 판독 경로의 형식은 아무도 재지 않았다. 형식이 다르면 REQ-PARITY-004의 인식이 실패하고 REQ-PARITY-005의 「번역되지 않음」 경로로 떨어진다 — **조용히 틀리지는 않으나, D2는 닫히지 않는다.**
6. **C2~C8 일곱 자리의 영향 미측정**(§A.3). 호출 지점의 존재와 원문만 측정됐다.
7. **`prechk`·`vwx`·`paperwork` 표면의 기존 테스트가 A-1 변경에 어떻게 반응하는지 미측정.** §A.4의 항등성 논거는 코드를 읽은 추론이며, 스위트를 돌려 확인한 결과가 아니다.
8. **리뷰 지적 미재현 2건** — 3번(`awaited_human` 미전파) · 5번(완전성 술어 재구현)은 가설로 남아 있고 이 SPEC이 다루지 않는다. 4번(`rows_total` 중복 계수)은 재현됐으나 콘솔 영향이 없다.

---

## E. 잔여 위험

- **A-1을 고르면 공용 판독 표면이 바뀐다.** 항등성 덕에 회귀 위험은 낮다고 보지만, 그것은 추론이지 측정이 아니다(Gap 7). M1은 전체 스위트로 이를 반증할 기회를 반드시 가져야 한다.
- **트리 판독이 절단되면 번역이 부분적으로만 된다.** REQ-PARITY-005가 조용한 실패를 막지만, 「일부만 번역된 리그」에서 D2가 부분적으로 남는 상태는 여전히 가능하다.
- **가짜↔실물 괴리는 이번이 세 번째다** — D1(절단) → D2(핸들) → RV1/RV2(폭 산정). 스위트가 원리적으로 못 보는 자리가 더 있다고 전제해야 하며, 이 SPEC은 그중 하나만 닫는다. 나머지를 체계적으로 찾는 일은 실기가 필요하고, **별도 카드로 권고한다**(plan.md §F).
- **워크트리 기본 상태가 품질 게이트를 무력화한다.** 새 워크트리에 `ui/node_modules`가 없어 pre-commit 게이트가 `vitest: command not found`로 죽는다(run 레인 보고, 이 세션 미재현). 「검사가 도는데 눈이 없다」는 이 SPEC의 주제와 계열이 같으나 **대상이 다르다**(제품 코드가 아니라 개발 환경). plan.md §F에 별도 카드로 권고한다.

---

## F. 참고

- `.moai/probes/t11-d2-probe.md` — D2 오프라인 재현 측정(정본, 재현하지 않고 인용)
- `.moai/specs/SPEC-COPILOT-LXSEQ-001/progress.md` §E.4 「독립 감사」 F1 행 · `:621` 라이브 관측 · `:1003` F13 정정
- `.moai/specs/SPEC-COPILOT-LXSEQ-001/review-72-defects.md` — 앵커 전달 방식 정정(이 카드에서 함께 고친다)
- `server/tests/test_lxseq_tool.py:86-99` — `truncate_at` 선례
