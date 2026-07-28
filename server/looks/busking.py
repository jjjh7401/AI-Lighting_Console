"""버스킹 준비 마법사 — 장르 조회 계층 (SPEC-COPILOT-BUSKWIZ-001, M1).

REQ-BUSKWIZ-001 (절단 없는 결정론적 조회) · REQ-BUSKWIZ-002 (한/영 별칭 해석과
정직한 실패) · REQ-BUSKWIZ-003 (룩 계층 무변경 — 읽기 전용 순회).

이 모듈은 출하된 ``LookLibrary``를 읽기만 한다. 콘솔·리그·게이트·실행 포트 어느
것도 import하지 않으며, 그 경계는 ``test_architecture.py``가 지킨다.

@MX:NOTE: [AUTO] 장르 조회가 ``matching.match_looks``를 쓰지 않는 것은 취향이
  아니라 요구다. 그 경로는 결과를 ``MAX_TOOL_MATCHES``(=8)에서 자르고
  ``truncated`` 신호를 붙이는데, 그것은 "물어본 것 중 상위 몇 개"를 돌려주는
  도구의 올바른 규율이지 "이 장르 전부"를 돌려주는 도구의 것이 아니다. EDM은
  9룩이므로 그 경로를 타는 순간 **정확히 1건이 조용히 사라진다** — 8룩이
  돌아오고 번들이 만들어지고 실행이 성공하므로 아무도 알아채지 못한다.
  그래서 이 모듈은 라이브러리를 직접 순회하고, 반환 형상에 절단 신호를 두지
  않는다(신호가 있다는 것 자체가 자를 수 있는 경로를 탔다는 뜻이다).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.looks.matching import EMPTY_QUERY, resolve_genre
from server.looks.schema import Look, LookLibrary

__all__ = [
    "EMPTY_QUERY",
    "UNRESOLVED_GENRE",
    "GenreSelection",
    "genres_in",
    "looks_for_genre",
    "select_genre",
]

# 장르 축이 침묵한 이유. ``EMPTY_QUERY``(matching에서 재사용)와 나란히 두되
# 합치지 않는다 — "아무것도 안 물었다"와 "우리가 모르는 것을 물었다"는 서로
# 다른 사실이고, 사용자가 취할 조치도 다르다(전자는 장르를 말하면 되고,
# 후자는 후보 중에서 골라야 한다). 이 구분은 resolver가 미매핑 사유를
# 갈라 두는 것과 같은 규율이다.
UNRESOLVED_GENRE = "unresolved_genre"


@dataclass(frozen=True)
class GenreSelection:
    """한 번의 장르 해석 결과. 성공이면 ``looks``, 실패면 ``reason``+``candidates``.

    절단 신호 필드가 **없다**는 것이 이 형상의 계약이다(REQ-BUSKWIZ-001).
    """

    genre: str | None = None
    looks: tuple[Look, ...] = ()
    reason: str | None = None
    candidates: tuple[str, ...] = ()


def genres_in(library: LookLibrary) -> tuple[str, ...]:
    """라이브러리가 실제로 담고 있는 장르. 후보 목록의 유일한 출처다.

    상수로 박지 않는 이유: 라이브러리가 늘면 후보도 함께 늘어야 하고, 두
    곳에 적힌 목록은 한쪽만 갱신되는 순간 거짓말이 된다.
    """
    return tuple(sorted({look.genre for look in library.looks}))


def looks_for_genre(library: LookLibrary, genre: str) -> tuple[Look, ...]:
    """그 장르의 룩 **전량**을 결정론적 전순서로 반환한다.

    순서는 다이내믹스 오름차순 → 동률 시 ``look_id`` 사전순. 이것은 신규
    발명이 아니라 ``matching._ranked``의 타이브레이크 관례가 점수 균일 구간에서
    퇴화한 형태이며, 잔잔함에서 클라이맥스로 올라가는 배열이 버스킹 팔레트의
    자연스러운 읽기 순서이기도 하다.

    모르는 장르는 예외가 아니라 빈 튜플이다 — 해석은 ``select_genre``의 일이고,
    여기서는 "그런 룩이 없다"가 정직한 답이다.
    """
    return tuple(
        sorted(
            (look for look in library.looks if look.genre == genre),
            key=lambda look: (look.dynamics, look.look_id),
        )
    )


def select_genre(library: LookLibrary, query: str) -> GenreSelection:
    """사용자 발화에서 장르를 해석하고 그 장르의 룩 전량을 붙여 돌려준다.

    별칭 표는 ``matching``의 것을 그대로 쓴다(REQ-BUSKWIZ-002) — 여기서
    재정의하면 한/영 어휘가 두 곳에 살게 되고, 그 순간 둘은 갈라지기
    시작한다. 해석 실패는 **가장 비슷한 장르로 승격되지 않는다**: 과신 매칭의
    결과는 사용자가 원한 적 없는 장르의 팔레트가 쇼파일에 남는 것이다.

    한계 하나를 적어 둔다: ``resolve_genre``는 "장르어 0개"와 "장르어 2개
    이상"을 모두 ``None``으로 접는다. 둘을 가르려면 별칭 표를 다시 훑어야
    하는데 그것이 곧 재정의이므로, 이 모듈은 둘을 ``UNRESOLVED_GENRE`` 하나로
    보고한다. 빈 질의만은 표 없이 판별되므로 따로 센다.
    """
    candidates = genres_in(library)
    if not query or not query.strip():
        return GenreSelection(reason=EMPTY_QUERY, candidates=candidates)
    genre = resolve_genre(query)
    if genre is None:
        return GenreSelection(reason=UNRESOLVED_GENRE, candidates=candidates)
    return GenreSelection(genre=genre, looks=looks_for_genre(library, genre))
