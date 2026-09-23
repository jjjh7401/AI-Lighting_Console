# t439 — 13게이트 × 8곡 최종 실측

명령: `uv run python .moai/reports/t439/gen_gates_final.py`

| 게이트 | Club Diver.m | Cut and Run. | Ice cream.mp | Morning.mp3 | Rain.mp3 | Too Cool.mp3 | scott-buckle | 걸그룹DinoDino_ |
|---|---|---|---|---|---|---|---|---|
| G1 어휘 닫힘 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G2 후렴 정체성 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a |
| G3 회차마다 새 축(5회차까지) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a |
| G4 피날레 새 축 + 여유 | PASS | PASS | n/a | PASS | PASS | PASS | PASS | n/a |
| G5 헤드룸 경고 0 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G6 컬러: 유보색 조기 0 · 브리지 위반 0 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| G7 후렴 주색 동일 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G8 후렴 앞 빌드업 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G9 트래킹: Block·Release·누출 0 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G10 상대 감소 겹침 없음 | n/a | PASS | n/a | PASS | PASS | PASS | PASS | PASS |
| G11 타이밍 전 큐 배정 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G12 MIB: 켜진 채 이동 0 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| G13 큐 밀도 10~45 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

집계: PASS 90 · n/a 6 · FAIL 8 (104칸)

구 기준선 98 은 프로토타입 G6 식 반전(final_integrated.py:169 — REQ-029 면제 조건을 위반으로 셈)으로 과대, 정정값 90.

## G6 세부(실제 위반)

- Club Diver.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 6)
- Cut and Run.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 12)
- Ice cream.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 3)
- Morning.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 3)
- Rain.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 5)
- Too Cool.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 7)
- scott-buckley-neon.mp3: 유보색 pass(위반 0) · 브리지 fail(위반 6)
- 걸그룹DinoDino_C_max최고품질.wav: 유보색 pass(위반 0) · 브리지 fail(위반 2)
