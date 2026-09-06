"""cyc 없는 리그의 D1 — 두 룩이 들어온 뒤의 최종 형태 (SPEC-COPILOT-D1GRANT-001).

이 파일은 **부재 트립와이어로 태어났다**(카드 t282, PR #344). 당시
`server/looks/library/` 는 PRESERVE 초크포인트에 막혀 추가조차 통과하지 못했고,
그래서 룩은 못 넣은 채 「룩이 들어오면 저절로 발화하는」 검사만 남겼다. 모든 검사가
부재 확인 헬퍼를 거쳐 건너뛰었고, 별도의 감시 클래스가 그 건너뜀이 조용한 합격으로
굳지 않게 잡고 있었다.

SPEC-COPILOT-D1GRANT-001 이 승인된 통로로 두 룩을 넣으면서 그 트립와이어는 자기
목적을 다했다. 이제 이 파일에 건너뛰기 게이트는 **하나도 없다** — 룩의 부재를
확인하던 헬퍼도, 그 건너뜀이 조용한 합격으로 굳지 않게 잡던 감시 클래스도 사라졌고,
남은 세 클래스가 무조건 실행된다. `-rs` 로 돌려 건너뜀 0건임을 확인할 수 있다.
(옛 이름은 이 파일의 git 이력에 남아 있다 — 문면에 다시 적으면 「건너뛰기 게이트
0건」을 재는 기계 검사가 자기 기록에 걸린다.)

역할을 왜 그렇게 골랐는지는 SPEC 본문 §3.1 과 두 YAML 파일의 블록 주석에 있다.
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

#: 도입된 룩 — 장르별 look_id 와, 그 룩이 실기 리그에서 묶이는 근거가 되는 역할.
#: 실기 18그룹에서 백라이트·프론트·사이드·스페셜 은 묶이고 탑·배경 은 `no_match` 다.
_ADDED = {
    "edm": ("edm-haze-shafts", "백라이트"),
    "rock": ("rock-wing-embers", "사이드"),
}

#: 기존 D1 룩 — cyc 있는 리그에서 계속 뽑혀야 하는 쪽. 새 룩이 이들 뒤로 오는 것은
#: 파일 위치가 아니라 **look_id 사전순** 때문이다(`looks_for_genre` 는 파일 순서를
#: 읽지 않는다). 그 성질은 :class:`TestTheOrderingAxisIsTheLookId` 가 못박는다.
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
    """게이트가 열렸다: cyc 없는 리그에서 edm·rock 의 D1 구간이 큐를 받는다."""

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_added_look_is_in_the_library(self, library, genre):
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


class TestTheOrderingAxisIsTheLookId:
    """무회귀의 축은 파일 위치가 아니라 ``look_id`` 사전순이다 (REQ-D1GRANT-003).

    PR #344 의 제안서는 무회귀 근거를 「파일에서 기존 D1 룩 **뒤에** 놓는다」로 적었고,
    그것은 틀렸다. ``looks_for_genre`` 는 ``(dynamics, look_id)`` 로 정렬하며 파일 안의
    위치를 보지 않는다. 오늘 결과가 맞는 것은 두 새 id 가 우연히 뒤로 정렬되기
    때문이며, **이름을 바꾸면 조용히 깨진다.** 그래서 주석이 아니라 검사로 고정한다.
    """

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_incumbent_look_id_sorts_before_the_added_one(self, genre):
        added, _role = _ADDED[genre]
        assert _INCUMBENT_D1[genre] < added

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_d1_order_follows_that_sort_not_the_file(self, library, genre):
        d1 = [look.look_id for look in looks_for_genre(library, genre) if look.dynamics == 1]
        assert d1 == sorted(d1)
        assert d1[0] == _INCUMBENT_D1[genre]


class TestTheCycRigDoesNotMove:
    """무회귀: cyc 가 있는 리그는 여전히 기존 ``배경`` 룩을 고른다.

    근거는 ``_select_bindable`` 의 「요청 다이내믹스 안에서 묶이는 **첫** 룩」 규칙이고,
    「첫」을 정하는 것은 위 클래스가 못박은 사전순이다.
    """

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_incumbent_backdrop_look_still_comes_first(self, library, genre):
        d1 = [look.look_id for look in looks_for_genre(library, genre) if look.dynamics == 1]
        assert d1[0] == _INCUMBENT_D1[genre]

    @pytest.mark.parametrize("genre", tuple(_ADDED))
    def test_the_cyc_rig_still_stores_its_ambient_cue(self, library, genre):
        assert _stored_cues(library, genre, "ambient", _CYC_RIG)
