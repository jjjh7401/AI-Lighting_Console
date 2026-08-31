"""t201 - 두 계기를 합쳐 45행 실태 표를 낸다.

분류 규칙(기계적으로 적용, 예외 없음):
  1. spec.md 자체가 없다              -> (c) 대상 소멸
  2. 프론트매터 status == completed    -> (e) 완료
  3. 비테스트 구현 파일 0              -> (a) 살아 있는 목표
  4. 비테스트 구현 파일 >= 5           -> (b) 구현됐고 닫기만 남음
  5. 그 사이 1~4                       -> (d) 판단 불가

status 는 moai spec status --list 를 정본으로 쓴다 - 내 정규식은 프론트매터
블록 밖의 status: 줄까지 잡아 IMGLAYOUT 을 틀리게 읽었다(도구가 맞았다).
"""

import csv

REALITY = ".moai/reports/t201/probes/spec-reality.tsv"
IMPL = ".moai/reports/t201/probes/spec-impl.tsv"
STATUSLIST = ".moai/reports/t201/probes/spec-status-list.txt"


def read_tsv(path):
    rows = dict()
    with open(path, encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or row[0].startswith("#") or row[0] == "id":
                continue
            rows[row[0]] = row
    return rows


def read_status():
    out = dict()
    with open(STATUSLIST, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith("SPEC-COPILOT-"):
                out[parts[0]] = parts[1]
    return out


def classify(has_spec, status, nontest):
    if not has_spec:
        return "c"
    if status == "completed":
        return "e"
    if nontest == 0:
        return "a"
    if nontest >= 5:
        return "b"
    return "d"


def main():
    reality = read_tsv(REALITY)
    impl = read_tsv(IMPL)
    status = read_status()
    tally = dict(a=0, b=0, c=0, d=0, e=0)
    live = []
    print("| SPEC | 프론트매터 | 실제 | 비테스트구현 | 커밋 | 최종 | 근거 |")
    print("|---|---|:--:|---:|---:|---|---|")
    for sid in sorted(reality):
        r = reality[sid]
        i = impl[sid]
        st = status.get(sid, "?")
        nontest = int(i[4])
        has_spec = r[1] != "no-spec.md"
        k = classify(has_spec, st, nontest)
        tally[k] += 1
        if k == "a":
            live.append(sid)
        why = f"커밋 {r[5]}건 · 구현파일 {i[2]} (비테스트 {nontest})"
        if not has_spec:
            why = "spec.md 없음"
        short = sid.replace("SPEC-COPILOT-", "")
        print(f"| {short} | {st} | **{k}** | {nontest} | {r[5]} | {r[7]} | {why} |")
    print()
    print(
        f"합계: a={tally[chr(97)]} b={tally[chr(98)]} c={tally[chr(99)]} "
        f"d={tally[chr(100)]} e={tally[chr(101)]}  총 {sum(tally.values())}"
    )
    print()
    print("살아 있는 목표 (a):")
    for sid in live:
        print(f"  - {sid}")


if __name__ == "__main__":
    main()
