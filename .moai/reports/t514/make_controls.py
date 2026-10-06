"""t514 — count_script.py 의 새 검사 두 개(카드 ③④)가 실제로 잡는지 보는 양성 대조 사본을 만든다.

c1_overlap.md   : 46~53마디 역광 펄스 행의 대상을 원래대로 「BACK과 MOVER-ALL을 함께」로 되돌린다
                  → 같은 마디의 엇갈린 팬 웨이브와 겹치므로 ④가 잡아야 한다
c2_kickstop.md  : 벌스 2 서클 행의 범위를 33~34마디로 옮긴다 → 킥 멈춤 33마디라 ③이 잡아야 한다

실행: uv run python .moai/reports/t514/make_controls.py
"""

from pathlib import Path

SRC = Path(".moai/specs/SPEC-LDRHYTHM-001/m1-love-attack-script.md")
OUT = Path(".moai/reports/t514/controls")
OUT.mkdir(parents=True, exist_ok=True)
text = SRC.read_text(encoding="utf-8")


def swap(old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new)


(OUT / "c1_overlap.md").write_text(
    swap(
        "(46~53마디 1·2·4박, 24회) | 박자 | 기타 | 킥/스네어 펄스 — BACK만, 킥 박에.",
        "(46~53마디 1·2·4박, 24회) | 박자 | 기타 | "
        "킥/스네어 펄스 — BACK과 MOVER-ALL을 함께, 킥 박에.",
    ),
    encoding="utf-8",
)
(OUT / "c2_kickstop.md").write_text(
    swap("| 1:14.4~1:29.4 (35~41마디) |", "| 1:10.1~1:14.4 (33~34마디) |"),
    encoding="utf-8",
)
print("controls:", sorted(p.name for p in OUT.iterdir()))
