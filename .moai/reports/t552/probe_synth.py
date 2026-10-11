"""t552 — 합성 mp3 로 원인을 재현할 수 있는지 (CI 에 원곡이 없다). 읽기 전용.

실행(워크트리 루트): uv run python .moai/reports/t552/probe_synth.py
"""

import io

import numpy as np
import soundfile as sf

sr = 44100
t = np.arange(sr * 3) / sr
y = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
buf = io.BytesIO()
sf.write(buf, y, sr, format="MP3")
mp3 = buf.getvalue()
print("mp3 bytes", len(mp3), "head", mp3[:4].hex())


def id3(n_body: int) -> bytes:
    """ID3v2.3 머리 + 태그 크기에 포함된 0 바이트 n_body 개."""
    size = bytes(
        [(n_body >> 21) & 0x7F, (n_body >> 14) & 0x7F, (n_body >> 7) & 0x7F, n_body & 0x7F]
    )
    return b"ID3\x03\x00\x00" + size + b"\x00" * n_body


cases = {
    "bare": mp3,
    "id3 no gap": id3(71) + mp3,
    "id3 + 626 zero gap": id3(71) + b"\x00" * 626 + mp3,
    "id3 + 1 zero gap": id3(71) + b"\x00" + mp3,
    "no id3, 626 zero lead": b"\x00" * 626 + mp3,
}
for name, data in cases.items():
    try:
        shape = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)[0].shape
        print(f"{name}: OK {shape}")
    except Exception as error:  # noqa: BLE001 — 측정 스크립트
        print(f"{name}: ERR {error}")
