"""「⇪ 콘솔에 반영」 단계별 시간 계측 시험 (SPEC-LDRHYTHM-001, 카드 apply-latency-2).

계측은 서버 로그에 단계마다 한 줄을 남긴다. 여기서는 (1) 콘솔 읽기 집계가 게이트를 거친 읽기만
세는지, (2) 단계 줄이 정해진 순서대로 빠짐없이 나오는지, (3) 실기 곡 규모(595칸, 승인 카드 2964항목
근처)에서 카드까지의 모든 단계가 기록되는지를 본다. 콘솔은 가짜 콘솔만 쓴다 — 실기 접촉 0.
"""

from __future__ import annotations

import logging

from server.observability.console_tally import ACTIVE_TALLY, ConsoleTally, counted_read
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.tests.test_beat_grid_send_t563 import (
    _APPROVED_EVIDENCE,
    RefusingProvider,
    _state_tree,
    _timeline,
)
from server.tests.test_safety_gate import FakeConsole
from server.web import apply_timing
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

#: 5 트랙 × 119마디 = 595칸 — 실기 곡 전체 칸 수와 같은 규모.
_TRACKS = (("BACK", 7), ("FOH", 3), ("WASH", 10), ("SIDE", 4), ("MOVER", 11))
_BARS = 119

_STAGE_ORDER = [
    "stage=pools_plan",
    "stage=sequences",
    "stage=ownership_pick",
    "stage=timecode",
    "stage=rig",
    "stage=dimmer_groups",
    "stage=bundle",
    "stage=precheck",
    "stage=card",
    "stage=gate_return",
    "stage=tail",
    "stage=total",
]


class _Recorder(logging.Handler):
    """계측 로거의 줄을 모은다 — 루트로 전파하지 않는 로거라 직접 붙인다."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _attach() -> _Recorder:
    recorder = _Recorder()
    apply_timing._LOG.addHandler(recorder)
    return recorder


class _CountedReads:
    """게이트의 읽기 메서드 모양만 흉내 낸다 — 집계가 세는 것만 본다."""

    @counted_read
    def _query_state(self, path: str, *, offset: int = 0) -> dict:
        return {"ok": True, "path": path, "offset": offset}

    @counted_read
    def _query_property(self, path: str, property_name: str) -> dict:
        return {"ok": True, "path": path, "name": property_name}


def test_counted_reads_land_in_the_active_tally_only() -> None:
    port = _CountedReads()
    port._query_state("DataPool/Sequences")  # 집계가 꺼져 있으면 아무것도 세지 않는다.
    tally = ConsoleTally()
    token = ACTIVE_TALLY.set(tally)
    try:
        port._query_state("DataPool/Sequences")
        port._query_property("Patch/Stages/1/Fixtures/7", "posx")
    finally:
        ACTIVE_TALLY.reset(token)
    assert tally.calls == 2
    assert tally.slowest_path in {"DataPool/Sequences", "Patch/Stages/1/Fixtures/7"}


def test_apply_clock_writes_one_line_per_stage_then_a_total() -> None:
    recorder = _attach()
    try:
        clock = apply_timing.ApplyClock()
        clock.start()
        clock.stage("pools_plan")
        clock.card(items=3, build_ms=1.0, send_ms=2.0)
        clock.finish()
    finally:
        apply_timing._LOG.removeHandler(recorder)
    assert [line.split()[1] for line in recorder.lines] == [
        "stage=pools_plan",
        "stage=card",
        "stage=tail",
        "stage=total",
    ]
    assert "items=3" in recorder.lines[1]


def _big_timeline() -> dict:
    timeline = _timeline()
    bars = []
    start_ms = 1000
    for n in range(1, _BARS + 2):
        bars.append({"bar": n, "start_ms": start_ms, "beats_ms": [start_ms]})
        start_ms += 2000
    timeline["bar_map"] = {"bpm": 112.35, "time_signature": [4, 4], "bars": bars}
    tracks = []
    for name, number in _TRACKS:
        cues = [
            {"bar": bar, "position_preset_no": "1.1", "evidence": _APPROVED_EVIDENCE}
            for bar in range(1, _BARS + 1)
        ]
        tracks.append(
            {"group_name": name, "group_no": number, "group_no_confirmed": True, "cues": cues}
        )
    timeline["beat_grid"]["tracks"] = tracks
    return timeline


def test_apply_at_595_cells_reports_every_stage_and_the_card_size(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = _big_timeline()
    sent: list[dict] = []
    channel = ApprovalChannel(timeout_seconds=1.0)

    def send_and_decline(event: dict) -> None:
        sent.append(event)
        if event.get("type") == "approval_request":
            channel.resolve(event["request_id"], approved=False)

    audit = AuditLog(tmp_path / "audit")
    gate = SafetyGate(
        console=FakeConsole(state_tree=_state_tree()), audit=audit, approval_port=channel
    )
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=send_and_decline,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    recorder = _attach()
    try:
        session.beat_grid_apply()
    finally:
        apply_timing._LOG.removeHandler(recorder)

    cards = [event for event in sent if event.get("type") == "approval_request"]
    assert len(cards) == 1
    items = len(cards[0]["items"])
    assert items > 2900, f"실기 규모(2964항목)에 못 미친다: {items}"

    assert [line.split()[1] for line in recorder.lines] == _STAGE_ORDER
    card_line = next(line for line in recorder.lines if "stage=card" in line)
    assert f"items={items}" in card_line
