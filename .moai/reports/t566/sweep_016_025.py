import re

with open(".moai/specs/SPEC-LDBEAT-001/spec.md", encoding="utf-8") as f:
    text = f.read()

rows = {}
for n in range(16, 26):
    key = f"REQ-LDBEAT-0{n}" if n < 100 else f"REQ-LDBEAT-{n}"
    start = f"| {key} |"
    i = text.find(start)
    if i == -1:
        continue
    nxt_n = n + 1
    nxt_key = f"REQ-LDBEAT-0{nxt_n}" if nxt_n < 100 else f"REQ-LDBEAT-{nxt_n}"
    j = text.find(f"\n| {nxt_key} |", i)
    if j == -1:
        j = text.find("\n\n## 4.", i)
    row = text[i:j]
    # requirement cell is between the first and second top-level '|'
    # (the row itself starts with "| KEY | requirement-cell | evidence-cell |")
    parts = row.split(" | ", 2)
    req_cell = parts[1] if len(parts) > 1 else row
    rows[key] = req_cell

splitter = re.compile(r"(?<=\.)\s+")
total_no_shall = 0
for key, cell in rows.items():
    sentences = splitter.split(cell)
    no_shall = [s.strip() for s in sentences if s.strip() and "shall" not in s]
    # drop the leading bookkeeping tag sentences (e.g. "[HARD] (a) **재교정(...)**: ..." has no own
    # period before the first shall, so it never appears standalone — safe to count all)
    if no_shall:
        print(f"{key}: {len(sentences)} 문장 중 shall 부재 {len(no_shall)}")
        for s in no_shall:
            print("    -", s[:160])
    total_no_shall += len(no_shall)

print(f"REQ-LDBEAT-016~025 합계 shall 부재 문장: {total_no_shall}")
