# ruff: noqa: E501 — HTML·CSS·한국어 안내문 템플릿 문자열을 그대로 싣는 렌더러라 줄 길이 규칙을 끈다
"""M1 대본(md) → 감독 검토용 HTML (moai-domain-html-report, basic 등급).

실행: uv run python .moai/reports/t514/render_script_html.py <script.md> <map.json> <out.html>
(t511 렌더러 사본에 움직임 효과 안내만 더함)
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


# 곡 흐름 그림: 마디별 음량 막대 + 빌드업(연두) + 덜어냄(주황) + 강조(빨간 표식)
med = sorted(b["rms"] for b in bars)[len(bars) // 2]
W, H, pad = 820, 200, 30
bw = (W - 2 * pad) / len(bars)
accent = {18: "코러스진입", 46: "코러스진입", 63: "드롭·스트로브", 67: "마지막코러스(4박)"}
BUILD = set(range(14, 18)) | set(range(42, 46))
REST = {33, 61, 67, 82}
svg = [f"<svg viewBox='0 0 {W} {H + 60}' role='img' aria-label='LOVE ATTACK 곡 흐름과 강조 위치'>"]
for k, b in enumerate(bars):
    rel = min(b["rms"] / med, 1.2)
    h = rel / 1.2 * (H - 40)
    n = b["bar"]
    col = "var(--clay)" if n in REST else ("#A7B98A" if n in BUILD else "var(--olive)")
    x = pad + k * bw
    svg.append(
        f"<rect x='{x:.1f}' y='{H - h:.1f}' width='{bw - 1:.1f}' height='{h:.1f}' fill='{col}'><title>{n}마디 {b['start_s']:.1f}초</title></rect>"
    )
    if n in accent:
        svg.append(
            f"<polygon points='{x + bw / 2:.1f},{H - h - 6:.1f} {x + bw / 2 - 6:.1f},{H - h - 18:.1f} {x + bw / 2 + 6:.1f},{H - h - 18:.1f}' fill='#C0392B'/>"
        )
        svg.append(
            f"<text x='{x + bw / 2:.1f}' y='{H - h - 22:.1f}' text-anchor='middle' class='ax'>{n} {accent[n]}</text>"
        )
    if n in (7, 14, 18, 33, 42, 46, 61, 63, 67, 82):
        svg.append(
            f"<text x='{x + bw / 2:.1f}' y='{H + 14}' text-anchor='middle' class='ax'>{n}</text>"
        )
svg.append(
    f"<text x='{W / 2}' y='{H + 34}' text-anchor='middle' class='ax'>마디 번호 · 연두 = 빌드업 · 주황 = 비우는 마디 · 빨간 삼각형 = 강조(블라인더·스트로브)</text></svg>"
)
chart = "\n".join(svg)

lead = """
<div class="lead">
<p><strong>이 문서는 무엇인가요?</strong> 리센느 「LOVE ATTACK」 한 곡에 조명을 어떻게 놓을지 적은 <b>연출 대본</b>이에요.
코드도, 콘솔 명령도 없어요. 감독님이 읽고 "이대로 콘솔에 올려 보자" 또는 "여기는 바꾸자"를 정하는 문서예요.</p>
<p><strong>두 층으로 나눠 읽으면 쉬워요.</strong> <b>박자 층</b>은 한 장면 안에서 박에 맞춰 움직이는 것(펄스, 체이스 한 칸, 색·위치 한 단계, 움직임 효과)이고,
<b>강조 층</b>은 블라인더·스트로브처럼 큰 순간에만 쓰는 것이에요. 표에서 분홍 줄이 강조 층이에요.</p>
<p><strong>이번에 더한 것 — 무빙의 움직임(Pan/Tilt)</strong> — 감독님 지적대로 초안은 무빙을 켜고 끄기만 했어요. 이제 무빙이 박자에 맞춰 직접 움직여요.
벌스 1은 느린 파도(2마디에 한 번), 프리코러스는 점점 빨라지는 좌우 왕복, 코러스 1은 줄지어 따라가는 좌우 흔들기, 벌스 2는 느린 원,
코러스 2는 좌우가 엇갈리는 빠른 흔들기, 드롭은 크게 휘젓는 발리후, 마지막 코러스는 가장 큰 원이에요.
한 구간에서 무빙은 움직이거나 깜빡이거나 둘 중 하나만 해요. 킥이 멈추는 마디에서는 움직임도 멈춰요.</p>
<p><strong>예를 들면</strong> — 14~17마디(0:29~0:37)는 노래가 점점 차오르는 빌드업이에요. 대본은 여기서 무빙의 좌우 왕복을 마디마다 두 배씩 빠르게 하다가,
17마디 3·4박에서 모든 움직임을 끊고 비워요. 그리고 18마디 첫 박(0:37.9, 감독님이 귀로 확인한 자리)에서 블라인더를 한 번 터뜨리고 핑크로 바꿔요.</p>
<p><strong>앱이 지금 만드는 것과 다른 점</strong> — 지금 앱은 후렴 하나를 30초 넘게 한 장면으로 둬요. 이 대본은 같은 동작을 8마디(약 17초)보다 길게 반복하지 않고,
펄스는 실제 킥이 오는 박의 역광에만 줘요.</p>
</div>
"""

check = """
<div class="lead"><p><strong>감독님이 봐 주실 것</strong></p><ol>
<li>강조 네 곳의 크기 순서 — 18마디(블라인더 60%) &lt; 46마디(블라인더 100%) &lt; 63마디(스트로브 2박) &lt; 67마디 4박(블라인더 + 스트로브 1마디).</li>
<li>63마디 드롭에 블라인더 없이 스트로브만 쓴 것이 맞는지.</li>
<li>76~81마디의 반 박 체이스(0.27초 간격)가 너무 빠르지 않은지.</li>
<li>무빙 움직임의 모양과 빠르기 — 특히 드롭의 발리후(1박에 한 바퀴)와 마지막 코러스의 큰 서클(2박에 한 바퀴)이 너무 빠르거나 크지 않은지.</li>
<li>무빙이 움직이는 구간과 깜빡이는 구간의 배분(대본 §2의 표)이 맞는지.</li>
<li>파스텔 세 색(라벤더·핑크·피치)과 차가운 화이트의 흐름이 곡과 어울리는지. 정확한 색 값은 나중에 맞춰요.</li>
<li>각 줄에 "어울릴 것 같다 / 아니다"를 표시해 주시면 M2 손 시연의 순서를 정할 때 써요.</li>
</ol></div>
"""

body = convert(src)
body = body.replace("<h2>", lead + "\n<h2>", 1)
body = body.replace("<h2>2. ", chart + "\n<h2>2. ", 1)
body = body.replace("<h2>6. ", check + "\n<h2>6. ", 1)

page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOVE ATTACK 연출 대본</title>
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
