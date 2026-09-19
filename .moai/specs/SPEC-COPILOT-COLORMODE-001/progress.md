# SPEC-COPILOT-COLORMODE-001 — 진행 기록

## §Phase 1 — Plan (현재)

- 워크트리: `t404` (`.claude/worktrees/t404`), 브랜치 `WT-color-usage-question`, base `main 91695109`.
- 카드: t404.
- 산출물: `spec.md`, `plan.md`, `acceptance.md`, `research.md`, `progress.md` (본 파일) — 5개 전부 plan-phase에 생성.
- 상태: `draft`. 코드 변경 없음, 커밋 없음(위임 지시대로 plan-phase 산출물 작성만 수행).

## §E.1 Plan-phase Audit-Ready Signal

- Tier: M (마일스톤 2개, 예상 변경 파일 ~8개). frontmatter `tier: M` 명시(plan-audit D8 보정).
- Out of Scope 절: `spec.md` §4에 5개 `### Out of Scope — <주제>` 하위 항목 존재(각 `-` 불릿 포함) — `OutOfScopeRule` 린트 충족.
- GEARS 요구사항 16건(`REQ-COLORMODE-001`~`016`, Tier M 상한 16 이내), 인수 기준 16건(`AC-COLORMODE-001`~`016`, Tier M 상한 16 이내) — acceptance.md 최소 2건 요건 충족. 모든 REQ가 최소 1개 AC로 검증됨(orphan 없음, spec.md §3 REQ→AC 추적 표), 모든 AC 헤딩이 검증 대상 REQ ID를 명시.
- `[NEEDS CLARIFICATION]` 마커 없음 — 위임된 설계 결정은 spec.md §2에 확정 사실로 기록됨(재검토 대상 아님).
- `research.md`에 실측 file:line 인용 다수(§1-§8) — 위임 브리프의 근거를 재확인·일부 수정(§9).
- **plan-audit iteration 1 FAIL(0.75) → 5건(D1/D2/D3/D4/D8) + minor 3건(D5/D6/D7) 전량 보정 완료** — 보정 내역: tier 프론트매터 추가(D8), single×palette_mode 우선순위를 REQ-013/plan.md M2/AC-012에 명시(D4), "Q2 다시"의 Q2B 폐기 부수효과를 REQ-016+AC-015로 명문화(D3), REQ-004 회귀를 AC-016으로 신설(D1), 전체 AC에 REQ 추적 인용 + spec.md REQ→AC 표 신설(D2), GEARS 태그 통일(D5), per_chorus 저-회차 경계 명시(D6), skipped_steps 문서화(D7).
- **plan-audit iteration 2 (v0.2.0) PASS — 조화평균 1.0** (Clarity/Completeness/Testability/Traceability 각 1.0, must-pass 7/7). 보고서 `.moai/reports/t404/plan-audit.md` § 재감사 2026-09-20 v0.2.0. 8건 델타 전량 RESOLVED, 잔여 차단 없음.
- plan_complete_at: 2026-09-20T15:40:00+09:00
- plan_status: audit-ready
- Implementation Kickoff: 감독 위임(2026-09-20 「남은 카드는 묻지 말고 판단해서 단계별로 진행」)에 따라 오케스트레이터가 승인 처리. 진행 방식 autonomous.

## §F Phase 4 Mode Selection

- 입력: tier M · 예상 파일 ~8(server/design/interview.py, server/web/session.py, server/design/song_plan.py, ui/src/components/analysisSummary.ts + 테스트 5) · 도메인 2(server python, ui ts) · 언어 혼합 py+ts · 동시성 이득 LOW(코딩 중심, 파일 간 의존 강함).
- 평가: direct — 미선택(다중 파일·의미 변경). fanout — 미선택(연구가 아니라 구현, 도메인 2). sweep — 미선택(기계적 변환 아님). serial — **선택**.
- Decision: serial
- 근거: 인터뷰 스텝 추가 → 축 추가 → 세션 배선 → 요약 소비 순으로 파일 간 의존이 직렬이라 한 구현 담당이 M1→M2 순서로 진행하는 것이 가장 단순하다. Anthropic 코딩 작업 병렬화 주의에 부합.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
