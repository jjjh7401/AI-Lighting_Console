"""t513 — 가짜 콘솔 리허설 비교: 승인=송신 · run1=run2 · t510 송신과 번호만 다른지.

실행: python3 .moai/reports/t513/compare_fake.py
"""

from pathlib import Path

D = Path(".moai/reports/t513")
a1 = (D / "run1_fake/console_commands_approved.txt").read_text("utf-8")
s1 = (D / "run1_fake/console_commands_sent.txt").read_text("utf-8")
s2 = (D / "run2_fake/console_commands_sent.txt").read_text("utf-8")
t510 = Path(".moai/reports/t510/run1/console_commands_sent.txt").read_text("utf-8")
print("lines run1", len(s1.splitlines()), "t510", len(t510.splitlines()))
print("approved==sent", a1 == s1)
print("run1==run2", s1 == s2)
renum = s1.replace("Sequence 219", "Sequence 211").replace("Timecode 19", "Timecode 11")
pairs = enumerate(zip(renum.splitlines(), t510.splitlines(), strict=True), 1)
diff = [(i, a, b) for i, (a, b) in pairs if a != b]
print("diff_lines_vs_t510_after_renumber", len(diff))
for row in diff[:10]:
    print(row)
touched = [x for x in s1.splitlines() if "219" in x or "Timecode 19" in x]
print("lines naming 219 / Timecode 19:", len(touched))
for x in touched[:6]:
    print("  ", x[:160])
