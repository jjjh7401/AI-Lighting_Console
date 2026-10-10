"""응답기 1.6.6 을 콘솔 편집기에 붙여넣을 수 있게 ASCII 전용 사본으로 만든다 (카드 t531).

onPC 플러그인 편집기는 붙여넣은 글에서 처음 나오는 비ASCII 글자(19줄 끝 「—」)
에서 붙여넣기를 멈췄다(2026-10-10 감독 화면, 20줄까지만 들어감). 비ASCII 는 전부
주석 안에만 있으므로(실측: 주석 밖 0줄) 주석 글자만 바꾼다. 줄 수는 그대로 둔다.
원본 `console/lua/copilot_responder.lua` 는 바꾸지 않는다.

실행: uv run python .moai/reports/t531/make_ascii_responder.py
"""

import re
from pathlib import Path

SRC = Path("console/lua/copilot_responder.lua")
OUT = Path(".moai/reports/t531/copilot_responder_1.6.6_ascii.lua")
SIMPLE = {"—": "-", "–": "-", "§": "S", "·": "*", "→": "->", "←": "<-"}

text = SRC.read_text(encoding="utf-8")
for line_no, line in enumerate(text.splitlines(), 1):
    if re.search(r"[^\x00-\x7F]", line):
        code = line.split("--", 1)[0]
        if re.search(r"[^\x00-\x7F]", code):
            raise SystemExit(f"주석 밖 비ASCII: {SRC}:{line_no}")
for k, v in SIMPLE.items():
    text = text.replace(k, v)
text = re.sub(r"[^\x00-\x7F]+", "?", text)
OUT.write_text(text, encoding="ascii")
print(OUT, len(text.splitlines()), "lines")
