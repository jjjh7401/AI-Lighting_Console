"""t295 — 반영 요청이 편집 라우트에 삼켜지는 오라우팅.

실측 재현(t293 부수 관측, 2026-09-06): 「이 곡 큐시트를 콘솔 시퀀스 3에
올려줘」가 **편집** 라우트로 갔다. 두 사실이 겹쳤다:

* `_DRAFT_APPLY_REQUEST` 는 `콘솔[에은는]?\\s*(반영|적용|전송|올려|보내)` 라
  콘솔과 동사가 **붙어** 있어야 한다. 사이에 「시퀀스 3에」가 끼면 안 맞는다.
* `cue_sheet_edit._BRIGHTER` 는 「올려」를 조도 올림 동사로 읽고, 문장은 t290
  판별기(40자·한 줄·곡 서술 표지 없음)를 통과한다.

두 방향 중 **더 위험한 쪽**이다: 감독은 데스크에 보냈다고 믿는데 아무것도
나가지 않았고, 대신 요청하지도 않은 조도가 움직인다.

고친 자리는 반영 술어 하나다(`session._is_draft_apply_request`) — 편집 쪽
t290 판별기는 손대지 않는다. 그래서 이 파일은 반영 술어의 정밀도를 두 코퍼스
전량에 대고 재고, 근접 오답 두 방향을 이름 붙여 고정한다.
"""

from __future__ import annotations

import pytest

from server.design.cue_sheet_edit import parse_cue_sheet_edit_request
from server.tests.test_cue_sheet_edit import (
    ANCHORLESS_CUE_COMMANDS,
    FADE_COMMANDS_WITHOUT_AN_EDIT_VERB,
    STILL_REFUSED_WITH_A_SELECTION,
)
from server.web.session import (
    _DRAFT_APPLY_DESTINATION,
    _DRAFT_APPLY_EDIT_OBJECT,
    _DRAFT_APPLY_MAX_CHARS,
    _DRAFT_APPLY_NEGATED,
    _DRAFT_APPLY_VERB,
    _is_draft_apply_request,
)

#: 반영으로 가야 하는 문장. 목적지(콘솔·데스크·초안·시퀀스 N)와 보내는 동사가
#: 함께 있다. 첫 줄이 t295 의 재현 문장이다.
APPLY_REQUESTS = (
    "이 곡 큐시트를 콘솔 시퀀스 3에 올려줘",
    "시퀀스 3에 반영해줘",
    "콘솔에 보내줘",
    "초안을 콘솔에 반영해줘",
    "시퀀스 210에 초안을 콘솔에 반영해줘",
    "초안 적용해줘",
    "데스크로 전송해줘",
)

#: 반영이 **아닌** 문장. 큐시트 칸을 고치라는 편집이거나, 목적지가 없다.
#: 「큐 3 조도 올려줘」가 근접 오답의 한쪽 끝이다 — 숫자가 있고 올림 동사가
#: 있지만 목적지가 없고, 올리는 대상이 큐시트 칸(조도)이다.
NOT_APPLY_REQUESTS = (
    "큐 3 조도 올려줘",
    "더 밝게",
    "조도 80으로 바꿔줘",
    "이 구간 페이드 3초로 바꿔줘",
    "시퀀스 3의 큐 2 조도 올려줘",
    "라이브러리에 저장해줘",
    # 근접 오답 ②: 부정. 반대 뜻인데 목적지와 동사가 다 들어 있다.
    "아직 콘솔에는 반영하지 말아줘",
    # 근접 오답 ③: 곡 설계 브리핑. 목적지(시퀀스 110)와 동사(올리고)를 함께
    # 갖고 있어 축을 넓히자마자 실제로 샜다(설계 인터뷰 1건이 깨졌다).
    "90초 록 곡 조명 설계를 만들어줘. 시퀀스 110, 프리셋 21번부터, 수동 Go. "
    "0:00 인트로는 파란색과 낮은 밝기로 시작하고, "
    "0:24 벌스에서 시안을 추가해 조금 올리고, "
    "0:48 후렴에서 마젠타와 화이트로 가장 크게 터뜨리고, "
    "1:12 마지막은 화이트 스냅으로 마무리해줘. "
    "아직 콘솔에는 적용하지 말고 검토용 타임라인만 만들어줘.",
)


@pytest.mark.parametrize("text", APPLY_REQUESTS)
def test_an_apply_shaped_request_reaches_the_apply_predicate(text):
    """t295 재현: 첫 문장이 오늘의 술어로는 거짓을 답했다."""
    assert _is_draft_apply_request(text) is True


@pytest.mark.parametrize("text", NOT_APPLY_REQUESTS)
def test_an_edit_shaped_request_does_not_reach_the_apply_predicate(text):
    assert _is_draft_apply_request(text) is False


