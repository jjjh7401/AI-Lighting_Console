"""SPEC-LDBEAT-001 M2 — 박자 격자 데이터 모델·저장 임베드 (카드 t532).

콘솔 접촉 0건. 이 시험이 재는 것은 네 가지다:

1. LOVE ATTACK 첫 기본값이 배치 규칙서 §2·§4를 그대로 옮겼는지(그리고 그
   값이 REQ-LDBEAT-004(h) 겹침 검증을 통과하는지).
2. 다른 곡은 강제 적용 없이 빈 상태로 떨어지는지(AC-LDBEAT-007).
3. 격자가 기존 timeline 사전의 ``beat_grid`` 키 하나로 심겨, 있으면 보존·
   없으면 기본값이 붙는지(REQ-LDBEAT-006) — 그리고 ``SongTimelineStore``·
   ``TimelineDraftHistory``가 **코드 추가 없이** 그 키를 덮는지(전체-사전
   스냅샷/atomic write 방식이므로).
4. 겹치는 그룹 트랙(예: MOVER-ALL + MOVER-U)이 단일-원인 사유로 거절되는지
   (REQ-LDBEAT-008의 "부분 적용 금지" 관행과 같은 모양).
"""

from __future__ import annotations

import copy

from server.design.beat_grid import (
    DEFAULT_BAR_RANGE,
    LOVE_ATTACK_TITLE,
    attach_beat_grid_default,
    default_beat_grid,
    find_overlapping_group_tracks,
    validate_beat_grid_tracks,
)
from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import (
    AccentDecision,
    ApprovalState,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
)
from server.web.session import SongTimelineStore, _song_timeline_payload
from server.web.timeline_draft import TimelineDraftHistory


