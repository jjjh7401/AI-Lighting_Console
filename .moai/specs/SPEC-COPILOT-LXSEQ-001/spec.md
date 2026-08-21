---
id: SPEC-COPILOT-LXSEQ-001
title: "LX-SEQ 연계 1단계 — RIG 팩 패치 CSV 가져오기 → 기존 패치 툴로 onPC 패치 (파서 + 매퍼 + 툴 1종)"
version: "0.2.2"
status: draft
created: 2026-08-21
updated: 2026-08-21
author: manager-spec
priority: P0
phase: "v0.2.0 target — LX-SEQ 연계 1단계(패치); 2단계 그룹 · 3단계 프리셋/FX · 4단계 시퀀스/큐는 후속 SPEC"
module: "server/lxseq/ (신규: parser · mapper), server/orchestrator/tools.py (신규 툴 1종 등재), server/tests/test_tools.py (툴 수 33→34), server/tests/fixtures/lxseq/ (실물 CSV 사본), server/vwx/** · server/prechk/** (재사용 · 무변경)"
lifecycle: spec-anchored
tags: "lxseq, rig-pack, patch, csv, import, patch_fixtures, resolve_fixture_type, occupied-slot, idempotent, grandma3"
tier: M
related_specs: [SPEC-COPILOT-VWX-001, SPEC-COPILOT-AUTOPATCH-001, SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-LXSEQ-001 — LX-SEQ 연계 1단계: RIG 팩 패치 CSV → 기존 패치 툴로 onPC 패치

> **칸반 카드 t9 · 4단계 중 1단계.** 조명감독 산출물(LX-SEQ v2.1 RIG 팩)의 **패치 CSV**를 읽어, MA 코파일럿에 **이미 있는** 콘솔 툴 33종만으로 grandMA3 onPC에 픽스처를 패치한다. 신규 코드는 **파서 + 매퍼 + 툴 등재 1종**뿐이다. 콘솔 조작·안전 가드·Lua 생성·실행·재조회는 전부 기존 `resolve_fixture_type` → `patch_fixtures` 경로를 그대로 쓴다.
>
> **감독 결정(2026-08-21, 카드 기록) — 구속력 있음.** ① 신규 코드 = 파서 + 매퍼만. 콘솔 쓰기 경로를 새로 만들지 않는다. ② 4단계 분할: 패치 → 그룹 → 프리셋/FX → 시퀀스/큐. 각 단계는 onPC 실기로 검증한다. 본 SPEC = 1단계. ③ **점유 슬롯은 절대 쓰지 않는다.** 대상 FID 또는 DMX 자리가 이미 차 있으면 건너뛰고 목록으로 보고한다(그룹 멤버십은 `query_state`로 읽을 수 없어 백업이 없고, 덮어쓰기는 복구 불가).

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-21 | manager-spec | 최초 작성 (draft, Tier M). 아티팩트 5종(spec/plan/acceptance/research/progress). REQ **15건**, AC **16건**(라이브 1건 포함), 마일스톤 **5개**(M0~M4), clarification 마커 **3건**(plan.md §A.4 — 입력 채널 · 픽스처 이름 접두 · 모드 미해결 시 처리). 기존 툴 4종의 정확한 계약은 `research.md` §2가 소유한다. |
| 0.2.0 | 2026-08-21 | manager-spec | plan-audit 1회차(FAIL 0.86) 델타 수정 + 감독 Kickoff 답 3건 반영. **마커 0건**(plan.md §A.4 ①②③ → 결정 H·I·J로 등록). ① 입력 채널 = `file_content_base64` 인자, 바이트는 UI 파일 선택기만 — 채팅 붙여넣기 금지를 **REQ-LXSEQ-016 `[Unwanted]`** + **AC-LXSEQ-017**로 신설(REQ 15→**16**, AC 16→**17**). ② 이름 접두 `group` 확정(12런; 타입 접두 대안은 **9런** — 10이 아님, D6). ③ **대안 채택**: 모드 미해결 행은 `mode_unresolved` 건너뛰기 + `mode_overrides` 재호출(REQ-LXSEQ-005/010/011 개정, 기본안 `patch_fixtures` 카드 위임 기각). D2 입력 정본 절대경로·사본 계약, D3 AC-003 ④ 겹침 104·105, D4 AC-011 선택자, D7 AC-007 ④ FID 502/`2.030`, O1 REQ-013 `When`, O2 REQ-015 `[Unwanted]`, O8 AC-015 ③ 수치화. |
| 0.2.1 | 2026-08-21 | manager-spec | **문서 전용 개정(설계 변경 0 · REQ 16 · AC 17 불변).** 감독 판정(칸반 리드 경유): UI 파일 선택기 → 툴 인자 전달 경로(`ui/` + `server/web/session.py`)는 **후속 카드 t10으로 위임** — 본 SPEC은 신규 툴 밖 0-diff 유지. **M4 라이브는 UI가 아니라 툴 직접 호출(채팅/스크립트)로 파일 경로를 지정해 수행**한다. REQ-LXSEQ-010/016의 "바이트는 UI 파일 선택기가 고른 파일에서만" 문구를 "파일(현재: 직접 호출로 지정한 경로 / t10 이후: UI 파일 선택기)에서만 — 채팅 본문 텍스트에서는 절대 아니다"로 완화해 AC-LXSEQ-016과의 모순을 제거; REQ-016에 금지 대상(붙여넣은 텍스트)과 M4 허용 경로(직접 호출 + 서버 파일 읽기)가 충돌하지 않음을 명문화. plan.md §A.2 4 · 결정 H · §A.4 ① · M3 · M4 · §F · §G, acceptance.md AC-016 · AC-017, research.md §4 · §6-6, progress.md 동조. (※ "직접 호출로 지정한 경로를 서버가 읽음" 문구는 0.2.2에서 N1로 정정.) |
| 0.2.2 | 2026-08-21 | manager-spec | **문서 전용 개정(설계 변경 0 · REQ 16 · AC 17 불변) — plan-audit 2회차(FAIL 0.88) N1·R1·R2·R3·R5 반영.** **N1(blocking, (가)안 채택 — 리드 승인)**: v0.2.1의 "툴을 직접 호출하며 파일 경로를 지정하고 서버가 파일을 읽어 `file_content_base64`를 구성"은 REQ-LXSEQ-010/AC-LXSEQ-017 ①의 닫힌 인자 집합(경로 인자 없음)과 모순이었다 → **현재 절차(t9): 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출한다 — 서버는 파일 경로를 받지 않는다(인자 집합 불변). 채팅 경유 호출은 t10 이후**로 REQ-LXSEQ-010 · REQ-LXSEQ-016 · AC-LXSEQ-016 · AC-LXSEQ-017 주 · plan.md §A.1 4 · 결정 H · §A.4 ① · M4(파일 줄에 스크립트 이름·소유·소재) · §F · §G · research.md §4 · §6-6 · progress.md §0/M0 표를 통일. **R1**: REQ-LXSEQ-008에 `name_prefix_mode="type"`이면 `Group`을 경계에서 제외(실물 CSV 9런) 1문장. **R2**: BACK+SIDE-L 병합 구간 `4.001–325` → 실물 **`4.001–450`**(acceptance AC-009 ①-b · plan §A.4 ② · research §1.1, fixture CSV 직접 재계산). **R3**: 시나리오 5 · AC-006 ③의 `Robe Spiider` 예를 실물 `Mode 1 49ch`/`Ch=49`로(25ch `Extended 25ch`는 MAC Aura XB). **R5**: SPEC 디렉터리 안 stray `.moai/state/*.json` 3건 삭제. |

---

## A. 개요

**한 줄**: `LXSEQ_RIG_01_ShowBase_r3.patch.csv`(86행 · `FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position`)를 읽어 픽스처 레코드로 정규화하고, 타입·모드·자리·FID를 **콘솔 실측으로 확정한 뒤** 기존 `patch_fixtures` 툴이 받는 인자 묶음(패치 런 계획)으로 번역해 순서대로 실행한다. 점유된 자리·FID와 모드를 확정하지 못한 타입의 행은 건너뛰고 목록으로 돌려준다(덮어쓰기 0 · 질문 카드 남발 0). 픽스처 이름은 `"{Group} {FID}"`(감독 Kickoff 답 ②). 같은 파일을 다시 돌리면 이미 패치된 행이 전부 점유로 분류되어 **0건 쓰기**로 끝난다.

### 사전 확정 사실 (조사 확정 — `research.md`가 근거를 소유)

1. **콘솔 쓰기 경로는 이미 둘 있고, 본 SPEC은 그중 `patch_fixtures`를 쓴다.** `patch_fixtures`(`server/orchestrator/tools.py:3820`)는 2026-08-18 라이브 onPC 2.4.2.2에서 서버 실행으로 픽스처가 **실제로 생기는 것을 재조회로 확인**한 경로다(주소 재검사 → FID 배정 → `luagen` AddFixtures Lua → per-type 플러그인 배포 → `run_commands` 경유 실행 → 재조회 판정). 또 다른 경로 `apply_vectorworks_patch`(AUTOPATCH-001)는 Lua를 **사람에게 건네고 서버는 검증만** 한다. 감독 결정 ①이 지목한 4종(`precheck_patch` · `resolve_fixture_type` · `resolve_patch_address` · `patch_fixtures`) 중 실제 쓰기는 `patch_fixtures` 하나다 — 본 SPEC은 그 하나만 쓰기 경로로 삼는다.
2. **`patch_fixtures`는 호출자가 준 `fids`를 검증하지 않는다.** `fids`를 생략하면 `read_existing_fids`로 전수 판독 후 빈 연속 블록을 고르지만, **명시하면 그대로 Lua에 싣는다**(`tools.py:4039-4041`). LX-SEQ는 FID 체계(101~ KEY, 201~ BACK …)를 보존해야 하므로 반드시 `fids`를 명시해야 하고, 따라서 **FID 점유 판정은 매퍼가 먼저 해야 한다**(감독 결정 ③의 실질). `patch_fixtures`의 `address_not_free` 거부는 **런 단위**(시작 주소+대수 전체)라 한 행만 점유돼도 런 전체가 거부된다 — 그래서 매퍼는 **행 단위**로 점유를 먼저 걸러내고 남은 행만 런으로 묶는다.
3. **콘솔 픽스처 번호(슬롯) ≠ FID.** 룰북과 선행 SPEC(`copilot-fid-vs-slot-decision`)이 FID를 주소로 다루는 것을 금지한다. 본 SPEC에서 FID는 오직 `patch_fixtures`의 `fids` 인자로만 흐르고, 자리는 오직 `Universe`·`Address` 열에서만 파생된다.
4. **타입·모드·폭은 콘솔이 안다, 파일이 아니다.** `resolve_fixture_type`은 토큰 단위 후보 대조 후 `present`/`ambiguous`/`absent`를 내고 애매하면 **스스로 사용자에게 묻는다**(질문 카드). `patch_fixtures`는 타입의 모드 목록과 채널 수를 **콘솔에서 실측**하고, 호출자의 `channels_per_fixture`는 실측이 이기는 폴백일 뿐이다. CSV의 `Mode`("Mode 1 39ch", "Extended 25ch", "4ch" …)는 콘솔 모드 이름이 아니라 LX-SEQ 표기이므로, 매퍼는 `Ch` 값으로 실측 모드 목록과 대조해 **유일하게** 맞을 때만 `console_mode`를 넘기고, 아니면 넘기지 않아 기존 툴이 사용자에게 고르게 한다.
5. **패치는 콘솔 명령 목적지가 픽스처 계층일 때만 먹는다.** 서버는 목적지를 옮길 수 없고(`ChangeDestination` 전부 Failed), `patch_fixtures`가 0건이면 편집기 열기를 청하고 스스로 재실행한다. 본 SPEC은 이 처리에 **아무것도 덧붙이지 않는다**.
6. **입력 데이터는 실물이 있다 — 단, 저장소 밖이다.** 정본은 주 체크아웃의 **git 미추적 로컬 디렉터리** `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv`(워크트리에는 존재하지 않는다) — UTF-8 BOM, 쉼표 구분, 86행, `AddrRange`에 en-dash(U+2013), `Position`에 한국어. 생성기 `make_rig.py`와 검증기 `validate_rig.py`(R1 FID 고유 · R2 무충돌/512 이내 · R3 풋프린트 산술)가 같은 디렉터리에 있다. 저장소 안 계약은 plan-phase v0.2.0(2026-08-21)에서 복사해 이 카드 커밋에 넣은 **사본** `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`(sha256 `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3`, 정본과 동일 실측)이며, 오프라인 테스트·AC는 사본만 읽는다(절대경로는 M4 사용자 라이브 절차에서만 쓴다). VWX-001과 달리 **컬럼 계약을 실물로 동결할 수 있다**.

### 단계 경계 — 이 SPEC이 하는 것 / 하지 않는 것

| 하는 것 | 하지 않는 것 |
|---|---|
| 패치 CSV 판독 · 검증(R1~R3 거울) | GROUP/PRESET/FX/CONSOLE 시트 판독 |
| 타입·모드·자리·FID를 콘솔 실측으로 확정 | xlsx 판독(패치 CSV가 정본 병행 출력) |
| `patch_fixtures` 인자 묶음(런 계획) 생성 · 순차 실행 | 그룹 생성 · 프리셋 · 시퀀스 · 큐 |
| 점유 행 건너뛰기 + 목록 보고, 재실행 멱등 | 점유 슬롯 덮어쓰기 · 자동 재배치 · 신규 Lua/쓰기 경로 |

---

## B. 요구사항 (GEARS)

### B.1 파싱 (`server/lxseq/parser.py`)

- **REQ-LXSEQ-001** `[Ubiquitous]` The 파서 **shall** LX-SEQ v2.1 RIG 팩 **패치 CSV**(UTF-8, BOM 유무 무관, 쉼표 구분)를 판독해 행마다 패치 레코드 `LxseqPatchRecord(fid:int, group:str, fixture_type:str, mode_label:str, channels:int, universe:int, address:int, addr_range_raw:str, position:str, extra:dict)`를 낸다. 컬럼은 **이름으로** 맞춘다(`FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position` 9개 정규 이름 · 대소문자·공백 무시) — 위치 기반 해석은 금지한다. 정규 9개 밖의 컬럼은 버리지 않고 `extra`에 원문 보존한다. 정규 9개 중 하나라도 헤더에 없으면 **파일 단위 판독 실패**(`missing_columns` + 빠진 이름)로 보고하고 행을 추측해 채우지 않는다.
- **REQ-LXSEQ-002** `[Event-driven]` **When** 행이 검증에 걸리면, the 파서 **shall** 그 행을 예외가 아니라 **구조화된 행 거부**(`row`, `fid_raw`, `kind`, `detail`)로 분류하고 계획에 넣지 않는다. 거부 부류(닫힌 집합): `non_integer_field`(FID/Ch/Universe/Address가 정수 아님) · `universe_overflow`(`address + channels - 1 > 512`) · `address_out_of_range`(`address < 1` 또는 `universe < 1`) · `addr_range_mismatch`(`AddrRange` ≠ `f"{universe}.{address:03d}–{address+channels-1:03d}"`; en-dash·hyphen·em-dash 모두 허용하되 숫자가 다르면 거부) · `duplicate_fid`(파일 안 FID 중복 — 관여 행 **전부** 거부, R1 거울) · `address_overlap_in_file`(같은 유니버스 안 구간 겹침 — 관여 행 전부 거부, R2 거울) · `zero_channels`(`Ch` = 0, 수동 운용 장비 등 DMX 비점유 행은 **제외행**으로 따로 센다, 거부가 아니다). 실물 CSV 86행은 전부 통과해야 한다(비공허성은 `acceptance.md`가 뮤테이션으로 증명).
- **REQ-LXSEQ-003** `[Unwanted]` The 파서와 매퍼 **shall not** `FID` 값을 콘솔 슬롯·DMX 주소·픽스처 번호 해석에 쓴다. FID는 오직 `patch_fixtures`의 `fids` 인자(및 보고용 FID 매핑표)로만 흐르고, DMX 자리는 오직 `Universe`·`Address` 열에서만 파생된다 — `Group`·`Position`·`FID`를 바꿔도 자리는 변하지 않는다.

### B.2 매핑 (`server/lxseq/mapper.py`)

- **REQ-LXSEQ-004** `[Ubiquitous]` The 매퍼 **shall** 파일에 등장하는 **서로 다른 `FixtureType`마다 한 번씩** 기존 `resolve_fixture_type` 계약(`status ∈ {present, ambiguous, absent, library_unreadable}`, `resolved`, `candidates`)으로 콘솔 라이브러리 이름을 확정한 뒤에만 그 타입의 행을 런에 넣는다. `present`가 아니면 그 타입의 모든 행을 `type_unresolved`(사유에 status와 candidates 동봉)로 **건너뛰고**, 타입 이름·GDTF 파일명·Import 문법을 추측하지 않는다. `library_unreadable`이면 전 행을 건너뛰고 "없다고 단정하지 않는다"를 사유에 싣는다.
- **REQ-LXSEQ-005** `[Ubiquitous]` The 매퍼 **shall** 콘솔 모드 이름을 CSV `Mode` 문자열에서 **추측하지 않는다**. 확정된 콘솔 타입에 대해 기존 `read_type_mode_widths`로 모드 목록과 채널 수를 실측해, 채널 수 == `Ch`인 모드가 **정확히 하나**면 그 이름을 `console_mode`로 넘긴다(같은 폭이 둘 이상이면 `Mode` 문자열의 숫자·단어 토큰이 모드 이름에 포함되는 것이 하나일 때만 채택). 호출 인자 `mode_overrides`에 그 CSV `FixtureType`의 항목이 있으면 그 이름이 실측 모드 목록에(대소문자 무시) **있을 때만** 위 규칙보다 우선해 채택하고, 없으면 채택하지 않는다(추측 금지). 그 밖의 경우(유일 일치 없음 · 토큰으로도 못 가름 · override가 실측 목록에 없음) 그 타입의 **모든 행을 `mode_unresolved`로 건너뛰고** 런에 넣지 않는다 — `patch_fixtures`의 모드 선택 카드에 맡기지 **않는다**(카드가 런마다 뜨는 대신 보고 1회, 감독 Kickoff 답 ③ — 대안 채택). 건너뛴 목록 항목의 `detail`에는 `measured_modes`와 "`mode_overrides: {"<FixtureType>": "<콘솔 모드 이름>"}`으로 재호출" 안내를 싣고, 계획에는 `mode_resolution: {resolution ∈ {resolved, unresolved, tree_unread}, measured_modes, resolved_by? ∈ {width_unique, label_token, override}}`를 싣는다. 모드 트리를 못 읽었으면(`tree_unread`) `channels_per_fixture=Ch`를 폴백으로 넘기되 계획에 `footprint_source: caller_unverified`를 표시하고, override가 있으면 그 이름을 검증 없이 `console_mode`로 넘긴다(`patch_fixtures`가 실측으로 `mode_not_found`를 낸다).
- **REQ-LXSEQ-006** `[Ubiquitous]` The 매퍼 **shall** 런을 만들기 **전에** 행마다 콘솔 점유를 판정한다 — ① **DMX 자리**: `read_inventory` 실측 → `occupants_from_patch_values` → 행의 구간 `[address, address+channels-1]` 안에서 **시작하는** 기존 장비가 있으면 점유(`addressfit.evaluate`의 규약과 동일, `blind_spot` 문구를 보고에 그대로 동봉) · ② **FID**: `read_existing_fids` 실측 집합에 행의 FID가 있으면 점유. 점유 행은 `address_occupied` / `fid_occupied`(둘 다면 둘 다)로 **건너뛰고** 점유자(주소·이름·타입 또는 FID)를 목록에 싣는다. 점유자의 콘솔 타입이 행의 확정 타입과 같고 같은 시작 주소면 `already_patched` 부류로 **따로** 표시한다("이미 했음"과 "남이 차지함"은 사용자 조치가 다르다). 점유 행을 덮어쓰는 경로는 **존재하지 않는다**.
- **REQ-LXSEQ-007** `[Event-driven]` **When** 콘솔 읽기가 전수가 아니면(인벤토리 caveat가 `CONSOLE_READ_INCOMPLETE`이거나, `read_existing_fids`가 미시도·루트 미판독·미해결 건수>0이면), the 매퍼 **shall** 모든 행을 `console_read_incomplete`로 건너뛰고 런을 **0개**로 낸다 — 빈 자리라고 말할 수 없으면 쓰지 않는다. 미리보기(preview)는 이 상태에서도 파싱·타입 해석 결과를 그대로 보여 주되 "점유 판정 미수행"을 명시한다.
- **REQ-LXSEQ-008** `[Ubiquitous]` The 매퍼 **shall** 남은 행을 **패치 런**(`PatchRun`)으로 묶어 순서 있는 계획을 낸다. 한 런 = `patch_fixtures` 호출 1회의 인자 그대로: `{console_type, console_mode?, address:"U.A", count, channels_per_fixture, fids:[...], name_prefix}`. 런 경계는 (확정 콘솔 타입, 모드 해석 결과, 유니버스, `Group`)이 같고 `address == 직전.address + channels`인 **최대 연속 구간**이다(건너뛴 행이 끼면 런이 갈라진다). 계획에는 런 목록과 별도로 **FID 매핑표**(`fid → {universe.address, console_type, run_index}`)와 건너뛴 행 목록을 싣는다. 실물 CSV를 빈 콘솔에 대면 런 12개 · 픽스처 86대 · FID 합집합이 CSV와 동일해야 한다. 비기본 `name_prefix_mode="type"`(REQ-LXSEQ-010)이면 `Group`을 런 경계에서 **제외**하고 나머지 조건은 같다 — 실물 CSV는 **9런**(KEY+FOH · BACK+SIDE-L · WASH-U+WASH-D가 각각 한 런으로 병합).
- **REQ-LXSEQ-009** `[Unwanted]` The `server/lxseq/**` 모듈 **shall not** 콘솔 쓰기 수단을 직접 다룬다 — `server.bridge`·`pythonosc`·`execution_port`·`deploy_pipeline`·`run_commands`·`deploy_plugin`·`luagen`을 import하거나 이름으로 부르지 않고, `AddFixtures`·`ChangeDestination`·`Plugin '` 문자열을 만들지 않는다. 콘솔 접촉은 **읽기**(`read_inventory`·`read_existing_fids`·`read_type_mode_widths`·`read_library_snapshot`)뿐이며 쓰기는 툴 계층이 `patch_fixtures` 핸들러로 위임한다.

### B.3 툴 (`server/orchestrator/tools.py` — 신규 1종 `import_lxseq_patch`)

- **REQ-LXSEQ-010** `[Ubiquitous]` The 시스템 **shall** 신규 툴 **1종** `import_lxseq_patch`를 `TOOL_NAMES`·핸들러 클로저·`ToolDefinition`·`handlers` 맵 4지점에 등재한다. 인자: `file_content_base64`(필수, 패치 CSV 바이트 — **파일**에서만 온다(현재 절차 t9: 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`가 정본 CSV 파일을 읽어 base64로 인코딩해 이 핸들러를 직접 호출한다 — **서버는 파일 경로를 받지 않는다**(경로 인자 없음, 인자 집합 불변) / t10 이후: UI 파일 선택기), 채팅 본문 텍스트에서는 절대 아니다 — REQ-LXSEQ-016) · `action ∈ {"preview","apply"}`(기본 `preview`) · `name_prefix_mode ∈ {"group","type"}`(기본 **`"group"`** — 감독 Kickoff 답 ②, plan.md 결정 I; 이름은 `"{Group} {FID}"`) · `only_fids`(선택, 적용 대상 FID 부분집합) · `mode_overrides`(선택, `{"<CSV FixtureType>": "<콘솔 모드 이름>"}` — REQ-LXSEQ-005의 `mode_unresolved` 재호출 수단). `preview`는 파싱 → 타입 해석 → 모드 해석 → 점유 판정 → 런 계획까지만 수행하고 **콘솔에 아무것도 쓰지 않는다**(`deploy_pipeline`·`execution_port` 호출 0건). `apply`는 계획의 런을 **순서대로** 기존 `patch_fixtures` 핸들러에 **내부 `ToolCall`로 위임**(`vectorworks_autopatch`가 형제 툴을 부르는 방식과 동일)해 실행하고 런마다 `status`(`created`/`created_partially`/`created_nothing`/`unverified`/그 밖의 거부 status)를 모은다. 한 런이 `created`가 아니면 **그 자리에서 멈추고** 나머지 런은 `not_attempted`로 보고한다 — 자동 재시도·건너뛰고 계속은 하지 않는다(부분 생성 뒤 재시도는 중복을 만든다).
- **REQ-LXSEQ-011** `[Ubiquitous]` The 툴 페이로드 **shall** 다음 최상위 키를 닫힌 구조로 싣는다: `source{file_name?, sha256, byte_length, rows_total, parsed, rejected[], excluded[]}` · `types{resolved{csv_type→console_type}, unresolved[]}` · `console_read{complete_enough_to_judge_absence, caveat, fid_read}` · `plan{runs[], fid_map{}, skipped[], write_count_planned}` · `apply{entered:bool, runs[{index, status, created, requested, detail}], stopped_at?}` · `summary_ko`. 건너뛴 항목의 `kind`는 닫힌 어휘 `{type_unresolved, mode_unresolved, address_occupied, fid_occupied, already_patched, console_read_incomplete, universe_overflow, rejected_row}`에서만 나온다. `summary_ko`는 "쓰기 0건"을 `apply.entered == false`이거나 모든 런이 `not_attempted`일 때만 말하고, `created` 합이 계획 합보다 작으면 **절대 성공이라 말하지 않는다**.
- **REQ-LXSEQ-012** `[While]` **While** 파일의 행이 이미 콘솔에 패치되어 있는 상태에서, the 툴 **shall** 같은 파일로 `preview`/`apply`를 다시 불러도 그 행을 `already_patched`(또는 `address_occupied`/`fid_occupied`)로 건너뛰어 런에서 제외하고, 전부 패치된 파일은 **런 0개 · 쓰기 0건**으로 정상 종료한다(오류가 아니라 "할 일 없음"). 재실행이 중복 픽스처를 만드는 경로는 존재하지 않는다.
- **REQ-LXSEQ-013** `[Event-driven]` **When** `patch_fixtures` 핸들러가 런 실행 중 사용자 확인(편집기 열기 · 매퍼가 넘기지 못한 모드의 선택 등)을 기존 질문 카드로 요청하면, the 툴 **shall** 그 대기를 가로채거나 대신 답하지 않고 `awaited_human`을 그대로 올려 보낸다. 사용자가 취소하거나 답하지 않으면 해당 런은 `not_run`으로 기록하고 멈춘다.
- **REQ-LXSEQ-014** `[Ubiquitous]` 사용자 대면 문자열(`summary_ko`·`guidance`·사유 문구) **shall** 한국어이며, `guidance`는 모델에게 "`apply.runs[*].status == created`인 수량만 성공으로 보고하라 · 점유로 건너뛴 행은 덮어쓰지 말고 목록을 사용자에게 보여 줘라 · 타입이 없으면 콘솔에서 추가해 달라고 청하라"를 명시한다.
- **REQ-LXSEQ-015** `[Unwanted]` The 변경 **shall not** 기존 툴 핸들러 본문·`server/vwx/**`·`server/prechk/**`·`console/lua/**`·`server/safety/**`·`server/rulebook/assets/**`를 수정한다(PRESERVE — §C). 예외는 두 가지뿐이다: `server/orchestrator/tools.py`의 신규 툴 4지점 **순수 추가**와 `server/tests/test_tools.py`의 닫힌 집합 단언(`len(TOOL_NAMES) == 33`) 34 갱신.
- **REQ-LXSEQ-016** `[Unwanted]` The 툴 **shall not** 채팅에 붙여넣은 텍스트로부터 `file_content_base64`를 구성하는 경로를 허용한다 — 바이트는 **파일(현재 절차 t9: 로컬 하네스 스크립트가 읽음 / t10 이후: UI 파일 선택기)에서만** 온다 — 채팅 본문 텍스트에서는 절대 아니다(감독 Kickoff 답 ①: 붙여넣기는 개행·공백이 조용히 깨져 잘못 패치된다). 감독이 금지한 것은 "사람이 CSV 본문을 채팅에 붙여넣어 그 텍스트로 바이트를 만드는 것"이며, M4에서 허용되는 것은 "로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출하는 것"이다 — **서버는 파일 경로를 받지 않는다**(REQ-LXSEQ-010의 인자 집합 불변); 채팅 경유 호출은 t10 이후다. 금지(채팅 본문 텍스트로 바이트 생성)와 허용(스크립트가 파일을 읽음)은 충돌하지 않는다. UI 파일 선택기 → 툴 인자 전달 경로는 후속 카드 **t10**으로 위임됐다(plan.md §A.4 ①). 기계적 보루 세 가지: (a) 툴 `description`과 `file_content_base64` 인자 설명이 "채팅 본문을 base64로 만들어 넣지 마라 · 파일에서 읽은 바이트만(목표 상태 t10: UI 파일 선택기)"을 명시한다 — 보루의 본질은 **붙여넣은 텍스트 거부**이고 "파일 선택기" 구절은 목표 상태를 가리킨다 (b) `guidance`가 같은 문구를 모델에게 반복한다 (c) 페이로드 `source.sha256`·`source.byte_length`에 받은 바이트의 해시·길이를 실어 사용자가 원본 파일과 대조할 수 있게 한다. 세션 업로드 포트(`upload_vectorworks_export`) 재사용과 신규 업로드 엔드포인트 신설은 둘 다 하지 않는다(기각 — plan.md 결정 H).

---

## C. 환경 및 전제

### 측정된 기준선

착수 브랜치 `jjjh7401/LX-SEQ`, HEAD **`453846a`**. 기준선 실측값은 `progress.md` §E.1 `baseline_measured`가 소유한다(본 SPEC 작성 중 `uv run pytest server/tests -q` 직접 실행 — 이월 인용 아님). 각 마일스톤은 착수 직전 다시 잰다.

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC을 이어받는다(AUTOPATCH-001이 `ASSUMPTION-71`까지 썼다).

- **ASSUMPTION-72** — **실물 LX-SEQ 기종 8종이 onPC 라이브러리에 있거나 `resolve_fixture_type`이 후보를 낸다.** CSV의 타입 표기(`ETC S4 LED S3 Lustr X8` · `Martin MAC Aura XB` · `Martin RUSH PAR 2 RGBW Z` · `Robe MegaPointe` · `Robe Spiider` · `Elation CUEPIX Blinder WW2` · `Martin Atomic 3000 LED` · `Look Unique 2.1`)는 제조사 표기이고 콘솔 제품명과 다를 수 있다(실측 선례: «robe esprite» ↔ «Robin Esprite»). NEGATIVE면 해당 타입은 `type_unresolved`로 건너뛰고 사용자가 콘솔에서 타입을 추가한 뒤 재실행한다 — 계약 위반이 아니라 REQ-LXSEQ-004의 정의된 결과. M4가 판정한다.
- **ASSUMPTION-73** — **각 타입에서 `Ch`와 같은 채널 수를 가진 콘솔 모드가 유일하다.** 아니면 REQ-LXSEQ-005의 사용자 선택 경로로 떨어진다(기능 축소 아님). M4가 판정한다.
- **ASSUMPTION-74** — **`read_existing_fids`가 onPC 쇼파일에서 전수로 읽힌다**(AUTOPATCH-001 M0 1차가 FID 프로퍼티 판독 GO를 실측했고, `patch_fixtures`의 자동 FID 경로가 같은 판독기를 쓴다). NEGATIVE면 REQ-LXSEQ-007에 따라 `apply`는 전 행 거부이고, 사용자에게 쇼파일 상태를 알린다. M4가 판정한다.

### PRESERVE — 무변경 대상

`console/lua/**` · `server/safety/**` · `server/prechk/**`(8개 파일 전량, 소비만) · `server/vwx/**`(전량, `addressfit`·`stagedpatch`·`patchplan.read_existing_fids`·`librarywatch`·`typemap`은 **소비만**) · `server/paperwork/**` · `server/rulebook/assets/**` · `server/orchestrator/tools.py`의 **기존 핸들러 본문 전부**(특히 `patch_fixtures`·`resolve_fixture_type`·`resolve_patch_address`·`precheck_patch`·`run_commands`)와 `_PROGRAMMER_STATE_COMMANDS`·실행/dedupe 루프. 허용 변경은 `tools.py`의 **신규 툴 4지점 순수 추가**와 `server/tests/test_tools.py`의 툴 수 상수 1건뿐이다. 게이트: `git diff --stat <BASE>..HEAD -- console/lua server/safety server/prechk server/vwx server/paperwork server/rulebook/assets`가 빈 출력.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — 그룹 · 프리셋/FX · 시퀀스/큐 (2~4단계)

감독 결정 ②의 후속 단계다. 각각 별도 SPEC(`plan.md` §E가 이름을 예약한다)이 맡으며 본 SPEC은 그 입력이 되는 **FID 매핑표**만 남긴다.

- RIG 팩의 `GROUP`·`PRESET-*`·`FX`·`CONSOLE` 시트와 `04_grandMA3/*.ma3.txt` 명령 스크립트를 읽거나 재생하는 코드는 0건이다.
- `Store Group`·`Store Preset`·시퀀스/큐 명령을 보내는 코드는 0건이다.

### Out of Scope — xlsx 판독 · 패치 외 필드

RIG 팩 `.xlsx`는 같은 데이터의 다중 시트 출력이고 패치 CSV가 기계용 정본 병행 출력이다(`make_rig.py`가 둘을 같은 `patch_rows`에서 만든다).

- `openpyxl` 경로로 RIG 팩 xlsx를 읽는 코드는 0건이다(VWX-001의 xlsx 경로를 재사용하지도 않는다).
- `FIXTURE` 시트의 회로/전원·용도, `RIG-HEAD`, `NOTE`는 다루지 않는다. `Position`은 보고용으로만 보존한다.

### Out of Scope — 점유 슬롯 쓰기 · 자동 재배치

감독 결정 ③이다.

- 점유된 DMX 자리·FID를 덮어쓰거나, 빈 자리를 찾아 **다른 주소로 옮겨** 패치하는 코드는 0건이다(`first_free_address`를 부르지 않는다). 충돌은 목록으로 돌려주고 사용자가 CSV 또는 콘솔을 고친 뒤 재실행한다.

### Out of Scope — 신규 콘솔 쓰기 경로

감독 결정 ①이다.

- 신규 Lua 생성기·신규 `deploy_plugin`/`run_commands` 호출·신규 OSC 경로·`ChangeDestination` 발화는 0건이다. 쓰기는 `patch_fixtures` 핸들러 위임뿐이다.
- `apply_vectorworks_patch`/`vectorworks_autopatch`(사람 실행 반자동 경로)를 LX-SEQ 입력으로 재사용하지 않는다 — 두 쓰기 경로를 섞지 않는다.

### Out of Scope — 콘솔 실측 재구현

- `read_inventory`·`read_existing_fids`·`read_type_mode_widths`·`occupants_from_patch_values`·`evaluate_address_fit`을 재구현하지 않는다(소비만). 점유 판정의 `blind_spot`(앞에서 시작해 뻗어 들어오는 장비는 못 본다)은 그대로 물려받고 보고에 명시한다.

---

## E. 데이터 모델 (What — 구현 함수명 아님)

| 개체 | 필드 | 출처 |
|---|---|---|
| `LxseqPatchRecord` | `fid`, `group`, `fixture_type`, `mode_label`, `channels`, `universe`, `address`, `addr_range_raw`, `position`, `extra{}` | CSV 1행 (REQ-LXSEQ-001) |
| `RowRejection` | `row`, `fid_raw`, `kind`(닫힌 집합), `detail` | REQ-LXSEQ-002 |
| `TypeResolution` | `csv_type`, `status`, `console_type?`, `candidates[]` | `resolve_fixture_type` 계약 (REQ-LXSEQ-004) |
| `ModeResolution` | `console_type`, `channels`, `console_mode?`, `resolution ∈ {resolved, unresolved, tree_unread}`, `resolved_by? ∈ {width_unique, label_token, override}`, `measured_modes[{name, channels}]` | `read_type_mode_widths` + `mode_overrides` (REQ-LXSEQ-005) |
| `SkippedRow` | `fid`, `address:"U.A"`, `kind`(닫힌 어휘), `occupant?{address,name,fixture_type}` 또는 `occupied_fid?`, `detail` | REQ-LXSEQ-006/007 |
| `PatchRun` | `index`, `group`, `console_type`, `console_mode?`, `address:"U.A"`, `count`, `channels_per_fixture`, `fids[]`, `name_prefix`, `footprint_source` | = `patch_fixtures` 인자 (REQ-LXSEQ-008) |
| `ImportPlan` | `runs[]`, `fid_map{fid→{address, console_type, run_index}}`, `skipped[]`, `write_count_planned` | REQ-LXSEQ-008 |
| 툴 페이로드 | `source`(`sha256`·`byte_length` 포함)·`types`·`console_read`·`plan`·`apply`·`summary_ko`·`guidance` | REQ-LXSEQ-011 · REQ-LXSEQ-016 |

---

## F. 참조 구현

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 실제 쓰기 경로 | `server/orchestrator/tools.py:3820 patch_fixtures` | 인자 계약 · 모드 실측 · 주소 재검사 · 재조회 판정. 본 SPEC의 유일한 쓰기 위임 대상 |
| 타입 확정 | `server/orchestrator/tools.py:3408 resolve_fixture_type` · `server/vwx/librarywatch.py candidate_names` | `present/ambiguous/absent` 계약, 질문 카드 |
| 자리 판정 규약 | `server/vwx/addressfit.py:137 evaluate` · `:86 occupants_from_patch_values` | 구간 안 시작 장비만 확정 충돌, `blind_spot` |
| FID 실측 | `server/vwx/patchplan.py:1395 read_existing_fids` | 전수 아니면 배정하지 않는다 |
| 모드 실측 | `server/prechk/mode_read.py:76 read_type_mode_widths` | 모드 이름·채널 수는 콘솔이 안다 |
| 콘솔 인벤토리 | `server/prechk/inventory.py:344 read_inventory` | 단일 진입점 · 절단 caveat |
| 형제 툴 내부 위임 패턴 | `server/orchestrator/tools.py:2923 vectorworks_autopatch` | 내부 `ToolCall`로 형제 핸들러를 부르고 결과를 그대로 올린다 |
| 툴 등록 4지점 | `server/orchestrator/tools.py:226 TOOL_NAMES` · `:3820` 핸들러 · `:7525 ToolDefinition` · `:8817 handlers` | 등재 절차 + `server/tests/test_tools.py:172` 닫힌 집합 단언 |
| 아키텍처 경계 | `server/tests/test_architecture.py:48 _FORBIDDEN_MODULE_PREFIXES` | 신규 `server/lxseq/`가 `server.bridge`·`pythonosc`를 import하지 않음 |
| 입력 정본 · 검증기 | 정본(미추적 로컬, 주 체크아웃만) `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` · 같은 디렉터리의 `90_빌드파이프라인/validate_rig.py` R1~R3 · 저장소 사본 `{COPY}`(plan-phase v0.2.0 복사·커밋, 오프라인 테스트는 사본만) | 파서 검증 규칙의 거울 |
