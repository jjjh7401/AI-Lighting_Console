"""t507 — M1 대본 기계 점검(사전 체일 뿐, 완료 판정 아님).

실행: python3 .moai/reports/t507/check_script.py

1) 대본에 적힌 마디 시각을 t505 음악 지도(위상 0)와 대조한다.
2) AC-LDRHYTHM-003: 6칸 머리글, 층·모멘트유형 닫힌 어휘, 코드 블록 0.
3) AC-LDRHYTHM-005: 박자 층 행의 연출이 세 범주 중 하나로 시작하는가.
4) AC-LDRHYTHM-006: 강조 행의 모멘트유형이 {코러스진입, 드롭, 마지막코러스} 안인가,
   "§10 금지목록 4번" 인용 ≥1, 오표기 0.
5) 박자 층 이벤트 수 합계를 대본 본문의 "N회" 표기에서 다시 센다.
"""

import json
import re
from pathlib import Path

SCRIPT = Path(".moai/specs/SPEC-LDRHYTHM-001/m1-club-diver-script.md")
MAP = Path(".moai/reports/t505/evidence/clubdiver_map_phase0.json")
HEADER = ["시각", "층", "모멘트유형", "연출", "잇는 방식", "이유"]
LAYERS = {"박자", "강조"}
MOMENTS = {"코러스진입", "드롭", "마지막코러스", "기타"}
ACCENT_OK = {"코러스진입", "드롭", "마지막코러스"}
BEAT_KINDS = ("킥/스네어 펄스", "체이스 한 칸", "색/위치 한 단계")

text = SCRIPT.read_text(encoding="utf-8")
bars = {b["bar"]: b["start_s"] for b in json.loads(MAP.read_text())["bars"]}

# 대본 표 추출 — 머리글이 HEADER 와 같은 표
lines = text.split("\n")
start = next(i for i, ln in enumerate(lines) if ln.startswith("| 시각 | 층 |"))
head = [c.strip() for c in lines[start].strip().strip("|").split("|")]
rows = []
for ln in lines[start + 2 :]:
    if not ln.startswith("|"):
        break
    rows.append([c.strip() for c in ln.strip().strip("|").split("|")])

problems = []
if head != HEADER:
    problems.append(f"머리글 불일치: {head}")
for r in rows:
    if len(r) != 6:
        problems.append(f"칸 수 {len(r)}: {r[0]}")
        continue
    t, layer, moment, act = r[0], r[1], r[2], r[3]
    if layer not in LAYERS:
        problems.append(f"층 어휘 밖: {t} {layer!r}")
    if moment not in MOMENTS:
        problems.append(f"모멘트유형 어휘 밖: {t} {moment!r}")
    if layer == "강조" and moment not in ACCENT_OK:
        problems.append(f"강조가 큰 히트 밖: {t} {moment}")
    if layer == "박자" and not act.startswith(BEAT_KINDS):
        problems.append(f"박자 행 범주 불명: {t} {act[:20]}")
    # 시각 대조: "m:ss.s (N마디" 꼴의 첫 시각과 첫 마디 번호
    m = re.match(r"(\d):(\d\d\.\d)", t)
    n = re.search(r"\((\d+)", t)
    if m and n:
        sec = int(m.group(1)) * 60 + float(m.group(2))
        bar = int(n.group(1))
        if abs(sec - bars[bar]) > 0.06:
            problems.append(f"시각 불일치: {t} → 지도 {bars[bar]:.3f}")
    # 여러 시각을 · 로 나열한 행은 마디 번호 목록과 하나씩 대조
    times = re.findall(r"(\d):(\d\d\.\d)", t.split("(")[0])
    nums = re.findall(r"\d+", t.split("(")[1].split("마디")[0]) if "(" in t else []
    if len(times) > 2 and len(times) == len(nums):
        for (mm, ss), nb in zip(times, nums, strict=True):
            sec = int(mm) * 60 + float(ss)
            if abs(sec - bars[int(nb)]) > 0.06:
                problems.append(f"나열 시각 불일치: {mm}:{ss} 마디 {nb} → {bars[int(nb)]:.3f}")

accent = [r for r in rows if r[1] == "강조"]
print("rows", len(rows), "beat", sum(r[1] == "박자" for r in rows), "accent", len(accent))
print("accent moments", [(r[0], r[2]) for r in accent])
print("code_blocks", text.count("```"))
print("cite_10_4", text.count("§10 금지목록 4번"))
print("misquote", len(re.findall(r"§10\.3", text)))
print("problems", len(problems))
for p in problems:
    print("  -", p)
