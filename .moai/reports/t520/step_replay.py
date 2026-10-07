# ruff: noqa: E501 — 한국어 머리말
"""t520 대화형 다시 보기 — 쓰기 없음, 한 번 실행에 한 줄(`Goto Cue 1 Sequence N` 또는 `Off Sequence N`).

감독(원문, 리드 경유): 「순서대로 하면서 켜져있을 때 하나씩 물어봐」. 대상 257 → 258 → 259 → 263 → 265(⑤ 264 는 뺀다).
한 단계씩: on N 실행 → 리드에게 「지금 N 켜짐」 → 리드 「다음」 → off N → 다음 on. 매 실행마다 N 의 이름을 사전 판독한다.

  --action all : 10줄 전부(리허설·전부-거절용, 순서 on257 off257 on258 … off265)
  --action on|off --seq N : 그 한 줄만(전부-거절 폴더의 문면으로 승인)
실행: uv run python .moai/reports/t520/step_replay.py <출력폴더> --action <all|on|off> [--seq N] [--rehearse | --approve <전부-거절 폴더>]
"""

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import argparse  # noqa: E402

#: --target f(기본) = 프로브 F 257·258·259·263·265 · --target s = 프로브 S 266·267·268
TARGET = "s" if "--target" in sys.argv and sys.argv[sys.argv.index("--target") + 1] == "s" else "f"
if "--target" in sys.argv:
    i = sys.argv.index("--target")
    del sys.argv[i : i + 2]
if TARGET == "s":
    import spiider_probe  # noqa: E402,F401 — PROBES(이름) 를 group_probe2 에 넣는다
else:
    import fixture_probe  # noqa: E402,F401
import group_probe2 as g  # noqa: E402
import tc_probe  # noqa: E402

from server.safety.gate import BatchRisk  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 대화형 다시 보기 — 재생만(쓰기 없음)", kind="t520_step_replay"
)
ORDER = [266, 267, 268] if TARGET == "s" else [257, 258, 259, 263, 265]
g.PROBES = [p for p in g.PROBES if p[0] in ORDER]


def all_bundles() -> list[tuple[str, list[str], float]]:
    out = []
    for seq in ORDER:
        out.append((f"on_{seq}", [f"Goto Cue 1 Sequence {seq}"], 0.0))
        out.append((f"off_{seq}", [f"Off Sequence {seq}"], 0.0))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("out")
    parser.add_argument("--action", choices=("all", "on", "off"), required=True)
    parser.add_argument("--seq", type=int, choices=ORDER)
    args, rest = parser.parse_known_args()
    if args.action == "all":
        phase = "store"  # 사전 판독을 빈 번호 대신 이름으로 해야 하므로 아래에서 갈아끼운다
        g.bundles = lambda _phase: all_bundles()
    else:
        if args.seq is None:
            raise SystemExit("--seq 가 필요하다")
        label = f"{args.action}_{args.seq}"
        g.bundles = lambda _phase: [b for b in all_bundles() if b[0] == label]
        phase = f"p{args.seq}"
    if args.action == "all":
        # 이름 사전 판독: 첫 시퀀스(257)로 대신한다 — 단계 실행은 매번 자기 N 을 읽는다
        phase = f"p{ORDER[0]}"
    sys.argv = [sys.argv[0], args.out, "--phase", phase, *rest]
    return g.main()


if __name__ == "__main__":
    sys.exit(main())
