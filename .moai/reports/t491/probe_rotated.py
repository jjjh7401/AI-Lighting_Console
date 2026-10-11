import sys
from pathlib import Path

sys.path.insert(0, str(Path(".moai/reports/t491").resolve()))
import measure_look_reuse as t  # noqa: E402

t._install_capture()
session, q = t._new_session()
p = Path(".moai/reports/t499/runs/Cut and Run/analysis.json")
row = t._run_song(session, q, "Cut and Run", p, 1, 1)
for c in q.log:
    print("CARD", repr(c["answer"]), "|", c["options"][:6])
print(len(row["cues"]))
reply = session.run_instruction  # noqa
