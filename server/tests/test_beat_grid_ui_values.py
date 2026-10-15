"""박자 배치 화면 값 — 트랙 둘째 줄·구간 에너지·구간 색·강조 마디 (곡·리그 일반)."""

from __future__ import annotations

import pytest

from server.audio.bar_map import BarFeatures, compute_bar_energy
from server.audio.bar_map_store import build_bar_map_payload, validate_bar_map
from server.design.beat_grid_ui_values import (
    SECTION_KIND_COLORS,
    accent_bars_from_bar_map,
    attach_beat_grid_ui_values,
    format_fid_ranges,
    section_kind,
    track_sub_info,
)
from server.design.love_attack_timeline import build_love_attack_timeline


# -- 1. 트랙 둘째 줄 -----------------------------------------------------------
def test_sub_info_full_line_for_two_different_rigs() -> None:
    first = track_sub_info(
        group_no=4,
        member_fids=list(range(201, 213)),
        complete=True,
        fixture_types={fid: "Aura XB" for fid in range(201, 213)},
    )
    assert first is not None
    assert first["text"] == "G4 · 201~212 · 12대 · Aura XB"
    assert first["fixture_count"] == 12

    second = track_sub_info(
        group_no=9,
        member_fids=[5, 6, 9],
        complete=True,
        fixture_types={5: "Spot A", 6: "Spot A", 9: "Wash B"},
    )
    assert second is not None
    assert second["text"] == "G9 · 5,6,9 · 3대 · Spot A + Wash B"
    assert second["fid_ranges"] == "5,6,9"


def test_sub_info_omits_unknown_parts() -> None:
    incomplete = track_sub_info(
        group_no=2, member_fids=[1, 2], complete=False, fixture_types={1: "X", 2: "X"}
    )
    assert incomplete == {"group_no": 2, "text": "G2"}
    no_type = track_sub_info(
        group_no=None, member_fids=[7, 8], complete=True, fixture_types={7: "X"}
    )
    assert no_type is not None
    assert "fixture_types" not in no_type
    assert no_type["text"] == "7,8 · 2대"
    assert track_sub_info(group_no=None, member_fids=[], complete=True, fixture_types=None) is None


def test_format_fid_ranges() -> None:
    assert format_fid_ranges([3, 1, 2, 2, 10]) == "1~3,10"
    assert format_fid_ranges([]) == ""


def test_sub_info_attached_to_tracks_by_group_name_case_insensitive() -> None:
    timeline = {"beat_grid": {"tracks": [{"group_name": "Mover", "cues": []}, {"group_name": "X"}]}}
    out = attach_beat_grid_ui_values(timeline, track_sub_infos={"MOVER": {"text": "G1"}})
    assert out["beat_grid"]["tracks"][0]["sub_info"] == {"text": "G1"}
    assert "sub_info" not in out["beat_grid"]["tracks"][1]
    assert "sub_info" not in timeline["beat_grid"]["tracks"][0]  # 원본 불변


# -- 3. 구간 색 ----------------------------------------------------------------
@pytest.mark.parametrize(
    ("label", "kind"),
    [
        ("인트로", "intro"),
        ("벌스 1", "verse"),
        ("프리 2", "pre-chorus"),
        ("후렴 3", "chorus"),
        ("코러스", "chorus"),
        ("브리지", "bridge"),
        ("드롭", "drop"),
        ("아웃트로", "outro"),
        ("Pre-Chorus", "pre-chorus"),
        ("Chorus 2", "chorus"),
        ("Outro", "outro"),
        ("Break", "break"),
        ("마지막 코러스", "final-chorus"),
        ("Last Chorus", "final-chorus"),
        ("final chorus", "final-chorus"),
        ("킥멈춤", "break"),
        ("덜어냄", "break"),
        ("간주", "break"),
        ("끝", "outro"),
        ("End", "outro"),
    ],
)
def test_section_kind_recognises_korean_and_english(label: str, kind: str) -> None:
    assert section_kind(label) == kind
    assert kind in SECTION_KIND_COLORS


def test_palette_matches_mockup_exactly() -> None:
    assert SECTION_KIND_COLORS == {
        "intro": "#5b6b8a",
        "bridge": "#5b6b8a",
        "verse": "#6d5ba8",
        "pre-chorus": "#8a6bc4",
        "chorus": "#c4508a",
        "final-chorus": "#e0607a",
        "drop": "#d9774f",
        "break": "#444",
        "outro": "#333",
    }


def test_unknown_label_gets_no_color() -> None:
    assert section_kind("뭔지모를구간") is None
    assert section_kind("드럼") is None
    assert section_kind("legend") is None
    out = attach_beat_grid_ui_values({"sections": [{"label": "뭔지모를구간", "start_ms": 0}]})
    assert "color" not in out["sections"][0]


def test_same_kind_same_color_across_songs() -> None:
    song_a = {"sections": [{"label": "후렴 1", "start_ms": 0}]}
    song_b = {"sections": [{"label": "Chorus", "start_ms": 5}, {"label": "벌스", "start_ms": 9}]}
    a = attach_beat_grid_ui_values(song_a)["sections"][0]["color"]
    b = attach_beat_grid_ui_values(song_b)["sections"][0]["color"]
    assert a == b == SECTION_KIND_COLORS["chorus"]


def test_love_attack_fixture_sections_all_colored() -> None:
    out = attach_beat_grid_ui_values(build_love_attack_timeline())
    assert all(section["color"] for section in out["sections"])


# -- 2. 구간 에너지 · 강조 마디 -------------------------------------------------
def _bar_map(energies: list[float | None], *, beat_ms: int = 500, events=()) -> dict:
    beats = list(range(0, len(energies) * 4 * beat_ms, beat_ms))
    return build_bar_map_payload(
        beats,
        0,
        bpm=60000 / beat_ms,
        events=events,
        bar_energy={i + 1: e for i, e in enumerate(energies) if e is not None},
    )


