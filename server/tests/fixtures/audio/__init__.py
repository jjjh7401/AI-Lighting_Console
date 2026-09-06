"""정답이 알려진 합성 트랙 — 코드로 만든다, 파일로 커밋하지 않는다.

REQ-MUSICSYNC-011 · AC-MUSICSYNC-011 · AC-MUSICSYNC-012.

저장소에 실제 곡을 두지 않는 이유는 두 가지다. 하나는 저작권이고, 다른 하나는
**정답을 아는 트랙만이 분석기를 판정할 수 있다**는 것이다. 실제 곡의 BPM 과 구간
경계는 그 자체가 측정 대상이라 기준이 되지 못한다.

그래서 이 모듈은 파형을 **표준 라이브러리만으로** 만든다(``wave`` · ``math`` ·
``struct``). 생성기가 numpy 나 librosa 에 의존하면 「분석기를 검증하는 도구」와
「검증받는 분석기」가 같은 라이브러리를 공유하게 되고, 그 라이브러리의 결함은
양쪽에서 같은 방향으로 어긋나 서로를 가린다.

정답:

* BPM ``128`` — 클릭이 ``60/128 = 0.46875s`` 간격으로 정확히 놓인다.
* 구간 경계 ``0 / 16000 / 32000 / 36000`` ms — 그 자리에서 진폭이 계단으로 바뀐다.
* D 등급 ``1 / 3 / 5 / 2`` — 구간별 RMS 를 최대 구간 RMS 로 나눈 비가 아래
  :data:`SECTION_GAINS` 대로 서로 다른 등급 띠에 떨어지도록 이득을 골랐다.
  등급이 넷 다 다른 것은 의도다 — 전부 같은 등급이면 「등급이 일치한다」가
  아무것도 판정하지 못한다(t109 의 「신호가 서로를 가림」).
"""

from __future__ import annotations

import io
import math
import struct
import wave

__all__ = [
    "FIXTURE_BOUNDARIES_MS",
    "FIXTURE_BPM",
    "FIXTURE_D_LEVELS",
    "FIXTURE_DURATION_MS",
    "LONG_FIXTURE_BOUNDARIES_MS",
    "LONG_FIXTURE_DURATION_MS",
    "LONG_SECTION_GAINS",
    "SAMPLE_RATE",
    "SECTION_GAINS",
    "synthesize_long_section_track",
    "synthesize_track",
]

#: 분석기가 쓰는 것과 같은 눈금. 22.05kHz 면 클릭의 상승 모서리가 충분히 살고,
#: 40초 트랙이 1.7MB 안에 들어 8 MiB 업로드 상한과 무관하게 시험할 수 있다.
SAMPLE_RATE = 22050

FIXTURE_BPM = 128.0
FIXTURE_DURATION_MS = 40_000
FIXTURE_BOUNDARIES_MS = (0, 16_000, 32_000, 36_000)

#: 구간별 진폭. 비(최대 대비)가 0.158 / 0.474 / 1.000 / 0.316 이 되어
#: :data:`FIXTURE_D_LEVELS` 의 네 등급 띠에 하나씩 떨어진다.
SECTION_GAINS = (0.15, 0.45, 0.95, 0.30)

FIXTURE_D_LEVELS = (1, 3, 5, 2)

#: 클릭의 감쇠 시정수와 길이. 박마다 같은 모양이라 박 간격이 일정하고,
#: 그 일정함이 곧 BPM 정답이다.
_CLICK_DECAY_SECONDS = 0.020
_CLICK_LENGTH_SECONDS = 0.080
_CLICK_HZ = 1200.0

#: 클릭 사이를 메우는 낮은 지속음. 구간 RMS 가 이득에 매끄럽게 비례하도록
#: 하는 것이 목적이다 — 클릭만 있으면 RMS 가 박에서만 튀어 계단이 흐려진다.
_DRONE_HZ = 220.0
_DRONE_MIX = 0.15


