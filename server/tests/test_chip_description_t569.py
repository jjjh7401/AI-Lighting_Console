"""카드 t569 — 프리셋 칩 설명의 출처(REQ-LDBEAT-023(c), 리드 결정 B).

① 앱이 만든 프리셋이면 앱이 저장한 설명(곡별 격자의 ``preset_descriptions``)
② 아니면 콘솔에서 읽은 쇼 프리셋 — 설명은 비우고 출처만 ``"show"``
   (칩 위 글자가 이미 콘솔 이름이라 툴팁에 다시 쓰지 않는다)
③ 둘 다 아니면 출처도 없다.

콘솔 ``NOTE``는 읽지 않는다(t569 실측: 칩 서랍 34칸 모두 빈 값).
"""

from __future__ import annotations

from server.design.beat_grid_presets import (
    build_preset_drawer,
    record_app_preset_description,
)

_POOLS = {
    "Dimmer": (1, {1: "LA Full"}),
    "Position": (2, {41: "Center"}),
    "Color": (4, {21: "LA Pink"}),
}
_POLICY = {"confirmed": True, "pools": {}}


def _entry(sections, preset_no: str) -> dict:
    for section in sections:
        for entry in section["entries"]:
            if entry["preset_no"] == preset_no:
                return entry
    raise AssertionError(preset_no)


class TestChipDescriptionSource:
    def test_app_saved_description_is_used_for_that_preset(self) -> None:
        grid = record_app_preset_description({"tracks": []}, "4.21", "차가운 흰")
        sections = build_preset_drawer(grid, pools=_POOLS, policy=_POLICY)
        entry = _entry(sections, "4.21")
        assert entry["description"] == "차가운 흰"
        assert entry["description_source"] == "app"

    def test_show_preset_without_app_description_is_marked_show(self) -> None:
        grid = record_app_preset_description({"tracks": []}, "4.21", "차가운 흰")
        sections = build_preset_drawer(grid, pools=_POOLS, policy=_POLICY)
        entry = _entry(sections, "2.41")
        assert entry["description"] is None
        assert entry["description_source"] == "show"

    def test_blank_app_description_falls_back_to_show(self) -> None:
        grid = {"tracks": [], "preset_descriptions": {"1.1": "   "}}
        entry = _entry(build_preset_drawer(grid, pools=_POOLS, policy=_POLICY), "1.1")
        assert entry["description"] is None
        assert entry["description_source"] == "show"


class TestRecordAppPresetDescription:
    def test_returns_a_copy_and_keeps_other_descriptions(self) -> None:
        original = {"tracks": [], "preset_descriptions": {"2.61": "틸트 웨이브"}}
        updated = record_app_preset_description(original, "4.41", "라벤더")
        assert updated["preset_descriptions"] == {"2.61": "틸트 웨이브", "4.41": "라벤더"}
        assert original["preset_descriptions"] == {"2.61": "틸트 웨이브"}

    def test_blank_description_is_refused(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            record_app_preset_description({"tracks": []}, "4.41", "  ")
