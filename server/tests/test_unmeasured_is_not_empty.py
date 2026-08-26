"""t109 — 「재지 못함」을 「비었음」으로 읽는 자리 둘 (외부 감사 C3+C4).

이 저장소가 같은 계열을 **네 번** 겪었다:

1. GROUPGEN-001 실기 — 그룹의 `childCount 0` 은 「비었다」가 아니라
   「이 채널로는 안 보인다」였다
2. t95 — 내용이 확실히 있는 Group 도 `COUNT 0` 을 답한다. 이 채널의 0/빈값은
   부재의 증거가 아니다
3. t104 — `introspect` 27개는 「이게 전부」가 아니라 「나머지 111개는 도달
   불가」였다
4. 그리고 여기, C3+C4

그래서 자리별로 고치지 않는다. 술어 하나(`server/rig/section.py`)를 뽑고 두
자리가 **그것을** 부른다. 자리별 수정은 다섯 번째 자리가 생길 때 또 난다
(`lesson-point-fixes-dont-drain-a-defect-family`).

## 두 자리의 무게가 다르다 — 그래서 검사도 다르다

**C3 은 생산 지점이다.** 풀을 **못 찾았는데** 겉보기 성공 단면
(`{"objects": [], "truncated": False}`)을 만들어 매퍼에 넘겼다. 매퍼의
`section_refusal` 은 `ok`/`reason` 을 보는데 위조 단면엔 둘 다 없어 통과한다.
결과는 발사가 아니라 **거짓 계획 보고** — 사람이 「아무것도 안 잰 것」에 대해
승인 판단을 한다.

**C4 는 소비 지점이다.** `_measure_empty_slots` 가 `.get("objects") or ()` 를
돌아, 판독 실패 단면(키 자체가 없다)이 빈 점유 집합이 되고 슬롯 1..N 이
비었다고 답한다. 그 함수 docstring 은 스스로 「어긋남을 **보고**해야 하지 던지면
안 된다」고 적어 놓고 `ok` 를 안 본다 — 의도와 코드가 갈렸다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.lxseq.group_mapper import map_groups
from server.lxseq.preset_mapper import section_refusal as preset_section_refusal
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.rig.section import SECTION_TRUNCATED, SECTION_UNREAD, section_refusal

RIG = Path("src/Lighting_Designer/02_RIG팩")
DIM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"

#: 판독이 **실패한** 단면 세 형태. 셋 다 「이 풀에 대해 아무것도 모른다」이며,
#: 어느 하나도 「빈 풀」이 아니다. 세 형태를 다 싣는 이유는 실제로 세 곳이
#: 서로 다른 모양을 내기 때문이다 — 하나만 검사하면 나머지 둘이 새어 나간다.
UNREAD_SECTIONS = (
    ({"ok": False, "reason": "프리셋 풀 목록이 오지 않았다"}, "ok=False + reason"),
    ({"reason": "풀 목록에 'Dimmer' 로 시작하는 풀이 없다"}, "reason 만"),
    ({}, "키가 아예 없다 — 판독 자체가 없었다"),
)


class _Port:
    """풀 목록을 **안 내는** 콘솔 — C3 의 조건을 만든다."""

    def __init__(self, *, pools: list | None = None) -> None:
        self.pools = pools
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str) -> dict:
        if path.endswith("PresetPools"):
            if self.pools is None:
                raise RuntimeError("풀 목록을 못 읽었다")
            return dict(children=self.pools, node=dict(childCount=len(self.pools)))
        return dict(children=[], node=dict(childCount=0), truncated=False)

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


class _Approval:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _dispatch_presets(port):
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t109",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(DIM.read_bytes()).decode("ascii"),
                action="preview",
            ),
        )
    )
    return json.loads(execution.result.content)


class TestThePredicateItself:
    """술어를 **직접** 잰다.

    처음에 이 반이 없었고, 뮤테이션이 그것을 드러냈다: 술어의 `ok`/`reason`/
    `truncated` 신호를 하나씩 죽여도 두 자리 검사가 **둘 다 초록**이었다. 자리별
    검사는 「무언가가 거절한다」를 재지 「술어가 거절한다」를 재지 않는다 —
    두 자리 모두 다른 가드가 같은 입력을 잡아 주기 때문이다.

    신호가 넷이고 각각 실제로 나오는 모양이라, 넷을 따로 잰다. 하나라도 안 재면
    그 신호는 조용히 죽어도 아무도 모른다.
    """

    def test_a_not_ok_section_is_refused_as_unread(self):
        verdict = section_refusal({"ok": False, "reason": "포트가 던졌다"})
        assert verdict is not None
        assert verdict[0] == SECTION_UNREAD, verdict

    def test_a_reason_bearing_section_is_refused_as_unread(self):
        verdict = section_refusal({"reason": "풀을 못 찾았다"})
        assert verdict is not None
        assert verdict[0] == SECTION_UNREAD, verdict

    def test_a_section_without_a_list_is_refused_as_unread(self):
        """C4 의 원래 결함 — 키 부재가 빈 점유로 흘렀다."""
        verdict = section_refusal({})
        assert verdict is not None
        assert verdict[0] == SECTION_UNREAD, verdict

    # 아래 둘은 뮤테이션이 불러냈다. 처음 코퍼스에서는 세 신호가 **서로를
    # 가렸다** — `ok` 를 지워도 `reason` 이 잡고, `reason` 을 지워도 목록 부재가
    # 잡아서, 셋 중 둘이 죽어도 아무 검사가 안 빨개졌다. 각 신호가 **혼자**
    # 걸리는 입력을 넣어야 그 신호에 판별력이 생긴다.
    #
    # 이 모양은 가상이 아니다: 부분 판독은 도착한 만큼의 목록을 실은 채 not-ok
    # 를 보고할 수 있고, 사유를 실은 단면이 목록을 함께 나를 수도 있다.

    def test_a_not_ok_section_that_still_carries_a_list_is_refused(self):
        """`ok` 신호만 걸리는 입력 — 목록이 있고 사유가 없다."""
        verdict = section_refusal({"ok": False, "objects": [{"no": 1}], "truncated": False})
        assert verdict is not None, "목록이 있다고 통과시켰다 — not-ok 는 관측이 아니다"
        assert verdict[0] == SECTION_UNREAD, verdict

    def test_a_reason_bearing_section_that_still_carries_a_list_is_refused(self):
        """`reason` 신호만 걸리는 입력 — 목록이 있고 `ok` 가 없다."""
        verdict = section_refusal({"reason": "부분만 왔다", "objects": [{"no": 1}]})
        assert verdict is not None, "목록이 있다고 통과시켰다 — 사유가 실렸으면 관측이 아니다"
        assert verdict[0] == SECTION_UNREAD, verdict

    def test_a_truncated_section_is_refused_as_truncated(self):
        verdict = section_refusal({"objects": [], "truncated": True})
        assert verdict is not None
        assert verdict[0] == SECTION_TRUNCATED, verdict

    def test_unread_wins_over_truncated_when_both_look_present(self):
        """판정 순서가 계약이다 — 판독 실패 단면에 `truncated` 가 실려 있어도
        절단으로 보고하면 사람이 페이징을 고치러 가서 안 낫는다."""
        verdict = section_refusal({"ok": False, "reason": "못 읽었다", "truncated": True})
        assert verdict is not None
        assert verdict[0] == SECTION_UNREAD, verdict

    def test_a_genuinely_empty_pool_passes(self):
        """대조군 — 콘솔이 답했고 그 답이 「없다」인 경우는 통과해야 한다.
        이게 없으면 술어가 정상적인 첫 임포트를 영영 막아도 안 걸린다."""
        assert section_refusal({"objects": [], "truncated": False}) is None

    def test_a_populated_pool_passes(self):
        assert (
            section_refusal({"objects": [{"no": 1, "name": "Dimmer"}], "truncated": False}) is None
        )


class TestTheDomainWrapperDelegates:
    """`preset_mapper.section_refusal` 은 어휘만 번역한다 — 판정은 공유 술어다.

    이 반이 없으면 위임을 옛 사본으로 되돌려도 아무 검사가 안 빨개진다(뮤테이션
    M7 이 그것을 드러냈다). 사본이 살아나면 술어가 둘이 되고, 갈라진 날 한쪽만
    고쳐진다 — 이 카드가 막으려던 바로 그 형태다.
    """

    def test_every_shared_verdict_maps_to_a_domain_code(self):
        from server.lxseq.preset_mapper import POOL_TRUNCATED, POOL_UNREADABLE

        cases = (
            ({"ok": False, "reason": "x"}, POOL_UNREADABLE),
            ({"reason": "x"}, POOL_UNREADABLE),
            ({}, POOL_UNREADABLE),
            ({"objects": [], "truncated": True}, POOL_TRUNCATED),
        )
        for section, expected in cases:
            verdict = preset_section_refusal(section)
            assert verdict is not None, section
            assert verdict[0] == expected, (section, verdict)

    def test_the_detail_is_carried_verbatim_from_the_shared_predicate(self):
        """문면을 다시 쓰면 두 문면이 갈린다 — 같은 입력에 다른 설명이 나온다."""
        for section, _label in UNREAD_SECTIONS:
            shared = section_refusal(section)
            domain = preset_section_refusal(section)
            assert shared is not None and domain is not None, section
            assert domain[1] == shared[1], (section, domain[1], shared[1])

    def test_a_readable_section_passes_both(self):
        section = {"objects": [], "truncated": False}
        assert section_refusal(section) is None
        assert preset_section_refusal(section) is None


class TestC3TheProducerDoesNotFabricateAReadSection:
    """풀을 못 찾았으면 **못 찾았다고** 말하는 단면을 내야 한다."""

    def test_an_unfound_pool_does_not_yield_a_plan(self):
        """🔴 결함이 난 자리다 — 못 찾은 풀이 빈 풀로 둔갑해 슬롯이 배정됐다."""
        payload = _dispatch_presets(_Port(pools=[]))
        assert payload["pool_no"] is None, payload["pool_no"]
        assert payload["planned"] == [], (
            "풀을 못 찾았는데 계획에 슬롯이 실렸다 — 아무것도 안 잰 것에 대해 "
            "사람이 승인 판단을 하게 된다. " + repr(payload["planned"])
        )

    def test_an_unreadable_pool_list_does_not_yield_a_plan(self):
        """포트가 던진 경우 — 같은 결론이어야 한다."""
        payload = _dispatch_presets(_Port(pools=None))
        assert payload["pool_no"] is None
        assert payload["planned"] == [], repr(payload["planned"])

    def test_the_payload_names_why_rather_than_going_quiet(self):
        """조용한 0건은 「풀을 못 읽었다」와 「넣을 게 없다」를 구별 못 하게 한다."""
        payload = _dispatch_presets(_Port(pools=[]))
        assert payload.get("refusal"), payload
        assert payload.get("pool_error"), payload

    def test_the_control_probe_still_plans_with_a_readable_pool(self):
        """대조군 — 풀이 읽히면 계획이 선다. 없으면 위 검사가 「무조건 0건」과
        구별되지 않는다(툴이 그냥 고장 난 경우)."""
        payload = _dispatch_presets(_Port(pools=[dict(i=1, name="Dimmer")]))
        assert payload["pool_no"] == 1
        assert payload["planned"], payload


class TestC4TheConsumerDoesNotReadUnreadAsEmpty:
    """판독 실패 단면에서 슬롯을 「비었다」고 답하면 안 된다."""

    @staticmethod
    def _map(groups_section):
        return map_groups(
            group_records=_records(),
            patch_rows=_patch_rows(),
            console_fids=[101, 102],
            console_fids_complete=True,
            groups_section=groups_section,
        )

    def test_an_unread_section_never_yields_batches(self):
        """🔴 결함이 난 자리다 — 키 없는 단면이 빈 점유가 되어 슬롯 1..N 이
        비었다고 답했다."""
        for section, label in UNREAD_SECTIONS:
            result = self._map(section)
            assert result.batches == (), (
                label + ": 판독 실패 단면에서 배치가 나왔다 — 콘솔이 답한 적 없는 "
                "슬롯에 그룹을 쓴다"
            )

    def test_an_unread_section_says_so_rather_than_reporting_divergence(self):
        """「어긋났다」로 보고하면 사람은 시트를 고치러 간다 — 실제로는 콘솔을
        못 읽은 것이라 시트를 고쳐도 안 낫는다."""
        for section, label in UNREAD_SECTIONS:
            result = self._map(section)
            assert result.console_read_incomplete is True, label

    def test_a_truncated_section_is_also_not_empty(self):
        """절단된 목록에서 안 보이는 슬롯이 점유돼 있을 수 있다."""
        result = self._map({"objects": [], "truncated": True})
        assert result.batches == ()
        assert result.console_read_incomplete is True

    def test_the_control_probe_still_batches_on_a_real_empty_pool(self):
        """대조군 — **정말로** 빈 풀(읽혔고 절단 안 됨)에서는 계획이 선다.
        이게 없으면 위 검사가 「무조건 안 만든다」와 구별되지 않는다."""
        result = self._map({"objects": [], "truncated": False, "total": 0})
        assert result.batches, "읽힌 빈 풀에서도 계획이 안 섰다 — 술어가 너무 넓다"


def _records():
    from server.lxseq.group_parser import LxseqGroupRecord

    return (LxseqGroupRecord(group_no=1, name="KEY", members_raw="KEY 2대", purpose=""),)


def _patch_rows():
    return (
        {"FID": "101", "Group": "KEY"},
        {"FID": "102", "Group": "KEY"},
    )
