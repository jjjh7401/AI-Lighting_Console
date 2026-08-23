# SPEC-COPILOT-SHEETPIPE-001 — 인수 기준 (acceptance)

문서 상태: draft (v0.2.0, 2026-08-23 — `AC-SHEETPIPE-005` 조건절 제거: 전제 성립 확인) · **Tier M · 통과 임계 0.80** · 칸반 카드 t10 · **분할 B(전달경로)**

## §A. 검증의 축 (분할 B)

B가 지는 물음은 하나다 — **"판별된 바이트가 실제로 툴 인자까지 도달하는가, 그리고 도달하기 전에는 아무 일도 일어나지 않는가."** 그래서 검증은 네 축으로 나뉜다:

1. **담김** — 슬롯이 넷을 제대로 들고, **툴이 그것을 본다**(`002` · `003`).
2. **안 함** — 시트 경로에서 실행이 0회이고, 그 금지가 **오늘 살아 있는 Vectorworks 동작을 회수하지 않는다**(`004` · `005`).
3. **보임** — 운영자가 넷을 보고, 행 수가 **어느 통을 센 수인지** 안다(`006`).
4. **나름** — 래퍼가 바이트를 주입하고, 스키마에는 바이트 인자가 없고, 못 나를 때는 **이름 붙은 사유**를 낸다(`007` · `008` · `009` · `010`).

여기에 경계(`011`)와 착수 게이트(`001`)가 붙는다.

**축 2가 특히 미묘하다.** "아무것도 실행하지 않는다"를 넓게 읽으면 `005`가 빨개지고, 좁게 읽으면 `004`가 빨개진다. 두 기준이 **서로를 잡도록** 짝지어 둔 것이 의도다.

## §B. 대표 시나리오 (Given-When-Then)

**시나리오 1 — 패치 CSV를 올리고, 아무 일도 일어나지 않고, 나중에 시킨다.**
**Given** 운영자가 첨부 버튼으로 LX-SEQ 패치 CSV를 고른다. **When** 파일이 서버에 닿으면 A의 판별기가 `patch`로 판정한다. **Then** 바이트·`sha256`·`byte_length`·`patch`가 슬롯에 담기고, 운영자 화면에 그 넷과 **이름 붙은 행 수**가 뜨며, `run_instruction`도 대상 툴도 **한 번도 불리지 않는다**. 나중에 운영자가 "이거 패치해 줘"라고 하면 모델이 래퍼 툴을 부르고, 핸들러가 슬롯의 바이트를 `import_lxseq_patch`의 `file_content_base64`에 넣어 형제 툴을 부른다 — **모델은 base64를 한 번도 보지 않는다**.

**시나리오 2 — Vectorworks 파일을 올리면 오늘 그대로다.**
**Given** 운영자가 Vectorworks Instrument Data export를 고른다. **When** 판별기가 `vectorworks`로 판정한다. **Then** 그 바이트는 **슬롯에 들어가지 않고** 기존 `_vectorworks_upload`에 담기며, 기존 지시문이 **그대로 발화한다**. 운영자가 보는 것은 오늘과 같다 — B는 이 가지에서 아무것도 바꾸지 않았다.

**시나리오 3 — 올린 것 없이 시킨다.**
**Given** 이번 대화에서 시트를 올린 적이 없다. **When** 모델이 래퍼 툴을 부른다. **Then** `no_uploaded_sheet`라는 **이름 붙은 사유**와 함께, 무엇을 하면 되는지가 적힌 문장이 돌아온다. 조용한 무동작도, 빈 바이트로 대상 툴을 부르는 일도 없다. **이 거절이 모델이 슬롯 상태를 아는 유일한 기계적 경로다** — 업로드 안내는 모델 문맥에 들어가지 않기 때문이다.

**시나리오 4 — 업로드가 세션 생성보다 늦게 온다.**
**Given** 세션이 만들어질 때 슬롯은 비어 있었다. **When** 운영자가 그 뒤에 시트를 올리고 래퍼를 부른다. **Then** 래퍼는 **방금 올린 것을 본다**. 세션 생성 시점의 `None`이 툴 클로저에 얼어붙어 있지 않다.

