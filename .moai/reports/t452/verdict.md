# t452 판정서 — 컨셉 파이프라인 `reduce ref` 실패

- 카드: t452 (클래스 B — 원인 미확정 결함)
- 브랜치: `WT-reduce-ref-short` · 기준 `origin/main` `dacba149`
- 콘솔 쓰기: 0건 (가짜 실행·상태 포트, 순수 계산 경로만 사용)

## 1. main에서 재현되는가 — 재현됨

명령:

```
.venv/bin/python .moai/reports/t452/repro.py > .moai/reports/t452/repro_main.txt
```

출력(`repro_main.txt`, 수정 전 `dacba149`):

```
records_absent is_error= False
  concept_report= {"available": false, "reason": "컨셉 파이프라인 실패: reduce: ref 'song_release_reference' 가 bases 에 없음(REQ-021)"}
records_present is_error= False
  concept_report= {"available": false, "reason": "컨셉 파이프라인 실패: reduce: ref 'song_release_reference' 가 bases 에 없음(REQ-021)"}
```

곡: t441 `_RAW_SECTIONS_B`(Intro 0:00 · Chorus 0:04 · Verse 0:08 · Drop 0:12 · Chorus 0:16, 120 BPM). 감독 기록 유무와 상관없이 같은 실패가 난다. t444 판정서 78행이 "main에서도 같은지는 재지 않았다"고 남긴 공백을 이번에 쟀다.

## 2. 원인 — REQ-021 "ref가 있으면 ref" 갈래

REQ-021의 세 갈래 중 **첫째 갈래**다. ref가 주어졌는데 `bases`에 없으면 조용히 폴백하지 않고 거절하는 규칙이며, 거절 자체는 규칙대로 맞게 동작했다. 결함은 기준 이름을 붙이는 위치에 있다.

단계 분리(`trace_stage.txt`): `build_song` OK · `compile_song` OK · **`evaluate_song` FAIL** — 스택은 `g9_tracking_block_release_leak` → `verify_no_cue_only_leak` → 두 번째 `resolve_sequence` → `reduce`에서 끝난다.

행 추적(`trace_rows.txt`):

```
row7 kind=phrase section=Chorus occ=2 base_name=song_release_reference ops=['add'] refs=[]
row8 kind=safety section=Outro occ=0 base_name=None ops=['reduce'] refs=['song_release_reference']
```

- `gates.py`가 기준 이름 `song_release_reference`를 **마지막 시퀀스 행**에 붙인다.
- 이 곡은 마지막 행이 프레이즈 큐(`tracking="cue_only"`)다. 구간이 짧고 마지막 Chorus 뒤 꼬리가 15초라 프레이즈 행이 맨 끝에 온다.
- G9 누출 검사는 `cue_only` 행을 **빼고** 한 번 더 해석한다. 이때 기준 이름을 달고 있던 행이 같이 빠지고, 마지막 안전 큐의 `reduce ref`가 가리킬 대상이 없어진다.

이것이 증상이 아니라 원인이라는 근거: 첫 해석(`build_song`)은 같은 행으로 성공했고, 실패는 `cue_only`를 거른 두 번째 해석에서만 난다. 기준 이름의 위치를 track 행으로 옮기자 두 해석이 모두 통과했다(아래 4절).

## 3. 운영 경로 영향 — 콘솔 무영향 확인

`session_bridge._run_concept_pipeline`이 예외를 삼켜 `available: False`로 내린다. 위 재현에서 `prepare_songcue` 툴 호출 결과는 `is_error=False`였다. 기존 시험 `test_songcue_concept_report_wiring.py`도 이 실패 상태에서 `Store Sequence` 명령이 나간다는 것을 고정해 두었다. 콘솔 명령은 영향이 없고, 사라지는 것은 부가 리포트(13게이트)뿐이다.

## 4. 수정 — 최소 한 곳

`server/concept/gates.py` `build_song`: 기준 이름을 "마지막 시퀀스 행" 대신 **마지막의 `cue_only`가 아닌 행**에 붙인다. `cue_only` 행이 없으면 예전처럼 마지막 행을 쓴다. 다음 큐로 이어지는 상태(carry)가 바로 그 track 행의 상태이므로 의미도 맞다.

## 5. 검증

| 항목 | 명령 | 결과 |
|---|---|---|
| RED (수정 전) | `pytest server/tests/test_concept_release_ref_t452.py` | `4 failed, 1 passed` (`pytest_red.txt`) — 통과한 1건은 "마지막 행이 cue_only" 전제 확인 |
| GREEN (수정 후) | 같은 명령 | `5 passed` (`pytest_green.txt`) |
| 관련 범위 | `pytest test_concept_*.py test_chorus_color_*.py test_song_timeline_concept_report_wiring.py test_songcue_concept_report_wiring.py` | `486 passed` (`pytest_scoped.txt`) |
| 기존 8곡 불변 | `.venv/bin/python .moai/reports/t452/pilot_invariance.py` | 같은 행을 고른 곡 **8/8**, 8곡 모두 마지막 행이 `track` (`pilot_invariance_after.txt`) |
| 린트 | `ruff check` / `ruff format --check` (변경 파일 전부) | 통과 (`ruff_check.txt`) |

8곡 불변의 의미: 기존 곡들은 수정 전과 후 규칙이 같은 행을 골랐으므로 해석기 입력이 바이트 단위로 같다. 따라서 기존 게이트 기준선은 구조적으로 바뀌지 않는다.

## 6. 기존 시험 3건을 고친 이유

이 결함은 t439 때 발견됐고, 그때 "gates.py는 이 카드의 수정 대상이 아니다"라며 **현재 동작을 그대로 고정**해 두었다.

- `test_concept_session_bridge.py` — 결함을 고정하던 시험이다. `available is False`를 `available is True` + G9 통과로 뒤집었다(클래스 이름 `...IsCaughtNotRaised` → `...IsJudged`).
- `test_song_timeline_concept_report_wiring.py`, `test_songcue_concept_report_wiring.py` — 의도는 "리포트가 실패해도 페이로드·콘솔 명령은 멀쩡하다"이다. 이 결함을 실패 유발원으로 빌려 썼을 뿐이므로, 의도는 두고 실패를 `build_song` 바꿔치기(기존 `TestConceptPipelineFailureIsSwallowed`와 같은 방식)로 일으키게 바꿨다.
- `test_concept_color_input_t444.py` — 이제 사실이 아닌 주석 한 줄을 과거형으로 고쳤다.

## 7. 안 잰 것 (Gaps)

- 전체 시험 묶음은 로컬에서 돌리지 않았다. 레인 규칙에 따라 CI에 맡긴다.
- 실기 콘솔: 0회. 이번 수정은 순수 계산 경로다.
- 수정 전 규칙과 후 규칙이 **다른 행**을 고르는 곡은 이번 결함을 겪던 곡뿐이다. 그런 곡에서 기준 행이 `occurrence == 1`인 구간 행이 되면, `resolve_sequence`가 그 행의 자동 구간 기준(`<구간> 1`) 등록을 건너뛴다(명시적 `base_name`이 있으면 `elif`로 넘어간다). 이 성질은 수정 전에도 마지막 행이 track일 때 똑같이 있었던 기존 동작이다. 이번 재현 곡에서는 기준 행이 Chorus 2회차라 해당하지 않는다.

## 8. 잔여 위험

- 이 곡들의 13게이트 **판정값**은 이번에 처음 나온다. 그 값이 연출상 맞는지는 이 카드의 범위가 아니다. G9 통과 여부만 시험으로 고정했다.
