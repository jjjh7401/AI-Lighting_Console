"""t501 AC-016 — 쓰기 뒤 읽기 전용 되읽기: 시퀀스 212(Rain)·213(Club Diver) 큐 속성.

t498 run8_cue_props.txt 와 같은 props 조회(NAME,TRIGTYPE,TRIGTIME,CUEFADE)만 보낸다 —
probe_readonly.py 를 그대로 돌린다(ping/state/props 만, 쓰기 없음).
자식 1·2 는 OffCue·CueZero 라서 3번부터 읽는다(postwrite_state.txt).

실행: uv run python .moai/reports/t501/ac016/postwrite_cue_props_probe.py
"""

import runpy
import sys

FIELDS = "NAME,TRIGTYPE,TRIGTIME,CUEFADE"
ROOT = "ShowData/DataPools/Default/Sequences"
steps = [f"props:{ROOT}/212/{i}|{FIELDS}" for i in range(3, 16)]
steps += [f"props:{ROOT}/213/{i}|{FIELDS}" for i in range(3, 17)]
sys.argv = [".moai/reports/t498/probe_readonly.py", *steps]
runpy.run_path(".moai/reports/t498/probe_readonly.py", run_name="__main__")
