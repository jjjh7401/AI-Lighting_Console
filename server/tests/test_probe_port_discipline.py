"""t61 — 콘솔에 쏘는 도구는 `--listen-port` 에 기본값을 두지 않는다.

왜 검사가 필요한가. 이 규율은 **새 도구가 늘 때마다** 깨진다. t61 이 전수를
떴을 때 17개 중 9005 기본값 셋 · 9000 기본값 셋 · argparse 를 아예 안 쓰고
손으로 훑으면서 침묵 기본값을 쓰는 것 다섯이었고, 그 다섯은 **전날 밤에 새로
만들어진 것**이었다. 사람이 지키는 규율은 도구가 늘면 진다.

검사가 **도구 목록을 하드코딩하지 않는 것**이 요점이다. 목록을 적으면 다음
도구가 목록 밖에서 태어나 조용히 고아가 된다(t51 이 세운 형태).

그리고 스캐너는 **argparse 만 보면 안 된다.** 실제로 있었던 형태가
`listen = 9005` + `sys.argv` 손수 훑기였다. argparse 만 훑는 검사였으면 그
다섯을 그대로 놓쳤다 — 검사 자신이 공허했을 것이다.
"""

from __future__ import annotations

import re
from pathlib import Path

TOOLS_DIR = Path("server/tools")

#: 콘솔에 실제로 쏘는 도구를 가려내는 표지. 이 중 하나라도 임포트하면 대상이다.
_CONSOLE_MARKERS = ("build_console_stack", "BridgeConfig")

#: 형태 ①: argparse 선언에 default 가 붙은 것.
_ARGPARSE_DEFAULT = re.compile(r'add_argument\(\s*\n?\s*"--listen-port"[^)]*?\bdefault\s*=', re.S)

#: 형태 ②: argparse 를 안 쓰고 변수에 포트를 박아 두는 것.
#: `listen = 9005` / `listen_port = 9000` / `port = 9005` 를 잡는다.
_BARE_ASSIGNMENT = re.compile(r"^\s*(?:listen|listen_port|reply_port)\s*=\s*\d{4,5}\s*$", re.M)


def find_default_port_declarations(source: str) -> list[str]:
    """이 소스가 응답 포트에 **기본값**을 두는 자리들. 없으면 빈 목록.

    두 형태를 모두 본다 — argparse 의 `default=` 와, argparse 를 우회한 변수
    대입. 둘째가 없으면 이 검사는 t61 이 실제로 잡은 다섯 건을 못 잡는다.
    """
    hits: list[str] = []
    for match in _ARGPARSE_DEFAULT.finditer(source):
        hits.append("argparse default: " + match.group(0).strip()[:60])
    for match in _BARE_ASSIGNMENT.finditer(source):
        hits.append("bare assignment: " + match.group(0).strip())
    return hits


def _console_tools() -> list[Path]:
    found = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in _CONSOLE_MARKERS):
            found.append(path)
    return found


class TestScannerIsNotVacuous:
    """날조 대조군 — 스캐너가 두 형태를 **실제로** 잡는지 먼저 잰다.

    이것이 없으면 아래 전수 검사는 「아무것도 안 잡는 스캐너가 아무것도 못
    찾았다」와 구분되지 않는다.
    """

    def test_it_catches_an_argparse_default(self):
        fabricated = """
        parser.add_argument("--listen-port", type=int, default=9005)
        """
        assert find_default_port_declarations(fabricated), "argparse 기본값을 못 잡는다"

    def test_it_catches_a_multiline_argparse_default(self):
        fabricated = """
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9000,
        help="local reply port",
    )
"""
        assert find_default_port_declarations(fabricated), "여러 줄 argparse 기본값을 못 잡는다"

    def test_it_catches_a_hand_rolled_default(self):
        """t61 이 실제로 잡은 형태 — argparse 를 안 쓴다."""
        fabricated = """
def main():
    listen = 9005
    for index, token in enumerate(args):
        if token == "--listen-port":
            listen = int(args[index + 1])
"""
        assert find_default_port_declarations(fabricated), "손수 파싱 기본값을 못 잡는다"

    def test_it_passes_a_clean_declaration(self):
        """반대편 — 올바른 형태는 통과해야 한다. 이게 없으면 스캐너가
        「무엇이든 잡는」 것과 구분되지 않는다."""
        clean = """
    add_listen_port_argument(parser)
    listen = known.listen_port
"""
        assert find_default_port_declarations(clean) == []


class TestEveryConsoleToolStatesItsPort:
    def test_the_scan_found_tools_at_all(self):
        """비공허 — 대상이 0개면 아래 검사가 자동으로 참이 된다."""
        tools = _console_tools()
        assert len(tools) >= 10, f"콘솔 접촉 도구를 {len(tools)}개만 찾았다 — 표지가 낡았다"

    def test_no_console_tool_defaults_its_listen_port(self):
        offenders: dict[str, list[str]] = {}
        for path in _console_tools():
            hits = find_default_port_declarations(path.read_text(encoding="utf-8"))
            if hits:
                offenders[path.as_posix()] = hits
        assert offenders == {}, (
            "응답 포트에 기본값을 둔 도구가 있다. 틀린 포트로 쏘면 침묵이 "
            "돌아오는데 그 침묵은 「응답기가 죽었다」와 구분되지 않는다 — "
            "`add_listen_port_argument(parser)` 를 써라: " + repr(offenders)
        )

    def test_they_all_use_the_single_shared_declaration(self):
        """선언이 도구마다 흩어지면 기본값이 다시 갈린다 — t61 이 그렇게 났다.

        이름의 **등장**이 아니라 **호출**을 잰다. 처음 이 검사는 파일 어디든
        `add_listen_port_argument` 라는 글자가 있으면 통과했는데, 임포트 줄만
        남기고 선언을 손수 파싱으로 되돌린 뮤테이션이 **안 걸렸다** — 임포트가
        검사를 만족시켰다. 찾는 도구와 판정하는 도구가 달랐던 것이다.
        """
        missing = [
            path.as_posix()
            for path in _console_tools()
            if "add_listen_port_argument(parser)" not in path.read_text(encoding="utf-8")
        ]
        assert missing == [], f"공용 선언을 **부르지** 않는 도구: {missing}"
