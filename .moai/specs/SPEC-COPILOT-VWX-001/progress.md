# SPEC-COPILOT-VWX-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**).

## §0 인수인계 — 여기서 시작한다 (2026-08-05)

> **이력을 모르는 사람이 처음 읽는 절이다.**

### 한 문단

**무엇**: Vectorworks Instrument Data(엑셀/CSV/tab-text)를 읽어 **설계상 리그(designed rig)** 모델을 만들고, 이미 라이브 검증된 `precheck_patch`(콘솔 실측)와 대조해 **"도면 vs 실제 콘솔 패치"** 차이 리포트를 낸다. `.moai/reports/ma3-copilot-overview.html` §7 P0 항목의 1단계만을 범위로 하며, 2단계(`AddFixtures` 자동 패치)와 3단계(MVR/GDTF)는 후속 SPEC으로 분리한다.
**상태**: **plan-phase 아티팩트 6종 작성 완료. 미커밋 · 미감사.** REQ 25건 · AC 26건 · ASSUMPTION 3건(68~70) · 마일스톤 9개(M0~M8) · 라이브 세션 0회 · clarification 마커 0건.
**열린 사용자 접점**: **2건** — ① 실물 Vectorworks export 샘플 제공(M0 선행조건, 컬럼 계약 동결의 유일한 전제) · ② 신규 의존성 `openpyxl` 채택 승인(`.xlsx` 경로 B 지원 여부, 미승인이어도 산출물은 성립).

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 25건 · §C PRESERVE와 **신규 의존성 승인 대기** · §D Out of Scope 6건 |
| 2 | 무엇을 통과해야 하나 | `acceptance.md` — AC 26건 · 역추적표 · 마일스톤별 배정 |
| 3 | 왜 이렇게 설계했나 / 왜 이 순서로 만들었나 | `design.md` 슬롯 A~E · `plan.md` §B M0~M8 |
| 4 | Vectorworks 형식 조사 원문(가장 김) | `research.md` — 2경로·별칭 테이블·주소 4형식·7가지 함정. 필요할 때만 |
| 5 | 라이브 세션 0회의 근거 | `plan.md` §C — 검토 후 적극적으로 0으로 결정한 것이지 생략이 아니다 |

### 인수인계 시 반드시 알아야 할 함정 3건

1. **이 저장소에 실물 Vectorworks export 샘플이 0건이다.** 컬럼 별칭 테이블(`research.md` §3)은 Vectorworks 공식 문서 조사에 근거한 **강력한 초안**이지 정본이 아니다 — M0가 실물 샘플로 검증·확장하기 전에는 M1 이후를 "완료"로 표시하지 않는다.
2. **콘솔 실측을 재구현하지 않는다.** `read_inventory`/`build_patch_sheet`/`normalize_address`/`_range_overlaps`는 PRECHK SPEC이 이미 라이브 검증했다 — `server/vwx/`는 그것을 **소비만** 한다. 재구현하면 두 경로가 드리프트한다.
3. **대조 조인 키는 (유니버스, 주소)+타입이며 `FID`/`CID`는 0건이다.** 슬롯==FID 우연일치 쇼파일에서는 원리적으로 FID 프로브와 슬롯 프로브를 구별할 수 없다(`console/lua/PROTOCOL.md:322-324`, PRECHK 선례) — 이 SPEC은 그 필요 자체를 조인 키 설계로 우회했다. 새 라이브 프로브를 열려는 유혹을 거절한다(`plan.md` §C가 근거를 적었다).

### 인수인계가 온전한지 기계로 확인하는 법

```
git rev-parse --abbrev-ref HEAD                 -> feature/SPEC-COPILOT-VWX-001
git status --short                              -> spec.md/plan.md/acceptance.md/design.md/research.md/progress.md 6개 신규(미커밋)
uv run pytest server/tests -q                   -> 4716 passed · 7 skipped · 1 warning (코드 변경 0 — plan-phase만 진행됨)
grep -oE 'REQ-VWX-[0-9]{3}' .moai/specs/SPEC-COPILOT-VWX-001/spec.md | sort -u | wc -l       -> 25
grep -oE '^### AC-VWX-[0-9]{3}' .moai/specs/SPEC-COPILOT-VWX-001/acceptance.md | sort -u | wc -l -> 26
```

### 다음 담당자가 먼저 결정할 것 2건

