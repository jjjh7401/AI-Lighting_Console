# SPEC-COPILOT-SHEETPIPE-001 — 진행 기록 (progress)

문서 상태: **in-progress** (updated 2026-08-24 — M1+M2 실행됨) · 직전 개정 v0.3.0, 2026-08-24 · **Tier M · 통과 임계 0.80** · 칸반 카드 t10 · **분할 B(전달경로)**

> **읽는 순서.** ① `spec.md` §A(개요 · 사전 확정 사실) → ② `spec.md` §F(세 성질 — **함정이 여기 있다**) → ③ `plan.md` §A.1(뒤집힐 수 있는 결정 넷) · §A.4(**닫힌** 결정 ① — A의 `target` 태그 재정) → ④ `spec.md` §G(등재 7지점) → ⑤ `acceptance.md` §C.
>
> **A를 먼저 읽어야 한다.** B는 판별하지 않는다. 레지스트리 · 술어 · 신원/사용성 축 · `.mvr` 위임 계약은 전부 `SPEC-COPILOT-FILEARG-001`이 소유하며, 그 `design.md` §1~§4가 설계 논증을 든다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
spec_id: SPEC-COPILOT-SHEETPIPE-001
tier: M
pass_threshold: 0.80
phase: plan
artifact_set:
  required: [spec.md, plan.md, acceptance.md]   # Tier M = 3종
  emitted:  [spec.md, plan.md, acceptance.md]
  progress_md: emitted (Tier 집합에 포함되지 않음 — A의 감사 A1이 잡은 오산)
counts:
  req: 9      # grep -c "^- \*\*REQ-SHEETPIPE-" spec.md
  ac: 11      # grep -c "^### AC-SHEETPIPE-" acceptance.md
  milestones: 3
  decisions_resolved: 8      # plan.md §A.3 (A~H) — B 자신의 결정
  clarification_markers: 0   # plan.md §A.4 ① 2026-08-23 A 재정으로 닫힘
lead_allocation:
  req: 8      # 실측 9 — +1의 사유는 spec.md §B 머리의 [HARD] 주가 소유한다
  ac: 11      # 일치
baseline_measured: null      # 의도적으로 비어 있음 — M0가 이 워크트리에서 직접 잰다
assumptions_open: [ASSUMPTION-78, ASSUMPTION-79]
mutation_ledger_planned: 8   # AC-003 · 004 · 005(문구 :555) · 005(앵커 주석) · 006 · 009 · 010 · 011
plan_audit:
  verdict: PASS-WITH-DEBT
  score: 0.91                # Tier M 임계 0.80
  must_pass: 7/7
  debts_closed: 6            # D1~D6 (v0.3.0) — 전부 문서 편집, 코드 변경 0
