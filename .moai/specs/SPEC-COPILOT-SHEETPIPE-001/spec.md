---
id: SPEC-COPILOT-SHEETPIPE-001
title: "시트 전달경로 — 판별된 바이트를 세션 슬롯과 래퍼 툴 인자까지 나른다 (분할 B)"
version: "0.3.0"
status: in-progress
created: 2026-08-23
updated: 2026-08-24
author: manager-spec (칸반 카드 t10)
priority: P1
phase: "v0.3.0 target — 분할 B(전달경로). SPEC-COPILOT-FILEARG-001(A · 판별기)이 통과한 뒤 착수한다"
module: "server/web/session.py (세션 슬롯 · 업로드 이음매), server/orchestrator/{tools,runner}.py (래퍼 툴 등재), ui/src/{App.tsx,useCopilotSocket.ts,protocol.ts} (첨부 경로 — 소비만), server/sheets/ (A가 소유 — 판정 호출만)"
lifecycle: spec-anchored
tags: "session-slot, wrapper-tool, tool-registration, file-picker, upload-frame, no-auto-execution, lxseq, grandma3"
tier: M
related_specs: [SPEC-COPILOT-FILEARG-001, SPEC-COPILOT-LXSEQ-001, SPEC-COPILOT-VWX-001, SPEC-COPILOT-IMGLAYOUT-001, SPEC-COPILOT-AUTOPATCH-001]
---

# SPEC-COPILOT-SHEETPIPE-001 — 판별된 바이트를 툴 인자까지 나른다

> **칸반 카드 t10 · 분할 B.** `SPEC-COPILOT-FILEARG-001`(A)은 **"이것은 무엇인가"**에 답한다 — 레지스트리 · 판별 술어 · 신원/사용성 축 · 배제 절 · `.mvr` 위임 계약. 본 SPEC(B)은 **"그 바이트를 어떻게 나르는가"**에 답한다 — 세션 슬롯 · 래퍼 툴의 인자 · UI 선택기 배선.
>
> **B는 A의 계약을 다시 적지 않는다.** 판별 결과의 의미(`resolved` · `unknown_sheet_kind` · `ambiguous_sheet_kind`), 레지스트리의 형태, 술어의 축은 전부 A가 소유하며 B는 **참조**한다. B가 소유하는 것은 그 판정을 받은 **뒤**에 일어나는 일 전부다.
>
> **경고 — B가 지적을 받은 적이 없다는 것은 깨끗하다는 뜻이 아니다.** A의 `.mvr` 계약도 두 라운드를 무사히 지난 뒤 **차단 결함**으로 드러났다. B의 "이미 증명된 패턴을 계승한다"는 틀은 **가설**로 다룬다 — 실제로 §F 속성 A는 그 계승을 문자 그대로 하면 조용히 무너지는 자리를 하나 찾아냈다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.3.0 | 2026-08-24 | manager-spec | **plan-audit PASS-WITH-DEBT 0.91 — 채무 6건 정리(문서 전용 · 코드 변경 0 · REQ 9 · AC 11 불변).** **D1 — "이미 겪은 결함"은 거짓이었다**: `43b1b04`은 `feat` 커밋이고 docstring은 **가정법**("would therefore freeze")이며 IMGLAYOUT 아티팩트의 언급은 **0건**이다 — 뷰를 쓴 사람이 위험을 **미리** 적은 것이지 아무도 당하지 않았다. 두 문장(§F 속성 A · `AC-SHEETPIPE-003`)을 예견으로 정정하고, `REQ-SHEETPIPE-002`를 떠받치는 근거를 **두 형태가 한 `build_toolset` 호출에 동시에 살아 있다는 실측**으로 바꿨다(요구 자체는 그대로 선다). 일반형은 §C.0 **규약 6**으로 등재. **D2 — 종류를 단정하는 문구가 넷이었다**: `useCopilotSocket.ts:336` 하나만 고쳐 두었고 `App.tsx:551` · `:555` · `:559` 셋이 남아 있었다. **`:555`·`:559`는 오늘의 패치 CSV에서도 도달한다**(8 MiB 초과 · 판독 실패). `REQ-SHEETPIPE-008` ②를 넷 전부로 넓히고 §G.1(정본 · 도달성 실측표) 신설, `AC-SHEETPIPE-005` ⑤에 넷을 명시. **③과 충돌하지 않는다** — ⑤는 `uploadVectorworksExport` **본문 문자열**, ③은 `routeAttachment` **분기**로 서로 다른 함수다. vitest 델타 실측 **0**(그 문구를 단언하는 기존 테스트 없음). **D3 — 주석을 진짜 검사로 승격**: `spec.md`는 "기계로 막는다"고, `plan.md`는 "기계 검사는 없다"고 적어 모순이었다. 문면 맞추기 대신 **`grep` 단언**을 택했다 — 주석에 앵커 토큰 `SPEC-COPILOT-SHEETPIPE-001`을 달고 `AC-SHEETPIPE-005` ⑥이 그 존재를 단언한다(오늘 그 파일의 토큰은 **0건**이므로 판별력 있음). 그 검사가 **존재만 단언하고 뜻은 단언하지 못한다**는 한계도 함께 적었다. **D4 — "한 줄도 바꾸지 않는다"는 결정 B와 모순**: 이음매가 그 메서드 본문에 들어가므로 글자는 필연적으로 바뀐다. 사전 확정 사실 3과 §F 속성 B를 **"동작을 회수하지 않는다"**로 정정했다. **D5 — 비용 열거가 미측정이었고 자기 규약을 어겼다**: `git grep -l` 재측정 → **16파일**(코드·계약 **8** + 문서 8). "빌더 둘"은 **하나 많았다**(이 프레임의 빌더는 `protocol.ts:503` 하나). `PROTOCOL.md` · `protocol.test.ts` · 테스트 3종이 빠져 있었다 — 결론은 뒤집히지 않고 **강해진다**. **D6 — "기재가 있을 것"은 실패 기록도 통과시킨다**: `AC-SHEETPIPE-001`에 항별 통과 조건표를 넣고, ①이 "A 없음"으로 확인된 경우는 **성실한 기록이지만 FAIL**임을 명시했다. |
| 0.2.0 | 2026-08-23 | manager-spec | **열린 결정 1건 닫힘 — A의 `target` 열 태그 재정 반영.** B가 v0.1.0에서 올린 물음(레지스트리 `target` 열이 툴 이름과 세션 메서드 **두 종**을 담는데 A의 `AC-FILEARG-023`은 술어를 한정 없이 적어 `vectorworks` 행을 매번 배제한다)을 **A의 소유자가 재정했다** — 열을 **(종, 대상) 쌍**으로 넓히고 각 항목에 종을 붙인다(`(tool, import_lxseq_patch)` · `(session_method, upload_vectorworks_export)`). 좁히면 A의 결정 I가 뒤집히고, 이름으로 면제하면 후속 SPEC에 규칙이 남지 않는다. 태그가 붙으면 `AC-FILEARG-023`은 여전히 기계적이다(`tool` → `TOOL_NAMES`, `session_method` → `ChatSession`의 속성 — 소유 클래스 `server/web/session.py:3405`, 메서드 `:9655`). B의 변경: **clarification 마커 1건 → 0건**(`plan.md` §A.4) · `AC-SHEETPIPE-005`의 **조건절 제거**(전제가 성립하는 쪽으로 풀렸다 — 재작성 불필요, 성립을 명문화) · `target`을 서술하는 자리 넷을 태그형으로 정렬(§A 사전 확정 사실 10 · `REQ-SHEETPIPE-005` · `REQ-SHEETPIPE-007` · §E) · `plan.md` §A.1 · §A.3 결정 C · M0 5 · §D 위험표 갱신. **A가 이번 패스에서 함께 고치는 것 2건은 B에서 다시 올리지 않는다**: A의 `README.md:85-95` 인용이 `server/tests/fixtures/vwx/README.md:84-95`로 정정되고, `base..HEAD` 지점 수가 **22곳**으로 정정된다 — **내가 적은 `:427 · :456 · :464`도 A가 적은 `:427 · :446 · :456`도 둘 다 부분집합이었다**(각자 자기 변수명만 훑었다). 특히 **`:446`이 그 파일에 없다던 v0.1.0의 정정은 틀렸다** — `_PRECHK_BASE`를 쓰는 진짜 지점이며, 본 세션에서 철회했다. 좁은 패턴의 히트 수는 **총계가 아니라 하한**이다. REQ **9** · AC **11** 불변. |
| 0.1.0 | 2026-08-23 | manager-spec | 최초 작성 (draft, **Tier M** · 통과 임계 **0.80**). 아티팩트 집합 **3종**(`spec.md` · `plan.md` · `acceptance.md`) + `progress.md`(집합에 **포함되지 않음** — A의 감사 A1이 잡은 오산을 되풀이하지 않기 위해 명시). REQ **9건**(`REQ-SHEETPIPE-001~009` — 리드 배정 8보다 **하나 많고**, 사유는 §B 머리의 [HARD] 주가 소유한다), AC **11건**(`AC-SHEETPIPE-001~011`), 마일스톤 **3개**(M0~M2), clarification 마커 **1건**(plan.md §A.4 ① — A 레지스트리 `target` 열의 두 종). 좌표 **11건**을 본 세션에서 전수 재측정했고(§H), 그중 **2건은 앞선 기록이 한 줄 이르게 적혀 있었다**(`@dataclass` 데코레이터를 시작으로 센 결과) — 정정해 실었다. 등재 지점은 **4지점도 6지점도 아니라 7지점**임을 측정으로 확정하고 §G에 **배제 기준과 측정 명령을 함께** 실었다. |

