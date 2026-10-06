# ruff: noqa: E501 — 대본에 그대로 들어갈 한국어 표 행 문자열이라 줄 길이 규칙을 끈다
"""t511 — M1 LOVE ATTACK 대본 기계 점검 + 수 세기 (사전 체일 뿐, 완료 판정 아님).

실행: python3 .moai/reports/t511/count_script.py [--fill]

1) AC-LDRHYTHM-003: 6칸 머리글, 층·모멘트유형 닫힌 어휘, 코드 블록 0
2) AC-LDRHYTHM-005: 박자 행 연출이 세 범주 중 하나로 시작
3) AC-LDRHYTHM-006: 강조 행 모멘트유형 ∈ {코러스진입, 드롭, 마지막코러스}, 인용 ≥1, 오표기 0
4) 시각 대조: 행의 시각을 t509 음악 지도(위상 1)의 마디·박 시각과 ±0.06초로 대조
5) 약점 ①②③ (리드 카드 t511) 행 번호로 보이기
6) 박자 층 이벤트 수, 기존 앱 연출(t510) 대비 표
--fill 이면 대본의 {{COUNTS}}·{{COMPARE}} 자리를 채운다.
"""

import json
import re
import sys
from pathlib import Path

SCRIPT = Path(".moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md")
MAP = Path(".moai/reports/t509/evidence/love_attack_map_phase1.json")
HEADER = ["시각", "층", "모멘트유형", "연출", "잇는 방식", "이유"]
MOMENTS = {"코러스진입", "드롭", "마지막코러스", "기타"}
ACCENT_OK = {"코러스진입", "드롭", "마지막코러스"}
KINDS = ("킥/스네어 펄스", "체이스 한 칸", "색/위치 한 단계")
MISQUOTE = "§10" + ".3"  # 문자열 그대로 두면 이 파일이 오표기 검색에 걸린다

text = SCRIPT.read_text(encoding="utf-8")
m = json.loads(MAP.read_text())
bar_t = {b["bar"]: b["start_s"] for b in m["bars"]}
per = 60.0 / m["app_path_bpm"]

lines = text.split("\n")
start = next(i for i, ln in enumerate(lines) if ln.startswith("| 시각 | 층 |"))
head = [c.strip() for c in lines[start].strip().strip("|").split("|")]
rows = []
for ln in lines[start + 2 :]:
    if not ln.startswith("|"):
        break
    rows.append([c.strip() for c in ln.strip().strip("|").split("|")])


def secs(mm: str, ss: str) -> float:
    return int(mm) * 60 + float(ss)


problems: list[str] = []
if head != HEADER:
    problems.append(f"머리글 불일치: {head}")
