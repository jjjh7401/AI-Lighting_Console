"""카드 WT-true-reasons — 서버가 거절·차단한 진짜 사유가 화면까지 그대로 간다.

새 곡 점검(2026-10-18)에서 반영이 「타임코드 5에 트랙 9개 — 최대 8개를 넘습니다」로 막혔는데
화면에는 「콘솔에 반영할 내용이 없습니다」만 나왔다. 트랙째 막힌 사유가 칸 목록
(``blocked_cells``)에도, 묶음 사유(``blocked_reason``)에도 실리지 않아 사라졌다.

같은 꼴의 경로를 전수로 세어 고쳤다(세는 법은 PR 본문):
- 반영 — 트랙째 막힌 사유(전부 막힘·일부 막힘).
- 미리보기·「콘솔 같이」 — 송신 실패를 참/거짓으로만 돌려받아 승인 거절·게이트 차단·콘솔
  실패가 한 문구(「감독이 미리보기 승인을 거절했습니다」)로 뭉개졌다.
- 자동 배치·제안·초안 적용·프리셋 계획 — 거절이 채팅에만 가서 전체화면에서 안 보였다.

시험은 사유 문자열을 그대로 단언한다(뭉갠 문구가 다시 들어오면 깨진다). 콘솔 접촉 0건.
"""

from __future__ import annotations

from server.design.beat_grid_emit import emit_beat_grid_write_bundle
from server.web.session import SongTimelineStore

from .test_beat_grid_reapply_t572 import (
    TIMECODE_NUMBER,
    _new_session,
    _owned_state_tree,
    _seed_record,
    _timeline,
)
from .test_new_color_preset_t594 import _apply_session

_OVER_LIMIT = (
    "타임코드 {tc}에 트랙 9개 — ①이 구조로 확인한 최대 8개"
    "(beat_grid_data/measured_console.yaml)를 넘습니다"
)
_NAMES = [f"T{i}" for i in range(1, 10)]


def _nine_track_grid() -> dict:
    return {
        "tracks": [
            {
                "group_name": name,
                "group_no": 10 + i,
                "group_no_confirmed": True,
                "cues": [{"bar": 1, "color_preset_no": "4.41", "evidence": None}],
            }
            for i, name in enumerate(_NAMES)
        ],
        "probe_results": {},
    }


class TestApplyNamesTheBlockedTracks:
    def test_all_tracks_over_the_timecode_limit_say_so(self, tmp_path) -> None:
        status, _store, approval, _console = _apply_session(
            tmp_path,
            _nine_track_grid(),
            pool4=[41],
            members={name: [101] for name in _NAMES},
        )

        assert status["ok"] is False
        assert approval.requests == []
        # 고치기 전(1081d374): "콘솔에 반영할 내용이 없습니다." — 트랙째 막힌 사유가 사라졌다.
        assert status["reason"] == (
            "콘솔에 반영할 내용이 없습니다 — 보내지 않은 트랙 9개"
            f"({', '.join(_NAMES)}): {_OVER_LIMIT.format(tc=20)}"
        )

    def test_a_partly_blocked_apply_names_the_unsent_track_on_card_and_result(
        self, tmp_path
    ) -> None:
        grid = _nine_track_grid()
        grid["tracks"] = grid["tracks"][:2]
        grid["tracks"][1]["group_no_confirmed"] = False
        status, _store, approval, _console = _apply_session(
            tmp_path, grid, pool4=[41], members={"T1": [101], "T2": [102]}
        )

        notice = (
            "보내지 않은 트랙 1개(T2): "
            "그룹 번호가 아직 확인되지 않았습니다(group_no_confirmed=False)"
        )
        assert status["ok"] is True, status
        assert notice in status["notices"]
        assert notice in " ".join(approval.requests[0].items[0].risk_reasons)

    def test_emit_result_lists_track_level_refusals_once_per_reason(self) -> None:
        from .test_beat_grid_emit_t549 import _TIMING

        tracks = _nine_track_grid()["tracks"]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={name: 300 + i for i, name in enumerate(_NAMES)},
            timecode_numbers={name: 5 for name in _NAMES},
            dimmer_attributes={name: ("Dimmer",) for name in _NAMES},
            probe_results={},
        )

        assert result.blocked_track_notices == (
            f"보내지 않은 트랙 9개({', '.join(_NAMES)}): {_OVER_LIMIT.format(tc=5)}",
        )
        # 칸 목록(blocked_cells)은 칸 단위 그대로 — 트랙째 막힘은 여기 없다.
        assert result.blocked_cells == ()


