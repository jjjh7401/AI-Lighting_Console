# SPEC-COPILOT-FILEARG-001 — 인수 기준 (acceptance)

문서 상태: draft (v0.4.0, 2026-08-23 — 델타 재감사 FAIL 0.62 시정) · Tier M · AC **29건**(오프라인 28 + 앱 실기 1 · 그중 AC-021은 조건부). 본 문서는 spec.md의 요구를 관측 가능한 Given-When-Then 기준으로 전개한다. 요구(GEARS)는 spec.md가 소유하며 여기서 되풀이하지 않는다.

> **참조 규약**: 정본(spec.md · 본 문서)은 줄번호로 인용하지 않고 안정 토큰만 쓴다. `파일:줄`은 코드·타 SPEC 아티팩트에만 쓴다.
>
> **검증 명령 규약**: 아래 명령은 워크트리 루트에서 실행한다. 테스트 파일이 아직 없는 시점에는 그 AC가 미충족이라는 뜻이며, "명령이 없어서 건너뜀"은 PASS가 아니다. 이 저장소에는 테스트 CI가 없으므로(spec.md §C) 각 AC의 증거는 **로컬 실행 출력**이다.

---

## §A. 검증의 축

| 축 | 내용 | 왜 축인가 |
|---|---|---|
| ① 판별의 정직성 | 헤더만으로 정하고, 못 정하면 못 정했다고 말한다 | 잘못 라우팅된 패치 CSV는 잘못된 패치이고, 그것은 무대 사고다 |
| ② 담기만 함 | 업로드는 아무것도 실행하지 않는다 | 대조(sha256)가 가능해지기 전에 움직이면 보루가 무의미해진다 |
| ③ 모델은 바이트를 만지지 않는다 | 래퍼 스키마에 바이트 인자가 없다 | `REQ-LXSEQ-016` 계승 — 채팅 본문이 바이트 출처가 되는 경로를 원리적으로 막는다 |
| ④ 한 줄로 늘어남 | 002/003/004는 표에 행 하나만 더한다 | 이 카드의 값어치는 다음 세 카드에서 회수된다 |

---

## §B. 대표 시나리오 (Given-When-Then)

**시나리오 1 — LX-SEQ 패치 CSV 첨부**: **Given** 앱이 떠 있고 슬롯이 비어 있으며 운영자가 실물 패치 CSV를 고름, **When** 첨부 버튼으로 올리면, **Then** 종류 `patch` · sha256 · byte_length · 행 수 86이 표시되고, 콘솔 접촉과 툴 실행은 0건이며, 슬롯에 바이트가 담겨 있다.

**시나리오 2 — 열 이름이 하나 어긋난 CSV**: **Given** `FixtureType` 열이 `Fixture Type X`로 바뀐 CSV, **When** 올리면, **Then** `unknown_sheet_kind`로 거절되고 읽은 헤더 원문이 함께 표시되며, 슬롯은 이전 상태 그대로다.

**시나리오 3 — 상위 집합 충돌**: **Given** 서명 두 개가 등록된 표(시험용)와 한쪽 서명의 상위 집합인 헤더, **When** 판별하면, **Then** `count == 2`이고 `ambiguous_sheet_kind`로 거절되며 두 종류 이름이 모두 보고된다.

**시나리오 4 — 업로드 없이 래퍼 호출**: **Given** 슬롯이 빈 세션, **When** 모델이 래퍼 툴을 부르면, **Then** `no_uploaded_sheet`로 거절되고 대상 툴은 호출되지 않는다.

**시나리오 5 — 업로드 뒤 미리보기**: **Given** 시나리오 1의 슬롯, **When** 운영자가 미리보기를 시켜 모델이 래퍼 툴을 `action="preview"`로 부르면, **Then** 래퍼가 `file_content_base64`를 주입해 `import_lxseq_patch`를 내부 호출하고, 모델이 받은 인자에는 base64가 없다.

---

## §C. 인수 기준

### §C.0 역추적표

| REQ | 커버 AC | M |
|---|---|---|
| REQ-FILEARG-001 | AC-FILEARG-002 | M1 |
| REQ-FILEARG-002 | AC-FILEARG-003 | M1 |
| REQ-FILEARG-003 | AC-FILEARG-004 | M1 |
| REQ-FILEARG-004 | AC-FILEARG-005 | M1 |
| REQ-FILEARG-005 | AC-FILEARG-002 (별 구간) · AC-FILEARG-009 | M1 · M2 |
| REQ-FILEARG-006 | AC-FILEARG-007 | M2 |
| REQ-FILEARG-007 | AC-FILEARG-006 · AC-FILEARG-019 | M1 |
| REQ-FILEARG-008 | AC-FILEARG-006 (별 구간) · AC-FILEARG-023 | M1 |
| REQ-FILEARG-009 | AC-FILEARG-008 | M2 |
| REQ-FILEARG-010 | AC-FILEARG-009 | M2 |
| REQ-FILEARG-011 | AC-FILEARG-010 · AC-FILEARG-013 | M3 |
| REQ-FILEARG-012 | AC-FILEARG-012 | M3 |
| REQ-FILEARG-013 | AC-FILEARG-011 | M3 |
| REQ-FILEARG-014 | AC-FILEARG-014 · AC-FILEARG-015 | M4 |
| REQ-FILEARG-015 | AC-FILEARG-016 | M4 |
| REQ-FILEARG-016 | AC-FILEARG-018 | M1 |
| REQ-FILEARG-017 | AC-FILEARG-020 | M1 |
| REQ-FILEARG-018 | AC-FILEARG-021 | M1 |
| REQ-FILEARG-019 | AC-FILEARG-022 | M1 |
| REQ-FILEARG-020 | AC-FILEARG-024 | M1 |
| REQ-FILEARG-021 | AC-FILEARG-022 (④⑤ 구간) | M1 |
| REQ-FILEARG-022 | AC-FILEARG-028 | M1 |
| REQ-FILEARG-023 | AC-FILEARG-029 | M1 |

