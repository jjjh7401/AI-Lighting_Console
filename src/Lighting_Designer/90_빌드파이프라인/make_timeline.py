# -*- coding: utf-8 -*-
import sys, os, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 출력 위치는 이 스크립트 위치에서 유도한다. 기계마다 다른 절대경로를
# 박아두면 그 기계 밖에서는 돌지 않는다.
SONG_DIR = os.environ.get("LXSEQ_SONG_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "03_곡파일_Sugar")
os.makedirs(SONG_DIR, exist_ok=True)
from seq_data import *

TOTAL = 240.0  # 차트 x축 (곡 236.0 + 종료 암전 여유)
SEC_TONE = {
    "INTRO": "#8A7A5C", "VERSE1": "#A9925F", "VERSE2": "#A9925F",
    "PRE1": "#2E8C8C", "PRE2": "#2E8C8C",
    "CHORUS1": "#C7307D", "CHORUS2": "#C7307D", "CHORUS3": "#9E1F63",
    "BRIDGE": "#5A2BC8", "OUTRO": "#4A5568",
}
def pct(x): return x / TOTAL * 100.0

# ── 강도 곡선 ────────────────────────────────────────────
pts, prev = [], 0
for c in CUES:
    tin, peak, fade = c[2], c[13], float(c[11])
    pts.append((tin, prev))
    pts.append((min(tin + fade, TOTAL), peak))
    prev = peak
pts.append((TOTAL, prev))
CH_W, CH_H = 1000.0, 132.0
TOP_PAD, BOT_PAD = 16.0, 4.0
SPAN = CH_H - TOP_PAD - BOT_PAD
poly = " ".join("%.2f,%.2f" % (t / TOTAL * CH_W, CH_H - (v / 100.0) * SPAN - BOT_PAD) for t, v in pts)
area = "0,%.1f " % CH_H + poly + " %.1f,%.1f" % (CH_W, CH_H)

# ── 눈금 ────────────────────────────────────────────────
ticks = "".join(
    '<div class="tick" style="left:%.4f%%"><span>%s</span></div>' % (pct(t), tc(t))
    for t in range(0, 209, 16))
ticks += '<div class="tick end" style="left:%.4f%%"><span>%s ▌곡끝</span></div>' % (pct(236.0), tc(236.0))

# ── 섹션 밴드 ───────────────────────────────────────────
secs = "".join(
    '<div class="sec" style="left:%.4f%%;width:%.4f%%;background:%s">'
    '<b>%s</b><i>%d마디 · %.0fs</i></div>' % (
        pct(a), pct(b - a), SEC_TONE[n], n, bars, b - a)
    for n, bars, a, b in SECTIONS)

# ── 큐 밴드 ─────────────────────────────────────────────
cueblocks = []
for c in CUES:
    q, sec, tin, tout = c[0], c[1], c[2], c[3]
    inten, trans, hexv = c[6], c[10], c[14]
    end = TOTAL if tout is None else tout
    dark = hexv in ("#5A2BC8", "#101418", "#FF3C9E", "#9E1F63")
    cueblocks.append(
        '<div class="cue%s%s" style="left:%.4f%%;width:calc(%.4f%% - 2px);background:%s;color:%s" '
        'title="%s %s | %s | %s">%s</div>' % (
            " snap" if trans == "SNAP" else "",
            " tiny" if pct(end - tin) < 2.5 else "",
            pct(tin), pct(end - tin), hexv,
            "#fff" if dark else "#20242c",
            q, sec, html.escape(inten), trans, q))
cues_html = "".join(cueblocks)

# ── 팔레트 범례 ─────────────────────────────────────────
used = {c[14] for c in CUES}
legend = "".join(
    '<span class="lg"><i style="background:%s"></i>%s %s</span>' % (hx, pid, nm)
    for pid, nm, ref, hx, use in PALETTE if hx in used)

# ── 상세 표 ─────────────────────────────────────────────
rows = []
for c in CUES:
    q, sec, tin, tout, mood, color, inten, fix, mov, eff, trans, fade, note = c[:13]
    dur = "—" if tout is None else "%.1f" % (tout - tin)
    rows.append(
        "<tr class='s-%s'><td class='m'>%s</td><td class='m'>%s</td><td class='m'>%s</td>"
        "<td class='m'>%s</td><td class='m'>%s</td><td>%s</td><td>%s</td><td class='m'>%s</td>"
        "<td class='fx'>%s</td><td>%s</td><td>%s</td><td class='m %s'>%s</td><td class='m'>%s</td>"
        "<td class='nt'>%s</td></tr>" % (
            sec, q, sec, tc(tin), tc(tout) or "—", dur,
            html.escape(mood), html.escape(color), html.escape(inten),
            html.escape(fix), mov, eff, "snapc" if trans == "SNAP" else "", trans, fade,
            html.escape(note)))
table = "".join(rows)

meta = dict(HEAD_META)
HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LX-SEQ 타임라인 — Maroon 5 / Sugar</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:24px;background:#12151b;color:#e8ecf2;
 font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic","맑은 고딕",sans-serif}
.wrap{max-width:1440px;margin:0 auto}
h1{margin:0 0 4px;font-size:22px;letter-spacing:-.3px}
h1 small{font-weight:400;color:#8b94a3;font-size:14px;margin-left:10px}
.meta{color:#8b94a3;font-size:12.5px;margin-bottom:14px}
.meta code{background:#1e2330;padding:1px 6px;border-radius:4px;color:#c8d2e0;font-size:12px}
.warn{background:#3a1f24;border-left:3px solid #d2506a;padding:9px 13px;border-radius:5px;
 font-size:12.5px;color:#f0c4cd;margin-bottom:18px}
.panel{background:#1a1e28;border:1px solid #2a3040;border-radius:9px;padding:16px 18px 10px;margin-bottom:16px}
.panel h2{margin:0 0 14px;font-size:13px;font-weight:600;color:#9aa5b6;letter-spacing:.6px;text-transform:uppercase}
.rail{position:relative;height:20px;margin-bottom:2px}
.tick{position:absolute;top:0;border-left:1px solid #333b4d;height:100%;padding-left:4px}
.tick span{font:10.5px/1 Consolas,monospace;color:#6b7588;white-space:nowrap}
.tick.end{border-left:1px solid #d2506a;padding-left:0;padding-right:4px;transform:translateX(-100%)}
.tick.end span{color:#d2506a}
.rail{overflow:hidden}
.band{position:relative;height:44px;margin-bottom:6px}
.sec{position:absolute;top:0;height:100%;border-radius:4px;overflow:hidden;
 display:flex;flex-direction:column;justify-content:center;padding:0 7px;border:1px solid rgba(0,0,0,.35)}
.sec b{font-size:11.5px;color:#fff;letter-spacing:.3px;white-space:nowrap}
.sec i{font-style:normal;font-size:10px;color:rgba(255,255,255,.72);white-space:nowrap}
.cband{position:relative;height:34px;margin-bottom:4px}
.cue{position:absolute;top:0;height:100%;min-width:9px;border-radius:3px;display:flex;align-items:center;
 justify-content:center;font:600 10.5px/1 Consolas,monospace;border:1px solid rgba(0,0,0,.3);overflow:hidden}
.cue.snap{border-left:3px solid #fff}
.cue.tiny{font-size:0}
.chart{position:relative;height:132px;margin-top:10px}
.chart svg{width:100%;height:100%;display:block}
.axis{font:10px Consolas,monospace;fill:#5d6779}
.lgrow{margin-top:12px;padding-top:11px;border-top:1px solid #2a3040;display:flex;flex-wrap:wrap;gap:14px}
.lg{font-size:11.5px;color:#98a2b3;display:flex;align-items:center;gap:6px}
.lg i{width:13px;height:13px;border-radius:3px;display:inline-block;border:1px solid rgba(255,255,255,.18)}
table{width:100%;border-collapse:collapse;font-size:11.5px}
th{background:#232a38;color:#9aa5b6;font-weight:600;padding:7px 6px;text-align:left;
 border-bottom:1px solid #333b4d;position:sticky;top:0;font-size:11px;white-space:nowrap}
td{padding:6px;border-bottom:1px solid #242b39;vertical-align:top}
td.m{font-family:Consolas,monospace;white-space:nowrap}
td.fx{font-family:Consolas,monospace;font-size:10.5px;color:#a8b4c6}
td.nt{color:#8b94a3;font-size:11px}
td.snapc{color:#ff7d97;font-weight:700}
tr.s-INTRO td:first-child{border-left:3px solid #8A7A5C}
tr.s-VERSE1 td:first-child,tr.s-VERSE2 td:first-child{border-left:3px solid #A9925F}
tr.s-PRE1 td:first-child,tr.s-PRE2 td:first-child{border-left:3px solid #2E8C8C}
tr.s-CHORUS1 td:first-child,tr.s-CHORUS2 td:first-child{border-left:3px solid #C7307D}
tr.s-CHORUS3 td:first-child{border-left:3px solid #9E1F63}
tr.s-BRIDGE td:first-child{border-left:3px solid #5A2BC8}
tr.s-OUTRO td:first-child{border-left:3px solid #4A5568}
.foot{color:#616b7d;font-size:11px;margin-top:16px;text-align:center}
@media print{
 @page{size:A3 landscape;margin:9mm}
 body{background:#fff;color:#111;padding:0;font-size:10px}
 .panel{background:#fff;border:1px solid #999;break-inside:avoid}
 .panel h2{color:#333}
 .warn{background:#fff;border-left:3px solid #000;color:#000}
 .meta,.meta code{color:#333;background:none}
 th{background:#e8e8e8;color:#000;border-bottom:1px solid #000}
 td{border-bottom:1px solid #ccc}
 td.nt,td.fx,.lg{color:#333}
 h1{color:#000} h1 small{color:#444}
 .foot{color:#666}
}
</style></head><body><div class="wrap">
<h1>Maroon 5 — Sugar <small>LX-SEQ v2.1 · r3 · 조명연출 시퀀스</small></h1>
<div class="meta">
 <code>03:56.0</code> <code>120 BPM</code> <code>4/4</code> <code>D♭ major</code>
 <code>118마디 · 1마디 2.000s</code> <code>TC_SOURCE: LTC</code> <code>18 cues</code>
 &nbsp;|&nbsp; TC_ORIGIN: 00:00.0 = 곡 첫 음 (카운트인 없음)
</div>
<div class="warn"><b>TC_METHOD: DERIVED</b> — 이 타임라인의 모든 타임코드는 마디 연산(1마디 = 2.000s)으로 도출한 값입니다.
음원 청취로 검증하지 않았습니다. 픽업·하프바 삽입이 있으면 전 구간이 어긋납니다. <b>리허설에서 LTC 대조 필수.</b></div>

<div class="panel"><h2>Timeline</h2>
 <div class="rail">{ticks}</div>
 <div class="band">{secs}</div>
 <div class="cband">{cues}</div>
 <div class="chart">
  <svg viewBox="0 0 {cw} {ch}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
   <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#ff3c9e" stop-opacity=".55"/>
    <stop offset="100%" stop-color="#ff3c9e" stop-opacity=".04"/></linearGradient></defs>
   <line x1="0" y1="{y100}" x2="{cw}" y2="{y100}" stroke="#2f394b" stroke-dasharray="3 4"/>
   <line x1="0" y1="{y50}" x2="{cw}" y2="{y50}" stroke="#2a3243" stroke-dasharray="3 4"/>
   <polygon points="{area}" fill="url(#g)"/>
   <polyline points="{poly}" fill="none" stroke="#ff3c9e" stroke-width="2"
    vector-effect="non-scaling-stroke" stroke-linejoin="round"/>
   <text class="axis" x="4" y="{y100t}">100%</text>
   <text class="axis" x="4" y="{y50t}">50%</text>
  </svg>
 </div>
 <div class="lgrow">{legend}
  <span class="lg"><i style="background:#fff;border-radius:0;width:3px"></i>흰 좌측선 = SNAP 전환</span>
  <span class="lg" style="margin-left:auto;color:#d2506a">OUTRO(03:52~) Q170·Q180은 폭이 좁아 라벨 생략 — 하단 표 참조</span>
 </div>
</div>

<div class="panel"><h2>Cue Sheet</h2>
<table><thead><tr>
<th>Q#</th><th>Section</th><th>TC In</th><th>TC Out</th><th>Dur</th><th>Mood</th>
<th>Color(주/보조)</th><th>Intensity</th><th>Fixture Group</th><th>Movement</th>
<th>Effect</th><th>Trans</th><th>Fade</th><th>Note</th>
</tr></thead><tbody>{table}</tbody></table></div>

<div class="foot">LX-SEQ v2.0 · 자체완결 단일 HTML (외부 의존 없음) · A3 가로 인쇄 대응 · 생성 2026-08-21 (r3)</div>
</div></body></html>"""

out = os.path.join(SONG_DIR, "LXSEQ_SAMPLE_01_Sugar_r3.timeline.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
SUBS = {
    "{ticks}": ticks, "{secs}": secs, "{cues}": cues_html,
    "{legend}": legend, "{table}": table,
    "{cw}": "%.0f" % CH_W, "{ch}": "%.0f" % CH_H,
    "{poly}": poly, "{area}": area,
    "{y100}": "%.1f" % (CH_H - SPAN - BOT_PAD),
    "{y50}":  "%.1f" % (CH_H - .5 * SPAN - BOT_PAD),
    "{y100t}": "%.1f" % (CH_H - SPAN - BOT_PAD - 4),
    "{y50t}":  "%.1f" % (CH_H - .5 * SPAN - BOT_PAD - 4),
}
doc = HTML
for k, v in SUBS.items():
    doc = doc.replace(k, v)
with open(out, "w", encoding="utf-8") as f:
    f.write(doc)
print("saved:", out, os.path.getsize(out), "bytes")
