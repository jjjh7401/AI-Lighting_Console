"""t552 원인 측정 — 같은 mp3 를 네 가지 방식으로 읽어 비교한다 (읽기 전용).

실행(워크트리 루트): uv run python .moai/reports/t552/probe_cause.py <mp3 경로...>
임시 사본은 스크래치 디렉터리(인자 TMPDIR 또는 시스템 임시)에만 만든다.
"""

import io
import os
import shutil
import sys
import tempfile

import soundfile as sf

print("libsndfile", sf.__libsndfile_version__, "soundfile", sf.__version__)


def attempt(label, target, **kw):
    try:
        data, sr = sf.read(target, dtype="float32", always_2d=True, **kw)
        return f"{label}: OK {data.shape} sr={sr}"
    except Exception as error:  # noqa: BLE001 — 측정 스크립트
        return f"{label}: ERR {error}"


def id3_info(b: bytes) -> str:
    if b[:3] != b"ID3":
        return f"no ID3v2; head={b[:4].hex()}"
    size = (b[6] << 21) | (b[7] << 14) | (b[8] << 7) | b[9]
    end = 10 + size + (10 if b[5] & 0x10 else 0)
    return (
        f"ID3v2.{b[3]}.{b[4]} flags=0x{b[5]:02x} tag_size={size} audio_starts_at={end} "
        f"bytes_at_end={b[end:end + 4].hex()}"
    )


with tempfile.TemporaryDirectory() as tmp:
    for path in sys.argv[1:]:
        raw = open(path, "rb").read()
        print("==", os.path.basename(path), "size", len(raw))
        print("  ", id3_info(raw))
        noext = os.path.join(tmp, "copy_noext")
        shutil.copyfile(path, noext)
        print("  ", attempt("path .mp3", path))
        print("  ", attempt("path no-ext", noext))
        print("  ", attempt("bytes", io.BytesIO(raw)))
        print("  ", attempt("bytes format=MP3", io.BytesIO(raw), format="MP3"))
