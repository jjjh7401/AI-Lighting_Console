# SPEC-COPILOT-FILEARG-001 — 조사 기록 (research)

문서 상태: **in-progress** (updated 2026-08-24 — M1 실행됨) · 직전 개정 (v1.0.0, 2026-08-24 — §11 델타 재감사 F2 뿌리 · 신원 열 재계산 · v1.0.0 zip 조기 반환 실측과 결과 ④ 소관 이관 기록) · **Tier L**(v0.5.0 분할 이후 — v0.4.0까지 이 줄은 Tier M으로 남아 있었다) · 본 문서는 **저장소 정적 조사**의 기록이다. 라이브 콘솔 관측은 0건(M5가 사용자 수행 앱 실기 1회를 소유). 근거 등급: `[코드]`(이 워크트리에서 직접 읽음) · `[리드]`(칸반 리드가 이 워크트리에서 읽어 확정해 넘긴 좌표) · `[문서]`(타 SPEC 아티팩트) · `[미확정]`.

> **참조 규약.** 정본(spec.md · acceptance.md)은 안정 토큰만. 코드는 `파일:줄`. 줄번호는 plan 작성 시점 트리 `eb436e8`(워크트리는 그 뒤 `6296af3`으로 fast-forward됐다 — 줄번호는 한 세대 낡았다) 기준이며 **드리프트한다** — M0가 토큰 앵커로 재확인한다.

---

## 0. 무엇을 읽었나

| 층 | 대상 | 산출 |
|---|---|---|
| 결함의 자리 | `ui/src/App.tsx`(라우터 · 확장자 목록 · `<input accept>`) · `ui/src/useCopilotSocket.ts` · `ui/src/protocol.ts` | §1 |
| 선례 세 가지 | `server/orchestrator/tools.py`(`vectorworks_autopatch`) · `server/web/session.py`(업로드 슬롯 둘) | §2 |
| 대상 툴 계약 | `server/orchestrator/tools.py`(`import_lxseq_patch` 스키마·핸들러) · LXSEQ-001 `acceptance.md` | §3 |
| 헤더 규약 | `server/lxseq/parser.py` | §4 |
| 전달 계층 | `server/web/messages.py` · `server/web/app.py` | §5 |
| 등재 지점 | `server/orchestrator/tools.py` · `server/orchestrator/runner.py` · `server/tests/{test_tools,test_runner_progress}.py` | §6 |
| 선행 SPEC | `.moai/specs/SPEC-COPILOT-LXSEQ-001/{spec,plan,acceptance}.md` | 계승 계약 |

---

## 1. 오늘의 결함 — 파일 선택기와 툴 인자 사이에 길이 없다

### 1.1 첨부 라우터는 두 갈래뿐이다 `[리드]`

`ui/src/App.tsx:625-635` — 이미지 MIME이면 `uploadLayoutImage`, **그 밖이면 전부** `uploadVectorworksExport`. 그 주석이 근거를 기록한다: **2026-08-15 운영자 결정** "첨부 버튼은 하나 — 파일 종류가 목적지를 고른다". Vectorworks 경로는 `.csv/.txt/.xlsx/.mvr`을 받는다(`App.tsx:550`). `<input accept>`는 `.csv,.txt,.xlsx,.mvr` + 이미지 MIME들이다(`App.tsx:824`).

**귀결**: LX-SEQ 패치 CSV는 else 가지에 떨어져 **조용히 Vectorworks 파서에게 간다**. 이것이 본 카드가 고치는 결함이다.

주목할 점 하나 — `.csv`는 **이미** accept 목록에 있다. 그러므로 이 카드의 UI 변경은 "받는 확장자를 넓히는 일"이 아니라 "목적지를 누가 정하는가를 옮기는 일"이다.

### 1.2 UI는 툴 호출을 조립하지 않는다 `[리드]`

`ui/src/useCopilotSocket.ts:332-351`의 `sendVectorworksExportUpload`·`sendLayoutImageUpload`는 채팅 메시지를 띄우고 프로토콜 프레임을 보낼 뿐이며, 프레임 빌더(`ui/src/protocol.ts:503-510`, `:519-531`)도 마찬가지다. **툴 인자를 채우는 코드는 UI에 없다** — 그래서 이 카드의 무게중심은 서버에 있다.

### 1.3 그래서 오늘 유일한 입력 경로는 개발용 하네스다 `[리드]`

`server/tools/lxseq_e2e.py:261`이 파일 바이트를 읽어 `base64.b64encode(raw)`하고 제품 툴 스택을 직접 부른다. `import_lxseq_patch`의 호출자는 이것 하나다. LXSEQ-001은 이 사실을 스스로 적어 두었고(`REQ-LXSEQ-010`·`REQ-LXSEQ-016`), UI 전달 경로를 **카드 t10으로 위임**했다(`.moai/specs/SPEC-COPILOT-LXSEQ-001/plan.md` §A.4 ①). 본 SPEC이 그 위임을 받는다. `[문서]`

