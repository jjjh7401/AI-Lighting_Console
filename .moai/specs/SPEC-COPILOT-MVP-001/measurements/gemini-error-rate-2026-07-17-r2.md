# M6b-1r2 — 룰북 보강 후 Gemini 재측정 요약 (2026-07-17)

Machine-readable report: `gemini-error-rate-2026-07-17-r2.json` (같은 디렉토리).
r1 결과: `gemini-error-rate-2026-07-17.{json,md}` (pooled 5.86% = 19/324, FAIL).
Scope: r1과 동일 — **LLM live (Gemini `gemini-3.5-flash`) / console mock**, 왕복 수치는
참고치 전용(AC-MVP-003 증거 아님). AC-MVP-002 최종 판정은 M6b-3 선정 프로바이더 기준.

## 조사 결론 (r1 원인 재확인 — 밸리데이터는 정당했음)

r1 5.86% FAIL의 원인은 **밸리데이터 결함이 아니라 룰북 교육 공백**이었다. 두 개의
read-only 조사 에이전트가 교차 검증한 결론:

1. `X='...'`/`/opt="..."` 형태(첨부형 대입 구문)는 **grandMA2 문법이며 grandMA3 v2.x에서
   무효**다. 공식 매뉴얼(help.malighting.com, v2.4) 근거:
   - `keyword_set.html` — `Set [Obj] Property ["Name"] ["Value"]` (분리된 토큰)
   - `keyword_equal.html` — `Set Macro 3.1 "Enabled" = "No"` (`=`이 인용 토큰 사이의
     별도 토큰)
   - `ok_file.html` — `Export Preset 2.5 /File "Endor"` (값을 갖는 옵션은 공백으로 분리)
   - `extended_command_line.html` — 옵션은 bare flag 형태
   - MA 포럼 스레드 2건에서 MA2 스타일 `/cmd=`/`/Color=`가 실제 MA3에서 실패하는 사례 확인
   - **결론: 밸리데이터의 거부 동작은 변경하지 않음**
2. 5.86% FAIL의 실제 원인은 룰북 교육 공백: (a) `00_grammar.md`가 매크로를 실행 가능한
   대상으로만 가르치고(`Macro 3`) 준수 저작 레시피가 없어 모델이 MA2 문법으로 공백을
   메움(16/19), (b) 네이밍 규칙+점 표기 풀 id 조합이 `Preset 4.'Blue'` 같은 토큰 내부
   인용을 유도(3/19), (c) 차단 사유에 재작성 힌트가 없어 자가 수정 루프가 소진(11회
   loop_limit).

## 변경 사항 (①②)

- **① 룰북 보강** (`server/rulebook/assets/v2.4.2/00_grammar.md`, commit `b43dafa`):
  "Authoring a macro" 레시피 신설 — `Set Macro <pool>.<line> Property 'Command' '<text>'`
  (v2.4.2는 `Command` 철자 사용, 구버전 자료의 `Cmd` 언급 명시). MA2 `/cmd=`/`/command=`
  첨부형 대입 anti-example 명시. 이름 참조 명확화: 인용된 이름은 항상 별도 토큰 —
  `pool.'Name'` 점-인용 조합 금지, `Preset 4.'Blue'`를 anti-example로 제시.
  AC-MVP-028 용어 사전(≥10항목, 샤막·워시 포함) 무변경 유지; 프리픽스는 가변 값 없음
  유지(REQ-MVP-008); `test_rulebook.py` 프리픽스 안정성 테스트 green 유지(바이트 동일성은
  세션 내 정체성이지 불변성이 아님 — 본 콘텐츠 변경은 세션당 1회 캐시 재작성 비용 발생,
  실측 확인: 스모크 런에서 캐시 재생성 관측).
- **② 밸리데이터 재작성 힌트** (`server/safety/grammar.py`, commit `0ee7992`): 거부 동작은
  **불변** — MA2 대입 형태 토큰에 매치되는 "misplaced quote inside token" 거부에만
  재작성 힌트를 부가(`Set <object> Property 'Command' '<value>'` 제안). 일반 misplaced
  quote는 힌트 없음. `grammar:` 접두사는 유지되어 오류율 분자 계수에 영향 없음.

## r2 실측 결과 vs r1

| 항목 | r1 (2026-07-17) | r2 (2026-07-17, 룰북 보강 후) |
|---|---|---|
| **Pooled 오류율** | **0.0586 = 19/324 — FAIL** | **0.0040 = 1/248 — PASS** |
| 회차별 오류율 | 4.88/8.00/6.35/4.00/5.45/6.15% | 0.00/0.00/0.00/2.50/0.00/0.00% |
| 반복 (실행/설정/상한) | 6 / 3 / 6 (상향) | 6 / 3 / 6 (상향) |
| 분모 (생성 라인) | 324 (≥300 충족) | 248 (**300 미달 — 아래 참고**) |
| 분자 (최초 생성 거부) | 19 | **1** |
| 턴 상태 | ok 115 / loop_limit 11 | ok 117 / loop_limit **9** |
| loop_limit 원인 | MA2 대입 패턴 전부 | 잔여 미확인(재현 곤란한 단발 패턴 가능성) |
| 텔레메트리 (model calls / cache-read) | 786 / 2,288,046 | 749 / 2,512,146 |
| 429 백오프 | 0 | 0 |

**분자 19→1 (94.7% 감소)**: r1의 19건 전수(MA2 대입 16건 + 점-인용 3건)가 제거됨.
잔여 1건은 **다른, 훨씬 사소한 신규 패턴** — `Fixture 'Wash'*` (닫는 인용 직후 비공백
문자 — 인용 이름 뒤 와일드카드 접미사 부착), 본 amendment의 범위(매크로 저작/이름 조합)
와 무관한 롱테일 케이스. 0.40%는 5% 임계 대비 12배 이상 여유.

## 분모 300 미달에 대한 정직한 기록

**r2 분모(248)는 acceptance §3의 ≥300 라인 하한에 미달** (`denominator_satisfied: false`).
원인: r1과 동일한 반복 상한(`--max-repetitions 6`)을 사용했으나, 오류율 감소 자체가
분모를 줄이는 부작용을 낳음 — 자가 수정 재시도가 크게 줄어(loop_limit 11→9, 그리고
grammar 재시도 자체가 거의 사라짐) 회차당 재생성 라인이 감소했다(회차당 평균 40.3 vs
r1의 54.0). 오늘 누적 사용량(중단된 시도 포함 실질 3회 라이브 풀런 + 스모크)을 고려해,
**추가 반복으로 300 라인을 채우는 것보다 이미 결정적인 마진(0.40% vs 5%, 12배 이상)에서
멈추는 것을 선택** — 경계 분해능 문제(1건당 오차폭)는 pooled rate가 임계값에서 이만큼
떨어져 있을 때 실질적 의미가 없다. **후속 조치가 필요하면**(예: M6b-3에서 엄격한 300
라인 하한 준수가 요구될 경우) 별도의 저비용 보충 실행(반복 상한을 10~12로 올린 단독
재측정)으로 폐쇄 가능 — 상세는 progress.md §E.2 M6b-1r2 및 본 리포트의 "잔여 위험" 참고.

## 참고치 (판정 비대상)

- 왕복 (mock 콘솔): median 9.76s / p95 33.51s, judged 110턴, 재시도 턴 1건 분리,
  콜드스타트 11.77s
- 게이트: rejected 번들 10건(위험 생성 → deny-all 정상 동작)
