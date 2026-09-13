"""카드 t385 잔여 — layer_mapping 이 계속 비어 러너 화면에 노란 경고
(「단일 레이어 계획입니다」)를 띄우는 원인 재현.

측정(t379): 이 리그의 콘솔 그룹은 다음과 같다 —
KEY FOH BACK SIDE-L SIDE-R SIDE-ALL MOVER-U MOVER-D MOVER-ALL WASH-U
WASH-D WASH-ALL BLIND STROBE HAZE ALL ODD EVEN.

측정(이 카드): `_layer_mapping_from_group_children`(session.py) 은
이 그룹 이름들에 대해 이미 발화하고 있었다 — key/audience/back 셋은
정확 일치로 판독됐다(KEY→key, FOH→audience, BACK→back). 발화하지
"않은" 것은 "effect" 역할뿐이었다: `_LAYER_GROUP_ALIASES["effect"]`
가 {effect, fx, aerial, beam} 뿐이라 STROBE·HAZE·MOVER-*·WASH-* 어느
것도 정확히 일치하지 않았다 — "구현 자체가 없다"가 아니라 "이 리그의
명명 관례가 effect 어휘 목록 밖에 있다"였다.

고침: STROBE·HAZE 는 어느 표준으로 읽어도 모호함 없이 "effect" 이므로
정확 일치 어휘에 추가한다. BLIND(블라인더)는 관객 지향 장비일 수 있어
역할이 모호하므로 뺀다(감독 확인이 필요한 별도 결정 — 이 카드에서
추측하지 않는다). MOVER-*/WASH-* 는 접미사가 붙어 있어 여전히
미판독이며, 이는 RG5(부분 문자열 매칭 금지)의 정책 결정이 선행돼야
하는 별도 카드로 남긴다 — 이 테스트가 그 잔여를 명시적으로 고정한다.
"""

from __future__ import annotations

from server.design.rig import _LAYER_GROUP_ALIASES
from server.web.session import _layer_mapping_from_group_children

# 카드 t379 실측 — 이 리그의 DataPool/Groups 그룹 이름 전수.
_MEASURED_GROUP_NAMES = (
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "SIDE-ALL",
    "MOVER-U",
    "MOVER-D",
    "MOVER-ALL",
    "WASH-U",
    "WASH-D",
    "WASH-ALL",
    "BLIND",
    "STROBE",
    "HAZE",
    "ALL",
    "ODD",
    "EVEN",
)


def _payload(names: tuple[str, ...]) -> dict[str, object]:
    return {"children": [{"name": name, "i": index} for index, name in enumerate(names, start=1)]}


class TestEffectRoleNowInfersFromThisRigsGroupNames:
    def test_key_audience_back_were_already_inferred_before_this_card(self):
        """회귀 없음 — 이 세 역할은 고침 전에도 이미 발화했다."""
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        roles = {entry["role"] for entry in mapping}
        assert {"key", "audience", "back"} <= roles

    def test_effect_role_now_infers_from_strobe_and_haze(self):
        """재현 대상: 고침 전에는 이 리그에서 effect 역할이 0건이었다."""
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        effect_groups = {entry["group_name"] for entry in mapping if entry["role"] == "effect"}
        assert effect_groups == {"STROBE", "HAZE"}, f"effect 판독: {effect_groups}"

    def test_blind_is_deliberately_left_unclassified(self):
        """블라인더는 관객 지향일 수 있어 이 카드에서 역할을 추측하지 않는다."""
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        blind_entries = [entry for entry in mapping if entry["group_name"] == "BLIND"]
        assert blind_entries == [], "BLIND 를 이 카드가 추측해 분류했다"

    def test_mover_and_wash_groups_remain_unmatched_documented_residual(self):
        """MOVER-*/WASH-* 는 접미사 때문에 여전히 미판독 — 잔여로 명시 고정."""
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        matched_names = {entry["group_name"] for entry in mapping}
        residual = {"MOVER-U", "MOVER-D", "MOVER-ALL", "WASH-U", "WASH-D", "WASH-ALL"}
        assert not (residual & matched_names), f"예상 밖으로 판독됨: {residual & matched_names}"

    def test_alias_table_matching_stays_exact_no_substring_guessing(self):
        """RG5 정책 불변식 — "MOVERHEAD" 같은 유사 문자열이 실수로 안 걸리는지."""
        assert "mover" not in _LAYER_GROUP_ALIASES["effect"]
        assert "wash" not in _LAYER_GROUP_ALIASES["effect"]