**REQ 23/23 커버, 누락 0.** 역추적표에 없는 AC는 5건이며 의도다 — AC-025~027은 REQ-007의 신원 술어를 여러 축에서 재는 보강 기준이고(정본 커버는 AC-006·AC-019), 나머지 2건은 — **AC-FILEARG-001**(M0 계약 확인 게이트) · **AC-FILEARG-017**(M5 앱 실기 — 형상 전체).

### §C.0a 마일스톤별 AC 배정 (정본)

| M | AC | 수 |
|---|---|---|
| M0 | AC-FILEARG-001 | 1 |
| M1 | AC-FILEARG-002 · 003 · 004 · 005 · 006 · 018 · 019 · 020 · 021 · 022 · 023 · 024 · 025 · 026 · 027 · 028 · 029 | 17 |
| M2 | AC-FILEARG-007 · 008 · 009 | 3 |
| M3 | AC-FILEARG-010 · 011 · 012 · 013 | 4 |
| M4 | AC-FILEARG-014 · 015 · 016 | 3 |
| M5 | AC-FILEARG-017 | 1 |

합 **29 · 중복 0 · 누락 0**.

### AC-FILEARG-001 — M0 계약 대조 게이트

**Given** 착수 시점 트리, **When** `research.md` §2의 좌표를 토큰 앵커로 대조하면, **Then** 다음 다섯이 모두 확인되고 드리프트가 `progress.md`에 기록된다.

① `vectorworks_autopatch` 핸들러가 세션 업로드 바이트를 `file_content_base64` 인자로 실어 형제 툴을 부르는 두 줄이 실재한다.
② `import_lxseq_patch`의 `required`가 `["file_content_base64"]`이고 경로 인자가 없다.
③ `_UploadedVectorworksExport`가 실재하고 교체·초기화 규약을 갖는다.
④ `_TOOL_TASKS`가 `server/orchestrator/runner.py`에 실재하고, `server/tests/test_runner_progress.py`가 등록 툴 이름과의 전단사를 단언한다.
⑤ `server/tests/test_tools.py`의 닫힌 집합 상수가 착수 시점 툴 수와 같다.
⑥ `progress.md`의 "M0 — Kickoff 결정 기록"에 결정 **I**(서명 미일치 CSV의 처분)와 결정 **J**(형식을 넓히고 행은 넓히지 않는다)의 답이 적혀 있고, 그 표에 `미정`이 **남아 있지 않다**(남아 있으면 **명시적 FAIL** — 건너뛰기 아님).

**검증**: `grep -n "vectorworks_upload.content_base64" server/orchestrator/tools.py` · `grep -n "_TOOL_TASKS" server/orchestrator/runner.py server/tests/test_runner_progress.py` · `grep -n "len(TOOL_NAMES)" server/tests/test_tools.py` · `grep -n "Kickoff 결정 기록" .moai/specs/SPEC-COPILOT-FILEARG-001/progress.md` — 넷 모두 비어 있지 않을 것. 아울러 `grep -c "미정" .moai/specs/SPEC-COPILOT-FILEARG-001/progress.md`의 결과가 Kickoff 결정 기록 표에 대해 **0**일 것.

### AC-FILEARG-002 — 포함 검사 술어 (REQ-FILEARG-001 · REQ-FILEARG-005 별 구간)

**Given** `patch` 서명과 실물 LX-SEQ 패치 CSV 헤더, **When** 술어를 적용하면, **Then** ① 정규 9열이 모두 있으면 일치 · ② 정규 열 밖의 열이 더 있어도 여전히 일치(관용) · ③ 열 순서가 뒤바뀌어도 일치 · ④ 대소문자·앞뒤 공백·BOM이 달라도 일치 · ⑤ 정규 열 하나가 빠지면 불일치 · ⑥ 술어 실행 중 `MissingColumnsError`가 발생하지 않는다(예외를 제어 흐름으로 쓰지 않음).

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "signature"`

### AC-FILEARG-003 — 전수 계수 · 조기 반환 금지 (REQ-FILEARG-002)

**Given** 시험용으로 서명 두 개를 주입한 표(등록 행 수와 무관하게 판별기에 표를 넘긴다)와 한쪽의 상위 집합인 헤더, **When** 판별하면, **Then** `matched`에 두 종류가 **모두** 있고 `count == 2`이다. 판별기를 첫 일치 반환으로 바꾸면 이 테스트가 죽는다(뮤테이션으로 확인하고 결과를 `progress.md`에 적는다).

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "superset or count"`

### AC-FILEARG-004 — 0건 거절 (REQ-FILEARG-003)

**Given** 어느 서명과도 맞지 않는 헤더, **When** 판별하면, **Then** `outcome == "unknown_sheet_kind"`이고, 결과에 읽은 헤더 원문 전체와 등록된 종류별 서명 목록이 실려 있으며, `matched`는 비어 있다. **가장 비슷한 종류를 고르는 분기는 코드에 존재하지 않는다**(유사도·부분 일치 점수 계산 0건).

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "unknown"` · `grep -rn "difflib\|SequenceMatcher\|closest\|best_match" server/sheets/` — 두 번째 명령은 **빈 출력**이어야 한다.

### AC-FILEARG-005 — 2건 이상 거절 (REQ-FILEARG-004)

**Given** AC-003의 상위 집합 헤더, **When** 판별하면, **Then** `outcome == "ambiguous_sheet_kind"`이고 일치한 종류 이름이 **전부** 보고되며, 그중 하나를 고르는 경로가 없다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "ambiguous"`