---

## 2. 저장소가 이미 가진 세 가지 선례

### 2.1 래퍼가 세션 바이트를 툴 인자에 주입한다 `[리드]`

`server/orchestrator/tools.py:2944-2964` — `vectorworks_autopatch` 핸들러가 `content = vectorworks_upload.content_base64`(:2950)로 세션 업로드를 꺼내 `arguments={"file_content_base64": content}`(:2961)로 형제 툴을 부른다. **래퍼 툴 스키마에는 `file_content_base64`가 없다.**

이 형태가 본 SPEC의 골격이다. 새로 발명할 것이 없다 — 이미 있는 형태에 "종류로 대상 툴을 고르는 한 단계"만 끼운다.

### 2.2 세션이 바이트를 담아 둔다 — 그런데 담자마자 실행한다 `[리드]`

`server/web/session.py:9655-9658` — `upload_vectorworks_export`는 `self._vectorworks_upload`(`_UploadedVectorworksExport`, `session.py:2492-2508`)에 담은 **뒤 곧바로** 고정 지시문으로 `run_instruction(...)`을 부른다.

이 즉시 실행이 LXSEQ-001이 "세션 업로드 포트 재사용"을 기각한 이유였고(`plan.md` 결정 H), 본 SPEC이 **기존 프레임을 재사용하지 않는** 이유이기도 하다(plan.md 결정 H). 저장 형태는 빌려오되 실행하는 태도는 빌려오지 않는다.

### 2.3 담고 안내만 하는 선례도 있다 `[리드]`

`server/web/session.py:9660-9688` — `upload_layout_image`는 `self._layout_image`에 담고 안내만 낸다. 리드 결정 ②("업로드는 담기만 한다")는 발명이 아니라 **이 선례를 고르는 일**이다.

세션 구성에서도 그 형태가 보인다 — `session.py:3490` 부근에서 `_vectorworks_upload`와 `_layout_image`가 나란히 초기화되고, `:3515`·`:3525`에서 각각 포트/뷰로 툴셋에 주입되며, `:3588`에서 `clear()`가 불린다. `[코드]` 신규 슬롯은 같은 자리들에 나란히 붙는다.

---

## 3. 대상 툴의 계약 — 닫혀 있고, 경로 인자가 없다

### 3.1 인자 집합 `[리드]`

`server/orchestrator/tools.py:9253-9306` — `import_lxseq_patch` 스키마. `required: ["file_content_base64"]`(:9304). 형제 인자 `action`·`name_prefix_mode`·`only_fids`·`mode_overrides`. **시트 종류 인자도, 경로 인자도 없다.** 설명문(:9264)이 이 툴은 파일 경로를 받지 않는다고 못박는다.

`additionalProperties == False`(LXSEQ-001 `acceptance.md:273`) `[문서]` — 그러므로 래퍼가 임의의 인자를 통과시키면 대상 툴이 거부한다. plan.md 결정 G(종류별 통과 화이트리스트)가 여기서 나온다.

### 3.2 저장소 전체에 경로 인자를 받는 툴은 없다 `[리드]`

툴 스키마 전수 훑기 결과 파일 시스템 경로로 파일 내용을 받는 툴은 0건이다. `query_state`의 `path`(`tools.py:7213-7231`)는 **콘솔 오브젝트 트리 주소**이지 파일 경로가 아니다. 본 SPEC은 이 성질을 깨지 않는다.

### 3.3 계승하는 안전 요구 `[문서]`

- `REQ-LXSEQ-016` `[Unwanted]` — 바이트는 **파일 판독**에서만 오고 채팅 본문 텍스트에서는 오지 않는다(붙여넣기는 개행·공백이 조용히 깨져 잘못 패치된다). 페이로드는 `source.sha256`을 실어 운영자가 원본과 대조할 수 있게 한다.
- 기각 두 건의 **상태가 서로 다르다**는 점이 중요하다. LXSEQ-001이 기각한 것은 ① 세션 업로드 포트(`upload_vectorworks_export`) 재사용 — 업로드 즉시 Vectorworks 안내 분석이 도는 까닭(`session.py:9655-9658`)이며 이 기각은 **여전히 유효**하다. ② "신규 업로드 엔드포인트는 UI 변경을 수반한다" — 이 기각은 **LXSEQ-001이 신규 툴 밖 0-diff를 유지하려던 사정 때문**이었고, 카드 t10은 그 UI 변경 자체가 목적이므로 **그 사정은 본 SPEC에 미치지 않는다**. 지나간 기각을 다시 적용하지 않도록 여기 명시해 둔다.

---

## 4. 헤더 규약 — 관용이 두 성질을 낳는다 `[코드]`

