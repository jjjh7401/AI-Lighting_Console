"""카드 t603 — 「＋ 새 프리셋 만들기」 창의 효과 종류: 효과 틀 + 주기(박/마디) + 영문 이름.

t593 은 반영 때 효과 프리셋을 만드는 서버 길(`preset_fx_recipes{"p.s": {fx_id,
period_unit, period_value}}`)만 있고 그 레시피를 채우는 화면이 없었다 — 창으로 효과
번호를 만들면 반영에서 「효과 프리셋 레시피(템플릿·주기)가 없음」으로 보류됐다.

이 카드: 창이 효과 틀(출하 fx 라이브러리 목록)·주기·이름을 받아 같은 저장 자리에
남긴다. 효과 틀 목록은 격자 이벤트에 실어 화면으로 내린다(콘솔 판독 0 — 출하 파일).
t599 위치 좌표와 같이 효과 종류에는 레시피가 **필수**다. 번호대·디머 효과 보류
규칙은 t593 그대로. 콘솔 쓰기 0(가짜 콘솔).
"""

from __future__ import annotations

import json

import pytest

from server.design.beat_grid_effect_presets import (
    EFFECT_TEMPLATE_KIND_MISMATCH,
    EFFECT_TEMPLATE_UNKNOWN,
    effect_preset_recipe,
    effect_template_catalog,
)
from server.design.beat_grid_presets import app_preset_label
from server.web.messages import ProtocolError, parse_client_message
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import (
    PROTOCOL_VERSION,
    _cue_of,
    _grid_with_effect_cell,
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline,
    _timeline_for_apply,
)

_REJECTED = "박자 격자 수정 거절"
_CREATED = "박자 격자 새 프리셋"
_AIM = {"x": 0, "y": 0, "z": 0}
_FX = {"fx_id": "sweep-soft-wide", "period_unit": "beat", "period_value": 2}


def _session(tmp_path, *, kind: str = "position", sent=None, for_apply: bool = False):
    store = SongTimelineStore()
    grid = _grid_with_effect_cell(kind)
    store.latest = _timeline_for_apply(beat_grid=grid) if for_apply else _timeline(beat_grid=grid)
    tree = _state_tree(
        **{
            "DataPool/PresetPools": _pool_list_payload({"Position": 2, "Color": 4, "All": 22}),
            "DataPool/PresetPools/2": _pool_children_payload({1: "P1"}),
            "DataPool/PresetPools/4": _pool_children_payload({1: "C1"}),
            "DataPool/PresetPools/22": _pool_children_payload({5: "A5"}),
        }
    )
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=tree, sent=sent
    )
    return session, store, console, approval


def _create(session, *, fx=_FX, label="LA Sweep 2"):
    return session.beat_grid_new_preset(1, "BACK", "effect", label, "부드러운 좌우 2박", fx=fx)


class TestDialogStoresTheRecipe:
    def test_recipe_label_and_number_are_stored(self, tmp_path) -> None:
        session, store, console, _approval = _session(tmp_path)
        event = _create(session)
        assert event["summary"] == _CREATED, event
        grid = store.latest["beat_grid"]
        number = _cue_of(grid, "BACK", 1)["effect_preset_no"]
        assert number == "2.61"
        assert effect_preset_recipe(grid, number) == _FX
        assert app_preset_label(grid, number) == "LA Sweep 2"
        assert console.executed == []

    def test_bar_unit_is_kept(self, tmp_path) -> None:
        session, store, _console, _approval = _session(tmp_path)
        fx = {"fx_id": "sweep-soft-wide", "period_unit": "bar", "period_value": 1}
        assert _create(session, fx=fx)["summary"] == _CREATED
        grid = store.latest["beat_grid"]
        assert effect_preset_recipe(grid, _cue_of(grid, "BACK", 1)["effect_preset_no"]) == fx


