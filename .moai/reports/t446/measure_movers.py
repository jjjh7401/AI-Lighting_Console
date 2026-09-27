"""t446 — 8곡에서 절 큐의 무버 상태와 MIB 판정을 변경 전·후로 센다.

명령: uv run python .moai/reports/t446/measure_movers.py before <density_c4506a7c.py>
      uv run python .moai/reports/t446/measure_movers.py after
before 의 파일은 `git show c4506a7c:server/concept/density.py` 로 뜬 것이다.
"""

import importlib.util
import json
import sys
from collections import Counter

if sys.argv[1] == "before":
    spec = importlib.util.spec_from_file_location("server.concept.density", sys.argv[2])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["server.concept.density"] = mod
    spec.loader.exec_module(mod)

from server.concept.density import MOVER_GROUPS  # noqa: E402
from server.concept.gates import build_song  # noqa: E402

with open("server/tests/fixtures/pilot_baseline.json", encoding="utf-8") as f:
    songs = [s for s in json.load(f) if "error" not in s]

total: Counter[str] = Counter()
for s in songs:
    b = build_song(s)
    verse: Counter[str] = Counter()
    for row, st in zip(b.rows, b.states, strict=True):
        if row["kind"] == "section" and row["section"] == "Verse":
            lv = sorted({st.dim.get(m, 0) for m in MOVER_GROUPS})
            verse["on" if lv != [0] else "off"] += 1
            verse[f"lvl{lv}"] += 1
    mib = Counter(v.status for v in b.mib if v is not None)
    total.update({f"verse_{k}": v for k, v in verse.items()})
    total.update({f"mib_{k}": v for k, v in mib.items()})
    print(f"{b.song[:28]:28} | verse {dict(verse)} | mib {dict(mib)}")
print("합계:", dict(sorted(total.items())))
