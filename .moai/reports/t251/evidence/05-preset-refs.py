"""t251 — cue-ex 89행이 실제로 어느 프리셋 ID 를 참조하는지 전수한다. 콘솔 접촉 0."""

import re
from collections import Counter
from pathlib import Path

from server.lxseq.cue_parser import parse_cue_csv

SONG = Path("src/Lighting_Designer/03_곡파일_Sugar")
REF = re.compile(r"\b(DIM|COL|POS|BM|FX)\.[0-9A-Za-z]+")


def main() -> None:
    text = (SONG / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv").read_text(encoding="utf-8-sig")
    parsed = parse_cue_csv(text)
    by_prefix: Counter[str] = Counter()
    rows_touching: Counter[str] = Counter()
    ids: Counter[str] = Counter()
    for rec in parsed.records:
        cells = (rec.dim_raw, rec.col_raw, rec.pos_raw, rec.bm_raw, rec.fx_raw)
        seen_prefix = set()
        for cell in cells:
            for match in REF.finditer(cell or ""):
                token = match.group(0)
                ids[token] += 1
                by_prefix[match.group(1)] += 1
                seen_prefix.add(match.group(1))
        for prefix in seen_prefix:
            rows_touching[prefix] += 1

    print("### 참조 총수 (셀 등장 횟수)")
    for prefix, n in by_prefix.most_common():
        print(f"  {prefix:4} {n:4} 회 · 그 계열을 쓰는 행 {rows_touching[prefix]:3}")
    print("\n### Dim 열이 프리셋 참조인가 숫자인가 (앞 8행)")
    for rec in parsed.records[:8]:
        print(
            f"  cue {rec.cue_no:6} {rec.group:10} dim={rec.dim_raw!r:10} "
            f"col={rec.col_raw!r:10} fx={rec.fx_raw!r}"
        )
    print("\n### 시트에 등장하는 프리셋 ID 전체")
    for token, n in sorted(ids.items()):
        print(f"  {token:10} {n} 회")


if __name__ == "__main__":
    main()
