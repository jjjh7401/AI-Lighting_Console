# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **SPEC-COPILOT-EVAL-001** — Phase 0 boardop 실사용 평가 및 격차 분석 완료 (문서 폴백 모드, REQ-EVAL-014). onPC 구동 실행 파일 미확보(베타 신청 대기)로 인해 문서·데모 영상 관찰 기반 평가로 전환(사용자 승인, AskUserQuestion 2026-07-16)하여 run-phase를 완결했다.
  - `.moai/project/research/boardop-eval-log.md` — 환경 기록(6종 중 5종 실측 + 1종 관찰 불가 명시) + 대표 시나리오 11종(S1~S10 + 파괴적 시나리오 S-D) 3태그 분류(관찰 기반 4 / 관찰 불가 7) 및 행별 근거 출처 인용.
  - `.moai/project/research/boardop-gap-analysis.md` — 4축(①한국어 UX ②안전장치 ③도구 커버리지 ④신뢰성) 전부 커버하는 격차 14건(Phase 1(MVP) 반영 11 / 보류 3 / 미반영 0) + FSL-1.1-Apache-2.0 라이선스 검토 결론(§3 — 내부 사용·평가 허용, 경쟁 제품 코드 재사용은 릴리스별 2년 제약, 아키텍처만 벤치마킹·clean-room 구현) + AC-EVAL-005 boardop 코드 미포함 4항목 이진 체크리스트 검수(§4, 전항목 0건).
  - AC-EVAL-001~006 전부 PASS(문서 폴백 경로), AC-EVAL-007(선택적 Claude/Gemini 비교)은 라이브 세션 미실행으로 평가 제외 — acceptance.md 기준 총 7개 AC 중 6개 평가·PASS, 1개 조건부 미평가.
  - amendment 이력: v0.2.0(LLM 듀얼 프로바이더 전략) → v0.3.0(문서 폴백 재조정, plan-audit delta FAIL 0.87) → v0.3.1(수정 후 delta re-audit PASS 0.95).

### Changed

- `.moai/project/tech.md` §5.1 — 단일 프로바이더(Anthropic 전용) 모델 전략 서술을 SPEC-COPILOT-MVP-001 REQ-MVP-038~041(프로바이더 교체 가능 추상화 계층, Claude/Gemini 듀얼 지원, 오류율 기반 기본 프로바이더 선정, 프로바이더별 캐싱) 반영으로 갱신하여 amended SPEC 상태와의 괴리를 해소.
