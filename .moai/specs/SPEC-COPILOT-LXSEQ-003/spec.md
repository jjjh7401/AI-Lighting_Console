---
id: SPEC-COPILOT-LXSEQ-003
title: "LX-SEQ 연계 3단계 — RIG PRESET 시트(Dim·Col·Beam 19건)에서 onPC 프리셋으로"
version: "0.1.0"
status: draft
created: 2026-08-25
updated: 2026-08-25
author: manager-spec
priority: P1
phase: "v0.3.0 target — LX-SEQ 연계 3단계(프리셋)"
module: "server/lxseq/ (신규 preset_parser, preset_mapper), server/orchestrator/tools.py (툴 1종 등재), server/sheets/registry.py (행 3개), server/tools/ (하네스 1종), server/tests/fixtures/lxseq/ (CSV 사본), server/web/session.py 및 server/spatial (재사용, 무변경)"
lifecycle: spec-anchored
tags: "lxseq, rig-pack, preset, csv, import, store-preset, sheet-registry, pool-slot, unmeasured-value-readback, grandma3"
tier: M
related_specs: [SPEC-COPILOT-LXSEQ-001, SPEC-COPILOT-LXSEQ-002, SPEC-COPILOT-FILEARG-001, SPEC-COPILOT-COLORPRESET-001, SPEC-COPILOT-FXLIB-001]
---

# SPEC-COPILOT-LXSEQ-003 — LX-SEQ 연계 3단계: RIG PRESET 시트에서 onPC 프리셋으로

> **칸반 카드 t69, 4단계 중 3단계.** 조명감독 산출물(LX-SEQ RIG 팩)의 **PRESET 시트 3종**을 읽어
> grandMA3 onPC 에 프리셋을 저장한다. 신규 코드는 **파서 · 매퍼 · 툴 등재 1종 · 레지스트리 행 3개 ·
> 하네스 1종**뿐이다. 명령 문형, 풀 측정, 빈 슬롯 선택, 게이트 심사, 발화, 재조회는 전부 기존 경로를 쓴다.
>
> **1·2단계와 같은 다리 놓기다.** 001 이 패치 CSV 를 `patch_fixtures` 에, 002 가 그룹 CSV 를
> `create_arrangement_groups` 에 이었듯, 003 은 프리셋 CSV 를 **`run_commands`** 에 잇는다.
> 엔진 신설 0건 — t68 조사가 확인한 대로 **툴 경유로 콘솔에 쓰는 길은 `run_commands` 하나뿐**이고,
> 프리셋 저장 명령을 만드는 빌더는 이미 세 자리에 있다.
>
> **범위는 19건이다.** Pos 8종은 이 SPEC 이 아니다(§C.3).

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-25 | manager-spec | 최초 작성 (draft, Tier M). 아티팩트 3종. REQ **16건**, AC **14건**(실기 1건 포함), 마일스톤 **5개**(M0~M4). 근거는 카드 t68 의 경로 실측(`.moai/specs/SPEC-COPILOT-LXSEQ-002/t68-path-survey.md`)이고, 그 위에서 **새로 잰 것 5건**을 §A.2 에 등록한다. FILEARG 계약 정합 판정은 §A.3. |

---

## A. 개요

**한 줄**: `preset-dim.csv`(6행) · `preset-col.csv`(8행) · `preset-bm.csv`(5행) = **19건**을 읽어
프리셋 레코드로 정규화하고, 콘솔에서 읽은 풀 목록의 **빈 슬롯**에만 배정한 뒤,
이미 있는 `Store Preset` 빌더로 번역해 `run_commands` 에 위임한다.
시트 기대와 콘솔이 답한 빈 슬롯이 어긋나면 **계획을 내지 않고 대조표를 보고한다.**
값이 콘솔에 맞게 들어갔는지는 **되읽을 수 없으므로**, 「검증했다」고 말하지 않고 확인 한계를 산출물에 싣는다.

### A.1 t68 이 확정한 것 — 이 SPEC 의 전제

