"""t182 1단계 — console_unreachable 이 이 경로에서 **계산되는가**.

카드가 가른 두 갈래는 처방이 다르다:
  (가) 계산은 되는데 소비자에게 안 나간다  -> 채널을 잇는 일
  (나) 예외가 먼저 터져 계산 자체가 없다   -> 예외를 거절로 바꾸는 일
재기 전에 어느 쪽 처방도 쓰지 않는다.

## 이 가짜가 무엇을 정하나 (t181 에서 걸린 자리라 먼저 적는다)

_Console 은 죽은 경로에서 **LookupError** 를 던진다. 실물 포트는
**StateQueryError** 를 던진다(server/safety/console.py:89, raise 8자리).
t181 에서 이 차이가 처방을 통째로 바꿀 뻔했다 — 가짜가 고른 종류를 실물의
성질로 읽으면 except LookupError 를 넣고 실기에서 아무것도 안 잡힌다.

그래서 이 프로브는 **두 종류를 다 쏜다.** collect_rig_sections:1012 가
except Exception 이라 종류를 안 가릴 것으로 **읽히는데**, 읽은 것과 도는 것이
같은지는 재야 안다. 두 종류의 답이 갈리면 그 자체가 발견이다.

정하는 것 셋:
  1. 예외 종류 — LookupError / StateQueryError 둘 다
  2. 어느 경로가 죽는가 — fixtures 만 / 둘 다
     (console_unreachable 은 아무도 안 답해야 나온다 — 형제가 답하면
      path_not_resolved 다. 둘 다 죽이는 팔이 이 카드의 본체다)
  3. 살아있는 팔 — 계기가 늘 같은 답을 내는 게 아님을 보인다
"""

from __future__ import annotations

import json
import sys
import traceback

sys.path.insert(0, ".")

from server.llm.types import ToolCall
from server.orchestrator import tools as T
from server.orchestrator.tools import build_toolset
from server.safety.console import StateQueryError
from server.tests import test_lxseq_group_section_request as G


def killing(base, dead, exc_factory):
    class Killed:
        def query_state(self, path, *args, **kwargs):
            if path in dead:
                raise exc_factory(path)
            return base.query_state(path, *args, **kwargs)

        def query_property(self, path, property_name):
            for d in dead:
                if path == d or path.startswith(d + "/"):
                    raise exc_factory(path)
            return base.query_property(path, property_name)

        def __getattr__(self, name):
            return getattr(base, name)

    return Killed()


def reason_of(value):
    if isinstance(value, dict) and "reason" in value:
        return value.get("reason")
    return "<읽힘>"


def run(dead, exc_factory):
    """도구를 태우고 (a) collect 가 무엇을 계산했나 (b) 도구가 무엇을 냈나."""
    seen = []
    original = T.collect_rig_sections

    def spy(state_port, paths, drilldown, budget):
        out = original(state_port, paths, drilldown, budget)
        seen.append(out[0])
        return out

    T.collect_rig_sections = spy
    assert T.collect_rig_sections is not original, "적용 안 됨 - 스파이가 안 걸렸다"
    try:
        console = G._Console(G._patch_fids())
        port = console if not dead else killing(console, dead, exc_factory)
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
            stack = traceback.extract_tb(error.__traceback__)
            frames = []
            for f in stack:
                if "tools.py" in f.filename or "patchplan.py" in f.filename:
                    frames.append(f.filename.split("/")[-1] + ":" + str(f.lineno) + " " + f.name)
            outcome = dict(outcome="RAISED", exc=type(error).__name__, frames=frames[-3:])
        else:
            content = ex.result.content or ""
            row = dict(outcome="RETURNED", is_error=ex.result.is_error)
            try:
                payload = json.loads(content)
            except Exception:
                row["payload"] = "<not json>"
            else:
                row["console_read_reason"] = payload.get("console_read_reason")
                row["refusal"] = payload.get("refusal")
                row["refusal_detail"] = payload.get("refusal_detail")
            outcome = row
    finally:
        T.collect_rig_sections = original
    assert T.collect_rig_sections is original, "복원 실패"

    computed = None
    if seen:
        computed = dict((k, reason_of(v)) for k, v in seen[0].items())
    return dict(spy_called=bool(seen), computed=computed, **outcome)


BOTH = frozenset([G.FIXTURES_PATH, G.GROUPS_PATH])
ONLY_FIXTURES = frozenset([G.FIXTURES_PATH])
CASES = [
    ("A  살아있음                        (대조군)", frozenset(), None),
    ("B  fixtures 만 죽음   LookupError", ONLY_FIXTURES, LookupError),
    ("C  fixtures 만 죽음   StateQueryError", ONLY_FIXTURES, StateQueryError),
    ("D  둘 다 죽음         LookupError", BOTH, LookupError),
    ("E  둘 다 죽음         StateQueryError", BOTH, StateQueryError),
]


def make_factory(kind):
    if kind is None:
        return None
    return lambda p: kind("console did not answer: " + p)


def main():
    for label, dead, kind in CASES:
        print(label)
        print("   ", json.dumps(run(dead, make_factory(kind)), ensure_ascii=False))
        print()


# 형제 프로브가 killing/make_factory 를 임포트한다 — 가드가 없으면
# 임포트만으로 이 회차가 다시 돌아 남의 출력에 섞인다.
if __name__ == "__main__":
    main()
