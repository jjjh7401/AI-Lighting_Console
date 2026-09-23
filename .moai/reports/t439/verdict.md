# t439 판정 — SPEC-LDDESIGN-001 M6 기존 하류 브리지 + 8곡 게이트 고정 (REQ-073~077, REQ-004)

- 레인: lane-3 · 워크트리 `.claude/worktrees/t439` · 브랜치 `WT-concept-bridge-gates`
- 기준: `origin/main@bb47bab4`에서 출발, 도중에 `origin/main@fbc3c838`을 합류(`f23f8fd0`)
- 판정: **PASS(범위 한정)** — 8곡 13게이트 정정 기준선 90/6/8을 재현하고 고정했다. 남은 FAIL 8칸은 모두 G6 실제 위반이다(카드 t444).

## 산출물

| 파일 | 내용 |
|---|---|
| `server/concept/escalation.py` | `remaining_motion_before_final` — G4 「남은 모션」을 피날레 전까지 쓴 최대 모션으로 계산 |
| `server/concept/gates.py` | 8곡 곡 파이프라인 + 13게이트 어댑터. 게이트는 기존 `server/concept/*` 함수를 부른다. `evaluate_song(color_usage=)` |
| `server/concept/density.py` | Intro 분기를 프로토타입대로 복원(KEY 10% · BACK 25% · 보컬 시작 4마디 전 35%). 무버 재배치 조건 로직(배선 안 함) |
| `server/concept/compile.py` | 컨셉 v2 → 콘솔 명령 컴파일. `lint.lint_sheet` · `energy.axis_budget` · `timing.emit_fade`(→`cue_fade.store_with_fade`)를 직접 호출 |
| `server/concept/session_bridge.py` | 두 입구용 `concept_report` 어댑터. 예외를 밖으로 내지 않는다 |
| `server/web/session.py` | `_arc_palette` 후렴 회차 색 고정(기본 모드). `per_chorus`는 예외. `_song_timeline_payload`에 `concept_report` 부가 |
| `server/orchestrator/tools.py` | `prepare_songcue`에 `concept_report` 부가 |
| `server/tests/fixtures/pilot_baseline.json` | `.claude/worktrees/pilot-labeling/pilot_baseline.json` 사본(`cmp` 동일). 원본은 보존했다 |
| 시험 | `test_concept_gates.py`(신규) 외 신규 5파일, 기존 4파일 수정 |
| `.moai/specs/SPEC-LDDESIGN-001/spec.md` | REQ-004·REQ-030 예외 구절 한 개씩 + HISTORY 한 줄(감독 결정 인용) |

## 레인이 직접 잰 것

1. **기준선 재현.** `python3 .moai/state/verify/f12e5c95-t429/final_integrated.py .moai/reports/t439/baseline` 실행 → PASS 98 · n/a 6 · FAIL 0 (`baseline/final_integrated.txt`). 셀 단위는 13게이트 × 8곡 = 104칸이다.
2. **구 기준선 98은 과대, 정정값은 90.** 프로토타입 G6 식(`final_integrated.py:169`)은 색이 다르고 **켜진 그룹이 안 겹칠 때만** 위반으로 센다. 이건 REQ-029가 면제하는 경우를 뒤집은 것이다. 같은 json을 REQ-029 식(색이 다르고 그룹이 겹침)으로 다시 세면 8곡 모두 곡당 2~12건 위반이 나온다. 그래서 G6 8칸은 거짓 PASS였다.
3. **최종 실측.** `uv run python .moai/reports/t439/gen_gates_final.py` → `{'PASS': 90, 'n/a': 6, 'FAIL': 8}` (`gates_final.md`). `test_concept_gates.py`가 이 행렬을 곡 × 게이트 단위로 고정한다.
4. **G4 새 정의.** 프로토타입 json으로 다시 계산했다. 적용 대상 6곡 모두 남은 모션이 1이라 PASS다. Morning과 Rain은 옛 정의(직전 행이 Pre-Chorus라 남은 모션 3)에서 잘못된 이유로 PASS였다.
5. **G5(scott-buckley-neon)는 원인이 둘이었다.** (가) t437에서 Intro 분기를 옮길 때 일부가 빠졌다. 이건 복원했다. (나) 어댑터가 Bridge를 비교할 대상을 구간 큐로만 골라서 Intro 끝의 "보컬 시작" 프레이즈(4그룹 35%)를 빠뜨렸다. 프로토타입 `_prev_nb`는 전체 행을 본다. (나)의 RED(1 failed)를 먼저 확인한 뒤 고쳤다. 다른 7곡의 G5는 바뀌지 않았다.
6. **변이 시험.** 결함을 심어서 돌린 뒤 되돌렸다(`mutation/`).

| 심은 결함 | 결과 |
|---|---|
| G4를 직전 한 행 기준으로 되돌림 | 6 failed |
| `compile_song`이 `lint_sheet`를 안 부름 | 10 failed |
| G5 비교 대상을 구간 큐로만 되돌림 | 1 failed |
| `per_chorus` 회차 고정 재도입(RED 단계) | 3 failed |

7. **시험.** `uv run pytest server/tests -k "palette or color or songcue or song_cue or arc or concept" -q` → `1159 passed, 4 skipped`, exit 0 (`pytest_per_chorus_exception.txt`). ruff check와 format은 바꾼 파일에서 통과했다. 전체 스위트는 ③④b 에이전트가 1회 돌려 `14166 passed, 35 skipped`를 얻었다(`pytest_full_suite.txt`, `a9bfae9e` 이전 기준). 최종 전체는 CI에 맡긴다.

## REQ별 판정