```

### 좌표 실측 기록 (본 세션 · `grep`)

`spec.md` §H가 좌표표를 소유한다. 본 세션에서 **11건을 전수 재측정**했고, 정정 4건이 나왔다:

| 대상 | 앞선 기록 | 실측 | 왜 어긋났나 |
|---|---|---|---|
| `_UploadedVectorworksExport` | `2492` | **`2493`** | `@dataclass` 데코레이터를 클래스 시작으로 셈 |
| `LayoutImageUpload` | `2511` | **`2512`** | 같음 |
| `protocol.ts` 빌더 둘 | `502` · `517` (본 세션 초안) | **`503`** · **`519`** | `sed` 출력에서 눈으로 셈 — `grep`으로 재서 잡음 |
| ~~`test_overlap_preserve.py`의 `base..HEAD`~~ | ~~`427` · `446` · `456`~~ | **철회 — 아래 참조** | 내 정정이 틀렸다 |

**철회 (v0.2.0) — 내가 A를 고친 것이 틀렸다.** v0.1.0은 A의 `:446`을 두고 "그 파일에 `base..HEAD`가 없다"고 적었다. **거짓이다.** `:446`은 `_PRECHK_BASE`를 쓰는 진짜 `..HEAD` 지점이며, 내 grep이 `{base}..HEAD`라는 **내 변수명**만 훑어 보이지 않았을 뿐이다. 리드가 변수명을 벗기고 재서 확정한 총계는 **22곳**이다:

```
grep -cE '\.\.HEAD' server/tests/test_overlap_preserve.py   → 22
```

내 셋(`427 · 456 · 464`)도 A의 셋(`427 · 446 · 456`)도 **둘 다 부분집합**이었고, 각자 자기 변수명만 매칭했기 때문이다. **좁은 패턴의 히트 수는 총계가 아니라 하한이다** — 이것은 §C.0 계수 규약 2(부정 grep은 부재의 증거가 아니다)의 세 번째 얼굴이며, A가 자기 함정 목록에 그 형태로 싣는다. 본 SPEC의 두 인용(`plan.md` §A.5 · `AC-SHEETPIPE-011`)은 낱개 좌표를 버리고 **총계와 그것을 낸 명령**으로 바꿨다.

**정정 하나 더 — 인용 경로.** A는 헤더 없는 내보내기 근거를 `README.md:85-95`로 적었다. 디렉터리가 없어 저장소 루트의 다른 문서(안전 게이트 절)로 풀린다. 실제 원본은 **`server/tests/fixtures/vwx/README.md:84-95`**다.

**교훈 세 줄** — ① **좌표는 눈이 아니라 `grep`이 낸다.** ② **결정적인 줄을 인용하고, 범위는 양끝을 잰다.** ③ **좁은 패턴의 히트 수는 총계가 아니라 하한이다** — 남의 좌표를 정정하기 전에 내 패턴이 그 사람의 표기까지 덮는지 먼저 본다(위 철회가 그 값을 치렀다).

### 등재 지점 실측 (본 세션)

`vectorworks_autopatch`를 추적해 **7지점**으로 확정했다(`spec.md` §G가 표와 배제 기준을 소유). 앞선 SPEC의 "4지점"(`REQ-LXSEQ-010`)은 낡았고, 빠진 셋 중 둘(`test_tools.py`의 리터럴 · 트립와이어)은 **툴 이름을 문자열로 담지 않아 첫 grep에 영원히 걸리지 않는다**.

독립 확인: `TOOL_NAMES` 파싱 결과 **34개**이며 `upload_vectorworks_export`는 **그 안에 없다**. 이 한 번의 측정이 두 가지를 동시에 준다 — `test_tools.py:172`의 리터럴 `34`가 옳다는 것과, A 레지스트리 `target` 열이 **두 종을 담는다**는 것(`plan.md` §A.4 ①의 근거이자, 그 재정의 리드측 독립 확인과 일치한다).

### 채무 정리 실측 (v0.3.0 · plan-audit 0.91)

| 채무 | 명령 | 결과 |
|---|---|---|
| **D1** 예견인가 사고인가 | `git log -1 --format='%s' 43b1b04` | `feat(SPEC-COPILOT-IMGLAYOUT-001): M4+M5 …` — **`fix`가 아니다** |
| **D1** docstring 서법 | `sed -n '3360,3361p' server/web/session.py` | `would therefore freeze` — **가정법** |
| **D1** 아티팩트 언급 | `grep -rc 'LayoutImageUploadView\|freeze\|얼어' .moai/specs/SPEC-COPILOT-IMGLAYOUT-001/` | `contract.md:0` · `spec.md:0` — **0건** |
| **D2** 형제 문구 | `grep -n 'Vectorworks' ui/src/App.tsx` | `:551` · `:555` · `:559` — **셋** |
| **D2** vitest 델타 | `grep -rln 'Vectorworks export는' ui/src/` | `App.tsx` 하나 — 테스트 단언 **0건** |
| **D3** 앵커 판별력 | `grep -c 'SPEC-COPILOT-SHEETPIPE-001' ui/src/App.tsx` | **0** — 검사가 오늘 빨갛다(판별력 있음) |
| **D5** 이름 변경 비용 | `git grep -l 'vectorworks_export_upload'` | **16파일**(코드·계약 8 + 문서 8) |
| **D5** 빌더 수 | `grep -c 'export function buildVectorworksExportUpload' ui/src/protocol.ts` | **1** — "빌더 둘"은 하나 많았다 |

**D1이 남긴 일반형은 §C.0 규약 6이 든다.** 이 카드에서 **세 번째 형태**다 — `columns.py` 오귀속(옮겨간 문서를 가리킴) · `:446` 철회(좁은 패턴을 총계로 읽음) · 그리고 이번(방어 코드의 설명문을 역사로 읽음). 셋 다 **읽은 것의 종류를 잘못 판정한** 결과다.

### 미해소 항목

| 항목 | 상태 | 해소 시점 |
|---|---|---|
| A의 태그 재정이 **A 쪽 코드에** 반영됐는가 | 미확인 | M0 5 — 재정은 문서에 적힌 것이지 A의 코드에 있는 것이 아니다 |
| `ASSUMPTION-78` — A가 이 워크트리에 있는가 | 미검증 | M0 ① |
| `ASSUMPTION-79` — 오늘 되던 업로드가 거절되는가 | 미검증 | 운영자 이력이 있어야 닫힌다 — **B에서 닫지 않는다** |
| `baseline_measured` | 미측정 | M0 ③ |

---

## §E.2 Run-phase Evidence

> **워크트리 · HEAD 실측.** `git rev-parse --show-toplevel` →
> `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/agent-a6b09215de55701b2`
> — **의도한 `t10b`가 아니다.** 이 보드에서 반복돼 온 형태이므로, 지시대로 있는
> 자리에서 `3ffda31`을 기반으로 일하고 브랜치
> `WT-sheetpipe-attachment-pipe`를 밀었다. 착수 시점
> `git rev-parse --short HEAD` → **`3ffda31`** (= `origin/main`).

### E.2.0 M0 — 착수 게이트 (`AC-SHEETPIPE-001`)

| 항 | 명령 | 관측 | 판정 |
|---|---|---|---|
| ① A 실재 | `ls server/sheets/` · `uv run pytest server/tests/test_sheets_registry.py -q` | `__init__.py` · `registry.py` 존재 · 스위트 초록 | **PASS** |
| ② 좌표 11건 | `grep -n` 전수 (E.2.1) | **정정 12건** — 전부 재측정해 아래 표에 반영 | **PASS** |
| ③ 등재 7지점 | §G 세 명령 (E.2.2) | 7지점 확인 · 6·7번이 첫 명령에 안 걸림도 확인 | **PASS** |
| ④ 기준선 2종 | 아래 | 이 워크트리에서 직접 측정 · 기존 실패 **0건** | **PASS** |
| ⑤ A 태그 재정 반영 | `grep -n 'HANDLER_TAG\|kind_tag' server/sheets/registry.py` | `Handler(kind_tag, name)` · `HANDLER_TAG_TOOL` · `HANDLER_TAG_SESSION_METHOD` 실재하고 `_handler_error`가 태그별 등록부(`TOOL_NAMES` vs `ChatSession` 속성)를 본다 | **PASS** |

**측정된 기준선** (이 워크트리 · `3ffda31` · `uv sync` + `npm --prefix ui install` 직후):

```
$ pgrep -fl app_gma3
(출력 없음 — 콘솔 미실행)

$ uv run pytest server/tests -q
9974 passed, 12 skipped, 1 warning in 150.42s (0:02:30)

