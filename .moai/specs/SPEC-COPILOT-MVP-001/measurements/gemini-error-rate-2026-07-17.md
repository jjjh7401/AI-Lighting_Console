# M6b-1 — Gemini 문법 오류율 실측 요약 (2026-07-17)

Machine-readable report: `gemini-error-rate-2026-07-17.json` (same directory).
Scope: **LLM live (Gemini `gemini-3.5-flash`) / console mock** — 왕복 수치는 참고치 전용
(AC-MVP-003 증거 아님). AC-MVP-002의 최종 판정은 M6b-3에서 선정되는 기본 프로바이더
기준이며, 본 결과는 그 선정 술어(REQ-MVP-040)의 **Gemini 측 입력**이다.

## 결과 (acceptance.md "문법 오류율 측정 방법" §1-8)

| 항목 | 값 |
|---|---|
| Pooled 오류율 (판정 기준) | **0.0586 = 19/324 — 5% 임계 초과 (Gemini 측 FAIL)** |
| 회차별 오류율 (6회) | 4.88% / 8.00% / 6.35% / 4.00% / 5.45% / 6.15% |
| 분모 (생성 명령 라인 총수) | 324 (≥300 충족 — 3회→6회 반복 상향) |
| 분자 (최초 생성 문법 거부) | 19 (자가 수정 성공 후에도 계수 — §4) |
| 코퍼스 | 21시나리오 × 6반복 (표준 시나리오 ≥20종 — §1) |
| 웜캐시 조건 | 워밍업 1턴 수행, 콜드스타트 13.87s 참고치 별도 (§3) |
| 고정 추론 설정 (§5) | model=`gemini-3.5-flash`, context_caching=true, cache_ttl=3600s, 생성 파라미터 = SDK 기본값 (온도 등 미지정) |

## 참고치 (판정 비대상)

- 왕복 (mock 콘솔 — 참고 전용): median 11.49s / p95 33.56s, judged 106턴, 재시도 턴 9건 분리
- 프로바이더 텔레메트리: 786 model calls, input 3,286,290 tok / output 38,607 tok /
  **cache-read 2,288,046 tok (input 대비 69.6%)** — AC-MVP-014② Gemini 구성 라이브 증거
- 429 백오프 재시도: 0건 (전 구간 rate-limit 미발생) · wall clock 2,152.6s
- 턴 상태: ok 115 / loop_limit 11 · 게이트: rejected 번들 16건 (위험 생성 → deny-all 승인 경로 — 정상 게이트 동작)

## 오류 분해 (분자 19건 전수)

19건 전부 동일 패턴: `misplaced quote inside token` — 모델이 MA3 옵션 대입 구문
`Assign Macro 21.1 /Cmd='ClearAll'` 형태(토큰 내부 인용)를 생성, 구조 밸리데이터가
거부. plan.md §A-6의 의도된 과차단(안전 비대칭) 설계와 실모델 출력 습관의 상호작용.
loop_limit 11턴도 동일 패턴의 교정 루프 소진. 밸리데이터의 토큰 내 인용 대입 구문
수용 여부는 게이트 동작 변경이므로 **M6b-3/체크인 결정 사항** (본 실측에서는
acceptance 정의 그대로 "밸리데이터가 거부한 라인"을 분자로 계수).
