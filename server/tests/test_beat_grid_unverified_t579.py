"""SPEC-LDBEAT-001 M5 — 「⚠ 실기 미확인」 판정 출처 (카드 t579, REQ-LDBEAT-010).

콘솔 접촉 0건. 이 시험이 재는 것:

1. 판정은 M1 상태표(``probe_results`` ⑨)와 실측 무빙 기록에서만 온다 —
   ⑨가 「통과」로 시작하면 배지가 사라지고, 아니면(지금 실제 문면 포함) 남는다.
2. 실측 기록이 연 (그룹·모양·축)은 미확인이 아니다(송신 게이트와 같은 판정).
3. 곡 기본값(LOVE ATTACK 기본 격자)에는 미확인 칸이 0개다 — REQ-LDBEAT-010
   「M1 PASS 전에는 곡의 기본값으로 제공하지 않는다」. 대조군: 같은 격자에
   circle 칸을 넣으면 잡힌다(공허한 0이 아님).
4. 편집 경고와 세션 재전송(``unverified_cells``)이 같은 판정을 따른다.
"""

from __future__ import annotations

import copy
from pathlib import Path

from server.design.beat_grid import (
    LOVE_ATTACK_TITLE,
    attach_beat_grid_runtime_extras,
    default_beat_grid,
)
from server.design.beat_grid_edit import apply_beat_grid_edit
from server.design.beat_grid_probes import default_progress_md_path
from server.design.beat_grid_unverified import (
    PHASE_SPREAD_TERM,
    unverified_beat_grid_cells,
    unverified_movement_terms,
)
from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import _new_session, _timeline

#: 지금 progress.md M1 표 ⑨ 판정 칸의 실제 문면(2026-10-11 main 63de8d95) —
#: 「통과」로 시작하지 않으므로 미확인이다.
_LIVE_ITEM9_TEXT = "wave 움직임 없음 · circle·발리후 미확인"


def _movement(shape="circle", axes=("Pan", "Tilt"), phase_spread=None):
    return {
        "shape": shape,
        "axes": list(axes),
        "period_unit": "beat",
        "period_value": 4,
        "phase_spread": phase_spread,
    }


class TestTermsComeFromTheM1Table:
    def test_circle_is_unverified_while_item9_is_not_a_pass(self) -> None:
        assert unverified_movement_terms(_movement(), {9: _LIVE_ITEM9_TEXT}) == ("circle",)

    def test_ballyhoo_is_unverified_with_an_empty_table(self) -> None:
        assert unverified_movement_terms(_movement("ballyhoo"), {}) == ("ballyhoo",)

    def test_item9_pass_clears_the_badge(self) -> None:
        assert unverified_movement_terms(_movement(), {9: "통과"}) == ()
        assert unverified_movement_terms(_movement(), {9: "통과(구조)"}) == ()

    def test_json_string_keys_are_read_too(self) -> None:
        assert unverified_movement_terms(_movement(), {"9": "통과"}) == ()

    def test_other_items_passing_do_not_clear_item9_vocabulary(self) -> None:
        table = {item: "통과" for item in range(1, 9)}
        assert unverified_movement_terms(_movement(), table) == ("circle",)

    def test_wave_without_phase_spread_is_not_section6_vocabulary(self) -> None:
        assert unverified_movement_terms(_movement("wave", ("Pan",)), {}) == ()

    def test_no_movement_no_badge(self) -> None:
        assert unverified_movement_terms(None, {}) == ()


class TestMeasuredRecordOpensTheSameCellsAsTheSendGate:
    def test_measured_wave_tilt_with_phase_spread_is_not_unverified(self) -> None:
        # measured_movements.yaml: group 12 · wave · [Tilt] · any (t548 D1, 위상 펼침 포함).
        movement = _movement("wave", ("Tilt",), phase_spread=True)
        assert unverified_movement_terms(movement, {9: _LIVE_ITEM9_TEXT}, group_no=12) == ()

    def test_same_movement_on_an_unmeasured_group_is_unverified(self) -> None:
        movement = _movement("wave", ("Tilt",), phase_spread=True)
        assert unverified_movement_terms(movement, {}, group_no=99) == (PHASE_SPREAD_TERM,)

    def test_unknown_group_never_opens(self) -> None:
        movement = _movement("wave", ("Tilt",), phase_spread=True)
        assert unverified_movement_terms(movement, {}, group_no=None) == (PHASE_SPREAD_TERM,)

    def test_tilted_base_only_record_does_not_open(self) -> None:
        # group 11 · wave · [Pan] 은 requires_tilted_base_unverifiable — 열지 않는다.
        movement = _movement("wave", ("Pan",), phase_spread=True)
        assert unverified_movement_terms(movement, {}, group_no=11) == (PHASE_SPREAD_TERM,)

    def test_circle_on_a_measured_group_stays_unverified(self) -> None:
        assert unverified_movement_terms(_movement("circle", ("Tilt",)), {}, group_no=12) == (
            "circle",
        )


