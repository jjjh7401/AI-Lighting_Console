import sys
sys.path.insert(0, ".")
from server.tests.test_chorus_color_two_paths_t441 import TestToolsetWiring, _RecordsPort, _records
t = TestToolsetWiring()
out = {}
for label, port in (("none", None), ("modulate", _RecordsPort(_records("modulate")))):
    reg = t._registry(interview_records=port) if port else t._registry()
    ex, payload = t._dispatch(reg)
    out[label] = payload["commands"]
    print(label, out[label][:12])
diff = [(a, b) for a, b in zip(out["none"], out["modulate"]) if a != b]
print("differing commands:", len(diff))
for a, b in diff: print(" -", a["command"]); print(" +", b["command"])
