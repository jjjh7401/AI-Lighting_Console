"""M3-b 실기 되읽기 검증 실행기 — 쓰기 0건, `query_state` 4회 이하.

SPEC-COPILOT-MUSICSYNC-001 REQ-021·022·024·025 · AC-024·025·030.

운영자가 콘솔에서 녹화 무장 명령(인계 목록의 그 한 줄)을 직접 실행하고 녹화를
마친 **뒤에** 부른다 — 이 파일은 그 명령 문자열을 담지 않는다(AC-MUSICSYNC-022).
이 도구는 `server.orchestrator.songcue_timecode.verify_songcue_timecode` 를 실기
상태 포트에 물려 돌리고, 5절 형식 산출물을 `--note` 에 쓴다. 판정 어휘에
`verified` 는 없다 — 갈래 B(M3-a: 재생 효과 미관측)에서 이벤트 내용 축은
`SongCueTimingSkip` 으로 좁혀진 채 보고된다.

쓰기는 한 줄도 없다. 게이트의 실행 포트는 만지지 않고 상태 포트만 쓴다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from server.orchestrator.songcue_timecode import (
    render_timecode_verification_report,
    verify_songcue_timecode,
)
from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_listen_port_argument(parser)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="grandMA3 onPC OSC 입력 포트")
    parser.add_argument("--slot", type=int, required=True, help="되읽을 타임코드 슬롯 번호")
    parser.add_argument("--expected-name", required=True, help="준비 단계에서 붙인 이름")
    parser.add_argument(
        "--expected-sequence", required=True, help="TrackGroup 아래 Track 이름(시퀀스 이름)"
    )
    parser.add_argument(
        "--baseline-pool-count",
        type=int,
        default=None,
        help="준비 전 풀 childCount (없으면 증가 판정을 안 한다)",
    )
    parser.add_argument("--out", required=True, help="검증 결과 JSON 경로")
    parser.add_argument("--note", required=True, help="5절 산출물(markdown) 경로")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_host="127.0.0.1",
        receive_port=args.listen_port,
        approval_port=None,  # 승인 통로 없음 — 이 도구는 아무 명령도 심사받지 않는다
        audit_dir=Path(".moai/state/verify/musicsync-m3b"),
        timeouts=LinkTimeouts(state_query_seconds=6.0),
        attempt_session_backup=False,
    )
    try:
        health = preflight(
            stack.gate,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            console_port=args.port,
        )
        if health.get("verdict") != "responder_ok":
            print(json.dumps({"preflight": health}, ensure_ascii=False, indent=2))
            return 2
        verification = verify_songcue_timecode(
            stack.gate.state_port,
            args.slot,
            args.expected_name,
            args.expected_sequence,
            baseline_pool_child_count=args.baseline_pool_count,
            event_content_probe_note=None,  # 갈래 B — M3-a 는 이벤트 내용을 열지 않았다
        )
    finally:
        stack.stop()

    ran_at = datetime.now(UTC).isoformat(timespec="seconds")
    baseline = (
        f"실기 콘솔 {args.host}:{args.port} · 회신 {args.listen_port} · {ran_at} · "
        f"슬롯 {args.slot} · 조회 {verification.query_count}/4"
    )
    report = render_timecode_verification_report(
        verification,
        baseline=baseline,
        residual_risks=(
            "이벤트 내용은 갈래 B 라 읽지 않았다 — "
            "녹화된 이벤트가 계획과 일치한다는 주장은 하지 않는다",
            "빈 타임코드 풀에서는 앱이 첫 타임코드를 못 만든다(t270) — "
            "이 회차는 풀이 비어 있지 않았다",
        ),
    )
    out = {
        "ran_at": ran_at,
        "slot": args.slot,
        "preflight": health,
        "verification": asdict(verification),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    Path(args.note).parent.mkdir(parents=True, exist_ok=True)
    Path(args.note).write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": verification.verdict,
                "queries": verification.query_count,
                "reason": verification.reason,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
