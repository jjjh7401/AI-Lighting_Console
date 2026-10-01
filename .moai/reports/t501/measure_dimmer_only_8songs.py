"""카드 t501 — 배차서 Part C 항목 2 — "디머만으로 몇 버킷인가"를 색 포함 전체
상태(`ldrender_gate.layer_diversity`, AC-001 이 실제로 쓰는 집계)와 나란히
잰다. 리드의 예상 한 줄("층 대비는 색, 밝기 대비 0 — R5 이월")을 이 결과가
뒷받침하는지 확인하는 용도 — `measure_ac001_8songs.py`(M3 재사용) 가 만드는
``gate_cues`` 를 그대로 받아 디머만 키로 다시 세는 변형 집계 하나를 덧붙인다
(DSP 재실행 없음, 그 스크립트의 §방법론과 동일 전제).

실행: uv run python .moai/reports/t501/measure_dimmer_only_8songs.py
"""

from __future__ import annotations

import json
from pathlib import Path

import measure_ac001_8songs as m  # noqa: E402

HERE = Path(__file__).resolve().parent


def _dimmer_only_bucket_count(role_view) -> int:
    """`ldrender_gate.layer_diversity`의 디머-전용 변형 — 상태 전체(dim·rgb·
    pos)가 아니라 **디머 값만**으로 LIT 버킷을 센다. 같은 디머 값을 받은
    역할은 색이 달라도 한 버킷으로 합친다(이 함수만의 집계 — AC-001 의 실제
    판정은 여전히 `layer_diversity`, 이 함수는 "디머만으로는 몇 개인가"를
    별도로 보여주는 진단용이다)."""
    lit_dims: set[float] = set()
    for states in role_view.values():
        for state in states:
            dim = state.get("dim")
            if dim is None:
                continue
            try:
                if float(dim) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            lit_dims.add(float(dim))
    return len(lit_dims)


def main() -> None:
    analysis_files = sorted((m.T499 / "runs").glob("*/analysis.json"))
    analysis_files = [p for p in analysis_files if p.parent.name != "Rain_first"]
    assert len(analysis_files) == 8, [p.parent.name for p in analysis_files]

    summary = []
    for analysis_path in analysis_files:
        song_name = analysis_path.parent.name
        result = m.rehearse(song_name, analysis_path)
        gate_cues = m._gate_cues_from_commands(result["commands"], result["bundle_cues"])

        rows = []
        for cue in gate_cues:
            if cue.kind == m.BLACKOUT_KIND or cue.kind == m.MIB_PREMOVE_KIND:
                continue
            from server.design.ldrender_gate import layer_diversity

            full = layer_diversity(cue.role_view)
            dimmer_only = _dimmer_only_bucket_count(cue.role_view)
            rows.append(
                {"cue_no": cue.cue_no, "full_lit_buckets": full, "dimmer_only_buckets": dimmer_only}
            )

        min_full = min(r["full_lit_buckets"] for r in rows) if rows else None
        max_dimmer_only = max(r["dimmer_only_buckets"] for r in rows) if rows else None
        n_cues_dimmer_only_ge_3 = sum(1 for r in rows if r["dimmer_only_buckets"] >= 3)
        row = {
            "song": song_name,
            "n_section_cues": len(rows),
            "min_full_lit_buckets": min_full,
            "max_dimmer_only_buckets": max_dimmer_only,
            "n_cues_dimmer_only_ge_3": n_cues_dimmer_only_ge_3,
            "cues": rows,
        }
        summary.append(row)
        print(
            f"{song_name}: 구간/큐 {len(rows)}개 · 전체상태(색+디머) 최소버킷 {min_full} · "
            f"디머전용 최대버킷 {max_dimmer_only} · 디머전용>=3 인 큐 {n_cues_dimmer_only_ge_3}개"
        )

    (HERE / "dimmer_only_8songs.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), "utf-8"
    )


if __name__ == "__main__":
    main()
