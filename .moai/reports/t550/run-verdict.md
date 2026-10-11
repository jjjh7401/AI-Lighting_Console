# t550 run 판정 — detect_beat_grid 를 박 회귀 BPM 으로 맞추기

- 기준 트리: `WT-beatgrid-regression` @ origin/main `af00ffb2` (fetch 뒤 `git rev-list --count --left-right origin/main...HEAD` → `0 0`)
- 날짜: 2026-10-11

## 무엇을 바꿨나

`server/audio/bar_map.py` 의 `detect_beat_grid` 가 BPM 을 박 간격 **중앙값**(`_tempo_from_beats`)으로 내던 것을 `analyze()` 와 같은 **박 회귀**(`_tempo_from_beat_regression`)로 바꿨다. 한 줄이다. 절반/두 배 검사(`_check_bpm_half_double`)는 t547 이후 박 시각과 온셋 강도만으로 판정하고, BPM 숫자는 결과를 2배 또는 ½배 할 때만 쓴다. 그래서 판정 자체는 바뀌지 않는다(아래 10곡 표로 확인).

## RED → GREEN

재현 시험: `server/tests/test_audio_tempo_t546.py::TestOneTempoPath::test_both_paths_report_the_regressed_tempo_of_a_click_track[112.0|128.5|160.0]`. 참 BPM 을 아는 클릭 트랙 WAV 를 `analyze()` 와 `detect_beat_grid()` 에 똑같이 넣는다.

RED(고치기 전, 증거 `red_full.txt`):

```
$ uv run pytest server/tests/test_audio_tempo_t546.py -q
E         Obtained: 112.34714673913038
E         Obtained: 129.1992187499999
E         Obtained: 161.49902343749977
3 failed, 12 passed in 1.72s
```

세 값 모두 참값에서 hop 격자 한 칸(44.1kHz 에서 11.6ms) 어긋나 있다. 디코드 문제가 아니라 중앙값 양자화가 원인이라는 것과 들어맞는다.

GREEN(증거 `green_tempo.txt`, `green.txt`):

```
$ uv run pytest server/tests/test_audio_tempo_t546.py -q
15 passed in 1.65s
$ uv run pytest <오디오·박 격자·bar_map 관련 시험 17개 파일> -q -rs -p no:cacheprovider
462 passed, 1 warning in 42.95s      # skipped 0 — 로컬 전용 실곡 시험도 돌았다
$ uv run ruff check --no-cache server/audio <시험 2개>   → All checks passed!
$ uv run ruff format --check --no-cache …                 → 6 files already formatted
```

## 112.347 을 박은 기록 — 줄마다 판단

| 자리 | 의미 | 처리 |
|---|---|---|
| `test_audio_tempo_t546.py` `TestTwoPathsSplit` | 두 경로가 갈려 있다는 사실을 고정 | **고침** → `TestOneTempoPath`. 두 경로가 같은 값을 낸다는 시험. 중앙값 함수 자체가 112.347 을 낸다는 단언은 회귀를 쓰는 이유의 기록으로 남김 |
| `fixtures/love_attack_beat_grid.json` `bpm` | `detect_beat_grid` 실측값 고정 | **고침** 112.347 → 112.00191993244025(실측). 박 시각 326개 최대 차이 **0ms**, 확신 0.9673… 그대로. `_source_note` 에 경위 추가 |
| `test_audio_bar_map.py:500` 픽스처 BPM 단언 | 픽스처가 detect 출력과 같은지 확인 | **고침** → 112.002 ±0.01 |
| `test_audio_bar_map.py:563` 실곡 회귀 `112.35 rel=0.005` | detect 가 픽스처를 재현하는지 확인 | **고침** → `fixture["bpm"]` ±0.01. ±0.5% 는 112.347 과 112.002 를 둘 다 통과시켜 어느 경로인지 가리지 못했다 |
| `test_audio_bar_map.py:457` ac004c `112.35 rel=0.005` | acceptance.md AC-LDBARMAP-004c 문면(정답 112.35) | **유지**. 이미 회귀 BPM 을 넣는 시험이고 통과한다. 정답값 문면은 SPEC 몫이라 손대지 않았다 |
| `test_audio_bar_map.py:170` `60/112.35` | 부록 A 손 측정 간격으로 `derive_bars` 를 재현 | **유지**. detect 경로와 무관 |
| `test_audio_bar_map_store.py`·`test_session_bar_map_store.py` `bpm=112.35` | 저장 페이로드에 넣는 임의 BPM | **유지**. 어느 경로의 측정값도 아니다 |
| `analyze.py` `_tempo_from_beats` 독스트링 | "bar_map 때문에 남긴다" | **고침**. 이제 회귀의 출발점과 확신 계산으로 남는다 |
| `tools/barmap/*`(`candidates.py`·`ground_truth.py` TARGET_BPM) | M1 보정 도구 | **손대지 않음**. server/audio 밖이다. 생산 경로가 아니다 |

