"""MP3 프레임 헤더를 앞에서부터 순서대로 걷는다 — 동기가 끊기는 바이트 위치를 찾는다.

t440 재현 도구. 첫 비프레임 바이트에서 멈추는 단순 순회기라 일반 길이 측정기로는 쓰지 않는다.
"""

import sys
from pathlib import Path

BR = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
SR = [44100, 48000, 32000, 0]  # MPEG1 Layer III


def hdr(b, i):
    if i + 4 > len(b) or b[i] != 0xFF or (b[i + 1] & 0xE0) != 0xE0:
        return None
    if ((b[i + 1] >> 3) & 3) != 3 or ((b[i + 1] >> 1) & 3) != 1:
        return None
    br, sr = BR[b[i + 2] >> 4], SR[(b[i + 2] >> 2) & 3]
    if not br or not sr:
        return None
    return 144000 * br // sr + ((b[i + 2] >> 1) & 1), br, sr


def chain(b, i):
    n, brs = 0, {}
    while h := hdr(b, i):
        n += 1
        brs[h[1]] = brs.get(h[1], 0) + 1
        i += h[0]
    return n, i, brs


def seconds(frames):
    return frames * 1152 / 48000


b = Path(sys.argv[1]).read_bytes()
print(f"file bytes={len(b)}")
i = 0
if b[:3] == b"ID3":
    i = 10 + ((b[6] << 21) | (b[7] << 14) | (b[8] << 7) | b[9])
    print(f"ID3v2 tag bytes={i}")
n, end, brs = chain(b, i)
share = end / len(b)
print(
    f"contiguous frames from start={n} ends at byte={end} ({share:.1%} of file)"
    f" -> {seconds(n):.3f}s; bitrates={dict(sorted(brs.items()))}"
)
print(f"bytes at break: {b[end : end + 16].hex(' ')}")
seg_end = end
while seg_end < len(b) - 4:
    j = seg_end + 1
    while j < len(b) - 4 and not (hdr(b, j) and chain(b, j)[0] >= 3):
        j += 1
    if j >= len(b) - 4:
        break
    m, e2, brs2 = chain(b, j)
    nonzero = sum(1 for x in b[seg_end:j] if x)
    print(
        f"resync at byte={j} (gap {j - seg_end} bytes, nonzero {nonzero})"
        f" -> {m} frames {seconds(m):.3f}s, ends byte={e2}; bitrates={dict(sorted(brs2.items()))}"
    )
    seg_end = e2
has_id3v1 = b[-128:-125] == b"TAG"
print(f"trailing bytes after last chain={len(b) - seg_end}; ID3v1 TAG at end: {has_id3v1}")