$ npm --prefix ui run test
Test Files  20 passed (20)
     Tests  496 passed (496)
```

기존 실패 **0건**이므로 원인별 분류는 공란이다. 참고로 리드가 다른 트리에서 잰
값(`9974 / 12 / 0`, `496`)과 **일치했다** — 그러나 이 값은 그 일치를 근거로
적은 것이 아니라 이 트리에서 직접 잰 것이다.

### E.2.1 좌표 재측정 — 정정 12건

`spec.md` §H가 든 `session.py` · `tools.py` 좌표 다수가 **낡아 있었다**. 원인은
잘못 잰 것이 아니라 **시간**이다: 그 값들은 `session.py`가 76~126줄,
`tools.py`가 38줄 짧던 세대에서 잰 것이고 그 뒤 `origin/main`이 움직였다.
`spec.md` §C.0 규약 4("움직이는 대상은 수치로 못박지 않는다")가 정확히 이 경우를
가리키는데, §H의 좌표표 자신이 그 규약의 적용 대상이었다.

| 대상 | §H 기록 | 실측 (`3ffda31`) |
|---|---|---|
| `_UploadedVectorworksExport` | `session.py:2493` | **`:2569`** |
| `LayoutImageUpload` | `session.py:2512` | **`:2588`** |
| `_LayoutImageUploadView` | `session.py:3353` | **`:3429`** |
| `_VECTORWORKS_UPLOAD_INSTRUCTION` | `session.py:3157` | **`:3233`** |
| `build_toolset` 호출부 | `session.py:3508` | **`:3584`** |
| `ChatSession` 클래스 | `session.py:3405` | **`:3481`** |
| `upload_vectorworks_export` · 지시문 | `session.py:9655` · `:9658` | **`:9781`** · **`:9784`** |
| `upload_layout_image` | `session.py:9660` | **`:9786`** |
| `_record_history` · 호출부 둘 | `session.py:9719` · `:9639` · `:9650` | **`:9845`** · **`:9765`** · **`:9776`** |
| `ToolDefinition(vectorworks_autopatch)` | `tools.py:7615` | **`:7653`** |
| `handlers` 맵 | `tools.py:9321` | **`:9359`** |
| 트립와이어 두 상수 | `test_songcue_bundle.py:215` · `:282` | **`:244`** · **`:311`** |

**어긋나지 않은 것**(재측정으로 확인, 눈으로 넘기지 않았다): `tools.py:244`
(`TOOL_NAMES`) · `:1609`(`build_toolset`) · `:2944`·`:2950`·`:2961`(래퍼 선례) ·
`runner.py:137`·`:148` · `test_tools.py:172` · `parser.py:112`·`:162` ·
`app.py:494` · `messages.py:194-219` · `test_overlap_preserve.py:52`·`:186` ·
UI 좌표 **전부**(`App.tsx:551`·`:555`·`:559`·`:629` ·
`useCopilotSocket.ts:336` · `protocol.ts:503`·`:519`).

```
$ grep -cE '\.\.HEAD' server/tests/test_overlap_preserve.py
22
```

### E.2.2 등재 7지점 (`AC-SHEETPIPE-008`)

세 측정 명령을 전부 돌렸다. **6·7번이 첫 명령에 걸리지 않는다는 사실**을 함께
확인했다 — 첫 명령의 출력에 `test_tools.py:172`(리터럴)도
`test_songcue_bundle.py:244`(트립와이어)도 없다. 둘 다 툴 이름을 문자열로 담지
않기 때문이며, 그것이 앞선 SPEC이 두 자리를 반복해 빠뜨린 이유다.

| # | 지점 | B가 적은 것 | 확인 |
|---|---|---|---|
| 1 | `TOOL_NAMES` | `"import_uploaded_sheet",` | `len(TOOL_NAMES) == 35` |
| 2 | 핸들러 클로저 | `def import_uploaded_sheet(...)` | 디스패치로 확인 |
| 3 | `ToolDefinition` | 스키마 + 설명문 | `advertised == set(TOOL_NAMES)` |
| 4 | `handlers` 맵 | `"import_uploaded_sheet": import_uploaded_sheet,` | 디스패치로 확인 |
| 5 | `_TOOL_TASKS` | `"올라온 시트 읽어 넘김"` | `test_runner_progress` 전단사 초록 |
| 6 | 총 개수 리터럴 | **`34` → `35`** | `test_tools.py:172` |
| 7 | 헝크 트립와이어 | 시작점 **65 → 67** 통째 재생성 | 아래 |

**7번의 진짜 불변식은 재측정했다** — 전례로 미루지 않았다:

```
starts      = 67개
protected   = ((234, 238), (524, 569))
violations  = []          ← 침범 0건
```

배선 두 곳이 더 붙는다(§G 하단이 예고한 짝): `build_toolset` 시그니처
(`uploaded_sheet: UploadedSheetPort | None = None`)와 호출부
(`uploaded_sheet=_UploadedSheetView(self)`).

**⑤ 스위트를 두 번 돌았다.** 등재 직후 한 번 — 7번이 그때는 **초록**이었다
(미커밋이라 `base..HEAD`의 시야 밖). M1+M2 커밋(`5102032`) 직후 다시 돌려
그때 **빨개졌고**, 재생성 뒤(`86ae6cf`) 초록으로 돌아왔다. 이 순서 자체가
"커밋 전 초록은 구조적으로 보장된 거짓 신호"의 실측이다.

### E.2.3 스위트 델타 (기준선 대조)

| 스위트 | 기준선 | 최종 (`86ae6cf`) | 델타 | 대조 |
|---|---|---|---|---|
| `uv run pytest server/tests -q` | 9974 passed / 12 skipped / 0 failed | **10009 passed / 12 skipped / 0 failed** | **+35** | `test_sheet_pipe.py` **34** + `test_web_app.py` **+1** = **35** ✅ |
| `npm --prefix ui run test` | 496 passed (20 files) | **500 passed (21 files)** | **+4** | `attachmentCopy.test.ts` **4** = 대조군 1 + 소스 2 + 앵커 1 ✅ |

감소 **0** · 신규 실패 **0**.

> **[HARD] 최종 pytest 실행 중 콘솔이 떠 있었다.** 기준선 측정 시점에는
> `pgrep -fl app_gma3`가 비었으나 최종 실행 직전 확인에서는
> `47006 … app_gma3 HOSTTYPE=onPC`가 잡혔다. 스위트는 그 상태에서도 초록이므로
> 거짓 빨강은 없었지만, **초록이 콘솔 부재 조건에서 난 것이 아니라는 사실**을
> 숨기지 않고 적는다. 기준선(9974)은 콘솔이 없을 때 잰 값이다.

### E.2.4 AC별 판정

| AC | 명령 | 관측 | 판정 |
|---|---|---|---|
| `001` | E.2.0 표 | ①~⑤ 전부 통과 조건 충족 | **PASS** |
| `002` | `pytest server/tests/test_sheet_pipe.py -q -k "slot"` | `4 passed` | **PASS** |
| `003` | `... -k "late_upload_visible"` | `1 passed` · 뮤테이션이 죽인다(E.2.5) | **PASS** |
| `004` | `... -k "no_execution_on_sheet_upload"` | `2 passed` (실행 0회 + 파싱 정확히 1회) | **PASS** |
| `005` | `... -k "vectorworks_branch_unchanged"` + grep 셋 + `git diff --stat` | `2 passed` · ④ 빈 출력 · ⑤ `0`,`0` · ⑥ `1` | **PASS** |
| `006` | `... -k "upload_notice"` | `4 passed` (④ 픽스처 판별력 실측 포함) | **PASS** |
| `007` | `... -k "wrapper_injects"` | `3 passed` | **PASS** |
| `008` | §G 세 명령 + 전체 스위트 | 7지점 · 침범 0 · 스위트 2회 | **PASS** |
| `009` | `... -k "wrapper_schema"` | `4 passed` | **PASS** |
| `010` | `... -k "wrapper_refusal"` | `6 passed` | **PASS** |
| `011` | 커밋 → 게이트 → 직접 diff | `41 passed` · 직접 diff **빈 출력** @ `86ae6cf` | **PASS** |

### E.2.5 뮤테이션 원장 — 8건 실측

`acceptance.md` §D 4는 "6건"이라 적었으나 `progress.md` §E.1
`mutation_ledger_planned`는 **8**이고 `AC-SHEETPIPE-005`가 자기 몸에서 뮤테이션
둘을 **필수**로 요구한다. 많은 쪽을 따랐다(소견 F-4).

| # | AC | 뮤테이션 | 관측 | 판별력 |
|---|---|---|---|---|
| 1 | `003` | 읽기 통과 뷰 제거 → 필드 직접 전달 | `AC-003` **FAIL** · `AC-002` 4건 **전부 초록** | ✅ 두 기준이 다른 것을 잰다 |
| 2 | `004` | 업로드 직후 `run_instruction` 호출 | `test_no_execution_on_sheet_upload` **FAIL** | ✅ |
| 3 | `005`⑤ | `:555` 문구를 원래대로 되돌림 | vitest `App.tsx` 소스 단언 **FAIL** · grep 값 `0 → 1` | ✅ |
| 4 | `005`⑥ | 라우터 옆 앵커 토큰 삭제 | vitest 앵커 단언 **FAIL** · grep 값 `1 → 0` | ✅ |
| 5 | `006` | 통 이름 제거 → 맨 숫자 하나 | `upload_notice` **2건 FAIL** | ✅ |
| 6 | `009` | 스키마에 `file_content_base64` 추가 | `wrapper_schema_has_no_byte_argument` **FAIL** | ✅ |
| 7 | `010` | 빈 슬롯에서 거절 대신 빈 바이트로 대상 툴 호출 | `wrapper_refusal` **3건 FAIL** | ✅ |
| 8 | `011` | `server/web/preview.py` 한 줄 수정 | **아래 두 상태** | ✅ |

**8번의 두 상태 — 그리고 전제 확인이 먼저다.**

```
0) git diff --stat 3ffda31..HEAD -- server/web/preview.py   (뮤테이션 전)
   → 빈 출력  ← 대상이 깨끗하므로 이 뮤테이션은 판별력이 있다

