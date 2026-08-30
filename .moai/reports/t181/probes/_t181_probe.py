"""t181 프로브 (임시, 커밋 안 함) - read_existing_fids 호출자 3자리 전수.

물음: 픽스처 경로만 죽었을 때 각 자리가 거절하는가, 예외로 죽는가.

각 자리 팔 둘 (lane-protocol 3절 「대조군은 두 팔」):
  A) 살아있는 콘솔 -> 안 죽어야 한다. 프로브가 그 코드에 닿는다는 증거.
  B) 픽스처만 죽임 -> 이게 측정값.
A 가 이미 빨개지면 B 는 읽을 수 없다 - 계기가 못 보는 것과 현상이 없는 것이 안 갈린다.
"""

from __future__ import annotations

import json
import sys
import traceback

sys.path.insert(0, ".")

from server.llm.types import ToolCall
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, build_toolset

FIXTURES = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]


def killing(base, dead_paths):
    """base 를 감싸 dead_paths 만 예외를 던지게 한다.

    프로덕션 포트의 실패 형태가 예외다 (server/safety/console.py query_state:
    "raises on failure/timeout"). ok=False 가짜를 지으면 이 갈래를 안 탄다.
    """

    class Killed:
        def __init__(self):
            self.killed = 0

        def query_state(self, path, *args, **kwargs):
            if path in dead_paths:
                self.killed += 1
                raise LookupError("console did not answer: " + path)
            return base.query_state(path, *args, **kwargs)

        def query_property(self, path, property_name):
            for dead in dead_paths:
                if path == dead or path.startswith(dead + "/"):
                    self.killed += 1
                    raise LookupError("console did not answer: " + path)
            return base.query_property(path, property_name)

        def __getattr__(self, name):
            return getattr(base, name)

    return Killed()


def observe(label, run):
    """도구를 한 번 태우고 사용자에게 무엇이 가는지 기록한다."""
    try:
        execution = run()
    except BaseException as error:
        return dict(
            arm=label,
            outcome="RAISED",
            exc_type=type(error).__name__,
            exc_msg=str(error)[:140],
            frame=traceback.extract_tb(error.__traceback__)[-1].name,
        )
    result = execution.result
    content = result.content or ""
    row = dict(
        arm=label,
        outcome="RETURNED",
        is_error=result.is_error,
        content_head=content[:220],
    )
    try:
        payload = json.loads(content)
    except Exception:
        row["payload_status"] = "<not json>"
    else:
        if isinstance(payload, dict):
            row["payload_status"] = payload.get("status")
            row["refusal"] = payload.get("refusal")
            row["console_read_reason"] = payload.get("console_read_reason")
    return row


def site_groups():
    """자리 4738 - import_lxseq_groups (t167 자리)."""
    from server.tests import test_lxseq_group_section_request as G

    def run(dead):
        console = G._Console(G._patch_fids())
        port = console if dead is None else killing(console, dead)
        registry = build_toolset(
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
        return lambda: registry.dispatch(ToolCall(id="t181", name=G.TOOL, arguments=args))

    return [
        observe("A live", run(None)),
        observe("B fixtures-dead", run(frozenset([G.FIXTURES_PATH]))),
    ]


def site_patch_tools():
    """자리 4358 patch_fixtures / 자리 5428 import_lxseq_patch."""
    from server.tests import test_lxseq_tool as L

    def registry_for(dead):
        console = L.FakeConsole()
        port = console if dead is None else killing(console, dead)
        return build_toolset(
            execution_port=L.FakeExec(console),
            state_port=port,
            property_port=port,
            deploy_pipeline=L.FakeDeploy(console),
            question_port=L.Answers(),
        )

    patch_args = dict(console_type="Robe MegaPointe", address="9.1", count=1)
    rows = []
    for label, dead in (("A live", None), ("B fixtures-dead", frozenset([FIXTURES]))):
        r1 = registry_for(dead)
        rows.append(
            (
                "patch_fixtures",
                observe(
                    label,
                    lambda r=r1: r.dispatch(
                        ToolCall(id="t181", name="patch_fixtures", arguments=patch_args)
                    ),
                ),
            )
        )
        r2 = registry_for(dead)
        lx_args = dict(file_content_base64=L._b64())
        rows.append(
            (
                "import_lxseq_patch",
                observe(
                    label,
                    lambda r=r2, a=lx_args: r.dispatch(
                        ToolCall(id="t181", name="import_lxseq_patch", arguments=a)
                    ),
                ),
            )
        )
    return rows


if __name__ == "__main__":
    print("=" * 70)
    print("SITE 4738  import_lxseq_groups")
    print("=" * 70)
    for row in site_groups():
        print(json.dumps(row, ensure_ascii=False, indent=2))
    print()
    print("=" * 70)
    print("SITE 4358 patch_fixtures / SITE 5428 import_lxseq_patch")
    print("=" * 70)
    for tool, row in site_patch_tools():
        print(tool, "::", json.dumps(row, ensure_ascii=False))
