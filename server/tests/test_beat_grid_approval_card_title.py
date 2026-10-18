"""승인 카드 머리 — 앱 소유 묶음은 감독 말로 (WT-approval-card-text).

「콘솔 같이」 송신 묶음(재생·이어 재생·일시정지·정지)의 승인 카드는 머리를 감독 말로 쓴다.
영어 게이트 사유는 카드의 「자세히」 안에만 남는다. 승인이 필요한지(게이트 판정)는 그대로다.

콘솔 접촉: 0건 — ``FakeConsole`` 과 ``ScriptedApproval`` 만 쓴다.
"""

from __future__ import annotations

from server.safety.approval import ApprovalItem, ApprovalRequest
from server.web.messages import approval_request_event
from server.web.session import SongTimelineStore, _beat_grid_transport_card_title

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _timeline,
)


class TestTransportCardTitle:
    def test_play_title_names_the_backup_the_sequences_and_the_timecode(self) -> None:
        title = _beat_grid_transport_card_title(
            "play", song="러브어택", timecodes=(5,), sequence_count=11
        )

        assert title == (
            "러브어택 재생 시작 — 쇼 백업 1 · 이 곡 시퀀스 11개 끄기 · TC5 처음으로·재생"
        )

    def test_stop_title_names_the_sequences_switched_off_and_every_timecode(self) -> None:
        title = _beat_grid_transport_card_title(
            "stop", song="러브어택", timecodes=(5, 6), sequence_count=11
        )

        assert title == "러브어택 정지 — 쇼 백업 1 · 이 곡 시퀀스 11개 끄기 · TC5 · TC6 멈춤"

    def test_pause_title_says_the_sequences_are_not_switched_off(self) -> None:
        title = _beat_grid_transport_card_title(
            "pause", song="러브어택", timecodes=(5,), sequence_count=0
        )

        assert title == "러브어택 일시정지 — 쇼 백업 1 · TC5 멈춤 · 시퀀스는 끄지 않음"

    def test_resume_title_continues_from_where_it_stopped(self) -> None:
        title = _beat_grid_transport_card_title(
            "resume", song="러브어택", timecodes=(5,), sequence_count=0
        )

        assert title == "러브어택 이어 재생 — 쇼 백업 1 · TC5 멈춘 자리부터 재생"


class TestApprovalEventCarriesTheTitle:
    def test_the_event_adds_the_title_key_only_when_a_title_is_given(self) -> None:
        request = ApprovalRequest(
            items=(
                ApprovalItem(
                    command="Top Timecode 5",
                    risk_reasons=("reference-invoking command",),
                ),
            )
        )

        assert "title" not in approval_request_event(request_id="req-1", request=request)
        titled = approval_request_event(
            request_id="req-1", request=request, title="러브어택 재생 시작"
        )
        assert titled["title"] == "러브어택 재생 시작"

    def test_the_title_rides_only_on_the_approval_raised_while_the_bundle_is_dispatched(
        self, tmp_path
    ) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        _seed_record(store)
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_owned_state_tree()
        )
        sent: list[dict] = []
        session._send = sent.append  # 승인 이벤트를 소켓 대신 받는다
        request = ApprovalRequest(
            items=(
                ApprovalItem(
                    command="Top Timecode 5",
                    risk_reasons=("reference-invoking command",),
                ),
            )
        )

        session._notify_approval("req-plain", request)
        assert "title" not in sent[-1]

        def raised_during_the_bundle(tool_id, commands, **kwargs):
            # 게이트가 송신 중에 승인을 묻는 순간을 그대로 흉내 낸다.
            session._notify_approval("req-bundle", request)
            return None

        session._beat_grid_dispatch_preview = raised_during_the_bundle
        session.beat_grid_console_play()

        # 세션 승인 전 첫 ▶ 의 승인 카드는 감독 말 머리를 달고 나가야 한다.
        # (송신 응답 상태 이벤트도 같은 채널로 나가므로 승인 이벤트만 골라 본다.)
        approvals = [event for event in sent if event.get("type") == "approval_request"]
        assert approvals[-1]["request_id"] == "req-bundle"
        assert "재생 시작 — 쇼 백업 1" in approvals[-1]["title"]
        assert f"TC{TIMECODE_NUMBER} 처음으로·재생" in approvals[-1]["title"]

        # 송신이 끝난 뒤의 승인에는 제목이 남지 않는다.
        session._notify_approval("req-after", request)
        assert "title" not in sent[-1]
