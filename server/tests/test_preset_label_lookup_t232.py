"""t232 — Position 프리셋을 번호 산술이 아니라 라벨로 찾는다.

**판독(``.moai/reports/t232/verdict.md``)**: 감독 확정 곡 큐, 대화 포지션
수정, 포지션 FX 세 경로 모두 ``preset_start + BASIC_POSITION_SEQUENCE.index(
label)`` (또는 FX 쪽은 ``fx_preset_start + offset``) 로 슬롯 번호를 지었다 —
그 슬롯이 실제로 그 라벨인지는 한 번도 확인하지 않았다. 포지션 풀의 연속
10칸이 기본 포지션 10종이 아니면(예: 시트 프리셋이 그 자리를 채운 쇼파일)
조용히 다른 프리셋을 불렀다.

이 파일이 지키는 것:

1. ``ChatSession._resolve_position_preset_labels`` — 라벨 집합을 콘솔
   판독 1회로 슬롯에 매핑한다. 단일 매치, ``#n`` 중복 접미 관용, 구간 내
   우선 선택, 모호성 거부, 라벨 부재 거부, 풀 판독 실패 거부(사유가 라벨
   부재와 다름) 를 각각 잰다.
2. 세 소비 경로(감독 확정 곡 큐 / 대화 포지션 수정 / 포지션 FX) 가 모두
   이 헬퍼를 타서, **정상 쇼파일(포지션 풀의 연속 10칸이 기본 포지션
   10종)** 에서는 옛 산술과 바이트 동일한 프리셋 번호를 낸다는 것.
3. 같은 세 경로가 **비정상 쇼파일**(그 10칸이 다른 프리셋으로 채워진
   경우) 에서는 라벨이 실제로 가리키는 슬롯을 부른다 — 옛 산술이 불렀을
   엉뚱한 슬롯이 아니다.
"""

from __future__ import annotations

import json

import pytest

from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import (
    AccentDecision,
    ApprovalState,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
)
from server.llm.types import ToolCall, ToolResult
from server.orchestrator.tools import ToolExecution
from server.spatial.pointing import (
    BASIC_POSITION_SEQUENCE,
    FX_POSITION_SEQUENCE,
    SpatialPointingError,
    preset_recall_command,
)
from server.spatial.position_fx import position_fx_commands, required_position_labels
from server.web.session import ChatSession

_FIDS = (1, 2, 3, 4)


# --------------------------------------------------------------------------
# 콘솔 대역 — `_resolve_position_preset_labels`/`_position_preset_pool_
# children`/`_paged_pool_children`가 실제로 쓰는 자리만 채운다.
# --------------------------------------------------------------------------


def _pool_payload(entries: dict[int, str]) -> dict:
    return {"children": [{"i": slot, "name": name} for slot, name in entries.items()]}


class _FakeRegistry:
    """``query_state`` 하나만 답한다. ``payload=None`` 이면 판독 실패."""

    def __init__(self, payload: dict | None) -> None:
        self._payload = payload
        self.calls: list[ToolCall] = []

    def dispatch(self, call: ToolCall, context=None) -> ToolExecution:
        self.calls.append(call)
        if self._payload is None:
            return ToolExecution(
                ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    content="responder unreachable",
                    is_error=True,
                )
            )
        return ToolExecution(
            ToolResult(tool_call_id=call.id, name=call.name, content=json.dumps(self._payload))
        )


class _PoolHost:
    """``_resolve_position_preset_labels`` 가 실제로 쓰는 두 자리(``_registry``,
    ``_rig_paths``)만 채운 대역 — 나머지는 ``ChatSession``의 진짜 메서드를
    그대로 묶는다(``_reviewed_song_timing_commands`` 대역과 같은 관행)."""

    def __init__(self, payload: dict | None) -> None:
        self._rig_paths: dict[str, str] = {}
        self.registry = _FakeRegistry(payload)
        self._registry = self.registry

    _position_preset_pool_children = ChatSession._position_preset_pool_children
    _paged_pool_children = ChatSession._paged_pool_children
    _resolve_position_preset_labels = ChatSession._resolve_position_preset_labels


def _resolve(payload: dict | None, labels, *, start: int, span: int) -> dict[str, int]:
    host = _PoolHost(payload)
    return host._resolve_position_preset_labels(labels, start=start, span=span)


