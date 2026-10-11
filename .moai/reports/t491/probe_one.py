import sys
from pathlib import Path

sys.path.insert(0, str(Path(".moai/reports/t501").resolve()))
import measure_ac001_8songs as m  # noqa: E402

p = Path(".moai/reports/t499/runs/Rain/analysis.json")
r = m.rehearse("Rain", p)
print("n_captured", r["n_captured"], "cues", len(r["bundle_cues"]))
for c in r["cards"]:
    print("CARD", c["answer"], "|", c["options"][:6])
for c in r["bundle_cues"][:5]:
    print(
        c.kind,
        c.cue_number,
        c.cue_name,
        c.position.stored,
        c.color.palette,
        c.color.palette_id,
        c.fx.permitted,
    )
print(str(r["reply"])[:300])
