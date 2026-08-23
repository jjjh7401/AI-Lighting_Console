# SPEC-COPILOT-FILEARG-001 — 진행 기록 (progress)

문서 상태: draft (v0.1.0, 2026-08-22 · plan-phase) · Tier M · 칸반 카드 t10

---

## §0 인수인계 — 여기서 시작한다 (2026-08-22)


**분할 A(판별기)** — "이것은 무엇인가"에만 답한다. 업로드된 바이트를 받아 **술어 레지스트리**로 종류를 판정하고, 0건이면 `unknown_sheet_kind` · 2건 이상이면 `ambiguous_sheet_kind`로 거절한다. 술어는 둘이다 — `patch`는 **열 집합 서명**(정규 9열 포함 검사), `vectorworks`는 **신원 술어**(zip이면 `SCENE_ENTRY`, 아니면 `_best_header_candidate >= 0`) **AND NOT** 다른 행 서명 일치. **사용성**("패치를 뽑을 수 있는가")은 판별에 쓰지 않는다 — 대상 툴이 판단한다. 그 바이트를 실제로 **나르는 일**(세션 슬롯 · 래퍼 툴 인자 · UI 배선)은 `SPEC-COPILOT-SHEETPIPE-001`이 **A 통과 뒤** 맡는다. 후속 카드 002/003/004는 레지스트리에 행 하나씩만 더한다.

### 읽는 순서

1. `spec.md` §A.4(분할 — 무엇이 어디로 갔나) → **§A.5(A가 Tier L인 이유)** → **§G.1(축이 다르다 — 감사 FAIL의 뿌리)** → §G.4(위임 계약 두 갈래) → §F(세 성질)
2. `plan.md` §A.1(뒤집힐 수 있는 결정) → §A.3 **결정 K · L** → §A.4(열린 결정 **0건**)
3. `acceptance.md` §C(AC **20건**과 검증 명령 · 표 밖 4건의 이유)
4. `research.md` **§11**(F2 뿌리 · 신원 열 재계산) → §10 → §9 → §7(갭)


### 인수인계 시 반드시 알아야 할 함정 10건