# --------------------------------------------------------------------------
# 1. 헬퍼 단위 — 해석·`#n`·중복·모호성·부재·판독 실패
# --------------------------------------------------------------------------


class TestResolution:
    def test_a_single_match_resolves(self):
        pool = _pool_payload({21: "Home", 22: "Wall"})
        resolved = _resolve(pool, ["Home"], start=21, span=10)
        assert resolved == {"Home": 21}

    def test_a_hash_suffix_duplicate_name_is_stripped(self):
        pool = _pool_payload({21: "Home#2"})
        resolved = _resolve(pool, ["Home"], start=21, span=10)
        assert resolved == {"Home": 21}

    def test_multiple_labels_resolve_in_one_pool_read(self):
        pool = _pool_payload({21: "Home", 25: "Vocal DSC", 30: "Ring In"})
        registry_payload = pool
        host = _PoolHost(registry_payload)
        resolved = host._resolve_position_preset_labels(
            ["Home", "Vocal DSC", "Ring In"], start=21, span=10
        )
        assert resolved == {"Home": 21, "Vocal DSC": 25, "Ring In": 30}
        # 배치 — 라벨이 몇 개든 풀 판독은 한 번(페이지 1개)뿐이어야 한다.
        query_calls = [c for c in host.registry.calls if c.name == "query_state"]
        assert len(query_calls) == 1

    def test_a_duplicate_inside_the_span_wins(self):
        # 'Home'이 구간 밖(99)과 구간 안(21) 둘 다에 있다 — 구간 안을 쓴다.
        pool = _pool_payload({21: "Home", 99: "Home"})
        resolved = _resolve(pool, ["Home"], start=21, span=10)
        assert resolved == {"Home": 21}

    def test_none_in_span_multiple_outside_is_ambiguous(self):
        pool = _pool_payload({50: "Home", 60: "Home"})
        with pytest.raises(SpatialPointingError, match="특정할 수 없습니다"):
            _resolve(pool, ["Home"], start=21, span=10)

    def test_two_in_span_is_also_ambiguous(self):
        pool = _pool_payload({21: "Home", 22: "Home"})
        with pytest.raises(SpatialPointingError, match="특정할 수 없습니다"):
            _resolve(pool, ["Home"], start=21, span=10)

    def test_an_absent_label_is_refused(self):
        pool = _pool_payload({21: "Wall"})
        with pytest.raises(SpatialPointingError, match="찾지 못했습니다"):
            _resolve(pool, ["Home"], start=21, span=10)

    def test_an_unreadable_pool_is_refused_with_a_distinct_reason(self):
        # 풀 판독 실패의 사유는 라벨 부재의 사유와 달라야 한다 — 운영자가
        # "저장 안 함"과 "콘솔이 안 읽힘"을 구별할 수 있어야 한다.
        with pytest.raises(SpatialPointingError, match="읽지 못해") as absent_excinfo:
            _resolve(None, ["Home"], start=21, span=10)
        with pytest.raises(SpatialPointingError, match="찾지 못했습니다") as unreadable_excinfo:
            _resolve(_pool_payload({}), ["Home"], start=21, span=10)
        assert str(absent_excinfo.value) != str(unreadable_excinfo.value)


# --------------------------------------------------------------------------
# 2. 감독 확정 곡 큐 — `_reviewed_song_commands`
# --------------------------------------------------------------------------


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 41)
    ]
    return build_rig_profile(
        patch=patch, groups={}, coords=[], declared_layers={"key": [1, 2], "back": [3, 4]}
    )


def _section(index: int, label: str, start_ms: int, position: str):
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=3, source="section_mood"),
        palette=PaletteDecision(colors=("blue", "cyan"), source="director"),
        position=PositionDecision(preset=position, source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), disabled=(), density=0),
        accent=AccentDecision(accents=()),
        cue_number=100 + index,
    )


def _composition(*positions: str):
    sections = tuple(
        _section(i, f"Section {i}", (i - 1) * 20_000, position)
        for i, position in enumerate(positions, start=1)
    )
    plan = UnifiedSongLightingPlan(
        song_title="t232 Position Lookup Test",
        sequence_name="Position Seq",
        sections=sections,
        timing=TimingPlan.timecode(9),
        music_profile=MusicProfile(bpm=120.0, palette=("blue", "warm white")),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="director"),
    )
    return compose_song_cue_bundle(plan)


