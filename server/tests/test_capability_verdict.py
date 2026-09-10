"""`server.design.capability_verdict` + `rig_capability_read` + **배선된 호출 지점**.

카드 t344 B. 가짜 포트만 쓴다 — 콘솔에 한 바이트도 안 보낸다(읽기조차).

고정값은 실측이다(2026-09-10, onPC / 응답기 1.6.5, 읽기 전용):

* ``Zoom`` PHYSICALFROM=42.0 PHYSICALTO=1.8 — **역방향**
* Source 4 는 고정 장비라 축이 Dimmer 하나뿐이다(팬/틸트 없음)

🔴 이 파일의 존재 이유는 「부품이 초록이어도 경로는 안 이어졌다」다. 능력을 직접
넣어주는 시험만으로는 `session.py` 의 `patch=[]` 회귀를 못 잡는다 — 그래서
:class:`TestWiredCallSite` 가 **배선된 호출 지점**을 가짜 포트로 두드린다.
"""

from __future__ import annotations

import pytest

from server.design.capability_join import (
    FixtureCapability,
    FixtureTypeRef,
    RigCapabilities,
    read_rig_capabilities,
)
from server.design.capability_verdict import (
    POSITION_CAPABILITY,
    VERDICT_ABSENT,
    VERDICT_HELD,
    VERDICT_OK,
    VERDICT_UNMEASURED,
    ZOOM_CAPABILITY,
    patch_records,
    position_verdict,
    range_verdict,
)
from server.design.rig_capability_read import (
    RIG_GAP_UNREADABLE,
    read_design_rig,
)
from server.prechk.capability_read import CHANNEL_FUNCTION_PROPERTIES, AxisRange

_TYPES_ROOT = "Patch/FixtureTypes"
_FIXTURE_ROOT = "Patch/Stages/1/Fixtures"

_RANGES = {
    "Pan": ("-270.0", "270.0"),
    "Tilt": ("-125.0", "125.0"),
    "Zoom": ("42.0", "1.8"),
    "Dimmer": ("0.0", "1.0"),
}

#: 타입 슬롯 -> (이름, 채널 슬롯 -> 속성). Source 4 에 팬/틸트가 없다(실측).
_TYPES = {
    11: ("Robin MegaPointe", {1: "Pan", 2: "Tilt", 3: "Zoom"}),
    5: ("Source 4", {1: "Dimmer"}),
}
_TYPE_NAMES = {slot: name for slot, (name, _) in _TYPES.items()}


