"""t502: 감독이 본 시퀀스 212·213 의 큐 유지 시간(다음 큐 TrigTime − 이 큐 TrigTime)을 잰다.

입력: t501 쓰기 직후 콘솔 되읽기(t501_postwrite_cue_props.txt, origin/WT-ldrender-run c7b231cd).
읽기 전용 — 콘솔에 아무것도 보내지 않는다.
"""

import json
import re
import sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("t501_postwrite_cue_props.txt"))
rows: dict[str, list[tuple[float, str]]] = {}
for m in re.finditer(r"<<< (\{.*\})", src.read_text()):
    d = json.loads(m.group(1))
    seq = d["path"].split("/")[-2]
    r = {x["n"]: x.get("v") for x in d["reads"]}
    rows.setdefault(seq, []).append((float(r["TRIGTIME"]), r["NAME"]))

for seq, cues in sorted(rows.items()):
    cues.sort()
    print(f"== Sequence {seq}: cues={len(cues)}")
    holds = []
    for i, (t, name) in enumerate(cues):
        if i + 1 < len(cues):
            h = cues[i + 1][0] - t
            holds.append((h, name))
            print(f"  {t:8.3f}  {name:18s} hold={h:5.1f}s")
        else:
            print(f"  {t:8.3f}  {name:18s} hold=(last, song end unknown)")
    hs = sorted(h for h, _ in holds)
    print(
        f"  holds n={len(hs)} max={hs[-1]:.1f}s median={hs[len(hs) // 2]:.1f}s "
        f">=20s={sum(h >= 20 for h in hs)} >=10s={sum(h >= 10 for h in hs)}"
    )
    print("  verse holds:", [f"{n}={h:.1f}s" for h, n in holds if n.startswith("Verse")])
