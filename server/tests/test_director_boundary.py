"""경계 시험 (SPEC-LDSTORE-001).

``server/director`` 는 교환·저장 층이다: 계약대로 파싱하고 불변으로 보관하고
context 를 발급한다. **콘솔을 만지지 않고 예술 판단을 하지 않는다.** 형제 경계
시험(``test_paperwork_boundary.py``, ``test_audio_boundary.py``)과 같은 임포트
스윕 규율을 이 패키지에도 건다.

왜 기계로 고정하는가: 이 층은 앞으로 `LDCOMPILE`·`LDRECV` 형제가 위에 얹힐 자리다.
"판단은 외부 Director 가 한다"는 결정이 문서에만 있으면, 편한 지점에서 기존
producer 를 부르는 코드가 슬며시 들어온다. 그것이 계약 §1 이 막으려는
**두 번째 예술 policy producer** 다.
"""

from __future__ import annotations

import ast
from pathlib import Path

DIRECTOR_DIR = Path(__file__).resolve().parents[1] / "director"

#: 송신 표면 — 서버 전체에서 `server/bridge/osc.py` 하나뿐이고, 이 층은 그 이름조차
#: 부르지 않는다.
_FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc", "pythonosc.udp_client")

#: 기존 예술 판정 생산자 둘 (인계 문서 §3.7). 이 층에서 호출하면 계약이 금지한
#: 두 번째 policy producer 가 된다.
_FORBIDDEN_ARTISTIC_NAMES = (
    "map_sections_to_looks",
    "_ARC_",
    "songcue",
    "resolve_section",
)

#: 실행 포트 이름 — 형제 경계 시험과 같은 목록.
_FORBIDDEN_EXECUTION_NAMES = ("CommandExecutionPort", "BundleGate")


def _python_files() -> list[Path]:
    return sorted(DIRECTOR_DIR.rglob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class TestPositiveControlSweepActuallySeesFiles:
    """계기가 헛돌지 않는지 — 매치 0 이 "깨끗함"인지 "안 훑었음"인지 갈라야 한다."""

    def test_sweep_finds_python_files(self):
        assert _python_files(), "server/director 에서 .py 를 하나도 못 찾았다 — 스윕이 헛돈다"

    def test_sweep_can_parse_and_see_imports(self):
        """적어도 한 파일에서 임포트를 실제로 읽어내는지."""
        seen = set()
        for path in _python_files():
            seen |= _imported_modules(path)
        assert seen, "임포트를 하나도 못 읽었다 — AST 스윕이 헛돈다"


class TestDirectorNeverTouchesTheConsole:
    def test_no_module_imports_the_osc_send_surface(self):
        offenders = []
        for path in _python_files():
            for module in _imported_modules(path):
                if any(module.startswith(prefix) for prefix in _FORBIDDEN_MODULE_PREFIXES):
                    offenders.append((path.name, module))
        assert offenders == []

    def test_no_module_names_an_execution_port(self):
        offenders = []
        for path in _python_files():
            text = path.read_text(encoding="utf-8")
            for name in _FORBIDDEN_EXECUTION_NAMES:
                if name in text:
                    offenders.append((path.name, name))
        assert offenders == []


class TestDirectorNeverCallsTheArtisticProducers:
    def test_no_module_references_an_artistic_producer(self):
        """독스트링의 설명 언급은 허용하되 코드에서의 참조는 막는다.

        문자열·주석에 이름이 나오는 것과 실제로 부르는 것은 다르다. AST 에서
        임포트와 속성 접근만 본다 — 그래서 이 패키지의 ``__init__`` 이 "우리는
        ``_ARC_*`` 를 호출하지 않는다"고 **설명하는** 것은 위반이 아니다.
        """
        offenders = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and any(
                    node.id.startswith(name) or name in node.id
                    for name in _FORBIDDEN_ARTISTIC_NAMES
                ):
                    offenders.append((path.name, node.id))
                elif isinstance(node, ast.Attribute) and any(
                    name in node.attr for name in _FORBIDDEN_ARTISTIC_NAMES
                ):
                    offenders.append((path.name, node.attr))
            for module in _imported_modules(path):
                if "looks" in module or "design" in module:
                    offenders.append((path.name, module))
        assert offenders == []
