---
id: SPEC-COPILOT-FILEARG-001
title: "파일 선택기 → 툴 인자 — 업로드 바이트를 헤더 서명으로 판별해 세션 슬롯에 담고 래퍼 툴이 인자로 주입한다"
version: "0.3.0"
status: draft
created: 2026-08-22
updated: 2026-08-23
author: manager-spec (칸반 카드 t10)
priority: P1
phase: "v0.3.0 target — LX-SEQ 연계 전달 경로(패치 1종 등록). 그룹 · 프리셋/FX · 시퀀스는 후속 SPEC이 레지스트리에 행만 더한다"
module: "ui/src/{App.tsx,useCopilotSocket.ts,protocol.ts}, server/web/{messages.py,app.py,session.py}, server/sheets/ (신규 — 헤더 서명 레지스트리 · 판별기), server/orchestrator/{tools.py,runner.py} (래퍼 툴 등재)"
lifecycle: spec-anchored
tags: "file-picker, upload, header-signature, sheet-kind, registry, session-slot, wrapper-tool, file_content_base64, lxseq, grandma3"
tier: M
related_specs: [SPEC-COPILOT-LXSEQ-001, SPEC-COPILOT-VWX-001, SPEC-COPILOT-IMGLAYOUT-001, SPEC-COPILOT-AUTOPATCH-001]
---

# SPEC-COPILOT-FILEARG-001 — 파일 선택기가 고른 CSV의 바이트를 툴 인자까지 보낸다

> **칸반 카드 t10.** LXSEQ-001이 만든 `import_lxseq_patch`는 `file_content_base64`를 필수 인자로 받지만, 그 바이트를 넣어 줄 수 있는 것은 개발용 하네스 스크립트 `server/tools/lxseq_e2e.py` 하나뿐이다. 운영자는 앱으로 LX-SEQ 패치 CSV를 넣을 수 없다. 본 SPEC은 그 전달 경로를 만든다 — 앱의 파일 선택기가 고른 파일의 바이트가 실제 툴 인자에 도달하게 한다.
>
> **리드 확정 결정(2026-08-22) — 구속력 있음.** ① **종류 판별은 헤더 서명으로 한다.** 파일 이름은 힌트일 뿐 분기 근거가 아니다. 어느 서명과도 맞지 않으면 `unknown_sheet_kind`로 거절하고, 가장 비슷한 종류로 보내지 않는다. 두 서명에 동시에 맞아도 같은 거절이다. ② **업로드는 담기만 한다.** `preview`조차 자동 실행하지 않는다. ③ **일반화하는 것은 전달 수단이지 의미가 아니다.** 슬롯 하나와 `종류 → 대상 툴` 레지스트리를 지금 만들되, 채우는 행은 `patch` 하나뿐이다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-22 | manager-spec | 최초 작성 (draft, Tier M). 아티팩트 5종(spec/plan/acceptance/research/progress). REQ **15건**(REQ-FILEARG-001~015), AC **17건**(라이브 1건 포함), 마일스톤 **6개**(M0~M5), clarification 마커 **1건**(plan.md §A.4 ① — 어느 서명과도 맞지 않는 CSV의 처분). 리드 결정 ①②③은 결정 A·B·C로 등록해 마커로 남기지 않는다. |
| 0.2.0 | 2026-08-23 | manager-spec | **리드 재정 반영 — 마커 0건.** ① 열린 결정 마감: 서명 미일치 CSV의 처분은 **(나)안**(Vectorworks를 레지스트리 행으로 등록하고 0건이면 거절) → plan.md 결정 **I**. ② 리드가 결정 ③의 "행 하나" 문면을 정정 — 행의 개수가 아니라 **파서·핸들러 없는 종류를 만들지 말라**는 뜻(plan.md 결정 D 정정 기록). ③ 리드 실측 3건 반영(`research.md` §9, `origin/main` `e7a8e90` · `6296af3`에서 불변 확인): 표본 실재로 `ASSUMPTION-75` **닫힘**, LX-SEQ↔VW 열 대조 3/9 일치로 비충돌 확정, 후속 시트 7종 헤더로 **프리셋 4종 충돌 실증**(속성 A는 이론이 아니다). ④ 결정 **J** — **서명 형식**의 표현력을 넓히고 **레지스트리 행**은 넓히지 않는다 → REQ **016·017** 신설. ⑤ 결정 I의 안전판(브리틀 시 폴백은 반드시 선언된 레지스트리 항목 + UI 고지) → REQ **018** 신설. REQ 15→**18**, AC 17→**21**(AC-018 형식 충분성 증명 · 019 교차 분류 · 020 행 불증식 · 021 안전판), 결정 8→**10**(A~J), ASSUMPTION 3→**2**(75 닫힘). |
| 0.3.0 | 2026-08-23 | manager-spec | **독립 감사 FAIL(차단 5건) 시정.** 뿌리는 설계 오류 하나였다 — **열 집합 서명으로는 Vectorworks의 신원을 표현할 수 없다**(B1·B2·B3). zip에는 헤더 행이 없고(`.mvr`·`.xlsx`), 헤더는 1행이라는 보장이 없으며(판독기가 **탐색**한다), 서명 소유자를 `columns.py`로 잘못 적었다(정본은 호출 지점 `reader.py:286`). 그대로 두면 (다)안을 기각한 사유가 (나)안 **안에서** 되살아나 살아 있는 `.mvr`/`.xlsx` 업로드를 회수한다. **결정 K** — 레지스트리 행은 열 집합이 아니라 **판별 술어**를 든다(`patch`=열 집합 술어 · `vectorworks`=기존 판독기 위임). 앞선 네 결정(0건 거절 · 2건 이상 거절 · 파서/핸들러 0건 · 기존 업로드 유지)은 전부 살아남으며, 치른 값(표가 순수 데이터가 아니게 됨)을 §G.1에 명시했다. 신설: **REQ-019**(판별기 입력 경계 — B1의 재발 방지) · **REQ-020**(암묵적 `else` 금지를 조건부에서 **무조건**으로 분리, B5) · **AC-022**(실물 `.mvr` 315,155 B가 `unknown_sheet_kind`가 아님) · **AC-023**(대상 툴 부재는 **판별 시점**에 후보 제외 + 오류, B4) · **AC-024**(암묵적 `else` 부재, 무조건). 개정: REQ-007(행=술어) · REQ-016(열 집합 술어 한정) · REQ-018(안전판에서 ① 분리 · 대상 fixture 전량) · AC-006 · AC-013(6지점 열거에 **핸들러 클로저** 추가, `test_runner_progress`는 편집 지점이 아니라 **누락 검출 가드**로 재분류 — D1) · AC-019(대상 = `server/tests/fixtures/vwx/` **전량 12개 · `.mvr` 포함**, 추정 "7종" 폐기 — D2) · AC-021(③ 검증을 `발동함`이라는 **판별력 있는** 토큰으로 — 기존 grep은 오늘도 통과했다). **ASSUMPTION-77 닫힘 · POSITIVE** — 실물 CSV **7,258 B**(≈7 KB), 8 MiB는 약 1,150배("수십 KB"는 한 자릿수 오차였다). REQ 18→**20**, AC 21→**24**, 결정 10→**11**(A~K), ASSUMPTION 2→**1**. 감사가 강점으로 지목한 것(결정 ① 계수 요구의 5중 고정 · AC-003의 주입 표 · 좌표 27건 무오류 · `addr_range_mismatch` 함정 봉쇄)은 **그대로 두었다**. |

