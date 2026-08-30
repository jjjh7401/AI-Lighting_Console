"""t182 2단계 — 죽는 것을 고치면 console_unreachable 이 **사용자에게 닿는가**.

1단계가 정한 것: 분류는 계산된다. 그리고 그 다음 줄(read_existing_fids)에서
도구가 죽어 페이로드가 안 만들어진다.

그래서 남는 물음은 「죽음만 고치면 채널이 흐르는가」다. 둘은 다른 일이다 —
죽음을 고쳐도 소비자가 그 값을 안 읽으면 채널은 여전히 안 흐른다.
t152 가 이 도구는 sections["groups"] 하나만 읽는다고 기록해 뒀다.

소스를 안 건드리고 read_existing_fids 만 감싸서, 죽는 대신 **미판독 상태**를
돌려주게 한다(= 그 자리가 고쳐진 상태를 흉내낸다). 그러고 나서 페이로드에
무엇이 실리는지 본다.

⚠️ 이 흉내는 「어떻게 고칠지」를 정하지 않는다. 실제 수리는 거절일 수도, 미판독
전달일 수도 있다. 여기서는 **죽지만 않으면 무엇이 나가는가**만 잰다.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

import _t182_computed as P

from server.llm.types import ToolCall
from server.orchestrator import tools as T
from server.orchestrator.tools import build_toolset
from server.safety.console import StateQueryError
from server.tests import test_lxseq_group_section_request as G
from server.vwx.patchplan import ExistingFidRead

_original = T.read_existing_fids


def survivable(port):
    """죽는 대신 「아무것도 못 읽었다」를 돌려준다."""
    try:
        return _original(port)
    except Exception:
        return ExistingFidRead(attempted=True, fids=(), root_unreadable=True)


def run(dead, kind):
    T.read_existing_fids = survivable
    assert T.read_existing_fids is not _original, "적용 안 됨"
    try:
        console = G._Console(G._patch_fids())
        port = P.killing(console, dead, P.make_factory(kind))
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
        try:
            ex = registry.dispatch(ToolCall(id="t182", name=G.TOOL, arguments=args))
        except BaseException as error:
            return dict(outcome="STILL RAISES", exc=type(error).__name__, msg=str(error)[:90])
        content = ex.result.content or ""
        row = dict(outcome="RETURNED", is_error=ex.result.is_error)
        try:
            payload = json.loads(content)
        except Exception:
            row["payload"] = content[:160]
            return row
        row["console_read_reason"] = payload.get("console_read_reason")
        row["refusal"] = payload.get("refusal")
        row["refusal_detail"] = payload.get("refusal_detail")
        row["console_read_incomplete"] = payload.get("console_read_incomplete")
        hay = json.dumps(payload, ensure_ascii=False)
        row["말이 페이로드 어디엔가 있나"] = dict(
            console_unreachable=("console_unreachable" in hay),
            path_not_resolved=("path_not_resolved" in hay),
        )
        return row
    finally:
        T.read_existing_fids = _original


CASES = [
    ("A  살아있음               (대조군)", frozenset(), None),
    ("C  fixtures 만 죽음       StateQueryError", P.ONLY_FIXTURES, StateQueryError),
    ("E  둘 다 죽음             StateQueryError", P.BOTH, StateQueryError),
]

for label, dead, kind in CASES:
    print(label)
    print("   ", json.dumps(run(dead, kind), ensure_ascii=False))
    print()
