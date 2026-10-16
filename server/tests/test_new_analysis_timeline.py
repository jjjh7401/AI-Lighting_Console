"""새 곡 분석 → 새 작업본 — 리드 지시 2026-10-16 (전 과정 진단 D1·D3).

곡을 새로 첨부해 분석을 확인하고 마디 지도까지 저장하면, 작업본은 분석 구간·마디 지도·빈 격자로
새로 시작한다. 옛 작업본은 라이브러리에 자동 백업된다. 그 빈 격자에 자동 배치를 적용하면 칸이
생긴다. 적용해서 바뀐 칸이 0개면 성공처럼 보이지 않고 실패로 알린다.

콘솔 접촉 0건 — 콘솔 대역이 받은 호출 수를 센다. 마디 지도 합성은 시험 픽스처 타임라인의
마디 지도를 돌려주는 대역이다(실제 오디오 분석은 하지 않는다).
"""

from __future__ import annotations

import base64
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from server.design.analysis_timeline import ANALYSIS_SOURCE_KEY, build_analysis_timeline
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_ui_values import SECTION_KIND_COLORS, attach_beat_grid_ui_values
from server.design.profile import resolve_bpm
from server.safety.audit import AuditLog
from server.safety.console import ExecOutcome
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.question import ConfirmedSongAnalysis, ConfirmedSongSection
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "love_attack_shape_timeline.json"


class _Console:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def execute(self, command: str) -> ExecOutcome:
        self.calls.append(("execute", command))
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        self.calls.append(("ping",))
        return True

    def query_state(self, path: str) -> dict:
        self.calls.append(("query_state", path))
        return {}


class _RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _bar_map() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["bar_map"]


def _old_timeline() -> dict:
    """옛 작업본 — 손 설계 격자(칸 있음)·옛 구간 11개·타임코드 4."""
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "song_title": "OLD TITLE",
        "sequence_number": 54,
        "timecode_number": 4,
        "sections": fixture["sections"],
        "beat_grid": copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE)),
    }


#: 분석이 낸 구간(D 레벨 라벨) — 시각은 픽스처 마디 지도의 마디 시작과 맞춘다.
_SECTIONS = (
    ("D1", 964, 15_000, 1),
    ("D4", 15_000, 44_000, 4),
    ("D2", 44_000, 70_000, 2),
    ("D5", 70_000, 100_000, 5),
    ("D3", 100_000, 130_000, 3),
    ("D1", 130_000, 160_000, 1),
)


def _session(tmp_path, monkeypatch):
    store = SongTimelineStore()
    store.latest = _old_timeline()
    sent: list[dict] = []
    console = _Console()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    library = SongTimelineLibrary(tmp_path / "library.json")
    session = ChatSession(
        gate=gate,
        provider=_RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=library,
    )
    session.upload_song_audio(
        "LOVE ATTACK.wav", "audio/wav", base64.b64encode(b"RIFF....").decode()
    )
    audio = session._song_audio
    bpm = resolve_bpm(measured_bpm=112.0, sheet_bpm=None, fx_rate=None, beats_per_cycle=None)
    session._song_analysis = ConfirmedSongAnalysis(
        source_sha256=audio.sha256,
        source_file_name=audio.file_name,
        confirmed_at=datetime.now(UTC).isoformat(),
        bpm=bpm,
        sections=tuple(
            ConfirmedSongSection(
                index=index,
                label=label,
                start_ms=start,
                end_ms=end,
                d_level=level,
                selected=True,
            )
            for index, (label, start, end, level) in enumerate(_SECTIONS)
        ),
    )
    monkeypatch.setattr("server.web.session.synthesize_bar_map", lambda _audio, _offset: _bar_map())
    sent.clear()
    return session, store, sent, console, library


def _cells(timeline: dict) -> int:
    return sum(len(track["cues"]) for track in timeline["beat_grid"]["tracks"])