### AC-FILEARG-006 — 레지스트리 표 (REQ-FILEARG-007 · REQ-FILEARG-008)

**Given** 레지스트리, **When** 표를 읽으면, **Then** ① 채워진 행이 **정확히 둘**(`patch` · `vectorworks`)이고 그 밖의 종류 행은 **없다**(결정 I) · ② 각 행이 드는 것은 열 목록이 아니라 **판별 술어**다(결정 K) — `patch`는 **열 집합 술어**이고 그 정본은 `server/lxseq/parser.py`의 `CANONICAL_COLUMNS`를 **참조**하며 사본이 아니다(참조 동일성 단언) · ③ `vectorworks`는 **위임 술어**이며 `server/vwx/reader.py`의 판정을 **호출**한다 — 판정 논리를 이 모듈에 옮겨 적지 않았고(사본 0건), `columns.py`를 서명 정본으로 삼지 않는다(v0.2.0의 오귀속 교정) · ④ 두 행의 대상이 각각 등록된 툴 집합 / 기존 세션 업로드 경로로 실제 해소된다 · ⑤ 표에 없는 종류 이름은 판별에서 `unknown_sheet_kind`로 떨어지고 통과하는 경로가 없다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "registry"`

### AC-FILEARG-007 — 세션 슬롯 (REQ-FILEARG-006)

**Given** 세션, **When** 판별에 성공한 업로드를 처리하면, **Then** ① 슬롯에 `content_base64`·`sha256`·`byte_length`·`kind`·`file_name`·`received_at`이 담긴다 · ② `sha256`이 원본 바이트의 해시와 같다 · ③ 두 번째 업로드가 첫 번째를 **교체**한다(슬롯은 하나) · ④ 세션 초기화 시 슬롯이 비워진다 · ⑤ 판별 실패 시 슬롯은 **직전 상태 그대로**다.

**검증**: `uv run pytest server/tests/test_sheet_upload_session.py -q -k "slot"`

### AC-FILEARG-008 — 저장 전용, 자동 실행 0건 (REQ-FILEARG-009)

**Given** 세션과 유효한 패치 CSV, **When** 업로드 프레임을 처리하면, **Then** ① `run_instruction`이 호출되지 않는다(호출 계수 0) · ② 래퍼 툴·대상 툴 핸들러가 호출되지 않는다 · ③ 콘솔 접촉이 0이다(`server.bridge`·`pythonosc`·`execution_port`·`deploy_pipeline`·`run_commands` 호출 0). 핸들러에 `run_instruction` 호출을 한 줄 넣으면 이 테스트가 죽어야 한다(뮤테이션 확인).

**검증**: `uv run pytest server/tests/test_sheet_upload_session.py -q -k "store_only or no_auto"` · `grep -n "run_instruction" server/web/session.py` 결과에 신규 시트 업로드 핸들러의 줄이 **포함되지 않을 것**(기존 Vectorworks 핸들러의 줄만 남는다).

### AC-FILEARG-009 — 업로드 직후 넷 보고 (REQ-FILEARG-010 · REQ-FILEARG-005)

**Given** 실물 패치 CSV, **When** 업로드가 성공하면, **Then** ① 응답에 `kind`·`sha256`·`byte_length`·`rows_total`이 있고 `rows_total == 86`이다 · ② `parsed`·`rejected` 건수가 함께 있다 · ③ 실제 파싱은 **한 번만** 돈다(파서 진입점 호출 계수 1) · ④ 응답에 점유 판정·타입 해석·"패치 가능" 류의 문구가 없다 · ⑤ 응답 문자열은 한국어다.

**검증**: `uv run pytest server/tests/test_sheet_upload_session.py -q -k "report"`

### AC-FILEARG-010 — 래퍼가 바이트를 주입한다 (REQ-FILEARG-011)

**Given** `patch` 종류가 담긴 슬롯, **When** 래퍼 툴을 `action="preview"`로 부르면, **Then** ① 대상 툴 `import_lxseq_patch` 핸들러가 내부 `ToolCall`로 정확히 한 번 호출된다 · ② 그 호출의 `arguments`에 `file_content_base64`가 슬롯의 바이트와 **동일하게** 실려 있다 · ③ 화이트리스트 인자(`action` 등)가 그대로 전달된다 · ④ 화이트리스트 밖 인자를 주면 전달되지 않고 거절 사유로 보고된다 · ⑤ 대상 툴의 결과가 가공 없이 올라온다.

**검증**: `uv run pytest server/tests/test_sheet_wrapper_tool.py -q -k "inject"`

### AC-FILEARG-011 — 거절 3종 (REQ-FILEARG-013)

**Given** 각각 ① 빈 슬롯 ② 요청과 다른 종류가 담긴 슬롯 ③ 대상 툴 이름이 등록 툴 집합에 없는 표, **When** 래퍼 툴을 부르면, **Then** 각각 `no_uploaded_sheet` · `kind_mismatch` · `no_target_tool`로 거절되고, **어느 경우에도 대상 툴이 호출되지 않으며**, 직전 업로드를 재사용하거나 다른 종류의 툴로 대신 보내는 경로가 없다. 사유 문자열은 닫힌 집합 밖의 값을 낼 수 없다.

**검증**: `uv run pytest server/tests/test_sheet_wrapper_tool.py -q -k "refuse"`

### AC-FILEARG-012 — 래퍼 스키마에 바이트·경로 인자가 없다 (REQ-FILEARG-012)

**Given** 등록된 툴 정의 집합, **When** 래퍼 툴의 입력 스키마를 읽으면, **Then** ① `properties`에 `file_content_base64`가 **없다** · ② `required`에도 없다 · ③ 파일 시스템 경로를 뜻하는 인자(`file_path`·`path`·`filename` 류)가 없다 · ④ 스키마에 `file_content_base64`를 추가하면 이 테스트가 죽는다(뮤테이션 확인 필수 — 이 AC의 비공허성 증명이다).

**검증**: `uv run pytest server/tests/test_sheet_wrapper_tool.py -q -k "schema"`

### AC-FILEARG-013 — 6지점 등재 (REQ-FILEARG-011 별 구간)

**용어 고정(감사 D1).** "6지점"은 **편집 지점 6곳**을 뜻하며 그 정본은 `research.md` §6이다. 가드는 지점이 아니다 — `test_runner_progress.py`는 **누락을 검출하는 가드**이지 편집 지점이 아니므로 아래 열거에서 지점으로 세지 않는다.

**Given** 착수 후 트리, **When** 등재를 확인하면, **Then** 편집 지점 **6곳**이 모두 채워져 있다 — ① `TOOL_NAMES`에 래퍼 이름 · ② **핸들러 클로저**(v0.2.0 열거에서 빠져 있었다 — 감사 D1) · ③ `ToolDefinition` · ④ `handlers` 맵 · ⑤ `server/orchestrator/runner.py`의 `_TOOL_TASKS` · ⑥ `server/tests/test_tools.py`의 닫힌 집합 상수 35.

**가드 확인(지점 아님)**: `server/tests/test_runner_progress.py`의 전단사 단언이 통과한다. `_TOOL_TASKS` 등재(⑤)를 빼면 이 가드가 죽어야 한다 — 6지점 중 가장 자주 빠지는 자리이므로 뮤테이션으로 확인한다.

**검증**: `uv run pytest server/tests/test_tools.py server/tests/test_runner_progress.py -q`

### AC-FILEARG-014 — UI 라우팅 (REQ-FILEARG-014)

**Given** 첨부 버튼 하나, **When** ① 이미지 MIME 파일을 고르면 **Then** 레이아웃 이미지 경로가 불리고(무변경 보증), **When** ② 비이미지 파일을 고르면 **Then** **신규 시트 업로드 프레임**이 나가며 옛 Vectorworks 송신 함수는 호출되지 않는다(단, plan.md §A.4 ①이 (가)안으로 닫힌 경우 서버 폴백이 그 역할을 하며 UI 단언은 그대로다 — UI는 어느 안에서도 목적지를 고르지 않는다). ③ 비어 있거나 8 MiB를 넘는 파일은 기존과 같은 문구로 UI가 먼저 막는다.

**검증**: `npm --prefix ui run test -- --run App` · `npm --prefix ui run test -- --run protocol`

### AC-FILEARG-015 — UI는 두 번째 검증 계층이 아니다 (REQ-FILEARG-014 별 구간 · plan 결정 A)

**Given** `ui/src/`, **When** 훑으면, **Then** ① 정규 열 이름(`FixtureType`·`AddrRange` 등)이 UI 소스에 등장하지 않는다 · ② CSV 헤더를 파싱하는 코드가 없다 · ③ `<input accept>` 목록이 착수 시점과 **같다**(넓히지 않았다) · ④ 2026-08-15 운영자 결정 주석이 남아 있고, 종류를 무엇으로 읽는지가 바뀐 사실이 한 줄로 갱신돼 있다.

**검증**: `grep -rn "FixtureType\|AddrRange\|CANONICAL" ui/src/` — **빈 출력**이어야 한다. `grep -n "accept=" ui/src/App.tsx` — 착수 시점 값과 동일할 것. `grep -n "2026-08-15" ui/src/App.tsx` — 비어 있지 않을 것.

### AC-FILEARG-016 — PRESERVE (REQ-FILEARG-015)

**Given** 착수 SHA `6296af3`와 현재 HEAD, **When** 보존 대상 경로의 변경 통계를 내면, **Then** **빈 출력**이다. 아울러 `import_lxseq_patch`의 스키마 `required`·`properties` 키 집합과 설명문이 착수 시점과 **바이트 동일**하다.

**검증**:

```
git diff --stat 6296af3..HEAD -- server/lxseq server/vwx server/prechk server/safety server/paperwork console/lua server/rulebook/assets
```

빈 출력일 것. 결정 F의 공개 별칭 한 줄을 실제로 추가했다면 `server/lxseq` 항목만 예외로 허용하되 그 한 줄임을 `progress.md`에 적고 `git diff` 본문을 인용한다(예외를 조용히 넘기지 않는다).

### AC-FILEARG-017 — 앱으로 실제 넣어 본다 (M5 · 사용자 수행 · 형상 전체)

**Given** 앱이 떠 있고 운영자가 실물 LX-SEQ 패치 CSV를 가지고 있음, **When** 첨부 버튼으로 그 파일을 고르면, **Then** ① 종류 `patch`가 표시된다 · ② 표시된 sha256이 운영자가 로컬에서 잰 값과 **일치한다** · ③ 표시된 행 수가 86이다 · ④ 아무 툴도 자동 실행되지 않았다(채팅에 실행 흔적 0) · ⑤ 그 뒤 미리보기를 시키면 래퍼 툴이 대상 툴을 부르고 결과가 올라온다.

**미통과 시**: 이 AC가 실패하면 M5는 PASS로 닫히지 않으며, SPEC은 `implemented`에서 멈추고 `completed`가 되지 않는다(§D). onPC가 없어 ⑤의 콘솔 판독이 불가능하면 그 부분만 미검증으로 적고, ①~④는 그대로 판정한다 — **"검증 못 했음"을 "통과"로 적지 않는다**.

**검증**: 운영자 관측. 증거는 `progress.md`에 화면 인용과 로컬 sha256 값으로 남긴다.

---
### AC-FILEARG-018 — [HARD] 확장 형식이 프리셋 4종을 실제로 가른다 (REQ-FILEARG-016 · 결정 J)

형식을 넓혀 놓고 "003에서는 괜찮을 것"이라고 적으면 문제를 푼 것이 아니라 미룬 것이다. 이 AC는 넓힌 형식이 **실제로 충분한지**를 증명한다.

**Given** `research.md` §9 (c)가 인용한 실물 헤더로 만든 **합성 서명 픽스처** 넷(`preset-dim` `ID,Name,Level,Purpose` · `preset-col` `ID,Name,Value,Purpose` · `preset-bm` `ID,Name,TargetGroup,Value` · `preset-pos` `ID,StageMeaning,TargetGroup,RecordGuide`) — **레지스트리 행이 아니라 판별기에 주입한 표**다(AC-FILEARG-003과 같은 기법), **When** 확장 형식으로 넷의 서명을 쓰고 넷의 헤더를 각각 판별하면, **Then** ① 헤더 넷이 각각 **자기 종류 하나에만** 맞는다(`count == 1` × 4) · ② 어느 헤더도 `ambiguous_sheet_kind`로 떨어지지 않는다.

**비공허성(필수)**: 같은 헤더 넷을 **포함 검사만으로** 쓴 서명으로 다시 돌리면 **반드시 실패해야 한다** — 구체적으로 `preset-col` 서명을 포함 검사 `{ID, Name, Value}`로 두면 `preset-bm` 헤더가 두 서명에 맞아 `count == 2`가 되어야 한다. 이 대조군이 통과해 버리면 시험이 형식의 힘을 재고 있지 않다는 뜻이므로 AC는 미충족이다.

**[HARD] 범위 봉쇄**: 이 AC는 **합성 서명 픽스처만** 쓴다. 프리셋 종류의 레지스트리 행·파서·핸들러를 만들면 REQ-FILEARG-017 위반이며 `AC-FILEARG-020`이 그것을 잡는다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "format_sufficiency"`