| REQ | 판정 | 근거 |
|---|---|---|
| 073 기존 하류 재사용 | PASS | `compile.py:193` `lint_sheet`, `:199` `axis_budget`, `:203` `emit_fade`→`cue_fade`. 스파이 시험과 변이 시험 |
| 074 기존 저장·승인 흐름 | 부분 | 방출한 `Store Sequence … Cue …` 줄이 기존 `session._SONG_STORE_CUE` 리드백 정규식을 그대로 통과한다. 전체 승인 payload는 재구성하지 않았다 |
| 075 13게이트 고정 | PASS | `test_concept_gates.py`, 정정 기준선 90/6/8 |
| 076 악화 시 보류·기록 | PASS | 새 FAIL은 전부 원인을 밝혔다. G6은 거짓 PASS 교정, G5는 이식 누락 교정 |
| 077 songcue 사다리 흡수 | 이관 | 리드 결정으로 카드 t441 몫 |
| 004 / 030 후렴 색 | PASS(기본값) | 기본 modulate: 후렴 6회 모두 (블루, warm white). 경로 B: 6회 모두 같은 Look(edm-drop-crimson). `per_chorus`는 감독 결정에 따른 예외라 회전하고 G7은 n/a |

### 감독 결정(2026-09-23) — 곡별 색 운용

「음악 스타일마다 다르니 하나로 고정은 무리」에 따라 이렇게 적용했다.

- **기본(modulate):** 후렴 회차 색을 고정한다.
- **`per_chorus`(Q2B):** 회차마다 색을 바꾸는 원래 동작을 되살렸다. t404 시험 파일은 t439 이전 원본으로 복원했다.
- **분할 큐 주·보조색 맞바꾸기(`session.py` 약 2113행):** 현행을 유지했다. t305 시험은 바꾸지 않았다. 정식화는 카드 t445 몫이다.

### 경로 간 동일은 t441

같은 곡이라도 경로 A는 블루, 경로 B는 크림슨을 낸다. 경로 B가 감독 팔레트를 읽지 않고 버스킹 룩 라이브러리의 RGB를 쓰기 때문이다. 이건 REQ-003(단일 컴포저) 문제라서 카드 t441의 합격 조건으로 넘긴다. 이 카드는 각 경로 안에서 후렴 회차 색이 같은지까지만 본다. 표는 `chorus_color_two_paths.md`에 있다.

### 다시 쓴 기존 시험

| 파일 | 바꾼 것 | 사유 |
|---|---|---|
| `test_song_palette_occurrence_t402.py` | 후렴 회차 색이 "달라야 한다"를 "같아야 한다"로 | REQ-004/030 기본값 |
| `test_song_color_usage_t404.py` | 최종 변경 없음. t439 이전 원본으로 복원 | 감독 결정으로 `per_chorus` 회전 유지 |
| `test_concept_escalation.py` | Rain 통합 시험의 남은 모션 계산을 새 헬퍼로 | G4 재정의(REQ-044/048) |
| `test_concept_density.py` | Intro 프로토타입 이식 시험 추가 | t437 이식 누락 복원 |

### M5에서 넘어온 판단 3건

- **safety factor=0:** 안전하다. `resolver.py:114`가 참조한 base의 모든 키에 0을 명시적으로 쓰고, 하류 소비처는 모두 `값 > 0`으로 판정한다. 회귀 시험을 추가했다.
- **REQ-058 매핑(변경 없음, 감독 보고용):** snap 0.2초 = 드롭 직전의 정적 / short 1.5초 = 악기 추가·제거, 보컬 시작·종료, 빌드업 시작 / long 3.0초 = 코드·조성 변화, 핵심 가사, 안무 대형 변화, 중심 멤버·솔로 변경, Outro / 그 밖은 short.
- **movers_off 조건:** 로직과 단위 시험 7건만 넣고 조립기에는 배선하지 않았다(리드 결정 (a)). 배선하면 AC-LDDESIGN-010 잠금 시험(Too Cool 절1 밝기 45%)이 깨진다. 소등하지 않을 때 무버 밝기를 얼마로 둘지는 감독 결정이 필요하다.

## 범위 밖 — 카드로 넘긴 것

1. **무버 재배치 조건 조립기 배선.** 소등하지 않을 때의 무버 밝기를 감독이 정해야 한다. 카드 번호는 리드가 대조한다.
2. **g9 누출 검사 VocabError.** Outro 없이 `cue_only` 프레이즈로 끝나는 곡에서 `gates.py`의 g9 재해석이 release 기준 행을 빼버려 `VocabError`가 난다. 8곡은 모두 Outro로 끝나서 걸리지 않는다. bridge는 `available: false`로 내려가서 콘솔 경로에는 영향이 없다. 카드 번호는 리드가 대조한다.
3. **G6 주색+보조색 방출.** 카드 t444.
4. **REQ-003·077 구조 통합과 경로 간 색 동일.** 카드 t441.
5. **곡별 스위치 정식화.** 카드 t445.

## 안 잰 것

- 실기 grandMA3 콘솔에는 한 번도 쏘지 않았다. 순수 계산 경로만 확인했다.
- REQ-074는 리드백 정규식 통과까지만 확인했다. 승인 UI를 통한 종단 확인은 하지 않았다.
- `compile.py`의 D-레벨은 밝기에서 역산한 값이다. D5(정확히 100%)는 도달할 수 없고 D4로 떨어진다.
- 바뀐 파일에 mypy나 pyright 같은 타입 검사기는 돌리지 않았다.
- 최종 커밋(`a9bfae9e`) 기준 전체 스위트는 로컬에서 돌리지 않았다. CI 결과로 확인한다.
