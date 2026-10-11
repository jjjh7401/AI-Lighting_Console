"""카드 t552 — 첫 MPEG 프레임 앞에 0 바이트가 낀 mp3 를 업로드 바이트열로 못 읽던 결함.

libsndfile 은 바이트열의 **내용**으로 형식을 알아낸다. ID3v2 태그(또는 파일 머리) 바로
뒤에 프레임 동기 대신 0 바이트가 있으면 MP3 로 알아보지 못하고 ``Format not
recognised`` 를 낸다. 파일 경로로 읽을 때는 확장자 ``.mp3`` 로 형식을 정하는 대체 경로가
있어 읽혔다 — 그래서 경로로는 되고 업로드(BytesIO)로는 안 됐다(실측
``.moai/reports/t552/probe_cause.txt``: 실제 곡은 태그 뒤 0 바이트 626개).

시험은 원곡 없이 합성 mp3 로 한다(``probe_synth.txt`` — 0 바이트 1개로도 재현된다).
"""

from __future__ import annotations

import io

import numpy as np
import pytest

from server.audio.analyze import AnalysisFailure, analyze
from server.audio.bar_map import BeatGridFailure, BeatGridResult, detect_beat_grid

_SAMPLE_RATE = 44100


@pytest.fixture(scope="module")
def click_mp3() -> bytes:
    """120 BPM 클릭 8초를 mp3 로 인코드한 바이트열(머리에 태그 없음)."""
    import soundfile as sf

    audio = np.zeros(_SAMPLE_RATE * 8, dtype=np.float32)
    burst = np.sin(2 * np.pi * 1000 * np.arange(441) / _SAMPLE_RATE).astype(np.float32)
    burst *= np.hanning(882)[441:].astype(np.float32)
    period = 60.0 / 120.0
    for beat in range(int(8 / period)):
        start = int(round(beat * period * _SAMPLE_RATE))
        end = min(start + burst.size, audio.size)
        audio[start:end] += burst[: end - start]
    buffer = io.BytesIO()
    sf.write(buffer, audio, _SAMPLE_RATE, format="MP3")
    payload = buffer.getvalue()
    assert payload[:2] == b"\xff\xfb"  # 첫 바이트가 바로 프레임 동기
    return payload


def _id3(body_len: int) -> bytes:
    """ID3v2.3 머리 + 태그 크기에 포함된 0 바이트 ``body_len`` 개."""
    size = bytes(
        [
            (body_len >> 21) & 0x7F,
            (body_len >> 14) & 0x7F,
            (body_len >> 7) & 0x7F,
            body_len & 0x7F,
        ]
    )
    return b"ID3\x03\x00\x00" + size + b"\x00" * body_len


def _read_frames(payload: bytes) -> int:
    import soundfile as sf

    return len(sf.read(io.BytesIO(payload), dtype="float32", always_2d=True)[0])


@pytest.mark.parametrize(
    "prefix",
    [
        pytest.param(lambda: _id3(71) + b"\x00" * 626, id="id3_then_626_zero_bytes"),
        pytest.param(lambda: _id3(71) + b"\x00", id="id3_then_1_zero_byte"),
        pytest.param(lambda: b"\x00" * 626, id="626_zero_bytes_without_id3"),
    ],
)
class TestZeroGapBeforeFirstFrame:
    def test_analyze_reads_it_like_the_clean_file(self, click_mp3, prefix):
        clean = analyze(_id3(71) + click_mp3)
        gapped = analyze(prefix() + click_mp3)
        assert not isinstance(clean, AnalysisFailure), clean
        assert not isinstance(gapped, AnalysisFailure), gapped.reason
        assert gapped.bpm == pytest.approx(clean.bpm)
        assert gapped.onsets_ms == clean.onsets_ms
        assert gapped.rms_curve == clean.rms_curve

    def test_detect_beat_grid_reads_it_like_the_clean_file(self, click_mp3, prefix):
        clean = detect_beat_grid(_id3(71) + click_mp3)
        gapped = detect_beat_grid(prefix() + click_mp3)
        assert isinstance(clean, BeatGridResult), clean
        assert isinstance(gapped, BeatGridResult), gapped.reason
        assert gapped.beat_times_ms == clean.beat_times_ms
        assert gapped.bpm == pytest.approx(clean.bpm)


def test_a_clean_file_is_decoded_unchanged(click_mp3):
    """대조군 — 틈이 없는 파일은 지금과 똑같이 읽힌다(재시도 경로를 타지 않는다)."""
    assert _read_frames(_id3(71) + click_mp3) == _read_frames(click_mp3)
    assert not isinstance(analyze(_id3(71) + click_mp3), AnalysisFailure)


def test_non_zero_junk_before_the_first_frame_is_still_refused(click_mp3):
    """0 이 아닌 바이트는 건너뛰지 않는다 — 무엇인지 모르는 내용을 오디오로 추측하지
    않는다. 지금처럼 정직하게 거절한다."""
    junk = bytes(range(1, 200)) * 3
    assert isinstance(analyze(_id3(71) + junk + click_mp3), AnalysisFailure)
    assert isinstance(detect_beat_grid(_id3(71) + junk + click_mp3), BeatGridFailure)


def test_garbage_that_is_only_zero_bytes_is_still_refused():
    """0 바이트만 있고 프레임이 없으면 거절한다(예외가 새지 않는다)."""
    assert isinstance(analyze(_id3(71) + b"\x00" * 5000), AnalysisFailure)
    assert isinstance(detect_beat_grid(b"\x00" * 5000), BeatGridFailure)
