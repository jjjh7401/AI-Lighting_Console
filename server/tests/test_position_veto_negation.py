"""Korean negation must close by paradigm, not by suffix list (card t27)."""

from __future__ import annotations

import pytest

from server.web.session import _POSITION_FX_VETO

#: 조작자가 팬/틸트를 **제외했다**고 믿는 문장. 하나라도 새면 콘솔에 저장된다.
NEGATIONS = (
    "포지션 아님, R/G 컬러 서클 시퀀스",
    "포지션 아님",
    "포지션아님",
    "포지션 아니야",
    "포지션 아니다",
    "포지션 아닙니다",
    "포지션 아닌 컬러",
    "포지션 아녜요",
    "포지션 아냐",
    "빔 아녀",
    "팬틸트 아님",
    "틸트는 아닙니다",
    "컬러만 하고 포지션 아님",
    "position 아님",
    "포지션 말고 컬러",
    "무빙 제외",
)

#: 조작자가 포지션을 **원한** 문장. 여기서 베토가 걸리면 기능을 막는 쪽이라
#: 놓치는 것보다 나쁘다 — 한 방향만 지키는 검사가 되지 않게 같이 쏜다.
WANTED = (
    "포지션 시퀀스",
    "포지션 이펙트 만들어",
    "포지션 잡아줘",
    "포지션 프리셋 저장",
    "무빙 서클 만들어",
    "팬 아니면 틸트로",
    "포지션 아니냐",
    "포지션 아니니",
)


@pytest.mark.parametrize("text", NEGATIONS)
def test_every_negation_form_vetoes(text):
    assert _POSITION_FX_VETO.search(text), text


@pytest.mark.parametrize("text", WANTED)
def test_a_wanted_position_request_is_not_vetoed(text):
    """Positive control — the opposite failure blocks what the operator asked for."""
    assert _POSITION_FX_VETO.search(text) is None, text


def test_the_suffix_list_would_not_have_closed_this():
    """`아님` is `아`+`님`, not `아니`+`ㅁ` — a literal `아니` never matches it.

    This is why the fix closes the inflection paradigm instead of listing
    endings: the syllable is precomposed, so each new ending is a new codepoint.
    """
    assert "아니" not in "포지션 아님"
    assert "아니" not in "포지션 아닌"


def test_the_controls_are_not_vacuous():
    """Both sets must be non-empty and disjoint, or the parametrize proves nothing."""
    assert NEGATIONS and WANTED
    assert not (set(NEGATIONS) & set(WANTED))
