# SPEC-COPILOT-LXSEQ-001 — 조사 기록 (research)

문서 상태: implemented (v0.2.1, 2026-08-21 — M4에서 라이브 관측이 실제로 수행됨(감독 onPC 2.4.2, 86대 패치) — 그 기록은 progress.md §E.2가 소유한다 — v0.2.0 plan-audit 델타: O3 좌표 정정 · §1.1 정본 경로 · §4 입력 채널 결정 H · §6 갭 갱신; v0.2.1 문서 전용: §6-6 UI 전달 경로 t10 위임) · Tier M · 본 문서는 **저장소 정적 조사 + 입력 데이터 실물 조사**의 기록이다. 라이브 콘솔 관측은 0건(M4가 사용자 수행 라이브 1회를 소유). 근거 등급: `[코드]` · `[데이터]` · `[문서]` · `[메모리]`(저장소 메모리 인덱스, 코드로 재확인한 것만) · `[미확정]`.

> **참조 규약.** 정본(spec.md · acceptance.md)은 안정 토큰만. 코드·입력 데이터는 `파일:줄`. 줄번호는 착수 SHA `453846a` 기준이며 **드리프트한다** — M0가 재확인한다.

---

## 0. 무엇을 읽었나

| 층 | 대상 | 산출 |
|---|---|---|
| 입력 데이터 | `src/Lighting_Designer/00_README.md` · `01_스펙/LX-SEQ-SPEC-v2.1.md` §9·§13 · `02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` 전문 · `90_빌드파이프라인/rig_data.py`·`validate_rig.py`·`make_rig.py` · `04_grandMA3/*.ma3.txt` 머리 | §1 |
| 기존 툴 4종 + 보조 | `server/orchestrator/tools.py` `TOOL_NAMES`(226~259) · `precheck_patch`(2649) · `resolve_fixture_type`(3408) · `resolve_patch_address`(3630) · `patch_fixtures`(3820~4340) · `vectorworks_autopatch`(2923) · `apply_vectorworks_patch`(3003) · ToolDefinition(7437~7620) · `build_toolset`(1588) | §2 |
| 재사용 헬퍼 | `server/vwx/stagedpatch.py`(plan/judge/free_fids) · `server/vwx/addressfit.py`(Occupant/Placement/Fit/evaluate/occupants_from_patch_values/first_free) · `server/vwx/patchplan.py`(`read_existing_fids` 1395) · `server/prechk/inventory.py`(`FixtureRecord` 178 · `read_inventory` 344) · `server/prechk/mode_read.py`(`read_type_mode_widths` 76) · `server/vwx/librarywatch.py` | §3 |
| 경계·테스트 | `server/tests/test_architecture.py:48` · `server/tests/test_tools.py:170-172` · `server/tests/test_vwx_stagedpatch.py` 머리 · `server/web/session.py:9655-9658, 9825-9831` · `server/rulebook/assets/v2.4.2/30_plugin_patterns.md:8-53` · `pyproject.toml` | §4 |
| 선행 SPEC | `.moai/specs/SPEC-COPILOT-VWX-001/{spec,plan,acceptance,research,progress}.md` · `SPEC-COPILOT-AUTOPATCH-001/spec.md` 머리 | 형식·계승 |

---

## 1. 입력 데이터 — 실물이 있고 계약을 동결할 수 있다 `[데이터]`

### 1.1 패치 CSV

