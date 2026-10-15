# t649 길이 측정 기록 (SPEC-LDBARMAP-004 plan 전)

- 측정 날짜: 2026-10-14
- 기준: 워크트리 `.claude/worktrees/WT-barmap-song-match`, 브랜치 `WT-barmap-song-match`, 커밋 `af2dd7e1` (작업 트리 깨끗함)
- 측정 코드: 이 커밋의 `server/audio/analyze.py`, `server/audio/bar_map.py`
- 스크립트 (이 디렉터리, 읽기 전용): `measure_len.py` (앱 디코더 + ffprobe + afinfo), `measure_ffmpeg.py` (FFmpeg 전체 디코드)
- 표기: 「없음」·「측정 불가」는 잴 수 없었다는 뜻이다. 옮긴 값은 쓰지 않았다. 디코드 길이는 샘플 수 ÷ 샘플레이트다.

## 0. 기준선 (측정 전에 확인)

```
git status --short                                          → (출력 없음, 깨끗함)
git rev-parse --short HEAD                                  → af2dd7e1
git rev-list --count --left-right origin/main...HEAD        → 2	2
git ls-remote --heads origin                                → 원격 브랜치 목록 (SPEC 번호가 든 이름 없음)
git log --all --oneline --name-only -- '*LDBARMAP-004*'     → (출력 없음)
git ls-files | grep -i -E "\.(mp3|wav|m4a|flac|ogg|aac)$" | wc -l   → 0
```

- 갈라짐 2:2. origin/main 쪽 두 커밋(`adae706a`, `8ee56a9a`)은 `server/web/PROTOCOL.md` 한 줄만 바꾼다. 측정 코드와 겹치지 않는다. 머지는 측정 뒤에 한다.
- SPEC-LDBARMAP-004 는 모든 원격 기준으로 비어 있다. 커밋 메시지의 `REQ-LDBARMAP-004`, `AC-LDBARMAP-004a~d` 는 SPEC-LDBARMAP-001 의 요구사항 번호이지 SPEC 번호가 아니다.

## 1. 계기 보정 — 정답지가 있는 파일

정답은 생성할 때 정했다. 10.000 초짜리 사인파 WAV 하나와, 그 WAV 에서 만든 MP3 두 개다.

생성 명령 (scratchpad 에서 실행, 저장소 밖):

```
ffmpeg -v error -y -f lavfi -i "sine=frequency=440:duration=10:sample_rate=44100" -ac 1 cal_10s.wav
ffmpeg -v error -y -i cal_10s.wav -c:a libmp3lame -b:a 128k cal_cbr_xing.mp3
ffmpeg -v error -y -i cal_10s.wav -c:a libmp3lame -q:a 0 -write_xing 0 cal_vbr_noxing.mp3
```

측정 명령과 원문 출력 (앱 디코더 + ffprobe + afinfo):

```
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I -B .moai/reports/t649/measure_len.py "<scratchpad>/calib"
versions: python=3.11.15 soundfile=0.14.0 libsndfile=1.2.2 numpy=2.4.6 ffprobe version 8.1 Copyright (c) 2007-2026 the FFmpeg developers macOS=26.5.2
cal_10s.wav | format=WAV/PCM_16 | frames=441000 | sr=44100 | declared_s=10.000 | decoded_s=10.000 | app_ms=10000 | bitrate_guess=False | xing_tag=False | ffprobe_s=10.000000 | afinfo_s=10.000000
cal_cbr_xing.mp3 | format=MP3/MPEG_LAYER_III | frames=441000 | sr=44100 | declared_s=10.000 | decoded_s=10.000 | app_ms=10000 | bitrate_guess=False | xing_tag=True | ffprobe_s=10.000000 | afinfo_s=10.031020
cal_vbr_noxing.mp3 | format=MP3/MPEG_LAYER_III | frames=144806 | sr=44100 | declared_s=3.284 | decoded_s=3.284 | app_ms=3284 | bitrate_guess=True | xing_tag=False | ffprobe_s=9.686059 | afinfo_s=8.349273
```

FFmpeg 전체 디코드 원문 출력:

