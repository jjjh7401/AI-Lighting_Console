"""Preset-pool browsing API (``server/web/presets_api.py``) — the on-demand
half of the dashboard preset design.

Four properties this file exists to hold:

* The pool number the client supplies is validated against the pool LISTING
  the console just returned — an unlisted number is a 404, never a guessed
  path read, and a TRUNCATED listing says so in the refusal.
* Contents are fetched fresh per call (two ``query_state`` reads, no shared
  drilldown budget) and carry the responder's own completeness signals.
* A name-only slot (no real ``no``) degrades honestly instead of being
  numbered by position — the shared ``rig_object`` rule.
* The module holds NO execution surface: a source scan pins that it never
  imports ``server.bridge`` or an execution-capable port.
"""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.web.presets_api import PresetsDeps, build_presets_router

POOLS_PATH = "DataPool/PresetPools"


class _StatePort:
    def __init__(self, tree: dict[str, dict]) -> None:
        self._tree = tree
        self.queried: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queried.append(path)
        if path not in self._tree:
            raise LookupError(f"unknown object path: {path}")
        return self._tree[path]


def _payload(path: str, children: list[dict], *, truncated: bool = False, name: str = "") -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": children,
        "node": {"childCount": len(children), "name": name},
        "truncated": truncated,
    }


def _client(tree: dict[str, dict]) -> tuple[TestClient, _StatePort]:
    port = _StatePort(tree)
    app = FastAPI()
    app.include_router(build_presets_router(PresetsDeps(state_port=port)))
    return TestClient(app), port


def _default_tree(*, pool_truncated: bool = False, pools_truncated: bool = False) -> dict:
    return {
        POOLS_PATH: _payload(
            POOLS_PATH,
            [{"i": 1, "name": "Dimmer"}, {"i": 21, "name": "All 1"}],
            truncated=pools_truncated,
        ),
        f"{POOLS_PATH}/21": _payload(
            f"{POOLS_PATH}/21",
            [{"i": 1, "name": "Breath FX"}, {"i": 2, "name": "Snap Pulse"}, {"name": "ghost"}],
            truncated=pool_truncated,
            name="All 1",
        ),
    }


class TestListPools:
    def test_the_pool_listing_rides_the_shared_rig_shape(self):
        client, _port = _client(_default_tree())
        body = client.get("/api/presets").json()
        assert body["pools"] == [
            {"no": 1, "name": "Dimmer"},
            {"no": 21, "name": "All 1"},
        ]
        assert body["truncated"] is False
        assert body["total"] == 2

    def test_an_unreachable_console_is_a_502_not_an_empty_list(self):
        client, _port = _client({})
        response = client.get("/api/presets")
        assert response.status_code == 502
        assert "읽지 못했습니다" in response.json()["detail"]


class TestReadPool:
    def test_the_happy_path_costs_exactly_one_read(self):
        # Popup-open latency is one OSC round trip: the pool is read DIRECTLY
        # and named by its own node — no pre-validating listing query.
        client, port = _client(_default_tree())
        body = client.get("/api/presets/21").json()
        assert port.queried == [f"{POOLS_PATH}/21"]
        assert body["pool"] == {"no": 21, "name": "All 1"}
        # The name-only "ghost" child degrades to a name-only entry — never
        # numbered by its listing position.
        assert body["presets"] == [
            {"no": 1, "name": "Breath FX"},
            {"no": 2, "name": "Snap Pulse"},
            {"name": "ghost"},
        ]
        assert body["total"] == 3

    def test_an_unlisted_pool_is_a_404_diagnosed_on_the_failure_path_only(self):
        client, port = _client(_default_tree())
        response = client.get("/api/presets/99")
        assert response.status_code == 404
        # The listing is spent only AFTER the direct read failed.
        assert port.queried == [f"{POOLS_PATH}/99", POOLS_PATH]

    def test_a_truncated_pool_listing_names_the_uncertainty_in_the_404(self):
        client, _port = _client(_default_tree(pools_truncated=True))
        response = client.get("/api/presets/99")
        assert response.status_code == 404
        assert "잘려 있어" in response.json()["detail"]

    def test_the_pools_own_truncation_flag_rides_through(self):
        client, _port = _client(_default_tree(pool_truncated=True))
        assert client.get("/api/presets/21").json()["truncated"] is True

    def test_a_listed_pool_whose_read_fails_is_a_502_not_a_404(self):
        tree = _default_tree()
        del tree[f"{POOLS_PATH}/21"]
        client, _port = _client(tree)
        assert client.get("/api/presets/21").status_code == 502

    def test_a_dead_console_is_a_502_from_the_diagnosis_path(self):
        client, _port = _client({})
        assert client.get("/api/presets/21").status_code == 502


