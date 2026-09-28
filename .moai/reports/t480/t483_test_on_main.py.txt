"""카드 t483 — 대화 길 Q2 에서 'edm 느낌 색 조합' 을 고르면 주색이 색 이름이
아닌 수식어('단색')로 잡혀 RGB 로 안 풀리고, 곡 큐의 색 줄이 0 이 되던 결함.

Q2 후보의 값은 표준 §7 ``GENRE_DEFAULT_TABLE`` 의 ``color_tendency`` 문장
그대로다(``_q2_color_candidates``). edm 행은 ``"단색 볼드, 퍼플/레드/화이트"``
라 ``_palette_value_tokens`` 가 ``('단색', '볼드', '퍼플', '레드', '화이트')``
를 내고, ``_arc_palette`` 는 반환 튜플 첫 칸을 **항상** 첫 토큰으로 고정하므로
(카드 t409 "메인 컬러 중심") 모든 구간의 주색이 '단색' → ``resolve_color_name``
None → 색 덮어쓰기 실패였다.

전수(장르 행 5개, 2026-09-28 실측): 메탈 행도 첫 토큰 '스래시' 로 같은 모양,
록·발라드는 첫 토큰이 색이라 무사, 팝 행('유사색 3~4 + 액센트 1')은 RGB 로
풀리는 토큰이 **하나도 없어** 순서를 바꿔도 고칠 수 없다 — 이 카드 범위 밖
(아래 시험이 그 사실 자체를 고정해 둔다).
"""

from __future__ import annotations

import pytest

from server.design.color_names import resolve_color_name
from server.design.interview import _palette_value_tokens
from server.design.profile import GENRE_DEFAULT_TABLE
from server.tests.test_chorus_color_two_paths_t441 import _path_b_selections, _records

_GENRE_ROWS = {entry.genre: entry.color_tendency for entry in GENRE_DEFAULT_TABLE}

#: 색 이름으로 풀리는 토큰이 하나라도 있는 장르 행 — 주색이 반드시 색이어야 한다.
_ROWS_WITH_A_COLOR = ("메탈", "록", "edm", "발라드")


@pytest.mark.parametrize("genre", _ROWS_WITH_A_COLOR)
def test_genre_row_primary_token_resolves_to_rgb(genre: str) -> None:
    tokens = _palette_value_tokens(_GENRE_ROWS[genre])
    assert resolve_color_name(tokens[0]) is not None, (genre, tokens)


def test_no_token_is_dropped_only_reordered() -> None:
    """수식어는 건너뛸 뿐 버리지 않는다 — 팔레트 토큰 수(lint L5 가 세는
    것)는 그대로다."""
    edm = _palette_value_tokens(_GENRE_ROWS["edm"])
    assert edm[0] == "퍼플"
    assert set(edm) == {"단색", "볼드", "퍼플", "레드", "화이트"}


def test_unknown_user_color_keeps_first_place() -> None:
    """감독이 우리 어휘에 없는 색을 적으면(``민트``) 그 자리를 빼앗지 않는다 —
    건너뛰는 것은 표준 표에 이미 있는 **비색 수식어**뿐이다."""
    assert _palette_value_tokens("민트, 블루")[0] == "민트"
    assert _palette_value_tokens("블루와 화이트") == ("블루", "화이트")


def test_pop_row_has_no_resolvable_color_out_of_scope() -> None:
    tokens = _palette_value_tokens(_GENRE_ROWS["팝"])
    assert all(resolve_color_name(token) is None for token in tokens), tokens


def test_edm_answer_reaches_every_songcue_cue_as_rgb() -> None:
    """곡 큐 경로(LLM 도구, ``_override_songcue_main_color``)까지 — 실측
    Ice cream 7/7 · Rain 12/12 가 색 줄 0 이던 그 경로."""
    selections, notes = _path_b_selections(records=_records(palette=_GENRE_ROWS["edm"]))
    assert not notes, notes