---

## §C. 인수 기준

### §C.0 역추적표

| AC | 요구 | 축 |
|---|---|---|
| `AC-SHEETPIPE-001` | 전항(착수 게이트) | — |
| `AC-SHEETPIPE-002` | `REQ-SHEETPIPE-001` | 담김 |
| `AC-SHEETPIPE-003` | `REQ-SHEETPIPE-002` | 담김 |
| `AC-SHEETPIPE-004` | `REQ-SHEETPIPE-003` | 안 함 |
| `AC-SHEETPIPE-005` | `REQ-SHEETPIPE-003`(별 구간) · `REQ-SHEETPIPE-008` | 안 함 |
| `AC-SHEETPIPE-006` | `REQ-SHEETPIPE-004` | 보임 |
| `AC-SHEETPIPE-007` | `REQ-SHEETPIPE-005` | 나름 |
| `AC-SHEETPIPE-008` | `REQ-SHEETPIPE-005` | 나름 |
| `AC-SHEETPIPE-009` | `REQ-SHEETPIPE-006` | 나름 |
| `AC-SHEETPIPE-010` | `REQ-SHEETPIPE-007` | 나름 |
| `AC-SHEETPIPE-011` | `REQ-SHEETPIPE-009` | 경계 |

**요구 9건이 전부 덮인다** — `001`(AC-002) · `002`(AC-003) · `003`(AC-004·005) · `004`(AC-006) · `005`(AC-007·008) · `006`(AC-009) · `007`(AC-010) · `008`(AC-005) · `009`(AC-011).

### §C.0a 마일스톤별 AC 배정 (정본)

| 마일스톤 | AC |
|---|---|
| M0 | `001` |
| M1 | `002` · `003` · `004` · `005` · `006` |
| M2 | `007` · `008` · `009` · `010` · `011` |

### AC-SHEETPIPE-001 — M0 계약 대조 게이트

**Given** 착수 시점의 워크트리, **When** M0를 돌면, **Then**

① **A가 실재한다** — `server/sheets/`의 판별 진입점과 레지스트리가 있고 A의 테스트가 초록이다(`ASSUMPTION-78`). 없으면 **B는 여기서 멈춘다**.
② **좌표 11건**(`spec.md` §H)이 **`grep`으로** 재확인됐다. 눈으로 센 값은 증거가 아니다.
③ **등재 7지점**(`spec.md` §G)이 세 측정 명령으로 재확인됐다 — 6·7번이 첫 명령에 **걸리지 않는다는 사실**도 함께 확인한다.
④ **기준선 2종**이 이 워크트리에서 측정돼 `progress.md` §E.1에 기록됐다. 기존 실패는 **원인별로 나눠** 적혔다.
⑤ **A의 태그 재정이 A 쪽에 반영됐는지** 확인돼 기록됐다(`plan.md` §A.4 ① · M0 5) — 레지스트리 행이 `(종, 대상)` 쌍을 들고 `AC-FILEARG-023`이 태그에 맞는 등록부를 본다.

**검증**: `progress.md` §E.1에 ①~⑤가 명령·출력과 함께 있을 것.

### AC-SHEETPIPE-002 — 슬롯이 넷을 든다 (`REQ-SHEETPIPE-001`)

**Given** `patch`로 판정된 바이트, **When** 업로드가 끝나면, **Then**

