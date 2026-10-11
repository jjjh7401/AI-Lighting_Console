"""SPEC-LDBEAT-001 — 「움직임」 고르기 목록의 서버 어휘 (카드 t584,
REQ-LDBEAT-006(vi)·010·021(b)).

콘솔 접촉 0건. 이 시험이 재는 것:

1. 모양·축·주기 단위는 서버의 닫힌 어휘(``POSITION_FX_EFFECTS``·``AXES_VALUES``·
   ``PERIOD_UNITS``)에서만 온다 — 화면에 상수를 두지 않는다.
2. 목록의 「⚠」는 t579 의 같은 판정 함수(M1 표 ⑨)를 따른다.
3. 두 서빙 경로(첫 로드 = runtime extras, 편집 뒤 재전송 = session refresh)
   모두 어휘를 싣는다. 고른 값은 ``apply_beat_grid_edit`` 한 길로 저장된다.
"""

from __future__ import annotations

from pathlib import Path

from server.design.beat_grid import (
    LOVE_ATTACK_TITLE,
    attach_beat_grid_runtime_extras,
    default_beat_grid,
)
from server.design.beat_grid_edit import AXES_VALUES, PERIOD_UNITS, movement_vocabulary
from server.spatial.position_fx import POSITION_FX_EFFECTS
from server.web.session import SongTimelineStore

from .test_beat_grid_send_t563 import _new_session, _timeline

_LIVE_ITEM9_TEXT = "wave 움직임 없음 · circle·발리후 미확인"


class TestVocabularyIsTheServerClosedSet:
    def test_shapes_axes_units_are_the_closed_sets(self) -> None:
        vocab = movement_vocabulary({})
        assert [shape["name"] for shape in vocab["shapes"]] == list(POSITION_FX_EFFECTS)
        assert set(vocab["axes"]) == set(AXES_VALUES)
        assert set(vocab["period_units"]) == set(PERIOD_UNITS)
        assert "second" not in vocab["period_units"]

    def test_unverified_marks_follow_item9(self) -> None:
        unconfirmed = movement_vocabulary({9: _LIVE_ITEM9_TEXT})
        flagged = {s["name"] for s in unconfirmed["shapes"] if s["unverified"]}
        assert flagged == {"circle", "ballyhoo"}
        assert unconfirmed["phase_spread_unverified"] is True

        passed = movement_vocabulary({9: "통과"})
        assert not any(s["unverified"] for s in passed["shapes"])
        assert passed["phase_spread_unverified"] is False


class TestBothServingPathsCarryTheVocabulary:
    def test_runtime_extras(self, tmp_path: Path) -> None:
        payload = {"beat_grid": default_beat_grid(LOVE_ATTACK_TITLE)}
        refreshed = attach_beat_grid_runtime_extras(
            payload, progress_md_path=tmp_path / "absent.md"
        )
        vocab = refreshed["beat_grid"]["movement_vocabulary"]
        # 표 없음 = 전부 미확인(지어낸 PASS 0건).
        assert {s["name"] for s in vocab["shapes"] if s["unverified"]} == {"circle", "ballyhoo"}

    def test_picked_movement_is_saved_through_the_edit_path_and_resent(
        self, tmp_path: Path
    ) -> None:
        timeline = _timeline()
        timeline["beat_grid"]["probe_results"] = {
            **timeline["beat_grid"]["probe_results"],
            9: _LIVE_ITEM9_TEXT,
        }
        store = SongTimelineStore()
        store.latest = timeline
        sent: list[dict] = []
        session, _console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)
        picked = {
            "shape": "circle",
            "axes": ["Pan", "Tilt"],
            "period_unit": "beat",
            "period_value": 4,
            "phase_spread": None,
        }

        session.beat_grid_edit(1, "BACK", {"app_movement": picked})

        grid = [e for e in sent if e.get("type") == "song_timeline"][-1]["timeline"]["beat_grid"]
        cue = next(c for c in grid["tracks"][0]["cues"] if c["bar"] == 1)
        # 정규화는 axes 를 튜플로 둔다(JSON 을 거치면 목록) — 값으로 비교한다.
        assert {**cue["app_movement"], "axes": list(cue["app_movement"]["axes"])} == picked
        assert grid["unverified_cells"] == [{"group_name": "BACK", "bar": 1, "terms": ["circle"]}]
        assert grid["movement_vocabulary"]["shapes"][2] == {"name": "circle", "unverified": True}

    def test_picking_none_clears_the_movement(self, tmp_path: Path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        sent: list[dict] = []
        session, _console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)
        session.beat_grid_edit(
            1,
            "BACK",
            {
                "app_movement": {
                    "shape": "wave",
                    "axes": ["Tilt"],
                    "period_unit": None,
                    "period_value": None,
                    "phase_spread": None,
                }
            },
        )

        session.beat_grid_edit(1, "BACK", {"app_movement": None})

        grid = [e for e in sent if e.get("type") == "song_timeline"][-1]["timeline"]["beat_grid"]
        cue = next(c for c in grid["tracks"][0]["cues"] if c["bar"] == 1)
        assert cue["app_movement"] is None
