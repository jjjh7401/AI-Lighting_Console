---
id: SPEC-COPILOT-VWX-001
title: "Vectorworks 연계 1단계 — Instrument Data CSV/엑셀 가져오기 + 설계상 리그 모델 + precheck_patch 대조 리포트"
version: "0.1.7"
status: draft
created: 2026-08-05
updated: 2026-08-05
author: manager-spec
priority: P0
phase: "Phase 3 이후 차별화 기능 — P0 신설 항목(Vectorworks 연계 1단계, 자동 패치·MVR은 후속 SPEC으로 분리)"
module: "server/vwx/ (신규), server/orchestrator/tools.py (수정), server/prechk/ (재사용·무변경), server/paperwork/ (재사용·무변경), pyproject.toml (의존성 조건부 1건: openpyxl)"
lifecycle: spec-anchored
tags: "vectorworks, csv, excel, instrument-data, precheck, rig, import"
tier: L
related_specs: [SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-OVERLAP-001]
---

# SPEC-COPILOT-VWX-001 — Vectorworks 연계 1단계 — Instrument Data CSV/엑셀 가져오기 + 설계상 리그 모델 + precheck_patch 대조 리포트

> **본 SPEC은 `.moai/reports/ma3-copilot-overview.html` §7의 P0 항목**(원문 인용): *"P0. Vectorworks 연계 — 디자인 도면을 콘솔 셋업으로. Vectorworks Spotlight에서 확정한 조명 디자인(장비 종류·수량·패치·배치)을 그대로 가져와 콘솔 셋업의 출발점으로 씁니다. 세 단계로 나누면: 1단계 — 엑셀/CSV 장비 리스트 가져오기: Vectorworks가 내보내는 Instrument Data(픽스처 타입·수량·유니버스·주소·포지션)를 읽어 '설계상 리그' 모델을 만듭니다. 이미 있는 공연 전 점검(precheck_patch)과 붙이면 '도면 vs 실제 콘솔 패치' 차이 리포트가 바로 나옵니다 — 빠진 장비, 주소 충돌, 수량 불일치를 공연 전에 잡습니다. 2단계 — 자동 패치 생성: 차이 리포트에서 사람이 승인하면, 라이브 검증이 끝난 Lua 패치 기법(AddFixtures)으로 부족한 픽스처를 콘솔에 자동 패치합니다. 3단계 — MVR/GDTF 가져오기: MVR 파일(3D 배치+GDTF 장비 정의)을 파싱하면 무대 위 실제 좌표까지 확보됩니다."*
>
> **본 SPEC은 1단계만을 범위로 한다.** 2단계(자동 패치)와 3단계(MVR/GDTF)는 §D가 명시적으로 배제하고 후속 SPEC으로 분리한다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-05 | manager-spec | 최초 작성 (draft, Tier L). 출처는 `.moai/reports/ma3-copilot-overview.html` §7 P0 항목. **아티팩트 6종**(spec/plan/acceptance/design/research/progress). REQ **25건**, AC **26건**, ASSUMPTION **3건**(68~70), 마일스톤 **9개**(M0~M8), 라이브 세션 **0회**(§C가 근거를 적는다), clarification 마커 **0건**. Vectorworks 형식 조사(경로 A/B, 인코딩, 컬럼 별칭표, 주소 표현, 7가지 대조 함정)는 `research.md`가 소유. **승인 대기 1건** — 신규 의존성 `openpyxl` 채택 여부(§C, `plan.md` 사용자 접점). |
| 0.1.1 | 2026-08-05 | (run-phase worker) | **Implementation Kickoff Approval 확정.** `openpyxl` 신규 의존성 **승인** — 경로 B `.xlsx` 지원을 v1 범위에 포함(§C 갱신, §D `.xlsx` 조건부 Out-of-Scope 절 무효화 명시). 실물 Vectorworks export 샘플은 **여전히 미제공** — M0는 완료 처리하지 않고 BLOCKED로 유지, M1~M7은 합성 픽스처(문서 근거·실물 미검증)로 선행 진행한다(`progress.md` §E.2). |
| 0.1.2 | 2026-08-05 | (run-phase worker) | **실물 파일 투입이 드러낸 P0 결함 2건 수정 + 잔존 지적 1건 교정.** 결함 1(CR 전용 줄바꿈 예외 탈출)·결함 2(패치 출처 아닌 파일에 "이상 없음" 오발) 최초 수정 후, 결함 2의 핵심(사용자가 읽는 `summary_ko` 문장이 여전히 "차이 없음"으로 시작하던 거짓 안전 신호)이 잔존한다는 재현이 들어와 교정했다. `REQ-VWX-023` 문구를 이 규칙을 명시하도록 갱신(§B), `AC-VWX-022`/`AC-VWX-023`에 대응 기대 결과 각 1건 추가(비공허성 포함). 코드 변경 상세는 `progress.md` §E.2 이번 라운드 기록. |
| 0.1.3 | 2026-08-05 | (run-phase worker) | **거짓 안전 신호 3라운드째 — kind 열거를 불변식으로 대체.** v0.1.2의 미수행 판정이 `read_failures`의 특정 kind 2종(`not_patch_source`·`worksheet_block_undetected`)에만 걸려 있어, 그 목록에 없는 새 경로(주소 열은 있어 판독 자체는 성공하지만 `unit_number`/`channel`이 전부 공란이라 `join_key_conflicts`로 전 행이 탈락하는 경우 — `read_failures`는 빈 튜플)에서 정확히 같은 거짓 안전 신호가 다시 샜다(코디네이터 재현). `REQ-VWX-023`을 "설계상 리그 픽스처 0대 = 대조 미수행" **불변식**으로 재정의해 트리거 목록 열거 방식을 폐기했다 — 이제 원인이 무엇이든(판독 실패·조인키 충돌·그 밖의 무엇이든) 픽스처 0대이면 동일하게 처리된다. 기존 두 read_failure 경로의 사유 문구는 그대로 유지(회귀 테스트로 검증). |
| 0.1.4 | 2026-08-05 | (run-phase worker) | **M0 실물 샘플 수령 — PARTIAL.** `vectorworks_export_sample_with_data.csv`(25컬럼×10행, UTF-8 BOM·CRLF·쉼표)로 ASSUMPTION-68을 NEGATIVE 판정, 별칭 테이블에 `fixture_name`·`gdtf_fixture` 2개 정규 필드 승격(REQ-VWX-026)으로 해소. 신규 REQ 3건(REQ-VWX-026~028) 추가 — 컬럼 승격, 주소 3중 표현 교차검증(REQ-VWX-027), 설계 측 구간 겹침 판정(REQ-VWX-028). AC 3건(AC-VWX-027~029) 대응 추가. ASSUMPTION-69/70은 이 샘플로 미해소(전자는 위험 완화, 후자는 전혀 미검증) — `progress.md` §E.2 M0 절이 덮는 범위·안 덮는 범위를 상세히 기록. M0=PARTIAL, M8=BLOCKED 유지, run_status=partial-blocked 유지. |
| 0.1.5 | 2026-08-05 | (run-phase worker) | **조인 키 스코프 결함 수정 — 실사용 리그 대부분이 전멸하던 결함(코디네이터 재현).** `unit_number`를 전역 유일로 취급해 서로 다른 포지션의 동명 유닛(예: `Upstage Truss`의 `1`번과 `FOH`의 `1`번)을 같은 픽스처로 오판정·충돌 거부해 전 행이 탈락하던 결함을 고쳤다. M0 실물 샘플이 이를 못 잡은 이유는 그 샘플이 포지션 1종(`Upstage Truss`)뿐이라 우연히 통과했기 때문이다(Position이 유일했다는 것이 결함을 가린 것이지 해소한 것이 아니다). REQ-VWX-016/AC-VWX-016을 조인 키 우선순위(① `channel` 전역 유일 → ② `(position, unit_number)` 복합 키 → ③ 조인 불가)로 재정의. REQ/AC 개수는 불변(기존 항목의 내용·기대 결과만 갱신). 부수: 손으로 만든 합성 경로 B 워크시트 그리드로 그 휴리스틱 코드 경로가 최초로 실행됨을 확인(구조 탐지·소계 배제 정상 동작) — 합성물이므로 `ASSUMPTION-70`은 여전히 미해소. |
| 0.1.6 | 2026-08-05 | (run-phase worker) | **실물 샘플 3종(멀티시스템·절대주소전용·헤더없음) 투입 — P0 1건 + P1 2건 수정, ASSUMPTION-69 NEGATIVE 판정, M8 여전히 BLOCKED.** 결함 1(P0): System 2개 이상 관측 시 전 행을 차단하던 REQ-VWX-010을 재정의 — 주소 아이덴티티를 `(system, universe, address)`로 확장해 설계 측 산출(픽스처 목록·수량·내부 충돌·미패치·멀티셀)은 System 수와 무관하게 항상 내고, **콘솔 대조만**(System→콘솔 유니버스 매핑 부재) 별도로 미수행 처리한다(REQ-VWX-023에 멀티시스템 사유를 일반 판독 실패와 구분해 추가). 결함 2(P1): 집계행(SUBTOTAL/TOTAL)·비-DMX 액세서리를 "판독 실패"로 오세던 것을 `excluded_rows`(REQ-VWX-007 확장)로 분리 — `summary_ko`가 "판독 실패 N건 · 제외 M건(...)" 형태로 두 사건을 절대 뭉뚱그리지 않는다. 결함 3(P1): 헤더 없는 경로 A 파일의 행별 실패 폭주(N건)를 파일 단위 판정 1건 + 실행 가능한 해결책으로 압축(REQ-VWX-001 확장) — 헤더 유무 스니퍼 자체는 정확했음을 긍정 증거로 기록. REQ-VWX-014를 "Static Accessory 문자열 리터럴"에서 "실제 DMX 점유(footprint) 기준"으로 재정의 — 같은 `"Accessory"` 리터럴을 쓰는 DMX 소비/비소비 액세서리를 실물로 구분해야 했다. REQ-VWX-016에 액세서리 carve-out 추가(액세서리는 channel 우선순위를 건너뛰고 `(position, unit_number)`로 직행 — 부모와 channel을 공유하는 액세서리가 잘못 접히는 결함 방지). ASSUMPTION-69는 **NEGATIVE로 판정**(Absolute Address 단독으로는 System을 구분할 수 없음을 실물로 확인, System 필드 보존이 유일한 해법). ASSUMPTION-70은 **PARTIAL 유지**(단일 최상단 헤더+인라인 집계행 변형은 이제 실물 확인됐으나, 헤더 반복형·제목행 선행형은 여전히 미검증). M8은 6개 검증 항목이 전부 통과했음에도 ASSUMPTION-70이 부분 미해소이므로 **여전히 BLOCKED로 유지**(§E.2 참조, 판단 근거 기록). REQ/AC 개수는 불변(28/29, 기존 항목 내용만 갱신). |
| 0.1.7 | 2026-08-05 | (run-phase worker) | **02(절대주소 단독) 재설계 — 거부 대신 근거 등급으로 역산, 대량 탈락 스코프 한정.** REQ-VWX-009 재정의: Universe/DMX Address 쌍이 없고 Absolute Address만 있으면 이제 **항상** `abs=(u-1)*512+a`로 역산한다("전제를 확인할 수 없으니 거부"가 아니라 `server/prechk/patch.py`의 `OverlapBasis` 규약 — 날조 금지이지 파생 금지는 아니다). 파생 근거는 픽스처마다·리그 전체에 등급(`address_basis`: `universe_address_direct` > `absolute_confirmed` > `absolute_back_calculated`, 가장 약한 것이 리그 전체 등급)으로 표기하고, 등급이 역산이면 명시적 전제 문구("Universes pane이 기본 연속 512블록이라는 전제 위에서 역산했다…")를 payload·`summary_ko`에 싣는다. 하드 거부는 Universe/DMX Address와 Absolute가 **둘 다 있는데 어긋나는** 경우(REQ-VWX-027 `address_triple_mismatch`)에만 남는다. 결함 2(P1): 컬럼 해석을 통과한 후보 행 중 주소 해석 단계에서 진짜로 탈락한 행이 있으면(`scope_qualified`) 대조 결과에 스코프 한정을 붙인다(`server/prechk/patch.py`의 `scope_qualified`/`scope_note` 규약을 vwx 자체로 재구현) — 탈락 비율 30% 이상이면 `summary_ko`가 "도면 픽스처 N개"보다 탈락 사실을 먼저 말한다. 집계행·비-DMX 액세서리 같은 의도적 제외는 탈락으로 세지 않는다(분모는 "읽으려 했으나 실패한 행"). `ASSUMPTION-69` 판정을 재작성 — v0.1.6의 "NEGATIVE(미해소)"는 구현(거부)과 판정문이 일치했으나, 이번 재설계로 구현이 "선언된 전제 위에서 역산 지원"으로 바뀌었으므로 판정문도 그에 맞춰 갱신했다(System 구분 불가라는 관측 자체는 유지되지만, "그래서 거부한다"가 아니라 "그래서 System을 근거 축과 별개로 보존해 역산을 지원한다"로 결론이 바뀌었다). REQ/AC 개수는 불변(28/29 — REQ-VWX-009/014/016 등 기존 항목 내용만 갱신, 신규 번호 없음). M8/ASSUMPTION-70은 이 라운드가 손대지 않는다(제목행 선행형 실물 워크시트 부재는 여전히 정확한 기록) — 여전히 BLOCKED/PARTIAL. |

