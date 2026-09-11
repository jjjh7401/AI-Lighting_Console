"""t348 — 리그가 못 조정하는 축을 쓰려는 룩은 저장 계획에서 보류된다.

두 층을 따로 시험한다.

1. ``_plan_stores`` 의 새 rung — 주입된 :class:`AxisPresence` 하나만 보고 판단한다.
   가짜 판독기를 쓰는 이유는 이 층의 계약이 프로토콜 하나라서다(리그 판독 사슬을
   끌고 오면 시험하는 대상이 흐려진다).
2. :class:`server.looks.rig_axes.RigAxisPresence` — 실제 능력 판독을
   ``present``/``absent``/``unread`` 로 읽는 어댑터.

콘솔 접촉 0. 숫자 비교 0 — 이 카드는 축의 **존재**만 묻는다.
"""

from __future__ import annotations

import pytest

from server.design.capability_join import FixtureCapability, RigCapabilities
from server.looks.instantiate import (
    AXIS_ABSENT,
    CONFLICT,
    NO_FREE_SLOT,
    POOL_UNRESOLVED,
    PRESENCE_ABSENT,
    PRESENCE_PRESENT,
    PRESENCE_UNREAD,
    instantiate_look,
)
from server.looks.rig_axes import MEASURED_ATTRIBUTE_SPELLINGS, RigAxisPresence
from server.prechk.capability_read import AxisRange
from server.tests.test_looks_instantiate import (
    DEFAULT_POOL_NAMES,
    _groups,
    _look,
    _pools,
    _preset,
)

RIG = _groups((11, "백라이트"))


class _FakeAxes:
    """주어진 속성만 부재로, 나머지는 있음으로 답하는 판독기."""

    def __init__(self, *absent: str, unread: tuple[str, ...] = ()) -> None:
        self._absent = {a.casefold() for a in absent}
        self._unread = {u.casefold() for u in unread}

    def presence(self, attribute: str) -> str:
        key = attribute.strip().casefold()
        if key in self._unread:
            return PRESENCE_UNREAD
        return PRESENCE_ABSENT if key in self._absent else PRESENCE_PRESENT


def _zoom_look():
    """Focus family 는 Zoom 하나, Beam family 는 Iris 하나로 갈린다."""
    return _look(attributes=(("Dimmer", 80), ("Zoom", 35), ("Iris", 100)))


def _plan(look, axes=None):
    return instantiate_look(look, groups_section=RIG, preset_pools_section=_pools(), axes=axes)


def _skip(report, family: str):
    hits = [s for s in report.skipped if s.family == family]
    assert len(hits) == 1, f"{family}: {report.to_dict()['skipped']}"
    return hits[0]


def _families_stored(report) -> set[str]:
    return {c.family for c in report.created}


# -- the rung ------------------------------------------------------------------


class TestAxisAbsentHold:
    def test_a_zoom_look_against_a_rig_without_zoom_is_held_with_its_own_reason(self):
        report = _plan(_zoom_look(), axes=_FakeAxes("Zoom"))
        hold = _skip(report, "Focus")
        # 사유 문자열을 단언한다: 「건너뜀」만 보면 이 보류와 NO_FREE_SLOT·CONFLICT 를
        # 구별할 수 없고, 그 셋은 고칠 곳이 서로 다르다.
        assert hold.reason == AXIS_ABSENT
        assert hold.reason not in (NO_FREE_SLOT, CONFLICT, POOL_UNRESOLVED)
        assert "Zoom" in hold.detail
        assert "Focus" not in _families_stored(report)

    def test_the_hold_does_not_swallow_the_other_families(self):
        report = _plan(_zoom_look(), axes=_FakeAxes("Zoom"))
        assert {"Dimmer", "Beam"} <= _families_stored(report)
        assert report.skipped_count == 1
        assert report.complete is False

    def test_iris_is_held_the_same_way_so_the_rung_is_not_zoom_only(self):
        report = _plan(_zoom_look(), axes=_FakeAxes("Iris"))
        hold = _skip(report, "Beam")
        assert hold.reason == AXIS_ABSENT
        assert "Iris" in hold.detail
        assert "Beam" not in _families_stored(report)
        assert "Focus" in _families_stored(report)

    def test_the_detail_names_the_attribute_that_drove_the_hold_not_the_family(self):
        # Color family 는 세 속성을 나른다 — 어느 것이 보류를 불렀는지 문면이 답해야
        # 한다. family 이름만 있으면 셋 중 무엇이 없는지 알 수 없다.
        look = _look(attributes=(("ColorRGB_R", 100), ("ColorRGB_G", 25), ("ColorRGB_B", 0)))
        hold = _skip(_plan(look, axes=_FakeAxes("ColorRGB_G")), "Color")
        assert "ColorRGB_G" in hold.detail

    def test_no_console_command_is_emitted_for_a_held_family(self):
        report = _plan(_zoom_look(), axes=_FakeAxes("Zoom"))
        assert all("Zoom" not in c or "Store" not in c for c in report.commands)
        stores = [c for c in report.commands if c.startswith("Store Preset")]
        # Dimmer + Beam 만 저장된다.
        assert len(stores) == 2


