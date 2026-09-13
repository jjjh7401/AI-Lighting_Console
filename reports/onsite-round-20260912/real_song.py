"""감독이 준 실제 곡으로 1단계를 재측정한다. 콘솔 접촉 0."""

import sys
from pathlib import Path

from server.audio.analyze import AnalysisFailure, AnalysisResult, analyze

path = Path(sys.argv[1])
raw = path.read_bytes()
print(f"곡: {path.name}  {len(raw):,} bytes")

out = analyze(raw)
if isinstance(out, AnalysisFailure):
    print("🔴 분석 실패:", out.reason)
    raise SystemExit(1)

assert isinstance(out, AnalysisResult)
print(f"BPM {out.bpm:.2f} (신뢰도 {out.bpm_confidence:.3f})")
print(f"온셋 {len(out.onsets_ms)}개")
print(f"구간 후보 {len(out.d_candidates)}개")
for i, c in enumerate(out.d_candidates, 1):
    dur = (c.end_ms - c.start_ms) / 1000
    print(
        f"  {i:2}  {c.start_ms / 1000:7.1f}s ~ {c.end_ms / 1000:7.1f}s  ({dur:5.1f}s)  D{c.d_level}"
    )
