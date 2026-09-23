"""t443 탐침 — 샘플 폴더(git 밖) 곡 전부를 고친 analyze() 로 다시 판정한다."""

import io
import pathlib
import sys

import soundfile

sys.path.insert(0, ".")
from server.audio.analyze import (  # noqa: E402
    AnalysisResult,
    _mp3_length_is_a_bitrate_guess,
    analyze,
)

folder = pathlib.Path(sys.argv[1])
for path in sorted(folder.iterdir()):
    if path.suffix.lower() not in {".mp3", ".wav"}:
        continue
    data = path.read_bytes()
    try:
        info = soundfile.info(io.BytesIO(data))
        guess = info.format == "MP3" and _mp3_length_is_a_bitrate_guess(data)
        declared = f"{info.frames / info.samplerate:.3f}s"
    except Exception as error:  # noqa: BLE001
        guess, declared = None, f"info 실패({type(error).__name__})"
    outcome = analyze(data)
    if isinstance(outcome, AnalysisResult):
        verdict = f"AnalysisResult bpm={outcome.bpm:.2f}"
    else:
        verdict = f"AnalysisFailure: {outcome.reason[:70]}"
    print(f"{path.name:32s} declared={declared:18s} guess={guess!s:5s} -> {verdict}")
