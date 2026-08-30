"""t182 3단계 — 내 스텁이 답을 만들었나. 두 축을 갈라서 다시 잰다.

2단계에서 read_existing_fids 를 root_unreadable=True 로 흉내 냈더니
console_read_reason 이 「콘솔의 픽스처 루트 상태를 읽지 못했다」로 찼다.
그건 **FID 축**의 사유다. 섹션 축(console_unreachable)이 안 나온 것이
- 코드가 원래 안 내보내서인지
- 내 스텁이 FID 축으로 채널을 먼저 채워서인지
2단계로는 안 갈린다. 스텁 값을 바꿔 가른다.

스텁 둘:
  S1  root_unreadable=True   (2단계와 같음 — FID 축이 말한다)
  S2  attempted=True, 깨끗함  (FID 축은 조용하다 — 섹션 축만 남는다)

S2 에서도 console_unreachable 이 안 나오면 그건 **코드의 성질**이다.
S2 에서 나오면 2단계 결론은 내 스텁이 만든 것이고 철회해야 한다.
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


def make_stub(clean):
    def stub(port):
        try:
            return _original(port)
        except Exception:
            if clean:
                # 살아있을 때와 **같은** FID 를 완전 판독으로 돌려준다.
                # 지어낸 fids=(1,2,3) 은 패치 시트와 안 맞아 하류가
                # SpatialAnalysisError 로 터졌다 — 그 팔은 무효였다.
                real = tuple(G._patch_fids())
                return ExistingFidRead(
                    attempted=True,
                    fids=real,
                    child_count=len(real),
                    enumerated_count=len(real),
                    unseen=0,
                )
            return ExistingFidRead(attempted=True, fids=(), root_unreadable=True)

    return stub


def run(dead, clean):
    stub = make_stub(clean)
    T.read_existing_fids = stub
    assert T.read_existing_fids is not _original, "적용 안 됨"
    try:
        console = G._Console(G._patch_fids())
        port = P.killing(console, dead, P.make_factory(StateQueryError))
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
            return dict(outcome="RAISES", exc=type(error).__name__)
        content = ex.result.content or ""
        payload = json.loads(content)
        hay = json.dumps(payload, ensure_ascii=False)
        return dict(
            console_read_reason=payload.get("console_read_reason"),
            refusal=payload.get("refusal"),
            refusal_detail=payload.get("refusal_detail"),
            console_read_incomplete=payload.get("console_read_incomplete"),
            has_console_unreachable=("console_unreachable" in hay),
            has_path_not_resolved=("path_not_resolved" in hay),
        )
    finally:
        T.read_existing_fids = _original


for stub_label, clean in (("S1 root_unreadable=True", False), ("S2 FID 축 조용함", True)):
    print("=" * 60)
    print(stub_label)
    print("=" * 60)
    for case_label, dead in (
        ("  C  fixtures 만 죽음  (계산=path_not_resolved)", P.ONLY_FIXTURES),
        ("  E  둘 다 죽음        (계산=console_unreachable)", P.BOTH),
    ):
        print(case_label)
        print("     ", json.dumps(run(dead, clean), ensure_ascii=False))
    print()
