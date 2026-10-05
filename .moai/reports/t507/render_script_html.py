# ruff: noqa: E501 — HTML·CSS·한국어 안내문 템플릿 문자열을 그대로 싣는 렌더러라 줄 길이 규칙을 끈다
"""M1 대본(md) → 감독 검토용 HTML (moai-domain-html-report, basic 등급).

실행: python3 .moai/reports/t507/render_script_html.py <script.md> <map.json> <out.html>
대본 md 가 정본이다. HTML 은 사람이 읽기 쉽게 보충(쉬운 말 안내·곡 흐름 그림)만 더한다.
"""

import html
import json
import re
import sys
from pathlib import Path

md_path, map_path, out_path = sys.argv[1:4]
src = Path(md_path).read_text(encoding="utf-8")
bars = json.loads(Path(map_path).read_text())["bars"]


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


def convert(text: str) -> str:
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            t = (
                "<div class='tw'><table><thead><tr>"
                + "".join(f"<th>{inline(c)}</th>" for c in head)
                + "</tr></thead><tbody>"
            )
            for r in body:
                cls = " class='acc'" if len(r) == 6 and r[1] == "강조" else ""
                t += f"<tr{cls}>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,4}) (.*)", ln)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
        elif re.match(r"^\d+\. ", ln):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


# 곡 흐름 그림: 마디별 음량 막대 + 브레이크(주황) + 강조(빨간 표식)
med = sorted(b["rms"] for b in bars[2:82])[40]
W, H, pad = 820, 200, 30
bw = (W - 2 * pad) / len(bars)
accent = {19: "드롭", 35: "코러스진입", 51: "드롭+스트로브", 67: "마지막코러스+스트로브"}
svg = [f"<svg viewBox='0 0 {W} {H + 60}' role='img' aria-label='Club Diver 곡 흐름과 강조 위치'>"]
for k, b in enumerate(bars):
    rel = min(b["rms"] / med, 1.2)
    h = rel / 1.2 * (H - 40)
    brk = b["bar"] in (18, 34, 50, 66)
    col = "var(--clay)" if brk else ("var(--g300)" if b["bar"] in (1, 2, 83) else "var(--olive)")
    x = pad + k * bw
    svg.append(
        f"<rect x='{x:.1f}' y='{H - h:.1f}' width='{bw - 1:.1f}' height='{h:.1f}' fill='{col}'><title>{b['bar']}마디 {b['start_s']:.1f}초</title></rect>"
    )
    if b["bar"] in accent:
        svg.append(
            f"<polygon points='{x + bw / 2:.1f},{H - h - 6:.1f} {x + bw / 2 - 6:.1f},{H - h - 18:.1f} {x + bw / 2 + 6:.1f},{H - h - 18:.1f}' fill='#C0392B'/>"
        )
        svg.append(
            f"<text x='{x + bw / 2:.1f}' y='{H - h - 22:.1f}' text-anchor='middle' class='ax'>{b['bar']} {accent[b['bar']]}</text>"
        )
    if b["bar"] in (3, 18, 34, 50, 66, 83):
        svg.append(
            f"<text x='{x + bw / 2:.1f}' y='{H + 14}' text-anchor='middle' class='ax'>{b['bar']}</text>"
        )
svg.append(
    f"<text x='{W / 2}' y='{H + 34}' text-anchor='middle' class='ax'>마디 번호 · 초록 = 음량 · 주황 = 브레이크(덜어내는 자리) · 빨간 삼각형 = 강조(블라인더·스트로브)</text></svg>"
)
chart = "\n".join(svg)

