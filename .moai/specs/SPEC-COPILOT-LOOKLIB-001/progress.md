# SPEC-COPILOT-LOOKLIB-001 — progress

## Plan-phase log

### v0.1.0 (최초 작성)

- 2026-07-26 — 출처: `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md` §3 P1-3(연출 어휘 계층 — 룩 라이브러리, 승인된 제안). manager-spec이 spec.md/plan.md/acceptance.md/design.md/research.md(5-file Tier L) + 본 progress.md 스켈레톤을 동시 생성.
- 2026-07-26 — 사용자 사전 확정 3건(재질의 금지, spec.md §A 수록): ① 속성 범위, ② 장르 4종(워십/록/발라드/EDM × 6~10룩), ③ v1 = 데이터 계층 + 인스턴스화 + 자연어 매칭 전부.
- 2026-07-26 — 미해결 결정 6건을 plan.md §A.4에 clarification 마커로 기록.
- ~~"브랜치 `feat/lighting-direction-features`, HEAD `81e2232`. 커밋은 오케스트레이터/사용자 결정 대기(파일은 워킹 트리에만 존재)."~~ — **낡음, v0.2.0에서 정정**(감사 D15). 아래 기준선 참조.
- ~~"design.md §5와 1:1"~~ — **거짓, v0.2.0에서 정정**(감사 D6a). 실제로는 마커 ③④가 슬롯 C 하나로 접혔고 슬롯 F에는 대응 마커가 없었다.

### v0.2.0 (독립 감사 반영 개정 — 2026-07-26)

- **감사 결과**: 독립 plan-audit **FAIL, 종합 0.65** (Tier L PASS 기준 0.85). 감사를 권위로 수용하고 원문을 방어하지 않는 방침으로 6개 아티팩트 전면 개정.
- **정정된 기준선 (감사 D15)**: 브랜치 `feat/lighting-direction-features`, HEAD **`fd59163`**. 아티팩트 6종은 **전부 git 추적·커밋 상태**(`8325b9b` 최초 작성 → `fd59163` 잔여 런타임 상태 파일 untrack). v0.1.0이 기록한 "워킹 트리에만 존재"는 그 시점의 사실이나 현재는 낡았다. `.moai/state/context-usage.json`은 이미 untrack되었으며 재생성하지 않는다.
- **사용자 확정 4건 추가 반영** (재질의 금지, spec.md §A 수록):
  - ④ **빔 축 유지 + M0 라이브 프로브 선행** — 라이브러리 저작 전 실물 콘솔에서 attribute 문법 실측(EXECBODY-001 M1 GO/DESCOPE 패턴). 스트로브 포함 여부는 프로브 결과 + 프리뷰 안전 발견(D5)과 함께 판단.
  - ⑤ **프리셋 슬롯 = 런타임 빈 슬롯 탐색** (고정 대역·설정값 기각).
  - ⑥ **인스턴스화 산출물 = 프리셋만** (데모 시퀀스·익스큐터 바인딩 기각).
  - ⑦ **충돌 처리 = 건너뛰고 "N개 건너뜀" 명시 보고** (덮어쓰기·재슬롯 기각).
- **감사 결함 처리 (18건 중 지적된 전부)**:

  | 결함 | 처리 |
  |---|---|
  | D2 (critical) REQ-001/003 상호 충족 불가 | 한 쌍으로 개정. 빔 어휘 리포지토리 0건 재실측 → ASSUMPTION-15 + M0 게이트. REQ-003을 3구간(확정/용도한정/프로브대기)으로 재구성, Pan/Tilt는 무브먼트 내부로 한정. `10_object_model.md:39` zoom=Focus 그룹핑 오류 정정. |
  | D5 (major) preview.py 안전 계층 누락 | research.md §5.5 신설 + §6 프리뷰 절 + §8 표 4행 추가. design.md §3 데이터 흐름에 프리뷰 단계 추가 + "screen 이후 무변경" 주장 정정(감싼다) + §4 위험 #9/#10 추가. 스트로브 v1 제외 확정. |
  | D3+D13 (major) 역할 어휘 사전 근거 부재 | spec.md §A·research.md §3에서 "신규 어휘"로 정정(0건 실측 명시). REQ-006을 명명 관례 *스타일* 준수로 재진술 — PRESERVE 파일 무변경. |
  | D6+D8 (major) 마커 집합 결함 | (a) 1:1 허위 주장 4곳 정정. (b) 마커 ①⑤를 리포지토리·문서 증거로 폐쇄. (c) 다이내믹스 척도를 신규 마커로 승격. |
  | D4 (major) 미커버 REQ 4건 | AC-015/016/017/019 신설 + §C.0 REQ↔AC 역추적표 도입(재발 구조적 봉쇄). REQ-021은 EXECBODY AC-011 형식 계승. |
  | D7 (major) 범위 누출 | REQ-010에서 "(또는 장르 묶음)" 제거. |
  | D9 (major) M1 과적재 + 전제 순서 결함 | M0 프로브 신설 + M1 분해(스키마/어휘/로더 ↔ 라이브러리 저작). 마일스톤 M0~M7. spec.md:93 허위 교차참조 삭제. 라이브 세션 **2회**로 명시. |
  | D10 AC-008 검증 미달 | ①~④로 분해, 실행 호출 경로 grep(③) 신설. |
  | D11 REQ-014 `Where` 오용 | 역량 게이트로 재진술 + AC-016(정적 부재 검증). |
  | D12 AC-014 비토큰 축약 | 완전 토큰으로 정정 + REQ-013 유닛 AC-018 신설. |
  | D14 AC-007 대소문자 | `re.IGNORECASE` assert 규칙 명문화 + design.md AP-13. |
  | D15 낡은 기준선 | 본 절 + spec.md §C 갱신. |
  | D17 Phase 2/3 | spec.md §A에 1문단 추가(Phase 3 산출물로 Phase 2 기준 충족). |
  | D18 빔 출처 | spec.md §A에 P1-2:78 ↔ P1-3:84 치환 기록. |
  | 인용 nit | `tools.py:233-265` → **`231-272`**(`drill_into` 실제 범위). |

- **남은 미해결 마커 3건** (plan.md §A.4b ↔ design.md §5.2 슬롯 R1/R2/R3, **진짜 1:1**) — 각각 구체적 제안 기본값 + 근거 동반:
  1. **역할 어휘 폐쇄 집합** — 제안: 6종(백라이트/프론트/사이드/탑/배경/스페셜) + 한영 별칭 + 매핑 힌트.
  2. **다이내믹스 단계 척도** — 제안: 정수 1~5, 검증식 `1 <= level <= 5`, 스팬 판정 `{1,2}`≥1 ∧ `{4,5}`≥1.
  3. **역할 매핑 확정 UX** — 제안: 자동 휴리스틱 + 적용 전 요약 보고(방어 3겹 근거) / 반대 논거 병기.
- **next**: plan-audit 재실행(Tier L PASS 기준 0.85) → §A.4b 마커 3건 AskUserQuestion 해소 → **M0 라이브 세션 접근 가능성 확인** → Implementation Kickoff Approval → run(M0 프로브부터).

## §E.1 Plan-phase Audit-Ready Signal

_<pending plan-audit>_

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