```
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I -B .moai/reports/t649/measure_ffmpeg.py "<scratchpad>/calib"
versions: ffmpeg version 8.1 Copyright (c) 2000-2026 the FFmpeg developers
cal_10s.wav | ffmpeg_samples=441000 | sr=44100 | ffmpeg_decoded_s=10.000 | rc=0 | stderr=없음
cal_cbr_xing.mp3 | ffmpeg_samples=441000 | sr=44100 | ffmpeg_decoded_s=10.000 | rc=0 | stderr=없음
cal_vbr_noxing.mp3 | ffmpeg_samples=442368 | sr=44100 | ffmpeg_decoded_s=10.031 | rc=0 | stderr=없음
```

| 파일 (정답) | 앱 디코드 (libsndfile 1.2.2) | FFmpeg 전체 디코드 (ffmpeg 8.1) | ffprobe 헤더 (8.1) | afinfo 헤더 (macOS 26.5.2) | 출처 |
|---|---|---|---|---|---|
| cal_10s.wav (10.000 s) | 10.000 s | 10.000 s | 10.000 s | 10.000 s | af2dd7e1 · `scratchpad/calib/cal_10s.wav` |
| cal_cbr_xing.mp3 (10.000 s) | 10.000 s | 10.000 s | 10.000 s | 10.031 s (+0.031) | af2dd7e1 · `scratchpad/calib/cal_cbr_xing.mp3` |
| cal_vbr_noxing.mp3 (10.000 s) | **3.284 s (−6.716)** | 10.031 s (+0.031) | 9.686 s (−0.314) | 8.349 s (−1.651) | af2dd7e1 · `scratchpad/calib/cal_vbr_noxing.mp3` |

해석 (관찰과 추정을 나눴다):

- **관찰 1.** 앱 디코더는 `cal_vbr_noxing.mp3` 를 3.284 초에서 멈췄다. 에러는 없었다. `bitrate_guess=True` 라서 잘림 검사(`server/audio/bar_map.py:199-211`)가 꺼졌고, 10 초짜리 파일이 3.284 초 곡으로 그대로 통과했다.
- **관찰 2.** 앱이 읽은 샘플 수 144806 은 libsndfile 이 헤더 추정으로 잡은 프레임 수(`frames=144806`)와 같다.
- **추정 (미확인).** libsndfile 이 헤더 추정 프레임까지만 읽었을 것이다. 추정이 실제보다 작으면 조용히 잘린다. 관찰 2 에서 나온 추정이고, 다른 파일로 재현하지는 않았다.
- **관찰 3.** FFmpeg 은 파일 끝까지 읽었다. 10.031 초이고 정답보다 1368 샘플(+0.031 초) 많다. 이 파일에는 인코더 지연을 되돌리는 Xing/LAME 태그가 없다. 추정: +0.031 초는 인코더 지연과 패딩이다.
- **관찰 4.** 헤더 기반 판독기(ffprobe, afinfo)는 이 파일에서 0.3~1.7 초 틀렸다. 길이 기준으로 쓰면 안 된다.
- **관찰 5.** Xing 이 있는 CBR 파일은 앱 디코더와 FFmpeg 이 모두 정확하다. afinfo 만 +0.031 초다.

## 2. 실제 곡 10개

명령과 원문 출력:

