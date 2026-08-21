# SPEC-COPILOT-LXSEQ-001 — 구현 계획 (plan)

문서 상태: implemented (v0.2.2, 2026-08-21 — M0~M4 종료 · sync 완료 · AC 17건 중 16 PASS + AC-016 PASS-WITH-DEBT(결함 D2는 카드 t11로 분리) — 문서 전용: plan-audit 2회차 N1·R1~R3·R5 반영 — M4 입력 = 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`, 서버는 파일 경로를 받지 않는다) · Tier M · 칸반 카드 t9 (4단계 중 1단계)

> **v0.2.2 — plan-audit 2회차(FAIL 0.88) N1(blocking)·R1~R3·R5 반영(문서 전용, 설계 변경 0).** M4 입력 전달 = 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV를 읽어 base64로 `import_lxseq_patch` 핸들러를 직접 호출; 서버는 파일 경로를 받지 않는다(REQ-LXSEQ-010 인자 집합 불변); 채팅 경유 호출은 t10 이후. v0.2.1 — 문서 전용: UI 전달 경로 t10 위임.
>
> **v0.2.0 — plan-audit 1회차(FAIL 0.86) 델타 + 감독 Kickoff 답 3건 반영.** 마일스톤 **M0~M4**(5개), 결정 등록부 **10건(A~J)**, 열린 결정 마커 **0건**(§A.4의 3건은 2026-08-21 감독 답으로 닫혀 결정 H·I·J가 됐다). REQ 16건 · AC 17건(라이브 1건) · ASSUMPTION 3건(72~74). 마일스톤별 `- **AC**:` 줄은 `acceptance.md` §C.0a와 1:1이며 합 **17 · 중복 0 · 누락 0**.
>
> v0.1.0 — 최초 작성(결정 A~G, 마커 3건).
>
> **참조 규약.** 정본(spec.md · acceptance.md)은 줄번호로 인용하지 않고 `REQ-LXSEQ-001` · `AC-LXSEQ-001` · `ASSUMPTION-72` 같은 안정 토큰만 쓴다. 코드·룰북·입력 데이터·타 SPEC 아티팩트는 `파일:줄` 좌표를 쓴다.

---

## §A. 맥락과 우선순위 — 바뀔 가능성이 큰 결정부터

### §A.1 가장 먼저 읽을 것 — 이 SPEC에서 결정이 뒤집힐 수 있는 지점

| 순위 | 결정 | 왜 앞에 두나 | 어디서 닫히나 |
|---|---|---|---|
| 1 | **쓰기 경로 = `patch_fixtures` 하나.** `apply_vectorworks_patch`(사람 실행) 경로는 쓰지 않는다 | 저장소에 쓰기 경로가 둘이다. 섞으면 "누가 실행했나"가 보고에서 흐려진다. 라이브로 생성이 확인된 쪽은 `patch_fixtures`(2026-08-18)다 | 결정 A(§A.3) — 닫힘 |
| 2 | **매퍼가 행 단위로 점유를 먼저 거른다.** `patch_fixtures`는 `fids`를 검증하지 않고, 주소 거부는 런 단위다 | 감독 결정 ③을 기존 툴이 그대로는 보장하지 못한다(`research.md` §2.4). 매퍼의 핵심 책임이 여기다 | 결정 B — 닫힘 |
| 3 | **런 경계에 `Group`을 포함한다(=이름 접두 단위, `name_prefix_mode="group"`).** KEY 6대와 FOH 8대는 같은 타입·연속 주소지만 런 2개(86대 → 12런) | 이름 접두(`name_prefix`)가 런 단위이므로 Group을 접두로 쓰려면 런을 갈라야 한다. 접두를 타입명으로 하면 **9런**으로 합쳐지나 콘솔 이름에서 그룹을 읽을 수 없다 | 결정 I(§A.3) — **닫힘**(감독 답 ②, 2026-08-21) |
| 4 | **입력 채널 = `file_content_base64` 인자, 바이트는 파일에서만(채팅 붙여넣기 금지; 현재 절차 t9: 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`가 읽어 base64로 전달 — 서버는 파일 경로를 받지 않는다 / t10 이후: UI 파일 선택기)** | 세션 업로드 포트는 Vectorworks 안내 분석을 즉시 시작한다(`session.py:9655`). LX-SEQ CSV를 거기 올리면 VWX 파서가 먼저 받는다. 붙여넣기는 개행·공백이 조용히 깨진다 | 결정 H(§A.3) — **닫힘**(감독 답 ①, 2026-08-21) · **UI 측 전달 경로는 후속 카드 t10으로 위임됨**(§A.4 ① 잔여 메모) |
| 5 | **모드 미해결 시 `mode_unresolved` 건너뛰기 + `mode_overrides` 재호출(대안 채택, 기본안 카드 위임 기각)** | 86대 중 한 타입이라도 모드가 여럿이면 기본안은 런마다 카드가 뜬다. 대안은 보고 1회 + 재호출 1회 — 감독 결정 ③(건너뛰고 보고)과 같은 자세 | 결정 J(§A.3) — **닫힘**(감독 답 ③, 2026-08-21, **비기본 선택**) |
| 6 | 툴 1종(`preview`/`apply`) vs 2종 | `vectorworks_autopatch`가 `analyse`/`prepare`를 한 툴로 묶은 선례가 있다. 2종이면 계획을 모델이 들고 다녀야 한다 | 결정 C — 닫힘(1종) |
| 7 | 파일 구조·테스트 파일명·등재 지점 | 기계적 | 결정 D~G — 닫힘 |

