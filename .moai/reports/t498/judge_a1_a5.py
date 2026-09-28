"""t498 — 가짜 콘솔 리허설 2회에서 A1~A5 를 판정한다(읽기만, 콘솔 접촉 0).

실행: uv run python .moai/reports/t498/judge_a1_a5.py <run1 폴더> <run2 폴더>
"""

import json
import sys
from collections import Counter
from pathlib import Path

R1, R2 = Path(sys.argv[1]), Path(sys.argv[2])


def lines(p):
    return p.read_text("utf-8").splitlines()


for r in (R1, R2):
    a = json.loads((r / "analysis.json").read_text("utf-8"))
    sel = [s for s in a["sections"] if s["selected"]]
    print(
        f"A1 {r.name}: bpm={a['bpm']} source={a['bpm_source']} "
        f"sections={len(a['sections'])} selected={len(sel)}"
    )

ev = json.loads((R1 / "events.json").read_text("utf-8"))
print("event types:", Counter(e.get("type") for e in ev if isinstance(e, dict)))
for e in ev:
    if not isinstance(e, dict):
        continue
    for holder in (e, e.get("timeline") or {}, e.get("payload") or {}):
        rep = holder.get("concept_report") if isinstance(holder, dict) else None
        if isinstance(rep, dict) and rep.get("gates"):
            # 키는 "passed"(bool). True 가 아닌 것은 None 을 포함해 전부 미통과로 센다 —
            # 없는 키를 「FAIL 아님」으로 읽는 공허 판정을 막는다(1차 판정기가 그랬다).
            verdicts = {k: v.get("passed") for k, v in rep["gates"].items()}
            fails = [k for k, v in verdicts.items() if v is not True]
            passed = len(verdicts) - len(fails)
            print(f"A2 gates={len(verdicts)} passed={passed} not_passed={fails}")

for name in ("console_commands_approved.txt", "console_commands_sent.txt"):
    same = (R1 / name).read_bytes() == (R2 / name).read_bytes()
    print(f"A3 {name}: run1==run2 bytes {same} ({len(lines(R1 / name))} lines)")

approved = lines(R1 / "console_commands_approved.txt")
sent = lines(R1 / "console_commands_sent.txt")
print(f"A4 approved={len(approved)} sent={len(sent)} diff={len(sent) - len(approved)}")
extra = [x for x in sent if x not in approved]
missing = [x for x in approved if x not in sent]
print(f"A5 sent-not-approved={len(extra)} {extra[:10]}")
print(f"   approved-not-sent={len(missing)} {missing[:10]}")
print("order equal:", sent == approved)
risky = [
    x for x in approved if x.startswith(("Store Preset", "Delete", "ClearAll")) or "Overwrite" in x
]
print("preset store / delete / clearall lines in approved:", len(risky), risky[:10])
seqs = sorted({x.split()[2] for x in approved if x.startswith("Store Sequence")})
print("sequence numbers:", seqs)
print("timecode lines:", [x for x in approved if "Timecode" in x])
refs = sorted(
    {
        toks[i + 1]
        for x in approved
        for toks in [x.split()]
        for i, t in enumerate(toks[:-1])
        if t == "Preset"
    }
)
print("preset refs:", refs)