① 슬롯이 **바이트 · `sha256` · `byte_length` · `kind`**를 든다. `sha256`은 **디코드된 바이트**의 해시이고, `byte_length`도 디코드된 길이다(base64 문자열 길이가 아니다).
② 같은 세션에 새 시트가 오면 **통째로 교체**되고, 교체 사실이 운영자에게 보인다.
③ **기존 두 슬롯과 독립**이다 — 시트 업로드가 `_vectorworks_upload`나 `_layout_image`를 지우지 않고, 그 둘의 업로드도 시트 슬롯을 지우지 않는다.
④ 세션이 끝나면 사라진다(세션 범위).

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "slot"`

### AC-SHEETPIPE-003 — [HARD] 세션 생성 뒤 도착한 업로드를 툴이 본다 (`REQ-SHEETPIPE-002`)

**Given** 슬롯이 비어 있는 채로 만들어진 세션, **When** 그 뒤에 시트를 올리고 래퍼 툴을 부르면, **Then** 래퍼가 **방금 올린 슬롯**을 본다(시나리오 4).

**왜 이것이 따로 서는가.** `AC-SHEETPIPE-002`가 전부 초록이어도 이것은 빨갈 수 있다 — 슬롯은 제대로 채워지고, 안내도 뜨고, 운영자 화면은 정상인데 **툴이 보는 것만** 어긋나기 때문이다. 저장소가 이 결함을 이미 한 번 겪었고 그 기록이 `_LayoutImageUploadView`의 docstring(`server/web/session.py:3353-3364`)에 남아 있다.

**뮤테이션(필수)**: 읽기 통과 뷰를 걷어내고 슬롯 필드를 `build_toolset`에 **그대로** 넘기면 이 AC가 **빨개져야 한다**. `AC-SHEETPIPE-002`는 그 상태에서도 **초록**임을 함께 기록한다 — 두 기준이 다른 것을 재고 있다는 증거다.

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "late_upload_visible"`

### AC-SHEETPIPE-004 — 시트 경로는 아무것도 실행하지 않는다 (`REQ-SHEETPIPE-003`)

**Given** `patch`로 판정된 바이트, **When** 업로드가 끝나면, **Then**

① `run_instruction` 호출 계수 **0**.
② 대상 툴(`import_lxseq_patch`) 호출 계수 **0** — `action="preview"`도 아니다.
③ 콘솔 포트(`execution_port` · `deploy_pipeline`) 호출 계수 **0**.
④ **파싱은 정확히 1회 돈다** — 행 수를 얻기 위한 국소 호출이며, ①②③ 어디에도 닿지 않는다. **0회여도 실패다**(행 수를 낼 수 없으므로) — 이 항이 "실행 금지"를 파싱까지 넓혀 읽는 것을 막는다.

**뮤테이션(필수)**: 업로드 직후 `run_instruction`을 부르도록 바꾸면 ①이 **빨개져야 한다**.

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "no_execution_on_sheet_upload"`

### AC-SHEETPIPE-005 — Vectorworks 가지는 오늘 그대로다 (`REQ-SHEETPIPE-003` 별 구간 · `REQ-SHEETPIPE-008`)

**Given** `vectorworks`로 판정되는 바이트, **When** 업로드가 끝나면, **Then**

① 기존 `_vectorworks_upload`에 담기고 **시트 슬롯은 비어 있다**(결정 C).
② 기존 지시문이 **발화한다** — `run_instruction` 호출 계수 **1**이며 인자는 `_VECTORWORKS_UPLOAD_INSTRUCTION`(`server/web/session.py:3157`) 그대로다.
③ 첨부 버튼은 **하나**이고 비이미지 가지가 보내는 프레임은 **하나**다 — `ui/src/App.tsx:629-635`의 분기가 두 갈래로 남아 있고 세 번째 프레임 종류가 생기지 않았다.
④ `server/web/app.py`와 `server/web/messages.py`는 **한 줄도 바뀌지 않았다**(`git diff --stat <착수 SHA>..HEAD -- server/web/app.py server/web/messages.py`가 빈 출력).
⑤ 전사 문구는 **종류를 단정하지 않는다** — `ui/src/useCopilotSocket.ts:336`이 더 이상 판정 전에 "Vectorworks 파일"이라 적지 않는다.

**[HARD] ②가 이 카드에서 가장 되돌리기 쉬운 항이다.** `REQ-SHEETPIPE-003`을 프레임 전체로 넓혀 읽으면 ②가 사라지고, 그것은 **오늘 살아 있는 기능의 회수**다. ①~⑤ 중 하나라도 빨가면 그 넓은 읽기를 한 것이다.

**전제 — 성립한다 (2026-08-23 재정).** v0.1.0은 이 AC에 조건절을 달아 두었다: `plan.md` §A.4 ①이 `vectorworks` 행에 **불리하게** 풀리면 "판정이 `vectorworks`"라는 가지가 도달 불가가 되므로 AC를 재작성해야 한다는 것이었다. 재정은 행을 **살리는** 쪽이었다 — `target` 열을 (종, 대상) 쌍으로 넓히고 `vectorworks` 행은 `(session_method, upload_vectorworks_export)`로 **등록된 채 남는다**. 그러므로 그 가지는 **도달 가능**하고 **이 AC는 조건 없이 선다**. 조건절은 걷어냈고, 이 AC는 §D의 "조건부 AC 0건"에 그대로 든다.

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "vectorworks_branch_unchanged"` + ④의 `git diff --stat`

