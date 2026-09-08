# -*- coding: utf-8 -*-
"""grandMA3 프로그래밍 스크립트 생성 — RIG 팩 + Sugar CUE-EX에서 자동 전개
출력: .ma3.txt (명령 스크립트) / .macros.xml (매크로 풀 템플릿) / runbook .md
※ Store Cue 구문은 MA3 공식 도움말 기준. 프리셋 풀 번호·매크로 XML DataVersion은
  콘솔 소프트웨어 버전에서 확인 필요 (스크립트 내 [VERIFY] 표기).
"""

import sys, os, html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 출력 위치는 이 스크립트 위치에서 유도한다. 기계마다 다른 절대경로를
# 박아두면 그 기계 밖에서는 돌지 않는다.
MA3_DIR = os.environ.get("LXSEQ_MA3_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "04_grandMA3"
)
os.makedirs(MA3_DIR, exist_ok=True)
from rig_data import (
    FIXTURES,
    FID_BASE,
    GROUPS,
    PRESET_DIM,
    PRESET_COL,
    PRESET_POS,
    PRESET_BM,
    FX_LIB,
)
from exec_data import CUE_EX, SONG_BPM
from seq_data import CUES, tc

FIX = {f[0]: f for f in FIXTURES}

# ── 프리셋 풀 매핑 (MA3 기본 풀 순서 가정 — [VERIFY]) ──
# 1=Dimmer 2=Position 4=Color 5=Beam(프리즘) / BM·FX는 All-type 풀 권장
POOL = {"DIM": 1, "POS": 2, "COL": 4, "BM": 21, "FX": 22}  # 21·22 = All 풀 지정 가정


def pool_ref(pid):
    typ, num = pid.split(".")
    return "%d.%d" % (POOL[typ], int(num))


def fid_range(g):
    base, cnt = FID_BASE[g], FIX[g][4]
    return "%d Thru %d" % (base, base + cnt - 1) if cnt > 1 else str(base)


def fid_parity(parity):  # ODD/EVEN: MOVER-ALL 기준 명시 리스트
    fids = []
    for g in ("MOVER-U", "MOVER-D"):
        base, cnt = FID_BASE[g], FIX[g][4]
        fids += [base + i for i in range(cnt)]
    sel = [f for f in fids if f % 2 == (1 if parity == "ODD" else 0)]
    return " + ".join(map(str, sel))


L = []  # (section, command_or_comment, is_command)


def cmd(s):
    L.append(("C", s))


def rem(s):
    L.append(("#", "// " + s))


def sec(s):
    L.append(("S", s))


# ═══ 1. 그룹 ═══
sec("1. 그룹 생성 (Group Pool — RIG GROUP 시트와 1:1)")
rem("패치 선행 필수: FIXTURE·PATCH 시트대로 Patch 메뉴에서 완료 후 실행")
for gnum, name, comp, use in GROUPS:
    cmd("ClearAll")
    if name == "ALL":
        parts = [fid_range(f[0]) for f in FIXTURES if f[3] > 0]
        cmd("Fixture " + " + ".join(parts))
    elif name in ("SIDE-ALL",):
        cmd("Fixture %s + %s" % (fid_range("SIDE-L"), fid_range("SIDE-R")))
    elif name == "WASH-ALL":
        cmd("Fixture %s + %s" % (fid_range("WASH-U"), fid_range("WASH-D")))
    elif name == "MOVER-ALL":
        cmd("Fixture %s + %s" % (fid_range("MOVER-U"), fid_range("MOVER-D")))
    elif name in ("ODD", "EVEN"):
        cmd("Fixture " + fid_parity(name))
    else:
        cmd("Fixture " + fid_range(name))
    cmd('Store Group %d "%s" /Overwrite /NoConfirm' % (gnum, name))
cmd("ClearAll")

# ═══ 2. 딤머 프리셋 ═══
sec("2. 딤머 프리셋 (Pool %d Dimmer)" % POOL["DIM"])
for i, (pid, name, lvl, use) in enumerate(PRESET_DIM, start=1):
    cmd("ClearAll")
    cmd('Group "ALL"')
    cmd("At %s" % lvl.rstrip("%"))
    cmd('Store Preset %d.%d "%s %s" /Universal /Overwrite /NoConfirm' % (POOL["DIM"], i, pid, name))