---

## A. 개요

**한 줄**: Vectorworks가 내보내는 Instrument Data(엑셀/CSV/tab-text)를 읽어 **설계상 리그(designed rig)** 모델을 만들고, 이미 있는 `precheck_patch`(콘솔 실측)와 대조해 **"도면 vs 실제 콘솔 패치"** 차이 리포트를 낸다 — 빠진 장비, 주소 충돌, 수량 불일치를 공연 전에 잡는다.

본 SPEC은 **읽고 대조만** 한다. 콘솔에 아무것도 쓰지 않는다 — 자동 패치(2단계)와 MVR/GDTF 좌표 확보(3단계)는 §D가 명시적으로 배제한다.

### 사전 확정 사실 (조사 확정 — 재질의 금지)

1. **Vectorworks export는 하나의 포맷이 아니라 두 경로다.** (A) `File > Export > Export Instrument Data` — **tab-delimited text 전용**(csv도 xlsx도 아니다), 헤더 존재 여부는 체크박스로 선택적이며 `UID` 열이 자동 추가된다. (B) `File > Export > Export Worksheet`(Instrument Data 워크시트에서) — `.xls/.xlsx/.txt(tab)/.csv/.dif/.slk`를 낼 수 있으나 파일 자체가 **워크시트 그리드**(제목행 + DB 헤더행 + 개체별 서브행 + 소계행이 한 파일에 섞임)다. 사용자의 "CSV/엑셀" 표현은 경로 B를 가리킨다(`research.md` §1). 파서는 **확장자만으로 구분자를 단정하지 않는다.**
2. **`Instrument Summary`는 패치 출처가 아니다.** 도면 오브젝트 썸네일·수량용 리포트이며 **주소 열이 아예 없다**(`research.md` §1). 발견되면 거부한다.
3. **FID/CID 기반 픽스처 아이덴티티 대조는 이 단계에서 원리적으로 불가능하다.** `server/prechk/inventory.py:57 PROPERTY_WHITELIST`는 `Patch`·`FixtureType`·`Mode`·`Name` 4종만 읽고, 콘솔 슬롯과 FID가 우연히 일치하는 캘리브레이션 쇼파일에서는 **올바른 FID 프로브와 슬롯 프로브를 구별할 수 없다**(`console/lua/PROTOCOL.md:305-324`, `server/rulebook/assets/v2.4.2/20_korean_terms.md:34-36`, `server/rulebook/assets/v2.4.2/31_choreography_patterns.md:203-209`). 따라서 본 SPEC의 대조 조인 키는 **(유니버스, 주소) + 픽스처 타입**이며, ID 대조는 `SkippedCheck`/`not_performed` 구조로 명시한다(REQ-VWX-018, REQ-VWX-019) — 숨기지 않는다.
4. **실물 Vectorworks export 샘플이 이 저장소에 없다.** 저장소 전체 grep에서 `.gitignore`의 `.Spotlight-V100` 노이즈와 무관한 문자열 일치 외에는 아무것도 없다(`research.md` §0). **컬럼 계약은 실물 파일 없이 동결하지 않는다** — M0가 사용자 제공 실물 export를 선행조건으로 요구한다(§C).

