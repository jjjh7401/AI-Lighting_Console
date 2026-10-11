"""SPEC-LDBEAT-001 M4 — 박자 격자 전용 새 에미터 + M1 의존 게이트 (카드 t549,
REQ-LDBEAT-001/003/013, AC-LDBEAT-001/006/012/015).

콘솔 접촉 0건, 콘솔 쓰기 0건 — 순수 함수가 명령 문자열 리스트만 만든다.
"""

from __future__ import annotations

from server.design.beat_grid import default_beat_grid
from server.design.beat_grid_emit import (
    MEASURED_MAX_TIMECODE_TRACKS,
    SongTiming,
    blocked_m1_items_for_cue,
    emit_beat_grid_write_bundle,
    required_m1_items_for_cue,
)
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS, default_progress_md_path

# M1 9항목 전부 "통과" — 축 충돌·evidence.approval 검사를 M1 게이트와
# 독립적으로 재는 용도의 합성 probe_results(실제 progress.md 값이 아니다).
_ALL_M1_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}

# 실제 progress.md M1 표 그대로(①⑧만 통과, 나머지는 미확인/부분/움직임 없음)
# — card t549의 "Read the live probe results via the existing progress.md
# parser" 지시를 그대로 따른다.
_LIVE_M1 = {
    1: "통과(구조)",
    2: "미확인",
    3: "부분",
    4: "미확인",
    5: "움직임 없음",
    6: "미확인 — 문법 불명",
    7: "부분(결과 기록)",
    8: "통과",
    9: "wave 움직임 없음 · circle·발리후 미확인",
}


def _empty_cue(bar: int) -> dict:
    return {
        "bar": bar,
        "label": "",
        "brightness": {"mode": None, "value_percent": None, "preset_no": None},
        "position_preset_no": None,
        "color_preset_no": None,
        "effect_preset_no": None,
        "effect_kind": None,
        "entry": {"fade_bars": None, "mib_mode": None},
        "source_ref": None,
        "app_movement": None,
        "evidence": None,
    }


def _brightness_cue(bar: int, *, value_percent: int) -> dict:
    cue = _empty_cue(bar)
    cue["brightness"] = {"mode": "value", "value_percent": value_percent, "preset_no": None}
    return cue


def _effect_cue(bar: int, *, effect_preset_no: str, effect_kind: str = "mixed") -> dict:
    cue = _empty_cue(bar)
    cue["effect_preset_no"] = effect_preset_no
    cue["effect_kind"] = effect_kind
    cue["evidence"] = {
        "grade": "name_only",
        "approval": {"by": "supervisor", "date": "2026-10-10", "source": "test-fixture#1"},
    }
    return cue


def _app_movement_cue(bar: int, *, axes: tuple[str, ...] = ("Pan",)) -> dict:
    cue = _empty_cue(bar)
    cue["app_movement"] = {
        "shape": "wave",
        "axes": axes,
        "period_unit": "beat",
        "period_value": 2,
        "phase_spread": None,
    }
    return cue


def _position_cue(bar: int, *, position_preset_no: str, with_approval: bool = True) -> dict:
    cue = _empty_cue(bar)
    cue["position_preset_no"] = position_preset_no
    if with_approval:
        cue["evidence"] = {
            "grade": "measured",
            "approval": {"by": "supervisor", "date": "2026-10-10", "source": "test-fixture#2"},
        }
    return cue


def _track(
    group_name: str, group_no: int | None, cues: list[dict], *, confirmed: bool = True
) -> dict:
    return {
        "group_name": group_name,
        "group_no": group_no,
        "group_no_confirmed": confirmed,
        "layer_role": None,
        "cues": cues,
    }


_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.5)


class TestSongTiming:
    def test_bar1_is_the_downbeat_anchor(self) -> None:
        assert _TIMING.bar_start_seconds(1) == 1.5

    def test_bar2_is_one_bar_later(self) -> None:
        # 120 BPM, 4박/마디 → 한 마디 = 2초.
        assert _TIMING.bar_start_seconds(2) == 3.5

    def test_bar0_without_pickup_beats_is_unresolvable(self) -> None:
        assert _TIMING.bar_start_seconds(0) is None

    def test_bar0_with_pickup_beats_is_resolvable(self) -> None:
        timing = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.5, pickup_beats=2)
        # 2박 pickup, 120 BPM → 1초 당김.
        assert timing.bar_start_seconds(0) == 0.5


