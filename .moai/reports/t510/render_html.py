"""reports/loveattack-baseline-20261006.md → .html (moai-domain-html-report, explainer · basic 등급).

md 를 그대로 옮기고, 사람이 읽을 보충(쉬운 말 안내·큐 타임라인 SVG)만 HTML 에 더한다.
타임라인 데이터는 hold_table.json(잰 값)에서 읽는다.

실행: python3 .moai/reports/t510/render_html.py
"""

# ruff: noqa: E501 — HTML·CSS 템플릿 문자열을 그대로 싣는 렌더러라 줄 길이 규칙을 끈다
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MD = ROOT / "reports/loveattack-baseline-20261006.md"
OUT = MD.with_suffix(".html")
data = json.loads((HERE / "hold_table.json").read_text("utf-8"))
src = MD.read_text("utf-8")


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = s.replace("[잰 값]", '<span class="tag m">잰 값</span>')
    s = s.replace("[추정]", '<span class="tag e">추정</span>')
    return s


def convert(text: str) -> str:
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[2:]]
            out.append(
                '<div class="tw"><table><thead><tr>'
                + "".join(f"<th>{inline(c)}</th>" for c in head)
                + "</tr></thead><tbody>"
            )
            for r in body:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table></div>")
            continue
        if ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("## "):
            title = ln[3:]
            out.append(f"<h2>{inline(title)}</h2>")
            if lead := LEADS.get(title.split(".")[0]):
                out.append(f'<p class="lead">{lead}</p>')
            if title.startswith("2."):
                out.append(timeline_svg())
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


#: basic 등급 — 절마다 쉬운 말 한 문단(HTML 에만 싣는다).
LEADS = {
    "1": "앱에 노래 파일을 넣고, 앱이 묻는 질문에 미리 정해 둔 답을 넣어 끝까지 돌렸습니다. 명령은 진짜 콘솔이 아니라 컴퓨터 안의 「가짜 콘솔」이 받았습니다 — 무대에 실제로 나간 것은 없습니다.",
    "2": "큐(cue)는 「한 장면」입니다. 아래 그림은 곡 처음부터 끝까지 장면이 언제 바뀌는지, 한 장면이 얼마나 오래 가는지(유지 시간), 얼마나 밝은지(막대 높이)를 보여 줍니다. 색 띠는 양옆·워시 조명(SIDE·WASH)의 색입니다.",
    "3": "같은 방법으로 쟀던 Rain·Club Diver 와 나란히 놓았습니다. 숫자가 클수록 한 장면이 오래 멈춰 있다는 뜻입니다.",
    "4": "조명이 바뀌는 여러 「손잡이」(색·밝기·위치·효과)마다 무엇이 나갔는지 정리했습니다.",
    "5": "프로젝트의 조명 연출 기준(정본)에 비춰 어긋난 곳입니다. 숫자는 위반 개수입니다.",
    "6": "",
    "7": "이 결과를 볼 때 감안해야 할, 이번에 직접 재지 않은 것들입니다.",
}

RGB = {"블루": "#2846d6", "cyan": "#13b5d1", "warm white": "#f1c27d"}


