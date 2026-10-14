"""t649 길이 측정 — 읽기 전용.

앱 디코더(`server/audio/analyze.py` 의 `_read_audio`, `server/audio/bar_map.py` 의
`_decode_mono_audio`)가 내는 길이와 외부 판독기(ffprobe, macOS afinfo)가 내는 길이를
같은 파일에서 나란히 잰다. 파일을 옮기거나 쓰지 않는다.

실행: .venv/bin/python -I -B .moai/reports/t649/measure_len.py <폴더 또는 파일>...
"""

import re
import subprocess
import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKTREE))

import numpy  # noqa: E402
import soundfile  # noqa: E402

from server.audio import analyze, bar_map  # noqa: E402

AUDIO_SUFFIXES = {".mp3", ".wav"}
XING_TAGS = (b"Xing", b"Info", b"VBRI")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def ffprobe_seconds(path):
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ]
    )
    return out or "없음"


def afinfo_seconds(path):
    match = re.search(r"estimated duration: ([\d.]+) sec", run(["afinfo", str(path)]))
    return match.group(1) if match else "없음"


def measure(path):
    payload = path.read_bytes()
    try:
        info, samples, sample_rate, used = analyze._read_audio(soundfile, payload)
    except Exception as error:  # 앱이 읽지 못한 경우도 그대로 적는다
        return f"{path.name} | 앱 읽기 실패: {type(error).__name__}: {error}"
    app = bar_map._decode_mono_audio(payload)
    app_ms = app.duration_ms if isinstance(app, bar_map._DecodedAudio) else f"실패({app})"
    guess = info.format == "MP3" and analyze._mp3_length_is_a_bitrate_guess(used)
    fields = [
        path.name,
        f"format={info.format}/{info.subtype}",
        f"frames={info.frames}",
        f"sr={info.samplerate}",
        f"declared_s={info.frames / info.samplerate:.3f}",
        f"decoded_s={samples.shape[0] / sample_rate:.3f}",
        f"app_ms={app_ms}",
        f"bitrate_guess={guess}",
        f"xing_tag={any(tag in used[:8192] for tag in XING_TAGS)}",
        f"ffprobe_s={ffprobe_seconds(path)}",
        f"afinfo_s={afinfo_seconds(path)}",
    ]
    return " | ".join(fields)


def main(args):
    print(
        "versions:",
        f"python={sys.version.split()[0]}",
        f"soundfile={soundfile.__version__}",
        f"libsndfile={soundfile.__libsndfile_version__}",
        f"numpy={numpy.__version__}",
        run(["ffprobe", "-version"]).splitlines()[0],
        f"macOS={run(['sw_vers', '-productVersion'])}",
    )
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
