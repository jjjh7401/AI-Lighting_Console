"""카드 t453 — 흰색 큐는 콘솔 컬러 프리셋을 **이름으로** 불러 W 를 켠다.

감독 결정(2026-09-27): 앱이 RGBW 숫자를 박지 않고 콘솔 컬러 프리셋을 이름으로
참조한다(t232 포지션과 같은 방식). 흰색 둘의 콘솔 라벨은 판독값이다
(`.moai/reports/t469/run3_phaser_pools.txt`, 컬러 풀 4 — 슬롯 7
「웜 화이트 (=P2)」, 슬롯 8 「뉴트럴 화이트 (=P3)」).

이 파일이 지키는 것:

1. 흰색 큐의 W 기구는 오늘 줄(RGB + ``W At 0``) **뒤에** ``At Preset`` 한 줄을
   더 받는다(뒤에 온 값이 이긴다). RGB 전용 기구 줄은 그대로다.
2. 흰색이 아닌 큐, W 기구가 없는 곡은 오늘과 같다 — 풀도 읽지 않는다.
3. 라벨을 못 찾으면 지어내지 않는다 — 프리셋 줄 없이 오늘 줄만 내고 사유를 남긴다.
4. 라벨 → 슬롯은 풀 판독으로 찾는다(``#n`` 접미 무시, 여러 슬롯이면 모호로 거절).
"""

from __future__ import annotations

import json

from server.design.song_cue_render import _song_color_value_lines
from server.design.song_plan import TimingPlan
from server.llm.types import ToolResult
from server.orchestrator.tools import ToolExecution
from server.tests.test_song_cue_color_emission import _FIDS, _composition, _Stub
from server.web.session import ChatSession

COOL = "뉴트럴 화이트 (=P3)"
WARM = "웜 화이트 (=P2)"

# t469 run3 판독 원문의 컬러 풀 자식 그대로.
_MEASURED_COLOR_POOL = {
    1: "골드 앰버 (=P1)",
    2: "핫 핑크 (=P4)",
    3: "딥 퍼플 (=P5)",
    4: "터쿼이즈 (=P6)",
    5: "선셋 오렌지 (=P7)",
    6: "딥 블루",
    7: WARM,
    8: COOL,
    32: "Preset 32",
}


# --------------------------------------------------------------------------
# §1~3 — _song_color_value_lines
# --------------------------------------------------------------------------


class TestWhiteCueRecallsThePresetOnWFixtures:
    def test_cool_white_adds_a_preset_line_after_the_w_line(self) -> None:
        cue = _composition(("Cool White", "cyan")).bundle.cues[0]
        before, _ = _song_color_value_lines(cue, (1, 2, 3, 4), frozenset({2, 4}))

        lines, failure = _song_color_value_lines(
            cue, (1, 2, 3, 4), frozenset({2, 4}), {"Cool White": (4, 8)}
        )
        assert failure is None
        assert lines == (*before, "Fixture 2 + 4 ; At Preset 4.8")

    def test_warm_white_uses_its_own_slot(self) -> None:
        cue = _composition(("Warm White", "cyan")).bundle.cues[0]
        lines, failure = _song_color_value_lines(
            cue, (5, 6), frozenset({5, 6}), {"Warm White": (4, 7), "Cool White": (4, 8)}
        )
        assert failure is None
        assert lines[-1] == "Fixture 5 + 6 ; At Preset 4.7"

    def test_a_non_white_cue_is_unchanged(self) -> None:
        cue = _composition(("blue", "cyan")).bundle.cues[0]
        before = _song_color_value_lines(cue, (1, 2), frozenset({2}))
        after = _song_color_value_lines(cue, (1, 2), frozenset({2}), {"Cool White": (4, 8)})
        assert after == before

    def test_no_w_fixtures_means_no_preset_line(self) -> None:
        cue = _composition(("Cool White", "cyan")).bundle.cues[0]
        before = _song_color_value_lines(cue, (1, 2))
        after = _song_color_value_lines(cue, (1, 2), frozenset(), {"Cool White": (4, 8)})
        assert after == before

    def test_unfound_label_keeps_todays_lines_and_reports_why(self) -> None:
        cue = _composition(("Cool White", "cyan")).bundle.cues[0]
        before, _ = _song_color_value_lines(cue, (1, 2), frozenset({2}))
        reason = f"'{COOL}' 라벨의 Color 프리셋을 콘솔에서 찾지 못했습니다"
        lines, failure = _song_color_value_lines(
            cue, (1, 2), frozenset({2}), {"Cool White": reason}
        )
        assert lines == before
        assert failure is not None and COOL in failure


# --------------------------------------------------------------------------
# §4 — 라벨 → 슬롯 판독
# --------------------------------------------------------------------------


class _PoolStub:
    def __init__(self, pool_no, children) -> None:
        self._rig_paths: dict[str, str] = {}
        self._pool_no = pool_no
        self._children = children
        self.paths: list[str] = []

    def _resolve_named_pool_no(self, target_name, *, probe_id):
        assert target_name == "Color"
        return self._pool_no

    def _paged_pool_children(self, path, *, probe_id):
        self.paths.append(path)
        return self._children


