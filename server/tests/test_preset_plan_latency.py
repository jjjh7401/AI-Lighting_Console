"""자동 프리셋 계획 지연 — 리드 지시 2026-10-17 (재실행 1: 요청→카드 78 초).

재실행 1 감사로그(읽기만)로 본 시간: 그룹 소속·장비 판독 약 17 초, 장비 종류 속성 약 27 초,
그룹 소속
**한 번 더** 약 7 초, 색 채널용 패치 판독 약 10 초, 위치 조준 좌표 약 6 초. 여기서 고친 것은
① 단계별 시간 로그(``apply.timing stage=plan_*``) ② 그룹 소속 한 번만 읽기 ③ 색 채널·조준 좌표를
장비 판독 캐시(120 초)에 기억하기 ④ 승인 카드의 Store Preset 사유를 한국어로.

콘솔 접촉 0건 — 가짜 콘솔과 시험 대역만 쓴다.
"""

from __future__ import annotations

import logging

from server.design.beat_grid_position_presets import PointingFrames
from server.design.rig_read_cache import KIND_MEMBERS
from server.safety.approval import ApprovalItem, ApprovalRequest
from server.web.messages import approval_request_event

from .test_planned_color_presets import _applied_grid, _card_session

_STORE_PRESET_REASON = "blacklisted command (matches closed-set entry 'Store Preset')"


