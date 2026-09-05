"""M2 — 오디오 층의 경계를 기계 검사로 (AC-MUSICSYNC-010).

형제 넷(``test_paperwork_boundary.py`` · ``test_scene_boundary.py`` ·
``test_looks_boundary.py`` · ``test_fx_boundary.py``)과 **같은 형태**다. 형태를
맞추는 것은 취향이 아니라 규율이다 — 다음에 경계를 추가하는 사람이 어느 쪽을
베낄지 알아야 한다(design.md §7).

주장은 하나다: ``server/audio/**`` 는 콘솔 포트도, ``run_commands`` 도, 실행
경로도 **이름조차 부르지 않는다**. M2 의 콘솔 예산이 쓰기 0건·조회 0건이기
때문이다(spec.md §A.4).

**AST 식별자 스캔이지 raw grep 이 아니다.** ``server/audio/__init__.py`` 는 자신이
부르지 않겠다고 선언한 그 이름들을 문서화하므로, 텍스트 스캔은 불변식을 **적어
둔 문장**에 걸린다. ``test_looks_boundary.py`` 가 이미 한 AP-19 정정을 그대로
물려받는다.

콘솔 접촉: 0건. 아래 전부 정적 소스 판독이거나 메모리 안이다.
"""

from __future__ import annotations

import ast
from pathlib import Path

from server.audio.analyze import AnalysisFailure, AnalysisResult, analyze

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "server"
AUDIO_DIR = SERVER_DIR / "audio"

# 실행이 닿는 자리에만 나타나는 이름들. 형제 파일의 목록에 이 SPEC 의 축
# (콘솔 포트·조회)을 더한 집합이다.
FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "SafetyGate",
        "screen",  # 유일한 심사 경로
        "run_commands",
        "query_state",
        "execution_port",
        "state_port",
        "CommandExecutionPort",
        "ExecutionPort",
        "RigStatePort",
        "ConsoleLink",
        "OscBridge",
        "send_command",
    }
)

FORBIDDEN_MODULE_PREFIXES = (
    "server.safety.gate",
    "server.safety.console",
    "server.orchestrator.ports",
    "server.orchestrator.tools",
    "server.bridge",
    "server.looks",
    "server.lxseq",
)


def _audio_modules() -> list[Path]:
    return sorted(AUDIO_DIR.rglob("*.py"))