class TestPaletteSwatches:
    """팔레트 라벨 → 색 원형(#rrggbb) — 앱이 아는 색만, 발명 금지.

    콘솔은 프리셋 색을 노출하지 않는다(Appearance/Color prop 판독 불가,
    2026-08-16 라이브 프로브) — 유일하게 정직한 출처는 앱 자신이 저장한
    COLOR_PALETTE_SEQUENCE다. 수동 프리셋은 color 필드 자체가 없다.
    """

    def _color_tree(self) -> dict:
        return {
            POOLS_PATH: _payload(POOLS_PATH, [{"i": 4, "name": "Color"}]),
            f"{POOLS_PATH}/4": _payload(
                f"{POOLS_PATH}/4",
                [
                    {"i": 1, "name": "FrontWarm"},  # 수동 — 색 미상
                    {"i": 21, "name": "Warm White"},
                    {"i": 31, "name": "Warm White#2"},  # 콘솔 중복명 접미
                    {"i": 23, "name": "Red"},
                ],
                name="Color",
            ),
        }

    def test_palette_names_carry_their_own_hex_and_manual_ones_do_not(self):
        client, _port = _client(self._color_tree())
        presets = {p["no"]: p for p in client.get("/api/presets/4").json()["presets"]}
        assert presets[23]["color"] == "#ff0000"  # Red (100,0,0) → #ff0000
        assert presets[21]["color"] == presets[31]["color"]  # #N 접미 동일 취급
        assert "color" not in presets[1]  # 수동 프리셋 — 색 발명 금지

    def test_the_hex_conversion_is_percent_scaled(self):
        from server.web.presets_api import _palette_hex_by_label
        from server.web.session import COLOR_PALETTE_SEQUENCE

        palette = _palette_hex_by_label()
        assert set(palette) == {label for label, _rgb in COLOR_PALETTE_SEQUENCE}
        # Amber (100,55,5) → 255,140,13
        assert palette["Amber"] == "#ff8c0d"

    def test_phaser_presets_carry_their_step_colours_in_order(self):
        # 앱 자신이 저장한 페이저(4.31~4.40)의 스텝 색 — 같은 발명 금지
        # 규율의 확장: COLOR_PHASER_SEQUENCE가 유일한 출처다.
        tree = {
            POOLS_PATH: _payload(POOLS_PATH, [{"i": 4, "name": "Color"}]),
            f"{POOLS_PATH}/4": _payload(
                f"{POOLS_PATH}/4",
                [
                    {"i": 33, "name": "Chase RB"},
                    {"i": 37, "name": "Rainbow"},
                    {"i": 39, "name": "Duo GL#2"},  # 콘솔 중복명 접미 동일 취급
                    {"i": 1, "name": "MyPhaser"},  # 수동 페이저 — 색 미상, 발명 금지
                ],
                name="Color",
            ),
        }
        client, _port = _client(tree)
        presets = {p["no"]: p for p in client.get("/api/presets/4").json()["presets"]}
        from server.web.presets_api import _palette_hex_by_label

        hx = _palette_hex_by_label()
        assert presets[33]["colors"] == [hx["Red"], hx["Blue"]]  # 스텝 순서 보존
        assert presets[37]["colors"] == [hx["Red"], hx["Green"], hx["Blue"]]
        assert presets[39]["colors"] == [hx["Green"], hx["Lavender"]]  # 접미 동일 취급
        assert "colors" not in presets[1] and "color" not in presets[1]

    def test_every_catalog_phaser_label_resolves_to_step_hexes(self):
        from server.web.presets_api import _phaser_hexes_by_label
        from server.web.session import COLOR_PHASER_SEQUENCE

        hexes = _phaser_hexes_by_label()
        assert set(hexes) == {label for label, _s, _f, _p in COLOR_PHASER_SEQUENCE}
        for label, steps, _form, _phase in COLOR_PHASER_SEQUENCE:
            assert len(hexes[label]) == len(steps) >= 2


