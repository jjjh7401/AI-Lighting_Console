"""t448 실측 — 두 조립 경로의 기능 흔적·시험 결합도·생산 호출처.

실행: uv run python .moai/reports/t448/measure.py
"""

import re
from pathlib import Path

ROOT = Path(".")
FILES = ("server/looks/songcue.py", "server/design/song_cue_composer.py")
WORDS = (
    "climax", "accent", "darkness", "return", "ladder", "yield", "front_fill", "mib", "premove",
)  # fmt: skip
TEST_FN = re.compile(r"^(?:    )?def test_", re.MULTILINE)

for name in FILES:
    text = (ROOT / name).read_text(encoding="utf-8")
    folded = text.lower()
    counts = " ".join(f"{w}={folded.count(w)}" for w in WORDS)
    print(f"{name}: {text.count(chr(10))} lines · {counts}")


def callers(symbol: str, root: str) -> list[tuple[str, int, int]]:
    rows = []
    for path in sorted((ROOT / root).rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        calls = text.count(f"{symbol}(")
        if calls and f"def {symbol}(" not in text:
            rows.append((str(path), calls, len(TEST_FN.findall(text))))
    return rows


for symbol in ("build_songcue_bundle", "compose_song_cue_bundle"):
    tests = callers(symbol, "server/tests")
    prod = [row for row in callers(symbol, "server") if "/tests/" not in row[0]]
    print(f"\n== {symbol}")
    n_calls = sum(r[1] for r in tests)
    n_fns = sum(r[2] for r in tests)
    print(f"  시험 파일 {len(tests)}개 · 호출 {n_calls}곳 · 그 파일들의 시험 함수 {n_fns}개")
    for path, calls, fns in tests:
        uses_entry = "prepare_songcue" in (ROOT / path).read_text(encoding="utf-8")
        tail = " · prepare_songcue 도 씀" if uses_entry else ""
        print(f"    {path}: 호출 {calls} · 시험 {fns}{tail}")
    print(f"  생산 호출처: {[p for p, _, _ in prod]}")