- 파일: 정본 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv` — 주 체크아웃의 **git 미추적 로컬 디렉터리**(`git status` → `?? src/Lighting_Designer/`)라 워크트리에는 없다(plan-audit D2). 저장소 안 계약은 plan-phase v0.2.0에서 복사·커밋한 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`(sha256 `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3`). **UTF-8 BOM**(`EF BB BF`) · 쉼표 · LF · 헤더 1행 + **86행**(`tail -n +2 | wc -l` → 86). `file` 판정 "CSV text".
- 헤더(정확): `FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position`. 생성기 `make_rig.py:146`이 이 9개 이름을 그대로 쓴다(`encoding="utf-8-sig"`).
- `AddrRange` 형식: `f"{U}.{A:03d}–{A+Ch-1:03d}"`, 구분자 **en-dash U+2013**(예 `1.001–012`). `Position`은 한국어(`FOH 브리지`, `하수 붐 (3단×2)`).
- 값 분포: 유니버스 1~5; 타입 8종(`ETC S4 LED S3 Lustr X8`·`Elation CUEPIX Blinder WW2`·`Martin Atomic 3000 LED`·`Look Unique 2.1`·`Robe MegaPointe`·`Robe Spiider`·`Martin MAC Aura XB`·`Martin RUSH PAR 2 RGBW Z`); 그룹 12종(KEY 6 · FOH 8 · BLIND 6 · STROBE 4 · HAZE 2 · MOVER-U 8 · MOVER-D 8 · BACK 12 · SIDE-L 6 · SIDE-R 6 · WASH-U 10 · WASH-D 10 = 86); `Mode` 표기는 `Direct 12ch`·`4ch`·`Extended 14ch`·`2ch`·`Mode 1 39ch`·`Mode 1 49ch`·`Extended 25ch`·`9ch` — **콘솔 모드 이름이 아니라 LX-SEQ 라벨**이다.
- 연속성: 각 그룹 안에서 `Address`가 `Ch`씩 증가하는 연속 블록(유니버스 계획 `rig_data.py UNIVERSE_PLAN`: U1=KEY·FOH·BLIND·STROBE·HAZE, U2=MOVER-U, U3=MOVER-D, U4=BACK·SIDE-L, U5=SIDE-R·WASH-U·WASH-D). KEY(1.001~072)와 FOH(1.073~168)는 같은 타입·같은 모드·연속 주소다 — 런 경계를 Group으로 가르기로 확정(plan.md 결정 I, 감독 답 ② 2026-08-21): Group 경계 **12런**, 타입 접두 대안은 **9런**(KEY+FOH · BACK+SIDE-L 4.001–450 · WASH-U+WASH-D 5.151–330 병합 — 86행 직접 계산).
- FID 체계: 그룹당 100번대 블록(`FID_BASE`: KEY 101 · FOH 111 · BACK 201 · SIDE-L 301 · SIDE-R 311 · WASH-U 401 · WASH-D 421 · MOVER-U 501 · MOVER-D 521 · BLIND 601 · STROBE 611 · HAZE 621 · FOLLOW-1 631). LX-SEQ 스펙 §13 규칙 3이 곡 파일과 RIG 팩이 공유한다고 못박는다 → **FID는 보존해야 하며 자동 배정으로 대체할 수 없다**.
- `Ch=0` 장비(FOLLOW-1 수동 운용, `rig_data.py` FIXTURES 마지막 행)는 `make_rig.py:37`이 `manual_rows`로 분리해 **CSV 패치 행에 넣지 않는다**(이번 CSV에 없음). 파서는 방어적으로 `Ch=0`을 제외행으로 다룬다.

### 1.2 검증기 R1~R8 — 파서가 거울로 삼을 것

`validate_rig.py`: R1 FID 고유 · R2 같은 유니버스 안 구간 겹침 없음 + 끝 주소 ≤ 512 · R3 그룹 총 ch = ch×수량 · R4~R8은 유니버스 계획·그룹·프리셋·곡 파일 상호참조(**패치 단계 밖**). 파서는 R1·R2를 행 거부로, R3는 `AddrRange` 산술로 거울 삼는다.

### 1.3 스펙 §9·§13

PATCH 시트 열(§9)은 곡 파일용 요약(`Count`·`Fixture ID` 범위 `101 thru 108`)이고, RIG 팩 PATCH(§13)는 **픽스처 단위**(FID·Universe.Address·주소 범위)다. 본 SPEC의 입력은 후자의 CSV 병행 출력이다. §13 규칙 2: 충돌 시 RIG 팩이 정본.

### 1.4 `04_grandMA3/*.ma3.txt`

머리 주석 "실행 순서: **패치(수동)** → §1 그룹 …" — 스크립트는 패치를 다루지 않는다(손 패치 전제). `Fixture 101 Thru 106 … Store Group` 구문은 2단계(그룹) SPEC의 참고 자료. 본 SPEC이 재생하지 않는다.

---

## 2. 기존 툴 4종의 정확한 계약 `[코드]`