class _FakeConsole:
    """타입 라이브러리 트리 + 픽스처 트리를 함께 답하는 가짜 포트.

    ``fixtures`` 는 슬롯 -> (타입 슬롯, FID) 다. FID 를 ``None`` 으로 두면 그 슬롯의
    ``FID`` 프로퍼티가 답하지 않는다 — 조인 키가 없는 슬롯을 재현한다.
    """

    def __init__(self, fixtures: dict[int, tuple[int, int | None]]) -> None:
        self.fixtures = fixtures
        self.writes: list[object] = []  # 언제나 비어 있어야 한다

    # ── 열거 ────────────────────────────────────────────────────────────
    def query_state(self, path: str, *, offset: int = 0) -> dict:
        parts = path.split("/")
        if path == _TYPES_ROOT:
            children = [{"i": slot, "name": name} for slot, name in _TYPE_NAMES.items()]
            return {"ok": True, "node": {"childCount": len(children)}, "children": children}
        if path == _FIXTURE_ROOT:
            children = [{"i": slot, "name": f"fixture {slot}"} for slot in self.fixtures]
            return {"ok": True, "node": {"childCount": len(children)}, "children": children}
        if len(parts) >= 4 and parts[3] == "DMXModes":
            type_slot = int(parts[2])
            if type_slot not in _TYPES:
                return {"ok": False}
            channels = _TYPES[type_slot][1]
            if len(parts) == 4:
                return {"ok": True, "children": [{"i": 1, "name": "Mode 1"}]}
            if len(parts) == 6 and parts[5] == "DMXChannels":
                return {
                    "ok": True,
                    "children": [
                        {"i": slot, "name": f"Main Module_{attr}"}
                        for slot, attr in channels.items()
                    ],
                }
            if len(parts) == 7:
                attr = channels.get(int(parts[6]))
                if attr is None:
                    return {"ok": True, "children": []}
                return {"ok": True, "children": [{"i": 1, "name": attr}]}
            if len(parts) == 8:
                return {
                    "ok": True,
                    "children": [{"i": 1, "name": f"{channels[int(parts[6])]} 1"}],
                }
        return {"ok": False}

    # ── 단건 프로퍼티: FID 판독 + 모드 폭 ──────────────────────────────
    def query_property(self, path: str, name: str) -> dict:
        if path.startswith(_FIXTURE_ROOT) and name == "FID":
            slot = int(path.split("/")[-1])
            entry = self.fixtures.get(slot)
            if entry is None or entry[1] is None:
                return {"ok": False}
            return {"ok": True, "value": str(entry[1])}
        return {"ok": True, "value": "32"}

    # ── 벌크 프로퍼티: 픽스처 속성 + 채널함수 범위 ─────────────────────
    def query_properties(self, path: str, property_names) -> dict:
        parts = path.split("/")
        if path.startswith(_FIXTURE_ROOT):
            slot = int(parts[-1])
            type_slot = self.fixtures[slot][0]
            values = {
                "Patch": "1.001",
                "FixtureType": f"FixtureType {type_slot}",
                "Mode": "1 Mode 1",
                "Name": f"fixture {slot}",
            }
            return {
                "ok": True,
                "reads": [
                    {"n": name, "ok": True, "v": values.get(name, "")} for name in property_names
                ],
            }
        attr = _TYPES[int(parts[2])][1][int(parts[6])]
        physical_from, physical_to = _RANGES[attr]
        values = {
            "ATTRIBUTE": attr,
            "DMXFROM": "0",
            "DMXTO": "255",
            "PHYSICALFROM": physical_from,
            "PHYSICALTO": physical_to,
            "DEFAULT": "0",
        }
        return {
            "ok": True,
            "reads": [
                {"n": key, "ok": True, "v": values[key]} for key in CHANNEL_FUNCTION_PROPERTIES
            ],
        }


class _DeadConsole:
    """콘솔이 안 답한다 — 판독은 **빈 리그가 아니라 고지**로 끝나야 한다."""

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        return {"ok": False}

    def query_property(self, path: str, name: str) -> dict:
        return {"ok": False}

    def query_properties(self, path: str, property_names) -> dict:
        return {"ok": False}


def _caps(*specs: tuple[int, int]) -> RigCapabilities:
    """가짜 콘솔을 거쳐 실제 A 편 조인으로 만든 판독(직접 조립하지 않는다)."""
    console = _FakeConsole({slot: (type_slot, slot) for slot, type_slot in specs})
    return read_rig_capabilities(
        console,
        console,
        root=_TYPES_ROOT,
        fixtures=[
            FixtureTypeRef(fid=slot, type_raw=f"FixtureType {type_slot}", mode_raw="1 Mode 1")
            for slot, type_slot in specs
        ],
        type_names=_TYPE_NAMES,
    )


# ── (2b) 역방향 Zoom 범위 ──────────────────────────────────────────────


