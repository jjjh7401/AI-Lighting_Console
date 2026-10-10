"""t543 ③ — 감독이 손으로 프리셋 번호를 고르는 기입표를 만든다. 오프라인(콘솔 안 씀).

입력: 앱 로더가 실제로 돌려주는 LOVE ATTACK 기본 격자(default_beat_grid) +
      r1_pools.json(콘솔 프리셋 풀 읽기 전용 목록).
레인은 번호를 고르지 않는다 — 기입 칸은 전부 빈칸이고, 후보는 풀 목록 전체다.

실행: .venv/bin/python .moai/reports/t543/make_fill_table.py > .moai/reports/t543/fill-in-table.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid  # noqa: E402

HERE = Path(__file__).parent
POOLS = {
    "1": "디머 프리셋 (풀 1 Dimmer)",
    "2": "위치 프리셋 (풀 2 Position)",
    "4": "색 프리셋 (풀 4 Color)",
    "21": "효과·혼합 프리셋 (풀 21 All 1)",
    "22": "효과·혼합 프리셋 (풀 22 All 2)",
}


def pool_lines(presets):
    out = []
    for no, title in POOLS.items():
        items = presets[no]["children"]
        listed = " · ".join(f"`{no}.{c['i']}` {c['name']}" for c in items)
        out.append(f"- **{title}** — {len(items)}개: {listed}")
    empty = [k for k, v in presets.items() if not v["children"]]
    out.append(
        f"- 비어 있는 풀: {', '.join(empty)} (Gobo·Beam·Focus·Control·Shapers·Video·All 3~5)"
    )
    return out


def cell(value):
    return "" if value is None else str(value)


def main():
    pools = json.loads((HERE / "r1_pools.json").read_text())
    grid = default_beat_grid(LOVE_ATTACK_TITLE)
    lines = [
        "# LOVE ATTACK 0~25마디 — 프리셋 번호 기입표 (카드 t543 ③)",
        "",
        "감독이 손으로 고르는 표다. **레인은 번호를 고르지 않았다** — 기입 칸은 전부 비어 있다.",
        "번호는 아래 「풀 목록」(콘솔 읽기 전용 실측, `r1_pools.json`, 응답기 1.6.6)에서 고른다.",
        "§4 에 숫자가 있던 밝기 값(%)만 「지금 값」에 채워져 있다(REQ-LDBEAT-015(f)).",
        "",
        "## 풀 목록 (후보 — 콘솔에서 읽은 그대로)",
        "",
        *pool_lines(pools["presets"]),
        "",
        "> 프리셋 이름은 실제 모양·색의 증거가 아니다 — t538 에서 `21.2 PT-CIRCLE` 은 원이",
        "> 아니었고 `2.1` 은 이름과 다른 곳을 가리켰다. 색 프리셋의 실제 색 값은 응답기가",
        "> 읽지 못한다(t543 `r5_color_values.json`, 4.1·4.2 실측). 이름은 고를 때 참고만 한다.",
        "",
        "## 큐별 기입 칸",
        "",
        "| # | 마디 | 트랙 (그룹) | §4 원문 | 지금 값 "
        "| 밝기: % 또는 디머/디머효과 프리셋 | 위치 프리셋 | 색 프리셋 | 효과 프리셋 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    n = 0
    for track in grid["tracks"]:
        for cue in track["cues"]:
            n += 1
            b = cue["brightness"]
            now = f"{b['value_percent']}%" if b["value_percent"] is not None else ""
            fade = cue["entry"]["fade_bars"]
            if fade is not None:
                now += f" · {fade}마디 번짐"
            group = f"{track['group_name']} (G{cell(track['group_no']) or '?'})"
            lines.append(
                f"| {n} | {cue['bar']} | {group} | {cue['label']} | {now} | "
                f"{cell(b['preset_no'])} | {cell(cue['position_preset_no'])} | "
                f"{cell(cue['color_preset_no'])} | {cell(cue['effect_preset_no'])} |"
            )
    empty_tracks = [t["group_name"] for t in grid["tracks"] if not t["cues"]]
    lines += [
        "",
        f"큐 {n}개. 큐가 없는 트랙: {', '.join(empty_tracks)}.",
        "",
        "## 트랙에 못 얹은 SCENE 칸 (메모 — 어느 그룹에 둘지부터 정할 것)",
        "",
        "| 마디 | §4 원문 | 왜 메모인가 |",
        "|---|---|---|",
    ]
    why = {
        0: "BACK 을 부르지만 그 마디에 BACK 큐(앞박 1회)가 이미 있다",
        7: "「워시」는 WASH-ALL 을 글자로 부르지 않는다 "
        "(같은 칸의 「FOH 켬」은 FOH 트랙 #1 로 옮김)",
        11: "그룹을 부르지 않는다",
        14: "그룹을 부르지 않는다 (기존 판정 그대로 — 「워시」를 그룹 지칭으로 보지 않았다)",
        18: "그룹을 부르지 않는다",
        22: "그룹을 부르지 않는다",
    }
    for memo in grid["scene_memos"]:
        lines.append(f"| {memo['bar']} | {memo['text']} | {why.get(memo['bar'], '')} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
