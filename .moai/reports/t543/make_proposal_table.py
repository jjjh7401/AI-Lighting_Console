"""t543 — 프리셋 번호 **제안표**(AI 초안 → 감독 승인). 오프라인(콘솔 안 씀).

리드 지시 2026-10-10: 31→33큐 × 4칸에 번호 + 근거(§4 원문 줄 · 풀 후보 · 실측 경로).
근거가 없는 칸은 비운다. 제안 번호는 yaml 에 넣지 않는다(감독 승인 전 미정).

근거 등급:
  [실측]  — 감독이 눈으로 본 기록이 있다(경로 표기). 단 잰 그룹·기종 밖이면 그렇게 적는다.
  [이름]  — 풀 목록의 이름만 §4 원문과 맞는다. 프리셋 이름은 증거가 아니다.

실행 (R=.moai/reports/t543):
    .venv/bin/python $R/make_proposal_table.py > $R/proposal-table.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid  # noqa: E402

HERE = Path(__file__).parent
RULES = "reports/effect-arrangement-rules-20261007.md"
T538 = ".moai/specs/SPEC-LDBEAT-001/progress.md:130"  # 쇼 효과 프리셋 실측 행
T538_POS = ".moai/specs/SPEC-LDBEAT-001/progress.md:131"  # 위치 프리셋 큐 실측 행
T538_SOLVE = ".moai/specs/SPEC-LDBEAT-001/progress.md:123"  # 2단계 해법 행

# (그룹, 마디) → {칸: (번호, 근거)}. 칸: dim(밝기 프리셋) · pos · color · fx
PROPOSALS: dict[tuple[str, int], dict[str, tuple[str, str]]] = {
    ("FOH", 7): {
        "dim": ("1.1", "[이름] 「풀」 · 규칙 7 「얼굴은 밝게」(" + RULES + ":27)"),
    },
    ("BACK", 3): {
        "fx": ("21.1", "[이름] 「DIM-PULSE」 ↔ §4 「마디 4박마다」"),
    },
    ("BACK", 7): {
        "fx": (
            "21.1",
            "[이름] 「DIM-PULSE」 ↔ §4 「킥 1·2·4박」 — "
            "박 패턴(1·2·4)은 프리셋 안을 못 읽어 미확인",
        ),
    },
    ("BACK", 18): {
        "fx": ("21.1", "[이름] 같은 펄스 · §4 「킥 1·2·4박 100%」"),
    },
    ("BACK", 22): {
        "fx": ("21.1", "[이름] 같은 펄스 · §4 「킥 1·2·4박 100%」"),
    },
    ("SIDE-ALL", 11): {
        "fx": ("21.3", "[이름] 「DIM-CHASE」 ↔ §4 「SIDE-L/R 2·4박 번갈이」"),
    },
    ("SIDE-ALL", 14): {
        "fx": (
            "21.3",
            "[이름] 같은 체이스 · 「가속(마디마다 두 배)」은 속도 변화라 프리셋만으로 안 됨",
        ),
    },
    ("MOVER-U", 14): {
        "fx": (
            "21.5",
            f"[실측] Group 11 에서 「위아래로 쓸기」({T538}, A6b 319) · 가속은 속도로 따로",
        ),
    },
    ("MOVER-U", 18): {
        "pos": (
            "2.1",
            f"[실측] Group 11 에서 「조금 무대 앞, 틸트업」({T538_POS}, B1 320) ↔ 「위로 열고」",
        ),
    },
    ("MOVER-D", 14): {
        "fx": ("21.5", f"[실측·다른 그룹] Group 11 에서만 잼({T538}) — Group 12(Spiider) 미측정"),
    },
    ("MOVER-D", 18): {
        "pos": ("2.1", f"[실측·다른 그룹] Group 11 에서만 잼({T538_POS}) — Group 12 미측정"),
    },
    ("BLIND", 17): {
        "dim": ("1.6", "[이름] 「아웃」 ↔ §4 「3·4박 전부 비움」"),
    },
}

# 근거가 없어 비운 칸 중 이유를 적어 둘 것(번호 없음).
NOTES: dict[tuple[str, int], str] = {
    ("WASH-ALL", 7): "색 「라벤더」 — 색 풀에 라벤더 이름 프리셋 없음, 색 값은 못 읽음(r5) → 비움",
    ("MOVER-U", 0): "「바닥 쪽 좁은 빔」 — 바닥을 가리킨다고 잰 위치 프리셋 없음 → 비움",
    ("MOVER-U", 11): f"「느린 팬 흔들기」 — 맞는 프리셋 없음(21.2 는 원도 아닌 다른 모양, {T538}). "
    f"t538 2단계 상대 페이저로 직접 만드는 길({T538_SOLVE})",
    ("MOVER-U", 18): "19마디 팬 웨이브(한 바퀴 2박)는 맞는 효과 프리셋 없음 — 2단계 상대 페이저로",
    (
        "MOVER-D",
        7,
    ): "「틸트 웨이브, 위상 펼침」 — 21.5 는 쓸기로 잼, 웨이브·위상 펼침은 미측정 → 비움",
    ("MOVER-D", 22): "「틸트 웨이브(한 바퀴 2박)」 — 위와 같음 → 비움",
}

COLS = ("dim", "pos", "color", "fx")


def main():
    grid = default_beat_grid(LOVE_ATTACK_TITLE)
    keys = {(t["group_name"], c["bar"]) for t in grid["tracks"] for c in t["cues"]}
    unknown = (set(PROPOSALS) | set(NOTES)) - keys
    if unknown:
        raise SystemExit(f"격자에 없는 자리: {sorted(unknown)}")
    pools = json.loads((HERE / "r1_pools.json").read_text())["presets"]
    names = {f"{no}.{c['i']}": c["name"] for no, v in pools.items() for c in v["children"]}
    for proposal in PROPOSALS.values():
        for number, _ in proposal.values():
            if number not in names:
                raise SystemExit(f"풀에 없는 번호: {number}")

    lines = [
        "# LOVE ATTACK 0~25마디 — 프리셋 번호 제안표 (AI 초안, 감독 승인 전 미정)",
        "",
        "> ⚠️ **프리셋 이름은 증거가 아니다.** t538 에서 `21.2 PT-CIRCLE` 은 원이 아니었고",
        "> `2.1` 「보컬 센터」는 실제로 「조금 무대 앞, 틸트업」을 가리켰다. 색 프리셋의 실제 색",
        "> 값은 응답기가 읽지 못한다(t543 `r5_color_values.json`). **[이름]** 표시 칸은 이름만",
        "> 맞춘 후보이고, **[실측]** 칸만 감독이 눈으로 본 기록이 있다.",
        "",
        "- 이 표의 번호는 `love_attack.yaml` 에 **넣지 않았다**. "
        "감독 승인 뒤 정해진 번호만 넣는다.",
        "- 근거가 없는 칸은 비워 뒀다. 밝기는 §4 에 % 가 있으면 그 값(단일모드)이라 "
        "프리셋을 제안하지 않았다.",
        "- 풀 목록 전체는 `fill-in-table.md`, 콘솔 원자료는 `r1_pools.json`. "
        f"§4 원문은 `{RULES}:104-110`.",
        "",
        "| # | 마디 | 트랙 | §4 원문 | 지금 값 | 밝기 프리셋 | 위치 | 색 | 효과 | 근거 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    n = filled = 0
    for track in grid["tracks"]:
        for cue in track["cues"]:
            n += 1
            key = (track["group_name"], cue["bar"])
            proposal = PROPOSALS.get(key, {})
            b = cue["brightness"]
            now = f"{b['value_percent']}%" if b["value_percent"] is not None else ""
            if cue["entry"]["fade_bars"] is not None:
                now += f" · {cue['entry']['fade_bars']}마디 번짐"
            cells = []
            for col in COLS:
                if col in proposal:
                    number = proposal[col][0]
                    cells.append(f"`{number}` {names[number]}")
                    filled += 1
                else:
                    cells.append("")
            why = [f"{col}: {proposal[col][1]}" for col in COLS if col in proposal]
            if key in NOTES:
                why.append(NOTES[key])
            src = cue["source_ref"] or ""
            if src:
                why.append(f"§4 `{src.rsplit('/', 1)[-1]}`")
            lines.append(
                f"| {n} | {cue['bar']} | {track['group_name']} (G{track['group_no']}) | "
                f"{cue['label']} | {now} | " + " | ".join(cells) + f" | {' · '.join(why)} |"
            )
    measured = sum(1 for p in PROPOSALS.values() for v in p.values() if v[1].startswith("[실측]"))
    other = sum(1 for p in PROPOSALS.values() for v in p.values() if v[1].startswith("[실측·"))
    lines += [
        "",
        f"큐 {n}개 · 제안한 칸 {filled}개(실측 {measured} · 다른 그룹에서 잰 실측 {other} · "
        f"나머지는 이름 후보) · "
        f"나머지 {n * len(COLS) - filled}칸은 비움.",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