### 2.1 `resolve_fixture_type` — `tools.py:3408`, ToolDefinition `:7437`

- 인자: `{"instrument_type": str}`(필수, additionalProperties False).
- 동작: `read_library_snapshot(state_port)` → `candidate_names(requested, snapshot.names)`(토큰 단위) · 정확 일치.
- `status` 분기: `library_unreadable`(is_error=True, "없다고 단정하지 마라") · `present`(`resolved`, 정확 일치 또는 후보 1개면 `matched_by="name"`) · `ambiguous`(후보 여럿 — `question_port` 있으면 **스스로 카드로 묻고** 답이 후보면 `present`+`confirmed_by_user`) · `absent`(`can_the_server_add_it=False`, `provisioning_plan`, `why_not`; `question_port` 있으면 콘솔에서 추가해 달라고 청하고 `wait_for_library_addition`로 대기 → 들어오면 `present`).
- 반환 `awaited_human=bool(payload.get("answer"))`. 실측 선례: «robe esprite» → «Robin Esprite» 토큰 대조.
- 매퍼에의 함의: 타입마다 1회 호출, `present`의 `resolved`만 `console_type`으로 쓴다. 카드 대기를 가로채지 않는다.

### 2.2 `resolve_patch_address` — `tools.py:3630`, ToolDefinition `:7476`

- 인자: `address:"U.A"`, `count:int`, `channels_per_fixture:int`(전부 필수). `property_port` 없으면 에러.
- 동작: `read_inventory` → `occupants_from_patch_values((patch_raw, name, fixture_type) …)` → `evaluate_address_fit(requested, count, width, occupants)`. `fit.ok`면 `status="free"` + `placements`; 아니면 `occupied` + `collisions` + `suggestion=first_free_address(...)` + 카드로 새 주소를 묻고 재판정(`still_occupied`/`unreadable_answer`).
- 매퍼에의 함의: **본 SPEC은 이 툴을 부르지 않는다** — 점유 시 다른 자리를 제안·이동하는 것이 감독 결정 ③과 충돌한다. 같은 판정 규약(`addressfit.evaluate`, 구간 안 시작 장비만 확정 충돌, `blind_spot`)을 **행 단위(count=1, width=Ch)**로 매퍼가 직접 소비한다.

### 2.3 `patch_fixtures` — `tools.py:3820~4340`, ToolDefinition `:7525`

- 인자 스키마: `console_type`(필수) · `console_mode` · `address`(필수, "U.A") · `count`(필수) · `channels_per_fixture`(폴백) · `fids: int[]` · `name_prefix` · `plugin_name`. additionalProperties False.
- 전제 포트: `deploy_pipeline`·`property_port`·`execution_port` 셋 다 없으면 에러(쓰기 전 거부).
- 흐름: ① `read_type_mode_widths(state_port, property_port, root=rig_paths["fixture_types"], type_name)` → 모드 목록·채널 수 실측. `console_mode` 지정 시 이름(대소문자 무시) 일치 필요(`mode_not_found`); 미지정+모드 1개면 자동; 여럿이면 `question_port` 카드(없으면 `mode_choice_needed`). 실측 폭이 호출자 폭을 이긴다(`footprint_corrected`). 폭 미확정 → `footprint_unknown`. ② `read_inventory` → `occupants_from_patch_values` → `evaluate_address_fit(address, count, width)` → 충돌 시 `address_not_free`(**런 전체 거부**, 옮기지 않음). ③ `fids` 주어지면 **그대로**(`tools.py:4039-4041`, 검증 없음); 없으면 `read_existing_fids` 전수 판독 → 미해결>0이면 `fids_unknown` 거부 → `free_fids(taken, count, start=max+1)`. ④ `staged_plan(console_type, console_mode, footprint, placements=fit.placements, fids, name_prefix)` → `luagen` AddFixtures Lua(픽스처당 1 call, 이름 `f"{prefix} {fid}"`). ⑤ `deploy_pipeline.deploy("CopilotPatch"+타입영숫자, lua)` → `deployed` 아니면 `not_deployed`(is_error). ⑥ `run_commands(["Plugin 'X'"])` **경유**(게이트 통과) → 재조회 `read_inventory` → `judge_staged_patch`(계획 자리에 무엇이 앉았는지만 센다) → `created`/`created_partially`/`created_nothing`/`unverified`. 0건+실행됨+`question_port` → "Patch 편집기를 열어 달라" 카드 → `ANSWER_RAN_IT`면 서버 재실행 1회. `command_outcomes`는 게이트 행 또는 `executed_ok/partially_created/not_created`.
- 매퍼에의 함의(핵심): (a) **FID 점유는 호출자 책임** — `fids`를 명시하면 검증이 없다. (b) 주소 거부는 런 단위 → 행 단위 선별 필요. (c) `console_mode`는 콘솔 이름이어야 한다 → CSV `Mode`를 그대로 넣으면 `mode_not_found`. (d) 이름은 `name_prefix`+FID — Group 접두 확정(`"{Group} {FID}"`, plan.md 결정 I). (d′) 모드 선택 카드는 빌리지 않는다 — 매퍼가 `console_mode`를 확정하지 못한 타입은 `mode_unresolved`로 건너뛰고 `mode_overrides`로 재호출(결정 J). (e) 플러그인 이름은 타입별 기본값으로 충분(런이 같은 타입이면 같은 플러그인 슬롯을 재배포 — 순차 실행이라 안전).