def test_a_confirmed_new_analysis_starts_a_fresh_timeline(tmp_path, monkeypatch) -> None:
    session, store, sent, console, library = _session(tmp_path, monkeypatch)
    old = copy.deepcopy(store.latest)
    assert _cells(old) > 0

    session.analyse_bar_map(1)

    fresh = store.latest
    assert [s["label"] for s in fresh["sections"]] == [label for label, *_ in _SECTIONS]
    assert [s["start_ms"] for s in fresh["sections"]] == [start for _l, start, *_ in _SECTIONS]
    assert fresh["bar_map"] == _bar_map()
    # 분석이 확정한 BPM 이 실린다 — 상단 바가 「BPM —」로 비지 않는다.
    assert fresh["bpm"] == 112.0
    # 구간 종류는 D 레벨로 추정한다. 이름(D 레벨)은 바꾸지 않는다.
    assert [s["kind"] for s in fresh["sections"]] == [
        "intro",
        "verse",
        "bridge",
        "chorus",
        "verse",
        "outro",
    ]
    # 곡 이름은 새로 붙인 오디오 파일 이름이다 — 옛 작업본 이름(OLD TITLE)을 이어받지 않는다.
    assert fresh["song_title"] == LOVE_ATTACK_TITLE
    assert fresh["beat_grid"]["song_title"] == LOVE_ATTACK_TITLE
    assert _cells(fresh) == 0
    assert [t["group_name"] for t in fresh["beat_grid"]["tracks"]] == [
        t["group_name"] for t in old["beat_grid"]["tracks"]
    ]
    assert "timecode_number" not in fresh
    assert fresh[ANALYSIS_SOURCE_KEY] == session._song_audio.sha256
    # 옛 작업본은 라이브러리에 그대로 백업되고, 되돌리기로도 돌아갈 수 있다.
    [backup] = library.items()
    assert backup["name"].startswith("OLD TITLE 분석 전 백업")
    assert backup["timeline"] == old
    assert session._draft_history.depth == 1
    assert [frame["type"] for frame in sent].count("chat_response") == 1
    assert console.calls == []


def test_auto_arrangement_on_the_fresh_grid_places_cells(tmp_path, monkeypatch) -> None:
    session, store, sent, _console, _library = _session(tmp_path, monkeypatch)
    session.analyse_bar_map(1)
    proposed = session.beat_grid_draft_propose()
    session.beat_grid_draft_apply(proposed["draft_id"])
    assert _cells(store.latest) > 0


def test_the_same_analysis_does_not_start_over_twice(tmp_path, monkeypatch) -> None:
    # 같은 분석으로 이미 만든 작업본이면 마디 지도만 다시 붙이고 격자를 지우지 않는다.
    session, store, _sent, _console, library = _session(tmp_path, monkeypatch)
    session.analyse_bar_map(1)
    proposed = session.beat_grid_draft_propose()
    session.beat_grid_draft_apply(proposed["draft_id"])
    placed = _cells(store.latest)
    session.analyse_bar_map(1)
    assert _cells(store.latest) == placed
    assert len(library.items()) == 1


def test_an_apply_that_changes_nothing_is_reported_as_a_failure(tmp_path, monkeypatch) -> None:
    session, store, sent, _console, _library = _session(tmp_path, monkeypatch)
    session.analyse_bar_map(1)
    first = session.beat_grid_draft_propose()
    session.beat_grid_draft_apply(first["draft_id"])
    before = copy.deepcopy(store.latest)
    second = session.beat_grid_draft_propose()
    sent.clear()
    session.beat_grid_draft_apply(second["draft_id"])
    assert store.latest == before
    status = [frame for frame in sent if frame["type"] == "beat_grid_send_status"]
    assert status and status[-1]["ok"] is False
    assert "completed" not in status[-1]
    chat = [frame for frame in sent if frame["type"] == "chat_response"]
    assert chat and "바뀐 칸이 0개" in chat[-1]["text"]


def test_sections_starting_in_the_same_bar_keep_the_first() -> None:
    class _S:
        def __init__(self, label: str, start: int) -> None:
            self.label, self.start_ms, self.end_ms, self.d_level = label, start, start + 1, 1

    timeline = build_analysis_timeline(
        song_title="X",
        sections=[_S("A", 964), _S("B", 970), _S("C", 15_000)],
        bar_map=_bar_map(),
        layout=[],
        source_sha256="abc",
    )
    assert [s["label"] for s in timeline["sections"]] == ["A", "C"]
    assert timeline["sections"][0]["bar_count"] == timeline["sections"][1]["bar_start"]


def test_the_screen_colors_a_section_by_its_explicit_kind() -> None:
    # 이름이 「D5」뿐이어도 실린 종류(chorus)로 화면 색이 붙는다.
    timeline = {"sections": [{"label": "D5", "kind": "chorus", "start_ms": 0}]}
    [section] = attach_beat_grid_ui_values(timeline)["sections"]
    assert section["kind"] == "chorus"
    assert section["color"] == SECTION_KIND_COLORS["chorus"]


def test_bpm_falls_back_to_the_bar_map() -> None:
    timeline = build_analysis_timeline(
        song_title="X", sections=[], bar_map=_bar_map(), layout=[], source_sha256="abc"
    )
    assert timeline["bpm"] == float(_bar_map()["bpm"])
