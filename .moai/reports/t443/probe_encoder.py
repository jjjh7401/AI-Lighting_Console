"""t443 탐침 — soundfile 의 MP3 인코더가 어떤 헤더·비트레이트 모양을 쓰는지 잰다.

MPEG1/2/2.5 Layer III 프레임을 헤더 규칙대로 순회해 비트레이트 분포와 Xing/Info/VBRI 유무를 본다.
"""

import io

import numpy
import soundfile

BR1 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
BR2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
SR = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def header(b, i):
    if i + 4 > len(b) or b[i] != 0xFF or (b[i + 1] & 0xE0) != 0xE0:
        return None
    ver = (b[i + 1] >> 3) & 3
    if ver == 1 or ((b[i + 1] >> 1) & 3) != 1:
        return None
    bri, sri = b[i + 2] >> 4, (b[i + 2] >> 2) & 3
    if bri in (0, 15) or sri == 3:
        return None
    br = (BR1 if ver == 3 else BR2)[bri]
    sr = SR[ver][sri]
    coeff = 144000 if ver == 3 else 72000
    return coeff * br // sr + ((b[i + 2] >> 1) & 1), br


def walk(b):
    i = 0
    if b[:3] == b"ID3":
        i = 10 + ((b[6] << 21) | (b[7] << 14) | (b[8] << 7) | b[9])
    first = i
    brs, n = {}, 0
    while h := header(b, i):
        brs[h[1]] = brs.get(h[1], 0) + 1
        n += 1
        i += h[0]
    tags = [t.decode() for t in (b"Xing", b"Info", b"VBRI") if t in b[first : first + 2000]]
    return f"frames={n} end={i}/{len(b)} tags={tags} bitrates={dict(sorted(brs.items()))}"


rate = 44100
t = numpy.arange(int(rate * 12)) / rate
rng = numpy.random.default_rng(7)
# 앞 2초 무음 → 뒤는 잡음 + 음정: 첫 프레임은 낮은 비트레이트, 뒤는 높게
signal = numpy.where(
    t < 2.0, 0.0, 0.4 * rng.standard_normal(t.size) + 0.3 * numpy.sin(2 * numpy.pi * 440 * t)
)
stereo = numpy.stack([signal, signal], axis=1).astype("float32")
for mode in ("CONSTANT", "VARIABLE", "AVERAGE"):
    buf = io.BytesIO()
    soundfile.write(buf, stereo, rate, format="MP3", bitrate_mode=mode)
    b = buf.getvalue()
    inf = soundfile.info(io.BytesIO(b))
    d = len(soundfile.read(io.BytesIO(b))[0])
    print(mode, walk(b), "declared", inf.frames, "decoded", d)

# 한결같은 큰 잡음 → 프레임 비트레이트가 한 값으로 모이는지 (CBR 모양)
noise = (0.9 * rng.standard_normal(int(rate * 12))).clip(-1, 1)
buf = io.BytesIO()
soundfile.write(buf, numpy.stack([noise, noise], axis=1).astype("float32"), rate, format="MP3")
print("NOISE", walk(buf.getvalue()))
quiet = numpy.zeros(int(rate * 12), dtype="float32")
buf = io.BytesIO()
soundfile.write(buf, numpy.stack([quiet, quiet], axis=1), rate, format="MP3")
print("SILENCE", walk(buf.getvalue()))
