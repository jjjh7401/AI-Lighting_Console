"""t222 — 퇴화 리그 술어 두 후보를 코퍼스에 대고 잰다.

후보 A: `derive_position_presets` 안에서 x·y·z span 을 직접 계산해 판정.
후보 B: `get_spatial_context` 응답의 `analysis.low_confidence` 를 그대로 신뢰.

두 술어의 경계가 겹치는지가 이 프로브의 질문이다. 콘솔 접촉 0 —
live 리그는 t221 이 저장한 응답 원문을 읽는다.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.spatial.rows import SPATIAL_ROW_NOISE_SPAN, analyze_spatial_rows
from server.spatial.schema import SpatialFixture

EPSILON = 1e-9
RAW = Path(".moai/reports/t221/evidence/spatial_raw.json")


def _live() -> dict:
    payload = json.loads(RAW.read_text(encoding="utf-8"))
    return dict(
        (record["fid"], (record["x"], record["y"], record["z"])) for record in payload["fixtures"]
    )


SYNTHETIC = dict(
    [
        (101, (-2.0, 0.0, 6.0)),
        (102, (0.0, 0.0, 6.0)),
        (103, (2.0, 0.0, 6.0)),
        (201, (-3.0, 8.0, 6.0)),
        (202, (0.0, 8.0, 6.0)),
        (203, (3.0, 8.0, 6.0)),
        (501, (-3.0, 6.0, 7.0)),
        (502, (0.0, 6.0, 7.0)),
        (503, (3.0, 6.0, 7.0)),
        (521, (-3.0, 2.0, 7.0)),
        (522, (0.0, 2.0, 7.0)),
        (523, (3.0, 2.0, 7.0)),
    ]
)

WEAK_GAPS = dict((100 + i, (-4.0 + 2.0 * (i % 5), float(i // 5), 6.0)) for i in range(20))

VERTICAL_ONLY = dict((100 + i, (0.0, 0.0, 4.0 + 0.5 * i)) for i in range(8))

# y 가 등간격이라 최대 갭이 중앙값의 4배를 못 넘는다 -> weak_gap_separation.
# 그런데 x·y 폭은 실값이다 — 조준도 등분도 성립하는 멀쩡한 리그.
EVEN_DEPTH = dict((100 + i, (-4.0 + 2.0 * (i % 3), float(i), 6.0)) for i in range(9))

SINGLE_BAR = dict((100 + i, (-4.0 + i, 0.0, 6.0)) for i in range(9))

SINGLE_FIXTURE = dict([(101, (1.0, 2.0, 6.0))])

TINY_SPREAD = dict((100 + i, (0.01 * i, 0.0, 6.0)) for i in range(6))

CORPUS = dict(
    [
        ("live_86_console", _live()),
        ("synthetic_12", SYNTHETIC),
        ("weak_gaps_20", WEAK_GAPS),
        ("vertical_only_8", VERTICAL_ONLY),
        ("even_depth_9", EVEN_DEPTH),
        ("single_bar_9", SINGLE_BAR),
        ("single_fixture_1", SINGLE_FIXTURE),
        ("tiny_spread_6", TINY_SPREAD),
    ]
)


def _spans(coordinates):
    axes = list(zip(*coordinates.values(), strict=True))
    return tuple(max(axis) - min(axis) for axis in axes)


def main() -> int:
    rows = []
    for name, coordinates in CORPUS.items():
        spans = _spans(coordinates)
        analysis = analyze_spatial_rows(
            tuple(
                SpatialFixture(fid=fid, name=str(fid), x=p[0], y=p[1], z=p[2])
                for fid, p in coordinates.items()
            )
        )
        a_zero = max(spans) <= EPSILON
        a_noise = max(spans) <= 0.05
        # 채택안 C — 수평면(x·y)만 노이즈 폭에 건다. z 는 뺀다:
        # 한 트러스에 매단 멀쩡한 리그가 z span 0 이다.
        c_plane = max(spans[0], spans[1]) <= SPATIAL_ROW_NOISE_SPAN
        b_subset = analysis.confidence_reason in (
            "no_spatial_spread",
            "vertical_spread_only",
        )
        rows.append(
            dict(
                rig=name,
                n=len(coordinates),
                span_x=round(spans[0], 4),
                span_y=round(spans[1], 4),
                span_z=round(spans[2], 4),
                A_span_zero=a_zero,
                A_span_noise=a_noise,
                B_low_confidence=analysis.low_confidence,
                B_reason=analysis.confidence_reason,
                A_zero_vs_B=("agree" if a_zero == analysis.low_confidence else "DISAGREE"),
                A_noise_vs_B=("agree" if a_noise == analysis.low_confidence else "DISAGREE"),
                C_plane_noise=c_plane,
                C_vs_B=("agree" if c_plane == analysis.low_confidence else "DISAGREE"),
                C_vs_B_subset=("agree" if c_plane == b_subset else "DISAGREE"),
            )
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print("")
    head = "rig".ljust(18) + "A0".ljust(7) + "Anoise".ljust(8) + "C".ljust(7)
    head += "B".ljust(7) + "B_reason".ljust(22) + "C~B".ljust(10) + "C~Bsub"
    print(head)
    for row in rows:
        line = str(row["rig"]).ljust(18) + str(row["A_span_zero"]).ljust(7)
        line += str(row["A_span_noise"]).ljust(8) + str(row["C_plane_noise"]).ljust(7)
        line += str(row["B_low_confidence"]).ljust(7)
        line += str(row["B_reason"]).ljust(22) + str(row["C_vs_B"]).ljust(10)
        line += str(row["C_vs_B_subset"])
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