### 2.4 `precheck_patch` — `tools.py:2649`

- 인자 `create_macro: bool`. `read_inventory` → `walk_mode_widths`(점유폭 상계) → `evaluate_patch` → `build_precheck_report`. 매크로 옵션은 `run_commands` 경유.
- 매퍼에의 함의: 본 SPEC의 점유 판정은 `precheck_patch`가 아니라 그 아래 `read_inventory`를 직접 소비한다(`precheck_vectorworks_diff`·`apply_vectorworks_patch`가 이미 그렇게 한다 — `_InventoryPort(state_port, property_port)`). `precheck_patch`의 리포트는 **쓰기 전후 대조용**으로 M4 사용자 절차에서 부른다(코드 의존 없음).

### 2.5 두 쓰기 경로의 차이 — 왜 `patch_fixtures`인가

| | `patch_fixtures`(MVP/round24 후속) | `apply_vectorworks_patch`(AUTOPATCH-001) |
|---|---|---|
| 실행 주체 | **서버**(`run_commands` 경유) + 재조회 판정 | **사람**(Lua 전달) + 서버 검증 |
| 라이브 증거 | 2026-08-18 onPC 2.4.2.2: 편집기 열림 → 60→62 생성 확인(`tools.py:4120-4132` 주석) | AUTOPATCH M0: 서버 실행 AddFixtures 0건(목적지 Root) → 사람 실행으로 전환 |
| 입력 | 타입·주소·대수(+fids) | VWX 차이 리포트 |
| 점유 처리 | 런 단위 거부 | `screen_idempotent`/`screen_console_occupancy` 행 단위 |

두 증거는 모순이 아니다 — 갈림길은 **명령 목적지**(편집기 열림 여부)였고, `patch_fixtures`는 그 조건을 카드로 청한 뒤 재실행한다. LX-SEQ 입력은 차이 리포트가 아니라 행 단위 패치 지시이므로 `patch_fixtures`가 맞다. AUTOPATCH의 행 단위 선별 아이디어(`already_patched_identical`)는 매퍼가 **개념만** 계승한다(코드 재사용은 `server/vwx/apply.py`가 VWX 리포트 형상에 묶여 있어 부적합).

---

## 3. 재사용 헬퍼 시그니처 `[코드]`