cmd("ClearAll")

# ═══ 3. 컬러 프리셋 ═══
sec("3. 컬러 프리셋 (Pool %d Color — RGB는 %% 단위 환산값)" % POOL["COL"])
RGB = {
    "COL.01": (255, 180, 60),
    "COL.02": None,
    "COL.03": None,
    "COL.04": (255, 60, 158),
    "COL.05": (90, 43, 200),
    "COL.06": (46, 216, 216),
    "COL.07": (255, 106, 40),
    "COL.08": (30, 60, 255),
}
CCT = {"COL.02": 3200, "COL.03": 5600}
for pid, name, absval, use in PRESET_COL:
    n = int(pid.split(".")[1])
    cmd("ClearAll")
    cmd('Group "ALL"')
    if RGB.get(pid):
        r, g, b = RGB[pid]
        cmd('Attribute "ColorRGB_R" At %.1f' % (r / 255 * 100))
        cmd('Attribute "ColorRGB_G" At %.1f' % (g / 255 * 100))
        cmd('Attribute "ColorRGB_B" At %.1f' % (b / 255 * 100))
    else:
        rem("[MANUAL] %s = CCT %dK — 기종별 CTO/화이트 채널로 설정 후 저장" % (pid, CCT[pid]))
    cmd(
        'Store Preset %d.%d "%s %s" /Universal /Overwrite /NoConfirm'
        % (POOL["COL"], n, pid, name.split(" (")[0])
    )
cmd("ClearAll")

# ═══ 4. 포지션 프리셋 (현장 레코드) ═══
sec("4. 포지션 프리셋 (Pool %d Position — 현장 레코드 세션)" % POOL["POS"])
rem("[MANUAL] 각 항목: 그룹 선택 → Pan/Tilt 조준(레코드 가이드 참조) → Store 실행")
for pid, mean, grp, guide in PRESET_POS:
    n = int(pid.split(".")[1])
    g1 = grp.split("+")[0]
    rem("%s %s — 가이드: %s" % (pid, mean, guide))
    cmd('ClearAll ; Group "%s"' % g1)
    rem("  (조준 후) ↓")
    cmd('Store Preset %d.%d "%s %s" /Merge /NoConfirm' % (POOL["POS"], n, pid, mean))
cmd("ClearAll")

# ═══ 5. 빔 프리셋 ═══
sec(
    "5. 빔 프리셋 (Pool %d All-type — Zoom은 Focus 계열 어트리뷰트라 단일 피처그룹 풀에 안 담김 [VERIFY])"
    % POOL["BM"]
)
for pid, name, grp, val in PRESET_BM:
    n = int(pid.split(".")[1])
    g1 = grp.split("+")[0].replace("MOVER-ALL", "MOVER-ALL")
    cmd('ClearAll ; Group "%s"' % g1)
    rem("[MANUAL] %s: %s — Zoom/Gobo/Prism/Frost 어트리뷰트명은 기종 GDTF 기준" % (pid, val))
    cmd('Store Preset %d.%d "%s %s" /Merge /NoConfirm' % (POOL["BM"], n, pid, name))
cmd("ClearAll")

# ═══ 6. FX(Phaser) 프리셋 ═══
sec("6. FX Phaser 프리셋 (Pool %d — SpeedMaster 1 종속)" % POOL["FX"])
cmd("Store SpeedMaster 1 /NoConfirm")
cmd('Set SpeedMaster 1 Property "BPM" %d' % SONG_BPM)
rem("[VERIFY] SpeedMaster 설정 구문은 버전별 상이 — Speed 창에서 120BPM 확인")
for pid, name, attr, wave, rate, width, phase, note in FX_LIB:
    n = int(pid.split(".")[1])
    rem(
        "%s %s — %s %s · Rate %s · Width %s · Phase %s"
        % (pid, name, attr, wave, rate, width, phase)
    )
    rem("  [MANUAL] Programmer: 대상 그룹 선택 → %s 저값 입력 → Step 2 → 고값 입력" % attr)
    rem("  → Phaser 레이어에서 Speed=Rate·Phase·Width 설정 → Speed를 SpeedMaster 1 종속 →")
    cmd('Store Preset %d.%d "%s %s" /Merge /NoConfirm' % (POOL["FX"], n, pid, name))