class TestRequiredM1ItemsForCue:
    def test_plain_brightness_value_has_no_m1_dependency(self) -> None:
        assert required_m1_items_for_cue(_brightness_cue(7, value_percent=60)) == frozenset()

    def test_effect_preset_depends_on_item_4(self) -> None:
        assert required_m1_items_for_cue(_effect_cue(3, effect_preset_no="21.1")) == frozenset({4})

    def test_app_movement_depends_on_items_5_7_9(self) -> None:
        assert required_m1_items_for_cue(_app_movement_cue(11)) == frozenset({5, 7, 9})

    def test_static_position_preset_recall_has_no_m1_dependency(self) -> None:
        # 전파(③)가 아니라 단순 리콜 — REQ-LDBEAT-001의 게이트 대상이 아니다.
        assert required_m1_items_for_cue(_position_cue(18, position_preset_no="2.1")) == frozenset()


class TestBlockedM1ItemsForCue:
    def test_blocked_against_live_m1_status(self) -> None:
        reasons = blocked_m1_items_for_cue(_effect_cue(3, effect_preset_no="21.1"), _LIVE_M1)
        assert reasons == frozenset({4})

    def test_not_blocked_when_all_required_items_pass(self) -> None:
        reasons = blocked_m1_items_for_cue(_effect_cue(3, effect_preset_no="21.1"), _ALL_M1_PASS)
        assert reasons == frozenset()

    def test_missing_status_counts_as_not_confirmed(self) -> None:
        reasons = blocked_m1_items_for_cue(_effect_cue(3, effect_preset_no="21.1"), {})
        assert reasons == frozenset({4})

    def test_measured_movement_override_opens_mover_d_tilt_wave(self) -> None:
        # 카드 t553 — group_no=12(MOVER-D) + Tilt wave는 측정된 무빙
        # 허용목록과 일치해 ⑤⑦⑨가 live M1 "움직임 없음/미확인"이어도 열린다.
        cue = _app_movement_cue(7, axes=("Tilt",))
        reasons = blocked_m1_items_for_cue(cue, _LIVE_M1, group_no=12)
        assert reasons == frozenset()

    def test_measured_movement_override_does_not_open_mover_u_pan_wave(self) -> None:
        # group_no=11(MOVER-U) + Pan은 허용목록에 없다 — 그대로 막힌다.
        cue = _app_movement_cue(11, axes=("Pan",))
        reasons = blocked_m1_items_for_cue(cue, _LIVE_M1, group_no=11)
        assert reasons == frozenset({5, 7, 9})

    def test_measured_movement_override_requires_group_no(self) -> None:
        # group_no를 안 넘기면(기본값 None) 허용목록을 조회하지 않는다 —
        # 기존 2-위치-인자 호출부(이 모듈 전체)는 바이트 동일하게 동작한다.
        cue = _app_movement_cue(7, axes=("Tilt",))
        reasons = blocked_m1_items_for_cue(cue, _LIVE_M1)
        assert reasons == frozenset({5, 7, 9})

    def test_measured_movement_override_ignores_non_movement_items(self) -> None:
        # 허용목록이 열어주는 건 app_movement 항목(5,7,9)뿐이다 — 효과
        # 프리셋(4) 같은 다른 필요 항목은 그대로 막힌다.
        cue = _effect_cue(3, effect_preset_no="21.1")
        reasons = blocked_m1_items_for_cue(cue, _LIVE_M1, group_no=12)
        assert reasons == frozenset({4})


