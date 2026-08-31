"""t191 - 색인 예산 분해: 주소(경로)가 먹는 자리 대 본문이 먹는 자리.

카드가 안 쟀다고 적은 값: 색인 총 바이트 중 경로 비율.
리드가 요구한 첫 걸음: 형태 비율(새 줄 대 형제 붙임) + 항목당 본문 바이트 분포.

우주 주의(t147): 색인은 셋이지만 25KB/200행 상한은 MEMORY.md 에만 걸린다.
하위 둘은 포인터로만 참조되고 세션 시작에 안 읽히므로 대조군으로만 잰다.
"""

import re
import statistics as st

MEMDIR = (
    "/Users/studiox/.claude/projects/"
    "-Users-studiox-Documents-Claude-Code-AI-Lighting-Console/memory"
)
INDICES = (
    "MEMORY.md",
    "index-overflow-craft-and-tooling.md",
    "index-console-grandma3.md",
)
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
NL = chr(10)


def nb(text):
    """UTF-8 바이트 수. 한글은 1자 3바이트라 len() 과 다르다."""
    return len(text.encode("utf-8"))


def split_forms(raw):
    """줄이 나르는 .md 링크 개수로 형태를 가른다."""
    own = []
    sib = []
    none = []
    for line in raw.split(NL):
        md = [p for p in LINK.findall(line) if p[1].endswith(".md")]
        if not md:
            none.append((line, md))
        elif len(md) == 1:
            own.append((line, md))
        else:
            sib.append((line, md))
    return own, sib, none


def decompose(rows):
    """링크 있는 줄을 표시/경로/문법/전체 바이트로 가른다."""
    disp = sum(nb(d) for _, md in rows for d, _ in md)
    path = sum(nb(t) for _, md in rows for _, t in md)
    syn = sum(4 * len(md) for _, md in rows)
    tot = sum(nb(line) + 1 for line, _ in rows)
    return disp, path, syn, tot


def spread(values):
    """최소/중앙/최대/평균을 한 줄로."""
    v = sorted(values)
    q1 = v[len(v) // 4]
    q3 = v[3 * len(v) // 4]
    med = st.median(v)
    mean = st.mean(v)
    return f"min={v[0]} p25={q1} med={med:.0f} p75={q3} max={v[-1]} mean={mean:.1f}"


def report(name):
    with open(f"{MEMDIR}/{name}", encoding="utf-8") as fh:
        raw = fh.read()
    own, sib, none = split_forms(raw)
    total = nb(raw)
    od, op, oy, ot = decompose(own)
    sd, sp, sy, stt = decompose(sib)
    nt = sum(nb(line) + 1 for line, _ in none)
    n_sib = sum(len(md) for _, md in sib)

    print("=" * 62)
    print(name)
    print("=" * 62)
    print(f"TOTAL bytes={total} newlines={raw.count(NL)}")
    print(f"FORM  entries own={len(own)} sib={n_sib}")
    print(f"      lines own={len(own)} sib={len(sib)} nolink={len(none)}")
    print(f"LINEB own={ot} ({100.0 * ot / total:.1f}%)")
    print(f"      sib={stt} ({100.0 * stt / total:.1f}%)")
    print(f"      nolink={nt} ({100.0 * nt / total:.1f}%)")
    print(f"OWN   disp={od} path={op} syn={oy} body={ot - od - op - oy}")
    print(f"SIB   disp={sd} path={sp} syn={sy} body={stt - sd - sp - sy}")
    print(f"CARDQ path={op + sp} of {total} = {100.0 * (op + sp) / total:.1f}%")

    own_body = [
        nb(line) + 1 - sum(nb(d) + nb(t) + 4 for d, t in md)
        for line, md in own
    ]
    if own_body:
        print(f"OWNBODY {spread(own_body)}")
    if own:
        print(f"OWNLINE {spread([nb(line) + 1 for line, _ in own])}")
    if sib:
        frag = [nb(d) + nb(t) + 7 for _, md in sib for d, t in md]
        print(f"SIBITEM {spread(frag)}  (link 4B + separator 3B included)")

    paths = [t for _, md in own + sib for _, t in md]
    disps = [d for _, md in own + sib for d, _ in md]
    if not paths:
        return
    print(f"PATHLEN n={len(paths)} {spread([nb(p) for p in paths])}")
    print(f"DISPLEN n={len(disps)} {spread([nb(d) for d in disps])}")
    plen = [nb(p) for p in paths]
    for cap in (24, 16, 8):
        saved = sum(max(0, x - cap) for x in plen)
        pct = 100.0 * saved / total
        print(f"  OPT1 cap path at {cap}B -> saves {saved} B ({pct:.1f}% of file)")
    saved = sum(x - 3 for x in plen if x > 3)
    pct = 100.0 * saved / total
    print(f"  OPT2 path -> 3B key   -> saves {saved} B ({pct:.1f}% of file)")
    print()


def main():
    for name in INDICES:
        report(name)


if __name__ == "__main__":
    main()
