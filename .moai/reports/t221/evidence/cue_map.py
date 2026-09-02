import csv
import io
import pathlib

p = pathlib.Path("src/Lighting_Designer/03_곡파일_Sugar/LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv")
rows = list(csv.DictReader(io.StringIO(p.read_text("utf-8-sig"))))
fail = ("POS.02", "POS.03", "POS.04")
cues_fail = set()
cues_ok = set()
allq = set()
for row in rows:
    q = (row.get("Q#") or "").strip()
    if q:
        allq.add(q)
    v = (row.get("POS") or "").strip()
    if not v:
        continue
    print(q, "|", (row.get("Group") or "").strip(), "| POS=" + v)
    if v in fail:
        cues_fail.add(q)
    else:
        cues_ok.add(q)
print()
print("cues touching a FAILING POS:", sorted(cues_fail), len(cues_fail))
print("cues touching only OK POS:", sorted(cues_ok - cues_fail), len(cues_ok - cues_fail))
print("total distinct cues:", len(allq))