class TestWhitePresetSlots:
    def test_measured_pool_resolves_both_whites(self) -> None:
        stub = _PoolStub(4, _MEASURED_COLOR_POOL)
        assert ChatSession._white_preset_slots(stub) == {
            "Warm White": (4, 7),
            "Cool White": (4, 8),
        }
        assert stub.paths == ["DataPool/PresetPools/4"]

    def test_duplicate_suffix_is_ignored(self) -> None:
        pool = {3: f"{COOL}#2", 7: WARM}
        assert ChatSession._white_preset_slots(_PoolStub(4, pool))["Cool White"] == (4, 3)

    def test_missing_label_is_a_reason_not_a_slot(self) -> None:
        pool = {7: WARM}
        slots = ChatSession._white_preset_slots(_PoolStub(4, pool))
        assert slots["Warm White"] == (4, 7)
        assert isinstance(slots["Cool White"], str) and COOL in slots["Cool White"]

    def test_label_in_two_slots_is_ambiguous(self) -> None:
        pool = {7: WARM, 8: COOL, 9: COOL}
        reason = ChatSession._white_preset_slots(_PoolStub(4, pool))["Cool White"]
        assert isinstance(reason, str) and "[8, 9]" in reason

    def test_unresolved_pool_or_unreadable_pool_is_a_reason_for_both(self) -> None:
        for stub in (_PoolStub(None, _MEASURED_COLOR_POOL), _PoolStub(4, None)):
            slots = ChatSession._white_preset_slots(stub)
            assert all(isinstance(v, str) for v in slots.values())
            assert set(slots) == {"Warm White", "Cool White"}


# --------------------------------------------------------------------------
# 실제 _reviewed_song_commands 경로
# --------------------------------------------------------------------------


class _WhiteStub(_Stub):
    def __init__(self, slots) -> None:
        super().__init__()
        self._slots = slots
        self.lookups = 0

    def _white_preset_slots(self):
        self.lookups += 1
        return self._slots


def _run(composition, stub, w_fids):
    return ChatSession._reviewed_song_commands(
        stub,
        composition,
        sequence_no=210,
        preset_start=1,
        fids=list(_FIDS),
        timing=TimingPlan.timecode(9),
        layer_mapping=(),
        w_fids=w_fids,
    )


class TestSongFlow:
    def test_white_cue_on_w_rig_recalls_the_preset(self) -> None:
        stub = _WhiteStub({"Cool White": (4, 8), "Warm White": (4, 7)})
        commands = _run(
            _composition(("blue", "cyan"), ("Cool White", "cyan")), stub, frozenset({2, 4})
        )
        assert stub.lookups == 1
        recalls = [c for c in commands if "At Preset 4." in c]
        assert recalls == ["Fixture 2 + 4 ; At Preset 4.8"]
        # W 누수 방지 — 흰색 아닌 큐의 W 기구 줄은 여전히 W 0 을 적는다.
        assert sum(1 for c in commands if c.endswith("Attribute 'ColorRGB_W' At 0")) == 2

    def test_no_white_cue_reads_no_pool(self) -> None:
        stub = _WhiteStub({})
        _run(_composition(("blue", "cyan"), ("amber", "red")), stub, frozenset({2, 4}))
        assert stub.lookups == 0

    def test_no_w_fixtures_reads_no_pool(self) -> None:
        stub = _WhiteStub({})
        _run(_composition(("Cool White", "cyan")), stub, frozenset())
        assert stub.lookups == 0

    def test_unfound_label_is_disclosed_and_nothing_is_invented(self) -> None:
        reason = f"'{COOL}' 라벨의 Color 프리셋을 콘솔에서 찾지 못했습니다"
        stub = _WhiteStub({"Cool White": reason, "Warm White": (4, 7)})
        commands = _run(_composition(("Cool White", "cyan")), stub, frozenset({2, 4}))
        assert not any("At Preset 4." in c for c in commands)
        assert any(COOL in r for r in stub._last_color_failures.values())


# --------------------------------------------------------------------------
# 경계 — 진짜 판독 메서드(`_resolve_named_pool_no` → `_paged_pool_children`)를
# t469 실측 응답 모양으로 태운다.
# --------------------------------------------------------------------------

# `.moai/reports/t469/run3_phaser_pools.txt` 9행 응답(id 만 뺐다).
_T469_COLOR_POOL_REPLY = {
    "children": [{"class": "Preset", "i": i, "name": n} for i, n in _MEASURED_COLOR_POOL.items()],
    "kind": "state",
    "node": {"childCount": 9, "class": "Presets", "enumeration": "ok", "name": "Color"},
    "offset": 0,
    "ok": True,
    "path": "ShowData/DataPools/Default/PresetPools/4",
    "truncated": False,
    "v": 1,
}
_POOL_LIST_REPLY = {
    "children": [{"i": 2, "name": "Position"}, {"i": 4, "name": "Color"}],
    "node": {"childCount": 2},
    "truncated": False,
}


class _PathRegistry:
    def __init__(self, replies) -> None:
        self._replies = replies
        self.paths: list[str] = []

    def dispatch(self, call, context=None):
        path = call.arguments["path"]
        self.paths.append(path)
        return ToolExecution(
            ToolResult(
                tool_call_id=call.id, name=call.name, content=json.dumps(self._replies[path])
            )
        )


class _RealReadHost:
    def __init__(self, replies) -> None:
        self._rig_paths: dict[str, str] = {}
        self._registry = _PathRegistry(replies)

    _resolve_named_pool_no = ChatSession._resolve_named_pool_no
    _paged_pool_children = ChatSession._paged_pool_children
    _white_preset_slots = ChatSession._white_preset_slots


class TestRealReadPath:
    def test_measured_reply_resolves_through_the_real_readers(self) -> None:
        host = _RealReadHost(
            {
                "DataPool/PresetPools": _POOL_LIST_REPLY,
                "DataPool/PresetPools/4": _T469_COLOR_POOL_REPLY,
            }
        )
        assert host._white_preset_slots() == {"Warm White": (4, 7), "Cool White": (4, 8)}
        assert host._registry.paths == ["DataPool/PresetPools", "DataPool/PresetPools/4"]