class TestReversedZoomRange:
    """🔴 42.0 -> 1.8. `from <= v <= to` 로 쓴 회귀는 여기서 전부 빨개진다."""

    ZOOM = AxisRange(
        attribute="Zoom", channel_name="Main Module_Zoom", physical_from=42.0, physical_to=1.8
    )

    @pytest.mark.parametrize("value", [1.8, 5.0, 20.0, 42.0])
    def test_in_range_values_pass_on_a_descending_axis(self, value):
        verdict = range_verdict(self.ZOOM, value)
        assert verdict.status == VERDICT_OK, verdict.detail
        assert verdict.descending is True

    @pytest.mark.parametrize("value", [45.0, 100.0])
    def test_above_the_wide_end_is_held(self, value):
        verdict = range_verdict(self.ZOOM, value)
        assert verdict.status == VERDICT_HELD
        assert verdict.held

    @pytest.mark.parametrize("value", [1.7, 0.0, -3.0])
    def test_below_the_narrow_end_is_held(self, value):
        verdict = range_verdict(self.ZOOM, value)
        assert verdict.status == VERDICT_HELD

    def test_the_held_reason_names_the_measured_range(self):
        """보류 사유에 측정 범위가 없으면 감독은 무엇이 밖인지 모른다."""
        verdict = range_verdict(self.ZOOM, 45.0)
        assert "42" in verdict.detail and "1.8" in verdict.detail
        assert "45" in verdict.detail

    def test_the_value_is_not_clamped(self):
        """clamp 하면 요구값과 콘솔에 가는 값이 조용히 달라진다."""
        verdict = range_verdict(self.ZOOM, 45.0)
        assert verdict.requested == 45.0

    def test_an_unmeasured_range_is_not_a_pass(self):
        axis = AxisRange(attribute="Zoom", channel_name="c", physical_from=42.0)
        assert range_verdict(axis, 45.0).status == VERDICT_UNMEASURED

    def test_an_absent_axis_is_its_own_verdict(self):
        verdict = range_verdict(None, 45.0, attribute="Zoom")
        assert verdict.status == VERDICT_ABSENT
        assert "Zoom" in verdict.detail


# ── (2a) 포지션 프리셋 거절 + 대조군 ───────────────────────────────────


class TestPositionRefusal:
    def test_a_fixed_type_is_refused_with_its_name_in_the_reason(self):
        """🔴 「거절됐다」만 보는 단언은 참 거절과 거짓 거절을 못 가른다(t112)."""
        verdict = position_verdict(_caps((1, 5)))
        assert verdict.refused == ("Source 4",)
        reason = verdict.reason()
        assert "Source 4" in reason
        assert "팬/틸트" in reason
        assert not verdict.any_positionable

    def test_a_moving_head_is_not_refused(self):
        """대조군 — 이것이 없으면 위 시험은 범위에 대해 아무 것도 증명하지 않는다."""
        verdict = position_verdict(_caps((1, 11)))
        assert verdict.allowed == ("Robin MegaPointe",)
        assert verdict.refused == ()
        assert verdict.reason() == ""
        assert verdict.any_positionable

    def test_a_mixed_rig_refuses_only_the_fixed_type(self):
        verdict = position_verdict(_caps((1, 11), (2, 5)))
        assert verdict.allowed == ("Robin MegaPointe",)
        assert verdict.refused == ("Source 4",)
        assert verdict.any_positionable  # 움직이는 장비가 있으니 축은 열린다

    def test_a_partial_read_is_not_a_refusal(self):
        """부분 판독으로 거절하면 있는 장비를 없다고 말한다."""
        cut = FixtureCapability(
            fid=1,
            type_slot=5,
            type_name="Source 4",
            mode_slot=1,
            mode_name="Mode 1",
            mode_width=None,
            channel_count=32,
            axes=(),
            gaps=("절단",),
        )
        verdict = position_verdict(RigCapabilities(fixtures={1: cut}))
        assert verdict.refused == ()
        assert verdict.unknown == ("Source 4",)
        assert verdict.any_positionable


# ── 어휘 매핑 (의도적으로 부분집합) ────────────────────────────────────


