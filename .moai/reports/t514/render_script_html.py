# ruff: noqa: E501 — HTML·CSS·한국어 안내문 템플릿 문자열을 그대로 싣는 렌더러라 줄 길이 규칙을 끈다
"""M1 대본(md) → 감독 검토용 HTML (moai-domain-html-report, basic 등급).

실행: uv run python .moai/reports/t514/render_script_html.py <script.md> <map.json> <out.html>
(t511 렌더러 사본 + t514 감독 요청 2026-10-06: 효과 종류별 색 하이라이트·필터·타임라인, 칸 안 줄바꿈)
대본 md 가 정본이다. HTML 은 사람이 읽기 쉽게 보충(쉬운 말 안내·곡 흐름 그림)만 더한다.

효과 분류(기계적, 리드 지시): '연출' 칸 첫머리(킥/스네어 펄스·체이스 한 칸·색/위치 한 단계·움직임 효과)
+ BLIND/STROBE 글자(「~는 쓰지 않는다」 부정은 뺀다). 색/위치 한 단계는 색 이름이 있으면 '색 변경',
위치 말이 있으면 '위치 변경', 둘 다면 둘 다, 둘 다 없으면 '기타'. 분류 개수는 stdout 에 찍는다.
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


# ── 효과 종류 (dataviz validate_palette.js light: ALL CHECKS PASS, 대비 WARN 3색은 글자 칩으로 보완)
#   (키, 라벨, 색, 인쇄용 띠 모양, 띠 굵기 px, 밑줄 모양)
KINDS = [
    ("color", "색 변경", "#CC79A7", "solid", 8, "solid"),
    ("pos", "위치 변경", "#0072B2", "double", 9, "double"),
    ("move", "Pan/Tilt 움직임", "#009E73", "dashed", 8, "dashed"),
    ("pulse", "킥/스네어 펄스", "#E69F00", "dotted", 8, "dotted"),
    ("chase", "체이스", "#56B4E9", "solid", 4, "wavy"),
    ("blind", "BLIND", "#D55E00", "solid", 14, "solid"),
    ("strobe", "STROBE", "#7E57C2", "double", 14, "double"),
]
ETC = ("etc", "기타(밝기 등)", "#87867F", "solid", 2, "solid")
KMAP = {k[0]: k for k in [*KINDS, ETC]}
PREFIX = {
    "킥/스네어 펄스": "pulse",
    "체이스 한 칸": "chase",
    "움직임 효과": "move",
    "색/위치 한 단계": "step",
}
COLOR_RE = re.compile(r"라벤더|핑크|피치|화이트|흰색|세 색")
POS_RE = re.compile(r"위치|높이|위로|바닥 쪽|관객 쪽|무대 쪽|사선|각도|위쪽 한 점")
NEG_RE = re.compile(r"(BLIND|STROBE)는 쓰지 않는다")
MARK_RE = re.compile(
    "|".join(
        f"(?P<{k}>{p})"
        for k, p in [
            (
                "move",
                r"엇갈린 팬 웨이브|팬 웨이브|틸트 웨이브|가속 스윕|큰 서클|서클|발리후|한 바퀴 [^,.]{0,12}?박",
            ),
            ("blind", r"BLIND(?!는 쓰지)[^,.—]{0,20}"),
            ("strobe", r"STROBE(?!는 쓰지)[^,.—]{0,24}"),
            ("color", r"차가운 화이트|라벤더|핑크|피치|화이트|흰색|세 색"),
            (
                "pos",
                r"위치를 한 칸|위로 활짝 연다|위로 연다|위로 연|가장 넓은 각도|바닥 쪽|관객 쪽|무대 중간 높이|위쪽 한 점|좌우 사선",
            ),
            ("pulse", r"킥 박에[^,.]{0,10}|1·2·4박|1·3박|마디 4박에 한 번씩"),
            ("chase", r"ODD/EVEN|반 박마다|2·4박에 번갈아"),
        ]
    )
)


def kinds_of(row: list[str]) -> list[str]:
    """행 하나의 효과 종류(리드 지시 규칙 그대로, 기계적)."""
    act = row[3].replace("**", "")
    if row[1] == "강조":
        clean = NEG_RE.sub("", act)
        return [k for k, w in (("blind", "BLIND"), ("strobe", "STROBE")) if w in clean]
    cat = next((v for p, v in PREFIX.items() if act.startswith(p)), "etc")
    if cat != "step":
        return [cat]
    body = act.split(" — ", 1)[-1]
    found = [k for k, rx in (("color", COLOR_RE), ("pos", POS_RE)) if rx.search(body)]
    return found or ["etc"]


def is_stop(row: list[str]) -> bool:
    """「킥/스네어 펄스 멈춤·줄임」 행 — 분류는 규칙대로 펄스지만, 실제로는 펄스를 끄는 자리다.
    칩 글자와 타임라인 모양(속이 빈 막대)으로 구분해 「멈춘 마디에 펄스가 있다」로 읽히지 않게 한다."""
    return row[3].startswith(("킥/스네어 펄스 멈춤", "킥/스네어 펄스 줄임"))


def marked(s: str) -> str:
    """형광펜: 핵심어를 종류 색으로. html.escape 뒤, code/strong 앞에 적용한다."""
    s = html.escape(s, quote=False)
    s = MARK_RE.sub(lambda m: f"<mark class='m-{m.lastgroup}'>{m.group(0)}</mark>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


GROUP_SPLIT = re.compile(r",\s+(?:그리고\s+)?(?=WASH|FOH|BACK|MOVER|SIDE|BLIND|STROBE|ODD|EVEN)")


def sentences(s: str) -> list[str]:
    """문장(마침표) 단위로 끊고, 한 문장 안에서도 대상 그룹이 바뀌는 쉼표에서 한 번 더 끊는다."""
    out = []
    for p in re.split(r"\.\s+", s.strip()):
        out += [q.strip().rstrip(".") for q in GROUP_SPLIT.split(p)]
    return [q for q in out if q]


CITE_RE = re.compile(r"^(§\d|곡 조사 §)")
PAREN_CITE = re.compile(r"\((§[^)]*|곡 조사 §[^)]*)\)")


def chip(k: str) -> str:
    return f"<span class='chip c-{k}'>{KMAP[k][1]}</span>"


def cell_act(row: list[str], kinds: list[str]) -> str:
    """연출 칸: 「종류 — 내용」의 종류는 칩으로, 문장마다 한 줄, 줄마다 해당 칩."""
    act = row[3].replace("**", "")
    head, _, rest = act.partition(" — ")
    if head not in PREFIX:
        rest = act
    lines = sentences(rest)
    out = []
    for n, ln in enumerate(lines):
        if row[1] == "강조":
            ks = [
                k for k, w in (("blind", "BLIND"), ("strobe", "STROBE")) if w in NEG_RE.sub("", ln)
            ]
        elif kinds[0] in ("pulse", "chase", "move"):
            ks = kinds if n == 0 else []
        else:
            ks = [k for k, rx in (("color", COLOR_RE), ("pos", POS_RE)) if rx.search(ln)]
            if n == 0 and not ks and kinds == ["etc"]:
                ks = ["etc"]
        chips = "".join(chip(k) for k in ks)
        if n == 0 and is_stop(row):
            label = "펄스 멈춤" if "멈춤" in row[3][:12] else "펄스 줄임"
            chips = f"<span class='chip c-pulse stop'>{label}</span>"
            ln = ln.split(" — ", 1)[-1]
        out.append(f"<div class='ln'>{chips}{marked(ln)}</div>")
    return "".join(out)


def cell_reason(s: str) -> str:
    """잇는 방식·이유 칸: '—' 와 '.' 로 끊고, 근거 인용은 작은 회색 줄로 따로."""
    out = []
    for sent in sentences(s.replace("**", "")):
        for seg in [x.strip() for x in sent.split(" — ") if x.strip()]:
            cites = PAREN_CITE.findall(seg)
            seg = PAREN_CITE.sub("", seg).strip()
            if seg:
                cls = "cite" if CITE_RE.match(seg) else "ln"
                out.append(f"<div class='{cls}'>{html.escape(seg)}</div>")
            out += [f"<div class='cite'>{html.escape(c)}</div>" for c in cites]
    return "".join(out)


def cell_time(s: str) -> str:
    t, _, rest = s.partition(" (")
    return f"<div>{html.escape(t)}</div>" + (
        f"<div class='sub'>({html.escape(rest)}</div>" if rest else ""
    )


def script_table(head: list[str], body: list[list[str]], counts: dict) -> str:
    t = (
        "<div class='tw'><table class='script'><thead><tr>"
        + "".join(f"<th>{html.escape(c)}</th>" for c in head)
        + "</tr></thead><tbody>"
    )
    for r in body:
        ks = kinds_of(r)
        for k in ks:
            counts[k] = counts.get(k, 0) + 1
        k1 = KMAP[ks[0]]
        style = f"border-left:{k1[4]}px {k1[3]} {k1[2]}"
        if len(ks) > 1:
            style += f";box-shadow:inset 6px 0 0 {KMAP[ks[1]][2]}"
        cls = "acc" if r[1] == "강조" else ""
        t += (
            f"<tr class='{cls}' data-k='{' '.join(ks)}'>"
            f"<td style='{style}'>{cell_time(r[0])}</td><td>{html.escape(r[1])}</td><td>{html.escape(r[2])}</td>"
            f"<td>{cell_act(r, ks)}</td><td>{cell_reason(r[4])}</td><td>{cell_reason(r[5])}</td></tr>"
        )
    return t + "</tbody></table></div>"


def row_bars(t: str, bar_of) -> list[tuple[int, int]]:
    """시각 칸 → 마디 구간 목록 (타임라인용)."""
    inner = t.split("(", 1)[1] if "(" in t else ""
    if m := re.match(r"앞박~(\d+)마디", inner):
        return [(0, int(m.group(1)))]
    if m := re.match(r"(\d+)~(\d+)마디", inner):
        return [(int(m.group(1)), int(m.group(2)))]
    if m := re.match(r"([\d·]+)마디", inner):
        return [(int(x), int(x)) for x in m.group(1).split("·")]
    if inner.startswith("앞박"):
        return [(0, 0)]
    if m := re.search(r"(\d+)초", inner):
        b = bar_of(float(m.group(1)))
        return [(b, b)]
    return []


SCRIPT_ROWS: list[list[str]] = []
COUNTS: dict[str, int] = {}


def effects_block() -> tuple[str, str]:
    """범례·필터(위에 고정) + 한눈에 타임라인(인라인 SVG, 종류별 가로줄 7개)."""
    starts = [b["start_s"] for b in bars]

    def bar_of(sec: float) -> int:
        return max(i for i, s in enumerate(starts) if s <= sec) + bars[0]["bar"]

    used = [k for k in [*KINDS, ETC] if COUNTS.get(k[0])]
    btns = "".join(
        f"<button type='button' class='fb c-{k[0]}' data-k='{k[0]}' aria-pressed='true'>"
        f"<span class='sw' style='border-left:{k[4]}px {k[3]} {k[2]}'></span>{k[1]} <small>{COUNTS[k[0]]}행</small></button>"
        for k in used
    )
    bar_ui = (
        "<div class='legend' role='group' aria-label='효과 종류 필터'><strong>효과 종류</strong>"
        f"{btns}<button type='button' class='fb all'>모두 켜기</button></div>"
        "<p class='hint'>버튼을 누르면 그 종류의 행을 숨기거나 다시 보여요. 표의 왼쪽 띠·칩·형광펜과 아래 그림이 같은 색이에요. "
        "인쇄하면 띠 모양(실선·이중선·파선·점선·굵기)과 칩 글자로 구분돼요.</p>"
    )
    W, L, R, top, rh = 1040, 150, 16, 34, 26
    last = 84
    xw = (W - L - R) / last

    def x(b: float) -> float:
        return L + b * xw

    svg = [
        f"<svg class='tl' viewBox='0 0 {W} {top + rh * len(KINDS) + 34}' role='img' aria-label='효과 종류별 마디 타임라인'>"
    ]
    for b in range(0, last + 1, 4):
        svg.append(
            f"<line x1='{x(b):.1f}' x2='{x(b):.1f}' y1='{top - 4}' y2='{top + rh * len(KINDS)}' class='grid'/>"
        )
        svg.append(
            f"<text x='{x(b):.1f}' y='{top + rh * len(KINDS) + 16}' text-anchor='middle' class='ax'>{b}</text>"
        )
    for n, k in enumerate(KINDS):
        y = top + n * rh
        svg.append(
            f"<text x='{L - 8}' y='{y + rh / 2 + 4:.1f}' text-anchor='end' class='lab'>{k[1]}</text>"
        )
        for r in SCRIPT_ROWS:
            if k[0] not in kinds_of(r):
                continue
            stop = k[0] == "pulse" and is_stop(r)
            paint = (
                f"fill='none' stroke='{k[2]}' stroke-width='2' stroke-dasharray='3 2'"
                if stop
                else f"fill='{k[2]}'"
            )
            for a, b in row_bars(r[0], bar_of):
                tip = html.escape(f"{r[0]} · {'펄스 멈춤/줄임' if stop else k[1]}")
                svg.append(
                    f"<rect class='tb c-{k[0]}' data-k='{k[0]}' x='{x(a) + 1:.1f}' y='{y + 4}' width='{max((b - a + 1) * xw - 2, 3):.1f}' height='{rh - 8}' rx='3' {paint}><title>{tip}</title></rect>"
                )
    # 63·67 은 4마디 간격이라 글자가 겹친다 — 63 은 선 왼쪽, 67 은 선 오른쪽으로 붙인다
    for b, name, anchor, dx in (
        (18, "후렴 진입", "middle", 0),
        (46, "후렴 진입", "middle", 0),
        (63, "드롭", "end", -3),
        (67, "마지막 코러스", "start", 3),
    ):
        svg.append(
            f"<line x1='{x(b):.1f}' x2='{x(b):.1f}' y1='{top - 10}' y2='{top + rh * len(KINDS)}' class='mk'/>"
        )
        svg.append(
            f"<text x='{x(b) + dx:.1f}' y='{top - 14}' text-anchor='{anchor}' class='lab'>{b} {name}</text>"
        )
    svg.append(
        f"<text x='{(L + W) / 2:.0f}' y='{top + rh * len(KINDS) + 32}' text-anchor='middle' class='ax'>마디 번호(0~83)</text></svg>"
    )
    return (
        "<h2>효과 한눈에 보기</h2>"
        + "\n".join(svg)
        + "<p class='hint'>막대에 마우스를 올리면 대본의 시각이 보여요. 세로 점선은 후렴 진입(18·46마디), 드롭(63마디), 마지막 코러스(67마디)예요. "
        "펄스 줄의 속이 빈 점선 막대는 펄스를 끄거나 줄이는 자리("
        + "·".join(str(a) for r in SCRIPT_ROWS if is_stop(r) for a, _ in row_bars(r[0], bar_of))
        + "마디)예요.</p>",
        bar_ui,
    )


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
            if head == ["시각", "층", "모멘트유형", "연출", "잇는 방식", "이유"]:
                SCRIPT_ROWS.extend(body)
                out.append(script_table(head, body, COUNTS))
                continue
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
        # 63·67 글자가 겹쳐서(t514 화면 확인) 63 은 왼쪽, 67 은 오른쪽으로 붙인다
        anchor, dx = {63: ("end", 4), 67: ("start", -4)}.get(n, ("middle", 0))
        svg.append(
            f"<text x='{x + bw / 2 + dx:.1f}' y='{H - h - 22:.1f}' text-anchor='{anchor}' class='ax'>{n} {accent[n]}</text>"
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


def tint(hexc: str, a: float) -> str:
    r, g, b = (int(hexc[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{a})"


effect_css = "\n".join(
    f".chip.c-{k}{{border-color:{c};background:{tint(c, 0.16)}}} "
    f"mark.m-{k}{{background:{tint(c, 0.26)};text-decoration-color:{c};text-decoration-style:{u}}} "
    f".fb.c-{k}[aria-pressed=true]{{border-color:{c};background:{tint(c, 0.12)}}}"
    for k, _, c, _s, _w, u in [*KINDS, ETC]
)

body = convert(src)
timeline, bar_ui = effects_block()
body = body.replace("<h2>3. ", timeline + "\n<h2>3. ", 1)
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
{effect_css}
.legend{{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:var(--paper);border:1.5px solid var(--g300);border-radius:10px;padding:8px 10px;margin:8px 0}}
.fb{{font:13px var(--sans);display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border:1.5px solid var(--g300);border-radius:999px;background:var(--paper);color:var(--slate);cursor:pointer}}
.fb[aria-pressed=false]{{opacity:.35;text-decoration:line-through}} .fb.all{{margin-left:auto}} .fb small{{color:var(--g500)}}
.sw{{display:inline-block;width:0;height:16px}}
.hint{{font-size:13px;color:var(--g700)}}
.chip.stop{{border-style:dashed;background:transparent}} .chip{{display:inline-block;font-size:11.5px;font-weight:600;line-height:1.5;padding:0 7px;margin-right:6px;border-radius:999px;border:1.5px solid;color:var(--slate);white-space:nowrap}}
table.script td{{line-height:1.55}} table.script td:nth-child(2),table.script td:nth-child(3){{white-space:nowrap}}
table.script td:nth-child(1){{min-width:96px}} table.script td:nth-child(4){{min-width:300px}} table.script .ln{{margin:2px 0}} table.script .sub{{font-size:12px;color:var(--g500)}}
table.script .cite{{font-size:11.5px;color:var(--g500);margin:1px 0}} tr.acc .ln{{font-weight:700}}
tr.hide{{display:none}} .tl .grid{{stroke:var(--g100)}} .tl .mk{{stroke:var(--g700);stroke-dasharray:3 3}} .tl .lab{{font-size:12px;fill:var(--slate)}}
.tl rect.off{{opacity:.08}} mark{{color:inherit;padding:0 2px;border-radius:3px;text-decoration-line:underline;text-decoration-thickness:2px;text-underline-offset:3px}}
@media print{{body{{background:#fff}} .tw{{overflow:visible}} .legend{{position:static}} .fb.all{{display:none}} *{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body><main>
{bar_ui}
{body}
</main>
<script>
(() => {{
  const btns = [...document.querySelectorAll('.fb[data-k]')];
  const on = () => new Set(btns.filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.k));
  const apply = () => {{
    const s = on();
    document.querySelectorAll('table.script tbody tr').forEach(tr => {{
      tr.classList.toggle('hide', !tr.dataset.k.split(' ').some(k => s.has(k)));
    }});
    document.querySelectorAll('.tl rect[data-k]').forEach(r => r.classList.toggle('off', !s.has(r.dataset.k)));
  }};
  btns.forEach(b => b.addEventListener('click', () => {{
    b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); apply();
  }}));
  document.querySelector('.fb.all').addEventListener('click', () => {{ btns.forEach(b => b.setAttribute('aria-pressed', 'true')); apply(); }});
}})();
</script></body></html>"""
Path(out_path).write_text(page, encoding="utf-8")
print(out_path, len(page.encode()))
print("rows", len(SCRIPT_ROWS), "kind counts (rows)", {KMAP[k][1]: COUNTS[k] for k in COUNTS})
print("multi-kind rows", sum(1 for r in SCRIPT_ROWS if len(kinds_of(r)) > 1))
print("pulse stop/reduce rows", [r[0] for r in SCRIPT_ROWS if is_stop(r)])
print("etc rows", [r[0] for r in SCRIPT_ROWS if kinds_of(r) == ["etc"]])
