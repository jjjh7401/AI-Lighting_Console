# t552 run 판정 — 업로드 바이트열로 일부 mp3 를 분석하지 못하던 결함

- 기준 트리: `WT-mp3-bytes-decode` @ origin/main `f5b16963` (fetch 뒤 `git rev-list --count --left-right origin/main...HEAD` → `0 0`)
- 날짜: 2026-10-11 · 환경: libsndfile 1.2.2 · soundfile 0.14.0

## 원인 — 측정 결과

카드에 적혀 있던 가설("ID3 태그 크기? libsndfile 판별?")을 직접 쟀다. 원인은 **첫 MPEG 프레임 앞에 0 바이트가 끼어 있는 것**이다. BytesIO 자체는 원인이 아니다.

1) 같은 파일을 네 가지 방식으로 읽었다(`probe_cause.py` → `probe_cause.txt`).

```
== LoveMe.mp3 size 2594979
   ID3v2.3.0 flags=0x00 tag_size=71 audio_starts_at=81 bytes_at_end=00000000
   path .mp3: OK (4766976, 2) sr=44100
   path no-ext: ERR … Format not recognised.
   bytes: ERR … Format not recognised.
== Morning.mp3      … bytes_at_end=fffba040  path/no-ext/bytes 모두 OK
== LOVE ATTACK.mp3  … bytes_at_end=fffbb000  path/no-ext/bytes 모두 OK
```

같은 파일이라도 **경로에서 확장자만 빼면** 실패한다. 경로로 읽혔던 것은 libsndfile 이 확장자 `.mp3` 로 형식을 정하는 대체 경로 덕분이었다. 업로드 바이트열에는 확장자가 없다. 다른 두 곡은 태그 바로 뒤가 프레임 동기(`fffb…`)이고, LoveMe 는 그 자리가 `00000000` 이다.

2) 틈을 쟀다(`probe_gap.txt`).

```
tag_end 81 first_sync_at 707 gap_len 626 gap_all_zero True sync_bytes fffbb064
tag+gap stripped OK (4766976, 2)
tag kept, gap removed OK (4766976, 2)
only tag stripped ERR … Format not recognised.
```

태그 크기에 들어가지 않는 0 바이트 626개가 태그 뒤에 있다. 이 틈만 빼면 바이트열로도 읽히고, 샘플 수가 경로로 읽은 값(4766976)과 같다. 태그만 빼고 틈을 남기면 여전히 실패한다. 원인은 태그가 아니라 틈이다.

3) 합성 mp3 로 재현했다(`probe_synth.py` → `probe_synth.txt`, 원곡 없이).

```
bare: OK · id3 no gap: OK
id3 + 626 zero gap: ERR · id3 + 1 zero gap: ERR · no id3, 626 zero lead: ERR
```

0 바이트 **하나**로도 재현되고, 태그가 없어도 재현된다.

## 수정

`server/audio/analyze.py` 에 공용 디코드 `_read_audio` 를 두고, `analyze()` 와 `bar_map._decode_mono_audio` 가 둘 다 이 함수를 쓴다. 두 곳에 같은 코드가 복사돼 있었다.

- 동작은 그대로다. 단, **처음 읽기가 실패했을 때만** `_without_zero_gap_before_mp3` 로 첫 진짜 프레임(다음 프레임까지 이어지는 동기) 앞의 틈을 찾는다.
- 틈이 **전부 0** 이면 그 틈만 빼고 한 번 더 읽는다. 0 이 아닌 바이트가 섞여 있거나, 프레임이 없거나, 틈이 없으면 원래의 거절을 그대로 낸다.
- 지금 읽히는 파일은 재시도 경로를 타지 않으므로 바이트 하나 바뀌지 않는다.
- 태그 끝·첫 프레임 찾기는 `_mp3_length_is_a_bitrate_guess` 안에 있던 코드를 `_id3v2_end`·`_first_mp3_frame` 로 뽑아 함께 쓴다. 동작은 같다.
- 곡 이름·파일 상수·크기 문턱은 없다. 탐색 범위는 기존 상수 `_MP3_SYNC_SEARCH_BYTES` 를 쓴다.
- 새 의존성은 없다.

## RED → GREEN

새 시험 `server/tests/test_audio_mp3_zero_gap_t552.py` 는 합성 클릭 mp3 를 쓰고, CI 에서 돈다.

RED(고치기 전, `red_full.txt`): `6 failed, 3 passed`. 실패 6건이 모두 `Format not recognised` 다(태그+626 0 바이트 · 태그+1 · 태그 없이 626, 각각 `analyze`·`detect_beat_grid`). 통과한 3건은 대조군이다(틈 없는 파일, 0 이 아닌 쓰레기, 0 바이트만 있는 입력).

GREEN:

```
$ uv run pytest server/tests/test_audio_mp3_zero_gap_t552.py -q      → 9 passed
$ uv run pytest <오디오·박 격자·bar_map 관련 18개 파일> -q -rs      → 471 passed (skipped 0)
$ uv run ruff check / format --check --no-cache …                    → 통과
```

- 첫 GREEN 실행에서 3건이 떨어졌다. 원인은 시험 오류였다(`AnalysisResult` 에 없는 `duration_ms` 단언). `onsets_ms`·`rms_curve` 동일 비교로 고친 뒤 9 passed.
- RED 실패는 그 단언에 닿기 전, 읽기 단계에서 났다.

## 실곡 10곡 — 업로드와 같은 바이트열로 (`songs_after.py` → `songs_after.txt`)

| 곡 | analyze BPM | detect_beat_grid BPM | 판정 | t550(고치기 전) |
|---|---|---|---|---|
| LOVE ATTACK 외 8곡 | t550 과 같음(소수 셋째 자리) | t550 과 같음 | 모두 keep | 같음 |
| **LoveMe** | **99.994** | **99.994** | keep | **읽기 실패** → 경로 읽기 값 99.994 와 같음 |

## 안 잰 것

- 0 이 아닌 쓰레기 바이트가 프레임 앞에 낀 실제 파일. 일부러 거절로 남겼다.
- 프레임 사이(곡 중간)에 낀 0 바이트. 이번 실패는 형식 판별(파일 머리) 단계의 문제였다.
- mp3 가 아닌 형식(wav·flac·ogg 등)의 머리 틈.
- 이 기계의 libsndfile 1.2.2 밖의 버전. CI 판별 결과는 PR 의 CI 로 본다.
- 전체 시험 스위트(CI 에 맡김). 실기 콘솔(쓰기 0).