class _SongStub:
    """``_reviewed_song_commands``가 실제로 쓰는 자리만 채운 대역."""

    def __init__(self, payload: dict | None) -> None:
        self._last_phaser_failures: dict[str, str] = {}
        self._last_color_failures: dict[str, str] = {}
        self._rig_paths: dict[str, str] = {}
        self._registry = _FakeRegistry(payload)

    def _phaser_slots_for_bundle(self, bundle):
        return {}, {}

    _reviewed_song_timing_commands = ChatSession._reviewed_song_timing_commands
    _position_preset_pool_children = ChatSession._position_preset_pool_children
    _paged_pool_children = ChatSession._paged_pool_children
    _resolve_position_preset_labels = ChatSession._resolve_position_preset_labels


def _song_commands(composition, *, payload: dict | None, preset_start: int = 21):
    stub = _SongStub(payload)
    return ChatSession._reviewed_song_commands(
        stub,
        composition,
        sequence_no=210,
        preset_start=preset_start,
        fids=list(_FIDS),
        timing=TimingPlan.timecode(9),
        layer_mapping=(),
    )


def _recall_lines(commands):
    return [line for line in commands if "At Preset" in line]


class TestSongCueByteIdentity:
    def test_case_c_contiguous_pool_matches_the_old_arithmetic(self):
        # C: 콘솔 포지션 풀 21~30에 기본 포지션 10종이 순서대로 저장돼 있다
        # — 옛 산술(preset_start + index)과 바이트 동일해야 한다.
        pool = _pool_payload({21 + i: name for i, name in enumerate(BASIC_POSITION_SEQUENCE)})
        composition = _composition("Center", "Ring In")
        commands = _song_commands(composition, payload=pool)
        expected_center = 21 + BASIC_POSITION_SEQUENCE.index("Center")
        expected_ring_in = 21 + BASIC_POSITION_SEQUENCE.index("Ring In")
        recalls = _recall_lines(commands)
        assert any(f"At Preset 2.{expected_center}" in line for line in recalls)
        assert any(f"At Preset 2.{expected_ring_in}" in line for line in recalls)

    def test_case_d_noncontiguous_pool_finds_the_real_label(self):
        # D: 21~30 칸은 시트 프리셋('POS.. 시트')이 차지하고, 진짜 'Center'
        # 는 다른 자리(41)에 있다 — 옛 산술은 41번이 아니라 21+3=24를
        # 불렀을 것이다. 라벨 조회는 41을 불러야 한다.
        pool = _pool_payload({21 + i: f"POS{i:02d} 시트" for i in range(10)})
        pool["children"].append({"i": 41, "name": "Center"})
        composition = _composition("Center")
        commands = _song_commands(composition, payload=pool)
        recalls = _recall_lines(commands)
        assert any("At Preset 2.41" in line for line in recalls)
        old_wrong_slot = 21 + BASIC_POSITION_SEQUENCE.index("Center")
        assert not any(f"At Preset 2.{old_wrong_slot}" in line for line in recalls)

    def test_case_d_missing_label_refuses_before_any_write(self):
        # 'Center'가 어디에도 없으면 조용히 다른 슬롯을 부르지 말고 거부한다.
        pool = _pool_payload({21 + i: f"POS{i:02d} 시트" for i in range(10)})
        composition = _composition("Center")
        with pytest.raises(SpatialPointingError, match="'Center'"):
            _song_commands(composition, payload=pool)


# --------------------------------------------------------------------------
# 3. 대화 포지션 수정 — `_merge_timeline_cue_position`이 라벨 하나를
#    해석해 `preset_recall_command`에 넘기는 자리(핵심 산술만 재현).
# --------------------------------------------------------------------------