| # | 사실 | 근거 |
|---|---|---|
| 1 | 툴 경유로 콘솔에 쓰는 길은 `run_commands` 하나뿐이다 | `server/orchestrator/tools.py:1881` 단일 호출 · 강제 테스트 `server/tests/test_prechk_tool.py:326`(범위: `tools.py` + `ast.Name` 형태) |
| 2 | 프리셋은 ① 파서 없음 ② 콘솔 경로는 **세션 어휘로만** 있음 ③ 하네스 없음 ④ RIG 시트 투입 SPEC 없음 | t68 §1 매트릭스 · `server/lxseq/` 전수 4파일(패치·그룹뿐) |
| 3 | 레지스트리는 3행이고, 예약된 종류의 행은 「파서·핸들러가 없어서」 안 만든 것이다 | `server/sheets/registry.py:320-322` |
| 4 | 큐(LXSEQ-004)가 프리셋 ID 를 참조하므로 프리셋이 먼저다 | `…Sugar_r3.cue-ex.csv` 본문의 `COL.01` · `POS.03` |
| 5 | Pos 8종은 「현장 레코드 필요」라 값 투입 대상이 아니다 | `src/Lighting_Designer/90_빌드파이프라인/rig_data.py:162` |

### A.2 이 SPEC 이 새로 잰 것 5건 (t68 에 없다)

1. **세 시트의 열 집합이 서로 다르다.** 실측 헤더:
   `preset-dim` = `ID,Name,Level,Purpose` · `preset-col` = `ID,Name,Value,Purpose` ·
   `preset-bm` = `ID,Name,TargetGroup,Value` (제외되는 `preset-pos` = `ID,StageMeaning,TargetGroup,RecordGuide`).
   **넷은 정확 열 집합으로 쌍마다 구별된다** — 판별에 새 술어 형식이 필요하지 않다.
2. **그 판별은 이미 증명돼 있다.** `AC-FILEARG-018` 이 위 네 헤더를 그대로 **합성 서명 픽스처**로 써서
   「넷이 각각 자기 종류 하나에만 맞는다」를 증명했고, 비공허성 대조군까지 명시했다 —
   `preset-col` 을 포함 검사 세 열(`ID` `Name` `Value`)로 두면 `preset-bm` 헤더가 두 서명에 맞아
   `count == 2` 가 되어야 한다. **본 SPEC 은 그 설계를 다시 유도하지 않고 물려받는다.**
3. **`Store Preset` 빌더가 이미 세 자리에 있다.**
   `server/web/session.py:2951 _preset_store_commands`(`Store Preset <pool>.<n>` + `Label`, `:2968`) ·
   `server/spatial/pointing.py:331 position_preset_store_commands`(`session.py:4418` 호출) ·
   `server/fx/instantiate.py:694`. 신규 문형을 만들 이유가 없다.
4. **풀 목록은 읽힌다.** `_fx_preset_destination`(`tools.py:5281-5300`)이 `state_port` 로 풀 목록을 읽어
   빈 슬롯을 고르고, 「`All 1` 이 고정 슬롯이라고 가정하지 않는다」를 독스트링에 못박아 뒀다.
   **슬롯 점유는 관측 가능하다.**
5. **레지스트리 트립와이어는 개수가 아니라 조건을 잰다.**
   `server/tests/test_sheets_registry.py:222` 는 원래 `len(REGISTRY) == 2` 였으나
   「행이 늘면 숫자만 올리게 된다」는 이유로 **핸들러가 실재하는가**로 바뀌었다(`:225-231`).
   행을 3개 더해도 **올릴 숫자가 없다.**

### A.3 FILEARG 계약 정합 판정 — 「각각 한 행씩」 대 3행

리드가 이 SPEC 에 판정을 위임한 항목이다. 재서 판정한다.

| 문면 | 위치 | 성격 |
|---|---|---|
| 「프리셋 4종 · `group` · `fx` · `cue-ex`의 서명을 쓰지 않는다」 | `FILEARG-001/spec.md:119` **REQ-FILEARG-017** | **규범 절.** 종류를 7개로 **열거**한다 |
| 「LXSEQ-002/003/004가 **각각 한 행씩** 더하라고 예약해 둔 계약」 | `FILEARG-001/spec.md:82` | **티어 판정 근거 문단.** 요구가 아니다 |
| 「등록 행은 `patch`와 `vectorworks` 둘뿐이다」 | `FILEARG-001/acceptance.md:170-172` **AC-FILEARG-020** | **그 카드 시점의 상태 단언** |

