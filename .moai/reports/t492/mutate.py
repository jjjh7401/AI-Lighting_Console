"""t492 가드 변이 — 새 단언이 각 결함을 잡는지 본다(t485 mutate.py 와 같은 모양).

실행: 워크트리 루트에서 ``uv run python .moai/reports/t492/mutate.py``.
파일은 매 회차 끝에 원본 바이트로 되돌린다(finally).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TABS = "ui/src/components/conceptTabs.ts"
GLANCE = "ui/src/components/conceptGlance.ts"
UI_TEST = ["npx", "vitest", "run", "src/components/conceptTabs.test.ts"]

MUTANTS = [
    (
        "U1 저장된 큐에도 생성기를 가리킴",
        TABS,
        'if (status === "stored" || status === "verified") {',
        "if (false) {",
    ),
    (
        "U2 해제 위치를 released_q(행 번호)로 읽음",
        TABS,
        "const section = sections[item.screen_position];",
        "const section = sections[item.released_q] ?? sections[item.screen_position];",
    ),
    (
        "U3 움직임=포지션이어도 따로 셈(공간 반복)",
        TABS,
        "if (!differs && sections.some((section) => section.movement?.trim())) {",
        "if (false) {",
    ),
    (
        "U4 4칸이 바꾸려면 문장을 무시",
        GLANCE,
        "text: changeGuide ?? `${NO_DATA} — 변경 안내 원천이 서버에 없다`",
        "text: `${NO_DATA} — 변경 안내 원천이 서버에 없다`",
    ),
    (
        "U5 해제 못 찾음에 이유를 지어냄",
        TABS,
        'release = "미해제 — 해제 큐를 찾지 못했다";',
        'release = "미해제 — 이 곡에서 한 번도 쓰이지 않는다";',
    ),
    (
        "U6 시작–끝이 빈 값 경계도 바뀜으로 셈",
        TABS,
        "if (!before || !now) continue;",
        "",
    ),
]


def main() -> None:
    caught = 0
    for name, rel, old, new in MUTANTS:
        path = ROOT / rel
        original = path.read_bytes()
        text = original.decode("utf-8")
        assert text.count(old) == 1, f"{name}: 변이 지점이 정확히 1곳이 아니다"
        try:
            path.write_text(text.replace(old, new), encoding="utf-8")
            result = subprocess.run(UI_TEST, cwd=ROOT / "ui", capture_output=True, text=True)
            lines = [line.strip() for line in result.stdout.splitlines()]
            failed = [line for line in lines if line.startswith("×")]
            status = "CAUGHT" if result.returncode != 0 else "SURVIVED"
            caught += status == "CAUGHT"
            print(f"{status} {name}")
            for line in failed[:4]:
                print(f"    {line}")
        finally:
            path.write_bytes(original)
    print(f"{caught}/{len(MUTANTS)} CAUGHT")


if __name__ == "__main__":
    main()
