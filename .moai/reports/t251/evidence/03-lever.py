"""t251 — 계열별 기여를 순서 artifact 없이 잰다: 단독 추가 · 하나만 빼기. 콘솔 접촉 0."""

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
FAMILIES = {
    "DIM": tuple(f"DIM.{n}" for n in ("FULL", "SHOW", "MID", "LOW", "GLOW", "OUT")),
    "COL": tuple(f"COL.0{n}" for n in range(1, 9)),
    "POS": tuple(f"POS.0{n}" for n in range(1, 9)),
    "BM": tuple(f"BM.0{n}" for n in range(1, 6)),
    "FX": tuple(f"FX.0{n}" for n in range(1, 9)),
}


def slots(names):
    return dict((name, i) for i, name in enumerate(names, start=1))


def planned_rows(preset_names) -> tuple[int, int]:
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
    rows = sum(len(cue.rows) for cue in result.planned) if result.planned else 0
    return rows, len(result.planned)


def main() -> None:
    base, base_cues = planned_rows(())
    allp = sum(FAMILIES.values(), ())
    full, full_cues = planned_rows(allp)
    print(f"기준선(프리셋 0종): 계획 행 {base} · 계획 큐 {base_cues}")
    print(f"전부 배정:          계획 행 {full} · 계획 큐 {full_cues}\n")

    print("### 단독 추가 — 이 계열 하나만 콘솔에 있을 때")
    for name, members in FAMILIES.items():
        rows, cues = planned_rows(members)
        print(f"  {name:4} 단독 → 계획 행 {rows:3} (기준선 대비 {rows - base:+3}) · 큐 {cues}")

    print("\n### 하나만 빼기 — 나머지 전부가 있을 때 이 계열이 없으면")
    for name in FAMILIES:
        rest = tuple(m for k, v in FAMILIES.items() if k != name for m in v)
        rows, cues = planned_rows(rest)
        print(f"  {name:4} 빠짐 → 계획 행 {rows:3} (전부 대비 {rows - full:+3}) · 큐 {cues}")


if __name__ == "__main__":
    main()