class TestControlProbe:
    """보류가 범위 밖으로 새지 않는다는 것을 재는 대조군."""

    def test_the_same_look_against_a_rig_that_has_zoom_still_plans_its_store(self):
        report = _plan(_zoom_look(), axes=_FakeAxes())
        assert [s.reason for s in report.skipped] == []
        assert "Focus" in _families_stored(report)
        assert report.complete is True

    def test_an_unrelated_absence_does_not_hold_the_zoom_store(self):
        report = _plan(_zoom_look(), axes=_FakeAxes("Prism1"))
        assert "Focus" in _families_stored(report)
        assert report.skipped_count == 0


class TestUnreadIsNotAbsent:
    def test_with_no_lookup_at_all_the_plan_is_what_it_is_today(self):
        without = _plan(_zoom_look())
        assert without.skipped_count == 0
        assert _families_stored(without) == {"Dimmer", "Beam", "Focus"}
        # 기본값이 보류를 시작하면 이 단언이 깨진다.
        assert AXIS_ABSENT not in [s.reason for s in without.skipped]

    def test_the_default_and_a_present_everything_lookup_agree_exactly(self):
        assert _plan(_zoom_look()).to_dict() == _plan(_zoom_look(), axes=_FakeAxes()).to_dict()

    def test_an_unread_axis_does_not_hold(self):
        report = _plan(_zoom_look(), axes=_FakeAxes(unread=("Zoom",)))
        assert report.skipped_count == 0
        assert "Focus" in _families_stored(report)


class TestExistingReasonsUnchanged:
    """기존 rung 들이 그대로 발사되는가 — 판독기를 들고서도."""

    def test_pool_unresolved_still_fires(self):
        renamed = tuple((no, "Focus Backup" if n == "Focus" else n) for no, n in DEFAULT_POOL_NAMES)
        report = instantiate_look(
            _zoom_look(),
            groups_section=RIG,
            preset_pools_section=_pools(renamed),
            axes=_FakeAxes(),
        )
        assert _skip(report, "Focus").reason == POOL_UNRESOLVED

    def test_conflict_still_fires(self):
        look = _zoom_look()
        report = instantiate_look(
            look,
            groups_section=RIG,
            preset_pools_section=_pools(contents={6: [_preset(1, look.display_name)]}),
            axes=_FakeAxes(),
        )
        assert _skip(report, "Focus").reason == CONFLICT

    def test_an_absent_axis_outranks_no_free_slot_and_says_so(self):
        # 같은 저장이 두 이유로 막힐 때 축 부재가 이긴다: 고칠 곳이 슬롯이 아니라
        # 장비이기 때문이다.
        report = instantiate_look(
            _zoom_look(),
            groups_section=RIG,
            preset_pools_section=_pools(contents={6: [_preset(None, "이름 없는 프리셋")]}),
            axes=_FakeAxes("Zoom"),
        )
        assert _skip(report, "Focus").reason == AXIS_ABSENT

    def test_that_same_shape_reports_no_free_slot_when_the_axis_is_present(self):
        report = instantiate_look(
            _zoom_look(),
            groups_section=RIG,
            preset_pools_section=_pools(contents={6: [_preset(None, "이름 없는 프리셋")]}),
            axes=_FakeAxes(),
        )
        assert _skip(report, "Focus").reason == NO_FREE_SLOT