---

## A. 개요

**한 줄**: 첨부 버튼이 고른 비(非)이미지 파일의 바이트가 서버에 닿으면, A의 판별기가 그것이 무엇인지 정한다. 판정이 `vectorworks`면 **오늘 그대로** 기존 경로로 흘러간다. 판정이 시트 종류(오늘은 `patch` 하나)면 바이트·`sha256`·`byte_length`·종류를 **세션 슬롯 하나**에 담고 **아무것도 실행하지 않는다**. 나중에 운영자가 시킬 때, 모델은 바이트를 만지지 않는 **래퍼 툴**을 부르고, 그 핸들러가 슬롯의 바이트를 대상 툴의 `file_content_base64` 인자에 넣어 형제 툴을 내부 `ToolCall`로 호출한다.

### 사전 확정 사실 (본 세션 실측 — 좌표는 §H가 소유)

1. **바이트를 툴 인자에 넣는 선례가 저장소에 있다.** `vectorworks_autopatch` 핸들러(`server/orchestrator/tools.py:2944`)가 세션이 든 바이트를 `content = vectorworks_upload.content_base64`(`:2950`)로 꺼내 `arguments={"file_content_base64": content}`(`:2961`)로 형제 툴을 부른다. 래퍼 자신의 스키마에는 그 인자가 **없다**. B는 이 형태를 계승한다.
2. **세션 슬롯의 선례는 둘이고, 둘은 서로 다른 물건이다.** `_UploadedVectorworksExport`(`server/web/session.py:2493`)는 **가변** 데이터클래스이며 `.replace()`로 **제자리에서** 바뀌고 `build_toolset`에 **필드가 그대로** 넘어간다(`session.py:3515`). `LayoutImageUpload`(`session.py:2512`)는 **`frozen=True`**이며 업로드마다 **통째로 교체**되므로 필드를 그대로 넘기면 툴 클로저에 업로드 이전의 `None`이 **영구히 얼어붙는다** — 그래서 `_LayoutImageUploadView`(`session.py:3353`)라는 **읽기 통과 뷰**를 거쳐 넘긴다(`session.py:3525`). 이 둘을 섞으면 조용히 무너진다(§F 속성 A).
3. **업로드가 실행을 부르는가는 이미 갈려 있다.** `upload_vectorworks_export`(`session.py:9655`)는 담은 **직후** `run_instruction(_VECTORWORKS_UPLOAD_INSTRUCTION)`을 부른다(`:9658`). `upload_layout_image`(`session.py:9660`)는 담고 안내만 낸다. B의 시트 경로는 **후자**를 따른다. `vectorworks` 판정 경로는 **오늘의 동작을 회수하지 않는다** — 이음매가 그 메서드 **본문 안**에 들어가므로(plan.md 결정 B) 그 메서드는 필연적으로 바뀌지만, 판정이 `vectorworks`일 때 흐르는 두 줄(`:9657` 담기 · `:9658` 지시문)은 **그대로 남고 그대로 발화한다**. 불변인 것은 파일의 글자가 아니라 **운영자가 보는 결과**다.
4. **UI는 툴 호출을 조립하지 않는다.** `sendVectorworksExportUpload`·`sendLayoutImageUpload`(`ui/src/useCopilotSocket.ts:332-351`)는 채팅 메시지 하나를 띄우고 프레임을 보낼 뿐이고, 빌더(`ui/src/protocol.ts:503` · `:519`)도 마찬가지다. 인자를 채우는 일은 전부 서버에서 일어난다 — B도 그 경계를 지킨다.
5. **첨부 버튼은 하나다.** `routeAttachment`(`ui/src/App.tsx:629`)는 이미지 MIME이면 `uploadLayoutImage`, **그 밖이면 전부** `uploadVectorworksExport`로 보낸다(`:630-634`). 바로 위 주석(`:625-628`)이 **2026-08-15 운영자 결정** — "첨부 버튼은 하나 — 파일 종류가 목적지를 고른다" — 을 기록한다. 그 결정은 유지된다.
6. **비이미지 프레임은 서버에서 확장자로 한 번 더 걸린다.** `parse_client_message`(`server/web/messages.py:194-203`)가 `vectorworks_export_upload.file_name`을 `VECTORWORKS_UPLOAD_EXTENSIONS`(`.csv`/`.txt`/`.xlsx`/`.mvr`)로 검사하고, 8 MiB 상한과 base64 유효성도 그 자리에서 본다(`:208-219`). 이 검사는 **바이트가 세션에 닿기 전**이며 B는 건드리지 않는다.
7. **`notice_event`는 모델의 문맥에 들어가지 않는다.** 전사 기록은 `_record_history`(`session.py:9719`)를 거치는데, 그것을 부르는 곳은 `run_instruction` 경로 둘뿐이다(`:9639` · `:9650`). 그러므로 업로드 안내는 **운영자 화면에만** 뜬다 — 모델은 슬롯이 채워진 것을 안내로 알지 못하고, 운영자의 말 또는 래퍼 툴의 **이름 붙은 거절**로 안다. `analyse_layout_image`가 이미 그렇게 산다.
8. **대상 툴의 인자 집합은 닫혀 있고 경로 인자가 없다.** `import_lxseq_patch` 스키마(`tools.py:9253-9306`)는 `required: ["file_content_base64"]`(`:9304`) · `additionalProperties: False`(`:9305`)이며 형제 인자는 `action`·`name_prefix_mode`·`only_fids`·`mode_overrides`뿐이다. 인자 설명문이 **"이 툴은 파일 경로를 받지 않는다"**를 명시한다(`:9264`).
9. **오늘 유일한 호출자는 개발용 하네스다.** `server/tools/lxseq_e2e.py`가 파일을 읽어 base64로 만들어 제품 툴 스택을 직접 부른다. 운영자는 앱으로 LX-SEQ 패치 CSV를 넣을 수 없다 — 이것이 본 카드가 고치는 결함이다.

