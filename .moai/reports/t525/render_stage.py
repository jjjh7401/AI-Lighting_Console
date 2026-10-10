# ruff: noqa: E501 — 아래 TEMPLATE 은 한 파일짜리 HTML·CSS·JS 원문이라 줄을 자르지 않는다
"""t525 — 측정 JSON 으로 무대 2D 그림(위에서 본 X·Y, 객석에서 본 X·Z) HTML 을 만든다.

입력(이 카드에서 잰 것만):
    r1_spatial_bulk.json  — 앱 경로 read_spatial_fixtures 로 읽은 86대 좌표·회전
    r3_group_fields.json  — 그룹 SELECTIONDATA (응답기 240바이트 한도로 그룹당 앞 2칸만)
    r4_patch_tree.json    — 픽스처별 SUBFIXTUREINDEX (sf_index → fid 대응)
    lead_stage_crop.png   — 리드 시안 무대 칸 캡처(비교용)

실행 (프로젝트 루트에서):
    .venv/bin/python .moai/reports/t525/render_stage.py reports/ldbeat-stage-from-patch-20261010.html
"""

import base64
import json
import sys
from pathlib import Path

HERE = Path(".moai/reports/t525")

# 패치 이름 앞부분 → 색 (참고 보기 전용. 그룹 소속이 아니다)
PREFIX_COLOR = {
    "KEY": "#f2c14e",
    "FOH": "#e8e6df",
    "BLIND": "#ffffff",
    "STROBE": "#9be7ff",
    "HAZE": "#8a8a8a",
    "MOVER-U": "#5fb3ff",
    "MOVER-D": "#2f7fe0",
    "BACK": "#b06cff",
    "SIDE-L": "#ff5fa2",
    "SIDE-R": "#ff8fc0",
    "WASH-U": "#7a6cff",
    "WASH-D": "#5a4ccc",
}
GROUP_COLOR = {"MOVER-ALL": "#5fb3ff", "BACK": "#b06cff", "SIDE-L": "#ff5fa2", "BLIND": "#ffffff"}


def load():
    spatial = json.loads((HERE / "r1_spatial_bulk.json").read_text())
    groups = json.loads((HERE / "r3_group_fields.json").read_text())
    tree = json.loads((HERE / "r4_patch_tree.json").read_text())

    def val(node, key):
        for read in node.get("reads") or []:
            if read.get("n") == key and read.get("ok"):
                return read.get("v")
        return None

    sf_to_fid = {int(val(n, "SUBFIXTUREINDEX")): int(val(n, "FID")) for n in tree["tree"]}
    known = {}  # fid -> group name (SELECTIONDATA 로 확인된 것만)
    group_rows = []
    for entry in groups["groups"].values():
        name = entry["state"]["node"]["name"]
        sel = next(v for v in entry["values"] if v.get("n") == "SELECTIONDATA")
        sfs = [e["sf_index"] for e in json.loads(sel["v"])]
        fids = [sf_to_fid.get(s) for s in sfs]
        for fid in fids:
            if fid is not None:
                known[fid] = name
        group_rows.append(
            {"group": name, "sf": sfs, "fids": fids, "truncated": sel.get("truncated")}
        )
    return spatial["fixtures"], known, group_rows


def prefix(name):
    return name.rsplit(" ", 1)[0]


