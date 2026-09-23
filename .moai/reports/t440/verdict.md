# t440 판정 — Let's Dance.mp3 분석 거부 원인

카드: t440 (클래스 B, 원인 보고만 · 코드 수정 없음)
기준: origin/main `bb47bab4` · 브랜치 `WT-letsdance-decode` · 측정일 2026-09-23
입력: `src/sample music/Let's Dance.mp3` (git 밖, 2,248,728 bytes, sha256 `0003d64b…d4632cc5f`)

## 결론

**디코더는 멈추지 않았다. 곡이 실제로 90.98초이고, 틀린 쪽은 「파일은 140.5초」라는 선언 길이다.**

- 이 파일은 **VBR(가변 비트레이트) MP3인데 Xing/Info/VBRI 헤더가 없다.** 헤더가 없으면 판독기는
  첫 프레임 비트레이트(128 kbps)로 길이를 **추정**한다: 2,248,728 B × 8 ÷ 128,000 = **140.5455초**.
  실제 프레임 평균은 약 197 kbps라 추정이 1.54배 부풀었다.
- 앱의 거부 판정(`server/audio/analyze.py:248` `soundfile.info().frames` 대 `:249` `soundfile.read()` 길이,
  `:260` 임계 `_MIN_DECODED_FRACTION = 0.98`)은 그 **추정값을 선언 길이로 믿어서** 비율 0.647로 거절했다.
- 파일 손상 아님: 프레임 3,791개가 파일 첫 바이트부터 **마지막 바이트(2,248,728)까지 빈틈없이** 이어진다.
  끝 부분 음량은 자연스러운 페이드아웃이다(아래 표).
- 모든 판독기가 같은 90.98초를 읽는다 — soundfile·librosa·ffmpeg 모두 오류 없이 4,367,232샘플.

## 판독기별 실측

| 판독기 | 선언/추정 길이 | 실제로 디코드한 길이 |
|---|---|---|
| `soundfile` 0.14.0 / libsndfile 1.2.2 `info().frames` | 140.546초 | — |
| `soundfile.read` (앱 경로 `analyze.py:249`) | — | 90.984초 (4,367,232샘플) |
| `librosa.load(sr=None)` | — | 90.984초 |
| `ffprobe` format.duration | 139.224초 (`Estimating duration from bitrate` 경고) | — |
| `ffmpeg -f s16le` 전체 디코드 | — | 90.984초 (17,468,928 bytes, 경고 외 오류 0줄) |
| `afinfo` (macOS) | 139.456초 (`estimated duration`) | — |
| 프레임 직접 순회 `mp3walk.py` | — | 3,791프레임 × 1152 ÷ 48 kHz = 90.984초, 파일 100% 도달 |

추정 판독기 셋(soundfile.info·ffprobe·afinfo)은 139~140.5초로 서로도 다르고, 실제 디코드 넷은 90.984초로 정확히 일치한다.

프레임 비트레이트 분포(`mp3walk.py`): `{32:1, 40:1, 64:6, 80:2, 96:15, 112:82, 128:162, 160:675, 192:1796, 224:498, 256:371, 320:182}` — 첫 프레임은 128 kbps(`ff fa 94 40`, CRC 보호 비트 켜짐).

끝부분 음량(모노 RMS, 0.5초 창):

| 끝에서 | −2.0s | −1.5s | −1.0s | −0.5s | 0.0s |
|---|---|---|---|---|---|
| RMS | 0.0385 | 0.0150 | 0.0057 | 0.0019 | 0.0004 |

곡 전체 RMS 0.1806 대비 끝 1초 RMS 0.0014 — 끊김이 아니라 페이드아웃으로 끝난다.

## 대조군

같은 `analyze()` 경로(이 트리 코드 그대로):

| 입력 | 선언 | 디코드 | 비율 | 결과 |
|---|---|---|---|---|
| Let's Dance.mp3 원본 | 140.546s | 90.984s | 0.647 | `AnalysisFailure` — 「파일은 140.5초인데 91.0초에서 디코더가 멈췄습니다」 |
| Club Diver.mp3 (정상 곡, CBR 320) | 145.726s | 145.685s | 1.000 | `AnalysisResult` bpm=139.67 |
| Let's Dance → `ffmpeg` WAV 재출력 | 90.984s | 90.984s | 1.000 | `AnalysisResult` bpm=119.68 |