### AC-FILEARG-019 — 실물 교차 분류 (REQ-FILEARG-007 · 결정 I)

**Given** `server/tests/fixtures/`의 실물 표본 — 대상은 `vwx/` **디렉터리 전량**이며 `.mvr`을 포함한다(12개 항목 중 업로드 페이로드 **10개**: `.csv` 8 · `.txt` 1 · `.mvr` 1; `README.md`와 `stage1_contract_snapshot.json`은 페이로드가 아니다), **When** 각각을 판별하면, **Then** ① `lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` → `patch` 단일 일치이며 `vectorworks`에 **맞지 않는다**(`AC-FILEARG-025`가 소유) · ② `vwx/vectorworks_export_sample_with_data.csv` → `vectorworks` 단일 일치 · ③ `vwx/drop_dk_rigging_not_a_vectorworks_export.csv` → `unknown_sheet_kind`(`AC-FILEARG-026`) · ④ `vwx/vectorworks_export_instrument_data_no_header.txt` → **`unknown_sheet_kind`**(문구는 조건부 힌트로 보존 — `AC-FILEARG-029`) · ⑤ 페이로드 10개 전량에 대해 **신원 술어**의 적중/불발을 표로 기록한다.

**v0.4.0 개정 — 판정 축이 바뀌었다.** v0.3.0의 이 표는 **사용성 술어**(`has_address_family`)로 시뮬레이션한 값이라 **무효다**. 신원 축(`_best_header_candidate >= 0`)으로 다시 계산해야 하며, 그 결과 헤더 없는 `.txt` 한 칸이 `vectorworks` → `unknown_sheet_kind`로 **옮겨간다** — 결정 L의 의도된 결과이지 결함이 아니다. 재계산된 표와 그 근거는 `research.md` §11이 소유한다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "cross_classify"` · 표는 `progress.md` M1 절에 남긴다.

### AC-FILEARG-020 — 레지스트리는 이 카드에서 늘지 않는다 (REQ-FILEARG-017)

**Given** 착수 후 트리, **When** `server/sheets/`를 훑으면, **Then** 프리셋 4종·`group`·`fx`·`cue-ex`의 **서명도 행도 파서도 핸들러도 없다**. 등록 행은 `patch`와 `vectorworks` 둘뿐이다.

**검증**: `grep -rn "preset-dim\|preset-col\|preset-bm\|preset-pos\|cue-ex" server/sheets/` — **빈 출력**이어야 한다(합성 픽스처는 `server/tests/`에 있으므로 이 grep에 걸리지 않는다). 아울러 `uv run pytest server/tests/test_sheets_registry.py -q -k "registry"`의 ① 항(행 정확히 둘)이 통과할 것.

**grep의 한계를 기록한다(감사 F4).** 위 grep 패턴은 프리셋 4종과 `cue-ex`만 훑고 **`group`과 `fx`는 빠져 있다** — Then 절이 그 둘을 포함하는데 검증 명령이 그것을 재지 않는다. 보완하는 것은 같은 AC의 **행 수 단언**(등록 행이 정확히 둘)이다: `group`이나 `fx` 행이 생기면 행 수가 셋이 되어 그 단언이 죽는다. 그러므로 이 AC는 여전히 비공허하지만, **grep 하나만으로 통과를 주장하지 않는다** — 두 검사가 함께여야 Then 절 전체를 덮는다.

### AC-FILEARG-021 — 안전판을 타면 선언되고 고지된다 (REQ-FILEARG-018 · 조건부)

**조건부 AC.** `AC-FILEARG-019` ④가 "위임 술어가 실물 변형을 전부 흡수한다"로 나오면 이 AC는 **발동하지 않으며**, 그 사실을 명령·출력과 함께 `progress.md`에 **N/A로 명시 기록**한다 — 판정하지 않은 것을 통과로 적지 않는다.

> **분할 교정(감사 B5).** v0.2.0은 "판별기에 암묵적 `else`가 없다"를 이 조건부 AC 안에 두었다. 그것은 **폴백이 발화하지 않는 동안 아무도 확인하지 않는다**는 뜻이었다. 그 절은 `AC-FILEARG-024`로 **분리했고 무조건 검사**한다. 여기 남는 것은 폴백이 실제로 발동했을 때만 성립할 수 있는 두 가지다.

**Given** M1이 위임 술어로 실물 변형을 흡수할 수 없다고 실측한 경우, **When** 폴백을 구현하면, **Then** ① 폴백이 **레지스트리 항목으로 선언**돼 있다 — 표에 그 행이 있고, 판별 결과가 그 행의 술어에서 나온다 · ② 그 경로로 흐른 파일에 대해 UI가 **"Vectorworks export로 읽는 중"임을 소리 내어 말한다**(문구가 화면에 있다) · ③ `plan.md` §D.1의 안전판 문단이 **`발동함`으로 갱신**돼 있고 "`unknown_sheet_kind` 거절 규칙에 살아 있는 경로가 없어졌다"가 적혀 있다.

**③의 검증 토큰(감사 B5 교정)**: `grep -n "발동함" .moai/specs/SPEC-COPILOT-FILEARG-001/plan.md`. v0.2.0은 §D.1에 **이미 있는** 문장을 grep해 **오늘도 통과하는** 검사를 걸어 두었다 — 기능 코드가 한 줄도 없는 SPEC에서 통과하는 검사는 검사가 아니다. `발동함`은 폴백이 실제로 발동해 문단을 갱신했을 때만 나타나므로 **판별력이 있다**. 이 AC가 N/A일 때 이 grep은 **빈 출력이어야 하며**, 빈 출력이 곧 N/A의 증거다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "declared_fallback"` · `npm --prefix ui run test -- --run App` · 위 `발동함` grep.