@pytest.mark.parametrize("text", ANCHORLESS_CUE_COMMANDS)
def test_the_t290_short_command_corpus_never_leaks_into_apply(text):
    """t290 이 받기로 한 짧은 명령 7건은 반영으로 새면 안 된다."""
    assert _is_draft_apply_request(text) is False


@pytest.mark.parametrize("text", STILL_REFUSED_WITH_A_SELECTION)
def test_the_t290_song_brief_corpus_never_leaks_into_apply(text):
    """t290 이 거절하기로 한 곡 브리핑 6건도 반영으로 새면 안 된다."""
    assert _is_draft_apply_request(text) is False


def test_the_apply_discriminator_precision_on_every_corpus():
    """반영 술어의 정밀도를 숫자로 남긴다 — 네 코퍼스 전량에 대고 잰다."""
    accepted = [t for t in APPLY_REQUESTS if _is_draft_apply_request(t)]
    leaked_edit = [t for t in NOT_APPLY_REQUESTS if _is_draft_apply_request(t)]
    leaked_short = [t for t in ANCHORLESS_CUE_COMMANDS if _is_draft_apply_request(t)]
    leaked_brief = [t for t in STILL_REFUSED_WITH_A_SELECTION if _is_draft_apply_request(t)]
    assert len(accepted) == len(APPLY_REQUESTS)  # 재현율 7/7
    assert leaked_edit == []  # 거짓양성 0/6
    assert leaked_short == []  # 거짓양성 0/7 (t290 짧은 명령)
    assert leaked_brief == []  # 거짓양성 0/6 (t290 곡 브리핑)


def test_the_misrouted_apply_no_longer_moves_an_intensity_the_director_never_asked_for(
    tmp_path,
):
    """t295 의 실제 피해를 세션 층에서 고정한다.

    고치기 전: 이 문장이 편집으로 가서 고른 큐(Q010)의 조도가 60→80 으로 움직이고,
    콘솔에는 0건이 나갔다 — 감독은 데스크에 보냈다고 믿는다.
    고친 뒤: 반영 라우트가 받고, 기준본이 없으므로 「달라진 큐가 없다」로 거절한다.
    어느 쪽이든 조도는 움직이지 않는다.
    """
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession, SongTimelineStore
    from server.web.timeline_library import SongTimelineLibrary

    from .test_safety_gate import FakeConsole
    from .test_web_cue_sheet_apply import RefusingProvider, _timeline

    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    store = SongTimelineStore()
    store.latest = _timeline()
    session = ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=channel),
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=[].append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )

    session.run_instruction("이 곡 큐시트를 콘솔 시퀀스 3에 올려줘", 10)

    assert store.latest["sections"][0]["intensity"] == [{"group": "KEY", "level": 60}]
    assert store.latest["sections"][0]["d_level"] == 3
    assert console.executed == []


def test_the_edit_route_still_owns_the_near_miss_that_mentions_a_number():
    """근접 오답 ①: 숫자를 낀 진짜 조도 편집은 편집이 계속 가져간다."""
    request = parse_cue_sheet_edit_request("큐 3 조도 올려줘")
    assert request is not None
    assert request["cue"] == 3
    assert request["changes"] == {"intensity_delta": 20}


# -- t297: 「이 시퀀스 조도 올려줘」는 반영이 아니다 -------------------------------


def test_a_sequence_worded_brightness_edit_does_not_reach_the_apply_predicate():
    """카드 t297 의 진단은 오늘의 코드에 대고 재보면 성립하지 않는다.

    카드는 이 문장이 「`시퀀스` + `올려` 로 2점을 받아 반영으로 가고, 시퀀스
    번호가 없어 거절된다」고 적었다. 실측(2026-09-06, 이 트리): 반영 술어는
    **거짓**을 답한다. 두 축이 각각 막고 있다 —

    * 목적지 축은 `시퀀스\\s*\\d+` 라 숫자를 요구하고, 「이 시퀀스」에는 없다.
    * 올림-대상 축(`_DRAFT_APPLY_EDIT_OBJECT`)이 「조도 올려」를 잡아낸다.

    즉 t297 이 고쳐 달라던 자리는 이미 닫혀 있고, 판별기를 약하게 만들 이유가
    없다. 이 시험은 그 사실을 고정한다.
    """
    text = "이 시퀀스 조도 올려줘"
    assert _DRAFT_APPLY_DESTINATION.search(text) is None
    assert _DRAFT_APPLY_EDIT_OBJECT.search(text) is not None
    assert _is_draft_apply_request(text) is False


