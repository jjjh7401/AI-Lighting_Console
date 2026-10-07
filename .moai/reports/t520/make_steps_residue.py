"""t520 — 정리용 잔여 객체 판독 단계 파일(읽기 전용): 시퀀스 250~270, 타임코드 22~24 의 이름."""

from pathlib import Path

lines = ["ping"]
lines += [f"props:ShowData/DataPools/Default/Sequences/{n}|NAME" for n in range(250, 271)]
lines += [f"props:ShowData/DataPools/Default/Timecodes/{n}|NAME" for n in (22, 23, 24)]
Path(".moai/reports/t520/steps_residue.txt").write_text("\n".join(lines) + "\n", "utf-8")
print(len(lines))
