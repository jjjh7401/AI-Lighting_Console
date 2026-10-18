"""카드 WT-wave-custom 리드 실기 시험 결함 3 — 스피드 마스터는 곡마다 따로 쓴다.

``Master 3.N At BPM`` 은 쇼 전체가 공유하는 스피드 마스터의 BPM 을 바꾼다. 번호가 하나로 고정돼
있으면 한 곡을 저장할 때 다른 곡의 효과 속도가 같이 바뀐다. 그래서 곡마다 번호를 따로 두고,
배정 없는 곡은 마스터에 묶지 않는다(효과는 ``At Speed`` 로, 웨이브는 만들지 않음).
"""

from __future__ import annotations

from pathlib import Path

from server.design.beat_grid_edit import load_preset_pool_policy, speed_master_of
from server.design.beat_grid_effect_presets import speed_master_bpm_lines

from .test_beat_grid_wave_presets import _session, _tree

_SINE_2B = {"shape": "sine", "beats": 2, "label": "MY SINE 2B", "display_name": "내 사인 2박"}
_TWO_SONGS = {
    "confirmed": True,
    "pools": {},
    "song_speed_masters": {"LOVE ATTACK": 15, "OTHER SONG": 14},
}
_LOVE_ONLY = {"confirmed": True, "pools": {}, "song_speed_masters": {"LOVE ATTACK": 15}}


def _retitle(session, title: str) -> None:
    """저장소의 격자를 다른 곡 제목으로 바꾼다(타임라인과 격자 둘 다)."""
    store = session._timeline_store
    timeline = dict(store.latest)
    timeline["song_title"] = title
    timeline["beat_grid"] = {**timeline["beat_grid"], "song_title": title}
    store.latest = timeline


class TestPerSongMasterLookup:
    def test_each_mapped_song_has_its_own_master(self) -> None:
        assert speed_master_of(_TWO_SONGS, "LOVE ATTACK") == 15
        assert speed_master_of(_TWO_SONGS, "OTHER SONG") == 14

    def test_a_song_with_no_entry_gets_no_master(self) -> None:
        assert speed_master_of(_LOVE_ONLY, "OTHER SONG") is None

    def test_spacing_underscores_and_case_do_not_split_one_song(self) -> None:
        assert speed_master_of(_LOVE_ONLY, "love_attack") == 15
        assert speed_master_of(_LOVE_ONLY, "  LOVE  ATTACK ") == 15

    def test_the_shipped_policy_maps_love_attack_and_no_other_song(self) -> None:
        policy = load_preset_pool_policy()

        assert speed_master_of(policy, "LOVE ATTACK") == 15
        assert speed_master_of(policy, "OTHER SONG") is None

    def test_an_out_of_range_or_bool_entry_is_dropped_not_guessed(self, tmp_path: Path) -> None:
        path = tmp_path / "pools.yaml"
        path.write_text(
            'confirmed: false\npools: {}\nsong_speed_masters:\n  "A": 16\n  "B": true\n  "C": 3\n',
            encoding="utf-8",
        )
        policy = load_preset_pool_policy(path)

        assert speed_master_of(policy, "A") is None
        assert speed_master_of(policy, "B") is None
        assert speed_master_of(policy, "C") == 3


class TestEffectMasterLineFollowsTheSong:
    def test_a_love_attack_effect_grid_gets_its_master_line(self) -> None:
        grid = {"song_title": "LOVE ATTACK", "tracks": [{"cues": [{"effect_preset_no": "2.61"}]}]}

        assert speed_master_bpm_lines(grid, policy=_LOVE_ONLY, bpm=112.35) == (
            "Master 3.15 At BPM 112.35",
        )

    def test_an_unmapped_song_effect_grid_emits_no_master_line(self) -> None:
        grid = {"song_title": "OTHER SONG", "tracks": [{"cues": [{"effect_preset_no": "2.61"}]}]}

        assert speed_master_bpm_lines(grid, policy=_LOVE_ONLY, bpm=128.0) == ()


class TestTheWaveUsesTheSongsOwnMaster:
    def test_another_song_saves_on_its_own_master_not_the_shared_one(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "server.web.session.load_preset_pool_policy", lambda *a, **k: _TWO_SONGS
        )
        session, console, _approval = _session(tmp_path, tree=_tree({}))
        _retitle(session, "OTHER SONG")

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is True
        assert "Master 3.14 At BPM 112.35" in console.executed
        assert not any(line.startswith("Master 3.15") for line in console.executed)

    def test_a_song_with_no_master_is_refused_and_sends_nothing(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "server.web.session.load_preset_pool_policy", lambda *a, **k: _LOVE_ONLY
        )
        session, console, approval = _session(tmp_path, tree=_tree({}))
        _retitle(session, "OTHER SONG")

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is False
        assert "스피드 마스터" in status["reason"]
        assert approval.requests == []
        assert console.executed == []
