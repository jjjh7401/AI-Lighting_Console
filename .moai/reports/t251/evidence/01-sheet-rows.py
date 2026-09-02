"""t251 — 시트 행이 콘솔에 도달하는지 파서로 전수한다. 콘솔 접촉 0.

실행: PYTHONPATH=. .venv/bin/python <this>
"""

from pathlib import Path

from server.lxseq.cue_parser import parse_cue_csv
from server.lxseq.preset_parser import parse_preset_csv

RIG = Path("src/Lighting_Designer/02_RIG팩")
SONG = Path("src/Lighting_Designer/03_곡파일_Sugar")
BASE = "LXSEQ_RIG_01_ShowBase_r3"


def show_preset(kind_file: str) -> None:
    path = RIG / f"{BASE}.{kind_file}.csv"
    text = path.read_text(encoding="utf-8-sig")
    try:
        result = parse_preset_csv(text)
    except Exception as error:  # noqa: BLE001 — 판별기가 거절하는 것도 관측이다
        print(f"\n### {kind_file}: 파서 거절 — {type(error).__name__}: {error}")
        return
    print(f"\n### {kind_file}  (sheet_kind={result.sheet_kind})")
    print(f"  레코드 {len(result.records)} · 거절행 {len(result.rejected)}")
    storable = 0
    for rec in result.records:
        if rec.storable:
            storable += 1
        mark = "저장가능" if rec.storable else "보류    "
        why = " · ".join(sorted(set(rec.hold_classes)))
        print(f"    [{mark}] {rec.preset_id:8} {rec.name[:20]:22} {why}")
    print(f"  => 저장가능 {storable} / {len(result.records)}")


def main() -> None:
    for kind in ("preset-dim", "preset-col", "preset-bm", "preset-pos"):
        show_preset(kind)

    fx = (RIG / f"{BASE}.fx.csv").read_text(encoding="utf-8-sig")
    print("\n### fx  (레지스트리 행 없음)")
    print("  헤더:", fx.splitlines()[0])
    print("  데이터행:", sum(1 for line in fx.splitlines()[1:] if line.strip()))

    text = (SONG / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv").read_text(encoding="utf-8-sig")
    cues = parse_cue_csv(text)
    print("\n### cue-ex")
    print(
        f"  레코드 {len(cues.records)} · 거절 {len(cues.rejections)} · 큐 {len(cues.cue_numbers)}"
    )
    for rej in cues.rejections[:5]:
        print(f"    [거절] {rej}")


if __name__ == "__main__":
    main()
