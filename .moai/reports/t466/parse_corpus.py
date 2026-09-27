"""t461 — 기존 문장 회귀 기준선. server/tests/*.py 의 한국어 문자열 상수 전부를
parse_cue_sheet_edit_request 에 넣어(cue_selected 참·거짓 둘 다) 결과를 JSON 으로
남긴다. 수정 전(base)과 수정 후를 같은 스크립트로 떠서 바이트 대조한다.

실행: .venv/bin/python .moai/reports/t461/parse_corpus.py <출력 json>
"""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

from server.design.cue_sheet_edit import parse_cue_sheet_edit_request  # noqa: E402

_HANGUL = re.compile(r"[가-힣]")

sentences: set[str] = set()
for path in sorted(Path("server/tests").glob("*.py")):
    tree = ast.parse(path.read_text("utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            if _HANGUL.search(text) and len(text) <= 200:
                sentences.add(text)

result = {
    text: [
        parse_cue_sheet_edit_request(text, cue_selected=False),
        parse_cue_sheet_edit_request(text, cue_selected=True),
    ]
    for text in sorted(sentences)
}
Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=0, sort_keys=True))
parsed = sum(1 for pair in result.values() if pair[0] is not None or pair[1] is not None)
print(f"sentences={len(result)} parsed_any={parsed}")
