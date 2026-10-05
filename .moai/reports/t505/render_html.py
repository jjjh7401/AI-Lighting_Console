"""reports/clubdiver-music-map-20261005.md → .html (moai-domain-html-report, basic 등급).

md 를 그대로 옮기고, 사람이 읽을 보충(쉬운 말 안내·마디 음량 그래프·흐름도)만 HTML 에 더한다.
"""

# ruff: noqa: E501 — HTML·CSS·한국어 안내문 템플릿 문자열을 그대로 싣는 렌더러라 줄 길이 규칙을 끈다
import html
import json
import re
import sys
from pathlib import Path

md_path, json_path, out_path = sys.argv[1:4]
src = Path(md_path).read_text(encoding="utf-8")
bars = json.loads(Path(json_path).read_text())["bars"]


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = s.replace("[잰 값]", '<span class="tag m">잰 값</span>')
    s = s.replace("[추정]", '<span class="tag e">추정</span>')
    s = s.replace("[미확정]", '<span class="tag u">미확정</span>')
    return s


def convert(text: str) -> str:
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1 : j])) + "</code></pre>")
            i = j + 1
            continue
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
                cls = (
                    " class='mo'" if len(r) == 9 and r[8] and not r[8].startswith("앱 구간") else ""
                )
                t += f"<tr{cls}>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,4}) (.*)", ln)
        if m:
            lvl = len(m.group(1))
            hid = "s" + str(len(out))
            out.append(f"<h{lvl} id='{hid}'>{inline(m.group(2))}</h{lvl}>")
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


# 마디 음량 그래프 (인라인 SVG)
med = sorted(b["rms"] for b in bars[2:82])[40]
W, H, pad = 820, 220, 30
bw = (W - 2 * pad) / len(bars)
svg = [f"<svg viewBox='0 0 {W} {H + 40}' role='img' aria-label='마디별 음량'>"]
y1 = H - (1.0 / 1.2) * (H - 20)
svg.append(
    f"<line x1='{pad}' x2='{W - pad}' y1='{y1:.1f}' y2='{y1:.1f}' stroke='var(--g500)' stroke-dasharray='4 3'/>"
)
svg.append(f"<text x='{W - pad}' y='{y1 - 4:.1f}' text-anchor='end' class='ax'>중앙값 1.0</text>")
for k, b in enumerate(bars):
    rel = b["rms"] / med
    h = min(rel, 1.2) / 1.2 * (H - 20)
    brk = b["bar"] in (18, 34, 50, 66)
    col = "var(--clay)" if brk else ("var(--g300)" if b["bar"] in (1, 2, 83) else "var(--olive)")
    svg.append(
        f"<rect x='{pad + k * bw:.1f}' y='{H - h:.1f}' width='{bw - 1:.1f}' height='{h:.1f}' fill='{col}'>"
        f"<title>{b['bar']}마디 {b['start_s']:.1f}초 {b['section']} 음량 {rel:.2f}</title></rect>"
    )
    if b["bar"] in (3, 18, 34, 50, 66, 83):
        svg.append(
            f"<text x='{pad + k * bw + bw / 2:.1f}' y='{H + 14}' text-anchor='middle' class='ax'>{b['bar']}</text>"
        )
svg.append(
    f"<text x='{W / 2}' y='{H + 32}' text-anchor='middle' class='ax'>마디 번호 (주황 = 브레이크, 16마디 간격)</text></svg>"
)
chart = "\n".join(svg)

lead = """
<div class="lead">
<p><strong>이 문서는 무엇인가요?</strong> 조명 연출 대본을 쓰려면 먼저 "음악의 어디에서 무슨 일이 일어나는지"를 알아야 해요.
이 문서는 Club Diver 한 곡을 컴퓨터로 분석해서 그 지도를 그린 거예요.</p>
<p><strong>용어 몇 개</strong> — <b>BPM</b>: 1분에 박이 몇 번 오는지(빠르기). <b>마디</b>: 박 4개를 한 묶음으로 센 단위.
<b>다운비트</b>: 마디의 첫 박, 사람들이 "하나!" 하고 세는 자리. <b>브레이크</b>: 비트가 잠깐 빠지거나 줄어드는 순간.
<b>클릭 트랙</b>: 원곡 위에 "틱" 소리를 덧입혀, 컴퓨터가 찾은 박이 맞는지 귀로 확인하는 파일.</p>
<p><strong>예를 들면</strong> — 18마디(28.76초)에서 음량이 직전의 63%로 떨어졌다가, 19마디(30.48초)에서 다시 차올라요.
조명으로 치면 "18마디에서 덜어내고, 19마디 첫 박에서 터뜨리는" 자리예요. 이런 자리가 16마디마다 한 번씩, 모두 네 번 있어요.</p>
</div>
"""

