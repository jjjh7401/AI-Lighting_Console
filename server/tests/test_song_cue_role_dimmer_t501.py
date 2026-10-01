"""카드 t501 — SPEC-LDRENDER-001 M3, REQ-LDRENDER-001/003.

``song_cue_render._role_dimmer_value_lines``(결함 6 `_back_layer_value_lines`의
일반화)와 ``song_cue_composer.CueDimmerData.role_pct``를 직접 겨눈다.

AC-LDRENDER-003(단일 레이어 리그는 오늘과 바이트 동일)의 **직접** 증거는 이
파일의 ``TestSingleLayerIsByteIdentical``이다 — 두 버전 소스를 나란히 돌려
비교한 실측은 ``.moai/reports/t501/ac003_byte_diff.py``(이 워크트리에 원곡
오디오가 없어 전체 세션 리허설로 두 트리를 대조할 수 없다, 그 스크립트 머리말
참조).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from server.design.song_cue_composer import CueDimmerData, SongCueComposerError
from server.design.song_cue_render import _role_dimmer_value_lines, _role_group_numbers


@dataclass(frozen=True)
class _Cue:
    """``_role_dimmer_value_lines``가 실제로 읽는 두 필드(``kind``·``dimmer``)만
    채운 대역 — 전체 ``ComposedCue``를 짓는 비용 없이 역할 순회 로직만 겨눈다."""

    kind: str
    dimmer: CueDimmerData


def _dimmer(role_pct: dict[str, float], *, key_pct: float = 80.0) -> CueDimmerData:
    return CueDimmerData(
        key_pct=key_pct,
        back_pct=role_pct.get("back"),
        budget_range_pct=(0.0, 100.0),
        role_pct=role_pct,
    )


#: t379 실측(rig.py 주석) — side 역할에 매칭되는 콘솔 그룹이 셋(SIDE-L/R/ALL)
#: 이다. 순서는 production `declared_layers` 딕셔너리 컴프리헨션과 같은 순서로
#: 둔다(session.py:7571) — 마지막(SIDE-ALL)이 이겨야 한다.
_MULTI_GROUP_SIDE_MAPPING = (
    {"role": "key", "group_no": 2, "group_name": "KEY"},
    {"role": "back", "group_no": 4, "group_name": "BACK"},
    {"role": "side", "group_no": 5, "group_name": "SIDE-L"},
    {"role": "side", "group_no": 6, "group_name": "SIDE-R"},
    {"role": "side", "group_no": 7, "group_name": "SIDE-ALL"},
    {"role": "wash", "group_no": 10, "group_name": "WASH-ALL"},
    {"role": "mover", "group_no": 13, "group_name": "MOVER-ALL"},
    {"role": "effect", "group_no": 14, "group_name": "BLIND"},
    {"role": "audience", "group_no": 3, "group_name": "FOH"},
)


class TestMultiRoleIteration:
    """REQ-LDRENDER-001 — 매핑된 모든 역할을 순회하는 다중 역할 함수."""

    def test_every_role_with_a_role_pct_value_gets_its_own_group_line(self) -> None:
        cue = _Cue(
            kind="section",
            dimmer=_dimmer({"key": 80.0, "back": 64.0, "side": 50.0, "wash": 45.0, "mover": 55.0}),
        )
        lines = _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING)
        assert set(lines) == {
            "Group 4 ; Attribute 'Dimmer' At 64",
            "Group 7 ; Attribute 'Dimmer' At 50",
            "Group 10 ; Attribute 'Dimmer' At 45",
            "Group 13 ; Attribute 'Dimmer' At 55",
        }
        assert len(lines) == 4, lines

    def test_a_role_with_multiple_matching_groups_uses_the_last_one_iteration_order_wins(
        self,
    ) -> None:
        """side 가 SIDE-L/SIDE-R/SIDE-ALL 셋에 매칭될 때 그룹 7(SIDE-ALL, 매핑
        목록의 마지막 side 항목)을 쓴다 — `declared_layers`(session.py)가
        `has_layer("side")`로 보는 것과 같은 그룹이어야 한다(M2 progress.md
        "여러 그룹이 한 역할에 매칭될 때의 동점 규율"과 동일 규율)."""
        cue = _Cue(kind="section", dimmer=_dimmer({"key": 80.0, "side": 33.0}))
        lines = _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING)
        assert lines == ("Group 7 ; Attribute 'Dimmer' At 33",)

    def test_key_role_is_never_emitted_as_a_delta_line(self) -> None:
        """key 는 전체 기구 키 디머 줄로 이미 나가 있다 — 델타 줄로 또 내면 중복."""
        cue = _Cue(kind="section", dimmer=_dimmer({"key": 80.0}))
        assert _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING) == ()

    def test_effect_role_is_never_emitted_even_if_role_pct_has_a_value(self) -> None:
        """R3(REQ-LDRENDER-007) HARD 불변식의 방어적 이중 장치 — `_dimmer_data`가
        실제로는 `role_pct["effect"]`를 채우지 않지만(M3 가 막아 둔 미해결
        결정), 설령 호출자가 실수로 채워도 이 함수는 effect 역할 그룹 줄을
        **절대** 내지 않는다(spec.md §3.1 HARD, M5 를 기다리지 않는 구조적 가드)."""
        cue = _Cue(kind="section", dimmer=_dimmer({"key": 80.0, "effect": 99.0}))
        lines = _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING)
        assert "Group 14" not in " ".join(lines)
        assert lines == ()

    def test_a_mapped_role_with_no_role_pct_value_emits_nothing(self) -> None:
        """audience 가 층 매핑엔 있지만(role=audience, group_no=3) role_pct 에
        값이 없으면(이 SPEC 이 audience 퍼센트도 안 지어낸다) 줄을 안 낸다 —
        발명이 아니라 생략."""
        cue = _Cue(kind="section", dimmer=_dimmer({"key": 80.0, "back": 64.0}))
        lines = _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING)
        assert all("Group 3 " not in line for line in lines)

    def test_blackout_cue_with_zero_key_pct_emits_nothing(self) -> None:
        cue = _Cue(
            kind="section",
            dimmer=CueDimmerData(
                key_pct=0.0,
                back_pct=0.0,
                budget_range_pct=(0.0, 100.0),
                blackout=True,
                role_pct={"key": 0.0, "back": 0.0, "side": 0.0},
            ),
        )
        assert _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING) == ()

    def test_non_section_kind_emits_nothing_regardless_of_role_pct(self) -> None:
        cue = _Cue(kind="mib_premove", dimmer=_dimmer({"back": 50.0, "side": 40.0}))
        assert _role_dimmer_value_lines(cue, _MULTI_GROUP_SIDE_MAPPING) == ()


class TestSingleLayerIsByteIdentical:
    """AC-LDRENDER-003 — 층 매핑이 역할을 전혀 해석 못 한 리그는 오늘과 바이트
    동일(빈 튜플)하다. 모든 역할에 role_pct 값이 있어도 매핑이 비면 그룹 번호
    자체가 없어 줄을 낼 수 없다 — 구성상 항상 참인 속성이라 조합을 넓게 돈다."""

    @pytest.mark.parametrize(
        "role_pct",
        [
            {"key": 80.0},
            {"key": 80.0, "back": 64.0},
            {"key": 80.0, "back": 64.0, "side": 50.0, "wash": 45.0, "mover": 55.0},
            {},
        ],
    )
    def test_empty_layer_mapping_always_yields_empty_lines(self, role_pct) -> None:
        cue = _Cue(kind="section", dimmer=_dimmer(role_pct))
        assert _role_dimmer_value_lines(cue, ()) == ()


class TestRoleGroupNumbers:
    def test_last_matching_entry_per_role_wins(self) -> None:
        numbers = _role_group_numbers(_MULTI_GROUP_SIDE_MAPPING)
        assert numbers["side"] == 7
        assert numbers["back"] == 4
        assert numbers["mover"] == 13

    def test_non_int_group_no_or_non_str_role_is_skipped(self) -> None:
        mapping = (
            {"role": "back", "group_no": None, "group_name": "BACK"},
            {"role": None, "group_no": 4, "group_name": "BACK"},
            {"role": "wash", "group_no": 10, "group_name": "WASH-ALL"},
        )
        assert _role_group_numbers(mapping) == {"wash": 10}


class TestCueDimmerDataRolePct:
    """CueDimmerData.role_pct — 키/값 유효성, 하위호환(key_pct/back_pct 유지)."""

    def test_role_pct_defaults_to_empty_mapping(self) -> None:
        d = CueDimmerData(key_pct=50.0, back_pct=None, budget_range_pct=(0.0, 100.0))
        assert dict(d.role_pct) == {}

    def test_role_pct_is_validated_like_key_pct(self) -> None:
        with pytest.raises(SongCueComposerError):
            CueDimmerData(
                key_pct=50.0,
                back_pct=None,
                budget_range_pct=(0.0, 100.0),
                role_pct={"side": 150.0},
            )

    def test_role_pct_rejects_an_empty_string_role_key(self) -> None:
        with pytest.raises(SongCueComposerError):
            CueDimmerData(
                key_pct=50.0,
                back_pct=None,
                budget_range_pct=(0.0, 100.0),
                role_pct={"": 50.0},
            )

    def test_role_pct_is_immutable(self) -> None:
        d = CueDimmerData(
            key_pct=50.0, back_pct=40.0, budget_range_pct=(0.0, 100.0), role_pct={"back": 40.0}
        )
        with pytest.raises(TypeError):
            d.role_pct["back"] = 0.0  # type: ignore[index]

    def test_to_dict_includes_role_pct(self) -> None:
        d = CueDimmerData(
            key_pct=50.0, back_pct=40.0, budget_range_pct=(0.0, 100.0), role_pct={"back": 40.0}
        )
        assert d.to_dict()["role_pct"] == {"back": 40.0}

    def test_key_pct_and_back_pct_fields_still_work_independent_of_role_pct(self) -> None:
        """하위호환 — 기존 소비자가 `key_pct`/`back_pct`만 읽어도 그대로 동작."""
        d = CueDimmerData(key_pct=70.0, back_pct=56.0, budget_range_pct=(0.0, 100.0))
        assert d.key_pct == 70.0
        assert d.back_pct == 56.0
