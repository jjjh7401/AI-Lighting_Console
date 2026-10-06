"""reports/loveattack-music-map-20261006.md → .html (t509, t505 렌더러 사본) (moai-domain-html-report, basic 등급).

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


# 마디 음량 그래프 (인라인 SVG) — t509: 빌드업(연두)·큰 히트(빨강)·킥 멈춤/브레이크(주황)
med = sorted(b["rms"] for b in bars)[len(bars) // 2]
W, H, pad = 820, 220, 30
bw = (W - 2 * pad) / len(bars)
BUILD = set(range(14, 18)) | set(range(42, 46))
HIT = {18, 46, 68}
DROP = {33, 61, 62, 67, 82}
svg = [f"<svg viewBox='0 0 {W} {H + 40}' role='img' aria-label='LOVE ATTACK 마디별 음량'>"]
y1 = H - (1.0 / 1.2) * (H - 20)
svg.append(
    f"<line x1='{pad}' x2='{W - pad}' y1='{y1:.1f}' y2='{y1:.1f}' stroke='var(--g500)' stroke-dasharray='4 3'/>"
)
svg.append(f"<text x='{W - pad}' y='{y1 - 4:.1f}' text-anchor='end' class='ax'>중앙값 1.0</text>")
for k, b in enumerate(bars):
    rel = b["rms"] / med
    h = min(rel, 1.2) / 1.2 * (H - 20)
    n = b["bar"]
    col = (
        "#C0392B"
        if n in HIT
        else "var(--clay)"
        if n in DROP
        else "#A7B98A"
        if n in BUILD
        else "var(--olive)"
    )
    svg.append(
        f"<rect x='{pad + k * bw:.1f}' y='{H - h:.1f}' width='{bw - 1:.1f}' height='{h:.1f}' fill='{col}'>"
        f"<title>{n}마디 {b['start_s']:.1f}초 {b['section']} 음량 {rel:.2f}</title></rect>"
    )
    if n in (7, 14, 18, 33, 42, 46, 61, 62, 68, 82):
        svg.append(
            f"<text x='{pad + k * bw + bw / 2:.1f}' y='{H + 14}' text-anchor='middle' class='ax'>{n}</text>"
        )
svg.append(
    f"<text x='{W / 2}' y='{H + 32}' text-anchor='middle' class='ax'>마디 번호 · 연두 = 빌드업 · 빨강 = 후렴 진입 히트 · 주황 = 덜어내는 마디(킥 멈춤·브레이크)</text></svg>"
)
chart = "\n".join(svg)

lead = """
<div class="lead">
<p><strong>이 문서는 무엇인가요?</strong> 리센느 「LOVE ATTACK」을 컴퓨터로 분석해서, 곡의 어디에서 무슨 일이 일어나는지 지도를 그린 거예요.
다음 단계에서 조명 연출 대본을 쓸 때 이 지도를 뼈대로 써요. 앱이 같은 곡을 어떻게 나누는지도 나란히 비교했어요.</p>
<p><strong>용어 몇 개</strong> — <b>BPM</b>: 1분에 박이 몇 번 오는지(이 곡은 112.35). <b>마디</b>: 박 4개 묶음(이 곡은 2.14초).
<b>다운비트</b>: 마디의 첫 박, "하나!" 하고 세는 자리. <b>빌드업</b>: 후렴 앞에서 소리가 점점 커지며 기대를 쌓는 구간.
<b>클릭 트랙</b>: 원곡 위에 "틱" 소리를 덧입혀 컴퓨터가 찾은 박이 맞는지 귀로 확인하는 파일.</p>
<p><strong>예를 들면</strong> — 14~17마디(0:29~0:38)는 소리가 네 마디 연달아 커져요(0.74 → 0.99). 그다음 18마디(0:37.9)에서
저음이 평소의 4.4배로 터지며 후렴이 시작돼요. 조명으로 치면 "네 마디 동안 쌓다가 18마디 첫 박에 연다"는 자리예요. 같은 모양이 42~46마디에 한 번 더 나와요.</p>
</div>
"""

flow = """
<pre class="mermaid">
flowchart LR
  A[원곡 mp3] --> B[앱 분석 경로 그대로<br/>BPM 112.35 · 구간 10개]
  A --> C[같은 박 위에서 측정<br/>마디 음량 · 저역 · 다운비트]
  C --> D[빌드업 2 · 큰 히트 · 킥 멈춤 3]
  B --> E[나란히 비교]
  D --> E
  C --> F[클릭 wav → 감독이 귀로 확인]
</pre>
<noscript><p>흐름: 원곡을 앱 분석 경로(BPM 112.35, 구간 10개)와 같은 박 위의 측정(마디 음량·저역·다운비트)으로 나눠 보고,
측정에서 빌드업·큰 히트·킥 멈춤을 찾아 앱 구간과 나란히 비교한다. 박은 클릭 wav로 감독이 귀로 확인한다.</p></noscript>
"""

check = """
<div class="lead"><p><strong>직접 확인해 볼 것</strong></p><ol>
<li><code>LOVE_ATTACK_beats_clicks_phase1.wav</code>를 틀고 높은 "틱"이 "하나"에 오는지 들어 보세요. 특히 0:37.9와 1:37.9의 후렴 진입에서요. 아니라면 <code>phase0</code> 파일을 들어 보세요.</li>
<li>14~17마디(0:29~0:38)에서 소리가 점점 커지는지, 18마디에서 크게 터지는지 들어 보세요. 그래프의 연두·빨강 막대 자리예요.</li>
<li>2:14~2:21(63~65마디)이 노래 없이 연주만 나오는 브릿지인지 들어 보세요.</li>
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
<title>LOVE ATTACK 음악 순간 지도</title>
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
