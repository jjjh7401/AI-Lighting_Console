"""t226 — 퇴화 방향 확인. 정본 CSV + 콘솔이 실제로 답한 86 대 FID 로,
좌표만 t221 이 실측한 상태(전부 0.0)로 되돌려 전 행이 거절되는지 잰다.

콘솔 접촉 0 — 라이브 좌표 개수는 직전 프리뷰 산출물에서 읽는다.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.lxseq.position_derive import (
    derive_position_presets,
    group_members_from_sheets,
    parse_position_sheet,
    rig_is_degenerate,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3"
LIVE = Path(".moai/reports/t226/evidence/live_preview.json")


def main() -> None:
    rows = parse_position_sheet((RIG / (STEM + ".preset-pos.csv")).read_text("utf-8-sig"))
    members = group_members_from_sheets(
        (RIG / (STEM + ".patch.csv")).read_text("utf-8-sig"),
        (RIG / (STEM + ".group.csv")).read_text("utf-8-sig"),
    )
    fids = sorted(set(fid for group in members.values() for fid in group))
    origin = dict((fid, (0.0, 0.0, 0.0)) for fid in fids)

    live = json.loads(LIVE.read_text("utf-8"))
    report = dict(
        fid_count=len(fids),
        live_coordinate_count=live["coordinates_read"]["count"],
        rig_is_degenerate=rig_is_degenerate(origin),
    )
    result = derive_position_presets(rows, members, origin)
    report["derived_count"] = len(result.derived)
    report["skipped_count"] = len(result.skipped)
    report["reasons"] = sorted(set(item.reason for item in result.skipped))
    report["skipped_ids"] = sorted(item.preset_id for item in result.skipped)
    report["first_detail"] = result.skipped[0].detail if result.skipped else None
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