---

## A. 개요

**한 줄**: 운영자가 첨부 버튼으로 고른 파일의 바이트를 서버 세션이 받아, **헤더 행의 서명**으로 시트 종류를 판별하고, 그 바이트·sha256·판별된 종류를 세션 슬롯 하나에 담아 둔다. 아무것도 실행하지 않는다. 나중에 운영자가 시킬 때, 모델은 바이트를 만지지 않는 **래퍼 툴**을 부르고, 핸들러가 슬롯의 바이트를 레지스트리가 지목한 대상 툴의 `file_content_base64` 인자에 넣어 형제 툴을 호출한다.

### 사전 확정 사실 (조사 확정 — `research.md`가 근거를 소유)

1. **바이트를 툴 인자에 넣는 선례가 이미 저장소에 있다.** `vectorworks_autopatch` 핸들러(`server/orchestrator/tools.py:2944-2964`)는 세션이 들고 있는 업로드 바이트를 `content = vectorworks_upload.content_base64`(:2950)로 꺼내 `arguments={"file_content_base64": content}`(:2961)로 형제 툴을 부른다. **래퍼 툴 자신의 스키마에는 `file_content_base64`가 없다** — 그래서 모델은 base64를 한 번도 다루지 않는다. 본 SPEC은 이 형태를 그대로 계승한다.
2. **세션에 바이트를 담아 두는 선례도 둘 있다.** `upload_vectorworks_export`(`server/web/session.py:9655-9658`)는 `self._vectorworks_upload`(`_UploadedVectorworksExport`, `session.py:2492-2508`)에 담은 **뒤 곧바로** 고정 지시문으로 `run_instruction(...)`을 부른다. `upload_layout_image`(`session.py:9660-9688`)는 `self._layout_image`에 담고 안내만 낸다. 본 SPEC의 슬롯은 **저장 형태는 전자를, 실행하지 않는 태도는 후자를** 따른다(리드 결정 ②).
3. **오늘 LX-SEQ 패치 CSV는 조용히 Vectorworks로 간다.** `ui/src/App.tsx:625-635`의 라우터는 이미지 MIME이면 `uploadLayoutImage`, **그 밖이면 전부** `uploadVectorworksExport`다. Vectorworks 경로는 `.csv/.txt/.xlsx/.mvr`을 받으므로(`App.tsx:550`) LX-SEQ 패치 CSV는 else 가지에 떨어져 Vectorworks 파서에게 간다. 이것이 본 카드가 고치는 결함이다. 라우터의 주석은 **2026-08-15 운영자 결정**을 기록한다 — "첨부 버튼은 하나 — 파일 종류가 목적지를 고른다". 그 결정은 유지된다. 바뀌는 것은 "종류"를 무엇으로 읽느냐다(확장자·MIME → **헤더 서명**).
4. **UI는 툴 호출을 조립하지 않는다.** `sendVectorworksExportUpload`·`sendLayoutImageUpload`(`ui/src/useCopilotSocket.ts:332-351`)는 채팅 메시지 하나를 띄우고 프로토콜 프레임을 보낼 뿐이며, 프레임 빌더(`ui/src/protocol.ts:503-510`, `:519-531`)도 마찬가지다. 툴 인자를 채우는 일은 전부 서버 쪽에서 일어난다 — 본 SPEC도 그 경계를 지킨다.
5. **대상 툴의 인자 집합은 닫혀 있고 경로 인자는 없다.** `import_lxseq_patch` 스키마(`tools.py:9253-9306`)는 `required: ["file_content_base64"]`(:9304)이고 형제 인자는 `action`·`name_prefix_mode`·`only_fids`·`mode_overrides`이며 시트·종류 인자는 없다. `additionalProperties == False`(`.moai/specs/SPEC-COPILOT-LXSEQ-001/acceptance.md:273`). 툴 설명문은 이 툴이 파일 경로를 받지 않는다고 명시한다(`tools.py:9264`). 저장소 전체 툴 스키마를 훑어도 **파일 시스템 경로로 파일 내용을 받는 툴은 없다** — `query_state`의 `path`(`tools.py:7213-7231`)는 콘솔 오브젝트 트리 주소이지 파일 경로가 아니다. 따라서 본 SPEC은 경로 인자를 새로 만들지 않는다.
6. **헤더 판독은 이미 위치 무관·관대하다.** `server/lxseq/parser.py:122-135`의 `_resolve_header_map`은 대소문자·공백·BOM을 무시하고 위치와 무관하게 정규 열을 찾으며, 하나라도 없으면 `MissingColumnsError`를 던진다. 정규 열 **밖의 열은 버리지 않고 `extra`에 보존한다**(`parser.py:172-175`) — 즉 관용된다. 이 관용이 §F의 [HARD] 속성 두 가지를 낳는다.
7. **오늘 유일한 호출자는 개발용 하네스다.** `server/tools/lxseq_e2e.py:261`이 파일 바이트를 읽어 `base64.b64encode(raw)`한 뒤 제품 툴 스택을 직접 부른다. `import_lxseq_patch`의 호출자는 그것 하나다.

### 이 SPEC이 하는 것 / 하지 않는 것

