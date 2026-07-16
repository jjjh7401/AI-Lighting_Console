# SPEC-COPILOT-EVAL-001 — progress

## §E.1 Plan-phase Audit-Ready Signal

plan_status: audit-ready
plan_complete_at: 2026-07-15

Plan-phase 산출물 3종(spec.md / plan.md / acceptance.md) + progress.md 생성 완료, `status: draft` (v0.2.0). 산출물 형상: `tier: S` + 별도 acceptance.md (의도적 과제공 — spec.md §A 비고 참조).

amendment 이력: **v0.2.0 (2026-07-15)** — LLM 프로바이더 전략 정식 amendment: 평가는 Anthropic 또는 Gemini API 키로 수행(Gemini 무료 등급 우선 권장, $20 상한은 양 프로바이더 유료분 합산 — REQ-EVAL-001/003 개정), REQ-EVAL-013(선택적 Claude/Gemini 비교) + AC-EVAL-007(조건부) 신설. **delta re-audit 필요.**

plan-audit 이력: iteration 1 **PASS (0.90)** — minor 지적(E-m1~E-m5) 반영 → iteration 2 **PASS (0.96)** — E-m6 반영 완료 (REQ-EVAL-011의 이중 shall 절을 REQ-EVAL-011 [Ubiquitous] / REQ-EVAL-012 [State-driven]로 분리, AC-EVAL-006 연계 갱신).

clarification gate: **resolved** — plan.md §A 마커 2건 전원 사용자 결정(AskUserQuestion 라운드)으로 해소, "결정됨 (2026-07-15)" 기록으로 대체 (최신 안정 v2.x 릴리스 핀 / API 예산 상한 $20).

## §F Phase 4 Mode Selection

- Input parameters: tier=S, scope=문서 산출물 2~3개 (코드 0), domain=1 (평가/리서치), language mix=markdown 100%, concurrency benefit=LOW (대화형 데스크톱 평가 — onPC GUI 관찰 필수)
- Mode evaluation: trivial=미선택(다단계 작업) / background=미선택(GUI·사용자 상호작용 필요) / agent-team=RETIRED / parallel=미선택(단일 도메인) / workflow=미선택(기계적 대량 변환 아님) / **sub-agent(변형)=선택**
- Decision: sub-agent (orchestrator-direct 변형 — 대화형 평가 세션은 오케스트레이터가 직접 수행, 조사·문서 위임은 필요 시 개별 spawn)
- Justification: 평가 SPEC의 핵심 작업(onPC 구동 관찰, boardop 세션, API 키 입력)은 사용자 상호작용과 데스크톱 GUI 접근이 필요해 격리된 서브에이전트로 수행 불가. Anthropic coding-task parallelism caveat에 따라 순차 진행. Implementation Kickoff Approval 승인 완료 (2026-07-15, AskUserQuestion — "지금 시작" 선택), git init 승인 포함.

## §E.2 Run-phase Evidence

**2026-07-15 — M1 부분 완료 + 외부 대기, M2 완료 (병행 진행 사용자 승인)**

- git 저장소 초기화 + 베이스라인 커밋 (사용자 승인, Implementation Kickoff Approval 라운드).
- 환경 기록 6종 중 5종 확보: onPC 2.4.2 (macOS) / boardop 공개 저장소 c13c274 (README-only) / macOS 26.4.1 / Python 3.11.15 / 프로바이더 계획 Gemini. 모델 ID는 번들 수신 후 실측.
- **M1 blocker (외부 대기)**: boardop 실행 코드 미공개 — 베타 신청(hello@boardop.dev) 후 zero-install 번들 이메일 수신 필요. 플랫폼 Windows-first (macOS 미언급) — macOS 구동 시도 결과 자체를 격차 데이터로 기록 예정. 사용자 결정: "베타 신청 + 병행 진행".
- M2 산출: `.moai/project/research/boardop-eval-log.md` — 환경 기록 표 + 시나리오 세트 11종 (S1~S10 + S-D 파괴적 1종, REQ-EVAL-005/011 충족; S-D는 일회용 쇼파일 전용 REQ-EVAL-012).
- 격차 후보 1건 선등록: 배포 채널 폐쇄성 + Windows 단일 플랫폼 (축 ④).

**2026-07-16 — 문서 폴백 전환 + M3~M5 완료 (run-phase 산출 완결)**

