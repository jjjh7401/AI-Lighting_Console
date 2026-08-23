"""축 판정은 어휘가 아니라 카드가 내린다 (card t34).

`_POSITION_AXIS_CLAIM` 은 「포지션 낱말이 나오는가」에만 답한다. 그 답을
「사용자가 이 축을 원하는가」로 승격시키면, 배제 문장이 **배제하려는 바로 그
낱말을 쓰기 때문에** 긍정으로 뒤집힌다 — `포지션 빼고 컬러 스윕` 이 축 확인
없이 포지션으로 진행했다.

극성을 어휘로 잡아 보려는 시도는 수렴하지 않았다(3라운드 실측): 매 라운드 새
어법이 새고, 동시에 긍정 문장이 막히기 시작했다. 그래서 경쟁 축이 이펙트
주체로 지목되면 어휘로 판정하지 않고 **카드로 묻는다.**
"""

from __future__ import annotations

import pytest

from server.web.session import (
    _NON_POSITION_ATTRIBUTE,
    _POSITION_AXIS_CLAIM,
    ChatSession,
)

#: 조작자가 포지션 축을 **배제한** 문장. 하나라도 「포지션 진행」으로 새면
#: 사용자가 빼라고 한 축으로 시퀀스가 조용히 저장된다 — 실패 신호가 없고
#: 콘솔 쓰기는 되돌리기 어렵다.
#:
#: 세 갈래로 모았다. 배제는 한 가지 어법이 아니다:
#:   덜어내는 말(빼고·제외·말고) · 그대로 둔다는 말(고정·유지·그대로·놔두고)
#:   · 부사 부정(안·못) · 결여(없이·없는)
#: 어휘로 잡으려던 시도가 이 셋을 라운드마다 하나씩 흘렸다.
EXCLUSIONS = (
    "포지션 빼고 컬러 스윕 시퀀스 만들어줘",
    "포지션은 손대지 마, 컬러 스윕 시퀀스 만들어줘",
    "포지션 말고 컬러 스윕 시퀀스 만들어줘",
    "컬러만 바뀌는 스윕 시퀀스 만들어줘",
    "무빙 없이 컬러만 도는 웨이브 시퀀스 만들어줘",
    "팬틸트는 제외하고 디머 서클 시퀀스 저장해줘",
    "빔은 고정, 컬러 발리후 시퀀스 걸어줘",
    "틸트 빼줘 컬러 플라이아웃 시퀀스 생성",
    "포지션 그대로 두고 컬러 스윕 시퀀스 만들어줘",
    "무빙은 유지한 채 디머 웨이브 시퀀스 저장",
    "팬틸트 안 건드리고 컬러 서클 시퀀스 만들어",
    "빔 위치 그대로, 색만 바뀌는 발리후 시퀀스 걸어줘",
    "포지션 못 움직이게 하고 컬러 스윕 시퀀스 만들어줘",
    "무빙 안 쓰고 디머 웨이브 시퀀스 저장해줘",
    "틸트는 놔두고 컬러 서클 시퀀스 걸어줘",
    "팬 없는 컬러 발리후 시퀀스 만들어줘",
)

#: (나) 경쟁 축이 **없는** 긍정 문장 — 물을 것이 없으므로 카드 없이 진행한다.
#: 여기서 카드가 뜨면 그건 진짜 과잉이다.
POSITION_ONLY = (
    "포지션 스윕 시퀀스 만들어줘",
    "빔이 움직이는 서클 시퀀스 만들어줘",
    "무빙 웨이브 시퀀스 저장해줘",
    "팬 틸트로 발리후 시퀀스 걸어줘",
)

#: (가) 두 축을 **다 지목한** 문장 — 카드가 뜨는 것이 **정답**이다.
#:
#: 이 목록을 「없애야 할 과잉」으로 읽지 말 것. 사용자가 컬러와 포지션을 모두
#: 말했으면 어느 쪽이 움직이는지는 문장이 정하지 않는다. 여기서 하나를 조용히
#: 고르는 것이 이 파일이 막으려는 바로 그 동작이다.
ACCEPTED_COST = (
    # 저장소 테스트(`test_web_session.py`)에 이미 있던 문장. 내 코퍼스에는
    # 없었고, 그래서 「(나) = 0, 과잉 비용 없음」이라는 잘못된 결론이 나왔다.
    # 코퍼스를 새로 만들 때 **기존 테스트의 입력을 먼저 긁어오지 않은 것**이
    # 그 구멍이다.
    #
    # 이 문장은 두 축이 다 나오지만 **모호하지 않다** — 머리말이 `포지션
    # 이펙트` 이고 `컬러 프리셋도 쓰는` 은 그것을 꾸민다. 여기서 묻는 것은
    # 과잉이고, 개정 REQ-INTENT-008 이 그 비용을 명시적으로 받아들였다.
    # 「없애야 할 과잉」이 아니라 **알고 지불하는 값**으로 읽을 것.
    "컬러 프리셋도 쓰는 포지션 이펙트 서클 시퀀스 201 만들어줘, FX 프리셋 41번부터",
)

BOTH_AXES_NAMED = (
    "컬러랑 포지션 같이 도는 스윕 시퀀스 만들어줘",
    "컬러도 같이 바뀌는 포지션 스윕 시퀀스 만들어줘",
    "디머랑 무빙 둘 다 도는 웨이브 시퀀스 저장해줘",
    "포지션 건드리는 컬러 스윕 시퀀스 만들어줘",
    "컬러랑 포지션 안 빼고 다 도는 웨이브 시퀀스 저장",
)