| 하는 것 | 하지 않는 것 |
|---|---|
| 헤더 서명으로 시트 종류 판별(0건·2건 이상은 거절) | 종류를 파일 이름·확장자·MIME으로 분기 |
| 세션 슬롯 1개(바이트 · sha256 · 종류 · 길이) | 업로드 시점의 자동 실행(`preview` 포함) |
| `종류 → 대상 툴` 레지스트리(행 1개: `patch`) | 002/003/004용 파서·핸들러 선제 구현 |
| 바이트를 만지지 않는 래퍼 툴 1종 등재 | 대상 툴의 인자 집합 변경 · 경로 인자 신설 |
| UI 라우터를 헤더 기반 목적지 선택으로 교체 | 첨부 버튼 2개화 · 2026-08-15 운영자 결정 번복 |

---

## B. 요구사항 (GEARS)

### B.1 판별 — 술어와 계수 (`server/sheets/`)

- **REQ-FILEARG-001** `[Ubiquitous]` The 판별기 **shall** 업로드된 바이트의 **헤더 행**만으로 시트 종류를 정한다. 판별 단위는 **포함 검사**다 — 등록된 서명의 정규 열이 **전부** 헤더에 있으면 그 종류에 맞는 것으로 센다. 헤더 정규화는 `server/lxseq/parser.py:118 _normalize_header`의 규약(양끝 공백 제거 · 내부 공백 제거 · BOM 제거 · 소문자화)을 **재사용**하며 새로 정의하지 않는다. 파일 이름·확장자·MIME은 **기록만** 하고 분기에 쓰지 않는다 — 판별 결과에 `filename_hint`로 실어 사람이 대조할 수 있게 하되, 서명과 어긋나도 서명이 이긴다.
- **REQ-FILEARG-002** `[Ubiquitous]` The 판별기 **shall** 첫 일치에서 멈추지 않고 **레지스트리 전체를 훑어 일치 건수를 센다**. 포함 검사이므로 어떤 시트가 다른 시트 서명의 상위 집합이면 두 종류에 동시에 맞을 수 있고, 조기 반환은 그 충돌을 조용히 가린다(§F 속성 A). 판별 결과는 `{matched: [kind...], count, header_read: [원문 열 이름...], filename_hint}`를 그대로 싣는다.
- **REQ-FILEARG-003** `[Event-driven]` **When** 일치 건수가 **0**이면, the 시스템 **shall** `unknown_sheet_kind`로 거절하고 슬롯에 **아무것도 담지 않으며**, 가장 비슷한 종류로 보내지 않는다. 거절 보고에는 읽은 헤더 열 원문과 등록된 종류의 서명 목록을 함께 실어, 운영자가 어느 열이 어긋났는지 스스로 볼 수 있게 한다.
- **REQ-FILEARG-004** `[Event-driven]` **When** 일치 건수가 **2 이상**이면, the 시스템 **shall** `ambiguous_sheet_kind`로 거절하고 일치한 종류를 **전부** 이름으로 밝히며, 그중 하나를 고르지 않는다. 애매함은 추측해도 되는 자리가 아니다 — 잘못 라우팅된 LX-SEQ CSV는 잘못된 패치가 되고, 그것은 무대 사고다.
- **REQ-FILEARG-005** `[Unwanted]` The 판별기 **shall not** 후보 종류마다 그 종류의 실제 파서를 시험 삼아 돌려 예외 발생 여부로 종류를 정한다. `_resolve_header_map`은 불일치를 `MissingColumnsError` **예외**로 알리므로(`parser.py:122-135`), 후보별 투기적 파싱은 예외를 제어 흐름으로 삼고 라우터를 파서 내부 구현에 묶는다(§F 속성 B). 판별은 `CANONICAL_COLUMNS`와 정규화 함수만 쓰는 가벼운 술어로 하고, 진짜 파싱은 종류가 정해진 **뒤 한 번만** 돈다.

### B.2 슬롯과 레지스트리 (`server/web/session.py` · `server/sheets/`)

- **REQ-FILEARG-006** `[Ubiquitous]` The 세션 **shall** 판별에 성공한 업로드를 슬롯 **하나**에 담는다. 슬롯이 싣는 것: `content_base64`(원문 바이트) · `sha256` · `byte_length` · `kind`(판별된 종류) · `file_name`(힌트, 보고용) · `received_at`. 저장 형태는 `_UploadedVectorworksExport`(`session.py:2492-2508`)의 교체형 슬롯을 거울로 삼는다 — 새 업로드는 앞의 것을 **교체**하고, 세션 초기화 시 함께 비워진다(`session.py:3588`의 `clear()` 규약과 같은 자리에서 처리한다). 슬롯은 **하나**이며 종류별로 늘리지 않는다.
- **REQ-FILEARG-007** `[Ubiquitous]` The 시스템 **shall** 레지스트리를 **표 하나**로 두되, 행의 형태는 **`(kind, 판별 술어, 대상)`**이다 — 열 목록이 아니라 **술어**를 든다(결정 K · §G.1). 술어는 두 갈래다: **열 집합 술어**(헤더 1행의 정규 열을 대조 — REQ-FILEARG-016)와 **위임 술어**(기존 판독기의 판정을 호출). 오늘 채워진 행은 **둘**이다 — **`patch`**(열 집합 술어, 정본 `server/lxseq/parser.py:18 CANONICAL_COLUMNS`, 대상 툴 `import_lxseq_patch`, 통과 인자 `action`·`name_prefix_mode`·`only_fids`·`mode_overrides`)와 **`vectorworks`**(위임 술어 — `server/vwx/reader.py`의 판정을 호출한다: ZIP 매직 판별 · 헤더 행 탐색 · `reader.py:286`의 `has_address_family(탐색된 헤더)`; 대상은 기존 세션 업로드 경로 `upload_vectorworks_export`, 통과 인자 없음). `vectorworks` 행은 **이미 있는 판정을 호출**할 뿐이며 신규 파서·핸들러·판정 논리는 0건이다. 후속 SPEC은 이 표에 **행을 더한다**. 치른 값: 레지스트리가 더 이상 순수한 데이터 표가 아니다(§G.1이 그 값을 기록한다).
- **REQ-FILEARG-008** `[Unwanted]` The 시스템 **shall not** 레지스트리에 없는 종류를 통과시킨다. 이름이 예약만 되어 있고 아직 구현되지 않은 종류는 등록 행이 없으므로 REQ-FILEARG-003의 `unknown_sheet_kind` 거절로 떨어진다 — **미구현이 조용한 통과가 되는 경로는 존재하지 않는다**. 또한 레지스트리 행이 지목하는 대상 툴 이름이 실제 등록된 툴 집합에 없으면 그것은 설정 오류이며, 그 행은 판별 후보에서 제외되고 오류로 보고된다(조용한 무시가 아니다).

### B.3 저장 전용 — 자동 실행 금지