def _transport_session(tmp_path, *, decisions=(True,), fail_on=None):
    store = SongTimelineStore()
    store.latest = _timeline()
    _seed_record(store)
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_owned_state_tree(), decisions=decisions
    )
    if fail_on:
        console.fail_on.update(fail_on)
    return session, console, approval


class TestConsoleSendSaysWhyItFailed:
    def test_declined_card_says_declined_or_expired(self, tmp_path) -> None:
        session, console, _approval = _transport_session(tmp_path, decisions=(False,))

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert event["reason"] == (
            "콘솔 타임코드 명령이 실행되지 않았습니다 — 승인 카드가 거절됐거나 시간 안에 "
            "승인되지 않아 아무것도 보내지 않았습니다."
        )

    def test_console_failure_names_the_command_and_its_detail(self, tmp_path) -> None:
        go = f"Go Timecode {TIMECODE_NUMBER}"
        session, _console, _approval = _transport_session(
            tmp_path, fail_on={go: "no reply from console"}
        )

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert event["reason"] == (
            f"콘솔 타임코드 명령이 실행되지 않았습니다 — 콘솔이 명령을 실행하지 못했습니다: "
            f"{go} (no reply from console)"
        )

    def test_preapproved_console_failure_also_names_the_command(self, tmp_path) -> None:
        go = f"Go Timecode {TIMECODE_NUMBER}"
        session, console, _approval = _transport_session(tmp_path)
        assert session.beat_grid_console_play()["ok"] is True  # 세션 1회 승인
        console.fail_on[go] = "no reply from console"

        event = session.beat_grid_console_play()

        assert event["ok"] is False
        assert event["reason"] == (
            f"콘솔 타임코드 명령이 실행되지 않았습니다 — 콘솔이 명령을 실행하지 못했습니다: "
            f"{go} (no reply from console)"
        )

    def test_stop_failure_keeps_the_still_running_warning(self, tmp_path) -> None:
        session, _console, _approval = _transport_session(tmp_path, decisions=(False,))

        event = session.beat_grid_console_stop()

        assert event["reason"] == (
            "콘솔 타임코드 명령이 실행되지 않았습니다 — 승인 카드가 거절됐거나 시간 안에 "
            "승인되지 않아 아무것도 보내지 않았습니다. "
            f"콘솔 Timecode {TIMECODE_NUMBER}이(가) 아직 돌고 있을 수 있어요 — "
            "콘솔 화면을 확인해 주세요."
        )


class TestChatOnlyRefusalsReachTheGrid:
    def test_auto_arrange_without_bar_map_sends_a_failed_status(self, tmp_path) -> None:
        sent: list[dict] = []
        store = SongTimelineStore()
        timeline = _timeline()
        timeline.pop("bar_map", None)
        store.latest = timeline
        session, _console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)

        session.beat_grid_draft_propose()

        statuses = [e for e in sent if e.get("type") == "beat_grid_send_status"]
        assert [(s["last_action"], s["ok"], s["reason"]) for s in statuses] == [
            (
                "edit",
                False,
                "마디 지도가 없어 자동 배치를 만들 수 없습니다. 곡 오디오를 먼저 분석하세요.",
            )
        ]

    def test_unknown_draft_apply_sends_a_failed_status(self, tmp_path) -> None:
        sent: list[dict] = []
        store = SongTimelineStore()
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)

        session.beat_grid_draft_apply("gone")

        reasons = [e["reason"] for e in sent if e.get("type") == "beat_grid_send_status"]
        assert reasons == [
            "초안 'gone'을 찾을 수 없습니다(이미 적용·거절된 초안이거나, "
            "재연결로 보류 초안이 버려진 경우일 수 있습니다)."
        ]


def test_gate_block_says_the_gate_and_its_reason() -> None:
    from server.web.session import _console_send_refusal

    payload = {
        "gate_status": "locked",
        "notice": "",
        "commands": [{"command": "Go Timecode 5", "status": "locked", "reasons": ["live lock"]}],
    }

    assert _console_send_refusal(payload) == (
        "안전 게이트가 막아 아무것도 보내지 않았습니다(locked): live lock"
    )
