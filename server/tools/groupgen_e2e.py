"""GROUPGEN M6 종단 라이브 검증 하네스 (AC-GROUPGEN-040 · 046).

This is a DEV TOOL, not a production execution path — the same class as
``busking_e2e``: it needs **no** bridge exemption because it reaches the console
only through the production seam.

**우회 배선을 만들지 않는다**: 콘솔 스택은 조립 루트 `build_console_stack`이
세우고, 툴은 `ChatSession`이 쓰는 것과 같은 `build_toolset`으로 만든다. 여기서
게이트·감사·브리지를 손으로 엮으면 M6이 검증하는 것이 제품 경로가 아니게 된다.

Usage (from the project root, with grandMA3 onPC running the responder)::

    uv run python -m server.tools.groupgen_e2e --stage classify --listen-port 9005

승인은 `--approve`가 있을 때만 자동 승인된다. 없으면 `DenyAllApprovalPort`가
막고, 그때의 관측(콘솔 송신 0건)도 유효한 결과다 — 실제로 AC-GROUPGEN-046의
Gemini 턴 관측이 그 형태였다.

⚠ `sys.path[0]` 함정: 이 모듈을 파일 경로로 실행하면 스크립트 디렉터리가
`sys.path[0]`이 되어 editable 설치가 가리키는 **다른 체크아웃**의 `server`
패키지를 import할 수 있다(이 저장소에서 실측된 함정). 반드시 `-m`으로 실행하라.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.approval import ApprovalRequest
from server.safety.bootstrap import build_console_stack

# The 18 fixtures the container actually LISTS, addressed by their REAL fid.
#
# SLOT != FID on this rig (measured 2026-08-04, the repository's recurring trap):
#   slots  1..20  ->  fids 20..39   Robin LEDBeam 350  (added later, all at origin)
#   slots 21..39  ->  fids  1..19   Robin MMX Spot     (older, carry SPATIAL leftovers)
# The listing is payload-truncated at 18 of 39 children, so the visible set is
# slots 1..18 == fids 20..37. Targeting fids 1..18 instead made arrange_fixtures
# refuse with "no patch slot answered with this fid" and write NOTHING — a
# coordinate write with no backup has no way back (REQ-SPATIAL-020). That
# fail-closed refusal is itself M6 evidence.
#
# Slots 21..39 are NOT listed, so the classifier reports coverage 18/39 and flags
# the judgement partial — that disclosure is the honest outcome, not a bug.
VISIBLE_FIDS = tuple(range(20, 38))


class _RecordingApproval:
    """Approval channel for this session. Records every bundle it clears."""

    def __init__(self, *, approve: bool) -> None:
        self._approve = approve
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        self.asked.append(tuple(request.commands))
        return self._approve


#: Each stage is (label, list of arrange_fixtures calls, expected topology token).
#: The expectation is written down BEFORE the run so a mismatch is a finding,
#: not a post-hoc rationalisation.
#: arrange_fixtures takes FLAT keys (preset/fids/rows/columns/spacing/radius/
#: start_angle/origin/orientation) — required: preset, fids.
STAGES: dict[str, dict] = {
    "rows": {
        "expect": ("depth_rows", "grid"),
        "arrange": [
            {
                "preset": "grid",
                "fids": list(VISIBLE_FIDS),
                "rows": 3,
                "columns": 6,
                "spacing": 2.0,
                "orientation": "xy",
            }
        ],
    },
    "concentric": {
        "expect": ("concentric",),
        "arrange": [
            {
                "preset": "circle",
                "fids": list(VISIBLE_FIDS[:6]),
                "radius": 2.0,
                "orientation": "xy",
            },
            {
                "preset": "circle",
                "fids": list(VISIBLE_FIDS[6:]),
                "radius": 6.0,
                "orientation": "xy",
            },
        ],
    },
    "lateral": {
        # A PURE lateral split: y and z constant, x in two clusters. The first
        # attempt used two 3x3 grids, which also made the DEPTH axis significant
        # (3 distinct y values) -> both axes confident -> contention -> "grid".
        # That was a flaw in the test arrangement, not in the classifier, so the
        # arrangement was fixed rather than the expectation relaxed.
        "expect": ("lateral_split",),
        "arrange": [
            {
                "preset": "row",
                "fids": list(VISIBLE_FIDS[:9]),
                "spacing": 1.0,
                "orientation": "x",
                "origin": [-7.0, 0.0, 0.0],
            },
            {
                "preset": "row",
                "fids": list(VISIBLE_FIDS[9:]),
                "spacing": 1.0,
                "orientation": "x",
                "origin": [7.0, 0.0, 0.0],
            },
        ],
    },
}


def _payload(execution) -> dict:
    try:
        return json.loads(execution.result.content)
    except (json.JSONDecodeError, TypeError):
        return {"raw": execution.result.content}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=[*STAGES, "classify"], default="classify")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--listen-port", type=int, default=9005)
    parser.add_argument(
        "--approve",
        action="store_true",
        help="clear the approval gate; WITHOUT this nothing reaches the console",
    )
    parser.add_argument(
        "--write-groups",
        action="store_true",
        help="also call create_arrangement_groups with the suggested buckets",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    approval = _RecordingApproval(approve=args.approve)
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_port=args.listen_port,
        approval_port=approval,
    )
    out: dict = {"stage": args.stage, "approve": args.approve}
    try:
        registry = build_toolset(
            execution_port=stack.gate.execution_port,
            state_port=stack.gate.state_port,
            bundle_gate=stack.gate,
            group_approval_port=approval,
        )

        # -- 1) arrange (only for a named stage; `classify` reads only) --------
        if args.stage != "classify":
            out["arrange"] = []
            for index, call_args in enumerate(STAGES[args.stage]["arrange"]):
                ex = registry.dispatch(
                    ToolCall(id=f"m6-arr-{index}", name="arrange_fixtures", arguments=call_args)
                )
                p = _payload(ex)
                out["arrange"].append(
                    {
                        "preset": call_args["preset"],
                        "fids": call_args["fids"],
                        "is_error": ex.result.is_error,
                        "status": p.get("status"),
                        "truncated": p.get("truncated"),
                        "written": p.get("written") or p.get("placements"),
                        "detail": p if ex.result.is_error else None,
                    }
                )
                if ex.result.is_error:
                    out["arrange_failed_at"] = index
                    break

        # -- 2) classify — the read/propose half -----------------------------
        ex = registry.dispatch(
            ToolCall(id="m6-classify", name="classify_arrangement_topology", arguments={})
        )
        c = _payload(ex)
        out["classify"] = {
            "is_error": ex.result.is_error,
            "coverage": c.get("coverage"),
            "truncated": c.get("truncated"),
            "roundtrip_capped": c.get("roundtrip_capped"),
            "topology_partial": c.get("topology_partial"),
            "selected_kind": (c.get("topology") or {}).get("selected", {}).get("kind"),
            "selected_buckets": (c.get("topology") or {}).get("selected", {}).get("fids_by_bucket"),
            "grid_axes": (c.get("topology") or {}).get("selected", {}).get("grid_axes"),
            "candidates": [
                {"kind": cand.get("kind"), "low_confidence": cand.get("low_confidence")}
                for cand in (c.get("topology") or {}).get("candidates", [])
            ],
            "suggested_groups": c.get("suggested_groups"),
            "error": c if ex.result.is_error else None,
        }
        if args.stage != "classify":
            expected = STAGES[args.stage]["expect"]
            actual = out["classify"]["selected_kind"]
            out["classify"]["expected_kind"] = list(expected)
            out["classify"]["expectation_met"] = actual in expected

        # -- 3) write the groups (approval-gated) ----------------------------
        if args.write_groups and not out["classify"]["is_error"]:
            groups = [g for g in (out["classify"]["suggested_groups"] or []) if g.get("fids")]
            if groups:
                ex = registry.dispatch(
                    ToolCall(
                        id="m6-create",
                        name="create_arrangement_groups",
                        arguments={"groups": groups},
                    )
                )
                w = _payload(ex)
                out["create"] = {
                    "is_error": ex.result.is_error,
                    "status": w.get("status"),
                    "executed": w.get("executed"),
                    "unverified": w.get("unverified"),
                    "fixture_list_truncated": w.get("fixture_list_truncated"),
                    "verified_steps": w.get("verified_steps"),
                    "human_check_commands": w.get("human_check_commands"),
                    "plan": w.get("plan"),
                    "commands": w.get("commands"),
                }
            else:
                out["create"] = {"skipped": "classify proposed no groups with fids"}

        out["approval_bundles_asked"] = len(approval.asked)
    finally:
        stack.stop()

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
