"""t520 — 시퀀스 269·270 큐 Part 크기 읽기 단계 파일을 만든다(읽기 전용, t516 비교 포함)."""

from pathlib import Path

lines = ["ping"]
for i in range(3, 18):
    lines.append(f"props:ShowData/DataPools/Default/Sequences/270/{i}|NAME,MEMORYFOOTPRINT")
    lines.append(f"props:ShowData/DataPools/Default/Sequences/270/{i}/1|NAME,MEMORYFOOTPRINT")
for i in range(3, 10):
    lines.append(f"props:ShowData/DataPools/Default/Sequences/269/{i}/1|NAME,MEMORYFOOTPRINT")
for seq in (228, 229, 236, 237, 246, 248, 255, 263):
    lines.append(f"props:ShowData/DataPools/Default/Sequences/{seq}/3/1|NAME,MEMORYFOOTPRINT")
Path(".moai/reports/t520/steps_parts.txt").write_text("\n".join(lines) + "\n", "utf-8")
print(len(lines))
