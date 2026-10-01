"""t499 — 기구 번호 → 이름·그룹 접두어 표.

출처는 t498 run4 실기 읽기(콘솔 접촉 없음, 파일만 읽는다).
그룹은 **기구 이름의 첫 단어**(예: 'KEY 101' → KEY)다.
콘솔 그룹 풀의 실제 구성원은 응답기로 못 읽는다
(t498 §6) — 이 표는 이름 기반 추정이며, 판독 도구는 그 사실을 INFERRED 로 표기한다.

실행: uv run python .moai/reports/t499/fid_names.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE.parent / "t498/run4_fixture_names.txt").read_text("utf-8")
pairs = []
for line in src.splitlines():
    if not line.startswith("<<< "):
        continue
    reads = {r["n"]: r.get("v") for r in json.loads(line[4:]).get("reads", [])}
    if "FID" in reads and "Name" in reads:
        pairs.append((int(reads["FID"]), reads["Name"], reads.get("FixtureType")))
table = {str(f): {"name": n, "group": n.split()[0], "type": t} for f, n, t in pairs}
real_line = (HERE.parent / "t498/run3_rain_real_denyall/approval_request_1.txt").read_text("utf-8")
real = {
    int(x) for x in real_line.splitlines()[1].split(";")[0].removeprefix("Fixture ").split(" + ")
}
assert real == {f for f, _, _ in pairs}, (len(real), len(pairs))
(HERE / "fid_names.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), "utf-8")
print(len(table), "fixtures; same set as real approval list line 2")