class TestDialogRefusals:
    def test_effect_without_recipe_is_rejected(self, tmp_path) -> None:
        session, store, _console, _approval = _session(tmp_path)
        event = session.beat_grid_new_preset(1, "BACK", "effect", "LA X", "설명")
        assert event["summary"] == _REJECTED
        assert "효과 틀" in event["text"]
        assert _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"] is None

    def test_unknown_template_is_rejected_before_a_number_is_assigned(self, tmp_path) -> None:
        session, store, _console, _approval = _session(tmp_path)
        event = _create(session, fx={**_FX, "fx_id": "no-such-fx"})
        assert event["summary"] == _REJECTED
        assert EFFECT_TEMPLATE_UNKNOWN in event["text"]
        assert _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"] is None

    def test_template_kind_mismatch_is_rejected(self, tmp_path) -> None:
        # 위치 효과 칸에 색 템플릿.
        session, store, _console, _approval = _session(tmp_path, kind="position")
        event = _create(session, fx={**_FX, "fx_id": "chase-warm-cool"})
        assert event["summary"] == _REJECTED
        assert EFFECT_TEMPLATE_KIND_MISMATCH in event["text"]
        assert _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"] is None

    def test_mixed_band_takes_any_template(self, tmp_path) -> None:
        session, store, _console, _approval = _session(tmp_path, kind="mixed")
        assert _create(session, fx={**_FX, "fx_id": "chase-warm-cool"})["summary"] == _CREATED
        number = _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"]
        assert number.startswith("22.")

    @pytest.mark.parametrize("field", ["dimmer_effect", "position", "color", "dimmer_preset"])
    def test_recipe_on_another_field_is_rejected(self, tmp_path, field) -> None:
        session, _store, _console, _approval = _session(tmp_path)
        event = session.beat_grid_new_preset(
            1, "BACK", field, "LA X", "설명", aim=_AIM if field == "position" else None, fx=_FX
        )
        assert event["summary"] == _REJECTED
        assert "효과 틀" in event["text"]


class TestApplyUsesTheDialogRecipe:
    def test_number_made_in_the_dialog_is_created_on_apply(self, tmp_path) -> None:
        """창 → 반영 왕복: 창이 남긴 레시피가 t593 만들기 줄로 나간다."""
        session, store, _console, approval = _session(tmp_path, for_apply=True)
        assert _create(session)["summary"] == _CREATED
        number = _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"]
        status = session.beat_grid_apply()
        assert status["ok"] is True, status
        card = [item.command for r in approval.requests for item in r.items]
        assert f"Store Preset {number} 'LA Sweep 2' /Universal" in card


class TestCatalogReachesTheGrid:
    def test_catalog_lists_templates_with_their_kinds(self) -> None:
        catalog = {entry["fx_id"]: entry for entry in effect_template_catalog()}
        assert catalog["sweep-soft-wide"]["kinds"] == ["position", "mixed"]
        assert catalog["chase-warm-cool"]["kinds"] == ["color", "mixed"]
        assert catalog["pulse-beat"]["kinds"] == ["mixed"]
        assert catalog["sweep-soft-wide"]["display_name"]

    def test_grid_event_carries_the_catalog(self, tmp_path) -> None:
        sent: list[dict] = []
        session, _store, _console, _approval = _session(tmp_path, sent=sent)
        _create(session)
        grids = [e["timeline"]["beat_grid"] for e in sent if e.get("type") == "song_timeline"]
        assert grids, "격자 이벤트가 안 나갔다"
        ids = [entry["fx_id"] for entry in grids[-1]["fx_templates"]]
        assert "sweep-soft-wide" in ids


class TestProtocol:
    def _payload(self, **overrides) -> dict:
        base = {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_new_preset",
            "bar": 1,
            "target": "BACK",
            "field": "effect",
            "label": "LA Sweep 2",
            "description": "설명",
            "fx": dict(_FX),
        }
        base.update(overrides)
        return base

    def test_effect_with_recipe_parses(self) -> None:
        assert parse_client_message(json.dumps(self._payload()))["fx"] == _FX

    def test_effect_without_recipe_is_rejected(self) -> None:
        payload = self._payload()
        del payload["fx"]
        with pytest.raises(ProtocolError):
            parse_client_message(json.dumps(payload))

    @pytest.mark.parametrize(
        "fx",
        [
            {**_FX, "fx_id": ""},
            {**_FX, "period_unit": "second"},
            {**_FX, "period_value": 0},
            {**_FX, "period_value": 1.5},
            {**_FX, "period_value": True},
            "sweep-soft-wide",
        ],
    )
    def test_bad_recipe_is_rejected(self, fx) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(json.dumps(self._payload(fx=fx)))

    def test_recipe_on_another_field_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(json.dumps(self._payload(field="dimmer_effect")))
