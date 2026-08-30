"""t131 — 호출부가 첫 창에서 멈추면 큰 풀에서 임포트가 통째로 거절된다.

## 무엇이 결함이었나

`import_lxseq_presets` 는 프리셋 풀을 **한 번** 조회하고 그 창을 풀 전체로 썼다.
응답기는 자식을 다 싣지 않으므로 그 단면에는 `truncated: True` 가 실리고,
`server/rig/section.py` 의 술어가 그것을 `section_truncated` 로 **fail-closed**
한다. 결과는 잘못된 발사가 아니라 **능력 상실** — 풀이 조금만 커도 임포트가
아예 안 됐다. 안전한 방향으로 틀렸지만, 틀린 것은 맞다.

## 절단 축이 둘이다 — 검사가 이걸 반영해야 한다

개수 캡은 `max_children = 24` (`console/lua/copilot_responder.lua:33`)이고,
페이로드 예산은 절단 경계 `[1200, 1208)` 바이트다(t12 실측). 둘 중 **먼저
걸리는 쪽**에서 잘린다.

t131 실기(1.6.2)에서 `Patch/Stages/1/Fixtures` 의 `childCount 86` 이 **19 · 18**
두 창으로 왔다. 19 는 24보다 작다 — 바이트 축에 걸린 것이다. 그래서:

- 「자식 25개 이상일 때만 페이징」이라는 판별기는 **틀린다**
- 「한 창에 N개씩 온다」로 못박는 검사도 **틀린다** — 이름 길이에 따라 변한다

이 파일의 더블은 그래서 창 크기를 **일부러 들쭉날쭉하게**(19 · 18 · 3) 낸다.
고정 창을 가정한 구현은 여기서 걸린다.

## 단언을 `truncated is False` 로 잡으면 공허하다

「안 잘렸다」와 「이어 붙였다」는 다른 말이다. 첫 창만 쓰고 플래그만 지우는
구현도 `truncated is False` 를 통과한다. 이 저장소가 이미 겪은 「검사 자신이
공허할 수 있다」 계열이다. 그래서 단언은 둘 다 완전성을 본다:

1. **단위** — `len(모은 자식) == node.childCount`
2. **호출부** — 2·3창에만 있는 점유가 `already_present` 로 잡히는가.
   첫 창만 읽는 구현은 그 이름을 못 보므로 원리적으로 통과할 수 없다

콘솔·네트워크 접촉 0. 순수 검증이다.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.rig.paging import PAGE_CAP, paged_children

RIG = Path("src/Lighting_Designer/02_RIG팩")
DIM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"

#: 시트가 실제로 싣는 여섯 이름 — `already_present` 판정은 이름으로 난다.
SHEET_NAMES = ("풀", "쇼 하이", "미드", "로우", "잔광", "아웃")

#: 일부러 들쭉날쭉한 창 — 실기가 19·18 로 왔다. 고정 창 가정을 잡는다.
WINDOW_SIZES = (19, 18, 3)

#: 여섯 이름을 세 창에 흩는다. 하나(3번)만 첫 창이고 나머지는 2·3창이라,
#: 첫 창만 읽는 구현은 다섯 개를 못 본다. 40번은 3창이라 마지막 창까지
#: 걷지 않으면 안 잡힌다.
OCCUPANT_SLOTS = dict(
    [(3, "풀"), (25, "쇼 하이"), (30, "미드"), (33, "로우"), (36, "잔광"), (40, "아웃")]
)
POOL_TOTAL = 40


def _pool_children(total: int = POOL_TOTAL) -> list[dict]:
    return [
        dict(i=slot, name=OCCUPANT_SLOTS.get(slot, "기타 " + str(slot)))
        for slot in range(1, total + 1)
    ]


def _paginate(children: list[dict], sizes: tuple[int, ...]) -> list[list[dict]]:
    """창 크기를 순서대로 적용해 페이지로 쪼갠다 — 마지막 크기가 반복된다."""
    pages: list[list[dict]] = []
    start = 0
    step = 0
    while start < len(children):
        size = sizes[min(step, len(sizes) - 1)]
        pages.append(children[start : start + size])
        start += size
        step += 1
    return pages or [[]]


class _Console:
    """페이징을 아는 응답기 더블. 요청한 offset 을 **에코**한다.

    에코가 전진의 유일한 증거다 — 낡은 응답기는 offset 을 무시하고 매번 첫
    창을 돌려주므로, 에코를 안 보는 구현은 무한 루프가 된다(t104).
    """

    def __init__(
        self,
        *,
        children: list[dict] | None = None,
        sizes: tuple[int, ...] = WINDOW_SIZES,
        echo: bool = True,
    ) -> None:
        self.children = _pool_children() if children is None else children
        self.pages = _paginate(self.children, sizes)
        self.starts: dict[int, list[dict]] = dict()
        start = 0
        for page in self.pages:
            self.starts[start] = page
            start += len(page)
        self.echo = echo
        self.calls: list[tuple[str, int]] = []
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append((path, offset))
        if path.endswith("PresetPools"):
            pools = [dict(i=1, name="Dimmer")]
            return dict(children=pools, node=dict(childCount=len(pools)), truncated=False)
        return self.pool_window(offset)

    def pool_window(self, offset: int) -> dict:
        window = self.starts.get(offset, [])
        payload = dict(
            children=window,
            node=dict(childCount=len(self.children), name="Dimmer"),
            truncated=offset + len(window) < len(self.children),
        )
        if self.echo:
            payload["offset"] = offset
        return payload


class _LegacyConsole(_Console):
    """페이징을 **모르는** 포트 — `offset` 키워드를 아예 안 받는다."""

    def query_state(self, path: str) -> dict:  # type: ignore[override]
        return super().query_state(path)


class _Approval:
    def request_approval(self, request) -> bool:
        return True


def _dispatch(port) -> dict:
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t131",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(DIM.read_bytes()).decode("ascii"),
                action="preview",
            ),
        )
    )
    return json.loads(execution.result.content)


class TestTheLoopCollectsEverything:
    """단위 단언 — 「모은 개수 == childCount」. `truncated` 플래그가 아니다."""

    def test_every_child_arrives_across_uneven_windows(self):
        console = _Console()
        first = console.pool_window(0)
        children, truncated = paged_children(console, "DataPool/PresetPools/1", first)
        assert len(children) == first["node"]["childCount"], (
            "모은 자식이 childCount 에 못 미친다 — 「안 잘렸다」는 「이어 붙였다」가 "
            "아니다. 모은 " + str(len(children)) + " / 총 " + str(POOL_TOTAL)
        )
        assert truncated is False
        assert [c["i"] for c in children] == list(range(1, POOL_TOTAL + 1))

    def test_the_windows_really_were_uneven(self):
        """대조군 — 창이 균일하면 위 검사가 「고정 창 가정」을 못 잡는다."""
        sizes = [len(page) for page in _Console().pages]
        assert len(set(sizes[:-1])) > 1, sizes

    def test_a_single_window_pool_spends_no_follow_up_query(self):
        """대조군 — 안 잘린 풀에서 후속 조회를 쏘면 왕복 낭비다."""
        console = _Console(children=_pool_children(6), sizes=(24,))
        first = console.pool_window(0)
        console.calls.clear()
        children, truncated = paged_children(console, "DataPool/PresetPools/1", first)
        assert (len(children), truncated, console.calls) == (6, False, [])


class TestNoProgressIsNotALoop:
    """전진 못 하는 갈래는 **즉시** 멈추고 미완을 고지한다."""

    def test_an_echoless_responder_stops_after_one_probe(self):
        console = _Console(echo=False)
        first = console.pool_window(0)
        console.calls.clear()
        children, truncated = paged_children(console, "DataPool/PresetPools/1", first)
        assert truncated is True, "에코가 없는데 완전 판독을 주장했다"
        assert len(console.calls) == 1, console.calls
        assert len(children) == len(first["children"])

    def test_a_port_without_the_offset_kwarg_degrades_honestly(self):
        console = _LegacyConsole()
        first = console.pool_window(0)
        children, truncated = paged_children(console, "DataPool/PresetPools/1", first)
        assert truncated is True
        assert len(children) == len(first["children"])

    def test_a_pool_past_the_page_cap_stays_truncated(self):
        """상한을 넘으면 부분을 전체인 척하지 않는다."""
        console = _Console(children=_pool_children(400), sizes=(19,))
        first = console.pool_window(0)
        children, truncated = paged_children(console, "DataPool/PresetPools/1", first)
        assert truncated is True
        assert len(children) == 19 * (PAGE_CAP + 1)


class TestTheCallSiteWalksTheWholePool:
    """결함이 난 자리 — `server/orchestrator/tools.py` 의 프리셋 풀 판독.

    2·3창에만 있는 점유를 잡는지로 잰다. 첫 창만 읽는 구현은 그 이름을 못 보므로
    이 검사를 **원리적으로** 통과할 수 없다 — 플래그만 지우는 우회가 안 통한다.
    """

    def test_occupants_beyond_the_first_window_are_seen(self):
        payload = _dispatch(_Console())
        present = sorted(h["preset_id"] for h in payload["already_present"])
        assert payload.get("refusal") in (None, ""), payload.get("refusal")
        assert len(present) == len(SHEET_NAMES), (
            "2·3창의 점유를 못 봤다 — 첫 창에서 멈췄다. 잡힌 것: " + repr(present)
        )
        assert payload["planned"] == [], (
            "이미 콘솔에 있는 이름을 다시 계획했다 — 안 보인 자리를 비었다고 읽었다. "
            + repr(payload["planned"])
        )

    def test_the_tool_pages_rather_than_asking_once(self):
        console = _Console()
        _dispatch(console)
        pool_offsets = [off for path, off in console.calls if not path.endswith("PresetPools")]
        assert pool_offsets == [0, 19, 37], pool_offsets

    def test_a_truncated_pool_that_cannot_be_paged_is_still_refused(self):
        """대조군 — 걷지 **못하면** 여전히 fail-closed 다. 이 카드가 안전을 깎지
        않았음을 잰다. 없으면 위 검사가 「절단 방어를 지웠다」와 구별되지 않는다."""
        payload = _dispatch(_LegacyConsole())
        assert payload.get("refusal") == "pool_truncated", payload.get("refusal")
        assert payload["planned"] == []

    def test_the_control_probe_still_plans_on_an_empty_pool(self):
        """대조군 — 정말로 빈 풀에서는 여섯 건이 계획된다. 없으면 위 검사가
        「무조건 0건」과 구별되지 않는다."""
        payload = _dispatch(_Console(children=[], sizes=(24,)))
        assert payload.get("refusal") in (None, ""), payload.get("refusal")
        assert len(payload["planned"]) == len(SHEET_NAMES), payload["planned"]


class TestThePagingDisciplineHasOneHome:
    """사본이 늘면 무진전 방어를 빠뜨린 사본이 반드시 생긴다(t104: 무한 루프).

    이 검사가 없으면 위임을 옛 사본으로 되돌려도 아무것도 안 빨개진다.
    """

    def test_the_web_reader_delegates_to_the_shared_loop(self):
        from server.web import presets_api

        assert presets_api._paged_pool_children is paged_children
        assert presets_api._POOL_PAGE_CAP == PAGE_CAP

    def test_the_call_site_does_not_carry_its_own_loop(self):
        source = Path("server/orchestrator/tools.py").read_text(encoding="utf-8")
        assert "paged_children(" in source
        assert "offset=seen" not in source, "호출부에 루프 사본이 생겼다"