## 10곡 반/두배 재측정 — 생산 함수 `detect_beat_grid` 를 그대로 호출

명령: `uv run python .moai/reports/t550/songs_after.py` (출력 `songs_after.txt`). 비교 기준은 `.moai/reports/t547/after_songs.txt` 의 outcome@reg·adopt@reg 열이다.

| 곡 | t550 raw=adopted | 판정 | 모호 | t547 adopt@reg | 같음 |
|---|---|---|---|---|---|
| LOVE ATTACK | 112.002 | keep | False | 112.002 keep | ✓ |
| Club Diver | 140.026 | keep | False | 140.026 keep | ✓ |
| Cut and Run | 107.666 | keep | False | 107.666 keep | ✓ |
| Ice cream | 100.446 | keep | False | 100.446 keep | ✓ |
| Let's Dance | 120.030 | keep | False | 120.030 keep | ✓ |
| LoveMe | 🔴 **읽기 실패**(아래) | — | — | 99.994 keep | 경로 읽기로만 ✓ |
| Morning | 117.454 | keep | False | 117.454 keep | ✓ |
| Rain | 76.013 | keep | False | 76.013 keep | ✓ |
| Too Cool | 160.003 | keep | False | 160.003 keep | ✓ |
| scott-buckley-neon | 120.185 | keep | False | 120.185 keep | ✓ |

**결론: `detect_beat_grid` 로 잰 9곡이 모두 keep 이고, BPM 은 t547 의 회귀 열과 소수 셋째 자리까지 같다.** 거짓 두 배는 0곡이다. 이 변경에서 새로 넣은 문턱은 없다.

### 🔴 LoveMe — 이 변경과 무관한 기존 결함(카드 필요)

`detect_beat_grid(bytes)` 가 `Format not recognised` 로 실패한다. 원인은 디코드다. `soundfile` 이 이 mp3 를 **경로로는 읽고 BytesIO 로는 못 읽는다**(`loveme.txt`):

```
path  (4766976, 2)
bytes ERR Error opening <_io.BytesIO …>: Format not recognised.
analyze(bytes): None 오디오 형식을 읽지 못했습니다: … Format not recognised.
```

이 변경 이전부터 있던 결함이다. 근거는 두 가지다.
- 같은 디코드를 쓰는 `analyze()`(이 PR 에서 디코드 코드를 바꾸지 않음)도 같은 오류를 낸다.
- `git diff origin/main -- server/audio/bar_map.py | grep -c _decode_mono_audio` → `0`.

t547 스크립트는 파일 경로로 읽었기 때문에 이 결함을 만나지 않았다. 경로로 읽어 같은 함수로 계산하면 raw=adopted=99.994, keep, p_mid=7.02e-28 이다. 즉 업로드 경로(바이트열)에서는 이 곡을 분석할 수 없다. 리드에게 카드 생성을 요청한다.

## 안 잰 것

- 템포가 곡 중간에 바뀌는 곡. t546 의 한계가 그대로 남는다(잔차가 크면 중앙값으로 돌아간다).
- LoveMe 의 BytesIO 디코드 실패 원인. ID3 태그 크기인지 libsndfile 버전인지 재지 않았다.
- 전체 시험 스위트. 관련 17개 파일만 돌렸고, 전체는 CI 에 맡긴다.
- 실기 콘솔. 콘솔 쓰기는 0이다.