10. **A의 레지스트리 `target` 열은 (종, 대상) 쌍이다** (2026-08-23 A 재정 — 정본은 A가 소유한다). 한 열이 두 종을 담는다 — `(tool, import_lxseq_patch)`와 `(session_method, upload_vectorworks_export)`. **B가 이 물음을 A에 올렸고**(v0.1.0의 clarification 마커), A가 열을 좁히거나 이름으로 면제하는 대신 **넓히고 태그를 붙이는** 쪽으로 재정했다. B에 대한 귀결은 좁다 — 래퍼가 부르는 것은 **`tool` 종뿐**이고(`session_method` 종은 업로드 이음매에서 이미 처분된다), `no_target_tool` 검사는 **태그에 맞는 등록부**를 본다. 본 세션 확인: `TOOL_NAMES`는 34개이며 `upload_vectorworks_export`는 그 안에 없다(`ChatSession`의 메서드다 — 소유 클래스 `server/web/session.py:3405`, 메서드 `:9655`).

    **같은 결함의 데이터판 쌍둥이.** A가 함수 층위에서 이미 기록한 결함과 형태가 같다 — `has_address_family`는 **한 함수가 두 물음**에 답했고, `target` 열은 **한 열이 두 종**을 담았다. 둘 다 *"판별자 없이 한 자리에 두 가지"*다. **짝의 기록은 A가 자기 쪽에 남긴다**(`design.md` §1); B는 교차 참조만 들고 사본을 만들지 않는다.

### 이 SPEC이 하는 것 / 하지 않는 것

| 하는 것 (B · 전달경로) | 하지 않는 것 |
|---|---|
| 세션 슬롯 하나 — 바이트 · `sha256` · `byte_length` · 종류 | **판별 자체** — 술어 · 레지스트리 · 신원/사용성 축은 **A가 소유** |
| 시트 판정 뒤 **아무것도 실행하지 않기** | `vectorworks` 판정 경로의 동작 변경 |
| 업로드 직후 **넷 표시**(종류 · `sha256` · `byte_length` · 행 수) | 행 수를 판별의 입력으로 쓰기(A의 순서 속성) |
| 래퍼 툴 **1종** 등재 + 핸들러의 바이트 주입 | 래퍼 스키마에 `file_content_base64`나 경로 인자 두기 |
| 이름 붙은 거절 **3종**(닫힌 집합) | 조용한 무동작 |
| 첨부 버튼 **하나** 유지 · 프레임 하나로 서버가 라우팅 | 확장자·MIME으로 시트 종류 분기 |

### §A.4 분할 좌표 — A와 B의 경계 (A `spec.md` §A.4의 거울면)

| | A (`SPEC-COPILOT-FILEARG-001`) | B (본 SPEC) |
|---|---|---|
| 답하는 물음 | **"이것은 무엇인가"** | **"그 바이트를 어떻게 나르는가"** |
| REQ | 16 (`001~005` · `007` · `008` · `016~024`) | **9** (`REQ-SHEETPIPE-001~009`) |
| AC | 20 | **11** (`AC-SHEETPIPE-001~011`) |
| Tier · 임계 | L · 0.85 | **M · 0.80** |
| 소유 트리 | `server/sheets/**` | `server/web/` · `server/orchestrator/` · `ui/` |

**번호는 새로 매긴다.** A는 자기 번호에 빈칸(`006` · `009~015`)을 남겼고 그 빈칸은 **A의 감사 추적을 위한 자리 표시**이지 B의 번호가 아니다(A `spec.md` §A.4 — "A는 B의 번호 체계를 인용하지 않는다"). 그러므로 B는 `REQ-SHEETPIPE-001`부터 자기 번호를 쓴다. A의 빈칸과 B의 번호 사이에 **1:1 대응은 없다** — 분할 이후 요구를 다시 나눴기 때문이다(예: A의 빈 `010`이 담던 "업로드 직후 넷 표시"는 B에서 `REQ-SHEETPIPE-004`이고, 그 옆의 "실행하지 않는다"는 `REQ-SHEETPIPE-003`으로 갈라져 나왔다).

**A가 B에 넘긴 단언이 하나 있다.** A의 `AC-FILEARG-009`는 두 요구를 겸하다 쪼개졌다 — **순서** 단언(판별이 파싱하지 않는다)은 A가 갖고, **표시** 단언(업로드 직후 넷을 보인다)은 B가 자기 번호로 가져간다. B에서 그것은 **`AC-SHEETPIPE-006`**이다.

### §A.5 B가 Tier M인 이유

`spec-workflow.md`는 Tier L을 "**> 1000 LOC 또는 constitutional**"로 정의한다. B는 **어느 쪽도 아니다**:

- **constitutional 아님** — B는 다른 SPEC이 따라야 할 규칙을 세우지 않는다. 레지스트리 계약(후속 SPEC이 행을 더하는 규칙)은 **A**가 소유한다. B는 그 계약의 **소비자 하나**를 만들 뿐이며, LXSEQ-002/003/004는 B를 읽지 않아도 자기 행을 더할 수 있다.
- **> 1000 LOC 아님** — 신규 코드는 세션 슬롯 하나 · 이음매 분기 하나 · 래퍼 핸들러 하나 · 등재 7지점이다. 나머지는 기존 두 선례의 형태를 따른다.

**Tier M의 천장은 REQ 16 / AC 16이다.** B는 REQ **9** / AC **11**로 그 안에 있다. AC는 리드 배정(11)과 같고, REQ는 배정(8)보다 **하나 많다** — 사유와 합치지 않은 근거는 §B 머리의 [HARD] 주가 소유한다.

---

## B. 요구사항 (GEARS)

> **계수 앵커**: `grep -c "^- \*\*REQ-SHEETPIPE-" spec.md` → **9**. 참조까지 세는 맨 ID 훑기는 과대 보고한다(§C.0 계수 규약).
>
> **[HARD] 배정보다 하나 많다 — 숨기지 않고 적는다.** 리드 배정은 REQ **8**이었고 실측은 **9**다. 늘어난 하나는 `REQ-SHEETPIPE-002`(슬롯 가변성이 노출 방식을 강제한다)이며, 리드 배정 1번("세션 슬롯 — 증명된 `_UploadedVectorworksExport` 패턴을 계승")을 **가설로 다뤄** 나온 자리다(§F 속성 A). 합치지 않은 이유는 **따로 무너지기 때문**이다 — 슬롯이 넷을 제대로 담아도(`REQ-001` 초록) 노출 방식이 어긋나면 툴은 영원히 빈 슬롯을 본다. Tier M 천장(REQ 16 / AC 16) 안이며, 예산 완화가 아니라 **배정 대비 +1의 기록**이다.

### B.1 세션 슬롯 (`server/web/session.py`)

