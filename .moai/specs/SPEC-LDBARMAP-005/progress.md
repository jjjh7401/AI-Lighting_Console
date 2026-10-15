# SPEC-LDBARMAP-005 — Progress

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-15
- 작성 카드: t656. 워크트리 `.claude/worktrees/t656`, 브랜치 `WT-barmap-meter`, 작성 base `bef3e16d9da14a398f7c07a8f48bdff94097a636`. 입력과 읽은 줄은 spec.md §4와 research.md에 있다.
- Tier: L (spec.md §0 근거) — REQ 21개, AC 22개. 두 상한(각 25개) 안이다 [measured: `grep -c "^| REQ-LDBARMETER-" spec.md` → 21, `grep -c "^### AC-LDBARMETER-" acceptance.md` → 22 @ 이 plan-phase 산출물].
- 산출물 6개: spec.md, plan.md, acceptance.md, design.md, research.md, progress.md. **커밋·스테이징은 하지 않았다** — 커밋은 오케스트레이터가 한다.
- 자체 점검(plan-audit 전):
  - SPEC ID 정규식: `ID="SPEC-LDBARMAP-005"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS` [measured: research.md 부록 A-13].
  - ID·접두사 유일성: `LDBARMETER`가 HEAD, `origin/main`, 전체 이력에서 0건. `SPEC-LDBARMAP-005`도 이력에서 0건. 형제 워크트리에는 SPEC-LDBARMAP-001·002·003·004만 있다 [measured: research.md 부록 A-13].
  - `depends_on: [SPEC-LDBARMAP-001, SPEC-LDBARMAP-002]` — 둘 다 `status: completed`라 충족. `related_specs`의 SPEC-LDARRANGE-001(`draft`)·SPEC-LDBEAT-001(`completed`)은 존재한다 [measured: research.md 부록 A-14]. `amendment_of`는 쓰지 않았다.
  - 프런트매터: 12필드(`id`, `title`, `version`, `status`, `created`, `updated`, `author`, `priority`, `phase`, `module`, `lifecycle`, `tags`)와 선택 필드 `tier`, `related_specs`, `depends_on`. `phase`는 `"Lighting Copilot v1.2 target"` — SPEC-001·002·LDBEAT-001·LDARRANGE-001이 같은 값을 쓰는 릴리스 목표 라벨이고 생애주기 단계 이름이 아니다.
  - `moai spec lint .moai/specs/SPEC-LDBARMAP-005/spec.md` → `✓ No findings — all SPEC documents are valid`, `--strict`도 같은 결과, `--json`은 `[]` [measured: moai-adk 3.1.2, 2026-10-15]. 린터가 공허하지 않음은 확인했다 — 제외 범위 제목의 「Out of Scope」를 바꾼 사본에서 `MissingExclusions` 경고가 나왔다(사본은 지웠다).
  - 추적성(AC-LDBARMETER-022의 명령, AC 제목 줄만 센다): REQ 21개 모두 1 이상 [measured: 위 명령 @ 산출물].
  - 동결 파일: `git diff --name-only bef3e16d… HEAD -- .moai/specs/SPEC-LDBARMAP-001 .moai/specs/SPEC-LDBARMAP-002 | wc -l` → 0, `git status --short -- …` 같은 두 디렉터리 → 0 [measured: research.md 부록 A-17b]. 이 plan-phase는 두 디렉터리의 어떤 파일도 쓰지 않았다.
  - 시험·코드 실행 0회, 콘솔 접촉 0건, `server/` 아래 수정 0건.
- 감독·리드에게 올라가는 항목(답이 없다): **OD-3**(표지 저장 자리 — 기본안은 저장하지 않음), **OD-4**(오프셋이 판별한 분자 이상일 때), OQ-1~OQ-12(spec.md §6.4). 사전 등록 문턱 PR-01~18은 설계자의 제안이다(OQ-9).
- 알려진 미검증: spec.md §7(Gaps 13개). 요점 — 판별 알고리즘은 한 번도 실행되지 않았다, 라벨된 3/4·6/8 실제 곡이 없다, 「11곡」을 찾지 못했다(기록은 10곡), 기록된 10곡의 박자표를 사람이 확인한 기록이 없다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §G Plan-audit 이력 (orchestrator 기록, 카드 t656)

- 1회차 — 기준 커밋 `016ec56e`: plan-auditor(sonnet) **FAIL, 0.82** (통과선 0.85, Tier L). 차원별: Clarity 0.80 · Completeness 0.75 · Testability 0.80 · Traceability 0.95 (조화평균). 필수 점검 MP1–MP9는 전부 통과. 보고서: `.moai/reports/plan-audit/SPEC-LDBARMAP-005-review-1.md` (로컬 산출물, gitignored).
- 블로킹 5건: (1) AC-010 grep이 `bar_map.py:618·620`의 주파수 대역(300~3,400Hz)을 잡는다. (2) 동결 시점이 설계, spec, AC-007에서 서로 다르다. (3) OD-4의 각 선택지가 REQ-001·008·011과 충돌한다. (4) SPEC-004와의 겹침이 파일 단위에만 적혀 있다. (5) SPEC-004 인용이 `f46f6dc7` 시점 내용을 현재인 것처럼 적고 있다(라이브 워크트리는 v0.1.3).
- 비블로킹 9건(REQ 복합 조항 분리, AC 정밀화, 줄 번호 정정, 태그 누락 등)은 2회차에서 함께 고친다.
- 리드 조율 결정(2026-10-15): (a) 직렬 실행. 004를 먼저 머지하고 005는 그 뒤 main을 merge 받아 착수하며, 동시 run은 하지 않는다. (b) 타임라인 최상위 새 키 없음. (c) OD-3 닫음. 「박자 추정」 표지는 마디 지도 데이터 안의 필드 하나이며, 착수 승인 때 감독이 확인한다. (d) 의존성 한 줄을 적고, 004 REQ-LDBARLEN-002의 여섯-키 고정을 그 표지 키 하나에 한해 대체한다고 선언한다. 004 문서는 건드리지 않는다.
- 다음: 2회차 수정(manager-spec, sonnet) → 명시 경로 커밋·push → plan-auditor 재감사. 3회차 한도 안에서 진행한다.