lead = """
<div class="lead">
<p><strong>이 문서는 무엇인가요?</strong> Club Diver 한 곡에 조명을 어떻게 놓을지 적은 <b>연출 대본</b>이에요.
코드도, 콘솔 명령도 없어요. 감독님이 읽고 "이대로 콘솔에 올려 보자" 또는 "여기는 바꾸자"를 정하는 문서예요.</p>
<p><strong>두 층으로 나눠 읽으면 쉬워요.</strong> <b>박자 층</b>은 한 장면 안에서 박에 맞춰 움직이는 것(펄스, 체이스 한 칸, 색·위치 한 단계)이고,
<b>강조 층</b>은 블라인더·스트로브처럼 큰 순간에만 쓰는 것이에요. 표에서 분홍 줄이 강조 층이에요.</p>
<p><strong>예를 들면</strong> — 18마디(0:28.8)에서 소리가 직전의 63%로 줄어요. 대본은 여기서 펄스와 체이스를 끄고 빛을 20%로 내려요.
다음 19마디 첫 박(0:30.5)에서 블라인더를 한 번 터뜨리고, 무빙을 위로 열어요. "비워 뒀다가 터뜨리기"가 이 곡 연출의 기본 모양이고, 16마디마다 네 번 반복돼요. 갈수록 조금씩 커져요.</p>
</div>
"""

check = """
<div class="lead"><p><strong>감독님이 봐 주실 것</strong></p><ol>
<li>강조 네 곳(19·35·51·67마디)의 크기 순서가 맞는지 — 35 &lt; 19 &lt; 51 &lt; 67.</li>
<li>45~49마디를 보컬 구간으로 보고 낮춘 것이 맞는지. 아니면 앞 장면을 그대로 이어 가요.</li>
<li>67~80마디의 반 박 체이스가 너무 빠르지 않은지.</li>
<li>각 줄에 "어울릴 것 같다 / 아니다"를 표시해 주시면 M2 손 시연의 순서를 정할 때 써요.</li>
</ol></div>
"""

body = convert(src)
body = body.replace("<h2>", lead + "\n<h2>", 1)
body = body.replace("<h2>2. ", chart + "\n<h2>2. ", 1)
body = body.replace("<h2>5. ", check + "\n<h2>5. ", 1)

page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Club Diver 연출 대본</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
:root{{--ivory:#FAF9F5;--paper:#FFF;--slate:#141413;--clay:#D97757;--clay-d:#B85C3E;--oat:#E3DACC;--olive:#788C5D;
--g100:#F0EEE6;--g300:#D1CFC5;--g500:#87867F;--g700:#3D3D3A;
--sans:"Pretendard",system-ui,-apple-system,sans-serif;--mono:"JetBrains Mono",ui-monospace,"SF Mono",monospace;
--max-width:1100px;--radius-panel:12px}}
body{{margin:0;background:var(--ivory);color:var(--slate);font:15px/1.7 var(--sans)}}
main{{max-width:var(--max-width);margin:0 auto;padding:32px 16px 80px}}
h1{{font-size:26px;line-height:1.35}} h2{{margin-top:44px;border-bottom:2px solid var(--oat);padding-bottom:6px}}
code{{font:13px var(--mono);background:var(--g100);padding:1px 5px;border-radius:4px}}
.tw{{overflow-x:auto;margin:12px 0}} table{{border-collapse:collapse;width:100%;background:var(--paper);font-size:13.5px}}
th,td{{border:1px solid var(--g300);padding:6px 8px;text-align:left;vertical-align:top}} th{{background:var(--g100);white-space:nowrap}}
tr.acc td{{background:#F9E1DA}}
.lead{{background:var(--paper);border-left:4px solid var(--clay);border-radius:var(--radius-panel);padding:8px 18px;margin:20px 0}}
svg{{width:100%;height:auto;background:var(--paper);border-radius:var(--radius-panel);border:1.5px solid var(--g300);margin:12px 0}}
svg .ax{{font-size:11px;fill:var(--g700)}} hr{{border:0;border-top:1px solid var(--g300);margin:32px 0}}
@media print{{body{{background:#fff}} .tw{{overflow:visible}}}}
</style></head><body><main>
{body}
</main></body></html>"""
Path(out_path).write_text(page, encoding="utf-8")
print(out_path, len(page.encode()))