### §A.2 빌드 순서 vs 무엇이 무엇을 막는가

빌드 순서 **M0 → M1 → M2 → M3 → M4**. 강한 순차 사슬이다(파서 산출 → 매퍼 입력 → 툴 위임 → 라이브).

| 항목 | 막는 대상 | 성격 | 부정 시 처리 |
|---|---|---|---|
| (닫힘) 결정 H·I·J(§A.3) | M2 런 경계·M3 입력 채널·M2 모드 처리 | 2026-08-21 감독 답으로 닫힘 — 마커 0건 | 해당 없음. 답은 `progress.md` "M0 — Kickoff 결정 기록"에 있다(AC-LXSEQ-001 ⑤) |
| `ASSUMPTION-72` 타입 8종 해석 | M4만 | 동작 축소 아님 — `type_unresolved` 건너뛰기 | 사용자가 콘솔에서 타입 추가 후 재실행 |
| `ASSUMPTION-73` 모드 유일성 | M4만 | 그 타입 행이 `mode_unresolved`로 건너뛰어짐(결정 J) | 사용자가 `mode_overrides`로 재호출; 코드 변경 없음 |
| `ASSUMPTION-74` FID 전수 판독 | M4 `apply` 전부 | 전 행 `console_read_incomplete` | 쇼파일 상태를 사용자에게 알린다; 코드 변경 없음 |

### §A.3 결정 현황 — 해소 10건 (A~G 최초 · H~J 2026-08-21 감독 Kickoff 답)