### AC-FILEARG-022 — 실물 `.mvr`이 Vectorworks로 간다 (REQ-FILEARG-019 · 감사 B1)

이 AC가 없으면 SPEC은 `.mvr`·`.xlsx`의 처분에 대해 **한 줄도 말하지 않는 상태**로 남는다. 그것이 B1이 들어온 경로였다.

**Given** 실물 `server/tests/fixtures/vwx/demoshow_grandma3.mvr`(ZIP 아카이브, **315,155 바이트** — `wc -c` 실측), **When** 판별기에 그 바이트를 넣으면, **Then** ① 결과가 `unknown_sheet_kind`가 **아니다** · ② `vectorworks` 단일 일치이며 대상이 기존 세션 업로드 경로로 해소된다 · ③ 판별 과정에서 그 바이트를 CSV 텍스트로 해석하려는 시도가 없다 · ④ **`.mvr` 판정의 소유자를 정확히 부른다** — `server/vwx/reader.py`가 아니라 `server/orchestrator/tools.py:2859-2860`(`is_mvr = SCENE_ENTRY in archive.namelist()`)와 `server/vwx/mvr.py`다(`grep -c "mvr\|MVR" server/vwx/reader.py` → **0**) · ⑤ `openpyxl` **두 경로 모두** 닫혀 있다 — 설치 시 `KeyError: '[Content_Types].xml'`도, 미설치 시 `unapproved_dependency` 안내도 나오지 않는다(후자가 더 나쁘다: `.mvr`은 xlsx가 아니므로 설치해도 고쳐지지 않는데 운영자를 쓸모없는 곳으로 보낸다).