1. **plan-auditor 감사 1회차 PASS(0.92, Tier L 임계 0.85).** `plan_status: audit-ready`(아래 §E.1)로 갱신됨. 지적 10건(전부 minor, P0/P1 0건)은 `§E.1a` 참조.
2. **Kickoff 사용자 접점 2건**(실물 샘플 · `openpyxl` 승인)이 미해결이다. `plan.md` §G가 접점 표를 소유한다.

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 6종 작성 (2026-08-05)

착수 SHA **`b1a630eb9380fd37436252e366289350bd22feff`**(= `origin/main`, SPATIAL/GROUPGEN 머지 직후), 착수 baseline **4716 passed · 7 skipped · 1 warning · 91.35s(0:01:31)**(직접 실측, 이월 인용 아님).

| 아티팩트 | 내용 | 라인 수 |
|---|---|---|
| `spec.md` | REQ 25건 · Out of Scope 6개 H3(전부 `-` 불릿 보유) · ASSUMPTION 68~70 | 184 |
| `plan.md` | 마일스톤 M0~M8 · 결정 A~G · 라이브 세션 0회 근거 · Phase 4 Mode Selection 권고 | 253 |
| `acceptance.md` | AC 26건 · 역추적표 REQ 25/25 · 마일스톤별 배정 합 26 | 405 |
| `design.md` | 변경 표면 · 흐름 8단계 · 위험 검토 13항 · 설계 슬롯 A~E · 뮤테이션 25개 | 338 |
| `research.md` | 2경로 export · 별칭 테이블 · 주소 4형식 · 7가지 대조 함정 · 재사용 계약 | 206 |
| `progress.md`(본 파일) | 인수인계 + plan-phase 로그 + §E 골격 | (본 절 포함, §E.1 참조) |

### 조사 방법 — 실물 샘플 없이 공식 문서로 초안을 잡았다

이번 SPEC은 PRECHK와 달리 **라이브 콘솔 사전 프로브를 돌리지 않았다** — 대상이 콘솔이 아니라 Vectorworks export 파일 포맷이기 때문이다. 대신 Vectorworks 공식 도움말 문서 3건(WebFetch로 검증됨, `research.md` §1)을 조사해 두 export 경로(tab-text 전용 경로 A, 워크시트 그리드 경로 B)와 컬럼 별칭 테이블 초안을 확립했다. **이 초안은 실물 파일로 검증되지 않았다** — M0가 그 검증을 소유한다.

### 사용자 브리핑이 이미 확정한 사실을 그대로 반영했다

사용자 브리핑이 제공한 조사(두 export 경로, 4가지 주소 표현, 별칭 테이블, 7가지 대조 함정, FID/CID 불가 근거, 실물 샘플 부재)는 이미 검증된 기존 지식으로 취급하고 재조사하지 않았다 — 다만 저장소 코드 인용(`inventory.py:54` 등)은 실제 파일과 대조해 **드리프트를 5건 발견하고 정정했다**(plan-audit 지적 반영 — 아래 표는 5행이며 프로즈 수치를 표와 일치시켰다):

| 브리핑 인용 | 실제 값 | 정정 |
|---|---|---|
| `server/orchestrator/tools.py:98`(TOOL_NAMES) | `TOOL_NAMES = (`은 실제로 **127행** | design.md·spec.md·plan.md 전부 127로 정정 |
| `server/orchestrator/tools.py:1542-1697`(precheck_patch 핸들러) | `def precheck_patch(...)`는 실제로 **1986행** | 정정 |
| `server/orchestrator/tools.py:2916-2955`(ToolDefinition) | `name="precheck_patch"`는 실제로 **4317행** | 정정 |
| `server/orchestrator/tools.py:3443`(handlers dict) | `handlers: dict[str, _Handler] = {`는 실제로 **5134행**(항목은 5143행) | 정정 |
| `server/prechk/inventory.py:54`(PROPERTY_WHITELIST) | 실제로 **57행** | 정정 |

브리핑 자체가 "content-token anchor; line numbers drift"라고 경고했고, 이 드리프트가 정확히 그 사례였다 — 인용 전에 직접 grep으로 재확인했다.

### 라이브 세션 0회 — 적극적 결정

