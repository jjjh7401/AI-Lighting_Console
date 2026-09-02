"""t222 — `unaimable` 이 두 사유로 갈리는지 실측. 콘솔 접촉 0."""

from __future__ import annotations

from pathlib import Path

from server.lxseq.position_derive import (
    derive_position_presets,
    group_members_from_sheets,
    parse_position_sheet,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")


def _text(name: str) -> str:
    return (RIG / name).read_text(encoding="utf-8-sig")


def main() -> int:
    rows = parse_position_sheet(_text("LXSEQ_RIG_01_ShowBase_r3.preset-pos.csv"))
    members = group_members_from_sheets(
        _text("LXSEQ_RIG_01_ShowBase_r3.patch.csv"),
        _text("LXSEQ_RIG_01_ShowBase_r3.group.csv"),
    )
    all_fids = sorted(set(fid for group in members.values() for fid in group))
    # 수평 폭은 실값 — 퇴화 가드를 통과시킨 뒤 조준 실패만 남긴다.
    # cy 가 0 이 되도록 y 를 대칭으로 깐다.
    coordinates = dict()
    for index, fid in enumerate(all_fids):
        coordinates[fid] = (-8.0 + 0.2 * index, 0.0, 6.0)
    # MOVER-U 는 목표점(x, cy, 0.0)과 같은 자리에 둔다 -> 거리 0.
    cy = 0.0  # y 를 전부 0 으로 깔았으니 기준틀 cy 도 0 이다.
    for fid in members["MOVER-U"]:
        coordinates[fid] = (coordinates[fid][0], cy, 0.0)
    # BACK 은 목표점(x, cy, 1.6) 바로 아래 -> 순수 상방, tilt 180.
    for fid in members["BACK"]:
        coordinates[fid] = (coordinates[fid][0], cy, 0.0)

    result = derive_position_presets(rows, members, coordinates)
    print("derived:", [item.preset_id for item in result.derived])
    for item in result.skipped:
        print(item.preset_id, "|", item.reason)
        print("   ", item.detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
