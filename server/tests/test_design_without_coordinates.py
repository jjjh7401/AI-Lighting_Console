"""t311 — 좌표 없는 리그도 큐 시트를 받는다.

t310 이 고정한 현재 동작은 「좌표를 못 읽으면 디자인이 통째로 멈춘다」였다.
그 멈춤은 손실보다 훨씬 넓었다: 좌표가 주지 못하는 것은 포지션(무브) 축
하나뿐이고, 조도와 컬러는 좌표를 보지 않는다. 2026-09-07 브라우저 실측에서
패치 없는 리그로 업로드·분석·구간 확인까지 다 지나간 뒤 디자인 요청 하나가
문장 한 줄로 끝났다.

여기 고정하는 것은 셋이다.

1. **좌표가 없어도 큐가 나온다** — 큐 개수, 조도·컬러의 존재, 포지션의 부재,
   그리고 부재의 **사유 문자열**까지.
2. **조준(FOCUS/LOOK)은 여전히 거절한다** — 빛을 조준하는 일 자체가 기하라서
   거기서는 멈추는 것이 옳다. 같은 판독을 공유하지만 중단 여부는 호출자가 정한다.
3. **좌표가 있는 리그는 그대로다** — 큐도, 포지션도 오늘 이전과 같다.
"""

from __future__ import annotations

import json

from server.web.question import UNANSWERED

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import TestSongDesignInterviewSession as _Harness
from .test_web_session import _session

#: 인터뷰 답 — 좌표가 없으면 Q4(공간 스토리)를 **묻지 않으므로** 5장
#: (Q1/Q2/Q2B/Q3/Q5)이다.
_ANSWERS_NO_COORDS = ["우주", "우주 색 조합", "", "Ring In", "템포 맞춤 (BPM 기준)"]
#: 좌표가 있으면 오늘과 같은 6장(Q1/Q2/Q2B/Q3/Q4/Q5).
_ANSWERS_WITH_COORDS = [
    "우주",
    "우주 색 조합",
    "",  # Q2B_COLOR_USAGE default-accepted
    "Ring In",
    "우주 컨셉 우선 배치",
    "템포 맞춤 (BPM 기준)",
]

_REQUEST = (
    "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7: "
    "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
)

#: 감독이 읽는 사유. 문면 자체가 계약이라 여기서 그대로 못 박는다.
COORD_GAP_NOTICE = (
    "3D 좌표를 읽지 못해 포지션(무브) 축은 만들지 못했습니다 — "
    "조도·컬러 큐만 설계했습니다. 콘솔 연결과 패치를 확인해 주세요."
)


def _drive(tmp_path, *, spatial_fails: bool):
    harness = _Harness()
    session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
    calls: list = []
    session._registry = harness._registry(calls, spatial_fails=spatial_fails)
    answers = _ANSWERS_NO_COORDS if spatial_fails else _ANSWERS_WITH_COORDS
    channel = harness._Channel(list(answers))
    session._question_channel = channel
    event = session.run_instruction(_REQUEST)
    timelines = [item["timeline"] for item in sent if item["type"] == "song_timeline"]
    return event, channel, timelines, calls


class TestACoordinatelessRigStillGetsCues:
    def test_the_design_reaches_the_approval_card(self, tmp_path):
        # 대조: t310 의 핀은 여기서 「연출 인터뷰를 시작하지 않았습니다」였다.
        _event, channel, _timelines, _calls = _drive(tmp_path, spatial_fails=True)
        assert any("전곡 리뷰 번들" in request.prompt for request in channel.asked)

    def test_the_timeline_carries_a_cue_per_section(self, tmp_path):
        _event, _channel, timelines, _calls = _drive(tmp_path, spatial_fails=True)
        assert timelines, "좌표가 없다고 타임라인이 아예 안 나가면 안 된다"
        assert len(timelines[-1]["sections"]) == 2

    def test_intensity_and_colour_survive(self, tmp_path):
        _event, _channel, timelines, _calls = _drive(tmp_path, spatial_fails=True)
        for section in timelines[-1]["sections"]:
            assert isinstance(section["d_level"], int) and 1 <= section["d_level"] <= 5
            assert section["palette"], "컬러는 좌표를 보지 않는다"

    def test_the_position_column_is_empty_not_invented(self, tmp_path):
        _event, _channel, timelines, _calls = _drive(tmp_path, spatial_fails=True)
        sections = timelines[-1]["sections"]
        assert [section["position"] for section in sections] == ["", ""]
        # 큐시트의 MOVE 칸도 같이 빈다 — `requested` 후보로 되돌아가면 그것이
        # 곧 지어낸 포지션이다.
        # (값이 없는 필드는 payload 에서 아예 빠진다 — 빈 문자열도 아니다.)
        assert [section.get("movement") for section in sections] == [None, None]

    def test_the_reason_is_named_on_the_timeline(self, tmp_path):
        _event, _channel, timelines, _calls = _drive(tmp_path, spatial_fails=True)
        timeline = timelines[-1]
        assert COORD_GAP_NOTICE in timeline["warnings"]
        assert {"axis": "position", "section_index": None, "reason": COORD_GAP_NOTICE} in timeline[
            "disabled"
        ]

    def test_the_reason_is_named_in_the_reply(self, tmp_path):
        event, _channel, _timelines, _calls = _drive(tmp_path, spatial_fails=True)
        assert COORD_GAP_NOTICE in event["text"]

    def test_the_review_line_does_not_read_as_a_choice(self, tmp_path):
        # 「포지션 유지」는 감독이 고른 결과처럼 읽힌다 — 고른 적이 없다.
        _event, channel, _timelines, _calls = _drive(tmp_path, spatial_fails=True)
        review = next(request for request in channel.asked if "전곡 리뷰 번들" in request.prompt)
        assert "포지션 불가(좌표 없음)" in review.prompt
        assert "포지션 유지" not in review.prompt

    def test_the_spatial_story_card_is_not_asked(self, tmp_path):
        # 기본값으로 조용히 답하지도 않는다: 카드가 아예 없다.
        _event, channel, _timelines, _calls = _drive(tmp_path, spatial_fails=True)
        prompts = [request.prompt for request in channel.asked]
        assert not any("무대가 어떻게 달라 보이면" in prompt for prompt in prompts)
        assert len([p for p in prompts if "전곡 리뷰 번들" not in p]) == 5

    def test_no_console_write_happens_before_approval(self, tmp_path):
        _event, _channel, _timelines, calls = _drive(tmp_path, spatial_fails=True)
        assert [call for call in calls if call.name == "run_commands"] == []


