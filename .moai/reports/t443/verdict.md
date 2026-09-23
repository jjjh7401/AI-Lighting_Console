# t443 판정 — 헤더 없는 VBR MP3 절단 오판 수정

카드: t443 (클래스 B) · 기준 origin/main `fbc3c838` · 브랜치 `WT-vbr-length-check` · 측정일 2026-09-23
원인 근거: `.moai/reports/t440/verdict.md` (Let's Dance.mp3 — 선언 140.546초는 헤더 없는 VBR 의 비트레이트 어림, 실제 곡 90.984초)

## 판정: PASS

앱의 절단 판정(t416)이 **헤더 없는 VBR MP3** 의 부푼 선언 길이를 더는 기준으로 쓰지 않는다.
디코더(읽기)는 바뀌지 않았고, 진짜 잘린 파일 세 모양은 계속 거절된다.

## 바뀐 것 (`server/audio/analyze.py`)

- `_mp3_frame(payload, at)` — MPEG1/2/2.5 Layer III 프레임 헤더 하나를 읽어 (프레임 바이트 수, kbps).
- `_mp3_length_is_a_bitrate_guess(payload)` — ID3v2 를 건너뛰고, 다음 프레임까지 이어지는 첫 프레임을 찾아,
  그 프레임에 Xing/Info/VBRI 가 **없고** 이어지는 프레임의 비트레이트가 **둘 이상 섞였을 때만** 참.
  프레임을 못 찾거나 헤더가 있거나 비트레이트가 한 값이면 거짓 → 절단 검사가 이전 그대로 돈다.
- `analyze()` — `soundfile.info()` 의 `format == "MP3"` 이고 위 함수가 참이면 절단 검사(`_MIN_DECODED_FRACTION`)를 건너뛴다.
  `soundfile.read` 호출과 그 결과는 손대지 않았다.
- 주석 정정: t416 주석과 `_MIN_DECODED_FRACTION` 설명의 「Let's Dance 는 libmpg123 dequantization failed 로 91초에서 멈춤 / 0.647 은 실측 잘림」
  서술을 t440 실측(선언이 부푼 것)으로 고쳤다. `dequantization failed` 는 합성 절단 변형에서는 실제로 찍힌다(아래 변이 실행 stderr) — 그 곡에서만 아니었다.

## 시험 (`server/tests/test_audio_analyze.py`, 새 클래스 `TestAHeaderlessVbrMp3IsNotMistakenForATruncatedOne`)

Let's Dance 는 git 밖이라 시험 입력은 전부 `soundfile` 로 합성한다(CI 에 ffmpeg 없음 — `.github/workflows/test.yml` 에 설치 단계 없음).
인코더는 `bitrate_mode` 를 무시하고 항상 **Xing 붙은 VBR** 을 쓴다(`probe_encoder.py` 실측: CONSTANT/VARIABLE/AVERAGE 세 출력 바이트 수 동일, 전부 Xing).
그래서 모양은 Xing 프레임을 떼어 만든다.

| 시험 | 입력 모양 | 기대 |
|---|---|---|
| `test_the_fixture_reproduces_the_inflated_declaration` | 무음 3초 + 합성 곡, Xing 프레임 제거 = 헤더 없는 VBR | 디코드 < 선언 × 0.9 (픽스처가 Let's Dance 모양인지 자체 검증) |
| `test_a_headerless_vbr_mp3_is_analysed` | 위와 같음 | `AnalysisResult` |
| `test_a_truncated_vbr_mp3_with_a_xing_header_is_still_refused` | Xing 있는 VBR 을 바이트 절반에서 자름 (대조군 1) | `AnalysisFailure` 「끝까지 읽지 못했습니다」 |
| `test_a_silently_truncated_headerless_cbr_mp3_is_still_refused` | 무음 → 한 비트레이트(CBR), Xing 제거, 가운데 24바이트를 0xFF 로 덮음 (대조군 2) | `AnalysisFailure` 「끝까지 읽지 못했습니다」; 덮지 않은 같은 CBR 은 그 사유로 거절 안 됨 |
| 기존 `TestASilentlyTruncatedDecodeIsRefusedNotAnalysed` | Xing 있는 VBR 가운데를 0x55 로 덮음 (대조군 3) | 그대로 거절 |

CBR 대조군의 덮는 값은 탐침으로 골랐다(`probe_cbr_tail.py`): 0x00·0x55 는 예외를 내거나 멈추지 않았고 0xFF 만 예외 없이 33% 지점에서 멈췄다.
처음 시도한 「0 바이트 꼬리 덧붙이기」는 libmpg123 가 `Giving up resync` 예외를 내 조용한 절단 모양이 아니어서 버렸다.

### 녹색

```
.venv/bin/python -m pytest -q server/tests/test_audio_analyze.py server/tests/test_audio_fallback.py
54 passed in 5.45s
```

### 빨강 — 판정만 옛 동작으로 되돌림 (`length_is_a_guess = False`, 도우미는 그대로)

```
FAILED ...::TestAHeaderlessVbrMp3IsNotMistakenForATruncatedOne::test_a_headerless_vbr_mp3_is_analysed
E  AssertionError: 오디오를 끝까지 읽지 못했습니다 — 파일은 49.0초인데 23.1초에서 디코더가 멈췄습니다. ...
1 failed, 6 passed, 36 deselected
```

합성 곡이 Let's Dance 와 같은 문장으로 거절된다 — 픽스처가 결함을 재현한다.
(파일째 되돌린 첫 시도는 새 도우미 import 에서 먼저 죽어 판별력이 없어서 이 형태로 다시 쐈다.)

### 변이 — 판정을 항상 「어림」으로 (`length_is_a_guess = True`)

```
[src/libmpg123/layer3.c:INT123_do_layer3():1804] error: dequantization failed!
FAILED ...::TestASilentlyTruncatedDecodeIsRefusedNotAnalysed::test_a_truncated_decode_comes_back_as_a_failure_naming_both_lengths
FAILED ...::TestAHeaderlessVbrMp3IsNotMistakenForATruncatedOne::test_a_truncated_vbr_mp3_with_a_xing_header_is_still_refused
FAILED ...::TestAHeaderlessVbrMp3IsNotMistakenForATruncatedOne::test_a_silently_truncated_headerless_cbr_mp3_is_still_refused
3 failed, 4 passed, 36 deselected
```

대조군 셋이 모두 이 변이를 잡는다 — 검사를 통째로 끄는 수정이면 통과하지 못한다.

## 실제 곡 (git 밖 `src/sample music/`, `probe_samples.py` → `samples_after.txt`)

| 곡 | 선언 | 어림 판정 | 결과 |
|---|---|---|---|
| Let's Dance.mp3 | 140.546s | **True** | **AnalysisResult bpm=119.68** (t440 의 WAV 재출력 결과 119.68 과 같다) |
| Club Diver · Cut and Run · Ice cream · Morning · Rain · Too Cool · scott-buckley-neon | — | False | AnalysisResult (변화 없음) |
| DinoDino.wav | 178.339s | False(MP3 아님) | AnalysisResult |
| LoveMe.mp3 | info 실패 | — | AnalysisFailure 형식 오류 (t413 별건, 그대로) |

판정이 바뀐 곡은 Let's Dance 하나다.

## 한계 (알고 넘긴 것)

- **헤더 없는 VBR 이 가운데서 조용히 잘리면 이제 통과한다.** 선언 자체가 어림이라 원래도 절단의 증거가 못 되던 경우다 —
  기준이 틀린 검사로 막던 것을 뺀 것이지 새 구멍을 연 것은 아니다. 다만 그 곡은 잘린 부분만 분석된다.
- 판별은 **첫 프레임부터 동기가 끊기기 전까지** 본 비트레이트만 쓴다. 가운데가 깨진 헤더 없는 VBR 이라도 깨지기 전에
  비트레이트가 한 값뿐이었다면 CBR 로 보고 검사를 유지한다(보수적 방향).
- 동기 탐색은 ID3 뒤 64 KiB 까지. 그 안에서 연속 두 프레임을 못 찾으면 검사를 유지한다.
- 앱을 띄워 업로드하지는 않았다 — `analyze()` 를 직접 불렀다.
- 전체 스위트는 로컬에서 돌리지 않았다(pre-push 의 test-fast + CI 가 돈다).
