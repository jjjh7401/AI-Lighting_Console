"""t395 — FOH 는 `audience` 가 아니라 `key`(Key/Front) 다.

## 재현 대상

`_LAYER_GROUP_ALIASES["audience"]` 가 `{audience, house, foh}` 라서 이 리그의
FOH 그룹이 `audience` 로 판독됐다. 조명 실무에서 FOH(Front of House)는 객석
**뒤편에 매단 위치**를 뜻하고 비추는 대상은 무대와 연주자다 — 객석을 향해 쏘는
것은 블라인더 쪽이다. 정본 §6.2 는 그 층을 **프론트 필**이라 부르며 "밝은
워시가 아니라 부드러운 보정광으로 항상 유지"라 못박았다(카드 t377 이 그 층을
`server/looks/songcue.py` 에 구현했다).

## 실측으로 좁혀진 피해 범위 — 카드의 전제 절반은 반증됐다

착수 전 카드는 "audience 로 분류되면 관객 쪽 연출 규칙이 프론트 필에 걸리고
반대로 프론트 필 규칙은 배정된 그룹을 잃는다"고 적었다. **둘 다 일어나지
않는다**(2026-09-15, origin/main 794a161 실측):

* `RigLayers.mapping` 을 읽는 프로덕션 술어는 셋뿐이고, `has_layer(role)` 의
  호출 인수는 **전부 `"back"`** 이다(`song_cue_composer.py:635`·`:640`).
  `layer_rules_active()` 는 역할과 무관한 `mapped` 불리언이고, `fids_for()` 는
  프로덕션 호출이 **0건**이다. 즉 `audience` 역할을 읽는 연출 규칙이 없다 —
  FOH 가 그 역할에 들어가도 발화하는 것이 없다.
* 프론트 필은 **다른 표**를 쓴다. `FRONT_FILL_ROLE = "프론트"` 는 위치 역할이고
  `server/looks/roles.py` 의 `aliases=("front", "FOH")` 로 해석된다 — 층 매핑과
  독립이라 그룹을 잃지 않는다.

## 그래서 이 카드가 고치는 것은 **감독이 읽는 라벨** 하나다

층 매핑은 감독에게 보여주고 승인을 받는다(`session.py` `_confirm_song_layer_mapping`
→ `_ask_one`). 감독이 보는 문장이 `Group N 'FOH' = Audience` 였다
(`_LAYER_ROLE_LABELS["audience"] == "Audience"`). 발화하는 규칙이 없어도 사람이
읽는 자리에 오분류가 노출되고, 감독이 「객석」으로 이해한 채 승인하면 그 이해가
이후 판단의 전제가 된다. `key` 의 라벨은 이미 `"Key/Front"` 이므로 `foh` 를
`key` 로 옮기면 감독이 보는 문장이 정본의 어휘와 맞는다.

`rig.py` 의 별칭표 주석은 이 모호함을 **이미 알고 있었다**: "Front of House" 는
부분 일치를 허용하면 `key`(via "front")와 `audience`(via "house") 양쪽에 걸린다고
적어 두고, 그 다음 줄에서 `foh` 를 `audience` 에만 넣었다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from server.design.rig import _LAYER_GROUP_ALIASES
from server.web.session import _LAYER_ROLE_LABELS, _layer_mapping_from_group_children

#: 카드 t379 실측 — 이 리그의 DataPool/Groups 그룹 이름 전수.
#: `test_layer_mapping_effect_role.py` 와 같은 목록이다(같은 실측이 출처).
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


def _role_of(group_name: str, names: tuple[str, ...] = _MEASURED_GROUP_NAMES) -> str | None:
    mapping = _layer_mapping_from_group_children(_payload(names))
    for entry in mapping:
        if entry["group_name"] == group_name:
            return str(entry["role"])
    return None


class TestFohReadsAsFrontNotAudience:
    def test_foh_is_classified_as_key_front(self):
        """재현 대상 — 고침 전 이 단언은 'audience' 를 받아 빨강이었다."""
        assert _role_of("FOH") == "key"

    def test_foh_is_not_classified_as_audience(self):
        """같은 사실의 반대쪽. 두 단언이 함께 있어야 '어느 역할도 안 붙었다'와
        '올바른 역할이 붙었다'가 구별된다 — 별칭을 그냥 지우면 위 단언만 깨진다."""
        assert _role_of("FOH") != "audience"

    def test_foh_is_not_left_unclassified(self):
        """빼는 것이 아니라 옮기는 것이다. 부재는 오분류의 고침이 아니다."""
        assert _role_of("FOH") is not None, (
            "FOH 가 어느 역할도 못 받았다 — 옮긴 것이 아니라 지운 것"
        )

    def test_foh_left_the_audience_alias_set(self):
        """별칭표 자체를 잰다 — 판독 결과만 재면 상위에서 덮어써도 통과한다."""
        assert "foh" not in _LAYER_GROUP_ALIASES["audience"]

    def test_foh_joined_the_key_alias_set(self):
        assert "foh" in _LAYER_GROUP_ALIASES["key"]


class TestTheOperatorFacingLabelIsWhatThisCardFixes:
    def test_the_label_the_director_sees_names_front(self):
        """이 카드의 실제 산출물 — 감독이 읽는 문장. 발화하는 연출 규칙은
        없으므로(모듈 독스트링) 이 라벨이 바뀐 것이 전부이고, 그것이 목적이다."""
        assert _LAYER_ROLE_LABELS[_role_of("FOH")] == "Key/Front"

    def test_the_key_label_still_names_both_words(self):
        """`Key/Front` 라벨 자체가 이 고침의 근거다 — 라벨이 `Key` 로 줄면
        FOH 를 여기 넣은 이유(정본의 '프론트')가 화면에서 사라진다."""
        assert "Front" in _LAYER_ROLE_LABELS["key"]


class TestTheOtherRolesAreUnchanged:
    def test_key_and_back_still_read_from_their_own_groups(self):
        """KEY·BACK 은 이 변경과 무관하다 — 회귀 방지."""
        assert _role_of("KEY") == "key"
        assert _role_of("BACK") == "back"

    def test_strobe_and_haze_still_read_as_effect(self):
        """t385 가 넣은 effect 어휘가 살아 있는지 — 같은 표를 건드렸으므로 잰다."""
        assert _role_of("STROBE") == "effect"
        assert _role_of("HAZE") == "effect"

    def test_blind_stays_unclassified_pending_the_directors_answer(self):
        """BLIND 는 여전히 감독 확인 대기다 — 이 카드가 추측해 채우지 않는다.
        FOH 를 옮기면서 '관객 지향 장비'를 audience 로 몰아넣고 싶어지는데,
        그 판정 근거는 이 저장소에 없다."""
        assert _role_of("BLIND") is None

    def test_the_audience_role_keeps_its_own_vocabulary(self):
        """audience 역할 자체를 없애는 것이 아니다 — FOH 만 나간다."""
        assert "audience" in _LAYER_GROUP_ALIASES["audience"]
        assert "house" in _LAYER_GROUP_ALIASES["audience"]

    def test_no_group_in_this_rig_reads_as_audience_anymore(self):
        """이 리그에서의 귀결 — FOH 가 나가면 audience 를 받는 그룹이 없다.
        이것이 회귀가 아니라 **이 카드가 의도한 결과**임을 고정한다: audience 를
        받을 자격이 있는 그룹(BLIND)은 감독 확인 대기 중이고, 없는 역할을
        있는 것처럼 세우지 않는다."""
        mapping = _layer_mapping_from_group_children(_payload(_MEASURED_GROUP_NAMES))
        audience_groups = {e["group_name"] for e in mapping if e["role"] == "audience"}
        assert audience_groups == set(), f"audience 판독: {audience_groups}"


class TestExactMatchPolicyStillHolds:
    def test_front_of_house_style_names_do_not_double_match(self):
        """별칭표 주석이 경고한 그 형태 — 부분 일치가 살아나면 'Front of House'
        하나가 key·audience 양쪽에 걸린다. 정확 일치라서 어디에도 안 걸려야 한다."""
        assert _role_of("Front of House", ("Front of House",)) is None

    def test_the_key_set_did_not_gain_a_substring_token(self):
        """`foh` 는 정확 일치 토큰이다 — 부분 문자열 어휘를 들이지 않았는지."""
        for token in _LAYER_GROUP_ALIASES["key"]:
            assert token == token.lower(), f"별칭 {token!r} 가 소문자가 아니다"
        assert "f.o.h" not in _LAYER_GROUP_ALIASES["key"], "구두점 변형은 이 표의 어휘가 아니다"
