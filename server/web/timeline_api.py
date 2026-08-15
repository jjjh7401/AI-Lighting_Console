"""REST surface for the director-timeline library (save / list / load / delete).

Query-and-projection only: no route here sends a console command. "Load"
means "make this saved projection the runbook's current timeline" — the
shared ``SongTimelineStore`` is updated, so the SAME replay path that already
serves page refreshes serves the loaded timeline to every (re)connection.
Executing anything from a loaded timeline still rides the approval gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from server.web.session import SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary, timeline_entry_summary

__all__ = ["TimelineLibraryDeps", "build_timeline_router"]


@dataclass
class TimelineLibraryDeps:
    store: SongTimelineStore
    library: SongTimelineLibrary


def build_timeline_router(deps: TimelineLibraryDeps) -> APIRouter:
    router = APIRouter()

    @router.get("/api/timelines")
    def list_timelines() -> dict:
        return {"items": [timeline_entry_summary(entry) for entry in deps.library.items()]}

    @router.post("/api/timelines")
    def save_timeline(body: dict) -> dict:
        name = body.get("name") if isinstance(body, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_name", "message": "저장 이름을 입력해 주세요."},
            )
        current = deps.store.latest
        if current is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_timeline",
                    "message": "저장할 감독 타임라인이 아직 없습니다. "
                    "곡 설계를 먼저 완료해 주세요.",
                },
            )
        entry = deps.library.save(name, current)
        return {"ok": True, "item": timeline_entry_summary(entry)}

    @router.post("/api/timelines/{entry_id}/load")
    def load_timeline(entry_id: str) -> dict:
        entry = deps.library.get(entry_id)
        if entry is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "해당 타임라인을 찾을 수 없습니다."},
            )
        # The store is the single replay source: a refresh or a second browser
        # sees the SAME loaded timeline, exactly like a fresh design turn. The
        # library NAME becomes the displayed song title — the design flow only
        # knows the generic "Design Interview"; the director's chosen name is
        # the meaningful one (user finding, 2026-08-15).
        timeline = dict(entry["timeline"])
        timeline["song_title"] = entry["name"]
        deps.store.latest = timeline
        return {"ok": True, "item": timeline_entry_summary(entry), "timeline": timeline}

    @router.delete("/api/timelines/{entry_id}")
    def delete_timeline(entry_id: str) -> dict:
        if not deps.library.remove(entry_id):
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "해당 타임라인을 찾을 수 없습니다."},
            )
        return {"ok": True}

    return router
