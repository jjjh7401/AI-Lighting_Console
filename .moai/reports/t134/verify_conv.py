import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-col.csv"
MA3 = ROOT / "src/Lighting_Designer/04_grandMA3/LXSEQ_SAMPLE_01_Sugar_r3.ma3.txt"
GEN = ROOT / "src/Lighting_Designer/90_빌드파이프라인/make_ma3.py"

sheet = dict()
for row in csv.DictReader(CSV.open(encoding="utf-8-sig")):
    m = re.search(r"R(\d+)\s+G(\d+)\s+B(\d+)", row["Value"])
    sheet[row["ID"]] = tuple(int(x) for x in m.groups()) if m else None
have = sum(1 for v in sheet.values() if v)
print("시트 행 수:", len(sheet), "| RGB 있는 행:", have, "| RGB 없는 행:", len(sheet) - have)

src = GEN.read_text(encoding="utf-8")
pairs = re.findall(r'"(COL\.\d+)":\s*\((\d+,\d+,\d+)\)', src)
gen = dict((k, tuple(int(x) for x in v.split(","))) for k, v in pairs)
gen_none = re.findall(r'"(COL\.\d+)":\s*None', src)
print("생성기 RGB 항목:", len(gen), "| None 항목:", len(gen_none), gen_none)

mismatch = [k for k in sorted(sheet) if sheet[k] != gen.get(k)]
print("시트 vs 생성기 하드코딩 불일치:", mismatch if mismatch else "없음 (전 8행 일치)")

block = MA3.read_text(encoding="utf-8").split("컬러 프리셋")[1].split("포지션 프리셋")[0]
emitted = dict()
cur = []
for line in block.splitlines():
    m = re.match(r'Attribute "ColorRGB_([RGB])" At ([\d.]+)', line.strip())
    if m:
        cur.append(float(m.group(2)))
    m2 = re.search(r'Store Preset \d+\.\d+ "(COL\.\d+)', line)
    if m2:
        emitted[m2.group(1)] = tuple(cur) if cur else None
        cur = []
withval = sum(1 for v in emitted.values() if v)
print("ma3.txt COL 저장 행:", len(emitted), "| 값 실린 행:", withval)

print("")
print("ID | 시트 0-255 | ma3.txt 방출 | round(r/255*100,1) | 일치")
ok = 0
for k in sorted(sheet):
    rgb = sheet[k]
    em = emitted.get(k)
    if rgb is None:
        print(k, "| (RGB 없음) |", em, "| - | 값 미방출:", "맞음" if em is None else "어긋남")
        continue
    calc = tuple(round(v / 255 * 100, 1) for v in rgb)
    ok = ok + (1 if em == calc else 0)
    print(k, "|", rgb, "|", em, "|", calc, "|", "예" if em == calc else "아니오")
print("")
print("선형(x100/255, 소수 1자리)로 방출값이 재현된 행:", ok, "/", have)
