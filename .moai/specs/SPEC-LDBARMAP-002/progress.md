# SPEC-LDBARMAP-002 — Progress

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-14
- 작성 카드: t638. 입력과 읽은 줄은 `spec.md` §3 전제표에 있다.
- Tier: M (`spec.md` §0 근거) — REQ 16개·AC 16개, Tier M 상한(각 16개)에 정확히 닿는다.
- 자체 점검(plan-audit 전):
  - SPEC ID 정규식: Bash 실행 `ID="SPEC-LDBARMAP-002"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS`.
  - ID 유일성: `git grep -c "SPEC-LDBARMAP-002"` 를 `origin/main` 과 원격 브랜치 `WT-barmap-plan`·`WT-barmap-store`·`WT-barmap-run`·`WT-barmap-precision`·`WT-barmap-halfdouble`·`worktree-WT-ldbarmap-close` 에 실행 → 출력 없음(0건). REQ/AC 접두사 `LDBARENTRY` 도 `origin/main` 0건.
  - `depends_on: SPEC-LDBARMAP-001` → 그 SPEC `status: completed`(`SPEC-LDBARMAP-001/spec.md:5`)라 충족.
  - 프런트매터 12필드와 `tier` 선택 필드를 `spec-frontmatter-schema.md` 와 대조.
  - 시험·코드 실행 0회 — 이 plan-phase 는 문서만 쓴다.
- **감독 결정 반영(2026-10-14, 「전부 권고안대로」)**: `plan.md` §B의 미결 표지 6개를 해소했다 — D1 오프셋은 필수 요청 필드, D2 4/4 전용, D3 새 타입 `bar_map_analyse`, E1 두 배 BPM 채택은 저장 거절, E2 거절도 `status` `ok` + 요약, E3 곡 대응은 확인하지 않음(알려진 한계). E4(저장 `bpm`은 검출기 값만)도 확정을 확인했다. D4(화면 자리)는 후속 UI 카드의 결정이라 run-phase 를 막지 않는다.
- plan-audit 1차: FAIL(MP-7) — `.moai/reports/plan-audit/SPEC-LDBARMAP-002-review-1.md`(0.84, 문턱 0.80 위, 게이트 사유 MP-7 표지 6개). 결함 반영(2026-10-14, version 0.1.1): D2~D11, D13, D14 반영. D12(REQ 본문의 식별자)는 문체 문제이고 변경이 크다고 보아 반영하지 않았다. 표지 6개(D1·D2·D3·E1·E2·E3)는 감독 결정 대기로 유지. 2차 대기. (그 일자의 기록 — 같은 날 감독 결정으로 해소, 위 항목 참조.)
- plan-audit 2차: FAIL(MP-7만, 0.94) — review-2. 감독 결정 후 3차 감사.
- base 갱신(2026-10-14): `origin/main` `f5eada95` → `cca88d23` rebase. `server/web/app.py`·`session.py`의 줄 번호 인용을 새 base 기준으로 고쳤다(spec.md 54곳, plan.md 3곳, acceptance.md 3곳, 합 60곳). 처음 감사한 base는 `f5eada95`이고 `.moai/reports/plan-audit/`의 감사 보고서는 그 base의 줄 번호를 유지한다. 전제 P1~P18은 줄 번호만 이동, 서술이 바뀐 것은 Gaps 5번뿐.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
