"""t256 — 바뀐 것이 「거부 여부」가 아니라 「사유」임을 보인다. 콘솔 접촉 0."""

from dataclasses import dataclass

from server.lxseq.cue_mapper import DIM_REFERENCE_SHAPE, map_cues


@dataclass(frozen=True)
class Row:
    cue_no: str
    group: str
    dim_raw: str = ""
    col_raw: str = ""
    pos_raw: str = ""
    bm_raw: str = ""
    fx_raw: str = ""
    fx_rate_raw: str = ""
    fx_phase_raw: str = ""
    fx_width_raw: str = ""
    i_fade_raw: str = ""
    i_delay_raw: str = ""
    p_fade_raw: str = ""
    c_fade_raw: str = ""
    b_fade_raw: str = ""
    snap_raw: str = ""
    note: str = ""
    is_video_call: bool = False


def run(label: str, **cells) -> None:
    record = Row(cue_no="Q010", group="BACK", **cells)
    result = map_cues(
        [record],
        declared_cues=("Q010",),
        sequence_name="Sugar",
        sequence_section=dict(objects=[], truncated=False),
        group_slots={"BACK": 1},
        preset_slots={"COL.01": 1},
    )
    if result.held:
        held = result.held[0]
        print(f"  {label:26} 보류 · classes={list(held.hold_classes)}")
        for detail in held.details:
            print(f"      {detail}")
    else:
        row = result.planned[0].rows[0]
        print(f"  {label:26} 계획됨 · dim={row.dim}")


def main() -> None:
    print("### 같은 입력에 대해 — 거부 여부는 그대로, 사유만 갈렸다")
    run("Dim='DIM.01'", dim_raw="DIM.01")
    run("Dim='COL.01'", dim_raw="COL.01")
    run("Dim='확인필요'", dim_raw="확인필요")
    run("Dim='55'", dim_raw="55")
    run("Dim='12.5'", dim_raw="12.5")
    run("P-Fade='COL.01'", dim_raw="55", p_fade_raw="COL.01")

    print("\n### 판별자 자체")
    for value in ("DIM.01", "DIM.FULL", "COL.01", "12.5", "0.0", "55", "확인필요"):
        matched = DIM_REFERENCE_SHAPE.match(value) is not None
        print(f"  {value!r:12} 참조꼴={matched}")


if __name__ == "__main__":
    main()