class TestChatPositionEditByteIdentity:
    def test_case_c_contiguous_pool_matches_the_old_arithmetic(self):
        pool = _pool_payload({21 + i: name for i, name in enumerate(BASIC_POSITION_SEQUENCE)})
        resolved = _resolve(pool, ["Center"], start=21, span=len(BASIC_POSITION_SEQUENCE))
        expected = 21 + BASIC_POSITION_SEQUENCE.index("Center")
        assert resolved["Center"] == expected
        assert preset_recall_command([20, 26], resolved["Center"]) == (
            f"Fixture 20 + 26 ; At Preset 2.{expected}"
        )

    def test_case_d_noncontiguous_pool_finds_the_real_label(self):
        pool = _pool_payload({21 + i: f"POS{i:02d} 시트" for i in range(10)})
        pool["children"].append({"i": 41, "name": "Center"})
        resolved = _resolve(pool, ["Center"], start=21, span=len(BASIC_POSITION_SEQUENCE))
        assert resolved["Center"] == 41
        old_wrong_slot = 21 + BASIC_POSITION_SEQUENCE.index("Center")
        assert resolved["Center"] != old_wrong_slot

    def test_case_d_absent_label_refuses(self):
        pool = _pool_payload({21 + i: f"POS{i:02d} 시트" for i in range(10)})
        with pytest.raises(SpatialPointingError, match="'Center'"):
            _resolve(pool, ["Center"], start=21, span=len(BASIC_POSITION_SEQUENCE))


# --------------------------------------------------------------------------
# 4. 포지션 FX — `required_position_labels` + `_resolve_position_preset_
#    labels` + `position_fx_commands`.
# --------------------------------------------------------------------------


class TestPositionFxByteIdentity:
    def _resolved_numbers(self, pool, effect: str, *, start: int = 41):
        needed = required_position_labels(effect)
        return needed, _resolve(pool, needed, start=start, span=len(FX_POSITION_SEQUENCE))

    def test_case_c_ab_effect_matches_the_old_arithmetic(self):
        pool = _pool_payload({41 + i: name for i, name in enumerate(FX_POSITION_SEQUENCE)})
        needed, numbers = self._resolved_numbers(pool, "sweep")
        commands = position_fx_commands(
            "sweep", fids=(11, 12, 13), preset_numbers=numbers, sequence_no=201, label="My FX"
        )
        offset_a = FX_POSITION_SEQUENCE.index(needed[0])
        offset_b = FX_POSITION_SEQUENCE.index(needed[1])
        assert commands == (
            "ChangeDestination Root",
            "ClearAll",
            f"Fixture 11 + 12 + 13 ; At Preset 2.{41 + offset_a}",
            f"Store Sequence 201 Cue 1 '{needed[0]}' CueFade 2",
            "ClearAll",
            f"Fixture 11 + 12 + 13 ; At Preset 2.{41 + offset_b}",
            f"Store Sequence 201 Cue 2 '{needed[1]}' CueFade 2 /Merge",
            "ClearAll",
            "Label Sequence 201 'My FX'",
        )

    def test_case_c_base_effect_matches_the_old_arithmetic(self):
        pool = _pool_payload({41 + i: name for i, name in enumerate(FX_POSITION_SEQUENCE)})
        needed, numbers = self._resolved_numbers(pool, "circle")
        commands = position_fx_commands(
            "circle", fids=(11, 12, 13), preset_numbers=numbers, sequence_no=201, label="My FX"
        )
        offset = FX_POSITION_SEQUENCE.index(needed[0])
        assert commands[2] == f"Fixture 11 + 12 + 13 ; At Preset 2.{41 + offset}"

    def test_case_d_noncontiguous_pool_finds_the_real_label(self):
        # D: 41~50 칸은 다른 프리셋으로 차 있고, 'Sweep L'/'Sweep R'은 다른
        # 자리(61, 62)에 있다.
        pool = _pool_payload({41 + i: f"OTHER{i}" for i in range(10)})
        pool["children"].append({"i": 61, "name": "Sweep L"})
        pool["children"].append({"i": 62, "name": "Sweep R"})
        needed, numbers = self._resolved_numbers(pool, "sweep")
        assert numbers == {"Sweep L": 61, "Sweep R": 62}
        commands = position_fx_commands(
            "sweep", fids=(11, 12, 13), preset_numbers=numbers, sequence_no=201, label="My FX"
        )
        assert "At Preset 2.61" in commands[2]
        assert "At Preset 2.41" not in "".join(commands)

    def test_case_d_missing_label_refuses(self):
        pool = _pool_payload({41 + i: f"OTHER{i}" for i in range(10)})
        with pytest.raises(SpatialPointingError, match="Sweep"):
            self._resolved_numbers(pool, "sweep")