| 함수 | 위치 | 시그니처 · 반환 |
|---|---|---|
| `read_inventory(port, policy=None) -> Inventory` | `server/prechk/inventory.py:344` | `Inventory.fixtures: tuple[FixtureRecord]`(`slot, name, patch_raw, fixture_type, mode, fid_note`) · `completeness` |
| `console_read_caveat(inventory: Inventory) -> dict | None` | `server/vwx/apply.py:672`(plan-audit O3 — 이전 기재 inventory.py는 오기; `grep -rn "def console_read_caveat" server/` 로 확인) | 절단 caveat(`CONSOLE_READ_INCOMPLETE` 코드는 `server/vwx/verdicts.py:81`) — 매퍼는 dict만 소비 |
| `occupants_from_patch_values(iter[(patch_raw, name, fixture_type)]) -> tuple[Occupant]` | `server/vwx/addressfit.py:86` | 못 읽은 주소는 버린다 |
| `evaluate(requested, *, count, width, occupants) -> Fit` | `server/vwx/addressfit.py:137` | `Fit.ok/collisions/placements/blind_spot/span_text` — 구간 안 시작 장비만 충돌 |
| `read_existing_fids(fid_property_port) -> ExistingFidRead` | `server/vwx/patchplan.py:1395` | `.attempted/.fids/.unseen/.unreadable_fids/.unusable_rows/.unparsable_rows/.root_unreadable/.child_count` — `patch_fixtures:4050-4063`이 미해결 합으로 거부 |
| `read_type_mode_widths(state_port, property_port, *, root, type_name) -> TypeModeRead` | `server/prechk/mode_read.py:76` | `.attempted/.type_found/.modes[ModeChoice(name,width)]/.detail` |
| `read_library_snapshot(state_port) -> LibrarySnapshot` · `candidate_names(requested, names)` | `server/vwx/librarywatch.py` | 타입 후보 토큰 대조(툴 내부에서 이미 쓰임 — 매퍼는 툴 결과만 받는다) |
| `staged_plan(...)`/`judge_staged_patch(...)`/`free_fids(...)` | `server/vwx/stagedpatch.py:133/215/118` | **매퍼가 부르지 않는다**(`patch_fixtures` 내부) — 계약만 참고: `plan`은 자리 수≠FID 수면 ValueError |
| `_InventoryPort(state_port, property_port)` | `tools.py` 내부 어댑터 | 툴 계층에서만 — `server/lxseq/`는 Protocol 타입만 받는다 |

---

## 4. 경계 · 테스트 · 입력 채널 `[코드]`

