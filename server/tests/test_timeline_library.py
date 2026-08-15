"""Director-timeline library (save / list / load / delete) — store + REST.

여러 곡·여러 버전을 저장했다가 다시 불러오는 라이브러리 (user request,
2026-08-14). Read-and-projection only: no route sends a console command, and
loading an entry only swaps the runbook's review projection.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.timeline_library import SongTimelineLibrary, timeline_entry_summary

from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

_TIMELINE = {
    "song_title": "Design Interview",
    "sequence_number": 210,
    "lifecycle": "verified",
    "sections": [{"index": 1, "label": "도입"}],
}


def _deps(tmp_path):
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel)
    return WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
    )


class TestSongTimelineLibrary:
    def test_save_list_get_remove_roundtrip_with_persistence(self, tmp_path):
        path = tmp_path / "library.json"
        library = SongTimelineLibrary(path)
        entry = library.save("밝은 팝 무대 v1", _TIMELINE)
        assert entry["name"] == "밝은 팝 무대 v1"
        assert entry["timeline"]["sequence_number"] == 210

        # Same name twice = two versions, newest first in the listing.
        second = library.save("밝은 팝 무대 v1", {**_TIMELINE, "lifecycle": "pending_approval"})
        names = [item["id"] for item in library.items()]
        assert names == [second["id"], entry["id"]]

        # A fresh instance (= restarted server) reads both back.
        reborn = SongTimelineLibrary(path)
        assert len(reborn.items()) == 2
        assert reborn.get(entry["id"])["timeline"] == _TIMELINE

        assert reborn.remove(entry["id"]) is True
        assert reborn.remove(entry["id"]) is False
        assert SongTimelineLibrary(path).get(entry["id"]) is None

    def test_auto_save_numbers_versions_per_base_name(self, tmp_path):
        library = SongTimelineLibrary(tmp_path / "library.json")
        first = library.auto_save("Sequence 110", _TIMELINE)
        second = library.auto_save("Sequence 110", _TIMELINE)
        other = library.auto_save("밝은 팝 무대", _TIMELINE)
        assert first["name"] == "Sequence 110 (자동 v1)"
        assert second["name"] == "Sequence 110 (자동 v2)"
        assert other["name"] == "밝은 팝 무대 (자동 v1)"

    def test_auto_save_ignores_manual_names_and_survives_deletion_gaps(self, tmp_path):
        library = SongTimelineLibrary(tmp_path / "library.json")
        library.save("Sequence 110", _TIMELINE)  # manual save, no stamp
        library.save("Sequence 110 (자동 v7) 복사본", _TIMELINE)  # not an exact stamp
        third = library.auto_save("Sequence 110", _TIMELINE)
        assert third["name"] == "Sequence 110 (자동 v1)"
        # Numbering is max(existing stamp)+1 — deleting versions frees numbers.
        library.remove(third["id"])
        library.auto_save("Sequence 110", _TIMELINE)
        latest = library.auto_save("Sequence 110", _TIMELINE)
        assert latest["name"] == "Sequence 110 (자동 v2)"

    def test_blank_name_and_empty_payload_are_refused(self, tmp_path):
        library = SongTimelineLibrary(tmp_path / "library.json")
        try:
            library.save("   ", _TIMELINE)
            raise AssertionError("blank name must be refused")
        except ValueError:
            pass
        try:
            library.save("이름", {})
            raise AssertionError("empty payload must be refused")
        except ValueError:
            pass

    def test_corrupt_file_fails_open_to_an_empty_library(self, tmp_path):
        path = tmp_path / "library.json"
        path.write_text("{broken", encoding="utf-8")
        assert SongTimelineLibrary(path).items() == []

    def test_summary_carries_no_section_payload(self):
        summary = timeline_entry_summary(
            {"id": "abc", "name": "n", "saved_at": "t", "timeline": _TIMELINE}
        )
        assert summary["section_count"] == 1
        assert "sections" not in summary
        assert summary["sequence_number"] == 210


class TestTimelineApi:
    def test_save_requires_a_current_timeline_and_a_name(self, tmp_path):
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client:
            no_name = client.post("/api/timelines", json={"name": "  "})
            assert no_name.status_code == 400
            assert no_name.json()["detail"]["error"] == "invalid_name"
            no_timeline = client.post("/api/timelines", json={"name": "곡1"})
            assert no_timeline.status_code == 400
            assert no_timeline.json()["detail"]["error"] == "no_timeline"

    def test_save_list_load_delete_roundtrip(self, tmp_path):
        deps = _deps(tmp_path)
        deps.song_timeline_store.latest = _TIMELINE
        with TestClient(create_app(deps)) as client:
            saved = client.post("/api/timelines", json={"name": "밝은 팝 무대"})
            assert saved.status_code == 200
            entry_id = saved.json()["item"]["id"]

            listed = client.get("/api/timelines").json()["items"]
            assert [item["id"] for item in listed] == [entry_id]
            assert listed[0]["sequence_number"] == 210

            # Loading swaps the shared store — the replay path every
            # (re)connection already uses now serves the loaded timeline.
            deps.song_timeline_store.latest = None
            loaded = client.post(f"/api/timelines/{entry_id}/load")
            assert loaded.status_code == 200
            assert loaded.json()["timeline"]["sequence_number"] == 210
            # The library name becomes the displayed song title on load.
            assert loaded.json()["timeline"]["song_title"] == "밝은 팝 무대"
            assert deps.song_timeline_store.latest == {**_TIMELINE, "song_title": "밝은 팝 무대"}

            assert client.delete(f"/api/timelines/{entry_id}").status_code == 200
            assert client.get("/api/timelines").json()["items"] == []
            assert client.post(f"/api/timelines/{entry_id}/load").status_code == 404
            assert client.delete(f"/api/timelines/{entry_id}").status_code == 404