- **REQ-FILEARG-009** `[Unwanted]` The 업로드 처리 **shall not** 어떤 툴이든 자동으로 실행한다 — `action="preview"`도 예외가 아니다. 구체적으로 업로드 경로에서 `run_instruction`으로 고정 지시문을 밀어 넣거나(`session.py:9655-9658`의 Vectorworks 방식), 래퍼 툴·대상 툴을 내부 호출하지 않는다. 근거: LXSEQ-001의 `REQ-LXSEQ-016` 기계적 보루는 `source.sha256`·`byte_length`를 실어 **운영자가 원본 파일과 대조할 수 있게** 하는 데 있는데, 자동 실행은 그 대조가 가능해지기 전에 움직인다. 실행은 운영자가 시키는 나중 턴에 일어난다.
- **REQ-FILEARG-010** `[Ubiquitous]` The 시스템 **shall** 업로드 직후 다음 **넷**을 운영자에게 보인다: 판별된 **종류** · **sha256** · **byte_length** · **행 수**. 행 수는 종류가 정해진 뒤 도는 **단 한 번의 실제 파싱**에서 나오며(REQ-FILEARG-005), 그 파싱은 파일만 읽는다 — 콘솔 접촉 0(`server.bridge`·`pythonosc`·`execution_port`·`deploy_pipeline`·`run_commands` 호출 0건). 행 수는 `rows_total`을 정본으로 하고 `parsed`·`rejected` 건수를 곁들인다(LXSEQ-001 페이로드 `source`의 어휘를 그대로 쓴다). 이 넷 밖의 해석(패치 가능 여부 · 점유 판정 · 타입 해석)은 이 시점에 말하지 않는다.

### B.4 래퍼 툴 (`server/orchestrator/tools.py` · `server/orchestrator/runner.py`)

- **REQ-FILEARG-011** `[Ubiquitous]` The 시스템 **shall** 래퍼 툴 **1종**을 등재해, 그 핸들러가 세션 슬롯의 바이트를 레지스트리가 지목한 대상 툴의 `file_content_base64` 인자에 넣어 **내부 `ToolCall`로 형제 핸들러를 부른다**(`vectorworks_autopatch`, `tools.py:2944-2964`와 같은 형태). 래퍼는 슬롯의 `kind`로 대상 툴을 고르며, 모델이 준 인자는 그 종류의 통과 화이트리스트에 있는 것만 그대로 전달한다 — 대상 툴의 인자 집합은 닫혀 있으므로(`additionalProperties == False`) 화이트리스트 밖 인자는 전달하지 않고 거절 사유로 밝힌다. 등재는 저장소의 **6지점**을 모두 거친다: `TOOL_NAMES` · 핸들러 클로저 · `ToolDefinition` · `handlers` 맵 · `server/orchestrator/runner.py:137 _TOOL_TASKS` · `server/tests/test_tools.py:172`의 닫힌 집합 단언(`34` → `35`).
- **REQ-FILEARG-012** `[Unwanted]` The 래퍼 툴 **shall not** 자신의 스키마에 `file_content_base64`를 선언하거나 받는다. 파일 시스템 경로를 받는 인자도 두지 않는다. 이것은 부수적 구현 세부가 아니라 **요구**이며, `SPEC-COPILOT-LXSEQ-001`의 `REQ-LXSEQ-016`을 잇는다 — 모델이 원문 바이트를 한 번도 손에 쥐지 않아야 채팅 본문이 바이트의 출처가 되는 경로가 원리적으로 생기지 않는다. 나중의 편의 개정이 이 성질을 되돌리지 못하도록 요구로 못박는다.
- **REQ-FILEARG-013** `[Event-driven]` **When** 슬롯이 비어 있거나, 슬롯의 종류가 모델이 요청한 작업과 맞지 않거나, 레지스트리가 그 종류의 대상 툴을 찾지 못하면, the 래퍼 툴 **shall** 이름 있는 사유(`no_uploaded_sheet` · `kind_mismatch` · `no_target_tool`)로 거절하고 **추측하지 않는다** — 직전 업로드를 재사용하거나, 다른 종류의 대상 툴로 대신 보내지 않는다. 사유 어휘는 닫힌 집합이다.

### B.5 UI와 보존

- **REQ-FILEARG-014** `[Ubiquitous]` The UI **shall** 첨부 버튼을 **하나로** 유지한다(2026-08-15 운영자 결정, `App.tsx:625-635` 주석). 라우팅은 그대로 두 갈래로 시작한다 — 이미지 MIME이면 레이아웃 이미지 경로(무변경), 그 밖이면 시트 업로드 경로. 다만 "그 밖"의 목적지는 더 이상 UI가 정하지 않는다: UI는 바이트를 보내고 **서버의 헤더 판별이 목적지를 정한다**. UI는 라우터일 뿐 두 번째 검증 계층이 아니므로, 크기·공백 가드(비어 있지 않을 것 · 8 MiB 이하)만 기존 경로와 같은 문구로 유지하고 헤더는 읽지 않는다. `.csv`·`.txt`는 이미 `<input accept>`에 있으므로(`App.tsx:824`) 받아들이는 확장자 목록은 넓히지 않는다.
- **REQ-FILEARG-015** `[Unwanted]` The 변경 **shall not** 다음을 수정한다(PRESERVE — §C): `server/lxseq/**` · `server/vwx/**` · `server/prechk/**` · `server/safety/**` · `console/lua/**` · `server/rulebook/assets/**`, 그리고 `server/web/session.py`의 `upload_vectorworks_export`·`upload_layout_image` **본문**과 `server/orchestrator/tools.py`의 **기존 핸들러 본문**. 허용되는 변경은 신규 모듈 추가, 신규 프레임·핸들러·래퍼 툴의 **순수 추가**, UI 라우터 교체, 그리고 툴 수 상수 1건 갱신뿐이다. 특히 `import_lxseq_patch`의 인자 집합·스키마·설명문은 **불변**이다(경로 인자 신설 0건).

### B.6 술어의 표현력 · 입력 경계 · 확장 경계 (`server/sheets/`)