**판정: 003 이 행 3개를 더하는 것은 REQ-FILEARG-017 위반이 아니다.** 근거 셋.

① 규범 절이 열거한 것은 **7종**인데 「각각 한 행씩」은 그 열거와 산수가 맞지 않는다
(7종을 3 SPEC 이 한 행씩 나누면 3행뿐이다) — `:82` 는 요약이 부정확한 산문이다.
② REQ-FILEARG-017 은 `[Unwanted]` 절이고 금지 대상은 **FILEARG 자신의 변경**이다(「The 변경 shall not …」).
003 이 자기 종류의 행을 만드는 것은 그 금지의 대상이 아니라, 오히려 같은 요구가 명시한 조건
(「그 종류의 파서·핸들러가 있어야 행을 만든다」)의 **충족**이다.
③ AC-FILEARG-020 의 「둘뿐」은 이미 LXSEQ-002 가 `group` 행을 더하며 지나간 값이고,
그 검사는 **개수에서 조건으로** 다시 쓰였다(§A.2-5).

**처방(본 SPEC 밖, 별건 권고)**: `FILEARG-001/spec.md:82` 의 「각각 한 행씩」은
「각자 소유한 종류의 행을」로 정정하는 것이 맞다. 지금 문면대로 읽으면 003 이 위반처럼 보인다.
정정은 FILEARG-001 소유이므로 본 SPEC 은 판정만 남기고 고치지 않는다.

---

## B. 배경과 문제

패치 86 과 그룹 18 은 콘솔에 들어갔다. 프리셋은 못 들어간다 — **막는 것은 규칙이 아니라 부재**다.
파서가 없고, 시트를 받는 툴이 없고, 그것을 실기로 확인한 하네스가 없다.

그런데 콘솔 쓰기 자체는 이미 가능하다. 운영자가 채팅으로 말하면 프리셋이 저장된다
(COLORPRESET-001 계열 어휘). 없는 것은 **조명감독의 시트를 그 경로에 잇는 다리**다.
그래서 이 SPEC 은 엔진을 만들지 않고 다리를 놓는다.

문제의 크기도 작다. 19건이고, 열은 넷이며, 판별 설계는 이미 증명돼 있다(§A.2-2).

---

## C. 범위

### C.1 In Scope

1. 세 시트의 파서 (`server/lxseq/preset_parser.py`)
2. 레코드에서 `Store Preset` 명령으로 가는 매퍼 (`server/lxseq/preset_mapper.py`)
3. 툴 1종 등재: `import_lxseq_presets` (`server/orchestrator/tools.py`)
4. 시트 종류 레지스트리 행 3개 (`server/sheets/registry.py`) — 술어는 `ExactColumns`
5. 라이브 하네스 1종 (`server/tools/lxseq_presets_e2e.py`) — `--approve` 없이는 콘솔에 안 닿는다
6. 픽스처: 정본 CSV 3종 사본 (`server/tests/fixtures/lxseq/`)

### C.2 Out of Scope

1. **`preset-pos`** — §C.3
2. **FX 8건** — 카드 t71. 경로는 있으나 나르는 재료가 다르다(t68 §2.3)
3. **곡 큐 89건** — LXSEQ-004. 본 SPEC 이 선행이다
4. **FILEARG-001 문면 정정** — §A.3 처방. 그 SPEC 소유
5. **새 콘솔 쓰기 경로** — `run_commands` 위임만. `server/lxseq/` 에 쓰기 수단 0
6. **새 명령 문형** — 기존 빌더 3자리 재사용(§A.2-3)
7. **UI 파일 선택기** — 001 에서 t10 으로 위임된 접점. 하네스가 파일을 읽는다

### C.3 Out of Scope 근거 — Pos 8종을 왜 빼는가

`rig_data.py:162` RIG_NOTES: 「POS.01~08 포지션 프리셋 **전부 현장 레코드 필요** — 레코드 가이드 열 기준」.
그리고 그 시트는 열이 다르다 — `ID,StageMeaning,TargetGroup,RecordGuide` 로 **값 열이 없다.**
넣을 값이 CSV 에 없고, 무대에서 조준해 기록하는 대상이다. 그 경로는 이미 있다(`server/spatial/pointing.py:331`).

