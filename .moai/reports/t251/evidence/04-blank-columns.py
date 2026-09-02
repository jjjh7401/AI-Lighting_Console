"""t251 — 「그 계열 셀을 비우면」 몇 행이 열리나. 시트 편집은 감독 결정이라 갈라 잰다.

콘솔 접촉 0 · 시트 파일 수정 0 (메모리에서만 비운다).
"""

import csv
import io
from pathlib import Path

from server.lxseq.cue_mapper import map_cues
from server.lxseq.cue_parser import parse_cue_csv

SONG = Path("src/Lighting_Designer/03_곡파일_Sugar")
CSV_PATH = SONG / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv"
GROUPS = (
    "BACK",
    "WASH-U",
    "WASH-D",
    "KEY",
    "SIDE-L",
    "SIDE-R",
    "MOVER-U",
    "MOVER-D",
    "HAZE",
    "STROBE",
    "BLIND",
    "ALL",
    "LED-W",
    "MOVER-ALL",
    "SIDE-ALL",
    "WASH-ALL",
    "ODD",
    "EVEN",
    "FOH",
)
COL = tuple(f"COL.0{n}" for n in range(1, 9))
POS = tuple(f"POS.0{n}" for n in range(1, 9))
BM = tuple(f"BM.0{n}" for n in range(1, 6))
FX = tuple(f"FX.0{n}" for n in range(1, 9))


def blanked(columns: set[str]) -> str:
    text = CSV_PATH.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = list(reader.fieldnames or ())
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in reader:
        for name in fields:
            if name.strip() in columns:
                row[name] = ""
        writer.writerow(row)
    return out.getvalue()


def run(label: str, text: str, preset_names) -> None:
    parsed = parse_cue_csv(text)
    result = map_cues(
        parsed.records,
        declared_cues=parsed.cue_numbers,
        sequence_name="Sugar",
        sequence_section=dict(objects=[], truncated=False),
        group_slots=dict((n, i) for i, n in enumerate(GROUPS, 1)),
        preset_slots=dict((n, i) for i, n in enumerate(preset_names, 1)),
    )
    rows = sum(len(cue.rows) for cue in result.planned) if result.planned else 0
    print(
        f"  {label:46} 계획 행 {rows:3} · 계획 큐 {len(result.planned):2} "
        f"· 보류 행 {len(result.held):2}"
    )


def main() -> None:
    original = CSV_PATH.read_text(encoding="utf-8-sig")
    print("### 시트 원본 그대로")
    run("COL 만 콘솔에 (오늘 코드로 갈 수 있는 최대)", original, COL)
    run("COL+POS", original, COL + POS)
    run("COL+POS+FX", original, COL + POS + FX)
    run("COL+POS+BM+FX (전부)", original, COL + POS + BM + FX)

    print("\n### BM 열을 비웠을 때 (감독 시트 결정 — BM.03·04 는 기종 능력 부재 확정)")
    no_bm = blanked({"BM"})
    run("COL 만", no_bm, COL)
    run("COL+POS", no_bm, COL + POS)
    run("COL+POS+FX", no_bm, COL + POS + FX)

    print("\n### BM·FX 둘 다 비웠을 때 (FX importer 없이 가는 길)")
    no_bm_fx = blanked({"BM", "FX", "FX Rate", "FX Phase", "FX Width"})
    run("COL 만", no_bm_fx, COL)
    run("COL+POS", no_bm_fx, COL + POS)


if __name__ == "__main__":
    main()