flow = """
<pre class="mermaid">
flowchart LR
  A[원곡 mp3] --> B[앱과 같은 박 추적<br/>BPM 139.67]
  B --> C[타악/화성 분리]
  C --> D[킥·스네어 후보]
  C --> E[다운비트 근거 4개]
  B --> F[마디별 음량]
  F --> G[브레이크 4 · 재진입 4]
  E --> H[83마디 표]
  D --> H
  G --> H
  B --> I[클릭 wav → 감독이 귀로 확인]
</pre>
<noscript><p>흐름: 원곡 → 앱과 같은 박 추적(BPM 139.67) → 타악/화성 분리 → 킥·스네어 후보와 다운비트 근거 →
마디별 음량에서 브레이크·재진입 → 83마디 표. 박 추적 결과는 클릭 wav로 만들어 감독이 귀로 확인한다.</p></noscript>
"""

check = """
<div class="lead"><p><strong>직접 확인해 볼 것</strong></p><ol>
<li><code>Club_Diver_beats_clicks_phase0.wav</code>를 틀고 높은 "틱"이 "하나"에 오는지 들어 보세요. 아니면 <code>phase3</code> 파일을 들어 보세요.</li>
<li>18·50마디(28.8초, 83.6초)에서 소리가 확 줄어드는지 들어 보세요. 그래프의 주황 막대 자리예요.</li>
<li><code>Rain_appbpm_hi_midpoint_lo.wav</code>에서 발이 높은 틱에만 맞는지(76), 낮은 틱까지 다 맞는지(152) 들어 보세요.</li>
</ol></div>
"""

body = convert(src)
body = body.replace("<h2 id=", lead + "\n<h2 id=", 1)
body = re.sub(
    r"(<h3 id='[^']+'>2\.1 [^<]*</h3>)", chart.replace("\\", "\\\\") + r"\n\1", body, count=1
)
body = re.sub(r"(<h2 id='[^']+'>1\. [^<]*</h2>)", r"\1" + flow.replace("\\", "\\\\"), body, count=1)
body = re.sub(r"(<h2 id='[^']+'>부록 A)", check.replace("\\", "\\\\") + r"\n\1", body, count=1)

page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Club Diver 음악 순간 지도</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
:root{{--ivory:#FAF9F5;--paper:#FFF;--slate:#141413;--clay:#D97757;--clay-d:#B85C3E;--oat:#E3DACC;--olive:#788C5D;
--g100:#F0EEE6;--g300:#D1CFC5;--g500:#87867F;--g700:#3D3D3A;
--sans:"Pretendard",system-ui,-apple-system,sans-serif;--mono:"JetBrains Mono",ui-monospace,"SF Mono",monospace;
--max-width:960px;--radius-panel:12px}}
body{{margin:0;background:var(--ivory);color:var(--slate);font:15px/1.7 var(--sans)}}
main{{max-width:var(--max-width);margin:0 auto;padding:32px 16px 80px}}
h1{{font-size:26px;line-height:1.35}} h2{{margin-top:44px;border-bottom:2px solid var(--oat);padding-bottom:6px}}
h3{{margin-top:28px}} code{{font:13px var(--mono);background:var(--g100);padding:1px 5px;border-radius:4px}}
pre{{background:var(--paper);border:1.5px solid var(--g300);border-radius:8px;padding:12px;overflow-x:auto}}
.tw{{overflow-x:auto;margin:12px 0}} table{{border-collapse:collapse;width:100%;background:var(--paper);font-size:13.5px}}
th,td{{border:1px solid var(--g300);padding:6px 8px;text-align:left;vertical-align:top}} th{{background:var(--g100)}}
tr.mo td{{background:#FBEDE6}}
.lead{{background:var(--paper);border-left:4px solid var(--clay);border-radius:var(--radius-panel);padding:8px 18px;margin:20px 0}}
.tag{{font-size:11.5px;padding:1px 6px;border-radius:10px;white-space:nowrap}}
.tag.m{{background:#E4EBDC;color:#3E4E2C}} .tag.e{{background:var(--oat);color:var(--g700)}} .tag.u{{background:#F6DDD3;color:var(--clay-d)}}
svg{{width:100%;height:auto;background:var(--paper);border-radius:var(--radius-panel);border:1.5px solid var(--g300)}}
svg .ax{{font-size:11px;fill:var(--g700)}} hr{{border:0;border-top:1px solid var(--g300);margin:32px 0}}
@media print{{body{{background:#fff}} .tw{{overflow:visible}}}}
</style></head><body><main>
{body}
</main>
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
mermaid.initialize({{startOnLoad:true,theme:"base",themeVariables:{{primaryColor:"#FAF9F5",primaryTextColor:"#141413",
primaryBorderColor:"#D97757",lineColor:"#87867F",secondaryColor:"#E3DACC",tertiaryColor:"#F0EEE6"}}}});
</script></body></html>"""
Path(out_path).write_text(page, encoding="utf-8")
print(out_path, len(page.encode()))