cmd("ClearAll")

# ═══ 7. 시퀀스 + 큐 ═══
sec("7. 메인 시퀀스 — Sugar (Cue 번호 = Q# 뒤 3자리, CueFade = CUE Fade)")
cmd('Store Sequence 1 "SUGAR — Maroon5 120BPM" /NoConfirm')
cue_meta = {c[0]: c for c in CUES}
from collections import OrderedDict

by_q = OrderedDict()
for row in CUE_EX:
    by_q.setdefault(row[0], []).append(row)

# ── 개별 타이밍 → 큐 파트 (t215 실측: onPC · 응답기 1.6.2 · 2026-09-01) ──
# I/P/C/B Fade·Delay 는 큐가 아니라 큐 **파트**의 속성이다.
#   Set Cue <n> [Part <p>] Sequence <s> Property 'Preset<타입>Fade' <초>
# 프리셋 타입 번호는 콘솔에서 읽었다 — 1 Dimmer · 2 Position · 3 Gobo ·
# 4 Color · 5 Beam · 6 Focus (DataPool/PresetPools/1..6 의 name).
# 한 파트는 타입당 값을 하나만 갖는다. 그래서 같은 큐에서 값이 충돌하는
# 그룹은 파트를 갈라야 한다. 증거: .moai/reports/t215/verdict.md
TIMING_PROP = (
    ("Preset1Fade", 10),  # I  — 인텐시티 페이드
    ("Preset1Delay", 11),  # Id — 인텐시티 딜레이
    ("Preset2Fade", 12),  # P  — 포지션
    ("Preset4Fade", 13),  # C  — 컬러
    ("Preset5Fade", 14),  # B  — 빔
)


def row_timing(r):
    """행의 개별 타이밍을 속성명→값으로. 빈 칸은 담지 않는다(콘솔 기본값 CueTiming)."""
    return dict((prop, r[idx]) for prop, idx in TIMING_PROP if r[idx] not in ("", None))


def split_parts(rows):
    """값이 충돌하지 않는 그룹끼리 한 파트로 묶는다. 반환 0번이 Part 0."""
    plain, buckets = [], []
    for r in rows:
        timing = row_timing(r)
        if not timing:
            plain.append(r)  # 개별 타이밍이 없으면 큐 타이밍을 따른다
            continue
        for b_rows, b_timing in buckets:
            if all(b_timing.get(k, v) == v for k, v in timing.items()):
                b_timing.update(timing)
                b_rows.append(r)
                break
        else:
            buckets.append(([r], dict(timing)))
    return ([(plain, dict())] if plain else []) + buckets


for q, rows in by_q.items():
    meta = cue_meta[q]
    cueno = int(q[1:])
    fade = meta[11]
    label = "%s %s %s" % (q, meta[1], meta[4].split(",")[0])
    tcin = tc(meta[2])
    sec("  %s — TC %s · %s · Fade %s" % (q, tcin, meta[4], fade))
    for r in rows:
        if r[1] == "LED-W":
            rem(
                "  [영상팀 콜] LED-W %s%% — %s (조명 콘솔 큐 아님)"
                % (r[2] or "trk", r[16] or "레벨 동기")
            )
    lit_rows = [r for r in rows if r[1] != "LED-W"]
    for pi, (prows, timing) in enumerate(split_parts(lit_rows)):
        cmd("ClearAll")
        for r in prows:
            _, grp, dim, col, pos, bm, fx, rate, phase, width = r[:10]
            cmd('Group "%s"' % grp)
            if dim != "":
                cmd("At %s" % dim)
            if col not in ("",):
                cmd("At Preset %s" % pool_ref(col))
            if pos not in ("",):
                cmd("At Preset %s" % pool_ref(pos))
            if bm not in ("",):
                cmd("At Preset %s" % pool_ref(bm))
            if fx == "OFF":
                rem("  [MANUAL] %s: 기존 Phaser 정지 — Stomp 후 저장" % grp)
            elif fx != "":
                cmd("At Preset %s" % pool_ref(fx))
                rem("  %s Rate %s BPM · Phase %s · Width %s" % (fx, rate, phase, width or "—"))
        if pi == 0:
            cmd('Store Cue %d "%s" CueFade %s Sequence 1 /Merge /NoConfirm' % (cueno, label, fade))
        else:
            cmd('Store Cue %d Part %d "%s P%d" Sequence 1 /Merge /NoConfirm' % (cueno, pi, q, pi))
        if timing:
            rem("  Part %d 개별 타이밍 — %s" % (pi, ", ".join(r[1] for r in prows)))
            part = "" if pi == 0 else "Part %d " % pi
            for prop, _idx in TIMING_PROP:
                if prop in timing:
                    cmd(
                        "Set Cue %d %sSequence 1 Property '%s' %s"
                        % (cueno, part, prop, timing[prop])
                    )