def _conflict(text: str) -> str | None:
    return next((name for name, p in _NON_POSITION_ATTRIBUTE if p.search(text)), None)


def _verdict(text: str) -> str:
    """**실제** ChatSession._position_fx_sequence 를 몰아 판정을 읽는다.

    M2 판정을 여기에 베껴 쓰면 검사가 제 재구현을 시험하게 된다 — 실측:
    베낀 헬퍼로는 session.py 의 판정 줄을 결함으로 되돌려도 28건이 전부
    초록이었다. 그래서 메서드를 직접 부르고, 카드가 떴는지를 관측한다.
    """
    session = object.__new__(ChatSession)
    asked: list[str] = []

    def fake_ask(prompt, **kwargs):
        asked.append(prompt)
        return None  # 답을 안 고른 것으로 두면 그 자리에서 None 으로 빠진다

    def fake_read(_tag):
        return []  # 좌표 없음 → 포지션 경로에 **도달했음**이 거절문으로 드러난다

    session._ask_one = fake_ask
    session._read_pointing_coordinates = fake_read

    result = session._position_fx_sequence(text)
    if asked:
        return "card"
    return "veto" if result is None else "position"


# ---------------------------------------------------------------------------
# 공허 방지 — 경쟁 축이 0개인 입력만 쓰면 이 판정은 한 번도 돌지 않는다.
# ---------------------------------------------------------------------------


def test_the_corpus_actually_exercises_the_competing_axis_branch():
    """경쟁 축이 실제로 잡히는 문장이 양쪽 코퍼스에 다 있어야 한다."""
    # 빈 목록에서 all() 은 참이다 — 개수를 먼저 못 박지 않으면 공허 방지
    # 자신이 공허해진다(뮤테이션 M3 실측: ACCEPTED_COST 를 비우자 검사가
    # 물지 않고 skip 으로 넘어갔다).
    assert len(EXCLUSIONS) >= 16
    assert len(POSITION_ONLY) >= 4
    assert len(BOTH_AXES_NAMED) >= 5
    assert len(ACCEPTED_COST) >= 1
    assert sum(_conflict(t) is not None for t in EXCLUSIONS) >= 10
    assert all(_conflict(t) is not None for t in BOTH_AXES_NAMED)
    assert all(_conflict(t) is not None for t in ACCEPTED_COST)
    assert not any(_conflict(t) is not None for t in POSITION_ONLY)


def test_the_exclusion_corpus_uses_the_position_words_it_excludes():
    """배제 문장이 포지션 낱말을 **쓴다**는 것이 이 결함의 전제다.

    낱말이 안 나오는 문장만 모으면 어휘 판정도 통과해 버려, 이 검사가 무엇을
    지키는지 알 수 없게 된다.
    """
    naming = [t for t in EXCLUSIONS if _POSITION_AXIS_CLAIM.search(t)]
    assert len(naming) >= 12


# ---------------------------------------------------------------------------
# 누출 — 코퍼스 전량
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", EXCLUSIONS)
def test_an_excluded_axis_never_proceeds_silently(text: str):
    assert _verdict(text) != "position", text


# ---------------------------------------------------------------------------
# (나) 과잉 — 경쟁 축이 없으면 묻지 않는다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", POSITION_ONLY)
def test_a_position_only_request_is_not_carded(text: str):
    assert _verdict(text) == "position", text


# ---------------------------------------------------------------------------
# (가) 카드가 정답인 자리
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", BOTH_AXES_NAMED)
def test_naming_both_axes_is_answered_by_the_card_not_by_vocabulary(text: str):
    """두 축이 다 나오면 문장이 축을 정하지 않는다 — 카드가 정답이다."""
    assert _verdict(text) == "card", text


def test_the_answer_string_is_where_the_lexical_predicate_belongs():
    """`_POSITION_AXIS_CLAIM` 의 정당한 용도 — 통제된 선택지 문자열.

    선택지는 이 코드가 직접 만들었으므로 어휘와 의도가 같은 것을 가리킨다.
    이 성질이 깨지면 카드의 답을 읽는 자리가 조용히 틀린다.
    """
    assert _POSITION_AXIS_CLAIM.search("빔이 움직인다 (포지션 이펙트)") is not None
    assert _POSITION_AXIS_CLAIM.search("색(컬러)이 바뀐다 (장비는 고정)") is None
    assert _POSITION_AXIS_CLAIM.search("밝기(디머)이 바뀐다 (장비는 고정)") is None


@pytest.mark.parametrize("text", ACCEPTED_COST)
def test_an_unambiguous_sentence_is_carded_anyway_at_a_known_cost(text: str):
    """모호하지 않은 문장에도 카드가 뜬다 — 개정 SPEC 이 받아들인 비용이다.

    이 테스트가 빨개지면 비용이 사라진 것이므로 좋은 소식이지만, 그때는
    REQ-INTENT-008 의 [받아들인 비용] 문단과 AC-INTENT-005 도 함께 고쳐야
    한다. 비용을 줄이려면 낱말이 아니라 **문장 구조(머리말)** 를 읽어야 하고,
    그건 이 카드의 범위가 아니었다.
    """
    assert _verdict(text) == "card", text
