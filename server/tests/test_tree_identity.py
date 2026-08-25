"""트리 동일성 가드 — 빌린 인터프리터로 도구를 돌리면 죽는가 (SPEC-COPILOT-TREEID-001).

이 저장소의 콘솔 실측 증거는 `server/tools/` 의 도구가 생산한다. 그 도구를 다른
워크트리의 인터프리터로 **스크립트 경로**로 부르면 `sys.path[0]` 이 `server/tools/` 라
자기 트리 루트를 담지 않고, venv 의 editable `.pth` 가 이겨서 남의 트리 `server` 가
경고 0줄로 임포트된다. 증거의 출처가 조용히 바뀐다.

## 어떻게 「남의 트리」를 만드는가

CI 러너에는 워크트리가 하나뿐이라 두 번째 venv 를 쓸 수 없다. 대신 `server/` 를
임시 디렉터리로 **복사**하고 `PYTHONPATH` 로 얹는다 — PYTHONPATH 가 editable `.pth`
보다 앞서므로 「스크립트는 A 트리, server 는 B 트리」라는 그 상황이 그대로 재현된다.

**복사여야 한다.** 심볼릭 링크로 만들면 `Path.resolve()` 가 링크를 되짚어 두 트리가
같아지고 가드가 통과해 버린다.

## 종료 코드가 3 인 이유

argparse 는 인자 오류에 **exit 2** 를 쓴다(이 저장소 도구에서 실측). 가드가 2 를 쓰면
「가드가 죽였다」와 「인자가 틀렸다」를 검사가 구별하지 못한다. 그래서 3 이다.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent

# 검사 대상 도구 — 명시 지명. glob 으로 고르지 않는다: 찾는 도구가 판정까지 하면
# 패턴에 안 걸리는 도구가 조용히 빠진다. 전수 적용 여부는 완전성 검사가 따로 본다.
TOOL = "server/tools/osc_smoke.py"

# 가드 전용 종료 코드. 1(일반 실패)·2(argparse)와 겹치지 않아야 한다.
GUARD_EXIT = 3

# 가드 메시지가 반드시 담아야 하는 조각.
MESSAGE_MARK = "트리 동일성"
FIX_MARK = "-m server.tools."


@pytest.fixture(scope="session")
def foreign_tree(tmp_path_factory) -> Path:
    """남의 워크트리를 합성한다 — 복사본이라야 resolve() 가 되짚지 못한다."""
    root = tmp_path_factory.mktemp("foreign_tree")
    shutil.copytree(
        SERVER_DIR,
        root / "server",
        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
    )
    return root.resolve()


def _run(args: list[str], foreign: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    if foreign is not None:
        env["PYTHONPATH"] = str(foreign)
    return subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestTreeIdentityGuard:
    def test_borrowed_tree_kills_the_tool(self, foreign_tree: Path) -> None:
        """양성: server 가 남의 트리에서 오면 죽는다."""
        proc = _run([TOOL, "--help"], foreign=foreign_tree)

        assert proc.returncode == GUARD_EXIT, (
            "빌린 트리로 실행했는데 가드가 죽이지 않았다 — "
            f"exit={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
        # 두 경로가 모두 찍혀야 사람이 무엇과 무엇이 어긋났는지 안다.
        assert str(PROJECT_ROOT) in proc.stderr, proc.stderr
        assert str(foreign_tree) in proc.stderr, proc.stderr
        # 계기 확인: 정말 남의 트리가 임포트됐는가. 이 단언이 없으면 검사가 공허해진다.
        assert str(foreign_tree) != str(PROJECT_ROOT)

    def test_message_names_the_fix(self, foreign_tree: Path) -> None:
        """죽이기만 하고 고칠 길을 안 알려주면 사람이 막힌다."""
        proc = _run([TOOL, "--help"], foreign=foreign_tree)
        assert MESSAGE_MARK in proc.stderr, proc.stderr
        assert FIX_MARK in proc.stderr, proc.stderr

    def test_own_tree_runs_normally(self) -> None:
        """음성 대조군: 자기 트리에서는 죽지 않는다. 항상 죽는 가드는 고장이다."""
        proc = _run([TOOL, "--help"])

        assert proc.returncode == 0, (
            f"자기 트리인데 가드가 죽였다 — exit={proc.returncode}\nstderr={proc.stderr}"
        )
        assert MESSAGE_MARK not in proc.stderr, proc.stderr


class TestGuardCoverage:
    """노출면 전수에 가드가 붙어 있는가.

    손으로 관리하는 목록을 쓰지 않는다 — 목록은 새 도구가 생기면 조용히 뒤처지고,
    뒤처진 목록은 통과하는 검사가 된다. 대신 `server/tools/` 를 훑어
    「server 를 임포트하는데 가드를 안 부르는 파일」을 0으로 단언한다.
    """

    # 가드 자신. 자기를 자기가 부를 수 없다.
    EXEMPT = ("__init__.py", "tree_identity.py")

    def _tools_importing_server(self) -> list[Path]:
        found = []
        for path in sorted((SERVER_DIR / "tools").glob("*.py")):
            if path.name in self.EXEMPT:
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"^\s*(?:from|import)\s+server\b", text, re.MULTILINE):
                found.append(path)
        return found

    def test_every_tool_importing_server_calls_the_guard(self) -> None:
        targets = self._tools_importing_server()

        # 공허한 통과 방지 — 대상 0개를 훑고 초록이 나오면 아무것도 안 지킨 것이다.
        # 착수 시점 실측 19개. 도구가 늘어도 줄지 않아야 한다.
        assert len(targets) >= 19, (
            f"검사 대상이 {len(targets)}개다. 19개 미만이면 계기가 고장났거나 "
            "도구가 사라진 것이다 — 통과로 읽지 말 것."
        )

        missing = [
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in targets
            if "assert_same_tree(__file__)" not in path.read_text(encoding="utf-8")
        ]
        assert missing == [], (
            f"가드를 안 부르는 도구 {len(missing)}/{len(targets)}개 — "
            f"빌린 인터프리터로 부르면 조용히 남의 트리 코드가 돈다: {missing}"
        )