### 조사가 확립한 제약 — 본 SPEC이 이 위에 선다

1. **주소는 콘솔의 단일 `<유니버스>.<주소>` 표기와 달리 Vectorworks가 4가지 동시 표현을 갖는다** — `Universe/Address`(구분자 가변, 기본 `/`, 무제로패딩) · `Universe`(정수) · `DMX Address`(1..512) · `Absolute Address`(`(u-1)*512+a`, **Universes 창이 연속 기본 512블록일 때만** 안전하다). `DMX Address`/`Absolute Address`가 `0`이거나 공란이면 **"미패치"**이며, 이것은 "콘솔에 없음"과 다른 **제3의 분류**다(`research.md` §Address).
2. **컬럼 헤더는 별칭 테이블로만 해석한다.** 같은 값이 파일 버전에 따라 `U Dimmer`/`User U Address`/`DMX Address`/`User Address` 등 여러 철자로 나타난다(`research.md` §Address). 위치 기반 파싱은 금지한다.
3. **대조에는 7가지 알려진 함정이 있다** — 멀티셀 픽스처, 액세서리 오분류, 타입/모드 명칭 불일치, 미패치 오분류, 파일 내부 조인키 중복, Vectorworks 자체 패치 충돌 통과, 멀티시스템(A-Z) 유니버스 혼동(`research.md` §Pitfalls). 각각 REQ로 승격했다.
4. **인코딩은 문서화되어 있지 않다.** BOM 스니프를 우선하고, 실패 시 순차 폴백하며, 모지바케를 조용히 삼키지 않는다(`research.md` §Encoding).

---

## B. 요구사항 (GEARS)

### B.1 가져오기 (Import)

- **REQ-VWX-001** `[Ubiquitous]` The 가져오기 파서 **shall** Vectorworks **경로 A**(`Export Instrument Data`, tab-delimited text) 파일을 판독한다. 헤더 존재 여부는 첫 행의 별칭 테이블 매칭 개수로 스니핑하며, 확장자를 구분자 판단에 쓰지 않는다. **(v0.1.6 — 헤더 없음 파일 단위 판정)** **When** 헤더 스니핑이 "헤더 없음"(체크박스 미선택)을 식별하면, the 가져오기 파서 **shall** 위치 기반 의미 해석을 시도하지 않고(추측 금지, REQ-VWX-005) 컬럼 해석 단계에서 행마다 개별 판독 실패를 내는 대신 **파일 단위 판정 1건**("Export field names as first record"를 켜고 재수출하라는 실행 가능한 해결책 포함)으로 보고한다 — 헤더 유무 스니퍼 자체가 정확히 판정했다는 사실은 실패가 아니라 이 요구사항의 **긍정 증거**다.
- **REQ-VWX-002** `[Ubiquitous]` The 가져오기 파서 **shall** Vectorworks **경로 B**(`Export Worksheet`, xls/xlsx/txt/csv) 파일에서 **데이터 블록을 구조적으로 식별**한다 — 별칭 테이블 컬럼명을 2개 이상 해석 가능한 첫 행을 헤더 후보로 삼고, 그 아래 컬럼 수가 연속으로 일치하는 구간만 레코드로 채택한다. 문서화된 구획 마커는 존재하지 않는다(`research.md` §Path B).
- **REQ-VWX-003** `[Unwanted]` The 가져오기 파서 **shall not** `Instrument Summary` 리포트(주소 열이 없는 요약)를 패치 출처로 채택한다. 발견 시 판독 실패로 분류하고 사유를 리포트에 싣는다.
- **REQ-VWX-004** `[Event-driven]` **When** 파일 인코딩이 불확실하면, the 가져오기 파서 **shall** BOM 스니프 → `utf-8-sig` → `utf-16` → `cp1252` → `mac_roman` 순으로 판독을 시도하고, 전부 실패하면 **바이트 오프셋과 함께 명시적으로 실패**한다 — 모지바케 상태로 조용히 통과시키지 않는다.