- `server/lxseq/parser.py:18` — `CANONICAL_COLUMNS` 9열 튜플이 정본이다.
- `:118` — `_normalize_header`: 양끝 공백 제거 · 내부 공백 제거 · BOM 제거 · 소문자화.
- `:122-135` — `_resolve_header_map`: 정규화 사전으로 위치 무관 대조, 빠진 열이 있으면 `MissingColumnsError(tuple(missing))`를 **던진다**.
- `:172-175` — 정규 열 밖의 열은 버리지 않고 `extra`에 원문 보존 — **관용된다**. `[리드]`

**성질 A**(포함 검사 · 전수 계수)는 이 관용에서 곧장 따라 나온다. 관용하므로 서명 대조는 동일성이 아니라 포함이고, 포함이므로 상위 집합이 두 종류에 맞을 수 있다.

**성질 B**(예외를 제어 흐름으로 쓰지 않는다)는 `MissingColumnsError`가 예외라는 사실에서 나온다. 후보별 투기적 파싱은 예외를 분기로 삼고 라우터를 파서 내부에 묶는다.

주의 — 리드가 함께 짚었듯 `parser.py:263`의 `addr_range_mismatch`는 **행 단위 값 검사**이지 헤더 비교가 아니다. 헤더 판별의 근거로 인용하면 안 된다.

---

## 5. 전달 계층 — 신규 프레임이 붙는 자리 `[코드]`

| 자리 | 좌표 | 할 일 |
|---|---|---|
| 프레임 종류 허용 목록 | `server/web/messages.py:81` · `:83` | 신규 종류 1행 |
| 프레임 검증기 | `server/web/messages.py:194`(vectorworks) · `:227`(layout image) | 신규 검증 1블록(비어 있지 않음 · 8 MiB 이하 · base64 유효) |
| 소켓 분기 | `server/web/app.py:494` · `:505` | 신규 분기 1블록 |
| 세션 핸들러 | `server/web/session.py:9655` · `:9660` | 신규 핸들러(판별 → 저장 → 넷 보고) |

기존 두 검증기는 각각 Vectorworks 확장자 목록과 이미지 MIME에 묶여 있다 — 재사용하면 LX-SEQ CSV가 남의 규칙으로 검사받는다. 그래서 신규 프레임 1종이다(plan.md 결정 H).

---

## 6. 등재는 4지점이 아니라 6지점이다 `[코드]`

| 번호 | 자리 | 좌표 |
|---|---|---|
| 1 | `TOOL_NAMES` | `server/orchestrator/tools.py:232` (현재 **34종**, `import_lxseq_patch`는 `:250`) |
| 2 | 핸들러 클로저 | 예: `import_lxseq_patch`는 `tools.py:4418` |
| 3 | `ToolDefinition` | 예: `tools.py:9226` |
| 4 | `handlers` 맵 | 예: `tools.py:9327` |
| 5 | `_TOOL_TASKS` | `server/orchestrator/runner.py:137` — 진행 표시 문구 사전 |
| 6 | 닫힌 집합 단언 | `server/tests/test_tools.py:172` (`len(names) == len(TOOL_NAMES) == 34`) |

5번을 빠뜨리면 `server/tests/test_runner_progress.py:303`·`:307`의 **전단사 단언**이 빨갛게 된다(`_TOOL_TASKS`에 없는 툴 0건 · 등록되지 않은 `_TOOL_TASKS` 항목 0건). 저장소 메모리가 "툴 등재는 4지점이 아니라 6지점"이라고 경고했고, 본 조사에서 그 두 자리를 **직접 확인했다** — 인용이 아니라 실측이다.

---

## 7. 갭 — 조사가 답하지 못한 것

| 갭 | 왜 못 닫았나 | 어디서 닫히나 |
|---|---|---|
| ~~서명 미일치 CSV의 처분~~ | **닫힘 (2026-08-22 리드 재정)** — (나)안 채택: Vectorworks를 레지스트리 행으로 등록하고 0건이면 거절 | plan.md 결정 **I** |
| ~~LX-SEQ 헤더와 Vectorworks 헤더의 실제 교차 여부~~ | **닫힘 (리드 실측)** — 9열 중 일치 3 · 불일치 6, 포함 검사가 깨끗이 가른다 | §9 (b) · `ASSUMPTION-75` 닫힘 |
| ~~표본이 저장소 안에 있는가~~ | **닫힘 (리드 실측)** — lxseq 1종 + vwx 8종이 `server/tests/fixtures/`에 실재하며, 그중 하나는 이미 만들어져 있는 **음성 대조군**이다 | §9 (a) |
| Vectorworks **위임 술어**가 `server/tests/fixtures/vwx/` 전량(12개 항목 · 페이로드 10개 · `.mvr` 포함)을 흡수하는가 | 판독기가 실물 변형을 얼마나 관대하게 받는지는 재지 않았다. 결정 I·K의 회귀 위험 크기가 여기에 달렸다. v0.2.0이 적었던 "7종"은 형제 시트 수에서 옮겨 붙은 추정값이었고 폐기한다 | **M1이 실측**. 흡수하지 못하면 안전판 `REQ-FILEARG-018` |
| 확장 형식이 프리셋 4종을 실제로 가르는가 | 형식을 넓히는 것과 그 형식이 충분한 것은 다른 주장이다 | **M1** · `AC-FILEARG-018`(합성 서명 픽스처로 증명) |
| 앱 실기에서의 실제 동작 | 정적 조사로는 알 수 없다 | M5(사용자 수행) · `AC-FILEARG-017` |

