"""t479 — 고친 곡 되읽기를 실기 콘솔(시퀀스 210 · 타임코드 9, t474 가 넣은 것)에 읽기로만 댄다.

앱과 같은 `build_console_stack` 의 게이트 상태 포트로 `state` · `props` 만 보낸다. 쓰기 0.
자동 쇼 저장(SaveShow)은 보내지 않게 바꿔 끼운다(t474 감독 결정과 같다).

기대값은 t474 에서 승인·반영한 13개 큐의 TrigTime
(`.moai/reports/t474/run8_cue_props.txt` 와 같은 값).
고치기 전 판정(`_validate_song_sequence_readback` 을 자식만으로)과 고친 뒤 판정을 나란히 찍는다.

실행: uv run python .moai/reports/t479/live_readback_check.py
"""

from __future__ import annotations

from server.safety.bootstrap import build_console_stack
from server.web.session import (
    ChatSession,
    _SongTimedCueExpectation,
    _validate_song_sequence_readback,
    _validate_song_timecode_readback,
)

EXPECTED = (
    (1, "0"),
    (2, "20.939"),
    (3, "33.568"),
    (4, "49.515"),
    (5, "66.517"),
    (6, "79.595"),
    (7, "106.432"),
    (8, "123.008"),
    (9, "138.581"),
    (10, "166.421"),
    (11, "179.061"),
    (11.5, "180.64"),
    (12, "209.141"),
)
SEQUENCE_PATH = "ShowData/DataPools/Default/Sequences/210"
TIMECODE_PATH = "ShowData/DataPools/Default/Timecodes/9"


class _Holder:
    """`_fill_readback_cue_properties` 가 쓰는 속성 하나만 가진 대역 — 세션 전체를 띄우지 않는다."""

    def __init__(self, port):
        self._readback_props_port = port


stack = build_console_stack(send_port=8000, receive_port=9005, attempt_session_backup=False)
stack.backup._backup_action = lambda: None  # SaveShow 를 보내지 않는다
try:
    port = stack.gate.state_port
    expectations = tuple(
        _SongTimedCueExpectation(cue_no=float(cue), trig_time=token) for cue, token in EXPECTED
    )
    sequence = port.query_state(SEQUENCE_PATH)
    timecode = port.query_state(TIMECODE_PATH)
    before = _validate_song_sequence_readback(sequence, expectations)
    filled, props_failure = ChatSession._fill_readback_cue_properties(
        _Holder(port), sequence, SEQUENCE_PATH, expectations
    )
    after = props_failure or _validate_song_sequence_readback(filled, expectations)
    timecode_failure = _validate_song_timecode_readback(timecode, 9)
finally:
    stack.stop()

print(f"children={len(sequence.get('children', []))}")
print(f"고치기 전 판정: {before or '통과'}")
print(f"고친 뒤 판정: {after or '통과'}")
print(f"타임코드 9 판정: {timecode_failure or '통과'}")
