"""t649 길이 측정 — FFmpeg 전체 디코드 (앱과 다른 독립 디코더). 읽기 전용.

ffprobe 의 format.duration 은 헤더 추정일 수 있다(VBR·Xing 없음). 그래서 파일을 끝까지
디코드해 샘플 수를 센다. 모노로 내리고 16비트 원시 PCM 으로 뽑아 바이트 수 ÷ 2 가 샘플 수다.
샘플 수 ÷ 샘플레이트가 디코드된 길이다. 파일을 옮기거나 쓰지 않는다.

실행: .venv/bin/python -I -B .moai/reports/t649/measure_ffmpeg.py <폴더 또는 파일>...
"""

import subprocess
import sys
from pathlib import Path

AUDIO_SUFFIXES = {".mp3", ".wav"}


def run(cmd, binary=False):
    return subprocess.run(cmd, capture_output=True, text=not binary)


def sample_rate(path):
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    return int(out.stdout.strip())


def measure(path):
    rate = sample_rate(path)
    proc = run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-f",
            "s16le",
            "-",
        ],
        binary=True,
    )
    samples = len(proc.stdout) // 2
    error = proc.stderr.decode(errors="replace").strip()[:120]
    return (
        f"{path.name} | ffmpeg_samples={samples} | sr={rate} "
        f"| ffmpeg_decoded_s={samples / rate:.3f} | rc={proc.returncode} "
        f"| stderr={error or '없음'}"
    )


def main(args):
    print("versions:", run(["ffmpeg", "-version"]).stdout.splitlines()[0])
    for arg in args:
        target = Path(arg)
        if target.is_dir():
            files = sorted(p for p in target.iterdir() if p.suffix.lower() in AUDIO_SUFFIXES)
        else:
            files = [target]
        for path in files:
            print(measure(path))


if __name__ == "__main__":
    main(sys.argv[1:])