---

## 8. 좌표 드리프트

본 문서의 줄번호는 plan 작성 시점 트리 `eb436e8`(워크트리는 그 뒤 `6296af3`으로 fast-forward됐다 — 줄번호는 한 세대 낡았다) 기준이다. 리드가 넘긴 좌표 중 `import_lxseq_patch` 스키마 위치(`tools.py:9253-9306`)와 본 조사에서 관측한 `ToolDefinition(name="import_lxseq_patch")` 위치(`tools.py:9226`)에 차이가 있다 — 같은 블록의 다른 지점을 가리키거나 기준 트리가 다른 것으로 보이며, **어느 쪽도 사실 주장을 바꾸지 않는다**(스키마의 `required`가 `file_content_base64` 하나라는 사실은 그대로다). M0가 토큰 앵커로 전부 재확인하고 드리프트를 `progress.md`에 적는다.

---

## 9. 리드 실측 (2026-08-22) — `[리드]` · 재측정 금지

> **귀속.** 아래 세 측정은 모두 `origin/main` **`e7a8e90`** 트리를 `git show`로 읽어 관측했다(작업 트리가 아니다). 이후 `main`이 **`6296af3`**(t20)으로 이동했고, 리드가 `git diff --stat e7a8e90 origin/main -- "src/Lighting_Designer/02_RIG팩/" "src/Lighting_Designer/03_곡파일_Sugar/" server/tests/fixtures/`를 실행해 **빈 출력**을 확인했다 — 표본 파일은 두 커밋 사이에서 **바이트 동일**하다. 그러므로 본 절은 **`e7a8e90` 귀속이며 `6296af3`에서 불변 확인**된 것이지, 새 SHA로 조용히 재귀속한 것이 아니다. 헤더 원문을 인용하면서 기준 트리를 적지 않으면 그것은 귀속 없는 주장이다.

### (a) 표본은 실재한다 — `ASSUMPTION-75`의 전제가 충족됐다

`git ls-tree -r --name-only origin/main` 결과 중 관련 항목:

```
server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv
server/tests/fixtures/vwx/vectorworks_export_sample_with_data.csv
server/tests/fixtures/vwx/drop_dk_rigging_not_a_vectorworks_export.csv
server/tests/fixtures/vwx/vectorworks_worksheet_grid_ma3_patch.csv
server/tests/fixtures/vwx/vectorworks_worksheet_multisystem_full.csv
server/tests/fixtures/vwx/vwx_worksheet_grid_patch_ready.csv   (+3 more vwx)
```

따라서 **M1은 막히지 않는다** — 합성 헤더로 대신할 필요가 없다. 특히 `drop_dk_rigging_not_a_vectorworks_export.csv`는 **이미 만들어져 있는 음성 대조군**이다. 판별 테스트는 이것을 그대로 쓰며 별도로 만들지 않는다.

**경로 규약**: 테스트는 **`server/tests/fixtures/`**를 읽는다. `src/Lighting_Designer/`에도 같은 계열 파일이 있으나 그쪽은 파이프라인 산출물이지 테스트 픽스처가 아니다 — 테스트가 읽는 경로는 fixtures 하나뿐이다.

### (b) LX-SEQ와 Vectorworks는 충돌하지 않는다

Vectorworks export 헤더(25열):

```
UID,Fixture Name,Fixture Type,GDTF Fixture,Fixture Mode,DMX Footprint,Channel,Position,
Unit Number,Universe,DMX Address,Absolute Address,Dimmer,Circuit Number,Circuit Name,
Purpose,Color,Gobo,Focus,X,Y,Z,Rotation Z,Pan,Tilt
```

`_normalize_header` 규약(대소문자·공백·BOM 무시)으로 정규 9열과 대조한 결과:

| | 열 | 근거 |
|---|---|---|
| **있다 (3)** | `FixtureType` · `Universe` · `Position` | "Fixture Type" → `fixturetype` |
| **없다 (6)** | `FID` · `Group` · `Mode` · `Ch` · `Address` · `AddrRange` | VW는 `UID`; "Fixture Mode" → `fixturemode`(≠ `mode`); "Channel" → `channel`(≠ `ch`); "DMX Address" → `dmxaddress`(≠ `address`) |