### AC-SHEETPIPE-006 — 업로드 직후 넷이 보이고, 행 수에 이름이 붙는다 (`REQ-SHEETPIPE-004`)

> **분할 기록.** A의 `AC-FILEARG-009`가 겸하던 두 단언 중 **표시** 단언이 여기다. A는 **순서** 단언(판별이 파싱하지 않는다)을 자기 번호로 가진다.

**Given** `patch`로 판정된 바이트, **When** 업로드가 끝나면, **Then**

① 운영자에게 **종류 · `sha256` · `byte_length` · 행 수** 넷이 보인다.
② 표시 주체는 **서버**다 — `notice_event`로 나가며 UI에 새 렌더링 코드가 생기지 않았다.
③ **행 수에 이름이 붙어 있다** — `records` · `rejected` · `excluded` 중 **어느 통을 센 수인지** 문구가 밝힌다.
④ 세 통이 전부 0이 아닌 입력에서, 표시가 **그 사실을 말한다**. 거부된 행이 있는데 맨 숫자만 보이면 빨갛다.
⑤ `sha256`은 운영자가 원본 파일과 **대조할 수 있는 값**이다(`shasum -a 256 <파일>`과 일치).

**뮤테이션(필수)**: 행 수 문구에서 통 이름을 떼고 맨 숫자로 바꾸면 ③이 **빨개져야 한다**. ④의 픽스처(거부 행이 섞인 CSV)가 없으면 ④는 판별력이 없으므로, 픽스처를 먼저 만들고 그 사실을 기록한다.

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "upload_notice"`

### AC-SHEETPIPE-007 — 래퍼가 바이트를 주입한다 (`REQ-SHEETPIPE-005`)

**Given** 슬롯에 `patch` 시트가 담긴 세션, **When** 모델이 래퍼 툴을 부르면, **Then**

① 핸들러가 슬롯의 바이트를 꺼내 **내부 `ToolCall`**로 형제 툴을 부른다. 주입 지점은 대상 툴의 `file_content_base64` 인자다.
② 대상 툴 이름은 **레지스트리 행이 지목한 것**이며 핸들러 안에 하드코딩돼 있지 않다 — 행의 `target` **쌍**(`(종, 대상)`)을 읽는다. 종이 **`tool`인 행만** 이 경로로 온다 — `session_method` 종은 업로드 이음매에서 이미 처분되므로(결정 C) 래퍼에 닿지 않으며, 닿았다면 그것이 결함이다.
③ 형제 툴이 받은 바이트가 슬롯의 바이트와 **동일**하다(`sha256` 일치).
④ 통과 인자는 레지스트리 행의 **화이트리스트로 한정**된다 — 화이트리스트 밖의 인자를 래퍼가 받아도 형제 툴에 전달되지 않는다.

**주입 대조표** (호출 1회에서 관측):

| 관측 지점 | 기대 |
|---|---|
| 래퍼가 받은 인자 | `file_content_base64` **없음** |
| 형제 툴이 받은 인자 | `file_content_base64` **있음** · 값이 슬롯 바이트 |
| 형제 툴이 받은 그 밖의 인자 | 화이트리스트 안의 것만 |

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "wrapper_injects"`

### AC-SHEETPIPE-008 — [HARD] 등재 7지점이 전부 쳐졌다 (`REQ-SHEETPIPE-005`)

**Given** M2 완료 후의 트리, **When** `spec.md` §G의 세 측정 명령을 돌리면, **Then**