**즉 「프리셋 27건 투입」은 27 중 8에 대해 틀린 처방이다.** 19와 8은 다른 물건이다.

---

## D. 요구 (GEARS)

### D.1 파싱 (M1)

- **REQ-LXSEQ3-001** `[Ubiquitous]` The 파서 **shall** 세 시트를 각각의 **정확 열 집합**으로 읽는다.
  정본은 실측 헤더이며(§A.2-1) 사본을 만들지 않고 한 자리에서 선언한다.
- **REQ-LXSEQ3-002** `[Unwanted]` The 파서 **shall not** `preset-pos` 를 읽는다 — 서명도 분기도 두지 않는다.
- **REQ-LXSEQ3-003** `[Ubiquitous]` The 파서 **shall** ID 접두(`DIM.`·`COL.`·`BM.`)가 시트 종류와
  일치하는지 검사하고, 어긋난 행을 **거부하며 그 행을 보고**한다.
- **REQ-LXSEQ3-004** `[Unwanted]` The 파서 **shall not** 산문 열(`Purpose`)을 해석해 값을 만든다.
  보존은 하되 값 산출에 쓰지 않는다.
- **REQ-LXSEQ3-005** `[Ubiquitous]` The 파서 **shall** `TargetGroup`(bm)을 **이름 문자열로만** 취급한다 —
  FID 로 확장하지 않는다. 그룹 멤버십은 어느 채널로도 읽히지 않아 확장의 근거가 없다.

### D.2 매핑 (M2)

- **REQ-LXSEQ3-006** `[Ubiquitous]` The 매퍼 **shall** 풀 번호를 **콘솔이 답한 목록에서만** 정한다(§A.2-4).
- **REQ-LXSEQ3-007** `[Unwanted]` The 매퍼 **shall not** 점유 슬롯에 쓴다 — 001 감독 결정 ③의 승계.
- **REQ-LXSEQ3-008** `[Unwanted]` **Where** 풀·슬롯 측정이 불완전하거나 시트 기대와 어긋난 경우,
  the 매퍼 **shall not** 부분 계획을 낸다 — 0건을 내고 대조표를 보고한다.
- **REQ-LXSEQ3-009** `[Ubiquitous]` The 매퍼 **shall** 기존 `Store Preset` 빌더를 재사용한다(§A.2-3).
- **REQ-LXSEQ3-010** `[Ubiquitous]` The 매퍼 **shall** 발화 전 번들 바이트를 재어 **기록**한다.
  **다만 바이트 상한을 판정 근거로 선언하지 않는다** — 그 축은 미지다(§G.1).

### D.3 툴과 배선 (M3)

- **REQ-LXSEQ3-011** `[Ubiquitous]` The 시스템 **shall** 툴 `import_lxseq_presets` 1종을 등재한다.
  파일 내용은 `file_content_base64` 인자로만 받고 서버는 경로를 받지 않는다(001 규약 승계).
- **REQ-LXSEQ3-012** `[Ubiquitous]` The 시스템 **shall** 레지스트리 행 **3개**를 `ExactColumns` 로 더한다.
  포함 검사는 쓰지 않는다 — `col` 과 `bm` 이 갈리지 않는다(§A.2-2 대조군).
- **REQ-LXSEQ3-013** `[Unwanted]` The 변경 **shall not** `server/lxseq/` 에 콘솔 쓰기 수단을 둔다.
- **REQ-LXSEQ3-014** `[Ubiquitous]` The 산출물 **shall** 확인 한계를 명시한다 —
  「슬롯이 찼다」는 되읽었고 「값이 맞다」는 되읽지 못했다고 말한다(§G.2).

### D.4 라이브 (M4)

- **REQ-LXSEQ3-015** `[Where]` **Where** `--approve` 가 없는 경우, the 하네스 **shall not** 콘솔에 발화한다.
- **REQ-LXSEQ3-016** `[Ubiquitous]` The SPEC **shall** §A.3 의 계약 정합 판정을 산출물에 남긴다 —
  다음 사람이 「위반 아닌가」를 다시 묻지 않도록.