```
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I -B .moai/reports/t649/measure_len.py "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music"
versions: python=3.11.15 soundfile=0.14.0 libsndfile=1.2.2 numpy=2.4.6 ffprobe version 8.1 Copyright (c) 2007-2026 the FFmpeg developers macOS=26.5.2
Club Diver.mp3 | format=MP3/MPEG_LAYER_III | frames=6426506 | sr=44100 | declared_s=145.726 | decoded_s=145.685 | app_ms=145685 | bitrate_guess=False | xing_tag=False | ffprobe_s=145.684900 | afinfo_s=145.684900
Cut and Run.mp3 | format=MP3/MPEG_LAYER_III | frames=9475460 | sr=44100 | declared_s=214.863 | decoded_s=214.831 | app_ms=214831 | bitrate_guess=False | xing_tag=False | ffprobe_s=214.831025 | afinfo_s=214.831025
Ice cream.mp3 | format=MP3/MPEG_LAYER_III | frames=3747456 | sr=48000 | declared_s=78.072 | decoded_s=78.072 | app_ms=78072 | bitrate_guess=False | xing_tag=False | ffprobe_s=78.072000 | afinfo_s=78.072000
Let's Dance.mp3 | format=MP3/MPEG_LAYER_III | frames=6746184 | sr=48000 | declared_s=140.546 | decoded_s=90.984 | app_ms=90984 | bitrate_guess=True | xing_tag=False | ffprobe_s=139.223960 | afinfo_s=139.456000
LoveMe.mp3 | format=MP3/MPEG_LAYER_III | frames=4774272 | sr=44100 | declared_s=108.260 | decoded_s=108.095 | app_ms=108095 | bitrate_guess=False | xing_tag=False | ffprobe_s=108.094667 | afinfo_s=108.094667
Morning.mp3 | format=MP3/MPEG_LAYER_III | frames=6771806 | sr=44100 | declared_s=153.556 | decoded_s=153.313 | app_ms=153313 | bitrate_guess=False | xing_tag=False | ffprobe_s=153.312650 | afinfo_s=153.312650
Rain.mp3 | format=MP3/MPEG_LAYER_III | frames=10684416 | sr=48000 | declared_s=222.592 | decoded_s=222.592 | app_ms=222592 | bitrate_guess=False | xing_tag=True | ffprobe_s=222.592000 | afinfo_s=222.624000
Too Cool.mp3 | format=MP3/MPEG_LAYER_III | frames=8009853 | sr=44100 | declared_s=181.629 | decoded_s=181.577 | app_ms=181577 | bitrate_guess=False | xing_tag=False | ffprobe_s=181.577156 | afinfo_s=181.577156
scott-buckley-neon.mp3 | format=MP3/MPEG_LAYER_III | frames=11425487 | sr=44100 | declared_s=259.081 | decoded_s=259.081 | app_ms=259081 | bitrate_guess=False | xing_tag=True | ffprobe_s=259.081338 | afinfo_s=259.108550
걸그룹DinoDino_C_max최고품질.wav | format=WAV/PCM_16 | frames=7864741 | sr=44100 | declared_s=178.339 | decoded_s=178.339 | app_ms=178339 | bitrate_guess=False | xing_tag=False | ffprobe_s=178.338798 | afinfo_s=178.338798

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I -B .moai/reports/t649/measure_ffmpeg.py "/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music"
versions: ffmpeg version 8.1 Copyright (c) 2000-2026 the FFmpeg developers
Club Diver.mp3 | ffmpeg_samples=6424704 | sr=44100 | ffmpeg_decoded_s=145.685 | rc=0 | stderr=없음
Cut and Run.mp3 | ffmpeg_samples=9474048 | sr=44100 | ffmpeg_decoded_s=214.831 | rc=0 | stderr=없음
Ice cream.mp3 | ffmpeg_samples=3747456 | sr=48000 | ffmpeg_decoded_s=78.072 | rc=0 | stderr=없음
Let's Dance.mp3 | ffmpeg_samples=4367232 | sr=48000 | ffmpeg_decoded_s=90.984 | rc=0 | stderr=없음
LoveMe.mp3 | ffmpeg_samples=4766976 | sr=44100 | ffmpeg_decoded_s=108.095 | rc=0 | stderr=없음
Morning.mp3 | ffmpeg_samples=6761088 | sr=44100 | ffmpeg_decoded_s=153.313 | rc=0 | stderr=없음
Rain.mp3 | ffmpeg_samples=10684416 | sr=48000 | ffmpeg_decoded_s=222.592 | rc=0 | stderr=없음
Too Cool.mp3 | ffmpeg_samples=8007552 | sr=44100 | ffmpeg_decoded_s=181.577 | rc=0 | stderr=없음
scott-buckley-neon.mp3 | ffmpeg_samples=11425487 | sr=44100 | ffmpeg_decoded_s=259.081 | rc=0 | stderr=없음
걸그룹DinoDino_C_max최고품질.wav | ffmpeg_samples=7864741 | sr=44100 | ffmpeg_decoded_s=178.339 | rc=0 | stderr=없음
```

곡별 요약 (출처는 모두 커밋 `af2dd7e1`, 경로는 `src/sample music/` 아래 파일):