- **REQ-FILEARG-016** `[Ubiquitous]` The **열 집합 술어**의 형식 **shall** 최소한 다음 두 형태를 표현할 수 있다: **(i) 정확 열 집합** — 헤더의 정규 열 집합이 명시된 집합과 **정확히 같을 때만** 일치 · **(ii) 포함·배제 쌍** — 명시된 열이 **전부 있고** 배제 열이 **하나도 없을 때만** 일치. 오늘의 포함 검사는 (ii)에서 배제 목록이 빈 경우다(`patch` 행은 그대로 포함 검사로 남는다). The 판별기 **shall** 형식이 허용하는 **모든** 형태를 해석하며, 해석하지 못하는 형태를 표에서 만나면 조용히 건너뛰지 않고 설정 오류로 보고한다(REQ-FILEARG-008과 같은 자세). 넓히는 것은 **열 집합 술어의 표현력**이지 판별 전략이 아니다 — 전체 훑기 · 계수 · 0건·2건 이상 거절은 그대로다. **이 형식은 열 집합 술어에만 적용된다** — 위임 술어(REQ-FILEARG-007 · §G.1)는 열을 세지 않으므로 이 형식의 대상이 아니다.
- **REQ-FILEARG-017** `[Unwanted]` The 변경 **shall not** LXSEQ-002/003/004가 소유하는 종류의 술어·파서·핸들러·레지스트리 행을 만든다. 특히 프리셋 4종(`preset-dim` · `preset-col` · `preset-bm` · `preset-pos`) · `group` · `fx` · `cue-ex`의 서명을 **쓰지 않는다**. 본 SPEC이 넓히는 것은 형식뿐이고, 그 형식이 실제로 프리셋 4종을 가르는지는 **합성 서명 픽스처**로 증명한다(레지스트리 행이 아니다 — `AC-FILEARG-018`).
- **REQ-FILEARG-018** `[Where]` **Where** M1이 Vectorworks 위임 술어로는 `server/tests/fixtures/vwx/`의 실제 변형을 흡수할 수 없다고 실측한 경우, the 시스템 **shall** 결정 I의 안전판으로 폴백하되 그 폴백을 **레지스트리 항목으로 선언**한다. 아울러 그 경로로 파일이 흐를 때 the UI **shall** 그 파일을 **Vectorworks export로 읽고 있다고 소리 내어 말한다**. 조용한 폴백과 선언된 폴백은 다른 물건이다 — 전자는 오늘의 결함 그대로이고 후자는 운영자가 볼 수 있는 상태다. 이 경로를 타면 `unknown_sheet_kind` 거절 규칙에 살아 있는 경로가 없어지므로, 그 사실을 plan.md §D.1 잔여 위험에 **반드시 기록한다**. (암묵적 `else` 금지는 이 조건과 무관하게 언제나 성립한다 — REQ-FILEARG-020으로 분리했다.)
- **REQ-FILEARG-019** `[Ubiquitous]` The 판별기 **shall** 자기 입력 경계를 선언한다. 받는 것은 **바이트 전체와 파일 이름 힌트**이며, 바이트가 CSV 텍스트라고 **가정하지 않는다** — ZIP 아카이브(`.mvr` · `.xlsx`, 매직 바이트 `PK`)와 헤더 행이 1행이 아닌 텍스트, 쉼표가 아닌 구분자를 쓰는 텍스트가 모두 정상 입력이다. 각 술어가 자기 입력 형태를 스스로 판정하며(열 집합 술어는 헤더 행을 읽을 수 있을 때만 참이 될 수 있고, 위임 술어는 바이트 전체를 본다), **어느 술어도 자기 것이라 하지 않은 바이트만** `unknown_sheet_kind`로 떨어진다. 그러므로 `.mvr` · `.xlsx` · 헤더 없는 탭 구분 텍스트는 **오늘 그것들을 분류하는 코드가 술어가 되므로 계속 동작한다** — 이 SPEC은 그 능력을 회수하지 않는다. 판별기가 다룰 수 없는 입력 형태가 생기면 그것은 조용한 거절이 아니라 **선언되지 않은 경계**이며 SPEC 결함으로 다룬다.
- **REQ-FILEARG-020** `[Unwanted]` The 판별기 **shall not** 암묵적 `else` 가지를 둔다 — 어떤 바이트가 어느 종류로 가는지는 **선언된 술어의 결과로만** 정해지고, 표 어디에도 없는 경로로 흘러가는 분기는 존재하지 않는다. 이 성질은 **조건과 무관하게 언제나** 성립하며, 안전판(REQ-FILEARG-018)이 발동하든 하지 않든 똑같이 검사된다 — 조건부 AC 안에 넣어 두면 폴백이 발화하지 않는 동안 아무도 확인하지 않기 때문이다(`AC-FILEARG-024`).

---

## C. 환경 및 전제

### 측정된 기준선

착수 브랜치 `WT-file-picker-args`, HEAD **`6296af3`**(= `origin/main`, t20). plan-phase 작성은 `eb436e8`에서 시작했고 그 뒤 워크트리가 `6296af3`으로 fast-forward됐다 — 사이에 `e7a8e90`(t17)과 `6296af3`(t20) 두 커밋이 들어와 **3커밋**을 건너뛰었다(리드 실측: `merge-base --is-ancestor` ANCESTOR-OK · 잃을 자체 커밋 0 · 병합 후 divergence `0 0`). 그러므로 본 문서가 인용한 **줄번호는 한 세대 낡았다** — M0가 토큰 앵커로 전부 재확인한다.

기준선 실측값은 `progress.md` §E.1 `baseline_measured`가 소유하며, 그 값은 **미측정**이다. 다른 트리에서 잰 전체 스위트 수치는 이월하지 않는다 — `eb436e8`에서 쟀더라도 트리가 밑에서 바뀌었으므로 똑같이 틀린 값이 됐을 것이다. M0가 **이 워크트리 `6296af3`에서** 직접 잰다. 각 마일스톤은 착수 직전 다시 잰다.

**이 저장소에는 테스트 CI가 없다.** `.github/workflows/`에는 라벨 동기화 워크플로 하나뿐이고, 회귀의 유일한 증거는 **로컬 전체 스위트**(`uv run pytest server/tests -q` + `npm --prefix ui run test`)다. 카드를 닫기 전 전량 실행하고 기준선과 대조한다.

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC을 이어받는다(LXSEQ-001이 `ASSUMPTION-74`까지 썼다).

