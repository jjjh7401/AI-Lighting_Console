"""t182 4단계 — (ㄱ) 을 고치면 S1(현실 조합)에서 사용자가 무엇을 보는가.

리드의 물음: FID 축이 「콘솔이 안 답했다」를 채우는가(a), 거기도 비어 있는가(b).
(a) 면 (ㄱ) 만으로도 「서버 내부 문제」가 콘솔을 가리키는 말로 바뀐다.

## 스텁을 쓰지 않는다 — 그게 이 회차의 요점

3단계는 read_existing_fids 를 감싼 스텁으로 쟀다. 그 스텁이 답을 만들었을 수
있으므로(2단계에서 실제로 그랬다) 이번엔 **진짜 함수를 그 갈래로 태운다.**

patchplan.py:1461-1466 을 읽었다:

    state = fid_property_port.query_state(FID_FIXTURE_ROOT)
    if state.get("ok") is not True:
        return ExistingFidRead(attempted=True, root_unreadable=True)

즉 포트가 **예외 대신 ok=False** 를 주면 그 갈래를 스텁 없이 탄다. 그리고 그 반환은
3단계 S1 스텁과 바이트 동일하다 — 내 스텁이 지어낸 값이 아니라 이 함수의 실패 반환이다.

⚠️ **이 자극은 섹션 축도 바꾼다.** collect_rig_sections:1012 는 예외만 잡으므로
ok=False 는 그 갈래를 안 탄다. 그래서 이 회차가 정하는 것은 **FID 축 문면 하나**이고,
섹션 축 거동은 여기서 읽지 않는다. 자극이 두 축을 건드리는 것을 알고 쏘는 것과
모르고 쏘는 것은 다르다 — 2단계에서 후자를 했다.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.tests import test_lxseq_group_section_request as G
from server.vwx.patchplan import FID_FIXTURE_ROOT


def not_ok(base, dead_root):
    """예외 대신 ok=False 를 준다 — 진짜 read_existing_fids 의 실패 갈래를 탄다."""

    class NotOk:
        def query_state(self, path, *args, **kwargs):
            if path == dead_root:
                return dict(ok=False, error="console did not answer: " + path)
            return base.query_state(path, *args, **kwargs)

        def query_property(self, path, property_name):
            if path == dead_root or path.startswith(dead_root + "/"):
                return dict(ok=False, error="not readable")
            return base.query_property(path, property_name)

        def __getattr__(self, name):
            return getattr(base, name)

    return NotOk()


def run(dead_root):
    console = G._Console(G._patch_fids())
    port = console if dead_root is None else not_ok(console, dead_root)
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
        return dict(outcome="RAISED", exc=type(error).__name__, msg=str(error)[:90])
    payload = json.loads(ex.result.content or "null")
    return dict(
        outcome="RETURNED",
        is_error=ex.result.is_error,
        console_read_reason=payload.get("console_read_reason"),
        console_read_incomplete=payload.get("console_read_incomplete"),
        refusal=payload.get("refusal"),
        existing_fid_read=payload.get("existing_fid_read"),
    )


print("FID_FIXTURE_ROOT =", FID_FIXTURE_ROOT)
print()
print("대조군  살아있음")
print("   ", json.dumps(run(None), ensure_ascii=False))
print()
print("측정값  FID 루트가 ok=False (스텁 없음, 진짜 read_existing_fids)")
print("   ", json.dumps(run(FID_FIXTURE_ROOT), ensure_ascii=False))
