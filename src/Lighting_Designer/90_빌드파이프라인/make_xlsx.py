import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 출력 위치는 이 스크립트 위치에서 유도한다. 기계마다 다른 절대경로를
# 박아두면 그 기계 밖에서는 돌지 않는다.
SONG_DIR = os.environ.get("LXSEQ_SONG_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "03_곡파일_Sugar"
)
os.makedirs(SONG_DIR, exist_ok=True)
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.page import PageMargins
from seq_data import CUES, FIXTURE_GROUPS, HEAD_META, NOTES, PALETTE, tc

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HDR_FILL = PatternFill("solid", fgColor="2F3B52")
HDR_FONT = Font(name="맑은 고딕", size=9, bold=True, color="FFFFFF")
BODY_FONT = Font(name="맑은 고딕", size=9)
MONO_FONT = Font(name="Consolas", size=9)
SEC_FILLS = {
    "INTRO": "FFF2DC",
    "VERSE1": "FFF8EC",
    "VERSE2": "FFF8EC",
    "PRE1": "E4F8F8",
    "PRE2": "E4F8F8",
    "CHORUS1": "FFE2F0",
    "CHORUS2": "FFE2F0",
    "CHORUS3": "FFD2E8",
    "BRIDGE": "EAE2FA",
    "OUTRO": "EDEFF2",
}

wb = Workbook()

# ---------------- HEAD ----------------
ws = wb.active
ws.title = "HEAD"
r = 1
ws.cell(r, 1, "LX-SEQ v2.0 — 조명연출 시퀀스 큐시트").font = Font(
    name="맑은 고딕", size=14, bold=True, color="2F3B52"
)
r += 2
ws.cell(r, 1, "■ 곡 · 공연 정보").font = Font(name="맑은 고딕", size=10, bold=True)
r += 1
for k, v in HEAD_META:
    c1 = ws.cell(r, 1, k)
    c1.font = Font(name="Consolas", size=9, bold=True)
    c1.fill = PatternFill("solid", fgColor="EDEFF2")
    c1.border = BORDER
    c2 = ws.cell(r, 2, v)
    c2.font = BODY_FONT
    c2.border = BORDER
    c2.alignment = Alignment(wrap_text=True, vertical="center")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    r += 1

r += 1
ws.cell(r, 1, "■ 장비 그룹 정의 (FIXTURE_GROUP) — CUE 시트는 이 약칭만 사용").font = Font(
    name="맑은 고딕", size=10, bold=True
)
r += 1
for i, h in enumerate(["약칭", "정의", "기종·대수", "비고"], start=1):
    c = ws.cell(r, i, h)
    c.font = HDR_FONT
    c.fill = HDR_FILL
    c.border = BORDER
    c.alignment = Alignment(horizontal="center")
r += 1
for row in FIXTURE_GROUPS:
    for i, v in enumerate(row, start=1):
        c = ws.cell(r, i, v)
        c.font = MONO_FONT if i == 1 else BODY_FONT
        c.border = BORDER
    r += 1

r += 1
ws.cell(r, 1, "■ 색 팔레트 (PALETTE) — CUE 시트 Color 열은 'ID 한글색상명' 병기 필수").font = Font(
    name="맑은 고딕", size=10, bold=True
)
r += 1
for i, h in enumerate(["ID", "색상명(한글)", "참고값", "견본", "용도"], start=1):
    c = ws.cell(r, i, h)
    c.font = HDR_FONT
    c.fill = HDR_FILL
    c.border = BORDER
    c.alignment = Alignment(horizontal="center")
r += 1
for pid, name, ref, hexv, use in PALETTE:
    ws.cell(r, 1, pid).font = MONO_FONT
    ws.cell(r, 2, name).font = BODY_FONT
    ws.cell(r, 3, ref).font = BODY_FONT
    sw = ws.cell(r, 4, hexv)
    sw.fill = PatternFill("solid", fgColor=hexv.lstrip("#"))
    sw.font = Font(name="Consolas", size=8, color="FFFFFF" if pid in ("P5", "P8") else "000000")
    sw.alignment = Alignment(horizontal="center")
    ws.cell(r, 5, use).font = BODY_FONT
    for i in range(1, 6):
        ws.cell(r, i).border = BORDER
    r += 1

for col, w in zip("ABCDE", [16, 30, 26, 22, 34]):
    ws.column_dimensions[col].width = w