parsed = []  # (행번호, 시작초, 층, 모멘트, 연출, 이벤트 수, 마디 범위)
for n, r in enumerate(rows, start=1):
    if len(r) != 6:
        problems.append(f"행 {n}: 칸 수 {len(r)}")
        continue
    t, layer, moment, act = r[0], r[1], r[2], r[3]
    if layer not in {"박자", "강조"}:
        problems.append(f"행 {n}: 층 어휘 밖 {layer!r}")
    if moment not in MOMENTS:
        problems.append(f"행 {n}: 모멘트유형 어휘 밖 {moment!r}")
    if layer == "강조" and moment not in ACCENT_OK:
        problems.append(f"행 {n}: 강조가 큰 히트 밖 {moment}")
    if layer == "박자" and not act.startswith(KINDS):
        problems.append(f"행 {n}: 박자 행 범주 불명 {act[:15]}")
    # AC-003: 이유 칸이 벤치마크 §2.1·§2.3 또는 곡 조사 §3·§4 를 인용하는가
    if not re.search(r"§2\.[13]|곡 조사 §[34]", r[5]):
        problems.append(f"행 {n}: 이유 칸 인용 없음")
    times = re.findall(r"(\d):(\d\d\.\d)", t.split("(")[0])
    t0 = secs(*times[0]) if times else None
    inner = t.split("(")[1] if "(" in t else ""
    rng = re.match(r"(\d+)~(\d+)마디", inner)
    one = re.match(r"(\d+)마디 (\d)", inner)
    lst = re.match(r"([\d·]+)마디", inner)
    if rng:
        a, b = int(rng.group(1)), int(rng.group(2))
        if abs(t0 - bar_t[a]) > 0.06:
            problems.append(f"행 {n}: 시작 시각 {t0} ≠ {a}마디 {bar_t[a]:.3f}")
        if len(times) > 1:
            t1 = secs(*times[1])
            hi = bar_t.get(b + 1, bar_t[b] + 4 * per)
            if not (bar_t[b] - 0.06 <= t1 <= hi + 0.06):
                problems.append(f"행 {n}: 끝 시각 {t1} 이 {b}마디 범위 밖")
        span = (a, b)
    elif one:
        a, beat = int(one.group(1)), int(one.group(2))
        want = bar_t[a] + (beat - 1) * per
        if abs(t0 - want) > 0.06:
            problems.append(f"행 {n}: 시각 {t0} ≠ {a}마디 {beat}박 {want:.3f}")
        span = (a, a)
    elif lst and "·" in lst.group(1):
        nums = [int(x) for x in lst.group(1).split("·")]
        for (mm, ss), nb in zip(times, nums, strict=True):
            if abs(secs(mm, ss) - bar_t[nb]) > 0.06:
                problems.append(f"행 {n}: 나열 시각 {mm}:{ss} ≠ {nb}마디 {bar_t[nb]:.3f}")
        span = (nums[0], nums[-1])
    else:
        span = None  # 앞박·179초 같은 마디 밖 시각
    cnt = re.search(r"([\d+]+)회\)", t)
    events = sum(int(x) for x in cnt.group(1).split("+")) if cnt else 1
    parsed.append((n, t0, layer, moment, act, events, span))

accent = [p for p in parsed if p[2] == "강조"]
beat = [p for p in parsed if p[2] == "박자"]
total = {k: sum(p[5] for p in beat if p[4].startswith(k)) for k in KINDS}

print(f"rows {len(rows)} beat {len(beat)} accent {len(accent)}")
print("accent", [(p[0], round(p[1], 2), p[3]) for p in accent])
print("code_blocks", text.count("```"))
print("cite_10_4", text.count("§10 금지목록 4번"))
print("misquote", text.count(MISQUOTE))
print("events", total, "sum", sum(total.values()))

# 약점 ① 같은 박자 동작(펄스·체이스 범위 행)이 8마디를 넘는가
print("\n[약점 ①] 펄스·체이스 범위 행의 마디 길이(8 이하여야 함)")
for p in beat:
    if p[6] and p[4].startswith(KINDS[:2]) and p[6][1] > p[6][0]:
        length = p[6][1] - p[6][0] + 1
        flag = "OK" if length <= 8 else "OVER"
        print(f"  행 {p[0]:2d} {p[6][0]}~{p[6][1]}마디 {length}마디 {flag}")
        if length > 8:
            problems.append(f"행 {p[0]}: 같은 동작 {length}마디")

# 약점 ② 펄스 대상 — WASH 전체를 박마다 출렁이는 행이 있는가
print("\n[약점 ②] 펄스 행의 대상(첫 문장)")
for p in beat:
    if p[4].startswith("킥/스네어 펄스 —"):
        first = p[4].split(". ")[0]
        bad = re.search(r"WASH[^.]*(올리|펄스|켜고)", first)
        print(f"  행 {p[0]:2d} {first[:60]}{'  ← WASH 펄스!' if bad else ''}")
        if bad:
            problems.append(f"행 {p[0]}: WASH 펄스")