- **REQ-SHEETPIPE-001** `[Ubiquitous]` The 세션 **shall** 판별을 통과한 업로드를 **슬롯 하나**에 담는다. 슬롯이 드는 것은 넷이다 — **바이트**(base64 원문) · **`sha256`**(그 바이트의 해시) · **`byte_length`**(디코드된 바이트 길이) · **`kind`**(A의 판별기가 정한 종류). 슬롯은 세션 범위이며 세션이 끝나면 사라진다. 같은 세션에서 새 시트가 올라오면 **통째로 교체**하고, 교체했다는 사실을 소리 내어 말한다(`upload_layout_image`가 이미 그렇게 한다 — `session.py:9672` · `:9681-9686`). 슬롯은 기존 두 슬롯(`_vectorworks_upload` · `_layout_image`)과 **독립**이며 서로를 지우지 않는다 — 셋은 서로 다른 툴이 읽는 서로 다른 물건이다.
- **REQ-SHEETPIPE-002** `[Ubiquitous]` The 슬롯의 **가변성 선택**은 **노출 방식을 강제한다**. 두 선례는 형태가 다르다 — `_UploadedVectorworksExport`(`session.py:2493`)는 가변이고 제자리에서 바뀌므로 필드를 `build_toolset`에 **그대로** 넘겨도 되고, `LayoutImageUpload`(`session.py:2512`)는 `frozen=True`이고 통째로 교체되므로 **읽기 통과 뷰**(`_LayoutImageUploadView`, `session.py:3353`)를 거쳐야 한다. The 구현 **shall** 둘 중 하나를 고르고 **그 짝을 지킨다** — 통째 교체를 고르고서 필드를 그대로 넘기면 툴 클로저에 업로드 이전의 `None`이 **영구히 얼어붙고**, 그 결함은 운영자가 파일을 올려 툴을 시켜 보기 전까지 **보이지 않는다**(§F 속성 A · `AC-SHEETPIPE-003`).

### B.2 실행 금지와 표시 (`server/web/session.py`)

- **REQ-SHEETPIPE-003** `[Unwanted]` The 시트 업로드 경로 **shall not** 무엇도 실행한다 — `run_instruction` 호출 **0회**, 대상 툴 호출 **0회**이며 `action="preview"`조차 부르지 않는다. **경계선을 분명히 한다**: 금지되는 것은 **모델·콘솔·대상 툴에 닿는 호출**이고, 종류가 정해진 **뒤** 행 수를 얻으려 도는 **국소 파싱 한 번**은 여기 해당하지 않는다(그것은 A의 `REQ-FILEARG-005`가 이미 허용한 "종류가 정해진 뒤 한 번"이다). **이 금지는 시트 경로에만 걸린다** — `vectorworks` 판정이 나면 기존 `run_instruction`(`session.py:9658`)은 **그대로 발화한다**. 오늘의 Vectorworks 동작을 회수하지 않는 것이 이 요구의 일부다(`REQ-SHEETPIPE-008` · `AC-SHEETPIPE-005`).
- **REQ-SHEETPIPE-004** `[Event-driven]` **When** 슬롯이 채워지면, the 시스템 **shall** 운영자에게 **넷**을 보인다 — **종류** · **`sha256`** · **`byte_length`** · **행 수**. 표시 주체는 **서버**이며 수단은 `notice_event`다(`upload_layout_image`와 같은 형태) — UI에는 새 렌더링 코드가 생기지 않는다. **행 수는 이름 붙은 수여야 한다.** `parse_patch_csv`(`server/lxseq/parser.py:162`)가 돌려주는 `ParseResult`(`:112`)는 `records` · `rejected` · `excluded` **세 통**으로 나뉘므로, 맨 숫자 하나는 어느 통인지 말하지 않는다. 표시는 **어느 통을 센 수인지 함께** 밝히고, 세 통이 전부 0이 아니면 **그 사실도 함께** 밝힌다 — "행 12건"이라 적고 그중 3건이 거부됐다면 그것은 운영자를 잘못 안심시키는 문장이다.

### B.3 래퍼 툴 (`server/orchestrator/tools.py` · `runner.py`)

- **REQ-SHEETPIPE-005** `[Ubiquitous]` The 시스템 **shall** 래퍼 툴 **1종**을 등재하고, 그 핸들러가 슬롯의 바이트를 **A의 레지스트리 행이 지목한 대상**(`target` 쌍의 종이 **`tool`**인 것 — 사전 확정 사실 10)의 `file_content_base64` 인자에 넣어 **내부 `ToolCall`**로 형제 툴을 부른다. 형태는 `vectorworks_autopatch`(`tools.py:2944` · 꺼내기 `:2950` · 주입 `:2961`)를 그대로 계승한다. 통과 인자는 A의 레지스트리 행이 정한 **화이트리스트**로 한정하며(오늘 `patch` 행: `action` · `name_prefix_mode` · `only_fids` · `mode_overrides`), 화이트리스트 밖의 인자는 전달하지 않는다. 등재 지점은 **7곳**이며 그 열거와 배제 기준은 §G가 소유한다 — 앞선 SPEC이 "4지점"이라 적어 두 자리를 반복해 빠뜨렸고, 그 둘은 `tools.py`를 읽어서는 보이지 않고 **전체 스위트를 돌려야** 드러난다.
- **REQ-SHEETPIPE-006** `[Unwanted]` The 래퍼 툴의 스키마 **shall not** `file_content_base64`를 선언하거나 받아들이며, **파일 시스템 경로 인자도 두지 않는다**. `additionalProperties: False`로 인자 집합을 닫는다. **이것은 구현 세부가 아니라 요구다** — 이 부재가 곧 "모델은 바이트를 한 번도 다루지 않는다"의 보증이고(A `spec.md` §F 속성 C), 편의를 위해 언제든 되돌릴 수 있는 종류의 것이라 못박아 둔다. `REQ-LXSEQ-016`으로 역추적한다 — 그 요구가 금지한 것은 "채팅에 붙여넣은 텍스트로 바이트를 만드는 것"이고, 래퍼가 바이트 인자를 갖는 순간 모델이 그 텍스트를 채워 넣을 자리가 생긴다.
- **REQ-SHEETPIPE-007** `[Event-driven]` **When** 래퍼 호출이 진행될 수 없으면, the 시스템 **shall** 사유를 **이름으로** 밝히고 조용히 아무것도 하지 않는 경로를 두지 않는다. 사유는 **닫힌 집합 3종**이다 — **`no_uploaded_sheet`**(슬롯이 비었다) · **`kind_action_mismatch`**(슬롯의 종류가 요청된 `action`을 지원하지 않는다) · **`no_target_tool`**(그 종류의 대상이 자기 **태그에 맞는 등록부**에 없다 — `tool` 종은 `TOOL_NAMES`를, `session_method` 종은 `ChatSession`의 속성을 본다. 사전 확정 사실 10). 각 사유는 운영자가 **다음에 무엇을 할지 알 수 있는 문장**을 함께 낸다. `no_target_tool`은 **래퍼 호출 시점**의 방어이며 A의 `AC-FILEARG-023`(**판별 시점**의 방어)을 대신하지 않는다 — 둘은 다른 지점이고 서로를 대신하지 않는다. **슬롯이 비었을 때의 거절이 특히 중요하다**: `notice_event`는 모델 문맥에 들어가지 않으므로(사전 확정 사실 7), 모델이 "올라온 시트가 없다"를 아는 유일한 기계적 경로가 이 거절이다.

### B.4 첨부 경로 (`ui/src/**` · `server/web/app.py`)