**v0.4.0 개정 — 헤더 없는 `.txt`는 여기서 빠진다.** v0.3.0의 ④는 `vectorworks_export_instrument_data_no_header.txt`도 `vectorworks`에 도달한다고 단언했다. 결정 L 이후 그 파일은 **`unknown_sheet_kind`가 정답이다**(신원 술어 `_best_header_candidate` → `-1`). 그것은 결함이 아니라 **의도된 결과**이며, 잃는 문구는 `AC-FILEARG-029`가 조건부 힌트로 보존한다.

**뮤테이션 ① — 지금은 세지 않는다(F3).** `vectorworks` 술어를 열 집합 술어로 되돌리는 뮤테이션은 F1(위임 계약 · `.mvr` 소유자)이 열려 있는 동안 **판별력이 없다** — 그 단언은 뮤테이션 없이도 이미 빨갛기 때문이다. F1이 닫히고 이 AC가 **뮤테이션 없이 초록**이 된 뒤 재점화하며, 그때 **두 상태를 모두** 기록한다. 그 전까지 §D 원장에서 제외한다.
**비공허성**: `vectorworks` 행의 술어를 열 집합 술어로 바꿔 놓으면 ①과 ④가 **반드시 죽어야 한다**(그것이 v0.2.0의 상태였다). 뮤테이션으로 확인하고 `progress.md`에 적는다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "mvr or headerless"`

### AC-FILEARG-023 — 대상이 없는 행은 판별 시점에 후보에서 빠진다 (REQ-FILEARG-008 · 감사 B4)

**Given** 레지스트리에 대상 툴 이름이 등록 툴 집합에 **없는** 행을 주입한 표, **When** 아무 바이트나 판별하면, **Then** ① 그 행은 **판별 시점에** 후보에서 제외된다 — 일치 계수에 들어가지 않는다 · ② 제외 사실이 **오류로 보고**된다(조용한 무시가 아니다) · ③ 그 오류가 판별 결과에 실려 올라와, 나중에 래퍼 툴이 `no_target_tool`로 발견하기 **전에** 드러난다 · ④ 정상 행들의 판별은 그 오류와 무관하게 그대로 진행된다.

**왜 판별 시점인가**: 대상 부재를 실행 시점에 발견하면 운영자는 파일을 올리고, 기다리고, 시켜 본 뒤에야 안다. 판별 시점에 걸면 업로드 응답에서 바로 안다. `AC-FILEARG-011`의 `no_target_tool`은 **래퍼 호출 시점**의 방어이고 이 AC는 **판별 시점**의 방어다 — 둘은 다른 지점이며 서로를 대신하지 않는다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "missing_target"`

