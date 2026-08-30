import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
CSV = ROOT / "src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-col.csv"

from server.web.session import COLOR_PALETTE_SEQUENCE as PAL  # noqa: E402

print("팔레트 원천: server.web.session.COLOR_PALETTE_SEQUENCE ( 손 사본 아님 )")
print("팔레트 색 수:", len(PAL))

rows = []
for row in csv.DictReader(CSV.open(encoding="utf-8-sig")):
    m = re.search(r"R(\d+)\s+G(\d+)\s+B(\d+)", row["Value"])
    rgb = tuple(int(x) for x in m.groups()) if m else None
    rows.append((row["ID"], row["Name"], rgb))

print("")
print("=== 값 대조: 시트 RGB 를 x100/255 로 옮긴 뒤 팔레트 10색과 정확 일치하는가 ===")
exact = 0
converted = 0
for rid, name, rgb in rows:
    if rgb is None:
        print(rid, name, "| RGB 없음 - 값 대조 대상 아님")
        continue
    converted = converted + 1
    conv = tuple(round(v / 255 * 100, 1) for v in rgb)
    hit = [p for p, prgb in PAL if tuple(float(c) for c in prgb) == conv]
    best = min(PAL, key=lambda e: max(abs(c - p) for c, p in zip(conv, e[1], strict=True)))
    dist = max(abs(c - p) for c, p in zip(conv, best[1], strict=True))
    if hit:
        exact = exact + 1
    print(
        rid,
        name,
        "|",
        rgb,
        "->",
        conv,
        "| 정확 일치:",
        hit if hit else "없음",
        "| 최근접:",
        best[0],
        best[1],
        "| 최대 축차:",
        round(dist, 1),
    )
print("")
print("정확 일치한 행:", exact, "/", converted)

print("")
print("=== 이름 대조: 시트 이름이 팔레트 라벨과 대응하는가 ===")
palnames = [p for p, _ in PAL]
print("팔레트 라벨:", palnames)
for rid, name, rgb in rows:
    base = name.split(" (")[0].strip()
    print(rid, "|", base, "| RGB:", "있음" if rgb else "없음")