# ---------------- CUE ----------------
cs = wb.create_sheet("CUE")
HEADERS = [
    "Q#",
    "Section",
    "TC In",
    "TC Out",
    "Dur",
    "Mood",
    "Color(주/보조)",
    "Intensity",
    "Fixture Group",
    "Movement",
    "Effect",
    "Transition",
    "Fade",
    "Note",
]
cs.cell(1, 1, "Maroon 5 — Sugar  |  03:56.0  |  120BPM 4/4  |  LX-SEQ v2.1  |  r3").font = Font(
    name="맑은 고딕", size=11, bold=True, color="2F3B52"
)
cs.merge_cells(start_row=1, start_column=1, end_row=1, end_column=14)
cs.cell(
    2,
    1,
    "TC_ORIGIN: 00:00.0 = 곡 첫 음 (카운트인 없음)   |   TC_METHOD: DERIVED — 리허설 LTC 대조 필수",
).font = Font(name="맑은 고딕", size=9, italic=True, color="B03030")
cs.merge_cells(start_row=2, start_column=1, end_row=2, end_column=14)

HR = 4
for i, h in enumerate(HEADERS, start=1):
    c = cs.cell(HR, i, h)
    c.font = HDR_FONT
    c.fill = HDR_FILL
    c.border = BORDER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

r = HR + 1
for cue in CUES:
    q, sec, tin, tout, mood, color, inten, fix, mov, eff, trans, fade, note = cue[:13]
    dur = "" if tout is None else "%04.1f" % (tout - tin)
    vals = [q, sec, tc(tin), tc(tout), dur, mood, color, inten, fix, mov, eff, trans, fade, note]
    fill = PatternFill("solid", fgColor=SEC_FILLS.get(sec, "FFFFFF"))
    for i, v in enumerate(vals, start=1):
        c = cs.cell(r, i, v)
        c.font = MONO_FONT if i in (1, 2, 3, 4, 5, 12, 13) else BODY_FONT
        c.fill = fill
        c.border = BORDER
        c.alignment = Alignment(
            vertical="center",
            wrap_text=(i in (6, 7, 9, 14)),
            horizontal="center" if i in (1, 2, 3, 4, 5, 8, 12, 13) else "left",
        )
    if trans == "SNAP":
        cs.cell(r, 12).font = Font(name="Consolas", size=9, bold=True, color="B03030")
    if "[MANUAL]" in note:
        cs.cell(r, 14).font = Font(name="맑은 고딕", size=9, bold=True, color="B03030")
    r += 1

for col, w in zip(
    ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"],
    [8, 10, 9, 9, 7, 16, 24, 17, 30, 15, 14, 11, 7, 40],
):
    cs.column_dimensions[col].width = w
cs.freeze_panes = "C5"
cs.row_dimensions[HR].height = 30
cs.page_setup.orientation = "landscape"
cs.page_setup.fitToWidth = 1
cs.sheet_properties.pageSetUpPr.fitToPage = True
cs.page_margins = PageMargins(left=0.3, right=0.3, top=0.4, bottom=0.4)
cs.print_title_rows = "%d:%d" % (HR, HR)

# ---------------- NOTE ----------------
ns = wb.create_sheet("NOTE")
ns.cell(1, 1, "NOTE — 확인 필요 항목 · 변경 이력 · 스펙 개정 후보").font = Font(
    name="맑은 고딕", size=11, bold=True, color="2F3B52"
)
for i, h in enumerate(["구분", "대상 Q#", "내용", "기록일", "상태"], start=1):
    c = ns.cell(3, i, h)
    c.font = HDR_FONT
    c.fill = HDR_FILL
    c.border = BORDER
    c.alignment = Alignment(horizontal="center")
GUBUN_COLOR = {
    "확인필요": "FFE0E0",
    "장비이슈": "FFF0D8",
    "스펙개정후보": "E2ECFF",
    "리허설변경": "E8F5E0",
}
DONE_FILL = PatternFill("solid", fgColor="DFF0DA")
r = 4
for g, q, txt, d, st in NOTES:
    vals = [g, q, txt, d, st]
    for i, v in enumerate(vals, start=1):
        c = ns.cell(r, i, v)
        c.font = BODY_FONT
        c.border = BORDER
        c.alignment = Alignment(
            vertical="center",
            wrap_text=(i == 3),
            horizontal="center" if i in (1, 2, 4, 5) else "left",
        )
        if i == 1:
            c.fill = PatternFill("solid", fgColor=GUBUN_COLOR.get(g, "FFFFFF"))
            c.font = Font(name="맑은 고딕", size=9, bold=True)
    r += 1
for col, w in zip("ABCDE", [14, 14, 88, 12, 10]):
    ns.column_dimensions[col].width = w
ns.freeze_panes = "A4"

out = os.path.join(SONG_DIR, "LXSEQ_SAMPLE_01_Sugar_r3.xlsx")
os.makedirs(os.path.dirname(out), exist_ok=True)
wb.save(out)
print("saved:", out)
