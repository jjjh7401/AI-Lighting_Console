"""t443 탐침 — 헤더 없는 CBR 에서 디코더가 **예외 없이** 멈추는 변형이 있는지 찾는다."""

import io
import sys

import numpy
import soundfile

sys.path.insert(0, ".")
from server.audio.analyze import _mp3_frame  # noqa: E402

rate = 22050
buf = io.BytesIO()
soundfile.write(buf, numpy.zeros((rate * 20, 1), dtype="float32"), rate, format="MP3")
raw = buf.getvalue()
cbr = raw[_mp3_frame(raw, 0)[0] :]
print("cbr bytes", len(cbr), "first frame", _mp3_frame(cbr, 0))

for fill in (b"\x55", b"\xff", b"\x00"):
    for width in (24, 256):
        found = 0
        for pos in range(len(cbr) // 3, len(cbr) - 400, 13):
            broken = bytearray(cbr)
            broken[pos : pos + width] = fill * width
            try:
                declared = soundfile.info(io.BytesIO(bytes(broken))).frames
                decoded = len(soundfile.read(io.BytesIO(bytes(broken)))[0])
            except Exception:  # noqa: BLE001
                continue
            if declared and 0.3 < decoded / declared < 0.9:
                print(
                    "fill", fill, "width", width, "pos", pos, "ratio", round(decoded / declared, 3)
                )
                found += 1
                break
        if not found:
            print("fill", fill, "width", width, "none")