# 약점 ③ 강조 직전 박이 비어 있는가 — 같은 마디 안(4박 이내)에서 시작해 히트 직전 박을 덮는
# 멈춤·당김 행을 찾는다. 비움은 히트까지 이어지므로 시작 시각이 히트보다 1~4박 앞이면 된다.
print("\n[약점 ③] 강조 행 직전 1~4박 안에서 시작한 비움·당김(히트 바로 앞 박까지 이어짐)")
for a in accent:
    pre = [p for p in parsed if p[1] is not None and 0 < a[1] - p[1] <= 4 * per + 0.06]
    stops = [p for p in pre if ("멈춤" in p[4] or "당김" in p[4]) and p[2] == "박자"]
    print(
        f"  강조 행 {a[0]:2d} ({a[1]:.2f}s) ← "
        + ", ".join(f"행 {p[0]}({p[1]:.2f}s)" for p in stops)
    )
    if not stops:
        problems.append(f"강조 행 {a[0]}: 직전 비움 없음")

# 장면(색/위치가 바뀌는 지점) 간격 — 179초 뒤 무음은 빼고
looks = sorted(p[1] for p in parsed if p[1] is not None and p[4].startswith(KINDS[2]))
gaps = [b - a for a, b in zip(looks, looks[1:], strict=False)]
max_gap = max(gaps)
print(f"\nlook changes {len(looks)} max_gap {max_gap:.2f}s")
print("problems", len(problems))
for pr in problems:
    print("  -", pr)

counts_md = "\n".join(
    [
        "| 항목 | 수 | 무엇을 세나 |",
        "|---|---|---|",
        f"| 킥/스네어 펄스 | {total[KINDS[0]]} | 박자 층 이벤트 |",
        f"| 체이스 한 칸 | {total[KINDS[1]]} | 박자 층 이벤트 |",
        f"| 색/위치 한 단계 | {total[KINDS[2]]} | 박자 층 이벤트(장면이 바뀌는 지점 포함) |",
        f"| **박자 층 합계** | **{sum(total.values())}** | 곡당 수백 개를 허용한 감독 결정 3의 범위 안이다 |",
        f"| 강조 층 | {len(accent)} | 18마디 · 46마디 · 63마디 · 67마디 4박 |",
    ]
)
compare_md = "\n".join(
    [
        "| 항목 | 기존 앱 연출(t510, 가짜 콘솔) | 이 대본 |",
        "|---|---|---|",
        f"| 장면 수 | 큐 11개 | 색/위치가 바뀌는 지점 {len(looks)}곳 |",
        f"| 장면이 가장 오래 그대로인 시간 | 34.2초(Chorus 2), 후렴 셋이 모두 30초 넘음 | {max_gap:.1f}초 |",
        "| 장면 안의 움직임 | 없음 — 페이저 제안 9큐, 송신 0줄, 속도 줄 0 | "
        f"박자 층 이벤트 {sum(total.values())}개(펄스·체이스·한 단계), 킥 박에 맞춤 |",
        "| 강조 위치 | Chorus 3(144.3초) BLIND 80 1.1초 한 번 | "
        "18마디 BLIND 60 · 46마디 BLIND 100 · 63마디 STROBE 2박 · 67마디 4박 BLIND 100 + STROBE 1마디 |",
        "| 후렴 진입 시각 | 앱 경계 37.5 · 97.5 · 144.3초(실제 첫 박보다 0.4~0.8초 이름) | "
        "37.9 · 97.9초(감독 귀 확인 첫 박) · 144.5초(당긴 히트, 잰 값) |",
        "| 무음 179~197초 | Finale 큐, 디머 100 | 179초에 3초 페이드 → 어둠 유지 |",
    ]
)
if "--fill" in sys.argv:
    out = text.replace("{{COUNTS}}", counts_md).replace("{{COMPARE}}", compare_md)
    SCRIPT.write_text(out, encoding="utf-8")
    print("filled")
