"""cyc 없는 리그의 D1 — 두 룩이 들어온 뒤의 새 현실 (카드 t282 → SPEC-COPILOT-D1GRANT-001).

이 파일은 **부재 트립와이어로 태어났다.** 카드 t282 는 `server/looks/library/` 가
PRESERVE 초크포인트 아래에 있어 룩을 넣지 못했고(그 게이트의
`test_exactly_the_three_granted_files_changed` 가 바뀐 **파일 집합 자체**를 못박아
추가조차 통과시키지 않았다), 그래서 룩 없이 검사만 남겼다. 세 클래스는 제안된
두 look_id 가 없는 동안 건너뛰었고, 별도의 부재-단언 클래스 하나가 그 건너뜀이
조용한 합격으로 굳지 않게 잡았다(이름과 본문은 이 파일의 git 이력에 있다 — 여기에
문면으로 옮기지 않는 이유는 AC-D1GRANT-012 가 skip 어휘의 잔존을 개수로 재기
때문이고, 그 검사는 문자열이 주석 안에 있는지 코드 안에 있는지를 구별하지 않는다).

**그 트립와이어는 자기 목적을 다했다.** SPEC-COPILOT-D1GRANT-001 이 승인된 통로로
두 룩을 넣었고(`_LOOKS_GRANTED_D1_APPENDS`), 부재를 단언하던 클래스는 사라졌다.
남은 것은 조건 없이 도는 검사뿐이다 — skip 게이트 0건, `-rs` 로 확인한다.

한 가지는 태어날 때의 문면과 **다르다.** 이 파일은 원래 무회귀의 근거를 「새 룩을
파일에서 기존 D1 룩 **뒤에** 놓는다」로 적었는데, `looks_for_genre` 는
`(dynamics, look_id)` 로 정렬하며 **파일 순서를 읽지 않는다**. 오늘 결과가 맞는 것은
두 새 id 가 사전순으로 뒤에 오기 때문이고, 이름을 바꾸면 조용히 깨진다. 그래서
`TestTheCycRigDoesNotMove` 가 그 축을 산문이 아니라 **검사로** 고정한다.
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

#: 들어온 룩 — 장르별 look_id 와, 그 룩이 실기 리그에서 묶이는 근거가 되는 역할.
#: 역할은 `resolve_roles` 로 실측했다: 실기 18그룹에서 백라이트·프론트·사이드·스페셜
#: 은 묶이고 탑·배경 은 `no_match` 다.
_ADDED = {
    "edm": ("edm-haze-shafts", "백라이트"),
    "rock": ("rock-wing-embers", "사이드"),
}

#: 기존 D1 룩 — cyc 있는 리그에서 계속 뽑혀야 하는 쪽. 새 룩이 이들 **뒤에**
#: 정렬되므로(파일 위치가 아니라 `look_id` 사전순), 「묶이는 첫 룩」을 고르는
#: `_select_bindable` 규칙에 의해 cyc 가 있으면 이쪽이 이긴다.
_INCUMBENT_D1 = {
    "edm": "edm-ambient-hold",
    "rock": "rock-empty-stage",
}


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir(Path("server/looks/library"))


def _look_ids(library, genre: str) -> tuple[str, ...]:
    return tuple(look.look_id for look in looks_for_genre(library, genre))


class TestTheCycLessRigGainsItsQuietCue:
    """cyc 없는 리그에서 edm·rock 의 D1 구간이 큐를 받는다 — 이 SPEC 이 닫는 손해."""

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_added_look_is_in_the_library(self, library, genre):
        # 비공허성: 아래 검사들이 재는 대상이 실재한다. 이 단언이 이 파일의 옛
        # skip 게이트를 대체한다 — 부재는 이제 skip 이 아니라 실패다.
        look_id, _role = _ADDED[genre]
        assert look_id in _look_ids(library, genre)

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_ambient_band_now_stores_a_cue(self, library, genre):
        assert _stored_cues(library, genre, "ambient", _REAL_RIG)

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_look_that_binds_is_the_added_one(self, library, genre):
        look_id, _role = _ADDED[genre]
        d1 = [look for look in looks_for_genre(library, genre) if look.dynamics == 1]
        bindable = [look for look in d1 if look.look_id == look_id]
        assert bindable, f"{look_id} 가 D1 이 아니다"

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_added_look_uses_a_role_this_rig_actually_binds(self, library, genre):
        look_id, role = _ADDED[genre]
        (look,) = [
            candidate
            for candidate in looks_for_genre(library, genre)
            if candidate.look_id == look_id
        ]
        assert role in look.roles
        # 실기 리그에서 안 묶이는 두 역할을 새 룩이 **유일한** 역할로 들고 있으면
        # 이 SPEC 이 고치려던 결함을 그대로 재현한다.
        assert set(look.roles) - {"탑", "배경"}


class TestTheCycRigDoesNotMove:
    """무회귀: cyc 가 있는 리그는 여전히 기존 `배경` 룩을 고른다.

    근거는 `_select_bindable` 의 「요청 다이내믹스 안에서 묶이는 **첫** 룩」 규칙과,
    `looks_for_genre` 가 `(dynamics, look_id)` 로 정렬한다는 사실이다. 「파일에서
    뒤에 놓는다」가 아니다 — 그 문장은 이 파일이 태어날 때의 잘못된 근거이고,
    정렬기는 파일 순서를 읽지 않는다.
    """

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_incumbent_sorts_before_the_added_look_by_look_id(self, library, genre):
        # 무회귀의 **유일한** 기제를 직접 단언한다. 이름을 바꾸면 여기서 깨지고,
        # 그것이 아래 두 검사가 왜 초록인지에 대한 이유다.
        look_id, _role = _ADDED[genre]
        assert _INCUMBENT_D1[genre] < look_id

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_incumbent_backdrop_look_still_comes_first(self, library, genre):
        d1 = [look.look_id for look in looks_for_genre(library, genre) if look.dynamics == 1]
        assert d1[0] == _INCUMBENT_D1[genre]

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_cyc_rig_still_stores_its_ambient_cue(self, library, genre):
        assert _stored_cues(library, genre, "ambient", _CYC_RIG)
