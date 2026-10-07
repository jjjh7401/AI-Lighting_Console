# ruff: noqa: E501 — 한국어 표 출력
"""t520 — B 그룹판 설계상 「그 시각에 디머가 0 보다 큰 그룹」 표(콘솔 0, 생성기 데이터에서 계산).

장면 253 은 트래킹으로 앞 큐 값이 이어진다고 보고 누적한다. 리듬 254 는 매 큐가 BACK·SIDE 디머를 두 단계로 다시 적는다.
실행: uv run python .moai/reports/t520/lit_table.py
"""

import re
import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import m2a_batch1 as gen  # noqa: E402

gen.configure(253, 254, 23, "M2a B", "group", None)
NAMES = {
    3: "FOH",
    4: "BACK",
    5: "SIDE-L",
    6: "SIDE-R",
    7: "SIDE-ALL",
    10: "WASH-ALL",
    11: "MOVER-U",
    12: "MOVER-D",
    13: "MOVER-ALL",
    14: "BLIND",
}

events = []
for cue, label, _, t, _, lines in gen.SCENE:
    dims = {}
    for v in lines:
        for p in v.parts:
            m = re.match(r"Attribute 'Dimmer' At ([\d.]+)", p)
            if m:
                dims[gen.group_selection(v.ids)] = float(m.group(1))
    events.append((t, "scene", cue, label, dims))
for cue, label, t, _, st in gen.rhythm_states():
    dims = {
        "Group 4": f"{st['back'][0]}/{st['back'][1]}",
        "Group 5": f"{st['side_l'][0]}/{st['side_l'][1]}",
        "Group 6": f"{st['side_r'][0]}/{st['side_r'][1]}",
    }
    events.append((t, "rhythm", cue, label, dims))
events.sort(key=lambda e: (e[0], e[1]))

scene_state: dict = {}
rhythm_state: dict = {}
print("음악초 | 시퀀스.큐 이름 | 이 큐가 준 디머 | → 그 시각 디머 > 0 인 그룹(누적)")
for t, kind, cue, label, dims in events:
    (scene_state if kind == "scene" else rhythm_state).update(dims)
    lit = []
    for g, v in {**scene_state, **rhythm_state}.items():
        hi = max(float(x) for x in str(v).split("/"))
        if hi > 0:
            n = int(g.split()[1])
            lit.append(f"{g}({NAMES[n]}) {v}")
    given = ", ".join(f"{g}={v}" for g, v in dims.items())
    seq = 253 if kind == "scene" else 254
    print(f"{t:6.2f} | {seq}.{cue} {label} | {given} | {' · '.join(lit)}")
print(
    "디머를 한 번도 안 받는 그룹: KEY(2) · WASH-U/D 개별(8·9) · STROBE(15) · HAZE(16) — 이 묶음 대본에 없음"
)