- **REQ-SHEETPIPE-008** `[Ubiquitous]` The 첨부 경로 **shall** 버튼 **하나**를 유지하고(2026-08-15 운영자 결정 — `ui/src/App.tsx:625-628`), 비이미지 파일은 **프레임 하나**로 서버에 보내며, **종류 판정은 서버가** 한다. UI는 분류하지 않는다 — A의 판별기가 서버에 있고 확장자·MIME 분기는 A가 금지했으므로, UI가 세 번째 프레임 종류를 **고를 수 있는 근거가 없다**. 그러므로 비이미지 가지는 기존 프레임 `vectorworks_export_upload`를 계속 쓰고, 그 이름은 **"Vectorworks 파일"이 아니라 "비이미지 첨부"를 뜻하는 유산 이름**으로 다시 읽힌다. 이름을 바꾸지 않는 이유는 값이 이름보다 크기 때문이다 — **`git grep -l 'vectorworks_export_upload'` → 16파일**이며, 그중 코드·계약 **8파일**(`server/web/app.py` · `server/web/messages.py` · `server/web/PROTOCOL.md` · `ui/src/protocol.ts` · `ui/src/protocol.test.ts` · `server/tests/test_web_app.py` · `server/tests/test_web_messages.py` · `server/tests/test_prechk_tool.py`)이 전부 따라 움직인다(나머지 8은 `CHANGELOG.md` · 보고서 2 · SPEC 아티팩트 5). **v0.1.0의 이 문장은 §C.0 규약 1을 스스로 어겼다** — 수치를 명령 없이 적었고, "빌더 둘"은 **하나 많았다**(`ui/src/protocol.ts`에 이 프레임을 만드는 빌더는 `buildVectorworksExportUpload` **하나**뿐이다 — `:503`; 둘로 센 것은 업로드 빌더 둘(vectorworks + layout image)과 혼동한 것이다). 재측정은 결론을 **뒤집지 않고 강화한다** — 빠져 있던 `PROTOCOL.md` · `protocol.test.ts` · 테스트 3종이 비용을 **더 크게** 만든다. 대신 **두 가지를 기계로 막는다**: ① 그 프레임이 더 이상 한 종류만 나르지 않는다는 사실을 `routeAttachment` 옆 주석으로 남겨 나중에 읽는 사람이 확장자 라우팅을 "복원"하지 않게 하되, **그 주석의 존재를 `grep`으로 단언한다** — 주석은 앵커 토큰 `SPEC-COPILOT-SHEETPIPE-001`을 달고, 그 토큰이 `ui/src/App.tsx`에 없으면 검사가 빨개진다(오늘 그 파일에 그 토큰은 **0건**이므로 이 검사는 판별력이 있다). **기대값이 주석에만 있는 검사는 아무것도 단언하지 않으므로**, 의도를 적어 두는 것으로 그치지 않고 적혀 있음 자체를 기계에 건다 · ② UI가 띄우는 **종류를 단정하는 문구 전부**를 종류 중립으로 바꾼다 — 이 문구들은 **판정 전에** 나가므로 어느 것도 종류를 단정할 수 없다(대상은 §G.1이 열거한다).

### B.5 경계 보존 (PRESERVE)

- **REQ-SHEETPIPE-009** `[Unwanted]` The 변경 **shall not** B가 소유하는 트리와 그 테스트 **밖의 파일을 수정한다**. B가 여는 것은 `server/web/session.py` · `server/orchestrator/tools.py` · `server/orchestrator/runner.py` · `ui/src/{App.tsx,useCopilotSocket.ts,protocol.ts}` 와 §G가 열거한 두 가드 파일, 그리고 B의 신규 테스트다. **`server/sheets/**`는 A의 트리이며 B는 판정을 호출할 뿐 한 줄도 고치지 않는다.** 그 밖에 읽기만 하는 것: `server/lxseq/**` · `server/vwx/**` · `console/lua/**` · `server/safety/**` · `server/prechk/**` · `server/paperwork/**` · `server/rulebook/assets/**` · `server/web/preview.py`. **A의 경계 요구를 빌려 쓸 수 없다** — A의 경계는 "`server/sheets/`만 만들고 그 밖은 안 건드린다"이고 B의 경계는 그 반대 모양이다(`server/sheets/`가 **읽기 전용**이고 UI·세션·오케스트레이터가 **열려 있다**). 검증은 `AC-SHEETPIPE-011`이 소유하며 **커밋 뒤에** 돌린다(사유는 그 AC가 소유한다).

---

## C. 환경 및 전제

### §C.0 [HARD] 증거 규약 — 여섯 줄

A가 다섯 라운드에 걸쳐 값을 치르고 얻은 규약이며, B는 **첫 판부터** 지킨다.

1. **정의로 세고, 언급으로 세지 않는다.** REQ·AC 수는 **정의 앵커**가 낸 값이며, 그 값 옆에는 **그 값을 만든 명령**이 붙는다. 숫자만 적으면 다음 사람이 다른 명령을 부른다.
   ```
   grep -c "^- \*\*REQ-SHEETPIPE-" spec.md        → 9
   grep -c "^### AC-SHEETPIPE-"   acceptance.md   → 11
   ```