# -- the rig adapter -----------------------------------------------------------


def _fixture(fid: int, type_name: str, *attributes: str, gaps: tuple[str, ...] = ()):
    return FixtureCapability(
        fid=fid,
        type_slot=11,
        type_name=type_name,
        mode_slot=1,
        mode_name="Mode 1",
        mode_width=32,
        channel_count=len(attributes),
        axes=tuple(AxisRange(attribute=a, channel_name=a) for a in attributes),
        gaps=gaps,
    )


def _caps(*fixtures, unread: dict[int, str] | None = None) -> RigCapabilities:
    return RigCapabilities(fixtures={f.fid: f for f in fixtures}, unread=dict(unread or {}))


class TestRigAxisPresence:
    def test_an_axis_no_whole_read_carries_is_absent(self):
        caps = _caps(_fixture(1, "Source Four", "Dimmer"))
        assert RigAxisPresence(caps).presence("Zoom") == PRESENCE_ABSENT

    def test_one_fixture_carrying_it_makes_it_present_for_the_whole_rig(self):
        caps = _caps(
            _fixture(1, "Source Four", "Dimmer"), _fixture(2, "MegaPointe", "Dimmer", "Zoom")
        )
        assert RigAxisPresence(caps).presence("Zoom") == PRESENCE_PRESENT

    def test_the_match_is_case_insensitive_but_not_a_prefix(self):
        caps = _caps(_fixture(1, "MegaPointe", "ZoomMSpeed"))
        assert RigAxisPresence(caps).presence("zoom") == PRESENCE_ABSENT
        assert RigAxisPresence(caps).presence("Dimmer") == PRESENCE_ABSENT

    @pytest.mark.parametrize(
        "caps",
        [
            _caps(),
            _caps(_fixture(1, "Source Four", "Dimmer"), unread={9: "capability_unread"}),
            _caps(_fixture(1, "MegaPointe", "Dimmer", gaps=("budget",))),
        ],
        ids=["nothing-read", "a-fid-unread", "a-partial-read"],
    )
    def test_absence_is_never_claimed_on_an_incomplete_read(self, caps):
        assert RigAxisPresence(caps).presence("Zoom") == PRESENCE_UNREAD

    def test_an_unmeasured_spelling_is_unread_rather_than_absent(self):
        caps = _caps(_fixture(1, "Source Four", "Dimmer"))
        assert "Iris" not in MEASURED_ATTRIBUTE_SPELLINGS
        for attribute in ("Iris", "ColorRGB_R"):
            assert RigAxisPresence(caps).presence(attribute) == PRESENCE_UNREAD

    def test_widening_the_judged_set_is_a_parameter_not_a_rewrite(self):
        caps = _caps(_fixture(1, "Source Four", "Dimmer"))
        widened = RigAxisPresence(caps, judged=("Dimmer", "Zoom", "Iris"))
        assert widened.presence("Iris") == PRESENCE_ABSENT

    def test_the_adapter_holds_a_real_looks_plan_end_to_end(self):
        caps = _caps(_fixture(1, "Source Four", "Dimmer"))
        report = _plan(_zoom_look(), axes=RigAxisPresence(caps))
        hold = _skip(report, "Focus")
        assert hold.reason == AXIS_ABSENT and "Zoom" in hold.detail
        # Iris 는 철자가 미측정이라 판정하지 않는다 -> 저장은 그대로 간다.
        assert "Beam" in _families_stored(report)

    def test_the_adapter_never_touches_a_range(self):
        # 방향을 나르는 AxisRange 를 읽지도 정렬하지도 않는다는 것을 값으로 재기:
        # 물리 범위가 아예 없는 축으로도 판정이 나온다.
        caps = _caps(_fixture(1, "MegaPointe", "Zoom"))
        assert all(a.physical_from is None for a in caps.fixtures[1].axes)
        assert RigAxisPresence(caps).presence("Zoom") == PRESENCE_PRESENT