- `test_architecture.py:48 _FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc")` — 신규 `server/lxseq/`도 자동 대상.
- `test_tools.py:170-172`: `sorted(definition names) == sorted(TOOL_NAMES)` + `len == 33` — 신규 툴 등재 시 **34로 한 줄 갱신 필수**(M3 파일 목록).
- `test_vwx_stagedpatch.py`: `build_toolset` 가짜 포트로 `patch_fixtures`를 오프라인 검증하는 선례 — M3 테스트가 같은 가짜를 재사용.
- `build_toolset(...)` 포트: `execution_port`·`state_port`·`property_port`·`deploy_pipeline`·`question_port`·`vectorworks_upload` 등. 신규 툴은 새 포트를 요구하지 않는다.
- 입력 채널: `session.py:9655 upload_vectorworks_export(file_name, content_base64)`는 세션 업로드를 바꾸고 **즉시 `_VECTORWORKS_UPLOAD_INSTRUCTION`을 실행**한다; 시스템 노트(`:9825-9831`)도 "Vectorworks export 1개 업로드됨 — `vectorworks_autopatch`로만 접근"을 주입한다. LX-SEQ CSV를 이 포트로 올리면 VWX 파서가 먼저 받는다 → 재사용 **기각**(plan.md 결정 H, 감독 답 ① 2026-08-21). 채택: `precheck_vectorworks_diff:2830-2836`과 같은 `file_content_base64` 인자(base64 `validate=True` 검증·오류 문구 패턴 재사용). 바이트는 파일에서만(현재 절차 t9: 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`가 읽어 base64로 전달 — 서버는 파일 경로를 받지 않는다 / t10 이후: UI 파일 선택기) — 채팅 붙여넣기 불허(REQ-LXSEQ-016). **주의**: 현재 UI(`ui/src/App.tsx` FileReader 2곳 · `ui/src/protocol.ts` `buildVectorworksExportUpload`/`buildLayoutImageUpload`)는 세션 메시지로만 파일을 보내며 **툴 인자를 채우는 파일 선택기는 아직 없다** — §6-6.
- 룰북 `30_plugin_patterns.md:8-53`: "패치는 Lua `AddFixtures`뿐 · `ChangeDestination` 금지 · 플러그인 이름은 단일 인용부호" — 전부 `patch_fixtures`/`luagen`이 이미 지키며 본 SPEC은 룰북을 건드리지 않는다.
- `pyproject.toml`: Python ≥3.11, pytest 경로 `server/tests`, `ruff` dev 의존. 신규 런타임 의존성 **0건**(csv·base64 표준 라이브러리).
- `quality.yaml development_mode: tdd` → M1~M3 cycle_type=tdd.

---

## 5. 메모리 교차 확인 `[메모리]`→`[코드]`

| 메모리 | 코드로 확인한 것 | 본 SPEC 반영 |
|---|---|---|
| `grandma3-group-membership-not-readable` | (코드 밖 관측) 그룹 멤버십 `childCount:0` | 감독 결정 ③의 근거 — 점유 덮어쓰기 금지(REQ-LXSEQ-006) |
| `copilot-fid-vs-slot-decision` | `patch_fixtures:4043-4049` 주석 "FID는 인벤토리에서 못 얻는다", `inventory.FixtureRecord.fid_note` 미확정 | FID는 `fids` 인자로만(REQ-LXSEQ-003); FID 점유는 `read_existing_fids`로(REQ-LXSEQ-006) |
| `project_copilot_patch_cracked` | `tools.py:4120-4132` 2026-08-18 재실측 주석 · 룰북 `30_plugin_patterns.md:20-29` | 목적지 처리는 `patch_fixtures`에 위임, 덧붙임 0(사전 확정 사실 5) |
| "추측하지 마라"(`resolve_fixture_type` 독스트링 `:3411-3418`) | Import 문법·GDTF 추측 5회 실측 실패 | REQ-LXSEQ-004/005 |

---

## 6. 갭 · 미확정 `[미확정]`

1. **콘솔 라이브러리의 실제 타입명 8종** — 라이브 없이는 모른다(`ASSUMPTION-72`). 테스트는 녹화 payload로 4분기를 모두 덮고, 실제 이름은 M4가 적는다.
2. **타입별 모드 수·이름** — `ASSUMPTION-73`. `Ch` 폭 유일 매칭이 8종 중 몇 종에서 성립하는지 M4가 판정.
3. **`read_existing_fids` 전수 여부(onPC 쇼파일)** — `ASSUMPTION-74`. AUTOPATCH M0 1차 GO를 계승하되 이번 쇼파일로 재판정.
4. ~~입력 채널·이름 접두·모드 미해결 처리~~ — 2026-08-21 감독 답으로 닫힘(plan.md 결정 H·I·J, `progress.md` "M0 — Kickoff 결정 기록").
6. **UI 파일 선택기 → `file_content_base64` 전달 경로가 저장소에 없다.** 감독 답 ①은 "바이트는 UI 파일 선택기만 · 세션 업로드 포트 재사용 기각 · 신규 엔드포인트 기각"인데, 현재 UI의 파일 선택기 2곳은 모두 세션 메시지(`vectorworks_export_upload`·`layout_image_upload`)로 가고 툴 인자를 직접 채우지 않는다. 본 SPEC은 `ui/`·`session.py`를 건드리지 않으므로(파일 범위 밖) 전달 경로는 **후속 카드 t10으로 위임됐다**(감독 판정, 칸반 리드 경유, 2026-08-21) — M3는 툴 측 보루(설명문·`guidance`·`source.sha256`)까지만. M4 라이브는 UI가 아니라 **로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님; `server/tools/busking_e2e.py`·`groupgen_e2e.py`와 같은 DEV TOOL 계열, `build_console_stack` + `build_toolset` 실포트 조립)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출**해 수행한다(plan.md M4 · acceptance.md AC-016) — 서버는 파일 경로를 받지 않는다(REQ-LXSEQ-010 인자 집합 불변); 채팅 경유 호출은 t10 이후(그때까지 운영자는 채팅으로 이 툴을 쓸 수 없다). UI 파일 선택기 경로는 t10 이후의 목표 상태다.
5. **`name_prefix`에 한국어/하이픈 그룹명(`SIDE-L`, `MOVER-U`)이 들어갈 때 Lua 문자열·플러그인 이름 안전성** — `luagen._lua_string`이 이스케이프를 맡고 플러그인 이름은 타입 영숫자만 쓰므로 문제 없어 보이나(`[코드]` `tools.py:4094`), 하이픈 포함 이름으로 실기 확인은 M4에서.