### AC-FILEARG-024 — 판별기에 암묵적 `else`가 없다 (REQ-FILEARG-020 · 무조건)

**Given** 착수 후 트리, **When** 판별 경로를 훑으면, **Then** ① 어떤 바이트가 어느 종류로 가는지가 **선언된 술어의 결과로만** 정해진다 · ② 표 어디에도 없는 경로로 흘러가는 분기가 없다 · ③ 술어가 전부 거짓이면 결과는 `unknown_sheet_kind` 하나뿐이며, 그것은 암묵적 `else`가 아니라 **REQ-FILEARG-003이 선언한 결과**다.

**이 AC는 조건과 무관하게 언제나 검사한다.** 안전판(`AC-FILEARG-021`)이 발동하든 하지 않든 같다 — 조건부 안에 두면 폴백이 없는 동안 아무도 보지 않는다(감사 B5).

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "no_implicit_else"`. 아울러 판별 함수 본문에 남은 `else`가 있으면 그것이 **선언된 술어의 결과 분기**임을 `progress.md`에 근거와 함께 밝힌다(있다/없다를 세는 grep은 근거가 되지 못하므로 테스트가 정본이다).


### AC-FILEARG-025 — 패치 CSV는 자기 종류로만 간다 (REQ-FILEARG-007 · ASSUMPTION-75-b · F2)

**Given** 실물 `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv`, **When** 판별하면, **Then** `count == 1`이고 종류는 `patch`다 — `vectorworks`에는 **맞지 않는다**.

**확장 뮤테이션(필수)**: `vectorworks` 술어에서 **배제 절**(`AND NOT 다른 행 서명 일치`)을 빼면 이 AC가 **빨개져야 한다**. 배제 절이 없으면 패치 CSV는 헤더가 찾아지므로 신원 술어를 만족해 `count == 2`가 되고 `ambiguous_sheet_kind`로 떨어진다. 이 뮤테이션이 통과하면 배제 절이 아무것도 지키지 않는다는 뜻이다.

**이 AC가 `ASSUMPTION-75-b`를 소유한다.** v0.2.0은 75를 "VW 헤더 → patch 서명" **한 방향만** 재고 닫았고, 묻지 않은 반대 방향이 F2를 통과시켰다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "patch_identity"`

### AC-FILEARG-026 — 음성 대조군은 거절된다 (REQ-FILEARG-003 · 좁히기 대조군)

**Given** `server/tests/fixtures/vwx/drop_dk_rigging_not_a_vectorworks_export.csv`(**이미 있는** 음성 대조군, 새로 만들지 않는다), **When** 판별하면, **Then** `unknown_sheet_kind`다 — 신원 술어가 헤더를 찾지 못하거나 임계에 못 미쳐 `vectorworks`가 되지 않는다.

**왜 필요한가**: AC-025가 "너무 넓지 않은가"를 재는 반면 이 AC는 **"너무 좁히다 아무거나 받지는 않는가"**의 반대편을 고정한다. 둘이 같이 있어야 술어가 한쪽으로 무너지는 것을 잡는다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "negative_control"`

### AC-FILEARG-027 — 별칭 임계 2가 고정된다 (REQ-FILEARG-007 · 신원 술어의 민감도)

**Given** `server/vwx/reader.py:43`의 `_MIN_HEADER_ALIAS_MATCHES = 2`, **When** 판별기가 신원 술어를 부르면, **Then** 그 임계가 유효하게 작동한다 — 별칭이 1개만 맞는 헤더는 `vectorworks`가 되지 않는다.

**뮤테이션**: 임계를 **1로 낮추면** 무관한 대조군 하나가 `vectorworks`로 새어 들어와 이 AC가 **빨개져야 한다**.

**[HARD] 이 AC가 덮지 못하는 것을 함께 적는다.** 이 임계는 **균일폭 폴백 구멍을 막지 못한다** — `_process_rows`(`reader.py:253-266`)의 탭·균일폭 폴백은 임계를 **통과하는 것이 아니라 우회한다**(헤더 탐색 실패 후 `col_0..`를 지어낸다). 그 구멍은 `AC-FILEARG-028`이 따로 막는다. 임계 고정만으로 "새는 곳이 없다"고 적으면 그것이 곧 이번 라운드에서 잡힌 종류의 착각이다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "alias_threshold"`