PRECHK와 달리 본 SPEC은 라이브 세션을 **0회**로 결정했다. 콘솔 실측(대조의 절반)은 이미 라이브 검증된 `read_inventory`/`build_patch_sheet`를 재사용하고, FID/CID 재프로브는 조인 키 설계가 그 결과에 의존하지 않으므로 열지 않았다 — 대안을 검토하고 기각한 근거는 `plan.md` §C에 있다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-05
spec_version: "0.1.0"
base_sha: b1a630eb9380fd37436252e366289350bd22feff
baseline_measured: "uv run pytest server/tests -q → 4716 passed, 7 skipped, 1 warning in 91.35s (0:01:31)"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
artifact_lines: "spec 184 · plan 253 · acceptance 405 · design 338 · research 206"
requirements: 25          # REQ-VWX-001~025 — spec.md 정의 25 = 고유 토큰 25
acceptance_criteria: 26   # AC-VWX-001~026 — acceptance.md 절 제목 26 = 고유 토큰 26
milestones: 9             # M0~M8. M0·M8만 cycle_type=none (코드 변경 0)
assumptions_open: 3       # ASSUMPTION-68~70
decisions_closed: 7       # plan.md 결정 등록부 A~G
decisions_open: 0
design_slots_closed: 5    # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
live_sessions_planned: 0  # plan.md §C — 적극적 결정, 근거는 해당 절 참조
machine_gates:
  requirements_counted: "25 — spec.md 정의 25 = 고유 토큰 25"
  req_to_ac_coverage: "25/25 — acceptance.md 역추적표 REQ 행 25, 커버 누락 0"
  acceptance_criteria_counted: "26 — acceptance.md 절 제목 26 = 고유 토큰 26"
  ac_milestone_assignment: "26 — M0 1 · M1 4 · M2 3 · M3 4 · M4 5 · M5 4 · M6 3 · M7 1 · M8 1. 중복 0 · 누락 0. plan.md 마일스톤별 AC 줄과 1:1 대조 완료"
  ac_absent_from_traceability_table: "3 — AC-VWX-001(M0 전제 확보 게이트) · AC-VWX-025(형상 전체) · AC-VWX-026(종단 통합). acceptance.md가 의도로 명시"
  out_of_scope_h3_headings: "6 — 전부 `-` 불릿 1건 이상 보유(OutOfScopeRule 요건 충족)"
  abbreviated_tokens_all_artifacts: 0     # 정규식 [^A-Z-](AC|REQ)-[0-9]{3} — 6문서 합 0
  clarification_markers_all_artifacts: 0  # NEEDS CLARIFICATION/TODO/TBD/FIXME 검색 — 6문서 합 0
  mutations_proposed: 25    # design.md §6.3 (plan-audit 지적 반영 — 표 25행과 일치)
preflight_probe:
  real_sample_present: false   # 이 저장소에 실물 Vectorworks export 샘플 0건. M0가 확보를 소유한다
  code_citation_drift_found: 5 # tools.py TOOL_NAMES/handler/definition/handlers dict 4개 좌표 + inventory.py 1개 좌표가 브리핑 인용과 어긋나 직접 재확인 후 정정 (plan-audit 지적 반영 — 표 5행과 일치)
known_gaps:
  - "이 저장소에 실물 Vectorworks export 샘플이 없다 — 컬럼 별칭 테이블(research.md §3)은 Vectorworks 공식 문서 조사에 근거한 초안이며 M0가 실물 파일로 검증·확장한다."
  - "openpyxl 신규 의존성 승인이 확보되지 않았다 — 미승인이어도 산출물은 성립하며 경로 B의 .xlsx만 v1 범위 밖으로 축소된다(spec.md §D)."
  - "ASSUMPTION-68~70 3건 모두 M0/M1~M3에서 판정될 예정이며 아직 GO/NEGATIVE가 배정되지 않았다."
  - "plan-audit 1회차 PASS(0.92) — minor 지적 10건 잔존(§E.1a), P0/P1 0건이라 run-phase 착수를 막지 않는다."