3/9는 포함 검사를 통과시키지 못한다. 이것이 **결정 I의 회귀 위험을 LX-SEQ 쪽에서 봉쇄한다** — VW export가 `patch`로 오분류될 일은 없다. 남은 위험은 반대 방향, 즉 VW **자신의** 서명이 vwx fixture 7종의 변형을 견디느냐이며 그것은 §7의 열린 항목으로 M1이 잰다.

### (c) 후속 시트는 충돌한다 — 속성 A는 실증됐다

형제 시트 7종의 헤더 전문:

```
group.csv      : GroupNo,Name,Members,Purpose
preset-dim.csv : ID,Name,Level,Purpose
preset-col.csv : ID,Name,Value,Purpose
preset-bm.csv  : ID,Name,TargetGroup,Value
preset-pos.csv : ID,StageMeaning,TargetGroup,RecordGuide
fx.csv         : ID,Name,Attribute,WaveSteps,BaseRate,Width,Phase,Note
cue-ex.csv     : Q#,Group,Dim,COL,POS,BM,FX,FX-Rate,FX-Phase,FX-Width,I-Fade,I-Delay,P-Fade,C-Fade,B-Fade,Snap,Note
```

**t10 자신의 범위는 안전하다** — 일곱 중 어느 것도 9열 `patch` 서명을 만족하지 않는다.

**그러나 프리셋 넷은 서로 갈리지 않는다.** 넷은 `ID,Name`을 공유하고 열이 각각 넷뿐이라 포함 검사 서명으로는 분리할 수 없다. 구체적 반례: `preset-col`의 서명을 `{ID, Name, Value}`로 쓰면 `preset-bm`의 헤더(`ID,Name,TargetGroup,Value`)도 그 서명을 만족한다 → `preset-bm`은 두 서명에 맞아 `ambiguous_sheet_kind`로 거절되고 **영구히 못 싣는 파일**이 된다. 그러므로 속성 A의 충돌은 **LXSEQ-003에서 반드시 발화한다** — 이론이 아니다.

무너지는 것은 판별 전략이 아니라 **서명의 표현력**이다(spec.md §F 속성 A 말미 · 결정 J).

**M1 재현 안내.** 워크트리가 `6296af3`으로 올라오면서 `src/Lighting_Designer/02_RIG팩/`에 형제 시트 7종이, `03_곡파일_Sugar/`에 cue-ex 시트가 실재한다 — M1은 위 헤더 인용에만 기대지 않고 **실물 파일로 상위 집합 충돌을 재현할 수 있다**. 다만 테스트가 읽는 경로는 여전히 `server/tests/fixtures/`이며, `src/` 사본은 재현·확인용이다.

---

## 10. 감사 FAIL 시정 근거 (2026-08-23) — `[리드]` 관측 + `[코드]` 본 세션 재확인

> **귀속.** (a)(b)(c)는 리드가 이 워크트리에서 직접 읽어 넘긴 관측이다. (d)(e)는 본 세션이 같은 워크트리에서 직접 실행해 확인했다 — 인용이 아니라 실측이다.

### (a) 판독기는 확장자를 보지 않는다 — zip은 매직 바이트로 갈린다 `[리드]`

`server/vwx/reader.py:350-360` (`read`)의 docstring이 스스로 밝힌다: *"확장자를 전혀 참조하지 않는다 — xlsx는 ZIP 매직 바이트(`PK`)로, delimiter는 별칭 매칭 점수로 판별한다."* 이어서 `if data[:2] == _XLSX_MAGIC:`.

**귀결**: `.mvr`·`.xlsx`는 **헤더 행이 아예 없다**. 열 집합 서명으로 재는 판별기는 이런 바이트를 필연적으로 `unknown_sheet_kind`로 떨어뜨린다 — 그것이 감사 **B1**이다. (다)안을 기각한 사유("살아 있는 기능을 회수한다")가 (나)안 안에서 되살아난다.

### (b) 헤더 행은 탐색된다 — 1행이라는 보장이 없다 `[리드]`

`server/vwx/reader.py:158 _best_header_candidate(rows)`가 헤더 후보를 **점수로 고르고**, `:212`·`:254`에서 호출된다. 구분자도 별칭 매칭 점수로 정한다((a)의 docstring).

**귀결**: 열 집합 서명(정확 열 집합 · 포함·배제 쌍)은 헤더의 **위치**도 **구분자**도 표현하지 못한다 — 감사 **B2**.

### (c) 서명 소유자는 `columns.py`가 아니라 호출 지점이다 `[리드]` `[코드]`

```
columns.py:88:def has_address_family(headers: list[str]) -> bool:
reader.py:21:from server.vwx.columns import has_address_family, match_count
reader.py:286:    if not has_address_family(header):   ← header = rows[header_index] (탐색된 헤더)
```