class TestEmitBeatGridWriteBundleRefusals:
    def test_missing_timing_refuses_the_whole_bundle(self) -> None:
        tracks = [_track("FOH", 3, [_brightness_cue(7, value_percent=60)])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=None,
            sequence_numbers={"FOH": 300},
            timecode_numbers={"FOH": 30},
            dimmer_attributes={"FOH": ("Dimmer",)},
            probe_results=_ALL_M1_PASS,
        )
        assert result.blocked_reason is not None
        assert result.commands == ()

    def test_unconfirmed_group_refuses_that_track(self) -> None:
        tracks = [_track("MYSTERY", None, [_brightness_cue(7, value_percent=60)], confirmed=False)]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"MYSTERY": 300},
            timecode_numbers={"MYSTERY": 30},
            dimmer_attributes={"MYSTERY": ("Dimmer",)},
            probe_results=_ALL_M1_PASS,
        )
        assert result.blocked_reason is None
        assert len(result.tracks) == 1
        assert result.tracks[0].blocked_reason is not None
        assert result.tracks[0].commands == ()

    def test_effect_preset_cue_is_blocked_by_m1_gate_with_reason_text(self) -> None:
        tracks = [_track("BACK", 4, [_effect_cue(3, effect_preset_no="21.1")])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"BACK": 300},
            timecode_numbers={"BACK": 30},
            dimmer_attributes={},
            probe_results=_LIVE_M1,
        )
        track_result = result.tracks[0]
        assert len(track_result.cues) == 1
        cue_result = track_result.cues[0]
        assert cue_result.commands == ()
        assert cue_result.blocked_reason is not None
        assert "미확인 항목" in cue_result.blocked_reason
        assert "4" in cue_result.blocked_reason

    def test_app_movement_cue_is_blocked_by_m1_gate(self) -> None:
        tracks = [_track("MOVER-U", 11, [_app_movement_cue(11)])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"MOVER-U": 300},
            timecode_numbers={"MOVER-U": 30},
            dimmer_attributes={},
            probe_results=_LIVE_M1,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.commands == ()
        assert cue_result.blocked_reason is not None
        for item in ("5", "7", "9"):
            assert item in cue_result.blocked_reason

    def test_app_movement_cue_passes_when_all_m1_items_pass(self) -> None:
        tracks = [_track("MOVER-U", 11, [_app_movement_cue(11)])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"MOVER-U": 300},
            timecode_numbers={"MOVER-U": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.blocked_reason is None
        assert len(cue_result.commands) > 0

    def test_effect_cue_without_evidence_approval_is_blocked_even_when_m1_passes(self) -> None:
        cue = _effect_cue(3, effect_preset_no="21.1")
        cue["evidence"] = None  # 승인 없음 — REQ-LDBEAT-015(f) 위반
        tracks = [_track("BACK", 4, [cue])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"BACK": 300},
            timecode_numbers={"BACK": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.commands == ()
        assert cue_result.blocked_reason is not None
        assert "evidence" in cue_result.blocked_reason or "승인" in cue_result.blocked_reason

    def test_same_axis_conflict_between_app_movement_and_effect_preset_is_blocked(self) -> None:
        cue = _app_movement_cue(11, axes=("Tilt",))
        cue["effect_preset_no"] = "21.5"
        cue["effect_kind"] = "mixed"
        cue["evidence"] = {
            "grade": "measured",
            "approval": {"by": "supervisor", "date": "2026-10-10", "source": "test-fixture#3"},
        }
        tracks = [_track("MOVER-U", 11, [cue])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"MOVER-U": 300},
            timecode_numbers={"MOVER-U": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.commands == ()
        assert cue_result.blocked_reason is not None

    def test_brightness_value_without_dimmer_attributes_is_blocked(self) -> None:
        tracks = [_track("WASH-ALL", 10, [_brightness_cue(7, value_percent=40)])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"WASH-ALL": 300},
            timecode_numbers={"WASH-ALL": 30},
            dimmer_attributes={},  # 누락
            probe_results=_ALL_M1_PASS,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.commands == ()
        assert cue_result.blocked_reason is not None


class TestEmitBeatGridWriteBundleHappyPath:
    def test_brightness_value_cue_emits_group_selection_and_dimmer_line(self) -> None:
        tracks = [_track("WASH-ALL", 10, [_brightness_cue(7, value_percent=40)])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"WASH-ALL": 300},
            timecode_numbers={"WASH-ALL": 30},
            dimmer_attributes={"WASH-ALL": ("Dimmer",)},
            probe_results=_ALL_M1_PASS,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.blocked_reason is None
        assert any("Group 10" in line and "40" in line for line in cue_result.commands)
        assert any(line.startswith("Store Cue") for line in cue_result.commands)

    def test_dimmer_preset_cue_emits_at_preset_form_not_attribute_prefixed(self) -> None:
        cue = _empty_cue(7)
        cue["brightness"] = {"mode": "dimmer_preset", "value_percent": None, "preset_no": "1.1"}
        cue["evidence"] = {
            "grade": "name_only",
            "approval": {"by": "supervisor", "date": "2026-10-10", "source": "test-fixture#4"},
        }
        tracks = [_track("FOH", 3, [cue])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"FOH": 300},
            timecode_numbers={"FOH": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        cue_result = result.tracks[0].cues[0]
        assert cue_result.blocked_reason is None
        assert any(
            "At Preset 1.1" in line and "Attribute" not in line for line in cue_result.commands
        )

    def test_track_emits_store_sequence_and_ascii_name(self) -> None:
        tracks = [_track("FOH", 3, [])]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"FOH": 300},
            timecode_numbers={"FOH": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        track_result = result.tracks[0]
        assert "Store Sequence 300" in track_result.store_sequence_commands
        assert any(
            "Set Sequence 300 Property 'Name'" in line
            for line in track_result.store_sequence_commands
        )
        # 이름은 ASCII만(한글 0건) — songcue._ascii_label 재사용 확인.
        name_line = next(
            line for line in track_result.store_sequence_commands if "Property 'Name'" in line
        )
        assert all(ord(ch) < 128 for ch in name_line)

    def test_many_to_many_timecode_assignment_one_line_per_track(self) -> None:
        tracks = [
            _track("FOH", 3, []),
            _track("BLIND", 14, []),
        ]
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers={"FOH": 300, "BLIND": 301},
            timecode_numbers={"FOH": 30, "BLIND": 30},
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        assert result.tracks[0].assign_timecode_commands == ("Assign Sequence 300 At Timecode 30",)
        assert result.tracks[1].assign_timecode_commands == ("Assign Sequence 301 At Timecode 30",)
        assert any("Store Timecode 30" in cmd for cmd in result.commands)

    def test_exceeding_measured_max_timecode_tracks_refuses_the_whole_timecode_group(self) -> None:
        group_names = [f"G{i}" for i in range(MEASURED_MAX_TIMECODE_TRACKS + 1)]
        tracks = [_track(name, idx + 1, []) for idx, name in enumerate(group_names)]
        sequence_numbers = {name: 300 + idx for idx, name in enumerate(group_names)}
        timecode_numbers = {name: 30 for name in group_names}
        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers=sequence_numbers,
            timecode_numbers=timecode_numbers,
            dimmer_attributes={},
            probe_results=_ALL_M1_PASS,
        )
        for track_result in result.tracks:
            assert track_result.assign_timecode_commands == ()
            assert track_result.blocked_reason is not None
            assert str(MEASURED_MAX_TIMECODE_TRACKS) in track_result.blocked_reason

    def test_zero_rig_literals_in_module_source(self) -> None:
        import inspect

        from server.design import beat_grid_emit as module

        source = inspect.getsource(module)
        # 실측된 LOVE ATTACK 콘솔 그룹 번호(4/7/10/11/12/14/15)나 프리셋
        # 번호("21.1" 류)가 모듈 소스에 리터럴로 박혀 있지 않아야 한다.
        for literal in ("BACK", "SIDE-ALL", "MOVER-U", "MOVER-D", "WASH-ALL", "21.1", "2.1"):
            assert literal not in source


class TestLoveAttackIntegrationAgainstLiveM1Status:
    """실제 `default_beat_grid(LOVE_ATTACK_TITLE)` + 진짜 progress.md M1
    판정으로 어떤 칸이 막히는지를 직접 잰다(카드 t549 "blocked-cell list"
    요구) — 테스트 입력 번호(시퀀스·타임코드)는 실제 콘솔 번호가 아니다."""

    def test_blocked_and_allowed_cells_match_the_m1_gate_mapping(self) -> None:
        from server.design.beat_grid import LOVE_ATTACK_TITLE
        from server.design.beat_grid_probes import read_m1_probe_results_from_path

        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        tracks = grid["tracks"]
        probe_results = read_m1_probe_results_from_path(default_progress_md_path())

        # LOVE ATTACK은 트랙(콘솔 그룹) 8개다 — 전부를 타임코드 하나에
        # 몰면 MEASURED_MAX_TIMECODE_TRACKS(6, ①이 구조로 확인한 실제
        # 최대)를 넘어 트랙 레벨에서 전부 거절된다(그 자체로 중요한
        # 발견 — run-verdict에 별도로 기록). 이 시험은 M1 **칸** 게이트를
        # 재는 것이 목적이라 타임코드를 둘로 쪼개 그 트랙-레벨 상한을
        # 피한다(시험 입력, 콘솔 번호 아님).
        sequence_numbers = {t["group_name"]: 300 + i for i, t in enumerate(tracks)}
        timecode_numbers = {t["group_name"]: (30 if i < 4 else 31) for i, t in enumerate(tracks)}
        dimmer_attributes = {t["group_name"]: ("Dimmer",) for t in tracks}

        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers=sequence_numbers,
            timecode_numbers=timecode_numbers,
            dimmer_attributes=dimmer_attributes,
            probe_results=probe_results,
        )

        blocked = {
            (track.group_name, cue.bar)
            for track in result.tracks
            for cue in track.cues
            if cue.blocked_reason is not None
        }
        allowed_with_content = {
            (track.group_name, cue.bar)
            for track in result.tracks
            for cue in track.cues
            if cue.blocked_reason is None and cue.commands
        }

        expected_effect_blocked = {
            ("BACK", 3),
            ("BACK", 7),
            ("BACK", 18),
            ("BACK", 22),
            ("SIDE-ALL", 11),
            ("SIDE-ALL", 14),
            ("MOVER-U", 14),
            ("MOVER-D", 14),
        }
        # 2026-10-11 대체(카드 t553, progress.md M1 후속 대체 고지 참조):
        # MOVER-D(group 12)의 Tilt wave(bar 7·22)는 M1 표의 원래 판정과
        # 별개로 t548 라이브 프로브(D1·D3)가 직접 확인했다 —
        # `beat_grid_measured`의 측정된 무빙 허용목록과 일치해 더 이상
        # 막히지 않는다. MOVER-U(group 11)의 Pan 단독(bar 11·18)은 여전히
        # 미측정이라 막힌 채다 — "부분 적용 0건" 원칙 그대로.
        expected_app_movement_blocked = {
            ("MOVER-U", 11),
            ("MOVER-U", 18),
        }
        assert expected_effect_blocked <= blocked
        assert expected_app_movement_blocked <= blocked
        assert ("MOVER-D", 7) not in blocked
        assert ("MOVER-D", 22) not in blocked

        expected_allowed = {
            ("FOH", 7),
            ("WASH-ALL", 7),
            ("WASH-ALL", 14),
            ("MOVER-D", 18),
            ("MOVER-D", 7),
            ("MOVER-D", 22),
            ("BLIND", 17),
            ("BLIND", 18),
        }
        assert expected_allowed <= allowed_with_content

    def test_all_eight_love_attack_tracks_on_one_timecode_exceeds_measured_max(self) -> None:
        # 중요한 발견 — LOVE ATTACK은 콘솔 그룹 트랙 8개(FOH·WASH-ALL·
        # BACK·SIDE-ALL·MOVER-U·MOVER-D·BLIND·STROBE)다. "한 곡 = 타임코드
        # 하나"로 전부 몰면 ①이 구조로 확인한 실제 최대(6)를 넘어 **트랙
        # 레벨**에서 전부 거절된다 — 쪼개거나(둘 이상의 타임코드) M1 ①을
        # 6개 초과로 재확인해야 전부 한 타임코드에 들어간다.
        from server.design.beat_grid import LOVE_ATTACK_TITLE
        from server.design.beat_grid_probes import read_m1_probe_results_from_path

        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        tracks = grid["tracks"]
        assert len(tracks) == 8
        probe_results = read_m1_probe_results_from_path(default_progress_md_path())
        sequence_numbers = {t["group_name"]: 300 + i for i, t in enumerate(tracks)}
        timecode_numbers = {t["group_name"]: 30 for t in tracks}
        dimmer_attributes = {t["group_name"]: ("Dimmer",) for t in tracks}

        result = emit_beat_grid_write_bundle(
            tracks,
            timing=_TIMING,
            sequence_numbers=sequence_numbers,
            timecode_numbers=timecode_numbers,
            dimmer_attributes=dimmer_attributes,
            probe_results=probe_results,
        )
        assert all(track.blocked_reason is not None for track in result.tracks)
        assert all(
            str(MEASURED_MAX_TIMECODE_TRACKS) in track.blocked_reason for track in result.tracks
        )