1. **툴 등재는 4지점이 아니라 6지점이다.** `_TOOL_TASKS`(`server/orchestrator/runner.py:137`)와 `test_tools.py`의 닫힌 집합 상수를 빠뜨리면 `test_runner_progress.py`의 전단사 단언이 빨갛게 된다. 정본 열거는 `research.md` §6이며, `test_runner_progress`는 **지점이 아니라 누락 검출 가드**다.
2. **판별기가 첫 일치에서 멈춰도 오늘은 테스트가 통과한다** — 등록 행이 둘뿐이고 둘은 서로 겹치지 않기 때문이다. 그래서 충돌 시험은 **주입한 표**로 돌린다(`AC-FILEARG-003`). 충돌은 이론이 아니다 — 프리셋 4종에서 반드시 발화한다(`research.md` §9 (c)).
3. **서명을 사본으로 적으면 언젠가 실물을 거절한다.** `patch`는 `CANONICAL_COLUMNS`를 참조하고, `vectorworks`는 `reader.py`의 판정을 **호출**한다. 열 이름도 판정 논리도 옮겨 적지 않는다.
4. **이 저장소에는 테스트 CI가 없다.** `.github/workflows/`는 라벨 동기화 하나뿐이라 로컬 전체 스위트(pytest + vitest)가 유일한 회귀 증거다. 그리고 **착수 시점에 이미 실패 1건이 있다**(`test_pipeline_out_paths.py` / t20 귀속) — 이 SPEC 것이 아니고 여기서 고치지 않는다(§E.1 `known_baseline_failure`).
5. **열 집합으로 Vectorworks를 재려 하지 마라 — 1차 감사 FAIL의 뿌리였다.** `.mvr`·`.xlsx`는 zip이라 헤더 행이 없고(`reader.py:350-360`), 헤더는 1행이라는 보장도 없다(`reader.py:158`이 **탐색**한다). 행이 드는 것은 열 목록이 아니라 **술어**다(결정 K · `spec.md` §G.1).
6. **그리고 술어는 "무엇인가"를 물어야 한다 — 2차(델타) 감사 FAIL의 뿌리였다.** `has_address_family`는 **"패치를 뽑을 수 있는가"**를 묻는다. 축이 다르므로 **양방향으로 틀린다**: LX-SEQ 패치 CSV가 `True`(9열 중 **7열이 VW 별칭**으로 해소 — LX-SEQ는 VW 어휘의 **부분집합**이다)이고, 주소 열 없는 진짜 VW 파일은 `False`다. 사용성 함수를 판별에 끌어들이는 순간 같은 결함이 재발한다(결정 L · REQ-FILEARG-022 · `research.md` §11.1). 그리고 **대조군을 한 축으로만 세우지 마라** — 쉼표 전용 대조군이 전부 초록인 동안 탭 축이 열려 있었고, 장바구니 목록이 실패 0건으로 Vectorworks가 됐다(`AC-FILEARG-028`).
7. **경계 게이트는 커밋 뒤에 돌린다 — 커밋 전 초록은 거짓이다.** `server/tests/test_overlap_preserve.py`는 고정 base와 **`HEAD`**를 diff하므로(`:427` · `:446` · `:456`) **작업 트리의 미커밋 변경은 그 진단의 시야 밖**이다. 커밋 전에 재서 초록이 나오는 것은 운이 아니라 **구조적으로 보장된 결과**다 — 오늘 이 보드에서 두 번 나왔고(t20 · t31), t31에서는 동결 문서의 실제 위반을 **커밋 뒤에야** 잡았다(미커밋 상태에서는 `41 passed`). 순서는 **커밋 → 게이트 → 보고**이며, "미리 돌려 두면 빠르다"로 되돌리는 것은 **검사를 없애는 것과 같다**(`AC-FILEARG-030`).
8. **수를 셀 때는 정의 앵커 grep을 쓴다.** 이 SPEC은 `006` · `009~015`를 **비운 자리로 문서화**하므로 맨 ID 패턴 grep은 참조까지 세어 과대 보고한다. `grep -c "^- \*\*REQ-FILEARG-" spec.md` → **16**, `grep -c "^### AC-FILEARG-" acceptance.md` → **20**(`acceptance.md` §D 계수 규약). 오늘 이 보드에서 같은 혼동이 네 번 나왔다.
9. **부정 grep 결과를 "없앴다"의 증거로 쓰지 마라 — 인라인 강조가 문자열을 쪼갠다.** `정본을 **참조**한다`는 `정본을 참조`로 검색해도 걸리지 않는다. `columns.py` 오귀속이 **세 번째로** 살아남은 경로가 정확히 이것이었다(감사 A2) — grep이 비었길래 "고쳤다"고 적었는데 강조 마크업 때문에 매치가 빗나간 것이었다. 문구 확인은 **강조를 걷어낸 짧은 토큰**(`columns.py` 같은)으로 훑고 히트를 눈으로 판독한다(`acceptance.md` §D 계수 규약).
10. **Tier 아티팩트는 세는 것이 아니라 집합을 맞추는 것이다.** Tier L 집합은 `spec + plan + acceptance + design + research`이며 **`progress.md`는 그 집합에 없다**. 파일이 다섯 개라는 것과 집합이 채워졌다는 것은 다른 문장이고, v0.6.0까지 그 둘을 혼동해 `design.md` 없이 Tier L을 주장했다(감사 A1). 이것은 `AC-FILEARG-030`의 "가드가 초록이다 ≠ 그 가드가 이 트리를 본다"와 같은 종류의 구분이다.

### 다음 담당자가 먼저 결정할 것