class TestVocabulary:
    def test_patch_records_carry_only_the_mapped_capabilities(self):
        records = patch_records(_caps((7, 11)))
        assert records == (
            {
                "fid": 7,
                "type_name": "Robin MegaPointe",
                "capabilities": [POSITION_CAPABILITY, ZOOM_CAPABILITY],
            },
        )

    def test_a_fixed_type_declares_neither(self):
        records = patch_records(_caps((3, 5)))
        assert records[0]["capabilities"] == []

    def test_position_is_any_of_not_all_of(self):
        """Pan 만 있어도 헤드는 움직인다 — all-of 로 바꾸면 그 장비가 거절된다.

        🔴 Pan 전용 기종은 리그 실측 15기종에 **없다**(9기종이 Pan+Tilt, 4기종이
        둘 다 없음). 그래서 이 시험의 장비 모양은 실측이 아니라 **어휘 의미의
        대조군**이다: any-of 를 all-of 로 조용히 바꾸는 회귀를 잡는 자리이며,
        그런 기종이 리그에 있다는 주장이 아니다.
        """
        pan_only = FixtureCapability(
            fid=9,
            type_slot=99,
            type_name="Pan Only",
            mode_slot=1,
            mode_name="Mode 1",
            mode_width=1,
            channel_count=1,
            axes=(
                AxisRange(
                    attribute="Pan",
                    channel_name="Main Module_Pan",
                    physical_from=-270.0,
                    physical_to=270.0,
                ),
            ),
        )
        rig = RigCapabilities(fixtures={9: pan_only})
        assert patch_records(rig)[0]["capabilities"] == [POSITION_CAPABILITY]
        assert position_verdict(rig).allowed == ("Pan Only",)

    def test_the_effect_capability_is_deliberately_unmapped(self):
        """`energy.EFFECT_AXIS_CAPABILITY` 를 추측으로 열지 않는다."""
        from server.design.capability_verdict import CAPABILITY_VOCABULARY
        from server.design.energy import EFFECT_AXIS_CAPABILITY

        assert EFFECT_AXIS_CAPABILITY not in CAPABILITY_VOCABULARY


# ── 조인 키 (item 1 의 실측) ───────────────────────────────────────────


class TestJoinKey:
    def test_the_slot_to_fid_join_produces_real_fids(self):
        """슬롯 2·5 에 FID 41·42 — 결과가 **슬롯이 아니라 FID** 로 키를 잡는다."""
        console = _FakeConsole({2: (11, 41), 5: (5, 42)})
        read = read_design_rig(console, fixture_types_root=_TYPES_ROOT)
        assert read.attempted
        assert sorted(record["fid"] for record in read.patch) == [41, 42]

    def test_a_slot_without_a_readable_fid_is_not_promoted(self):
        """🔴 슬롯을 FID 로 승격시키면 조용히 엉뚱한 장비를 가리킨다."""
        console = _FakeConsole({2: (11, 41), 5: (5, None)})
        read = read_design_rig(console, fixture_types_root=_TYPES_ROOT)
        assert [record["fid"] for record in read.patch] == [41]
        assert read.gap  # 빠진 슬롯은 고지된다
        assert not read.whole


class TestUnreachableConsole:
    def test_a_dead_console_yields_a_disclosed_gap_not_an_empty_rig(self):
        read = read_design_rig(_DeadConsole(), fixture_types_root=_TYPES_ROOT)
        assert read.attempted
        assert read.gap == RIG_GAP_UNREADABLE
        assert read.patch == ()
        assert not read.whole

    def test_an_unattempted_read_is_not_an_empty_rig(self):
        from server.design.rig_capability_read import DesignRigRead

        assert not DesignRigRead().attempted
        assert not DesignRigRead().whole


# ── 배선된 호출 지점 (`session.py` 의 옛 `patch=[]` 자리) ──────────────