### AC-FILEARG-028 — 날조 대조군을 **두 축**으로 쏜다 (REQ-FILEARG-022 · 균일폭 폴백 구멍)

**Given** VW와 무관한 날조 입력 **두 가지** — **탭 축**은 아래 바이트를 그대로 픽스처로 쓴다:

```
milk	2	3000
eggs	1	5000
bread	3	2500
```

**쉼표 축**은 같은 내용을 쉼표로 구분한 변형이다. **When** 각각을 판별하면, **Then** **둘 다 `vectorworks`가 아니다**(`unknown_sheet_kind`).

**왜 두 축인가 — 한 축만 세운 대조군이 이번 결함을 통과시켰다.** 앞선 라운드의 대조군은 **쉼표 전용**이었고, 그래서 대조군 전체가 초록인 채로 **탭 축이 활짝 열려 있었다**: 위 장바구니 바이트는 느슨한 술어에서 `header 비어 있음 = False · records = 3 · path_kind = A · failures = []`로 **Vectorworks가 됐다**. 대조군을 한 축으로만 세우면 그 축 밖은 전혀 재지 않는다 — 이 한 문장이 이 AC의 존재 이유다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "fabricated_control"`

### AC-FILEARG-029 — 재수출 안내 문구가 보존된다 (REQ-FILEARG-023 · 좁히기로 잃는 유일한 것)

**Given** 헤더 행이 없는 균일폭 입력(실물 `vwx/vectorworks_export_instrument_data_no_header.txt` 및 AC-028의 탭 날조 대조군), **When** 판별이 `unknown_sheet_kind`로 끝나면, **Then** ① 재수출 힌트가 함께 나온다 — "헤더 행이 없는 균일폭 표로 보인다. **Vectorworks에서 내보낸 것이라면** 'Export field names as first record'를 켜고 다시 내보내라." · ② 그 문구에 **조건절이 있다**(무조건 단정이 아니다) · ③ 힌트가 나와도 분류는 여전히 `unknown_sheet_kind`이며 `vectorworks`로 바뀌지 않는다 — 힌트는 **형상 관측**이지 신원 주장이 아니다.

**뮤테이션(필수)**: 힌트를 **제거하면** 이 AC가 **빨개져야 한다**. 좁히기로 잃는 것은 능력이 아니라 이 문구 하나뿐이므로, 그 하나를 잃지 않았음을 기계로 지킨다.

**검증**: `uv run pytest server/tests/test_sheets_registry.py -q -k "reexport_hint"`

## §D. Definition of Done

1. AC 29건 중 **오프라인 28건 전부 PASS**(`AC-FILEARG-021`은 조건부 — 발동하지 않으면 N/A로 명시 기록하고 PASS로 세지 않는다. `AC-FILEARG-024`는 조건부가 아니며 **언제나** 판정한다).
2. 전체 스위트 2종(`uv run pytest server/tests -q` · `npm --prefix ui run test`)이 착수 기준선 대비 **감소 0 · 신규 실패 0**. 착수 시점의 기존 실패(`test_pipeline_out_paths.py` / t20 귀속)는 **이 SPEC의 델타가 아니며 여기서 고치지 않는다** — 원인별로 나눠 적는다(plan.md M0).
3. plan.md §A.4의 열린 결정 마커가 **0건**이고, 결정 I·J·K·L의 답이 `progress.md`에 기록돼 있다.
4. **뮤테이션 원장 — 5건**(F3으로 6→5). AC-003 조기 반환 · AC-006 서명 사본 · AC-012 스키마 추가 · AC-013 `_TOOL_TASKS` 누락 · AC-018 포함 검사 대조군. 각각 해당 테스트를 죽이는 것을 실측하고 `progress.md`에 적었다.
   - **AC-022 뮤테이션 ①은 지금 세지 않는다(F3).** F1(위임 계약 · `.mvr` 소유자)이 열려 있는 동안 그 단언은 **뮤테이션을 걸지 않아도 이미 빨갛다** — 이미 빨간 단언에 뮤테이션을 걸어 빨간 것을 확인하는 일에는 **판별력이 없다**. F1이 닫히고 ①이 **뮤테이션 없이 초록**이 된 뒤에 재점화하며, 그때 **두 상태(뮤테이션 전 초록 · 뮤테이션 후 빨강)를 모두** 기록한다. 그 시점에 원장은 6건이 된다.
   - v0.4.0에서 새로 선 뮤테이션 4건(AC-025 배제 절 제거 · AC-027 임계 1로 하향 · AC-029 힌트 제거 · AC-022 ① 재점화 예정)은 각각 해당 AC가 소유하며, 위 원장은 **이미 판별력이 확인된 것만** 센다.
5. AC-FILEARG-017(앱 실기)이 PASS면 `completed`, 미수행·부분 수행이면 `implemented`에서 멈추고 잔여를 카드로 남긴다.
6. **감사가 강점으로 지목한 것은 손대지 않았다** — 결정 ① 계수 요구의 5중 고정 · `AC-FILEARG-003`의 **주입 표** 기법 · 좌표 인용 · `addr_range_mismatch` 오인용 봉쇄. 이 넷 중 하나라도 약해졌으면 시정이 아니라 퇴행이다. 결정 L의 배제 절도 계수를 없애지 않는다 — 술어를 배타적으로 만들 뿐이다.
