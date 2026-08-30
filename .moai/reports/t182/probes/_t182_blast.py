"""t182 5단계 — 폭발 반경. 리드가 읽은 것을 내가 잰다 (조건 4).

리드의 읽기: read_existing_fids 호출자 셋 중 둘(4368 · 5447)은 t181 이 고친
read_inventory 에서 **먼저** 거절되므로 실질 변화는 4748 하나다.

t181 에서 같은 형태를 쟀지만 그건 **수리 전 트리**였다. 지금은 t181 이 들어간
뒤(0fc0439)라 앞자리가 거절로 바뀌었다 — 그래서 다시 잰다. 옮겨 온 값이 아니라
이 트리에서 나온 값이어야 한다.

⚠️ 도구마다 맞는 가짜가 다르다. import_lxseq_groups 는 페이징이 필요해
_Console 을, 나머지 둘은 FakeConsole 을 쓴다. **셋을 서로 비교하는 것이 아니라
도구별로 「어디서 멈추나」를 따로 묻는 것**이므로 이 차이는 이 물음에 안 걸린다.
"""

from __future__ import annotations

import json
import sys
import traceback

sys.path.insert(0, ".")

from server.llm.types import ToolCall
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, build_toolset
from server.safety.console import StateQueryError

FIXTURES = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]


def killing(base, dead):
    class Killed:
        def query_state(self, path, *args, **kwargs):
            if path in dead:
                raise StateQueryError("no state reply for " + repr(path) + " within 5.0s")
            return base.query_state(path, *args, **kwargs)

        def query_property(self, path, property_name):
            for d in dead:
                if path == d or path.startswith(d + "/"):
                    raise StateQueryError("no prop reply for " + repr(path) + " within 5.0s")
            return base.query_property(path, property_name)

        def __getattr__(self, name):
            return getattr(base, name)

    return Killed()


def observe(label, run):
    try:
        ex = run()
    except BaseException as error:
        stack = traceback.extract_tb(error.__traceback__)
        frames = []
        for f in stack:
            if "tools.py" in f.filename or "patchplan.py" in f.filename:
                frames.append(f.filename.split("/")[-1] + ":" + str(f.lineno) + " " + f.name)
        return dict(tool=label, outcome="RAISES", exc=type(error).__name__, frames=frames[-2:])
    return dict(
        tool=label,
        outcome="REFUSES",
        is_error=ex.result.is_error,
        content=(ex.result.content or "")[:110],
    )


def groups_tool():
    from server.tests import test_lxseq_group_section_request as G

    console = G._Console(G._patch_fids())
    port = killing(console, frozenset([G.FIXTURES_PATH]))
    reg = build_toolset(
        execution_port=G._SilentPort(),
        state_port=port,
        property_port=port,
        group_approval_port=G._ApprovePort(),
    )
    args = dict(
        group_content_base64=G._b64(G.GROUP_CSV),
        patch_content_base64=G._b64(G.PATCH_CSV),
        action="preview",
    )
    return observe(
        "4748 import_lxseq_groups",
        lambda: reg.dispatch(ToolCall(id="t182", name=G.TOOL, arguments=args)),
    )


def patch_tools():
    from server.tests import test_lxseq_tool as L

    rows = []
    for label, name, args in (
        (
            "4368 patch_fixtures",
            "patch_fixtures",
            dict(console_type="Robe MegaPointe", address="9.1", count=1),
        ),
        ("5447 import_lxseq_patch", "import_lxseq_patch", dict(file_content_base64=L._b64())),
    ):
        console = L.FakeConsole()
        port = killing(console, frozenset([FIXTURES]))
        reg = build_toolset(
            execution_port=L.FakeExec(console),
            state_port=port,
            property_port=port,
            deploy_pipeline=L.FakeDeploy(console),
            question_port=L.Answers(),
        )
        rows.append(
            observe(
                label,
                lambda r=reg, n=name, a=args: r.dispatch(ToolCall(id="t182", name=n, arguments=a)),
            )
        )
    return rows


print(json.dumps(groups_tool(), ensure_ascii=False, indent=2))
for row in patch_tools():
    print(json.dumps(row, ensure_ascii=False, indent=2))
