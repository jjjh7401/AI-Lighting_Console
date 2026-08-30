"""프레임 보강 - 예외가 tools.py 의 몇 번째 줄에서 나갔는지 기록한다.

「셋 다 죽는다」와 「셋 다 같은 자리에서 죽는다」는 다른 주장이다.
5428 자리는 바로 위 read_inventory(5422) 가 먼저 터졌을 수 있고,
그러면 read_existing_fids 를 고쳐도 그 도구는 안 낫는다.
"""

from __future__ import annotations

import json
import traceback

import _t181_probe as P


def frames_of(run):
    try:
        run()
    except BaseException as error:
        stack = traceback.extract_tb(error.__traceback__)
        return [
            f"{f.filename.split('/')[-1]}:{f.lineno} {f.name}"
            for f in stack
            if "tools.py" in f.filename or "patchplan.py" in f.filename
        ]
    return ["<did not raise>"]


def main():
    from server.llm.types import ToolCall
    from server.orchestrator.tools import build_toolset
    from server.tests import test_lxseq_group_section_request as G
    from server.tests import test_lxseq_tool as L

    dead = frozenset([P.FIXTURES])

    console = G._Console(G._patch_fids())
    port = P.killing(console, frozenset([G.FIXTURES_PATH]))
    reg = build_toolset(
        execution_port=G._SilentPort(),
        state_port=port,
        property_port=port,
        group_approval_port=G._ApprovePort(),
    )
    gargs = dict(
        group_content_base64=G._b64(G.GROUP_CSV),
        patch_content_base64=G._b64(G.PATCH_CSV),
        action="preview",
    )
    print("SITE 4738 import_lxseq_groups")
    print(
        json.dumps(
            frames_of(lambda: reg.dispatch(ToolCall(id="f", name=G.TOOL, arguments=gargs))),
            ensure_ascii=False,
            indent=2,
        )
    )

    def rig(d):
        c = L.FakeConsole()
        p = P.killing(c, d)
        return build_toolset(
            execution_port=L.FakeExec(c),
            state_port=p,
            property_port=p,
            deploy_pipeline=L.FakeDeploy(c),
            question_port=L.Answers(),
        )

    r1 = rig(dead)
    pargs = dict(console_type="Robe MegaPointe", address="9.1", count=1)
    print("SITE 4358 patch_fixtures")
    print(
        json.dumps(
            frames_of(
                lambda: r1.dispatch(ToolCall(id="f", name="patch_fixtures", arguments=pargs))
            ),
            ensure_ascii=False,
            indent=2,
        )
    )

    r2 = rig(dead)
    largs = dict(file_content_base64=L._b64())
    print("SITE 5428 import_lxseq_patch")
    print(
        json.dumps(
            frames_of(
                lambda: r2.dispatch(ToolCall(id="f", name="import_lxseq_patch", arguments=largs))
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


main()
