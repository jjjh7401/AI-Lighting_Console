"""MA3 생성 스크립트 정합 검증 (M1~M5)"""

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 입력 위치는 이 스크립트 위치에서 유도한다. 기계마다 다른 절대경로를
# 박아두면 그 기계 밖에서는 돌지 않는다.
MA3_DIR = os.environ.get("LXSEQ_MA3_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "04_grandMA3"
)
from rig_data import FX_LIB, GROUPS, PRESET_BM, PRESET_COL, PRESET_DIM, PRESET_POS
from seq_data import CUES

TXT = os.path.join(MA3_DIR, "LXSEQ_SAMPLE_01_Sugar_r3.ma3.txt")
XMLF = os.path.join(MA3_DIR, "LXSEQ_SAMPLE_01_Sugar_r3.macros.xml")
with open(TXT, encoding="utf-8") as _fh:
    lines = _fh.read().splitlines()
cmds = [line for line in lines if line and not line.startswith("//")]

R = []


def chk(n, name, ok, detail):
    R.append((n, name, ok, detail))


# M1: Group "X" 참조가 전부 RIG GROUP 정의
gnames = {g[1] for g in GROUPS}
refs = {m for line in cmds for m in re.findall(r'Group "([^"]+)"', line)}
badg = sorted(refs - gnames)
chk(
    "M1",
    "Group 참조 ⊆ RIG GROUP",
    not badg,
    str(badg) if badg else "%d개 그룹 참조 전부 유효" % len(refs),
)

# M2: At Preset p.n 참조가 정의된 풀·번호 내
POOL = {"DIM": 1, "POS": 2, "COL": 4, "BM": 21, "FX": 22}
counts = {
    1: len(PRESET_DIM),
    2: len(PRESET_POS),
    4: len(PRESET_COL),
    21: len(PRESET_BM),
    22: len(FX_LIB),
}
badp = []
for line in cmds:
    for p, n in re.findall(r"At Preset (\d+)\.(\d+)", line):
        p, n = int(p), int(n)
        if p not in counts or n < 1 or n > counts[p]:
            badp.append("%d.%d" % (p, n))
chk(
    "M2",
    "Preset 참조 풀·번호 유효",
    not badp,
    str(sorted(set(badp))) if badp else "풀 매핑 {DIM:1, POS:2, COL:4, BM:21, FX:22} 내 전부 유효",
)

# M3: Store Cue 개수·번호 = CUES와 일치
# 개별 타이밍이 그룹마다 다른 큐는 파트로 갈린다(t215). 파트 저장은 큐를 새로
# 만들지 않으므로 큐 목록에서 빼고 세되, 그 번호가 실재 큐인지는 따로 본다.
stored = [int(m) for line in cmds for m in re.findall(r"Store Cue (\d+) (?!Part )", line)]
parts = [int(m) for line in cmds for m in re.findall(r"Store Cue (\d+) Part \d+ ", line)]
expect = [int(c[0][1:]) for c in CUES]
orphan = sorted(set(parts) - set(expect))
chk(
    "M3",
    "Store Cue 번호 = CUE 시트",
    stored == expect and not orphan,
    f"누락/불일치 {set(expect) ^ set(stored)} · 고아 파트 {orphan}"
    if (stored != expect or orphan)
    else "%d큐 (10~180) 순서 일치 · 파트 %d개 전부 실재 큐" % (len(stored), len(parts)),
)

# M4: SNAP 큐는 CueFade 0.0
snapq = {int(c[0][1:]) for c in CUES if c[10] == "SNAP"}
badf = []
for line in cmds:
    m = re.search(r"Store Cue (\d+) .*CueFade ([\d.]+)", line)
    if m and int(m.group(1)) in snapq and float(m.group(2)) != 0.0:
        badf.append(m.group(1))
chk("M4", "SNAP 큐 CueFade 0.0", not badf, str(badf) if badf else "SNAP %d큐 전부 0.0" % len(snapq))

# M5: 매크로 XML 파싱 가능 + 명령 수 일치
try:
    root = ET.parse(XMLF).getroot()
    xml_cmds = [ml.get("Command") for ml in root.iter("MacroLine")]
    ok = len(xml_cmds) == len(cmds)
    chk(
        "M5",
        "매크로 XML 유효 · 명령 수 일치",
        ok,
        "XML %d vs TXT %d" % (len(xml_cmds), len(cmds))
        if not ok
        else "%d매크로 · %d명령 · XML 파싱 OK" % (len(list(root.iter("Macro"))), len(xml_cmds)),
    )
except Exception as e:
    chk("M5", "매크로 XML 유효", False, str(e))

w = max(len(x[1]) for x in R)
print("=" * 86)
print("MA3 생성 스크립트 정합 검증 — ma3.txt + macros.xml")
print("=" * 86)
fails = 0
for n, name, ok, d in R:
    s = "PASS" if ok else "FAIL"
    if not ok:
        fails += 1
    print("%s. %-*s  %s  %s" % (n, w, name, s, d))
print("-" * 86)
print(
    "결과: %d/%d PASS" % (len(R) - fails, len(R)) + ("" if fails == 0 else "  ← FAIL %d건" % fails)
)
sys.exit(1 if fails else 0)