- **ASSUMPTION-75 — 닫힘 (2026-08-22 리드 실측, `origin/main` `e7a8e90` 기준 · `6296af3`에서 불변 확인).** **LX-SEQ 패치 CSV의 헤더 9열은 Vectorworks export CSV의 헤더와 겹치지 않는다.** 실물 VW export 헤더 25열을 `_normalize_header` 규약으로 정규화해 정규 9열과 대조한 결과 **일치 3 / 불일치 6**이다 — 있는 것은 `FixtureType`("Fixture Type") · `Universe` · `Position`, 없는 것은 `FID`(VW는 `UID`) · `Group` · `Mode`("Fixture Mode" → `fixturemode`) · `Ch`("Channel" → `channel`) · `Address`("DMX Address" → `dmxaddress`) · `AddrRange`다. 포함 검사가 둘을 깨끗이 가른다. 근거와 원문 헤더는 `research.md` §9 (b)가 소유한다. **남는 질문은 다른 것이다** — VW **자신의** 서명이 vwx fixture 7종의 변형을 견디는지는 별개이며 M1이 실측한다(견디지 못하면 결정 I의 안전판, REQ-FILEARG-018).
- **ASSUMPTION-76** — **운영자가 올리는 LX-SEQ 패치 CSV는 생성기 산출물 그대로다**(열 이름 변형 없음). NEGATIVE면 그 파일은 `unknown_sheet_kind`로 거절되고 운영자가 원본을 다시 내려받는다 — 계약 위반이 아니라 REQ-FILEARG-003이 정의한 결과다.
- **ASSUMPTION-77 — 닫힘 · POSITIVE (2026-08-23 실측).** **8 MiB 상한이 LX-SEQ 패치 CSV에 넉넉하다.** 실측: `wc -c server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` → **7,258 바이트**(약 7 KB). 8 MiB는 그 약 **1,150배**다. v0.2.0의 "수십 KB 규모"는 한 자릿수 오차로 틀린 서술이었고(약 7 KB가 맞다), 정정해도 결론은 바뀌지 않을 뿐 아니라 **더 강해진다**. 상한 조정은 필요 없다.

### PRESERVE — 무변경 대상

`server/lxseq/**`(소비만 — `CANONICAL_COLUMNS`·정규화 함수·파서 진입점) · `server/vwx/**` · `server/prechk/**` · `server/safety/**` · `server/paperwork/**` · `console/lua/**` · `server/rulebook/assets/**` · `server/web/session.py`의 기존 업로드 핸들러 두 본문 · `server/orchestrator/tools.py`의 기존 핸들러 본문 전부. 게이트: 착수 SHA 대비 위 경로의 변경 통계가 빈 출력이어야 한다(정확한 명령은 `acceptance.md` AC-FILEARG-016이 소유한다).

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — 002/003/004 시트의 파서와 핸들러

리드 결정 ③이 "일반화하는 것은 전달 수단이지 의미가 아니다"라고 못박은 자리다.

- 그룹 · 프리셋/FX · 시퀀스/큐 시트를 **판독**하는 코드는 0건이다. 레지스트리에 그 종류의 행을 미리 채우지도 않는다.
- 그 시트들의 대상 툴을 미리 만들지 않는다. 각 후속 SPEC이 자기 파서·툴과 함께 레지스트리 행 **하나**를 더한다(§G 부록).
- 레지스트리를 설정 파일·플러그인 로더로 확장하지 않는다. 오늘 필요한 것은 표 하나다.

### Out of Scope — 대상 툴의 계약 변경

- `import_lxseq_patch`의 인자 집합·스키마·설명문·페이로드 구조를 바꾸지 않는다. 시트 종류 인자·경로 인자를 새로 만들지 않는다(사전 확정 사실 5).
- `server/lxseq/{parser,mapper}.py`의 동작을 바꾸지 않는다. 본 SPEC은 `CANONICAL_COLUMNS`와 헤더 정규화 규약을 **읽어 쓸** 뿐이다.

### Out of Scope — 첨부 UI의 재설계

- 첨부 버튼을 둘로 늘리거나, 업로드 전에 종류를 고르게 하는 선택기를 넣지 않는다(2026-08-15 운영자 결정 유지).
- 드래그 앤 드롭 · 다중 파일 · 업로드 이력 보관 · 진행률 표시를 넣지 않는다.
- 레이아웃 이미지 경로(`upload_layout_image`)의 동작·문구·크기 상한을 바꾸지 않는다.

### Out of Scope — 콘솔 쓰기와 자동화

- 업로드 시점에 콘솔을 읽거나 쓰지 않는다. `preview`의 점유 판정·타입 해석도 이 카드의 경로에서는 일어나지 않는다(REQ-FILEARG-009).
- 새 Lua 생성기 · 새 OSC 경로 · 새 쓰기 경로는 0건이다. 쓰기는 여전히 `import_lxseq_patch` → `patch_fixtures` 위임뿐이다.

---

## E. 데이터 모델 (What — 구현 함수명 아님)

| 개체 | 필드 | 출처 |
|---|---|---|
| `DiscriminationPredicate` | 두 갈래 중 하나. **(A) 열 집합 술어** — `kind` + **(i) 정확 열 집합**(`exact_columns[]`, 헤더의 정규 열 집합이 그것과 정확히 같을 때만 일치) 또는 **(ii) 포함·배제 쌍**(`required_columns[]` + `forbidden_columns[]`); 오늘의 포함 검사는 (ii)에서 배제 목록이 빈 경우다. **(B) 위임 술어** — 기존 판독기의 판정을 호출하는 호출 가능한 것(바이트를 받아 "내 것인가"를 답한다) | REQ-FILEARG-016 · REQ-FILEARG-019 · §G |
| `SheetKindRow` | `kind`, `predicate`(위 둘 중 하나), `target`(툴 이름 또는 기존 세션 경로), `passthrough_args[]` | REQ-FILEARG-007 · §G |
| `Discrimination` | `matched[]`, `count`, `header_read[]`, `filename_hint`, `outcome ∈ {resolved, unknown_sheet_kind, ambiguous_sheet_kind}` | REQ-FILEARG-002~004 |
| `UploadedSheet`(세션 슬롯) | `content_base64`, `sha256`, `byte_length`, `kind`, `file_name`, `received_at` | REQ-FILEARG-006 |
| 업로드 직후 보고 | `kind`, `sha256`, `byte_length`, `rows_total`(+`parsed`, `rejected`) | REQ-FILEARG-010 |
| 래퍼 툴 거절 사유 | `no_uploaded_sheet` · `kind_mismatch` · `no_target_tool` · `unknown_sheet_kind` · `ambiguous_sheet_kind` (닫힌 집합) | REQ-FILEARG-013 |

---

## F. [HARD] 세 가지 성질 — 명시하지 않으면 조용히 무너진다

### 속성 A — 판별기는 첫 일치에서 멈추면 안 된다

