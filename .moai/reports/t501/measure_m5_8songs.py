"""카드 t501 M5 — 배차서 측정 a~c. `measure_ac001_8songs.py`(M3/M4 재사용)가
만드는 리허설 인프라를 그대로 쓴다 — DSP 재실행 없음, 콘솔 접촉 0건.

측정:
  a. 곡마다: 비액센트 큐 중 effect 그룹(BLIND 14/STROBE 15/HAZE 16)의 최종
     디머가 0 보다 큰 큐 수(목표 0), 그룹별로.
  b. 곡마다: 액센트 큐 각각 — effect 그룹 값이 직전 큐 → 이 큐로 상승하는가.
  c. AC-001(기대: 변화 없음, M5 가 공유 fids 를 안 건드렸으므로 디머 렌더링
     자체는 불변)과 AC-004 숫자 — 변화가 있으면 보고.

실행: uv run python .moai/reports/t501/measure_m5_8songs.py
"""

from __future__ import annotations

import json
from pathlib import Path

import measure_ac001_8songs as m  # noqa: E402

from server.design.ldrender_gate import evaluate

HERE = Path(__file__).resolve().parent

_EFFECT_GROUPS = {14: "BLIND", 15: "STROBE", 16: "HAZE"}


def _effect_states_per_cue(commands: list[str]) -> list[dict]:
    """송신 명령 → 큐마다 effect 그룹(14/15/16) 각각의 최종 디머 상태(트래킹
    반영, readout.py apply() 와 같은 last-wins 순서 적용)."""
    cues = m._readout.parse_sent(commands)
    state: dict[int, dict] = {}
    rows = []
    for cue in cues:
        m._readout.apply(cue["lines"], state)
        group_dims = {}
        for group_no, name in _EFFECT_GROUPS.items():
            fids = m._readout.members(group_no)
            dims = {state.get(f, {}).get("dim") for f in fids}
            # 그룹 구성원 전체가 같은 값이어야 "그 그룹의 디머"로 읽을 수 있다
            # (이 송신기는 그룹 주소 한 줄로 전부 같은 값을 준다 — 갈리면 결함).
            assert len(dims) == 1, (cue["no"], name, dims)
            group_dims[name] = next(iter(dims))
        rows.append({"cue_no": cue["no"], "cue_name": cue["name"], **group_dims})
    return rows


def main() -> None:
    analysis_files = sorted((m.T499 / "runs").glob("*/analysis.json"))
    analysis_files = [p for p in analysis_files if p.parent.name != "Rain_first"]
    assert len(analysis_files) == 8, [p.parent.name for p in analysis_files]

    summary_a = []
    summary_b = []
    summary_c = []
    for analysis_path in analysis_files:
        song_name = analysis_path.parent.name
        result = m.rehearse(song_name, analysis_path)
        commands = result["commands"]
        bundle_cues = {c.cue_number: c for c in result["bundle_cues"]}
        effect_rows = _effect_states_per_cue(commands)

        # --- 측정 a: 비액센트 큐 중 effect 그룹 디머 > 0 인 큐 수 ---
        non_accent_violations = {name: 0 for name in _EFFECT_GROUPS.values()}
        non_accent_cue_count = 0
        for row in effect_rows:
            try:
                cue_no_float = float(row["cue_no"])
            except ValueError:
                continue
            composed = bundle_cues.get(cue_no_float)
            is_accent_cue = composed is not None and composed.accent_fixture is not None
            if is_accent_cue:
                continue
            non_accent_cue_count += 1
            for name in _EFFECT_GROUPS.values():
                val = row[name]
                if val is not None and val > 0:
                    non_accent_violations[name] += 1
        summary_a.append(
            {
                "song": song_name,
                "n_non_accent_cues": non_accent_cue_count,
                "violations_per_group": non_accent_violations,
            }
        )

        # --- 측정 b: 액센트 큐 — effect 그룹 값 직전 큐 -> 이 큐 (상승 확인) ---
        accent_rows = []
        prev_dims = {name: None for name in _EFFECT_GROUPS.values()}
        for row in effect_rows:
            try:
                cue_no_float = float(row["cue_no"])
            except ValueError:
                prev_dims = {name: row[name] for name in _EFFECT_GROUPS.values()}
                continue
            composed = bundle_cues.get(cue_no_float)
            if composed is not None and composed.accent_fixture is not None:
                accent_group_name = _EFFECT_GROUPS.get(composed.accent_fixture.group_no)
                if accent_group_name is not None:
                    before = prev_dims[accent_group_name]
                    after = row[accent_group_name]
                    rises = (before or 0.0) < (after or 0.0)
                    accent_rows.append(
                        {
                            "cue_no": row["cue_no"],
                            "group": accent_group_name,
                            "before": before,
                            "after": after,
                            "rises": rises,
                        }
                    )
            prev_dims = {name: row[name] for name in _EFFECT_GROUPS.values()}
        summary_b.append({"song": song_name, "accent_cues": accent_rows})

        # --- 측정 c: AC-001/AC-004 재확인 ---
        gate_cues = m._gate_cues_from_commands(commands, result["bundle_cues"])
        gate_result = evaluate(gate_cues, sent_lines=commands)
        under3 = [(no, n) for no, n in gate_result.cue_lit_layers if n < 3]
        summary_c.append(
            {
                "song": song_name,
                "n_section_cues": len(gate_result.cue_lit_layers),
                "n_cues_lit_ge_3": len(gate_result.cue_lit_layers) - len(under3),
                "n_cues_lit_lt_3": len(under3),
                "color_count": gate_result.color_count,
                "color_change_count": gate_result.color_change_count,
            }
        )

        n_violations = sum(non_accent_violations.values())
        n_accent_ok = sum(1 for r in accent_rows if r["rises"])
        print(
            f"{song_name}: 비액센트 큐 {non_accent_cue_count}개 중 effect>0 위반 "
            f"{non_accent_violations} (합 {n_violations}) · "
            f"액센트 큐 {len(accent_rows)}개 중 상승 {n_accent_ok}/{len(accent_rows)} · "
            f"LIT>=3 {summary_c[-1]['n_cues_lit_ge_3']}/{summary_c[-1]['n_section_cues']} · "
            f"색 {summary_c[-1]['color_count']}종"
        )

    (HERE / "measure_m5_a_non_accent_zero.json").write_text(
        json.dumps(summary_a, ensure_ascii=False, indent=1), "utf-8"
    )
    (HERE / "measure_m5_b_accent_rising.json").write_text(
        json.dumps(summary_b, ensure_ascii=False, indent=1), "utf-8"
    )
    (HERE / "measure_m5_c_ac001_ac004_recheck.json").write_text(
        json.dumps(summary_c, ensure_ascii=False, indent=1), "utf-8"
    )

    total_violations = sum(sum(row["violations_per_group"].values()) for row in summary_a)
    total_accent = sum(len(row["accent_cues"]) for row in summary_b)
    total_accent_ok = sum(sum(1 for r in row["accent_cues"] if r["rises"]) for row in summary_b)
    total_lit_ge_3 = sum(row["n_cues_lit_ge_3"] for row in summary_c)
    total_section_cues = sum(row["n_section_cues"] for row in summary_c)
    print(
        f"\n합계: 비액센트 큐 effect>0 위반 {total_violations}건(목표 0) · "
        f"액센트 상승 {total_accent_ok}/{total_accent} · "
        f"AC-001 LIT>=3 {total_lit_ge_3}/{total_section_cues}"
    )


if __name__ == "__main__":
    main()