2. **부정 grep 결과는 부재의 증거가 아니다.** 이 문서 묶음은 인라인 강조가 문자열을 쪼갠다 — `정본을 **참조**한다`는 `정본을 참조`로 훑어도 걸리지 않는다. 문구 확인은 ① 강조를 걷어낸 **짧은 핵심 토큰**으로 훑고 ② 히트를 **눈으로 판독**한다.
3. **그 거울상도 같은 실수다.** 무엇을 **옮기거나 지웠으면** 그 이름을 **긍정으로 전수 훑어** 살아남은 포인터를 찾는다. A는 규약 2를 쓴 바로 그 라운드에 이 거울상을 어겨 포인터 19곳을 고아로 만들었다.
4. **움직이는 대상은 수치로 못박지 않는다.** `origin/main` 대비 규모 같은 값은 이 보드가 커밋하는 동안 달라지므로 **같은 명령이 몇 시간 안에 다른 값**을 낸다. 크기가 논증을 지지하지 않으면 **정성적으로** 적고, 굳이 남기려면 **두 ref와 명령을 함께** 적는다.
5. **결정적인 줄을 인용하고, 범위는 양끝을 잰다.** 데코레이터를 클래스의 시작으로 세면 좌표가 한 줄 이르게 적힌다(`2492`/`2511` → 실제 **`2493`**/**`2512`**). 본 세션에서도 `sed` 출력에서 눈으로 센 두 좌표가 한 줄씩 어긋났고 `grep`으로 재서야 잡혔다 — **좌표는 눈이 아니라 `grep`이 낸다.**
6. **가드의 docstring은 예견이지 사고 기록이 아니다 — 도입 커밋을 열어 보기 전까지 역사로 읽지 않는다.** 방어 코드 옆의 설명문은 대개 **가정법**으로 쓰인다("그대로 넘기면 …이 얼어붙**을 것이다**"). 그것은 저자가 위험을 **미리** 적은 것이지 누군가 당했다는 뜻이 아니다. 판별법은 싸다 — `git log -1 --format='%s' <커밋>`이 `fix`인지 `feat`인지 보고, 그 SPEC의 아티팩트가 그 사고를 언급하는지 본다. 본 SPEC이 v0.1.0~v0.2.0에서 이 함정에 걸렸다(`43b1b04`은 `feat`이고 IMGLAYOUT 아티팩트의 언급은 **0건**이다). **요구가 서는 근거를 사고에서 실측으로 바꿔야 한다** — `REQ-SHEETPIPE-002`를 떠받치는 것은 "한 번 당했다"가 아니라 **두 형태가 한 `build_toolset` 호출에 동시에 살아 있다**는 측정이다.

### 측정된 기준선

착수 브랜치 `WT-file-picker-args`. 기준선 실측값은 `progress.md` §E.1 `baseline_measured`가 소유하며 그 값은 **미측정**이다 — 다른 트리·다른 세대에서 잰 전체 스위트 수치는 이월하지 않는다. **M0가 A 병합 직후의 이 워크트리에서 직접 잰다.**

**이 저장소에는 테스트 CI가 없다.** `.github/workflows/`에는 라벨 동기화 워크플로 하나뿐이므로 회귀의 유일한 증거는 **로컬 전체 스위트**(`uv run pytest server/tests -q` + `npm --prefix ui run test`)다. **B는 A와 달리 `ui/`를 건드리므로 vitest 델타가 0이 아니다** — 두 스위트를 모두 기준선과 대조한다.

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC을 이어받는다(A가 `ASSUMPTION-77`까지 썼다).

- **ASSUMPTION-78** — **A가 먼저 통과했고 그 판별기가 이 워크트리에 있다.** B는 A의 판정을 호출할 뿐 스스로 판별하지 않으므로, A 없이는 착수할 수 없다. NEGATIVE면 그것은 결함이 아니라 **순서 위반**이며 B는 M0에서 멈춘다(`AC-SHEETPIPE-001`).
- **ASSUMPTION-79** — **오늘 Vectorworks 경로로 잘 처리되던 업로드 중 A의 판별기가 `unknown_sheet_kind`로 거절할 파일이 운영자의 실사용에 없다.** A는 헤더 없는 `.txt`가 이제 `unknown_sheet_kind`가 **정답**이라고 결정했고(A `AC-FILEARG-022`), 근거는 `server/tests/fixtures/vwx/README.md:84-95` 판독이다 — A는 이 인용을 디렉터리 없이 `README.md:85-95`로 적었고, 그 경로는 **저장소 루트의 다른 문서**(안전 게이트 절)로 풀린다. 본 세션에서 실제 원본을 찾아 다시 인용했다. 그러나 **그 판단은 운영자의 실제 업로드 이력으로 재지 않았다** — 저장소 픽스처로 잰 것이다. NEGATIVE면 오늘 되던 업로드가 B의 이음매에서 거절되고, 그것은 **B의 이음매에서 표면화하지만 A의 결정**이다(plan.md §D.1 잔여 위험).

### PRESERVE — 무변경 대상

`server/sheets/**`(**A의 트리 — 판정 호출만**) · `server/lxseq/**` · `server/vwx/**` · `console/lua/**` · `server/safety/**` · `server/prechk/**` · `server/paperwork/**` · `server/rulebook/assets/**` · `server/web/preview.py` · `server/web/messages.py`의 기존 프레임 검증 본문 · `session.py`의 `upload_layout_image` 본문 · `tools.py`의 기존 핸들러 본문 전부. 게이트는 `AC-SHEETPIPE-011`이 소유한다.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — 판별 그 자체 (A가 소유)

- 판별 술어를 정의하거나 고치지 않는다. 열 집합 서명 · 위임 술어 · 신원/사용성 축 · 배제 절은 전부 A의 것이다.
- 레지스트리의 형태·행·표현력을 바꾸지 않는다. B는 행을 **읽어** 대상과 통과 인자를 꺼낼 뿐이다.
- `unknown_sheet_kind` · `ambiguous_sheet_kind`의 판정 규칙(0건 거절 · 2건 이상 거절)을 다시 정의하지 않는다. B는 그 결과를 **받아** 운영자에게 전달할 뿐이다.
- `.mvr` · `.xlsx` zip 갈래의 위임 계약을 만들지 않는다(A `REQ-FILEARG-021`).

### Out of Scope — 002/003/004 시트의 파서와 핸들러

- 그룹 · 프리셋/FX · 시퀀스 시트를 읽는 코드도, 그 종류의 대상 툴도 만들지 않는다. B가 만드는 래퍼는 **한 종**이고, 그것은 **레지스트리가 지목한 대상**을 부르므로 후속 SPEC이 행을 더하면 래퍼는 그대로 둔 채 동작한다.
- 종류별로 래퍼를 늘리지 않는다. 래퍼가 늘어나야 한다면 그것은 레지스트리 계약이 실패했다는 신호이며, 그때 고칠 곳은 A다.

### Out of Scope — 대상 툴의 계약 변경

- `import_lxseq_patch`의 인자 집합 · 스키마 · 설명문 · 페이로드 구조를 바꾸지 않는다. 시트 종류 인자도 경로 인자도 만들지 않는다.
- `server/lxseq/{parser,mapper}.py`의 동작을 바꾸지 않는다. B는 `parse_patch_csv`를 **부를** 뿐이다.

### Out of Scope — 첨부 UI의 재설계

- 첨부 버튼을 둘로 늘리거나, 업로드 전에 종류를 고르게 하는 선택기를 넣지 않는다(2026-08-15 운영자 결정 유지).
- 드래그 앤 드롭 · 다중 파일 · 업로드 이력 보관 · 진행률 표시를 넣지 않는다.
- 프로토콜 프레임의 **이름을 바꾸지 않는다**(`REQ-SHEETPIPE-008` — 값이 이름보다 크다). 프로토콜 버전도 올리지 않는다.
- `upload_layout_image` 경로의 동작 · 문구 · 크기 상한을 바꾸지 않는다.
- `messages.py`의 확장자 허용 목록과 8 MiB 상한을 바꾸지 않는다.

### Out of Scope — 콘솔 쓰기와 자동화

- 업로드 시점에 콘솔을 읽거나 쓰지 않는다. 새 Lua 생성기 · 새 OSC 경로 · 새 쓰기 경로는 0건이다.
- 래퍼가 `apply`를 대신 승인하지 않는다. 쓰기 승인은 여전히 대상 툴과 번들 게이트가 한다.

---

## E. 데이터 모델 (What — 구현 함수명 아님)

| 개체 | 필드 | 출처 |
|---|---|---|
| `UploadedSheet` (세션 슬롯) | `content_base64` · `sha256` · `byte_length` · `kind` · `file_name` | REQ-SHEETPIPE-001 |
| 슬롯 노출 방식 | 가변·제자리 교체 → 필드 직접 전달 / 불변·통째 교체 → **읽기 통과 뷰** (둘 중 하나를 고르고 그 짝을 지킨다) | REQ-SHEETPIPE-002 |
| 업로드 직후 보고 | `kind` · `sha256` · `byte_length` · **이름 붙은 행 수**(어느 통을 센 수인지 함께) | REQ-SHEETPIPE-004 |
| 래퍼 거절 사유 | `no_uploaded_sheet` · `kind_action_mismatch` · `no_target_tool` (닫힌 집합 — 래퍼가 낼 수 있는 전부) | REQ-SHEETPIPE-007 |
| 래퍼 통과 인자 | 레지스트리 행의 화이트리스트 (오늘 `patch`: `action` · `name_prefix_mode` · `only_fids` · `mode_overrides`) | REQ-SHEETPIPE-005 |
| 레지스트리 `target` (A 소유 — 참조만) | **(종, 대상) 쌍** — 종 ∈ {`tool`, `session_method`}. 래퍼는 `tool` 종만 부른다 | 사전 확정 사실 10 · A `spec.md` §G |

> **여기서 빠진 개체는 A가 소유한다.** `DiscriminationPredicate` · `SheetKindRow` · `Discrimination` · 판별 거절 사유 둘은 A `spec.md` §E가 정의하며, B는 그 정의를 참조만 한다.

---

## F. [HARD] 세 가지 성질 — 명시하지 않으면 조용히 무너진다

### 속성 A — 슬롯의 가변성이 노출 방식을 강제한다

리드의 지시는 "증명된 `_UploadedVectorworksExport` 패턴을 계승한다"였다. 그 틀을 **가설로 다루자** 곧바로 자리 하나가 나왔다. 저장소에는 슬롯 선례가 **둘**이고 둘은 형태가 반대다:

| 선례 | 형태 | `build_toolset`에 넘기는 법 |
|---|---|---|
| `_UploadedVectorworksExport` (`session.py:2493`) | **가변** · `.replace()`로 제자리 변경 | 필드를 **그대로** (`session.py:3515`) |
| `LayoutImageUpload` (`session.py:2512`) | **`frozen=True`** · 업로드마다 통째 교체 | **읽기 통과 뷰**를 거쳐 (`session.py:3525`) |

섞으면 무너진다. 뷰를 쓴 사람이 그 위험을 **미리** 적어 두었다(`43b1b04`, docstring `session.py:3353-3364`) — 통째 교체되는 필드를 세션 생성 시점에 그대로 넘기면 툴 클로저에 업로드 이전의 `None`이 **영구히 얼어붙어**, 세션 생성 뒤 도착한 업로드가 툴에게 보이지 않는다.

**이 결함은 조용하다.** 슬롯은 채워지고, 안내도 뜨고, 운영자 화면은 정상이다. 어긋나는 것은 **툴이 보는 것**뿐이라, 운영자가 실제로 시켜 봐서 `no_uploaded_sheet` 거절을 받기 전까지 아무 신호도 없다. 그래서 이것을 요구로 못박고(`REQ-SHEETPIPE-002`) 뮤테이션으로 지킨다(`AC-SHEETPIPE-003`).

### 속성 B — 실행 금지는 시트 경로에만 걸리고, 파싱은 실행이 아니다

`REQ-SHEETPIPE-003`을 문면 그대로 넓게 읽으면 두 가지가 함께 부서진다. 첫째, "업로드 경로에서 `run_instruction` 금지"를 프레임 전체에 걸면 **오늘 살아 있는 Vectorworks 동작이 사라진다** — 그 경로는 담은 직후 지시문을 부르는 것이 설계다(`session.py:9658`). 둘째, "아무것도 실행하지 않는다"를 파싱까지로 넓히면 **행 수를 낼 수 없다**(`REQ-SHEETPIPE-004`). 그러므로 경계선을 두 번 긋는다:

- **어느 경로인가** — 금지는 **시트 판정** 뒤의 경로에만 걸린다. `vectorworks` 판정 경로의 **동작은 회수되지 않는다**(메서드 본문에는 분기가 들어가므로 글자는 바뀐다 — 사전 확정 사실 3).
- **무엇이 실행인가** — 실행은 **모델 · 콘솔 · 대상 툴에 닿는 호출**이다. 종류가 정해진 뒤 도는 국소 파싱 한 번은 그 셋 중 무엇에도 닿지 않으며, A의 `REQ-FILEARG-005`가 이미 "종류가 정해진 뒤 한 번"으로 허용한 바로 그 호출이다.

### 속성 C — 래퍼 스키마의 부재는 구현 세부가 아니라 요구다

`file_content_base64`가 래퍼 스키마에 **없다**는 사실이 "모델은 바이트를 한 번도 다루지 않는다"를 보장한다. 이 부재는 편의를 위해 언제든 되돌아온다 — 누군가 "그냥 인자로 받으면 간단한데"라고 생각하는 순간 `REQ-LXSEQ-016`이 막던 붙여넣기 경로가 다시 열린다. 그래서 `REQ-SHEETPIPE-006`으로 못박고 `REQ-LXSEQ-016`으로 역추적한다. A `spec.md` §F 속성 C와 같은 문장이며, **그 요구를 실제로 지는 것은 B다** — 래퍼를 만드는 쪽이 B이기 때문이다.

---

## G. 부록 — 툴 등재 지점 (정본 · 실측)

**앞선 SPEC은 "4지점"이라 적었고**(`SPEC-COPILOT-LXSEQ-001` `REQ-LXSEQ-010`), 그 결과 두 자리가 반복해서 빠졌다. 두 자리 모두 `tools.py`를 읽어서는 **보이지 않고** 전체 스위트를 돌려야 드러난다. 본 세션에서 `vectorworks_autopatch`가 손댄 자리를 전수로 훑어 **7곳**으로 확정했다.

**측정 명령**(첫 명령이 **14행**을 낸다 — 아래 분류표가 그 14행을 전부 처분한다):
```
grep -rn 'vectorworks_autopatch' server/orchestrator/ server/tests/
grep -n 'len(names) == len(TOOL_NAMES)' server/tests/test_tools.py
grep -n '_TOOLS_EXPECTED_HUNK_OLD_STARTS' server/tests/test_songcue_bundle.py
```

**[HARD] 배제 기준 — 숫자만 옮기지 않고 기준을 함께 싣는 이유.** 총 몇 행이 나왔는지가 아니라 **무엇을 왜 뺐는지**가 다음 사람의 검산 근거다. 기준은 하나다: **그 파일에 새 툴에 관한 값을 손으로 적어 넣어야 하는가.** "그렇다"면 편집 지점, 집합 비교나 전단사로 **저절로 따라오면** 가드다.

| # | 지점 | 좌표(`vectorworks_autopatch` 기준) | 무엇을 적는가 |
|---|---|---|---|
| 1 | `TOOL_NAMES` 튜플 | `server/orchestrator/tools.py:244` | 툴 이름 1줄 |
| 2 | 핸들러 클로저 (`build_toolset` 안) | `server/orchestrator/tools.py:2944` | 함수 정의 |
| 3 | `ToolDefinition(name=…)` | `server/orchestrator/tools.py:7615` | 스키마 · 설명문 |
| 4 | `handlers` 맵 | `server/orchestrator/tools.py:9321` | 이름 → 핸들러 1줄 |
| 5 | `_TOOL_TASKS` | `server/orchestrator/runner.py:148` (표 정의 `:137`) | 한국어 작업 이름 1줄 |
| 6 | 툴 총 개수 리터럴 | `server/tests/test_tools.py:172` | **`34` → `35`** |
| 7 | `tools.py` 헝크 트립와이어 | `server/tests/test_songcue_bundle.py:215` | 시작점 목록 **통째 재생성** |

**14행의 처분 (전수 — 남는 행 0)**: `tools.py` **6**(코드 4 = 지점 1·2·3·4 + 주석 `:2935` · `:3244`) · `runner.py` **1**(지점 5) · `test_autopatch_tool.py` **5**(그 툴 **자신의 동작 테스트** — B는 자기 테스트를 **새 파일**로 쓰므로 기존 파일 편집이 아니다) · `test_tools.py` **1**(주석 `:153` — 리터럴 `34`는 툴 이름을 담지 않아 이 grep에 걸리지 않고, 그래서 **두 번째 명령이 따로 필요하다**) · `test_prechk_tool.py` **1**(형제 툴 테스트의 언급). 지점 6·7은 툴 이름을 문자열로 담지 않으므로 **첫 명령으로는 영원히 안 걸린다** — 두 자리가 반복해 빠진 이유가 정확히 이것이다.

**배제한 것 — 가드이지 편집 지점이 아니다:**

- `server/tests/test_runner_progress.py:303` · `:307` — `_TOOL_TASKS` **양방향 전단사**. 5번을 빠뜨리면 여기가 빨개진다(빠뜨림 검출기이지 적어 넣는 자리가 아니다).
- `test_autopatch_tool.py:274` · `test_busking_tool.py:107` · `test_layout_image_tool.py:151` 등의 `advertised == set(TOOL_NAMES)` — `TOOL_NAMES`에서 파생되므로 1번만 하면 저절로 통과한다.
- `tools.py:2935` · `:3244` · `test_tools.py:153` — 주석 안의 이름 언급. 동작에 관여하지 않는다.

**7번의 진짜 불변식은 시작점 목록이 아니다.** `_TOOLS_EXPECTED_HUNK_OLD_STARTS`(`:215`)는 **갱신 대상**이고, 지켜야 하는 것은 `_TOOLS_PROTECTED_OLD_RANGES`(`:282`) 침범 **0건**이다. 본 세션에서 그 두 구간이 무엇을 지키는지 base(`38a6e7e`)에서 직접 읽었다 — `234..238`은 프로그래머 상태 판별 튜플(`_PROGRAMMER_STATE_COMMANDS`)이고 `TOOL_NAMES`가 **아니다**. 그러므로 `TOOL_NAMES` 한 줄 삽입이 보호 구간을 침범할 이유는 없지만, **가정하지 말고 M2에서 다시 잰다**(`AC-SHEETPIPE-008`).

**B가 여는 자리는 여기에 두 곳이 더 붙는다** — 등재가 아니라 **래퍼가 슬롯을 보게 하는 배선**이며, 계획의 파일 목록이 빠뜨리기 쉬운 짝이다:

| 지점 | 좌표(기존 두 슬롯 기준) | 무엇을 적는가 |
|---|---|---|
| `build_toolset` 시그니처 | `server/orchestrator/tools.py:1609` (선례 인자 `:1626` · `:1628`) | 슬롯 포트 인자 |
| `build_toolset` 호출부 | `server/web/session.py:3508` (선례 `:3515` · `:3525`) | 슬롯 또는 뷰 전달 |

---

### G.1 부록 — 종류를 단정하는 UI 문구 (정본 · 실측)

**원칙은 하나다** — 이 문구들은 **판정 전에** 나가므로 **어느 것도 종류를 단정할 수 없다**. v0.1.0은 그 원칙을 세워 놓고 `useCopilotSocket.ts:336` **한 곳에만** 적용했다. 형제 셋이 `uploadVectorworksExport` 본문에 있고, 그 함수는 결정 A 이후 **비이미지 첨부 전부**가 지나는 자리다.

**측정 명령**: `grep -n 'Vectorworks' ui/src/App.tsx ui/src/useCopilotSocket.ts`

| 좌표 | 문구 | 언제 발화하나 | 오늘의 시트 종류(`patch`)에서 도달하나 |
|---|---|---|---|
| `useCopilotSocket.ts:336` | `Vectorworks 파일 업로드: {name}` | 비이미지 업로드 **전부** | **도달** — 정상 경로 |
| `App.tsx:551` | `Vectorworks export는 CSV, TXT, XLSX 또는 MVR 파일만 …` | 확장자가 넷 밖일 때 | **미도달** — `.csv`는 목록 안이다. 다만 `.pdf` 등을 붙인 운영자는 **Vectorworks 문구**를 받는다 |
| `App.tsx:555` | `Vectorworks export는 비어 있지 않은 8 MiB 이하 …` | 빈 파일 또는 8 MiB 초과(`App.tsx:94`) | **도달** — 8 MiB 넘는 패치 CSV |
| `App.tsx:559` | `Vectorworks 파일을 읽지 못했습니다.` | `FileReader` 실패 | **도달** — 어느 비이미지 파일이든 |

**넷 모두 바꾼다.** `:551`이 오늘의 `patch`에서 미도달이라는 것은 **면제 사유가 아니다** — 그 문구를 받는 사람은 Vectorworks를 올린 적이 없는 운영자이고, 레지스트리에 행이 하나 더 붙는 순간(LXSEQ-002/003/004) 확장자 목록 밖의 시트가 생기면 그대로 도달한다. 도달 여부는 **오늘의 사실**이지 문구가 참인 이유가 아니다.

**이 넷은 `routeAttachment`(`App.tsx:629-635`)의 분기와 다른 자리다.** 분기는 두 갈래로 남고(`AC-SHEETPIPE-005` ③), 바뀌는 것은 `uploadVectorworksExport` 본문의 **문자열**과 전사 문구다 — 둘은 충돌하지 않는다.

## H. 참조 구현 — 좌표 (본 세션 `grep` 실측)

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 래퍼 → 형제 툴 바이트 주입 | `server/orchestrator/tools.py:2944` · 꺼내기 `:2950` · 주입 `:2961` | 래퍼 스키마에 바이트 인자를 두지 않고 핸들러가 주입하는 형태 |
| 가변 슬롯 | `server/web/session.py:2493` (`_UploadedVectorworksExport`) | 제자리 교체 · 필드 직접 전달 |
| 불변 슬롯 | `server/web/session.py:2512` (`LayoutImageUpload`) | 통째 교체 · **읽기 통과 뷰 필수** |
| 읽기 통과 뷰 | `server/web/session.py:3353-3364` (`_LayoutImageUploadView`) | 클로저 동결 회피 (§F 속성 A) |
| 실행하는 업로드 | `server/web/session.py:9655` · 지시문 발화 `:9658` | **바꾸지 않는다** — `vectorworks` 판정 경로 |
| 담기만 하는 업로드 | `server/web/session.py:9660` · 교체 고지 `:9672` · `:9681-9686` | 시트 경로가 따르는 형태 |
| 전사 미기록 | `_record_history` `server/web/session.py:9719`, 호출부 `:9639` · `:9650` | `notice_event`는 모델 문맥에 들어가지 않는다 |
| 첨부 라우터 | `ui/src/App.tsx:625-628`(운영자 결정) · `:629-635`(분기) · `:550`(확장자) | 버튼 하나 유지 |
| 종류를 단정하는 문구 **넷** | `ui/src/useCopilotSocket.ts:336` · `ui/src/App.tsx:551` · `:555` · `:559` (정본 · 도달성 실측표는 §G.1) | 넷 다 **판정 전에** 나가므로 어느 것도 종류를 단정하지 않는다 |
| 프레임 빌더 | `ui/src/protocol.ts:503` · `:519` | UI는 툴 호출을 조립하지 않는다 |
| 프레임 검증 | `server/web/messages.py:194-219` · 분기 `server/web/app.py:494` | 확장자 · 8 MiB · base64 — **바꾸지 않는다** |
| 대상 툴 스키마 | `server/orchestrator/tools.py:9253-9306` (`:9264` · `:9304` · `:9305`) | 닫힌 인자 집합 · 경로 인자 없음 |
| 행 수 출처 | `server/lxseq/parser.py:162` (`parse_patch_csv`) · `:112` (`ParseResult`) | 세 통으로 나뉘므로 **이름 붙은 수**로 보고 |
