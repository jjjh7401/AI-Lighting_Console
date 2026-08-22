# -*- coding: utf-8 -*-
"""MA3 생성 스크립트 정합 검증 (M1~M5)"""
import sys, os, re, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig_data import GROUPS, PRESET_DIM, PRESET_COL, PRESET_POS, PRESET_BM, FX_LIB
from seq_data import CUES

TXT = "/home/claude/plugin-run/out/LXSEQ_SAMPLE_01_Sugar_r3.ma3.txt"
XMLF = "/home/claude/plugin-run/out/LXSEQ_SAMPLE_01_Sugar_r3.macros.xml"
lines = open(TXT, encoding="utf-8").read().splitlines()
cmds = [l for l in lines if l and not l.startswith("//")]

R = []
def chk(n, name, ok, detail): R.append((n, name, ok, detail))

# M1: Group "X" 참조가 전부 RIG GROUP 정의
gnames = {g[1] for g in GROUPS}
refs = {m for l in cmds for m in re.findall(r'Group "([^"]+)"', l)}
badg = sorted(refs - gnames)
chk("M1", 'Group 참조 ⊆ RIG GROUP', not badg, str(badg) if badg else "%d개 그룹 참조 전부 유효" % len(refs))

# M2: At Preset p.n 참조가 정의된 풀·번호 내
POOL = {"DIM": 1, "POS": 2, "COL": 4, "BM": 21, "FX": 22}
counts = {1: len(PRESET_DIM), 2: len(PRESET_POS), 4: len(PRESET_COL), 21: len(PRESET_BM), 22: len(FX_LIB)}
badp = []
for l in cmds:
    for p, n in re.findall(r'At Preset (\d+)\.(\d+)', l):
        p, n = int(p), int(n)
        if p not in counts or n < 1 or n > counts[p]:
            badp.append("%d.%d" % (p, n))
chk("M2", "Preset 참조 풀·번호 유효", not badp, str(sorted(set(badp))) if badp else "풀 매핑 {DIM:1, POS:2, COL:4, BM:21, FX:22} 내 전부 유효")

# M3: Store Cue 개수·번호 = CUES와 일치
stored = [int(m) for l in cmds for m in re.findall(r'Store Cue (\d+) ', l)]
expect = [int(c[0][1:]) for c in CUES]
chk("M3", "Store Cue 번호 = CUE 시트", stored == expect,
    "누락/불일치 %s" % (set(expect) ^ set(stored)) if stored != expect else "%d큐 (10~180) 순서 일치" % len(stored))

# M4: SNAP 큐는 CueFade 0.0
snapq = {int(c[0][1:]) for c in CUES if c[10] == "SNAP"}
badf = []
for l in cmds:
    m = re.search(r'Store Cue (\d+) .*CueFade ([\d.]+)', l)
    if m and int(m.group(1)) in snapq and float(m.group(2)) != 0.0:
        badf.append(m.group(1))
chk("M4", "SNAP 큐 CueFade 0.0", not badf, str(badf) if badf else "SNAP %d큐 전부 0.0" % len(snapq))

# M5: 매크로 XML 파싱 가능 + 명령 수 일치
try:
    root = ET.parse(XMLF).getroot()
    xml_cmds = [ml.get("Command") for ml in root.iter("MacroLine")]
    ok = len(xml_cmds) == len(cmds)
    chk("M5", "매크로 XML 유효 · 명령 수 일치", ok,
        "XML %d vs TXT %d" % (len(xml_cmds), len(cmds)) if not ok else
        "%d매크로 · %d명령 · XML 파싱 OK" % (len(list(root.iter('Macro'))), len(xml_cmds)))
except Exception as e:
    chk("M5", "매크로 XML 유효", False, str(e))

w = max(len(x[1]) for x in R)
print("=" * 86)
print("MA3 생성 스크립트 정합 검증 — ma3.txt + macros.xml")
print("=" * 86)
fails = 0
for n, name, ok, d in R:
    s = "PASS" if ok else "FAIL"
    if not ok: fails += 1
    print("%s. %-*s  %s  %s" % (n, w, name, s, d))
print("-" * 86)
print("결과: %d/%d PASS" % (len(R) - fails, len(R)) + ("" if fails == 0 else "  ← FAIL %d건" % fails))
sys.exit(1 if fails else 0)
