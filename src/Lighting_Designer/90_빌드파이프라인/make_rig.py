# -*- coding: utf-8 -*-
"""RIG 팩 생성 — XLSX(8시트) + 픽스처 단위 패치 CSV. 주소는 유니버스 계획에서 자동 계산."""
import sys, os, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig_data import *
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HDR_FILL = PatternFill("solid", fgColor="4A3560")   # RIG 팩은 보라 계열
HDR_FONT = Font(name="맑은 고딕", size=9, bold=True, color="FFFFFF")
BODY = Font(name="맑은 고딕", size=9)
MONO = Font(name="Consolas", size=9)
WARN = Font(name="맑은 고딕", size=9, bold=True, color="B03030")
TITLE = Font(name="맑은 고딕", size=12, bold=True, color="4A3560")

FIX = {f[0]: f for f in FIXTURES}

# ── 패치 자동 계산 ─────────────────────────────────────────
patch_rows = []   # (FID, Group, 기종, Mode, ch, Universe, Addr, Addr범위, 리깅)
overflow = []
for uni, groups, desc in UNIVERSE_PLAN:
    addr = 1
    for g in groups:
        grp, model, mode, ch, cnt, rig, circuit, use, sugar = FIX[g]
        for i in range(cnt):
            fid = FID_BASE[g] + i
            if addr + ch - 1 > 512:
                overflow.append((uni, g, fid, addr))
            patch_rows.append((fid, g, model, mode, ch, uni, addr, "%d.%03d–%03d" % (uni, addr, addr + ch - 1), rig))
            addr += ch
if overflow:
    raise SystemExit("UNIVERSE OVERFLOW: %s" % overflow)

# DMX 미사용 장비 (FOLLOW)
manual_rows = [(FID_BASE[f[0]], f[0], f[1], f[2], "—", "—", "—", "수동 운용", f[5]) for f in FIXTURES if f[3] == 0]

uni_usage = {}
for r in patch_rows:
    uni_usage[r[5]] = max(uni_usage.get(r[5], 0), r[6] + r[4] - 1)

wb = Workbook()

def sheet(name, title, headers, rows, widths, mono_cols=(), warn_texts=("확인필요", "현장 레코드"), start=3):
    ws = wb.create_sheet(name) if wb.sheetnames != ["Sheet"] else wb.active
    if ws.title == "Sheet": ws.title = name
    ws.cell(1, 1, title).font = TITLE
    hr = start
    for i, h in enumerate(headers, start=1):
        c = ws.cell(hr, i, h); c.font = HDR_FONT; c.fill = HDR_FILL; c.border = BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    r = hr + 1
    for row in rows:
        for i, v in enumerate(row, start=1):
            c = ws.cell(r, i, v)
            c.font = MONO if i in mono_cols else BODY
            c.border = BORDER
            c.alignment = Alignment(vertical="center", wrap_text=True,
                                    horizontal="center" if i in mono_cols else "left")
            if isinstance(v, str) and any(w in v for w in warn_texts):
                c.font = WARN
        r += 1
    for idx, w in enumerate(widths):
        ws.column_dimensions[chr(65 + idx)].width = w
    ws.freeze_panes = "A%d" % (hr + 1)
    return ws

# 1 RIG-HEAD
sheet("RIG-HEAD", "LX-SEQ v2.1 — RIG 팩 (쇼 단위 콘솔 기본설정) · 곡 큐시트가 참조하는 공통 기반",
      ["항목", "값"], RIG_HEAD, [16, 96], mono_cols=(1,))

# 2 FIXTURE
sheet("FIXTURE", "장비 인벤토리 — 실제 공연 표준 기종 제안 · 풋프린트=제조사 DMX 차트 실측 (보유/대여 확정 필요)",
      ["Group", "기종(실제 제안)", "Mode", "ch", "수량", "리깅 위치", "회로", "용도", "Sugar"],
      FIXTURES, [10, 20, 10, 6, 6, 18, 6, 26, 8], mono_cols=(1, 3, 4, 5, 7))

# 3 PATCH (픽스처 단위)
total_ch = sum(r[4] for r in patch_rows)
ws = sheet("PATCH", "패치 — 픽스처 단위 (주소 자동 계산 초안 · 총 %d대 · %dch)" % (len(patch_rows), total_ch),
      ["FID", "Group", "기종", "Mode", "ch", "Uni", "Addr", "주소 범위", "리깅 위치"],
      patch_rows + manual_rows, [7, 10, 20, 10, 6, 6, 7, 15, 18], mono_cols=(1, 2, 4, 5, 6, 7, 8))
usage_txt = "  |  ".join("U%d: %d/512ch" % (u, m) for u, m in sorted(uni_usage.items()))
ws.cell(2, 1, "유니버스 사용량 — " + usage_txt + "  (여유분은 예비·추가 장비용)").font = Font(name="맑은 고딕", size=9, italic=True, color="4A5568")

# 4 GROUP
sheet("GROUP", "MA3 그룹 풀 — CUE-EX Fixture Group은 이 이름만 사용",
      ["Group#", "이름", "구성", "용도"], GROUPS, [8, 12, 26, 24], mono_cols=(1, 2))

# 5 PRESET-DIM / COL (한 시트)
ws = sheet("PRESET-DIM·COL", "딤머 · 컬러 프리셋",
      ["ID", "이름", "레벨", "용도"], PRESET_DIM, [10, 14, 10, 40], mono_cols=(1, 3))