본 세션이 `reader.py:284-290`을 직접 읽어 확인했다 — `header = rows[header_index]` 다음 줄이 `if not has_address_family(header):`다. `columns.py`는 별칭 표이고 스스로 정본이 아니라고 밝힌다. **판정**은 그 술어를 **탐색된 헤더에 적용하는 호출 지점**에 있다. v0.2.0이 `columns.py`를 VW 서명 정본이라 적은 것은 오귀속이었다 — 감사 **B3**. 정정된 좌표는 `reader.py:286`이다.

### (d) 실물 `.mvr`은 315,155 바이트다 `[코드]`

```
$ wc -c server/tests/fixtures/vwx/demoshow_grandma3.mvr
  315155
```

zip 아카이브이며 헤더 행이 없다. `AC-FILEARG-022`가 이 파일이 `unknown_sheet_kind`가 **아님**을 못박는다.

### (e) vwx fixture는 12개 항목 · 페이로드 10개다 `[코드]`

```
$ ls -1 server/tests/fixtures/vwx/ | wc -l
      12
$ ls -1 server/tests/fixtures/vwx/
demoshow_grandma3.mvr
drop_dk_rigging_not_a_vectorworks_export.csv
README.md
stage1_contract_snapshot.json
synthetic_path_b_worksheet_grid.csv
vectorworks_export_instrument_data_no_header.txt
vectorworks_export_sample_with_data.csv
vectorworks_worksheet_absolute_address_only.csv
vectorworks_worksheet_grid_ma3_patch.csv
vectorworks_worksheet_multisystem_full.csv
vwx_worksheet_grid_from_screenshot.csv
vwx_worksheet_grid_patch_ready.csv
```

**분해**: 업로드 페이로드 **10개**(`.csv` 8 · `.txt` 1 · `.mvr` 1) + 비페이로드 **2개**(`README.md` · `stage1_contract_snapshot.json`). v0.2.0이 적었던 "vwx fixture 7종"은 형제 시트 7종에서 옮겨 붙은 **추정값**이었다 — 실측과 다르므로 폐기한다(감사 **D2**).

**핵심 표본 둘**: `vectorworks_export_instrument_data_no_header.txt`(파일 이름이 스스로 밝히듯 **헤더가 없다**)와 `demoshow_grandma3.mvr`(zip). 열 집합 서명이었다면 **둘 다 떨어졌을 것**이고, 그것이 B1이 지적한 회수다. 두 파일은 위임 술어의 필요성을 파일 이름만으로도 증명한다.

### (f) 실물 패치 CSV는 7,258 바이트다 — `ASSUMPTION-77` 닫힘 `[코드]`

```
$ wc -c server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv
    7258
```

약 **7 KB**. 8 MiB 상한은 그 약 **1,150배**다. v0.2.0의 "수십 KB 규모"는 한 자릿수 오차였고, 정정하면 결론이 바뀌는 것이 아니라 **더 강해진다**. `ASSUMPTION-77`을 **POSITIVE로 닫는다**.

---

## 11. 델타 재감사 FAIL 0.62 — F2의 뿌리 (2026-08-23)

> **귀속.** F2 측정과 두 후보 비교, 장바구니 대조군, README 확인은 리드가 이 워크트리에서 실행한 것이다 — `[리드]`. `.mvr` 소유자 좌표와 임계 상수는 본 세션이 직접 확인했다 — `[코드]`.

### 11.1 우리는 다른 물음에 답하는 함수를 판별자로 썼다 — 관대함이 아니라 축이 다르다 `[리드]`

`has_address_family`가 답하는 물음은 **"이 바이트에서 패치를 뽑을 수 있는가"**(사용성)이고, 레지스트리가 묻는 물음은 **"이것은 무엇인가"**(신원)다. 축이 다르므로 술어는 **양쪽으로 다 틀린다**.

| 파일 | 패치 가능? | 무엇인가? | `has_address_family` | 결과 |
|---|---|---|---|---|
| LX-SEQ 패치 CSV | 그래 보인다(9열 중 7열 해소) | **LX-SEQ** | **True** | **F2 — 남의 종류 파일을 자기 것이라 주장** |
| `vwx_worksheet_grid_from_screenshot.csv` | 아니다(주소 계열 열 없음) | **Vectorworks** | **False** | 진짜 VW 파일을 놓친다 |

측정:

```
LX-SEQ header: FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position
has_address_family = True   match_count = 7   rows = 86
  FID→fixture_id  FixtureType→instrument_type  Mode→mode  Ch→channel
  Universe→universe  Address→absolute_address  Position→position
  Group→None  AddrRange→None          ← LX-SEQ 고유는 이 둘뿐
```