① 지점 1~5가 새 툴 이름을 담는다.
② 지점 6 — `server/tests/test_tools.py`의 리터럴이 **`35`**이고, `TOOL_NAMES` 길이도 35다.
③ 지점 7 — 트립와이어 시작점 목록이 재생성됐고 **`_TOOLS_PROTECTED_OLD_RANGES` 침범이 0건**이다. 침범 0건은 **재측정한 값**이지 전례로 미루는 값이 아니다.
④ 가드 두 종이 초록이다 — `test_runner_progress.py`의 양방향 전단사, 각 툴 테스트의 `advertised == set(TOOL_NAMES)`.
⑤ **전체 스위트를 두 번 돌았다** — 등재 직후 한 번, 트립와이어 재생성 후 한 번. 두 결과를 `progress.md`에 적는다.

**[HARD] ③은 ①②를 증명하지 않고, ④는 ①~③을 증명하지 않는다.** 가드는 **빠뜨림 검출기**이지 등재의 증거가 아니다 — 가드가 초록인 것과 그 가드가 이 자리를 **보는 것**은 다른 문장이다. 지점 6·7은 툴 이름을 문자열로 담지 않으므로 첫 측정 명령에 **영원히 걸리지 않으며**, 그래서 두 번째·세 번째 명령이 따로 있다.

**검증**: `spec.md` §G의 세 명령 + `uv run pytest server/tests -q`

### AC-SHEETPIPE-009 — 래퍼 스키마에 바이트 인자도 경로 인자도 없다 (`REQ-SHEETPIPE-006` → `REQ-LXSEQ-016`)

**Given** 등재된 래퍼의 `ToolDefinition`, **When** 스키마를 읽으면, **Then**

① `properties`에 **`file_content_base64`가 없다**.
② `properties`의 어떤 인자도 **파일 시스템 경로**를 받지 않는다 — 이름과 설명문 양쪽으로 확인한다(`path` · `file` · `filename` 같은 이름이 없고, 설명문이 경로를 요구하지 않는다).
③ `additionalProperties`가 **`False`**다 — 인자 집합이 닫혀 있어 모델이 임의 인자를 밀어 넣을 수 없다.
④ 설명문이 **"바이트는 이미 세션에 있다"**를 말한다 — 모델이 바이트를 요구하거나 채팅 본문을 base64로 만들 생각을 하지 않도록.

