"""마디 지도 분석의 끝 응답 라벨을 UI 리듀서가 전부 아는가 — 서버·UI 경계 계약 시험.

UI 의 「분석 중」 대기는 ``chat_response.summary`` 라벨로만 끝난다
(``ui/src/components/barMapEntryState.ts``). 서버에 끝 응답 길이 새로 생겼는데 UI 가 그
라벨을 모르면 결과가 와도 화면은 「분석 중」에 머문다 — 2026-10-20 실측(러브어택)에서
「새 분석으로 새 작업본」이 25초 만에 왔는데 300초 넘게 대기가 풀리지 않았다.

공유 스키마 생성이 없는 프로젝트라(``test_web_messages.py`` 879행) 서버 원본에서 라벨을
읽어 UI 원본과 맞춘다. 분석 한 건이 지나는 세 메서드에서 ``summary=`` 리터럴, ``say("…")``
첫 인자, 거절 라벨 상수를 모은다.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / "server" / "web" / "session.py"
REDUCER = ROOT / "ui" / "src" / "components" / "barMapEntryState.ts"

# 분석 한 건이 끝 응답을 보내는 메서드 — ``analyse_bar_map`` 과 그가 부르는 둘.
_BAR_MAP_METHODS = {"analyse_bar_map", "store_timeline_bar_map", "_start_analysis_timeline"}


def _module_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.targets[0].id] = node.value.value
    return constants


def _label(node: ast.expr, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _bar_map_summaries() -> set[str]:
    tree = ast.parse(SESSION.read_text(encoding="utf-8"))
    constants = _module_constants(tree)
    labels: set[str] = set()
    for func in ast.walk(tree):
        if not (isinstance(func, ast.FunctionDef) and func.name in _BAR_MAP_METHODS):
            continue
        for call in ast.walk(func):
            if not isinstance(call, ast.Call):
                continue
            for keyword in call.keywords:
                if keyword.arg == "summary":
                    label = _label(keyword.value, constants)
                    if label is not None:
                        labels.add(label)
            if isinstance(call.func, ast.Name) and call.func.id == "say" and call.args:
                label = _label(call.args[0], constants)
                if label is not None:
                    labels.add(label)
    return labels


def test_the_scan_finds_the_known_labels():
    # 시험 자신이 공허하지 않은지 — 알려진 끝 응답 라벨을 실제로 모으는가.
    labels = _bar_map_summaries()
    assert {
        "마디 지도 저장",
        "마디 지도 저장 거절",
        "마디 지도 저장 불가",
        "마디 지도 분석 거절",
        "새 분석으로 새 작업본",
        "새 분석 작업본 만들기 실패",
    } <= labels


def test_every_bar_map_terminal_label_is_known_to_the_ui_reducer():
    reducer = REDUCER.read_text(encoding="utf-8")
    missing = sorted(label for label in _bar_map_summaries() if f'"{label}"' not in reducer)
    assert missing == []
