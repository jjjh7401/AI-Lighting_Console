"""트리 동일성 가드 (SPEC-COPILOT-TREEID-001).

`server/tools/` 의 도구는 이 저장소의 **콘솔 실측 증거를 생산한다.** 그 도구를
다른 워크트리의 인터프리터로 스크립트 경로로 부르면 남의 트리 코드가 경고 한 줄
없이 돈다 — 증거의 출처가 조용히 바뀐다. 이 모듈은 그때 **죽는다.**

## 왜 이 비교로 충분한가 — 가드 모듈 자신이 증인이다

도구 ``A/server/tools/foo.py`` 가 ``from server.tools.tree_identity import ...`` 를
하면, 이 모듈은 **인터프리터가 데려온 트리**(B)에서 실려 온다. 그래서 비교는
자기완결적이다::

    caller_tree : 호출자 __file__ 이 속한 트리   -> A
    guard_tree  : 이 모듈 자신의 __file__        -> B

``A != B`` 이면 죽는다. git 도, 환경변수도, 서브프로세스도 필요 없다.

## 기전

스크립트 경로 실행은 ``sys.path[0]`` 이 **스크립트 디렉터리**(``server/tools/``)라
자기 트리 루트를 담지 않는다. 가릴 것이 없으니 venv 의 editable ``.pth`` 가 이긴다.
``-m`` 과 ``-c`` 는 ``sys.path[0]`` 이 cwd 라 자기 트리가 이기지만, ``-P`` 플래그
하나면 그 안전도 뒤집힌다 — 지금의 안전은 구조가 아니라 기본값이다.

## 호출 위치

각 도구의 **임포트 블록 뒤, 본문 앞**에서 ``assert_same_tree(__file__)`` 을 부른다.
임포트 앞에 두면 뒤따르는 임포트가 전부 ruff ``E402`` 에 걸린다. 그 대가를 감수할
이유가 없다는 것은 실측으로 확인했다 — 19개 도구를 본문 실행 없이 임포트만 시켰을 때
파일 쓰기·소켓·프로세스·삭제·환경변수 변형이 전부 0건이었다
(``.moai/reports/t80/m0-import-side-effects.md``).

## 종료 코드

**3** 이다. 1(일반 실패)과 **2(argparse 인자 오류)** 둘 다와 달라야 검사가
「가드가 죽였다」와 「인자가 틀렸다」를 구별할 수 있다.
"""

from __future__ import annotations

import sys
from pathlib import Path

EXIT_CODE = 3


def _die(*lines: str) -> None:
    for line in lines:
        print(line, file=sys.stderr)
    raise SystemExit(EXIT_CODE)


def _tree_of(path: str | Path) -> Path:
    """``<tree>/server/...`` 에서 ``<tree>`` 를 뽑는다.

    고정 깊이(``parents[N]``)를 가정하지 않는다 — ``server/`` 아래 하위 디렉터리가
    생겨도 견딘다. 못 찾으면 **조용히 통과시키지 않는다**: 건너뛰는 갈래를 새로
    만드는 것이 바로 이 가드가 없애려는 결함이다.
    """
    resolved = Path(path).resolve()
    for parent in resolved.parents:
        if parent.name == "server":
            return parent.parent
    _die(
        "트리 동일성 가드: 트리 뿌리를 찾지 못했다.",
        f"  대상: {resolved}",
        "  이 파일은 server/ 아래에 있지 않다. 가드는 판정할 수 없을 때 통과시키지 않는다.",
    )
    raise AssertionError("unreachable")  # pragma: no cover


_GUARD_TREE = _tree_of(__file__)


def assert_same_tree(caller_file: str | Path) -> None:
    """호출자와 이 모듈이 같은 워크트리에서 왔는지 확인하고, 아니면 죽는다.

    각 도구의 임포트 블록 뒤에서 ``assert_same_tree(__file__)`` 으로 부른다.
    """
    caller_tree = _tree_of(caller_file)
    if caller_tree == _GUARD_TREE:
        return

    module = Path(caller_file).stem
    _die(
        "트리 동일성 위반 — 이 도구는 남의 워크트리 코드를 부르고 있다.",
        "",
        f"  실행한 스크립트 : {caller_tree}",
        f"  임포트된 server : {_GUARD_TREE}",
        "",
        "인터프리터가 다른 트리의 venv 다. 스크립트 경로로 실행하면 sys.path[0] 이",
        "server/tools/ 라 자기 트리가 가려지고, venv 의 editable .pth 가 이긴다.",
        "",
        f"고칠 것:  uv run python -m server.tools.{module} <인자...>",
    )