**뮤테이션(필수)**: 스키마에 `file_content_base64`를 더하면 ①이 **빨개져야 한다**. 이것이 `REQ-LXSEQ-016`이 막던 붙여넣기 경로가 다시 열리는 자리이므로, 편의로 되돌아오는 것을 기계가 막는다.

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "wrapper_schema"`

### AC-SHEETPIPE-010 — 거절 3종이 이름으로 나온다 (`REQ-SHEETPIPE-007`)

**Given** 래퍼 호출이 진행될 수 없는 세 상황, **When** 각각을 부르면, **Then**

| 상황 | 사유 이름 | 함께 나오는 것 |
|---|---|---|
| 슬롯이 비었다 | `no_uploaded_sheet` | 파일을 올리라는 안내(바이트를 붙여넣으라고 **하지 않는다**) |
| 슬롯 종류가 요청된 `action`을 지원하지 않는다 | `kind_action_mismatch` | 그 종류가 지원하는 `action` 목록 |
| 그 종류의 대상이 **자기 태그에 맞는 등록부**에 없다 (`tool` → `TOOL_NAMES`) | `no_target_tool` | 어느 종류의 어느 대상이 어느 등록부에 없는지 |

① 세 사유는 **닫힌 집합**이다 — 래퍼가 낼 수 있는 거절이 이 셋뿐임을 테스트가 단언한다.
② **조용한 무동작 경로가 없다** — 어느 경우에도 빈 결과를 성공으로 돌려주지 않는다.
③ `no_target_tool`은 **래퍼 호출 시점**의 방어이며 A의 `AC-FILEARG-023`(**판별 시점**)을 대신하지 않는다. 둘을 한 지점으로 합치지 않는다.

**뮤테이션(필수)**: 빈 슬롯일 때 거절 대신 빈 바이트로 대상 툴을 부르도록 바꾸면 ①②가 **빨개져야 한다**.

**검증**: `uv run pytest server/tests/test_sheet_pipe.py -q -k "wrapper_refusal"`

### AC-SHEETPIPE-011 — 경계 게이트 · **커밋 뒤에** 돌린다 (`REQ-SHEETPIPE-009`)

**Given** M2 완료 후의 트리, **When** 보존 대상 변경을 기계로 확인하면, **Then**

**① 직접 diff — 이것이 본 검사다.** `plan.md` §C의 "열지 않는 것" 목록이 **한 줄도 바뀌지 않았다**.

**② 대상 트리.** `server/sheets/**`(**A의 트리**) · `server/web/app.py` · `server/web/messages.py` · `server/web/preview.py` · `ui/src/protocol.ts` · `server/lxseq/**` · `server/vwx/**` · `console/lua/**` · `server/safety/**` · `server/prechk/**` · `server/paperwork/**` · `server/rulebook/assets/**`.

**③ 저장소 PRESERVE 가드가 초록이다 — 단, 그 가드가 덮는 범위는 좁다.** `server/tests/test_overlap_preserve.py:52 _PRESERVE_PATHS`가 지키는 것은 열 항목뿐이며(`server/looks/*` · `server/looks/library/` · `server/web/preview.py` · `console/lua/` · `server/rulebook/assets/v2.4.2/`), ②가 열거한 나머지는 **그 목록에 없다**. `server/safety/`는 예외로 별도 상수 `_SAFETY_DIR`(`:186`)이 따로 지키므로 가드 시야 **안**이다.

> **[HARD] ③은 ②를 증명하지 않는다.** ②의 대부분에 대해서는 **①의 직접 diff가 유일한 검사**다. 여기서도 구분은 같다 — **"가드가 초록이다"와 "그 가드가 이 트리를 본다"는 다른 문장이다.**

**[HARD] 실행 순서 — 커밋 → 게이트 → 보고.** 취향이 아니라 **정확성 조건**이다. `test_overlap_preserve.py`는 고정 base와 **`HEAD`**를 diff하므로(그 파일의 `..HEAD` 지점은 **22곳** — `grep -cE '\.\.HEAD'`), 작업 트리의 미커밋 변경은 그 진단의 **시야 밖**이고 **커밋 전 초록은 구조적으로 보장된 거짓 신호**다. 저장소 메모리의 "게이트는 미추적 파일을 못 본다"와 같은 계열이다.

> **나중에 읽는 사람에게**: 이 단계를 "커밋 전에 미리 돌려 두면 빠르다"로 되돌리지 마라. `base..HEAD` 스코핑 때문에 그 최적화는 **검사를 없애는 것과 같다**.

**검증**(이 순서 그대로):

```
1) git add <B가 연 파일들> && git commit          # 반드시 먼저
2) uv run pytest server/tests/test_overlap_preserve.py -q                 # ③ (좁은 범위)
3) git diff --stat <착수 SHA>..HEAD -- server/sheets server/web/app.py server/web/messages.py server/web/preview.py ui/src/protocol.ts server/lxseq server/vwx console/lua server/safety server/prechk server/paperwork server/rulebook/assets     # ① (②의 전 트리)
```

3)이 **빈 출력**이고 2)가 초록일 것. **3)이 본 검사이고 2)는 보조다.** 커밋 전에 잰 결과는 증거로 인정하지 않으며 `progress.md`에는 **커밋 SHA와 함께** 적는다.

**뮤테이션 — 대상은 `server/web/preview.py` 하나로 지정한다.** `_PRESERVE_PATHS`에 **실제로 들어 있는 것을 확인했기 때문**이다. "보존 대상 중 아무 파일이나"로 두면 구현자가 `server/lxseq/`를 집고, ③이 **초록**으로 나오는 것을 *"내 뮤테이션이 실패했다"*로 읽어 헤매다 흘려보낸다 — 그 초록은 뮤테이션 실패가 아니라 **가드의 사각지대**다.

**[HARD] 전제 확인 — 뮤테이션 전에 대상이 깨끗한지 먼저 잰다.**

```
0) git diff --stat <가드 base>..HEAD -- server/web/preview.py   # 뮤테이션 **전에**
```

**빈 출력이어야 시작한다.** 비어 있지 않으면 이 뮤테이션은 **판별력 없음(N/A)**으로 기록하고 실제 출력을 함께 남긴다 — 더러운 파일을 물려받은 실행이 기존 빨강을 자기 성과로 읽는 것을 막는다.

- `server/web/preview.py`를 한 줄 고쳐 **커밋한 뒤** 돌리면 ①③이 **빨개져야 한다**.
- 같은 수정을 **커밋하지 않고** 돌리면 **초록**이 나온다 — 그 초록이 이 AC가 막는 거짓 신호이며 **두 상태를 모두** 기록한다.
- 참고(기록만, 판정 아님): `server/sheets/`처럼 `_PRESERVE_PATHS` 밖 트리를 고치면 커밋 뒤에도 ③은 초록이고 **①만 빨개진다**. 그것이 ①이 본 검사인 이유다.

## §D. Definition of Done

**Tier M · 통과 임계 0.80** (`spec.md` §A.5 — 성격이 티어를 정하고, 티어가 임계를 정한다).

**[HARD] 계수 규약** — `spec.md` §C.0이 정본이며 다섯 줄 전부 여기에도 걸린다. 특히:

```
grep -c "^- \*\*REQ-SHEETPIPE-" spec.md        → 9
grep -c "^### AC-SHEETPIPE-"   acceptance.md   → 11
```

**숫자만 적고 그 숫자를 만든 명령을 적지 않으면 다음 사람이 틀린 명령을 부른다.** 그리고 **부정 grep 결과는 부재의 증거가 아니다** — 인라인 강조가 문자열을 쪼갠다. 무엇을 옮기거나 지웠으면 그 이름을 **긍정으로 전수 훑는다**.

1. **AC 11건 전부 PASS.** 조건부 AC는 **없다.** `AC-SHEETPIPE-005`가 v0.1.0에 달고 있던 유일한 조건절은 §A.4 ①의 재정으로 **성립 확인되어 걷어냈다** — `vectorworks` 행이 `(session_method, …)`로 남으므로 그 가지는 도달 가능하다. 어떤 AC도 **N/A로 세지 않는다**.
2. **전체 스위트 2종**(`uv run pytest server/tests -q` · `npm --prefix ui run test`)이 착수 기준선 대비 **감소 0 · 신규 실패 0**. **B는 `ui/`를 열므로 vitest 델타가 0이 아닌 것이 정상**이며, 델타의 내용이 `REQ-SHEETPIPE-008`이 예고한 변경과 일치해야 한다.
3. **`plan.md` §A.4의 clarification 마커가 0건**이고, 결정 A~H의 답이 `progress.md`에 기록돼 있다.
4. **뮤테이션 원장 — 6건.** `AC-003` 뷰 제거 · `AC-004` 업로드 직후 실행 · `AC-006` 통 이름 제거 · `AC-009` 스키마에 바이트 인자 추가 · `AC-010` 빈 슬롯에 빈 바이트 호출 · `AC-011` 경계 침범(커밋 뒤 판정). 각각 해당 테스트를 **실제로 죽이는 것을 실측**하고 `progress.md`에 적는다.
   - **`AC-003`의 뮤테이션은 두 결과를 함께 적는다** — 뷰를 걷어내면 `AC-003`은 빨갛고 `AC-002`는 **초록**이다. 그 짝이 두 기준이 다른 것을 재고 있다는 증거이며, 초록 쪽을 적지 않으면 판별력을 보이지 못한다.
   - **`AC-011`의 뮤테이션도 두 상태를 함께 적는다** — 커밋 뒤는 빨강, 커밋 전은 초록. 그 초록이 이 AC가 막는 거짓 신호다. 그리고 **전제 확인 0)이 빈 출력이 아니면 N/A로 기록**한다.
5. **등재 7지점이 §G의 세 명령으로 확인**됐고, 트립와이어 **보호 구간 침범 0건**이 재측정값으로 기록됐다.
6. **좌표 재확인 결과**가 `progress.md`에 있다 — 어긋난 것이 있었으면 정정 전후를 함께 적는다.
