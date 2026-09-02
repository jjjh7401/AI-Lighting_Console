"""t251 — cue-ex 89행이 프리셋 배정 상태에 따라 몇 행 열리는지 잰다. 콘솔 접촉 0.

시나리오별로 `preset_slots` 만 바꾸고 나머지는 고정한다 — 한 축만 움직인다.
"""

from collections import Counter
from pathlib import Path

from server.lxseq.cue_mapper import map_cues
from server.lxseq.cue_parser import parse_cue_csv

SONG = Path("src/Lighting_Designer/03_곡파일_Sugar")

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
DIM = tuple(f"DIM.{n}" for n in ("FULL", "SHOW", "MID", "LOW", "GLOW", "OUT"))
COL = tuple(f"COL.0{n}" for n in range(1, 9))
POS = tuple(f"POS.0{n}" for n in range(1, 9))
BM = tuple(f"BM.0{n}" for n in range(1, 6))
FX = tuple(f"FX.0{n}" for n in range(1, 9))


def slots(names):
    return dict((name, i) for i, name in enumerate(names, start=1))


def run(label: str, preset_names) -> None:
    text = (SONG / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv").read_text(encoding="utf-8-sig")
    parsed = parse_cue_csv(text)
    result = map_cues(
        parsed.records,
        declared_cues=parsed.cue_numbers,
        sequence_name="Sugar",
        sequence_section=dict(objects=[], truncated=False),
        group_slots=slots(GROUPS),
        preset_slots=slots(preset_names),
    )
    planned_rows = sum(len(cue.rows) for cue in result.planned) if result.planned else 0
    causes = Counter(c for h in result.held for c in h.hold_classes)
    print(f"\n### {label}")
    print(f"  프리셋 배정 {len(preset_names)}종 · 거절코드={result.refusal}")
    print(
        f"  계획된 행 {planned_rows} · 보류 행 {len(result.held)} "
        f"· 빠진 큐 {len(result.cues_held)} · 영상 호출 {len(result.video_calls)}"
    )
    for cause, n in causes.most_common():
        print(f"    보류사유 {cause:22} {n} 행")


def main() -> None:
    run("① 오늘 — LXSEQ 프리셋이 콘솔에 0종", ())
    run("② dim 6 만 저장", DIM)
    run("③ dim 6 + col 8 저장", DIM + COL)
    run("④ + pos 8", DIM + COL + POS)
    run("⑤ + bm 5", DIM + COL + POS + BM)
    run("⑥ + fx 8 (전부)", DIM + COL + POS + BM + FX)


if __name__ == "__main__":
    main()
