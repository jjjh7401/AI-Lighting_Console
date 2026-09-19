# 진행 기록 — SPEC-LDWIRE-001

[요구사항](spec.md) · [설계 결정](design.md) · [계획](plan.md) · [인수](acceptance.md)

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-09-19T00:00:00+09:00
- plan_status: audit-ready

(plan-auditor iteration 2/2 — CONDITIONAL→ 모든 blocking 결함 D1~D3 해소,
남은 MP-7 결함도 research.md:153 정정으로 해소. 착수 승인은 사용자가
AskUserQuestion 으로 확정했다.)

### 2026-09-19 — [NEEDS CLARIFICATION] 4항목 해소

plan.md §2 의 네 [NEEDS CLARIFICATION] 마커를 사용자가 전부 확인했다 —
네 항목 모두 design.md 의 권고 대안(대안 A)을 채택했다:

1. 운영 자격증명 수명 — 매 기동 재발급(design.md §가 대안 A).
2. `ValidationReport` 저장 위치 — 기존 `DirectorStore`(sqlite) 확장
   (design.md §나 대안 A).
3. `PipelineValidator` per-request context 주입 — route 층에서 요청마다
   재구성(design.md §다 대안 A; `PlanValidator` Protocol 은 건드리지 않음).
4. `ContextProvider` 관측 축 범위 — `identity`/`expiry`/`policy` 세 축만
   이 SPEC 에서 관측 소스를 배선하고, 나머지 여섯 축(`show`/`audio`/
   `group_membership`/`preset_content`/`compiler`/`capability`)은 스파이크
   없이 처음부터 정직한 미관측 상태로 채우기로 확정(design.md §라).

반영 파일: `plan.md`(§2 재작성 + M1/M3/§6 위험 갱신), `spec.md`(§2 범위 결정
불릿 + REQ-LDWIRE-004), `acceptance.md`(AC-LDWIRE-004 + 엣지 케이스 + DoD),
`design.md`(§가/§나/§다/§라 + 맺음 문단). `plan.md`/`design.md` 안의
`[NEEDS CLARIFICATION: ...]` 마커는 모두 제거·치환됐다(grep 재확인 완료).
`spec.md` frontmatter `status:` 는 `draft` 로 유지 — plan-auditor 검토 전이라
`audit-ready` 로 승격하지 않는다.

### 2026-09-19 — plan-auditor CONDITIONAL 판정 D1~D3 수정

plan-auditor 가 CONDITIONAL 판정과 함께 blocking 결함 3건을 반환했다 — 기존에
확정된 4개 설계 결정(design.md §가/§나/§다/§라)은 재검토하지 않고, 지적된
결함만 수정했다:

- **D1 (route-count-mismatch)**: `grep -c "^    @router\." server/director/
  director_api.py` 로 실측한 결과 route 수는 8개가 아니라 **10개**였다.
  spec.md:37, research.md(§88-90 부근 prose), acceptance.md AC-LDWIRE-009
  네 곳의 "8개"를 전부 "10개"로 정정했다. 재발 방지를 위해 AC-LDWIRE-009 를
  바레 개수 단언에서 **10개 route 의 (method, path) 경로 전부를 부분집합으로
  포함**하는지 확인하는 형태로 재작성했다 — route 가 추가/제거돼도 이 AC 가
  조용히 낡은 숫자로 남지 않도록.
- **D2 (phantom-expiry-policy-not-traced-to-any-REQ)**: acceptance.md §2
  엣지 케이스가 REQ-LDWIRE-006/design.md §나 어디에도 없는 "10분" TTL 값을
  단언하고 있었다 — 실제로는 사용자에게 확인받은 적 없는 조작된 설계 세부
  였다. 그 구체적 수치 주장을 제거하고 "만료 정책(TTL 의 정확한 값·산식)은
  M2 구현 시 확정한다"는 명시적 유예 마커로 치환했다 — 없는 사용자 확인을
  날조하지 않는다.
- **D3 (REQ-LDWIRE-010-has-no-acceptance-criterion)**: REQ-LDWIRE-010(스레드
  제약 — `DirectorStore`/`ExecutionJournal` 은 FastAPI event-loop 스레드
  안에서 생성돼야 한다, `director_api.py:156-159` docstring 이 이미 문서화한
  실측 `sqlite3.ProgrammingError` 재현 조건)에 대응하는 AC 가 없었다.
  `test_director_ops_lifecycle.py` 의 `client` fixture `_lifespan` 패턴(비동기
  lifespan 안에서 `DirectorStore` 생성)을 모델로 신규 `AC-LDWIRE-011` 을
  추가하고, REQ↔AC 추적 줄을 명시했다.

반영 파일: `spec.md`(§1.1 표 8개→10개, grep 근거 인용 추가),
`research.md`(§1 prose 8개→10개), `acceptance.md`(AC-LDWIRE-009 재작성 +
엣지 케이스 D2 치환 + AC-LDWIRE-011 신규 + REQ↔AC 추적 줄). grep 재확인
결과: "8개" 0건, 미귀속 "10분" 0건, REQ-LDWIRE-010 ↔ AC-LDWIRE-011 추적
확보(위 검증 출력 참고). design.md 의 4개 확정 결정(§가/§나/§다/§라)과 plan.md
의 M1~M7 마일스톤 구조는 이번 수정에서 손대지 않았다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
