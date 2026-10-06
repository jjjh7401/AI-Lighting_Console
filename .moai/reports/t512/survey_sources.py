"""t512 ① — 송신 기록 후보 파일의 행 종류를 센다(어느 행이 「실제로 나간 줄」인지 고르기 위한 판독).

실행: uv run python .moai/reports/t512/survey_sources.py <jsonl> [<jsonl> ...]
"""

import collections
import json
import pathlib
import sys

for p in sys.argv[1:]:
    c = collections.Counter()
    keys = set()
    for line in pathlib.Path(p).read_text("utf-8").splitlines():
        d = json.loads(line)
        c[(d.get("event"), d.get("kind"), d.get("outcome"), d.get("fired"))] += 1
        keys |= set(d)
    print(p)
    for k, n in c.most_common():
        print("   ", n, "event/kind/outcome/fired =", k)
    print("    keys:", sorted(keys))
