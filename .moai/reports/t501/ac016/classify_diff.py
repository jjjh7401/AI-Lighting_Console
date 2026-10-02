"""t501 AC-016 준비 — 리허설 승인 목록(가짜 콘솔) 대 실기 승인 목록(전부-거절)의
차이 줄을 **전부** 분류한다. t498 `classify_diff.py`를 일반화한 것 — 두 인자
모두 어느 곡·시퀀스든 받는 평문 명령 목록 파일이면 된다(로직은 한 글자도
안 바꿨다, t498 분류 규칙이 곡에 의존하지 않기 때문).

리드 규칙(2026-09-28, t498 원문 인용): 차이 줄 전부가 「가짜 콘솔에 없던 W 채널
줄」로 설명될 때만 실기 목록으로 고정 승인. 설명 안 되는 줄이 하나라도 있으면
쓰지 않는다.

분류 방법:
  1) 기구 목록 정규화 — 줄 머리 `Fixture <번호 + 번호 ...> ;` 를 `Fixture <SET> ;` 로
     바꾼다. 가짜 콘솔은 좌표 판독을 두 기구(fid 20·26)로 대역하므로 기구 목록만
     다른 줄이 생긴다.
  2) 정규화 뒤 두 목록을 순서대로 맞춘다(difflib). 남는 줄을 종류별로 센다.
  3) 실기 쪽에만 있는 줄이 전부 `ColorRGB_W` 줄인지, 그 기구 번호가 무엇인지 적는다.
  4) 정규화로 같아진 줄도 **기구 수**를 적는다(실기 쪽 기구 목록이 줄마다 같은지).

자가 시험: t498 저장 쌍(run1_fake_rain_1 대 run3_rain_real_denyall)에 돌려
run3_classify_diff.txt 와 같은 분류(UNEXPLAINED 0, W-channel=12)가 나오는지
확인한다 — 이 파일의 README.md 참조.

실행: uv run python .moai/reports/t501/ac016/classify_diff.py <리허설.txt> <실기.txt>
"""

import difflib
import re
import sys
from collections import Counter
from pathlib import Path

REH, REAL = Path(sys.argv[1]), Path(sys.argv[2])
FIX = re.compile(r"^Fixture ((?:\d+)(?: \+ \d+)*) ;")


def norm(line: str) -> str:
    return FIX.sub("Fixture <SET> ;", line)


def fixtures(line: str) -> tuple[int, ...]:
    m = FIX.match(line)
    return tuple(int(x) for x in m.group(1).split(" + ")) if m else ()


reh = REH.read_text("utf-8").splitlines()
real = REAL.read_text("utf-8").splitlines()
print(f"lines rehearsal={len(reh)} real={len(real)}")

nreh, nreal = [norm(x) for x in reh], [norm(x) for x in real]
sm = difflib.SequenceMatcher(a=nreh, b=nreal, autojunk=False)
only_reh, only_real = [], []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    only_reh += reh[i1:i2]
    only_real += real[j1:j2]
print(f"after fixture-set normalisation: only_rehearsal={len(only_reh)} only_real={len(only_real)}")
for x in only_reh:
    print("  UNEXPLAINED rehearsal-only:", x[:200])

w_lines = [x for x in only_real if "ColorRGB_W" in x]
other = [x for x in only_real if "ColorRGB_W" not in x]
print(f"real-only lines: W-channel={len(w_lines)} other={len(other)}")
for x in other:
    print("  UNEXPLAINED real-only:", x[:200])
print("W line tails:", Counter(FIX.sub("", x).strip() for x in w_lines))
w_sets = Counter(fixtures(x) for x in w_lines)
for s, n in w_sets.items():
    print(f"W fixture set used {n}x: count={len(s)} ids={list(s)}")

# 정규화로 같아진 줄의 실기 쪽 기구 목록 종류
real_sets = Counter(fixtures(x) for x in real if FIX.match(x) and "ColorRGB_W" not in x)
reh_sets = Counter(fixtures(x) for x in reh if FIX.match(x))
print("rehearsal fixture sets:", [(len(s), list(s)[:6], n) for s, n in reh_sets.items()])
print("real non-W fixture sets:", [(len(s), n) for s, n in real_sets.items()])
verdict = not only_reh and not other
print("VERDICT all diff lines explained by fixture-set + W-channel:", verdict)
