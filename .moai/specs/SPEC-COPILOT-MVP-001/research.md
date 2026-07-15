# SPEC-COPILOT-MVP-001 — 리서치 노트 (research)

> Tier L 리서치 산출물 (plan-audit MVP-M6 반영). 이 프로젝트는 그린필드로 분석할 기존 코드가 없다. 본 문서는 ① DESIGN.md 소스에서 도출한 MA3 OSC/Lua 외부 제약 정리, ② Phase 0(SPEC-COPILOT-EVAL-001) 산출물 포인터로 구성된다.

## A. MA3 OSC 통신 제약 (DESIGN.md §3, §8; tech.md §8)

- **UDP 무연결**: 송신 유실은 관측 불가능하며, 콘솔 오프라인은 "침묵하는 아웃바운드 유실"로 나타난다 → REQ-MVP-030~032(장애 모드)의 설계 근거. 부수효과 명령의 블라인드 재전송은 중복 실행 위험이므로 금지(REQ-MVP-032~033).
- **주소 체계**: 자체 네임스페이스 `/copilot/*` 확정(2026-07-15 결정) — 송신 `/copilot/cmd`, 피드백 `/copilot/feedback`, 상태 `/copilot/state`. boardop 관례(`/gma3/cmd`/`/python/feedback`)와의 비호환은 동시 설치 충돌 방지를 위한 의도적 선택.
- **피드백 수신**: 콘솔의 오류/성공 응답을 수신해 자가 수정 루프에 공급한다 (DESIGN.md §4.5 3중 방어의 ③).

## B. grandMA3 Lua 5.4 responder 제약 (tech.md §2; DESIGN.md §9)

- 콘솔측 상주 컴포넌트는 Lua 5.4 환경이며, socket 기반 상태 회수를 담당한다.
- 오브젝트 트리 경로 조회(예: `DataPool/Sequences`, `ShowData/Patch`)가 상태 스냅샷의 기본 단위다 (REQ-MVP-003).
- responder 자체의 크래시/미응답은 서버에서 하트비트/타임아웃으로만 감지 가능 → REQ-MVP-031의 근거.
- MA3 버전 업데이트가 Lua API/OSC 스펙을 바꿀 수 있다 → v2.x 세부 버전 핀(plan.md §A-2) + 버전별 룰북 분리 + 회귀 테스트 스위트 (DESIGN.md §8 리스크).

## C. 프롬프트 캐싱 제약 (DESIGN.md §4.3)

- 시스템 프롬프트(문법 룰북 + 오브젝트 모델 요약)는 1~2만 토큰 규모 — 고정 프리픽스 캐싱이 비용 구조의 핵심.
- 프리픽스 1바이트 변경도 캐시 전체를 무효화한다 → 룰북에 타임스탬프·세션 ID 등 가변 값 삽입 금지(REQ-MVP-008) + 프리픽스 바이트 안정성 자동 테스트(AC-MVP-014).
- 쇼 스냅샷 등 턴마다 변하는 컨텍스트는 messages의 마지막 user 턴에 주입 (캐시 프리픽스 보존).
- 첫 턴은 캐시 write(1.25×)로 지연이 크다 → 왕복 시간 판정은 웜캐시 조건(acceptance.md "왕복 시간 측정 방법" ③).

## D. boardop 아키텍처 관찰 항목 (코드 미열람 원칙)

FSL-1.1 제약에 따라 **동작 관찰 기준**으로만 벤치마킹한다 (코드 인용·의사코드 전사 금지 — SPEC-COPILOT-EVAL-001 REQ-EVAL-010):

- 3계층 지식 레이어(검증된 문법 룰 / 콘솔 오브젝트 모델 / 사용자 커스텀 룰) — 문법 환각 억제의 선행 사례.
- blast-radius 안전 필터 — 우리 설계는 이를 폐쇄 블랙리스트 + 전개-또는-보류 + 단일 관문으로 강화(spec.md B.8).
- Lua responder + 플러그인 풀, pcall 컴파일 하네스 — deploy_plugin 게이트(REQ-MVP-019, 027~028)의 참고 패턴.

