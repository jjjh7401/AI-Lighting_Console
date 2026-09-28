"""t498 — 3단계 재생 준비: 큐마다 「의도한 시각」 대
「MA3 가 직전 큐 기준으로 읽을 때의 발사 시각」.

근거(콘솔 실측 아님):
- MA3 공식 문서(Sequence Sheet, grandMA3 2.2): Trig Type Time 은 "triggered a set time after
  the previous cue is triggered", Trig Time 은 "starts counting down when the previous cue
  is triggered".
- 저장소 계약 LD-TIME-003(server/director/validate/timing.py:155): 절대 at_ms 를 TrigTime 으로
  넘기지 말고 직전과의 차이로 저장한다.
- 이번 곡 경로(server/looks/songcue.py:654)는 구간 시작 절대 시각을 TrigTime 으로 쓴다.

실행: uv run python .moai/reports/t498/playback_prediction.py <run8_cue_props.txt> <run7 판독.txt>
"""

import json
import re
import sys
from pathlib import Path

PROPS, STATE = Path(sys.argv[1]), Path(sys.argv[2])
BEAT = 60 / 76.0135  # Rain BPM(run1 분석값)

state = STATE.read_text("utf-8").split(">>> state:ShowData/DataPools/Default/Sequences/211\n")[1]
children = json.loads(re.search(r"<<< (\{.*\})", state).group(1))["children"]
slot_to_cue = {c["i"]: (c["cueNo"], c["name"]) for c in children if c.get("cueNo")}

rows = []
for block in PROPS.read_text("utf-8").split(">>> ")[1:]:
    m = re.search(r"<<< (\{.*\})", block)
    if not m:
        continue
    d = json.loads(m.group(1))
    slot = int(d["path"].rsplit("/", 1)[1])
    vals = {r["n"]: r.get("v") for r in d.get("reads", []) if r.get("ok")}
    cue, name = slot_to_cue[slot]
    rows.append((cue, name, float(vals["TRIGTIME"])))
rows.sort()

print(f"beat = {BEAT:.3f}s (B2 허용 오차 1박)")
print("cue | 구간 | 의도 시각(초) | 직전 기준 해석 시 발사(초) | 차이(초) | 차이(박)")
acc = 0.0
for cue, name, t in rows:
    acc += t
    delta = acc - t
    print(f"{cue:g} | {name} | {t:.3f} | {acc:.3f} | {delta:.3f} | {delta / BEAT:.1f}")
print(
    "곡 길이 222.592초(pilot_baseline duration_ms) — "
    "직전 기준 해석이면 그 뒤 발사 큐는 곡 안에 안 온다"
)
