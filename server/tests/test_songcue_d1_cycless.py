"""cyc 없는 리그의 D1 — 제안된 두 룩이 들어오면 자동으로 켜지는 검사 (카드 t282).

이 파일은 **게이트에 막힌 작업의 나머지**다. `server/looks/library/` 는 PRESERVE
초크포인트(`test_overlap_preserve.py` 의 `TestLooksLibraryGrantedExtension`) 아래에
있고, 그 클래스의 `test_exactly_the_three_granted_files_changed` 가 바뀐 **파일 집합
자체**를 못박기 때문에 이 디렉터리에서는 추가조차 통과하지 못한다. 이 브랜치에서
후보 룩 하나를 붙여 실측했고 그 단언이 실패했다 — 상세는
`docs/proposals/2026-09-06-cycless-d1-looks-proposal.md` §3.

그래서 룩은 안 넣었고, 룩이 들어오면 **저절로 발화하는** 검사만 남긴다. 아래 세
클래스는 제안된 두 look_id 가 라이브러리에 없는 동안 건너뛰고, 들어오는 순간
새 현실을 단언한다. `TestTheSkipIsNotAPermanentPass` 가 이 건너뜀이 조용한
합격으로 굳지 않게 잡는다.

설계 근거(어떤 역할을, 왜, 무대에서 무엇으로 보이는지)는 제안서 §2 에 있다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.looks.busking import looks_for_genre
from server.looks.loader import load_library_from_dir
from server.tests.test_songcue_rig_aware_look import (
    _CYC_RIG,
    _REAL_RIG,
    _stored_cues,
)

#: 제안된 룩 — 장르별 look_id 와, 그 룩이 실기 리그에서 묶이는 근거가 되는 역할.
#: 역할은 이 브랜치에서 `resolve_roles` 로 실측했다(제안서 §1 표): 실기 18그룹에서
#: 백라이트·프론트·사이드·스페셜 은 묶이고 탑·배경 은 `no_match` 다.
_PROPOSED = {
    "edm": ("edm-haze-shafts", "백라이트"),
    "rock": ("rock-wing-embers", "사이드"),
}

#: 기존 D1 룩 — cyc 있는 리그에서 계속 뽑혀야 하는 쪽. 새 룩은 파일에서 이들
#: **뒤에** 놓이므로, 「묶이는 첫 룩」을 고르는 `_select_bindable` 규칙에 의해
#: cyc 가 있으면 이쪽이 이긴다.
_INCUMBENT_D1 = {
    "edm": "edm-ambient-hold",
    "rock": "rock-empty-stage",
}


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir(Path("server/looks/library"))


def _look_ids(library, genre: str) -> tuple[str, ...]:
    return tuple(look.look_id for look in looks_for_genre(library, genre))


def _require_proposed(library, genre: str):
    look_id, _role = _PROPOSED[genre]
    if look_id not in _look_ids(library, genre):
        pytest.skip(f"{look_id} 미도입 — PRESERVE 게이트에 막혀 있다 (카드 t282)")


class TestTheSkipIsNotAPermanentPass:
    """건너뜀이 조용한 합격으로 굳지 않게 하는 자리.

    아래 검사들은 룩이 없으면 전부 skip 이다. skip 만 남으면 「없어서 못 쟀다」와
    「재서 통과했다」가 밖에서 구별이 안 된다. 그래서 부재를 **명시적으로** 단언하고,
    룩이 들어오는 순간 이 클래스가 실패하며 갱신을 요구한다.
    """

    @pytest.mark.parametrize("genre", tuple(_PROPOSED))
    def test_the_proposed_look_is_absent_and_that_is_why_the_others_skip(self, library, genre):
        look_id, _role = _PROPOSED[genre]
        if look_id in _look_ids(library, genre):
            pytest.fail(
                f"{look_id} 가 라이브러리에 들어왔다. 이 파일의 skip 게이트를 걷어내고 "
                "test_songcue_rig_aware_look.TestWhatThisFixCannotReach 를 갱신하라 (카드 t282)."
            )

    @pytest.mark.parametrize("genre", tuple(_INCUMBENT_D1))
    def test_the_incumbent_d1_look_is_the_one_this_card_works_around(self, library, genre):
        # 비공허성: 우회 대상이 실재하고, 그 역할이 실기 리그에서 안 묶이는 `배경`
        # 하나뿐이라는 것 — 이것이 이 카드 전체의 전제다.
        d1 = [look for look in looks_for_genre(library, genre) if look.dynamics == 1]
        assert [look.look_id for look in d1] == [_INCUMBENT_D1[genre]]
        assert [look.roles for look in d1] == [("배경",)]


class TestTheCycLessRigGainsItsQuietCue:
    """게이트가 열리면: cyc 없는 리그에서 edm·rock 의 D1 구간이 큐를 받는다."""

    @pytest.mark.parametrize("genre", tuple(_PROPOSED))
    def test_the_ambient_band_now_stores_a_cue(self, library, genre):
        _require_proposed(library, genre)
        assert _stored_cues(library, genre, "ambient", _REAL_RIG)

    @pytest.mark.parametrize("genre", tuple(_PROPOSED))
    def test_the_look_that_binds_is_the_proposed_one(self, library, genre):
        _require_proposed(library, genre)
        look_id, _role = _PROPOSED[genre]
        d1 = [look for look in looks_for_genre(library, genre) if look.dynamics == 1]
        bindable = [look for look in d1 if look.look_id == look_id]
        assert bindable, f"{look_id} 가 D1 이 아니다"

    @pytest.mark.parametrize("genre", tuple(_PROPOSED))
    def test_the_proposed_look_uses_a_role_this_rig_actually_binds(self, library, genre):
        _require_proposed(library, genre)
        look_id, role = _PROPOSED[genre]
        (look,) = [
            candidate
            for candidate in looks_for_genre(library, genre)
            if candidate.look_id == look_id
        ]
        assert role in look.roles
        # 실기 리그에서 안 묶이는 두 역할을 새 룩이 **유일한** 역할로 들고 있으면
        # 이 카드가 고치려던 결함을 그대로 재현한다.
        assert set(look.roles) - {"탑", "배경"}


class TestTheCycRigDoesNotMove:
    """무회귀: cyc 가 있는 리그는 여전히 기존 `배경` 룩을 고른다.

    근거는 `_select_bindable` 의 「요청 다이내믹스 안에서 묶이는 **첫** 룩」 규칙이고,
    새 룩을 파일에서 기존 D1 룩 **뒤에** 놓는 것이 이 성질을 지키는 방법이다.
    """

    @pytest.mark.parametrize("genre", tuple(_PROPOSED))
    def test_the_incumbent_backdrop_look_still_comes_first(self, library, genre):
        _require_proposed(library, genre)
        d1 = [look.look_id for look in looks_for_genre(library, genre) if look.dynamics == 1]
        assert d1[0] == _INCUMBENT_D1[genre]

    @pytest.mark.parametrize("genre", tuple(_PROPOSED))
    def test_the_cyc_rig_still_stores_its_ambient_cue(self, library, genre):
        _require_proposed(library, genre)
        assert _stored_cues(library, genre, "ambient", _CYC_RIG)