next: "Implementation Kickoff Approval(실물 Vectorworks export 샘플 제공 + openpyxl 의존성 승인, 2건) 확보 후 /moai run SPEC-COPILOT-VWX-001."
```

## §E.1a Plan-audit 결과

**1회차 — PASS, 종합 점수 0.92** (Tier L 임계 0.85). 전체 리포트: `.moai/reports/plan-audit/SPEC-COPILOT-VWX-001-round1.md`.

Must-pass 7축: MP-1 REQ 시퀀싱 PASS(25/25, 결번·중복 0) · MP-2 AC GEARS 준수 PASS(26건 전부 IF/THEN 0·`[Option]` 0) · MP-3 frontmatter PASS(12/12 정본, 별칭 0) · MP-4 언어 중립성 N/A(단일 언어 Python) · MP-5 D7 교차-SPEC 정합 PASS(PRECHK/OVERLAP/GROUPGEN 전부 `status: completed`) · MP-6 D8 크로스플랫폼 N/A(`syscall` 언급 0) · MP-7 clarification 게이트 PASS(마커 0).

Minor 지적 10건(P0/P1 없음, 전부 run-phase 착수 비차단):
- REQ-VWX-025가 `[Ubiquitous]` 태그인데 "shall" 부재
- REQ 7건이 비정형 후행 조건절을 태그 없이 포함
- REQ 5건이 정본 텍스트 안에 `file:line 함수명` 구현 좌표를 직접 인용
- PRESERVE 목록이 `server/prechk/` 8개 파일 중 4개만 커버(`__init__.py`/`footprint.py`/`macro.py`/`query.py` 미포함) — 감사가 조사한 결과 3개 모듈은 무관 기능이라 위험도 낮음으로 판정
- 미문서화된 `related_specs` frontmatter 필드
- `id` 정규식이 SSOT 리터럴과 문자 그대로는 다름(비차단 — 리포 전역 다분절 관례와 합치)
- `progress.md`가 드리프트 정정 "3건"이라 적었는데 자체 표는 5건 나열(자기모순)
- `design.md`가 변형 "24건"이라 적었는데 자체 표는 25행(3+3+4+5+4+3+2+1=25, 재계산 확인)
- "0건" AC 주장 2건이 형제 AC들이 갖춘 비공허성 인라인 주석을 누락
- AC-VWX-013②의 동점 처리 규칙이 "예시"이지 닫힌 결정이 아님

강점: 코드 좌표 인용 11건 전량 라이브 재검증 통과(`tools.py:127/136/1986/4317/5134/5143`, `inventory.py:57`, `patch.py:118/440`, `paperwork/data.py:67`, `verdicts.py:52`, `report.py:143`). FID/CID 불가·실물 샘플 부재 두 orchestrator 지정 정직-처리 항목 모두 `SkippedCheck`/`not_performed` 어휘로 충실히 처리됨(얼버무림 없음). `base_sha`가 실측 `git log -1`과 정확히 일치. REQ↔AC 25↔26 역추적을 표본이 아닌 전수 검증(누락 0, 고아 0).

**후속 처리**: 10건 minor는 audit-ready 신호를 막지 않는다(모두 P0/P1 미해당). run-phase 착수 전 또는 M1 중 정정 권고 — 이번 plan-phase worker 범위에서는 재수정하지 않고 다음 담당자(Implementation Kickoff Approval 승인자 및 manager-develop)에게 인계한다.

## §E.2 Run-phase Evidence

### run-phase 착수 baseline (직접 실측, 이월 인용 아님)

```
git rev-parse HEAD → 2bc95cf309457de5f6fc2b6757b3a8c7aa9f6ec7 (feature/SPEC-COPILOT-VWX-001, base origin/main b1a630e)
uv run pytest server/tests -q → 4716 passed, 7 skipped, 1 warning in 89.90s (0:01:29)
```

### Implementation Kickoff Approval — 확정 (2건 모두 종결)

1. **`openpyxl` 신규 의존성 — 승인.** `pyproject.toml` 런타임 의존성에 추가, 경로 B `.xlsx`를 v1 범위에 포함. spec.md §C/§D v0.1.1로 갱신됨(무효화된 조건부 Out-of-Scope 절 명시).
2. **실물 Vectorworks export 샘플 — 미제공.** 사용자가 아직 제공하지 않았다. M0는 완료 처리하지 않는다.

### M0 — `BLOCKED: 사용자 산출물 대기 — 실물 Vectorworks export 샘플 미제공`

M0는 사용자가 실물 export 파일(경로 A 또는 경로 B, 최소 1건)을 제공해야 완료 가능하다. 제공되면 다음을 검증한다:
- 컬럼 계약 검증: `research.md` §3 별칭 테이블이 실제 헤더와 합치하는지(ASSUMPTION-68) — 불일치 시 별칭 테이블을 실물 헤더로 확장하고 확장분을 본 절에 기록.
- `Absolute Address` 단일값 파일의 실존 여부(ASSUMPTION-69).
- 경로 B 데이터 블록 구조적 식별 휴리스틱의 실물 적중 여부(ASSUMPTION-70).

M0가 미충족이므로 M1~M7은 **합성 픽스처**(문서 근거·실물 미검증, research.md §3 알려진 형식 조사에만 근거)로 선행 진행한다. M8(종단 검증)은 실물 샘플 없이는 닫히지 않으므로 아래에서 별도 BLOCKED로 기록한다.

### M1~M7 구현 로그 (manager-develop 위임 완료, 오케스트레이터 직접 재검증 완료)

**AC PASS/FAIL 매트릭스** (M0/M8 제외 24건 전량):

| 마일스톤 | AC | 검증 명령 | 결과(오케스트레이터 재실측) |
|---|---|---|---|
| M1 | AC-VWX-002~005 | `uv run pytest server/tests/test_vwx_reader.py -q` | 15 passed |
| M2 | AC-VWX-006~008 | `uv run pytest server/tests/test_vwx_columns.py -q` | 8 passed |
| M3 | AC-VWX-009~012 | `uv run pytest server/tests/test_vwx_address.py -q` | 12 passed |
| M4 | AC-VWX-013~017 | `uv run pytest server/tests/test_vwx_rig.py -q` | 17 passed |
| M5 | AC-VWX-018~021 | `uv run pytest server/tests/test_vwx_diff.py -q` | 11 passed |
| M6 | AC-VWX-022~024 | `uv run pytest server/tests/test_vwx_report.py server/tests/test_vwx_tool.py -q` | 22 passed |
| M7 | AC-VWX-025 | PRESERVE diff + 전체 스위트 + AST 스캔 비공허성 | PASS(아래) |

**전체 스위트 (오케스트레이터 직접 재실측, HEAD 7c2a19b)**:
```
uv run pytest server/tests -q
→ 4801 passed, 7 skipped, 1 warning in 92.58s (0:01:32)
```
착수 baseline `4716 passed, 7 skipped`(2bc95cf) 대비 **+85**(신규 VWX 테스트 7파일 합계: 15+8+12+17+11+8+14=85), skip·warning 카운트 불변 — 델타 전량 설명됨. 회귀 0건.

**ruff (오케스트레이터 직접 재실측)**: `uv run ruff check server/vwx/ server/tests/test_vwx_*.py server/orchestrator/tools.py` → `All checks passed!`

**PRESERVE diff 게이트 (오케스트레이터 직접 재실측)**:
```
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ \
  server/prechk/__init__.py server/prechk/inventory.py server/prechk/patch.py \
  server/prechk/report.py server/prechk/footprint.py server/prechk/macro.py server/prechk/query.py \
  server/prechk/verdicts.py \
  server/paperwork/data.py server/paperwork/render.py server/paperwork/output.py server/looks/