| 곡 (파일) | 형식 · Hz | 앱 디코드 (ms, libsndfile 1.2.2) | FFmpeg 전체 디코드 (s, ffmpeg 8.1) | ffprobe 헤더 (s, 8.1) | afinfo 헤더 (s, macOS 26.5.2) | libsndfile 헤더 선언 (s) |
|---|---|---|---|---|---|---|
| Club Diver.mp3 | MP3 · 44100 | 145685 | 145.685 (6424704 샘플) | 145.685 | 145.685 | 145.726 (+0.041) |
| Cut and Run.mp3 | MP3 · 44100 | 214831 | 214.831 (9474048) | 214.831 | 214.831 | 214.863 (+0.032) |
| Ice cream.mp3 | MP3 · 48000 | 78072 | 78.072 (3747456) | 78.072 | 78.072 | 78.072 (0) |
| Let's Dance.mp3 | MP3 · 48000 · Xing 없음 · 비트레이트 섞임 | 90984 | 90.984 (4367232) | 139.224 (+48.240) | 139.456 (+48.472) | 140.546 (+49.562) |
| LoveMe.mp3 | MP3 · 44100 | 108095 | 108.095 (4766976) | 108.095 | 108.095 | 108.260 (+0.165) |
| Morning.mp3 | MP3 · 44100 | 153313 | 153.313 (6761088) | 153.313 | 153.313 | 153.556 (+0.243) |
| Rain.mp3 | MP3 · 48000 · Xing 있음 | 222592 | 222.592 (10684416) | 222.592 | 222.624 (+0.032) | 222.592 (0) |
| Too Cool.mp3 | MP3 · 44100 | 181577 | 181.577 (8007552) | 181.577 | 181.577 | 181.629 (+0.052) |
| scott-buckley-neon.mp3 | MP3 · 44100 · Xing 있음 | 259081 | 259.081 (11425487) | 259.081 | 259.109 (+0.027) | 259.081 (0) |
| 걸그룹DinoDino_C_max최고품질.wav | WAV PCM_16 · 44100 | 178339 | 178.339 (7864741) | 178.339 | 178.339 | 178.339 (0) |

- **앱 디코드 = FFmpeg 전체 디코드.** 10곡 모두 밀리초 단위에서 같다. 샘플 단위로는 비교하지 않았다. 앱 쪽 샘플 수는 출력하지 않았다.
- **헤더 기준은 디코드와 다르다.** libsndfile 선언값은 Let's Dance 를 빼고 0~0.243 초 차이다(Morning 이 최대). Let's Dance 는 ffprobe·afinfo·선언값 모두 +48 초 이상이다.
- **LoveMe (카드 t413 에서 「디코더마다 다름」).** 이번 측정에서 디코드 길이 네 개(앱, FFmpeg, ffprobe, afinfo)는 108.095 초로 같다. 다른 값은 libsndfile 헤더 선언값(108.260 초, +0.165)뿐이다.
- **Let's Dance.** 앱 디코드 90.984 초 = FFmpeg 90.984 초. 코드 주석의 t440 실측 90.98 초와도 맞는다(`server/audio/analyze.py:322-323`). ffprobe·afinfo·선언값은 프레임 비트레이트로 어림한 헤더 추정이다(`server/audio/analyze.py:317-327`).

## 3. 타임라인 길이 — 「없음」 (이번 측정에서 잰 값 없음)

- 추적 파일 이름 검색(`git ls-files | grep -i -E "timeline|sections|bar_map|beat_grid"`)에 곡별 타임라인 파일은 없다. 걸린 것은 그림, 문서, LOVE ATTACK 산출물뿐이다.
- 곡 이름 `git grep -c -i` 에 걸린 파일은 보고서 위주다. 그중 `server/tests/fixtures/pilot_baseline.json` 은 LoveMe 를 언급하지만 이번에 열어 확인하지 않았다. 옮긴 값으로 쓰지 않는다.
- 타임라인은 세션 안에서 만들어진다: `analyse_bar_map` (`server/web/session.py:9478`). 지도 저장소 `server/audio/bar_map_store.py` 에는 저장 경로 정의가 없다(`Path`, `expanduser`, `environ` 검색 결과 없음).
- 이번 측정은 앱을 띄우지 않았으므로 10곡 모두 타임라인 길이는 「없음 — 측정 안 함」이다. 재려면 앱 세션에서 곡마다 분석해야 한다.

## 4. 편집판 쌍 — 「편집판 측정 불가」