## E. Phase 0 산출물 포인터 (EVAL→MVP fold-in 입력)

- 격차 분석 문서: `.moai/project/research/boardop-gap-analysis.md` (SPEC-COPILOT-EVAL-001 완료 시 산출).
- "Phase 1 반영" 격차 항목은 plan.md §F 절차(manager-spec amendment + plan-audit delta 재실행)를 통해서만 본 SPEC 요구사항에 반영된다.
- 격차 축 → 마일스톤 매핑은 plan.md §F의 표를 따른다 (축① UX→M5, 축② 안전장치→M4, 축③ 도구→M3, 축④ 신뢰성→M1/M2/M6).

## F. Google Gemini API 제약 (2026-07-15 amendment — 아는 범위 정리)

멀티 프로바이더 추상화(spec.md §B.12)의 Gemini 어댑터 설계 입력. 확실도가 낮은 항목은 **[구현 시 검증]** 으로 표기한다 (사용자 결정 대기 항목 아님 — run-phase 검증 태스크).

- **도구 호출(function calling)**: Gemini API는 function declaration 기반 도구 호출을 지원하며, 스키마 형식이 Anthropic tools 형식과 다르다(OpenAPI 스타일 함수 선언) — 어댑터가 중립 도구 정의에서 변환해야 한다. 병렬 함수 호출 지원 여부와 도구 강제(tool_choice 상당) 옵션의 세부는 **[구현 시 검증]**.
- **tool runner 상당 기능**: Anthropic SDK의 `tool_runner()` 같은 자동 도구 실행 루프가 Gemini SDK에 동일 형태로 존재하지 않을 수 있다 — 어댑터에서 수동 도구 루프 구현 필요 여부 **[구현 시 검증]**.
- **컨텍스트 캐싱(context caching)**: Gemini API는 명시적 context caching(캐시 객체 + TTL)을 제공하며, **최소 캐시 가능 토큰 임계**가 존재한다 — 룰북(1~2만 토큰) 이 임계를 충족하는지, 모델별 임계값·암시적(implicit) 캐싱 적용 조건은 **[구현 시 검증]**. 임계 미달 시 REQ-MVP-041의 비캐시 경로로 동작.
- **시스템 프롬프트**: system instruction 필드로 전달 — Anthropic system 파라미터와 배치 전략(고정 프리픽스 + 가변 컨텍스트 분리)의 등가성 **[구현 시 검증]**.
- **무료 등급 rate limit**: Gemini 무료 등급은 RPM/TPM/일일 요청 상한이 있다 — Phase 0 평가에는 적합하나, MVP의 왕복 <10초 중앙값 판정과 오류율 측정 코퍼스(≥300라인) 실행이 rate limit 하에서 가능한지 **[구현 시 검증]** (유료 등급 전환 조건 포함).
- **adaptive thinking / effort 상당**: DESIGN.md §4.2의 `thinking={"type": "adaptive"}` + `effort` 설정은 Anthropic 전용이다 — Gemini의 thinking 설정(사고 예산 등) 등가 매핑은 **[구현 시 검증]**.

## G. 미해결 조사 항목

- 문법 밸리데이터의 검증 깊이(키워드 화이트리스트 수준 vs 완전 문법 파싱)는 Phase 0 격차 분석의 "신뢰성" 축 결과를 입력으로 M4에서 확정한다 (plan.md §A-6).
- 감사 로그(JSONL·일별 로테이션·90일)와 OSC 네임스페이스(`/copilot/*`)는 사용자 결정 완료 (2026-07-15, plan.md §A-4/§A-5) — 잔여는 저장 경로 세부(`server/` 하위)로 구현 시 결정.
- Gemini 어댑터의 [구현 시 검증] 항목 목록은 §F 참조 — run-phase M3에서 검증 태스크로 소화한다.