### B.2 컬럼 해석과 정규화

- **REQ-VWX-005** `[Ubiquitous]` The 컬럼 해석기 **shall** 대소문자·공백·구두점을 무시하는 **별칭 테이블**로 컬럼을 매칭한다(`research.md`의 별칭표가 정본). 위치(순번) 기반 매칭은 금지한다.
- **REQ-VWX-006** `[Ubiquitous]` The 컬럼 해석기 **shall** 별칭 테이블 밖의 컬럼을 폐기하지 않고 레코드의 `extra` 딕셔너리에 원문 그대로 보존한다.
- **REQ-VWX-007** `[Event-driven]` **When** 레코드가 최소 유효 조건(`instrument_type` + 해석 가능한 주소 표현 하나)을 만족하지 못하면, the 컬럼 해석기 **shall** 그 레코드를 **구조화된 판독 실패**로 분류하고 판정에 쓰지 않는다 — 예외를 던지지 않는다. **(v0.1.6 — 판독 실패와 의도적 제외를 분리)** **Where** 미달 레코드가 워크시트 집계행(`Device Type` == SUBTOTAL/TOTAL) 또는 해석 가능한 주소 표현이 없는 액세서리 계열 행이면, the 컬럼 해석기 **shall** 이를 판독 실패가 아니라 별도의 **`excluded_rows`**(제외행, 사유 코드 `aggregate_row`/`non_dmx_accessory`)로 분류한다 — "읽을 수 없었다"와 "읽었지만 의도적으로 제외했다"는 서로 다른 사건이며, 대조 리포트(`summary_ko`)는 두 건수를 절대 뭉뚱그리지 않는다.

### B.3 주소 처리

- **REQ-VWX-008** `[Event-driven]` **When** `DMX Address` 또는 `Absolute Address`가 `0`이거나 공란이면, the 주소 해석기 **shall** 그 픽스처를 **"설계됨·미배정"**으로 별도 분류한다 — "콘솔에 없음"(대조 단계의 결과)과 혼동하지 않는다.
- **REQ-VWX-009** `[Where]` **Where** 파일이 `Universe`/`DMX Address` 쌍 컬럼도 `Universe/Address` 조합값도 갖지 못해 `Absolute Address` 단일값에서 유니버스·주소를 파생해야 하면, the 주소 해석기 **shall** `abs=(u-1)*512+a` 역산을 **항상** 수행한다. **(v0.1.7 — 재정의, 02 재설계 P0)** v0.1.6까지는 "그 파일의 Universes 창이 연속 기본 512블록이라는 전제가 검증 가능할 때만" 역산했고, 검증 불가면 판독 실패로 거부했다 — 그 결과 절대주소 단독 export(사용자가 실제로 제공한 정상 형식, VW 2019 이하 기본 컬럼 구성)가 사실상 통째로 미지원이었다(코디네이터 재현: 유효 16행 중 15행 탈락). 리포 교리는 **날조 금지**이지 **파생 금지**가 아니다 — `server/prechk/patch.py`의 `OverlapBasis`(판정을 거부하는 대신 실제로 수행한 비교의 가장 약한 근거를 등급으로 선언하는 규약)를 그대로 따라, 전제를 검증할 수 없어도 역산을 수행하고 그 근거를 **약한 등급**(`absolute_back_calculated`)으로 낮춰 표기한다 — 숨기지 않는다. 근거 등급은 픽스처마다, 그리고 리그 전체(가장 약한 것)에 표기하며(`address_basis`: `universe_address_direct` > `absolute_confirmed` > `absolute_back_calculated`), 리그 전체 등급이 `absolute_back_calculated`면 명시적 전제 문구(payload `address_basis_note` + `summary_ko`)를 함께 싣는다: "Universes pane이 기본 연속 512블록이라는 전제 위에서 역산했다. Start#/End#를 편집했거나 유니버스를 삭제해 구멍이 있으면 이 유니버스·주소는 틀린다." 하드 거부는 **좁혀졌다** — Universe/DMX Address 쌍과 Absolute Address가 **둘 다 있는데 서로 어긋나는** 경우(REQ-VWX-027 `address_triple_mismatch`)에만 남는다; 그때는 역산하지 않고 직접값을 그대로 쓴다. `contiguous_512_confirmed`를 외부에서 명시적으로 참으로 주입한 경우(예: 사용자가 Universes pane을 직접 확인)에는 더 강한 등급(`absolute_confirmed`)을 매기고 전제 문구를 생략한다.
- **REQ-VWX-010** `[Event-driven]` **When** 파일에서 System 문자(A-Z) 2개 이상이 관측되면, the 시스템 **shall** 주소 아이덴티티를 **`(system, universe, address)`로 확장**해 설계 측 해석·산출(픽스처 목록·수량·내부 주소 충돌·미패치 목록·멀티셀 폴딩)을 System 수와 무관하게 정상 수행한다 — System 컬럼이 없으면 단일 암묵 스코프로 취급한다. **(v0.1.6 — 재정의, 코디네이터 재현 결함 1 P0)** v0.1.5까지는 System 2개 이상에서 순수 `Universe` 해석 자체를 모호로 차단해 설계 측 산출이 전멸했다(`fixture_count=0`) — 콘솔에는 System 개념이 없어 **System→콘솔 유니버스 매핑이 없을 때만** 대조기(§B.5)가 콘솔 조인(missing_in_console/quantity_mismatch)을 별도로 미수행 처리하며, 그 사유는 일반 판독 실패와 뭉뚱그리지 않고 "멀티시스템 매핑 부재"로 명시한다(REQ-VWX-023).
- **REQ-VWX-011** `[Ubiquitous]` The 주소 해석기가 산출하는 정규화 표현(유니버스 정수, 주소 정수)은 `server/prechk/patch.py:118 normalize_address`가 산출하는 `AddressParse`와 **동일한 표현 규약**을 따른다 — 값을 재사용하는 것이 아니라 표현 형태(정수 튜플)를 일치시켜 대조 단계(§B.5)가 하나의 비교 로직만 갖게 한다.

### B.4 설계상 리그(designed rig) 모델

