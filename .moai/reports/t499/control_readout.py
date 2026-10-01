"""t499 — readout.py 계기 검증(양성 대조).

Rain 송신 목록 사본에 줄을 하나씩 끼워 넣고 판독 숫자가 움직이는지 본다.

축 하나씩만 건드린다(규약 §3.3): 색 / 층 / 효과 / 포지션. 치환 적용은 assert 로 확인한다.
콘솔 접촉 없음. 실행: uv run python .moai/reports/t499/control_readout.py
"""

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("readout", HERE / "readout.py")
readout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readout)

SRC = HERE / "runs" / "Rain"
ANCHOR = "Store Sequence 211 Cue 4 "  # Chorus 1 저장 줄 바로 앞에 끼운다
ARMS = {
    "color": (
        "Fixture 101 + 102 ; Attribute 'ColorRGB_R' At 100 ; "
        "Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0"
    ),
    "layer": "Group 2 ; Attribute 'Dimmer' At 33",
    "effect": "Fixture 101 + 102 ; At Preset 3.5",
    "position": "Fixture 501 + 502 ; At Preset 2.27",
}


def metrics(song: dict) -> dict:
    cues = song["cues"]
    return {
        "sent_rgb": len({tuple(r) for c in cues for r in c["sent_rgb_in_cue"]}),
        "layers_max": max(c["stage_rig_layers"] for c in cues),
        "selection_max": max(c["sent_selection_sets"] for c in cues),
        "fx_sent": len(song["phaser_or_other_preset_lines"]),
        "presets": len({p for c in cues for p in c["sent_presets"]}),
    }


base = metrics(readout.read_song(SRC))
print("baseline", base)
for arm, line in ARMS.items():
    with tempfile.TemporaryDirectory(prefix="t499-ctl-") as tmp:
        dst = Path(tmp) / "Rain"
        shutil.copytree(SRC, dst)
        path = dst / "console_commands_approved.txt"
        original = path.read_text("utf-8")
        lines = original.splitlines()
        idx = next(i for i, x in enumerate(lines) if x.startswith(ANCHOR))
        lines.insert(idx, line)
        mutated = "\n".join(lines) + "\n"
        assert mutated != original, arm
        path.write_text(mutated, "utf-8")
        shutil.copy(path, dst / "console_commands_sent.txt")
        got = metrics(readout.read_song(dst))
        moved = {k: (base[k], got[k]) for k in base if base[k] != got[k]}
        print(arm, "moved:", json.dumps(moved))
