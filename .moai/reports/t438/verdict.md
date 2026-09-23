# t438 — SPEC-LDDESIGN-001 M5 판정 (lane-3)

- 브랜치: `WT-concept-tracking-mib` · 기준 `origin/main@06e3d125` → `origin/main@a54db70e`(M3 t436) 합류
- 구현: `manager-develop`(sonnet), TDD. RED `d69eb4b2` → GREEN `dc0b9e93` → progress `9da92b73`
- 스펙 정정: `8b4541b3` (REQ-062 문장, 리드 승인 범위 한 줄 + HISTORY 한 줄)
- 작성: 2026-09-23

## 1. 판정

**M5 모듈 구현 PASS — 단, 곡 조립 경로에는 아직 연결되지 않았다.** 트래킹·타이밍·MIB·안전 큐·근거 등급은 순수 계산 함수로 들어갔다. 이 함수들을 부르는 곡 단위 조립기는 M6 몫이다. 따라서 "8곡" 인수 조건(AC-009/011/012/026)은 픽스처로만 확인했다.

## 2. REQ별 상태

| REQ | 상태 | 위치 |
|---|---|---|
| 053~056 트래킹 기본값 | 구현 | `server/concept/tracking.py` `default_tracking` |
| 057 Cue Only 비전파 | 구현(M2 해석기 재사용) + 속성 검사기 | `tracking.verify_no_cue_only_leak` |
| 058 타이밍 기본값 | 구현 — 트리거→종류 대응은 판단값(아래 §4) | `server/concept/timing.py` `default_timing` |
| 059·060 후렴 진입 snap+stagger+색/밝기 분리 | 구현(데이터만) | `timing.chorus_entry_timing` |
| 061 페이드 방출 재사용 | 구현 — `store_with_fade`에 위임 | `timing.emit_fade` |
| 062 MIB 판정 | M2 `resolver.mib_verdict` 재사용, 시퀀스 순회 추가 | `server/concept/mib.py` `compute_mib_sequence` |
| 063 Mark 큐 | 구현 — mark 판정마다 1건 | `mib.mark_cue_spec` |
| 064 절·브릿지 무버 소등 | 구현(동작 목록 생성) | `mib.movers_off_ops` |
| 065 어두운 창 없으면 포지션 유지 | 구현 | `mib.resolve_position` |
| 066 live_move 표시+대안 | 구현 | `mib.live_move_note` |
| 067 director mib.py 미import | 구현 + AST 검사 | `server/tests/test_concept_no_director_import.py` |
| 068·069 안전 큐 | 구현(큐 스펙 생성, `apply()` 통과) | `server/concept/safety.py` |
| 070 description | 기존 M2 `describe()` 재사용, 시험만 추가 | `server/tests/test_concept_safety.py` 등 |
| 071·072 근거 등급 설명·[공개 근거 없음] | 데이터 쪽만 구현. 화면 노출은 M7 | `server/concept/evidence.py` |

MIB 잠정값(1.5초 + 0.5초)은 `server/concept/resolver.py`의 `MOVE_SECONDS`/`SETTLE_SECONDS` 한 곳에만 있다. `mib.py`에서 이 값을 다시 적으면 시험이 실패한다.

## 3. 증거 (lane-3이 직접 다시 잰 값)

| 주장 | 명령 | 관측 |
|---|---|---|
| concept 시험 (M5만, 06e3d125 기준) | `uv run pytest -q server/tests/test_concept_*.py` | `202 passed in 0.25s` |
| concept 시험 (M3 합류 후) | 같은 명령 | `240 passed in 0.27s` |
| 전체 시험 (합류 후) | `uv run pytest -q -x` | `13971 passed, 35 skipped, 1 warning in 190.68s` |
| 린트 | `uv run ruff check server/concept server/tests/test_concept_*.py` | `All checks passed!` |
| 포맷 | `uv run ruff format --check …` | `20 files already formatted` |
| director import 금지 (REQ-067) | `grep -rlnE '^(from\|import) server\.director' server/concept` | 0 |
| 금지 파일 무변경 | `git diff --stat 06e3d125..9da92b73` | resolver·cue_model·description·vocab·worksheet·__init__ 변경 0. 신규 파일 11개와 progress.md, spec.md(정정분)만 바뀜 |
| 가드 판별력 (에이전트 보고 — lane-3이 다시 재지 않음) | cue_only 전파 줄 파손 / mib.py에 상수 재선언 | 각각 3건·1건 FAIL → 복구 |

## 4. 안 잰 것 (Gaps)

- **8곡 게이트 미측정.** AC-009/011/012/026은 곡 조립기(M6)가 있어야 8곡에 대고 잴 수 있다. 지금은 픽스처 기준이다.
- **REQ-058 트리거 대응은 판단값이다.** 스펙은 "드롭·히트·백색 플래시=snap, 프레이즈 전환=short, 발라드 확장·아웃트로=long"이라고만 적었다. 이를 10종 트리거 어휘에 옮긴 대응은 에이전트가 정했다(`timing.py` 독스트링에 기록). 감독 또는 리드의 확인이 필요하다. 트리거가 없는 큐는 short로 처리한다.
- **REQ-064는 조건 판정을 호출자에게 넘긴다.** `movers_off_ops`는 절이나 브릿지 구간이면 무조건 소등 동작을 낸다. "다음 후렴을 위해 포지션을 바꿔야 할 때만"이라는 조건은 M6 조립기가 판단해야 한다.
- **`resolve_position`은 mark를 내지 못한다**(dim을 바꾸지 않는 프로브라서). mark가 필요한 자리는 `compute_mib_sequence`를 쓴다. 독스트링에 적혀 있다.
- **뮤테이션 검사는 에이전트 보고를 옮긴 것이다.** lane-3이 다시 쏘지는 않았다.

## 5. 남은 위험

- `last_safety_cue`의 `reduce factor=0`은 `ref` 기준 상태에 있는 그룹만 다시 쓴다. 기준 상태에 없는 그룹은 dim 사전에서 빠져 결과적으로 0이 된다. 그래서 "모든 그룹 0"은 성립하지만, 사전 키가 사라지는 방식이라 하류가 키 유무로 판단하면 어긋날 수 있다(M6 연결 때 확인할 것).
