"""RIG 팩 검증 (R1~R6) + 곡 파일 상호참조 (R7~R8)"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exec_data
from rig_data import (
    FID_BASE,
    FIXTURES,
    FX_LIB,
    GROUPS,
    PRESET_BM,
    PRESET_COL,
    PRESET_DIM,
    PRESET_POS,
    UNIVERSE_PLAN,
)

R = []


def chk(n, name, ok, detail):
    R.append((n, name, ok, detail))


FIX = {f[0]: f for f in FIXTURES}

# 패치 재계산 (make_rig와 동일 로직)
patch = []
for uni, groups, desc in UNIVERSE_PLAN:
    addr = 1
    for g in groups:
        ch, cnt = FIX[g][3], FIX[g][4]
        for i in range(cnt):
            patch.append((FID_BASE[g] + i, g, uni, addr, addr + ch - 1))
            addr += ch

# R1: FID 고유성
fids = [p[0] for p in patch]
dup = sorted({f for f in fids if fids.count(f) > 1})
chk("R1", "FID 고유성", not dup, (f"중복 {dup}") if dup else "%d대 전부 고유" % len(fids))

# R2: 주소 충돌·512 초과
bad = []
for uni in {p[2] for p in patch}:
    spans = sorted((p[3], p[4], p[0]) for p in patch if p[2] == uni)
    for i in range(1, len(spans)):
        if spans[i][0] <= spans[i - 1][1]:
            bad.append(("U%d" % uni, "겹침", spans[i][2]))
    if spans and spans[-1][1] > 512:
        bad.append(("U%d" % uni, "512 초과", spans[-1][1]))
chk(
    "R2",
    "주소 무충돌 · 512ch 이내",
    not bad,
    str(bad[:3])
    if bad
    else " · ".join(
        "U%d %dch" % (u, max(p[4] for p in patch if p[2] == u))
        for u in sorted({p[2] for p in patch})
    ),
)

# R3: 풋프린트 산술 (그룹 총 ch = ch × 수량)
errs = [
    g
    for g in FIX
    if FIX[g][3] > 0 and sum(p[4] - p[3] + 1 for p in patch if p[1] == g) != FIX[g][3] * FIX[g][4]
]
chk("R3", "풋프린트 산술 정합", not errs, str(errs) if errs else "전 그룹 ch×수량 일치")

# R4: 유니버스 계획이 DMX 장비 전부 커버
planned = {g for _, gs, _ in UNIVERSE_PLAN for g in gs}
dmx = {f[0] for f in FIXTURES if f[3] > 0}
miss = sorted(dmx - planned)
chk(
    "R4",
    "DMX 장비 유니버스 배치 완전성",
    not miss,
    str(miss) if miss else "%d개 DMX 그룹 전부 배치" % len(dmx),
)

# R5: GROUP 시트 구성 그룹이 FIXTURE에 존재
gnames = {g[1] for g in GROUPS}
base = {f[0] for f in FIXTURES}
derived = {"ALL", "SIDE-ALL", "WASH-ALL", "MOVER-ALL", "ODD", "EVEN"}
badg = sorted(g for g in gnames if g not in base and g not in derived)
chk(
    "R5",
    "GROUP 정의 유효성",
    not badg,
    str(badg)
    if badg
    else "%d그룹 (기본 %d + 파생 %d)" % (len(gnames), len(gnames & base), len(gnames & derived)),
)

# R6: 프리셋 ID 고유성
pids = [p[0] for p in PRESET_DIM + PRESET_COL + PRESET_POS + PRESET_BM + FX_LIB]
dupp = sorted({p for p in pids if pids.count(p) > 1})
chk("R6", "프리셋 ID 고유성", not dupp, str(dupp) if dupp else "%d개 프리셋 고유" % len(pids))

# R7: 곡 파일(CUE-EX) 그룹이 RIG GROUP에 존재
song_groups = {r[1] for r in exec_data.CUE_EX}
badsg = sorted(g for g in song_groups if g not in gnames and g != "LED-W")
chk(
    "R7",
    "Sugar CUE-EX 그룹 ⊆ RIG GROUP",
    not badsg,
    str(badsg) if badsg else "%d그룹 매핑 (LED-W는 영상팀 관할 예외)" % len(song_groups),
)

# R8: 곡 파일 프리셋 참조가 RIG 프리셋에 존재 (COL/POS/BM/FX)
rig_pids = set(pids)
badp = sorted(
    {
        v
        for r in exec_data.CUE_EX
        for v in (r[3], r[4], r[5], r[6])
        if v not in ("", "OFF") and v not in rig_pids
    }
)
chk(
    "R8",
    "Sugar 프리셋 참조 ⊆ RIG 프리셋",
    not badp,
    str(badp) if badp else "곡 파일 참조 전부 RIG에 정의",
)

w = max(len(x[1]) for x in R)
print("=" * 86)
print("LX-SEQ v2.1 RIG 팩 검증 — LXSEQ_RIG_01_ShowBase_r3 + Sugar r3 상호참조")
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
