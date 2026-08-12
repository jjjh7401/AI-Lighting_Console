# SPEC-COPILOT-VWX-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**).

## §0 인수인계 — 여기서 시작한다 (2026-08-05)

> **이력을 모르는 사람이 처음 읽는 절이다.**

### 한 문단

**무엇**: Vectorworks Instrument Data(엑셀/CSV/tab-text)를 읽어 **설계상 리그(designed rig)** 모델을 만들고, 이미 라이브 검증된 `precheck_patch`(콘솔 실측)와 대조해 **"도면 vs 실제 콘솔 패치"** 차이 리포트를 낸다. `.moai/reports/ma3-copilot-overview.html` §7 P0 항목의 1단계만을 범위로 하며, 2단계(`AddFixtures` 자동 패치)와 3단계(MVR/GDTF)는 후속 SPEC으로 분리한다.
**상태**: **plan-phase 아티팩트 6종 작성 완료. 미커밋 · 미감사.** REQ 25건 · AC 26건 · ASSUMPTION 3건(68~70) · 마일스톤 9개(M0~M8) · 라이브 세션 0회 · clarification 마커 0건. **(v0.1.0 시점 스냅샷. 현재 v0.1.7 기준 REQ 28건 · AC 29건 · run_status=partial-blocked — ASSUMPTION-69 GO(선언된 전제 위에서 역산 지원)로 재판정·ASSUMPTION-70 PARTIAL 유지·M8 여전히 BLOCKED, 아래 §E.2 "02(절대주소 단독) 재설계" 절 참조.)**
**열린 사용자 접점**: **2건** — ① 실물 Vectorworks export 샘플 제공(M0 선행조건, 컬럼 계약 동결의 유일한 전제) · ② 신규 의존성 `openpyxl` 채택 승인(`.xlsx` 경로 B 지원 여부, 미승인이어도 산출물은 성립).

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 25건(v0.1.0)→**현재 28건**(REQ-VWX-026~028 v0.1.4 추가) · §C PRESERVE와 **신규 의존성 승인**(확정) · §D Out of Scope 6건 |
| 2 | 무엇을 통과해야 하나 | `acceptance.md` — AC 26건(v0.1.0)→**현재 29건**(AC-VWX-027~029 v0.1.4 추가) · 역추적표 · 마일스톤별 배정 |
| 3 | 왜 이렇게 설계했나 / 왜 이 순서로 만들었나 | `design.md` 슬롯 A~E · `plan.md` §B M0~M8 |
| 4 | Vectorworks 형식 조사 원문(가장 김) | `research.md` — 2경로·별칭 테이블·주소 4형식·7가지 함정. 필요할 때만 |
| 5 | 라이브 세션 0회의 근거 | `plan.md` §C — 검토 후 적극적으로 0으로 결정한 것이지 생략이 아니다 |

### 인수인계 시 반드시 알아야 할 함정 3건

1. **이 저장소에 실물 Vectorworks export 샘플이 0건이다.** 컬럼 별칭 테이블(`research.md` §3)은 Vectorworks 공식 문서 조사에 근거한 **강력한 초안**이지 정본이 아니다 — M0가 실물 샘플로 검증·확장하기 전에는 M1 이후를 "완료"로 표시하지 않는다.
2. **콘솔 실측을 재구현하지 않는다.** `read_inventory`/`build_patch_sheet`/`normalize_address`/`_range_overlaps`는 PRECHK SPEC이 이미 라이브 검증했다 — `server/vwx/`는 그것을 **소비만** 한다. 재구현하면 두 경로가 드리프트한다.
3. **대조 조인 키는 (유니버스, 주소)+타입이며 `FID`/`CID`는 0건이다.** 슬롯==FID 우연일치 쇼파일에서는 원리적으로 FID 프로브와 슬롯 프로브를 구별할 수 없다(`console/lua/PROTOCOL.md:322-324`, PRECHK 선례) — 이 SPEC은 그 필요 자체를 조인 키 설계로 우회했다. 새 라이브 프로브를 열려는 유혹을 거절한다(`plan.md` §C가 근거를 적었다).

### 인수인계가 온전한지 기계로 확인하는 법

아래는 **plan-phase 착수 시점(v0.1.0)의 기록**이다 — 그대로 재실행하면 지금은 다른 값이 나온다(코드가 M1~M7까지 구현되고 M0가 v0.1.4까지 진행됐기 때문). **현재 값으로 다시 확인하려면**:

```
git rev-parse --abbrev-ref HEAD                 -> feature/SPEC-COPILOT-VWX-001
git status --short                              -> (클린 — 전부 커밋됨, 최신 HEAD는 §E.3 head_sha 참조)
uv run pytest server/tests -q                    -> 4842 passed 이상 · 7 skipped (M1~M7 구현 완료, 회귀 0)
grep -oE 'REQ-VWX-[0-9]{3}' .moai/specs/SPEC-COPILOT-VWX-001/spec.md | sort -u | wc -l        -> 28
grep -oE '^### AC-VWX-[0-9]{3}' .moai/specs/SPEC-COPILOT-VWX-001/acceptance.md | sort -u | wc -l -> 29
```