class TestDimmerSwatches:
    """디머 라벨 → 회색 색 원형(#rrggbb) — T5 지시(``TestPaletteSwatches``의
    미러). 값(0~100)을 255*v/100 반올림한 R=G=B 회색으로 렌더한다. 라벨은
    컬러 팔레트·페이저와 서로소라(Dim 10..Full vs Warm White..Lavender,
    Breathe Soft.. vs Breathe Warm..) 병합에 충돌이 없다.
    """

    def _dimmer_tree(self) -> dict:
        return {
            POOLS_PATH: _payload(POOLS_PATH, [{"i": 1, "name": "Dimmer"}]),
            f"{POOLS_PATH}/1": _payload(
                f"{POOLS_PATH}/1",
                [
                    {"i": 1, "name": "FrontBack"},  # 수동 — 색 미상
                    {"i": 11, "name": "Dim 10"},
                    {"i": 15, "name": "Dim 50"},
                    {"i": 25, "name": "Dim 50#2"},  # 콘솔 중복명 접미
                    {"i": 20, "name": "Full"},
                ],
                name="Dimmer",
            ),
        }

    def test_level_labels_carry_their_own_gray_hex_and_manual_ones_do_not(self):
        client, _port = _client(self._dimmer_tree())
        presets = {p["no"]: p for p in client.get("/api/presets/1").json()["presets"]}
        assert presets[11]["color"] == "#1a1a1a"  # Dim 10 (10%) → round(25.5)=26
        assert presets[15]["color"] == "#808080"  # Dim 50 (50%) → round(127.5)=128
        assert presets[15]["color"] == presets[25]["color"]  # #N 접미 동일 취급
        assert presets[20]["color"] == "#ffffff"  # Full (100%)
        assert "color" not in presets[1]  # 수동 프리셋 — 색 발명 금지

    def test_the_gray_conversion_is_percent_scaled(self):
        from server.web.presets_api import _dimmer_hex_by_label
        from server.web.session import DIMMER_LEVEL_SEQUENCE

        gray = _dimmer_hex_by_label()
        assert set(gray) == {label for label, _value in DIMMER_LEVEL_SEQUENCE}
        assert gray["Dim 50"] == "#808080"
        assert gray["Full"] == "#ffffff"
        assert all(
            hex_value[1:3] == hex_value[3:5] == hex_value[5:7] for hex_value in gray.values()
        )

    def test_dimmer_phaser_presets_carry_their_step_gray_hexes_in_order(self):
        # 앱 자신이 저장한 디머 페이저(1.21~1.30)의 스텝 회색 — 컬러 페이저와
        # 같은 발명 금지 규율의 확장: DIMMER_PHASER_SEQUENCE가 유일한 출처다.
        tree = {
            POOLS_PATH: _payload(POOLS_PATH, [{"i": 1, "name": "Dimmer"}]),
            f"{POOLS_PATH}/1": _payload(
                f"{POOLS_PATH}/1",
                [
                    {"i": 23, "name": "Pulse Hard"},
                    {"i": 27, "name": "Ripple"},
                    {"i": 29, "name": "Alt Half#2"},  # 콘솔 중복명 접미 동일 취급
                    {"i": 1, "name": "MyFade"},  # 수동 페이저 — 색 미상, 발명 금지
                ],
                name="Dimmer",
            ),
        }
        client, _port = _client(tree)
        presets = {p["no"]: p for p in client.get("/api/presets/1").json()["presets"]}

        assert presets[23]["colors"] == ["#000000", "#ffffff"]  # Pulse Hard 0/100
        assert presets[27]["colors"] == ["#4c4c4c", "#999999", "#ffffff"]  # Ripple 30/60/100
        assert presets[29]["colors"] == ["#808080", "#ffffff"]  # Alt Half 접미 동일 취급
        assert "colors" not in presets[1] and "color" not in presets[1]

    def test_every_catalog_dimmer_phaser_label_resolves_to_step_gray_hexes(self):
        from server.web.presets_api import _dimmer_phaser_hexes_by_label
        from server.web.session import DIMMER_PHASER_SEQUENCE

        hexes = _dimmer_phaser_hexes_by_label()
        assert set(hexes) == {label for label, _v, _f, _p in DIMMER_PHASER_SEQUENCE}
        for label, values, _form, _phase in DIMMER_PHASER_SEQUENCE:
            assert len(hexes[label]) == len(values) >= 2

    def test_dimmer_and_color_swatch_labels_do_not_collide(self):
        from server.web.presets_api import (
            _dimmer_hex_by_label,
            _dimmer_phaser_hexes_by_label,
            _palette_hex_by_label,
            _phaser_hexes_by_label,
        )

        assert set(_dimmer_hex_by_label()).isdisjoint(_palette_hex_by_label())
        assert set(_dimmer_phaser_hexes_by_label()).isdisjoint(_phaser_hexes_by_label())


