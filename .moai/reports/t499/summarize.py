"""t499 — readout.py 가 남긴 summary.json 에서 8곡 요약표 + 「붕괴 지점별 영향 곡 수」 표.

콘솔 접촉 없음.
실행: uv run python .moai/reports/t499/summarize.py > .moai/reports/t499/summary_tables.md
"""

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
songs = json.loads((HERE / "summary.json").read_text("utf-8"))
RIG = ("KEY", "FOH", "BACK", "SIDE", "WASH", "MOVER", "BLIND", "STROBE")


def differing_groups(view: dict) -> int:
    """8그룹 중 다수 값과 다른 값을 받은 그룹 수(그룹 안이 섞여 있으면 그것도 다름으로 센다)."""
    keys = [json.dumps(view[g], sort_keys=True) for g in RIG]
    majority, _ = Counter(keys).most_common(1)[0]
    return sum(1 for k in keys if k != majority)


rows, collapse = [], Counter()
for s in songs:
    cues = s["cues"]
    sec = [c for c in cues if c["kind"] == "section"]
    names = {p for c in sec for p in c["design_palette"]}
    combos = {tuple(c["design_palette"]) for c in sec}
    primaries = {c["design_palette"][0] for c in sec if c["design_palette"]}
    sent_rgb = {tuple(r) for c in cues for r in c["sent_rgb_in_cue"]}
    d_prim_changes = sum(c["design_color_changed"] for c in cues)
    d_pal_changes = sum(c["design_palette_changed"] for c in cues)
    s_changes = sum(c["sent_color_changed"] for c in cues)
    sel_max = max(c["sent_selection_sets"] for c in cues)
    layers_max = max(c["stage_rig_layers"] for c in cues)
    diff_groups = [differing_groups(c["stage_rig_view"]) for c in cues]
    d_pos = {c["design_position"] for c in sec if c["design_position"]}
    s_pos = {p for c in cues for p in c["sent_presets"]}
    fx_req = sum(len(c["design_fx_requested"]) for c in cues)
    fx_perm = sum(len(c["design_fx_permitted"]) for c in cues)
    hint = sum(1 for c in cues if c["design_phaser_hint"])
    fx_sent = len(s["phaser_or_other_preset_lines"])
    # 송신 디머 = 설계 key_pct 인가(구간 큐의 전체 기구 디머 줄)
    dim_mismatch = [
        c["cue"]
        for c in sec
        if c["design_key_pct"] is not None
        and c["sent_dimmers"]
        and c["sent_dimmers"][0] != c["design_key_pct"]
    ]
    by_role = {}
    for c in sec:
        if c["design_key_pct"] is not None:
            by_role.setdefault(c["role"], []).append(c["design_key_pct"])
    acc_design = sum(len(c["design_accents"]) for c in cues)
    acc_fixture = sum(1 for c in cues if c["design_accent_fixture"])
    acc_sent = sum(
        1 for c in cues for g in c["sent_group_lines"] if "BLIND" in g and not g.endswith("At 0")
    )
    pre_drop = sum(1 for c in cues if c["design_pre_drop_from"] is not None)
    viol = Counter(v[0] for v in s["violations"])
    strobe_dim = max(c["stage_rig_view"]["STROBE"][0].get("dim", 0) for c in cues)
    rows.append(
        {
            "song": s["song"],
            "sections": len(sec),
            "cues": s["n_sent_cues"],
            "lines": s["n_lines"],
            "design_color_names": len(names),
            "design_combos": len(combos),
            "design_primaries": len(primaries),
            "sent_rgb": len(sent_rgb),
            "d_prim_changes": d_prim_changes,
            "d_pal_changes": d_pal_changes,
            "s_changes": s_changes,
            "sel_max": sel_max,
            "layers_max": layers_max,
            "diff_groups_max": max(diff_groups),
            "d_pos": len(d_pos),
            "s_pos": len(s_pos),
            "fx_req": fx_req,
            "fx_perm": fx_perm,
            "hint": hint,
            "fx_sent": fx_sent,
            "dim_mismatch": dim_mismatch,
            "dim_by_role": {r: (min(v), max(v)) for r, v in by_role.items()},
            "acc_design": acc_design,
            "acc_fixture": acc_fixture,
            "acc_sent": acc_sent,
            "pre_drop": pre_drop,
            "viol": dict(viol),
            "arc_notes": s["arc_notes"],
            "strobe_dim": strobe_dim,
        }
    )