class TestDefaultBeatGrid:
    def test_love_attack_gets_the_hand_arranged_first_default(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        assert grid["source"] == "love_attack_default"
        assert grid["note"] is None
        assert grid["bar_range"] == {"start": DEFAULT_BAR_RANGE[0], "end": DEFAULT_BAR_RANGE[1]}
        names = [track["group_name"] for track in grid["tracks"]]
        # 배치 규칙서 §2가 "줄 하나 = 그룹 하나"로 깨끗이 떨어지는 넷 + ACCENT를
        # 그 모양대로 쪼갠 둘 — SCENE은 단일 그룹이 아니라서 뺐다(코드 주석).
        assert names == ["BACK", "SIDE-ALL", "MOVER-U", "MOVER-D", "BLIND", "STROBE"]

    def test_group_numbers_match_the_rules_doc_and_t525_where_evidenced(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        by_name = {t["group_name"]: t for t in grid["tracks"]}

        # 배치 규칙서 §2 "그룹(선택 하나)" 칸에 적힌 숫자 그대로.
        assert by_name["BACK"]["group_no"] == 4
        assert by_name["BACK"]["group_no_confirmed"] is True
        assert by_name["SIDE-ALL"]["group_no"] == 7
        assert by_name["MOVER-U"]["group_no"] == 11
        assert by_name["MOVER-D"]["group_no"] == 12
        # t525 §② 실측(probe_groups.py) — 그룹 14.
        assert by_name["BLIND"]["group_no"] == 14
        assert by_name["BLIND"]["group_no_confirmed"] is True
        # STROBE는 이 plan-phase 증거 어디에도 번호가 없다 — 지어내지 않는다.
        assert by_name["STROBE"]["group_no"] is None
        assert by_name["STROBE"]["group_no_confirmed"] is False

    def test_layer_role_labels_come_from_the_shared_rig_resolver(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        by_name = {t["group_name"]: t["layer_role"] for t in grid["tracks"]}

        assert by_name["BACK"] == "back"
        assert by_name["SIDE-ALL"] == "side"
        assert by_name["MOVER-U"] == "mover"
        assert by_name["MOVER-D"] == "mover"
        assert by_name["BLIND"] == "effect"
        assert by_name["STROBE"] == "effect"

    def test_the_0_to_25_bar_range_is_the_exact_grid_from_section_4(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        by_name = {t["group_name"]: t["cues"] for t in grid["tracks"]}

        back_cues = {cue["bar"]: cue["label"] for cue in by_name["BACK"]}
        assert back_cues[0] == "앞박 1회"
        assert back_cues[18] == "킥 1·2·4박 100%"

        side_cues = {cue["bar"]: cue["label"] for cue in by_name["SIDE-ALL"]}
        assert side_cues[11] == "SIDE-L/R 2·4박 번갈이"
        assert side_cues[0] == "—"

        mover_u_cues = {cue["bar"]: cue["label"] for cue in by_name["MOVER-U"]}
        assert mover_u_cues[14] == "가속 스윕 4박→2박→1박→반 박"

        # ACCENT 열의 0~25마디 실제 발화는 BLIND 둘뿐 — 63·67마디(스트로브 포함)는
        # §4 표시 범위 밖이다. 빈 STROBE 트랙은 거짓이 아니라 이 구간의 정확한 모습.
        assert [c["bar"] for c in by_name["BLIND"]] == [17, 18]
        assert by_name["STROBE"] == []

    def test_a_different_song_gets_no_forced_default(self) -> None:
        grid = default_beat_grid("Sugar")

        assert grid["source"] == "empty"
        assert grid["tracks"] == []
        assert grid["note"] == "이 곡의 기본값 없음"

    def test_an_empty_song_title_also_falls_back_to_empty_not_love_attack(self) -> None:
        grid = default_beat_grid("")

        assert grid["tracks"] == []
        assert grid["source"] == "empty"

    def test_title_match_is_whitespace_and_case_insensitive(self) -> None:
        grid = default_beat_grid("  love attack  ")

        assert grid["source"] == "love_attack_default"
        assert grid["tracks"]


class TestOverlapValidation:
    def test_love_attack_default_tracks_pass_validation_cleanly(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        assert validate_beat_grid_tracks(grid["tracks"]) is None

    def test_mover_all_and_mover_u_together_are_rejected(self) -> None:
        tracks = [{"group_name": "MOVER-ALL"}, {"group_name": "MOVER-U"}]

        conflict = find_overlapping_group_tracks([t["group_name"] for t in tracks])
        reason = validate_beat_grid_tracks(tracks)

        assert conflict == ("MOVER-ALL", "MOVER-U")
        assert reason is not None
        assert "MOVER-ALL" in reason and "MOVER-U" in reason

    def test_the_same_group_twice_is_rejected(self) -> None:
        tracks = [{"group_name": "BACK"}, {"group_name": "back"}]

        reason = validate_beat_grid_tracks(tracks)

        assert reason is not None

    def test_non_overlapping_prefix_families_pass(self) -> None:
        # SIDE-ALL과 MOVER-U는 접두가 다르다 — 겹치지 않는다.
        tracks = [{"group_name": "SIDE-ALL"}, {"group_name": "MOVER-U"}]

        assert validate_beat_grid_tracks(tracks) is None

    def test_a_hyphenless_name_is_never_treated_as_a_prefix_conflict(self) -> None:
        tracks = [{"group_name": "BLIND"}, {"group_name": "STROBE"}]

        assert validate_beat_grid_tracks(tracks) is None


class TestAttachBeatGridDefault:
    def test_absent_key_gets_the_default_attached(self) -> None:
        timeline = {"song_title": LOVE_ATTACK_TITLE, "sections": []}

        merged = attach_beat_grid_default(timeline)

        assert "beat_grid" not in timeline  # 원본은 건드리지 않는다
        assert merged["beat_grid"]["source"] == "love_attack_default"
        assert merged["sections"] == []  # ADDITIVE — 다른 칸은 그대로

    def test_a_present_grid_is_preserved_verbatim_not_reset(self) -> None:
        custom_grid = {
            "song_title": LOVE_ATTACK_TITLE,
            "bar_range": {"start": 0, "end": 25},
            "tracks": [{"group_no": 99, "group_name": "CUSTOM", "layer_role": None, "cues": []}],
            "source": "custom",
            "note": None,
        }
        timeline = {"song_title": LOVE_ATTACK_TITLE, "beat_grid": custom_grid}

        merged = attach_beat_grid_default(timeline)

        assert merged["beat_grid"] == custom_grid

    def test_cross_song_edits_do_not_leak_ac_008(self) -> None:
        love_attack = attach_beat_grid_default({"song_title": LOVE_ATTACK_TITLE})
        other_song = attach_beat_grid_default({"song_title": "Sugar"})

        # 한 곡의 격자를 고쳐도 — 독립 사전이므로 — 다른 곡에 영향이 없다.
        love_attack["beat_grid"]["tracks"][0]["cues"].append({"bar": 99, "label": "편집"})

        assert other_song["beat_grid"]["tracks"] == []
        assert len(love_attack["beat_grid"]["tracks"][0]["cues"]) == 8


class TestStorageRoundTrip:
    """REQ-LDBEAT-006 M2 결정 — 격자는 `timeline["beat_grid"]`로 심겨 기존
    저장소 둘을 코드 추가 없이 재사용한다. 이 시험은 그 재사용이 실제로
    되는지 재지, 그렇다고 가정하지 않는다."""

    def test_song_timeline_store_persists_beat_grid_across_restart(self, tmp_path) -> None:
        path = tmp_path / "song-timeline.json"
        store = SongTimelineStore(path)
        timeline = attach_beat_grid_default({"song_title": LOVE_ATTACK_TITLE, "sections": []})

        store.latest = timeline  # 기존 setter 그대로 — atomic JSON write

        reborn = SongTimelineStore(path)  # 서버 재시작 흉내
        assert reborn.latest["beat_grid"]["source"] == "love_attack_default"
        assert reborn.latest["beat_grid"]["tracks"][0]["group_name"] == "BACK"

    def test_timeline_draft_history_undo_restores_the_grid_with_no_new_code(self) -> None:
        history = TimelineDraftHistory()
        before = attach_beat_grid_default({"song_title": LOVE_ATTACK_TITLE})
        after = copy.deepcopy(before)
        after["beat_grid"]["tracks"][0]["cues"][0]["label"] = "편집됨"

        history.record(before)  # 편집 직전 상태를 쌓는다(session.py:8505와 같은 호출)
        restored = history.undo(after)

        assert restored is not None
        assert restored["beat_grid"]["tracks"][0]["cues"][0]["label"] == "앞박 1회"
        # 직전 상태는 깊은 사본이다 — after를 계속 고쳐도 되돌린 사본은 안 바뀐다.
        after["beat_grid"]["tracks"][0]["cues"][0]["label"] = "또 편집"
        assert restored["beat_grid"]["tracks"][0]["cues"][0]["label"] == "앞박 1회"


# -- `_song_timeline_payload` 실제 배선 — session.py 변경이 실제로 호출되는지 ----


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 21)
    ]
    return build_rig_profile(patch=patch, groups={}, coords=[], declared_layers={"back": [1, 2]})


def _section() -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(
            index=1, label="INTRO", start_ms=0, source="song_design_interview"
        ),
        d=DLevelDecision(level=2, source="section_mood"),
        palette=PaletteDecision(colors=("hot_pink",), source="director"),
        position=PositionDecision(preset="Center", source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=(), density=0),
        accent=AccentDecision(),
        cue_number=10,
    )


def _plan(song_title: str) -> UnifiedSongLightingPlan:
    return UnifiedSongLightingPlan(
        song_title=song_title,
        sequence_name=f"{song_title} Seq",
        sections=(_section(),),
        timing=TimingPlan.timecode(77),
        music_profile=MusicProfile(bpm=120.0, meter="4/4", key_mode="D♭ major"),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="LD"),
    )


class TestSongTimelinePayloadWiring:
    def test_love_attack_payload_carries_the_hand_arranged_default(self) -> None:
        plan = _plan(LOVE_ATTACK_TITLE)
        payload = _song_timeline_payload(
            plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
        )

        assert payload["beat_grid"]["source"] == "love_attack_default"
        assert len(payload["beat_grid"]["tracks"]) == 6

    def test_another_song_payload_carries_the_empty_no_default_marker(self) -> None:
        plan = _plan("Sugar")
        payload = _song_timeline_payload(
            plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
        )

        assert payload["beat_grid"]["source"] == "empty"
        assert payload["beat_grid"]["tracks"] == []