열린 결정은 **없다**(I·J = 리드 재정 · **K·L** = 감사 FAIL 시정 · **분할** = 2차 델타 감사 시정 — `plan.md` §A.3, 답은 아래 "M0 — Kickoff 결정 기록"). 다음 담당자가 기다리는 것은 결정이 아니라 **운영자의 Implementation Kickoff Approval**이다 — M1은 `cycle_type=tdd` 구현이므로 승인 전에는 M0도 시작하지 않는다. 승인 뒤 M1이 실측할 것: ① **`ASSUMPTION-75-b`** — LX-SEQ 패치 헤더가 `vectorworks` 신원 술어를 만족하지 **않는가**(F2가 통과한 바로 그 미측정 방향 · `AC-FILEARG-025`) ② 신원 술어가 `server/tests/fixtures/vwx/` 페이로드 10개를 흡수하는가(못 하면 안전판 REQ-FILEARG-018) ③ 확장 형식이 프리셋 4종을 가르는가(`AC-FILEARG-018`). **B(`SPEC-COPILOT-SHEETPIPE-001`)는 A가 통과할 때까지 착수하지 않는다.**

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
| **결정 K** — 레지스트리 행이 드는 것 | **판별 술어**다 (2026-08-23, 독립 감사 FAIL 시정). `patch`=열 집합 술어 · `vectorworks`=기존 판독기 위임(`server/vwx/reader.py`). 열 집합 서명으로는 zip(`.mvr`·`.xlsx`)도 탐색된 헤더도 표현할 수 없어, 그대로 두면 살아 있는 업로드를 회수한다. 치른 값: 표가 순수 데이터가 아니게 된다(spec.md §G.1) |
| **결정 L** — 술어가 무엇을 묻는가 | **신원**이다 (2026-08-23, 델타 재감사 FAIL 0.62 시정). `vectorworks` = `_best_header_candidate >= 0` **AND NOT** 다른 행 서명 일치; 사용성(`has_address_family`·`not_patch_source`)은 판별에서 뺀다. 결정 K가 위임한 함수는 **다른 물음**(패치 가능성)에 답하므로 **양방향으로 틀렸다** — LX-SEQ는 VW 어휘의 **부분집합**이라 주소 계열 검사로는 영원히 갈 수 없다 |
| **분할 (v0.5.0)** | 합본이 Tier M 예산(REQ 16 / AC 16)을 넘어 **둘로 나눴다** — 본 SPEC = **A(판별기)** REQ 15 · AC 19 · Tier **L** · 임계 **0.85**; **B(전달경로)** = `SPEC-COPILOT-SHEETPIPE-001` REQ 8 · AC 11 · Tier M · **A 통과 뒤 착수**. 감사 차단 결함은 전부 A에 있었고 B는 지적 0건이다 |
| **A가 Tier L인 근거** | **성격이다, 크기가 아니다.** A는 `REQ-FILEARG-017`이 LXSEQ-002/003/004에게 행 추가를 예약한 **레지스트리 계약을 정의**하므로 constitutional이다. **AC가 10건이어도 Tier L이다** — 예산에 맞춰 티어를 고른 것이 아니다(`spec.md` §A.5) |
| **`AC-FILEARG-009` 분할** | 두 요구를 동시에 섬기던 기준을 쪼갰다 — **A는 순서 단언**(판별이 파싱하지 않는다; ID 유지), **B는 표시 단언**(업로드 직후 네 필드; B 자기 번호) |
| **D1 — 위임 계약** | **두 갈래 전역 함수**로 확정. zip이면 `SCENE_ENTRY`(`tools.py:2861`), 아니면 `_best_header_candidate >= 0`. 판독기 결과 **넷**에 값 배정(미발견 F · 예외 F · `not_patch_source` T · **`unapproved_dependency` T** — 넷째는 v0.4.0에 없던 경우이며 오늘 `.mvr`이 실제로 내는 결과다) |
| **D5 — 좌표 정정** | `tools.py:2859-2860` → **`2860-2861`**, 결정 줄은 **2861**. 문서 7곳 전부 교정(spec 3 · research 2 · acceptance 1 · progress 1). `AC-FILEARG-022` ④가 이 좌표를 인수 근거로 써서, 그대로면 통과 불가였다 |
| **D3 — 세 번째 오귀속** | `plan.md` §E가 VW 서명 소유자를 `columns.py`로 되살려 두었다 — 결정 K가 오귀속으로 판정하고 L이 `reader.py`로 옮긴 그 문장이다. **같은 SPEC이 한 문서에서 고치고 다른 문서에서 되살린** 자리이며 하필 다음 카드가 먼저 읽는 절이었다. 교정 완료 |
| **D4 — AC-027 주장 축소** | "임계 2 고정"은 사실이 아니다. T=1로 낮추면 뒤집히는 것은 무관 대조군이 아니라 **진짜 VW 파일**(점수 1)이고, **T=3은 코퍼스 전체가 초록**이다(2~4점 입력 없음). **하한만** 고정된다고 다시 적었다 |
| 결정 K의 위임 대상 | **정정됨** — "판독기에 위임"이 아니라 **`_best_header_candidate`(`reader.py:158`) 호출**이다. `.mvr` 판정은 `reader.py`에 **없다**(`grep -c "mvr\|MVR"` → 0) — `tools.py:2860-2861` + `mvr.py`가 소유(F1) |
| `ASSUMPTION-75` | **재개방** — v0.2.0이 **한 방향만**(VW 헤더 → patch 서명) 재고 닫은 것이 F2를 통과시켰다. 이제 **75-a**(VW 헤더 ↛ patch 서명, 참) · **75-b**(LX-SEQ 헤더 ↛ vectorworks 술어, **M1 실측 필요**)를 각각 단언한다 — `AC-FILEARG-025` |
| 헤더 없는 `.txt`의 처분 | **`unknown_sheet_kind`가 정답이다** — 그 파일은 오늘 패치를 만들지 못한다(`fixtures/vwx/README.md:85-95`). 잃는 것은 능력이 아니라 문구 하나이며, **조건부** 재수출 힌트로 보존한다(REQ-023 · AC-029) |
| 결정 J의 적용 범위 | **열 집합 술어에 한정** — 결정 K 이후 위임 술어는 열을 세지 않으므로 형식 확장의 대상이 아니다 |
| VW 서명 정본 좌표 | **정정됨** — `server/vwx/columns.py`(v0.2.0 오귀속) → 호출 지점 **`server/vwx/reader.py:286`**(`has_address_family(탐색된 헤더)`) |
| `ASSUMPTION-77` | **닫힘 · POSITIVE** — 실물 패치 CSV **7,258 B**(≈7 KB), 8 MiB는 약 1,150배. "수십 KB"는 한 자릿수 오차였다 |
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
spec_version: "0.7.0"
tier: L                     # 분할 A는 constitutional (레지스트리 계약 정의) — 크기가 아니라 성격. 통과 임계 0.85
base_sha: 6296af3
baseline_measured: "미측정 — 의도적으로 비워 둔 칸이다(미완성이 아니다). plan 세션은 전체 스위트를 실행하지 않았고, 이 트리를 두고 돌던 수치 중 최소 하나는 틀렸다(0 failed 로 전달됐으나 실제로는 실패 1건). 다른 트리·다른 시점의 값을 이월하지 않는다 — M0가 이 워크트리 6296af3에서 직접 잰다."
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md]   # Tier L 집합 5종. progress.md는 Tier 집합에 없는 별도 파일이다 — v0.6.0까지 이 칸이 progress.md를 세고 design.md를 빠뜨렸다(감사 A1)
requirements: 16            # 정의 앵커: grep -c "^- \*\*REQ-FILEARG-" spec.md → 16 (001~005 · 007 · 008 · 016~024; 006 · 009~015는 SHEETPIPE로 이동 — 번호 재사용 금지)
acceptance_criteria: 20     # 정의 앵커: grep -c "^### AC-FILEARG-" acceptance.md → 20 (001~006 · 009(순서 구간) · 018~030; 조건부 1: AC-021 · 앱 실기 0 — B가 소유)
milestones: 2               # M0(게이트, cycle_type=none) · M1(판별기·레지스트리, tdd). M2~M5는 SHEETPIPE로 이동
assumptions_open: 2         # ASSUMPTION-75(재개방 — 75-b 미검증) · 76. 77은 7,258 B 실측으로 POSITIVE 닫힘
decisions_closed: 12        # plan.md §A.3 A~L (I·J = 리드 재정 · K = 감사 FAIL 시정 · L = 델타 감사 FAIL 시정)
clarifications_open: 0      # 결정 I로 닫힘 — 답은 "M0 — Kickoff 결정 기록"
live_sessions_planned: 0    # A는 콘솔도 앱도 건드리지 않는다 — 실기 확인은 B(SHEETPIPE)가 소유
new_runtime_dependencies: 0
new_data_files: 0
known_baseline_failure: "server/tests/test_overlap_preserve.py::TestTouchedFilesPassLint::test_ruff_format_reports_no_change — 착수 시점 기존 실패 1건. 원인은 t20(6296af3)이 server/tests/test_pipeline_out_paths.py를 ruff format 없이 들여온 것. 이 SPEC 범위 밖이며 여기서 고치지 않는다(다른 레인이 별도 카드로 처리 중). M0가 실행 시점에 이미 고쳐져 있으면 그 상태를 관측한 대로 적는다."
base_advance: "eb436e8 → 6296af3 (3커밋: e7a8e90 t17 · 6296af3 t20). 문서의 코드 줄번호는 한 세대 낡았다 — M0가 토큰 앵커로 재확인한다."
tool_count_delta: "0 (A는 툴을 등재하지 않는다 — 34 → 35 래퍼 툴 등재는 SHEETPIPE 몫)"
```

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F.1 Phase 4 Mode Selection

- **tier**: **L**(constitutional — 레지스트리 계약 정의; 크기가 아니라 성격, `spec.md` §A.5) · **통과 임계 0.85** · **scope**: 3파일(신규 `server/sheets/__init__.py` · `server/sheets/registry.py` · `server/tests/test_sheets_registry.py`) · **domain**: 1(Python 백엔드 — UI 0) · **parallel benefit**: LOW.
- 평가: `direct` 미선택(신규 모듈 + 술어 설계, 사소하지 않다) · `fanout` 미선택(도메인 1, 조사형 아님) · `sweep` 미선택(기계적 일률 변환 아님) · **`serial` 선택**.
- **Decision: serial**
- **Justification**: 분할 후 A는 M0(게이트) → M1(판별기·레지스트리) 둘뿐이고 한 도메인·한 모듈이다. 마일스톤이 둘이므로 병렬화할 사슬 자체가 없다. 분할 전 근거(M1→M2→M3→M4 데이터 사슬)는 **B로 이관**됐다 — 세션 슬롯·래퍼 툴·UI 배선은 `SPEC-COPILOT-SHEETPIPE-001`이 자기 모드 선택을 기록한다.

_M1 — manager-develop 소유, Implementation Kickoff Approval 통과 후 착수 예정_