print("## 8곡 요약표 (설계 층 → 송신 층)\n")
print(
    "| 곡 | 구간 | 송신 큐·줄 | 색: 설계 이름/조합/주색 → 송신 RGB "
    "| 색 변화: 설계 주색·팔레트 → 송신 | 기구 선택 묶음(큐당 최대) "
    "| 무대 층(최대) · 다른 값 받은 그룹(8중 최대) | 포지션: 설계 → 송신 "
    "| 효과: 요청/허용/페이저 제안 큐 → 송신 줄 | 액센트: 설계 액센트·블라인더 큐 → 송신 "
    "| 드롭 앞 어둠(설계) |"
)
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print(
        f"| {r['song']} | {r['sections']} | {r['cues']}·{r['lines']} | "
        f"{r['design_color_names']}/{r['design_combos']}/{r['design_primaries']} "
        f"→ **{r['sent_rgb']}** | "
        f"{r['d_prim_changes']}·{r['d_pal_changes']} → **{r['s_changes']}** | {r['sel_max']} | "
        f"{r['layers_max']} · {r['diff_groups_max']} | "
        f"{r['d_pos']} → {r['s_pos']} | {r['fx_req']}/{r['fx_perm']}/{r['hint']} "
        f"→ **{r['fx_sent']}** | "
        f"{r['acc_design']}·{r['acc_fixture']} → {r['acc_sent']} | {r['pre_drop']} |"
    )
print("\n## 구간 성격별 디머(설계 key_pct = 송신 전체 디머)\n")
print("| 곡 | 설계≠송신 큐 | intro | verse | chorus | bridge | finale |")
print("|---|---|---|---|---|---|---|")


def cell(row: dict, role: str) -> str:
    if role not in row["dim_by_role"]:
        return "—"
    return "{:g}~{:g}".format(*row["dim_by_role"][role])


for r in rows:
    roles = ("intro", "verse", "chorus", "bridge", "finale")
    print(
        f"| {r['song']} | {len(r['dim_mismatch'])} | "
        + " | ".join(cell(r, k) for k in roles)
        + " |"
    )
print("\n정본 §6 대역: intro 20~40 · verse 25~50 · chorus 80~100 · bridge 20~35 · finale 행 없음\n")

clauses = ["§6 밝기", "§6 색", "§6 움직임·효과", "§6.1", "§6.2 층", "§6.3 색", "§7 상승", "§8 어둠"]
print("## 정본 조항별 위반 (곡마다 위반 항목 수, readout.py violations())\n")
print("| 곡 | " + " | ".join(clauses) + " |")
print("|---|" + "---|" * len(clauses))
for r in rows:
    print(f"| {r['song']} | " + " | ".join(str(r["viol"].get(c, 0)) for c in clauses) + " |")
print(
    "| **위반 곡 수** | "
    + " | ".join(str(sum(1 for r in rows if r["viol"].get(c))) for c in clauses)
    + " |"
)

pts = [
    ("P1 보조색 탈락", lambda r: r["design_color_names"] > 1 and r["sent_rgb"] == 1),
    ("P2 설계 주색 고정", lambda r: r["design_primaries"] == 1),
    ("P3 기구 선택 한 묶음", lambda r: r["sel_max"] == 1),
    ("P3′ 효과 기구가 전체 값을 받음", lambda r: r["strobe_dim"] > 0),
    ("P4 층 매핑 미사용(BACK 외)", lambda r: r["layers_max"] <= 2),
    ("P5a 효과 허용 0", lambda r: r["fx_req"] > 0 and r["fx_perm"] == 0),
    ("P5b 페이저 제안 → 송신 0", lambda r: r["hint"] > 0 and r["fx_sent"] == 0),
    ("P6 디머 대역 이탈(설계)", lambda r: r["viol"].get("§6 밝기", 0) > 0),
    ("P7 후렴 이음 무변화", lambda r: r["viol"].get("§7 상승", 0) > 0),
    ("P8 드롭 앞 어둠 부재", lambda r: r["viol"].get("§8 어둠", 0) > 0),
    (
        "P9 절정 블라인더 근거 없음",
        lambda r: any("blinder_six_row_absent" in n for n in r["arc_notes"]),
    ),
]
print("\n## 붕괴 지점별 영향 곡 수\n")
print("| 붕괴 지점 | 영향 곡 수 | 곡 |")
print("|---|---|---|")
for name, pred in pts:
    hit = [r["song"] for r in rows if pred(r)]
    print(f"| {name} | **{len(hit)}/8** | {', '.join(hit)} |")