class _Lines(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def test_the_store_step_reuses_the_members_the_dimmer_step_read(tmp_path, monkeypatch) -> None:
    # 디머 속성 단계가 곡의 모든 그룹 소속을 읽어 캐시에 넣었다(전체 그룹 열쇠). 저장 줄 단계는
    # 후보 그룹만으로 다시 읽지 않고 그 판독에서 꺼낸다.
    grid = _applied_grid()
    session, _console, _approval, _store = _card_session(
        tmp_path, monkeypatch, grid, decisions=(False,)
    )
    names = [str(track["group_name"]) for track in grid["tracks"]]
    members = session._beat_grid_group_members(names)
    session._rig_read_cache.put(KIND_MEMBERS, session._group_members_key(names), members)
    calls: list[list[str]] = []
    stub = session._beat_grid_group_members

    def counting(group_names, **kwargs):
        calls.append(list(group_names))
        return stub(group_names, **kwargs)

    monkeypatch.setattr(session, "_beat_grid_group_members", counting)
    session.beat_grid_preset_plan()
    assert calls == []


def test_the_store_step_reads_members_when_the_cache_has_none(tmp_path, monkeypatch) -> None:
    session, _console, _approval, _store = _card_session(
        tmp_path, monkeypatch, _applied_grid(), decisions=(False,)
    )
    calls: list[list[str]] = []
    stub = session._beat_grid_group_members

    def counting(group_names, **kwargs):
        calls.append(list(group_names))
        return stub(group_names, **kwargs)

    monkeypatch.setattr(session, "_beat_grid_group_members", counting)
    session.beat_grid_preset_plan()
    assert len(calls) == 1


def test_the_plan_logs_each_stage(tmp_path, monkeypatch) -> None:
    session, _console, _approval, _store = _card_session(
        tmp_path, monkeypatch, _applied_grid(), decisions=(False,)
    )
    handler = _Lines()
    logger = logging.getLogger("server.web.apply_timing")
    logger.addHandler(handler)
    try:
        session.beat_grid_preset_plan()
    finally:
        logger.removeHandler(handler)
    stages = [line.split()[1] for line in handler.lines if line.startswith("apply.timing")]
    for stage in (
        "stage=plan_pools",
        "stage=plan_dimmer_attributes",
        "stage=plan_build",
        "stage=plan_color_channels",
        "stage=plan_pointing_frames",
        "stage=plan_stores",
        "stage=total",
    ):
        assert stage in stages, (stage, stages)
    # 단계 줄에는 그 단계의 콘솔 읽기 수가 함께 남는다. (stage=card 줄은 실제 승인 채널이 카드를
    # 보낼 때 찍힌다 — 이 대역은 그 채널을 거치지 않는다.)
    assert all("console_reads=" in line for line in handler.lines if "stage=plan_" in line)


def test_color_channels_are_read_once_within_the_cache_window(tmp_path, monkeypatch) -> None:
    session, _console, _approval, _store = _card_session(
        tmp_path, monkeypatch, _applied_grid(), decisions=(False,)
    )
    # 대역을 걷고 진짜 함수를 쓰되, 그 안의 콘솔 판독 두 개만 센다.
    monkeypatch.delattr(session, "_beat_grid_color_channel_names")
    reads: list[str] = []

    def pairs():
        reads.append("pairs")
        return [(1, 101), (2, 102)], []

    def names(filtered, *, probe_id_prefix):
        reads.append("names")
        return {fid: ["R", "G", "B"] for _slot, fid in filtered}

    monkeypatch.setattr(session, "_color_rig_fixture_pairs", pairs)
    monkeypatch.setattr(session, "_fixture_color_channel_names", names)
    first = session._beat_grid_color_channel_names([101, 102])
    second = session._beat_grid_color_channel_names([102, 101])
    assert first == second == {101: ["R", "G", "B"], 102: ["R", "G", "B"]}
    assert reads == ["pairs", "names"]
    # 캐시를 비우면(재연결·명시적 새로고침) 다시 읽는다.
    session.invalidate_rig_read_cache()
    session._beat_grid_color_channel_names([101, 102])
    assert reads == ["pairs", "names", "pairs", "names"]


def test_a_partial_color_read_is_not_remembered(tmp_path, monkeypatch) -> None:
    session, _console, _approval, _store = _card_session(
        tmp_path, monkeypatch, _applied_grid(), decisions=(False,)
    )
    monkeypatch.delattr(session, "_beat_grid_color_channel_names")
    reads: list[str] = []
    monkeypatch.setattr(
        session, "_color_rig_fixture_pairs", lambda: (reads.append("pairs"), ([(1, 101)], [2]))[1]
    )
    monkeypatch.setattr(
        session,
        "_fixture_color_channel_names",
        lambda filtered, *, probe_id_prefix: {fid: ["R"] for _slot, fid in filtered},
    )
    session._beat_grid_color_channel_names([101, 102])
    session._beat_grid_color_channel_names([101, 102])
    assert reads == ["pairs", "pairs"]  # 102 를 못 읽어서 기억하지 않는다


def test_pointing_frames_are_read_once_within_the_cache_window(tmp_path, monkeypatch) -> None:
    session, _console, _approval, _store = _card_session(
        tmp_path, monkeypatch, _applied_grid(), decisions=(False,)
    )
    monkeypatch.delattr(session, "_beat_grid_pointing_frames")
    reads: list[str] = []

    def frames(call_id):
        reads.append(call_id)
        return [(101, (0.0, 0.0, 5.0))], {101: 0.0}, [], []

    monkeypatch.setattr(session, "_read_pointing_frames", frames)
    first = session._beat_grid_pointing_frames()
    second = session._beat_grid_pointing_frames()
    assert isinstance(first, PointingFrames)
    assert first == second
    assert len(reads) == 1


def test_the_card_shows_the_app_store_preset_reason_in_korean() -> None:
    request = ApprovalRequest(
        items=(
            ApprovalItem(command="Store Preset 4.33", risk_reasons=(_STORE_PRESET_REASON,)),
            ApprovalItem(
                command="Delete Group 3",
                risk_reasons=("blacklisted command (matches closed-set entry 'Delete')",),
            ),
        )
    )
    event = approval_request_event(request_id="r1", request=request)
    assert event["items"][0]["risk_reasons"] == ["앱이 만든 프리셋 저장 — 승인 필요"]
    # 다른 위험 명령의 사유는 그대로다 — 안전 판정의 원문을 바꾸지 않는다.
    assert event["items"][1]["risk_reasons"] == [
        "blacklisted command (matches closed-set entry 'Delete')"
    ]