def timeline_svg() -> str:
    rows, end = data["rows"], data["song_end_s"]
    w, h, x0, top = 820, 230, 30, 20
    scale = (w - x0 - 10) / end
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="LOVE ATTACK 큐 타임라인" class="tl">'
    ]
    base = top + 130
    for r in rows:
        x = x0 + r["trig_s"] * scale
        bw = max(r["hold_s"] * scale, 2)
        bh = r["all_dimmer"] * 1.2
        side = r["layer_rgb"].get("SIDE-ALL") or "블루"
        parts.append(
            f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{bw - 1:.1f}" height="{bh:.1f}" fill="#d97757" opacity="{0.35 + r["all_dimmer"] / 160:.2f}"><title>큐 {r["cue"]} {r["name"]} · {r["trig_s"]:.1f}s · 유지 {r["hold_s"]:.1f}s · 디머 {r["all_dimmer"]:g}</title></rect>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{base + 6}" width="{bw - 1:.1f}" height="10" fill="{RGB.get(side, "#999")}"/>'
        )
        if r["layer_dimmer"].get("BLIND"):
            parts.append(
                f'<text x="{x:.1f}" y="{base - bh - 6:.1f}" font-size="11" fill="#b85c3e">블라인더</text>'
            )
        if bw > 34:
            parts.append(
                f'<text x="{x + 3:.1f}" y="{base + 32}" font-size="10.5" fill="#3d3d3a">{html.escape(r["name"].replace("Chorus 3 Return", "C3 복귀"))}</text>'
            )
            parts.append(
                f'<text x="{x + 3:.1f}" y="{base + 46}" font-size="10" fill="#87867f">{r["hold_s"]:.1f}s</text>'
            )
    for s in range(0, int(end) + 1, 30):
        x = x0 + s * scale
        parts.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{base}" stroke="#d1cfc5" stroke-dasharray="2 3"/><text x="{x:.1f}" y="{top - 6}" font-size="10" fill="#87867f">{s // 60}:{s % 60:02d}</text>'
        )
    parts.append("</svg>")
    legend = '<p class="cap">막대 높이 = 전체 디머(30~100) · 아래 띠 = SIDE·WASH 색(<span style="color:#13b5d1">■</span> cyan · <span style="color:#f1c27d">■</span> warm white) · 막대 안에서는 아무것도 바뀌지 않습니다(페이저·속도 줄 0).</p>'
    return '<figure class="fig">' + "".join(parts) + legend + "</figure>"


body = convert(src)
page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOVE ATTACK 기존 앱 연출 기준선</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&family=Noto+Serif+KR:wght@700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
:root{{--ivory:#FAF9F5;--paper:#FFFFFF;--slate:#141413;--clay:#D97757;--clay-d:#B85C3E;--oat:#E3DACC;--olive:#788C5D;
--g100:#F0EEE6;--g300:#D1CFC5;--g500:#87867F;--g700:#3D3D3A;
--sans:"Noto Sans KR",system-ui,sans-serif;--serif:"Noto Serif KR",Georgia,serif;--mono:"JetBrains Mono",ui-monospace,monospace;
--max-width:1100px;--radius-panel:12px;--border:1.5px solid var(--g300)}}
body{{background:var(--ivory);color:var(--slate);font-family:var(--sans);line-height:1.65;margin:0;padding:24px 16px}}
main{{max-width:var(--max-width);margin:0 auto}}
h1{{font-family:var(--serif);font-size:1.7rem}} h2{{font-family:var(--serif);border-bottom:2px solid var(--oat);padding-bottom:4px;margin-top:2.2em}}
.lead{{background:var(--g100);border-left:4px solid var(--clay);padding:10px 14px;border-radius:8px}}
.tw{{overflow-x:auto;background:var(--paper);border:var(--border);border-radius:var(--radius-panel)}}
table{{border-collapse:collapse;width:100%;font-size:.86rem}} th,td{{padding:6px 8px;border-bottom:1px solid var(--g100);text-align:left;white-space:nowrap}}
th{{background:var(--g100)}} code{{font-family:var(--mono);font-size:.85em;background:var(--g100);padding:1px 4px;border-radius:4px}}
.tag{{font-size:.75em;padding:1px 6px;border-radius:10px;margin:0 2px}} .tag.m{{background:#dfe8d2;color:#3f5326}} .tag.e{{background:#f6dccf;color:#8a3d22}}
.fig{{background:var(--paper);border:var(--border);border-radius:var(--radius-panel);padding:12px;margin:12px 0}} .tl{{width:100%;height:auto}}
.cap{{font-size:.85rem;color:var(--g700);margin:6px 0 0}}
@media print{{body{{background:#fff}}}}
</style></head><body><main>
{body}
</main></body></html>
"""
OUT.write_text(page, "utf-8")
print(OUT, len(page.encode()))
