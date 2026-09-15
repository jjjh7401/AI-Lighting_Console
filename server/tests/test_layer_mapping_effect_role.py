"""카드 t385 잔여 — layer_mapping 이 계속 비어 러너 화면에 노란 경고
(「단일 레이어 계획입니다」)를 띄우는 원인 재현.

측정(t379): 이 리그의 콘솔 그룹은 다음과 같다 —
KEY FOH BACK SIDE-L SIDE-R SIDE-ALL MOVER-U MOVER-D MOVER-ALL WASH-U
WASH-D WASH-ALL BLIND STROBE HAZE ALL ODD EVEN.

측정(이 카드): `_layer_mapping_from_group_children`(session.py) 은
이 그룹 이름들에 대해 이미 발화하고 있었다 — key/audience/back 셋은
정확 일치로 판독됐다(KEY→key, FOH→audience, BACK→back).

🔴 **위 문장의 `FOH→audience` 는 2026-09-15 t395 로 만료됐다** — 그 판독은
오분류였고, `foh` 는 `key`(라벨 "Key/Front")로 옮겼다. 이 문단은 t385 시점의
기록으로 남기고 고치지 않는다(당시 사실이므로); 현재 동작은
`test_layer_mapping_foh_front.py` 가 정본이다. 발화하지
"않은" 것은 "effect" 역할뿐이었다: `_LAYER_GROUP_ALIASES["effect"]`
가 {effect, fx, aerial, beam} 뿐이라 STROBE·HAZE·MOVER-*·WASH-* 어느
것도 정확히 일치하지 않았다 — "구현 자체가 없다"가 아니라 "이 리그의
명명 관례가 effect 어휘 목록 밖에 있다"였다.

고침: STROBE·HAZE 는 어느 표준으로 읽어도 모호함 없이 "effect" 이므로
정확 일치 어휘에 추가한다. BLIND(블라인더)는 관객 지향 장비일 수 있어
역할이 모호하므로 뺀다(감독 확인이 필요한 별도 결정 — 이 카드에서
추측하지 않는다).

🔴 **위 BLIND 유보는 2026-09-15 감독 답으로 해소됐다** — `effect` 다. 이 문단은
t385 시점의 기록으로 남기고, 현재 동작은 아래
`test_blind_reads_as_effect_by_the_directors_answer` 가 정본이다.

MOVER-*/WASH-* 는 접미사가 붙어 있어 여전히
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
    def test_key_and_back_were_already_inferred_before_this_card(self):
        """회귀 없음 — 이 두 역할은 고침 전에도 이미 발화했다.

        🔴 t395 개정: 원래 이 단언은 `{"key", "audience", "back"}` 이었다. 그
        `audience` 는 **FOH 그룹의 오분류를 못박고 있었다** — 이 파일이 t385
        시점의 사실을 「회귀 없음」으로 고정하면서, 그것이 옳은지는 재지 않았기
        때문이다. t395 가 `foh` 를 `key`(라벨 "Key/Front")로 옮겼고, FOH 의 역할
        이동은 이 파일 밖의 `test_layer_mapping_foh_front.py` 가 잰다.

        `audience` 를 여기서 뺀 것은 그 역할을 없앤 것이 아니다 — 이 리그에
        audience 를 받을 그룹이 없을 뿐이다(후보 BLIND 는 감독 확인 대기).
        """
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        roles = {entry["role"] for entry in mapping}
        assert {"key", "back"} <= roles

    def test_effect_role_now_infers_from_strobe_and_haze(self):
        """재현 대상: 고침 전에는 이 리그에서 effect 역할이 0건이었다.

        🔴 2026-09-15 개정 — BLIND 가 합류했다(감독 답, 아래 항목). 이 단언은
        「effect 를 받는 그룹 전수」라서 셋이 됐다.
        """
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        effect_groups = {entry["group_name"] for entry in mapping if entry["role"] == "effect"}
        assert effect_groups == {"STROBE", "HAZE", "BLIND"}, f"effect 판독: {effect_groups}"

    def test_blind_reads_as_effect_by_the_directors_answer(self):
        """감독 답 2026-09-15 — BLIND 는 `effect` 다.

        t385(이 파일)와 t395 는 이 판정을 **비워 뒀다**: 블라인더는 객석을 향해
        쏘니 `audience` 로도, 순간에 터뜨리는 장비이니 `effect` 로도 읽혀서
        저장소만으로는 정할 근거가 없었다. 감독에게 직접 물어 `effect` 를 받았다 —
        운용 방식이 스트로브와 같은 계열이라는 판단이다.

        근거가 코드도 문서도 아니라 **감독의 연출 판단**이라, 뒤집으려면 추론이
        아니라 감독에게 다시 물어야 한다.
        """
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        blind_roles = [entry["role"] for entry in mapping if entry["group_name"] == "BLIND"]
        assert blind_roles == ["effect"], f"BLIND 판독: {blind_roles}"

    def test_the_full_word_blinder_reads_as_effect_too(self):
        """이 리그는 `BLIND` 로 줄여 쓰지만 `BLINDER` 로 쓰는 쇼파일도 있다.

        같은 장비의 온전한 이름이라 같은 판정을 받아야 한다 — 이 표의 기존 관례와
        같다(`back` 이 `backlight`·`rear` 를, `effect` 가 `fx`·`aerial` 을 함께 든다).
        어휘를 넣고 검사를 안 붙이면 나중에 정리 과정에서 조용히 사라진다.
        """
        mapping = _layer_mapping_from_group_children(_payload(("BLINDER",)))
        assert [entry["role"] for entry in mapping] == ["effect"]

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
