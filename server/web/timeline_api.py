"""REST surface for the director-timeline library (save / list / load / delete).

Query-and-projection only: no route here sends a console command. "Load"
means "make this saved projection the runbook's current timeline" — the
shared ``SongTimelineStore`` is updated, so the SAME replay path that already
serves page refreshes serves the loaded timeline to every (re)connection.
Executing anything from a loaded timeline still rides the approval gate.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from server.design.analysis_timeline import carry_console_preset_records
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values
from server.web.messages import fill_bar_map_header
from server.web.session import (
    SongTimelineStore,
    beat_grid_has_owned_record,
    beat_grid_recorded_sequence_numbers,
    derive_beat_grid_fields,
)
from server.web.song_audio_store import SongAudioLinkStore
from server.web.timeline_library import SongTimelineLibrary, timeline_entry_summary

__all__ = ["TimelineLibraryDeps", "build_timeline_router"]

#: ``SongTimelineLibrary.auto_save`` 가 붙이는 이름 꼬리.
_AUTO_SAVE_NAME = re.compile(r".* \(자동 v\d+\)$")
#: 설계 흐름이 새 설계에 찍는 일반 이름(``song_cue_render._DESIGN_INTERVIEW_TITLE``).
_DESIGN_INTERVIEW_TITLE = "Design Interview"


@dataclass
class TimelineLibraryDeps:
    store: SongTimelineStore
    library: SongTimelineLibrary
    # 불러오기로 제목이 바뀌면 음원 링크를 새 열쇠로 복제하는 데 쓴다(``None`` 이면 건너뜀).
    song_audio_link_store: SongAudioLinkStore | None = None
    # 곡을 열 때 부른다 — 장비 판독 예열(리드 결정, 2026-10-19). ``None`` 이면 아무것도 하지 않는다.
    on_open: Callable[[], None] | None = None


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
        # 자동 저장(``<base> (자동 vN)``) 이름은 감독이 고른 이름이 아니다 — 저장된 곡 이름이
        # 있으면 그대로 둔다(1차 전체 실행 B-02: 「… 분석 전 백업 (자동 v1)」이 제목이 됐다).
        # 곡 이름이 비었거나 일반 설계 이름뿐이면 지금처럼 저장 이름을 쓴다.
        timeline = dict(entry["timeline"])
        old_key = (timeline.get("song_title"), timeline.get("sequence_number"))
        saved_title = str(timeline.get("song_title") or "").strip()
        keep_title = _AUTO_SAVE_NAME.match(str(entry["name"])) is not None and saved_title not in (
            "",
            _DESIGN_INTERVIEW_TITLE,
        )
        timeline["song_title"] = saved_title if keep_title else entry["name"]
        new_key = (timeline["song_title"], timeline.get("sequence_number"))
        # 음원 링크의 열쇠는 (song_title, sequence_number) — 이름이 바뀌면 옛 열쇠의 링크를
        # 새 열쇠로 복제한다(옛 열쇠는 지우지 않는다). 링크가 없거나 쓰기가 실패하면 조용히 넘긴다.
        links = deps.song_audio_link_store
        if links is not None and new_key != old_key:
            found = links.resolve(old_key)
            if found.status == "found" and found.record is not None and found.data is not None:
                with contextlib.suppress(OSError):
                    links.link(
                        new_key,
                        file_name=found.record["file_name"],
                        mime_type=found.record["mime_type"],
                        data=found.data,
                    )
        # WT-preset-reuse — 콘솔 프리셋 저장 기록은 작업본이 아니라 콘솔의 사실이다. 옛 작업본을
        # 불러와도 지금 작업본의 기록을 버리지 않는다. 안 그러면 다음 계획이 콘솔에 있는 같은
        # 프리셋을 못 알아보고 새 번호에 또 저장한다(2026-10-20 실측: 21개 재사용 0, DIM-100
        # 1.925 → 1.939). 재사용 여부는 콘솔 이름·기록 대조(``preset_plan``)가 가른다.
        current = deps.store.latest
        previous_grid = current.get("beat_grid") if isinstance(current, Mapping) else None
        if isinstance(previous_grid, Mapping) and isinstance(timeline.get("beat_grid"), Mapping):
            timeline = carry_console_preset_records(previous_grid, timeline)
        deps.store.latest = timeline
        if deps.on_open is not None:
            deps.on_open()
        # 카드 t644 — 응답도 재생(``ChatSession.song_timeline_replay``)과 같은 함수로 파생
        # 필드를 채운다. 카드 t651 — 풀 기억은 저장소의 것을 쓴다(재생 프레임과 같은 값). 이 요청은
        # 콘솔을 읽지 않는다. 저장소에는 원본을 그대로 둔다(보낼 때마다 파생).
        # 화면용 값(콘솔 프리셋 이름 등)도 재생(``_beat_grid_refresh_unsent_cells``)과 같은 함수로
        # 채운다 — 풀 기억은 저장소의 것이라 새 연결 재생과 같은 값이다.
        # 콘솔 시퀀스 번호도 같은 방식이다: 반영 기록을 저장소에서 읽는데, 곡 열쇠가 이 응답의
        # 이름(``song_title``)을 따르므로 이름을 바꾼 **뒤의** 타임라인으로 읽는다.
        timeline = attach_beat_grid_ui_values(
            timeline,
            pool_slots=deps.store.beat_grid_pool_slots,
            track_sequence_numbers=beat_grid_recorded_sequence_numbers(deps.store, timeline),
        )
        derived = derive_beat_grid_fields(
            timeline,
            snapshots=deps.store.beat_grid_snapshots,
            pool_slots=deps.store.beat_grid_pool_slots,
            empty_marks={},
            pool_read_at=deps.store.beat_grid_pool_read_at,
            has_owned_record=beat_grid_has_owned_record(deps.store, timeline),
        )
        # 화면 머리말(BPM·마디 수·박자표)도 재생(``song_timeline_event``)과 같은 함수로 채운다.
        return {
            "ok": True,
            "item": timeline_entry_summary(entry),
            "timeline": fill_bar_map_header(derived),
        }

    @router.delete("/api/timelines/{entry_id}")
    def delete_timeline(entry_id: str) -> dict:
        if not deps.library.remove(entry_id):
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "해당 타임라인을 찾을 수 없습니다."},
            )
        return {"ok": True}

    return router