class TestAimingStillRefuses:
    """조준은 좌표가 곧 그 기능이다 — 여기서 멈추는 것은 결함이 아니다."""

    def _aim(self, tmp_path, instruction):
        harness = _Harness()
        session, _console, _audit, _sent, _ = _session(tmp_path, ScriptedProvider([]))
        calls: list = []
        session._registry = harness._registry(calls, spatial_fails=True)
        session._question_channel = harness._Channel([])
        return session.run_instruction(instruction), calls

    def test_focus_refuses_with_its_own_reason(self, tmp_path):
        event, calls = self._aim(tmp_path, "무빙 헤드를 무대 중앙으로 조준해줘")
        assert "3D 좌표를 읽지 못해 조명 방향 변경을 시작하지 않았습니다." in event["text"]
        assert "콘솔 연결을 확인해 주세요." in event["text"]
        assert [call for call in calls if call.name == "run_commands"] == []

    def test_the_aim_refusal_is_not_the_design_notice(self, tmp_path):
        # 같은 판독, 다른 문장 — 공유 헬퍼가 호출자를 가른다는 것의 관측 가능한 면.
        event, _calls = self._aim(tmp_path, "무빙 헤드를 무대 중앙으로 조준해줘")
        assert COORD_GAP_NOTICE not in event["text"]


class TestACoordinateRigIsUnchanged:
    def test_the_position_column_still_carries_presets(self, tmp_path):
        _event, _channel, timelines, _calls = _drive(tmp_path, spatial_fails=False)
        sections = timelines[-1]["sections"]
        assert all(section["position"] for section in sections), sections
        assert all(section["movement"] for section in sections), sections

    def test_no_gap_notice_appears(self, tmp_path):
        event, _channel, timelines, _calls = _drive(tmp_path, spatial_fails=False)
        assert "포지션(무브) 축은 만들지 못했습니다" not in event["text"]
        assert not [note for note in timelines[-1]["disabled"] if note["axis"] == "position"]

    def test_the_five_cards_are_still_asked(self, tmp_path):
        _event, channel, _timelines, _calls = _drive(tmp_path, spatial_fails=False)
        prompts = [request.prompt for request in channel.asked]
        assert any("무대가 어떻게 달라 보이면" in prompt for prompt in prompts)
        assert len([p for p in prompts if "전곡 리뷰 번들" not in p]) == 6


def test_the_two_rigs_differ_only_in_the_position_axis(tmp_path):
    """대조군 — 두 리그의 큐를 나란히 놓고 **무엇만** 달라졌는지 잰다.

    카드 t387 — `position_source`/`position_candidates` 는 position 축의
    일부다(값 자체는 아니지만 그 출처·후보). 좌표 유무에 따라 포지션
    결정 경로 자체가 바뀌면(`section_mood` vs `director_intent`) 이 두
    필드도 함께 달라지는 게 맞다 — position/movement 만 벗기던 기존
    화이트리스트에 이 둘을 추가한다.
    """
    _e1, _c1, without, _k1 = _drive(tmp_path, spatial_fails=True)
    _e2, _c2, with_coords, _k2 = _drive(tmp_path, spatial_fails=False)
    position_axis_keys = ("position", "movement", "position_source", "position_candidates")
    stripped = [
        {key: value for key, value in section.items() if key not in position_axis_keys}
        for section in without[-1]["sections"]
    ]
    reference = [
        {key: value for key, value in section.items() if key not in position_axis_keys}
        for section in with_coords[-1]["sections"]
    ]
    assert json.dumps(stripped, sort_keys=True) == json.dumps(reference, sort_keys=True)


def test_the_question_channel_reports_unanswered_when_exhausted():
    """답을 다 소진한 채널은 UNANSWERED 를 돌려준다 — 위 흐름의 전제."""
    channel = _Harness._Channel([])
    assert channel.ask(object()) is UNANSWERED