def svg_view(fixtures, known, axis, title):
    """axis: 'y' (위에서) 또는 'z' (객석에서). 1 m = SCALE px."""
    scale, pad = 34, 40
    xs = [f["x"] for f in fixtures]
    vs = [f[axis] for f in fixtures]
    x0, x1 = min(xs) - 1, max(xs) + 1
    v0, v1 = min(vs) - 1, max(vs) + 1
    w = int((x1 - x0) * scale + pad * 2)
    h = int((v1 - v0) * scale + pad * 2)

    def px(x):
        return pad + (x - x0) * scale

    def py(v):
        return pad + (v1 - v) * scale  # 위로 갈수록 값이 큼

    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{title}">']
    # 1 m 격자
    for gx in range(int(x0), int(x1) + 1):
        out.append(
            f'<line x1="{px(gx):.1f}" y1="{pad}" x2="{px(gx):.1f}" y2="{h - pad}" class="grid"/>'
        )
    for gv in range(int(v0), int(v1) + 1):
        out.append(
            f'<line x1="{pad}" y1="{py(gv):.1f}" x2="{w - pad}" y2="{py(gv):.1f}" class="grid"/>'
        )
    # 원점 축
    out.append(f'<line x1="{px(0):.1f}" y1="{pad}" x2="{px(0):.1f}" y2="{h - pad}" class="axis"/>')
    if v0 <= 0 <= v1:
        out.append(
            f'<line x1="{pad}" y1="{py(0):.1f}" x2="{w - pad}" y2="{py(0):.1f}" class="axis"/>'
        )
    if axis == "y":
        out.append(f'<text x="{w / 2}" y="{pad - 14}" class="cap">무대 안쪽 (Y +)</text>')
        out.append(f'<text x="{w / 2}" y="{h - 10}" class="cap">객석 (Y −)</text>')
    else:
        out.append(f'<text x="{w / 2}" y="{pad - 14}" class="cap">위 (Z +)</text>')
        out.append(f'<text x="{w / 2}" y="{h - 10}" class="cap">바닥 (Z 0)</text>')
    out.append(f'<text x="{pad - 6}" y="{h / 2}" class="cap end">X −</text>')
    out.append(f'<text x="{w - pad + 6}" y="{h / 2}" class="cap start">X +</text>')
    # 줄 이름표: 패치 이름 앞부분마다 가장 왼쪽 장비 옆에 한 번
    firsts = {}
    for f in fixtures:
        key = prefix(f["name"])
        if key not in firsts or f["x"] < firsts[key]["x"]:
            firsts[key] = f
    # 객석에서 본 그림은 같은 높이 트러스에 줄이 겹쳐 이름표가 서로 덮이므로 위에서 본 그림에만 단다
    for key, f in firsts.items() if axis == "y" else ():
        out.append(
            f'<text x="{px(f["x"]) - 9:.1f}" y="{py(f[axis]) - 9:.1f}" class="lab">{key}</text>'
        )
    # 객석에서 볼 때는 뒤(무대 안쪽) 장비를 먼저 그려 앞 장비가 위에 오게 한다.
    # 소속이 확인된 장비는 맨 나중에 그린다 — 같은 자리의 다른 장비에 덮이지 않게.
    order = sorted(fixtures, key=lambda f: -f["y"]) if axis == "z" else list(fixtures)
    order.sort(key=lambda f: f["fid"] in known)
    for f in order:
        group = known.get(f["fid"])
        pcol = PREFIX_COLOR.get(prefix(f["name"]), "#999")
        gcol = GROUP_COLOR.get(group, "#5a5a63") if group else "#5a5a63"
        rot = f"rot {f.get('rotx', 0):.0f}/{f.get('roty', 0):.0f}/{f.get('rotz', 0):.0f}"
        tip = (
            f"{f['name']} (fid {f['fid']}) · x {f['x']:.1f} y {f['y']:.1f} z {f['z']:.1f} · {rot}"
            + (f" · 그룹 {group} (SELECTIONDATA 확인)" if group else " · 그룹 소속 모름")
        )
        ring = ' class="known"' if group else ""
        out.append(
            f'<circle cx="{px(f["x"]):.1f}" cy="{py(f[axis]):.1f}" r="6" '
            f'data-g="{gcol}" data-p="{pcol}" fill="{gcol}"{ring}><title>{tip}</title></circle>'
        )
    out.append("</svg>")
    return "\n".join(out)


def main(target):
    fixtures, known, group_rows = load()
    lead_png = base64.b64encode((HERE / "lead_stage_crop.png").read_bytes()).decode()
    legend_p = "".join(
        f'<span><i style="background:{c}"></i>{k}</span>' for k, c in PREFIX_COLOR.items()
    )
    legend_g = (
        "".join(f'<span><i style="background:{c}"></i>{k}</span>' for k, c in GROUP_COLOR.items())
        + '<span><i style="background:#5a5a63"></i>소속 모름</span>'
    )
    rows = "".join(
        f"<tr><td>{r['group']}</td><td>{', '.join(map(str, r['sf']))}</td>"
        f"<td>{', '.join(map(str, r['fids']))}</td><td>{'예' if r['truncated'] else '아니오'}</td></tr>"
        for r in group_rows
    )
    html = TEMPLATE.format(
        top=svg_view(fixtures, known, "y", "위에서 본 무대"),
        front=svg_view(fixtures, known, "z", "객석에서 본 무대"),
        lead=lead_png,
        legend_p=legend_p,
        legend_g=legend_g,
        rows=rows,
        n=len(fixtures),
        k=len(known),
    )
    Path(target).write_text(html)
    print(target, len(html), "bytes", len(fixtures), "fixtures", len(known), "known members")


TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>패치 좌표 무대 그림</title>
<style>
:root{{--bg:#101014;--panel:#18181f;--ink:#e8e6df;--mute:#8a889a;--grid:#23232c;--axis:#3a3a48;--line:#2a2a34}}
@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]){{--bg:#f6f5f1;--panel:#fff;--ink:#1d1c22;--mute:#6b697a;--grid:#ecebe6;--axis:#c9c7c0;--line:#e2e0da}}}}
:root[data-theme="dark"]{{--bg:#101014;--panel:#18181f;--ink:#e8e6df;--mute:#8a889a;--grid:#23232c;--axis:#3a3a48;--line:#2a2a34}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
main{{max-width:1240px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:17px;margin:28px 0 8px}}
.sub{{color:var(--mute);font-size:13px}}
.verdict{{background:var(--panel);border-left:4px solid #f2c14e;padding:12px 16px;border-radius:6px;margin:16px 0}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media (max-width:820px){{.grid2{{grid-template-columns:1fr}}}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}}
.card h3{{margin:0 0 8px;font-size:14px}}
svg{{width:100%;height:auto;display:block}}
svg .grid{{stroke:var(--grid);stroke-width:1}} svg .axis{{stroke:var(--axis);stroke-width:1.5}}
svg .cap{{fill:var(--mute);font-size:12px;text-anchor:middle}} svg .cap.end{{text-anchor:end}} svg .cap.start{{text-anchor:start}}
svg circle{{stroke:#000;stroke-opacity:.35}} svg circle.known{{stroke:#f2c14e;stroke-width:2.5;stroke-opacity:1}}
img{{max-width:100%;border-radius:6px;display:block}}
.legend[hidden]{{display:none}} svg .lab{{fill:var(--mute);font-size:10px;text-anchor:end}}
.front{{max-width:900px}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--mute);margin:8px 0}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.tabs button{{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px 12px;margin-right:6px;cursor:pointer;font:inherit;font-size:13px}}
.tabs button[aria-pressed="true"]{{border-color:#f2c14e;color:#f2c14e}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}}
.wrap{{overflow-x:auto}}
</style></head><body><main>
<h1>패치 좌표로 그린 무대</h1>
<div class="sub">카드 t525 · 2026-10-10 · grandMA3 onPC 2.4.2 · 응답기 1.6.5 · 읽기만(콘솔 쓰기 0) · 앱 경로 <code>read_spatial_fixtures</code>로 {n}대 전부 읽음</div>
<div class="verdict"><b>결론 — 조건부 가능.</b> 장비 위치는 앱 경로만으로 {n}대 전부 읽혀 지금 바로 그릴 수 있어요(아래 두 그림). 그룹 소속은 콘솔에 들어 있지만(그룹의 <code>SELECTIONDATA</code>) 응답기가 값 하나를 240바이트에서 잘라 그룹당 앞 2대만 보여요. 그래서 지금은 {k}대만 그룹 색이고 나머지는 회색이에요. 응답기에 긴 값 나눠 읽기를 붙이면 전부 칠할 수 있어요.</div>

<h2>위에서 본 무대 (X·Y)와 리드 시안</h2>
<div class="tabs" role="group" aria-label="색 기준"><button id="bg" aria-pressed="true">그룹 소속(확인된 것만)</button><button id="bp" aria-pressed="false">패치 이름(참고)</button></div>
<div class="legend" id="lg">{legend_g}</div>
<div class="legend" id="lp" hidden>{legend_p}</div>
<div class="grid2">
<div class="card"><h3>실제 패치 좌표 — 위에서 (1칸 = 1 m, 아래가 객석)</h3>{top}</div>
<div class="card"><h3>리드 시안 무대 칸 (손그림, 2026-10-08)</h3><img alt="리드 시안 무대 칸 캡처" src="data:image/png;base64,{lead}"></div>
</div>

<h2>객석에서 본 무대 (X·Z)</h2>
<div class="card front">{front}</div>

<h2>그룹 소속 — 읽힌 만큼</h2>
<div class="wrap"><table><tr><th>그룹</th><th>sf_index (SELECTIONDATA)</th><th>fid (SUBFIXTUREINDEX 대응)</th><th>값 잘림</th></tr>{rows}</table></div>
<p class="sub">노란 테두리 = 그룹 소속이 콘솔에서 확인된 장비. 점에 마우스를 올리면 이름·fid·좌표·회전이 나와요. 패치 이름 색은 이름 앞부분으로 칠한 참고용이고, 그룹 소속과는 다른 정보예요.</p>
</main>
<script>
const set=g=>{{document.querySelectorAll("svg circle").forEach(c=>c.setAttribute("fill",g?c.dataset.g:c.dataset.p));
document.getElementById("bg").setAttribute("aria-pressed",g);document.getElementById("bp").setAttribute("aria-pressed",!g);
document.getElementById("lg").hidden=!g;document.getElementById("lp").hidden=g;}};
document.getElementById("bg").onclick=()=>set(true);document.getElementById("bp").onclick=()=>set(false);
</script></body></html>
"""

if __name__ == "__main__":
    main(sys.argv[1])