def _identifiers_of_source(source: str) -> list[str]:
    """실행 위치의 식별자 전부 — 속성 · 이름 · import.

    주석은 AST 노드가 아니고 독스트링은 ``ast.Constant`` 이지
    ``Attribute``/``Name``/import 이름이 아니다. 제외 로직이 필요 없다는 것이
    grep 대신 AST 를 쓰는 이유의 전부다.
    """
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            found.append(node.attr)
        elif isinstance(node, ast.Name):
            found.append(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.append(node.module)
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
    return found


def _executable_identifiers(path: Path) -> list[str]:
    return _identifiers_of_source(path.read_text(encoding="utf-8"))


def _offenders(path: Path) -> list[str]:
    hits: list[str] = []
    for identifier in _executable_identifiers(path):
        if identifier in FORBIDDEN_IDENTIFIERS:
            hits.append(f"{path.name}: {identifier}")
        if identifier.startswith(FORBIDDEN_MODULE_PREFIXES):
            hits.append(f"{path.name}: imports {identifier}")
    return hits


class TestAudioLayerTouchesNoExecutionPath:
    """AC-MUSICSYNC-010 — 식별자 스캔, 위반 0건."""

    def test_the_scan_reaches_real_code_in_every_audio_module(self):
        # 비-공허성: 아무것도 파싱하지 못한 스캔은 잘못된 이유로 통과한다.
        modules = _audio_modules()
        assert len(modules) >= 2, f"오디오 모듈을 못 찾았다: {[p.name for p in modules]}"
        count = len(_executable_identifiers(AUDIO_DIR / "analyze.py"))
        assert count > 20, f"analyze.py 가 식별자 {count}개만 냈다"

    def test_the_scan_sees_identifiers_it_should_see(self):
        # 개수가 아니라 아는 이름으로 거는 두 번째 비-공허성 대조군.
        # 함수 **정의** 이름(``analyze``)은 ``ast.Name`` 이 아니므로 잡히지
        # 않는다 — 실행 위치에 실제로 서는 이름으로 건다.
        identifiers = set(_executable_identifiers(AUDIO_DIR / "analyze.py"))
        assert "_boundaries_from_rms" in identifiers
        assert "AnalysisResult" in identifiers
        assert "librosa" in identifiers

    def test_no_audio_module_names_an_execution_path_symbol(self):
        offenders = [hit for path in _audio_modules() for hit in _offenders(path)]
        assert offenders == []

    def test_the_package_docstring_naming_the_budget_survives_the_scan(self):
        # ``server/audio/__init__.py`` 는 자기가 안 부르는 것들을 이름으로 적어
        # 불변식을 **말한다**. 이 스캔이 그 문장이 사라지는 이유가 되면 안 된다.
        init = AUDIO_DIR / "__init__.py"
        text = init.read_text(encoding="utf-8")
        assert "콘솔" in text
        assert _offenders(init) == []

    def test_the_scan_catches_an_injected_call(self):
        # 뮤테이션 대조군, 같은 프로세스 안: 실행 경로를 **부르는** 소스에
        # 같은 수집기를 걸면 반드시 잡혀야 한다. 없으면 위의 빈 결과가
        # 스캐너에 대해 아무것도 증명하지 않는다.
        identifiers = _identifiers_of_source("def go(gate, cmds):\n    return gate.screen(cmds)\n")
        assert any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)

    def test_the_scan_catches_an_injected_state_query(self):
        # 이 SPEC 이 더한 축: M2 는 **조회도 0건**이다(spec.md §A.4).
        identifiers = _identifiers_of_source(
            "def peek(port):\n    return port.query_state('DataPool/Timecodes')\n"
        )
        assert any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)

    def test_the_scan_catches_an_injected_bridge_import(self):
        identifiers = _identifiers_of_source("from server.bridge.osc import send\n")
        assert any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)

    def test_the_scan_catches_an_injected_tools_import(self):
        identifiers = _identifiers_of_source("from server.orchestrator.tools import run_commands\n")
        assert any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)

    def test_the_scan_ignores_the_same_text_inside_a_docstring(self):
        # raw grep 이 못 하는 바로 그 구별.
        prose = '"""run_commands 로 gate.screen() 을 부르지 않는다."""\nX = 1\n'
        identifiers = _identifiers_of_source(prose)
        assert not any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)

    def test_the_scan_ignores_the_same_text_inside_a_comment(self):
        prose = "# never call gate.screen() or query_state here\nX = 1\n"
        identifiers = _identifiers_of_source(prose)
        assert not any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)


class TestNoConsolePortLiteralLivesInTheAudioLayer:
    """조회 0건의 다른 얼굴 — 포트 번호조차 여기 없다.

    식별자 스캔은 ``8000`` 같은 **상수**를 못 본다. 그래서 이 한 축만 텍스트로
    본다: 숫자 리터럴은 독스트링에 적혀도 위험하지 않으므로 AST 의 상수 노드만
    보면 되고, 그러면 산문 오탐도 없다.
    """

    CONSOLE_PORTS = frozenset({8000, 9000})

    @staticmethod
    def _int_constants(path: Path) -> set[int]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
        }

    def test_no_audio_module_carries_a_console_port_literal(self):
        offenders = [
            f"{path.name}: {value}"
            for path in _audio_modules()
            for value in self._int_constants(path)
            if value in self.CONSOLE_PORTS
        ]
        assert offenders == []

    def test_the_constant_scan_is_not_vacuous(self):
        # analyze.py 는 정수 상수를 실제로 여럿 갖고 있다(hop · frame 길이 등).
        constants = self._int_constants(AUDIO_DIR / "analyze.py")
        assert len(constants) >= 3
        assert 512 in constants

    def test_the_constant_scan_would_catch_an_injected_port(self):
        tree = ast.parse("CONSOLE_PORT = 8000\n")
        values = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, int)
        }
        assert values & self.CONSOLE_PORTS


class TestTheAnalyzerRunsWithNoConsoleWired:
    """행동 쪽 절반 — 콘솔을 하나도 안 준 채로 분석이 성립한다.

    정적 스캔은 「부르지 않는다」를 보이고, 이 시험은 「부를 필요가 없다」를
    보인다. 콘솔 스텁도, 게이트도, 포트도 만들지 않는다.
    """

    def test_analysis_answers_without_any_console_object(self):
        from .fixtures.audio import synthesize_track

        outcome = analyze(synthesize_track())
        assert isinstance(outcome, AnalysisResult | AnalysisFailure)

    def test_the_failure_path_also_needs_no_console(self):
        assert isinstance(analyze(b"\x00\x01\x02"), AnalysisFailure)
