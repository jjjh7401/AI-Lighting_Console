"""t510: LOVE ATTACK 기존 앱 연출 기준선 — 큐별 시각·유지 시간·색·층·페이저·속도·강조 표.

입력(전부 rehearse_song.py 산출, 가짜 콘솔 — 콘솔 접촉 0):
  run1/console_commands_approved.txt  송신 층(= console_commands_sent.txt, cmp 확인)
  run1/bundle_full.json               설계 층(조립기 번들)
  run1/readout.json                   readout.py 판독(무대 층·페이저 제안)
  run1/analysis.json                  곡 분석(마지막 구간 끝 = 곡 끝)

유지 시간 = 다음 큐 TrigTime − 이 큐 TrigTime (t502 hold_durations.py 와 같은 정의).
마지막 큐는 t502 와 달리 곡 끝(분석 마지막 구간 end_ms)까지로 잰다 — 표에 따로 표시.

실행: python3 .moai/reports/t510/hold_table.py  → 표준출력(마크다운 표) + hold_table.json
"""

# ruff: noqa: E501 — 마크다운 표 한 행을 f-string 그대로 찍는 판독 스크립트라 줄 길이 규칙을 끈다
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / "run1"
sent = (RUN / "console_commands_approved.txt").read_text("utf-8").splitlines()
bundle = {
    f"{c['cue_number']:g}": c for c in json.loads((RUN / "bundle_full.json").read_text())["cues"]
}
readout = {c["cue"]: c for c in json.loads((RUN / "readout.json").read_text())["cues"]}
song_end = json.loads((RUN / "analysis.json").read_text())["sections"][-1]["end_ms"] / 1000

STORE = re.compile(r"^Store Sequence \d+ Cue ([\d.]+) '([^']*)'(?: CueFade ([\d.]+))?")
TRIG = re.compile(r"^Set Cue ([\d.]+) Sequence \d+ Property 'TrigTime' ([\d.]+)$")
GRP = re.compile(r"^Group (\d+) ; Attribute '(\w+)' At ([\d.]+)")
GROUP_NAMES = {3: "FOH", 4: "BACK", 7: "SIDE-ALL", 10: "WASH-ALL", 13: "MOVER-ALL",
               14: "BLIND", 15: "STROBE", 16: "HAZE"}  # fmt: skip
RGB_NAME = {(5, 20, 100): "블루", (0, 90, 100): "cyan", (100, 75, 40): "warm white"}

trig = {m.group(1): float(m.group(2)) for line in sent if (m := TRIG.match(line))}
cues, pending = [], []
for line in sent:
    if m := STORE.match(line):
        cues.append({"no": m.group(1), "name": m.group(2), "fade": m.group(3), "lines": pending})
        pending = []
    elif line.startswith(("Fixture", "Group")):
        pending.append(line)

speed_lines = [x for x in sent if re.search(r"speed|BPM", x, re.I)]
phaser_lines = [x for x in sent if "At Preset" in x and not re.search(r"At Preset 2\.", x)]

rows = []
for i, c in enumerate(cues):
    t = trig[c["no"]]
    nxt = trig[cues[i + 1]["no"]] if i + 1 < len(cues) else song_end
    fix_dim = next(
        (
            float(x.rsplit("At ", 1)[1])
            for x in c["lines"]
            if x.startswith("Fixture") and "'Dimmer'" in x
        ),
        None,
    )
    fix_rgb = next(
        (tuple(int(v) for v in re.findall(r"At (\d+)", x)) for x in c["lines"]
         if x.startswith("Fixture") and "ColorRGB_R" in x),
        None,
    )  # fmt: skip
    layer_rgb, layer_dim = {}, {}
    for x in c["lines"]:
        if m := GRP.match(x):
            g = GROUP_NAMES[int(m.group(1))]
            if m.group(2) == "Dimmer":
                layer_dim[g] = float(m.group(3))
            else:
                layer_rgb[g] = tuple(int(v) for v in re.findall(r"At (\d+)", x))
    d = bundle[c["no"]]
    r = readout[c["no"]]
    rows.append(
        {
            "cue": c["no"],
            "name": c["name"],
            "kind": d["kind"],
            "d": d["d_level"],
            "trig_s": t,
            "hold_s": round(nxt - t, 3),
            "hold_to_song_end": i + 1 == len(cues),
            "fade_s": float(c["fade"]) if c["fade"] else 0.0,
            "position": d["position"]["stored"],
            "preset": next(iter(r["sent_presets"]), None),
            "all_dimmer": fix_dim,
            "layer_dimmer": layer_dim,
            "all_rgb": RGB_NAME.get(fix_rgb, fix_rgb),
            "layer_rgb": {k: RGB_NAME.get(v, v) for k, v in layer_rgb.items()},
            "stage_layers": r["stage_rig_layers"],
            "phaser_hint": r["design_phaser_hint"],
            "fx_requested": d["fx"]["requested"],
            "fx_permitted": d["fx"]["permitted"],
            "accent_fixture": d.get("accent_fixture"),
            "accents": d.get("accents", []),
            "pre_drop_from": d.get("pre_drop_from"),
        }
    )

print(
    "| 큐 | 이름 | D | 시각(s) | 유지(s) | 페이드(s) | 포지션(프리셋) | 전체 디머 | "
    "BACK/SIDE/WASH/MOVER | BLIND | 전체 색 | SIDE·WASH 색 | FOH 색 | 무대 층 | 페이저 제안 → 송신 | 효과 요청/허용 |"
)
print("|" + "---|" * 16)
for w in rows:
    ld = w["layer_dimmer"]
    hold = f"{w['hold_s']:.1f}" + ("*" if w["hold_to_song_end"] else "")
    print(
        f"| {w['cue']} | {w['name']} | D{w['d']} | {w['trig_s']:.1f} | {hold} | {w['fade_s']:.2f} | "
        f"{w['position']}({w['preset']}) | {w['all_dimmer']:g} | "
        f"{ld.get('BACK', 0):g}/{ld.get('SIDE-ALL', 0):g}/{ld.get('WASH-ALL', 0):g}/{ld.get('MOVER-ALL', 0):g} | "
        f"{ld.get('BLIND', 0):g} | {w['all_rgb']} | {w['layer_rgb'].get('SIDE-ALL')} | {w['layer_rgb'].get('FOH')} | "
        f"{w['stage_layers']} | {w['phaser_hint'] or '—'} → 0 | "
        f"{len(w['fx_requested'])}/{len(w['fx_permitted'])} |"
    )
holds = sorted(w["hold_s"] for w in rows)
inner = sorted(w["hold_s"] for w in rows if not w["hold_to_song_end"])
print(
    f"\n유지 시간(마지막 큐 제외, t502 정의) n={len(inner)} max={inner[-1]:.1f}s "
    f"median={inner[len(inner) // 2]:.1f}s >=20s={sum(h >= 20 for h in inner)} "
    f">=10s={sum(h >= 10 for h in inner)}"
)
print(f"마지막 큐 포함(곡 끝 {song_end:.3f}s 까지) n={len(holds)} max={holds[-1]:.1f}s")
print(
    f"송신 속도(speed/BPM) 줄 {len(speed_lines)} · 페이저(풀 2 밖 At Preset) 줄 {len(phaser_lines)}"
)
(HERE / "hold_table.json").write_text(
    json.dumps(
        {
            "song_end_s": song_end,
            "rows": rows,
            "speed_lines": speed_lines,
            "phaser_lines": phaser_lines,
        },
        ensure_ascii=False,
        indent=1,
        default=str,
    ),
    "utf-8",
)
