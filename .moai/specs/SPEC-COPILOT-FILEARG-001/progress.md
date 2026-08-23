# SPEC-COPILOT-FILEARG-001 — 진행 기록 (progress)

문서 상태: draft (v0.1.0, 2026-08-22 · plan-phase) · Tier M · 칸반 카드 t10

---

## §0 인수인계 — 여기서 시작한다 (2026-08-22)

### 한 문단

운영자가 앱의 첨부 버튼으로 고른 LX-SEQ 패치 CSV의 바이트가 `import_lxseq_patch`의 `file_content_base64` 인자까지 도달하게 만드는 카드다. 오늘 그 길은 없고, 이미지가 아닌 파일은 전부 Vectorworks 경로로 조용히 흘러간다. 만드는 것은 넷이다 — **헤더 서명 판별기**(어느 서명과도 안 맞으면 거절, 둘에 맞아도 거절) · **`종류 → 대상 툴` 레지스트리**(오늘 행 하나) · **세션 슬롯 하나**(담기만 하고 실행하지 않는다) · **바이트를 만지지 않는 래퍼 툴**. 후속 카드 002/003/004는 표에 행 하나씩만 더한다.

### 읽는 순서

1. `spec.md` §A(사전 확정 사실 7건) → §F(세 성질) → §G(레지스트리 부록)
2. `plan.md` §A.1(뒤집힐 수 있는 결정) → **§A.4 ①(열린 결정 — Kickoff 전에 닫아야 한다)** → §B(마일스톤)
3. `acceptance.md` §C(AC 17건과 검증 명령)
4. `research.md` §7(갭)

### 인수인계 시 반드시 알아야 할 함정 4건

1. **툴 등재는 4지점이 아니라 6지점이다.** `_TOOL_TASKS`(`server/orchestrator/runner.py:137`)와 `test_tools.py`의 닫힌 집합 상수를 빠뜨리면 `test_runner_progress.py`의 전단사 단언이 빨갛게 된다.
2. **판별기가 첫 일치에서 멈춰도 오늘은 테스트가 통과한다** — 등록 행이 둘뿐이고 둘은 서로 겹치지 않기 때문이다. 그래서 충돌 시험은 **주입한 표**로 돌린다(`AC-FILEARG-003`). 충돌은 이론이 아니다 — 프리셋 4종에서 반드시 발화한다(`research.md` §9 (c)).
3. **서명을 사본으로 적으면 언젠가 실물을 거절한다.** `CANONICAL_COLUMNS`를 참조하고 열 이름을 옮겨 적지 않는다.
4. **이 저장소에는 테스트 CI가 없다.** `.github/workflows/`는 라벨 동기화 하나뿐이라 로컬 전체 스위트(pytest + vitest)가 유일한 회귀 증거다. 그리고 **착수 시점에 이미 실패 1건이 있다**(`test_pipeline_out_paths.py` / t20 귀속) — 이 SPEC 것이 아니고 여기서 고치지 않는다(§E.1 `known_baseline_failure`).

### 다음 담당자가 먼저 결정할 것

열린 결정은 **없다**(2026-08-22 리드 재정으로 결정 I·J 확정 — `plan.md` §A.3, 답은 아래 "M0 — Kickoff 결정 기록"). 다음 담당자가 기다리는 것은 결정이 아니라 **운영자의 Implementation Kickoff Approval**이다 — M1은 `cycle_type=tdd` 구현이므로 승인 전에는 M0도 시작하지 않는다. 승인 뒤 M1이 실측할 두 가지: ① Vectorworks 서명이 vwx fixture 7종의 변형을 견디는가(못 견디면 안전판 REQ-FILEARG-018) ② 확장 형식이 프리셋 4종을 실제로 가르는가(AC-FILEARG-018).

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 5종 작성 (2026-08-22)

- 워크트리 `.claude/worktrees/t10`, 브랜치 `WT-file-picker-args`, HEAD `eb436e8`(= `origin/main`)에서 작성.
- SPEC ID 자기 점검을 Bash로 실행해 `PASS`를 관측했다(`^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$`). `.moai/specs/`에 동명 디렉터리가 없음을 확인했다.
- 리드가 확정해 넘긴 좌표 8건은 재측정하지 않고 그대로 인용했다(`research.md`가 `[리드]` 등급으로 표시). 본 세션이 **직접 관측한 것**은 다음이며 `[코드]` 등급으로 표시했다: `TOOL_NAMES` 34종과 위치(`tools.py:232`) · `import_lxseq_patch`의 핸들러/정의/맵 위치(`:4418`·`:9226`·`:9327`) · `_TOOL_TASKS`(`runner.py:137`)와 전단사 단언(`test_runner_progress.py:303`·`:307`) · 닫힌 집합 상수 34(`test_tools.py:172`) · `CANONICAL_COLUMNS`/`_normalize_header`/`_resolve_header_map`(`parser.py:18`·`:118`·`:122-135`) · 프레임 허용 목록·검증기·분기(`messages.py:81-83`·`:194`·`:227`, `app.py:494`·`:505`) · `<input accept>`와 라우터 주석(`App.tsx:824`·`:625-635`) · Vectorworks CSV 실물 표본 언급(`server/vwx/columns.py:21`).
- 코드 변경 0건. `ui/`·`server/`·`src/` 아래 파일은 하나도 건드리지 않았다.