- 폴백 전환: 사용자 결정("문서·영상 관찰 기반으로 SPEC 재조정", AskUserQuestion 2026-07-16) → manager-spec amendment v0.3.0 → plan-auditor delta FAIL 0.87 (F1~F6) → manager-spec 수정 v0.3.1 → **delta re-audit PASS 0.95** (사이클 2/3 종결). status: draft → in-progress (F5 해소).
- M3: eval-log §3 — S1~S10+S-D 전 행 3태그 분류(관찰 기반 4 / 관찰 불가 7) + 행별 출처 인용(README·demo GIF 프레임·homescreen). 폴백 트리거 충족 증거 §3.0 기록. API 사용량·모델 ID는 데모 관찰값으로 기록(REQ-EVAL-001 폴백 조항).
- M4: `boardop-gap-analysis.md` — 격차 **14건** (반영 11/보류 3/미반영 0), 4축 전부 커버 (REQ-EVAL-007/008 충족).
- M5: FSL-1.1-Apache-2.0 결론 절(§3, REQ-EVAL-009) + AC-EVAL-005 4항목 검수 기록(§4, 전항목 0건).

### AC 자가 검증 매트릭스 (문서 폴백 경로)

| AC | 판정 | 증거 |
|---|---|---|
| AC-EVAL-001 | PASS [문서 폴백] | 환경 기록 6종 (모델 ID·토큰 실측 = "관찰 불가 — 라이브 실행 미확보" 표기) + 접근 시도 기록 §3.0 (eval-log) |
| AC-EVAL-002 | PASS [문서 폴백] | 시나리오 행 11종(≥8) — 전 행 태그+출처 인용, 관찰 불가 행은 탐색 범위 기록 |
| AC-EVAL-003 | PASS | gap-analysis 존재, 4축, 격차 14≥10, 반영 여부 전 항목 표기 |
| AC-EVAL-004 | PASS | gap-analysis §3 독립 절 + 결론 문장(내부 평가 허용/경쟁 제품 코드 재사용 제약/아키텍처만 벤치마킹) |
| AC-EVAL-005 | PASS | gap-analysis §4 — 4항목 이진 체크리스트 전항목 0건, 검수자 확인 |
| AC-EVAL-006 | PASS [문서 폴백] | S-D 세트 유지 + REQ-015 태그 + 안전장치 문서 근거 평가, 실행+쇼파일 조항 N/A (eval-log §3.1) |
| AC-EVAL-007 | 평가 안 함 | 선택 실행 미수행 (라이브 세션 부재) |

## §E.3 Run-phase Audit-Ready Signal

run_status: audit-ready
run_complete_at: 2026-07-16

문서 폴백 모드(REQ-EVAL-014) 하 run-phase 산출 완결. DoD 5항목 중 4항목 충족(마지막 1항목 — MVP 범위 확정 입력 제공 — 은 격차 목록+반영 여부로 충족, sync-phase에서 최종 확인). 잔여: 라이브 접근 확보 시 라이브 증거 우선 원칙에 따라 재평가 여지 존재(비차단).

## §E.4 Sync-phase Audit-Ready Signal

sync_status: audit-ready
sync_complete_at: 2026-07-16
sync_commit_sha: 0f7fbeb7e86108a18893dde33fd8434d26acab00

- `CHANGELOG.md` `[Unreleased]` — SPEC-COPILOT-EVAL-001 항목 신설 (B12 자가검증: `grep -c 'SPEC-COPILOT-EVAL-001' CHANGELOG.md` = 1 사전 확인, AC 수 acceptance.md 7건과 CHANGELOG 서술 정합, 산출물 경로 `ls` 검증 완료).
- `.moai/project/tech.md` §5 — 감사 트레일에 기록된 divergence(Anthropic 단일 프로바이더 서술 vs amended SPEC-COPILOT-MVP-001 REQ-MVP-038~041 듀얼 프로바이더 추상화) 해소.
- `.moai/specs/SPEC-COPILOT-EVAL-001/spec.md` frontmatter: `status: in-progress` → `completed` (단일 sync 커밋, `updated:` 은 이미 2026-07-16). spec/plan/acceptance 본문은 미변경 (manager-docs 소유 경계 준수).
- 단일 sync 커밋으로 3-phase close 완결 (별도 Mx 커밋 없음). SHA는 커밋 이후 후속 커밋에서 백필.