**우연한 유사가 아니다.** 둘 다 픽스처·유니버스·주소·모드를 기술하므로 LX-SEQ는 VW **어휘의 부분집합**이다. 그러므로 **어떤 주소 계열 검사로도 둘을 가를 수 없다** — 임계를 올리든 열을 더하든 같은 축 위에 있는 한 결과는 같다.

### 11.2 두 후보를 실측했다 — 정확히 한 파일 부류에서 갈린다 `[리드]`

```
vectorworks_export_instrument_data_no_header.txt
  _best_header_candidate → idx = -1        (신원 후보: False)
  ReadResult.header      → 비어 있지 않음    (느슨한 후보: True)
  records = 17, delimiter = '\t'
```

원인은 `_process_rows`(`reader.py:253-266`)의 **균일폭 폴백**이다 — 헤더 탐색이 실패해도 탭 구분 + 균일폭이면 `col_0..` 헤더를 지어내고 전 행을 데이터로 삼는다.

**날조 대조군을 느슨한 후보에 쏜 결과:**

```
reader.read(b"milk\t2\t3000\neggs\t1\t5000\nbread\t3\t2500\n")
  header 비어 있음 = False    records = 3    path_kind = A    failures = []
```

**장바구니 목록이 실패 0건으로 Vectorworks가 된다.** 균일폭 폴백은 VW 어휘가 아니라 **모양**(탭 + 균일폭)으로 받으므로 `_MIN_HEADER_ALIAS_MATCHES`(`reader.py:43`, 값 **2** — 본 세션 `[코드]` 확인)를 **통과하는 것이 아니라 우회한다**. 그래서 임계 고정(AC-027)만으로는 이 구멍이 막히지 않으며, 탭 축 날조 대조군(AC-028)이 따로 필요하다.

### 11.3 무엇이 결정을 갈랐나 — 헤더 없는 VW 파일은 살아 있는 능력이 아니다 `[리드]`

`server/tests/fixtures/vwx/README.md:84-95`(본 세션 `[코드]` 직접 확인):

> 헤더 없는 경로 A 파일이 … 이제는 파일 단위 판정 1건(`headerless_path_a_export`) + 실행 가능한 해결책("Export field names as first record"를 켜고 재수출)으로 압축된다. … **긍정** 증거로 기록한다 — 실패가 아니다.

그 파일은 **오늘 패치를 만들어 내지 못한다**. 시스템의 올바른 답은 재수출 안내다. 장바구니 목록과 그 실물 VW 파일은 **바이트 동일한 `headerless_path_a_export` 판정**을 받는다(해소 열 0/28 · 0/3).

**그러므로 좁히기는 능력을 잃지 않는다 — 문구 하나를 잃는다.** 그 문구를 `unknown_sheet_kind` 경로의 **조건부 힌트**로 복원한다(REQ-FILEARG-023). 조건절이 없으면 오늘처럼 **장바구니 목록에게도 Vectorworks에서 재수출하라고 말한다**.

**기각 근거.** (ㄱ) 느슨한 술어 유지 — 전제가 "장바구니 목록은 VW 안에서 안전하게 죽는다"였으나 **진짜 VW 파일도 같은 자리에서 같은 이유로 죽는다**. 둘 다 받아 얻는 것이 없고 판별만 뒤로 미룬다. (ㄷ) 운영자 선택 — 입력이 **어느 쪽이든 쓸 수 없는데** 두 종류 중 고르라고 하는 것이다. 필요한 것은 메뉴가 아니라 재수출 지시다.

### 11.4 12개 표의 신원 열 재계산 — 이전 표는 무효다

v0.3.0의 시뮬레이션 표는 **사용성 술어**로 계산한 값이라 무효다. 신원 축(`_best_header_candidate >= 0` **AND NOT** 다른 행 서명)으로 다시 계산한다.

| 파일 | 신원 술어 | 분류 | 비고 |
|---|---|---|---|
| `demoshow_grandma3.mvr` | zip 경로(`tools.py:2860`) | `vectorworks` | 315,155 B `[코드]` |
| `vectorworks_export_sample_with_data.csv` | True | `vectorworks` | 정상 경로 |
| `vectorworks_worksheet_absolute_address_only.csv` | True 기대 | `vectorworks` | M1 실측 |
| `vectorworks_worksheet_grid_ma3_patch.csv` | True 기대 | `vectorworks` | M1 실측 |
| `vectorworks_worksheet_multisystem_full.csv` | True 기대 | `vectorworks` | M1 실측 |
| `vwx_worksheet_grid_from_screenshot.csv` | True 기대 | `vectorworks` | **사용성 술어로는 False였다**(11.1) |
| `vwx_worksheet_grid_patch_ready.csv` | True 기대 | `vectorworks` | M1 실측 |
| `synthetic_path_b_worksheet_grid.csv` | True 기대 | `vectorworks` | M1 실측 |
| `drop_dk_rigging_not_a_vectorworks_export.csv` | False | `unknown_sheet_kind` | 음성 대조군 |
| `vectorworks_export_instrument_data_no_header.txt` | **False**(idx = -1) | **`unknown_sheet_kind`** | **문구는 조건부 힌트로 보존**(AC-029) — 결정 L의 의도된 결과 |
| `README.md` · `stage1_contract_snapshot.json` | — | 페이로드 아님 | 대상 제외 |