### M0 — Kickoff 결정 기록 (`AC-FILEARG-001` ⑥의 기록처)

| 항목 | 답 |
|---|---|
| **결정 I** — 서명 미일치 CSV의 처분 | **(나)안 채택** (2026-08-22 리드 재정). Vectorworks export CSV를 레지스트리 행으로 등록하고, 일치 0건이면 거절한다. (가) 폴백 보존은 [HARD] 거절 규칙에 살아 있는 경로를 남기지 않고, (다) 순수 거절은 폐기 지시 없이 살아 있는 기능을 회수하므로 둘 다 기각 |
| **결정 J** — 무엇을 넓히는가 | **서명 형식의 표현력을 넓히고 레지스트리 행은 넓히지 않는다** (2026-08-22 리드 재정). 형식은 정확 열 집합과 포함·배제 쌍을 표현해야 하며(REQ-016), 프리셋·group·fx·cue-ex의 서명은 쓰지 않는다(REQ-017). 형식 충분성은 합성 서명 픽스처로 증명한다(AC-018) |
| 리드 결정 ③ "행 하나" 문면 | **정정됨** — 행의 개수가 아니라 **파서·핸들러 없는 종류를 만들지 말라**는 뜻. 결정 D에 반영 |
| `ASSUMPTION-75` | **닫힘** — 리드 실측(`research.md` §9 (a)(b)). 표본 실재 · LX-SEQ와 VW 헤더 비충돌(9열 중 일치 3) |
| Implementation Kickoff Approval | **미통과** — M0·M1 포함 착수는 운영자 승인 뒤. 리드의 "지금 M1 착수" 지시는 철회됨 |

> **run 세션에게**: 위 표에 결정 I·J의 답이 있으므로 `AC-FILEARG-001` ⑥의 답 요건은 충족됐다. 남은 것은 **Implementation Kickoff Approval**이며, 그 전에는 M0도 시작하지 않는다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-pending   # plan-audit 미실시 · Implementation Kickoff Approval 미통과(M0 착수 전제)
plan_complete_at: 2026-08-22
plan_audit: "미실시"
spec_version: "0.2.0"
tier: M
base_sha: 6296af3
baseline_measured: "미측정 — 의도적으로 비워 둔 칸이다(미완성이 아니다). plan 세션은 전체 스위트를 실행하지 않았고, 이 트리를 두고 돌던 수치 중 최소 하나는 틀렸다(0 failed 로 전달됐으나 실제로는 실패 1건). 다른 트리·다른 시점의 값을 이월하지 않는다 — M0가 이 워크트리 6296af3에서 직접 잰다."
artifacts: [spec.md, plan.md, acceptance.md, research.md, progress.md]
requirements: 18            # REQ-FILEARG-001~018 (016~018은 리드 재정으로 신설)
acceptance_criteria: 21     # AC-FILEARG-001~021 (앱 실기 1: AC-017 · 조건부 1: AC-021)
milestones: 6               # M0~M5 (M0·M5 cycle_type=none)
assumptions_open: 2         # ASSUMPTION-76~77 (75는 리드 실측으로 닫힘)
decisions_closed: 10        # plan.md §A.3 A~J (I·J = 2026-08-22 리드 재정)
clarifications_open: 0      # 결정 I로 닫힘 — 답은 "M0 — Kickoff 결정 기록"
live_sessions_planned: 1    # M5, 사용자 수행(앱 실기)
new_runtime_dependencies: 0
new_data_files: 0
known_baseline_failure: "server/tests/test_overlap_preserve.py::TestTouchedFilesPassLint::test_ruff_format_reports_no_change — 착수 시점 기존 실패 1건. 원인은 t20(6296af3)이 server/tests/test_pipeline_out_paths.py를 ruff format 없이 들여온 것. 이 SPEC 범위 밖이며 여기서 고치지 않는다(다른 레인이 별도 카드로 처리 중). M0가 실행 시점에 이미 고쳐져 있으면 그 상태를 관측한 대로 적는다."
base_advance: "eb436e8 → 6296af3 (3커밋: e7a8e90 t17 · 6296af3 t20). 문서의 코드 줄번호는 한 세대 낡았다 — M0가 토큰 앵커로 재확인한다."
tool_count_delta: "34 → 35 (래퍼 툴 1종)"
```

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F.1 Phase 4 Mode Selection

- **tier**: M · **scope**: 약 15파일(신규 6 · 추가 5 · 수정 4) · **domain**: 2(Python 백엔드 · TypeScript UI) · **parallel benefit**: LOW.
- 평가: `direct` 미선택(신규 모듈 + 프레임 + 툴 배선, 사소하지 않다) · `fanout` 미선택(조사형이 아니고, 도메인이 둘이지만 UI는 서버 프레임이 확정된 뒤에야 배선된다) · `sweep` 미선택(기계적 일률 변환이 아니다) · **`serial` 선택**.
- **Decision: serial**
- **Justification**: M1(판별기·레지스트리) → M2(슬롯·프레임) → M3(래퍼 툴) → M4(UI 배선)가 앞 산출물을 순차로 소비하는 사슬이며 코딩 중심 작업이다. `plan.md` §F의 사전 권고와 일치한다.

_M1 이하 — manager-develop 소유, 착수 예정_