`server/lxseq/parser.py:172-175`가 정규 열 **밖의 열을 관용**하므로, 포함 검사 서명의 대조는 "이 9열이 전부 있는가"이지 "열 집합이 정확히 같은가"가 아니다. 그러므로 어떤 시트가 다른 시트 서명의 **상위 집합**이면 두 종류에 동시에 맞는다. 조기 반환하는 판별기는 그런 상위 집합 충돌을 발견하지 못하고 먼저 등록된 종류로 조용히 보낸다. 따라서 판별기는 레지스트리 **전체**를 훑고, 일치 건수를 세고, 0이면 `unknown_sheet_kind`, 2 이상이면 `ambiguous_sheet_kind`로 거절한다(REQ-FILEARG-002~004).

**이 성질은 가설이 아니라 실측으로 확정됐다.** 리드가 후속 시트 7종의 헤더를 전부 읽었다(`research.md` §9 (c), `origin/main` `e7a8e90` 기준). 프리셋 시트 넷은 `ID,Name`을 공유하고 열이 각각 넷뿐이다. 구체적 반례 하나로 족하다 — `preset-col`의 서명을 포함 검사 `{ID, Name, Value}`로 쓰면 `preset-bm`의 헤더(`ID,Name,TargetGroup,Value`)도 그 서명을 만족한다. 그러면 `preset-bm`은 두 서명에 맞아 `ambiguous_sheet_kind`로 거절되고 **영구히 못 싣는 파일이 된다**. 즉 충돌은 LXSEQ-003에서 **반드시 발화한다**.

한 가지를 정확히 짚어 둔다 — 무너지는 것은 판별 **전략**이 아니라 서명의 **표현력**이다. 9열짜리 서명은 포함 검사만으로도 혼자 갈린다. 네 열짜리 헤더가 `ID`·`Name`·`Value`·`Purpose` 같은 일반명으로만 이뤄져 있으면 포함 검사로는 갈리지 않는다. 그래서 본 SPEC은 형식의 표현력을 넓히고(REQ-FILEARG-016), 레지스트리 행은 넓히지 않는다(REQ-FILEARG-017).

### 속성 B — 파서의 예외를 제어 흐름으로 쓰지 않는다

`_resolve_header_map`(`parser.py:122-135`)은 열 불일치를 `MissingColumnsError` 예외로 알린다. 후보 종류마다 `parse_patch_csv`를 시험 삼아 부르고 예외가 나는지로 종류를 정하면 ① 예외가 제어 흐름이 되고 ② 라우터가 파서 내부 구현에 묶이며 ③ 행 단위 거부(`RowRejection`)와 파일 단위 실패가 뒤섞인다. 그러므로 판별은 `CANONICAL_COLUMNS`와 `_normalize_header` 규약만 재사용하는 **가벼운 술어**로 하고, 진짜 파싱은 종류가 정해진 뒤 **한 번만** 돈다(REQ-FILEARG-005 · REQ-FILEARG-010).

### 속성 C — 래퍼 스키마의 부재는 구현 세부가 아니라 요구다

`file_content_base64`가 래퍼 스키마에 **없다**는 사실이 "모델이 바이트를 다루지 않는다"를 보장한다(사전 확정 사실 1). 이 부재는 편의를 위해 언제든 되돌릴 수 있는 종류의 것이므로 REQ-FILEARG-012로 못박고, `REQ-LXSEQ-016`으로 역추적한다.

---

## G. 부록 — 판별 술어 레지스트리 (정본)

**행의 형태가 바뀌었다.** v0.2.0까지 행은 `(kind, 헤더 서명, 대상 툴)`이었다. 지금은 **`(kind, 판별 술어, 대상 툴)`**이다. 이유는 §G.1이 소유한다.

| kind | 판별 술어 | 대상 | 통과 인자 화이트리스트 | 상태 |
|---|---|---|---|---|
| `patch` | **열 집합 서명** — 헤더 1행에 `FID` · `Group` · `FixtureType` · `Mode` · `Ch` · `Universe` · `Address` · `AddrRange` · `Position` 9열이 전부 있는가(포함 검사). 정본은 `server/lxseq/parser.py:18 CANONICAL_COLUMNS` | 툴 `import_lxseq_patch` | `action` · `name_prefix_mode` · `only_fids` · `mode_overrides` | **등록됨** |
| `vectorworks` | **기존 판독기에 위임** — `server/vwx/reader.py`의 판정을 그대로 부른다: ZIP 매직(`PK`)이면 xlsx/mvr 경로 · 아니면 헤더 행을 **탐색**하고(`_best_header_candidate`, 구분자도 점수로 고름) 찾은 헤더에 주소 계열 열이 있는지 본다(`reader.py:286`의 `has_address_family(header)`). 새 판정을 만들지 않고 **이미 있는 판정을 호출한다** | 기존 세션 업로드 경로 `upload_vectorworks_export` | 해당 없음 | **등록됨 (결정 I · 술어는 결정 K로 교정)** |
| `group` (예약) | LXSEQ-002가 정한다 | LXSEQ-002가 정한다 | LXSEQ-002가 정한다 | 미등록 |
| `preset-dim` / `preset-col` / `preset-bm` / `preset-pos` / `fx` (예약) | LXSEQ-003이 정한다 — 열 집합 술어를 쓰되 **포함 검사만으로는 갈리지 않는다**(§F 속성 A). 확장 형식(정확 열 집합 또는 포함·배제 쌍)을 써야 한다 | LXSEQ-003이 정한다 | LXSEQ-003이 정한다 | 미등록 |
| `cue-ex` (예약) | LXSEQ-004가 정한다 | LXSEQ-004가 정한다 | LXSEQ-004가 정한다 | 미등록 |

### G.1 왜 열 집합으로는 Vectorworks를 표현할 수 없는가 (감사 FAIL B1·B2·B3의 뿌리)

v0.2.0은 두 종류를 **하나의 열 집합 서명**으로 재려 했다. 그것이 설계 오류였고, 세 가지 결과를 낳았다. 근거는 `research.md` §10이 소유한다.