"기대"로 표시한 칸은 **아직 재지 않았다** — M1이 실측하며, 여기 적힌 것은 예측이지 관측이 아니다.

### 11.5 F1 — `.mvr` 분기는 `reader.py`에 없다 · 좌표 정정 `[코드]`

**아래는 2026-08-23 이 워크트리에서 재실행한 출력이다** — v0.4.0의 블록은 명령과 출력이 어긋나 있었다(`2859,2860p`를 인용하면서 결정 줄인 2861을 출력에 담았다). 명령과 출력을 맞춰 다시 싣는다.

```
$ grep -c "mvr\|MVR" server/vwx/reader.py
0
$ sed -n '2859,2862p' server/orchestrator/tools.py
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
                is_mvr = SCENE_ENTRY in archive.namelist()
        except zipfile.BadZipFile:
```

**결정 줄은 `2861`**(`is_mvr = SCENE_ENTRY in archive.namelist()`)이고, 인용 범위는 **`2860-2861`**이다(2860이 `with zipfile.ZipFile(...) as archive:`). v0.4.0이 쓴 `2859-2860`은 결정 줄을 **빗나갔다** — 2859는 `try:`다.

**이 하나가 왜 차단이었나.** 17개 좌표 중 16개가 맞았고 **틀린 하나가 하필 F1이 고치겠다고 약속한 좌표**였으며, `AC-FILEARG-022` ④가 그 좌표를 **인수 근거**로 쓰고 있었다 — 그대로면 그 AC는 통과할 수 없었다. 문서 7곳(spec 3 · research 2 · acceptance 1 · progress 1)을 전부 `2860-2861`로 고쳤다.

**`.mvr`이 `_best_header_candidate`에 도달하지 못하는 이유** — `server/vwx/reader.py:360`:

```
$ sed -n '358,362p' server/vwx/reader.py
    """
    available = OPENPYXL_AVAILABLE if _openpyxl_available is None else _openpyxl_available
    if data[:2] == _XLSX_MAGIC:
        if not available:
            return ReadResult(
```

`PK` 매직이면 `_read_xlsx` 경로로 갈라지므로 `_process_rows`가 호출되지 않는다. 그래서 술어는 **두 갈래 전역 함수**여야 한다(D1 · `design.md` §4). 미설치 시 `return ReadResult(...)` — **예외가 아니라 구조적 정상 반환**이며, 이것이 `design.md` §4 표의 결과 ④(`unapproved_dependency`)다.

**[HARD] 다만 이 결과는 이 SPEC의 것이 아니다(v1.0.0 실측 정정).** 신원 술어의 zip 갈래는 `zipfile.ZipFile`이 **열리는지만** 묻고 곧장 True를 반환하므로, `.mvr`도 `.xlsx`도 신원 단계에서는 `_read_xlsx`에 닿지 않는다. 결과 ④가 실제로 나는 곳은 `SPEC-COPILOT-SHEETPIPE-001`의 **뒷단 판독기**이며, openpyxl 없는 환경에서 `.xlsx`가 거기까지 갔을 때다 — 그래서 A의 결과표는 ④를 미도달 칸으로 남기지 않고 **B 소관으로 넘긴다**(거기서 안 나는 것이 아니라 거기 것이 아니다). `.xlsx` 신원을 True로 채운 재정이 되살린 것은 **④가 아니라 그 앞의 도달성**이다 — **"신원이 참이 됐다"와 "그 뒤의 갈래가 실행된다"는 다른 문장이고, 술어가 조기 반환하면 참이어도 뒤가 안 돈다.** 이 문장이 재정문에서 두 사람을 거쳐 검증 없이 내려왔고, 코드를 읽은 구현자가 되잡았다.

소유자는 `server/orchestrator/tools.py:2860-2861`과 `server/vwx/mvr.py`다. v0.3.0이 "판독기에 위임한다"고 쓴 것은 **그 판독기가 무엇을 판정하는지 재지 않고 쓴 문장**이며, B3와 같은 부류의 오귀속이 **두 번째**였다. 위임 계약의 전체 형상(두 갈래 · 결과 4종 · openpyxl 두 경로)은 `design.md` §4와 `REQ-FILEARG-021`이 소유한다(v0.7.0에서 `spec.md` §G.4가 `design.md` §4로 이동했다 — 이 문장은 v0.8.0에서 그 이동을 반영해 고쳤다).