- **REQ-VWX-012** `[Ubiquitous]` The 시스템 **shall** 파싱된 레코드를 정규화하는 **설계상 리그(designed rig)** 도메인 모델을 생성한다 — 콘솔 슬롯 대응이 아니라 도면이 선언한 장비 목록의 구조화된 표현이다.
- **REQ-VWX-013** `[Event-driven]` **When** 동일 픽스처의 여러 셀/액세서리 행이 `Part Index` 컬럼으로 관측되면, the 시스템 **shall** 대조 전에 **논리적 픽스처 1개로 접는다** — 셀 N행 = 픽스처 1대는 정상이며 위양성 수량 불일치로 세지 않는다.
- **REQ-VWX-014** `[Ubiquitous]` The 시스템 **shall** `Device Type` 컬럼으로 Light-class와 비-DMX 액세서리를 대조 계수 이전에 **필터링**한다. 비-DMX 액세서리는 콘솔 패치 대상이 아니다. **(v0.1.6 — 문자열 리터럴 대신 실제 DMX 점유 기준으로 재정의, 결함 2 P1)** 배제 기준은 `"Static Accessory"` 문자열 리터럴이 아니라 **실제 DMX 점유 여부**(액세서리 계열 + 양수 `DMX Footprint` 부재)다 — 실물 샘플은 DMX를 소비하는 액세서리(스크롤러 등)와 소비하지 않는 액세서리(Top Hat 등)가 **똑같이** `"Accessory"` 리터럴을 쓴다.
- **REQ-VWX-015** `[Unwanted]` The 시스템 **shall not** Vectorworks 타입·모드 표시 문자열과 콘솔 타입·모드 표시 문자열을 **동등 비교(`==`)**로 판정한다. 별칭·퍼지 매칭을 쓰고, 해결되지 않으면 **미해결 표시**를 판정에 남긴다 — 둘의 명명 체계는 서로 다른 소스에서 온다.
- **REQ-VWX-016** `[Event-driven]` **When** 파일 내부에서 조인 키가 중복이거나 공란인 레코드가 2개 이상이면, the 시스템 **shall** 자동 last-write-wins 병합을 **거부**하고 그 충돌을 판독 실패로 보고한다. **(v0.1.5 — 조인 키 스코프 수정)** 조인 키 우선순위는 ① `channel`(Vectorworks **전역 유일** 디자이너 번호, 비숫자 가능 — 문자열로 다룬다) → ② `(position, unit_number)` **복합 키**(channel이 없거나 공란일 때만) → ③ 둘 다 없으면 조인 불가로 거부다. `unit_number`는 **포지션 안에서만 유일**하다(Vectorworks 문서·브리핑이 명시한 함정) — `unit_number`만으로 전역 조인하면 서로 다른 포지션의 동명 유닛이 충돌로 오판정돼 포지션이 2개 이상인 실사용 리그가 전멸한다(코디네이터 재현 결함). 충돌 판정은 그 스코프(channel 값 또는 (position, unit_number) 조합) 안에서만 성립하며, 충돌 보고 사유에 어느 스코프에서 중복인지 명시한다. **(v0.1.6 — 액세서리 carve-out, 결함 4 P1)** `Device Type`이 액세서리 계열을 표시하는 레코드는 ① channel 우선순위를 **건너뛰고** 곧바로 ②`(position, unit_number)`로 조인한다 — 액세서리는 부모 픽스처의 channel 번호를 그대로 물려받으므로, channel 우선 조인을 적용하면 부모와 액세서리 여러 개가 서로 다른 유닛인데도 하나로 잘못 접힌다(직전 라운드 조인-키-스코프 수정 자체가 만든 구멍).
- **REQ-VWX-017** `[Ubiquitous]` The 시스템 **shall** Vectorworks 자체 패치 충돌 분류(Patch overlap · Identical Patch · Patch conflict)를 **판정 실패로 만들지 않고 구조화된 부류로 통과**시킨다 — MA3의 `Multipatch` IDType과 동형으로 취급한다.

### B.5 precheck_patch 대조

- **REQ-VWX-018** `[Unwanted]` The 대조기 **shall not** 대조 조인 키로 `FID` 또는 `CID`를 사용한다. 조인 키는 **(유니버스, 주소) + 픽스처 타입**에 한정한다(§A 사전 확정 사실 3).
- **REQ-VWX-019** `[Ubiquitous]` The 대조기 **shall** `FID`/`CID` 기반 아이덴티티 대조가 이 쇼파일로 원리적으로 수행 불가함을 `server/prechk/patch.py:188 SkippedCheck`와 동형인 **`not_performed` 구조**로 명시한다 — 산문으로 흘리지 않는다.
- **REQ-VWX-020** `[Ubiquitous]` The 대조 리포트 **shall** 최소 3부류를 싣는다 — ① 도면에는 있으나 콘솔에 없는 장비(missing_in_console), ② 실제 주소 충돌(콘솔 실측 기준), ③ 도면·콘솔 간 수량 불일치. 각 부류는 관여 항목 전량을 열거한다(집계만 내지 않는다). **(v0.1.7 — 스코프 한정 추가, 02 재설계 P1)** **When** 컬럼 해석을 통과한 후보 행 중 일부가 주소 해석 단계에서 진짜로 탈락(판독 실패)하면, the 대조 리포트 **shall** 그 대조 결과에 **스코프 한정**(`scope_qualified`/`scope_note`)을 붙인다 — `server/prechk/patch.py`의 `scope_qualified`/`scope_note`/"관측된 범위에서" 규약을 vwx 자체로 재구현한다(그 파일은 PRESERVE라 import하지 않는다). 탈락 비율이 30% 이상이면 `summary_ko`는 "도면 픽스처 N개"보다 탈락 사실을 **먼저** 말한다 — 대량 탈락 후 소수 픽스처만으로 낸 수량 불일치 판정이 확신에 찬 것처럼 읽히지 않게 한다. 집계행·비-DMX 액세서리처럼 컬럼 해석 이전에 **의도적으로 제외**된 행은 탈락으로 세지 않는다 — 분모는 "읽으려 했으나 실패한 행"이다. 탈락 0건이면 스코프 한정은 전혀 붙지 않는다(비공허성).
- **REQ-VWX-021** `[Where]` **Where** 도면에서 `DMX Footprint` 폭 출처가 확보되면, the 대조기 **shall** `server/prechk/patch.py:440 _range_overlaps`를 재사용해 **구간 겹침** 확장 판정을 수행한다(`FootprintPolicy.enabled=True`로 주입). 확보되지 않으면 이 축은 미수행으로 보고한다(REQ-VWX-019와 같은 구조).
- **REQ-VWX-022** `[Ubiquitous]` The 대조기 **shall** 콘솔 실측 데이터를 `server/prechk/inventory.py:344 read_inventory` 또는 `server/paperwork/data.py:67 build_patch_sheet`를 통해서만 얻는다. 신규 모듈은 `server.bridge`를 **직접 import하지 않는다**.

### B.6 보고 · 경계