r0 = 3 + len(PRESET_DIM) + 3
ws.cell(r0 - 1, 1, "■ 컬러 프리셋 (연출 팔레트 P.xx와 1:1 · COL 견본색은 곡 파일 HEAD 참조)").font = Font(name="맑은 고딕", size=10, bold=True)
for i, h in enumerate(["ID", "이름", "절대값", "용도"], start=1):
    c = ws.cell(r0, i, h); c.font = HDR_FONT; c.fill = HDR_FILL; c.border = BORDER; c.alignment = Alignment(horizontal="center")
for j, row in enumerate(PRESET_COL):
    for i, v in enumerate(row, start=1):
        c = ws.cell(r0 + 1 + j, i, v); c.font = MONO if i in (1, 3) else BODY; c.border = BORDER
        c.alignment = Alignment(vertical="center", wrap_text=True)

# 6 PRESET-POS·BM
ws = sheet("PRESET-POS·BM", "포지션 프리셋 — 전부 현장 레코드 대상 (가이드 기준으로 레코드)",
      ["ID", "무대 의미", "대상 그룹", "레코드 가이드"], PRESET_POS, [10, 24, 14, 46], mono_cols=(1, 3))
r0 = 3 + len(PRESET_POS) + 3
ws.cell(r0 - 1, 1, "■ 빔 프리셋").font = Font(name="맑은 고딕", size=10, bold=True)
for i, h in enumerate(["ID", "이름", "대상 그룹", "값"], start=1):
    c = ws.cell(r0, i, h); c.font = HDR_FONT; c.fill = HDR_FILL; c.border = BORDER; c.alignment = Alignment(horizontal="center")
for j, row in enumerate(PRESET_BM):
    for i, v in enumerate(row, start=1):
        c = ws.cell(r0 + 1 + j, i, v); c.font = MONO if i in (1, 3) else BODY; c.border = BORDER
        c.alignment = Alignment(vertical="center", wrap_text=True)

# 7 FX
ws = sheet("FX", "FX(Phaser) 라이브러리 — Rate는 SpeedMaster 1(곡 BPM) 종속 · 공식: SongBPM÷사이클박수",
      ["ID", "이름", "어트리뷰트", "파형·스텝", "기본 Rate", "Width", "Phase", "비고"],
      FX_LIB, [8, 16, 10, 16, 13, 7, 9, 34], mono_cols=(1, 2, 5, 6, 7))

# 8 CONSOLE
ws = sheet("CONSOLE", "grandMA3 콘솔 기본설정",
      ["항목", "설정"], CONSOLE_SETUP, [14, 96])
r0 = 3 + len(CONSOLE_SETUP) + 3
ws.cell(r0 - 1, 1, "■ 이그제큐터 레이아웃 (Page 1)").font = Font(name="맑은 고딕", size=10, bold=True)
for i, h in enumerate(["위치", "할당", "동작"], start=1):
    c = ws.cell(r0, i, h); c.font = HDR_FONT; c.fill = HDR_FILL; c.border = BORDER; c.alignment = Alignment(horizontal="center")
for j, row in enumerate(EXEC_LAYOUT):
    for i, v in enumerate(row, start=1):
        c = ws.cell(r0 + 1 + j, i, v); c.font = MONO if i == 1 else BODY; c.border = BORDER
        c.alignment = Alignment(vertical="center", wrap_text=True)
ws.column_dimensions["A"].width = 20
ws.column_dimensions["B"].width = 36
ws.column_dimensions["C"].width = 40

# 9 NOTE
sheet("NOTE", "NOTE — 확인 필요 항목",
      ["구분", "대상", "내용", "기록일", "상태"], RIG_NOTES, [12, 16, 76, 12, 10])

# ── 출력 ───────────────────────────────────────────────────
# 출력 위치는 이 스크립트 위치에서 유도한다. 기계마다 다른 절대경로를
# 박아두면 그 기계 밖에서는 돌지 않는다.
OUT_DIR = os.environ.get("LXSEQ_RIG_OUT") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3"
os.makedirs(OUT_DIR, exist_ok=True)

out = os.path.join(OUT_DIR, STEM + ".xlsx")
wb.save(out)
print("saved:", out, "| sheets:", wb.sheetnames)

# ── CSV (기계 정본) ────────────────────────────────────────
# 규약: 확장자 앞 접미사로 시트를 구분 · 헤더는 ASCII · utf-8-sig
# (기존 patch.csv · cue-ex.csv 와 동일)
def write_csv(suffix, header, rows):
    path = os.path.join(OUT_DIR, "%s.%s.csv" % (STEM, suffix))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    print("csv:", path, len(rows), "rows")
    return path

write_csv("patch", ["FID", "Group", "FixtureType", "Mode", "Ch", "Universe", "Address", "AddrRange", "Position"], patch_rows)
write_csv("group", ["GroupNo", "Name", "Members", "Purpose"], GROUPS)
write_csv("preset-dim", ["ID", "Name", "Level", "Purpose"], PRESET_DIM)
write_csv("preset-col", ["ID", "Name", "Value", "Purpose"], PRESET_COL)
write_csv("preset-pos", ["ID", "StageMeaning", "TargetGroup", "RecordGuide"], PRESET_POS)
write_csv("preset-bm", ["ID", "Name", "TargetGroup", "Value"], PRESET_BM)
write_csv("fx", ["ID", "Name", "Attribute", "WaveSteps", "BaseRate", "Width", "Phase", "Note"], FX_LIB)
print("universe usage:", uni_usage)