**v0.1.0 시점 기록(참고용, 재실행하지 말 것 — 이월 인용 금지 원칙과 별개로 이 블록 자체가 이미 과거 값이다)**:
```
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
plan_amended_at: 2026-08-05   # v0.1.4 — M0 실물 샘플 반영으로 REQ 25→28 · AC 26→29 (아래 amendment 블록 참조)
spec_version: "0.1.0"
base_sha: b1a630eb9380fd37436252e366289350bd22feff
baseline_measured: "uv run pytest server/tests -q → 4716 passed, 7 skipped, 1 warning in 91.35s (0:01:31)"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
artifact_lines: "spec 184 · plan 253 · acceptance 405 · design 338 · research 206"
#: 아래 requirements/acceptance_criteria/mutations_proposed는 plan-phase(v0.1.0) 착수 시점의
#: 날짜 있는 스냅샷이다 — 덮어쓰지 않는다(리포 선례: SPEC-COPILOT-FXLIB-001/SCENE-001의
#: plan_amended_at 패턴). run-phase에서 늘어난 실제 수치는 amendment 블록(§E.2 M0 절 참조)을 본다.
requirements: 25          # REQ-VWX-001~025 — spec.md 정의 25 = 고유 토큰 25 (v0.1.0 시점, 이후 v0.1.4에서 28로 증가 — amendment 블록 참조)
acceptance_criteria: 26   # AC-VWX-001~026 — acceptance.md 절 제목 26 = 고유 토큰 26 (v0.1.0 시점, 이후 v0.1.4에서 29로 증가 — amendment 블록 참조)
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

### plan_amended_at 2026-08-05 (v0.1.4 — M0 실물 샘플 반영으로 REQ/AC 증가)

M0 실물 컬럼 계약 검증(§E.2 "M0 실물 컬럼 계약 검증" 절)이 ASSUMPTION-68을 NEGATIVE로 닫으며
`fixture_name`·`gdtf_fixture` 정규 필드 승격, 주소 3중 표현 교차검증, 설계 측 구간 겹침 판정
3개 기능을 추가로 요구했다 — 계획 시점(v0.1.0)에는 예견되지 않았던 실물 검증 결과다.

- `requirements: 25 → 28` (REQ-VWX-026~028 신설 — 위 `requirements:` 필드는 v0.1.0 스냅샷 그대로 보존)
- `acceptance_criteria: 26 → 29` (AC-VWX-027~029 신설 — 위 `acceptance_criteria:` 필드도 v0.1.0 스냅샷 그대로 보존)
- `mutations_proposed: 25` (v0.1.0 스냅샷) — v0.1.4에서 신규 기능당 뮤테이션이 추가됐으나 design.md는 개정하지 않았다(코드 변경 없이 뮤테이션 표만 갱신하는 것은 비례성 밖으로 판단, 회귀 테스트로 비공허성은 이미 증명됨).
- 마일스톤·ASSUMPTION 수·라이브 세션 회계는 불변(M2/M3/M5에 각 AC 1건씩 추가됐을 뿐 마일스톤 자체는 늘지 않았다).
- **정본은 `acceptance.md` §C.0/§C.0a·§F(Definition of Done)이며, 이 절의 25/26 숫자는 plan-phase 착수 시점 기록으로 고정된다** — 현재 값을 확인하려면 §0의 기계 확인 커맨드(현재 값 블록) 또는 `acceptance.md` §F를 본다.

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

### M0 — `PARTIAL: 컬럼 계약 1건 실물 검증 — ASSUMPTION-68 해소, 69/70 미해소 (v0.1.4)`

M0는 사용자가 실물 export 파일(경로 A 또는 경로 B, 최소 1건)을 제공해야 완료 가능하다. 제공되면 다음을 검증한다:
- 컬럼 계약 검증: `research.md` §3 별칭 테이블이 실제 헤더와 합치하는지(ASSUMPTION-68) — 불일치 시 별칭 테이블을 실물 헤더로 확장하고 확장분을 본 절에 기록.
- `Absolute Address` 단일값 파일의 실존 여부(ASSUMPTION-69).
- 경로 B 데이터 블록 구조적 식별 휴리스틱의 실물 적중 여부(ASSUMPTION-70).

M0가 미충족이므로 M1~M7은 **합성 픽스처**(문서 근거·실물 미검증, research.md §3 알려진 형식 조사에만 근거)로 선행 진행한다. M8(종단 검증)은 실물 샘플 없이는 닫히지 않으므로 아래에서 별도 BLOCKED로 기록한다.

**사용자 제공 파일 1건 수령 (2026-08-05) — M0 여전히 미충족, BLOCKED 유지.** `/tmp/vwx_sample.csv`
(원본: <https://d3cvt6oaff0blz.cloudfront.net/drop.dk/website/Downloads/Examples%20Shows/csv_example1.csv>)를
수령했으나, **이 파일은 Vectorworks Instrument Data export가 아니다** — drop.dk의 리깅 포인트/하중
(rigging point/load) CSV다. 헤더 `Name,PT-NAME,X_Coordinate,Y_Coordinate,LOAD`, 픽스처 타입·유니버스·
DMX 주소 컬럼이 전부 없다(주소 계열 컬럼 0개, `ADDRESS_FAMILY_FIELDS` 교집합 0). 줄바꿈은 CR 전용
(classic Mac 스타일 — `\r` 120개, `\n` 0개). 따라서 M0의 실물 검증 산출물(ASSUMPTION-68~70 판정)로
쓸 수 없다 — M0/M8은 계속 BLOCKED다. 이 파일은 오직 **REQ-VWX-003(패치 출처 아님 거부) 경로의 실물
음성(negative) 사례**로만 활용했다 — `server/tests/fixtures/vwx/drop_dk_rigging_not_a_vectorworks_export.csv`
(+ 동 디렉터리 `README.md`가 출처·특성을 기록)로 커밋해 회귀 픽스처로 승격했다.

**이 실물 파일 투입이 결함 2건(P0)을 드러냈다 — 코디네이터가 직접 실측·재현·보고, 본 워커가 수정·검증.**

- **결함 1(P0) — CR 전용 줄바꿈에서 예외가 툴 경계 밖으로 탈출.** 재현:
  `reg.dispatch(ToolCall(name='precheck_vectorworks_diff', arguments={'file_content_base64': <파일 base64>}))`
  → `_csv.Error: new-line character seen in unquoted field`
  (`server/vwx/reader.py:117 _split_rows` → `:136 _choose_delimiter` → `:248 _read_text` → `:289 read`).
  원인: `io.StringIO(text)`를 `newline=''` 없이 만들어 `csv.reader`에 넘겼다 — bare `\r`이 필드 내부
  개행으로 오인됐다. REQ-VWX-004는 "명시적으로 실패"이지 예외 투척이 아니며, 리포 비협상 원칙
  (`server/prechk/patch.py:15-21`)을 위반했다.
  **수정**: ① `_normalize_newlines()`로 CR 전용·CRLF·LF를 파싱 전 전부 LF로 통일 + `newline=''`
  적용(`server/vwx/reader.py`). ② 정규화 이후에도 csv 계층이 거부할 수 있는 입력(따옴표 불균형 등)을
  `_MalformedCsv` 내부 신호로 흡수해 신규 `READ_FAILURE_MALFORMED_CSV` 구조화 실패로 변환 —
  `_read_text`가 예외를 최종 흡수한다. ③ **방어선 2중화**: `server/orchestrator/tools.py`의
  `precheck_vectorworks_diff` 핸들러 자체에도 read→columns→address→rig→diff 파이프라인 전체를 감싸는
  `try/except Exception`을 추가해, reader.py 이후 계층(예상 못한 예외)도 툴 경계를 절대 넘지 않게 했다.
  **검증**: CR 전용·CRLF·LF 3종 + 몽키패치로 강제 유발한 csv 예외 1종 회귀 테스트 4건
  (`test_vwx_reader.py::TestNewlineVariantsNeverEscapeAsExceptions`) + 실물 파일 dispatch 종단 테스트 2건
  (`test_vwx_tool.py::TestRealWorldNegativeSampleEndToEndThroughDispatch`). **비공허성**: 수정 전 코드로
  되돌려(`git stash`) 재실행한 결과, `test_vwx_reader.py` 전체가 `ImportError`(신규 상수 부재)로
  collection 자체가 실패했고, `test_vwx_tool.py`의 신규 2건은 정확히 위와 동일한 `_csv.Error`로
  실패함을 직접 확인했다(수정 되돌림 없이는 재현되지 않는 새 테스트임을 증명).

- **결함 2(P0) — 패치 출처가 아닌 파일에 "이상 없음"을 내준다.** 재현(LF로 바꿔 예외를 우회): `is_error:
  False`, `{"designed_rig": {"fixture_count": 0}, "diffs": {전부 빈 배열}}` — "설계 0대·차이 0건"이
  "도면과 콘솔이 일치"로 오독될 수 있는 거짓 안전 신호였다. 부수 원인: `_choose_delimiter`가 tab을 먼저
  순회하고 `score > best[3]`(엄격한 초과)만으로 갱신해, 별칭 매칭이 전부 0으로 동점인 파일에서 tab이
  최초 채택된 채 절대 교체되지 않았다 — comma로 쪼개면 5컬럼짜리 진짜 구조가 나오는 이 파일도 tab
  순회 우선순위 때문에 단일 컬럼(`col_0`) 쓰레기 구조 121개 레코드로 오분류됐다.
  **수정**: ① `_column_width_score()`를 도입해 점수 동점 시 **다중 컬럼 일관성이 더 높은** 구분자를
  우선 채택하도록 `_choose_delimiter`의 타이브레이크를 수정. 이 파일은 이제 comma(5컬럼, `_uniform_width`
  참)로 정확히 채택되고, 별칭 매칭 헤더가 여전히 0(2 미만)이므로 `READ_FAILURE_BLOCK_UNDETECTED` 단일
  구조화 거부(레코드 0건)로 귀결된다 — 120개 개별 `min_record_incomplete`가 아니라 명확한 단일 거부다.
  ② 신규 판정 코드(`READ_FAILURE_MALFORMED_CSV`)는 `server/vwx/reader.py`의 **자유형 문자열**
  `ReadFailure.kind`이며 `VWX_CLOSED_VOCABULARIES`(diff_kind·skipped_check_kind만 검증) 대상이 아니다 —
  등록 불필요. `server/prechk/**`는 완전히 비접촉 유지(아래 PRESERVE 확인).
  **검증**: `_choose_delimiter` 타이브레이크 단위 테스트 2건 + 실물 파일 단일 구조화 거부 검증 2건
  (`test_vwx_reader.py::TestDelimiterTieBreakPrefersMultiColumnStructure`,
  `::TestRealWorldNonPatchSourceIsRejectedStructurally`) + 툴 dispatch 종단 검증 1건
  (`test_vwx_tool.py::test_real_sample_is_not_reported_as_a_clean_zero_diff_match` — `read_failures`
  1건 이상 & 10건 미만임을 직접 assert, "수정 전엔 120개였다"를 주석으로 명시). **비공허성**: 결함 1과
  동일한 stash-and-rerun으로 재확인 — 수정 되돌리면 이 테스트들도 함께 실패한다(신규 상수 의존).

**재검증(오케스트레이터 직접 실측, 수정 후 최종 HEAD)**:
```
uv run pytest server/tests -q → 4812 passed, 7 skipped, 1 warning in 90.69s
```
착수 baseline(이 회차) `4801 passed, 7 skipped` 대비 **+11**(신규 회귀 테스트: reader 9건 + tool 2건),
회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_*.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_*.py server/orchestrator/tools.py → 15 files already formatted
```
`server/safety/console.py:292,346` · `server/tests/test_web_dash.py:523`의 E501 3건은 b1a630e 시점
선재 결함이며 손대지 않았다(PRESERVE·범위 밖, 코디네이터 지시).
```
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ \
  server/prechk/__init__.py server/prechk/inventory.py server/prechk/patch.py \
  server/prechk/report.py server/prechk/footprint.py server/prechk/macro.py server/prechk/query.py \
  server/prechk/verdicts.py \
  server/paperwork/data.py server/paperwork/render.py server/paperwork/output.py server/looks/
→ (완전 빈 출력, exit=0)
```

### 결함 2 잔존 교정 라운드 (2026-08-05, v0.1.2) — 1차 수정은 미충족이었다

**정직한 기록**: 위 결함 2 수정(1차)은 `read_failures`를 채우는 데는 성공했지만 **핵심을 놓쳤다.**
코디네이터가 직접 재현해 지적한 대로, 사용자·모델이 실제로 읽는 단 하나의 한국어 문장인
`summary_ko`가 여전히 **"차이 없음"으로 시작**했다 — 재현 입력(별칭에 잡히는 헤더 + 주소 계열
컬럼 0개: `Instrument Type,Position,Purpose,Unit Number`)에서 `summary_ko`가 `"도면 픽스처
0개. 차이 없음. …"`을 냈다. `read_failures`에 `not_patch_source`가 있어도, 사람이 실제로 읽는
문장은 "패치 출처 아님"이 아니라 "차이 없음"이었다 — 대조를 아예 수행하지 않았음에도 "찾아봤는데
일치한다"로 오독될 수 있는 거짓 안전 신호였다. `diffs`도 여전히 빈 배열 3종(`missing_in_console:
[]` 등)이라 "찾아봤는데 없다"로 읽혔다.

**교정 (`server/vwx/report.py`)**:
- `_rejection_reason()` / `comparison_performed()` 신설 — `read_failures`에 `not_patch_source`
  또는 `worksheet_block_undetected`(결함 1 경로도 동일 규칙 적용, 요구사항 2)가 있으면 대조가
  성립하지 않은 것으로 판정한다.
- `summary_ko()`: 대조 미성립 시 **거부 사유로 시작**하고 **"차이 없음"이라는 문구를 절대 내지
  않는다** — `"패치 출처로 성립하지 않는다 — {사유}. 대조를 수행하지 않았다. …"` 형태로 고정.
- `_diffs_payload()`(신설, `to_dict()`가 소비): 대조 미성립 시 `diffs`가 3키 빈 배열 대신
  `{"performed": false, "reason": …}`로 축소된다 — 3키 자체가 **생략**돼 "찾아봤는데 없다"와
  구조적으로 구별된다. 정상 대조는 `{"performed": true, ...기존 3키}`로 확장(기존 호출자·테스트
  호환 유지 — 3키 존재 자체는 안 바뀜, `performed` 키만 추가됨).
- 신규 판정 어휘 없음 — `not_patch_source`/`worksheet_block_undetected`는 이미 `reader.py`/
  `diff.py`에 존재하던 자유형 문자열이며 `VWX_CLOSED_VOCABULARIES`(diff_kind·skipped_check_kind만
  검증) 대상이 아니므로 신규 등록이 불필요했다. `server/prechk/**`는 이번에도 완전 비접촉이다.

**SPEC 아티팩트 동기화**: `spec.md` REQ-VWX-023 문구에 이 규칙을 명시하도록 v0.1.2로 갱신,
HISTORY에 v0.1.2 행 추가. `acceptance.md`에 `AC-VWX-022 ③`(diffs.performed 구조)·
`AC-VWX-023 ③`(summary_ko "차이 없음" 금지) 기대 결과를 각각 추가(REQ/AC 개수는 불변 — 기존 AC에
하위 항목만 추가). — "코드만 고치고 SPEC을 방치하지 마라"는 지시에 따름.

**회귀 테스트 (비공허성 필수 조건 충족)**:
- `server/tests/test_vwx_report.py::TestStructuralRejectionNeverReadsAsACleanMatch` 신설 3건 —
  `not_patch_source` 케이스 1건 · `worksheet_block_undetected` 케이스 1건(결함 1 경로도 동일 규칙,
  요구사항 2) · `comparison_performed()` 플래그 일치 1건. 각각 "차이 없음" **부재**를 assert하며,
  대조군인 기존 `test_a_fully_clean_comparison_reports_no_difference`(정상 케이스에서 "차이 없음"이
  **실제로 등장**함을 확인)가 문자열 검사기가 죽어있지 않음을 함께 증명한다 — 요구사항 4의 "부재만
  assert하면 공허해지기 쉽다" 지적에 대한 직접 대응.
- `server/tests/test_vwx_tool.py::test_real_sample_is_not_reported_as_a_clean_zero_diff_match`
  (기존 테스트 갱신) — drop.dk 실물 파일이 dispatch 종단까지 `diffs.performed: False` +
  `summary_ko` 거부-사유-시작을 낸다.
- 정상 케이스(주소 열 존재, 차이 있음/없음) 기존 테스트 전량(`test_vwx_report.py`·
  `test_vwx_tool.py`의 `TestPayloadShape` 등)이 그대로 통과함을 재확인 — 이번 교정이 정상 경로를
  건드리지 않았음을 증명한다.

**재검증(오케스트레이터 직접 실측)**:
```
uv run pytest server/tests -q → 4815 passed, 7 skipped, 1 warning in 91.52s
```
이번 라운드 착수 baseline(코디네이터 재실측) `4812 passed, 7 skipped` 대비 **+3**(신규 회귀 테스트
3건), 회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_*.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_*.py → 14 files already formatted
```
PRESERVE diff 재확인: 위 M1~M7 블록의 동일 명령이 이번 라운드 커밋 이후에도 빈 출력이다(아래
결함 2 잔존 교정 커밋 SHA까지 재실측 완료).

### 거짓 안전 신호 3라운드째 교정 (2026-08-05, v0.1.3) — kind 열거가 새는 근본 원인을 불변식으로 닫음

**정직한 기록: 2라운드째 교정도 미충족이었다.** `not_patch_source`/`worksheet_block_undetected`
두 kind에만 걸린 방어는 **트리거를 kind 목록으로 열거**하는 방식이었다 — 그 목록에 없는 새 경로가
생기면 반드시 다시 새는 구조였고, 실제로 코디네이터가 정확히 그 경로를 재현해 지적했다:

```
입력: Instrument Type,Universe,DMX Address,Position
      Robin MMX Spot,1,1,FOH
      Mac Aura,1,43,Truss 1
```
주소 열(`Universe`·`DMX Address`)이 존재해 **판독 자체는 성공**한다(`read_failures = []`). 하지만
`Unit Number`·`Channel` 컬럼이 아예 없어 전 행이 `unit_number`·`channel` 둘 다 공란으로 조인
불가 판정을 받고(`join_key_conflicts` 2건), `designed_rig.fixture_count`가 0으로 떨어진다.
2라운드째 방어는 `read_failures`만 검사했으므로 이 경로를 통과시켜 `diffs.performed: true` +
"차이 없음"을 그대로 냈다 — 직전 교정과 **정확히 같은 종류의 거짓 안전 신호**가 트리거만 바뀌어
재발한 것이다.

**근본 교정 — 트리거 열거를 불변식으로 대체.** `server/vwx/report.py`:
- `comparison_performed()`를 재정의 — 더 이상 `read_failures`의 kind를 검사하지 않고, **불변식
  하나**로 판정한다: `len(self.diff.designed_rig.fixtures) > 0`. 원인이 판독 실패든 조인키
  충돌이든 그 밖의 무엇이든, 비교할 설계 픽스처가 0대이면 대조는 성립하지 않는다 — 결과로
  판정하므로 새 경로가 추가돼도 자동으로 커버된다.
- `_no_fixtures_reason()`(신설) — 픽스처 0대의 **실제 원인**을 우선순위대로 지목한다: ①
  `not_patch_source`/`worksheet_block_undetected`(기존 사유 문구 그대로 유지 — 회귀 테스트가
  검사) → ② 그 밖의 판독 실패(건수 기반 문구) → ③ `join_key_conflicts`(신규 — 충돌 상세를
  최대 3건까지 나열) → ④ 그 무엇도 해당하지 않는 방어적 폴백 문구(이 분기가 실제로 도달하면
  아직 발견되지 않은 새 원인이 있다는 신호로 남겨둔다).
- `_no_fixtures_summary_lead()`(신설) — `summary_ko`의 첫 문장을 원인 종류에 맞게 감싼다.
  구조적 판독 실패는 "패치 출처로 성립하지 않는다 — {사유}", 그 밖은 `_no_fixtures_reason()`이
  이미 완결된 문장이므로 그대로 쓴다.
- `_diffs_payload()`는 변경 없음(이미 `comparison_performed()`를 소비하도록 2라운드째 설계돼
  있었다 — 이번 교정은 그 판정 함수의 **내부 로직만** 재설계했다).
- 신규 어휘 없음 — `join_key_conflicts`의 `.detail`은 이미 `rig.py`가 만드는 필드를 그대로
  읽었을 뿐이다. `server/prechk/**`는 이번에도 완전 비접촉.

**SPEC 아티팩트 동기화 (요구사항 4)**: `spec.md` REQ-VWX-023을 "픽스처 0대 = 미수행" **불변식**
형태로 재정의(v0.1.3), 기존 "read_failure 일 때"로 좁게 읽히던 표현을 제거. `acceptance.md`
AC-VWX-022③·AC-VWX-023③을 동일하게 갱신 — 트리거를 kind 목록으로 서술하지 않고 불변식으로
서술한다. HISTORY에 v0.1.3 행 추가. REQ/AC 개수는 불변(기존 항목의 하위 기대 결과만 갱신).

**회귀 테스트 (`server/tests/test_vwx_report.py::TestZeroFixturesInvariantCoversNonReadFailureTriggers`,
신설 3건)**:
- `test_join_key_conflict_with_no_read_failures_is_still_not_performed` — 코디네이터 재현 입력을
  정확히 재구성(`read_failures=()`이면서 `join_key_conflicts` 2건). `performed: false` ·
  "차이 없음" 부재 · `reason`/`summary_ko` 양쪽에 "조인 키 충돌"이 등장함을 assert. 비공허성:
  재구성한 레코드가 실제로 `join_key_conflicts`를 만듦을 먼저 확인.
- `test_read_failure_paths_still_covered_by_the_invariant` — 기존 두 read_failure 경로(1·2라운드째
  방어 대상)가 불변식 전환 이후에도 여전히 미수행으로 판정됨을 회귀 확인.
- `test_normal_comparison_control_group_still_reports_no_difference` — **비공허성 대조군**: 설계
  픽스처 ≥1이고 실제로 차이가 없으면 `performed: true` + "차이 없음"이 **여전히** 나온다. 이
  대조군이 없으면 불변식이 정상 경로까지 삼켜버린 회귀를 못 잡는다(요구사항 3 명시 사항).

**재검증(오케스트레이터 직접 실측)**:
```
uv run pytest server/tests -q → 4818 passed, 7 skipped, 1 warning in 92.01s
```
이번 라운드 착수 baseline `4812 passed, 7 skipped` 대비 **+6**(2라운드째 신규 3건 + 이번 라운드
신규 3건, 누적), 회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_*.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_*.py → 14 files already formatted
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ server/prechk/{__init__,inventory,patch,report,footprint,macro,query,verdicts}.py server/paperwork/{data,render,output}.py server/looks/ → (완전 빈 출력, exit=0)
```

**교훈 (자기 자신에게 남기는 기록)**: 거짓 안전 신호 방어를 "어떤 kind가 있으면"으로 열거하면,
그 목록 밖의 새 경로가 생길 때마다 같은 결함이 다른 얼굴로 재발한다. 이번처럼 **트리거를
열거하지 말고 결과(픽스처 0대)로 판정**하면 새 경로가 추가돼도 자동으로 커버된다 — 다음에
"이번엔 어떤 kind가 새로 새는가"를 또 찾지 않아도 되는 설계가 됐다(불변식이 다시 새려면
`fixture_count > 0`인데도 대조가 성립하지 않는 경우가 있어야 하는데, 그런 경우는 정의상
존재하지 않는다).

### M0 실물 컬럼 계약 검증 (2026-08-05, v0.1.4) — M0 = PARTIAL

**수령한 파일**: `vectorworks_export_sample_with_data.csv`
(원본: `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/vectorworks_export_sample_with_data.csv`).
UTF-8 BOM · CRLF · 쉼표 구분 · 25컬럼 × 10행. `UID`는 Vectorworks UID 형식, `GDTF Fixture`는
`Martin Professional@MAC Encore Performance CLD` 정품 GDTF 표기. **실물 형식 샘플로 취급한다.**
코디네이터가 현행 파이프라인 통과 결과와 주소 산술을 10행 전수 직접 계산해 실측·보고했다 —
본 절은 그 실측을 오케스트레이터가 재검증한 기록이다.

**오케스트레이터 재검증(직접 실측)**:
```
python3 -c "read → columns → address → rig → diff → report" (10행 전수)
→ encoding=utf-8-sig, path_kind=A, nrec=10, read_failures=()
→ col valid 10 / fail 0, extra keys = {Gobo,Focus,X,Y,Z,'Rotation Z',Pan,Tilt} (8개, 범위 밖)
→ resolved 10, addr_failures=[] (3중 표현 10/10 일치 재확인)
→ fixture_count=10, design_overlaps=(), footprint_data_present=True
→ diffs.performed=true, missing_in_console 10건, quantity_mismatch 1건
→ skipped: fid_cid_identity_unreachable, console_footprint_width_injection_deferred
```

#### 【1】ASSUMPTION-68 — NEGATIVE(부정) 판정, 별칭표 확장으로 해소

`research.md` §3 별칭 테이블이 실물 헤더와 **합치하지 않았다** — 실물 컬럼 10개가 원래 별칭표
밖으로 떨어졌다: `Fixture Name`·`GDTF Fixture`·`Gobo`·`Focus`·`X`·`Y`·`Z`·`Rotation Z`·`Pan`·`Tilt`.

**정규 필드로 승격한 2개** (`server/vwx/columns.py` `ALIAS_TABLE` 확장, REQ-VWX-026 신설):
- `fixture_name` ← `Fixture Name`/`FixtureName`/`Instrument Name`. 콘솔에서 실제로 읽을 수 있는
  4개 화이트리스트 속성(`server/prechk/inventory.py` `PROPERTY_WHITELIST`) 중 하나가
  `FixtureRecord.name`이므로, 이름은 도면·콘솔 양쪽에서 다 관측 가능한 몇 안 되는 축이다 — 대조
  조인이 (유니버스,주소)+타입뿐이었던 것에 비해 놀리고 있던 신호였다. `symbol_name`과는 정규화
  키가 다름을 테스트로 못박았다(합치지 않았다).
- `gdtf_fixture` ← `GDTF Fixture`/`GDTFFixture`. 자유문자열 `Fixture Type`보다 정규화된 제조사@모델
  식별자다. `mode`의 `GDTF Fixture Mode` 별칭과 정규화 키 충돌이 없음(`gdtffixture` vs
  `gdtffixturemode`)을 테스트로 확인했다. `DesignedFixture.match_type`(신설)이 타입 퍼지 매칭에서
  이 값을 우선 사용하고, 없으면 `instrument_type`으로 폴백한다(`diff.py`의 두 지점 — 콘솔 대조
  매칭·수량 집계 키 — 모두 `match_type`으로 갱신).

**범위 밖으로 남긴 8개** — `Gobo`·`Focus`·`X`·`Y`·`Z`·`Rotation Z`·`Pan`·`Tilt`는 여전히 `extra`
로 보존된다(REQ-VWX-006, 코드 변경 없이 기존 동작 그대로). **3D 좌표(X/Y/Z/Rotation Z/Pan/Tilt)가
CSV 워크시트로도 나온다 — 3단계(MVR/GDTF) 전유물이 아니었다.** extra 보존 결정(REQ-VWX-006) 덕에
후속 SPEC이 재파싱 없이 쓸 수 있다.

**문서-구현 드리프트 정리**: `research.md` §3에 `frame_size`/`focus`/`wattage`/`weight`가 "정규 필드
후보"로 언급돼 있었으나 `ALIAS_TABLE`(구현)에는 등록돼 있지 않았다 — 기능적으로는 문제없다(미등록
컬럼은 이미 `extra`로 보존되므로). **정본은 `ALIAS_TABLE`(구현)이다** — `research.md`는 조사
기록이지 구현 약속이 아니다. 이 4개의 정규 필드 승격 여부는 범위 밖 결정으로 남긴다(`research.md`
해당 행에 이 정리를 직접 기록했다).

#### 【2】주소 3중 표현 교차검증 — REQ-VWX-027 신설

이 샘플의 주소 산술을 오케스트레이터가 10행 전수 재계산해 코디네이터 실측과 일치함을 확인했다:
`Universe=1` 고정, `DMX Address` = 1,39,77,115,153,191,229,267,305,343(stride 38),
`Absolute Address == DMX Address`가 10/10 일치하며 공식 `(u-1)*512+a`와 전수 일치한다 — **음성
대조군**이다.

`server/vwx/address.py`의 Universe+DMX Address 최우선 분기에 교차검증을 추가했다 — 세 표현이
모두 있으면 `absolute == (u-1)*512+a`를 검사하고, **불일치해도 Absolute Address로 유니버스를
역산하지 않는다**(추측 금지, REQ-VWX-009와 동일 원칙) — `Universe`+`DMX Address` 조합을 그대로
채택하고 구조화된 경고(`address_triple_mismatch`)로만 보고한다. 이 샘플에는 양성(불일치) 케이스가
없으므로 합성 픽스처로 별도 증명했다(`test_vwx_address.py::TestTripleRepresentationCrossCheck`).

`ASSUMPTION-69`(Absolute 단독 파일 존재)는 **이 샘플로 해소되지 않는다** — Universe+DMX Address가
항상 함께 있어 역산 경로 자체가 실행되지 않았다. 다만 **위험도는 낮아졌다** — 이 교차검증이 있으면
향후 Absolute 단독 파일이 나타나도 3중 표현이 동시에 존재하는 다른 레코드들에서 조용한 오역산을
잡아낼 여지가 생겼다(간접 완화 — 직접 해소는 아니다).

#### 【3】설계 측 구간 겹침 판정 — REQ-VWX-028 신설, 실제로 수행됨

이전엔 `footprint_overlap_descope`("DMX Footprint 폭 출처 미주입")가 항상 떴다. 이 샘플에는
`DMX Footprint`(38, 전 행)가 있고 이미 `footprint`로 파싱되고 있었으므로 — **설계 측
(universe, address, footprint)만으로 구간 겹침을 실제로 계산하도록 구현했다**(`server/vwx/rig.py`
`_compute_design_overlaps`, `DesignedRig.design_overlaps`/`footprint_data_present` 신설).

- **스코프**: 설계 도면 내부의 주소 구간 겹침으로 한정했다. `server/prechk/patch.py`의
  `FootprintPolicy.widths`(콘솔 SLOT 키)는 건드리지 않았다 — `server/prechk/**`는 PRESERVE다.
  콘솔 측 폭 주입((유니버스,주소) 조인 이후에나 가능한 2차 작업)은 이번엔 하지 않았고, 그 이유를
  새 미수행 판정(`console_footprint_width_injection_deferred`)으로 `skipped_checks`에 남겼다.
- 이 샘플은 stride(38) == footprint(38) → **겹침 0이 정답**이다(음성 대조군, 완벽 패킹).
  **양성 케이스(stride < footprint)는 합성 픽스처로 만들어 비공허성을 증명했다**
  (`test_vwx_rig.py::TestDesignSideOverlapDetection::test_stride_smaller_than_footprint_is_caught_as_an_overlap`)
  — 실제로 겹침 1건이 잡힘을 확인했다.
- VW 자체 다중패치는 기존 `vw_patch_conflicts` 규약과 독립적으로 공존하며 실패시키지 않는다(회귀
  테스트로 확인).

#### 【4】M0 상태 — PARTIAL, 이 샘플의 한계 (정직한 기록)

- `ASSUMPTION-68`: **부정 → 별칭표 확장(fixture_name·gdtf_fixture)으로 해소.** 위 【1】.
- `ASSUMPTION-69`: **미해소** — Absolute 단독 파일이 아니다. 【2】의 교차검증이 위험을 완화했을
  뿐 직접 해소는 아니다.
- `ASSUMPTION-70`: **미해소, 전혀 건드리지 못함** — 이 파일은 `path_kind=A`(flat 단일 테이블)라
  경로 B 워크시트 그리드(제목행·DB헤더행·서브행·소계행) 휴리스틱을 **한 번도 실행하지 않았다.**
- **이 샘플이 덮지 못하는 것**(M8 종단 검증을 이걸로 닫으면 안 되는 이유 — 행복 경로만 검증했다):
  단일 유니버스 · 단일 픽스처 타입 · `Device Type` 열 없음(액세서리 구분 불가) · `Part Index`
  없음(멀티셀 접기 미검증) · `System` 열 없음(멀티시스템 차단 미검증) · 미패치 행(주소 0/공란)
  없음 · 조인키 중복 없음 · 경로 B 워크시트 아님 · 탭 구분 아님(경로 A tab-text 실물 미검증) ·
  구간 겹침 양성 케이스 없음(합성으로만 증명) · 주소 3중 표현 불일치 케이스 없음(합성으로만 증명).
- **결론**: `M0 = PARTIAL(컬럼 계약 1건 실물 검증 — ASSUMPTION-68 해소, 69/70 미해소)`,
  `M8 = BLOCKED 유지`, `run_status = partial-blocked 유지`. 사용자가 경로 B 워크시트 export 또는
  Absolute 단독 파일을 추가로 제공해야 69/70이 닫힌다.

**픽스처 커밋**: `server/tests/fixtures/vwx/vectorworks_export_sample_with_data.csv`(원문 그대로).
`server/tests/fixtures/vwx/README.md`에 출처·성격(양성 사례)·덮는 범위·안 덮는 범위를 기록했다
(기존 drop.dk 음성 픽스처 항목은 그대로 유지).

**SPEC 아티팩트 동기화**: `spec.md` REQ-VWX-026~028 신설(v0.1.4), ASSUMPTION-68~70 판정 갱신,
HISTORY v0.1.4 행 추가. `acceptance.md` AC-VWX-027~029 신설, §C.0 역추적표(REQ 28/28) ·
§C.0a 마일스톤표(M2/M3/M5 각 +1, 합 29) 갱신. `plan.md` §B M2/M3/M5의 `- **AC**:` 줄 갱신 +
헤더에 v0.1.4 요약 추가.

**회귀 테스트 (신규 클래스, 비공허성 대조군 동반)**:
- `test_vwx_columns.py::TestFixtureNameAndGdtfFixtureAliases`(5건) — 별칭 해석, symbol_name/mode
  비충돌, extra 승격 종단.
- `test_vwx_rig.py::TestFixtureNameAndGdtfFixtureFields`(3건, match_type 폴백 대조군 포함) +
  `::TestDesignSideOverlapDetection`(4건, 음성/양성/멀티유니버스/footprint없음 대조군).
- `test_vwx_address.py::TestTripleRepresentationCrossCheck`(5건, 음성 2·양성 1·종단 1·회귀 1).
- `test_vwx_diff.py::TestDesignSideFootprintDeferralNote`(2건, 있음/없음 대조군).
- `test_vwx_tool.py::TestRealWorldPositiveSampleEndToEndThroughDispatch`(5건) — 이 실물 파일
  기반 종단 테스트: 10 픽스처 확인 · 주소 교차검증 통과(경고 없음) · 겹침 0(필드 존재로 확인,
  생략 아님) · fixture_name/gdtf_fixture가 quantity_mismatch의 instrument_type에 gdtf 값으로
  반영됨(extra 아님을 간접 확인) · 콘솔 측 폭 주입 이연 판정 노출.

**재검증(오케스트레이터 직접 실측)**:
```
uv run pytest server/tests -q → 4842 passed, 7 skipped, 1 warning in 90.47s
```
이번 라운드 착수 baseline(3라운드째 종료 시점) `4818 passed, 7 skipped` 대비 **+24**(이번 라운드
신규 회귀 테스트), 필수 최소 기준선 `4812 passed, 7 skipped` 대비로는 **+30**. 회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_*.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_*.py → 14 files already formatted
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ server/prechk/{__init__,inventory,patch,report,footprint,macro,query,verdicts}.py server/paperwork/{data,render,output}.py server/looks/ → (완전 빈 출력, exit=0)
```

### 조인 키 스코프 결함 수정 (2026-08-05, v0.1.5) — 실사용 리그 대부분이 전멸하던 결함

**결함 (코디네이터 재현, 툴 dispatch 경유)**: `unit_number`를 사실상 전역 유일 조인 키로 취급하고
있었다. 재현 입력:

```
헤더: Fixture Type,Universe,DMX Address,Unit Number,Position
A) MAC Encore,1,1,1,Upstage Truss
   Source Four,2,1,1,FOH
```

서로 다른 포지션(`Upstage Truss`·`FOH`)에 있는 **서로 다른** 픽스처 2대가 둘 다 `Unit Number=1`
이라는 이유만으로 "동일 픽스처의 중복"으로 오판정되어 last-write-wins 병합을 거부하고
`join_key_conflicts` 1건으로 **둘 다 탈락**했다 — `fixture_count: 0`이 되어 v0.1.3의 "픽스처
0대 = 대조 미수행" 불변식까지 걸려 "대조를 수행하지 않았다"로 보고됐다. Vectorworks에서
`Unit Number`는 **포지션 안에서만 유일**하다(트러스마다 1번부터 다시 센다 — 정상적인 도면이고
예외가 아니다, 브리핑이 이미 경고했던 함정이다). 지금 구현은 포지션이 2개 이상인 리그를
**사실상 전부 전멸**시켰다.

**왜 M0 실물 샘플이 이 결함을 못 잡았는가 — 정직한 기록**: `vectorworks_export_sample_with_data.csv`
(v0.1.4가 검증한 실물 샘플)는 `Position`이 `'Upstage Truss'` **하나뿐**이었다. 포지션이 하나면
"포지션 안에서만 유일"과 "전역으로 유일" 두 스코프가 우연히 일치하므로 결함이 드러나지
않는다 — **통과한 것은 우연이지 검증된 것이 아니다.** 이것이 정확히 M0 PARTIAL의 "행복 경로만
검증했다" 한계 목록에 이미 적혀 있던 항목("단일 포지션") 중 하나가 실제로 결함을 가렸던
사례다. 조용히 병합하지 않고 거부한 것 자체는 옳았다 — 고칠 것은 **키의 스코프**였다.

**수정 (`server/vwx/rig.py`)**: 조인 키 우선순위를 재정의했다 — ① `channel`(Vectorworks
**전역 유일** 디자이너 번호, 문서상 비숫자 "channel name"일 수 있어 항상 문자열로 다룬다,
`_fold_by_channel` 신설) → ② `(position, unit_number)` **복합 키**(channel이 없거나 공란일
때만, `_fold_by_position_and_unit_number` 신설 — position 공란도 하나의 스코프로 취급해
공란끼리만 충돌) → ③ 둘 다 없으면 기존대로 조인 불가 거부. `_fold_group`이 사람이 읽을 수 있는
스코프 라벨(예: `"포지션 'FOH' 내 unit_number '1'"`)을 받아 충돌 사유에 **어느 스코프에서
중복인지** 명시하도록 갱신했다. `part_index` 멀티셀 폴딩 규약은 새 스코프 안에서도 그대로
유지된다(회귀 테스트로 확인).

**부수 발견 — 기존 테스트 1건의 전제가 바뀜**: `TestVectorworksNativeConflictPassthrough`의
"Identical Patch" 테스트가 두 행에 **문자 그대로 같은 `channel` 값**("1")을 부여하고 있었다.
channel이 전역 유일 최우선 키가 된 이상, 정말로 같은 channel 값을 가진 두 행은 서로 다른
2대의 픽스처가 아니라 **조인 키 중복**이다 — 이제 이 시나리오는 `join_key_conflicts`로 먼저
잡히고 `_classify_vw_conflicts`(서로 다른 조인 키로 만들어진 별개 픽스처가 우연히 같은 주소를
공유하는 경우) 단계에는 도달하지 않는다. 테스트를 이 새 행동을 검증하도록 갱신했다(설명 주석
포함) — `VW_IDENTICAL_PATCH`/`VW_PATCH_CONFLICT`/`VW_PATCH_OVERLAP` 분류 코드 자체는 무변경이며
나머지 두 VW 충돌 테스트(서로 다른 channel · channel 부재)는 그대로 통과한다.

**회귀 테스트 (`test_vwx_rig.py::TestUnitNumberIsScopedToPositionNotGlobal` 신설 7건 +
`test_vwx_tool.py::TestUnitNumberScopeFixEndToEndThroughDispatch` 신설 2건)**:
- 코디네이터 재현 A(서로 다른 포지션의 Unit 1 두 개) → `fixture_count 2`, 충돌 0.
- **비공허성 대조군** — 같은 포지션 안의 Unit 1 두 개 → 충돌 1건, 사유에 "포지션"·"FOH" 명시
  (스코프가 죽어있지 않음을 증명 — 이게 없으면 이번 수정이 충돌 탐지 자체를 통째로 죽인 것을
  못 잡는다).
- 포지션 공란은 그 자체로 하나의 스코프(공란끼리만 충돌, 공란 vs 실포지션은 서로 다른 스코프).
- channel이 있고 unit_number가 전 행 공란인 파일 → channel로 정상 조인(3행 전량).
- channel이 비숫자 문자열("House Left A"/"House Left B")이어도 정상 조인.
- part_index 멀티셀 폴딩이 새 스코프에서도 유지됨.
- 실물 샘플(`vectorworks_export_sample_with_data.csv`)이 **여전히 10 픽스처**(직접 재실측 확인
  — 이 파일은 포지션 1종이라 이번 수정으로 영향받지 않는다).

**비공허성 — stash-and-rerun**: 수정 전 코드로 되돌려 신규 테스트를 재실행한 결과, 코디네이터
재현과 정확히 일치하는 4건이 실패했다(`fixture_count`가 기대와 다르게 0으로 나옴) — 수정
되돌림 없이는 재현되지 않는 새 테스트임을 직접 확인했다.

**SPEC 아티팩트 동기화**: `spec.md` REQ-VWX-016을 조인 키 우선순위(①channel→②(position,
unit_number)→③거부) 형태로 재정의(v0.1.5), HISTORY v0.1.5 행 추가. `acceptance.md` AC-VWX-016을
동일 스코프로 갱신 + 회귀 시나리오(③~⑦) 추가. REQ/AC 개수는 불변(28/29, 기존 항목의 내용만
갱신) — §C.0/§C.0a 갱신 불필요.

**경로 B(워크시트 그리드) 합성 검증 — 코디네이터 요청, ⚠ 합성물이지 실물 아님**: 손으로
`server/tests/fixtures/vwx/synthetic_path_b_worksheet_grid.csv`를 만들었다(제목행 + DB헤더행 +
데이터 4행(포지션 2종, 조인 키 스코프 수정 재현 조건과 같은 형태) + 소계행, CRLF). 이 파일로
**처음으로** 경로 B 판별·헤더 구조적 식별·소계행 배제 휴리스틱이 실행됐다 — M0 실물 샘플은
`path_kind=A`(flat 단일 테이블)라 이 경로를 한 번도 타지 않았었다. 직접 실측 결과:
`path_kind=B` 정확히 판별 · 소계행 1건이 `worksheet_subtotal_row`로 데이터에서 구조적으로
배제 · 데이터 4행 전량 판독 · 새 조인 키 스코프도 이 파일 안에서 정상 동작(fixture_count 4,
충돌 0) — **전부 확인됨**. 그러나 **이건 합성물이므로 실물 워크시트 export의 실제 마커·서식·
인코딩 특이성을 대변하지 않는다 — `ASSUMPTION-70`은 여전히 미해소로 남는다.** 실물로 오인해
GO로 닫으면 안 된다는 경고를 픽스처 README에 명시했다(`server/tests/fixtures/vwx/README.md`).
회귀 테스트: `test_vwx_tool.py::TestSyntheticPathBGridEndToEndThroughDispatch`(신설 1건).

**재검증(오케스트레이터 직접 실측)**:
```
uv run pytest server/tests -q → 4852 passed, 7 skipped, 1 warning in 91.88s
```
이번 라운드 착수 baseline `4842 passed, 7 skipped` 대비 **+10**(join-scope 회귀 9건 + 경로 B
합성 검증 1건), 회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_*.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_*.py → 14 files already formatted
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ server/prechk/{__init__,inventory,patch,report,footprint,macro,query,verdicts}.py server/paperwork/{data,render,output}.py server/looks/ → (완전 빈 출력, exit=0)
```

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

### 실물 샘플 3종 투입 — 결함 1(P0)/2(P1)/3(P1) 수정, ASSUMPTION-69 NEGATIVE 확정 (2026-08-05, v0.1.6)

**착수 baseline (오케스트레이터 직접 실측)**: `4852 passed, 7 skipped, 1 warning in 92.07s` — 코디네이터가 직접 실측한 baseline(`4852 passed / 7 skipped · ruff clean · PRESERVE diff 0`)과 정확히 일치.

**투입 파일 3종 (전부 REAL)**: `01_pathB_worksheet_instrument_data_full.csv`(UTF-8 BOM·CRLF·29컬럼×20행, 멀티시스템·멀티셀·DMX/비-DMX 액세서리·미패치·집계행 3건이 전부 한 파일에 의도적으로 섞임), `02_pathB_worksheet_absolute_address_only.csv`(같은 리그를 Universe/DMX Address 없이 Absolute Address만으로 재수출), `03_pathA_export_instrument_data_no_header.txt`(탭 구분·LF·헤더 없음·28필드×17행). 코디네이터의 직접 실측: 3파일 전부 `fixture_count=0`(01/02는 멀티시스템 차단, 03은 헤더없음→전 행 min-record 미달) — 거짓 안전 신호는 없었으나(미수행 사유는 정확히 보고됨) 전부 사용 불가였다.

**결함 1(P0) — 멀티시스템이 설계 측 산출 전체를 무너뜨림.** `server/vwx/address.py:109`(당시 줄번호)의 `classify_and_resolve`가 System 2개 이상 관측 시 **전 행**을 `blocked`로 차단했다 — 콘솔에는 System 개념이 없어 대조(diff.py)만 미수행이어야 할 것을, 설계 측 리그 구축(rig.py) 단계에서부터 차단해 `fixture_count`가 0으로 무너지고, 그로 인해 `device_type_column_present`까지 파생적으로 False가 됐다(별개 결함이 아니라 빈 records 리스트의 파생 증상).

**수정**: 주소 아이덴티티를 `(system, universe, address)`로 확장했다.
- `address.py`: `classify_and_resolve`에서 `len(system_letters) >= 2` 차단 분기를 제거 — 개별 레코드 해석은 System 수와 무관하게 항상 진행한다. System 문자 자체는 `fields["system"]`(원문 컬럼 값)에 이미 보존돼 있어 별도 필드 추가가 불필요했다.
- `rig.py`: `DesignedFixture`에 `system: str | None` 필드 신설(`_normalize_system` — 대문자 첫 글자로 정규화, 공란은 단일 암묵 스코프 `None`). `_compute_design_overlaps`(구간 겹침)와 `_classify_vw_conflicts`(VW 자체 패치 충돌)를 `universe` 단독 버킷팅에서 `(system, universe)`/`(system, universe, address)` 버킷팅으로 재정의 — System이 다르면 같은 (universe, address)라도 겹침·충돌로 오탐하지 않는다. `DesignedRig`에 `observed_systems: frozenset[str]` 신설(전체 레코드에서 계산).
- `diff.py`: `compare()`가 `len(designed_rig.observed_systems) >= 2`일 때만 콘솔 조인(`missing_in_console`/`quantity_mismatch`)을 건너뛴다 — `address_collision`(콘솔 실측 자체 내부 판정, 설계 리그와 무관)은 System 수와 무관하게 항상 수행한다. 신규 `skipped_checks` kind `multi_system_mapping_absent` 신설, `server/vwx/report.py`의 `SKIPPED_CHECK_KIND_VWX`/라벨 표(`VWX_CLOSED_VOCABULARIES` 패턴 그대로 계승)에 등록.
- `report.py`: `comparison_performed()`가 `len(fixtures) > 0 and len(observed_systems) <= 1`로 확장. `diffs.reason`은 **"픽스처 0대" 원인과 "멀티시스템 매핑 부재" 원인을 절대 뭉뚱그리지 않는다**(`_diffs_not_performed_reason` 신설이 두 사유 함수를 분기) — 이것이 코디네이터가 요구한 "distinct from generic read failure" 요건이다. `summary_ko()`도 멀티시스템일 때는 "판독 실패"가 아니라 먼저 "도면 픽스처 N개"(설계 측 산출이 정상임)를 밝힌 뒤 멀티시스템 사유로 이어간다.

**결함 2(P1) — 집계행·비-DMX 액세서리가 "판독 실패"로 오세짐.** SUBTOTAL/TOTAL 집계행 3건과 Top Hat(비-DMX 액세서리) 1건이 `min_record_incomplete` 판독 실패로 잡혀, 깨끗한 파일이 "판독 실패 4건"으로 오보고됐다(코디네이터 직접 실측). "읽을 수 없었다"와 "읽었지만 의도적으로 제외했다"는 다른 사건이다.

**수정**: `columns.py::resolve_columns`가 3-튜플 `(records, failures, excluded_rows)`을 반환하도록 확장(호출자 전부 갱신 — `server/orchestrator/tools.py` + 테스트 12곳). 집계행(`Device Type` in {SUBTOTAL, TOTAL})은 최소 유효 레코드 판정 이전에 먼저 분리해 `ExcludedRow(kind=aggregate_row)`로 분류한다. 최소 유효 레코드 미달 레코드 중 `instrument_type`은 있고 주소만 없으며 `Device Type`이 액세서리 계열이면 `ExcludedRow(kind=non_dmx_accessory)`로 분류한다(그 밖은 기존대로 `min_record_incomplete`). `report.py`의 `VwxReport`에 `excluded_rows` 필드 신설, `to_dict()` 최상위에 `excluded_rows` 키 추가, `summary_ko()`가 `excluded_rows`가 있으면 판독 실패 0건이어도 "판독 실패 N건 · 제외 M건(집계행 A · 비DMX 액세서리 B)"를 명시하도록 확장(`_excluded_breakdown_ko`/`_append_read_failure_and_excluded_parts` 신설). 제외행이 없는 파일은 기존 "판독 실패 N건" 단독 문구를 그대로 유지(회귀 테스트로 확인).

**결함 3(P1) — 헤더 없는 경로 A 파일이 행별 실패를 폭주시킴.** 헤더 없는 실물 파일(17행)에서 `columns.resolve_columns`가 `col_0`..`col_27` 자리표시자 헤더로 인해 **17건**의 개별 `min_record_incomplete`를 냈다(코디네이터 직접 실측). "판독 불가"라는 판정 자체는 옳다(REQ-VWX-005가 위치 기반 추측을 금지하므로) — 문제는 그것을 알리는 방식이었다.

**수정**: `columns.py`에 `_is_synthetic_placeholder_header`(정규식 `^col_\d+$` 전량 일치 판정) 신설. `resolve_columns` 최상단에서 이 패턴을 감지하면 행별 루프를 돌기 전에 **파일 단위 판정 1건**(`READ_FAILURE_HEADERLESS_EXPORT`, 실행 가능한 해결책 "Vectorworks의 File > Export > Export Instrument Data에서 'Export field names as first record'를 켜고 다시 내보내라" 포함)만 반환한다. `reader.py`는 **무변경**이다 — 헤더 유무 스니핑 자체(`col_N` 자리표시자 부여)는 이미 정확했고, 이는 REQ-VWX-001의 **긍정 증거**로 기록한다(코디네이터 요청대로 실패가 아닌 설계-대로-동작으로 기술).

**결함 4(P1, 코디네이터 명명 "join-key channel-collision trap") — 직전 라운드(v0.1.5) 조인-키-스코프 수정 자체가 만든 구멍.** 이 실물 파일에서 Channel `"1"`이 3행에 등장한다 — 부모 픽스처(S4 26 1, Unit 2) + 액세서리 2개(Top Hat Unit 2A, Coloram Unit 2B). v0.1.5가 channel을 최우선 조인 키로 승격시켰기 때문에, 액세서리가 부모의 channel 번호를 물려받는 정상적인 Vectorworks 관례와 충돌해 세 행이 하나로 잘못 접힐 뻔했다.

**수정**: `rig.py::build_designed_rig`가 레코드를 먼저 액세서리/비액세서리로 분리(`_is_accessory_row` — `Device Type`에 "accessory" 부분 문자열 포함, 대소문자 무시)한 뒤, 액세서리는 ① channel 우선순위 계층을 **건너뛰고** 곧바로 ②`(position, unit_number)` 계층으로 라우팅한다. 비숫자 unit_number("2A"/"2B")도 기존 `(position, unit_number)` 복합 키 로직이 그대로 문자열로 처리하므로 별도 수정이 불필요했다.

**결함 2 재교정 — `_is_static_accessory`가 액세서리 배제 자체도 잘못 판정하고 있었다.** Top Hat(비-DMX, footprint 0)과 Coloram(DMX 소비, footprint 1)이 **똑같이** `Device Type = "Accessory"` 리터럴을 쓴다 — `STATIC_ACCESSORY = "Static Accessory"` 문자열과의 정확 일치만 검사하던 기존 규칙은 이 파일에서 **둘 다** 걸러내지 못했다(Coloram도 배제하지 못하고, Top Hat도 포함시키지 못했을 것 — 실제로는 Top Hat이 컬럼 해석 단계에서 먼저 주소 부재로 `excluded_rows`에 걸려 rig.py까지 도달하지 않았다). `_is_static_accessory`를 `_is_non_dmx_accessory`로 재작성 — 액세서리 계열(`_is_accessory_row`)이면서 양수 `DMX Footprint`가 없으면 배제한다. **부수 발견**: 기존 테스트 `test_dmx_consuming_accessory_is_included`가 footprint를 아예 지정하지 않은 채(암묵적으로 `None`) "DMX 소비"를 자처하고 있었다 — 새 규칙에서는 이 전제 자체가 틀렸으므로(footprint 없음 = 배제 대상), 명시적으로 `footprint="1"`을 부여하도록 테스트를 재작성했다(비공허성 실제 확보) + 별도로 "리터럴은 같지만 footprint 없어 배제됨" 대조군 테스트를 신설했다.

**여섯 검증 항목 — 전부 실물 파일 01/02로 직접 확인**:
1. **멀티셀 폴딩**: Part Index 1~8(ColorForce 72) → 정확히 1개 픽스처, 대표 행(최솟값) 주소 201, `part_indices == ("1",...,"8")`. `fixture_count`가 8배 부풀지 않음(9개 픽스처 — 8셀 폴딩 1 + 나머지 8개)을 직접 확인.
2. **DMX 액세서리 처리**: Coloram(footprint 1) 포함, Top Hat(footprint 0/공란) 배제 — 결함 2 재교정 절 참조.
3. **미패치 3번째 분류**: Titan Tube(DMX Address 0) → `unpatched_designed`, `missing_in_console`과 다른 코드값임을 직접 assert. 단일 System으로 축소한 서브셋에서 콘솔 조인이 정상 수행되는 상황에서도 미패치는 조인 대상이 되지 않음을 확인.
4. **조인-키 channel-collision trap**: 위 결함 4 참조. 부모(Unit 2)와 액세서리(Unit 2B)가 channel `"1"`을 공유해도 별개 픽스처로 남는다.
5. **System별 절대주소 모호성(ASSUMPTION-69)**: 아래 별도 절.
6. **오버랩 오탐 방지**: `(system, universe)` 버킷팅 후 파일 01의 `design_overlaps`가 정확히 0건(A/U1·A/U2·B/U1 전 구간 확인). System을 무시했다면 A/U1/1과 B/U1/1이 오탐 겹침이었을 시나리오를 별도 재현해 실제로는 겹치지 않음을 확인. 동시에 같은 (system,universe) 안의 진짜 겹침(stride < footprint)은 여전히 잡히는 양성 대조군도 유지.

**ASSUMPTION-69 — NEGATIVE 판정.** 파일 02(Absolute Address만 있고 Universe/DMX Address 없음)로 `A/System U1/abs=1`과 `B/System U1/abs=1`이 완전히 같은 숫자값임을 실물로 확인했다 — `abs=(u-1)*512+a` 공식 자체에는 System을 구분할 변수가 없다. `classify_and_resolve`에 `contiguous_512_confirmed=True`를 강제 주입해 두 System 레코드가 동일한 `(universe, address)`로 역산됨을 직접 재현(`TestPerSystemAbsoluteAddressAmbiguity`). System 문자가 `fields["system"]`으로 **별도 보존**돼야만(=결함 1 수정이 도입한 `(system, universe, address)` 아이덴티티 확장) 두 레코드를 구분할 수 있다 — 이는 결함 1의 수정이 정확히 이 문제의 구조적 해법임을 뜻한다. 기본값(`contiguous_512_confirmed=False`)에서는 여전히 추측하지 않고 `absolute_address_premise_unverified`로 보류함도 재확인(REQ-VWX-009 불변).

**ASSUMPTION-68 — 추가 증거(판정은 v0.1.4 NEGATIVE 유지).** 이번 실물 샘플 3종의 좌표 컬럼 철자(`X Location`/`Y Location`/`Z Location`/`Z Rotation`)가 M0 샘플의 철자(`X`/`Y`/`Z`/`Rotation Z`)와 또 다르다 — 같은 개념을 실물 파일 2건이 서로 다르게 표기한다는 사실 자체가 별칭표 확장 정책을 뒷받침하는 추가 증거다(둘 다 이번 SPEC 범위 밖이라 승격은 하지 않음, `extra` 보존 유지). 신규 관측된 `Notes` 컬럼도 마찬가지.

**ASSUMPTION-70 — PARTIAL 유지 (닫히지 않음, 남은 변형 명시).** 이번 3파일은 "단일 최상단 DB 헤더 + 인라인 집계행" 변형(0번 행이 헤더라 `path_kind=A`로 판독)을 실물로 확인했다 — 집계행이 컬럼 수 불일치가 아니라 `Device Type` 값으로 구조적으로 배제됨을 실측했다. **미검증으로 남은 변형 2종**: ① 헤더 반복형(포지션마다 DB 헤더행이 되풀이되는 워크시트), ② 제목행 선행형(`path_kind=B`로 실제 판독되는, 진짜 제목행 + DB헤더행이 분리된 워크시트 그리드 — `synthetic_path_b_worksheet_grid.csv`는 이 변형을 **합성물로만** 흉내낸다, 실물 아님).

**M8 판단 — 여전히 BLOCKED로 유지 (임의로 닫지 않음).** 여섯 검증 항목이 전부 통과하고 ASSUMPTION-69가 NEGATIVE로 확정됐지만, ASSUMPTION-70이 PARTIAL(변형 2종 미검증)로 남아 있다 — M8(AC-VWX-026, 실물 파일 기반 종단 통합 검증)의 완결 조건은 "경로 B 워크시트 데이터 블록 구조적 식별"이 실물로 검증되는 것이었는데, 지금까지 관측된 실물 경로 B 파일은 전부 `path_kind=A`로 판독되는 (헤더가 0번 행인) 변형뿐이다. 진짜 `path_kind=B`(제목행 선행형) 실물 샘플이 최소 1건 더 확보돼야 M8을 GO로 닫을 수 있다. 이 판단은 임의가 아니라 ASSUMPTION-70의 명시적 PARTIAL 상태에서 직접 도출된다.

**회귀 테스트**: `server/tests/test_vwx_multisystem_real_samples.py`(신설, 30개 — 결함 1~4 각각 전용 테스트 클래스 + 6개 검증 항목 전용 클래스, 전부 실물 파일 01/02/03 또는 코디네이터 재현 조건을 그대로 재현), `test_vwx_address.py::TestMultiSystemAmbiguity`(재작성 3건 — 차단 제거를 검증), `test_vwx_address.py::TestResolveAllPipeline`(재작성 1건), `test_vwx_rig.py::TestAccessoryFiltering`(1건 footprint 명시로 교정 + 신규 대조군 1건). 모든 "0건" 주장에 비공허성 대조군 동반(예: 판독 실패 0건 주장은 코디네이터 재현 4건 대비, 오버랩 0건 주장은 양성 대조군 동반, 헤더없음 1건 주장은 수정 전 17건 대비).

**비공허성 — git stash 재현**: 신규 회귀 테스트 파일(`test_vwx_multisystem_real_samples.py`)을 수정 전 HEAD(`87714e0`)에서 재실행 시 `EXCLUDED_ROW_AGGREGATE` 등 신규 API가 존재하지 않아 **import 자체가 실패**했다(collection error) — 새 테스트가 실제로 새 API 표면을 요구함을 직접 확인.

**픽스처 커밋**: `server/tests/fixtures/vwx/{vectorworks_worksheet_multisystem_full.csv, vectorworks_worksheet_absolute_address_only.csv, vectorworks_export_instrument_data_no_header.txt}`(전부 REAL) 신설, `README.md`에 REAL/SYNTHETIC 표기 + 테스트 벡터 표 추가(합성 픽스처 `synthetic_path_b_worksheet_grid.csv`는 그대로 유지·참조).

**SPEC 아티팩트 동기화**: `spec.md` REQ-VWX-001/007/010/014/016/023 확장(HISTORY v0.1.6 행 + 각 REQ 본문에 `(v0.1.6 — ...)` 인라인 주석), ASSUMPTION-68/69/70 판정 갱신. `acceptance.md` AC-VWX-002/008/011/014/016/022/023 확장. REQ/AC 개수는 **불변**(28/29 — 전부 기존 항목 내용 확장, 신규 번호 없음).

**재검증 (오케스트레이터 직접 실측)**:
```
uv run pytest server/tests -q → 4884 passed, 7 skipped, 1 warning in 91.28s
```
착수 baseline `4852 passed, 7 skipped` 대비 **+32**(신규 파일 30건 + 재작성 테스트로 순증 2건 — `TestMultiSystemAmbiguity` 2→3, `TestAccessoryFiltering` 2→3), 회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_multisystem_real_samples.py server/orchestrator/tools.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_multisystem_real_samples.py → 8 files already formatted
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ server/prechk/{__init__,inventory,patch,report,footprint,macro,query,verdicts}.py server/paperwork/{data,render,output}.py server/looks/ → (완전 빈 출력, exit=0)
```

### 02(절대주소 단독) 재설계 — 거부 대신 근거 등급, 대량 탈락 스코프 한정 (2026-08-05, v0.1.7)

**착수 baseline (오케스트레이터 직접 실측)**: `4884 passed, 7 skipped, 1 warning in 90.29s` — 코디네이터가 직접 실측한 baseline(`4884 passed / 7 skipped · ruff(server/vwx) clean · PRESERVE diff 0`)과 정확히 일치.

**인정 재확인**: 코디네이터가 직전 라운드(v0.1.6)를 전수 재검증한 결과를 그대로 신뢰했다 — 01(멀티시스템 전체 리그, fixture_count 9, 멀티셀 8→1 산술, read_failures 0)·조인 충돌 0(액세서리 channel-collision 구멍 닫힘)·겹침 시스템 버킷팅 비공허 확인(같은 A/U1 겹침 1건, A/U1 vs B/U1 겹침 0건)·다중 시스템 사유 분리·03 판정 1건 통합, 전부 재작업 없이 그대로 둔다.

**문제 1(P0) — 절대주소 단독 파일이 사실상 미지원이었다.** 02 실측: 유효 16행 중 15행 탈락, `fixture_count=1`(Titan Tube만 — Absolute Address=0인 미배정 sentinel만 추측 없이 해석 가능했고, 나머지 15행 전부 `absolute_address_premise_unverified`로 보류됐다). 코디네이터 지적: "의도는 옳지만 결과가 틀렸다" — 이 파일은 사용자가 실제로 요청해 받은 정상 export이고, VW 2019 이하의 기본 컬럼 구성이기도 하다. 리포 교리는 **날조 금지**이지 **파생 금지**가 아니다 — `server/prechk/patch.py`의 `OverlapBasis`(판정을 거부하는 대신 실제로 수행한 비교의 가장 약한 근거를 등급으로 선언)가 정확히 이 상황의 선례였다.

**수정 (`server/vwx/address.py`)**: 절대주소 단독 분기(`classify_and_resolve` 최후 분기)에서 `contiguous_512_confirmed` 게이트를 제거했다 — 이제 항상 `universe = (abs-1)//512 + 1`, `address = (abs-1)%512 + 1`로 역산한다. 대신 새 축 `address_basis`(`ADDRESS_BASIS_DIRECT` / `ADDRESS_BASIS_ABS_CONFIRMED` / `ADDRESS_BASIS_ABS_BACK_CALCULATED`, 약한 순서)를 도입해 근거를 숨기지 않는다 — `contiguous_512_confirmed=False`(기본값, 대부분의 실사용 케이스)는 `absolute_back_calculated`(약함)로, 외부에서 명시적으로 참을 주입하면 `absolute_confirmed`(강함)로 등급을 매긴다. Universe+DMX Address 쌍/조합값 직접 경로는 `universe_address_direct`(가장 강함)다. `READ_FAILURE_ABS_UNVERIFIED` 상수는 실사용 경로가 없어졌지만(grep 대비) 보존만 해뒀다.

**전파 (`server/vwx/rig.py`)**: `ResolvedRecord`·`DesignedFixture` 양쪽에 `address_basis` 필드를 추가해 대표 레코드의 근거를 그대로 물려받는다. `DesignedRig`에 리그 전체 등급(`address_basis` — 실제로 쓰인 근거 중 가장 약한 것, `OverlapBasis._BASIS_ORDER`와 동일한 "약한 순서" 규약)과 `address_basis_note`(등급이 `absolute_back_calculated`일 때만 채워지는 전제 문구, 코디네이터 지정 원문 그대로: "Universes pane이 기본 연속 512블록이라는 전제 위에서 역산했다. Start#/End#를 편집했거나 유니버스를 삭제해 구멍이 있으면 이 유니버스·주소는 틀린다.")를 신설했다. `report.py::to_dict()`가 `designed_rig.fixtures`(픽스처마다 `address_basis` 포함, 전에는 payload에 개별 픽스처 목록 자체가 없었다 — 신설)와 `designed_rig.address_basis`/`address_basis_note`를 노출하고, `summary_ko()`가 리그 등급이 역산이면 전제 문구를 함께 싣는다.

**하드 거부는 좁혔다** — Universe/DMX Address 쌍과 Absolute Address가 **둘 다 있는데 어긋나는** 경우(기존 `address_triple_mismatch`, REQ-VWX-027)에만 역산을 금지하고 직접값을 쓴다. 이 경로는 무변경이다(회귀 테스트로 확인, `TestTripleMismatchStillRejectsDerivation`).

**문제 2(P1) — 대량 탈락 후에도 확신에 찬 대조를 냈다.** 02 수정 전 출력: "도면 픽스처 1개. 수량 불일치 … 1건."(`diffs.performed = true`) — 16행 중 15행이 죽었는데 9대짜리 리그를 1대로 보고 콘솔과 비교해 "수량 불일치"를 단정했다. `fixture_count == 0` 불변식은 1이니까 걸리지 않았다 — 불변식에 동반 규칙이 없었다.

**수정 (`server/vwx/rig.py`, `server/vwx/report.py`)**: `build_designed_rig`가 `candidate_count`(컬럼 해석을 통과한 후보 행 수) 선택 인자를 받아 `dropped_row_count = candidate_count - len(records)`, `scope_qualified = dropped_row_count > 0`, `scope_note`를 계산한다 — `server/prechk/patch.py`의 `scope_qualified`/`scope_note`/`SCOPE_QUALIFIER`("관측된 범위에서") 규약을 vwx 자체 구현으로 재현했다(PRESERVE 파일은 import하지 않는다). `server/orchestrator/tools.py`의 실제 파이프라인이 `candidate_count=len(column_records)`를 넘긴다 — `column_records`는 이미 집계행·비-DMX 액세서리 같은 의도적 제외(`excluded_rows`)를 걷어낸 뒤의 수이므로, 분모는 정확히 "읽으려 했으나 실패한 행"이다(문제 2 요건 c). `summary_ko()`는 탈락 비율(`dropped_row_count / candidate_row_count`)이 **30% 이상**이면 "도면 픽스처 N개"보다 스코프 한정 문구를 먼저 낸다 — 30%는 오탈자 한 줄 수준의 잡음(수 % 이내)과 리그 대부분이 무너진 경우(02의 원래 증상, 93.75%)를 확실히 가르는 값으로 골랐다(코드 주석에 근거 명시). 임계 미만이지만 0건은 아닌 경우 문구는 여전히 붙되 꼬리에 붙는다 — 정보를 숨기지 않되 맨 앞을 차지하지는 않는다. 탈락 0건이면 스코프 한정 자체가 붙지 않는다(01로 확인).

**부수 발견**: performed=True 분기(정상 대조 경로)가 `excluded_rows` 구별(직전 라운드 결함 2 수정)을 전혀 반영하지 않고 있었다 — performed=False 분기만 `_append_read_failure_and_excluded_parts`를 썼다. 이번에 정상 대조 경로도 같은 헬퍼를 쓰도록 통일했다(스코프 한정 로직을 추가하며 같은 메서드를 다시 여는 김에 정정 — 별도 드라이브바이 아님).

**02가 이제 9대로 읽힌다 — 01과 정확히 같은 리그.** 코디네이터가 직접 검산한 5개 좌표(A/abs1→u1a1, A/abs45→u1a45, A/abs513→u2a1, A/abs642→u2a130, B/abs1→u1a1)를 포함해 미패치(주소 0) 이외의 전 픽스처가 01과 동일한 (system, universe, address)로 수렴함을 회귀 테스트로 확인했다(`test_02_and_01_derive_the_same_universe_address_pairs_per_system`). 02의 리그 전체 근거는 `absolute_back_calculated` + 전제 문구, 01은 `universe_address_direct` + 빈 문구(비공허성 대조군).

**ASSUMPTION-69 판정 재작성**: v0.1.6의 "NEGATIVE(미해소)"는 관측(System 구분 불가)은 맞았지만, 그 결론("그래서 거부한다")이 실제로는 실사용 리그의 94%를 죽이는 구현과 결과적으로 어긋났다 — 코디네이터가 지적한 "판정문과 구현이 일치해야 한다"를 반영해 **GO(선언된 전제 위에서 역산 지원)**로 재작성했다. 관측 자체(System을 별도로 안 붙이면 절대주소만으로 원리적 구분 불가)는 그대로 유지되지만, 결론이 "그래서 System을 근거 축과 별개로 보존해 역산을 지원한다"로 바뀌었다 — 결함 1(P0, v0.1.6)이 도입한 `(system, universe, address)` 아이덴티티 확장이 정확히 그 보존 메커니즘이었다는 것도 이번에 명확히 드러났다.

**M8/ASSUMPTION-70 — 이 라운드가 손대지 않는다(코디네이터 지시).** 제목행 선행형 실물 워크시트 그리드(`path_kind=B`)가 여전히 없다는 기록은 정확하며, 이 라운드는 그 갭을 메우지 않았다. M8은 여전히 BLOCKED, ASSUMPTION-70은 여전히 PARTIAL.

**회귀 테스트**: `test_vwx_address.py::TestAbsoluteAddressConditionalInversion`(2건 재작성 — 거부 대신 근거 등급 역산을 검증, 신규 비공허성 대조군 1건 추가), `TestTripleRepresentationCrossCheck`(1건 재작성 — 절대주소 단독 경로가 이제 resolved임을 확인), `test_vwx_multisystem_real_samples.py`에 신규 클래스 4개(`TestPerSystemAbsoluteAddressAmbiguity` 4건 재작성/확장, `TestAddressBasisPayloadAndSummary` 4건 신설, `TestTripleMismatchStillRejectsDerivation` 1건 신설, `TestScopeQualificationOnMassDrop` 6건 신설) — 스위트 순증 14건. 모든 "0건"/"탈락 없음" 주장에 비공허성 대조군 동반(예: 01 스코프 한정 0건 주장은 합성 대량 탈락 케이스와 대조, 소액 탈락 케이스는 대량 탈락 케이스와 대조).

**SPEC 아티팩트 동기화**: `spec.md` REQ-VWX-009 전면 재정의(전제 게이트 제거, 근거 등급 도입) + REQ-VWX-020 확장(스코프 한정), HISTORY v0.1.7 행 추가, ASSUMPTION-69 판정문 전면 재작성(GO). `acceptance.md` AC-VWX-010 전면 재정의 + AC-VWX-020 확장(⑤~⑦). REQ/AC 개수는 **불변**(28/29 — 전부 기존 항목 내용 확장, 신규 번호 없음).

**재검증 (오케스트레이터 직접 실측)**:
```
uv run pytest server/tests -q → 4898 passed, 7 skipped, 1 warning in 90.39s
```
착수 baseline `4884 passed, 7 skipped` 대비 **+14**, 회귀 0건.
```
uv run ruff check server/vwx server/tests/test_vwx_multisystem_real_samples.py server/tests/test_vwx_address.py server/orchestrator/tools.py → All checks passed!
uv run ruff format --check server/vwx server/tests/test_vwx_multisystem_real_samples.py server/tests/test_vwx_address.py → 9 files already formatted
git diff --stat 2bc95cf..HEAD -- console/lua/ server/safety/ server/prechk/{__init__,inventory,patch,report,footprint,macro,query,verdicts}.py server/paperwork/{data,render,output}.py server/looks/ → (완전 빈 출력, exit=0)
```

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_status: partial-blocked   # M1~M7 completed + verified; M0=PARTIAL (4 real samples, ASSUMPTION-69 now GO); M8 still BLOCKED (ASSUMPTION-70 partial)
run_complete_at: 2026-08-05
head_sha: b2c45ec6f6ad2434a4018fb537b61c5b3e159898   # 02 재설계(결함 1 P0/2 P1) 커밋(v0.1.7, 직접 실측)
base_sha: 2bc95cf309457de5f6fc2b6757b3a8c7aa9f6ec7
milestones_completed: [M1, M2, M3, M4, M5, M6, M7]
milestones_partial: [M0]   # 실물 컬럼 계약 4건 검증 — ASSUMPTION-68/69 해소(69는 v0.1.7에서 GO로 재판정), 70 여전히 PARTIAL
milestones_blocked: [M8]
milestones_blocked_reason: "ASSUMPTION-70(경로 B 진짜 path_kind=B 워크시트 그리드 — 제목행 선행형·헤더 반복형)만 남아 M8을 닫을 수 없다. ASSUMPTION-68/69는 해소됐다(69는 v0.1.6 NEGATIVE에서 v0.1.7 GO로 판정문이 구현에 맞춰 재작성됨) — 사유가 v0.1.4 시점보다 훨씬 좁아졌다."
acceptance_criteria_verified: 24   # AC-VWX-002~025 (M0=AC-VWX-001, M8=AC-VWX-026 제외)
acceptance_criteria_verified_v017: 11   # AC-VWX-010①~⑥(재정의) + AC-VWX-020⑤~⑦(신규) — v0.1.7 확장분, 전부 PASS
acceptance_criteria_blocked: 2     # AC-VWX-001 (M0, PARTIAL로 격상됐으나 완전 GO는 아님) · AC-VWX-026 (M8)
defects_found_and_fixed: 8   # 누적: v0.1.2 P0 2건 + v0.1.5 조인키스코프 1건 + v0.1.6 결함1~4 4건 + v0.1.7 결함1(P0)/2(P1) 2건
defect2_correction_rounds: 3 # v0.1.2~v0.1.3, v0.1.6/v0.1.7 결함2는 각각 별개 재발(집계행/비-DMX 오분류 → 대량 탈락 확신 대조)
m0_partial_round: 3   # v0.1.4(실물 1종) → v0.1.6(실물 4종 누적, ASSUMPTION-68 해소) → v0.1.7(ASSUMPTION-69 GO 재판정, 02 전체 리그 복원)
full_suite: "4898 passed, 7 skipped, 1 warning in 90.39s — this-round entry baseline 4884 passed 7 skipped, delta +14, 0 regressions"
ruff: "All checks passed! (server/vwx/, server/tests/test_vwx_*.py) — ruff format --check also clean"
preserve_gate: "empty diff on all 8 server/prechk/ files + console/lua/** + server/safety/** + server/paperwork/{data,render,output}.py + server/looks/** — reverified after this round's commit"
tool_registration: "unchanged — no new tool sites added this round, existing dispatch-based verification still passes"
architecture_boundary: "server/tests/test_architecture.py — 4 passed — server/vwx/ imports neither server.bridge nor pythonosc"
plan_audit_minor_findings_closed: 4   # 자기모순 2건 + REQ-VWX-025 shall + AC-013② (v0.1.4 이전, 불변)
plan_audit_minor_findings_deferred: 6 # 비차단, 후속 사이클로 이연 (불변)
push_count: 0
pr_count: 0
main_touched: false
known_gaps:
  - "M8은 ASSUMPTION-70(진짜 path_kind=B 워크시트 그리드 — 제목행 선행형 또는 헤더 반복형) 실물 샘플이 최소 1건 더 필요하다. 지금까지 확보한 실물 경로 B 파일은 전부 헤더가 0번 행이라 path_kind=A로 판독된다. 이 라운드(v0.1.7)는 이 갭을 손대지 않았다(코디네이터 지시)."
  - "합성 픽스처 synthetic_path_b_worksheet_grid.csv는 여전히 합성물이다 — path_kind=B 코드 경로가 실행됨은 증명하지만 실물 워크시트의 마커·서식을 대변하지 않는다(ASSUMPTION-70을 이걸로 GO 판정하면 안 됨)."
  - "M6 설계가 계획 대비 변경됐다 — server/prechk/verdicts.py를 건드리지 않고 server/vwx/report.py에 독립 어휘 레지스트리를 신설했다(spec.md §C·acceptance.md AC-VWX-023 갱신 완료, v0.1.6에서 skipped_check_kind 1건 추가 등록)."
  - "research.md §3의 focus/frame_size/wattage/weight 언급과 ALIAS_TABLE(구현) 사이 문서-구현 드리프트를 발견해 research.md에 '정본은 구현' 한 줄로 정리했다 — 이 4개는 여전히 정규 필드가 아니다(extra 보존, 범위 밖 결정)."
  - "address_basis 근거 등급은 v0.1.7 신설이라 M0 실물 샘플(vectorworks_export_sample_with_data.csv, 직접값만 존재)에서는 한 번도 absolute_confirmed 등급(외부 확인 절차로 격상)을 실측하지 못했다 — 그 등급은 단위 테스트로만 비공허성 확보됨."
next: "진짜 path_kind=B(제목행 선행형) 워크시트 그리드 실물 샘플을 추가로 확보해 ASSUMPTION-70을 닫아야 M8 종단 검증을 시작할 수 있다. 그 전까지는 sync-phase로 진행하지 않는다(M8 BLOCKED가 SPEC 완결을 막는다)."
```

### 카운트 드리프트 정리 (2026-08-05) — 살아있는 기준 vs 날짜 있는 기록 전수 스캔

REQ가 25→28, AC가 26→29로 늘어난 뒤(v0.1.4), `acceptance.md` §F Definition of Done이 옛 숫자
("AC-VWX-001~026 26건 전량 PASS", "REQ-VWX-001~025 25건 전량 커버")를 그대로 들고 있어 신규
REQ-VWX-026~028·AC-VWX-027~029가 검증되지 않은 채로도 DoD를 통과할 수 있는 실질 결함이었다 —
같은 문서 3행의 status 줄은 이미 "AC 29건 계획"으로 갱신돼 있어 **문서 내부 자기모순**이었다
(코디네이터가 검증 중 발견). `acceptance.md` §F를 28 REQ/29 AC 기준으로 갱신했고, ASSUMPTION
68~70 판정 확정 항목은 "M8이 실제로 닫혀야 참이 되는 조건"임을 명시해 지금은 미충족임을 분명히
했다. `spec.md`·`plan.md`·`design.md`·`research.md`·`acceptance.md`·`progress.md` 6종 전수를
`25건`/`26건`/`REQ 25`/`AC 26`/`25/25`/`26/26` 패턴으로 훑은 결과, 나머지 매치는 전부 **날짜가
붙은 기록**이었다 — `spec.md`/`plan.md`/`acceptance.md`의 `v0.1.0 — 최초 작성` HISTORY·블록쿼트
행, `progress.md`의 "Plan-phase log v0.1.0" 아티팩트 요약 표, `§E.1` yaml의 `requirements:`/
`acceptance_criteria:` 필드(FXLIB-001·SCENE-001 선례를 따라 `plan_amended_at:` 개정 줄 + 별도
amendment 서술 블록을 추가하고 원 필드는 보존), `§E.1a`의 1회차 감사 결과 서술(그 감사가 실제로
v0.1.0 시점의 25/26을 대상으로 수행됐다는 사실 자체를 담고 있으므로 보존)이 그것이다 — 이들은
"현재 값"을 주장하지 않고 "그 시점에 무엇이었는가"를 기록하므로 손대지 않았다. `progress.md` §0
(상태 줄·읽는 순서 표·기계 확인 커맨드)만 다음 담당자가 실제로 참고할 **살아있는 안내**이므로
현재 값(28/29)을 병기하도록 갱신했고, 기계 확인 커맨드 블록은 v0.1.0 시점 기록과 현재 재실행 시
기대값 블록으로 분리했다.

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