커밋하지 않고:  test_overlap_preserve.py → 41 passed   · 직접 diff → 빈 출력
                ^^^^^^^^^^^^^^ 이 초록이 이 AC가 막는 거짓 신호다

커밋한 뒤:      test_overlap_preserve.py → 1 failed    · 직접 diff → preview.py | 2 ++
```

뮤테이션 커밋은 즉시 되돌렸다(`git reset HEAD~1` + 백업 복원). 복원은 눈이 아니라
체크섬으로 확인했다 — `session.py` `4c93d8c4…` · `tools.py` `3e6cc217…` ·
`App.tsx` `b53f7da1…` · `preview.py` `f311e798…` 넷 다 뮤테이션 전 값과 일치.
(뮤테이션 복원에 `git checkout`을 쓰지 않았다 — 미커밋 변경을 함께 날린다.)

### E.2.6 SPEC 소견 — 침묵 · 모호 · 오류

**이 목록이 이 구현의 부산물 중 가장 값이 나가는 부분이다.** 문면을 매끄럽게
고쳐 덮지 않고 그대로 적는다. `spec.md` · `plan.md` · `acceptance.md` 본문은
manager-docs의 소유이므로 여기서 고치지 않았다.

#### F-1 [차단급 오류] `AC-SHEETPIPE-005` ⑤의 검증 명령이 자기 기대값과 어긋난다

AC는 `grep -c 'Vectorworks' ui/src/App.tsx ui/src/useCopilotSocket.ts`가 **0**
이어야 하고 "오늘 이 값은 **넷**"이라고 적었다. 실측:

```
$ grep -c 'Vectorworks' ui/src/App.tsx ui/src/useCopilotSocket.ts   # AC 문면 그대로
ui/src/useCopilotSocket.ts:6
ui/src/App.tsx:13                                                    # 합계 19, 넷이 아니다
```

19 중 15는 **식별자**다 — `sendVectorworksExportUpload` ·
`buildVectorworksExportUpload` · `uploadVectorworksExport` ·
`vectorworksUploadError` · `setVectorworksUploadError`. 이 값을 0으로 만들려면
그 이름들을 전부 바꿔야 하고, 그중 `buildVectorworksExportUpload`는 **정의가
`ui/src/protocol.ts`에 있다** — `plan.md` §C가 "열지 않는 것"으로 못박은 파일이다.
즉 **AC를 문면대로 만족시키는 것은 같은 SPEC의 경계 요구를 어기지 않고는
불가능하다.**

의도는 §G.1 · 결정 H · `REQ-SHEETPIPE-008` ②가 일관되게 "**문구** 넷"이라고
말하므로 회수 가능하다. 인용부호에 앵커를 건 변형이 AC 자신의 기대값을 정확히
재현한다:

```
$ grep -cE "[\"'\`]Vectorworks" ui/src/App.tsx ui/src/useCopilotSocket.ts
ui/src/App.tsx:3   ui/src/useCopilotSocket.ts:1      → 합계 4   ← AC가 말한 "넷"
(구현 후) App.tsx:0   useCopilotSocket.ts:0            → 합계 0   ← AC가 말한 "0"
```

**의도를 구현하고, 그 변형으로 검증했다.** 이 변형을 `ui/src/attachmentCopy.test.ts`에
테스트로 고정했고 **날조 대조군**을 함께 넣었다 — 패턴이 아무것도 못 잡는
정규식이면 그 단언들은 늘 초록이므로, 대조 문자열에서 1을 세고 식별자에서 0을
세는 것을 먼저 단언한다.

> 형태의 일반화: **검사의 기대값은 채택 전에 실제 코퍼스에 대고 재야 한다.**
> 이 AC는 "오늘 넷"이라는 값을 적었지만 그 값을 내는 명령을 돌려 보지 않았다.
> `spec.md` §C.0 규약 1이 "숫자 옆에 그 값을 만든 명령을 적으라"고 요구하는데,
> 여기서는 명령과 숫자가 **둘 다 적혔는데 서로 맞지 않았다** — 규약 1의 사각지대다.

#### F-2 [주요] `plan.md` §C의 파일 목록이 실제 대상보다 작다 (8 → 10)

§C는 스스로 "[HARD] 이 목록을 6~7파일로 잡는다 … 전체 목록"이라 선언한다. 실제로
열려야 했던 파일은 **10개**이며, 빠진 둘은 둘 다 필연이다:

- **`server/tests/test_web_app.py`** — `test_vectorworks_upload_starts_a_guided_chat_turn`이
  페이로드로 `"c2FmZQ=="`(= `safe`, 4바이트)를 쓴다. 이음매가 들어오면 그 바이트는
  `unknown_sheet_kind`로 떨어져 `chat_response`가 오지 않는다. 그 테스트는
  **실패하지 않고 영원히 매달린다** — `_receive_until(ws, "chat_response")`가
  무한 대기하기 때문이다(전체 스위트가 86%에서 멈춰 10분을 넘겼다). 이것은
  `plan.md` §D.1 1(`ASSUMPTION-79`)이 예고한 위험이 **테스트 픽스처에서 먼저**
  터진 것이다. SPEC은 그 위험을 "운영자의 실사용"으로만 서술했고, **저장소 안의
  픽스처가 같은 성질을 갖는다는 점은 예상하지 않았다.**
- **`ui/src/attachmentCopy.test.ts`(신규)** — F-3 참조.

부수 소견 — **`t52`로 등재됨. 아래는 이 SPEC이 관측한 증거다.** 그 테스트가
**빨개지지 않고 매달린다**는 것 자체가 하네스 취약점이다. `_receive_until`에
타임아웃이 없어, 도착하지 않는 프레임은 실패가 아니라 정지로 나타난다. 실측:
**전량 스위트가 86%에서 두 번 섰고 두 번 다 10분을 넘겨** 백그라운드로
밀려났다(기준선 소요는 150초다). 원인은 느린 테스트가 아니라 **오지 않는
프레임**이었고, 진단은 `-v`로 이름을 뽑아 마지막 PASSED 다음 줄을 읽고서야
됐다. 진단 비용이 가장 비싼 실패 형태다.

**같은 형태가 다른 픽스처에도 있는지는 세지 않았다 — 미측정이며 이 카드 밖이다.**

#### F-3 [주요] vitest 델타가 0이 아니어야 한다는 요구와 파일 목록이 모순이다

`acceptance.md` §D 2는 "B는 `ui/`를 열므로 **vitest 델타가 0이 아닌 것이 정상**"
이라 하고 `plan.md` M1 6은 "늘어나는 것은 B가 새로 쓰는 테스트뿐"이라 적는다.
그런데 §C는 "B의 인수 테스트 **전부**"를 `server/tests/test_sheet_pipe.py` 하나에
배정하고 vitest 파일을 배정하지 않는다. 그리고 `plan.md` M1 6이 스스로 실측했듯
그 문구를 단언하는 **기존 vitest는 0건**이다.

세 문장이 동시에 참일 수 없다: 새 vitest를 안 쓰면 델타는 **0**이고, 델타가 0이면
§D 2가 빨갛다. 실측:

```
문구만 바꾸고 UI 테스트를 쓰지 않은 상태:  Tests 496 passed  (델타 0)
```

**새 vitest를 쓰는 쪽으로 풀었다** — `REQ-SHEETPIPE-009`가 "B의 신규 테스트"를
허용하고, 그 편이 `AC-005` ⑤⑥의 grep 두 개에 지속되는 자리를 준다(이 저장소에는
테스트 CI가 없으므로 손으로 치는 grep은 다음 사람에게 전달되지 않는다).
델타 **+4**는 새로 쓴 테스트 수와 정확히 일치한다.

#### F-4 [관찰] 뮤테이션 원장의 계수가 문서 안에서 갈린다 (6 vs 8)

`acceptance.md` §D 4는 "**6건**"이라 적고 여섯을 열거하는데, 그 목록은
`AC-SHEETPIPE-005`가 자기 본문에서 **필수**로 요구하는 뮤테이션 둘(문구 되돌리기 ·
앵커 주석 삭제)을 빠뜨린다. `progress.md` §E.1 `mutation_ledger_planned`는 **8**
이고 여덟을 열거한다. 많은 쪽(8)을 따랐다.

#### F-5 [주요 · 침묵] `kind_action_mismatch`를 기계로 판정할 근거가 A의 레지스트리에 없다

`REQ-SHEETPIPE-007`은 "슬롯의 종류가 요청된 `action`을 지원하지 않는다"를 닫힌
집합의 한 사유로 요구하고, `AC-SHEETPIPE-010`은 거절과 함께 "그 종류가 지원하는
`action` 목록"을 내라고 한다. 그런데 A의 `SheetKindRow`가 드는 것은
`kind` · `predicate` · `handler` · `passthrough_args` **넷뿐**이다 — 어떤
`action`이 그 종류에서 유효한지는 **어디에도 없다**. `passthrough_args`에
`"action"`이 들어 있다는 사실은 *그 인자가 전달된다*는 뜻이지 *어떤 값이
유효한가*를 말하지 않는다.

그러므로 B가 **종류를 키로 하는 두 번째 표**를 따로 들 수밖에 없다
(`SHEET_KIND_ACTIONS`). `server/sheets/**`는 읽기 전용이므로 A에 열을 더할 수도
없다. 결과:

- `plan.md` §E는 "LXSEQ-002/003/004가 행을 더할 때 **B는 열리지 않는다**"고
  적었는데 **그 문장이 참이 아니다.** 새 종류가 생기면 `SHEET_KIND_ACTIONS`에도
  줄이 하나 늘어야 하고, 빠뜨리면 그 종류는 어떤 `action`을 줘도
  `kind_action_mismatch`로 거절된다(`supported`가 빈 튜플이 되므로).
- 같은 형태가 **행 수 판독기**에도 있다(`_SHEET_ROW_COUNTERS`). `REQ-SHEETPIPE-004`는
  넷 중 하나로 행 수를 요구하지만 A의 행에는 행 수를 세는 훅이 없다.

두 표 모두 코드 주석에 이 사실을 적어 두었다. **A의 계약 결함이므로 B에서
고치지 않고 올린다** — `plan.md` §D.1 1이 세운 원칙("B의 이음매에서 표면화하지만
A의 결정")과 같은 처분이다.

#### F-6 [관찰 · 침묵] `session_method` 종이 둘 이상이면 이음매의 동작이 정의돼 있지 않다

`plan.md` 결정 C와 `AC-SHEETPIPE-007` ②는 "`session_method` 종은 업로드
이음매에서 **이미 처분된다**"고 일반형으로 적는다. 실제로 처분되는 것은 그
행의 대상이 **바로 그 메서드 자신**(`upload_vectorworks_export`)일 때뿐이다.
다른 이름의 `session_method` 행이 생기면 이 자리에서 무엇을 해야 하는지 SPEC에
없다 — 그 메서드를 동적으로 부르는 것은 자기 자신을 부르는 무한 재귀가 되므로
일반형 그대로 구현할 수 없다.

조용히 삼키지 않도록, 그 경우를 이름 붙은 안내로 처리했다("그 종류를 받는 세션
메서드가 이 첨부 경로에 배선돼 있지 않습니다"). **오늘 도달 불가**이며 방어일
뿐이다.

#### F-7 [관찰 · 침묵] 판별 불가 · `.mvr` 위임의 운영자 문구를 SPEC이 정하지 않는다

`plan.md` §D.1 1은 판별 불가가 "슬롯에도 Vectorworks 경로에도 가지 않는다"까지만
정하고, 운영자가 **무엇을 보는가**는 정하지 않는다(`REQ-SHEETPIPE-007`의 닫힌
집합 3종은 **래퍼**의 것이지 이음매의 것이 아니다). A의 `Discrimination.hint`
(조건부 재수출 안내)를 문구에 실어 붙이고, 결과 이름(`unknown_sheet_kind` ·
`ambiguous_sheet_kind`)을 그대로 노출했다. **B가 고른 것이지 SPEC이 정한 것이
아니다.**

#### F-8 [관찰] `AC-SHEETPIPE-001` ②의 "본문에 반영"과 에이전트 소유권이 부딪힌다

②는 어긋난 좌표가 "전부 정정돼 **본문에 반영**"될 것을 통과 조건으로 건다.
그런데 좌표표는 `spec.md` §H에 있고, `spec.md` 본문은 이 에이전트의 수정 금지
대상이다(frontmatter의 `status` · `updated`만 허용). 앞선 판(v0.1.0~v0.3.0)이
정정을 `progress.md`의 좌표 표에 실었으므로 **같은 자리**(E.2.1)에 실었다.
`spec.md` §H 자체는 여전히 낡은 좌표를 든다 — sync 단계에서 정리할 몫이다.

#### F-9 [관찰] `spec.md` §A.5의 "신규 코드는 … 등재 7지점" 규모 추정이 낮다

실측 규모: `10 files changed, 1104 insertions(+), 14 deletions(-)` (M1+M2 커밋).
그중 테스트가 약 600줄이다. Tier M(≤1000 LOC) 판정 자체는 **뒤집히지 않는다**
(제품 코드 기준). 다만 §A.5가 든 근거("슬롯 하나 · 분기 하나 · 핸들러 하나 ·
등재 7지점")는 실제 표면적을 낮게 잡았다 — 배선 두 곳, 두 번째 종류-키 표 둘
(F-5), 테스트 두 파일이 그 열거에 없다.

#### F-10 [환경] 이 워크트리에서 Write/Edit 도구가 막혀 있다

`Write`/`Edit`가 `Path traversal detected: file is outside project directory`로
거절한다 — 도구의 프로젝트 루트가 이 워크트리가 아니다(다른 체크아웃을 가리킨다).
Bash 쓰기는 정상이므로 전 구간을 heredoc + 파이썬 스플라이스로 처리했다.
부수적으로, 워크트리 격리 가드가 **따옴표 밖의 내용 있는 중괄호 쌍**을 담은
명령을 브레이스 확장으로 읽고 거절한다 — 파이썬·TS 소스를 heredoc으로 쓰려면
자리표시자 치환이 필요하다. 구현 사실이 아니라 **이 보드의 도구 사실**이므로
기록만 한다. 재현 가능한 대조군 표와 회피법은 **§E.2.7 ③**이 든다.

> **정정 (2026-08-24, 검증 회차).** 이 항의 첫 판은 거절 형태를 **둘**로 적었다
> — 중괄호 그룹과 "슬래시 든 산문 토큰(`try/except`)". 뒤엣것은 **고립해서 재지
> 않은 추론**이었다: 그 토큰을 담은 청크가 거절된 것은 사실이나 그 청크에는
> 중괄호 쌍이 함께 있었다. 단독으로 다시 재니 **통과한다**(§E.2.7 표 f). 같은
> 이유로 용의선상에 있던 `**` 언패킹도 무죄다(표 g). 고립된 판별 형태는
> **중괄호 하나뿐**이다. 거절을 관측한 것과 무엇이 거절시켰는지를 아는 것은
> 다른 문장이며, 이 항의 첫 판은 그 둘을 섞었다.

### E.2.7 하네스 마찰 기록 (F-10 계열 — 기록만, 카드는 t47이 든다)

이 SPEC의 내용과 무관하게 **이 보드의 도구 사실**이다. 세 가지를 밟았다.

#### ① 다섯 번째 격리 워크트리 착지

지정된 `t10b`가 아니라 `agent-a6b09215de55701b2`로 떨어졌다. 이 보드에서
**다섯 번째**다. 지시대로 `git -C`나 `cd`로 `t10b`에 닿으려 하지 않고
(격리 세션의 교차 트리 git은 거절되며 그 거절이 옳다) 있는 자리에서
`3ffda31`을 기반으로 일한 뒤 브랜치를 밀었다.

#### ② `Write` / `Edit` 도구가 이 워크트리에서 경로 차단

```
Write(file_path="…/agent-a6b09215de55701b2/server/tests/test_sheet_pipe.py")
→ Path traversal detected: file is outside project directory
```

빈 파일 하나로도 재현된다. 도구의 "project directory"가 이 워크트리가 아니라
다른 체크아웃으로 해소된다(이 세션에 실린 스킬 기준 경로는
`/Users/studiox/orca/workspaces/AI-Lighting_Console/LX-SEQ/…`를 가리킨다).
**Bash 쓰기는 정상**이므로 전 구간을 heredoc + 파이썬 스플라이스로 처리했다 —
읽기(`Read`)는 막히지 않는다. 편집 도구가 아니라 편집 **경로**의 문제다.

#### ③ 워크트리 가드가 거절하는 명령 형태 — 실측으로 하나 고립

거절 문구는 늘 같다:

```
This agent is isolated in the worktree …, but this command is too complex to
verify that it stays inside the worktree. Refusing to run it …
```

**거절 자체는 옳은 동작이다** — 정적으로 추적할 수 없는 셸 구조를 막는 것이
설계다. 문제는 *어떤 형태가 걸리는지 적힌 데가 없다*는 것뿐이다. 그래서
시행착오로 알아낸 것을 **양성·음성 대조군을 짝지어** 남긴다. 아래는 전부
`cat > <파일> <<'EOF'` 한 줄짜리 heredoc으로, **본문만 다르게** 해서 잰 것이다.

| # | heredoc 본문 | 결과 |
|---|---|---|
| a | `call = ToolCall(id="c1", name=WRAPPER, arguments={"action": "preview"})` | **거절** |
| b | `call = ToolCall(id="c1", name=WRAPPER, arguments=ARGS)` — a와 그 줄만 다름 | 통과 |
| c | `call = ToolCall(id="c1", name=WRAPPER, arguments={})` — 빈 중괄호 | 통과 |
| d | 여러 줄 딕셔너리 (`kwargs = {` 줄 · `"execution_port": port,` 줄 · `}` 줄) | **거절** |
| e | `parameters={` + `"type": "object",` 두 줄 | **거절** |
| f | 산문 안의 슬래시 토큰 — 파이썬 docstring에 `` `try/except` `` | 통과 |
| g | `def _registry(**overrides):` + `return build_toolset(**overrides)` | 통과 |

**고립된 판별 형태는 하나다: 따옴표 밖의 중괄호 쌍에 내용이 있는 것.**
a↔b가 그 한 줄만 바꾼 대조쌍이고, c가 경계를 준다 — **빈 `{}`는 통과하고
내용이 들어가면 거절된다.** d·e는 여러 줄에 걸쳐도 같다. 정적 분석기가 셸
브레이스 확장(`{a,b}`)으로 읽는 것으로 보이며, 따옴표 안의 중괄호는
(f-string의 `{kind}` 등) 인용 구간이 접히므로 걸리지 않는다 — 그래서
같은 파일에 f-string이 잔뜩 있어도 통과한다.

**f와 g는 무죄다.** 이 둘은 처음에 용의선상에 올랐는데, 각각을 *포함한* 청크가
거절됐기 때문이다. 그러나 그 청크들에는 중괄호 쌍이 **함께** 들어 있었고,
단독으로 다시 재 보니 둘 다 통과한다. 교란 변수였다.

> **이 표 자체가 규율의 예다.** 처음 §E.2.6 F-10에는 "중괄호와 **슬래시 든 산문
> 토큰** 둘"이라고 적었다. 슬래시 쪽은 **고립해서 재지 않은 추론**이었고,
> 재 보니 **틀렸다**(f 통과). 거절을 관측한 것과 *무엇이 거절시켰는지*를 아는
> 것은 다른 문장이다 — 아래 F-10에 정정을 실었다.

**실무 회피법**(다음 사람용): 파이썬·TS 소스를 heredoc으로 쓸 때 중괄호를
`LBRC`·`RBRC` 같은 자리표시자로 적고, 파일을 쓴 뒤 파이썬 한 줄로
`chr(123)`·`chr(125)`로 치환한다. 이 SPEC의 툴 스키마와 `attachmentCopy.test.ts`
전체가 그렇게 들어갔다. 딕셔너리를 `dict()` + 항목 대입으로 바꾸는 우회도
통하지만, JSON 스키마처럼 중첩이 깊으면 자리표시자 쪽이 읽기 낫다.

---

## §E.3 Run-phase Audit-Ready Signal

```yaml
spec_id: SPEC-COPILOT-SHEETPIPE-001
tier: M
pass_threshold: 0.80
phase: run
run_complete_at: 2026-08-24
run_commit_sha: 86ae6cf            # M-final. M1+M2 구현은 5102032
run_branch: WT-sheetpipe-attachment-pipe
run_worktree: .claude/worktrees/agent-a6b09215de55701b2   # 의도한 t10b가 아니다
run_base: 3ffda31
run_status: complete
ac_pass_count: 11
ac_fail_count: 0
ac_conditional_count: 0
baseline_measured:
  pytest: "9974 passed, 12 skipped, 0 failed"      # 이 워크트리 · 3ffda31 · 콘솔 미실행
  vitest: "496 passed (20 files)"
final_measured:
  pytest: "10009 passed, 12 skipped, 0 failed"     # +35 = 34(test_sheet_pipe) + 1(test_web_app)
  vitest: "500 passed (21 files)"                  # +4 = attachmentCopy.test.ts
  console_running_during_final_pytest: true        # 기준선 때는 false — E.2.3 주 참조
mutation_ledger_executed: 8        # 계획 8 · acceptance §D 4는 6이라 적었다(소견 F-4)
mutation_all_discriminating: true
registration_points_hit: 7
tripwire_protected_range_violations: 0             # 재측정값 — 전례로 미루지 않았다
suite_runs_in_m2: 2
preserve_direct_diff: empty                        # AC-011 ① — 커밋 뒤 측정
preserve_guard: "41 passed"                        # AC-011 ③ — 보조
lint: "ruff check server/ → All checks passed"
format: "ruff format --check server/ → 407 files already formatted"
ui_typecheck: "tsc && vite build → ✓ built"
files_changed: 11                  # 구현 10 + 트립와이어 1
new_warnings_or_lints_introduced: 0
spec_findings: 10                  # F-1 차단급 1 · 주요 3 · 관찰 5 · 환경 1
spec_findings_corrected: 1         # F-10 — 거절 형태 둘 중 하나가 미고립 추론이었다 (E.2.7)
harness_friction_recorded: 3       # E.2.7 — 격리 착지 · Write/Edit 경로 차단 · 가드 거절 형태
spec_body_edits: 0                 # spec/plan/acceptance 본문 무수정 (frontmatter status만)
m1_to_mN_commit_strategy: "M1+M2 한 커밋(5102032) + 트립와이어(86ae6cf) + 이 기록"
blocked: false
```

### 미해소 항목 (run 이후)

| 항목 | 상태 | 비고 |
|---|---|---|
| `ASSUMPTION-79` — 오늘 되던 업로드가 거절되는가 | **부분 관측** | 운영자 이력으로는 여전히 미검증이나, **저장소 픽스처에서는 실제로 일어났다**(F-2). B에서 닫지 않는다 |
| `spec.md` §H 좌표표 | 낡음 | 정정은 E.2.1에 있다. 본문 반영은 sync의 몫 (F-8) |
| A 레지스트리의 `action`·행 수 훅 부재 | 미해소 | A로 올린다 (F-5) |
| `_receive_until` 타임아웃 부재 | 미해소 | B의 범위 밖. 실패가 정지로 나타난다 (F-2 부수) |

---

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