# ═══ 8. 타임코드 ═══
sec("8. 타임코드 트리거 (LTC → TC Slot 1)")
rem(
    "[MANUAL] Timecode 에디터에서 Sequence 1 GO 이벤트를 아래 시각에 배치 (TC_METHOD: DERIVED — 리허설 LTC 대조 후 확정)"
)
for q in by_q:
    meta = cue_meta[q]
    rem("  Cue %-4d ← %s  (%s)" % (int(q[1:]), tc(meta[2]), meta[1]))
rem("Q180은 TC 트리거 아님 — [MANUAL] 곡 종료 확인 후 수동 GO")

# ── 출력: .ma3.txt ──────────────────────────────────────
txt_path = os.path.join(MA3_DIR, "LXSEQ_SAMPLE_01_Sugar_r3.ma3.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write("// LX-SEQ v2.1 → grandMA3 프로그래밍 스크립트 (자동 생성)\n")
    f.write("// RIG: LXSEQ_RIG_01 r3 · SONG: Sugar r3 · SpeedMaster 1 = %d BPM\n" % SONG_BPM)
    f.write("// [VERIFY] = 콘솔 버전에서 구문 확인 · [MANUAL] = 수동 작업 필요\n")
    f.write("// 실행 순서: 패치(수동) → §1 → §2 → §3 → §4(현장) → §5 → §6 → §7 → §8\n\n")
    for kind, line in L:
        if kind == "S":
            f.write("\n// ═══ %s ═══\n" % line)
        else:
            f.write(line + "\n")
ncmds = sum(1 for k, _ in L if k == "C")
print("ma3.txt:", txt_path, "| 명령", ncmds, "줄")

# ── 출력: 매크로 XML (템플릿) ────────────────────────────
xml_path = os.path.join(MA3_DIR, "LXSEQ_SAMPLE_01_Sugar_r3.macros.xml")
macros, cur, curname = [], [], None
for kind, line in L:
    if kind == "S":
        if cur:
            macros.append((curname, cur))
        curname, cur = line.split("—")[0].strip(), []
    elif kind == "C":
        cur.append(line)
if cur:
    macros.append((curname, cur))
# 큐 단위 세분 매크로는 §7 하나로 병합
merged, seen = [], {}
for name, cmds in macros:
    key = name.split(".")[0].strip()
    if key.startswith("7") or name.startswith("Q"):
        seen.setdefault("7. 메인 시퀀스", []).extend(cmds)
    else:
        merged.append((name, cmds))
if "7. 메인 시퀀스" in seen:
    idx = next((i for i, (n, _) in enumerate(merged) if n.startswith("7")), len(merged))
    merged = [m for m in merged if not m[0].startswith("7")]
    merged.insert(min(idx, len(merged)), ("7. 메인 시퀀스 Sugar", seen["7. 메인 시퀀스"]))
with open(xml_path, "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write("<!-- [VERIFY] DataVersion을 콘솔 소프트웨어 버전에 맞게 수정 후\n")
    f.write("     gma3_library/datapools/macros 에 복사 → Macro Pool에서 Import -->\n")
    f.write('<GMA3 DataVersion="2.2.0.0">\n')
    for name, cmds in merged:
        f.write('  <Macro Name="%s">\n' % html.escape("LXSEQ " + name))
        for c in cmds:
            f.write('    <MacroLine Command="%s" />\n' % html.escape(c, quote=True))
        f.write("  </Macro>\n")
    f.write("</GMA3>\n")
print("macros.xml:", xml_path, "| 매크로", len(merged), "개")

# 검증용 내보내기
MA3_STATS = {"commands": ncmds, "macros": len(merged), "cues": len(by_q)}
if __name__ == "__main__":
    pass
