"""t221 — POS 불가 3행의 기하를 숫자로 연다. 읽기 전용, 콘솔 쓰기 0."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from server.llm.types import ToolCall  # noqa: E402
from server.lxseq.position_derive import (  # noqa: E402
    _RULE_BY_ID,
    _resolve_group,
    _stage_frame,
    group_members_from_sheets,
    parse_position_sheet,
)
from server.orchestrator.tools import build_toolset  # noqa: E402
from server.safety.approval import ApprovalRequest  # noqa: E402
from server.safety.bootstrap import build_console_stack  # noqa: E402
from server.spatial.pointing import POINTING_TILT_LIMIT_DEGREES, fan_chain  # noqa: E402

RIG = Path("src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3")


class _Deny:
    def request_approval(self, request: ApprovalRequest) -> bool:
        return False


class _Q:
    def ask(self, request) -> str:
        return ""


def raw_tilt(position, target):
    vx = target[0] - position[0]
    vy = target[1] - position[1]
    vz = target[2] - position[2]
    length = math.sqrt(vx * vx + vy * vy + vz * vz)
    if length < 1e-9:
        return None, None, 0.0
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, -vz / length))))
    pan = 0.0 if (vx == 0.0 and vy == 0.0) else math.degrees(math.atan2(-vx, vy))
    return pan, tilt, length


def main() -> int:
    pos_path = RIG.parent / (RIG.name + ".preset-pos.csv")
    rows = parse_position_sheet(pos_path.read_text("utf-8-sig"))
    members = group_members_from_sheets(
        (RIG.parent / (RIG.name + ".patch.csv")).read_text("utf-8-sig"),
        (RIG.parent / (RIG.name + ".group.csv")).read_text("utf-8-sig"),
    )
    stack = build_console_stack(
        send_host="127.0.0.1", send_port=8000, receive_port=9005, approval_port=_Deny()
    )
    try:
        registry = build_toolset(
            execution_port=stack.gate.execution_port,
            state_port=stack.gate.state_port,
            property_port=stack.gate.state_port,
            bundle_gate=stack.gate,
            question_port=_Q(),
            group_approval_port=_Deny(),
        )
        execution = registry.dispatch(
            ToolCall(id="t221-coords", name="get_spatial_context", arguments=dict())
        )
        payload = json.loads(execution.result.content)
    finally:
        stack.stop()

    records = payload.get("fixtures") or payload.get("partial_fixtures") or []
    coordinates = {}
    for record in records:
        try:
            coordinates[int(record["fid"])] = (
                float(record["x"]),
                float(record["y"]),
                float(record["z"]),
            )
        except (KeyError, TypeError, ValueError):
            continue

    frame = _stage_frame(coordinates)
    out = dict(
        coordinate_count=len(coordinates),
        coordinates={str(k): list(v) for k, v in sorted(coordinates.items())},
        frame=dict(
            cx=frame.cx,
            cy=frame.cy,
            min_x=frame.min_x,
            max_x=frame.max_x,
            vocal_point=list(frame.vocal_point),
        ),
        rig_extent=dict(
            x=[min(p[0] for p in coordinates.values()), max(p[0] for p in coordinates.values())],
            y=[min(p[1] for p in coordinates.values()), max(p[1] for p in coordinates.values())],
            z=[min(p[2] for p in coordinates.values()), max(p[2] for p in coordinates.values())],
        ),
        tilt_limit=POINTING_TILT_LIMIT_DEGREES,
        rows=[],
    )

    for row in rows:
        rule = _RULE_BY_ID.get(row.preset_id)
        if rule is None:
            continue
        fids = _resolve_group(row.target_group, members) or ()
        placed = [(fid, coordinates[fid]) for fid in fids if fid in coordinates]
        entry = dict(
            preset_id=row.preset_id,
            group=row.target_group,
            kind=rule.kind,
            member_count=len(fids),
            placed_count=len(placed),
            fixtures=[],
        )
        span = frame.max_x - frame.min_x
        count = len(placed)
        ordered = list(placed)
        if rule.kind == "spread_floor" and placed:
            chain = fan_chain(list(placed))
            by_fid = dict(placed)
            ordered = [(fid, by_fid[fid]) for fid in chain]
        for index, (fid, position) in enumerate(ordered):
            if rule.kind == "silhouette_line":
                target = (position[0], frame.cy, 1.6)
            elif rule.kind == "floor_inside":
                target = (position[0], frame.cy, 0.0)
            elif rule.kind == "spread_floor":
                target = (
                    frame.cx if count == 1 else frame.min_x + index * span / (count - 1),
                    frame.cy,
                    0.0,
                )
            elif rule.kind == "focus_vocal":
                target = frame.vocal_point
            else:
                target = None
            if target is None:
                continue
            pan, tilt, length = raw_tilt(position, target)
            entry["fixtures"].append(
                dict(
                    fid=fid,
                    position=list(position),
                    target=list(target),
                    pan=None if pan is None else round(pan, 2),
                    tilt=None if tilt is None else round(tilt, 2),
                    distance=round(length, 3),
                    over_by=None if tilt is None else round(tilt - POINTING_TILT_LIMIT_DEGREES, 2),
                    degenerate=length < 1e-9,
                )
            )
        out["rows"].append(entry)

    Path(".moai/reports/t221/evidence/reach.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("coords", len(coordinates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