class TestPagedPoolRead:
    """24캡 너머 풀의 팝업 판독 — 라이브 2026-08-16: 페이저 10종(4.31~4.40)이
    첫 창 밖이라 팝업이 콘솔과 다른 풀을 보여줬다. 세션 판독기의 페이징
    규율(에코 검증·무진전 방어)을 상속하되, 읽기 전용 팝업은 부분을
    ``truncated=True``로 고지하며 보여준다(None 강등이 아니라)."""

    class _PagingPort:
        """offset을 에코하는 §4.2 페이징 응답기 더블."""

        def __init__(self, pool_children: list[dict], *, window: int = 24) -> None:
            self._children = pool_children
            self._window = window
            self.calls: list[tuple[str, int]] = []

        def query_state(self, path: str, *, offset: int = 0) -> dict:
            self.calls.append((path, offset))
            if path == POOLS_PATH:
                return _payload(POOLS_PATH, [{"i": 4, "name": "Color"}])
            window = self._children[offset : offset + self._window]
            payload = {
                "v": 1,
                "kind": "state",
                "path": path,
                "children": window,
                "node": {"childCount": len(self._children), "name": "Color"},
                "truncated": offset + len(window) < len(self._children),
            }
            if offset:
                payload["offset"] = offset
            return payload

    @staticmethod
    def _app(port) -> TestClient:
        app = FastAPI()
        app.include_router(build_presets_router(PresetsDeps(state_port=port)))
        return TestClient(app)

    @staticmethod
    def _thirty_four() -> list[dict]:
        # 24캡 첫 창 + 둘째 창에 걸치는 34슬롯 — 4.31~4.40 라이브 사고 재현.
        return [{"i": n, "name": f"P{n}"} for n in range(1, 31)] + [
            {"i": 31, "name": "Breathe Warm"},
            {"i": 32, "name": "Breathe Cool"},
            {"i": 39, "name": "Duo GL"},
            {"i": 40, "name": "Slam RW"},
        ]

    def test_a_pool_past_the_window_is_read_to_completion(self):
        port = self._PagingPort(self._thirty_four())
        body = self._app(port).get("/api/presets/4").json()
        numbers = [p["no"] for p in body["presets"]]
        assert numbers[-4:] == [31, 32, 39, 40]  # 첫 창 밖 슬롯이 도착했다
        assert len(numbers) == 34
        assert body["truncated"] is False
        assert body["total"] == 34
        # 첫 요청은 무페이징(하위호환), 후속 창만 offset을 싣는다.
        assert port.calls == [(f"{POOLS_PATH}/4", 0), (f"{POOLS_PATH}/4", 24)]

    def test_a_complete_first_window_still_costs_exactly_one_read(self):
        port = self._PagingPort([{"i": 1, "name": "Solo"}])
        body = self._app(port).get("/api/presets/4").json()
        assert port.calls == [(f"{POOLS_PATH}/4", 0)]
        assert body["truncated"] is False

    def test_a_legacy_port_without_offset_degrades_to_an_honest_truncation(self):
        # 페이징을 모르는 포트(offset 키워드 없음) — 첫 창만 보여주되
        # truncated로 미완을 고지한다. 부분을 전체로 꾸미지 않는다.
        children = self._thirty_four()
        tree = {
            POOLS_PATH: _payload(POOLS_PATH, [{"i": 4, "name": "Color"}]),
            f"{POOLS_PATH}/4": {
                **_payload(f"{POOLS_PATH}/4", children[:24], name="Color"),
                "node": {"childCount": 34, "name": "Color"},
                "truncated": True,
            },
        }
        client, port = _client(tree)
        body = client.get("/api/presets/4").json()
        assert len(body["presets"]) == 24
        assert body["truncated"] is True
        assert body["total"] == 34

    def test_a_responder_ignoring_offset_is_no_progress_not_a_loop(self):
        # 구버전 응답기: offset을 무시하고 항상 첫 창(에코 부재) — 에코
        # 불일치는 즉시 중단, 무한 페이징 루프에 빠지지 않는다.
        class _EcholessPort(self._PagingPort):
            def query_state(self, path: str, *, offset: int = 0) -> dict:
                payload = super().query_state(path, offset=offset)
                payload.pop("offset", None)
                return payload

        port = _EcholessPort(self._thirty_four())
        body = self._app(port).get("/api/presets/4").json()
        assert len(body["presets"]) == 24
        assert body["truncated"] is True
        assert len(port.calls) == 2  # 첫 창 + 무진전 확인 1회 — 반복 없음


class TestNoExecutionSurface:
    def test_the_module_never_imports_the_send_surface(self):
        source = Path("server/web/presets_api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
        forbidden = [m for m in modules if m.startswith("server.bridge")]
        assert forbidden == []
        assert "execute" not in source.replace("execution-capable", "")