→ (완전 빈 출력, exit=0) — 8개 prechk 파일 전부 포함. verdicts.py도 0-diff(당초 순수 추가 예외보다 엄격).
```
비공허성 증명: manager-develop이 `server/prechk/patch.py`에 임시 라인을 추가·커밋해 게이트가 `1 file changed, 1 insertion(+)`로 적발함을 확인한 뒤 `git revert`로 되돌려 재확인함(커밋 582746c → 9f3de4b, 히스토리에 정직하게 보존 — squash 미실시).

**아키텍처 경계 (오케스트레이터 직접 재실측)**: `uv run pytest server/tests/test_architecture.py -q` → `4 passed`.

**툴 등록 검증 (dispatch 기반, dict 조회 아님)**: `test_vwx_tool.py::TestRegistrationByDispatch` 4-assertion 전부 PASS — `TOOL_NAMES` 포함 · `definitions()` 이름집합 포함 · dispatch가 'unknown tool' 미발생 · `advertised == set(TOOL_NAMES)`.

**M6 설계 변경 (계획 대비 더 안전한 결과)**: 신규 판정 어휘를 `server/prechk/verdicts.py`의 공유 `CLOSED_VOCABULARIES`에 추가하면 기존 `test_prechk_verdicts.py`/`test_prechk_report.py`의 정확-집합 assert 3건이 깨짐을 실측으로 발견. `server/vwx/report.py`에 독립 닫힌 어휘 레지스트리(`VWX_CLOSED_VOCABULARIES` + `vwx_label()`, 동일 패턴: 닫힌 집합+라벨표+미등록 예외)를 신설해 `verdicts.py`를 완전 비접촉으로 유지 — spec.md §C·acceptance.md AC-VWX-023①을 이 실제 설계로 갱신했다.

**M7 부수 수정**: `server/tests/test_songcue_bundle.py`가 `tools.py` 위치 트립와이어(과거 여러 SPEC이 갱신해온 관례)를 갖고 있어 M6의 신규 hunk(`base64`/`binascii` import) 반영을 위해 튜플 갱신. `test_tools.py`의 하드코딩 툴 개수(22→23)도 함께 갱신.

**환경 메모**: 커밋 시점 품질 게이트가 `npm test`(ui vitest)를 무조건 실행하는데 `ui/node_modules`가 부재해 커밋이 전부 막혔다 — `npm --prefix ui install`(기존 lockfile 기준 의존성 설치만, 소스 미변경)로 해소. 소스 코드 범위 밖.

**커밋 (전부 로컬, push 0건 — `git status -sb`로 확인, upstream 추적 없음)**:
```
e40c4d0 feat(SPEC-COPILOT-VWX-001): M1-M2 file reading + column alias resolution
3f2da4a feat(SPEC-COPILOT-VWX-001): M3 address handling
5349269 feat(SPEC-COPILOT-VWX-001): M4 designed-rig domain model
071d29a feat(SPEC-COPILOT-VWX-001): M5 precheck_patch diff
a83a42f feat(SPEC-COPILOT-VWX-001): M6 report + tool wiring
582746c test: PRESERVE-gate non-vacuity probe (to be reverted)
9f3de4b Revert "test: PRESERVE-gate non-vacuity probe (to be reverted)"
7c2a19b fix(SPEC-COPILOT-VWX-001): M7 update SONGCUE tools.py hunk tripwire
```

**신규/변경 파일**: 신규 `server/vwx/{__init__,reader,columns,address,rig,diff,report}.py`, `server/tests/test_vwx_{reader,columns,address,rig,diff,report,tool}.py`(7파일). 수정 `pyproject.toml`(openpyxl 추가)·`uv.lock`·`server/orchestrator/tools.py`(신규 툴 5지점 등록)·`server/tests/test_tools.py`·`server/tests/test_songcue_bundle.py`.

**plan-audit minor 10건 처리 (오케스트레이터 직접 정정, M1 병행)**: 자기모순 2건(드리프트 "3건"→5건 정정, 뮤테이션 "24"→25 정정) · REQ-VWX-025 shall 누락 정정 · AC-VWX-023②/AC-VWX-024④ 비공허성 주석 추가 · AC-VWX-013② 대표 규칙을 닫힌 결정으로 명확화. 나머지 6건(비차단, `related_specs` 미문서화·`id` 정규식 문구·REQ 7건 비정형 조건절·REQ 5건 file:line 인용)은 감사 비차단 판정대로 후속 사이클로 이연한다.

### M8 — `BLOCKED: 실물 Vectorworks export 샘플 없이는 종단 검증을 닫을 수 없음`

M0가 미충족인 채로는 M8(실물 파일 기반 종단 통합 검증, AC-VWX-026)을 완료로 표시하지 않는다. M8은 합성 픽스처 기반 종단 스모크(있다면)와는 별개로, 실물 샘플이 도착한 뒤 재개한다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: partial-blocked   # M1~M7 completed + verified; M0/M8 BLOCKED (real Vectorworks sample not provided)
run_complete_at: 2026-08-05
head_sha: 7c2a19b
base_sha: 2bc95cf309457de5f6fc2b6757b3a8c7aa9f6ec7
milestones_completed: [M1, M2, M3, M4, M5, M6, M7]
milestones_blocked: [M0, M8]
milestones_blocked_reason: "실물 Vectorworks export 샘플 미제공 — 사용자 산출물 대기"
acceptance_criteria_verified: 24   # AC-VWX-002~025 (M0=AC-VWX-001, M8=AC-VWX-026 제외)
acceptance_criteria_blocked: 2     # AC-VWX-001 (M0), AC-VWX-026 (M8)
full_suite: "4801 passed, 7 skipped, 1 warning in 92.58s — entry baseline 4716 passed 7 skipped, delta +85 fully explained (7 new test files), 0 regressions"
ruff: "All checks passed! (server/vwx/, server/tests/test_vwx_*.py, server/orchestrator/tools.py)"
preserve_gate: "empty diff on all 8 server/prechk/ files (including verdicts.py — stricter than the pure-addition exception spec.md originally allowed) + console/lua/** + server/safety/** + server/paperwork/{data,render,output}.py + server/looks/**; non-vacuity proven via plant-and-revert (582746c/9f3de4b)"
tool_registration: "dispatch-verified — TOOL_NAMES membership, definitions() name-set, dispatch no-unknown-tool, advertised==set(TOOL_NAMES) — all 4 assertions PASS"
architecture_boundary: "server/tests/test_architecture.py — 4 passed — server/vwx/ imports neither server.bridge nor pythonosc"
plan_audit_minor_findings_closed: 4   # 자기모순 2건 + REQ-VWX-025 shall + AC-013②
plan_audit_minor_findings_deferred: 6 # 비차단, 후속 사이클로 이연
push_count: 0
pr_count: 0
main_touched: false
known_gaps:
  - "M0/M8은 완료되지 않았다 — 실물 Vectorworks export 샘플이 사용자로부터 제공되어야 재개 가능하다."
  - "M1~M7은 전량 합성 픽스처(문서 근거·실물 미검증)로 검증됐다 — ASSUMPTION-68~70은 여전히 미판정(GO/NEGATIVE 없음)."
  - "M6 설계가 계획 대비 변경됐다 — server/prechk/verdicts.py를 건드리지 않고 server/vwx/report.py에 독립 어휘 레지스트리를 신설했다(spec.md §C·acceptance.md AC-VWX-023 갱신 완료)."
next: "실물 Vectorworks export 샘플 확보(M0) 후 M8 종단 검증 재개. 그 전까지는 sync-phase로 진행하지 않는다(M0/M8 BLOCKED가 SPEC 완결을 막는다)."
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

### 입력 파라미터

- **tier**: L
- **scope (file count)**: 예상 10~13 파일 — 신규 `server/vwx/{__init__,reader,columns,address,rig,diff,report}.py`(7) · `pyproject.toml`(1, openpyxl 승인 확정) · `server/orchestrator/tools.py` 수정(1) · `server/prechk/verdicts.py`/`server/prechk/report.py` 신규 부류 순수 추가(2) · 신규 테스트 7개 이상
- **domain count**: 1 (Python 백엔드 단일 도메인)
- **concurrency benefit**: LOW — M1(판독)→M2(컬럼)→M3(주소)→M4(리그)→M5(대조)→M6(보고/툴)의 강한 순차 데이터 사슬
- **Agent Teams prereqs**: 해당 없음 (Mode 3 retired)

### 모드 평가

| # | 모드 | 선택 | 근거 |
|---|---|---|---|
| 1 | trivial | 미선택 | 신규 모듈 7개 + 툴 배선 |
| 2 | background | 미선택 | Write/Edit 포함 |
| 3 | agent-team | 미선택 | retired |
| 4 | parallel | 미선택 | 단일 도메인 + 강한 순차 의존(코딩 중심 caveat) |
| 5 | **sub-agent** | **선택** | 순차 데이터 사슬(M1→…→M7), 단일 worker가 계약대로 순서대로 진행하는 편이 충돌·재작업이 적다 |
| 6 | workflow | 미선택 | 균일 기계 변환이 아니다 — 판정·미수행·보고 형상을 매 마일스톤 확인해야 함 |

### Decision: sub-agent

plan.md §G의 권고(sub-agent)와 일치한다 — 어긋나지 않으므로 §F가 §G를 override할 필요 없음. M1~M7을 manager-develop 단일 sequential 위임으로 순서대로 진행하며, 마일스톤 경계마다 오케스트레이터(본 워커)가 PRESERVE diff·ruff·pytest를 직접 재실측한다.

### 사용자 접점 표 (Kickoff 시점 확정 반영)

| 시점 | 접점 | 결과 |
|---|---|---|
| Kickoff | `openpyxl` 신규 의존성 채택 여부 | **승인** — .xlsx v1 범위 포함 |
| Kickoff | 실물 Vectorworks export 샘플 제공 | **미제공** — M0/M8 BLOCKED 유지, M1~M7은 합성 픽스처로 진행 |
