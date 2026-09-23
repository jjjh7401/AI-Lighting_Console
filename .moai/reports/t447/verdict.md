# t447 판정서 — Outro 없이 끝나는 곡의 G9 누출 검사 VocabError

- 카드: t447 (클래스 B)
- 브랜치: `WT-g9-no-outro`, 기준 `origin/main` 36da2f92(PR #500 머지 후)
- 콘솔 쓰기: 0
- 결론: **t452(PR #500, 7b3bcc6c)로 해소됨.** 이 PR 은 코드 수정 0이고, 회귀 방지 시험과 이 판정서만 넣는다.

## 1. 주장

곡이 Outro 없이 후렴(cue_only 「악기 추가」 프레이즈)으로 끝나면, G9 누출 검사(`verify_no_cue_only_leak`)가
멈췄다. 이 검사는 cue_only 행을 빼고 한 번 더 해석하는데, 곡 끝 안전 큐의 Release 기준 이름
(`song_release_reference`)이 그 cue_only 행에 붙어 있어서 같이 사라졌다. 그 결과 `reduce` 가
`VocabError` 로 거절됐다.

- 어긋난 가정: REQ-069(마지막 큐가 기준 상태를 reduce 로 되돌린다)의 기준을 「마지막 시퀀스 행」에
  붙이면서, 그 행이 REQ-057(cue_only는 다음 큐로 이어지지 않음)의 cue_only 일 수 있다는 점을 보지 않았다.
- 수정은 lane-3 의 t452(PR #500)가 먼저 머지했다. `gates.py` 가 기준 이름을 마지막 **track 행**에
  붙인다. 이 카드에서 세운 수정안과 같은 방식이다(리드가 같은 뿌리로 판단해 이 카드의 코드 수정을 멈췄다).

## 2. 증거

### 2.1 재현 시험 — `server/tests/test_concept_g9_no_outro_t447.py`

샘플 8곡(`fixtures/pilot_baseline.json`)의 마지막 구간을 빼면 후렴으로 끝나는 6곡(Club Diver·Cut and
Run·Ice cream·Morning·Rain·scott-buckley-neon)이 대상이다. 시험은 두 가지다. 전제 시험은 마지막 시퀀스
행이 정말 cue_only 인지 확인한다. G9 시험은 G9 가 판정을 내고 passed=True 인지 확인한다.

| 트리 | 명령 | 결과 |
|---|---|---|
| 187f6061 (`gates.py` 만 되돌림) | `uv run pytest -q server/tests/test_concept_g9_no_outro_t447.py` | **6 failed, 6 passed** — G9 6건 모두 `VocabError: reduce: ref 'song_release_reference' 가 bases 에 없음(REQ-021)` (`red_at_187f6061.txt`) |
| 36da2f92 | 같은 명령 | **12 passed** (`green_at_36da2f92.txt`) |

187f6061 과 36da2f92 사이에서 바뀐 운영 코드는 `server/concept/gates.py` 한 곳뿐이다
(`git diff --stat 187f6061 36da2f92 -- server ':!server/tests'` → 1 file, +13 −1). 그래서 187f6061 측정은
그 파일 하나만 되돌려 쟀고, 잰 뒤 다시 되살렸다.

### 2.2 8곡 기준선 불변 — `baseline.py`

| | 187f6061 (`baseline_before.txt`) | 36da2f92 (`baseline_after.txt`) |
|---|---|---|
| 8곡 게이트 합계 | PASS 75 / n·a 29 / FAIL 0 | PASS 75 / n·a 29 / FAIL 0 |
| 곡별 `table`+`rows` 지문 | 8곡 | 8곡 모두 같음 |
| 마지막 구간을 뺀 변형 | 6곡 VocabError, 2곡 G9 True | 8곡 모두 G9 True |

`diff baseline_before.txt baseline_after.txt` 는 「마지막 구간을 뺀 변형」 6줄만 다르다.
8곡 모두 기준 이름은 예전처럼 마지막 Outro(track) 행에 붙어 있다(실측: owner = 마지막 시퀀스 행).

**측정 방법 정정:** 처음 지문은 `repr()` 로 떴고, 8곡 모두 달라진 것처럼 나왔다. 같은 트리에서 두 번
실행해도 지문이 달랐다. 원인은 행의 `layers` 가 `frozenset` 이라 실행마다 반복 순서가 바뀌는
것(해시 무작위화)이었다. 그래서 정렬된 JSON 지문으로 바꿨다. 같은 트리 2회 실행 결과가 같은 것을
먼저 확인했다(`baseline_after.txt` = `baseline_after_run2.txt`). 그다음 두 커밋을 비교했다.

### 2.3 콘솔 경로 무영향 재확인

`server/concept/session_bridge.py` `_run_concept_pipeline` 은 예외를 잡아
`{"available": False, "reason": "컨셉 파이프라인 실패: …"}` 로 돌려준다(157~165행). 그래서 수정 전에도 이
결함은 컨셉 리포트가 사라지는 데서 그쳤고, 콘솔로 가는 번들에는 닿지 않았다. 이 확인은 코드 판독이고,
세션으로 태워 보지는 않았다.

## 3. 미검증

- 실제 곡 중 Outro 없이 끝나는 곡을 앱 분석 경로로 태운 적은 없다(샘플 8곡은 전부 Outro 로 끝난다). 재현은 합성 변형(마지막 구간 제거)으로만 했다.
- cue_only 행만으로 이뤄진 곡(track 행이 하나도 없는 곡)은 `owner` 가 마지막 행으로 돌아간다(t452 코드의 기본값). compile_density 구조상 각 구간은 section(track) 행을 먼저 내므로 이런 곡은 생기지 않는다고 보지만, 따로 쏘지는 않았다.

## 4. 판정

t447 은 PR #500 으로 해소됐다. 187f6061 에서 6 failed, 36da2f92 에서 12 passed이고, 8곡 기준선
75/29/0 과 지문 8/8 이 같다. 재현 시험은 회귀 방지용으로 남긴다.
