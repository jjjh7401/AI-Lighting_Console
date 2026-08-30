"""자리 4293/5422 를 고쳤다고 가정하면 그다음 무엇이 죽는가.

소스를 안 건드리고 read_inventory 만 감싸 LookupError -> InventoryReadError 로
옮긴다 (= 그 자리의 except 가 이 형태도 잡게 된 상태를 흉내낸다).
그러면 두 도구가 (a) 정상 거절하는가 (b) 다음 자리에서 또 죽는가.

「한 자리 고치면 되는가」의 답이 여기서 갈린다.
"""

from __future__ import annotations

import json
import traceback

import _t181_probe as P

import server.orchestrator.tools as T
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.prechk.inventory import InventoryReadError
from server.tests import test_lxseq_tool as L

_original = T.read_inventory
assert _original is not None


def patched(port, **kwargs):
    try:
        return _original(port, **kwargs)
    except LookupError as error:
        raise InventoryReadError(str(error)) from error


T.read_inventory = patched
assert T.read_inventory is not _original, "적용 안 됨 - 뮤테이션이 안 걸렸다"

DEAD = frozenset([P.FIXTURES])


def rig():
    c = L.FakeConsole()
    p = P.killing(c, DEAD)
    return build_toolset(
        execution_port=L.FakeExec(c),
        state_port=p,
        property_port=p,
        deploy_pipeline=L.FakeDeploy(c),
        question_port=L.Answers(),
    )


def observe(name, args):
    reg = rig()
    try:
        ex = reg.dispatch(ToolCall(id="s", name=name, arguments=args))
    except BaseException as error:
        stack = traceback.extract_tb(error.__traceback__)
        frames = [
            f"{f.filename.split('/')[-1]}:{f.lineno} {f.name}"
            for f in stack
            if "tools.py" in f.filename or "patchplan.py" in f.filename
        ]
        return dict(tool=name, outcome="STILL RAISES", exc=type(error).__name__, frames=frames)
    return dict(
        tool=name,
        outcome="REFUSED CLEANLY",
        is_error=ex.result.is_error,
        content=(ex.result.content or "")[:220],
    )


print(
    json.dumps(
        observe("patch_fixtures", dict(console_type="Robe MegaPointe", address="9.1", count=1)),
        ensure_ascii=False,
        indent=2,
    )
)
print(
    json.dumps(
        observe("import_lxseq_patch", dict(file_content_base64=L._b64())),
        ensure_ascii=False,
        indent=2,
    )
)