1. **zip에는 헤더 행이 없다.** `.mvr`·`.xlsx`는 ZIP 아카이브이고 `reader.py`는 확장자를 보지 않고 매직 바이트 `PK`로 가른다. 헤더 서명 판별기는 이런 바이트를 **필연적으로** `unknown_sheet_kind`로 떨어뜨린다 — 즉 (다)안을 기각한 바로 그 사유("살아 있는 기능을 회수한다")가 (나)안 **안에서** 되살아난다.
2. **헤더가 1행이라는 보장이 없다.** `reader.py`는 헤더 행을 **탐색**하고(`_best_header_candidate`) 구분자도 별칭 점수로 고른다. 열 집합 서명은 헤더의 **위치**도 **구분자**도 표현할 수 없다.
3. **서명 소유자를 잘못 적었다.** v0.2.0은 `server/vwx/columns.py`를 VW 서명의 정본이라 적었다. `columns.py`는 별칭 표이며 스스로 정본이 아니라고 밝힌다. `has_address_family`가 그 안에 있는 것은 사실이나, **판정**은 그 술어를 **탐색된 헤더에 적용하는 호출 지점** `reader.py:286`에 있다. 정본은 호출 지점이다.

**교정.** 행이 드는 것은 열 목록이 아니라 **술어**다(결정 K). LX-SEQ는 "1행에 이 9열이 있는가"라는 열 집합 술어를, Vectorworks는 "기존 판독기가 자기 것이라고 하는가"라는 위임 술어를 쓴다. 서로 다른 종류의 신원 검사를 하나의 형식에 욱여넣지 않는다.

### G.2 앞선 네 결정은 이 교정에서 전부 살아남는다

- **0건 → 거절**은 그대로 발화한다. 임의의 `.txt`는 `patch` 열 집합에도 맞지 않고 VW 판독기도 자기 것이라 하지 않으므로 일치 0건이 되어 `unknown_sheet_kind`로 거절된다.
- **2건 이상 → 거절**도 그대로다. 술어가 여럿 참이면 계수는 여전히 2 이상이고 `ambiguous_sheet_kind`로 거절된다(REQ-FILEARG-002·004 불변).
- **파서·핸들러 0건**도 그대로다. VW 술어는 **이미 있는 판정을 호출**할 뿐 새 판정을 만들지 않는다 — 결정 D의 정정된 뜻("파서·핸들러 없는 종류를 만들지 말라")에 어긋나지 않는다.
- **`.mvr` · `.xlsx` · 헤더 없는 탭 파일이 계속 동작한다.** 그것들을 오늘 분류하고 있는 바로 그 코드가 술어이기 때문이다.

**치른 값을 정직하게 적는다.** 레지스트리는 더 이상 **순수한 데이터 표가 아니다** — 행 하나가 호출 가능한 것을 든다. 그것이 이 교정의 비용이다. 다만 대안의 비용이 더 컸다: 헤더 탐색과 구분자 점수와 zip 매직까지 표현하도록 서명 형식을 넓히는 것은, 결국 `reader.py`를 선언형으로 다시 쓰는 일이고 그 사본은 반드시 드리프트한다.

**서명·술어는 정본을 참조하고 사본을 만들지 않는다.** `patch`는 `CANONICAL_COLUMNS`를, `vectorworks`는 `reader.py`의 판정을 **호출**한다. 열 이름도 판정 논리도 이 표에 옮겨 적지 않는다.

**후속 SPEC이 하는 일은 이 표에 행을 더하는 것이다.** 002 · 003 · 004는 각각 자기 파서와 대상 툴을 만들고 `{kind, 술어, 대상}` 줄을 추가한다. 판별기 · 슬롯 · 래퍼 툴 · UI 라우터는 손대지 않는다. 예약된 이름이 표에 없는 동안 그 종류의 시트는 REQ-FILEARG-008에 따라 `unknown_sheet_kind`로 거절된다 — 미구현이 조용한 통과가 되지 않는다.

---
## H. 참조 구현

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 래퍼 → 형제 툴 바이트 주입 | `server/orchestrator/tools.py:2944-2964` (`vectorworks_autopatch`, :2950 · :2961) | 래퍼 스키마에 바이트 인자를 두지 않고 핸들러가 주입하는 형태 |
| 세션 업로드 슬롯 | `server/web/session.py:2492-2508` (`_UploadedVectorworksExport`) · `:9655-9658` | 교체형 슬롯 저장 형태(단, 자동 실행은 계승하지 않는다) |
| 담기만 하는 업로드 | `server/web/session.py:9660-9688` (`upload_layout_image`) | 담고 안내만 내는 태도(리드 결정 ②) |
| 첨부 라우터 | `ui/src/App.tsx:625-635` · `:550` · `:824` | 버튼 하나 · 종류가 목적지를 고른다(2026-08-15 운영자 결정) |
| 프레임 송신 · 빌더 | `ui/src/useCopilotSocket.ts:332-351` · `ui/src/protocol.ts:503-510` · `:519-531` | UI는 프레임만 보내고 툴 호출을 조립하지 않는다 |
| 프레임 검증 · 디스패치 | `server/web/messages.py:81-83` · `:194` · `:227` · `server/web/app.py:494` · `:505` | 신규 프레임의 허용 목록 등재 · 검증 · 분기 자리 |
| 대상 툴 계약 | `server/orchestrator/tools.py:9253-9306` (`required` :9304, 설명문 :9264) · `.moai/specs/SPEC-COPILOT-LXSEQ-001/acceptance.md:273` | 닫힌 인자 집합 · 경로 인자 없음 |
| 헤더 규약 | `server/lxseq/parser.py:18` · `:118` · `:122-135` · `:172-175` | 정규 열 · 정규화 · 관용(속성 A) · 예외(속성 B) |
| 툴 등재 지점 | `server/orchestrator/tools.py:232 TOOL_NAMES` · `server/orchestrator/runner.py:137 _TOOL_TASKS` · `server/tests/test_tools.py:172` · `server/tests/test_runner_progress.py:303,307` | 6지점 등재(4지점이 아니다) |
| 현행 유일 호출자 | `server/tools/lxseq_e2e.py:261` | 이 카드가 대체하려는 개발용 경로 |

> **좌표 드리프트 주의.** 위 줄번호는 리드가 확정해 넘긴 것과 본 SPEC 작성 중 이 워크트리에서 관측한 것이 섞여 있다. 본 워크트리(`eb436e8`)에서 `ToolDefinition(name="import_lxseq_patch")`는 `tools.py:9226`, `TOOL_NAMES`는 `:232`, `import_lxseq_patch` 핸들러는 `:4418`, `handlers` 맵 등재는 `:9327`에서 관측됐다. 줄번호는 흔들리므로 M0가 **토큰 앵커로** 재확인한다. 그 뒤 워크트리가 `6296af3`으로 fast-forward됐으므로(중간 커밋 `e7a8e90` t17 · `6296af3` t20, 3커밋) 위 줄번호는 **한 세대 낡았다** — 재확인은 선택이 아니라 필수다.