---

## E. 가정 (ASSUMPTION)

- **ASSUMPTION-01** 풀 목록 판독은 `_fx_preset_destination` 이 쓰는 경로에서 계속 동작한다.
  M0 에서 코드로 재확인하고, 실기 확인은 M4.
- **ASSUMPTION-02** `Store Preset` 문형은 `/Universal` 없이 성립한다.
  ⚠️ `session.py:1933` 이 「Global/Universal 플래그는 **미검증 문법**」이라 적어 뒀다 —
  M4 가 답할 항목이며 그때까지 기본형만 쓴다.
- **ASSUMPTION-03** 19건 번들을 한 번에 보낼 수 있다. **근거 없음**(§G.1).
  M2 는 배치 크기를 조절 가능하게 만들고 M4 가 실측한다.

---

## F. 성공 판정

1. 세 시트 19행이 레코드로 읽히고, `preset-pos` 는 어느 서명에도 맞지 않는다.
2. 판별기가 세 헤더를 각각 하나로 가른다 — 그리고 포함 검사 대조군이 `count == 2` 를 낸다.
3. 풀·슬롯이 어긋나면 계획 0건 + 대조표.
4. `server/lxseq/` 에 콘솔 쓰기 수단 0건(기계 확인).
5. 산출물이 확인 한계를 말한다.
6. M4 에서 프리셋이 콘솔에 저장되고 **슬롯 점유가 되읽힌다**(값 일치는 미검증으로 기록).

---

## G. 위험

### G.1 🔴 바이트 축의 미지 — 「짧게 유지하면 안전」은 근거가 없다

카드 t72 의 실측(**리드 보고이며 내 관측이 아니다**): 콘솔 거절이 **길이가 아니라 내용**에 달렸고
축을 못 찾았다 — **2044B 거절 · 2080B 통과**가 재현됐다. 더 긴 payload 가 통과하고 더 짧은 것이 거절된다.
그리고 t66 실측(같은 출처): **요청 방향은 86개 1201B 까지 상한을 못 찾았고**,
회신 방향의 `[1200,1208)` 과는 **다른 축**이다.

**따라서 본 SPEC 은 바이트 상한을 안전 근거로 쓰지 않는다.** 19건이 만들 명령이 그 미지에 걸릴 수 있다.
대응은 상한 선언이 아니라 **실패를 놓치지 않는 것**이다 — 하네스가 부분 실패를 fail-fast 로 잡고
어느 명령까지 갔는지 보고한다(REQ-LXSEQ3-010 · AC-LXSEQ3-013).

### G.2 🔴 값 일치를 되읽을 수 없다

t68 §2.7 이 프리셋을 **부분**으로 쟀다 — 풀 슬롯 점유는 `state_port` 로 읽히지만 **값 일치는 미측정**이다.
「19건을 만들었다」는 확인되고 「값이 맞다」는 확인되지 않는다.

이 비대칭은 이미 한 번 값을 치렀다. 그룹 멤버십에서 쓴 것이 어느 채널로도 되읽히지 않아 오해석이
조용히 영속했고, 002 는 그것을 **미검증으로 적는 것**으로 다뤘다. 003 도 같게 다룬다.

**확인 못 하는 것을 만드는 것은 되돌릴 수 없는 쓰기다.** 그래서 M4 는 19건을 한 번에 넣지 않고
소수 먼저 넣어 되읽고 그 다음을 정한다.

### G.3 시트 기대와 콘솔 상태의 어긋남

시트에는 슬롯 번호가 없다. 배정은 콘솔이 답한 빈 슬롯에서 온다. 그러면
**RIG ID 와 콘솔 슬롯 번호의 대응을 기록하지 않으면 다음 단계가 참조를 못 한다** —
LXSEQ-004(큐)가 `COL.01` 을 참조하기 때문이다. 대응표를 산출물에 남기는 것이 M2 의 의무다.

### G.4 본 SPEC 이 다루지 않는 위험

- Pos 8종의 현장 레코드 절차 (별건)
- `/Universal` 플래그의 미검증 문법 (ASSUMPTION-02, M4 가 답한다)
- FILEARG 문면 정정 (§A.3 처방, 그 SPEC 소유)
