"""M3 — 마디 지도 분석 프레임의 파서 (SPEC-LDBARMAP-002, 카드 t647).

AC-LDBARENTRY-002(프레임 모양: 오프셋 필수, 기본값 없음)만 다룬다. 합성 단계
(``synthesize_bar_map``)는 ``test_audio_bar_map_entry.py``, 세션 메서드는
``test_session_bar_map_entry.py``, 와이어 왕복은 ``test_web_bar_map_entry.py`` 가 잰다.

파서가 하는 일은 둘뿐이다 — 정수 ``first_beat_offset`` 이 있는지 보고, 알려진 필드만 돌려준다.
범위(0~3) 판정은 세션이 맡는다(AC-LDBARENTRY-003). 그래서 -1 과 4 도 파서는 통과시킨다.

콘솔 접촉: 0건. 순수 함수 호출만 한다.
"""

from __future__ import annotations

import json

import pytest

from server.web.messages import (
    CLIENT_MESSAGE_TYPES,
    PROTOCOL_VERSION,
    ProtocolError,
    parse_client_message,
)

_TYPE = "bar_map_analyse"


def _raw(**fields: object) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, "type": _TYPE, **fields}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# (1) 정수 여섯 — 범위 밖 정수까지 통과하고, 출력은 정확히 세 키뿐이다.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset", [0, 1, 2, 3, -1, 4])
def test_an_integer_offset_passes_with_exactly_the_three_keys(offset: int) -> None:
    parsed = parse_client_message(_raw(first_beat_offset=offset))
    assert set(parsed) == {"v", "type", "first_beat_offset"}
    assert parsed == {"v": PROTOCOL_VERSION, "type": _TYPE, "first_beat_offset": offset}
    assert type(parsed["first_beat_offset"]) is int  # bool 이 아니라 정수 그대로다


def test_the_parser_carries_no_audio_and_no_other_field() -> None:
    """프레임에 다른 필드를 얹어 보내도 파서 출력에 남지 않는다 — 알려진 필드만 돌려준다."""
    parsed = parse_client_message(
        _raw(
            first_beat_offset=2,
            time_signature=[3, 4],
            content_base64="AAAA",
            file_name="track.wav",
            mime_type="audio/wav",
            sheet_bpm="120",
        )
    )
    assert parsed == {"v": PROTOCOL_VERSION, "type": _TYPE, "first_beat_offset": 2}


# ---------------------------------------------------------------------------
# (2) 나머지 여섯 — 기본값으로 채우지 않고 프로토콜 오류로 거절한다.
# ---------------------------------------------------------------------------

_MISSING = object()

#: 필드 없음 · null · bool(참/거짓) · 실수 · 문자열 · 목록 — 그리고 0 과 같다고 읽히기 쉬운 값들.
_REJECTED = [
    pytest.param(_MISSING, id="missing"),
    pytest.param(None, id="null"),
    pytest.param(True, id="true"),
    pytest.param(False, id="false"),
    pytest.param(1.0, id="float-1.0"),
    pytest.param(0.0, id="float-0.0"),
    pytest.param("1", id="string-1"),
    pytest.param("0", id="string-0"),
    pytest.param([1], id="list"),
    pytest.param({"first_beat_offset": 1}, id="object"),
]


@pytest.mark.parametrize("value", _REJECTED)
def test_a_missing_or_non_integer_offset_is_a_protocol_error(value: object) -> None:
    fields = {} if value is _MISSING else {"first_beat_offset": value}
    with pytest.raises(ProtocolError, match="first_beat_offset") as caught:
        parse_client_message(_raw(**fields))
    # 서브클래스가 아닌 ProtocolError 그대로여야 와이어에서 kind "protocol" 로 나간다.
    assert caught.type is ProtocolError


def test_a_missing_offset_is_never_defaulted_to_zero() -> None:
    """기본값 금지의 직접 표현 — 필드가 없으면 0 으로 통과하지 않고 거절한다."""
    with pytest.raises(ProtocolError, match="first_beat_offset"):
        parse_client_message(_raw())


# ---------------------------------------------------------------------------
# (3) 새 타입은 허용 목록에 들어 있다.
# ---------------------------------------------------------------------------


def test_the_new_type_is_on_the_client_allowlist() -> None:
    assert _TYPE in CLIENT_MESSAGE_TYPES
    assert CLIENT_MESSAGE_TYPES.count(_TYPE) == 1


def test_a_misspelled_type_is_still_an_unknown_type() -> None:
    """대조군 — 허용 목록은 닫혀 있다. 철자만 다른 타입은 여전히 모르는 타입이다."""
    with pytest.raises(ProtocolError, match="unknown message type"):
        parse_client_message(
            json.dumps({"v": PROTOCOL_VERSION, "type": "bar_map_analyze", "first_beat_offset": 0})
        )


def test_a_rejected_offset_is_not_confused_with_an_unknown_type() -> None:
    """위 거절 시험이 공허하지 않다는 대조군 — 거절 사유가 「모르는 타입」이 아니라 필드다."""
    with pytest.raises(ProtocolError) as caught:
        parse_client_message(_raw(first_beat_offset="1"))
    assert "unknown message type" not in str(caught.value)
