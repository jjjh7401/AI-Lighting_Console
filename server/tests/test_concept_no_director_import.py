"""제약 4 — server/concept/ 의 M5 신규 모듈은 server.director 를 import 하지
않는다(REQ-LDDESIGN-067 — 계약 경계가 다르다, mib.py 독스트링과 같은 이유로
이 계층 전체가 순수 계산이어야 한다). SPEC-LDDESIGN-001 M5, 카드 t438.

AST 기반 시험이다 — 문자열 grep 이 아니라 실제 import 문(``import``/
``from ... import``)만 판정한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

NEW_M5_MODULES = [
    "server/concept/tracking.py",
    "server/concept/timing.py",
    "server/concept/mib.py",
    "server/concept/safety.py",
    "server/concept/evidence.py",
]


def _director_imports(path: str) -> list[str]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "server.director" or alias.name.startswith("server.director."):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "server.director" or module.startswith("server.director."):
                hits.append(module)
    return hits


@pytest.mark.parametrize("path", NEW_M5_MODULES)
def test_no_server_director_import(path):
    hits = _director_imports(path)
    assert hits == [], f"{path}: server.director import 발견 — {hits}"