- **REQ-VWX-023** `[Ubiquitous]` The 대조 리포트 **shall** 판독 실패·데이터 블록 미탐·미수행 판정·부정 전제를 모두 **구조화된 페이로드 부류**로 담는다 — 예외 산문으로 흘리지 않는다. **(v0.1.3 — 불변식으로 재정의)** **설계상 리그 픽스처가 0대이면 대조를 수행한 것이 아니다** — 트리거가 판독 실패(주소 열 없음·데이터 블록 미탐)이든, 파일 내부 조인키(`unit_number`/`channel`) 충돌로 전 행이 탈락한 경우이든, 그 밖의 어떤 원인으로 픽스처가 0대가 되든 동일하게 적용된다. 이때 `diffs`는 빈 배열 3종이 아니라 `performed: false` + 실제 원인을 지목하는 사유로 미수행임을 구조적으로 드러내며, `summary_ko`는 "차이 없음"을 말하지 않고 그 사유로 시작한다 — 대조를 수행하지 않은 상태를 "찾아봤는데 없다"로 오독시키지 않는다. **트리거는 kind 목록 열거가 아니라 픽스처 수 0건이라는 결과로 판정한다** — 특정 kind에만 매칭하는 방식은 목록에 없는 새 경로(조인키 충돌 등)에서 반드시 새기 때문이다(`progress.md` §E.2 v0.1.3 라운드). **(v0.1.6 — 멀티시스템 사유 분리, 결함 1 P0)** 설계 픽스처가 1대 이상이어도 System이 2개 이상 관측되면(REQ-VWX-010) `diffs`는 여전히 `performed: false`다 — 이때의 `reason`은 "픽스처 0대" 원인(`_no_fixtures_reason`)과 **절대 뭉뚱그리지 않고** "System→콘솔 유니버스 매핑이 없어 콘솔 대조를 수행하지 않았다"는 멀티시스템 전용 문구를 쓰며, `skipped_checks`에 관측된 System 문자 집합과 함께 "매핑이 주어지면 수행 가능하다"를 명시한다.
- **REQ-VWX-024** `[Ubiquitous]` 사용자 대면 문자열 **shall** 한국어이며 표현 계층 코드에 둔다. 라벨 재사용은 `server/prechk/report.py:143 label()`의 공개 접근자를 통하며 밑줄 식별자를 직접 import하지 않는다.
- **REQ-VWX-025** `[Ubiquitous]` The 신규 대조 리포트 툴 **shall** `server/orchestrator/tools.py`의 **`TOOL_NAMES`·핸들러 클로저·`definitions`·`handlers`** 전 지점에 등재되며, 신규 REST 라우트·웹소켓 메시지·`execution_port` 직접 접근을 **0건**으로 유지한다.
- **REQ-VWX-026** `[Ubiquitous]` **(v0.1.4 — M0 실물 샘플 ASSUMPTION-68 NEGATIVE 반영)** The 컬럼 해석기 **shall** `Fixture Name`을 정규 필드 `fixture_name`으로, `GDTF Fixture`를 정규 필드 `gdtf_fixture`로 해석한다. `fixture_name`은 `symbol_name`과 별개 필드다(합치지 않는다). 타입 퍼지 매칭(REQ-VWX-015)은 `gdtf_fixture`가 있으면 그것을 우선 사용하고, 없으면 `instrument_type`으로 폴백한다.
- **REQ-VWX-027** `[Where]` **(v0.1.4)** **Where** `Universe`·`DMX Address`·`Absolute Address` 세 표현이 모두 존재하면, the 주소 해석기 **shall** `absolute == (universe-1)*512 + address` 공식으로 교차검증한다. 불일치 시 **Absolute Address로 유니버스를 역산하지 않고**(추측 금지, REQ-VWX-009와 동일 원칙) `Universe`+`DMX Address` 조합을 그대로 채택하며, 구조화된 경고(`address_triple_mismatch`)로 보고한다.
- **REQ-VWX-028** `[Where]` **(v0.1.4)** **Where** `DMX Footprint` 컬럼이 해석되면, the 대조기 **shall** 설계 도면 내부에서 (유니버스, 주소, 폭)만으로 주소 구간 겹침을 판정한다(콘솔 SLOT 키가 필요한 `FootprintPolicy.widths`는 쓰지 않는다 — `server/prechk/**` PRESERVE). `DMX Footprint`가 없으면 이 판정은 기존과 같이 미수행으로 보고한다. 콘솔 측 폭 주입((유니버스,주소) 조인 이후 2차 작업)은 이 SPEC의 범위 밖이며, 설계 측 판정이 수행됐을 때 그 사실을 별도 미수행 판정(`console_footprint_width_injection_deferred`)으로 남긴다.

---

## C. 환경 및 전제

### 측정된 기준선

착수 SHA **`b1a630eb9380fd37436252e366289350bd22feff`**에서 **직접 실측**한 값은 `uv run pytest server/tests -q` → **4716 passed · 7 skipped · 1 warning · 91.35s(0:01:31)**다. 각 마일스톤은 착수 직전 직접 실측하며 이월 인용을 금지한다.

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC 이후를 이어받는다(GROUPGEN이 `ASSUMPTION-67`까지 썼다, `.moai/specs/SPEC-COPILOT-GROUPGEN-001/spec.md:324`).

