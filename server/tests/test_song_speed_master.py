"""리드 실기 시험 결함 3(2차) — 스피드 마스터는 곡마다 앱이 기록하고 자동으로 고른다.

``Master 3.N At BPM`` 은 쇼 전체가 공유하는 스피드 마스터의 BPM 을 바꾼다. 곡이 같은 번호를
쓰면 한 곡의 BPM 줄이 다른 곡의 효과·웨이브 속도를 덮는다. 그래서 곡마다 번호를 하나씩
기록하고(speed_masters.json), 기록이 없는 곡은 빈 번호 가운데 가장 큰 번호를 그 곡에 적는다.

conftest 가 기록 폴더를 테스트마다 임시 폴더로 돌린다(실제 앱 저장소를 건드리지 않는다).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from server.design.beat_grid_edit import (
    _PRESET_POOLS_PATH,
    load_preset_pool_policy,
    speed_master_of,
)
from server.design.beat_grid_effect_presets import speed_master_bpm_lines
from server.design.speed_master_registry import (
    REGISTRY_FILE_NAME,
    assign_speed_master,
    with_song_speed_master,
)

from .test_beat_grid_wave_presets import _session, _tree

_SINE_2B = {"shape": "sine", "beats": 2, "label": "MY SINE 2B", "display_name": "내 사인 2박"}


def _registry(tmp_path: Path) -> Path:
    return tmp_path / REGISTRY_FILE_NAME


def _recorded(path: Path) -> dict[str, int]:
    """기록된 곡 제목 → 번호(검사용으로만 읽는다)."""
    songs = json.loads(path.read_text(encoding="utf-8"))["songs"]
    return {song["title"]: song["master"] for song in songs}


def _full_record(path: Path) -> None:
    """번호 1~15 가 모두 다른 곡에 기록된 상태."""
    songs = [{"title": f"SONG {n}", "master": n} for n in range(1, 16)]
    path.write_text(json.dumps({"version": 1, "songs": songs}), encoding="utf-8")


def _retitle(session, title: str) -> None:
    """저장소의 격자를 다른 곡 제목으로 바꾼다(타임라인과 격자 둘 다)."""
    store = session._timeline_store
    timeline = dict(store.latest)
    timeline["song_title"] = title
    timeline["beat_grid"] = {**timeline["beat_grid"], "song_title": title}
    store.latest = timeline


class TestAutomaticAssignment:
    def test_the_first_song_takes_the_highest_empty_master(self, tmp_path: Path) -> None:
        assert assign_speed_master(_registry(tmp_path), "LOVE ATTACK") == 15
        assert _recorded(_registry(tmp_path)) == {"LOVE ATTACK": 15}

    def test_a_second_song_takes_the_next_empty_master_not_the_same_one(
        self, tmp_path: Path
    ) -> None:
        assert assign_speed_master(_registry(tmp_path), "LOVE ATTACK") == 15
        assert assign_speed_master(_registry(tmp_path), "OTHER SONG") == 14
        assert _recorded(_registry(tmp_path)) == {"LOVE ATTACK": 15, "OTHER SONG": 14}

    def test_a_song_keeps_its_recorded_number_and_is_not_recorded_twice(
        self, tmp_path: Path
    ) -> None:
        assign_speed_master(_registry(tmp_path), "LOVE ATTACK")
        assign_speed_master(_registry(tmp_path), "OTHER SONG")

        assert assign_speed_master(_registry(tmp_path), "LOVE ATTACK") == 15
        assert len(_recorded(_registry(tmp_path))) == 2

    def test_spacing_underscores_and_case_are_one_song(self, tmp_path: Path) -> None:
        assert assign_speed_master(_registry(tmp_path), "LOVE ATTACK") == 15
        assert assign_speed_master(_registry(tmp_path), "love_attack") == 15

    def test_when_all_fifteen_numbers_are_recorded_a_new_song_gets_none(
        self, tmp_path: Path
    ) -> None:
        path = _registry(tmp_path)
        _full_record(path)
        before = path.read_text(encoding="utf-8")

        assert assign_speed_master(path, "NEW SONG") is None
        assert path.read_text(encoding="utf-8") == before

    def test_an_unreadable_record_refuses_instead_of_guessing(self, tmp_path: Path) -> None:
        path = _registry(tmp_path)
        path.write_text("{ not json", encoding="utf-8")

        assert assign_speed_master(path, "LOVE ATTACK") is None
        assert path.read_text(encoding="utf-8") == "{ not json"

    def test_a_recorded_number_outside_1_to_15_refuses(self, tmp_path: Path) -> None:
        path = _registry(tmp_path)
        path.write_text(
            json.dumps({"version": 1, "songs": [{"title": "A", "master": 16}]}), encoding="utf-8"
        )

        assert assign_speed_master(path, "B") is None


class TestTheConfigNamesNoSongAndNoMaster:
    def test_the_shipped_policy_has_no_master_and_the_file_has_no_master_key(self) -> None:
        policy = load_preset_pool_policy()
        document = yaml.safe_load(_PRESET_POOLS_PATH.read_text(encoding="utf-8"))

        assert "speed_master" not in policy
        assert "speed_master" not in document
        assert "song_speed_masters" not in document


class TestPolicyCarriesTheSongsOwnMaster:
    def test_only_a_valid_resolved_number_is_read(self) -> None:
        assert speed_master_of({"speed_master": 14}) == 14
        for bad in (16, 0, "15", True, None):
            assert speed_master_of({"speed_master": bad}) is None, bad
        assert speed_master_of({}) is None

    def test_with_song_speed_master_resolves_the_songs_own_number(self, tmp_path: Path) -> None:
        assign_speed_master(_registry(tmp_path), "LOVE ATTACK")

        policy = with_song_speed_master(
            load_preset_pool_policy(), "OTHER SONG", registry_path=_registry(tmp_path)
        )

        assert speed_master_of(policy) == 14
        assert _recorded(_registry(tmp_path))["OTHER SONG"] == 14

    def test_a_song_that_never_asks_for_a_master_records_nothing(self, tmp_path: Path) -> None:
        with_song_speed_master(
            load_preset_pool_policy(), "OTHER SONG", registry_path=_registry(tmp_path)
        )

        assert not _registry(tmp_path).exists()

    def test_the_song_policy_carries_only_strings_and_serializes(self, tmp_path: Path) -> None:
        policy = with_song_speed_master(
            load_preset_pool_policy(), "OTHER SONG", registry_path=_registry(tmp_path)
        )

        assert json.loads(json.dumps(policy))["speed_master_song"] == "OTHER SONG"


class TestEffectMasterLineFollowsTheSong:
    def test_a_grid_with_no_effect_cells_records_no_master(self, tmp_path: Path) -> None:
        policy = with_song_speed_master(
            load_preset_pool_policy(), "OTHER SONG", registry_path=_registry(tmp_path)
        )
        grid = {"song_title": "OTHER SONG", "tracks": [{"cues": [{"effect_preset_no": None}]}]}

        assert speed_master_bpm_lines(grid, policy=policy, bpm=128.0) == ()
        assert not _registry(tmp_path).exists()

    def test_a_second_song_effect_grid_binds_its_own_master_line(self, tmp_path: Path) -> None:
        assign_speed_master(_registry(tmp_path), "LOVE ATTACK")
        policy = with_song_speed_master(
            load_preset_pool_policy(), "OTHER SONG", registry_path=_registry(tmp_path)
        )
        grid = {"song_title": "OTHER SONG", "tracks": [{"cues": [{"effect_preset_no": "2.61"}]}]}

        assert speed_master_bpm_lines(grid, policy=policy, bpm=128.0) == ("Master 3.14 At BPM 128",)


class TestTheWaveOfEachSong:
    def test_a_new_song_saves_on_its_own_recorded_master_never_on_the_shared_one(
        self, tmp_path: Path
    ) -> None:
        assign_speed_master(_registry(tmp_path), "LOVE ATTACK")
        session, console, _approval = _session(tmp_path, tree=_tree({}))
        _retitle(session, "OTHER SONG")

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is True
        assert "Master 3.14 At BPM 112.35" in console.executed
        assert not any(line.startswith("Master 3.15") for line in console.executed)
        assert _recorded(_registry(tmp_path))["OTHER SONG"] == 14

    def test_the_first_song_on_an_empty_record_saves_on_fifteen(self, tmp_path: Path) -> None:
        session, console, _approval = _session(tmp_path, tree=_tree({}))

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is True
        assert "Master 3.15 At BPM 112.35" in console.executed
        assert _recorded(_registry(tmp_path)) == {"LOVE ATTACK": 15}

    def test_a_song_with_no_empty_master_is_refused_and_sends_nothing(self, tmp_path: Path) -> None:
        _full_record(_registry(tmp_path))
        session, console, approval = _session(tmp_path, tree=_tree({}))
        _retitle(session, "OTHER SONG")

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is False
        assert "스피드 마스터" in status["reason"]
        assert approval.requests == []
        assert console.executed == []
