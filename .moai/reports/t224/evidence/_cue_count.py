import json
import re
from pathlib import Path

EIGHT = ["Q010", "Q020", "Q040", "Q050", "Q080", "Q090", "Q110", "Q130"]

for tag, path in (
    ("BEFORE (조인 수리 전)", ".moai/reports/t224/evidence/cues_preview_after_pos.json"),
    ("AFTER  (조인 수리 후)", ".moai/reports/t224/evidence/cues_preview_after_join_fix.json"),
):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    p = d["tool"]["payload"] if "payload" in d["tool"] else d["tool"]
    planned = [c["cue_no"] for c in p["planned_cues"]]
    held = p["held"]
    held_cues = sorted(set(h["cue_no"] for h in held))
    detail = p.get("refusal_detail") or ""
    kinds = sorted(set(re.findall(r"프리셋 ((?:POS|COL|BM|FX|DIM)\.\d+)", detail)))
    print(tag)
    print("  preset_slots_resolved:", p["preset_slots_resolved"])
    print("  refusal:", p["refusal"])
    print("  planned_cues:", planned)
    print("  held rows:", len(held), "  held cues:", held_cues)
    print("  여덟 중 planned:", [q for q in EIGHT if q in planned])
    print("  여덟 중 held  :", [q for q in EIGHT if q in held_cues])
    print("  미해결 프리셋:", kinds)
    print()