세 번째 줄이 판별 대조군이다: 오디오 내용은 같고 **길이 선언만 정확해지자** 통과한다. 거부의 원인은 오디오가 아니라 선언 길이다.

샘플 폴더 MP3 8곡의 VBR 헤더 유무(`Xing`/`Info`/`VBRI` 탐색):

| 곡 | 비트레이트 | 헤더 |
|---|---|---|
| Rain | VBR | Xing 있음 → 정확 |
| scott-buckley-neon | CBR 320 | Info |
| Club Diver · Cut and Run · Ice cream · Morning · Too Cool | CBR | 없음(CBR이라 추정이 맞음) |
| **Let's Dance** | **VBR** | **없음 → 추정이 틀림** |
| LoveMe | — | 프레임 동기 없음(t413 별건) |

이 표본에서 **VBR + 헤더 없음** 조합은 Let's Dance 하나다.

## 기존 주석과 어긋나는 점 (t416)

`analyze.py:256-259` 주석은 「libmpg123가 91초에서 `dequantization failed`로 멈추고」라고 적는다. 이 트리·이 환경에서는
재현되지 않았다: `soundfile.read` 를 stderr 포함으로 돌려도 그 메시지는 0줄이었고, 91초 뒤에 디코드할 프레임 자체가 없다.
주석은 「디코더가 조용히 잘라 읽었다」로 진단했지만, 실측은 「선언이 부풀었다」이다. 거부 로직(부분 분석 금지)은 이
파일에서 **결과적으로 오진**이다 — 온전한 곡을 잘린 곡으로 판정한다. 코드는 배차대로 손대지 않았다.

## 처방 선택지 (리드·감독 판단용, 이 카드에선 실행 안 함)

1. **파일 쪽**: 곡을 WAV로 다시 내보내거나 `ffmpeg -i in.mp3 -c copy -write_xing 1 out.mp3`로 Xing 헤더를 붙인다. 앱 변경 없음.
2. **앱 쪽**: 선언 길이를 믿는 조건을 좁힌다 — 예: 헤더 없는 VBR에선 추정 길이를 기준으로 쓰지 않는다. 거부 메시지가
   「WAV로 다시 내보내라」를 이미 안내하므로 1번만으로도 사용자는 풀 수 있다. 다만 메시지 문구(「디코더가 멈췄습니다」)는
   이 경우 사실이 아니다.

## 재현 명령줄

```
python3 .moai/reports/t440/mp3walk.py "src/sample music/Let's Dance.mp3"
# → contiguous frames from start=3791 ends at byte=2248728 (100.0% of file) -> 90.984s
ffmpeg -hide_banner -nostdin -i "src/sample music/Let's Dance.mp3" -f s16le -ac 2 -ar 48000 - 2>/dev/null | wc -c
# → 17468928  (= 90.984s)
ffprobe -v error -show_entries format=duration -of default=nw=1 "src/sample music/Let's Dance.mp3"
# → duration=139.223960
afinfo "src/sample music/Let's Dance.mp3"
# → estimated duration: 139.456000 sec
.venv/bin/python -c "import io,soundfile as s;d=open(\"src/sample music/Let's Dance.mp3\",'rb').read();i=s.info(io.BytesIO(d));x,_=s.read(io.BytesIO(d));print(i.frames/i.samplerate,len(x)/i.samplerate)"
# → 140.5455 90.984
```

`ffmpeg_decode.txt` = 전체 디코드의 경고 출력 원문(1줄, 오류 0).

## 안 잰 것

- libmpg123를 직접 호출해 `dequantization failed`를 찾지는 않았다(`mpg123` CLI 미설치). 부재는 soundfile 경유 stderr로만 확인.
- 앱을 실제로 띄워 업로드하지는 않았다 — `analyze()` 함수를 직접 불렀다(t429 는 앱 경로로 같은 메시지를 관측).
- `mp3walk.py` 는 첫 비프레임 바이트에서 멈추는 단순 순회기다. Club Diver 에서는 133.8초에서 멈췄다(디코더는 145.7초) —
  일반 길이 측정기로는 못 쓴다. Let's Dance 에서는 파일 끝 바이트에 정확히 도달했고 디코더 넷과 일치해서 근거로 썼다.
- 원 음원의 제작 길이(출처 메타데이터)는 확인 수단이 없다. 91초라는 판단은 프레임 수·페이드아웃·판독기 일치에 근거한다.
