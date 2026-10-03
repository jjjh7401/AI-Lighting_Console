"""카드 t501 M6 — 배차서 측정 6(8곡): fx.requested/permitted/송신 줄 수, AC-001/
AC-004 불변 재확인. `measure_ac001_8songs.py`(M3/M4/M5 재사용)의 리허설
인프라를 그대로 쓴다 — DSP 재실행 없음, 콘솔 접촉 0건.

측정:
  - 곡마다: fx.requested 합·fx.permitted 합·송신(recall) 줄 수
    (``song_cue_render._fx_report_counts`` 재사용 — REQ-010 게이트와 바이트
    단위로 맞춘 그 함수를 그대로 써서, 이 스크립트가 독자적인 "sent" 셈을
    따로 만들지 않는다).
  - AC-001(LIT>=3)·색 수 재확인 — M5 측정과 바이트 동일해야 한다(M6 는
    `_phaser_cue_value_lines`/`_fx_axes` 축만 건드렸지 디머·색 렌더링은
    건드리지 않았으므로).

실행: uv run python .moai/reports/t501/measure_m6_8songs.py
"""

from __future__ import annotations

import json
from pathlib import Path

import measure_ac001_8songs as m  # noqa: E402

from server.design.ldrender_gate import evaluate
from server.design.song_cue_render import _fx_report_counts

HERE = Path(__file__).resolve().parent


def main() -> None:
    analysis_files = sorted((m.T499 / "runs").glob("*/analysis.json"))
    analysis_files = [p for p in analysis_files if p.parent.name != "Rain_first"]
    assert len(analysis_files) == 8, [p.parent.name for p in analysis_files]

    summary = []
    for analysis_path in analysis_files:
        song_name = analysis_path.parent.name
        result = m.rehearse(song_name, analysis_path)
        commands = result["commands"]
        bundle_cues = result["bundle_cues"]

        class _Bundle:
            cues = bundle_cues

        # 이 리허설 하네스가 실제로 콘솔에서 받는 phaser_slots 는 M1 progress.md
        # 가 이미 적어 둔 대로 production 호출부(session.py `_phaser_slots_for_
        # bundle`)를 통째로 거치지 않는다 — 여기서는 송신 명령열 자체에서
        # "At Preset" 줄 수를 세어 "sent" 를 교차검증한다(phaser_slots 딕셔너리
        # 재구성 없이 명령열만으로 재확인 가능한 하한).
        recall_lines = [c for c in commands if " At Preset " in c and "Fixture" in c]

        requested, permitted, sent_by_gate = _fx_report_counts(_Bundle(), {})

        gate_cues = m._gate_cues_from_commands(commands, result["bundle_cues"])
        gate_result = evaluate(gate_cues, sent_lines=commands)
        under3 = [(no, n) for no, n in gate_result.cue_lit_layers if n < 3]

        summary.append(
            {
                "song": song_name,
                "fx_requested": requested,
                "fx_permitted": permitted,
                "fx_sent_by_gate_count": sent_by_gate,
                "recall_lines_in_commands": len(recall_lines),
                "n_section_cues": len(gate_result.cue_lit_layers),
                "n_cues_lit_ge_3": len(gate_result.cue_lit_layers) - len(under3),
                "color_count": gate_result.color_count,
            }
        )
        print(
            f"{song_name}: fx 요청 {requested} · 허용 {permitted} · "
            f"게이트상 송신 {sent_by_gate} · 실제 At Preset 줄 {len(recall_lines)} · "
            f"LIT>=3 {summary[-1]['n_cues_lit_ge_3']}/{summary[-1]['n_section_cues']} · "
            f"색 {summary[-1]['color_count']}종"
        )

    (HERE / "measure_m6_8songs_fx.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), "utf-8"
    )

    total_requested = sum(row["fx_requested"] for row in summary)
    total_permitted = sum(row["fx_permitted"] for row in summary)
    total_sent = sum(row["fx_sent_by_gate_count"] for row in summary)
    total_recall_lines = sum(row["recall_lines_in_commands"] for row in summary)
    total_lit_ge_3 = sum(row["n_cues_lit_ge_3"] for row in summary)
    total_section_cues = sum(row["n_section_cues"] for row in summary)
    print(
        f"\n합계: fx 요청 {total_requested} · 허용 {total_permitted} · "
        f"게이트상 송신 {total_sent} · 실제 At Preset 줄 {total_recall_lines} · "
        f"AC-001 LIT>=3 {total_lit_ge_3}/{total_section_cues}"
    )


if __name__ == "__main__":
    main()