class TestWiredCallSite:
    """🔴 `patch=[]` 로 되돌리면 이 클래스가 빨개진다.

    「부품이 초록이어도 경로는 안 이어졌다」가 이 카드가 고치러 온 결함이라, 능력을
    직접 넣어주는 시험은 여기서 **충분하지 않다**. 가짜 포트를 세션에 물려 실제
    호출 지점을 두드린다.
    """

    _REQUEST = (
        "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7: "
        "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
    )
    #: 좌표가 있고 팬/틸트 장비가 있으면 인터뷰는 5장이다(Q4 포함).
    _ANSWERS = [
        "우주",
        "우주 색 조합",
        "Ring In",
        "우주 컨셉 우선 배치",
        "템포 맞춤 (BPM 기준)",
    ]

    def _drive(self, tmp_path, monkeypatch, port):
        from server.tests.test_runner_self_correction import ScriptedProvider
        from server.tests.test_web_session import TestSongDesignInterviewSession as Harness
        from server.tests.test_web_session import _session
        from server.web import session as session_module

        seen: list[dict] = []
        real = session_module.build_rig_profile

        def spy(*, patch, groups, coords, **kwargs):
            seen.append({"patch": list(patch), "coords": list(coords)})
            return real(patch=patch, groups=groups, coords=coords, **kwargs)

        monkeypatch.setattr(session_module, "build_rig_profile", spy)

        harness = Harness()
        session, _console, _audit, _sent, _ = _session(tmp_path, ScriptedProvider([]))
        session._registry = harness._registry([], spatial_fails=False)
        session._question_channel = harness._Channel(list(self._ANSWERS))
        if port is not None:
            session._rig_capability_port = port
        session.run_instruction(self._REQUEST)
        return seen, session

    def test_the_call_site_hands_the_console_read_to_build_rig_profile(self, tmp_path, monkeypatch):
        """`patch` 가 콘솔에서 온다 — 리터럴 빈 목록이면 여기서 죽는다."""
        console = _FakeConsole({2: (11, 41), 5: (5, 42)})
        seen, _session = self._drive(tmp_path, monkeypatch, console)
        assert seen, "build_rig_profile 이 아예 안 불렸다 — 호출 지점이 바뀌었다"
        patch = seen[-1]["patch"]
        assert patch, "patch=[] 회귀 — 콘솔 판독이 호출 지점에 닿지 않는다"
        assert sorted(record["fid"] for record in patch) == [41, 42]
        by_fid = {record["fid"]: record for record in patch}
        assert POSITION_CAPABILITY in by_fid[41]["capabilities"]  # MegaPointe
        assert by_fid[42]["capabilities"] == []  # Source 4 — 고정 장비

    def test_a_fixed_only_rig_skips_the_spatial_question_and_says_why(self, tmp_path, monkeypatch):
        """팬/틸트 장비가 하나도 없으면 Q4 를 묻지 않는다 — 카드 t311 과 같은 기제."""
        console = _FakeConsole({1: (5, 42)})
        # Q4 를 건너뛰므로 답은 4장이다. 5장을 주면 남는다.
        from server.tests.test_runner_self_correction import ScriptedProvider
        from server.tests.test_web_session import TestSongDesignInterviewSession as Harness
        from server.tests.test_web_session import _session

        harness = Harness()
        session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
        session._registry = harness._registry([], spatial_fails=False)
        session._question_channel = harness._Channel(
            ["우주", "우주 색 조합", "Ring In", "템포 맞춤 (BPM 기준)"]
        )
        session._rig_capability_port = console
        session.run_instruction(self._REQUEST)
        notice = session._design_coord_notice
        assert "팬/틸트" in notice
        assert "Source 4" in notice, "거절된 기종 이름이 사유에 없으면 감독은 못 고친다"
        timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
        assert timelines, "포지션이 닫혔다고 큐 시트가 아예 안 나가면 안 된다"

    def test_an_unreachable_console_is_disclosed_at_the_call_site(self, tmp_path, monkeypatch):
        """빈 리그를 지어내지 않는다 — `patch=[]` 자리의 원래 규율이 살아 있다."""
        seen, session = self._drive(tmp_path, monkeypatch, _DeadConsole())
        assert seen[-1]["patch"] == []
        assert "장비 능력을 콘솔에서 읽지 못해" in session._design_coord_notice
