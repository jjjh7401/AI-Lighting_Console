"""t498 — A7: 콘솔에서 직접 읽은 큐 속성(run8) 대 승인 목록의 이름·TrigType·TrigTime(±0.001초).

실행: uv run python .moai/reports/t498/judge_a7.py \
      <승인 목록.txt> <run8_cue_props.txt> <run7 판독.txt>
"""

import json
import re
import sys
from pathlib import Path

APPROVED, PROPS, STATE = (Path(p) for p in sys.argv[1:4])
lines = APPROVED.read_text("utf-8").splitlines()

want: dict[str, dict] = {}
for x in lines:
    if m := re.match(r"^Store Sequence 211 Cue ([\d.]+) '([^']*)'", x):
        want.setdefault(m.group(1), {})["name"] = m.group(2)
    elif m := re.match(r"^Set Cue ([\d.]+) Sequence 211 Property '(\w+)' '?([^']*)'?$", x):
        want.setdefault(m.group(1), {})[m.group(2).upper()] = m.group(3)
print("approved cues:", len(want), "props per cue:", sorted({k for v in want.values() for k in v}))

state = STATE.read_text("utf-8").split(">>> state:ShowData/DataPools/Default/Sequences/211\n")[1]
children = json.loads(re.search(r"<<< (\{.*\})", state).group(1))["children"]
slot_to_cue = {c["i"]: c["cueNo"] for c in children if "cueNo" in c and c["cueNo"] != 0}

got = {}
for block in PROPS.read_text("utf-8").split(">>> ")[1:]:
    m = re.search(r"<<< (\{.*\})", block)
    if not m:
        continue
    d = json.loads(m.group(1))
    slot = int(d["path"].rsplit("/", 1)[1])
    vals = {r["n"]: r.get("v") for r in d.get("reads", []) if r.get("ok")}
    cue = slot_to_cue[slot]
    got[f"{cue:g}"] = vals

match = 0
for cue, w in sorted(want.items(), key=lambda kv: float(kv[0])):
    g = got.get(f"{float(cue):g}", {})
    name_ok = g.get("NAME") == w.get("name")
    type_ok = w.get("TRIGTYPE") is None or g.get("TRIGTYPE") == w.get("TRIGTYPE")
    t_want, t_got = w.get("TRIGTIME"), g.get("TRIGTIME")
    time_ok = (t_want is None and t_got is None) or (
        t_want is not None and t_got is not None and abs(float(t_want) - float(t_got)) <= 0.001
    )
    ok = name_ok and type_ok and time_ok
    match += ok
    print(
        f"cue {cue}: name {g.get('NAME')!r} want {w.get('name')!r} | "
        f"type {g.get('TRIGTYPE')} want {w.get('TRIGTYPE')} | "
        f"time {t_got} want {t_want} | {'OK' if ok else 'MISMATCH'}"
    )
print(f"A7 match {match} / {len(want)} (console cues read: {len(got)})")