class TestSongDefaultCarriesNoUnverifiedCell:
    def test_love_attack_default_has_zero_unverified_cells_against_the_live_table(self) -> None:
        payload = {"beat_grid": default_beat_grid(LOVE_ATTACK_TITLE)}
        refreshed = attach_beat_grid_runtime_extras(
            payload, progress_md_path=default_progress_md_path()
        )
        assert refreshed["beat_grid"]["unverified_cells"] == []

    def test_love_attack_default_has_zero_unverified_cells_even_with_nothing_confirmed(
        self,
    ) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        grid["probe_results"] = {}
        assert unverified_beat_grid_cells(grid) == []

    def test_control_a_circle_cell_in_the_default_is_caught(self) -> None:
        grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
        grid["probe_results"] = {}
        mover = next(t for t in grid["tracks"] if t["group_name"] == "MOVER-U")
        mover["cues"][0]["app_movement"] = _movement("circle")
        cells = unverified_beat_grid_cells(grid)
        assert cells == [
            {"group_name": "MOVER-U", "bar": mover["cues"][0]["bar"], "terms": ["circle"]}
        ]


class TestRuntimeExtrasReadTheTableItJustRead:
    def _grid_with_circle(self) -> dict:
        grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
        mover = next(t for t in grid["tracks"] if t["group_name"] == "MOVER-U")
        mover["cues"][0]["app_movement"] = _movement("circle")
        return grid

    def _progress(self, tmp_path: Path, item9: str) -> Path:
        path = tmp_path / "progress.md"
        path.write_text(
            "| 항목 | 판정 | 무엇을 봤나 | 근거 |\n"
            "|---|---|---|---|\n"
            f"| ⑨ circle·발리후·wave | **{item9}** | x | y |\n",
            encoding="utf-8",
        )
        return path

    def test_item9_unconfirmed_lists_the_cell(self, tmp_path: Path) -> None:
        payload = {"beat_grid": self._grid_with_circle()}
        refreshed = attach_beat_grid_runtime_extras(
            payload, progress_md_path=self._progress(tmp_path, _LIVE_ITEM9_TEXT)
        )
        assert [c["terms"] for c in refreshed["beat_grid"]["unverified_cells"]] == [["circle"]]

    def test_item9_pass_lists_nothing(self, tmp_path: Path) -> None:
        payload = {"beat_grid": self._grid_with_circle()}
        refreshed = attach_beat_grid_runtime_extras(
            payload, progress_md_path=self._progress(tmp_path, "통과")
        )
        assert refreshed["beat_grid"]["unverified_cells"] == []


class TestEditWarningFollowsTheSameJudgment:
    def _edit(self, grid, target, bar, movement):
        return apply_beat_grid_edit(
            grid, bar=bar, target=target, changes={"app_movement": movement}
        )

    def test_circle_edit_warns_while_unconfirmed(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        _updated, report = self._edit(grid, "MOVER-U", 11, _movement("circle"))
        assert any(line.startswith("⚠ 실기 미확인 — MOVER-U 11마디 circle") for line in report)

    def test_circle_edit_is_silent_once_item9_passes(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        grid["probe_results"] = {**grid["probe_results"], 9: "통과"}
        _updated, report = self._edit(grid, "MOVER-U", 11, _movement("circle"))
        assert not any("실기 미확인" in line for line in report)

    def test_measured_phase_spread_edit_is_silent(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        _updated, report = self._edit(
            grid, "MOVER-D", 7, _movement("wave", ("Tilt",), phase_spread=True)
        )
        assert not any("실기 미확인" in line for line in report)


class TestSessionResendsUnverifiedCellsAfterAnEdit:
    def test_edit_to_circle_appears_in_the_resent_grid(self, tmp_path: Path) -> None:
        timeline = _timeline()
        timeline["beat_grid"]["probe_results"] = {
            **timeline["beat_grid"]["probe_results"],
            9: _LIVE_ITEM9_TEXT,
        }
        store = SongTimelineStore()
        store.latest = timeline
        sent: list[dict] = []
        session, _console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)

        session.beat_grid_edit(1, "BACK", {"app_movement": _movement("circle")})

        timelines = [e for e in sent if e.get("type") == "song_timeline"]
        assert timelines[-1]["timeline"]["beat_grid"]["unverified_cells"] == [
            {"group_name": "BACK", "bar": 1, "terms": ["circle"]}
        ]
