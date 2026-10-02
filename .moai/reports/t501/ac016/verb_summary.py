"""t501 AC-016 준비 — 명령 목록 파일 한 장의 동사·번호 요약.

리드가 재승인(`--approve`) 전 눈으로 확인할 지점: 이 명령 목록이 Store 류만
하는지, Delete/Overwrite/SaveShow 같은 위험한 동사가 섞여 있는지, 그리고
실제로 손댄 번호(시퀀스·큐·타임코드·프리셋·그룹)가 이번 지시(212/213,
타임코드 12/13, 프리셋 풀 2 의 21~30, 풀 4 의 9~11, 풀 21 의 7~8)를
벗어나는지 — 콘솔을 열지 않고 명령 목록 텍스트 한 장만 읽고 판단한다.

판독 방식: 각 줄의 **첫 토큰**으로 동사를 센다(문장 중간의 같은 단어는
세지 않는다 — 예: `Set Cue 1 Sequence 211 Property 'TrigType' 'Time'` 의
`Cue`/`Sequence`는 Store/Assign 같은 동사가 아니다). 번호는 줄 안 어디든
`<종류> <번호>` 패턴으로 전부 긁는다(문법상 같은 숫자가 여러 줄에 걸쳐
반복되는 것은 정상 — Store 에서 쓴 번호를 Set/Assign 이 다시 참조한다).

실행: uv run python .moai/reports/t501/ac016/verb_summary.py <명령 목록.txt>
"""

import re
import sys
from collections import Counter
from pathlib import Path

PATH = Path(sys.argv[1])
lines = PATH.read_text("utf-8").splitlines()

#: 배차서가 지정한 8개 동사. 줄 머리에서만 센다.
VERBS = ("Store", "Delete", "Overwrite", "SaveShow", "Label", "Copy", "Move", "Assign")
_FIRST_WORD = re.compile(r"^(\w+)")

verb_counts: Counter[str] = Counter()
verb_lines: dict[str, list[str]] = {v: [] for v in VERBS}
other_first_words: Counter[str] = Counter()
for line in lines:
    m = _FIRST_WORD.match(line)
    if not m:
        continue
    head = m.group(1)
    if head in VERBS:
        verb_counts[head] += 1
        verb_lines[head].append(line)
    else:
        other_first_words[head] += 1

#: 손댄 번호 — 줄 안 어디든 「<종류> <번호>」 패턴을 전부 긁는다.
NUM_PATTERNS = {
    "Sequence": re.compile(r"\bSequence (\d+)\b"),
    "Cue": re.compile(r"\bCue ([\d.]+)\b"),
    "Timecode": re.compile(r"\bTimecode (\d+)\b"),
    "Preset (pool.no)": re.compile(r"\bPreset (\d+\.\d+)\b"),
    "Group": re.compile(r"^Group (\d+)\b"),
    "Fixture": re.compile(r"^Fixture ([\d \+]+) ;"),
}

written_numbers: dict[str, set[str]] = {k: set() for k in NUM_PATTERNS}
for line in lines:
    for kind, pattern in NUM_PATTERNS.items():
        for m in pattern.finditer(line):
            written_numbers[kind].add(m.group(1))

print(f"파일: {PATH} ({len(lines)}줄)")
print("--- 동사 줄 머리 집계(배차서 지정 8종) ---")
for v in VERBS:
    print(f"  {v}: {verb_counts.get(v, 0)}")
risky = [v for v in VERBS if v not in ("Store", "Assign") and verb_counts.get(v, 0) > 0]
print(f"  위험 동사(Store/Assign 밖) 발견: {risky if risky else '없음'}")

print("--- 줄 머리에 있지만 8종 동사가 아닌 토큰(참고) ---")
for word, n in other_first_words.most_common():
    print(f"  {word}: {n}")

print("--- 손댄 번호(종류별 집합) ---")
for kind, nums in written_numbers.items():
    if kind == "Fixture":
        # 기구 번호는 집합이 아니라 "쓰인 서로 다른 조합 수"로 요약(줄마다
        # 수십~백여 개라 집합을 그대로 찍으면 안 읽힌다).
        combos = {line for line in lines if NUM_PATTERNS["Fixture"].match(line)}
        fid_union: set[str] = set()
        for combo in combos:
            fid_union.update(re.findall(r"\d+", NUM_PATTERNS["Fixture"].match(combo).group(1)))
        print(
            f"  Fixture: 서로 다른 조합 {len(combos)}개, "
            f"등장한 기구 번호 합집합 {len(fid_union)}개"
        )
        continue
    print(f"  {kind}: {sorted(nums, key=lambda x: float(x))}")

#: 동사별로 실제 어떤 줄이었는지(위험 동사가 있을 때 바로 읽도록).
if risky:
    print("--- 위험 동사 줄 전문 ---")
    for v in risky:
        for line in verb_lines[v]:
            print(f"  [{v}] {line[:200]}")
