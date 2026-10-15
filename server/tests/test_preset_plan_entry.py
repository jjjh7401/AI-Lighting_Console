"""연출 프리셋 계획 — 버튼 진입(beat_grid_apply 의 mode)·계획표·곡별 주석 읽기 (콘솔 무접촉)."""

from __future__ import annotations

import json

import pytest

from server.design.beat_grid import LOVE_ATTACK_TITLE
from server.design.preset_plan import load_preset_annotations, plan_table_markdown
from server.web.messages import ProtocolError, parse_client_message

from .test_preset_plan import _plan


def _apply(**fields) -> dict:
    return parse_client_message(json.dumps({"v": 1, "type": "beat_grid_apply", **fields}))


class TestBeatGridApplyMode:
    def test_without_mode_the_apply_path_is_unchanged(self) -> None:
        assert _apply()["mode"] == "apply"

    def test_preset_plan_mode_rides_on_the_existing_message_type(self) -> None:
        message = _apply(mode="preset_plan")
        assert message["type"] == "beat_grid_apply"
        assert message["mode"] == "preset_plan"

    def test_unknown_mode_is_rejected_as_a_protocol_error(self) -> None:
        with pytest.raises(ProtocolError):
            _apply(mode="console_write_everything")


class TestPlanTableAndSongAnnotations:
    def test_plan_table_lists_presets_and_the_supervisor_marks(self) -> None:
        table = plan_table_markdown(_plan())
        assert "| DIM-100 | 100% | 1.11 | 19 | 저장(이 카드) |" in table
        assert "| LAVENDER |" in table
        assert "**이 카드 밖**" in table
        assert "**감독이 고칠 값**" in table

    def test_a_song_without_an_annotation_file_gets_an_empty_annotation(self) -> None:
        assert load_preset_annotations("Some Other Song") == {}

    def test_the_loaded_song_reads_its_own_annotation_file(self) -> None:
        annotations = load_preset_annotations(LOVE_ATTACK_TITLE)
        assert [entry["console_name"] for entry in annotations["colors"]] == ["LAVENDER"]