- `src/sample music/` 에는 원본 10개뿐이다. 저장소 추적 음원 파일은 0개다(0절).
- 편집판 쌍은 만들지 않았다.

## 5. LOVE ATTACK — 음원 없음 (측정 불가)

- 리드 보고는 `.moai/reports/t505/` 아래라고 했다. 실제로 `t505/` 와 `t505/evidence/` 에는 LOVE 파일이 없다(`find ... -iname "*LOVE*"` 결과 없음).
- 주 체크아웃 전체에서 `*love*attack*` 를 찾았다(`node_modules`, `.venv`, `.git`, `.claude/worktrees`, `dist`, `build` 제외). 산출물(md, json, html, png, py)만 나왔고 음원(.mp3, .wav)은 없었다.
- 숫자를 쓰지 않는다. `server/tests/fixtures/love_attack_bar_features_real.json` 같은 픽스처에 길이 값이 있을 수 있지만 이번에 재지 않았고, 옮긴 값으로도 쓰지 않는다.

## 6. 이번 측정이 말하는 것 (관찰과 추정)

관찰:

1. 실제 곡 10개에서 앱 디코드 길이와 FFmpeg 전체 디코드 길이는 밀리초 단위에서 모두 같다.
2. 헤더 기반 길이는 디코드와 다르다. libsndfile 선언값은 0~0.243 초(Let's Dance 제외), Let's Dance 는 헤더 판독기 셋 모두 +48 초 이상이다.
3. Xing 헤더 없는 VBR MP3 보정 파일에서 앱 디코더는 10 초 파일을 3.284 초로 읽었고, 에러 없이 통과했다(`bitrate_guess=True` 라서 잘림 검사가 꺼졌다).

추정 (미확인):

- 3번의 원인은 libsndfile 이 헤더 추정 프레임까지만 읽는 것이다(읽은 프레임 수 = 헤더 추정 프레임 수 = 144806). 다른 파일로 재현하지 않았다.
- 실제 곡 10개에서는 3번 현상이 나타나지 않았다. Let's Dance 는 `bitrate_guess=True` 였지만 헤더 추정이 과대(140.5 초)여서 디코드가 파일 끝까지 갔다(90.984 초, FFmpeg 과 일치). 추정이 과소인 경우는 보정 파일로만 봤다.

## 7. 허용 오차 — 정하지 않았다

- 근거: 편집판 쌍 0개, 타임라인 길이 측정 0개. 근거가 없으면 숫자를 정하지 않는다(감독 결정).
- 측정으로 말할 수 있는 것은 산포뿐이다. 숫자를 고르는 근거는 아니다. 디코드끼리(앱 vs FFmpeg)는 10곡 모두 차이 0 ms. 헤더 기준은 선언값 최대 +49.562 초(Let's Dance, §2 109행), afinfo의 Let's Dance 값은 +48.472 초(§2 109행), Let's Dance를 뺀 최대는 +0.243 초(Morning, §2 111행). (정정 2026-10-15)
- 리드에게 보고할 항목: (a) 편집판 쌍 목록, (b) 타임라인 길이를 어떻게 잴지(앱 세션에서 곡마다 분석할지), (c) 3번 조용한 잘림을 길이 검사가 어떻게 다룰지.

## 8. 미검증 (Gaps)

- 샘플 단위 비교: 앱 쪽 샘플 수를 출력하지 않았다. 밀리초 단위까지만 비교했다.
- 타임라인 길이: 측정하지 않았다(앱 세션 필요).
- 편집판 길이 차이: 쌍이 없다.
- LOVE ATTACK: 음원이 없다.
- 조용한 잘림의 원인: 관찰과 추정만 있다.
- afinfo: macOS 26.5.2 의 시스템 도구이고, 버전 문자열은 얻지 못했다.

## 9. 잔여 위험

- 길이 검사가 디코드 길이를 기준으로 쓰이면, 3번 경로(Xing 없음, 프레임 비트레이트 섞임, 헤더 추정 과소)에서 틀린 길이가 통과할 수 있다.
- 헤더 기준 판독기를 길이 기준으로 쓰면 곡에 따라 최대 48 초(Let's Dance) 틀린다.
- 디코더 버전이 바뀌면 헤더 추정과 잘림 동작이 달라질 수 있다.
