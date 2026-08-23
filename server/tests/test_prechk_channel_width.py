"""t23 — 픽스처 슬롯에서 실측 채널폭까지의 4단계 조인.

이 검사의 판별력은 표본에 달려 있다. TotalFootprint 와 DMXChannels 는 단순한
장비에서 값이 같다. 그래서 단순 장비만 표본에 넣으면 틀린 지표로 짜도 초록이다 —
검사가 도는데 판별력이 0 이 된다. 그래서 이 페이크 콘솔은 16비트 채널이 있어
두 지표가 갈리는 타입을 반드시 포함한다(폭 25 vs 채널 수 23).

표본 값은 t4(2026-08-22)의 실측을 승계한 것이며 이 카드가 다시 잰 값이 아니다.

파싱 함정 둘도 여기서 못박는다. 두 표시 문자열은 숫자 위치가 반대이고,
모드 이름은 숫자로 시작할 수 있다.
"""

from __future__ import annotations

import pytest

from server.prechk.channel_width import (
    FixtureModeRef,
    parse_mode_reference,
    resolve_widths,
)
from server.prechk.mode_read import read_type_mode_widths

_ROOT = "Patch/FixtureTypes"

# 승계 값(t4 2026-08-22). 이 카드가 재측정하지 않았다.
#   16비트 타입은 폭과 채널 수가 갈린다 — 이 표본의 판별력이 거기서 나온다.
_SIXTEEN_BIT_FOOTPRINT = 25
_SIXTEEN_BIT_CHANNELS = 23
_SIMPLE_FOOTPRINT = 12
_SIMPLE_CHANNELS = 12


class _FakeConsole:
    """4단계 조인이 닿는 노드만 갖춘 최소 콘솔."""

    #: 타입 슬롯 -> (이름, 모드슬롯 -> (모드이름, 폭, 채널수))
    TYPES = {
        10: (
            "Robin Esprite",
            {3: ("Direct", _SIXTEEN_BIT_FOOTPRINT, _SIXTEEN_BIT_CHANNELS)},
        ),
        20: (
            "Simple PAR",
            {4: ("4 channel", _SIMPLE_FOOTPRINT, _SIMPLE_CHANNELS)},
        ),
    }

    def query_state(self, path: str) -> dict:
        if path == _ROOT:
            children = [
                {"i": slot, "name": name} for slot, (name, _modes) in sorted(self.TYPES.items())
            ]
            return self._listing(path, children)
        parts = path.split("/")
        type_slot = int(parts[2])
        _name, modes = self.TYPES[type_slot]
        children = [
            {"i": slot, "name": mode_name} for slot, (mode_name, _w, _c) in sorted(modes.items())
        ]
        return self._listing(path, children)

    def query_property(self, path: str, property_name: str) -> dict:
        parts = path.split("/")
        type_slot = int(parts[2])
        mode_slot = int(parts[4])
        _name, modes = self.TYPES[type_slot]
        _mode_name, footprint, channels = modes[mode_slot]
        # 두 이름 모두에 답한다. 그래야 틀린 지표를 물었을 때 오류가 아니라
        # 틀린 숫자가 돌아오고, 뮤테이션이 그 차이로 잡힌다.
        value = footprint if property_name == "TotalFootprint" else channels
        return {"ok": True, "path": path, "property": property_name, "value": str(value)}

    @staticmethod
    def _listing(path: str, children: list[dict]) -> dict:
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(children)},
            "children": children,
        }


@pytest.fixture
def type_reads() -> dict:
    console = _FakeConsole()
    return {
        name: read_type_mode_widths(console, console, root=_ROOT, type_name=name)
        for name in ("Robin Esprite", "Simple PAR")
    }