- **ASSUMPTION-68** — **별칭 테이블의 실효성. `PARTIAL — NEGATIVE 판정, 확장으로 해소(v0.1.4)`.** M0 실물 샘플(`vectorworks_export_sample_with_data.csv`, 25컬럼×10행, UTF-8 BOM·CRLF·쉼표) 투입 결과 **부정**이었다 — 실물 컬럼 10개(`Fixture Name`·`GDTF Fixture`·`Gobo`·`Focus`·`X`·`Y`·`Z`·`Rotation Z`·`Pan`·`Tilt`)가 원래 별칭 테이블 밖으로 떨어졌다. 이 중 결정적인 2개(`Fixture Name`→`fixture_name`, `GDTF Fixture`→`gdtf_fixture`)를 정규 필드로 승격해 별칭 테이블을 확장했다(REQ-VWX-026). 나머지 8개(Gobo/Focus/X/Y/Z/Rotation Z/Pan/Tilt)는 이번 SPEC 범위 밖이며 `extra`로 계속 보존된다(REQ-VWX-006) — 확장 상세는 `progress.md` §E.2 M0 절. **(v0.1.6 추가 증거)** 실물 샘플 3종의 좌표 컬럼 철자는 `X Location`/`Y Location`/`Z Location`/`Z Rotation`으로, M0 샘플의 `X`/`Y`/`Z`/`Rotation Z`와 **또 다르다** — 두 실물 파일이 같은 개념(3D 좌표)을 서로 다른 철자로 내보낸다는 사실이 별칭표 확장 정책 자체를 뒷받침하는 추가 증거다(둘 다 이번 SPEC 범위 밖 필드라 `extra` 보존은 그대로 유지, 별칭 승격은 하지 않음). 새로 관측된 `Notes` 컬럼도 마찬가지로 `extra` 보존 대상이다.
- **ASSUMPTION-69** — **`Absolute Address` 단일값만 있는 파일의 존재. `GO — 선언된 전제 위에서 역산 지원(v0.1.7 재판정)`.** `vectorworks_worksheet_absolute_address_only.csv`(Universe/DMX Address 컬럼 없음, Absolute Address만 존재)로 이 경로가 실제 실행됐다 — 사용자가 직접 제공한 정상 export이며 VW 2019 이하 기본 컬럼 구성이기도 하다(가상의 엣지 케이스가 아니다). **v0.1.6의 판정문("NEGATIVE — 원리적으로 구분 불가")은 관측(System을 구분할 수 없다는 사실)은 맞았지만 결론(그래서 미해소로 남긴다)이 구현과 어긋났다** — 실제로는 이 파일을 통째로 거부해 리그의 94%(16행 중 15행)를 죽이고 있었다. v0.1.7이 판정문을 구현에 맞춰 재작성했다: System 문자가 `fields["system"]`으로 **별도 보존**되지 않으면 Absolute Address 단독으로는 두 System의 같은 절대주소값(예: A/U1/abs=1과 B/U1/abs=1)을 원리적으로 구분할 수 없다는 관측은 **여전히 참**이다 — 하지만 그 결론은 "그래서 역산을 거부한다"가 아니라 **"그래서 System을 주소 근거 축과 별개로 보존해 역산을 지원한다"**다. 결함 1(P0)이 도입한 `(system, universe, address)` 아이덴티티 확장이 정확히 그 보존 메커니즘이다 — System은 `fields["system"]`에 원문 그대로 남아 있고, 역산은 System과 무관하게 (universe, address)만 계산하며, 그 결과를 `(system, universe, address)`로 스코프해 서로 다른 System의 같은 (universe, address)를 절대 혼동하지 않는다. `classify_and_resolve`에 `contiguous_512_confirmed=True`를 강제 주입해 두 System 레코드가 동일한 (universe, address)로 역산됨을 직접 확인했고(`test_vwx_multisystem_real_samples.py::TestPerSystemAbsoluteAddressAmbiguity`), 02 전체가 01과 동일한 9대 리그로 정확히 복원됨도 확인했다(같은 클래스 `test_02_and_01_derive_the_same_universe_address_pairs_per_system`). 근거 등급은 `absolute_back_calculated`(약함, 전제 문구 동반)로 정직하게 낮춰 표기한다 — GO는 "완벽히 신뢰할 수 있다"가 아니라 "거부 대신 등급을 낮춰 지원한다"는 뜻이다.
- **ASSUMPTION-70** — **경로 B(워크시트 export) 데이터 블록의 구조적 식별 가능성. `PARTIAL 유지(v0.1.6) — 변형 1종 실물 확인, 나머지 미검증`.** `vectorworks_worksheet_multisystem_full.csv`/`vectorworks_worksheet_absolute_address_only.csv` 2종이 **"단일 최상단 DB 헤더 + 인라인 집계행(SUBTOTAL/TOTAL)"** 형태의 경로 B(0번 행이 헤더라 `path_kind=A`로 판독됨)를 실물로 확인했다 — 집계행이 컬럼 수 불일치가 아니라 `Device Type` 값으로 구조적으로 배제됨을 실측했다(`excluded_rows`). **그러나 다음 두 변형은 여전히 미검증이다**: ① **헤더 반복형**(같은 파일 안에서 DB 헤더행이 포지션마다 반복되는 워크시트), ② **제목행 선행형**(`Instrument Data` 같은 제목행이 DB 헤더 앞에 별도로 존재해 `path_kind=B`로 판독되는 진짜 워크시트 그리드 — `synthetic_path_b_worksheet_grid.csv`가 이 변형을 합성물로만 흉내낸다). GO로 닫으려면 이 두 변형 중 최소 1종의 실물 샘플이 더 필요하다. 우회(추측으로 블록을 자르는 것)는 여전히 금지한다.

> **FID/CID의 의미는 ASSUMPTION이 아니다.** `console/lua/PROTOCOL.md:322-324`가 슬롯 ≠ FID로 패치된 쇼파일을 검증 조건으로 명시하며, 그것은 선행 SPEC(PRECHK)이 이미 구조적으로 배제하고 출하한 사실이다(`.moai/specs/SPEC-COPILOT-PRECHK-001/spec.md` §C). 본 SPEC은 그 판정을 재측정하지 않고 **조인 키 설계로 그 필요 자체를 우회한다**(REQ-VWX-018) — 새 라이브 프로브를 열지 않는다(라이브 세션 회계는 `plan.md` §C 소유이며 0회다).

### 신규 의존성 — **승인 확정 (v0.1.1)**

**경로 B의 `.xlsx` 바이너리 포맷 지원은 신규 의존성(`openpyxl`)을 요구한다.** 기존 `pyproject.toml`의 런타임 의존성은 `anthropic`·`fastapi`·`google-genai`·`keyring`·`lupa`·`python-osc`·`pyyaml`·`uvicorn`·`websockets` 9건이며 CSV/Excel 파싱 라이브러리가 **0건**이었다(직접 확인). `.xls/.txt/.csv`는 표준 라이브러리(`csv`, 텍스트 판독)로 충분하지만 `.xlsx`는 아니다. **Implementation Kickoff Approval에서 사용자가 채택을 승인했다** — `openpyxl`을 `pyproject.toml` 런타임 의존성에 추가하고, 경로 B의 `.xlsx`를 v1 범위에 **포함**한다. §D의 조건부 Out-of-Scope 절("`.xlsx` 바이너리 지원(신규 의존성 미승인 시)")은 이 승인으로 **무효화**된다.

### PRESERVE — 무변경 대상

