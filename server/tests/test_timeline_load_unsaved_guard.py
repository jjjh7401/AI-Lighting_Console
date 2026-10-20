"""WT-load-unsaved-guard — 저장 안 한 작업본을 라이브러리 불러오기가 말없이 덮지 않는다.

실측(2026-10-20, 헤드리스 E2E): 작업본 「LOVE ATTACK — Aside 새 연출 v5」가 「수정됨 · 미저장」
상태였는데, 라이브러리 항목 「LOVE ATTACK 2026-10-15」를 불러오자 확인 창 없이 바뀌었고 12:37–
12:40 사이 자동 백업도 없어 수정이 사라졌다.

원인: ``timeline_api.load_timeline`` 이 ``store.latest`` 를 저장본으로 통째로 바꾸면서 지금 작업본의
「미저장」 표식(``draft.dirty``, ``ChatSession._draft_badge``)을 보지 않았다.

고침(서버가 기준 — 어느 화면 경로로 불러와도 안전하게): 미저장 수정이 있으면 먼저 지금 작업본을
「<곡> 불러오기 전 백업 (자동 vN)」으로 라이브러리에 남기고 불러온다. 백업을 못 남기면 불러오지
않는다. 콘솔 접촉 0건.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.web.app import create_app

from .test_timeline_library import _deps

_SAVED = {
    "song_title": "LOVE ATTACK",
    "sequence_number": 210,
    "lifecycle": "verified",
    "sections": [{"index": 1, "label": "도입"}],
}

_DIRTY_DRAFT = {
    "song_title": "LOVE ATTACK — Aside 새 연출 v5",
    "sequence_number": 210,
    "lifecycle": "verified",
    "sections": [{"index": 1, "label": "도입 (수정)"}],
    "draft": {"dirty": True, "depth": 3, "last_change": ["큐 1 색 바꿈"]},
}


def _names(deps) -> list[str]:
    return [entry["name"] for entry in deps.timeline_library.items()]


def test_loading_over_an_unsaved_draft_backs_it_up_first(tmp_path):
    deps = _deps(tmp_path)
    entry = deps.timeline_library.save("LOVE ATTACK 2026-10-15", _SAVED)
    deps.song_timeline_store.latest = dict(_DIRTY_DRAFT)
    with TestClient(create_app(deps)) as client:
        response = client.post(f"/api/timelines/{entry['id']}/load")
    assert response.status_code == 200
    backup_name = "LOVE ATTACK — Aside 새 연출 v5 불러오기 전 백업 (자동 v1)"
    assert backup_name in _names(deps)
    backup = next(e for e in deps.timeline_library.items() if e["name"] == backup_name)
    # 백업은 지금 작업본 그대로다 — 수정한 칸이 남는다.
    assert backup["timeline"]["sections"] == _DIRTY_DRAFT["sections"]
    assert response.json()["backup"]["name"] == backup_name
    # 불러오기 자체는 그대로 일어난다.
    assert deps.song_timeline_store.latest["sections"] == _SAVED["sections"]


def test_a_clean_draft_is_replaced_without_a_backup(tmp_path):
    deps = _deps(tmp_path)
    entry = deps.timeline_library.save("LOVE ATTACK 2026-10-15", _SAVED)
    clean = {**_DIRTY_DRAFT, "draft": {"dirty": False, "depth": 0, "last_change": []}}
    deps.song_timeline_store.latest = clean
    with TestClient(create_app(deps)) as client:
        response = client.post(f"/api/timelines/{entry['id']}/load")
    assert response.status_code == 200
    assert _names(deps) == ["LOVE ATTACK 2026-10-15"]
    assert response.json()["backup"] is None


def test_a_draft_already_saved_as_is_is_not_backed_up_twice(tmp_path):
    # 감독이 「현재 타임라인 저장」으로 막 저장했다면 같은 내용이 이미 라이브러리에 있다.
    deps = _deps(tmp_path)
    entry = deps.timeline_library.save("LOVE ATTACK 2026-10-15", _SAVED)
    draft = dict(_DIRTY_DRAFT)
    deps.song_timeline_store.latest = draft
    with TestClient(create_app(deps)) as client:
        assert client.post("/api/timelines", json={"name": "Aside v5"}).status_code == 200
        response = client.post(f"/api/timelines/{entry['id']}/load")
    assert response.status_code == 200
    assert sorted(_names(deps)) == sorted(["LOVE ATTACK 2026-10-15", "Aside v5"])
    assert response.json()["backup"] is None


def test_a_freshly_loaded_timeline_carries_no_unsaved_marker(tmp_path):
    # 미저장 상태에서 저장한 판에는 「draft.dirty」가 같이 저장된다. 불러온 직후는 저장본과 같으니
    # 미저장이 아니다 — 안 그러면 다음 불러오기마다 손대지 않은 판을 또 백업한다.
    deps = _deps(tmp_path)
    entry = deps.timeline_library.save("Aside v5", dict(_DIRTY_DRAFT))
    with TestClient(create_app(deps)) as client:
        response = client.post(f"/api/timelines/{entry['id']}/load")
    assert response.status_code == 200
    assert "draft" not in deps.song_timeline_store.latest
    assert "draft" not in response.json()["timeline"]


def test_a_failed_backup_refuses_the_load_and_keeps_the_draft(tmp_path, monkeypatch):
    deps = _deps(tmp_path)
    entry = deps.timeline_library.save("LOVE ATTACK 2026-10-15", _SAVED)
    draft = dict(_DIRTY_DRAFT)
    deps.song_timeline_store.latest = draft

    def _boom(base_name, timeline):
        raise OSError("disk full")

    monkeypatch.setattr(deps.timeline_library, "auto_save", _boom)
    with TestClient(create_app(deps)) as client:
        response = client.post(f"/api/timelines/{entry['id']}/load")
    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "backup_failed"
    assert deps.song_timeline_store.latest == draft