class TestTheSampleCanDiscriminate:
    """판별력 검사 — 이게 없으면 아래 검사들이 공허하다."""

    def test_the_two_metrics_actually_diverge_in_this_sample(self) -> None:
        assert _SIXTEEN_BIT_FOOTPRINT != _SIXTEEN_BIT_CHANNELS, (
            "표본의 두 지표가 같으면 틀린 지표로 짜도 초록이다 — 16비트 장비를 반드시 포함해야 한다"
        )

    def test_a_simple_fixture_alone_would_not_discriminate(self) -> None:
        assert _SIMPLE_FOOTPRINT == _SIMPLE_CHANNELS, (
            "단순 장비는 두 지표가 같다 — 그것만으로는 판별할 수 없다는 사실을 표본 안에 남긴다"
        )


class TestWidthComesFromTheFootprintNotTheChannelCount:
    """폭은 TotalFootprint 에서 온다. DMXChannels 는 16비트를 한 번만 센다."""

    def test_a_sixteen_bit_fixture_resolves_to_the_footprint(self, type_reads) -> None:
        resolution = resolve_widths(
            [FixtureModeRef(slot=306, type_name="Robin Esprite", mode_raw="3 Direct")],
            type_reads,
        )
        assert resolution.widths[306] == _SIXTEEN_BIT_FOOTPRINT
        assert resolution.widths[306] != _SIXTEEN_BIT_CHANNELS, (
            "채널 수가 나왔다면 FOOTPRINT_PROPERTY 가 DMXChannels 로 바뀐 것이다"
        )

    def test_a_simple_fixture_resolves_too(self, type_reads) -> None:
        resolution = resolve_widths(
            [FixtureModeRef(slot=101, type_name="Simple PAR", mode_raw="4 4 channel")],
            type_reads,
        )
        assert resolution.widths[101] == _SIMPLE_FOOTPRINT
        assert resolution.unresolved == {}


class TestTheTwoDisplayStringsPutTheirNumberOnOppositeSides:
    """FixtureType 은 숫자가 뒤, Mode 는 숫자가 앞이다."""

    def test_a_mode_name_may_begin_with_a_digit(self) -> None:
        parsed = parse_mode_reference("4 4 channel")
        assert parsed is not None
        assert (parsed.slot, parsed.name) == (4, "4 channel"), (
            "한 번만 갈라야 한다 — 슬롯 44 도, 이름 channel 도 아니다"
        )

    def test_another_digit_leading_name(self) -> None:
        parsed = parse_mode_reference("2 9 channel")
        assert parsed is not None
        assert (parsed.slot, parsed.name) == (2, "9 channel")

    def test_a_plain_name_parses(self) -> None:
        parsed = parse_mode_reference("3 Direct")
        assert parsed is not None
        assert (parsed.slot, parsed.name) == (3, "Direct")

    def test_a_string_without_a_name_half_is_not_a_mode_reference(self) -> None:
        assert parse_mode_reference("12") is None

    def test_a_string_without_a_leading_slot_is_not_a_mode_reference(self) -> None:
        assert parse_mode_reference("Direct") is None


class TestTheSelfCheckFailsLoudly:
    """모드 이름과 도달한 노드의 이름이 어긋나면 폭을 내지 않는다."""

    def test_a_name_mismatch_yields_no_width(self, type_reads) -> None:
        resolution = resolve_widths(
            [FixtureModeRef(slot=606, type_name="Robin Esprite", mode_raw="3 Indirect")],
            type_reads,
        )
        assert 606 not in resolution.widths, (
            "이름이 어긋났는데 폭을 냈다 — 다른 모드의 폭으로 주소를 잡게 된다"
        )
        assert resolution.unresolved[606] == "mode_name_mismatch"

    def test_an_unparsable_mode_is_reported_not_dropped(self, type_reads) -> None:
        resolution = resolve_widths(
            [FixtureModeRef(slot=424, type_name="Robin Esprite", mode_raw="Direct")],
            type_reads,
        )
        assert resolution.unresolved[424] == "mode_unparsed"

    def test_an_absent_mode_slot_is_reported(self, type_reads) -> None:
        resolution = resolve_widths(
            [FixtureModeRef(slot=9, type_name="Robin Esprite", mode_raw="7 Direct")],
            type_reads,
        )
        assert resolution.unresolved[9] == "mode_slot_absent"
