"""t222 재현 — 좌표가 전부 0 인 리그에서 오늘 무엇이 초록인가."""

from __future__ import annotations

from pathlib import Path

from server.lxseq.position_derive import (
    derive_position_presets,
    group_members_from_sheets,
    parse_position_sheet,
    position_preset_bundles,
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
    fids = sorted(set(fid for group in members.values() for fid in group))
    coordinates = dict((fid, (0.0, 0.0, 0.0)) for fid in fids)
    result = derive_position_presets(rows, members, coordinates)
    print("좌표 대수:", len(coordinates))
    print("derived :", [item.preset_id for item in result.derived])
    for item in result.derived:
        pans = sorted(set(round(pan, 1) for _fid, pan, _tilt in item.aims))
        tilts = sorted(set(round(tilt, 1) for _fid, _pan, tilt in item.aims))
        print("  ", item.preset_id, "n=" + str(len(item.aims)), "pan", pans, "tilt", tilts)
        print("   label:", item.label)
    print("skipped :", [(item.preset_id, item.reason) for item in result.skipped])
    bundles = position_preset_bundles(result.derived)
    print("bundle 첫 3줄 (--approve 였다면 콘솔에 나갈 명령):")
    for line in (bundles[0][:2] + bundles[0][-2:]) if bundles else []:
        print("   ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