def test_a_sequence_worded_brightness_edit_reaches_the_edit_route_when_a_cue_is_selected():
    """남은 절반: 선택된 큐가 있으면 편집이 받는다(t290 판별기 그대로)."""
    assert parse_cue_sheet_edit_request("이 시퀀스 조도 올려줘", cue_selected=True) == {
        "cue": None,
        "changes": {"intensity_delta": 20},
    }


# -- t298: 40자 천장을 실제로 재본다 ---------------------------------------------
#
# 천장의 근거는 실측된 누수 한 건(197자 브리핑)이었지만, 「진짜 반영 지시가
# 40자를 넘는 일이 얼마나 되는가」는 아무도 재지 않았다. 아래가 그 측정이다.

#: 감독이 실제로 칠 법한 반영 지시. 짧은 것부터 길게 — 곡 제목·시퀀스 번호·
#: 수식어를 함께 실은 문장까지 포함한다.
REALISTIC_APPLY_INSTRUCTIONS = (
    "콘솔에 반영해줘",
    "초안 적용해줘",
    "데스크로 전송해줘",
    "시퀀스 3에 반영해줘",
    "시퀀스 210에 반영해줘",
    "이 큐시트를 콘솔에 올려줘",
    "지금 초안을 콘솔에 반영해줘",
    "큐시트를 시퀀스 3에 적용해줘",
    "방금 고친 초안을 콘솔에 반영해줘",
    "이 곡 큐시트를 콘솔 시퀀스 3에 올려줘",
    "수정한 큐시트를 시퀀스 210에 반영해줘",
    "Sugar 큐시트를 시퀀스 210에 반영해줘",
    "Sugar 큐시트 초안을 콘솔 시퀀스 210에 반영해줘",
    "방금 고친 Sugar 큐시트를 콘솔 시퀀스 210에 반영해줘",
    "검토 끝났으니 이 곡 큐시트 초안을 콘솔 시퀀스 210에 그대로 반영해줘",
)


def test_no_realistic_apply_instruction_exceeds_the_ceiling():
    """측정값을 숫자로 남긴다: 15건 중 40자 초과 **0건**, 최장 40자.

    최장 문장이 천장에 **정확히 닿는다** — 여유가 0자다. 이 사실은 기록하되
    천장을 올리지는 않았다: 아래 시험이 그 근거를 잰다.
    """
    over = [text for text in REALISTIC_APPLY_INSTRUCTIONS if len(text) > _DRAFT_APPLY_MAX_CHARS]
    assert over == []
    assert max(len(text) for text in REALISTIC_APPLY_INSTRUCTIONS) == _DRAFT_APPLY_MAX_CHARS == 40


@pytest.mark.parametrize("text", REALISTIC_APPLY_INSTRUCTIONS)
def test_every_realistic_apply_instruction_reaches_the_apply_predicate(text):
    assert _is_draft_apply_request(text) is True


def test_no_measured_negative_is_stopped_by_the_length_ceiling_alone():
    """천장을 **올리지 않기로** 한 근거. 두 사실이 함께 나왔다.

    ① 알려진 부정 코퍼스 어느 것도 길이 축에 의존하지 않는다 — 길이 검사를
       빼고 나머지 네 축만 돌려도 새는 문장이 0건이다(197자 브리핑은 「적용하지
       말고」 부정 축이 잡는다). 즉 40이라는 값 자체를 지지하는 관측은 없다.
    ② 그렇다고 올릴 근거도 없다. 41~60자 구간은 곡 브리핑이 목적지와 동사를
       함께 갖고 들어오는 대역이라, 넓히면 그쪽으로 열린다.

    관측이 어느 쪽도 지지하지 않으므로 **현행 유지**한다. 감으로 올리지 않는다.
    """

    def survives_every_axis_but_length(text: str) -> bool:
        stripped = text.strip()
        if "\n" in stripped:
            return False
        return (
            _DRAFT_APPLY_NEGATED.search(stripped) is None
            and _DRAFT_APPLY_EDIT_OBJECT.search(stripped) is None
            and _DRAFT_APPLY_DESTINATION.search(stripped) is not None
            and _DRAFT_APPLY_VERB.search(stripped) is not None
        )

    negatives = (*NOT_APPLY_REQUESTS, *ANCHORLESS_CUE_COMMANDS, *STILL_REFUSED_WITH_A_SELECTION)
    assert [text for text in negatives if survives_every_axis_but_length(text)] == []


# -- t300 코퍼스가 반영으로 새지 않는다 -------------------------------------------


@pytest.mark.parametrize("text", FADE_COMMANDS_WITHOUT_AN_EDIT_VERB)
def test_the_t300_fade_corpus_never_leaks_into_apply(text):
    assert _is_draft_apply_request(text) is False