def test_compute_bar_energy_normalises_within_song() -> None:
    feats = [
        BarFeatures(bar=1, volume_norm=0.5, low_band_norm=0.5),
        BarFeatures(bar=2, volume_norm=1.0, low_band_norm=1.0),
        BarFeatures(bar=3, volume_norm=1.5, low_band_norm=2.5),
    ]
    energy = compute_bar_energy(feats)
    assert energy == {1: 0.0, 2: pytest.approx(0.333, abs=1e-3), 3: 1.0}
    assert compute_bar_energy(feats[:1]) == {}
    flat = [BarFeatures(bar=i, volume_norm=1.0, low_band_norm=1.0) for i in (1, 2, 3)]
    assert compute_bar_energy(flat) == {}


def test_bar_map_energy_is_validated_and_optional() -> None:
    payload = _bar_map([0.1, 0.9])
    assert validate_bar_map(payload) is None
    payload["bars"][0]["energy"] = 1.5
    assert "energy" in (validate_bar_map(payload) or "")
    legacy = _bar_map([None, None])
    assert validate_bar_map(legacy) is None
    assert all("energy" not in bar for bar in legacy["bars"])


def test_section_energy_is_mean_of_bars_inside_each_section() -> None:
    # 120 BPM(박 500ms) 4/4 -> 마디 2000ms. 마디 1~4 에너지.
    bar_map = _bar_map([0.0, 0.2, 0.8, 1.0])
    timeline = {
        "bar_map": bar_map,
        "sections": [
            {"label": "벌스", "start_ms": 0},
            {"label": "후렴", "start_ms": 4000},
        ],
    }
    sections = attach_beat_grid_ui_values(timeline)["sections"]
    assert sections[0]["energy"] == pytest.approx(0.1)
    assert sections[1]["energy"] == pytest.approx(0.9)


def test_section_energy_other_tempo_and_length() -> None:
    # 다른 곡: 90 BPM 근처(박 667ms), 3개 마디, 마지막 구간은 마디 지도 밖.
    bar_map = _bar_map([0.5, 0.5, 1.0], beat_ms=667)
    bar_ms = 4 * 667
    timeline = {
        "bar_map": bar_map,
        "sections": [
            {"label": "Intro", "start_ms": 0},
            {"label": "Drop", "start_ms": 2 * bar_ms},
            {"label": "Outro", "start_ms": 10 * bar_ms},
        ],
    }
    sections = attach_beat_grid_ui_values(timeline)["sections"]
    assert sections[0]["energy"] == 0.5
    assert sections[1]["energy"] == 1.0
    assert "energy" not in sections[2]


def test_no_energy_without_bar_map_or_without_bar_energy() -> None:
    timeline = {"sections": [{"label": "벌스", "start_ms": 0}]}
    assert "energy" not in attach_beat_grid_ui_values(timeline)["sections"][0]
    legacy = {**timeline, "bar_map": _bar_map([None, None])}
    assert "energy" not in attach_beat_grid_ui_values(legacy)["sections"][0]
    assert "accent_bars" not in attach_beat_grid_ui_values(legacy)


def test_accent_bars_from_drop_events_only() -> None:
    events = [
        {"kind": "drop", "start_bar": 2, "end_bar": 3, "start_beat": 1, "grade": "estimated"},
        {"kind": "build", "start_bar": 1, "end_bar": 1, "start_beat": 1, "grade": "measured"},
        {"kind": "drop", "start_bar": 2, "end_bar": 2, "start_beat": 1, "grade": "estimated"},
    ]
    bar_map = _bar_map([0.1, 0.5, 0.9], events=events)
    assert accent_bars_from_bar_map(bar_map) == [{"bar": 2, "kind": "drop", "grade": "estimated"}]
    out = attach_beat_grid_ui_values({"bar_map": bar_map})
    assert out["accent_bars"] == [{"bar": 2, "kind": "drop", "grade": "estimated"}]
    assert accent_bars_from_bar_map(None) == []


# -- 세션 배선 --------------------------------------------------------------
def test_session_stage_read_gives_groups_and_next_timeline_tracks_a_sub_info(tmp_path) -> None:
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession, SongTimelineStore
    from server.web.timeline_library import SongTimelineLibrary

    from .test_beat_grid_stage import FIXTURES, GROUPS, _rig
    from .test_safety_gate import FakeConsole as GateConsole

    class _NoModel:
        def complete(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("이 경로는 모델을 부르지 않는다")

    store = SongTimelineStore()
    store.latest = {"song_title": "LOVE ATTACK", "sequence_number": 210}
    sent: list[dict] = []
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    session = ChatSession(
        gate=SafetyGate(console=GateConsole(), audit=audit, approval_port=channel),
        provider=_NoModel(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    session._stage_port = _rig()
    session._rig_paths = {**session._rig_paths, "fixtures": FIXTURES, "groups": GROUPS}

    event = session.beat_grid_stage()

    assert len(sent) == 1  # 프레임을 더 보내지 않는다
    for group in event["groups"]:
        info = group["sub_info"]
        assert info["group_no"] == group["group_no"]
        assert info["fixture_count"] == len(group["member_fids"])
    replay = session.song_timeline_replay()
    assert replay is not None
    by_name = {t["group_name"]: t for t in replay["timeline"]["beat_grid"]["tracks"]}
    assert by_name["BACK"]["sub_info"]["text"].startswith("G")
    assert any("sub_info" not in t for t in by_name.values())  # 콘솔에 없는 트랙은 달지 않는다
