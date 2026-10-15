"""LOVE ATTACK 라이브러리 시드 — 항목 모양, 기본 격자, 불러오기 경로.

시드는 저장소에 있는 값만 싣는다: 구간·마디 지도는 비어 있어야 하고(마디 지도는 곡
오디오 분석이 만든다), 격자는 곡별 기본값 레지스트리와 같아야 한다.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.love_attack_timeline import (
    LOVE_ATTACK_ENTRY_ID,
    build_love_attack_timeline,
    love_attack_library_entry,
)
from server.web.session import SongTimelineStore
from server.web.timeline_api import TimelineLibraryDeps, build_timeline_router
from server.web.timeline_library import SongTimelineLibrary


def test_seed_entry_names_the_song_and_invents_no_sections() -> None:
    entry = love_attack_library_entry()
    timeline = entry["timeline"]

    assert entry["id"] == LOVE_ATTACK_ENTRY_ID
    assert entry["name"] == LOVE_ATTACK_TITLE
    assert timeline["song_title"] == LOVE_ATTACK_TITLE
    # 구간 초안은 마디 번호가 측정 지도와 어긋나 옮기지 않는다 — 시드에는 구간이 없다.
    assert timeline["sections"] == []
    # 마디 지도는 곡 오디오 분석이 만들어 초안에 붙인다 — 시드가 미리 싣지 않는다.
    assert "bar_map" not in timeline


def test_seed_beat_grid_is_the_registered_song_default() -> None:
    timeline = build_love_attack_timeline()

    assert timeline["beat_grid"]["tracks"], "LOVE ATTACK 기본 격자에 트랙이 있어야 한다"
    assert timeline["beat_grid"]["tracks"] == default_beat_grid(LOVE_ATTACK_TITLE)["tracks"]


def test_library_lists_the_seed_and_load_makes_it_the_live_draft() -> None:
    library = SongTimelineLibrary(path=None, seed=(love_attack_library_entry(),))
    store = SongTimelineStore()
    app = FastAPI()
    app.include_router(build_timeline_router(TimelineLibraryDeps(store=store, library=library)))
    client = TestClient(app)

    listing = client.get("/api/timelines").json()["items"]
    assert any(item["id"] == LOVE_ATTACK_ENTRY_ID for item in listing)

    response = client.post(f"/api/timelines/{LOVE_ATTACK_ENTRY_ID}/load")
    assert response.status_code == 200
    assert store.latest is not None
    assert store.latest["song_title"] == LOVE_ATTACK_TITLE
    assert store.latest["beat_grid"]["tracks"]