#: 긴 구간 픽스처 — 마디 분할이 **실제로 걸리는** 유일한 합성 트랙 (카드 t308).
#:
#: 위 40초 픽스처는 가장 긴 구간이 16초라, 8마디 단위 둘(129 BPM 에서 29.7초)에
#: 원리적으로 못 닿는다. 그래서 t306 까지 분할 경로의 시험은 전부 손으로 만든
#: ``ConfirmedSongAnalysis`` 위에서 돌았고, DSP 가 쪼갤 수 있는 구간을 실제로
#: 내놓는지는 **아무도 안 쟀다**. 이 픽스처가 그 구멍을 메운다.
#:
#: 35초 두 구간을 고른 근거: 129.199 BPM · 4/4 에서 8마디 = 14.86초이므로 두
#: 단위가 29.72초다. 35초는 그 문턱을 넘으면서 3단위(44.6초)에는 못 미쳐,
#: 구간마다 큐가 정확히 둘 나온다 — 회전이 한 바퀴 돌아 앞 큐와 같아지는
#: 갈래(``cue_density`` 의 @MX:WARN)를 건드리지 않는다.
LONG_SECTION_GAINS = (0.30, 0.90)
LONG_FIXTURE_BOUNDARIES_MS = (0, 35_000)
LONG_FIXTURE_DURATION_MS = 70_000


def _index_for(time_seconds: float, boundaries_ms: tuple[int, ...]) -> int:
    """이 시각이 몇 번째 구간인가 — 경계 목록을 그대로 읽는다."""
    index = 0
    for boundary_index, boundary_ms in enumerate(boundaries_ms):
        if time_seconds * 1000.0 >= boundary_ms:
            index = boundary_index
    return index


def synthesize_track(
    *,
    bpm: float = FIXTURE_BPM,
    duration_ms: int = FIXTURE_DURATION_MS,
    sample_rate: int = SAMPLE_RATE,
) -> bytes:
    """16비트 모노 WAV 바이트열 하나를 만든다 — 파일 시스템을 거치지 않는다.

    반환값이 ``bytes`` 인 것은 :func:`server.audio.analyze.analyze` 의 입력이
    바이트열이기 때문이다. 임시 파일을 거치면 「분석 중 파일 시스템 접촉 0건」을
    확인하는 시험이 자기 픽스처 때문에 못 서게 된다.
    """
    return _render(
        bpm=bpm,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
        boundaries_ms=FIXTURE_BOUNDARIES_MS,
        gains=SECTION_GAINS,
    )


def synthesize_long_section_track(
    *,
    bpm: float = FIXTURE_BPM,
    duration_ms: int = LONG_FIXTURE_DURATION_MS,
    sample_rate: int = SAMPLE_RATE,
) -> bytes:
    """구간이 **8마디 단위 둘을 넘는** 트랙 — 분할 경로의 유일한 합성 입력.

    파형 규칙은 :func:`synthesize_track` 과 한 벌을 함께 쓴다. 다른 것은 구간
    경계와 이득뿐이다(:data:`LONG_FIXTURE_BOUNDARIES_MS` ·
    :data:`LONG_SECTION_GAINS`) — 파형 규칙을 두 벌 두면 갈라지고, 갈라지면 두
    픽스처가 서로 다른 분석기를 재게 된다.
    """
    return _render(
        bpm=bpm,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
        boundaries_ms=LONG_FIXTURE_BOUNDARIES_MS,
        gains=LONG_SECTION_GAINS,
    )


def _render(
    *,
    bpm: float,
    duration_ms: int,
    sample_rate: int,
    boundaries_ms: tuple[int, ...],
    gains: tuple[float, ...],
) -> bytes:
    beat_period = 60.0 / bpm
    total_samples = int(sample_rate * duration_ms / 1000.0)
    frames = bytearray()
    for n in range(total_samples):
        t = n / sample_rate
        gain = gains[_index_for(t, boundaries_ms)]
        phase = math.fmod(t, beat_period)
        if phase < _CLICK_LENGTH_SECONDS:
            click = math.exp(-phase / _CLICK_DECAY_SECONDS) * math.sin(
                2.0 * math.pi * _CLICK_HZ * phase
            )
        else:
            click = 0.0
        drone = math.sin(2.0 * math.pi * _DRONE_HZ * t)
        value = gain * ((1.0 - _DRONE_MIX) * click + _DRONE_MIX * drone)
        frames += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32000))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()