`console/lua/**` · `server/safety/**` · `server/prechk/{__init__,inventory,patch,report,verdicts,footprint,macro,query}.py`(8개 파일 전량, 본 SPEC은 **소비만** 한다; `verdicts.py`는 신규 부류 순수 추가만 예외) · `server/paperwork/{data,render,output}.py`(소비만 한다) · `server/looks/**` · `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 실행/dedupe 루프 · `server/rulebook/assets/v2.4.2/**`.

> **`server/prechk/**`를 PRESERVE로 두는 근거(plan-audit 지적 반영 — 8개 파일 전량 잠금).** 본 SPEC의 대조 절반(콘솔 실측 측)은 이미 라이브 검증된 `read_inventory`/`evaluate_patch`/`build_patch_sheet`를 그대로 소비한다 — 재구현하지 않는다. `footprint.py`/`macro.py`/`query.py`/`__init__.py`는 본 SPEC이 직접 호출하지 않는 무관 기능이지만, PRESERVE 게이트가 파일 단위가 아니라 **디렉터리 단위**로 명확하도록 8개 파일 전량을 명시한다. **run-phase에서 실제로 확정된 설계(당초 계획보다 더 안전한 결과, `progress.md` §E.2 M6 기록 참조): 신규 판정 어휘를 `server/prechk/verdicts.py`의 공유 `CLOSED_VOCABULARIES`에 추가하지 않는다.** 시도 결과 `verdicts.py`/`report.py`의 기존 테스트(정확한 집합을 assert)가 깨졌기 때문이다 — 대신 `server/vwx/report.py`가 **독립된** 닫힌 어휘 레지스트리(`VWX_CLOSED_VOCABULARIES` + `vwx_label()`)를 동일한 패턴(닫힌 집합 + 라벨표 + 미등록 코드에 예외를 던지는 접근자)으로 자체 소유한다. 이로써 `verdicts.py`도 **순수 추가 예외 없이 완전 0-diff**가 된다(당초 계획의 "순수 추가만 허용" 예외보다 엄격). 게이트 검증: `git diff --stat <BASE>..HEAD -- server/prechk/__init__.py server/prechk/inventory.py server/prechk/patch.py server/prechk/report.py server/prechk/footprint.py server/prechk/macro.py server/prechk/query.py server/prechk/verdicts.py`가 **8개 파일 전부** 빈 출력이어야 한다 — 예외 없음.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — Lua `AddFixtures` 자동 패치

**제안서 원문의 2단계다.** 차이 리포트에서 사람이 승인한 뒤 라이브 검증된 `AddFixtures` 기법으로 콘솔에 자동 패치하는 것은 **본 SPEC의 산출물이 아니다.** 본 SPEC은 차이를 **읽고 보고**만 한다. 콘솔에 대한 `exec` 발화는 0건이다. 후속 SPEC(2단계)이 본 SPEC의 대조 리포트를 입력으로 받는다.

- 본 SPEC이 만드는 차이 리포트를 소비해 자동 패치를 수행하는 코드는 0건이다.
- `console/lua/**`의 `AddFixtures` 관련 로직은 PRESERVE이며 본 SPEC이 호출하지 않는다.

### Out of Scope — MVR/GDTF 가져오기

**제안서 원문의 3단계다.** MVR 파일(3D 배치 + GDTF 장비 정의) 파싱과 무대 좌표 확보는 본 SPEC 범위가 아니다. MVR/GDTF는 SPATIAL/GROUPGEN이 이미 구축한 공간 인식 계층과의 결합이 필요하며 별도 SPEC이 다룬다.

- 본 SPEC은 `.mvr` 확장자 파일을 다루지 않는다.
- GDTF 장비 정의 파싱 코드는 0건이다.

### Out of Scope — 도면 이미지 자동 반영

Vectorworks 도면의 시각적 이미지(플롯·뷰포트 렌더)를 자동으로 가져와 반영하는 것은 범위 밖이다. 좌표 정밀도가 없는 참고 자료일 뿐이며 본 SPEC의 패치 대조와 무관하다.

- 이미지·PDF·플롯 파일을 파싱하는 코드는 0건이다.

### Out of Scope — FID/CID 기반 픽스처 아이덴티티 대조

§A·§C가 근거를 적었다 — 현재 쇼파일로는 원리적으로 불가능하다. 본 SPEC은 이 축을 열지 않고 `SkippedCheck` 구조로 명시한다(REQ-VWX-019). 슬롯 ≠ FID로 패치된 쇼파일이 준비되면 후속 SPEC이 이 축을 연다.

- 본 SPEC이 `FID`/`CID` 값을 대조 조인 키로 사용하는 코드는 0건이다(REQ-VWX-018).
- 슬롯≠FID 검증용 신규 라이브 프로브를 여는 코드는 0건이다(`plan.md` §C).

### Out of Scope — 패치 자동 재배치·충돌 해소

본 SPEC은 대조하고 보고한다. 차이가 발견되어도 콘솔 패치를 옮기거나 도면을 수정하지 않는다. 자동 재배치는 물리 배선 정책을 요구하는 별도 산출물이다.

- 콘솔에 `exec` 발화를 보내 패치를 옮기거나 재배치하는 코드는 0건이다.
- 도면 파일을 되쓰는(write-back) 코드는 0건이다.

### Out of Scope — `.xlsx` 바이너리 지원(신규 의존성 미승인 시) — **v0.1.1: 무효화됨**

**이 절은 §C의 승인으로 무효화됐다.** `openpyxl`이 승인되어 경로 B의 `.xlsx` 형식은 v1 범위에 **포함**된다. 이 절은 승인 전 조건부 축소 규칙이 실제로 무엇이었는지 감사 가능하도록 기록으로만 남긴다 — 승인 전에는 `.txt(tab)`·`.csv`(텍스트 기반 워크시트 export)만 지원하고 `.xlsx` 파일을 판독 실패("미승인 의존성")로 분류하는 규칙이었다.

- `.xlsx` 파서를 바이트 단위로 자체 구현(우회)하는 코드는 여전히 0건이다 — `openpyxl` 표준 API만 사용한다.

---

## E. 참조 구현

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 주소 정규화 계약 | `server/prechk/patch.py:118 normalize_address` | (유니버스, 주소) 정수 튜플 표현 규약 — 값이 아니라 형태를 일치 |
| 콘솔 실측 인벤토리 | `server/prechk/inventory.py:344 read_inventory` | 콘솔측 대조 입력의 단일 진입점, 화이트리스트 프로퍼티 읽기 |
| 콘솔 실측 패치 시트 | `server/paperwork/data.py:67 build_patch_sheet` | 재사용 가능한 실측 표(대안 소스) |
| 구간 겹침 판정 | `server/prechk/patch.py:440 _range_overlaps` | `FootprintPolicy` 주입 시 재사용(REQ-VWX-021) |
| 닫힌 판정 어휘 + 한국어 라벨 | `server/prechk/verdicts.py:52`, `server/prechk/report.py:143 label()` | 신규 부류를 순수 추가하는 확장 패턴 |
| 아키텍처 경계 | `server/tests/test_architecture.py:48 _FORBIDDEN_MODULE_PREFIXES` | 신규 `server/vwx/`가 `server.bridge`·`pythonosc`를 직접 import하지 않는 강제 |
| 툴 등록 4지점 패턴 | `server/orchestrator/tools.py:127,1986,4317,5134`(`precheck_patch` 등록 좌표) | `TOOL_NAMES`·핸들러·`definitions`·`handlers` 등재 절차 |
