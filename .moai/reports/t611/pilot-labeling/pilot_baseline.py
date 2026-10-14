"""기준선 측정 — 지금 시스템이 실제 곡에서 무엇을 내놓는가.

저장소의 실제 코드(analyze + _infer_confirmed_role + _confirmed_section_names)를
그대로 불러 쓴다. 재구현하지 않는다 — 재구현하면 지금 동작이 아니라 내 해석을
재는 것이 된다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from server.audio.analyze import analyze  # noqa: E402
from server.web.session import _confirmed_section_names, _infer_confirmed_role  # noqa: E402

MUSIC = Path("/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample music")


def ms(v: int) -> str:
    return f"{v // 60000}:{(v % 60000) // 1000:02d}"


def main() -> None:
    out = []
    for path in sorted(MUSIC.iterdir()):
        if path.suffix.lower() not in {".mp3", ".wav", ".m4a", ".flac"}:
            continue
        result = analyze(path.read_bytes())
        if not hasattr(result, "d_candidates"):
            out.append({"song": path.name, "error": getattr(result, "reason", "unknown")})
            print(f"[FAIL] {path.name}: {getattr(result, 'reason', '?')}", flush=True)
            continue

        cands = list(result.d_candidates)
        d_levels = [c.d_level for c in cands]
        roles = [_infer_confirmed_role(i, d_levels) for i in range(len(d_levels))]
        names = _confirmed_section_names(roles)

        song = {
            "song": path.name,
            "bpm": round(result.bpm, 1),
            "bpm_confidence": round(result.bpm_confidence, 3),
            "duration_ms": cands[-1].end_ms if cands else 0,
            "n_sections": len(cands),
            "sections": [
                {
                    "i": i,
                    "start": ms(c.start_ms),
                    "end": ms(c.end_ms),
                    "dur_s": round((c.end_ms - c.start_ms) / 1000, 1),
                    "d": c.d_level,
                    "baseline_name": names[i],
                }
                for i, c in enumerate(cands)
            ],
        }
        out.append(song)
        print(f"[OK] {path.name}: {len(cands)}구간, BPM {song['bpm']}", flush=True)

    dest = ROOT / "pilot_baseline.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {dest}")


if __name__ == "__main__":
    main()