| 결정 | 이름 | 확정 내용 | 반영 M |
|---|---|---|---|
| **A** | 쓰기 경로 | `patch_fixtures` 핸들러에 내부 `ToolCall`로 위임. `apply_vectorworks_patch`·신규 Lua·`run_commands` 직접 호출 0건 | M3 |
| **B** | 점유 판정 주체 | 매퍼가 **행 단위**로 DMX 자리(`occupants_from_patch_values` + 구간 안 시작 규약)와 FID(`read_existing_fids`)를 먼저 거른다. 전수 아니면 `apply` 0런 | M2 |
| **C** | 툴 수 | **1종** `import_lxseq_patch`, `action ∈ {preview, apply}`(기본 preview). 2종(parse/preview + apply) 기각 — 계획을 모델 컨텍스트로 왕복시키고, 두 호출 사이에 콘솔이 바뀌어도 모른다. 1종은 `apply`가 내부에서 계획을 **다시** 만들어 그 시점 콘솔 상태로 점유를 판정한다 | M3 |
| **D** | 모듈 위치 | `server/lxseq/{__init__,parser,mapper}.py` 신설. `server/vwx/` 안에 두지 않는다(VWX PRESERVE 전량, 그리고 LX-SEQ는 Vectorworks가 아니다) | M1~M2 |
| **E** | 닫힌 어휘 | 행 거부 `kind` 7종 · 건너뛰기 `kind` 8종 · 모드 해석 3종(`resolved`/`unresolved`/`tree_unread`) · 런 status는 `patch_fixtures`의 status를 **그대로** 전달(재명명 0건) | M1~M3 |
| **F** | 라이브 세션 회계 | **1회(M4, 사용자 수행).** 감독 결정 ②가 "각 단계 onPC 실기 검증"을 명시한다. M0~M3은 오프라인(녹화 fixture·가짜 포트) | M4 |
| **G** | 테스트 입력 | 실물 CSV 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`가 계약이다 — **plan-phase v0.2.0(2026-08-21)에서 복사해 이 카드 커밋에 포함**(sha256 `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3`, 정본과 동일 실측; 이 카드가 저장소에 넣는 유일한 데이터 파일). 원본은 주 체크아웃의 **git 미추적 로컬 정본**(`src/Lighting_Designer/02_RIG팩/`, 워크트리에는 없다 — 저장소 아카이브가 아니다). 오프라인 테스트·AC는 **사본만** 읽는다(절대경로 0건). 뮤테이션은 이 사본을 메모리에서 변형 | 사본 확인 M0 · 소비 M1~M3 |
| **H** | 입력 채널(감독 답 ①) | 툴 인자 `file_content_base64`(기본안 채택). 세션 업로드 포트(`upload_vectorworks_export`) 재사용 **기각** · 신규 엔드포인트 **기각**. 바이트는 **파일(현재 절차 t9: 로컬 하네스 스크립트가 읽음 / t10 이후: UI 파일 선택기)에서만** — 채팅 붙여넣기 경로는 **불허**(개행·공백이 조용히 깨져 잘못 패치된다) → `REQ-LXSEQ-016 [Unwanted]` + `AC-LXSEQ-017`. 감독이 금지한 것은 "사람이 CSV 본문을 채팅에 붙여넣어 그 텍스트로 바이트를 만드는 것"이며, M4에서 허용되는 것은 "로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출하는 것"이다 — **서버는 파일 경로를 받지 않는다**(REQ-LXSEQ-010 인자 집합 불변, `file_path` 류 인자 신설 없음); 채팅 경유 호출은 t10 이후. 둘은 충돌하지 않는다. UI 파일 선택기 → 툴 인자 전달 경로는 **후속 카드 t10으로 위임됨**(§A.4 ①) | M3 |
| **I** | 픽스처 이름 접두(감독 답 ②) | `name_prefix_mode="group"`(기본안 채택), 이름 `"{Group} {FID}"`. 런 10→**12개**는 수용한 비용. 근거: 콘솔이 이름에서 그룹을 읽는다 · 2단계 그룹 SPEC과 어휘를 공유한다. 타입 접두 대안은 `name_prefix_mode="type"`으로 남되 런은 **9개**(KEY+FOH · BACK+SIDE-L · WASH-U+WASH-D 병합 — 실물 CSV 계산, 10이 아님) | M2 |
| **J** | 모드 미해결 시 처리(감독 답 ③ — **대안 채택, 기본안 기각**) | 실측 폭·토큰으로 모드를 확정하지 못한 타입의 행은 `mode_unresolved`로 **건너뛰고** 보고 목록 하나에 모은다. 사용자가 `mode_overrides: {"<FixtureType>": "<콘솔 모드>"}` 인자로 재호출한다(실측 목록에 있는 이름만 채택). `patch_fixtures` 선택 카드 위임(기본안)은 **채택하지 않는다** — 감독 결정 ③과 같은 자세(건너뛰고 보고, 최대 12회 대신 1회 중단). `ASSUMPTION-73`은 그대로 둔다 | M2~M3 |

### §A.4 열린 결정 — 전부 닫힘 (2026-08-21 감독 Kickoff 답 · 마커 0건)

세 항목은 결정 H·I·J(§A.3)로 옮겼다. 아래는 기각안과 잔여 메모만 남긴다.

1. **입력 채널 → 결정 H.** 기본안(`file_content_base64` 인자) 채택. 기각: 세션 업로드 포트 재사용(업로드 즉시 Vectorworks 안내 분석이 돈다, `server/web/session.py:9655-9658`) · 신규 업로드 엔드포인트(UI 변경 수반). 채팅 붙여넣기 **불허**(REQ-LXSEQ-016). **잔여 메모(후속 카드 t10으로 위임됨):** 현재 UI의 파일 선택기 2곳(`ui/src/App.tsx` FileReader — Vectorworks export 업로드 · 레이아웃 이미지 업로드)은 둘 다 세션 메시지로 가며 툴 인자를 직접 채우는 경로가 **아직 없다**. "UI 파일 선택기가 `file_content_base64`를 채운다"는 전달 경로(`ui/` + `server/web/session.py`)는 감독 판정(칸반 리드 경유, 2026-08-21)으로 **후속 카드 t10**에 위임됐다 — 본 SPEC은 신규 툴 밖 0-diff를 유지하고, M3는 툴 인자 계약과 기계적 보루(설명문 · `guidance` · `source.sha256`)까지만 책임진다(`research.md` §6-6). 본 카드(t9)의 M4 라이브는 UI가 아니라 **로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV를 읽어 base64로 `import_lxseq_patch` 핸들러를 직접 호출**해 수행한다(M4 절) — 서버는 파일 경로를 받지 않는다; 채팅 경유 호출은 t10 이후. 감독 결정 ①은 t10으로 이행된다.
2. **픽스처 이름 접두 → 결정 I.** `group` 채택, 12런 비용 수용. 타입 접두였다면 **9런**(10이 아님 — KEY+FOH 1.001–168 · BACK+SIDE-L 4.001–450 · WASH-U+WASH-D 5.151–330 세 쌍 병합, 86행 직접 계산).
3. **모드 미해결 시 처리 → 결정 J.** **대안 채택**(`mode_unresolved` 건너뛰기 + `mode_overrides` 재호출), 기본안(`console_mode` 생략 → `patch_fixtures` 카드) **기각**. 이 항목만 비기본 선택임을 명시한다.

### §A.5 PRESERVE 재확인

| 항목 | 방침 |
|---|---|
| `console/lua/**` · `server/safety/**` | 쓰기 경로를 새로 만들지 않으므로 접촉 0건 |
| `server/vwx/**` · `server/prechk/**` · `server/paperwork/**` | **소비만**. `addressfit.evaluate`/`occupants_from_patch_values`·`patchplan.read_existing_fids`·`mode_read.read_type_mode_widths`·`inventory.read_inventory`·`librarywatch.read_snapshot`/`candidate_names` |
| `server/orchestrator/tools.py` 기존 핸들러 | 본문 0-diff. 신규 툴은 `vectorworks_autopatch`처럼 **내부 `ToolCall`**로 `resolve_fixture_type`·`patch_fixtures` 핸들러를 부른다 |
| `server/rulebook/assets/**` | 무변경. 신규 툴의 `description`이 모델 안내를 전담한다 |
| `server/tests/test_tools.py` | `len(TOOL_NAMES) == 33` → `34` 한 줄만 |

---

## §B. 마일스톤 M0~M4

각 마일스톤은 착수 직전 baseline을 직접 잰다. plan-phase 기준선(`progress.md` §E.1: **9596 passed · 8 skipped · 1 warning · 157.34s**)은 기록일 뿐 이월하지 않는다.

### M0 — 기존 툴 계약 확인 · 입력 정본 고정 (cycle_type=none — 코드 변경 0)

- **요구·설계 지시**: `research.md` §2의 4종 툴 계약(인자·status·거부 분기)을 run-phase 착수 시점의 `tools.py`와 **다시** 대조해 드리프트를 `progress.md`에 기록한다(줄번호는 흔들린다 — 토큰 앵커로 재확인). **입력 사본 확인:** 사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`는 plan-phase v0.2.0이 이미 복사해 커밋했다(결정 G). M0는 복사하지 않고 `test -f server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv || { echo FAIL; exit 1; }` + `shasum -a 256` == `77a34d4bfd611fc034ce621c9715c1e33129df244a67c7e8dfd75d83816d7ee3` + 86행을 확인만 한다(없거나 다르면 **명시적 FAIL**, 건너뛰기 없음). 전체 스위트 baseline을 잰다. 결정 H·I·J의 답이 `progress.md` "M0 — Kickoff 결정 기록"에 있는지 확인한다.
- **baseline**: 코드 baseline 없음. 사본 존재(`test -f … || exit 1`) + sha256 일치 + 86행 + 헤더 9열을 직접 확인.
- **뮤테이션**: ① 계약 대조 없이 M1로 가면 `AC-LXSEQ-001`이 죽어야 한다. ② CSV 사본 sha256이 기록된 정본 해시와 다르거나 사본이 없으면 `AC-LXSEQ-001` ②가 명시적으로 죽어야 한다(건너뛰기 아님).
- **파일**: 코드 변경 0(사본 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`는 plan-phase 커밋에 이미 포함). 기록은 `progress.md` M0 절.
- **AC**: AC-LXSEQ-001.

### M1 — 파서 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-LXSEQ-001`~`REQ-LXSEQ-003` 구현. `server/lxseq/parser.py` — BOM 흡수, 헤더 이름 매칭(위치 금지), 9열 누락 시 파일 단위 실패, 행 검증 7부류(`validate_rig.py` R1~R3 거울 + AddrRange 산술 + 512 초과), `extra` 보존, `Ch=0` 제외행 분리. 순수 함수 — 콘솔·네트워크 0.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 위치 기반으로 열을 읽으면(열 순서 섞은 CSV) `AC-LXSEQ-002`가 죽어야 한다. ② AddrRange 산술 검사를 끄면 `AC-LXSEQ-003`이 죽어야 한다. ③ FID를 주소로 쓰면 `AC-LXSEQ-004`가 죽어야 한다. ④ 거부 행에서 예외를 던지면 `AC-LXSEQ-003`이 죽어야 한다.
- **파일**: 신규 `server/lxseq/__init__.py`, `server/lxseq/parser.py`; 테스트 `server/tests/test_lxseq_parser.py`.
- **AC**: AC-LXSEQ-002, AC-LXSEQ-003, AC-LXSEQ-004.

### M2 — 매퍼 · 드라이런 계획 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-LXSEQ-004`~`REQ-LXSEQ-009` 구현. `server/lxseq/mapper.py` — 타입 해석 결과(`TypeResolution`)·모드 실측(`read_type_mode_widths`)·`mode_overrides`·인벤토리(`read_inventory`)·FID 실측(`read_existing_fids`)을 **주입받아** 모드 확정(유일 폭 → 토큰 → override, 아니면 `mode_unresolved` 건너뜀 — 결정 J) → 점유 판정 → 런 묶기(`Group` 경계 — 결정 I) → `ImportPlan`. 콘솔 포트는 인자로 받는다(읽기만). 쓰기 수단 이름·문자열 0건(AST 스캔). `resolve_fixture_type` 호출 자체는 M3 툴 계층이 하고, M2는 그 결과 dict를 받는다(테스트는 녹화 payload).
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① `absent` 타입의 행을 런에 넣으면 `AC-LXSEQ-005`가 죽어야 한다. ② 같은 폭 모드가 둘인데 첫 번째를 집으면(또는 `mode_unresolved`로 건너뛰지 않고 `console_mode`를 비워 런에 넣으면) `AC-LXSEQ-006`이 죽어야 한다. ③ 점유 행을 런에 넣으면 `AC-LXSEQ-007`이 죽어야 한다. ④ FID 판독이 불완전한데 런을 내면 `AC-LXSEQ-008`이 죽어야 한다. ⑤ 런 경계 규칙을 깨면(비연속 주소를 한 런으로) `AC-LXSEQ-009`가 죽어야 한다. ⑥ `server/lxseq/`에 `from server.vwx.luagen import …`를 넣으면 `AC-LXSEQ-010`이 죽어야 한다.
- **파일**: 신규 `server/lxseq/mapper.py`; 테스트 `server/tests/test_lxseq_mapper.py`.
- **AC**: AC-LXSEQ-005, AC-LXSEQ-006, AC-LXSEQ-007, AC-LXSEQ-008, AC-LXSEQ-009, AC-LXSEQ-010.

### M3 — 툴 등재 · 위임 · 보고 (cycle_type=tdd)

- **요구·설계 지시**: `REQ-LXSEQ-010`~`REQ-LXSEQ-016` 구현. `tools.py`에 `import_lxseq_patch` 4지점 순수 추가(인자 `file_content_base64`·`action`·`name_prefix_mode`(기본 `group`)·`only_fids`·`mode_overrides`; 설명문·`guidance`에 "채팅 붙여넣기 금지 · 파일에서 읽은 바이트만(목표 상태 t10: UI 파일 선택기)" 명시 — 보루의 본질은 붙여넣은 텍스트 거부, 페이로드 `source.sha256`·`byte_length` — 결정 H). `preview`: 파싱 → 타입마다 `resolve_fixture_type` 내부 호출 → 모드 실측 → 인벤토리·FID 읽기 → 매퍼 → 페이로드(쓰기 0). `apply`: 같은 계획을 **그 호출에서 다시** 만든 뒤 런을 순서대로 `patch_fixtures` 내부 `ToolCall`로 위임, `created` 아니면 멈춤, `awaited_human` 전달, 페이로드 집계. `test_tools.py` 33→34.
- **baseline**: 착수 직전 전체 스위트 실측.
- **뮤테이션**: ① 4지점 중 하나를 빼면 `AC-LXSEQ-011`이 죽어야 한다(파리티 테스트). ② `preview`에서 `deploy_pipeline.deploy`가 한 번이라도 불리면 `AC-LXSEQ-011`이 죽어야 한다. ③ 첫 런이 `created_partially`인데 다음 런을 실행하면 `AC-LXSEQ-012`가 죽어야 한다. ④ 2회차 호출에서 이미 패치된 행이 런에 다시 들어가면 `AC-LXSEQ-013`이 죽어야 한다. ⑤ `created` 합 < 계획 합인데 `summary_ko`가 "성공"을 말하면 `AC-LXSEQ-014`가 죽어야 한다. ⑥ PRESERVE 경로에 변경을 주입하면 `AC-LXSEQ-015` 게이트가 적발해야 한다. ⑦ 설명문·`guidance`에서 붙여넣기 금지 문구를 빼거나 `source.sha256`을 빼면 `AC-LXSEQ-017`이 죽어야 한다.
- **파일**: 수정 `server/orchestrator/tools.py`(4지점), `server/tests/test_tools.py`(상수 1); 테스트 `server/tests/test_lxseq_tool.py`.
- **AC**: AC-LXSEQ-011, AC-LXSEQ-012, AC-LXSEQ-013, AC-LXSEQ-014, AC-LXSEQ-015, AC-LXSEQ-017.

### M4 — onPC 실기 확인 (cycle_type=none — 사용자 수행 라이브 세션 1회)

- **요구·설계 지시**: 사용자가 onPC 2.4.2.2에서 Patch 편집기를 연 상태로, 입력 파일은 정본 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv`(사용자 측 절대경로)을 쓴다. **입력 전달 — 현재 절차(t9)**: 로컬 하네스 스크립트 `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님)가 정본 CSV 파일을 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러를 직접 호출한다 — **서버는 파일 경로를 받지 않는다**(인자 집합 불변). 채팅 경유 호출은 t10 이후. **목표 상태(t10 이후)**: UI 파일 선택기가 인자를 채운다(본 카드 범위 밖). 어느 쪽이든 채팅 붙여넣기 금지(REQ-LXSEQ-016 — 금지 대상은 채팅 본문 텍스트로 바이트를 만드는 것이지 스크립트가 파일을 읽는 것이 아니다). ① `preview` → 계획 확인(런 수 12·건너뛴 행·타입 해석 결과·`mode_unresolved` 목록 → 필요하면 `mode_overrides`로 재호출) ② `apply` → 런마다 `created` 관측 ③ 같은 파일로 `preview` 재호출 → 런 0개·`already_patched` 86건. `ASSUMPTION-72/73/74`를 판정한다. 제품 코드 변경 0(하네스 스크립트는 검증 도구) — 결함이 나오면 M1~M3 재개방(블로커 보고).
- **baseline**: M3 최종 스위트. 콘솔은 빈 패치(또는 사용자가 정한 시작 상태 — `progress.md`에 기록).
- **뮤테이션**: ① 계획 없이 `apply`를 곧장 부르는 경로가 있으면(`preview` 없이도 `apply`는 내부에서 계획을 만들므로 허용 — 단 점유 판정 없이 쓰면) `AC-LXSEQ-016`이 죽어야 한다.
- **파일**: 제품 코드 변경 0. 신규 **검증 도구(제품 코드 아님)** `server/tools/lxseq_e2e.py` — **소유 M4**(run 단계 파일 목록에 포함, 커밋 대상), 소재 `server/tools/`(`busking_e2e.py`·`groupgen_e2e.py`와 같은 DEV TOOL 계열 — `build_console_stack` + `build_toolset` 실포트 조립, 우회 배선 0, `server.bridge` import 0이라 `test_architecture.py` 면제 불필요, `--approve` 없으면 `DenyAllApprovalPort`). 동작: `--csv <정본 절대경로>`의 파일을 **스크립트가** 읽어 base64로 인코딩해 `import_lxseq_patch` 핸들러에 `ToolCall`로 넘긴다(`--action preview|apply`, `--mode-overrides` JSON, `--only-fids`) — 서버는 파일 경로를 받지 않는다. 실행: `uv run python -m server.tools.lxseq_e2e --csv <정본 절대경로> --action preview --listen-port 9005`(`-m` 필수 — `sys.path[0]` 함정). 기록은 `progress.md` M4 절(명령·관측값·스크린샷 경로).
- **AC**: AC-LXSEQ-016.

---

## §C. 라이브 세션 회계

**1회(M4), 사용자 수행.** 감독 결정 ②("각 단계 onPC 실기 검증")의 직접 요구다. M0~M3은 전부 오프라인 — 녹화된 `resolve_fixture_type` payload, 가짜 `state_port`/`property_port`/`deploy_pipeline`/`execution_port`(`test_vwx_stagedpatch.py`가 쓰는 `build_toolset` 가짜 포트 패턴 재사용)로 검증한다. 라이브 AC는 `AC-LXSEQ-016` 하나이며 "onPC 실기 확인" 행으로 분리한다.

---

## §D. 제약

1. **순수 함수 우선.** `server/lxseq/`는 바이트 → 레코드 → 계획. 콘솔 읽기는 주입된 포트로만, 쓰기는 0.
2. **테스트 파일명 고정.** `server/tests/test_lxseq_{parser,mapper,tool}.py`.
3. **실패 모드 분리.** 행 거부·타입 미해결·모드 미해결·점유·읽기 불완전을 한 카운터에 합치지 않는다.
4. **0건은 비공허성 동반.** "건너뛴 행 0"·"쓰기 0"을 단언할 때 스캔 대상이 비어 있지 않음을 함께 단언한다.
5. **AST 스캔.** import 경계·금지 식별자는 raw grep이 아니라 AST 식별자 스캔(`test_architecture.py` 패턴).
6. **status 재명명 금지.** `patch_fixtures`의 status 문자열을 그대로 전달한다.
7. **시간 추정 없음.** 우선순위·순서만 적는다.

---

## §E. 후속 SPEC 예약 (이름만 — 본 SPEC 범위 아님)

| 단계 | 예약 ID | 입력 |
|---|---|---|
| 2 — 그룹 | `SPEC-COPILOT-LXSEQ-002` | 본 SPEC의 FID 매핑표 + RIG `GROUP` 시트 |
| 3 — 프리셋/FX | `SPEC-COPILOT-LXSEQ-003` | `PRESET-*`·`FX` 시트 (+ 기존 FXLIB/LOOKLIB 툴) |
| 4 — 시퀀스/큐 | `SPEC-COPILOT-LXSEQ-004` | 곡 파일 `CUE-EX` CSV (+ 기존 SONGCUE/SCENE 툴) |

> 2단계 착수 메모(본 SPEC 범위 밖, 조사하지 않음): 실물 patch.csv의 `Group` 라벨은 **12종**(KEY6·FOH8·BLIND6·STROBE4·HAZE2·MOVER-U8·MOVER-D8·BACK12·SIDE-L6·SIDE-R6·WASH-U10·WASH-D10 = 86)인데 RIG팩 README는 **그룹 18**이라 적는다. 12는 패치 열 라벨, 18은 RIG `GROUP` 시트 정의일 가능성이 크다 — LXSEQ-002는 "18개를 만든다"로 출발하기 전에 나머지 6개의 출처부터 확인할 것.

---

## §F. 테스트 골격

| 파일 | 소유 AC | 핵심 fixture |
|---|---|---|
| `server/tests/test_lxseq_parser.py` | AC-LXSEQ-002, 003, 004 | 실물 CSV 사본 · 열 순서 섞음 · BOM 없음 · AddrRange 변형(hyphen/en-dash/틀린 숫자) · 512 초과 · FID 중복 · 구간 겹침 · `Ch=0` 행 |
| `server/tests/test_lxseq_mapper.py` | AC-LXSEQ-005~010 | 녹화 `resolve_fixture_type` payload 4종(present/ambiguous/absent/unreadable) · 모드 목록(유일/중복 폭/`mode_overrides` 적합·부적합) · 인벤토리(빈/부분 점유/전부 점유/절단) · FID 판독(전수/불완전) · AST 스캔 |
| `server/tests/test_lxseq_tool.py` | AC-LXSEQ-011~015, 017 | `build_toolset` 가짜 포트(호출 기록) · 파리티 · preview 쓰기 0 · apply 순차·중단 · 2회차 멱등 · 페이로드 스키마 · PRESERVE diff · 붙여넣기 금지 문구·`source.sha256` |
| (라이브 — 사용자) `server/tools/lxseq_e2e.py`(검증 도구 — 제품 코드 아님) | AC-LXSEQ-016 | onPC 2.4.2.2 · 실물 CSV(정본 절대경로 — 현재 절차 t9: 스크립트가 읽어 base64로 핸들러 직접 호출, 서버는 파일 경로를 받지 않는다 / t10 이후: UI 파일 선택기) |

---

## §G. Phase 4 Mode Selection — 사전 평가 (권고 · 확정은 progress.md §F)

- **tier** M · **scope** 약 10파일(신규 3 + 테스트 3 + 검증 도구 1 `server/tools/lxseq_e2e.py` + fixture 1 — plan-phase 커밋에 선반영 + 수정 2) · **domain** 1(Python 백엔드) · **언어** Python+markdown · **parallel benefit** LOW(M1→M2→M3 데이터 사슬).
- 평가: `direct` 미선택(신규 모듈+툴 배선) · `fanout` 미선택(도메인 1) · `sweep` 미선택(기계 변환 아님) · **`serial` 선택**.
- **Decision: serial** (권고).
- **사용자 접점(Kickoff)**: (§A.4 3건은 2026-08-21 답으로 닫힘) · M4 라이브 세션 일정(사용자 수행 — `server/tools/lxseq_e2e.py`로 정본 CSV를 읽어 핸들러 직접 호출). UI 파일 선택기 → 툴 인자 전달 경로는 **후속 카드 t10으로 위임됨**(§A.4 ① 잔여 메모 — 더는 접점이 아니다).
